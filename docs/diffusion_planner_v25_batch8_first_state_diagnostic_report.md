# V25 Single-Invocation Batch8 First-State Diagnostic Report

## Decision

The authorized development/nonholdout preselector diagnostic completed and was
independently reviewed. Its bounded taxonomy is
`batch8_pool_valid_diverse`.

This means only that, for the exact preregistered state
`development_calibration:000`, repeat 0, one formal fixed-DP invocation with
one ego state expanded on model batch dimension `B=8` consumed eight unique
prefrozen latent rows and produced eight finite, byte-distinct candidate rows.
It is not a calibration result, distributional guarantee, performance result,
Fresh result, or claim.

## Frozen authority and architecture

- High authority SHA256:
  `8b63c3564fa3f0ae1f87c5a97794eb01cc172fc6567814411d739aa0a6e7ed14`.
- Fixed DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Diagnostic implementation HEAD:
  `cf0dc3fa6b90611d945ae90119cee0d166f2c6b3`.
- Reviewer mechanical-repair HEAD:
  `c4d34eb1b1df4562f6d73d7cd1a5a1859b55a0ef`.
- Mode: `single_invocation_batch8`; source ego states: 1; expanded model
  batch: 8; `agent_as_ego_batch=false`.
- Formal model invocations: 1. Sequential model invocations: 0. Selector
  invocations: 0. The diagnostic stopped before Static14D or Scene14D.
- Candidate0 remains tensor row 0. No post-pool model, DP, latent-generation,
  candidate-generation, or selector path ran.

## Input-only preflight

The new manifest retained the preregistered state, route, geometry, source, and
seed while replacing only the superseded broadcast latent construction with
the contract-frozen policy: row 0 all zero; rows 1 through 7 one independent
PCG64 standard-normal draw of RHS shape `[7,321,81,4]`, cast to float32.

The input-only preflight and separate-role review rebuilt the new manifest,
latent tensor, instance key, old 64+64 nonholdout inventories, and the sealed
B2/B3/B4 forbidden clone inventory before the model call. All recorded overlap
counts were zero; no state was dropped or replaced.

## Byte-level result

| Item | Sealed result |
|---|---|
| Latent | `[8,321,81,4] <f4`, finite, 8/8 unique rows |
| Latent tensor SHA256 | `7be67d387c045852169e64c88cc11b69e19b17c6d7dd2b3ae143209c7994bf99` |
| Nonlatent input rows | exact-equal across all 8 batch rows |
| Candidate | `[8,80,4] <f4`, finite, 8/8 unique rows, no duplicate groups |
| Candidate tensor SHA256 | `899a81f7129627ccbe49ad74d3b3295a887f7a50ef7512b77c585de6561b6f3b` |
| Neighbor | `[8,32,80,4] <f4`, finite |
| Neighbor tensor SHA256 | `e52ba476477e0cfb8fe77cfabc78df776ebba94f2ccb6df0080ffa2b13d64f46` |
| Formal forward ID | `b4862848f7038983adbd3cc0b7e6cc5934b4e20ef6c1ae34e4b1cfa2b9e45e74` |
| Pool ID | `aa8ca514db4855739d8a22af4513b34c66df265c4c0b129a2a7a19d250d0a61d` |
| Receipt SHA256 | `6cfbc68e8f9408b62710494fc36758bb96f0ed7b7b9411644b300010b457caaf` |
| Pool-generation latency | 504901053 ns (single controlled diagnostic sample) |

The latency value is a single development measurement, not a distribution,
deadline qualification, operational baseline, or production-readiness result.

## Independent review

The separate-role reviewer read the sealed latent, expanded-input, candidate,
and neighbor bytes and independently rebuilt shapes, dtypes, finiteness,
per-row hashes, duplicate groups, same-ego equality, forward ID, pool ID,
candidate0 binding, call topology, and taxonomy. Its source AST contains exactly
one unlooped formal `model(...)` call and no selector path.

The first reviewer launch encountered a JSON object-order fixture error after
the valid diagnostic artifact was sealed. It did not call the model. The
versioned repair changed the reviewer from insertion-order comparison to exact
keyset comparison, added a canonical-JSON round-trip regression test, and then
reviewed the original immutable diagnostic root. The diagnostic was not rerun.

Earlier implementation `be2d036d...` contract/preflight artifacts and its
pre-model `ModuleNotFoundError` remain preserved diagnostics. That import-only
failure made zero model calls and formed no diagnostic artifact.

## Scientific and execution boundary

- Full 640-run calibration: not authorized and not run.
- Threshold materialization: not authorized and not formed.
- Independent validation and qualification decision: not authorized and not
  run.
- Closed-loop, Fresh/holdout, training, retraining: not authorized and not run.
- Static14D/Scene14D selector execution: not run.
- Fresh/B4 outcome read: false.
- Old artifact/CAS writes: 0.
- Claim, promotion, deployment, online activation, and production readiness:
  not authorized.

The preserved legacy conclusion remains
`honest_no_claim_under_frozen_preregistered_all_gate`. The diagnostic does not
authorize Fresh benefit, real-road safety, broad unseen-map performance,
native-ranked Top1, industrial conformity, or a “no retraining needed”
conclusion. High/control must separately decide whether any prospective
batch8-primary calibration authority is issued.
