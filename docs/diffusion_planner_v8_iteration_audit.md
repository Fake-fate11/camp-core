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
