# milemate

서울대학교 산업공학과 대학원 기술혁이론 수업 팀 프로젝트 저장소.

milemate는 라스트마일 서비스 기획의 동반자라는 의미를 담은 프로젝트 이름이다.

이 프로젝트는 라스트마일 관련 서비스 아이디어를 구현 관점으로 번역하여,
- 필요한 기반 기술과 기술 의존성을 구조화하고
- 현실적인 MVP 범위를 제안하며
- stage 기반 human-in-the-loop 워크플로우로 기획 과정을 정리하는
기술기획 에이전트 시스템을 만드는 것을 목표로 한다.

현재 프레임워크 방향은 Microsoft Agent Framework 기준으로 정리되어 있다.
모델 호출 경계는 OpenAI Codex SDK(Responses API) 기준으로 정리되어 있다.

## 1. 핵심 방향

### 프로젝트 핵심 개념
- 도메인: 라스트마일 배송 운영
- 목표: 특정 서비스 하나가 아니라 라스트마일 서비스 기획 전반에 재사용 가능한 planning workflow 만들기
- 대표 시나리오
  - 동적 배차 및 경로 재추천
  - ETA 예측 및 지연 알림
  - 실패 배송 리스크 예측 및 사전 개입

### 핵심 워크플로우
이 시스템은 단순 챗봇이 아니라 stage 기반 워크플로우를 따른다.
- stage 1: 문제 정의 및 KPI 정렬
- stage 2: 서비스 구조 및 MVP 범위 설계
- stage 3: 기술/운영/규제 검증
- stage 4: 최종 planner/engineer output 생성

특징
- 각 stage는 사용자 승인 후 다음 단계로 진행
- 이후 stage에서 새 제약이 발견되면 이전 stage로 rollback 가능
- verifier가 중간 검증 수행
- planner report / engineer report / decision log 생성

### 전체 파이프라인 시각화

```text
[사용자 / 기획자 입력]
         |
         v
+-------------------------+
| 프론트엔드 / 데모 UI    |
| - stage 화면            |
| - 승인 / 수정           |
| - rollback              |
+-------------------------+
         |
         v
+-------------------------+
| FastAPI API 계층        |
| - session               |
| - stage 요청            |
| - report 조회           |
+-------------------------+
         |
         v
+---------------------------------------------------+
| Microsoft Agent Framework 워크플로우 런타임       |
|                                                   |
|  [Stage 1] 문제 정의 / KPI 정렬                   |
|        |                                          |
|        | 승인                                     |
|        v                                          |
|  [Stage 2] 서비스 구조 / MVP 범위                 |
|        |                                          |
|        | 승인                                     |
|        v                                          |
|  [Stage 3] 기술 / 운영 / 규제 검증                |
|        |                                          |
|        | 통과                                     |
|        v                                          |
|  [Stage 4] 최종 planner / engineer output         |
|                                                   |
|  * stage 3 또는 stage 4에서 문제 발견 시          |
|    -> stage 1 또는 stage 2로 rollback 가능        |
+---------------------------------------------------+
         |
         +------------------------+
         |                        |
         v                        v
+---------------------+   +--------------------------+
| Planner Agent       |   | Verifier Agent           |
| - 문제 재정의       |   | - 데이터 현실성          |
| - KPI / 기능 구조   |   | - 기술 가능성            |
| - MVP 범위          |   | - 규제 / 법령 검토       |
+---------------------+   +--------------------------+
         |                        |
         +------------+-----------+
                      |
                      v
             +---------------------+
             | Report Agent        |
             | - planner report    |
             | - engineer report   |
             | - decision log      |
             +---------------------+
                      |
                      v
                 [최종 결과 출력]

공통 지원 계층:
- YAML 설정: stages / scenarios / sources / prompts / mcp-hub / app
- 프롬프트 파일: prompts/agents/{agent_name}/*
- 검색 계층: MCP Hub + GitHub + Fetch + legalize-kr + 웹 검색
- 모델 계층: OpenAI Codex SDK + fakeable client boundary
- 지식 계층: papers / docs / cases / laws / datasets / patents
```

### 파이프라인 해석
1. 사용자가 라스트마일 서비스 아이디어를 입력한다.
2. UI가 현재 stage 상태와 승인/수정/rollback 동작을 관리한다.
3. FastAPI가 요청을 workflow runtime으로 전달한다.
4. Microsoft Agent Framework workflow가 stage 1 -> 2 -> 3 -> 4를 관리한다.
5. Planner / Verifier / Report agent가 각 역할에 맞는 작업을 수행한다.
6. retrieval layer와 Codex SDK boundary가 각 stage를 뒷받침한다.
7. 최종적으로 planner report, engineer report, decision log가 출력된다.

## 2. 프레임워크 방향

현재 기준
- 에이전트/워크플로우 프레임워크: Microsoft Agent Framework
- backend/API: FastAPI
- 설정 관리: YAML 기반
- 모델 호출: OpenAI Codex SDK / Responses API
- retrieval: MCP Hub + custom adapter
- Python/버전 관리: uv 기반

## 3. 레포 구조

```text
.
├── app/
│   ├── backend/
│   │   ├── api/
│   │   ├── core/
│   │   ├── integrations/
│   │   └── services/
│   └── frontend/
├── config/
├── data/
├── docs/
├── knowledge/
├── prompts/
│   └── agents/
└── tests/
```

### 폴더 설명
- `app/backend/`: 워크플로우, stage 상태, API, verifier, retrieval adapter 관련 코드
- `app/backend/schemas/`: Pydantic 기반 data schema 모듈
- `app/frontend/`: 데모 UI 위치
- `config/`: YAML 단일 설정 소스
- `knowledge/`: 논문/기술문서/사례/법령/데이터셋/특허 메모
- `prompts/`: 에이전트별 × stage별 프롬프트 파일
- `data/`: 데모 입력/출력 및 합성 데이터
- `tests/`: 테스트 파일

## 4. 설정 원칙

이 프로젝트는 가능한 많은 공통 정보를 YAML config로 관리한다.

핵심 원칙
- stage 정의는 코드에 하드코딩하지 않는다.
- 시나리오 메타데이터는 config에서 읽는다.
- source category와 citation schema는 config에서 읽는다.
- prompt 경로는 config에서 읽는다.
- MCP source mapping은 config에서 읽는다.
- prompt는 inline 문자열이 아니라 파일로 관리한다.
- prompt는 agent별 × stage별 텍스트 파일 구조를 사용한다.

중요 파일
- `config/app.yaml`: app/model/serving/storage/features 설정
- `config/stages.yaml`: stage 정의, outputs, rollback target
- `config/scenarios.yaml`: dispatch / eta / failed-delivery 시나리오 메타데이터
- `config/sources.yaml`: retrieval/citation/source category
- `config/prompts.yaml`: agent별 prompt 파일 경로
- `config/mcp-hub.yaml`: MCP server와 source mapping
- `pyproject.toml`: uv 기반 프로젝트/의존성 정의
- `.python-version`: Python 버전 고정

## 5. 모델 및 실행 설정

현재 기본 가정
- model: `gpt-5.2-codex`
- runtime engine: `codex_sdk`
- API style: OpenAI Responses API

관련 설정은 `config/app.yaml`에 있다.

주요 필드
- `model.provider`
- `model.model_id`
- `serving.engine`
- `serving.api_key_env`
- `serving.request_timeout_seconds`
- `storage.stage_state`

## 6. config_loader 상태

`app/backend/core/config_loader.py`는 현재 다음 역할을 한다.
- YAML 로드
- `${ENV_VAR}` 형태 env 치환
- typed config validation
- stage/scenario/prompt 조회 helper 제공
- Codex SDK runtime 설정 helper 제공

대표 helper
- `load_app_config()`
- `reload_app_config()`
- `get_stage_definition(stage_id)`
- `get_scenario_definition(scenario_name)`
- `get_prompt_path(agent_name, stage_id)`
- `get_model_runtime_config()`

현재 기준에서 config loader는 정상 로딩 검증까지 완료됨.

## 7. 주요 문서

팀원들이 먼저 읽으면 좋은 문서
1. `docs/project-overview.md`
2. `docs/last-mile-service-options.md`
3. `docs/framework-selection.md`
4. `docs/implementation-plan.md`

## 8. 현재 상태 요약

완료된 것
- 프로젝트 방향 정리
- 라스트마일 시나리오 3종 정리
- stage 기반 workflow 설계
- source/MCP/legalize-kr 조사 방향 정리
- 레포 구조 scaffold 생성
- YAML config 구조 생성
- 에이전트별 prompt 파일 구조 생성
- config loader 구체화
- 프레임워크 방향 정리
- mock MVP backend 구현
  - in-memory session/state 관리
  - stage 1-4 deterministic output 생성
  - approve / advance / rollback 규칙 구현
  - final planner / engineer report 생성
- FastAPI endpoint 구현
- citation-ready mock retrieval / legal adapter 구현
- Streamlit demo UI 구현
- mock MVP hardening
  - demo-only in-memory session store boundary 정리
  - approval-before-run 및 final report approval gate 적용
  - rollback event/history 기록
  - FastAPI app factory와 dependency injection 적용
  - Microsoft Agent Framework core dependency와 graph runner boundary 추가
  - retrieval provider boundary와 Codex SDK client boundary 추가
  - scenario-aware Streamlit demo input과 stage 3 verification preset 추가
  - Streamlit AppTest smoke 추가

아직 구현하지 않은 것
- Microsoft Agent Framework 고급 graph/checkpoint 기능 활용
- Codex SDK 실호출을 stage output 생성에 기본 활성화
- 외부 retrieval / MCP 실연동

즉, 현재는 `dispatch_recommendation` 기준으로 발표 가능한 mock vertical slice가 동작한다.
실제 Codex 기반 생성과 external retrieval은 다음 phase에서 붙인다.

## 9. 실행 및 검증

테스트:

```bash
uv run pytest -q
uv run ruff check .
uv run python -m py_compile app/frontend/streamlit_app.py
```

API 서버:

```bash
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

Streamlit demo:

```bash
uv run streamlit run app/frontend/streamlit_app.py
```

병렬 구현 상세와 발표용 runbook은 `docs/parallel-implementation-plan.md`에 정리되어 있다.

## 10. 개발 환경 메모
- 의존성/버전 관리는 `uv` 기준으로 진행한다.
- 기본 Python 버전은 `.python-version`에 맞춰 3.11을 사용한다.

### uv 설치
macOS / Linux 예시
- `curl -LsSf https://astral.sh/uv/install.sh | sh`

설치 확인
- `uv --version`

### 프로젝트 환경 생성 및 동기화
1. 가상환경 생성
- `uv venv`

2. 기본 의존성 + 개발 도구 + UI + LLM 의존성 설치
- `uv sync --extra dev --extra ui --extra llm`

3. 가상환경 활성화
- macOS / Linux: `source .venv/bin/activate`

### 자주 쓰는 명령
- 테스트 실행: `uv run pytest -q`
- 특정 테스트 실행: `uv run pytest tests/test_config_loader.py`
- 린트 실행: `uv run ruff check .`
- FastAPI 실행 예시: `uv run uvicorn app.backend.main:app --reload`
- Streamlit 실행 예시: `uv run --extra ui streamlit run app/frontend/streamlit_app.py`

### Mock MVP 실행
터미널 1에서 backend를 실행한다.

```bash
uv run uvicorn app.backend.main:app --reload
```

터미널 2에서 Streamlit UI를 실행한다.

```bash
uv run --extra ui streamlit run app/frontend/streamlit_app.py
```

기본 UI는 `http://127.0.0.1:8000` backend를 호출한다.
다른 주소를 사용할 때는 `MILEMATE_API_BASE`를 지정한다.

```bash
MILEMATE_API_BASE=http://127.0.0.1:8010 uv run --extra ui streamlit run app/frontend/streamlit_app.py
```

현재 public API는 다음 최소 endpoint를 제공한다.
- `POST /sessions`
- `GET /sessions/{session_id}`
- `POST /stages/run`
- `POST /stages/approve`
- `POST /stages/rollback`
- `GET /reports/{session_id}`

### 참고
- 새 의존성을 추가할 때는 `pyproject.toml` 기준으로 관리한다.
- 팀원 간 Python 버전 차이를 줄이기 위해 `.python-version`을 유지한다.

## 9. 구현 시작 전 합의 권장 순서
1. `stages.yaml` / `scenarios.yaml` 검토
2. prompt 구조 검토
3. backend API contract 검토
4. Microsoft Agent Framework에서 stage graph를 어떻게 만들지 합의
5. 역할 분담 확정
