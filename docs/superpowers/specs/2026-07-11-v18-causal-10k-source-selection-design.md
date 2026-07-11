# V18 Causal nuPlan 10k Source Selection Design

## Scope

Build one immutable, label-free 10,000-record causal source manifest before any
10k fixed-DP candidate generation. This gate may read official nuPlan SQLite
metadata and decision-time causal inputs. It must not read expert-future values,
load the DP model, generate candidates, materialize atoms, train, calibrate,
evaluate, or change the frozen bounded-offline safety protocol.

## Frozen parent and split

- Parent source is the refreshed mini v2 manifest at SHA256
  `bcf19b29b9c3654f41502d494a441858142d2d9c3b77bd686b5a764c1107d7a2`.
- The parent contributes 367 adapter-validated scenes across 46 logs.
- Preserve every parent's existing seed-3407 whole-log assignment: 25 train,
  9 calibration, and 12 holdout logs. A log or scene may not migrate splits.
- Exclude all 367 parent decision tokens. Every selected 10k decision identity
  must therefore be new relative to the mini corpus.

## Deterministic selection

For every parent scene, enumerate distinct official `scenario_tag` lidar ticks
whose timestamp has at least 3 seconds of scene history and 8 seconds of future
timestamp coverage. Timestamp coverage is an availability check only; no future
pose, box, trajectory, or outcome value may be queried.

Order candidates by SHA256 of
`3407:{split}:{log_token}:{scene_token}:{decision_token}`. For each candidate,
run the existing causal adapter and require the exact v2 causal schema, no key
containing `future`, finite arrays, valid source dt, and a reproducible causal
input SHA256. Adapter failures remain recorded with stable failure class and are
excluded rather than repaired or replaced with fallback sources.

Accept exactly 6,000 train, 2,000 calibration, and 2,000 sealed-holdout records.
No log may contribute more than 500 accepted records and no scene more than 64.
The completed manifest must cover at least 30 logs and 30 scenes, have unique
`(split, log_token, scene_token, decision_token)` identities, and have zero log
and scene overlap across splits. If any target or invariant cannot be met, do
not publish a 10k manifest.

## Output and naming

The manifest records immutable source paths, decision timestamp, scenario
types, causal schema/shapes/SHA256, static/neighbor counts, parent manifest
SHA256, selection policy, and split. A sidecar records attempted adapter
failures and a summary records counts, caps, overlaps, zero label/model calls,
and the controller pointer.

Because 10k contains multiple decisions per scene, candidate and canonical NPZ
paths must use `scene_token__decision_token.npz`. This is an identity/path fix
only; it cannot modify a DP candidate tensor, candidate order, K=8, candidate-0
semantics, an atom, a feasibility mask, or a label.

## Unchanged boundaries

- DP remains fixed at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Candidate 0 remains the fixed-DP deterministic/MAP baseline, not native
  ranked Top-1.
- Canonical score remains affine on the nonnegative 14D simplex and the
  CVaR/L2 master remains convex.
- All-K-infeasible records remain auditable but fail-closed excluded.
- Exact OBB feasibility remains limited to the frozen 32-dynamic + 5-static
  observable source and is not complete-scene or closed-loop safety evidence.
- `camp_dp_bounded_offline_safety_score_v1` remains frozen at protocol SHA256
  `54022f480b53d1a036af82f81b4d9124b333bda1971a07122523e9e692a6f94b`.
- The 10k holdout stays label-sealed until its separately frozen one-shot
  paired-evaluation gate.
