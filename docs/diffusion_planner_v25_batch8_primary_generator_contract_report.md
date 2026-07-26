# V25 Batch8-Primary Generator Contract Amendment

Date: 2026-07-26 (Asia/Shanghai)

## Decision

The additive, outcome-independent contract amendment is sealed and independently
reviewed. The primary target generator is
`new_single_invocation_batched_k8_candidate_pool`: one formal model invocation
receives one ego state expanded along model batch dimension `B=8`, with each row
bound to one of eight prefrozen latent rows, and returns eight candidate ego
trajectories.

This package is contract design only. It does not qualify runtime behavior and
does not authorize a model diagnostic, calibration, threshold materialization,
validation, closed-loop execution, Fresh/holdout work, training, retraining,
claim, promotion, or deployment.

## Authority and immutable history

- High authority SHA256:
  `16f63578b401a2bb5079035f3c047874dde6adc35cb162a71ed4d5016f197690`.
- Superseded authority SHA256:
  `f7d90c476de74f0122bce8ffeeab80260d17ad8cd040035ee97c81040e964aef`.
  It was superseded before any model call and authorizes no sequential
  diagnostic.
- Source-audit root:
  `ef7fed1d077aa2edcdfe4114daaf1904b936ead23d713fc4ba96acbcb8cedc3e`.
- Source-audit review root:
  `bd81175f3088755e41f799854bcc84d09deca8da1e443b1e20ad7cbd3dd09ef6`.
- Implementation HEAD:
  `bcc847870dacbf986ad5aac66b052660b7197696`.
- Fixed Diffusion Planner HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- All old B4, corrected-evaluation, Evaluation v2, calibration-attempt,
  diagnostic, adaptation-contract, ledger, CAS, and report roots remain
  immutable.

## Primary generator contract

| Property | Frozen value |
|---|---|
| Generator | `new_single_invocation_batched_k8_candidate_pool` |
| Formal model calls per pool | `1` |
| Source ego-state count | `1` |
| Expanded model batch | `B=8` |
| Candidate-axis meaning | `same_ego_expanded_batch_dimension_B_equals_8` |
| Agent-as-ego batch | `false` |
| Independent native `K` axis | `false` |
| Operational default batch size | `1` |
| “Operational batch1 already has K8” | `false` |
| Future runtime diagnostic | requires new High authority |

The contract does not rename eight sequential batch-1 calls as the primary
architecture. Operational batch-1 latency remains a separate architecture
reference.

## Latent policy

The latent policy is
`eight_prefrozen_unique_rows_row0_zero_rows1_7_independent_pcg64_standard_normal_float32`.
Its tensor shape is `[8,321,81,4] <f4`; row 0 is all zero; rows 1 through 7
are produced in one PCG64 draw with RHS shape `[7,321,81,4]` and then frozen.
All eight row hashes must be unique before a future model invocation. A single
`[321,81,4]` RHS broadcast across rows 1 through 7 is forbidden.

Synthetic TDD confirms the new formula creates eight unique rows for seed
61000 and that the historical broadcast formula creates only two. No runtime
latent manifest or model output was materialized in this package.

## Pool and selector boundary

Every future pool must bind the same `input_id`, `state_id`, model SHA,
checkpoint SHA, forward invocation ID, pool ID, and candidate-tensor SHA. The
candidate tensor is frozen before selection and immutable afterwards.

- Pool-matched candidate0 is exactly frozen row 0 and is not outcome-selected.
- `Static14D` and `Scene14D` may consume only the same frozen tensor.
- After pool formation, model calls, DP calls, latent generation, and candidate
  generation must each remain exactly zero.

The present package runs no real selector path and therefore makes no selector
effect or action claim.

## Latency accounting

Pool generation is a common cost charged to all three future arms. Atoms,
context, weights, and selector are reported separately as incremental stages;
end-to-end latency is their sum with pool generation. Pool-matched candidate0
includes the same pool-generation cost. Operational single-output batch-1
latency is an architecture reference and cannot be called the pool baseline.

## Sequential legacy exclusion

`sequential_batch1_x8` is retained only as a
`legacy_non_gating_diagnostic_reference_only`. The sealed rows-1-through-7
repetition finding remains unchanged, but sequential evidence is excluded from:

- the formal denominator;
- hard PASS/BLOCK;
- primary latency; and
- the primary qualification decision.

It contributes no threshold and cannot pass or block the batch8-primary
generator.

## Verification

- Local new-contract TDD: `18 passed`.
- Combined local and AutoDL focused suite: `62 passed`.
- Contract root:
  `15cf642f5abcb1cd44687e8f4298517f47e8c878633602e9b42fcffe7c30e5d7`.
- Independent literal review root:
  `a0cd179311b5ce1fd18b7e764154d92041bfda57216c0be2365aa20100133978`.
- Authoritative focused root:
  `bb012e5800fbc37e4106a11032f03c166fb793f34366fe5165068f5daa00ba20`.
- Bundle SHA256, equal before and after transport:
  `ffd38f193a97fb6d3c92f4cd50ec9a08b07495b882f12329db3452b778cace3a`.
- Bundle prerequisite:
  `d7457c7d7e8a26ef3729c3d49ef4f3f2ad04f12e`.
- Bundle target:
  `bcc847870dacbf986ad5aac66b052660b7197696`.
- `git bundle verify` and `git merge --ff-only` passed.

The independent reviewer uses local literal tables and does not import the
producer generator, fairness, or selector oracle. Adversarial tests reject
eight calls presented as one, agent batches presented as same-ego candidate
batches, operational batch-1 presented as native K8, sequential evidence
reintroduced into gating, candidate0 not equal to row0, post-pool calls, and
latency accounting that omits the shared pool cost.

## Run and claim boundary

Model, pool, selector, calibration, threshold, validation, closed-loop, Fresh,
holdout, training, and retraining counts are all zero. No outcome value was
read, and no old artifact or CAS was written. Runtime qualification is
`not_run_not_authorized`; the formal denominator is
`not_formed_not_authorized`; hard PASS is `not_evaluated_not_authorized`.

The legacy scientific conclusion remains
`honest_no_claim_under_frozen_preregistered_all_gate`. This amendment does not
authorize Fresh benefit, safety, OOD, comfort, promotion, deployment, online
activation, or production-readiness claims.

## Next authority

High must review this additive contract package before separately deciding
whether to authorize any future single-invocation batch8 runtime diagnostic.
