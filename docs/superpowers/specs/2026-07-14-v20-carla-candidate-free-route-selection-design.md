# V20 Candidate-Free CARLA Route Selection Design

## Diagnosis

The sealed Town10HD_Opt diagnosis at CAMP head
`4ede23266956eb657c151737d8f860024fd66460` found two predecessors for the
first waypoint of the former deterministic route. The waypoint is not an
OpenDRIVE topology root, and the lookup did not omit a legal predecessor.
Therefore the preregistered `cardinality > 1` branch remains fail-closed and
does not change the predecessor/source contract.

## Frozen selection rule

Using only official `carla.Map` topology, enumerate
`map.generate_waypoints(5.0)` in the existing `_waypoint_key` order. A start is
eligible only when `start.previous(5.0)` returns exactly one waypoint. From an
eligible start, accept each next step only when there is exactly one unseen
`next(5.0)` waypoint. Reject that start on zero, multiple, or repeated
successors. Select the first start that yields exactly 81 waypoints; fail
closed if none exists.

Selection must not read candidates, DP requests or responses, outcomes,
metrics, future labels, holdout data, corridor coverage, or contact-tolerance
results. It must not start a CARLA server. Route step, length, ordering, and
predecessor cardinality are frozen before the revised census.

## Acceptance

One focused test must prove ambiguous starts are skipped in canonical order,
only a unique-predecessor/unique-successor route is accepted, and absence of a
valid route fails closed. Existing v19/v20 route and census tests must pass.
After one independent review, only one revised map-only census is allowed.
