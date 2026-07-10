# v18 nuPlan Causal Source Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Repair the existing v18 CAMP path so a new immutable nuPlan candidate corpus contains real fixed-DP static input, candidate-specific same-call neighbor predictions, and fail-closed unknown-signal provenance.

**Architecture:** Keep the existing adapter and single v18 orchestrator. The adapter encodes the nearest five real decision-tick static objects in fixed-DP's historical schema; the orchestrator captures ego plus first-32 neighbor predictions from the same eight decoder calls, refreshes causal hashes into a new manifest, and writes new candidate/provenance fields without touching the old corpus.

**Tech Stack:** Python 3.12, sqlite3, argparse, hashlib, json, NumPy, existing PyTorch, pytest, Git, and AutoDL.

## Global Constraints

- CAMP branch remains main; confirm repo and branch before each task.
- Fixed DP remains tracked-clean at 7a1d33da277a1992ec474b5383a0c963c72e04e4.
- Modify no DP source, config, weight, or checkpoint.
- K remains 8: deterministic DP Top-1 at index 0 plus seven stochastic samples.
- Do not access expert future, holdout labels, or closed-loop outcomes.
- Do not mutate the old manifest or /root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_candidates_44b4082ce707.
- Do not add a runner, dependency, abstraction layer, or unrelated cleanup.
- WHITE/unknown is unavailable, never green/no-red/zero cost.
- Do not materialize atoms/labels, train, evaluate, claim, promote, or deploy in this plan.
- Each code task uses TDD, git diff --check, and a focused commit; Task 4 performs the normal push, AutoDL ff-only, evidence build, and live EOF re-read.

---

### Task 1: Real decision-tick static objects

**Files:**
- Modify: camp_core/camp_core/integrations/nuplan_causal_adapter.py:206-420
- Test: camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py

**Interfaces:**
- Consumes: nuPlan lidar_box, track, and category rows at one lidar_pc_token.
- Produces: _load_static_objects(db, lidar_pc_token, current_ego_xy) -> np.ndarray with shape [5,10], world-frame poses, deterministic nearest-first order, and zero padding only after real rows.

- [ ] **Step 1: Add failing static-object tests**

Add sqlite3 and _load_static_objects imports, then add:

~~~python
def _static_object_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.executescript(
        """
        CREATE TABLE category(token BLOB PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE track(token BLOB PRIMARY KEY, category_token BLOB NOT NULL);
        CREATE TABLE lidar_box(
            lidar_pc_token BLOB NOT NULL,
            track_token BLOB NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            yaw REAL NOT NULL,
            width REAL NOT NULL,
            length REAL NOT NULL
        );
        """
    )
    names = ("czone_sign", "barrier", "traffic_cone", "generic_object", "vehicle")
    for index, name in enumerate(names):
        category = bytes([index + 1])
        track = bytes([index + 11])
        db.execute("INSERT INTO category VALUES (?, ?)", (category, name))
        db.execute("INSERT INTO track VALUES (?, ?)", (track, category))
        db.execute(
            "INSERT INTO lidar_box VALUES (?, ?, ?, ?, ?, ?, ?)",
            (b"decision", track, float(5 - index), 0.0, 0.1 * index, 1.0, 2.0),
        )
    return db


def test_static_objects_use_exact_fixed_dp_schema_and_ignore_dynamic() -> None:
    db = _static_object_db()
    try:
        actual = _load_static_objects(db, b"decision", np.array([0.0, 0.0]))
    finally:
        db.close()

    assert actual.shape == (5, 10)
    assert actual.dtype == np.float32
    assert np.count_nonzero(np.any(actual != 0.0, axis=1)) == 4
    np.testing.assert_array_equal(actual[:4, 6:], np.eye(4, dtype=np.float32)[::-1])
    assert not np.any(actual[4])
    assert np.all(np.diff(np.linalg.norm(actual[:4, :2], axis=1)) >= 0.0)


def test_static_objects_fail_closed_on_nonpositive_dimensions() -> None:
    db = _static_object_db()
    db.execute("UPDATE lidar_box SET width = 0 WHERE track_token = ?", (bytes([11]),))
    try:
        with pytest.raises(NuPlanCausalSourceError, match="dimensions"):
            _load_static_objects(db, b"decision", np.array([0.0, 0.0]))
    finally:
        db.close()
~~~

- [ ] **Step 2: Run RED**

Run:

~~~powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m pytest -q camp_core\tests\test_diffusion_planner_v18_nuplan_causal_adapter.py -k static_objects
~~~

Expected: collection fails because _load_static_objects is absent.

- [ ] **Step 3: Implement the minimal static loader**

Add near _load_neighbor_histories:

~~~python
_STATIC_OBJECT_TYPES = {
    "czone_sign": (1.0, 0.0, 0.0, 0.0),
    "barrier": (0.0, 1.0, 0.0, 0.0),
    "traffic_cone": (0.0, 0.0, 1.0, 0.0),
    "generic_object": (0.0, 0.0, 0.0, 1.0),
}


def _load_static_objects(
    db: sqlite3.Connection,
    lidar_pc_token: bytes,
    current_ego_xy: np.ndarray,
) -> np.ndarray:
    rows = db.execute(
        """
        SELECT b.track_token, b.x, b.y, b.yaw, b.width, b.length, c.name
        FROM lidar_box AS b
        JOIN track AS t ON t.token = b.track_token
        JOIN category AS c ON c.token = t.category_token
        WHERE b.lidar_pc_token = ?
        """,
        (lidar_pc_token,),
    ).fetchall()
    encoded = []
    ego_xy = np.asarray(current_ego_xy, dtype=np.float64).reshape(2)
    for track_token, x, y, yaw, width, length, category in rows:
        name = str(category).lower()
        if name not in _STATIC_OBJECT_TYPES:
            continue
        values = np.asarray([x, y, yaw, width, length], dtype=np.float64)
        if not np.isfinite(values).all() or float(width) <= 0.0 or float(length) <= 0.0:
            raise NuPlanCausalSourceError(
                "static object pose and dimensions must be finite and positive"
            )
        row = np.array(
            [x, y, math.cos(yaw), math.sin(yaw), width, length, *_STATIC_OBJECT_TYPES[name]],
            dtype=np.float32,
        )
        encoded.append((float(np.linalg.norm(row[:2] - ego_xy)), bytes(track_token), row))
    encoded.sort(key=lambda item: (item[0], item[1]))
    result = np.zeros((5, 10), dtype=np.float32)
    for index, (_, _, row) in enumerate(encoded[:5]):
        result[index] = row
    return result
~~~

In _load_nuplan_batch, after current = lidar_rows[-1], add:

~~~python
static_objects = _load_static_objects(
    db,
    token,
    np.asarray(current[2:4], dtype=np.float64),
)
~~~

Assign batch.static_objects = static_objects before return. In
materialize_nuplan_decision replace the zero array with:

~~~python
"static_objects": batch.static_objects,
~~~

- [ ] **Step 4: Extend the real-mini assertion and run GREEN**

Add:

~~~python
assert np.any(materialized.dp_input["static_objects"] != 0.0)
assert materialized.dp_input["static_objects"].shape == (5, 10)
~~~

Run:

~~~powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m pytest -q camp_core\tests\test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core\tests\test_diffusion_planner_v17_causal_materializer.py
~~~

Expected: all unit tests pass; the real-mini test skips locally when
NUPLAN_DATA_ROOT is unset.

- [ ] **Step 5: Verify and commit Task 1**

~~~powershell
C:\Users\lenovo\anaconda3\python.exe -m py_compile camp_core\camp_core\integrations\nuplan_causal_adapter.py
git diff --check
git add -- camp_core/camp_core/integrations/nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py
git commit -m "fix: materialize real nuPlan static objects"
~~~

Expected: checks exit 0 and only the two listed files are committed.

---

### Task 2: Same-call neighbor predictions and unknown-signal mask

**Files:**
- Modify: scripts/integrations/run_diffusion_planner_dp_camp_v18.py:35-135
- Test: camp_core/tests/test_diffusion_planner_v18_orchestrator.py

**Interfaces:**
- Consumes: validated causal DP input and existing fixed-DP context.
- Produces: sample_fixed_dp_sources(...) -> tuple[np.ndarray, np.ndarray, np.ndarray] for candidates [8,80,4], neighbor predictions [8,32,80,4], and valid mask [32]; candidate_signal_source_available_mask(...) -> [8] bool.

- [ ] **Step 1: Write failing paired-prediction and signal tests**

~~~python
def test_same_calls_return_paired_ego_and_first_32_neighbors() -> None:
    torch = pytest.importorskip("torch")
    module = _orchestrator()

    class Decoder:
        _guidance_fn = "original"
        _guidance_scale = 9.0

    class Model:
        decoder = Decoder()

        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, _data):
            prediction = torch.zeros((1, 321, 80, 4), dtype=torch.float32)
            prediction[:, :, :, 0] = self.calls
            prediction[:, :, :, 1] = torch.arange(321).reshape(1, 321, 1)
            self.calls += 1
            return None, {"prediction": prediction}

    model = Model()
    context = {
        "torch": torch,
        "device": torch.device("cpu"),
        "model": model,
        "config": type(
            "Config",
            (),
            {
                "predicted_neighbor_num": 320,
                "future_len": 80,
                "observation_normalizer": staticmethod(lambda value: value),
            },
        )(),
        "heading_to_cos_sin": lambda value: value,
        "make_initial_latent": lambda batch, agents, horizon, device, scale: torch.zeros(
            (batch, agents, horizon, 4), device=device
        ),
    }
    data = _causal_input()
    data["neighbor_agents_past"][:3, 0, 0] = 1.0

    candidates, neighbors, valid = module.sample_fixed_dp_sources(data, context)

    assert model.calls == 8
    assert candidates.shape == (8, 80, 4)
    assert neighbors.shape == (8, 32, 80, 4)
    np.testing.assert_array_equal(candidates[:, 0, 0], np.arange(8))
    np.testing.assert_array_equal(neighbors[0, :, 0, 1], np.arange(1, 33))
    np.testing.assert_array_equal(valid[:3], np.ones(3, dtype=bool))
    assert not valid[3:].any()
    assert model.decoder._guidance_fn == "original"
    assert model.decoder._guidance_scale == 9.0


def test_white_signal_mask_is_fail_closed_only_when_reachable() -> None:
    module = _orchestrator()
    candidates = np.zeros((2, 80, 4), dtype=np.float32)
    candidates[:, :, 2] = 1.0
    candidates[0, :, 0] = np.linspace(0.0, 20.0, 80)
    candidates[1, :, 0] = np.linspace(0.0, 2.0, 80)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :, 0] = np.linspace(10.0, 15.0, 20)
    route[0, :, 2] = 1.0
    route[0, :, 11] = 1.0

    available = module.candidate_signal_source_available_mask(candidates, route)

    np.testing.assert_array_equal(available, [False, True])
~~~

- [ ] **Step 2: Run RED**

~~~powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m pytest -q camp_core\tests\test_diffusion_planner_v18_orchestrator.py -k "same_calls or white_signal"
~~~

Expected: missing sample_fixed_dp_sources and
candidate_signal_source_available_mask.

- [ ] **Step 3: Implement paired full prediction capture**

Replace sample_fixed_dp_candidates with:

~~~python
def sample_fixed_dp_sources(
    data: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    noise_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw_neighbors = np.asarray(data["neighbor_agents_past"])
    neighbor_valid_mask = np.any(np.abs(raw_neighbors) > 1e-8, axis=(1, 2))
    arrays = prepare_causal_arrays(data)
    torch = context["torch"]
    device = context["device"]
    tensors = {
        key: torch.as_tensor(value).unsqueeze(0).to(device)
        for key, value in arrays.items()
    }
    tensors["ego_agent_past"] = context["heading_to_cos_sin"](tensors["ego_agent_past"])
    tensors["goal_pose"] = context["heading_to_cos_sin"](tensors["goal_pose"])
    normalized = context["config"].observation_normalizer(tensors)
    normalized["delay"] = torch.zeros(
        normalized["ego_current_state"].shape[0],
        dtype=torch.float32,
        device=device,
    )
    model = context["model"]
    original_fn = model.decoder._guidance_fn
    original_scale = model.decoder._guidance_scale
    model.decoder._guidance_fn = None
    model.decoder._guidance_scale = 0.5

    def draw(scale: float, count: int) -> np.ndarray:
        results = []
        for _ in range(count):
            normalized["sampled_trajectories"] = context["make_initial_latent"](
                1,
                1 + context["config"].predicted_neighbor_num,
                context["config"].future_len,
                device,
                scale,
            )
            _, output = model(normalized)
            prediction = output["prediction"]
            if tuple(prediction.shape) != (1, 321, 80, 4):
                raise ValueError("fixed DP full prediction must have shape [1,321,80,4]")
            value = prediction[0, :33].detach().cpu().numpy().astype(np.float32)
            if not np.isfinite(value).all():
                raise ValueError("fixed DP full prediction must be finite")
            results.append(value)
        return np.stack(results)

    try:
        full = np.concatenate([draw(0.0, 1), draw(noise_scale, 7)], axis=0)
    finally:
        model.decoder._guidance_fn = original_fn
        model.decoder._guidance_scale = original_scale
    candidates = np.ascontiguousarray(full[:, 0], dtype=np.float32)
    neighbors = np.ascontiguousarray(full[:, 1:33], dtype=np.float32)
    return candidates, neighbors, neighbor_valid_mask.astype(bool, copy=False)
~~~

Delete the now-unused combine_candidates function and
test_combine_candidates_requires_exact_k8_shape; the full-prediction shape and
finiteness checks replace that narrower helper.

Change _load_context to add the existing fixed-DP helper:

~~~python
context = load_fixed_dp_export_context(
    dp_repo=dp_repo,
    checkpoint=checkpoint,
    args_json=args_json,
    device=device,
)
from rlvr.closed_loop.batched_rollout import make_initial_latent

context["make_initial_latent"] = make_initial_latent
return context
~~~

- [ ] **Step 4: Implement exact unknown-signal masking**

~~~python
_WHITE_CHANNEL = 11
_SIGNAL_PROXIMITY_M = 3.0
_SIGNAL_HEADING_THRESHOLD = 0.5
_MOVING_THRESHOLD_MPS = 0.5
_TARGET_DT_S = 0.1


def candidate_signal_source_available_mask(
    candidates: np.ndarray,
    route_lanes: np.ndarray,
) -> np.ndarray:
    trajectories = np.array(candidates, dtype=np.float64, copy=True)
    route = np.asarray(route_lanes, dtype=np.float64)
    white = route[
        (route[..., _WHITE_CHANNEL] > 0.5)
        & (np.linalg.norm(route[..., :2], axis=-1) > 0.1)
    ]
    if white.size == 0:
        return np.ones(trajectories.shape[0], dtype=bool)
    white_xy = white[:, :2]
    white_direction = white[:, 2:4]
    white_direction /= np.maximum(
        np.linalg.norm(white_direction, axis=1, keepdims=True), 1e-6
    )
    heading = trajectories[:, :, 2:4].copy()
    heading /= np.maximum(np.linalg.norm(heading, axis=2, keepdims=True), 1e-6)
    distance = np.linalg.norm(
        trajectories[:, :, None, :2] - white_xy[None, None, :, :],
        axis=3,
    )
    aligned = (
        np.einsum("kti,ri->ktr", heading, white_direction)
        > _SIGNAL_HEADING_THRESHOLD
    )
    speed = (
        np.linalg.norm(np.diff(trajectories[:, :, :2], axis=1), axis=2)
        / _TARGET_DT_S
    )
    speed = np.concatenate([speed, speed[:, -1:]], axis=1)
    reaches = ((distance < _SIGNAL_PROXIMITY_M) & aligned).any(axis=2)
    reaches &= speed > _MOVING_THRESHOLD_MPS
    return ~reaches.any(axis=1)
~~~

- [ ] **Step 5: Run GREEN and commit Task 2**

~~~powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m pytest -q camp_core\tests\test_diffusion_planner_v18_orchestrator.py
C:\Users\lenovo\anaconda3\python.exe -m py_compile scripts\integrations\run_diffusion_planner_dp_camp_v18.py
git diff --check
git add -- scripts/integrations/run_diffusion_planner_dp_camp_v18.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py
git commit -m "feat: export same-call nuPlan neighbor predictions"
~~~

Expected: all orchestrator tests pass and only the two listed files are
committed.

---

### Task 3: Refreshed manifest and immutable v2 provenance

**Files:**
- Modify: scripts/integrations/run_diffusion_planner_dp_camp_v18.py:120-280
- Test: camp_core/tests/test_diffusion_planner_v18_orchestrator.py

**Interfaces:**
- Consumes: immutable v1 manifest plus repaired materialize_nuplan_decision.
- Produces: refresh_manifest(args) -> dict[str, Any], a v2 JSONL manifest, and
  v2 NPZ/records hashes.

- [ ] **Step 1: Write failing manifest-refresh test**

~~~python
def test_refresh_manifest_preserves_identity_and_replaces_causal_provenance(
    tmp_path, monkeypatch
) -> None:
    module = _orchestrator()
    old = tmp_path / "old.jsonl"
    row = {
        "split": "train",
        "log_token": "log",
        "scene_token": "scene",
        "decision_token": "decision",
        "db_path": "db",
        "map_path": "map",
        "causal_input_sha256": "old",
    }
    old.write_text(json.dumps(row) + "\n", encoding="utf-8")
    output = tmp_path / "new.jsonl"
    data = _causal_input()
    data["static_objects"][0, :6] = [1.0, 0.0, 1.0, 0.0, 1.0, 2.0]
    data["neighbor_agents_past"][:3, 0, 0] = 1.0
    monkeypatch.setattr(
        module,
        "materialize_nuplan_decision",
        lambda *_args: type("Result", (), {"dp_input": data})(),
    )
    args = type(
        "Args",
        (),
        {
            "manifest": old,
            "expected_manifest_sha256": module._sha256(old),
            "refresh_manifest_output": output,
        },
    )()

    report = module.refresh_manifest(args)
    refreshed = json.loads(output.read_text(encoding="utf-8"))

    assert report["record_count"] == 1
    assert refreshed["split"] == "train"
    assert refreshed["scene_token"] == "scene"
    assert refreshed["causal_input_sha256"] != "old"
    assert refreshed["causal_source_schema_version"] == module.CAUSAL_SOURCE_SCHEMA_VERSION
    assert refreshed["parent_manifest_sha256"] == args.expected_manifest_sha256
    assert refreshed["static_object_count"] == 1
    assert refreshed["neighbor_valid_count"] == 3
    with pytest.raises(FileExistsError):
        module.refresh_manifest(args)
~~~

- [ ] **Step 2: Run RED**

~~~powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m pytest -q camp_core\tests\test_diffusion_planner_v18_orchestrator.py -k refresh_manifest
~~~

Expected: missing refresh_manifest or CAUSAL_SOURCE_SCHEMA_VERSION.

- [ ] **Step 3: Implement atomic manifest refresh**

~~~python
CAUSAL_SOURCE_SCHEMA_VERSION = "dp_camp_v18_nuplan_causal_source_v2"


def _nonzero_row_count(array: np.ndarray) -> int:
    values = np.asarray(array)
    axes = tuple(range(1, values.ndim))
    return int(np.count_nonzero(np.any(np.abs(values) > 1e-8, axis=axes)))


def refresh_manifest(args: argparse.Namespace) -> dict[str, Any]:
    rows = _read_manifest(args.manifest, args.expected_manifest_sha256)
    output = args.refresh_manifest_output
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            for row in rows:
                materialized = materialize_nuplan_decision(
                    row["db_path"], row["map_path"], row["decision_token"]
                )
                refreshed = dict(row)
                refreshed.update(
                    {
                        "causal_input_sha256": causal_input_sha256(materialized.dp_input),
                        "causal_source_schema_version": CAUSAL_SOURCE_SCHEMA_VERSION,
                        "parent_manifest_sha256": args.expected_manifest_sha256,
                        "static_object_count": _nonzero_row_count(
                            materialized.dp_input["static_objects"]
                        ),
                        "neighbor_valid_count": _nonzero_row_count(
                            materialized.dp_input["neighbor_agents_past"]
                        ),
                    }
                )
                stream.write(json.dumps(refreshed, sort_keys=True) + "\n")
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "schema_version": CAUSAL_SOURCE_SCHEMA_VERSION,
        "parent_manifest": str(args.manifest),
        "parent_manifest_sha256": args.expected_manifest_sha256,
        "refreshed_manifest": str(output),
        "refreshed_manifest_sha256": _sha256(output),
        "record_count": len(rows),
        "candidate_generation_executed": False,
    }
~~~

Add --refresh_manifest_output to parse_args. At the start of run_manifest:

~~~python
if args.refresh_manifest_output is not None:
    if args.execute:
        raise ValueError(
            "manifest refresh and candidate execution are mutually exclusive"
        )
    return refresh_manifest(args)
~~~

Before candidate execution:

~~~python
if any(
    row.get("causal_source_schema_version") != CAUSAL_SOURCE_SCHEMA_VERSION
    for row in selected
):
    raise ValueError("candidate execution requires the refreshed v2 causal manifest")
~~~

- [ ] **Step 4: Extend NPZ and records provenance**

Replace sampling with:

~~~python
candidates, neighbor_predictions, neighbor_valid_mask = sample_fixed_dp_sources(
    materialized.dp_input, context, noise_scale=args.noise_scale
)
signal_available = candidate_signal_source_available_mask(
    candidates, materialized.dp_input["route_lanes"]
)
~~~

Add NPZ fields:

~~~python
neighbor_prediction_tensor=neighbor_predictions,
neighbor_valid_mask=neighbor_valid_mask,
candidate_signal_source_available_mask=signal_available,
eligible_for_canonical_14d=np.array(bool(signal_available.all())),
causal_source_schema_version=np.array(CAUSAL_SOURCE_SCHEMA_VERSION),
~~~

Add JSONL fields:

~~~python
"causal_source_schema_version": CAUSAL_SOURCE_SCHEMA_VERSION,
"neighbor_prediction_tensor_sha256": _array_sha256(neighbor_predictions),
"neighbor_valid_mask_sha256": _array_sha256(neighbor_valid_mask),
"candidate_signal_source_available_mask_sha256": _array_sha256(signal_available),
"neighbor_valid_count": int(neighbor_valid_mask.sum()),
"signal_source_available_count": int(signal_available.sum()),
"eligible_for_canonical_14d": bool(signal_available.all()),
"physical_feasibility_mask_materialized": False,
~~~

Change output schema to dp_camp_v18_causal_fixed_dp_export_v2.

- [ ] **Step 5: Add one-record v2 output test**

Add a run_manifest test that monkeypatches subprocess.run, _load_context,
materialize_nuplan_decision, and sample_fixed_dp_sources. Use a reachable white
route and exact fake arrays, then assert:

~~~python
with np.load(output_npz, allow_pickle=False) as payload:
    assert set(payload.files) == {
        "candidate_tensor",
        "neighbor_prediction_tensor",
        "neighbor_valid_mask",
        "candidate_signal_source_available_mask",
        "eligible_for_canonical_14d",
        "causal_input_sha256",
        "causal_source_schema_version",
        "dp_top1_index",
        "candidate_count",
    }
    assert payload["neighbor_prediction_tensor"].shape == (8, 32, 80, 4)
    assert payload["neighbor_valid_mask"].shape == (32,)
    assert payload["candidate_signal_source_available_mask"].shape == (8,)
    assert not bool(payload["eligible_for_canonical_14d"])
record = json.loads((args.output_dir / "records.jsonl").read_text().strip())
assert record["physical_feasibility_mask_materialized"] is False
assert record["eligible_for_canonical_14d"] is False
~~~

Expected: first run passes; a second call with the same output directory raises
FileExistsError.

- [ ] **Step 6: Run GREEN and commit Task 3**

~~~powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m pytest -q camp_core\tests\test_diffusion_planner_v18_orchestrator.py camp_core\tests\test_diffusion_planner_v18_nuplan_causal_adapter.py
C:\Users\lenovo\anaconda3\python.exe -m py_compile scripts\integrations\run_diffusion_planner_dp_camp_v18.py
git diff --check
git add -- scripts/integrations/run_diffusion_planner_dp_camp_v18.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py
git commit -m "feat: freeze v18 causal source provenance"
~~~

Expected: focused tests pass and no candidate generation occurs.

---

### Task 4: Three-end verification and Gate 14 evidence

**Files:**
- Modify: docs/diffusion_planner_v18_iteration_audit.md
- Modify: docs/diffusion_planner_current_status.md
- External artifact path is assigned by
  `artifact="/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_atom_source_remediation_implementation_$(TZ=Asia/Shanghai date +%Y%m%dT%H%M%SCST)"`.

**Interfaces:**
- Consumes: Tasks 1-3 commits and live local/GitHub/AutoDL state.
- Produces: verified implementation artifact, Gate 14 EOF, and identical CAMP heads; no new manifest or candidate execution yet.

- [ ] **Step 1: Run complete local causal suite**

~~~powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m py_compile camp_core\camp_core\integrations\nuplan_causal_adapter.py camp_core\camp_core\integrations\diffusion_planner_causal_atoms.py scripts\integrations\run_diffusion_planner_dp_camp_v18.py
C:\Users\lenovo\anaconda3\python.exe -m pytest -q camp_core\tests\test_diffusion_planner_v17_causal_materializer.py camp_core\tests\test_diffusion_planner_v17_causal_atom_availability.py camp_core\tests\test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core\tests\test_diffusion_planner_v18_orchestrator.py
git diff --check
~~~

Expected: checks exit 0; all available tests pass, with only real-data tests
allowed to skip locally.

- [ ] **Step 2: Push implementation commits and fast-forward AutoDL**

Run git push origin main. On AutoDL, source /etc/network_turbo, require
tracked-clean CAMP/DP, run git pull --ff-only origin main, and assert
CAMP/GitHub heads match while DP remains fixed.

- [ ] **Step 3: Run real AutoDL causal suite**

~~~bash
cd /root/autodl-tmp/camp_core
NUPLAN_DATA_ROOT=/root/autodl-tmp/nuplan/dataset \
PYTHONPATH=/root/autodl-tmp/camp_v18_shapely:/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python -m pytest -q \
camp_core/tests/test_diffusion_planner_v17_causal_materializer.py \
camp_core/tests/test_diffusion_planner_v17_causal_atom_availability.py \
camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py \
camp_core/tests/test_diffusion_planner_v18_orchestrator.py
~~~

Expected: all tests, including the real-mini static assertion, pass; no model is
invoked.

- [ ] **Step 4: Build and verify implementation artifact**

Create the timestamped artifact with exactly:

- COMMAND: JSON array of py_compile and pytest commands;
- HEADS: local/GitHub/AutoDL CAMP head, fixed DP head, tracked status;
- result.json: schema dp_camp_v18_nuplan_causal_atom_source_remediation_implementation_v1, test counts, changed files, model_invocations=0, candidate_generation=false, atom_materialization=false, holdout_label_values_accessed=false;
- result.md, stdout.txt, stderr.txt, run.exit;
- SHA256SUMS and ROOT_SHA256SUMS=sha256(SHA256SUMS).

Run sha256sum -c SHA256SUMS. Expected: every entry OK, empty stderr, run.exit=0.
After verification, assign
`root_sha=$(cut -d' ' -f1 "$artifact/ROOT_SHA256SUMS")` and print both
variables before editing the audit.

- [ ] **Step 5: Append Gate 14 and set exact next EOF**

Append evidence without rewriting history:

~~~text
current_v18_status=v18_nuplan_mini_causal_atom_source_remediation_implementation_passed
current_v18_artifact_scope=nuplan_mini_causal_atom_source_remediation_test_driven_implementation
current_v18_artifact=$artifact
current_v18_artifact_root_sha256=$root_sha
next_work_target=v18_nuplan_mini_refreshed_causal_manifest_and_single_record_source_smoke_preflight_only
~~~

Use apply_patch with the literal values printed for `$artifact` and
`$root_sha`; do not write the dollar-sign forms into the docs. State that
physical feasibility/atoms/labels remain unmaterialized and the old candidate
root remains immutable.

- [ ] **Step 6: Verify, commit, push, sync, and re-read EOF**

~~~powershell
git diff --check
git add -- docs/diffusion_planner_v18_iteration_audit.md docs/diffusion_planner_current_status.md
git commit -m "docs: record v18 causal source remediation"
git push origin main
~~~

Fast-forward AutoDL, assert all three CAMP heads match, fixed DP remains clean,
and re-read both EOFs. Expected next target:
v18_nuplan_mini_refreshed_causal_manifest_and_single_record_source_smoke_preflight_only.

---

## Completion boundary

This plan is complete only when Gate 14 is verified and synchronized. It does
not authorize manifest refresh execution, a real model call, candidate
regeneration, physical feasibility/atom/label materialization, training,
holdout access, evaluation, or any claim. The persistent v18 goal remains
active and continues from the Gate 14 EOF.
