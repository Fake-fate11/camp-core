# V25 Fair-Pool Development Calibration Hard-Stop Report

## Decision

The authorized development-calibration acquisition stopped at the first
planned raw run. The exact classification is:

`first_calibration_run_k8_validity_compound_gate_triggered; exact_subcondition_unresolved_from_preserved_evidence`

This is a scientific-contract BLOCK. It is not a transport failure and it is
not a completed calibration result.

## Authorized scope

- High decision SHA256:
  `ed0d298cbde0e66d7ed2b0bdd90e6be5f2ebbc49f4d818a6c97ff47440f88f59`
- authorized split: `development_calibration`
- planned states/modes/repeats: `64 x 2 x 5`
- planned raw runs: `640`
- planned pair receipts: `1600`
- independent validation: not authorized
- closed-loop, Fresh, holdout, training/retraining: not authorized

The authority, input-only preflight and independent preflight review sealed
successfully:

| Artifact | Root SHA256 |
|---|---|
| calibration authority | `bd6fee62418d062266e8f922d2f2dd3672ced115f9c1065e922db4b207054820` |
| input-only preflight | `5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22` |
| independent preflight review | `ece7c80b6e764598ff867606f225a29a40f8ddededc641e7f22032b4b5d49ef3` |

## Exact hard stop

The first raw-run identity was:

- state: `development_calibration:000`
- mode: `sequential_batch1_x8`
- repeat: `0`
- completed model forwards: `8`
- selector calls: `0`

The frozen compound predicate was evaluated after the eight batch-1 forwards
and before selector execution. Its three possible subconditions were:

1. candidate tensor contains a non-finite value;
2. neighbor tensor contains a non-finite value;
3. the eight candidate-row SHA256 values are not unique.

The preserved control evidence records only the compound exception. It does
not preserve candidate or neighbor bytes, so the exact subcondition is
`unknown` and cannot be recovered without an unauthorized rerun. No one of the
three alternatives is asserted.

## Denominator and downstream state

| Item | State |
|---|---|
| completed raw runs | `0 / 640` |
| completed pair receipts | `0 / 1600` |
| raw artifact | absent |
| raw independent review | absent |
| threshold freeze | not formed |
| threshold independent review | absent |
| independent validation executions | `0` |
| closed-loop executions | `0` |
| replacement calibration executions | `0` |
| Fresh/holdout executions | `0` |
| training/retraining executions | `0` |
| old artifact/CAS writes | `0` |
| Fresh/B4 outcome values read | `false` |

Because the raw denominator did not form, no threshold can be estimated and no
validation consumer may start.

## Outcome-blind closeout

| Artifact | Root SHA256 |
|---|---|
| implementation focused, 24/24 | `ddeef758461fa9f1b3d5f67bab0ebeea91674dc8fc54b5ee0513dbed490a70a8` |
| hard-stop closeout | `50e22c19fab0394992a9b915560ac58c96766ed4ff775a6def83c78ec0f7871e` |
| closeout content | `7e6f17622ca86c76eb3078d7ce24311c4f6e45246f37c116de1fdab981b183e4` |
| independent closeout review | `07e1969f05b110eea2f658fc8c9228480a18a0e1f2ab2131cf6e469fac2e08ed` |

The independent reviewer rebuilt the literal three-way predicate, rehashed
the producer/control bytes, reverified the three authority seals, confirmed
PID termination and the four absent downstream directories, and imported
neither the raw producer nor any model/selector oracle.

## Preserved pre-artifact diagnostics

Three earlier failures remain classified only as model-call-zero fixture
diagnostics:

- Lanelet2 projection compatibility;
- causal map-cache serialization;
- sealed model-input versus unpinned scene-history reconstruction.

They do not change the later post-forward hard-stop classification.

## Scientific boundary

This failure does not establish:

- candidate non-finiteness specifically;
- neighbor non-finiteness specifically;
- duplicate candidate rows specifically;
- model failure;
- batch-8 architecture failure;
- OOD or training-distribution drift;
- a requirement to retrain;
- any benefit, safety, comfort, or deployment claim.

The preserved legacy decision remains
`honest_no_claim_under_frozen_preregistered_all_gate`. The next authority is a
High/control decision. Replacement calibration, validation, closed-loop,
Fresh/holdout, training/retraining and claim promotion remain prohibited.
