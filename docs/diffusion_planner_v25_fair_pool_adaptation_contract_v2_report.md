# V25 Fair-Pool Adaptation Contract v2 Executability Report

## Outcome and scope

The versioned
`camp_dp_v25_fair_pool_adaptation_contract_v2` and its separate-role
independent semantic review are sealed and PASS. This package closes only the
pre-acquisition contract-executability gap. It authorizes no acquisition,
model, pool, selector, closed-loop, Fresh, holdout, training, retraining,
claim, promotion, or deployment run.

The qualification scope is machine-limited to one
`four_track_highway` map, one ordered route, four density tiers, 64
development-calibration states, and 64 independent-validation states. A future
PASS would mean only that evidence in this bounded single-route scope did not
trigger retraining. It would not establish general architecture equivalence,
OOD coverage, benefit, or safety.

The v1 contract roots remain sealed as a superseded pre-acquisition
diagnostic. No v1 artifact, prior validation artifact, Fresh artifact, or CAS
was changed.

## Executable input-only manifest contract

The versioned materializer is
`camp_core/camp_core/integrations/diffusion_planner_v25_fair_pool_input_manifest.py`,
SHA
`33f5ea5eb6d92757fbb408e318eccd04048265a295871c9862f1ca539a98bfb6`.
It implements:

- exact source-record fields and units with unknown-field rejection;
- finite checks, half-away-from-zero 1 mm position/dimension and 0.001 m/s
  speed quantization;
- heading wrap to `[-pi, pi)` and 1e-4 rad quantization;
- ordered piecewise-linear 0.5 m route resampling with the exact final
  endpoint, no padding, and rejection of segments no longer than 1e-12 m;
- deterministic actor ordering and an explicit empty-list rule;
- canonical ASCII JSON with sorted keys, compact separators, no NaN, and one
  trailing LF;
- input-only clone payload and clone-key SHA generation;
- exact 64+64 preflight receipt validation before the first model, pool, or
  selector call.

The forbidden Fresh B4 source is the accepted preopen root
`bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829`.
Its `fresh_b4_prepared_runtime_cases.json` file SHA is
`e67fee3309f822c80605b3e9b00009d2ae3e27139e36396d009b9a2b306535a2`
and contains 100 outcome-blind prepared scenario inputs. The extractor binds
map source, start/goal pose, ordered world route, sorted initial actors, and
semantic source content into 100 ID-free forbidden clone keys. The future
preflight must bind the derived forbidden-manifest SHA and prove all four
intersections empty: within calibration, within validation, across the two
splits, and both splits against B4. Any collision aborts with no drop,
replacement, or suffix.

Actual development input/state/latent manifests have not been materialized in
this design stage: count=0. The contract freezes their exact source schema,
state order, map/route authority, sampler fingerprint, materialization steps,
and preflight receipt schema for a future separately authorized acquisition.

## Required endpoint registry

The registry contains 37 unique required endpoints:

| Family | Required endpoints | Units / shape |
|---|---:|---|
| normalized atoms | 14 individually named/indexed atoms | training-scale normalized, `[8,14]` pair |
| ego trajectory | position, wrapped heading, speed | `[8,80,*]` pair |
| neighbor trajectory | position, wrapped heading, speed | `[8,A,80,*]` pair |
| Static14D | score absolute/normalized delta, margin ratio, rank error, mask, selected action | score `[8]`, mask `[8]`, action `[80,4]` |
| Scene14D | score absolute/normalized delta, margin ratio, rank error, mask, selected action | score `[8]`, mask `[8]`, action `[80,4]` |
| global gates | neighbor inflation, K8 finite/diverse, authority, tensor/zero-call, clone nonoverlap | typed exact receipts |

Every registry row freezes its formula, units, input shape, applicability,
finite/missing policy, resolution floor, within-mode pair topology, matched
cross-mode topology, per-state reduction, and 64-state no-drop denominator.
Unknown or omitted endpoints fail closed.

The 14 atom scales bind training root
`8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9`,
`runtime_atom_scales.json` SHA
`72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb`,
and each literal name/index/value. Zero or nonfinite scales are authority
failures.

## Frozen threshold mathematics

Each mode has five repeats and all ten unordered within-mode pairs. Cross-mode
pairs are repeat-index matched and are entered only after both within-mode
vectors pass.

For numeric endpoints, per-pair errors are reduced within state by empirical
q99 with the `higher` rule. Exactly 64 calibration state statistics feed a
10,000-resample state bootstrap with replacement using NumPy
`Generator(PCG64DXSM(825071))`. Indices are generated as
`integers(0,64,size=(10000,64),endpoint=False,dtype=int64)`. Each resample uses
sorted index 63; the one-sided 95% percentile uses sorted bootstrap index
9500. The frozen threshold is the maximum of that value and the endpoint's
literal resolution floor.

Validation uses exactly 64 states. Equality passes: an error is an exceedance
only when it is strictly greater than the threshold. The one-sided 95%
Clopper-Pearson upper bound is:

- `1 - 0.05**(1/n)` when `k=0`;
- `scipy.stats.beta.ppf(0.95, k+1, n-k)` when `0<k<n`;
- `1.0` when `k=n`.

PASS requires `k<=2` and the upper bound `<=0.10`. Missing, nonfinite, wrong
shape, or any denominator other than 64 blocks rather than shrinking the
sample.

## Score, rank, action, and decision semantics

Static and Scene thresholds are separately owned by arm and mode. Lower score
is better. Margin is eligible runner-up minus eligible best. Fewer than two
shared eligible candidates is ambiguous/evidence-missing. Exact score ties
use average ranks and the smallest eligible row index. Constant vectors are
rank-computable only when both vectors are elementwise equal; otherwise rank
evidence is missing. All score/margin/inflation denominators have positive
literal floors and NaN/Inf blocks.

Action comparison has exactly 80 rows ordered
`[x_m,y_m,heading_rad,speed_mps]`, 0.1 s index-aligned samples, no
interpolation, wrapped heading difference, and finite-only values. A flipped
selection is descriptively action-equivalent only when maximum XY error is
`<=0.05 m`, heading error `<=0.01 rad`, speed error `<=0.05 m/s`, and the
executable and terminal enums match. A flip is neither automatically failed
nor automatically excused.

The decision consumes the exact 37-endpoint keyset. It blocks in the order
authority failure, evidence missing, within-mode generator instability, then
cross-mode functional drift. There is no weighted total. The old 1e-5
single-float neighbor veto remains superseded; it is not part of v2.

## Independent review and adversarial TDD

The reviewer imports neither the producer contract, the input-manifest
materializer, nor their threshold/decision tables. Reviewer-local literals
reconstruct the two 64-state manifests, source and clone schemas, B4 source
binding, endpoint table, resolution floors, repeat topology, training-scale
index, bootstrap, Clopper-Pearson, rank/tie rules, action rules, full decision
table, and zero-run boundary. The full payload pin is retained as an
additional byte-level lock.

The 21-test focused suite proves route endpoint and quantization behavior,
synthetic 100-key B4 extraction, 64+64 zero-overlap preflight, reproducible
bootstrap, CP `k=0/2/3`, equality boundaries, tie/constant/missing rank cases,
80x4 action wrap/threshold/status cases, endpoint omission/unknown rejection,
and block precedence. Adversarial tests repoint the reviewer payload pin to a
rehash of each mutation and still require the independent semantic oracle to
reject changed q, bootstrap, CP, floor, state/split/repeat, scale, margin/tie,
action, decision, endpoint, scope, and claim fields.

## Immutable scientific boundary

The prior programmatic HARD STOP and its reverse functional evidence remain
unchanged. The current classification remains
`overconservative_equivalence_contract_triggered; functional adaptation risk
unresolved`. This contract does not prove architecture/model failure,
training-distribution or OOD drift, or a need to retrain.

`acquisition_authorized=false`. Actual input-manifest materialization,
calibration, repeat-model, pool, selector, closed-loop, Fresh, holdout, and
training counts are all zero. No B4/Fresh outcome was read. No old artifact or
CAS was written. The legacy claim remains
`honest_no_claim_under_frozen_preregistered_all_gate`.
