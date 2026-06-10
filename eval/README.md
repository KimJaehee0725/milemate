# 평가 파이프라인 실행 런북 (eval/)

단계형 기획 방법론의 유효성을 LLM-as-a-judge로 검증하는 파이프라인이다.
이 문서는 **다른 머신(연구실 서버)에서, 다른 작업자/에이전트가 이 평가를
처음부터 실행**할 수 있도록 필요한 모든 요소를 설명한다.

- 평가 설계·체크리스트(채점 기준의 단일 진실 원천): [docs/llm-judge-evaluation-checklist.md](../docs/llm-judge-evaluation-checklist.md)
- 파이프라인 구현: [eval/pipeline.py](pipeline.py) (단일 파일, 표준 라이브러리 + 레포 내부 모듈만 사용)

## 1. 무엇을 비교하는가

| 조건 | 정의 | 생성 경로 |
|---|---|---|
| **A (baseline)** | 동일 입력으로 중간 단계 없이 한 번에 최종 기획서 작성 | codex CLI 단일 호출 |
| **B (proposed)** | 4단계(문제정의→MVP범위→리스크검증→최종기획서)를 거쳐 작성 | 운영 코드와 동일한 `Orchestrator` 경로 (stage 실행→승인→진행 ×4) |

- 입력: `data/demo_inputs/*.json`의 `initial_input` (시나리오 8개, 비개발 기획자의 첫 요청).
- **정보 동등성**: B는 단계마다 사용자 요청문을 받으므로, A에도 같은 요청문 전체를
  "추가 요청사항"으로 한 번에 제공한다 (기본값. `--no-parity`로 해제 가능).
- 판정: 쌍당 1회, **문서1 = B(제안), 문서2 = A** 고정 순서. 32개 항목을
  pass/partial/fail로 판정하고 점수는 파이프라인이 산식으로 재계산한다.

## 2. 사전 요구사항

1. **레포**: `git clone https://github.com/KimJaehee0725/milemate.git && cd milemate`
2. **uv** (Python 패키지 매니저): https://docs.astral.sh/uv/ — Python 3.11 사용.
3. **의존성 설치**: `uv sync --group dev --extra ui`
4. **Codex CLI** (생성·판정 모두 이것으로 호출된다):
   - 설치 확인: `codex --version` (개발 당시 0.138.0에서 검증)
   - **로그인 필수**: `codex login` 후 인증 완료 상태여야 한다.
     미인증이면 파이프라인이 `ModelNotConfiguredError`로 즉시 실패한다.
   - 모델: `config/app.yaml`의 `model.model_id`가 빈 문자열이면 codex CLI의
     기본 모델을 쓴다. 특정 모델을 강제하려면 그 값을 채운다.
5. **네트워크**: 생성 프롬프트가 web_search를 사용하므로 외부 네트워크가 필요하다.

## 3. 실행 전 검증 (LLM 호출 없음, 1분)

```bash
# 1) 전체 테스트 — 97개 통과해야 한다
uv run --extra ui pytest -q

# 2) 파이프라인 데이터 로딩 스모크 — scenarios: 8 / initial inputs: 8 이 나와야 한다
uv run python - <<'EOF'
import importlib.util
spec = importlib.util.spec_from_file_location('p', 'eval/pipeline.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
print('scenarios:', len(p.list_scenarios()), '/ initial inputs:', len(p.load_initial_inputs()))
print('judge schema items:', len(p.judge_output_schema()['properties']['items']['items']['properties']['item_id']['enum']))
EOF
```

## 4. 실행 명령

### 4-1. 스모크 (필수 선행 — 1쌍, 약 30분)

```bash
uv run python eval/pipeline.py all --scenarios dispatch_recommendation --seeds 1 --run smoke
```

성공 기준: exit 0, `eval/results/smoke/summary.md` 생성,
판정 로그에 `[warn]` 없음.

### 4-2. Full run (8 시나리오 × seed 3 = 24쌍)

순차 실행 (가장 단순, 약 10~11시간):

```bash
uv run python eval/pipeline.py all --seeds 3 --run full1
```

**병렬 실행 (권장)** — 생성을 시나리오별로 나눠 동시에 돌린다.
모든 프로세스에 **같은 `--run` id**를 줘야 한 결과로 합쳐진다:

```bash
RUN=full1
for s in dispatch_recommendation eta_prediction failed_delivery_risk \
         rider_onboarding_dropout return_pickup_flow checkout_fee_transparency \
         merchant_prep_visibility cs_repeat_inquiry_triage; do
  nohup uv run python eval/pipeline.py generate --scenarios "$s" --seeds 3 --run "$RUN" \
    > "eval/results/gen_$s.log" 2>&1 &
done
wait
# 생성이 모두 끝난 뒤 판정·집계 (판정은 순차로 충분: 24회 × 약 2~3분 ≈ 1시간)
uv run python eval/pipeline.py judge     --run "$RUN"
uv run python eval/pipeline.py aggregate --run "$RUN"
```

병렬도 주의: codex CLI 호출이 동시에 8개 돌므로 계정의 rate limit에 따라
일부 호출이 실패할 수 있다. 실패해도 안전하다 — 아래 재개 규칙대로 같은
명령을 다시 실행하면 빠진 것만 다시 만든다.

### 4-3. 판정 모델 분리 (권장)

생성과 판정에 같은 모델을 쓰면 자기 선호 편향 우려가 있다. codex에서 사용
가능한 다른 모델 ID가 있으면 판정에만 지정한다:

```bash
uv run python eval/pipeline.py judge --run full1 --judge-model <모델ID>
```

### 4-4. 옵션 요약

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--run` | 타임스탬프 | 결과 디렉토리 이름. **재개하려면 같은 값을 다시 줘야 한다** |
| `--scenarios` | `all` | 쉼표 구분 시나리오 id 목록 |
| `--seeds` | 3 | 시나리오당 생성 반복 수 |
| `--no-parity` | (꺼짐) | A에 initial_input만 주고 단계 요청문을 주지 않음 |
| `--judge-model` | CLI 기본 모델 | 판정 전용 모델 ID |
| `--orders` | `BA` | 판정 제시 순서. `BA,AB`로 주면 순서 스왑 2회 판정(전원 일치 기준)으로 전환 |

## 5. 재개(resume) 규칙 — 중간에 끊겨도 안전

모든 단계는 **출력 파일이 이미 있으면 건너뛴다**. 서버 재부팅, rate limit,
타임아웃 등으로 중단되면 **같은 `--run` id로 같은 명령을 재실행**하면 된다.

- 생성: `A.md`와 `B.md`가 모두 있으면 그 쌍은 skip
- 판정: `judgments/<시나리오>_seed<k>_<순서>.json`이 있으면 skip
- 집계: 항상 다시 계산 (멱등)

특정 쌍을 다시 만들고 싶으면 해당 파일을 지우고 재실행한다.

## 6. 산출물 구조

```
eval/results/<run_id>/
  generations/<시나리오>/seed<k>/
    A.md            # baseline 보고서 원문
    B.md            # 제안 방법론 보고서 (중복 제거 렌더링)
    B_bundle.json   # B의 원본 번들 (렌더링 전 전체 데이터)
    meta.json       # 입력·생성 시각·소요 시간
  masked/<시나리오>/seed<k>/{A.txt,B.txt}   # 판정에 실제 제출된 텍스트
  judgments/<시나리오>_seed<k>_BA.json      # 판정 원본 (32항목 grade + 인용)
  judgments_scored.jsonl                    # 재계산된 점수·차원 판정
  summary.md                                # 최종 보고용 요약
```

`summary.md`에 포함: 종합 승률, sign test p-value, 부트스트랩 95% CI,
차원별(D1~D8) 승률 표, **32개 항목별 평균 획득 점수 차이 표**(핵심 결과),
쌍별 결과, 사람 검토가 필요한 판정 목록.

## 7. 시간·호출량 추정 (smoke 실측 기반)

| 작업 | 호출 | 실측/추정 |
|---|---|---|
| 쌍 1개 생성 (A 1회 + B 4단계) | codex 5회 (+품질 미달 시 stage당 repair 1회) | 약 24분 |
| 판정 1회 | codex 1회 | 약 2~3분 |
| **Full run 합계** | 생성 ~120회 + 판정 24회 | 순차 ~10.5시간 / 생성 8-way 병렬 시 ~2.5시간 |

## 8. 문제 해결

| 증상 | 원인/조치 |
|---|---|
| `ModelNotConfiguredError: codex CLI binary was not found` | codex 미설치 또는 PATH 누락 |
| `auth is not configured` / `not logged in` 류 메시지 | `codex login` 후 재실행 |
| `codex CLI call timed out` | 호출당 타임아웃 600초(`config/app.yaml serving.request_timeout_seconds`). 같은 run id로 재실행하면 그 지점부터 재개 |
| 판정 로그에 `[warn] invalid na ...` | 판정자가 허용 외 항목에 na를 줌 — 자동으로 fail 처리되므로 진행에는 문제없으나, 건수가 많으면 해당 판정을 사람이 검토 |
| `aggregate`가 "no judgments found" | judge 단계를 먼저 실행해야 함 |
| Streamlit/앱 관련 오류 | 평가 파이프라인은 앱 서버를 띄울 필요가 없다. `pipeline.py`만 사용 |

## 9. 완료 기준과 보고

완료 기준:
1. `generations/` 아래 24쌍(8 시나리오 × seed 3)의 A.md/B.md 존재
2. `judgments/` 아래 24개 판정 JSON 존재, validation 경고 비율 확인
3. `summary.md` 생성

보고 시 가져올 것:
- `summary.md` 전체
- `judgments_scored.jsonl` (분석 원자료)
- `summary.md`의 "검토 필요" 목록에 대해 최소 20% 사람 표본 검토 결과
  (판정 인용이 실제 문서 내용과 일치하는지)

결과 해석 시 명시할 한계 (체크리스트 문서 §2에 정의됨):
- 판정 제시 순서가 고정(제안 B가 항상 문서1)이라 위치 편향을 통제하지 않았다.
- 생성·판정에 같은 모델 계열을 썼다면 자기 선호 편향 가능성을 함께 명시한다.

## 10. 바꾸면 안 되는 것 / 바꿔도 되는 것

**바꾸면 안 됨** (결과 비교 가능성이 깨진다):
- 체크리스트 32개 항목과 채점 산식 (`docs/llm-judge-evaluation-checklist.md` §3~§5,
  `pipeline.py`의 `DIMENSION_ITEMS`/`GRADE_POINTS`/`PENALTY_RULES`)
- A/B 조건 정의와 정보 동등성 규칙
- B 렌더링 규칙 (PRD 본문 + 개발 뷰 보강 키만, 중복 문장 제거)

**바꿔도 됨** (run 간 일관성만 유지하면):
- seed 수, 판정 모델, 병렬도, run id
- `--orders BA,AB` (순서 스왑 모드 — 비용 2배, 위치 편향 통제 강화)
