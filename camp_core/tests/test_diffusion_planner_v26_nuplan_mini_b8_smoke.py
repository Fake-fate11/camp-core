from __future__ import annotations

import importlib.util
import hashlib
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _module():
    path = ROOT / "scripts/integrations/run_diffusion_planner_v26_nuplan_mini_b8_smoke.py"
    spec = importlib.util.spec_from_file_location("v26_nuplan_mini_b8_smoke", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_smoke_parser_requires_only_the_active_mode_inputs(tmp_path: Path) -> None:
    module = _module()
    adapter = module.parse_args(
        [
            "--mode",
            "adapter",
            "--data-root",
            str(tmp_path / "dataset"),
            "--db-file",
            str(tmp_path / "mini.db"),
            "--output-root",
            str(tmp_path / "adapter"),
        ]
    )
    assert adapter.mode == "adapter"
    assert adapter.fixed_dp_repo is None
    assert adapter.maps_root is None


def test_adapter_parser_accepts_a_frozen_three_city_source_record_binding(tmp_path: Path) -> None:
    module = _module()
    adapter = module.parse_args(
        [
            "--mode",
            "adapter",
            "--data-root",
            str(tmp_path / "dataset"),
            "--maps-root",
            str(tmp_path / "maps"),
            "--db-file",
            str(tmp_path / "boston.db"),
            "--source-manifest",
            str(tmp_path / "academic_split.json"),
            "--source-record-id",
            "boston:db:scene",
            "--output-root",
            str(tmp_path / "adapter"),
        ]
    )
    assert adapter.source_record_id == "boston:db:scene"
    assert adapter.maps_root == tmp_path / "maps"


def test_same_pool_selector_tie_is_deterministic_without_row_mutation() -> None:
    module = _module()
    scores = np.array([3.0, 1.0, 1.0, 2.0, 9.0, 8.0, 7.0, 6.0])
    mask = np.array([True, True, True, False, False, False, False, False])
    rows = [f"row-{index}" for index in range(8)]
    before_scores = scores.copy()
    before_mask = mask.copy()

    receipt = module._select(scores, mask, rows)

    assert receipt == {
        "status": "ok",
        "selected_index": 1,
        "selected_row_sha256": "row-1",
        "candidate_pool_sha256": None,
        "mask_count": 3,
        "margin": 0.0,
        "tie_indices": [1, 2],
    }
    assert np.array_equal(scores, before_scores)
    assert np.array_equal(mask, before_mask)


def test_map_identity_uses_the_verified_official_archive_layout(tmp_path: Path) -> None:
    module = _module()
    map_path = tmp_path / "maps/us-nv-las-vegas-strip/9.15.1915/map.gpkg"
    map_path.parent.mkdir(parents=True)
    map_path.write_bytes(b"official-map")

    assert module._map_path(
        tmp_path, "las_vegas", "us-nv-las-vegas-strip"
    ) == map_path


def test_source_identity_binds_authoritative_db_route_not_expanded_runtime_route(
    tmp_path: Path,
) -> None:
    module = _module()
    database = tmp_path / "city.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE log (token BLOB, location TEXT, map_version TEXT)")
        connection.execute("CREATE TABLE lidar_pc (token BLOB, scene_token BLOB)")
        connection.execute("CREATE TABLE scene (token BLOB, roadblock_ids TEXT)")
        connection.execute(
            "INSERT INTO log VALUES (?, ?, ?)",
            (bytes.fromhex("01"), "us-ma-boston", "9.12.1817"),
        )
        connection.execute(
            "INSERT INTO lidar_pc VALUES (?, ?)",
            (bytes.fromhex("02"), bytes.fromhex("03")),
        )
        connection.execute(
            "INSERT INTO scene VALUES (?, ?)",
            (bytes.fromhex("03"), "raw-roadblock-chain"),
        )
    map_path = tmp_path / "maps/9.12.1817/revision/map.gpkg"
    map_path.parent.mkdir(parents=True)
    map_path.write_bytes(b"official-map")

    scenario = type("Scenario", (), {"token": "02"})()
    initialization = type(
        "Initialization", (), {"route_roadblock_ids": ("runtime", "expanded")}
    )()
    source, _resolved_map, runtime_assets = module._source_identity(
        data_root=tmp_path,
        db_path=database,
        scenario=scenario,
        initialization=initialization,
        maps_root=tmp_path / "maps",
    )

    source_hash = hashlib.sha256(b"raw-roadblock-chain").hexdigest()
    runtime_hash = hashlib.sha256(b"runtime\0expanded").hexdigest()
    assert source["mission_route_roadblock_chain_sha256"] == source_hash
    assert source["corridor_id"] == f"us-ma-boston:{source_hash[:20]}"
    assert runtime_assets["source_route_roadblock_chain_sha256"] == source_hash
    assert runtime_assets["runtime_route_roadblock_chain_sha256"] == runtime_hash
    assert source_hash != runtime_hash


def _source_identity() -> dict[str, object]:
    digest = lambda text: hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "record_id": "mini:log:scenario",
        "official_split": "mini",
        "log_token": "log",
        "scenario_token": "scenario",
        "scene_token": "scene",
        "state_token": "state",
        "mission_route_roadblock_chain_sha256": digest("route"),
        "corridor_id": "corridor",
        "geometry_clone_group_sha256": digest("geometry"),
        "city": "las_vegas",
        "map_family": "us-nv-las-vegas-strip",
        "source_db_sha256": digest("db"),
        "map_sha256": digest("map"),
        "event_strata": ["scenario_type:source"],
    }


def test_official_empty_signal_source_maps_to_typed_missing_atom_authority() -> None:
    module = _module()
    authority = module._build_v26_no_signal_authority(
        source=_source_identity(),
        route_lanes=np.ones((4, 3, 2), dtype=np.float32),
        traffic_light_data=[],
        decision_time_s=12.5,
    )

    assert authority["source_state"] == "not_applicable"
    assert authority["red_light_endpoint_status"] == "missing_or_inapplicable"
    assert authority["typed_missing_atoms"] == [
        "planned_red_light_cost",
        "red_stopping_margin_cost",
    ]
    assert authority["causal_signal_atom_input"]["applicable"] is False
    assert authority["causal_signal_atom_input"]["current_phase"] == "none"


def test_signal_adapter_rejects_unknown_or_unmapped_signal_source_without_default() -> None:
    module = _module()
    args = {
        "source": _source_identity(),
        "route_lanes": np.ones((4, 3, 2), dtype=np.float32),
        "decision_time_s": 12.5,
    }
    with pytest.raises(ValueError, match="explicit list"):
        module._build_v26_no_signal_authority(traffic_light_data=None, **args)
    with pytest.raises(ValueError, match="stop-line adapter"):
        module._build_v26_no_signal_authority(traffic_light_data=[object()], **args)


def test_inapplicable_atom_mask_excludes_only_legal_zero_values_without_weight_change() -> None:
    module = _module()
    atoms = np.ones((8, 14), dtype=np.float64)
    atoms[:, [10, 12]] = 0.0
    applicable = np.ones((8, 14), dtype=bool)
    applicable[:, [10, 12]] = False
    weights = np.zeros(14, dtype=np.float64)
    weights[10] = 1.0

    _normalized, scores = module._score_applicable_atoms(
        atoms, np.ones(14), weights, applicable
    )

    assert np.array_equal(scores, np.zeros(8))
    bad = atoms.copy()
    bad[:, 10] = 1.0
    with pytest.raises(ValueError, match="exact legal zero"):
        module._score_applicable_atoms(bad, np.ones(14), weights, applicable)


def test_v26_mini_smoke_does_not_reference_legacy_high_level_runner_or_no_signal_builder() -> None:
    source = (
        ROOT / "scripts/integrations/run_diffusion_planner_v26_nuplan_mini_b8_smoke.py"
    ).read_text(encoding="utf-8")
    assert "_build_no_signal_chain" not in source
    assert "run_diffusion_planner_v25" not in source


def test_pre_forward_status_receipt_has_zero_execution_counts() -> None:
    module = _module()
    assert module._status("running", "scenario_builder") == {
        "schema": module.SCHEMA,
        "status": "running",
        "reason": "scenario_builder",
        "model_calls": 0,
        "dp_calls": 0,
        "gpu_calls": 0,
    }


def test_completed_smoke_status_records_the_single_gpu_invocation() -> None:
    module = _module()
    assert module._completed_smoke_status(1) == {
        "schema": module.SCHEMA,
        "status": "complete",
        "reason": "same_ego_b8",
        "model_calls": 1,
        "dp_calls": 1,
        "gpu_calls": 1,
    }
