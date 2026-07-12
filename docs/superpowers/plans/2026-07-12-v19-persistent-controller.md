# V19 Persistent Safety-Evidence Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace repeated route-speed blockers with one exhaustive, independently reviewed source-support census and a frozen three-rung protocol ladder, then resume the existing v19 closed-loop safety workflow without changing DP, atoms, weights, metrics, or claims.

**Architecture:** Keep `docs/diffusion_planner_v19_iteration_audit.md` as the sole controller state. Extend the existing causal adapter, bridge, worker, and smoke harness with one explicit route-speed policy, and add one focused census/review script that selects the first supported rung before any simulator arm advances. Use the existing v19 task plus one hourly heartbeat; do not add a general controller framework or a second runner.

**Tech Stack:** Python 3.9/3.12, NumPy, pytest, official nuPlan v1.2 runtime at `ce3c323af01c0d7ec5672f7832ef53f9c679aab0`, fixed TiER IV Diffusion Planner at `7a1d33da277a1992ec474b5383a0c963c72e04e4`, existing CAMP artifact/SHA helpers, Codex heartbeat automation.

## Global Constraints

- Fixed DP commit remains exactly `7a1d33da277a1992ec474b5383a0c963c72e04e4`; do not modify DP code, configuration, weights, checkpoint, or environment.
- CAMP may only select or rerank unchanged fixed-DP candidate tensors. It may not generate, repair, rewrite, blend, guide, postprocess, or postselect trajectories outside the existing fixed-DP K=8 source probe.
- Keep `score_k(w)=a_k^T w`, the approved 14D atom schema, nonnegative simplex weights, and the convex simplex/CVaR/L2 master unchanged.
- Do not use closed-loop outcomes as training or online inputs. Do not reopen the v18 holdout. Do not use Full36 or formal seeds `11/12/13`.
- Seed `3411`, two smoke scenarios, fixed selector artifacts, SafetyCost v1 formula, official/secondary metrics, thresholds, and baseline provenance remain unchanged.
- No invented/default/ego/statutory/nearby-lane/large-value speed fallback is allowed. Missing official speed remains explicit source unavailability.
- Source-only scenario construction and fixed-DP candidate probes are allowed before freeze; simulator advancement, safety/trajectory metric computation, and outcome-driven protocol selection are forbidden before freeze.
- After either closed-loop arm advances or any evaluation metric is computed, scenario identities and protocol rung are immutable.
- Each mutating gate requires aligned tracked-clean local/GitHub/AutoDL CAMP heads, tracked-clean fixed DP and nuPlan source heads, artifact SHA verification, and more than 10 GiB free space.
- Preserve all existing failed artifacts. Never repeat an audited gate or start a second copy of a running job.

## File Map

- Create `scripts/integrations/audit_diffusion_planner_dp_camp_v19_source_support.py`: exhaustive source census, deterministic protocol selection, and independent review CLI.
- Create `camp_core/tests/test_diffusion_planner_v19_source_support.py`: pure selection, census serialization, and review contract tests.
- Modify `camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py`: explicit full-window/candidate-local speed projection and source mask.
- Modify `camp_core/camp_core/integrations/nuplan_causal_adapter.py`: preserve route geometry while marking missing official speed unavailable under the candidate-local policy.
- Modify `camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py`: carry and validate the frozen speed policy plus source-probe evidence.
- Modify `camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py`: pass the frozen policy into each live causal request.
- Modify `scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py`: add source-only K=8 probe and runtime source-completeness checks.
- Modify `scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py`: validate rung-specific bucket semantics and freeze provenance.
- Modify focused v18/v19 tests listed in the tasks below; do not add broad duplicate audit suites.
- Modify `docs/diffusion_planner_current_status.md` and append `docs/diffusion_planner_v19_iteration_audit.md` only after AutoDL evidence exists.

---

### Task 1: Candidate-local exact-speed source contract

**Files:**
- Modify: `camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py:258-369`
- Modify: `camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py:533-692`
- Test: `camp_core/tests/test_diffusion_planner_v18_orchestrator.py`

**Interfaces:**
- Produces constants `FULL_WINDOW_EXACT_SPEED` and `CANDIDATE_LOCAL_EXACT_SPEED`.
- Extends `project_candidates_to_route(candidates, route_lanes, route_speed_limits, route_has_speed_limits, *, speed_source_policy=FULL_WINDOW_EXACT_SPEED) -> dict[str, np.ndarray]` with `route_speed_source_eligible_mask`.
- Adds keyword `speed_source_policy: str = FULL_WINDOW_EXACT_SPEED` to `materialize_canonical_14d` without changing its default behavior or 14D output schema.

- [ ] **Step 1: Add failing projection tests**

Add tests that build two connected route slots, mark the second slot's official speed unavailable, and place different candidates on each slot:

```python
def test_candidate_local_speed_rejects_only_candidates_using_unknown_segments() -> None:
    candidates, route, speed, has_speed = _route_projection_fixture()
    has_speed[1, 0] = False
    speed[1, 0] = 0.0

    with pytest.raises(ValueError, match="route slot 1"):
        causal_atoms.project_candidates_to_route(candidates, route, speed, has_speed)

    projection = causal_atoms.project_candidates_to_route(
        candidates,
        route,
        speed,
        has_speed,
        speed_source_policy=causal_atoms.CANDIDATE_LOCAL_EXACT_SPEED,
    )

    assert projection["route_speed_source_eligible_mask"].shape == (8,)
    assert projection["route_speed_source_eligible_mask"].dtype == np.bool_
    assert projection["route_speed_source_eligible_mask"].any()
    assert not projection["route_speed_source_eligible_mask"].all()
    unavailable = ~projection["route_speed_source_eligible_mask"]
    assert np.isnan(projection["speed_limit"][unavailable]).any()


def test_candidate_local_speed_never_uses_zero_as_a_speed_source() -> None:
    candidates, route, speed, has_speed = _route_projection_fixture()
    has_speed[:] = False
    speed[:] = 0.0

    projection = causal_atoms.project_candidates_to_route(
        candidates,
        route,
        speed,
        has_speed,
        speed_source_policy=causal_atoms.CANDIDATE_LOCAL_EXACT_SPEED,
    )

    assert not projection["route_speed_source_eligible_mask"].any()
```

- [ ] **Step 2: Run the projection tests and confirm RED**

Run:

```powershell
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -k candidate_local_speed -q
```

Expected: failure because the policy constants/keyword and source mask do not exist.

- [ ] **Step 3: Implement the minimal explicit policy**

Keep the current full-window precheck unchanged. Under candidate-local policy, retain route geometry, mark every segment whose endpoint speed source is missing as unavailable, and return a per-candidate mask:

```python
FULL_WINDOW_EXACT_SPEED = "full_window_exact_speed"
CANDIDATE_LOCAL_EXACT_SPEED = "candidate_local_exact_speed"
_SPEED_SOURCE_POLICIES = frozenset(
    {FULL_WINDOW_EXACT_SPEED, CANDIDATE_LOCAL_EXACT_SPEED}
)


def project_candidates_to_route(
    candidates: np.ndarray,
    route_lanes: np.ndarray,
    route_speed_limits: np.ndarray,
    route_has_speed_limits: np.ndarray,
    *,
    speed_source_policy: str = FULL_WINDOW_EXACT_SPEED,
) -> dict[str, np.ndarray]:
    if speed_source_policy not in _SPEED_SOURCE_POLICIES:
        raise ValueError("unsupported route speed-source policy")
    # Preserve the existing geometry projection. Full-window mode raises on
    # any valid slot without speed. Candidate-local mode carries NaN only as
    # an unavailable-source sentinel and never converts it into a speed.
```

For candidate-local mode, compute `route_speed_source_eligible_mask` as `True` only when all 80 projected trajectory points have finite positive official speed. Do not interpolate across an unavailable endpoint. Preserve K=8 validation in `materialize_canonical_14d`; allowing a one-candidate array is limited to the pure projection helper used by the baseline source check.

- [ ] **Step 4: Make canonical materialization fail closed per candidate**

Pass the policy to projection, intersect the physical mask with the source mask, append `route_speed_source_unavailable` to rejected candidates, and compute the three speed atoms only for source-complete rows:

```python
source_complete = np.asarray(
    projection["route_speed_source_eligible_mask"], dtype=bool
)
physical = np.asarray(feasibility["physical_feasible_mask"], dtype=bool)
physical &= source_complete

speed_atoms = np.zeros((8, 3), dtype=np.float64)
for candidate_index in np.flatnonzero(source_complete):
    candidate_limits = np.asarray(
        projection["speed_limit"][candidate_index, 1:], dtype=np.float64
    )
    speed_atoms[candidate_index] = [
        float(dt)
        * np.sum(
            np.maximum(
                speeds[candidate_index] - (candidate_limits - margin), 0.0
            )
            ** 2
        )
        for margin in (0.0, 0.5, 1.0)
    ]
```

Zero speed-atom rows are sentinels only for candidates already excluded by `physical_feasible_mask`; add a result field `route_speed_source_eligible_mask` so the evidence cannot be interpreted as measured zero cost. If all K are source-ineligible, return `canonical_eligible=False` and `exclusion_reason="all_candidates_route_speed_source_ineligible"`.

- [ ] **Step 5: Run focused and existing atom tests**

Run:

```powershell
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py camp_core/tests/test_diffusion_planner_v17_causal_atom_availability.py -q
```

Expected: all tests pass; existing full-window results remain byte-for-byte compatible at the public return fields used by current callers.

- [ ] **Step 6: Commit and push the source contract checkpoint**

```powershell
git add camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py
git commit -m "Add v19 candidate-local speed source contract"
git push origin main
```

Before push, run `git diff --check` and confirm no unrelated files are staged.

---

### Task 2: Propagate the frozen policy through the live adapter and worker

**Files:**
- Modify: `camp_core/camp_core/integrations/nuplan_causal_adapter.py:27-31`
- Modify: `camp_core/camp_core/integrations/nuplan_causal_adapter.py:259-289`
- Modify: `camp_core/camp_core/integrations/nuplan_causal_adapter.py:468-543`
- Modify: `camp_core/camp_core/integrations/nuplan_causal_adapter.py:1211-1265`
- Modify: `camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py:71-119`
- Modify: `camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py:182-318`
- Modify: `camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py:66-115`
- Modify: `camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py:129-166`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py:43-180`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py:333-465`
- Test: `camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_dp_worker.py`

**Interfaces:**
- `materialize_nuplan_planner_input(current_input, initialization, *, speed_source_policy=FULL_WINDOW_EXACT_SPEED)` preserves default fail-closed behavior.
- `NuPlanCAMPPlanner` gains keyword `speed_source_policy: str = FULL_WINDOW_EXACT_SPEED` and freezes it for every tick.
- Bridge request metadata includes `speed_source_policy`.
- Worker operation `source_probe` returns unchanged K=8 candidates and `route_speed_source_eligible_mask` without atom selection or simulator advancement.

- [ ] **Step 1: Add adapter RED tests for missing official speed**

Add this test to `test_diffusion_planner_v19_nuplan_closed_loop_adapter.py`; it confirms default mode still raises and candidate-local mode preserves geometry with explicit false availability:

```python
def test_live_candidate_local_route_preserves_missing_speed_as_unavailable() -> None:
    current_input, initialization = _fixture()
    second_roadblock = initialization.map_api.get_map_object("rb-1", None)
    second_roadblock.interior_edges[0].speed_limit_mps = None

    with pytest.raises(NuPlanCausalSourceError, match="speed_limit_mps"):
        nuplan_causal_adapter.materialize_nuplan_planner_input(
            current_input, initialization
        )

    materialized = nuplan_causal_adapter.materialize_nuplan_planner_input(
        current_input,
        initialization,
        speed_source_policy=(
            nuplan_causal_adapter.CANDIDATE_LOCAL_EXACT_SPEED
        ),
    )

    assert materialized.dp_input["route_lanes_has_speed_limit"][1, 0] == 0
    assert materialized.dp_input["route_lanes_speed_limit"][1, 0] == 0.0
    assert np.any(materialized.dp_input["route_lanes"][1, :, 13] > 0.5)
```

The test must explicitly assert that zero plus `has_speed_limit=False` is an unavailable-source encoding, not a fallback speed.

- [ ] **Step 2: Add bridge/worker RED tests**

Add this complete response test to `test_diffusion_planner_v19_nuplan_bridge.py`:

```python
def test_source_probe_response_requires_unchanged_k8_and_source_mask(tmp_path: Path) -> None:
    module = _bridge()
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    source_mask = np.array([True, False, True, False, False, False, False, False])
    digest = module.array_sha256(candidates)
    metadata = {
        "schema_version": module.BRIDGE_SCHEMA_VERSION,
        "arm": "camp",
        "run_key": "run:camp",
        "iteration_index": 0,
        "operation": "source_probe",
        "speed_source_policy": "candidate_local_exact_speed",
        "status": "ok",
        "native_ranked_top1": False,
        "candidate_sha256_before": digest,
        "candidate_sha256_after": digest,
        "dp_default_source_complete": True,
        "eligible_candidate_count": 2,
    }

    module.write_response(
        tmp_path,
        {
            "candidates": candidates,
            "route_speed_source_eligible_mask": source_mask,
        },
        metadata,
    )
    loaded = module.read_response(
        tmp_path,
        expected_run_key="run:camp",
        expected_iteration_index=0,
    )

    assert loaded.arrays["candidates"].shape == (8, 80, 4)
    np.testing.assert_array_equal(
        loaded.arrays["route_speed_source_eligible_mask"], source_mask
    )
    assert loaded.metadata["candidate_sha256_before"] == digest
    assert loaded.metadata["candidate_sha256_after"] == digest
```

In `test_diffusion_planner_v19_dp_worker.py`, update `_request` to create one valid route slot and accept the two source-policy inputs:

```python
def _request(
    tmp_path,
    *,
    arm: str,
    speed_source_policy: str = "full_window_exact_speed",
    route_speed_available: bool = True,
):
    arrays = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    arrays["version"] = np.array(1, dtype=np.int64)
    arrays["route_lanes"][0, :, 0] = np.linspace(0.0, 19.0, 20)
    arrays["route_lanes"][0, :, 4:6] = [0.0, 2.0]
    arrays["route_lanes"][0, :, 6:8] = [0.0, -2.0]
    arrays["route_lanes"][0, :, 13] = 1.0
    arrays["route_lanes_has_speed_limit"][0, 0] = route_speed_available
    arrays["route_lanes_speed_limit"][0, 0] = (
        10.0 if route_speed_available else 0.0
    )
    metadata = build_request_metadata(
        arm=arm,
        log_name="log-a",
        scenario_token="scenario-a",
        iteration_index=0,
        simulation_time_us=0,
        scenario_seed=3411,
        dp_seed_root=3412,
        camp_head="a" * 40,
        dp_head="b" * 40,
        nuplan_head="c" * 40,
        causal_input=arrays,
        selector_hashes=("d" * 64, "e" * 64, "f" * 64)
        if arm == "camp"
        else None,
        speed_source_policy=speed_source_policy,
    )
    write_request(tmp_path, arrays, metadata)
    return metadata
```

Then add the runtime fail-closed test:

```python
def test_process_default_candidate_local_tick_fails_without_speed_source(
    tmp_path,
) -> None:
    module = _worker()
    metadata = _request(
        tmp_path,
        arm="dp_default",
        speed_source_policy="candidate_local_exact_speed",
        route_speed_available=False,
    )

    module.process_request(
        tmp_path,
        operation="plan_tick",
        infer_one=_fake_infer,
        planned_red_cost=lambda _candidates, _causal: np.zeros(1),
    )
    response = read_response(
        tmp_path,
        expected_run_key=str(metadata["run_key"]),
        expected_iteration_index=0,
    )

    assert response.metadata["status"] == "failed"
    assert response.metadata["failure_reason"] == (
        "dp_default_route_speed_source_ineligible"
    )
    assert "selected_trajectory" not in response.arrays
```

Use the existing `_fake_infer` helper and do not introduce a new fixture framework.

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```powershell
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py camp_core/tests/test_diffusion_planner_v19_dp_worker.py -q
```

Expected: failures for the missing keyword, metadata field, and `source_probe` operation.

- [ ] **Step 4: Preserve geometry and explicit speed availability**

Change `EncodedRouteLane.speed_limit_mps` to `float | None`. Add `require_speed_limit: bool = True` to `encode_route_lane`. When it is false and the official value is missing/nonpositive, encode the lane geometry exactly as before, return `None`, and leave the numeric speed field at zero with the availability flag false. Do not catch or replace any other route/geometry/traffic error.

Add `speed_source_policy` to `materialize_nuplan_planner_input`, `_live_planner_context`, and `NuPlanCAMPPlanner`. Validate it against the two constants and retain the default full-window mode.

- [ ] **Step 5: Carry the policy in bridge metadata**

Extend `build_request_metadata` and `_validate_common_metadata`:

```python
speed_source_policy = str(metadata.get("speed_source_policy", ""))
if speed_source_policy not in {
    FULL_WINDOW_EXACT_SPEED,
    CANDIDATE_LOCAL_EXACT_SPEED,
}:
    raise ValueError("request speed-source policy is invalid")
```

Every response must echo the exact request policy. Reject response/request policy mismatch.

- [ ] **Step 6: Implement source-only worker operation**

Add `source_probe` to `parse_args` and `process_request`. It is valid only for the CAMP arm and must branch immediately after fixed-DP K=8 generation, before planned-red, signal, atom, weight, or selector work:

```python
if operation == "source_probe":
    candidates, _ = run_fixed_dp_candidates(
        infer_one,
        np.random.default_rng(int(request.metadata["tick_seed"])),
        noise_scale=1.0,
    )
    projection = project_candidates_to_route(
        candidates,
        request.arrays["route_lanes"],
        request.arrays["route_lanes_speed_limit"],
        request.arrays["route_lanes_has_speed_limit"],
        speed_source_policy=CANDIDATE_LOCAL_EXACT_SPEED,
    )
    source_mask = np.asarray(
        projection["route_speed_source_eligible_mask"], dtype=bool
    )
    write_response(
        directory,
        {
            "candidates": candidates,
            "route_speed_source_eligible_mask": source_mask,
        },
        {
            **response_metadata,
            "status": "ok",
            "candidate_sha256_before": array_sha256(candidates),
            "candidate_sha256_after": array_sha256(candidates),
            "dp_default_source_complete": bool(source_mask[0]),
            "eligible_candidate_count": int(source_mask.sum()),
        },
    )
    return
```

Source-probe responses must contain no selected trajectory, atom matrix, SafetyCost component, label, metric, or outcome.

- [ ] **Step 7: Enforce the same policy during real plan ticks**

For CAMP ticks, pass the request policy to `materialize_canonical_14d`. For DP-default candidate-local ticks, project the single default trajectory and fail closed unless candidate 0 is source-complete. Full-window behavior remains unchanged.

- [ ] **Step 8: Run focused tests and v19 bridge regression**

Run:

```powershell
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py camp_core/tests/test_diffusion_planner_v19_dp_worker.py -q
```

Expected: all pass, including existing default-provenance and plan-tick tests.

- [ ] **Step 9: Commit and push policy propagation**

```powershell
git add camp_core/camp_core/integrations/nuplan_causal_adapter.py camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py camp_core/tests/test_diffusion_planner_v19_dp_worker.py
git commit -m "Propagate v19 route speed source policy"
git push origin main
```

---

### Task 3: Exhaustive source census and deterministic protocol ladder

**Files:**
- Create: `scripts/integrations/audit_diffusion_planner_dp_camp_v19_source_support.py`
- Create: `camp_core/tests/test_diffusion_planner_v19_source_support.py`

**Interfaces:**
- `selection_sha256(bucket: str, row: Mapping[str, Any]) -> str`
- `choose_protocol(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]`
- CLI modes `census` and `review`.
- Census outputs `census_rows.jsonl`, `candidate_tensors.npy`, `support_matrix.json`, `selected_protocol.json`, and conditionally `smoke_config.json`.

- [ ] **Step 1: Write RED tests for ladder ordering and honest bucket semantics**

Freeze the official tag sets found in the original v19 selection artifact:

```python
NORMAL_TAGS = (
    "following_lane_without_lead",
    "medium_magnitude_speed",
)
INTERACTION_TAGS = (
    "waiting_for_pedestrian_to_cross",
    "near_pedestrian_on_crosswalk_with_ego",
    "near_multiple_vehicles",
    "high_magnitude_jerk",
    "near_pedestrian_on_crosswalk",
)
```

Tests must prove:

1. full-window normal+interaction wins even when candidate-local rows exist;
2. rung 2 requires candidate 0 plus at least one eligible K=8 candidate in both buckets;
3. rung 3 selects two interaction rows from distinct official `selection_tag`, logs, and scenes, and never labels either row `normal`;
4. deterministic order is `sha256("3411|bucket|log_token|scene_token|scenario_token")`;
5. no support returns `selected=False`, `exhausted=True`, and no smoke config.

Example:

```python
def test_interaction_only_rung_keeps_honest_bucket_names() -> None:
    rows = [
        _row("interaction", "near_multiple_vehicles", "log-a", "scene-a"),
        _row(
            "interaction",
            "waiting_for_pedestrian_to_cross",
            "log-b",
            "scene-b",
        ),
    ]
    for row in rows:
        row.update(
            candidate_local_any=True,
            dp_default_source_complete=True,
            full_window_source_complete=False,
        )

    selected = source_support.choose_protocol(rows)

    assert selected["rung"] == "interaction_only_candidate_local_exact_speed"
    assert [row["bucket"] for row in selected["selected_scenarios"]] == [
        "interaction",
        "interaction",
    ]
```

- [ ] **Step 2: Run tests and confirm RED**

Run:

```powershell
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v19_source_support.py -q
```

Expected: import failure because the census script does not exist.

- [ ] **Step 3: Implement pure protocol selection first**

Use plain dictionaries and `hashlib`; do not add classes or dependencies. `choose_protocol` must sort within each bucket by the frozen hash, require distinct logs/scenes, and return only these rung identifiers:

```python
PROTOCOL_RUNGS = (
    "full_window_exact_speed",
    "candidate_local_exact_speed",
    "interaction_only_candidate_local_exact_speed",
)
```

The selected result includes `selection_seed=3411`, selected identities, exact source policy, support counts per rung/tag/location, rejection counts, and `selection_uses_outcomes=False`.

- [ ] **Step 4: Add census serialization tests**

Mock scenario construction and source-probe invocation at the script boundary. Assert the census:

- reads every non-v18 candidate identity once;
- persists every rejection reason;
- writes candidate tensors in deterministic row order;
- records `expert_future_value_reads=0`, `simulator_advances=0`, `metric_computations=0`, and `outcome_reads=0`;
- refuses an existing output root;
- writes no `smoke_config.json` when all rungs are exhausted.

- [ ] **Step 5: Implement exhaustive census mode**

Use the frozen v18 exclusion manifest:

```text
/root/autodl-tmp/camp_dp_v18_nuplan_causal_10k_source_selection_c7f3e7f3_20260711T113655CST/causal_10k_manifest.jsonl
SHA256 703a47bec14d9ee4605184618e6bb61b6a4ce4ed73bee4173df508d6a6dfa5e5
```

Enumerate all official scenario-tag anchors in the 18 unseen mini logs with at least 3.0 seconds history and 8.0 seconds future timestamp coverage. Each row must retain official tag(s), location, DB/log/scene/scenario identity, timestamp spans, mission-goal availability, route count/uniqueness/connectivity, valid route-slot count, finite-positive speed-slot count, full-window support, candidate-local K=8 mask/count, candidate-0 completeness, v18 log/scene overlap counts, and exact failure class/reason. Aggregate the same fields by tag, location, log, scene, rung, and rejection class in `support_matrix.json`.

Construct official scenario/simulation input without advancing the simulator. Materialize causal input with `candidate_local_exact_speed`; record full-window support from valid route slots. Invoke exactly one `source_probe` for each source-constructible identity, retain its unchanged K=8 tensor, and record candidate-local mask plus candidate-0 completeness.

The source-probe command must use the already frozen v19 fixed-DP worker/checkpoint/selector paths and hashes from the executable-provenance/closed-loop preflight artifacts; the census script receives the complete command as `--worker-command-json` and never guesses paths.

Write candidate tensors as one contiguous `candidate_tensors.npy`; each JSONL row stores `candidate_tensor_index` and its SHA256. Atomic rename the artifact only after all JSON/JSONL/NPY files and the support matrix are complete.

- [ ] **Step 6: Implement independent review mode**

Review mode must not invoke fixed DP. It must:

1. verify the source artifact `SHA256SUMS` and root digest;
2. re-enumerate SQLite identities/timestamps/tags and v18 exclusions;
3. reconstruct official route geometry and speed availability;
4. recompute candidate-local masks from retained candidate tensors;
5. recompute selection hashes, support matrix, and selected rung;
6. compare `smoke_config.json` byte-for-byte when selection succeeded;
7. emit its own JSON/Markdown review and SHA chain.

- [ ] **Step 7: Run source-support tests**

Run:

```powershell
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v19_source_support.py -q
```

Expected: all pass.

- [ ] **Step 8: Commit and push census implementation**

```powershell
git add scripts/integrations/audit_diffusion_planner_dp_camp_v19_source_support.py camp_core/tests/test_diffusion_planner_v19_source_support.py
git commit -m "Add v19 source support census"
git push origin main
```

---

### Task 4: Freeze rung-aware smoke configuration and runtime contract

**Files:**
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py:59-143`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py:193-229`
- Modify: `camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py`

**Interfaces:**
- Adds required `source_protocol` object to `smoke_config.json`.
- Full-window/rung-2 require one normal and one interaction scenario.
- Interaction-only requires two honest interaction scenarios from distinct tag families/logs/scenes.

- [ ] **Step 1: Add RED config tests**

Extend `_config()` with:

```python
"source_protocol": {
    "rung": "full_window_exact_speed",
    "speed_source_policy": "full_window_exact_speed",
    "selection_seed": 3411,
    "census_root_sha256": "b" * 64,
    "review_root_sha256": "c" * 64,
    "selection_uses_outcomes": False,
    "dp_default_source_complete_required": True,
},
```

Add tests that reject missing roots, outcome-driven selection, candidate-local without candidate-0 requirement, normal relabeling in rung 3, duplicate interaction tag family, and rung/policy mismatch.

- [ ] **Step 2: Run harness tests and confirm RED**

Run:

```powershell
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py -q
```

Expected: current validator ignores the required protocol object and rejects honest interaction-only semantics.

- [ ] **Step 3: Implement exact rung validation**

Validate SHA256 fields as 64 lowercase hexadecimal characters. For rungs 1 and 2 require bucket set `{"normal", "interaction"}`. For rung 3 require both buckets equal `interaction`, distinct `selection_tag`, distinct logs, and distinct scenes. Always require seed 3411 and `selection_uses_outcomes is False`.

Do not rename the schema or change metric/arm/seed validation. `construct_nuplan_scenario` continues using official `map_version`.

- [ ] **Step 4: Run harness and adjacent evidence tests**

Run:

```powershell
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py camp_core/tests/test_diffusion_planner_v19_closed_loop_evidence.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit and push the freeze contract**

```powershell
git add scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py
git commit -m "Freeze v19 source protocol ladder"
git push origin main
```

---

### Task 5: Execute census, independent review, freeze, and resume the live EOF loop

**Files:**
- Modify: `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`
- Modify: `docs/diffusion_planner_current_status.md`
- Modify: `docs/diffusion_planner_v19_iteration_audit.md`

**Interfaces:**
- Consumes the new census/review CLI and existing artifact wrapper.
- Produces the next live EOF based only on independently reviewed support.

- [ ] **Step 1: Reconcile and sync all three CAMP heads**

Run locally:

```powershell
git status --short --branch --untracked-files=no
git fetch --prune origin
git pull --ff-only
git rev-parse HEAD
git rev-parse origin/main
```

On AutoDL, run network turbo before `git fetch --prune origin` and `git pull --ff-only`. Verify CAMP tracked-clean, DP at the fixed commit, nuPlan source at `ce3c323af01c0d7ec5672f7832ef53f9c679aab0`, no related process, and free space above 10 GiB.

- [ ] **Step 2: Run local and AutoDL preflight verification**

Run locally, then in the existing AutoDL v19 nuPlan Python 3.9 environment and fixed-DP Python 3.12 environment:

```powershell
py -3.12 -m py_compile scripts/integrations/audit_diffusion_planner_dp_camp_v19_source_support.py scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v19_source_support.py camp_core/tests/test_diffusion_planner_v19_dp_worker.py camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py camp_core/tests/test_diffusion_planner_v19_orchestrator.py -q
git diff --check
```

- [ ] **Step 3: Start exactly one census job**

Create a new immutable staging root named:

```text
/root/autodl-tmp/camp_dp_v19_source_support_census_<CAMP10>_<timestamp>.tmp
```

Invoke `audit_diffusion_planner_dp_camp_v19_source_support.py --mode census` with the exact mini roots, v18 manifest path/SHA, frozen source smoke config, worker command JSON, fixed heads, and final output root. Record PID and command before start. If a matching PID or staging/final root already exists, monitor or review it instead of restarting.

- [ ] **Step 4: Monitor without duplicating work**

At each continuation, report PID, processed/total identities, source-probe count, rejection counts, stderr tail, candidate tensor bytes, disk free bytes, and staging/final state. Do not mark the goal blocked merely because the census is slow.

- [ ] **Step 5: Apply bounded retry rules only to unchanged gates**

For network fetch/download failures, retain the failed evidence and retry at most twice with AutoDL network turbo enabled. For wrapper/import/path defects, add the smallest regression test, repair only the harness, and rerun the same gate when formula, protocol, candidates, and outputs are unchanged. Never retry an evaluation after freeze by changing scenarios or source policy. Mark the goal blocked only after the same genuine external or user-decision condition reaches the required consecutive-turn threshold.

- [ ] **Step 6: Run exactly one independent review**

After census exit 0 and complete SHA sealing, run `--mode review` into a separate immutable artifact. The review must make zero worker/model/simulator/metric calls. Verify both SHA chains.

- [ ] **Step 7: Advance by the reviewed result**

Use this exact decision table:

| Reviewed support | Next action |
|---|---|
| Rung 1 valid pair | Freeze full-window config, static review, execution preflight |
| Rung 2 valid pair | Freeze candidate-local config, static review, execution preflight |
| Rung 3 valid pair | Freeze honest interaction-only config, static review, execution preflight |
| No rung valid | Write one exhaustion artifact and stop at `user_decision_required_before_new_data_scope_or_atom_source_contract` |

Do not create a fourth rung.

- [ ] **Step 8: Update pointer tests before docs**

Change the checked-in expected tuple in `test_diffusion_planner_v19_orchestrator.py` to the actual next gate. Run it RED, append the v19 audit evidence and update the named Current V19 section, then rerun GREEN.

- [ ] **Step 9: Seal each ordinary gate and continue**

For every completed gate: local checks, AutoDL checks, artifact SHA, audit/current-status update, small commit/push, AutoDL ff-only sync, EOF reread. Continue through static review, freeze review, execution preflight, closed-loop execution, and result review unless a real stop condition from the design is reached.

- [ ] **Step 10: Preserve post-freeze failures honestly**

Once either arm advances, retain any unfavorable result and stop protocol changes. Update claim taxonomy only from preregistered result-review evidence; do not turn a smoke result into a broad safety or native-Top1 claim.

---

### Task 6: Attach one hourly heartbeat to the existing v19 task

**Files:**
- No repository file changes.

**Interfaces:**
- Target Codex task: `019f4aa5-5dfb-7283-a119-e26632b640d4`.
- One hourly heartbeat named `v19 source and closed-loop monitor`.

- [ ] **Step 1: Inspect existing automations and avoid duplicates**

Use the Codex automation tool to verify no active heartbeat already targets the v19 task. Do not reuse the paused historical `nuplan-mini` download automation.

- [ ] **Step 2: Create the heartbeat with this prompt**

```text
Read the active v19 goal, docs/diffusion_planner_current_status.md, and the EOF of docs/diffusion_planner_v19_iteration_audit.md. If the task is already running, do nothing. If exactly one authorized AutoDL job is running, report PID/progress/stderr tail/staging-final state/free bytes and do not restart it. If that job completed and the task is idle, verify its exit and SHA evidence, then send one continuation to this same v19 task from the current EOF. Deduplicate by EOF plus artifact path plus PID. Stay silent at genuine user_decision_required or terminal EOF states. Never run a simulator, change a protocol, delete data, or make a claim from the heartbeat.
```

- [ ] **Step 3: Verify heartbeat state**

View the saved automation and confirm: target task ID matches, status is active, cadence is hourly, and there is only one matching heartbeat. Pause it when the persistent v19 goal reaches complete or terminal state.

---

## Final Verification

Before reporting implementation complete, run:

```powershell
py -3.12 -m py_compile scripts/integrations/audit_diffusion_planner_dp_camp_v19_source_support.py scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py
py -3.12 -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v19_source_support.py camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py camp_core/tests/test_diffusion_planner_v19_dp_worker.py camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py camp_core/tests/test_diffusion_planner_v19_closed_loop_evidence.py camp_core/tests/test_diffusion_planner_v19_orchestrator.py -q
git diff --check
git status --short --branch --untracked-files=no
```

Repeat the focused tests on AutoDL in the existing v19 environments, verify all source/review/freeze/execution artifacts with `sha256sum -c SHA256SUMS` plus root digest, and confirm local/GitHub/AutoDL CAMP heads match. Report the accurately limited claim taxonomy and the latest live EOF.
