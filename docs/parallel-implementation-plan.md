# 병렬 구현 및 데모 실행 계획

이 문서는 mock MVP를 Codex SDK/MCP 실연동 전 단계의 implementation skeleton으로 강화한 현재 기준을 정리한다.

## 현재 구현 기준

- `StageManager`는 `SessionStore` 인터페이스 뒤에서 상태를 읽고 쓴다.
- 기본 런타임과 테스트는 demo-only `InMemorySessionStore`를 사용한다.
- stage approval은 현재 stage output이 생성된 뒤에만 가능하다.
- rollback은 `RollbackManager`가 처리하며 `rollback_events`에 invalidated stage를 기록한다.
- final report는 `stage_4` output이 있고 `stage_4`가 승인된 뒤에만 조회 가능하다.
- FastAPI는 `create_app()` factory를 제공하며 테스트별 manager/orchestrator를 분리할 수 있다.
- retrieval은 `RetrievalAdapter` coordinator와 provider boundary로 분리되어 있다.
- Codex 호출은 `CodexClient` boundary에 격리되어 있고 unit test에서는 network를 호출하지 않는다.
- Streamlit demo는 run 후 session을 refresh하고, current stage output이 없으면 approve를 비활성화한다.
- Microsoft Agent Framework core dependency와 graph runner adapter가 orchestration entrypoint를 담당한다.

## Agent 배치표

| 역할 | 파일 소유권 | 주요 책임 |
| --- | --- | --- |
| Main integrator | `schemas/*`, `pyproject.toml`, `uv.lock`, 최종 문서 | 공용 contract, merge 순서, 최종 검증 |
| Worker A: State/Demo Memory | `app/backend/core/stage_manager.py`, `session_store.py`, `rollback_manager.py`, `tests/test_stage_manager.py` | in-memory store boundary, approval gate, rollback history |
| Worker B: API Contract | `app/backend/api/**`, `app/backend/main.py`, `tests/test_api_routes.py` | app factory, dependency injection, shared request models, error code |
| Worker C: Orchestrator/Graph | `app/backend/core/orchestrator.py`, `agent_graph.py`, `tests/test_orchestrator.py` | MAF graph runner boundary, injected services, final report gate |
| Worker D: Retrieval/Model | `app/backend/integrations/**`, `tests/test_retrieval_adapters.py` | provider boundary, citation normalization, Codex SDK boundary |
| Worker E: Frontend/Demo | `app/frontend/**`, `data/demo_inputs/**`, Streamlit tests | scenario demo input, safe approve, rollback preset/context |
| Worker F: Docs/Runbook | `README.md`, `docs/**` | workflow docs, verification commands, demo script, caveats |

## Merge 순서

1. Main integrator가 shared schema와 error/status enum을 먼저 고정한다.
2. Worker A가 state/store/rollback contract를 반영한다.
3. Worker B가 API app factory와 dependency injection을 맞춘다.
4. Worker C가 orchestrator handler registry와 report gate를 맞춘다.
5. Worker D가 retrieval/Codex boundaries를 추가한다.
6. Worker E가 안정화된 API contract 기준으로 Streamlit demo를 조정한다.
7. Worker F가 실제 명령과 동작 기준으로 README와 runbook을 정리한다.

## 검증 명령

```bash
uv run pytest -q
uv run ruff check .
uv run python -m py_compile app/frontend/streamlit_app.py
```

수동 API smoke:

```bash
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

별도 터미널에서:

```bash
curl -s -X POST http://127.0.0.1:8000/sessions \
  -H 'Content-Type: application/json' \
  -d '{"scenario":"dispatch_recommendation","user_input":"peak dispatch bottleneck"}'
```

반환된 `session_id`로 `/stages/run`과 `/stages/approve`를 stage 1-4까지 반복한 뒤 `/reports/{session_id}`를 호출한다. stage 3에서 rollback을 확인하려면 `/stages/rollback`에 `{"target_stage":"stage_2","reason":"data risk"}`를 보낸다.

## 3-5분 데모 스크립트

1. FastAPI 서버를 시작한다.
2. Streamlit을 실행한다.

```bash
uv run streamlit run app/frontend/streamlit_app.py
```

3. sidebar에서 `Dynamic Dispatch and Route Recommendation`을 선택하고 `Start Session`을 누른다.
4. stage 1과 stage 2는 `Run Stage` 후 `Approve / Next`를 반복한다.
5. stage 3에서 `Stage 3 Check`를 `Missing data` 또는 `Poor labels`로 바꿔 verifier risk와 rollback target을 보여준다.
6. rollback이 필요한 경우 stage 2로 되돌린 뒤 다시 stage 2 output을 생성한다.
7. stage 4를 run/approve한 뒤 final report를 확인한다.

## Rollback 절차

- rollback은 현재 stage의 `rollback_targets`에 포함된 target으로만 허용된다.
- target stage와 그 이후의 output/approval은 invalidated state로 처리된다.
- invalidated stage 목록은 `rollback_events[*].invalidated_stages`에 남는다.
- rollback 후에는 target stage를 다시 run해야 approval이 가능하다.

## Mock-vs-real Caveats

- 현재 retrieval 결과는 deterministic mock provider와 local legal note를 사용한다.
- MCP/GitHub/Web provider class는 no-network boundary만 제공한다.
- `CodexClient`는 OpenAI Responses API payload를 만들고 호출할 수 있지만, unit test는 fake/request construction만 검증한다.
- `MilemateAgentGraphRunner`는 Microsoft Agent Framework core dependency가 설치되어 있는지 감지하고, 발표 demo에서는 deterministic graph nodes를 기본으로 사용한다.
