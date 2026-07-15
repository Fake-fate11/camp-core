# V24 Map-Family Split Plan

## Boundary

Consume only the sealed, outcome-blind 401-route census. Outcomes, K=8 scores,
and holdout metrics are forbidden inputs. No model, candidate generation,
training, calibration, evaluation, or holdout execution occurs in this gate.

## Indivisibility and assignment

For the current three route-supporting families, each entire map family is
indivisible. Therefore corridor groups, route families, overlapping corridors,
map bytes, route records, and all seeds for a route cannot cross a split.

Enumerate all nonempty family-level assignments and minimize route-count
absolute deviation from train/calibration/holdout = 70/10/20. Ties prefer the
holdout route count closest to 20%, then the larger train count, then the
lexicographically smallest assignment. This source-only rule freezes:

- Kashi/standard family, 375 routes: train;
- simple-cross family, 2 routes: calibration;
- four-track-highway family, 24 routes: holdout.

The resulting train/calibration/holdout route counts are 375 / 2 / 24. The
ratio is necessarily skewed because map families are indivisible; no record is
moved across a family boundary to improve the ratio.

## Seeds

Freeze disjoint primary seed namespaces: train uses 24001, 24002, 24003, 24004,
24005; calibration uses 24101-24105; holdout uses 24201-24205. The first seed
in each split is that split's sole pilot seed. The same route and all of its
seeds remain in one split, and no numeric seed appears in two splits. This gives
1875 / 10 / 120 train/calibration/holdout route-seed records. No favorable seed
replacement or post-outcome seed expansion is allowed.

## Gate sequence

1. Static preflight validates source root, census flags, 401 unique routes,
   five corridor groups, three supporting families, outcome closure, and the
   deterministic assignment without materializing a formal split manifest.
2. Execution materializes every route identity, corridor group, family, split,
   and five-seed namespace once.
3. Independent review rehashes and recomputes zero overlap, full denominator,
   family/corridor/route/seed indivisibility, and projected counts without
   generating candidates or opening holdout.
