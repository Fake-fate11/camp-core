# V25 Fair-Pool Adaptation Contract v1 Evidence Index

## Authoritative package

| Evidence | Path | Root / SHA | Status |
|---|---|---|---|
| versioned contract | `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_9cb22ec1_8680c1b19ce0620b` | `b2de5b71509526407e102b3ba3aec74000290f13ab75918d0008596a6b52f824` | sealed |
| independent literal review | `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_review_9cb22ec1_8680c1b19ce0620b` | `a16a523766493826d6b5b3f4e0a8188a1019571e4491a53e3149af2bb408aa37` | PASS |
| focused tests | `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_focused_9cb22ec1_8680c1b19ce0620b` | `a0db3bc9ae56089d635372262bb8d12346869a48ac675c2e10fda50aa9ffcea3` | 24/24 PASS |
| implementation | Git HEAD | `9cb22ec1c51666d40bb1c22dba220d55809eeb36` | tracked clean at sealing |
| fixed DP | Git HEAD | `7a1d33da277a1992ec474b5383a0c963c72e04e4` | tracked clean at sealing |
| capability authority | sealed artifact | `fa94808c70ce1953d50b52497f9c4d056dabccd96e3ffdaed84faead5f2ed8e6` | read-only binding |
| training authority | sealed artifact | `8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9` | read-only binding |
| runtime atom scale file | `runtime_atom_scales.json` in training artifact | `72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb` | 14 literal scales bound |

## Independent review coverage

The reviewer imports neither the producer contract nor its threshold, decision,
or manifest oracle. Reviewer-local literals reconstruct:

- all 128 state specifications and both manifest SHA values;
- split counts, ordinals, route/map/source/seed/latent bindings and disjoint
  state-spec SHA values;
- the ID-free clone-key fields and fail-closed conflict policy;
- runtime, model, checkpoint, fixed-DP and training-scale authority;
- five-repeat pairing topology and cross-mode entry condition;
- q, quantile method, CI method/level, bootstrap seed/count, resolution and
  exceedance rules;
- margin, tie, near-tie, rank, action-equivalence and hard-fail rules;
- exact PASS/BLOCK topology, claim boundary and all zero-run counters.

## Adversarial TDD

The focused suite changes q, CI method/level, resolution floor, exceedance
rate, state/sample/split counts, split membership, repeat count, scale source,
scale index, margin/tie/rank, action-equivalence threshold, hard-fail topology,
PASS topology and claim boundary. It also tests unknown fields, zero/nonfinite
scales, exact split cardinality and state-spec zero overlap. Every post-hoc
mutation fails both producer validation and the independent literal reviewer.

## Preserved prior evidence

The previous validation and additive summary remain sealed and unchanged:

- fair validation root
  `29688aa7ff4eb5edf43ca2379063f45228faedea80a7a3245e07aba297cc9dfd`;
- validation review root
  `0ea09a3330fbc8eaae74be3f30114d1f0a746cd8b13adee3d839b8ad17f086c8`;
- additive summary root
  `d2bf378bb02976490c1527f6cc49e59ac26e521db9fb1b82792ecc04ea3cd228`;
- additive review root
  `f54e03e0b3052d37ae9a353cad9182c2e5c85338d48485674a7da1b0c01ee1b9`.

The legacy programmatic HARD STOP, 0/192 closed-loop ticks and reverse
functional evidence remain unchanged. The new contract is prospective and
does not retroactively reclassify the earlier artifact.

## Explicit non-events

`acquisition_authorized=false`. Calibration=0, repeat-model=0, pool=0,
selector=0, closed-loop=0, Fresh=0, holdout=0 and training=0. No B4/Fresh
outcome was read. No old artifact or CAS was written. No benefit, general OOD,
retraining, promotion or deployment claim is authorized.

