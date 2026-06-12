#!/usr/bin/env python3
"""Run the A/B evaluation pipeline across all reasoning effort levels — fully parallel.

Parallelism:
  - Effort level parallelism: all N efforts run simultaneously (threads)
  - Scenario parallelism:     within each effort, 8 generate processes run simultaneously

Total concurrent codex processes: N_efforts × 8_scenarios
  (e.g. 4 efforts → 32 generate processes, then 4 parallel judge streams)

Usage (full run, ~2-3 h with full parallelism):
    uv run python eval/run_all_efforts.py

Options:
    --model        Model ID passed to codex -m  (default: gpt-5.5)
    --efforts      Comma-separated effort list  (default: low,medium,high,xhigh)
    --seeds        Seeds per scenario            (default: 3)
    --run-prefix   Prefix for run directory IDs (default: gpt55)
    --retry        Max retry rounds per effort   (default: 2)

Resume: rerun the same command — completed pairs/judgments are skipped automatically.
Progress is tracked in eval/results/run_all_efforts_progress.json.
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


def log(msg: str, effort: str = "") -> None:
    prefix = f"[{effort}]" if effort else ""
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
    seeds: int,
    log_dir: Path,
) -> Tuple[str, bool]:
    """Acquire a global slot, run generate for one scenario, release slot. Returns (scenario, ok)."""
    log_path = log_dir / f"gen_{scenario}.log"
    cmd = _uv_python(
        str(PIPELINE),
        "generate",
        "--run", run_id,
        "--scenarios", scenario,
        "--seeds", str(seeds),
        "--model", model,
        "--reasoning-effort", effort,
    )
    _global_slots.acquire()
    try:
        log(f"  spawned generate {scenario}", effort)
        with open(log_path, "a") as fh:
            rc = subprocess.run(
                cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(ROOT_DIR)
            ).returncode
    finally:
        _global_slots.release()

    if rc != 0:
        log(f"  FAILED generate {scenario}  rc={rc}  log={log_path.name}", effort)
        return scenario, False
    log(f"  done   generate {scenario}", effort)
    return scenario, True


def run_generate_parallel(
    run_id: str,
    model: str,
    effort: str,
    seeds: int,
    log_dir: Path,
    batch_size: int = 4,  # kept for signature compat, unused (global semaphore controls concurrency)
) -> List[str]:
    """Spawn all scenarios concurrently, respecting the global slot semaphore."""
    log_dir.mkdir(parents=True, exist_ok=True)
    threads = []
    results: Dict[str, bool] = {}
    lock = threading.Lock()

    def _worker(scenario: str) -> None:
        _, ok = _run_one_scenario(scenario, run_id, model, effort, seeds, log_dir)
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
) -> int:
    cmd = _uv_python(
        str(PIPELINE),
        step,
        "--run", run_id,
        "--model", model,
        "--reasoning-effort", effort,
    )
    log(f"  running {step} ...", effort)
    with open(log_path, "w") as fh:
        rc = subprocess.run(
            cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=str(ROOT_DIR)
        ).returncode
    status = "done" if rc == 0 else f"FAILED rc={rc}"
    log(f"  {step} {status}  log={log_path.name}", effort)
    return rc


# ---------------------------------------------------------------------------
# Per-effort orchestration
# ---------------------------------------------------------------------------


def effort_complete(run_dir: Path) -> bool:
    return (run_dir / "summary.md").exists()


def run_effort(
    effort: str,
    run_id: str,
    model: str,
    seeds: int,
    max_retry: int,
    results: Dict[str, bool],
    lock: threading.Lock,
    progress: Dict[str, Any],
    batch_size: int = 4,
) -> None:
    """Run generate → judge → aggregate for one effort level (runs in its own thread)."""
    run_dir = RESULTS_DIR / run_id
    log_dir = run_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log(f"{'='*50}", effort)
    log(f"EFFORT={effort}  run_id={run_id}", effort)
    log(f"{'='*50}", effort)

    if effort_complete(run_dir):
        log("already complete (summary.md exists) — skipping", effort)
        with lock:
            results[effort] = True
            progress[f"effort_{effort}_done"] = True
        return

    # ---- generate (parallel scenarios, with retry) -------------------------
    for attempt in range(1, max_retry + 1):
        log(f"generate attempt {attempt}/{max_retry}", effort)
        failed = run_generate_parallel(run_id, model, effort, seeds, log_dir, batch_size)
        if not failed:
            log("all generates complete", effort)
            break
        log(f"{len(failed)} scenario(s) still failed: {failed} — retry in 30 s", effort)
        time.sleep(30)
    else:
        log(f"generate incomplete after {max_retry} retries — proceeding anyway", effort)

    # ---- judge (sequential within this effort) -----------------------------
    rc_judge = run_pipeline_step(
        "judge", run_id, model, effort, log_dir / "judge.log"
    )
    if rc_judge != 0:
        log("judge step failed — skipping aggregate", effort)
        with lock:
            results[effort] = False
            progress[f"effort_{effort}_done"] = False
        return

    # ---- aggregate ---------------------------------------------------------
    rc_agg = run_pipeline_step(
        "aggregate", run_id, model, effort, log_dir / "aggregate.log"
    )
    ok = rc_agg == 0

    with lock:
        results[effort] = ok
        progress[f"effort_{effort}_done"] = ok
    log(f"effort {effort} {'OK' if ok else 'FAILED'}", effort)


# ---------------------------------------------------------------------------
# Combined cross-effort summary
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
        dim: (f"{tallies[dim]['B']/tallies[dim]['total']*100:.0f}%"
              if tallies[dim]["total"] else "-")
        for dim in DIMS
    }


def _item_mean_scores(
    scored_path: Path,
    all_item_ids: List[str],
    na_allowed: set,
    grade_points: Dict[str, float],
) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, Dict[str, List[float]]] = {
        iid: {"A": [], "B": []} for iid in all_item_ids
    }
    with open(scored_path, encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            order = record["order"]
            for item in record.get("judgment", {}).get("items", []):
                iid = item["item_id"]
                for doc_key, cond in (
                    ("doc1", "A" if order == "AB" else "B"),
                    ("doc2", "B" if order == "AB" else "A"),
                ):
                    grade = item[doc_key]["grade"]
                    if grade == "na" and iid in na_allowed:
                        continue
                    buckets[iid][cond].append(grade_points.get(grade, 0.0))

    def _m(vals: List[float]) -> float:
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    return {iid: {"A": _m(buckets[iid]["A"]), "B": _m(buckets[iid]["B"])}
            for iid in all_item_ids}


def build_combined_summary(
    effort_run_pairs: List[Tuple[str, str]],
    model: str,
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

    efforts = [e for e, _ in effort_run_pairs]
    col_sep = "|---|" * len(efforts)

    lines = [
        "# Reasoning Effort별 A/B 평가 비교",
        "",
        f"- 모델: **{model}**",
        f"- 생성: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "- 판정 순서: BA 고정 (문서1=B=제안, 문서2=A=baseline) — 위치 편향 한계 있음",
        "- 생성/판정 모두 동일 모델·동일 reasoning_effort (effort별 전반적 품질 비교)",
        "",
        "## 종합 결과",
        "",
        f"| 지표 | {' | '.join(efforts)} |",
        f"| --- | {col_sep}",
    ]

    stats = {e: _parse_summary_stats(RESULTS_DIR / r / "summary.md")
             if (RESULTS_DIR / r / "summary.md").exists() else {}
             for e, r in effort_run_pairs}

    for key, label in [
        ("b_wins",    "B 승"),
        ("a_wins",    "A 승"),
        ("ties",      "tie"),
        ("mean_diff", "평균 점수 차 (B-A)"),
        ("p_value",   "sign test p-value"),
        ("ci_low",    "95% CI 하한"),
        ("ci_high",   "95% CI 상한"),
    ]:
        vals = " | ".join(str(stats[e].get(key, "-")) for e in efforts)
        lines.append(f"| {label} | {vals} |")

    lines += [
        "",
        "## 차원별 B 승률",
        "",
        f"| 차원 | {' | '.join(efforts)} |",
        f"| --- | {col_sep}",
    ]
    dim_data = {e: (_dim_win_rates(RESULTS_DIR / r / "judgments_scored.jsonl")
                    if (RESULTS_DIR / r / "judgments_scored.jsonl").exists() else {})
                for e, r in effort_run_pairs}
    for dim in DIMS:
        vals = " | ".join(dim_data[e].get(dim, "-") for e in efforts)
        lines.append(f"| {dim} | {vals} |")

    if all_item_ids:
        lines += [
            "",
            "## 항목별 B 평균 점수",
            "",
            f"| 항목 | A (공통) | {' | '.join(f'B({e})' for e in efforts)} |",
            f"| --- | --- | {col_sep}",
        ]
        item_data = {
            e: (_item_mean_scores(
                    RESULTS_DIR / r / "judgments_scored.jsonl",
                    all_item_ids, na_allowed, grade_points
                ) if (RESULTS_DIR / r / "judgments_scored.jsonl").exists() else {})
            for e, r in effort_run_pairs
        }
        first_e = efforts[0]
        for iid in all_item_ids:
            a_score = item_data[first_e].get(iid, {}).get("A", "-")
            b_vals = " | ".join(
                str(item_data[e].get(iid, {}).get("B", "-")) for e in efforts
            )
            lines.append(f"| {iid} | {a_score} | {b_vals} |")

    lines += ["", "## 개별 실행 디렉토리", ""]
    for effort, run_id in effort_run_pairs:
        done = "완료" if (RESULTS_DIR / run_id / "summary.md").exists() else "미완료"
        lines.append(f"- **{effort}**: `eval/results/{run_id}/`  ({done})")

    out_path = RESULTS_DIR / "combined_effort_summary.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"[combined] wrote {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Progress file
# ---------------------------------------------------------------------------


def _progress_path() -> Path:
    return RESULTS_DIR / "run_all_efforts_progress.json"


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
    parser.add_argument("--efforts", default="low,medium,high,xhigh")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--run-prefix", default="gpt55", dest="run_prefix")
    parser.add_argument("--date-tag", default=None, dest="date_tag",
                        help="Override date tag in run ID (default: today's date YYYYMMDD)")
    parser.add_argument("--retry", type=int, default=2)
    parser.add_argument(
        "--max-concurrent", type=int, default=4, dest="max_concurrent",
        help="global max concurrent codex generate processes across ALL efforts (default: 4)",
    )
    args = parser.parse_args(argv)

    efforts = [e.strip() for e in args.efforts.split(",") if e.strip()]
    date_tag = args.date_tag if args.date_tag else datetime.now().strftime("%Y%m%d")

    effort_run_pairs: List[Tuple[str, str]] = [
        (effort, f"{args.run_prefix}_effort_{effort}_{date_tag}")
        for effort in efforts
    ]

    progress = _load_progress()
    progress.setdefault("started_at", datetime.now(timezone.utc).isoformat())
    progress.update({"model": args.model, "efforts": efforts, "seeds": args.seeds,
                     "effort_run_pairs": effort_run_pairs})
    _save_progress(progress)

    global _global_slots
    _global_slots = threading.Semaphore(args.max_concurrent)

    log(f"model={args.model}  efforts={efforts}  seeds={args.seeds}")
    log(f"run IDs: {[r for _, r in effort_run_pairs]}")
    log(f"max concurrent codex processes (global): {args.max_concurrent}")

    results: Dict[str, bool] = {}
    lock = threading.Lock()

    threads = []
    for effort, run_id in effort_run_pairs:
        t = threading.Thread(
            target=run_effort,
            name=f"effort-{effort}",
            kwargs=dict(
                effort=effort,
                run_id=run_id,
                model=args.model,
                seeds=args.seeds,
                max_retry=args.retry,
                results=results,
                lock=lock,
                progress=progress,
                batch_size=args.max_concurrent,
            ),
            daemon=False,
        )
        t.start()
        threads.append(t)
        log(f"started thread for effort={effort}", effort)

    for t in threads:
        t.join()

    log("all effort threads finished — building combined summary ...")
    try:
        out = build_combined_summary(effort_run_pairs, args.model)
        log(f"combined summary: {out}")
    except Exception as exc:
        log(f"combined summary error: {exc}")

    progress["completed_at"] = datetime.now(timezone.utc).isoformat()
    progress["results"] = results
    _save_progress(progress)

    log("=" * 60)
    log("ALL DONE")
    for effort, ok in sorted(results.items()):
        log(f"  {effort}: {'OK' if ok else 'FAILED'}")


if __name__ == "__main__":
    main()
