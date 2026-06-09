"""Small deterministic PRD packets for local demos and tests."""

from __future__ import annotations

from typing import Any, Iterable, List

from app.backend.core.config_loader import get_scenario_definition
from app.backend.schemas.common import Citation
from app.backend.schemas.stage import (
    PrdDataRequirement,
    PrdDecisionAgendaItem,
    PrdEventLog,
    PrdImplementationSlice,
    PrdMetric,
    PrdOpenQuestion,
    PrdPacket,
    PrdPersona,
    PrdPolicyRule,
    PrdProblem,
    PrdQualityReport,
    PrdScope,
    PrdScreenSpec,
)
from app.backend.services.scenario_profiles import get_scenario_profile


def ready_prd_quality() -> PrdQualityReport:
    return PrdQualityReport(status="ready", score=100, findings=[], repair_attempted=False)


def _topic_particle(word: str) -> str:
    """Return the Korean topic particle (은/는) for the last character."""
    if not word:
        return "는"
    last = word[-1]
    if "가" <= last <= "힣":
        has_final_consonant = (ord(last) - 0xAC00) % 28 != 0
        return "은" if has_final_consonant else "는"
    return "는"


def build_demo_prd_packet(
    *,
    stage_id: str,
    scenario: str,
    summary: str,
    citations: Iterable[Citation] | None = None,
    user_input: str = "",
    evidence: dict[str, Any] | None = None,
) -> PrdPacket:
    scenario_def = get_scenario_definition(scenario)
    profile = get_scenario_profile(scenario)
    label = scenario_def.display_label if scenario_def else scenario
    data_sources = _core_data(scenario_def, evidence)
    stage_goal = {
        "stage_1": "서비스 문제와 성공 기준을 회의에서 합의할 수 있게 정리",
        "stage_2": "MVP 범위, 화면, 운영 정책을 개발 회의 수준으로 구체화",
        "stage_3": "데이터/운영 리스크와 보류 조건을 점검",
        "stage_4": "최종 추진안과 개발 착수 범위를 보고서 형태로 확정",
    }.get(stage_id, "서비스 기획 산출물 정리")
    note = f" 사용자 요청 반영: {user_input[:160]}" if user_input else ""

    return PrdPacket(
        stage_goal=stage_goal,
        one_page_summary=(
            f"{label}{_topic_particle(label)} {profile['one_page_focus']} {summary}{note}"
        ).strip(),
        problem=PrdProblem(**profile["problem"]),
        personas=[PrdPersona(**persona) for persona in profile["personas"]],
        scope=PrdScope(
            in_scope=list(profile["scope_in"]),
            out_of_scope=list(profile["scope_out"]),
        ),
        screens=[PrdScreenSpec(**profile["screen"])],
        policies=[PrdPolicyRule(**profile["policy"])],
        metrics=[PrdMetric(**metric) for metric in profile["metrics"]],
        data_requirements=_data_requirements(profile, data_sources),
        event_logs=[PrdEventLog(**event) for event in profile["event_logs"]],
        implementation_slices=[PrdImplementationSlice(**profile["impl_slice"])],
        decision_agenda=[PrdDecisionAgendaItem(**profile["decision_agenda"])],
        open_questions=[PrdOpenQuestion(**profile["open_question"])],
        developer_handoff=list(profile["developer_handoff"]),
        evidence_links=list(citations or []),
    )


def _data_requirements(
    profile: dict[str, Any],
    data_sources: List[str],
) -> List[PrdDataRequirement]:
    requirements: List[PrdDataRequirement] = []
    specs = profile["data_requirements"]
    for index, spec in enumerate(specs):
        field_name = data_sources[index] if index < len(data_sources) else spec["source"]
        requirements.append(PrdDataRequirement(field_name=field_name, **spec))
    return requirements


def _core_data(scenario_def: Any, evidence: dict[str, Any] | None) -> List[str]:
    evidence_sources = list((evidence or {}).get("data_sources") or [])
    configured = list(scenario_def.core_data if scenario_def else [])
    values = [*evidence_sources, *configured]
    defaults = ["order_status_event", "courier_location_event", "zone_peak_calendar"]
    merged: List[str] = []
    for value in [*values, *defaults]:
        if value and value not in merged:
            merged.append(str(value))
    return merged[:3]
