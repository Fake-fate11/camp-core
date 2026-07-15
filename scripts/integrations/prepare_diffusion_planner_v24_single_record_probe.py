#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

PROBE_SCHEMA = "camp_dp_v24_single_record_source_probe_v1"
PROBE_SEED = 24001


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select_probe_route(census: Mapping[str, Any]) -> dict[str, Any]:
    if census.get("schema") != "diffusion_planner_v24_outcome_blind_route_census_v1":
        raise ValueError("Unsupported v24 route-census schema.")
    if census.get("route_census_completed") is not True:
        raise ValueError("Route census is incomplete.")
    for field in (
        "model_loaded",
        "candidate_generation_started",
        "outcome_accessed",
        "holdout_opened",
    ):
        if census.get(field) is not False:
            raise ValueError(f"Route census crossed source-only boundary: {field}")
    routes = [dict(route) for route in census.get("retained_routes", [])]
    if not routes:
        raise ValueError("Route census has no retained source-valid route.")
    return min(
        routes,
        key=lambda route: (
            str(route["map_family_id"]),
            str(route["identity_sha256"]),
            str(route["record_key"]),
        ),
    )


def build_probe_config(
    template: Mapping[str, Any],
    selected_route: Mapping[str, Any],
    *,
    route_asset_path: Path,
    route_asset_sha256: str,
) -> dict[str, Any]:
    config = copy.deepcopy(dict(template))
    identity = str(selected_route["identity_sha256"])
    if len(identity) != 64 or len(route_asset_sha256) != 64:
        raise ValueError("Probe route and asset require SHA256 identities.")
    map_path = str(selected_route["source_map_path"])
    map_sha256 = str(selected_route["source_map_sha256"])
    if len(map_sha256) != 64:
        raise ValueError("Probe source map requires a SHA256 receipt.")

    config["schema_version"] = PROBE_SCHEMA
    config["selector"]["selection_policy"] = "v22_source_valid"
    config["selector"]["role"] = "v24_read_only_baseline_source_probe"
    config["map"] = {"path": map_path, "sha256": map_sha256}
    config["routes"] = [
        {
            "name": identity,
            "path": route_asset_path.as_posix(),
            "sha256": route_asset_sha256,
        }
    ]
    config["seeds"] = {
        "scenario": PROBE_SEED,
        "candidate": PROBE_SEED,
        "bootstrap": PROBE_SEED,
        "formal_forbidden": [11, 12, 13],
    }
    config["spawn_config"]["seed"] = PROBE_SEED
    config["spawn_config"]["max_steps"] = 1
    config["protocol"] = {
        "arm_order": ["camp"],
        "route_order": [identity],
        "capability_route": identity,
        "capability_steps": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v24_source_only_single_record_probe",
        "route_selection_rule": (
            "lexicographic_map_family_identity_record_key"
        ),
        "candidate_k": 8,
        "claim_authorized": False,
        "training_authorized": False,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
    }
    return config


def prepare_probe(
    route_census_path: Path,
    template_path: Path,
    output_dir: Path,
    dp_repo: Path,
) -> dict[str, Any]:
    route_census_path = Path(route_census_path)
    template_path = Path(template_path)
    output_dir = Path(output_dir)
    dp_repo = Path(dp_repo)
    if output_dir.exists():
        raise FileExistsError(f"Output already exists: {output_dir}")
    census = json.loads(route_census_path.read_text(encoding="utf-8"))
    template = json.loads(template_path.read_text(encoding="utf-8"))
    selected = select_probe_route(census)
    map_path = Path(str(selected["source_map_path"]))
    if _file_sha256(map_path) != selected["source_map_sha256"]:
        raise ValueError("Selected probe map SHA does not match live source.")

    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.route import Route

    output_dir.mkdir(parents=True)
    route_path = output_dir / "probe_route.pkl"
    route_spec = selected["route_spec"]
    lanelet_ids = [int(value) for value in route_spec["lanelet_ids"]]
    route = Route(
        map_path=str(map_path),
        start_pose=np.asarray(route_spec["start_pose"], dtype=np.float32),
        goal_pose=np.asarray(route_spec["goal_pose"], dtype=np.float32),
        start_lanelet_id=lanelet_ids[0],
        goal_lanelet_id=lanelet_ids[-1],
        route_lanelet_ids=lanelet_ids,
    )
    route.save(route_path)
    route_sha256 = _file_sha256(route_path)
    config = build_probe_config(
        template,
        selected,
        route_asset_path=route_path,
        route_asset_sha256=route_sha256,
    )
    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_v24_single_record_source_probe_config,
    )

    validate_v24_single_record_source_probe_config(config)
    config_path = output_dir / "probe_config.json"
    selection_path = output_dir / "selected_route.json"
    config_path.write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    selection_path.write_text(
        json.dumps(selected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = {
        "schema": "diffusion_planner_v24_single_record_probe_preparation_v1",
        "route_census_path": str(route_census_path),
        "route_census_sha256": _file_sha256(route_census_path),
        "selection_rule": "lexicographic_map_family_identity_record_key",
        "selected_record_key": selected["record_key"],
        "selected_identity_sha256": selected["identity_sha256"],
        "selected_map_family_id": selected["map_family_id"],
        "selected_map_path": str(map_path),
        "selected_map_sha256": selected["source_map_sha256"],
        "route_asset_path": str(route_path),
        "route_asset_sha256": route_sha256,
        "config_path": str(config_path),
        "config_sha256": _file_sha256(config_path),
        "seed": PROBE_SEED,
        "candidate_k": 8,
        "probe_steps": 1,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    (output_dir / "preparation.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare the source-only v24 single-record fixed-DP probe."
    )
    parser.add_argument("--route-census", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = prepare_probe(
        args.route_census,
        args.template,
        args.output_dir,
        args.dp_repo,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
