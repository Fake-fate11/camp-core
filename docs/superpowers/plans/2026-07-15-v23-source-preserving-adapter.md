# v23 source-preserving Lanelet2 adapter plan

## Scope

Prepare the frozen Autoware bidirectional map for the fixed DP native builder
without changing the source OSM or discarding any regulatory-element semantics.
The exact source bytes and SHA256 remain the authority.

## Observed runtime boundary

- The fixed DP builder calls `lanelet2.io.load` and imports Autoware's
  `MGRSProjector` immediately before building the routing graph.
- AutoDL has `lanelet2==1.2.2`; its Python binding exposes no regulatory-element
  factory or registration hook.
- No official `autoware_lanelet2_extension_python` module or Autoware Lanelet2
  extension shared library is installed.
- The frozen map has nine `detection_area` regulatory relations, each attached
  to a lanelet. Treating them as ignorable XML is therefore a semantic change.

## Contract

1. Inspect the original OSM read-only and record extended regulatory subtype,
   relation, and lanelet-reference counts plus source SHA256.
2. Maps without Autoware-only regulatory elements may use stock Lanelet2 plus
   the existing projection fallback.
3. Maps with `detection_area` or another frozen Autoware-only subtype require a
   real installed official Autoware extension before the projection fallback
   is allowed to install its process-local Python module.
4. A process-local projection fallback is not proof of regulatory registration.
5. Never call `sanitize_lanelet2_map`, remove relations/references, rewrite a
   subtype, or silently fall back. Fail with an exact receipt instead.
6. Success requires byte-identical source before/after preparation and an
   unmodified-source `LaneletSceneBuilder` single-map smoke.

## TDD sequence

1. Add unit tests for stock-map acceptance, exact extended-element census,
   official-module gating, fallback rejection, and source-byte identity.
2. Add a runner contract test proving adapter preparation occurs before the
   projection fallback and builder construction.
3. Run the tests red before production edits.
4. Implement the smallest read-only preparation gate and runner call-order
   change; run targeted tests green.
5. Run local `py_compile`, targeted pytest, audit tests, and `git diff --check`.

## Static review and smoke

Record package/module/shared-library capability, source relation/reference
counts, prohibited alternatives, and a reviewer verdict. Then sync AutoDL and
attempt exactly one builder load of the frozen original Autoware map. Record
stdout, stderr, exit status, source SHA256 before/after, CAMP/DP heads, commands,
and artifact hashes.

## Decision

- Pass: original bytes load through the fixed builder with the official
  extension active; continue to map-family census.
- Stop: the reviewed environment still cannot register/load the required
  element and every remaining route would delete semantics, alter the map, add
  an unapproved public source, or change the fixed-DP scientific contract.
