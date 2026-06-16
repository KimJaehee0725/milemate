"""Render the captured per-stage data into a presentation-friendly Markdown doc.

Input : presentation/jh/_capture_<scenario>.json   (from capture_stages.py)
Output: presentation/jh/생성문_단계별_예시_<scenario>.md

Per stage we emit:
  ① 요청 (request)            — the text fed to that stage (canned for stage 2-4)
  ② Reasoning (summary)        — the stage's own narrative judgement
  ③ 출력물 (output)            — each non-empty section as a <details> toggle with
                                 a readable nested-markdown view, plus a raw-JSON toggle.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "dispatch_recommendation"
CAP = ROOT / "presentation" / "jh" / f"_capture_{SCENARIO}.json"
OUT = ROOT / "presentation" / "jh" / f"생성문_단계별_예시_{SCENARIO}.md"

STAGE_NAMES = {
    "stage_1": "1단계 · 문제 정의 (Problem framing)",
    "stage_2": "2단계 · 서비스 구조 / MVP 범위 (Service structure)",
    "stage_3": "3단계 · 검증 / 리스크 (Verification)",
    "stage_4": "4단계 · 최종 기획서 (Final PRD)",
}
STAGE_ROLE = {
    "stage_1": "비개발 기획자의 자연어 아이디어를 받아, 팀이 바로 논의할 수 있는 문제 정의로 구조화",
    "stage_2": "문제 정의를 기반으로 기획·개발 두 관점에서 MVP 범위와 구조를 확정",
    "stage_3": "확정안을 현업 관점에서 압박 검증 — 수요/비용/안내 과장/보류 조건 점검",
    "stage_4": "앞 단계 승인 결과를 하나의 서비스 기획서(PRD)로 통합",
}
# top-level output sections -> (korean label, emoji)
SECTIONS = [
    ("planner_view", "기획 관점"),
    ("engineer_view", "개발 관점"),
    ("prd_packet", "기획서 패킷 (PRD)"),
    ("prd_quality", "품질 검증 결과"),
    ("decision_points", "결정이 필요한 항목"),
    ("required_user_input", "사용자 확인이 필요한 입력"),
    ("risks", "리스크"),
    ("citations", "참고 자료"),
    ("rollback_targets", "되돌리기 대상 단계"),
]


def is_empty(v):
    return v is None or v == "" or v == [] or v == {} or (
        isinstance(v, dict) and all(is_empty(x) for x in v.values())
    )


def md_inline(v):
    if isinstance(v, bool):
        return "예" if v else "아니오"
    return str(v)


def render(v, depth=0):
    """Render a JSON value as a nested markdown bullet list."""
    pad = "  " * depth
    lines = []
    if isinstance(v, dict):
        for k, val in v.items():
            if is_empty(val):
                continue
            if isinstance(val, (dict, list)):
                lines.append(f"{pad}- **{k}**")
                lines.append(render(val, depth + 1))
            else:
                lines.append(f"{pad}- **{k}**: {md_inline(val)}")
    elif isinstance(v, list):
        for item in v:
            if isinstance(item, dict):
                fields = [(k, val) for k, val in item.items() if not is_empty(val)]
                if not fields:
                    continue
                # lead the bullet with the first field so there is no empty parent
                k0, v0 = fields[0]
                if isinstance(v0, (dict, list)):
                    lines.append(f"{pad}- **{k0}**")
                    lines.append(render(v0, depth + 1))
                else:
                    lines.append(f"{pad}- **{k0}**: {md_inline(v0)}")
                for k, val in fields[1:]:
                    if isinstance(val, (dict, list)):
                        lines.append(f"{pad}  - **{k}**")
                        lines.append(render(val, depth + 2))
                    else:
                        lines.append(f"{pad}  - **{k}**: {md_inline(val)}")
            elif isinstance(item, (list,)):
                lines.append(render(item, depth + 1))
            else:
                lines.append(f"{pad}- {md_inline(item)}")
    else:
        lines.append(f"{pad}- {md_inline(v)}")
    return "\n".join(x for x in lines if x.strip())


def count_summary(v):
    """A short '(n건)' style hint for the toggle title."""
    if isinstance(v, list):
        return f" — {len(v)}건"
    if isinstance(v, dict):
        n = sum(1 for x in v.values() if not is_empty(x))
        return f" — {n}개 항목"
    return ""


def details(title, body):
    return f"<details>\n<summary>{title}</summary>\n\n{body}\n\n</details>"


def main():
    data = json.loads(CAP.read_text(encoding="utf-8"))
    scenario = data.get("scenario", SCENARIO)
    md = []
    md.append(f"# 단계별 생성 예시 — {scenario}")
    md.append("")
    md.append("> milemate(staged Human-in-the-loop)는 **사용자 자연어 입력 1개**를 받아 "
              "**4단계 파이프라인**으로 기획서를 만든다. 각 단계는 "
              "`reasoning(summary) → 구조화 출력`을 내고, 단계 사이에서 사람은 "
              "**승인 / 보류 / 되돌리기**로만 개입한다(자유 재질문이 아님).")
    md.append(">")
    md.append(f"> - 모델 reasoning effort: **{data.get('model',{}).get('reasoning_effort','medium')}** "
              "· 실제 codex 실행 캡처본")
    md.append("> - Stage 1 입력 = 기획자의 원본 자연어 / Stage 2~4 입력 = 각 단계용으로 "
              "**사전에 고정된 요청 프롬프트**")
    md.append("")
    # the raw initial hook
    md.append("## 사용자 초기 입력 (raw hook)")
    md.append("")
    md.append("> " + data["initial_input"].replace("\n", "\n> "))
    md.append("")
    md.append("---")
    md.append("")

    for st in data.get("stages", []):
        sid = st["stage_id"]
        out = st["output"]
        md.append(f"## {STAGE_NAMES.get(sid, sid)}")
        md.append("")
        md.append(f"*{STAGE_ROLE.get(sid,'')}*")
        if st.get("elapsed_seconds") is not None:
            md.append(f"<sub>생성 소요 {st['elapsed_seconds']}초</sub>")
        md.append("")

        # ① request
        md.append("### ① 요청")
        if sid == "stage_1":
            md.append("> *(Stage 1의 요청 = 위 사용자 초기 입력 그대로)*")
        else:
            md.append("> *(이 단계용으로 사전 고정된 요청 프롬프트)*")
        md.append(">")
        md.append("> " + st["request"].replace("\n", "\n> "))
        md.append("")

        # ② reasoning (summary)
        md.append("### ② Reasoning (이 단계의 판단 서술 · summary)")
        md.append("")
        summary = out.get("summary", "").strip()
        md.append("> " + summary.replace("\n", "\n> ") if summary else "> *(없음)*")
        md.append("")

        # ③ output
        md.append("### ③ 출력물")
        md.append("")
        any_section = False
        for key, label in SECTIONS:
            val = out.get(key)
            if is_empty(val):
                continue
            any_section = True
            body = render(val)
            md.append(details(f"📄 {label} <code>{key}</code>{count_summary(val)}", body))
            md.append("")
        if not any_section:
            md.append("*(구조화 출력 없음)*")
            md.append("")
        # raw json toggle (fidelity)
        raw = json.dumps(out, ensure_ascii=False, indent=2)
        md.append(details("🔧 이 단계 출력 — 원본 JSON",
                          f"```json\n{raw}\n```"))
        md.append("")
        md.append("---")
        md.append("")

    # final merged bundle
    fb = data.get("final_bundle")
    if fb:
        md.append("## 최종 통합 보고서 (build_final_report)")
        md.append("")
        md.append("> 4단계 승인 결과를 하나로 병합한 최종 산출물. "
                  "발표 슬라이드의 *Ours* 생성문이 이 번들에서 나온다.")
        md.append("")
        for key, label in [
            ("planner_report", "기획 관점 요약"),
            ("engineer_report", "개발 관점 요약"),
            ("prd_report", "기획서 본문 (PRD)"),
            ("prd_quality", "품질 검증"),
            ("decision_log", "의사결정 기록"),
            ("risks", "리스크"),
            ("citations", "참고 자료"),
        ]:
            val = fb.get(key)
            if is_empty(val):
                continue
            md.append(details(f"📄 {label} <code>{key}</code>{count_summary(val)}",
                              render(val)))
            md.append("")
        raw = json.dumps(fb, ensure_ascii=False, indent=2)
        md.append(details("🔧 최종 번들 — 원본 JSON", f"```json\n{raw}\n```"))
        md.append("")

    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {OUT}  ({len(''.join(md))} chars, {len(data.get('stages',[]))} stages)")


if __name__ == "__main__":
    main()
