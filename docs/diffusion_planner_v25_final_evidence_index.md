# V25 Final Evidence Index and Acceptance Checklist

Date: 2026-07-25 (Asia/Shanghai)  
Disposition: `post_exposure_evaluation_control_fatal_honest_no_claim`

## Eleven-item acceptance checklist

| # | Required delivery | Final state | Evidence |
|---:|---|---|---|
| 1 | 14D atom table | complete | 14 PASS / 0 WARN / 0 FAIL; atom/review roots below |
| 2 | 26D context and leakage audit | complete | no-V2I phase-remaining availability 0; train-only scaler; forbidden future/identity/outcome fields |
| 3 | Static/Scene 9D/14D training and convergence | complete | four CLARABEL optimal models; training/review roots below |
| 4 | Corpus, split, coverage, retained failures | complete | 1,500 training identities; 500 Fresh pairs; 1,500 Fresh terminal arms; full denominator |
| 5 | Benchmark A/B three-arm account | complete with honest boundary | Legacy A read-only no-claim; B4 execution complete, evaluation unavailable |
| 6 | SafetyCost six components, CI95, B-T-W, strata | unavailable | `unavailable_due_to_post_exposure_evaluation_fatal` |
| 7 | Performance/comfort NI tradeoff | unavailable | `unavailable_due_to_post_exposure_evaluation_fatal` |
| 8 | Ablation and atom mechanism | complete as association only | calibration 9D/14D and leave-group diagnostics; no causal claim |
| 9 | Latency | calibration descriptive evidence only | Fresh latency not read; `unavailable_due_to_post_exposure_evaluation_fatal` |
| 10 | Failure accounting and one-time state | complete | B2/B3 tombstones; B4 closeout/review; scientific CAS terminal failure |
| 11 | Roots, HEADs, claim/no-claim, paper report | complete | this index, final report, current-status, and audit EOF |

## Current B4 authority chain

| Role | Path | Root/status |
|---|---|---|
| Controller | `/root/autodl-tmp/camp_dp_v25_fresh_b4_controller_decision_7be93df2_8680c1b19ce0620b` | `06f2bf198b9983e0e15f9e0feaba52bc0d595fdd5703d73d98e21c1e8c4f08a2` |
| Opening release | `/root/autodl-tmp/camp_dp_v25_fresh_b4_opening_release_7be93df2_8680c1b19ce0620b` | `7deec7b81a1ad20dd9eb4657c0c3066ce695bc797349def843c0e7152f85851b` |
| Execution | `/root/autodl-tmp/camp_dp_v25_fresh_b4_execution_7be93df2_8680c1b19ce0620b` | `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881` |
| Execution review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_execution_review_7be93df2_8680c1b19ce0620b` | `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d` |
| Evaluation control | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_chain_7be93df2_8680c1b19ce0620b` | `run.exit=1`; deterministic engineering fatal |
| Evaluation | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_7be93df2_8680c1b19ce0620b` | absent; no root |
| Evaluation review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_review_7be93df2_8680c1b19ce0620b` | not started; absent |
| Terminal closeout | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_terminal_closeout_7be93df2_8680c1b19ce0620b` | `a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398` |
| Terminal closeout review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_terminal_closeout_review_7be93df2_8680c1b19ce0620b` | `86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062` |
| Scientific ledger | `/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/scientific/5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a.json` | SHA `c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4`; `terminal_failure` |

Closeout payload SHA:
`a2ae9d62192e2617ad83720615b59f60577e72df7c9b846e09450d07117d6a27`.

Evaluation control evidence SHA256:

- command:
  `5c2134847ef9a1686d3653d48d0147912ee5abc713cf15f574dc5ec02cc0e304`;
- run.exit:
  `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`;
- stderr:
  `23ffd85aa1c6abf6c04a4bef15469fdd83a1e05a01f53aadbc6d5a4a3a1d8a60`.

## Frozen identities and source heads

| Item | SHA |
|---|---|
| Execution source | `7be93df20deee03587b9898e8560909662df972c` |
| Execution pointer | `06d3a1f3a37061f93f5c9788312ae59d1356d126` |
| Reporting machinery | `77b735dcb24ed17e5a897f98f430ca1c536d787c` |
| Fixed DP | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Critical manifest | `f3b707d480b30e1d37d2c10355d8a824df4cff8230af7d78d803dd4504ef6c2b` |
| 24-role contract | `3254191ef3ff10e8ab0dda5985acb3589bb44df8534f51a8a033bca26e01c653` |
| Holdout identity | `5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a` |
| Experiment protocol | `aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f` |
| Execution plan | `41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0` |
| Unique nonce | `8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42` |

## Accepted upstream evidence

| Evidence | Path | Root |
|---|---|---|
| Corrected training corpus | `/root/autodl-tmp/camp_dp_v25_a17_corrected_full_corpus_19bcebe6_e591ab98ae575ed6` | `97a361b2bbb3544e842c9b6d12b3c17b8f63982db3217e9e360643b0cd7b0ffd` |
| Corpus independent review | `/root/autodl-tmp/camp_dp_v25_a17_corrected_full_corpus_review_shards_709a76c2` | `548a5468e585bd39bfbb58ecfd4780e6c78ff88cddb7fef985532639d8dd2c4a` |
| Train-only atom audit | `/root/autodl-tmp/camp_dp_v25_train_only_atom_audit_2e643245_20260722T094825CST` | `4dc98d9a812403148f30e2041358fbd79c967e3c8581a9d8569dc362f71d8e7e` |
| Atom audit review | `/root/autodl-tmp/camp_dp_v25_train_only_atom_audit_review_2e643245_20260722T100733CST` | `149995eacbcdf21201934bbf428ca5d8871f6c3085b4ab5e90db1d8ef78753bc` |
| Four-model training | `/root/autodl-tmp/camp_dp_v25_camp_training_863e28da_20260722T103219CST` | `8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9` |
| Training review | `/root/autodl-tmp/camp_dp_v25_camp_training_review_8fecda47_20260722T122701CST` | `ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9` |
| Calibration raw execution | `/root/autodl-tmp/camp_dp_v25_paired_calibration_execution_325cd486_20260722Tcalibration325cd486CST` | `5cd071b6ac9dd805422d7fe572f3db273abe9fce5cd4f910a0cf6fa9296e8249` |
| Calibration recovery analysis | `/root/autodl-tmp/camp_dp_v25_paired_calibration_recovery_analysis_7d924b64_20260722T145211CST` | `9d67e57bfa4a96ff3bf318c5aafd17f024207645344f076963fc5f756caa6551` |
| Calibration recovery review | `/root/autodl-tmp/camp_dp_v25_paired_calibration_recovery_review_f4a4110b_20260722T153812CST` | `650e6749bda63f23b073a5491c0f57dd9f97136a644be8ab7c918a48a3f609f7` |
| Calibration freeze | `/root/autodl-tmp/camp_dp_v25_calibration_freeze_from_paired_a52c1717_20260723TproductionCST` | `295e22adcb6c4840c678f0e1d6ea7725a9786519bf7a856285a008ee0ce4fa80` |
| Calibration freeze review | `/root/autodl-tmp/camp_dp_v25_calibration_freeze_from_paired_review_a52c1717_20260723TproductionCST` | `8d11c6794925fa99cb24183e0291c4e46f324f5a5ae8460f1bfd8aa8821eb5eb` |
| Atom mechanism | recorded by accepted root | `79c733159594ce31e204127802971e47f9461187f420c1bf90f29467ce931c07` |
| Atom mechanism review | recorded by accepted root | `214550b755fe520d601ed97138202eb1ba772a8bd851062bb14eb54a2bd87073` |
| B4 pre-open authority | `/root/autodl-tmp/camp_dp_v25_fresh_b4_preopen_authority_7be93df2_20260724TconsumerFinalCST` | `bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829` |
| B4 pre-open review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_preopen_review_7be93df2_20260724TconsumerFinalCST` | `4b4b64682addf728cafcd01dbde1e5ff837124e9be5105ed3000ab68eb18ea55` |

The accepted pre-closeout focused contract suite remains 279/279, root
`d618b6dcc509c0223038f8bf25308be6baa466b055487104a99f79c7e77d8f79`.
The terminal reporting machinery synthetic/regression suite passed 66/66 at
reporting HEAD `77b735dcb24ed17e5a897f98f430ca1c536d787c`.

## Legacy and terminal history

| Stage | State | Root evidence |
|---|---|---|
| Legacy Benchmark A | frozen read-only `honest_no_claim` | evidence/claim `044defd7e6a0fb03893b7c676182d79587d0bfe8ed9f5638687cc1093fed6808`; final review `6203712edf374433ab948781da72c30a399e1cb77e332b15beb7e4f97e883895` |
| Fresh B2 | permanent one-shot terminal failure, 0 complete pairs | closeout `b2c545ff3afa77a3d2c5a7cb91735f9859f1a70286ca3404f2d680b5b6f12363`; review `6d1d785cd452335cbce135eb4f1ecbf53edcf651a0191a07fe4d67b698d28367` |
| Fresh B3 | permanent execution artifact fatal, 0 complete pairs | closeout `b57f3d23d4d0537b315161c5c5eb1dbd2b1c095c0c0f6ac327b54ba3910b5e83`; review `b0d87070278ee2f32cbc98420f1b11701db25982a8334c2b0130e679651b3171` |
| Fresh B4 | execution full denominator; post-exposure evaluation fatal | execution `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881`; review `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d`; closeout/review above |

## Claim boundary

`claim_authorized=false`, `rerun_allowed=false`,
`raw_outcome_values_inspected=false`.

Fresh B4 SafetyCost, component, CI95, Better/Tie/Worse, stratified, NI,
latency, and post-Fresh mechanism tables are
`unavailable_due_to_post_exposure_evaluation_fatal`. No result may be
reconstructed manually from the execution artifact.
