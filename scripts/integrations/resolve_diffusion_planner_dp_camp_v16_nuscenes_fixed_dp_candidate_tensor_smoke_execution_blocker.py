#!/usr/bin/env python3
"""Resolve the v16 nuScenes fixed-DP smoke execution blocker up to retry preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_resolution_v1"
SOURCE_BLOCKER_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocked"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_resolution_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_resolution_preflight_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_resolution_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_only"
REPORT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_resolution.json"
REPORT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_resolution.md"

NUSCENES_MINI_TABLES = (
    "attribute.json",
    "calibrated_sensor.json",
    "category.json",
    "ego_pose.json",
    "instance.json",
    "log.json",
    "map.json",
    "sample.json",
    "sample_annotation.json",
    "sample_data.json",
    "scene.json",
    "sensor.json",
    "visibility.json",
)
NUSCENES_MAP_EXPANSION_JSONS = (
    "boston-seaport.json",
    "singapore-hollandvillage.json",
    "singapore-onenorth.json",
    "singapore-queenstown.json",
)
DP_INPUT_SCHEMA = {
    "ego_agent_future": ((80, 3), "float32"),
    "ego_agent_past": ((31, 3), "float32"),
    "ego_current_state": ((10,), "float32"),
    "ego_shape": ((3,), "float32"),
    "goal_pose": ((3,), "float32"),
    "lanes": ((140, 20, 33), "float32"),
    "lanes_has_speed_limit": ((140, 1), "bool"),
    "lanes_speed_limit": ((140, 1), "float32"),
    "line_strings": ((60, 20, 4), "float32"),
    "neighbor_agents_future": ((32, 80, 3), "float32"),
    "neighbor_agents_past": ((32, 31, 11), "float32"),
    "polygons": ((10, 40, 3), "float32"),
    "route_lanes": ((25, 20, 33), "float32"),
    "route_lanes_has_speed_limit": ((25, 1), "bool"),
    "route_lanes_speed_limit": ((25, 1), "float32"),
    "static_objects": ((5, 10), "float32"),
    "turn_indicators": ((31,), "int32"),
    "version": ((), "int64"),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_blocker_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_blocker_json", type=Path, required=True)
    parser.add_argument("--source_blocker_sha256s", type=Path, required=True)
    parser.add_argument("--source_blocker_root_sha256s", type=Path, required=True)
    parser.add_argument("--metadata_root", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--probe_npz", type=Path, required=True)
    parser.add_argument("--valid_set_list", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--trajdata_cache_dir", type=Path)
    parser.add_argument("--materialize_probe_from_nuscenes", action="store_true")
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_resolution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    materializer_summary = None
    if args.materialize_probe_from_nuscenes:
        if args.trajdata_cache_dir is None:
            raise SystemExit("--trajdata_cache_dir is required with --materialize_probe_from_nuscenes")
        materializer_summary = materialize_probe_from_nuscenes(
            metadata_root=args.metadata_root,
            trajdata_cache_dir=args.trajdata_cache_dir,
            probe_npz=args.probe_npz,
            valid_set_list=args.valid_set_list,
        )
    report = build_report(
        source_blocker_artifact_dir=args.source_blocker_artifact_dir,
        source_blocker_json=args.source_blocker_json,
        source_blocker_sha256s=args.source_blocker_sha256s,
        source_blocker_root_sha256s=args.source_blocker_root_sha256s,
        metadata_root=args.metadata_root,
        dp_repo=args.dp_repo,
        probe_npz=args.probe_npz,
        valid_set_list=args.valid_set_list,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker_resolution,
        materializer_summary=materializer_summary,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_blocker_artifact_dir: Path,
    source_blocker_json: Path,
    source_blocker_sha256s: Path,
    source_blocker_root_sha256s: Path,
    metadata_root: Path,
    dp_repo: Path,
    probe_npz: Path,
    valid_set_list: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
    materializer_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del output_dir
    source = _read_json(source_blocker_json) if source_blocker_json.is_file() else {}
    source_sha256s = _read_sha256s(source_blocker_sha256s) if source_blocker_sha256s.is_file() else {}
    v16_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md)
    metadata = _metadata_resolution(metadata_root)
    dp_contract = _dp_contract(dp_repo)
    probe = _probe_status(probe_npz, valid_set_list)
    blocker = {
        "artifact": str(source_blocker_artifact_dir),
        "json_sha256": _sha256(source_blocker_json) if source_blocker_json.is_file() else None,
        "sha256s_sha256": _sha256(source_blocker_sha256s) if source_blocker_sha256s.is_file() else None,
        "root_sha256s_sha256": _sha256(source_blocker_root_sha256s)
        if source_blocker_root_sha256s.is_file()
        else None,
        "failed_checks": source.get("final_decision", {}).get("failed_checks", []),
        "failure_class": source.get("final_decision", {}).get("failure_class"),
    }
    checks = [
        _expect("blocker_resolution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_blocker_artifact_exists", source_blocker_artifact_dir.is_dir(), str(source_blocker_artifact_dir), "directory"),
        _expect("source_blocker_status", source.get("status"), SOURCE_BLOCKER_STATUS),
        _expect("source_blocker_dp_head_fixed", source.get("heads", {}).get("dp_head"), FIXED_DP_HEAD),
        _expect(
            "source_blocker_failure_class",
            source.get("final_decision", {}).get("failure_class"),
            "missing_extracted_nuscenes_tables_and_missing_dp_input_materializer",
        ),
        _sha_check("source_blocker_json_sha", source_blocker_json, source_sha256s),
        _contains("audit_authorizes_blocker_resolution", v16_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_blocker_resolution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _expect("metadata_tables_readable_by_trajdata", metadata["tables_readable_by_trajdata"], True),
        _expect("metadata_map_expansion_readable", metadata["map_expansion_jsons_readable"], True),
        _expect("metadata_large_blobs_not_extracted", metadata["extracted_large_blobs"], False),
        _expect("dp_valid_predictor_available", dp_contract["valid_predictor_available"], True),
        _expect("dp_fixture_schema_available", dp_contract["fixture_schema_available"], True),
        _expect("probe_npz_exists", probe["probe_npz_exists"], True),
        _expect("valid_set_list_loadable", probe["valid_set_list_loadable"], True),
        _expect("probe_schema_valid", probe["schema_valid"], True),
    ]
    remaining = []
    if not metadata["tables_readable_by_trajdata"]:
        remaining.append("nuScenes mini metadata tables are not readable from the prepared metadata root")
    if not metadata["map_expansion_jsons_readable"]:
        remaining.append("nuScenes map expansion JSON is not readable from the prepared metadata root")
    if not probe["schema_valid"]:
        remaining.append("DP-format valid_set_list probe NPZ does not satisfy the fixed DP input schema")
    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else AUTHORIZED_CURRENT_WORK,
            "source_blocker": blocker,
            "metadata_resolution": metadata,
            "dp_contract": dp_contract,
            "dp_input_probe": probe,
            "materializer_summary": materializer_summary or {},
            "files_scripts_touched": (
                "scripts/integrations/resolve_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker.py",
                "camp_core/tests/test_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_blocker_resolution.py",
            ),
            "remaining_gaps": remaining,
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else AUTHORIZED_CURRENT_WORK,
                "candidate_generation_retry_allowed": not failed,
                "candidate_generation_executed": False,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
        }
    )


def materialize_probe_from_nuscenes(
    *,
    metadata_root: Path,
    trajdata_cache_dir: Path,
    probe_npz: Path,
    valid_set_list: Path,
) -> dict[str, Any]:
    from camp_core.data_interfaces.nuscenes_trajdata_bridge import (  # type: ignore
        NuscenesDatasetConfig,
        NuscenesTrajdataBridge,
    )

    cfg = NuscenesDatasetConfig(
        data_root=str(metadata_root),
        cache_dir=str(trajdata_cache_dir),
        split="nusc_mini-mini_val",
        batch_size=1,
        num_workers=0,
        shuffle=False,
        pin_memory=False,
        use_vector_map=True,
        history_sec=(3.0, 3.0),
        future_sec=(8.0, 8.0),
        max_neighbor_num=32,
        rebuild_cache=False,
        rebuild_maps=False,
    )
    bridge = NuscenesTrajdataBridge(cfg)
    batch = next(iter(bridge.make_dataloader()))
    data = dp_input_from_agent_batch(batch, metadata_root=metadata_root)
    write_dp_input_probe(probe_npz, valid_set_list, data)
    return {
        "metadata_root": str(metadata_root),
        "trajdata_cache_dir": str(trajdata_cache_dir),
        "probe_npz": str(probe_npz),
        "valid_set_list": str(valid_set_list),
        "dataset_len": len(bridge),
        "fields_materialized": sorted(data),
    }


def dp_input_from_agent_batch(batch: Any, *, metadata_root: Path) -> dict[str, np.ndarray]:
    agent_hist = _as_numpy(batch.agent_hist)[0]
    agent_fut = _as_numpy(batch.agent_fut)[0]
    curr = _as_numpy(batch.curr_agent_state)[0]
    data = example_dp_input()
    data["ego_agent_past"] = _state_to_xyh(agent_hist, 31)
    data["ego_agent_future"] = _state_to_xyh(agent_fut, 80)
    speed = float(np.linalg.norm(curr[2:4])) if curr.shape[0] >= 4 else 0.0
    accel = _longitudinal_accel(curr)
    data["ego_current_state"] = np.array([0.0, 0.0, 1.0, 0.0, speed, 0.0, accel, 0.0, 0.0, 0.0], dtype=np.float32)
    data["goal_pose"] = data["ego_agent_future"][-1].astype(np.float32)
    data["ego_shape"] = _ego_shape(batch)
    data["neighbor_agents_past"], data["neighbor_agents_future"] = _neighbors(batch)
    lanes = _lanes_from_nuscenes_map(batch, metadata_root=metadata_root)
    data["lanes"] = lanes
    data["route_lanes"] = lanes[:25].copy()
    data["line_strings"] = _line_strings_from_lanes(lanes)
    return data


def write_dp_input_probe(probe_npz: Path, valid_set_list: Path, data: dict[str, np.ndarray]) -> None:
    errors = validate_dp_input(data)
    if errors:
        raise ValueError("; ".join(errors))
    probe_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(probe_npz, **data)
    valid_set_list.write_text(json.dumps({"files": [str(probe_npz)]}, indent=2) + "\n", encoding="utf-8")


def example_dp_input() -> dict[str, np.ndarray]:
    data: dict[str, np.ndarray] = {}
    for key, (shape, dtype) in DP_INPUT_SCHEMA.items():
        data[key] = np.zeros(shape, dtype=np.dtype(dtype))
    data["version"] = np.array(1, dtype=np.int64)
    data["ego_shape"] = np.array([2.8, 4.8, 1.9], dtype=np.float32)
    data["ego_current_state"][2] = 1.0
    return data


def validate_dp_input(data: dict[str, np.ndarray]) -> list[str]:
    errors = []
    for key, (shape, dtype) in DP_INPUT_SCHEMA.items():
        if key not in data:
            errors.append(f"missing:{key}")
            continue
        arr = np.asarray(data[key])
        if tuple(arr.shape) != tuple(shape):
            errors.append(f"shape:{key}:{tuple(arr.shape)}!={shape}")
        if arr.dtype != np.dtype(dtype):
            errors.append(f"dtype:{key}:{arr.dtype}!={dtype}")
        if arr.dtype.kind in "fc" and not np.isfinite(arr).all():
            errors.append(f"finite:{key}")
    return errors


def _metadata_resolution(root: Path) -> dict[str, Any]:
    tables = [root / "v1.0-mini" / name for name in NUSCENES_MINI_TABLES]
    map_jsons = [root / "maps" / "expansion" / name for name in NUSCENES_MAP_EXPANSION_JSONS]
    large_blobs = list((root / "samples").glob("*")) if (root / "samples").is_dir() else []
    return {
        "root": str(root),
        "tables_readable_by_trajdata": all(path.is_file() for path in tables),
        "map_expansion_jsons_readable": all(path.is_file() for path in map_jsons),
        "table_files": [str(path) for path in tables],
        "map_expansion_jsons": [str(path) for path in map_jsons],
        "source_paths_used": (
            "/autodl-pub/data/nuScenes/Fulldatasetv1.0/Mini/v1.0-mini.tgz",
            "/autodl-pub/data/nuScenes/Mapexpansion/nuScenes-map-expansion-v1.3.zip",
        ),
        "extracted_large_blobs": bool(large_blobs),
    }


def _dp_contract(dp_repo: Path) -> dict[str, Any]:
    return {
        "repo": str(dp_repo),
        "valid_predictor_available": (dp_repo / "diffusion_planner" / "valid_predictor.py").is_file(),
        "dataset_loader_available": (
            dp_repo / "diffusion_planner" / "diffusion_planner" / "utils" / "dataset.py"
        ).is_file(),
        "fixture_schema_available": (
            dp_repo / "scenario_generation" / "tests" / "test_data" / "fixture_scene.npz"
        ).is_file(),
        "valid_predictor_required_args": (
            "--valid_set_list",
            "--resume_model_path",
            "--args_json_path",
            "--save_predictions_dir",
        ),
    }


def _probe_status(probe_npz: Path, valid_set_list: Path) -> dict[str, Any]:
    probe = {
        "probe_npz": str(probe_npz),
        "probe_npz_exists": probe_npz.is_file(),
        "valid_set_list": str(valid_set_list),
        "valid_set_list_loadable": False,
        "fields_materialized": [],
        "schema_errors": [],
        "schema_valid": False,
        "probe_npz_sha256": _sha256(probe_npz) if probe_npz.is_file() else None,
    }
    if not probe_npz.is_file() or not valid_set_list.is_file():
        return probe
    try:
        files = json.loads(valid_set_list.read_text(encoding="utf-8")).get("files", [])
        probe["valid_set_list_loadable"] = str(probe_npz) in files
        with np.load(probe_npz, allow_pickle=True) as loaded:
            data = {key: loaded[key] for key in loaded.files}
        probe["fields_materialized"] = sorted(data)
        probe["schema_errors"] = validate_dp_input(data)
        probe["schema_valid"] = not probe["schema_errors"]
    except Exception as exc:
        probe["schema_errors"] = [f"{type(exc).__name__}: {exc}"]
    return probe


def _as_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        return value.detach().cpu().numpy()
    if hasattr(value, "cpu"):
        return value.cpu().numpy()
    return np.asarray(value)


def _state_to_xyh(states: np.ndarray, target_len: int) -> np.ndarray:
    states = np.asarray(states, dtype=np.float32)
    xy = states[:, :2]
    if states.shape[1] >= 8:
        heading = np.arctan2(states[:, 6], states[:, 7])
    elif states.shape[1] >= 4:
        heading = np.arctan2(states[:, 3], states[:, 2])
    else:
        heading = np.zeros(states.shape[0], dtype=np.float32)
    return _resample(np.column_stack([xy, heading]).astype(np.float32), target_len)


def _resample(values: np.ndarray, target_len: int) -> np.ndarray:
    if values.shape[0] == target_len:
        return values.astype(np.float32)
    if values.shape[0] == 0:
        return np.zeros((target_len, values.shape[1]), dtype=np.float32)
    src = np.linspace(0.0, 1.0, values.shape[0])
    dst = np.linspace(0.0, 1.0, target_len)
    cols = [np.interp(dst, src, values[:, idx]) for idx in range(values.shape[1])]
    return np.stack(cols, axis=1).astype(np.float32)


def _longitudinal_accel(curr: np.ndarray) -> float:
    if curr.shape[0] < 6:
        return 0.0
    vel = curr[2:4]
    acc = curr[4:6]
    speed = float(np.linalg.norm(vel))
    if speed < 1e-6:
        return 0.0
    return float(np.dot(vel, acc) / speed)


def _ego_shape(batch: Any) -> np.ndarray:
    if hasattr(batch, "agent_hist_extent"):
        extent = _as_numpy(batch.agent_hist_extent)[0, -1]
        length = float(extent[0]) if np.isfinite(extent[0]) else 4.8
        width = float(extent[1]) if np.isfinite(extent[1]) else 1.9
        return np.array([2.8, length, width], dtype=np.float32)
    return np.array([2.8, 4.8, 1.9], dtype=np.float32)


def _neighbors(batch: Any) -> tuple[np.ndarray, np.ndarray]:
    past = np.zeros(DP_INPUT_SCHEMA["neighbor_agents_past"][0], dtype=np.float32)
    future = np.zeros(DP_INPUT_SCHEMA["neighbor_agents_future"][0], dtype=np.float32)
    if not hasattr(batch, "neigh_hist"):
        return past, future
    neigh_hist = _as_numpy(batch.neigh_hist)[0]
    neigh_fut = _as_numpy(batch.neigh_fut)[0] if hasattr(batch, "neigh_fut") else np.zeros((0, 0, 8))
    extents = _as_numpy(batch.neigh_hist_extents)[0] if hasattr(batch, "neigh_hist_extents") else None
    count = min(32, neigh_hist.shape[0])
    for idx in range(count):
        hist = _state_to_xyh(neigh_hist[idx], 31)
        past[idx, :, :2] = hist[:, :2]
        past[idx, :, 2] = np.cos(hist[:, 2])
        past[idx, :, 3] = np.sin(hist[:, 2])
        past[idx, :, 4:6] = _resample(neigh_hist[idx, :, 2:4], 31)
        if extents is not None:
            extent = extents[idx, -1]
            if np.isfinite(extent).all():
                past[idx, :, 6] = float(extent[1])
                past[idx, :, 7] = float(extent[0])
        if idx < neigh_fut.shape[0]:
            future[idx] = _state_to_xyh(neigh_fut[idx], 80)
    return past, future


def _lanes_from_nuscenes_map(batch: Any, *, metadata_root: Path) -> np.ndarray:
    try:
        from nuscenes.map_expansion.map_api import NuScenesMap  # type: ignore
    except Exception:
        return np.zeros(DP_INPUT_SCHEMA["lanes"][0], dtype=np.float32)
    map_name = str(batch.map_names[0]).split(":", 1)[-1]
    curr = _as_numpy(batch.curr_agent_state)[0]
    world_xy = curr[:2]
    world_to_agent = _as_numpy(batch.agents_from_world_tf)[0]
    nusc_map = NuScenesMap(dataroot=str(metadata_root), map_name=map_name)
    records = nusc_map.get_records_in_radius(float(world_xy[0]), float(world_xy[1]), 80.0, ["lane", "lane_connector"])
    tokens = records.get("lane", []) + records.get("lane_connector", [])
    if not tokens:
        return np.zeros(DP_INPUT_SCHEMA["lanes"][0], dtype=np.float32)
    centerlines = nusc_map.discretize_lanes(tokens, 1.0)
    lanes = []
    for token, points in centerlines.items():
        xyh = np.asarray(points, dtype=np.float32)
        if xyh.ndim != 2 or xyh.shape[0] < 2:
            continue
        local_xy = _transform_xy(xyh[:, :2], world_to_agent)
        sample = _resample(local_xy, 20)
        dist = float(np.min(np.linalg.norm(sample[:, :2], axis=1)))
        lanes.append((dist, sample))
    lanes.sort(key=lambda item: item[0])
    out = np.zeros(DP_INPUT_SCHEMA["lanes"][0], dtype=np.float32)
    for idx, (_, xy) in enumerate(lanes[: out.shape[0]]):
        out[idx, :, :2] = xy
        direction = np.gradient(xy, axis=0)
        norm = np.linalg.norm(direction, axis=1, keepdims=True)
        norm[norm < 1e-6] = 1.0
        direction = direction / norm
        out[idx, :, 2:4] = direction
        out[idx, :, 4:6] = direction
    return out


def _transform_xy(xy: np.ndarray, transform: np.ndarray) -> np.ndarray:
    homog = np.column_stack([xy, np.ones(xy.shape[0], dtype=np.float32)])
    return (homog @ transform.T)[:, :2].astype(np.float32)


def _line_strings_from_lanes(lanes: np.ndarray) -> np.ndarray:
    out = np.zeros(DP_INPUT_SCHEMA["line_strings"][0], dtype=np.float32)
    count = min(out.shape[0], lanes.shape[0])
    out[:count, :, :2] = lanes[:count, :, :2]
    return out


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REPORT_JSON_NAME
    md_path = output_dir / REPORT_MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        f"{_sha256(json_path)}  {json_path.name}\n{_sha256(md_path)}  {md_path.name}\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Smoke Execution Blocker Resolution",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Candidate generation retry allowed: `{decision['candidate_generation_retry_allowed']}`",
            f"- Source blocker artifact: `{report['source_blocker']['artifact']}`",
            f"- Probe NPZ: `{report['dp_input_probe']['probe_npz']}`",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _read_sha256s(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        entries[Path(name.strip()).name] = digest
    return entries


def _sha_check(name: str, path: Path, sha256s: dict[str, str]) -> dict[str, Any]:
    expected = sha256s.get(path.name)
    actual = _sha256(path) if path.is_file() else None
    return _check(name, actual == expected, actual, expected)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
