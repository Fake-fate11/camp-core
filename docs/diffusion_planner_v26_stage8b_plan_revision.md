# V26 Stage 8b forward plan revision disclosure

The original development/nonholdout Stage 8b design remains the immutable
6-family, 155-corridor, 1,786-route plan with logical SHA-256
`83aca15f323c97dab396952be5a7f40d95585e919c744b72f10f67e692d06b20`.
Its zero-model qualification evidence and all 1,786 per-route receipts remain
unchanged.

An explicit scientific-design decision creates a forward successor plan with
1,783 routes.  It excludes only parent ordinals 1185, 1187, and 1454.  They
share Nishishinjuku lanelet 423 and regulatory element 1391.  The authoritative
sidecar records an `AutowareTrafficLight` with `light_bulbs` and `refers`, but
no `ref_line`; the source-quality finding is
`upstream_map_missing_ref_line`.

The successor is derived only from already-qualified immutable parent units.
It preserves parent order, route identities, corridor inventory, source maps,
and all non-excluded source strata.  The versioned revision receipt binds both
plans, the original qualification root and hashes, the three typed failures,
and all included unit hashes.  This is a pre-model, zero-outcome design change,
not an inferred stopline repair or result-driven selection.  It does not claim
unseen-family generalization.
