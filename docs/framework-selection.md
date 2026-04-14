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
- 로컬 vLLM 모델 연동

Microsoft Agent Framework는 저장소 설명과 README 기준으로 아래 특성을 전면에 둔다.
- graph-based workflows
- checkpointing
- human-in-the-loop
- time-travel
- multi-agent workflows
- Python/.NET 지원
- DevUI 기반 개발/디버깅 경험

즉, 단순 채팅 에이전트보다 workflow 중심 구조가 필요한 우리 프로젝트와 잘 맞는다.

## 이 프로젝트에서 기대하는 역할
Microsoft Agent Framework는 아래 역할을 담당한다.
- stage 1~4 흐름을 그래프 형태로 관리
- 각 stage의 승인 여부를 상태로 관리
- verifier 이후 rollback 가능 여부를 판단
- 나중에 retrieval agent, verifier agent, legal/risk agent 같은 멀티에이전트 확장 가능성 제공
- workflow 개발/디버깅 구조 제공

## 우리 프로젝트에 매핑되는 개념
### 1. stage workflow
프로젝트의 핵심 흐름은 아래와 같다.
- stage 1: 문제 정의 및 KPI 정렬
- stage 2: 서비스 구조 및 MVP 범위 설계
- stage 3: 기술/운영/규제 검증
- stage 4: 최종 planner/engineer output 생성

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
- 규제/법령 제약
- 사용자 피드백 반영 여부
를 확인하도록 설계한다.

### 5. multi-agent 확장
초기 MVP는 단일 workflow 중심으로 가되, 장기적으로는 다음과 같이 확장할 수 있다.
- planner agent
- retrieval agent
- verifier agent
- legal/risk agent
- report generator agent

이 확장은 지금 당장 필수는 아니지만, Microsoft Agent Framework를 쓰는 중요한 이유 중 하나다.

## 로컬 vLLM + Gemma 연동 방향
모델은 로컬에서 다음 구성으로 사용한다.
- model: google/gemma-4-26B-A4B-it
- serving: vLLM

실행 전략:
- vLLM을 OpenAI-compatible endpoint로 띄운다.
- Microsoft Agent Framework의 Python 쪽 모델 클라이언트 레이어에서 이 로컬 endpoint를 호출하도록 맞춘다.
- 모델 호출 설정은 코드에 하드코딩하지 않고 YAML config에서 관리한다.

즉 핵심은 특정 모델 전용 기능보다, OpenAI-compatible local endpoint와 잘 연결되는 구조를 유지하는 것이다.

## 구현 구조에서의 위치
현재 레포 구조에서 Microsoft Agent Framework는 주로 backend orchestration 중심에 놓인다.

예상 매핑:
- `app/backend/core/orchestrator.py`
  - workflow 진입점
- `app/backend/core/stage_manager.py`
  - stage 상태 관리
- `app/backend/core/rollback_manager.py`
  - rollback 조건과 대상 관리
- `app/backend/services/verifier_service.py`
  - stage 3 검증 로직
- `app/backend/services/report_service.py`
  - planner/engineer 출력 생성
- `app/backend/integrations/*`
  - retrieval, GitHub, 법령, MCP 연동

즉 frontend나 retrieval보다 backend orchestration 계층에서 가장 중요한 프레임워크다.

## YAML configuration과의 관계
이 프로젝트는 중복을 줄이기 위해 YAML configuration을 중심으로 움직인다.
Microsoft Agent Framework를 쓰더라도 아래 항목은 config에서 읽어야 한다.
- stages.yaml: stage 정의와 rollback target
- scenarios.yaml: 시나리오 정의
- sources.yaml: source category와 citation schema
- prompts.yaml: 공통 prompt 및 시나리오 overlay 경로
- mcp-hub.yaml: MCP source mapping
- app.yaml: 앱 전역 설정

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

즉 첫 단계에서는 workflow 엔진으로 쓰고, 이후 필요할 때 멀티에이전트 기능을 확장하는 전략이 적절하다.

## 팀 구현 관점에서의 장점
4인 팀 기준으로 보면 아래 장점이 있다.
- workflow와 state 개념이 분명해서 역할 분담이 쉽다.
- human approval과 rollback을 구조적으로 설명하기 좋다.
- stage-driven 프로젝트와 개념적으로 잘 맞는다.
- 장기적으로 multi-agent 확장 여지를 남긴다.
- 발표에서 "단순 챗봇"이 아니라 "agent workflow system"이라고 설명하기 좋다.

## 현재 선택 문장
이 프로젝트는 Microsoft Agent Framework를 기반으로, 라스트마일 서비스 기획 아이디어를 stage-based human-in-the-loop workflow로 구조화하고, 필요한 기반 기술과 검증 쟁점을 단계적으로 도출하는 planning agent system으로 구현한다.

## 다음 구현 단계
1. Microsoft Agent Framework의 Python workflow 기본 예제를 확인한다.
2. stage 1~4를 workflow graph로 매핑한다.
3. local vLLM endpoint를 연결한다.
4. FastAPI route를 workflow 실행 계층 위에 얹는다.
5. retrieval / verifier / report 모듈을 단계적으로 붙인다.
