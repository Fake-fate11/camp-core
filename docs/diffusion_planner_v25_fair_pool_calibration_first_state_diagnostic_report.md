# V25 Fair-Pool Calibration First-State Diagnostic Report

## Decision scope

This report is an additive development diagnostic. It does not reopen or
rewrite the failed 0/640 calibration attempt, and it does not authorize a new
640-run calibration, threshold materialization, validation, closed-loop,
Fresh/holdout execution, training/retraining, or any claim.

The prior attempt remains sealed as:

`first_calibration_run_k8_validity_compound_gate_triggered; exact_subcondition_unresolved_from_preserved_evidence`

Its outcome-blind closeout and independent review roots remain
`50e22c19fab0394992a9b915560ac58c96766ed4ff775a6def83c78ec0f7871e`
and
`07e1969f05b110eea2f658fc8c9228480a18a0e1f2ab2131cf6e469fac2e08ed`.
That closeout terminates only the failed attempt, not the project.

## Diagnostic authority

High authorized exactly one replay of:

- state: `development_calibration:000`
- mode: `sequential_batch1_x8`
- repeat: `0`
- model forwards: `8`
- selector calls: `0`
- stop point: before selector

Canonical authority SHA256:
`3a72e639152b3416f7ef769f20dee05a2334d160b866ada4bd609c0c801277c8`.
The remaining 639 runs, threshold materialization, validation, and closed-loop
were not authorized.

The versioned contract and independent literal contract review were frozen
before replay:

| Artifact | Root SHA256 |
|---|---|
| first-state diagnostic contract | `9f70b46f10d915ecfe3fec7830467ddb42efeeec89fac9a6eddfdd43f0305fd7` |
| independent contract review | `64be791bc609fac3b168fcb97096d4dff366fa6b8cc97e52d2c7b0a075bc0e79` |
| 43/43 focused qualification | `eb1e71f147d9110b86ffd65a5aae9a191a05a92a9c12317c426771f1cd5d5228` |

Implementation HEAD:
`bacc9d2a795c471f1547823528a4c06d5372ea18`.
Fixed Diffusion Planner HEAD:
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

## Tensor-byte result

The producer atomically formed a precondition receipt before applying the
compound gate. The separate-role reviewer independently decoded the exact
tensor bytes and rebuilt every subcondition without importing the producer or
model.

| Field | Producer and reviewer result |
|---|---|
| candidate shape/dtype | `[8,80,4]`, `<f4` |
| candidate non-finite indices | `0` |
| neighbor shape/dtype | `[8,32,80,4]`, `<f4` |
| neighbor non-finite indices | `0` |
| candidate row SHA256 unique cardinality | `2 / 8` |
| duplicate row groups | `[[1,2,3,4,5,6,7]]` |
| exact resolved subcondition | `candidate_row_sha256_not_unique_across_k8` |
| model calls | `8` |
| selector calls | `0` |
| receipt SHA256 | `d97fc4bbcfdb1ccf8fed517b8c47b89e7401952b1a9b5b5f1766ae50f38f3a45` |

The diagnostic artifact root is
`685c1529a95409f9f92220ac40d02c054d939bc93410e2ce4c0608e0e6dbffb8`.
The independent review root is
`8767856884b6597668a22c9c3dc1db8aa3dfacce329d29fe5002b26fa77c95ca`.

## Interpretation

The replay resolves the diagnostic replay's compound predicate: candidate and
neighbor tensors were finite, while candidate rows 1 through 7 shared one row
SHA256 and row 0 was distinct. This is a precise structural observation for
the authorized first state and sequential mode.

It does not by itself establish:

- general model failure;
- failure of the single-invocation batch-8 architecture;
- OOD or training-distribution drift;
- a requirement to retrain;
- behavior on the remaining 63 calibration states;
- any threshold, validation, closed-loop, Fresh benefit, safety, comfort,
  promotion, deployment, or production-readiness conclusion.

## High scientific-contract decision

High accepted the closeout and diagnostic evidence chain but withheld a new
0/640 calibration authority. The automatic replacement condition required the
first-state K8 to be valid with the prior failure attributable only to the
harness or receipt ordering. The tensor-byte diagnostic instead established
the real frozen diversity-gate subcondition
`candidate_row_sha256_not_unique_across_k8`.

The current machine state is
`first_state_sequential_k8_nondiversity_resolved_new_calibration_authority_withheld_scientific_contract_review_required`.
This decision does not broaden the bounded observation into failure of batch-8,
all 64 states, the model generally, OOD, or a need to retrain. High/control or
the user must separately decide whether to authorize an outcome-free
latent-injection/source audit or change the target-generator contract. The
executor did not start a replacement calibration.
