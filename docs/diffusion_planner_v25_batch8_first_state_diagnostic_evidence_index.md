# V25 Single-Invocation Batch8 First-State Diagnostic Evidence Index

## Accepted runtime chain

| Role | Exact path | Root SHA256 |
|---|---|---|
| Outcome-independent contract | `/root/autodl-tmp/camp_dp_v25_single_invocation_batch8_first_state_diagnostic_contract_cf0dc3fa_8b63c356` | `8b08de216c190d02a85c76e15a9eb565b6528defb11017ff2e3e62c0832ab3d9` |
| Independent contract review | `/root/autodl-tmp/camp_dp_v25_single_invocation_batch8_first_state_diagnostic_contract_review_cf0dc3fa_8b63c356` | `8a4f8a621f9d7c65824e165fde0b31f03cd52684509721f71f366d191f69a6bd` |
| Pre-model focused tests (52/52) | `/root/autodl-tmp/camp_dp_v25_single_invocation_batch8_first_state_diagnostic_focused_cf0dc3fa_8b63c356` | `30fe043a4cd2254ceaf7599d4e523b501bbfb861bf10a2a5bee8e3a45083d35a` |
| Input-only zero-overlap preflight | `/root/autodl-tmp/camp_dp_v25_single_invocation_batch8_first_state_preflight_cf0dc3fa_8b63c356` | `f65ec544fe7fa9178debbfab97adcfc456e31f3831d2bd5f056694e46fe98a81` |
| Independent preflight review | `/root/autodl-tmp/camp_dp_v25_single_invocation_batch8_first_state_preflight_review_cf0dc3fa_8b63c356` | `f47aec6587846c7c2a933ae35c171283c10fbc431bb1133b5afb8d58ec45d192` |
| One-call diagnostic | `/root/autodl-tmp/camp_dp_v25_single_invocation_batch8_first_state_diagnostic_cf0dc3fa_8b63c356` | `6a9e1a364b6d25716a471d34039553b11521c2d911563df0e3ee0edf1ed3eec5` |
| Reviewer-repair focused tests (53/53) | `/root/autodl-tmp/camp_dp_v25_single_invocation_batch8_first_state_diagnostic_review_repair_focused_c4d34eb1_8b63c356` | `4e84046f56c7729dfe2286909d96fa9bf3e174a897958d6c99f9491e152c8e94` |
| Independent raw-byte/source review | `/root/autodl-tmp/camp_dp_v25_single_invocation_batch8_first_state_diagnostic_review_c4d34eb1_8b63c356` | `92e33a3e1747764a65d6d6b8e38645f7faa9825b2b08c980255025ac840073c3` |

## Preserved superseded diagnostics

- `be2d036d...` contract/review/focused/preflight/review roots:
  `5d301663...`, `f940213a...`, `da3e462d...`, `82789ef3...`,
  `5e6971f1...`. The later diagnostic launch stopped before the model because
  the fixed-DP package import root was absent; its diagnostic and review exact
  dirs remain absent.
- The first `cf0dc3fa...` reviewer launch failed after the diagnostic root was
  complete because canonical JSON had sorted the `base_bindings` object keys.
  Its review output dir remained absent. The repair reviewed the same diagnostic
  root without any model rerun.
- All older sequential calibration failure, closeout, diagnostic, source-audit,
  Fresh B4, Evaluation v2, metric-semantics, and CAS roots remain immutable.

## Immutable bindings and counters

- High authority SHA256:
  `8b63c3564fa3f0ae1f87c5a97794eb01cc172fc6567814411d739aa0a6e7ed14`.
- Fixed DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Contract implementation HEAD:
  `cf0dc3fa6b90611d945ae90119cee0d166f2c6b3`.
- Independent review repair HEAD:
  `c4d34eb1b1df4562f6d73d7cd1a5a1859b55a0ef`.
- Formal model calls: 1; sequential model calls: 0; selector calls: 0.
- Source ego states: 1; expanded same-ego batch rows: 8.
- Additional calibration runs: 0; threshold artifacts: 0; validation runs: 0;
  closed-loop runs: 0; Fresh/holdout runs: 0; training/retraining runs: 0.
- Outcome reads: 0; old artifact/CAS writes: 0.
- Final taxonomy: `batch8_pool_valid_diverse`.

This index is evidence for one bounded development preselector diagnostic only.
It is not a scientific-effect, deployment, industrial, or general-distribution
qualification.
