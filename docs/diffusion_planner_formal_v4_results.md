# CAMP + Diffusion Planner Formal V4 Results

This document records the first strictly paired four-way closed-loop benchmark
for the CAMP integration with TIER IV Diffusion Planner.

## Provenance

- CAMP commit used for the run: `d1031de`
- Statistics/archive code: `336a9ae`
- Diffusion Planner commit:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- DP checkpoint: official v5.0 `diffusion_planner.pth`
- Remote result root:
  `/root/autodl-tmp/camp_dp_formal_v4_d1031de`
- Versioned full report:
  `results/diffusion_planner/benchmark_comparison_bootstrap_v4.json`
- Full report SHA-256:
  `959a3f79bc5d3481fc5ffaf1e56f948dddb2e1feb954b2bdcf28056f3af59e91`

The report uses deterministic percentile bootstrap confidence intervals with
10,000 resamples.

## Matched Matrix

Each selector was evaluated on the same 36 scenario keys:

- selectors: original DP Top-1, Uniform CAMP, Static CAMP, and
  scene-conditioned Theta;
- routes: `sample59_86`, `sample2_104`, and `nishishinjuku`;
- unseen seeds: 11, 12, and 13;
- NPC caps: 0 and 4;
- traffic lights: on and off;
- 200 closed-loop steps per run;
- eight DP candidates for each CAMP selector.

This produced 144 successful runs. The pairing audit found 36 runs per
selector, 36 common keys, no missing keys, no duplicate keys, and
`strictly_paired=true`.

## Aggregate Results

| Selector | Route completion | OBB collision | Near miss | Lane violation | Realized red light | Planned red light | Mean jerk | Fallback | Feasible candidates | p95 selection latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DP Top-1 | 0.2808 | 0 | 0.0051 | 0.0501 | 0.0734 | 0.0813 | 3.1901 | n/a | n/a | n/a |
| Uniform CAMP | 0.2965 | 0 | 0.0068 | 0.0450 | 0.0787 | 0.1053 | 4.1350 | 0.1856 | 0.7751 | 107.84 ms |
| Static CAMP | 0.2869 | 0 | 0.0119 | 0.0467 | 0.0787 | 0.0986 | 4.6013 | 0.1731 | 0.7826 | 106.65 ms |
| Theta CAMP | 0.2908 | 0 | 0.0082 | 0.0449 | 0.0787 | 0.1006 | 4.9320 | 0.1756 | 0.7757 | 108.32 ms |

## Paired Findings

The following changes are selector minus original DP Top-1. A result is called
significant here only when its paired bootstrap 95% interval excludes zero.

| Selector | Route completion delta | Near-miss delta | Planned-red delta | Mean-jerk delta | Mean lateral-acceleration delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Uniform CAMP | +0.0158 `[+0.0079, +0.0254]` | +0.0017 `[-0.0008, +0.0054]` | +0.0240 `[+0.0017, +0.0558]` | +0.9449 `[+0.3424, +1.4342]` | +0.0440 `[+0.0209, +0.0688]` |
| Static CAMP | +0.0062 `[-0.0037, +0.0168]` | +0.0068 `[+0.0004, +0.0147]` | +0.0174 `[-0.0007, +0.0478]` | +1.4112 `[+0.9068, +1.8563]` | +0.0345 `[+0.0213, +0.0526]` |
| Theta CAMP | +0.0100 `[+0.0022, +0.0194]` | +0.0031 `[+0.0004, +0.0068]` | +0.0193 `[+0.0021, +0.0410]` | +1.7419 `[+1.0586, +2.4268]` | +0.0470 `[+0.0189, +0.0723]` |

Uniform and Theta significantly improve route completion over Top-1 in this
matrix. Those gains are not broad quality improvements: both worsen planned
red-light rate and comfort, and Theta also has a significantly higher
near-miss rate. Static does not significantly improve route completion and
worsens near misses and comfort.

Theta minus Static has route-completion delta
`+0.0038 [-0.0001, +0.0082]`; all selected aggregate Theta-versus-Static
intervals cross zero. Scene conditioning therefore does not show a reliable
overall advantage in this matrix. On `sample2_104` alone, Theta improves route
completion by `+0.0092 [+0.0080, +0.0106]` and reduces mean jerk by
`-0.2218 [-0.2945, -0.1486]`, but that route-specific result does not
generalize to the other two routes.

All selectors had zero OBB collisions, so this benchmark cannot support a
collision-reduction claim.

## Interpretation And Next Target

The integration and evaluation protocol are now validated: DP produces eight
candidates, CAMP filters and ranks them, the chosen trajectory drives the
perfect-tracking simulator, and all four methods are compared on identical
scenario keys.

The current Static and Theta targets are preferences derived from DP's
candidate reward decomposition after safety and progress gating. They are
stronger than the earlier hand-written proxy labels, but they are still
model-based candidate labels rather than counterfactual closed-loop outcomes
or human preferences. This is the principal modeling limitation.

The next experiment should:

1. generate short-horizon counterfactual closed-loop outcomes for each
   candidate from the same saved simulator state;
2. build preference labels from realized collision, near miss, lane/red-light
   violations, progress, and comfort;
3. retrain Static and scene-conditioned Theta on those labels with
   scenario-level train/validation separation;
4. rerun the same 144-run matrix and report paired bootstrap intervals;
5. reduce selection latency below the simulator's 100 ms tick budget.
