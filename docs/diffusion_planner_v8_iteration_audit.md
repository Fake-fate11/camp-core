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

## V10 comfort-preserving shadow candidate

Following the DP-prior shadow result, the next development candidate is a
shadow-only DP-prior comfort-excess diagnostic. It does not change the v9
schema, selector weights, checkpoint, hard feasible branch, or fallback policy.

For each current-tick candidate trajectory \(y_k\), with candidate 0 as the
audited DP-prior reference:

\[
j_k = \mathrm{mean}_t \lVert D^3 y_k(t) \rVert_2,
\qquad
a_k = \mathrm{mean}_t \lVert D^2 y_k(t) \rVert_2.
\]

The logged shadow costs are:

\[
c^{\mathrm{jerk}}_k = \max(j_k - j_0, 0),
\qquad
c^{\mathrm{accel}}_k = \max(a_k - a_0, 0).
\]

Mathematical contract check:

- online inputs only: current candidate coordinates and simulator `dt`;
- deterministic, finite, nonnegative, and "larger is worse";
- independent of `w`, ranking, selected candidate, and closed-loop outcome;
- candidate 0 is zero by construction, making the DP-prior reference auditable;
- for fixed reference values \(j_0,a_0\), each term is
  \(\max(\mathrm{mean}\lVert D^n y_k\rVert_2 - c, 0)\), a convex function of
  candidate coordinates;
- in the finite-candidate CAMP master, these would be fixed coefficients in
  `score = a^T w`; therefore the robust margin loss remains a finite maximum
  of affine functions in simplex weights if they are later promoted.

Implementation status:

- `compute_dp_prior_comfort_excess_costs(candidates, dt)` computes jerk-excess
  and acceleration-excess shadow arrays;
- replay logs now include `candidate_dp_prior_jerk_excess_cost`,
  `candidate_dp_prior_acceleration_excess_cost`, and
  `latency_ms_shadow_dp_prior_comfort_excess`;
- coverage reports now include `shadow_dp_prior_jerk_excess` and
  `shadow_dp_prior_acceleration_excess`, each with coverage, selected-vs-Top1
  diagnostics, latency, and target-alignment correlations.

Local verification:

```text
py -3.12 -m py_compile camp_core/camp_core/integrations/diffusion_planner.py camp_core/camp_core/integrations/diffusion_planner_coverage.py scripts/integrations/run_diffusion_planner_camp_replay.py
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'; py -3.12 -m pytest camp_core/tests/test_diffusion_planner_integration.py camp_core/tests/test_diffusion_planner_coverage.py
```

Result: 58 passed, 5 skipped.

AutoDL smoke verification:

```text
/root/autodl-tmp/camp_dp_shadow_comfort_smoke_seed101_83ef09b
```

This used non-formal seed 101, `advance_mode=perfect`, 3 replay steps, 4
candidates, no NPCs, the certified v9 static weights, and
`camp_collect_closed_loop_outcomes=true`. It is only a field/coverage smoke,
not a performance claim.

The replay summary contains:

- `mean_shadow_dp_prior_comfort_excess_latency_ms = 0.123 ms`;
- `p95_shadow_dp_prior_comfort_excess_latency_ms = 0.132 ms`;
- `fallback_rate = 0.0`;
- `candidate_feasible_rate = 0.666667`.

Generated coverage artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `comfort_shadow_coverage.json` | `07f4c1abad173a90cca8aae3257e2ce636f0e2d59d301a7206fdc6320b7058c4` |
| `comfort_shadow_coverage.md` | `7fb043eb051d5179dcf7a2cb865ca71ea53c841232fba93c16871357fcc4cd60` |

Smoke coverage reported:

| Shadow field | Availability | Records with variation | Feasible records with variation | Reference-zero records | Mean selected cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| `shadow_dp_prior_jerk_excess` | 1.0 | 3 | 2 | 3 | 0.532076 |
| `shadow_dp_prior_acceleration_excess` | 1.0 | 3 | 2 | 3 | 0.021693 |

The 12-candidate smoke is too small for alignment conclusions, but it proves
the new fields are produced by the real DP replay, summarized, parsed by the
coverage report, and inexpensive relative to candidate generation and outcome
collection.

Next gate: run the 36-run development shadow matrix with these fields enabled.
Promotion to a v10 schema is not justified until the shadow coverage shows high
variation, low latency, and stronger alignment with the jerk/lateral failure
modes than the prior DP-position deviation diagnostic.

## Full comfort-shadow matrix and horizon decision

The complete non-formal development matrix is:

```text
/root/autodl-tmp/camp_dp_development_shadow_v9_comfort_d6703f6
```

It contains 36/36 completed perfect-tracking runs over routes
`sample59_86`, `sample2_104`, and `nishishinjuku`; seeds 1/2/3; NPC counts
0/4; and traffic lights off/on. Each run used 200 steps, 8 candidates,
candidate noise scale 1.0, the certified v9 Static checkpoint, and candidate
closed-loop outcome collection. Formal seeds 11/12/13 were not used.

The fail-closed matrix audit passed:

| Item | Evidence |
| --- | ---: |
| Selection records | 7,200 |
| Candidates | 57,600 |
| All-infeasible records | 1,207 |
| Complete candidate outcomes | yes |
| Exact v9 schema metadata | yes |
| Finite nonnegative atoms | yes |
| Forbidden-seed check | yes |
| DP-prior jerk variation | 7,155 records |
| DP-prior acceleration variation | 7,156 records |
| Candidate-0 reference zero | 7,200 records for every shadow field |

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `comfort_shadow_matrix_audit.json` | `5f0bdfd47dfc509923a81d5dc46e7309862bea2315126b5b7edf8d90d8fd91dc` |
| `comfort_shadow_coverage.json` | `a9f41a3ecf56b3f9832d67a1ad628ce25474dbe957d7e26df11905438561c505` |
| `comfort_shadow_coverage.md` | `ad0842769f3e5f944ab7abe8ae41de95cb2a5e8527736f7f5915dda68d105e62` |
| `benchmark_comparison_with_v7_v8_v9_comfort_shadow.json` | `ab246daae1ef1a9cd022bd001c9534286e7c0d70f284609963338a74ccd3eab5` |
| `benchmark_comparison_with_v7_v8_v9_comfort_shadow.md` | `69d941b9ad9d6c9b941a7f9225bc157e7a3b9e757b8c3f8562a1286c5c3ea957` |

The full-horizon jerk-excess shadow is substantially better aligned with
Top-1 comfort gaps than raw DP-position deviation:

| Shadow field and target | Global corr. | Feasible corr. | Top-1-gap corr. | Feasible Top-1-gap corr. |
| --- | ---: | ---: | ---: | ---: |
| DP deviation vs jerk | 0.0324 | 0.0567 | 0.2640 | 0.4487 |
| DP deviation vs lateral | -0.0237 | -0.0027 | 0.1114 | 0.2494 |
| Jerk excess vs jerk | 0.1580 | 0.1400 | 0.7102 | 0.6736 |
| Jerk excess vs lateral | 0.0508 | 0.0758 | 0.5766 | 0.5893 |
| Acceleration excess vs jerk | 0.1356 | 0.1216 | 0.6245 | 0.6045 |
| Acceleration excess vs lateral | -0.0011 | 0.0250 | 0.4359 | 0.4074 |

Jerk excess has 7,155 records with variation, 5,836 feasible records with
variation, mean latency 0.133 ms, and p95 latency 0.143 ms. However, it is
positive for only 70.4% of candidates whose 30-step closed-loop jerk is worse
than Top-1. Acceleration excess is weaker on both target alignments and is not
retained as the leading v10 candidate.

The shadow run is strictly paired with Top-1, Uniform, v7 Static, v8 Static,
and v9 Static: all six variants have 36 unique common run keys, with no
missing or duplicate keys. Because the fields are shadow-only, v9 comfort
shadow exactly matches v9 Static on closed-loop metrics:

| Variant | Completion | Planned red | Realized red | Jerk | Lateral | Fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-1 | 0.287765 | 0.011944 | 0.000279 | 8.362638 | 0.292413 | n/a |
| v9 Static | 0.300137 | 0.025972 | 0.006561 | 21.246975 | 0.337275 | 0.167639 |
| v9 comfort shadow | 0.300137 | 0.025972 | 0.006561 | 21.246975 | 0.337275 | 0.167639 |

The shadow run's 518.868 ms aggregate p95 selector time includes offline
candidate outcome labeling and is not deployable latency. The unchanged v9
deployable p95 remains 87.966 ms.

The current implementation computes comfort excess over the complete DP
candidate horizon, while the candidate outcome labels and intended short-term
comfort objective use the first 30 steps. An offline definition-screening
probe recomputed exact 30-step relative costs from stored kinematic outcome
fields:

| Probe item | Value |
| --- | ---: |
| Jerk records with variation | 7,166 |
| Jerk feasible records with variation | 5,853 |
| Jerk positive candidates | 27,989 |
| Jerk mean selected cost | 0.137301 |
| Lateral records with variation | 7,167 |
| Jerk/lateral excess corr., all candidates | 0.710072 |
| Jerk/lateral excess corr., feasible candidates | 0.659315 |

Artifact:

| Artifact | SHA-256 |
| --- | --- |
| `comfort_horizon_alignment_probe.json` | `8180b50e19d9aebdbead2b035161921f477bfe7c6b6b45ddb4e71ceea87ca6cb` |

This probe is not online-atom or promotion evidence because it is derived from
stored outcome fields. It supports one narrower next experiment:

1. align the online DP-relative jerk-excess shadow to the same first 30
   candidate steps;
2. log the actual horizon as provenance and reject invalid horizons;
3. rerun a non-formal smoke and the complete 36-run shadow matrix;
4. promote at most the jerk atom only if the online rerun preserves coverage,
   low latency, and stronger Top-1-gap alignment.

No v10 schema promotion or formal-seed run is justified by the full-horizon
matrix. The lateral-relative candidate is deliberately deferred because its
30-step excess is highly correlated with jerk excess rather than demonstrably
orthogonal.

## Online 30-step comfort-shadow smoke

The horizon-aligned implementation was verified in the real DP replay at:

```text
/root/autodl-tmp/camp_dp_shadow_comfort_h30_smoke_seed101_ae04845
```

Configuration:

- non-formal seed 101;
- route `sample_map_tl_route_59_to_86`;
- perfect tracking and traffic lights enabled;
- 3 replay steps, 4 candidates, candidate noise scale 1.0;
- no NPCs;
- DP-reward feasibility and uniform all-infeasible fallback;
- certified v9 Static weights and scales;
- candidate outcome horizon and online comfort-shadow horizon both 30.

The first audit attempt exposed a post-processing integrity defect:
`run_diffusion_planner_camp_remote.sh` ran the standalone summarizer after the
replay, and that summarizer overwrote tracker, feasibility, seed, and shadow
provenance in `camp_validation_summary.json`. The summarizer now merges an
explicit allowlist of replay metadata into recomputed metrics. The dataset
audit also treats the completed-run benchmark seed as authoritative and
requires it to match any seed encoded in the directory hierarchy.

Verification after resummarization:

| Check | Result |
| --- | ---: |
| Completed logs | 1 |
| Selection records | 3 |
| Candidates | 12 |
| Advance mode | `perfect` |
| Summary seed | 101 |
| Formal seeds 11/12/13 excluded | yes |
| Outcome candidate coverage | 1.0 |
| Effective comfort horizon | 30 in summary and every record |
| Jerk reference-zero records | 3/3 |
| Jerk records with variation | 3/3 |
| Acceleration records with variation | 2/3 |
| Jerk p95 shadow latency | 0.119 ms |
| Acceleration selected mean cost | 0.0 |

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `h30_smoke_dataset_audit.json` | `6f6230072129589ea86a4bc478df002bf709365eecd2369cac7e165934a81ca1` |
| `h30_comfort_shadow_coverage.json` | `82b70e439abfe67df07aa47dfaaadee6fb27edc9a2c2243d4988a4cf03eb7a31` |
| `h30_comfort_shadow_coverage.md` | `a8f540bfc40b9ef9a6a5178083f48c48bffc7ca3a6804d3b5bd8551c78cb2a07` |

Local DP tests passed with 85 passed and 5 skipped. AutoDL DP tests passed
with 90 passed. The smoke proves that the horizon-aligned shadow is computed
from current DP candidates online, remains nonnegative and candidate-0
anchored, carries fail-closed provenance through post-processing, and adds
negligible diagnostic latency. It is not evidence of a selection or
closed-loop improvement because the shadow still has no selection effect and
the sample contains only three ticks.

Next gate: rerun the complete 36-run non-formal development shadow matrix with
the 30-step online definition, then compare its coverage and Top-1-gap
alignment directly against the frozen full-horizon artifacts above.

## Online 30-step comfort-shadow development matrix

The complete horizon-aligned matrix is:

```text
/root/autodl-tmp/camp_dp_development_shadow_v9_comfort_h30_8b4c66f
```

It reran the exact 36 non-formal development scenarios with v9 Static
selection and the online 30-step shadow. All three routes contain 12 completed
runs. The fail-closed audit passed for 7,200 records and 57,600 candidates:

- perfect tracking in every completed-run summary;
- complete closed-loop candidate outcomes;
- exact v9 schema and atom metadata;
- finite nonnegative atoms and all three shadow candidate fields;
- summary/path seed provenance consistency;
- seeds 11/12/13 absent;
- comfort-shadow horizon 30 in every record and summary;
- candidate 0 zero in all 7,200 records.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `h30_comfort_shadow_matrix_audit.json` | `83399bbd155d918859d2f3440803d71898e434c4cbafd8df3173dc2fb3e8171a` |
| `h30_comfort_shadow_coverage.json` | `3bf9cc7311a84aa70c98058d0a51040003d7d05065da13ca31bd0a3a5522a970` |
| `h30_comfort_shadow_coverage.md` | `2a483b47ba3de2a68052bec31e94d9b6e810928b7972a75b164168d377c3cdea` |
| `benchmark_comparison_with_v7_v8_v9_h30_comfort_shadow.json` | `20ab20aa8ff01c6fe75dbe47ac65c447b8f7dbe292bbdce59704a186e99c97d9` |
| `benchmark_comparison_with_v7_v8_v9_h30_comfort_shadow.md` | `36311803849163166d4ca6590ff00c246e331adf2f7f31d26eb3ead8b84aa8e0` |

Horizon alignment materially improves the jerk diagnostic:

| Metric | Full horizon | Online h30 |
| --- | ---: | ---: |
| Records with jerk variation | 7,155 | 7,166 |
| Feasible records with jerk variation | 5,836 | 5,853 |
| Mean selected jerk-excess cost | 0.243671 | 0.137301 |
| p95 positive jerk-excess cost | 1.356544 | 1.235095 |
| Mean shadow latency | 0.133 ms | 0.115 ms |
| p95 shadow latency | 0.143 ms | 0.126 ms |
| Global corr. with closed-loop jerk | 0.1580 | 0.2219 |
| Feasible corr. with closed-loop jerk | 0.1400 | 0.2093 |
| Top-1-gap jerk corr. | 0.7102 | 0.8829 |
| Feasible Top-1-gap jerk corr. | 0.6736 | 0.9065 |
| Positive cost on jerk-worse candidates | 70.4% | 100.0% |
| Mean cost gap on non-worse candidates | 0.095605 | 0.0 |

The 100% jerk-worse coverage and zero mean gap for non-worse candidates are
expected from using the same first-30-step finite-difference jerk definition
as the candidate outcome label. This is not label leakage: the online atom is
computed directly from the current candidate coordinates before selection,
while the outcome field is only an offline audit of the same kinematic
quantity.

The h30 jerk atom still carries useful but weaker lateral alignment:
Top-1-gap correlation is 0.5525 over all candidates and 0.5668 over feasible
candidates. Acceleration excess is not selected for promotion because its
h30 Top-1-gap correlations are weaker for both jerk (0.5729/0.6015) and
lateral acceleration (0.3046/0.2898).

Strict pairing passed for Top-1, Uniform, v7 Static, v8 Static, v9 Static, and
v9 h30 shadow: 36 common and union run keys, no missing keys, and no
duplicates. As required for a shadow-only change, h30 shadow exactly matches
v9 Static on completion, red-light metrics, jerk, lateral acceleration, and
fallback. Its aggregate 523.069 ms p95 includes candidate outcome labeling;
the unchanged deployable v9 p95 remains 87.966 ms.

Promotion decision:

1. promote only `dp_prior_jerk_excess_cost` into `dp_camp_v10_14d`;
2. keep the first-30-step horizon fixed and provenance-checked;
3. do not promote acceleration or a correlated relative lateral atom;
4. train Robust Static on augmented v9 records with grouped validation;
5. require final master gap at most 1e-6 and full-epigraph agreement before
   any closed-loop v10 claim;
6. keep formal seeds 11/12/13 frozen until the v10 development matrix passes.

This decision authorizes a v10 training experiment only. It does not establish
that adding the atom will receive nonzero robust weight or improve the
industrial development gates.

## V10 jerk-excess schema, training, and certification

Commit `3a18db0` promotes the online h30 jerk-excess shadow into the deployed
static selector schema:

```text
dp_camp_v10_14d
```

The new ordered atom appends `dp_prior_jerk_excess_cost` to the certified v9
schema. The atom is computed from the current DP candidate coordinates before
selection, uses the same fixed first-30-step horizon as the training outcome
audit, is finite, nonnegative, and candidate-0 anchored. It is independent of
the selector weights, the final ranking, the selected trajectory, and any
closed-loop outcome labels. For fixed candidates it is just one more fixed
coefficient in `score = a^T w`, so the Robust Static CVaR master remains a
finite maximum of affine functions over the simplex.

The v10 training view is:

```text
/root/autodl-tmp/camp_dp_training_v10_jerk_h30_3a18db0
```

It augments the h30 v9 shadow matrix into 36 logs, 7,200 records, and 57,600
candidates. The augmentation contract requires:

- source schema `dp_camp_v9_13d`;
- target schema `dp_camp_v10_14d`;
- effective comfort-shadow horizon 30 in every record and summary;
- finite nonnegative `candidate_dp_prior_jerk_excess_cost`;
- candidate 0 jerk-excess cost equal to zero;
- no closed-loop outcome value as an atom input;
- no stale normalized atoms or weights copied from the source logs.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `v10_jerk_excess_augmentation_manifest.json` | `96238cc4824ee0c4f7981681b0334e41a09556ca1d12596f561dce8effc50c3d` |
| `v10_training_dataset_audit.json` | `fe7aa905d51ec182b4044f72989af3d5adc38bfb85bb890d7bf16fd29335eb01` |

The certified Robust Static v10 checkpoint is:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_jerk_h30_3a18db0
```

Training configuration:

- label source: closed-loop outcome value over the h30 candidate branch;
- objective: feasible ranking with CVaR alpha 0.9;
- margin scale 0.1, margin clip 2.0, L2 1e-4;
- CLARABEL solver, maximum 20 cutting-plane iterations, tolerance 1e-6;
- p95 train-group-only atom scaling;
- grouped validation split 0.2 with seed 7;
- exact `dp_camp_v10_14d` schema required.

Training result:

| Item | Value |
| --- | ---: |
| Solver status | optimal |
| Final master gap | 0 |
| Input records | 7,200 |
| Eligible records | 5,979 |
| Dropped records | 1,221 |
| Train records | 4,848 |
| Validation records | 1,131 |
| Train groups | 29 |
| Validation groups | 7 |
| Train oracle match | 0.944926 |
| Train CVaR | 0.027241 |
| Validation oracle match | 0.953139 |
| Validation CVaR | 0.022911 |

Learned nonzero weights:

| Atom | Weight |
| --- | ---: |
| `jerk_early_cost` | 0.275082 |
| `rms_acceleration_cost` | 0.045287 |
| `speed_limit_margin_1p0_cost` | 0.007063 |
| `lane_deviation_cost` | 0.001509 |
| `progress_shortfall_cost` | 0.392047 |
| `planned_red_light_cost` | 0.115296 |
| `planned_lateral_acceleration_cost` | 0.151589 |
| `dp_prior_jerk_excess_cost` | 0.012127 |

Checkpoint artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `atom_scales_dp_static.json` | `a50d6d5b26888bdc0d2715dbfce525d3725697fa6e6565b6dd7ae9e8dd105b15` |
| `offline_weights_dp_static.npy` | `d5eabf5ce488bf46221353d1ed591ec5e4cbbb3395d10f13cf0c68b773415fb7` |
| `training_summary.json` | `7293f1da95d8662de5f8a90e75a29c83c43d059db22b233ebbbcdac8e15e6ef4` |

The full finite-candidate epigraph audit reconstructs all 37,030 train-group
finite feasible candidate constraints in one convex CVaR problem and verifies
the saved cutting-plane solution against the complete master:

| Check | Value |
| --- | ---: |
| Saved exact objective | 0.027260725971086915 |
| Full problem objective | 0.02726072606688107 |
| Full exact objective | 0.027260725969639413 |
| Saved vs full problem diff | 9.58e-11 |
| Full exact vs problem diff | 9.72e-11 |
| Weight L-infinity diff | 4.006e-8 |

Artifact:

| Artifact | SHA-256 |
| --- | --- |
| `full_epigraph_consistency.json` | `d8c0f700589d43bb98cc1a16343f8b1d0cb4ea7622b1b73d452975ec2156223f` |

## V10 real-DP smoke

The first v10 selector smoke in real Diffusion Planner replay is:

```text
/root/autodl-tmp/camp_dp_v10_jerk_h30_smoke_seed101_3a18db0
```

Configuration:

- non-formal seed 101;
- route `sample_map_tl_route_59_to_86`;
- perfect tracking and traffic lights enabled;
- 3 replay steps, 4 candidates, candidate noise scale 1.0;
- no NPCs;
- v10 static weights and scales;
- candidate closed-loop outcomes collected only for smoke/audit labeling.

The dataset audit passed. Every record has schema `dp_camp_v10_14d`, 14 atom
dimensions, `dp_prior_jerk_excess_used_as_atom = true`, and comfort-shadow
horizon 30. Selected candidate indices were `[0, 2, 1]`. The p95 runtime in
this smoke is not deployable evidence because candidate outcome collection was
enabled.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `v10_smoke_dataset_audit.json` | `bbb64af9e3c23d903c4eafc973f2801faf265fd537ff54dc2d4977c90fa32958` |
| `camp_selection_log.json` | `2a3b62ac370fde6c221f36e888f8609c262c03a48bd95b1141e813c55a7b1663` |
| `camp_validation_summary.json` | `78a715a22d593088deb6334754ba18ab858ac0a25f5178beff551cacb727afca` |

Commit `ac76541` adds an explicit dataset-audit outcome policy:
`required`, `optional`, or `forbidden`. Training and label audits keep the
default `required` behavior. Deployable latency audits must use
`--closed_loop_outcome_policy forbidden`, which rejects any collected
`candidate_closed_loop_outcomes` payload while allowing the replay's explicit
`null` sentinel for "not collected"; it must report zero outcome-candidate
coverage. This separates certification datasets from deployable runtime
measurements without weakening the fail-closed checks for schema, atoms, seeds,
DP red-light provenance, and h30 jerk-excess provenance.

The next gate is the complete non-formal v10 deployable matrix:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_jerk_h30_ac76541
```

This run intentionally omits `--camp_collect_closed_loop_outcomes`. It must be
audited with forbidden candidate outcomes, strict schema/provenance checks, and
then paired against Top-1, Uniform, v7, v8, and v9 before any industrial
improvement claim.

## V10 deployable development matrix

The first v10 deployable matrix was launched as three concurrent route shards:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_jerk_h30_ac76541
```

It completed all 36 non-formal scenarios and passed the forbidden-outcome
dataset audit and strict pairing. Its aggregate latency was rejected as a
measurement artifact, not a selector result: mean per-run p95 selection latency
was 195.338 ms, while phase decomposition showed candidate generation and DP
reward scoring roughly doubled relative to v9. The v10 atom itself remained
cheap (`p95_shadow_dp_prior_comfort_excess_latency_ms` about 0.128 ms). Because
the run used three simultaneous DP replay processes on one GPU, it is retained
only as a concurrency-contaminated diagnostic.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `v10_deployable_dataset_audit.json` | `39d9123bce03d43cb3d4ab03f944e4ede6de811f73a73866241b33aad862dab2` |
| `benchmark_comparison_with_v7_v8_v9_v10.json` | `7af6faf6c35a8bd9082d856c66f3c6913a80d8c1f92a949278daba3555146570` |
| `benchmark_comparison_with_v7_v8_v9_v10.md` | `52dad1978cff5eadea8dec41092458c43e4a072b001cb3f483a017beb1fad55d` |

The accepted latency evidence is the sequential rerun:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_jerk_h30_seq_f36c249
```

Configuration:

- 36 non-formal development scenarios;
- routes `sample59_86`, `sample2_104`, and `nishishinjuku`;
- seeds 1/2/3 only; formal seeds 11/12/13 absent;
- max NPCs 0 and 4;
- traffic lights on and off;
- perfect tracking, 200 steps, 8 candidates;
- v10 Static weights and scales;
- no `--camp_collect_closed_loop_outcomes`;
- one replay process at a time.

The deployable dataset audit passed for 7,200 records and 57,600 candidates:

| Check | Value |
| --- | ---: |
| Logs | 36 |
| Records | 7,200 |
| Candidates | 57,600 |
| All-infeasible records | 1,188 |
| Closed-loop outcome policy | `forbidden` |
| Closed-loop outcome records | 0 |
| Outcome candidate coverage | 0.0 |
| Comfort-shadow horizon verified | yes |
| Formal seeds 11/12/13 excluded | yes |
| Jerk-excess records with variation | 7,164 |
| Jerk-excess candidate-0 zero records | 7,200 |

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `v10_deployable_dataset_audit.json` | `217115cd46979ec521c9a010ec724858a15dcfdabbb86e4ce7111e3298ce9f73` |
| `benchmark_comparison_with_v7_v8_v9_v10.json` | `22635adb6685ed134ff61b21bdaf3d90aeaea50bba3657c49fc3bcc2d36284f2` |
| `benchmark_comparison_with_v7_v8_v9_v10.md` | `80621d16d2572c6a97b15db7d723506887a03f316caff1052faa8082e46590d6` |

Strict pairing passed for Top-1, Uniform, v7 Static, v8 Static, v9 Static, and
v10 Static: each variant has 36 runs, the common and union run counts are 36,
and there are no missing or duplicate run keys. Confidence intervals use the
deterministic 10,000-resample paired bootstrap.

Aggregate metrics:

| Variant | Completion | Planned red | Realized red | Jerk | Lateral acc. | Fallback | p95 latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Top-1 | 0.287765 | 0.011944 | 0.000279 | 8.362638 | 0.292413 | n/a | n/a |
| Uniform | 0.299205 | 0.034028 | 0.011446 | 20.225194 | 0.336922 | 0.168333 | 88.706443 |
| v7 Static | 0.300491 | 0.027361 | 0.006561 | 21.202830 | 0.339689 | 0.167639 | 88.357823 |
| v8 Static | 0.300336 | 0.027917 | 0.006561 | 21.317561 | 0.339232 | 0.168750 | 89.408765 |
| v9 Static | 0.300137 | 0.025972 | 0.006561 | 21.246975 | 0.337275 | 0.167639 | 87.965748 |
| v10 Static | 0.300505 | 0.026944 | 0.006421 | 21.537884 | 0.338346 | 0.165000 | 89.795503 |

The sequential latency gate is acceptable at the aggregate comparison level:
mean per-run p95 selection latency is 89.796 ms with bootstrap interval
[88.016, 91.615]. One individual run has p95 101.919 ms, so the next accepted
version should still keep a per-scenario latency audit, but v10 is not rejected
for the concurrent-root 195 ms artifact.

Phase decomposition confirms the new atom is not the latency driver:

| Phase | Mean run p95 latency |
| --- | ---: |
| Total selection path | 89.795503 ms |
| Candidate generation | 59.436115 ms |
| DP reward scoring | 20.945521 ms |
| CAMP selection | 9.431915 ms |
| h30 jerk-excess shadow | 0.127519 ms |
| Outcome collection | 0.000720 ms |

Paired v10-minus-v9 deltas:

| Metric | Mean delta | 95% bootstrap CI |
| --- | ---: | ---: |
| Completion | +0.000368 | [-0.000963, +0.001852] |
| Planned red | +0.000972 | [-0.000972, +0.003333] |
| Realized red | -0.000140 | [-0.000419, 0.000000] |
| Mean jerk | +0.290909 | [-0.599873, +1.356313] |
| Mean lateral acceleration | +0.001071 | [-0.004174, +0.006679] |
| Fallback | -0.002639 | [-0.008056, +0.002083] |
| Candidate feasible rate | +0.003073 | [-0.003785, +0.011892] |
| p95 selection latency | +1.829755 | [+0.658901, +2.972222] |

Paired v10-minus-Top-1 deltas:

| Metric | Mean delta | 95% bootstrap CI |
| --- | ---: | ---: |
| Completion | +0.012740 | [+0.008624, +0.017184] |
| Planned red | +0.015000 | [+0.000694, +0.039167] |
| Realized red | +0.006142 | [0.000000, +0.018425] |
| Mean jerk | +13.175246 | [+10.866447, +15.891541] |
| Mean lateral acceleration | +0.045933 | [+0.029604, +0.065144] |

Gate decision:

1. v10 is mathematically certified and deployable-latency feasible under a
   sequential replay measurement;
2. v10 does not improve the industrial development gate over v9;
3. relative to Top-1, v10 remains significantly worse on planned red, jerk,
   and lateral acceleration;
4. formal seeds remain frozen;
5. v10 should be archived as a mathematically valid but industrially
   ineffective schema upgrade.

The next iteration should not add another correlated comfort atom by default.
The h30 jerk-excess atom received only a small learned weight and did not move
closed-loop behavior. The higher-value next hypothesis is to audit the robust
training objective and label weighting: the current outcome value still rewards
progress enough that the optimizer accepts Top-1 comfort degradation. A
candidate v11 should first train static v10 weights from the same certified
v10 dataset with stronger comfort penalties, for example increasing jerk and
lateral-acceleration outcome weights, then run full-epigraph certification and
only a small non-formal smoke before spending another 36-run matrix.

## V10 comfort-reweighted objective audit

The next cycle kept the deployable v10 schema fixed and changed only the
robust static training objective. This preserves the finite-candidate convex
contract: candidates, atom values, atom scales, labels, and margins are fixed
before optimizing \(w\); the master problem remains the same simplex-constrained
CVaR epigraph over finite affine losses. No new online atom or DP retraining is
introduced.

Two comfort-weighted checkpoints were trained from the certified v10 training
view:

| Candidate | Asset root | Outcome weight change | Weight SHA | Full epigraph SHA |
| --- | --- | --- | --- | --- |
| j1_lat2 | `/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_comfort_j1_lat2_f36c249` | mean jerk 1.0, lateral 2.0 | `c0e03dbf8065c852ee5e6bf3c6e592396156a37daab2fb1bfcce8e9f198d988f` | `694c49ba07bb848f2b2404fbb71795538fa9a5b74e339e2601ff456ce990eddb` |
| j2_lat4 | `/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_comfort_j2_lat4_f36c249` | mean jerk 2.0, lateral 4.0 | `a4928f2ff3f347a180a52fe431a18be3fc283d2469a4649e6e764a621fa78ed9` | `6e015ea66fd1b9ca3745d1418e62e9c53c0cf05467134ba1a186a8cb14c4eca0` |

Both candidates passed the full finite-candidate epigraph audit. The pilot
matrix intentionally used only the sample59_86 route with non-formal seeds
1--3, NPC counts 0/4, traffic lights on/off, 200 steps, 8 candidates, perfect
advance, and no candidate closed-loop outcome collection.

| Artifact | SHA-256 |
| --- | --- |
| j1 pilot dataset audit | `e10f982800524a8e559b7cd184f6e3a14c498cc21d9a32f3d9345394ddb7c8a4` |
| j2 pilot dataset audit | `20c5b1f018c92aa85c5d6c5512c1995d36caf6e8cd503683bb226dc0f0e5d2c6` |
| strict pilot comparison JSON | `a9655aece3b4bd0b7ce5a5f9aa9d1d4556e5f0bb205f4fb4d9eac7570b74a333` |
| strict pilot comparison markdown | `081f5d17ecc038775ff6899ccef40b9142aaa95947a334a3dd9f70fa33ca1470` |
| mechanism diagnosis JSON | `9cab3d0dd0aeadacdd96fa81939b30269596924424d2b0b5da99c1ca0f6686bc` |
| mechanism diagnosis markdown | `da9b278e21c797877dea08f437e51f5cbabea50f19c0e3615ec1aa7a9bfe0b9d` |

The deployable dataset audits passed for both pilot roots:

- 12 logs, 2,400 records, and 19,200 candidates per candidate;
- `candidate_dp_prior_jerk_excess_cost` present for every candidate;
- candidate 0 reference-zero check passed for all 2,400 records;
- closed-loop outcome policy was `forbidden`;
- formal seeds 11/12/13 were absent;
- effective comfort-shadow horizon was 30.

Strict paired comparison used the 12 common sample59_86 keys for top1, uniform,
v7, v8, v9, v10, j1_lat2, and j2_lat4. Pairing audit: 12 common keys, 12 union
keys, no missing or duplicate keys.

Aggregate pilot metrics:

| Variant | Completion | Planned red | Realized red | Near miss | Jerk | Lateral | Fallback | p95 selection latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| top1 | 0.145106 | 0.008750 | 0.000838 | 0.046250 | 6.382563 | 0.359492 | n/a | n/a |
| v9_static | 0.154644 | 0.045833 | 0.019682 | 0.040000 | 15.404942 | 0.430507 | 0.196250 | 94.966910 |
| v10_static | 0.154272 | 0.047500 | 0.019263 | 0.024167 | 14.460047 | 0.424298 | 0.197083 | 95.463059 |
| j1_lat2 | 0.152934 | 0.045833 | 0.019263 | 0.056250 | 15.143158 | 0.419638 | 0.207083 | 94.512399 |
| j2_lat4 | 0.152689 | 0.046250 | 0.018844 | 0.055833 | 15.197518 | 0.417019 | 0.205000 | 94.444249 |

Key paired deltas on the 12-run pilot, using 10,000 deterministic bootstrap
resamples:

| Comparison | Completion | Planned red | Near miss | Jerk | Lateral | Fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| j1 - v9 | -0.001710 [-0.003362, -0.000511] | +0.000000 [-0.002500, +0.003333] | +0.016250 [-0.010417, +0.059167] | -0.261784 [-1.465535, +0.896688] | -0.010869 [-0.019645, -0.004537] | +0.010833 [-0.007917, +0.042917] |
| j2 - v9 | -0.001955 [-0.003505, -0.000788] | +0.000417 [-0.001667, +0.003750] | +0.015833 [-0.010833, +0.057917] | -0.207424 [-1.335349, +0.810927] | -0.013488 [-0.021957, -0.006428] | +0.008750 [-0.010000, +0.041250] |
| j1 - v10 | -0.001338 [-0.002653, -0.000362] | -0.001667 [-0.003750, +0.000000] | +0.032083 [+0.000000, +0.078333] | +0.683111 [-0.567419, +2.141041] | -0.004660 [-0.009081, -0.001408] | +0.010000 [-0.013333, +0.045417] |
| j2 - v10 | -0.001583 [-0.002891, -0.000577] | -0.001250 [-0.002500, +0.000000] | +0.031667 [+0.000000, +0.076667] | +0.737471 [-0.383954, +1.896679] | -0.007280 [-0.011171, -0.003866] | +0.007917 [-0.014583, +0.042500] |

Mechanism diagnosis against v10_static:

| Candidate | Selection change rate | Fallback delta | Selected feasible delta | DP-prior deviation delta | DP-prior jerk-excess delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| j1_lat2 | 0.306250 | +0.010000 | -0.010000 | +0.106194 | -0.075027 |
| j2_lat4 | 0.404167 | +0.007917 | -0.007917 | +0.287247 | -0.065409 |

Selected normalized atom deltas against v10_static show the tradeoff clearly:

| Candidate | `progress_shortfall` | `lane_deviation` | `jerk_full` | `planned_lateral_acceleration_cost` | `dp_prior_jerk_excess_cost` |
| --- | ---: | ---: | ---: | ---: | ---: |
| j1_lat2 | +0.038703 | +0.040100 | -0.029735 | -0.023895 | -0.108146 |
| j2_lat4 | +0.052815 | +0.028055 | -0.029990 | -0.025285 | -0.109353 |

Gate decision:

1. j1_lat2 and j2_lat4 remain mathematically valid deployable checkpoints;
2. neither candidate passes the industrial pilot gate;
3. both improve selected lateral acceleration cost, but both significantly
   reduce completion on this paired pilot and increase near-miss/fallback risk;
4. the mechanism is not random noise: the reweighted selectors trade lower
   comfort atoms for higher `progress_shortfall` and greater DP-prior
   deviation;
5. do not spend a full 36-run matrix on either candidate;
6. formal seeds remain frozen.

The next hypothesis should be progress-preserving comfort, not stronger
comfort reweighting. A valid next candidate may still keep the v10 schema fixed,
but the objective must prevent the optimizer from buying small comfort gains
with worse progress, lower selected feasibility, or larger DP-prior deviation.

## Progress-preserving comfort follow-up

The follow-up candidate `progress2_j1_lat2` keeps the v10 schema and the j1
comfort penalties, but raises the closed-loop progress outcome weight from
1.0 to 2.0. This is still the same finite-candidate convex optimization
problem: only the offline utility labels are changed before the robust margin
master is solved.

Training asset:

`/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_j1_lat2_7205895`

| Artifact | SHA-256 |
| --- | --- |
| `outcome_weights.json` | `9df61a4fbeeba3908113aedabf06fed1c92f0737613ccf9da93399902fa52425` |
| `training_summary.json` | `4115f718c9d068d0ac7a3eb906b0b1e635e50cbc8776ae3cde0a7d3d0742174c` |
| `offline_weights_dp_static.npy` | `44e278018ba4c21a54beb32d70d61fa3b59d695f6588a26e46a76b88643ddb8a` |
| `atom_scales_dp_static.json` | `a50d6d5b26888bdc0d2715dbfce525d3725697fa6e6565b6dd7ae9e8dd105b15` |
| `full_epigraph_consistency.json` | `c496aa979a37afab2b1ab23fbd688bb084f4ce2888aefc3078d67d2000865419` |
| `offline_counterfactual_vs_v10_comfort.json` | `96fe3f82d1af1c89015aa2cbca023a9bb9e1330d8113b15043fa8415facd48c1` |

The learned static weights moved back toward progress preservation:

| Atom | Weight |
| --- | ---: |
| `jerk_early` | 0.452293 |
| `jerk_full` | 0.018694 |
| `speed_limit_margin_0_0` | 0.000300 |
| `clearance` | 0.000069 |
| `progress_shortfall` | 0.470494 |
| `dp_prior_jerk_excess_cost` | 0.058149 |

The complete finite-candidate epigraph audit passed:

- train records: 4,848;
- finite pieces: 37,030;
- saved objective: 0.078752931479;
- complete epigraph objective: 0.078752931686;
- saved-minus-full objective: \(-2.07\times10^{-10}\);
- weight \(L_\infty\) distance: \(9.60\times10^{-10}\).

The real-DP smoke root
`/root/autodl-tmp/camp_dp_v10_progress2_j1_lat2_smoke_seed101_7205895`
passed schema, horizon, forbidden-outcome, and artifact checks:

| Smoke artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `c443a2d0e52d3b06cfab099409a40422b6011b59b79e1fd8dec57fd176b37c18` |
| `camp_validation_summary.json` | `7171736a82fa29cab7f62e11dc6f744f45e508e92226019778c802e4bfc4afb5` |
| `smoke_dataset_audit.json` | `baa0da485214afbe82d8f89525a7b060921787acb7c3eeaa671d94094647e830` |

The fixed-candidate offline counterfactual confirmed that the progress weight
does what it was intended to do:

| Variant | Selection change vs v10 | Progress shortfall | Jerk full | Lateral atom | DP-prior jerk excess |
| --- | ---: | ---: | ---: | ---: | ---: |
| v10_default | 0.000000 | 0.138684 | 2090.725656 | 0.380324 | 0.181034 |
| j1_lat2 | 0.220278 | 0.213094 | 2053.640704 | 0.376768 | 0.093676 |
| j2_lat4 | 0.329444 | 0.276263 | 2044.300934 | 0.375661 | 0.063419 |
| progress2_j1_lat2 | 0.078472 | 0.157986 | 2077.872269 | 0.379194 | 0.138045 |

The 12-run sample59_86 pilot root is
`/root/autodl-tmp/camp_dp_pilot_sample59_v10_progress2_j1_lat2_7205895`.
Its deployable dataset audit passed:

- 12 logs, 2,400 records, 19,200 candidates;
- `candidate_dp_prior_jerk_excess_cost` present for every candidate;
- candidate 0 reference-zero check passed for all records;
- closed-loop outcome policy was `forbidden`;
- formal seeds 11/12/13 were absent.

| Pilot artifact | SHA-256 |
| --- | --- |
| `pilot_dataset_audit.json` | `0a00e07b80f283965720eb8a2e965c592fbd6ba5526e17641d3d5520c78df85d` |
| strict comparison JSON | `0ae2a4e3c291c8c6ed6e63ebe33f0442d23821a511d491e65b02b4cb0cccea3c` |
| strict comparison markdown | `c1412b4dbe869b42632dfcdf83872a418fa344479642849b07b47e9a48880a6c` |

Pilot aggregate metrics:

| Variant | Completion | Planned red | Realized red | Near miss | Jerk | Lateral | Fallback | p95 selection latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v9_static | 0.154644 | 0.045833 | 0.019682 | 0.040000 | 15.404942 | 0.430507 | 0.196250 | 94.966910 |
| v10_static | 0.154272 | 0.047500 | 0.019263 | 0.024167 | 14.460047 | 0.424298 | 0.197083 | 95.463059 |
| j1_lat2 | 0.152934 | 0.045833 | 0.019263 | 0.056250 | 15.143158 | 0.419638 | 0.207083 | 94.512399 |
| j2_lat4 | 0.152689 | 0.046250 | 0.018844 | 0.055833 | 15.197518 | 0.417019 | 0.205000 | 94.444249 |
| progress2_j1_lat2 | 0.154120 | 0.047917 | 0.019263 | 0.024167 | 14.508181 | 0.425070 | 0.195000 | 94.758131 |

Key paired deltas:

| Comparison | Completion | Planned red | Near miss | Jerk | Lateral | Fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| progress2 - v9 | -0.000524 [-0.002501, +0.000988] | +0.002083 [+0.000000, +0.005000] | -0.015833 [-0.040000, +0.000000] | -0.896762 [-1.552892, -0.285088] | -0.005437 [-0.015043, +0.000165] | -0.001250 [-0.010417, +0.007917] |
| progress2 - v10 | -0.000152 [-0.000410, +0.000008] | +0.000417 [+0.000000, +0.001250] | +0.000000 [+0.000000, +0.000000] | +0.048133 [-0.368429, +0.449395] | +0.000772 [-0.000768, +0.002328] | -0.002083 [-0.005833, +0.000417] |

Gate decision:

1. `progress2_j1_lat2` is mathematically certified and deployable-smoke
   compatible;
2. it fixes the main j1/j2 failure mode by restoring progress and reducing
   fallback pressure;
3. it does not create a meaningful comfort improvement over v10;
4. relative to v9, it improves jerk and near-miss on this pilot but still
   worsens planned red-light rate;
5. do not run the full 36-run matrix for this candidate yet;
6. formal seeds remain frozen.

A red-light follow-up, `progress2_red50_j1_lat2`, raised the red-light outcome
penalty from 30 to 50 while keeping the other `progress2_j1_lat2` weights. It
trained to the exact same static weights as `progress2_j1_lat2`:

| Artifact | SHA-256 |
| --- | --- |
| `progress2_red50_j1_lat2/outcome_weights.json` | `c61a447c373ac5a18daa17492bc72e27e7ceedf2c3a12cd31c49be0795cc5fa4` |
| `progress2_red50_j1_lat2/training_summary.json` | `65aebed4c83a12418f3c080626e81fe946614a2024e5a4022aeb1e1c3fe3e0f9` |
| `progress2_red50_j1_lat2/offline_weights_dp_static.npy` | `44e278018ba4c21a54beb32d70d61fa3b59d695f6588a26e46a76b88643ddb8a` |

This shows that increasing the red-light label penalty alone is inactive for
the current robust master: it does not change the active cuts or the deployed
weights. The next hypothesis should therefore use an explicit convex simplex
lower bound on an online red-light atom, or redesign the red atom/labels so
that red-light failures enter the active finite maximum. A small lower bound is
mathematically admissible because it only adds convex linear constraints to the
simplex; it must still pass full-epigraph audit before any deployable pilot.

## Convex red-light atom lower-bound sweep

The next cycle kept the v10 atom schema fixed and added only static simplex
lower bounds. This preserves the finite-candidate convex contract: the atom
values are still fixed before optimizing \(w\), and the feasible set is the
simplex intersected with additional linear inequalities \(w_i \ge \epsilon\).

Three lower-bound candidates were screened:

| Candidate | Lower bound | Asset root |
| --- | --- | --- |
| `redfloor05` | `planned_red_light_cost >= 0.05` | `/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redfloor05_j1_lat2_e70f263` |
| `redstopfloor02` | `red_stopping_margin_cost >= 0.02` | `/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor02_j1_lat2_e70f263` |
| `redstopfloor05` | `red_stopping_margin_cost >= 0.05` | `/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263` |

All three checkpoints converged with final master gap 0 and passed complete
finite-candidate epigraph audits:

| Candidate | Weights SHA | Training summary SHA | Full epigraph SHA | Saved-full objective delta | Weight \(L_\infty\) |
| --- | --- | --- | --- | ---: | ---: |
| `redfloor05` | `426785479ea311f1ba5505cdca6ccc55a36381a7964017bc4cb5258c06db4a61` | `e32d6a393d810aa791e113171de0f571cd38d6b2a3d35aaf34710d167041bed8` | `b67358d6bef31084a9920cdc569d2db3f3cc91890a1e169f4dda14654fb5a9a2` | -3.13e-12 | 2.04e-10 |
| `redstopfloor02` | `fb9f02632314b01fc29b3269a09c08ef7cc49e511554910b57bd323e04c58d8a` | `4805b463faf2ddf4ad7a2ab5b710f2535a46cf669e510950a3b979f91c509b7f` | `7f5be618da89ae7787bb0031641d928be16428063c671745a87494db17304650` | -2.37e-11 | 8.54e-10 |
| `redstopfloor05` | `dbfe8333c8a2f7944710003d1bcf39fda84626b9c5728c80bddf6f5d41be81b1` | `b6ced7c71240e9c8b3d1c6c47470ea7411069edeb48825d24ec2f8f693951e32` | `12733885d22a50308b52ec6090af49f6ab973300a33394b140a24e5776b3c0c3` | -5.16e-12 | 1.23e-10 |

The planned-red lower bound was rejected after offline screening. It forced the
weight but barely changed the fixed-candidate selections:

| Variant | Change vs progress2 | Selected planned-red atom | Selected red-stopping atom | Progress shortfall | DP-prior deviation |
| --- | ---: | ---: | ---: | ---: | ---: |
| progress2 | 0.000000 | 0.226111 | 5.401664 | 0.157986 | 3.479023 |
| redfloor05 | 0.004583 | 0.226111 | 5.402096 | 0.157451 | 3.477529 |

The red-stopping lower-bound sweep had a real mechanism:

| Variant | Change vs progress2 | Selected red-stopping atom | Progress shortfall | Jerk full | DP-prior deviation |
| --- | ---: | ---: | ---: | ---: | ---: |
| progress2 | 0.000000 | 5.401664 | 0.157986 | 2077.872269 | 3.479023 |
| redstopfloor02 | 0.008750 | 5.045779 | 0.158911 | 2077.031772 | 3.303541 |
| redstopfloor05 | 0.013889 | 4.835732 | 0.162012 | 2076.660782 | 3.184942 |

`redstopfloor02` passed smoke and a 12-run sample59 pilot, but remained too weak
on planned-red. `redstopfloor05` passed smoke, sample59 pilot, and was expanded
to the full 36-run development matrix.

Important artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `redstopfloor02` smoke dataset audit | `5d5e261f2972aaddab7424eb4da4384c2205ec0c6baf5f221b781c45e644779e` |
| `redstopfloor02` pilot dataset audit | `ae36bf3cb1442d51dd6de204cfccf1b0c61fd87c3bb2cc004a7372adc278e646` |
| red-stopping sweep pilot comparison JSON | `b6de822a817c06291f26c8117b5e4dca4ee7205e60dff67867e64795d5efb733` |
| `redstopfloor05` smoke dataset audit | `42eb9111bd29884106bea3b01e27433042e82d86a6ad85adb72c8d3762aec7f5` |
| `redstopfloor05` full36 dataset audit | `0081688e4ca0c525d7004401fd058035edee7c4801d973f5d0b9f90ae86579c9` |
| `redstopfloor05` full36 comparison JSON | `df41383699e1e5a268160ec2dbd1f1294b07f6eceb75cc0d8746975dad77a9ca` |
| `redstopfloor05` full36 comparison markdown | `3159d84b978c97e279f7dcd23313fc481bd81fb8c9b369ed90589eb0e1d5fb72` |

The full36 dataset audit passed:

- 36 logs, 7,200 records, and 57,600 candidates;
- 1,202 all-infeasible records;
- `candidate_dp_prior_jerk_excess_cost` present for every candidate;
- candidate 0 reference-zero check passed for every record;
- closed-loop outcome policy was `forbidden`;
- formal seeds 11/12/13 were absent;
- effective comfort-shadow horizon was 30.

Strict 36-run comparison used 36 common keys for top1, uniform, v7, v8, v9,
v10, and `v10_redstopfloor05`. Pairing audit: 36 common keys, 36 union keys,
no missing or duplicate keys.

Aggregate metrics:

| Variant | Completion | Planned red | Realized red | Near miss | Jerk | Lateral | Fallback | p95 selection latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| top1 | 0.287765 | 0.011944 | 0.000279 | 0.028472 | 8.362638 | 0.292413 | n/a | n/a |
| uniform | 0.299205 | 0.034028 | 0.011446 | 0.026944 | 20.225194 | 0.336922 | 0.168333 | 88.706442 |
| v9_static | 0.300137 | 0.025972 | 0.006561 | 0.029722 | 21.246975 | 0.337275 | 0.167639 | 87.965748 |
| v10_static | 0.300505 | 0.026944 | 0.006421 | 0.023889 | 21.537884 | 0.338346 | 0.165000 | 89.795503 |
| redstopfloor05 | 0.299747 | 0.024444 | 0.006421 | 0.028889 | 20.479529 | 0.337342 | 0.166944 | 90.872458 |

Key paired deltas, 10,000 deterministic bootstrap resamples:

| Comparison | Completion | Planned red | Realized red | Near miss | Jerk | Lateral | Fallback | p95 latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| redstop05 - v9 | -0.000390 [-0.001582, +0.000783] | -0.001528 [-0.004861, +0.000694] | -0.000140 [-0.000419, +0.000000] | -0.000833 [-0.012083, +0.009028] | -0.767446 [-1.367895, -0.164735] | +0.000067 [-0.004715, +0.004468] | -0.000694 [-0.007361, +0.006111] | +2.906710 [+1.600361, +4.157821] |
| redstop05 - v10 | -0.000758 [-0.002853, +0.000731] | -0.002500 [-0.005556, -0.000000] | +0.000000 [+0.000000, +0.000000] | +0.005000 [-0.000417, +0.013056] | -1.058355 [-2.359984, -0.125415] | -0.001004 [-0.003832, +0.001577] | +0.001944 [-0.001389, +0.006944] | +1.076956 [-0.062264, +2.228079] |
| redstop05 - top1 | +0.011982 [+0.008380, +0.016005] | +0.012500 [-0.001667, +0.035000] | +0.006142 [+0.000000, +0.018425] | +0.000417 [-0.015278, +0.012361] | +12.116891 [+10.277971, +14.019839] | +0.044929 [+0.028234, +0.064603] | n/a | n/a |

Gate decision:

1. `redstopfloor05` is mathematically certified and deployable-smoke compatible.
2. The full36 deployable audit and strict pairing checks pass.
3. It is the first v10-family candidate that improves planned-red relative to
   both v9 and v10 while also improving mean jerk relative to v9.
4. p95 selection latency remains deployable at 90.872 ms, but it is slower than
   v9 by about 2.91 ms.
5. Completion, realized red, near-miss, and fallback do not show a clear
   regression relative to v9, but the confidence intervals are not strong enough
   to call these improvements.
6. Lateral acceleration is essentially unchanged relative to v9 and remains far
   worse than Top-1.
7. The industrial development gate is therefore not complete: the red/jerk
   side improved, but the lateral/comfort requirement is still open.
8. formal seeds remain frozen.

The next hypothesis should not increase the red-stopping lower bound further.
The active bottleneck is now lateral acceleration without losing the red/jerk
gains. A mathematically admissible next step is a very small convex lower bound
on `planned_lateral_acceleration_cost` combined with the `redstopfloor05`
checkpoint structure, but prior failed lateral-floor evidence means it must be
screened offline first and should not go directly to a 36-run matrix.

## Lateral lower-bound screen after redstopfloor05

A small lateral lower-bound candidate was screened offline:

`/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstop05_latfloor02_e70f263`

It keeps `red_stopping_margin_cost >= 0.05` and adds
`planned_lateral_acceleration_cost >= 0.02`. This remains mathematically
admissible because it adds only another linear lower bound to the static
simplex.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `training_summary.json` | `b268f61aa813ab0b30b47f8145f3c8300e4c1e189c92e8ea49593f1dfa624e7c` |
| `offline_weights_dp_static.npy` | `ff7ea27fadf2ef86930ce8490792ad1a34d2463969b430d88526b6a2d8773e65` |
| `full_epigraph_consistency.json` | `c0c74f1947b721afa5f60ba8a22cf7a8788f9b21ea96a340ef8cba0f19835164` |
| `offline_counterfactual_lateral_floor_screen.json` | `9bdd6f29997ba3d523946b5534004b00764a1edff8413ef2e7eff4f76501e84a` |

The complete epigraph audit passed with 4,848 train records and 37,030 finite
pieces:

- saved-minus-full objective: \(-2.63\times10^{-11}\);
- weight \(L_\infty\): \(7.81\times10^{-10}\);
- active lower bounds: `red_stopping_margin_cost=0.05`,
  `planned_lateral_acceleration_cost=0.02`.

Offline fixed-candidate screen:

| Variant | Change vs redstop05 | Planned lateral atom | Red-stopping atom | Progress shortfall | Jerk full | DP-prior deviation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| redstopfloor05 | 0.000000 | 0.379326 | 4.835732 | 0.162012 | 2076.660782 | 3.184942 |
| redstop05_latfloor02 | 0.003194 | 0.379277 | 4.835732 | 0.162054 | 2076.306916 | 3.184670 |

Decision: reject `redstop05_latfloor02` before smoke/pilot. It changes only
0.32% of fixed-candidate selections and gives a negligible lateral-atom
improvement. The lateral bottleneck is not solved by a small static lower
bound on the existing planned-lateral atom. The next lateral hypothesis should
use a more informative online atom or diagnostic, not another tiny floor on the
current atom.

## Horizon-aligned lateral shadow diagnosis

The next diagnostic cycle tested whether the lateral bottleneck came from the
existing planned-lateral atom using the complete DP candidate horizon while
the training outcome and intended short-term comfort objective use the first
30 steps.

Four current-tick, pre-selection, shadow-only candidate fields were added:

- first-30-step mean lateral acceleration;
- positive lateral-acceleration excess over deterministic candidate 0;
- first-30-step mean absolute yaw rate;
- positive yaw-rate excess over deterministic candidate 0.

All fields are deterministic, finite, nonnegative costs computed from the
current candidate coordinates before CAMP selection. They do not depend on
the CAMP weights, candidate rank, selected trajectory, or closed-loop outcome.
They are therefore admissible finite-candidate diagnostics. They are not
included in the affine CAMP score and do not change the v10 schema.

The replay metadata records the requested/effective horizon, field names, and
diagnostic latency. The dataset audit can require the horizon and finite
candidate arrays and can require candidate 0 to be zero for relative fields.
The coverage report also compares candidate-level and Top-1-gap correlations
between the diagnostics and existing atoms.

Relevant local/AutoDL tests passed:

```text
101 passed
```

### Real-DP smoke

The non-formal smoke used the certified `redstopfloor05` checkpoint:

```text
/root/autodl-tmp/camp_dp_shadow_lateral_smoke_seed101_20260614
```

Configuration: seed 101, sample59 route, traffic lights on, no NPCs, perfect
tracking, three replay steps, four candidates, noise scale 1.0, h30 candidate
outcomes, and the unchanged upstream DP commit
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The fail-closed smoke audit passed. Every field had candidate variation in all
three records, both relative fields were candidate-0 anchored, and the
effective lateral-shadow horizon was 30. Mean added diagnostic latency was
`0.427 ms`; p95 was `0.461 ms`.

A field-by-field comparison with the prior `redstopfloor05` smoke showed exact
equality for selected index, fallback flag, feasibility, infeasibility reasons,
scores, weights, selection scores/weights, raw atoms, and normalized atoms.
The new fields therefore had no selection effect.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| smoke dataset audit | `fdee414621dc6f8452442de1f54b6e395f14af26e49a2191821f2fdbde5b75d3` |
| smoke coverage JSON | `9238ed9a64468dd28aa1fc8b50b053bfd9e7c19bdf7d233ddddd056c9f7b6913` |
| smoke coverage markdown | `36569ae462c6743ec651be57a7ea16d520302525136b12787d906572d4bc9c34` |
| smoke selection log | `b9bc55d627ac27bc3d04f7fd0440839c22c88c63690b97769c9b837f157f9346` |

### Existing-matrix definition screen

Before spending a new 36-run matrix, the updated coverage analysis was run on
the existing non-formal h30 comfort matrix:

```text
/root/autodl-tmp/camp_dp_development_shadow_v9_comfort_h30_8b4c66f
```

It contains 36 logs, 7,200 records, and 57,600 candidates with complete h30
candidate outcome labels. The labels were used only for offline
definition-screening and are not online atom provenance.

A refreshed coverage pass with the current scripts wrote:

```text
/root/autodl-tmp/camp_dp_development_shadow_v9_comfort_h30_8b4c66f/lateral_definition_screen_with_offline_proxy_20260614.json
/root/autodl-tmp/camp_dp_development_shadow_v9_comfort_h30_8b4c66f/lateral_definition_screen_with_offline_proxy_20260614.md
```

This existing matrix predates the deployable h30 shadow candidate fields, so
`shadow_horizon_lateral_acceleration`,
`shadow_dp_prior_lateral_acceleration_excess`,
`shadow_horizon_yaw_rate`, and `shadow_dp_prior_yaw_rate_excess` all have
zero record availability in this artifact. It can therefore screen offline
label definitions and redundancy, but it cannot prove the deployable h30
planned-shadow atom.

The candidate-0-relative h30 lateral label proxy had variation in 7,167
records and 5,854 feasible records. Its lateral Top-1-gap correlation was
`0.7801` over all candidates and `0.8636` over feasible candidates. However,
it was not orthogonal:

- Top-1-gap correlation with the existing full-horizon planned-lateral atom:
  `0.7228` overall and `0.7203` feasible;
- Top-1-gap correlation with h30 jerk excess: `0.7071` overall and `0.6554`
  feasible;
- absolute h30 lateral and the existing planned-lateral atom had candidate
  correlation `0.8687` and feasible correlation `0.8296`.

The report also audited whether the candidate set offered a lower-lateral
alternative without sacrificing the metrics already protected by
`redstopfloor05`:

| Opportunity definition | Records | Feasible-record rate | Mean lateral gain | p95 lateral gain |
| --- | ---: | ---: | ---: | ---: |
| progress/red/jerk all non-worse | 22 | 0.003671 | 0.014056 | 0.099451 |
| progress within 0.01 m | 682 | 0.113799 | 0.007178 | 0.023544 |
| progress within 0.05 m | 1,072 | 0.178875 | 0.006407 | 0.019774 |
| progress within 0.05 m, red non-worse | 1,072 | 0.178875 | 0.006407 | 0.019774 |
| progress within 0.05 m, red/jerk non-worse | 167 | 0.027866 | 0.005254 | 0.015626 |

Although the selected candidate was laterally worse than candidate 0 in
69.58% of feasible records, a strictly non-worse progress/red/jerk alternative
existed in only 0.37% of feasible records. Even allowing 0.05 m progress loss
left a red/jerk-preserving lower-lateral alternative in only 2.79% of records,
with a small mean lateral gain.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| lateral definition screen JSON | `39b30cb14d385a8a986b6e9d9f2dbec6831f7393289789613dff749d2f1efa22` |
| lateral definition screen markdown | `8cb3f0e5a04ca8fcf1a0aad71cf1779beca043db7aa04c2444c8602fa550f91a` |

Decision:

1. Do not promote h30 absolute lateral, relative lateral, absolute yaw rate, or
   relative yaw rate into a new schema from this evidence.
2. Do not retrain CAMP or run a new 36-run matrix for these candidate fields.
3. The lateral failure is not primarily missing atom information. The existing
   planned-lateral atom already aligns strongly with the h30 lateral label, and
   the relative definition is substantially redundant with both it and the
   jerk-excess atom.
4. The stronger falsifiable root-cause hypothesis is candidate-pool
   limitation: the current `K=8`, noise-scale-1.0 pool rarely contains an
   alternative that improves lateral while preserving progress, red, and jerk.
5. The next controlled variable should therefore be candidate generation, not
   another atom. Screen lower diffusion noise or a larger candidate pool on
   non-formal scenarios while keeping DP weights, CAMP weights, feasibility,
   schema, and formal seeds fixed. Any candidate-pool change must pass the
   existing `<100 ms` deployable latency gate before a development matrix.

## Candidate-Pool And Progress-Guard Screen

This screen kept the certified `redstopfloor05` CAMP weights, atom schema,
DP checkpoint, sample59 route, seeds 1/2/3, NPC counts 0/4, traffic lights
off/on, perfect tracking, and no closed-loop outcome labels. Formal seeds
11/12/13 remained frozen.

Two fail-closed issues were fixed before interpreting the new artifacts:

1. `camp_validation_summary.json` now carries the same
   `camp_shadow_lateral_comfort` metadata as `camp_replay_summary.json`, so
   lateral-shadow horizon certification is available to the dataset audit.
2. The comparison script now canonicalizes run keys from benchmark fields
   before falling back to legacy `benchmark_key` strings, avoiding false
   strict-pairing failures when old and new summaries are compared.

The standalone resummarizer was also made conservative: when a completed
validation summary already exists, it preserves existing non-null metrics that
cannot be recomputed without a route centerline, such as
`route_completion_rate`, and then merges replay metadata.

All candidate-pool and guard artifacts below passed the deployable dataset
audit: 12 logs, 2,400 records, 8 candidates, perfect advance mode, forbidden
closed-loop outcomes, forbidden formal seeds, h30 comfort-shadow horizon, and
h30 lateral-shadow horizon.

Correction: the two `routec0progress` rows in the table are retained only as
obsolete evidence. A later code audit found that those runs projected
ego-frame candidate trajectories onto the world-frame route centerline. The
current implementation transforms the route centerline into the ego frame and
limits the projection horizon before applying the route-progress guard, but
the old `routec0progress` artifacts below must not be used as valid gate
evidence.

| Config | Completion delta | Planned red delta | Realized red delta | Near-miss delta | Jerk delta | Lateral delta | Fallback delta | p95 latency delta | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `noise0p5` | -0.006746 [-0.013698, -0.001591] | -0.030833 | -0.018425 | +0.001667 | -4.475678 | -0.053655 | -0.038333 | -1.375799 | reject: completion loss |
| `noise0p75` | -0.000679 [-0.000897, -0.000477] | -0.002917 | -0.000838 | +0.000833 | -1.745514 | -0.006744 | -0.005417 | +1.682255 | reject: completion loss |
| `noise0p75_progress0p90` | -0.000661 [-0.000845, -0.000492] | -0.002917 | -0.000838 | +0.001250 | -1.856721 | -0.006720 | -0.004167 | +0.851429 | reject: completion loss |
| `noise0p75_progress0p95` | -0.001367 [-0.002507, -0.000663] | -0.002083 | -0.000838 | +0.013333 | -2.531749 | -0.008638 | -0.007500 | +1.433509 | reject: completion and near-miss |
| `noise0p75_c0progress0p98` | -0.000724 [-0.000985, -0.000476] | -0.002917 | -0.000838 | +0.000833 | -2.141276 | -0.007159 | +0.000000 | -2.315476 | reject: completion loss |
| `noise0p75_c0progress1p00` | -0.000725 [-0.000984, -0.000475] | -0.002500 | -0.000838 | +0.000833 | -2.489813 | -0.006967 | +0.007917 | +0.615702 | reject: completion and fallback |
| `noise0p75_routec0progress0p98` | -0.000679 [-0.000894, -0.000482] | -0.002917 | -0.000838 | +0.000833 | -1.745514 | -0.006744 | -0.005417 | +17.177267 | reject: completion and latency |
| `noise0p75_routec0progress1p00` | -0.000822 [-0.001467, -0.000286] | -0.000833 | -0.000838 | +0.000833 | -2.650780 | -0.006628 | +0.000417 | +18.176821 | reject: completion and latency |

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `noise0p5` dataset audit | `466a2037b0e0032f3e3483791dd296405c4a5f56e596f9c93da350b40466b6e4` |
| `noise0p5` comparison JSON | `921e8180cbc1959d9e4fe3724213594a49211e918faae2728e3d64812c08c07e` |
| `noise0p75` dataset audit | `16a9c3bb1f20d9ffc068affb29aa366a36490b5a2a53e1c3816bc5e52ca986f4` |
| `noise0p75` comparison JSON | `1cd9c323ec175ac5d1fae9e1298c4b066ce7728402a32c3cd39d91aad9648a96` |
| `noise0p75_progress0p90` dataset audit | `37d2851a09c8f51dce4fbac2dcb40dd592bde5b2fdd617c5f0091e8f6d91d69e` |
| `noise0p75_progress0p90` comparison JSON | `c6d237f7e1ee651e0fda7583fb3dd5aaff5473ee94064dbf48b29cbfd061a012` |
| `noise0p75_progress0p95` dataset audit | `05e2e5a32aaaa7b693f819672b3ad511352fd2be51d8442e292410856032dcd3` |
| `noise0p75_progress0p95` comparison JSON | `302d0ff6ffd8079df405a0b74c4950b0a9f71b5cde105b90dd8a1203c8939718` |
| `noise0p75_c0progress0p98` dataset audit | `9ddb5cfbcaea97f3a5224d08d262225b65621f29e33f9824e0d3d3de0d6724f8` |
| `noise0p75_c0progress0p98` comparison JSON | `888c5bdb12f408ff3fdb8af5229a17d2651a5af314056568b5badd5adc3f58dc` |
| `noise0p75_c0progress1p00` dataset audit | `24229b11600a042388e0130a600bab46ec04fdbfd2ee23c72c2c8ee8ef8666d7` |
| `noise0p75_c0progress1p00` comparison JSON | `8777a52899b07a4c261464898a39fc26b996db7a68c8017b3c87cdcdc130793b` |
| `noise0p75_routec0progress0p98` dataset audit | `be136d7ea0387956dd416ca1ed374d8fcbc168d8402d2fcd4518f5a4565a39ee` |
| `noise0p75_routec0progress0p98` comparison JSON | `84efc5302b3078ba676ecb60b7ac87ca617bed731c1a2dd738c19c5199c3b271` |
| `noise0p75_routec0progress1p00` dataset audit | `e3814f36ac5c0da137c08fa29bf32bb223112495ee85f39c5b63f588e98cd376` |
| `noise0p75_routec0progress1p00` comparison JSON | `98cb58fab2f96ffcf908fcf7e797809e37185fbc04cd25ad9b14a09377ca301a` |

Decision:

1. Do not expand any screened candidate-pool or progress-guard setting to a
   36-run development matrix. Every screened setting has a strictly negative
   paired completion delta on sample59.
2. Do not run formal seeds. The development gate is still not satisfied.
3. Do not retrain DP. DP remains the frozen official checkpoint.
4. Do not retrain CAMP yet from these scalar screens alone. The failure mode is
   not a missing lateral/yaw atom and not solved by lower noise or simple
   progress guards.
5. The next useful design should be a two-stage selector or Pareto feasibility
   filter that enforces route-progress non-regression before comfort/red-light
   improvements are allowed, then reuses the existing CAMP affine score within
   the admissible set. This preserves the finite-candidate mathematical
   contract because the admissible set is fixed before optimizing or applying
   weights, but it needs a cheap online route-progress surrogate before it can
   be considered deployable.

## Perfect-tracker first-step reach screen

A follow-up audit of the Diffusion Planner simulator showed that
`PerfectTracker.track()` sets the target speed from the first reference point,
`ref_world[0] - current_pose`, and only uses the longer horizon for the
resume-from-rest push. A new default-off deploy-time guard was therefore added:

```text
--camp_min_candidate0_step_reach_ratio
```

For candidate set \(X=\{x_k\}_{k=0}^{K-1}\), with each trajectory already in
the ego frame, define

\[
r_k = \left\|x_{k,0}^{xy}\right\|_2.
\]

The guard keeps candidate 0 and rejects candidate \(k>0\) when
\[
r_k < \rho r_0,\quad \rho\in[0,1].
\]

This is not a CAMP atom and is not part of \(a^\top w\). It is a
selection-precomputed feasibility filter: deterministic, finite, nonnegative,
fixed before applying CAMP weights, independent of candidate ranking and
closed-loop outcome, and therefore compatible with the finite-candidate
robust-selection contract. It is a closer online surrogate for the perfect
tracker's executed progress than the rejected route-progress artifacts above.

The screen used the same sample59 paired setup as the candidate-pool screen:
seeds 1/2/3, NPC counts 0/4, traffic lights off/on, perfect tracking,
forbidden closed-loop outcome labels, frozen DP checkpoint
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, and frozen `redstopfloor05`
CAMP weights. All listed runs passed dataset audit with 12 logs, 2,400
records, 8 candidates, h30 comfort/lateral shadow horizons, and forbidden
formal seeds.

| Config | Completion delta | Planned red delta | Realized red delta | Near-miss delta | Jerk delta | Lateral delta | Fallback delta | Feasible-rate delta | p95 latency delta | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `noise0p75_stepreach0p98` | -0.000286 [-0.000513, -0.000061] | -0.002917 | -0.000419 | +0.000833 | -2.661177 | -0.001925 | +0.002917 | -0.037135 | -0.352523 | reject: completion and fallback |
| `noise0p75_stepreach0p99` | -0.000163 [-0.000360, +0.000026] | -0.002917 | -0.000419 | +0.000417 | -2.941414 | -0.000380 | +0.008750 | -0.095000 | -2.657798 | reject: fallback |
| `noise0p75_stepreach0p995` | -0.000179 [-0.000421, +0.000054] | -0.002500 | -0.000419 | +0.000000 | -3.093988 | +0.001026 | +0.012917 | -0.155052 | +0.370795 | reject: fallback and lateral |
| `noise0p75_stepreach1p00` | -0.000082 [-0.000266, +0.000106] | -0.002917 | +0.000000 | +0.000000 | -3.242133 | +0.001720 | +0.014167 | -0.310417 | -2.314045 | reject: fallback and lateral |
| `noise0p75_stepreach0p99_preservefeasible` | -0.000274 [-0.000493, -0.000058] | -0.002500 | -0.000419 | +0.000417 | -2.713757 | -0.001618 | +0.001250 | -0.093802 | -3.013839 | reject: completion |

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `noise0p75_stepreach0p98` comparison JSON | `7efc3a2a82801995d419ac54bd5c2af57605ba42f78773b03750795d99a0f24d` |
| `noise0p75_stepreach0p99` dataset audit | `12545f3ab764ea6d9c66372452c08380a96032b9c20a91f5f5778302d074fa1d` |
| `noise0p75_stepreach0p99` coverage JSON | `a06caa8eb157b83a052dc43da87bc99475a140632b98210b93e6093d7cbf81ea` |
| `noise0p75_stepreach0p99` coverage markdown | `6d1a5039e0243ef8d6688eb5531ea13f517b11051ffaff18d53402c7964688a4` |
| `noise0p75_stepreach0p99` comparison JSON | `db44864b8d9934e104c8e4a4ba435efbd961b5c693e535b35e8c1e3ce9172c71` |
| `noise0p75_stepreach0p99` comparison markdown | `696085e12b4a57a584de074849d27cb7e7ed7a537bd91820864a4a84f74ee39a` |
| `noise0p75_stepreach0p995` dataset audit | `8f70f7d9dc2067c10118679b799dfa486a4b47cc63a56304d15dcbf8e92e0898` |
| `noise0p75_stepreach0p995` coverage JSON | `f7509f533bc88ec4acb57b7e7e9031229159370e4e65bbd15b8899d9b2285c9e` |
| `noise0p75_stepreach0p995` coverage markdown | `ef7b4e46d93482d354dfe49b3338e5353fad97b4675375b8124d8c7574746828` |
| `noise0p75_stepreach0p995` comparison JSON | `aa1dedd786ec43f1f049305bdbac239733366f5d993283b4b7a6f66bccb90a6f` |
| `noise0p75_stepreach0p995` comparison markdown | `36b7cbca5fa54774295e56fe89ce1554ed89b62e79728c563fb5d28d9e7ce60f` |
| `noise0p75_stepreach1p00` comparison JSON | `161ede35e4b5e13c08cf86f6ae4d517a99c6281b0dc05029a5a010ae36868034` |
| `noise0p75_stepreach0p99_preservefeasible` dataset audit | `f05247dae7dc51e97173a5178fd44a492ed47e5e829667b4bfaaae7f6b93f621` |
| `noise0p75_stepreach0p99_preservefeasible` coverage JSON | `5f487b4e8ab6621fa658365b5f5fea20cdfb89ea3bea702d7de6b661d6e8792a` |
| `noise0p75_stepreach0p99_preservefeasible` coverage markdown | `cc863841265af92d2519e111b2997c2538c41b8637a9e8556e4b57640746397f` |
| `noise0p75_stepreach0p99_preservefeasible` comparison JSON | `88a4ed0a681a24a9f634065ba3899d0084b7a055bd91c8f0ce0a98abec88ea0a` |
| `noise0p75_stepreach0p99_preservefeasible` comparison markdown | `03b284d68194a7bff009b678ce9558b29a6e44484491a640bbc097edf48cabb2` |

Decision:

1. First-step reach is the best-tested online surrogate for the current
   perfect tracker, but alone it still does not satisfy the development gate.
2. Ratios near 0.99 make completion nearly non-regressive on this small
   sample, but they do so by shrinking the feasible set and increasing
   fallback. Ratios at 0.995 and 1.0 also worsen mean lateral acceleration.
3. A default-off `--camp_candidate0_step_reach_preserve_feasible` safeguard was
   also tested at ratio 0.99. It relaxed 19 of 2,400 guarded ticks
   (`0.007917`) and reduced the fallback delta to nearly zero, but completion
   became strictly negative again. The failure is therefore not only
   all-infeasible fallback; it is also that the preserved candidates recover
   insufficient executed progress.
4. Do not expand any first-step reach setting to the 36-run development matrix
   yet and do not run formal seeds.
5. The next design should preserve candidate-0 execution progress without
   causing fallback: for example, a lexicographic or Pareto filter that first
   keeps candidates within a small first-step reach tolerance, then applies
   CAMP among non-dominated candidates on red, jerk, and lateral, while always
   retaining candidate 0 as a feasible fallback. This remains a fixed
   finite-candidate admissible-set construction and does not require DP
   retraining.

## Nonempty lexicographic preselection screen

The scalar first-step guard was followed by a default-off, staged
finite-candidate preselection. This implementation keeps the certified
`redstopfloor05` CAMP checkpoint, v10 atom schema and scales, affine CAMP
score, robust master, DP checkpoint, and DP training fixed.

Let \(F_0\) be the set accepted by the existing DP-reward hard constraints.
For fixed nonnegative tolerances, the staged sets are

\[
\begin{aligned}
F_1 &= \{k\in F_0:p_k\geq \max_{j\in F_0}p_j-\epsilon_p\},\\
F_2 &= \{k\in F_1:r_k\leq \min_{j\in F_1}r_j+\epsilon_r\},\\
F_3 &= \{k\in F_2:j_k\leq \min_{j\in F_2}j_j+\epsilon_j\},\\
F_4 &= \{k\in F_3:l_k\leq \min_{j\in F_3}l_j+\epsilon_l\},
\end{aligned}
\]

where \(p\) is current-tick DP candidate progress, \(r\) is planned-red
cost, \(j\) is DP-prior jerk-excess cost, and \(l\) is h30 absolute lateral
acceleration. The original CAMP score \(a_k^\top w\) selects within \(F_4\).
The screened configuration was

```text
progress epsilon = 2.0 m
planned-red epsilon = 0.0
jerk epsilon = 1.0
lateral epsilon = 0.05
```

### Mathematical contract

Each \(F_i\) is a subset of the finite DP candidate index set. If \(F_{i-1}\)
is nonempty, its finite maximum or minimum is attained. The attaining
candidate satisfies the corresponding inequality for every nonnegative
epsilon, so \(F_i\) is nonempty. Therefore a nonempty \(F_0\) cannot be
emptied by these four stages.

The construction is deterministic for fixed candidate fields and epsilons,
is evaluated before CAMP weights and final ranking, and uses neither the
selected trajectory nor a closed-loop outcome. Since
\(F_4\subseteq F_0\), it cannot restore a candidate rejected by an existing
hard constraint. If \(F_0\) is empty, the existing fallback path is retained.
This proves that the preselection itself creates no new all-infeasible case;
it does not claim that a later independent collision check can never cause a
fallback.

The atom values remain finite constants on the selected finite candidate set,
so \(a_k^\top w\) remains affine in \(w\). The CVaR/simplex/L2 robust master
and its convexity are unchanged. This is finite-candidate preselection, not
classical Benders decomposition.

The dataset audit now optionally verifies this contract fail closed. It
requires exact summary metadata and fixed stage order, finite nonnegative
epsilons, integer stage counts in `[0,K]`, monotonically nonincreasing stage
counts, all-zero stages for an empty base set, and a nonempty final stage for
every nonempty base set.

### Offline fixed-candidate screen

The offline definition screen combined two independent sample59 log roots and
reconstructed the base feasible set by removing only the experimental
first-step-guard reason. Every other safety reason remained hard.

| Quantity | Result |
| --- | ---: |
| Logs / records | 24 / 4,800 |
| Base-feasible / base-empty records | 3,826 / 974 |
| Selection change versus base | 0.123366 |
| Mean base / final-stage candidates | 7.567956 / 6.845008 |
| Step-reach delta | -0.000517 |
| DP progress delta | -0.047745 |
| Planned-red delta | 0.000000 |
| Jerk-excess delta | -0.018796 |
| Absolute lateral delta | -0.007309 |

This was definition-screen evidence only. It showed the intended comfort
tradeoff and structural nonemptiness, but the progress and step-reach losses
prevented treating it as closed-loop improvement evidence.

### Sample59 paired pilot

The online pilot used seeds 1/2/3, NPC counts 0/4, traffic lights off/on,
200 steps, perfect tracking, eight candidates, no collected outcome labels,
and no formal seeds. Coverage and strict pairing passed with 12 common and 12
union keys. The new fail-closed audit certified all 2,400 stage-count records;
409 records had an already-empty base set.

| Metric: lexicographic minus `redstopfloor05` | Mean paired delta | 95% bootstrap CI |
| --- | ---: | ---: |
| Route completion | -0.002000 | [-0.003377, -0.000990] |
| Planned red-light violation | -0.002500 | [-0.008750, +0.001250] |
| Realized red-light violation | -0.001256 | [-0.003769, 0.000000] |
| Near miss | +0.001250 | [0.000000, +0.003333] |
| Mean jerk | -1.738080 | [-2.684234, -0.778644] |
| Mean lateral acceleration | -0.019114 | [-0.033407, -0.007297] |
| Fallback | -0.031667 | [-0.086667, 0.000000] |
| Candidate feasible rate | -0.044687 | [-0.080626, +0.005366] |
| Mean per-run p95 latency | +0.066943 ms | [-1.939409, +2.171649] |

The variant's aggregate mean per-run p95 latency was `95.941132 ms`, with
bootstrap interval `[93.160839, 99.237584]`. Latency was therefore not the
rejection reason. Completion was strictly worse and near miss did not improve,
so the variant was rejected before the 36-run matrix. Formal seeds remain
frozen.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| Offline counterfactual JSON | `a04d82ccf107443ba3e4cd0cd66fa7bd4abded0cc139a806b9ff375e09a01e06` |
| Offline counterfactual markdown | `89627c6462a46ece666c037d8c53e7fbb91991833d25a3b740d30e8ba2b74356` |
| Pilot fail-closed dataset audit | `db6ff63c6c5f6941845e8f2ce26f6e5ef5e8a2da91847c960a066b6e7f76de4b` |
| Pilot coverage JSON | `3e5e3cc1f7952ce37358bdb88f41b7ce12a0335d96b686a0af19205701bc2ca3` |
| Pilot coverage markdown | `1925938d4470c1a6574cfcef8787135a3cf3871df8a66122bce7a7b551410631` |
| Pilot comparison JSON | `2ccb43d52d6dcdf9ce2da1e8d2f0724a6f478232be1546ed8be2ebf4e375d6f6` |
| Pilot comparison markdown | `47fa96433429f68719677e5f35b2581e25d78c742eb451a7bcc44ab2332be8e9` |

Verification for this milestone was `118 passed, 5 skipped` locally and
`123 passed` on AutoDL.

Decision:

1. Reject this lexicographic configuration. Do not run the 36-run matrix or
   formal seeds.
2. Do not retrain DP or CAMP from this result. The preselection changed the
   admissible set, not the CAMP robust-training problem.
3. The current evidence supports a working diagnosis that the eight-candidate
   pool lacks enough progress-preserving comfort alternatives. It is not a
   theorem that no possible K=8 rule can pass.
4. The next controlled variable is candidate count. Screen K=12 first while
   keeping DP/CAMP weights, noise, feasibility, route, schema, and seeds fixed.
   A sufficiently long non-formal profile must pass the `<100 ms` p95 gate,
   and fixed-candidate logs must show progress-preserving Pareto opportunities
   before any paired sample59 pilot is launched.

## Candidate-count latency and opportunity screen

The next screen changed only the number of stochastic DP candidates. It kept
the official DP checkpoint, certified `redstopfloor05` CAMP weights and
scales, noise scale `1.0`, DP-reward feasibility, h30 reward and comfort
horizons, perfect tracking, sample59 route, seed 1, no NPCs, traffic lights
off, and 200 steps fixed.

| Candidate count | p95 total | p95 generation | p95 reward | p95 CAMP | Completion | Jerk | Lateral | Fallback |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 94.395 ms | 56.635 ms | 18.252 ms | 14.537 ms | 0.156785 | 10.128817 | 0.426936 | 0.120 |
| 9, first run | 99.185 ms | 63.364 ms | 22.931 ms | 17.604 ms | 0.156941 | 11.009428 | 0.428313 | 0.120 |
| 9, audited rerun | 100.256 ms | 62.698 ms | 23.333 ms | 18.199 ms | 0.156941 | 11.009428 | 0.428313 | 0.120 |
| 10 | 108.882 ms | 67.241 ms | 25.344 ms | 19.088 ms | 0.156981 | 11.095556 | 0.428930 | 0.120 |
| 12 | 116.161 ms | 69.300 ms | 25.937 ms | 22.114 ms | 0.157059 | 9.060290 | 0.430164 | 0.130 |

K=10 and K=12 clearly failed the latency gate. K=9 had no deployable margin:
the same deterministic run moved from `99.185 ms` to `100.256 ms` p95 across
two executions. Its comfort metrics were also worse than K=8.

The audited K=9 rerun logged candidate step reach for every candidate. A new
outcome-free fixed-candidate audit used zero tolerance and required each
alternative to have:

1. step reach and DP progress no lower than the CAMP-selected candidate;
2. planned-red cost no higher;
3. jerk and lateral cost both no higher, with at least one strictly lower.

Among 176 non-fallback ticks, candidate index 8 was selected on 28 ticks, but
there were zero weak or joint-strict comfort-Pareto opportunities from any
candidate. Therefore the extra random sample changed ranking without supplying
the required progress-preserving comfort alternative.

A predefined diagnostic grid used step-reach tolerances `{0, 0.001, 0.002}` m
and DP-progress tolerances `{0, 0.05, 0.10}` m, with planned-red tolerance
fixed at zero. The ninth candidate supplied an opportunity unavailable among
the first eight candidates on at most `1.136%` of non-fallback ticks, and only
after allowing progress loss. At `0.05 m` progress tolerance the
expanded-only rate was `0.568%`; at `0.10 m` it was at most `1.136%`.
This is too sparse to justify the measured latency regression or a paired
closed-loop pilot.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| K=9 diagnostic dataset audit | `8a75100b8fa6ac4a5dd1467c5dbd23f5e7d7be31723d07324e490c04084d0ef1` |
| K=9 strict opportunity JSON | `5ea27931e964405a8723857fff66eb801a70e32a01baff490ef640772f952b08` |
| K=9 strict opportunity markdown | `760379193501e89d4370e739d220791f531f7844eb5e4cba64c47fddc83a32ad` |
| K=9 tolerance-grid summary | `016d02e69bf83ca4b7738abcd386244e91cb55737edf7f60954d5f538f826ddc` |

Verification for this milestone was `122 passed, 5 skipped` locally and
`127 passed` on AutoDL.

Decision:

1. Reject K=9, K=10, and K=12 random candidate-count expansion. Do not run a
   sample59 matrix or formal seeds.
2. Do not optimize the CAMP robust master or retrain weights from this screen.
   The missing object is a suitable candidate, not a convexity or solver
   failure.
3. The next candidate-generation experiment should keep K=8 and preserve the
   perfect tracker's first-step execution quantity by construction. A fixed,
   outcome-free prefix blend between candidate 0 and each stochastic DP sample
   is a suitable screen: it changes only the finite candidate set, then
   re-applies the existing reward, safety, atom, and CAMP checks.

## Perfect-tracker prefix-blend screen

A default-off structured candidate transform was implemented for K=8. For
candidate \(k>0\), fixed blend length \(m\), and trajectory index \(t\),

\[
y'_{k,t}=(1-\lambda_t)y_{0,t}+\lambda_t y_{k,t},
\qquad
\lambda_t=\min(t/m,1).
\]

Candidate 0 is unchanged. Every stochastic candidate has exactly the same
first reference pose as candidate 0 and recovers its original DP sample from
`t >= m`. Orientation vectors are normalized only inside the blend interval;
the exact first pose and post-blend suffix are explicitly restored afterward.
The transform is deterministic, finite, independent of CAMP weights and
closed-loop outcomes, and default-off.

For xy coordinates this is an affine map with fixed coefficients. No atom,
schema, scale, CAMP weight, CVaR/simplex/L2 term, or robust-master constraint
was changed. The transformed candidate set is fully rescored by the existing
DP reward, safety, atom, and CAMP paths. Therefore the robust master continues
to optimize affine candidate scores \(a_k^\top w\). This is candidate
construction, not Benders decomposition.

The dataset audit was extended to require exact blend metadata and, for every
record, the configured blend length, finite `[K,2]` first-reference
coordinates, equality of all first-reference coordinates to candidate 0, and
equal candidate step reach. All three profiles passed this fail-closed audit.

### Tracker-source audit

The fixed DP commit's `PerfectTracker.track()` uses:

1. first-reference displacement magnitude for target speed;
2. first-reference orientation for the next yaw;
3. when current speed is below `0.1 m/s`, full-horizon tail reach for a
   resume-from-rest speed override.

The prefix blend preserved items 1 and 2 exactly but restored the stochastic
tail after \(m\), so item 3 remained candidate-dependent. This is the only
tracker path through which the transformed middle/tail can alter execution
when the first pose is fixed.

### Non-formal profiles

The screen kept the same sample59 seed-1, no-NPC, traffic-light-off,
200-step configuration as the candidate-count screen. No outcome labels or
formal seeds were used.

| Config | p95 latency | Completion | Completion delta | Jerk | Jerk delta | Lateral | Lateral delta | Fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 94.395 ms | 0.156785 | 0.000000 | 10.128817 | 0.000000 | 0.426936 | 0.000000 | 0.120 |
| blend 3 | 99.331 ms | 0.154933 | -0.001852 | 5.763921 | -4.364896 | 0.411095 | -0.015841 | 0.110 |
| blend 5 | 94.572 ms | 0.155294 | -0.001491 | 5.468463 | -4.660354 | 0.415439 | -0.011497 | 0.110 |
| blend 10 | 98.316 ms | 0.155489 | -0.001296 | 5.166127 | -4.962690 | 0.416899 | -0.010036 | 0.110 |

Planned-red and near-miss rates remained zero in this scenario. Every blend
length strongly improved realized jerk and lateral acceleration and reduced
fallback, but every one also reduced route completion. Since first pose was
certified equal, the source audit identifies the candidate-dependent
resume-from-rest tail-speed override as the remaining execution mechanism.

The strict fixed-candidate opportunity audit found weak comfort-Pareto
opportunities on only `1.685%`, `2.247%`, and `1.124%` of non-fallback ticks
for blend lengths 3, 5, and 10 respectively. Joint-strict opportunities were
zero for blend 3 and 10 and `1.124%` for blend 5.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| Blend-3 dataset audit | `874cd4170dc9df8e39548d41874afdb584127163cde995f416d9b3bdae0d7c2f` |
| Blend-3 opportunity JSON | `87e2c668b54262fe531667885feef17d71e7bd656ca28fd9870247d6098da84f` |
| Blend-3 opportunity markdown | `3c657f4dc59bf12d13743276e1b98d3d9418cd42fa6725ae1a63c3be3ae5bd1e` |
| Blend-5 dataset audit | `eade31cafbcbccf8e326648848dda36bdffbdbfab94ca7a11d4a8b23ebbc83ee` |
| Blend-5 opportunity JSON | `d5b3f3814af5447c240882898d440c4a78d101f14518733eb9d6a160df505602` |
| Blend-5 opportunity markdown | `55781676bf383dd2bce3a1c6e50e35e74866094874c1fe99a84f5cb90ef2de0d` |
| Blend-10 dataset audit | `4d5a30fff187ce11380cc1e134e923f509bd3ce98e02c81461078aa1ec203f57` |
| Blend-10 opportunity JSON | `018b827c80902ef27d5f50f041d9bb2d2d8827aa0519e8666319f05fe5ad9476` |
| Blend-10 opportunity markdown | `357104f16d65f51c6a85e1c4405afa1960c5ddd640f2b4d8498943d832be8c56` |

Verification for this milestone was `130 passed, 5 skipped` locally and
`135 passed` on AutoDL.

Decision:

1. Reject all three prefix-blend settings before a paired sample59 matrix.
   Completion regressed in the first deterministic profile.
2. Keep the transform default-off as an audited diagnostic, not a promoted
   deployment policy.
3. The next atom/selector diagnosis must model the actual PerfectTracker
   command: first-step target speed and heading, plus the tail-based restart
   override. Planned full-trajectory jerk/lateral costs alone are not aligned
   with the simulator's realized one-step command.
4. Tracker-aligned diagnostics may be introduced as fixed, outcome-free
   candidate constants. They do not alter convexity in \(w\); they must remain
   shadow-only until their relationship to realized completion and comfort is
   established on non-formal data.

## PerfectTracker command-shadow certification

The next default-on logging diagnostic reproduces the command path used by the
fixed DP commit without changing feasibility, CAMP scores, or selection. The
source path is:

1. transform each ego-frame candidate to world coordinates;
2. apply `scenario_generation.mpc_tracker.postprocess_reference`;
3. call `scenario_generation.mpc_tracker.PerfectTracker.track`.

The postprocessor leaves the first pose unchanged but can freeze the remaining
positions after a smoothed-speed stop transition. The command shadow therefore
reproduces the forward velocity smoothing and force-stop logic before using the
postprocessed tail.

For candidate \(k\), let \(q_{k,0}\) be its first ego-frame xy point,
\(\bar q_{k,T}\) its postprocessed tail point, \(T\) its trajectory length,
\(\Delta t\) the simulation step, \(s\) the nonnegative current longitudinal
speed, and \(a_{\mathrm{prev}}\) the current longitudinal acceleration. With
the upstream constants \(v_{\max}=20\), \(s_{\mathrm{restart}}=0.1\), and
\(\bar v_{\mathrm{restart}}=0.5\),

\[
u_{k,0}=\min(\lVert q_{k,0}\rVert/\Delta t,v_{\max}),\qquad
\bar v_k=\lVert\bar q_{k,T}\rVert/(T\Delta t),
\]

\[
I_k=[s<0.1\land \bar v_k>0.5],\qquad
u_k=
\begin{cases}
\max(u_{k,0},\min(v_{\max},\bar v_k)),&I_k,\\
u_{k,0},&\text{otherwise}.
\end{cases}
\]

The logged command-aligned comfort quantities are

\[
a_k=(u_k-s)/\Delta t,\quad
j_k=\lvert a_k-a_{\mathrm{prev}}\rvert/\Delta t,\quad
\omega_k=\lvert\operatorname{wrap}(\theta_{k,0})\rvert/\Delta t,\quad
a^{\mathrm{lat}}_k=u_k\omega_k.
\]

The replay log includes all inputs needed to recompute these values. The
dataset audit checks exact tracker metadata, fixed thresholds, candidate
dimensions, finite values, strict restart inequalities, and every formula
above. The shadow remains outcome-free and has `selection_effect=false`.

These expressions are not claimed to be globally convex in trajectory
coordinates: norm clipping and the restart branch contain `min`, `max`, and a
discrete condition. For the existing finite-candidate CAMP master, however,
their values are fixed constants before optimization. If a later version
promotes one to a candidate atom, the score remains affine in \(w\), so the
simplex/CVaR/L2 master remains convex. This does not constitute classical
Benders decomposition.

An upstream parity check used 72 random 80-step candidates at current speeds
`0.0`, `0.05`, and `2.0 m/s`. It directly called the fixed DP commit's
postprocessor and tracker, then compared their outputs with the CAMP helper.
Maximum absolute errors were:

| Quantity | Maximum absolute error |
| --- | ---: |
| Target speed | `4.440892098500626e-16` |
| Signed acceleration | `7.105427357601002e-15` |
| Yaw-rate magnitude | `1.7763568394002505e-15` |
| Postprocessed tail xy | `0.0` |
| Tail-average speed | `0.0` |
| Jerk magnitude | `5.684341886080802e-14` |

Local verification for this implementation was `137 passed, 5 skipped`.
The next step is an AutoDL test and non-formal K=8 baseline replay with the
new shadow enabled. Formal seeds remain frozen.

### AutoDL command-shadow baseline

AutoDL verification passed with `142 passed`. The upstream parity artifact is:

`/root/autodl-tmp/camp_dp_tracker_command_shadow/perfect_tracker_parity_20260614.json`

Its SHA-256 is
`33383fc18fec02f5dae1c226225147458ff37dec42f9700eeac8c6957debd53c`.

Two non-formal sample59 K=8 profiles used the frozen `redstopfloor05`
checkpoint, seed 1, no NPCs, traffic lights off, 200 steps, DP-reward
feasibility, and no candidate outcome labels. Both dataset audits certified
200 records and 1,600 candidates. Relative to the prior baseline, the first
profile had exactly equal selected indices, feasible masks, atoms, candidate
rewards, and closed-loop trajectory.

| Profile | Total p95 | Command-shadow p95 | Completion | Jerk | Lateral | Fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| First run | 104.908 ms | 0.320 ms | 0.156785 | 10.128817 | 0.426936 | 0.120 |
| Independent rerun | 97.375 ms | 0.317 ms | 0.156785 | 10.128817 | 0.426936 | 0.120 |

The first run exceeded the latency gate because candidate-generation p95 rose
to `67.749 ms`; the command shadow itself remained below `0.321 ms`. The
independent rerun passed the total gate with candidate-generation p95
`62.867 ms`. This supports keeping the diagnostic, but a later paired matrix
must still evaluate total latency rather than subtracting the shadow phase.

Artifacts:

| Artifact | SHA-256 |
| --- | --- |
| Rerun selection log | `a3cabcee084d5f56f07727a2c910c38937d56e8b3d82983ba6f26330f5624c73` |
| Rerun validation summary | `0614dd5324cdb8d0d7ecab3ffe9ef5f84d3adf83b8371ced0bd1aa02bc2cec07` |
| Rerun dataset audit | `076c181972a2d8949bb1f9479f8c387a49f26ef61d13ba82548c0f5504e5a833` |
| Command opportunity JSON | `db2332011b9a739b669c8e574eb20aad1a245e0b457ea367e24bdeaf7ec37470` |
| Command opportunity markdown | `20a987867cc2361071f0d4f4a69e04898197fcd18832a7bc9132622eedf9d4ae` |

### Nonempty command-dominance postselection

The outcome-free command audit initially found 24 of 176 non-fallback ticks
with target-speed/red-preserving candidates that jointly improved command jerk
and lateral acceleration. That definition was rejected because only `37.5%`
of those changes preserved h30 DP progress and mean progress fell by
`0.115 m`.

The accepted offline definition additionally requires DP progress not to fall.
Let \(b\) be the candidate selected by the unchanged CAMP selector and \(F\)
the existing base-feasible set. Define

\[
D_b=\{k\in F:
u_k\ge u_b,\ p_k\ge p_b,\ r_k\le r_b,\ j_k\le j_b,\
a^{\mathrm{lat}}_k\le a^{\mathrm{lat}}_b\}.
\]

Candidate \(b\) is always in \(D_b\), so the set is nonempty whenever \(F\) is
nonempty. A replacement is permitted only if some member strictly improves
command jerk or lateral acceleration. Candidates in \(D_b\) are ordered
deterministically by command jerk, command lateral acceleration, original CAMP
score, then candidate index. If \(F\) is empty, the original fallback and
selected index are retained.

This finite postselection:

1. never restores a candidate removed by base safety/reward feasibility;
2. cannot create a new all-infeasible tick;
3. preserves target speed, h30 progress, and planned-red cost relative to the
   original CAMP selection;
4. preserves command jerk and lateral acceleration and requires a strict
   improvement before changing the selection;
5. does not modify the atom schema, scales, CAMP weights, or robust master.

The baseline-dependent finite rule is not classical Benders decomposition.
It leaves the certified convex weight-training problem unchanged. Its mapping
from trajectories to a selected discrete index is not claimed to be convex.

The strict offline counterfactual changed 9 of 176 non-fallback ticks
(`5.1136%`). Mean deltas on changed ticks were:

| Quantity | Delta |
| --- | ---: |
| PerfectTracker target speed | +0.018265 m/s |
| h30 DP progress | +0.045761 m |
| Planned-red cost | 0.000000 |
| Command jerk | -1.826506 m/s^3 |
| Command lateral acceleration | -0.016396 m/s^2 |

The rule is implemented behind
`--camp_perfect_tracker_command_postselection`, which is default-off and
requires DP-reward feasibility plus `advance_mode=perfect`. Summary metadata
and every per-record baseline/final index and stage count are independently
recomputed by the dataset audit. The next evidence step is a non-formal
sample59 paired pilot. Formal seeds remain frozen.

### Command-dominance paired pilot

The non-formal paired pilot used the fixed DP commit, frozen
`redstopfloor05` checkpoint, `sample59_86`, seeds 1/2/3, NPC counts 0/4,
traffic lights on/off, 200 steps, K=8, candidate noise 1.0, h30 DP-reward
feasibility, and PerfectTracker. The only intentional difference from the
existing 12-run baseline was
`--camp_perfect_tracker_command_postselection`.

The fail-closed dataset audit passed all 12 logs and 2,400 records. It
independently recomputed the command shadow and postselection, rejected
candidate outcome payloads, and confirmed that formal seeds 11/12/13 were
absent. Strict pairing found 12 common and 12 union keys with no missing or
duplicate runs.

The postselector changed 75 of 2,400 ticks (`3.125%`). Its own mean and p95
latencies were `0.0713 ms` and `0.1020 ms`; the command shadow mean and p95
latencies were `0.2371 ms` and `0.3070 ms`.

| Postselection minus `redstopfloor05` | Mean paired delta | 95% bootstrap CI |
| --- | ---: | ---: |
| Route completion | +0.000212 | [+0.000037, +0.000422] |
| OBB collision | 0.000000 | [0.000000, 0.000000] |
| Near miss | 0.000000 | [0.000000, 0.000000] |
| Lane violation | -0.001667 | [-0.005000, 0.000000] |
| Realized red-light violation | 0.000000 | [0.000000, 0.000000] |
| Planned red-light violation | +0.001250 | [0.000000, +0.002500] |
| Mean jerk magnitude | -0.085687 | [-0.465913, +0.269498] |
| Mean lateral acceleration | +0.001056 | [-0.000074, +0.002311] |
| Fallback rate | -0.000833 | [-0.003750, +0.001250] |
| Total selection p95 | +3.535447 ms | [+1.054654, +6.066308] |

The variant's mean per-run total p95 was `99.4096 ms`, compared with
`95.8742 ms` for the baseline. The variant therefore had almost no latency
margin even though the postselection phase itself was inexpensive.

Decision: reject before the 36-run matrix. Completion improved, but planned
red-light violations and mean lateral acceleration increased, the jerk
improvement was not statistically established, fallback non-increase was not
established, and the total latency increment was strictly positive.

The mathematical reason is important. Membership in \(D_b\) proves only
one-tick, candidate-conditional dominance for the fixed state and candidate
set at that tick. Once a different candidate is executed, the next state,
future candidate sets, traffic-light exposure, and tracker history can differ.
Consequently, the finite rule cannot imply monotonicity of closed-loop
planned-red, jerk, or lateral metrics. The implementation remains useful as a
default-off audited ablation, but it is not an industrial acceptance
candidate.

The next design must evaluate a short closed-loop state transition or a
mathematically certified upper bound over that transition. It must keep all
quantities outcome-free at online selection time, preserve the existing CAMP
CVaR/simplex/L2 master unless a separately versioned convex atom is justified,
and screen counterfactual definitions offline before another simulator
matrix. Formal seeds remain frozen.

Artifacts:

| Artifact | Path | SHA-256 |
| --- | --- | --- |
| Pilot root | `/root/autodl-tmp/camp_dp_tracker_command_postselection_sample59_pilot_f6c2381` | n/a |
| Dataset audit | `postselection_dataset_audit.json` | `73490b3a99b6a28158dc6f28161fe158996057c9e3449e66b36884e4362bfd0e` |
| Paired comparison | `paired_comparison.json` | `586a859e2b97b4b75ba469294be5f510fbadd021a12147ffd607dcdf82183503` |
| Paired comparison markdown | `paired_comparison.md` | `320fc2a3b7c843a32fd2da911176191faa2c30c1680cbce3b1b49f202d972bdd` |

## Full-red safety budget audit

Commit `6980b628356df560133ebe8a47d5549cfc617ffa` extends the
PerfectTracker rollout shadow analyzer without changing the online selector,
atom schema, CAMP weights, DP weights, feasibility, or simulator execution.
The new report records every selected h30-safe candidate that is unsafe under
the full-horizon red-light shadow, then evaluates predeclared H3 safety
budgets:

- progress loss budgets: `0.5`, `1.0`, and `1.5 m`;
- H3 distance loss budgets: `0.05` and `0.1 m`;
- H3 max lateral acceleration guard: `2.0 m/s^2`;
- no hard jerk guard, because no specification-backed jerk threshold has been
  selected yet.

The budget screen is a development sensitivity analysis, not an online
selector and not parameter tuning. It uses the union red certificate
`max(h30_red, h80_red)` and chooses among admissible lower-red candidates by
minimum union-red, original CAMP score, then candidate index. The computation
uses only current-tick candidate constants and remains outcome-free.

AutoDL verification at this commit passed the full CAMP test set:
`166 passed`. The same commit also passes locally with `161 passed, 5 skipped`.

The real sample59 non-formal v3 shadow artifact was re-analyzed at:

`/root/autodl-tmp/camp_dp_tracker_rollout_shadow_sample59_acba493`

| Artifact | SHA-256 |
| --- | --- |
| Budget analysis JSON | `c2958b8fa057f510d2909e287f7192da9034153ffc50333b8c8d28da97c04d46` |
| Budget analysis markdown | `982669b0587ecec382f7e8d8c9f2144a1efb27e48515c90c5fb66eaa060572b8` |

The selected h30-safe/full-red misses are now attributed as:

| Count | Value |
| --- | ---: |
| Selected h30-safe/full-red records | 32 |
| Fallback misses | 0 |
| Nonfallback misses | 32 |
| With a lower union-red base-feasible candidate | 20 |
| Without a lower union-red base-feasible candidate | 12 |
| Selected full-horizon red records, regardless h30 status | 107 |

The predeclared H3 budget sensitivity is:

| Progress loss budget | H3 distance loss budget | Covered records | Coverage | Union-red delta | Progress delta | H3 distance delta | H3 vector jerk delta | H3 lateral delta |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 m | 0.05 m | 10/32 | 0.312500 | -0.650000 | -0.313686 | -0.008459 | +1.928413 | +0.014726 |
| 0.5 m | 0.1 m | 10/32 | 0.312500 | -0.650000 | -0.313686 | -0.008459 | +1.928413 | +0.014726 |
| 1.0 m | 0.05 m | 14/32 | 0.437500 | -1.071429 | -0.505146 | -0.020840 | +2.086067 | +0.021312 |
| 1.0 m | 0.1 m | 15/32 | 0.468750 | -1.133333 | -0.591974 | -0.034521 | +1.292091 | +0.016710 |
| 1.5 m | 0.05 m | 14/32 | 0.437500 | -1.142857 | -0.538808 | -0.022304 | +2.419672 | +0.018773 |
| 1.5 m | 0.1 m | 17/32 | 0.531250 | -1.529412 | -0.776554 | -0.047694 | +2.743974 | -0.012755 |

Decision: keep this as shadow analysis and do not implement the safety
override yet. The analysis confirms a real h30/full-horizon blind spot, but it
also shows that even the widest predeclared budget covers only `17/32` misses
and materially worsens H3 vector jerk. The remaining `12/32` misses have no
lower union-red base-feasible candidate, so a finite selector alone cannot
repair them without changing candidate generation or feasibility. The next
design step is therefore a mathematically explicit lexicographic safety rule
with state-dependent progress/comfort budgets, plus a separate answer for the
no-lower-red-candidate cases. Formal seeds remain frozen.

## Safety override mathematical contract

The proposed next rule is now specified in
`docs/dp_camp_mathematical_contract.md` under "Full-Horizon Safety Override".
It is intentionally not implemented yet. The contract keeps the unchanged
CAMP candidate unless all of the following are true:

1. the baseline selected candidate has positive union-red exposure;
2. a base-feasible candidate has strictly lower union-red exposure;
3. that candidate satisfies predeclared progress, H-step tracker distance,
   and absolute comfort budgets;
4. deterministic tie-breaking selects among the remaining candidates by
   union-red certificate, original CAMP score, then index.

The nonempty/fail-closed proof is baseline retention: if the strict
override set is empty, the unchanged CAMP choice is used. Therefore the rule
cannot create fallback by itself and cannot restore candidates rejected by
hard feasibility. If it overrides, it proves only fixed-current-candidate
union-red improvement under the declared budgets. It does not prove future
Diffusion Planner replanning improvement.

The contract also records an impossibility result: if no base-feasible
candidate has lower union-red exposure than the selected candidate, no
finite-candidate selector can repair that tick by reordering alone. The
sample59 v3 evidence contains `12/32` selected h30-safe/full-red misses in
that category. Those cases require a candidate-generation, feasibility,
horizon, fallback, or planner-interface change rather than another CAMP score
tie-break.

Decision: the next coding step is not an online selector. First choose
specification-backed or state-derived progress/comfort budgets and justify
whether jerk can be a hard cap. If no such budget can cover enough of the
`20/32` repairable misses without material comfort regression, the safety
override remains rejected and the investigation moves to candidate-pool or
feasibility changes. Formal seeds remain frozen.

### State budget diagnosis

The same sample59 v3 artifact was summarized by state to separate the
`20/32` repairable misses from the `12/32` no-lower-red misses.

| Artifact | SHA-256 |
| --- | --- |
| State budget diagnosis JSON | `002e90e8f39c02e8d78dce5029e7c344c43ad4fc82904b3862c98706a3824e8f` |
| State budget diagnosis markdown | `55705100dbc694000a42d5e43b27be80ed1e9f137b3dcf7a2f2d75302400ef96` |

| Group | Speed p50 | Progress p50 | H3 distance p50 | Union-red p50 | H3 jerk p50 | H3 max lateral p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Repairable by finite selector | 5.001160 | 12.262799 | 1.455898 | 29.250000 | 19.653819 | 0.326900 |
| No lower-red feasible candidate | 0.715262 | 1.556463 | 0.145918 | 32.750000 | 24.829574 | 0.025714 |

For the repairable group, the best lower-red candidate reduces union-red by a
mean `-3.1`, but the mean progress delta is `-1.270539 m` and the mean H3
vector-jerk delta is `+3.154113 m/s^3`. The absolute progress loss normalized
by one-tick travel has mean `2.647902`, median `2.584709`, and p90
`4.504409`. Therefore a one-step-travel progress budget is too strict for
most currently repairable red-light misses; a larger budget would need a
separate stopping-envelope or safety-distance justification rather than a
simple kinematic one-tick argument.

The no-lower-red group is mostly low-speed, low-progress, low-H3-distance
behavior. That supports the current impossibility diagnosis: these cases are
more likely candidate-pool or stopping/candidate-generation failures than
ranking failures inside the existing base-feasible set.

### Stopping-margin consistency screen

Commit `42a29394b2cd3a80557891ed3a4425d5bf6ad3a3` extends the rollout shadow
analyzer with an additional stricter budget table. It reuses the existing
`candidate_red_stopping_margin_cost`, which is computed from current route
red-light points, a `2.0 m/s^2` comfort deceleration envelope, a `3 m` stop
buffer, and the current candidate trajectory. This is still a shadow-only
fixed-candidate screen.

The analyzer now reports two tables:

1. lower union-red plus progress/H3-distance/H3-lateral budgets;
2. the same budgets plus red stopping-margin nonworse relative to the selected
   candidate.

AutoDL verification at this commit passed the full CAMP test set:
`166 passed`. Local verification passed with `161 passed, 5 skipped`.

The real sample59 non-formal v3 shadow artifact was re-analyzed at:

`/root/autodl-tmp/camp_dp_tracker_rollout_shadow_sample59_acba493`

| Artifact | SHA-256 |
| --- | --- |
| Stopping-margin analysis JSON | `add077a63a7c10261f6f158b4fcf0439a7e3b3d35dd90c1020298cb311cfa92b` |
| Stopping-margin analysis markdown | `39e1c47ff8868be462eb5741d692d68400fd19ccb6c33eb7ee07f10d19da2e0c` |

The stricter stopping-margin-nonworse budget sensitivity is:

| Progress loss budget | H3 distance loss budget | Covered records | Coverage | Union-red delta | Stopping-margin delta | Progress delta | H3 vector jerk delta |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 m | 0.05 m | 5/32 | 0.156250 | -0.600000 | -4.618275 | -0.419675 | +0.489044 |
| 0.5 m | 0.1 m | 5/32 | 0.156250 | -0.600000 | -4.618275 | -0.419675 | +0.489044 |
| 1.0 m | 0.05 m | 8/32 | 0.250000 | -1.125000 | -4.918167 | -0.536327 | +0.947411 |
| 1.0 m | 0.1 m | 8/32 | 0.250000 | -1.187500 | -5.086774 | -0.618475 | +0.742798 |
| 1.5 m | 0.05 m | 8/32 | 0.250000 | -1.250000 | -4.100930 | -0.595235 | +1.531220 |
| 1.5 m | 0.1 m | 10/32 | 0.312500 | -1.750000 | -4.415187 | -0.876761 | +2.266827 |

Decision: do not implement this as an online safety override. The
stopping-margin condition makes the selected alternatives more safety
consistent, but it reduces coverage to at most `10/32` selected h30-safe/full
red misses and still worsens H3 vector jerk. The evidence now points away
from another selector-only iteration and toward candidate-generation or
feasibility changes for the low-speed no-lower-red cases, plus a
specification-backed jerk/comfort cap before any deployable safety override.
Formal seeds remain frozen.

### Infeasible lower-red candidate attribution

Commit `75daf6a7544c3eda451b0052e778d107a94a014a` extends the rollout
shadow analyzer with a no-lower-feasible attribution pass and exposes the
result in both JSON and markdown reports. For every selected h30-safe/full-red
miss with no lower union-red base-feasible alternative, the analyzer now
separates two cases:

1. a lower union-red candidate was generated, but base feasibility rejected it;
2. no lower union-red candidate existed anywhere in the generated candidate
   pool.

The analysis remains shadow-only and outcome-free. It uses current-tick fixed
candidate constants: union-red certificates, base feasibility masks, original
CAMP scores, and already logged infeasibility reasons. It does not change the
online selector, atom schema, CAMP weights, Diffusion Planner weights, or any
formal seed.

Verification:

| Environment | Result |
| --- | --- |
| Local Windows, Python 3.12 | `162 passed, 5 skipped` |
| AutoDL, Python 3.9 | `167 passed` |

The real sample59 non-formal v3 shadow artifact was re-analyzed at:

`/root/autodl-tmp/camp_dp_tracker_rollout_shadow_sample59_acba493`

| Artifact | SHA-256 |
| --- | --- |
| Infeasible-lower-red analysis JSON | `59962861e181d8104e0795e2782dd88eb12ae9356b07fb6261ebb9ec9d831fbb` |
| Infeasible-lower-red analysis markdown | `d968b330972abb0111ba47918188d19f57d263eb224f428773317166535f0990` |

The selected h30-safe/full-red misses are unchanged:

| Count | Value |
| --- | ---: |
| Records | 2,400 |
| Candidates | 19,200 |
| Fallback records | 484 |
| Nonfallback records | 1,916 |
| Selected h30-safe/full-red records | 32 |
| With lower union-red base-feasible candidate | 20 |
| Without lower union-red base-feasible candidate | 12 |

The new attribution resolves the `12/32` no-lower-feasible cases:

| Diagnosis | Count |
| --- | ---: |
| Events without lower union-red base-feasible candidate | 12 |
| Events with lower union-red candidates blocked by feasibility | 12 |
| Events with no lower union-red candidate in the generated pool | 0 |

The infeasible lower-red candidate reason counts are:

| Reason | Count |
| --- | ---: |
| `dp_underprogress` | 51 |
| `dp_kinematic` | 13 |
| `dynamic_obb_collision` | 4 |

Decision: keep the online safety override rejected for now. The new evidence
shows that the generated pool does contain lower-red alternatives for all
previously unexplained misses, but those alternatives are excluded by the base
feasibility contract. A finite-candidate selector cannot legally select them
without changing the feasibility definition. `dynamic_obb_collision` must stay
hard. `dp_kinematic` should also be treated as hard unless a separate
trajectory-validity argument proves otherwise. The only plausible next
investigation is therefore a narrowly scoped, shadow-only feasibility audit of
`dp_underprogress`: determine whether low-speed red-light approach states need
a state-dependent progress relaxation, a stopping-specific candidate branch,
or no change. Formal seeds remain frozen, and no new CAMP training or online
selector implementation is justified by the current evidence.

### Underprogress-blocked lower-red counterfactual

Commit `a12282bff718a0e1e138b0d534e5a32aae87137b` adds the narrow
shadow-only `dp_underprogress` counterfactual. It does not change the replay
selector. For the no-lower-feasible h30-safe/full-red misses, it virtually
ignores only `dp_underprogress` and leaves every other infeasibility reason
hard. This is a feasibility audit, not a CAMP score change and not a Benders
cut.

Verification:

| Environment | Result |
| --- | --- |
| Local Windows, Python 3.12 | `163 passed, 5 skipped` |
| AutoDL, Python 3.9 | `168 passed` |

The real sample59 non-formal v3 shadow artifact was re-analyzed at:

`/root/autodl-tmp/camp_dp_tracker_rollout_shadow_sample59_acba493`

| Artifact | SHA-256 |
| --- | --- |
| Underprogress relaxation JSON | `6c20d0cbd6232a21a513643a071e9ae86cee90a4c12a2c6791ec2ecbd17b8068` |
| Underprogress relaxation markdown | `bafeed0d0e8481842b5a1e1ca3a87f0b1e9747b7cfe52cf42f51efb056aea328` |

The no-lower-feasible diagnosis remains:

| Diagnosis | Count |
| --- | ---: |
| Events without lower union-red base-feasible candidate | 12 |
| Events with lower union-red candidates blocked by feasibility | 12 |
| Events with no lower union-red candidate in the generated pool | 0 |

After virtually ignoring only `dp_underprogress`:

| Metric | Value |
| --- | ---: |
| Event denominator | 12 |
| Events with lower union-red candidate restored | 10 |
| Events still without lower union-red candidate | 2 |
| Mean eligible candidates | 4.25 |

Mean deltas for the 10 restored events, chosen by minimum union-red then
existing selection score/index, are:

| Metric | Mean delta |
| --- | ---: |
| Union-red certificate | -31.800000 |
| Red stopping-margin cost | -28.655999 |
| Progress | -1.168156 m |
| H3 distance | -0.035404 m |
| H3 mean vector jerk | -11.011042 m/s^3 |
| H3 mean lateral acceleration | -0.002860 m/s^2 |
| PerfectTracker target speed | -0.219185 m/s |
| PerfectTracker jerk command | +3.935407 m/s^3 |
| PerfectTracker lateral command | -0.009176 m/s^2 |

Decision: this overturns the earlier suspicion that the no-lower-feasible
misses are mainly candidate-pool absence. They are mostly progress-gate
misses: the lower-red candidates already exist and are often more stop-like
under the full-horizon red and stopping-margin shadows. However, the
counterfactual still changes the external feasible set, so it cannot be
deployed as a selector-only override. The next acceptable step is another
offline gate: evaluate predeclared progress/H3-distance/2.0 m/s^2 lateral
budgets on the `dp_underprogress`-relaxed candidates, and separately inspect
the remaining `2/12` hard-blocked cases. Only if that budget screen is
coverage-positive, comfort-nonregressive, deterministic, and fail-closed
should an online, default-off underprogress relaxation be specified. Formal
seeds remain frozen.

### Underprogress-relaxed budget gate

Commit `71a2b9b3a77901e1bafa7ba17f483c9496ab96d5` adds the
predeclared budget tables for the `dp_underprogress` counterfactual. The
tables use the same offline H3 gates as the earlier safety screens:

- progress loss budgets: `0.5 m`, `1.0 m`, `1.5 m`;
- H3 distance loss budgets: `0.05 m`, `0.1 m`;
- absolute H3 max lateral guard: `2.0 m/s^2`;
- a stricter variant requiring red stopping-margin nonworse.

The analyzer and tests remain shadow-only. Local verification passed with
`163 passed, 5 skipped`; AutoDL verification passed with `168 passed`.

The real sample59 non-formal v3 shadow artifact was re-analyzed at:

`/root/autodl-tmp/camp_dp_tracker_rollout_shadow_sample59_acba493`

| Artifact | SHA-256 |
| --- | --- |
| Underprogress budget JSON | `3c88376147313c2e5f11d9714aad5b7b98700b9c3fb127c1754150d8f5143474` |
| Underprogress budget markdown | `25dea17f0c7c4d4e13a374bcd02c1edc005fa50a49515aef3633274eadeb510a` |

The plain underprogress-relaxed budget table is:

| Progress loss | H3 distance loss | Covered | Union red | Progress | H3 distance | H3 vector jerk | H3 lateral |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 m | 0.05 m | 1/12 | -27.000000 | -0.466817 | -0.046299 | +6.785523 | +0.004925 |
| 0.5 m | 0.1 m | 1/12 | -27.000000 | -0.466817 | -0.046299 | +6.785523 | +0.004925 |
| 1.0 m | 0.05 m | 5/12 | -18.100000 | -0.648251 | -0.010429 | -7.320106 | -0.001820 |
| 1.0 m | 0.1 m | 5/12 | -18.100000 | -0.648251 | -0.010429 | -7.320106 | -0.001820 |
| 1.5 m | 0.05 m | 9/12 | -21.500000 | -0.919981 | -0.015352 | -14.333906 | -0.003701 |
| 1.5 m | 0.1 m | 10/12 | -22.650000 | -0.947520 | -0.021682 | -12.343982 | -0.003215 |

The stopping-margin-nonworse variant has the same coverage on this artifact,
with stronger stopping evidence:

| Progress loss | H3 distance loss | Covered | Union red | Stopping margin | Progress | H3 vector jerk |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 m | 0.05 m | 1/12 | -27.000000 | -18.761424 | -0.466817 | +6.785523 |
| 0.5 m | 0.1 m | 1/12 | -27.000000 | -18.761424 | -0.466817 | +6.785523 |
| 1.0 m | 0.05 m | 5/12 | -18.100000 | -16.339795 | -0.648251 | -7.320106 |
| 1.0 m | 0.1 m | 5/12 | -18.100000 | -16.339795 | -0.648251 | -7.320106 |
| 1.5 m | 0.05 m | 9/12 | -21.500000 | -20.681256 | -0.919981 | -14.333906 |
| 1.5 m | 0.1 m | 10/12 | -22.650000 | -21.207705 | -0.947520 | -12.343982 |

The remaining `2/12` events after ignoring `dp_underprogress` are hard-blocked:

| Case | Speed | Selected union-red | Lower candidates | Blocking reason |
| --- | ---: | ---: | ---: | --- |
| seed 2, npc 0, step 194 | 0.753574 m/s | 34.0 | 7 | all `dp_kinematic` |
| seed 2, npc 4, step 126 | 4.991127 m/s | 34.0 | 4 | all `dynamic_obb_collision` |

Decision: this is the first selector-adjacent screen with enough coverage to
justify a formal specification pass, but not enough to directly deploy. The
widest budget plus stopping-margin nonworse repairs `10/12` of the previously
unrepairable no-lower-feasible misses and improves union-red, stopping margin,
H3 jerk, and H3 lateral on average, with about `0.95 m` mean progress loss.
However, it relaxes an external DP progress gate and still has no
specification-backed command jerk cap. The next step is to update the
mathematical contract for a default-off, fail-closed, state-dependent
underprogress relaxation candidate set. It must preserve hard kinematic,
collision, road, lane, and red-light feasibility; use only current-tick
candidate constants; remain deterministic; and state explicitly that changing
the feasible set is outside the original CAMP convex master, while the CAMP
score over any admitted finite set remains affine in the fixed weights. Formal
seeds remain frozen.

### Default-off underprogress relaxation implementation

Commit `d10a18a916ea5eef4e6fcb73340138a1fc9daca3` implements the
underprogress relaxation as a default-off replay selector feature. It is not
enabled unless `--camp_underprogress_relaxation` is passed.

The implementation follows the mathematical contract:

- requires `--camp_feasibility_source dp_reward`;
- cannot be combined with the older lexicographic preselection or
  PerfectTracker command postselector;
- preserves hard feasibility reasons, including `dp_kinematic` and
  `dynamic_obb_collision`;
- admits only candidates whose sole blocker was exactly `dp_underprogress`;
- requires lower union-red, progress loss budget, H3 distance loss budget,
  red stopping-margin nonworse, and an absolute H3 max lateral limit;
- chooses by union-red, stopping margin, original CAMP score, then index;
- is fail-closed: if the admissible set is empty, the original CAMP selection
  remains unchanged.

The new CLI knobs are:

```text
--camp_underprogress_relaxation
--camp_underprogress_progress_loss_budget_m
--camp_underprogress_h3_distance_loss_budget_m
--camp_underprogress_lateral_limit_mps2
```

The benchmark matrix forwards these flags for non-Top1 variants. Replay
summary and validation files record `camp_underprogress_relaxation`; each
selection log record records `underprogress_relaxation` stats and the effective
feasible mask/reasons after relaxation. The summary latency aggregator now
tracks `underprogress_relaxation_latency_ms`.

Verification:

| Environment | Result |
| --- | --- |
| Local Windows, Python 3.12 | `166 passed, 5 skipped` |
| AutoDL, Python 3.9 | `171 passed` |

Decision: implementation gate is passed for a default-off pilot, not for
formal evaluation. The next allowed experiment is the predeclared paired
sample59 seeds `1/2/3` non-formal 12-run, using the current fixed DP commit
and frozen CAMP weights, comparing baseline `redstopfloor05` against the same
configuration with underprogress relaxation enabled. Formal seeds `11/12/13`
remain frozen.

### Underprogress relaxation H3 rollout access fix

The first AutoDL underprogress-relaxation pilot attempt after commit `06687c9`
failed before completing the first relaxation run:

```text
ValueError: Underprogress relaxation requires H3 rollout metrics.
```

The failure was a replay implementation bug, not a selector result. The
PerfectTracker open-loop diagnostic function returns horizon metrics under the
runtime structure `perfect_tracker_open_loop["horizons"]["3"]`, while the new
underprogress relaxation helper was reading only top-level horizon keys. The
selection log writer already used the nested `horizons` structure, so the
contract and stored artifact schema were unchanged.

The follow-up fix makes the helper read H3 metrics from the nested `horizons`
dictionary first, accepting both string and integer horizon keys, and keeps a
legacy top-level fallback for unit-level compatibility. The new tests cover:

- runtime-like nested string key `"horizons" -> "3"`;
- nested integer key `"horizons" -> 3`;
- legacy top-level `"3"`;
- hard-blocked candidates remaining infeasible.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_integration.py -k "underprogress_relaxation"
4 passed, 99 deselected

$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests
168 passed, 5 skipped
```

Decision: this restores the default-off pilot path to implementation-ready
status, but the previous failed relaxation roots must not be reused as evidence.
After syncing this fix to AutoDL, rerun remote tests and a short
underprogress-relaxation smoke before launching the remaining sample59 paired
12-run. The completed baseline root can still be reused because it finished
before the relaxation-side failure. Formal seeds remain frozen.

### Underprogress relaxation sample59 pilot result

Commit `259bc6031622ee55cba7d85668c4f99baadbf6ff` was synced to AutoDL. CAMP
was fast-forwarded to that commit and DP was rechecked at the fixed commit
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Remote verification:

```text
/root/miniconda3/envs/camp/bin/python -m pytest camp_core/tests
173 passed
```

A 2-step runtime smoke with `--camp_underprogress_relaxation` completed under:

```text
/root/autodl-tmp/camp_dp_underprogress_smoke_259bc60
```

The smoke confirmed that the H3 open-loop rollout metrics are available at
runtime and that `underprogress_relaxation_latency_ms` is recorded. The smoke
is not used as performance evidence.

The predeclared sample59 non-formal paired relaxation side was then run under:

```text
/root/autodl-tmp/camp_dp_underprogress_sample59_pilot_259bc60_relax
```

It completed all `12/12` runs. The strict paired comparison reused the already
completed baseline root:

```text
Baseline: /root/autodl-tmp/camp_dp_underprogress_sample59_pilot_9527721_base
Relaxed: /root/autodl-tmp/camp_dp_underprogress_sample59_pilot_259bc60_relax
Compare: /root/autodl-tmp/camp_dp_underprogress_sample59_pilot_259bc60_compare
```

| Artifact | SHA-256 |
| --- | --- |
| `paired_comparison.json` | `5c101a05074ec77a76a75d84f4e353ead692a16d1d7e7ccd5b101cc2d72efafb` |
| `paired_comparison.md` | `ca3510a9194cc70815de76ee167d9c7a2dd5ca96b36975f8fd9e26a2c0c81ef5` |

Strict pairing passed with `12` baseline runs and `12` relaxed runs. Aggregate
paired deltas for `underprogress_relaxation - redstopfloor05` were:

| Metric | Mean delta | 95% bootstrap CI |
| --- | ---: | ---: |
| Route completion rate | `-0.000018` | `[-0.000055, 0.000000]` |
| OBB collision rate | `0.000000` | `[0.000000, 0.000000]` |
| Near-miss rate | `0.000000` | `[0.000000, 0.000000]` |
| Lane-violation rate | `0.000000` | `[0.000000, 0.000000]` |
| Realized red-light violation rate | `0.000000` | `[0.000000, 0.000000]` |
| Planned red-light violation rate | `-0.002500` | `[-0.007500, 0.000000]` |
| Mean jerk magnitude | `+0.058318 m/s^3` | `[0.000000, +0.174955]` |
| Fallback rate | `0.000000` | `[0.000000, 0.000000]` |
| p95 selection latency | `-0.529243 ms` | `[-3.016653, +2.008160]` |

Only one run changed behavior: seed `2`, npc `0`, traffic lights on. It had
`8` changed ticks and `29` total admissible relaxed candidates. That run reduced
planned-red violation rate by `0.03`, but did not change realized red-light
violation rate, collision rate, near-miss rate, lane-violation rate, or fallback
rate. It reduced route completion by `0.000222` and increased mean jerk by
`0.699822 m/s^3`.

The aggregate p95 selection latency means were:

| Variant | Mean per-run p95 |
| --- | ---: |
| `redstopfloor05` | `102.635467 ms` |
| `underprogress_relaxation` | `102.106224 ms` |

Decision: reject promotion to 36-run. The pilot is strictly paired and
runtime-valid, but it does not satisfy the development gate: realized safety is
unchanged, planned-red improvement is small and localized, mean jerk regresses,
route completion weakly regresses, and average per-run p95 latency remains above
`100 ms` with no industrial margin. This does not invalidate the mathematical
contract for the finite-candidate relaxation, but it shows the current online
rule has insufficient useful coverage. Formal seeds `11/12/13` remain frozen.

Next diagnostic target: explain why most positive offline opportunities did not
translate into behavior. In particular, audit baseline-red-positive ticks where
the runtime stats reported `lower_red_base_feasible_candidate_exists`; the
current underprogress-only rule intentionally refuses those cases, so any
candidate-set safety override that handles them must be analyzed separately
with progress, H3 distance, stopping-margin, jerk, lateral, fallback, and latency
budgets before any new implementation.

### Base-feasible lower-red override diagnostic

The rejected underprogress pilot was audited for runtime ticks where the
underprogress helper reported `lower_red_base_feasible_candidate_exists`. These
are cases where the baseline selected candidate had positive union-red cost and
at least one lower-red candidate was already feasible under the normal DP reward
gates. They are not underprogress-relaxation opportunities; they would require a
separate base-feasible safety override.

Artifact root:

```text
/root/autodl-tmp/camp_dp_underprogress_sample59_pilot_259bc60_compare
```

| Artifact | SHA-256 |
| --- | --- |
| `base_feasible_safety_override_diagnosis.json` | `733849826ed6c2baf301614bd18e4456c4cf607943f121e1adb714473c387ae9` |
| `base_feasible_safety_override_diagnosis.md` | `c22206d88e1d2917b60417afe1beb618773281d7cedeef1189ebe11c6ccebdbc` |

Across the 2400 selection ticks, runtime underprogress reasons were:

| Reason | Count |
| --- | ---: |
| `baseline_union_red_zero` | 1884 |
| `fallback_or_no_base_feasible_candidate` | 484 |
| `lower_red_base_feasible_candidate_exists` | 22 |
| `underprogress_relaxed_lower_red_candidate` | 8 |
| `no_underprogress_relaxed_candidate` | 2 |

The 22 base-feasible lower-red opportunities were concentrated in only two
runs:

| Run | Events |
| --- | ---: |
| `sample59_86/seed_2/npc_0/spawn_0p3/tl_on/static` | 4 |
| `sample59_86/seed_2/npc_4/spawn_0p3/tl_on/static` | 18 |

Using the same budget family as the underprogress screen, with red
stopping-margin nonworse and absolute H3 max lateral `<= 2.0 m/s^2`, the
base-feasible candidate screen was:

| Progress loss | H3 distance loss | Covered | Union red | Progress | H3 distance | H3 mean jerk | H3 max jerk |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5 m | 0.05 m | 5/22 | -0.600000 | -0.419675 | -0.023867 | +0.489044 | -0.521638 |
| 0.5 m | 0.1 m | 6/22 | -0.583333 | -0.393493 | -0.034909 | +3.146894 | +3.167237 |
| 1.0 m | 0.05 m | 8/22 | -1.125000 | -0.536327 | -0.026273 | +0.947411 | +0.477641 |
| 1.0 m | 0.1 m | 9/22 | -1.111111 | -0.578932 | -0.043124 | +2.486502 | +1.084511 |
| 1.5 m | 0.05 m | 8/22 | -1.250000 | -0.595235 | -0.028835 | +1.531220 | +0.626101 |
| 1.5 m | 0.1 m | 11/22 | -1.636364 | -0.820927 | -0.058403 | +3.554947 | +4.480754 |

A pure diagnostic comfort-nonworse filter at the widest budget reduces coverage
substantially:

| Jerk guard | Covered | Union red | Progress | H3 mean jerk | H3 max jerk |
| --- | ---: | ---: | ---: | ---: | ---: |
| none | 11/22 | -1.636364 | -0.820927 | +3.554947 | +4.480754 |
| mean nonworse | 3/22 | -1.500000 | -0.892818 | -3.818584 | -6.418135 |
| max nonworse | 5/22 | -1.400000 | -0.887451 | -1.054926 | -6.363177 |
| mean and max nonworse | 3/22 | -1.500000 | -0.892818 | -3.818584 | -6.418135 |

Decision: do not implement a base-feasible safety override yet. The candidate
constants remain valid finite current-tick diagnostics, but the opportunity is
too localized, the red reduction is small, and the no-jerk-guard version has a
large H3 jerk regression. Adding a jerk-nonworse guard makes the screen more
comfortable but leaves only `3/22` to `5/22` covered events before any closed-loop
validation. This is not enough evidence to justify another online selector
variant. The next useful direction is not wider safety override logic; it is to
reduce latency overhead and improve the candidate generator or atom/safety
certificate so lower-red choices are available without paying progress and jerk
taxes. Formal seeds remain frozen.

### Rejected batch atom evaluation

Commit `412e248889a67624573921d86640592a33096687` replaced the per-candidate
base atom loop with a vectorized batch implementation. The implementation kept
the atom schema, weights, normalization, feasibility, collision checks, affine
score, and selector tie-break unchanged. Unit tests compared the batch result
against a stack of the original `compute_atom_bank_vector` calls with static and
candidate-specific dynamic obstacles.

Verification before the benchmark:

| Environment | Result |
| --- | --- |
| Local Windows, Python 3.12 | `169 passed, 5 skipped` |
| AutoDL, Python 3.9 | `174 passed` |

The batch implementation was evaluated on the same sample59 non-formal 12-run:

```text
Old vector root:
/root/autodl-tmp/camp_dp_underprogress_sample59_pilot_9527721_base

Batch atom root:
/root/autodl-tmp/camp_dp_batch_atom_sample59_412e248_base

Comparison root:
/root/autodl-tmp/camp_dp_batch_atom_sample59_412e248_compare
```

| Artifact | SHA-256 |
| --- | --- |
| `paired_comparison.json` | `19634d0f9dcc5b3caae3f3127e630d77a41b5dcf6ab3ef97daca68b2cf439583` |
| `paired_comparison.md` | `5168fafc821ddb68539c230fa073e86fd8aad9113a6eefd876ff8617db5ff85b` |

Strict pairing passed for all `12/12` runs. Across all 2400 selection records,
the following fields were exactly equal:

- selected index and fallback state;
- feasible mask and infeasibility reasons;
- raw atoms and normalized atoms;
- CAMP scores and selection scores;
- selection weights and selection normalized atoms.

All closed-loop paired deltas were exactly zero for route completion,
collision, near miss, lane violation, realized red-light violation, planned
red-light violation, jerk, and fallback. This confirms mathematical and
behavioral equivalence.

The performance result was negative:

| Mean per-run p95 | Old vector | Batch atom |
| --- | ---: | ---: |
| Total selection | `102.635467 ms` | `101.370465 ms` |
| Candidate generation | `63.497816 ms` | `60.867233 ms` |
| DP reward scoring | `23.643619 ms` | `21.116328 ms` |
| CAMP selection | `15.749189 ms` | `17.823681 ms` |
| CAMP atom computation | `13.142379 ms` | `16.038219 ms` |
| CAMP collision checks | `2.907745 ms` | `2.297451 ms` |

The lower total selection mean is explained by unrelated candidate-generation
and reward-scoring runtime variation. The controlled CAMP component regressed:
atom computation increased by about `2.90 ms` p95 and CAMP selection increased
by about `2.07 ms` p95. The batch implementation also increased code size and
temporary array allocation.

Decision: reject and revert the batch atom implementation. Commit `60604bf`
reverts `412e248`. The exact-equivalence result remains useful evidence, but
this implementation is not an industrial latency improvement and must not be
reintroduced without a different memory/layout design and a pre-implementation
microbenchmark. Formal seeds remain frozen.

## Predeclared component microbenchmark protocol

The next latency iteration uses an independent snapshot-and-replay
microbenchmark. It must not infer component improvements from total replay
runtime, candidate-generation variation, or subtraction between separate
closed-loop runs.

The fixed development inputs are:

- Diffusion Planner commit
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`;
- the frozen `redstopfloor05` CAMP checkpoint, atom scales, and K=8 selector;
- the non-formal `sample59_86` route only;
- seed 1, no NPCs, traffic lights off, and seed 2, maximum 4 NPCs, traffic
  lights on;
- perfect tracking, 40 replay steps, candidate noise 1.0, h30 DP-reward
  feasibility, and no closed-loop outcome labels;
- snapshots at completed selection steps 10, 20, 30, and 39 in each run.

Each snapshot must contain only current-tick finite data needed to replay the
measured functions: normalized DP model inputs, reward tensors, generated
candidates, candidate obstacle predictions, CAMP context, fixed selector
weights/scales, red-route points, and tracker state. Capturing snapshots is
default-off and has no selection effect. Snapshot-capture runs are diagnostic
only and are not latency evidence.

The independent replay reports these phases separately:

1. DP candidate generation, with fixed random seed and CUDA synchronization;
2. DP near-horizon reward and full-horizon red scoring;
3. the nine base CAMP atoms, decomposed into kinematics, jerk, acceleration,
   speed, centerline projection/lane hinge, dynamic clearance, and static
   clearance;
4. extra fixed candidate atoms and affine CAMP normalization/scoring/tie-break;
5. enabled audit quantities, including DP-prior comfort, lateral comfort,
   PerfectTracker command/open-loop rollout, full-red, and stopping margin.

For CPU phases, use 20 warmups and 100 measured repetitions per snapshot. For
GPU candidate generation and reward phases, use 10 warmups and 30 measured
repetitions per snapshot. Report per-snapshot median and p95, then the median
and p95 across snapshots. GPU timings must synchronize before and after every
measured call. The benchmark artifact must record command, environment,
snapshot hashes, fixed seeds, dimensions, and raw timing samples.

Before any online optimization is implemented:

- the decomposed atom implementation must reproduce the current raw atom
  vector within `rtol=1e-12`, `atol=1e-12`;
- repeated fixed-seed candidate generation and reward scoring must be
  deterministic within the upstream numeric contract;
- an optimization target must account for enough measured work to support an
  expected stable saving of at least `3 ms` at atom p95;
- the proposal must state expected saving, memory cost, and exact equivalence
  conditions.

Any later implementation must preserve raw/normalized atoms, feasibility
reasons, scores, fallback state, selected index, atom schema, fixed weights,
and deterministic tie-break. The finite current-tick atom values remain
nonnegative constants and the score remains affine in `w`; the simplex,
CVaR, and L2 master therefore remain convex. This diagnostic and any cache or
preprocessing optimization are not classical Benders decomposition, and no
global convexity in trajectory coordinates is claimed.

### Component microbenchmark result

Commits `f9baa9f3f9ccde4555338e66a67463b561524e09` and
`9e9adaa` add the default-off snapshot exporter and independent component
replay benchmark. Local verification passed with `172 passed, 5 skipped`;
AutoDL verification passed with `177 passed`.

The two predeclared 40-step capture runs produced eight current-tick snapshots
under:

```text
/root/autodl-tmp/camp_dp_component_microbenchmark_f9baa9f
```

The capture runs are not latency evidence. The separate snapshot replay used
the predeclared 20/100 CPU and 10/30 synchronized GPU protocol.

| Artifact | SHA-256 |
| --- | --- |
| `component_microbenchmark.json` | `124714b5475c7f33b5578ff6c7b2fb8e13fa6fb89ff0651579a107613822e918` |
| `component_microbenchmark.md` | `75da7797eab87b0942b017ae940cde1fd4f440cd56bf3febac374d18ffe3b409` |

All eight snapshots passed:

- raw base atom equality at `rtol=1e-12`, `atol=1e-12`;
- profiled implementation equality at the same tolerance;
- affine selection-score and selected-index equality;
- fixed-seed candidate generation repeat max error `0`;
- reward repeat max error `0`.

The attributable timing result is:

| Phase | Median of snapshot medians | p95 of snapshot p95 |
| --- | ---: | ---: |
| DP candidate generation | 55.796 ms | 63.294 ms |
| DP near-horizon reward | 9.451 ms | 13.134 ms |
| Current CAMP atom total | 11.443 ms | 16.111 ms |
| Centerline projection inside atoms | 10.317 ms | 13.331 ms |
| Centerline segment setup | 0.180 ms | 0.211 ms |
| Extra lateral atom | 0.306 ms | 0.363 ms |
| CAMP affine scoring | 0.003 ms | 0.003 ms |
| PerfectTracker open-loop audit | 0.969 ms | 1.003 ms |
| Red stopping-margin audit | 0.581 ms | 1.464 ms |

The centerline has 343 to 362 points while each tick contains 640 candidate
points. Centerline projection accounts for almost the entire atom cost.
Caching only segment setup cannot meet the 3 ms implementation gate because
that setup costs about 0.21 ms p95. The rejected all-candidate batch
implementation also remains rejected.

### Predeclared exact centerline-slice proposal

The next offline-only proposal keeps the original per-candidate projection
formula but computes an exact conservative contiguous centerline slice once per
tick.

For every candidate point `p`, exact distances to anchor segments spaced every
16 segments provide an upper bound `u(p)` on the nearest-segment distance. For
each centerline segment `j`, the Euclidean distance from `p` to the segment
axis-aligned bounding box is a lower bound `l(p,j)` on the true point-to-segment
distance. Segment `j` is potentially nearest only if

```text
l(p,j)^2 <= u(p)^2 + numeric_tolerance
```

for at least one candidate point. The retained polyline is the contiguous slice
from the minimum to maximum potentially-nearest segment index, inclusive.
Using a contiguous slice prevents artificial connections between disjoint
segments.

This pruning is exact: every true nearest segment has true distance no greater
than the anchor upper bound, while its AABB lower bound is no greater than its
true distance, so it cannot be removed. The implementation uses 64-segment
chunks for the lower-bound screen; at K=8, T=80 this keeps the largest temporary
matrix below 640 by 64 doubles, plus the anchor workspace. Expected temporary
memory is below 1 MB.

The proposal may enter online code only if the snapshot benchmark proves:

- raw 9-atom and full 14-atom equality at `rtol=1e-12`, `atol=1e-12`;
- normalized atoms, feasibility, scores, fallback, and selected index unchanged;
- preprocessing plus original projection on the retained slice saves at least
  3 ms at p95 relative to the current atom path;
- the retained slice is deterministic and fail-closed to the full centerline
  on invalid or degenerate input.

The slice depends only on the finite current-tick candidates and map
centerline. It does not change the atom definition, candidate set, weights,
master constraints, or tie-break. Therefore the CAMP score remains affine in
`w` and the existing simplex/CVaR/L2 master remains convex.

### Rejected AABB centerline-slice implementation

Commit `cfc21ed` evaluated the predeclared AABB lower-bound proposal on the
same eight snapshots. AutoDL verification passed with `178 passed`.

| Artifact | SHA-256 |
| --- | --- |
| `component_microbenchmark_slice_cfc21ed.json` | `a504b07b9d753709350bc69271be3c591148cff12d58564a3321027bf2848045` |
| `component_microbenchmark_slice_cfc21ed.md` | `eef7941a911aec247f6f8c64fc9cb8ed378eadb790d26be6f48f3cf6dbc17807` |

All eight snapshots had exact full-atom equality with maximum absolute error
`0`. The retained contiguous slices contained only 18 to 33 of the original
342 to 361 segments, or 5.3% to 9.6%.

The performance result failed the implementation gate:

| Phase | p95 of snapshot p95 |
| --- | ---: |
| Current atom total | 13.477 ms |
| Sliced atom evaluation after preprocessing | 2.709 ms |
| AABB exact-slice preprocessing | 10.572 ms |
| Preprocessing plus sliced atom total | 13.116 ms |

The AABB certificate moved the cost instead of removing it. Its net p95 saving
was about 0.36 ms, far below the required 3 ms. Decision: reject this
implementation and do not add it to the online selector.

### Predeclared midpoint KD-tree exact-slice proposal

The next offline-only proposal uses the existing `scipy>=1.10` dependency and
the same contiguous-slice output.

Build one KD-tree over centerline vertices and one over segment midpoints. For
each candidate point `p`, the nearest-vertex distance `u(p)` is an upper bound
on the nearest-segment distance. Let `h_max` be the largest segment
half-length. Query the midpoint tree with radius

```text
u(p) + h_max + numeric_tolerance.
```

This is exact. If segment `j` is truly nearest and `m_j` is its midpoint, then
for the closest point `q` on that segment,

```text
distance(p, m_j)
<= distance(p, q) + distance(q, m_j)
<= u(p) + half_length(j)
<= u(p) + h_max.
```

Therefore every true nearest segment is returned by the radius query. The
retained polyline is again the contiguous slice from the minimum to maximum
returned segment index, so no artificial segment is introduced.

The expected cost is two trees with about 350 points, 640 nearest/radius
queries, and no 640 by 350 dense matrix. Expected temporary memory is well
below 1 MB. Since the measured sliced atom cost is about 2.71 ms p95, this
proposal is eligible for offline measurement only if preprocessing is
expected to remain below about 7.7 ms; online acceptance still requires at
least 3 ms total p95 saving, exact full-atom equality, deterministic slice
indices, and fail-closed handling of invalid inputs.

### Accepted midpoint KD-tree microbenchmark

Commit `e2effae` evaluated the midpoint KD-tree certificate on the same eight
snapshots. AutoDL verification passed with `178 passed`.

| Artifact | SHA-256 |
| --- | --- |
| `component_microbenchmark_kdtree_e2effae.json` | `8c061966cffc56f0478640134977c4c88184be7ada12c1587b062baeb4e4b635` |
| `component_microbenchmark_kdtree_e2effae.md` | `2d5116d756db7e0001667be2a70a85be9a34348042223ae760e822a4eba19054` |

All eight snapshots again had exact full 14-atom equality with maximum absolute
error `0`. The KD-tree slices retained 18 to 23 of the original 342 to 361
segments, or 5.3% to 6.4%.

| Phase | p95 of snapshot p95 |
| --- | ---: |
| Current atom total | 14.914 ms |
| KD-tree exact-slice preprocessing | 0.963 ms |
| Sliced atom evaluation | 2.100 ms |
| Preprocessing plus sliced atom total | 3.044 ms |

The attributable expected p95 saving is about 11.87 ms, well above the 3 ms
implementation gate. Unlike the rejected all-candidate batch path, this keeps
the original per-candidate projection and only removes segments proven unable
to be nearest.

Decision: accept a minimal online implementation. The production helper must
be the same helper exercised by the benchmark, run once per selector tick, and
have its preprocessing time included in `latency_ms_camp_atom_computation`.
The selector must continue to use the original atom, feasibility, collision,
normalization, affine score, fallback, and tie-break logic. Before any paired
12-run, it must pass local and AutoDL full tests, a fixed-seed 40-step strict
selector-log comparison against the pre-optimization capture, and a short
latency smoke showing the expected atom reduction.

### Online smoke: rejected first wiring, accepted corrected wiring

Commit `21e72c6` first wired the exact KD-tree slice into `CAMPSelector`.
AutoDL passed `179` tests and both 40-step selector logs were strictly
equivalent to the pre-optimization captures. However, the online atom p95
remained `13.998 ms` and `13.695 ms`, so this wiring failed the latency gate.

The cause was attributable and local: when `candidate_obstacles` was present,
the per-candidate context was rebuilt from the original `context` instead of
the sliced `atom_context`. The replay always supplies that tensor, including
zero-filled no-NPC cases, so the optimized centerline was discarded before
atom evaluation. No 12-run was started from this rejected wiring.

Commit `bfdbb65` changes only that context base and adds a regression test that
observes the centerline passed to atom evaluation when candidate obstacles are
provided. It does not alter candidates, atom definitions, feasibility,
collision checks, normalization, weights, affine scoring, fallback, or
tie-breaking. The CAMP score therefore remains affine in `w`; the existing
simplex/CVaR/L2 master remains convex.

Verification:

- local: `174 passed, 5 skipped`;
- AutoDL: `179 passed`;
- CAMP local, GitHub, and AutoDL: `bfdbb657198525891834e550c7f82c727044ba19`;
- fixed DP: `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Corrected smoke root:

```text
/root/autodl-tmp/camp_dp_centerline_kdtree_smoke_bfdbb65
```

| Case | Total p95 | CAMP p95 | Atom p95 | Fallback | Collision | Near miss | Planned / realized red |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| seed 1, NPC 0, TL off | 85.409 ms | 4.772 ms | 3.271 ms | 0 | 0 | 0 | 0 / 0 |
| seed 2, NPC 4, TL on | 92.383 ms | 5.670 ms | 3.684 ms | 0 | 0 | 0 | 0 / 0 |

Both strict comparisons covered 40 records and had zero mismatches for
selected index, feasible mask, infeasibility reasons, fallback, atom schema,
atoms, normalized atoms, scores, and weights. All maximum absolute numeric
differences were `0`.

| Artifact | SHA-256 |
| --- | --- |
| `seed1_selector_equivalence.json` | `3b41f82ed77ad7190fb2537ea11f24276260ef4d6b0f3ada4833446dd1c88d6a` |
| `seed2_selector_equivalence.json` | `58e65f1704ad8e4ee66e445ff44cf8f6c9879ef70d1963f0f7687c3bcf268223` |
| `seed1_npc0_tloff/camp_validation_summary.json` | `22912aa8268a57be7908ee99005849354d8390aef541ece10bb0b4aa94241d3a` |
| `seed2_npc4_tlon/camp_validation_summary.json` | `a8b42c46dbe938c4d276f121e18603874ce592c7ed72c4c27f3ec233a2967953` |

Decision: the corrected implementation passes the strict-equivalence and
short-latency smoke gates. The next session may run the predeclared paired
sample59 12-run on seeds 1/2/3. Formal seeds 11/12/13 remain frozen, and no
36-run, schema change, or CAMP retraining is allowed until the paired 12-run
passes all safety, comfort, completion, fallback, and latency gates.

## Predeclared Sample59 Paired 12-Run

The migrated development state was re-audited before starting the paired run:

- CAMP local, GitHub, and AutoDL:
  `f9eedcdd1c9aa0c1a36f06548254d18fd00ea7b9`;
- fixed Diffusion Planner:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`;
- AutoDL full suite: `179 passed`;
- the four corrected-smoke artifact SHA-256 values above were independently
  reproduced;
- the baseline root contains exactly 12 validation summaries at
  `/root/autodl-tmp/camp_dp_underprogress_sample59_pilot_9527721_base`.

The mathematical audit distinguishes two objectives that must not be described
as identical. The paper and `camp_nonnegative_atom_weights.tex` present the
finite-candidate worst cost

```text
Q_i(w_i) = max_k w_i^T A_ik.
```

The current Diffusion Planner training path instead uses the robust ranking
loss

```text
max(0, margin_ik + (A_oracle - A_k)^T w).
```

Both are convex finite maxima of affine functions of `w`. The candidate affine
pieces therefore give globally valid cuts, and the existing nonnegative
simplex, Rockafellar-Uryasev CVaR epigraph, and L2-regularized master remain
convex. Training rejects nonfinite or negative atoms and requires the final
full finite-maximum gap to meet tolerance. The robust ranking master is a
separately defined finite-candidate cutting-plane formulation; it is not
claimed to be the paper's identical worst-cost objective.

This experiment changes neither formulation. The midpoint KD-tree helper only
removes centerline segments proven unable to be nearest while preserving the
original per-candidate projection. Strict equality of candidate atoms,
normalized atoms, feasibility, scores, weights, fallback, and selected index
therefore proves that the fixed candidate constants and selector optimization
problem are unchanged on the evaluated ticks. No new atom, checkpoint,
training, outcome label, or future-state input is introduced.

The 12-run matrix is fixed before execution:

| Parameter | Value |
| --- | --- |
| Route | `sample59_86` |
| Seeds | `1,2,3` |
| Maximum NPCs | `0,4` |
| Traffic lights | `off,on` |
| Spawn probability | `0.3` |
| Steps | `200` |
| Advance mode | `perfect` |
| Candidates | `8` |
| Candidate noise scale | `1.0` |
| CAMP variant | static `redstopfloor05` |
| Feasibility | DP reward, minimum progress ratio `0.8` |
| Reward horizon | `30` steps |
| All-infeasible fallback | `uniform` |

The new, non-overwriting output root is:

```text
/root/autodl-tmp/camp_dp_centerline_kdtree_sample59_f9eedcd
```

The exact 12-command dry-run was persisted before execution at:

```text
/root/autodl-tmp/camp_dp_centerline_kdtree_sample59_f9eedcd_predeclare.txt
```

Its SHA-256 is
`9d542a83e5b5df3ad85b3502bdb2b03c4ef5cbedb8053080f71aa0b12a851bfe`.

Acceptance is conjunctive:

1. all 12 selector logs and all 2,400 records pass strict equivalence with
   absolute and relative tolerances `1e-12`;
2. parsed closed-loop trajectory logs are exactly equal for every paired run;
3. safety, comfort, completion, and fallback metrics do not change;
4. every optimized-run p95 and the average per-run p95 are reported, with the
   average below `100 ms` and enough observed margin to justify a 36-run;
5. any behavioral mismatch or failed latency gate rejects expansion to the
   36-run.

Formal seeds 11/12/13 remain frozen. No schema change, CAMP retraining, or
Diffusion Planner modification is permitted during this gate.

### Sample59 paired 12-run result

The predeclared matrix completed sequentially at:

```text
/root/autodl-tmp/camp_dp_centerline_kdtree_sample59_f9eedcd
```

The strict selector audit paired all 12 logs and all 2,400 records. Every
discrete field and every numeric entry was exactly equal: selected index,
feasible mask, infeasibility reasons, fallback, atom schema, atoms, normalized
atoms, scores, and weights all had zero mismatches and maximum absolute and
relative differences of `0`.

The independent closed-loop audit also paired all 12 runs. Each of the
trajectory, clearance, metric, and evaluation-state logs contained 2,400
behavior records with zero numeric, type, key, length, or value mismatches and
maximum absolute difference `0`. The audit ignores only `png_dir`, a provenance
field whose absolute output root must differ between the baseline and new
artifact. The official replay comparison was strictly paired and all safety,
completion, comfort, feasibility, and fallback deltas were exactly `0`.

Per-run total and atom p95 values:

| Run | Baseline total | Optimized total | Delta | Optimized atom |
| --- | ---: | ---: | ---: | ---: |
| seed 1, NPC 0, TL off | 99.734 | 85.661 | -14.073 | 3.385 |
| seed 1, NPC 0, TL on | 103.390 | 92.078 | -11.312 | 3.487 |
| seed 1, NPC 4, TL off | 104.109 | 93.422 | -10.686 | 3.723 |
| seed 1, NPC 4, TL on | 107.212 | 94.719 | -12.492 | 3.992 |
| seed 2, NPC 0, TL off | 94.424 | 86.459 | -7.964 | 3.416 |
| seed 2, NPC 0, TL on | 101.970 | 86.837 | -15.133 | 3.180 |
| seed 2, NPC 4, TL off | 99.362 | 101.247 | +1.884 | 4.383 |
| seed 2, NPC 4, TL on | 109.090 | 99.572 | -9.518 | 4.083 |
| seed 3, NPC 0, TL off | 102.039 | 90.543 | -11.496 | 3.596 |
| seed 3, NPC 0, TL on | 98.242 | 90.902 | -7.340 | 3.589 |
| seed 3, NPC 4, TL off | 103.259 | 94.541 | -8.718 | 3.930 |
| seed 3, NPC 4, TL on | 108.795 | 94.571 | -14.224 | 3.921 |

The optimized mean per-run total p95 is `92.546 ms`, with fixed-seed 10,000
resample bootstrap interval `[89.944, 95.268] ms`. The mean and upper-bound
margins to the 100 ms budget are `7.454 ms` and `4.732 ms`. Mean total p95 fell
by `10.089 ms`; mean atom p95 is `3.724 ms` and fell by `9.419 ms`, providing
component-level attribution rather than a wall-clock-only claim.

One of 12 runs has total p95 above budget at `101.247 ms`. This does not fail
the predeclared aggregate gate, whose mean and bootstrap upper bound both
remain below budget, but it is retained as an explicit tail-latency risk for
the 36-run. It must not be hidden by aggregate reporting.

| Artifact | SHA-256 |
| --- | --- |
| Run log | `e8aa69a41ecdd43ecc1ea710f0cd1dab3a26f4cf29d2da84cb52711533a4e549` |
| Selector equivalence | `3313a6a62101201204616c1e56da804f460d0c064da8f8fef68616f6d01595af` |
| Paired comparison JSON | `b0a42d2f8f1b5dace3f7bb834a28a76b0b60713f56ba69ff8181863ce37ea199` |
| Paired comparison markdown | `ded994a260f24f0d331be877ec844dce6bcf3c343d243e5590980bddf41248f5` |
| Closed-loop exact equivalence | `97589e85c42c02b56e5446c939962334ae8b30f11ae9011953de63b910fe7897` |
| Latency gate JSON | `d7ac9c9d10fcab4befda980b8d7bd0d6ee071680e85c842baeacff6d4e559fae` |
| Latency gate markdown | `eb572d6523cd77ab611c4067d88fb7218755953f14efa3feb14e8a70b9377d95` |

Decision: pass the sample59 12-run optimization gate and proceed to the
predeclared non-formal 36-run. This accepts the exact runtime optimization, not
the overall CAMP industrial development gate.

### Predeclared exact-optimization 36-run

The next matrix keeps every selector and simulator parameter above and expands
only the route set to:

```text
sample59_86=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
sample2_104=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
nishishinjuku=/root/autodl-tmp/camp_dp_assets/nishishinjuku_release_auto_route.pkl
```

Together with seeds 1/2/3, NPC counts 0/4, and traffic lights off/on, this
produces 36 sequential 200-step runs. The independent output root is:

```text
/root/autodl-tmp/camp_dp_centerline_kdtree_full36_f9eedcd
```

The dry-run emitted exactly 36 commands at:

```text
/root/autodl-tmp/camp_dp_centerline_kdtree_full36_f9eedcd_predeclare.txt
```

Its SHA-256 is
`5ef38aafe059c844958c90dac40e02f385422f0e2587c830a750ca8331a98baa`.

Behavior is compared against the certified same-route `redstopfloor05` root:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263
```

That historical root predates the current diagnostic-only command, rollout,
and full-horizon red-light shadows. It is valid for selector and closed-loop
behavior equivalence, but not for direct total-latency attribution. Latency is
therefore judged from the new sequential root itself, while the current
sample59 paired run supplies before/after component attribution.

The 36-run gate requires:

1. strict equality for 36 selector logs and 7,200 records;
2. exact trajectory, clearance, metric, and evaluation-state equality, again
   ignoring only the output-root provenance field `png_dir`;
3. zero paired deltas for safety, completion, comfort, feasibility, and
   fallback;
4. all 36 total p95 values, the count above 100 ms, and the maximum reported;
5. mean per-run p95 and its fixed-seed bootstrap upper bound below 100 ms.

Any behavioral mismatch or failed latency condition rejects the optimization.
Formal seeds 11/12/13 remain frozen. A passing optimization gate does not by
itself authorize schema changes or CAMP retraining; the remaining industrial
safety and comfort evidence must be reassessed first.

### Rejected historical 36-run control and replacement

The optimized 36-run completed all scenarios with exit status `0`, but the
first strict comparison rejected the historical control assumption above.
Against
`camp_dp_development_perfect_v10_redstopfloor05_e70f263`, the 7,200-record
comparison found 44 selected-index mismatches, 31 feasible-mask mismatches,
and 7,064 records with different atoms.

The mismatch is attributable to code-path age, not to the exact centerline
optimization. Route-level audits found:

| Historical comparison | Records | Atom-record mismatches | Selected-index mismatches |
| --- | ---: | ---: | ---: |
| `sample59_86` | 2,400 | 2,364 | 21 |
| `sample2_104` | 2,400 | 2,328 | 1 |
| `nishishinjuku` | 2,400 | 2,372 | 22 |

In contrast, the `sample59_86` subset of this same optimized full matrix is
strictly identical to the recent current-chain baseline: all 12 logs and 2,400
records have zero selected, feasible, atom, score, weight, and fallback
differences. The old full36 root therefore cannot isolate the optimization and
is rejected as its behavior control. It remains historical performance
evidence only.

| Diagnostic artifact | SHA-256 |
| --- | --- |
| Historical `sample59_86` selector comparison | `339775ad7b6caf9dc5939a1c883bc141dec3c2503499361bb9ce220132615144` |
| Historical `sample2_104` selector comparison | `5eb2f05c33a762c45b47840699ebdf3a947a7cdb659509a31464990bcb097f8f` |
| Historical `nishishinjuku` selector comparison | `607fe4b8519326feda68be85e0c79a96c3c7dd665deb874fb7f7561d8ff61e4c` |
| Current-chain `sample59_86` equivalence | `6b53123541fd403774b80da5f144288bb9f8412a256dfdb8be7e11d256aca7f3` |

The replacement control is CAMP commit
`21e72c627a6379812045fa8fe76bd8aec99186f6` in the isolated worktree:

```text
/root/autodl-tmp/camp_core_fullcenterline_21e72c6
```

Relative to the accepted implementation, its only runtime code difference is
the context used when `candidate_obstacles` is supplied:

```text
21e72c6: replace(context, dynamic_obstacles=dynamic)
accepted: replace(atom_context, dynamic_obstacles=dynamic)
```

The DP replay supplies `candidate_obstacles` on every selector tick, including
zero-filled no-NPC cases. Consequently `21e72c6` computes the same current
candidate set, reward gates, shadows, atoms, scores, weights, fallback, and
tie-break while intentionally discarding the sliced centerline and evaluating
the original full centerline. It is the current-chain full-centerline control,
not a different selector design. The isolated worktree passes `179` tests.

The replacement 36-run keeps the exact matrix above and writes to:

```text
/root/autodl-tmp/camp_dp_fullcenterline_full36_21e72c6
```

Its 36-command dry-run is:

```text
/root/autodl-tmp/camp_dp_fullcenterline_full36_21e72c6_predeclare.txt
```

with SHA-256
`e052ab104e103ed1e6fbfcd6c71fc1fff7c4db812710bda2a6d3d267401a742d`.

The replacement comparison must satisfy the original strict 7,200-record and
closed-loop equality gates. Because both sides now contain the same diagnostic
phases, it also supplies a direct paired total- and component-latency
attribution. No result from the rejected historical control may be used to
accept or reject the optimization.

### Accepted exact-optimization 36-run result

The replacement full-centerline control and optimized matrix both completed
36/36 sequential runs with exit status `0`.

The strict selector audit paired 36 logs and 7,200 records. Every discrete and
numeric field was exactly equal, including selected index, feasible mask,
infeasibility reasons, fallback, atom schema, atoms, normalized atoms, scores,
and weights. All mismatch counts and maximum absolute and relative differences
were `0`.

The closed-loop audit paired all 36 runs and found exact equality for 7,200
trajectory, clearance, metric, and evaluation-state records in each log type.
It again ignored only the output-root provenance field `png_dir`. The official
paired comparison found zero deltas for completion, collision, near miss, lane
violation, planned and realized red light, jerk, lateral acceleration,
feasibility, and fallback.

Direct same-chain latency results:

| Quantity | Full centerline | Exact slice | Paired delta |
| --- | ---: | ---: | ---: |
| Mean per-run total p95 | 91.783 ms | 88.667 ms | -3.116 ms |
| Mean atom p95 | 8.124 ms | 3.796 ms | -4.327 ms |

The paired total-p95 bootstrap interval is `[-4.931, -1.375] ms`; the paired
atom-p95 interval is `[-5.721, -3.059] ms`. The optimized total-p95 interval is
`[87.416, 89.934] ms`, leaving `10.066 ms` to the 100 ms budget at its upper
bound. All 36 optimized runs are below 100 ms; the maximum is `95.923 ms`.
The complete per-run table is persisted in `fullcenterline_latency_gate.md`.

| Route | Mean optimized total p95 | 95% bootstrap interval | Runs >= 100 ms |
| --- | ---: | ---: | ---: |
| `sample59_86` | 89.374 ms | [87.252, 91.439] | 0/12 |
| `sample2_104` | 88.716 ms | [86.849, 90.594] | 0/12 |
| `nishishinjuku` | 87.911 ms | [85.692, 90.235] | 0/12 |

Current-chain Static behavior, unchanged by the optimization:

| Metric | Mean across 36 runs |
| --- | ---: |
| Route completion | 0.299770 |
| OBB collision | 0.000000 |
| Near miss | 0.028889 |
| Lane violation | 0.045694 |
| Realized red light | 0.006421 |
| Planned red light | 0.024167 |
| Mean jerk magnitude | 20.402821 m/s^3 |
| Mean lateral acceleration | 0.338062 m/s^2 |
| Fallback | 0.166806 |

| Artifact | SHA-256 |
| --- | --- |
| Optimized run log | `f09897c288436fb2df75d5128ae194553c5513dfb9b6e713184b2c8d02c027db` |
| Full-centerline run log | `3dd9a0a264005e640e4d2a5bf4195cb5c0abb9be6ca0f5983840c179d8c0e84d` |
| Selector equivalence | `87a75563ce1e54aa3e63a246df4dc420224aefbba82a309826e64ce295dfa930` |
| Paired comparison JSON | `7c6012802eea7f193f71cb77fbab196d84ab3ca6cf472477a39629d60989b3c6` |
| Paired comparison markdown | `836f245519f3693a94139ed7a14083e36299efe314b8624a65bf459f55bf1c3f` |
| Closed-loop exact equivalence | `50737bcf72b90c8a196ae6ed123ea7f399323b99919f852d473240b60c2f5116` |
| Latency gate JSON | `142f81f2190e5b7a010f41dd60dc3ab1a20e21e357474ac6608885ea734d9ebd` |
| Latency gate markdown | `cc639c3f445a3198956999d75270c89342e196cd2203aec90946dbe11e36d470` |

Decision: accept the midpoint KD-tree contiguous centerline slice as an
industrial runtime optimization. Exact equality proves that it does not alter
the finite candidate constants, affine score, simplex weights, feasibility,
fallback, or selected trajectory. The existing robust finite-maximum master,
CVaR epigraph, simplex constraints, and L2 regularization are mathematically
unchanged. This result does not establish that the current `redstopfloor05`
weights meet the overall industrial safety and comfort gate.

### Predeclared current-chain Top-1 decision matrix

A same-chain Top-1 matrix is required before deciding whether to freeze the
current CAMP checkpoint or version the atom schema and retrain. Historical
Top-1 results are close enough to be informative but are not a valid strict
control after the code-path drift identified above.

The current CAMP main commit is
`1ecbc834e98874e0a5111865e7a11386d0148d13`; Diffusion Planner remains fixed
at `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The matrix uses the same three
routes, seeds 1/2/3, NPC counts 0/4, traffic lights off/on, 200 steps, and
perfect tracking. Its output root is:

```text
/root/autodl-tmp/dp_top1_currentchain_full36_1ecbc83
```

The 36-command dry-run is:

```text
/root/autodl-tmp/dp_top1_currentchain_full36_1ecbc83_predeclare.txt
```

with SHA-256
`0af729a3238c5025a3bafc1168ab1c5657f3dd32319a9ff73bc3714bcf699115`.

The comparison against the accepted optimized Static root is diagnostic but
conjunctive for formal readiness:

1. strict pairing must include all 36 scenario keys;
2. CAMP completion noninferiority requires the paired completion CI lower
   bound to be nonnegative;
3. collision, near miss, lane violation, planned and realized red light, mean
   jerk, and mean lateral acceleration noninferiority each require the paired
   CAMP-minus-Top-1 CI upper bound to be nonpositive;
4. a positive lower bound for any safety or comfort regression establishes
   the need for a new offline design rather than formal seeds;
5. inconclusive intervals do not establish readiness.

If this gate fails, formal seeds remain frozen. The next step is not an
unconstrained weight rerun: first audit execution-aligned, current-tick,
finite, nonnegative candidate quantities such as fixed-horizon
PerfectTracker rollout jerk and lateral acceleration. Any promoted atom must
be versioned and outcome-free online; for fixed candidates its value is a
constant, so the CAMP score remains affine in `w` and the simplex/CVaR/L2
finite-maximum master remains convex. No convexity claim is made in trajectory
coordinates.

### Current-chain Top-1 result

The predeclared Top-1 matrix completed 36/36 runs with exit status `0`. Strict
pairing found 36 common and union keys with no missing or duplicate runs.

| CAMP minus Top-1 | Mean delta | 95% bootstrap interval | Decision |
| --- | ---: | ---: | --- |
| Route completion | +0.012005 | [+0.008387, +0.015885] | pass |
| OBB collision | 0.000000 | [0.000000, 0.000000] | pass |
| Near miss | +0.000417 | [-0.015000, +0.012222] | inconclusive |
| Lane violation | +0.001389 | [-0.000972, +0.004583] | inconclusive |
| Planned red light | +0.012222 | [-0.001944, +0.035139] | inconclusive |
| Realized red light | +0.006142 | [0.000000, +0.018425] | inconclusive |
| Mean jerk magnitude | +12.040183 m/s^3 | [+10.223277, +13.910016] | established regression |
| Mean lateral acceleration | +0.045649 m/s^2 | [+0.029342, +0.065299] | established regression |

The current checkpoint is not formal-ready. It provides a clear completion
gain and preserves zero OBB collision, but jerk and lateral acceleration are
strictly worse than Top-1. The four other safety intervals do not establish
noninferiority. Formal seeds 11/12/13 remain frozen.

| Artifact | SHA-256 |
| --- | --- |
| Top-1 run log | `1e85dec79379fba40e18205bebfd75b6e7dd3f7e0baf68a20306eab8dfd09c1e` |
| Current-chain Top-1 comparison JSON | `e58d6d2f0bbc1758f5532688dd49c317ad96b1063d1d3e5c2a58a41a48306eb6` |
| Current-chain Top-1 comparison markdown | `fb2f2d0b682e593d4a09dca66ad67ad0669c3b38e7c717778b623222b0be9cb6` |
| Top-1 decision gate | `feb65202e89f0644ea071fb564aacf0a9dd8699b92ab6d4df9e30ebe5f73769b` |

The outcome-free full36 rollout screen also rejects another narrow
postselector. Among 5,999 non-fallback records, an H3 candidate that preserved
red, progress, and rollout distance while strictly improving rollout comfort
existed on only 85 records (`1.42%`). H3 command-to-rollout correlations were
`0.697` for jerk and `0.923` for lateral acceleration, so the fields are
meaningful diagnostics, but the free Pareto coverage is too small to repair
the aggregate Top-1 comfort gap by a local dominance rule.

| Artifact | SHA-256 |
| --- | --- |
| Full36 rollout shadow analysis JSON | `81df77292c05724b0272ffc28a9b5c12d4c9f89a0c1acb7fddcb6544658dcc37` |
| Full36 rollout shadow analysis markdown | `c837f4194779a3fe577ed629358845d60f3543e47f3bfa9123399f1faa87d8d3` |

### Predeclared rollout-to-outcome atom screen

Commit `209bdfcc0d8f38934fa88786c854d3b630fcbdee` adds only an offline
rollout-to-outcome alignment analyzer and fail-closed tests. It does not change
the online selector, atom schema, weights, or Diffusion Planner. Local
verification passed `177` tests with `5` environment-dependent skips; AutoDL
passed all `182` tests.

No existing artifact contains both the current H3/H5/H10 PerfectTracker
rollout shadows and candidate closed-loop outcomes, and older outcome logs do
not persist candidate trajectories. The minimum new collection is therefore
the 12-run sample59 development matrix:

```text
/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc
```

It keeps the accepted Static selector, seeds 1/2/3, NPC counts 0/4, traffic
lights off/on, K=8, perfect tracking, and 200 steps. The only added operation
is diagnostic 30-step candidate outcome collection with the existing outcome
weights. Its 12-command dry-run is:

```text
/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc_predeclare.txt
```

with SHA-256
`7cc26d147e4e9cd7a0c387ed0ae88b77dc2ab8a4ab41797d60a085168834cae3`.

The collection must preserve the accepted Static selected index, atoms,
feasibility, weights, fallback, and closed-loop trajectory. Outcome collection
is label generation only and must have no selection effect.

For jerk and lateral separately, the fixed horizons H3, H5, and H10 are
evaluated without tuning. A horizon is ineligible if availability is below
100%, any value is nonfinite or negative, feasible-record variation is below
90%, feasible Top-1-gap correlation is nonpositive, or feasible pairwise
ordering is below 0.5. Among eligible horizons, select the largest feasible
Top-1-gap Pearson correlation; differences within `0.02` are broken by larger
pairwise ordering agreement, then by the shorter horizon.

Schema promotion requires the selected rollout feature to exceed the best
corresponding existing proxy on both feasible Top-1-gap correlation and
feasible pairwise ordering agreement. Otherwise reject the new atom. Passing
this sample screen authorizes a non-formal 36-run outcome collection and
schema-v11 training design, not online deployment.

The rollout values are current-tick, fixed-candidate, finite, and nonnegative;
candidate outcomes are used only as offline labels. If promoted, each atom is
a constant for each finite candidate, so `w^T A_k` remains affine in `w` and
the finite-maximum, simplex, CVaR, and L2 master remains convex. No outcome is
available to online inference, and no convexity claim is made in trajectory
coordinates.

### Sample59 rollout-to-outcome result

The predeclared collection completed 12/12 runs with exit status `0`: 2,400
records, 19,200 candidates, and 484 fallback records. Candidate-outcome
logging preserved the accepted Static chain exactly. The selected index,
atoms, feasibility, weights, reasons, fallback state, and all four closed-loop
log streams had zero differences against the accepted sample59 subset.

| Target and feature | Feasible candidate Pearson | Feasible Top-1-gap Pearson | Feasible pairwise agreement | Oracle match |
| --- | ---: | ---: | ---: | ---: |
| Jerk, existing `dp_prior_jerk_excess` | 0.2053 | 0.8780 | 1.0000 | 0.0809 |
| Jerk, rollout H3 | 0.2406 | 0.0231 | 0.5498 | 0.2495 |
| Jerk, rollout H5 | 0.2511 | 0.0224 | 0.5507 | 0.2469 |
| Jerk, rollout H10 | 0.2590 | 0.0481 | 0.5532 | 0.2495 |
| Lateral, existing horizon feature | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Lateral, rollout H3 | 0.6926 | 0.3846 | 0.6640 | 0.3826 |
| Lateral, rollout H5 | 0.7300 | 0.4559 | 0.6885 | 0.4275 |
| Lateral, rollout H10 | 0.8295 | 0.6088 | 0.7137 | 0.4734 |

All evaluated rollout quantities had 100% availability, were finite and
nonnegative, and varied on 97.13% of feasible records. H10 is the best rollout
horizon for both targets under the predeclared ranking, but it does not exceed
the corresponding existing proxy on both required promotion metrics.

The reported pairwise agreement skips tied pairs. Excess-style existing
features therefore can show perfect agreement over comparable pairs while
having low oracle match because many candidates are tied at zero. This limits
the interpretation of pairwise agreement in isolation, but does not change
the rejection: the rollout features are also substantially worse on the
predeclared Top-1-gap metric.

Decision: reject rollout atom promotion, do not collect the 36-run outcome
matrix, and do not create schema v11. The evidence points to weight,
lower-bound, active-cut, or label-sensitivity behavior in the existing robust
master rather than a missing execution-aligned comfort atom. The next
development step is a read-only audit of the current redstopfloor05 asset and
the previously rejected lateral lower-bound and outcome-weight experiments
before predeclaring any new convex weight intervention.

| Artifact | SHA-256 |
| --- | --- |
| Predeclare | `7cc26d147e4e9cd7a0c387ed0ae88b77dc2ab8a4ab41797d60a085168834cae3` |
| Run log | `c4d1eec91dcee946210214c638cbb6264e889dff297c4958b9dd8a4b736779b9` |
| Selector equivalence | `e6549ae683971cfa41170642a3c3dfb597c1a5219f8cf81604fb8c3cd01c2292` |
| Closed-loop exact equivalence | `e520a863529d555e55265e236de2244ac92455bea1aa5f6ef68957c7ba4207e7` |
| Dataset audit | `f3fdf5029cd6edfec909f689405ce47831ffef00ec11c4d8ebf77b5ea5b09ff4` |
| Alignment JSON | `4eb770f202acca793505a69f002130349894332d3d0437432febcecf93e1119e` |
| Alignment markdown | `2a9b61e406fe79c1149cacd42cf8c41bcbf50e863e6a1888423819df7a7e35fa` |

### Migration sync and redstopfloor05 asset audit

After session migration, the local checkout was fast-forwarded from
`f9eedcdd1c9aa0c1a36f06548254d18fd00ea7b9` to
`2b67d33b465b406d1581fb4ac90e0f0c57ab8a18`. GitHub `origin/main` and AutoDL
`/root/autodl-tmp/camp_core` were verified at the same commit. The fixed
Diffusion Planner checkout remained
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Existing untracked files were left
untouched.

The current redstopfloor05 asset is:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263
```

It is a static `dp_camp_v10_14d` checkpoint trained on 5,979 feasible-ranking
records from 7,200 input records, with 1,221 all-infeasible records dropped
from the master. The master settings were CVaR alpha `0.9`, margin scale `0.1`,
margin clip `2.0`, L2 `1e-4`, CLARABEL, tolerance `1e-6`, max 20 cutting-plane
iterations, train-group-only scale fitting, and scale percentile 95. It
converged in four iterations with final master gap `0.0`, 7,111 active finite
cuts, and cut-count histogram `{1: 2899, 2: 1652, 3: 280, 4: 17}` over the
4,848 train records. The complete epigraph audit passed with saved-minus-full
objective `-5.16e-12`, weight \(L_\infty\) distance `1.23e-10`, saved CVaR
`0.110257`, and `full_worst_unique=8`.

The deployed weights and scales are:

| Atom | Scale | Weight |
| --- | ---: | ---: |
| `jerk_early` | 758.944720 | 0.410287 |
| `jerk_late` | 4577.087790 | 0.000000 |
| `jerk_full` | 5119.924473 | 0.000000 |
| `rms_acceleration` | 1.674076 | 0.000000 |
| `speed_limit_margin_0_0` | 2.036647 | 0.000630 |
| `speed_limit_margin_0_5` | 7.440118 | 0.000000 |
| `speed_limit_margin_1_0` | 16.833999 | 0.000000 |
| `lane_deviation` | 0.000001 | 0.000000 |
| `clearance` | 0.000001 | 0.000369 |
| `progress_shortfall` | 2.121215 | 0.479370 |
| `planned_red_light_cost` | 0.000001 | 0.000000 |
| `planned_lateral_acceleration_cost` | 1.017984 | 0.000000 |
| `red_stopping_margin_cost` | 0.000001 | 0.050000 |
| `dp_prior_jerk_excess_cost` | 0.711169 | 0.059344 |

Only `red_stopping_margin_cost >= 0.05` is an active lower bound. The
outcome-label weights were progress `2.0`, collision `100.0`, near miss `10.0`,
lane violation `20.0`, red light `30.0`, mean jerk `1.0`, and mean lateral
acceleration `2.0`. Train oracle match was `0.8806`; validation oracle match
was `0.9045`. Train CVaR was `0.110257`; validation CVaR was `0.078911`.

The prior lateral and label-sensitivity evidence rules out two easy fixes:

1. the comfort-reweighted `j1_lat2` and `j2_lat4` checkpoints improved selected
   comfort atoms but paid for it with lower completion, higher fallback or
   near-miss pressure, and larger DP-prior deviation;
2. `redstop05_latfloor02`, adding
   `planned_lateral_acceleration_cost >= 0.02`, changed only 0.32% of
   fixed-candidate selections and gave negligible lateral-atom improvement;
3. increasing the red-light outcome weight to 50 was inactive for the robust
   master and reproduced the same deployed weights as `progress2_j1_lat2`.

The pairwise metric was also made more explicit. The rollout-to-outcome
analyzer now reports comparable-pair coverage in addition to pairwise ordering
agreement, because tied pairs are skipped by the agreement statistic. Recomputing
the sample59 outcome screen with this diagnostic gave:

| Feature | Pair agreement | Pair coverage | Top-1-gap Pearson |
| --- | ---: | ---: | ---: |
| `dp_prior_jerk_excess` | 1.000000 | 0.705301 | 0.877957 |
| `horizon_lateral_acceleration` | 1.000000 | 1.000000 | 1.000000 |
| `dp_prior_lateral_acceleration_excess` | 1.000000 | 0.726683 | 0.860880 |
| `rollout_h10_mean_vector_jerk_mps3` | 0.553248 | 1.000000 | 0.048137 |
| `rollout_h10_mean_lateral_acceleration_mps2` | 0.713702 | 1.000000 | 0.608798 |

This strengthens rather than weakens the prior rejection. The existing jerk
and lateral proxies are not merely artifacts of skipped tied pairs: the
existing lateral horizon feature is exactly aligned with the lateral label, and
the existing jerk-excess feature has strong Top-1-gap alignment despite only
70.53% comparable-pair coverage. The deployed comfort regression is therefore
not explained by missing rollout atoms. The more likely failure modes are:

1. `planned_lateral_acceleration_cost` is outcome-aligned but has effectively
   zero deployed weight;
2. `dp_prior_jerk_excess_cost` is weighted, but the Top-1 comparison still
   shows a large jerk gap, so the active robust cuts and progress/red tradeoff
   allow comfort loss;
3. simple static lower bounds on the current lateral atom already failed;
4. the candidate pool rarely contains a lower-comfort alternative that preserves
   progress, red, and jerk, consistent with the previous candidate-pool screen.

Decision: do not train new CAMP weights, do not run a new 12/36 matrix, and do
not revive schema v11 or rollout atoms. The next admissible step is a
predeclared, offline-only sensitivity screen that keeps the existing schema and
fixed DP, and tests whether a convex intervention has a nontrivial mechanism
without repeating `planned_lateral_acceleration_cost >= 0.02`. Any proposed
intervention must state its feasible set, nonemptiness proof, fixed grid,
acceptance gate, and why it is not the rejected tiny lateral floor.

| Artifact | SHA-256 |
| --- | --- |
| redstopfloor05 atom scales | `a50d6d5b26888bdc0d2715dbfce525d3725697fa6e6565b6dd7ae9e8dd105b15` |
| redstopfloor05 weights | `dbfe8333c8a2f7944710003d1bcf39fda84626b9c5728c80bddf6f5d41be81b1` |
| redstopfloor05 training summary | `b6ced7c71240e9c8b3d1c6c47470ea7411069edeb48825d24ec2f8f693951e32` |
| redstopfloor05 full epigraph audit | `12733885d22a50308b52ec6090af49f6ab973300a33394b140a24e5776b3c0c3` |
| redstopfloor05 outcome weights | `9df61a4fbeeba3908113aedabf06fed1c92f0737613ccf9da93399902fa52425` |
| pair-coverage alignment JSON | `c8efdb4e3ea56f6d7f437d0113dc9984fc7a68c11d4a0b25fb6819df0d823565` |
| pair-coverage alignment markdown | `b88646437b134c87e11f603e4281d1f6bca26431fed728c24cdbf8556b453188` |

Local verification on the migrated Windows machine:

```text
python -m pytest camp_core/tests
178 passed, 5 skipped

python scripts/integrations/analyze_diffusion_planner_rollout_outcome_alignment.py --help
passed
```

Plain `python -m pytest` over the repository was not a valid local gate on this
machine because collection enters `adaptive-prediction` tests that require
uninstalled `torch`, `trajectron`, and separate test-package import layout. The
DP/CAMP integration test scope above is the relevant local gate for this
milestone.

### Predeclared static weight-transfer sensitivity

The next screen is offline-only and uses the existing
`/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc` candidate-outcome
logs. It does not train CAMP, does not run a simulator matrix, does not alter
Diffusion Planner, and does not change the online selector. It answers a
narrow diagnostic question: if the current redstopfloor05 weight vector is
held inside the same convex simplex/lower-bound feasible set but small mass is
transferred from `progress_shortfall` to existing comfort atoms, is there a
nontrivial fixed-candidate mechanism before spending another training or
simulation run?

For the deployed weight vector \(w^0\), each screened vector is

\[
w = w^0 - \sum_j \epsilon_j e_{\text{progress\_shortfall}}
        + \sum_j \epsilon_j e_{a_j}.
\]

The fixed grid is:

| Variant | Transfer |
| --- | --- |
| `baseline_redstopfloor05` | none |
| `progress_to_lateral_0p01` | `progress_shortfall -> planned_lateral_acceleration_cost`: 0.01 |
| `progress_to_lateral_0p03` | `progress_shortfall -> planned_lateral_acceleration_cost`: 0.03 |
| `progress_to_lateral_0p05` | `progress_shortfall -> planned_lateral_acceleration_cost`: 0.05 |
| `progress_to_jerk_0p02` | `progress_shortfall -> dp_prior_jerk_excess_cost`: 0.02 |
| `progress_to_jerk_0p05` | `progress_shortfall -> dp_prior_jerk_excess_cost`: 0.05 |
| `progress_to_lateral_0p02_jerk_0p02` | 0.02 to lateral and 0.02 to jerk-excess |
| `progress_to_lateral_0p03_jerk_0p03` | 0.03 to lateral and 0.03 to jerk-excess |

Nonemptiness and convexity: the current `progress_shortfall` weight is
`0.479370`, so the largest total transfer `0.06` keeps all weights
nonnegative. The sum of weights remains one, and the active
`red_stopping_margin_cost >= 0.05` lower bound is unchanged. Thus every
screened \(w\) lies in the same static convex feasible set. For the fixed
finite candidate set, every atom value is a current-tick nonnegative constant,
so each score remains affine in \(w\). No claim is made about convexity in
trajectory coordinates, and this is not a Benders procedure.

The screen retains the baseline selected index for all-infeasible/fallback
records and rescored only records with at least one base-feasible candidate.
For each variant it reports selection change rate, outcome-label deltas
against the baseline selected candidate, key atom deltas, simplex checks, and
lower-bound preservation.

Acceptance for mechanism only, not deployment:

1. reject a variant immediately if it violates simplex, nonnegativity, or the
   red-stopping lower bound;
2. reject as inactive if nonfallback selection change rate is below 1%;
3. reject as repeating the tiny lateral-floor failure if it changes selections
   but gives negligible lateral-label improvement, defined here as mean
   lateral delta above `-0.002 m/s^2`;
4. reject as progress/safety tradeoff if mean progress delta is below
   `-0.001 m`, or if red, collision, near-miss, or lane-violation deltas are
   positive;
5. only if a variant passes these offline diagnostics may a later milestone
   predeclare an actual convex lower-bound or robust-master solve. Passing this
   screen alone does not authorize online deployment, a 12/36-run matrix, or
   formal seeds.

### Static weight-transfer sensitivity result

Commit `002a1522c7a24e33353d4745460b2c1524be50d5` implements the predeclared
offline analyzer and fail-closed tests. Local verification passed:

```text
python -m pytest camp_core/tests
181 passed, 5 skipped
```

AutoDL was fast-forwarded to the same commit, with Diffusion Planner still at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Remote verification passed:

```text
/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
186 passed
```

The predeclared offline screen was run on:

```text
/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc
```

It used 12 logs, 2,400 records, 1,916 nonfallback records, and retained the
baseline selected index for 484 fallback records. Results:

| Variant | Changed records | Nonfallback change rate | Progress delta | Red delta | Jerk delta | Lateral delta | Value delta | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `progress_to_lateral_0p01` | 20 | 0.010438 | -0.001330 | 0.000000 | -0.003312 | -0.000163 | -0.000339 | reject: progress and negligible lateral |
| `progress_to_lateral_0p03` | 48 | 0.025052 | -0.003581 | 0.000000 | -0.009231 | -0.000786 | -0.000487 | reject: progress and negligible lateral |
| `progress_to_lateral_0p05` | 73 | 0.038100 | -0.005608 | 0.000000 | -0.015747 | -0.001014 | -0.000657 | reject: progress and negligible lateral |
| `progress_to_jerk_0p02` | 85 | 0.044363 | -0.007406 | 0.000000 | -0.016717 | -0.000897 | -0.002329 | reject: progress/value tradeoff |
| `progress_to_jerk_0p05` | 179 | 0.093424 | -0.018176 | 0.000000 | -0.033580 | -0.001826 | -0.007955 | reject: progress/value tradeoff |
| `progress_to_lateral_0p02_jerk_0p02` | 114 | 0.059499 | -0.009519 | 0.000000 | -0.021670 | -0.001134 | -0.002968 | reject: progress/value tradeoff |
| `progress_to_lateral_0p03_jerk_0p03` | 154 | 0.080376 | -0.014167 | 0.000000 | -0.031285 | -0.001604 | -0.004742 | reject: progress/value tradeoff |

Decision: reject all screened static transfers before any robust-master solve,
new training, or simulator matrix. The variants prove a mechanism exists in
the sense that small comfort mass transfers change selected candidates, but
the improvement is not industrially useful: the lateral-label deltas remain
below the predeclared `-0.002 m/s^2` threshold, and every nontrivial variant
pays progress and utility. This is consistent with the earlier candidate-pool
and lateral-floor conclusions: the current K=8 candidate set rarely offers a
free comfort improvement that preserves progress. The next step should not be
another static lower bound on `planned_lateral_acceleration_cost` or a simple
progress-to-comfort transfer.

The remaining evidence-backed options are:

1. diagnose whether a progress-normalized comfort metric can separate genuine
   comfort waste from necessary progress tradeoff without using outcome labels
   online;
2. audit candidate generation/DP sampling diversity while keeping the official
   DP weights fixed;
3. revisit the robust label construction only if it can encode progress
   preservation explicitly rather than merely increasing comfort penalties.

Formal seeds remain frozen.

| Artifact | SHA-256 |
| --- | --- |
| Static weight-transfer sensitivity JSON | `dadeff089920a2e784875868cfc397beeec1bb008df15e9064558053869b5d47` |
| Static weight-transfer sensitivity markdown | `05f41351558ae00ba3d9c5894f87f3aaf42e9ee0ab54cc44e2143a3af683f05c` |

### Predeclared progress-normalized comfort diagnostic

The next screen remains offline-only and uses the same existing
`/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc` candidate-outcome
logs. It does not train CAMP, does not run a simulator matrix, does not alter
Diffusion Planner, and does not change the online selector. The diagnostic
tests whether current-tick progress-normalized comfort metrics can separate
genuine comfort waste from comfort improvements that necessarily buy lower
progress.

For each nonfallback record, define the fail-closed admissible set

\[
D_{\Delta p} = \{k: k\text{ is base-feasible},
q_k \le q_b + \Delta p,
u_k \le u_b,
s_k \le s_b\},
\]

where \(b\) is the baseline selected index, \(q_k\) is the raw
`progress_shortfall` atom, \(u_k\) is
`candidate_horizon_union_planned_red_light_cost`, and \(s_k\) is
`candidate_red_stopping_margin_cost`. The selected baseline is always retained,
so \(D_{\Delta p}\) is nonempty. Fallback records retain the baseline index.

The fixed extra-shortfall budgets are `0.0`, `0.05`, `0.10`, and `0.25 m`.
The fixed diagnostic metrics are:

1. `candidate_horizon_lateral_acceleration_cost`;
2. `candidate_dp_prior_jerk_excess_cost`;
3. lateral cost multiplied by `(1 + progress_shortfall)`;
4. jerk-excess cost multiplied by `(1 + progress_shortfall)`.

Each screen chooses the admissible candidate with the smallest diagnostic
metric, then original CAMP score, then candidate index. Outcomes are used only
afterward for offline evaluation. The report must include changed records,
opportunity records, progress/red/jerk/lateral/value deltas, and current-tick
diagnostic deltas.

Mathematical scope: all quantities used by the screen are fixed-current-tick
candidate constants and are nonnegative. If any diagnostic were later promoted
as an atom with fixed scales, the candidate score would remain affine in
\(w\) over the simplex/CVaR/L2 master. This screen itself is not a Benders
procedure and makes no convexity claim over trajectory coordinates.

Acceptance for a future intervention is deliberately strict:

1. reject if nonfallback change rate is below 1%;
2. reject if mean progress delta is below `-0.001 m`;
3. reject if red-light, collision, near-miss, or lane-violation deltas are
   positive;
4. reject if both mean jerk and mean lateral deltas fail to improve by at least
   `-0.002` in their native units;
5. passing this diagnostic only authorizes a later predeclared atom or master
   design. It does not authorize deployment, 12/36-run matrices, DP retraining,
   or formal seeds.

### Progress-normalized comfort diagnostic result

Commits `a56271530c6b57cfd890e1664ac5ff2d16023420`,
`a75425240685e1e00ee39334b9ab0f6f90c4f2d0`,
`00586507e2f51b6bb9eeeefc61a335bc35154ab1`, and
`32ec34f0bad1580d5d08785027432e8915ac36ee` implement the predeclared
diagnostic and adapt it to the actual sample59 outcome logs:

- `candidate_route_progress` is absent in this artifact, so the diagnostic uses
  the raw `progress_shortfall` atom, which is the current v10 master progress
  certificate;
- `selection_scores` may include masked infinities for infeasible candidates,
  so score tie-breaking requires non-NaN values rather than finite nonnegative
  values.

Local verification passed:

```text
python -m pytest camp_core/tests
184 passed, 5 skipped
```

AutoDL was synchronized by git bundle because GitHub HTTPS timed out from the
remote host. Remote verification passed:

```text
/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
189 passed
```

The diagnostic ran on the existing sample59 outcome root:

```text
/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc
```

It used 12 logs, 2,400 records, 1,916 nonfallback records, and retained 484
fallback records.

| Metric | Extra shortfall budget | Changed | Progress delta | Red delta | Jerk delta | Lateral delta | Value delta | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `horizon_lateral` | 0.00 | 92 | +0.002004 | 0.000000 | +0.011250 | -0.000309 | -0.000499 | reject: negligible lateral, jerk worse |
| `jerk_excess` | 0.00 | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | reject: inactive |
| `horizon_lateral_progress_normalized` | 0.00 | 416 | +0.213529 | 0.000000 | +0.133792 | +0.005741 | +0.174341 | reject: comfort worse |
| `jerk_excess_progress_normalized` | 0.00 | 2 | +0.000141 | 0.000000 | +0.000521 | +0.000035 | -0.000024 | reject: inactive and comfort worse |
| `horizon_lateral` | 0.05 | 359 | -0.002543 | 0.000000 | +0.015978 | -0.000859 | -0.005679 | reject: progress loss and jerk worse |
| `jerk_excess` | 0.05 | 82 | -0.001045 | 0.000000 | -0.001711 | -0.000035 | -0.000582 | reject: progress loss and weak comfort |
| `horizon_lateral_progress_normalized` | 0.05 | 472 | +0.212917 | 0.000000 | +0.133900 | +0.005632 | +0.173810 | reject: comfort worse |
| `jerk_excess_progress_normalized` | 0.05 | 83 | -0.000887 | 0.000000 | -0.001189 | +0.000002 | -0.000591 | reject: weak comfort |
| `horizon_lateral` | 0.10 | 612 | -0.014045 | 0.000000 | +0.014938 | -0.001909 | -0.015871 | reject: progress loss and jerk worse |
| `jerk_excess` | 0.10 | 175 | -0.004211 | 0.000000 | -0.005769 | -0.000189 | -0.002580 | reject: progress loss |
| `horizon_lateral_progress_normalized` | 0.10 | 479 | +0.212715 | 0.000000 | +0.133957 | +0.005606 | +0.173619 | reject: comfort worse |
| `jerk_excess_progress_normalized` | 0.10 | 176 | -0.004054 | 0.000000 | -0.005248 | -0.000152 | -0.002589 | reject: progress loss |
| `horizon_lateral` | 0.25 | 1173 | -0.074688 | 0.000000 | +0.002212 | -0.005717 | -0.069523 | reject: large progress/value loss |
| `jerk_excess` | 0.25 | 456 | -0.026458 | 0.000000 | -0.024986 | -0.000887 | -0.019324 | reject: progress/value loss |
| `horizon_lateral_progress_normalized` | 0.25 | 480 | +0.212662 | 0.000000 | +0.133939 | +0.005603 | +0.173574 | reject: comfort worse |
| `jerk_excess_progress_normalized` | 0.25 | 441 | -0.025040 | 0.000000 | -0.024267 | -0.000831 | -0.018142 | reject: progress/value loss |

Decision: reject the progress-normalized comfort diagnostic as a basis for a
new atom, lower bound, master solve, online selector, or simulator matrix.
The result confirms the current diagnosis rather than opening a new route:
when progress-shortfall is held tight, comfort gains are negligible or coupled
to jerk degradation; when the shortfall budget is widened, the improvement is
paid for with progress and utility. The multiplicative shortfall-normalized
metrics are especially poor: the lateral-normalized metric prefers high
progress but worsens both jerk and lateral comfort.

The next evidence-backed direction is not another score reweighting or
progress-normalized comfort atom. The remaining plausible bottleneck is
candidate availability/diversity under the fixed official DP checkpoint: audit
whether the K=8 sampled candidates contain Pareto-improving branches often
enough, and whether the lack of such branches is tied to sampling variance,
route context, red-light context, or fallback/infeasible records. Formal seeds
remain frozen.

| Artifact | SHA-256 |
| --- | --- |
| Progress-shortfall comfort diagnostic JSON | `d6fa03cd972ec9becf2283226b5ef57b5d4f8f99cd513be4fb6d4f347f3b982b` |
| Progress-shortfall comfort diagnostic markdown | `c76fd53faaa2334c802b5c690159751387b04f70fa4ea2aa79446b75d365b451` |

### Predeclared K=8 candidate availability audit

The next step is an offline outcome-labeled audit of the fixed official DP
K=8 candidate pool. It does not change DP, CAMP weights, atom schema, online
selection, or simulator execution, and it does not use formal seeds. It asks
whether the existing candidate set frequently contains a branch that is already
Pareto-better than the selected candidate under stored candidate outcomes, and
whether current-tick proxies can see those branches.

For each nonfallback record and progress budget
\(\Delta p \in \{0.0, 0.05, 0.10, 0.25\}\), an outcome-level weak Pareto branch
is a base-feasible candidate \(k\ne b\) such that:

1. candidate outcome progress is at least selected progress minus \(\Delta p\);
2. collision, near miss, lane violation, and red-light violation are no worse
   than the selected candidate;
3. outcome jerk and outcome lateral acceleration are both no worse;
4. at least one of outcome jerk or outcome lateral acceleration is strictly
   better.

A joint-strict branch requires both outcome jerk and outcome lateral
acceleration to be strictly better. Candidate outcomes are offline labels only.

The proxy-side audit uses only fixed-current-tick nonnegative candidate
quantities: raw `progress_shortfall`, `candidate_horizon_union_planned_red_light_cost`,
`candidate_red_stopping_margin_cost`, `candidate_dp_prior_jerk_excess_cost`,
and `candidate_horizon_lateral_acceleration_cost`. A proxy weak branch is
defined analogously with progress-shortfall within \(\Delta p\), union-red and
red-stopping nonworse, jerk-excess and horizon-lateral nonworse, and at least
one proxy comfort quantity strictly better.

The report must include:

1. outcome weak and joint-strict branch coverage;
2. proxy weak and joint-strict branch coverage;
3. hidden outcome opportunities, where outcome-level Pareto branches exist but
   proxy branches do not;
4. proxy-only opportunities, where current-tick proxies suggest a branch but
   outcome labels do not;
5. candidate diversity ranges for progress, jerk, and lateral labels and
   proxies.

Interpretation gate:

1. if outcome weak coverage is low under tight progress budgets, the bottleneck
   is candidate availability rather than scoring;
2. if hidden outcome opportunities are high, the bottleneck is proxy/atom
   visibility;
3. if proxy-only opportunities are high, proxy comfort screens are unsafe as
   deployment criteria;
4. this audit alone authorizes no online selector, no new atom, no CAMP
   training, no 12/36-run matrix, and no formal seeds.

### K=8 candidate availability audit result

Commit `aba3c60955107a7ba155ddfdf51611747427a625` implements the predeclared
offline availability audit and fail-closed tests. Local verification passed:

```text
python -m pytest camp_core/tests
187 passed, 5 skipped
```

AutoDL was synchronized to the same commit by git bundle after SSH/GitHub
network timeout on the combined command path. Remote verification passed:

```text
/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
192 passed
```

The audit ran on:

```text
/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc
```

It used 12 logs, 2,400 records, 1,916 nonfallback records, and 484 fallback
records.

| Progress budget | Outcome weak | Outcome joint | Proxy weak | Proxy joint | Hidden outcome | Proxy-only | Best progress delta | Best jerk delta | Best lateral delta |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.00 | 2 (0.001044) | 2 (0.001044) | 20 (0.010438) | 0 (0.000000) | 1 (0.000522) | 19 (0.009916) | +0.553410 | -0.028853 | -0.003473 |
| 0.05 | 122 (0.063674) | 122 (0.063674) | 226 (0.117954) | 63 (0.032881) | 4 (0.002088) | 108 (0.056367) | -0.024222 | -0.070607 | -0.003303 |
| 0.10 | 288 (0.150313) | 288 (0.150313) | 456 (0.237996) | 138 (0.072025) | 7 (0.003653) | 175 (0.091336) | -0.057630 | -0.092975 | -0.006385 |
| 0.25 | 737 (0.384656) | 737 (0.384656) | 1020 (0.532359) | 381 (0.198852) | 16 (0.008351) | 299 (0.156054) | -0.148112 | -0.150935 | -0.012449 |

Diversity summary:

| Quantity | Mean range |
| --- | ---: |
| Feasible candidates | 7.467119 |
| Outcome jerk | 0.740269 |
| Outcome lateral | 0.044491 |
| Proxy jerk-excess | 0.400723 |
| Proxy horizon-lateral | 0.044491 |

Decision: the K=8 candidate set is the active comfort bottleneck under tight
progress preservation. With zero progress loss, only `2/1916` nonfallback
records have an outcome-level branch that preserves safety/progress and
strictly improves both jerk and lateral. Hidden outcome opportunities are
negligible (`1/1916` at zero budget and `16/1916` at 0.25 m), so the failure is
not primarily that current atoms/proxies are blind to many good branches.
Proxy-only opportunities are much more common than hidden outcome
opportunities, which means a proxy-only selector or atom screen would often
chase branches that do not satisfy the offline outcome Pareto definition.

This result supports the previous rejection chain: weight transfer, small
lateral lower bounds, progress-normalized comfort, and postselection rules are
not the main path forward. The next evidence-backed route is candidate
generation/diversity under the fixed official DP checkpoint: predeclare a
non-formal diagnostic that changes only candidate sampling configuration or
candidate count, with no DP weight changes and no formal seeds, then first
measure whether tight-progress outcome Pareto availability increases enough
and whether latency remains below the deployable budget before any closed-loop
matrix is considered.

| Artifact | SHA-256 |
| --- | --- |
| K=8 candidate availability JSON | `d4376188ff0c6f3e6ed77cb45c4b6c4ccfd837250e60953e27dba5801075742d` |
| K=8 candidate availability markdown | `2f096be7edc44b6eb09d124e749b507900a8cc5c0b21e28dbfd49475c56d4659` |

### Predeclared K16/noise availability comparison gate

This milestone does not train CAMP, does not alter Diffusion Planner weights,
does not change the default online selector, and does not use formal seeds. It
adds a comparison gate for future offline outcome-labeled candidate-generation
diagnostics against the accepted K=8 availability baseline above.

The fixed development grid is:

| Label | Candidate count | Noise scale | Purpose |
| --- | ---: | ---: | --- |
| `k16_noise1p0` | 16 | 1.0 | isolate candidate count under the official DP sampler |
| `k16_noise0p75` | 16 | 0.75 | diagnose whether a denser, lower-variance pool increases tight-progress availability |

The `k16_noise0p75` row does not revive the rejected K=8 `noise0p75`
closed-loop route. It is only an offline availability diagnostic. Passing it
would still require a separate no-outcome latency smoke and a new paired pilot
predeclaration before any closed-loop claim.

For each row, the collection must keep the official DP checkpoint, the frozen
`redstopfloor05` static weights and atom scales, `sample59_86`, seeds `1/2/3`,
NPC counts `0/4`, traffic lights `off/on`, perfect tracking, 200 steps,
DP-reward feasibility, h30 reward horizon, and the existing outcome-label
weights. Candidate outcomes remain offline labels only. Formal seeds `11/12/13`
remain frozen.

The comparison uses the existing K=8 baseline report:

```text
/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc/k8_candidate_availability_aba3c60.json
```

and the new diagnostic comparator:

```text
python scripts/integrations/compare_diffusion_planner_candidate_availability.py \
  --baseline_json /root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc/k8_candidate_availability_aba3c60.json \
  --candidate_json k16_noise1p0=/path/to/k16_noise1p0_candidate_availability.json \
  --candidate_json k16_noise0p75=/path/to/k16_noise0p75_candidate_availability.json \
  --output_json /path/to/k16_candidate_availability_comparison.json \
  --output_md /path/to/k16_candidate_availability_comparison.md
```

Default gate thresholds are intentionally strict because K=9/10/12 random
candidate-count expansion already failed deployable latency or supplied too few
progress-preserving opportunities:

1. at `0.00 m` progress budget, candidate outcome-joint coverage must be at
   least `0.02` and improve over K=8 by at least `0.015`;
2. at `0.05 m` progress budget, candidate outcome-joint coverage must be at
   least `0.15` and improve over K=8 by at least `0.08`;
3. mean feasible-candidate count must increase by at least `2.0`;
4. hidden-outcome weak coverage at `0.00 m` and `0.05 m` must remain no higher
   than `0.05`, otherwise the result points back to atom/proxy visibility;
5. proxy-only weak coverage must remain no higher than `0.10` at `0.00 m` and
   `0.20` at `0.05 m`, otherwise proxy-only screening is too unreliable;
6. latency is not evaluated by this report. A passing availability comparison
   only advances the row to a separate no-outcome latency smoke; it does not
   authorize CAMP retraining, formal seeds, online selector changes, or a
   12/36-run acceptance matrix.

Mathematical status: the diagnostic changes only the finite candidate set
sampled by the fixed DP checkpoint. For every fixed current tick and candidate,
the CAMP atoms remain finite, nonnegative, and outcome-free, and the score
remains affine in the static weight vector. The simplex, CVaR, L2, and
finite-maximum master terms therefore retain their convexity for any later
weight intervention. No convexity claim is made in trajectory coordinates, and
the candidate generator itself is not a Benders subproblem.

Implementation verification for the comparator milestone:

```text
python -m pytest camp_core/tests/test_diffusion_planner_candidate_availability.py camp_core/tests/test_diffusion_planner_candidate_availability_compare.py
6 passed

python -m pytest camp_core/tests
190 passed, 5 skipped

python scripts/integrations/compare_diffusion_planner_candidate_availability.py --help
```

AutoDL verification after fast-forward to the comparator milestone:

```text
/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests/test_diffusion_planner_candidate_availability.py camp_core/tests/test_diffusion_planner_candidate_availability_compare.py
6 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
195 passed
```

A real-artifact parsing smoke compared the K=8 baseline report against itself:

```text
/root/autodl-tmp/dp312_venv/bin/python scripts/integrations/compare_diffusion_planner_candidate_availability.py \
  --baseline_json /root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc/k8_candidate_availability_aba3c60.json \
  --candidate_json k8_self=/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc/k8_candidate_availability_aba3c60.json \
  --output_json /tmp/k8_candidate_availability_self_compare.json \
  --output_md /tmp/k8_candidate_availability_self_compare.md
```

The self-compare correctly failed the availability and candidate-pool gates
because it has zero improvement over the K=8 baseline.

| Artifact | SHA-256 |
| --- | --- |
| Candidate availability comparator | `d4eedd37fba27feefd5fab453b157a2f695ea43d3841300061f71399739d312c` |
| Comparator tests | `e1cea47f605d40d9a68c61099e6d62653c99301d55e19c0c396986cfabf8e95a` |
| K=8 self-compare JSON | `9aa688ee9aa94f0059f112a1b77ab33d883335d3665295ee8fc7a7a22370b47d` |
| K=8 self-compare markdown | `13b29cc5a7f8a40d0c2eecfe0dc9b06fc7951d40cdf476472aa8f981bde99e71` |

### K16/noise availability result

The predeclared K16/noise diagnostic grid completed on AutoDL at CAMP commit
`2212309f7523e96fc64462e57a87f2f4b942d818`, with Diffusion Planner still fixed
at `7a1d33da277a1992ec474b5383a0c963c72e04e4`. Both rows used
`--model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json`,
which is required because the public `.pth` file does not carry its parameter
JSON next to the checkpoint under the default `args.json` name.

Output roots:

```text
/root/autodl-tmp/camp_dp_candidate_availability_k16_noise1p0_2212309
/root/autodl-tmp/camp_dp_candidate_availability_k16_noise0p75_2212309
```

Both dataset audits passed with 12 logs, 2,400 records, 16 candidates, perfect
tracking, required candidate outcomes, required h30 comfort shadows, required
open-loop rollout and full-horizon red-light shadows, and formal seeds
`11/12/13` absent.

| Candidate | Nonfallback | Fallback | Mean feasible candidates | Joint@0.00 | Delta@0.00 | Joint@0.05 | Delta@0.05 | Hidden@0.05 | Proxy-only@0.05 | Gate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| K=8 baseline | 1,916 | 484 | 7.467119 | 0.001044 | n/a | 0.063674 | n/a | 0.002088 | 0.056367 | baseline |
| `k16_noise1p0` | 1,791 | 609 | 14.672250 | 0.006142 | +0.005098 | 0.074260 | +0.010586 | 0.010050 | 0.062535 | reject: availability |
| `k16_noise0p75` | 1,887 | 513 | 14.889242 | 0.002650 | +0.001606 | 0.118177 | +0.054503 | 0.007419 | 0.087970 | reject: availability |

Decision: reject both K16 rows before latency smoke, closed-loop acceptance
matrices, CAMP retraining, or formal seeds. Both rows pass the candidate-pool
gate by increasing mean feasible candidates by more than 7, and both pass the
proxy-reliability gate under the predeclared thresholds. They fail the primary
availability gate: zero-progress outcome-joint coverage remains far below
`0.02`, and the `0.05 m` progress-budget deltas remain below the required
`+0.08`. The `k16_noise0p75` row improves the `0.05 m` budget more than
`k16_noise1p0`, but it still does not supply enough tight-progress comfort
alternatives to justify a deployability/latency campaign.

This closes the simple K16/noise branch. The evidence now points away from
larger random candidate count or lower diffusion noise as an industrial path
under the current fixed DP sampler. The next candidate-generation idea must
change candidate structure more deliberately, or it should be rejected before
simulation if it cannot state why it avoids the same tight-progress availability
failure.

| Artifact | SHA-256 |
| --- | --- |
| `k16_noise1p0` predeclare commands | `568b3ca9c96031a4cbc88fc378f1ee591ff3e12f3ace7971f29e39b5cf66a59b` |
| `k16_noise1p0` run log | `0b88455d9f3b86e2f6261b3dbff5c29f217f781c6028e9d9341cadf679190cd3` |
| `k16_noise1p0` dataset audit | `928f4c8ba009b5acfe74aea8da90c106bc9e51ab8c690748365a9bd1ad889468` |
| `k16_noise1p0` availability JSON | `2f69001717f88ebafe62a83d009dab59b289160fb23ee3b209b6c0500ebcf517` |
| `k16_noise1p0` availability markdown | `e07d08201f929a5c04f6c6a0696f7e410f8053687c5a768f85ad48801c27c212` |
| `k16_noise0p75` predeclare commands | `5cb402fede83206c3654a746b755d56e52ed5873baf526c886db653ef355d5d8` |
| `k16_noise0p75` run log | `077e29054a4f1aa95caa99a0f7e5a2453332f4842fcc1676db79f5511928afbb` |
| `k16_noise0p75` dataset audit | `01cab550b2020674d5ce1030bf9c9fd87068feca9fae753facadcc605dac6292` |
| `k16_noise0p75` availability JSON | `86ad50e868c510a4771c3145629eebb5d311e1c6577ed5314b5b72812ee33287` |
| `k16_noise0p75` availability markdown | `290841da70976c0c6f9f89234adb7cc6dadaf6bdab83afa142bd8f4efd8ca5e4` |
| Combined K16 comparison JSON | `93055fb33fdb292980248ba3743e59c196488ddebcf3bac03c3b6b7417e0eefb` |
| Combined K16 comparison markdown | `29a25da34d6f0fa133ef03054485bb9e977118e5559469f2698c0a8e2d4dde36` |

### Candidate availability blocker audit

Commit `0c0688ff18f10eecfb923231c4bbb95ff1e9e81d` adds an offline blocker audit
for existing outcome-labeled candidate logs. The audit does not change the
online selector, CAMP weights, DP weights, atom schema, or simulator behavior.
It decomposes the failed outcome-joint availability gate into:

1. whether any feasible alternative exists;
2. whether any alternative strictly improves both outcome jerk and outcome
   lateral acceleration;
3. whether that joint-comfort alternative is safety-nonworse;
4. the minimum progress deficit needed to use a safety-preserving joint-comfort
   candidate.

The analyzer was verified locally and on AutoDL:

```text
python -m pytest camp_core/tests
193 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
198 passed
```

It was then run on the existing K=8 baseline and both K16/noise diagnostic
roots. Summary:

| Candidate set | Joint-comfort records | Safety-preserving joint-comfort records | Min progress deficit mean | P50 | P90 | Joint@0.00 | Joint@0.05 | Progress-blocked among failed@0.05 | Safety-blocked among failed@0.05 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 1,314/1,916 (0.685804) | 1,314/1,916 (0.685804) | 0.292355 m | 0.218676 m | 0.615692 m | 2 (0.001044) | 122 (0.063674) | 1,192/1,794 (0.664437) | 0 |
| `k16_noise1p0` | 1,355/1,791 (0.756561) | 1,355/1,791 (0.756561) | 1.252943 m | 0.207944 m | 0.620154 m | 11 (0.006142) | 133 (0.074260) | 1,222/1,658 (0.737033) | 0 |
| `k16_noise0p75` | 1,447/1,887 (0.766826) | 1,447/1,887 (0.766826) | 0.510523 m | 0.152702 m | 0.452525 m | 5 (0.002650) | 223 (0.118177) | 1,224/1,664 (0.735577) | 0 |

Interpretation:

1. Safety is not the active blocker in these sample59 outcome logs. Every
   joint-comfort candidate was also safety-preserving under the audited boolean
   outcome labels, and safety-blocked records were zero at all audited budgets.
2. K16 increases the frequency and count of joint-comfort candidates, but those
   candidates mostly sit behind progress loss. At the `0.05 m` progress budget,
   progress still blocks `66.44%` of failed K=8 records, `73.70%` of failed
   `k16_noise1p0` records, and `73.56%` of failed `k16_noise0p75` records.
3. Lower noise (`k16_noise0p75`) improves the `0.05 m` availability relative to
   K=8, but not enough to pass the predeclared gate, and it still leaves a
   progress-deficit median of `0.152702 m` for safety-preserving joint-comfort
   alternatives.
4. The next useful candidate-generation route must be progress-preserving by
   construction, not merely larger or lower-variance. Because prior
   prefix-blend and step-reach screens were rejected, any new structured
   candidate transform must first give a formal finite-candidate definition and
   a cheap offline proof that it can reduce progress deficit without repeating
   those rejected transforms.

Decision: do not run latency smoke, a paired matrix, CAMP retraining, or formal
seeds from K16/noise. The blocker evidence rejects simple random candidate
expansion and lower-noise sampling as sufficient industrial interventions.

| Artifact | SHA-256 |
| --- | --- |
| Blocker analyzer | `6b5df112a5d8e662bcd727c9d095455d49241d9412e2138bc1839e78f3e214ba` |
| Blocker analyzer tests | `098e406aac1e924d948099572b2ef74569254f17bb3217d67531086172419eb9` |
| K=8 blocker JSON | `86c8da13d1416d55d1431254e3eb6d7da1dcb0a77934dc52d07fb8ec39c5ceaf` |
| K=8 blocker markdown | `e70bfbcaab2622b3c64180d50f6f3a3420bc58c95dcf20d573121e7841611a20` |
| `k16_noise1p0` blocker JSON | `48704a358e4f61467a3c703f779d4b99f24ed633ec14d3a36f482e9381d53a11` |
| `k16_noise1p0` blocker markdown | `305964e17ff844c8cfd9885b3249eb3d1d09521e90eb9eb790a744d06d5ec3f0` |
| `k16_noise0p75` blocker JSON | `62cbcbe2af56b0d2d755902ea0a78b549fd8ca3748df7f1944b131580c551db4` |
| `k16_noise0p75` blocker markdown | `7dc4fe4616535361b8583eeb6a94dc249f766e201ed48e428fd70ba73c0e917c` |

### Progress-deficit attribution audit

Commit `254bceed816ef6b3a216b5b155f4697526c2092a` adds a narrower attribution
audit for the safety-preserving joint-comfort candidates identified above. For
each nonfallback record with such a branch, the analyzer selects the candidate
with minimum outcome progress deficit and compares it with the selected
candidate on current-tick PerfectTracker command fields, open-loop rollout
distance, and existing atom/proxy quantities. Candidate outcomes are still
offline labels only; no online selector or candidate generator changes.

Verification:

```text
python -m pytest camp_core/tests
195 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
200 passed
```

Summary:

| Candidate set | Qualifying records | No-progress-loss rate | Lower target-speed rate | Lower first-step reach rate | Lower H3 distance rate | Restart changed rate | Progress deficit mean | P50 | H3 distance delta mean | Command jerk delta mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 1,314 | 0.001522 | 0.807458 | 0.807458 | 0.866058 | 0.000000 | 0.292355 m | 0.218676 m | -0.015172 m | +0.436726 m/s^3 |
| `k16_noise1p0` | 1,355 | 0.008118 | 0.768266 | 0.768266 | 0.825092 | 0.000000 | 1.252943 m | 0.207944 m | -0.013267 m | +0.877841 m/s^3 |
| `k16_noise0p75` | 1,447 | 0.003455 | 0.776780 | 0.776780 | 0.845888 | 0.000000 | 0.510523 m | 0.152702 m | -0.011188 m | +0.178910 m/s^3 |

Interpretation:

1. Restart-tail logic is not the active mechanism in these outcome logs:
   selected and minimum-deficit joint-comfort candidates had zero restart-push
   rate and zero restart-change rate.
2. The progress deficit is strongly aligned with the first-step command path.
   The minimum-deficit comfort branch has lower PerfectTracker target speed and
   lower first-step reach in roughly `77-81%` of qualifying records, and lower
   H3 open-loop distance in roughly `83-87%`.
3. The chosen comfort branch improves outcome jerk/lateral but often worsens
   command jerk. Therefore command-jerk dominance is not a sufficient design
   rule for fixing the closed-loop outcome comfort gap.
4. Planned/proxy red-light quantities can move even when realized boolean
   safety labels are nonworse. Any later structured candidate transform must
   still be fully re-scored by the existing DP reward, red-light, feasibility,
   and CAMP atom paths before selection.

Decision: do not run new simulation from this audit alone. The next admissible
candidate-generation design must preserve or explicitly constrain first-step
reach/PerfectTracker target speed while creating comfort diversity downstream.
It must not repeat the rejected prefix-blend, step-reach guard, K expansion, or
noise-only routes. A valid predeclaration should first define the finite
candidate transform, prove it is current-tick/outcome-free and deterministic,
state how first-step reach is preserved, and show via cheap offline diagnostics
that it can reduce the measured progress deficit before any new non-formal
matrix is launched.

| Artifact | SHA-256 |
| --- | --- |
| Progress-deficit attribution analyzer | `e901717e601ac94dab6d0842ab32dd003b4abd008e39420b3a72cf7107efe9a3` |
| Progress-deficit attribution tests | `41fc4da2773d5a0dffdabbaf74ecdf9cf9c6b6f96adeabd0b8e856329349a0b3` |
| K=8 attribution JSON | `e60f17f9bd3df448d0ba2ef2c7cc5bd9c4df7bd172f44450f81fd5eec6b475d2` |
| K=8 attribution markdown | `7f182534fa74159365fa8868481cb9cae1519a4b9d930297f1727962ae44a553` |
| `k16_noise1p0` attribution JSON | `ef615385fa90dac5d0a2da66ee79ea8c42c1aca65d5622a8b8a2e8e4846eebda` |
| `k16_noise1p0` attribution markdown | `639b241392af725f3850df54678f9cc9d886cea896d7a3e59906c68982744b45` |
| `k16_noise0p75` attribution JSON | `f960d93efe32710c2b2b8f29e902e468590783c91c7fc7b55fd65920990e999d` |
| `k16_noise0p75` attribution markdown | `9b9f44db189cebea0ffbdbed71fc68d0f1403bcf3975562cd6d1f6d89ce01656` |

### First-step graft potential audit

Commit `4a0e4a58e682fb810d2a1cb6f77fcdcab336c06a` adds an offline
cheap-proof screen for a first-step-preserving reference graft. This is a
diagnostic only. It does not change the online selector, CAMP weights, DP
weights, atom schema, simulator state update, or candidate generation used by
the replay.

For each existing outcome-labeled nonfallback record, the analyzer uses
candidate outcomes only to choose an oracle diagnostic donor: a feasible
candidate that is safety-nonworse, strictly improves both outcome jerk and
outcome lateral acceleration, and has the minimum outcome progress deficit
among such candidates. The audited graft formula itself uses only current-tick
stored postprocessed reference prefixes:

```text
g_t = p_s0 + p_dt - p_d0
```

Here `s` is the selected anchor, `d` is the oracle donor, `p_s0` is the
selected candidate's first postprocessed reference point, and `p_dt`/`p_d0`
come from the donor prefix. This is a translation of the donor prefix onto the
selected first reference point, so the first reference `xy` is preserved
exactly. It is not the rejected prefix-blend route because it does not
interpolate toward candidate 0. It is not the rejected step-reach guard because
it constructs a diagnostic prefix instead of filtering the finite candidate
set.

Mathematical boundary:

1. The donor choice is oracle/outcome-labeled and is used only to test
   potential on already collected logs. It is not an online policy and must
   not be used as selection evidence.
2. The graft formula is deterministic and current-tick once `s`, `d`, and the
   stored prefixes are fixed, but this audit does not prove downstream
   closed-loop progress preservation.
3. If a future online finite-candidate transform uses an outcome-free donor
   rule, fixed-candidate CAMP scoring can remain affine in `w`, so the existing
   simplex/CVaR/L2 master remains convex. The transform itself is not claimed
   to be Benders, and no global convexity is claimed over trajectory
   coordinates.

Verification before running the remote artifacts:

```text
python -m pytest camp_core/tests
197 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
202 passed
```

Summary:

| Candidate set | With oracle donors | First-step exact preservation | Donor lower first-step before graft | H3 displacement nonloss | H5 displacement nonloss | H10 displacement nonloss | Graft jerk-proxy improvement | Outcome progress deficit mean | P50 | P90 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 1,314 | 1.000000 | 0.807458 | 0.114155 | 0.101218 | 0.073820 | 0.592085 | 0.292355 m | 0.218676 m | 0.615692 m |
| `k16_noise1p0` | 1,355 | 1.000000 | 0.768266 | 0.154244 | 0.143911 | 0.115129 | 0.591144 | 1.252943 m | 0.207944 m | 0.620154 m |
| `k16_noise0p75` | 1,447 | 1.000000 | 0.776780 | 0.137526 | 0.128542 | 0.096752 | 0.597097 | 0.510523 m | 0.152702 m | 0.452525 m |

Additional displacement summaries:

| Candidate set | Graft H3 displacement delta mean | P50 | P90 | P95 | Graft H5 displacement delta mean | Graft H10 displacement delta mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | -0.011692 m | -0.008374 m | 0.000559 m | 0.003587 m | -0.024921 m | -0.064896 m |
| `k16_noise1p0` | -0.010644 m | -0.007749 m | 0.002087 m | 0.006655 m | -0.022660 m | -0.059439 m |
| `k16_noise0p75` | -0.008476 m | -0.005654 m | 0.001058 m | 0.003648 m | -0.017880 m | -0.045958 m |

Interpretation:

1. The translation graft proves only that first-step reference preservation is
   easy by construction. It does not solve the measured downstream progress
   bottleneck: H3 displacement nonloss is only `11-15%`, and H10 displacement
   nonloss is only `7-12%`.
2. The graft often improves the cheap prefix jerk proxy, roughly `59-60%` of
   oracle-donor records, so the donor shape contains comfort signal. That
   signal is not enough to justify simulation because the multi-step progress
   proxy still regresses for most records.
3. The rejected K16/noise rows behave similarly: larger candidate sets do not
   make first-step-only grafting a sufficient industrial intervention.

Decision: reject first-step-only graft before any new replay matrix, latency
smoke, online selector change, CAMP retraining, or formal seeds. The next
admissible candidate-generation design must preserve or explicitly constrain
multi-step progress/open-loop distance, at least over H3/H5/H10, while still
creating downstream comfort diversity. A future design should be evaluated
offline first with a current-tick, outcome-free rule and a fail-closed finite
candidate definition before any non-formal simulation is launched.

| Artifact | SHA-256 |
| --- | --- |
| First-step graft analyzer | `2aae1cd3c576cc8689d214b6fccfa687c8eb8c9228553dff592fd46384bfb68c` |
| First-step graft analyzer tests | `43510e633911e6974e0bf63fe67dbd779308f82012ad1d8dfe78135860af1ae9` |
| K=8 graft JSON | `98fd6c3dcace1ec04367fc1a4dd3c006439af7253a484f76a0b2d4e5c12abc4f` |
| K=8 graft markdown | `1c5de9bc3bb099f1fbcd76c6bf21bdaf096b0c2afdc3185c479f77eca0b282f9` |
| `k16_noise1p0` graft JSON | `bff45393a22d4b75941da33e926b5d416964c34cb4daf1fef491aa0a7248313e` |
| `k16_noise1p0` graft markdown | `dfb1f386909408d5e06fa561622f00077ef1744bc12aa9d652a59f3618e4a8e5` |
| `k16_noise0p75` graft JSON | `8199445ca7b146e8c198e8a73907920b1c51c1334058d7c1d7071746787250d3` |
| `k16_noise0p75` graft markdown | `f674c71367905c345d8917d9611ff89c1cd8c68aef07fadf115d8caa33d27568` |

### Anchored residual graft potential audit

Commit `599f1ebdd8de4e66ba04c7d8b873ecc08d800bb6` adds a stricter
multi-step progress-anchor screen after rejecting the first-step-only graft.
This is still an offline oracle-potential diagnostic. It does not change the
online selector, CAMP weights, DP weights, atom schema, simulator state update,
or replay candidate generation.

The analyzer uses the same oracle diagnostic donor definition as the
first-step graft screen: outcome labels choose a feasible, safety-nonworse,
joint jerk/lateral-improving candidate with minimum outcome progress deficit.
The audited transform then ignores outcome labels and uses only the selected
and donor postprocessed reference prefixes.

For anchor horizons `A = {1, 3, 5, 10}`, let `a` and `b` be adjacent
zero-indexed anchor indices. For each `t` in `[a, b]`, define

```text
lambda_t = (t - a) / (b - a)
S_lin(t) = S_a + lambda_t (S_b - S_a)
D_lin(t) = D_a + lambda_t (D_b - D_a)
G_t = S_lin(t) + (D_t - D_lin(t))
```

This injects the donor residual relative to its own anchor-interval linear
interpolation into the selected anchor interval. Therefore `G_t = S_t` at
H1/H3/H5/H10 by construction. It is not the rejected prefix-blend route because
it does not interpolate toward candidate 0, and it is not a step-reach guard
because it constructs a diagnostic finite candidate instead of filtering the
candidate set.

Mathematical boundary:

1. The transform is deterministic and affine in the selected/donor prefix
   coordinates once `s` and `d` are fixed. This does not imply global convexity
   over trajectory coordinates.
2. Fixed finite candidates can still be scored by the existing CAMP affine
   score in `w`, so the simplex/CVaR/L2 master remains convex if a future
   outcome-free donor rule is used.
3. This is not a Benders decomposition. No master/subproblem split, dual, or
   valid cut is constructed here.

Verification:

```text
python -m pytest camp_core/tests
199 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
204 passed
```

Summary:

| Candidate set | With oracle donors | Anchor exact preservation | H3 displacement nonloss | H5 displacement nonloss | H10 displacement nonloss | H3 path nonloss | H5 path nonloss | H10 path nonloss | Prefix jerk-proxy improvement | Prefix jerk-proxy delta mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 1,314 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.268645 | 0.270167 | 0.229072 | 0.072298 | +0.000592 |
| `k16_noise1p0` | 1,355 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.309963 | 0.304797 | 0.247232 | 0.070111 | +0.000631 |
| `k16_noise0p75` | 1,447 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 0.295784 | 0.292329 | 0.257775 | 0.127160 | +0.000380 |

Additional summaries:

| Candidate set | Outcome progress deficit mean | P50 | P90 | Donor prefix jerk-proxy delta mean | Graft H10 path delta mean | P95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 0.292355 m | 0.218676 m | 0.615692 m | -0.000007 | -0.000023 m | 0.000005 m |
| `k16_noise1p0` | 1.252943 m | 0.207944 m | 0.620154 m | -0.000007 | -0.000039 m | 0.000010 m |
| `k16_noise0p75` | 0.510523 m | 0.152702 m | 0.452525 m | -0.000004 | -0.000027 m | 0.000006 m |

Interpretation:

1. The anchor construction proves that selected H1/H3/H5/H10 displacement can
   be preserved exactly by a current-tick finite transform.
2. The comfort-shape signal does not survive this hard anchoring. The donor
   prefixes had slightly negative mean jerk-proxy deltas, but the anchored
   residual graft has positive mean jerk-proxy deltas and improves the proxy in
   only `7-13%` of oracle-donor records.
3. Path-length deltas are numerically tiny, but the very low strict nonloss
   rates under `1e-12` tolerance show that this screen is not providing a
   meaningful path-progress advantage beyond the enforced displacement
   anchors.

Decision: reject anchored residual graft before any replay matrix, latency
smoke, online selector change, CAMP retraining, or formal seeds. It fixes the
previous displacement-progress proof gap only by introducing hard anchor
kinks/residuals that destroy the cheap comfort proxy. The next admissible route
must preserve multi-step progress while controlling smoothness directly, for
example with a current-tick finite smoothing/projection screen whose objective
and constraints are stated before running logs. It must still remain a finite
candidate transform unless a valid convex subproblem, dual, and cuts are
explicitly constructed.

| Artifact | SHA-256 |
| --- | --- |
| Anchored residual graft analyzer | `c67fb979f3d08d4cb1485723539a69a2b5be9cfd83c8968d8c57edbac5f9ddb7` |
| Anchored residual graft analyzer tests | `407f2d1ac2634fd7bf47095786d94f2e154a1e39992f29475661b121acbc2d51` |
| K=8 anchored residual JSON | `b79a6faa986843502301dafe5418add69d1b38c1df396bf2f8dc4cfa6c8f6b9c` |
| K=8 anchored residual markdown | `5997bc51ea52f06865c2fb304709c8e275fa0b88bdbfe45515f4c495c2e6b645` |
| `k16_noise1p0` anchored residual JSON | `f0dccd8610a8f14059e1831fb225c73065e62adba6708f9e27e24e8dff58fbaf` |
| `k16_noise1p0` anchored residual markdown | `656e8479430f403e9749af33d65dad72dce1f42e6cec5979d0f33c5cb5c34829` |
| `k16_noise0p75` anchored residual JSON | `b2b02b525e07f71cc306df5a1796c9ced93e2d57718556dc54b3ede2e377fecf` |
| `k16_noise0p75` anchored residual markdown | `0e143ed2f329cab6bf059af3d9993347d9ee573c50db0593acd3d6d3eb04c7fe` |

### Smooth anchor projection potential audit

Commit `3a07ff1281ecce9c1455d8f67be14db1120375af` adds a convex
least-squares projection screen after rejecting hard anchored residual grafts.
This is still an offline oracle-potential diagnostic. It does not change the
online selector, CAMP weights, DP weights, atom schema, simulator state update,
or replay candidate generation.

The analyzer uses the same oracle diagnostic donor definition as the previous
screens: outcome labels choose a feasible, safety-nonworse, joint
jerk/lateral-improving candidate with minimum outcome progress deficit. For a
fixed selected prefix `S`, donor prefix `D`, and ridge `rho >= 0`, the audited
projection solves independently for `x` and `y`:

```text
min_G ||D3 G - D3 D||_2^2 + rho ||G - S||_2^2
s.t.  G_A = S_A,  A = {H1, H3, H5, H10}
```

`D3` is the third-difference operator over the stored postprocessed reference
prefix. The equality constraints preserve selected H1/H3/H5/H10 anchors
exactly. The first term tries to inherit the donor smoothness profile without
the hard residual kinks seen in the previous screen; the ridge term controls
deviation from the selected prefix.

Mathematical boundary:

1. For fixed `S`, `D`, and `rho`, this is a convex quadratic least-squares
   projection with affine equality constraints. It is deterministic and
   current-tick.
2. The oracle donor choice uses outcome labels only for offline potential
   diagnosis. A future online transform would need an outcome-free donor rule.
3. Fixed finite candidates can still be scored by the existing CAMP affine
   score in `w`, so the simplex/CVaR/L2 master remains convex. This projection
   is not a Benders decomposition, and no global convexity is claimed over
   trajectory coordinates.

Verification:

```text
python -m pytest camp_core/tests
202 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
207 passed
```

AutoDL GitHub fetch timed out during synchronization, so the `3a07ff1` commit
was transferred by a local git bundle and merged fast-forward. DP remained at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Summary over the fixed ridge grid `{0, 1e-4, 1e-3, 1e-2, 1e-1}`:

| Candidate set | With oracle donors | Anchor exact | H3/H5/H10 displacement nonloss | H10 path nonloss range | Jerk-proxy improvement range | Jerk-proxy delta mean range | Max selected deviation P95 range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 1,314 | 1.000000 | 1.000000 / 1.000000 / 1.000000 | 0.467275-0.477169 | 0.573820-0.584475 | -0.000004 to -0.000003 | 0.000239-0.000387 m |
| `k16_noise1p0` | 1,355 | 1.000000 | 1.000000 / 1.000000 / 1.000000 | 0.453875-0.470849 | 0.608856-0.615498 | -0.000004 | 0.000246-0.000440 m |
| `k16_noise0p75` | 1,447 | 1.000000 | 1.000000 / 1.000000 / 1.000000 | 0.446441-0.453352 | 0.606773-0.612301 | -0.000003 | 0.000197-0.000342 m |

Representative ridge `0.1` rows:

| Candidate set | Jerk-proxy improvement | Jerk-proxy delta mean | Max selected deviation P95 | H10 path delta mean | Third-difference target error mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 0.584475 | -0.000004 | 0.000239 m | 0.000034 m | 0.000053 |
| `k16_noise1p0` | 0.615498 | -0.000004 | 0.000246 m | -0.000001 m | 0.000060 |
| `k16_noise0p75` | 0.612301 | -0.000003 | 0.000197 m | 0.000003 m | 0.000041 |

Interpretation:

1. The projection fixes the two previous cheap-proof failures at once:
   H1/H3/H5/H10 displacement anchors are preserved exactly, and the prefix jerk
   proxy has a negative mean delta with a `57-62%` improvement rate.
2. The result is mathematically clean but industrially weak as a standalone
   transform. The P95 maximum deviation from the selected prefix is only about
   `0.0002-0.0004 m`, so applying this projection online is unlikely to
   materially change the PerfectTracker trajectory or closed-loop comfort.
3. The tiny transform magnitude also explains why this is not enough evidence
   to launch a paired replay matrix: the oracle donor has much larger realized
   outcome jerk/lateral improvements, but the current-prefix projection changes
   the selected command by sub-millimeter amounts.

Decision: keep smooth anchor projection as a valid mathematical building block
but do not run a replay matrix, latency smoke, online selector change, CAMP
retraining, or formal seeds from this screen alone. The next admissible route
should diagnose materiality: either show a current-tick outcome-free transform
that creates meter-scale or command-scale diversity while preserving
multi-step progress and smoothness, or explain why the realized outcome
improvements are coming from simulator/rollout mechanisms not visible in the
stored H10 reference prefix. Until that gap is closed, the default DP/CAMP
chain remains unchanged.

| Artifact | SHA-256 |
| --- | --- |
| Smooth anchor projection analyzer | `6f9de9c44ad591e33eb052002d3260d65c009e47b45532d1f0b05ff0db80d6f6` |
| Smooth anchor projection analyzer tests | `5929edf375d09d1e20751cdf22c0ea0643f198ae77047d170d1ff0071219a51d` |
| K=8 smooth projection JSON | `2db57ec14e47d8f7b3ab3c018311fc46d81d3c297951a7aad58d8b6773fe36b7` |
| K=8 smooth projection markdown | `127bd340d985a19c6172a41db84e674283deb85fbb5e5babd18cc32cf4a9ded9` |
| `k16_noise1p0` smooth projection JSON | `6335d3058b3dfebdccd41348229993b00b9cce36d10540fb066b5d3a1c8bd193` |
| `k16_noise1p0` smooth projection markdown | `1d651f7e70e97d34dcc846cf60dd84340bcc3884c7e0ed38eb38a1fc1dc4b966` |
| `k16_noise0p75` smooth projection JSON | `777f173011a180472f6439e763b4526fd702c49b8aac2b51ce3fd9a7ac279dcf` |
| `k16_noise0p75` smooth projection markdown | `e7ae7826a6e199dc0ffb6062d2a52efa222d3b015496e8e65ccd7b766362f442` |

### Materiality gap audit

Commit `e53e70c31cd46126ec1a5f9904a6b3445f9ebcc4` adds a layer-by-layer
materiality audit for the same safety-nonworse, joint jerk/lateral-improving
oracle donor candidates used by the graft/projection screens. Commit
`cfe6789f9de599204b16cdab1c5b6454ae70442f` makes `candidate_route_progress`
optional because early records in the existing logs store it as `null`.

This audit exists to explain why the smooth anchor projection was too small to
matter. It compares the oracle donor against the selected candidate across:

1. realized outcome labels computed from raw DP candidate trajectories;
2. raw DP candidate proxy costs;
3. PerfectTracker command proxy values;
4. stored PerfectTracker postprocessed reference prefixes;
5. fixed-candidate PerfectTracker open-loop rollout shadows.

Important provenance boundary:

```text
candidate_closed_loop_outcomes = compute_candidate_closed_loop_outcomes(candidates, ...)
```

Those labels are computed from the raw DP candidate trajectory branch. The
recent first-step, anchored-residual, and smooth-projection screens operate on
`candidate_perfect_tracker_postprocessed_reference_prefix`. Therefore a
projection that is clean on the tracker prefix can still erase the raw
candidate differences that made the oracle donor improve realized outcome
comfort.

Verification:

```text
python -m pytest camp_core/tests
204 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
209 passed
```

AutoDL GitHub fetch timed out during synchronization, so both materiality
commits were transferred by local git bundles and merged fast-forward. DP
remained at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Layer agreement summary:

| Candidate set | Raw DP jerk excess improve | Raw horizon lateral improve | Tracker command jerk improve | Tracker command lateral improve | Prefix jerk proxy improve | H3 rollout jerk improve | H3 rollout lateral improve |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 0.550989 | 1.000000 | 0.441400 | 0.609589 | 0.592085 | 0.480213 | 0.661339 |
| `k16_noise1p0` | 0.515129 | 1.000000 | 0.429520 | 0.573432 | 0.591144 | 0.478229 | 0.659041 |
| `k16_noise0p75` | 0.521078 | 1.000000 | 0.446441 | 0.578438 | 0.597097 | 0.505874 | 0.666897 |

Key deltas:

| Candidate set | Outcome progress delta mean | Outcome jerk delta mean | Outcome lateral delta mean | Tracker command jerk delta mean | H3 rollout jerk delta mean | Prefix max xy distance mean | Prefix H10 displacement delta mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | -0.291513 m | -0.179400 m/s^3 | -0.014655 m/s^2 | +0.436726 m/s^3 | -0.013038 m/s^3 | 0.075502 m | -0.068314 m |
| `k16_noise1p0` | -1.248050 m | -0.153059 m/s^3 | -0.015786 m/s^2 | +0.877841 m/s^3 | +0.031385 m/s^3 | 0.074605 m | -0.062012 m |
| `k16_noise0p75` | -0.509320 m | -0.127507 m/s^3 | -0.011280 m/s^2 | +0.178910 m/s^3 | -0.058772 m/s^3 | 0.055173 m | -0.048635 m |

Prefix materiality:

| Candidate set | Prefix max >= 1 mm | Prefix max >= 1 cm | Prefix max >= 10 cm | Prefix max xy P95 |
| --- | ---: | ---: | ---: | ---: |
| K=8 baseline | 1.000000 | 0.938356 | 0.223744 | 0.228560 m |
| `k16_noise1p0` | 0.999262 | 0.935793 | 0.231734 | 0.226365 m |
| `k16_noise0p75` | 0.997927 | 0.872840 | 0.140981 | 0.180481 m |

Interpretation:

1. Lateral outcome improvement is not hidden. The raw DP horizon lateral proxy
   improves in `100%` of oracle-donor records, with the same mean deltas as
   realized outcome lateral acceleration.
2. Jerk outcome improvement is only weakly visible in current tracker-level
   quantities. Raw DP jerk excess improves in only `52-55%`; tracker command
   jerk improves in only `43-45%` and has a positive mean delta; H3 rollout jerk
   is near coin-flip and can have positive mean delta.
3. The postprocessed donor prefix is materially different from the selected
   prefix at centimeter scale in most records. The smooth projection became
   sub-millimeter because it forced selected H1/H3/H5/H10 anchors exactly,
   removing the donor's useful anchor/progress displacement.
4. The useful donor differences are tied to progress/anchor displacement:
   donors reduce outcome comfort metrics but lose progress and target speed.
   Hard-constraining progress anchors preserves progress by construction but
   also removes the material geometry needed for comfort change.

Decision: do not run a replay matrix, latency smoke, online selector change,
CAMP retraining, or formal seeds from materiality alone. The next admissible
route should operate closer to the raw DP candidate geometry or explicitly
allow a bounded, state-dependent progress/anchor tradeoff while preserving
smoothness. A tracker-prefix-only projection with exact selected anchors is
too small to matter; a command-jerk rule is also insufficient because it is
anti-aligned on average for these oracle donors.

| Artifact | SHA-256 |
| --- | --- |
| Materiality gap analyzer | `1373c3dd2d04b5ba0e4e9e14cd3847b2046d6a7a5e673ca7b540cf9f18e67ae1` |
| Materiality gap analyzer tests | `5f2baf05a6f75206e29db28a779f3bf007a2d37e7dca66a379ad40cf116fa3ea` |
| K=8 materiality JSON | `9ce21dcb9c1923bcb2abaae1eceecb6a94005bd8f1d8f67c62b10bb5f75bcb45` |
| K=8 materiality markdown | `018f272bd1553567e97bc5a222d49a19350ab1ba8dbac4fe276bdbfc959fe726` |
| `k16_noise1p0` materiality JSON | `d84155625c54004b69aa25fdff7bec21edc0428575c38529a2bb88d7cf916d7d` |
| `k16_noise1p0` materiality markdown | `899d56915f401e9b28f67106f06a8cbf7deacb86db4a10808a531f41bb2aa990` |
| `k16_noise0p75` materiality JSON | `30085779aa56b0a0381f7db0c2fbd74c08879913bf089d0167211072f7514d86` |
| `k16_noise0p75` materiality markdown | `aca40024c5e8f8f2abe9cb8cd1f042415486b2f0653144286498c0bbfc0274ad` |

### Bounded tradeoff audit

Commit `5c087b3dc9251d20c5873a4077da48fdcbb0e3a6` adds an offline budget
screen for the raw-candidate geometry direction identified by the materiality
gap audit. It asks how much selected-candidate progress, PerfectTracker target
speed, and H10 displacement loss must be allowed before the existing finite
candidate set contains a safety-nonworse, joint outcome jerk/lateral-improving
oracle donor.

This is not an online selector. Outcome labels define the oracle donor set for
diagnosis only. The budget predicates are current-log constants over a fixed
finite candidate set. If later converted into atoms or guards, fixed-candidate
CAMP scores remain affine in `w`; no Benders or trajectory-coordinate convexity
claim is introduced.

Verification:

```text
python -m pytest camp_core/tests
206 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests
211 passed
```

AutoDL was synchronized by git bundle because GitHub fetch was unreliable. DP
remained at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Oracle donor baseline:

| Candidate set | With oracle donors | Progress loss mean | P50 | P90 | Target-speed loss mean | H10 loss mean | Prefix max distance mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 1,314 | 0.292355 m | 0.218676 m | 0.615692 m | 0.040774 m/s | 0.070469 m | 0.075502 m |
| `k16_noise1p0` | 1,355 | 1.252943 m | 0.207944 m | 0.620154 m | 0.039404 m/s | 0.066566 m | 0.074707 m |
| `k16_noise0p75` | 1,447 | 0.510523 m | 0.152702 m | 0.452525 m | 0.033581 m/s | 0.050740 m | 0.055173 m |

Progress-budget slice with target-speed loss `<=0.1 m/s` and H10 displacement
loss `<=0.1 m`:

| Candidate set | 0.05 m | 0.10 m | 0.25 m | 0.50 m | 1.00 m |
| --- | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | 0.063152 | 0.149269 | 0.378914 | 0.527662 | 0.544885 |
| `k16_noise1p0` | 0.074260 | 0.185930 | 0.436628 | 0.589615 | 0.609715 |
| `k16_noise0p75` | 0.117117 | 0.266561 | 0.547960 | 0.664547 | 0.674616 |

Target-speed budget slice with progress loss `<=0.5 m` and H10 displacement
loss `<=0.1 m`:

| Candidate set | 0.02 m/s | 0.05 m/s | 0.10 m/s | 0.25 m/s |
| --- | ---: | ---: | ---: | ---: |
| K=8 baseline | 0.333507 | 0.492693 | 0.527662 | 0.531837 |
| `k16_noise1p0` | 0.401452 | 0.557231 | 0.589615 | 0.591848 |
| `k16_noise0p75` | 0.469528 | 0.626391 | 0.664547 | 0.665607 |

H10 displacement budget slice with progress loss `<=0.5 m` and target-speed
loss `<=0.1 m/s`:

| Candidate set | 0.01 m | 0.05 m | 0.10 m | 0.25 m |
| --- | ---: | ---: | ---: | ---: |
| K=8 baseline | 0.118998 | 0.366910 | 0.527662 | 0.570981 |
| `k16_noise1p0` | 0.164712 | 0.447236 | 0.589615 | 0.631491 |
| `k16_noise0p75` | 0.199258 | 0.523582 | 0.664547 | 0.695284 |

Interpretation:

1. Tight no-loss behavior remains unavailable. With target-speed and H10 loss
   both bounded at `0.1`, only `6-12%` of nonfallback records retain an oracle
   donor at `0.05 m` progress loss.
2. A moderate state-dependent tradeoff is materially different. At
   `progress<=0.5 m`, `target-speed<=0.1 m/s`, and `H10<=0.1 m`, the existing
   pool retains oracle donors in `52.8%` of K=8, `59.0%` of K16/noise1p0, and
   `66.5%` of K16/noise0p75 nonfallback records.
3. Target-speed budgets saturate quickly after about `0.1 m/s`, while H10
   anchor budget still matters between `0.01 m` and `0.10 m`. This reinforces
   the materiality conclusion: exact selected anchors are too strict, but
   unbounded progress sacrifice is also not acceptable.

Decision: do not run replay, implement an online selector, retrain CAMP, or
use formal seeds from this oracle budget screen alone. The next admissible
step is to predeclare an outcome-free finite rule that approximates this
bounded tradeoff using current-tick quantities: base feasibility, red guards,
progress/target-speed/H10 budgets, raw horizon lateral improvement, and a
carefully handled jerk proxy. The rule must retain the baseline when no
candidate passes and must be evaluated offline before any paired replay.

| Artifact | SHA-256 |
| --- | --- |
| Bounded tradeoff analyzer | `6a1e5141465ae7428373bf04e81521c10fbe81b00d1a843a563903744b1cca85` |
| Bounded tradeoff analyzer tests | `f3e72b04003a2f8268254e18ae3b1e503e92b6c9939807d5a2d8c4fd36e36af7` |
| K=8 bounded tradeoff JSON | `a689e2b4618dd2196fcaefa27b5aca704924f6297cd21523f98f175cf9e4760b` |
| K=8 bounded tradeoff markdown | `4eee3291628b526ac94d2e3c5e2ed449b86ed2e7a322fb58403354042b5bdb41` |
| `k16_noise1p0` bounded tradeoff JSON | `6f4ddd9c172e2e30d6f1f2ae9e62367ee831c6bb2bee70da72b11e45d495ec73` |
| `k16_noise1p0` bounded tradeoff markdown | `b9649fe559794f7e9869ba77237805cbc4fcadb9253958375fdff17c6a2aac96` |
| `k16_noise0p75` bounded tradeoff JSON | `44798995e1bddff61ba4a773a6b8389eba2441a74c082d529000bb58d7750971` |
| `k16_noise0p75` bounded tradeoff markdown | `5b5730a67498d329d34d9d8f6147e030931affe354ef8aa36864c49759089717` |

### Outcome-free bounded selector screen

Commits:

- `70d9a86de275ec36adb484f3677af706227e8978` fixes the selector screen so
  nonfinite `selection_scores` from real DP logs are treated as deterministic
  tie-break sentinels instead of aborting the audit. These scores are used only
  after safety, progress, target-speed, H10, raw lateral, and optional raw jerk
  guards.
- `61693ec5a8de57a644aa4586c6c60aea9202c324` changes the progress proxy order
  to `candidate_route_progress`, then `dp_candidate_rewards.progress`, then
  `candidate_step_reach`. The K8/K16 logs do not contain route progress but do
  contain DP reward progress for all 2,400 records in each candidate set.
- `20505e55125d813b6d154447a69e1042b7d5cd44` adds jerk-safe progress-budget
  screens at `0.05`, `0.10`, and `0.25 m` before the prior `0.50 m` moderate
  screen.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_outcome_free_bounded_selector.py
5 passed

python -m pytest camp_core
211 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_outcome_free_bounded_selector.py
5 passed
```

AutoDL was synchronized by git bundle. DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. No replay, formal seeds, online
selector, CAMP retraining, or DP modification was run.

The screen is outcome-free at selection time. It uses fixed finite candidate
diagnostics from the current tick: base feasibility, red-light guards, DP
reward progress or fallback progress proxy, PerfectTracker target speed, H10
postprocessed-reference displacement, raw horizon lateral cost, optional raw
jerk nondegradation, the original CAMP score as a late tie-break, and candidate
index. Candidate closed-loop outcomes are used only for posterior evaluation.
For a fixed finite candidate set these quantities are constants, so a later
atomized CAMP score would remain affine in `w` and compatible with the existing
simplex/CVaR/L2 convex master. This finite-candidate lexicographic screen is
not Benders and makes no trajectory-coordinate convexity claim.

Final artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| K=8 outcome-free selector JSON | `3067f253cd5d75c15a774ef85fc3852729b318ff8f0a98e0187fbcdb92ea621a` |
| K=8 outcome-free selector markdown | `2135bfc2f2fcdf8eddaa177e858f979065aa6d0a2511483ad0c76a980ea331b7` |
| `k16_noise1p0` outcome-free selector JSON | `16dcd9b4e6a0b49b9dab6d207cabf5bf06836b4d4c8a6f03295edcb927bd6b61` |
| `k16_noise1p0` outcome-free selector markdown | `392e2710fafc0d269adcf56a2cc33db9c28de5af4388a93301911c33e4dd7b10` |
| `k16_noise0p75` outcome-free selector JSON | `d810ee41c74d50773bb63e3565eb1f9ff61545b7073b2f698da58f2518f0fa29` |
| `k16_noise0p75` outcome-free selector markdown | `fc9dae276b17a925c4823bdaa290f4d08ab76d86c69d1142836278a742bc56f6` |

Key jerk-safe screens:

| Candidate set | Screen | Changed rate | Safety regressions | Joint comfort rate | Changed progress mean | Changed jerk mean | Changed lateral mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | tight `0.05 m` | 0.115 | 0 | 0.591 | -0.036 m | -0.003 m/s^3 | -0.005 m/s^2 |
| K=8 baseline | balanced `0.10 m` | 0.234 | 0 | 0.612 | -0.066 m | -0.016 m/s^3 | -0.007 m/s^2 |
| K=8 baseline | relaxed `0.25 m` | 0.511 | 0 | 0.691 | -0.152 m | -0.063 m/s^3 | -0.011 m/s^2 |
| K=8 baseline | moderate `0.50 m` | 0.667 | 0 | 0.726 | -0.244 m | -0.110 m/s^3 | -0.015 m/s^2 |
| `k16_noise1p0` | tight `0.05 m` | 0.125 | 0 | 0.513 | -0.039 m | +0.027 m/s^3 | -0.005 m/s^2 |
| `k16_noise1p0` | balanced `0.10 m` | 0.271 | 0 | 0.606 | -0.073 m | -0.025 m/s^3 | -0.008 m/s^2 |
| `k16_noise1p0` | relaxed `0.25 m` | 0.556 | 0 | 0.733 | -0.170 m | -0.104 m/s^3 | -0.015 m/s^2 |
| `k16_noise1p0` | moderate `0.50 m` | 0.721 | 0 | 0.741 | -0.279 m | -0.125 m/s^3 | -0.020 m/s^2 |
| `k16_noise0p75` | tight `0.05 m` | 0.196 | 0 | 0.562 | -0.039 m | +0.027 m/s^3 | -0.004 m/s^2 |
| `k16_noise0p75` | balanced `0.10 m` | 0.376 | 0 | 0.643 | -0.072 m | -0.026 m/s^3 | -0.007 m/s^2 |
| `k16_noise0p75` | relaxed `0.25 m` | 0.696 | 0 | 0.700 | -0.165 m | -0.078 m/s^3 | -0.012 m/s^2 |
| `k16_noise0p75` | moderate `0.50 m` | 0.811 | 0 | 0.716 | -0.257 m | -0.109 m/s^3 | -0.017 m/s^2 |

Interpretation:

1. Replacing step reach with DP reward progress fixed the largest progress
   proxy failure. The earlier step-reach screen produced changed-record mean
   progress losses as large as about `-1.0 m` on `k16_noise1p0`; the DP reward
   proxy reduces the `0.50 m` jerk-safe screen to about `-0.28 m`.
2. Safety is encouraging but not sufficient for an online gate. All jerk-safe
   screens have zero posterior safety regressions in these 12-run nonformal
   artifacts, but the non-jerk-safe tight screen still had one posterior safety
   regression on `k16_noise1p0`.
3. No screen is a free Pareto improvement. Tight jerk-safe screens preserve
   progress but have low opportunity and weak posterior comfort coverage;
   on both K16 sets their changed-record mean jerk delta is still positive.
   Relaxed and moderate screens improve mean jerk and lateral acceleration but
   accept explicit progress loss and still have only `0.70-0.74` joint comfort
   improvement rates on the K16 sets.
4. The finite candidate set contains useful bounded tradeoffs, but the current
   outcome-free rule is not yet industrially acceptable as an online selector.
   It lacks a predeclared guarantee that posterior comfort will not regress on
   individual changed ticks, and the progress/comfort tradeoff remains a design
   choice rather than a validated control policy.

Decision: reject online deployment from this screen for now. Keep the tool as a
diagnostic and do not run replay, formal seeds, online selector wiring, CAMP
retraining, or DP retraining from these results. The next admissible step is to
audit the changed records that fail posterior joint comfort under the balanced
and relaxed jerk-safe screens, using only current-tick quantities, to determine
whether an additional finite, convex-safe atom or guard can explain those
failures before any replay gate is considered.

### Outcome-free failure attribution

Commits:

- `9f4b8def57dcc89f8452f90949872c1ca04cbe0a` adds a failure-attribution
  screen for the balanced and relaxed jerk-safe outcome-free selectors.
- `543914872ad3ae5ba711a535c63c754d780d87f7` adds paired nonworse guard
  attribution so single-feature explanations are not over-interpreted.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_outcome_free_failure_attribution.py
1 passed

python -m pytest camp_core
212 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_outcome_free_failure_attribution.py
1 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
217 passed
```

AutoDL was synchronized by git bundle. DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. No replay, formal seeds, online
selector, CAMP retraining, or DP modification was run.

The attribution replays the stored outcome-free selector screens. Selection is
still based only on current-tick finite candidate diagnostics; outcomes are used
only to classify changed records as posterior joint-comfort success/failure.
All audited guard features are fixed candidate constants: raw DP prior/horizon
costs, PerfectTracker command magnitudes, PerfectTracker open-loop rollout
metrics, and postprocessed-prefix jerk proxy. If atomized as nonnegative costs,
they preserve affine scoring in `w` for a fixed finite candidate set. This is a
finite-candidate diagnostic, not Benders, and it makes no global convexity claim
over trajectory coordinates.

Final artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| K=8 failure attribution JSON | `a79b17a7c6b83569248e09fc9f80f07fbb8c2ef23c0899d8091dfad791957522` |
| K=8 failure attribution markdown | `f294b6b38aff668e93def8242f9cd5c6119708190f54594d112ad8e6a0156f29` |
| `k16_noise1p0` failure attribution JSON | `c55335368a00f3886e6bf8288713c591ac97f2fedb1d15f87b25bedd90001617` |
| `k16_noise1p0` failure attribution markdown | `6eda95897ef9a7b1de25713d2ebc774efaeaabb16c7fcb9c08260f5607da3d8c` |
| `k16_noise0p75` failure attribution JSON | `7b5b32826023d69cb8c481f2a25f8244514fa7cd1ef1a344f53151ec5c6a11f2` |
| `k16_noise0p75` failure attribution markdown | `1fdf07a282a59c3c634a2bb53d5fe9e9e874e23106a1b54b9c75bf9c9bf8af0a` |

Changed-record pass/fail summary:

| Candidate set | Screen | Changed | Success | Failure | Failure mode |
| --- | --- | ---: | ---: | ---: | --- |
| K=8 baseline | balanced `0.10 m` | 448 | 274 | 174 | jerk-not-improved only |
| K=8 baseline | relaxed `0.25 m` | 979 | 676 | 303 | jerk-not-improved only |
| `k16_noise1p0` | balanced `0.10 m` | 485 | 294 | 191 | jerk-not-improved only |
| `k16_noise1p0` | relaxed `0.25 m` | 996 | 730 | 266 | jerk-not-improved only |
| `k16_noise0p75` | balanced `0.10 m` | 709 | 456 | 253 | jerk-not-improved only |
| `k16_noise0p75` | relaxed `0.25 m` | 1,313 | 919 | 394 | jerk-not-improved only |

Selected paired guard results:

| Candidate set | Screen | Pair guard | Kept | Success keep | Failure removal | Precision | Progress mean | Jerk mean | Lateral mean |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | balanced | prefix jerk + tracker jerk nonworse | 108 | 0.303 | 0.856 | 0.769 | -0.063 m | -0.051 m/s^3 | -0.009 m/s^2 |
| K=8 baseline | relaxed | prefix jerk + tracker jerk nonworse | 236 | 0.281 | 0.848 | 0.805 | -0.153 m | -0.120 m/s^3 | -0.015 m/s^2 |
| `k16_noise1p0` | balanced | prefix jerk + tracker jerk nonworse | 115 | 0.276 | 0.822 | 0.704 | -0.066 m | -0.077 m/s^3 | -0.009 m/s^2 |
| `k16_noise1p0` | relaxed | prefix jerk + tracker jerk nonworse | 226 | 0.244 | 0.820 | 0.788 | -0.168 m | -0.143 m/s^3 | -0.017 m/s^2 |
| `k16_noise0p75` | balanced | prefix jerk + tracker jerk nonworse | 176 | 0.285 | 0.818 | 0.739 | -0.069 m | -0.041 m/s^3 | -0.006 m/s^2 |
| `k16_noise0p75` | relaxed | prefix jerk + tracker jerk nonworse | 322 | 0.270 | 0.812 | 0.770 | -0.169 m | -0.111 m/s^3 | -0.013 m/s^2 |
| K=8 baseline | balanced | H3 distance nonloss + tracker jerk nonworse | 43 | 0.139 | 0.971 | 0.884 | -0.047 m | -0.089 m/s^3 | -0.007 m/s^2 |
| `k16_noise1p0` | balanced | H3 distance nonloss + tracker jerk nonworse | 74 | 0.194 | 0.911 | 0.770 | -0.053 m | -0.072 m/s^3 | -0.008 m/s^2 |
| `k16_noise0p75` | balanced | H3 distance nonloss + tracker jerk nonworse | 68 | 0.118 | 0.945 | 0.794 | -0.057 m | -0.046 m/s^3 | -0.005 m/s^2 |

Interpretation:

1. The posterior failures are structurally narrow: every failure in the audited
   balanced/relaxed jerk-safe screens is `jerk_not_improved`. There are no
   posterior safety regressions, lateral-only failures, or both-comfort failures
   in these artifacts.
2. Current-tick jerk proxies have signal but not enough coverage. The prefix
   jerk + tracker command jerk nonworse pair removes about `81-86%` of failures
   with precision around `0.70-0.81`, but it keeps only `24-30%` of successes.
   That is useful evidence for diagnosis, not an industrial online selector.
3. Distance-nonloss pairs remove `91-97%` of failures, but they keep only
   `5-19%` of successes in the shown balanced screens and even less in some
   relaxed screens. This mostly recreates the previously rejected strict
   progress-preservation behavior.
4. Raw DP lateral-excess and horizon-yaw nonworse guards do not explain the
   failures. Raw lateral is already improved by construction, and the residual
   failure is jerk alignment between current-tick proxies and posterior outcome.

Decision: reject adding another online guard or atom from this attribution
alone. The guard candidates either have too little success coverage or fail to
remove enough jerk failures. Keep the attribution tool for diagnosis. The next
admissible step is to audit, within each failing changed record, whether a
different admissible candidate existed that also passed the promising current
tick jerk guards and was posterior joint-comfort successful. If such candidates
exist, the issue is tie-break/ranking inside the finite set; if not, the issue
returns to candidate generation/diversity rather than CAMP weight training.

### Outcome-free alternative-candidate audit

Commit `d4047deab41670bf4dc6bdbae946318bd49e1bc2` adds an offline audit that
inspects only the changed records where the outcome-free selector picked a
posterior joint-comfort failure. For each such failure tick it asks:

1. whether any other candidate inside the same current-tick admissible set was
   posterior joint-comfort successful; and
2. whether any such successful candidate also passed predeclared current-tick
   jerk guards: prefix + tracker jerk nonworse, prefix + H3 rollout jerk
   nonworse, tracker + H3 rollout jerk nonworse, or H3 distance + tracker jerk
   nonworse.

Selection and guard predicates still use only fixed current-tick finite
candidate diagnostics. Outcomes are posterior labels for diagnosis only. If
these guard quantities are later atomized as candidate costs, fixed-candidate
CAMP scoring remains affine in `w`; this is not Benders and makes no
trajectory-coordinate convexity claim.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_outcome_free_alternative_candidates.py
1 passed

python -m pytest camp_core
213 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_outcome_free_alternative_candidates.py
1 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
218 passed
```

AutoDL was synchronized by git bundle. DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. No replay, formal seeds, online
selector, CAMP retraining, or DP modification was run.

Final artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| K=8 alternative-candidate JSON | `526f7e92ab66452cca5423d44bbef1d9c6e58a0ba2d7b79fd69450f661ea9bdc` |
| K=8 alternative-candidate markdown | `6111a9a4ac4c4e2f41755ca0e66155456ceec3c91391de64fd5a642468e27666` |
| `k16_noise1p0` alternative-candidate JSON | `673ec69716a2d64c11f6fcefc278cec99e124feb258f5b1c19fe61a4c26aba3b` |
| `k16_noise1p0` alternative-candidate markdown | `9e768848b26357f49a1abb14b9ee8569c1da5ed72c82a697988e702c99b9f7b6` |
| `k16_noise0p75` alternative-candidate JSON | `6fba73a7b63daec4843101513409eb7e85c59e9e7d46d58bf0136116c60d5802` |
| `k16_noise0p75` alternative-candidate markdown | `8fd86a7278a6e112e89614bc08f0f85b6e82b617fbb6a52733ebc8ae9e8d1792` |

Failure-tick availability:

| Candidate set | Screen | Failure ticks | Any admissible posterior-success candidate | Rate |
| --- | --- | ---: | ---: | ---: |
| K=8 baseline | balanced `0.10 m` | 174 | 19 | 0.109 |
| K=8 baseline | relaxed `0.25 m` | 303 | 46 | 0.152 |
| `k16_noise1p0` | balanced `0.10 m` | 191 | 24 | 0.126 |
| `k16_noise1p0` | relaxed `0.25 m` | 266 | 59 | 0.222 |
| `k16_noise0p75` | balanced `0.10 m` | 253 | 50 | 0.198 |
| `k16_noise0p75` | relaxed `0.25 m` | 394 | 117 | 0.297 |

Guarded successful alternatives:

| Candidate set | Screen | Guard set | With guarded success | Rate | Best success rank mean | Progress mean | Jerk mean | Lateral mean |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 baseline | balanced | prefix + tracker jerk | 1 | 0.006 | 1.000 | -0.066 m | -0.135 m/s^3 | -0.010 m/s^2 |
| K=8 baseline | relaxed | prefix + tracker jerk | 8 | 0.026 | 1.125 | -0.119 m | -0.098 m/s^3 | -0.008 m/s^2 |
| `k16_noise1p0` | balanced | prefix + tracker jerk | 8 | 0.042 | 2.250 | -0.053 m | -0.090 m/s^3 | -0.006 m/s^2 |
| `k16_noise1p0` | relaxed | prefix + tracker jerk | 13 | 0.049 | 2.769 | -0.090 m | -0.075 m/s^3 | -0.005 m/s^2 |
| `k16_noise0p75` | balanced | prefix + tracker jerk | 17 | 0.067 | 2.647 | -0.037 m | -0.050 m/s^3 | -0.003 m/s^2 |
| `k16_noise0p75` | relaxed | prefix + tracker jerk | 37 | 0.094 | 3.000 | -0.085 m | -0.043 m/s^3 | -0.003 m/s^2 |
| K=8 baseline | relaxed | prefix + H3 rollout jerk | 15 | 0.050 | 1.733 | -0.088 m | -0.113 m/s^3 | -0.006 m/s^2 |
| `k16_noise1p0` | relaxed | prefix + H3 rollout jerk | 21 | 0.079 | 3.429 | -0.085 m | -0.070 m/s^3 | -0.005 m/s^2 |
| `k16_noise0p75` | relaxed | prefix + H3 rollout jerk | 51 | 0.129 | 3.275 | -0.089 m | -0.044 m/s^3 | -0.003 m/s^2 |

Interpretation:

1. The failure ticks mostly do not contain a better finite-set alternative for
   the current bounded screens. Only `10.9-29.7%` of failure ticks have any
   admissible posterior-success candidate at all.
2. The promising current-tick jerk guards are not hiding a large tie-break
   opportunity. Prefix + tracker jerk nonworse finds guarded successful
   alternatives in only `0.6-9.4%` of failure ticks; prefix + H3 rollout jerk is
   slightly better on relaxed screens but still at most `12.9%`.
3. When guarded successful alternatives exist, their average progress loss is
   modest and ranks are usually after the selected failing candidate, so there
   is a real tie-break component. However, the coverage is too small to justify
   an online selector or a new atom by itself.
4. The dominant blocker is candidate availability under the fixed DP candidate
   set and bounded progress/anchor constraints. This aligns with the earlier
   K8/K16 availability conclusion: continuing to tune CAMP weights or add a
   scalar atom is likely to chase sparse proxy opportunities rather than solve
   the industrial problem.

Decision: reject tie-break/ranking changes, online guard wiring, CAMP
retraining, DP retraining, and formal seeds from this evidence. The next
admissible step is candidate-generation/diversity diagnosis under fixed DP
weights: compare candidate pools by sample count/noise/temperature-like
available controls and ask whether the rate of admissible posterior-success
alternatives in failure ticks increases without changing the CAMP mathematical
contract. Any generator-side experiment must be reported as changing the
finite candidate set, not as a Benders or convex trajectory-coordinate claim.

### Alternative-candidate comparison gate

Commit `63356630309ecf409ab9e22ce27e9ceb8aa96a4b` adds a comparator for the
stored alternative-candidate reports. The comparator is deliberately stricter
than the descriptive audit above: every required bounded screen must satisfy
both of the following before the candidate-generation setting can advance to a
separate latency and paired-replay design step:

- any admissible posterior-success coverage at least `0.40`, with improvement
  over K=8 at least `0.15`;
- best predeclared current-tick guarded-success coverage at least `0.20`, with
  improvement over K=8 at least `0.10`.

This is an offline comparison gate only. It reads posterior outcomes from
stored reports as labels, does not select online trajectories, does not modify
DP, does not train CAMP, and does not authorize formal seeds. The mathematical
boundary is unchanged: generator-side changes alter the finite candidate set;
for any fixed set, CAMP scoring remains affine in `w` and compatible with the
simplex/CVaR/L2 convex master. The comparator is not Benders and makes no
trajectory-coordinate convexity claim.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_alternative_candidates_compare.py
3 passed

python -m pytest camp_core
216 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_alternative_candidates_compare.py
3 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
221 passed
```

AutoDL was synchronized by git bundle. CAMP local/GitHub/AutoDL reached
`63356630309ecf409ab9e22ce27e9ceb8aa96a4b`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Existing untracked files on local
and AutoDL were left untouched.

The comparison command was:

```bash
K8=/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc
K16A=/root/autodl-tmp/camp_dp_candidate_availability_k16_noise1p0_2212309
K16B=/root/autodl-tmp/camp_dp_candidate_availability_k16_noise0p75_2212309
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/compare_diffusion_planner_alternative_candidates.py \
  --baseline_json "$K8/k8_baseline_outcome_free_alternative_candidates.json" \
  --candidate_json "k16_noise1p0=$K16A/k16_noise1p0_outcome_free_alternative_candidates.json" \
  --candidate_json "k16_noise0p75=$K16B/k16_noise0p75_outcome_free_alternative_candidates.json" \
  --output_json "$K8/k8_vs_k16_alternative_candidate_comparison.json" \
  --output_md "$K8/k8_vs_k16_alternative_candidate_comparison.md"
```

Final artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Alternative-candidate comparator | `a91fb7bf39d7526eb1bb2eeb1d34ebdf0d137ca5f43ff79e1e6f2f8bee521c2a` |
| Comparator tests | `a27982bf63154899fee0383ff7f47372bc2034d985aad09915faac48c4d35be2` |
| K8-vs-K16 comparison JSON | `1fc65638e1f2eba3541a0959805ff8efcadb5c6f6ea3c9b0be175763b546fe32` |
| K8-vs-K16 comparison markdown | `63dd686681cb6e56d5f02024ab39702ffc3a3a633cbcd7f2252073946fc02647` |

Comparison result:

| Candidate set | Screen | Failure ticks | Any success rate | Delta | Best guard | Guarded success rate | Delta | Gate |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| `k16_noise1p0` | balanced `0.10 m` | 191 | 0.126 | +0.016 | tracker + H3 rollout jerk | 0.052 | +0.041 | fail |
| `k16_noise1p0` | relaxed `0.25 m` | 266 | 0.222 | +0.070 | prefix + H3 rollout jerk | 0.079 | +0.029 | fail |
| `k16_noise0p75` | balanced `0.10 m` | 253 | 0.198 | +0.088 | prefix + H3 rollout jerk | 0.091 | +0.062 | fail |
| `k16_noise0p75` | relaxed `0.25 m` | 394 | 0.297 | +0.145 | prefix + H3 rollout jerk | 0.129 | +0.080 | fail |

Interpretation:

1. The best current K16/noise setting still misses both industrial coverage
   thresholds. The strongest any-success rate is `0.297`, below the `0.40`
   gate; the strongest guarded-success rate is `0.129`, below the `0.20` gate.
2. `k16_noise0p75` improves relaxed-screen availability but also has more
   failure ticks than K=8 (`394` versus `303`). It is therefore not a clean
   candidate-generation fix.
3. The comparator confirms the earlier descriptive conclusion with an explicit
   predeclared gate: the current K16/noise candidate-generation grid should be
   rejected, not promoted to online selector wiring or new CAMP training.

Decision: reject the current K16/noise candidate-generation grid. Do not run
replay, formal seeds, online selector wiring, CAMP retraining, or DP
retraining from these results. The next admissible step is to diagnose why the
fixed DP generator does not place enough guarded posterior-success candidates
inside the bounded admissible set, using generator-side metadata and
outcome-free candidate-set descriptors before proposing any new sampling or
conditioning change.

### Failure-tick current descriptor audit

Commit `51958b12fbb70266a4609e1ce96e58ab713e2710` adds a failure-tick
descriptor audit. It replays the same bounded outcome-free screens and only
keeps changed ticks where the screen selected a posterior joint-comfort
failure. For those ticks it summarizes current-tick finite-candidate
descriptors: admissible counts, feature ranges, best feature deltas relative to
the selected candidate, and the predeclared jerk-guard availability. Posterior
outcomes are used only to split failure ticks into "with any successful
alternative" and "without any successful alternative" groups.

This diagnostic is still not an online selector and has no future-outcome
input at selection time. All descriptor values are fixed finite-candidate
constants. If any descriptor is later atomized, fixed-candidate CAMP scoring
remains affine in `w` and compatible with the simplex/CVaR/L2 convex master.
This diagnostic is not Benders and makes no trajectory-coordinate convexity
claim.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_failure_candidate_descriptors.py
1 passed

python -m pytest camp_core
217 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_failure_candidate_descriptors.py
1 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
222 passed
```

AutoDL was synchronized by git bundle. CAMP local/GitHub/AutoDL reached
`51958b12fbb70266a4609e1ce96e58ab713e2710`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The descriptor commands were:

```bash
K8=/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc
K16A=/root/autodl-tmp/camp_dp_candidate_availability_k16_noise1p0_2212309
K16B=/root/autodl-tmp/camp_dp_candidate_availability_k16_noise0p75_2212309

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_failure_candidate_descriptors.py \
  --root "$K8" --label k8_baseline \
  --output_json "$K8/k8_baseline_failure_candidate_descriptors.json" \
  --output_md "$K8/k8_baseline_failure_candidate_descriptors.md"

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_failure_candidate_descriptors.py \
  --root "$K16A" --label k16_noise1p0 \
  --output_json "$K16A/k16_noise1p0_failure_candidate_descriptors.json" \
  --output_md "$K16A/k16_noise1p0_failure_candidate_descriptors.md"

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_failure_candidate_descriptors.py \
  --root "$K16B" --label k16_noise0p75 \
  --output_json "$K16B/k16_noise0p75_failure_candidate_descriptors.json" \
  --output_md "$K16B/k16_noise0p75_failure_candidate_descriptors.md"
```

Final artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Failure descriptor analyzer | `3cddc765da57f7aacec40564cc3ca0d2b1960c291db62216809201bc1de27b5b` |
| Failure descriptor tests | `d2ebc08d2edfb26d906e8a9dfb538bc1704910cbcbf7d0fcbba8ee0a556b679f` |
| K=8 descriptor JSON | `1455cc70ee1579188c42d6547a741dcb77c236507551787a6ef479a819f98951` |
| K=8 descriptor markdown | `64cc6d00550eee76e2d1f80abf92727162414b85aeea1f6bd8037182331ecbf6` |
| `k16_noise1p0` descriptor JSON | `fec671954076c0d83f31741096153f32a93fedc93f2a12ce9858eb097ff3318f` |
| `k16_noise1p0` descriptor markdown | `e35e0216118f7b728d1c103d674230f073ca35ab190ccec5a50e651401bf5146` |
| `k16_noise0p75` descriptor JSON | `21bc91aca69ad4f9ecffea548e7e1bdade092db28c0f4144665b516556a4442f` |
| `k16_noise0p75` descriptor markdown | `9e394543f7ff2cf2b5fda1ee61c619c94f42da2fc5f60911e0c835c64c63efc5` |

Selected descriptor results:

| Candidate set | Screen | Failure ticks | With posterior-success alternative | Best progress delta mean | Best tracker jerk delta mean | Best H3 rollout jerk delta mean | No-success guarded admissible mean |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| K=8 | balanced | 174 | 19 | -0.051 m | +0.126 m/s^3 | +0.078 m/s^3 | 0.342 |
| K=8 | relaxed | 303 | 46 | -0.109 m | +0.011 m/s^3 | -0.040 m/s^3 | 0.533 |
| `k16_noise1p0` | balanced | 191 | 24 | -0.047 m | -0.242 m/s^3 | -0.245 m/s^3 | 0.503 |
| `k16_noise1p0` | relaxed | 266 | 59 | -0.098 m | -0.187 m/s^3 | -0.500 m/s^3 | 0.768 |
| `k16_noise0p75` | balanced | 253 | 50 | -0.043 m | -0.677 m/s^3 | -0.570 m/s^3 | 0.601 |
| `k16_noise0p75` | relaxed | 394 | 117 | -0.090 m | -0.409 m/s^3 | -0.563 m/s^3 | 0.783 |

Here "no-success guarded admissible mean" is the mean number of current-tick
tracker+H3-rollout jerk-nonworse admissible candidates among failure ticks that
had no posterior-success alternative.

Interpretation:

1. The current K16/noise grids do create more current-tick jerk-diverse
   admissible candidates. In the no-success failure group, tracker+H3 guarded
   admissible means rise from `0.342-0.533` on K=8 to `0.503-0.783` on K16.
2. This extra current-tick diversity does not translate reliably into
   posterior joint-comfort success. K16 failure ticks often have negative
   tracker or H3 rollout jerk deltas, but still no posterior-success
   alternative. The blocker is therefore not simply "no guarded candidate
   exists".
3. The strongest remaining hypothesis is proxy/outcome miscalibration: the
   fixed current-tick jerk proxies and short PerfectTracker rollout descriptors
   can improve while the closed-loop posterior mean jerk still fails to
   improve jointly with lateral acceleration.

Decision: reject adding the current tracker/H3/prefix jerk descriptors as
online guards or CAMP atoms from this evidence. The next admissible step is an
offline calibration audit that quantifies how current-tick jerk descriptors map
to posterior jerk success within the bounded admissible set. That audit may use
posterior outcomes as labels, but any deployable rule must remain based on
current-tick finite-candidate quantities and must preserve the fixed-candidate
affine CAMP scoring contract.

### Jerk descriptor calibration audit

Commit `99776743f73056cd6b852a048304022fcdbd439d` adds a candidate-level
calibration audit for current-tick jerk descriptors inside the same bounded
admissible finite candidate sets. For every admissible candidate, the audit
computes descriptor deltas relative to the selected candidate and labels the
candidate by posterior jerk improvement and posterior joint-comfort success.
It reports AUC plus the precision, recall, and precision lift of the
predeclared nonworse rule for each descriptor.

The predeclared failure-tick calibration gate requires, for at least one
descriptor on a screen:

- posterior jerk AUC at least `0.65`;
- nonworse-rule posterior jerk precision lift at least `0.15`;
- nonworse-rule posterior jerk recall at least `0.30`;
- nonworse-rule posterior joint-comfort precision lift at least `0.05`;
- nonworse-rule posterior joint-comfort recall at least `0.10`.

This is an offline calibration diagnostic only. Posterior outcomes are labels,
not online inputs. All candidate descriptors are current-tick finite constants;
if later atomized, fixed-candidate CAMP scoring remains affine in `w` and
compatible with the simplex/CVaR/L2 convex master. This audit is not Benders
and makes no trajectory-coordinate convexity claim.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_jerk_descriptor_calibration.py
1 passed

python -m pytest camp_core
218 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_jerk_descriptor_calibration.py
1 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
223 passed
```

AutoDL was synchronized by git bundle. CAMP local/GitHub/AutoDL reached
`99776743f73056cd6b852a048304022fcdbd439d`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The calibration commands were:

```bash
K8=/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc
K16A=/root/autodl-tmp/camp_dp_candidate_availability_k16_noise1p0_2212309
K16B=/root/autodl-tmp/camp_dp_candidate_availability_k16_noise0p75_2212309

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_jerk_descriptor_calibration.py \
  --root "$K8" --label k8_baseline \
  --output_json "$K8/k8_baseline_jerk_descriptor_calibration.json" \
  --output_md "$K8/k8_baseline_jerk_descriptor_calibration.md"

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_jerk_descriptor_calibration.py \
  --root "$K16A" --label k16_noise1p0 \
  --output_json "$K16A/k16_noise1p0_jerk_descriptor_calibration.json" \
  --output_md "$K16A/k16_noise1p0_jerk_descriptor_calibration.md"

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_jerk_descriptor_calibration.py \
  --root "$K16B" --label k16_noise0p75 \
  --output_json "$K16B/k16_noise0p75_jerk_descriptor_calibration.json" \
  --output_md "$K16B/k16_noise0p75_jerk_descriptor_calibration.md"
```

Final artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Jerk calibration analyzer | `66c5be2031bf3c1060254776b255e8e95fd0a39e21b3ad523158773cd30a1fbb` |
| Jerk calibration tests | `29d0e856895e4485e49ed17f983209b055ab0ffe4bb7193906f97ca06dbbe1ea` |
| K=8 calibration JSON | `37ef670e161b9c587774b61a43293c711bcc23f86c6b01b939726edea3352cec` |
| K=8 calibration markdown | `6f36a49819e21c92c9812859efd48d6c24ba09121730aeafdbda40319bc75548` |
| `k16_noise1p0` calibration JSON | `970034ec53fede0e024f1559f5633b3a11fdbd8968d07d8f3e9de7775016b52c` |
| `k16_noise1p0` calibration markdown | `f835ee105ab4ee5536b5106b37209173c09301d09e816926674026836a0a251e` |
| `k16_noise0p75` calibration JSON | `0ebd0ef3c0d983c839b7c961efc7ed08be9dd1740024ae537834ff5141ee9d52` |
| `k16_noise0p75` calibration markdown | `8d114e9b64f7b65cdc63e1607e2593e2a443de81249cc399dbe229df346889ba` |

Failure-tick calibration results:

| Candidate set | Screen | Candidate rows | Success rate | Best descriptor | AUC | Precision | Lift | Recall | Gate |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| K=8 | balanced | 275 | 0.095 | prefix jerk | 0.603 | 0.118 | +0.023 | 0.615 | fail |
| K=8 | relaxed | 582 | 0.096 | prefix jerk | 0.578 | 0.116 | +0.020 | 0.571 | fail |
| `k16_noise1p0` | balanced | 396 | 0.101 | prefix jerk | 0.705 | 0.173 | +0.072 | 0.675 | fail |
| `k16_noise1p0` | relaxed | 782 | 0.136 | prefix jerk | 0.640 | 0.198 | +0.062 | 0.717 | fail |
| `k16_noise0p75` | balanced | 615 | 0.153 | prefix jerk | 0.672 | 0.235 | +0.082 | 0.702 | fail |
| `k16_noise0p75` | relaxed | 1,360 | 0.174 | H3 rollout jerk | 0.607 | 0.232 | +0.058 | 0.578 | fail |

The table reports the best descriptor by failure-tick AUC/lift summary. The
success rate is posterior joint-comfort success among failure-tick admissible
candidates; in these audited failure ticks posterior jerk success and posterior
joint-comfort success have the same counts.

Interpretation:

1. Prefix jerk is the strongest current descriptor in most screens, and K16
   improves its ranking signal over K=8. The best AUC is `0.705` on
   `k16_noise1p0` balanced.
2. The signal is still too weak for an industrial online guard. The strongest
   precision lift is only `+0.082`, well below the predeclared `+0.15` gate.
   High recall comes mostly from broad nonworse coverage, not from strong
   separation.
3. Raw DP prior jerk has no discriminative value under the audited screens:
   because balanced/relaxed screens already require raw jerk nondegradation,
   raw jerk nonworse predicts every candidate and has AUC `0.5`.
4. Tracker-command jerk and H3 rollout jerk are not consistently calibrated.
   They sometimes improve coverage but do not provide enough precision lift to
   justify an online guard or atom.

Decision: reject current raw/tracker/prefix/H3 jerk descriptors as online
guards or CAMP atoms. Do not run replay, formal seeds, online selector wiring,
CAMP retraining, or DP retraining from this calibration. The next admissible
step is to examine richer current-tick descriptors that are still finite and
outcome-free, such as multi-horizon PerfectTracker rollout jerk/lateral
features already present in the logs, and test whether they improve
calibration without changing DP or the CAMP convex master contract.

### Expanded multi-horizon rollout calibration

Commit `e8c59e010f4504f4a7c81e3c51372ba1f20f0652` extends the calibration
audit to the existing PerfectTracker open-loop rollout descriptors at horizons
`3`, `5`, and `10`: mean/max vector jerk and mean/max lateral acceleration.
These fields were already present in the stored logs, so this extension does
not modify DP, rerun replay, train CAMP, or add online logic.

The mathematical boundary is unchanged. The expanded descriptors are
current-tick finite candidate constants. If later atomized, fixed-candidate
CAMP scoring remains affine in `w` and compatible with the simplex/CVaR/L2
convex master. This is still not Benders and makes no trajectory-coordinate
convexity claim.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_jerk_descriptor_calibration.py
1 passed

python -m pytest camp_core
218 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_jerk_descriptor_calibration.py
1 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
223 passed
```

AutoDL was synchronized by git bundle. CAMP local/GitHub/AutoDL reached
`e8c59e010f4504f4a7c81e3c51372ba1f20f0652`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The expanded calibration commands were the same as above, writing distinct
`*_jerk_descriptor_calibration_expanded.{json,md}` artifacts.

Final expanded artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Expanded calibration analyzer | `b101daf9a23a3f4957176834c35d907c08470692225bb9cae486852df434619c` |
| Expanded calibration tests | `2c0f65493ccffceea409d1d3122e73c117118dc902a8aba2e816a7af7566cd0d` |
| K=8 expanded calibration JSON | `a347f4e116f2dc7569d8b5320ec22998db618b7bbffe90999299df01120864c4` |
| K=8 expanded calibration markdown | `996d2a72e3e7ae09d4b1b9cffdc8478d9b856d9efc672a8750f8a49ece87f78a` |
| `k16_noise1p0` expanded calibration JSON | `08807d5732e60b355f19118c73422e6358bbff2032157940d574ed10cea11cd9` |
| `k16_noise1p0` expanded calibration markdown | `12557334783dc5456bf3ef804b7186993abce1ea277d55a5ff5b6b9dd2ba27d2` |
| `k16_noise0p75` expanded calibration JSON | `3fd6ba769cbcb0f16e3a7804f392a5657eaad6602c7d527a7596bb48100b1ffc` |
| `k16_noise0p75` expanded calibration markdown | `4655e7f226fd065386b5d0e5e0de2f0f933fa39fd91fa4bf251fb28e9117300d` |

Expanded failure-tick calibration results:

| Candidate set | Screen | Candidate rows | Best descriptor | AUC | Precision | Lift | Recall | Gate |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| K=8 | balanced | 275 | prefix jerk | 0.603 | 0.118 | +0.023 | 0.615 | fail |
| K=8 | relaxed | 582 | prefix jerk | 0.578 | 0.116 | +0.020 | 0.571 | fail |
| `k16_noise1p0` | balanced | 396 | prefix jerk | 0.705 | 0.173 | +0.072 | 0.675 | fail |
| `k16_noise1p0` | relaxed | 782 | prefix jerk | 0.640 | 0.198 | +0.062 | 0.717 | fail |
| `k16_noise0p75` | balanced | 615 | prefix jerk | 0.672 | 0.235 | +0.082 | 0.702 | fail |
| `k16_noise0p75` | relaxed | 1,360 | H10 mean vector jerk | 0.612 | 0.242 | +0.068 | 0.595 | fail |

The best added rollout descriptors were close but still below the gate. For
example, `k16_noise1p0` balanced H10 mean vector jerk reached AUC `0.661` and
precision lift `+0.054`; `k16_noise0p75` relaxed H10 mean vector jerk reached
AUC `0.612` and precision lift `+0.068`. These are improvements over some H3
metrics but remain far below the `+0.15` precision-lift requirement.

Interpretation:

1. Multi-horizon rollout jerk features add signal but do not change the
   industrial decision. No descriptor passes the calibration gate on any
   required screen.
2. Lateral rollout descriptors do not become the best calibrated predictors in
   the failure-tick summaries. The limiting factor remains weak mapping from
   current-tick descriptors to posterior joint-comfort success.
3. The expanded audit further supports rejecting scalar guard/atom changes
   based only on these rollout descriptors.

Decision: reject current multi-horizon rollout jerk/lateral descriptors as
online guards or CAMP atoms. Do not run replay, formal seeds, online selector
wiring, CAMP retraining, or DP retraining from this evidence. The next
admissible step is not another scalar jerk descriptor; it is to inspect whether
candidate-set structure itself is missing behavior diversity, for example by
auditing endpoint/lane-relative/spatial spread and mode coverage in the fixed
candidate set using current-tick quantities only.

### Candidate spatial diversity audit

Commits:

- `7a8deccf11c3d4f04ffa63541844286a060d95ad` adds a current-tick spatial
  diversity audit for bounded-selector posterior failure ticks.
- `d6a6b982864cf5d59abc1d0957081418dd9c7756` refines the evidence split into
  relative with-success/without-success bottleneck evidence and absolute
  low-diversity evidence.

The audit uses only the stored
`candidate_perfect_tracker_postprocessed_reference_prefix` for current-tick
endpoint descriptors. For each bounded-screen posterior failure tick, it
computes admissible candidate count, endpoint pairwise spread, lateral and
longitudinal endpoint ranges in the selected candidate's local frame, path
length range, heading range, and a simple endpoint mode count. Posterior
outcomes only split failure ticks by whether any admissible posterior-success
candidate existed.

This is a finite-candidate diagnostic, not an online selector. Endpoint and
mode descriptors are fixed current-tick candidate constants. If later atomized,
fixed-set CAMP scoring remains affine in `w` and compatible with the
simplex/CVaR/L2 convex master. This audit is not Benders and makes no
trajectory-coordinate convexity claim.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_candidate_spatial_diversity.py
1 passed

python -m pytest camp_core
219 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_candidate_spatial_diversity.py
1 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
224 passed
```

AutoDL was synchronized by git bundle. CAMP local/GitHub/AutoDL reached
`d6a6b982864cf5d59abc1d0957081418dd9c7756`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The spatial audit commands were:

```bash
K8=/root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc
K16A=/root/autodl-tmp/camp_dp_candidate_availability_k16_noise1p0_2212309
K16B=/root/autodl-tmp/camp_dp_candidate_availability_k16_noise0p75_2212309

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_candidate_spatial_diversity.py \
  --root "$K8" --label k8_baseline \
  --output_json "$K8/k8_baseline_candidate_spatial_diversity_v2.json" \
  --output_md "$K8/k8_baseline_candidate_spatial_diversity_v2.md"

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_candidate_spatial_diversity.py \
  --root "$K16A" --label k16_noise1p0 \
  --output_json "$K16A/k16_noise1p0_candidate_spatial_diversity_v2.json" \
  --output_md "$K16A/k16_noise1p0_candidate_spatial_diversity_v2.md"

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_candidate_spatial_diversity.py \
  --root "$K16B" --label k16_noise0p75 \
  --output_json "$K16B/k16_noise0p75_candidate_spatial_diversity_v2.json" \
  --output_md "$K16B/k16_noise0p75_candidate_spatial_diversity_v2.md"
```

Final artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Spatial diversity analyzer | `3ea4f2b177f54e412e4b836e67aa366df663d9f8ce58658837c65e9d253d90ac` |
| Spatial diversity tests | `133f732df34c086dd7044d9e1ab9f5f6b5dfa4bc093d0f4b5d0454759825a5a3` |
| K=8 spatial JSON | `af58bb982a43d9e8a162c2c3e31f7d1d541a105313a251d6514ffd53d9d6cf7c` |
| K=8 spatial markdown | `0ee20c3c68c1b5e7f747bd21cca29216a3f3f678fd78913488dfb37fa6d11eeb` |
| `k16_noise1p0` spatial JSON | `747a387ead1d5d150c8974a777201b1dce1747ac5d19ed5b1360a90a0a336fbc` |
| `k16_noise1p0` spatial markdown | `df839036173d83df03cf9a11f524ae8e27ea612017c560f6b65ae75631492264` |
| `k16_noise0p75` spatial JSON | `91c53ad9404029d3164b7cdbee5d46db57cbff2b3abfba3e2e9dcc366a0752e1` |
| `k16_noise0p75` spatial markdown | `102e043d544fcce6e58e94dc9b0bc32e455ec33e8f8aa7ceb87c3edba186af94` |

Spatial failure-tick results:

| Candidate set | Screen | Failure ticks | With success | Mode count | Endpoint pairwise mean | Lateral range | Admissible count | Evidence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| K=8 | balanced | 174 | 19 | 1.000 | 0.006 m | 0.003 m | 1.580 | global low |
| K=8 | relaxed | 303 | 46 | 1.000 | 0.013 m | 0.005 m | 1.921 | global low |
| `k16_noise1p0` | balanced | 191 | 24 | 1.000 | 0.009 m | 0.006 m | 2.073 | global low |
| `k16_noise1p0` | relaxed | 266 | 59 | 1.000 | 0.018 m | 0.007 m | 2.940 | global low |
| `k16_noise0p75` | balanced | 253 | 50 | 1.000 | 0.009 m | 0.005 m | 2.431 | global low |
| `k16_noise0p75` | relaxed | 394 | 117 | 1.000 | 0.019 m | 0.007 m | 3.452 | global low |

Interpretation:

1. The simple spatial-mode count is `1.0` for every audited failure group.
   Under the predeclared `0.25 m` lateral/longitudinal endpoint thresholds, the
   bounded admissible candidates do not form distinct endpoint modes.
2. K16/noise increases the number of admissible alternatives, but those
   alternatives remain tiny perturbations of the same endpoint mode. The
   average endpoint pairwise spread is still only about `0.009-0.019 m`, and
   the lateral range is only about `0.005-0.007 m`.
3. With-success failure ticks do have slightly larger spread than without-
   success ticks, but the relative gap is far below the predeclared split
   thresholds. The stronger finding is global low endpoint diversity, not a
   separable online spatial guard.
4. This supports the candidate-generation bottleneck hypothesis more directly
   than the scalar jerk descriptor audits: the fixed DP generator is mostly
   producing same-mode local variants, so CAMP has little finite-set support
   for industrially meaningful behavior selection.

Decision: reject using these endpoint descriptors as an online guard or CAMP
atom. Do not run replay, formal seeds, online selector wiring, CAMP retraining,
or DP retraining from this evidence. The next admissible step is to inspect
fixed-DP generator sampling controls or logged candidate-generation metadata to
find whether endpoint/mode spread can be increased while keeping DP weights
fixed and reporting the change strictly as a finite candidate-set change.

### Candidate generation metadata contract

Commit `bedc0b605911e30a5df4beb076d89d9ad1d85009` records an explicit
candidate-generation contract in new replay outputs. This is a logging-only
change: it does not alter Diffusion Planner, CAMP weights, the atom schema, the
selector, feasibility, or the generated candidates.

Read-only inspection of the fixed Diffusion Planner checkout found:

- the official parameter file
  `/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json` uses
  `diffusion_model_type=x_start`, `future_len=80`,
  `predicted_neighbor_num=320`, and `guidance_scale=0.5`;
- the decoder inference path uses DPM-Solver with `steps=10` and
  `skip_type=logSNR`;
- Diffusion Planner contains classifier-guidance and prototype/anchor
  guidance machinery, but the CAMP candidate path currently disables
  `decoder._guidance_fn` during candidate generation;
- the existing K8/K16 logs record `num_candidates` per selection record and
  `candidate_noise_scale` in replay summaries, but not enough per-record
  sampling contract metadata to audit future candidate-set changes.

The new `candidate_generation_contract` is written to:

1. `camp_selection_log.json` records;
2. `camp_replay_summary.json`;
3. microbenchmark snapshot metadata; and
4. resummarized validation output via
   `summarize_diffusion_planner_camp_replay.py`.

The contract fields include the fixed DP model type, latent shape, latent
distribution (`standard_normal_scaled`), noise scale, deterministic candidate
0, reference-blend steps, disabled guidance policy, DPM solver step count,
DPM skip type, RNG scope, and explicit flags stating that this changes only the
finite candidate set, not CAMP scoring or DP weights. Per-tick seeds are not
invented: the replay path uses the process-global Torch RNG, so
`recorded_tick_seed` is `null`. The microbenchmark snapshot keeps its existing
repeatability seed but now marks it as
`microbenchmark_replay_only_not_original_tick_rng`.

Mathematical boundary:

- This is metadata only and has no selection effect.
- If a later experiment changes latent sampling, reference blending, or
  guidance, it must be reported as a change to the finite candidate set.
- For any fixed candidate set, CAMP scoring remains affine in `w`; the
  simplex/CVaR/L2 master remains convex.
- Guidance/prototype steering, if used later, is not Benders and should not be
  described as a convex trajectory-coordinate guarantee.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_replay_summary.py
3 passed

python -m pytest \
  camp_core/tests/test_diffusion_planner_replay_summary.py \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_benchmark_matrix.py
11 passed

python -m pytest camp_core
220 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_replay_summary.py \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_benchmark_matrix.py
11 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
225 passed
```

Decision: accept the metadata-contract patch as an auditability prerequisite.
Do not run formal seeds, online selector wiring, CAMP retraining, or DP
retraining from this change alone. The next admissible experiment is a
predeclared, non-formal candidate-set diagnostic that either uses this contract
to compare generator settings, or explicitly rejects settings that cannot be
described as finite candidate-set changes under fixed DP weights.

### Candidate generation controls audit

Commit `c896b3de2279fec6b69fded5bc53f81e21140c20` adds a static audit tool
for fixed-DP candidate generation controls:

```bash
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_candidate_generation_controls.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --num_candidates 8 \
  --candidate_noise_scale 1.0 \
  --output_json \
    /root/autodl-tmp/camp_dp_candidate_generation_controls_c896b3d/candidate_generation_controls.json \
  --output_md \
    /root/autodl-tmp/camp_dp_candidate_generation_controls_c896b3d/candidate_generation_controls.md
```

This audit does not execute Diffusion Planner and does not change any
candidate, weight, atom, selector, or replay artifact. It reads the fixed DP
checkout, official model parameter JSON, and CAMP runner source to determine
which candidate-generation controls are available and which are currently
disabled.

Verification:

```text
python -m pytest \
  camp_core/tests/test_diffusion_planner_candidate_generation_controls.py \
  camp_core/tests/test_diffusion_planner_replay_summary.py
5 passed

python -m pytest camp_core
222 passed, 5 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_candidate_generation_controls.py \
  camp_core/tests/test_diffusion_planner_replay_summary.py
5 passed
```

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Controls JSON | `8b4176f131a1f2eb4290cd9d49baf7684ee46f222335516b38b3587dd23705fe` |
| Controls markdown | `bf78598a15d11ff5744c7a68111c5d4fd6d244ee3f2afc0244c9c42a677f1905` |

Key findings:

| Item | Finding |
| --- | --- |
| CAMP commit | `c896b3de2279fec6b69fded5bc53f81e21140c20` |
| DP commit | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| DP model type | `x_start` |
| Future length / neighbors | `80` / `320` |
| Decoder sampler | DPM-Solver `steps=10`, `skip_type=logSNR` |
| Current CAMP candidate path | disables and restores `decoder._guidance_fn` |
| Current candidate variables | `num_candidates`, `candidate_noise_scale`, `candidate_reference_blend_steps` |
| Official guidance availability | `11` registered guidance functions, GuidanceComposer and legacy wrapper present |
| Prototype support | `anchor_following.py` and `sampling/build_prototypes.py` present |
| Audit decision | `predeclare_default_off_guidance_candidate_set_diagnostic` |

Mathematical boundary:

1. This audit is source/metadata inspection only and has no selection effect.
2. Enabling official DP guidance later would be a generator-side finite
   candidate-set change under fixed DP weights, not a CAMP atom change.
3. For a fixed generated candidate set, CAMP scoring remains affine in `w` and
   the simplex/CVaR/L2 master remains convex.
4. DP guidance/prototype steering is not Benders and gives no global convexity
   guarantee in trajectory coordinates.

Predeclared next gate:

- Any guidance/prototype diagnostic must be default-off and metadata-logged.
- It must not modify DP source or DP weights.
- It must not train CAMP or change CAMP atom schema.
- It must run only non-formal sample59 paired seeds before any formal seed.
- It must compare against the current K8 baseline and rejected K16/noise
  evidence.
- It must reject unless endpoint/mode spread and outcome-free availability
  improve without comfort or latency regressions.
- A single global guidance config is not assumed to create behavior modes; if
  used, it must be evaluated as a finite candidate-set variant, and if it
  collapses candidates further it is rejected.

Decision: accept the controls audit and predeclare the guidance/prototype
candidate-set branch as the next possible diagnostic. Do not run it until a
default-off implementation records the guidance contract in every replay
summary and selection record.

### Default-off DP guidance candidate diagnostic entrance

Commit `3de947e4994819b3ec8f498340e4d230496b1242` implements the
predeclared default-off entrance for official Diffusion Planner guidance during
CAMP candidate generation. The default remains unchanged: candidate generation
clears `decoder._guidance_fn`, runs without gradients, and restores the decoder
state after the batched forward pass. The explicit diagnostic path is enabled
only by providing `--candidate_guidance_config`; then the runner installs the
official `GuidanceComposer`, preserves that guidance during candidate
generation, and records the guidance contract in replay summary metadata,
selection records, and microbenchmark snapshots.

CLI and wrapper controls:

```text
--candidate_guidance_config PATH
--candidate_guidance_scale FLOAT
CANDIDATE_GUIDANCE_CONFIG=...
CANDIDATE_GUIDANCE_SCALE=...
```

The guidance contract records whether guidance is enabled, the policy string,
config path, config SHA-256, active guidance functions, and effective guidance
scale. The wrapper fails closed if a configured guidance file is missing, and
the replay parser rejects a scale override without a guidance config.

Mathematical boundary:

1. This is a finite candidate-set diagnostic under fixed DP source, fixed DP
   weights, fixed CAMP atom schema, and fixed CAMP weights.
2. For any realized finite candidate set, CAMP scoring remains affine in `w`;
   the simplex/CVaR/L2 master remains convex.
3. The official DP guidance composer is generator-side logic. It is not a CAMP
   atom, not a Benders subproblem, and does not justify a global convexity claim
   in trajectory coordinates.
4. Formal seeds remain frozen. This change alone does not authorize a new
   online selector, CAMP retraining, DP retraining, or formal replay.

Verification:

```text
python -m pytest camp_core
224 passed, 8 skipped

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
232 passed
```

Implementation checkpoint verified before this documentation update:

| Location | State |
| --- | --- |
| Local CAMP | `3de947e4994819b3ec8f498340e4d230496b1242` |
| GitHub `main` | `3de947e4994819b3ec8f498340e4d230496b1242` |
| AutoDL CAMP | `3de947e4994819b3ec8f498340e4d230496b1242` |
| AutoDL DP | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |

Decision: accept the default-off guidance diagnostic entrance as an
auditability and experimentation prerequisite. The next admissible step is to
define one concrete non-formal guidance config, run only sample59 paired seeds,
and reject the branch unless endpoint/mode spread and outcome-free availability
improve without comfort, fallback, or latency regression.

### Guidance scale contract correction

Commit `e8cfacb025f83a8b24f19c74f34f9f2b8268a147` corrects the execution
contract for candidate guidance configs. TiER IV Diffusion Planner stores the
classifier-guidance multiplier on `model.decoder._guidance_scale`; the
serialized `GuidanceSetConfig.global_scale` is not consumed by
`GuidanceComposer` itself. Therefore a CAMP diagnostic that records
`global_scale` but leaves the decoder at an unrelated previous value is not
reproducible.

The runner now applies the following deterministic scale policy whenever
`--candidate_guidance_config` is provided:

1. If `--candidate_guidance_scale` is provided, it overrides the config and is
   recorded with `guidance_scale_source="cli_override"`.
2. Otherwise, `GuidanceSetConfig.global_scale` is copied into
   `model.decoder._guidance_scale` and recorded with
   `guidance_scale_source="config_global_scale"`.
3. Non-finite config, CLI, or effective scales fail closed before replay.

This does not change the default path: without `--candidate_guidance_config`,
CAMP candidate generation still disables DP guidance and the summary records
`guidance_enabled=false`. The correction only makes the explicit default-off
diagnostic path internally consistent.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_replay_summary.py
7 passed

python -m pytest \
  camp_core/tests/test_diffusion_planner_replay_summary.py \
  camp_core/tests/test_diffusion_planner_integration.py \
  camp_core/tests/test_diffusion_planner_component_benchmark.py
111 passed, 8 skipped

python -m pytest camp_core
226 passed, 8 skipped
```

Decision: accept this as a reproducibility fix before any guidance candidate-set
replay. The next diagnostic config should prefer official guidance functions
whose inputs already exist in the DP replay tensors, such as
`route_centerline_following` and possibly `lane_keeping`; avoid anchor,
prototype, lateral, or longitudinal guidance until their additional reference
or mode-selection semantics are explicitly defined.

### Predeclared route-lane guidance config

Commit `ffd4a16e5212e515e6807b8fb993d79a4351e04e` adds the first concrete
default-off guidance candidate-set diagnostic config:

```text
configs/integrations/dp_candidate_guidance_route_centerline_lane.json
```

Config SHA-256:

```text
aaff213cd12c845f98ec8997a09ec6641308ee0f0440f31c7ec06bb89cd8e456
```

The config is intentionally conservative:

```text
global_scale = 0.2
route_centerline_following scale = 0.5
lane_keeping scale = 0.25
```

Rationale:

1. Both functions are official TiER IV DP guidance functions registered by the
   fixed DP checkout.
2. Both consume tensors already present in the replay inputs
   (`route_lanes`, `lanes`, and `ego_shape`), so no new policy, prototype, or
   reference trajectory semantics are introduced.
3. The config changes only the finite candidate set generated by fixed DP
   weights. It does not change CAMP atoms, CAMP weights, the CAMP master, or
   default replay behavior.
4. A single route/lane guidance config is not assumed to improve modal
   diversity; it may collapse candidates. That outcome is admissible only as a
   diagnostic and must be rejected if availability, comfort, or latency gates
   regress.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_guidance_configs.py \
  camp_core/tests/test_diffusion_planner_replay_summary.py
8 passed

python -m pytest camp_core
227 passed, 8 skipped

# AutoDL official DP loader check
active_function_names = ["route_centerline_following", "lane_keeping"]
composer_type = "GuidanceComposer"
global_scale = 0.2
guidance_scale = 0.2
guidance_scale_source = "config_global_scale"

/root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core
235 passed
```

Predeclared next gate:

1. Run a one-seed, short-step smoke with `CANDIDATE_GUIDANCE_CONFIG` pointing
   to this file, `formal seeds` still frozen.
2. Confirm replay summary and selection records include the exact config SHA
   and `guidance_scale_source`.
3. If smoke is numerically valid, run paired sample59 seeds only as a
   non-formal diagnostic.
4. Compare against the frozen K8 baseline availability report and rejected
   K16/noise evidence.
5. Reject unless outcome-free availability and candidate spatial/endpoint
   spread improve without comfort, fallback, or p95 latency regression.

### Route-lane guidance smoke rejection

The predeclared route-lane guidance config was evaluated in a matched
one-seed, three-step, non-formal smoke on AutoDL:

```text
Baseline:
/root/autodl-tmp/camp_dp_guidance_route_lane_smoke_baseline_seed101_219e9f6

Route-lane guidance:
/root/autodl-tmp/camp_dp_guidance_route_lane_smoke_seed101_219e9f6

Comparison:
/root/autodl-tmp/camp_dp_guidance_route_lane_smoke_comparison_219e9f6
```

Both runs used fixed DP commit `7a1d33da277a1992ec474b5383a0c963c72e04e4`,
fixed CAMP commit `219e9f6d761766609c12e26893cf1e0b1beb0313`, K=8, noise
scale 1.0, the sample59 traffic-light route, seed 101, no NPCs, perfect
tracking, redstopfloor05 static weights, and no formal seeds. The route-lane
run recorded the expected guidance contract in both the replay summary and all
selection records:

```text
config_sha256 = aaff213cd12c845f98ec8997a09ec6641308ee0f0440f31c7ec06bb89cd8e456
active_function_names = ["route_centerline_following", "lane_keeping"]
guidance_scale = 0.2
guidance_scale_source = "config_global_scale"
record_contract_variants = 1
```

Matched smoke deltas, route-lane guidance minus disabled-guidance baseline:

| Metric | Baseline | Route-lane guidance | Delta |
| --- | ---: | ---: | ---: |
| Candidate feasible rate | 0.500000 | 0.416667 | -0.083333 |
| Mean feasible candidates | 4.000000 | 3.333333 | -0.666667 |
| p95 candidate-generation latency | 59.745 ms | 184.670 ms | +124.925 ms |
| p95 selection latency | 261.173 ms | 349.298 ms | +88.125 ms |
| Fallback rate | 0.000000 | 0.000000 | 0.000000 |
| Route progress | 0.955171 m | 0.924882 m | -0.030289 m |
| Planned lane-violation rate | 0.333333 | 0.333333 | 0.000000 |
| Planned red-light violation rate | 0.000000 | 0.000000 | 0.000000 |

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Smoke comparison JSON | `aa29da128df44ef29bb9897d3144b3f464e447f54b884a7d61ff4caae4ae13f0` |
| Smoke comparison markdown | `d4f34859794c29f40f37faf8bb6609233116b1e6df3004e4e02e34417eb76a15` |

Decision: reject this concrete route-centerline + lane-keeping guidance config
before any sample59 paired run. The branch is numerically valid and
metadata-complete, but it fails the smoke gate because it reduces candidate
feasibility and adds large latency in the candidate generator. This is still a
finite candidate-set diagnostic under fixed DP weights; it does not invalidate
the CAMP affine/simplex/CVaR/L2 mathematical boundary. The next candidate-set
idea must address DP guidance runtime cost or use a different generator-side
mechanism; do not expand this config to 12-run or formal seeds.

### Antithetic latent sampling diagnostic predeclaration

The next low-cost candidate-set diagnostic is default-off antithetic latent
sampling. The historical default remains `--candidate_noise_strategy iid`. The
new diagnostic mode is `--candidate_noise_strategy antithetic`, which keeps
candidate 0 deterministic and pairs subsequent stochastic latents as `+z/-z`
inside the same batched DP forward pass. If the stochastic count is odd, the
last stochastic candidate remains an unpaired iid draw.

Mathematical boundary:

1. DP weights, CAMP atoms, CAMP weights, CAMP feasibility policy, CAMP affine
   score, and the simplex/CVaR/L2 master are unchanged.
2. Antithetic sampling only changes the finite candidate set observed at a
   fixed tick. Once the candidate set is realized, candidate diagnostics are
   fixed finite values and the CAMP score remains affine in the CAMP weights.
3. This is not a Benders decomposition change, does not add a valid master /
   subproblem pair or cuts, and makes no global convexity claim over trajectory
   coordinates.
4. The intended industrial test is latency-neutral diversity: it must not add
   DP guidance backward-pass cost or additional DP forwards.

Implementation gate:

```text
python -m pytest camp_core/tests/test_diffusion_planner_integration.py \
  camp_core/tests/test_diffusion_planner_replay_summary.py \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_candidate_generation_controls.py

python -m pytest camp_core

git diff --check
```

Non-formal AutoDL smoke gate, if local tests pass:

1. Rerun a matched iid baseline and antithetic run at the same CAMP commit,
   seed 101, sample59 traffic-light route, K=8, three steps, no NPCs, perfect
   tracking, and redstopfloor05 static weights.
2. Confirm summaries and selection records record `noise_strategy` and the
   latent pairing contract.
3. Reject unless feasibility, selected safety metrics, fallback rate, and p95
   latency are at least non-regressing. Treat any improvement as diagnostic
   only; do not use formal seeds or retrain CAMP weights.

### Antithetic latent sampling smoke rejection

The predeclared antithetic sampling diagnostic was evaluated in a matched
one-seed, three-step, non-formal smoke on AutoDL:

```text
Baseline iid:
/root/autodl-tmp/camp_dp_antithetic_smoke_iid_seed101_78900038_20260616165908

Antithetic:
/root/autodl-tmp/camp_dp_antithetic_smoke_seed101_78900038_20260616165908

Comparison:
/root/autodl-tmp/camp_dp_antithetic_smoke_comparison_78900038_20260616165908
```

Both runs used fixed DP commit `7a1d33da277a1992ec474b5383a0c963c72e04e4`,
fixed CAMP commit `789000386f76ec6c75e933515611ac129020148b`, K=8, noise
scale 1.0, the sample59 traffic-light route, seed 101, no NPCs, perfect
tracking, redstopfloor05 static weights, and no formal seeds.

The metadata gate passed: the replay summaries and selection records recorded
the expected candidate-generation contract variants:

```text
iid noise_strategy = iid
iid latent_pairing = independent iid draws after deterministic candidate 0
antithetic noise_strategy = antithetic
antithetic latent_pairing = +z/-z antithetic pairs after deterministic candidate 0; one unpaired iid draw if stochastic count is odd
record_contract_variants = 1 for both runs
```

Matched smoke deltas, antithetic minus iid:

| Metric | iid | antithetic | Delta |
| --- | ---: | ---: | ---: |
| Candidate feasible rate | 0.500000 | 0.416667 | -0.083333 |
| Mean feasible candidates | 4.000000 | 3.333333 | -0.666667 |
| p95 candidate-generation latency | 59.432 ms | 59.911 ms | +0.479 ms |
| p95 selection latency | 261.251 ms | 266.246 ms | +4.995 ms |
| Fallback rate | 0.000000 | 0.000000 | 0.000000 |
| Route progress | 0.955171 m | 1.085566 m | +0.130395 m |
| Planned lane-violation rate | 0.333333 | 0.000000 | -0.333333 |
| Planned red-light violation rate | 0.000000 | 0.000000 | 0.000000 |
| Mean jerk magnitude | 305.513 m/s^3 | 374.011 m/s^3 | +68.499 m/s^3 |
| Mean lateral acceleration | 0.342090 m/s^2 | 0.065431 m/s^2 | -0.276659 m/s^2 |
| Minimum road-border clearance | 1.160821 m | 1.093167 m | -0.067655 m |

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Smoke comparison JSON | `3f8e30e061aa0b0e2d2d4274b59eab0d8c8e9e79b4b43ad89dedc3830cbfd60e` |
| Smoke comparison markdown | `7ea67deba93809eca777df84c5ce54badb8d87cc8e8cf2658d8151683b2fce1f` |
| Strict replay comparison JSON | `eeb2d4699a231361429c489b57d9945cbd89a4bdac31c7eb577571a901f5d19a` |
| Strict replay comparison markdown | `7dde84bfb8268a6b4e699ed33dfd9400de3cc0e4ef8ef29bcb946733a2c7a6fe` |

Decision: reject default-off antithetic latent sampling before any sample59
paired run. It is numerically valid and metadata-complete, and it does not
alter DP weights or CAMP's affine/simplex/CVaR/L2 mathematical boundary.
However, it fails the predeclared smoke gate because candidate feasibility
regresses and both p95 candidate-generation and p95 selection latency increase.
The route-progress and planned-lane improvements are not sufficient to override
the feasibility and latency regressions. Do not expand this branch to formal
seeds, online selection, or CAMP retraining.

### Anchor-following progress-mode guidance predeclaration

After rejecting K16/noise, route/lane guidance, and antithetic latent sampling,
the only remaining official DP guidance path with a plausible progress
preservation story is `anchor_following`: it is registered in the fixed DP
checkout and does not require adding `reference_trajectory` to replay inputs.
Its energy softly attracts the generated ego trajectory to one precomputed
prototype trajectory. This branch still uses the official `GuidanceComposer`,
so the expected risk is the same guidance backward-pass latency that rejected
the route/lane config.

Read-only prototype audit:

```text
/root/autodl-tmp/Diffusion-Planner/rlvr/prototypes_k16.npy
shape = (16, 80, 2)
chosen anchor_index = 15
final_x = 25.350845 m
final_y = 1.946983 m
path_length = 25.192469 m
max_abs_y = 1.946984 m
```

This is the most forward low-lateral prototype in the `rlvr` prototype set.
The farther `rlvr` index 14 has `final_y = 9.156084 m`, so it is a stronger
lateral-mode intervention rather than a progress-preserving smoke. The
`guidance_gui` prototype file contains more aggressive 50-70 m forward anchors
and is not used for this minimal gate.

Predeclared config content for the AutoDL smoke:

```json
{
  "global_scale": 0.2,
  "functions": [
    {
      "name": "anchor_following",
      "enabled": true,
      "scale": 0.5,
      "params": {
        "prototypes_path": "/root/autodl-tmp/Diffusion-Planner/rlvr/prototypes_k16.npy",
        "anchor_index": 15
      }
    }
  ]
}
```

Gate:

1. Run only a matched one-seed, three-step, non-formal smoke against the same
   iid baseline pattern: sample59 traffic-light route, seed 101, K=8, no NPCs,
   perfect tracking, redstopfloor05 static weights, and no formal seeds.
2. Confirm replay summaries and selection records record the exact guidance
   config SHA, `active_function_names = ["anchor_following"]`, and the disabled
   CAMP/DP weight-change flags.
3. Reject unless feasibility, selected safety metrics, fallback rate, route
   progress, and p95 latency are all non-regressing. Because route/lane guidance
   already failed latency, any p95 candidate-generation or selection regression
   is sufficient to reject this branch before sample59 paired runs.
4. Treat the result strictly as a fixed-DP finite candidate-set diagnostic. It
   is not a CAMP atom, not Benders, and does not imply trajectory-coordinate
   convexity.

### Anchor-following progress-mode guidance smoke rejection

The predeclared anchor-following guidance smoke was evaluated in a matched
one-seed, three-step, non-formal smoke on AutoDL:

```text
Baseline iid:
/root/autodl-tmp/camp_dp_anchor_guidance_iid_seed101_6a039c03_20260616171128

Anchor-following guidance:
/root/autodl-tmp/camp_dp_anchor_guidance_seed101_6a039c03_20260616171128

Comparison:
/root/autodl-tmp/camp_dp_anchor_guidance_comparison_6a039c03_20260616171128
```

Both runs used fixed DP commit `7a1d33da277a1992ec474b5383a0c963c72e04e4`,
fixed CAMP commit `6a039c037ad66640846bd52473cb7f2590ee6314`, K=8, noise
scale 1.0, the sample59 traffic-light route, seed 101, no NPCs, perfect
tracking, redstopfloor05 static weights, and no formal seeds.

The metadata gate passed. The replay summary and selection records recorded:

```text
active_function_names = ["anchor_following"]
config_sha256 = 91696d7f7d5d5c92bcdbd955cb85ffd12249904c78818efc73cb2f0c23baf153
guidance_scale = 0.2
guidance_scale_source = config_global_scale
record_contract_variants = 1
changes_camp_score = false
changes_diffusion_planner_weights = false
```

Matched smoke deltas, anchor-following minus iid:

| Metric | iid | anchor-following | Delta |
| --- | ---: | ---: | ---: |
| Candidate feasible rate | 0.500000 | 0.583333 | +0.083333 |
| Mean feasible candidates | 4.000000 | 4.666667 | +0.666667 |
| p95 candidate-generation latency | 64.940 ms | 165.725 ms | +100.785 ms |
| p95 selection latency | 269.927 ms | 358.909 ms | +88.982 ms |
| Fallback rate | 0.000000 | 0.000000 | 0.000000 |
| Route progress | 0.955171 m | 0.896608 m | -0.058563 m |
| Planned lane-violation rate | 0.333333 | 0.333333 | 0.000000 |
| Planned red-light violation rate | 0.000000 | 0.000000 | 0.000000 |
| Mean jerk magnitude | 305.513 m/s^3 | 330.999 m/s^3 | +25.486 m/s^3 |
| Mean lateral acceleration | 0.342090 m/s^2 | 0.411980 m/s^2 | +0.069889 m/s^2 |
| Minimum road-border clearance | 1.160821 m | 1.192591 m | +0.031769 m |

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Anchor config JSON | `91696d7f7d5d5c92bcdbd955cb85ffd12249904c78818efc73cb2f0c23baf153` |
| Smoke comparison JSON | `52a0845f016eb505f13dbb02160b73e7a9d1dcedc3ce857b1b411aea5b78183f` |
| Smoke comparison markdown | `f0fc7301642d95312dbc26000cce9c1a3b48c96d51d918322c397c9161285884` |
| Strict replay comparison JSON | `d0e31571a2cdd091c0db985c21c4010663c9f0d90075fdb06bb24f5e376df7dd` |
| Strict replay comparison markdown | `622c3d0bee478622cf05d75e17101d288e7e9adcbb3207a2171d7e1005b4691b` |

Decision: reject anchor-following progress-mode guidance before any sample59
paired run. It is a valid fixed-DP finite candidate-set diagnostic and it
improves the three-step feasible-candidate rate, but it fails the predeclared
gate because route progress regresses and p95 latency increases sharply. It
also worsens realized mean jerk and mean lateral acceleration in this smoke.
Together with the route/lane guidance rejection, this closes the current
official `GuidanceComposer` branch as an industrial path under the p95 latency
gate. Do not expand this branch to formal seeds, online selection, or CAMP
retraining.

### Raw candidate prefix observability predeclaration

The next step is not a new selector, atom, weight vector, or candidate generator.
It closes an observability gap found after the materiality and projection
audits: existing `camp_selection_log.json` records preserve only
`candidate_first_reference_xy` from raw DP candidates plus the PerfectTracker
postprocessed prefix. They do not preserve enough raw DP candidate geometry to
audit future raw-geometry transforms or materiality claims from historical
artifacts.

The implementation is a default-off logging flag:

```text
--camp_log_raw_candidate_prefix_steps N
```

with default `N=0`. When enabled in a non-formal replay, each selection record
may include:

```text
candidate_raw_trajectory_prefix_steps
candidate_raw_trajectory_prefix
```

where the prefix has shape `K x min(N,T) x D` for the realized raw DP ego
candidate tensor before Savitzky-Golay smoothing, `postprocess_reference`, and
PerfectTracker command generation. In the current DP replay this state is
expected to be `[x, y, cos_yaw, sin_yaw]`.

Mathematical boundary:

1. This flag logs fixed finite candidate constants after candidate generation.
2. It does not change the finite candidate set, CAMP atom values, CAMP score,
   feasibility, selection, DP weights, CAMP weights, or tracker input.
3. If a future audit derives atoms from these logged constants, that atom must
   be separately defined and scaled. For fixed realized candidates, CAMP score
   can remain affine in `w`; the simplex/CVaR/L2 master remains convex only
   under that fixed-candidate interpretation.
4. Logging itself is not Benders, provides no master/subproblem dual cuts, and
   makes no global convexity claim over trajectory coordinates.

Verification gate for this observability milestone:

```text
python -m pytest camp_core/tests/test_diffusion_planner_replay_summary.py
bash -n scripts/integrations/run_diffusion_planner_camp_remote.sh
```

After local tests and a minimal commit, the only admissible remote check is a
short non-formal metadata smoke with `CAMP_LOG_RAW_CANDIDATE_PREFIX_STEPS=10`
on sample59 seed 101, no NPCs, K=8, perfect tracking, and redstopfloor05 static
weights. The smoke should verify field presence and shape, and should be
treated as logging validation only. It does not authorize a new 12/36-run,
formal seeds, online selector, DP retraining, or CAMP retraining.

### Raw candidate prefix observability smoke result

Commit `8b331f8b2db7d2d74bb64a1116b115cf95437fcb` implements the default-off
raw candidate prefix logger. The local/GitHub/AutoDL CAMP checkouts were
synchronized to this commit, and Diffusion Planner remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_replay_summary.py
12 passed

PYTHONPATH=... python -m pytest \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_candidate_generation_controls.py
8 passed

PYTHONPATH=... python -m pytest \
  camp_core/tests/test_diffusion_planner_integration.py \
  -k "summarize_replay_artifacts or train_diffusion_planner_static_camp_from_selection_log"
3 passed, 105 deselected

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_replay_summary.py
12 passed

PYTHONPATH=... /root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_candidate_generation_controls.py
8 passed

bash -n scripts/integrations/run_diffusion_planner_camp_remote.sh
passed
```

The non-formal metadata smoke ran at:

```text
/root/autodl-tmp/camp_dp_raw_prefix_smoke_seed101_8b331f8
```

It used sample59 seed 101, K=8, 3 steps, no NPCs, perfect tracking,
redstopfloor05 static weights, and
`CAMP_LOG_RAW_CANDIDATE_PREFIX_STEPS=10`. The smoke produced three selection
records. The first record's raw prefix shape was:

```text
8 x 10 x 4
```

Both `camp_replay_summary.json` and `camp_validation_summary.json` recorded:

```text
camp_raw_candidate_prefix_logging.enabled = true
camp_raw_candidate_prefix_logging.selection_effect = false
camp_raw_candidate_prefix_logging.steps = 10
camp_raw_candidate_prefix_logging.field = candidate_raw_trajectory_prefix
```

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Replay summary | `9269317a343dc62da0aa724d5679926b360c663948429e97d7df9dc9d311083f` |
| Validation summary | `bc269dda7944f505204af48b3a706fa8c2d70418c263957ec1fda070e50dabbc` |
| Selection log | `cacbd8aca90795c7b6ac0191b37bf641c28068126d632b17c9cb82ff8bebf849` |

Decision: accept this as an observability milestone only. It proves future
non-formal raw-geometry audits can inspect raw DP candidate prefixes without
changing the default replay path or CAMP mathematics. It does not prove an
improved selector, does not authorize formal seeds, and does not justify
claiming Benders structure or trajectory-coordinate convexity for any future
raw-geometry transform.

### Predeclared raw-vs-postprocessed prefix geometry audit

The next offline-only diagnostic uses the raw prefix fields introduced above to
answer one narrow observability question: how much of the raw DP candidate
geometry survives the Savitzky-Golay plus `postprocess_reference` path used by
PerfectTracker shadows?

Inputs:

```text
candidate_raw_trajectory_prefix
candidate_perfect_tracker_postprocessed_reference_prefix
```

Both are treated as fixed current-tick candidate constants. The audit compares
only xy geometry over the shared prefix horizon and reports:

1. candidate endpoint pairwise spread in raw and postprocessed prefixes;
2. mean pairwise prefix spread in raw and postprocessed prefixes;
3. candidate distance-to-selected spread in both representations;
4. raw-to-post displacement magnitude for all candidates and for the selected
   candidate;
5. compression rates where raw geometry is above 1 mm, 1 cm, or 10 cm but the
   postprocessed representation falls below the same threshold.

Mathematical boundary:

1. The audit does not use closed-loop outcomes or future labels.
2. It does not alter candidate generation, CAMP atoms, CAMP score, feasibility,
   selected trajectory, DP weights, CAMP weights, or tracker inputs.
3. If later atomized, each measured descriptor is a fixed finite-candidate
   constant at selection time; score can remain affine in `w` under that fixed
   candidate set, preserving the simplex/CVaR/L2 convex master.
4. This is not Benders and makes no global convexity claim over trajectory
   coordinates.

Acceptance gate for this diagnostic is modest: the tool must fail clearly when
raw prefixes are missing, pass unit tests on synthetic compressed geometry, and
run on the non-formal raw-prefix smoke artifact. The result can justify a later
predeclared raw-geometry transform audit, but cannot by itself authorize an
online selector, 12/36-run matrix, formal seeds, CAMP retraining, or DP
retraining.

### Raw-vs-postprocessed prefix geometry audit smoke result

Commit `6d5acc506401890c9de16ecb14ffd98f928bfd16` adds the offline
raw-prefix geometry analyzer. It is outcome-free, training-free, and reports
fixed finite-candidate geometry constants only.

Verification:

```text
python -m pytest camp_core/tests/test_diffusion_planner_raw_prefix_geometry.py
3 passed

python -m pytest camp_core/tests/test_diffusion_planner_replay_summary.py
12 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_raw_prefix_geometry.py
3 passed
```

The analyzer was run on the non-formal raw-prefix smoke artifact:

```text
Input:
/root/autodl-tmp/camp_dp_raw_prefix_smoke_seed101_8b331f8/camp_selection_log.json

Output:
/root/autodl-tmp/camp_dp_raw_prefix_geometry_audit_6d5acc5
```

This artifact has only three selection records, so it is a metadata/geometry
smoke, not a deployment conclusion. Within this smoke:

| Metric | Mean |
| --- | ---: |
| Raw endpoint pairwise spread | 0.395746 m |
| Postprocessed endpoint pairwise spread | 0.396521 m |
| Endpoint spread ratio post/raw | 1.002088 |
| Raw prefix pairwise spread | 0.208308 m |
| Postprocessed prefix pairwise spread | 0.208481 m |
| Prefix spread ratio post/raw | 1.000863 |
| Raw-to-post displacement mean | 0.002103 m |
| Raw-to-post displacement max | 0.006093 m |
| Raw/post selected-distance correlation | 0.999999 |

Compression rates were zero for the 1 mm, 1 cm, and 10 cm thresholds:

```text
endpoint_pairwise_mean_compression_rate = 0.0
prefix_pairwise_mean_compression_rate = 0.0
```

Decision: accept the analyzer as a valid diagnostic tool, but do not draw an
industrial conclusion from the three-record smoke. The smoke suggests that, at
least for these early sample59 ticks, SG plus `postprocess_reference` preserves
candidate spread almost exactly and adds only millimeter-scale displacement.
Therefore the earlier materiality loss is unlikely to be explained by generic
postprocessing compression in this tiny sample. The next admissible evidence
step is a predeclared larger non-formal raw-prefix logging pass or an
offline-only audit over any existing logs that already include raw prefixes.
It still does not authorize online selector changes, 12/36-run acceptance,
formal seeds, CAMP retraining, or DP retraining.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Raw prefix geometry JSON | `f798465e8d99f3329e12919fdd617a25a29b5b37e19d60fb9f75a527f4ef5c0b` |
| Raw prefix geometry markdown | `71543dbffdaa1b9ba146b484ed833980bcf7cb9ab158a625b6ba0d4ee742f9a5` |

### Raw-prefix logging benchmark-matrix scheduling support

The raw-prefix observability gate is clean enough to prepare the next
predeclared non-formal diagnostic pass, but the benchmark matrix entry point
must be able to schedule the already default-off replay logger. The matrix now
accepts `--camp_log_raw_candidate_prefix_steps` and forwards it only to CAMP
variants (`uniform`, `static`, and `theta`) when the value is positive. It is
not forwarded to `top1`, because the upstream baseline does not run the CAMP
candidate-selection path.

This is scheduling support only:

1. default remains `0`;
2. candidate generation, CAMP atoms, CAMP scores, selector behavior, DP
   weights, CAMP weights, and tracker inputs are unchanged;
3. the replay metadata keeps `selection_effect=false`;
4. the logged prefix remains a fixed finite-candidate diagnostic constant, not
   a Benders cut or an online selection rule.

Verification:

```text
py -3.12 -m py_compile scripts\integrations\run_diffusion_planner_camp_benchmark_matrix.py

py -3.12 -m pytest camp_core\tests\test_diffusion_planner_benchmark_matrix.py
3 passed

py -3.12 -m pytest camp_core\tests\test_diffusion_planner_replay_summary.py
12 passed
```

Decision: accept this as a narrow infrastructure milestone for the next
non-formal raw-prefix geometry audit. It does not authorize formal seeds,
online selector changes, CAMP retraining, DP retraining, or performance claims.

### Predeclared sample59 raw-prefix geometry diagnostic

The next raw-prefix audit is fixed before execution and remains diagnostic
only. It observes whether the three-record smoke result generalizes across the
existing non-formal sample59 static baseline grid. It does not tune a selector,
change candidate generation, change CAMP weights, change atom scales, retrain
CAMP, retrain DP, or use formal seeds.

| Parameter | Value |
| --- | --- |
| CAMP commit at predeclare | `e488ff842425cd6611f0c2bf5357e65d637fba04` |
| DP commit | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Route | `sample59_86` |
| Seeds | `1,2,3` |
| Maximum NPCs | `0,4` |
| Traffic lights | `off,on` |
| Spawn probability | `0.3` |
| Steps | `200` |
| Advance mode | `perfect` |
| Candidates | `8` |
| Candidate noise scale | `1.0` |
| CAMP variant | static `redstopfloor05` |
| Feasibility | DP reward, minimum progress ratio `0.8` |
| Reward horizon | `30` steps |
| All-infeasible fallback | `uniform` |
| Raw-prefix logging | `--camp_log_raw_candidate_prefix_steps 10` |

The new, non-overwriting output root is:

```text
/root/autodl-tmp/camp_dp_raw_prefix_sample59_static_e488ff8
```

The exact 12-command dry-run was persisted before execution at:

```text
/root/autodl-tmp/camp_dp_raw_prefix_sample59_static_e488ff8_predeclare.txt
```

Its SHA-256 is
`8fce3f077e359e12197f7c36007992a171041a93c5f734c4023c0f000ae7ea8b`.

Acceptance for this diagnostic is intentionally narrow:

1. all 12 static runs complete and each summary records
   `camp_raw_candidate_prefix_logging.selection_effect=false`;
2. every selection record contains a raw prefix with shape `8 x 10 x 4`;
3. `analyze_diffusion_planner_raw_prefix_geometry.py` runs over the root and
   reports only fixed finite-candidate geometry constants;
4. any conclusion is limited to raw-vs-postprocessed geometry materiality, not
   safety, comfort, latency, formal performance, Benders, or a new online
   selector.

Formal seeds `11/12/13` remain frozen.

### Sample59 raw-prefix geometry diagnostic result

The predeclared 12-run static `redstopfloor05` diagnostic completed under:

```text
/root/autodl-tmp/camp_dp_raw_prefix_sample59_static_e488ff8
```

Execution used the predeclared matrix from commit
`d94821328e5a034afa34d92c7ee6e1d4783ca42f`. The geometry analyzer was then
rerun after commit `74978a46e00cafc9bd190cd4109c85f4d3535d06`, which only adds
explicit `post - raw` delta metrics to the offline report.

The structural audit passed:

| Check | Result |
| --- | ---: |
| Selection logs | 12 |
| Validation summaries | 12 |
| Selection records | 2,400 |
| Missing raw prefixes | 0 |
| Raw prefix shape | `8 x 10 x 4` for all records |
| Postprocessed prefix shape | `8 x 10 x 3` for all records |
| Validation mode | `('static', 'perfect')` for all 12 runs |

The offline geometry output is:

```text
/root/autodl-tmp/camp_dp_raw_prefix_geometry_sample59_static_e488ff8
```

Key geometry summaries over all 2,400 records:

| Metric | Mean | Median | P95 | Min | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw endpoint pairwise spread | 0.098633 m | 0.074516 m | 0.280582 m | 0.008384 m | 0.648173 m |
| Post endpoint pairwise spread | 0.099000 m | 0.074766 m | 0.281348 m | 0.004427 m | 0.659115 m |
| Endpoint `post - raw` delta | +0.000368 m | -0.000013 m | +0.000627 m | -0.020132 m | +0.102445 m |
| Endpoint spread ratio post/raw | 1.009098 | 0.999825 | 1.007468 | 0.436648 | 7.727128 |
| Raw prefix pairwise spread | 0.050898 m | 0.038471 m | 0.143439 m | 0.004492 m | 0.341310 m |
| Post prefix pairwise spread | 0.051065 m | 0.038526 m | 0.143423 m | 0.003799 m | 0.341367 m |
| Prefix `post - raw` delta | +0.000167 m | +0.000002 m | +0.000086 m | -0.008340 m | +0.061172 m |
| Prefix spread ratio post/raw | 1.009385 | 1.000049 | 1.002009 | 0.650561 | 7.640093 |
| Raw-to-post displacement mean | 0.001866 m | 0.001345 m | 0.002584 m | 0.000244 m | 0.125308 m |
| Raw-to-post displacement max | 0.005903 m | 0.003335 m | 0.006525 m | 0.000569 m | 0.263686 m |
| Raw/post selected-distance correlation | 0.994711 | 1.000000 | 1.000000 | -0.999885 | 1.000000 |

The simple compression indicators should not be overread: endpoint pairwise
mean is slightly lower after postprocessing in 57.125% of records and prefix
pairwise mean is slightly lower in 42.167% of records, but threshold-crossing
compression is almost absent:

| Threshold-crossing rate | Value |
| --- | ---: |
| endpoint raw >= 1 mm and post < 1 mm | 0.000000 |
| endpoint raw >= 1 cm and post < 1 cm | 0.000833 |
| endpoint raw >= 10 cm and post < 10 cm | 0.000000 |
| prefix raw >= 1 mm and post < 1 mm | 0.000000 |
| prefix raw >= 1 cm and post < 1 cm | 0.000000 |
| prefix raw >= 10 cm and post < 10 cm | 0.000000 |

Decision: accept this diagnostic as evidence against generic
Savitzky-Golay/`postprocess_reference` geometry compression as the current
materiality bottleneck on sample59. The stronger finding is that the first
10-step raw candidate set is itself very local: mean raw endpoint spread is
only about 9.9 cm and mean raw prefix spread is about 5.1 cm. This explains why
many finite-candidate selector changes have had little useful action space.
The result does not authorize an online selector, formal seeds, CAMP retraining,
DP retraining, or a performance claim.

Next admissible step: run an offline, state-conditioned materiality audit over
the same logs, grouping raw-prefix spread and postprocessed spread by red-light
exposure, fallback/nonfallback, selected index, feasibility, and progress/comfort
atoms. If the low-spread finding is concentrated in the safety-critical records,
then the next intervention should target candidate-set generation or horizon
coverage, not the CAMP master. If it is not concentrated, reject raw-prefix
geometry as the active blocker and return to bounded finite-candidate safety
override design.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Raw-prefix predeclare dry-run | `8fce3f077e359e12197f7c36007992a171041a93c5f734c4023c0f000ae7ea8b` |
| Raw-prefix shape audit JSON | `fadc927f22bba8fa34503454ee97a588d543252c749e4cc90e075789018116f3` |
| Raw-prefix geometry JSON | `4bec67ee5a40c7eb549104acf7c1b6debc2798186cbfb4dcbfd7c48b03d263bb` |
| Raw-prefix geometry markdown | `26d5e1b512c241a7b0ad5a7f1e70889fa9153b43211b36ab77d56cbe51da5d62` |
