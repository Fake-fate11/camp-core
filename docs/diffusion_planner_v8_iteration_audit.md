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
| lateral definition screen JSON | `d80981208d2fb1eb05fe471c0e16982564a8ebecf2c2d5774fd2204a55a9734c` |
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
