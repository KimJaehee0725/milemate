# Microsoft Agent Framework

## 선택 방향
이 프로젝트의 에이전트 프레임워크는 Microsoft Agent Framework를 기준으로 검토한다.

이 문서는 다른 프레임워크와의 비교 메모를 남기지 않고, Microsoft Agent Framework를 우리 프로젝트에 어떻게 적용할지에만 집중한다.

## 왜 이 프레임워크가 프로젝트와 맞는가
우리 프로젝트는 다음 요구사항을 가진다.
- stage-based workflow
- human-in-the-loop 승인 구조
- 이전 stage로의 rollback
- verifier 기반 중간 검증
- 장기적으로 multi-agent orchestration 가능성
- Python 기반 구현
- Codex CLI 기반 모델 호출

Microsoft Agent Framework는 저장소 설명과 README 기준으로 아래 특성을 전면에 둔다.
- graph-based workflows
- checkpointing
- human-in-the-loop
- time-travel
- multi-agent workflows
- Python / .NET 지원
- DevUI 기반 개발 / 디버깅 경험

즉, 단순 채팅 에이전트보다 workflow 중심 구조가 필요한 우리 프로젝트와 잘 맞는다.

## 이 프로젝트에서 기대하는 역할
- stage 1~4 흐름을 그래프 형태로 관리
- 각 stage의 승인 여부를 상태로 관리
- verifier 이후 rollback 가능 여부를 판단
- 장기적으로 retrieval agent, verifier agent, legal/risk agent 같은 멀티에이전트 확장 가능성 제공
- workflow 개발 / 디버깅 구조 제공

## 우리 프로젝트에 매핑되는 개념
### 1. stage workflow
프로젝트의 핵심 흐름은 아래와 같다.
- stage 1: 문제 정의 및 KPI 정렬
- stage 2: 서비스 구조 및 MVP 범위 설계
- stage 3: 기술 / 운영 / 규제 검증
- stage 4: 최종 planner / engineer output 생성

Microsoft Agent Framework에서는 이를 workflow graph 또는 process 형태로 표현하는 방향을 기본으로 본다.

### 2. human-in-the-loop
각 stage는 자동으로 다음 단계로 넘어가지 않는다.
사용자 승인 후 진행하며, 이 승인 상태가 workflow state에 반영되어야 한다.

### 3. rollback
미래 stage에서 새로운 제약이 발견되면 이전 stage로 되돌아갈 수 있어야 한다.
예를 들어:
- stage 3에서 데이터 가정이 틀리면 stage 2로 rollback
- stage 3에서 KPI-기능 정렬이 깨지면 stage 1로 rollback

### 4. verifier
stage 3에서 verifier 또는 critic 역할을 가진 구성요소가
- 데이터 현실성
- 기술 구현 가능성
- 규제 / 법령 제약
- 사용자 피드백 반영 여부
를 확인하도록 설계한다.

### 5. multi-agent 확장
초기 MVP는 단일 workflow 중심으로 가되, 장기적으로는 다음과 같이 확장할 수 있다.
- planner agent
- retrieval agent
- verifier agent
- legal / risk agent
- report generator agent

## Codex CLI 연동 방향
모델 호출은 다음 구성으로 사용한다.
- model: gpt-5.5
- runtime: Codex CLI / `codex exec`
- test mode: fake command runner

실행 전략
- `CodexClient`가 `codex exec` 호출을 감싼다.
- Microsoft Agent Framework graph runner는 Codex client를 injectable dependency로 받는다.
- unit test와 발표 demo는 network를 호출하지 않는 explicit fake Codex client를 주입한다.
- 기본 runtime은 deterministic fallback 없이 Codex structured output 경로를 사용한다.
- 모델 호출 설정은 코드에 하드코딩하지 않고 YAML config에서 관리한다.

## 구현 구조에서의 위치
현재 레포 구조에서 Microsoft Agent Framework는 주로 backend orchestration 중심에 놓인다.

예상 매핑
- `app/backend/core/orchestrator.py`: workflow 진입점
- `app/backend/core/stage_manager.py`: stage 상태 관리
- `app/backend/core/rollback_manager.py`: rollback 조건과 대상 관리
- `app/backend/services/verifier_service.py`: stage 3 검증 로직
- `app/backend/services/report_service.py`: planner / engineer 출력 생성
- `app/backend/integrations/*`: retrieval, GitHub, 법령, MCP 연동

## YAML configuration과의 관계
이 프로젝트는 중복을 줄이기 위해 YAML configuration을 중심으로 움직인다.
Microsoft Agent Framework를 쓰더라도 아래 항목은 config에서 읽어야 한다.
- `stages.yaml`: stage 정의와 rollback target
- `scenarios.yaml`: 시나리오 정의
- `sources.yaml`: source category와 citation schema
- `prompts.yaml`: 에이전트별 stage prompt 경로
- `mcp-hub.yaml`: MCP source mapping
- `app.yaml`: 앱 전역 설정, 모델, Codex CLI runtime, demo state 설정

즉 프레임워크가 workflow 엔진 역할을 하더라도, 도메인 정의는 YAML이 source of truth가 된다.

## MVP 구현 원칙
초기 MVP에서는 프레임워크의 모든 기능을 다 쓰지 않는다.
우선 필요한 것만 쓴다.

우선 구현할 것
- single workflow graph
- stage state tracking
- approval checkpoint
- rollback path
- verifier step
- final report generation

나중에 붙일 수 있는 것
- multi-agent decomposition
- advanced memory behavior
- richer observability
- DevUI 고도 활용
- distributed orchestration

## 현재 선택 문장
이 프로젝트는 Microsoft Agent Framework를 기반으로, 라스트마일 서비스 기획 아이디어를 stage 기반 human-in-the-loop workflow로 구조화하고, 필요한 기반 기술과 검증 쟁점을 단계적으로 도출하는 planning agent system으로 구현한다.
