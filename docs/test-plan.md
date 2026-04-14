# 테스트 계획

이 문서는 팀 협업을 위한 구현 완료 기준을 정의한다.
핵심 원칙은 다음과 같다.

- 각 팀원은 자신이 맡은 모듈의 테스트를 통과시키는 것을 1차 목표로 한다.
- 전체 구현 완료는 핵심 테스트 케이스가 모두 통과하는 상태로 판단한다.
- 현재 일부 테스트는 아직 구현 전이므로 실패할 수 있으며, 이 실패가 곧 구현 TODO를 의미한다.

## 1. 테스트 철학

이 프로젝트의 테스트는 단순 회귀 확인용이 아니라, 협업 계약(contract) 역할을 한다.
즉 테스트는 아래를 정의한다.
- 어떤 객체와 함수가 존재해야 하는가
- 어떤 입력/출력을 가져야 하는가
- 어떤 stage 규칙을 만족해야 하는가
- 어떤 verifier/report/retrieval 동작이 최소 구현 범위인가

## 2. 팀원별 테스트 책임

### 팀원 1: 프론트엔드 / UX
직접 pytest 파일보다는 API contract와 mock response 구조를 기준으로 구현한다.
완료 기준:
- backend stage 응답 구조를 화면에 올바르게 렌더링
- approve / revise / rollback 동작을 UI에서 호출 가능
- planner report / engineer report / decision log 화면 제공

### 팀원 2: backend / orchestration
직접 책임 테스트:
- `tests/test_stage_manager.py`
- `tests/test_report_schema.py` 일부
- 필요 시 향후 `tests/test_api_routes.py`

완료 기준:
- stage 상태 전이
- 승인 규칙
- rollback 규칙
- 최종 보고서 생성 계약 만족

### 팀원 3: retrieval / MCP / 법령
직접 책임 테스트:
- `tests/test_retrieval_adapters.py`
- `tests/test_config_loader.py`

완료 기준:
- source category / citation schema 준수
- retrieval adapter 인터페이스 구현
- legalize-kr 경로 연결 가능
- config loader가 source / MCP / prompt 경로를 올바르게 읽음

### 팀원 4: prompt / verifier / evaluation
직접 책임 테스트:
- `tests/test_verifier.py`
- `tests/test_report_schema.py` 일부

완료 기준:
- verifier 결과 구조 정의
- rollback recommendation 로직 정의
- planner / engineer / decision log 출력 구조 만족

## 3. 테스트 파일별 의미

### `tests/test_config_loader.py`
목적:
- YAML config가 프로젝트의 single source of truth로 정상 로딩되는지 검증
- vLLM / Hugging Face / prompt 경로 / scenario / stage 정의를 읽는지 확인

### `tests/test_stage_manager.py`
목적:
- stage progression, approval, rollback 계약 검증
- stage 엔진의 최소 동작 보장

### `tests/test_verifier.py`
목적:
- verifier 출력 구조와 rollback recommendation 규칙 검증
- 데이터 부족 / 과도한 스코프 / KPI 불일치 같은 리스크 판단 기준 고정

### `tests/test_report_schema.py`
목적:
- planner report / engineer report / decision log가 최소 요구 필드를 만족하는지 검증

### `tests/test_retrieval_adapters.py`
목적:
- retrieval 결과가 source_type/title/locator/relevance_note를 포함하는지 검증
- source category와 legal adapter 연결 경로를 확인

## 4. 완료 판정 기준

다음 조건을 만족하면 “핵심 구현 완료”로 본다.
- config loader 테스트 통과
- stage manager 테스트 통과
- verifier 테스트 통과
- report schema 테스트 통과
- retrieval adapter 테스트 통과
- dispatch 시나리오 기준 stage 1 -> 4 경로가 동작
- rollback 경로 1개 이상 동작

## 5. 현재 상태 해석

현재 테스트 중 일부는 아직 구현이 없기 때문에 실패하도록 설계되어 있다.
이는 문제라기보다 구현 계약을 미리 고정한 상태로 보는 것이 맞다.

즉,
- 지금 실패하는 테스트 = 아직 구현되지 않은 약속
- 나중에 모두 통과하는 상태 = 협업 관점에서 구현 완료
