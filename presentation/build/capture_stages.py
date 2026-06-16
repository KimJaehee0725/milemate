"""Capture per-stage request / reasoning(summary) / output for ONE scenario.

Mirrors eval/pipeline.generate_proposed but snapshots each StageResponse.output
(the full StageOutputBundle, including `summary` = that stage's reasoning) BEFORE
approving, plus the per-stage request text and the final merged bundle.

Writes incrementally to presentation/jh/_capture_<scenario>.json so a partial run
is still useful if a later stage fails.

Run from repo root:  python presentation/build/capture_stages.py [scenario]
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from eval.pipeline import (  # noqa: E402
    STAGE_IDS,
    load_initial_inputs,
    load_stage_requests,
    stage_inputs_for,
)
from app.backend.core.config_loader import get_model_runtime_config  # noqa: E402
from app.backend.core.orchestrator import Orchestrator  # noqa: E402
from app.backend.core.stage_manager import StageManager  # noqa: E402
from app.backend.core.agent_graph import MilemateAgentGraphRunner  # noqa: E402
from app.backend.integrations.codex_client import CodexClient  # noqa: E402

SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "dispatch_recommendation"
OUT = ROOT / "presentation" / "jh" / f"_capture_{SCENARIO}.json"


def log(msg: str) -> None:
    print(f"[capture] {msg}", flush=True)


def main() -> None:
    inits = load_initial_inputs()
    initial_input = inits[SCENARIO]
    reqs = load_stage_requests()
    stage_inputs = stage_inputs_for(SCENARIO, initial_input, reqs)

    rt = get_model_runtime_config()  # config/app.yaml: medium effort, codex binary
    log(f"scenario={SCENARIO} model_id={rt.get('model_id')!r} "
        f"effort={rt.get('reasoning_effort')!r} timeout={rt.get('timeout')}")

    manager = StageManager()
    runner = MilemateAgentGraphRunner(codex_client=CodexClient(runtime_config=rt))
    orchestrator = Orchestrator(stage_manager=manager, graph_runner=runner)
    session = manager.create_session(scenario=SCENARIO, user_input=stage_inputs["stage_1"])

    result = {
        "scenario": SCENARIO,
        "initial_input": initial_input,
        "model": {"model_id": rt.get("model_id"), "reasoning_effort": rt.get("reasoning_effort")},
        "stages": [],
        "final_bundle": None,
    }

    def flush():
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    flush()
    for stage_id in STAGE_IDS:
        log(f"running {stage_id} ...")
        t0 = time.monotonic()
        response = orchestrator.run_current_stage(
            session.session_id, user_input=stage_inputs[stage_id], context={}
        )
        elapsed = round(time.monotonic() - t0, 1)
        if response.stage_id != stage_id:
            raise RuntimeError(f"stage drift: expected {stage_id}, got {response.stage_id}")
        result["stages"].append({
            "stage_id": stage_id,
            "request": stage_inputs[stage_id],
            "elapsed_seconds": elapsed,
            "output": response.output.model_dump(mode="json"),
        })
        flush()
        log(f"  {stage_id} done in {elapsed}s "
            f"(summary len={len(response.output.summary)})")
        orchestrator.approve_current_stage(session.session_id)

    log("building final report ...")
    t0 = time.monotonic()
    bundle = orchestrator.build_final_report(session.session_id)
    result["final_bundle"] = bundle.model_dump(mode="json")
    result["final_elapsed_seconds"] = round(time.monotonic() - t0, 1)
    flush()
    log(f"DONE -> {OUT}")


if __name__ == "__main__":
    main()
