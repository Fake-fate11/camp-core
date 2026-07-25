# V25 Fair Nonholdout Qualification Report

Date: 2026-07-25 (Asia/Shanghai)

## Outcome

The fair target architecture is **not qualified for compute-matched
closed-loop execution**. The outcome-independent contract and its independent
review passed, and all three real selector paths passed the same-pool,
post-pool-zero-call gate on 16 development/nonholdout states. The required
pool-adaptation audit then triggered its preregistered hard stop:

- same-ego trajectory rows within frozen `atol=rtol=1e-5`: **128/128**;
- neighbor tensor rows within the same tolerance: **114/128**;
- affected states: **9/16**;
- exact batch-8 repeatability: **16/16**;
- source/physical masks equal: **16/16**;
- Static14D and Scene14D selected indices equal between batched and sequential
  pools: **16/16 for each arm**;
- post-pool model/DP, latent replacement, and candidate-generation calls:
  **0**;
- compute-matched closed-loop: **not started (0/3 arms, 0/192 ticks)**.

This is a development/nonholdout programmatic contract HARD STOP with
functional adaptation risk unresolved, not a Fresh or confirmatory result.
No training or retraining was performed.

## Frozen architecture and authority

The generator is named exactly
`new_single_invocation_batched_k8_candidate_pool`. It makes one actual
`Diffusion_Planner.forward(inputs)` invocation with a same-ego candidate axis
of eight rows. The operational default remains `batch_size=1`; this phase does
not claim that the deployed/default path natively had K=8.

The contract was sealed before any real selector replay:

| Role | Path | Root SHA-256 |
|---|---|---|
| Fair contract | `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_contract_b7cd48b3_8680c1b19ce0620b` | `480981070d1a08b1980fdf43d1f7b84eb1030c6e2742e055edff87b8825c5603` |
| Independent contract review | `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_contract_review_b7cd48b3_8680c1b19ce0620b` | `74d45468aefb483bb73e316557d756c3899257ae35dd743979c48b539d99c93d` |
| Validation / hard-stop artifact | `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_validation_8d84e46c_8680c1b19ce0620b` | `29688aa7ff4eb5edf43ca2379063f45228faedea80a7a3245e07aba297cc9dfd` |
| Independent hard-stop review | `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_validation_hard_stop_review_3f440445_8680c1b19ce0620b` | `0ea09a3330fbc8eaae74be3f30114d1f0a746cd8b13adee3d839b8ad17f086c8` |
| Authoritative hard-stop focused | `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_hard_stop_focused_3f440445_8680c1b19ce0620b` | `2fc9cd4c5a86ab01afce93f4375c2362cc07b104d7cb1efabbf8a7e1f384a59c` |
| Additive adaptation summary | `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_adaptation_summary_d74b012e_8680c1b19ce0620b` | `d2bf378bb02976490c1527f6cc49e59ac26e521db9fb1b82792ecc04ea3cd228` |
| Independent additive-summary review | `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_adaptation_summary_review_d74b012e_8680c1b19ce0620b` | `f54e03e0b3052d37ae9a353cad9182c2e5c85338d48485674a7da1b0c01ee1b9` |
| Additive-summary focused | `/root/autodl-tmp/camp_dp_v25_fair_nonholdout_adaptation_summary_focused_d74b012e_8680c1b19ce0620b` | `2c9c6238c8eb26eddd02efd2437a517f657daefad69d358b89cee958e4215ef2` |

The contract implementation HEAD is `b7cd48b3fb2a0c11228403c8804b066e566f8d14`.
The outcome-blind no-signal source binding repair HEAD is
`8d84e46c656b0b1f83f8881cd17540e65d96370a`; the independent BLOCK reviewer
HEAD is `3f440445c2d56041760b37dfee5cbf01493356df`.
The fixed Diffusion Planner remains
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The first producer start stopped before artifact formation because the
source-valid 14D materializer required an explicit causal no-signal atom
input. The repair deterministically binds the actual route lanelets, full map
SHA, route SHA, zero route traffic-light regulatory elements, and a validated
same-tick no-signal receipt. It did not use outcome values or alter any
scientific parameter.

## State-matched real selector replay

Each of the 16 bounded development states generated one authoritative K=8
pool. Candidate0, Static14D, and Scene14D then consumed the same immutable
candidate tensor. Candidate0 selected frozen row0. Static14D and Scene14D ran
the canonical 14D atom materializer, context/weight path, and selector.

Static14D selected indices were:

`[7, 5, 3, 5, 4, 2, 3, 5, 5, 3, 6, 7, 5, 3, 3, 2]`.

Scene14D selected indices were:

`[7, 2, 3, 5, 4, 2, 1, 7, 5, 5, 4, 4, 5, 4, 2, 6]`.

Both methods flipped away from row0 on 16/16 states. These are selector
execution facts only; no safety/effect interpretation is authorized.

The candidate tensor SHA was unchanged across every selector path. Every
selector receipt binds the input SHA, checkpoint/model SHA, forward invocation
ID, pool ID, candidate tensor SHA, eight row SHAs, atom matrix, masks, context,
weights, scores, selected index, selected row SHA, and zero-call counters.

## Pool adaptation audit

For each state, the authoritative single-invocation batch-8 pool was compared
with eight diagnostic batch-1 calls using the same state and per-row latent.
The nine diagnostic calls per state (one exact batch-8 repeat plus eight
batch-1 rows) occurred before pool freeze and were never available to the
selectors.

| State | Neighbor rows outside tolerance | Max neighbor abs difference | Max ego-trajectory abs difference |
|---:|---|---:|---:|
| 2 | 2, 5, 6 | `9.1552734375e-05` | `3.814697265625e-05` |
| 3 | 3, 4, 5 | `9.1552734375e-05` | `2.6702880859375e-05` |
| 4 | 2 | `8.392333984375e-05` | `2.288818359375e-05` |
| 6 | 6 | `6.103515625e-05` | `1.9073486328125e-05` |
| 7 | 1 | `7.62939453125e-05` | `3.0517578125e-05` |
| 9 | 1 | `6.103515625e-05` | `3.0517578125e-05` |
| 10 | 1, 5 | `7.62939453125e-05` | `1.9073486328125e-05` |
| 13 | 6 | `6.866455078125e-05` | `2.6702880859375e-05` |
| 15 | 3 | `7.62939453125e-05` | `3.0517578125e-05` |

The global maximum absolute neighbor difference was
`1.983642578125e-04`; tolerance classification also includes the frozen
relative tolerance, so a maximum absolute difference alone does not determine
row failure. All 128 ego-trajectory rows passed the frozen allclose rule.

The frozen contract defined **any** neighbor row outside tolerance as a
programmatic HARD STOP, so closed-loop entry was correctly blocked under that
contract. The scientific interpretation is narrower:
`overconservative_equivalence_contract_triggered; functional adaptation risk
unresolved`. The trigger proves only that the frozen neighbor-tensor allclose
rule fired. It does not prove that the batch-8 architecture is wrong, the
model failed, the training distribution or OOD behavior drifted, or retraining
is required.

The reverse functional evidence is material: ego trajectories were equivalent
for 128/128 rows, masks were equal for 16/16 states, and Static14D and
Scene14D selected indices were each equal for 16/16 states. No selector
functional selection drift was observed in these 16 states. The legacy sealed
field `possible_training_pool_adaptation_required=true` is preserved as an
overconservative contract field, not adopted as a scientific conclusion.

## Additive sealed-preimage adaptation summary

The versioned additive summary read only the sealed validation `report.json`
and `replay_preimages.npz`. It did not invoke the model, generator, selector,
repeat path, or closed loop. Exact/absolute differences are descriptive; no
new atom or score threshold was added.

| Quantity | Result |
|---|---:|
| Atom values exact equal | 977 / 1,792 |
| Atom values nonexact | 815 / 1,792 |
| Global atom maximum absolute difference | `1.2076380426831292` |
| Static14D score values exact equal | 0 / 128 |
| Static14D maximum absolute score difference | `3.999504226261032e-06` |
| Scene14D score values exact equal | 0 / 128 |
| Scene14D maximum absolute score difference | `3.400720101572746e-05` |
| Static14D selected-index flips | 0 / 16 |
| Scene14D selected-index flips | 0 / 16 |
| Primary K8 finite and diverse | 16 / 16 states |
| Sequential K8 finite and diverse | 16 / 16 states |

Per-atom exact counts and maximum absolute differences were:

| Atom | Exact rows | Maximum absolute difference |
|---|---:|---:|
| `jerk_early` | 0 / 128 | `0.1281872576902856` |
| `jerk_late` | 0 / 128 | `1.1749788285833347` |
| `jerk_full` | 0 / 128 | `1.2076380426831292` |
| `rms_acceleration` | 0 / 128 | `0.0001824689504810184` |
| `speed_limit_margin_0_0` | 128 / 128 | `0.0` |
| `speed_limit_margin_0_5` | 128 / 128 | `0.0` |
| `speed_limit_margin_1_0` | 128 / 128 | `0.0` |
| `lane_deviation` | 128 / 128 | `0.0` |
| `clearance` | 128 / 128 | `0.0` |
| `progress_shortfall` | 16 / 128 | `5.337444829223159e-05` |
| `planned_red_light_cost` | 128 / 128 | `0.0` |
| `planned_lateral_acceleration_cost` | 0 / 128 | `1.9339401811646617e-05` |
| `red_stopping_margin_cost` | 128 / 128 | `0.0` |
| `dp_prior_jerk_excess_cost` | 65 / 128 | `0.0054014542167273305` |

The mutually exclusive, exhaustive state-level primary taxonomy uses the
frozen priority recorded in the summary. It assigns 9 states to
`neighbor_tolerance` and 7 to `no_failure`; all other classes are zero. The
nonexclusive indicators likewise contain only 14 neighbor rows across 9
states. This taxonomy records why the old rule stopped execution; it is not a
new adaptation or retraining decision.

## Latency accounting

The following distributions are for the 16-state qualification replay. The
end-to-end value includes the adaptation-only diagnostic calls and is not a
pool-matched arm runtime or production deadline result.

| Stage (ms) | n | Mean | Median | p95 | p99 | Max |
|---|---:|---:|---:|---:|---:|---:|
| Input materialization | 16 | 33.522 | 26.038 | 57.482 | 122.900 | 139.255 |
| Primary pool generation | 16 | 79.001 | 57.695 | 144.912 | 343.142 | 392.699 |
| Causal sources | 16 | 3.740 | 3.675 | 4.118 | 4.169 | 4.181 |
| Atoms | 16 | 24.207 | 23.524 | 25.710 | 25.809 | 25.833 |
| Context | 16 | 2.949 | 2.938 | 3.028 | 3.034 | 3.035 |
| Weights | 16 | 0.292 | 0.290 | 0.308 | 0.316 | 0.319 |
| Three selectors, pure incremental total | 16 | 0.344 | 0.340 | 0.359 | 0.363 | 0.365 |
| Qualification end-to-end including diagnostics | 16 | 680.113 | 652.392 | 773.898 | 1037.577 | 1103.497 |

Because the hard stop prevented compute-matched closed-loop entry, per-arm
pool-matched end-to-end latency and Evaluation-v2 endpoint vectors are
unavailable. The old operational single-output latency remains a separate
architecture reference and is not substituted for the missing fair-pool
baseline.

## Independent review

The result reviewer does not import the producer selector, pool generator,
fairness oracle, or threshold tables. It independently reconstructed:

- all 16 authoritative candidate pools and 128 row bindings;
- row0 baseline and Static14D/Scene14D score, source mask, selected index and
  selected-row SHA;
- batch-8 repeatability, batch-8 versus batch-1 trajectory/neighbor allclose,
  physical/source mask equality, and selected-index equality;
- all 1,792 atom differences, 256 arm-score differences, K8
  finiteness/diversity receipts, and the exhaustive failure taxonomy;
- all post-pool zero-call counters and tensor immutability;
- the 16-state denominator, 9-state hard stop, and zero closed-loop execution.

The independent review sealed PASS for the hard-stop classification. The
original authoritative focused suite passed 136 tests; the additive-summary
focused suite passed 143 tests.

## Preserved evidence and claim boundary

The unique Fresh B4 execution, corrected evaluation, Evaluation v2, all
scientific/continuation ledgers, and all legacy values remain unchanged.
Existing B4 evidence continues to describe
`compute_augmented_candidate_expansion_plus_reranking`; it is not migrated to
the target single-invocation architecture.

No Fresh/holdout data were accessed. No Fresh arm, DP/K8, legacy evaluation, or
Evaluation-v2 materialization was rerun. No fixed-DP source/checkpoint,
CAMP weights/Theta/atoms/scales, old artifact, or CAS was written. No training
occurred.

The scientific state remains `scientific_contract_review_required`. The
legacy claim remains
`honest_no_claim_under_frozen_preregistered_all_gate`. This package does not
authorize Fresh benefit, real-road or industrial safety, broad unseen-map,
native-ranked Top1, comfort conformity, promotion, deployment, online
activation, or production-readiness claims.
