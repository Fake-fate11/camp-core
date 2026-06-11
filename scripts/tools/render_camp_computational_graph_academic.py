from __future__ import annotations

import os
import textwrap
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[2] / ".matplotlib-cache"),
)

import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "ppt_assets" / "camp_research_briefing"
ADAPTIVE_ASSET_DIR = ROOT / "ppt_assets" / "adaptive_rebuilt_elements"

INK = "#111827"
MUTED = "#4B5563"
GRAY = "#6B7280"
TRAIN = "#1D4ED8"
INFER = "#047857"
ARTIFACT = "#B45309"


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def box(
    ax,
    xy: tuple[float, float],
    wh: tuple[float, float],
    title: str,
    body: str = "",
    edge: str = GRAY,
    title_color: str = INK,
    lw: float = 1.35,
    title_size: float = 8.7,
    body_size: float = 7.2,
    body_width: int = 28,
):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.009,rounding_size=0.010",
        linewidth=lw,
        edgecolor=edge,
        facecolor="white",
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h - 0.012,
        title,
        ha="center",
        va="top",
        fontsize=title_size,
        fontweight="bold",
        color=title_color,
        zorder=3,
    )
    if body:
        ax.text(
            x + w / 2,
            y + h / 2 - 0.012,
            wrap(body, body_width),
            ha="center",
            va="center",
            fontsize=body_size,
            color=INK,
            linespacing=1.16,
            zorder=3,
        )
    return patch


def panel(
    ax,
    xy: tuple[float, float],
    wh: tuple[float, float],
    title: str,
    subtitle: str,
    edge: str,
):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.014",
        linewidth=2.0,
        edgecolor=edge,
        facecolor="white",
        zorder=0,
    )
    ax.add_patch(patch)
    ax.text(x + 0.018, y + h - 0.030, title, ha="left", va="top", fontsize=12.0, fontweight="bold", color=edge, zorder=3)
    ax.text(x + 0.018, y + h - 0.060, subtitle, ha="left", va="top", fontsize=7.5, color=MUTED, zorder=3)
    return patch


def arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str,
    lw: float = 1.55,
    linestyle: str = "-",
    rad: float = 0.0,
):
    arr = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=10,
        linewidth=lw,
        linestyle=linestyle,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=3,
        shrinkB=3,
        zorder=5,
    )
    ax.add_patch(arr)
    return arr


def loop_arrow(
    ax,
    center: tuple[float, float],
    width: float,
    height: float,
    color: str,
):
    x, y = center
    arc = Arc((x, y), width, height, theta1=35, theta2=335, linewidth=1.8, color=color, zorder=4)
    ax.add_patch(arc)
    arrow(ax, (x + width * 0.39, y + height * 0.20), (x + width * 0.37, y + height * 0.30), color=color, lw=1.8)


def draw() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(16.0, 9.0))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.035,
        0.965,
        "CAMP-Select Architecture and Computational Graph",
        ha="left",
        va="top",
        fontsize=18,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        0.035,
        0.932,
        "Frozen candidate generation, offline Θ learning, and one-shot scene-conditioned selection",
        ha="left",
        va="top",
        fontsize=9.5,
        color=MUTED,
    )

    panel(
        ax,
        (0.025, 0.105),
        (0.245, 0.790),
        "Shared Frozen Extraction",
        "Used for cache construction and deployment",
        GRAY,
    )
    panel(
        ax,
        (0.300, 0.545),
        (0.670, 0.350),
        "Training Time Workflow",
        "Offline optimization: Θ is learned here",
        TRAIN,
    )
    panel(
        ax,
        (0.300, 0.105),
        (0.670, 0.355),
        "Inference Time Workflow",
        "One-shot deployment: Θ is fixed; w(x) changes per scene",
        INFER,
    )

    # Shared extraction and architecture notation.
    b_in = box(
        ax,
        (0.055, 0.788),
        (0.185, 0.060),
        "Scene Context x",
        "map, agents, obstacles, speed limits, history",
        GRAY,
        body_width=28,
    )
    b_tpp = box(
        ax,
        (0.055, 0.660),
        (0.185, 0.075),
        "Frozen Trajectron++",
        "encoder and sampler; base predictor is not trained by CAMP-Select",
        GRAY,
        body_width=27,
    )
    b_phi = box(ax, (0.045, 0.535), (0.088, 0.070), "ϕ(x)", "64-D scene embedding", GRAY, body_width=16)
    b_y = box(ax, (0.151, 0.535), (0.088, 0.070), "Y={yₖ}", "fixed candidate pool, K=50", GRAY, body_width=16)
    b_atom = box(
        ax,
        (0.055, 0.370),
        (0.185, 0.095),
        "Atom Evaluator",
        "A(x,yₖ) ∈ R⁹ and hard feasibility mask mₖ",
        GRAY,
        body_width=27,
    )
    b_atoms = box(
        ax,
        (0.045, 0.190),
        (0.205, 0.120),
        "Nine Atom Costs",
        "jerk early, jerk late, jerk full; RMS acceleration; speed margins 0.0, 0.5, 1.0; lane deviation; clearance",
        GRAY,
        title_size=8.3,
        body_size=6.5,
        body_width=29,
    )

    arrow(ax, (0.147, 0.788), (0.147, 0.735), GRAY)
    arrow(ax, (0.147, 0.660), (0.090, 0.605), GRAY)
    arrow(ax, (0.147, 0.660), (0.195, 0.605), GRAY)
    arrow(ax, (0.090, 0.535), (0.120, 0.465), GRAY, rad=-0.15)
    arrow(ax, (0.195, 0.535), (0.175, 0.465), GRAY)
    arrow(ax, (0.147, 0.370), (0.147, 0.310), GRAY)

    # Model architecture reference strip.
    ax.text(
        0.304,
        0.505,
        "Model Architecture and Notation Reference",
        ha="left",
        va="center",
        fontsize=10.8,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        0.570,
        0.505,
        "x → Trajectron++ → ϕ(x), Y;  (x,yₖ) → Aₖ,mₖ;  w(x)=ΠΔ(Θ[ϕ(x);1]);  sₖ=w(x)ᵀAₖ;  k*=arg minₖ sₖ",
        ha="left",
        va="center",
        fontsize=7.6,
        color=MUTED,
    )
    ax.plot([0.300, 0.970], [0.485, 0.485], color="#D1D5DB", linewidth=1.2, zorder=1)

    # Training workflow.
    tr_cache = box(
        ax,
        (0.326, 0.770),
        (0.112, 0.067),
        "Offline Cache",
        "ϕ, Y, raw A, m, gt trajectory, gt atoms",
        ARTIFACT,
        ARTIFACT,
        title_size=8.2,
        body_size=6.8,
        body_width=18,
    )
    tr_norm = box(
        ax,
        (0.462, 0.770),
        (0.114, 0.067),
        "Normalize and Clip",
        "Aₙ = clip(A / atom_scales, 0, 10)",
        TRAIN,
        TRAIN,
        title_size=8.2,
        body_size=6.8,
        body_width=18,
    )
    tr_bt = box(
        ax,
        (0.600, 0.770),
        (0.118, 0.067),
        "Bradley-Terry Warmup",
        "compare gt atoms with candidate atoms",
        TRAIN,
        TRAIN,
        title_size=8.0,
        body_size=6.7,
        body_width=18,
    )
    tr_anchor = box(
        ax,
        (0.742, 0.770),
        (0.096, 0.067),
        "Anchor Weights",
        "global prior w_off",
        ARTIFACT,
        ARTIFACT,
        title_size=8.0,
        body_size=6.7,
        body_width=14,
    )
    tr_saved = box(
        ax,
        (0.855, 0.770),
        (0.090, 0.067),
        "Saved Θ",
        "checkpoint, 9 × 65",
        ARTIFACT,
        ARTIFACT,
        title_size=8.0,
        body_size=6.7,
        body_width=14,
    )

    b_loop = FancyBboxPatch(
        (0.330, 0.595),
        0.500,
        0.125,
        boxstyle="round,pad=0.010,rounding_size=0.010",
        linewidth=1.7,
        linestyle="--",
        edgecolor=TRAIN,
        facecolor="white",
        zorder=1,
    )
    ax.add_patch(b_loop)
    ax.text(0.344, 0.700, "Benders Master Loop", ha="left", va="center", fontsize=9.2, fontweight="bold", color=TRAIN, zorder=3)
    tr_w = box(ax, (0.345, 0.622), (0.095, 0.055), "Current Weights", "wᵢ=ΠΔ(Θ[ϕᵢ;1])", TRAIN, TRAIN, title_size=7.1, body_size=6.0, body_width=15)
    tr_imax = box(ax, (0.462, 0.622), (0.085, 0.055), "Inner Max", "kmax=arg maxₖ wᵢᵀAᵢₖ", TRAIN, TRAIN, title_size=7.1, body_size=6.0, body_width=14)
    tr_cut = box(ax, (0.570, 0.622), (0.090, 0.055), "Cut Generation", "gᵢ=Aᵢ,kmax", TRAIN, TRAIN, title_size=7.1, body_size=6.0, body_width=14)
    tr_min = box(
        ax,
        (0.682, 0.610),
        (0.125, 0.076),
        "CVXPY Outer Min",
        "updates Θ, η, s, q; simplex constraints; Benders cuts; CVaR α=0.9; regularization",
        TRAIN,
        TRAIN,
        title_size=7.1,
        body_size=5.7,
        body_width=20,
    )

    arrow(ax, (0.270, 0.430), (0.326, 0.803), ARTIFACT, linestyle="--", rad=0.12)
    arrow(ax, (0.438, 0.803), (0.462, 0.803), TRAIN)
    arrow(ax, (0.576, 0.803), (0.600, 0.803), TRAIN)
    arrow(ax, (0.718, 0.803), (0.742, 0.803), TRAIN)
    arrow(ax, (0.519, 0.770), (0.392, 0.720), TRAIN, rad=0.15)
    arrow(ax, (0.440, 0.650), (0.462, 0.650), TRAIN)
    arrow(ax, (0.547, 0.650), (0.570, 0.650), TRAIN)
    arrow(ax, (0.660, 0.650), (0.682, 0.650), TRAIN)
    arrow(ax, (0.742, 0.770), (0.748, 0.686), ARTIFACT)
    arrow(ax, (0.682, 0.675), (0.440, 0.675), TRAIN, rad=0.23)
    loop_arrow(ax, (0.575, 0.648), 0.420, 0.110, TRAIN)
    arrow(ax, (0.807, 0.650), (0.855, 0.803), ARTIFACT, rad=-0.18)
    ax.text(0.842, 0.690, "Θ updated during training", ha="left", va="center", fontsize=7.0, color=TRAIN, fontweight="bold")
    ax.text(0.330, 0.565, "No backpropagation through Trajectron++; training uses Inner Max.", ha="left", va="center", fontsize=7.1, color=MUTED)

    # Inference workflow.
    inf_load = box(
        ax,
        (0.326, 0.335),
        (0.112, 0.063),
        "Load Fixed Θ",
        "no parameter update",
        ARTIFACT,
        ARTIFACT,
        title_size=8.1,
        body_size=6.8,
        body_width=16,
    )
    inf_runtime = box(
        ax,
        (0.326, 0.195),
        (0.160, 0.080),
        "Runtime Extraction",
        "ϕ(x), Y, normalized Aₙ, feasibility mask m",
        INFER,
        INFER,
        title_size=8.1,
        body_size=6.7,
        body_width=23,
    )
    inf_forward = box(
        ax,
        (0.485, 0.335),
        (0.130, 0.063),
        "Single Forward Pass",
        "w(x)=ΠΔ(Θ[ϕ(x);1])",
        INFER,
        INFER,
        title_size=8.1,
        body_size=6.8,
        body_width=19,
    )
    inf_score = box(ax, (0.640, 0.335), (0.105, 0.063), "Score Candidates", "sₖ=w(x)ᵀAₖ", INFER, INFER, title_size=8.1, body_size=6.8, body_width=15)
    inf_mask = box(ax, (0.770, 0.335), (0.095, 0.063), "Hard Mask", "infeasible sₖ=+∞", INFER, INFER, title_size=8.1, body_size=6.8, body_width=15)
    inf_select = box(
        ax,
        (0.790, 0.195),
        (0.135, 0.080),
        "Selected Trajectory",
        "k*=arg minₖ sₖ; if none feasible, use w_safe fallback",
        INFER,
        INFER,
        title_size=8.1,
        body_size=6.4,
        body_width=20,
    )

    arrow(ax, (0.855, 0.770), (0.382, 0.398), ARTIFACT, linestyle="--", rad=0.16)
    arrow(ax, (0.270, 0.430), (0.326, 0.236), INFER, linestyle="--", rad=-0.12)
    arrow(ax, (0.438, 0.367), (0.485, 0.367), INFER)
    arrow(ax, (0.486, 0.236), (0.485, 0.350), INFER, rad=-0.12)
    arrow(ax, (0.615, 0.367), (0.640, 0.367), INFER)
    arrow(ax, (0.486, 0.236), (0.640, 0.350), INFER, rad=0.12)
    arrow(ax, (0.745, 0.367), (0.770, 0.367), INFER)
    arrow(ax, (0.818, 0.335), (0.838, 0.275), INFER)
    arrow(ax, (0.486, 0.236), (0.790, 0.235), INFER, rad=0.05)
    ax.text(0.480, 0.305, "Dynamic w(x), not dynamic Θ", ha="left", va="center", fontsize=7.0, color=INFER, fontweight="bold")
    ax.text(0.330, 0.140, "No optimizer, no CVXPY, no Benders loop; inference uses Inner Min.", ha="left", va="center", fontsize=7.1, color=MUTED)

    return fig


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    ADAPTIVE_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    fig = draw()
    outputs = [
        ASSET_DIR / "computational_graph_academic.png",
        ASSET_DIR / "computational_graph_academic.svg",
        ADAPTIVE_ASSET_DIR / "computational_graph_academic.png",
        ADAPTIVE_ASSET_DIR / "computational_graph_academic.svg",
    ]
    for path in outputs:
        fig.savefig(path, dpi=260, bbox_inches="tight", facecolor="white")
        print(f"Wrote {path}")
    plt.close(fig)


if __name__ == "__main__":
    main()
