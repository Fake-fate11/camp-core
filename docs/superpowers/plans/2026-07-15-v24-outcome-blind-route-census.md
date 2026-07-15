# v24 outcome-blind route-census plan

## Frozen enumeration

For each loadable unique source blob, run one isolated worker and make one
deterministic route attempt per fixed-builder drivable start lanelet. Starting
lanelets are sorted. At every step choose the smallest numeric successor that
has not already appeared in the route. Stop at the first prefix whose
accumulated source arc length is >=80m, a dead end, a cycle, or 100 hops.

This reproduces the established fixed-DP source-only enumeration boundary
without using its random branch helper. The 80m threshold, branch rule, and
hop ceiling are frozen before any simulator result. A short, cyclic, failed,
or qualifying attempt is never redrawn: every start-lanelet attempt remains in
the denominator and failure accounting.

## Deduplication and leakage boundary

Exact route identity duplicates collapse within one adjudicated map family;
all original records retain receipts pointing to the deterministic retained
record. Exact identity uses the family identity plus the directed source
centerline sampled at 1m and quantized to 1mm.

After exact deduplication, source-only lanelet, boundary, and geometry overlap
edges use the already reviewed 3m / 20 sample / 15 degree thresholds.
corridor-overlap connected components remain indivisible for the later split;
they are not treated as independent routes and are not tuned from outcomes.

## Execution boundary

Only blobs that passed the fixed-builder smoke are executed. One worker
failure excludes that blob, keeps its receipt, and does not stop other maps.
Source SHA is checked before and after every worker. The original OSM and fixed
DP remain unchanged. During this gate the model, candidate, outcome, and
holdout stay unopened. No route asset, seed, split, training corpus, selector,
claim, deployment, or activation is created.

## Gate sequence

1. Local TDD and static source review.
2. AutoDL import/dependency/input/root/head/disk/process preflight only.
3. Commit and reread live v24 EOF.
4. Run the census exactly once only when the EOF names execution.
