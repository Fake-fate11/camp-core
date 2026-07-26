# V25 Selector-After-Pool Replacement Replay Report

Status:
`selector_after_pool_replay_replacement_full_denominator_independently_reviewed_high_review_required`

This bounded development/nonholdout stage replayed the production Static14D
and Scene14D no-V2I selector paths against the immutable candidate and neighbor
tensors already sealed by the corrected same-input/same-latent batch8
generator run. It made no model, DP, latent, candidate-generation, Fresh,
holdout, training or closed-loop call and read no outcome.

## Preserved failure and correction

The first replay root
`7a85ef00c10a79aa1b8e92729f51d9512e5e67d53d1ef44e00da55d19840109d`
is preserved unchanged as
`full_denominator_preselector_tolerance_wiring_failure`. Its 320/320 slots
retained typed failures: Static was called 320 times, Scene was not reached,
the candidate and neighbor tensors were never mutated, and all forbidden call
counts remained zero.

Independent closeout reconstructed the accepted Static weight vector as
shape `[14]`, finite, sum `1.0000000000000004`, minimum
`-5.9639495628241106e-18`, one negative entry, and zero entries below
`-1e-9`. The failure was therefore a consumer wiring defect: the Static
callsite omitted the accepted
`TRAINED_SIMPLEX_NONNEGATIVE_ATOL=1e-9`, causing a numerically harmless
residual to be rejected by an implicit zero default. This is not weight drift,
a selector scientific failure, training-support/OOD evidence or a retraining
result.

The additive replacement changed only replay-consumer wiring. Both production
selector callsites now pass the same sealed tolerance explicitly. Selector
defaults, weights, Theta, atoms, scales, masks, scoring, tie resolution and
candidate data are unchanged.

## Replacement evidence

High replacement authority:
`e6579ca71ccfdd7e0a94d52450b2473d4b8c52c38e8b0504e0dcb8b35935ab3c`.
Implementation HEAD:
`21c88931b0dd413493f05f7acd11e7b6c78c0111`.
Fixed DP remains
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The replacement replay:

- retained the complete 320-slot denominator: 64 states x 5 byte-identical
  repeats;
- loaded the immutable corrected raw root
  `731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4`;
- bound candidate0 structurally to row0;
- executed the production Static14D and Scene14D no-V2I selector once per
  slot, for 640 total selector calls;
- preserved before/after candidate and neighbor tensor SHA values exactly;
- recorded 0 typed failures and 0 nondeterministic states;
- recorded 0 model, DP, latent or candidate-generation calls; and
- wrote no upstream artifact or CAS.

Each slot sealed the 14D atom/source/applicability receipts, physical mask,
accepted weights/context/Theta, eight scores, best/runner-up margin, tie set,
lowest-index selection, selected index and selected action/trajectory binding.
Each arm was isolated so one arm's typed failure could not suppress the other
arm's evidence.

The separate-role reviewer did not import the producer scoring or decision
oracle. It reconstructed all 320 slots and both selector arms from the sealed
corrected tensor bytes and accepted training/scales authority, and matched all
values, masks, indices, SHA bindings and call counts exactly.

## Interpretation boundary

The accepted statement is limited to runtime selector compatibility on the
sealed corrected pools, same-pool tensor immutability, zero extra generation
calls and deterministic selection across the five identical repeats.

This does not establish training-distribution support, absence of OOD drift,
that retraining is unnecessary, scientific benefit, industrial effect,
closed-loop behavior, Fresh/holdout performance, promotion or deployment.
SafetyCost remains an immutable legacy exploratory diagnostic; old NI and
industrial-v3 effect endpoints were not read or computed. The historical
scientific conclusion remains
`honest_no_claim_under_frozen_preregistered_all_gate`.

## Engineering diagnostics

Pre-artifact keyset and callsite-validator fixture failures, plus the preflight
wrapper import-path failure, were preserved as engineering diagnostics. A
preflight stdout-control parsing issue was closed by consuming the already
sealed root and did not rerun preflight. None formed a scientific artifact or
changed the immutable 320 pools.

The implementation-focused receipt at HEAD `45f310f6` passed 31/31 tests with
root `c0b107cc5302335ace66d5d0af930fdb04f4d7177544a80fa7f316aae9615f7e`.
It is retained as implementation evidence; the final docs-focused receipt at
the pointer HEAD is the authoritative final pointer closure.

## Future-bound requirement

Only after High accepts this replacement package may a new authority combine
the industrial-v3 bounded nonholdout compute-matched closed-loop contract
design with one zero-model/pre-execution hardening sweep. That future sweep
must cover the machine parameter-propagation matrix, every production
entrypoint and consumer, PASS and typed-FAIL dry-runs, duplicate default/schema
policy removal, mutation tests, residual-risk classification, and explicit
local/AutoDL interpreter paths.

That future hardening and any closed-loop attempt are not authorized or
executed in this package. This package creates no new micro-gate or artifact
for them.
