# V25 Fair-Pool Adaptation Qualification Contract v1

## Decision

This package freezes a prospective, outcome-independent qualification contract.
It does **not** authorize acquisition. No model, repeat, candidate pool,
selector, closed loop, Fresh/holdout, or training run occurred.

The preserved classification remains:

`overconservative_equivalence_contract_triggered; functional adaptation risk unresolved`

The earlier 1e-5 neighbor rule remains a valid programmatic HARD STOP for its
own run, but it is not a scientific conclusion that batch8 is wrong, the model
failed, an OOD/training-distribution shift occurred, or retraining is required.
The preserved reverse evidence remains 128/128 ego trajectories, 16/16 masks,
and 16/16 selected indices for both Static14D and Scene14D.

## Sealed authority

- Schema: `camp_dp_v25_fair_pool_adaptation_contract_v1`
- Implementation HEAD: `9cb22ec1c51666d40bb1c22dba220d55809eeb36`
- Fixed DP HEAD: `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Contract:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_9cb22ec1_8680c1b19ce0620b`
- Contract root:
  `b2de5b71509526407e102b3ba3aec74000290f13ab75918d0008596a6b52f824`
- Independent review:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_review_9cb22ec1_8680c1b19ce0620b`
- Review root:
  `a16a523766493826d6b5b3f4e0a8188a1019571e4491a53e3149af2bb408aa37`
- Focused receipt:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_focused_9cb22ec1_8680c1b19ce0620b`
- Focused root:
  `a0db3bc9ae56089d635372262bb8d12346869a48ac675c2e10fda50aa9ffcea3`
- Focused result: 24/24 passed.

## Exact split manifest

The contract contains 128 state specifications, not acquired states:

| Split | State specifications | Ordinals | Independent unit |
|---|---:|---|---|
| development calibration | 64 | 0-63 | state |
| independent validation | 64 | 64-127 | state |

Each split has exactly 16 states in each of the four predeclared tiers:
`no_npc`, `low_density`, `medium_density`, and `high_density`. All use the
development/nonholdout four-track-highway source, route SHA
`63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd`,
and map SHA
`c13a9234727186c77c019766c3358c30faf10af61503a566f0fff0963be53bbd`.
Scenario and latent seeds are literal per-state fields. Rows and ticks are
within-state observations and never independent statistical units.

The ID-free clone key is the SHA-256 of canonical geometry/source content:
map geometry, ordered route geometry, quantized spawn and goal poses, a
0.5-m-resampled route polyline, sorted actor initial geometry/kinematics, and
source content SHA. Database, scenario, route, and state IDs are forbidden from
the clone formula. Any duplicate within a split, between splits, or against the
input-only B4 clone manifest aborts before the first run. There is no drop,
replacement, or suffix path.

The design manifests are specification-disjoint. Actual input/state/latent
tensor SHA and the input-only B4 clone comparison remain a future acquisition
preflight obligation. They are not falsely reported as already observed.
B4/Fresh outcomes are forbidden for sampling or deduplication.

## Repeat and authority topology

The generator is named exactly
`new_single_invocation_batched_k8_candidate_pool`.

Each future state has five sequential-batch1-x8 repeats and five
single-invocation-batch8 repeats. Within-mode comparison uses all ten unordered
repeat pairs. Cross-mode comparison uses repeat-index-matched pairs and is
closed unless both within-mode gates pass.

The frozen runtime is RTX 5090 GPU UUID
`GPU-c82677a4-21d3-a44c-5195-e41c150e086c`, driver `595.71.05`, PyTorch
`2.8.0+cu128`, CUDA `12.8`, cuDNN `91002`, float32, eval mode,
deterministic algorithms, TF32 disabled, cuDNN benchmark disabled, and an
unchanged global RNG boundary. Input/state/latent/model/checkpoint/source,
runtime, mode, repeat, forward and invocation fingerprints are mandatory.

Any fingerprint drift, incorrect repeat topology, nonfinite K8, fewer than
eight unique row SHA values, or RNG-boundary mutation fails closed.

## Calibration and validation thresholds

The endpoint threshold recipe is machine literal:

- per predeclared pair, compute the endpoint error;
- within each state, use empirical q=0.99 with method `higher`;
- across 64 calibration states, use empirical q=0.99 with method `higher`;
- run a deterministic state bootstrap with 10,000 resamples, seed 825071;
- take the upper 95th percentile and the maximum of that value and the
  endpoint resolution floor.

Validation passes an endpoint only when every value uses `error <= threshold`,
the observed exceedance rate is at most 0.05, the exceedance count is at most
2/64, and the one-sided exact Clopper-Pearson 95% upper bound is at most 0.10.
Missing or ambiguous evidence blocks; no complete-case substitution is
allowed.

Atom normalization is bound to the sealed training root
`8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9`,
relative path `runtime_atom_scales.json`, SHA
`72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb`,
JSON fields `/atom_names` and `/scales`, and all 14 literal name/index/value
entries. Zero or nonfinite scales are authority failures.

The score vector includes absolute score delta, within-mode-normalized delta,
margin ratio and Spearman rank error. Margin is runner-up minus best among
eligible candidates, with lower score better. Fewer than two eligible rows is
ambiguous/missing; exact ties use zero margin and the smallest eligible row
index. A near tie is `margin <= 2*max(frozen score threshold, score floor)`.
The previously observed 1.2076 atom delta, 114/128 neighbors, 9/16 states, and
zero selection flips are explicitly forbidden as threshold inputs.

## Functional and action gates

Hard failures are mask/eligibility change, any post-pool DP/model/latent/
generation call, candidate-tensor mutation, K8 nonfinite/nondiverse, and
authority/fingerprint drift.

A selected-index flip is neither automatically failed nor automatically
excused. The prospective action-equivalence rule requires the same 80 samples
at 0.1 s without interpolation, maximum XY error <=0.05 m, wrapped heading
error <=0.01 rad, speed error <=0.05 m/s, and identical executable and terminal
states. All conditions are required.

Neighbor evidence is assessed by state/row exceedance, quantile coverage, and
relative within-mode inflation against their frozen calibration thresholds.
A single float beyond 1e-5 is explicitly not a veto.

## Decision topology and interpretation

The qualification vector contains per-atom normalized delta, score delta and
within-mode ratio, margin ratio, rank correlation, mask/eligibility,
selected-index/action flip, neighbor/trajectory coverage, and K8 taxonomy.
There is no weighted total.

PASS requires authority and split PASS, both within-mode PASS, every cross-mode
endpoint PASS, and zero hard failures. BLOCK precedence is authority failure,
evidence missing, within-mode generator instability, then cross-mode
functional drift.

PASS would mean only that current evidence does not trigger retraining. FAIL
is a classified block and does not itself mean retraining is required. Neither
outcome authorizes a benefit claim or general OOD equivalence claim.

## Zero-run boundary

`acquisition_authorized=false`. Calibration, repeat-model, pool, selector,
closed-loop, Fresh, holdout, and training run counts are all exactly zero.
Fresh, holdout, training and closed loop are false. No claim, promotion, or
deployment is authorized.

