# v18 nuPlan Canonical Materialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Implement the exact causal nuPlan mini physical-mask, canonical 14D atom, and train/calibration expert-label materializer without changing fixed DP or the frozen K=8 candidate corpus.

**Architecture:** Extend the existing v18 orchestrator and its two CAMP integration modules. Pure NumPy helpers compute route projection, bounded 32+5 OBB evidence, and canonical atoms; the adapter alone may query expert future, and only after split and eligibility checks. The existing runner gets one mutually exclusive materialization mode and writes a new immutable root.

**Tech Stack:** Python 3.12, NumPy, SQLite, existing CAMP geometry helpers, fixed-DP torch reward function, pytest, Git, AutoDL.

## Global Constraints

- Work directly on the current main branch; the user preselected Inline Execution.
- Do not restart the goal or repeat an audited gate.
- Fixed DP stays tracked-clean at 7a1d33da277a1992ec474b5383a0c963c72e04e4.
- K is exactly 8; never generate, modify, repair, blend, or postprocess candidates.
- The frozen candidate root and its SHA256SUMS hash remain immutable.
- v18 audit EOF is the controller authority. In current_status, parse only the Current V18 Status section.
- Candidate 0 is the fixed-DP deterministic/MAP baseline. dp_top1_index=0 is position-only, not native K=8 ranking evidence.
- Before first paired evaluation, independently prove candidate 0 equals a same-input deterministic/MAP fixed-DP inference elementwise or by SHA256.
- Exact OBB statements are limited to the frozen observable source of at most 32 dynamic and 5 static objects.
- Never infer complete-scene feasibility, closed-loop safety, or a safety claim from the 32+5 source.
- All-K-infeasible records retain masks/reasons but have no canonical NPZ, label, training, calibration, or evaluation entry.
- Never force candidate 0 feasible and never fall back to all K for progress_shortfall.
- Expert labels are train/calibration only; all 71 holdout labels stay sealed.
- Reuse the existing runner and helpers; add no dependency or per-gate runner.
- Use TDD for every behavior change and commit only task files at each checkpoint.
- For local PowerShell tests set PYTHONPATH to the repo root plus repo\camp_core.

---

### Task 1: Enforce v18 pointer and baseline/scope contracts

**Files:**
- Modify: scripts/integrations/run_diffusion_planner_dp_camp_v18.py:33-71
- Modify: camp_core/tests/test_diffusion_planner_v18_orchestrator.py:1-125

**Interfaces:**
- Produces: read_v18_status_pointer(current_status: Path, v18_audit: Path) -> dict[str, str]
- Produces: BASELINE_INDEX, BASELINE_SEMANTICS, NATIVE_RANKED_TOP1, FEASIBILITY_SCOPE, CLOSED_LOOP_SAFETY_CLAIM

- [ ] **Step 1: Write failing pointer and semantic tests**

~~~python
def test_v18_pointer_reader_ignores_historical_file_tail(tmp_path) -> None:
    module = _orchestrator()
    pointer = {
        "current_v18_status": "ready",
        "current_v18_artifact_scope": "scope",
        "current_v18_artifact": "/artifact",
        "current_v18_artifact_root_sha256": "a" * 64,
        "next_work_target": "implementation_only",
    }
    lines = "\n".join(f"{key}={value}" for key, value in pointer.items())
    status = tmp_path / "status.md"
    status.write_text(
        "## Current V18 Status\n" + lines
        + "\n## Historical V14\nnext_work_target=wrong\n",
        encoding="utf-8",
    )
    audit = tmp_path / "audit.md"
    audit.write_text(lines + "\n", encoding="utf-8")

    assert module.read_v18_status_pointer(status, audit) == pointer


def test_candidate_zero_metadata_is_deterministic_map_not_native_ranking() -> None:
    module = _orchestrator()
    assert module.BASELINE_INDEX == 0
    assert module.BASELINE_SEMANTICS == "fixed_dp_deterministic_map_baseline"
    assert module.NATIVE_RANKED_TOP1 is False
    assert module.FEASIBILITY_SCOPE == (
        "frozen_observable_32_dynamic_plus_5_static_only"
    )
    assert module.CLOSED_LOOP_SAFETY_CLAIM is False


def test_checked_in_current_v18_pointer_matches_v18_audit_eof() -> None:
    module = _orchestrator()
    root = module.ROOT
    pointer = module.read_v18_status_pointer(
        root / "docs" / "diffusion_planner_current_status.md",
        root / "docs" / "diffusion_planner_v18_iteration_audit.md",
    )
    assert pointer["next_work_target"].startswith("v18_nuplan_mini_")
~~~

- [ ] **Step 2: Run tests and verify RED**

Run:

~~~powershell
python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -q
~~~

Expected: FAIL because read_v18_status_pointer and the semantic constants do not exist.

- [ ] **Step 3: Implement the bounded pointer reader and constants**

~~~python
POINTER_KEYS = (
    "current_v18_status",
    "current_v18_artifact_scope",
    "current_v18_artifact",
    "current_v18_artifact_root_sha256",
    "next_work_target",
)
BASELINE_INDEX = 0
BASELINE_SEMANTICS = "fixed_dp_deterministic_map_baseline"
NATIVE_RANKED_TOP1 = False
FEASIBILITY_SCOPE = "frozen_observable_32_dynamic_plus_5_static_only"
CLOSED_LOOP_SAFETY_CLAIM = False


def _latest_pointer(lines: list[str]) -> dict[str, str]:
    result = {}
    for key in POINTER_KEYS:
        matches = [line for line in lines if line.startswith(f"{key}=")]
        if not matches:
            raise ValueError(f"missing {key}")
        result[key] = matches[-1].split("=", 1)[1]
    return result


def read_v18_status_pointer(
    current_status: Path, v18_audit: Path
) -> dict[str, str]:
    text = current_status.read_text(encoding="utf-8")
    try:
        section = text.split("## Current V18 Status", 1)[1].split(
            "\n## ", 1
        )[0]
    except IndexError as exc:
        raise ValueError("Current V18 Status section is missing") from exc
    status_pointer = _latest_pointer(section.splitlines())
    audit_pointer = _latest_pointer(
        v18_audit.read_text(encoding="utf-8").splitlines()
    )
    if status_pointer != audit_pointer:
        raise ValueError("latest v18 status pointer does not match v18 audit EOF")
    return audit_pointer
~~~

Also update the existing sampling test to capture latent scales and assert exactly one 0.0 draw followed by seven noise_scale draws. Do not rename or remove the historical dp_top1_index source field.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

~~~powershell
python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -q
~~~

Expected: all orchestrator tests pass.

- [ ] **Step 5: Commit checkpoint**

~~~powershell
git add scripts/integrations/run_diffusion_planner_dp_camp_v18.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py
git commit -m "test: enforce v18 controller and baseline semantics"
git push origin main
~~~

---

### Task 2: Add the isolated train/cal expert-future loader

**Files:**
- Modify: camp_core/camp_core/integrations/nuplan_causal_adapter.py:214-365
- Modify: camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py:1-246

**Interfaces:**
- Produces: load_nuplan_expert_ego_future(db_path: str | Path, lidar_pc_token: str | bytes, *, target_dt_s: float, horizon_steps: int = 80) -> np.ndarray
- Returns: float32 array [80,3] containing decision-frame x, y, wrapped yaw for times 0.1 through 8.0 seconds

- [ ] **Step 1: Write failing interpolation and no-extrapolation tests**

Create a temporary SQLite DB with lidar_pc(token, scene_token, timestamp, ego_pose_token) and ego_pose(token, x, y, qw, qx, qy, qz). Insert the decision pose plus same-scene poses every 0.2 seconds through 8.0 seconds, and insert a distracting future row from another scene.

~~~python
def _expert_future_db(tmp_path, *, end_seconds: float):
    path = tmp_path / "expert.sqlite"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE lidar_pc("
        "token BLOB PRIMARY KEY, scene_token BLOB, timestamp INTEGER, "
        "ego_pose_token BLOB);"
        "CREATE TABLE ego_pose("
        "token BLOB PRIMARY KEY, x REAL, y REAL, "
        "qw REAL, qx REAL, qy REAL, qz REAL);"
    )
    scene = b"s" * 16
    decision = b"d" * 16
    for index in range(int(round(end_seconds / 0.2)) + 1):
        pose = index.to_bytes(16, "big")
        lidar = decision if index == 0 else (1000 + index).to_bytes(16, "big")
        timestamp = index * 200_000
        db.execute(
            "INSERT INTO ego_pose VALUES (?, ?, ?, 1, 0, 0, 0)",
            (pose, index * 0.2, 0.0),
        )
        db.execute(
            "INSERT INTO lidar_pc VALUES (?, ?, ?, ?)",
            (lidar, scene, timestamp, pose),
        )
    other_pose = b"o" * 16
    db.execute(
        "INSERT INTO ego_pose VALUES (?, 999, 999, 1, 0, 0, 0)",
        (other_pose,),
    )
    db.execute(
        "INSERT INTO lidar_pc VALUES (?, ?, ?, ?)",
        (b"x" * 16, b"z" * 16, 4_000_000, other_pose),
    )
    db.commit()
    db.close()
    return path, decision


def test_expert_future_interpolates_only_same_scene_in_decision_frame(tmp_path):
    db_path, decision = _expert_future_db(tmp_path, end_seconds=8.0)
    future = load_nuplan_expert_ego_future(
        db_path, decision, target_dt_s=0.1
    )
    assert future.shape == (80, 3)
    np.testing.assert_allclose(future[:, 0], np.arange(1, 81) * 0.1)
    np.testing.assert_allclose(future[:, 1], 0.0)
    assert np.all(np.abs(future[:, 2]) <= np.pi)


def test_expert_future_rejects_required_extrapolation(tmp_path):
    db_path, decision = _expert_future_db(tmp_path, end_seconds=7.8)
    with pytest.raises(NuPlanCausalSourceError, match="bracket|extrapolat"):
        load_nuplan_expert_ego_future(
            db_path, decision, target_dt_s=0.1
        )
~~~

- [ ] **Step 2: Run focused tests and verify RED**

Run:

~~~powershell
python -m pytest camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py -q
~~~

Expected: collection/import FAIL because load_nuplan_expert_ego_future does not exist.

- [ ] **Step 3: Implement the read-only loader**

~~~python
def load_nuplan_expert_ego_future(
    db_path: str | Path,
    lidar_pc_token: str | bytes,
    *,
    target_dt_s: float,
    horizon_steps: int = 80,
) -> np.ndarray:
    if not np.isfinite(target_dt_s) or target_dt_s <= 0.0:
        raise NuPlanCausalSourceError("target_dt_s must be finite and positive")
    token = _token_bytes(lidar_pc_token)
    db = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    try:
        decision = db.execute(
            "SELECT scene_token, timestamp, ego_pose_token "
            "FROM lidar_pc WHERE token = ?",
            (token,),
        ).fetchone()
        if decision is None:
            raise NuPlanCausalSourceError("decision lidar token is absent")
        rows = db.execute(
            "SELECT l.timestamp, e.x, e.y, e.qw, e.qx, e.qy, e.qz "
            "FROM lidar_pc AS l JOIN ego_pose AS e ON e.token=l.ego_pose_token "
            "WHERE l.scene_token=? AND l.timestamp>=? ORDER BY l.timestamp",
            (decision[0], decision[1]),
        ).fetchall()
    finally:
        db.close()
    timestamps = np.asarray([row[0] for row in rows], dtype=np.int64)
    if timestamps.size < 2 or np.any(np.diff(timestamps) <= 0):
        raise NuPlanCausalSourceError("expert timestamps must be strictly increasing")
    source_t = (timestamps - int(decision[1])) / 1_000_000.0
    target_t = np.arange(1, horizon_steps + 1, dtype=np.float64) * target_dt_s
    if source_t[0] > 0.0 or source_t[-1] < target_t[-1]:
        raise NuPlanCausalSourceError("expert future does not bracket target horizon")
    xy = np.asarray([[row[1], row[2]] for row in rows], dtype=np.float64)
    yaw = np.unwrap(np.asarray([_quaternion_yaw(*row[3:]) for row in rows]))
    decision_xy = xy[0]
    decision_yaw = float(yaw[0])
    world_xy = np.column_stack(
        [np.interp(target_t, source_t, xy[:, axis]) for axis in range(2)]
    )
    c, s = math.cos(decision_yaw), math.sin(decision_yaw)
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    local_xy = (world_xy - decision_xy) @ rotation.T
    local_yaw = np.arctan2(
        np.sin(np.interp(target_t, source_t, yaw) - decision_yaw),
        np.cos(np.interp(target_t, source_t, yaw) - decision_yaw),
    )
    return np.column_stack([local_xy, local_yaw]).astype(np.float32)
~~~

- [ ] **Step 4: Run adapter tests and verify GREEN**

Run:

~~~powershell
python -m pytest camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py -q
~~~

Expected: all adapter tests pass, including existing causal-history tests.

- [ ] **Step 5: Commit checkpoint**

~~~powershell
git add camp_core/camp_core/integrations/nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py
git commit -m "feat: load sealed-split nuPlan expert labels"
git push origin main
~~~

---

### Task 3: Project candidates onto real per-segment route sources

**Files:**
- Modify: camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py:1-348
- Modify: camp_core/tests/test_diffusion_planner_v18_orchestrator.py

**Interfaces:**
- Produces: project_candidates_to_route(candidates, route_lanes, route_speed_limits, route_has_speed_limits) -> dict[str, np.ndarray]
- Returned arrays: lateral_offset, left_width, right_width, speed_limit [K,T], route_progress [K]

- [ ] **Step 1: Write failing variable-source tests**

Build two connected route slots whose left/right widths and speed limits differ. Assert that projections in each slot inherit their own source, that right-side and left-side deviations use the correct boundary, and that a global SE(2) transform leaves lateral widths/progress unchanged.

~~~python
projection = project_candidates_to_route(
    candidates,
    route_lanes,
    np.array([[5.0], [12.0]] + [[0.0]] * 23),
    np.array([[True], [True]] + [[False]] * 23),
)
np.testing.assert_allclose(projection["speed_limit"][0, :40], 5.0)
np.testing.assert_allclose(projection["speed_limit"][0, 40:], 12.0)
assert projection["left_width"][0, 10] != projection["left_width"][0, 60]
assert projection["route_progress"].shape == (8,)
~~~

- [ ] **Step 2: Run focused test and verify RED**

Run:

~~~powershell
python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -q
~~~

Expected: FAIL because project_candidates_to_route is absent.

- [ ] **Step 3: Implement ordered projection**

Validate [8,80,4] candidates and [25,20,33] route lanes. Keep rows whose validity channel 13 is true and whose direction norm is positive. Flatten valid slots in route order, repeat each slot's required positive speed limit for its 20 points, and form nonzero ordered segments.

For each candidate point, compute every clamped segment projection, choose the minimum-distance segment, interpolate left/right offsets and speed, and compute:

~~~python
normal = np.array([-direction[1], direction[0]])
lateral = np.dot(point - projected_xy, normal)
left_width = np.dot(interpolated_left_offset, normal)
right_width = -np.dot(interpolated_right_offset, normal)
arc = segment_arc_start + along
~~~

Reject non-positive side widths or speed. Define route progress as the last value of maximum.accumulate(projected_arc) for each candidate. Do not use nearby lanes, median widths, scalar speed, path length, or current speed.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

~~~powershell
python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -q
~~~

Expected: route tests and prior orchestrator tests pass.

- [ ] **Step 5: Commit checkpoint**

~~~powershell
git add camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py
git commit -m "feat: project v18 candidates onto route sources"
git push origin main
~~~

---

### Task 4: Build exact-within-32+5 OBB evidence and masks

**Files:**
- Modify: camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py
- Modify: camp_core/tests/test_diffusion_planner_v18_orchestrator.py

**Interfaces:**
- Produces: build_observable_obbs(neighbor_predictions, neighbor_valid_mask, neighbor_history, static_objects) -> np.ndarray
- Produces: observable_feasibility(candidates, signal_mask, route_projection, obstacle_obbs, ego_shape) -> dict[str, object]

- [ ] **Step 1: Write failing OBB and all-false tests**

~~~python
obbs = build_observable_obbs(
    neighbor_predictions, neighbor_valid_mask, neighbor_history, static_objects
)
assert obbs.shape == (8, 37, 80, 5)
assert module.FEASIBILITY_SCOPE == (
    "frozen_observable_32_dynamic_plus_5_static_only"
)

result = observable_feasibility(
    candidates, signal_mask, projection, obbs, ego_shape
)
np.testing.assert_array_equal(
    result["physical_feasible_mask"],
    result["signal_mask"]
    & result["lane_feasible_mask"]
    & result["obb_collision_free_mask"],
)
assert result["closed_loop_safety_claim"] is False
assert not bool(result["physical_feasible_mask"][0])
~~~

Include one collision caused only by a valid dynamic slot, one caused only by a static box, a padded dynamic slot that is ignored, and an all-eight-collide case whose reasons retain obb_collision for every candidate.

- [ ] **Step 2: Run focused tests and verify RED**

Expected: FAIL because the OBB helpers are absent.

- [ ] **Step 3: Implement bounded OBB construction and exact checks**

Dynamic rows are [x, y, atan2(sin, cos), length, width] using prediction columns 0:4 and matching causal-history columns 7 and 6. Static rows use [x, y, atan2(sin, cos), length, width] from columns 0:6 and repeat for 80 steps. Include only the 32 frozen validity slots and nonzero static rows; reject malformed headings or non-positive dimensions.

Use causal ego_shape as [wheelbase, length, width]. For every candidate, call the existing CAMPSelector._collision_failure_reason OBB branch with point-static context disabled. Use _obb_corners and _obb_distance for exact surface distances inside the frozen source. Store candidate-level signal, lane, collision-free, final masks, stable reasons, FEASIBILITY_SCOPE, and CLOSED_LOOP_SAFETY_CLAIM.

Lane feasibility uses the side-specific boundary plus the existing 1.0 metre CAMP corridor buffer. Lane-deviation atoms later use the boundary without that allowance.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

~~~powershell
python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -q
~~~

Expected: OBB scope/mask tests and prior tests pass.

- [ ] **Step 5: Commit checkpoint**

~~~powershell
git add camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py
git commit -m "feat: materialize bounded v18 OBB feasibility"
git push origin main
~~~

---

### Task 5: Assemble and validate canonical dp_camp_v10_14d

**Files:**
- Modify: camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py
- Modify: camp_core/tests/test_diffusion_planner_v18_orchestrator.py

**Interfaces:**
- Produces: materialize_canonical_14d(*, candidates, causal_input, neighbor_predictions, neighbor_valid_mask, signal_mask, planned_red_light_cost, dt) -> dict[str, object]
- Returns atom_matrix=None for source-incomplete or all-K-infeasible records; otherwise [8,14]

- [ ] **Step 1: Write failing atom and fail-closed tests**

Test exact atom order, finite nonnegative [8,14] shape, variable per-step speed/lane inputs, exact-within-32+5 clearance, feasible-only progress reference, candidate-0 DP-prior reference, and future perturbation invariance.

~~~python
result = materialize_canonical_14d(
    candidates=candidates,
    causal_input=causal_input,
    neighbor_predictions=neighbors,
    neighbor_valid_mask=valid,
    signal_mask=np.ones(8, dtype=bool),
    planned_red_light_cost=np.arange(8, dtype=np.float64),
    dt=0.1,
)
assert result["canonical_eligible"] is True
assert result["atom_matrix"].shape == (8, 14)
assert np.all(np.isfinite(result["atom_matrix"]))
assert np.all(result["atom_matrix"] >= 0.0)
np.testing.assert_allclose(
    result["atom_matrix"][:, 9],
    np.maximum(
        result["route_progress"][result["physical_feasible_mask"]].max()
        - result["route_progress"],
        0.0,
    ),
)
~~~

For all-K-infeasible input assert atom_matrix is None, exclusion_reason is all_candidates_physically_infeasible, candidate 0 stays false, and no all-K progress reference is computed.

- [ ] **Step 2: Run focused tests and verify RED**

Expected: FAIL because materialize_canonical_14d is absent.

- [ ] **Step 3: Implement the minimal canonical assembler**

Compute:

- jerk early/late/full from third position differences and dt;
- RMS acceleration from second differences;
- three speed hinges using projected per-step limits and margins 0.0/0.5/1.0;
- lane deviation from side-specific boundary overrun without corridor allowance;
- clearance as dt times squared hinge of 3.0 metres minus exact OBB surface distance;
- progress shortfall using only the nonempty physical feasible set;
- supplied fixed-DP planned-red cost;
- existing compute_lateral_comfort_shadow_costs absolute lateral cost;
- existing compute_red_stopping_margin_costs with current red route points;
- existing compute_dp_prior_comfort_excess_costs jerk excess.

Call canonical_atom_availability with every real-source flag, then validate_canonical_atom_matrix("dp_camp_v10_14d", availability, matrix). Never substitute zero for an unavailable source.

- [ ] **Step 4: Run v17/v18 causal tests and verify GREEN**

Run:

~~~powershell
python -m pytest camp_core/tests/test_diffusion_planner_v17_causal_atom_availability.py camp_core/tests/test_diffusion_planner_v17_causal_materializer.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py -q
~~~

Expected: all selected tests pass.

- [ ] **Step 5: Commit checkpoint**

~~~powershell
git add camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py
git commit -m "feat: materialize v18 canonical 14d atoms"
git push origin main
~~~

---

### Task 6: Add immutable materialization mode to the existing orchestrator

**Files:**
- Modify: scripts/integrations/run_diffusion_planner_dp_camp_v18.py:191-407
- Modify: camp_core/tests/test_diffusion_planner_v18_orchestrator.py

**Interfaces:**
- Produces: run_materialization(args: argparse.Namespace) -> dict[str, object]
- New mutually exclusive CLI inputs: --candidate_root, --expected_candidate_root_sha256, --materialize_output_dir, --current_status, --v18_audit

- [ ] **Step 1: Write failing output-boundary tests**

Use a two-row fake manifest: one calibration row that is eligible and one holdout row. Patch causal replay, canonical materialization, fixed-DP red cost, and expert loader. Assert:

~~~python
report = module.run_materialization(args)
assert report["model_calls"] == 0
assert report["candidate_generation_executed"] is False
assert report["baseline_semantics"] == module.BASELINE_SEMANTICS
assert report["native_ranked_top1"] is False
assert report["feasibility_scope"] == module.FEASIBILITY_SCOPE
assert report["closed_loop_safety_claim"] is False
assert label_calls == ["calibration_decision"]
~~~

Open output NPZ files with allow_pickle=False. Calibration contains expert_ego_future_xyh; holdout does not. Add an all-K-infeasible row and assert it appears in records.jsonl with full masks/reasons but has canonical_output_npz=null and never calls the label loader. Assert existing output raises FileExistsError and every candidate source hash is unchanged.

- [ ] **Step 2: Run orchestrator tests and verify RED**

Expected: FAIL because run_materialization and materialization CLI fields are absent.

- [ ] **Step 3: Implement source verification and fixed-DP red cost**

Require SHA256(candidate_root / "SHA256SUMS") to equal --expected_candidate_root_sha256. Parse records.jsonl, verify all 367 identities and per-NPZ hashes, load every NPZ with allow_pickle=False, and replay causal input SHA before use.

Install fixed DP on sys.path without loading the model. On CPU, compute planned red cost with:

~~~python
from rlvr.reward import RewardConfig, compute_red_light_score_batch

config = RewardConfig(dt=dt)
scores = compute_red_light_score_batch(
    torch.from_numpy(candidates).float(),
    {"route_lanes": torch.from_numpy(causal_input["route_lanes"]).float()},
    config,
)
cost = np.maximum(-scores.detach().cpu().numpy().astype(np.float64), 0.0)
~~~

This is the frozen DP formula; do not reimplement or alter DP.

- [ ] **Step 4: Implement atomic per-record output**

At function entry call read_v18_status_pointer. Refuse an existing target. Write through temporary files and os.replace. records.jsonl contains all source rows and freezes component/final masks, reasons, source hashes, baseline metadata, equivalence_verified=false, scope/non-safety metadata, canonical eligibility, label-read flag, and NPZ path/hash or null exclusion.

Only after split in {train, calibration} and canonical_eligible is true call load_nuplan_expert_ego_future. Holdout and excluded rows never call it. Eligible holdout NPZs contain atoms/masks but no label field. Verify candidate SHA files again after the run.

- [ ] **Step 5: Run all focused tests and verify GREEN**

Run:

~~~powershell
python -m py_compile camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py camp_core/camp_core/integrations/nuplan_causal_adapter.py scripts/integrations/run_diffusion_planner_dp_camp_v18.py
python -m pytest camp_core/tests/test_diffusion_planner_v17_causal_atom_availability.py camp_core/tests/test_diffusion_planner_v17_causal_materializer.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py -q
git diff --check
~~~

Expected: compile exit 0, all selected tests pass, diff check empty.

- [ ] **Step 6: Commit checkpoint**

~~~powershell
git add scripts/integrations/run_diffusion_planner_dp_camp_v18.py camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py camp_core/camp_core/integrations/nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py
git commit -m "feat: implement v18 canonical materializer"
git push origin main
~~~

---

### Task 7: AutoDL verification, immutable implementation artifact, and EOF handoff

**Files:**
- Modify: docs/diffusion_planner_v18_iteration_audit.md
- Modify: docs/diffusion_planner_current_status.md within Current V18 Status only

**Interfaces:**
- Consumes: the implementation commit from Task 6
- Produces: immutable AutoDL implementation evidence and the next v18 EOF target

- [ ] **Step 1: AutoDL ff-only and preflight safety checks**

Load network_turbo, require AutoDL CAMP tracked-clean, ff-only to GitHub main, verify fixed DP HEAD and tracked status, verify no v18 job is running, and do not start a duplicate.

- [ ] **Step 2: Run the implementation-only verification artifact**

Create one new artifact directory under /root/autodl-tmp with HEADS, COMMAND, stdout.txt, stderr.txt, run.exit, JSON/MD summary, SHA256SUMS, and ROOT_SHA256SUMS. Run only the Task 6 compile/tests/diff check; invoke the model zero times and do not execute real corpus materialization.

Expected: exit 0, empty stderr apart from explicitly classified upstream warnings, all focused tests pass, candidate root SHA256 remains 92b2c989187d58387e3310579cc9d3ea9695b2b369684d807020c98f6885b028, and DP remains fixed.

- [ ] **Step 3: Update audit/status without changing historical file EOF**

Append one implementation gate to the v18 audit. In current_status modify only Current V18 Status. Record tests, artifact/root SHA, three-surface CAMP HEAD, DP HEAD, zero model calls, no candidate/label materialization, baseline and 32+5 scope semantics, and sealed holdout.

Set:

~~~text
current_v18_status=v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_implementation_passed
next_work_target=v18_nuplan_mini_physical_feasibility_canonical_atom_and_expert_label_materialization_execution_preflight_only
~~~

Keep the actual current_status EOF historical v14. Require the latest five-field Current V18 Status pointer to equal the new v18 audit EOF.

- [ ] **Step 4: Verify, commit, push, and AutoDL ff-only**

Run:

~~~powershell
git diff --check
python -m pytest camp_core/tests/test_diffusion_planner_v18_orchestrator.py -q
git add docs/diffusion_planner_v18_iteration_audit.md docs/diffusion_planner_current_status.md
git commit -m "docs: record v18 canonical materializer implementation"
git push origin main
~~~

Then AutoDL ff-only to the docs commit, verify local/GitHub/AutoDL CAMP HEAD equality and fixed DP HEAD, and reread only the v18 audit EOF to select the next gate.

---

## Inline Execution

The user preselected option 2 / Inline Execution. After this plan is committed, immediately invoke superpowers:executing-plans and execute tasks in order with checkpoint reports but no approval waits. Stop only at the explicit user-defined boundaries in the approved spec.
