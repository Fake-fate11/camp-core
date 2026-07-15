#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SPLIT_PLAN_SHA256 = (
    "52ea1a5c498c73be64ed9a2f4ec6093574eb534f25e7dd0f82081b683a376539"
)
SPLIT_MANIFEST_SHA256 = (
    "ba814ee3da89fc6d9b3ae1ce9a9929e38bebc6349f3871f8d105f285207bf5fa"
)
TRAIN_SEEDS = (24001, 24002, 24003, 24004, 24005)
EXPECTED_ROUTE_COUNTS = {"train": 375, "calibration": 2, "holdout": 24}
CORPUS_STEPS = 64
SAMPLE_EVERY_TICKS = 1


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _source_root_checks(
    root: Path, expected_root_sha256: str, prefix: str
) -> list[dict[str, Any]]:
    root = Path(root).resolve()
    manifest = root / "SHA256SUMS"
    checks = [
        {"name": f"{prefix}_manifest_exists", "passed": manifest.is_file()},
        {
            "name": f"{prefix}_root_sha256",
            "passed": manifest.is_file()
            and _file_sha256(manifest) == expected_root_sha256,
        },
    ]
    if not manifest.is_file():
        return checks
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = (root / relative).resolve()
        within_root = root == path or root in path.parents
        checks.append(
            {
                "name": f"{prefix}_sha:{relative}",
                "passed": within_root and path.is_file() and _file_sha256(path) == digest,
            }
        )
    return checks


def build_corpus_plan(
    split_manifest: Mapping[str, Any], route_census: Mapping[str, Any]
) -> dict[str, Any]:
    if split_manifest.get("schema") != "camp_dp_v24_map_family_split_manifest_v1":
        raise ValueError("corrected split schema mismatch")
    if split_manifest.get("plan_sha256") != SPLIT_PLAN_SHA256:
        raise ValueError("corrected split plan SHA256 mismatch")
    if split_manifest.get("manifest_sha256") != SPLIT_MANIFEST_SHA256:
        raise ValueError("corrected split manifest SHA256 mismatch")
    if split_manifest.get("outcome_fields_consumed") != []:
        raise ValueError("corrected split consumed outcome fields")
    if split_manifest.get("holdout_opened") is not False:
        raise ValueError("corrected split opened holdout")
    if route_census.get("schema") != "diffusion_planner_v24_outcome_blind_route_census_v1":
        raise ValueError("route census schema mismatch")
    for field, expected in {
        "route_census_completed": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "outcome_accessed": False,
        "holdout_opened": False,
    }.items():
        if route_census.get(field) is not expected:
            raise ValueError(f"route census source-only boundary mismatch: {field}")

    routes_by_key = {
        str(route["record_key"]): dict(route)
        for route in route_census.get("retained_routes", [])
    }
    records = [dict(record) for record in split_manifest.get("records", [])]
    if len(routes_by_key) != 401 or len(records) != 401:
        raise ValueError("v24 corpus requires all 401 frozen routes")
    if set(routes_by_key) != {str(record["record_key"]) for record in records}:
        raise ValueError("split and route census record keys differ")

    counts = {split: 0 for split in EXPECTED_ROUTE_COUNTS}
    train_routes = []
    for record in records:
        split = str(record["split"])
        if split not in counts:
            raise ValueError("unknown split")
        counts[split] += 1
        route = routes_by_key[str(record["record_key"])]
        if (
            str(record["identity_sha256"]) != str(route["identity_sha256"])
            or str(record["map_family_id"]) != str(route["map_family_id"])
        ):
            raise ValueError("split route identity mismatch")
        expected_seeds = list(split_manifest["seed_namespaces"][split])
        if list(record["seeds"]) != expected_seeds:
            raise ValueError("split route seed namespace mismatch")
        if split == "train":
            if tuple(expected_seeds) != TRAIN_SEEDS:
                raise ValueError("train seed namespace mismatch")
            route["corridor_group_sha256"] = str(
                record["corridor_group_sha256"]
            )
            train_routes.append(route)
    if counts != EXPECTED_ROUTE_COUNTS:
        raise ValueError("v24 route counts mismatch")

    train_routes.sort(key=lambda item: str(item["record_key"]))
    plan = {
        "schema": "camp_dp_v24_native_corpus_plan_v1",
        "source_split_plan_sha256": SPLIT_PLAN_SHA256,
        "source_split_manifest_sha256": SPLIT_MANIFEST_SHA256,
        "route_counts": counts,
        "execution_splits": ["train"],
        "train_route_count": len(train_routes),
        "train_seeds": list(TRAIN_SEEDS),
        "train_route_seed_run_count": len(train_routes) * len(TRAIN_SEEDS),
        "corpus_steps": CORPUS_STEPS,
        "sample_every_ticks": SAMPLE_EVERY_TICKS,
        "thinning_rule": "none_capture_every_available_tick",
        "theoretical_max_snapshot_count": (
            len(train_routes) * len(TRAIN_SEEDS) * CORPUS_STEPS
        ),
        "candidate_k": 8,
        "feature_schema": "dp_camp_v10_14d",
        "feature_payload_fields": [
            "atom_matrix",
            "source_valid_mask",
            "candidate_row_sha256",
        ],
        "receipt_only_identity_fields": [
            "logical_map_sha256",
            "map_family_id",
            "corridor_group_sha256",
            "route_identity_sha256",
            "record_key",
            "split",
            "seed",
        ],
        "causal_snapshot_required": True,
        "candidate_immutability_required": True,
        "candidate0_default_identity_required": True,
        "score_contract": "score_k(w)=a_k^T w",
        "nonnegative_simplex": True,
        "phases": [
            {
                "name": "capability_pilot_all_train_routes_first_seed",
                "seeds": [TRAIN_SEEDS[0]],
                "route_seed_run_count": len(train_routes),
                "tuning_authorized": False,
            },
            {
                "name": "main_completion_remaining_frozen_seeds",
                "seeds": list(TRAIN_SEEDS[1:]),
                "route_seed_run_count": len(train_routes) * 4,
                "tuning_authorized": False,
            },
        ],
        "failure_accounting": "retain_every_attempted_route_seed_in_denominator",
        "minimum_free_disk_gib": 10,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "calibration_access_authorized": False,
        "holdout_access_authorized": False,
        "holdout_opened": False,
        "training_execution_authorized": False,
        "claim_authorized": False,
    }
    plan["plan_sha256"] = _canonical_sha256(plan)
    plan["train_routes"] = train_routes
    return plan


def build_corpus_run_config(
    template: Mapping[str, Any], route: Mapping[str, Any], route_asset: Mapping[str, str], seed: int
) -> dict[str, Any]:
    if seed not in TRAIN_SEEDS:
        raise ValueError("v24 corpus seed namespace mismatch")
    config = copy.deepcopy(dict(template))
    identity = str(route["identity_sha256"])
    config["schema_version"] = "camp_dp_v24_native_corpus_run_v1"
    config["selector"]["selection_policy"] = "v22_source_valid"
    config["selector"]["role"] = "v24_train_corpus_collection_only"
    config["map"] = {
        "path": str(route["source_map_path"]),
        "sha256": str(route["source_map_sha256"]),
    }
    config["routes"] = [
        {
            "name": identity,
            "path": str(route_asset["path"]),
            "sha256": str(route_asset["sha256"]),
        }
    ]
    config["seeds"] = {
        "scenario": seed,
        "candidate": seed,
        "bootstrap": seed,
        "formal_forbidden": [11, 12, 13],
    }
    config["spawn_config"]["seed"] = seed
    config["spawn_config"]["max_steps"] = CORPUS_STEPS
    config["protocol"] = {
        "arm_order": ["camp"],
        "route_order": [identity],
        "corpus_steps": CORPUS_STEPS,
        "sample_every_ticks": SAMPLE_EVERY_TICKS,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v24_train_corpus_collection",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_authorized": True,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
    }
    return config


def _validate_template_assets(template: Mapping[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for owner, name in (
        ("fixed_dp", "checkpoint"),
        ("fixed_dp", "args_json"),
        ("selector", "atom_scales"),
        ("selector", "weights"),
    ):
        asset = template[owner][name]
        path = Path(str(asset["path"]))
        checks.append(
            {
                "name": f"template_asset:{owner}:{name}",
                "passed": path.is_file() and _file_sha256(path) == asset["sha256"],
            }
        )
    return checks


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_sha = _file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--split-root", type=Path, required=True)
    parser.add_argument("--expected-split-root-sha256", required=True)
    parser.add_argument("--route-census", type=Path, required=True)
    parser.add_argument("--route-census-root", type=Path, required=True)
    parser.add_argument("--expected-route-census-root-sha256", required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {args.output_dir}")

    split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    census = json.loads(args.route_census.read_text(encoding="utf-8"))
    template = json.loads(args.template.read_text(encoding="utf-8"))
    plan = build_corpus_plan(split, census)
    train_routes = plan.pop("train_routes")
    checks = _source_root_checks(
        args.split_root, args.expected_split_root_sha256, "split"
    )
    checks.extend(
        _source_root_checks(
            args.route_census_root,
            args.expected_route_census_root_sha256,
            "route_census",
        )
    )
    dp_head = subprocess.run(
        ["git", "-C", str(args.dp_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dp_status = subprocess.run(
        ["git", "-C", str(args.dp_repo), "status", "--short", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    checks.extend(
        [
            {"name": "fixed_dp_head", "passed": dp_head == FIXED_DP_HEAD},
            {"name": "fixed_dp_tracked_clean", "passed": dp_status == ""},
            {"name": "template_fixed_dp_head", "passed": template["fixed_dp"]["head"] == FIXED_DP_HEAD},
        ]
    )
    checks.extend(_validate_template_assets(template))

    for map_path, expected_sha in sorted(
        {(str(route["source_map_path"]), str(route["source_map_sha256"])) for route in train_routes}
    ):
        path = Path(map_path)
        checks.append(
            {
                "name": f"source_map_sha:{path.name}:{expected_sha[:12]}",
                "passed": path.is_file() and _file_sha256(path) == expected_sha,
            }
        )
    failed = [check["name"] for check in checks if not check["passed"]]
    if failed:
        raise ValueError(f"pre-materialization checks failed: {failed}")

    for path in (args.dp_repo, args.dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.route import Route
    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_v24_corpus_run_config,
    )

    args.output_dir.mkdir(parents=True)
    route_dir = args.output_dir / "routes"
    route_dir.mkdir()
    corpus_routes = []
    config_receipts = []
    for route in train_routes:
        identity = str(route["identity_sha256"])
        asset_path = route_dir / f"{identity}.pkl"
        spec = route["route_spec"]
        lanelet_ids = [int(value) for value in spec["lanelet_ids"]]
        route_object = Route(
            map_path=str(route["source_map_path"]),
            start_pose=np.asarray(spec["start_pose"], dtype=np.float32),
            goal_pose=np.asarray(spec["goal_pose"], dtype=np.float32),
            start_lanelet_id=lanelet_ids[0],
            goal_lanelet_id=lanelet_ids[-1],
            route_lanelet_ids=lanelet_ids,
        )
        route_object.save(asset_path)
        asset = {"path": asset_path.as_posix(), "sha256": _file_sha256(asset_path)}
        corpus_routes.append(
            {
                "record_key": route["record_key"],
                "identity_sha256": identity,
                "map_family_id": route["map_family_id"],
                "corridor_group_sha256": route["corridor_group_sha256"],
                "logical_map_sha256": route["logical_map_sha256"],
                "source_map_path": route["source_map_path"],
                "source_map_sha256": route["source_map_sha256"],
                "source_stratum": route["source_stratum"],
                "route_spec": route["route_spec"],
                "route_asset": asset,
                "seeds": list(TRAIN_SEEDS),
            }
        )
        for seed in TRAIN_SEEDS:
            run_config = build_corpus_run_config(template, route, asset, seed)
            validate_v24_corpus_run_config(run_config)
            config_receipts.append(
                {
                    "record_key": route["record_key"],
                    "route_identity_sha256": identity,
                    "seed": seed,
                    "config_sha256": _canonical_sha256(run_config),
                }
            )

    corpus_manifest = {
        "schema": "camp_dp_v24_native_corpus_manifest_v1",
        "plan_sha256": plan["plan_sha256"],
        "source_split_manifest_sha256": SPLIT_MANIFEST_SHA256,
        "split": "train",
        "routes": corpus_routes,
        "route_count": len(corpus_routes),
        "seeds": list(TRAIN_SEEDS),
        "route_seed_run_count": len(config_receipts),
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
    }
    corpus_manifest["manifest_sha256"] = _canonical_sha256(corpus_manifest)
    _write_json(args.output_dir / "corpus_plan.json", plan)
    _write_json(args.output_dir / "corpus_manifest.json", corpus_manifest)
    with (args.output_dir / "run_config_receipts.jsonl").open("w", encoding="utf-8") as handle:
        for receipt in config_receipts:
            handle.write(json.dumps(receipt, sort_keys=True) + "\n")

    free_gib = shutil.disk_usage(args.output_dir).free / (1024**3)
    checks.extend(
        [
            {"name": "train_route_count_375", "passed": len(corpus_routes) == 375},
            {"name": "train_route_seed_runs_1875", "passed": len(config_receipts) == 1875},
            {"name": "theoretical_max_snapshots_120000", "passed": plan["theoretical_max_snapshot_count"] == 120000},
            {"name": "per_tick_no_thinning", "passed": plan["sample_every_ticks"] == 1 and plan["thinning_rule"] == "none_capture_every_available_tick"},
            {"name": "disk_floor_preflight", "passed": free_gib > 10.0},
            {"name": "holdout_closed", "passed": corpus_manifest["holdout_opened"] is False},
        ]
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    result = {
        "schema": "camp_dp_v24_native_corpus_static_preflight_v1",
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "plan_sha256": plan["plan_sha256"],
        "corpus_manifest_sha256": corpus_manifest["manifest_sha256"],
        "route_count": len(corpus_routes),
        "route_seed_run_count": len(config_receipts),
        "theoretical_max_snapshot_count": plan["theoretical_max_snapshot_count"],
        "free_disk_gib_after_preflight": free_gib,
        "fixed_dp_head": dp_head,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
        "training_executed": False,
        "claim_authorized": False,
        "next_work_target": "v24_native_corpus_capability_pilot_all_train_routes_seed_24001_only",
    }
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={dp_head}\n"
        f"SOURCE_SPLIT_ROOT_SHA256={args.expected_split_root_sha256}\n"
        f"SOURCE_ROUTE_CENSUS_ROOT_SHA256={args.expected_route_census_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 train-only native corpus plan and static preflight\n", encoding="utf-8"
    )
    _write_json(args.output_dir / "preflight.json", result)
    (args.output_dir / "preflight.md").write_text(
        "# v24 native corpus static preflight\n\n"
        f"- status: `{result['status']}`\n"
        f"- checks / failed: `{result['check_count']} / {result['failed_count']}`\n"
        "- train routes / seeds / runs: `375 / 5 / 1875`\n"
        "- capture: `64 ticks, every tick, no thinning, max 120000`\n"
        "- model/simulator/candidates/outcomes/holdout: `false/false/false/false/false`\n",
        encoding="utf-8",
    )
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(result, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text(
        "0\n" if result["status"] == "passed" else "1\n", encoding="ascii"
    )
    root_sha = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha,
                "status": result["status"],
                "check_count": result["check_count"],
                "failed_count": result["failed_count"],
                "plan_sha256": result["plan_sha256"],
                "corpus_manifest_sha256": result["corpus_manifest_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
