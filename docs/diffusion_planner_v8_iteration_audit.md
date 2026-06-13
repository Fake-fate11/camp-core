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
- recollect the 36-run training matrix under perfect tracking and retrain
  before any formal evaluation;
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

## Formal Evaluation Gate

Do not run seeds 11, 12, and 13 yet. First recollect the 36-run Uniform dataset
with explicit perfect tracking, mode metadata, 12D schema checks, complete
candidate outcomes, and the selection-neutral shadow diagnostic. Retrain and
repeat the grouped validation, fallback ablation, development matrix, and
latency/equivalence gates on that distribution. Only a frozen design that
improves development evidence without safety or completion regression may
consume the formal seeds once.
