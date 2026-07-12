# V19 CARLA Exact-Speed Source Ladder Design

## Goal

Freeze and audit the first exact-speed source rung that can support a legal
paired CARLA smoke without reading any planner, trajectory, safety, or latency
outcome. The ladder is ordered `A -> B -> C`; the first independently reviewed
rung with at least one legal pair is permanent for the experiment.

## Frozen Ladder

The coverage unit is every OpenDRIVE `(road_id, section_id, lane_id)` segment
actually traversed by a fixed-DP candidate. Every returned speed is finite,
strictly positive, and converted to metres per second exactly once.

1. **A — official actor/landmark.** Accept only one official CARLA
   `traffic.speed_limit.*` actor or speed-limit landmark uniquely mapped to the
   candidate-used OpenDRIVE segment. Multiple different values, no ID, or an
   ambiguous mapping makes the segment unavailable.
2. **B — explicit non-junction road speed.** If A has no legal pair, accept the
   candidate-used segment only when its non-junction road has an explicit
   finite-positive OpenDRIVE `<type><speed>` record covering the segment.
3. **C — topology-derived junction exact speed.** If B has no legal pair, a
   junction connector without an explicit speed is eligible only when its
   topology is unique and every related incoming and outgoing driving road has
   an explicit finite-positive speed with one identical normalized value.
   Missing, ambiguous, or inconsistent topology or speed makes the connector
   unavailable.

Candidate eligibility is the conjunction across all traversed segments. An
all-K-ineligible record is retained with masks and reasons but excluded
fail-closed. DP-default candidate 0 must also be eligible; it is never forced.

The following remain forbidden: `Vehicle.get_speed_limit()`, current ego
speed, statutory/default/map-average values, one-sided inheritance, nearest
lane or road, interpolation, outcome-driven selection, and any fourth rung.

## Minimal Architecture

Use one small CAMP-side pure-Python module for the ladder and one thin census
CLI. The module consumes already observed OpenDRIVE IDs, explicit road speed
records, topology, and optional official actor/landmark mappings. It does not
import CARLA, launch a simulator, call DP, or compute outcomes. A later
runtime probe may produce the actor observations; its output is data, not a
new source rule.

The census CLI applies the same module to every source-only record and emits
per-rung candidate masks, per-record reasons, support counts, and a root SHA.
Independent review recomputes the masks from the frozen inputs. Scenario
selection may use only source eligibility plus existing zero-overlap rules.

This deliberately avoids a general controller, cooked Unreal asset parser,
or new dependency. Existing v19 artifact conventions and Python 3.9 standard
library are sufficient.

## Freeze and Execution Order

1. Implement and test the pure ladder contract.
2. Run map/runtime source census for A, B, and C without outcomes.
3. If candidate paths are required, generate fixed-DP K=8 tensors without
   simulator outcomes and census those paths.
4. Independently review the first rung with a legal paired smoke, then freeze
   its source inputs, scenarios, candidate hashes, seed, metrics, thresholds,
   and failure rules before either arm advances.
5. Only after the freeze review may paired closed-loop arms run.

Post-freeze source or scenario replacement is prohibited even if results are
unfavourable.

## Invariants and Stop Rules

- Fixed DP remains `7a1d33da277a1992ec474b5383a0c963c72e04e4` and produces
  unchanged K=8 tensors.
- CAMP only affine-reranks/selects those tensors using approved 14D atoms and
  nonnegative-simplex weights; the master remains convex.
- Candidate 0 remains the DP-default deterministic/MAP baseline with
  `native_ranked_top1=false`.
- Closed-loop outcomes are evaluation-only and never enter source census,
  scenario selection, training, calibration, or tuning.
- A single job/staging/final path and the 10 GiB floor apply to every gate.
- Stop if all three rungs have zero reviewed support or any fix requires a
  frozen DP, 3+8, 14D, weight, training, license, disk, formal-seed, holdout,
  deployment, activation, or broad-claim change.

Claim taxonomy remains unchanged until a separate claim decision:
`performance_claim=no_claim`, bounded offline proxy supported, closed-loop
safety not yet supported, and broad CAMP-over-native-DP-Top1 not supported.
