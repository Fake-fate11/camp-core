# V19 CARLA Route-Constrained Lifting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce auditable route-constrained 2D-to-3D OpenDRIVE lifting receipts for immutable fixed-DP K=8 CARLA candidates before scoring or outcomes.

**Architecture:** Extend the existing pure CARLA exact-speed module with route-surface matching and canonical receipts, reuse the existing causal transform and v19 bridge/worker SHA evidence, and extend the existing CARLA exact-speed audit CLI. Do not add a runner, controller, dependency, or DP-side code.

**Tech Stack:** Python 3.9/3.12, standard-library dataclasses/JSON/SHA256/math, existing NumPy bridge arrays, pytest, official CARLA 0.9.16 `Map.get_waypoint_xodr`.

## Global Constraints

- Fixed DP stays exactly `7a1d33da277a1992ec474b5383a0c963c72e04e4`; do not modify its repository, environment, config, weights, checkpoint, or output.
- Candidate tensors stay immutable `float32 [8,80,4]`; derived world XYZ exists only in receipts.
- Use only the inverse same-tick `agents_from_world_tf` and the pre-registered route/lane graph. No global nearest-road/lane or `project_to_road=True`.
- z comes only from identity-checked official `get_waypoint_xodr`; no z=0, ego-z constant, sample-z interpolation, or unknown-lane inheritance.
- Lift all 80 points, require unique identity/station and directed topology continuity, and fail closed per candidate.
- DP operational Top-1 is the actual single DP output, independently equivalent to candidate 0; keep `native_ranked_top1=false` and never imply native K-ranking.
- Eligibility precedes CAMP scoring. Candidate 0 must be source-complete; all-K ineligible or operational/candidate-0 mismatch excludes the record.
- Freeze numeric tolerances from official map geometry and outcome-free source census only, before any K=8 coverage census.
- Keep seed `3411`, two-scenario smoke size, A-to-B-to-C speed order, 3+8, 14D, affine/simplex/convex constraints, single staging/final, and 10 GiB floor.
- No outcome, metric, holdout, Full36, formal seed `11/12/13`, promotion, deployment, activation, model replacement, or broad claim.

## File Map

- Modify `camp_core/camp_core/integrations/carla_exact_speed_source.py`: immutable route-surface context, strict lifting, tolerance freeze, and canonical receipts.
- Modify `camp_core/tests/test_carla_exact_speed_source.py`: pure lifting, ambiguity, continuity, z, immutability, and equivalence tests.
- Modify `scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py`: active operational Top-1 provenance name only.
- Modify `camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py`: validate the operational Top-1 name and retain `native_ranked_top1=false`.
- Modify `camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py`: expose the active operational Top-1 planner name.
- Modify `scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py`: validate the active paired-arm name.
- Modify `scripts/integrations/audit_diffusion_planner_dp_camp_v19_source_support.py`: emit the active baseline name in future freeze configs.
- Modify focused v19 worker/bridge/adapter/smoke/source-support tests that assert the active name; do not rewrite historical evidence documents.
- Modify `scripts/integrations/audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py`: validate lifting receipts and combine lifting with A/B/C speed masks.
- Modify `camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py`: census receipt and fail-closed tests.

---

### Task 1: Pure route-surface lifting kernel

**Files:**
- Modify: `camp_core/camp_core/integrations/carla_exact_speed_source.py:1-328`
- Test: `camp_core/tests/test_carla_exact_speed_source.py`

**Interfaces:**
- Consumes: plain route sample/edge payloads, the same-tick world-to-ego transform, candidate XY, injected `map_api.get_waypoint_xodr`, and frozen tolerances.
- Produces: `RouteLiftingContext`, `CandidateLiftDecision`, per-point receipts, and `trajectory_lifting_sha256`.

- [ ] **Step 1: Add RED tests for one unique lift and the strict z source**

Add a fake map whose only API is `get_waypoint_xodr`, build 80 ego-frame points, and assert that the function uses the inverse transform without changing the input:

```python
def test_route_lift_uses_unique_surface_and_official_xodr_z() -> None:
    candidate = tuple((float(i), 0.0, 1.0, 0.0) for i in range(80))
    before = tuple(candidate)
    context = _route_context(samples=_straight_samples())
    result = lift_candidate_to_route_surface(
        candidate_index=0,
        candidate=candidate,
        agents_from_world_tf=((1.0, 0.0, -10.0), (0.0, 1.0, -20.0), (0.0, 0.0, 1.0)),
        context=context,
        map_api=_FakeXodrMap(z=3.5),
    )
    assert result.eligible is True
    assert result.points[0].world_x == 10.0
    assert result.points[0].world_y == 20.0
    assert result.points[0].z == 3.5
    assert result.points[-1].point_index == 79
    assert tuple(candidate) == before
```

- [ ] **Step 2: Add RED fail-closed tests**

Cover two route identities containing the same XY, excessive residual, missing/mismatched `get_waypoint_xodr`, a backward s jump, a non-edge transition, and a non-finite transform. Assert exact reasons:

```python
@pytest.mark.parametrize(
    ("fixture", "reason"),
    [
        ("overlapping_lanes", "lane_identity_ambiguous"),
        ("outside_surface", "lateral_residual_exceeds_tolerance"),
        ("missing_xodr", "xodr_waypoint_missing"),
        ("wrong_section", "xodr_identity_mismatch"),
        ("backward_station", "route_topology_discontinuous"),
        ("branch_hop", "route_topology_discontinuous"),
    ],
)
def test_route_lift_fails_closed(fixture: str, reason: str) -> None:
    decision = _lift_fixture(fixture)
    assert decision.eligible is False
    assert decision.reason == reason
    assert decision.points
```

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py -k "route_lift" -q
```

Expected: collection fails because `RouteLiftingContext`, `LiftingTolerances`, and `lift_candidate_to_route_surface` do not exist.

- [ ] **Step 4: Add the minimum immutable types and canonical hash helper**

Add these public types; keep matching helpers private:

```python
from dataclasses import dataclass, replace
from typing import Optional


RouteIdentity = Tuple[str, int, int]


@dataclass(frozen=True)
class LaneSurfaceSample:
    road_id: str
    section_id: int
    lane_id: int
    s: float
    x: float
    y: float
    z: float
    lane_width: float
    is_junction: bool


@dataclass(frozen=True)
class LiftingTolerances:
    geometry_epsilon_m: float
    station_epsilon_m: float
    z_epsilon_m: float
    continuity_epsilon_m: float


@dataclass(frozen=True)
class RouteLiftingContext:
    samples: Tuple[LaneSurfaceSample, ...]
    edges: Tuple[Tuple[RouteIdentity, RouteIdentity], ...]
    route_sample_step_m: float
    tolerances: LiftingTolerances
    map_sha256: str
    source_sha256: str
    route_graph_sha256: str


@dataclass(frozen=True)
class LiftedPointReceipt:
    candidate_index: int
    point_index: int
    ego_x: float
    ego_y: float
    world_x: float
    world_y: float
    road_id: Optional[str]
    section_id: Optional[int]
    lane_id: Optional[int]
    s: Optional[float]
    z: Optional[float]
    lateral_residual_m: Optional[float]
    unique_identity: bool
    unique_station: bool
    topology_continuous: bool
    reason: str


@dataclass(frozen=True)
class CandidateLiftDecision:
    eligible: bool
    points: Tuple[LiftedPointReceipt, ...]
    reason: str
    trajectory_lifting_sha256: str


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

Validate every finite/positive field, 64-character lowercase SHA, directed edge identity, and orientation-preserving planar transform at construction/use boundaries.

- [ ] **Step 5: Implement strict route-only chord matching**

Implement `lift_candidate_to_route_surface(...) -> CandidateLiftDecision` with this order:

```python
def lift_candidate_to_route_surface(
    *,
    candidate_index: int,
    candidate: Sequence[Sequence[float]],
    agents_from_world_tf: Sequence[Sequence[float]],
    context: RouteLiftingContext,
    map_api: Any,
) -> CandidateLiftDecision:
    if len(candidate) != 80:
        raise ValueError("candidate must contain exactly 80 points")
    world_xy = _inverse_transform_xy(candidate, agents_from_world_tf)
    points = []
    previous = None
    first_failure = None
    for point_index, ((ego_x, ego_y, *_), (world_x, world_y)) in enumerate(
        zip(candidate, world_xy)
    ):
        match = _unique_route_surface_match(world_x, world_y, context)
        if match.reason:
            receipt = _failed_point_receipt(
                candidate_index, point_index, ego_x, ego_y, world_x, world_y,
                match.reason,
            )
        else:
            waypoint = map_api.get_waypoint_xodr(
                int(match.road_id), int(match.lane_id), float(match.s)
            )
            receipt = _validated_xodr_receipt(
                candidate_index, point_index, ego_x, ego_y, world_x, world_y,
                match, waypoint, context.tolerances,
            )
            if previous is not None and not _continuous(previous, receipt, context):
                receipt = replace(
                    receipt,
                    topology_continuous=False,
                    reason="route_topology_discontinuous",
                )
        points.append(receipt)
        if receipt.reason != "lifted" and first_failure is None:
            first_failure = receipt.reason
        previous = receipt if receipt.reason == "lifted" else None
    payload = [_point_payload(point) for point in points]
    return CandidateLiftDecision(
        first_failure is None,
        tuple(points),
        "source_complete" if first_failure is None else first_failure,
        canonical_json_sha256(payload),
    )
```

Possible identities are restricted to `context.samples`; group matches by identity before choosing any station. Every decision retains exactly 80 point receipts, including explicit null segment/z fields and reasons for failures. Do not call `project_world_point_to_segment` or any global map lookup in this path.

- [ ] **Step 6: Add deterministic map-only tolerance freeze**

Add a pure helper that accepts source-only measured maxima and a coordinate scale:

```python
def freeze_lifting_tolerances(
    *,
    max_chord_error_m: float,
    max_station_roundtrip_error_m: float,
    max_z_roundtrip_error_m: float,
    coordinate_scale_m: float,
) -> LiftingTolerances:
    allowance = max(1e-9, 64.0 * math.ulp(float(coordinate_scale_m)))
    return LiftingTolerances(
        geometry_epsilon_m=max_chord_error_m + allowance,
        station_epsilon_m=max_station_roundtrip_error_m + allowance,
        z_epsilon_m=max_z_roundtrip_error_m + allowance,
        continuity_epsilon_m=max_station_roundtrip_error_m + allowance,
    )
```

Reject negative/non-finite inputs. Tests must show deterministic output and that changing a source maximum changes the contract hash.

- [ ] **Step 7: Run GREEN and regression tests**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py camp_core\tests\test_diffusion_planner_v19_carla_exact_speed_sources.py -q
py -3.12 -m py_compile camp_core\camp_core\integrations\carla_exact_speed_source.py
git diff --check
```

Expected: all focused tests pass; the older strict world-point helper and A/B/C resolver tests remain unchanged.

- [ ] **Step 8: Commit and push Task 1**

```powershell
git add camp_core/camp_core/integrations/carla_exact_speed_source.py camp_core/tests/test_carla_exact_speed_source.py
git commit -m "feat(v19): add route-constrained CARLA lifting"
git push origin main
```

AutoDL must ff-only sync and reproduce the same focused tests with Python 3.9 before Task 2.

---

### Task 2: Immutable K=8 and operational Top-1 receipts

**Files:**
- Modify: `camp_core/camp_core/integrations/carla_exact_speed_source.py`
- Test: `camp_core/tests/test_carla_exact_speed_source.py`

**Interfaces:**
- Consumes: immutable K=8 candidates, independently generated DP operational Top-1, their existing array SHAs, one transform/context/map API, and source provenance.
- Produces: one canonical tick receipt with eight candidate masks/reasons and an independent operational/candidate-0 equivalence certificate.

- [ ] **Step 1: Add RED tests for immutability and independent equivalence**

```python
def test_k8_receipt_preserves_tensor_and_matches_operational_top1() -> None:
    candidates = _k8_candidates()
    before = candidates.copy()
    default = candidates[0].copy()
    receipt = lift_k8_route_receipt(
        candidates=candidates,
        operational_top1=default,
        agents_from_world_tf=np.eye(3),
        context=_route_context(samples=_straight_samples()),
        map_api=_FakeXodrMap(z=3.5),
        candidate_tensor_sha256=array_sha256(candidates),
        operational_top1_sha256=array_sha256(default),
        provenance=_provenance(),
    )
    np.testing.assert_array_equal(candidates, before)
    assert receipt["candidate_source_eligible_mask"] == [True] * 8
    assert receipt["dp_operational_top1_source_complete"] is True
    assert receipt["candidate0_operational_top1_equivalent"] is True
    assert receipt["candidate_receipts"][0]["trajectory_lifting_sha256"] == receipt["operational_top1_receipt"]["trajectory_lifting_sha256"]
```

Add separate failures for any XY/segment/s/z/SHA drift, candidate 0 incomplete, and all-K ineligible. Failed receipts retain eight masks/reasons and no selected index.

- [ ] **Step 2: Run RED**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py -k "k8_receipt or operational_top1" -q
```

Expected: import failure for `lift_k8_route_receipt`.

- [ ] **Step 3: Implement the canonical tick receipt**

Add:

```python
def lift_k8_route_receipt(
    *,
    candidates: Any,
    operational_top1: Any,
    agents_from_world_tf: Any,
    context: RouteLiftingContext,
    map_api: Any,
    candidate_tensor_sha256: str,
    operational_top1_sha256: str,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_k8_shape_without_mutation(candidates)
    _reject_forbidden_receipt_fields(provenance)
    decisions = tuple(
        lift_candidate_to_route_surface(
            candidate_index=index,
            candidate=candidates[index],
            agents_from_world_tf=agents_from_world_tf,
            context=context,
            map_api=map_api,
        )
        for index in range(8)
    )
    default = lift_candidate_to_route_surface(
        candidate_index=0,
        candidate=operational_top1,
        agents_from_world_tf=agents_from_world_tf,
        context=context,
        map_api=map_api,
    )
    equivalent = _equivalent_lifting(decisions[0], default)
    payload = _tick_receipt_payload(
        decisions, default, equivalent, candidate_tensor_sha256,
        operational_top1_sha256, context, provenance,
    )
    payload["lifting_receipt_sha256"] = canonical_json_sha256(payload)
    return payload
```

The canonical per-trajectory payload omits the origin label so candidate 0 and operational Top-1 hashes are comparable. The outer tick payload records both origins and all K receipts.

- [ ] **Step 4: Run GREEN and immutability regressions**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py camp_core\tests\test_diffusion_planner_v19_dp_worker.py -q
git diff --check
```

Expected: all tests pass; fixed-DP worker tensor tests remain byte-identical.

- [ ] **Step 5: Commit and push Task 2**

```powershell
git add camp_core/camp_core/integrations/carla_exact_speed_source.py camp_core/tests/test_carla_exact_speed_source.py
git commit -m "feat(v19): seal K8 CARLA lifting receipts"
git push origin main
```

AutoDL must ff-only sync and independently review candidate SHA preservation and receipt equivalence before Task 3.

---

### Task 3: Active DP operational Top-1 provenance naming

**Files:**
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py`
- Modify: `camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py`
- Modify: `camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py`
- Modify: `scripts/integrations/audit_diffusion_planner_dp_camp_v19_source_support.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_dp_worker.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_source_support.py`

**Interfaces:**
- Produces: active runtime/report metadata `baseline_name="DP operational Top-1"`, `baseline_provenance="unmodified single DP output; independently equivalent to K=8 candidate 0"`, and `native_ranked_top1=false`.

- [ ] **Step 1: Change tests first**

Update only active v19 runtime assertions:

```python
assert metadata["baseline_name"] == "DP operational Top-1"
assert metadata["baseline_provenance"] == (
    "unmodified single DP output; independently equivalent to K=8 candidate 0"
)
assert metadata["native_ranked_top1"] is False
```

Do not rewrite historical v18 results, old evidence-gap artifacts, or past markdown.

- [ ] **Step 2: Run RED**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v19_dp_worker.py camp_core\tests\test_diffusion_planner_v19_nuplan_bridge.py camp_core\tests\test_diffusion_planner_v19_nuplan_closed_loop_adapter.py camp_core\tests\test_diffusion_planner_v19_closed_loop_smoke_harness.py camp_core\tests\test_diffusion_planner_v19_source_support.py -q
```

Expected: failures show the old baseline string and missing provenance field.

- [ ] **Step 3: Add one shared active constant and propagate it**

Define in the bridge:

```python
DP_OPERATIONAL_TOP1_NAME = "DP operational Top-1"
DP_OPERATIONAL_TOP1_PROVENANCE = (
    "unmodified single DP output; independently equivalent to K=8 candidate 0"
)
```

Import these constants in the active worker, adapter, smoke validator, and source-support freeze builder. Validate both fields and `native_ranked_top1 is False`; do not infer ranking from index 0.

- [ ] **Step 4: Run GREEN**

Run the same five test files plus:

```powershell
py -3.12 -m py_compile scripts\integrations\run_diffusion_planner_dp_camp_v19_worker.py camp_core\camp_core\integrations\diffusion_planner_v19_nuplan_bridge.py camp_core\camp_core\integrations\nuplan_closed_loop_adapter.py scripts\integrations\run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py scripts\integrations\audit_diffusion_planner_dp_camp_v19_source_support.py
git diff --check
```

Expected: all active v19 tests pass and every runtime response still carries `native_ranked_top1=false`.

- [ ] **Step 5: Commit and push Task 3**

```powershell
git add scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py scripts/integrations/audit_diffusion_planner_dp_camp_v19_source_support.py camp_core/tests/test_diffusion_planner_v19_dp_worker.py camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py camp_core/tests/test_diffusion_planner_v19_source_support.py
git commit -m "refactor(v19): name DP operational Top-1"
git push origin main
```

AutoDL must reproduce all focused tests before Task 4.

---

### Task 4: Existing exact-speed census consumes lifting receipts

**Files:**
- Modify: `scripts/integrations/audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py`

**Interfaces:**
- Consumes: one canonical lifting receipt JSON plus XODR and optional A-source actor/landmark observations.
- Produces: A/B/C candidate source masks, per-point/per-candidate exclusions, operational Top-1 completeness/equivalence, coverage breakdown, and zero-access counters.

- [ ] **Step 1: Add RED receipt census tests**

Add a fixture with eight receipts: candidate 0 lifting-complete, one ambiguous candidate, one discontinuous candidate, and five complete candidates. Assert lifting is intersected before the speed rung:

```python
def test_lifted_report_intersects_lifting_and_speed_masks(tmp_path: Path) -> None:
    xodr, lifting, actors = _write_lifting_inputs(tmp_path)
    report = build_lifted_report(xodr, lifting, "A", actors)
    row = report["records"][0]
    assert row["candidate_lifting_eligible_mask"][0] is True
    assert row["candidate_source_eligible_mask"][1] is False
    assert row["dp_operational_top1_source_complete"] is True
    assert row["candidate0_operational_top1_equivalent"] is True
    assert report["outcome_reads"] == 0
    assert report["metric_calls"] == 0
```

Add failures for tampered `lifting_receipt_sha256`, candidate SHA mismatch, missing point receipt, operational Top-1 mismatch, candidate 0 incomplete, all-K ineligible, and forbidden outcome fields.

- [ ] **Step 2: Run RED**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v19_carla_exact_speed_sources.py -q
```

Expected: import failure for `build_lifted_report`.

- [ ] **Step 3: Add strict receipt validation and reuse the existing ladder**

Implement:

```python
def build_lifted_report(
    xodr_path: Path,
    lifting_receipt_path: Path,
    rung: str,
    actor_observations_path: Optional[Path],
) -> Dict[str, Any]:
    payload = json.loads(lifting_receipt_path.read_text(encoding="utf-8"))
    _reject_outcome_fields(payload)
    _validate_lifting_receipt(payload)
    index = parse_opendrive_speed_index(xodr_path.read_text(encoding="utf-8"))
    actors = _actor_values(actor_observations_path)
    records = [_lifted_record(row, index, actors, rung) for row in payload["records"]]
    return _source_coverage_report(
        records=records,
        rung=rung,
        xodr_sha256=_sha256(xodr_path),
        lifting_receipt_sha256=_sha256(lifting_receipt_path),
        actor_observations_sha256=(
            _sha256(actor_observations_path)
            if actor_observations_path is not None else None
        ),
    )
```

Keep `build_report` for historical segment-only artifacts, but make the CLI require exactly one of `--candidates` or `--lifting-receipts`. New v19 execution must use `--lifting-receipts`.

- [ ] **Step 4: Make record eligibility fail closed**

For each candidate, reconstruct `SegmentRef`s only from its validated 80 point receipts, run `candidate_source_mask`, and intersect the speed result with lifting eligibility. Require operational Top-1 completeness and candidate-0 equivalence before `record_source_eligible=True`. Retain all K masks/reasons even when excluded.

- [ ] **Step 5: Run GREEN and source-support regressions**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v19_carla_exact_speed_sources.py camp_core\tests\test_diffusion_planner_v19_source_support.py camp_core\tests\test_diffusion_planner_v18_orchestrator.py -q
py -3.12 -m py_compile scripts\integrations\audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py
git diff --check
```

Expected: all tests pass; historical segment-only reports remain deterministic.

- [ ] **Step 6: Commit and push Task 4**

```powershell
git add scripts/integrations/audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py
git commit -m "feat(v19): census route-lifting receipts"
git push origin main
```

AutoDL must reproduce the focused suites and independently review the implementation artifact.

---

### Task 5: Pre-outcome qualification and freeze gates

**Files:**
- Evidence: `/root/autodl-tmp/camp_dp_v19_carla_*`
- Modify: `docs/diffusion_planner_v19_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`
- Modify: `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`

**Interfaces:**
- Consumes: the four reviewed implementation checkpoints and official CARLA/OpenDRIVE source geometry.
- Produces: frozen tolerance artifact, one real source-only K=8 lifting probe, full source-only A/B/C census, and an independently reviewed legal paired freeze or exact zero-support stop.

- [ ] **Step 1: Run implementation static review**

Review exact call graphs and assert: no global map lookup in lifting, no candidate writes, no CARLA import in the pure module, no outcome fields, operational/candidate-0 independent lift, and active naming with `native_ranked_top1=false`. Seal `HEADS`, `COMMAND`, stdout/stderr, JSON, `SHA256SUMS`, and root SHA.

- [ ] **Step 2: Freeze map-only numeric tolerances**

Using official CARLA 0.9.16 maps and the pre-registered route sampling step, census maximum chord, station, z, and coordinate round-trip errors without DP candidates. Call `freeze_lifting_tolerances`, seal exact formulas/values/source rows/map SHA, and obtain independent review. Any non-finite source or failed identity round-trip fails closed.

- [ ] **Step 3: Run one real source-only fixed-DP K=8 probe**

Reuse the existing v19 bridge and worker `source_probe`. Generate one immutable K=8 tensor plus an independent operational Top-1, build the decision-time route sidecar, produce lifting receipts, and verify before/after candidate SHA plus operational/candidate-0 receipt equivalence. No simulator arm advances and all access counters remain zero.

- [ ] **Step 4: Run the full source-only census**

Apply lifting, then A/B/C in order. Report per-map/tag/log/scene/route coverage, every exclusion class, candidate masks, operational Top-1 completeness, all-K counts, disk/time, and zero-access counters. Stop at the first independently reviewed rung with a legal two-scenario pair; do not run later rungs.

- [ ] **Step 5: Freeze or stop**

If legal paired support is nonzero, freeze the lifting contract SHA, tolerances, route graphs, scenario/run keys, seed, candidate hashes, operational Top-1 receipts, speed rung, metrics, thresholds, bootstrap, latency definitions, and failure rules before any outcome. If support is zero or any approved invariant fails, retain evidence and set an exact user-decision/terminal pointer without simulator execution.

- [ ] **Step 6: Verify and checkpoint every gate**

Run Python 3.9/3.12 `py_compile`, focused pytest, v18/v19 pointer tests, `git diff --check`, AutoDL reproduction, artifact SHA review, small commit/push, AutoDL ff-only, and reread live v19 EOF after each gate.

## Plan Self-Review Result

- Every approved spec boundary maps to a task: route-only geometry and z in Task 1; immutable K8 and independent operational Top-1 receipts in Task 2; active naming in Task 3; fail-closed A/B/C census in Task 4; tolerance/source/freeze execution in Task 5.
- No new runner, controller, dependency, DP change, 14D change, or outcome path is introduced.
- Public names and types are consistent across tasks.
- There are no placeholders; production tolerances are deliberately frozen by the map-only gate rather than guessed in code.

Execution choice is already fixed by the user: **Inline Execution on current main** with small verified commits, push, and AutoDL ff-only checkpoints.
