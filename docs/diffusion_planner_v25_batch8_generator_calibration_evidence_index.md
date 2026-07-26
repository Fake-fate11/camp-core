# V25 Same-Ego Batch8 Generator Calibration Evidence Index

| Role | Exact directory | Root SHA256 | Result |
|---|---|---|---|
| outcome-independent contract | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_contract_v1_989c9c75` | `5bdf49344a7a22cac09bfdcd139381f17cc0488c4acf825861c0d0b06e07f43c` | PASS |
| independent contract review | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_contract_v1_review_989c9c75` | `722e7c1beac4c9a846213c6620587a0e9f57973d12023caa0744de2f8d001c53` | PASS |
| zero-model focused | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_focused_v1_989c9c75` | `6c0a1dc3bc0326aa090c7506e653efa68cf66a9a4cb9a2500568bbee22ff32a2` | 25/25 PASS |
| 320-run input/latent preflight | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_preflight_v1_989c9c75` | `2e3935ed1690ea168daba29a07a497640de0b3d092e7f465bd10c7f4fa416348` | PASS |
| independent preflight review | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_preflight_v1_review_989c9c75` | `196828896cbb10fb51622d3b3f582a3eb71551336ceb1319f1e12ab0ce1180ee` | PASS |
| raw 320-call full denominator | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_raw_v1_989c9c75` | `1dc673dc99df411ccee571fe80a1261c08fba5b52ab87ff397bb2733c2868f82` | PASS |
| independent raw review | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_raw_v1_review_989c9c75` | `8756b1d5aa32f666aaabe7cab6bdfddc3ced0ded638caed673f7a4d05f61b45b` | PASS |
| frozen threshold envelope | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_threshold_v1_989c9c75` | `abc15b2cae990e8465aa2fd1a97a6f2903dda948c0606ba167867dcf1a1c0e5b` | PASS |
| independent threshold review | `/root/autodl-tmp/camp_dp_v25_batch8_generator_calibration_threshold_v1_review_989c9c75` | `0d3388f0d4821a09d4c7b0d90710a469a3042f2040c3d0d05865ff7f8c9cf519` | PASS |

Immutable upstream design evidence remains:

- industrial evaluation v3 contract/review:
  `908fe1d5…128cb` / `23bb07ac…e48556`;
- batch8-primary contract/review:
  `15cf642f…30e5d7` / `a0cd1793…33978`;
- first-state batch8 diagnostic/review:
  `6a9e1a36…3eec5` / `92e33a3e…073c3`;
- batch8-only design/review:
  `f4216e9e…53c1c` / `8f2b198b…9237457`.

The raw review rebuilt 320 receipts, 640 unordered repeat pairs and 64
state-level statistics. The threshold review independently rebuilt all six
endpoint formulas and the exact bootstrap index preimage. Outcome reads,
selector calls, old-artifact/CAS writes and claims were all zero.
