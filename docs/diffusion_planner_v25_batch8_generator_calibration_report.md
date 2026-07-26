# V25 Same-Ego Batch8 Generator-Only Calibration Report

Status: `bounded_64_state_batch8_generator_calibration_full_denominator_formed_and_independently_reviewed`

This development/nonholdout stage used the target
`new_single_invocation_batched_k8_candidate_pool` architecture. It did not
run a selector, read Fresh/B4 outcomes, train a model, or make an effect,
industrial-safety, compatibility, validation, or deployment claim.

## Authority and denominator

- High authority SHA256:
  `677c3792f52cd817871b6c9948360edced81198d4207cd59b22050080697ee21`.
- CAMP implementation HEAD:
  `cdea31b642830015113661007a456a553acd3ab8`.
- Fixed DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Source-spec manifest:
  `569718077a1c6c7f5193074ba86e646da4a3a40a2fdc573c7bfa51f3cfaa722f`.
- 64 frozen development states × 5 repeats = 320/320 completed slots.
- Each slot used exactly one same-ego B=8 formal model invocation.
- Total formal calls: 320. Sequential calls: 0. Selector calls: 0.
  Post-pool model/DP/latent/candidate-generation calls: 0.
- Candidate tensors were `[8,80,4] <f4`, finite, immutable and 8/8
  row-diverse in all slots. Neighbor tensors were `[8,32,80,4] <f4`
  and finite in all slots.
- Typed slot failures: 0. Hard-integrity failures: 0. No slot was dropped,
  replaced, resumed under a suffix, or converted to complete-case evidence.

## Independently reviewed repeatability envelope

For each state, the five repeats form ten unordered pairs. Each endpoint uses
the higher q0.99 pair statistic (`sorted[9]`). Across the 64 state values,
PCG64DXSM seed 825071 generates 10,000 state bootstrap resamples; each
resample uses `sorted[63]`, and the one-sided 95% UCB is zero-based index
9500. The frozen threshold is `max(UCB, resolution_floor)` and equality is
inside the envelope.

| Generator-only endpoint | Units | State q99 min | State q99 max | Frozen threshold |
|---|---:|---:|---:|---:|
| candidate position L2 max | m | 2.5556353313 | 8.5386366336 | 8.5386366336 |
| candidate heading wrapped abs max | rad | 0.0013318062 | 0.0073866844 | 0.0073866844 |
| candidate speed abs max | m/s | 0.0032443944 | 0.0177671178 | 0.0177671178 |
| neighbor position L2 max | m | 20.3698262224 | 63.3647317199 | 63.3647317199 |
| neighbor heading wrapped abs max | rad | 0.0883196592 | 0.4141414762 | 0.4141414762 |
| neighbor speed abs max | m/s | 0.0323903151 | 0.0917967362 | 0.0917967362 |

These values are a bounded development repeatability envelope. They are not
an independent validation result, an equivalence claim, a selector/training
support result, or a general OOD statement.

## Preserved engineering diagnostics

Before the first model call, three ordinary control defects were preserved:

1. NPZ member order was incorrectly treated as semantic tensor order.
2. A wrapper with `pipefail` interpreted a no-match `pgrep` as failure.
3. The raw producer initially omitted fixed-DP import roots.

All stopped before model load/forward and before the raw artifact existed.
The final unique scientific attempt then executed 320 calls once. Contract,
preflight, raw, and threshold artifacts remain distinct and sealed.

## Scientific boundary and next authority

SafetyCost, old NI, industrial-v3 effect leaves, atoms, scores, weights,
Static/Scene selectors, candidate0 selector receipts, training support,
validation, closed-loop, Fresh/holdout, training/retraining, promotion and
deployment were excluded. The legacy scientific result remains
`honest_no_claim_under_frozen_preregistered_all_gate`.

Only High/control may next choose a selector-adaptation reference or a
versioned v3 closed-loop design. This report does not authorize either.
