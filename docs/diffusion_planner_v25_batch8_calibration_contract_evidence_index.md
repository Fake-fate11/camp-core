# V25 Batch8-Only Calibration Contract Evidence Index

## Decision

`contract_design_passed_acquisition_unauthorized_training_support_reference_evidence_missing`

This index is additive. It does not mutate any sealed V25 artifact or CAS.

## Authority

| Item | Value |
|---|---|
| High authority SHA256 | `81dbf890717297cebf477ee9192c98c5c4f641bd3b976cab5154d6da872a5f7b` |
| implementation HEAD | `383d9944ac1bc912880d15ef3c5ed4944c07c9ed` |
| fixed-DP HEAD | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| actual acquisition authorized | `false` |
| threshold materialization authorized | `false` |
| validation/closed-loop/Fresh/training authorized | `false` |

## New sealed artifacts

| Role | Exact path | Root SHA256 | Status |
|---|---|---|---|
| contract | `/root/autodl-tmp/camp_dp_v25_batch8_primary_calibration_contract_383d9944_81dbf890` | `f4216e9e59d7cc81cf8d7ebd69e0bdd38b1399ec11d6fe95866994b309d53c1c` | PASS |
| independent contract review | `/root/autodl-tmp/camp_dp_v25_batch8_primary_calibration_contract_review_383d9944_81dbf890` | `8f2b198be18ef01607f4e355e014f3de07f049981ee05c0c18b96017b9237457` | PASS |
| authoritative focused | `/root/autodl-tmp/camp_dp_v25_batch8_primary_calibration_contract_focused_383d9944_81dbf890` | `ec272560f2bb7c31a32cea8e9e5f6d83caad4f041ae5340a3f4881f8db90bdd5` | 84/84 PASS |

## Preserved mechanical diagnostic

| Role | Exact path | Root / state |
|---|---|---|
| d6 contract | `/root/autodl-tmp/camp_dp_v25_batch8_primary_calibration_contract_d6d67d8c_81dbf890` | `2e93f633ec6053200b5bdc32ff2500118ee059db0e8be1415ed7c76b9f2b37a4` |
| d6 review | `/root/autodl-tmp/camp_dp_v25_batch8_primary_calibration_contract_review_d6d67d8c_81dbf890` | absent; JSON-order fixture failed before artifact |
| d6 focused | `/root/autodl-tmp/camp_dp_v25_batch8_primary_calibration_contract_focused_d6d67d8c_81dbf890` | absent |

## Contract matrix

| Dimension | Frozen value |
|---|---|
| primary mode | `single_invocation_batch8` |
| generator | `new_single_invocation_batched_k8_candidate_pool` |
| phase keys | `batch8_within` only |
| states × repeats | `64 × 5` |
| model invocations | `320` planned; `0` executed |
| unordered within pairs | `10/state`, `640` total |
| selector receipts | Static `320` + Scene `320` = `640` planned; `0` executed |
| numeric endpoints | exact 22 v5 within endpoints |
| sequential numeric/denominator/threshold contribution | `0 / 0 / 0` |
| cross-mode endpoints and receipts | `0` |
| independent statistical unit | state |
| failure handling | retain every slot; fail closed; no drop/replacement |
| weighted total | forbidden |

## Training-support evidence

| Evidence | Status |
|---|---|
| 14D atom-scale root/SHA/index | bound and sufficient for normalization |
| same-ego batch8 training candidate rows | evidence missing |
| Static14D training score/mask/margin/eligible/action reference | evidence missing |
| Scene14D training score/mask/margin/eligible/action reference | evidence missing |
| training-support threshold materialization | not formed |
| calibration may set training-support thresholds | false |
| “retraining unnecessary” conclusion | unauthorized |

## Verification matrix

| Check | Result |
|---|---|
| producer literal validation | PASS |
| separate-role reviewer local 22-formula reconstruction | PASS |
| 320/640/640 topology reconstruction | PASS |
| q99/PCG64DXSM bootstrap/UCB reconstruction | PASS |
| sequential/cross re-entry adversarial tests | fail closed |
| old 640/1600/73 topology adversarial tests | fail closed |
| tick/row statistical-unit substitution | fail closed |
| dropped-failure mutation | fail closed |
| eight calls masquerading as one | fail closed |
| calibration-set training thresholds | fail closed |
| model/pool/selector/calibration runs | `0` |
| old artifact/CAS writes | `0` |
| outcome reads | `false` |

## Preserved accepted roots

- batch8-primary contract/review:
  `15cf642f5abcb1cd44687e8f4298517f47e8c878633602e9b42fcffe7c30e5d7` /
  `a0cd179311b5ce1fd18b7e764154d92041bfda57216c0be2365aa20100133978`
- batch8 first-state diagnostic/review:
  `6a9e1a364b6d25716a471d34039553b11521c2d911563df0e3ee0edf1ed3eec5` /
  `92e33a3e1747764a65d6d6b8e38645f7faa9825b2b08c980255025ac840073c3`
- v5 contract/review:
  `78584ecc74a1a4f42e18fe0f4ee81e4fd0f48e98e33fd56c7128954c2ce0e4c6` /
  `3e0f5c5247fc3fc4e877d0c2597022a5b31c2e297023fd39cc0a58060c0491e5`

## Claim boundary

The package is a design qualification only. It does not authorize acquisition,
thresholds, validation, closed loop, Fresh/holdout, training/retraining,
benefit, general OOD, industrial safety, promotion, deployment, online
activation, or production readiness. The legacy result remains
`honest_no_claim_under_frozen_preregistered_all_gate`.
