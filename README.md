# Last-Mile Planning Agent

서울대학교 산업공학과 대학원 기술혁이론 수업 팀 프로젝트 저장소.

이 프로젝트는 라스트마일 관련 서비스 아이디어를 구현 관점으로 번역해,
- 필요한 기반 기술과 기술 의존성을 구조화하고
- 현실적인 MVP 범위를 제안하며
- stage-based human-in-the-loop workflow로 기획을 정리하는
planning agent system을 만드는 것을 목표로 한다.

현재 프레임워크 방향은 Microsoft Agent Framework 중심으로 정리되어 있다.
모델은 로컬에서 `google/gemma-4-26B-A4B-it`을 vLLM으로 서빙하는 구성을 전제로 한다.

## 1. 현재까지 정리된 핵심 방향

### 프로젝트 핵심 개념
- 도메인: 라스트마일 배송 운영
- 목표: 특정 서비스 하나가 아니라 라스트마일 서비스 기획 전반에 재사용 가능한 planning workflow 만들기
- 대표 예시 시나리오
  - 동적 배차 및 경로 재추천
  - ETA 예측 및 지연 알림
  - 실패 배송 리스크 예측 및 사전 개입

### 핵심 workflow
이 시스템은 단순 챗봇이 아니라 stage-based workflow를 따른다.

- stage 1: 문제 정의 및 KPI 정렬
- stage 2: 서비스 구조 및 MVP 범위 설계
- stage 3: 기술/운영/규제 검증
- stage 4: 최종 planner/engineer output 생성

특징:
- 각 stage는 사용자 승인 후 다음 단계로 진행
- 미래 stage에서 새 제약이 발견되면 이전 stage로 rollback 가능
- verifier가 중간 검증 수행
- planner report / engineer report / decision log 생성

### 전체 파이프라인 시각화

```text
[User / Planner Input]
         |
         v
+-------------------------+
| Frontend / Demo UI      |
| - stage 화면            |
| - approve / revise      |
| - rollback              |
+-------------------------+
         |
         v
+-------------------------+
| FastAPI API Layer       |
| - session               |
| - stage submit          |
| - report fetch          |
+-------------------------+
         |
         v
+---------------------------------------------------+
| Microsoft Agent Framework Workflow Runtime        |
|                                                   |
|  [Stage 1] 문제 정의 / KPI 정렬                   |
|        |                                          |
|        | approve                                  |
|        v                                          |
|  [Stage 2] 서비스 구조 / MVP 범위                 |
|        |                                          |
|        | approve                                  |
|        v                                          |
|  [Stage 3] 기술 / 운영 / 규제 검증                |
|        |                                          |
|        | pass                                     |
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
            [Final Stage Output to Team/User]

Supporting layers used across stages:
- YAML Config: stages / scenarios / sources / prompts / mcp-hub / app
- Prompt Files: prompts/agents/{agent_name}/*
- Retrieval Layer: MCP Hub + GitHub + Fetch + legalize-kr + web search
- Model Layer: local vLLM serving google/gemma-4-26B-A4B-it
- Knowledge Layer: papers / docs / cases / laws / datasets / patents
```

### 파이프라인을 한 줄씩 해석하면
1. 사용자가 라스트마일 서비스 아이디어를 입력한다.
2. UI가 현재 stage 상태와 승인/수정/rollback 동작을 관리한다.
3. FastAPI가 요청을 workflow runtime으로 전달한다.
4. Microsoft Agent Framework workflow가 stage 1 -> 2 -> 3 -> 4를 관리한다.
5. Planner / Verifier / Report agent가 각 역할에 맞는 작업을 수행한다.
6. retrieval layer와 local vLLM이 각 stage를 뒷받침한다.
7. 최종적으로 planner report, engineer report, decision log가 출력된다.

## 2. 프레임워크 방향

현재 프레임워크 메모는 `docs/framework-selection.md`에 정리되어 있다.

현재 기준:
- agent/workflow framework: Microsoft Agent Framework
- backend/API: FastAPI
- config: YAML 기반
- model serving: vLLM
- model metadata: Hugging Face 기준 관리
- retrieval: MCP Hub + custom adapters

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

#### `app/backend/`
백엔드 및 workflow orchestration 관련 코드 위치.

- `core/`: stage manager, orchestrator, rollback manager, schemas, config loader
- `api/`: stage/session/report API route
- `services/`: planner, verifier, report, memory 관련 서비스
- `integrations/`: retrieval, MCP, GitHub, 법령, web search adapter

현재는 scaffold + placeholder 중심 구조이며, 실제 구현은 이후 팀원들과 진행 예정.

#### `app/frontend/`
프론트엔드/데모 UI 위치.

현재는 구조만 생성되어 있고 실제 UI 구현은 아직 시작 전.

#### `config/`
YAML single source of truth.

현재 파일:
- `app.yaml`
- `stages.yaml`
- `scenarios.yaml`
- `sources.yaml`
- `prompts.yaml`
- `mcp-hub.yaml`

#### `knowledge/`
자료 축적용 폴더.

카테고리:
- papers
- docs
- cases
- laws
- datasets
- patents

한국 법령 자료는 `knowledge/laws/legalize-kr-notes.md`와 `legalize-kr` 기반 조사 방향을 반영해 두었다.

#### `prompts/`
프롬프트 파일 저장소.

현재는 에이전트별 × stage별 텍스트 파일 구조를 사용한다.

예:
- `prompts/agents/orchestrator_agent/system.txt`
- `prompts/agents/orchestrator_agent/orchestrator_agent_stage1.txt`
- `prompts/agents/planner_agent/planner_agent_stage2.txt`
- `prompts/agents/verifier_agent/verifier_agent_stage3.txt`
- `prompts/agents/report_agent/report_agent_stage4.txt`

#### `data/`
- `demo_inputs/`: 데모 입력 예시
- `demo_outputs/`: 데모 출력 저장 위치
- `synthetic/`: 합성 데이터 및 mock 데이터

#### `tests/`
테스트 placeholder 위치.

## 4. Config 원칙

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
- `config/app.yaml`: app/model/serving/huggingface/storage/features 설정
- `config/stages.yaml`: stage 정의, outputs, rollback target
- `config/scenarios.yaml`: dispatch / eta / failed-delivery 시나리오 메타데이터
- `config/sources.yaml`: retrieval/citation/source category
- `config/prompts.yaml`: agent별 prompt 파일 경로
- `config/mcp-hub.yaml`: MCP server와 source mapping

## 5. 모델 및 서빙 설정

현재 기본 가정은 다음과 같다.

- model: `google/gemma-4-26B-A4B-it`
- serving engine: `vllm`
- API style: OpenAI-compatible endpoint

관련 설정은 `config/app.yaml`에 있다.

주요 필드:
- `model.provider`
- `model.model_id`
- `serving.engine`
- `serving.base_url`
- `serving.chat_completions_path`
- `huggingface.token_env`
- `huggingface.cache_dir`

## 6. config_loader 상태

`app/backend/core/config_loader.py`는 현재 다음 역할을 한다.
- YAML 로드
- `${ENV_VAR}` 형태 env 치환
- typed config validation
- stage/scenario/prompt 조회 helper 제공
- vLLM/Hugging Face runtime 설정 helper 제공

현재 제공 helper 예시:
- `load_app_config()`
- `reload_app_config()`
- `get_stage_definition(stage_id)`
- `get_scenario_definition(scenario_name)`
- `get_prompt_path(agent_name, stage_id)`
- `get_model_runtime_config()`

현재 기준에서 config loader는 정상 로딩 검증까지 완료됨.

## 7. 주요 문서

팀원들이 먼저 읽어야 할 문서:

1. `docs/project-overview.md`
- 프로젝트의 전체 목표와 agent workflow 개요

2. `docs/last-mile-service-options.md`
- 라스트마일 서비스 기획 프레임워크
- 시나리오 비교표
- 자료 확보 계획
- MCP/source 전략

3. `docs/framework-selection.md`
- Microsoft Agent Framework 중심 설명

4. `docs/implementation-plan.md`
- 4인 팀 기준 모듈 분리와 구현 계획


## 8. 현재 상태 요약

현재 저장소는 다음 상태다.

완료된 것:
- 프로젝트 방향 정리
- 라스트마일 시나리오 3종 정리
- stage-based workflow 설계
- source/MCP/legalize-kr 조사 방향 정리
- 레포 구조 scaffold 생성
- YAML config 구조 생성
- 에이전트별 prompt 파일 구조 생성
- config loader 구체화
- 프레임워크 방향 정리

아직 구현하지 않은 것:
- 실제 backend workflow 로직
- frontend 화면
- retrieval adapter 구현
- verifier 구현
- report 생성 로직
- Microsoft Agent Framework 실제 연결 코드

즉, 현재는 “구조와 설계는 정리되었고, 구현은 팀원들과 함께 시작할 단계”라고 보면 된다.

## 9. 팀원 작업 시작 전 권장 순서

팀원들이 바로 구현에 들어가기 전에 아래 순서로 합의하면 좋다.

1. `stages.yaml` / `scenarios.yaml` 검토
2. prompt 구조 검토
3. backend API contract 검토
4. Microsoft Agent Framework에서 stage graph를 어떻게 만들지 합의
5. 역할 분담 확정

## 10. 참고

- 한국 법령 자료: `legalize-kr/legalize-kr` 활용 방향 반영 완료
- MCP Hub 자료원 연결 전략 반영 완료
- prompt는 JSON inline이 아니라 파일 기반으로 관리
- config는 YAML 중심으로 관리

이 README는 현재 팀 공유용 상태 문서이며, 구현이 진행되면 실행 방법과 개발 규칙을 추가로 보강하면 된다.
