# V25 Industrial-v3 Multiroute Review-only Recovery Evidence Index

| Evidence | Exact authority |
| --- | --- |
| merged High authority | `181be7266035f4a1a40c11bf1bf1c3458dd79491e97e5e91ecd1914cbc7672b4` |
| implementation HEAD | `fe6ce7e63edd017865c3a11072b8fc7a6eeee9eb` |
| fixed-DP HEAD | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| correction continuation | `ca642a15dd612ef925ce6f6e5783597e9e0a41be49e1385cdf0143f5a966fc28` |
| execution | `/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_v2_replacement_8fc8e271_47a47c03_execution`, root `7d143a95cf42aa702e362dd75a1b8c5d7559690bdcd701a001ee0fac186fb052` |
| execution review | `/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_v2_replacement_8fc8e271_47a47c03_execution_review`, root `6c90f5e966e78203702c71168098ae3fe93f385e7af750890e248ef156cabf27` |
| corrected evaluation | `/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_v2_evaluation_actor_binding_replacement_495d3b2b_ca642a15_evaluation`, root `16a156ac21fba0cd5038802df7b0735f4c66d25b1cb73663fd8710fda97cdf8c` |
| authorized preflight | root `5f56246ac312682920f0aaae63cab3d5f4f0ea5e75c85156b30395ce8e30f341` |
| stage authority | `/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_v2_merged_review_recovery_fe6ce7e6_181be726_stage_authority`, root `1015df19895128a46f6b7717974d8a7aed51b9d96174f89724aa74ab4f987963` |
| stage-authority review | same prefix + `stage_authority_review`, root `eacad2d58275ac65f9ad3e0e7f45abe5d20e9fd48e383fd0f3650d3292b8ab9a` |
| stage-authority operation | same prefix + `stage_authority_operation`, root `417d44a67bd5ad522a26a00e1a12e131b8a3d71baf727435ef35d41882cf02b1` |
| evaluation review | same prefix + `evaluation_review`, root `e652394725a038d3b501ecdd30f9e39e9e26bc5cbd6d4b6c3789b16550af6fd3` |
| review-only operation | same prefix + `evaluation_review_operation`, root `1a92d1fd1c892679335e23823b7ed6df849bd32d053b8ff045decc7144e8dbb5` |
| orchestration focused | same prefix + `orchestration_focused`, root `6677cb361dac75d8d2cd55ce1c43b740717f75cb2913770c250a60409efb9c7c` |

## Machine evidence

- `stage_authority/report.json` binds the actual verified root receipts,
  schema/status/HEAD/continuation/exact directories, the authorized preflight,
  industrial-v3 roots, execution/review, and corrected evaluation.
- `stage_authority_review/report.json` independently reconstructs and checks
  the complete external authority chain using reviewer-local literals.
- `evaluation_review_operation/machine_result.json` and
  `operation_receipt.json` prove review-only execution, producer skip, separate
  process streams/exits, and target-root provenance without stdout parsing.
- `evaluation_review/report.json` independently rebuilds all 161 leaves and
  verifies that the source evaluation itself recorded the authorized preflight
  root.
- the final-docs artifact contains the complete 161-row main result table and
  full failure/accounting JSON copied from the independently reviewed sealed
  inputs.

## Immutable and excluded evidence

- The earlier unreviewed evaluation root
  `2cf2689fddabb07f583f51e512ca21a867b31bd245117e3c071aa178e3f531b5`
  remains a diagnostic only.
- No model, execution, producer, evaluator, pool, selector, Fresh, holdout,
  training, or old CAS write was performed by this recovery.
- No SafetyCost, weighted total, Holm/IUT/NI claim, deployment, or industrial
  certification is authorized.
