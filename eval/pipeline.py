"""LLM-as-a-judge evaluation pipeline for the staged planning methodology.

Compares two report-writing conditions on the same initial input:
  A (baseline): one-shot final report, no intermediate stages.
  B (proposed): the 4-stage flow (problem -> MVP scope -> risk -> final report)
                driven through the production Orchestrator + Codex CLI path.

Checklist source of truth: docs/llm-judge-evaluation-checklist.md
(32 atomic items D1-1..D8-4, penalties P1..P4, scoring formula in section 3).

Usage:
    uv run python eval/pipeline.py generate  --seeds 3
    uv run python eval/pipeline.py judge     --run <run_id> [--judge-model MODEL]
    uv run python eval/pipeline.py aggregate --run <run_id>
    uv run python eval/pipeline.py all       --seeds 3 [--judge-model MODEL]

Every step is resumable: existing output files are skipped, so a crashed run
can be re-invoked with the same --run id.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import random
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

CHECKLIST_PATH = ROOT_DIR / "docs" / "llm-judge-evaluation-checklist.md"
RESULTS_DIR = ROOT_DIR / "eval" / "results"
STAGE_IDS = ["stage_1", "stage_2", "stage_3", "stage_4"]

# Ablation conditions: each entry is the set of prior stages before output_layer.
# stages_4 runs all STAGE_IDS with no output_layer (identical to existing B).
ABLATION_STAGE_SETS: Dict[str, List[str]] = {
    "stages_1": ["stage_1"],
    "stages_2": ["stage_1", "stage_2"],
    "stages_3": ["stage_1", "stage_2", "stage_3"],
    "stages_4": ["stage_1", "stage_2", "stage_3", "stage_4"],
}

# ---------------------------------------------------------------------------
# Runtime config override — set by --model / --reasoning-effort CLI args
# ---------------------------------------------------------------------------

_RUNTIME_OVERRIDE: Dict[str, Any] = {}


def _make_runtime_config() -> Optional[Dict[str, Any]]:
    if not _RUNTIME_OVERRIDE:
        return None
    from app.backend.core.config_loader import get_model_runtime_config

    base = get_model_runtime_config()
    base.update(_RUNTIME_OVERRIDE)
    return base


# ---------------------------------------------------------------------------
# Checklist structure (must mirror docs/llm-judge-evaluation-checklist.md)
# ---------------------------------------------------------------------------

DIMENSION_ITEMS: Dict[str, List[str]] = {
    "D1": ["D1-1", "D1-2", "D1-3", "D1-4"],
    "D2": ["D2-1", "D2-2", "D2-3", "D2-4"],
    "D3": ["D3-1", "D3-2", "D3-3", "D3-4", "D3-5"],
    "D4": ["D4-1", "D4-2", "D4-3", "D4-4"],
    "D5": ["D5-1", "D5-2", "D5-3", "D5-4"],
    "D6": ["D6-1", "D6-2", "D6-3"],
    "D7": ["D7-1", "D7-2", "D7-3", "D7-4"],
    "D8": ["D8-1", "D8-2", "D8-3", "D8-4"],
}
ALL_ITEM_IDS = [item for items in DIMENSION_ITEMS.values() for item in items]
NA_ALLOWED_ITEMS = {"D5-4", "D8-1"}
GRADE_POINTS = {"pass": 1.0, "partial": 0.5, "fail": 0.0}
PENALTY_RULES = {
    "P1": {"per_hit": 0.5, "cap": 0.5},
    "P2": {"per_hit": 0.5, "cap": 1.5},
    "P3": {"per_hit": 0.5, "cap": 1.5},
    "P4": {"per_hit": 1.0, "cap": None},
}

# ---------------------------------------------------------------------------
# Pure scoring / masking helpers (unit-tested in tests/test_eval_pipeline.py)
# ---------------------------------------------------------------------------


def dimension_score(grades: Dict[str, str], dimension: str) -> Optional[float]:
    """Score = 1 + 4 * (earned / valid items); na items leave the denominator."""
    earned = 0.0
    valid = 0
    for item_id in DIMENSION_ITEMS[dimension]:
        grade = grades.get(item_id)
        if grade is None:
            raise ValueError(f"missing grade for {item_id}")
        if grade == "na":
            if item_id not in NA_ALLOWED_ITEMS:
                grade = "fail"  # invalid na is treated as fail
            else:
                continue
        earned += GRADE_POINTS[grade]
        valid += 1
    if valid == 0:
        return None
    return round(1 + 4 * (earned / valid), 2)


def penalty_deduction(penalty_codes: List[str]) -> float:
    total = 0.0
    counts: Dict[str, int] = {}
    for code in penalty_codes:
        if code not in PENALTY_RULES:
            continue
        counts[code] = counts.get(code, 0) + 1
    for code, count in counts.items():
        rule = PENALTY_RULES[code]
        deduction = rule["per_hit"] * count
        if rule["cap"] is not None:
            deduction = min(deduction, rule["cap"])
        total += deduction
    return round(total, 2)


def document_scores(
    item_grades: Dict[str, str],
    penalty_codes: List[str],
) -> Dict[str, Any]:
    dims = {dim: dimension_score(item_grades, dim) for dim in DIMENSION_ITEMS}
    valid_dims = [score for score in dims.values() if score is not None]
    base_total = sum(valid_dims) / len(valid_dims)
    deduction = penalty_deduction(penalty_codes)
    return {
        "dimensions": dims,
        "base_total": round(base_total, 3),
        "penalty": deduction,
        "total": round(base_total - deduction, 3),
    }


def verdict_from_scores(score_1: Optional[float], score_2: Optional[float]) -> str:
    if score_1 is None or score_2 is None:
        return "tie"
    if score_1 > score_2:
        return "doc1"
    if score_2 > score_1:
        return "doc2"
    return "tie"


def combine_verdicts(verdicts: List[str]) -> str:
    """Combine one or more verdicts expressed in condition terms (A/B/tie).

    With a single judgment the verdict stands as-is; with multiple judgments
    (e.g. swapped orders) a win only counts when all of them agree.
    """
    unique = set(verdicts)
    if len(unique) == 1 and unique <= {"A", "B"}:
        return verdicts[0]
    return "tie"


def doc_verdict_to_condition(verdict: str, order: str) -> str:
    """Map doc1/doc2/tie to A/B/tie given the presentation order ('AB' or 'BA')."""
    if verdict == "tie":
        return "tie"
    mapping = (
        {"doc1": "A", "doc2": "B"} if order == "AB" else {"doc1": "B", "doc2": "A"}
    )
    return mapping[verdict]


_MASK_PATTERNS = [
    re.compile(r"stage[_\s]?[1-4]", re.IGNORECASE),
    re.compile(r"[1-4]\s*단계"),
    re.compile(r"(?:문제\s*정의|MVP\s*범위|리스크\s*검증|최종\s*기획서?)\s*단계"),
    re.compile(r"이전\s*단계"),
    re.compile(r"다음\s*단계"),
    re.compile(r"단계를\s*거쳐"),
    re.compile(r"단계별\s*승인"),
]


def mask_process_mentions(text: str) -> str:
    for pattern in _MASK_PATTERNS:
        text = pattern.sub("[프로세스]", text)
    return text


def normalize_plain_text(text: str) -> str:
    """Flatten formatting so neither condition wins on markdown styling."""
    lines = []
    for line in text.splitlines():
        if re.fullmatch(r"\s*\|?[\s:|-]+\|?\s*", line) and "|" in line:
            continue  # markdown table separator row
        line = re.sub(r"^#{1,6}\s*", "## ", line)
        line = line.replace("**", "").replace("__", "")
        line = re.sub(r"\s*\|\s*", " · ", line).strip(" ·")
        lines.append(line.rstrip())
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def prepare_for_judging(text: str) -> str:
    return mask_process_mentions(normalize_plain_text(text))


# ---------------------------------------------------------------------------
# Repo data loading
# ---------------------------------------------------------------------------


def load_initial_inputs() -> Dict[str, str]:
    from app.frontend.demo_data import load_demo_inputs, scenario_initial_input

    inputs = load_demo_inputs(ROOT_DIR)
    return {
        scenario: scenario_initial_input(inputs, scenario) for scenario in inputs
    }


def load_stage_requests(source_path: Optional[Path] = None) -> Dict[str, Any]:
    """Extract DEMO_STAGE_REQUESTS / defaults from streamlit_app.py without
    importing it (the module runs the Streamlit app at import time)."""
    path = source_path or (ROOT_DIR / "app" / "frontend" / "streamlit_app.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: Dict[str, Any] = {}
    for node in tree.body:
        target_name = ""
        value = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            target_name, value = node.targets[0].id, node.value
        if target_name in {"DEMO_STAGE_REQUESTS", "DEFAULT_DEMO_STAGE_REQUESTS"}:
            found[target_name] = ast.literal_eval(value)
    if "DEFAULT_DEMO_STAGE_REQUESTS" not in found:
        raise RuntimeError("DEFAULT_DEMO_STAGE_REQUESTS not found in streamlit_app.py")
    return {
        "default": found["DEFAULT_DEMO_STAGE_REQUESTS"],
        "per_scenario": found.get("DEMO_STAGE_REQUESTS", {}),
    }


def stage_inputs_for(
    scenario: str,
    initial_input: str,
    stage_requests: Dict[str, Any],
) -> Dict[str, str]:
    per_scenario = stage_requests["per_scenario"].get(scenario, {})
    default = stage_requests["default"]
    inputs = {
        stage_id: per_scenario.get(stage_id, default[stage_id])
        for stage_id in STAGE_IDS
    }
    inputs["stage_1"] = initial_input  # the first ask is always the raw hook
    return inputs


def list_scenarios() -> List[str]:
    import yaml

    with open(ROOT_DIR / "config" / "scenarios.yaml", "r", encoding="utf-8") as f:
        return list(yaml.safe_load(f)["scenarios"].keys())


# ---------------------------------------------------------------------------
# Generation — condition A (one-shot) and condition B (staged orchestrator)
# ---------------------------------------------------------------------------

BASELINE_INSTRUCTIONS = "\n".join(
    [
        "당신은 서비스 기획 어시스턴트입니다.",
        "아래 비개발 기획자의 요청을 읽고, 최종 서비스 기획서를 한국어로 작성하세요.",
        "기획서는 경영진이 진행/보류를 결재하고 개발팀이 착수 검토를 시작할 수 있는 "
        "수준이어야 합니다.",
        "필요하면 web_search로 외부 근거를 조사해 반영하세요.",
        "출력은 마크다운 문서 하나로만 작성하세요.",
    ]
)


def generate_baseline(
    initial_input: str,
    extra_requests: List[str],
) -> str:
    from app.backend.integrations.codex_client import CodexClient

    blocks = ["[기획자의 요청]", initial_input]
    if extra_requests:
        blocks.append("[기획자의 추가 요청사항]")
        blocks.extend(f"- {request}" for request in extra_requests)
    client = CodexClient(runtime_config=_make_runtime_config(), cwd=ROOT_DIR)
    return client.generate_text(
        instructions=BASELINE_INSTRUCTIONS,
        input_text="\n".join(blocks),
    )


def generate_proposed(scenario: str, stage_inputs: Dict[str, str]) -> Dict[str, Any]:
    from app.backend.core.orchestrator import Orchestrator
    from app.backend.core.stage_manager import StageManager

    manager = StageManager()
    rt = _make_runtime_config()
    if rt is not None:
        from app.backend.core.agent_graph import MilemateAgentGraphRunner
        from app.backend.integrations.codex_client import CodexClient

        runner = MilemateAgentGraphRunner(codex_client=CodexClient(runtime_config=rt))
        orchestrator = Orchestrator(stage_manager=manager, graph_runner=runner)
    else:
        orchestrator = Orchestrator(stage_manager=manager)
    session = manager.create_session(
        scenario=scenario,
        user_input=stage_inputs["stage_1"],
    )
    for stage_id in STAGE_IDS:
        response = orchestrator.run_current_stage(
            session.session_id,
            user_input=stage_inputs[stage_id],
            context={},
        )
        if response.stage_id != stage_id:
            raise RuntimeError(
                f"stage drift: expected {stage_id}, got {response.stage_id}"
            )
        orchestrator.approve_current_stage(session.session_id)
    bundle = orchestrator.build_final_report(session.session_id)
    return bundle.model_dump(mode="json")


def generate_proposed_ablation(
    scenario: str,
    stage_inputs: Dict[str, str],
    prior_stages: List[str],
) -> Dict[str, Any]:
    """Run prior_stages then output_layer (or build_final_report for stages_4)."""
    from app.backend.core.agent_graph import AgentGraphInput, MilemateAgentGraphRunner
    from app.backend.core.orchestrator import Orchestrator
    from app.backend.core.stage_manager import StageManager
    from app.backend.integrations.codex_client import CodexClient
    from app.backend.schemas.report import FinalReportBundle

    manager = StageManager()
    rt = _make_runtime_config()
    if rt is not None:
        runner = MilemateAgentGraphRunner(codex_client=CodexClient(runtime_config=rt))
        orchestrator = Orchestrator(stage_manager=manager, graph_runner=runner)
    else:
        orchestrator = Orchestrator(stage_manager=manager)

    session = manager.create_session(
        scenario=scenario,
        user_input=stage_inputs["stage_1"],
    )
    for stage_id in prior_stages:
        response = orchestrator.run_current_stage(
            session.session_id,
            user_input=stage_inputs[stage_id],
            context={},
        )
        if response.stage_id != stage_id:
            raise RuntimeError(
                f"stage drift: expected {stage_id}, got {response.stage_id}"
            )
        orchestrator.approve_current_stage(session.session_id)

    # stages_4 already ends with stage_4 — use the normal final report path
    if prior_stages == STAGE_IDS:
        bundle = orchestrator.build_final_report(session.session_id)
        return bundle.model_dump(mode="json")

    # For stages_1/2/3: run output_layer directly via graph_runner (bypasses
    # session advancement — the session pointer still points to the next
    # unrun stage, but output_layer is an eval-only synthesis step)
    session_state = manager.get_session(session.session_id)
    output = orchestrator.graph_runner.run(
        AgentGraphInput(
            session=session_state,
            stage_id="output_layer",
            user_input=stage_inputs["stage_1"],
            context={},
            citations=orchestrator._citations(scenario, "output_layer"),
            approved_state=orchestrator._approved_state(session_state),
            proposal_state=orchestrator._proposal_state(session_state),
            evidence_state=orchestrator._evidence_state(session_state, {}),
            collected_risks=orchestrator._collected_risks(session_state),
        )
    )
    bundle = FinalReportBundle.model_validate(
        {
            "planner_report": output.planner_view,
            "engineer_report": output.engineer_view,
            "prd_report": output.prd_packet,
            "prd_quality": output.prd_quality,
            "decision_log": output.decision_points,
            "citations": [c.model_dump(mode="json") for c in output.citations],
            "risks": [r.model_dump(mode="json") for r in output.risks],
        }
    )
    return bundle.model_dump(mode="json")


_SECTION_LABELS = [
    ("prd_report", "기획서 본문"),
    ("engineer_report", "개발 인계 보강"),
    ("risks", "리스크"),
    ("decision_log", "의사결정 기록"),
    ("citations", "참고 자료"),
]
_SKIP_KEYS = {"prd_quality", "metadata"}
# The planner view restates the PRD body and the engineer view overlaps it on
# data/constraints, so rendering them whole makes the judged document repeat
# the same guardrails in paraphrased form (penalty P1). Keep only the engineer
# keys that add content the PRD body does not carry.
_ENGINEER_KEEP_KEYS = {
    "implementation_order",
    "verification_plan",
    "required_tech_blocks",
}


_DEDUPE_MIN_CHARS = 12


def render_report_text(bundle: Dict[str, Any]) -> str:
    """Render the final report bundle as plain text.

    The bundle carries the same statements (e.g. guardrails) in several views
    (PRD body, planner view, engineer view). Long sentences are emitted only
    on first occurrence so the judged document does not repeat itself; the raw
    bundle JSON keeps the full content.
    """
    lines: List[str] = []
    seen: set[str] = set()
    for key, label in _SECTION_LABELS:
        value = bundle.get(key)
        if key == "engineer_report" and isinstance(value, dict):
            value = {k: v for k, v in value.items() if k in _ENGINEER_KEEP_KEYS}
        if not value:
            continue
        section_lines: List[str] = []
        _render_value(value, section_lines, indent=0, seen=seen)
        if not section_lines:
            continue
        lines.append(f"## {label}")
        lines.extend(section_lines)
        lines.append("")
    return "\n".join(lines).strip()


def _is_duplicate(payload: Any, seen: set[str]) -> bool:
    text = str(payload).strip()
    if len(text) < _DEDUPE_MIN_CHARS:
        return False
    if text in seen:
        return True
    seen.add(text)
    return False


def _render_value(value: Any, lines: List[str], indent: int, seen: set[str]) -> None:
    pad = "  " * indent
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _SKIP_KEYS or child in (None, "", [], {}):
                continue
            if isinstance(child, (dict, list)):
                child_lines: List[str] = []
                _render_value(child, child_lines, indent + 1, seen)
                if child_lines:
                    lines.append(f"{pad}{key}:")
                    lines.extend(child_lines)
            elif not _is_duplicate(child, seen):
                lines.append(f"{pad}{key}: {child}")
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                child_lines = []
                _render_value(child, child_lines, indent + 1, seen)
                if child_lines:
                    lines.append(f"{pad}-")
                    lines.extend(child_lines)
            elif not _is_duplicate(child, seen):
                lines.append(f"{pad}- {child}")
    else:
        if not _is_duplicate(value, seen):
            lines.append(f"{pad}{value}")


# ---------------------------------------------------------------------------
# Judge call
# ---------------------------------------------------------------------------


def judge_output_schema() -> Dict[str, Any]:
    grade_object = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "grade": {"type": "string", "enum": ["pass", "partial", "fail", "na"]},
            "evidence": {"type": "string"},
            "missing": {"type": "string"},
        },
        "required": ["grade", "evidence", "missing"],
    }
    penalty_array = {
        "type": "array",
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "code": {"type": "string", "enum": list(PENALTY_RULES)},
                "evidence": {"type": "string"},
            },
            "required": ["code", "evidence"],
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "item_id": {"type": "string", "enum": ALL_ITEM_IDS},
                        "doc1": grade_object,
                        "doc2": grade_object,
                    },
                    "required": ["item_id", "doc1", "doc2"],
                },
            },
            "penalties": {
                "type": "object",
                "additionalProperties": False,
                "properties": {"doc1": penalty_array, "doc2": penalty_array},
                "required": ["doc1", "doc2"],
            },
            "overall_verdict": {
                "type": "string",
                "enum": ["doc1", "doc2", "tie"],
            },
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        },
        "required": ["items", "penalties", "overall_verdict", "confidence"],
    }


def checklist_body() -> str:
    """Sections 3-5 of the checklist doc are the judge's rubric."""
    text = CHECKLIST_PATH.read_text(encoding="utf-8")
    start = text.index("## 3. 채점 규칙")
    end = text.index("## 6. 판정자 출력 형식")
    return text[start:end].strip()


def build_judge_prompt(initial_input: str, doc1: str, doc2: str) -> str:
    return "\n\n".join(
        [
            "당신은 서비스 기획서 품질을 심사하는 전문 심사위원입니다.",
            "같은 요청에서 출발한 두 개의 기획서(문서1, 문서2)를 평가합니다.",
            f"[원 요청]\n{initial_input}",
            f"[문서1]\n{doc1}",
            f"[문서2]\n{doc2}",
            "\n".join(
                [
                    "평가 규칙:",
                    "- 길이는 품질이 아닙니다. 같은 내용이면 더 짧은 문서가 우수합니다.",
                    "- 섹션 구조나 용어가 아니라, 필요한 내용이 존재하고 구체적인지를 "
                    "평가합니다.",
                    "- 항목마다 pass/partial/fail/na 중 하나를 부여합니다. 각 항목에 "
                    "적힌 기준을 그대로 적용하고, 기준에 수치가 있으면 세어서 판정합니다.",
                    "- pass와 partial에는 해당 문서의 문장을 그대로 인용한 근거가 "
                    "필수입니다. 인용할 문장을 찾지 못하면 fail입니다.",
                    "- na는 항목 정의에 N/A 조건이 명시된 경우(D5-4, D8-1)에만 "
                    "허용됩니다.",
                    "- 점수 계산은 하지 않아도 됩니다. 당신의 임무는 32개 항목 전부에 "
                    "대한 grade와 인용입니다.",
                    "- 웹 검색이나 외부 조사는 하지 마세요. 두 문서와 원 요청만 보고 "
                    "판정합니다.",
                ]
            ),
            "다음 체크리스트의 32개 항목(D1-1 ~ D8-4)을 두 문서 각각에 대해 판정하고, "
            "감점 항목(P1~P4)을 점검한 뒤, 출력 스키마에 맞는 JSON으로만 답하십시오.",
            checklist_body(),
        ]
    )


def run_judge(
    initial_input: str,
    doc1: str,
    doc2: str,
    judge_model: Optional[str],
) -> Dict[str, Any]:
    from app.backend.integrations.codex_client import CodexClient

    client = CodexClient(runtime_config=_make_runtime_config(), cwd=ROOT_DIR)
    prompt = build_judge_prompt(initial_input, doc1, doc2)
    with tempfile.TemporaryDirectory(prefix="milemate-judge-") as tmp_dir:
        schema_path = Path(tmp_dir) / "judge_schema.json"
        output_path = Path(tmp_dir) / "judge_output.json"
        schema_path.write_text(
            json.dumps(judge_output_schema(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        command = client.build_cli_command(
            output_path=str(output_path),
            schema_path=str(schema_path),
            model=judge_model,
        )
        client._run_command(command=command, prompt=prompt)
        return json.loads(output_path.read_text(encoding="utf-8"))


def validate_judgment(judgment: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    seen = [item["item_id"] for item in judgment.get("items", [])]
    missing = [item_id for item_id in ALL_ITEM_IDS if item_id not in seen]
    duplicated = sorted({item_id for item_id in seen if seen.count(item_id) > 1})
    if missing:
        warnings.append(f"missing items: {missing}")
    if duplicated:
        warnings.append(f"duplicated items: {duplicated}")
    for item in judgment.get("items", []):
        for doc_key in ("doc1", "doc2"):
            entry = item[doc_key]
            if entry["grade"] == "na" and item["item_id"] not in NA_ALLOWED_ITEMS:
                warnings.append(
                    f"invalid na on {item['item_id']}/{doc_key} (treated as fail)"
                )
            if entry["grade"] in {"pass", "partial"} and not entry["evidence"].strip():
                warnings.append(
                    f"{item['item_id']}/{doc_key}: {entry['grade']} without evidence"
                )
    return warnings


def score_judgment(judgment: Dict[str, Any]) -> Dict[str, Any]:
    grades_1 = {item["item_id"]: item["doc1"]["grade"] for item in judgment["items"]}
    grades_2 = {item["item_id"]: item["doc2"]["grade"] for item in judgment["items"]}
    penalties_1 = [entry["code"] for entry in judgment["penalties"]["doc1"]]
    penalties_2 = [entry["code"] for entry in judgment["penalties"]["doc2"]]
    doc1 = document_scores(grades_1, penalties_1)
    doc2 = document_scores(grades_2, penalties_2)
    dim_verdicts = {
        dim: verdict_from_scores(doc1["dimensions"][dim], doc2["dimensions"][dim])
        for dim in DIMENSION_ITEMS
    }
    return {
        "doc1": doc1,
        "doc2": doc2,
        "dimension_verdicts": dim_verdicts,
        "overall_verdict": verdict_from_scores(doc1["total"], doc2["total"]),
        "judge_reported_verdict": judgment["overall_verdict"],
        "confidence": judgment["confidence"],
    }


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def sign_test_p(wins: int, losses: int) -> float:
    """Exact two-sided binomial sign test, ties excluded."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = max(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / (2**n)
    return min(1.0, 2 * tail)


def bootstrap_ci(
    values: List[float],
    iterations: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    means = sorted(
        sum(rng.choices(values, k=len(values))) / len(values)
        for _ in range(iterations)
    )
    lower = means[int((alpha / 2) * iterations)]
    upper = means[min(iterations - 1, int((1 - alpha / 2) * iterations))]
    return (round(lower, 3), round(upper, 3))


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def step_generate(
    run_dir: Path,
    scenarios: List[str],
    seeds: int,
    parity: bool,
    ablation_prior_stages: Optional[List[str]] = None,
) -> None:
    """Generate A/B pairs.

    ablation_prior_stages: if set, B is generated with generate_proposed_ablation
    using those stages + output_layer (or all stages for stages_4). If None,
    B uses the standard 4-stage generate_proposed.
    """
    initial_inputs = load_initial_inputs()
    stage_requests = load_stage_requests()
    for scenario in scenarios:
        initial_input = initial_inputs.get(scenario, "")
        if not initial_input:
            print(f"[generate] skip {scenario}: no demo initial_input")
            continue
        stage_inputs = stage_inputs_for(scenario, initial_input, stage_requests)
        extra = [stage_inputs[s] for s in STAGE_IDS[1:]] if parity else []
        for seed in range(1, seeds + 1):
            pair_dir = run_dir / "generations" / scenario / f"seed{seed}"
            a_path = pair_dir / "A.md"
            b_path = pair_dir / "B.md"
            meta_path = pair_dir / "meta.json"
            if a_path.exists() and b_path.exists():
                print(f"[generate] skip {scenario}/seed{seed} (exists)")
                continue
            pair_dir.mkdir(parents=True, exist_ok=True)
            started = time.time()
            if not a_path.exists():
                print(f"[generate] {scenario}/seed{seed} condition A ...")
                a_path.write_text(
                    generate_baseline(initial_input, extra), encoding="utf-8"
                )
            if not b_path.exists():
                if ablation_prior_stages is not None:
                    n = len(ablation_prior_stages)
                    label = f"{n} stage(s) + output_layer" if n < 4 else "4 stages"
                    print(f"[generate] {scenario}/seed{seed} condition B ({label}) ...")
                    bundle = generate_proposed_ablation(
                        scenario, stage_inputs, ablation_prior_stages
                    )
                else:
                    print(f"[generate] {scenario}/seed{seed} condition B (4 stages) ...")
                    bundle = generate_proposed(scenario, stage_inputs)
                _write_json(pair_dir / "B_bundle.json", bundle)
                b_path.write_text(render_report_text(bundle), encoding="utf-8")
            _write_json(
                meta_path,
                {
                    "scenario": scenario,
                    "seed": seed,
                    "parity": parity,
                    "initial_input": initial_input,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "elapsed_seconds": round(time.time() - started, 1),
                    "model_id": _RUNTIME_OVERRIDE.get("model_id", ""),
                    "reasoning_effort": _RUNTIME_OVERRIDE.get("reasoning_effort", ""),
                    "ablation_prior_stages": ablation_prior_stages,
                },
            )


def step_judge(
    run_dir: Path,
    judge_model: Optional[str],
    orders: List[str],
) -> None:
    generations = sorted((run_dir / "generations").glob("*/seed*/meta.json"))
    if not generations:
        raise SystemExit("no generations found — run `generate` first")
    for meta_path in generations:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pair_dir = meta_path.parent
        scenario, seed = meta["scenario"], meta["seed"]
        doc_a = prepare_for_judging((pair_dir / "A.md").read_text(encoding="utf-8"))
        doc_b = prepare_for_judging((pair_dir / "B.md").read_text(encoding="utf-8"))
        masked_dir = run_dir / "masked" / scenario / f"seed{seed}"
        masked_dir.mkdir(parents=True, exist_ok=True)
        (masked_dir / "A.txt").write_text(doc_a, encoding="utf-8")
        (masked_dir / "B.txt").write_text(doc_b, encoding="utf-8")
        for order in orders:
            out_path = run_dir / "judgments" / f"{scenario}_seed{seed}_{order}.json"
            if out_path.exists():
                print(f"[judge] skip {scenario}/seed{seed}/{order} (exists)")
                continue
            doc1, doc2 = (doc_a, doc_b) if order == "AB" else (doc_b, doc_a)
            print(f"[judge] {scenario}/seed{seed} order={order} ...")
            judgment = run_judge(meta["initial_input"], doc1, doc2, judge_model)
            warnings = validate_judgment(judgment)
            for warning in warnings:
                print(f"  [warn] {warning}")
            _write_json(
                out_path,
                {
                    "scenario": scenario,
                    "seed": seed,
                    "order": order,
                    "judge_model": judge_model or "(cli default)",
                    "judged_at": datetime.now(timezone.utc).isoformat(),
                    "validation_warnings": warnings,
                    "judgment": judgment,
                },
            )


def step_aggregate(run_dir: Path) -> None:
    judgment_paths = sorted((run_dir / "judgments").glob("*.json"))
    if not judgment_paths:
        raise SystemExit("no judgments found — run `judge` first")

    records: List[Dict[str, Any]] = []
    for path in judgment_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        scored = score_judgment(payload["judgment"])
        order = payload["order"]
        by_condition = {
            ("A" if order == "AB" else "B"): scored["doc1"],
            ("B" if order == "AB" else "A"): scored["doc2"],
        }
        records.append(
            {
                "scenario": payload["scenario"],
                "seed": payload["seed"],
                "order": order,
                "confidence": scored["confidence"],
                "warnings": payload.get("validation_warnings", []),
                "scores": by_condition,
                "dimension_verdicts": {
                    dim: doc_verdict_to_condition(verdict, order)
                    for dim, verdict in scored["dimension_verdicts"].items()
                },
                "overall_verdict": doc_verdict_to_condition(
                    scored["overall_verdict"], order
                ),
                "judgment": payload["judgment"],
            }
        )

    scored_path = run_dir / "judgments_scored.jsonl"
    with open(scored_path, "w", encoding="utf-8") as f:
        for record in records:
            slim = {k: v for k, v in record.items() if k != "judgment"}
            f.write(json.dumps(slim, ensure_ascii=False) + "\n")

    # --- pair-level verdicts (multiple orders, when present, must agree) ---
    pairs: Dict[Tuple[str, int], Dict[str, Dict[str, Any]]] = {}
    for record in records:
        pairs.setdefault((record["scenario"], record["seed"]), {})[
            record["order"]
        ] = record

    overall = {"A": 0, "B": 0, "tie": 0}
    dim_tallies = {dim: {"A": 0, "B": 0, "tie": 0} for dim in DIMENSION_ITEMS}
    total_diffs: List[float] = []
    pair_rows: List[str] = []
    orders_seen: set[str] = set()
    for (scenario, seed), by_order in sorted(pairs.items()):
        judgments = list(by_order.values())
        orders_seen.update(by_order)
        verdict = combine_verdicts([r["overall_verdict"] for r in judgments])
        overall[verdict] += 1
        for dim in DIMENSION_ITEMS:
            dim_tallies[dim][
                combine_verdicts([r["dimension_verdicts"][dim] for r in judgments])
            ] += 1
        diff = sum(
            r["scores"]["B"]["total"] - r["scores"]["A"]["total"] for r in judgments
        ) / len(judgments)
        total_diffs.append(diff)
        pair_rows.append(f"| {scenario} | {seed} | {verdict} | {diff:+.2f} |")

    # --- item-level pass rates ---
    item_points: Dict[str, Dict[str, List[float]]] = {
        item_id: {"A": [], "B": []} for item_id in ALL_ITEM_IDS
    }
    for record in records:
        order = record["order"]
        for item in record["judgment"]["items"]:
            for doc_key, condition in (
                ("doc1", "A" if order == "AB" else "B"),
                ("doc2", "B" if order == "AB" else "A"),
            ):
                grade = item[doc_key]["grade"]
                if grade == "na" and item["item_id"] in NA_ALLOWED_ITEMS:
                    continue
                item_points[item["item_id"]][condition].append(
                    GRADE_POINTS.get(grade, 0.0)
                )

    def _mean(values: List[float]) -> float:
        return round(sum(values) / len(values), 3) if values else 0.0

    p_value = sign_test_p(overall["B"], overall["A"])
    ci_low, ci_high = bootstrap_ci(total_diffs)
    mean_diff = _mean(total_diffs)

    verdict_rule = (
        "복수 순서 전원 일치 기준" if len(orders_seen) > 1 else "단일 순서 판정"
    )
    lines = [
        "# 평가 결과 요약",
        "",
        f"- 생성 쌍: {len(pairs)} (시나리오×seed), 판정 호출: {len(records)}, "
        f"판정 순서: {', '.join(sorted(orders_seen))} (doc1=B는 BA)",
        f"- 종합 판정 ({verdict_rule}): B 승 {overall['B']} / "
        f"A 승 {overall['A']} / tie {overall['tie']}",
        f"- sign test p-value (tie 제외): {p_value:.4f}",
        f"- 총점 차이 평균 (B-A): {mean_diff:+.3f}, 부트스트랩 95% CI "
        f"[{ci_low:+.3f}, {ci_high:+.3f}]",
        "",
        f"## 차원별 승률 ({verdict_rule})",
        "",
        "| 차원 | B 승 | A 승 | tie |",
        "|---|---|---|---|",
    ]
    for dim, tally in dim_tallies.items():
        lines.append(f"| {dim} | {tally['B']} | {tally['A']} | {tally['tie']} |")
    lines += [
        "",
        "## 항목별 평균 획득 점수 (pass=1 / partial=0.5 / fail=0)",
        "",
        "| 항목 | A | B | 차이 (B-A) |",
        "|---|---|---|---|",
    ]
    for item_id in ALL_ITEM_IDS:
        mean_a = _mean(item_points[item_id]["A"])
        mean_b = _mean(item_points[item_id]["B"])
        lines.append(
            f"| {item_id} | {mean_a:.2f} | {mean_b:.2f} | {mean_b - mean_a:+.2f} |"
        )
    lines += [
        "",
        "## 쌍별 결과",
        "",
        "| 시나리오 | seed | 판정 | 총점 차이 (B-A) |",
        "|---|---|---|---|",
        *pair_rows,
        "",
        "## 검토 필요",
        "",
    ]
    review_targets = [
        f"- {r['scenario']}/seed{r['seed']}/{r['order']}: "
        f"confidence={r['confidence']}, warnings={len(r['warnings'])}"
        for r in records
        if r["confidence"] == "low" or r["warnings"]
    ]
    lines += review_targets or ["- 없음"]

    summary_path = run_dir / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[aggregate] wrote {summary_path}")
    print(f"[aggregate] wrote {scored_path}")
    print(
        f"[aggregate] overall: B {overall['B']} / A {overall['A']} / "
        f"tie {overall['tie']}, mean diff {mean_diff:+.3f}, p={p_value:.4f}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--run", default=None, help="run id (default: timestamp)")
        p.add_argument("--model", default=None, help="override model_id (e.g. gpt-5.5)")
        p.add_argument(
            "--reasoning-effort",
            default=None,
            dest="reasoning_effort",
            help="override reasoning_effort for all codex calls (low/medium/high/xhigh)",
        )

    p_gen = sub.add_parser("generate", help="generate A/B report pairs")
    add_common(p_gen)
    p_gen.add_argument("--scenarios", default="all", help="comma list or 'all'")
    p_gen.add_argument("--seeds", type=int, default=3)
    p_gen.add_argument(
        "--no-parity",
        action="store_true",
        help="give condition A only the initial input (omit stage requests)",
    )
    p_gen.add_argument(
        "--ablation-stages",
        default=None,
        dest="ablation_stages",
        help=(
            "ablation condition key (stages_1/stages_2/stages_3/stages_4). "
            "B is generated with N prior stages + output_layer synthesis."
        ),
    )

    p_judge = sub.add_parser(
        "judge", help="run judge calls (default: single order, ours first)"
    )
    add_common(p_judge)
    p_judge.add_argument("--judge-model", default=None)
    p_judge.add_argument(
        "--orders",
        default="BA",
        help="comma list of presentation orders; BA = proposed(B) first "
        "(default), pass 'BA,AB' for swapped-order double judging",
    )

    p_agg = sub.add_parser("aggregate", help="recompute scores and summarize")
    add_common(p_agg)

    p_all = sub.add_parser("all", help="generate + judge + aggregate")
    add_common(p_all)
    p_all.add_argument("--scenarios", default="all")
    p_all.add_argument("--seeds", type=int, default=3)
    p_all.add_argument("--no-parity", action="store_true")
    p_all.add_argument("--judge-model", default=None)
    p_all.add_argument("--orders", default="BA")

    args = parser.parse_args(argv)
    run_id = args.run or datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RESULTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run] {run_dir}")

    global _RUNTIME_OVERRIDE
    _RUNTIME_OVERRIDE = {}
    if getattr(args, "model", None):
        _RUNTIME_OVERRIDE["model_id"] = args.model
    if getattr(args, "reasoning_effort", None):
        _RUNTIME_OVERRIDE["reasoning_effort"] = args.reasoning_effort
    if _RUNTIME_OVERRIDE:
        _write_json(
            run_dir / "run_config.json",
            {
                "run_id": run_id,
                **_RUNTIME_OVERRIDE,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        print(f"[run] model_override={_RUNTIME_OVERRIDE}")

    if args.command in {"generate", "all"}:
        scenarios = (
            list_scenarios()
            if args.scenarios == "all"
            else [s.strip() for s in args.scenarios.split(",") if s.strip()]
        )
        ablation_key = getattr(args, "ablation_stages", None)
        ablation_prior: Optional[List[str]] = None
        if ablation_key:
            if ablation_key not in ABLATION_STAGE_SETS:
                raise SystemExit(
                    f"unknown ablation key {ablation_key!r}; "
                    f"choose from {list(ABLATION_STAGE_SETS)}"
                )
            ablation_prior = ABLATION_STAGE_SETS[ablation_key]
        step_generate(
            run_dir, scenarios, args.seeds,
            parity=not args.no_parity,
            ablation_prior_stages=ablation_prior,
        )
    if args.command in {"judge", "all"}:
        orders = [o.strip().upper() for o in args.orders.split(",") if o.strip()]
        invalid = [o for o in orders if o not in {"AB", "BA"}]
        if invalid:
            raise SystemExit(f"invalid orders: {invalid}")
        step_judge(run_dir, args.judge_model, orders)
    if args.command in {"aggregate", "all"}:
        step_aggregate(run_dir)


if __name__ == "__main__":
    main()
