# V19 WOMD/Waymax and CARLA New-Data Qualification Design

## Decision

Qualify WOMD with Waymax first using official schema and documentation only.
If any frozen hard gate fails, preserve the evidence and qualify CARLA as a
synthetic closed-loop fallback. Do not download a dataset or simulator, build
an adapter, run a simulator, or compute an outcome in this gate.

## Frozen Boundaries

- Fixed DP remains `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- CAMP only affine-reranks unchanged fixed-DP K=8 tensors with nonnegative
  simplex weights and the frozen convex master.
- Candidate 0 remains `DP-default deterministic/MAP baseline` and
  `native_ranked_top1=false`.
- The causal input contract remains an unpadded, non-extrapolated three-second
  history and eight-second evaluation window with the existing 14D source
  semantics.
- Missing route speed is source-unavailable. Ego speed, statutory/default
  values, nearby lanes, and one-sided fallbacks are forbidden.
- No v18 holdout access, DP modification, training, simulator execution,
  metric calculation, promotion, deployment, activation, or claim is allowed.

## Qualification Matrix

Each source is evaluated against six conjunctive gates:

1. finite positive official speed limits on every route segment actually used;
2. lane topology/boundaries, dynamic actors, and traffic-signal state;
3. exact 3 s history plus 8 s evaluation without padding, leakage, or
   extrapolation;
4. CAMP-side materialization of the frozen DP input and unchanged DP K=8;
5. an official closed-loop execution path and corresponding safety metrics;
6. accepted terms, a legal minimum sample path, bounded peak disk, and a
   post-operation free-space floor of at least 10 GiB.

An unknown item does not pass. The first failed item is sufficient to stop a
source, but the artifact records every known pass, fail, and unknown.

## WOMD/Waymax Evidence

Official WOMD motion scenarios are nine-second windows with one second of
history and eight seconds of future. That does not satisfy the frozen
three-second causal history. Overlapping windows may not be stitched because
doing so would rely on records outside the scenario contract and cannot prove
identity/source continuity without a new data contract.

The official proto exposes lane `speed_limit_mph`, lane/map features, dynamic
tracks, and per-timestep traffic-signal lane states. Those fields establish
schema capability, not actual finite-positive coverage on candidate-used
segments; sample coverage therefore remains unproven.

Waymax provides official WOMD-based closed-loop simulation and overlap,
off-road, wrong-way, route, progression, and kinematic metrics. These do not
repair the 3 s history failure. WOMD access also requires accepting the Waymo
non-commercial dataset terms, so no sample is fetched under this gate.

Decision: WOMD/Waymax fails closed on gate 3 before download or adapter work.

## CARLA Fallback Evidence

CARLA can accumulate an online three-second history and roll forward for eight
seconds. Its OpenDRIVE-backed maps expose topology, lane markings, landmarks,
actors, and traffic-light state. A later adapter would have to read exact
finite-positive OpenDRIVE speed records for every candidate-used segment; API
defaults or current vehicle speed remain forbidden.

No CARLA runtime or source is installed locally or on AutoDL. The official
CARLA 0.9.16 Linux package is `8,346,095,504` bytes compressed. AutoDL has
`15,041,548,288` free bytes, leaving only `4,304,130,048` bytes above the
10 GiB floor. The compressed archive alone exceeds that headroom by
`4,041,965,456` bytes, before extraction or artifacts.

Decision: CARLA qualification stops before download. Continuing requires an
explicit large-download and additional-disk decision, followed by a fresh
license/source and exact-speed coverage preflight. Any future CARLA evidence
must be labelled synthetic closed-loop evidence.

## Evidence Shape

One focused, standard-library audit consumes a checked-in evidence JSON and
emits a machine-readable decision plus Markdown. Tests cover conjunctive
fail-closed behavior, the WOMD history failure, the CARLA disk calculation,
unchanged taxonomy, and the baseline name. The immutable AutoDL artifact also
contains `HEADS`, `COMMAND`, stdout/stderr, exit status, source receipts,
`SHA256SUMS`, and its root digest.

## Result State

The gate advances to:

`user_decision_required_before_carla_large_download_additional_disk_and_license_source_preflight`

The claim taxonomy is unchanged: performance no-claim; bounded offline safety
proxy supported only in its frozen observable source; closed-loop safety not
yet supported; broad CAMP over native DP Top-1 not supported.
