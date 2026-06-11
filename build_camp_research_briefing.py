from __future__ import annotations

import os
import runpy
import shutil
import subprocess
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


ASSET_DIR = ROOT / "ppt_assets" / "camp_research_briefing"
MARKDOWN_OUT = ROOT / "CAMP_Research_Briefing_25min.md"
PPTX_OUT = ROOT / "CAMP_Research_Briefing_25min.pptx"
RAW_PPTX_OUT = ROOT / "_camp_research_briefing_raw.pptx"
REFERENCE_PPTX = ROOT / "CMU_Blue_Academic_Research_Briefing.pptx"
STYLED_REFERENCE_PPTX = ROOT / "CMU_Blue_Academic_Research_Briefing_reference.pptx"


CMU_RED = "#C41230"
CMU_BLUE = "#0055A4"
DARK_BLUE = "#15395B"
TEAL = "#008A8A"
GOLD = "#FDB515"
GRAY = "#5E6A71"
LIGHT_GRAY = "#E7EBEF"
INK = "#1C2430"
EMU_PER_INCH = 914400
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


K50_ROWS = [
    ("CAMP-Select It100", 2.66, 4.58, 60.2, 3.79, 12.64, 1.08),
    ("Finetune + CAMP E5", 1.71, 3.64, 63.2, 2.64, 8.78, 1.10),
    ("Finetune + CAMP E10", 1.65, 3.51, 63.9, 2.80, 9.30, 1.10),
    ("Finetune + CAMP E20", 1.61, 3.46, 63.6, 2.43, 8.03, 1.10),
    ("Finetune Safe E5", 1.09, 2.62, 68.4, 0.17, 0.24, 1.17),
    ("Finetune Safe E10", 0.99, 2.34, 69.7, 0.17, 0.28, 1.17),
    ("Finetune Safe E20", 1.06, 2.52, 68.6, 0.20, 0.34, 1.16),
    ("Oracle MinADE", 1.06, 1.84, 75.4, 4.51, 15.37, 1.41),
    ("Pred Top1", 3.17, 6.53, 82.0, 7.48, 25.35, 1.95),
    ("Reranker Safe", 2.07, 3.90, 74.1, 4.18, 14.19, 1.19),
    ("Select Static", 2.27, 3.93, 60.2, 2.83, 9.30, 1.15),
]

ABLATED_ROWS = [
    ("CAMP-Select", 64.7, 60.2, 2.64, 2.66),
    ("Select Static", 64.7, 60.2, 2.42, 2.27),
    ("Reranker Safe", 71.2, 74.1, 2.24, 2.07),
    ("Pred Top1", 82.3, 82.0, 3.15, 3.17),
    ("Oracle MinADE", 77.0, 75.4, 1.43, 1.06),
]

CVARS = [
    ("CAMP-Select", 1397.81, 10.75, 1.08),
    ("Select Static", 1411.59, 11.46, 1.15),
    ("Pred Top1", 1434.52, 19.49, 1.95),
    ("Oracle MinADE", 1404.40, 14.14, 1.41),
    ("Reranker Safe", 1396.87, 11.87, 1.19),
]

QUAL_ROOT = (
    ROOT
    / "analysis_bundles"
    / "qualitative_k50_wide"
    / "figures"
    / "qualitative_mapaware_clearance_v2_cvxpy_full_ft20_k50_wide"
)
QUALITATIVE_ASSETS = {
    "qual_camp_improves_top1.png": QUAL_ROOT
    / "camp_improves_top1"
    / "camp_improves_top1_01_cache_36933.png",
    "qual_curve.png": QUAL_ROOT / "curve" / "curve_03_cache_17788.png",
    "qual_no_feasible_floor.png": QUAL_ROOT
    / "no_feasible_floor"
    / "no_feasible_floor_01_cache_16824.png",
    "qual_straight.png": QUAL_ROOT / "straight" / "straight_01_cache_53863.png",
    "qual_contact_sheet.png": ROOT / "analysis_bundles" / "qualitative_k50_wide" / "contact_sheet.png",
}


def ensure_dirs() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / ".matplotlib-cache").mkdir(parents=True, exist_ok=True)


def style_axes(ax, title: str | None = None) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#B8C1CC")
    ax.spines["bottom"].set_color("#B8C1CC")
    ax.tick_params(colors=INK, labelsize=10)
    ax.grid(axis="y", color="#E7EBEF", linewidth=0.8)
    if title:
        ax.set_title(title, fontsize=16, color=INK, loc="left", pad=14, weight="bold")


def save_fig(fig, name: str) -> None:
    fig.savefig(ASSET_DIR / name, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_violation_bar() -> None:
    labels = [r[0] for r in K50_ROWS]
    violation = [r[3] for r in K50_ROWS]
    colors = [
        CMU_BLUE if "CAMP-Select" in label else
        TEAL if "Finetune + CAMP" in label else
        GOLD if "Finetune Safe" in label else
        "#7A83C6" if "Static" in label else
        "#8FB76D" if "Reranker" in label else
        "#B65D5D" if "Top1" in label else
        "#8D858B"
        for label in labels
    ]
    fig, ax = plt.subplots(figsize=(10.2, 6.0))
    y = np.arange(len(labels))
    ax.barh(y, violation, color=colors, height=0.58)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Violation rate (%) - lower is better", color=INK)
    ax.set_xlim(55, 85)
    style_axes(ax, "K=50 safety frequency")
    for idx, v in enumerate(violation):
        ax.text(v + 0.5, idx, f"{v:.1f}%", va="center", fontsize=10, color=INK)
    ax.axvline(60.2, color=CMU_RED, linewidth=1.2, linestyle="--")
    ax.text(60.4, -0.7, "candidate-pool floor", fontsize=9, color=CMU_RED)
    save_fig(fig, "violation_bar.png")


def plot_tradeoff() -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.5))
    def color_for(label: str) -> str:
        if "CAMP-Select" in label:
            return CMU_BLUE
        if "Finetune + CAMP" in label:
            return TEAL
        if "Finetune Safe" in label:
            return GOLD
        if "Static" in label:
            return "#7A83C6"
        if "Reranker" in label:
            return "#8FB76D"
        if "Top1" in label:
            return "#B65D5D"
        return "#8D858B"

    for label, ade, _fde, viol, _acc, _jerk, cvar in K50_ROWS:
        ax.scatter(ade, viol, s=160 + 70 * cvar, color=color_for(label), edgecolor="white", linewidth=1.2)
        if label in {"CAMP-Select It100", "Finetune + CAMP E20", "Finetune Safe E20", "Select Static", "Pred Top1", "Oracle MinADE"}:
            dx = 0.04 if label != "Oracle MinADE" else 0.08
            dy = 0.8 if label not in {"CAMP-Select It100", "Select Static"} else -2.0
            ax.text(ade + dx, viol + dy, label.replace(" It100", ""), fontsize=8.6, color=INK)
    ax.set_xlabel("ADE - lower is better", color=INK)
    ax.set_ylabel("Violation rate (%) - lower is better", color=INK)
    ax.set_xlim(0.8, 3.4)
    ax.set_ylim(56, 85)
    style_axes(ax, "Accuracy-safety trade-off")
    ax.annotate(
        "Finetune + CAMP E20 improves accuracy while staying below pure finetuning violation",
        xy=(1.61, 63.6),
        xytext=(1.05, 58.5),
        arrowprops=dict(arrowstyle="->", color=CMU_RED, lw=1.2),
        fontsize=9,
        color=CMU_RED,
    )
    save_fig(fig, "tradeoff_scatter.png")


def plot_ablation() -> None:
    labels = [r[0] for r in ABLATED_ROWS]
    k12 = [r[1] for r in ABLATED_ROWS]
    k50 = [r[2] for r in ABLATED_ROWS]
    x = np.arange(len(labels))
    width = 0.34
    fig, ax = plt.subplots(figsize=(10.2, 5.0))
    ax.bar(x - width / 2, k12, width, label="K=12", color="#9AA9B7")
    ax.bar(x + width / 2, k50, width, label="K=50", color=CMU_BLUE)
    ax.set_ylabel("Violation rate (%) - lower is better", color=INK)
    ax.set_xticks(x, labels, rotation=14, ha="right")
    ax.set_ylim(55, 86)
    ax.legend(frameon=False, loc="upper left")
    style_axes(ax, "Candidate pool ablation")
    for idx, (v12, v50) in enumerate(zip(k12, k50)):
        delta = v50 - v12
        ax.text(idx, max(v12, v50) + 1.0, f"{delta:+.1f} pp", ha="center", fontsize=9, color=CMU_RED if delta > 0 else TEAL)
    save_fig(fig, "candidate_pool_ablation.png")


def plot_training_time() -> None:
    labels = ["CAMP-Select", "Finetune Safe"]
    hours = [10.36, 22.99]
    fig, ax = plt.subplots(figsize=(8.8, 4.2))
    y = np.arange(len(labels))
    ax.barh(y, hours, color=[CMU_BLUE, GOLD], height=0.45)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Training wall time (hours)", color=INK)
    ax.set_xlim(0, 25)
    style_axes(ax, "Training cost")
    for idx, h in enumerate(hours):
        ax.text(h + 0.5, idx, f"{h:.2f} h", va="center", fontsize=11, color=INK)
    ax.text(10.36, 1.35, "Finetuning is 2.22x slower", fontsize=11, color=CMU_RED, ha="center")
    save_fig(fig, "training_time.png")


def plot_metric_audit() -> None:
    labels = [r[0] for r in CVARS]
    clipped = [r[2] for r in CVARS]
    weighted = [r[3] for r in CVARS]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9.8, 4.8))
    ax.bar(x - 0.18, clipped, 0.36, label="Clipped sum CVaR", color="#9AA9B7")
    ax.bar(x + 0.18, weighted, 0.36, label="Weighted + clipped CVaR", color=CMU_BLUE)
    ax.set_ylabel("CVaR value", color=INK)
    ax.set_xticks(x, labels, rotation=16, ha="right")
    ax.legend(frameon=False, loc="upper left")
    style_axes(ax, "Metric audit: final scale matches training")
    ax.text(0.02, 0.88, "Unclipped diagnostic values are near 1400 and are not the final paper metric.", transform=ax.transAxes, fontsize=9, color=CMU_RED)
    save_fig(fig, "metric_audit.png")


def plot_table_image(name: str, title: str, columns: list[str], rows: list[list[str]], figsize=(11.2, 5.6), font_size=8.6) -> None:
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    ax.text(0.0, 0.98, title, transform=ax.transAxes, fontsize=16, weight="bold", color=INK, va="top")
    table = ax.table(cellText=rows, colLabels=columns, bbox=[0.0, 0.0, 1.0, 0.86], cellLoc="center", colLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    table.scale(1, 1.15)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#C8D0D8")
        cell.set_linewidth(0.6)
        if r == 0:
            cell.set_facecolor(DARK_BLUE)
            cell.set_text_props(color="white", weight="bold")
        elif r % 2 == 0:
            cell.set_facecolor("#F5F7FA")
        else:
            cell.set_facecolor("white")
        if c == 0 and r > 0:
            cell.set_text_props(ha="left")
    save_fig(fig, name)


def plot_main_results_table() -> None:
    columns = ["Method", "ADE", "FDE", "Violation", "RMS Accel.", "RMS Jerk", "CVaR weighted+clipped"]
    rows = [
        [method, f"{ade:.2f}", f"{fde:.2f}", f"{viol:.1f}%", f"{acc:.2f}", f"{jerk:.2f}", f"{cvar:.2f}"]
        for method, ade, fde, viol, acc, jerk, cvar in K50_ROWS
    ]
    plot_table_image(
        "main_k50_table.png",
        "Main K=50 map-aware clearance results",
        columns,
        rows,
        figsize=(12.8, 6.4),
        font_size=8.0,
    )


def plot_ablation_table_image() -> None:
    columns = ["Method", "K=12 ADE", "K=50 ADE", "K=12 FDE", "K=50 FDE", "K=12 Violation", "K=50 Violation", "Violation Change"]
    rows = [
        [method, f"{k12_ade:.2f}", f"{k50_ade:.2f}", "", "", f"{k12_v:.1f}%", f"{k50_v:.1f}%", f"{(k50_v - k12_v):+.1f}%"]
        for method, k12_v, k50_v, k12_ade, k50_ade in ABLATED_ROWS
    ]
    # Fill the FDE columns from the LaTeX table.
    fde_values = {
        "CAMP-Select": (4.70, 4.58),
        "Select Static": (4.25, 3.93),
        "Reranker Safe": (4.22, 3.90),
        "Pred Top1": (6.50, 6.53),
        "Oracle MinADE": (2.70, 1.84),
    }
    for row in rows:
        f12, f50 = fde_values[row[0]]
        row[3] = f"{f12:.2f}"
        row[4] = f"{f50:.2f}"
    plot_table_image(
        "candidate_ablation_table.png",
        "Candidate pool ablation: K=12 versus K=50",
        columns,
        rows,
        figsize=(12.8, 4.2),
        font_size=8.0,
    )


def plot_training_time_table() -> None:
    columns = ["Run", "CAMP Time", "Finetune Time", "Stage Wall Time", "CAMP/Finetune", "Finetune/CAMP"]
    rows = [
        ["K=12", "8.14 h", "21.00 h", "21.00 h", "0.387", "2.58"],
        ["K=50", "10.36 h", "22.99 h", "22.99 h", "0.451", "2.22"],
    ]
    plot_table_image(
        "training_time_table.png",
        "Training-time comparison",
        columns,
        rows,
        figsize=(10.8, 2.6),
        font_size=9.0,
    )


def plot_computational_graph() -> None:
    runpy.run_path(str(ROOT / "scripts" / "tools" / "render_camp_computational_graph.py"), run_name="__main__")


def plot_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(11.2, 4.8))
    ax.axis("off")
    steps = [
        ("Frozen predictor", "Trajectron++ epoch 20\nsamples K candidates"),
        ("Atom bank", "9 normalized atoms\ncomfort, speed, lane, clearance"),
        ("CAMP training", "Bradley-Terry warmup\nCVXPY Benders RU-CVaR"),
        ("Scene policy", "linear map w(x)\nTheta shape 9 x 65"),
        ("Deployment", "score candidates\nselect lowest weighted cost"),
    ]
    x0 = 0.03
    w = 0.17
    gap = 0.035
    colors = [CMU_BLUE, TEAL, GOLD, "#7A83C6", CMU_RED]
    for i, (title, body) in enumerate(steps):
        x = x0 + i * (w + gap)
        rect = plt.Rectangle((x, 0.28), w, 0.44, transform=ax.transAxes, fc="white", ec=colors[i], lw=2.0)
        ax.add_patch(rect)
        ax.text(x + 0.015, 0.62, title, transform=ax.transAxes, fontsize=13, color=colors[i], weight="bold", va="top")
        ax.text(x + 0.015, 0.54, body, transform=ax.transAxes, fontsize=10, color=INK, va="top", linespacing=1.35)
        if i < len(steps) - 1:
            ax.annotate(
                "",
                xy=(x + w + gap * 0.82, 0.50),
                xytext=(x + w + gap * 0.15, 0.50),
                xycoords=ax.transAxes,
                arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.6),
            )
    ax.text(0.03, 0.86, "CAMP separates candidate generation from risk-aware selection", transform=ax.transAxes, fontsize=17, weight="bold", color=INK)
    ax.text(0.03, 0.12, "Training uses an outer-min / inner-max convex surrogate; deployment uses a single outer-min / inner-min scoring pass.", transform=ax.transAxes, fontsize=11, color=GRAY)
    save_fig(fig, "pipeline.png")


def plot_atom_bank() -> None:
    fig, ax = plt.subplots(figsize=(11.0, 4.8))
    ax.axis("off")
    groups = [
        ("Comfort", ["early jerk", "late jerk", "full jerk", "RMS accel"], CMU_BLUE),
        ("Speed margins", ["speed@0m", "speed@0.5m", "speed@1.0m"], TEAL),
        ("Map adherence", ["lane deviation"], GOLD),
        ("Interaction", ["dynamic clearance"], CMU_RED),
    ]
    x = 0.04
    widths = [0.30, 0.25, 0.17, 0.18]
    for (title, atoms, color), width in zip(groups, widths):
        rect = plt.Rectangle((x, 0.24), width, 0.52, transform=ax.transAxes, fc="white", ec=color, lw=2.0)
        ax.add_patch(rect)
        ax.text(x + 0.018, 0.67, title, transform=ax.transAxes, fontsize=14, weight="bold", color=color, va="top")
        for j, atom in enumerate(atoms):
            ax.text(x + 0.026, 0.57 - j * 0.095, f"- {atom}", transform=ax.transAxes, fontsize=10.5, color=INK, va="top")
        x += width + 0.025
    ax.text(0.04, 0.88, "Nine-atom representation of each candidate trajectory", transform=ax.transAxes, fontsize=17, weight="bold", color=INK)
    ax.text(
        0.04,
        0.11,
        "All atoms are normalized with run-specific scales and clipped at 10.0 before training and selection diagnostics.",
        transform=ax.transAxes,
        fontsize=11,
        color=GRAY,
    )
    save_fig(fig, "atom_bank.png")


def plot_evidence_chain() -> None:
    fig, ax = plt.subplots(figsize=(11.0, 4.8))
    ax.axis("off")
    steps = [
        ("Protocol", "same base model\nsame map-aware cache\nsame atom scaling"),
        ("Main result", "K=50 table\nweighted-clipped\nCVaR_0.90"),
        ("Ablation", "K=12 -> K=50\ncandidate coverage\n-4.5 pp violation"),
        ("Audit", "raw CVaR shift\nexplained by\nmetric definition"),
        ("Diagnostics", "18 map overlays\nfloor cases\nCAMP vs top-1"),
    ]
    x0 = 0.035
    w = 0.17
    colors = [DARK_BLUE, CMU_BLUE, TEAL, GOLD, CMU_RED]
    for i, (head, body) in enumerate(steps):
        x = x0 + i * 0.19
        ax.add_patch(plt.Rectangle((x, 0.30), w, 0.44, transform=ax.transAxes, fc="#FFFFFF", ec=colors[i], lw=2))
        ax.text(x + 0.014, 0.65, head, transform=ax.transAxes, fontsize=13, weight="bold", color=colors[i], va="top")
        ax.text(x + 0.014, 0.55, body, transform=ax.transAxes, fontsize=10, color=INK, va="top", linespacing=1.3)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + w + 0.018, 0.52), xytext=(x + w + 0.002, 0.52), xycoords=ax.transAxes, arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.5))
    ax.text(0.035, 0.86, "Evidence chain used in the revised deck", transform=ax.transAxes, fontsize=17, weight="bold", color=INK)
    ax.text(0.035, 0.14, "The presentation separates paper-ready results from historical/debug tables and uses qualitative figures as diagnostics, not additional metrics.", transform=ax.transAxes, fontsize=11, color=GRAY)
    save_fig(fig, "evidence_chain.png")


def plot_feasibility_floor() -> None:
    values = [39.8, 60.2]
    labels = ["scenes with >=1 feasible candidate", "no feasible candidate"]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    wedges, _ = ax.pie(values, startangle=90, colors=[TEAL, CMU_RED], wedgeprops=dict(width=0.42, edgecolor="white"))
    ax.text(0, 0.06, "60.2%", ha="center", va="center", fontsize=26, weight="bold", color=CMU_RED)
    ax.text(0, -0.18, "floor", ha="center", va="center", fontsize=13, color=INK)
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(0.86, 0.5), frameon=False, fontsize=10)
    ax.set_title("Feasibility floor in the K=50 eval cache", fontsize=15, weight="bold", color=INK)
    save_fig(fig, "feasibility_floor.png")


def copy_qualitative_assets() -> None:
    for out_name, src in QUALITATIVE_ASSETS.items():
        if src.exists():
            shutil.copyfile(src, ASSET_DIR / out_name)


def crop_qualitative_case() -> None:
    src = ROOT / "compare_crash_vs_safe.png"
    if not src.exists():
        return
    im = Image.open(src).convert("RGB")
    width, height = im.size
    # Remove plot margins and keep the useful map/trajectory/legend region.
    crop_box = (
        int(width * 0.05),
        int(height * 0.05),
        int(width * 0.96),
        int(height * 0.92),
    )
    cropped = im.crop(crop_box)
    cropped.thumbnail((1800, 1050), Image.LANCZOS)
    cropped.save(ASSET_DIR / "qualitative_case.png", quality=95)


def markdown_table(rows: list[tuple[str, float, float, float, float, float, float]]) -> str:
    lines = [
        "| Method | ADE | FDE | Violation | RMS Acc. | RMS Jerk | Safety CVaR |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for method, ade, fde, viol, acc, jerk, cvar in rows:
        lines.append(f"| {method} | {ade:.2f} | {fde:.2f} | {viol:.1f}% | {acc:.2f} | {jerk:.2f} | {cvar:.2f} |")
    return "\n".join(lines)


def write_markdown() -> None:
    md = f"""# CAMP Map-Aware Clearance Results Summary

Corrective Adaptation for Motion Prediction (CAMP)

**Map-aware clearance experiments, results, diagnostics, and artifacts**

Carnegie Mellon University Research Collaboration

::: notes
This deck is constrained to short_methods_results_summary.tex. The audience has technical background but no project-specific context, so define all abbreviations before using them heavily.
:::

# Deck Structure

| Section | Source section in the tex |
| :--- | :--- |
| Scope and protocol | Scope; Experimental Protocol |
| Training methods | CAMP-Select; Finetune Safe; Finetune + CAMP-Select; Other Baselines |
| Quantitative results | Main K=50 Results; Candidate Pool Ablation |
| Diagnostics | Metric Definition Audit; Qualitative Visualization Set |
| Cost and implementation | Training Time; Loss and Implementation Notes |
| Summary | Key Findings; Paper-Ready Summary; Artifacts Used |

::: notes
Use this slide to signal that the PowerPoint follows the LaTeX summary rather than a new narrative.
:::

# Terminology I

| Term | Meaning in this presentation |
| :--- | :--- |
| CAMP | Corrective Adaptation for Motion Prediction. |
| CAMP-Select | CAMP used as a post-hoc candidate selector. |
| Trajectron++ | Pretrained multimodal trajectory prediction model used as the base predictor. |
| Candidate pool size K | Number of candidate trajectories sampled per scenario. |
| Atom | Normalized cost feature of a candidate trajectory. |
| Map-aware clearance | Evaluation setting using vector-map context and dynamic-neighbor clearance. |

::: notes
This slide is added for audience context. It does not add new experimental claims.
:::

# Terminology II

| Abbreviation | Full name and role |
| :--- | :--- |
| ADE | Average Displacement Error; average prediction error over the horizon. |
| FDE | Final Displacement Error; endpoint prediction error. |
| RMS | Root Mean Square; used for acceleration and jerk comfort metrics. |
| CVaR | Conditional Value-at-Risk; here it measures 0.90 tail risk. |
| RU-CVaR | Rockafellar-Uryasev Conditional Value-at-Risk formulation. |
| NLL | Negative Log-Likelihood; prediction loss used in finetuning. |
| MLP | Multi-Layer Perceptron; used by the reranker baseline. |
| CVXPY | Python package for convex optimization modeling. |

::: notes
These abbreviations appear later in tables and method names. Define them once up front.
:::

# Scope

The current main result uses:

- Main run tag: `mapaware_clearance_v2_cvxpy_full_ft20_k50`.
- Ablation run tag: `mapaware_clearance_v2_cvxpy_full_ft20_clean`.
- Rebuilt map-aware cache with dynamic-neighbor clearance enabled.
- Base predictor: Trajectron++ checkpoint epoch 20.
- CAMP trainer: historical CVXPY Benders master.
- Evaluation follows the training atom normalization and clipping convention.

::: notes
This is a direct paraphrase of the Scope section. CVXPY is a Python convex optimization modeling package; the temporary Torch master is only mentioned in the tex as not being used.
:::

# Experimental Protocol I

| Item | Setting from the tex |
| :--- | :--- |
| Base predictor | Same pretrained Trajectron++ base model at epoch 20. |
| Candidate pool | K=50 candidates for the main run; K=12 for the ablation. |
| Full cache | K=50 train cache has 245,463 scenarios; eval cache has 66,843 scenarios. |
| Map source | Cache reports `vector_map` for all train/eval scenarios. |

::: notes
This splits the protocol into two slides to avoid overflow.
:::

# Experimental Protocol II

| Item | Setting from the tex |
| :--- | :--- |
| Atom bank | 9 atoms: jerk, RMS acceleration, speed margins, lane deviation, dynamic-obstacle clearance. |
| Atom scaling | Recomputed for map-aware candidates. |
| Clipping | Normalized atoms are clipped to 10.0. |
| Evaluation | Same atom normalization and clipping convention as training. |

::: notes
The tex lists the exact nine atoms. This slide groups them by type to stay readable.
:::

# CAMP Computational Graph

![CAMP computational graph]({ASSET_DIR.as_posix()}/computational_graph.png){{width=96%}}

::: notes
This diagram is grounded in the current implementation: cache_dataset.py for shared extraction, train_camp_select.py for BT warmup and CVXPY Benders training, and eval_camp_select.py for inference-time selection.
:::

# Evaluation Metrics

| Metric | Meaning in the tex |
| :--- | :--- |
| ADE and FDE | Average and final displacement error. |
| Violation rate | Hard safety/feasibility failure. |
| RMS acceleration and RMS jerk | Comfort metrics based on root mean square values. |
| Safety CVaR | Weighted and clipped Conditional Value-at-Risk at alpha = 0.90. |
| Diagnostic CVaR | Unclipped sum retained only for metric-audit diagnosis. |

::: notes
The final Safety CVaR convention is detailed later on the Metric Definition Audit slide.
:::

# CAMP-Select

Given scene embedding \\(\\phi(x)\\) and candidate atom vector \\(A(x,y_k)\\), Corrective Adaptation for Motion Prediction learns:

$$w(x) = \\mathrm{{normalize}}_+(\\Theta [\\phi(x); 1]).$$

It selects the candidate with the lowest weighted atom cost.

The current checkpoint stores \\(\\Theta\\) with shape \\(9 \\times 65\\).

::: notes
This slide should match the CAMP-Select subsection closely. Keep the equation central.
:::

# CAMP Training Details

| Parameter | Value from the tex |
| :--- | :--- |
| Risk objective | Conditional Value-at-Risk risk |
| Alpha | 0.9 |
| Solver | CLARABEL conic optimization solver |
| Benders iterations | 100 |
| Master batch size | 500 |
| Max cuts per scene | 120 |
| Narrative status | Paper-consistent CAMP trainer |

::: notes
This separates solver details from the conceptual CAMP slide so the layout is cleaner.
:::

# Finetune Safe: Objective

Finetune Safe starts from the same Trajectron++ epoch-20 checkpoint.

It optimizes:

$$\\mathcal{{L}}_{{total}} = \\mathcal{{L}}_{{NLL}} + w(t)s_{{bal}}\\mathcal{{L}}_{{safety}}.$$

Here, NLL means Negative Log-Likelihood.

The safety loss uses Conditional Value-at-Risk at alpha = 0.90.

::: notes
This slide defines the finetuning objective without crowding the settings onto the same slide.
:::

# Finetune Safe: Settings

Safety atoms used in the loss:

- speed0, speed0.5, speed1.0
- lane
- clearance

Run settings from the tex:

- Atom clipping at 10.0.
- Clearance safety radius 1.0 m.
- Clearance soft margin 4.0 m.
- Clearance atom radius 5.0 m.
- Evaluated at epochs 5, 10, and 20.

::: notes
Use this slide to distinguish finetuning from selection. These details are all from the Finetune Safe subsection.
:::

# Finetune + CAMP and Baselines

| Method | Description from the tex |
| :--- | :--- |
| Finetune + CAMP-Select | Evaluates candidates from finetuned checkpoints, then applies CAMP selector. |
| Embedding convention | Uses the base epoch-20 encoder embedding for apples-to-apples comparison. |
| Pred Top1 | Base model top-1 prediction without adaptation. |
| Oracle MinADE | Chooses candidate with minimum Average Displacement Error against ground truth. |
| Select Static | Fixed-weight selector trained from offline preferences. |
| Reranker Safe | Multi-Layer Perceptron reranker over scene embedding and normalized atoms. |

::: notes
This is directly scoped to the Finetune + CAMP and Other Baselines subsections.
:::

# Main K=50 Result Table

![Main K50 table]({ASSET_DIR.as_posix()}/main_k50_table.png){{width=96%}}

::: notes
The table is rendered as a single figure for layout stability, but the numbers match the LaTeX table exactly.
:::

# Main Result Reading

From the Key Findings section:

- CAMP-Select and Select Static have the lowest violation rate: 60.2%.
- Finetune Safe gives the best pointwise accuracy and comfort.
- Finetune Safe also has higher violation.
- Finetune + CAMP is the best accuracy-safety compromise.
- The Conditional Value-at-Risk scale shift is a reporting correction.

::: notes
These bullets are intentionally copied from the Key Findings content, not newly inferred claims.
:::

# Safety Frequency View

![Violation bar chart]({ASSET_DIR.as_posix()}/violation_bar.png){{width=92%}}

CAMP-Select and Select Static both reach 60.2% violation.

::: notes
The chart is derived from the K=50 table. State the number, then move to the feasibility-floor explanation.
:::

# Candidate Pool Ablation Table

![Candidate pool ablation table]({ASSET_DIR.as_posix()}/candidate_ablation_table.png){{width=96%}}

::: notes
The ablation table follows the Candidate Pool Ablation section. It compares Average Displacement Error, Final Displacement Error, and violation only because K=12 used the older CVaR reporting.
:::

# Candidate Pool Interpretation

The tex states that the ablation separates selector quality from candidate availability.

- Increasing K from 12 to 50 reduces CAMP-Select violation from 64.7% to 60.2%.
- Select Static shows the same violation-rate improvement.
- Oracle MinADE improves from 1.43/2.70 to 1.06/1.84 in ADE/FDE.
- The candidate set itself becomes stronger.

::: notes
Keep the causal language exactly as in the tex: improved candidate coverage drives much of the better safety frontier.
:::

# Metric Definition Audit

The final paper table uses the training-consistent metric:

$$\\mathrm{{SafetyCVaR}} =
\\mathrm{{CVaR}}_{{0.9}}\\left(0.1\\sum_{{r=4}}^8 \\min(A_r/scale_r, 10)\\right).$$

Large intermediate Conditional Value-at-Risk values came from reporting the unclipped sum of normalized safety atoms after dynamic clearance was restored.

::: notes
This slide should prevent confusion between raw/unclipped diagnostics and weighted-clipped final reporting.
:::

# Metric Audit View

![Metric audit]({ASSET_DIR.as_posix()}/metric_audit.png){{width=90%}}

The final table reports the weighted+clipped column.

The 1400-scale values are retained only as diagnostic audit values.

::: notes
This chart is derived from the Metric Definition Audit table.
:::

# Feasibility Floor

![Feasibility floor]({ASSET_DIR.as_posix()}/feasibility_floor.png){{width=70%}}

The K=50 evaluation cache contains 66,843 scenarios.

Only 39.8% have at least one feasible candidate, so the no-feasible-candidate rate is 60.2%.

::: notes
The tex explicitly says this explains why CAMP-Select and Select Static both reach exactly 60.2% violation.
:::

# Qualitative Visualization Set

The generated qualitative set contains 18 figures.

Each category has 3 matched examples:

- straight
- curve
- obstacle
- intersection-like
- no-feasible-floor
- CAMP improves top-1

::: notes
This content should match the Qualitative Visualization Set section, including the "diagnostics, not metrics" framing.
:::

# Qualitative Figure Construction

The figures are map-overlay comparisons from the K=50 evaluation cache.

The visualization script:

- selects representative cache cases;
- matches cache items back to the unshuffled nuScenes validation dataloader;
- uses ground-truth trajectory for matching;
- shows map context, agent boxes, ground truth, candidates, and selected trajectories.

::: notes
This splits the long qualitative description so the previous slide does not overflow.
:::

# Recommended Qualitative Figure: Curve

![Curve example]({ASSET_DIR.as_posix()}/qual_curve.png){{width=86%}}

Recommended in the tex as a clear curved-road behavior example with visible separation among methods.

::: notes
This is one of the four recommended qualitative figures listed in the tex.
:::

# Recommended Qualitative Figure: No-Feasible Floor

![No feasible floor]({ASSET_DIR.as_posix()}/qual_no_feasible_floor.png){{width=86%}}

Recommended in the tex because it shows why violation cannot go below the candidate-pool floor in some scenes.

::: notes
Use this as the visual companion to the feasibility-floor slide.
:::

# Recommended Qualitative Figure: CAMP Improves Top1

![CAMP improves Top1]({ASSET_DIR.as_posix()}/qual_camp_improves_top1.png){{width=80%}}

Recommended in the tex because CAMP avoids a high-safety-cost top-1 behavior.

::: notes
Do not generalize from one image; the tex frames these as qualitative diagnostics.
:::

# Training Time

![Training time table]({ASSET_DIR.as_posix()}/training_time_table.png){{width=92%}}

K=50 timing:

- CAMP takes 10.36 h.
- Finetune Safe takes 22.99 h.
- CAMP/finetune ratio is 0.451.
- Finetuning is about 2.22 times slower.

::: notes
The tex adds that CAMP time is dominated by CVXPY master solves as cuts accumulate.
:::

# Loss and Implementation Notes I

The tex records two implementation caveats:

- Current reranker losses are not directly comparable to older reranker losses.
- Earlier runs used different candidate pools.
- Earlier runs sometimes used hard-coded atom scales.
- Some intermediate experiments had incomplete dynamic-neighbor clearance.

::: notes
This slide explains why changed loss magnitude should not be read as optimization failure.
:::

# Loss and Implementation Notes II

The current implementation is described as more defensible because learned selectors share:

- the same base model;
- the same candidate cache;
- full map-aware clearance atoms;
- run-specific atom scales;
- atom clipping at 10.0;
- safety regularization with lambda_safe = 0.1.

::: notes
This slide continues the Loss and Implementation Notes section while keeping the layout short.
:::

# Key Findings I

1. Candidate coverage is a real bottleneck.
2. CAMP remains the strongest safety-frequency selector.
3. Finetune Safe gives the best pointwise accuracy and comfort, but higher violation.

::: notes
This is the first half of the Key Findings section.
:::

# Key Findings II

4. Finetune + CAMP is the best accuracy-safety compromise.
5. CAMP is substantially cheaper than finetuning.
6. The Conditional Value-at-Risk scale shift is a reporting correction, not a retraining change.

::: notes
This is the second half of the Key Findings section. Splitting prevents text overflow and lets the audience absorb the findings.
:::

# Paper-Ready Summary I

Increasing the candidate pool from 12 to 50 substantially improves the safety-quality frontier of selection-based methods.

CAMP-Select reduces violation from 64.7% to 60.2%.

This indicates that a major bottleneck lies in candidate coverage rather than downstream selection alone.

::: notes
This slide paraphrases the first part of the Paper-Ready Summary section.
:::

# Paper-Ready Summary II

Under candidate pool size K=50:

- Finetune Safe achieves the best Average Displacement Error, Final Displacement Error, and smoothness.
- CAMP-Select and Select Static obtain the lowest violation rate.
- Finetune + CAMP provides a useful middle ground.
- CAMP takes 10.36 h, compared with 22.99 h for finetuning.

::: notes
This slide finishes the Paper-Ready Summary section while expanding ADE/FDE for the audience.
:::

# Artifacts Used: Bundles

The tex lists these top-level bundles:

- `table2_k12_k50_results_bundle.tar.gz`
- `table2_logs_bundle.tar.gz`
- `table2_k50_weighted_cvar_bundle.tar.gz`
- `qualitative_figures_mapaware_clearance_v2_cvxpy_full_ft20_k50_wide.tar.gz`

::: notes
These are the top-level bundles listed in the Artifacts Used section.
:::

# Artifacts Used: Result Files

Additional files listed in the tex:

- K=50 final table.
- K=50 metric audit.
- K=50 qualitative case list.
- K=12 final table.

::: notes
End with reproducibility. This slide is intentionally short to avoid overflowing the slide.
:::
"""
    MARKDOWN_OUT.write_text(md, encoding="utf-8")


def qn(namespace: str, tag: str) -> str:
    namespaces = {"p": P_NS, "a": A_NS, "r": R_NS}
    return f"{{{namespaces[namespace]}}}{tag}"


def emu(inches: float) -> int:
    return int(round(inches * EMU_PER_INCH))


def srgb(color: str) -> str:
    return color.strip().lstrip("#").upper()


def add_solid_fill(parent: etree._Element, color: str) -> None:
    fill = etree.SubElement(parent, qn("a", "solidFill"))
    etree.SubElement(fill, qn("a", "srgbClr"), val=srgb(color))


def add_no_line(parent: etree._Element) -> None:
    ln = etree.SubElement(parent, qn("a", "ln"))
    etree.SubElement(ln, qn("a", "noFill"))


def make_rect(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, color: str) -> etree._Element:
    sp = etree.Element(qn("p", "sp"))
    nv = etree.SubElement(sp, qn("p", "nvSpPr"))
    etree.SubElement(nv, qn("p", "cNvPr"), id=str(shape_id), name=name)
    etree.SubElement(nv, qn("p", "cNvSpPr"))
    etree.SubElement(nv, qn("p", "nvPr"))
    sp_pr = etree.SubElement(sp, qn("p", "spPr"))
    xfrm = etree.SubElement(sp_pr, qn("a", "xfrm"))
    etree.SubElement(xfrm, qn("a", "off"), x=str(x), y=str(y))
    etree.SubElement(xfrm, qn("a", "ext"), cx=str(cx), cy=str(cy))
    geom = etree.SubElement(sp_pr, qn("a", "prstGeom"), prst="rect")
    etree.SubElement(geom, qn("a", "avLst"))
    add_solid_fill(sp_pr, color)
    add_no_line(sp_pr)
    return sp


def make_textbox(
    shape_id: int,
    name: str,
    text: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    size_pt: float,
    color: str,
    bold: bool = False,
    align: str = "l",
) -> etree._Element:
    sp = etree.Element(qn("p", "sp"))
    nv = etree.SubElement(sp, qn("p", "nvSpPr"))
    etree.SubElement(nv, qn("p", "cNvPr"), id=str(shape_id), name=name)
    etree.SubElement(nv, qn("p", "cNvSpPr"), txBox="1")
    etree.SubElement(nv, qn("p", "nvPr"))
    sp_pr = etree.SubElement(sp, qn("p", "spPr"))
    xfrm = etree.SubElement(sp_pr, qn("a", "xfrm"))
    etree.SubElement(xfrm, qn("a", "off"), x=str(x), y=str(y))
    etree.SubElement(xfrm, qn("a", "ext"), cx=str(cx), cy=str(cy))
    geom = etree.SubElement(sp_pr, qn("a", "prstGeom"), prst="rect")
    etree.SubElement(geom, qn("a", "avLst"))
    etree.SubElement(sp_pr, qn("a", "noFill"))
    add_no_line(sp_pr)
    tx_body = etree.SubElement(sp, qn("p", "txBody"))
    etree.SubElement(tx_body, qn("a", "bodyPr"), wrap="none", anchor="ctr")
    etree.SubElement(tx_body, qn("a", "lstStyle"))
    para = etree.SubElement(tx_body, qn("a", "p"))
    etree.SubElement(para, qn("a", "pPr"), algn=align)
    run = etree.SubElement(para, qn("a", "r"))
    attrs = {"lang": "en-US", "sz": str(int(round(size_pt * 100)))}
    if bold:
        attrs["b"] = "1"
    r_pr = etree.SubElement(run, qn("a", "rPr"), **attrs)
    add_solid_fill(r_pr, color)
    etree.SubElement(r_pr, qn("a", "latin"), typeface="Aptos")
    etree.SubElement(run, qn("a", "t")).text = text
    return sp


def style_slide_xml(xml_bytes: bytes, slide_index: int, slide_count: int, slide_w: int, slide_h: int) -> bytes:
    xml = etree.fromstring(xml_bytes)
    sp_tree = xml.find(".//p:spTree", namespaces={"p": P_NS})
    if sp_tree is None:
        return xml_bytes
    existing_ids = [
        int(el.get("id"))
        for el in xml.xpath(".//p:cNvPr[@id]", namespaces={"p": P_NS})
        if (el.get("id") or "").isdigit()
    ]
    next_id = max(existing_ids, default=1000) + 1

    bg_shapes = [
        make_rect(next_id, "CMU blue top rule", 0, 0, slide_w, emu(0.035), CMU_BLUE),
        make_rect(next_id + 1, "CMU red top accent", 0, emu(0.035), slide_w, emu(0.018), CMU_RED),
        make_rect(next_id + 2, "CMU bottom rule", 0, slide_h - emu(0.055), slide_w, emu(0.025), "#C8D0D8"),
    ]
    for offset, shape in enumerate(bg_shapes):
        sp_tree.insert(2 + offset, shape)

    footer_left = make_textbox(
        next_id + 4,
        "CMU footer left",
        "CAMP map-aware clearance research summary",
        emu(0.35),
        slide_h - emu(0.32),
        emu(5.0),
        emu(0.18),
        7.5,
        GRAY,
    )
    footer_right = make_textbox(
        next_id + 5,
        "CMU footer right",
        f"May 2026 | {slide_index}/{slide_count}",
        slide_w - emu(3.0),
        slide_h - emu(0.32),
        emu(2.65),
        emu(0.18),
        7.5,
        GRAY,
        align="r",
    )
    for shape in [footer_left, footer_right]:
        sp_tree.append(shape)

    return etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)


def postprocess_pptx(raw_pptx: Path, final_pptx: Path) -> None:
    with zipfile.ZipFile(raw_pptx, "r") as zin:
        presentation_xml = etree.fromstring(zin.read("ppt/presentation.xml"))
        size_el = presentation_xml.find(".//p:sldSz", namespaces={"p": P_NS})
        slide_w = int(size_el.get("cx")) if size_el is not None else emu(13.333)
        slide_h = int(size_el.get("cy")) if size_el is not None else emu(7.5)
        slide_names = sorted(
            [
                name
                for name in zin.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            ],
            key=lambda n: int(Path(n).stem.replace("slide", "")),
        )
        slide_count = len(slide_names)
        theme_bytes = None
        if REFERENCE_PPTX.exists():
            with zipfile.ZipFile(REFERENCE_PPTX, "r") as ref_zip:
                if "ppt/theme/theme1.xml" in ref_zip.namelist():
                    theme_bytes = ref_zip.read("ppt/theme/theme1.xml")

        with zipfile.ZipFile(final_pptx, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename in slide_names:
                    slide_index = slide_names.index(info.filename) + 1
                    data = style_slide_xml(data, slide_index, slide_count, slide_w, slide_h)
                elif info.filename == "ppt/theme/theme1.xml" and theme_bytes is not None:
                    data = theme_bytes
                zout.writestr(info.filename, data)


def run_pandoc() -> None:
    cmd = [
        "pandoc",
        str(MARKDOWN_OUT),
        "--slide-level=1",
        "-o",
        str(RAW_PPTX_OUT),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    postprocess_pptx(RAW_PPTX_OUT, PPTX_OUT)


def main() -> None:
    ensure_dirs()
    plot_computational_graph()
    plot_pipeline()
    plot_atom_bank()
    plot_evidence_chain()
    plot_violation_bar()
    plot_tradeoff()
    plot_ablation()
    plot_feasibility_floor()
    plot_metric_audit()
    plot_training_time()
    plot_main_results_table()
    plot_ablation_table_image()
    plot_training_time_table()
    copy_qualitative_assets()
    write_markdown()
    run_pandoc()
    print(PPTX_OUT)


if __name__ == "__main__":
    main()
