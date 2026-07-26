# V25 Corrected Batch8 Generator Repeatability Evidence Index

| Role | Exact directory | Root SHA256 | Result |
|---|---|---|---|
| corrected outcome-independent contract | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_contract_v1_dc76fbc8` | `4aacc1addf1ecefb4ddea4c58ef96391f09a350eaf687eea3fd59fc6a356c60a` | PASS |
| independent contract review | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_contract_review_v1_dc76fbc8` | `9dcd2e6b7d928768b0344b9b2423ec4acd58c4d013af9de87923b795996ef8a7` | PASS |
| zero-model focused | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_focused_v1_dc76fbc8` | `1aa3344a30ba95585604f40d5b082e21e80af77602e749389948d3ce9d90d5ef` | 27/27 PASS |
| 64 canonical records / 320 expansion preflight | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_preflight_v1_dc76fbc8` | `5be8831533f0a46ecc5439c3eafbff85118689f7696996d825c4b09838189fac` | PASS |
| independent preflight review | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_preflight_review_v1_dc76fbc8` | `280e45b18630f286147bfe8796df71085701841d339c602a5cd30de6d7943584` | PASS |
| corrected raw 320-call full denominator | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_raw_v1_dc76fbc8` | `731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4` | PASS |
| independent raw review | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_raw_review_v1_dc76fbc8` | `c0e24bb60a4eb9694bfda099d4d6d9b9be07f85fb486577275f0b32178cfbfc8` | PASS |
| corrected threshold envelope | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_threshold_v1_dc76fbc8` | `a4f6c54cb46378119b261fe0ef19f83f8b92d18fa3be3e02693f7905f3f8ac89` | PASS |
| independent threshold review | `/root/autodl-tmp/camp_dp_v25_batch8_generator_repeatability_corrected_threshold_review_v1_dc76fbc8` | `8882f0fa66d1690460662848fa67673657926cc663b0edf476866e1418034e0e` | PASS |

Immutable superseded dispersion diagnostic:

- raw `1dc673dc99df411ccee571fe80a1261c08fba5b52ab87ff397bb2733c2868f82`
- raw review `8756b1d5aa32f666aaabe7cab6bdfddc3ced0ded638caed673f7a4d05f61b45b`
- threshold `abc15b2cae990e8465aa2fd1a97a6f2903dda948c0606ba167867dcf1a1c0e5b`
- threshold review `0d3388f0d4821a09d4c7b0d90710a469a3042f2040c3d0d05865ff7f8c9cf519`

That older chain is not a generator-repeatability qualification and supplied
no raw value or threshold to the corrected chain.

Immutable upstream design evidence remains:

- industrial evaluation v3 contract/review:
  `908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb`
  / `23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556`;
- 64-state source-spec manifest:
  `569718077a1c6c7f5193074ba86e646da4a3a40a2fdc573c7bfa51f3cfaa722f`.

No selector, SafetyCost/NI, training support, validation, closed-loop,
Fresh/holdout, training, outcome read, old-artifact/CAS write or claim was
authorized or performed.
