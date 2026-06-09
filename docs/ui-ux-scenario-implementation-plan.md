# UI/UX 개선 & 시나리오 풍부화 구현 계획

> 브랜치: `feat/ui-ux-scenario` · 워크트리: `../taste-of-text-ui-ux`
> 작성 기준일: 2026-06-02
> 목적: 각 작업을 약 3분 단위 원자 작업으로 쪼개 두어 나중에 순서대로 따라가기만 하면 구현이 끝나도록 한다.

---

## 0. 핵심 배경 (구현 전 반드시 숙지)

### 0.1 데모 데이터 흐름 (발표에서 실제로 타는 경로)
프론트엔드는 기본 `MILEMATE_API_MODE` 환경값에 따라 동작하지만, 오프라인 데모/스모크는
`LocalDemoAPI` → `MilemateAgentGraphRunner(codex_client=LocalFakeCodexClient())`를 탄다.

```
LocalFakeCodexClient.generate_stage_output()
  stage_1, stage_2 → PlannerService.build_stage_output()
  stage_3          → VerifierService.build_stage_output()
  stage_4          → ReportService.build_stage_output()
        └ 모두 내부에서 build_demo_prd_packet() 호출
```

> ⚠️ 현재 `PlannerService` / `build_demo_prd_packet` / `VerifierService`는 **dispatch 시나리오 언어로 하드코딩**되어 있다.
> eta_prediction / failed_delivery_risk 를 선택해도 동일한 dispatch 텍스트가 나온다.
> **시나리오 풍부화의 핵심 = 이 세 서비스를 시나리오별로 분기**하는 것.

### 0.2 설정 스키마 제약
- `config_loader.ScenarioDefinition` 은 `label / primary_users / primary_kpis / core_data` 만 가진다.
- Pydantic v2 기본값이 `extra="ignore"` 라, `scenarios.yaml`에 새 필드를 넣어도 **백엔드에선 조용히 무시**된다.
- 프론트엔드(`load_scenarios()`)는 `yaml.safe_load`로 직접 읽으므로 새 필드를 볼 수 있다.
- 백엔드에서도 새 필드를 쓰려면 `ScenarioDefinition`을 확장해야 한다. (Phase 1)

### 0.3 검증 명령 (각 Phase 종료 시 실행)
```bash
cd ../taste-of-text-ui-ux
uv run pytest -q
uv run ruff check .
uv run python -m py_compile app/frontend/streamlit_app.py
```

### 0.4 작업 4대 축
- **A. 시나리오 풍부화** (기존 3종 상세화) — Phase 1~3
- **B. Stage 진행 시각화** — Phase 5
- **C. Stage 결과 표시** — Phase 4, 6
- **D. 최종 리포트 화면** — Phase 7

---

## Phase 1 — 시나리오 데이터 레이어 (≈ 21분)

데이터를 한 곳(YAML + 스키마)에서 시나리오별로 들고 있게 만든다.

- [ ] **1.1 (3분)** `config/scenarios.yaml` 신규 필드 확정 검토
  - 이미 추가됨: `label_ko / description / pain_points / kpi_targets`.
  - 3개 시나리오 모두 동일 키 세트를 갖는지, 들여쓰기/오타 점검.
  - 검증: `uv run python -c "import yaml; yaml.safe_load(open('config/scenarios.yaml'))"`

- [ ] **1.2 (3분)** `config_loader.ScenarioDefinition` 확장
  - 위치: `app/backend/core/config_loader.py:114`
  - 필드 추가:
    ```python
    label_ko: str = ""
    description: str = ""
    pain_points: List[str] = Field(default_factory=list)
    kpi_targets: Dict[str, str] = Field(default_factory=dict)
    ```
  - `Dict`는 이미 import 되어 있음(typing) — 확인만.

- [ ] **1.3 (3분)** `ScenarioDefinition`에 헬퍼 프로퍼티 추가 (선택)
  - `display_label`: `label_ko or label` 반환하는 `@property`.
  - 프론트/백엔드가 한국어 라벨을 일관되게 쓰도록.

- [ ] **1.4 (3분)** `data/demo_inputs/dispatch.json` 확장
  - 현재: `{scenario, title}` 뿐.
  - 추가 키: `title`(한국어로 교체), `context`(1~2문장 상황), `data_sources`(리스트), `constraints`(리스트).
  - `data_sources`는 `verification_context_for_preset`가 stage_3에서 사용 → 시나리오별 검증 현실성 ↑.

- [ ] **1.5 (3분)** `data/demo_inputs/eta.json` 동일 구조로 확장
  - `data_sources` 예: `["live_location", "travel_history", "delay_logs"]`.

- [ ] **1.6 (3분)** `data/demo_inputs/failed_delivery.json` 동일 구조로 확장
  - `data_sources` 예: `["failed_delivery_logs", "customer_response_history", "intervention_logs"]`.

- [ ] **1.7 (3분)** Phase 1 검증
  - `uv run python -c "from app.backend.core.config_loader import reload_app_config; reload_app_config()"` 무에러 확인.
  - `get_scenario_definition('eta_prediction').description` 값이 나오는지 한 줄 확인.

---

## Phase 2 — 시나리오 콘텐츠 프로파일 모듈 신설 (≈ 24분)

백엔드 서비스의 if/else 폭발을 막기 위해, 시나리오별 한국어 copy를 한 모듈에 모은다.

- [ ] **2.1 (3분)** 새 파일 생성: `app/backend/services/scenario_profiles.py`
  - 모듈 docstring + 타입 정의(`from __future__ import annotations`, `from typing import Any, Dict, List`).

- [ ] **2.2 (3분)** 프로파일 자료구조 설계 (dict 스키마 주석으로 명시)
  - 각 시나리오 키 → dict:
    ```
    {
      "one_page_focus": str,        # PRD 한 장 요약 도입부
      "customer_pain": str,
      "business_impact": str,
      "current_workaround": str,
      "success_criteria": List[str],
      "personas": List[{name, role, needs:List[str]}],
      "scope_in": List[str], "scope_out": List[str],
      "screen": {name, purpose, components, primary_actions, ...},
      "policy": {name, trigger, rule, owner, exception_handling},
      "metrics": List[{name, baseline, target, measurement, owner}],
      "stage1_scope_candidates": List[str],
      "stage2_in_scope": List[str], "stage2_out_scope": List[str],
      "stage2_open_questions": List[str],
      "verify_guardrails": List[str],
    }
    ```

- [ ] **2.3 (3분)** `dispatch_recommendation` 프로파일 작성
  - 현재 `prd_packet_factory`/`planner_service`에 하드코딩된 dispatch 텍스트를 **그대로 이전**(원본 보존).

- [ ] **2.4 (3분)** `eta_prediction` 프로파일 작성 (고객 알림/지연 안내 관점 copy)
  - customer_pain: ETA 신뢰·지연 안내 지연. screen: "지연 위험 주문 알림 콘솔" 등.

- [ ] **2.5 (3분)** `failed_delivery_risk` 프로파일 작성 (실패 예측/사전 개입 관점 copy)
  - screen: "실패 위험 주문 검토 큐" 등. policy: 자동 연락 금지·상담팀 확인 우선.

- [ ] **2.6 (3분)** 접근 헬퍼 함수 추가
  - `get_scenario_profile(scenario: str) -> Dict[str, Any]`
  - 미존재 시 `dispatch_recommendation` 폴백 + 빈 키 안전 접근.

- [ ] **2.7 (3분)** 단위 점검용 임시 스크립트로 3종 프로파일 키 일치 확인
  - `set(eta.keys()) == set(dispatch.keys())` 등. 확인 후 임시 코드 제거.

- [ ] **2.8 (3분)** Phase 2 검증: `uv run ruff check app/backend/services/scenario_profiles.py`

---

## Phase 3 — 백엔드 서비스 시나리오 인식화 (≈ 27분)

프로파일을 실제 출력에 연결한다. **여기까지 끝나면 시나리오 풍부화(A)의 백엔드가 완성**된다.

- [ ] **3.1 (3분)** `prd_packet_factory.build_demo_prd_packet`에 프로파일 주입 (1) — import & 로드
  - `from app.backend.services.scenario_profiles import get_scenario_profile`
  - 함수 시작부에서 `profile = get_scenario_profile(scenario)`.

- [ ] **3.2 (3분)** `build_demo_prd_packet` (2) — `one_page_summary` / `problem` 치환
  - 하드코딩 dispatch 문장을 `profile["customer_pain"]` 등으로 교체. `label`은 기존대로 사용.

- [ ] **3.3 (3분)** `build_demo_prd_packet` (3) — `personas` / `scope` 치환
  - `profile["personas"]`, `profile["scope_in"]`, `profile["scope_out"]` 사용.

- [ ] **3.4 (3분)** `build_demo_prd_packet` (4) — `screens` / `policies` / `metrics` 치환
  - 시나리오별 화면명·정책·KPI가 나오도록.

- [ ] **3.5 (3분)** `build_demo_prd_packet` (5) — `event_logs` / `implementation_slices` 점검
  - 이벤트명에 시나리오 식별자 prefix(예: `eta_`, `failed_`)가 들어가게.

- [ ] **3.6 (3분)** `planner_service._stage_1` 시나리오 인식화
  - `problem_summary` / `scope_candidates` / `engineer_view`를 프로파일 기반으로.
  - dispatch 외 시나리오에서 dispatch 단어가 안 나오는지 확인.

- [ ] **3.7 (3분)** `planner_service._stage_2` 시나리오 인식화
  - `mvp_in_scope` / `mvp_out_of_scope` / `open_questions`를 `profile["stage2_*"]`로.

- [ ] **3.8 (3분)** `verifier_service` 시나리오 인식화
  - `implementation_guardrails`를 `profile["verify_guardrails"]`로.
  - scope 위험 감지 키워드를 시나리오별로 보정(예: eta는 `notification`, failed는 `intervention`).

- [ ] **3.9 (3분)** Phase 3 통합 검증
  - 임시 스크립트로 3종 시나리오 stage_1~4 출력 생성 후 `one_page_summary` 첫 60자 출력 → 서로 다른지 눈으로 확인.
  - `uv run pytest -q` 통과(기존 dispatch 테스트가 깨지면 3.2~3.4의 dispatch 프로파일이 원본과 다른 것 → 맞춤).

---

## Phase 4 — UI: 사이드바 시나리오 정보 카드 (C) (≈ 12분)

선택한 시나리오의 맥락/페인포인트/KPI 목표를 한눈에.

- [ ] **4.1 (3분)** `streamlit_app.py`에 `render_scenario_info(scenario_meta: Dict)` 함수 추가
  - 위치: 다른 `render_*` 함수 근처(예: `render_session` 위).
  - `st.caption(description)` + pain_points 불릿 + kpi_targets 표.

- [ ] **4.2 (3분)** 사이드바에 카드 연결
  - 위치: `with st.sidebar:` 블록 내 `verification_preset` 아래.
  - `render_scenario_info(scenarios[scenario_id])` 호출. `with st.expander("시나리오 개요", expanded=False)` 권장.

- [ ] **4.3 (3분)** KPI 목표 표 렌더 헬퍼
  - `kpi_targets` dict → `[{"KPI": k, "목표": v}]` 변환 후 `st.dataframe(..., hide_index=True)`.
  - `format_label`에 신규 KPI 키 한글 라벨 추가(`delay_rate→지연률` 등).

- [ ] **4.4 (3분)** Phase 4 검증: `uv run python -m py_compile app/frontend/streamlit_app.py`

---

## Phase 5 — UI: Stage 진행 시각화 (B) (≈ 18분)

라디오 버튼을 시각적 stepper/timeline으로 교체(선택 기능은 유지).

- [ ] **5.1 (3분)** 상태→색/아이콘 매핑 상수 추가
  - 모듈 상단: `STAGE_STATUS_STYLE = {"승인 완료": ("✅","#1a7f37"), "승인 대기": ("🕓","#9a6700"), "작업 중": ("🔵","#0969da"), "생성 완료": ("◽","#57606a"), "대기": ("⚪","#8c959f")}`.

- [ ] **5.2 (3분)** stepper용 CSS 블록 추가
  - 기존 `st.markdown("<style>...</style>")` 안에 `.stage-stepper`, `.stage-step`, `.stage-connector`, 상태 클래스 추가.

- [ ] **5.3 (3분)** `render_stage_stepper(session)` HTML 생성 함수 작성
  - 4개 step을 flex로 가로 배치, 각 step에 번호/제목/상태 배지/연결선.
  - `stage_status()` 재사용.

- [ ] **5.4 (3분)** `render_stage_navigator` 리팩터
  - 상단에 `render_stage_stepper(session)` 표시.
  - 기존 라디오는 `label_visibility="collapsed"`로 유지하거나, step별 `st.button`으로 선택 구현(라디오 제거 시 selected_stage_id 동기화 주의).
  - 안전 우선: 라디오 유지 + 시각 stepper를 위에 추가하는 방식 권장.

- [ ] **5.5 (3분)** 카드 그리드(기존 `cols`)와 stepper 중복 제거
  - 둘 중 하나만 남겨 화면 정리. stepper를 메인으로.

- [ ] **5.6 (3분)** Phase 5 검증: py_compile + 로컬 실행 시 4단계 색 변화 육안 확인(approve 후 색 전이).

---

## Phase 6 — UI: Stage 결과 표시 개선 (C) (≈ 12분)

- [ ] **6.1 (3분)** 산출물 헤더에 상태 배지 추가
  - `render_stage_output` 상단에 현재 stage 상태(`stage_status`) 컬러 배지(markdown+CSS span).

- [ ] **6.2 (3분)** 메트릭 카드 라벨/도움말 보강
  - 기존 5개 `st.metric`에 `help=` 추가, PRD 품질은 status 텍스트(ready/needs_review) 함께.

- [ ] **6.3 (3분)** verifier 상태(통과/주의) 강조
  - stage_3일 때 `planner_view.verifier_status` → `st.success`/`st.warning` 배너.

- [ ] **6.4 (3분)** Phase 6 검증: py_compile + 3단계 검증 프리셋(Missing data 등) 전환 시 배너 변화 확인.

---

## Phase 7 — UI: 최종 리포트 화면 개선 (D) (≈ 15분)

- [ ] **7.1 (3분)** 리포트 상단 요약 카드 행 추가
  - `render_report` 첫머리에 `st.columns(4)`: 결정 이력 수 / 리스크 수 / 근거 수 / PRD 품질.

- [ ] **7.2 (3분)** 한 장 요약 하이라이트 박스
  - `prd_report.one_page_summary`를 `st.container(border=True)` + 강조 마크다운으로 상단 배치.

- [ ] **7.3 (3분)** 탭 구조 정리
  - 기존 4탭 유지하되 "PRD 보고서" 탭을 sub-section(요약/실행/데이터/전달)으로 명확히 구획(`st.divider`).

- [ ] **7.4 (3분)** 리스크/결정 이력 색상 표 적용
  - `rows_for_risks` 결과에 severity 한글 라벨 강조(이미 있음) — 빈 경우 안내문 통일.

- [ ] **7.5 (3분)** Phase 7 검증: stage_4 승인까지 진행 → 리포트 PDF/JSON 다운로드 정상 동작 확인.

---

## Phase 8 — 테스트 & 회귀 검증 (≈ 15분)

- [ ] **8.1 (3분)** `tests/test_frontend_demo_data.py` 확장
  - 신규 demo_inputs 키(`context`, `data_sources`) 존재 검증 추가.

- [ ] **8.2 (3분)** 시나리오 인식 테스트 신설: `tests/test_scenario_profiles.py`
  - 3종 프로파일 키 일치, `get_scenario_profile` 폴백 동작.

- [ ] **8.3 (3분)** planner/verifier 시나리오 분기 테스트
  - eta/failed 출력의 `one_page_summary`가 dispatch와 다름을 assert.

- [ ] **8.4 (3분)** `tests/test_streamlit_app.py` 스모크 갱신
  - 새 함수(`render_scenario_info`, `render_stage_stepper`) import/실행 깨짐 없는지.

- [ ] **8.5 (3분)** 전체 검증
  - `uv run pytest -q && uv run ruff check . && uv run python -m py_compile app/frontend/streamlit_app.py`

---

## Phase 9 — 시연 확인 & 커밋 (≈ 12분)

- [ ] **9.1 (3분)** 로컬 데모 기동
  - `MILEMATE_API_MODE=local uv run --extra ui streamlit run app/frontend/streamlit_app.py`

- [ ] **9.2 (3분)** 3종 시나리오 각각 stage 1→4 클릭 시연
  - 시나리오별 텍스트 차이 / stepper 색 전이 / 리포트 요약 카드 육안 확인.

- [ ] **9.3 (3분)** rollback 1회 시연 (3단계 Missing data 프리셋 → stage_1 롤백)
  - 색/상태 원복 확인.

- [ ] **9.4 (3분)** 커밋 (사용자 승인 후)
  - 논리 단위로 커밋 권장: (1) 시나리오 데이터/백엔드, (2) UI 개선.
  - 메시지 예: `feat: enrich scenarios with per-scenario content profiles`, `feat: improve stage progress and report UI`.

---

## 부록 — 파일별 변경 요약 (구현 시 빠른 참조)

| 파일 | 변경 내용 | Phase |
|------|-----------|-------|
| `config/scenarios.yaml` | 한국어 라벨/설명/페인포인트/KPI목표 (완료) | 1.1 |
| `app/backend/core/config_loader.py` | `ScenarioDefinition` 필드 4개 확장 | 1.2~1.3 |
| `data/demo_inputs/*.json` | context/data_sources/constraints 확장 | 1.4~1.6 |
| `app/backend/services/scenario_profiles.py` | **신규** 시나리오 copy 프로파일 | 2 |
| `app/backend/services/prd_packet_factory.py` | 프로파일 기반 PRD 생성 | 3.1~3.5 |
| `app/backend/services/planner_service.py` | stage1/2 시나리오 분기 | 3.6~3.7 |
| `app/backend/services/verifier_service.py` | guardrail/위험 시나리오 분기 | 3.8 |
| `app/frontend/streamlit_app.py` | 시나리오 카드/stepper/배지/리포트 | 4~7 |
| `tests/*` | 신규 + 회귀 테스트 | 8 |

## 부록 — 리스크 & 주의사항
- **테스트 회귀**: dispatch 텍스트를 프로파일로 옮길 때 기존 assert 문자열이 깨질 수 있음 → 3.3에서 원본 보존이 핵심.
- **Streamlit 라디오 ↔ stepper 동기화**: `selected_stage_id` session_state를 한 곳에서만 갱신. 라디오 제거 시 버그 위험 → 5.4에서 라디오 유지 권장.
- **config 캐시**: `load_app_config`는 `@lru_cache`. 스키마 수정 후엔 프로세스 재시작 또는 `reload_app_config()`.
- **PDF 폰트**: 한글 폰트 경로는 로컬 의존(`PDF_FONT_CANDIDATES`). 시연 머신에 NanumGothic/Pretendard 설치 확인.
