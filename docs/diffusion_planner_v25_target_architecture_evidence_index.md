# V25 Target-Architecture Qualification Evidence Index

Date: 2026-07-25 (Asia/Shanghai)

| Evidence | Result | Authority |
|---|---|---|
| Outcome-independent architecture amendment | PASS | root `3cfba03b2fd21cfa068610f8989f0c2b1df890cf64f6b1ac4b10eae67e291c7b` |
| Independent amendment review | PASS | root `202461e5045bba42cb10ad7bbdb03c36b82c00defce2df60edd6a971d1d2fd8f` |
| Same-ego single-invocation K=8 capability | PASS, development/nonholdout only | root `fa94808c70ce1953d50b52497f9c4d056dabccd96e3ffdaed84faead5f2ed8e6` |
| Independent capability reconstruction | PASS | root `cb9f4efd5d72962513ea83777a68f3ffa5455fd731bc1cc5859b407cd9d25ac1` |
| Implementation focused tests | 52 passed, 2 skipped | root `47c099f78986b21f0fb116d1989d41fdc96a001859a4e14a860e94f33b533ba1` |
| Candidate axis | same ego, not agent-as-ego | source batch 1, expanded batch 8 |
| One-call output | finite/diverse `[8,80,4]` | tensor `02685eb0...d4d72`, pool `975404af...50e90` |
| Determinism | exact | repeated tensor SHA equal, max error 0 |
| Batch vs sequential | equivalent under frozen tolerance | `atol=rtol=1e-5`, max error `3.814697265625e-05` |
| Selector-after-pool | PASS structural boundary | three labels share pool; post-pool model/latent/generation counts 0 |
| Closed-loop/Fresh/scientific effect | NOT EXECUTED / NOT AUTHORIZED | scientific contract review required |

## Preserved immutable evidence

- B4 execution:
  `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881`
- B4 execution review:
  `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d`
- Corrected legacy evaluation/review:
  `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f`
  / `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459`
- Evaluation v2 second correction/review:
  `4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941`
  / `e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b`
- Continuation ledger SHA-256:
  `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392`
- Legacy scientific conclusion:
  `honest_no_claim_under_frozen_preregistered_all_gate`

Those roots and values were neither overwritten nor re-evaluated. They remain
evidence for the historical `compute_augmented_candidate_expansion_plus_reranking`
intervention, not for a target-architecture closed-loop effect.

## Superseded diagnostic

Capability root
`5833ba72726a0e7d0a55aa4659ae800991f029d284e730df6afee7f9fb18a967`
is retained as a pre-review engineering diagnostic. The accepted qualification
captured the latent preimage before every direct forward and cloned mutable
model inputs.

## Claim boundary

This index records a machine capability and architecture contract only.
Row0 selection for all three structural labels is not CAMP score evaluation.
No Fresh, arm, DP/K8 closed-loop, holdout, or training run occurred. No new
scientific endpoint, threshold, multiplicity rule, hard gate, benefit claim,
industrial claim, promotion, deployment, or online activation is authorized.
