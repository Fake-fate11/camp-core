# v24 fixed-DP single-record source-probe plan

## Frozen record and seed

Choose the lexicographically minimum (map_family_id, identity_sha256,
record_key) from the sealed 401-route census. This is source-only selection;
no metric, result, risk score, candidate, or prior execution may influence the
record. Materialize that exact route against its unchanged frozen source map.

Freeze seed 24001 for scenario, candidate latent, and bootstrap namespaces.
The probe runs exactly one tick through the existing native replay runner with
fixed K=8. Formal seeds 11/12/13, training, calibration, and holdout are
forbidden.

## Existing runner boundary

Use the fixed checkpoint, args, code, request semantics, native tensor
converter, tracker, and existing v22 source-valid selection policy. The v18/v22
weights and scales are a read-only 14D baseline used only to prove the full
selector call path. They are not v24 trained weights and support no comparison
or claim.

The tick must seal all eight row hashes, the whole candidate tensor before and
after selection, source-valid/physical/source-complete masks, affine scores,
selected index/hash, candidate 0 identity to the operational DP default,
neighbor tensor, causal input, RNG state, tracker receipt, and latency. CAMP
may return only the exact indexed fixed-DP row.

## Preflight boundary

Preflight deterministically chooses and materializes the route asset, freezes
the config and SHA chain, imports dependencies, checks CUDA and disk, and
proves no related process exists. The preflight must not load the checkpoint,
run replay, generate a candidate, or access an outcome; holdout remains unopened.

The later single-record result cannot tune route choice, seeds, atoms, scales,
weights, thresholds, or the broader K=8 census. Success authorizes only the
pre-registered broader source probe; failure is attributed before any normal
bug fix and does not permit choosing a replacement record from results.
