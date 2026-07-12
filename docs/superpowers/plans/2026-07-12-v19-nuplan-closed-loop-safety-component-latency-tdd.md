# V19 nuPlan Closed-loop Safety Component and Latency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task on the current `main` branch. The user already selected Inline Execution; do not request another execution choice or create a worktree.

**Goal:** Make the existing two-scenario nuPlan smoke harness able to materialize every frozen SafetyCost v1 component and six auditable latency receipts for both paired arms, without changing fixed DP, candidates, selector weights, or baseline provenance.

**Architecture:** Reuse the existing replay-summary math instead of creating a second metric stack. Add one narrow official-history adapter, extend the existing file bridge with selected planned-red and worker timing evidence, and have the existing planner write one immutable per-tick receipt. Keep official nuPlan metrics secondary and keep real simulator execution outside this TDD plan.

**Tech Stack:** Python 3.9 official nuPlan v1.2 runtime, Python 3.12 fixed-DP runtime, standard library, NumPy, Shapely already present in the official runtime, pytest.

## Global Constraints

- Starting CAMP local/GitHub/AutoDL HEAD: `a80db7209f8525da8c4b61d9e9fd618a1b474b27`.
- Fixed DP HEAD: `7a1d33da277a1992ec474b5383a0c963c72e04e4`; do not modify its repository, environment, config, checkpoint, or weights.
- Official nuPlan source HEAD: `ce3c323af01c0d7ec5672f7832ef53f9c679aab0`.
- Design spec SHA256: `56a24ce729f5c7b4a8f13b9f9dc8cec9563d28251fc4f011425dbfcc6d91e50e`.
- SafetyCost v1 protocol SHA256: `5a3f6cd77bb5ff34e002321b1dbd201d2a4fd56af058fa57f7d6b8d06dffe9d3`; weights, normalization, seeds, hard gates, and claim rule do not change.
- Baseline name remains `DP-default deterministic/MAP baseline`; `native_ranked_top1=false`.
- CAMP selects only from the unchanged fixed-DP K=8 tensor. No generation, repair, blend, guidance, postprocess, postselection, candidate-0 fallback, or all-K progress fallback.
- Online candidate feasibility remains exact only within the frozen 32 dynamic + 5 static observable source. Posterior closed-loop evaluation may use all objects exposed by official `DetectionsTracks` and must be labeled separately.
- No new dependency, old-holdout access, Full36, seeds 11/12/13, simulator execution, metric compute, promotion, deployment, activation, model replacement, or broad claim in this plan.
- Every failure preserves requests, responses, candidates, masks, reasons, receipts, logs, and SHA manifests and fails the matched pair closed.

---

### Task 1: Causal 0.05-second history downsampling

**Files:**
- Modify: `camp_core/camp_core/integrations/nuplan_causal_adapter.py`
- Test: `camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py`

**Interfaces:**
- Consumes: official `PlannerInput.history` with aligned `ego_states`, `observations`, timestamps, and `sample_interval`.
- Produces: `_causal_history_view(history: Any) -> SimpleNamespace` containing exactly 31 aligned samples at `sample_interval=0.1`.

- [ ] **Step 1: Add failing 0.05-second history tests**

Create 61 ego/observation samples spaced 50,000 microseconds apart. Assert that `_causal_history_view` selects indices `0, 2, ..., 60`, ends at the current tick, and returns 31 samples at 0.1 seconds. Add failures for 60 samples, timestamp jitter above 1 millisecond, ego/observation length mismatch, and unsupported intervals.

```python
view = nuplan_causal_adapter._causal_history_view(history)
assert view.sample_interval == 0.1
assert [state.time_us for state in view.ego_states] == [
    states[index].time_us for index in range(0, 61, 2)
]
assert view.observations[-1] is observations[-1]
```

- [ ] **Step 2: Run the target test and retain RED**

Run:

```bash
PYTHONPATH=camp_core python -m pytest -q \
  camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py
```

Expected: failure because `_causal_history_view` does not exist or the current adapter rejects `sample_interval=0.05`.

- [ ] **Step 3: Implement the minimal shared history view**

```python
def _causal_history_view(history: Any) -> SimpleNamespace:
    ego = list(history.ego_states)
    observations = list(history.observations)
    if len(ego) != len(observations):
        raise ValueError("ego and observation history must align")
    source_dt = float(history.sample_interval)
    count, stride = (61, 2) if np.isclose(source_dt, 0.05) else (31, 1)
    if not np.isclose(source_dt * stride, 0.1) or len(ego) < count:
        raise ValueError("history must cover 3.0 seconds at 0.05 or 0.1 seconds")
    ego = ego[-count:]
    observations = observations[-count:]
    times = np.asarray([_state_time_us(state) for state in ego], dtype=np.int64)
    if not np.allclose(np.diff(times) / 1e6, source_dt, rtol=0.0, atol=1e-3):
        raise ValueError("history timestamps must be uniformly sampled")
    return SimpleNamespace(
        ego_states=ego[::stride],
        observations=observations[::stride],
        sample_interval=0.1,
    )
```

Call this once at the start of `materialize_nuplan_planner_input`; leave the existing 0.1-second validation and causal materialization unchanged.

- [ ] **Step 4: Run GREEN and compile**

Run the target test plus:

```bash
python -m py_compile camp_core/camp_core/integrations/nuplan_causal_adapter.py
```

Expected: target tests pass; no future or interpolation path is added.

- [ ] **Step 5: Commit and push this slice**

```bash
git add camp_core/camp_core/integrations/nuplan_causal_adapter.py \
  camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py
git commit -m "fix(v19): causally downsample nuPlan history"
git push origin main
```

### Task 2: Reuse replay summaries for official closed-loop evidence

**Files:**
- Modify: `camp_core/camp_core/integrations/diffusion_planner.py`
- Create: `camp_core/camp_core/integrations/nuplan_closed_loop_evidence.py`
- Create: `camp_core/tests/test_diffusion_planner_v19_closed_loop_evidence.py`

**Interfaces:**
- Consumes: completed official `SimulationHistory`, scenario route/map, validated per-tick planned-red receipts.
- Produces: `materialize_closed_loop_evidence(history: Any, scenario: Any, tick_receipts: Sequence[Mapping[str, Any]]) -> dict[str, Any]` with all eight `_SAFETY_FIELDS`, raw counts/denominators, and source qualification.

- [ ] **Step 1: Add failing pure evidence tests**

Use synthetic official-shaped samples with Shapely ego/object polygons, route polygons, red connector points, timestamps, and planned-red receipts. Assert exact rates for collision threshold `1e-6`, near miss `2.0`, route-corridor coverage, realized-red speed/alignment/distance, planned-red tolerance `1e-12`, observed-dt jerk/lateral acceleration, and monotone route completion. Assert missing geometry, receipt, timestamp, or disconnected route fails.

```python
summary = materialize_closed_loop_evidence(history, scenario, receipts)
assert summary["obb_collision_rate"] == 1 / 4
assert summary["near_miss_rate"] == 2 / 4
assert summary["planned_red_light_violation_rate"] == 1 / 3
assert summary["source_scope"] == "official_full_posterior_observation"
```

- [ ] **Step 2: Run the new test and retain RED**

Expected: import failure for `nuplan_closed_loop_evidence`.

- [ ] **Step 3: Parameterize the existing trajectory summary instead of copying it**

Change only the signature and three derivatives in `_summarize_trajectory_log`:

```python
def _summarize_trajectory_log(
    records: list[dict[str, Any]], *, dt: float = 0.1
) -> dict[str, Any]:
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive")
    accel = np.diff(speeds) / dt
    jerk = np.diff(accel) / dt
    # velocity-vector acceleration, jerk, and yaw rate use the same dt
```

The default stays 0.1 so existing replay callers and tests remain unchanged.

- [ ] **Step 4: Implement one thin official-history adapter**

Normalize official samples into the existing replay helper inputs, then call `_summarize_trajectory_log(..., dt=observed_dt)`, `_project_route_progress`, `_summarize_realized_red_lights(..., dt=observed_dt)`, and `_summarize_clearance_log(..., near_miss_threshold_m=2.0)`. Compute only route-corridor `lane_crossing` and receipt-backed planned-red booleans locally. Require exactly one receipt per planner tick and matching arm/run/trajectory SHA.

```python
summary = {}
summary.update(_summarize_trajectory_log(trajectory_records, dt=dt))
summary.update(_project_route_progress(trajectory_records, route_centerline))
summary.update(_summarize_realized_red_lights(trajectory_records, dt=dt))
summary.update(_summarize_clearance_log({"records": clearance}, near_miss_threshold_m=2.0))
summary.update(_summarize_metrics_log({"steps": metric_steps}))
return _require_complete_safety_fields(summary)
```

- [ ] **Step 5: Run GREEN, existing replay tests, and compile**

Run the new test plus `camp_core/tests/test_diffusion_planner_integration.py` tests for replay summary/red light/route projection. Expected: new and existing summary behavior pass.

- [ ] **Step 6: Commit and push this slice**

```bash
git add camp_core/camp_core/integrations/diffusion_planner.py \
  camp_core/camp_core/integrations/nuplan_closed_loop_evidence.py \
  camp_core/tests/test_diffusion_planner_v19_closed_loop_evidence.py
git commit -m "feat(v19): materialize closed-loop safety evidence"
git push origin main
```

### Task 3: Planned-red and worker latency bridge evidence

**Files:**
- Modify: `camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py`
- Modify: `camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py`
- Modify: `camp_core/tests/test_diffusion_planner_v19_dp_worker.py`

**Interfaces:**
- Produces successful response metadata fields `operation`, `selected_planned_red_light_cost`, `planned_red_source`, and `worker_latency_ms` with exactly `dp_inference` and `atom_selector`.
- Preserves the existing response arrays, candidate SHA checks, all-K failure evidence, and baseline naming.

- [ ] **Step 1: Add failing worker tests for both arms**

For DP-default `plan_tick`, assert `_fixed_dp_red_cost` is called on only the direct default trajectory and no K tensor is generated. For CAMP, assert the recorded scalar equals the selected entry of the same planned-red vector. Assert costs over `1e-12` are retained, candidates remain byte-identical, and both latency values are finite/nonnegative with DP-default `atom_selector == 0.0`.

- [ ] **Step 2: Add failing bridge validation tests**

Require successful `plan_tick` responses to carry the new fields. Reject non-finite/negative latency, missing planned-red, selected-SHA mismatch, or CAMP selected cost unequal to the selected atom input. Keep `default_provenance` backwards compatible.

- [ ] **Step 3: Run both target files and retain RED**

Run bridge and worker tests in the local Python 3.12 environment. Expected: missing metadata/validation failures.

- [ ] **Step 4: Time existing worker blocks and expose the existing red calculation**

Use `time.perf_counter_ns()` around the existing inference call(s) and CAMP materialize/select block. For DP-default `plan_tick`, pass the existing `planned_red_cost` callback from `main` and evaluate `default[None, ...]`. Do not call `run_fixed_dp_candidates` for baseline.

```python
response_metadata.update({
    "operation": operation,
    "selected_planned_red_light_cost": float(selected_red_cost),
    "planned_red_source": "fixed_dp_red_cost_v18",
    "worker_latency_ms": {
        "dp_inference": inference_ns / 1e6,
        "atom_selector": selector_ns / 1e6 if arm == "camp" else 0.0,
    },
})
```

- [ ] **Step 5: Add narrow bridge validation**

Validate the two worker latency keys, finite nonnegative values, planned-red scalar, source name, operation, and existing selected trajectory SHA. Do not add a serializer, daemon, queue, or protocol version.

- [ ] **Step 6: Run GREEN in local and fixed-DP environments**

Run bridge/worker tests locally and under `/root/autodl-tmp/dp312_venv`. Expected: all tests pass without real checkpoint inference.

- [ ] **Step 7: Commit and push this slice**

```bash
git add camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py \
  scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py \
  camp_core/tests/test_diffusion_planner_v19_nuplan_bridge.py \
  camp_core/tests/test_diffusion_planner_v19_dp_worker.py
git commit -m "feat(v19): record planned-red and worker timing"
git push origin main
```

### Task 4: Planner tick receipts and harness integration

**Files:**
- Modify: `camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py`
- Modify: `camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py`
- Modify: `camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py`

**Interfaces:**
- Produces one immutable `planning_receipt.json` per tick with pair/run key, arm, iteration, timestamp, request/response/selected SHA values, worker exit code, `native_ranked_top1=false`, and exactly six latency fields.
- Makes `execute_arm` call `materialize_closed_loop_evidence` directly; no injectable production component materializer remains.

- [ ] **Step 1: Add failing adapter receipt tests**

Patch `perf_counter_ns`, subprocess, request/response IO, and trajectory conversion. Assert all six fields, `total_planning_path >= max(other fields)`, exact arm/run identity, and exclusive creation. Assert an existing receipt, cross-arm response, worker nonzero, missing worker latency, or failed CAMP response raises without returning a trajectory.

- [ ] **Step 2: Add failing harness integration tests**

Use fake history/scenario/metric engine plus real pure evidence materialization. Assert `history.json`, `official_metrics.json`, `result.json`, and per-tick receipts agree; missing any of eight safety fields or six latency fields creates `failure.json` and fails the pair.

- [ ] **Step 3: Run both targets and retain RED**

Expected: missing receipt writer and production evidence wiring.

- [ ] **Step 4: Add minimal timing around existing planner operations**

Measure causal conversion, `write_request`, `read_response`, and total path with `perf_counter_ns`. Merge the two validated worker fields. Build the official trajectory exactly as before, then atomically create the receipt with mode `x`; never overwrite a prior tick.

```python
latency = {
    "causal_conversion": causal_ns / 1e6,
    "bridge_write": write_ns / 1e6,
    **response.metadata["worker_latency_ms"],
    "bridge_read": read_ns / 1e6,
    "total_planning_path": total_ns / 1e6,
}
```

- [ ] **Step 5: Wire the existing harness to the evidence adapter**

Remove the production callback requirement from `execute_arm`. Load tick receipts from only that arm root, call `materialize_closed_loop_evidence`, validate latency keys with `_validate_latency`, compute unchanged SafetyCost v1, and preserve the existing failure JSON path.

- [ ] **Step 6: Run GREEN and official-runtime construction-only tests**

Run adapter/harness/evidence tests in the official Python 3.9 environment. Do not call `SimulationRunner.run`, planner compute with a real worker, metric compute, or a holdout.

- [ ] **Step 7: Commit and push this slice**

```bash
git add camp_core/camp_core/integrations/nuplan_closed_loop_adapter.py \
  scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py \
  camp_core/tests/test_diffusion_planner_v19_nuplan_closed_loop_adapter.py \
  camp_core/tests/test_diffusion_planner_v19_closed_loop_smoke_harness.py
git commit -m "feat(v19): integrate smoke evidence receipts"
git push origin main
```

### Task 5: Non-execution integration review and controller update

**Files:**
- Modify: `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`
- Modify: `docs/diffusion_planner_current_status.md` only inside `## Current V19 Status`
- Append: `docs/diffusion_planner_v19_iteration_audit.md`

**Interfaces:**
- Produces an immutable TDD result/review artifact and advances only to a fresh execution-preflight gate.

- [ ] **Step 1: Run bounded local verification**

Run py_compile, the five v19 target files, v18/v19 pointer tests, causal adapter/materializer/atom tests, replay-summary tests, and `git diff --check`. A Windows-only unrelated torch import abort is not a pass; use the isolated AutoDL fixed-DP suite for that file and retain the local failure if encountered.

- [ ] **Step 2: Run separated AutoDL verification**

After proving zero peer jobs and at least 10 GiB free, ff-only sync. Run official-history/adapter/evidence/harness tests in `camp_v19_nuplan_env` and bridge/worker tests in `dp312_venv`. Reverify CAMP/GitHub/AutoDL HEADs, fixed DP/source heads, tracked-clean state, design/protocol/selector/checkpoint hashes, and both prior artifact manifests.

- [ ] **Step 3: Produce immutable TDD and independent-review artifacts**

Include `HEADS`, `COMMAND`, exit codes, stdout/stderr, JSON/MD reviews, source hashes, `SHA256SUMS`, and root SHA. Record `no_planner_compute=true`, `no_worker_execution=true`, `no_simulator_run=true`, `no_metric_compute=true`, and `no_holdout_access=true`.

- [ ] **Step 4: Update the controller**

Append the passed result and retained failures to the v19 audit. Update only the Current V19 tuple and its regression test. Set the next target to `v19_nuplan_v12_closed_loop_smoke_execution_preflight_retry_only`; do not authorize execution from the TDD result alone.

- [ ] **Step 5: Commit, push, AutoDL ff-only, and reread EOF**

If the new preflight proves every field and receipt before execution, continue to its next target. Stop on a running job, drift, incomplete component/receipt, protocol-changing repair, or any existing stop condition.
