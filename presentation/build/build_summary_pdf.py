"""One-page landscape PDF: 4 stages x 4 core elements, condensed.

Each cell is a faithful one-line condensation of the captured fields in
presentation/jh/_capture_dispatch_recommendation.json (medium effort, real run):
  Reasoning   <- output.summary
  기획자 관점  <- planner_view (first summary key)
  개발자 관점  <- engineer_view (system_shape / state model / required data)
  PRD 핵심    <- prd_packet.stage_goal
Full text + raw JSON live in the companion .md.

Render: md(none) -> html -> Chrome headless PDF (1 page, A4 landscape).
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "presentation" / "build" / "_summary_dispatch.html"
PDF = ROOT / "presentation" / "jh" / "단계별_핵심요약_1장_dispatch.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

STAGES = [
    {
        "no": "1단계", "name": "문제 정의", "en": "Problem framing",
        "reasoning": "‘자동 배차’가 아니라 <b>위험 주문 우선순위화 + 운영자 승인</b>으로 문제를 재정의. 추천 근거 표시·승인 이력·KPI 계측을 1단계 범위로 설정.",
        "planner": "피크 때 봐야 할 <b>위험 주문만 노출</b>, 추천 사유와 기사 부담 기준을 확인한 뒤 승인하는 흐름.",
        "engineer": "위험점수 / 추천후보 / 승인 워크플로 API 분리. <b>추천 생성과 배차 실행 사이에 ‘승인’ 상태 필수.</b>",
        "prd": "위험·보상·과부하 큰 주문만 대시보드 상단에 올리고, 사유 확인 후 승인하는 <b>승인형 배차 추천 MVP</b> 정의.",
    },
    {
        "no": "2단계", "name": "서비스 구조", "en": "Service structure",
        "reasoning": "완전 자동 배차를 제외하고 <b>승인·보류·거절</b> 흐름 확정. 지연률 / SLA / 배송원 편차 / 보상 비용을 같은 화면·KPI 체계로 통합.",
        "planner": "확인 → 사유 이해 → <b>승인/보류/거절</b> → 파일럿 KPI 리뷰까지의 운영 화면 정의. 현장 반발을 줄이는 의사결정 흐름이 핵심.",
        "engineer": "추천 <b>상태 모델</b>(generated/approved/held/rejected…) 정의. <b>approved 상태만 실제 배차 변경 요청</b>을 생성.",
        "prd": "1단계 대시보드 범위를 유지하며 승인·보류·거절 기록과 4대 지표 <b>리뷰 흐름을 확정.</b>",
    },
    {
        "no": "3단계", "name": "검증 / 리스크", "en": "Verification",
        "reasoning": "데이터가 늦거나 공급 부족이 구조적이면 <b>추천을 실행하지 말고 보류·수동확인·고객안내로 전환</b>해야 한다는 게이트 기준 추가.",
        "planner": "자동화 강화가 아니라 <b>‘추천을 믿어도 되는 조건’</b>을 정의. 오래된 데이터·공급 부족 시 승인보다 보류·롤백 권고.",
        "engineer": "생성·승인 직전 <b>데이터 신선도 재검증 게이트</b>. 실패는 <code>blocked_for_stale_data</code>로 기록, 화면 배지=API 신뢰도 일치.",
        "prd": "데이터 지연 / 공급 부족 / 수요 초과 상황에서 <b>믿을 추천 vs 보류할 판단</b>의 기준을 정의.",
    },
    {
        "no": "4단계", "name": "최종 기획서", "en": "Final PRD",
        "reasoning": "조기 발견 + 납득 가능한 추천으로 <b>고객 신뢰·기사 부담·매장 클레임·보상 비용을 함께 절감</b>하는 최종 서비스 시나리오로 정리.",
        "planner": "문제 재정의 — 기사 자동 교체가 아니라 <b>늦어질 주문을 먼저 찾아 운영자가 근거로 승인</b>하게 만드는 것.",
        "engineer": "필수 데이터 묶음(주문/위치/ETA/공급/매장/안내/비용/보존정책) + 기술 블록·제약·<b>구현 순서·검증 계획</b> 확정.",
        "prd": "3단계 신뢰도·보류 기준 위에 <b>설명 가능한 추천을 승인</b>해 지연 비용·신뢰 리스크를 줄이는 최종 PRD 확정.",
    },
]

COLS = [
    ("🧠 Reasoning<br><span class='sub'>그 단계의 판단</span>", "reasoning", "#163866"),
    ("📋 기획자 관점<br><span class='sub'>planner_view</span>", "planner", "#8FA38A"),
    ("🛠 개발자 관점<br><span class='sub'>engineer_view</span>", "engineer", "#8B5A3C"),
    ("📄 PRD 핵심<br><span class='sub'>prd_packet</span>", "prd", "#6B7280"),
]

CSS = """
@page { size: A4 landscape; margin: 11mm 11mm; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Apple SD Gothic Neo","NanumSquare",sans-serif; color:#1f2733; }
.title { font-size: 19pt; font-weight: 800; color:#163866; }
.title .scn { color:#8B5A3C; }
.sub-line { font-size: 10pt; color:#6B7280; margin: 4px 0 10px; line-height:1.4; }
.hook { font-size: 9.5pt; color:#4a5560; background:#F5F3EF; border-left:4px solid #8FA38A;
        padding:8px 11px; margin-bottom:13px; line-height:1.5; }
table { width:100%; border-collapse:collapse; table-layout:fixed; }
col.stage { width: 12%; }
col.cell  { width: 22%; }
th, td { border:1px solid #C9D2DE; vertical-align:top; }
thead th { padding:9px 9px; font-size:11pt; font-weight:700; color:#fff; line-height:1.3; }
thead th .sub { font-size:8pt; font-weight:400; opacity:.85; }
thead th.stagehead { background:#2D3338; }
.stagecell { background:#163866; color:#fff; padding:14px 9px; }
.stagecell .no { font-size:15pt; font-weight:800; }
.stagecell .nm { font-size:11pt; font-weight:700; margin-top:2px; }
.stagecell .en { font-size:8pt; opacity:.8; }
.stagecell.s2 { background:#27568c; } .stagecell.s3 { background:#3a6ea5; } .stagecell.s4 { background:#4f86c6; }
td.body { padding:13px 11px; font-size:10.5pt; line-height:1.55; }
td.body b { color:#163866; font-weight:700; }
td.body code { font-family:"SF Mono",Menlo,monospace; font-size:9pt; background:#EEF2F7;
               padding:0 3px; border-radius:3px; color:#8B5A3C; }
.foot { font-size:8.3pt; color:#9AA3AD; margin-top:11px; text-align:right; }
.flow { font-size:10pt; color:#163866; font-weight:700; margin:0 0 10px; }
"""


def build_html() -> str:
    head = ("<tr><th class='stagehead'>단계</th>"
            + "".join(f"<th style='background:{c}'>{label}</th>" for label, _, c in COLS)
            + "</tr>")
    rows = []
    for i, st in enumerate(STAGES, 1):
        scls = "" if i == 1 else f"s{i}"
        cells = "".join(f"<td class='body'>{st[key]}</td>" for _, key, _ in COLS)
        rows.append(
            f"<tr><td class='stagecell {scls}'>"
            f"<div class='no'>{st['no']}</div><div class='nm'>{st['name']}</div>"
            f"<div class='en'>{st['en']}</div></td>{cells}</tr>"
        )
    colgroup = ("<colgroup><col class='stage'>"
                + "<col class='cell'>" * 4 + "</colgroup>")
    return f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'>
<style>{CSS}</style></head><body>
<div class='title'>단계별 핵심 요약 — milemate <span class='scn'>(동적 배차 추천 시나리오)</span></div>
<div class='sub-line'>비개발 기획자의 자연어 입력 1개 → 4단계 파이프라인. 각 단계는 Reasoning을 거쳐 기획·개발 관점과 PRD를 구조화하고, 사람은 단계 사이에서 승인/보류/되돌리기로 개입.</div>
<div class='flow'>① 문제 정의 &nbsp;→&nbsp; ② 서비스 구조 &nbsp;→&nbsp; ③ 검증/리스크 &nbsp;→&nbsp; ④ 최종 기획서(PRD)</div>
<div class='hook'><b>사용자 초기 입력:</b> “저녁 6~8시 강남/서초에 주문이 몰리면 잘하는 기사 몇 명한테만 콜이 쏠려요. 늦은 주문 하나에 사과 쿠폰 3천 원씩 날아가고요. 시스템이 기사를 확 바꾸면 반발할까 무섭고… 위험한 주문이 ‘왜 위험한지’ 이유까지 떠서 운영자가 승인만 누르면 좋겠는데, 개발은 1도 몰라서 뭐부터 말해야 할지 모르겠어요.”</div>
<table>{colgroup}<thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>
<div class='foot'>각 칸은 실제 생성 데이터(medium effort · codex 캡처)의 핵심을 한 줄로 압축 · 전체 단계별 상세 + 원본 JSON: 생성문_단계별_예시_dispatch_recommendation.md</div>
</body></html>"""


def main() -> None:
    HTML.write_text(build_html(), encoding="utf-8")
    PDF.unlink(missing_ok=True)
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           "--run-all-compositor-stages-before-draw", "--virtual-time-budget=10000",
           f"--print-to-pdf={PDF}", HTML.as_uri()]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not PDF.exists():
        print("CHROME STDERR:", res.stderr[-1500:])
        raise SystemExit("PDF not produced")
    print(f"pdf -> {PDF} ({PDF.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
