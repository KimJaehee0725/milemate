#!/usr/bin/env python3
"""Run the A/B evaluation pipeline across stage-count ablation conditions.

Conditions (B is generated with N prior stages + output_layer synthesis):
  stages_1  : stage_1 → output_layer
  stages_2  : stage_1 → stage_2 → output_layer
  stages_3  : stage_1 → stage_2 → stage_3 → output_layer
  stages_4  : stage_1 → stage_2 → stage_3 → stage_4  (full pipeline, no output_layer)

All 4 conditions run in parallel threads; globally at most --max-concurrent
codex processes run at any time (semaphore shared across all condition threads).

Usage:
    uv run python eval/run_ablation_stages.py

Options:
    --model          Model ID passed to codex -m  (default: gpt-5.5)
    --effort         Reasoning effort for all conditions (default: medium)
    --conditions     Comma-separated condition list (default: stages_1,stages_2,stages_3,stages_4)
    --seeds          Seeds per scenario             (default: 3)
    --run-prefix     Prefix for run directory IDs  (default: gpt55)
    --date-tag       Override date tag YYYYMMDD    (default: today)
    --retry          Max retry rounds per condition (default: 2)
    --max-concurrent Global max concurrent codex processes (default: 4)

Resume: rerun the same command — completed pairs/judgments are skipped automatically.
Progress is tracked in eval/results/run_ablation_stages_progress.json.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
PIPELINE = ROOT_DIR / "eval" / "pipeline.py"
RESULTS_DIR = ROOT_DIR / "eval" / "results"

SCENARIOS = [
    "dispatch_recommendation",
    "eta_prediction",
    "failed_delivery_risk",
    "rider_onboarding_dropout",
    "return_pickup_flow",
    "checkout_fee_transparency",
    "merchant_prep_visibility",
    "cs_repeat_inquiry_triage",
]
DIMS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"]

_print_lock = threading.Lock()
_global_slots: threading.Semaphore  # set in main()


# ---------------------------------------------------------------------------
# Thread-safe logging
# ---------------------------------------------------------------------------


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def log(msg: str, condition: str = "") -> None:
    prefix = f"[{condition}]" if condition else ""
    with _print_lock:
        print(f"[{_ts()}]{prefix} {msg}", flush=True)


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def _uv_python(*args: str) -> List[str]:
    return ["uv", "run", "python", *args]


def _run_one_scenario(
    scenario: str,
    run_id: str,
    model: str,
    effort: str,
    ablation_key: str,
    seeds: int,
    log_dir: Path,
    condition: str,
) -> Tuple[str, bool]:
    """Acquire a global slot, run generate for one scenario, release slot."""
    log_path = log_dir / f"gen_{scenario}.log"
    cmd = _uv_python(
        str(PIPELINE),
        "generate",
        "--run", run_id,
        "--scenarios", scenario,
        "--seeds", str(seeds),
        "--model", model,
        "--reasoning-effort", effort,
        "--ablation-stages", ablation_key,
    )
    _global_slots.acquire()
    try:
        log(f"  spawned generate {scenario}", condition)
        with open(log_path, "a") as fh:
            rc = subprocess.run(
                cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(ROOT_DIR)
            ).returncode
    finally:
        _global_slots.release()

    if rc != 0:
        log(f"  FAILED generate {scenario}  rc={rc}  log={log_path.name}", condition)
        return scenario, False
    log(f"  done   generate {scenario}", condition)
    return scenario, True


def run_generate_parallel(
    run_id: str,
    model: str,
    effort: str,
    ablation_key: str,
    seeds: int,
    log_dir: Path,
    condition: str,
) -> List[str]:
    """Spawn all scenarios concurrently, respecting the global slot semaphore."""
    log_dir.mkdir(parents=True, exist_ok=True)
    threads = []
    results: Dict[str, bool] = {}
    lock = threading.Lock()

    def _worker(scenario: str) -> None:
        _, ok = _run_one_scenario(
            scenario, run_id, model, effort, ablation_key, seeds, log_dir, condition
        )
        with lock:
            results[scenario] = ok

    for scenario in SCENARIOS:
        t = threading.Thread(target=_worker, args=(scenario,), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return [s for s, ok in results.items() if not ok]


def run_pipeline_step(
    step: str,
    run_id: str,
    model: str,
    effort: str,
    log_path: Path,
    condition: str,
) -> int:
    cmd = _uv_python(
        str(PIPELINE),
        step,
        "--run", run_id,
        "--model", model,
        "--reasoning-effort", effort,
    )
    log(f"  running {step} ...", condition)
    with open(log_path, "w") as fh:
        rc = subprocess.run(
            cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(ROOT_DIR)
        ).returncode
    status = "done" if rc == 0 else f"FAILED rc={rc}"
    log(f"  {step} {status}  log={log_path.name}", condition)
    return rc


# ---------------------------------------------------------------------------
# Per-condition orchestration
# ---------------------------------------------------------------------------


def condition_complete(run_dir: Path) -> bool:
    return (run_dir / "summary.md").exists()


def run_condition(
    condition: str,
    run_id: str,
    model: str,
    effort: str,
    seeds: int,
    max_retry: int,
    results: Dict[str, bool],
    lock: threading.Lock,
    progress: Dict[str, Any],
) -> None:
    """Run generate → judge → aggregate for one ablation condition."""
    run_dir = RESULTS_DIR / run_id
    log_dir = run_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log(f"{'='*50}", condition)
    log(f"CONDITION={condition}  run_id={run_id}", condition)
    log(f"{'='*50}", condition)

    if condition_complete(run_dir):
        log("already complete (summary.md exists) — skipping", condition)
        with lock:
            results[condition] = True
            progress[f"condition_{condition}_done"] = True
        return

    # ---- generate (parallel scenarios, with retry) -------------------------
    for attempt in range(1, max_retry + 1):
        log(f"generate attempt {attempt}/{max_retry}", condition)
        failed = run_generate_parallel(
            run_id, model, effort, condition, seeds, log_dir, condition
        )
        if not failed:
            log("all generates complete", condition)
            break
        log(
            f"{len(failed)} scenario(s) still failed: {failed} — retry in 30 s",
            condition,
        )
        time.sleep(30)
    else:
        log(
            f"generate incomplete after {max_retry} retries — proceeding anyway",
            condition,
        )

    # ---- judge ---------------------------------------------------------------
    rc_judge = run_pipeline_step(
        "judge", run_id, model, effort, log_dir / "judge.log", condition
    )
    if rc_judge != 0:
        log("judge step failed — skipping aggregate", condition)
        with lock:
            results[condition] = False
            progress[f"condition_{condition}_done"] = False
        return

    # ---- aggregate -----------------------------------------------------------
    rc_agg = run_pipeline_step(
        "aggregate", run_id, model, effort, log_dir / "aggregate.log", condition
    )
    ok = rc_agg == 0

    with lock:
        results[condition] = ok
        progress[f"condition_{condition}_done"] = ok
    log(f"condition {condition} {'OK' if ok else 'FAILED'}", condition)


# ---------------------------------------------------------------------------
# Combined cross-condition summary
# ---------------------------------------------------------------------------


def _parse_summary_stats(summary_path: Path) -> Dict[str, Any]:
    text = summary_path.read_text(encoding="utf-8")
    out: Dict[str, Any] = {}
    m = re.search(r"B 승 (\d+) / A 승 (\d+) / tie (\d+)", text)
    if m:
        out["b_wins"] = int(m.group(1))
        out["a_wins"] = int(m.group(2))
        out["ties"] = int(m.group(3))
    m = re.search(r"p-value[^:]*:\s*([\d.]+)", text)
    if m:
        out["p_value"] = m.group(1)
    m = re.search(r"총점 차이 평균 \(B-A\):\s*([+\-][\d.]+)", text)
    if m:
        out["mean_diff"] = m.group(1)
    m = re.search(r"부트스트랩 95% CI \[([+\-][\d.]+), ([+\-][\d.]+)\]", text)
    if m:
        out["ci_low"], out["ci_high"] = m.group(1), m.group(2)
    return out


def _dim_win_rates(scored_path: Path) -> Dict[str, str]:
    tallies: Dict[str, Dict[str, int]] = {d: {"B": 0, "total": 0} for d in DIMS}
    with open(scored_path, encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            for dim in DIMS:
                v = record.get("dimension_verdicts", {}).get(dim)
                tallies[dim]["total"] += 1
                if v == "B":
                    tallies[dim]["B"] += 1
    return {
        dim: (
            f"{tallies[dim]['B']/tallies[dim]['total']*100:.0f}%"
            if tallies[dim]["total"]
            else "-"
        )
        for dim in DIMS
    }


def build_combined_summary(
    condition_run_pairs: List[Tuple[str, str]],
    model: str,
    effort: str,
) -> Path:
    sys.path.insert(0, str(ROOT_DIR / "eval"))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "eval_pipeline", ROOT_DIR / "eval" / "pipeline.py"
        )
        pip = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pip)
        all_item_ids = pip.ALL_ITEM_IDS
        na_allowed = pip.NA_ALLOWED_ITEMS
        grade_points = pip.GRADE_POINTS
    except Exception:
        all_item_ids = []
        na_allowed = set()
        grade_points = {}

    conditions = [c for c, _ in condition_run_pairs]
    col_sep = "|---|" * len(conditions)

    lines = [
        "# Stage Ablation A/B 평가 비교",
        "",
        f"- 모델: **{model}**  reasoning_effort: **{effort}**",
        f"- 생성: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "- 판정 순서: BA 고정 (문서1=B=제안, 문서2=A=baseline) — 위치 편향 한계 있음",
        "- B 조건: stages_1=1단계+output_layer, stages_2=2단계+output_layer, "
        "stages_3=3단계+output_layer, stages_4=4단계(full pipeline)",
        "",
        "## 종합 결과",
        "",
        f"| 지표 | {' | '.join(conditions)} |",
        f"| --- | {col_sep}",
    ]

    stats = {
        c: (
            _parse_summary_stats(RESULTS_DIR / r / "summary.md")
            if (RESULTS_DIR / r / "summary.md").exists()
            else {}
        )
        for c, r in condition_run_pairs
    }

    for key, label in [
        ("b_wins",    "B 승"),
        ("a_wins",    "A 승"),
        ("ties",      "tie"),
        ("mean_diff", "평균 점수 차 (B-A)"),
        ("p_value",   "sign test p-value"),
        ("ci_low",    "95% CI 하한"),
        ("ci_high",   "95% CI 상한"),
    ]:
        vals = " | ".join(str(stats[c].get(key, "-")) for c in conditions)
        lines.append(f"| {label} | {vals} |")

    lines += [
        "",
        "## 차원별 B 승률",
        "",
        f"| 차원 | {' | '.join(conditions)} |",
        f"| --- | {col_sep}",
    ]
    dim_data = {
        c: (
            _dim_win_rates(RESULTS_DIR / r / "judgments_scored.jsonl")
            if (RESULTS_DIR / r / "judgments_scored.jsonl").exists()
            else {}
        )
        for c, r in condition_run_pairs
    }
    for dim in DIMS:
        vals = " | ".join(dim_data[c].get(dim, "-") for c in conditions)
        lines.append(f"| {dim} | {vals} |")

    if all_item_ids:
        lines += [
            "",
            "## 항목별 B 평균 점수",
            "",
            f"| 항목 | A (공통) | {' | '.join(f'B({c})' for c in conditions)} |",
            f"| --- | --- | {col_sep}",
        ]
        item_data = {
            c: (
                _item_mean_scores(
                    RESULTS_DIR / r / "judgments_scored.jsonl",
                    all_item_ids, na_allowed, grade_points,
                )
                if (RESULTS_DIR / r / "judgments_scored.jsonl").exists()
                else {}
            )
            for c, r in condition_run_pairs
        }
        first_c = conditions[0]
        for iid in all_item_ids:
            a_score = item_data[first_c].get(iid, {}).get("A", "-")
            b_vals = " | ".join(
                str(item_data[c].get(iid, {}).get("B", "-")) for c in conditions
            )
            lines.append(f"| {iid} | {a_score} | {b_vals} |")

    lines += ["", "## 개별 실행 디렉토리", ""]
    for condition, run_id in condition_run_pairs:
        done = "완료" if (RESULTS_DIR / run_id / "summary.md").exists() else "미완료"
        lines.append(f"- **{condition}**: `eval/results/{run_id}/`  ({done})")

    out_path = RESULTS_DIR / "combined_ablation_summary.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"[combined] wrote {out_path}")
    return out_path


def _item_mean_scores(
    scored_path: Path,
    all_item_ids: List[str],
    na_allowed: set,
    grade_points: Dict[str, float],
) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, Dict[str, List[float]]] = {
        iid: {"A": [], "B": []} for iid in all_item_ids
    }
    # raw judgment files live next to the scored file in a sibling judgments/ dir
    judgments_dir = scored_path.parent / "judgments"
    raw_files = sorted(judgments_dir.glob("*.json")) if judgments_dir.exists() else []
    for jf in raw_files:
        record = json.loads(jf.read_text(encoding="utf-8"))
        order = record.get("order", "BA")
        for item in record.get("judgment", {}).get("items", []):
            iid = item.get("item_id")
            if iid not in buckets:
                continue
            for doc_key, cond in (
                ("doc1", "A" if order == "AB" else "B"),
                ("doc2", "B" if order == "AB" else "A"),
            ):
                grade = item.get(doc_key, {}).get("grade")
                if grade is None:
                    continue
                if grade == "na" and iid in na_allowed:
                    continue
                buckets[iid][cond].append(grade_points.get(grade, 0.0))

    def _m(vals: List[float]) -> float:
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    return {
        iid: {"A": _m(buckets[iid]["A"]), "B": _m(buckets[iid]["B"])}
        for iid in all_item_ids
    }


# ---------------------------------------------------------------------------
# Progress file
# ---------------------------------------------------------------------------


def _progress_path() -> Path:
    return RESULTS_DIR / "run_ablation_stages_progress.json"


def _load_progress() -> Dict[str, Any]:
    p = _progress_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_progress(data: Dict[str, Any]) -> None:
    _progress_path().parent.mkdir(parents=True, exist_ok=True)
    _progress_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--effort", default="medium",
                        help="reasoning_effort used for all conditions (default: medium)")
    parser.add_argument(
        "--conditions",
        default="stages_1,stages_2,stages_3,stages_4",
        help="comma-separated ablation conditions to run",
    )
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--run-prefix", default="gpt55", dest="run_prefix")
    parser.add_argument(
        "--date-tag", default=None, dest="date_tag",
        help="Override date tag in run ID (default: today's date YYYYMMDD)",
    )
    parser.add_argument("--retry", type=int, default=2)
    parser.add_argument(
        "--max-concurrent", type=int, default=4, dest="max_concurrent",
        help="global max concurrent codex generate processes across ALL conditions (default: 4)",
    )
    args = parser.parse_args(argv)

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    date_tag = args.date_tag if args.date_tag else datetime.now().strftime("%Y%m%d")

    condition_run_pairs: List[Tuple[str, str]] = [
        (condition, f"{args.run_prefix}_ablation_{condition}_{date_tag}")
        for condition in conditions
    ]

    progress = _load_progress()
    progress.setdefault("started_at", datetime.now(timezone.utc).isoformat())
    progress.update({
        "model": args.model,
        "effort": args.effort,
        "conditions": conditions,
        "seeds": args.seeds,
        "condition_run_pairs": condition_run_pairs,
    })
    _save_progress(progress)

    global _global_slots
    _global_slots = threading.Semaphore(args.max_concurrent)

    log(f"model={args.model}  effort={args.effort}  conditions={conditions}  seeds={args.seeds}")
    log(f"run IDs: {[r for _, r in condition_run_pairs]}")
    log(f"max concurrent codex processes (global): {args.max_concurrent}")

    results: Dict[str, bool] = {}
    lock = threading.Lock()

    threads = []
    for condition, run_id in condition_run_pairs:
        t = threading.Thread(
            target=run_condition,
            name=f"condition-{condition}",
            kwargs=dict(
                condition=condition,
                run_id=run_id,
                model=args.model,
                effort=args.effort,
                seeds=args.seeds,
                max_retry=args.retry,
                results=results,
                lock=lock,
                progress=progress,
            ),
            daemon=True,
        )
        log(f"started thread for condition={condition}", condition)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    log("all condition threads finished — building combined summary ...")
    out_path = build_combined_summary(condition_run_pairs, args.model, args.effort)
    log(f"combined summary: {out_path}")

    progress["completed_at"] = datetime.now(timezone.utc).isoformat()
    _save_progress(progress)

    log("=" * 60)
    log("ALL DONE")
    for condition, _ in condition_run_pairs:
        status = "OK" if results.get(condition) else "FAILED"
        log(f"  {condition}: {status}")


if __name__ == "__main__":
    main()
