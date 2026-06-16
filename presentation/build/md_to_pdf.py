"""Render the per-stage Markdown into a readable, fully-expanded PDF.

- <details> toggles -> bold sub-headings (everything visible, no interactivity)
- the giant raw-JSON dumps (summary starts with 🔧) are DROPPED from the PDF
  (the readable nested-markdown sections already carry the same content);
  the full JSON stays in the .md / _capture json.
- nested bullet lists use 2-space indent, so markdown is parsed with tab_length=2.

Pipeline: md -> html (python-markdown) -> PDF (headless Google Chrome).
Run:  presentation/build/.venv-fig/bin/python presentation/build/md_to_pdf.py dispatch_recommendation
"""
import html as _html
import subprocess
import sys
from pathlib import Path

import markdown  # installed in .venv-fig

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "dispatch_recommendation"
MD = ROOT / "presentation" / "jh" / f"생성문_단계별_예시_{SCENARIO}.md"
HTML = ROOT / "presentation" / "build" / f"_stage_{SCENARIO}.html"
PDF = ROOT / "presentation" / "jh" / f"생성문_단계별_예시_{SCENARIO}.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def expand_toggles(md_text: str) -> str:
    out, skip_raw = [], False
    for line in md_text.split("\n"):
        s = line.strip()
        if s == "<details>":
            continue
        if s.startswith("<summary>") and s.endswith("</summary>"):
            inner = s[len("<summary>"):-len("</summary>")]
            if inner.startswith("🔧"):
                skip_raw = True
                continue
            out += ["", f"**▸ {inner}**", ""]
            continue
        if s == "</details>":
            skip_raw = False
            continue
        if skip_raw:
            continue
        out.append(line)
    return "\n".join(out)


CSS = """
@page { size: A4; margin: 14mm 14mm 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "Apple SD Gothic Neo","NanumSquare",sans-serif;
       font-size: 10.5pt; line-height: 1.5; color: #1f2733; }
h1 { font-size: 19pt; color: #163866; border-bottom: 3px solid #163866;
     padding-bottom: 6px; margin: 0 0 14px; }
h2 { font-size: 15pt; color: #163866; margin: 22px 0 8px;
     padding: 6px 10px; background: #EEF2F7; border-left: 5px solid #163866;
     page-break-before: always; page-break-after: avoid; }
h2:first-of-type { page-break-before: avoid; }
h3 { font-size: 12pt; color: #2D3338; margin: 16px 0 6px;
     page-break-after: avoid; }
p { margin: 6px 0; }
strong { color: #163866; }
em { color: #6B7280; }
blockquote { margin: 8px 0; padding: 7px 12px; background: #F7F8FA;
             border-left: 4px solid #8FA38A; color: #2D3338; }
blockquote p { margin: 3px 0; }
ul { margin: 4px 0 8px; padding-left: 20px; }
li { margin: 2px 0; page-break-inside: avoid; }
code { font-family: "SF Mono",Menlo,monospace; font-size: 9pt;
       background: #F0F2F5; padding: 1px 4px; border-radius: 3px; color: #8B5A3C; }
pre { background: #F0F2F5; padding: 10px; border-radius: 6px; overflow: auto;
      white-space: pre-wrap; word-wrap: break-word; font-size: 8.5pt; }
pre code { background: none; padding: 0; color: #2D3338; }
table { border-collapse: collapse; margin: 8px 0; width: 100%; }
th,td { border: 1px solid #C9D2DE; padding: 4px 8px; font-size: 9.5pt; text-align: left; }
th { background: #EEF2F7; color: #163866; }
hr { border: 0; border-top: 1px solid #D9DEE6; margin: 18px 0; }
sub { color: #8FA38A; font-size: 8.5pt; }
"""


def main() -> None:
    md_text = MD.read_text(encoding="utf-8")
    md_text = expand_toggles(md_text)
    body = markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "sane_lists", "attr_list"],
        tab_length=2,
    )
    doc = (f"<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
           f"<style>{CSS}</style></head><body>{body}</body></html>")
    HTML.write_text(doc, encoding="utf-8")
    print(f"html -> {HTML} ({len(doc):,} chars)")

    PDF.unlink(missing_ok=True)
    cmd = [
        CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw", "--virtual-time-budget=20000",
        f"--print-to-pdf={PDF}", HTML.as_uri(),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not PDF.exists():
        print("CHROME STDERR:", res.stderr[-1500:])
        raise SystemExit("PDF not produced")
    print(f"pdf  -> {PDF} ({PDF.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
