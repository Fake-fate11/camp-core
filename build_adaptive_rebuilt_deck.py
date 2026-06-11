from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from build_camp_research_briefing import postprocess_pptx


ROOT = Path(__file__).resolve().parent
SRC_ASSETS = ROOT / "ppt_assets" / "adaptive_source_elements"
CAMP_ASSETS = ROOT / "ppt_assets" / "camp_research_briefing"
OUT_ASSETS = ROOT / "ppt_assets" / "adaptive_rebuilt_elements"
MD_OUT = ROOT / "Adaptive_Risk-Aware_Motion_Prediction_rebuilt.md"
RAW_PPTX = ROOT / "_adaptive_rebuilt_raw.pptx"
PPTX_OUT = ROOT / "Adaptive_Risk-Aware_Motion_Prediction_rebuilt.pptx"


def prepare_assets() -> dict[str, str]:
    OUT_ASSETS.mkdir(parents=True, exist_ok=True)
    asset_map: dict[str, Path] = {}
    for name in [
        "main_k50_table.png",
        "violation_bar.png",
        "feasibility_floor.png",
        "candidate_ablation_table.png",
        "qual_curve.png",
        "qual_camp_improves_top1.png",
        "qual_no_feasible_floor.png",
        "training_time_table.png",
        "metric_audit.png",
        "computational_graph.png",
    ]:
        src = CAMP_ASSETS / name
        if src.exists():
            dst = OUT_ASSETS / name
            shutil.copyfile(src, dst)
            asset_map[name] = dst

    for src in sorted(SRC_ASSETS.glob("slide_*.png")):
        dst = OUT_ASSETS / f"source_{src.name}"
        shutil.copyfile(src, dst)
        asset_map[dst.name] = dst

    return {k: v.as_posix() for k, v in asset_map.items()}


def write_manifest(assets: dict[str, str]) -> None:
    manifest = {
        "source": "Adaptive_Risk-Aware_Motion_Prediction.pptx",
        "source_observation": "The source deck contains 15 slides, each represented as one full-slide PNG and no editable text/table/shape elements.",
        "rebuilt_output": PPTX_OUT.name,
        "principle": "Text and tables were rebuilt as editable PowerPoint content where practical; charts and qualitative cases were inserted as separate PNG elements.",
        "slides": [
            {"slide": 1, "title": "Title", "elements": ["editable title/subtitle/footer text"]},
            {"slide": 2, "title": "Executive Snapshot", "elements": ["editable KPI table", "editable central finding text"]},
            {"slide": 3, "title": "Workflow Architecture", "elements": ["computational_graph.png", "editable phase distinction note"]},
            {"slide": 4, "title": "Methodological Baselines", "elements": ["editable comparison table"]},
            {"slide": 5, "title": "Main K=50 Results", "elements": ["main_k50_table.png", "editable insight text"]},
            {"slide": 6, "title": "Safety Frequency", "elements": ["violation_bar.png", "editable sidebar text"]},
            {"slide": 7, "title": "Feasibility Floor", "elements": ["feasibility_floor.png", "editable bottleneck bullets"]},
            {"slide": 8, "title": "Candidate Pool Effects", "elements": ["candidate_ablation_table.png", "editable key takeaways"]},
            {"slide": 9, "title": "Qualitative Evidence I", "elements": ["qual_curve.png", "editable scenario analysis"]},
            {"slide": 10, "title": "Qualitative Evidence II", "elements": ["qual_camp_improves_top1.png", "editable scenario analysis"]},
            {"slide": 11, "title": "Qualitative Evidence III", "elements": ["qual_no_feasible_floor.png", "editable scenario analysis"]},
            {"slide": 12, "title": "Cost-Benefit Analysis", "elements": ["training_time_table.png", "editable summary table"]},
            {"slide": 13, "title": "Metric Integrity Audit", "elements": ["metric_audit.png", "editable correction bullets"]},
            {"slide": 14, "title": "Synthesis", "elements": ["editable insight boxes"]},
            {"slide": 15, "title": "Next-Stage Collaboration", "elements": ["editable roadmap table"]},
        ],
        "assets": assets,
    }
    (OUT_ASSETS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def p(name: str) -> str:
    return (OUT_ASSETS / name).as_posix()


def write_markdown() -> None:
    md = f"""# Adaptive Predictive Optimization for Risk-Aware Decision Making

Corrective Adaptation for Motion Prediction (CAMP): Map-Aware Clearance Results and Deployment Path

Carnegie Mellon University Research Collaboration | Prepared for partner technical leadership

::: notes
This rebuilt deck decomposes the original raster-only source deck into editable text/table elements plus separate PNG chart and qualitative figure elements.
:::

# Executive Snapshot: From Model Accuracy to Decision Quality

| Metric | Value | Meaning |
| :--- | :---: | :--- |
| Violation Rate Floor | 60.2% | Lowest hard-safety failure achievable by CAMP-Select under the current candidate pool. |
| Training Time | 10.36 h | CAMP optimization is 2.22x faster to train than pure safety finetuning. |
| Train / Eval Scenarios | 245k / 66k | Massive-scale testing with dynamic-neighbor map-aware clearance enabled. |
| Candidate Pool | K=50 | Expanding from K=12 to K=50 significantly shifts the safety frontier. |
| Central Finding | Hybrid adaptation | Finetune + CAMP provides the accuracy-safety compromise without the extreme compute costs of pure adaptation. |

::: notes
The KPI cards from the original slide are rebuilt as an editable table plus an editable central finding text block.
:::

# End-to-End Computational Graph Architecture

![CAMP computational graph]({p('computational_graph.png')}){{width=96%}}

Training time is the blue offline optimization path: cached Trajectron++ embeddings, atom vectors, Bradley-Terry warmup, and CVXPY Benders updates to the linear map. Inference time is the green one-shot path: load fixed `Theta`, compute scene weights, hard-mask infeasible candidates, and select by inner-min weighted atom cost.

::: notes
This replaces the earlier layer table with an implementation-grounded computational graph that explicitly separates training-time optimization from inference-time selection.
:::

# Methodological Baselines: Three Paths to Safety Adaptation

| CAMP-Select | Finetune Safe | Finetune + CAMP Hybrid |
| :--- | :--- | :--- |
| Approach: post-hoc selector over a fixed candidate pool. | Approach: adapts the base predictor directly. | Approach: finetunes the predictor, then applies the post-hoc CAMP selector. |
| Mechanism: selects the candidate with the lowest weighted atom cost via scene embedding. | Mechanism: optimizes joint Negative Log-Likelihood and safety Conditional Value-at-Risk objective. | Mechanism: uses base encoder embedding to evaluate stronger candidates generated by finetuning. |
| Trade-off: computationally cheap; dominated by candidate quality. | Trade-off: superior pointwise accuracy and comfort, but can permit higher violation rates. | Trade-off: optimal empirical compromise balancing high trajectory accuracy with robust safety constraints. |

::: notes
The original three-column method comparison is rebuilt as an editable table.
:::

# Main K=50 Map-Aware Clearance Quantitative Results

![Main K=50 result table]({p('main_k50_table.png')}){{width=96%}}

**Core insight:** Finetune Safe dominates pointwise accuracy, while CAMP-Select forces the absolute lowest achievable violation rate under the current candidate pool.

::: notes
The dense table is inserted as a separate PNG element for readability. It was generated from the LaTeX summary values.
:::

# Safety Frequency Optimization and Hard Constraint Adherence

![Violation-rate chart]({p('violation_bar.png')}){{width=72%}}

- Baseline reality: Pred Top1 fails hard constraints in 82.0% of evaluated map-aware scenarios.
- Selection effect: CAMP-Select drops violation to 60.2%.
- Finetuning gap: Finetune Safe improves accuracy and comfort, but remains higher in violation than selection policies.

::: notes
The chart is a separate PNG element; the explanatory sidebar is rebuilt as editable table text.
:::

# System Diagnostics: Hitting the 60.2% Feasibility Floor

![Feasibility floor]({p('feasibility_floor.png')}){{width=48%}}

- Data reality: out of 66,843 eval scenarios, 60.2% contain zero feasible candidates in the K=50 pool.
- Mathematical implication: CAMP-Select is hitting the candidate-pool floor.
- Engineering takeaway: downstream selection cannot overcome missing feasible candidates.

::: notes
The source slide paired a donut chart with a bottleneck box. This rebuild keeps the chart as PNG and the analysis as editable text.
:::

# Candidate Pool Effects: Expanding from K=12 to K=50

![Candidate-pool ablation table]({p('candidate_ablation_table.png')}){{width=96%}}

- Quality shift validation: Oracle MinADE improves from 1.43 to 1.06.
- Safety scaling: expanding the pool yields a 4.5 percentage-point violation reduction for selection models.
- Remaining limit: downstream selection is still constrained by upstream candidate coverage.

::: notes
The table is a separate PNG element; the two takeaway boxes are rebuilt as editable table cells.
:::

# Qualitative Evidence I: Navigating Complex Curve Geometries

![Curve qualitative case]({p('qual_curve.png')}){{width=72%}}

- Environment context: high-curvature road dynamics constrain neighboring agents.
- Methodological separation: baseline predictions and optimized selections diverge visibly.
- CAMP advantage: selected trajectories maintain map-aware clearance margins.

::: notes
The qualitative figure is a separate PNG; scenario analysis is editable text.
:::

# Qualitative Evidence II: Correcting Unadapted Base Failures

![CAMP improves top-1 case]({p('qual_camp_improves_top1.png')}){{width=52%}}

- Baseline failure: Pred Top1 defaults to a trajectory with severe safety costs.
- Corrective override: CAMP evaluates the full K=50 pool and retrieves an alternative candidate.
- Business value: visual evidence of tail-risk mitigation in an operational scene.

::: notes
The original slide used this case to explain CAMP correcting a high-safety-cost top-1 behavior.
:::

# Qualitative Evidence III: Visualizing the Feasibility Floor

![No-feasible-floor case]({p('qual_no_feasible_floor.png')}){{width=72%}}

- Reality of the floor: visualization of why violation rates stall at 60.2%.
- Constraint collision: every available candidate violates the hard feasibility mask.
- Engineering next step: improve upstream generative diversity.

::: notes
The no-feasible case is kept as a PNG; the explanatory bullets are editable.
:::

# Cost-Benefit Analysis: Training Efficiency and Compute Scaling

![Training-time comparison]({p('training_time_table.png')}){{width=86%}}

- High efficiency: CAMP training requires 10.36 h under K=50.
- Compute savings: full-model safety finetuning requires 22.99 h.
- Scalability profile: post-hoc selection scales without full retraining.

::: notes
The cost-benefit table is rebuilt as PNG plus editable operational summary.
:::

# Metric Integrity Audit: Aligning the Conditional Value-at-Risk Objective

![Metric audit]({p('metric_audit.png')}){{width=70%}}

- Diagnostic artifact: intermediate evaluations reported an unclipped sum near 1400.
- Final alignment: the paper metric reports weighted and clipped Safety Conditional Value-at-Risk.
- Why it matters: reporting now matches the training objective.

::: notes
The chart is a separate PNG; the correction narrative is editable.
:::

# Synthesis: Final Actionable Insights and Operational Trade-Offs

| Insight | Interpretation |
| :--- | :--- |
| Insight 1: The upstream bottleneck | Candidate coverage is the true mathematical ceiling. Increasing pool size improves safety, but downstream optimization remains constrained by generative limits. |
| Insight 2: The extremes of adaptation | CAMP-Select remains the strongest absolute method for minimizing safety-frequency violations. Finetune Safe achieves the best pointwise accuracy and ride comfort, but permits higher hard-violation rates. |
| Insight 3: The hybrid recommendation | Finetune + CAMP serves as the optimal engineering compromise, blending predictive accuracy from deep finetuning with hard-safety guarantees from post-hoc selection. |

::: notes
This reconstructs the three large insight boxes from the source slide as editable table content.
:::

# Next-Stage Collaboration: Industry Deployment Roadmap

| Stage | Duration | Objective |
| :--- | :---: | :--- |
| 01 Technical Alignment | 2 weeks | Define exact operational design domains, parameters, data access protocols, constraint definitions, and pilot success thresholds. |
| 02 Pilot Integration | 4-6 weeks | Connect the Finetune + CAMP architecture directly to the partner internal decision layer and evaluate against proprietary cache scenarios. |
| 03 Risk Review | 2 weeks | Conduct joint deep-dive audits isolating failure cases, model sensitivity analyses, predictive reliability, and fallback control mechanisms. |
| 04 Scale Decision Gate | 1 week | Executive review of pilot key performance indicators to determine full fleet deployment versus targeted research extension. |

::: notes
The source roadmap is rebuilt as an editable table.
:::
"""
    MD_OUT.write_text(md, encoding="utf-8")


def build() -> None:
    subprocess.run(
        ["pandoc", str(MD_OUT), "--slide-level=1", "-o", str(RAW_PPTX)],
        check=True,
        cwd=ROOT,
    )
    postprocess_pptx(RAW_PPTX, PPTX_OUT)


def main() -> None:
    assets = prepare_assets()
    write_manifest(assets)
    write_markdown()
    build()
    print(PPTX_OUT)
    print(OUT_ASSETS / "manifest.json")


if __name__ == "__main__":
    main()
