# V25 Corrected Same-Input/Same-Latent Batch8 Generator Repeatability Report

Status: `bounded_development_corrected_same_input_same_latent_generator_repeatability_calibration_full_denominator_and_independently_reviewed_envelope`

This development/nonholdout stage used the target
`new_single_invocation_batched_k8_candidate_pool` architecture. It did not
run a selector, read Fresh/B4 outcomes, train a model, or make an effect,
industrial-safety, compatibility, validation, or deployment claim.

## Correction and authority

High authority:
`eba03c38f8eb6272c9cc31de464b88752a94e622ac352ffe349c70726bbe4f77`.
CAMP implementation HEAD is
`24b4d35eb422fc3404c70f9deaf7ebb888be2095`; fixed DP remains
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The prior `677c3792…` chain is preserved unchanged as
`bounded_development_latent_resampled_candidate_pool_dispersion_diagnostic`.
Its five repeat-specific latent tensors and its thresholds were not used by
this replacement.

For each of the 64 canonical development states, the corrected preflight
derived one PCG64 latent seed solely from the new authority SHA and canonical
state clone key. It sealed one `[8,321,81,4] <f4` tensor: row0 all zero and
rows1–7 independent, finite and unique. The five repeats of a state shared
exact input and latent tensor SHA (cardinality 1 for each); repeat ordinal,
run ID and forward ID were not seed inputs.

## Full denominator and integrity

- 64 states × 5 repeats = 320/320 formal same-ego B=8 calls.
- 640 unordered within-state pairs; independent statistical n=64 states.
- Candidate tensors: `[8,80,4] <f4`, finite and unique8 for 320/320.
- Neighbor tensors: `[8,32,80,4] <f4`, finite for 320/320.
- Typed output failures: 0; hard-integrity failures: 0.
- Sequential calls: 0; selector calls: 0; post-pool model/DP/latent/candidate
  generation calls: 0.
- Outcome reads and old artifact/CAS writes: 0.

Independent raw review rebuilt all tensor SHA values, 320 receipts, 640 pair
values, the same-input/same-latent cardinalities, and failure taxonomy.

## Corrected repeatability envelope

Within each state, the 10 pair errors use higher q0.99 (`sorted[9]`). Across
64 state values, PCG64DXSM seed 825071 generates 10,000 resamples; each draw
uses `sorted[63]`, with one-sided 95% index 9500. Threshold is
`max(UCB,resolution_floor)` and equality is within the envelope.

All reconstructed pair errors and bootstrap UCB values were exactly zero.
Therefore the six frozen thresholds equal their pre-registered numerical
resolution floors:

| Endpoint | Units | UCB | Corrected threshold |
|---|---:|---:|---:|
| candidate position L2 max | m | 0 | 0.0001 |
| candidate heading wrapped abs max | rad | 0 | 0.00001 |
| candidate speed abs max | m/s | 0 | 0.0001 |
| neighbor position L2 max | m | 0 | 0.0001 |
| neighbor heading wrapped abs max | rad | 0 | 0.00001 |
| neighbor speed abs max | m/s | 0 | 0.0001 |

The threshold review independently rebuilt every pair, state statistic,
bootstrap index preimage and final floor comparison.

## Scientific boundary

The accepted statement is only: bounded development corrected
same-input/same-latent generator repeatability calibration formed its full
denominator and independently reviewed envelope.

It is not independent validation, selector compatibility, training support,
evidence that retraining is unnecessary, scientific benefit, industrial
effect, Fresh/holdout evidence, promotion or deployment readiness.
SafetyCost and old NI remain excluded; the historical result remains
`honest_no_claim_under_frozen_preregistered_all_gate`.
