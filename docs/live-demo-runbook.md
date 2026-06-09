# Live Demo Runbook

This runbook is for the class presentation of `milemate`. Treat the repo as a
demo artifact for explaining how a non-developer planner can turn a rough idea
into a stage-based technical planning document, not as a production
FastAPI/Streamlit service.

The two supported modes are intentionally different:

- Live Codex mode: Streamlit calls FastAPI, and FastAPI calls the Codex CLI.
  Failures are visible. Do not silently switch to fake output.
- Local no-network mode: Streamlit uses `LocalDemoAPI` and `LocalFakeCodexClient`
  in-process. This is only for development, tests, rehearsal, or explaining the
  UI when live Codex is unavailable.

## One-Time Setup

Run from the repo root:

```bash
cd /Users/jaeheemacbook/Desktop/mini-projects/taste-of-text
uv sync --group dev --extra ui
```

Confirm the runtime config you are about to present:

```bash
sed -n '15,40p' config/app.yaml
```

The live demo expects:

```text
model_id: gpt-5.5
reasoning_effort: medium
engine: codex_cli
cli_binary: codex
request_timeout_seconds: 600
allow_deterministic_fallback: false
```

## Pre-Demo Checklist

Run this before class, ideally on the same network and laptop used for the
presentation.

### 1. Tests

```bash
uv run pytest -q
```

Expected result: all active tests pass. Current tests include backend API
failure mapping, Streamlit local mode smoke tests, stage rollback behavior, and
Codex CLI command construction without network calls. They also smoke-test the
final report exports as Word, PDF, and PowerPoint OOXML/PDF artifacts.

### 2. Codex CLI Binary And Version

```bash
command -v codex
codex --version
```

Expected result: `command -v` prints a real Codex binary path and
`codex --version` prints a version. On this machine during runbook authoring,
the observed version was:

```text
codex-cli 0.137.0-alpha.4
```

Optional live model smoke, only if you are comfortable making a small real Codex
request before class:

```bash
tmp_output="$(mktemp -t milemate-codex-smoke.XXXXXX)"
printf 'Return exactly: OK' | codex --search exec -m gpt-5.5 --ephemeral --json --sandbox read-only --output-last-message "$tmp_output"
cat "$tmp_output"
rm "$tmp_output"
```

Expected result: the output file contains `OK`. If this fails, treat it as a
live runtime problem, not as a reason to hide the failure behind local mode.

### 3. Backend Health

Start the backend in terminal 1:

```bash
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

Check health from terminal 2:

```bash
curl -sS http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","app":"milemate-planning-assistant"}
```

### 4. Runtime Status

The class demo plan expects a runtime status endpoint:

```bash
curl -i http://127.0.0.1:8000/runtime/status
```

Expected live-ready response, if the backend worker has landed the endpoint:

```json
{
  "app_name": "milemate-planning-assistant",
  "api_mode": "responses",
  "runtime_mode": "live_codex_cli",
  "serving_engine": "codex_cli",
  "model_id": "gpt-5.5",
  "cli_binary": "codex",
  "cli_available": true,
  "cli_path": "/path/to/codex",
  "timeout": 600
}
```

If it returns `404`, the backend process is not using the current app wiring. If
`cli_available` is `false`, live mode is not ready on this machine. In either
case, do not treat the status check as passed.

### 5. Stage Timing Targets

Use these as classroom pacing targets, not hard guarantees:

| Mode | Stage 1 | Stage 2 | Stage 3 | Stage 4 | Timeout |
| --- | ---: | ---: | ---: | ---: | ---: |
| Live Codex | 45-120s | 45-120s | 45-150s | 60-180s | 600s per CLI call |
| Local no-network | <5s | <5s | <5s | <5s | Streamlit test timeout |

If a live stage exceeds about 3 minutes, narrate what the stage is doing and be
ready to stop before the 600 second timeout if the presentation slot is tight.

## Live Codex Mode Commands

Use two terminals.

Terminal 1, backend:

```bash
cd /Users/jaeheemacbook/Desktop/mini-projects/taste-of-text
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, Streamlit:

```bash
cd /Users/jaeheemacbook/Desktop/mini-projects/taste-of-text
MILEMATE_API_MODE=http MILEMATE_API_BASE=http://127.0.0.1:8000 uv run --extra ui streamlit run app/frontend/streamlit_app.py
```

If port `8000` is already occupied, start the backend on another port and set
`MILEMATE_API_BASE` to the same address, for example `http://127.0.0.1:8010`.

Open the Streamlit URL printed by the command, usually:

```text
http://localhost:8501
```

Live mode is successful only if the UI calls FastAPI and FastAPI calls Codex
through `CodexClient`. A 503, 502, timeout, or model-output error is part of the
live demo contract and should be handled explicitly.

## Local No-Network Development Mode

Use this for rehearsal, screenshots, Streamlit testing, or UI explanation when
network/auth/model availability is not the point of the presentation.

```bash
cd /Users/jaeheemacbook/Desktop/mini-projects/taste-of-text
MILEMATE_API_MODE=local uv run --extra ui streamlit run app/frontend/streamlit_app.py
```

No backend process is needed. The UI caption should say `로컬 데모 백엔드`.
This mode uses deterministic services behind an explicit fake Codex client.
When using it in class, say: "This is local development mode. It demonstrates
the workflow mechanics, not a live Codex model call."

## Presentation Script

Default application example: `CleanGo 적용 예시: 피크타임 배차 추천`.

### Opening

Say:

"This is our class demo for helping a non-developer planner turn a rough service
idea into a technical planning document. CleanGo is only the application
example. The core idea is human-in-the-loop planning: generate one stage,
inspect it, approve it, or roll back when later verification finds a weak
assumption."

In the sidebar:

1. Select `CleanGo 적용 예시: 피크타임 배차 추천`.
2. Keep the generated Korean idea memo unless you need to shorten it.
3. Click `기획서 작성 시작`.

### Stage 1: Problem Definition And KPI Alignment

Action:

1. In `기획자 추가 요청`, keep the prepared stage 1 prompt.
2. Click `Codex로 기획서 생성`.
3. Wait for Codex or local mode to finish.
4. Point to problem summary, KPI candidates, citations, and decision points.
5. Click `경고 확인 후 승인` or `검토 후 승인`, depending on the review panel state.

Say:

"Stage 1 forces us to turn a planner's rough idea into a problem statement and
KPI frame before jumping to implementation. CleanGo is the example, but the
workflow is about writing a technical planning document."

### Stage 2: Service Structure And MVP Scope

Action:

1. Keep the prepared stage 2 prompt.
2. Click `Codex로 기획서 생성`.
3. Point to in-scope and out-of-scope MVP items.
4. Click `경고 확인 후 승인` or `검토 후 승인`, depending on the review panel state.

Say:

"Stage 2 is where the idea becomes a scoped MVP rather than a broad AI wish.
The important choice is to separate what the planner can approve now from what
should wait for data, policy, or engineering validation."

### Stage 3: Verification Warning With Missing Data

Action:

1. In the sidebar, set `검증에서 드러낼 리스크` to `데이터 부족`.
2. Keep the prepared stage 3 prompt.
3. Click `Codex로 기획서 생성`.
4. Show the verifier status, risk list, required user input, and rollback target.

Expected local-mode behavior:

- The stage 3 evidence context contains `{"data_sources": []}`.
- The verifier result shows `warning`.
- The risk text includes missing planning or operations data.
- A rollback recommendation is shown, usually `stage_1` for missing data.
- The rollback UI appears with configured targets such as `stage_1` and
  `stage_2`.

Say:

"This is the key tradeoff. We can approve a warning if the team accepts the data
risk for a narrow pilot, but that makes the assumption explicit. Or we can roll
back and repair the upstream plan before finalizing. Missing data is a reason to
revisit problem framing or MVP scope, not something the demo hides."

To show rollback:

1. Click `이전 단계로 되돌리기`.
2. Select `2단계 서비스 구조` if you want a short rollback demo, or
   `1단계 문제 정의` if you want to follow the missing-data recommendation
   literally.
3. In `롤백 사유 및 수정 지시`, write a detailed reason such as:

   ```text
   발견한 문제: 데이터 출처가 비어 있어 3단계 검증을 통과시키기 어렵습니다.
   잘못된 가정: 2단계 MVP 범위가 필요한 운영 데이터를 이미 확보했다고 봤습니다.
   되돌아가 수정할 내용: 데이터 소유자와 수집 주기를 먼저 확정하고, 데이터가 없는 기능은 MVP 밖으로 빼주세요.
   다음 단계에서 유지할 내용: 운영자 승인형 추천이라는 큰 방향은 유지합니다.
   ```

4. Click `이 사유로 되돌리기`.
5. Show that later outputs are invalidated and approval is disabled until
   the target stage is regenerated.

Say:

"Rollback is costly because it invalidates later work, but it is more honest
than approving a plan whose data assumptions are not credible."

To continue after rollback:

1. Regenerate the target stage.
2. Approve it.
3. On stage 3, set `검증에서 드러낼 리스크` back to `기본 자료 충분`.
4. Generate stage 3 again and approve it.

### Stage 4: Final Planner And Engineer Outputs

Action:

1. Keep the prepared stage 4 prompt.
2. Click `Codex로 기획서 생성`.
3. Show the planner summary, implementation review, planning document packet,
   citations, and decision log.
4. Click `경고 확인 후 승인` or `검토 후 승인` to load the final report.
5. In `문서 패키지`, point to the three business-facing outputs:
   `Word 문서`, `PDF 보고서`, and `발표 슬라이드`.
6. Keep `발표자용 원본 데이터` closed unless you need to explain the underlying
   JSON contract.

Say:

"Stage 4 is not a magic answer. It is a class presentation artifact assembled
from approved earlier stages, the verification result, and the decision log. The
workflow makes it clear what we approved and what risks remain."

Then say:

"The output is no longer just a Markdown note. A real planning workflow needs
an editable Word brief for review, a fixed PDF for submission, and a short slide
deck for presentation. All three come from the same approved report bundle."

## Failure Handling Script

Use these responses if live Codex mode fails. The rule is simple: do not pretend
local mode is live mode.

### Codex CLI Missing

Symptoms:

- `command -v codex` returns nothing.
- Backend returns `503` with `MODEL_NOT_CONFIGURED`.
- UI shows that the stage generation failed.

Say:

"The live Codex CLI is not installed or not on PATH on this machine. This demo
is intentionally configured to fail visibly instead of silently generating fake
output."

Do:

1. Show `command -v codex`.
2. Do not change to local mode without naming it.
3. If the presentation must continue, restart Streamlit with
   `MILEMATE_API_MODE=local` and say it is a no-network workflow walkthrough.

### Codex Auth Fails

Symptoms:

- CLI output mentions login, authentication, unauthorized, or not configured.
- Backend returns `503` with `MODEL_NOT_CONFIGURED`.

Say:

"The model call boundary is present, but this machine is not authenticated for
Codex CLI. We are seeing the designed explicit failure path."

Do:

1. Show the error.
2. Fix auth only if there is time and it does not expose private credentials.
3. Otherwise switch to local mode only as a clearly labeled walkthrough.

### Model Is Unavailable

Symptoms:

- CLI or backend error mentions unavailable model or invalid model.
- Backend returns `502` with `MODEL_CALL_FAILED`.

Say:

"The configured model ID in `config/app.yaml` is not available in this runtime.
Changing models during the live presentation would change the experiment, so I
will treat this as a runtime failure unless the team explicitly approves a
config update."

Do:

1. Show `config/app.yaml`.
2. Note the configured `gpt-5.5` model.
3. Do not silently swap the model or local fake client.

### Network Or Timeout Fails

Symptoms:

- CLI hangs or times out.
- Backend returns `502` with `MODEL_CALL_FAILED`.
- Stage generation fails after the Codex timeout.

Say:

"The workflow reached the live model boundary, but the network/model call did
not complete within the presentation window. The fallback is a labeled local
development walkthrough, not a fake live run."

Do:

1. Keep the backend error visible long enough to show explicit failure handling.
2. Stop the live attempt if timing would block the rest of the presentation.
3. Restart Streamlit in local mode only if you clearly label it.

## API Smoke Commands

These commands are useful if you want to verify the backend without Streamlit.

Create a session:

```bash
curl -sS -X POST http://127.0.0.1:8000/sessions \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"dispatch_recommendation","user_input":"CleanGo planner idea for reducing peak-time delivery delays"}'
```

Run the current stage after replacing `SESSION_ID`:

```bash
curl -sS -X POST http://127.0.0.1:8000/stages/run \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"SESSION_ID","user_input":"Generate the current stage for the class demo.","context":{}}'
```

Approve the current stage:

```bash
curl -sS -X POST http://127.0.0.1:8000/stages/approve \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"SESSION_ID"}'
```

Force the stage 3 missing-data context:

```bash
curl -sS -X POST http://127.0.0.1:8000/stages/run \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"SESSION_ID","user_input":"Verify the proposal with missing data.","context":{"data_sources":[]}}'
```

Roll back:

```bash
curl -sS -X POST http://127.0.0.1:8000/stages/rollback \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"SESSION_ID","target_stage":"stage_2","reason":"Missing operational data for verification"}'
```

Fetch the final report after stage 4 is run and approved:

```bash
curl -sS http://127.0.0.1:8000/reports/SESSION_ID
```

Download final report artifacts after stage 4 is run and approved:

```bash
curl -sS -o milemate-final-planning-brief.docx \
  http://127.0.0.1:8000/reports/SESSION_ID/exports/docx

curl -sS -o milemate-final-planning-brief.pdf \
  http://127.0.0.1:8000/reports/SESSION_ID/exports/pdf

curl -sS -o milemate-final-presentation-deck.pptx \
  http://127.0.0.1:8000/reports/SESSION_ID/exports/pptx
```
