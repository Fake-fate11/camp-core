# V25 Sequential Latent-Injection Source Audit

Date: 2026-07-26 (Asia/Shanghai)

## Decision

The outcome-free, zero-new-model-call source and sealed-evidence audit is
complete. Its mutually exclusive taxonomy is:

`latent_input_rows_repeated`

For the exact bounded identity
`development_calibration:000 / sequential_batch1_x8 / repeat0`, the requested
latent tensor was finite but had only two unique rows. Row 0 was the all-zero
row; rows 1 through 7 had the same SHA256 and were NumPy-broadcast from one
`[321,81,4]` random draw. The duplicate candidate and neighbor outputs for
rows 1 through 7 therefore correspond to duplicate requested inputs.

This resolves the source/evidence audit without new model evidence. It does
not establish batch-8 failure, model mapping collapse, failure across all 64
states, OOD, or a need to retrain.

## Authority and immutable inputs

- High authority SHA256:
  `f9a91cbeac8f004cbac8b87bf170e51d54a1a09f5bc25fb256c3abd9e5106ba4`
- implementation HEAD:
  `c33767307148e23397eaab28eae4c501ddadda29`
- fixed-DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- sealed first-state diagnostic root:
  `685c1529a95409f9f92220ac40d02c054d939bc93410e2ce4c0608e0e6dbffb8`
- sealed diagnostic review root:
  `8767856884b6597668a22c9c3dc1db8aa3dfacce329d29fe5002b26fa77c95ca`
- precondition receipt SHA256:
  `d97fc4bbcfdb1ccf8fed517b8c47b89e7401952b1a9b5b5f1766ae50f38f3a45`

No Fresh/B4 outcome, threshold, validation result, or old mutable artifact was
used.

## Sealed artifacts

| Artifact | Root SHA256 |
|---|---|
| source-audit contract | `34c49c2b5378475fce133d7e6a7e2353f3b9a6f864bc18777c015bcfa4e5812f` |
| independent contract review | `4c06f34630c9f979ae35eb735b8ba0de648fdddac99e4b853e83d3e20013b531` |
| focused tests, 14/14 | `19baef92203fa39f589ab00a24f6363f933121eb671c81f4cc0a5bd98a5e0c07` |
| zero-call source audit | `ef7fed1d077aa2edcdfe4114daaf1904b936ead23d713fc4ba96acbcb8cedc3e` |
| independent source-audit review | `bd81175f3088755e41f799854bcc84d09deca8da1e443b1e20ad7cbd3dd09ef6` |

All five artifacts have `run.exit=0` and complete seals.

## Requested latent reconstruction

| Field | Exact result |
|---|---|
| seed / bit generator | `61000 / PCG64` |
| shape / dtype | `[8,321,81,4] / <f4` |
| finite / non-finite indices | `true / []` |
| full tensor SHA256 | `b995f83f083df0321b8a575e10065aac041c14c30830129963048b73b7ebfea0` |
| unique row cardinality | `2 / 8` |
| duplicate group | `[[1,2,3,4,5,6,7]]` |
| row 0 SHA256 | `f3a50793e3db251cf7a8423a30c2657e7d027ee886c8389c0c412e0fd697f39f` |
| rows 1-7 SHA256 | `50f16e46e8702d0b3f037afc11528b9dc60489ec3d6eadf690a320eae94c7525` |

The sealed policy source executes:

`latent[1:] = rng.standard_normal(LATENT_SHAPE[1:]).astype(np.float32)`

The right-hand side shape is `[321,81,4]`; the left-hand side shape is
`[7,321,81,4]`. NumPy trailing-axis broadcasting copies that one draw into
all seven rows. The diagnostic materializer independently contains the same
shape relation.

## Static dataflow

The producer and independent reviewer separately parsed and hashed four pinned
source files:

| Source | SHA256 | Functions/spans |
|---|---|---|
| CAMP diagnostic materializer | `b08ac9b56f844ab2b5d54e3cd4d96a7725c428271a598674b06a8a7dda3d18cd` | `_latent` 104-108; `_expanded_inputs` 111-128; `_forward_id` 131-158; `main` 161-441 |
| CAMP input manifest v2 | `e603e2236ae77f33cb02e9de4b7c8b54f5f9977a2dae49f4574a327004ad7a85` | `materialize_latent_manifest` 341-362 |
| fixed-DP model | `341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d` | `Diffusion_Planner.forward` 17-21 |
| fixed-DP decoder | `8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd` | flow 384-421; x-start 423-505; inference dispatch 507-543; forward 545-591 |

The trace establishes:

1. the batch-1 non-latent inputs are expanded to eight rows;
2. `sampled_trajectories` is overwritten with the reconstructed latent;
3. sequential call `i` slices requested latent row `i`;
4. `Diffusion_Planner.forward` passes the same input mapping to the decoder;
5. inference reshapes and consumes `sampled_trajectories` as either flow
   state `x` or x-start state `xT`;
6. each row is bound to call index, sealed forward ID, candidate output row
   SHA, and neighbor output row SHA.

There is no separate formal latent argument that is silently ignored. The
repetition occurs during construction, before the input overwrite and
decoder consumption.

## Taxonomy

The five frozen categories are mutually exclusive:

- `latent_input_rows_repeated` — selected;
- `latent_rows_unique_but_not_consumed` — not selected;
- `latent_rows_consumed_model_mapping_collapsed` — not selected;
- `evidence_binding_error` — not selected;
- `unresolved_requires_minimal_new_model_evidence` — not selected.

Because the requested inputs already repeat, the sealed evidence does not
support attributing repeated outputs to model mapping collapse.

## Engineering proposal only

A future versioned latent policy could request seven independent draws by
making the random draw shape match the left-hand side, for example
`latent[1:].shape`. That would change the frozen latent preimage and manifest
SHA, so it is not applied here. It requires a new prospective latent-policy
contract and High authority before any model execution.

No fixed-DP source, checkpoint, weights, CAMP weights/atoms, threshold,
scientific contract, or sealed artifact was modified.

## Prohibited work remains zero

- new model calls: `0`
- new pool calls: `0`
- new selector calls: `0`
- replacement/full calibration: `0`
- threshold/validation/closed-loop: `0`
- Fresh/holdout: `0`
- training/retraining: `0`
- raw outcome reads: `0`
- old artifact/CAS writes: `0`
- claim/promotion/deployment authority: `false`
