# milemate

`milemate` is a class assignment and presentation demo for helping
non-developer planners turn rough service ideas into PRD-style technical
planning documents. It is not a production service. The repo is set up to show
how a planner can move from a natural-language idea to a structured planning
artifact while keeping human approval, warning, and rollback points visible.

The live presentation path uses FastAPI, Streamlit, and the Codex CLI boundary
documented in [docs/live-demo-runbook.md](docs/live-demo-runbook.md). The local
development path uses an explicit no-network fake Codex client for UI and test
work only.

## What The Demo Shows

- Stage 1: turn a rough planner idea into a problem definition and KPI frame.
- Stage 2: turn the idea into service structure and MVP scope.
- Stage 3: verify technical, operational, data, and policy risks.
- Stage 4: generate planner, engineer, PRD, and decision-log outputs, then
  export the final artifact as a Word document, PDF report, or presentation
  deck.

The important classroom concept is not model accuracy. It is the workflow:
generate a stage, inspect the result, approve it, or roll back when stage 3
finds a weak assumption.

The current classroom scenario uses CleanGo, a last-mile laundry logistics
startup, only as an application example. The product concept is broader:
Milemate is a planning-document assistant for people who have service ideas but
do not yet have enough development context to write implementation-ready specs.

## Quick Start

Install dependencies:

```bash
uv sync --group dev --extra ui
```

Run tests:

```bash
uv run pytest -q
```

Live Codex mode uses a real backend and does not silently fall back to fake
output:

```bash
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
MILEMATE_API_MODE=http MILEMATE_API_BASE=http://127.0.0.1:8000 uv run --extra ui streamlit run app/frontend/streamlit_app.py
```

Local no-network development mode runs Streamlit against the in-process fake
Codex client:

```bash
MILEMATE_API_MODE=local uv run --extra ui streamlit run app/frontend/streamlit_app.py
```

For the full pre-demo checklist, stage script, timing expectations, and failure
handling, use [docs/live-demo-runbook.md](docs/live-demo-runbook.md).

## Project Layout

```text
app/backend/      FastAPI routes, stage manager, orchestrator, Codex boundary
app/frontend/     Streamlit presentation UI and local demo backend
config/           YAML stage, scenario, runtime, prompt, and source settings
data/demo_inputs/ Scenario prompts for the classroom demo
docs/             Planning docs and live demo runbook
tests/            Contract tests for backend, frontend, and integrations
```

## Report Outputs

The final report JSON is still available at `/reports/{session_id}` for
debugging and tests. The demo-facing outputs are binary exports:

```text
GET /reports/{session_id}/exports/docx  Word document for meeting review
GET /reports/{session_id}/exports/pdf   Fixed PDF for submission or printing
GET /reports/{session_id}/exports/pptx  Presentation deck for class demo
```

These exports are generated from the same approved stage 4 report bundle. The
UI surfaces them as `Word 문서`, `PDF 보고서`, and `발표 슬라이드`, while JSON is
kept as presenter/debug source data.

## Demo Boundaries

- Live mode should surface Codex CLI auth, model, or network failures directly.
- Local mode is a development and test fallback, not evidence of live Codex
  generation.
- Session state is in memory and intended for one presentation run.
- External retrieval/MCP integrations are represented through boundaries and
  local fixtures in this assignment version.
