# Diffusion Planner Robust CAMP V7 Results

## Scope

V7 replaces the v5/v6 supervised candidate-oracle imitation objective with
outcome-margin cutting planes and a simplex-constrained CVaR master. It keeps:

- the same 36 v5 closed-loop outcome logs;
- the v6 red/comfort outcome weights;
- Diffusion Planner commit `7a1d33da277a1992ec474b5383a0c963c72e04e4`;
- the unchanged selector, checkpoint, routes, candidate generator, and
  benchmark configuration.

The CAMP implementation commit is `dceeefda987c4bc333fa14dc3ad8fed894e8f2d0`.
The AutoDL solve used CVXPY 1.6.7 with NumPy 1.26.4 and CLARABEL; this kept
the established Diffusion Planner environment on NumPy 1.x.

## Training

Both masters used CVaR alpha 0.9, margin scale 0.1, margin clip 2.0, and L2
regularization `1e-4`. Of 7,200 logged records, 5,844 contained at least one
finite candidate accepted by both feasibility sources. Both cutting-plane
solves converged in four iterations.

| Model | Split | Oracle match | Mean violation | CVaR violation |
| --- | --- | ---: | ---: | ---: |
| Static | train | 84.55% | 0.01218 | 0.05925 |
| Theta | train | 86.95% | 0.01061 | 0.05273 |
| Theta | validation | 89.31% | 0.00674 | 0.03128 |

The saved Static and Theta weights are nonnegative and sum to one. The Theta
checkpoint loads through the existing `CAMPSelector` with
`linear_activation=project_simplex`.

## Formal Matrix

The unchanged formal matrix completed 144/144 runs:

- 3 routes;
- unseen seeds 11, 12, and 13;
- NPC caps 0 and 4;
- traffic lights on and off;
- Top-1, Uniform, Static, and Theta;
- 200 simulator steps and 8 candidates.

The pairing audit reports 36 runs per variant, no missing or duplicate keys,
and `strictly_paired=true`. Confidence intervals use deterministic 10,000
resample percentile bootstrap.

| Variant | Route completion | Planned red light | Mean jerk | Mean lateral acceleration |
| --- | ---: | ---: | ---: | ---: |
| DP Top-1 | 0.28076 | 0.08125 | 3.19008 | 0.30045 |
| Uniform | 0.29521 | 0.10486 | 4.19376 | 0.34540 |
| Robust Static | 0.30042 | 0.10639 | 3.93520 | 0.35089 |
| Robust Theta | 0.29726 | 0.11111 | 4.23938 | 0.34706 |

### Paired deltas

| Comparison | Route completion | Planned red light | Mean jerk | Mean lateral acceleration |
| --- | ---: | ---: | ---: | ---: |
| Static - Top-1 | +0.01965 [0.01187, 0.02940] | +0.02514 [0.00264, 0.05806] | +0.74512 [0.10499, 1.28425] | +0.05044 [0.02689, 0.07649] |
| Static - Uniform | +0.00521 [0.00349, 0.00698] | +0.00153 [-0.00056, 0.00444] | -0.25856 [-0.39963, -0.12267] | +0.00550 [-0.00050, 0.01244] |
| Theta - Static | -0.00316 [-0.00871, 0.00025] | +0.00472 [-0.00153, 0.01583] | +0.30418 [0.00802, 0.68516] | -0.00384 [-0.01881, 0.00584] |

### Cross-version paired deltas

Each row below uses the same 36 route/seed/NPC/traffic-light keys.

| Comparison | Route completion | Planned red light | Mean jerk | Mean lateral acceleration |
| --- | ---: | ---: | ---: | ---: |
| v7 Static - v6 Static | -0.00265 [-0.01051, 0.00236] | -0.01819 [-0.04542, -0.00236] | -0.22217 [-0.46787, -0.01504] | +0.00145 [-0.01004, 0.01732] |
| v7 Theta - v6 Theta | -0.00532 [-0.01432, 0.00048] | -0.01097 [-0.02723, -0.00097] | +0.09022 [-0.20058, 0.45188] | +0.00087 [-0.00470, 0.00544] |

## Interpretation

Robust Static is the useful v7 result. Relative to v6 Static, it significantly
reduces planned red-light violations and mean jerk without a significant
route-completion loss. Relative to Uniform in the same v7 matrix, it improves
route completion and jerk while its red-light and lateral-acceleration
differences are not significant.

The result still does not satisfy the full target. Static remains
significantly worse than DP Top-1 on planned red-light, jerk, and lateral
acceleration. Theta has no verified benefit over Static and has significantly
worse mean jerk. Its online weights are not numerically saturated, so this is
not a checkpoint-loading or simplex-projection failure.

V7 therefore supports a narrower claim: robust outcome-margin optimization
improves the Static CAMP tradeoff over v5/v6 supervised imitation, but does
not yet make CAMP uniformly better than DP Top-1, and the current
scene-conditioned Theta formulation is not validated by closed-loop results.

## Artifacts

The local archive is under
`results/diffusion_planner/v7_robust_dceeefd/`. It contains the two trained
selectors, normalization files, training summaries, the full 144-run
comparison, and the cross-version paired bootstrap report.
