# Diffusion Planner CAMP V8 Iteration Audit

## Decision

The historical certified development configuration is:

- Diffusion Planner commit
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`;
- CAMP commit `753553722c5bb27afb66fe088c0cb8de6dad8b0b`;
- the original certified Robust Static v8 checkpoint;
- the `uniform` policy for the all-infeasible fallback branch;
- exact OBB collision checks with the certified broad phase and vectorized
  lane/clearance atom implementation.

The formal seeds 11, 12, and 13 remain unused. V8 is mathematically certified
for its collected finite-candidate dataset, but it is not a deployable
checkpoint for the requested perfect-tracking simulator. A June 13, 2026
configuration audit found that the benchmark matrix inherited the upstream
`SpawnConfig` default `advance_mode="mpc"` instead of forcing `perfect`.

The current decision is therefore:

- retain the old v8 artifacts only as an MPC-distribution development result;
- require explicit `advance_mode="perfect"` in every new collection,
  validation, and formal run;
- use the newly collected perfect-tracking v8 artifacts for the next
  development matrix;
- keep formal seeds untouched until the perfect-tracking design is frozen.

The benchmark runner now defaults to `perfect`, each replay records the mode,
pairing keys include the mode, and dataset audit can fail closed unless the
expected mode is present.

AutoDL verification passes 67 Diffusion Planner integration tests. The old
36-run dataset is rejected by `--expected_advance_mode perfect` because its
summaries contain no certified mode. A 5-step gate smoke at

```text
/root/autodl-tmp/camp_dp_perfect_mode_gate_smoke_20260613
```

prints `Advance mode: perfect` and records
`advance_mode=perfect` in both the summary and strict-pairing key.

As of CAMP commit `6225a378c7b3f96a381347580dbd7481c5dc9f34`, the 36-run
perfect-tracking Uniform collection, dataset audit, Robust Static training,
full-epigraph consistency audit, and all-infeasible fallback counterfactual are
complete on AutoDL.

## Dataset Gate

The historical Uniform v8 collection is:

```text
/root/autodl-tmp/camp_dp_v8_outcome_collect_uniform_5853d8c
```

The persisted audit passed all declared checks:

| Item | Evidence |
| --- | ---: |
| Complete scenarios | 36/36 |
| Planning records | 7,200 |
| Candidates | 57,600 |
| Candidate shape | 8 candidates x 12 atoms |
| Schema | `dp_camp_v8_12d` |
| All-infeasible records | 1,171 |
| Finite, nonnegative atoms | passed |
| Complete candidate outcomes | passed |
| Red atom equals online DP reward source | passed |
| Outcome labels excluded from online atoms | passed |

All normalization scales were fitted on training groups only. The normal
feasible-ranking dataset contains 5,854 records split into 27 training groups
and 7 validation groups.

These checks establish schema and data integrity, but the old summaries do not
record `advance_mode` and point directly to upstream `replay_default.json`,
whose default is MPC. They do not establish perfect-tracking provenance.

The perfect-tracking replacement collection is:

```text
/root/autodl-tmp/camp_dp_v8_outcome_collect_uniform_perfect_6225a37
```

The persisted audit is:

```text
/root/autodl-tmp/camp_dp_v8_outcome_collect_uniform_perfect_6225a37/camp_dataset_audit.json
```

Its SHA-256 is
`59f61fd3d8ba9491ad3ab333fab8d1aa8251bd704497d23c5fab2e7d1c037a84`.

| Item | Evidence |
| --- | ---: |
| Complete scenarios | 36/36 |
| Routes | 12 each for `sample59_86`, `sample2_104`, `nishishinjuku` |
| Planning records | 7,200 |
| Candidates | 57,600 |
| Candidate shape | 8 candidates x 12 atoms |
| Schema | `dp_camp_v8_12d` |
| All-infeasible records | 1,154 |
| `advance_mode` | `perfect`, verified in every completed run |
| Finite, nonnegative atoms | passed |
| Complete candidate outcomes | passed |
| Red atom equals online DP reward source | passed |

This is now the only v8 training dataset with certified perfect-tracking
provenance.

## Mathematical Certificate

The trained problem is finite-candidate exact constraint generation, or a
Benders-style cutting-plane method. It is not described as classical Benders
because there is no lower-level dual or strong-duality construction.

For fixed candidate atoms \(a_{ij}\), the score \(a_{ij}^{T}w\) is affine in
the simplex-constrained master variable. Every generated cut is one affine
member of the finite maximum defining the robust margin loss. CVaR epigraph
constraints and L2 regularization preserve convexity.

The normal v8 solve used CVaR alpha 0.9, margin scale 0.1, margin clip 2.0,
L2 `1e-4`, CLARABEL, and tolerance `1e-6`. It terminated with solver status
`optimal`, `converged=true`, and `final_master_gap=0`. The maximum simplex
error was `2.22e-16`.

Validation results were:

| Metric | Value |
| --- | ---: |
| Records | 1,217 |
| Oracle match | 0.871816 |
| Mean robust-margin violation | 0.012026 |
| CVaR violation | 0.062592 |
| Maximum violation | 1.509794 |

The learned weights concentrate on `jerk_early` (0.662202),
`progress_shortfall` (0.226413), `jerk_full` (0.063314), and
`rms_acceleration` (0.044749). The red-light and lateral-acceleration weights
are numerically zero.

The perfect-tracking Robust Static v8 solve is stored at:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v8_perfect_6225a37
```

It used the same convex objective and training contract: CVaR alpha 0.9,
margin scale 0.1, margin clip 2.0, L2 `1e-4`, CLARABEL, train-only
normalization, and tolerance `1e-6`. It terminated with solver status
`optimal`, `converged=true`, and `final_master_gap=0`.

Perfect-tracking training details:

| Metric | Value |
| --- | ---: |
| Input records | 7,200 |
| Feasible-ranking records | 6,026 |
| Dropped all-infeasible records | 1,174 |
| Train groups | 29 |
| Validation groups | 7 |
| Train oracle match | 0.844344 |
| Train CVaR violation | 0.062039 |
| Validation oracle match | 0.866315 |
| Validation CVaR violation | 0.035350 |
| Maximum simplex error | 0 |

The learned perfect-tracking weights are approximately
`[0.601314, 0, 0.017215, 0.164067, 0, 0, 0, 0, 0, 0.217404, 0, 0]`.

The full-epigraph consistency audit is:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v8_perfect_6225a37/full_epigraph_consistency.json
```

It solves the complete train-set epigraph master with all feasible candidate
cuts. The full objective and cutting-plane final objective differ by
`2.11e-10`; the static weights differ by L-infinity `1.94e-08`. This is direct
dataset-level evidence that the saved checkpoint matches the complete convex
finite-candidate master.

## Red-Light Identifiability

The zero red-light weight is a candidate-support issue, not evidence that the
red-light objective is unimportant:

- 6,029 records have at least one feasible candidate;
- `planned_red_light_cost` is zero for all 46,707 feasible candidates;
- no feasible record has red-light atom variation among feasible candidates;
- no feasible record has candidate-level realized red-light outcome variation
  among feasible candidates.

The DP red-light hard gate therefore removes every red-violating candidate
before CAMP scores the normal branch. This hard safety gate must remain in
place. Relaxing it to manufacture a learnable red-light signal would violate
the integration contract.

On the 12-run seed-1 development matrix, v7 and v8 both have zero planned and
realized red-light violations. The paired v8-minus-v7 deltas are:

| Metric | Mean delta | 95% bootstrap CI |
| --- | ---: | ---: |
| Route completion | +0.000239 | [-0.000100, +0.000778] |
| Mean jerk | -0.018282 | [-0.044013, +0.012438] |
| Mean lateral acceleration | -0.000041 | [-0.001736, +0.001998] |
| Fallback rate | +0.001667 | [-0.001667, +0.005417] |
| Planned red-light violation | 0 | [0, 0] |

This matrix does not establish a v8 performance gain over v7.

## Fallback Ablation

The dedicated all-infeasible master is mathematically certified:

- 1,171 fallback records;
- 22 training groups and 5 validation groups;
- `final_master_gap=2.38e-13`;
- nonnegative simplex weights with error at most `2.22e-16`.

The paired short-horizon counterfactual nevertheless rejects learned fallback
deployment. Relative to Uniform, learned fallback improves outcome value by
0.069161 and oracle match from 0.435525 to 0.704526, but worsens collision,
near-miss, lane violation, jerk, and lateral acceleration. Red-light outcome
is unchanged. Only 1 of 1,171 all-infeasible records has candidate-level
red-light outcome variation.

A separate lateral-acceleration weight floor of 0.2 also worsened the fallback
training/validation tradeoff. Uniform therefore remains the frozen fallback
policy.

On the perfect-tracking collection, a separate all-infeasible fallback master
was trained at:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_fallback_v8_perfect_6225a37
```

It is mathematically certified (`optimal`, `converged=true`,
`final_master_gap=0`) on 1,154 all-infeasible records with a 23/6 grouped
split. The paired counterfactual still rejects learned fallback deployment:
learned fallback improves oracle match from 0.516464 to 0.766031 and mean
outcome value by only `+0.004758`, but worsens collision by `+0.000867`,
near-miss by `+0.006066`, and lateral acceleration by `+0.003083`. Red-light
outcome is unchanged. Uniform remains the accepted fallback for perfect
development runs.

## Rejected Single-Variable Iterations

The following certified solves were not promoted:

- normal v8 lateral-acceleration weight floor 0.15: worse validation
  robust-margin metrics;
- lateral outcome weight 10: worse seed-1 route completion, lane violation,
  jerk, lateral acceleration, and p95 latency;
- lateral outcome weight 30: large degradation in validation oracle match and
  robust-margin risk;
- learned fallback and learned fallback with a 0.2 lateral weight floor:
  worse safety/comfort tradeoffs.

These are valid negative results. Their checkpoints must not replace the
frozen v8 artifacts.

### Shadow red stopping-margin atom

A continuous shadow diagnostic was implemented without changing the 12D
selector or its decisions. For distance \(d_t\) to the nearest aligned red
route point ahead of a candidate, it uses the comfortable stopping envelope

\[
v_{\mathrm{safe}}(d_t) =
\sqrt{2a_{\mathrm{comfort}}\max(d_t-d_{\mathrm{buffer}},0)}
\]

and integrates the proximity-weighted squared positive speed excess. It is
finite, deterministic, nonnegative, uses only current-tick online inputs, and
would remain constant with respect to master weights.

It is not admitted as an atom. A 12-run seed-1 MPC shadow matrix contains
19,200 candidates, but only four have nonzero cost. All 14,197 feasible
candidates have zero cost, so no feasible record has candidate variation.
The definition therefore fails the coverage gate on the historical matrix.
The diagnostic remains selection-neutral while perfect-tracking coverage is
measured.

The shadow report is under:

```text
/root/autodl-tmp/camp_dp_shadow_red_margin_matrix_seed1_20260613
```

On the perfect-tracking Uniform collection, the shadow diagnostic has more
coverage but is still not admitted automatically:

- 7,200 records and 57,600 candidates audited;
- 46,674 feasible candidates;
- 862 feasible candidates have nonzero shadow stopping-margin cost;
- 228 feasible records have candidate variation;
- mean shadow latency is `0.247 ms`, p95 is `1.281 ms`.

The persisted perfect coverage report is:

```text
/root/autodl-tmp/camp_dp_v8_outcome_collect_uniform_perfect_6225a37/atom_coverage_report.json
```

Its SHA-256 is
`7e14b0422941967c26772c191adcaa35eeaea72a76be00967fa6ab6aafb37c34`.
The diagnostic now has enough support to justify a future single-variable
atom experiment, but it was not part of the certified 12D v8 checkpoint or the
development matrix below.

## Perfect Development Matrix

The perfect-tracking development matrix is:

```text
/root/autodl-tmp/camp_dp_development_perfect_v8_a68dc48
/root/autodl-tmp/camp_dp_development_perfect_v7_a68dc48
```

It covers the three development routes, seeds 1/2/3, NPC counts 0/4, traffic
lights on/off, K=8, 200 steps, and `advance_mode=perfect`. The strict paired
comparison includes 36 matched run keys for each of:

- Top-1 DP;
- Uniform CAMP;
- v7 Static;
- perfect v8 Static.

The combined comparison is:

```text
/root/autodl-tmp/camp_dp_development_perfect_v8_a68dc48/benchmark_comparison_with_v7.json
```

Its SHA-256 is
`380d71ad817783e6c0de1b660872c8710b623a11abc85dead451093451b3d030`.
Pairing is strict: no missing or duplicate run keys, and all runs record
`advance_mode=perfect`.

Aggregate development metrics:

| Variant | Completion | Planned red | Realized red | Jerk | Lateral acc. | Fallback | p95 selector |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-1 | 0.287765 | 0.011944 | 0.000279 | 8.362638 | 0.292413 | n/a | n/a |
| Uniform | 0.299205 | 0.034028 | 0.011446 | 20.225194 | 0.336922 | 0.168333 | 88.706 ms |
| v7 Static | 0.300491 | 0.027361 | 0.006561 | 21.202830 | 0.339689 | 0.167639 | 88.358 ms |
| v8 Static | 0.300336 | 0.027917 | 0.006561 | 21.317561 | 0.339232 | 0.168750 | 89.409 ms |

Paired deltas show that perfect v8 Static does not satisfy the formal gate:

| Delta | Completion | Planned red | Realized red | Jerk | Lateral acc. | Fallback | p95 selector |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v8 - v7 | -0.000155 [-0.000651, +0.000248] | +0.000556 [-0.000139, +0.001528] | 0 [0, 0] | +0.114731 [-0.262923, +0.510018] | -0.000457 [-0.003188, +0.002053] | +0.001111 [-0.001111, +0.004583] | +1.050942 [-0.080675, +2.229460] |
| v8 - Top-1 | +0.012571 [+0.008658, +0.016847] | +0.015972 [+0.002083, +0.039726] | +0.006281 [0, +0.018844] | +12.954923 [+11.035148, +14.960182] | +0.046820 [+0.030504, +0.066454] | n/a | n/a |

Interpretation:

- v8 is not significantly worse than v7 on completion, but also does not
  improve v7 on planned red-light violation, jerk, or fallback rate.
- v8 is significantly worse than Top-1 on planned red-light violation, jerk,
  and lateral acceleration, while improving route completion.
- Runtime remains below the 100 ms tick budget on average and by aggregate
  p95, but that is not sufficient to enter formal evaluation.

Therefore the perfect 12D Static design is mathematically certified but not
industrially accepted. The next iteration must be a single attributable design
change, likely around red-light stopping-margin coverage or candidate-support
alignment, and must be revalidated on development seeds before formal seeds
are consumed.

## Accepted Runtime Optimization

The exact OBB test was retained. The collected dataset contains 121
OBB-only rejections beyond the upstream DP gate; 94 of those rejected
candidates later collide in the closed-loop outcome, and removing the OBB
test would falsely create a feasible candidate on three ticks.

The accepted implementation adds only:

- an exact circumscribed-circle broad phase before OBB SAT;
- cached ego OBB data;
- vectorized lane projection and clearance atom evaluation.

Across 12 matched runs and 2,400 planning ticks, optimized v8 versus the
original v8 has:

| Equivalence check | Mismatches |
| --- | ---: |
| Selected index | 0 |
| Feasible mask | 0 |
| Infeasibility reasons | 0 |
| Candidate scores | 0 |
| Fallback decision | 0 |

There are 42 non-bit-exact clearance atom entries with maximum absolute
difference `4.44e-16` and maximum relative difference `2.89e-15`. All
aggregate closed-loop metrics are equal.

The reusable audit command is:

```bash
python scripts/integrations/compare_diffusion_planner_selector_logs.py \
  --baseline_root /path/to/original/replays \
  --candidate_root /path/to/optimized/replays \
  --output_json /path/to/selector_equivalence.json \
  --require_equivalent
```

The persisted report is:

```text
/root/autodl-tmp/camp_dp_v7_v8_identifiability/v8_optimized_seed1/selector_equivalence_7535537.json
```

Its SHA-256 is
`1cafb68d963084e57b925a37d84454c387485e99b5a2e7c767165ddc511349b9`.
The AutoDL Diffusion Planner integration test set passes 63 tests.

The optimized historical 12-run MPC development matrix reports:

| Latency | Mean across runs | Worst run |
| --- | ---: | ---: |
| Total planning path mean | 83.39 ms | 89.68 ms |
| Total planning path p95 | 88.78 ms | 96.36 ms |
| Candidate generation mean | 56.45 ms | 58.90 ms |
| DP reward scoring mean | 18.34 ms | 18.87 ms |
| CAMP selector mean | 7.73 ms | 13.04 ms |
| CAMP atom computation mean | 5.29 ms | 9.90 ms |

All 12 run-level mean and p95 total planning-path measurements are below the
100 ms simulator tick budget. This latency result must be repeated under
explicit perfect tracking before industrial acceptance.

## Artifact Integrity

| Artifact | SHA-256 |
| --- | --- |
| DP weights | `4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75` |
| DP parameters | `ee3145b68fd1e1e44e532933dfe66cfee4384fbd637382c87ab5190c66a8e268` |
| v8 scales | `089135ac12547c7dcf551266675bd867515542410f4ece1081720e1d08c2dbac` |
| v8 weights | `bef39addd96eec9c6a9e3b43a2e5afdffe455ab4ba22a4515243403ed01d3d1a` |
| v8 training summary | `d14930d28742d62710b19ac27384f0707cefe108ea3b4bcfd5642c4b92ec2d0f` |
| v8 dataset audit | `724c5d9fae1bb7b8232506b8ff383af9415c1e554a65524d639c2bcea6d9567f` |
| fallback scales | `1bfab40c94b0c162e0da25995c97c15259f1b095b272b7a0dbf1d4555cf4a406` |
| fallback weights | `c578594bd82c737e58aca06856312cf4d211abc9b239aed7d12b480f331c3b67` |
| fallback report | `65cd9756fc22775e874ca1f03d77aad47371357346492e23c866551e14cd2b40` |
| perfect dataset audit | `59f61fd3d8ba9491ad3ab333fab8d1aa8251bd704497d23c5fab2e7d1c037a84` |
| perfect v8 scales | `567a8ad3a0d3478c71ea1adcaf33de724efc516d64f7b38c8262146c9f3ee2d3` |
| perfect v8 weights | `56bb392f4526072aa738d95f32a35fb142a719abe1839c80190c1f7af5163e85` |
| perfect v8 training summary | `fdac11b5c4f142b4e2a2204facd60e55e360e5d3c488b9dfa302ed899bf5f24f` |
| perfect full-epigraph audit | `be63d4a0ad946f0c4f37eece6658e562a2b655ee5b150f2effcf22a3150509af` |
| perfect fallback scales | `ae0932d2e4d792405c634ed0de730a2cea92c5fefdd86fc5de7d5ea89c1586c2` |
| perfect fallback weights | `25d7b652b7002008cb6e9d6c1601cc60ec8f25217a8bb703753cd9df6b0396d7` |
| perfect fallback report | `bd740fc41f48e951f335cf19094ca30422980c338d9e004416ab98e50d05e032` |
| perfect coverage report | `7e14b0422941967c26772c191adcaa35eeaea72a76be00967fa6ab6aafb37c34` |
| perfect development comparison | `380d71ad817783e6c0de1b660872c8710b623a11abc85dead451093451b3d030` |

## Formal Evaluation Gate

Do not run seeds 11, 12, and 13 yet. The perfect-tracking collection,
training, dataset audit, full-epigraph audit, and fallback counterfactual are
complete, and the matched development matrix has now been run. The current
perfect 12D Static design fails the formal gate because it does not improve v7
on planned red-light violation, jerk, or fallback rate, and is worse than
Top-1 on planned red-light violation and comfort. Formal seeds remain frozen.
Only a new frozen design that improves development evidence without safety or
completion regression may consume the formal seeds once.

## V9 Red Stopping-Margin Iteration

CAMP commit `becfee8` adds a single attributable v9 atom,
`red_stopping_margin_cost`, producing schema `dp_camp_v9_13d`. The atom is the
previous v8 shadow diagnostic promoted into the deployable selector path:
it is computed from current-tick candidates and red-route geometry before
selection, is deterministic, finite, nonnegative, independent of `w`, and is
appended to the fixed candidate atom matrix. The master objective therefore
remains the same finite maximum of affine functions of simplex-constrained
`w`; no lower-level dual or classical Benders claim is introduced.

The v9 training-log view is:

```text
/root/autodl-tmp/camp_dp_v9_red_stopping_augmented_perfect_becfee8
```

It appends the logged shadow field to the certified perfect v8 Uniform logs
without changing outcomes or using closed-loop labels as atom inputs. The
dataset audit passed with 36 logs, 7,200 records, 57,600 candidates,
8x13 atom shape, `advance_mode=perfect`, complete outcomes, finite
nonnegative atoms, exact schema metadata, and red-light provenance intact.

| Artifact | SHA-256 |
| --- | --- |
| v9 augmentation manifest | `11ddb3f627c3c0009d95104f8603c8d4b8d86be687c777fc14197bd5bb38558d` |
| v9 dataset audit | `1f59655bf1dc7dbbc956fc1d21618670e8e6fec9d5d03ede2e2d80304d402084` |
| v9 audit unit scales | `ebb2468211e7e11c89c6233c8ec5403a4b64d805dd4414a3aec4888183dbd84b` |

The v9 Robust Static checkpoint is:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v9_red_stopping_perfect_becfee8
```

It used the same grouped training contract as v8: CVaR alpha 0.9, margin
scale 0.1, margin clip 2.0, L2 `1e-4`, CLARABEL, train-only normalization,
validation fraction 0.2, seed 7, and required atom schema metadata. The solve
terminated with solver status `optimal`, `converged=true`, and
`final_master_gap=0`.

| Metric | Value |
| --- | ---: |
| Input records | 7,200 |
| Feasible-ranking records | 6,026 |
| Dropped all-infeasible records | 1,174 |
| Train groups | 29 |
| Validation groups | 7 |
| Train oracle match | 0.845367 |
| Train CVaR violation | 0.056191 |
| Validation oracle match | 0.848725 |
| Validation CVaR violation | 0.040754 |

The learned v9 weights are approximately
`[0.613724, 0, 0.118025, 0.026989, 0.000966, 0, 0, 0, 0, 0.228145, 0, 0, 0.012151]`.

The full-epigraph audit at

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v9_red_stopping_perfect_becfee8/full_epigraph_consistency.json
```

passed. The complete train-set epigraph objective and saved cutting-plane
objective differ by `2.07e-14`; the direct CVXPY value differs by
`6.90e-12`; the static weights differ by L-infinity `5.95e-11`.

| Artifact | SHA-256 |
| --- | --- |
| v9 scales | `e4290010435333eaf53a14d1fb3080fba75f1acd30dcfd4b2354e8499d6984b1` |
| v9 weights | `d8155ad12b5513f636464c3b9bca17b7da54d783431cc0d7f7ec2ec8d077a408` |
| v9 training summary | `2e8539f2b8d11bed18e3a1232169e2bfb7ca1aa4a2e4b22cdb99a4a86015b4ad` |
| v9 full-epigraph audit | `d64fccf29d18cf259722a346e36c43e56a3f9a7b77591205a08c9b1194fa6eaf` |

The v9 perfect development matrix is:

```text
/root/autodl-tmp/camp_dp_development_perfect_v9_red_stopping_becfee8
```

It completed 36/36 v9 Static runs, all with `advance_mode=perfect` and
200 selection steps. The combined strict comparison against existing Top-1,
Uniform, v7 Static, and v8 Static development runs is:

```text
/root/autodl-tmp/camp_dp_development_perfect_v9_red_stopping_becfee8/benchmark_comparison_with_v7_v8.json
```

Its SHA-256 is
`6f8f6e5b52b2090c36b425d144eb8737e9b1cc3d6e0700d06c22952996e78ea1`;
the markdown SHA-256 is
`b18ea1865fd3a673748a66d0369bd913022c3b4dadd1e24fb96fd59e75aacbe5`.
Pairing is strict: 36 common run keys and no missing or duplicate keys for
Top-1, Uniform, v7 Static, v8 Static, or v9 Static.

Aggregate development metrics:

| Variant | Completion | Planned red | Realized red | Jerk | Lateral acc. | Fallback | p95 selector |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-1 | 0.287765 | 0.011944 | 0.000279 | 8.362638 | 0.292413 | n/a | n/a |
| Uniform | 0.299205 | 0.034028 | 0.011446 | 20.225194 | 0.336922 | 0.168333 | 88.706 ms |
| v7 Static | 0.300491 | 0.027361 | 0.006561 | 21.202830 | 0.339689 | 0.167639 | 88.358 ms |
| v8 Static | 0.300336 | 0.027917 | 0.006561 | 21.317561 | 0.339232 | 0.168750 | 89.409 ms |
| v9 Static | 0.300137 | 0.025972 | 0.006561 | 21.246975 | 0.337275 | 0.167639 | 87.966 ms |

Paired v9 deltas:

| Delta | Completion | Planned red | Realized red | Jerk | Lateral acc. | Fallback | p95 selector |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v9 - v8 | -0.000199 [-0.000523, +0.000045] | -0.001944 [-0.003889, -0.000417] | 0 [0, 0] | -0.070586 [-0.456877, +0.353474] | -0.001958 [-0.004600, +0.000363] | -0.001111 [-0.004167, +0.000833] | -1.443017 [-2.419381, -0.420481] |
| v9 - v7 | -0.000354 [-0.000958, +0.000177] | -0.001389 [-0.002917, -0.000278] | 0 [0, 0] | +0.044145 [-0.283536, +0.390333] | -0.002414 [-0.005969, +0.000691] | 0 [-0.003056, +0.003889] | -0.392076 [-1.356464, +0.594637] |
| v9 - Top-1 | +0.012372 [+0.008523, +0.016558] | +0.014028 [+0.001111, +0.036806] | +0.006281 [0, +0.018844] | +12.884337 [+11.027569, +14.987724] | +0.044862 [+0.028967, +0.064036] | n/a | n/a |

Interpretation:

- v9 gives an attributable improvement over v8 on planned red-light
  violations and selector latency, with no realized-red regression and no
  statistically significant completion loss.
- v9 also improves planned red-light violations over v7, but does not improve
  jerk over v7.
- v9 remains significantly worse than Top-1 on planned red-light violation,
  jerk, and lateral acceleration, despite improving route completion.

Therefore v9 is a useful mathematically certified design iteration, but it
still does not satisfy the industrial/formal acceptance gate. Formal seeds
11, 12, and 13 remain frozen.

## Post-v9 Shadow DP-Prior Deviation Diagnostic

After the v9 gate failure, the next industrially relevant hypothesis is that
CAMP's sampled candidates can drift too far from Diffusion Planner's
deterministic low-comfort Top-1 behavior. This is evaluated as a shadow
diagnostic before any v10 schema change.

The diagnostic cost is the mean squared xy deviation from candidate 0:

```text
dp_prior_deviation(y_k) = mean_t || y_k(t) - y_0(t) ||_2^2
```

The TIER IV simulator initializes `sampled_trajectories` to zeros for the
deterministic replay prediction. CAMP candidate generation preserves that same
zero latent for candidate 0 and samples only candidates 1..K-1, so candidate 0
is the audited DP-prior reference for the current tick.

For a fixed reference trajectory `y_0`, this diagnostic is a finite
nonnegative quadratic function of `y_k`, hence convex. If promoted later, it
can be appended to the fixed candidate atom matrix and scored by the same
simplex-constrained linear master/epigraph objective. It is not currently a
v10 atom and has no selection effect.

Implemented shadow fields:

- `candidate_dp_prior_deviation_cost` in `camp_selection_log.json`;
- `latency_ms_shadow_dp_prior_deviation` per selection record;
- mean and p95 shadow latency in `camp_validation_summary.json`;
- `shadow_dp_prior_deviation` in atom-coverage reports, including record
  availability, candidate variation, reference-zero count, selected Top-1 rate,
  selected deviation, fallback variation, candidate-level target correlation,
  and selected-vs-Top-1 target gaps.

Local verification on June 13, 2026:

```text
py -3.12 -m py_compile camp_core/camp_core/integrations/diffusion_planner.py \
  camp_core/camp_core/integrations/diffusion_planner_coverage.py \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  camp_core/tests/test_diffusion_planner_integration.py \
  camp_core/tests/test_diffusion_planner_coverage.py
PYTHONPATH=F:\camp_core-main\camp_core;F:\camp_core-main \
  py -3.12 -m pytest camp_core/tests/test_diffusion_planner_coverage.py \
  camp_core/tests/test_diffusion_planner_integration.py -q
```

The targeted local result was `56 passed, 5 skipped`; the local
Diffusion-Planner test file set was `68 passed, 5 skipped`.

AutoDL verification:

```text
/root/miniconda3/envs/camp/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_coverage.py \
  camp_core/tests/test_diffusion_planner_integration.py -q
/root/miniconda3/envs/camp/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner*.py -q
```

The targeted remote result was `61 passed`; the remote DP test set was
`73 passed`.

After adding target-alignment analysis for the shadow diagnostic, the updated
local Diffusion-Planner test file set passed with `68 passed, 5 skipped`; the
updated remote DP test set passed with `73 passed`.

An exploratory smoke accidentally used seed 11 and is excluded from the
evidence below because formal seeds 11, 12, and 13 are frozen. The valid
AutoDL outcome smoke used non-formal seed 101 and wrote the new field at:

```text
/root/autodl-tmp/camp_dp_shadow_outcome_smoke_dp_prior_seed101_cb14a4a
```

It used `advance_mode=perfect`, `camp_collect_closed_loop_outcomes=true`,
3 replay steps, 4 candidates, no NPCs, and the certified v9 static checkpoint.
The generated coverage artifacts are:

| Artifact | SHA-256 |
| --- | --- |
| `dp_prior_shadow_coverage.json` | `abb127a00ea4159a6ee431d2c93a9457da5bfeb04e975f13649a2f4b42b84690` |
| `dp_prior_shadow_coverage.md` | `9c99f18da1c94134338b941a5b5621e30a53cfb3ce33e908dad82dfc7bb4d087` |

Coverage over the seed-101 smoke replay reported record availability `1.0`,
reference-zero records `3`, records with variation `3`, selected Top-1 rate
`0.333333`, and mean selected deviation `25.0845`. Candidate outcomes were
present.

The small smoke is not a performance claim, but it verifies that the new
diagnostic can expose the intended failure mode. Selected candidates improved
closed-loop value over Top-1 on all 3 records, but were worse than Top-1 on
closed-loop lateral acceleration in 2 of 3 records:

| Target | All-candidate corr | Feasible corr | Selected worse than Top-1 | Selected preference gap |
| --- | ---: | ---: | ---: | ---: |
| `closed_loop_value` | -0.980871 | -0.993403 | 0 | +72.8869 |
| `planned_red_light_cost` | n/a | n/a | 0 | 0 |
| `closed_loop_lateral_acceleration` | +0.0298217 | -0.0348515 | 0.666667 | -0.0384753 |

The full development shadow matrix is:

```text
/root/autodl-tmp/camp_dp_development_shadow_v9_dp_prior_410ff5c
```

It reran v9 Static on the 36 development scenarios with the DP-prior shadow
diagnostic and candidate closed-loop outcomes enabled. It used seeds 1/2/3,
three routes, NPC counts 0/4, traffic-light modes on/off, `advance_mode=perfect`,
8 candidates, and the certified v9 static checkpoint. Formal seeds 11, 12,
and 13 were not used.

Matrix integrity audit:

| Item | Evidence |
| --- | ---: |
| Completed logs | 36/36 |
| Selection records | 7,200 |
| Candidates | 57,600 |
| Routes | 12 each for `sample59_86`, `sample2_104`, `nishishinjuku` |
| Seeds | 1/2/3 only |
| NPC counts | 18 each for 0/4 |
| Traffic-light modes | 18 each for on/off |
| `advance_mode` | `perfect` in all 36 summaries |
| Schema | `dp_camp_v9_13d` in all 7,200 records |
| DP-prior shadow field | present in all 7,200 records |
| Candidate outcomes | present in all 7,200 records |
| Candidate 0 reference | zero in all 7,200 records |
| Candidate variation | present in all 7,200 records |

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `dp_prior_shadow_matrix_audit.json` | `424f8ccdb67042773ae67613618a31df2993dce6acb924d82ddf1782fc86120a` |
| `dp_prior_shadow_coverage.json` | `af0b0d568750ac306004c99f900894fbb52b5a585906bc5c6a0bc727e43303e8` |
| `dp_prior_shadow_coverage.md` | `d5ce9701dc90e302a9f5af04e424974f92e0b4de89eab1127145d520c2fb46fe` |
| `benchmark_comparison_with_v7_v8_v9_shadow.json` | `aeda15b15b6a722aed1fdde05673c8cc2d63c28b9062b79fbf5b5ff051192486` |
| `benchmark_comparison_with_v7_v8_v9_shadow.md` | `880369252d9b2bc54173cd7717037ecfcd9a7e4462324ddf716fc50dd977dda7` |

Full-matrix DP-prior coverage:

| Metric | Value |
| --- | ---: |
| Record availability | 1.0 |
| Records | 7,200 |
| Candidates | 57,600 |
| Records with variation | 7,200 |
| Feasible records with variation | 5,906 |
| Reference-zero records | 7,200 |
| Selected Top-1 rate | 0.020833 |
| Mean selected DP-prior deviation | 3.395307 |
| Mean shadow latency | 0.182 ms |
| p95 shadow latency | 0.224 ms |

Target alignment:

| Target | All-candidate corr | Feasible corr | Selected worse than Top-1 | Selected preference gap |
| --- | ---: | ---: | ---: | ---: |
| `closed_loop_value` | -0.003509 | -0.013334 | 0.0525 | +1.355214 |
| `planned_red_light_cost` | -0.011121 | n/a | 0 | +0.002083 |
| `closed_loop_red_light_violation` | -0.010157 | n/a | 0 | +0.000139 |
| `closed_loop_lateral_acceleration` | -0.023736 | -0.002723 | 0.658889 | -0.003943 |

The shadow matrix is strictly paired with existing Top-1, Uniform, v7 Static,
v8 Static, and v9 Static development runs: 36 common run keys, no missing
keys, and no duplicates for any variant.

Aggregate comparison:

| Variant | Completion | Planned red | Realized red | Jerk | Lateral acc. | Fallback | p95 selector |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-1 | 0.287765 | 0.011944 | 0.000279 | 8.362638 | 0.292413 | n/a | n/a |
| Uniform | 0.299205 | 0.034028 | 0.011446 | 20.225194 | 0.336922 | 0.168333 | 88.706 ms |
| v7 Static | 0.300491 | 0.027361 | 0.006561 | 21.202830 | 0.339689 | 0.167639 | 88.358 ms |
| v8 Static | 0.300336 | 0.027917 | 0.006561 | 21.317561 | 0.339232 | 0.168750 | 89.409 ms |
| v9 Static | 0.300137 | 0.025972 | 0.006561 | 21.246975 | 0.337275 | 0.167639 | 87.966 ms |
| v9 Shadow Static | 0.300137 | 0.025972 | 0.006561 | 21.246975 | 0.337275 | 0.167639 | 505.670 ms |

`v9_shadow_static` matches v9 Static on closed-loop metrics because the
shadow field has no selection effect. Its p95 latency is not a deployable
latency number because `camp_collect_closed_loop_outcomes=true` adds offline
candidate outcome labeling to every step. The deployable v9 p95 selector
latency remains the v9 Static value above.

Interpretation:

- DP-prior deviation is mathematically admissible as a fixed, finite,
  nonnegative, convex candidate cost, but the full-matrix diagnostic does not
  show strong target alignment.
- The selected candidate is worse than Top-1 on lateral acceleration in
  65.9% of records, while DP-prior deviation has near-zero correlation with
  lateral preference among feasible candidates.
- Planned-red and realized-red Top-1 gaps are not explained by DP-prior
  deviation in a way strong enough to justify promoting this diagnostic alone.
- Therefore DP-prior deviation should remain shadow-only for now. The next
  v10 candidate should prioritize a direct comfort-preserving atom computed
  from candidate kinematics, such as jerk/lateral/curvature smoothness, while
  preserving the same finite-candidate convex master contract.
