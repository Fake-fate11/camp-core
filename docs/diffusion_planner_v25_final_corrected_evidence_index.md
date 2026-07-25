# V25 Corrected-Evaluation Final Evidence Index

Date: 2026-07-25 (Asia/Shanghai)

Disposition: `honest_no_claim_under_frozen_preregistered_all_gate`

## Eleven-item acceptance checklist

| # | Deliverable | Status | Evidence boundary |
|---:|---|---|---|
| 1 | 14D atom table | complete | 14 PASS / 0 WARN / 0 FAIL; audit/review roots below |
| 2 | 26D context and leakage audit | complete | no-V2I phase-remaining available count 0; train-only scaler; future/identity/split/outcome/Fresh fields excluded |
| 3 | Static/Scene 9D/14D training and convergence | complete | four CLARABEL optimal models; gaps at or below `1e-6` |
| 4 | Corpus, split, coverage, retained failures | complete | 1,500 training identities; Fresh 500 pairs, 1,500 arms, 96,000 ticks; full denominator |
| 5 | Benchmark A/B three-arm account | complete | Legacy A remains no-claim; B4 corrected evaluation independently reviewed |
| 6 | SafetyCost six components, CI95, B-T-W, strata | complete | total gate passes; component all-gate fails both primary methods |
| 7 | Performance/comfort NI tradeoff | complete | mean jerk fails both; progress also fails Static14D |
| 8 | Ablation and atom mechanism | complete as association only | 9D/14D and leave-group diagnostics; no causal claim |
| 9 | Latency | complete as controlled benchmark timing | no deployment or online-runtime claim |
| 10 | Failure and one-time accounting | complete | B2/B3 tombstones; B4 old fatal preserved; additive continuation terminal |
| 11 | Provenance, claim boundary, paper-grade report | complete | dual-HEAD roles, roots, frozen claim rule, explicit no-claim |

## Final source and scientific identities

| Item | Value |
|---|---|
| Execution implementation source | `7be93df20deee03587b9898e8560909662df972c` |
| Release pointer | `06d3a1f3a37061f93f5c9788312ae59d1356d126` |
| Correction-authority HEAD | `dddca1c64f9e03ca515ffb4e06724b0842e33135` |
| Corrected-evaluation HEAD | `62079a71920f218f7a5269c6c01e6e3700db3723` |
| Independent-review HEAD | `6e43a625ca0a74dea569926d18fd26f0f7b552c3` |
| Fixed DP | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Execution critical manifest | `f3b707d480b30e1d37d2c10355d8a824df4cff8230af7d78d803dd4504ef6c2b` |
| 24-role contract | `3254191ef3ff10e8ab0dda5985acb3589bb44df8534f51a8a033bca26e01c653` |
| Holdout identity | `5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a` |
| Protocol | `aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f` |
| Plan | `41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0` |
| Nonce | `8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42` |

## Immutable Fresh B4 execution chain

| Artifact | Exact path | Root |
|---|---|---|
| Controller | `/root/autodl-tmp/camp_dp_v25_fresh_b4_controller_decision_7be93df2_8680c1b19ce0620b` | `06f2bf198b9983e0e15f9e0feaba52bc0d595fdd5703d73d98e21c1e8c4f08a2` |
| Opening release | `/root/autodl-tmp/camp_dp_v25_fresh_b4_opening_release_7be93df2_8680c1b19ce0620b` | `7deec7b81a1ad20dd9eb4657c0c3066ce695bc797349def843c0e7152f85851b` |
| Execution | `/root/autodl-tmp/camp_dp_v25_fresh_b4_execution_7be93df2_8680c1b19ce0620b` | `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881` |
| Execution review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_execution_review_7be93df2_8680c1b19ce0620b` | `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d` |

Execution facts: 500/500 complete pairs, 1,500/1,500 complete and terminal
arms, 96,000 ticks, identical paired set, full denominator, coverage PASS,
failed rows retained, no SafetyCost imputation, no Fresh rerun.

## Preserved superseded engineering diagnostic

| Artifact | Exact path | Root/state |
|---|---|---|
| Original evaluation control | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_chain_7be93df2_8680c1b19ce0620b` | `run.exit=1`; dual-HEAD policy error |
| Original evaluation exact dir | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_7be93df2_8680c1b19ce0620b` | absent |
| Original evaluation-review exact dir | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_review_7be93df2_8680c1b19ce0620b` | absent/not started |
| Terminal closeout | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_terminal_closeout_7be93df2_8680c1b19ce0620b` | `a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398` |
| Terminal closeout review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_terminal_closeout_review_7be93df2_8680c1b19ce0620b` | `86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062` |
| Old scientific ledger | `/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/scientific/5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a.json` | SHA `c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4`; unchanged `terminal_failure` |

Original control evidence SHA256: command
`5c2134847ef9a1686d3653d48d0147912ee5abc713cf15f574dc5ec02cc0e304`,
run.exit
`4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`,
stderr
`23ffd85aa1c6abf6c04a4bef15469fdd83a1e05a01f53aadbc6d5a4a3a1d8a60`.

The old history remains
`exposure_started -> full_denominator_formed -> terminal_failure`, reason
`post_exposure_evaluation_control_fatal`. This evidence was not deleted,
overwritten, or restated as if the failure never occurred.

## Additive correction and continuation chain

| Artifact | Exact path | Root/state |
|---|---|---|
| Correction authority | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_policy_correction_authority_dddca1c6_8680c1b19ce0620b` | `b468b5ec04379327db6ca8f736bc2ef249d7b65594891cda1e135bffbbd806f1` |
| Independent authority review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_policy_correction_authority_review_dddca1c6_8680c1b19ce0620b` | `c47ae78fdb7b5df9f050b775c3691b3abe562b7508fad42960c1ea5c9c8afc55` |
| Pre-artifact repair | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_policy_correction_repair_62079a71_8680c1b19ce0620b` | `f3696e993abd1d28fb2d194234d1b48c3a9b2fef851b7fae6460e2e62b05c027` |
| Independent repair review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_policy_correction_repair_review_62079a71_8680c1b19ce0620b` | `e622220157c46ae2a95173ad63699fd0afad03d24a6514edae92c28f746f3583` |
| Corrected evaluation | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_corrected_dddca1c6_8680c1b19ce0620b` | `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f` |
| Corrected independent review | `/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_corrected_review_dddca1c6_8680c1b19ce0620b` | `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459` |
| Continuation ledger | `/root/autodl-tmp/.camp_dp_v25_fresh_b4_evaluation_continuation_cas/625fee32ec6600d7d17345ffa5c096f3585ff91537a93f67a66dcda4335f6144.json` | `independently_reviewed_terminal` |

Continuation history:
`authorized_from_preserved_denominator -> evaluation_started ->
evaluation_artifact_formed -> independently_reviewed_terminal`.

## Correction implementation and focused evidence

| Stage | Tests | Root |
|---|---:|---|
| Initial correction machinery | 99/99 | `8b4878ac...` diagnostic |
| Correct execution role HEAD | 99/99 | `9178a426...` diagnostic |
| Arm-order consumer contract | 101/101 | `ae502c61...` diagnostic |
| Git HEAD schema | 101/101 | `3f1b69f6...` diagnostic |
| Separate evaluator/reviewer HEADs | 101/101 | `5548768d...` diagnostic |
| Historical sealed evaluation manifest | 101/101 | `7c01cd9ea5176da889186d3beffec38d6e9ab5d04e40d3fa2b4a47eea8713437` authoritative |

The authoritative focused artifact is:
`/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_policy_correction_focused_6e43a625_8680c1b19ce0620b`.
Tests use synthetic/tmp fixtures and fail closed on B3 disguise, outcome fields,
run.exit drift, directories or review appearing early, denominator drift,
root/command/error drift, duplicate/unknown fields, dual-HEAD/allowlist/manifest
drift, and consumer-contract drift.

## Accepted upstream evidence

| Evidence | Exact path or role | Root |
|---|---|---|
| Corrected training corpus | `/root/autodl-tmp/camp_dp_v25_a17_corrected_full_corpus_19bcebe6_e591ab98ae575ed6` | `97a361b2bbb3544e842c9b6d12b3c17b8f63982db3217e9e360643b0cd7b0ffd` |
| Corpus independent review | `/root/autodl-tmp/camp_dp_v25_a17_corrected_full_corpus_review_shards_709a76c2` | `548a5468e585bd39bfbb58ecfd4780e6c78ff88cddb7fef985532639d8dd2c4a` |
| Train-only atom audit | `/root/autodl-tmp/camp_dp_v25_train_only_atom_audit_2e643245_20260722T094825CST` | `4dc98d9a812403148f30e2041358fbd79c967e3c8581a9d8569dc362f71d8e7e` |
| Atom audit review | `/root/autodl-tmp/camp_dp_v25_train_only_atom_audit_review_2e643245_20260722T100733CST` | `149995eacbcdf21201934bbf428ca5d8871f6c3085b4ab5e90db1d8ef78753bc` |
| Four-model training | `/root/autodl-tmp/camp_dp_v25_camp_training_863e28da_20260722T103219CST` | `8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9` |
| Training review | `/root/autodl-tmp/camp_dp_v25_camp_training_review_8fecda47_20260722T122701CST` | `ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9` |
| Calibration freeze | `/root/autodl-tmp/camp_dp_v25_calibration_freeze_from_paired_a52c1717_20260723TproductionCST` | `295e22adcb6c4840c678f0e1d6ea7725a9786519bf7a856285a008ee0ce4fa80` |
| Calibration freeze review | `/root/autodl-tmp/camp_dp_v25_calibration_freeze_from_paired_review_a52c1717_20260723TproductionCST` | `8d11c6794925fa99cb24183e0291c4e46f324f5a5ae8460f1bfd8aa8821eb5eb` |
| Atom mechanism | accepted mechanism artifact | `79c733159594ce31e204127802971e47f9461187f420c1bf90f29467ce931c07` |
| Atom mechanism review | accepted independent review | `214550b755fe520d601ed97138202eb1ba772a8bd851062bb14eb54a2bd87073` |

## Legacy and one-time history

| Stage | State | Evidence |
|---|---|---|
| Legacy Benchmark A | frozen read-only `honest_no_claim` | evidence/claim `044defd7e6a0fb03893b7c676182d79587d0bfe8ed9f5638687cc1093fed6808`; final review `6203712edf374433ab948781da72c30a399e1cb77e332b15beb7e4f97e883895` |
| Fresh B2 | permanent one-shot terminal failure, zero complete pairs | closeout `b2c545ff3afa77a3d2c5a7cb91735f9859f1a70286ca3404f2d680b5b6f12363`; review `6d1d785cd452335cbce135eb4f1ecbf53edcf651a0191a07fe4d67b698d28367` |
| Fresh B3 | permanent first-arm artifact fatal, zero complete pairs | closeout `b57f3d23d4d0537b315161c5c5eb1dbd2b1c095c0c0f6ac327b54ba3910b5e83`; review `b0d87070278ee2f32cbc98420f1b11701db25982a8334c2b0130e679651b3171` |
| Fresh B4 old diagnostic | full denominator, original evaluator control fatal | closeout/review and old ledger above; preserved and superseded only by prospective policy authority |
| Fresh B4 corrected evaluation | reused sealed denominator; independently reviewed | evaluation/review roots above; no claim under frozen all-gate |

## Frozen result and claim boundary

- Static14D total SafetyCost delta:
  `-2.5299346354001058`, CI95
  `[-3.551884242964027, -1.5079850278361844]`, B/T/W `280/81/139`.
- Scene14D total SafetyCost delta:
  `-1.2135901546149832`, CI95
  `[-2.132750489352197, -0.29442981987776917]`, B/T/W `227/111/162`.
- Static14D component all-guardrail gate: `false`.
- Scene14D component all-guardrail gate: `false`.
- Static14D all-NI gate: `false`.
- Scene14D all-NI gate: `false`.
- Static14D safety claim: `false`.
- Scene14D safety claim: `false`.
- Static14D red-light claim: `false`.
- Scene14D red-light claim: `false`.
- Final decision: `honest_no_claim_under_frozen_preregistered_all_gate`.

No real-road safety, broad unseen-map, native-ranked Top-1, causal mechanism,
promotion, deployment, online activation, or production-readiness statement is
authorized.
