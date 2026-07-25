# V25 Fair-Pool Adaptation Contract v4 — Qualification Provenance Closure

## Outcome

This additive, outcome-independent contract closes the qualification
provenance gap found in v3. It does **not** authorize acquisition, model/pool
generation, selector replay, closed-loop execution, Fresh/holdout execution,
training, retraining, or a scientific claim.

Current status:
`v25_fair_pool_adaptation_contract_v4_provenance_fail_closed_acquisition_unauthorized_scientific_contract_review_required`.

The prior v3 contract remains sealed and unchanged at roots
`4365d56f0a7faa3bc73035fa731f3985ceff601c17ec0c75fbd1b81e4bc5a7ec`
and
`5f64756e952be9b502e4b40f8acf1f40e83cef3219858ab9ea5835e78f05d1e1`;
it is now classified as a superseded pre-acquisition diagnostic because its
qualification receipt could be structurally valid without sealed scientific
provenance.

## Sealed v4 artifacts

- implementation HEAD:
  `726d68343770cab44c8b8bf790c670d7ed1270a6`
- fixed DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- contract payload:
  `04cc1e685c61b6c1a5fe391b1fd1dbed4af07494a50e485b610389fca453cc6c`
- contract:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v4_726d6834_8680c1b19ce0620b`
- contract root:
  `69bd196a91cea572484ca28b044966acd3ad85b868409d1907bec99a6ea0af47`
- independent review:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v4_review_726d6834_8680c1b19ce0620b`
- independent review root:
  `2611ac2322f124daa1f1134e662447c5823cef0db88a9e12fb04abdc0561f954`
- implementation focused:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v4_focused_726d6834_8680c1b19ce0620b`
- focused root:
  `ad7056c6a83ca9098454d301bab1e0ef8e9892cce9c2da061018a345a1a846e8`
- focused result: 57/57 PASS.

## External High trust anchor

The qualification consumer no longer accepts roots supplied only inside a
qualification package. Its API requires an independent
`expected_trust_anchor_root_sha256` received out of band from the versioned
High control task `019f92d8-c971-7b13-924e-873ae9f24c14`.

That anchor must pin exact roots for:

1. acquisition authority and its independent review;
2. full input-only preflight and its independent review;
3. development-calibration receipts and their independent review;
4. the pre-validation threshold freeze and its independent review; and
5. independent-validation receipts and their independent review.

All ten artifacts use exact content-addressed schemas. A well-formed but
arbitrary root, an internally self-consistent root set, or a package-created
replacement anchor is an authority failure.

## Full preflight revalidation

The split-preflight artifact carries the complete route bytes, map bytes,
sealed B4 prepared-runtime-cases bytes, all 128 actual input tensor preimages,
and the complete preflight receipt.

Both producer and reviewer rebuild:

- the deterministic source scene;
- input tensor manifests;
- latent manifests;
- clone payloads and clone keys;
- the B4 forbidden inventory from exact sealed bytes; and
- all within-calibration, within-validation, cross-split, and B4 overlap
  counts.

A status string or a receipt SHA without these preimages cannot authorize a
qualification.

## Calibration freeze before validation

The frozen topology remains:

- 64 development-calibration states;
- 64 independent-validation states;
- 5 repeats per mode;
- 10 within-mode repeat pairs per state;
- 5 matched cross-mode pairs per state;
- state as the independent decision unit.

Each run receipt binds the actual input manifest, state, latent, fixed-DP
HEAD, checkpoint, model source, forward invocation, model-call count, pool ID,
candidate tensor SHA, and eight row SHAs.

Each pair receipt binds two exact run roots plus all applicable endpoint
values. The threshold-freeze artifact contains all 73 numeric phase keys,
64 state IDs, the 10-or-5 pair roots per state, state q99 statistics, the
complete deterministic PCG64DXSM bootstrap preimage/result, the resolution
floor, and the final threshold. It records zero validation
model/pool/selector calls at seal time. Validation must bind this exact freeze
and review root.

The consumer recomputes every state statistic and threshold. A post-validation
large threshold, even if self-hashed and re-sealed, fails semantic
reconstruction.

## Validation provenance and hard gates

Each validation split contains 640 run receipts and 1,600 pair receipts.
Numeric state values are rebuilt from those pair receipts; naked 64-value
arrays are not authority.

For every validation state and both modes, the hard receipt contains the
actual finite `float64 [8,80,4]` candidate tensor. Producer and independent
reviewer recompute the tensor SHA and all eight row SHAs and bind them to the
input, latent, model, checkpoint, forward invocation, and pool receipts.

Static14D and Scene14D selector receipts must bind that same pool ID and
tensor SHA. The consumer recomputes masks, score-based selected indices
(smallest eligible exact-minimum tie break), and the exact selected
trajectory row. Pre/post tensor SHA equality and zero post-pool
DP/model/latent/generation calls are required. Random unique row SHAs, equal
masks, or zero actions without these bindings cannot pass.

After provenance validation, the unchanged v3 83-key phase topology performs
the bounded decision. No caller status or within-mode boolean is accepted.

## Independent review and adversarial evidence

The v4 reviewer does not import the v4 producer, input-manifest producer,
fairness implementation, or selector implementation. It uses local literals
to rebuild the trust anchor, ten artifact roots and reviews, full preflight,
640-run/1,600-pair denominators, 73 thresholds, candidate tensors, selectors,
and the v3 result vector.

Synthetic/adversarial TDD includes:

- arbitrary but valid-looking roots;
- a forged preflight PASS;
- a validation-selected huge threshold with a valid self-hash;
- eight random unique row SHAs without a bound candidate tensor; and
- equal masks/zero actions whose selector receipt is not bound to the pool.

The last four cases are also re-sealed and re-anchored in tests; both producer
and reviewer still reject them by semantic reconstruction. Only the complete
trusted synthetic chain can PASS.

## Scientific boundary

No acquisition or scientific effect result exists in this package.
All current counts are zero:
actual input materialization, calibration, repeat-model, pool, selector,
closed-loop, Fresh, holdout, and training.

The earlier procedural HARD STOP and its interpretation remain unchanged:
`overconservative_equivalence_contract_triggered; functional adaptation risk unresolved`.
This package does not establish model failure, training-distribution/OOD
drift, a need to retrain, or a reason not to retrain.

The scope remains one route, one map, four density tiers, bounded development
nonholdout only. It does not authorize Fresh benefit, real-road or broad ODD
safety, native-ranked Top1, industrial comfort/standards conformity,
promotion, deployment, online activation, or production readiness. The
legacy scientific result remains
`honest_no_claim_under_frozen_preregistered_all_gate`.
