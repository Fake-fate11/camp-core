# V25 Fair Nonholdout Qualification Evidence Index

Date: 2026-07-25 (Asia/Shanghai)

## Current classification

- Machine state:
  `v25_fair_nonholdout_pool_adaptation_hard_stop_scientific_contract_review_required`
- Method result: state-matched real selector replay PASS; pool adaptation
  hard stop CONFIRMED; compute-matched closed-loop NOT STARTED.
- Scientific result: no new claim; legacy
  `honest_no_claim_under_frozen_preregistered_all_gate` unchanged.

## Sealed artifacts

| Evidence | Root SHA-256 | Key facts |
|---|---|---|
| Outcome-independent fair contract | `480981070d1a08b1980fdf43d1f7b84eb1030c6e2742e055edff87b8825c5603` | Frozen before replay; generator, 16 states, tolerances, zero-call gate, 3x64 conditional closed-loop |
| Independent contract review | `74d45468aefb483bb73e316557d756c3899257ae35dd743979c48b539d99c93d` | Reviewer-local literal authority/root/denominator/latency/hard-stop review |
| Validation hard-stop artifact | `29688aa7ff4eb5edf43ca2379063f45228faedea80a7a3245e07aba297cc9dfd` | 16 pools, 48 real selector receipts, 128/128 ego rows, 114/128 neighbor rows, 9 drift states, 0 closed-loop ticks |
| Independent hard-stop review | `0ea09a3330fbc8eaae74be3f30114d1f0a746cd8b13adee3d839b8ad17f086c8` | Independently reconstructed pools, scores/masks/selections, tolerances, zero calls, denominator and closed-loop exclusion |
| Authoritative hard-stop focused | `2fc9cd4c5a86ab01afce93f4375c2362cc07b104d7cb1efabbf8a7e1f384a59c` | 136 tests; fixed-DP clean; hard-stop branch and no-action boundaries |

Exact paths:

- `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_contract_b7cd48b3_8680c1b19ce0620b`
- `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_contract_review_b7cd48b3_8680c1b19ce0620b`
- `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_validation_8d84e46c_8680c1b19ce0620b`
- `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_validation_hard_stop_review_3f440445_8680c1b19ce0620b`
- `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_hard_stop_focused_3f440445_8680c1b19ce0620b`

## Implementation evidence

- Starting live authority:
  `540dca71136cd43da4bc045369e28c3d6030b232`
- Fair contract/producer implementation:
  `b7cd48b3fb2a0c11228403c8804b066e566f8d14`
- Outcome-blind causal no-signal source repair:
  `8d84e46c656b0b1f83f8881cd17540e65d96370a`
- Independent BLOCK reviewer:
  `3f440445c2d56041760b37dfee5cbf01493356df`
- Fixed Diffusion Planner:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`

The first validation start created no result artifact. It stopped at the first
state because the new harness omitted the explicit no-signal causal atom
input required by the existing source-valid 14D contract. The subsequent
repair bound the same root-verified map and route, verified zero route traffic
light regulatory elements, and did not read outcomes or modify model/scientific
parameters.

## Denominators and stop evidence

| Item | Value |
|---|---:|
| Bounded nonholdout states | 16 |
| Authoritative single-invocation pools | 16 |
| Real selector executions | 48 |
| Same-pool candidate rows | 128 |
| Ego trajectory rows within frozen tolerance | 128 |
| Neighbor tensor rows within frozen tolerance | 114 |
| Neighbor rows outside tolerance | 14 |
| States with substantive drift | 9 |
| Exact repeatable batch-8 pools | 16 |
| States with mask equality | 16 |
| Static selected-index equality | 16 |
| Scene selected-index equality | 16 |
| Post-pool forbidden calls | 0 |
| Closed-loop arms started | 0 |
| Closed-loop ticks executed | 0 |

The stopped closed-loop denominator is reported as planned `3 arms x 64 ticks`
and actual `0 arms / 0 ticks`; it is not silently shrunk or treated as an
effect experiment.

## Preserved legacy evidence

The following accepted evidence remains sealed and unchanged:

- Fresh B4 execution:
  `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881`
- Fresh B4 execution review:
  `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d`
- Corrected evaluation / review:
  `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f` /
  `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459`
- Evaluation v2 second correction / review:
  `4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941` /
  `e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b`
- Continuation ledger SHA:
  `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392`

None of those artifacts supports a target-architecture effect claim.

## Decision boundary

The target architecture remains blocked before compute-matched closed-loop.
The next authority decision is a training-pool adaptation/scientific-contract
review. Retraining, a revised tolerance, additional closed-loop execution,
Fresh/holdout work, and claim changes all require new explicit authority.
