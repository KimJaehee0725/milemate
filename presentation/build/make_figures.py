#!/usr/bin/env python
"""Generate evaluation charts for the Milemate final presentation.
Run with the dedicated uv env: .venv-fig/bin/python make_figures.py
Data source: eval/results/combined_effort_summary.md, combined_ablation_summary.md,
             presentation_analysis/synthesis_report.md
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm

# ---- Korean font ----
for cand in ("Apple SD Gothic Neo", "AppleGothic", "Apple SD Gothic NeoM"):
    if any(f.name == cand for f in fm.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False

# ---- Brand palette (extracted from deck) ----
NAVY = "#163866"      # primary / proposed (B)
GRAY = "#9CA3AF"      # baseline (A)
SAGE = "#8FA38A"      # accent
BROWN = "#8B5A3C"
DGRAY = "#2D3338"
LGRID = "#E2E4E8"
CREAM = "#F5F3EF"

OUT = "../assets"
DPI = 200

def style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#C7CBD1")
    ax.tick_params(colors=DGRAY, length=0)
    ax.yaxis.grid(True, color=LGRID, lw=1)
    ax.set_axisbelow(True)

# =====================================================================
# 1. Effort sweep — grouped Simple/Ours performance by effort
# =====================================================================
efforts = ["low", "medium", "high", "xhigh"]
e_diff = [0.524, 0.525, 0.430, 0.587]
e_bwin = [23, 23, 23, 23]
e_awin = [1, 1, 1, 1]

simple_effort = [4.06] * len(efforts)
ours_effort = [s + d for s, d in zip(simple_effort, e_diff)]

fig, ax = plt.subplots(figsize=(9.6, 4.7))
x = np.arange(len(efforts))
bwth = 0.34
ax.bar(x - bwth / 2, simple_effort, bwth, color=GRAY, zorder=3, label="Simple")
ax.bar(x + bwth / 2, ours_effort, bwth, color=NAVY, zorder=3, label="Ours")
for i, (sv, ov, d) in enumerate(zip(simple_effort, ours_effort, e_diff)):
    ax.text(i - bwth / 2, sv + 0.05, f"{sv:.2f}", ha="center", va="bottom", fontsize=10.5, color="#6B7280")
    ax.text(i + bwth / 2, ov + 0.05, f"{ov:.2f}", ha="center", va="bottom", fontsize=10.5, fontweight="bold", color=NAVY)
    ax.text(i, 5.22, f"격차 +{d:.3f}\n{e_bwin[i]}승-{e_awin[i]}패",
            ha="center", va="bottom", fontsize=9.3, color=DGRAY, linespacing=1.25)
ax.axhline(5.0, color=SAGE, lw=1.1, ls="--")
ax.text(3.52, 5.0, "만점 5.0", color=SAGE, fontsize=10.5, va="center")
style(ax)
ax.set_xticks(list(x)); ax.set_xticklabels([e.upper() for e in efforts], fontsize=11.5)
ax.set_ylabel("평균 점수 (1-5)", fontsize=12, color=DGRAY)
ax.set_ylim(0, 6.10)
ax.set_title("Effort별 성능 비교",
             fontsize=13.5, fontweight="bold", color=NAVY, pad=14, loc="left")
ax.legend(loc="upper center", frameon=False, fontsize=10.5, ncol=2,
          bbox_to_anchor=(0.5, 1.22), columnspacing=2.3, handlelength=1.9)
fig.subplots_adjust(left=0.11, right=0.96, top=0.68, bottom=0.24)
fig.text(0.11, 0.055, "각 effort에서 Simple/Ours를 함께 비교해도 Ours 우위가 유지된다.",
         fontsize=9.8, color="#5B626B", linespacing=1.35)
fig.savefig(f"{OUT}/fig_effort.png", dpi=DPI, facecolor="white")
plt.close(fig)

# ---- 1b. Absolute score: retained for backup assets, not inserted in the deck ----
fig, ax = plt.subplots(figsize=(5.0, 4.7))
abs_vals = [4.06, 4.81]
abs_cols = [GRAY, NAVY]
ax.bar([0, 1], abs_vals, width=0.55, color=abs_cols, zorder=3)
for i, v in enumerate(abs_vals):
    ax.text(i, v + 0.06, f"{v:.2f}", ha="center", va="bottom", fontsize=14,
            fontweight="bold", color=(NAVY if i else DGRAY))
ax.axhline(5.0, color=SAGE, lw=1.2, ls="--")
ax.text(1.55, 5.0, "만점 5.0", color=SAGE, fontsize=10.4, va="center")
style(ax)
ax.set_xticks([0, 1]); ax.set_xticklabels(["Simple\n(일회성)", "Ours\n(단계형)"], fontsize=11.5)
ax.set_xlim(-0.6, 1.9)
ax.set_ylim(0, 5.6)
ax.set_yticks([0, 1, 2, 3, 4, 5])
ax.set_ylabel("평균 점수 (1-5)", fontsize=11.5, color=DGRAY)
ax.set_title("절대 점수 비교",
             fontsize=13, fontweight="bold", color=NAVY, pad=12, loc="left")
fig.subplots_adjust(left=0.18, right=0.95, top=0.86, bottom=0.24)
fig.text(0.18, 0.045, "전체 파이프라인 기준 평균 점수",
         fontsize=10.0, color="#5B626B", linespacing=1.35)
fig.savefig(f"{OUT}/fig_effort_abs.png", dpi=DPI, facecolor="white")
plt.close(fig)

# =====================================================================
# 2. Stage ablation — grouped one-shot vs staged generation
# =====================================================================
stages = ["1단계", "1~2단계", "1~3단계", "전체"]
score_staged = [4.84, 4.83, 4.83, 4.81]
score_diff = [0.634, 0.716, 0.591, 0.723]
score_batch = [b - d for b, d in zip(score_staged, score_diff)]
s_bwin = [22, 22, 22, 23]
s_awin = [2, 2, 2, 1]

fig, ax = plt.subplots(figsize=(9, 4.7))
x = np.arange(len(stages))
bwth = 0.34
ax.bar(x - bwth / 2, score_batch, bwth, color=GRAY, zorder=3, label="일괄 생성(A)")
ax.bar(x + bwth / 2, score_staged, bwth, color=NAVY, zorder=3, label="단계별 생성(B)")
for i, (av, bv) in enumerate(zip(score_batch, score_staged)):
    ax.text(i - bwth / 2, av + 0.025, f"{av:.2f}", ha="center", va="bottom",
            fontsize=10.5, color="#6B7280")
    ax.text(i + bwth / 2, bv + 0.025, f"{bv:.2f}", ha="center", va="bottom",
            fontsize=10.8, fontweight="bold", color=NAVY)
ax.axhline(5.0, color=SAGE, lw=1.1, ls="--")
style(ax)
ax.set_xticks(list(x)); ax.set_xticklabels(stages, fontsize=11.5)
ax.set_ylim(3.95, 5.22); ax.set_yticks([4.0, 4.3, 4.6, 4.9, 5.0])
ax.set_ylabel("평균 점수 (1-5)", fontsize=12, color=DGRAY)
ax.set_title("단계별 생성 vs 일괄 생성",
             fontsize=13.5, fontweight="bold", color=NAVY, pad=14, loc="left")
ax.legend(loc="upper center", frameon=False, fontsize=10.5, ncol=2,
          bbox_to_anchor=(0.55, 1.18), columnspacing=2.4, handlelength=1.8)
fig.subplots_adjust(left=0.12, right=0.94, top=0.70, bottom=0.28)
fig.text(0.12, 0.055,
         "stage별 A/B 차이를 보존해 표시. 단계별 생성은 일괄 생성보다 높은 평균 점수와 승수를 유지한다.",
         fontsize=9.8, color="#5B626B", linespacing=1.35)
fig.savefig(f"{OUT}/fig_ablation.png", dpi=DPI, facecolor="white")
plt.close(fig)

# =====================================================================
# 3. Dimension verdict share
# =====================================================================
dims = ["문제\n정의", "범위\n규율", "실행\n구체성", "측정\n가능성",
        "리스크\n보류", "내적\n일관성", "인계\n준비", "입력\n충실"]
ours_win = np.array([71, 4, 100, 100, 21, 17, 100, 25])
simple_win = np.array([4, 0, 0, 0, 0, 4, 0, 8])
tie = 100 - ours_win - simple_win

fig, ax = plt.subplots(figsize=(9.2, 4.6))
x = np.arange(len(dims))
ax.bar(x, ours_win, width=0.62, color=NAVY, zorder=3, label="Ours 승")
ax.bar(x, tie, bottom=ours_win, width=0.62, color="#D9DEE5", zorder=3, label="무승부")
ax.bar(x, simple_win, bottom=ours_win + tie, width=0.62, color=BROWN, zorder=3, label="Simple 승")
for i, w in enumerate(ours_win):
    if w >= 15:
        ax.text(i, w / 2, f"{int(w)}%", ha="center", va="center", fontsize=9.8, color="white", fontweight="bold")
    elif w > 0:
        ax.text(i, w + 3, f"{int(w)}%", ha="center", va="bottom", fontsize=9.2, color=NAVY, fontweight="bold")
style(ax)
ax.set_xticks(range(len(dims))); ax.set_xticklabels(dims, fontsize=10.2)
ax.set_ylabel("판정 비중", fontsize=12, color=DGRAY)
ax.set_ylim(0, 100)
ax.set_yticks([0, 25, 50, 75, 100])
ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_title("차원별 승·패·무승부 비중",
             fontsize=13.5, fontweight="bold", color=NAVY, pad=14, loc="left")
ax.legend(loc="upper center", frameon=False, fontsize=10.0, ncol=3,
          bbox_to_anchor=(0.57, 1.22), columnspacing=2.2, handlelength=1.8)
fig.subplots_adjust(left=0.12, right=0.98, top=0.68, bottom=0.30)
fig.text(0.12, 0.055,
         "실행·측정·인계는 Ours 승이 거의 전부이고, 낮은 구간은 Simple 우세보다 무승부가 많다.",
         fontsize=9.8, color="#5B626B", linespacing=1.35)
fig.savefig(f"{OUT}/fig_dimension.png", dpi=DPI, facecolor="white")
plt.close(fig)

# =====================================================================
# 4. Item-level dumbbell
# =====================================================================
items = [
    ("결정 안건 완결성", 0.25, 1.00),
    ("미해결 질문 추적", 0.27, 1.00),
    ("KPI 담당 주체",   0.00, 0.75),
    ("KPI 측정 방법",   0.52, 1.00),
    ("KPI 기준값",      0.50, 0.96),
    ("화면 명세",       0.58, 1.00),
    ("예외/오류 처리",  0.50, 1.00),
    ("운영정책 4요소",  0.50, 1.00),
    ("현행 우회/한계",  0.62, 1.00),
    ("수치 출처 추적",  0.08, 0.23),
]
labels = [i[0] for i in items]
a = [i[1] for i in items]
b = [i[2] for i in items]
y = list(range(len(items)))[::-1]

fig, ax = plt.subplots(figsize=(9.6, 5.4))
for yi, av, bv in zip(y, a, b):
    ax.plot([av, bv], [yi, yi], color="#C7CBD1", lw=2.4, zorder=1)
simple_scatter = ax.scatter(a, y, s=110, color=GRAY, zorder=3, label="Simple")
ours_scatter = ax.scatter(b, y, s=130, color=NAVY, zorder=3, label="Ours")
for yi, av, bv in zip(y, a, b):
    ax.text(av - 0.03, yi, f"{av:.2f}", ha="right", va="center", fontsize=9, color="#6B7280")
    ax.text(bv + 0.03, yi, f"{bv:.2f}", ha="left", va="center", fontsize=9.5, color=NAVY, fontweight="bold")
ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10.5, color=DGRAY)
ax.set_xlim(-0.18, 1.25)
ax.set_xticks([0, 0.5, 1.0]); ax.set_xticklabels(["0.0\n(fail)", "0.5\n(partial)", "1.0\n(pass)"], fontsize=9.5)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#C7CBD1")
ax.tick_params(length=0)
ax.xaxis.grid(True, color=LGRID, lw=1); ax.set_axisbelow(True)
ax.set_title("항목별 평균 점수",
             fontsize=13.5, fontweight="bold", color=NAVY, pad=14, loc="left")
fig.subplots_adjust(left=0.25, right=0.96, top=0.78, bottom=0.23)
fig.legend(handles=[simple_scatter, ours_scatter],
           labels=["Simple", "Ours"],
           loc="upper right", frameon=False, fontsize=10.5, ncol=2,
           bbox_to_anchor=(0.96, 0.92))
fig.text(0.25, 0.055,
         "인계, KPI 측정 구조, 실행 구조는 Simple이 비우고 Ours가 채운다. 수치 출처 추적은 양쪽 모두 약하다.",
         fontsize=9.8, color="#5B626B", linespacing=1.35)
fig.savefig(f"{OUT}/fig_dumbbell.png", dpi=DPI, facecolor="white")
plt.close(fig)

# =====================================================================
# 5. Numeric-source traceability gap
# =====================================================================
conds = ["Simple\n(일회성)", "1단계", "1~2단계", "1~3단계", "전체"]
d82 = [0.08, 0.21, 0.17, 0.29, 0.23]
cols = [GRAY] + [NAVY] * 4
fig, ax = plt.subplots(figsize=(8.6, 4.0))
ax.bar(range(len(conds)), d82, width=0.6, color=cols, zorder=3)
for i, v in enumerate(d82):
    ax.text(i, v + 0.014, f"{v:.2f}", ha="center", va="bottom", fontsize=12.2, fontweight="bold", color=DGRAY)
ax.axhline(1.0, color=SAGE, lw=1.3, ls="--")
ax.text(4.18, 1.0, "PASS 기준 1.0", color=SAGE, fontsize=12, va="center")
style(ax)
ax.set_xticks(range(len(conds))); ax.set_xticklabels(conds, fontsize=11.2)
ax.set_xlim(-0.55, 4.85)
ax.set_ylim(0, 1.1)
ax.set_ylabel("평균 점수", fontsize=13, color=DGRAY)
ax.set_title("수치 출처 추적",
             fontsize=13.6, fontweight="bold", color=NAVY, pad=12, loc="left")
fig.subplots_adjust(left=0.13, right=0.96, top=0.82, bottom=0.18)
fig.savefig(f"{OUT}/fig_d82.png", dpi=DPI, facecolor="white")
plt.close(fig)

print("OK - 5 figures written to", OUT)
