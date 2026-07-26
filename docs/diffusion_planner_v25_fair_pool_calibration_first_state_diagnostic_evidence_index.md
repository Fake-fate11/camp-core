# V25 Fair-Pool Calibration First-State Diagnostic Evidence Index

## Current state

`failed_attempt_closed_diagnostic_authorized_scientific_contract_review_required`

The old 0/640 attempt is closed and immutable. The separately authorized
first-state diagnostic is complete and independently reviewed. No replacement
calibration has started.

## Preserved failed-attempt evidence

| Role | Root SHA256 | Status |
|---|---|---|
| failed-attempt closeout | `50e22c19fab0394992a9b915560ac58c96766ed4ff775a6def83c78ec0f7871e` | sealed |
| independent closeout review | `07e1969f05b110eea2f658fc8c9228480a18a0e1f2ab2131cf6e469fac2e08ed` | PASS |

The old attempt retains its unresolved-subcondition classification. It is not
silently rewritten using the later diagnostic.

## Current diagnostic chain

| Role | Exact path | Root SHA256 | Status |
|---|---|---|---|
| contract | `/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_first_state_diagnostic_contract_bacc9d2a_3a72e639` | `9f70b46f10d915ecfe3fec7830467ddb42efeeec89fac9a6eddfdd43f0305fd7` | sealed |
| independent contract review | `/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_first_state_diagnostic_contract_review_bacc9d2a_3a72e639` | `64be791bc609fac3b168fcb97096d4dff366fa6b8cc97e52d2c7b0a075bc0e79` | PASS |
| focused qualification | `/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_first_state_diagnostic_focused_bacc9d2a_3a72e639` | `eb1e71f147d9110b86ffd65a5aae9a191a05a92a9c12317c426771f1cd5d5228` | 43/43 PASS |
| tensor-byte diagnostic | `/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_first_state_diagnostic_bacc9d2a_3a72e639` | `685c1529a95409f9f92220ac40d02c054d939bc93410e2ce4c0608e0e6dbffb8` | sealed |
| independent tensor-byte review | `/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_first_state_diagnostic_review_bacc9d2a_3a72e639` | `8767856884b6597668a22c9c3dc1db8aa3dfacce329d29fe5002b26fa77c95ca` | PASS |

The authority SHA is
`3a72e639152b3416f7ef769f20dee05a2334d160b866ada4bd609c0c801277c8`.
Implementation/fixed-DP HEADs are
`bacc9d2a795c471f1547823528a4c06d5372ea18` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

## Exact receipt

- state/mode/repeat:
  `development_calibration:000 / sequential_batch1_x8 / 0`
- candidate: `[8,80,4]`, `<f4`, non-finite count `0`
- neighbor: `[8,32,80,4]`, `<f4`, non-finite count `0`
- candidate row SHA unique cardinality: `2`
- duplicate groups: `[[1,2,3,4,5,6,7]]`
- resolved subcondition:
  `candidate_row_sha256_not_unique_across_k8`
- model/selector calls: `8 / 0`
- receipt SHA256:
  `d97fc4bbcfdb1ccf8fed517b8c47b89e7401952b1a9b5b5f1766ae50f38f3a45`

Producer and reviewer both derived these fields from the candidate and neighbor
tensor bytes. Rehashed forged fields and tensor/hash mutations are fail-closed.

## Superseded pre-run diagnostic

The first implementation HEAD `dff0fb745c92ccfa52a0afbae7f62544897adf63`
formed contract/review/focused roots
`b42cfcac8a624a5a56bcb73df02567d6236bf8236dc9f13cd7799df89cc326ae`,
`0889d34303d28c263bffbe9470b1b2049a3e125f90a91b4d9de8f5060cb96839`,
and
`ed336c8e8591a9615399a560cfd2a27965fc5b7196448e49241a1c02c908aaac`.
A pre-run static audit found its fixed-DP Git HEAD type mismatch before any
model call. Those roots remain preserved as superseded pre-run diagnostics.

## Prohibited work remains zero

- remaining 639 calibration runs: `0`
- replacement 0/640 calibration runs: `0`
- selector calls: `0`
- threshold materialization: `0`
- validation and closed-loop: `0`
- Fresh/holdout: `0`
- training/retraining: `0`
- old artifact/CAS writes: `0`
- Fresh/B4 outcome reads: `0`

No benefit, OOD, retraining, safety, comfort, promotion, deployment, or
production-readiness conclusion is authorized.
