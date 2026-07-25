# V25 Fair-Pool Adaptation Contract v5 — Raw Numeric Semantics Closure

## Outcome

This additive, outcome-independent contract closes the last provenance gap
identified in v4: numeric endpoint values are no longer accepted as
authoritative fields merely because their containing artifacts are sealed.
Every future qualification value must be reconstructed from typed, sealed raw
semantic receipts.

This package does not authorize acquisition, repeated model calls, candidate
pool generation, selector replay, closed-loop execution, Fresh or holdout
execution, training, retraining, or any scientific claim. Current status
remains `scientific_contract_review_required`.

The preserved corrected-evaluation review remains a separate-role sealed
deterministic replay using the frozen canonical evaluation core; it is not
claimed to be a reviewer-local independent statistical implementation.

The v4 contract and review remain sealed and unchanged at roots
`69bd196a91cea572484ca28b044966acd3ad85b868409d1907bec99a6ea0af47`
and
`2611ac2322f124daa1f1134e662447c5823cef0db88a9e12fb04abdc0561f954`.
They are preserved as a superseded pre-acquisition diagnostic: v4 closed
authority topology, preflight, threshold-freeze, and repeat-0 hard-evidence
bindings, but its numeric pair values were still caller-provided caches.

## Sealed v5 artifacts

- implementation HEAD:
  `67308ac05e64808edf6f37dd2ad930ccf31899e1`
- fixed DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- contract payload:
  `2188c208ef144e73e3e9b2596906842bc13709781b8758bb2047fa9fe944f5a6`
- contract:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v5_67308ac0_8680c1b19ce0620b`
- contract root:
  `78584ecc74a1a4f42e18fe0f4ee81e4fd0f48e98e33fd56c7128954c2ce0e4c6`
- independent review:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v5_review_67308ac0_8680c1b19ce0620b`
- independent review root:
  `3e0f5c5247fc3fc4e877d0c2597022a5b31c2e297023fd39cc0a58060c0491e5`
- implementation focused:
  `/root/autodl-tmp/camp_dp_v25_fair_pool_adaptation_contract_v5_focused_67308ac0_8680c1b19ce0620b`
- implementation focused root:
  `aaeb20cd5278bc8566c621eb4c654e8250d690559502e5f9debf539477b87388`
- focused result: 66/66 PASS.

The implementation was transferred to AutoDL as a content-addressed Git
bundle after a GitHub transport timeout. The bundle prerequisite was
`befcf15d9193df2cd199f961a1c623f37bad05e7`, its only ref was
`refs/heads/main=67308ac05e64808edf6f37dd2ad930ccf31899e1`, and its
pre/post-transfer SHA-256 was
`7c2e7d0a119c6ee652be0bdeeae8e467d89053fed2e57935caf2cee50c0275f4`.
Remote bundle verification and fast-forward-only merge passed.

## Typed raw semantic receipts

A future authorized qualification must supply 640 raw semantic run receipts
for development calibration and 640 for independent validation:

- 64 states;
- two generator modes;
- five repeats per mode; and
- state, mode, repeat, input, latent, model, checkpoint, forward, pool and
  selector identities.

Every run contains reconstructable preimages for:

- ego candidate trajectories, `float64 [8,80,4]`;
- neighbor trajectories, `float64 [8,A,80,4]`, with exact sorted actor
  fingerprints;
- atom vectors, `float64 [8,14]`;
- Static14D and Scene14D score vectors and masks;
- the selected action, `float64 [80,4]`; and
- executable/terminal status and post-pool zero-call receipts.

Arrays use a fixed `zlib level 9` plus standard Base64 representation. The
consumer and reviewer independently decode bytes, require canonical Base64,
verify raw and encoded SHA-256, dtype, shape, byte count and finiteness, then
recompute the full candidate-tensor SHA and all eight row SHAs.

The forward-binding SHA is derived from the exact input/state/latent,
model/checkpoint, mode/repeat, candidate, neighbor and atom preimages.
`forward_invocation_id` and `pool_id` are deterministic functions of those
hashes. A non-empty caller-created identifier cannot establish provenance.

All five repeats require these receipts. Validation repeat 0 must additionally
equal the preserved v4 candidate-pool and formal selector hard receipts.

## Independent reconstruction of 73 numeric phase keys

The producer decision and separate reviewer each derive the numeric cache from
raw receipts:

1. Fourteen atom deltas use the exact training-scale authority and compute the
   maximum normalized absolute row delta.
2. Ego and neighbor position, wrapped-heading and speed errors are recomputed
   from the raw tensors.
3. Static14D and Scene14D score errors use equal masks and shared eligible
   candidates.
4. The two within-mode phases are reconstructed first. Their 64-state q99
   values and deterministic PCG64DXSM 10,000-resample upper thresholds are
   independently verified.
5. Cross-mode normalized score deltas then use those already verified
   within-mode thresholds.
6. Margin ratios and Spearman rank errors are rebuilt from raw score/mask
   vectors.
7. Neighbor relative inflation is the per-state maximum across the three
   neighbor endpoints of cross q99 divided by the maximum of the two
   within-mode q99 values and that endpoint's resolution floor.

Only after this reconstruction may the unchanged v4/v3 phase-aware decision
topology consume the values. `endpoint_values` is an exact-float64 derived
cache; it is never an authority input.

## Separate-role independent review

The v5 reviewer does not import the v5 producer, selector, fairness, metric,
threshold or decision implementation. It has local literals for:

- array decoding and SHA reconstruction;
- all 14 training scales and 37 endpoint formulas;
- score margin and exact-tie rank behavior;
- state q99 and deterministic bootstrap generation;
- forward/pool/selector bindings;
- all five-repeat denominators; and
- the outer High trust anchor plus semantic artifact/review roots.

It independently reconstructs 1,280 raw semantic runs and all 73 numeric phase
keys before invoking the preserved v4 reviewer topology.

## Adversarial evidence

The focused suite includes two P0 attacks that are re-sealed and re-trusted,
not merely rejected because an outer hash changed:

- every calibration and validation `endpoint_values` cache is replaced with
  zero, threshold artifacts and reviews are rebuilt, and both the v4 and v5
  anchors are regenerated; producer and reviewer still reject the cache
  because the raw semantic preimages are non-zero;
- each of repeat indices 1, 2, 3 and 4 has its candidate tensor changed and
  the semantic artifact, review and outer anchor regenerated; producer and
  reviewer reject the mismatch with the raw-derived forward/pool/tensor
  binding.

A complete externally trusted synthetic chain can PASS. Arbitrary finite
numeric caches, unbound forward/pool IDs, missing raw receipts, noncanonical
arrays, selector/tensor mismatch, and unknown or duplicate identities fail
closed.

## Scientific boundary

No actual raw semantic receipt was materialized in this package. All current
counts are zero: input materialization, calibration, repeated model calls,
pool generation, selector replay, closed-loop, Fresh, holdout and training.
No B4/Fresh outcome was read and no old artifact or CAS was written.

The prior procedural hard stop and its interpretation remain unchanged:
`overconservative_equivalence_contract_triggered; functional adaptation risk
unresolved`. v5 does not prove architecture/model failure,
training-distribution or OOD drift, or a need to retrain.

The scope remains one route, one map, four density tiers and bounded
development nonholdout only. The legacy result remains
`honest_no_claim_under_frozen_preregistered_all_gate`. Nothing here authorizes
Fresh benefit, real-road or broad-ODD safety, native-ranked Top1, industrial
comfort or standards conformity, promotion, deployment, online activation or
production readiness.
