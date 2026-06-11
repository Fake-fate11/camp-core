from __future__ import annotations

import os
import textwrap
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[2] / ".matplotlib-cache"),
)

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "ppt_assets" / "camp_research_briefing"
ADAPTIVE_ASSET_DIR = ROOT / "ppt_assets" / "adaptive_rebuilt_elements"

CMU_BLUE = "#0055A4"
TRAIN_BLUE = "#D9EAFB"
TRAIN_BLUE_EDGE = "#2F6FAE"
INFER_GREEN = "#DFF3E8"
INFER_GREEN_EDGE = "#2E8B57"
SHARED_GRAY = "#EEF2F5"
SHARED_EDGE = "#7C8792"
ARTIFACT_GOLD = "#FFF1C6"
ARTIFACT_EDGE = "#B58700"
INK = "#1C2430"
MUTED = "#5E6A71"
RED = "#C41230"


def wrap(text: str, width: int = 28) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def rounded_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str = "",
    face: str = "white",
    edge: str = SHARED_EDGE,
    title_color: str = INK,
    body_color: str = INK,
    lw: float = 1.6,
    title_size: float = 9.5,
    body_size: float = 8.0,
    radius: float = 0.012,
    body_width: int = 30,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.012,rounding_size={radius}",
        linewidth=lw,
        edgecolor=edge,
        facecolor=face,
        zorder=2,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h - 0.018,
        title,
        ha="center",
        va="top",
        color=title_color,
        fontsize=title_size,
        fontweight="bold",
        zorder=3,
    )
    if body:
        ax.text(
            x + w / 2,
            y + h / 2 - 0.012,
            wrap(body, body_width),
            ha="center",
            va="center",
            color=body_color,
            fontsize=body_size,
            linespacing=1.22,
            zorder=3,
        )
    return patch


def arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = MUTED,
    lw: float = 1.8,
    linestyle: str = "-",
    connectionstyle: str = "arc3,rad=0",
    mutation_scale: float = 12,
):
    arr = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        linewidth=lw,
        linestyle=linestyle,
        color=color,
        connectionstyle=connectionstyle,
        shrinkA=4,
        shrinkB=4,
        zorder=4,
    )
    ax.add_patch(arr)
    return arr


def label(ax, x: float, y: float, text: str, color: str = MUTED, size: float = 8.0):
    ax.text(x, y, text, ha="center", va="center", color=color, fontsize=size, zorder=5)


def draw() -> plt.Figure:
    fig, ax = plt.subplots(figsize=(17.6, 9.9))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        0.03,
        0.965,
        "CAMP Computational Graph: training-time optimization vs inference-time selection",
        ha="left",
        va="top",
        fontsize=19,
        fontweight="bold",
        color=INK,
    )
    ax.text(
        0.03,
        0.928,
        "Blue arrows/blocks are offline training. Green arrows/blocks are deployment/inference. Gray modules are shared, frozen extraction/evaluation.",
        ha="left",
        va="top",
        fontsize=10,
        color=MUTED,
    )

    shared_panel = FancyBboxPatch(
        (0.025, 0.10),
        0.245,
        0.80,
        boxstyle="round,pad=0.014,rounding_size=0.018",
        linewidth=1.8,
        edgecolor=SHARED_EDGE,
        facecolor=SHARED_GRAY,
        zorder=0,
    )
    ax.add_patch(shared_panel)
    ax.text(
        0.047,
        0.875,
        "Shared Base Extraction",
        ha="left",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=INK,
        zorder=3,
    )
    ax.text(
        0.047,
        0.848,
        "used by cache build and by inference",
        ha="left",
        va="center",
        fontsize=8.8,
        color=MUTED,
        zorder=3,
    )

    training_panel = FancyBboxPatch(
        (0.305, 0.515),
        0.665,
        0.385,
        boxstyle="round,pad=0.014,rounding_size=0.018",
        linewidth=2.0,
        edgecolor=TRAIN_BLUE_EDGE,
        facecolor="#F6FAFF",
        zorder=0,
    )
    ax.add_patch(training_panel)
    ax.text(
        0.327,
        0.874,
        "Training Time Procedure",
        ha="left",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=TRAIN_BLUE_EDGE,
        zorder=3,
    )
    ax.text(
        0.327,
        0.848,
        "offline cache + BT warmup + CVXPY Benders; no gradients through Trajectron++",
        ha="left",
        va="center",
        fontsize=8.8,
        color=MUTED,
        zorder=3,
    )

    inference_panel = FancyBboxPatch(
        (0.305, 0.10),
        0.665,
        0.355,
        boxstyle="round,pad=0.014,rounding_size=0.018",
        linewidth=2.0,
        edgecolor=INFER_GREEN_EDGE,
        facecolor="#F7FEFA",
        zorder=0,
    )
    ax.add_patch(inference_panel)
    ax.text(
        0.327,
        0.428,
        "Inference Time Procedure",
        ha="left",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=INFER_GREEN_EDGE,
        zorder=3,
    )
    ax.text(
        0.327,
        0.402,
        "single forward pass + hard mask + inner min; no Benders loop and no CVXPY solve",
        ha="left",
        va="center",
        fontsize=8.8,
        color=MUTED,
        zorder=3,
    )

    # Shared extraction lane.
    inp = rounded_box(
        ax,
        0.055,
        0.765,
        0.185,
        0.072,
        "Inputs x",
        "HD/vector map, dynamic agents/obstacles, speed limits, agent history",
        face="white",
        edge=SHARED_EDGE,
        body_width=28,
        body_size=7.5,
    )
    traj = rounded_box(
        ax,
        0.055,
        0.628,
        0.185,
        0.094,
        "Frozen Base Predictor",
        "Trajectron++ encoder and sampler",
        face="white",
        edge=SHARED_EDGE,
        body_width=24,
    )
    phi = rounded_box(
        ax,
        0.045,
        0.488,
        0.092,
        0.082,
        "Scene Embedding",
        "phi(x) in R^64",
        face="white",
        edge=SHARED_EDGE,
        title_size=8.3,
        body_size=7.4,
        body_width=16,
    )
    cand = rounded_box(
        ax,
        0.150,
        0.488,
        0.092,
        0.082,
        "Candidate Pool",
        "Y={y_k}; K=50 in final run",
        face="white",
        edge=SHARED_EDGE,
        title_size=8.3,
        body_size=7.2,
        body_width=16,
    )
    atom = rounded_box(
        ax,
        0.055,
        0.285,
        0.185,
        0.135,
        "Atom Evaluator",
        "compute_atom_bank_vector + compute_feasibility_mask",
        face="white",
        edge=SHARED_EDGE,
        body_width=26,
    )
    atom_out = rounded_box(
        ax,
        0.055,
        0.165,
        0.185,
        0.074,
        "Per-candidate outputs",
        "A(x,y_k) in R^9 and hard feasibility mask m_k",
        face="white",
        edge=SHARED_EDGE,
        title_size=8.8,
        body_size=7.5,
        body_width=26,
    )
    arrow(ax, (0.147, 0.765), (0.147, 0.722), SHARED_EDGE)
    arrow(ax, (0.147, 0.628), (0.091, 0.570), SHARED_EDGE)
    arrow(ax, (0.147, 0.628), (0.196, 0.570), SHARED_EDGE)
    arrow(ax, (0.196, 0.488), (0.182, 0.420), SHARED_EDGE)
    arrow(ax, (0.147, 0.285), (0.147, 0.239), SHARED_EDGE)
    arrow(ax, (0.147, 0.488), (0.112, 0.420), SHARED_EDGE, connectionstyle="arc3,rad=0.25")
    label(ax, 0.222, 0.457, "candidate trajectories", SHARED_EDGE, 7.4)

    # Training lane.
    cache = rounded_box(
        ax,
        0.330,
        0.744,
        0.138,
        0.080,
        "Offline Cache",
        "store phi, Y, raw A, mask, gt_atoms",
        face=TRAIN_BLUE,
        edge=TRAIN_BLUE_EDGE,
        body_width=22,
    )
    norm = rounded_box(
        ax,
        0.505,
        0.744,
        0.130,
        0.080,
        "Normalize + Clip",
        "A / atom_scales; clip to [0,10]",
        face=TRAIN_BLUE,
        edge=TRAIN_BLUE_EDGE,
        body_width=22,
    )
    bt = rounded_box(
        ax,
        0.672,
        0.744,
        0.132,
        0.080,
        "BT Warmup",
        "Bradley-Terry preference fit",
        face=TRAIN_BLUE,
        edge=TRAIN_BLUE_EDGE,
        body_width=20,
    )
    anchor = rounded_box(
        ax,
        0.830,
        0.744,
        0.100,
        0.080,
        "Anchor w_off",
        "global prior weights",
        face=ARTIFACT_GOLD,
        edge=ARTIFACT_EDGE,
        body_width=14,
        title_size=8.5,
    )
    loop = FancyBboxPatch(
        (0.345, 0.555),
        0.405,
        0.142,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        linewidth=1.8,
        linestyle="--",
        edgecolor=TRAIN_BLUE_EDGE,
        facecolor="#EDF5FF",
        zorder=1,
    )
    ax.add_patch(loop)
    ax.text(
        0.365,
        0.678,
        "Benders Master Loop (per iteration)",
        ha="left",
        va="center",
        fontsize=10.4,
        fontweight="bold",
        color=TRAIN_BLUE_EDGE,
        zorder=3,
    )
    wbox = rounded_box(
        ax,
        0.365,
        0.585,
        0.105,
        0.065,
        "Current weights",
        "w_i=normalize_+(Theta[phi_i;1])",
        face="white",
        edge=TRAIN_BLUE_EDGE,
        title_size=7.8,
        body_size=6.8,
        body_width=15,
    )
    imax = rounded_box(
        ax,
        0.492,
        0.585,
        0.092,
        0.065,
        "Inner Max",
        "arg max_k w_i^T A_ik",
        face="white",
        edge=TRAIN_BLUE_EDGE,
        title_size=7.8,
        body_size=6.8,
        body_width=14,
    )
    cut = rounded_box(
        ax,
        0.606,
        0.585,
        0.112,
        0.065,
        "Cut Pool",
        "g_i=A_i,kmax; q_i >= value + g_i^T(w-w_anchor)",
        face="white",
        edge=TRAIN_BLUE_EDGE,
        title_size=7.8,
        body_size=6.2,
        body_width=19,
    )
    master = rounded_box(
        ax,
        0.775,
        0.555,
        0.155,
        0.142,
        "CVXPY Outer Min",
        "optimize Theta, eta, s, q under simplex constraints, CVaR alpha=0.9; output fixed Theta",
        face=TRAIN_BLUE,
        edge=TRAIN_BLUE_EDGE,
        body_width=24,
        title_size=8.8,
        body_size=7.0,
    )
    saved = rounded_box(
        ax,
        0.777,
        0.520,
        0.153,
        0.028,
        "Saved Theta checkpoint (9 x 65)",
        "",
        face=ARTIFACT_GOLD,
        edge=ARTIFACT_EDGE,
        title_size=7.2,
        body_size=6.7,
        body_width=26,
    )

    arrow(ax, (0.270, 0.525), (0.330, 0.785), TRAIN_BLUE_EDGE, linestyle="--")
    label(ax, 0.289, 0.665, "cache build", TRAIN_BLUE_EDGE, 7.5)
    arrow(ax, (0.468, 0.785), (0.505, 0.785), TRAIN_BLUE_EDGE)
    arrow(ax, (0.635, 0.785), (0.672, 0.785), TRAIN_BLUE_EDGE)
    arrow(ax, (0.804, 0.785), (0.830, 0.785), TRAIN_BLUE_EDGE)
    arrow(ax, (0.570, 0.744), (0.430, 0.697), TRAIN_BLUE_EDGE, connectionstyle="arc3,rad=-0.18")
    arrow(ax, (0.470, 0.618), (0.492, 0.618), TRAIN_BLUE_EDGE)
    arrow(ax, (0.584, 0.618), (0.606, 0.618), TRAIN_BLUE_EDGE)
    arrow(ax, (0.718, 0.618), (0.775, 0.618), TRAIN_BLUE_EDGE)
    arrow(ax, (0.830, 0.744), (0.830, 0.697), ARTIFACT_EDGE)
    arrow(ax, (0.775, 0.650), (0.470, 0.650), TRAIN_BLUE_EDGE, connectionstyle="arc3,rad=0.22")
    label(ax, 0.610, 0.675, "update Theta", TRAIN_BLUE_EDGE, 7.3)
    arrow(ax, (0.852, 0.555), (0.852, 0.548), TRAIN_BLUE_EDGE)

    # Inference lane.
    fixed_theta = rounded_box(
        ax,
        0.330,
        0.318,
        0.128,
        0.065,
        "Fixed Theta",
        "loaded Theta checkpoint; no optimizer",
        face=ARTIFACT_GOLD,
        edge=ARTIFACT_EDGE,
        title_size=8.3,
        body_size=6.8,
        body_width=24,
    )
    fwd = rounded_box(
        ax,
        0.485,
        0.318,
        0.128,
        0.065,
        "Single Forward Pass",
        "w(x)=simplex_proj(Theta[phi(x);1])",
        face=INFER_GREEN,
        edge=INFER_GREEN_EDGE,
        title_size=8.3,
        body_size=6.8,
        body_width=20,
    )
    score = rounded_box(
        ax,
        0.640,
        0.318,
        0.118,
        0.065,
        "Score Candidates",
        "s_k = w(x)^T A(x,y_k)",
        face=INFER_GREEN,
        edge=INFER_GREEN_EDGE,
        title_size=8.3,
        body_size=7.0,
        body_width=17,
    )
    mask = rounded_box(
        ax,
        0.785,
        0.318,
        0.112,
        0.065,
        "Hard Mask",
        "set infeasible scores to +inf",
        face=INFER_GREEN,
        edge=INFER_GREEN_EDGE,
        title_size=8.3,
        body_size=7.0,
        body_width=16,
    )
    out = rounded_box(
        ax,
        0.805,
        0.150,
        0.122,
        0.095,
        "Selected Trajectory",
        "k* = arg min_k s_k; fallback to w_safe if no feasible candidate",
        face="#E7F7EE",
        edge=INFER_GREEN_EDGE,
        title_size=8.3,
        body_size=6.6,
        body_width=19,
    )
    features = rounded_box(
        ax,
        0.330,
        0.178,
        0.242,
        0.074,
        "Runtime extraction",
        "current phi(x), candidate pool Y, normalized atom matrix A, feasibility mask m",
        face="white",
        edge=INFER_GREEN_EDGE,
        title_size=8.3,
        body_size=7.1,
        body_width=36,
    )

    arrow(ax, (0.270, 0.275), (0.330, 0.215), INFER_GREEN_EDGE, linestyle="--")
    label(ax, 0.290, 0.238, "live/eval features", INFER_GREEN_EDGE, 7.2)
    arrow(ax, (0.458, 0.350), (0.485, 0.350), INFER_GREEN_EDGE)
    arrow(ax, (0.572, 0.252), (0.640, 0.332), INFER_GREEN_EDGE, connectionstyle="arc3,rad=0.12")
    arrow(ax, (0.613, 0.350), (0.640, 0.350), INFER_GREEN_EDGE)
    arrow(ax, (0.758, 0.350), (0.785, 0.350), INFER_GREEN_EDGE)
    arrow(ax, (0.841, 0.318), (0.805, 0.205), INFER_GREEN_EDGE)
    arrow(ax, (0.572, 0.215), (0.805, 0.206), INFER_GREEN_EDGE, connectionstyle="arc3,rad=0.06")
    label(ax, 0.720, 0.230, "A and m", INFER_GREEN_EDGE, 7.2)

    return fig


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    ADAPTIVE_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    fig = draw()
    for out_dir in (ASSET_DIR, ADAPTIVE_ASSET_DIR):
        fig.savefig(out_dir / "computational_graph.png", dpi=240, bbox_inches="tight", facecolor="white")
        fig.savefig(out_dir / "computational_graph.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {ASSET_DIR / 'computational_graph.png'}")
    print(f"Wrote {ASSET_DIR / 'computational_graph.svg'}")
    print(f"Wrote {ADAPTIVE_ASSET_DIR / 'computational_graph.png'}")
    print(f"Wrote {ADAPTIVE_ASSET_DIR / 'computational_graph.svg'}")


if __name__ == "__main__":
    main()
