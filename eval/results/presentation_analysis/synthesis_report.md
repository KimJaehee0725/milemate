# 단계별 기여도 & 실패 케이스 분석

## 1. 단계별 한계 기여 (각 단계가 실제로 무엇을 추가하는가)

### 1단계 → 2단계: 서비스 설계 추가 시

서비스 설계 단계의 핵심 기여는 **구조 완성**이다. 체크리스트 항목 중 가장 큰 점수 상승을 이끈 전환이다.

**D3-3 (운영정책 4요소 완비):** stages_1 B 문서는 정책 항목이 있어도 trigger/rule/owner/exception_handling 4요소가 불완전한 경우가 많았다. `merchant_prep_visibility` 시나리오에서 stages_2는 배차 권한 경계 정책에 4요소를 모두 채웠고, `failed_delivery_risk`에서는 출고 보류 금지 정책과 민감 속성 배제 정책을 신규로 추가하면서 4요소 구조를 완비했다.

**D3-4 (데이터 필드 명세 완전성):** `rider_onboarding_dropout`에서 stages_1은 2/3 시드에서 D3-4 partial이었는데, stages_2가 필드 목록을 ~13개에서 16개 이상으로 확장하면서 매니저 연락 가능 슬롯, 권장 연락 멘트 라이브러리를 포함한 모든 항목에 source/purpose/freshness/quality_rule 4속성을 완비했다. `merchant_prep_visibility`에서는 API 필드명(expected_ready_at, confidence, expires_at, source, apply_mode)이 처음으로 명시됐다.

**D4-1/D4-2/D4-3 (KPI 구조화):** `merchant_prep_visibility`에서 stages_1 B는 KPI별 baseline이 없었지만 stages_2가 'MVP 시작 전 최근 4주 주문 이벤트로 기준값 산출'이라는 측정 계획과 함께 담당자를 per-KPI로 할당했다. `dispatch_recommendation`에서는 보상 비용 산식 예시(1,000×8%×20%×3,000원)를 '예측치가 아닌 산식 검증용'으로 명시해 D8-2 한 시드가 fail에서 pass로 전환됐다.

**한계:** stages_2는 동시에 새로운 문제를 도입한다. `eta_prediction`에서 서비스 설계가 주문당 35~50건 처리량, 150~250건/일 상한 같은 정밀 운영 수치를 출처 없이 추가해 D8-2가 1/3 pass에서 0/3 pass로 전면 후퇴했다. `checkout_fee_transparency`에서도 15%/10%/99.5% 임계값이 근거 없이 도입됐다.

---

### 2단계 → 3단계: 타당성 검증 추가 시

타당성 검증 단계는 **개념적 신규성과 품질 퇴행이 동시에 일어나는 가장 복잡한 전환**이다.

**개념적 추가:** `failed_delivery_risk`에서 '개입 등급(intervention grade)'이 위험 점수와 별도 차원으로 도입됐다. 단일 확률값이 아니라 위험 점수+신뢰도+예상 예방 금액+고객 연락 피로도+상담 슬롯+개인정보 제한을 종합한 다요소 추천 등급으로 발전했고, shadow mode 구조(2주 백테스트→2주 섀도→4주 실제 적용)가 공식화됐다. `return_pickup_flow`에서는 capacity ledger가 처음으로 명세됐다: `pickup_capacity_bucket`에 total_capacity, hold_count, buffer_capacity, cutoff_at, capacity_version(낙관적 잠금용)이 모두 명시됐고, 확정 예약과 구별되는 2단계 보류(reservation_hold)가 race condition 해결책으로 구체화됐다.

**D5 계열 (가드레일) 개선:** `cs_repeat_inquiry_triage`에서 stages_3는 '오답률 2% 초과 또는 재문의율 기준선 대비 3%p 초과 시 의도별 중지'라는 구체적 stop 조건을 도입했다. `merchant_prep_visibility`에서는 '허위 신호율 10% 초과 또는 위험 신호 100건당 5건 분쟁 시 자동 중단' 같은 수치 기반 circuit breaker가 처음 등장해 D5-3을 패스시켰다. `rider_onboarding_dropout`에서는 contact_gate_status enum(allowed/reduced/deferred_data/suppressed_consent/suppressed_frequency/blocked_privacy/capacity_deferred)이 신규 도입돼 MVP 실현 가능성 조건을 구조화했다.

**퇴행 패턴:** `dispatch_recommendation`에서 stages_3는 85% 위치 수신률, 2초 갱신 같은 새 수치를 근거 없이 추가해 D8-2에 P3 패널티를 발생시켰다. 이전 stages_2 평균 점수 30.67보다 stages_3 평균 30.50이 낮아졌다. `cs_repeat_inquiry_triage`에서는 참고 자료 섹션에 시나리오 무관한 'source_type: news_report' 보일러플레이트만 채운 P2 패널티가 새로 생겼다. `rider_onboarding_dropout`에서는 contact_gate enum의 한영 명칭 불일치(연락 가능 vs allowed, 연락 억제 vs suppressed_consent)로 D6-2 내부 일관성이 partial로 하락했다.

---

### 3단계 → 4단계: 최종화 추가 시

최종화 단계는 **시나리오별로 방향이 갈리는 가장 이질적인 전환**이다. 일부 시나리오에서는 의미 있는 개발 핸드오프 자료를 추가하지만 다른 시나리오에서는 점수 하락을 초래한다.

**긍정적 기여:** `cs_repeat_inquiry_triage`에서 최종화는 D8-2 전면 해결이라는 가장 큰 단일 항목 개선을 이뤄냈다. 메커니즘은 명시적 인식론적 레이블이었다: '신뢰도 0.90'이라는 주장 대신 'baseline: 현재 미계측; 출시 전 최근 1주 수동 큐 로그로 산정', '기준값은 운영 초안이며, 최근 4주 로그 드라이런으로 조정해야 한다'는 문구를 사용해 3/3 시드 모두 pass로 전환했다. `failed_delivery_risk`에서는 '개입 상태 판정'을 5개 상태값(즉시 개입/보류/억제/수동 검토/처리 완료)으로 열거한 상태 기계로 구체화했고, 순개입가치 임계값 UI 파라미터와 before/after 시뮬레이션 미리보기까지 명세했다. `dispatch_recommendation`에서는 추천 API 반환 필드(reason_codes, reason_text_version, data_freshness_status, eta_delta_minutes, load_delta, cost_risk_estimate)가 영문 field_name으로 표준화됐다.

**퇴행 사례:** `return_pickup_flow`에서 stages_4는 문서 목적을 제품 PRD에서 개발 산정 회의 자료로 전환했다('stage_goal: 개발 산정 질문지 준비'). 그 결과 평균 점수가 stages_3의 31.33에서 29.33으로 2점 하락했고, D3-4(reverse_status_timeline의 source 필드 누락), D4-3(신규 KPI에 owner 없음), D6-1(개발 견적 확정률이 운영 문제 KPI와 무관), D6-3(개인정보 정책-설계 불일치) 네 항목이 동시에 퇴행했다. `dispatch_recommendation`에서도 stages_4 평균(29.67)이 stages_3(30.50)보다 낮았고, '위험도 87점', '반경 1.1km', '7분 단축' 같은 시나리오 예시 수치가 근거 없이 도입됐다.

---

## 2. 파이프라인의 구조적 강점 (1단계만으로도 이미 크게 개선되는 영역)

stages_1(문제정의 + output_layer 합성)만으로 A를 압도하는 영역이 세 가지 있다.

**D7-1/D7-2 (의사결정 거버넌스):** 전체 8개 시나리오, 3개 시드에서 A는 D7-1(결정 안건 완결성) 평균 0.25, D7-2(미해결 질문 추적) 평균 0.27이다. B stages_1은 두 항목 모두 1.00에 근접한다. A는 결정 안건에 선택지 2개 이상과 결정 주체를 붙이지 않고, 열린 질문에 답변 주체와 기한을 붙이지 않는다. 이는 output_layer가 decision_agenda 구조(6개 토픽, 각 2개 이상 선택지, decision_owner)와 open_questions 구조(owner, needed_by 포함)를 problem definition만으로도 생성하기 때문이다. 일회성 생성 방식으로는 이 거버넌스 구조가 자연스럽게 나오지 않는다는 점이 B의 근본적 우위다.

**D4-3 (KPI 담당 주체):** A 전체 평균 0.00, B 최대 +0.96 절대 이득. A는 KPI 표에 담당 주체 열 자체가 없다. B stages_1은 이미 per-KPI owner 할당이 기본 구조에 포함돼 있다.

**D3-2/D3-3 (예외처리 및 운영정책):** A 평균 0.50, B stages_1에서 1.00 근접. `dispatch_recommendation` 시나리오에서 stages_1은 체크리스트 31/32개 항목을 pass 수준으로 달성하는 강력한 기준선을 즉시 형성했다. 빈 상태/오류 상태가 있는 화면 3개, 트리거/담당자/예외가 있는 정책 6~8개, 기준/목표/측정/담당자가 있는 KPI 7개, 속성이 있는 이벤트 로그 8개가 문제 정의만으로 생성됐다. 구조 완전성의 대부분은 단계 수가 아니라 output_layer 합성에서 기인한다.

---

## 3. 실패 케이스 분석 — A가 이긴 이유

**공통 패턴 요약:** A가 이긴 4개 케이스 모두 동일한 구조적 실패 클러스터를 공유한다. B 파이프라인이 개념적 정교화를 추가할 때마다 기존 구조 항목(KPI owner, 결정 선택지, 질문 기한)을 채우지 않고 넘어갔다.

**케이스 1 — checkout_fee_transparency / seed1 / stages_1~3 (3조건 전패):**
A는 초기 단회 출력에서 D4-3(KPI owner), D7-1(결정 선택지 2개 이상), D7-2(질문 owner+deadline)를 모두 패스했다. B는 3개 단계 내내 이 세 항목을 실패했다. B가 각 단계에서 추가한 것은 개념적 심화였다: stages_1은 위험 주문 한정 범위, stages_2는 quote_id 결제 정합성 아키텍처, stages_3는 fee_exposure_mode 신뢰도 기반 3-tier 공개 게이트. 판사는 이 개념적 심화를 보상하지 않고 구조 미완성을 하드 fail로 처리했다. 유일하게 B가 A를 앞선 항목은 D8-2의 Baymard 인용이었지만 (stages_2 B가 D1-2 Baymard 70.22% 인용으로 pass) 나머지 D1-3, D4-3, D7-1 실패가 이를 상쇄했다.

**케이스 2 — rider_onboarding_dropout / seed3 / stages_1~2 (2조건 패배):**
이 케이스는 역설적이다. A(일회성 기준선)가 D1-3(현재 수동 우회 방법 기술), D4-3(KPI owner), D7-2(질문 owner+deadline)에서 B를 앞섰다. B stages_1과 stages_2 모두 현재 수동 우회 방법 설명이 빠졌고, KPI owner가 없었으며, 질문에 답변 주체와 기한이 없었다. stages_2는 추가로 시나리오 무관 참고 자료 섹션(P2 패널티)을 생성했다. 파이프라인이 구조 슬롯을 채우지 않은 채 내용 볼륨을 키운 전형적 사례다.

**케이스 3 — dispatch_recommendation / seed1 / stage_3 (1조건 패배):**
stages_3에서 B는 수요·공급 스트레스 관제 화면과 추천 신뢰 게이트라는 정교한 개념을 추가했지만 D4-3(KPI owner 없음), D7-1(결정 선택지 없음), D7-2(질문 owner·deadline 없음)을 여전히 실패했다. A는 P1(자동화 경계 3회 이상 반복), P2(일반 참고 자료), P3(미근거 수치 2건) 패널티를 받았지만 B보다 패널티가 많음에도 구조 통과 항목이 더 많았다. 패널티 수가 적어도 하드 fail 항목이 있으면 지는 구조다.

**케이스 4 — return_pickup_flow / seed3 / stage_4 (1조건 패배):**
stages_4가 문서 유형 자체를 바꿨다. stage_goal이 '개발 산정 회의 자료 준비'로 설정되고 implementation slice_0이 '개발 산정 워크숍 준비'로 시작하면서 체크리스트가 평가하는 화면 명세, 이벤트 로그, 정책 4요소, KPI owner, 열린 질문 책임 구조가 모두 제품 의도 프레임을 전제하는데, 공학 산정 프레임으로 전환된 문서는 이를 충족할 수 없었다. A는 D6-3 실패([프로세스] 플레이스홀더)와 P1/P3 패널티가 있었지만 B보다 구조 통과 항목이 많았다.

**파이프라인의 구조적 맹점:** 각 단계는 이전 단계 출력 위에 새 개념 레이어를 추가하도록 설계돼 있다. 하지만 기존 구조 항목(KPI owner, 결정 선택지 2개 이상, 질문 owner+기한, 정책 4요소, 이벤트 스키마 3속성)이 채워져 있는지 감사하는 단계가 없다. 체크리스트는 미완성 구조를 partial이 아닌 hard fail로 처리하기 때문에, 개념적으로 정교한 후기 단계 문서가 단순하지만 구조가 완전한 A에게 진다.

---

## 4. 파이프라인의 구조적 약점

**D8-2 (수치 출처 추적) — 전 단계 미해결:** D8-2는 A 평균 0.08, B 최고 0.29로 두 시스템 모두 약하지만 B도 어떤 단계도 일관되게 해결하지 못한다. `merchant_prep_visibility`에서는 4개 조건 24개 시드 전부 fail이었다. 각 단계가 추가하는 정밀 수치(신뢰도 임계값, 지연 임계값, 샘플 크기 하한, 오류율 차단기)가 출처나 가정 없이 등장하는 게 패턴이다. `dispatch_recommendation`의 '30초 이내 노출', `eta_prediction`의 '신뢰도 0.65', `checkout_fee_transparency`의 'predicted_delta_abs ≤500원'이 모두 같은 구조적 패턴이다. 유일하게 D8-2를 전면 해결한 사례는 `cs_repeat_inquiry_triage` stages_4인데, 수치를 제거한 게 아니라 'baseline: 현재 미계측; 드라이런으로 조정' 같은 인식론적 레이블을 붙여 해결했다. 이 접근법이 다른 시나리오에 전파되지 않은 것은 파이프라인에 수치 주장 출처 검증 전용 패스가 없기 때문이다.

**단계 추가가 순수한 개선을 보장하지 않는 패턴:** 전체 ablation에서 stages_3 평균이 stages_2보다 낮은 시나리오가 복수 존재한다. `dispatch_recommendation`에서 stages_2(30.67) → stages_3(30.50) → stages_4(29.67)로 단계가 늘수록 점수가 하락했다. `return_pickup_flow`에서 stages_3(31.33) → stages_4(29.33)로 2점 하락했다. 이는 후기 단계일수록 ① 미근거 수치 증가(D8-2 P3 패널티), ② 내용 반복 증가(D8-1 P1 패널티), ③ 새 KPI 추가 시 owner 누락(D4-3 퇴행) 패턴이 누적되기 때문이다.

**D4-3 불안정성:** D4-3는 stages_2에서 거의 완성되지만 stages_3이나 stages_4에서 새 KPI가 추가될 때 owner 없이 도입돼 퇴행한다. `eta_prediction` stages_4에서 '알림 피로 방어 지표' KPI에 owner가 빠져 3/3 시드 모두 partial로 고착됐다. `dispatch_recommendation` stages_4에서 '고객 안내 선제율' KPI의 owner가 누락됐다. 신규 KPI 추가 시 owner 필드를 강제하는 메커니즘이 파이프라인에 없다.

**P1 반복 패널티 미해결:** 파이프라인 전반에 걸쳐 핵심 제약 조건(자동 발송 금지, 자동 배차 제외 등)이 3개 이상 섹션에 반복된다. `cs_repeat_inquiry_triage`에서 '승인된 템플릿만 사용' 조건이 stages_4 전 시드에서 3개 이상 섹션에 verbatim 반복됐다. `return_pickup_flow`에서 '신규 배달원 앱 없음' 조건이 stages_4 doc1에 P1 패널티를 발생시켰다. output_layer 합성 프롬프트가 안전 가드레일 언어를 중복 제거하지 않는 구조적 문제다.

---

## 5. 발표용 핵심 메시지 (PPT 슬라이드 bullet 5개)

- **1단계(문제정의 + output_layer)만으로 B는 24쌍 중 22~23승을 확보한다** — 구조 완전성(D7-1 결정 선택지, D7-2 질문 책임, D4-3 KPI owner)이 일회성 GPT에 없고 파이프라인의 output_layer에 내장돼 있기 때문이며, 이후 단계 추가는 콘텐츠 심화이지 승패를 바꾸는 요인이 아니다.

- **서비스 설계(2단계)가 가장 안정적인 한계 이득을 낸다** — D3-3(정책 4요소), D3-4(데이터 필드 명세), D4-1/D4-2/D4-3(KPI 구조화) 전반에서 8개 시나리오 중 6개 이상에서 명확한 pass 전환이 일어나며, 이 단계의 기여는 일관적이고 다른 단계와 달리 시나리오 의존성이 낮다.

- **타당성 검증(3단계)은 개념적 신규성을 추가하지만 품질이 mixed다** — `return_pickup_flow`의 capacity ledger, `failed_delivery_risk`의 개입 등급, `eta_prediction`의 shadow mode처럼 PRD의 운영 깊이를 높이지만, 동시에 미근거 수치 증가(D8-2 P3), 내부 일관성 위반(D6-2), 반복 패널티(P1) 패턴도 함께 도입한다.

- **D8-2(수치 출처 추적)는 어떤 단계도 체계적으로 해결하지 못하는 파이프라인 전체의 구조적 공백이다** — 예외는 `cs_repeat_inquiry_triage` stages_4뿐이며, 이 케이스가 성공한 메커니즘(수치 제거가 아니라 '미계측/드라이런 조정' 레이블 부착)은 나머지 7개 시나리오에 전파되지 않았다; 수치 주장 출처 검증 전용 패스가 파이프라인에 없다는 증거다.

- **A가 이긴 4개 케이스의 공통 원인은 단 하나다** — B가 개념 레이어를 추가할 때 기존 구조 슬롯(KPI owner, 결정 선택지 2개 이상, 질문 기한)을 채우지 않고 넘어갔고, 체크리스트는 이를 hard fail로 처리한다; 파이프라인에 구조 완전성 감사(completeness audit) 단계가 추가돼야 이 패턴이 해소된다.
