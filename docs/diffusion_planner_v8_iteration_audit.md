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

### State-conditioned raw-prefix materiality audit

Commit `faa23ae721f5cb011ced8a5c54b8850eb77d3ab0` adds an offline
state-conditioned materiality analyzer. It reuses the same raw/postprocessed
prefix geometry calculation and groups fixed logged candidate constants by
traffic-light mode, NPC count, fallback, selected index, selected feasibility,
red-light exposure, progress atom, lateral atom, and DP-prior jerk atom. It
does not use outcomes, train weights, change candidate generation, or change
the selector.

Verification:

```text
py -3.12 -m py_compile scripts\integrations\analyze_diffusion_planner_raw_prefix_materiality_by_state.py

py -3.12 -m pytest camp_core\tests\test_diffusion_planner_raw_prefix_materiality_by_state.py
1 passed

py -3.12 -m pytest camp_core\tests\test_diffusion_planner_raw_prefix_geometry.py
3 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_raw_prefix_materiality_by_state.py
1 passed
```

The analyzer was run on the same predeclared 2,400-record sample59 raw-prefix
root. Output:

```text
/root/autodl-tmp/camp_dp_raw_prefix_geometry_sample59_static_e488ff8/raw_prefix_materiality_by_state.json
/root/autodl-tmp/camp_dp_raw_prefix_geometry_sample59_static_e488ff8/raw_prefix_materiality_by_state.md
```

Selected group summaries:

| Group | Count | Raw endpoint mean | Raw prefix mean | Endpoint delta mean | Selected union-red mean | Progress atom mean | Lateral atom mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 2,400 | 0.098633 m | 0.050898 m | +0.000368 m | 1.406250 | 0.109030 | 0.540956 |
| traffic_lights=on | 1,200 | 0.096187 m | 0.049591 m | +0.000273 m | 2.812500 | 0.111635 | 0.544423 |
| traffic_lights=off | 1,200 | 0.101078 m | 0.052205 m | +0.000462 m | 0.000000 | 0.106424 | 0.537488 |
| npc=0 | 1,200 | 0.070338 m | 0.036181 m | +0.000277 m | 0.352917 | 0.068740 | 0.544836 |
| npc=4 | 1,200 | 0.126927 m | 0.065615 m | +0.000458 m | 2.459583 | 0.149320 | 0.537075 |
| fallback=true | 484 | 0.109310 m | 0.057136 m | +0.000707 m | 4.997934 | 0.349802 | 0.697417 |
| fallback=false | 1,916 | 0.095935 m | 0.049322 m | +0.000282 m | 0.498956 | 0.048209 | 0.501432 |
| selected_union_red_positive=true | 107 | 0.101923 m | 0.052831 m | +0.000697 m | 31.542056 | 0.213729 | 0.780720 |
| selected_union_red_positive=false | 2,293 | 0.098479 m | 0.050808 m | +0.000352 m | 0.000000 | 0.104144 | 0.529768 |
| any_union_red=true | 131 | 0.117129 m | 0.060916 m | +0.000783 m | 25.763359 | 0.236310 | 0.694456 |
| any_union_red=false | 2,269 | 0.097565 m | 0.050319 m | +0.000344 m | 0.000000 | 0.101681 | 0.532094 |
| selected_feasible=true | 1,916 | 0.095935 m | 0.049322 m | +0.000282 m | 0.498956 | 0.048209 | 0.501432 |
| selected_feasible=false | 484 | 0.109310 m | 0.057136 m | +0.000707 m | 4.997934 | 0.349802 | 0.697417 |
| feasible_bucket=all | 1,644 | 0.078122 m | 0.040080 m | +0.000236 m | 0.058090 | 0.036079 | 0.462331 |
| feasible_bucket=partial | 272 | 0.203601 m | 0.105179 m | +0.000733 m | 3.163603 | 0.121522 | 0.737765 |
| feasible_bucket=none | 484 | 0.109310 m | 0.057136 m | +0.000707 m | 4.997934 | 0.349802 | 0.697417 |

Decision: reject the hypothesis that first-10-step raw-prefix materiality is
especially worse in red-light-exposed, fallback, or infeasible records.
Safety-critical groups have similar or larger raw spread than the global mean:
selected union-red-positive records have 10.19 cm mean raw endpoint spread,
any-union-red records have 11.71 cm, fallback records have 10.93 cm, and
partial-feasible records have 20.36 cm. The low first-prefix spread is therefore
a broad short-horizon candidate-generation property, not a state-local
postprocessing or safety-critical compression failure.

This narrows the next branch. First-10-step raw geometry should not be used as
the primary explanation for h80 red exposure misses. If candidate generation is
still investigated, the next diagnostic must be predeclared around longer raw
horizons such as 30 or 80 steps, because red-light exposure is a long-horizon
certificate. Otherwise, return to the finite-candidate safety override design
with explicit progress/comfort budgets, while keeping the result framed as a
selector over a fixed candidate set rather than Benders.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| State-conditioned materiality JSON | `9e0c52fd697bdd2ad473cb1edcf5a40f1e6ec8c126ffa1dc271ec09b47b0be46` |
| State-conditioned materiality markdown | `2da932f9f61e7fd72abae75aff80798346a504ea812be73c7e1c3c7d928675e5` |

### Predeclared H80 raw-prefix geometry diagnostic

The first-10-step raw-prefix audit rejected state-local short-prefix
materiality as the explanation for h80 red exposure misses. The next diagnostic
therefore logs the full 80-step raw candidate horizon on the same non-formal
sample59 static baseline grid. This is still diagnostic-only: it changes no
candidate generation, CAMP score, selector, atom schema, DP weights, CAMP
weights, tracker input, or formal seed.

| Parameter | Value |
| --- | --- |
| CAMP commit at predeclare | `9fa9824852aff03640192fe27fd1aa534bb63050` |
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
| Raw-prefix logging | `--camp_log_raw_candidate_prefix_steps 80` |

The new, non-overwriting output root is:

```text
/root/autodl-tmp/camp_dp_raw_prefix_h80_sample59_static_9fa9824
```

The exact 12-command dry-run was persisted before execution at:

```text
/root/autodl-tmp/camp_dp_raw_prefix_h80_sample59_static_9fa9824_predeclare.txt
```

Its SHA-256 is
`10a9edd9eb9c90fc29aa5166a11f6be3f9ea08de6201c64acfe7553f26d86b55`.

Acceptance for this diagnostic:

1. all 12 static runs complete and every summary records
   `camp_raw_candidate_prefix_logging.selection_effect=false`;
2. every selection record contains a raw prefix with shape `8 x 80 x 4`;
3. raw/postprocessed geometry and state-conditioned materiality analyzers run
   over the H80 root;
4. any conclusion is limited to fixed finite-candidate long-horizon geometry,
   not Benders, online safety override, formal performance, CAMP retraining, or
   DP retraining.

Formal seeds `11/12/13` remain frozen.

### H80 raw-prefix geometry diagnostic result

The predeclared H80 raw-prefix diagnostic completed under:

```text
/root/autodl-tmp/camp_dp_raw_prefix_h80_sample59_static_9fa9824
```

It produced 12 validation summaries and 12 selection logs. Structural audit:

| Check | Result |
| --- | ---: |
| Selection logs | 12 |
| Validation summaries | 12 |
| Selection records | 2,400 |
| Missing raw prefixes | 0 |
| Raw prefix shape | `8 x 80 x 4` for all records |
| Postprocessed prefix shape | `8 x 10 x 3` for all records |
| Validation mode | `('static', 'perfect')` for all 12 runs |

The older raw/postprocessed geometry analyzer clamps to the common available
horizon, so it remains a 10-step transform audit. Commit
`7acb911f82075f909ba8f8d33b17090d41b45904` adds a raw-only multi-horizon
materiality analyzer to evaluate the newly logged 80-step raw prefixes without
requiring a 80-step postprocessed prefix.

Verification:

```text
py -3.12 -m py_compile scripts\integrations\analyze_diffusion_planner_raw_prefix_horizon_materiality.py

py -3.12 -m pytest camp_core\tests\test_diffusion_planner_raw_prefix_horizon_materiality.py
2 passed

py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_raw_prefix_geometry.py \
  camp_core\tests\test_diffusion_planner_raw_prefix_materiality_by_state.py
4 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_raw_prefix_horizon_materiality.py
2 passed
```

Raw-only horizon summary over all 2,400 records:

| Horizon | Raw endpoint mean | Raw endpoint p95 | Raw endpoint max | Raw prefix mean | Selected-distance mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| H10 | 0.098633 m | 0.280582 m | 0.648173 m | 0.050898 m | 0.063390 m |
| H30 | 0.355850 m | 0.972424 m | 3.174570 m | 0.170378 m | 0.215884 m |
| H80 | 1.251789 m | 4.723663 m | 11.323578 m | 0.538569 m | 0.647065 m |

Selected H80 state-conditioned groups:

| Group | Count | H80 endpoint mean | H80 endpoint p95 | H80 prefix mean | Selected union-red mean | Progress atom mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 2,400 | 1.251789 m | 4.723663 m | 0.538569 m | 1.406250 | 0.109030 |
| traffic_lights=on | 1,200 | 1.222708 m | 4.691326 m | 0.533858 m | 2.812500 | 0.111635 |
| traffic_lights=off | 1,200 | 1.280869 m | 4.817676 m | 0.543279 m | 0.000000 | 0.106424 |
| npc=0 | 1,200 | 0.983218 m | 3.951549 m | 0.412499 m | 0.352917 | 0.068740 |
| npc=4 | 1,200 | 1.520360 m | 5.312454 m | 0.664638 m | 2.459583 | 0.149320 |
| fallback=true | 484 | 0.932489 m | 2.276625 m | 0.432786 m | 4.997934 | 0.349802 |
| fallback=false | 1,916 | 1.332447 m | 5.203695 m | 0.565290 m | 0.498956 | 0.048209 |
| selected_union_red_positive=true | 107 | 1.375450 m | 5.794157 m | 0.606037 m | 31.542056 | 0.213729 |
| selected_union_red_positive=false | 2,293 | 1.246018 m | 4.689885 m | 0.535420 m | 0.000000 | 0.104144 |
| any_union_red=true | 131 | 1.735982 m | 5.968796 m | 0.706556 m | 25.763359 | 0.236310 |
| any_union_red=false | 2,269 | 1.223834 m | 4.603770 m | 0.528870 m | 0.000000 | 0.101681 |
| selected_feasible=true | 1,916 | 1.332447 m | 5.203695 m | 0.565290 m | 0.498956 | 0.048209 |
| selected_feasible=false | 484 | 0.932489 m | 2.276625 m | 0.432786 m | 4.997934 | 0.349802 |
| feasible_bucket=all | 1,644 | 1.005088 m | 2.857958 m | 0.430401 m | 0.058090 | 0.036079 |
| feasible_bucket=partial | 272 | 3.311042 m | 8.748158 m | 1.380577 m | 3.163603 | 0.121522 |
| feasible_bucket=none | 484 | 0.932489 m | 2.276625 m | 0.432786 m | 4.997934 | 0.349802 |

Decision: reject the stronger long-horizon hypothesis that fixed DP lacks H80
raw geometric materiality on the red-exposed sample59 records. The H80 raw
candidate set is materially wider than H10: mean endpoint spread rises from
9.86 cm to 1.25 m, p95 rises from 28.06 cm to 4.72 m, and max rises to
11.32 m. Red-exposed groups are not below the global mean: selected union-red
positive records have 1.38 m mean H80 endpoint spread and any-union-red records
have 1.74 m. Partial-feasible records have the largest spread at 3.31 m.

This means the active blocker is not generic raw candidate geometry collapse.
The evidence points back to finite-candidate selection tradeoffs: lower-red
alternatives exist in some states, but earlier audits showed they usually cost
progress, H3 distance, or comfort. The next mathematically admissible branch is
therefore a finite-candidate safety override design with explicit progress and
comfort budgets. It must remain fail-closed, deterministic, fixed-candidate,
and outcome-free; it is not Benders unless a valid master/subproblem/dual-cut
construction is introduced.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| H80 predeclare dry-run | `10a9edd9eb9c90fc29aa5166a11f6be3f9ea08de6201c64acfe7553f26d86b55` |
| H80 shape audit JSON | `3b7dd7b8023ac389027affb325435a95c4bf3b423b033d234a30a19bed08490e` |
| H80 common-prefix geometry JSON | `436b04bd6e29dc773c2579101ec2af4a0a2041247853d11efcab57ac7d216cc3` |
| H80 common-prefix geometry markdown | `4ed7296719eac817d3fd1b6ab66b6724dab6185d99b6d9afeddcfe251b0c2639` |
| H80 common-prefix materiality JSON | `909a35ed576f5814a5fc0a3633f267ed18d31d63019608d5f68a752f950038fb` |
| H80 common-prefix materiality markdown | `70b6457fedd0d5a5c60dee0e642ad706555c4fe580d9ca1c95d67678367e77e4` |
| Raw-only horizon materiality JSON | `cb85e37e396f86e30edf0b6b48b8c49efd14284e3e18534aa52559dba0375ed5` |
| Raw-only horizon materiality markdown | `e4af6782fe56abc0fdfa5a16182e05146455e786216ef469c35edf94b93daebf` |

### Post-H80 safety budget gate replay

After migrating the session, the H80 raw-prefix root was re-analyzed with the
existing tracker rollout shadow analyzer at CAMP commit
`cba9ad54ec7d76dcf160ccd17cff82151f1f9d36`. This replay is a consistency
gate only: it uses logged current-tick candidate constants and does not change
the online selector, candidate generation, atom schema, CAMP weights, DP
weights, or formal seeds.

Input:

```text
/root/autodl-tmp/camp_dp_raw_prefix_h80_sample59_static_9fa9824
```

Output:

```text
/root/autodl-tmp/camp_dp_h80_safety_override_budget_gate_cba9ad5
```

The structural counts are unchanged: `2,400` records, `19,200` candidates,
`484` fallback records, and `1,916` nonfallback records. The selected
h30-safe/full-red misses also remain unchanged:

| Count | Value |
| --- | ---: |
| Selected h30-safe/full-red records | 32 |
| Fallback misses | 0 |
| Nonfallback misses | 32 |
| With lower union-red base-feasible candidate | 20 |
| Without lower union-red base-feasible candidate | 12 |

The replay reproduces the earlier base-feasible budget gate. The widest
predeclared base-feasible screen covers only `17/32` misses and still worsens
H3 vector jerk by `+2.743974 m/s^3` on changed records. Adding the red
stopping-margin-nonworse condition covers at most `10/32` and still worsens H3
vector jerk by `+2.266827 m/s^3`.

The no-lower-feasible attribution is also unchanged: all `12/12` no-lower
base-feasible misses have lower-red generated candidates blocked by
feasibility, with reason counts `dp_underprogress=51`, `dp_kinematic=13`, and
`dynamic_obb_collision=4`. Virtually ignoring only `dp_underprogress` restores
lower-red candidates for `10/12` events; under the widest
underprogress-relaxed budget with stopping-margin nonworse it changes `10/12`,
improves union-red by `-22.650000`, improves stopping margin by `-21.207705`,
and improves H3 vector jerk by `-12.343982 m/s^3`, at a mean progress cost of
`-0.947520 m`.

Decision: the H80 evidence does not revive the rejected base-feasible safety
override. The active blocker remains the fixed candidate-set tradeoff: legal
base-feasible lower-red alternatives are too localized and too comfort-costly
for a deployable selector, while the stronger underprogress-relaxed opportunity
changes the DP feasibility contract and has already failed the non-formal
closed-loop pilot gate due to small realized benefit, weak completion
regression, jerk regression, and insufficient latency margin. Do not implement
another online safety override, do not run a new 12/36 matrix, and do not train
new CAMP weights from this replay alone. The next admissible branch is a
candidate-generation or atom/certificate redesign that improves lower-red
availability without paying the observed progress and jerk taxes, with the
finite-candidate affine-score and convex robust-master contract preserved.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| H80 safety budget JSON | `7b260246355c76762a929581a6ea8ff3c31d2543e4b66c6fc9f07ba753669ba5` |
| H80 safety budget markdown | `25dea17f0c7c4d4e13a374bcd02c1edc005fa50a49515aef3633274eadeb510a` |

### Raw H80 candidate-set bottleneck audit

Commits `9012a04767d0a4130054585dba4c356dabef79a8` and
`05758d5c69e7d4266068f84e3b0043628d0be62f` add an offline
raw-horizon bottleneck analyzer. The second commit aligns short-horizon
red extraction with the tracker rollout shadow analyzer by reading
`max(-dp_candidate_rewards[*].red_light, 0)` when
`candidate_planned_red_light_cost` is not logged.

This diagnostic does not change DP, candidate generation, CAMP weights, CAMP
atoms, selection, replay behavior, or formal seeds. It reads the already logged
H80 raw candidate prefixes and measures endpoint spread and simple endpoint
mode count under increasingly strict current-tick masks:

1. all candidates;
2. base-feasible candidates;
3. lower union-red candidates;
4. lower union-red base-feasible candidates;
5. lower-red candidates that additionally satisfy progress, target-speed, H10
   distance, and H3 lateral budgets;
6. the same bounded mask plus H3 mean-jerk nondegradation.

The bounded screens use progress-loss budgets `0.10`, `0.25`, and `0.50 m`,
target-speed loss `0.10 m/s`, H10 distance loss `0.10 m`, and H3 max lateral
`2.0 m/s^2`. Endpoint modes use a `0.50 m` raw H80 endpoint connectivity
threshold. These are development diagnostics, not deployed thresholds.

Verification:

```text
py -3.12 -m py_compile scripts\integrations\analyze_diffusion_planner_raw_horizon_bottleneck.py

$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_raw_horizon_bottleneck.py
2 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_raw_horizon_bottleneck.py
2 passed
```

The real H80 sample59 artifact was analyzed at:

```text
/root/autodl-tmp/camp_dp_raw_h80_bottleneck_sample59_static_05758d5
```

Structural counts are unchanged: `2,400` records, `19,200` candidates, `484`
fallback records, and `1,916` nonfallback records. Event counts:

| Event | Count |
| --- | ---: |
| Selected union-red positive | 107 |
| Selected h30-safe/full-red | 32 |
| Any lower-red candidate | 88 |
| Any lower-red base-feasible candidate | 20 |

For the `32` selected h30-safe/full-red misses:

| Mask | Nonempty | Candidate count mean | Mode count mean | Raw H80 endpoint pairwise mean | Distance to selected mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| all candidates | 32/32 | 8.000000 | 3.906250 | 3.054723 m | 4.266608 m |
| base feasible | 32/32 | 4.218750 | 2.656250 | 0.907646 m | 0.983731 m |
| lower-red any | 32/32 | 5.406250 | 2.500000 | 1.663732 m | 5.568946 m |
| lower-red base feasible | 20/32 | 2.250000 | 2.250000 | 0.809753 m | 1.768624 m |

Bounded lower-red availability for those same `32` misses:

| Progress budget | Mask | Nonempty | Candidate count mean | Mode count mean | Raw H80 endpoint pairwise mean |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0.10 m | bounded | 0/32 | 0.000000 | n/a | n/a |
| 0.10 m | bounded + H3 jerk nondegrading | 0/32 | 0.000000 | n/a | n/a |
| 0.25 m | bounded | 2/32 | 0.062500 | 1.000000 | 0.000000 m |
| 0.25 m | bounded + H3 jerk nondegrading | 0/32 | 0.000000 | n/a | n/a |
| 0.50 m | bounded | 5/32 | 0.218750 | 1.000000 | 0.079427 m |
| 0.50 m | bounded + H3 jerk nondegrading | 1/32 | 0.031250 | 1.000000 | 0.000000 m |

Interpretation:

1. The H80 raw candidate pool is not globally collapsed. In the h30-missed
   group, all eight raw candidates span about `3.05 m` endpoint pairwise spread
   and roughly four endpoint modes.
2. Lower-red alternatives are present for all `32` h30-missed records, but the
   lower-red alternatives are far from the selected candidate in raw H80
   endpoint space: mean selected distance is `5.57 m`.
3. Base feasibility is a major bottleneck: lower-red base-feasible alternatives
   remain in only `20/32` records, matching the previous safety-budget
   attribution.
4. Industrially relevant bounded masks nearly empty the set. At `0.50 m`
   progress loss with target-speed, H10, and lateral guards, only `5/32`
   records retain any lower-red candidate; adding H3 jerk nondegradation leaves
   only `1/32`.
5. The surviving bounded lower-red set is single-mode and local, not a rich
   candidate-generation substrate for CAMP to rank.

Decision: this strengthens the candidate-generation bottleneck diagnosis and
rejects another selector-only iteration. The raw DP generator can produce
long-horizon lower-red geometry, but those alternatives usually live outside
the current base-feasible and bounded progress/comfort envelope. The next
admissible branch should be a predeclared candidate-generation or feasibility
design that creates lower-red candidates inside the bounded envelope, for
example a stop-aware/progress-compatible branch, while keeping DP weights fixed
and reporting the change strictly as a finite candidate-set change. Do not run
a new 12/36 matrix, online selector wiring, formal seeds, CAMP retraining, or
DP retraining from this diagnostic alone.

Mathematical boundary: every mask and raw H80 geometry descriptor above is a
fixed finite-candidate constant at the current tick. If a descriptor is later
atomized, the fixed-set CAMP score remains affine in `w` and the
simplex/CVaR/L2 robust master remains convex. This audit is not Benders and
makes no global convexity claim over trajectory coordinates.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Raw H80 bottleneck JSON | `0854bce6b45ad29def3169a3920cfa96a2f563ba40f1135b18824904e1012fcb` |
| Raw H80 bottleneck markdown | `e46ed499e01e889c35b3102f1f045f5dff01ddf1d13c352286c982a351f42342` |

### Raw H80 budget blocker attribution

Commit `41cd9426cccecb9133c33d74676068ced3047fd5` extends the raw H80
bottleneck analyzer with budget-blocker attribution. This remains an offline
diagnostic over fixed current-tick candidate constants. It does not change DP,
candidate generation, CAMP weights, atom schema, replay behavior, online
selection, or formal seeds.

For each progress budget screen, the analyzer records whether lower-red
base-feasible candidates exist, whether any satisfy the bounded progress /
target-speed / H10-distance / H3-lateral envelope, whether any also satisfy H3
mean-jerk nondegradation, and which budget condition blocks all lower-red
base-feasible candidates.

Verification:

```text
py -3.12 -m py_compile scripts\integrations\analyze_diffusion_planner_raw_horizon_bottleneck.py

$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_raw_horizon_bottleneck.py
2 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_raw_horizon_bottleneck.py
2 passed
```

The real H80 sample59 artifact was analyzed at:

```text
/root/autodl-tmp/camp_dp_raw_h80_bottleneck_blockers_sample59_static_41cd942
```

For the `32` selected h30-safe/full-red misses, blocker attribution is:

| Progress budget | Lower-red base feasible | Bounded | Bounded + H3 jerk nondegrading | Progress blocks all | Target-speed blocks all | H10 blocks all | Lateral blocks all | Jerk blocks bounded |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.10 m | 20/32 | 0/32 | 0/32 | 20/20 | 5/20 | 14/20 | 0/20 | 0/0 |
| 0.25 m | 20/32 | 2/32 | 0/32 | 17/20 | 5/20 | 14/20 | 0/20 | 2/2 |
| 0.50 m | 20/32 | 5/32 | 1/32 | 10/20 | 5/20 | 14/20 | 0/20 | 4/5 |

Across the `20` h30-missed records with any lower-red base-feasible candidate,
the best lower-red candidate still has these minimum deficits:

| Quantity | Median | Mean | P95 | Max |
| --- | ---: | ---: | ---: | ---: |
| Progress loss | 0.482559 m | 0.700578 m | 1.697065 m | 2.269403 m |
| Target-speed loss | 0.076329 m/s | 0.110299 m/s | 0.381921 m/s | 0.411755 m/s |
| H10 distance loss | 0.141668 m | 0.212973 m | 0.556723 m | 0.571431 m |
| H3 max lateral | 0.234244 m/s^2 | 0.240060 m/s^2 | 0.372518 m/s^2 | 0.475419 m/s^2 |
| H3 mean-jerk delta | +1.126135 m/s^3 | -0.644388 m/s^3 | +13.412870 m/s^3 | +19.066109 m/s^3 |

Interpretation:

1. H3 lateral is not the active blocker in the selected h30-safe/full-red
   misses: it blocks `0/20` lower-red base-feasible opportunities under every
   audited budget.
2. Progress and H10 distance are the primary envelope blockers. Even at a
   `0.50 m` progress budget, progress blocks `10/20` lower-red base-feasible
   opportunities and H10 distance blocks `14/20`.
3. Target speed is a secondary blocker (`5/20`), consistent with the
   stop-like nature of the lower-red alternatives.
4. Jerk remains a deployment blocker after the bounded envelope is satisfied:
   at `0.50 m`, `4/5` bounded candidates fail H3 mean-jerk nondegradation.

Decision: this predeclares the next admissible design target more sharply. A
stop-aware/progress-compatible candidate-generation branch must create
lower-red candidates that preserve the selected candidate's near-term progress
and H10 distance envelope while smoothing jerk. Simply relaxing lateral limits,
retuning CAMP weights, or adding another ranking tie-break is not supported.
Before any online wiring or paired replay, the next prototype must pass an
offline fixed-candidate or default-off generator diagnostic showing materially
better h30-missed coverage inside the same bounded envelope, with H3 jerk
nondegradation explicitly audited. DP weights and formal seeds remain frozen.

Mathematical boundary: blocker flags and deficit summaries are current-tick
finite-candidate constants. They may define future diagnostic atoms or guards
only if treated as fixed data per candidate, preserving affine scoring in
`w` and the simplex/CVaR/L2 convex master. This is not a Benders
decomposition and makes no convexity claim over trajectory coordinates.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Raw H80 blocker JSON | `90c788202641f7d887df79ecde8590c71649cda9f06dab4e6fb298e1defd5d86` |
| Raw H80 blocker markdown | `5a094f4cbfcd2ecd6bc4399e0037b5ae70a6f1dd794b236862264b50fc6f23fd` |

### Stop-aware raw-H80 splice potential audit

Commit `aee5fe7f9e7b3ca8aab120370a5b436e17f1ce07` adds an offline
stop-aware splice potential analyzer. It constructs a diagnostic raw-H80
candidate from the selected candidate \(S\) and a lower-red donor \(D\):

```text
G_t = S_t                                           for t < H10
T_t = S_H10 + (D_t - D_H10)                         donor tail in selected H10 frame
G_t = (1 - w_t) S_t + w_t T_t                       for t >= H10
```

with a smoothstep blend over `10` steps by default. This preserves the selected
raw H10 prefix exactly while testing whether the lower-red donor's long-horizon
tail can remain material and reduce a raw third-difference jerk proxy.

This is not an online generator, selector, CAMP atom, or Benders cut. It does
not recompute DP reward, red-light cost, hard feasibility, Savitzky-Golay
postprocessing, PerfectTracker commands, or closed-loop outcomes for the
synthetic splice. The donor's logged lower-red certificate is used only to
choose a diagnostic tail source; it is not a certificate for the transformed
splice.

Verification:

```text
py -3.12 -m py_compile scripts\integrations\analyze_diffusion_planner_stop_aware_splice_potential.py

$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_stop_aware_splice_potential.py
2 passed

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_stop_aware_splice_potential.py
2 passed
```

The real H80 sample59 artifact was analyzed at:

```text
/root/autodl-tmp/camp_dp_stop_aware_splice_h80_sample59_static_aee5fe7
```

The audit denominator is the same `32` selected h30-safe/full-red records.

| Donor pool | Donor records | Material splice | Jerk nondegrading splice | Material + jerk nondegrading | Best endpoint distance | Best jerk delta | H10 deviation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lower-red any | 32/32 | 28/32 | 29/32 | 26/32 | 6.468361 m | -4.737382 m/s^3 | 0.000000 m |
| lower-red base feasible | 20/32 | 16/32 | 15/32 | 13/32 | 2.254629 m | -1.468295 m/s^3 | 0.000000 m |

Additional summaries:

| Donor pool | Candidate count mean | Endpoint distance p95 | Endpoint-to-donor mean | Max selected deviation mean | Jerk delta p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| lower-red any | 5.406250 | 13.350203 m | 0.349362 m | 6.586716 m | +0.529048 m/s^3 |
| lower-red base feasible | 2.250000 | 5.505496 m | 0.351322 m | 2.414356 m | +0.764552 m/s^3 |

Interpretation:

1. This branch is meaningfully different from the rejected first-step graft,
   anchored residual graft, and smooth H10 anchor projection. It operates on
   raw H80 geometry, preserves the selected first H10 prefix exactly, and keeps
   meter-scale long-horizon tail materiality.
2. The raw third-difference proxy is encouraging: the best lower-red base
   feasible splice has mean jerk-proxy delta `-1.468295 m/s^3`, with
   `13/32` records both material and jerk-nondegrading.
3. The stronger lower-red-any pool reaches `26/32` material and
   jerk-nondegrading records, but those donors include candidates that were not
   base feasible before transformation. They cannot be used without a new
   hard-feasibility argument and reward recomputation.
4. This audit does not prove red-light improvement after transformation. The
   splice moves the donor tail into the selected H10 frame; its DP red-light
   score and feasibility must be recomputed before any replay or online claim.

Decision: accept this as a candidate-generation design lead, not as a deployed
method. The next admissible step is a default-off offline recomputation gate:
apply the H10-preserving raw splice to the selected h30-missed records, then
run the same Savitzky-Golay/postprocess, DP reward/red-light feasibility, and
PerfectTracker shadow calculations used by the replay logs. The gate must show
that transformed candidates actually enter the bounded lower-red envelope and
remain hard-feasible before any paired non-formal simulation, online wiring,
CAMP retraining, or formal seeds are considered. DP weights remain fixed.

Mathematical boundary: the splice map is deterministic for fixed current-tick
candidate prefixes and fixed hyperparameters. If transformed candidates are
later added to a finite candidate set and atomized from current-tick data,
CAMP scores remain affine in `w` and the simplex/CVaR/L2 robust master remains
convex for that fixed set. This still is not a Benders decomposition and makes
no global convexity claim over trajectory coordinates.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Stop-aware splice JSON | `f5a9c93d3fbbf42bbb5395d4776e62ac631ef6b4ed5143155da9df033597f352` |
| Stop-aware splice markdown | `7f7ab4cac757fc01650b9c484c7e741a6c8c5a47570d9afddfd0d091f18938dd` |

### Stop-aware splice recompute readiness audit

Commit `b674109c95698fac0f3d0d8d2a0b1fe23d1b3df7` adds a fail-closed artifact
readiness audit for the next gate. The audit checks whether existing selection
logs and optional
microbenchmark snapshots contain enough current-tick context to recompute a
stop-aware raw-H80 splice through the same SG/postprocess, PerfectTracker
shadow, red-stopping-margin, and DP reward/full-red calculations used by the
replay path. It is a logging-contract audit only; it does not recompute reward,
red-light score, CAMP score, or closed-loop outcome.

Local verification:

```text
py -3.12 -m py_compile scripts\integrations\analyze_diffusion_planner_splice_recompute_readiness.py

py -3.12 -m pytest camp_core\tests\test_diffusion_planner_splice_recompute_readiness.py
2 passed
```

Remote command:

```text
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_splice_recompute_readiness.py \
  --root /root/autodl-tmp/camp_dp_raw_prefix_h80_sample59_static_9fa9824 \
  --label sample59_static_raw_h80_34c1d4a \
  --output_json /root/autodl-tmp/camp_dp_splice_recompute_readiness_sample59_static_34c1d4a/readiness.json \
  --output_md /root/autodl-tmp/camp_dp_splice_recompute_readiness_sample59_static_34c1d4a/readiness.md
```

Remote artifact:

```text
/root/autodl-tmp/camp_dp_splice_recompute_readiness_sample59_static_34c1d4a
```

The audit found `12` selection logs, `2400` records, and the same `32`
selected h30-safe/full-red target records. Results on the target records:

| Stage | Ready target records | Missing target fields |
| --- | ---: | --- |
| raw splice geometry from selection log | 32/32 | none |
| CAMP logged score audit from selection log | 32/32 | none |
| PerfectTracker splice recompute from selection log | 32/32 | none |
| red-stopping-margin splice recompute from selection log | 0/32 | `red_route_points` for all 32 |
| DP reward/full-red recompute from selection log | 0/32 | `reward_input__lanes`, `reward_input__route_lanes`, `reward_input__line_strings`, `reward_input__ego_shape`, `reward_input__neighbor_agents_future`, `reward_input__neighbor_agents_past`, `reward_input__goal_pose` for all 32 |

There were `0` matching microbenchmark snapshots in the raw-H80 artifact, so
the snapshot recompute stages had no eligible inputs.

Decision: reject any claim that the current raw-H80 selection-log artifact can
prove splice feasibility or red-light improvement after transformation. The
old logs are sufficient for raw geometry, CAMP score audit, and PerfectTracker
state-context readiness, but they do not contain the red route point array or
the DP reward tensor context. The next admissible step is a default-off
snapshot/recompute-context capture on a small non-formal smoke run with
selection effect disabled, followed by the actual transformed-candidate
recompute gate. Do not implement an online selector, run 12/36-run replay, or
train CAMP weights from this evidence.

Mathematical boundary: this readiness audit inspects fixed current-tick
artifact fields only. It defines a finite-candidate recomputation logging
contract and does not invoke Benders. If transformed candidates later become
fixed current-tick candidate constants and are atomized, the CAMP score remains
affine in `w` and the simplex/CVaR/L2 master remains convex; no global
convexity over trajectory coordinates is claimed.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Splice recompute readiness JSON | `603a3436a41ce0be6cb362d4640b0428cb4d962fe2d76e9e285f38dc37d4de32` |
| Splice recompute readiness markdown | `d5c37063141e72d76107ec32b1c6dddbfd4a53191df8113f5978e6dc959a7806` |

### Snapshot recompute-context smoke

Commit `a818b2feea3c655fc70c3fc7e6c2b52ff15c9861` exposes the existing
microbenchmark snapshot capture through the AutoDL remote wrapper:

```text
CAMP_MICROBENCHMARK_SNAPSHOT_DIR
CAMP_MICROBENCHMARK_SNAPSHOT_STEPS
```

Both variables are default-off. When the directory is unset, the wrapper does
not pass any snapshot arguments and the replay path is unchanged. The same
commit also propagates `camp_microbenchmark_snapshots` into
`camp_validation_summary.json` and the replay resummarizer metadata allowlist,
matching the raw-prefix logging metadata behavior.

Verification:

```text
py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_replay_summary.py \
  camp_core\tests\test_diffusion_planner_splice_recompute_readiness.py
14 passed

bash -n scripts/integrations/run_diffusion_planner_camp_remote.sh

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_replay_summary.py \
  camp_core/tests/test_diffusion_planner_splice_recompute_readiness.py
14 passed
```

The non-formal snapshot-context smoke ran at:

```text
/root/autodl-tmp/camp_dp_snapshot_context_smoke_seed101_a818b2f
```

Configuration: sample59 route, seed `101`, `3` steps, no NPCs, K=`8`,
redstopfloor05 static weights, perfect tracking, raw-prefix logging `10`, and
snapshot steps `0,1`. This run is context-capture validation only; it is not
latency evidence and does not count as a paired safety/comfort replay.

Observed metadata and tensor contract:

| Check | Result |
| --- | --- |
| Replay summary snapshot metadata | present, `selection_effect=false`, `latency_evidence=false`, files `2` |
| Validation summary snapshot metadata | present, same requested steps/files |
| Snapshot files | `camp_microbenchmark_step_0000.npz`, `camp_microbenchmark_step_0001.npz` |
| Candidate tensor shape | `8 x 80 x 4` for both snapshots |
| Red route point shape | `40 x 4` for both snapshots |
| Reward tensor keys | `18` keys for both snapshots |
| Required reward keys | `lanes`, `route_lanes`, `line_strings`, `ego_shape`, `neighbor_agents_future`, `neighbor_agents_past`, `goal_pose` all present |
| Snapshot metadata | `capture_has_no_selection_effect=true` for both snapshots |

Running the splice recompute readiness audit on the smoke output produced:

| Snapshot stage | Ready | Missing fields |
| --- | ---: | --- |
| PerfectTracker splice recompute | 2/2 | none |
| red-stopping-margin splice recompute | 2/2 | none |
| DP reward/full-red recompute | 2/2 | none |

Gate decision:

```text
Snapshot artifacts contain the required tensor context. The next step can
implement the actual transformed-candidate recompute gate.
```

Decision: accept this as the recompute-context observability gate for a short
non-formal smoke only. It resolves the logging-context blocker found in the
previous readiness audit, but it still does not prove any transformed splice
candidate is lower-red, hard-feasible, or better after DP reward recomputation.
The next admissible implementation step is an offline transformed-candidate
recompute gate over captured snapshots. Do not implement an online selector,
run 12/36-run replay, train CAMP weights, or touch formal seeds from this smoke
alone.

Mathematical boundary: snapshot arrays are fixed current-tick constants and
their capture has no selection effect. They can support a finite-candidate
transformed-candidate audit. This is not Benders and provides no dual cuts; if
future transformed candidates are atomized from fixed snapshot constants, CAMP
scoring remains affine in `w` and the simplex/CVaR/L2 master remains convex
only for that fixed finite set.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Snapshot smoke replay summary | `87a7a13e58a06df3b0a74043c9dcb20985e36c5d0c390d82213c0b635c45e300` |
| Snapshot smoke validation summary | `ff8dc9d82c62385bcf5f86773e9f0eaa86df6f480e6d92c498b28e3ae2e26e6e` |
| Snapshot smoke readiness JSON | `b038aee333eb96d6e85b0806ab926d8addf2915a64b70ff4fb7496b8ef0d1688` |
| Snapshot smoke readiness markdown | `cb17d987f4bb36d3351231b570a401db23b0b526f4bb48c59dbed6c0334f9115` |
| Snapshot step 0000 NPZ | `be5135e4bf9cddb15f17bb394f532a552a6ff48b40e92cc112c1354e2d67c8f8` |
| Snapshot step 0001 NPZ | `0c3e374e939c4f14465802e1a804031790e6d75fc6bc0a8e2bf67273d4cb0b59` |

### Offline splice recompute gate smoke

Commit `ff424b6ccac1ead31c96252f9acf77b7b799a377` adds
`scripts/integrations/analyze_diffusion_planner_splice_recompute_gate.py`.
The analyzer loads fixed microbenchmark snapshot tensors, reconstructs
H10-preserving splice candidates, applies the same Savitzky-Golay smoothing
metadata, and recomputes DP near-horizon reward plus full-horizon red-light
cost using the snapshot `reward_input__*` tensors. It also first recomputes the
original logged candidates and compares the recomputed near/full red-light
costs against the logged snapshot arrays.

The transformed candidate used by this gate is a deterministic diagnostic:
the selected candidate's first H10 xy prefix is preserved, the donor tail is
translated into the selected H10 frame with a smoothstep blend, and
`cos_yaw/sin_yaw` are reconstructed from the transformed xy finite
differences. This is a fixed-snapshot audit candidate, not an online DP
candidate generator or controller command.

Verification:

```text
py -3.12 -m py_compile \
  scripts\integrations\analyze_diffusion_planner_splice_recompute_gate.py

py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_splice_recompute_gate.py \
  camp_core\tests\test_diffusion_planner_splice_recompute_readiness.py
6 passed

/root/autodl-tmp/dp312_venv/bin/python -m py_compile \
  scripts/integrations/analyze_diffusion_planner_splice_recompute_gate.py

/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_splice_recompute_gate.py \
  camp_core/tests/test_diffusion_planner_splice_recompute_readiness.py
6 passed
```

Remote artifact:

```text
/root/autodl-tmp/camp_dp_splice_recompute_gate_smoke_seed101_ff424b6
```

The smoke reused the two snapshot files from:

```text
/root/autodl-tmp/camp_dp_snapshot_context_smoke_seed101_a818b2f/snapshots
```

Two donor-pool modes were evaluated:

| Donor pool | Purpose |
| --- | --- |
| `lower_logged_union_red` | safety-screened gate: only logged candidates with lower logged union-red than the selected candidate |
| `all_nonselected` | mechanical smoke only: proves transformed-candidate reward/full-red recomputation runs; not a safety claim |

Results:

| Donor pool | Snapshots | Selected h30-safe/full-red | Snapshots with donors | Transforms | Baseline near-red max error | Baseline full-red max error | Lower recomputed union-red |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `lower_logged_union_red` | 2 | 0 | 0 | 0 | 0.0 | 0.0 | 0 |
| `all_nonselected` | 2 | 0 | 2 | 14 | 0.0 | 0.0 | 0 |

Per-row summary:

| Donor pool | Step | Selected index | Donors | Selected union-red | Min transformed union-red | Lower union-red transforms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `lower_logged_union_red` | 0 | 7 | 0 | 0.0 | n/a | 0 |
| `lower_logged_union_red` | 1 | 2 | 0 | 0.0 | n/a | 0 |
| `all_nonselected` | 0 | 7 | 7 | 0.0 | 0.0 | 0 |
| `all_nonselected` | 1 | 2 | 7 | 0.0 | 0.0 | 0 |

Interpretation:

1. The baseline recomputation is exact on this smoke: both logged near-red and
   logged full-red max absolute errors are `0.0`.
2. The safety-screened donor pool is empty because the selected candidates in
   this short smoke already have recomputed/logged union-red `0.0`; this smoke
   is not a target h30-safe/full-red miss.
3. The all-nonselected donor pool is deliberately not safety-screened. It
   verifies that the H10-preserving transformed candidates can pass through the
   actual DP reward/full-red recomputation path, but it does not establish any
   safety improvement.

Decision: accept this as a mechanical recompute-gate milestone only. The code
can now recompute DP reward/full-red for transformed fixed-snapshot
candidates, and it can exact-check the original logged candidates. The next
admissible evidence step is to capture snapshot context on selected
h30-safe/full-red miss ticks, then run the `lower_logged_union_red` gate there.
Do not implement an online selector, run 12/36-run replay, train CAMP weights,
or touch formal seeds from this mechanical smoke.

Mathematical boundary: every splice and reward calculation above is performed
on fixed current-tick snapshot constants. The transformed candidate set is
finite and deterministic for the snapshot and hyperparameters. This is still
not Benders, supplies no master/subproblem dual cuts, and makes no global
convexity claim over trajectory coordinates. If these recomputed diagnostics
are later atomized for a fixed finite candidate set, CAMP scoring remains
affine in `w` and the simplex/CVaR/L2 master remains convex only in that fixed
candidate interpretation.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Recompute gate all-nonselected JSON | `b646b84f958ac70bd9af5c29932a7dc10b1c1a9b754226bf3000ee4f0198f501` |
| Recompute gate all-nonselected markdown | `aebd0d93ec8aa91732beb7b78a8a9de3be3c0e8350aad8de459b14a16744ba6e` |
| Recompute gate lower-logged-union-red JSON | `32d09989db42a1ea27a2d275d2c8517c59befe4a3b33c72c43949cd147172004` |
| Recompute gate lower-logged-union-red markdown | `872cd0ecc15a6fed41b43a54a219a9a89c5840e3d7fbed115a9553784493f459` |

### Target miss tick recompute gate

The next step captured a snapshot at a real selected h30-safe/full-red miss
tick from the raw-H80 sample59 artifact instead of a mechanically safe smoke.
The selected source was:

```text
/root/autodl-tmp/camp_dp_raw_prefix_h80_sample59_static_9fa9824/
  sample59_86/seed_2/npc_0/spawn_0p3/tl_on/static/camp_selection_log.json
```

Target record:

| Field | Value |
| --- | ---: |
| Selection step | 69 |
| Selected index | 1 |
| Logged near/red-light cost | 0.0 |
| Logged full-horizon red-light cost | 11.5 |
| Logged union-red cost | 11.5 |
| Lower logged union-red donors | 7 |

The target capture ran only this single non-formal replay prefix:

```text
/root/autodl-tmp/camp_dp_target_snapshot_seed2_npc0_tlon_step69_619d3c0
```

Configuration: sample59 route, seed `2`, no NPCs, traffic lights on, `70`
steps, K=`8`, redstopfloor05 static weights, raw-prefix logging `80`, and
microbenchmark snapshot step `69`. This is a targeted context-capture replay,
not a paired 12-run or formal seed run.

The snapshot readiness audit reported that the captured snapshot contains the
required tensors for PerfectTracker, red-stopping-margin, and DP
reward/full-red recomputation. The recompute gate then used the
`lower_logged_union_red` donor pool only.

Results:

| Check | Result |
| --- | ---: |
| Snapshots | 1 |
| Selected h30-safe/full-red snapshots | 1 |
| Snapshots with donors | 1 |
| Transform count | 7 |
| Baseline logged near-red max error | 0.0 |
| Baseline logged full-red max error | 0.0 |
| Selected recomputed union-red | 11.5 |
| Minimum transformed union-red | 0.0 |
| Lower union-red transforms | 7/7 |
| Hard-feasible transforms | 7/7 |
| Progress-screen feasible transforms | 7/7 |
| Lower union-red hard-feasible transforms | 7/7 |
| Lower union-red progress-feasible transforms | 7/7 |

Interpretation:

1. This is the first positive target-tick evidence for the stop-aware splice
   design: on one real h30-safe/full-red miss, every lower-logged-union-red
   donor produced an H10-preserving transformed candidate whose recomputed
   union-red dropped from `11.5` to `0.0`.
2. The same transformed candidates also passed the replay-aligned hard checks
   for collision, road border, lane crossing, static collision, kinematic
   violation, and near-horizon red-light violation. They also passed the
   transform-pool progress screen at `min_progress_ratio=0.8`.
3. This is still single-tick offline evidence. It does not prove closed-loop
   benefit, latency, comfort, or robustness across the `32` miss records. It
   does not authorize an online selector, 12/36-run replay, CAMP retraining, or
   formal seeds.

Decision: accept this as a positive target-tick recompute gate result and move
to a broader targeted gate before any online wiring. The next admissible step
is to capture and recompute a small target set, for example all step-69 and
late-step misses in `seed_2/npc_0/tl_on` or the `seed_2/npc_4/tl_on` miss
cluster, then summarize coverage, feasibility, progress, and comfort proxy
costs. Keep the DP weights, CAMP weights, atom schema, and formal seeds fixed.

Mathematical boundary: the target snapshot, donor set, splice map, and
recomputed diagnostics are fixed current-tick constants. The transformed set
is finite and deterministic for the snapshot and hyperparameters. This remains
a finite-candidate offline gate, not Benders; no master/subproblem dual cut or
global trajectory-coordinate convexity is claimed. If these diagnostics are
later atomized, CAMP scoring is affine in `w` only for the fixed finite
candidate set, preserving the existing simplex/CVaR/L2 convex master under
that fixed-set interpretation.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Target replay summary | `0765fee80d3bf18f0c956dc4683e6c204ccf27b69a190cbdde8dff799679b6be` |
| Target validation summary | `503f87e4d41404c825f562c4b1519fa94129a8554cc8321f866bb340a31b4f22` |
| Target readiness JSON | `4d48a88bb71028b93f08e5f67319adea439fb9230072c070cb3c30bd2dcb23dd` |
| Target recompute gate JSON | `a1c64587502020b49019bdcd490e4014396577ee3b681510c5dc27b0d61fe9fd` |
| Target recompute gate markdown | `6fee21c5ebbcf713133cde61eafa62db276261bab7054f6e55a757643ca9b706` |
| Target snapshot step 0069 NPZ | `d4efe7aa17cfb7b7513fe4f8236e23db795b053d94438219b1ff1ef8671c53f9` |

### Seed2 npc0 tl-on target-cluster recompute gate

The single positive target tick was broadened to all selected
h30-safe/full-red miss ticks within the same non-formal run:

```text
sample59_86 / seed_2 / npc_0 / spawn_0p3 / tl_on / static
```

This remains one targeted replay prefix, not a 12-run or formal-seed run. The
captured target steps were:

```text
69,185,189,190,191,192,193,194,195,196,197,198,199
```

Remote artifact:

```text
/root/autodl-tmp/camp_dp_target_snapshots_seed2_npc0_tlon_13miss_626718a
```

Configuration: sample59 route, seed `2`, no NPCs, traffic lights on, `200`
steps, K=`8`, redstopfloor05 static weights, raw-prefix logging `80`, and
snapshot capture only at the `13` target steps above. The replay summary and
validation summary both record `camp_microbenchmark_snapshots` with
`selection_effect=false`.

The readiness audit again reported that snapshot tensors are sufficient for
PerfectTracker, red-stopping-margin, and DP reward/full-red recomputation. The
recompute gate used only the `lower_logged_union_red` donor pool.

Aggregate results:

| Check | Result |
| --- | ---: |
| Target snapshots | 13 |
| Selected h30-safe/full-red snapshots | 13 |
| Snapshots with lower-logged-union-red donors | 13 |
| Transform count | 75 |
| Lower recomputed union-red transforms | 74 |
| Hard-feasible transforms | 10 |
| Progress-screen feasible transforms | 10 |
| Lower union-red hard-feasible transforms | 9 |
| Lower union-red progress-feasible transforms | 9 |
| Baseline logged near-red max error | 0.0 |
| Baseline logged full-red max error | 0.0 |
| Min transformed union-red mean/max | 0.0 / 0.0 |

Blocker summary:

| Blocker set | Reason counts |
| --- | --- |
| All hard infeasible transformed candidates | `dp_kinematic: 65` |
| Lower union-red hard infeasible transformed candidates | `dp_kinematic: 65` |
| Lower union-red progress infeasible transformed candidates | none |

Per-target results:

| Step | Selected | Donors | Selected union-red | Lower union-red | Lower union-red hard-feasible | Lower union-red progress-feasible | Hard blocker |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 69 | 1 | 7 | 11.5 | 7 | 7 | 7 | none |
| 185 | 4 | 7 | 30.0 | 7 | 0 | 0 | `dp_kinematic: 7` |
| 189 | 2 | 7 | 32.5 | 7 | 0 | 0 | `dp_kinematic: 7` |
| 190 | 6 | 7 | 29.0 | 7 | 0 | 0 | `dp_kinematic: 7` |
| 191 | 7 | 6 | 32.5 | 6 | 0 | 0 | `dp_kinematic: 6` |
| 192 | 6 | 7 | 27.0 | 7 | 0 | 0 | `dp_kinematic: 7` |
| 193 | 3 | 6 | 31.5 | 6 | 0 | 0 | `dp_kinematic: 6` |
| 194 | 4 | 7 | 34.0 | 7 | 0 | 0 | `dp_kinematic: 7` |
| 195 | 5 | 4 | 33.5 | 4 | 1 | 1 | `dp_kinematic: 3` |
| 196 | 3 | 4 | 34.0 | 4 | 1 | 1 | `dp_kinematic: 3` |
| 197 | 5 | 5 | 35.0 | 5 | 0 | 0 | `dp_kinematic: 5` |
| 198 | 0 | 4 | 33.5 | 3 | 0 | 0 | `dp_kinematic: 3` |
| 199 | 7 | 4 | 33.0 | 4 | 0 | 0 | `dp_kinematic: 4` |

Interpretation:

1. Red-light coverage is strong within this run: `13/13` target snapshots have
   at least one transformed candidate with lower recomputed union-red, and
   `74/75` transformed candidates lower union-red.
2. The industrial blocker is now explicit: most late-step transformed
   candidates violate DP's kinematic hard check after the H10-preserving tail
   splice. The progress screen is not the active blocker once the hard checks
   pass.
3. The early target step `69` remains fully positive (`7/7` lower-red,
   hard-feasible, and progress-feasible). Late steps `195` and `196` retain one
   feasible lower-red transform each. The remaining late targets are blocked by
   kinematics, not by missing red-light benefit.

Decision: accept the stop-aware splice as a real red-risk reduction mechanism
under fixed-snapshot recomputation, but reject direct deployment of the current
raw splice. The next admissible iteration is a kinematic-aware transformed
candidate diagnostic: preserve the same finite-snapshot and H10-anchor
boundary, but add a deterministic acceleration/curvature/heading smoothing or
projection step whose constraints are explicitly tied to the DP kinematic
check. Do not implement an online selector, run paired 12/36-run replay, train
CAMP weights, or touch formal seeds until the kinematic blocker is resolved on
target snapshots and documented.

Mathematical boundary: all arrays, donor sets, splice transforms, and
recomputed diagnostics are fixed current-tick constants from non-formal
snapshots. The analysis remains a finite-candidate offline gate, not Benders;
no dual cuts or global trajectory-coordinate convexity are claimed. A future
kinematic-aware projection must either be treated as another deterministic
finite-candidate transform or, if claimed as an optimization atom, must have
its convexity and master/subproblem role stated separately.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Target-cluster replay summary | `cc4f74585f14993661698ea3d4a23b906f9b71e842d80cd8cacb6c25950012b7` |
| Target-cluster validation summary | `e884709fc5425773a0e8cfc71f96397c2b4da3cdc5bf17d933cf3f0d7e9d164a` |
| Target-cluster readiness JSON | `22ccd89914ec6ec73922872e5fc1b910d1e5e216813d64de1c9bdcbf0686cda7` |
| Target-cluster recompute gate JSON | `7ffee93fe3b1be95f23d47f6e8c9d41e24eebd9981d63d07a525fc448dda8d9e` |
| Target-cluster recompute gate markdown | `3e4c4b3b5394f3019a53e3e26faab54f882bfc8142c448eadb02b01429da18e2` |

### Seed2 npc0 tl-on donor-offset heading diagnostic

Follow-up to the target-cluster gate above: the same fixed snapshots and
`lower_logged_union_red` donor pool were re-evaluated with a heading-only
diagnostic switch:

```text
--heading_mode donor_offset
```

The XY splice remains H10-preserving. Instead of reconstructing heading from
finite differences over the spliced XY path, the diagnostic preserves the
selected candidate's heading prefix through H10, aligns the donor heading tail
at the same anchor, and smoothstep-blends the heading tail. This is still a
deterministic finite-candidate transform over fixed current-tick snapshots; it
does not change CAMP weights, DP weights, online selection, or the master
problem.

Remote artifact:

```text
/root/autodl-tmp/camp_dp_target_snapshots_seed2_npc0_tlon_13miss_626718a
```

Aggregate results:

| Check | Finite-difference heading | Donor-offset heading |
| --- | ---: | ---: |
| Target snapshots | 13 | 13 |
| Transform count | 75 | 75 |
| Lower recomputed union-red transforms | 74 | 74 |
| Hard-feasible transforms | 10 | 73 |
| Progress-screen feasible transforms | 10 | 64 |
| Lower union-red hard-feasible transforms | 9 | 72 |
| Lower union-red progress-feasible transforms | 9 | 63 |
| Hard infeasible `dp_kinematic` blockers | 65 | 2 |
| Progress infeasible `dp_underprogress` blockers | 0 | 9 |
| Baseline logged near/full red max error | 0.0 / 0.0 | 0.0 / 0.0 |
| Min transformed union-red mean/max | 0.0 / 0.0 | 0.0 / 0.0 |

Per-target donor-offset results:

| Step | Selected | Donors | Selected union-red | Lower union-red | Hard-feasible | Progress-feasible | Lower union-red hard-feasible | Lower union-red progress-feasible | Hard blocker |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 69 | 1 | 7 | 11.5 | 7 | 7 | 7 | 7 | 7 | none |
| 185 | 4 | 7 | 30.0 | 7 | 7 | 7 | 7 | 7 | none |
| 189 | 2 | 7 | 32.5 | 7 | 7 | 7 | 7 | 7 | none |
| 190 | 6 | 7 | 29.0 | 7 | 7 | 7 | 7 | 7 | none |
| 191 | 7 | 6 | 32.5 | 6 | 6 | 6 | 6 | 6 | none |
| 192 | 6 | 7 | 27.0 | 7 | 6 | 6 | 6 | 6 | `dp_kinematic: 1` |
| 193 | 3 | 6 | 31.5 | 6 | 6 | 6 | 6 | 6 | none |
| 194 | 4 | 7 | 34.0 | 7 | 7 | 7 | 7 | 7 | none |
| 195 | 5 | 4 | 33.5 | 4 | 4 | 1 | 4 | 1 | none |
| 196 | 3 | 4 | 34.0 | 4 | 4 | 1 | 4 | 1 | none |
| 197 | 5 | 5 | 35.0 | 5 | 4 | 4 | 4 | 4 | `dp_kinematic: 1` |
| 198 | 0 | 4 | 33.5 | 3 | 4 | 1 | 3 | 0 | none |
| 199 | 7 | 4 | 33.0 | 4 | 4 | 4 | 4 | 4 | none |

Interpretation:

1. The earlier kinematic blocker was mostly caused by finite-difference
   heading reconstruction around the H10 tail splice. Preserving and
   anchor-aligning heading reduces DP kinematic hard failures from `65` to `2`
   on the same `75` transformed candidates.
2. The red-light benefit is retained: `74/75` transformed candidates still
   lower recomputed union-red, and all `13/13` target snapshots retain at
   least one lower-red transformed candidate.
3. The remaining active blocker is no longer primarily hard kinematics. The
   progress screen rejects `9` transformed candidates, concentrated in late
   steps `195`, `196`, and `198`.

Decision: accept donor-offset heading as a positive fixed-snapshot diagnostic
and as evidence that a kinematic-aware finite-candidate transform is plausible.
Do not deploy it online yet. The next admissible step is to make the transform
explicitly gateable by progress/comfort budgets and then run a small closed-loop
shadow or default-off selector check only after the offline budget gate is
predeclared and documented.

Mathematical boundary: the heading transform is deterministic over fixed
candidate headings and anchor constants. It is not a Benders atom by itself and
does not introduce a master/subproblem decomposition or dual cuts. If its
outputs are later atomized as per-candidate diagnostics, those diagnostics are
fixed constants at the current tick, so CAMP's affine scoring in `w` and the
simplex/CVaR/L2 master convexity are unchanged for that fixed finite candidate
set.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Donor-offset recompute gate JSON | `bed295ef47d09e48f7a210e3881f4b6417c6256189fbda72f1ae7b61703b97ab` |
| Donor-offset recompute gate markdown | `d772f41fddf8377414967446454f07413842dc44c31eed38dedd3d944b62c06b` |

### Seed2 npc0 tl-on donor-offset budget sensitivity

The donor-offset heading diagnostic above was extended with an offline budget
sensitivity table. The table is posterior diagnostic evidence over fixed
transformed candidates only. A candidate must:

1. lower recomputed union-red;
2. pass the DP hard checks;
3. stay within an absolute DP reward-progress loss budget relative to the
   selected baseline candidate;
4. stay within a DP smoothness reward loss budget relative to the selected
   baseline candidate.

This is intentionally not an online selector and does not relax or retrain
CAMP/DP. The smoothness quantity is the scalar `smoothness` reward reported by
DP's reward breakdown, so it is a DP comfort proxy rather than a physical jerk
or lateral-acceleration threshold.

Remote artifact:

```text
/root/autodl-tmp/camp_dp_target_snapshots_seed2_npc0_tlon_13miss_626718a
```

Aggregate donor-offset results are unchanged before applying budgets:

| Check | Result |
| --- | ---: |
| Target snapshots | 13 |
| Transform count | 75 |
| Lower recomputed union-red transforms | 74 |
| Hard-feasible transforms | 73 |
| Progress-screen feasible transforms | 64 |
| Lower union-red hard-feasible transforms | 72 |
| Lower union-red progress-feasible transforms | 63 |
| Hard infeasible `dp_kinematic` blockers | 2 |
| Progress infeasible `dp_underprogress` blockers | 9 |

Budget sensitivity:

| Progress loss budget (m) | Smoothness loss budget | Candidate count | Snapshots with candidate |
| ---: | ---: | ---: | ---: |
| 0.5 | 0.0 | 1 | 1 |
| 0.5 | 0.5 | 7 | 2 |
| 0.5 | 1.0 | 7 | 2 |
| 1.0 | 0.0 | 7 | 1 |
| 1.0 | 0.5 | 29 | 7 |
| 1.0 | 1.0 | 35 | 8 |
| 1.5 | 0.0 | 7 | 1 |
| 1.5 | 0.5 | 35 | 8 |
| 1.5 | 1.0 | 54 | 10 |

At the widest diagnostic budget (`1.5 m` progress loss, `1.0` DP smoothness
reward loss), coverage remains meaningful but incomplete: `54/75` candidates
and `10/13` snapshots pass. The three still-uncovered target steps are `69`,
`194`, and `197`; each requires either a larger progress/smoothness budget or
a different transform. At the tightest budget (`0.5 m`, smoothness nonworse),
coverage collapses to `1/75` candidates and `1/13` snapshots, so this evidence
does not support a tight-budget online override.

Decision: accept the budget table as the next offline gate. The transform is
promising only under explicitly relaxed progress/smoothness proxy budgets.
Before any closed-loop shadow or default-off selector run, the next step must
predeclare an admissible budget policy and decide whether `1.5 m` progress loss
and `1.0` DP smoothness reward loss are industrially acceptable, or whether the
transform must be improved to cover more snapshots under stricter budgets.

Mathematical boundary: progress and smoothness are fixed per-candidate
diagnostics after DP reward recomputation on fixed snapshots. The budget table
is finite, deterministic, and outcome-free. It is not Benders and introduces no
dual cuts. If these fixed diagnostics become CAMP atoms later, CAMP scoring
remains affine in `w` and the existing simplex/CVaR/L2 master remains convex
only for the fixed finite candidate set.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Donor-offset budget JSON | `2a7e9953892f585e0363351e7c5d59af976a1f7c7889a1e32465ac6b2e105060` |
| Donor-offset budget markdown | `570730f534e8fc8f7df319c79009235b9188b0de517b11e82d2d79882f6609cf` |

### Seed2 npc0 tl-on H10-preserving blend-step sweep

The previous donor-offset budget gate showed that the H10-preserving transform
was promising but budget-sensitive. A follow-up offline sweep kept the same
fixed snapshots, donor pool, `anchor_steps=10`, and `heading_mode=donor_offset`,
and varied only the post-H10 smoothstep blend length:

```text
blend_steps in {0, 5, 10, 15, 20, 30, 40}
```

This does not change DP, CAMP, the selector, weights, atom schema, or the
master problem. It is still a fixed finite-candidate diagnostic.

Remote artifact:

```text
/root/autodl-tmp/camp_dp_target_snapshots_seed2_npc0_tlon_13miss_626718a/blend_sweep_28f1cc2
```

Aggregate sweep results:

| Blend steps | Lower red | Hard feasible | Lower-red hard feasible | Progress feasible | Lower-red progress feasible | Kinematic blockers | Underprogress blockers | Budget 0.5/0.0 count/snapshots | Budget 1.0/0.5 count/snapshots | Budget 1.5/1.0 count/snapshots |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 74 | 75 | 74 | 62 | 61 | 0 | 13 | 1 / 1 | 33 / 7 | 67 / 12 |
| 5 | 74 | 70 | 69 | 61 | 60 | 5 | 9 | 0 / 0 | 32 / 7 | 62 / 12 |
| 10 | 74 | 73 | 72 | 64 | 63 | 2 | 9 | 1 / 1 | 29 / 7 | 54 / 10 |
| 15 | 74 | 75 | 74 | 66 | 65 | 0 | 9 | 7 / 1 | 41 / 9 | 59 / 11 |
| 20 | 74 | 69 | 68 | 63 | 62 | 6 | 6 | 12 / 2 | 49 / 9 | 61 / 11 |
| 30 | 74 | 70 | 69 | 61 | 60 | 5 | 9 | 11 / 4 | 58 / 12 | 66 / 13 |
| 40 | 74 | 75 | 74 | 66 | 65 | 0 | 9 | 24 / 6 | 68 / 13 | 74 / 13 |

Wide-budget uncovered target steps:

| Blend steps | Uncovered at 1.5m progress / 1.0 smoothness |
| ---: | --- |
| 0 | `69` |
| 5 | `69` |
| 10 | `69, 194, 197` |
| 15 | `69, 194` |
| 20 | `69, 198` |
| 30 | none |
| 40 | none |

Interpretation:

1. The budget limitation is not fundamental to the donor-offset idea. A longer
   post-H10 blend improves the progress/smoothness tradeoff substantially.
2. `blend_steps=40` is the best observed offline configuration in this sweep:
   it keeps `74/75` lower-red transformed candidates, `75/75` hard-feasible
   candidates, and reaches full `13/13` snapshot coverage at the moderate
   `1.0 m` progress / `0.5` DP-smoothness budget.
3. Tight-budget coverage is still incomplete: even at `blend_steps=40`, the
   strict `0.5 m` progress / smoothness-nonworse gate covers only `24/75`
   candidates and `6/13` snapshots.

Decision: accept `blend_steps=40` as the next offline diagnostic configuration
for subsequent default-off or shadow analysis, but do not deploy an online
selector yet. The next admissible gate is a predeclared fixed-candidate shadow
rule using `anchor_steps=10`, `blend_steps=40`, `heading_mode=donor_offset`,
lower union-red, DP hard feasibility, and explicit progress/smoothness budgets.
That gate must remain fail-closed, deterministic, default-off, and
`selection_effect=false` until a closed-loop shadow result proves otherwise.

Mathematical boundary: changing `blend_steps` changes only the deterministic
finite-candidate transform applied to fixed current-tick snapshots. No Benders
cut, dual problem, online optimization, or trajectory-coordinate convexity is
claimed. If diagnostics from this transform are later atomized, they are fixed
per-candidate constants for the current tick; CAMP scoring remains affine in
`w` and the existing simplex/CVaR/L2 master remains convex only under that
fixed finite-candidate interpretation.

Artifact SHA-256:

| Blend steps | JSON SHA-256 | Markdown SHA-256 |
| ---: | --- | --- |
| 0 | `416dc0b0096ffb95e3aa55af8738be46b697850d8be39455792fc14ae2589155` | `effdc2ba0660fe97677ef69cab2a1dfd5a174fc0fc8f2b3555a3debdd0dd75ba` |
| 5 | `61b643c440ec1e7a8c829d74cfd35d50fc03200985175caeb25299e8e8137768` | `a137514d7ccbc836b3b955d9e17fa7f25fbbf73343da73955ee70afd327bea15` |
| 10 | `aeef7fe63af0ef2a6fac2e88986566337d971b4899937ee3e7caadff79c55fd9` | `570730f534e8fc8f7df319c79009235b9188b0de517b11e82d2d79882f6609cf` |
| 15 | `43b99c0f92fd793687ae25332ad66d0fc07bfda238de59565cbc124795a342ff` | `c581b8bdb50cf97392e6da6f601291f08f604228e5ea8a38b14ea586965ed753` |
| 20 | `fdbaf176d6186892f7548bc8d1cc60eacc6d2cde6461b558da1c98d9c315eee0` | `83ebc0f152e7c157fe12d3378b200ae3fbe215246bad01d8bcb4efefccc27127` |
| 30 | `711b1348139a34514be1e62d2f00150f77329b806557b2c6de5ea22a0a946d4b` | `f564505f287b5dcd953e0d1f92d4b40e163603671f89a5434cf79abd8409098b` |
| 40 | `9c7fce73d9224ef388b94966f1fc41931ddb21e37a6d81f6de9b4a291fd2c292` | `cfdaec770c77d595674c8da71af629fbc202af6664796167ce7ff255070f3121` |

### Seed2 npc0 tl-on fixed-candidate shadow rule

The H10-preserving blend sweep selected `blend_steps=40` as the next
diagnostic configuration. A default-off fixed-candidate shadow rule was then
added to the offline recompute analyzer and evaluated on the same `13` target
snapshots.

The rule is:

1. keep `anchor_steps=10`, `blend_steps=40`, and `heading_mode=donor_offset`;
2. construct only fixed transformed candidates from the current snapshot;
3. require lower recomputed union-red than the selected baseline candidate;
4. require DP hard feasibility;
5. require progress loss at most `1.0 m`;
6. require DP smoothness reward loss at most `0.5`;
7. choose deterministically by union-red, smoothness loss, progress loss, then
   transformed-candidate index;
8. fail closed to the baseline when no candidate is admissible.

This rule is explicitly default-off and has `selection_effect=false`. It is a
fixed-snapshot shadow diagnostic, not an online selector and not a closed-loop
replay.

Remote artifact:

```text
/root/autodl-tmp/camp_dp_target_snapshots_seed2_npc0_tlon_13miss_626718a/shadow_rule_dc989cb
```

Command configuration:

```text
--anchor_steps 10
--blend_steps 40
--heading_mode donor_offset
--donor_pool lower_logged_union_red
--enable_shadow_rule
--shadow_progress_loss_budget_m 1.0
--shadow_smoothness_loss_budget 0.5
```

Aggregate results:

| Check | Result |
| --- | ---: |
| Target snapshots | 13 |
| Transform count | 75 |
| Lower-red transforms | 74 |
| Hard-feasible transforms | 75 |
| Lower-red hard-feasible transforms | 74 |
| Budget-admissible transformed candidates | 68 |
| Shadow changed snapshots | 13 / 13 |
| Chosen union-red mean / max | 0.0 / 0.0 |
| Chosen progress loss mean / max | 0.609184 / 0.935844 |
| Chosen smoothness loss mean / max | -0.122078 / 0.497635 |
| Selection effect | false |
| Online selector change | false |

Per-target chosen candidate diagnostics:

| Step | Selected | Donors | Selected union-red | Admissible | Chosen transformed index | Chosen union-red | Progress loss | Smoothness loss |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 69 | 1 | 7 | 11.5 | 1 | 6 | 0.0 | 0.935844 | 0.497635 |
| 185 | 4 | 7 | 30.0 | 7 | 2 | 0.0 | 0.462917 | -0.317794 |
| 189 | 2 | 7 | 32.5 | 7 | 4 | 0.0 | 0.669576 | -0.195778 |
| 190 | 6 | 7 | 29.0 | 7 | 6 | 0.0 | 0.339281 | -0.258445 |
| 191 | 7 | 6 | 32.5 | 6 | 4 | 0.0 | 0.631163 | -0.221211 |
| 192 | 6 | 7 | 27.0 | 7 | 5 | 0.0 | 0.208706 | -0.160607 |
| 193 | 3 | 6 | 31.5 | 6 | 5 | 0.0 | 0.513660 | -0.308481 |
| 194 | 4 | 7 | 34.0 | 7 | 6 | 0.0 | 0.758222 | -0.040612 |
| 195 | 5 | 4 | 33.5 | 4 | 1 | 0.0 | 0.718473 | -0.080035 |
| 196 | 3 | 4 | 34.0 | 4 | 1 | 0.0 | 0.740857 | -0.087423 |
| 197 | 5 | 5 | 35.0 | 5 | 3 | 0.0 | 0.807570 | -0.015439 |
| 198 | 0 | 4 | 33.5 | 3 | 0 | 0.0 | 0.587558 | -0.212489 |
| 199 | 7 | 4 | 33.0 | 4 | 2 | 0.0 | 0.545558 | -0.186338 |

Interpretation:

1. The predeclared fixed-candidate rule covers every target miss in this
   snapshot cluster under the moderate `1.0 m` progress / `0.5` DP-smoothness
   budget.
2. The selected transformed candidates all reduce recomputed union-red to
   `0.0` while staying inside the declared budgets. The worst progress loss is
   `0.935844 m`; the worst DP smoothness reward loss is `0.497635`.
3. This is stronger than the earlier budget table because the rule is now
   deterministic and fail-closed, but it is still not closed-loop evidence.
   The transform may change later ego state, candidate generation, latency, and
   future traffic-light interactions once wired into replay.

Decision: accept the fixed-candidate shadow rule as the next offline gate. The
next admissible step is a default-off closed-loop shadow run on non-formal
sample59 seeds `1/2/3`, using the same `anchor=10`, `blend=40`,
`donor_offset`, and `1.0/0.5` budgets, while logging both baseline and shadow
decisions. Do not run formal seeds or train CAMP/DP. If closed-loop shadow
latency or comfort degrades, reject the online path and retain this only as
offline diagnostic math.

Mathematical boundary: the shadow rule operates over a fixed finite transformed
candidate set produced from current-tick constants. The chosen diagnostics are
fixed values after DP reward recomputation. The rule is deterministic and
fail-closed, but it is not Benders, does not introduce a master/subproblem
dual, and does not prove trajectory-coordinate convexity. If these diagnostics
are later atomized, CAMP scoring remains affine in `w` and the existing
simplex/CVaR/L2 master remains convex only for that fixed finite candidate
set.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Shadow JSON | `500b42c9e40f7c7650ce424985c338ff93d671c62dad41d6af7419419a0ffca9` |
| Shadow markdown | `4be3eceacc98e0aaeceef8b46b8bb7350642b3618a8ec026708b0c3d3fc3441d` |

### Closed-loop splice shadow logging smoke

The fixed-candidate shadow rule was wired into the replay script as a
default-off closed-loop shadow logger. It recomputes DP reward for transformed
candidates and records the hypothetical choice, but it never assigns that
choice to `selected_index` and never changes the trajectory fed to the
PerfectTracker.

Implementation contract:

```text
--camp_splice_shadow_rule
--camp_splice_shadow_anchor_steps 10
--camp_splice_shadow_blend_steps 40
--camp_splice_shadow_heading_mode donor_offset
--camp_splice_shadow_progress_loss_budget_m 1.0
--camp_splice_shadow_smoothness_loss_budget 0.5
```

The logger is rejected by argument validation if combined with top1 mode,
non-DP-reward feasibility, lexicographic preselection, underprogress
relaxation, or PerfectTracker command postselection. Summary and validation
metadata both record:

```text
camp_splice_shadow_rule.selection_effect = false
camp_splice_shadow_rule.online_selector_change = false
camp_splice_shadow_rule.default_off = true
```

Two non-formal smoke runs were executed on AutoDL with fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4` and CAMP commit
`bebce21978300e4305e492a610dcdef4b9ddc31a`.

#### Metadata fail-closed smoke

Artifact:

```text
/root/autodl-tmp/camp_dp_splice_shadow_smoke_bebce21_seed101_steps10
```

Configuration: sample59 route, seed `101`, no NPCs, traffic lights on,
perfect tracking, `10` steps, static `redstopfloor05`, K=`8`.

Result:

| Check | Result |
| --- | ---: |
| Records | 10 |
| Shadow records present | 10 |
| Selection unchanged | true |
| Selection effects | `{false}` |
| Changed records | 0 |
| Reason counts | `no_transformed_candidates: 10` |
| Mean / max splice-shadow latency | 0.0505 ms / 0.0589 ms |

This verifies field shape, metadata propagation, summary resummarization, and
fail-closed behavior when no lower-red donors exist in the early route prefix.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Replay summary | `32f9d1468ec26568d0f2cebd50f4b69f3da68738ead022b9e0b4bfb78bbb9cd9` |
| Validation summary | `fb7321ded8270fe7781a8d4c858dffff4df733da4c17a0eef3dfed4430f0d3c1` |
| Selection log | `dc0457c63a45d97d76e0e0e2bef21258fa0b0173006b9a4cc6a6b5d3f0c2ea6c` |

#### Target-prefix transformed-branch smoke

Artifact:

```text
/root/autodl-tmp/camp_dp_splice_shadow_target_smoke_bebce21_seed2_steps75
```

Configuration: sample59 route, seed `2`, no NPCs, traffic lights on, perfect
tracking, `75` steps, static `redstopfloor05`, K=`8`. This prefix reaches the
previously identified step-69 h30-safe/full-red miss.

Result:

| Check | Result |
| --- | ---: |
| Records | 75 |
| Shadow records present | 75 |
| Selection unchanged | true |
| Selection effects | `{false}` |
| Changed records | 1 |
| Changed steps | `69` |
| Admissible transformed candidates | 1 |
| Chosen donor index at step 69 | 7 |
| Chosen union-red | 0.0 |
| Chosen progress loss | 0.935844 m |
| Chosen DP smoothness loss | 0.497635 |
| Reason counts | `budget_admissible_lower_red_candidate: 1`, `no_transformed_candidates: 74` |
| Mean / max splice-shadow latency | 0.3035 ms / 19.1166 ms |

This verifies the transformed-candidate DP reward recomputation branch in a
real replay prefix while preserving the actual closed-loop behavior. The
overall run remains a smoke; latency from a single 75-step prefix is not an
industrial performance gate.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Replay summary | `11fffdbb7ce90c0c8745abe696a627efedb39d8d6ff6682f47c28faa5c6bc00a` |
| Validation summary | `39d5d52dfb98a08b9842273c84473102975c4b76c4e44ce568b7ce5dc74383f0` |
| Selection log | `d239d71f5be438898b64cb11210560796d6a9f45f11d07b2431d297814aaee2b` |

Decision: accept the closed-loop shadow logging gate. The next admissible
experiment is a non-formal sample59 shadow-only pilot over seeds `1/2/3`, NPC
counts `0/4`, and traffic lights on/off, still with `selection_effect=false`.
Do not switch the shadow choice into the executed selected trajectory until
that pilot shows coverage, latency, and comfort behavior are acceptable.

Mathematical boundary: the replay logger recomputes diagnostics for a fixed
finite transformed set at each tick. These diagnostics are constants for that
tick and are never used to update CAMP weights, DP weights, or the master
problem. The rule is deterministic and fail-closed, but it is not Benders and
does not define a dual subproblem or valid cuts. If later converted to CAMP
atoms, affine scoring and simplex/CVaR/L2 convexity remain valid only for the
fixed finite candidate set at the tick.

### Sample59 splice-shadow pilot

Commit `639cb8482ba94b26b6c75726c144bf5258382ea6` threads the default-off
splice-shadow logger through the benchmark matrix runner. The matrix runner now
forwards the splice-shadow parameters only to CAMP variants and rejects
combinations with lexicographic preselection, PerfectTracker command
postselection, underprogress relaxation, non-`dp_reward` feasibility, or missing
reward config. This keeps the run shadow-only and avoids mixing this diagnostic
with previously rejected selector branches.

Verification:

```text
Local:  py -3.12 -m py_compile scripts\integrations\run_diffusion_planner_camp_benchmark_matrix.py
Local:  py -3.12 -m pytest camp_core\tests\test_diffusion_planner_benchmark_matrix.py camp_core\tests\test_diffusion_planner_replay_summary.py
AutoDL: /root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests/test_diffusion_planner_benchmark_matrix.py camp_core/tests/test_diffusion_planner_replay_summary.py
```

All three checks passed with `19 passed`. CAMP local, GitHub, and AutoDL were
synchronized to `639cb8482ba94b26b6c75726c144bf5258382ea6`. Diffusion Planner
remained fixed at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Non-formal pilot artifact:

```text
/root/autodl-tmp/camp_dp_splice_shadow_sample59_pilot_639cb84
```

Configuration: `sample59_86`, seeds `1/2/3`, NPC counts `0/4`, traffic lights
on/off, static `redstopfloor05`, K=`8`, perfect tracking, `200` steps,
`camp_feasibility_source=dp_reward`, `selection_effect=false`,
`anchor_steps=10`, `blend_steps=40`, `heading_mode=donor_offset`, progress loss
budget `1.0 m`, smoothness loss budget `0.5`. Formal seeds `11/12/13` were not
used.

Aggregate result:

| Check | Result |
| --- | ---: |
| Replay summaries / validation summaries / selection logs | 12 / 12 / 12 |
| Selection records | 2400 |
| Splice-shadow records | 2400 |
| Selection effects | `{false}` |
| Online selector change | `{false}` |
| Changed shadow decisions | 31 |
| Admissible transformed candidates | 139 |
| Reason counts | `budget_admissible_lower_red_candidate: 31`, `no_budget_admissible_lower_red_candidate: 57`, `no_transformed_candidates: 2312` |
| Runs with changed decisions | `seed_2/npc_0/tl_on: 13`, `seed_2/npc_4/tl_on: 18` |
| Shadow latency mean-of-run-means / max | `0.796080 ms` / `24.110364 ms` |
| p95 selection latency mean / max | `94.463150 ms` / `115.368733 ms` |
| Route completion mean / min / max | `0.154349` / `0.124425` / `0.164963` |
| Fallback rate mean / min / max | `0.201667` / `0.0` / `0.57` |
| Planned red-light violation rate mean / max | `0.044583` / `0.45` |
| Realized red-light violation rate mean / max | `0.019263` / `0.221106` |

For the 31 changed shadow decisions, the baseline selected union-red averaged
`29.709677`, the chosen transformed union-red averaged `15.467742`, and the
mean union-red reduction was `14.241935` with min/max reduction
`0.5`/`35.0`. The progress loss stayed within the declared budget
(`mean=0.564483 m`, `max=0.935844 m`) and the smoothness loss stayed within the
declared budget (`mean=-0.037839`, `max=0.497635`).

Changed steps:

| Run | Steps |
| --- | --- |
| `sample59_86/seed_2/npc_0/spawn_0p3/tl_on/static` | `69, 185, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199` |
| `sample59_86/seed_2/npc_4/spawn_0p3/tl_on/static` | `110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127` |

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Aggregate JSON | `f314aaa6f28535201fbddfa09b531c82abbabce92f7af8478036fb755ce6f2a9` |
| Aggregate Markdown | `0690f3bc2299649463608f7c175b86d65a34f0e7f0386d5930405baa7975a5a1` |
| Per-file manifest | `8027346a3356ba3c712eb0baaf833545053abaccab99bcbe61fa26310e3f00b0` |

Decision: accept the matrix-runner wiring and the sample59 shadow-only pilot as
valid evidence that the fixed-candidate splice rule has nontrivial coverage on
the previously problematic `sample59` red-light states. Do not promote it to an
executed online selector yet. The run has no selection effect, so closed-loop
metrics still describe the baseline static policy, not an improved executed
policy. The maximum per-run p95 selection latency is also above the 100 ms
industrial gate, and 57 records had lower-red transformed candidates that failed
the declared progress/smoothness budget.

Next admissible step: audit the 31 changed and 57 no-budget records in the
pilot artifact to separate safety opportunity, budget tightness, and latency
cost. Any online selector proposal must first provide a cheaper or amortized
fixed-candidate implementation, prove deterministic fail-closed behavior, and
pass a paired non-formal pilot with p95 latency below 100 ms with margin. Do not
train CAMP, retrain DP, alter atom schema, or use formal seeds from this
shadow-only result.

### Splice-shadow pilot record audit

Commit `4153a36ad2ebe20fc2a0bdb7e780a79f0e25dc9d` adds a read-only
selection-log audit for the sample59 splice-shadow pilot. The analyzer consumes
only fixed finite constants already logged by the default-off shadow path. It
does not recompute DP reward, does not train, and has no selection effect.

Verification:

```text
Local:  py -3.12 -m py_compile scripts\integrations\analyze_diffusion_planner_splice_shadow_pilot.py
Local:  py -3.12 -m pytest camp_core\tests\test_diffusion_planner_splice_shadow_pilot_audit.py
AutoDL: /root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests/test_diffusion_planner_splice_shadow_pilot_audit.py
```

All checks passed. CAMP local, GitHub, and AutoDL were synchronized to
`4153a36ad2ebe20fc2a0bdb7e780a79f0e25dc9d`. Diffusion Planner remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Audit artifact:

```text
/root/autodl-tmp/camp_dp_splice_shadow_sample59_pilot_639cb84/splice_shadow_pilot_audit_4153a36.json
/root/autodl-tmp/camp_dp_splice_shadow_sample59_pilot_639cb84/splice_shadow_pilot_audit_4153a36.md
```

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Audit JSON | `068ff048d08e110236a65487e4e67a151b6fcc90b27d572827297ffbb3979caa` |
| Audit Markdown | `909b1e92e2fbd700609a91e7eb4e81200db4dc88c97751f9a56cb90d18b23b83` |

Counts:

| Check | Result |
| --- | ---: |
| Logs / total records | 12 / 2400 |
| Missing splice-shadow records | 0 |
| Target records | 88 |
| Changed records | 31 |
| No-budget records | 57 |
| Selection effects | `{false}` |
| Online selector change | `{false}` |
| No-budget class counts | `no_hard_feasible_transformed_candidates: 56`, `splice_removed_lower_red_advantage: 1` |

Changed records:

| Metric | Result |
| --- | ---: |
| Baseline union-red mean / max | `29.709677` / `35.0` |
| Chosen union-red mean / max | `15.467742` / `34.5` |
| Union-red reduction mean / p95 / max | `14.241935` / `34.0` / `35.0` |
| Zero-union changed records | 13 |
| Progress loss mean / p95 / max | `0.564483 m` / `0.917708 m` / `0.935844 m` |
| Smoothness loss mean / p95 / max | `-0.037839` / `0.241830` / `0.497635` |

No-budget records:

| Metric | Result |
| --- | ---: |
| Baseline union-red mean / max | `34.271930` / `41.0` |
| Donor count mean / p95 / max | `4.175439` / `7.0` / `7.0` |
| Hard-feasible transformed count mean / p95 / max | `0.017544` / `0.0` / `1.0` |
| Lower-red transformed count mean / p95 / max | `3.561404` / `7.0` / `7.0` |
| Lower-red hard-feasible count mean / max | `0.0` / `0.0` |

Latency over the 88 target records:

| Metric | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| All target records | `20.435994 ms` | `23.759643 ms` | `24.110364 ms` |
| Changed records | `20.649156 ms` | `23.746042 ms` | `24.110364 ms` |
| No-budget records | `20.320063 ms` | `23.747451 ms` | `23.862518 ms` |
| Internal full-red component | `0.627614 ms` | `0.629939 ms` | `2.744707 ms` |

Run breakdown:

| Run | Changed | No-budget | Main finding |
| --- | ---: | ---: | --- |
| `sample59_86/seed_2/npc_0/spawn_0p3/tl_on/static` | 13 | 0 | Large safety opportunity late in the run; mean union-red reduction `30.538462`. |
| `sample59_86/seed_2/npc_4/spawn_0p3/tl_on/static` | 18 | 57 | Smaller changed reductions plus many transformed candidates that lose hard feasibility after splice. |

Decision: the no-budget label was too coarse. Existing evidence does not show
that the declared `1.0 m` / `0.5` budget is the main blocker. In this pilot,
`56/57` no-budget records failed because no transformed candidate was
hard-feasible after recompute, and the remaining record lost its lower-red
advantage after the H10-preserving splice. The next engineering question is
therefore not primarily budget tuning. It is whether the splice transformation
can be made hard-feasibility preserving and cheaper, or whether this branch
should remain a shadow-only diagnostic.

Mathematical boundary: this audit is not Benders. It reads fixed finite
per-tick constants from `camp_selection_log.json`. It does not add atoms, update
CAMP weights, update DP weights, define a dual subproblem, or generate cuts.
Because transformed per-donor reward arrays are not logged, the audit does not
claim exact per-donor budget attribution for no-budget records. Future logging
would be required to distinguish progress-loss and smoothness-loss blockers
without recomputing the DP reward.

Next admissible step: before any online selector or paired executed pilot,
profile and redesign the transformed-candidate branch for hard-feasibility and
latency. A viable next screen should either show that a cheaper transformation
preserves lower-red hard feasibility on the 57 blocked records, or reject the
splice branch as an online mechanism. Do not train CAMP, retrain DP, alter atom
schema, or use formal seeds from this audit.

### Splice-shadow infeasibility reason logging

Commit `4f4c321932fd48b005147b2f941592f69f62ea46` adds aggregate transformed
hard-infeasibility reason counts to the default-off splice-shadow payload. The
runner already computes `reward_hard_feasibility(transformed_rewards)` inside
the shadow path; this change only preserves the reason counts in
`camp_selection_log.json`, `camp_replay_summary.json`, and
`camp_validation_summary.json`. It does not add candidates, change CAMP scores,
change the selected trajectory, train CAMP, or modify DP.

Verification:

```text
Local:  py -3.12 -m py_compile scripts\integrations\run_diffusion_planner_camp_replay.py scripts\integrations\analyze_diffusion_planner_splice_shadow_pilot.py
Local:  py -3.12 -m pytest camp_core\tests\test_diffusion_planner_replay_summary.py camp_core\tests\test_diffusion_planner_splice_shadow_pilot_audit.py
AutoDL: /root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests/test_diffusion_planner_replay_summary.py camp_core/tests/test_diffusion_planner_splice_shadow_pilot_audit.py
```

All checks passed with `17 passed`. CAMP local, GitHub, and AutoDL were
synchronized to `4f4c321932fd48b005147b2f941592f69f62ea46`. Diffusion Planner
remained fixed at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

A single non-formal reason-field smoke was then run on the known problematic
sample59 configuration:

```text
/root/autodl-tmp/camp_dp_splice_shadow_reason_smoke_4f4c321_seed2_npc4_tlon_steps200
```

Configuration: `sample59_86`, seed `2`, NPC count `4`, traffic lights on,
static `redstopfloor05`, K=`8`, perfect tracking, `200` steps,
`selection_effect=false`, `anchor_steps=10`, `blend_steps=40`,
`heading_mode=donor_offset`, progress loss budget `1.0 m`, smoothness loss
budget `0.5`. Formal seeds `11/12/13` were not used.

Result:

| Check | Result |
| --- | ---: |
| Records | 200 |
| Splice-shadow target records | 75 |
| Changed records | 18 |
| No-budget records | 57 |
| No-transformed-candidate records | 125 |
| Selection effects | `{false}` |
| Online selector change | `{false}` |
| No-budget class counts | `no_hard_feasible_transformed_candidates: 56`, `splice_removed_lower_red_advantage: 1` |
| Hard-infeasible reason counts | `dp_lane_crossing: 101`, `dp_red_light: 237` |
| Lower-red hard-infeasible reason counts | `dp_lane_crossing: 83`, `dp_red_light: 203` |
| Splice-shadow latency mean / max over all records | `7.746041 ms` / `24.311544 ms` |
| Splice-shadow latency mean / p95 / max over target records | `20.568445 ms` / `23.665907 ms` / `24.311544 ms` |
| p95 total selection latency | `116.558737 ms` |

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Replay summary | `53729d049a23fe038ef1ba56a59508ae5cd3b230020cd8e36f165983c52365b7` |
| Validation summary | `cff1a20708a8c34240facbd66ebe6c68bf9fe4bb5f261786e0eb40f53e11141a` |
| Selection log | `3ef51133256c877844ebfa3e581debe75aa23d5023722f48393319368d2897d5` |
| Reason audit JSON | `a88a40dc92c1a5324838e50c90d025d058069928773057d9306d99ebee008ea4` |
| Reason audit Markdown | `f5ed533ed3c3f2b65ec8e0ec44aa2fd2aff6e29769248c79658a88f39ca6d901` |

Decision: accept the reason logging as a useful observability improvement.
Reject budget tuning as the next primary lever for this splice branch. The
blocked transformed candidates fail hard feasibility mainly through red-light
and lane-crossing checks after splice, not through kinematic feasibility and not
primarily through the declared progress/smoothness budget. The current
splice-shadow branch also adds roughly `20-24 ms` on target records and the
single-run total p95 selection latency remains above the 100 ms industrial
gate. This branch must stay shadow-only.

Next admissible step: run an offline transform-design screen, not a new replay
matrix. The screen should reuse captured target states or selection logs to ask
whether a lane/red-preserving transformation can keep lower-red benefit without
recomputing every transformed candidate online. Candidate designs must remain
fixed finite diagnostics and must be explicitly rejected if they rely on future
outcomes, change DP weights, change CAMP weights, or violate the fixed-candidate
convexity boundary. Do not train CAMP, retrain DP, alter atom schema, or use
formal seeds from this smoke.

### Splice transform-design anchor screen

The first transform-design screen kept the investigation offline and restricted
to the previously identified non-formal `sample59_86 / seed_2 / npc_4 /
tl_on` no-budget records. The screen did not run a new paired matrix and did
not change the online selector. It captured fixed microbenchmark snapshots for
the 57 no-budget steps from the reason-smoke selection log, then recomputed DP
reward/full-red diagnostics for H-anchor-preserving splice variants.

Predeclare artifact:

```text
/root/autodl-tmp/camp_dp_splice_transform_design_screen_347ae79_seed2_npc4_tlon/predeclare_transform_design_screen.txt
```

Target no-budget steps:

```text
128,130,131,132,135,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,157,158,159,160,161,163,164,165,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,184,187,189,190,191,193,194,195,196
```

Snapshot capture artifact:

```text
/root/autodl-tmp/camp_dp_splice_transform_design_screen_347ae79_seed2_npc4_tlon/snapshots_no_budget
```

Snapshot capture used the same non-formal route/seed/NPC/traffic-light/static
configuration as the reason smoke, with `selection_effect=false` microbenchmark
snapshot metadata and no formal seeds. It captured 57 snapshots. Snapshot-run
artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Replay summary | `f89b573ea2adebcaed931059eca8fb263b56436590805d3e19e520f2f1b21a93` |
| Validation summary | `60ffab40ca871a7264d027929726b48d98123b3439b67d2b935df9763960fd18` |
| Selection log | `828cf0cbcfdf9627298cfec2ad79fb3a477f500c79675216e36655fb22d4d8dd` |

Recompute grid:

```text
/root/autodl-tmp/camp_dp_splice_transform_design_screen_347ae79_seed2_npc4_tlon/recompute_grid
```

Grid: `anchor_steps in {10,20,30,40}`, `blend_steps=40`,
`heading_mode=donor_offset`, donor pool `lower_logged_union_red`, shadow budget
`1.0 m / 0.5`. This was an offline recompute over fixed snapshots; it was not
an online selector and not Benders.

| Anchor | Lower union-red transforms | Hard-feasible transforms | Lower union-red hard-feasible | Shadow changed snapshots | Lower-red hard-infeasible reasons |
| ---: | ---: | ---: | ---: | ---: | --- |
| 10 | 203 | 1 | 0 | 0 | `dp_lane_crossing: 83`, `dp_red_light: 203` |
| 20 | 179 | 1 | 0 | 0 | `dp_lane_crossing: 64`, `dp_red_light: 179` |
| 30 | 121 | 1 | 0 | 0 | `dp_lane_crossing: 17`, `dp_red_light: 121` |
| 40 | 72 | 1 | 0 | 0 | `dp_red_light: 72` |

Grid artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| Anchor 10 JSON | `f346d36bb8a7dfa7faf041d477ae3347ab387c60a625800ddab4de4e233547a9` |
| Anchor 10 Markdown | `ad2375520621c05519023cd82ae3a4537f5def2e351d23e570f1fc5307f86bf1` |
| Anchor 20 JSON | `4c1224cfedade844b2b847730ee75aed12a69c65406f1e641df73bcc3acb74fc` |
| Anchor 20 Markdown | `6dfcbcdfb25102797d1d3f27da56b859f7f302cb77bc715467a9ea0208b027bf` |
| Anchor 30 JSON | `0ce5ce959509ddecf59321da26966501f26400186d381fc56c558f96142be56d` |
| Anchor 30 Markdown | `74a6cae117b732389adff596a4ad4b5fb56ee5904805d4ed7acb4988ba2352c8` |
| Anchor 40 JSON | `7a4ac8958c49efffcd5b293302ca2f3a81029aca4ae03240e42f24c276e3e372` |
| Anchor 40 Markdown | `f5ab2d20c8d5245901dc3c9e0ab28bcb2e1fba5e955f8ffb0473045775365e98` |
| Grid summary JSON | `2cfd2060d8b6fa6f70c7653ef552a0afe1e8b0a1a9051d23dbe8849ef6d8c04b` |
| Grid summary Markdown | `4fb41abbec0040ebb310392ace0215ff4f132b743f076a0cdafddabd029be18f` |

Decision: reject H-anchor length tuning as a path to an online splice selector.
Increasing the preserved prefix from H10 to H40 reduced lower-red opportunities
from `203` to `72`, but it did not produce a single lower-red hard-feasible
transformed candidate across the 57 target snapshots. The dominant blocker
remained red-light infeasibility; lane-crossing decreased with longer anchors
but disappeared only when most of the lower-red benefit had already been lost.

Mathematical boundary: the screen used fixed finite current-tick snapshots and
posterior reward recomputation for diagnostics only. It does not alter DP
weights, CAMP weights, atom schema, candidate generation, or the executed
closed-loop trajectory. It is not Benders and does not generate dual cuts. The
only valid conclusion is a diagnostic reject for this H-anchor splice family on
these non-formal target states.

Next admissible step: stop spending online-selector effort on the current
H-anchor splice family unless a genuinely different red/lane-preserving
transformation is defined. A better next screen is either (1) an offline
selection-log diagnostic that asks whether original fixed candidates already
contain lower-red, lane-safe, progress-acceptable alternatives before any
splice, or (2) a richer future shadow log that stores transformed per-donor
reward arrays so budget/feasibility attribution does not require repeated DP
reward recomputation. Do not train CAMP, retrain DP, alter atom schema, or use
formal seeds from this screen.

### DP-CAMP Benders-style formalization contract

After rejecting the current H-anchor splice family, the next milestone is a
mathematical contract rather than another selector or replay experiment. The
contract is documented in:

```text
docs/dp_camp_benders_formalization.md
```

It restates the old Trajectron++ CAMP proof object as a finite maximum of
affine risk-response functions exposed to a CVXPY CVaR/simplex master through
active affine cuts. It then defines the DP-specific counterpart over the fixed
finite candidate set already generated at each current tick:

```text
q_i(w) = max(0, max_{k in F_i} m_ik + (a_i,o_i - a_ik)^T w).
```

Here `a_ik` are fixed normalized nonnegative DP-CAMP atoms, `o_i` is the
offline oracle candidate for a training record, `m_ik` is the nonnegative
outcome margin, and `F_i` is the fixed feasible candidate set. The active
candidate gives the supporting cut

```text
ell_i >= m_i,k* + (a_i,o_i - a_i,k*)^T w.
```

Decision: accept this as a documentation and mathematical-boundary milestone
only. The valid DP-CAMP claim is finite-candidate generalized Benders-style
cutting-plane optimization, not classical LP-dual Benders. The DP neural
sampler, Savitzky-Golay smoothing, `postprocess_reference`, PerfectTracker,
closed-loop simulator, route geometry, and reward scorer are not optimization
variables in this subproblem. They may produce fixed candidates, diagnostics,
feasibility flags, or offline labels, but they do not provide trajectory
coordinate convexity or recourse dual cuts.

This milestone does not train CAMP, retrain DP, change the selector, run a new
12/36 matrix, or use formal seeds. The next admissible step is a read-only
audit of the deployed `redstopfloor05` asset against this contract: exact atom
schema, normalization, weights, lower bounds, CVaR/simplex/L2 settings, active
cuts, convergence/full-epigraph evidence, and training labels.

Verification:

```text
git diff --check -- docs/dp_camp_benders_formalization.md \
  docs/diffusion_planner_v8_iteration_audit.md

@'
from pathlib import Path
root = Path.cwd()
for p in [
    'scripts/train/train_camp_select.py',
    'camp_core/camp_core/outer_master/parametric_cvxpy_master.py',
    'camp_core/camp_core/outer_master/benders_master.py',
    'camp_core/camp_core/integrations/diffusion_planner.py',
    'camp_core/camp_core/outer_master/robust_margin_master.py',
    'scripts/integrations/train_diffusion_planner_robust_camp.py',
]:
    assert (root / p).exists(), p
'@ | python -
```

Both documentation checks passed locally. The formalization artifact SHA-256 is:

| Artifact | SHA-256 |
| --- | --- |
| `docs/dp_camp_benders_formalization.md` | `5fe5e6830af84ac9dd1477c44a4db8be317c6f807b226be4af851de24dbbdf12` |

### Post-formalization redstopfloor05 contract audit

The read-only post-formalization audit was run against the deployed
`redstopfloor05` asset after local/GitHub/AutoDL CAMP had advanced to:

```text
d03e52ad0d484a23fbe0612eea4cccaf28871368
```

AutoDL CAMP was checked out at the same commit. AutoDL's local
`origin/main` tracking ref remained stale, so `git status` reported
`main...origin/main [ahead 18]`, but the checked-out HEAD matched local and
GitHub. The fixed Diffusion Planner checkout remained:

```text
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

No DP code, DP weights, CAMP weights, selector code, formal seeds, or existing
untracked migration files were changed. The audited asset was:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263
```

The audit used `source /etc/profile` and the AutoDL `camp` Python environment
to read the asset JSON and NPY files directly. The relevant files and hashes
were:

| Artifact | SHA-256 |
| --- | --- |
| `atom_scales_dp_static.json` | `a50d6d5b26888bdc0d2715dbfce525d3725697fa6e6565b6dd7ae9e8dd105b15` |
| `offline_weights_dp_static.npy` | `dbfe8333c8a2f7944710003d1bcf39fda84626b9c5728c80bddf6f5d41be81b1` |
| `training_summary.json` | `b6ced7c71240e9c8b3d1c6c47470ea7411069edeb48825d24ec2f8f693951e32` |
| `full_epigraph_consistency.json` | `12733885d22a50308b52ec6090af49f6ab973300a33394b140a24e5776b3c0c3` |
| `outcome_weights.json` | `9df61a4fbeeba3908113aedabf06fed1c92f0737613ccf9da93399902fa52425` |
| `offline_counterfactual_red_lower_bounds.json` | `f7b23d8c91e0c8d0afc26a2ec880f582e44184887b6e0c1a13118b00e2267905` |
| `train_stdout.log` | `afd8ff09f918c3bdd99ce335e36d5d9e7ce4d41f97e8bf750e3116cf4a5abce6` |

Contract checklist:

| Requirement from `docs/dp_camp_benders_formalization.md` | Evidence | Audit result |
| --- | --- | --- |
| Fixed finite candidate set per training record | Training summary reports static mode, `num_candidates=8`, `training_scope=feasible_ranking`, 7,200 input records, 5,979 records retained after dropping 1,221 records without feasible/eligible candidates. | Pass for the retained robust-margin master records. Dropped all-infeasible records are outside the convex master and remain an online fail-closed policy concern. |
| Positive atom dimension and fixed atom schema | `atom_schema_version=dp_camp_v10_14d`, `num_atoms=14`, atom names match the deployed v10 schema. | Pass. |
| Finite positive normalization scales | All 14 scales are finite and positive, with minimum scale `1e-06`. | Pass. |
| Finite nonnegative normalized atom/cost direction | `robust_margin_master.py` rejects nonfinite or negative normalized atoms before solving; the saved training passed this path and the full epigraph audit. | Pass by code invariant plus successful saved audit. |
| Simplex weights | Saved weight vector has shape `(14,)`, finite entries, minimum `0.0`, maximum `0.4793703457629436`, and sum `0.9999999999999997`. | Pass within floating-point tolerance. |
| Lower-bound feasible set | Only configured lower bound is `red_stopping_margin_cost >= 0.05`; lower-bound sum is `0.05`; saved slack is `-1.54e-13`. | Pass within numerical tolerance; feasible simplex is nonempty. |
| Nonnegative finite margins and feasible oracle | Training used margin scale `0.1`, margin clip `2.0`; the training entry point drops records without finite feasible candidates; `outcome_oracle_and_margins` enforces finite feasible outcomes and clips margins to `[0, margin_clip]`. | Pass for the retained training records. |
| CVaR/simplex/L2 convex master | Summary reports `objective=robust_margin_cvar`, `risk_type=cvar`, `alpha=0.9`, `l2_reg=0.0001`, `solver=CLARABEL`, `solver_status=optimal`. | Pass. |
| Active finite-candidate cuts | Cutting-plane history converged in four iterations with total active cuts `7111`; cut histogram over 4,848 train records is `{1: 2899, 2: 1652, 3: 280, 4: 17}`. | Pass. |
| Full finite-candidate epigraph consistency | `full_epigraph_consistency.json` reports `passed=true`, `finite_pieces=37030`, `saved_minus_full_objective=-5.162e-12`, `weight_linf_distance=1.226e-10`, `full_worst_unique=8`. | Pass. |
| Naming boundary | The audited object is a finite-candidate generalized Benders-style cutting-plane master. It does not introduce DP trajectory-coordinate convexity, LP-dual recourse variables, or strong-duality cuts. | Pass as long as later writing keeps this name boundary. |

The learned static weights remain:

| Atom | Weight |
| --- | ---: |
| `jerk_early` | 0.410286878894 |
| `jerk_late` | 0.000000000001 |
| `jerk_full` | 0.000000000001 |
| `rms_acceleration` | 0.000000000000 |
| `speed_limit_margin_0_0` | 0.000630102016 |
| `speed_limit_margin_0_5` | 0.000000000000 |
| `speed_limit_margin_1_0` | 0.000000000000 |
| `lane_deviation` | 0.000000000000 |
| `clearance` | 0.000368953150 |
| `progress_shortfall` | 0.479370345763 |
| `planned_red_light_cost` | 0.000000000000 |
| `planned_lateral_acceleration_cost` | 0.000000000000 |
| `red_stopping_margin_cost` | 0.0499999999998 |
| `dp_prior_jerk_excess_cost` | 0.059343720175 |

Outcome-label weights were unchanged: progress `2.0`, collision `100.0`,
near miss `10.0`, lane violation `20.0`, red light `30.0`, mean jerk `1.0`,
and mean lateral acceleration `2.0`. Train oracle match was
`0.880569306930693`; validation oracle match was `0.9045092838196287`.
Train CVaR was `0.11025719644616892`; validation CVaR was
`0.07891120510944721`.

Decision: accept `redstopfloor05` as satisfying the DP-CAMP mathematical
contract for a static finite-candidate generalized Benders-style
robust-margin master. This is a mathematical/training-object acceptance only.
It does not complete the industrial development gate and does not authorize
formal seeds. Prior full36 evidence still shows lateral comfort remains far
worse than Top-1, and mean per-run p95 selection latency was close to the
100 ms budget. Therefore the next admissible step is an engineering
integration gate, not a new mathematical claim: implement or audit only
default-off DP-CAMP selector metadata/fail-closed behavior and paired
non-formal checks after the integration path proves it preserves the fixed
finite-candidate contract. Do not retrain CAMP, modify DP, or run formal seeds
from this audit alone.

### Replay finite-candidate contract metadata gate

After accepting the `redstopfloor05` mathematical contract, the next engineering
step was an auditability gate rather than a selector change. The replay runner
now records an explicit `dp_camp_finite_candidate_contract` block in
`camp_replay_summary.json`, and the resummarizer preserves it in
`camp_validation_summary.json`.

The new metadata block records:

- schema version `dp_camp_finite_candidate_contract_v1`;
- whether CAMP finite-candidate selection is enabled;
- selector mode, candidate count, feasibility source, fallback mode, and atom
  clip;
- the candidate set boundary as the fixed current-tick DP candidate tensor
  before CAMP scoring;
- the affine score form `a_ik^T w`;
- the finite feasible-candidate `argmin` selection rule;
- atom and weight contract flags: fixed before scoring, finite, nonnegative
  after normalization, simplex weights expected, and score affine in weights;
- fail-closed behavior for all-infeasible finite sets;
- the valid training claim as finite-candidate generalized Benders-style
  cutting-plane training over logged fixed candidates only;
- `classical_benders_claim=false`;
- excluded components: DP neural sampler, SG smoothing, `postprocess_reference`,
  PerfectTracker state transition, closed-loop simulator future states, and
  route/traffic-light geometry.

This is intentionally a metadata gate. It does not change the online selector,
candidate generation, CAMP weights, DP weights, atom schema, fallback policy,
or any replay experiment. It makes future non-formal and formal artifacts
self-describing enough to audit whether the run preserved the mathematical
contract documented in `docs/dp_camp_benders_formalization.md`.

Verification:

```text
python -m pytest camp_core\tests\test_diffusion_planner_replay_summary.py
16 passed

git diff --check -- scripts/integrations/run_diffusion_planner_camp_replay.py \
  scripts/integrations/summarize_diffusion_planner_camp_replay.py \
  camp_core/tests/test_diffusion_planner_replay_summary.py \
  docs/diffusion_planner_v8_iteration_audit.md
passed
```

Decision: accept this as a small engineering integration milestone. The next
admissible step is still default-off and non-formal: run a very small replay
smoke only to confirm the new metadata appears in real generated
`camp_replay_summary.json` and survives summarization. It should not be treated
as safety/performance evidence and must not use formal seeds.

### Replay finite-candidate contract metadata smoke

The default-off metadata gate above was verified in a real Diffusion Planner
replay on AutoDL. This was a two-step non-formal smoke only; it did not train
CAMP, modify DP, change selector logic, run a paired matrix, or use formal
seeds.

Configuration:

```text
Output root: /root/autodl-tmp/camp_dp_contract_metadata_smoke_cc5ad26_seed101_steps2
CAMP commit: cc5ad26c02eaa9f2bc769edd5ea83fa4df403218
DP commit: 7a1d33da277a1992ec474b5383a0c963c72e04e4
Route: sample_map_tl_route_59_to_86.pkl
Seed: 101
Steps: 2
NPCs: 0
Traffic lights: on
Candidates: 4
Selector: static redstopfloor05
Feasibility source: dp_reward
Fallback mode: uniform
Advance mode: perfect
```

The remote verifier checked both `camp_replay_summary.json` and
`camp_validation_summary.json` and required the exact same
`dp_camp_finite_candidate_contract` block in both files. The verified fields
were:

```text
schema_version = dp_camp_finite_candidate_contract_v1
enabled = true
selector_mode = static
num_candidates = 4
score = a_ik^T w
classical_benders_claim = false
feasibility_source = dp_reward
fallback_mode = uniform
atom_contract.fixed_before_scoring = true
weight_contract.affine_score_in_weights = true
excluded_from_subproblem contains Diffusion Planner neural sampler
```

The smoke ended by `max_steps` after two selection records. The validation
summary reported `selection_steps=2`, `selector_mode=static`,
`num_candidates=4`, `fallback_rate=0.0`, and `n_npc_spawned=0`. These runtime
metrics are recorded only to identify the artifact; the run is too small and
was not designed to support safety, comfort, latency, or completion claims.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `PREDECLARE.txt` | `99cea7104ef5025d2b513408375fde3f149dae9d5afd7032b710e681f2e1f12c` |
| `run.log` | `a17ea45835b230bd0b9a8e33cac81204a8346d35f177f8df0983a80fa856606a` |
| `camp_replay_summary.json` | `5096d7fab53d31926856221289a1ed40b4622d248d2ab149635e89532b1ba203` |
| `camp_validation_summary.json` | `ff80373314f4f9f4e7926d73f98152a3ea76fe9d72209575f6df9dec240f7f00` |
| `camp_selection_log.json` | `f8a61d371c78f2d3b83b707165fb4309e47749e4bdee21ae976c5e183e268996` |
| `contract_metadata_smoke_audit.json` | `2f222f15d5e57fa54742565855bc7d796284fa98d7a49406669cadb5f6e0689a` |

Decision: accept the replay metadata smoke. Future replay artifacts now carry
the finite-candidate mathematical contract in both generated and summarized
metadata. The next admissible step remains a non-formal integration gate:
either add a dataset-audit check that requires this metadata for DP-CAMP runs,
or run a slightly larger paired smoke only if the audit check first proves the
metadata is enforced. Formal seeds remain frozen.

### Dataset audit finite-candidate contract gate

The next integration gate was implemented as a dataset-audit requirement rather
than a selector change. `scripts/integrations/audit_diffusion_planner_camp_dataset.py`
now accepts:

```text
--require_finite_candidate_contract
```

When enabled, the audit requires `camp_validation_summary.json` to carry a
`dp_camp_finite_candidate_contract` block with:

- schema version `dp_camp_finite_candidate_contract_v1`;
- `enabled=true`;
- selector mode in `{uniform, static, linear}`;
- exact expected candidate count;
- affine score form `a_ik^T w`;
- finite feasible-candidate `argmin` selection rule;
- atom contract flags for fixed finite nonnegative normalized atoms;
- simplex and affine-in-weights weight contract flags;
- feasibility source in `{context, dp_reward}`;
- fallback mode in `{uniform, learned}`;
- fail-closed wording that stays inside the same current-tick candidate set;
- training claim limited to finite-candidate generalized Benders-style
  cutting-plane training over logged fixed candidates;
- `classical_benders_claim=false`;
- the exact list of components excluded from the subproblem: DP neural sampler,
  Savitzky-Golay smoothing, `postprocess_reference`, PerfectTracker state
  transition, closed-loop simulator future states, and route/traffic-light
  geometry.

This gate makes the mathematical boundary machine-checkable for generated DP
replay artifacts. It does not change Diffusion Planner, CAMP weights, atom
schema, online selection behavior, or fallback policy. It also does not provide
new safety, comfort, latency, or completion evidence.

Local verification for the implementation commit:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_dataset_audit.py

42 passed in 1.32s

git diff --check -- \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  camp_core/tests/test_diffusion_planner_dataset_audit.py

passed
```

The implementation was committed and pushed as:

```text
f4d1320fd3cd12779e3b108ef486d47ceca0abe2
Gate DP CAMP finite-candidate dataset contract
```

AutoDL CAMP was then fast-forwarded from `3f2d7c0` to `f4d1320`. The remote
checkout still had unrelated untracked files:

```text
diffusion_planner_integration.md
dp_camp_device_handoff.md
test_diffusion_planner_benchmark_matrix.py
```

Those files were left untouched. The fixed Diffusion Planner checkout remained:

```text
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The new audit gate was run against the existing non-formal two-step metadata
smoke artifact:

```text
/root/autodl-tmp/camp_dp_contract_metadata_smoke_cc5ad26_seed101_steps2
```

Command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  --selection_log \
    /root/autodl-tmp/camp_dp_contract_metadata_smoke_cc5ad26_seed101_steps2/camp_selection_log.json \
  --atom_scales \
    /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --expected_logs 1 \
  --expected_candidates 4 \
  --expected_advance_mode perfect \
  --closed_loop_outcome_policy forbidden \
  --require_finite_candidate_contract \
  --output_json \
    /root/autodl-tmp/camp_dp_contract_metadata_smoke_cc5ad26_seed101_steps2/dataset_contract_audit.json
```

Remote result:

```text
Dataset audit passed: 1 logs, 2 records
counts: logs=1, records=2, candidates=8, all_infeasible_records=0
closed_loop_outcome_policy=forbidden
complete_closed_loop_outcomes=false
finite_candidate_contract_required=true
finite_candidate_contract_verified=true
finite_candidate_contract_logs=1
```

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `dataset_contract_audit.json` | `2b8b81caa431d36b3c24b4d302187cb349afb669f3133035be109f8adab6a310` |

Decision: accept this as a non-formal auditability milestone. The DP-CAMP
finite-candidate mathematical contract is now documented, emitted by replay
metadata, preserved by replay summarization, and enforceable by dataset audit
on a real DP replay artifact. The next admissible work is still not formal
seeds and not retraining: use this gate as a prerequisite for any larger
paired non-formal replay, and only then evaluate whether the current online
integration path has enough latency and behavior margin for the development
matrix.

The first audit record for this dataset-contract milestone was committed,
pushed, and synced as:

```text
6cb5dc6c141d5766be2e20b4b1fa42850b49759f
Document DP CAMP dataset contract gate
```

At that checkpoint, local CAMP, GitHub `origin/main`, and AutoDL CAMP all
matched that commit. AutoDL Diffusion Planner remained fixed at:

```text
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The only remaining local untracked files were the existing session handoff
artifacts, and the only remaining AutoDL untracked files were the existing
handoff/integration notes listed above. They were left untouched.

### SafetyCost v1 comparison gate

The next evaluation milestone defined a composite DP-CAMP safety score instead
of continuing selector tuning. The contract is documented in:

```text
docs/dp_camp_safety_score_v1.md
```

SafetyCost v1 is a lower-is-better weighted-and-clipped replay summary score:

```text
SafetyCost_v1 =
  100 * obb_collision_rate
+  10 * near_miss_rate
+  20 * lane_violation_rate
+  30 * red_light_violation_rate
+  15 * planned_red_light_violation_rate
+   1 * clip(mean_jerk_magnitude_mps3 / 10.0, 0, 10)
+   2 * clip(mean_lateral_acceleration_mps2 / 2.0, 0, 10)
+   2 * clip(1.0 - route_completion_rate, 0, 1)
```

This mirrors the Trajectron++ CAMP reporting principle that safety metrics must
be weighted and clipped before aggregation so rare outliers do not dominate the
claim. It is an evaluation score only. It does not change CAMP weights, DP
weights, candidate generation, the simulator, the finite-candidate mathematical
contract, or the Benders-style master.

The compare tool was extended in:

```text
scripts/integrations/compare_diffusion_planner_camp_replays.py
```

New outputs:

- per-run `safety_cost_v1` and component breakdowns;
- aggregate SafetyCost mean and upper-tail `safety_cost_v1_cvar90`;
- paired CAMP-minus-Top1 SafetyCost delta with deterministic 10,000-resample
  bootstrap CI;
- paired CVaR90 delta;
- hard-gate assessment;
- explicit scenario bucket support through a JSON manifest.

The hard gate requires:

- collision, near-miss, lane, and realized-red paired deltas to be nonpositive
  with CI high at most zero;
- completion CI low not below `-0.001`;
- variant p95 selection latency CI high at most `95 ms`, leaving `5 ms` margin
  under the `100 ms` budget;
- every paired CAMP run to carry `dp_camp_finite_candidate_contract_v1`;
- formal seeds `11/12/13` absent.

The claim rule is strict: CAMP may be called better than DP Top-1 only if this
hard gate passes and `ci95_high(SafetyCost_CAMP - SafetyCost_Top1) < 0`.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py \
  camp_core\tests\test_diffusion_planner_integration.py \
  -k "comparison or safety_cost"

4 passed, 107 deselected

$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py

3 passed

python -m py_compile \
  scripts\integrations\compare_diffusion_planner_camp_replays.py

passed

git diff --check -- \
  scripts/integrations/compare_diffusion_planner_camp_replays.py \
  camp_core/tests/test_diffusion_planner_safety_score_compare.py \
  docs/dp_camp_safety_score_v1.md

passed
```

The implementation was committed, pushed, and synced to AutoDL as:

```text
07c3b9ac0dec8859b560c671fbda4e6f17423176
Add DP CAMP SafetyCost comparison gate
```

AutoDL CAMP matched that commit. AutoDL Diffusion Planner remained fixed at:

```text
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The first read-only SafetyCost v1 recomputation used the existing non-formal
36-run `redstopfloor05` development artifacts. It did not run new replay,
train CAMP, modify DP, use formal seeds, or relabel scenarios. No scenario
bucket manifest was supplied, so all runs are bucketed as `overall` only.

Output root:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/safety_score_v1_07c3b9a
```

Command source:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/compare_diffusion_planner_camp_replays.py \
  --baseline top1 \
  --variant top1=<36 existing top1 replay dirs from prior comparison> \
  --variant v10_redstopfloor05=<36 existing redstopfloor05 replay dirs> \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/safety_score_v1_07c3b9a/safety_score_v1_comparison.json \
  --output_markdown \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/safety_score_v1_07c3b9a/safety_score_v1_comparison.md \
  --require_strict_pairing
```

The actual command was assembled from the prior
`comparison/benchmark_comparison.json` to avoid manually rewriting all 72
paths. Pairing remained strict: 36 Top-1 runs, 36 `v10_redstopfloor05` runs, 36
common keys, zero missing keys, and zero duplicate keys.

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `safety_score_v1_comparison.json` | `ca254ed88182a55b603c803a3167a3deb692319e038f880b2bedb656c8c80a27` |
| `safety_score_v1_comparison.md` | `b207f611e05b2e85f3c36bf55e248e9ba29f03b023587d5401b1ebd7bd6fb424` |

SafetyCost v1 result for `v10_redstopfloor05 - top1`:

| Metric | Paired delta |
| --- | ---: |
| SafetyCost v1 mean | `+1.636354 [1.128720, 2.435982]` |
| SafetyCost v1 CVaR90 delta | `+4.877437 [1.558574, 10.598288]` |
| Route completion | `+0.011982 [0.008380, 0.016005]` |
| Realized red-light rate | `+0.006142 [0.000000, 0.018425]` |
| Planned red-light rate | `+0.012500 [-0.001667, 0.035000]` |
| Mean jerk | `+12.116891 [10.277971, 14.019839]` |
| Mean lateral acceleration | `+0.044929 [0.028234, 0.064603]` |

Hard-gate result:

| Gate | Result |
| --- | --- |
| Collision nonworse | Pass |
| Near-miss nonworse | Fail |
| Lane nonworse | Fail |
| Realized red nonworse | Fail |
| Completion not significantly lower | Pass |
| Latency margin | Pass (`p95_selection_latency_ms` CI high `92.622 ms`) |
| Finite-candidate contract metadata | Fail (`0/36` legacy runs carried the new metadata block) |
| Formal seeds absent | Pass |

Decision: reject `redstopfloor05` as a comprehensive-safety improvement over
DP Top-1 under SafetyCost v1. This agrees with the earlier metric-by-metric
interpretation: `redstopfloor05` is mathematically certified and improves route
completion, but it has worse composite safety cost, worse tail risk, and fails
hard safety gates. The next admissible engineering step is to use SafetyCost v1
as the default comparison gate for any larger non-formal scenario suite. A
larger suite must include explicit scenario bucket manifests before critical
bucket claims such as red-light turn, sharp turn, dense NPC, or lane change are
made.

## Scenario bucket coverage audit entry point

The next development gate is scenario coverage, not selector tuning. This
milestone adds an explicit-only scenario bucket entry point so future
SafetyCost v1 comparisons can report whether normal, traffic-light,
red-light-turn, sharp-turn, NPC interaction, dense-scene, and lane-change/merge
conditions are actually represented.

Implementation:

- `configs/integrations/dp_camp_scenario_buckets_v1.template.json` is an empty
  manifest template. It contains no route labels and therefore does not
  fabricate critical scenario coverage.
- `docs/dp_camp_scenario_suite_v1.md` defines the scenario bucket development
  gate and repeats the mathematical boundary: bucket labels are evaluation
  metadata only, not CAMP atoms, not selector logic, and not a Benders
  subproblem.
- `scripts/integrations/audit_diffusion_planner_scenario_buckets.py` consumes a
  SafetyCost comparison JSON, recomputes bucket-level aggregates, paired
  deltas, hard-gate status, and coverage gaps, and can fail on missing required
  buckets with `--fail_on_missing_required`.

This is read-only analysis infrastructure. It does not modify DP, retrain CAMP,
change `redstopfloor05`, change the atom schema, run formal seeds, or run a
new replay matrix.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py

6 passed

python -m py_compile \
  scripts\integrations\audit_diffusion_planner_scenario_buckets.py

passed

python -m ruff check \
  scripts\integrations\audit_diffusion_planner_scenario_buckets.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py

All checks passed

git diff --check

passed
```

Predeclared remote check after push: run the new bucket audit on the existing
`redstopfloor05` SafetyCost v1 comparison JSON. Because that comparison was
generated without a bucket manifest, the expected result is `overall` coverage
only and missing required scenario buckets. That is a coverage-gap finding, not
a selector regression.

The implementation was committed, pushed, and synced to AutoDL as:

```text
84a50f923d71188eeee5fd1057bfc64c540925de
Add DP CAMP scenario bucket audit
```

AutoDL CAMP matched that commit after a fast-forward pull. AutoDL Diffusion
Planner remained fixed at:

```text
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Remote read-only audit command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_scenario_buckets.py \
  --comparison_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/safety_score_v1_07c3b9a/safety_score_v1_comparison.json \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/scenario_bucket_audit_84a50f9/scenario_bucket_coverage.json \
  --output_markdown \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/scenario_bucket_audit_84a50f9/scenario_bucket_coverage.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `scenario_bucket_coverage.json` | `a5924b25502353936500218e02f2c02800567d34d8756913f9e91e3f2a53de93` |
| `scenario_bucket_coverage.md` | `12eb910227d50169b8155bc20bb46b53b73f661e22f335d930c3ea581f96edca` |

Remote result:

| Bucket | Run keys | Strict pairing |
| --- | ---: | --- |
| `overall` | 36 | yes |

Missing required buckets:

```text
normal
traffic_light
red_light_turn
sharp_turn
npc_interaction
dense_scene
lane_change_or_merge
```

All 36 run keys were `overall` only. Decision: accept the audit tool and
reject the existing full36 SafetyCost result as evidence for any critical
scenario bucket. The next admissible step is to label or create a non-formal
scenario manifest from inspected routes before making red-light-turn,
sharp-turn, dense-scene, NPC-interaction, or lane-change claims.

## Scenario bucket manifest skeleton builder

The prior bucket audit proved that the existing full36 SafetyCost comparison
has no critical-bucket evidence. The next engineering step is not to guess
labels from route names or metrics, but to create an explicit manifest skeleton
from the comparison rows so route/run-key inspection has a concrete target.

Implementation:

- `scripts/integrations/build_diffusion_planner_scenario_bucket_manifest.py`
  reads a SafetyCost comparison JSON and writes a
  `dp_camp_scenario_buckets_v1` manifest skeleton.
- The skeleton records every route, run key, seed, step count, NPC count,
  spawn probability, traffic-light mode, and tracker mode.
- By default, every route and run key has an empty bucket list. Optional
  `--route_bucket` and `--run_key_bucket` labels must be supplied explicitly
  and are rejected if the route or run key is absent from the comparison.
- The builder does not inspect outcomes, infer labels from metrics, change the
  selector, train CAMP, modify DP, or run a replay.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_scenario_bucket_manifest.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py

10 passed

python -m py_compile \
  scripts\integrations\build_diffusion_planner_scenario_bucket_manifest.py \
  scripts\integrations\audit_diffusion_planner_scenario_buckets.py

passed

python -m ruff check \
  scripts\integrations\build_diffusion_planner_scenario_bucket_manifest.py \
  scripts\integrations\audit_diffusion_planner_scenario_buckets.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_manifest.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py

All checks passed

git diff --check

passed
```

Predeclared remote check after push: generate a manifest skeleton from the
existing `redstopfloor05` SafetyCost comparison JSON. Expected result: three
routes, 36 run keys, empty route/run-key bucket labels, and therefore no new
critical-bucket claim.

The implementation was committed, pushed, and synced to AutoDL as:

```text
b7e8cf398cd4d4d5fdeab911bc1e1a71fa177751
Add DP CAMP scenario bucket manifest builder
```

AutoDL CAMP matched that commit after a fast-forward pull. AutoDL Diffusion
Planner remained fixed at:

```text
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Remote skeleton generation command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/build_diffusion_planner_scenario_bucket_manifest.py \
  --comparison_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/safety_score_v1_07c3b9a/safety_score_v1_comparison.json \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/scenario_manifest_skeleton_b7e8cf3/scenario_buckets_skeleton.json \
  --include_run_keys
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `scenario_buckets_skeleton.json` | `9e78d7d69caabe6daab4672ddbb2d915e8bb610c56d59da2838e14843a890279` |

Remote skeleton result:

| Field | Value |
| --- | ---: |
| Routes | 3 |
| Run keys | 36 |
| Unlabeled routes | 3 |
| Unlabeled run keys | 36 |

Routes present in the existing full36 SafetyCost comparison:

```text
nishishinjuku_release_auto_route
sample_map_route_2_to_104
sample_map_tl_route_59_to_86
```

All route and run-key bucket lists are intentionally empty. Decision: accept
the skeleton builder and reject any attempt to label these routes from names,
traffic-light flags, or SafetyCost outcomes alone. The next admissible step is
a route/scenario-definition inspection pass that records geometry and traffic
control evidence before filling manifest labels.

## Route scenario inspection entry point

The manifest skeleton provides targets for labeling, but it still has no
evidence. This milestone adds a read-only route inspection entry point that
extracts scenario-definition evidence from the fixed DP `Route` files and
Lanelet2 maps before any bucket labels are applied.

Implementation:

- `scripts/integrations/inspect_diffusion_planner_routes.py` imports the fixed
  Tier4 Diffusion Planner checkout, loads saved `Route` pickle files, rebuilds
  `LaneletSceneBuilder`, and records route geometry and traffic-light
  regulatory groups on the route.
- The route geometry report includes route length, endpoint distance, repeated
  lanelets, total and windowed heading changes, and route lanelets associated
  with traffic-light regulatory groups.
- If a SafetyCost comparison JSON is supplied, the report also records the
  run-level seed, step count, NPC count, spawn probability, traffic-light mode,
  tracker mode, and run keys for each route.
- The tool does not apply labels, does not infer labels from metrics, does not
  modify DP, does not run replay, and does not change CAMP weights or atom
  definitions.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_route_inspection.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_manifest.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py

13 passed

python -m py_compile \
  scripts\integrations\inspect_diffusion_planner_routes.py

passed

python -m ruff check \
  scripts\integrations\inspect_diffusion_planner_routes.py \
  camp_core\tests\test_diffusion_planner_route_inspection.py

All checks passed

git diff --check

passed
```

Predeclared remote check after push: run the route inspection tool on the three
routes present in the existing `redstopfloor05` full36 SafetyCost comparison:
`nishishinjuku_release_auto_route`, `sample_map_route_2_to_104`, and
`sample_map_tl_route_59_to_86`. The expected output is an evidence artifact,
not a filled manifest.

The implementation was committed, pushed, and synced to AutoDL as:

```text
8a3b0a43507621f793ea516c2cc1df8f079a5373
Add DP CAMP route scenario inspection
```

The inspection was then extended with per-lanelet evidence and synced as:

```text
a9fc312293b584165140dc713631f2eb46c1554c
Add lanelet evidence to DP route inspection
```

AutoDL CAMP matched `a9fc312293b584165140dc713631f2eb46c1554c`. AutoDL
Diffusion Planner remained fixed at:

```text
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Remote route inspection command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/inspect_diffusion_planner_routes.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --comparison_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/safety_score_v1_07c3b9a/safety_score_v1_comparison.json \
  --route \
    nishishinjuku_release_auto_route=/root/autodl-tmp/camp_dp_assets/nishishinjuku_release_auto_route.pkl \
  --route \
    sample_map_route_2_to_104=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl \
  --route \
    sample_map_tl_route_59_to_86=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/route_inspection_a9fc312/route_scenario_inspection.json \
  --output_markdown \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/route_inspection_a9fc312/route_scenario_inspection.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `route_scenario_inspection.json` | `ac7ec6c7b2f7028722905cb3ba41a99f5f249c491bbd62ab9bf8f6a3b15d5f3d` |
| `route_scenario_inspection.md` | `1cf907cab6dbfad29d6ae06fd31eed74a20d3672347d6c5a4c66290e120a5575` |

Route evidence:

| Route | Length m | TL lanelets/groups | Max 10 m turn | Max 25 m turn | Run keys | TL modes | NPC counts |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `nishishinjuku_release_auto_route` | `747.198` | `5/5` | `29.210 deg` | `68.632 deg` | `12` | `[False, True]` | `[0, 4]` |
| `sample_map_route_2_to_104` | `338.996` | `0/0` | `6.277 deg` | `14.806 deg` | `12` | `[False, True]` | `[0, 4]` |
| `sample_map_tl_route_59_to_86` | `501.934` | `4/4` | `84.735 deg` | `90.209 deg` | `12` | `[False, True]` | `[0, 4]` |

Per-lanelet traffic-light evidence shows that `sample_map_tl_route_59_to_86`
has traffic-light lanelets with large local net heading changes:

| Route lanelet | Group | Cumulative range m | Net heading change |
| ---: | ---: | ---: | ---: |
| `59` | `1021` | `0.000-14.219` | `90.000 deg` |
| `33` | `1009` | `67.311-82.184` | `79.533 deg` |
| `57` | `1018` | `221.904-236.291` | `89.939 deg` |
| `16` | `1026` | `285.334-301.066` | `81.221 deg` |

Decision: accept the route inspection artifact as scenario-definition evidence.
It supports explicit future labeling of traffic-light and red-light-turn
run-key buckets for inspected traffic-light-enabled runs, especially
`sample_map_tl_route_59_to_86`. It does not by itself pass the coverage gate,
because the existing comparison mixes `traffic_lights=True/False`; applying a
route-level traffic-light label would mislabel the off runs. The next
admissible step is to add or use an explicit run-key/filter manifest so labels
can depend on route name plus run-level traffic-light/NPC configuration without
using replay outcomes.

## Scenario bucket filter manifest support

The route inspection artifact showed why route-wide labels are insufficient:
the same route appears under both `traffic_lights=True` and
`traffic_lights=False`. This milestone extends the scenario bucket manifest so
labels can be applied through explicit filters over benchmark/scenario
configuration fields instead of absolute run-key strings or outcome metrics.

Implementation:

- `scripts/integrations/compare_diffusion_planner_camp_replays.py` now accepts
  an optional manifest field `filters`.
- Each filter has `name`, `match`, and `buckets`. Matches are exact and may use
  only scenario configuration fields:

```text
route
route_name
route_stem
seed
steps
max_npcs
spawn_probability
traffic_lights
advance_mode
```

- Outcome and metric fields such as collisions, red-light violation,
  completion, jerk, latency, or SafetyCost are rejected as filter fields.
- Existing `routes`, `run_keys`, and `default_buckets` behavior remains
  backward compatible.
- `configs/integrations/dp_camp_scenario_buckets_v1.template.json`,
  `docs/dp_camp_safety_score_v1.md`, and
  `docs/dp_camp_scenario_suite_v1.md` now document the filter field.

This changes only evaluation metadata assignment. It does not modify DP, run
replay, train CAMP, alter atoms, alter the finite-candidate master, or create a
Benders subproblem.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_manifest.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py \
  camp_core\tests\test_diffusion_planner_route_inspection.py

15 passed

python -m py_compile \
  scripts\integrations\compare_diffusion_planner_camp_replays.py \
  scripts\integrations\build_diffusion_planner_scenario_bucket_manifest.py \
  scripts\integrations\audit_diffusion_planner_scenario_buckets.py

passed

python -m ruff check \
  scripts\integrations\compare_diffusion_planner_camp_replays.py \
  scripts\integrations\build_diffusion_planner_scenario_bucket_manifest.py \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_manifest.py

All checks passed

git diff --check

passed
```

Predeclared remote check after push: create an explicit development manifest
from the route inspection evidence using filters for `traffic_lights=True`
runs, rerun the existing SafetyCost comparison with that manifest, and audit
bucket coverage. This is a metadata reclassification of existing non-formal
artifacts only; it must not be presented as a new replay or a CAMP improvement.

The implementation was committed, pushed, and synced to AutoDL as:

```text
56e09ad9e874a4a6fe52f3cd888015da4fbbfd30
Add DP CAMP scenario bucket filters
```

AutoDL CAMP matched that commit after a fast-forward pull. AutoDL Diffusion
Planner remained fixed at:

```text
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Remote output root:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/scenario_filter_manifest_56e09ad
```

The development manifest used route-inspection evidence only:

- route-level `sharp_turn` for `sample_map_tl_route_59_to_86`;
- filter-level `traffic_light` for `nishishinjuku_release_auto_route` when
  `traffic_lights=true`;
- filter-level `traffic_light` and `red_light_turn` for
  `sample_map_tl_route_59_to_86` when `traffic_lights=true`;
- filter-level `normal` for `sample_map_route_2_to_104` when
  `traffic_lights=false` and `max_npcs=0`.

No label used SafetyCost, collision, red-light violation, completion, jerk,
latency, or any other replay outcome.

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `development_scenario_buckets.json` | `9d561f12c09df38761848754117504c42bc2e587f8e18f357b0ec059c8c01730` |
| `safety_score_v1_bucketed_comparison.json` | `5dca912291dec2d5aee2a89e33f7c903b749fb4ce93666c5e35308b5a404b517` |
| `safety_score_v1_bucketed_comparison.md` | `b207f611e05b2e85f3c36bf55e248e9ba29f03b023587d5401b1ebd7bd6fb424` |
| `scenario_bucket_coverage.json` | `d365a1e07e9285518f6e277c7dd47428f5200de5df26f1f91857f0338f595d2e` |
| `scenario_bucket_coverage.md` | `e61504b8ac51989306c63f5905d6f064f53428c0528a8d762e32e25266623cae` |

Bucket coverage and gate result:

| Bucket | Run keys | Strict pairing | Hard gate | SafetyCost claim | Mean SafetyCost delta |
| --- | ---: | --- | --- | --- | ---: |
| `overall` | 36 | yes | fail | fail | `+1.636354` |
| `normal` | 3 | yes | fail | fail | `+0.727142` |
| `traffic_light` | 12 | yes | fail | fail | `+2.322308` |
| `red_light_turn` | 6 | yes | fail | fail | `+2.927210` |
| `sharp_turn` | 12 | yes | fail | fail | `+1.810889` |

Missing required buckets:

```text
npc_interaction
dense_scene
lane_change_or_merge
```

Decision: accept filter-based metadata assignment and bucketed recomputation,
but keep `redstopfloor05` rejected. The existing non-formal full36 suite now
has explicit evidence-backed coverage for `normal`, `traffic_light`,
`red_light_turn`, and `sharp_turn`, but it still lacks acceptable coverage for
NPC interaction, dense scenes, and lane-change/merge. Even in the covered
buckets, `redstopfloor05` fails the hard gate and has positive SafetyCost
deltas. The next admissible step is scenario-suite design or route generation
for the missing buckets, not CAMP weight tuning.

## Versioned development scenario manifest

The route-inspection-backed development manifest used for the existing
redstopfloor05 full36 artifacts is now versioned in the repository:

```text
configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json
```

This is a reproducibility milestone only. It records the same explicit labels
used in the AutoDL `scenario_filter_manifest_56e09ad` recomputation:

- `sample_map_tl_route_59_to_86` receives route-level `sharp_turn` from route
  geometry evidence.
- `nishishinjuku_release_auto_route` receives `traffic_light` only when
  `traffic_lights=true`.
- `sample_map_tl_route_59_to_86` receives `traffic_light` and
  `red_light_turn` only when `traffic_lights=true`.
- `sample_map_route_2_to_104` receives `normal` only when
  `traffic_lights=false` and `max_npcs=0`.

The manifest metadata records the known missing buckets:

```text
npc_interaction
dense_scene
lane_change_or_merge
```

Mathematical conclusion: this manifest changes only evaluation metadata. It
does not modify DP, CAMP weights, candidate generation, atoms, feasibility
masks, affine scoring, or the finite-candidate generalized Benders-style
cutting-plane master.

Decision: accept the versioned manifest as a reproducibility improvement for
development audits. Reject any claim that it improves `redstopfloor05` or makes
the current full36 suite complete.

## SafetyCost comparison relabel reproducibility check

The existing redstopfloor05 replay directories are not required for scenario
bucket recomputation as long as the SafetyCost comparison JSON retains route
and run-configuration fields. A new metadata-only relabel tool was added:

```text
scripts/integrations/relabel_diffusion_planner_safety_comparison.py
```

It reads an existing comparison JSON, reapplies an explicit scenario bucket
manifest, recomputes aggregates, paired deltas, SafetyCost v1 hard gates, and
pairing audit fields, and writes a new comparison JSON/Markdown. It does not
rerun DP, CAMP selection, PerfectTracker, closed-loop simulation, or training.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_safety_comparison_relabel.py \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_manifest.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py

15 passed

python -m ruff check \
  scripts\integrations\relabel_diffusion_planner_safety_comparison.py \
  camp_core\tests\test_diffusion_planner_safety_comparison_relabel.py \
  camp_core\tests\test_diffusion_planner_safety_score_compare.py

All checks passed

python -m py_compile scripts\integrations\relabel_diffusion_planner_safety_comparison.py

passed

git diff --check

passed
```

The tool was committed, pushed, and synced to AutoDL as:

```text
ba62357589c00f9e6a323787d5ea18ac7a6c977a
Add DP CAMP safety comparison relabel tool
```

AutoDL verification:

```text
CAMP_HEAD=ba62357589c00f9e6a323787d5ea18ac7a6c977a
CAMP_ORIGIN=ba62357589c00f9e6a323787d5ea18ac7a6c977a
DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4

15 passed
```

Remote output root:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/scenario_relabel_ba62357
```

Input comparison:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/safety_score_v1_07c3b9a/safety_score_v1_comparison.json
```

Manifest:

```text
/root/autodl-tmp/camp_core/configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `safety_score_v1_bucketed_comparison.json` | `c7562429cf0a5831036f57e844f60b8c0c456cf3525d8ece4e1bdf99d5f75852` |
| `safety_score_v1_bucketed_comparison.md` | `6194ba2b536532e720acf5874f992132e4cb58373e26302e43596097844b05b5` |
| `scenario_bucket_coverage.json` | `f72bf2f34015ed33c07e82c564663a170976ce4f29adc2d9c39cb0199c23536e` |
| `scenario_bucket_coverage.md` | `e61504b8ac51989306c63f5905d6f064f53428c0528a8d762e32e25266623cae` |

Bucket coverage and gate result:

| Bucket | Run keys | Strict pairing | Hard gate | SafetyCost claim | Mean SafetyCost delta | CI95 low | CI95 high |
| --- | ---: | --- | --- | --- | ---: | ---: | ---: |
| `overall` | `36` | yes | fail | fail | `+1.636354` | `+1.120940` | `+2.450326` |
| `normal` | `3` | yes | fail | fail | `+0.727142` | `+0.656163` | `+0.780721` |
| `traffic_light` | `12` | yes | fail | fail | `+2.322308` | `+0.966325` | `+4.522844` |
| `red_light_turn` | `6` | yes | fail | fail | `+2.927210` | `+0.311772` | `+7.315351` |
| `sharp_turn` | `12` | yes | fail | fail | `+1.810889` | `+0.494978` | `+4.084322` |

Missing required buckets remain:

```text
npc_interaction
dense_scene
lane_change_or_merge
```

Decision: accept the relabel tool and committed manifest as reproducibility
infrastructure for existing artifacts. Reject any improvement claim for
`redstopfloor05`: all covered buckets still have positive SafetyCost deltas and
fail the hard gate, and three required scenario buckets remain uncovered. The
next admissible engineering step remains scenario-suite expansion and candidate
availability analysis, not CAMP weight tuning.

## Candidate availability input readiness audit

Before running the outcome-labeled candidate availability oracle, the current
selection logs must prove that the required finite-candidate inputs are present:
selected index, feasible mask, current-tick proxy costs, and candidate
closed-loop outcome labels. A new read-only readiness tool was added:

```text
scripts/integrations/audit_diffusion_planner_candidate_availability_inputs.py
```

This tool does not select trajectories, train CAMP, modify DP, run formal
seeds, or evaluate an online selector. It only checks whether existing
selection logs satisfy the input contract for the offline oracle. Proxy costs
may come from top-level candidate fields or fixed atom columns when the
selection log schema stores them as atoms.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_candidate_availability_inputs.py \
  camp_core\tests\test_diffusion_planner_candidate_availability.py \
  camp_core\tests\test_diffusion_planner_candidate_availability_compare.py \
  camp_core\tests\test_diffusion_planner_candidate_availability_blockers.py

12 passed

python -m ruff check \
  scripts\integrations\audit_diffusion_planner_candidate_availability_inputs.py \
  camp_core\tests\test_diffusion_planner_candidate_availability_inputs.py

All checks passed

python -m py_compile scripts\integrations\audit_diffusion_planner_candidate_availability_inputs.py

passed

git diff --check

passed
```

The tool was committed, pushed, and synced to AutoDL as:

```text
6981c07fb2f0cfeaffa57d22433a990d411eba4b
Add DP CAMP candidate availability input audit
```

AutoDL verification:

```text
CAMP_HEAD=6981c07fb2f0cfeaffa57d22433a990d411eba4b
CAMP_ORIGIN=6981c07fb2f0cfeaffa57d22433a990d411eba4b
DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4

12 passed
```

Remote output root:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_availability_input_readiness_6981c07
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `candidate_availability_input_readiness.json` | `3747e7fb2aaf7d5893fd0a636e48c64e4dda52859bf4f1bd4552f328e38a3380` |
| `candidate_availability_input_readiness.md` | `f45d9d2f89fb516a53994d2fa0bbeca7fddffe77fce5c162d5f427f9bba3ddfb` |

Readiness result:

| Field | Records | Rate |
| --- | ---: | ---: |
| `candidate_closed_loop_outcomes_complete` | `0` | `0.000000` |
| `progress_shortfall` | `7200` | `1.000000` |
| `proxy_jerk` | `7200` | `1.000000` |
| `proxy_lateral` | `7200` | `1.000000` |
| `red_stopping` | `7200` | `1.000000` |
| `union_red` | `7200` | `1.000000` |

Record summary:

```text
logs=36
records=7200
nonfallback_records=5998
fallback_records=1202
```

Proxy sources:

```text
progress_shortfall: atom:progress_shortfall
proxy_jerk: candidate_dp_prior_jerk_excess_cost
proxy_lateral: atom:planned_lateral_acceleration_cost
red_stopping: candidate_red_stopping_margin_cost
union_red: atom:planned_red_light_cost
```

Readiness decision:

```text
candidate_availability_oracle_ready=false
outcome_labels_ready=false
current_tick_proxy_inputs_ready=true
next_step=generate_or_attach_candidate_closed_loop_outcomes_before_running_oracle
```

Mathematical conclusion: current-tick finite-candidate proxy inputs are present
for the existing redstopfloor05 logs, but the outcome-labeled oracle cannot be
run because all `candidate_closed_loop_outcomes` entries are missing or null.
Using only proxy atoms would be an outcome-free diagnostic, not the requested
candidate availability oracle against SafetyCost/hard-gate outcomes.

Decision: accept the readiness tool and artifact. Reject running or reporting
the outcome-labeled candidate availability oracle on these artifacts until
candidate closed-loop outcome labels are generated or attached under a fixed,
offline, non-formal process. The next admissible step is to design that
label-generation pass for existing fixed finite candidates, still without
modifying DP or selecting online trajectories.

## Candidate outcome label-pass plan

A direct post-hoc attachment of candidate closed-loop outcomes to the current
redstopfloor05 logs is not supported by the stored fields. The current
selection logs contain selected index, atoms, feasibility, DP rewards, and the
current-tick proxy atoms, but they do not store the complete candidate
trajectories, NPC branch futures, red-light geometry, or tracker descriptors
needed to recompute `compute_candidate_closed_loop_outcomes` after the fact.
Historical outcome roots collected those labels during replay with
`--camp_collect_closed_loop_outcomes`; they are not evidence that the current
redstopfloor05 logs can be repaired in place.

A command-planning tool was added:

```text
scripts/integrations/plan_diffusion_planner_candidate_outcome_label_pass.py
```

The tool reads an existing paired comparison JSON, extracts the exact
non-formal scenario grid for a source variant, rejects formal seeds, requires
perfect tracking, and emits a static-only benchmark-matrix command with
`--camp_collect_closed_loop_outcomes` and `--skip_compare`. It does not run DP,
does not train CAMP, does not change online selection, and does not make a
Benders or trajectory-coordinate convexity claim.

Local verification:

```text
$env:PYTHONPATH='F:\camp_core-main\camp_core'; python -m pytest \
  camp_core\tests\test_diffusion_planner_candidate_outcome_label_pass_plan.py \
  camp_core\tests\test_diffusion_planner_candidate_availability_inputs.py

7 passed

python -m ruff check \
  scripts\integrations\plan_diffusion_planner_candidate_outcome_label_pass.py \
  camp_core\tests\test_diffusion_planner_candidate_outcome_label_pass_plan.py

All checks passed

python -m py_compile scripts\integrations\plan_diffusion_planner_candidate_outcome_label_pass.py

passed

git diff --check

passed
```

The tool was committed, pushed, and synced to AutoDL as:

```text
d97b7c220e24ee97e70ec5969d8fc8b26edb1815
Add DP CAMP candidate outcome label pass planner
```

AutoDL verification:

```text
CAMP_HEAD=d97b7c220e24ee97e70ec5969d8fc8b26edb1815
CAMP_ORIGIN=d97b7c220e24ee97e70ec5969d8fc8b26edb1815
DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4

7 passed
```

Remote output root:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_label_pass_plan_d97b7c2
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `candidate_outcome_label_pass_plan.json` | `1641e9c179ea1d88994c3551af0426578c27eb06e87c8c72b05917d1ea39db84` |
| `candidate_outcome_label_pass_plan.md` | `fcbd431c700e68f6978cdb567e4d65f7653d29f8415c2ca4bdf3ca576ab398cf` |

Plan summary:

| Item | Value |
| --- | --- |
| Source variant | `v10_redstopfloor05` |
| Scenario count | `36` |
| Routes | `3` |
| Seeds | `1,2,3` |
| Formal seeds | absent |
| NPC caps | `0,4` |
| Traffic lights | `off,on` |
| Steps | `200` |
| Advance mode | `perfect` |
| Candidates | `8` |
| Candidate noise scale | `1.0` |
| Outcome horizon | `30` |
| Planned matrix variant | `static` only |
| Planned comparison | skipped |
| Outcome collection | enabled |

Planned routes:

```text
nishishinjuku_release_auto_route=/root/autodl-tmp/camp_dp_assets/nishishinjuku_release_auto_route.pkl
sample_map_route_2_to_104=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
sample_map_tl_route_59_to_86=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
```

The plan uses the verified redstopfloor05 assets:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/offline_weights_dp_static.npy
```

Mathematical conclusion: the label pass, if run, would regenerate a fixed
finite candidate set under the same non-formal scenario grid and attach
candidate closed-loop outcomes as offline labels. These labels remain outside
the CAMP finite-candidate master and must not be used by online selection.
For any later training run, only the resulting fixed atoms, feasibility masks,
and offline labels may enter the robust-margin oracle.

Decision: accept the label-pass plan as the next admissible run design. Do not
claim candidate availability, SafetyCost improvement, or development-gate
progress from the plan alone. The next step is to run this planned non-formal
label pass on AutoDL, then require input readiness, dataset audit with
`closed_loop_outcome_policy=required`, and candidate availability analysis
before any selector or weight change.

## Candidate outcome label-pass audit

The planned static outcome-label pass was run on AutoDL against the fixed DP
checkpoint, frozen `redstopfloor05` CAMP weights, perfect tracking, K=8
candidates, seeds `1/2/3`, NPC caps `0/4`, traffic lights off/on, and the three
predeclared routes. Formal seeds `11/12/13` were not used.

Run artifact:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2
```

Run status:

```text
RUN_STATUS=done
SUMMARIES=36
SELECTION_LOGS=36
COUNTS_BY_ROUTE
     12 nishishinjuku_release_auto_route
     12 sample_map_route_2_to_104
     12 sample_map_tl_route_59_to_86
```

The first strict dataset audit with `--require_finite_candidate_contract`
failed because the generated `camp_validation_summary.json` files did not carry
the `dp_camp_finite_candidate_contract` block. This was a validation-summary
metadata propagation defect: the paired `camp_replay_summary.json` files already
contained both `candidate_generation_contract` and
`dp_camp_finite_candidate_contract` with the expected schema versions. No DP
run, candidate generation, CAMP scoring, feasibility mask, selector decision, or
closed-loop outcome label was changed.

The existing validation summaries were repaired by rerunning the repository
summarizer over the 36 replay output directories:

```text
python scripts/integrations/summarize_diffusion_planner_camp_replay.py \
  --output_dir <each candidate_outcome_labels_static_d97b7c2 run directory>
```

A code patch now also copies the replay-level contract metadata into
`camp_validation_summary.json` during replay generation, so future benchmark
outputs are audit-ready without the post-run summarizer step.

Audit artifact:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_label_audit_a838f7d
```

Audit artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `candidate_availability_input_readiness.json` | `ab2a7c5cf01651827de7aa4c1508ec6b0b5a86bcad9257d1516cc9b12426c582` |
| `candidate_availability_input_readiness.md` | `c478aae3f4fe4fe673c6c2a2aa769a838d4bc5b98f184b1b9cd2b993795bb723` |
| `dataset_audit_required_outcomes.json` | `a650ad4b71898db1c778f54c60275d8323f68e4f9e5f1d7e6c5124e479b50341` |
| `candidate_availability_oracle.json` | `0634deee6c75c4c1426ec1a27727b8f4ee1ae369dc66380decfb42a7a3ca9ff7` |
| `candidate_availability_oracle.md` | `2881917cd453899f57b82c7eb625d91a11c9b46f34388ed6610e9ead08a6e93f` |
| `candidate_availability_blockers.json` | `8ba9aa2082c80c7c1e65475195738be77e57ef148f755861ded03a8f2469770f` |
| `candidate_availability_blockers.md` | `7cfa59d64687c03c9ebdbae0a591c25ed8c8a27ee1f296ddad5dfabe20e237de` |

Strict dataset audit result:

```text
passed=true
logs=36
records=7200
candidates=57600
closed_loop_outcome_policy=required
closed_loop_outcome_records=7200
outcome_candidate_coverage=1.0
finite_candidate_contract_required=true
finite_candidate_contract_verified=true
finite_candidate_contract_logs=36
forbidden_seed_check=true
advance_mode_verified=true
schema=dp_camp_v10_14d
num_atoms=14
```

Candidate availability input readiness:

```text
records=7200
nonfallback_records=5939
fallback_records=1261
candidate_counts={8: 7200}
current_tick_proxy_inputs_ready=true
outcome_labels_ready=true
candidate_availability_oracle_ready=true
```

Outcome-labeled K=8 candidate availability among nonfallback records:

| Progress budget | Outcome joint | Proxy joint | Hidden outcome | Proxy-only |
| ---: | ---: | ---: | ---: | ---: |
| `0.00 m` | `1454` (`0.244822`) | `1` (`0.000168`) | `1445` (`0.243307`) | `56` (`0.009429`) |
| `0.05 m` | `1645` (`0.276983`) | `103` (`0.017343`) | `1430` (`0.240781`) | `215` (`0.036201`) |
| `0.10 m` | `1916` (`0.322613`) | `235` (`0.039569`) | `1404` (`0.236403`) | `392` (`0.066004`) |
| `0.25 m` | `2848` (`0.479542`) | `901` (`0.151709`) | `1202` (`0.202391`) | `674` (`0.113487`) |

Blocker audit:

```text
feasible_alternatives=5800 (0.976595), mean_candidates=6.528203
joint_comfort_alternatives=4204 (0.707863), mean_candidates=2.374137
safety_preserving_joint_comfort_alternatives=4203 (0.707695), mean_candidates=2.373127
safety_joint_progress_deficit_mean=0.651946 m
safety_joint_progress_deficit_p50=0.131145 m
safety_joint_progress_deficit_p90=0.578572 m
safety_joint_progress_deficit_p95=0.816842 m
```

The blocker table shows that candidate availability is not zero: many fixed
candidate pools contain outcome-labeled joint-comfort improvements. The current
proxy feature set, however, sees only a small subset of those improvements.
At a 0.10 m progress budget, for example, the outcome oracle finds 1916 joint
records while the proxy screen finds 235; 1404 records are hidden outcome
opportunities. The dominant blocker for strict budgets is progress loss, not
safety infeasibility: at 0.10 m, failed records are split into 1735 with no
joint-comfort alternative, 2287 progress-blocked records, and only 1
safety-blocked record.

Mathematical conclusion: this remains an offline label audit over fixed
current-tick finite candidates. The candidate closed-loop outcomes are future
labels used only to measure candidate availability; they are not online atoms,
not selector inputs, not a DP trajectory-coordinate convexity claim, and not a
Benders subproblem. The replay metadata gate now certifies the existing
finite-candidate generalized Benders-style CAMP master boundary for every run,
but the oracle result does not prove that the current online proxy selector can
recover the outcome improvements.

Decision: accept the outcome-label pass and oracle as a valid development-gate
diagnostic. Reject any claim that `redstopfloor05` is now better than DP Top-1
or that an online selector is ready. The next admissible step is a read-only
analysis that explains the hidden-outcome gap by route/bucket/tick context and
predeclares whether a fixed current-tick proxy atom or deterministic
finite-candidate preprocessing rule can expose those opportunities without
using future outcomes online.

## Hidden outcome gap attribution

The next read-only diagnostic was added:

```text
scripts/integrations/analyze_diffusion_planner_hidden_outcome_gap.py
```

It reuses the existing candidate availability definitions:

- outcome joint: the candidate passes the outcome Pareto mask and is strictly
  better than the selected candidate on both outcome jerk and outcome lateral
  acceleration;
- proxy joint: the candidate passes the fixed current-tick proxy Pareto mask
  and is strictly better than the selected candidate on both proxy jerk and
  proxy lateral acceleration;
- hidden joint: an outcome-joint candidate exists, but no proxy-joint candidate
  exists for the same tick and progress budget.

The tool attributes hidden opportunities by route, explicit scenario bucket,
run context, and 50-tick bin. It uses the committed scenario manifest:

```text
configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json
```

It does not rerun DP, train CAMP, change weights, change atoms, alter
feasibility, or select trajectories. Candidate outcomes remain offline labels
only.

Local verification for the analyzer milestone:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_hidden_outcome_gap.py \
  camp_core\tests\test_diffusion_planner_candidate_availability.py \
  camp_core\tests\test_diffusion_planner_candidate_availability_blockers.py -q

8 passed

python -m py_compile \
  scripts\integrations\analyze_diffusion_planner_hidden_outcome_gap.py

passed

python -m ruff check \
  scripts/integrations/analyze_diffusion_planner_hidden_outcome_gap.py \
  camp_core/tests/test_diffusion_planner_hidden_outcome_gap.py

All checks passed

git diff --check

passed
```

The analyzer was committed and pushed as:

```text
4037ab11430f20b125361bc3cd062f2c8c4d3e85
Add DP CAMP hidden outcome gap audit
```

AutoDL was fast-forwarded to that commit and the analyzer test passed remotely:

```text
2 passed
```

Remote diagnostic command:

```text
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_hidden_outcome_gap.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest \
    /root/autodl-tmp/camp_core/configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/hidden_outcome_gap_4037ab1/hidden_outcome_gap.json \
  --output_md \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/hidden_outcome_gap_4037ab1/hidden_outcome_gap.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `hidden_outcome_gap.json` | `f9a5e03db73649ad51bc1ca120990632ec49e0476f33732658ab35403af9172e` |
| `hidden_outcome_gap.md` | `b88772877f5a1a3ff924818f1a029dccd3cff1609eb05f59af47ac1e00c08ee2` |

Record counts:

```text
logs=36
records=7200
nonfallback=5939
fallback=1261
```

Overall hidden-gap summary:

| Progress budget | Outcome joint | Proxy joint | Hidden joint | Hidden / outcome |
| ---: | ---: | ---: | ---: | ---: |
| `0.00 m` | `1454` (`0.244822`) | `1` (`0.000168`) | `1453` (`0.244654`) | `0.999312` |
| `0.05 m` | `1645` (`0.276983`) | `103` (`0.017343`) | `1542` (`0.259640`) | `0.937386` |
| `0.10 m` | `1916` (`0.322613`) | `235` (`0.039569`) | `1685` (`0.283718`) | `0.879436` |
| `0.25 m` | `2848` (`0.479542`) | `901` (`0.151709`) | `1953` (`0.328843`) | `0.685744` |

At the predeclared 0.10 m progress budget, hidden opportunities are concentrated
by route as follows:

| Route | Nonfallback | Outcome joint | Proxy joint | Hidden joint | Hidden / outcome |
| --- | ---: | ---: | ---: | ---: | ---: |
| `nishishinjuku_release_auto_route` | `1826` | `1453` (`0.795728`) | `22` (`0.012048`) | `1431` (`0.783680`) | `0.984859` |
| `sample_map_tl_route_59_to_86` | `1916` | `288` (`0.150313`) | `138` (`0.072025`) | `154` (`0.080376`) | `0.534722` |
| `sample_map_route_2_to_104` | `2197` | `175` (`0.079654`) | `75` (`0.034137`) | `100` (`0.045517`) | `0.571429` |

At the same budget, hidden opportunities by explicit scenario bucket are:

| Bucket | Nonfallback | Outcome joint | Proxy joint | Hidden joint | Hidden / outcome |
| --- | ---: | ---: | ---: | ---: | ---: |
| `overall` | `5939` | `1916` (`0.322613`) | `235` (`0.039569`) | `1685` (`0.283718`) | `0.879436` |
| `traffic_light` | `1810` | `861` (`0.475691`) | `96` (`0.053039`) | `767` (`0.423757`) | `0.890825` |
| `sharp_turn` | `1916` | `288` (`0.150313`) | `138` (`0.072025`) | `154` (`0.080376`) | `0.534722` |
| `red_light_turn` | `942` | `153` (`0.162420`) | `85` (`0.090234`) | `70` (`0.074310`) | `0.457516` |
| `normal` | `600` | `62` (`0.103333`) | `26` (`0.043333`) | `36` (`0.060000`) | `0.580645` |

The hidden opportunities are also time-dependent. At 0.10 m, later ticks carry
most hidden records:

| Tick bin | Nonfallback | Outcome joint | Proxy joint | Hidden joint | Hidden / outcome |
| --- | ---: | ---: | ---: | ---: | ---: |
| `0000-0049` | `1364` | `126` (`0.092375`) | `42` (`0.030792`) | `86` (`0.063050`) | `0.682540` |
| `0050-0099` | `1667` | `513` (`0.307738`) | `60` (`0.035993`) | `453` (`0.271746`) | `0.883041` |
| `0100-0149` | `1619` | `661` (`0.408277`) | `77` (`0.047560`) | `584` (`0.360716`) | `0.883510` |
| `0150-0199` | `1289` | `616` (`0.477890`) | `56` (`0.043445`) | `562` (`0.435997`) | `0.912338` |

Proxy blocker counts for the best hidden outcome candidate at 0.10 m:

```text
proxy_progress_shortfall_blocked=1431
proxy_joint_comfort_not_strict=589
proxy_safety_proxy_blocked=1
```

Hidden-candidate delta summary at 0.10 m:

```text
outcome_progress_delta_mean=+0.169677 m
outcome_jerk_delta_mean=-0.567966 m/s^3
outcome_lateral_delta_mean=-0.036970 m/s^2
proxy_progress_shortfall_delta_mean=+1.067593
proxy_progress_shortfall_delta_p50=+0.893070
proxy_progress_shortfall_delta_p90=+2.334815
proxy_jerk_delta_mean=-0.313045
proxy_lateral_delta_mean=-0.036970
proxy_union_red_delta_mean=0.000000
proxy_red_stopping_delta_mean=0.000141
```

Interpretation: the candidate pool contains many outcome-labeled joint-comfort
opportunities, and those opportunities are not primarily blocked by red-light
or safety proxy regressions. The dominant blocker is the current
`progress_shortfall` proxy: the best hidden outcome candidates often have equal
or better realized outcome progress, but look much worse under the current-tick
progress-shortfall atom. This explains why a selector-only change over the
existing proxy score is unlikely to recover the hidden opportunities.

Mathematical conclusion: this is still an offline diagnostic over fixed
finite candidates. The hidden outcome labels are not admissible online atoms and
do not create a Benders subproblem. A future admissible design must expose these
opportunities through fixed current-tick quantities, for example a predeclared
progress-proxy alignment audit using existing outcome-free fields such as
`candidate_route_progress`, `candidate_step_reach`,
`candidate_perfect_tracker_first_step_reach_m`, or the stored fixed-candidate
PerfectTracker open-loop rollout descriptors.

Decision: accept the hidden-gap attribution as evidence that the bottleneck is
proxy progress alignment, not candidate-pool emptiness. Reject online selector
implementation, CAMP retraining, DP modification, and any 12/36-run expansion
from this result alone. The next admissible step is a read-only
progress-proxy alignment audit that tests whether any existing current-tick
finite-candidate progress descriptor can expose the hidden outcome-joint
candidates without using outcome labels online.

## Progress-deficit attribution on outcome-labeled candidates

The repository already contained the next required read-only diagnostic:

```text
scripts/integrations/analyze_diffusion_planner_progress_deficit_attribution.py
```

For every nonfallback record, it selects the safety-preserving joint-comfort
candidate with the minimum outcome progress deficit, then compares that
candidate with the selected candidate using fixed current-tick descriptors:
`candidate_step_reach`, `candidate_perfect_tracker_first_step_reach_m`,
PerfectTracker target speed, H3/H5/H10 open-loop rollout distance, DP-prior
jerk excess, horizon lateral cost, union-red, and red-stopping cost. Candidate
outcomes are used only to choose the offline label candidate for attribution;
they are not online selector inputs.

Remote command:

```text
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_progress_deficit_attribution.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --label redstopfloor05_outcome_labels \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_deficit_attribution_4037ab1/progress_deficit_attribution.json \
  --output_md \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_deficit_attribution_4037ab1/progress_deficit_attribution.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `progress_deficit_attribution.json` | `67b672dcc6d7935029bc34715627e1c6ef017e526283e5cd6cdae2ac0408a3b3` |
| `progress_deficit_attribution.md` | `1eddac28199b4fd935a3abd5a5cb1b645835cb76ee30254b4cdd14eec52c458b` |

Record counts:

```text
logs=36
records=7200
nonfallback=5939
fallback=1261
with_safety_joint_comfort=4203
without_safety_joint_comfort=1736
```

Minimum outcome progress deficit among safety-preserving joint-comfort
candidates:

```text
count=4203
mean=0.651946 m
p50=0.131145 m
p90=0.578572 m
p95=0.816842 m
candidate_progress_no_loss_rate=0.345943
```

Fixed current-tick descriptor deltas for the chosen attribution candidate:

| Quantity | Mean | P50 | P90 | P95 |
| --- | ---: | ---: | ---: | ---: |
| Outcome progress delta m | `-0.580246` | `-0.131145` | `0.000000` | `0.000000` |
| Candidate step reach delta m | `-0.010436` | `-0.004574` | `0.003882` | `0.009058` |
| PerfectTracker first-step reach delta m | `-0.010195` | `-0.004458` | `0.004014` | `0.009291` |
| PerfectTracker target speed delta m/s | `-0.101952` | `-0.044582` | `0.040136` | `0.092906` |
| H3 rollout distance delta m | `-0.045838` | `-0.024273` | `0.002130` | `0.012417` |
| H5 rollout distance delta m | `-0.083124` | `-0.044982` | `0.001199` | `0.015733` |
| H10 rollout distance delta m | `-0.184276` | `-0.103234` | `-0.006975` | `0.015855` |
| DP-prior jerk-excess delta | `-0.187635` | `-0.033302` | `0.000000` | `0.000000` |
| Horizon lateral delta | `-0.019436` | `-0.008964` | `-0.001232` | `-0.000536` |
| Union-red delta | `0.002022` | `0.000000` | `0.000000` | `0.000000` |
| Red-stopping delta | `0.000249` | `0.000000` | `0.000000` | `0.000000` |

Rates:

```text
candidate_lower_first_step_reach_rate=0.785867
candidate_lower_h3_distance_rate=0.877468
candidate_lower_target_speed_rate=0.785867
candidate_restart_push_rate=0.000000
selected_restart_push_rate=0.000000
restart_push_changed_rate=0.000000
```

Interpretation: the best safety-preserving joint-comfort alternatives usually
improve jerk and lateral proxy values, and they rarely regress union-red or
red-stopping costs. Their blocker is progress representation. Most of them
have lower first-step reach, lower short-horizon PerfectTracker rollout
distance, and lower target speed, even when the eventual outcome progress is
acceptable or better. This makes a naive relaxation of the existing
`progress_shortfall` atom unsafe: it could admit comfort-improving but
progress-sacrificing candidates without a current-tick certificate that the
closed-loop outcome remains acceptable.

Mathematical conclusion: the current evidence still does not justify an online
selector or CAMP retraining. A valid next design must first define an
outcome-free finite-candidate progress certificate with explicit budgets,
probably using a longer-horizon or state-conditioned descriptor rather than the
single existing `progress_shortfall` atom. If that certificate is atomized, it
must remain a fixed nonnegative current-tick coefficient so the score stays
affine in CAMP weights and the simplex/CVaR/L2 master stays convex. Without a
separate master/subproblem/dual/cut construction, it remains a finite-candidate
diagnostic or selector, not classical Benders.

Decision: reject immediate selector deployment and reject any 12/36-run
promotion from the current outcome-label evidence. Accept the next engineering
target as a predeclared progress-certificate design audit: compare candidate
descriptors such as H10 rollout distance, route progress, and state-conditioned
step reach against hidden outcome opportunities, choose conservative budgets,
and only then consider a default-off finite-candidate selector smoke.

## Progress-certificate design audit

Commit `a8ff98e` added a read-only analyzer:

```text
scripts/integrations/analyze_diffusion_planner_progress_certificate_design.py
```

The analyzer asks a narrower question than selector evaluation: given the
existing fixed DP candidate set and offline outcome labels, which outcome-free
current-tick progress descriptor can expose the hidden outcome-joint
opportunities found above? It does not change selection, train CAMP, modify
Diffusion Planner, or use outcome labels as online atoms.

Remote command:

```text
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_progress_certificate_design.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --label redstopfloor05_outcome_labels \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_certificate_design_a8ff98e/progress_certificate_design.json \
  --output_md \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_certificate_design_a8ff98e/progress_certificate_design.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `progress_certificate_design.json` | `b5b55525c0f4f499749ed91e0161c119b01767574fc84999767e43e122c40793` |
| `progress_certificate_design.md` | `0ac5cb06e1ce6ce83d7c360c785bc82903fa57bb66b4dd5513b091c3ceec2e3b` |

Remote test:

```text
/root/autodl-tmp/dp312_venv/bin/python \
  -m pytest camp_core/tests/test_diffusion_planner_progress_certificate_design.py -q

2 passed in 0.30s
```

Record counts:

```text
logs=36
records=7200
nonfallback=5939
fallback=1261
route_progress_available_records=0
```

The certificate rule is deliberately outcome-free: a candidate must remain in
the fixed finite candidate set, be base-feasible, have union-red and
red-stopping costs no worse than the selected candidate, and have descriptor
loss within the declared progress budget. Candidate outcomes are used only as
offline labels for measuring whether the certificate exposes useful hidden
opportunities.

At the predeclared `0.10 m` progress budget:

```text
nonfallback_records=5939
outcome_joint_records=1916
current_proxy_joint_records=235
hidden_outcome_joint_records=1685
```

Descriptor coverage at the same budget:

| Descriptor | Available | Outcome-joint certified | Hidden-joint certified | Hidden capture | Proxy-comfort hidden | Proxy-comfort precision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `progress_shortfall_atom` | `5939` | `499` | `268` | `0.159050` | `0` | `0.982979` |
| `route_progress` | `0` | `0` | `0` | `0.000000` | `0` | `0.000000` |
| `step_reach` | `5939` | `1902` | `1671` | `0.991691` | `1088` | `0.516445` |
| `tracker_first_step_reach` | `5939` | `1903` | `1672` | `0.992285` | `1089` | `0.516634` |
| `tracker_target_speed` | `5939` | `1365` | `1139` | `0.675964` | `712` | `0.462525` |
| `rollout_h3_distance` | `5939` | `1726` | `1495` | `0.887240` | `954` | `0.496855` |
| `rollout_h5_distance` | `5939` | `1438` | `1208` | `0.716914` | `742` | `0.470019` |
| `rollout_h10_distance` | `5939` | `978` | `753` | `0.446884` | `390` | `0.419509` |

Interpretation:

1. The existing `progress_shortfall_atom` is too restrictive for this candidate
   pool: at `0.10 m`, it exposes only `268/1685` hidden outcome-joint records.
2. `route_progress` is unavailable in this artifact, so it cannot support the
   next selector design without first changing logging or candidate metadata.
3. First-step descriptors expose nearly all hidden outcome-joint records, and
   H3 rollout distance exposes most of them. However, their proxy-comfort
   precision is only about `0.50`, so they are not by themselves deployable
   online acceptance rules.
4. Longer-horizon H10 distance is more conservative but loses more hidden
   opportunity coverage. It is useful as a guard candidate, not as a standalone
   recovery mechanism.

Mathematical conclusion: this remains a fixed finite-candidate diagnostic. The
descriptors are current-tick constants; if any of them is later atomized with a
fixed nonnegative scale, CAMP scores remain affine in `w` and the simplex/CVaR/L2
master remains convex. This audit does not construct a classical Benders
master/subproblem/dual/cut, does not claim trajectory-coordinate convexity, and
does not make DP sampler, smoothing, postprocessing, PerfectTracker, or future
closed-loop outcomes part of a Benders subproblem.

Decision: accept the analyzer and artifact as evidence that an outcome-free
progress certificate is plausible, but reject online selector deployment from
this result alone. The next admissible engineering step is to predeclare a
state-conditioned finite-candidate certificate that combines a first-step or H3
progress descriptor with explicit safety, comfort, and latency gates, then test
it first as a default-off offline selector screen. If that screen cannot pass
SafetyCost v1 hard gates and bucket coverage, keep the current DP-CAMP path in
shadow mode.

## State-conditioned certificate screen audit

Commit `47845e5` added a default-off read-only analyzer and commit `7fc2c16`
added posterior examples for safety regressions and worst progress losses:

```text
scripts/integrations/analyze_diffusion_planner_state_conditioned_certificate.py
```

The analyzer tests predeclared finite-candidate screens that combine
current-tick first-step reach, H3 PerfectTracker open-loop distance, target
speed, union-red, red-stopping, lateral cost, and jerk cost. Scenario buckets
only choose conservative budgets; they are not atoms, not learned weights, and
not outcome-derived labels. Candidate closed-loop outcomes are used only for
posterior audit.

Remote command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_state_conditioned_certificate.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest \
    /root/autodl-tmp/camp_core/configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/state_conditioned_certificate_7fc2c16/state_conditioned_certificate.json \
  --output_md \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/state_conditioned_certificate_7fc2c16/state_conditioned_certificate.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `state_conditioned_certificate.json` | `81cbbd96ed33af648f29dd9e36be562b1af566305f23f3e199bc484fd2dabd2a` |
| `state_conditioned_certificate.md` | `aa6cf0e10b480c82447b82024c00f5419aeaab003abb1edf2f002883ef217882` |

Remote test:

```text
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_state_conditioned_certificate.py \
  camp_core/tests/test_diffusion_planner_hidden_outcome_gap.py \
  camp_core/tests/test_diffusion_planner_scenario_bucket_audit.py \
  -q

8 passed in 1.03s
```

Record counts:

```text
logs=36
records=7200
nonfallback=5939
fallback=1261
```

Overall posterior result:

| Screen | Changed | Posterior joint comfort | Safety regressions | Progress delta mean | Jerk delta mean | Lateral delta mean | First-step loss mean | H3 loss mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `state_guard_strict_005` | `3356` | `2437` | `1 near_miss` | `-0.895581 m` | `-0.170757` | `-0.014700` | `0.001734 m` | `0.015788 m` |
| `state_guard_balanced_010` | `3902` | `2752` | `1 near_miss` | `-0.863154 m` | `-0.174827` | `-0.015654` | `0.003439 m` | `0.023785 m` |
| `state_guard_relaxed_noncritical_025` | `3902` | `2752` | `1 near_miss` | `-0.863154 m` | `-0.174827` | `-0.015654` | `0.003439 m` | `0.023785 m` |

Bucket-level summary for `state_guard_balanced_010`:

| Bucket | Records | Changed | Posterior joint comfort | Safety regressions |
| --- | ---: | ---: | ---: | ---: |
| `overall` | `5939` | `3902` | `2752` | `1` |
| `traffic_light` | `1810` | `999` | `812` | `1` |
| `red_light_turn` | `942` | `624` | `455` | `0` |
| `sharp_turn` | `1916` | `1380` | `1017` | `0` |
| `normal` | `600` | `487` | `280` | `0` |

The single posterior safety regression is a near-miss in
`nishishinjuku_release_auto_route`, seed `2`, `max_npcs=4`,
`traffic_lights=True`, selection step `134`, changing selected candidate `2`
to candidate `0`. The screen saw only small current-tick losses:

```text
first_step_loss=0.001273 m
H3_loss=0.049962 m
target_speed_loss=0.012729 m/s
union_red_delta=0
red_stopping_delta=0
outcome_progress_delta=0
outcome_jerk_delta=+0.112426
outcome_lateral_delta=-0.002847
```

The worst progress-loss example is also in
`nishishinjuku_release_auto_route`, seed `3`, `max_npcs=0`,
`traffic_lights=True`, selection step `149`, changing selected candidate `7`
to candidate `0`:

```text
first_step_loss=0
H3_loss=0.040716 m
target_speed_loss=0
union_red_delta=0
red_stopping_delta=0
outcome_progress_delta=-298.389663 m
outcome_jerk_delta=-0.738102
outcome_lateral_delta=-0.012449
```

Interpretation: first-step reach plus H3 distance is not a sufficient
outcome-free progress certificate for this candidate pool. It can select
comfort-improving candidates with tiny current-tick losses while causing large
closed-loop progress collapse. The screen also violates the posterior safety
direction through one near-miss regression in the traffic-light bucket. This
fails the development-gate spirit before any replay smoke is justified.

Mathematical conclusion: the analyzer itself is valid as a finite-candidate
diagnostic. All selector-side quantities are fixed current-tick constants, so a
future atomization with fixed nonnegative scales would keep CAMP scoring
affine in `w` and preserve the simplex/CVaR/L2 master convexity. The tested
screens, however, are rejected as engineering policies. They do not construct
a classical Benders subproblem and do not prove DP-CAMP superiority.

Decision: accept the state-conditioned analyzer as a reusable rejection gate.
Reject the first-step/H3 certificate screens for online implementation,
default-off smoke, CAMP retraining, 12-run, or 36-run promotion. The next
admissible step is to either (a) add a stronger outcome-free long-horizon
progress certificate using already logged DP reward progress or H10/route
progress metadata, then repeat this bucketed posterior gate, or (b) keep the
current path in shadow mode if no such current-tick certificate can block the
large progress-collapse examples without reintroducing safety regressions.

## DP-reward/H10 long-horizon certificate screen audit

Commit `beacd8e` extended the default-off certificate analyzer with
long-horizon screens that replace first-step/H3 progress guards with
`dp_candidate_rewards.progress` and H10 PerfectTracker open-loop distance.
This remains a read-only posterior audit over fixed current-tick finite
candidates.

Remote command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_state_conditioned_certificate.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest \
    /root/autodl-tmp/camp_core/configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/state_conditioned_certificate_beacd8e/state_conditioned_certificate.json \
  --output_md \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/state_conditioned_certificate_beacd8e/state_conditioned_certificate.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `state_conditioned_certificate.json` | `4ecce88246cd2bef8b27a5b62b1372c16366d71f16b93174bea389c6db867834` |
| `state_conditioned_certificate.md` | `e4321d3353a618600114e15c023216dd518c325cc281cfc8277c9a5d9a732125` |

Remote test:

```text
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_state_conditioned_certificate.py \
  camp_core/tests/test_diffusion_planner_hidden_outcome_gap.py \
  camp_core/tests/test_diffusion_planner_scenario_bucket_audit.py \
  -q

10 passed in 1.04s
```

Record counts are unchanged:

```text
logs=36
records=7200
nonfallback=5939
fallback=1261
```

Posterior result for the long-horizon screens:

| Screen | Changed | Posterior joint comfort | Safety regressions | Progress delta mean | Progress delta min | Jerk delta mean | Lateral delta mean | Reward-progress loss mean | H10 loss mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `reward_h10_guard_strict_005` | `328` | `183` | `0` | `-0.028783 m` | `-0.109144 m` | `+0.003401` | `-0.004370` | `0.027965 m` | `0.012344 m` |
| `reward_h10_guard_balanced_010` | `706` | `390` | `0` | `-0.052685 m` | `-0.152361 m` | `+0.003416` | `-0.005157` | `0.052550 m` | `0.028465 m` |
| `reward_h10_guard_relaxed_noncritical_025` | `1185` | `740` | `0` | `-0.116211 m` | `-0.250189 m` | `-0.029734` | `-0.004956` | `0.126365 m` | `0.038512 m` |

Bucket-level summary for `reward_h10_guard_balanced_010`:

| Bucket | Records | Changed | Posterior joint comfort | Safety regressions |
| --- | ---: | ---: | ---: | ---: |
| `overall` | `5939` | `706` | `390` | `0` |
| `sharp_turn` | `1916` | `328` | `204` | `0` |
| `traffic_light` | `1810` | `130` | `76` | `0` |
| `red_light_turn` | `942` | `122` | `72` | `0` |
| `normal` | `600` | `115` | `60` | `0` |

The prior near-miss regression and `-298.389663 m` progress-collapse example
are blocked by the long-horizon certificate. For the previous near-miss case,
the candidate had:

```text
dp_reward_progress_loss=0.682098 m
H10_loss=0.225675 m
```

For the previous worst progress-collapse case, the candidate had:

```text
dp_reward_progress_loss=0.744923 m
H10_loss=0.200395 m
```

Both are far outside the predeclared long-horizon budgets.

The new worst progress-loss examples are bounded by construction. Under the
balanced screen the worst changed record has:

```text
outcome_progress_delta=-0.152361 m
dp_reward_progress_loss=0.047617 m
H10_loss=0.020177 m
target_speed_loss=0.076687 m/s
safety_regression=false
```

Under the relaxed noncritical screen the worst changed record has:

```text
outcome_progress_delta=-0.250189 m
dp_reward_progress_loss=0.249676 m
H10_loss=0.074888 m
target_speed_loss=0.090554 m/s
safety_regression=false
```

Interpretation: DP reward progress plus H10 distance is a materially stronger
outcome-free progress certificate than first-step/H3. It blocks the known
catastrophic progress-collapse and posterior near-miss examples while
preserving explicit bucket reporting. However, this is still not proof that
DP-CAMP is better than DP Top-1. The strict and balanced screens have slightly
positive posterior mean jerk deltas, while the relaxed screen improves jerk and
lateral posterior metrics at the cost of a larger bounded progress loss.

Mathematical conclusion: this remains within the CAMP finite-candidate
contract. The screen reads fixed current-tick candidate constants
(`dp_candidate_rewards.progress`, H10 open-loop distance, target speed,
union-red, red-stopping, raw lateral, raw jerk). If later represented as atoms
with fixed nonnegative scaling, the candidate score remains affine in `w` and
the simplex/CVaR/L2 master remains convex. The audit does not construct a
classical Benders master/subproblem/dual/cut and does not make DP sampler,
postprocessing, PerfectTracker, or closed-loop outcomes part of a Benders
subproblem.

Decision: accept the DP-reward/H10 certificate as a valid next engineering
candidate and reject the earlier first-step/H3-only certificate. Do not claim
SafetyCost improvement, do not train CAMP, and do not run 12/36-run yet. The
next admissible step is a default-off implementation plan for one or more
reward/H10 screens with fail-closed metadata and latency accounting, followed
only by a small paired non-formal smoke if local/AutoDL tests and audit
metadata pass.

## Bucketed candidate availability oracle audit

Commit `664025d` extends the offline candidate availability oracle with an
optional explicit scenario bucket manifest. This is a read-only evaluation
change: it relabels fixed selection logs by inspected route/run metadata,
keeps candidate outcomes as offline labels only, and does not change the
online selector, CAMP weights, DP, or the finite-candidate Benders-style
training object.

Local tests:

```text
python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_candidate_availability.py \
  camp_core\tests\test_diffusion_planner_candidate_availability.py

python -m pytest \
  camp_core\tests\test_diffusion_planner_candidate_availability.py \
  camp_core\tests\test_diffusion_planner_hidden_outcome_gap.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_manifest.py \
  camp_core\tests\test_diffusion_planner_safety_comparison_relabel.py \
  -q

15 passed in 2.81s
```

AutoDL sync and test:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_candidate_availability.py \
  camp_core/tests/test_diffusion_planner_hidden_outcome_gap.py \
  camp_core/tests/test_diffusion_planner_scenario_bucket_audit.py \
  camp_core/tests/test_diffusion_planner_scenario_bucket_manifest.py \
  camp_core/tests/test_diffusion_planner_safety_comparison_relabel.py \
  -q

15 passed in 2.03s
```

Remote analysis command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_candidate_availability.py \
  --root \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest \
    configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_availability_bucketed_664025d/candidate_availability_bucketed.json \
  --output_md \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_availability_bucketed_664025d/candidate_availability_bucketed.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `candidate_availability_bucketed.json` | `f0a39b4e94c7f16dc5838ab16abf4783f93663359fcdaa90c19fbb8a8b42b3d3` |
| `candidate_availability_bucketed.md` | `880b008c7d40b9c45b232054088df4502c73e74625c2ef033573eddf1570fc6a` |

Record coverage:

```text
logs=36
records=7200
nonfallback=5939
fallback=1261
```

Explicit bucket record counts:

| Bucket | Records | Nonfallback | Fallback |
| --- | ---: | ---: | ---: |
| `overall` | `7200` | `5939` | `1261` |
| `normal` | `600` | `600` | `0` |
| `traffic_light` | `2400` | `1810` | `590` |
| `red_light_turn` | `1200` | `942` | `258` |
| `sharp_turn` | `2400` | `1916` | `484` |

At the predeclared `0.10 m` progress budget, the outcome-labeled oracle sees:

| Bucket | Nonfallback | Outcome joint | Proxy joint | Hidden outcome |
| --- | ---: | ---: | ---: | ---: |
| `overall` | `5939` | `1916` | `235` | `1404` |
| `normal` | `600` | `62` | `26` | `0` |
| `traffic_light` | `1810` | `861` | `96` | `684` |
| `red_light_turn` | `942` | `153` | `85` | `4` |
| `sharp_turn` | `1916` | `288` | `138` | `7` |

Interpretation: the candidate pool contains many outcome-labeled joint-comfort
opportunities, but most of the gap between outcome labels and current-tick
proxy visibility is concentrated in the broader `traffic_light` bucket. The
`normal` bucket has zero hidden outcome opportunities at the same budget, while
`red_light_turn` and `sharp_turn` have only small residual hidden counts under
the current development manifest. This means the next engineering question is
not a global retune: it is whether a traffic-light-specific fixed
finite-candidate certificate can expose the hidden outcome opportunities
without violating SafetyCost hard gates or latency.

Mathematical conclusion: bucket labels remain evaluation metadata. The proxy
side uses fixed current-tick finite-candidate constants; candidate closed-loop
outcomes are offline labels for oracle attribution only. This audit does not
create a classical Benders subproblem and does not make DP sampling,
postprocessing, PerfectTracker, closed-loop future states, or trajectory
coordinates optimization variables.

Decision: accept the bucketed oracle audit as a development diagnostic. It
does not prove CAMP is better than DP Top-1, and it does not authorize 12-run
or 36-run promotion. The next admissible step is to inspect the traffic-light
hidden opportunities and identify which fixed current-tick candidate signals
could legally expose them; if no such signal exists, keep the policy in shadow
or treat the DP candidate pool/proxy schema as the bottleneck.

## Bucketed progress-certificate descriptor audit

Commit `9629500` extends the progress-certificate design audit with the same
explicit scenario bucket manifest used by the SafetyCost and candidate
availability tools. This is still a read-only descriptor audit: it does not
change online selection, train CAMP, modify Diffusion Planner, or use outcome
labels as online atoms.

Local verification:

```text
python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_progress_certificate_design.py \
  camp_core\tests\test_diffusion_planner_progress_certificate_design.py

python -m pytest \
  camp_core\tests\test_diffusion_planner_progress_certificate_design.py \
  camp_core\tests\test_diffusion_planner_hidden_outcome_gap.py \
  camp_core\tests\test_diffusion_planner_candidate_availability.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py \
  -q

12 passed in 1.50s
```

AutoDL sync and test:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_progress_certificate_design.py \
  camp_core/tests/test_diffusion_planner_hidden_outcome_gap.py \
  camp_core/tests/test_diffusion_planner_candidate_availability.py \
  camp_core/tests/test_diffusion_planner_scenario_bucket_audit.py \
  -q

12 passed in 1.07s
```

Remote analysis command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_progress_certificate_design.py \
  --root \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest \
    configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_certificate_bucketed_9629500/progress_certificate_bucketed.json \
  --output_md \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_certificate_bucketed_9629500/progress_certificate_bucketed.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `progress_certificate_bucketed.json` | `f8f7e749903dacc4be7987b41e43ac9df2e6d2e18cc6c367bfc26a459e916f12` |
| `progress_certificate_bucketed.md` | `5094c9e9f0f830cce8854bf3f2f0d9e726fd77be24ff6d56ae98584db8e2ec23` |

Record coverage:

```text
logs=36
records=7200
nonfallback=5939
fallback=1261
route_progress_available_records=0
```

At the predeclared `0.10 m` progress budget, descriptor capture by bucket:

| Bucket | Descriptor | Hidden capture | Proxy-comfort hidden capture | Proxy-comfort precision |
| --- | --- | ---: | ---: | ---: |
| `traffic_light` | `progress_shortfall_atom` | `73/767` (`0.095176`) | `0/767` (`0.000000`) | `0.979167` |
| `traffic_light` | `step_reach` | `760/767` (`0.990874`) | `521/767` (`0.679270`) | `0.691789` |
| `traffic_light` | `tracker_target_speed` | `514/767` (`0.670143`) | `354/767` (`0.461538`) | `0.639485` |
| `traffic_light` | `rollout_h3_distance` | `671/767` (`0.874837`) | `452/767` (`0.589309`) | `0.670762` |
| `traffic_light` | `rollout_h10_distance` | `314/767` (`0.409387`) | `192/767` (`0.250326`) | `0.590062` |
| `red_light_turn` | `progress_shortfall_atom` | `65/70` (`0.928571`) | `0/70` (`0.000000`) | `0.976471` |
| `red_light_turn` | `step_reach` | `69/70` (`0.985714`) | `0/70` (`0.000000`) | `0.238506` |
| `red_light_turn` | `rollout_h3_distance` | `69/70` (`0.985714`) | `0/70` (`0.000000`) | `0.241983` |
| `sharp_turn` | `progress_shortfall_atom` | `146/154` (`0.948052`) | `0/154` (`0.000000`) | `0.971014` |
| `sharp_turn` | `step_reach` | `153/154` (`0.993506`) | `2/154` (`0.012987`) | `0.188105` |
| `sharp_turn` | `rollout_h3_distance` | `153/154` (`0.993506`) | `2/154` (`0.012987`) | `0.189679` |
| `normal` | `step_reach` | `36/36` (`1.000000`) | `0/36` (`0.000000`) | `0.143646` |

Interpretation:

1. The broad `traffic_light` bucket is the only current development bucket
   where first-step/H3-style progress descriptors expose many hidden
   outcome-joint candidates while also retaining a substantial proxy-comfort
   subset.
2. The same descriptors are not clean generic rules. In `red_light_turn`,
   `sharp_turn`, and `normal`, they often capture hidden candidates but almost
   never with proxy-comfort-hidden support, and their proxy-comfort precision
   is poor. A global relaxation would repeat the rejected first-step/H3 route.
3. `rollout_h10_distance` is safer and consistent with the accepted
   reward/H10 screen direction, but it captures only `192/767` proxy-comfort
   hidden traffic-light cases at `0.10 m`; it is a guard, not a recovery rule.
4. `route_progress` is unavailable in the current artifacts, so it cannot be
   used for a development selector without a predeclared logging/candidate
   metadata change.

Mathematical conclusion: this remains within the finite-candidate diagnostic
contract. Scenario buckets are evaluation metadata; all tested descriptors are
fixed current-tick candidate constants. If a future traffic-light-specific
descriptor is atomized with fixed nonnegative scaling, CAMP scoring remains
affine in `w` and the simplex/CVaR/L2 master remains convex. This audit does
not construct a classical Benders subproblem and does not make DP sampling,
postprocessing, PerfectTracker, closed-loop outcomes, or trajectory
coordinates optimization variables.

Decision: accept the bucketed progress-certificate audit. Reject any global
first-step/H3 relaxation. The next admissible design is a strictly default-off
traffic-light-only offline screen that combines a high-recall descriptor
(`step_reach` or H3) with a conservative long-horizon guard
(`dp_candidate_rewards.progress` plus H10 distance), no-worse union-red and
red-stopping, strict proxy comfort, deterministic tie-break, and posterior
SafetyCost/hard-gate rejection criteria before any smoke run.

## Traffic-light hybrid certificate screen audit

Commit `047725a` adds two default-off read-only traffic-light-only screens to
the existing state-conditioned certificate analyzer:

- `traffic_light_hybrid_step_h10_guard_005`
- `traffic_light_hybrid_h3_h10_guard_005`

Both screens activate only when the explicit scenario buckets contain
`traffic_light`. They require base feasibility, union-red and red-stopping
nonworse than the selected candidate, strict raw lateral improvement, strict
raw jerk improvement, target-speed loss within `0.05 m/s`, DP-reward progress
loss within `0.05 m`, and H10 rollout distance loss within `0.05 m`. The step
variant additionally allows first-step loss up to `0.10 m`; the H3 variant
allows H3 rollout-distance loss up to `0.10 m`. The baseline candidate is
retained if no candidate passes.

Local verification:

```text
python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_state_conditioned_certificate.py \
  camp_core\tests\test_diffusion_planner_state_conditioned_certificate.py

python -m pytest \
  camp_core\tests\test_diffusion_planner_state_conditioned_certificate.py \
  camp_core\tests\test_diffusion_planner_hidden_outcome_gap.py \
  camp_core\tests\test_diffusion_planner_scenario_bucket_audit.py \
  camp_core\tests\test_diffusion_planner_candidate_availability.py \
  -q

16 passed in 1.38s
```

AutoDL sync and test:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_state_conditioned_certificate.py \
  camp_core/tests/test_diffusion_planner_hidden_outcome_gap.py \
  camp_core/tests/test_diffusion_planner_scenario_bucket_audit.py \
  camp_core/tests/test_diffusion_planner_candidate_availability.py \
  -q

16 passed in 1.08s
```

Remote analysis command:

```text
cd /root/autodl-tmp/camp_core
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_state_conditioned_certificate.py \
  --root \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest \
    configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/state_conditioned_certificate_047725a/state_conditioned_certificate.json \
  --output_md \
    /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/state_conditioned_certificate_047725a/state_conditioned_certificate.md
```

Remote artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `state_conditioned_certificate.json` | `384d0e6377239530c43b594c804f1198388f9dad7bbb37b05cb8540044f4b833` |
| `state_conditioned_certificate.md` | `1b1e856e7bc7543ad68a2e0c3b6fdc7e2150f3251c55cba5e42eedf265fce567` |

The two hybrid screens produced identical selected candidates on the current
artifact, which means the long-horizon DP reward/H10/target-speed guard is
dominant over the step-vs-H3 choice.

Posterior result:

| Screen | Changed | Posterior joint comfort | Safety regressions | Progress delta mean | Progress delta min | Jerk delta mean | Lateral delta mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `traffic_light_hybrid_step_h10_guard_005` | `41` | `41` | `0` | `-0.035831 m` | `-0.060693 m` | `-0.049751` | `-0.002667` |
| `traffic_light_hybrid_h3_h10_guard_005` | `41` | `41` | `0` | `-0.035831 m` | `-0.060693 m` | `-0.049751` | `-0.002667` |
| `reward_h10_guard_strict_005` | `328` | `183` | `0` | `-0.028783 m` | `-0.109144 m` | `+0.003401` | `-0.004370` |

Bucket-level result for either hybrid screen:

| Bucket | Records | Changed | Posterior joint comfort | Safety regressions |
| --- | ---: | ---: | ---: | ---: |
| `overall` | `5939` | `41` | `41` | `0` |
| `traffic_light` | `1810` | `41` | `41` | `0` |
| `red_light_turn` | `942` | `40` | `40` | `0` |
| `sharp_turn` | `1916` | `40` | `40` | `0` |
| `normal` | `600` | `0` | `0` | `0` |

Mean selector-side losses for changed records:

```text
first_step_loss_m=0.001149
H3_loss_m=0.005618
H10_loss_m=0.010503
dp_reward_progress_loss_m=0.034823
target_speed_loss_mps=0.011491
```

Interpretation: the hybrid screen is much more conservative than
`reward_h10_guard_strict_005`, but it removes the positive posterior jerk mean
seen in that screen and every changed record is a posterior joint comfort
improvement on the existing labels. Because `red_light_turn` and `sharp_turn`
overlap with the traffic-light route labels, the changed records appear in
those buckets too; the screen itself is still gated by `traffic_light` and has
zero changes in `normal`.

This does not prove DP-CAMP is better than DP Top-1. It is a safe-looking
offline candidate for a default-off selector slice, but only on the current
non-formal artifact and still without paired replay SafetyCost evidence.

Mathematical conclusion: the screen remains a finite-candidate diagnostic. All
selection-side quantities are current-tick constants, and the rule is
fail-closed and deterministic. If later atomized with fixed nonnegative scales,
the score remains affine in `w` and the simplex/CVaR/L2 master remains convex.
The screen is not classical Benders and does not make DP sampling,
postprocessing, PerfectTracker, closed-loop outcomes, or trajectory
coordinates part of a Benders subproblem.

Decision: accept the traffic-light hybrid screen as the next default-off
engineering candidate. Do not claim improvement, do not run 12/36-run, and do
not train CAMP. The next admissible step is to implement this screen in replay
behind an explicit disabled-by-default CLI flag with complete metadata,
fail-closed audit fields, latency accounting, and strict mutual exclusion from
previous rejected postselectors. Only after local/AutoDL tests pass should a
small paired non-formal smoke be considered.

## Traffic-light hybrid replay postselector implementation

Implementation commit:

```text
a622f279413c2398c10c7ec7ae799dd0778403c2
```

Scope:

1. Added a disabled-by-default replay CLI flag:
   `--camp_traffic_light_hybrid_postselection`, with modes `off`,
   `step_h10_guard_005`, and `h3_h10_guard_005`.
2. The rule is mutually exclusive with lexicographic preselection,
   underprogress relaxation, PerfectTracker command postselection, and splice
   shadow. It requires a CAMP selector mode and `--camp_feasibility_source
   dp_reward`.
3. The online rule mirrors the accepted offline certificate screen:
   traffic-light enabled only, base feasible only, union-red and red-stopping
   nonworse, strict raw lateral and raw jerk improvement, bounded DP-reward
   progress loss, bounded H10 distance loss, bounded target-speed loss, and
   either bounded first-step loss or bounded H3 distance loss depending on the
   mode.
4. Selection records now include
   `traffic_light_hybrid_postselection`,
   `camp_selected_index_before_traffic_light_hybrid_postselection`, and
   `latency_ms_traffic_light_hybrid_postselection`.
5. Replay summary, validation summary, and the standalone replay summarizer
   preserve the new metadata. Core selection summaries now compute mean/p95
   latency for `traffic_light_hybrid_postselection_latency_ms`.

Local verification:

```text
git diff --check
# passed

python -m compileall -q \
  scripts\integrations\run_diffusion_planner_camp_replay.py \
  scripts\integrations\summarize_diffusion_planner_camp_replay.py \
  camp_core\camp_core\integrations\diffusion_planner.py \
  camp_core\tests\test_diffusion_planner_integration.py \
  camp_core\tests\test_diffusion_planner_replay_summary.py
# passed

$env:PYTHONPATH='F:\camp_core-main\camp_core'
python -m pytest \
  camp_core\tests\test_diffusion_planner_integration.py \
  camp_core\tests\test_diffusion_planner_replay_summary.py \
  -q
# 120 passed, 10 skipped in 1.68s
```

Local ruff note:

```text
ruff check <repo paths>
# reported E902 "stream did not contain valid UTF-8" for every repo target

Python UTF-8 decode check on the same files
# all five modified files decoded as UTF-8

ruff check <temporary copies of the same five files>
# All checks passed
```

Interpretation: the modified file contents pass ruff when copied out of the
current repo path, and Python decode/compileall both pass in place. The direct
repo-path ruff failure is treated as a local Windows path/ACL/tooling anomaly,
not as a code acceptance pass.

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# a622f279413c2398c10c7ec7ae799dd0778403c2

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_integration.py \
  camp_core/tests/test_diffusion_planner_replay_summary.py \
  -q
# 130 passed in 2.15s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  scripts/integrations/summarize_diffusion_planner_camp_replay.py \
  camp_core/camp_core/integrations/diffusion_planner.py \
  camp_core/tests/test_diffusion_planner_integration.py \
  camp_core/tests/test_diffusion_planner_replay_summary.py
# passed
```

AutoDL ruff availability:

```text
/root/autodl-tmp/dp312_venv/bin/python -c \
  "import importlib.util; print(bool(importlib.util.find_spec('ruff')))"
# False
```

AutoDL state after sync:

```text
CAMP HEAD/origin/main:
a622f279413c2398c10c7ec7ae799dd0778403c2

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The known AutoDL untracked files remain unhandled:

```text
diffusion_planner_integration.md
dp_camp_device_handoff.md
test_diffusion_planner_benchmark_matrix.py
```

Artifact path and SHA:

```text
No replay artifact was generated in this milestone. The artifact is the Git
implementation commit a622f279413c2398c10c7ec7ae799dd0778403c2.
```

Mathematical conclusion: the implementation is a finite-candidate selector
slice, not classical Benders. It operates only on current-tick fixed candidate
constants already logged or computed for the replay tick: feasible mask,
selection scores, DP reward progress, union-red, red-stopping, raw jerk,
raw lateral, PerfectTracker command target speed, first-step reach, and
PerfectTracker open-loop H3/H10 distances. It does not use candidate outcome
labels, closed-loop future outcomes, DP sampler variables, postprocessing
variables, PerfectTracker state-transition variables, or trajectory-coordinate
optimization variables. If later atomized with fixed nonnegative scaling, the
score remains affine in `w` and the simplex/CVaR/L2 master remains convex.

Decision: accept the default-off implementation as an engineering milestone.
Do not claim DP-CAMP is better than DP Top-1, do not run a 36-run, and do not
train CAMP from this implementation alone. The next admissible step is a small
paired non-formal smoke on sample59 seeds 1/2/3 only if the command line carries
the finite-candidate contract metadata, the hybrid flag is explicit, and the
comparison is evaluated with SafetyCost v1 plus hard gates and scenario
buckets. If the smoke fails any hard gate or critical bucket check, keep the
selector shadow/default-off and reject promotion.

## Traffic-light hybrid benchmark-matrix wrapper gate

Implementation commit:

```text
d15d74686d0373d5d7e2c92706aa937ec2005162
```

Scope:

1. Added `--camp_traffic_light_hybrid_postselection` to
   `scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py`, with
   modes `off`, `step_h10_guard_005`, and `h3_h10_guard_005`.
2. The wrapper forwards the flag only to CAMP variants and never to `top1`.
3. The wrapper validates that the hybrid selector requires
   `--camp_feasibility_source dp_reward` and `--reward_config`.
4. The wrapper rejects combining the hybrid selector with lexicographic
   preselection, PerfectTracker command postselection, underprogress
   relaxation, or splice shadow.

Local verification:

```text
git diff --check
# passed

$env:PYTHONPATH='F:\camp_core-main\camp_core'
python -m pytest camp_core\tests\test_diffusion_planner_benchmark_matrix.py -q
# 8 passed in 0.09s

python -m compileall -q \
  scripts\integrations\run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py
# passed

ruff check <temporary copies of the two modified files>
# All checks passed
```

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# d15d74686d0373d5d7e2c92706aa937ec2005162

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_benchmark_matrix.py \
  -q
# 8 passed in 0.03s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core/tests/test_diffusion_planner_benchmark_matrix.py
# passed
```

AutoDL state after sync:

```text
CAMP HEAD/origin/main:
d15d74686d0373d5d7e2c92706aa937ec2005162

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The known AutoDL untracked files remain unhandled:

```text
diffusion_planner_integration.md
dp_camp_device_handoff.md
test_diffusion_planner_benchmark_matrix.py
```

Artifact path and SHA:

```text
No replay artifact was generated in this milestone. The artifact is the Git
implementation commit d15d74686d0373d5d7e2c92706aa937ec2005162.
```

Mathematical conclusion: this wrapper change does not alter CAMP mathematics,
candidate generation, DP weights, CAMP weights, atom schema, or replay
selection rules. It only makes the already documented finite-candidate hybrid
selector reachable through the matched benchmark matrix with explicit CLI
metadata and validation. It introduces no classical Benders claim.

Decision: accept the wrapper gate. The next admissible step is to predeclare
and run only a small paired non-formal sample59 smoke for `top1` versus static
`redstopfloor05` with the explicit hybrid flag, strict pairing, SafetyCost v1,
hard gates, scenario buckets, no formal seeds, and latency checks. A failed
hard gate, critical bucket, CVaR90, or p95 latency result must reject promotion
and keep the selector default-off.

## Benchmark comparison strict-gate forwarding

Implementation commit:

```text
43620544f070ae53ab4bf4ad7df5e2f228873644
```

Scope:

1. Added `--scenario_bucket_manifest` to
   `scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py` and
   forward it to `compare_diffusion_planner_camp_replays.py`.
2. Added `--require_strict_pairing` to the benchmark matrix wrapper and forward
   it to the aggregate comparison command.
3. Extracted the comparison command builder into `_compare_command(...)` so the
   strict gate can be tested without running the full replay matrix.
4. Added a focused unit test proving that the wrapper comparison command carries
   the scenario bucket manifest, strict-pairing flag, and expected output paths.

Initial state audit:

```text
Local/GitHub before implementation:
## main...origin/main
e14f7a9b15373517b9f2c2847ea87a6ea767c81c
origin/main = e14f7a9b15373517b9f2c2847ea87a6ea767c81c

Known local untracked files left untouched:
camp-dp-session-2b67d33-20260615-231639-HANDOFF.md
camp-dp-session-8ae0950-20260616-235726/
slides prompt.md

AutoDL CAMP before implementation:
## main...origin/main
e14f7a9b15373517b9f2c2847ea87a6ea767c81c
origin/main = e14f7a9b15373517b9f2c2847ea87a6ea767c81c

Known AutoDL untracked files left untouched:
diffusion_planner_integration.md
dp_camp_device_handoff.md
test_diffusion_planner_benchmark_matrix.py

AutoDL DP:
## tier4-main...origin/tier4-main
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Local verification:

```text
python -m pytest camp_core\tests\test_diffusion_planner_benchmark_matrix.py -q
# 9 passed in 0.08s

python -m compileall -q \
  scripts\integrations\run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py
# passed

git diff --check
# passed

python -m ruff check \
  scripts\integrations\run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py
# E902 stream did not contain valid UTF-8 on the direct repo paths.

ruff check <temporary copies of the two modified files>
# All checks passed
```

The direct repo-path ruff failure is treated as the same local Windows
path/tooling anomaly observed in prior milestones: both files start with ASCII
`from`, contain no NUL bytes, compile successfully, and pass ruff after copying
to a temporary path.

AutoDL sync and verification for the implementation commit:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# 43620544f070ae53ab4bf4ad7df5e2f228873644

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_benchmark_matrix.py \
  -q
# 9 passed in 0.04s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core/tests/test_diffusion_planner_benchmark_matrix.py
# passed

AutoDL DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Artifact path and SHA:

```text
No replay artifact was generated in this milestone. The artifact is the Git
implementation commit 43620544f070ae53ab4bf4ad7df5e2f228873644.
```

Mathematical conclusion: this wrapper change does not alter DP, candidate
generation, CAMP weights, atom schema, finite-candidate scoring, or any online
selection rule. It only makes the benchmark matrix's aggregate comparison carry
the predeclared scenario bucket manifest and strict-pairing requirement. It
therefore strengthens the development gate evidence path and introduces no new
Benders, subproblem, or trajectory-coordinate convexity claim.

Decision: accept the strict-gate forwarding milestone. The next admissible
action is a small paired non-formal sample59 smoke only if the matrix command
uses `--scenario_bucket_manifest
configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json`
and `--require_strict_pairing`. Without those flags, a matrix run is collection
only and cannot be used as development-gate evidence.

## Traffic-light hybrid sample59 strict-gate smoke result

Code/documentation state:

```text
CAMP local/GitHub/AutoDL HEAD:
41840e0acd5a31d2055947f94fc50003f89d90ed

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Predeclared non-formal smoke command:

```bash
cd /root/autodl-tmp/camp_core

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --route sample_map_tl_route_59_to_86=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --model_path /root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --config /root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json \
  --reward_config configs/integrations/dp_camp_reward_eval.json \
  --output_root /root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0 \
  --steps 200 \
  --seeds 1,2,3 \
  --max_npcs 0,4 \
  --spawn_probabilities 0.3 \
  --traffic_light_modes on,off \
  --variants top1,static \
  --camp_atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --camp_static_weights /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/offline_weights_dp_static.npy \
  --num_candidates 8 \
  --candidate_noise_scale 1.0 \
  --candidate_reference_blend_steps 5 \
  --camp_feasibility_source dp_reward \
  --camp_fallback_mode learned \
  --camp_min_progress_ratio 0.8 \
  --camp_reward_horizon_steps 30 \
  --camp_traffic_light_hybrid_postselection step_h10_guard_005 \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --require_strict_pairing \
  --resume
```

Asset/dry-run audit:

```text
All required assets existed:
/root/autodl-tmp/Diffusion-Planner
/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth
/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json
/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
/root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json
/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/offline_weights_dp_static.npy
/root/autodl-tmp/camp_core/configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json
/root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json

Dry-run confirmed:
- seeds: 1,2,3 only; no formal seeds 11,12,13;
- variants: top1, static only;
- 12 paired run keys and 24 replay commands;
- aggregate compare includes --scenario_bucket_manifest and
  --require_strict_pairing.
```

Artifact paths and SHA:

```text
Root:
/root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0

Run log:
/root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0.run.log
sha256 2dc77b0311cef06ba3b491fd96a909e8418c9909482acda53b426c09da2fef4c

Comparison JSON:
/root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0/benchmark_comparison.json
sha256 15bcdab9e7eaa148f315411a9d872bdb8cae0a3cd4755956d689ef57429a2342

Comparison Markdown:
/root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0/benchmark_comparison.md
sha256 73aeb6de5a7a6bd91158f505f00a22f0fb7798844d8eed0f9e9beafccaaabb6c
```

Pairing and contract gates:

```text
top1 runs: 12
static runs: 12
common run keys: 12
union run keys: 12
missing keys: none
duplicate keys: none
strictly_paired: true

static summaries: 12
finite-candidate contract verified: 12/12
traffic-light hybrid metadata enabled: 12/12
formal seeds present: 0
```

Aggregate result for `static - top1`:

| Metric | Delta / status |
| --- | ---: |
| SafetyCost v1 | `+0.113350`, 95% CI `[+0.020770, +0.235245]` |
| SafetyCost v1 CVaR90 delta | `+0.373838`, 95% CI `[+0.000275, +0.680226]` |
| Route completion | `-0.000395`, within `0.001` tolerance |
| OBB collision | `0.0`, nonworse |
| Near miss | `+0.000417`, hard gate failed |
| Lane violation | `-0.000417`, nonworse |
| Realized red light | `0.0`, nonworse |
| Planned red light | `+0.005417` |
| Mean jerk | `+0.381034 m/s^3` |
| Mean p95 selection latency | `92.024 ms`, 95% CI high `93.856 ms`, latency gate passed |
| Hard gate | failed |
| SafetyCost claim | failed |

Scenario bucket deltas:

| Bucket | n pairs | SafetyCost v1 delta | CVaR90 delta | Notes |
| --- | ---: | ---: | ---: | --- |
| `overall` | 12 | `+0.113350` `[+0.022013, +0.240510]` | `+0.373838` `[+0.009428, +0.680226]` | failed |
| `sharp_turn` | 12 | `+0.113350` `[+0.022013, +0.240510]` | `+0.373838` `[+0.009428, +0.680226]` | failed |
| `traffic_light` | 6 | `+0.192722` `[+0.011026, +0.418117]` | `+0.680226` `[-0.043800, +0.680226]` | failed |
| `red_light_turn` | 6 | `+0.192722` `[+0.011026, +0.418117]` | `+0.680226` `[-0.043800, +0.680226]` | failed |

Coverage caveat: this sample59-only smoke covers `overall`, `sharp_turn`,
`traffic_light`, and `red_light_turn` under the development manifest. It still
does not cover `normal`, `npc_interaction`, `dense_scene`, or
`lane_change_or_merge`, so even a pass would not have been sufficient for the
broader development gate.

Mathematical conclusion: the smoke preserves the CAMP-side finite-candidate
contract and does not introduce a DP Benders claim. The traffic-light hybrid
postselector uses current-tick fixed candidate diagnostics and remains a
finite-candidate selector slice. The rejection is empirical and gate-based: the
selected fixed candidates are worse than DP Top-1 under SafetyCost v1 and the
near-miss hard gate despite preserving the mathematical contract.

Decision: reject promotion of
`--camp_traffic_light_hybrid_postselection step_h10_guard_005`. Do not run a
36-run, do not touch formal seeds, and do not train CAMP from this result. The
next admissible step is a read-only failure attribution on this smoke artifact:
identify the exact changed ticks/runs where the hybrid selector diverges from
candidate 0 or the original CAMP baseline, then determine which current-tick
atoms/proxies made those worse choices look attractive. A future selector must
be more explicitly Top-1-preserving and should override only when the
candidate-level evidence clears a stricter SafetyCost/hard-gate certificate.

## Traffic-light hybrid failure attribution

Code/documentation state:

```text
CAMP local/GitHub/AutoDL HEAD for attribution implementation:
956f4c3f27500a05fc5a3e791de4c8bc7b1f1590

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Added:
scripts/integrations/analyze_diffusion_planner_traffic_light_hybrid_failure_attribution.py
camp_core/tests/test_diffusion_planner_traffic_light_hybrid_failure_attribution.py
```

Local verification before committing `956f4c3`:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_traffic_light_hybrid_failure_attribution.py \
  -q
# 2 passed in 0.20s

python -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_traffic_light_hybrid_failure_attribution.py \
  camp_core\tests\test_diffusion_planner_traffic_light_hybrid_failure_attribution.py
# passed

git diff --check
# passed

python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_traffic_light_hybrid_failure_attribution.py \
  camp_core\tests\test_diffusion_planner_traffic_light_hybrid_failure_attribution.py
# All checks passed
```

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# 956f4c3f27500a05fc5a3e791de4c8bc7b1f1590

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_traffic_light_hybrid_failure_attribution.py \
  -q
# 2 passed in 0.14s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/analyze_diffusion_planner_traffic_light_hybrid_failure_attribution.py \
  camp_core/tests/test_diffusion_planner_traffic_light_hybrid_failure_attribution.py
# passed
```

Attribution command:

```bash
cd /root/autodl-tmp/camp_core

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_traffic_light_hybrid_failure_attribution.py \
  --root /root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0 \
  --baseline_root /root/autodl-tmp/camp_dp_rollout_outcome_sample59_209bdfc \
  --label traffic_light_hybrid_sample59_smoke_41840e0 \
  --output_json /root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0/failure_attribution_956f4c3/traffic_light_hybrid_failure_attribution.json \
  --output_md /root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0/failure_attribution_956f4c3/traffic_light_hybrid_failure_attribution.md
```

Artifact paths and SHA:

```text
Failure attribution JSON:
/root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0/failure_attribution_956f4c3/traffic_light_hybrid_failure_attribution.json
sha256 bb712a161a03e6bda43a12b8b4fa41fa6f1d5c295e20a25a9b99f004fb816beb

Failure attribution Markdown:
/root/autodl-tmp/camp_dp_traffic_light_hybrid_sample59_smoke_41840e0/failure_attribution_956f4c3/traffic_light_hybrid_failure_attribution.md
sha256 6932123517f5413016cd194042f8e7941056a8fc54b4a5d936743359aeccc1c3
```

Read-only attribution result:

```text
runs: 12
records: 2400
hybrid-changed records: 28
selected nonzero records after hybrid: 2164 (0.901667)

hybrid reasons:
- traffic_lights_disabled: 1200
- no_admissible_traffic_light_hybrid_candidate: 994
- fallback_or_no_base_feasible_candidate: 178
- selected_admissible_traffic_light_hybrid_candidate: 28

hybrid change types:
- nonzero_to_nonzero: 19
- to_candidate0: 9
- away_from_candidate0: 0
```

Feature deltas for the 28 changed records are reported as
`selected_after_hybrid - selected_before_hybrid`:

| Feature | Mean delta | Sign pattern |
| --- | ---: | --- |
| CAMP affine score | `+0.00447632` | worse in all 28 |
| DP total reward proxy | `-0.062418` | worse in all 28 |
| DP progress proxy | `-0.0330626` | worse in all 28 |
| Raw jerk proxy | `-0.0332337` | better in all 28 |
| Raw lateral proxy | `-0.00269563` | better in all 28 |
| Union red exposure | `0.0` | no change in all 28 |
| Red stopping exposure | `0.0` | no change in all 28 |
| H10 rollout distance | `-0.00784927` | worse in 25, better in 3 |
| H3 rollout distance | `-0.000575` | mixed |
| First-step reach | `0.0` | no change in all 28 |

Feature deltas against candidate 0 show that the changed hybrid choices were
not consistently better than DP Top-1:

| Feature | Mean delta vs candidate 0 | Sign pattern |
| --- | ---: | --- |
| Raw jerk proxy | `+0.0291454` | worse in 7, equal in 21 |
| Raw lateral proxy | `-0.00105264` | better in 15, worse in 4, equal in 9 |
| CAMP affine score | `-0.00080207` | better in 7, worse in 12, equal in 9 |
| DP total reward proxy | `+0.027817` | better in 9, worse in 10, equal in 9 |

Run-level paired deltas against the existing no-hybrid sample59 baseline root
were useful for attribution only:

| Run key | Changed ticks | SafetyCost v1 delta | Planned red delta | Near miss delta | Mean jerk delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| `seed_1/npc_0/tl_on` | 3 | `-0.935687` | `0.0` | `0.0` | `-8.07659` |
| `seed_1/npc_4/tl_on` | 1 | `+0.659598` | `0.0` | `+0.215` | `-6.15014` |
| `seed_2/npc_0/tl_on` | 19 | `-1.16328` | `-0.04` | `0.0` | `-5.56014` |
| `seed_2/npc_4/tl_on` | 1 | `-12.9364` | `-0.325` | `+0.01` | `-13.9365` |
| `seed_3/npc_0/tl_on` | 2 | `-0.580833` | `0.0` | `0.0` | `-5.69688` |
| `seed_3/npc_4/tl_on` | 2 | `-1.4508` | `0.0` | `0.0` | `-6.66011` |

Attribution conclusion: the traffic-light hybrid screen was not the main
source of the Top-1 regression. It changed only 28/2400 records, returned to
candidate 0 in 9 records, and never moved away from candidate 0. The broader
Top-1 comparison failure is mainly inherited from the base static
`redstopfloor05` selector, which selected nonzero candidates in 2164/2400
records. Where the hybrid did change a tick, it traded away the original CAMP
affine score, DP total proxy, DP progress proxy, and H10 rollout distance for
small raw jerk/lateral proxy improvements, with no same-tick red-light exposure
benefit.

Mathematical conclusion: this attribution is read-only and outcome-auditing; it
does not alter the finite-candidate CAMP contract. The admissible next design
must not be another traffic-light threshold tweak. It should first address the
base static selector's non-Top-1 behavior using a Top-1-preserving finite
candidate contract: DP remains the fixed black-box candidate generator; CAMP
may score fixed atoms and finite candidates; any non-Top-1 selection must be
justified by a predeclared current-tick safety certificate and strict
paired-gate evidence. If the safety certificate is atomized, the score must
remain affine in the CAMP master variable, with fixed finite diagnostics and no
closed-loop future outcome leakage.

Decision: keep `step_h10_guard_005` rejected/default-off. Do not run a 36-run,
do not touch formal seeds, and do not train new CAMP weights from this result.
The next iteration should be an offline, read-only Top-1-preservation audit:
compare base static `redstopfloor05` selected candidates against candidate 0
across the existing sample59 artifacts, identify exactly which affine atoms and
feasibility filters cause the 2164 nonzero selections, and propose a
predeclared finite-candidate rule that defaults to candidate 0 unless a
candidate clears a strict current-tick SafetyCost/hard-gate certificate.

## Top-1 preservation attribution

Code/documentation state:

```text
CAMP local/GitHub/AutoDL HEAD for attribution implementation:
680f92dfb29662bc7e135cd60ce28934d1b0822e

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Added:
scripts/integrations/analyze_diffusion_planner_top1_preservation.py
camp_core/tests/test_diffusion_planner_top1_preservation.py
```

Local verification before committing `680f92d`:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_top1_preservation.py \
  -q
# 2 passed in 1.27s

python -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_top1_preservation.py \
  camp_core\tests\test_diffusion_planner_top1_preservation.py
# passed

git diff --check
# passed

python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_top1_preservation.py \
  camp_core\tests\test_diffusion_planner_top1_preservation.py
# All checks passed
```

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# 680f92dfb29662bc7e135cd60ce28934d1b0822e

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_top1_preservation.py \
  -q
# 2 passed in 0.35s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/analyze_diffusion_planner_top1_preservation.py \
  camp_core/tests/test_diffusion_planner_top1_preservation.py
# passed
```

Attribution command:

```bash
cd /root/autodl-tmp/camp_core

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_top1_preservation.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preservation_attribution_680f92d/top1_preservation_attribution.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preservation_attribution_680f92d/top1_preservation_attribution.md
```

Artifact paths and SHA:

```text
Top-1 preservation attribution JSON:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preservation_attribution_680f92d/top1_preservation_attribution.json
sha256 2241d32d72b82af7fdd0ab7858315e12842661a93b319eda0529e0ab6ff6eefe

Top-1 preservation attribution Markdown:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preservation_attribution_680f92d/top1_preservation_attribution.md
sha256 2f061209f027ea7130800e73199f75a2c304255948cf0aa0a29b30dd4a1ff5b9
```

Scope note: the previous traffic-light hybrid failure attribution used the
sample59 smoke artifact because it audited the rejected hybrid postselector.
This Top-1 preservation attribution needs candidate closed-loop outcome labels
to separate candidate availability from proxy visibility, so it uses the
existing outcome-labeled `redstopfloor05` root
`candidate_outcome_labels_static_d97b7c2` with the versioned development bucket
manifest. This is still non-formal, read-only, and does not authorize formal
seeds.

Read-only attribution result:

```text
runs/logs: 36
records: 7200
nonfallback / fallback: 5939 / 1261
selected nonzero: 6874 (0.954722)
candidate0 feasible records: 5639
candidate0 feasible active overrides: 5478 (0.971449)
candidate0 infeasible selected nonzero: 300
all-infeasible selected nonzero: 1096

preservation categories:
- all_infeasible_selected_candidate0: 165
- all_infeasible_selected_nonzero: 1096
- candidate0_feasible_selected_candidate0: 161
- candidate0_feasible_selected_nonzero: 5478
- candidate0_infeasible_selected_nonzero: 300
```

Active override score attribution for the 5,478 records where candidate0 was
feasible but `redstopfloor05` selected a nonzero sampled candidate:

| Quantity | Value |
| --- | ---: |
| Mean selection score delta, selected - candidate0 | `-0.108999` |
| Mean affine contribution residual | `0.000000` |
| Mean outcome progress delta, selected - candidate0 | `+0.507174 m` |
| Mean outcome jerk delta, selected - candidate0 | `+0.013225 m/s^3` |
| Median outcome jerk delta, selected - candidate0 | `-0.007755 m/s^3` |
| Mean outcome lateral delta, selected - candidate0 | `+0.006316 m/s^2` |

Top affine contribution drivers for active overrides:

| Atom | Sum contribution | Mean contribution | Attractive count | Repulsive count | Mean raw delta | Mean weight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `progress_shortfall` | `-671.424297` | `-0.122567` | `5353` | `125` | `-0.542361` | `0.479370` |
| `red_stopping_margin_cost` | `-3.000000` | `-0.000548` | `7` | `1` | `-0.001166` | `0.050000` |
| `dp_prior_jerk_excess_cost` | `+70.877963` | `+0.012939` | `0` | `2632` | `+0.155055` | `0.059344` |
| `jerk_early` | `+6.211375` | `+0.001134` | `2688` | `2790` | `+2.097434` | `0.410287` |

Interpretation: the base static selector's active non-Top-1 behavior is driven
primarily by `progress_shortfall`. Red stopping contributes negligibly, while
the weighted jerk-related terms are net repulsive against the sampled
candidate. This explains why traffic-light and comfort postselectors were
trying to patch symptoms rather than the dominant score mechanism.

Candidate availability oracle relative to feasible candidate0:

| Progress budget | Candidate0 feasible | Outcome override available | Proxy override available | Hidden outcome | Proxy only | Selected matches outcome | Selected without outcome |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `0.00 m` | `5639` | `2792` (`0.495123`) | `1983` (`0.351658`) | `834` (`0.147899`) | `25` (`0.004433`) | `902` (`0.164659`) | `2744` (`0.500913`) |
| `0.05 m` | `5639` | `3214` (`0.569959`) | `2475` (`0.438908`) | `766` (`0.135840`) | `27` (`0.004788`) | `943` (`0.172143`) | `2341` (`0.427346`) |
| `0.10 m` | `5639` | `3476` (`0.616421`) | `2781` (`0.493173`) | `715` (`0.126796`) | `20` (`0.003547`) | `961` (`0.175429`) | `2085` (`0.380613`) |
| `0.25 m` | `5639` | `4054` (`0.718922`) | `3552` (`0.629899`) | `517` (`0.091683`) | `15` (`0.002660`) | `987` (`0.180175`) | `1527` (`0.278751`) |

At the predeclared `0.05 m` progress budget, outcome-labeled better candidates
exist in 3,214/5,639 candidate0-feasible records, but the current selected
candidate matches that outcome oracle in only 943/5,478 active overrides. In
2,341/5,478 active overrides, `redstopfloor05` selects a nonzero candidate even
though no outcome-superior override over candidate0 exists under the same
budget. This is the strongest current evidence that the dominant online proxy
does not align tightly enough with the closed-loop oracle.

Scenario bucket digest at the `0.05 m` budget:

| Bucket | Records | Active overrides | Override rate | Outcome available | Selected matches outcome | Selected without outcome |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `overall` | `7200` | `5478` | `0.971449` | `3214` | `943` | `2341` |
| `normal` | `600` | `596` | `0.993333` | `278` | `124` | `320` |
| `traffic_light` | `2400` | `1652` | `0.958793` | `1153` | `288` | `534` |
| `red_light_turn` | `1200` | `869` | `0.962348` | `447` | `141` | `429` |
| `sharp_turn` | `2400` | `1740` | `0.966667` | `912` | `284` | `843` |

Mathematical conclusion: this audit preserves the CAMP-side finite-candidate
contract. It uses fixed current-tick atoms, masks, weights, and scores for
online-relevant attribution, and uses candidate closed-loop outcomes only as
offline labels. The score contribution residual is zero to reported precision,
so the active override explanation is exactly affine in the logged CAMP
selection weights. DP sampling, smoothing, postprocessing, PerfectTracker,
closed-loop state, SafetyCost v1, and trajectory coordinates remain outside the
Benders-style layer.

Decision: accept this read-only attribution milestone. Reject any claim that
the current `redstopfloor05` selector is better than DP Top-1, and do not run a
new smoke, 36-run, formal seed, or retraining from this result. The next
admissible step is to design an offline-only Top-1-preserving counterfactual
selector that defaults to candidate0 whenever candidate0 is feasible, and
allows a nonzero candidate only when a predeclared current-tick certificate can
explain why the candidate is likely to match the outcome oracle. That design
must explicitly constrain the `progress_shortfall`-driven override mechanism
instead of adding another traffic-light or comfort threshold patch.

## Top-1-preserving counterfactual certificate audit

Code/documentation state:

```text
CAMP local/GitHub/AutoDL HEAD for counterfactual implementation:
d113405e73c31de31fe6863b1746b5ace072a151

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Added:
scripts/integrations/analyze_diffusion_planner_top1_preserving_counterfactual.py
camp_core/tests/test_diffusion_planner_top1_preserving_counterfactual.py

Implementation commits:
dc6857fb2786cd5bf1b47c847f783666ed2da58b
d113405e73c31de31fe6863b1746b5ace072a151
```

Local verification:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_top1_preserving_counterfactual.py \
  -q
# 2 passed in 0.47s

python -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_top1_preserving_counterfactual.py \
  camp_core\tests\test_diffusion_planner_top1_preserving_counterfactual.py
# passed

git diff --check
# passed

python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_top1_preserving_counterfactual.py \
  camp_core\tests\test_diffusion_planner_top1_preserving_counterfactual.py
# All checks passed
```

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# d113405e73c31de31fe6863b1746b5ace072a151

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_top1_preserving_counterfactual.py \
  -q
# 2 passed in 0.35s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/analyze_diffusion_planner_top1_preserving_counterfactual.py \
  camp_core/tests/test_diffusion_planner_top1_preserving_counterfactual.py
# passed
```

Counterfactual command:

```bash
cd /root/autodl-tmp/camp_core

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_top1_preserving_counterfactual.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preserving_counterfactual_d113405/top1_preserving_counterfactual.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preserving_counterfactual_d113405/top1_preserving_counterfactual.md
```

Artifact paths and SHA:

```text
Top-1-preserving counterfactual JSON:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preserving_counterfactual_d113405/top1_preserving_counterfactual.json
sha256 844b6e9f16b18459dd6847a672d127efab5c1adf93775962ce065a94bd50a124

Top-1-preserving counterfactual Markdown:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preserving_counterfactual_d113405/top1_preserving_counterfactual.md
sha256 6e743ce3ee770bd603faa80fab3f5237818006cc8b5a539d4087f82a89c51864
```

Counterfactual contract:

```text
If candidate0 is feasible:
  select candidate0 unless a predeclared current-tick certificate admits a
  nonzero candidate.
If candidate0 is infeasible or all candidates are infeasible:
  retain the logged CAMP baseline selection.

Rules evaluated:
- top1_only
- strict_joint_comfort_p005
- strict_joint_comfort_p010
- strict_any_comfort_p005
- strict_red_or_joint_comfort_p005
```

The rules use only current-tick fixed candidate diagnostics:
`feasible_mask`, `progress_shortfall`, union planned red-light cost, red
stopping cost, proxy jerk, proxy lateral, affine score, and candidate index.
Candidate closed-loop outcomes are posterior labels only. The reported
`candidate_label_safety_delta` is not a closed-loop run SafetyCost v1; it is a
candidate-outcome-label proxy using the SafetyCost v1 event weights and
comfort normalizations, with candidate progress loss replacing route
shortfall.

Overall result:

| Rule | Overrides | True overrides | False overrides | Hidden outcome | Mean label safety delta | CVaR90 label safety delta | Bool hard-gate worse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `top1_only` | `0` | `0` | `0` | `3214` | n/a | n/a | all zero |
| `strict_joint_comfort_p005` | `0` | `0` | `0` | `3214` | n/a | n/a | all zero |
| `strict_joint_comfort_p010` | `0` | `0` | `0` | `3476` | n/a | n/a | all zero |
| `strict_any_comfort_p005` | `2475` | `2430` | `45` | `766` | `+0.024715` | `+0.547965` | lane `4`, near-miss `4` |
| `strict_red_or_joint_comfort_p005` | `5` | `5` | `0` | `3209` | `-0.023355` | `-0.011449` | all zero |

Scenario bucket digest:

| Rule | Bucket | Overrides | True | False | Hidden | Mean label safety delta | CVaR90 label safety delta | Bool hard-gate worse |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `strict_any_comfort_p005` | `normal` | `278` | `278` | `0` | `0` | `-0.010202` | `+0.065232` | all zero |
| `strict_any_comfort_p005` | `traffic_light` | `791` | `764` | `27` | `380` | `+0.071272` | `+1.055255` | lane `2`, near-miss `4` |
| `strict_any_comfort_p005` | `red_light_turn` | `452` | `429` | `23` | `11` | `+0.078440` | `+0.939743` | lane `2` |
| `strict_any_comfort_p005` | `sharp_turn` | `920` | `879` | `41` | `17` | `+0.076327` | `+0.951803` | lane `4` |
| `strict_red_or_joint_comfort_p005` | `traffic_light` | `5` | `5` | `0` | `1148` | `-0.023355` | `-0.011449` | all zero |
| `strict_red_or_joint_comfort_p005` | `red_light_turn` | `5` | `5` | `0` | `442` | `-0.023355` | `-0.011449` | all zero |
| `strict_red_or_joint_comfort_p005` | `sharp_turn` | `5` | `5` | `0` | `907` | `-0.023355` | `-0.011449` | all zero |

Interpretation:

1. The default `top1_only` rule is fail-closed and safe by construction, but it
   misses 3,214 outcome-labeled opportunities at the `0.05 m` budget. It is a
   baseline, not a CAMP improvement.
2. Requiring both proxy jerk and proxy lateral to strictly improve is too
   conservative on this artifact: it admits zero candidates even at `0.10 m`.
3. Weakening the comfort trigger to either proxy jerk or proxy lateral gives
   useful coverage, but fails the development gate before any smoke: it has 45
   false overrides, positive mean and CVaR90 candidate-label safety delta, and
   actual posterior lane/near-miss hard-gate worse events.
4. The red-or-joint comfort rule is the only one with zero false overrides and
   negative candidate-label safety delta, but it covers only 5 records and
   leaves 3,209 hidden outcome opportunities. That is not enough evidence to
   implement an online selector or run a 12-run smoke.

Mathematical conclusion: the counterfactual selector family remains inside the
CAMP-side finite-candidate contract. It is deterministic, nonempty, and
fail-closed: candidate0 is retained whenever feasible unless the fixed
certificate admits a candidate; if candidate0 is infeasible, the logged CAMP
baseline is retained. All certificate inputs are fixed current-tick
finite-candidate constants. If these diagnostics are atomized with fixed
nonnegative scaling, the score can remain affine in the CAMP master variable.
No DP sampler, smoothing, postprocessing, PerfectTracker rollout, closed-loop
state, SafetyCost evaluator, or trajectory coordinate is promoted to a
Benders subproblem or cut source.

Decision: accept the counterfactual audit implementation and artifact. Reject
all evaluated rules for online promotion. Do not implement a default-off online
selector, do not run sample59 smoke, do not run a 36-run, do not touch formal
seeds, and do not retrain CAMP from this result. The next admissible step is
to diagnose the 766 hidden outcome opportunities left by
`strict_any_comfort_p005` and the 45 false overrides it creates. A viable next
certificate must keep the zero-hard-gate property of `strict_red_or_joint`
while recovering materially more of the hidden outcome opportunities, using
only current-tick finite-candidate diagnostics.

## Top-1-preserving failure attribution

Code/documentation state:

```text
CAMP local/GitHub/AutoDL HEAD for failure attribution implementation:
3914fc24b98a9d077411c20b858ac9e629e2a82c

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Added:
scripts/integrations/analyze_diffusion_planner_top1_preserving_failure_attribution.py
camp_core/tests/test_diffusion_planner_top1_preserving_failure_attribution.py
```

Local verification before committing `3914fc2`:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_top1_preserving_failure_attribution.py \
  -q
# 1 passed in 0.50s

python -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_top1_preserving_failure_attribution.py \
  camp_core\tests\test_diffusion_planner_top1_preserving_failure_attribution.py
# passed

python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_top1_preserving_failure_attribution.py \
  camp_core\tests\test_diffusion_planner_top1_preserving_failure_attribution.py
# All checks passed

git diff --check
# passed
```

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# 3914fc24b98a9d077411c20b858ac9e629e2a82c

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_top1_preserving_failure_attribution.py \
  -q
# 1 passed in 0.33s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/analyze_diffusion_planner_top1_preserving_failure_attribution.py \
  camp_core/tests/test_diffusion_planner_top1_preserving_failure_attribution.py
# passed
```

Attribution command:

```bash
cd /root/autodl-tmp/camp_core

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_top1_preserving_failure_attribution.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --rule strict_any_comfort_p005 \
  --label redstopfloor05_outcome_labels \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preserving_failure_attribution_3914fc2/top1_preserving_failure_attribution.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preserving_failure_attribution_3914fc2/top1_preserving_failure_attribution.md
```

Artifact paths and SHA:

```text
Top-1-preserving failure attribution JSON:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preserving_failure_attribution_3914fc2/top1_preserving_failure_attribution.json
sha256 ec2cfce2988e88afdbe3148f0116b8e1178dedbf698791509503c11b470b085d

Top-1-preserving failure attribution Markdown:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/top1_preserving_failure_attribution_3914fc2/top1_preserving_failure_attribution.md
sha256 87540d6bc92ae9153c8792af79670c0745788402e350705758bccca787cf8961
```

Scope: this is a posterior attribution of the already rejected
`strict_any_comfort_p005` counterfactual. It does not change CAMP selection,
does not add online features, does not use outcome labels online, and does not
authorize smoke/formal runs.

Attribution records:

```text
logs: 36
records: 7200
candidate0 feasible: 5639
strict_any_comfort_p005 overrides: 2475
true overrides: 2430
false overrides: 45
hidden outcome opportunities: 766
```

False override attribution:

| False reason | Records |
| --- | ---: |
| `outcome_progress_loss_exceeds_budget` | `41` |
| `outcome_lane_violation_worse` | `4` |
| `outcome_near_miss_worse` | `4` |

False override posterior deltas:

| Quantity | Mean | p50 | p90 | CVaR90 |
| --- | ---: | ---: | ---: | ---: |
| Candidate-label safety delta | `+2.695321` | `+0.083592` | `+9.975013` | `+18.085182` |
| Outcome progress delta | `-0.111991 m` | `-0.062693 m` | `-0.050057 m` | `-0.016686 m` |
| Outcome jerk delta | `-0.977071 m/s^3` | `-0.311361` | `-0.070417` | `-0.038248` |
| Outcome lateral delta | `-0.097621 m/s^2` | `-0.021709` | `-0.012714` | `-0.008733` |

False override current-tick proxy deltas:

| Proxy delta | Mean | p50 | p90 | CVaR90 |
| --- | ---: | ---: | ---: | ---: |
| `progress_shortfall` | `-0.080080` | `+0.029566` | `+0.047528` | `+0.048685` |
| `proxy_jerk` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |
| `proxy_lateral` | `-0.097621` | `-0.021709` | `-0.012714` | `-0.008733` |
| `selection_score` | `-0.077217` | `-0.008493` | `+0.005887` | `+0.010007` |
| `union_red` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |
| `red_stopping` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |

False overrides are not red-light failures. They are mostly lateral-improving
proxy choices that appear admissible under `progress_shortfall <= 0.05 m` but
still lose more than the posterior outcome progress budget or introduce
posterior lane/near-miss events. Tightening red or comfort thresholds alone
does not address this failure mode.

Hidden outcome attribution:

| Hidden blocker | Records |
| --- | ---: |
| `progress_shortfall_exceeds_budget` | `762` |
| `union_red_worse` | `3` |
| `red_stopping_worse` | `2` |

Hidden best-candidate posterior deltas:

| Quantity | Mean | p50 | p90 | CVaR90 |
| --- | ---: | ---: | ---: | ---: |
| Candidate-label safety delta | `-0.081842` | `-0.053780` | `-0.022837` | `-0.007711` |
| Outcome progress delta | `+0.391860 m` | `0.000000 m` | `0.000000 m` | `+0.399299 m` |
| Outcome jerk delta | `-0.428219 m/s^3` | `-0.328512` | `-0.115526` | `-0.068620` |
| Outcome lateral delta | `-0.027290 m/s^2` | `-0.020974` | `-0.005056` | `-0.002503` |

Hidden best-candidate current-tick proxy deltas:

| Proxy delta | Mean | p50 | p90 | CVaR90 |
| --- | ---: | ---: | ---: | ---: |
| `progress_shortfall` | `+0.732152` | `+0.582485` | `+1.501063` | `+2.040917` |
| `proxy_jerk` | `0.000000` | `0.000000` | `0.000000` | `0.000000` |
| `proxy_lateral` | `-0.027290` | `-0.020974` | `-0.005056` | `-0.002503` |
| `selection_score` | `+0.142213` | `+0.113094` | `+0.315361` | `+0.424764` |
| `union_red` | `+0.003264` | `0.000000` | `0.000000` | `+0.003264` |
| `red_stopping` | `+0.001646` | `0.000000` | `0.000000` | `+0.010714` |

Hidden opportunities are overwhelmingly blocked by `progress_shortfall`, even
though their posterior outcomes are safety-improving and often progress-neutral
or progress-positive. The hidden best candidates generally have no proxy jerk
change and a lateral proxy improvement, but the `progress_shortfall` proxy
assigns a large penalty that is not reflected in posterior candidate progress.

Bucket summary:

| Bucket | False records | Hidden records | Notes |
| --- | ---: | ---: | --- |
| `traffic_light` | `27` | `380` | false mean safety delta `+2.929527`; hidden mean safety delta `-0.069964` |
| `red_light_turn` | `23` | `11` | false mean safety delta `+1.713300`; hidden mean safety delta `-0.001908` |
| `sharp_turn` | `41` | `17` | false mean safety delta `+1.990198`; hidden mean safety delta `+0.000860` |

Mathematical conclusion: the attribution stays inside the CAMP-side
finite-candidate contract. It evaluates fixed finite candidates and fixed
current-tick diagnostics; outcome labels are used only to classify posterior
false/hidden cases. No online selector, atom schema, CAMP master, DP sampler,
tracker, simulator, SafetyCost run metric, or trajectory coordinate is changed
or claimed as a Benders subproblem.

Decision: accept the failure-attribution tool and artifact. Continue rejecting
`strict_any_comfort_p005` and all previously evaluated counterfactual rules for
online promotion. Do not run sample59 smoke, 36-run, formal seeds, or CAMP
retraining. The next admissible step is to design a progress-proxy replacement
or guard audit using current-tick diagnostics already logged in the artifact
such as `candidate_route_progress`, `candidate_step_reach`,
`candidate_perfect_tracker_first_step_reach_m`,
`candidate_perfect_tracker_target_speed_mps`, and H3/H5/H10 open-loop rollout
distance. The target is to reduce the 762 progress-shortfall hidden blockers
without reintroducing the 45 false-override failure mode.

## Progress proxy guard audit

Code/documentation state:

```text
CAMP local/GitHub/AutoDL HEAD for progress proxy guard implementation:
9ba9c78ca0e8157be86c6a5ae5419e2a72f7cada

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Added:
scripts/integrations/analyze_diffusion_planner_progress_proxy_guard.py
camp_core/tests/test_diffusion_planner_progress_proxy_guard.py
```

Local verification before committing `9ba9c78`:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_progress_proxy_guard.py \
  -q
# 1 passed in 0.55s

python -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_progress_proxy_guard.py \
  camp_core\tests\test_diffusion_planner_progress_proxy_guard.py
# passed

python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_progress_proxy_guard.py \
  camp_core\tests\test_diffusion_planner_progress_proxy_guard.py
# All checks passed

git diff --check
# passed
```

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# 9ba9c78ca0e8157be86c6a5ae5419e2a72f7cada

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_progress_proxy_guard.py \
  -q
# 1 passed in 0.32s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/analyze_diffusion_planner_progress_proxy_guard.py \
  camp_core/tests/test_diffusion_planner_progress_proxy_guard.py
# passed
```

Audit command:

```bash
cd /root/autodl-tmp/camp_core

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_progress_proxy_guard.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_proxy_guard_9ba9c78/progress_proxy_guard.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_proxy_guard_9ba9c78/progress_proxy_guard.md
```

Artifact paths and SHA:

```text
Progress proxy guard JSON:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_proxy_guard_9ba9c78/progress_proxy_guard.json
sha256 173db0412231e9595dca9ba3dbf6e046ee6ced31df11818784afbee7617fd22b

Progress proxy guard Markdown:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/progress_proxy_guard_9ba9c78/progress_proxy_guard.md
sha256 edfba263aa4bfd4e92fce6a1fdbe35c55dbc557984fd991ed38d0d30444edc26
```

Scope: this audit swaps only the progress guard inside the already rejected
any-comfort Top-1-preserving certificate. The common certificate remains:
candidate0 feasible, nonzero base-feasible candidate, red proxies nonworse,
proxy jerk/lateral nonworse, and at least one proxy comfort metric strictly
better. Candidate outcomes are posterior labels only.

Overall result:

| Descriptor guard | Available | Overrides | True | False | Hidden | Mean override label safety delta | CVaR90 override label safety delta | Bool hard-gate worse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `progress_shortfall_p005` | `5639` | `2475` | `2430` | `45` | `766` | `+0.024715` | `+0.547965` | lane `4`, near-miss `4` |
| `route_progress_loss005` | `0` | `0` | `0` | `0` | `0` | n/a | n/a | all zero |
| `route_progress_loss010` | `0` | `0` | `0` | `0` | `0` | n/a | n/a | all zero |
| `step_reach_loss005` | `5639` | `4523` | `2526` | `1997` | `18` | `+1.654178` | `+15.412951` | lane `2`, near-miss `6` |
| `tracker_first_step_reach_loss005` | `5639` | `4525` | `2528` | `1997` | `16` | `+1.653408` | `+15.412951` | lane `2`, near-miss `6` |
| `target_speed_loss005` | `5639` | `3657` | `2069` | `1588` | `574` | `+1.258204` | `+11.747174` | lane `2`, near-miss `6` |
| `h3_rollout_distance_loss005` | `5639` | `4231` | `2359` | `1872` | `235` | `+1.443427` | `+13.331187` | lane `4`, near-miss `6` |
| `h5_rollout_distance_loss005` | `5639` | `3919` | `2209` | `1710` | `434` | `+0.744194` | `+6.570457` | lane `4`, near-miss `6` |
| `h10_rollout_distance_loss005` | `5639` | `3366` | `2167` | `1199` | `621` | `+0.393579` | `+3.600969` | lane `4`, near-miss `5` |
| `h10_rollout_distance_loss010` | `5639` | `3873` | `2218` | `1655` | `449` | `+0.732186` | `+6.539325` | lane `4`, near-miss `6` |

Interpretation:

1. `candidate_route_progress` is not available in this outcome-labeled root,
   so it cannot currently serve as a validated online guard without regenerating
   labels or logging repair.
2. Step reach, PerfectTracker first-step reach, target speed, and H3/H5/H10
   rollout distances reduce some hidden opportunities, but all introduce far
   more false overrides than `progress_shortfall_p005`. Their mean and CVaR90
   candidate-label safety deltas are strongly positive, and each creates
   posterior lane/near-miss hard-gate worse cases.
3. H10 rollout distance at `0.05 m` is the least bad of the tested alternatives
   by mean safety delta, but it still has 1,199 false overrides and hard-gate
   worse events. This is not close to an online or smoke-ready rule.
4. The failure mode is not fixed by simply replacing `progress_shortfall` with
   another single current-tick progress descriptor. The alternatives either
   miss many hidden opportunities or admit too many false positives.

Mathematical conclusion: all audited descriptors are fixed current-tick
finite-candidate diagnostics. The audit does not use outcome labels as online
inputs and does not change the CAMP atom schema, weights, selector, DP sampler,
postprocessing, tracker, simulator, or SafetyCost evaluator. If any descriptor
is later atomized, it must be fixed, finite, nonnegative after scaling, and
score-affine in the CAMP master variable. No classical Benders claim is made
for trajectory coordinates or simulator outcomes.

Decision: accept the progress proxy guard audit implementation and artifact.
Reject every tested single-descriptor replacement for online promotion. Do not
run sample59 smoke, 36-run, formal seeds, or CAMP retraining. The next
admissible step is a stricter composite guard audit, not another single-proxy
swap: candidate rules should combine an outcome-free progress descriptor with
additional current-tick constraints that target the observed false-positive
mechanism, especially posterior progress loss and lane/near-miss exposure. A
candidate composite rule must beat `progress_shortfall_p005` on false overrides
and hard-gate worse counts while recovering more of its 766 hidden
opportunities before any online selector implementation is considered.

## Composite guard audit

Code state for the composite guard implementation:

```text
CAMP local/GitHub/AutoDL HEAD for implementation:
a620738ee1bb0c8ba1b578eb4dec31a3e4aa2e87

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Added:
scripts/integrations/analyze_diffusion_planner_composite_guard.py
camp_core/tests/test_diffusion_planner_composite_guard.py
```

Local verification before committing `a620738`:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_composite_guard.py \
  -q
# 1 passed in 0.50s

python -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_composite_guard.py \
  camp_core\tests\test_diffusion_planner_composite_guard.py
# passed

python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_composite_guard.py \
  camp_core\tests\test_diffusion_planner_composite_guard.py
# All checks passed

git diff --check
# passed
```

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
. /etc/network_turbo
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# a620738ee1bb0c8ba1b578eb4dec31a3e4aa2e87

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_composite_guard.py \
  -q
# 1 passed in 0.33s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/analyze_diffusion_planner_composite_guard.py \
  camp_core/tests/test_diffusion_planner_composite_guard.py
# passed
```

Audit command:

```bash
cd /root/autodl-tmp/camp_core

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_composite_guard.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/composite_guard_a620738/composite_guard.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/composite_guard_a620738/composite_guard.md
```

Artifact paths and SHA:

```text
Composite guard JSON:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/composite_guard_a620738/composite_guard.json
sha256 33d5905574e2302099854d98bdde7c1a8019610d6f97438ff29e43eb54efa54b

Composite guard Markdown:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/composite_guard_a620738/composite_guard.md
sha256 0b41236fae7462b64beef5ce8be24d418745f9d6efe0c4fcee4371fb7ff2b183
```

Scope: this audit keeps DP as a fixed black-box candidate source and evaluates
only deterministic finite-candidate guards. Candidate outcomes are posterior
labels only. No online selector, atom schema, CAMP weights, DP sampler,
postprocessing, tracker, simulator, smoke run, 36-run, formal seed, or training
path is changed.

Overall result on 36 logs / 7200 records / 5639 candidate0-feasible records:

| Rule | Overrides | True | False | Hidden | Safety<0 | Safety>0 | Mean safety | CVaR90 safety | Bool hard-gate worse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `baseline_shortfall_any_p005` | `2475` | `2430` | `45` | `766` | `2030` | `445` | `+0.024715` | `+0.547965` | lane `4`, near-miss `4` |
| `banded_shortfall_m010_p005` | `1541` | `1506` | `35` | `1692` | `1080` | `461` | `-0.007948` | `+0.077186` | none |
| `banded_shortfall_m020_p005` | `1909` | `1871` | `38` | `1326` | `1456` | `453` | `+0.001559` | `+0.227684` | near-miss `3` |
| `tiered_banded_m010_escape_p010_h10_p005_score0` | `1573` | `1522` | `51` | `1675` | `1093` | `480` | `-0.007588` | `+0.078595` | none |
| `tiered_banded_m020_escape_p010_h10_p005_score0` | `1939` | `1886` | `53` | `1311` | `1468` | `471` | `+0.001716` | `+0.226710` | near-miss `3` |
| `intersect_shortfall_p010_h10_p005_score0` | `2066` | `1999` | `67` | `1180` | `1912` | `154` | `+0.027668` | `+0.607063` | lane `4`, near-miss `4` |

Interpretation:

1. The observed false-positive mechanism is partly exposed by an outcome-free
   current-tick signal: excessively negative `progress_shortfall` relative to
   candidate0. Filtering to a bounded band `[-0.10, 0.05]` eliminates all
   posterior lane/near-miss hard-gate worse records in this artifact and turns
   the mean candidate-label safety delta negative.
2. The banded rule is too conservative for online promotion. It drops overrides
   from 2475 to 1541 and increases hidden opportunities from 766 to 1692.
   This protects hard gates but loses too much candidate coverage.
3. The tiered H10/score escape recovers only 32 records for the `[-0.10,0.05]`
   band, with 16 additional true and 16 additional false overrides. It preserves
   the no-bool-hard-gate-worse property but does not materially solve hidden
   candidate visibility.
4. The non-tiered intersect contrast is not viable. It keeps many overrides but
   reintroduces the same lane/near-miss hard-gate worse cases as the baseline
   and increases false overrides.
5. This is a useful diagnostic, not an online selector. The current logged
   proxy set can either protect hard gates by becoming conservative or preserve
   coverage while retaining hard-gate risk; it does not yet provide an
   industrially acceptable composite override.

Mathematical conclusion: the composite audit remains inside the CAMP-side
finite-candidate contract. The rule inputs are fixed current-tick constants:
feasibility, `progress_shortfall` delta, H10 open-loop distance delta,
red proxies, proxy jerk/lateral, selection score, and deterministic candidate
index. Outcome labels are used only for posterior evaluation. If the banded
progress delta or H10 loss are later atomized, they must be fixed, finite,
nonnegative after scaling, and score-affine in the CAMP master variable. No
claim is made that DP, SG smoothing, `postprocess_reference`, PerfectTracker,
closed-loop future states, SafetyCost, or trajectory coordinates are Benders
subproblems or cut sources.

Decision: accept the composite guard audit tool and artifact. Reject all tested
composite rules for online promotion and do not run sample59 smoke, 36-run,
formal seeds, or CAMP retraining. The next admissible step is candidate
visibility analysis focused on the 1692 hidden cases under
`banded_shortfall_m010_p005`: identify which current-tick, outcome-free
features could recover true safety-improving candidates without reintroducing
the previously eliminated lane/near-miss hard-gate violations. If no such
feature exists in the current logs, the correct engineering move is to add
shadow-only logging of a new DP/current-map diagnostic rather than weakening
hard gates.

## Hidden candidate visibility audit

Code state for the hidden-visibility implementation:

```text
CAMP local/GitHub/AutoDL HEAD for implementation:
effec62b7ab0269a37d1dfc1b926d18f618e3b0b

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Added:
scripts/integrations/analyze_diffusion_planner_hidden_visibility.py
camp_core/tests/test_diffusion_planner_hidden_visibility.py

Fix:
effec62b7ab0269a37d1dfc1b926d18f618e3b0b
```

Local verification before committing `effec62`:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_hidden_visibility.py \
  -q
# 1 passed in 0.52s

python -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_hidden_visibility.py \
  camp_core\tests\test_diffusion_planner_hidden_visibility.py
# passed

python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_hidden_visibility.py \
  camp_core\tests\test_diffusion_planner_hidden_visibility.py
# All checks passed

git diff --check
# passed
```

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
. /etc/network_turbo
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# effec62b7ab0269a37d1dfc1b926d18f618e3b0b

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_hidden_visibility.py \
  -q
# 1 passed in 0.35s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/analyze_diffusion_planner_hidden_visibility.py \
  camp_core/tests/test_diffusion_planner_hidden_visibility.py
# passed
```

Audit command:

```bash
cd /root/autodl-tmp/camp_core

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_hidden_visibility.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/candidate_outcome_labels_static_d97b7c2 \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label redstopfloor05_outcome_labels \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/hidden_visibility_effec62/hidden_visibility.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/hidden_visibility_effec62/hidden_visibility.md
```

Artifact paths and SHA:

```text
Hidden visibility JSON:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/hidden_visibility_effec62/hidden_visibility.json
sha256 dbc9e2f41c8a8470addafabb343af5a9bba029f56ba7c85fd5152db2dd8ebe9c

Hidden visibility Markdown:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/hidden_visibility_effec62/hidden_visibility.md
sha256 86d01f48caa4a0d94771879704d237b09cba6a5a0e7daa8519a8a614fe6b3eed
```

Scope: this audit keeps `banded_shortfall_m010_p005` as the protected baseline
and evaluates shadow-only escape screens only in records where that protected
baseline keeps candidate0 while an outcome-label oracle candidate exists. It
does not change online selection, atoms, CAMP weights, DP, tracker, simulator,
smoke runs, formal seeds, or training.

Base protected rule recap:

```text
candidate0-feasible records: 5639
protected-rule overrides: 1541
protected-rule false overrides: 35
protected-rule hidden outcome records: 1692
risky common candidates in hidden contexts: 2498
bool hard-gate worse under protected-rule overrides: all zero
hidden blockers:
  progress_delta_below_lower_band: 749
  progress_delta_exceeds_budget: 941
  red_stopping_worse: 3
  union_red_worse: 4
```

Feature availability and overlap:

| Feature | Hidden best oracle p10/p50/p90 | Risky common p10/p50/p90 | Availability |
| --- | --- | --- | --- |
| `progress_delta` | `-0.6595 / +0.1578 / +1.1461` | `+0.0848 / +0.2433 / +0.6783` | available |
| `score_delta` | `-0.1641 / +0.0178 / +0.2270` | `+0.0127 / +0.0479 / +0.1428` | available |
| `h10_distance_loss` | `-0.2236 / +0.0425 / +0.3617` | `-0.0086 / +0.0554 / +0.1946` | available |
| `step_reach_loss` | `-0.0163 / +0.0025 / +0.0305` | `-0.0037 / +0.0025 / +0.0130` | available |
| `target_speed_loss` | `-0.1611 / +0.0257 / +0.2991` | `-0.0375 / +0.0252 / +0.1300` | available |
| `route_progress_loss` | n/a | n/a | missing for all 1692 hidden and 2498 risky-common rows |
| `proxy_lateral_delta` | `-0.0477 / -0.0120 / -0.0008` | `-0.0357 / -0.0054 / -0.0008` | available |

Shadow-only escape screen results:

| Screen | Escape | True recovery | False escape | Hidden remaining | Mean escape safety | CVaR90 escape safety | Bool hard-gate worse | Missing descriptors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `escape_p010_score0` | `34` | `29` | `5` | `1658` | `-0.048207` | `+0.027288` | none | `0` |
| `escape_p010_h10_p005_score0` | `17` | `16` | `1` | `1675` | `-0.033131` | `+0.030256` | none | `0` |
| `escape_p010_h5_p005_score0` | `20` | `19` | `1` | `1672` | `-0.040772` | `+0.030256` | none | `0` |
| `escape_p010_step_p005_score0` | `34` | `29` | `5` | `1658` | `-0.048207` | `+0.027288` | none | `0` |
| `escape_p010_target_speed_p005_score0` | `15` | `14` | `1` | `1677` | `-0.027857` | `+0.030256` | none | `0` |
| `escape_p010_route_p005_score0` | `0` | `0` | `0` | `1692` | n/a | n/a | none | `1692` |
| `escape_lower_m020_p005_score0` | `366` | `365` | `1` | `1326` | `-0.007745` | `+0.265762` | near-miss `1` | `0` |
| `escape_lower_m020_p005_h10_p005_score0` | `331` | `330` | `1` | `1361` | `-0.001208` | `+0.289522` | near-miss `1` | `0` |

Interpretation:

1. The existing logged current-tick features do not provide a good recovery
   signal for the protected rule. The hard-gate-safe escape screens recover only
   14 to 29 true hidden cases out of 1692.
2. The lower-band recovery screens recover many more hidden cases, but they
   reintroduce a posterior near-miss hard-gate worse record and have weak tail
   safety (`CVaR90` around `+0.27` to `+0.29`). That violates the development
   gate even though the mean remains slightly negative.
3. `route_progress_loss` cannot currently be evaluated in this labeled root:
   the field name exists in some logs, but the loaded descriptor is unavailable
   for all hidden and risky-common rows. It cannot be promoted or used as
   evidence without repaired shadow logging.
4. `h10_distance_loss`, `step_reach_loss`, `target_speed_loss`,
   `score_delta`, and `proxy_lateral_delta` have substantial distribution
   overlap between hidden-good and risky-common candidates. They are useful for
   diagnosis but not sufficient as a selector escape.

Mathematical conclusion: the audit remains inside the CAMP-side finite-candidate
contract. All screen inputs are fixed current-tick finite-candidate diagnostics.
Outcome labels only classify hidden, recovered, and false cases. If a later
feature is atomized, use nonnegative fixed transforms such as upper/lower hinge
violations or bounded-window costs so CAMP scores remain affine in the master
variables. No DP sampler, postprocess, tracker, closed-loop future state,
SafetyCost, or trajectory-coordinate optimization is treated as a Benders
subproblem or cut source.

Decision: accept the hidden-visibility audit implementation and artifact.
Reject all tested escape screens for online promotion. Do not run sample59
smoke, 36-run, formal seeds, or CAMP retraining. The next engineering step is
not to weaken the protected hard gates; it is to add default-off shadow-only
logging for a new route/map-aligned progress diagnostic, then regenerate or
repair outcome-labeled artifacts so the diagnostic is available for the hidden
and risky-common rows.

## Shadow route-progress logging

Code state for the shadow logging implementation:

```text
CAMP local/GitHub/AutoDL HEAD for implementation:
7b61ea2b1434f44c9a814994d0156c68c8d87999

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Modified:
scripts/integrations/run_diffusion_planner_camp_replay.py
scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py
camp_core/tests/test_diffusion_planner_benchmark_matrix.py
```

Change summary:

1. Added replay flag `--camp_shadow_route_progress`.
2. When enabled, replay computes `candidate_route_progress` with the existing
   `_candidate_route_progress` route-centerline projection and writes it to
   `camp_selection_log.json`.
3. The old selector-effecting route guard remains unchanged: feasibility is
   modified only when `--camp_min_candidate0_route_progress_ratio` is non-null.
4. The matrix runner forwards `--camp_shadow_route_progress` only to CAMP
   variants, not `top1`.
5. Replay summary and validation metadata now include
   `camp_shadow_route_progress = {enabled, selection_effect: false,
   logged_field: candidate_route_progress}`.

Local verification before committing `7b61ea2`:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py \
  -q
# 9 passed in 0.06s

$env:PYTHONPATH='F:\camp_core-main\camp_core'
python -m pytest \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate0_route_progress_guard_uses_route_projection \
  -q
# 1 passed in 0.43s

python -m compileall -q \
  scripts\integrations\run_diffusion_planner_camp_replay.py \
  scripts\integrations\run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py
# passed

git diff --check
# passed
```

Note: local `ruff` on the Windows environment reported `E902 stream did not
contain valid UTF-8` for the existing large replay/matrix files even though
direct Python UTF-8 decode, `ast.parse`, and `compileall` all succeeded. It was
not used as a blocking check for this milestone.

AutoDL sync and verification:

```text
cd /root/autodl-tmp/camp_core
. /etc/network_turbo
git fetch origin main
git merge --ff-only origin/main
git rev-parse HEAD
# 7b61ea2b1434f44c9a814994d0156c68c8d87999

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_benchmark_matrix.py \
  camp_core/tests/test_diffusion_planner_integration.py::test_candidate0_route_progress_guard_uses_route_projection \
  -q
# 10 passed in 0.38s

PYTHONPATH=/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m compileall -q \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core/tests/test_diffusion_planner_benchmark_matrix.py
# passed
```

Scope and mathematical boundary: this is an observability-only change. It logs
a fixed current-tick finite-candidate route-progress diagnostic computed from
the already generated candidate trajectories and the current route centerline.
It does not change the DP sampler, candidate set, feasibility mask, CAMP atoms,
weights, score, selected index, PerfectTracker, simulator, SafetyCost, smoke
matrix, formal seeds, or any training path. If later atomized, route-progress
loss should be represented as a fixed nonnegative current-tick atom, for
example `max(0, progress_0 - progress_k) / scale`, preserving affine CAMP
scores in the master variables.

Decision: accept this as a default-off observability milestone. It does not
make CAMP-DP better by itself and is not evidence for online selector
promotion. The next admissible experiment is to regenerate or repair a small
non-formal outcome-labeled artifact with `--camp_shadow_route_progress` enabled
for the same development setup, then rerun hidden-visibility analysis to check
whether `route_progress_loss` becomes available and separates hidden-good from
risky-common candidates without hard-gate regressions.

## Targeted shadow route-progress label pass

Code state for the route-progress visibility screen:

```text
CAMP local/GitHub/AutoDL HEAD for analyzer extension:
6b973613ebe09f006ab0f0f2f72a0b717b3da601

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Implementation:

```text
Modified:
scripts/integrations/analyze_diffusion_planner_hidden_visibility.py
camp_core/tests/test_diffusion_planner_hidden_visibility.py
```

Added shadow-only screens:

```text
escape_route_nonworse_lower_m200_p005_score0
escape_route_nonworse_lower_m200_p005_h10_p005_score0
```

These screens keep the protected base rule but, only when the base rule keeps
candidate0 and an outcome-label oracle candidate exists, allow lower-band
recovery down to `progress_delta >= -2.0 m` if `route_progress_loss <= 0` and
the CAMP score is nonworse. The second screen also requires H10 open-loop
distance loss `<= 0.05 m`.

Local verification before committing `6b97361`:

```text
python -m pytest \
  camp_core\tests\test_diffusion_planner_hidden_visibility.py \
  -q
# 1 passed in 0.66s

python -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_hidden_visibility.py \
  camp_core\tests\test_diffusion_planner_hidden_visibility.py
# passed

python -m ruff check \
  scripts\integrations\analyze_diffusion_planner_hidden_visibility.py \
  camp_core\tests\test_diffusion_planner_hidden_visibility.py
# All checks passed

git diff --check
# passed
```

Targeted label-pass scope:

```text
Artifact root:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_sample59_seed2_61a20a4

Route:
sample_map_tl_route_59_to_86

Seed:
2

NPC counts:
0, 4

Traffic lights:
on

Steps:
200

Variant:
static redstopfloor05

Selection-effecting route guard:
disabled; camp_min_candidate0_route_progress_ratio = null

Shadow diagnostic:
--camp_shadow_route_progress
```

Replay command template:

```bash
cd /root/autodl-tmp/camp_core

/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --map_path /root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm \
  --route /root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --model_path /root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --config /root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json \
  --device cuda \
  --steps 200 \
  --seed 2 \
  --max_npcs <0-or-4> \
  --spawn_probability 0.3 \
  --traffic_lights on \
  --advance_mode perfect \
  --reward_config configs/integrations/dp_camp_reward_eval.json \
  --camp_selector_mode static \
  --camp_atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --camp_static_weights /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/offline_weights_dp_static.npy \
  --num_candidates 8 \
  --candidate_noise_scale 1.0 \
  --camp_feasibility_source dp_reward \
  --camp_fallback_mode uniform \
  --camp_min_progress_ratio 0.8 \
  --camp_reward_horizon_steps 30 \
  --camp_collect_closed_loop_outcomes \
  --camp_outcome_horizon_steps 30 \
  --camp_shadow_route_progress \
  --near_miss_threshold_m 2.0 \
  --output_dir <artifact-root>/sample_map_tl_route_59_to_86/seed_2/npc_<0-or-4>/spawn_0p3/tl_on/static
```

Route-progress logging check:

```text
npc_0: records=200, route_progress_nonnull=200, vector length=8
npc_4: records=200, route_progress_nonnull=200, vector length=8

camp_shadow_route_progress:
{enabled: true, selection_effect: false, logged_field: candidate_route_progress}

camp_min_candidate0_route_progress_ratio:
null
```

Dataset/readiness audits:

```bash
cd /root/autodl-tmp/camp_core

ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_sample59_seed2_61a20a4
OUT=$ROOT/readiness_audit_6b97361

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  --root "$ROOT" \
  --atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --expected_logs 2 \
  --expected_candidates 8 \
  --expected_advance_mode perfect \
  --required_candidate_field candidate_route_progress \
  --closed_loop_outcome_policy required \
  --forbid_seed 11 --forbid_seed 12 --forbid_seed 13 \
  --require_finite_candidate_contract \
  --output_json "$OUT/dataset_audit_required_outcomes.json"

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_candidate_availability_inputs.py \
  --root "$ROOT" \
  --output_json "$OUT/candidate_availability_input_readiness.json" \
  --output_md "$OUT/candidate_availability_input_readiness.md" \
  --fail_on_not_ready
```

Readiness result:

```text
Dataset audit:
passed=true
logs=2
records=400
candidates=3200
all_infeasible_records=114
closed_loop_outcome_policy=required
finite_candidate_contract_verified=true
forbidden_seed_check=true
required_candidate_field=candidate_route_progress

Candidate availability input readiness:
candidate_availability_oracle_ready=true
current_tick_proxy_inputs_ready=true
outcome_labels_ready=true
candidate_counts={8: 400}
nonfallback_records=286
fallback_records=114
```

Readiness artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `dataset_audit_required_outcomes.json` | `fc41b12141ebd6756623be9254345c135ea6788d11535bbb137950b7cea224ba` |
| `candidate_availability_input_readiness.json` | `4e6bced80940d70ee148320b20d22deeb53e0e566554c6f9791470fd8cfcab01` |
| `candidate_availability_input_readiness.md` | `4b49fd609178a4220ed0fc4455df76a72d9845c8c34cbde23219744f0edcb3fb` |

Hidden-visibility command:

```bash
cd /root/autodl-tmp/camp_core

ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_sample59_seed2_61a20a4
OUT=$ROOT/hidden_visibility_route_progress_6b97361

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_hidden_visibility.py \
  --root "$ROOT" \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label shadow_route_progress_sample59_seed2 \
  --output_json "$OUT/hidden_visibility.json" \
  --output_md "$OUT/hidden_visibility.md"
```

Hidden-visibility artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `hidden_visibility.json` | `ef679649b46a88a164a7ec5b0c059b48b7eb3a4f9fb435bd5644ad2be5fd0884` |
| `hidden_visibility.md` | `f80b38b596d8d16580fa612c8347b9f97b475a65c9a3960456fb151274e9864f` |

Targeted hidden-visibility result:

```text
records=400
logs=2
candidate0_feasible=267
nonfallback=286
fallback=114

protected base overrides=107
protected base true overrides=103
protected base false overrides=4
protected base hidden outcome records=27
protected base bool hard-gate worse: all zero
hidden blockers:
  progress_delta_below_lower_band=25
  red_stopping_worse=3
  union_red_worse=4
```

Feature separation in this targeted artifact:

| Feature | Hidden best oracle p10/p50/p90 | Risky common p10/p50/p90 |
| --- | --- | --- |
| `route_progress_loss` | `-0.6978 / -0.2418 / -0.1256` | `+0.1003 / +0.3027 / +0.8046` |
| `progress_delta` | `-0.6820 / -0.2349 / -0.1219` | `+0.0810 / +0.2911 / +0.7925` |
| `score_delta` | `-0.1678 / -0.0584 / -0.0275` | `+0.0119 / +0.0576 / +0.1630` |
| `h10_distance_loss` | `-0.2132 / -0.0734 / -0.0104` | `+0.0045 / +0.0675 / +0.1876` |

Escape screen result:

| Screen | Escape | True | False | Hidden remaining | Mean safety | CVaR90 safety | Bool hard-gate worse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `escape_p010_route_p005_score0` | `0` | `0` | `0` | `27` | n/a | n/a | none |
| `escape_route_nonworse_lower_m200_p005_score0` | `23` | `23` | `0` | `4` | `-0.033225` | `-0.003654` | none |
| `escape_route_nonworse_lower_m200_p005_h10_p005_score0` | `23` | `23` | `0` | `4` | `-0.027064` | `-0.003654` | none |
| `escape_lower_m020_p005_score0` | `6` | `6` | `0` | `21` | `-0.005694` | `-0.002305` | none |
| `escape_lower_m020_p005_h10_p005_score0` | `6` | `6` | `0` | `21` | `-0.005694` | `-0.002305` | none |

Interpretation:

1. `candidate_route_progress` is now available and finite for every record in
   this targeted artifact.
2. In these two sample59 seed-2 traffic-light runs, `route_progress_loss <= 0`
   sharply separates hidden-good candidates from risky-common candidates.
   Hidden-good candidates are route-progress nonworse/better than candidate0,
   while risky-common candidates have positive route-progress loss.
3. The route-progress lower-band screen recovers `23/27` hidden opportunities
   with zero posterior false escape and zero bool hard-gate worsening. This is
   the first positive evidence that a current-tick, outcome-free diagnostic can
   recover lower-band hidden candidates without weakening hard gates.
4. The evidence is intentionally narrow: only `sample59_86`, seed `2`,
   traffic-lights on, NPC counts `0/4`. It is not a selector promotion gate and
   does not justify sample59 12-run smoke, 36-run, formal seeds, or CAMP
   retraining.

Mathematical conclusion: the route-progress screen remains inside the
CAMP-side finite-candidate contract. It uses fixed current-tick route-centerline
projection values already logged with each candidate. Online use would require
a fixed nonnegative atom such as `max(0, progress_0 - progress_k) / scale` or a
finite-candidate lexicographic guard with deterministic fail-closed fallback.
Outcome labels are used only to evaluate true/false recovery after the fact.
No DP sampler, SG smoothing, `postprocess_reference`, PerfectTracker,
closed-loop future state, SafetyCost, or trajectory-coordinate optimization is
treated as a Benders subproblem or cut source.

Decision: accept the targeted shadow route-progress label pass and analyzer
extension as a positive diagnostic milestone. Reject online promotion from this
targeted evidence alone. The next admissible step is to expand the same
shadow-only route-progress label pass to the full predeclared non-formal
development grid, or at minimum all three routes and seeds `1/2/3`, then rerun
hidden-visibility and bucketed hard-gate analysis. Only if the route-progress
lower-band screen remains hard-gate safe and materially recovers hidden
candidates across buckets should a default-off online selector implementation
be considered.

## Full36 shadow route-progress label pass

Code state for the expanded shadow-only label pass:

```text
CAMP local/GitHub/AutoDL HEAD for replay artifact generation:
d5c2075be56d9486a71a280fc2e17b515740b8ff

CAMP local/GitHub/AutoDL HEAD for H10-lower analyzer rerun:
b2d916ddf01c16555ff428ca5c287164bc4fbd90

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Scope:

```text
Artifact root:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_full36_d5c2075

Routes:
sample_map_tl_route_59_to_86
sample_map_route_2_to_104
nishishinjuku_release_auto_route

Seeds:
1, 2, 3

NPC counts:
0, 4

Traffic lights:
off, on

Steps:
200

Variant:
static redstopfloor05

Selection-effecting route guard:
disabled; camp_min_candidate0_route_progress_ratio = null

Shadow diagnostic:
--camp_shadow_route_progress

Candidate outcomes:
--camp_collect_closed_loop_outcomes, horizon 30, posterior labels only
```

The run was split into three disjoint route jobs writing the same root with
`--resume`; the main full command later skipped helper-completed directories.
All three jobs exited `0`. Final coverage:

```text
completed_summaries=36
selection_logs=36
routes_completed:
  12 nishishinjuku_release_auto_route
  12 sample_map_route_2_to_104
  12 sample_map_tl_route_59_to_86
missing_expected=0
```

Dataset and readiness audits:

```bash
cd /root/autodl-tmp/camp_core

ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_full36_d5c2075
OUT=$ROOT/audit_d5c2075

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  --root "$ROOT" \
  --atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --expected_logs 36 \
  --expected_candidates 8 \
  --expected_advance_mode perfect \
  --required_candidate_field candidate_route_progress \
  --closed_loop_outcome_policy required \
  --forbid_seed 11 --forbid_seed 12 --forbid_seed 13 \
  --require_finite_candidate_contract \
  --output_json "$OUT/dataset_audit_required_outcomes.json"

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_candidate_availability_inputs.py \
  --root "$ROOT" \
  --output_json "$OUT/candidate_availability_input_readiness.json" \
  --output_md "$OUT/candidate_availability_input_readiness.md" \
  --fail_on_not_ready
```

Audit result:

```text
dataset_audit.passed=true
logs=36
records=7200
candidates=57600
all_infeasible_records=1261
candidate_counts={8: 7200}
candidate_availability_oracle_ready=true
current_tick_proxy_inputs_ready=true
outcome_labels_ready=true
formal seeds 11/12/13 absent
```

Audit artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `dataset_audit_required_outcomes.json` | `b266b9ca48fceb3422de6dab6608794ae3e25960941ce92c363686e7801d7a5a` |
| `candidate_availability_input_readiness.json` | `ab2a7c5cf01651827de7aa4c1508ec6b0b5a86bcad9257d1516cc9b12426c582` |
| `candidate_availability_input_readiness.md` | `c478aae3f4fe4fe673c6c2a2aa769a838d4bc5b98f184b1b9cd2b993795bb723` |
| `predeclare_shadow_route_progress_full36_d5c2075.txt` | `db93f46edcce472766a58107b1c0c8afe1093f23d7b944a503751996c3f80c00` |
| `predeclare_shadow_route_progress_full36_d5c2075_sample2.txt` | `7805ed87bb428625ca471c1775ff2e50c1f2cb7661f7acd197cc81753587718c` |
| `predeclare_shadow_route_progress_full36_d5c2075_nishishinjuku.txt` | `88e04d7b9a6502f5de08149b8da1c2c89377f2ea4d1d5a1fb3d14da97170b907` |

Hidden-visibility rerun with the H10-lower sensitivity screens added in
`b2d916d`:

```bash
cd /root/autodl-tmp/camp_core

ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_full36_d5c2075
OUT=$ROOT/audit_b2d916d

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_hidden_visibility.py \
  --root "$ROOT" \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label shadow_route_progress_full36_h10_lower \
  --output_json "$OUT/hidden_visibility.json" \
  --output_md "$OUT/hidden_visibility.md"
```

Hidden-visibility artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `audit_b2d916d/hidden_visibility.json` | `d26f6e2f1cee56849df4767681690fbc7565a674dbd96b607df19b9df420e3a4` |
| `audit_b2d916d/hidden_visibility.md` | `0d071965884107a26ea87dcd7d8d039b5c735d71c1aee4bf3a4b9e62a5ab056d` |

Full36 hidden-visibility totals:

```text
records=7200
logs=36
candidate0_feasible=5639
nonfallback=5939
fallback=1261
base_hidden_context_records=1692
```

Screen results:

| Screen | Escape | True | False | Hidden remaining | Mean safety | CVaR90 safety | Bool hard-gate worse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `escape_route_nonworse_lower_m200_p005_score0` | `921` | `919` | `2` | `771` | `-0.023214` | `0.209884` | `near_miss:2` |
| `escape_route_nonworse_lower_m200_p005_h10_p005_score0` | `869` | `867` | `2` | `823` | `-0.018648` | `0.224750` | `near_miss:2` |
| `escape_route_nonworse_lower_m200_h10_min_m005_score0` | `303` | `303` | `0` | `1389` | `-0.042837` | `-0.002960` | none |
| `escape_route_nonworse_lower_m200_h10_min_m010_score0` | `468` | `468` | `0` | `1224` | `-0.037510` | `-0.002637` | none |
| `escape_route_nonworse_lower_m200_h10_min_m015_score0` | `610` | `610` | `0` | `1082` | `-0.035286` | `-0.003040` | none |
| `escape_route_nonworse_lower_m200_h10_min_m020_score0` | `738` | `736` | `2` | `954` | `-0.009831` | `0.265366` | `near_miss:2` |

Bucket detail for the strongest zero-false H10-lower screen
`escape_route_nonworse_lower_m200_h10_min_m015_score0`:

| Bucket | Hidden contexts | Escape | True | False | Hidden remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| overall | `1692` | `610` | `610` | `0` | `1082` |
| normal | `130` | `81` | `81` | `0` | `49` |
| traffic_light | `614` | `179` | `179` | `0` | `435` |
| red_light_turn | `84` | `69` | `69` | `0` | `15` |
| sharp_turn | `166` | `132` | `132` | `0` | `34` |

False-escape attribution for the rejected route-progress lower-band screen:

```text
Both posterior false escapes occur in:
nishishinjuku_release_auto_route, seed=2, max_npcs=4, traffic_lights=true.

selection_step=92:
selected candidate 1
false reason: outcome_near_miss_worse
candidate_label_safety_delta=+9.943471
progress_delta=-0.140615
route_progress_loss=0.0
h10_distance_loss=-0.187265
score_delta=-0.041247

selection_step=121:
selected candidate 6
false reason: outcome_near_miss_worse
candidate_label_safety_delta=+9.922577
progress_delta=-0.382462
route_progress_loss=0.0
h10_distance_loss=-0.160604
score_delta=-0.109239
```

Interpretation:

1. The broad route-progress lower-band screen is rejected for online promotion.
   It is no longer full36 safe: two NPC near-miss false escapes appear on
   `nishishinjuku`, and CVaR90 safety becomes positive.
2. The failure mode is not red-light exposure. It is an NPC interaction case
   where route progress is nonworse and CAMP score is lower, but the chosen
   candidate is materially more aggressive over the H10 PerfectTracker
   open-loop proxy.
3. Adding a current-tick H10 lower-bound guard is promising as an offline
   sensitivity result. `h10_distance_loss >= -0.15 m` recovers `610/1692`
   hidden contexts with zero posterior false escapes and no hard-gate boolean
   worsening across the labeled buckets. Relaxing to `-0.20 m` reintroduces the
   two near-miss false escapes, so `-0.20 m` is rejected.
4. This is still not an online selector gate. The H10 lower-bound screen was
   added after the full36 failure attribution and must be treated as a
   development sensitivity, not as predeclared validation. The next admissible
   step is to formalize the finite-candidate lexicographic rule using
   route-progress and H10 lower-bound atoms/proxies, then run a default-off
   no-outcome shadow selector audit before any online replay matrix.

Latency note:

```text
latency_ms_including_candidate_generation p95 = 831.907 ms
latency_ms_outcome_collection p95 = 707.316 ms
latency_ms_candidate_generation p95 = 95.188 ms
latency_ms_camp_selection p95 = 9.584 ms
latency_ms_shadow_perfect_tracker_open_loop p95 = 1.094 ms
```

This artifact is offline label-pass evidence, not deployable latency evidence,
because it intentionally collects posterior closed-loop candidate outcomes.
The H10 open-loop proxy itself is current-tick and cheap in this artifact, but
any online selector implementation still needs a no-outcome latency smoke with
the exact deployed metadata before it can be considered industrially usable.

Mathematical boundary: all accepted or rejected screen features here are fixed
current-tick finite-candidate diagnostics. Candidate outcomes are posterior
labels used only for offline true/false attribution. If route-progress or H10
lower-bound terms are atomized later, they must be represented as fixed
nonnegative transforms such as `max(0, progress_0 - progress_k) / scale` and
`max(0, h10_distance_k - h10_distance_0 - budget) / scale` or an equivalent
finite-candidate lexicographic guard. The score remains affine in CAMP master
variables. No DP sampler, Savitzky-Golay smoothing, `postprocess_reference`,
PerfectTracker state transition, closed-loop future state, SafetyCost, or
trajectory-coordinate optimization is treated as a Benders subproblem or cut
source.

Decision: accept the full36 shadow-route-progress artifact and H10-lower
sensitivity analysis as offline diagnostic evidence. Reject the original
route-progress lower-band screen and the `h10_min_m020` relaxation. Do not run
formal seeds, CAMP retraining, or online selector matrices from this result.
Next step: write the finite-candidate lexicographic route-progress plus H10
lower-bound rule as a default-off, fail-closed selector proposal, then verify it
with a no-outcome shadow-only audit and local/AutoDL tests before any replay
smoke.

### Route-progress plus H10 shadow selector audit

Commit `ec8efe248cca45c5a46592e9cdfa0b462707f4ba` added a default-off offline
audit for the finite-candidate route-progress plus H10 lower-bound selector:

```text
scripts/integrations/analyze_diffusion_planner_route_h10_shadow_selector.py
camp_core/tests/test_diffusion_planner_route_h10_shadow_selector.py
```

Commit `f6e7cb7a3a7bf9185ce01d0120531ecf5f1735a5` extended the report with
stage-level outcome summaries so that the protected base band and the
route-H10 escape can be judged separately.

Local verification:

```bash
py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_hidden_visibility.py \
  camp_core\tests\test_diffusion_planner_route_h10_shadow_selector.py \
  -q

py -3.12 -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_route_h10_shadow_selector.py \
  camp_core\tests\test_diffusion_planner_route_h10_shadow_selector.py

git diff --check
```

Result: `2 passed`, compileall passed, and whitespace check passed. AutoDL was
fast-forwarded to `f6e7cb7a3a7bf9185ce01d0120531ecf5f1735a5`; the targeted
route-H10 test passed on AutoDL, and DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Full36 audit command:

```bash
cd /root/autodl-tmp/camp_core

ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_full36_d5c2075
OUT=$ROOT/route_h10_shadow_selector_f6e7cb7

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_route_h10_shadow_selector.py \
  --root "$ROOT" \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --label route_h10_shadow_selector_full36_f6e7cb7 \
  --output_json "$OUT/route_h10_shadow_selector.json" \
  --output_md "$OUT/route_h10_shadow_selector.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `route_h10_shadow_selector_f6e7cb7/route_h10_shadow_selector.json` | `9ac51716651bd03f46217a2faaf50ea3d9cdecd506c040475af30d1b6c04d164` |
| `route_h10_shadow_selector_f6e7cb7/route_h10_shadow_selector.md` | `9404b5c9da844e22f462dd596c7de83b90ba7db024a17ac74b0d5ca5ca98f2ad` |

Full36 records:

```text
logs=36
records=7200
nonfallback=5939
fallback=1261
candidate0_feasible=5639
candidate0_infeasible=300
descriptor_missing_when_escape_needed=0
```

Shadow selector stage counts over candidate0-feasible records:

| Stage | Records |
| --- | ---: |
| `base` | `1541` |
| `candidate0_retain_empty_mask` | `3486` |
| `route_h10_escape` | `612` |

Comparison against DP candidate0:

| Selector | Overrides | True | False | Mean safety delta | CVaR90 safety delta | Hard bool worse |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| shadow route-H10 selector | `2153` | `2116` | `37` | `-0.006433` | `0.161312` | `near_miss:2` |
| logged redstopfloor05 selector | `5478` | `943` | `4535` | `0.199437` | `2.038179` | `lane_violation:4, near_miss:7` |

Stage-level attribution:

| Stage | Overrides | True | False | Mean safety delta | CVaR90 safety delta | Hard bool worse | False reasons |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `base` | `1541` | `1506` | `35` | `-0.007948` | `0.077186` | none | `outcome_progress_loss_exceeds_budget:35` |
| `route_h10_escape` | `612` | `610` | `2` | `-0.002617` | `0.318433` | `near_miss:2` | `outcome_near_miss_worse:2` |

The two route-H10 hard-gate failures occur on
`nishishinjuku_release_auto_route`, seed `2`, NPC `4`, traffic lights enabled,
at selection steps `117` and `133`. In both records, candidate0 and the selected
route-H10 escape have zero current-tick red-light and red-stopping proxy cost;
the regression is NPC near-miss, not red-light behavior.

An ad hoc current-tick red-improvement trigger was checked without changing the
artifact. Requiring strict `union_red` or `red_stopping` improvement removes the
two near-miss failures, but leaves only `1` route-H10 escape. This is too narrow
to serve as the main selector, but it confirms that the current failure mode is
not a red-light risk-response case.

The selection logs do not contain `candidate_obstacles`; they contain posterior
`candidate_closed_loop_outcomes[*].min_obstacle_clearance_m`, but that field is
an outcome label and cannot be used online. Therefore the current full36
artifact cannot support a legal no-leakage candidate-level NPC clearance guard.

Mathematical boundary: the audited route-progress and H10 quantities are fixed
current-tick finite-candidate constants and can be represented later as
nonnegative hinge atoms without breaking affine CAMP scoring or convex
simplex/CVaR/L2 master updates. The posterior near-miss and
`min_obstacle_clearance_m` labels cannot be atoms, selector inputs, Benders
subproblem data, or cut sources. A future NPC clearance atom is admissible only
if it is computed from current simulator state and candidate geometry before
selection, then logged as a candidate-level descriptor such as a nonnegative
clearance violation hinge.

Decision: reject the current route-progress plus H10 lower-bound selector for
online promotion. It improves substantially over the logged redstopfloor05
selector in this posterior audit, but it still has `2` hard-gate near-miss
regressions and positive CVaR90 safety delta. Do not run formal seeds, CAMP
retraining, or replay matrices from this selector. The next admissible step is a
default-off diagnostic replay extension that logs a candidate-level current-tick
NPC clearance descriptor, followed by a no-outcome shadow audit combining
route-progress, H10 lower-bound, and clearance hinge guards.

### Obstacle-clearance shadow descriptor v2

The route-progress plus H10 selector failure above required a legal
candidate-level NPC clearance descriptor. Commit
`4bc6485182ede0c05c39508c84a9e218c5ba6cd6` first added a default-off
`candidate_obstacle_clearance` shadow log with schema
`candidate_current_tick_obstacle_clearance_v1`. That v1 descriptor was
mathematically admissible as a current-tick fixed candidate diagnostic, but it
computed exact OBB distance for every candidate-obstacle-step pair.

The first nishishinjuku NPC smoke exposed the runtime problem:

```text
Commit: 4bc6485182ede0c05c39508c84a9e218c5ba6cd6
Artifact:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/obstacle_clearance_nishiseed2_4bc6485_20260617_202038

Route: nishishinjuku_release_auto_route
Seed: 2
NPC max: 4
Traffic lights: on
Steps: 140
Closed-loop candidate outcomes: disabled

records=140
schema=candidate_current_tick_obstacle_clearance_v1
mean_shadow_obstacle_clearance_latency_ms=50.409628
p95_shadow_obstacle_clearance_latency_ms=67.640427
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `fee45daed2811a6afebf0624b95c17c23f3b0a33a51d94939467cce459863b9b` |
| `camp_replay_summary.json` | `2c1b02e604d1e941d7794c34b2f3f49dd6d4379f97662feb538acceb0b5fb067` |
| `camp_validation_summary.json` | `32b944368faf691f69bd5e26148f1234dacaa2e7d7a2e43d219b25ea96443d8e` |

Decision: reject v1 exact-OBB clearance as an online descriptor candidate. Its
inputs are legal, but the measured per-tick latency is far too large for the
industrial budget.

Commit `832a76b1f32b2b85c9ad98e2617c764e80f383e1` replaced the shadow
descriptor with schema `candidate_current_tick_obstacle_clearance_v2`. The v2
definition keeps the descriptor default-off and selection-effect-free, but uses
a conservative bounding-circle lower bound for each dynamic OBB pair:

```text
lower_bound = max(0, ||center_ego - center_obstacle|| - radius_ego - radius_obstacle)
```

The reported hinge costs use this lower bound:

```text
soft_clearance_violation = max(0, soft_threshold - lower_bound)
near_miss_violation = max(0, near_miss_threshold - lower_bound)
```

Exact OBB distance is now evaluated only when the lower bound is already within
`max(soft_threshold, near_miss_threshold)`, and is logged only as diagnostic
provenance via `exact_min_obstacle_clearance_m` and `exact_evaluated_pairs`.
The compatibility field `min_obstacle_clearance_m` now mirrors
`min_obstacle_clearance_lower_bound_m`.

Local verification for `832a76b1f32b2b85c9ad98e2617c764e80f383e1`:

```text
PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core
py -3.12 -m pytest camp_core\tests -q
# 337 passed, 5 skipped

py -3.12 -m compileall -q \
  camp_core\camp_core\integrations\diffusion_planner.py \
  scripts\integrations\run_diffusion_planner_camp_replay.py \
  scripts\integrations\run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core\tests\test_diffusion_planner_integration.py \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py
# passed

git diff --check
# passed
```

AutoDL sync used a git bundle because direct GitHub access failed with a GnuTLS
TLS termination error. AutoDL CAMP was fast-forwarded to
`832a76b1f32b2b85c9ad98e2617c764e80f383e1`; AutoDL DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Targeted AutoDL tests passed:

```text
4 passed in 0.61s
```

The v2 no-outcome nishishinjuku smoke used the same route, seed, NPC setting,
traffic-light setting, and horizon as the v1 latency smoke:

```text
Artifact:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/obstacle_clearance_nishiseed2_832a76b_20260617_v2

records=140
schema=candidate_current_tick_obstacle_clearance_v2
mean_shadow_obstacle_clearance_latency_ms=2.011791
p95_shadow_obstacle_clearance_latency_ms=2.522393
non_null_records=110
positive_soft_records=0
exact_evaluated_pairs_total=0
```

The previously failing route-H10 near-miss steps still do not show a current
candidate-obstacle clearance violation in this smoke:

```text
step 117: selected_index=2, min lower-bound range 20.639138..20.661243 m
step 133: selected_index=6, min lower-bound range 28.837287..28.853339 m
soft clearance costs: all zero
exact evaluated pairs: all zero
```

This means the v2 descriptor is useful as a legal low-latency current-tick
diagnostic, but it does not explain or solve the route-H10 posterior near-miss
failures.

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `5bfd2cc46b663ed0ae12ce1283116f8ed1714d35f0bfb71dfb2d2b18a35f7113` |
| `camp_replay_summary.json` | `efc7a9ad911973e0c32064ffb19b5d6042b918b2ac5d10aad55ef4832d8ec415` |
| `camp_validation_summary.json` | `673322becac357abc8be7d3787aca148e37b0eb56e985c33d0fd0304eae6b60a` |

Mathematical boundary: v2 clearance lower bounds are computed from the fixed
current-tick finite candidate set, current predicted obstacle geometry, and
static obstacles before selection. The resulting hinge values are finite,
nonnegative constants for the current tick. If atomized later, the CAMP score
remains affine in the master weights and the simplex/CVaR/L2 master stays
convex. The optional exact OBB fields are diagnostic provenance only. This does
not make DP sampling, SG smoothing, `postprocess_reference`, PerfectTracker,
future closed-loop states, SafetyCost, or trajectory-coordinate optimization a
Benders subproblem or cut source.

Decision: accept v2 as the current default-off obstacle-clearance logging
implementation and reject v1 exact-OBB logging for online latency. Do not
promote any selector from this smoke. The full selection p95 in this single
NPC smoke is still above 100 ms, and the clearance descriptor did not expose
the route-H10 near-miss failure. The next admissible step is a no-outcome
offline shadow audit that combines the already logged route-progress, H10
lower-bound, and v2 clearance descriptor fields without changing selection.

### No-outcome route-H10-clearance shadow certificate audit

Commit `d5c72e7da78df85e41d450997a9488e5e4ddbadc` added a dedicated
no-outcome analyzer:

```text
scripts/integrations/analyze_diffusion_planner_no_outcome_shadow_certificate.py
camp_core/tests/test_diffusion_planner_no_outcome_shadow_certificate.py
```

Commit `45bafb28c30e98f3f0c120046cd1ed0f443ae59b` then relaxed only the
diagnostic provenance parser so that `min_obstacle_clearance_lower_bound_m`
may contain `null` on records with no active obstacle slots. The screen still
requires finite soft and near-miss clearance hinge costs.

The analyzer is intentionally narrower than the previous route-H10 posterior
selector audit:

1. It rejects any log with non-null `candidate_closed_loop_outcomes`.
2. It reads only fixed current-tick fields: finite candidate feasibility,
   affine CAMP scores, route progress, H10 open-loop distance, and v2
   clearance hinge costs.
3. It reports what a default-off finite-candidate certificate would do, but it
   does not change selection and does not score outcomes.

Local verification:

```text
PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core
py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_no_outcome_shadow_certificate.py \
  camp_core\tests\test_diffusion_planner_route_h10_shadow_selector.py \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_are_current_tick_hinges \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_reports_obb_mode \
  -q
# 5 passed

py -3.12 -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_no_outcome_shadow_certificate.py \
  camp_core\tests\test_diffusion_planner_no_outcome_shadow_certificate.py
# passed

git diff --check
# passed
```

AutoDL CAMP was advanced to
`45bafb28c30e98f3f0c120046cd1ed0f443ae59b` using a git bundle. AutoDL DP
remained fixed at `7a1d33da277a1992ec474b5383a0c963c72e04e4`. AutoDL targeted
test result:

```text
camp_core/tests/test_diffusion_planner_no_outcome_shadow_certificate.py
# 2 passed
```

No-outcome audit command:

```bash
cd /root/autodl-tmp/camp_core

ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/obstacle_clearance_nishiseed2_832a76b_20260617_v2
OUT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_shadow_certificate_45bafb2

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_no_outcome_shadow_certificate.py \
  --root "$ROOT" \
  --label nishiseed2_v2_no_outcome \
  --output_json "$OUT/no_outcome_shadow_certificate.json" \
  --output_md "$OUT/no_outcome_shadow_certificate.md"
```

Artifact:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_shadow_certificate_45bafb2
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `no_outcome_shadow_certificate.json` | `ba4a0c7c8d885d098afa305b3d946f08bc6942286366e2d7eb987d0092fa111b` |
| `no_outcome_shadow_certificate.md` | `e93b6c4d65c945e11f440c60f349cd4d19b00a48038f6e20014561e1b086353a` |

No-outcome audit summary:

```text
records.total=140
records.candidate0_feasible=126
records.fallback=14
records.closed_loop_outcome_records=0
descriptor_coverage.candidate_route_progress_records=140
descriptor_coverage.h10_distance_records=140
descriptor_coverage.obstacle_clearance_v2_records=140
descriptor_coverage.all_required_records=140
latency_ms.shadow_obstacle_clearance.p95=2.522506
```

Screen results:

| Screen | Descriptor available | Opportunity | Shadow changes candidate0 | Shadow differs from logged | Stage counts |
| --- | ---: | ---: | ---: | ---: | --- |
| `route_h10_score0` | `126` | `26` | `26` | `120` | `candidate0_retain_empty_mask:100, fallback_retain_logged:14, shadow_candidate:26` |
| `route_h10_clearance_nonworse` | `126` | `26` | `26` | `120` | `candidate0_retain_empty_mask:100, fallback_retain_logged:14, shadow_candidate:26` |
| `route_h10_clearance_zero` | `126` | `26` | `26` | `120` | `candidate0_retain_empty_mask:100, fallback_retain_logged:14, shadow_candidate:26` |

Interpretation:

1. The no-outcome audit path is now implemented and verified. It enforces the
   intended no-leakage boundary by rejecting non-null closed-loop outcome
   labels.
2. On this single nishishinjuku NPC smoke, all required current-tick
   descriptors are present on every record, and v2 obstacle-clearance latency
   remains low.
3. The clearance guard is inactive on this artifact: all three screens produce
   identical opportunities and shadow selections. This is consistent with the
   previous v2 observation that the route-H10 near-miss steps have large
   current-tick clearance lower bounds and zero clearance hinge costs.
4. The large `shadow_differs_from_logged=120` count is not a success signal.
   It mostly reflects that this certificate is measured against the logged
   redstopfloor05 selector on a single route smoke, without posterior safety
   labels and without changing selection.

Mathematical boundary: this analyzer is a finite-candidate diagnostic only.
The screen predicates are current-tick constants over the fixed DP candidate
set. If promoted later, route progress, H10 lower-bound, and clearance hinge
terms must be represented as nonnegative fixed atoms or lexicographic guards,
leaving CAMP scoring affine in the master weights. No DP model component,
postprocessing step, PerfectTracker transition, closed-loop outcome,
SafetyCost result, or trajectory-coordinate optimization is treated as a
Benders subproblem or cut source.

Decision: accept the no-outcome analyzer and its single-artifact smoke result
as a readiness check. Reject any selector promotion from this evidence. The
next admissible step is to collect or reuse a broader no-outcome development
grid with route-progress, H10, and v2 clearance logging enabled, then run this
analyzer plus dataset audit and latency summaries before considering any
online/default-off selector implementation.

## Full36 no-outcome route/H10/clearance shadow grid

After the single-artifact no-outcome smoke, the next development gate was a
broader no-outcome shadow grid. This grid is not a posterior safety-label pass:
it is a deployability/readiness audit for the fixed current-tick candidate
descriptors that a future default-off selector would be allowed to read.

Code state:

```text
CAMP local/GitHub/AutoDL HEAD:
57cd0d1ce155bab56a87a9014a62c62bac938930

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Scope:

```text
Artifact root:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1

Routes:
sample_map_tl_route_59_to_86
sample_map_route_2_to_104
nishishinjuku_release_auto_route

Seeds:
1, 2, 3

NPC counts:
0, 4

Traffic lights:
off, on

Steps:
200

Variant:
static redstopfloor05

Selection effect:
disabled; shadow-only diagnostics

Candidate outcomes:
not collected

Shadow diagnostics:
--camp_shadow_route_progress
--camp_shadow_perfect_tracker_open_loop_rollout
--camp_shadow_full_horizon_red_light
--camp_shadow_obstacle_clearance
```

The run completed `36/36` validation summaries and `36/36` selection logs.
Local, GitHub, and AutoDL CAMP were all checked at `57cd0d1`; AutoDL DP
remained fixed at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Dataset audit:

```bash
cd /root/autodl-tmp/camp_core

ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1
OUT=$ROOT/offline_gate_audit_57cd0d1
SCALES=/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  --root "$ROOT" \
  --atom_scales "$SCALES" \
  --expected_logs 36 \
  --expected_candidates 8 \
  --expected_advance_mode perfect \
  --closed_loop_outcome_policy forbidden \
  --forbid_seed 11 \
  --forbid_seed 12 \
  --forbid_seed 13 \
  --required_candidate_field candidate_route_progress \
  --require_perfect_tracker_open_loop_rollout \
  --require_full_horizon_red_light_shadow \
  --require_finite_candidate_contract \
  --output_json "$OUT/dataset_audit_no_outcome_grid.json"
```

Dataset audit result:

```text
passed=true
logs=36
records=7200
candidates=57600
all_infeasible_records=1201
candidate_route_progress_records=7200
candidate_route_progress_candidates=57600
candidate_route_progress_records_with_variation=7200
closed_loop_outcome_policy=forbidden
closed_loop_outcome_records=0
perfect_tracker_open_loop_rollout_records=7200
full_horizon_red_light_shadow_records=7200
finite_candidate_contract_logs=36
formal seeds 11/12/13 absent
```

Candidate-availability input readiness was also run without
`--fail_on_not_ready`, because this no-outcome grid is intentionally missing
posterior labels:

```bash
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_candidate_availability_inputs.py \
  --root "$ROOT" \
  --output_json "$OUT/candidate_availability_input_readiness_no_outcome.json" \
  --output_md "$OUT/candidate_availability_input_readiness_no_outcome.md"
```

Readiness result:

```text
candidate_availability_oracle_ready=false
current_tick_proxy_inputs_ready=true
outcome_labels_ready=false
next_step=generate_or_attach_candidate_closed_loop_outcomes_before_running_oracle

field coverage:
progress_shortfall=7200/7200
proxy_jerk=7200/7200
proxy_lateral=7200/7200
red_stopping=7200/7200
union_red=7200/7200
candidate_closed_loop_outcomes_complete=0/7200
```

No-outcome shadow certificate command:

```bash
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_no_outcome_shadow_certificate.py \
  --root "$ROOT" \
  --label no_outcome_devgrid_57cd0d1 \
  --max_examples 30 \
  --output_json "$OUT/no_outcome_shadow_certificate_grid.json" \
  --output_md "$OUT/no_outcome_shadow_certificate_grid.md"
```

No-outcome certificate summary:

```text
records.total=7200
records.logs=36
records.nonfallback=5999
records.fallback=1201
records.candidate0_feasible=5768
records.closed_loop_outcome_records=0
descriptor_coverage.all_required_records=7200
descriptor_coverage.candidate_route_progress_records=7200
descriptor_coverage.h10_distance_records=7200
descriptor_coverage.obstacle_clearance_v2_records=7200
```

Screen results:

| Screen | Descriptor available | Opportunity | Shadow changes candidate0 | Shadow differs from logged | Stage counts |
| --- | ---: | ---: | ---: | ---: | --- |
| `route_h10_score0` | `5768` | `1506` | `1506` | `5328` | `candidate0_infeasible_retain_logged:231, candidate0_retain_empty_mask:4262, fallback_retain_logged:1201, shadow_candidate:1506` |
| `route_h10_clearance_nonworse` | `5768` | `1503` | `1503` | `5329` | `candidate0_infeasible_retain_logged:231, candidate0_retain_empty_mask:4265, fallback_retain_logged:1201, shadow_candidate:1503` |
| `route_h10_clearance_zero` | `5768` | `1493` | `1493` | `5333` | `candidate0_infeasible_retain_logged:231, candidate0_retain_empty_mask:4275, fallback_retain_logged:1201, shadow_candidate:1493` |

Selected-candidate delta summaries for the strictest
`route_h10_clearance_zero` screen:

```text
n=1493
route_progress_loss.mean=-0.150031
route_progress_loss.p95=-0.006720
h10_distance_loss.mean=-0.043629
h10_distance_loss.p95=0.036639
score_delta.mean=-0.040774
score_delta.p95=-0.004062
progress_delta.mean=-0.148231
progress_delta.p95=-0.005296
proxy_jerk_delta.mean=0.0
proxy_lateral_delta.mean=-0.005471
soft_clearance_cost.max=0.0
near_miss_clearance_cost.max=0.0
```

Latency summary was generated as a read-only artifact over the same 36 logs.
This is the decisive deployability failure in this round:

```text
logs=36
records=7200
runs_over_100ms_including_candidate_generation_p95=15

overall latency_ms_including_candidate_generation:
mean=94.935122
p50=89.570196
p95=118.412714
max=317.124351

overall latency_ms_candidate_generation:
mean=56.591838
p95=60.368221
max=84.938101

overall latency_ms_camp_selection:
mean=5.950883
p95=6.812007
max=190.699888

overall latency_ms_shadow_obstacle_clearance:
mean=3.453839
p50=0.073134
p95=18.306384
max=116.254320

overall latency_ms_shadow_perfect_tracker_open_loop:
mean=1.039569
p95=1.076344
max=6.668014
```

Per-route latency:

| Route group | Logs | Records | Runs with p95 > 100 ms | Mean run p95 including generation | Max run p95 including generation | Max clearance run p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `nishishinjuku` | `12` | `2400` | `3` | `98.679664` | `127.487494` | `29.724396` |
| `sample_map` | `24` | `4800` | `12` | `111.409586` | `204.791084` | `98.279118` |

Worst run:

```text
sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static/camp_validation_summary.json
including_candidate_generation.p95=204.791084 ms
shadow_obstacle_clearance.p95=98.279118 ms
camp_selection.p95=9.787354 ms
shadow_perfect_tracker_open_loop.p95=1.042030 ms
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `dataset_audit_no_outcome_grid.json` | `4cc70abf37ca7906ea9a93b6a99b8fd32d99eb2f5b0eeda5a8554e646bbe2b34` |
| `no_outcome_shadow_certificate_grid.json` | `1586567a9c08c2a52a768cb4270ce4480eeb59f32a24c51cf27cd851270c61a8` |
| `no_outcome_shadow_certificate_grid.md` | `a7980d97309c968ce62ebce9b326e9cf1e1260ec6216809b2c35c845aa361fc3` |
| `candidate_availability_input_readiness_no_outcome.json` | `91dd7c219a157580c69d51ba3170d0bc41d9e69c4876d24baad7ffece93e8288` |
| `candidate_availability_input_readiness_no_outcome.md` | `2fd06787876eae6f5a63f98ba0ce674fcf65eb7212b7cdfc5c7a6f06a545941d` |
| `latency_summary_no_outcome_grid.json` | `d2535d6e69e571de4de5a4837a363143ace6e528cb493ef905d7128f500ca367` |
| `latency_summary_no_outcome_grid.md` | `728e73d5b9f00a892e362fa86d0e2c4f72be74a1d040c6d7ed084e22a0c593df` |

Interpretation:

1. The no-outcome input contract is strong enough for diagnostic work:
   route-progress, H10 open-loop rollout, full-horizon red-light shadow, v2
   clearance descriptors, finite-candidate metadata, and existing CAMP proxy
   atoms are all present without closed-loop outcome leakage.
2. This artifact cannot support hidden-visibility or bucketed hard-gate
   posterior claims, because it intentionally contains no
   `candidate_closed_loop_outcomes`. The earlier Full36 outcome-labeled pass
   remains the posterior hard-gate evidence, and it already rejected the
   route-H10 selector because of two near-miss regressions.
3. The strict no-outcome route/H10/clearance screen has many shadow
   opportunities (`1493`), but those are not success claims. They only say that
   current-tick descriptor masks are nonempty and deterministic over the fixed
   candidate set. Without posterior labels, they cannot prove lower safety
   score.
4. The deployment latency gate fails. Overall p95 including DP candidate
   generation is `118.413 ms`, and `15/36` runs exceed the 100 ms p95 target.
   The largest regression is concentrated in sample-map NPC runs where the v2
   obstacle-clearance shadow still reaches high p95 and max latency despite the
   bounding-circle optimization.

Mathematical boundary: all logged no-outcome quantities are fixed
finite-candidate diagnostics at the current tick. If route-progress, H10
distance, and obstacle-clearance terms are later atomized, they must be
nonnegative fixed transforms or deterministic finite-candidate guards, leaving
the CAMP score affine in master weights and the simplex/CVaR/L2 master convex.
No DP sampler, Savitzky-Golay smoothing, `postprocess_reference`,
PerfectTracker transition, closed-loop future outcome, SafetyCost result, or
trajectory-coordinate optimization is treated as a Benders subproblem or cut
source.

Decision: accept the Full36 no-outcome grid as an input-contract and
no-leakage audit. Reject online/default-off selector promotion from this
round. The immediate blocker is deployability latency, not descriptor coverage:
before another replay matrix or selector implementation, the
obstacle-clearance descriptor needs another latency-focused diagnostic or a
cheaper state-conditioned guard. Do not train new CAMP weights, do not run
formal seeds, and do not run a new 12/36 online selector matrix from this
evidence.

### Exact-OBB diagnostic default-off smoke

The Full36 no-outcome latency failure was traced to near-threshold exact OBB
distance diagnostics inside `candidate_obstacle_clearance`. The online-eligible
clearance atoms and no-outcome screens use the conservative bounding-circle
lower bound and hinge costs; exact OBB distance was only a diagnostic payload.
Commit `b3dcbc19a4e9e4636c674828d50fae430c077c7d` therefore made exact OBB
diagnostics explicitly optional and default-off for replay/matrix commands:

```text
compute_candidate_obstacle_clearance_diagnostics(..., evaluate_exact_obb=True)
  remains available for direct debug/tests.

run_diffusion_planner_camp_replay.py
  default: lower-bound-only obstacle-clearance shadow
  debug: --camp_shadow_obstacle_clearance_exact_obb

run_diffusion_planner_camp_benchmark_matrix.py
  forwards --camp_shadow_obstacle_clearance_exact_obb only when explicitly set.
```

Local verification:

```text
PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core
py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_are_current_tick_hinges \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_reports_obb_mode \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_can_skip_exact_obb \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py::test_variant_command_threads_fallback_mode_into_camp_variants \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py::test_variant_command_forwards_exact_obb_debug_flag_only_when_requested \
  -q
# 5 passed

py -3.12 -m compileall -q \
  camp_core\camp_core\integrations\diffusion_planner.py \
  scripts\integrations\run_diffusion_planner_camp_replay.py \
  scripts\integrations\run_diffusion_planner_camp_benchmark_matrix.py \
  camp_core\tests\test_diffusion_planner_integration.py \
  camp_core\tests\test_diffusion_planner_benchmark_matrix.py
# passed

git diff --check
# passed
```

AutoDL was synchronized to `b3dcbc19a4e9e4636c674828d50fae430c077c7d` with a
git bundle. DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. AutoDL targeted verification:

```text
camp_core/tests/test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_are_current_tick_hinges
camp_core/tests/test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_reports_obb_mode
camp_core/tests/test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_can_skip_exact_obb
camp_core/tests/test_diffusion_planner_benchmark_matrix.py::test_variant_command_threads_fallback_mode_into_camp_variants
camp_core/tests/test_diffusion_planner_benchmark_matrix.py::test_variant_command_forwards_exact_obb_debug_flag_only_when_requested
# 5 passed
```

Latency smoke command:

```bash
cd /root/autodl-tmp/camp_core

OUT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_exact_obb_off_b3dcbc1_sample_tl_seed1_npc4_tloff_static

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
REPLAY_NO_PNG=1 \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --map_path /root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm \
  --route /root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --model_path /root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --config /root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json \
  --output_dir "$OUT" \
  --device cuda \
  --advance_mode perfect \
  --steps 200 \
  --seed 1 \
  --max_npcs 4 \
  --spawn_probability 0.3 \
  --traffic_lights off \
  --reward_config /root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json \
  --camp_selector_mode static \
  --camp_atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --camp_static_weights /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/offline_weights_dp_static.npy \
  --num_candidates 8 \
  --candidate_noise_scale 1.0 \
  --candidate_reference_blend_steps 5 \
  --camp_lane_corridor_buffer 1.0 \
  --camp_feasibility_source dp_reward \
  --camp_fallback_mode learned \
  --camp_min_progress_ratio 0.8 \
  --camp_shadow_route_progress \
  --camp_shadow_obstacle_clearance \
  --camp_reward_horizon_steps 30 \
  --camp_outcome_horizon_steps 30 \
  --near_miss_threshold_m 2.0
```

Smoke audit commands:

```bash
ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_exact_obb_off_b3dcbc1_sample_tl_seed1_npc4_tloff_static
OUT=$ROOT/audit_b3dcbc1
SCALES=/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  --selection_log "$ROOT/camp_selection_log.json" \
  --atom_scales "$SCALES" \
  --expected_logs 1 \
  --expected_candidates 8 \
  --expected_advance_mode perfect \
  --closed_loop_outcome_policy forbidden \
  --forbid_seed 11 \
  --forbid_seed 12 \
  --forbid_seed 13 \
  --required_candidate_field candidate_route_progress \
  --require_perfect_tracker_open_loop_rollout \
  --require_full_horizon_red_light_shadow \
  --require_finite_candidate_contract \
  --output_json "$OUT/dataset_audit_no_outcome_exact_obb_off.json"

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_no_outcome_shadow_certificate.py \
  --selection_log "$ROOT/camp_selection_log.json" \
  --label no_outcome_exact_obb_off_b3dcbc1_sample_tl_seed1_npc4_tloff_static \
  --output_json "$OUT/no_outcome_shadow_certificate_exact_obb_off.json" \
  --output_md "$OUT/no_outcome_shadow_certificate_exact_obb_off.md"
```

Smoke result:

```text
records=200
closed_loop_outcome_records=0
candidate_route_progress_records=200
h10_distance_records=200
obstacle_clearance_v2_records=200
perfect_tracker_open_loop_rollout_records=200
full_horizon_red_light_shadow_records=200
finite_candidate_contract_logs=1

exact_obb_enabled=false
exact_evaluated_pairs.p95=0
exact_evaluated_pairs.max=0
obstacle_slots.mean=2.2
obstacle_slots.max=4

latency_ms_shadow_obstacle_clearance:
mean=5.148374
p50=4.690808
p95=9.296867
max=9.540996

latency_ms_including_candidate_generation:
mean=102.801354
p50=100.980750
p95=109.424894
max=311.714364
```

Comparison to the previous exact-on worst Full36 run:

| Run | Clearance p95 | Clearance max | Exact-pair p95 | Total p95 |
| --- | ---: | ---: | ---: | ---: |
| exact-on v2 Full36 worst run | `98.279118 ms` | `116.254320 ms` | `45` | `204.791084 ms` |
| exact-off smoke | `9.296867 ms` | `9.540996 ms` | `0` | `109.424894 ms` |

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `d1ba39591d701104e2361665e40bf3fbbfec573de67f6b9a24c43c8360485b14` |
| `camp_validation_summary.json` | `4bdfe40eaf6a934bdba502cdbad856a0259e87abb8971abbfc88d657c4b728e8` |
| `camp_replay_summary.json` | `ea353db03cd3dfe8b4b6ec2265a22060f4ee051369990b3b6acfe925e632300c` |
| `dataset_audit_no_outcome_exact_obb_off.json` | `75920b249ac5b99f5c13a027eac56b916ecee78ea95c3c285b9cd0d7f1ca07b0` |
| `no_outcome_shadow_certificate_exact_obb_off.json` | `b0440af5c0352122360762dd8b0113828bbd5f2ee051970821eaa685123d5bf8` |
| `no_outcome_shadow_certificate_exact_obb_off.md` | `f467dcf3d4bde550e33c2e7fbdf2024a5d4122b77e6127af584101140ccea139` |

Interpretation:

1. The exact-OBB default-off change is accepted as a deployability improvement.
   It removes a diagnostic-only cost path while preserving the current-tick
   lower-bound hinge atoms that would be admissible in a finite-candidate CAMP
   selector.
2. This is still not enough to pass the development gate. The representative
   worst-case smoke still has `latency_ms_including_candidate_generation.p95`
   above `100 ms`, with reward scoring and the remaining CAMP path now forming
   the visible latency floor.
3. The old exact-on Full36 artifact and the new smoke are not treated as a
   paired behavioral comparison. DP candidate sampling is not being used here
   as a deterministic equivalence oracle. The selection-invariance claim comes
   from code structure and unit tests: exact OBB affects only diagnostic exact
   fields, while lower-bound clearance and hinge costs are unchanged.

Mathematical boundary: disabling exact OBB does not weaken the CAMP/Benders-style
contract because exact OBB was never an online atom, selector input, oracle
label, subproblem result, or cut source. The admissible obstacle feature remains
a fixed current-tick nonnegative lower-bound hinge over a finite DP candidate
set. CAMP scores remain affine in weights; no trajectory-coordinate convexity
or classical Benders claim is introduced.

Decision: keep the exact-OBB default-off implementation. Reject online selector
promotion and reject new 12/36-run replay matrices from this smoke because the
overall latency p95 is still above the industrial target. The next admissible
step is a latency-focused attribution of the remaining `~109 ms` p95 floor,
especially reward scoring, candidate generation, and residual CAMP selection
components, before any broader rerun.

### Latency budget attribution after exact-OBB default-off

Commit `61d700345a5b9a4f8d9904ea5035bf7d6f14b45e` added a read-only latency
budget analyzer:

```text
scripts/integrations/analyze_diffusion_planner_latency_budget.py
camp_core/tests/test_diffusion_planner_latency_budget.py
```

The analyzer reads existing `camp_selection_log.json` files or an artifact
root, uses no closed-loop outcome labels, changes no selector, and trains no
weights. Its purpose is latency attribution only.

Verification at implementation time:

```text
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_latency_budget.py -q
# 1 passed

py -3.12 -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_latency_budget.py \
  camp_core\tests\test_diffusion_planner_latency_budget.py
# passed

git diff --check
# passed
```

AutoDL was synchronized to
`61d700345a5b9a4f8d9904ea5035bf7d6f14b45e`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. AutoDL targeted verification:

```text
camp_core/tests/test_diffusion_planner_latency_budget.py
# 1 passed
```

Analyzer commands:

```bash
cd /root/autodl-tmp/camp_core

SMOKE=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_exact_obb_off_b3dcbc1_sample_tl_seed1_npc4_tloff_static
SMOKE_OUT=$SMOKE/latency_budget_61d7003

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_latency_budget.py \
  --selection_log "$SMOKE/camp_selection_log.json" \
  --label no_outcome_exact_obb_off_b3dcbc1_sample_tl_seed1_npc4_tloff_static \
  --output_json "$SMOKE_OUT/latency_budget.json" \
  --output_md "$SMOKE_OUT/latency_budget.md"

GRID=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1
GRID_OUT=$GRID/offline_gate_audit_57cd0d1/latency_budget_61d7003

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_latency_budget.py \
  --root "$GRID" \
  --label no_outcome_full36_route_h10_clearance_57cd0d1 \
  --output_json "$GRID_OUT/latency_budget.json" \
  --output_md "$GRID_OUT/latency_budget.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `no_outcome_exact_obb_off.../latency_budget_61d7003/latency_budget.json` | `39d6a54b3941cf70a35cfa703697e5acbc57385e31df6b68375331980fa381de` |
| `no_outcome_exact_obb_off.../latency_budget_61d7003/latency_budget.md` | `b8f7292d1c31152ece7e11d01a6920b45b680a64e4d3833862b8a1d9da07175d` |
| `no_outcome_devgrid_57cd0d1/.../latency_budget_61d7003/latency_budget.json` | `27be782c894103c925eef9d3f6f3597b54e0d45a7e464edd85da6924a6bb30fa` |
| `no_outcome_devgrid_57cd0d1/.../latency_budget_61d7003/latency_budget.md` | `2bbe831909c1e7312de470b89c6a7a2b34cd62587e9bc26efc21d9313e9e9ca9` |

Exact-OBB-off smoke latency summary:

| Quantity | Mean | p95 | Max |
| --- | ---: | ---: | ---: |
| total including candidate generation | `102.801354 ms` | `109.424894 ms` | `311.714364 ms` |
| candidate generation | `57.589893 ms` | `58.762836 ms` | `83.103469 ms` |
| reward scoring | `28.775702 ms` | `30.120930 ms` | `205.798348 ms` |
| CAMP selection | `7.163944 ms` | `8.915116 ms` | `213.910233 ms` |
| obstacle clearance shadow | `5.148374 ms` | `9.296867 ms` | `9.540996 ms` |
| H10 open-loop shadow | `1.034807 ms` | `1.047682 ms` | `1.211481 ms` |
| context and obstacles | `1.326262 ms` | `1.455620 ms` | `2.011809 ms` |
| critical-path sum | `102.749035 ms` | `109.375071 ms` | `311.665178 ms` |
| non-candidate-generation remainder | `45.211461 ms` | `51.772334 ms` | `254.679419 ms` |
| uninstrumented residual | `0.052318 ms` | `0.062334 ms` | `0.182581 ms` |

Exact-OBB-off smoke removal sensitivity:

| Removed component | Remaining total p95 | p95 reduction |
| --- | ---: | ---: |
| candidate generation | `51.772334 ms` | `57.652560 ms` |
| reward scoring | `79.673602 ms` | `29.751292 ms` |
| CAMP selection | `100.594106 ms` | `8.830788 ms` |
| obstacle clearance shadow | `100.384059 ms` | `9.040835 ms` |

Full36 no-outcome grid latency summary:

| Quantity | Mean | p95 | Max |
| --- | ---: | ---: | ---: |
| total including candidate generation | `94.935122 ms` | `118.412714 ms` | `317.124351 ms` |
| candidate generation | `56.591838 ms` | `60.368221 ms` | `84.938101 ms` |
| reward scoring | `25.366729 ms` | `29.072235 ms` | `221.673478 ms` |
| CAMP selection | `5.950883 ms` | `6.812007 ms` | `190.699888 ms` |
| obstacle clearance shadow | `3.453839 ms` | `18.306384 ms` | `116.254320 ms` |
| H10 open-loop shadow | `1.039569 ms` | `1.076344 ms` | `6.668014 ms` |
| context and obstacles | `0.752216 ms` | `1.299788 ms` | `6.252378 ms` |
| critical-path sum | `94.899724 ms` | `118.379148 ms` | `317.075895 ms` |
| non-candidate-generation remainder | `38.343285 ms` | `60.289992 ms` | `260.485682 ms` |
| uninstrumented residual | `0.035398 ms` | `0.047099 ms` | `0.628720 ms` |

Full36 no-outcome grid removal sensitivity:

| Removed component | Remaining total p95 | p95 reduction |
| --- | ---: | ---: |
| candidate generation | `60.289992 ms` | `58.122722 ms` |
| reward scoring | `87.849056 ms` | `30.563658 ms` |
| CAMP selection | `107.953065 ms` | `10.459649 ms` |
| obstacle clearance shadow | `97.200250 ms` | `21.212464 ms` |

Top-tail notes:

1. The instrumented critical path almost exactly explains total latency:
   uninstrumented residual p95 is `0.062334 ms` on the smoke and `0.047099 ms`
   on the Full36 grid.
2. Candidate generation consumes about `58-60 ms` p95. This is the fixed DP
   black-box generator cost and is outside the permitted CAMP optimization
   boundary.
3. Reward scoring is the largest legal CAMP-side p95 lever, around `29-31 ms`.
   It currently supplies `dp_reward` feasibility, progress, planned red-light,
   full/union red-light, and related current-tick diagnostic quantities. It
   cannot be removed unless those fixed finite-candidate fields or guards are
   replaced with a mathematically admissible equivalent.
4. CAMP selection p95 is much smaller than reward scoring, but rare max spikes
   exist. The worst smoke record is step `147`, with total `311.714364 ms`,
   CAMP selection `213.910233 ms`, and atom computation `210.768191 ms`. This
   is a max-latency investigation target, not the current p95 floor.
5. The Full36 grid still fails the industrial latency gate:
   `latency_ms_including_candidate_generation.p95 = 118.412714 ms`.

Mathematical boundary: this analyzer does not alter the finite candidate set,
DP outputs, atoms, weights, master problem, or selector. It reads only logged
current-tick latency fields and does not use outcome labels. Therefore it makes
no new Benders, convexity, subproblem, or cut claim. Any future reward-scoring
replacement must preserve the accepted CAMP contract: finite DP candidates,
fixed current-tick nonnegative atom values, no future leakage, affine score in
weights, and convex simplex/CVaR/L2 master behavior.

Decision: accept the latency-budget analyzer and these attribution artifacts.
Reject online selector promotion, new CAMP weight training, new 12/36 online
matrices, and formal seeds from this evidence. The next admissible engineering
step is a reward-scoring decomposition and replacement design that preserves
the current finite-candidate CAMP math contract before any broader online
experiment.

### Reward-scoring latency decomposition instrumentation and smoke

Commit `fdc818085486fc664522b312c0c02f70d24d27c6` adds reward-scoring latency
subfields without changing DP, candidate generation, atoms, weights, feasibility
semantics, or selection. The replay log now decomposes the existing
`latency_ms_reward_scoring` bucket into:

```text
latency_ms_reward_npz_dump
latency_ms_reward_tensor_setup
latency_ms_reward_sg_smoothing
latency_ms_reward_candidate_tensor_transfer
latency_ms_reward_batch_compute
latency_ms_reward_postprocess
latency_ms_reward_full_horizon_red_light
latency_ms_reward_red_route_points
latency_ms_reward_feasibility
latency_ms_reward_field_extraction
latency_ms_reward_step_reach_guard
latency_ms_reward_route_progress
latency_ms_reward_route_progress_guard
latency_ms_reward_lexicographic_filter
```

`analyze_diffusion_planner_latency_budget.py` now treats these as nested
diagnostic fields and reports `reward_breakdown_sum` plus
`reward_unattributed_residual`.

Local verification:

```text
PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core
py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_latency_budget.py \
  camp_core\tests\test_diffusion_planner_integration.py::test_summarize_selection_records_reports_candidate_usage \
  camp_core\tests\test_diffusion_planner_integration.py::test_dp_reward_feasibility_applies_candidate0_progress_guard \
  -q
# 3 passed

py -3.12 -m compileall -q \
  scripts\integrations\run_diffusion_planner_camp_replay.py \
  scripts\integrations\analyze_diffusion_planner_latency_budget.py \
  camp_core\camp_core\integrations\diffusion_planner.py \
  camp_core\tests\test_diffusion_planner_latency_budget.py \
  camp_core\tests\test_diffusion_planner_integration.py
# passed

git diff --check
# passed
```

AutoDL was synchronized to
`fdc818085486fc664522b312c0c02f70d24d27c6`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. AutoDL targeted verification used
the same pytest selection plus compileall and `git diff --check`; all passed.

No-outcome reward-latency diagnostic smoke:

```bash
cd /root/autodl-tmp/camp_core

OUT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/reward_latency_decomp_fdc8180_sample_tl_seed1_npc4_tloff_static

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
REPLAY_NO_PNG=1 \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --map_path /root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm \
  --route /root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --model_path /root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --config /root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json \
  --output_dir "$OUT" \
  --device cuda \
  --advance_mode perfect \
  --steps 200 \
  --seed 1 \
  --max_npcs 4 \
  --spawn_probability 0.3 \
  --traffic_lights off \
  --reward_config /root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json \
  --camp_selector_mode static \
  --camp_atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --camp_static_weights /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/offline_weights_dp_static.npy \
  --num_candidates 8 \
  --candidate_noise_scale 1.0 \
  --candidate_reference_blend_steps 5 \
  --camp_lane_corridor_buffer 1.0 \
  --camp_feasibility_source dp_reward \
  --camp_fallback_mode learned \
  --camp_min_progress_ratio 0.8 \
  --camp_shadow_route_progress \
  --camp_shadow_obstacle_clearance \
  --camp_reward_horizon_steps 30 \
  --camp_outcome_horizon_steps 30 \
  --near_miss_threshold_m 2.0
```

Audit commands:

```bash
AUDIT=$OUT/audit_fdc8180
SCALES=/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  --selection_log "$OUT/camp_selection_log.json" \
  --atom_scales "$SCALES" \
  --expected_logs 1 \
  --expected_candidates 8 \
  --expected_advance_mode perfect \
  --closed_loop_outcome_policy forbidden \
  --forbid_seed 11 \
  --forbid_seed 12 \
  --forbid_seed 13 \
  --required_candidate_field candidate_route_progress \
  --require_perfect_tracker_open_loop_rollout \
  --require_full_horizon_red_light_shadow \
  --require_finite_candidate_contract \
  --output_json "$AUDIT/dataset_audit_reward_latency_decomp.json"

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_latency_budget.py \
  --selection_log "$OUT/camp_selection_log.json" \
  --label reward_latency_decomp_fdc8180_sample_tl_seed1_npc4_tloff_static \
  --output_json "$AUDIT/latency_budget_reward_decomp.json" \
  --output_md "$AUDIT/latency_budget_reward_decomp.md"
```

Dataset audit passed with `1` log and `200` records. It forbids closed-loop
outcome labels, confirms `candidate_route_progress`, requires the finite
candidate contract, and forbids formal seeds `11/12/13`.

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `aecbd4aa31de41e3e09e448199e7735a55a6216a310cca1e264809ba343e0de2` |
| `camp_validation_summary.json` | `e7a3c5e6d76107a12ecf7bd62670112554bbf4829e8d84be66bcf72ba5b7890f` |
| `camp_replay_summary.json` | `ced362088a14079a8078757a786c2d21af57cb9f893af1f63900448650a45d01` |
| `dataset_audit_reward_latency_decomp.json` | `384d275c10f317fb7647a477c7d9290d210dc6ec4c275912501cd701473c97a0` |
| `latency_budget_reward_decomp.json` | `a08ad7e5b279a47553523b74e23f82be86093224251262609cb5fa5adb1ce155` |
| `latency_budget_reward_decomp.md` | `839b416f9fec51c5628f2535ab33699c9de66d14a3a0b7db22ac5cb3fea4e06f` |

Reward-latency smoke summary:

| Quantity | Mean | p95 | Max |
| --- | ---: | ---: | ---: |
| total including candidate generation | `101.706329 ms` | `108.367819 ms` | `297.693390 ms` |
| candidate generation | `57.337520 ms` | `57.854581 ms` | `60.801134 ms` |
| reward scoring | `28.215771 ms` | `29.322685 ms` | `209.042622 ms` |
| reward npz dump | `2.005146 ms` | `2.126100 ms` | `2.390109 ms` |
| reward tensor setup | `0.378060 ms` | `0.394133 ms` | `0.522806 ms` |
| reward SG smoothing | `5.274101 ms` | `5.342995 ms` | `5.597378 ms` |
| reward candidate tensor transfer | `0.078521 ms` | `0.083757 ms` | `0.093444 ms` |
| reward batch compute | `13.350961 ms` | `14.430136 ms` | `193.751646 ms` |
| reward postprocess | `0.054450 ms` | `0.058395 ms` | `0.076419 ms` |
| reward full-horizon red light | `0.114524 ms` | `0.127154 ms` | `0.132134 ms` |
| reward red route points | `0.055318 ms` | `0.064109 ms` | `0.219128 ms` |
| reward feasibility | `0.065681 ms` | `0.079747 ms` | `0.467242 ms` |
| reward field extraction | `0.007584 ms` | `0.009026 ms` | `0.009343 ms` |
| reward route progress | `6.779380 ms` | `6.867220 ms` | `9.122293 ms` |
| obstacle clearance shadow | `5.130386 ms` | `9.300296 ms` | `10.588693 ms` |
| CAMP selection | `7.003787 ms` | `8.644735 ms` | `200.422055 ms` |
| reward breakdown sum | `28.163724 ms` | `29.273057 ms` | `208.987467 ms` |
| reward unattributed residual | `0.052046 ms` | `0.059128 ms` | `0.150087 ms` |

Removal sensitivity:

| Removed component | Remaining total p95 | p95 reduction |
| --- | ---: | ---: |
| candidate generation | `51.149401 ms` | `57.218418 ms` |
| reward scoring | `79.238951 ms` | `29.128868 ms` |
| CAMP selection | `99.952558 ms` | `8.415261 ms` |
| obstacle clearance shadow | `98.988998 ms` | `9.378820 ms` |

Interpretation:

1. The new reward subfields explain the reward bucket: the unattributed reward
   residual p95 is only `0.059128 ms`.
2. `compute_reward_batch` is the largest reward-internal p95 component
   (`14.430136 ms`) and also creates the largest max spike
   (`193.751646 ms`). This is the first reward-side target to understand.
3. Route-progress projection (`6.867220 ms` p95) and SG smoothing
   (`5.342995 ms` p95) are the next largest stable reward-side components.
   These are current-tick diagnostics, but any optimization must preserve the
   fixed finite-candidate values used by the audit.
4. Full-horizon red-light scoring is not the reward bottleneck in this smoke
   (`0.127154 ms` p95). Removing or weakening red-light diagnostics would be
   mathematically and empirically unjustified from this evidence.
5. The total p95 remains above `100 ms`; this smoke does not pass the
   industrial latency gate and is not a selector promotion result.

Mathematical boundary: these added latency fields are timing diagnostics only.
They are not atoms, weights, constraints, oracle labels, subproblem outputs, or
cuts. They read only current-tick computation durations and do not enter CAMP
scores. The finite candidate set, nonnegative fixed atoms, affine score in
weights, and simplex/CVaR/L2 master assumptions remain unchanged.

Decision: accept the reward-latency decomposition instrumentation and this
single no-outcome smoke as a diagnostic milestone. Reject online selector
promotion, new CAMP weights, broader 12/36 online matrices, and formal seeds.
The next admissible step is to design and audit a reward-cost replacement or
cache plan that targets `compute_reward_batch`, route-progress projection, and
SG smoothing while proving that every replacement feature remains current-tick,
finite-candidate, nonnegative, and score-affine.

### Reward replacement/cache feasibility audit

Commit `f18294af2ae3994bdc82c0734f736d3d09d9de0a` adds a read-only reward
replacement/cache feasibility analyzer:

```text
scripts/integrations/analyze_diffusion_planner_reward_replacement_plan.py
camp_core/tests/test_diffusion_planner_reward_replacement_plan.py
```

The analyzer does not change replay, selector behavior, DP, weights, atoms, or
training. It reconstructs the DP reward hard mask from logged
`dp_candidate_rewards`, compares candidate replacement masks against that DP
reward baseline, and estimates p95 latency changes from already logged timing
fields. It explicitly treats the estimates as engineering diagnostics, not as
semantic proof that a replacement is valid.

Local verification:

```text
PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core
py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_reward_replacement_plan.py \
  camp_core\tests\test_diffusion_planner_latency_budget.py \
  -q
# 2 passed

py -3.12 -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_reward_replacement_plan.py \
  camp_core\tests\test_diffusion_planner_reward_replacement_plan.py
# passed

git diff --check
# passed
```

AutoDL was synchronized to
`f18294af2ae3994bdc82c0734f736d3d09d9de0a`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. AutoDL targeted verification used
the same pytest selection plus compileall and `git diff --check`; all passed.

Analyzer command on the reward-latency smoke:

```bash
cd /root/autodl-tmp/camp_core

ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/reward_latency_decomp_fdc8180_sample_tl_seed1_npc4_tloff_static
OUT=$ROOT/audit_f18294a

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_reward_replacement_plan.py \
  --selection_log "$ROOT/camp_selection_log.json" \
  --label reward_latency_decomp_fdc8180_sample_tl_seed1_npc4_tloff_static \
  --output_json "$OUT/reward_replacement_plan.json" \
  --output_md "$OUT/reward_replacement_plan.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `reward_replacement_plan.json` | `942125143f267b5aa17b17111323cfbe7f2f9aa19d511a720b0981e32c8acd9d` |
| `reward_replacement_plan.md` | `c67a358ef134af06d55d9c10f6ea9ab76b5ce3a808c1d2c37b58713858a088e2` |

Records:

```text
logs=1
records=200
candidate_total=1600
nonfallback_records=130
fallback_records=70
```

Mask-plan result against the reconstructed DP reward baseline:

| Plan | Candidate mismatches | False feasible | False infeasible | Missing | Selected changes |
| --- | ---: | ---: | ---: | ---: | ---: |
| `route_progress_underprogress` | `181` | `181` | `0` | `0` | `7` |
| `full_red_hard_dp_progress` | `0` | `0` | `0` | `0` | `0` |
| `full_red_route_progress` | `181` | `181` | `0` | `0` | `7` |
| `union_red_route_progress_diagnostic` | `181` | `181` | `0` | `0` | `7` |

Latency-plan estimates on the same smoke:

| Hypothetical plan | Total p95 if removed | p95 reduction |
| --- | ---: | ---: |
| `remove_reward_batch_compute` | `94.131586 ms` | `14.236233 ms` |
| `cache_route_progress` | `101.676118 ms` | `6.691701 ms` |
| `reuse_sg_smoothed_candidates` | `103.105914 ms` | `5.261905 ms` |
| `batch_plus_route_progress` | `87.386639 ms` | `20.981180 ms` |
| `batch_plus_route_progress_plus_sg` | `82.132086 ms` | `26.235732 ms` |

Alignment diagnostics:

```text
route_minus_dp_progress_m:
mean=33.576028
p50=32.520088
p95=63.714044
min=-0.512302
max=64.164060
n=1600

full_minus_near_red_cost:
mean=0.0
p95=0.0
min=0.0
max=0.0
n=1600
```

Interpretation:

1. Directly replacing DP reward progress with `candidate_route_progress` is
   rejected. It creates `181` false-feasible candidates relative to the DP
   reward baseline and changes selected-candidate mask status in `7` records.
   The large positive `route_minus_dp_progress_m` distribution shows that the
   two progress quantities are not interchangeable without a calibrated mapping
   or different guard definition.
2. Replacing near-horizon DP reward red with full-horizon red is mask-equivalent
   on this smoke (`0` mismatches), but it is not a meaningful latency lever:
   full-horizon red was already only `0.127154 ms` p95 in the previous smoke.
   This supports keeping red diagnostics, not weakening them.
3. The latency estimates show why the bottleneck remains tempting:
   eliminating `compute_reward_batch`, route-progress projection, and SG
   smoothing together would put the smoke p95 near `82.132086 ms`. However, the
   mask audit proves the current progress replacement is semantically unsafe,
   so the estimate is not an acceptance result.
4. Non-red DP hard gates still come from `dp_candidate_rewards`
   (`dp_collision`, `dp_road_border`, `dp_lane_crossing`,
   `dp_static_collision`, `dp_kinematic`). This analyzer does not prove they
   can be removed; any future cache/replacement must account for each hard gate
   separately.

Mathematical boundary: every compared quantity is a fixed current-tick
finite-candidate diagnostic already logged in the artifact. The analyzer uses
no closed-loop outcome labels, changes no candidate set, and does not feed its
results into CAMP scoring. A future replacement can be considered compatible
with the CAMP contract only if it preserves fixed finite candidates,
nonnegative atom/proxy values, no future leakage, affine score in weights, and
convex simplex/CVaR/L2 master behavior. No classical Benders claim is made.

Decision: accept the reward replacement/cache audit tool and this single-smoke
result as a diagnostic milestone. Reject direct reward replacement, reject
route-progress-as-DP-progress, reject online selector promotion, reject new
CAMP weights, reject broader 12/36 online matrices, and keep formal seeds
frozen. The next admissible step is a progress mapping/guard audit: either
calibrate a current-tick route-progress-to-DP-progress relation with strict
false-feasible control, or design a separate finite-candidate progress guard
that does not pretend to reproduce DP reward progress.

### Progress mapping/guard audit

Commit `b0622528c3a15016b213d1df6421aed11559bddd` adds a read-only
progress mapping/guard analyzer:

```text
scripts/integrations/analyze_diffusion_planner_progress_mapping_guard.py
camp_core/tests/test_diffusion_planner_progress_mapping_guard.py
```

The analyzer compares current-tick `candidate_route_progress` guards against
the reconstructed DP reward underprogress baseline. It does not change replay,
selection, DP, weights, atoms, or training. It uses no closed-loop outcome
labels. The hard gates remain the logged DP reward gates
(`dp_collision`, `dp_road_border`, `dp_lane_crossing`,
`dp_static_collision`, `dp_kinematic`, `dp_red_light`); only the progress guard
is varied in a predeclared diagnostic grid.

Local verification:

```text
PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core
py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_progress_mapping_guard.py \
  camp_core\tests\test_diffusion_planner_reward_replacement_plan.py \
  -q
# 2 passed

py -3.12 -m compileall -q \
  scripts\integrations\analyze_diffusion_planner_progress_mapping_guard.py \
  camp_core\tests\test_diffusion_planner_progress_mapping_guard.py
# passed

git diff --check
# passed
```

AutoDL was synchronized to
`b0622528c3a15016b213d1df6421aed11559bddd`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. AutoDL targeted verification used
the same pytest selection plus compileall and `git diff --check`; all passed.
The remote could not fetch GitHub directly, so synchronization used a local
Git bundle and fast-forward merge from `/tmp/camp_sync_b062252.bundle`.

Analyzer command on the reward-latency smoke:

```bash
cd /root/autodl-tmp/camp_core

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_progress_mapping_guard.py \
  --selection_log /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/reward_latency_decomp_fdc8180_sample_tl_seed1_npc4_tloff_static/camp_selection_log.json \
  --label reward_latency_decomp_fdc8180_sample_tl_seed1_npc4_tloff_static \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/reward_latency_decomp_fdc8180_sample_tl_seed1_npc4_tloff_static/audit_b062252_progress_guard/progress_mapping_guard.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/reward_latency_decomp_fdc8180_sample_tl_seed1_npc4_tloff_static/audit_b062252_progress_guard/progress_mapping_guard.md
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `progress_mapping_guard.json` | `9a6df7226bf72ba76c044b125b2dc8b6462751b2a166edacd97323bc2f136803` |
| `progress_mapping_guard.md` | `02f09895e5dcd844e1a41539e21e1765bf0c1e196a72bfa835907bb4ed4f5552` |

Records:

```text
logs=1
records=200
candidate_total=1600
records_with_route_progress=200
nonfallback_records_by_dp_reward=156
fallback_records_by_dp_reward=44
```

Representative guard results against the reconstructed DP reward baseline:

| Guard | False feasible | False infeasible | Mismatches | Selected changes | Passing rate | Hint |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `route_best_ratio_0p8` | `181` | `0` | `181` | `7` | `0.725625` | reject false-feasible |
| `candidate0_route_ratio_0p95` | `176` | `5` | `181` | `7` | `0.719375` | reject false-feasible |
| `candidate0_route_loss_m_0` | `84` | `385` | `469` | `10` | `0.424375` | reject false-feasible |
| `route_best_loss_m_0` | `0` | `824` | `824` | `71` | `0.097500` | conservative, not equivalent |

The analyzer decision hint was:

```text
only_conservative_zero_false_feasible_route_guards_found; inspect false_infeasible availability before any online use: route_best_ratio_1, route_best_loss_m_0, route_best_loss_m_0p05, route_best_loss_m_0p1
```

Alignment diagnostics:

```text
route_minus_dp_progress_m:
mean=33.576027781265346
p50=32.52008789819595
p95=63.714044006840645
min=-0.5123020044579745
max=64.16406009755488
n=1600

candidate0_delta_route_minus_dp_m:
mean=-0.004131561761996071
p50=0.0
p95=0.008998863513039258
min=-1.4718985073073432
max=0.13571915352632935
n=1600

best_hard_feasible_index_overlap_rate=0.967948717948718
strict_pair_concordance_rate=0.9882142857142857
strict_pair_discordance_rate=0.011785714285714287
```

Interpretation:

1. The previous rejection is strengthened: a direct 0.8 ratio route-progress
   replacement reproduces the same `181` false-feasible candidates and `7`
   selected-mask changes as the reward replacement audit.
2. Candidate0-relative route guards are not sufficient. Even a strict
   `candidate0_route_ratio_0p95` still has `176` false-feasible candidates.
3. The only zero-false-feasible candidates in this grid are extremely
   conservative best-route guards (`route_best_ratio_1` and small best-route
   loss budgets). They reject many DP reward-feasible candidates; for example
   `route_best_loss_m_0` creates `824` false-infeasible candidates and changes
   selected-candidate mask status in `71` records. That is not an admissible
   online replacement without a separate availability and performance case.
4. Route and DP progress have strong local ordering agreement but incompatible
   absolute scales. The route-minus-DP offset is large, while candidate0
   normalized deltas are much closer. This supports future work on a separate
   conservative finite-candidate progress certificate, not a claim that route
   progress equals DP reward progress.

Mathematical boundary: this audit uses fixed current-tick finite-candidate
quantities only. A guard with false-feasible candidates relative to the DP
reward baseline cannot replace the DP progress gate. A zero-false-feasible
guard is still just a finite-candidate diagnostic unless it is later atomized
with fixed nonnegative scaling and keeps CAMP score affine in `w`; no classical
Benders subproblem, dual, or cut is claimed.

Decision: accept the progress mapping/guard analyzer and this single-smoke
audit as a diagnostic milestone. Reject direct route-progress replacement,
reject candidate0-relative route guard promotion, reject online selector
promotion, reject new CAMP weights, reject broader 12/36 online matrices, and
keep formal seeds frozen. The next admissible step is to run the same
progress mapping/guard audit over the predeclared development grid already
containing route-progress shadow logs, then decide whether any conservative
certificate has acceptable availability before designing a default-off online
selector.

### Full36 progress mapping/guard grid audit

The progress mapping/guard analyzer from
`b0622528c3a15016b213d1df6421aed11559bddd` was run over the two existing
predeclared Full36 development grids:

```text
Outcome-labeled posterior grid:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_full36_d5c2075

No-outcome input/latency grid:
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1
```

No new replay matrix was launched. DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`; CAMP local/GitHub/AutoDL HEAD was
`e72d7a1967aa40d3e50848514e4ebcddd4b4f7e6`.

Commands:

```bash
cd /root/autodl-tmp/camp_core

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_progress_mapping_guard.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_full36_d5c2075 \
  --label outcome_full36_e72d7a1 \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_full36_d5c2075/progress_mapping_guard_e72d7a1/progress_mapping_guard.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/shadow_route_progress_full36_d5c2075/progress_mapping_guard_e72d7a1/progress_mapping_guard.md

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_progress_mapping_guard.py \
  --root /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1 \
  --label no_outcome_full36_e72d7a1 \
  --output_json /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1/progress_mapping_guard_e72d7a1/progress_mapping_guard.json \
  --output_md /root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1/progress_mapping_guard_e72d7a1/progress_mapping_guard.md
```

A route-level breakdown artifact was also generated by invoking the same
analyzer separately for each route root and saving only the selected guard
metrics.

Artifact SHA:

| Grid | Artifact | SHA-256 |
| --- | --- | --- |
| outcome Full36 | `progress_mapping_guard.json` | `b101e4d114c8c4adde437f4f97400fc6c72c460b3bc89072141f0d99893e1c24` |
| outcome Full36 | `progress_mapping_guard.md` | `21b0f20878d918846e3d7a8d7a7c21f1480579a9ea6bca2cb3e7aaac19723f89` |
| outcome Full36 | `route_breakdown_progress_mapping_guard.json` | `ec2499f842c5d49f2e3fe62276c41d69e1d4c15c3b4c3ab3246b7c7e4cdd68d9` |
| outcome Full36 | `route_breakdown_progress_mapping_guard.md` | `78505d95e384e2ded58dc7e45e4b720953db71ffd9059a03d65d79ceaf765e11` |
| no-outcome Full36 | `progress_mapping_guard.json` | `5e7d6fcc806aac5373c02b27a81da834cc1dd3f27c5f89b0eebd7ed1cf860931` |
| no-outcome Full36 | `progress_mapping_guard.md` | `41e7c2ab9f6ae69cb0159c828c99f35134049b9ae7de273b1106349087ad9290` |
| no-outcome Full36 | `route_breakdown_progress_mapping_guard.json` | `e94f336794de28539ce5085727060bf6a5f5b1c53a3329ba43d5f07ea41ca47e` |
| no-outcome Full36 | `route_breakdown_progress_mapping_guard.md` | `2311ca685bc6ca9ea5e4ae6054c29889b49899b6f0c9deb99924d72ab7f1c1bd` |

Outcome-labeled Full36 global result:

```text
logs=36
records=7200
candidate_total=57600
records_with_route_progress=7200
nonfallback_records_by_dp_reward=6093
fallback_records_by_dp_reward=1107
decision_hint=reject_route_progress_guard_replacement_until_a_zero_false_feasible_guard_or_separate_progress_certificate_is_found
```

| Guard | False feasible | False infeasible | Mismatches | Selected changes | Passing rate | Hint |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `route_best_ratio_0p8` | `1195` | `81` | `1276` | `20` | `0.821163` | reject false-feasible |
| `route_best_ratio_1` | `407` | `28696` | `29103` | `953` | `0.310694` | reject false-feasible |
| `route_best_loss_m_0` | `407` | `28696` | `29103` | `953` | `0.310694` | reject false-feasible |
| `route_best_loss_m_0p05` | `497` | `27060` | `27557` | `608` | `0.340660` | reject false-feasible |
| `candidate0_route_ratio_0p95` | `1154` | `145` | `1299` | `20` | `0.819340` | reject false-feasible |
| `candidate0_route_loss_m_0` | `655` | `13783` | `14438` | `232` | `0.573906` | reject false-feasible |

Outcome-labeled alignment:

```text
best_hard_feasible_index_overlap_rate=0.9750533398982438
strict_pair_concordance_rate=0.962551972905251
strict_pair_discordance_rate=0.037448027094749016
route_minus_dp_progress_m.p95=274.49713954470496
candidate0_delta_route_minus_dp_m.p95=0.55242576599121
```

Outcome-labeled route breakdown:

| Route | Records | `route_best_0.8` false feasible | `route_best_1` false feasible | `route_best_1` false infeasible | `candidate0_0.95` false feasible | Best-overlap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `nishishinjuku_release_auto_route` | `2400` | `543` | `407` | `253` | `545` | `0.971196` |
| `sample_map_route_2_to_104` | `2400` | `171` | `0` | `15534` | `171` | `0.988011` |
| `sample_map_tl_route_59_to_86` | `2400` | `481` | `0` | `12909` | `438` | `0.964018` |

No-outcome Full36 global result:

```text
logs=36
records=7200
candidate_total=57600
records_with_route_progress=7200
nonfallback_records_by_dp_reward=6139
fallback_records_by_dp_reward=1061
decision_hint=only_conservative_zero_false_feasible_route_guards_found; inspect false_infeasible availability before any online use: route_best_ratio_1, route_best_loss_m_0, route_best_loss_m_0p05
```

| Guard | False feasible | False infeasible | Mismatches | Selected changes | Passing rate | Hint |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `route_best_ratio_0p8` | `1057` | `16` | `1073` | `18` | `0.838559` | reject false-feasible |
| `route_best_ratio_1` | `0` | `41121` | `41121` | `1253` | `0.106580` | conservative, not equivalent |
| `route_best_loss_m_0` | `0` | `41121` | `41121` | `1253` | `0.106580` | conservative, not equivalent |
| `route_best_loss_m_0p05` | `0` | `39301` | `39301` | `846` | `0.138177` | conservative, not equivalent |
| `route_best_loss_m_0p1` | `2` | `36954` | `36956` | `620` | `0.178958` | reject false-feasible |
| `candidate0_route_ratio_0p95` | `1005` | `127` | `1132` | `19` | `0.835729` | reject false-feasible |
| `candidate0_route_loss_m_0` | `368` | `19801` | `20169` | `202` | `0.483108` | reject false-feasible |

No-outcome alignment:

```text
best_hard_feasible_index_overlap_rate=0.977683661834175
strict_pair_concordance_rate=0.9885256473856533
strict_pair_discordance_rate=0.01147435261434666
route_minus_dp_progress_m.p95=165.52153920621703
candidate0_delta_route_minus_dp_m.p95=0.025748516178637715
```

No-outcome route breakdown:

| Route | Records | `route_best_0.8` false feasible | `route_best_1` false feasible | `route_best_1` false infeasible | `candidate0_0.95` false feasible | Best-overlap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `nishishinjuku_release_auto_route` | `2400` | `405` | `0` | `12678` | `396` | `0.979852` |
| `sample_map_route_2_to_104` | `2400` | `171` | `0` | `15534` | `171` | `0.988011` |
| `sample_map_tl_route_59_to_86` | `2400` | `481` | `0` | `12909` | `438` | `0.964018` |

Interpretation:

1. The single-smoke conclusion generalizes: route progress remains an unsafe
   replacement for DP reward progress. The broad `route_best_ratio_0p8` guard
   has more than one thousand false-feasible candidates on both Full36 grids.
2. Candidate0-relative route guards are also rejected at grid scale:
   `candidate0_route_ratio_0p95` has `1154` false-feasible candidates on the
   outcome-labeled grid and `1005` on the no-outcome grid.
3. The outcome-labeled grid is stricter evidence than the no-outcome rerun for
   DP-reward equivalence: even the best-route equality guard still has `407`
   false-feasible candidates, all on `nishishinjuku_release_auto_route`.
4. The no-outcome grid contains zero-false-feasible best-route guards, but only
   by becoming far too conservative: `route_best_ratio_1` keeps about
   `10.66%` of candidates and marks `41121` DP reward-feasible candidates as
   infeasible. This is not a viable online replacement without a separate
   availability and safety case.
5. Strong pairwise route/DP progress ordering agreement is not enough. Absolute
   scales remain incompatible, and small ordering disagreements can create
   false-feasible candidates exactly where a hard progress guard must be
   conservative.

Mathematical boundary: every measured quantity is a fixed current-tick
finite-candidate diagnostic. These grid audits compare masks only; they do not
define a CAMP atom, selector input, Benders subproblem, dual, or cut. A future
legal progress response should be a separate finite-candidate certificate or
nonnegative atomized hinge, not an attempted equality replacement for DP reward
progress.

Decision: reject route-progress-as-DP-progress at development-grid scale.
Reject candidate0-relative route guards. Reject online selector promotion,
formal seeds, and CAMP retraining from this evidence. The next admissible
engineering step is not another route-progress mapping attempt; it is either
to use route/H10/clearance as separate conservative finite-candidate atoms or
to reduce the latency of the already logged current-tick clearance descriptor
before re-running no-outcome shadow audits.

### Vectorized obstacle-clearance descriptor

Commit `3d980374479e31257c6fb5a2a476763f58f2385f` vectorizes the lower-bound
portion of `compute_candidate_obstacle_clearance_diagnostics`. The schema and
math definition remain unchanged:

```text
schema_version=candidate_current_tick_obstacle_clearance_v2
selection_effect=false
future_outcome_leakage=false
exact_obb_enabled remains default-off
```

The change replaces the Python obstacle-step loop for the online-eligible
bounding-circle lower-bound hinge with vectorized NumPy operations. Optional
exact OBB diagnostics are preserved and still run only when explicitly enabled
and only for near-threshold lower-bound pairs. This changes no DP weights,
sampler, candidate set, CAMP weights, atom schema, replay selector, or formal
seed usage.

Local verification:

```text
PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core
py -3.12 -m pytest \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_are_current_tick_hinges \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_reports_obb_mode \
  camp_core\tests\test_diffusion_planner_integration.py::test_candidate_obstacle_clearance_diagnostics_can_skip_exact_obb \
  camp_core\tests\test_diffusion_planner_component_benchmark.py \
  camp_core\tests\test_diffusion_planner_no_outcome_shadow_certificate.py \
  -q
# 11 passed

py -3.12 -m compileall -q camp_core\camp_core\integrations\diffusion_planner.py
# passed

git diff --check
# passed
```

AutoDL was synchronized to
`3d980374479e31257c6fb5a2a476763f58f2385f`; DP remained fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. The same targeted pytest
selection, compileall, and `git diff --check` passed on AutoDL.

Synthetic equivalence microbenchmark:

```text
Input: K=8, M=4, T=30, OBB lower-bound mode, exact OBB disabled.
The vectorized output matched a slow reference loop for:
min_obstacle_clearance_lower_bound_m,
soft_clearance_violation_cost,
near_miss_violation_cost,
obstacle_slots,
geometry_mode.

Local p95:
vectorized=6.312925 ms
slow_reference=53.857420 ms
p95_speedup=8.531294

AutoDL p95:
vectorized=1.164613 ms
slow_reference=9.232306 ms
p95_speedup=7.927361
```

No-outcome latency smoke:

```bash
cd /root/autodl-tmp/camp_core

OUT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/clearance_vectorized_3d98037_sample_tl_seed1_npc4_tloff_static

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
REPLAY_NO_PNG=1 \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --map_path /root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm \
  --route /root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --model_path /root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --config /root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json \
  --output_dir "$OUT" \
  --device cuda \
  --advance_mode perfect \
  --steps 200 \
  --seed 1 \
  --max_npcs 4 \
  --spawn_probability 0.3 \
  --traffic_lights off \
  --reward_config /root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json \
  --camp_selector_mode static \
  --camp_atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --camp_static_weights /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/offline_weights_dp_static.npy \
  --num_candidates 8 \
  --candidate_noise_scale 1.0 \
  --candidate_reference_blend_steps 5 \
  --camp_lane_corridor_buffer 1.0 \
  --camp_feasibility_source dp_reward \
  --camp_fallback_mode learned \
  --camp_min_progress_ratio 0.8 \
  --camp_shadow_route_progress \
  --camp_shadow_obstacle_clearance \
  --camp_reward_horizon_steps 30 \
  --camp_outcome_horizon_steps 30 \
  --near_miss_threshold_m 2.0
```

Audit commands:

```bash
AUDIT=$OUT/audit_3d98037

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  --selection_log "$OUT/camp_selection_log.json" \
  --atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --expected_logs 1 \
  --expected_candidates 8 \
  --expected_advance_mode perfect \
  --closed_loop_outcome_policy forbidden \
  --forbid_seed 11 \
  --forbid_seed 12 \
  --forbid_seed 13 \
  --required_candidate_field candidate_route_progress \
  --require_finite_candidate_contract \
  --output_json "$AUDIT/dataset_audit_clearance_vectorized.json"

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_latency_budget.py \
  --selection_log "$OUT/camp_selection_log.json" \
  --label clearance_vectorized_3d98037_sample_tl_seed1_npc4_tloff_static \
  --output_json "$AUDIT/latency_budget_clearance_vectorized.json" \
  --output_md "$AUDIT/latency_budget_clearance_vectorized.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `573e1715ea7d89c386629297d884d19afb176c3fb475a6644e85764ca5b4575b` |
| `camp_validation_summary.json` | `679566e4cb621e9c1939ee5903fa58a4b933e1bf5bdbd3204badbb3d54415cda` |
| `camp_replay_summary.json` | `51d2ec096db5012bff6ff51a6ba3cdd4f5423cd9863eed72da711a81f02818f9` |
| `dataset_audit_clearance_vectorized.json` | `220d730b99643a1047f434ad6cea68235715287759f481ff57117f6b9d472ebb` |
| `latency_budget_clearance_vectorized.json` | `88bee7f5494de1cf9ad49cd5c17b772bdd337274f4211ff24f284b2c32d2a140` |
| `latency_budget_clearance_vectorized.md` | `874889942347d9bba3ab2b44a653f882057c675fcb7552f249706925c3efba01` |

Latency comparison against the previous exact-OBB-off smoke
`no_outcome_exact_obb_off_b3dcbc1_sample_tl_seed1_npc4_tloff_static`:

| Quantity | Old p95 | New p95 |
| --- | ---: | ---: |
| `latency_ms_shadow_obstacle_clearance` | `9.296867 ms` | `0.858788 ms` |
| `latency_ms_including_candidate_generation` | `109.424894 ms` | `99.199241 ms` |
| `latency_ms_candidate_generation` | `58.762836 ms` | `59.183047 ms` |
| `latency_ms_camp_selection` | `8.915116 ms` | `8.466316 ms` |
| `latency_ms_reward_scoring` | `30.120930 ms` | `29.040589 ms` |

Clearance descriptor invariants on both old and new smoke:

```text
records=200
clearance_records=200
exact_obb_enabled=false
obstacle_slots.mean=2.2
obstacle_slots.p95=4.0
obstacle_slots.max=4.0
exact_pairs.p95=0
exact_pairs.max=0
soft_nonzero=590
near_nonzero=577
```

Interpretation:

1. The vectorized descriptor keeps the same finite current-tick lower-bound
   hinge semantics while removing most of the Python loop overhead.
2. On the single no-outcome latency smoke, clearance p95 falls from
   `9.296867 ms` to `0.858788 ms`, and total p95 falls below the `100 ms`
   development target (`99.199241 ms`). This is a useful diagnostic milestone,
   not a full development-gate pass.
3. The replay still has large max latency (`280.378 ms`) from non-clearance
   sources, including reward scoring and CAMP selection outliers, so a broader
   Full36 no-outcome rerun is required before any online/default-off selector
   promotion.

Mathematical boundary: the clearance descriptor remains a fixed current-tick
finite-candidate diagnostic and can be used later only as a nonnegative hinge
or deterministic finite-candidate guard. It is not a Benders subproblem, dual,
or cut source. No closed-loop future outcome labels were used in this smoke or
dataset audit.

Decision: accept the vectorized clearance descriptor and single no-outcome
latency smoke as a positive engineering milestone. Reject formal seeds,
CAMP retraining, and online selector promotion from this evidence alone. The
next admissible step is a no-outcome Full36 latency rerun or an equivalent
predeclared development-grid latency audit using the vectorized descriptor,
followed by the route/H10/clearance shadow selector audit if the p95 latency
budget has real margin.

### Clearance Latency Projection Audit on Existing No-Outcome Full36 Logs

Commit:

- Local/GitHub/AutoDL CAMP: `1b34a45bbb9e075fad9788e69e7ce4db5d6d01de`
  (`Add DP clearance latency projection audit`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The continuation prompt still referenced `d5c2075be56d9486a71a280fc2e17b515740b8ff`,
but live inspection showed the current authoritative CAMP state was already
`8bd5df51e0254906b2530340611204fb39257134` before this iteration and
`1b34a45bbb9e075fad9788e69e7ce4db5d6d01de` after the projection-audit commit.
AutoDL `git pull --ff-only` hung on the GitHub connection, so the exact
`8bd5df5 -> 1b34a45` update was transferred as a verified Git bundle and
fast-forwarded on AutoDL without touching existing untracked files.

Purpose:

This audit asks whether the single-smoke clearance vectorization result is
large enough to justify a broader no-outcome Full36 replay. It does not run a
new replay and does not change online selection. It projects existing
Full36 per-record total latency by replacing the old measured clearance
latency with three predeclared replacement models:

1. `constant_new_p95`: replace each old clearance value by the new smoke p95
   (`0.858788 ms`).
2. `cap_at_new_p95`: replace by `min(old_clearance, 0.858788 ms)`.
3. `scale_by_smoke_p95_ratio`: multiply each old clearance value by
   `0.858788 / 9.296867`.

Local verification:

```powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
py -3.12 -m pytest `
  camp_core\tests\test_diffusion_planner_clearance_latency_projection.py `
  camp_core\tests\test_diffusion_planner_latency_budget.py -q

py -3.12 -m py_compile `
  scripts\integrations\analyze_diffusion_planner_clearance_latency_projection.py `
  camp_core\tests\test_diffusion_planner_clearance_latency_projection.py

git diff --check
```

Result: `3 passed`; compile and diff checks passed.

AutoDL verification:

```bash
cd /root/autodl-tmp/camp_core
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_clearance_latency_projection.py \
  camp_core/tests/test_diffusion_planner_latency_budget.py -q
```

Result: `3 passed`.

Projection command:

```bash
cd /root/autodl-tmp/camp_core
ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1
OUT=$ROOT/clearance_latency_projection_1b34a45

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_clearance_latency_projection.py \
  --root "$ROOT" \
  --label no_outcome_full36_clearance_projection_1b34a45 \
  --reference_old_clearance_p95_ms 9.296867 \
  --reference_new_clearance_p95_ms 0.858788 \
  --reference_source old_exact_off_smoke_vs_vectorized_smoke_sha_88bee7f5494de1cf9ad49cd5c17b772bdd337274f4211ff24f284b2c32d2a140 \
  --output_json "$OUT/clearance_latency_projection.json" \
  --output_md "$OUT/clearance_latency_projection.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `clearance_latency_projection.json` | `501a1609ad8934d0a5a44906a2eacec156401ac216622ceb0300cd445d43b28f` |
| `clearance_latency_projection.md` | `64d43bd10e7512e27da848e3df89fee7d720695f6a4d379091568eed60005735` |

Projection summary:

| Quantity | Baseline | `constant_new_p95` | `cap_at_new_p95` | `scale_by_smoke_p95_ratio` |
| --- | ---: | ---: | ---: | ---: |
| logs | `36` | `36` | `36` | `36` |
| records | `7200` | `7200` | `7200` | `7200` |
| missing total/clearance | `0 / 0` | `0 / 0` | `0 / 0` | `0 / 0` |
| record-level total p95 | `118.412714 ms` | `98.059038 ms` | `98.034612 ms` | `98.459287 ms` |
| per-run p95 distribution p95 | `146.198818 ms` | `100.398759 ms` | `100.398759 ms` | `101.000880 ms` |
| runs over `100 ms` | `15 / 36` | `4 / 36` | `4 / 36` | `4 / 36` |

Remaining projected over-budget runs:

| Mode | Run | Baseline p95 | Projected p95 |
| --- | --- | ---: | ---: |
| `constant_new_p95` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `204.791084` | `104.471944` |
| `constant_new_p95` | `sample_map/sample_map_tl_route_59_to_86/seed_2/npc_4/spawn_0p3/tl_off/static` | `109.938423` | `100.839536` |
| `constant_new_p95` | `sample_map/sample_map_tl_route_59_to_86/seed_3/npc_4/spawn_0p3/tl_on/static` | `107.039037` | `100.251833` |
| `constant_new_p95` | `nishishinjuku/nishishinjuku_release_auto_route/seed_3/npc_4/spawn_0p3/tl_on/static` | `127.487494` | `100.020717` |
| `scale_by_smoke_p95_ratio` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `204.791084` | `111.469578` |
| `scale_by_smoke_p95_ratio` | `sample_map/sample_map_tl_route_59_to_86/seed_2/npc_4/spawn_0p3/tl_on/static` | `144.509146` | `101.157018` |
| `scale_by_smoke_p95_ratio` | `sample_map/sample_map_tl_route_59_to_86/seed_2/npc_4/spawn_0p3/tl_off/static` | `109.938423` | `100.948834` |
| `scale_by_smoke_p95_ratio` | `nishishinjuku/nishishinjuku_release_auto_route/seed_3/npc_4/spawn_0p3/tl_on/static` | `127.487494` | `100.623074` |

Interpretation:

1. Clearance vectorization is material at development-grid scale: the
   projected over-budget count falls from `15/36` to `4/36`, and record-level
   total p95 falls below `100 ms` under all three sensitivity modes.
2. The latency gate is still not passed. Per-run p95 remains above the
   `100 ms` target in `4/36` runs, and the worst projected run is still
   `104.471944 ms` under the constant/cap models and `111.469578 ms` under the
   proportional model.
3. The next bottleneck is no longer solely clearance. The remaining tail is
   concentrated in `npc_4` runs on `sample_map_tl_route_59_to_86` and one
   `nishishinjuku` traffic-light run, so the next engineering step should
   diagnose non-clearance tail components before spending a full replay matrix.

Mathematical boundary: this projection is a finite-log, read-only engineering
diagnostic. It uses current tick latency fields only to estimate runtime impact.
It does not define CAMP atoms, online selector inputs, a Benders subproblem,
duals, or cuts. No outcome labels, formal seeds, DP modification, DP retraining,
CAMP retraining, or online selector promotion were used.

Decision: accept the projection analyzer and projection artifact as a useful
development-grid latency diagnostic. Reject claiming a Full36 latency gate pass
from this evidence. The next admissible step is a targeted tail-component audit
on the remaining projected over-budget logs, followed by either a small
non-formal smoke confirming the specific tail fix or a no-outcome Full36 rerun
only if the tail audit indicates enough margin.

### Projected Latency Tail Attribution on Remaining Over-Budget Runs

Commit:

- Local/GitHub/AutoDL CAMP:
  `f5ef1177f0ef47296c3bce5f2b46167553fe8259`
  (`Add DP projected latency tail audit`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Purpose:

The previous projection reduced the development-grid projected over-budget
count from `15/36` to `4/36`, but it did not pass the per-run `100 ms` p95
gate. This audit attributes the remaining projected tail without replaying,
changing selection, training, or reading closed-loop outcomes.

Local verification:

```powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
py -3.12 -m pytest `
  camp_core\tests\test_diffusion_planner_projected_latency_tail.py `
  camp_core\tests\test_diffusion_planner_clearance_latency_projection.py -q

py -3.12 -m py_compile `
  scripts\integrations\analyze_diffusion_planner_projected_latency_tail.py `
  camp_core\tests\test_diffusion_planner_projected_latency_tail.py

git diff --check
```

Result: `4 passed`; compile and diff checks passed.

AutoDL verification:

```bash
cd /root/autodl-tmp/camp_core
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_projected_latency_tail.py \
  camp_core/tests/test_diffusion_planner_clearance_latency_projection.py -q
```

Result: `4 passed`.

Audit command:

```bash
cd /root/autodl-tmp/camp_core
ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1
OUT=$ROOT/projected_latency_tail_f5ef117

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_projected_latency_tail.py \
  --root "$ROOT" \
  --label no_outcome_full36_projected_latency_tail_f5ef117 \
  --reference_old_clearance_p95_ms 9.296867 \
  --reference_new_clearance_p95_ms 0.858788 \
  --reference_source old_exact_off_smoke_vs_vectorized_smoke_sha_88bee7f5494de1cf9ad49cd5c17b772bdd337274f4211ff24f284b2c32d2a140 \
  --output_json "$OUT/projected_latency_tail.json" \
  --output_md "$OUT/projected_latency_tail.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `projected_latency_tail.json` | `e14487fb861264e76974dbfe9cc5f4993578d4ffb92c8223321c1571477433c1` |
| `projected_latency_tail.md` | `2aa6699bbb5a0ef3c4d77578d42c9c67a383216e8652f4aca12b42f66fcc4445` |

Tail summary:

| Mode | Runs over budget | Tail rows | Shortfall mean | Shortfall p95 | Shortfall max |
| --- | ---: | ---: | ---: | ---: | ---: |
| `constant_new_p95` | `4 / 36` | `40` | `1.396007 ms` | `3.927083 ms` | `4.471944 ms` |
| `cap_at_new_p95` | `4 / 36` | `40` | `1.396007 ms` | `3.927083 ms` | `4.471944 ms` |
| `scale_by_smoke_p95_ratio` | `4 / 36` | `40` | `3.549626 ms` | `9.922694 ms` | `11.469578 ms` |

Top primary components across the remaining tail rows:

| Mode | Component | Mean | P95 | Max |
| --- | --- | ---: | ---: | ---: |
| `constant_new_p95` | `latency_ms_candidate_generation` | `60.197954` | `68.637244` | `84.938101` |
| `constant_new_p95` | `latency_ms_reward_scoring` | `47.753345` | `206.013012` | `218.426345` |
| `constant_new_p95` | `latency_ms_camp_selection` | `24.570530` | `171.482915` | `190.699888` |
| `scale_by_smoke_p95_ratio` | `latency_ms_candidate_generation` | `59.243097` | `68.637244` | `84.938101` |
| `scale_by_smoke_p95_ratio` | `latency_ms_reward_scoring` | `47.963396` | `205.847488` | `218.426345` |
| `scale_by_smoke_p95_ratio` | `latency_ms_camp_selection` | `24.350766` | `166.850207` | `190.699888` |

Nested CAMP tail:

| Mode | Component | Mean | P95 | Max |
| --- | --- | ---: | ---: | ---: |
| `constant_new_p95` | `latency_ms_camp_atom_computation` | `20.830185` | `168.914251` | `187.605512` |
| `constant_new_p95` | `latency_ms_camp_collision_checks` | `3.295744` | `6.183536` | `9.071019` |
| `scale_by_smoke_p95_ratio` | `latency_ms_camp_atom_computation` | `20.489023` | `163.690204` | `187.605512` |
| `scale_by_smoke_p95_ratio` | `latency_ms_camp_collision_checks` | `3.425215` | `6.058856` | `9.071019` |

Per-run observations:

| Mode | Run | Projected p95 | Shortfall | Tail note |
| --- | --- | ---: | ---: | --- |
| `constant_new_p95` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `104.471944` | `4.471944` | candidate generation mean `59.217512`; reward and CAMP have large tail outliers |
| `constant_new_p95` | `sample_map/sample_map_tl_route_59_to_86/seed_2/npc_4/spawn_0p3/tl_off/static` | `100.839536` | `0.839536` | shortfall is small; candidate generation remains the largest stable component |
| `constant_new_p95` | `sample_map/sample_map_tl_route_59_to_86/seed_3/npc_4/spawn_0p3/tl_on/static` | `100.251833` | `0.251833` | shortfall is small; reward/CAMP outliers are present but not a sufficient gate explanation alone |
| `constant_new_p95` | `nishishinjuku/nishishinjuku_release_auto_route/seed_3/npc_4/spawn_0p3/tl_on/static` | `100.020717` | `0.020717` | effectively at threshold; no online change justified |
| `scale_by_smoke_p95_ratio` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `111.469578` | `11.469578` | proportional clearance projection is more conservative; this run remains the true blocker |
| `scale_by_smoke_p95_ratio` | `sample_map/sample_map_tl_route_59_to_86/seed_2/npc_4/spawn_0p3/tl_on/static` | `101.157018` | `1.157018` | small residual shortfall |
| `scale_by_smoke_p95_ratio` | `sample_map/sample_map_tl_route_59_to_86/seed_2/npc_4/spawn_0p3/tl_off/static` | `100.948834` | `0.948834` | small residual shortfall |
| `scale_by_smoke_p95_ratio` | `nishishinjuku/nishishinjuku_release_auto_route/seed_3/npc_4/spawn_0p3/tl_on/static` | `100.623074` | `0.623074` | small residual shortfall |

Interpretation:

1. The remaining projected shortfall is small under constant/cap replacement
   (`max=4.471944 ms`) but not small under the proportional model
   (`max=11.469578 ms`).
2. `latency_ms_candidate_generation` is the largest stable component in the
   remaining p95 tail, but candidate generation belongs to the fixed DP
   black-box side of the boundary. Reducing it by changing DP sampling is not
   an admissible CAMP-side fix under the current goal.
3. The large CAMP-side outlier is `latency_ms_camp_atom_computation`, not
   collision checking or scoring. That makes exact semantic optimization of
   current-tick CAMP atom computation an admissible next engineering target,
   provided the atom values remain identical and the finite-candidate affine
   CAMP score is unchanged.
4. Reward scoring has large tail outliers, but it is part of the existing DP
   reward/feasibility instrumentation rather than a CAMP Benders subproblem.
   It can be audited or optimized as engineering plumbing only; it must not be
   reinterpreted as a cut source.

Mathematical boundary: this tail audit is a projection-based latency
attribution over existing logs. It uses current-tick latency measurements and
does not alter candidate trajectories, atoms, weights, feasibility, selector
outputs, or closed-loop outcomes. No outcome labels, formal seeds, DP
modification, DP retraining, CAMP retraining, online selector promotion, or
new replay matrix were used.

Decision: accept the tail audit as evidence that the immediate next step should
not be a Full36 rerun. Reject DP sampling changes and online selector promotion.
The next admissible task is a component-savings sensitivity audit and then a
semantics-preserving CAMP atom-computation optimization if the sensitivity
shows enough p95 margin without changing CAMP mathematics.

### Latency Component-Savings Sensitivity Audit

Commit:

- Local/GitHub/AutoDL CAMP:
  `0257f1a0c3638cda1338d64765ffb73ff7c866a6`
  (`Add DP latency savings sensitivity audit`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Purpose:

The previous tail attribution identified `latency_ms_camp_atom_computation` as
the largest CAMP-side outlier, but the development gate is per-run p95, not max
latency. This audit asks whether plausible or upper-bound component savings
would actually clear the projected Full36 latency gate before implementing any
optimization.

The audit remains read-only: it projects per-record total latency after the
same clearance replacement modes, then subtracts hypothetical savings for
predeclared components. It does not replay, alter candidate trajectories,
change atom values, change feasibility, change weights, or alter selection.

Local verification:

```powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
py -3.12 -m pytest `
  camp_core\tests\test_diffusion_planner_latency_savings_sensitivity.py `
  camp_core\tests\test_diffusion_planner_projected_latency_tail.py `
  camp_core\tests\test_diffusion_planner_clearance_latency_projection.py -q

py -3.12 -m py_compile `
  scripts\integrations\analyze_diffusion_planner_latency_savings_sensitivity.py `
  camp_core\tests\test_diffusion_planner_latency_savings_sensitivity.py

git diff --check
```

Result: `6 passed`; compile and diff checks passed.

AutoDL verification:

```bash
cd /root/autodl-tmp/camp_core
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_latency_savings_sensitivity.py \
  camp_core/tests/test_diffusion_planner_projected_latency_tail.py \
  camp_core/tests/test_diffusion_planner_clearance_latency_projection.py -q
```

Result: `6 passed`.

Audit command:

```bash
cd /root/autodl-tmp/camp_core
ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1
OUT=$ROOT/latency_savings_sensitivity_0257f1a

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_latency_savings_sensitivity.py \
  --root "$ROOT" \
  --label no_outcome_full36_latency_savings_sensitivity_0257f1a \
  --reference_old_clearance_p95_ms 9.296867 \
  --reference_new_clearance_p95_ms 0.858788 \
  --reference_source old_exact_off_smoke_vs_vectorized_smoke_sha_88bee7f5494de1cf9ad49cd5c17b772bdd337274f4211ff24f284b2c32d2a140 \
  --output_json "$OUT/latency_savings_sensitivity.json" \
  --output_md "$OUT/latency_savings_sensitivity.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `latency_savings_sensitivity.json` | `31b586fb8db4bd8aa75e3dd952c41dcd3aaa5dbf85fd0164fd695182a3312b01` |
| `latency_savings_sensitivity.md` | `cb59dd69c46dd6bedd9f8c82d2808a4e3fdeece4303facc8d706ca06af9c387a` |

Sensitivity summary:

| Projection mode | Scenario | CAMP-side exact-equivalence candidate | Runs over `100 ms` | Run-p95 distribution p95 | Max shortfall |
| --- | --- | ---: | ---: | ---: | ---: |
| `constant_new_p95` | `no_extra_saving` | yes | `4 / 36` | `100.398759` | `4.471944` |
| `constant_new_p95` | `camp_atom_computation_25pct_saving` | yes | `1 / 36` | `99.568805` | `3.656803` |
| `constant_new_p95` | `camp_atom_computation_50pct_saving` | yes | `1 / 36` | `98.718206` | `2.757182` |
| `constant_new_p95` | `camp_atom_computation_zero_upper_bound` | yes | `1 / 36` | `96.898324` | `0.532140` |
| `constant_new_p95` | `camp_selection_zero_upper_bound` | no | `0 / 36` | `94.056313` | `null` |
| `constant_new_p95` | `reward_scoring_zero_engineering_upper_bound` | no | `0 / 36` | `72.208449` | `null` |
| `constant_new_p95` | `candidate_generation_zero_inadmissible_upper_bound` | no | `0 / 36` | `42.634679` | `null` |
| `scale_by_smoke_p95_ratio` | `no_extra_saving` | yes | `4 / 36` | `101.000880` | `11.469578` |
| `scale_by_smoke_p95_ratio` | `camp_atom_computation_25pct_saving` | yes | `2 / 36` | `100.018174` | `10.507339` |
| `scale_by_smoke_p95_ratio` | `camp_atom_computation_50pct_saving` | yes | `1 / 36` | `99.109654` | `9.660349` |
| `scale_by_smoke_p95_ratio` | `camp_atom_computation_zero_upper_bound` | yes | `1 / 36` | `97.190324` | `7.567782` |
| `scale_by_smoke_p95_ratio` | `camp_selection_zero_upper_bound` | no | `1 / 36` | `94.339530` | `1.004804` |
| `scale_by_smoke_p95_ratio` | `reward_scoring_zero_engineering_upper_bound` | no | `0 / 36` | `72.367948` | `null` |
| `scale_by_smoke_p95_ratio` | `candidate_generation_zero_inadmissible_upper_bound` | no | `0 / 36` | `44.384598` | `null` |

Remaining blocker after CAMP-side upper bounds:

| Projection mode | Scenario | Remaining run | Projected p95 | Shortfall |
| --- | --- | --- | ---: | ---: |
| `constant_new_p95` | `camp_atom_computation_zero_upper_bound` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `100.532140` | `0.532140` |
| `scale_by_smoke_p95_ratio` | `camp_atom_computation_zero_upper_bound` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `107.567782` | `7.567782` |
| `scale_by_smoke_p95_ratio` | `camp_selection_zero_upper_bound` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `101.004804` | `1.004804` |

Interpretation:

1. CAMP atom-computation optimization is useful but insufficient as a sole
   gate-passing strategy. Even the unrealistic zero-cost upper bound still
   leaves one projected over-budget run under both the constant/cap and
   proportional clearance models.
2. Removing all CAMP selection latency is also insufficient under the more
   conservative proportional clearance model. Therefore a narrow CAMP atom
   optimization should not be treated as enough evidence to run a Full36 replay.
3. Reward-scoring removal clears the projected gate, but reward scoring is
   instrumentation/plumbing here, not a CAMP Benders subproblem or cut source.
   Any reward-side optimization must be exact-equivalent and documented as
   engineering latency work only.
4. Candidate-generation removal clears the projected gate, but it is explicitly
   inadmissible under the current objective because DP is fixed as the black-box
   generator.

Mathematical boundary: component savings are hypothetical runtime projections
over fixed current-tick logs. They do not change finite candidates, atoms,
weights, constraints, the affine CAMP score, the simplex/CVaR/L2 master, or any
Benders-style logic. No outcome labels, formal seeds, DP modification, DP
retraining, CAMP retraining, online selector promotion, or new replay matrix
were used.

Decision: accept this sensitivity audit as a rejection of the
`optimize only CAMP atom computation, then rerun Full36` path. The next
admissible engineering target is exact-equivalent reward/feasibility latency
plumbing or a combined exact-equivalent CAMP-selection plus reward-scoring
latency plan. Do not run a new Full36 replay until a projected exact-equivalent
combined plan clears the conservative proportional model with meaningful
per-run margin.

### Combined Latency Component-Savings Sensitivity Audit

Commit:

- Local/GitHub/AutoDL CAMP:
  `39ae39797e0155fec4a5bb6e5f4cff253be5d804`
  (`Add DP combined latency savings sensitivity`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Purpose:

The previous sensitivity audit rejected a CAMP-only atom-computation
optimization as insufficient. This audit extends the same read-only projection
to fractional reward-scoring savings and combined exact-equivalent engineering
scenarios. It separates two notions:

1. `camp_side_exact_equivalence_candidate`: the saving can be pursued inside
   CAMP-side computation while keeping atom values and affine scoring
   unchanged.
2. `exact_equivalence_engineering_candidate`: the saving can be considered only
   if all reward outputs, feasibility masks, atoms, scores, and selected
   trajectories remain exactly equivalent under the existing tolerances.

Reward/feasibility plumbing is explicitly not a CAMP Benders subproblem or cut
source.

Local verification:

```powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
py -3.12 -m pytest `
  camp_core\tests\test_diffusion_planner_latency_savings_sensitivity.py `
  camp_core\tests\test_diffusion_planner_projected_latency_tail.py `
  camp_core\tests\test_diffusion_planner_clearance_latency_projection.py -q

py -3.12 -m py_compile `
  scripts\integrations\analyze_diffusion_planner_latency_savings_sensitivity.py `
  camp_core\tests\test_diffusion_planner_latency_savings_sensitivity.py

git diff --check
```

Result: `6 passed`; compile and diff checks passed.

AutoDL verification:

```bash
cd /root/autodl-tmp/camp_core
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_latency_savings_sensitivity.py \
  camp_core/tests/test_diffusion_planner_projected_latency_tail.py \
  camp_core/tests/test_diffusion_planner_clearance_latency_projection.py -q
```

Result: `6 passed`.

Audit command:

```bash
cd /root/autodl-tmp/camp_core
ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1
OUT=$ROOT/combined_latency_savings_sensitivity_39ae397

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_latency_savings_sensitivity.py \
  --root "$ROOT" \
  --label no_outcome_full36_combined_latency_savings_sensitivity_39ae397 \
  --reference_old_clearance_p95_ms 9.296867 \
  --reference_new_clearance_p95_ms 0.858788 \
  --reference_source old_exact_off_smoke_vs_vectorized_smoke_sha_88bee7f5494de1cf9ad49cd5c17b772bdd337274f4211ff24f284b2c32d2a140 \
  --output_json "$OUT/combined_latency_savings_sensitivity.json" \
  --output_md "$OUT/combined_latency_savings_sensitivity.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `combined_latency_savings_sensitivity.json` | `f296c5636f954a2a0cf64734efd414ab440adbe59e5b2b5803103a38d025bf04` |
| `combined_latency_savings_sensitivity.md` | `a1a18f13302b37d4f63f79653cdbdd8d4f27684280a12948ccb7aa5f265d9708` |

Key sensitivity results:

| Projection mode | Scenario | Exact engineering candidate | Runs over `100 ms` | Run-p95 distribution p95 | Max shortfall |
| --- | --- | ---: | ---: | ---: | ---: |
| `constant_new_p95` | `no_extra_saving` | yes | `4 / 36` | `100.398759` | `4.471944` |
| `constant_new_p95` | `reward_scoring_10pct_saving` | yes | `1 / 36` | `97.390284` | `1.240096` |
| `constant_new_p95` | `reward_scoring_25pct_saving` | yes | `0 / 36` | `93.186998` | `null` |
| `constant_new_p95` | `camp_atom_50pct_plus_reward_10pct` | yes | `0 / 36` | `95.643702` | `null` |
| `scale_by_smoke_p95_ratio` | `no_extra_saving` | yes | `4 / 36` | `101.000880` | `11.469578` |
| `scale_by_smoke_p95_ratio` | `reward_scoring_10pct_saving` | yes | `1 / 36` | `97.983563` | `8.498877` |
| `scale_by_smoke_p95_ratio` | `reward_scoring_25pct_saving` | yes | `1 / 36` | `93.751388` | `3.904493` |
| `scale_by_smoke_p95_ratio` | `reward_scoring_50pct_saving` | yes | `0 / 36` | `86.446678` | `null` |
| `scale_by_smoke_p95_ratio` | `camp_atom_50pct_plus_reward_10pct` | yes | `1 / 36` | `96.143864` | `6.680325` |
| `scale_by_smoke_p95_ratio` | `camp_atom_50pct_plus_reward_25pct` | yes | `1 / 36` | `91.797058` | `2.123662` |
| `scale_by_smoke_p95_ratio` | `camp_atom_50pct_plus_reward_50pct` | yes | `0 / 36` | `84.576868` | `null` |

Remaining conservative-model blocker:

| Scenario | Remaining run | Projected p95 | Shortfall |
| --- | --- | ---: | ---: |
| `reward_scoring_10pct_saving` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `108.498877` | `8.498877` |
| `reward_scoring_25pct_saving` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `103.904493` | `3.904493` |
| `camp_atom_50pct_plus_reward_10pct` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `106.680325` | `6.680325` |
| `camp_atom_50pct_plus_reward_25pct` | `sample_map/sample_map_tl_route_59_to_86/seed_1/npc_4/spawn_0p3/tl_off/static` | `102.123662` | `2.123662` |

Interpretation:

1. Under the less conservative constant/cap clearance model, `reward 25%` or
   `camp atom 50% + reward 10%` is enough to clear the projected gate.
2. Under the conservative proportional clearance model, the same moderate
   savings are not enough. The only tested exact-engineering scenarios that
   clear the projected gate are `reward_scoring_50pct_saving` and
   `camp_atom_50pct_plus_reward_50pct`.
3. The remaining blocker is always
   `sample_map_tl_route_59_to_86/seed_1/npc_4/tl_off/static`; this run should
   be the focus of the next exact-equivalent reward-scoring attribution.
4. This evidence is still a projection, not a replay measurement, and it does
   not justify online selector promotion, formal seeds, CAMP retraining, or a
   Full36 replay.

Mathematical boundary: the combined scenarios are hypothetical runtime
savings over fixed current-tick logs. They do not change candidates, atom
values, feasibility masks, weights, affine CAMP scoring, convex master
structure, Benders-style logic, or selected trajectories. Reward-side work is
engineering plumbing only, not a CAMP/Benders subproblem.

Decision: accept combined sensitivity as evidence that the next useful step is
not implementation yet, but reward-scoring internal attribution on the blocker
run and tail rows. Reject `reward 10%`, `reward 25%`, and
`camp atom 50% + reward 25%` as sufficient conservative-gate plans. Do not run
new replays until a concrete exact-equivalent optimization path can plausibly
approach the `reward 50%` projected saving or produce an equivalent combined
margin under the proportional clearance model.

### Reward-Scoring Tail Attribution on Existing Full36 Logs

Commit:

- Local/GitHub/AutoDL CAMP:
  `3f71142aefcb4bd35fb2bdeddf1738c6a4ae6b25`
  (`Add DP reward latency tail audit`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Purpose:

The combined sensitivity audit showed that the conservative projection needs a
roughly `reward 50%`-level saving, or an equivalent combined saving, before a
Full36 rerun would be justified. This audit asks whether the existing Full36
logs already contain reward internal timing evidence that identifies such a
candidate subcomponent.

The audit is read-only. It applies the same clearance projection modes, selects
the over-budget run tails, and attributes `latency_ms_reward_scoring` to the
existing `latency_ms_reward_*` breakdown fields when present. It does not
replay, alter reward values, alter feasibility, alter CAMP atoms, alter
selection, train, or use outcome labels.

Local verification:

```powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
py -3.12 -m pytest `
  camp_core\tests\test_diffusion_planner_reward_latency_tail.py `
  camp_core\tests\test_diffusion_planner_latency_savings_sensitivity.py `
  camp_core\tests\test_diffusion_planner_projected_latency_tail.py `
  camp_core\tests\test_diffusion_planner_clearance_latency_projection.py -q

py -3.12 -m py_compile `
  scripts\integrations\analyze_diffusion_planner_reward_latency_tail.py `
  camp_core\tests\test_diffusion_planner_reward_latency_tail.py

git diff --check
```

Result: `8 passed`; compile and diff checks passed.

AutoDL verification:

```bash
cd /root/autodl-tmp/camp_core
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_reward_latency_tail.py \
  camp_core/tests/test_diffusion_planner_latency_savings_sensitivity.py \
  camp_core/tests/test_diffusion_planner_projected_latency_tail.py \
  camp_core/tests/test_diffusion_planner_clearance_latency_projection.py -q
```

Result: `8 passed`.

Audit command:

```bash
cd /root/autodl-tmp/camp_core
ROOT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/no_outcome_devgrid_57cd0d1
OUT=$ROOT/reward_latency_tail_3f71142

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_reward_latency_tail.py \
  --root "$ROOT" \
  --label no_outcome_full36_reward_latency_tail_3f71142 \
  --reference_old_clearance_p95_ms 9.296867 \
  --reference_new_clearance_p95_ms 0.858788 \
  --reference_source old_exact_off_smoke_vs_vectorized_smoke_sha_88bee7f5494de1cf9ad49cd5c17b772bdd337274f4211ff24f284b2c32d2a140 \
  --output_json "$OUT/reward_latency_tail.json" \
  --output_md "$OUT/reward_latency_tail.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `reward_latency_tail.json` | `56b6765fcc8254f1afc10fa6ed87b0cae5e4df3fa0d0c09bdacaf4902f3e8228` |
| `reward_latency_tail.md` | `9a2059867c8b09417c4c34de884600ae1bb3250c7622e63e183be7800b2a130c` |

Reward-tail attribution summary:

| Projection mode | Runs over budget | Tail rows | Reward scoring mean | Reward scoring p95 | Breakdown sum mean | Residual mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `constant_new_p95` | `4 / 36` | `40` | `47.753345` | `206.013012` | `0.000000` | `47.753345` |
| `cap_at_new_p95` | `4 / 36` | `40` | `47.753345` | `206.013012` | `0.000000` | `47.753345` |
| `scale_by_smoke_p95_ratio` | `4 / 36` | `40` | `47.963396` | `205.847488` | `0.000000` | `47.963396` |

The existing Full36 logs do not contain nonzero reward internal breakdown
fields on the relevant tail rows:

| Scenario | Conservative projected result |
| --- | --- |
| `latency_ms_reward_batch_compute_50pct_saving` | no effect; still `4 / 36` over budget |
| `latency_ms_reward_postprocess_50pct_saving` | no effect; still `4 / 36` over budget |
| `latency_ms_reward_full_horizon_red_light_50pct_saving` | no effect; still `4 / 36` over budget |
| `latency_ms_reward_tensor_setup_50pct_saving` | no effect; still `4 / 36` over budget |
| `all_instrumented_reward_breakdown_50pct_saving` | no effect; still `4 / 36` over budget |
| `reward_unattributed_residual_50pct_saving` | clears projected over-budget runs, but is not an actionable subcomponent |

Interpretation:

1. The old Full36 artifact can show that reward scoring is the large projected
   tail, but it cannot explain which reward subcomponent caused it. All named
   reward breakdown fields are zero on the relevant tail rows.
2. The previously observed `reward 50%` sensitivity is therefore entirely
   `reward_unattributed_residual` on this artifact. Treating it as an
   optimization target would be mathematically and experimentally unsupported.
3. Current code contains reward breakdown timing fields in
   `_score_candidates_with_dp_reward`, so the missing attribution is an artifact
   coverage problem rather than proof that reward internals are irreducible.

Mathematical boundary: this audit is latency attribution only. It does not
change candidate trajectories, reward values, feasibility masks, CAMP atoms,
weights, the affine CAMP score, the convex master, selected trajectories, or
Benders-style logic. Reward timing is engineering plumbing, not a CAMP
subproblem or cut source.

Decision: accept the reward-tail analyzer and existing-artifact audit. Reject
any reward subcomponent optimization decision from the old Full36 logs. The
next admissible step is a single blocker-focused, non-formal,
instrumentation-only smoke using current code to produce nonzero reward
breakdown timings for
`sample_map_tl_route_59_to_86/seed_1/npc_4/tl_off/static`, followed by the same
reward-tail attribution. Do not run a new Full36 matrix, train CAMP, use formal
seeds, or promote an online selector from this evidence.

### Blocker-Focused Reward Breakdown Instrumentation Smoke

Commits:

- Smoke run CAMP commit:
  `da89c50153b05381068667e7ce2d69ad39c61554`
  (`Record DP reward latency tail audit`).
- Reward-tail analyzer enhancement:
  `e02a56bfd46e1735369d9877aa40844e5fc035d4`
  (`Report overall DP reward latency attribution`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Purpose:

This is the blocker-focused, non-formal, instrumentation-only smoke requested
by the previous audit. It reruns only
`sample_map_tl_route_59_to_86/seed_1/npc_4/tl_off/static` with current logging
so reward-scoring latency has nonzero internal breakdown fields. It is not a
12-run, 36-run, formal-seed run, training run, online selector promotion, or DP
change.

Smoke command:

```bash
cd /root/autodl-tmp/camp_core
OUT=/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/reward_breakdown_smoke_da89c50_sample_tl_seed1_npc4_tloff_static

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
REPLAY_NO_PNG=1 \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --map_path /root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm \
  --route /root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --model_path /root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --config /root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json \
  --output_dir "$OUT" \
  --device cuda \
  --advance_mode perfect \
  --steps 200 \
  --seed 1 \
  --max_npcs 4 \
  --spawn_probability 0.3 \
  --traffic_lights off \
  --reward_config /root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json \
  --camp_selector_mode static \
  --camp_atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --camp_static_weights /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/offline_weights_dp_static.npy \
  --num_candidates 8 \
  --candidate_noise_scale 1.0 \
  --candidate_reference_blend_steps 5 \
  --camp_lane_corridor_buffer 1.0 \
  --camp_feasibility_source dp_reward \
  --camp_fallback_mode learned \
  --camp_min_progress_ratio 0.8 \
  --camp_shadow_route_progress \
  --camp_shadow_obstacle_clearance \
  --camp_reward_horizon_steps 30 \
  --camp_outcome_horizon_steps 30 \
  --near_miss_threshold_m 2.0
```

Audit commands:

```bash
AUDIT=$OUT/audit_da89c50

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/audit_diffusion_planner_camp_dataset.py \
  --selection_log "$OUT/camp_selection_log.json" \
  --atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --expected_logs 1 \
  --expected_candidates 8 \
  --expected_advance_mode perfect \
  --closed_loop_outcome_policy forbidden \
  --forbid_seed 11 \
  --forbid_seed 12 \
  --forbid_seed 13 \
  --required_candidate_field candidate_route_progress \
  --require_finite_candidate_contract \
  --output_json "$AUDIT/dataset_audit_reward_breakdown_smoke.json"

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_latency_budget.py \
  --selection_log "$OUT/camp_selection_log.json" \
  --label reward_breakdown_smoke_da89c50_sample_tl_seed1_npc4_tloff_static \
  --output_json "$AUDIT/latency_budget_reward_breakdown_smoke.json" \
  --output_md "$AUDIT/latency_budget_reward_breakdown_smoke.md"

PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/analyze_diffusion_planner_reward_latency_tail.py \
  --selection_log "$OUT/camp_selection_log.json" \
  --label reward_breakdown_smoke_e02a56b_sample_tl_seed1_npc4_tloff_static \
  --reference_old_clearance_p95_ms 9.296867 \
  --reference_new_clearance_p95_ms 0.858788 \
  --reference_source old_exact_off_smoke_vs_vectorized_smoke_sha_88bee7f5494de1cf9ad49cd5c17b772bdd337274f4211ff24f284b2c32d2a140 \
  --output_json "$AUDIT/reward_latency_tail_reward_breakdown_smoke_e02a56b.json" \
  --output_md "$AUDIT/reward_latency_tail_reward_breakdown_smoke_e02a56b.md"
```

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `18c6106e9dca6e5093263a067df2344107ff4e755988dbbfde43a46155492823` |
| `camp_validation_summary.json` | `2a9598c0ab46251449e7bdc47a4d130b5616f33f3a971d5f71dbca49b30843b9` |
| `camp_replay_summary.json` | `e8376e2b2f0a2bc6b74d3e90a826ab93eedae88c74fb855201cd1733a2e91b45` |
| `dataset_audit_reward_breakdown_smoke.json` | `e295bf21c5bc0970a1a9f26a204953470eb1a86e18bbf3ab6efe25f17471e01f` |
| `latency_budget_reward_breakdown_smoke.json` | `98160a548c15a3573baf77b7b4143f89938b3ef2f74155651ff66f86dab1e794` |
| `latency_budget_reward_breakdown_smoke.md` | `c5160f5efc7413a0e50b06ae8917c287b7dd713a487b2a1b7521d4c2ffab0d82` |
| `reward_latency_tail_reward_breakdown_smoke_e02a56b.json` | `f0a69f4884bc65220ff0abcc3a63f110f325131bdd07e78486d414eee0579322` |
| `reward_latency_tail_reward_breakdown_smoke_e02a56b.md` | `b158889bfdcb6e3ddbbe9527977b603be94877ad973662c35471ee8899ad47a8` |

Dataset audit:

- passed `1` log and `200` records;
- `closed_loop_outcome_policy=forbidden`;
- formal seeds `11/12/13` forbidden;
- `candidate_route_progress` required;
- finite-candidate contract required.

Latency summary:

| Metric | P95 |
| --- | ---: |
| `latency_ms_including_candidate_generation` | `99.847964` |
| `latency_ms_reward_scoring` | `29.968980` |
| `latency_ms_reward_batch_compute` | `14.318304` |
| `latency_ms_reward_route_progress` | `6.952000` |
| `latency_ms_reward_sg_smoothing` | `5.285364` |
| `latency_ms_camp_selection` | `8.430465` |
| `latency_ms_shadow_obstacle_clearance` | `0.858692` |

Reward attribution:

The old Full36 logs had zero reward-breakdown fields, but this current-code
smoke has nonzero breakdown fields on all 200 records. The reward residual is
small:

| Quantity | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| `latency_ms_reward_scoring` | `27.838365` | `29.968980` | `215.947859` |
| reward breakdown sum | `27.798792` | `29.923968` | `215.899331` |
| reward unattributed residual | `0.039574` | `0.046726` | `0.058055` |

Top all-record reward components:

| Component | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| `latency_ms_reward_batch_compute` | `13.164841` | `14.318304` | `200.497136` |
| `latency_ms_reward_route_progress` | `6.840850` | `6.952000` | `9.671570` |
| `latency_ms_reward_sg_smoothing` | `5.261901` | `5.285364` | `11.257770` |
| `latency_ms_reward_npz_dump` | `1.851800` | `1.936098` | `4.695484` |
| `latency_ms_reward_tensor_setup` | `0.337449` | `0.349120` | `0.951539` |

The single smoke no longer has an over-budget projected run (`0 / 1` under all
three clearance projection modes), so the reward-tail rows are empty by
definition. For all-record sensitivity, removing half of the instrumented
reward breakdown would project the single run to roughly `84.88-85.65 ms`,
while half of `reward_batch_compute` alone projects roughly `92.23-93.00 ms`.

Interpretation:

1. The current instrumentation is sufficient: reward breakdown nearly accounts
   for all reward scoring latency (`residual p95=0.046726 ms`).
2. The main reward-side targets are now concrete engineering components:
   `reward_batch_compute`, `reward_route_progress`, and `reward_sg_smoothing`.
3. This single smoke passes the `100 ms` per-run p95 target with very little
   margin (`99.847964 ms`). It is useful instrumentation evidence, not a
   development-grid pass.
4. Because the old Full36 logs lack reward breakdown fields, these component
   proportions cannot be safely projected across all 36 runs without a broader
   instrumentation artifact.

Mathematical boundary: this smoke and attribution do not change DP, candidate
generation, postprocessing, PerfectTracker, CAMP atoms, weights, feasible sets,
the affine score, the convex master, or any Benders-style logic. Reward timing
is engineering latency plumbing only.

Decision: accept the blocker smoke as proof that current-code reward
breakdown instrumentation is usable. Reject Full36 rerun, online selector
promotion, CAMP retraining, and formal seeds from this single-smoke evidence.
The next admissible step is an exact-equivalent reward-latency engineering plan
or microbenchmark for `reward_batch_compute`, `reward_route_progress`, and
`reward_sg_smoothing`; only after a concrete exact-equivalent plan projects
enough margin under the conservative model should a broader non-formal replay
be considered.

### Exact-Equivalent Reward SG Smoothing Optimization

Commit:

- CAMP commit:
  `02c158316e236081de82598eee41d10edad3a6c5`
  (`Vectorize DP reward SG smoothing`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Purpose:

The prior blocker smoke identified three reward-side latency targets:
`reward_batch_compute`, `reward_route_progress`, and `reward_sg_smoothing`.
This iteration implements only the exact-equivalent `reward_sg_smoothing`
change. The previous reward path converted candidates to `float32` and applied
Diffusion Planner's Savitzky-Golay smoothing one candidate at a time. The new
path uses the already-tested batch-axis smoothing helper on the same `float32`
candidate tensor, preserving the same Savitzky-Golay window/order and heading
renormalization.

Local equivalence and microbenchmark:

```text
python -m pytest \
  camp_core/tests/test_diffusion_planner_integration.py::test_tracker_reference_candidates_apply_replay_savgol_preprocessing \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_scoring_candidates_match_previous_per_candidate_savgol \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_scoring_candidates_preserve_disabled_copy_semantics \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_reward_latency_tail.py \
  camp_core/tests/test_diffusion_planner_latency_budget.py -q
```

Result: `12 passed`. A local synthetic SG-only microbenchmark over an `8 x 80 x
4` candidate tensor had exact output equality (`max_abs_error=0`) and reduced
SG p95 from about `3.460600 ms` to about `0.803575 ms`. This local benchmark is
development evidence only; the replay smoke below is the relevant AutoDL
runtime check.

Rejected route-progress attempt:

An exact scalar-to-batched route-progress projection was prototyped but not
committed. On a synthetic long-route case (`8 x 30` candidate points and about
`5000` route segments), it had exact equality but was slower:

| Variant | Median | P95 |
| --- | ---: | ---: |
| scalar route progress | `50.123300 ms` | `54.043850 ms` |
| batched route progress | `92.215250 ms` | `96.973700 ms` |

Decision: reject this route-progress implementation. `reward_route_progress`
remains a real target, but it needs a different design and a real-snapshot
microbenchmark before code changes.

AutoDL verification:

- AutoDL CAMP after sync:
  `02c158316e236081de82598eee41d10edad3a6c5`.
- AutoDL DP:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Remote targeted tests: `12 passed`.

Non-formal smoke:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/
  reward_sg_vectorized_smoke_02c1583_sample_tl_seed1_npc4_tloff_static
```

This reruns only
`sample_map_tl_route_59_to_86/seed_1/npc_4/tl_off/static` with the same
development setup as the previous reward-breakdown smoke. It is not a Full36
run, online selector promotion, formal-seed run, CAMP training run, or DP
change.

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `ed1a17e6f590951e844bd2622c622c7e107e393e45e9fe648cff4aa6b03d0eea` |
| `camp_validation_summary.json` | `99dd6c2310ec6658429008c6485167781e30ed465aa02ab46988f14ae929ff2e` |
| `camp_replay_summary.json` | `6abdbc7302edb3112464e07e1aeb253475ef181676bd8d41c7012dbe43a8111d` |
| `dataset_audit_reward_sg_vectorized_smoke.json` | `1c0a8eba7651cef50969e707839636942512863fcee4952272e6d7bca7a2a46f` |
| `latency_budget_reward_sg_vectorized_smoke.json` | `2bd38964f85a2610c2962c83f7f17d14ac24131ce1eabdc2b9d77f0a7adcc915` |
| `latency_budget_reward_sg_vectorized_smoke.md` | `283c7b912a52faee4f551c7e0062c08c3817dad8acc29fd76f92f0bee1af1cd1` |
| `reward_latency_tail_reward_sg_vectorized_smoke.json` | `48d34822be5cf0d4cfc74ae865affa88cd6230e0279b080e8a5f8e84ba19d441` |
| `reward_latency_tail_reward_sg_vectorized_smoke.md` | `21102468401c500e24b318fd5da5d6089f81734d23080a056ad7304b1694c625` |
| `selector_equivalence_vs_reward_breakdown_smoke.json` | `0a680a50059a81659a870a66eb3e36f0d0df830c83068398d5b893e02d6a9ead` |
| `non_latency_tolerance_summary_vs_reward_breakdown_smoke.json` | `d98dc6df47f95f3a5fdf18ab3c5b8d3b14f9c27781fdb605a68f90b76b1f346f` |

Dataset and equivalence audits:

- dataset audit passed `1` log and `200` records;
- `closed_loop_outcome_policy=forbidden`;
- formal seeds `11/12/13` forbidden;
- `candidate_route_progress` required;
- finite-candidate contract required;
- selector equivalence versus the previous reward-breakdown smoke passed with
  exact equality for selected index, feasible mask, infeasibility reasons,
  atoms, normalized atoms, scores, weights, and selection scores;
- non-latency record comparison had no nonnumeric mismatches and maximum
  numeric difference `7.593925488436071e-14`, limited to
  `candidate_perfect_tracker_open_loop_rollout` and
  `candidate_perfect_tracker_postprocessed_reference_prefix`.

Latency summary:

| Metric | Previous smoke P95 | SG-vectorized smoke P95 |
| --- | ---: | ---: |
| `latency_ms_including_candidate_generation` | `99.847964` | `97.684553` |
| `latency_ms_reward_scoring` | `29.968980` | `27.691599` |
| `latency_ms_reward_sg_smoothing` | `5.285364` | `0.467413` |
| `latency_ms_reward_batch_compute` | `14.318304` | `15.684527` |
| `latency_ms_reward_route_progress` | `6.952000` | `6.941473` |
| `latency_ms_camp_selection` | `8.430465` | `8.722617` |
| `latency_ms_shadow_obstacle_clearance` | `0.858692` | `0.865972` |

The total per-run p95 is now below `100 ms` with about `2.315447 ms` margin for
this single smoke. This is a positive engineering result but still not enough
for the development gate because it is one run and the old Full36 logs cannot
be retroactively upgraded into current-code reward-breakdown evidence.

Reward attribution after SG vectorization:

| Quantity | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| `latency_ms_reward_scoring` | `22.993297` | `27.691599` | `180.833546` |
| reward breakdown sum | `22.954007` | `27.655440` | `180.791772` |
| reward unattributed residual | `0.039290` | `0.044433` | `0.096203` |

Top all-record reward components:

| Component | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| `latency_ms_reward_batch_compute` | `13.070546` | `15.684527` | `170.443398` |
| `latency_ms_reward_route_progress` | `6.906255` | `6.941473` | `12.855146` |
| `latency_ms_reward_npz_dump` | `1.859383` | `1.962090` | `2.892023` |
| `latency_ms_reward_sg_smoothing` | `0.466525` | `0.467413` | `3.109545` |
| `latency_ms_reward_tensor_setup` | `0.336077` | `0.340647` | `1.209443` |

All three clearance projection modes still have `0` over-budget runs for this
single smoke and `0` reward-tail rows.

Mathematical boundary: this change does not modify DP candidate generation,
Savitzky-Golay parameters, `postprocess_reference`, PerfectTracker semantics,
CAMP atoms, atom normalization, affine scores, feasible masks, simplex/CVaR/L2
master logic, or the finite-candidate selector. It only changes the mechanical
implementation of an already-required current-tick smoothing operation from a
Python per-candidate loop to a batch-axis SciPy call with exact tested equality.
This is latency plumbing, not Benders, and it creates no new master/subproblem,
duals, or cuts.

Decision: accept the SG vectorization as an exact-equivalent latency
improvement. Reject route-progress vectorization as currently implemented.
Reject Full36 replay, online selector promotion, formal seeds, and CAMP
retraining from this one-run smoke. The next admissible step is to design an
exact-equivalent plan for either `reward_batch_compute` or `reward_route_progress`
using real snapshot microbenchmarks and selector-equivalence checks before any
broader non-formal replay.

### Exact-Equivalent Route Progress Projection Slice

Commit:

- CAMP commit:
  `58f132cdc5dde44fe0a8db3d6ae93c0392d2c746`
  (`Slice DP route progress projection`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Purpose:

The previous SG iteration left `reward_route_progress` as the second largest
reward-side component. This iteration does not change the route-progress
definition. It computes the same full-route cumulative arc lengths first, then
uses the existing conservative `exact_centerline_slice_for_candidates` helper
to restrict the nearest-segment search to a contiguous route segment slice.
Each point arc is still evaluated with the original scalar point-to-segment
projection and the full-route cumulative start value for the winning segment.

Local equivalence and synthetic benchmark:

```text
python -m pytest \
  camp_core/tests/test_diffusion_planner_integration.py::test_candidate0_route_progress_guard_uses_route_projection \
  camp_core/tests/test_diffusion_planner_integration.py::test_candidate_route_progress_preserves_scalar_projection \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_scoring_candidates_match_previous_per_candidate_savgol \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_reward_latency_tail.py \
  camp_core/tests/test_diffusion_planner_latency_budget.py -q
```

Result: `12 passed`. A local synthetic benchmark compared the previous scalar
route-progress implementation with the sliced implementation over route lengths
from `200` to `20000` segments. All cases were exactly equal by
`np.array_equal`; selected timing rows:

| Route segments | Previous P95 | Sliced P95 |
| --- | ---: | ---: |
| `200` | `6.116910 ms` | `5.670350 ms` |
| `1000` | `16.350755 ms` | `10.832710 ms` |
| `5000` | `50.870975 ms` | `28.728105 ms` |
| `20000` | `318.839445 ms` | `142.096980 ms` |

AutoDL verification:

- AutoDL CAMP after sync:
  `58f132cdc5dde44fe0a8db3d6ae93c0392d2c746`.
- AutoDL DP:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Remote targeted tests: `12 passed`.

Non-formal smoke:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/
  reward_route_sliced_smoke_58f132c_sample_tl_seed1_npc4_tloff_static
```

This reruns only
`sample_map_tl_route_59_to_86/seed_1/npc_4/tl_off/static` with the same
development setup as the prior SG-vectorized smoke. It is not a Full36 run,
online selector promotion, formal-seed run, CAMP training run, or DP change.

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `1b1a96205652e806ba83ac952bf47e2678ecdfaaab246f57a69a319abf6d35e9` |
| `camp_validation_summary.json` | `16c12ec0959eff93e42ed4fb3eef6893452d5a0c7f2de9fe53ac6b53604508d8` |
| `camp_replay_summary.json` | `aa957f748136bb9232698b788920c3bb40e00768e025c7403f306ae74a6def4b` |
| `dataset_audit_reward_route_sliced_smoke.json` | `3ad4d7a9cf6757352382ac132336d8206311ee23226c80157ba966702f23d576` |
| `latency_budget_reward_route_sliced_smoke.json` | `4791f3abaedaa48a7c62e5e66fffa18973ef1264554955e1594af1259fa457c9` |
| `latency_budget_reward_route_sliced_smoke.md` | `db6369d19a15275338ebe2cd97d0e0a08db33733392df2fe117864be75b112ca` |
| `reward_latency_tail_reward_route_sliced_smoke.json` | `3b06c7f616baa9659044f01e23351fc6cee21e63eac71b1fa7fc34676106f5ab` |
| `reward_latency_tail_reward_route_sliced_smoke.md` | `50301344bc68b9cf0022f5ecaf941c387af68d32f474e57986e3b2e8f834485d` |
| `selector_equivalence_vs_reward_sg_vectorized_smoke.json` | `2dfd16a7f7923771a169a2e04f750b7c3be7ce3603315014ac1aeca368818c2a` |
| `non_latency_tolerance_summary_vs_reward_sg_vectorized_smoke.json` | `e4d4247b95b0eeaa5295b7976357d04c0d89a82d362bd631c831e6c84f6dcf86` |

Dataset and equivalence audits:

- dataset audit passed `1` log and `200` records;
- `closed_loop_outcome_policy=forbidden`;
- formal seeds `11/12/13` forbidden;
- `candidate_route_progress` required;
- finite-candidate contract required;
- selector equivalence versus the SG-vectorized smoke passed with exact
  equality for selected index, feasible mask, infeasibility reasons, atoms,
  normalized atoms, scores, weights, and selection scores;
- non-latency record comparison had no nonnumeric mismatches and maximum
  numeric difference `7.593925488436071e-14`, again limited to
  `candidate_perfect_tracker_open_loop_rollout` and
  `candidate_perfect_tracker_postprocessed_reference_prefix`.

Latency summary:

| Metric | SG-vectorized smoke P95 | Route-sliced smoke P95 |
| --- | ---: | ---: |
| `latency_ms_including_candidate_generation` | `97.684553` | `95.908343` |
| `latency_ms_reward_scoring` | `27.691599` | `25.502188` |
| `latency_ms_reward_sg_smoothing` | `0.467413` | `0.465225` |
| `latency_ms_reward_batch_compute` | `15.684527` | `15.477383` |
| `latency_ms_reward_route_progress` | `6.941473` | `4.162828` |
| `latency_ms_camp_selection` | `8.722617` | `8.607626` |
| `latency_ms_shadow_obstacle_clearance` | `0.865972` | `0.837803` |

The total per-run p95 is now below `100 ms` with about `4.091657 ms` margin for
this single smoke. This is still one non-formal run only.

Reward attribution after route slicing:

| Quantity | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| `latency_ms_reward_scoring` | `20.176211` | `25.502188` | `176.000200` |
| reward breakdown sum | `20.136037` | `25.467786` | `175.961761` |
| reward unattributed residual | `0.040174` | `0.045843` | `0.386590` |

Top all-record reward components:

| Component | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| `latency_ms_reward_batch_compute` | `13.188276` | `15.477383` | `168.300051` |
| `latency_ms_reward_route_progress` | `3.988696` | `4.162828` | `8.021023` |
| `latency_ms_reward_npz_dump` | `1.849583` | `1.979898` | `6.629891` |
| `latency_ms_reward_sg_smoothing` | `0.454681` | `0.465225` | `0.530813` |
| `latency_ms_reward_tensor_setup` | `0.335974` | `0.350137` | `0.629492` |

All three clearance projection modes still have `0` over-budget runs for this
single smoke and `0` reward-tail rows.

Mathematical boundary: this change does not alter DP candidate generation,
Savitzky-Golay smoothing, `postprocess_reference`, PerfectTracker semantics,
CAMP atoms, atom normalization, affine scores, feasible masks, simplex/CVaR/L2
master logic, or the finite-candidate selector. `candidate_route_progress`
remains a fixed current-tick diagnostic over a fixed route polyline and fixed
candidate tensor. The slice is a conservative exact search-domain reduction,
not an approximation and not a learned feature. This is latency engineering,
not Benders, and it constructs no master/subproblem, dual, or cuts.

Decision: accept the route-progress slice as an exact-equivalent latency
improvement. Reject Full36 replay, online selector promotion, formal seeds, and
CAMP retraining from this one-run smoke. The next admissible step is now
`reward_batch_compute`: inspect whether any exact-equivalent wrapper-side data
preparation or microbenchmark can reduce/attribute the remaining DP reward
compute cost without modifying DP or changing reward semantics.

### Reward Batch Contiguous Horizon Tensor

Commit:

- CAMP commit:
  `bd512256ee6b82dd7dd96b34331ffcc945d1db66`
  (`Optimize DP reward horizon tensor`).
- DP remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Purpose:

The route-sliced smoke left `latency_ms_reward_batch_compute` as the largest
reward-internal p95 component. Inspection of the fixed DP reward source showed
that `compute_reward_batch` is already decorated with `@torch.no_grad()`, so
adding another `no_grad` wrapper is not a useful optimization. The wrapper-side
candidate was instead to pass the near-horizon reward tensor as a contiguous
tensor and call the fixed DP reward functions under `torch.inference_mode()`.

The implementation changes only
`scripts/integrations/run_diffusion_planner_camp_replay.py`:

- `full_trajectories[:, :reward_horizon_steps]` is materialized as a contiguous
  near-horizon tensor before calling the fixed DP reward scorer;
- `compute_reward_batch` and `compute_red_light_score_batch` are called under
  `torch.inference_mode()`;
- DP reward code, reward config, candidate generation, SG smoothing,
  `postprocess_reference`, PerfectTracker, CAMP atoms, normalization, affine
  scores, feasible masks, simplex/CVaR/L2 master logic, and selector rules are
  unchanged.

Pre-implementation fixed-snapshot probes:

```text
/root/autodl-tmp/camp_dp_reward_batch_contiguous_probe_53e4240.json
/root/autodl-tmp/camp_dp_reward_batch_inference_probe_53e4240.json
```

Both probes used the eight fixed component snapshots from
`/root/autodl-tmp/camp_dp_component_microbenchmark_f9baa9f/snapshots`.
The contiguous/inference probe reported zero output error for reward
breakdowns and full-horizon red-light scores. Its aggregate p95-of-snapshot-p95
rows were:

| Variant | p95 of snapshot p95 | Delta vs view |
| --- | ---: | ---: |
| view reward | `11.059199 ms` | `0.000000 ms` |
| view reward under inference mode | `11.168390 ms` | `+0.109191 ms` |
| contiguous copy plus reward under inference mode | `10.208615 ms` | `-0.850584 ms` |

The earlier contiguous-only probe was mixed: contiguous compute-only was worse
at p95, while copy-plus-compute looked better. Therefore the accepted code path
is justified only as the combined contiguous near-horizon tensor plus inference
mode path, and still requires replay-level validation.

Verification:

Local targeted tests:

```text
PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core python -m pytest \
  camp_core/tests/test_diffusion_planner_integration.py::test_candidate0_route_progress_guard_uses_route_projection \
  camp_core/tests/test_diffusion_planner_integration.py::test_candidate_route_progress_preserves_scalar_projection \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_scoring_candidates_match_previous_per_candidate_savgol \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_scoring_candidates_preserve_disabled_copy_semantics \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_horizon_trajectories_are_contiguous \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_reward_latency_tail.py \
  camp_core/tests/test_diffusion_planner_latency_budget.py -q
```

Result: `13 passed, 1 skipped`.

AutoDL sync note: the commit was pushed to GitHub from the local machine. AutoDL
could not fetch GitHub directly during this step because its HTTPS connection to
GitHub timed out, so the same Git commit was transferred with a verified Git
bundle and applied by `git fetch <bundle> main` plus `git merge --ff-only
FETCH_HEAD`. AutoDL HEAD became
`bd512256ee6b82dd7dd96b34331ffcc945d1db66`; its local `origin/main` reference
remained stale until network access recovers.

Remote targeted tests:

```text
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest \
  camp_core/tests/test_diffusion_planner_integration.py::test_candidate0_route_progress_guard_uses_route_projection \
  camp_core/tests/test_diffusion_planner_integration.py::test_candidate_route_progress_preserves_scalar_projection \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_scoring_candidates_match_previous_per_candidate_savgol \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_scoring_candidates_preserve_disabled_copy_semantics \
  camp_core/tests/test_diffusion_planner_integration.py::test_reward_horizon_trajectories_are_contiguous \
  camp_core/tests/test_diffusion_planner_component_benchmark.py \
  camp_core/tests/test_diffusion_planner_reward_latency_tail.py \
  camp_core/tests/test_diffusion_planner_latency_budget.py -q
```

Result: `14 passed`.

Non-formal smoke:

```text
/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/
  reward_batch_contiguous_smoke_bd51225_sample_tl_seed1_npc4_tloff_static
```

This reruns only
`sample_map_tl_route_59_to_86/seed_1/npc_4/tl_off/static` with the same setup
as the route-sliced smoke. It is not a Full36 run, online selector promotion,
formal-seed run, CAMP training run, or DP change.

Artifact SHA:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `e0a03f0aba669f611e2eb2e1281cbf88f0c2f8bf780d20250791e1f87d4c84f7` |
| `camp_validation_summary.json` | `411c6a1491139c542c3be292be330a8f3c2ff4cc8199fc1d3652eff4054173bf` |
| `camp_replay_summary.json` | `97ac6b7c6d50fe2e3a7d04477e57c46b59b793fafd3af3cd071e0c91910ff238` |
| `dataset_audit_reward_batch_contiguous_smoke.json` | `5bd2c44d4aa7c6d04a38ab6072ff3aaf11825b9497fad2742f0e0f7574c5369a` |
| `latency_budget_reward_batch_contiguous_smoke.json` | `3cc4caac5eef3f7e714a2582382d52de6d98e4e0bc2fe0a3e27e09994fb1cb29` |
| `latency_budget_reward_batch_contiguous_smoke.md` | `7d35fd0036e5d7e57879bd72c01e4cd01a3d87a49a739bfaae6327ca9c4ab338` |
| `reward_latency_tail_reward_batch_contiguous_smoke.json` | `d14b709eabc3669ba13fdd53b343630f666f138e0e8e4ef9213c179bceec2757` |
| `reward_latency_tail_reward_batch_contiguous_smoke.md` | `7ed89e231f139dc423494a195907cf76fb6434e5189784b4a8fe7cd0ce799185` |
| `selector_equivalence_vs_reward_route_sliced_smoke.json` | `097d11d45fdcc28d72ef2d0d0573043b069df721afa7868d9b5c366447f00661` |
| `non_latency_tolerance_summary_vs_reward_route_sliced_smoke.json` | `fde188d6d6e3a0898220191cfbb989706c027aafaed1c209ea84bccb1b4010b4` |
| `camp_dp_reward_batch_contiguous_probe_53e4240.json` | `f15835ceebe5706a58a98f933df4f1db69c7b9aeba4bbc6ad986dd87abf671c6` |
| `camp_dp_reward_batch_inference_probe_53e4240.json` | `31665a8cfbbf86d7f82595d157e19e089fdea8418c202b30c7a26d1602ac5d92` |

Dataset and equivalence audits:

- dataset audit passed `1` log and `200` records;
- `closed_loop_outcome_policy=forbidden`;
- formal seeds `11/12/13` forbidden;
- `candidate_route_progress` required;
- finite-candidate contract required;
- selector equivalence versus the route-sliced smoke passed with exact equality
  for selected index, feasible mask, infeasibility reasons, atoms, normalized
  atoms, scores, weights, and selection scores;
- non-latency behavior comparison excluding only latency and run-location path
  metadata passed across selection, metric, evaluation-state, trajectory,
  clearance, replay-summary, and validation-summary logs; maximum numeric
  difference was `6.927791673660977e-14`.

Latency summary:

| Metric | Route-sliced smoke P95 | Reward-contiguous smoke P95 |
| --- | ---: | ---: |
| `latency_ms_including_candidate_generation` | `95.908343` | `91.460901` |
| `latency_ms_reward_scoring` | `25.502188` | `20.847928` |
| `latency_ms_reward_batch_compute` | `15.477383` | `13.253058` |
| `latency_ms_reward_candidate_tensor_transfer` | not separately material | `0.088606` |
| `latency_ms_reward_sg_smoothing` | `0.465225` | `0.457779` |
| `latency_ms_reward_route_progress` | `4.162828` | `4.166758` |
| `latency_ms_reward_full_horizon_red_light` | not separately emphasized | `0.130974` |
| `latency_ms_camp_selection` | `8.607626` | `8.592079` |
| `latency_ms_shadow_obstacle_clearance` | `0.837803` | `0.860980` |

The total p95 margin in this single smoke is about `8.539099 ms` below the
`100 ms` tick budget. The strict behavior-equivalence audits mean the lower
latency does not come from a selector, feasibility, atom, or trajectory change.

Reward attribution after the contiguous reward-horizon change:

| Quantity | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| `latency_ms_reward_scoring` | `19.007363` | `20.847928` | `204.855124` |
| reward breakdown sum | `18.967621` | `20.810198` | `204.811327` |
| reward unattributed residual | `0.039742` | `0.046410` | `0.229876` |

Top all-record reward components:

| Component | Mean | P95 | Max |
| --- | ---: | ---: | ---: |
| `latency_ms_reward_batch_compute` | `12.027755` | `13.253058` | `196.980607` |
| `latency_ms_reward_route_progress` | `3.963517` | `4.166758` | `5.647108` |
| `latency_ms_reward_npz_dump` | `1.824806` | `1.941595` | `2.490368` |
| `latency_ms_reward_sg_smoothing` | `0.453679` | `0.457779` | `1.458010` |
| `latency_ms_reward_tensor_setup` | `0.335602` | `0.338426` | `1.890818` |

Closed-loop behavior for this smoke remained the same under the non-latency
audit. Key values: route completion `0.12775767335529134`, planned red-light
violation rate `0.0`, realized red-light violation rate `0.0`, mean absolute
jerk `7.4446096113233855`, mean lateral acceleration
`0.23776163436030362`, fallback rate `0.35`, and candidate feasible rate
`0.56375`.

Mathematical boundary: this change is exact-equivalent latency plumbing over
fixed current-tick tensors. It does not modify the finite candidate set, DP
reward definition, reward horizon, full-red diagnostic, SG smoothing,
post-processing, PerfectTracker state transition, CAMP atom schema, atom
normalization, affine score \(a_k^\top w\), feasible mask semantics, fallback
policy, or simplex/CVaR/L2 master. It also does not construct a classical
Benders master/subproblem pair, dual, or cuts. The DP-side finite selector
remains a finite-candidate selector; CAMP's logged robust training claim
remains limited to fixed candidates with fixed atoms and oracle margins.

Decision: accept the contiguous reward-horizon tensor plus inference-mode
wrapper as an exact-equivalent latency improvement. Reject Full36 replay,
online selector promotion, formal seeds, and CAMP retraining from this single
smoke. The next admissible step is to rerun a small paired development grid
only after deciding whether this latency margin is sufficient, or to continue
component-level diagnosis of the remaining stable terms (`reward_batch_compute`
and candidate generation) without changing DP.
