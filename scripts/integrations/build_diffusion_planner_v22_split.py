from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from camp_core.integrations.diffusion_planner_v22_split import (
    build_leakage_groups,
    canonical_json_sha256,
    freeze_split_manifest,
    validate_feature_fields,
    validate_split_manifest,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze the source-only v22 split.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--enumerate-map-json")
    parser.add_argument("--enumerate-map-output", type=Path)
    args = parser.parse_args(argv)
    child = args.enumerate_map_json is not None
    if child != (args.enumerate_map_output is not None):
        parser.error("map child arguments must be provided together")
    if not child and (args.config is None or args.output_dir is None):
        parser.error("--config and --output-dir are required")
    return args


def main(argv: list[str] | None = None) -> dict[str, Any] | None:
    args = parse_args(argv)
    if args.enumerate_map_json is not None:
        records = enumerate_map_routes(json.loads(args.enumerate_map_json))
        _write_json(args.enumerate_map_output, {"routes": records})
        return None
    config = json.loads(args.config.read_text(encoding="utf-8"))
    result = build_split_artifact(
        config,
        args.output_dir,
        command=" ".join([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]),
    )
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return result


def build_split_artifact(
    config: Mapping[str, Any],
    output_dir: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    _validate_config(config)
    output = Path(output_dir)
    staging = output.with_name(output.name + ".tmp")
    if output.exists() or staging.exists():
        raise FileExistsError(f"evidence target already exists: {output}")
    staging.mkdir(parents=True)
    try:
        heads = _verify_heads(config)
        _install_fixed_dp_path(config)
        records = _source_records(config, staging)
        expected_total = config.get("expected_source_route_count")
        if expected_total is not None and len(records) != int(expected_total):
            raise ValueError(
                f"source route count mismatch: {len(records)} != {expected_total}"
            )
        thresholds = config["leakage_thresholds"]
        grouping = build_leakage_groups(
            records,
            overlap_distance_m=float(thresholds["overlap_distance_m"]),
            min_overlap_samples=int(thresholds["min_overlap_samples"]),
            max_heading_delta_deg=float(thresholds["max_heading_delta_deg"]),
        )
        manifest = freeze_split_manifest(
            grouping,
            seed_namespaces=config["seed_namespaces"],
            targets=config["targets"],
        )
        if (
            config.get("materialize_route_assets", False)
            and manifest["status"] == "frozen"
        ):
            _materialize_route_assets(manifest, staging, output)
            manifest.pop("split_freeze_sha256", None)
            manifest["split_freeze_sha256"] = canonical_json_sha256(manifest)
            validate_split_manifest(manifest)
        summary = _summary(config, grouping, manifest)
        _write_json(staging / "source_route_census.json", {"routes": records})
        _write_json(staging / "leakage_groups.json", grouping)
        _write_json(staging / "split_manifest.json", manifest)
        _write_json(staging / "summary.json", summary)
        _write_json(staging / "preregistration_config.json", config)
        (staging / "HEADS").write_text(
            f"camp_source_head={heads['camp']}\nfixed_dp_head={heads['dp']}\n",
            encoding="ascii",
        )
        (staging / "COMMAND").write_text(command + "\n", encoding="utf-8")
        (staging / "stdout.txt").write_text(
            json.dumps(summary, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (staging / "stderr.txt").write_text("", encoding="utf-8")
        (staging / "summary.md").write_text(
            _summary_markdown(summary), encoding="utf-8"
        )
        (staging / "run.exit").write_text("0\n", encoding="ascii")
        root_sha = _seal(staging)
        staging.replace(output)
        return {**summary, "artifact": str(output), "root_sha256": root_sha}
    except Exception as exc:
        camp = _git_head(ROOT)
        dp_repo = Path(str(config.get("fixed_dp_repo", "/missing")))
        dp = _git_head(dp_repo) if dp_repo.is_dir() else "synthetic_fixture"
        failure = {
            "status": "failed",
            "failure_stage": "source_only_split_freeze",
            "failure_reason": str(exc),
            "model_loaded": False,
            "simulator_executed": False,
            "outcomes_read": False,
        }
        _write_json(staging / "failure.json", failure)
        _write_json(staging / "preregistration_config.json", config)
        (staging / "HEADS").write_text(
            f"camp_source_head={camp}\nfixed_dp_head={dp}\n", encoding="ascii"
        )
        (staging / "COMMAND").write_text(command + "\n", encoding="utf-8")
        (staging / "stdout.txt").write_text("", encoding="utf-8")
        (staging / "stderr.txt").write_text(str(exc) + "\n", encoding="utf-8")
        (staging / "summary.md").write_text(
            f"# V22 source-only split freeze failure\n\n{exc}\n", encoding="utf-8"
        )
        (staging / "run.exit").write_text("1\n", encoding="ascii")
        _seal(staging)
        staging.replace(output)
        raise


def enumerate_map_routes(map_config: Mapping[str, Any]) -> list[dict[str, Any]]:
    from camp_core.integrations.diffusion_planner import (
        install_lanelet2_projection_fallback,
    )
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

    map_path = Path(str(map_config["path"]))
    map_sha = _file_sha256(map_path)
    if map_sha != map_config["sha256"]:
        raise ValueError(f"map SHA mismatch: {map_path}")
    install_lanelet2_projection_fallback(map_path)
    builder = LaneletSceneBuilder(str(map_path))
    drivable = sorted(int(value) for value in builder._vehicle_ll_ids)
    traffic_lights = builder.get_traffic_light_groups()
    topology = _topology_complexes(builder, drivable, traffic_lights)
    observed_lanelets = set(int(value) for value in map_config.get("observed_lanelets", []))
    route_sequences = set()
    for start in drivable:
        if start not in builder._ll_by_id:
            continue
        sequence = [start]
        visited = {start}
        length = float(builder._cache[start].arc_length)
        current = builder._ll_by_id[start]
        for _ in range(int(map_config["max_hops"])):
            following = sorted(
                (
                    item
                    for item in builder._routing_graph.following(current)
                    if item.id in builder._cache and item.id not in visited
                ),
                key=lambda item: item.id,
            )
            if not following:
                break
            current = following[0]
            sequence.append(int(current.id))
            visited.add(int(current.id))
            length += float(builder._cache[current.id].arc_length)
            if length >= float(map_config["max_route_length_m"]):
                break
        if length >= float(map_config["min_route_length_m"]) and len(sequence) >= 2:
            route_sequences.add(tuple(sequence))
    if len(route_sequences) != int(map_config["expected_route_count"]):
        raise ValueError(
            f"{map_config['name']} route count changed: {len(route_sequences)}"
        )
    records = []
    for sequence in sorted(route_sequences):
        polyline = _route_polyline(builder, sequence)
        samples, headings, route_length = _sample_polyline(polyline, spacing_m=1.0)
        boundary_ids = sorted(
            {
                int(boundary.id)
                for lanelet_id in sequence
                for boundary in (
                    builder._ll_by_id[lanelet_id].leftBound,
                    builder._ll_by_id[lanelet_id].rightBound,
                )
            }
        )
        complex_name, entry_arm, exit_arm = _route_topology(sequence, topology)
        widths = np.concatenate(
            [
                np.linalg.norm(
                    builder._cache[lanelet_id].interp_left
                    - builder._cache[lanelet_id].interp_right,
                    axis=1,
                )
                for lanelet_id in sequence
            ]
        )
        route_spec = {
            "map_path": str(map_path),
            "lanelet_ids": list(sequence),
            "start_pose": [*samples[0], headings[0]],
            "goal_pose": [*samples[-1], headings[-1]],
            "route_length_m": route_length,
        }
        route_serialization_sha = canonical_json_sha256(route_spec)
        geometry_sha = canonical_json_sha256(
            {"samples": samples, "headings": headings}
        )
        identity = canonical_json_sha256(
            {
                "logical_map_sha256": map_sha,
                "lanelet_ids": list(sequence),
                "source_geometry_sha256": geometry_sha,
                "route_serialization_sha256": route_serialization_sha,
            }
        )
        records.append(
            {
                "record_key": f"{map_config['name']}/{sequence[0]}/{identity[:16]}",
                "identity_sha256": identity,
                "logical_map_sha256": map_sha,
                "logical_map_name": str(map_config["name"]),
                "lanelet_ids": list(sequence),
                "boundary_ids": boundary_ids,
                "centerline_samples_m": samples,
                "centerline_headings_rad": headings,
                "topology_complex": complex_name,
                "entry_arm": entry_arm,
                "exit_arm": exit_arm,
                "source_stratum": {
                    "traffic_light": bool(set(sequence).intersection(traffic_lights)),
                    "branch_intersection": complex_name is not None,
                    "tight_corridor": float(widths.min())
                    <= float(map_config["tight_corridor_width_m"]),
                    "short_progress_opportunity": route_length
                    <= float(map_config["short_progress_opportunity_m"]),
                },
                "holdout_forbidden": bool(set(sequence).intersection(observed_lanelets)),
                "route_spec": route_spec,
                "route_serialization_sha256": route_serialization_sha,
                "source_geometry_sha256": geometry_sha,
                "minimum_source_corridor_width_m": float(widths.min()),
                "source_route_length_m": route_length,
            }
        )
    return records


def _source_records(
    config: Mapping[str, Any], staging: Path
) -> list[dict[str, Any]]:
    if config.get("synthetic_fixture"):
        return [dict(route) for route in config["route_records"]]
    observed = _observed_lanelets(config)
    source_maps = staging / "source_maps"
    source_maps.mkdir()
    records = []
    for map_entry in config["maps"]:
        child_config = {
            **dict(map_entry),
            **dict(config["route_enumeration"]),
            "observed_lanelets": sorted(observed.get(map_entry["name"], set())),
        }
        output = source_maps / f"{map_entry['name']}.json"
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--enumerate-map-json",
                json.dumps(child_config, separators=(",", ":"), sort_keys=True),
                "--enumerate-map-output",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=_child_environment(config),
        )
        records.extend(json.loads(output.read_text(encoding="utf-8"))["routes"])
    return records


def _observed_lanelets(config: Mapping[str, Any]) -> dict[str, set[int]]:
    from scenario_generation.route import Route

    result: dict[str, set[int]] = {}
    for asset in config.get("observed_v21_routes", []):
        path = Path(str(asset["path"]))
        if _file_sha256(path) != asset["sha256"]:
            raise ValueError(f"observed v21 route SHA mismatch: {path}")
        route = Route.load(path)
        if not route.route_lanelet_ids:
            raise ValueError(f"observed v21 route is unresolved: {path}")
        result.setdefault(str(asset["logical_map_name"]), set()).update(
            int(value) for value in route.route_lanelet_ids
        )
    return result


def _topology_complexes(builder, drivable, traffic_lights):
    adjacency: dict[int, set[int]] = {lanelet_id: set() for lanelet_id in drivable}
    complex_seed = set(traffic_lights)
    for lanelet_id in drivable:
        lanelet = builder._ll_by_id[lanelet_id]
        following = {
            int(item.id)
            for item in builder._routing_graph.following(lanelet)
            if item.id in adjacency
        }
        previous = {
            int(item.id)
            for item in builder._routing_graph.previous(lanelet)
            if item.id in adjacency
        }
        adjacency[lanelet_id].update(following | previous)
        if len(following) > 1 or len(previous) > 1:
            complex_seed.add(lanelet_id)
    complex_lanelets = set(complex_seed)
    for lanelet_id in list(complex_seed):
        complex_lanelets.update(adjacency.get(lanelet_id, ()))
    remaining = set(complex_lanelets)
    components = []
    while remaining:
        root = min(remaining)
        stack = [root]
        component = set()
        while stack:
            lanelet_id = stack.pop()
            if lanelet_id in component:
                continue
            component.add(lanelet_id)
            stack.extend(adjacency.get(lanelet_id, set()).intersection(complex_lanelets))
        remaining.difference_update(component)
        components.append(component)
    lanelet_to_complex = {}
    for component in components:
        name = canonical_json_sha256(sorted(component))
        for lanelet_id in component:
            lanelet_to_complex[lanelet_id] = name
    return lanelet_to_complex


def _route_topology(sequence, lanelet_to_complex):
    indices = [index for index, value in enumerate(sequence) if value in lanelet_to_complex]
    if not indices:
        return None, None, None
    first = indices[0]
    complex_name = lanelet_to_complex[sequence[first]]
    same = [
        index
        for index in indices
        if lanelet_to_complex[sequence[index]] == complex_name
    ]
    last = max(same)
    entry = sequence[max(0, first - 1)]
    exit_arm = sequence[min(len(sequence) - 1, last + 1)]
    return complex_name, str(entry), str(exit_arm)


def _route_polyline(builder, sequence) -> np.ndarray:
    points = []
    for lanelet_id in sequence:
        centerline = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        if points and np.linalg.norm(points[-1] - centerline[0]) <= 1e-6:
            centerline = centerline[1:]
        points.extend(centerline)
    result = np.asarray(points, dtype=np.float64)
    if result.shape[0] < 2:
        raise ValueError("route source centerline is empty")
    return result


def _sample_polyline(polyline: np.ndarray, *, spacing_m: float):
    segment = np.linalg.norm(np.diff(polyline, axis=0), axis=1)
    keep = np.concatenate(([True], segment > 1e-9))
    points = polyline[keep]
    segment = np.linalg.norm(np.diff(points, axis=0), axis=1)
    arc = np.concatenate(([0.0], np.cumsum(segment)))
    total = float(arc[-1])
    targets = np.arange(0.0, total, spacing_m)
    if targets.size == 0 or not math.isclose(targets[-1], total):
        targets = np.append(targets, total)
    x = np.interp(targets, arc, points[:, 0])
    y = np.interp(targets, arc, points[:, 1])
    sampled = np.column_stack((x, y))
    diff = np.gradient(sampled, axis=0)
    headings = np.arctan2(diff[:, 1], diff[:, 0])
    return sampled.tolist(), headings.tolist(), total


def _materialize_route_assets(manifest, staging: Path, final_output: Path) -> None:
    from scenario_generation.route import Route

    for split, payload in manifest["splits"].items():
        for route in payload["routes"]:
            spec = route["route_spec"]
            identity = route["identity_sha256"]
            relative = Path("routes") / split / f"{identity}.pkl"
            target = staging / relative
            lanelets = [int(value) for value in spec["lanelet_ids"]]
            value = Route(
                map_path=str(spec["map_path"]),
                start_pose=np.asarray(spec["start_pose"], dtype=np.float32),
                goal_pose=np.asarray(spec["goal_pose"], dtype=np.float32),
                start_lanelet_id=lanelets[0],
                goal_lanelet_id=lanelets[-1],
                route_lanelet_ids=lanelets,
            )
            value.save(target)
            route["route_asset"] = {
                "path": str(final_output / relative),
                "sha256": _file_sha256(target),
            }


def _validate_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "v22_split_preregistration_v1":
        raise ValueError("v22 split config schema mismatch")
    validate_feature_fields(config.get("selector_feature_fields", []))
    if config.get("outcome_fields") not in (None, []):
        raise ValueError("split config must not contain outcome fields")
    if config.get("full36_authorized") is not False:
        raise ValueError("Full36 must remain forbidden")
    if not config.get("synthetic_fixture"):
        if config.get("fixed_dp_head") != FIXED_DP_HEAD:
            raise ValueError("fixed DP HEAD mismatch")
        if len(config.get("maps", [])) != 2:
            raise ValueError("v22 split requires the two fixed logical maps")
        if config.get("targets") != {
            "train": 500,
            "calibration": 30,
            "holdout": 100,
        }:
            raise ValueError("v22 split route targets changed")
        if (
            len(config.get("seed_namespaces", {}).get("calibration", [])) != 3
            or len(config.get("seed_namespaces", {}).get("holdout", [])) != 5
        ):
            raise ValueError("pilot/main seed counts changed")
        if config.get("claim_authorized") is not False:
            raise ValueError("split freeze must not authorize a claim")


def _verify_heads(config: Mapping[str, Any]) -> dict[str, str]:
    camp = _git_head(ROOT)
    if config.get("synthetic_fixture"):
        return {"camp": camp, "dp": "synthetic_fixture"}
    dp_repo = Path(str(config["fixed_dp_repo"]))
    dp = _git_head(dp_repo)
    if dp != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    if _git_dirty(dp_repo):
        raise ValueError("fixed DP tracked worktree is dirty")
    if _git_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    return {"camp": camp, "dp": dp}


def _install_fixed_dp_path(config: Mapping[str, Any]) -> None:
    if config.get("synthetic_fixture"):
        return
    dp_repo = Path(str(config["fixed_dp_repo"]))
    for path in (dp_repo, dp_repo / "diffusion_planner"):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def _child_environment(config: Mapping[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    dp_repo = Path(str(config["fixed_dp_repo"]))
    paths = [str(ROOT / "camp_core"), str(dp_repo), str(dp_repo / "diffusion_planner")]
    current = env.get("PYTHONPATH")
    if current:
        paths.append(current)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def _summary(config, grouping, manifest):
    maps = {}
    for route in grouping["route_records"]:
        name = route.get("logical_map_name", route["logical_map_sha256"])
        maps[name] = maps.get(name, 0) + 1
    return {
        "schema_version": "v22_split_freeze_summary_v1",
        "status": manifest["status"],
        "source_only": True,
        "outcomes_read": False,
        "model_loaded": False,
        "simulator_executed": False,
        "claim_authorized": False,
        "source_route_records": len(grouping["route_records"]),
        "source_routes_by_map": maps,
        "leakage_edge_count": len(grouping["edges"]),
        "route_family_group_count": len(grouping["groups"]),
        "targets": dict(manifest["targets"]),
        "achieved_route_counts": dict(manifest["achieved_route_counts"]),
        "target_reached": dict(manifest["target_reached"]),
        "expected_pair_count": len(manifest["expected_pairs"]),
        "excluded_pre_preregistration_records": len(
            manifest["excluded_pre_preregistration"]
        ),
        "split_freeze_sha256": manifest["split_freeze_sha256"],
        "pilot_seed_count": len(config["seed_namespaces"]["calibration"]),
        "main_seed_count": len(config["seed_namespaces"]["holdout"]),
    }


def _summary_markdown(summary) -> str:
    return (
        "# V22 source-only route-family split freeze\n\n"
        f"- status: `{summary['status']}`\n"
        f"- source routes: `{summary['source_route_records']}`\n"
        f"- route-family groups: `{summary['route_family_group_count']}`\n"
        f"- achieved train/calibration/holdout: `{summary['achieved_route_counts']}`\n"
        f"- expected paired runs: `{summary['expected_pair_count']}`\n"
        "- model/simulator/outcomes: `false / false / false`\n"
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    sums = root / "SHA256SUMS"
    sums.write_text(
        "\n".join(
            f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}"
            for path in files
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    root_sha = _file_sha256(sums)
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha}  SHA256SUMS\n", encoding="ascii", newline="\n"
    )
    return root_sha


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_dirty(path: Path) -> bool:
    return bool(
        subprocess.run(
            ["git", "-C", str(path), "status", "--short", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )


if __name__ == "__main__":
    main()
