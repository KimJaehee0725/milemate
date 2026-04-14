# 구현 계획

목표: stage 기반 human-in-the-loop planning agent를 4인 팀이 병렬 작업 가능하도록 모듈화하여 구현한다.

기본 기술 스택
- 에이전트 / 워크플로우: Microsoft Agent Framework
- backend: FastAPI
- 모델 서빙: vLLM
- 모델: google/gemma-4-26B-A4B-it
- 설정 관리: YAML
- 상태 저장: SQLite 우선
- retrieval: MCP Hub + custom adapter
- 프론트엔드: Streamlit 우선

## 1. 팀원 4명 기준 모듈 분리

### 모듈 A. UX / 프론트엔드 / stage 상호작용
담당: 팀원 1

목표
- planner-facing UI 구현
- stage 승인 / 수정 / rollback UX 구현
- planner report / engineer report 화면 구성

주요 산출물
- stage 화면
- 승인 / 수정 / rollback 버튼
- decision log 시각화
- 데모 흐름

### 모듈 B. backend / orchestration / stage 엔진
담당: 팀원 2

목표
- stage state machine 구현
- workflow orchestration 구현
- session / approval / rollback API 구현
- output schema 관리

주요 산출물
- backend API
- stage manager
- orchestrator
- response schema

### 모듈 C. 지식 / retrieval / MCP 연동
담당: 팀원 3

목표
- knowledge 폴더 구성
- retrieval adapter 구현
- GitHub / Fetch / 법령 / MCP 연결
- source citation 구조 설계

주요 산출물
- source inventory
- retrieval adapter layer
- legalize-kr 활용 경로
- mcp-hub 설정 초안

### 모듈 D. prompt / verifier / 평가
담당: 팀원 4

목표
- agent별 × stage별 prompt 작성
- scenario별 적용 규칙 정리
- verifier 체크리스트 정리
- demo input / expected output / 평가 기준 정리

주요 산출물
- prompt library
- verifier rule set
- evaluation checklist
- demo 예시

## 2. 추천 레포 구조

```text
project-root/
  README.md
  docs/
    project-overview.md
    last-mile-service-options.md
    framework-selection.md
    implementation-plan.md
  app/
    frontend/
      pages/
      components/
      stage_views/
    backend/
      main.py
      api/
      core/
      services/
      integrations/
  knowledge/
    papers/
    docs/
    cases/
    laws/
    datasets/
    patents/
  prompts/
    agents/
      orchestrator_agent/
      planner_agent/
      verifier_agent/
      report_agent/
  data/
    demo_inputs/
    demo_outputs/
    synthetic/
  tests/
  config/
    app.yaml
    stages.yaml
    scenarios.yaml
    sources.yaml
    prompts.yaml
    mcp-hub.yaml
```

## 3. 구현 순서

### Phase 1. 계약 고정
합의할 것
- stage 정의
- output schema
- API contract
- source category
- scenario enum
- citation format

이 단계가 가장 중요하다. 이걸 먼저 맞추지 않으면 모듈 통합이 어려워진다.

### Phase 2. mock 기반 vertical slice
범위
- 시나리오 1개: 동적 배차 및 경로 재추천
- mocked retrieval
- mocked verifier
- 실제 stage approval UI
- 실제 rollback 흐름

성공 기준
- 사용자 입장에서 stage 1~4를 따라갈 수 있음
- rollback 동작함
- planner report / engineer report 렌더링 가능

### Phase 3. 실제 retrieval 연결
범위
- markdown knowledge base
- web / document retrieval adapter
- legalize-kr law lookup
- source citation 출력

성공 기준
- 출력에 실제 source citation이 포함됨
- 기술 source, 사례 source, 법령 source를 최소 하나씩 보여줄 수 있음

### Phase 4. verifier + 다중 시나리오 일반화
범위
- stage 3 verifier 규칙 활성화
- ETA / failed-delivery 시나리오 추가
- 같은 stage 엔진으로 3개 시나리오 처리

성공 기준
- 3개 시나리오가 같은 workflow를 공유함
- verifier가 rollback 추천을 줄 수 있음

### Phase 5. 데모 고도화
범위
- demo script 정리
- sample input 안정화
- deterministic output 스타일 정리
- fallback plan 정리

성공 기준
- 3~5분 발표 데모가 안정적으로 작동함

## 4. 팀원별 세부 작업

### 팀원 1
- stage 1~4 화면 설계
- 승인 / 수정 / rollback 버튼 배치
- planner report / engineer report 화면 설계
- 시나리오 전환 UI 설계

### 팀원 2
- stage response schema 작성
- stage manager / rollback manager 작성
- orchestrator 작성
- FastAPI route 작성

### 팀원 3
- source inventory 정리
- retrieval adapter 작성
- MCP source mapping 정리
- legalize-kr 활용 노트 정리
- citation schema 적용

### 팀원 4
- orchestrator / planner / verifier / report agent prompt 작성
- dispatch / ETA / failed-delivery 적용 규칙 정리
- verifier rule 작성
- demo input / expected output / rubric 정리

## 5. 통합 전에 반드시 맞춰야 하는 것

### stage response schema
최소 필드
- stage_id
- status
- summary
- decision_points
- required_user_input
- citations
- rollback_targets
- planner_view
- engineer_view

### 시나리오 enum
- dispatch_recommendation
- eta_prediction
- failed_delivery_risk
- other_last_mile

### citation format
- source_type
- title
- locator
- relevance_note

### rollback semantics
- soft rollback suggestion
- hard rollback required
- blocked until user resolves

## 6. 주차별 추천 일정

### 1주차
- 팀원 1: UI wireframe
- 팀원 2: schema + stage manager 초안
- 팀원 3: source inventory + MCP 후보 정리
- 팀원 4: prompt / verifier 초안

### 2주차
- 팀원 1: stage UI 구현
- 팀원 2: backend mock flow 구현
- 팀원 3: retrieval mock 또는 단순 adapter 작성
- 팀원 4: dispatch 시나리오 prompt와 sample output 작성

### 3주차
- 팀원 1: report / UI 개선
- 팀원 2: real adapter 연결
- 팀원 3: MCP config + legalize-kr + citation 연결
- 팀원 4: ETA / failed-delivery prompt + verifier 규칙 추가

### 4주차
- 팀원 1: frontend demo polish
- 팀원 2: API / rollback 안정화
- 팀원 3: source pack / fallback retrieval 정리
- 팀원 4: demo script / 평가 기준 / expected output 정리

## 7. 시간 부족 시 우선순위

남겨야 할 것
- stage workflow
- 1개 시나리오 완전 구현
- 1개 실제 retrieval 경로
- verifier
- planner / engineer 분리 출력

나중에 잘라도 되는 것
- fancy frontend
- advanced long-term memory
- multi-agent decomposition
- full DB persistence
- 세 시나리오 모두 완전 인터랙티브 구현

## 8. 완료 기준
- dispatch 시나리오 기준 stage 1~4 완료 가능
- rollback 경로 최소 1개 작동
- planner report / engineer report 생성 가능
- 최종 출력에 실제 source 3개 이상 인용
- 법령 source 경로 1개 이상 시연 가능
- 동일한 stage framework가 ETA / failed-delivery에도 적용 가능함을 보여줄 수 있음
- 5분 이내 데모 가능
