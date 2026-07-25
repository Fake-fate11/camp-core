# V25 Fair-Pool Adaptation Contract v4 — Evidence Index

## Current package

| Evidence | Value |
|---|---|
| implementation HEAD | `726d68343770cab44c8b8bf790c670d7ed1270a6` |
| fixed DP HEAD | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| contract schema | `camp_dp_v25_fair_pool_adaptation_contract_v4` |
| contract payload | `04cc1e685c61b6c1a5fe391b1fd1dbed4af07494a50e485b610389fca453cc6c` |
| contract path | `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v4_726d6834_8680c1b19ce0620b` |
| contract root | `69bd196a91cea572484ca28b044966acd3ad85b868409d1907bec99a6ea0af47` |
| review path | `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v4_review_726d6834_8680c1b19ce0620b` |
| review root | `2611ac2322f124daa1f1134e662447c5823cef0db88a9e12fb04abdc0561f954` |
| implementation focused path | `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v4_focused_726d6834_8680c1b19ce0620b` |
| implementation focused root | `ad7056c6a83ca9098454d301bab1e0ef8e9892cce9c2da061018a345a1a846e8` |
| implementation focused result | 57/57 PASS |

## Qualification provenance matrix

| Layer | Exact evidence required | Consumer action |
|---|---|---|
| High trust | out-of-band expected root, High decision SHA, contract/review roots | reject package-created trust |
| acquisition authority | producer root + independent review root | validate exact authorized phases and prohibitions |
| split preflight | full receipt, route/map/B4 bytes, 128 tensor preimages | reconstruct manifests, clone keys, and zero overlap |
| calibration | 640 run receipts, 1,600 pair receipts | rebuild 64 state statistics for every key |
| threshold freeze | 73 keys, pair roots, q99, bootstrap preimage/result, floors | recompute; require seal before validation |
| validation | 640 run receipts, 1,600 pair receipts | rebuild numeric state values |
| K8 hard evidence | per-state/mode `[8,80,4]` candidate tensor | recompute tensor and row SHAs |
| selector hard evidence | pool/tensor IDs, scores, masks, selected row, zero-call receipt | reconstruct mask/index/action and immutability |
| independent review | separate local-literal implementation | reproduce complete decision |

## Required fail-closed tests

| Mutation | Required result |
|---|---|
| arbitrary 64-hex contract/authority/artifact roots | BLOCK authority failure |
| preflight PASS string with forged manifest | BLOCK |
| self-hashed threshold selected after validation | BLOCK |
| random eight unique row SHAs without tensor preimage | BLOCK |
| equal masks and zero actions without forward/pool binding | BLOCK |
| missing/duplicate/unknown artifact, run, pair, state, phase, mode, endpoint | BLOCK |
| threshold freeze after any validation call | BLOCK |
| pool/tensor/latent/model/checkpoint/forward mismatch | BLOCK |
| selector post-pool call or tensor mutation | BLOCK |
| complete externally trusted synthetic chain | eligible for bounded PASS |

The re-sealed/re-anchored adversarial variants must still fail semantic
reconstruction; rejection solely because an outer hash changed is not
sufficient evidence.

## Preserved diagnostics and immutable evidence

| Evidence | Root / status |
|---|---|
| v3 contract | `4365d56f0a7faa3bc73035fa731f3985ceff601c17ec0c75fbd1b81e4bc5a7ec` |
| v3 review | `5f64756e952be9b502e4b40f8acf1f40e83cef3219858ab9ea5835e78f05d1e1` |
| v3 classification | superseded pre-acquisition diagnostic |
| prior fair validation HARD STOP | preserved |
| interpretation | `overconservative_equivalence_contract_triggered; functional adaptation risk unresolved` |
| existing B4 / corrected evaluation / Evaluation v2 | unchanged |
| scientific and continuation ledgers | unchanged |
| fixed DP / weights / atoms / scales / claim rule | unchanged |

## Non-events

| Event | Count / value |
|---|---|
| acquisition authorized | `false` |
| actual input manifests materialized | `0` |
| calibration runs | `0` |
| repeat model runs | `0` |
| pool runs | `0` |
| selector runs | `0` |
| closed-loop runs | `0` |
| Fresh runs | `0` |
| holdout runs | `0` |
| training runs | `0` |
| Fresh/B4 outcome read | `false` |
| old artifact/CAS write | `false` |
| claim authorized | `false` |

Current scope is single-route, single-map, bounded development nonholdout with
four density tiers. No weighted total, benefit claim, general OOD equivalence,
retraining decision, Fresh, promotion, deployment, or production-readiness
claim is authorized.
