# V20 CARLA Pre-Generation Route Corridor TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an outcome-free CARLA lifting corridor that gives unchanged fixed-DP K=8 candidates auditable predecessor and route-boundary source support while keeping the DP route and candidate tensor immutable.

**Architecture:** Extend the existing pure lifting contract with ordered identity directions and consecutive route chords, add one standard-library OpenDRIVE lane-section parser plus a CAMP-side corridor builder, and carry the corridor as a separately hashed capture sidecar through the existing source-probe runner. Keep source completeness distinct from paired-comparison readiness: candidate 0 may be source-complete by itself, but CAMP selection remains closed unless candidate 0 and at least one additional unchanged candidate survive the combined source mask.

**Tech Stack:** Python 3.9/3.12, standard-library `dataclasses`, `hashlib`, `json`, `math`, and `xml.etree.ElementTree`; existing NumPy arrays and CARLA 0.9.16 map APIs; pytest.

## Global Constraints

- Fixed DP stays exactly `7a1d33da277a1992ec474b5383a0c963c72e04e4`; do not modify its repository, environment, config, weights, checkpoint, decoder, or output schema.
- Preserve the DP route, mission goal, causal history, `float32 [8,80,4]` candidate tensor, and operational Top-1 bytes exactly.
- Candidate 0 remains the DP operational Top-1 baseline with `native_ranked_top1=false`; do not claim native K-ranking provenance.
- The lifting corridor is built before DP inference from the same live CARLA map, OpenDRIVE text, deterministic route, and unique topology; it never enters the DP tensor.
- Use exactly one frozen `5.0 m` predecessor step. Zero or multiple predecessors fail closed.
- Boundary samples come only from exact OpenDRIVE lane-section bounds and identity-checked `Map.get_waypoint_xodr`; no global nearest-lane search, `project_to_road=True`, identity inheritance, z fallback, speed fallback, or outcome-driven retry.
- Preserve the approved A/B/C exact-speed ladder, 14D atoms, affine `score_k(w)=a_k^T w`, approved atoms, nonnegative simplex weights, and convex master.
- Do not read outcomes, metrics, future labels, holdout, SafetyCost, ADE/FDE, or eligible-candidate counts while constructing or freezing the corridor.
- Do not hardcode a boundary-contact tolerance in this implementation plan. The later map-only census supplies it before the single K=8 probe.
- Paired selection requires candidate 0 plus at least one additional candidate after source and physical feasibility masks. This plan records source-only readiness; the closed-loop executor must reapply the same minimum after physical feasibility.
- No new orchestrator, controller, dependency, data download, simulator execution, promotion, deployment, online activation, Full36, or formal seeds `11/12/13` in this plan.
- V19 code artifacts and no-claim evidence remain historical and unchanged; the reused v19-named source-probe file receives a v20 capture schema without rewriting prior artifacts.

## File Map

- Modify `camp_core/camp_core/integrations/carla_exact_speed_source.py`: explicit ordered identity directions, route-order chords, direction-aware continuity, lane-section bounds parser, and paired-support receipt fields.
- Modify `camp_core/camp_core/integrations/carla_causal_adapter.py`: validate/hash direction metadata and build the pre-generation corridor from official CARLA topology plus OpenDRIVE bounds.
- Modify `scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py`: v20 capture schema, separate `lifting_corridor` sidecar, hash validation, and required map-only contact tolerance input.
- Modify `scripts/integrations/audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py`: validate and report minimum paired source support after the existing A/B/C speed intersection.
- Modify `camp_core/tests/test_carla_exact_speed_source.py`: route-order, decreasing-station, backtrack, receipt, and immutability regressions.
- Modify `camp_core/tests/test_carla_causal_adapter.py`: deterministic direction hashing and repeated-identity rejection.
- Create `camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py`: fake-map tests for unique predecessor, exact boundary samples, contact checks, and candidate-independent hashing.
- Modify `camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py`: v20 schema separation and corridor tamper checks.
- Modify `camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py`: combined-mask paired-support tests and direct `RouteLiftingContext` construction updates.

---

### Task 1: Preserve route order and support both station directions

**Files:**
- Modify: `camp_core/camp_core/integrations/carla_exact_speed_source.py:20-472`
- Modify: `camp_core/camp_core/integrations/carla_causal_adapter.py:13-255`
- Test: `camp_core/tests/test_carla_exact_speed_source.py:243-438`
- Test: `camp_core/tests/test_carla_causal_adapter.py:213-286`
- Test: `camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py:116-153`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py:447-457`

**Interfaces:**
- Consumes: ordered `LaneSurfaceSample` values and `continuity_epsilon_m`.
- Produces: `route_identity_directions(samples, epsilon) -> Tuple[Tuple[RouteIdentity, int], ...]` and `RouteLiftingContext.identity_directions`.
- Invariant: one identity forms one contiguous block; each block has one nonzero station direction; ordinary chords join only consecutive same-identity samples.

- [ ] **Step 1: Add RED tests for decreasing-station travel and route-order chords**

Import `route_identity_directions`, update `_route_context` to pass its result, and add these tests to `camp_core/tests/test_carla_exact_speed_source.py`:

```python
def _decreasing_surface_samples() -> tuple[LaneSurfaceSample, ...]:
    return tuple(
        LaneSurfaceSample(
            "1", 0, 1, 80.0 - float(index), 10.0 + index, 20.0,
            3.5, 4.0, False,
        )
        for index in range(81)
    )


def test_route_lift_accepts_decreasing_station_in_travel_order() -> None:
    context = _route_context(_decreasing_surface_samples())

    result = _lift(context=context)

    assert context.identity_directions == ((('1', 0, 1), -1),)
    assert result.eligible is True
    assert result.points[0].s == 80.0
    assert result.points[-1].s == 1.0


def test_route_lift_rejects_backtrack_on_decreasing_station_lane() -> None:
    candidate = tuple(
        (float(index if index < 40 else 79 - index), 0.0, 1.0, 0.0)
        for index in range(80)
    )

    result = _lift(
        candidate,
        context=_route_context(_decreasing_surface_samples()),
    )

    assert result.eligible is False
    assert result.reason == "route_topology_discontinuous"


def test_route_identity_may_not_reappear_after_departure() -> None:
    samples = (
        _surface_samples(road_id="1", stop=2)
        + _surface_samples(road_id="2", lane_id=2, start=3, stop=5)
        + _surface_samples(road_id="1", start=6, stop=8)
    )

    with pytest.raises(ValueError, match="contiguous block"):
        _route_context(samples)
```

Change the shared test constructor to make direction metadata explicit:

```python
def _route_context(samples, *, edges=()) -> RouteLiftingContext:
    tolerances = LiftingTolerances(1e-6, 1e-6, 1e-6, 1e-6)
    return RouteLiftingContext(
        samples=samples,
        edges=tuple(edges),
        identity_directions=route_identity_directions(
            samples, tolerances.continuity_epsilon_m
        ),
        route_sample_step_m=1.0,
        tolerances=tolerances,
        map_sha256="a" * 64,
        source_sha256="b" * 64,
        route_graph_sha256="c" * 64,
    )
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py -k "decreasing_station or reappear" -q
```

Expected: collection fails because `route_identity_directions` and `RouteLiftingContext.identity_directions` do not exist.

- [ ] **Step 3: Add the explicit direction contract**

Add the field and pure helper to `carla_exact_speed_source.py`:

```python
@dataclass(frozen=True)
class RouteLiftingContext:
    samples: Tuple[LaneSurfaceSample, ...]
    edges: Tuple[Tuple[RouteIdentity, RouteIdentity], ...]
    identity_directions: Tuple[Tuple[RouteIdentity, int], ...]
    route_sample_step_m: float
    tolerances: LiftingTolerances
    map_sha256: str
    source_sha256: str
    route_graph_sha256: str


def route_identity_directions(
    samples: Sequence[LaneSurfaceSample],
    continuity_epsilon_m: float,
) -> Tuple[Tuple[RouteIdentity, int], ...]:
    if not math.isfinite(continuity_epsilon_m) or continuity_epsilon_m < 0.0:
        raise ValueError("continuity epsilon must be finite and nonnegative")
    groups: list[tuple[RouteIdentity, list[LaneSurfaceSample]]] = []
    seen: set[RouteIdentity] = set()
    for sample in samples:
        if not groups or sample.identity != groups[-1][0]:
            if sample.identity in seen:
                raise ValueError("route identity must occupy one contiguous block")
            seen.add(sample.identity)
            groups.append((sample.identity, []))
        groups[-1][1].append(sample)
    directions = []
    for identity, group in groups:
        deltas = [right.s - left.s for left, right in zip(group, group[1:])]
        signs = {
            1 if delta > 0.0 else -1
            for delta in deltas
            if abs(delta) > continuity_epsilon_m
        }
        if len(signs) != 1:
            raise ValueError("route identity needs one nonzero station direction")
        direction = signs.pop()
        if any(
            direction * delta < -continuity_epsilon_m
            for delta in deltas
        ):
            raise ValueError("route identity station order is inconsistent")
        directions.append((identity, direction))
    return tuple(directions)
```

- [ ] **Step 4: Replace sorting with consecutive route chords and direction-aware continuity**

Replace `_surface_chords` and the same-identity branch of `_continuous`:

```python
def _surface_chords(
    context: RouteLiftingContext,
) -> Tuple[Tuple[LaneSurfaceSample, LaneSurfaceSample], ...]:
    return tuple(
        (left, right)
        for left, right in zip(context.samples, context.samples[1:])
        if left.identity == right.identity
    )


def _continuous(previous, current, departed, context) -> bool:
    if previous is None:
        return True
    assert previous.identity is not None and current.identity is not None
    assert previous.s is not None and current.s is not None
    if previous.identity == current.identity:
        direction = dict(context.identity_directions)[current.identity]
        return (
            direction * (current.s - previous.s)
            + context.tolerances.continuity_epsilon_m
            >= 0.0
        )
    return (
        current.identity not in departed
        and (previous.identity, current.identity) in set(context.edges)
    )
```

In `_validate_lifting_context`, recompute the directions and require exact equality:

```python
expected_directions = route_identity_directions(
    context.samples, context.tolerances.continuity_epsilon_m
)
if context.identity_directions != expected_directions:
    raise ValueError("route identity direction metadata mismatch")
```

- [ ] **Step 5: Hash and deserialize the new field everywhere it is constructed**

In `build_route_lifting_context`, compute directions once, include ordered directions in `route_graph_sha256`, and pass the field to the context:

```python
directions = route_identity_directions(
    samples, tolerances.continuity_epsilon_m
)
route_graph_sha256 = canonical_json_sha256(
    {
        "identity_directions": [
            [list(identity), direction] for identity, direction in directions
        ],
        "directed_edges": edges,
    }
)
context = RouteLiftingContext(
    samples=tuple(samples),
    edges=tuple(edges),
    identity_directions=directions,
    route_sample_step_m=float(route_sample_step_m),
    tolerances=tolerances,
    map_sha256=map_sha256,
    source_sha256=source_sha256,
    route_graph_sha256=route_graph_sha256,
)
```

Update the two direct test constructors and the source-probe `_context` loader. The loader must parse the canonical JSON shape exactly:

```python
identity_directions=tuple(
    (tuple(identity), int(direction))
    for identity, direction in raw["identity_directions"]
),
```

- [ ] **Step 6: Run Task 1 tests and commit**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py camp_core\tests\test_carla_causal_adapter.py camp_core\tests\test_diffusion_planner_v19_carla_exact_speed_sources.py -q
git diff --check
```

Expected: all three files pass; `git diff --check` prints nothing.

Commit only the Task 1 files:

```powershell
git add -- camp_core/camp_core/integrations/carla_exact_speed_source.py camp_core/camp_core/integrations/carla_causal_adapter.py camp_core/tests/test_carla_exact_speed_source.py camp_core/tests/test_carla_causal_adapter.py camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py
git commit -m "Add direction-aware CARLA route lifting"
```

---

### Task 2: Build the candidate-independent OpenDRIVE route corridor

**Files:**
- Modify: `camp_core/camp_core/integrations/carla_exact_speed_source.py`
- Modify: `camp_core/camp_core/integrations/carla_causal_adapter.py`
- Create: `camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py`

**Interfaces:**
- Produces: `LaneSectionBounds`, `parse_opendrive_lane_section_bounds(xml_text)`, `CARLA_ROUTE_CORRIDOR_SCHEMA`, and `build_pre_generation_route_corridor(...) -> dict[str, Any]`.
- Consumes: the already selected deterministic route, `route[0].previous(5.0)`, `Map.get_waypoint_xodr`, frozen OpenDRIVE text, station allowance, and a caller-supplied map-only contact tolerance.
- Output keys: `schema_version`, `map_sha256`, `route_sample_step_m`, `station_allowance_m`, `contact_tolerance_m`, `route_samples`, `directed_edges`, `identity_directions`, `predecessor_receipt`, `boundary_receipts`, `max_contact_gap_m`, and `corridor_sha256`.

- [ ] **Step 1: Add RED parser tests with exact lane-section bounds**

Create `camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py` with a two-section OpenDRIVE fixture and this assertion:

```python
def test_lane_section_bounds_use_next_start_or_road_length() -> None:
    bounds = parse_opendrive_lane_section_bounds(XODR)

    assert bounds == (
        LaneSectionBounds("1", 0, 0.0, 40.0),
        LaneSectionBounds("1", 1, 40.0, 100.0),
        LaneSectionBounds("2", 0, 0.0, 25.0),
    )
```

The fixture must contain `<road id="1" length="100">` with lane-section starts `0` and `40`, plus `<road id="2" length="25">` with one start at `0`.

- [ ] **Step 2: Add RED corridor tests for predecessor and boundary contracts**

Use small fake waypoint/map classes whose `previous` and `get_waypoint_xodr` calls are recorded. Add these exact behavior tests:

```python
def test_corridor_adds_unique_predecessor_without_changing_route() -> None:
    route, map_api = _route_and_map(predecessor_count=1)
    original = tuple(_waypoint_record(item) for item in route)

    corridor = build_pre_generation_route_corridor(
        route=route,
        map_api=map_api,
        opendrive_xml=XODR,
        route_sample_step_m=5.0,
        station_allowance_m=3.0518578125e-05,
        contact_tolerance_m=0.01,
    )

    assert tuple(_waypoint_record(item) for item in route) == original
    assert corridor["predecessor_receipt"]["predecessor_count"] == 1
    assert corridor["predecessor_receipt"]["route_step_m"] == 5.0
    assert corridor["route_samples"][0]["s"] < route[0].s
    assert len(corridor["corridor_sha256"]) == 64


@pytest.mark.parametrize("predecessor_count", [0, 2])
def test_corridor_requires_exactly_one_predecessor(predecessor_count: int) -> None:
    route, map_api = _route_and_map(predecessor_count=predecessor_count)

    with pytest.raises(ValueError, match="exactly one predecessor"):
        build_pre_generation_route_corridor(
            route=route,
            map_api=map_api,
            opendrive_xml=XODR,
            route_sample_step_m=5.0,
            station_allowance_m=3.0518578125e-05,
            contact_tolerance_m=0.01,
        )


def test_corridor_records_inward_verified_boundary_samples() -> None:
    route, map_api = _route_and_map(predecessor_count=1)

    corridor = _corridor(route, map_api)

    first = corridor["boundary_receipts"][0]
    assert first["exact_entry_s"] == 0.0
    assert first["lookup_entry_s"] == pytest.approx(3.0518578125e-05)
    assert first["direction"] == 1
    assert map_api.xodr_calls
    assert all(item["identity_verified"] for item in corridor["boundary_receipts"])


def test_corridor_rejects_unsupported_boundary_contact() -> None:
    route, map_api = _route_and_map(predecessor_count=1, contact_gap_m=0.02)

    with pytest.raises(ValueError, match="boundary contact"):
        _corridor(route, map_api, contact_tolerance_m=0.01)
```

- [ ] **Step 3: Run the new test file and confirm RED**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v20_carla_route_corridor.py -q
```

Expected: collection fails because the v20 parser and corridor builder do not exist.

- [ ] **Step 4: Add the strict standard-library lane-section parser**

Add this type and parser to `carla_exact_speed_source.py`:

```python
@dataclass(frozen=True)
class LaneSectionBounds:
    road_id: str
    section_id: int
    start_s: float
    end_s: float


def parse_opendrive_lane_section_bounds(
    xml_text: str,
) -> Tuple[LaneSectionBounds, ...]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError("invalid OpenDRIVE XML") from exc
    result = []
    seen_roads = set()
    for road in root.findall("road"):
        road_id = road.get("id")
        try:
            length = float(road.get("length", ""))
        except ValueError as exc:
            raise ValueError("OpenDRIVE road length is invalid") from exc
        if not road_id or road_id in seen_roads or not math.isfinite(length) or length <= 0.0:
            raise ValueError("OpenDRIVE road metadata is invalid")
        seen_roads.add(road_id)
        sections = road.findall("./lanes/laneSection")
        starts = []
        for section in sections:
            try:
                starts.append(float(section.get("s", "")))
            except ValueError as exc:
                raise ValueError("OpenDRIVE lane-section start is invalid") from exc
        if starts != sorted(starts) or any(
            not math.isfinite(value) or value < 0.0 or value >= length
            for value in starts
        ) or any(right <= left for left, right in zip(starts, starts[1:])):
            raise ValueError("OpenDRIVE lane-section bounds are invalid")
        for section_id, start_s in enumerate(starts):
            end_s = starts[section_id + 1] if section_id + 1 < len(starts) else length
            result.append(LaneSectionBounds(road_id, section_id, start_s, end_s))
    if not result:
        raise ValueError("OpenDRIVE contains no lane-section bounds")
    return tuple(result)
```

- [ ] **Step 5: Implement the corridor builder with one candidate-free path**

Add `CARLA_ROUTE_CORRIDOR_SCHEMA = "dp_camp_v20_carla_route_corridor_v1"` and this public signature to `carla_causal_adapter.py`:

```python
def build_pre_generation_route_corridor(
    *,
    route: Sequence[Any],
    map_api: Any,
    opendrive_xml: str,
    route_sample_step_m: float,
    station_allowance_m: float,
    contact_tolerance_m: float,
) -> dict[str, Any]:
```

The body must execute in this fixed order:

```python
if len(route) < 2:
    raise ValueError("route corridor needs at least two future samples")
for name, value in (
    ("route step", route_sample_step_m),
    ("station allowance", station_allowance_m),
):
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
if not math.isfinite(contact_tolerance_m) or contact_tolerance_m < 0.0:
    raise ValueError("contact tolerance must be finite and nonnegative")
predecessors = list(route[0].previous(route_sample_step_m))
if len(predecessors) != 1:
    raise ValueError("route corridor requires exactly one predecessor")
source_waypoints = [predecessors[0], *route]
```

Group `source_waypoints` by consecutive `(road_id, section_id, lane_id)`, reject any identity that reappears after departure, and derive each group direction from its ordered station deltas. For every group, look up its `LaneSectionBounds` and compute:

```python
exact_entry_s = bounds.start_s if direction == 1 else bounds.end_s
exact_exit_s = bounds.end_s if direction == 1 else bounds.start_s
lookup_entry_s = exact_entry_s + direction * station_allowance_m
lookup_exit_s = exact_exit_s - direction * station_allowance_m
```

Require `lookup_entry_s` and `lookup_exit_s` to remain strictly inside the section. Resolve both with:

```python
waypoint = map_api.get_waypoint_xodr(
    int(identity[0]), identity[2], lookup_s
)
```

Reject `None`, wrong road/section/lane, nonfinite returned station or transform XYZ, nonpositive/nonfinite lane width, station error above `station_allowance_m`, or inconsistent junction state. Convert validated waypoints with one private `_lane_surface_sample_payload(waypoint)` helper containing exactly `_ROUTE_SAMPLE_FIELDS`.

For each identity, combine its validated entry boundary, original source waypoints, and validated exit boundary; order by `direction * s`; remove adjacent stations within `station_allowance_m`; and append the samples without sorting identities globally. Add ordinary directed edges only between consecutive identity groups.

For each adjacent identity pair, compute the 3D Euclidean gap from the left exit sample to the right entry sample and reject a gap above `contact_tolerance_m`. Seal this payload:

```python
payload = {
    "schema_version": CARLA_ROUTE_CORRIDOR_SCHEMA,
    "map_sha256": hashlib.sha256(opendrive_xml.encode("utf-8")).hexdigest(),
    "route_sample_step_m": float(route_sample_step_m),
    "station_allowance_m": float(station_allowance_m),
    "contact_tolerance_m": float(contact_tolerance_m),
    "route_samples": corridor_samples,
    "directed_edges": directed_edges,
    "identity_directions": [
        [list(identity), direction] for identity, direction in directions
    ],
    "predecessor_receipt": {
        "predecessor_count": 1,
        "route_step_m": float(route_sample_step_m),
        "identity": list(_waypoint_identity(predecessors[0])),
        "s": float(predecessors[0].s),
    },
    "boundary_receipts": boundary_receipts,
    "max_contact_gap_m": max(contact_gaps, default=0.0),
}
payload["corridor_sha256"] = canonical_json_sha256(payload)
return payload
```

Each boundary receipt must contain `identity`, `direction`, `exact_entry_s`, `exact_exit_s`, `lookup_entry_s`, `lookup_exit_s`, `entry_xyz`, `exit_xyz`, `contact_to_next_m`, and `identity_verified=True`. It must not contain candidate, outcome, metric, or selector fields.

- [ ] **Step 6: Run Task 2 tests and commit**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v20_carla_route_corridor.py camp_core\tests\test_carla_exact_speed_source.py camp_core\tests\test_carla_causal_adapter.py -q
git diff --check
```

Expected: all tests pass and diff check is silent.

Commit:

```powershell
git add -- camp_core/camp_core/integrations/carla_exact_speed_source.py camp_core/camp_core/integrations/carla_causal_adapter.py camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py camp_core/tests/test_carla_exact_speed_source.py camp_core/tests/test_carla_causal_adapter.py
git commit -m "Add v20 CARLA lifting corridor builder"
```

---

### Task 3: Separate the v20 lifting corridor from the fixed-DP route

**Files:**
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py:13-263,447-457,480-543`
- Modify: `camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py`

**Interfaces:**
- Capture schema: `dp_camp_v20_carla_source_capture_v1`.
- New capture field: `lifting_corridor`, sealed by `corridor_sha256`.
- Unchanged DP fields: `route_samples`, `directed_edges`, `route_lanes`, `mission_goal_pose`, and `frames`.
- `collect_carla_source_bundle` gains required keyword `corridor_contact_tolerance_m: float`.

- [ ] **Step 1: Convert the probe fixture to v20 and add RED separation tests**

Change `_capture()` to use schema `dp_camp_v20_carla_source_capture_v1` and add a sealed `lifting_corridor`. Its route samples must include one predecessor sample before the existing DP `route_samples` and retain the original future route after it.

Add:

```python
def test_materialization_keeps_corridor_out_of_fixed_dp_route() -> None:
    capture = _capture()
    dp_route_before = np.asarray(capture["route_lanes"][0]["centerline"]).copy()

    materialized, context, _ = _probe().build_probe_materialization(
        capture,
        tolerances=LiftingTolerances(
            1.5273609989704584,
            3.0518578125e-05,
            1e-9,
            3.0518578125e-05,
        ),
    )

    assert context.samples[0].x < capture["route_samples"][0]["x"]
    np.testing.assert_array_equal(
        materialized.dp_input["route_lanes"][0, : len(dp_route_before), :2],
        dp_route_before,
    )
    assert materialized.metadata["source_metadata"]["lifting_corridor_sha256"] == (
        capture["lifting_corridor"]["corridor_sha256"]
    )


def test_materialization_rejects_corridor_sha_drift() -> None:
    capture = _capture()
    capture["lifting_corridor"]["route_samples"][0]["x"] -= 1.0

    with pytest.raises(ValueError, match="corridor SHA mismatch"):
        _probe().build_probe_materialization(
            capture,
            tolerances=LiftingTolerances(1.5, 1e-6, 1e-6, 1e-6),
        )
```

- [ ] **Step 2: Run the probe tests and confirm RED**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v19_carla_candidate_source_probe.py -q
```

Expected: failures show the v19 capture schema and use of top-level `route_samples` for lifting.

- [ ] **Step 3: Wire the sidecar into capture before actor spawn or DP inference**

Import `build_pre_generation_route_corridor`, set:

```python
CAPTURE_SCHEMA = "dp_camp_v20_carla_source_capture_v1"
```

Change the collector signature and construct the corridor immediately after obtaining the route and OpenDRIVE text:

```python
def collect_carla_source_bundle(
    world: Any,
    *,
    source_head: str,
    corridor_contact_tolerance_m: float,
    route_sample_step_m: float = 5.0,
    route_point_count: int = 81,
) -> dict[str, Any]:
    _require_sha256(source_head, "source head")
    map_api = world.get_map()
    xodr = map_api.to_opendrive()
    route = _deterministic_route(map_api, route_sample_step_m, route_point_count)
    samples, edges, route_lanes = _route_source(route)
    lifting_corridor = build_pre_generation_route_corridor(
        route=route,
        map_api=map_api,
        opendrive_xml=xodr,
        route_sample_step_m=route_sample_step_m,
        station_allowance_m=FROZEN_LIFTING_TOLERANCES.station_epsilon_m,
        contact_tolerance_m=corridor_contact_tolerance_m,
    )
```

Keep the existing `route_samples`, `directed_edges`, and `route_lanes` entries unchanged and add only:

```python
"lifting_corridor": lifting_corridor,
```

- [ ] **Step 4: Validate the sidecar hash and build lifting only from it**

At the start of `build_probe_materialization`, add:

```python
corridor = capture.get("lifting_corridor")
if not isinstance(corridor, Mapping):
    raise ValueError("CARLA lifting corridor is missing")
corridor_payload = dict(corridor)
sealed_corridor_sha256 = corridor_payload.pop("corridor_sha256", None)
if sealed_corridor_sha256 != canonical_json_sha256(corridor_payload):
    raise ValueError("CARLA lifting corridor SHA mismatch")
if corridor.get("map_sha256") != capture.get("map_sha256"):
    raise ValueError("CARLA lifting corridor map SHA mismatch")
```

Build `RouteLiftingContext` from `corridor["route_samples"]` and `corridor["directed_edges"]`, not from the top-level DP route. Require the resulting canonical directions to equal `corridor["identity_directions"]`. Add only these source metadata fields:

```python
"lifting_corridor_schema": corridor["schema_version"],
"lifting_corridor_sha256": sealed_corridor_sha256,
```

The `decision_id` continues hashing top-level `capture["route_samples"]`; the DP lane tensor continues encoding only `capture["route_lanes"]`.

- [ ] **Step 5: Make contact tolerance an explicit capture CLI input**

Add:

```python
parser.add_argument("--corridor-contact-tolerance-m", type=float)
```

In capture mode, require the value and pass it to the collector:

```python
if args.corridor_contact_tolerance_m is None:
    raise ValueError("capture requires a frozen corridor contact tolerance")
bundle = collect_carla_source_bundle(
    client.get_world(),
    source_head=args.source_head,
    corridor_contact_tolerance_m=args.corridor_contact_tolerance_m,
)
_write_json_atomic(args.capture_json, bundle)
```

Update `_context` to deserialize `identity_directions` as specified in Task 1.

- [ ] **Step 6: Run Task 3 tests and commit**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v19_carla_candidate_source_probe.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor.py -q
git diff --check
```

Expected: both files pass and diff check is silent.

Commit:

```powershell
git add -- scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py
git commit -m "Separate v20 lifting corridor from DP route"
```

---

### Task 4: Fail closed when paired source support has fewer than two candidates

**Files:**
- Modify: `camp_core/camp_core/integrations/carla_exact_speed_source.py:279-360`
- Modify: `scripts/integrations/audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py:130-327`
- Modify: `camp_core/tests/test_carla_exact_speed_source.py:474-610`
- Modify: `camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py:132-286`

**Interfaces:**
- Lifting receipt fields: `source_complete_candidate_count`, `paired_source_support_eligible`, and `paired_source_support_reason`.
- Combined exact-speed record exposes the same three fields after intersecting lifting and A/B/C speed masks.
- `record_source_eligible` retains its current meaning: candidate 0 and operational Top-1 are source-complete and equivalent. It does not authorize paired CAMP selection by itself.

- [ ] **Step 1: Add RED tests for one-candidate-only support**

Add to `test_carla_exact_speed_source.py`:

```python
def test_k8_receipt_requires_two_candidates_for_paired_support() -> None:
    candidates = _k8_candidates()
    candidates[1:, :, 1] = np.float32(10.0)
    before = candidates.copy()

    receipt = _lift_k8(candidates)

    np.testing.assert_array_equal(candidates, before)
    assert receipt["record_source_eligible"] is True
    assert receipt["source_complete_candidate_count"] == 1
    assert receipt["paired_source_support_eligible"] is False
    assert receipt["paired_source_support_reason"] == (
        "fewer_than_two_source_complete_candidates"
    )
    assert receipt["selected_index"] is None
```

Extend the exact-speed test fixture with `only_candidate0=True`, reseal the receipt, and add:

```python
def test_lifted_report_blocks_paired_support_with_only_candidate0(tmp_path) -> None:
    receipt = _lifting_receipt(only_candidate0=True)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    row = build_lifted_report(xodr, lifting, "B", None)["records"][0]

    assert row["record_source_eligible"] is True
    assert row["source_complete_candidate_count"] == 1
    assert row["paired_source_support_eligible"] is False
    assert row["paired_source_support_reason"] == (
        "fewer_than_two_source_complete_candidates"
    )
```

- [ ] **Step 2: Run the two tests and confirm RED**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py::test_k8_receipt_requires_two_candidates_for_paired_support camp_core\tests\test_diffusion_planner_v19_carla_exact_speed_sources.py::test_lifted_report_blocks_paired_support_with_only_candidate0 -q
```

Expected: both fail because the three paired-support fields are absent.

- [ ] **Step 3: Add the minimal receipt decision**

After `_tick_failure_reason`, add:

```python
def _paired_source_support(
    record_reason: str, mask: Sequence[bool]
) -> Tuple[bool, str]:
    if record_reason != "source_complete":
        return False, record_reason
    if sum(bool(item) for item in mask) < 2:
        return False, "fewer_than_two_source_complete_candidates"
    return True, "paired_source_support_complete"
```

In `lift_k8_route_receipt`, compute the decision and extend the existing payload before calculating `lifting_receipt_sha256`:

```python
paired_eligible, paired_reason = _paired_source_support(reason, mask)
payload.update({
    "source_complete_candidate_count": sum(bool(item) for item in mask),
    "paired_source_support_eligible": paired_eligible,
    "paired_source_support_reason": paired_reason,
})
```

Insert the three fields into the existing payload rather than replacing it. Keep `selected_index=None` and the before/after tensor hashes unchanged.

- [ ] **Step 4: Recompute paired support after the A/B/C speed intersection**

In `_validate_lifting_receipt`, recompute the lifting-level count and paired decision and reject mismatches. In `_lifted_record`, compute from `source_mask` after speed intersection:

```python
source_complete_candidate_count = sum(bool(item) for item in source_mask)
paired_source_support_eligible = (
    reason == "source_complete" and source_complete_candidate_count >= 2
)
paired_source_support_reason = (
    "paired_source_support_complete"
    if paired_source_support_eligible
    else (
        "fewer_than_two_source_complete_candidates"
        if reason == "source_complete"
        else reason
    )
)
```

Return these fields per record and add to the report summary:

```python
"paired_source_support_record_count": sum(
    row["paired_source_support_eligible"] for row in records
),
```

- [ ] **Step 5: Run Task 4 tests and commit**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py camp_core\tests\test_diffusion_planner_v19_carla_exact_speed_sources.py -q
git diff --check
```

Expected: both files pass and diff check is silent.

Commit:

```powershell
git add -- camp_core/camp_core/integrations/carla_exact_speed_source.py scripts/integrations/audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py camp_core/tests/test_carla_exact_speed_source.py camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py
git commit -m "Gate CARLA paired support on two candidates"
```

---

### Task 5: Verify the integrated implementation and prepare the map-only gate

**Files:**
- Verify only: all files listed above.
- Do not modify: fixed DP repository, v19 evidence artifacts, candidates, selectors, training code, or closed-loop runner.

**Interfaces:**
- Produces a reviewed code state ready for a separate map-only contact-tolerance census plan.
- Does not produce a K=8 probe, selected candidate, simulator outcome, metric, or claim.

- [ ] **Step 1: Compile every changed Python module**

Run:

```powershell
py -3.12 -m py_compile camp_core/camp_core/integrations/carla_exact_speed_source.py camp_core/camp_core/integrations/carla_causal_adapter.py scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py scripts/integrations/audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py
```

Expected: exit `0` and no output.

- [ ] **Step 2: Run the complete focused local suite**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core/tests/test_carla_exact_speed_source.py camp_core/tests/test_carla_causal_adapter.py camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py -q
git diff --check
git status --short --branch --untracked-files=no
```

Expected: all focused tests pass, diff check is silent, and only intended tracked changes are listed before the final commit.

- [ ] **Step 3: Push the verified implementation checkpoints**

Run:

```powershell
git push origin main
git rev-parse HEAD
git rev-parse origin/main
git ls-remote origin refs/heads/main
```

Expected: all three `main` hashes match.

- [ ] **Step 4: Fast-forward AutoDL and rerun the same focused checks**

On AutoDL, without printing credentials:

```bash
source /etc/network_turbo >/dev/null 2>&1 || true
cd /root/autodl-tmp/camp_core
git fetch --prune origin
git pull --ff-only
PYTHONPATH=/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core \
  python -m pytest \
  camp_core/tests/test_carla_exact_speed_source.py \
  camp_core/tests/test_carla_causal_adapter.py \
  camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py \
  camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py \
  camp_core/tests/test_diffusion_planner_v20_carla_route_corridor.py -q
git diff --check
git status --short --branch --untracked-files=no
git rev-parse HEAD
git -C /root/autodl-tmp/Diffusion-Planner rev-parse HEAD
git -C /root/autodl-tmp/Diffusion-Planner status --short --untracked-files=no
```

Expected: focused tests pass; CAMP equals local/GitHub; fixed DP equals `7a1d33da277a1992ec474b5383a0c963c72e04e4`; both tracked trees are clean.

- [ ] **Step 5: Stop at the next scientifically valid boundary**

Record that implementation is ready for `v20_carla_route_corridor_map_only_contact_tolerance_census_plan_only`. The next plan must freeze contact tolerance from official map geometry without loading candidates, outcomes, metrics, or holdout. It may then authorize exactly one source-only K=8 probe under the already approved v20 design; this implementation plan itself does not run that probe.
