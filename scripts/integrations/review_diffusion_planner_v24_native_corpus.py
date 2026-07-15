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
CORPUS_PLAN_SHA256 = (
    "d1431ec7a0583d24e16b655b06264450761c770d503262658e5b63612e745e7b"
)
CORPUS_MANIFEST_SHA256 = (
    "87e65ae8347aa225282cfa05a1330d2f7b39464ecda83cae997f1a8c081895fc"
)
TRAIN_SEEDS = (24001, 24002, 24003, 24004, 24005)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_corpus_boundaries(
    plan: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    expected_plan = {
        "execution_splits": ["train"],
        "train_seeds": list(TRAIN_SEEDS),
        "sample_every_ticks": 1,
        "thinning_rule": "none_capture_every_available_tick",
        "outcome_fields_consumed": [],
        "calibration_access_authorized": False,
        "holdout_access_authorized": False,
        "holdout_opened": False,
        "training_execution_authorized": False,
        "claim_authorized": False,
    }
    expected_manifest = {
        "split": "train",
        "seeds": list(TRAIN_SEEDS),
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
    }
    if any(plan.get(name) != value for name, value in expected_plan.items()):
        raise ValueError("corpus plan boundary mismatch")
    if any(manifest.get(name) != value for name, value in expected_manifest.items()):
        raise ValueError("corpus manifest boundary mismatch")


def build_expected_run_config(
    template: Mapping[str, Any],
    route: Mapping[str, Any],
    route_asset: Mapping[str, str],
    seed: int,
) -> dict[str, Any]:
    if seed not in TRAIN_SEEDS:
        raise ValueError("review seed outside v24 train namespace")
    identity = str(route["identity_sha256"])
    config = copy.deepcopy(dict(template))
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
    config["spawn_config"]["max_steps"] = 64
    config["protocol"] = {
        "arm_order": ["camp"],
        "route_order": [identity],
        "corpus_steps": 64,
        "sample_every_ticks": 1,
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
            and file_sha256(manifest) == expected_root_sha256,
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
                "passed": within_root and path.is_file() and file_sha256(path) == digest,
            }
        )
    return checks


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{file_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files
    ]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_sha = file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(
        f"{root_sha}  SHA256SUMS\n", encoding="ascii"
    )
    return root_sha


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-root", type=Path, required=True)
    parser.add_argument("--expected-preflight-root-sha256", required=True)
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

    preflight = json.loads((args.preflight_root / "preflight.json").read_text())
    plan = json.loads((args.preflight_root / "corpus_plan.json").read_text())
    corpus = json.loads((args.preflight_root / "corpus_manifest.json").read_text())
    receipts = [
        json.loads(line)
        for line in (args.preflight_root / "run_config_receipts.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    census = json.loads(args.route_census.read_text(encoding="utf-8"))
    template = json.loads(args.template.read_text(encoding="utf-8"))
    validate_corpus_boundaries(plan, corpus)

    checks = _source_root_checks(
        args.preflight_root,
        args.expected_preflight_root_sha256,
        "preflight",
    )
    checks.extend(
        _source_root_checks(args.split_root, args.expected_split_root_sha256, "split")
    )
    checks.extend(
        _source_root_checks(
            args.route_census_root,
            args.expected_route_census_root_sha256,
            "route_census",
        )
    )
    plan_without_sha = dict(plan)
    plan_without_sha.pop("plan_sha256", None)
    corpus_without_sha = dict(corpus)
    corpus_without_sha.pop("manifest_sha256", None)
    checks.extend(
        [
            {"name": "preflight_status", "passed": preflight.get("status") == "passed" and preflight.get("failed_count") == 0},
            {"name": "split_plan_sha", "passed": split.get("plan_sha256") == SPLIT_PLAN_SHA256},
            {"name": "split_manifest_sha", "passed": split.get("manifest_sha256") == SPLIT_MANIFEST_SHA256},
            {"name": "corpus_plan_declared_sha", "passed": plan.get("plan_sha256") == CORPUS_PLAN_SHA256},
            {"name": "corpus_plan_recomputed_sha", "passed": canonical_sha256(plan_without_sha) == CORPUS_PLAN_SHA256},
            {"name": "corpus_manifest_declared_sha", "passed": corpus.get("manifest_sha256") == CORPUS_MANIFEST_SHA256},
            {"name": "corpus_manifest_recomputed_sha", "passed": canonical_sha256(corpus_without_sha) == CORPUS_MANIFEST_SHA256},
            {"name": "train_route_count", "passed": corpus.get("route_count") == 375 and len(corpus.get("routes", [])) == 375},
            {"name": "train_route_seed_run_count", "passed": corpus.get("route_seed_run_count") == 1875 and len(receipts) == 1875},
            {"name": "theoretical_max_snapshot_count", "passed": plan.get("theoretical_max_snapshot_count") == 120000},
            {"name": "template_fixed_dp_head", "passed": template["fixed_dp"]["head"] == FIXED_DP_HEAD},
        ]
    )
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
                "passed": path.is_file() and file_sha256(path) == asset["sha256"],
            }
        )

    census_by_key = {
        str(route["record_key"]): route for route in census.get("retained_routes", [])
    }
    train_records = {
        str(record["record_key"]): record
        for record in split.get("records", [])
        if record.get("split") == "train"
    }
    corpus_by_key = {
        str(route["record_key"]): route for route in corpus.get("routes", [])
    }
    checks.extend(
        [
            {"name": "source_census_401", "passed": len(census_by_key) == 401},
            {"name": "source_train_375", "passed": len(train_records) == 375},
            {"name": "corpus_train_membership_exact", "passed": set(corpus_by_key) == set(train_records)},
        ]
    )
    receipt_by_key = {
        (str(item["record_key"]), int(item["seed"])): item for item in receipts
    }
    checks.append(
        {"name": "config_receipt_keys_unique", "passed": len(receipt_by_key) == 1875}
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
        ]
    )
    for path in (args.dp_repo, args.dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.route import Route
    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
        validate_v24_corpus_run_config,
    )

    preflight_root = args.preflight_root.resolve()
    map_hash_cache = {}
    for record_key in sorted(corpus_by_key):
        route = corpus_by_key[record_key]
        source = census_by_key.get(record_key, {})
        split_record = train_records.get(record_key, {})
        identity = str(route["identity_sha256"])
        checks.append(
            {
                "name": f"route_source_identity:{identity}",
                "passed": (
                    identity == str(source.get("identity_sha256"))
                    and route.get("map_family_id") == source.get("map_family_id")
                    and route.get("logical_map_sha256") == source.get("logical_map_sha256")
                    and route.get("source_map_path") == source.get("source_map_path")
                    and route.get("source_map_sha256") == source.get("source_map_sha256")
                    and route.get("source_stratum") == source.get("source_stratum")
                    and route.get("route_spec") == source.get("route_spec")
                    and route.get("corridor_group_sha256") == split_record.get("corridor_group_sha256")
                    and route.get("seeds") == list(TRAIN_SEEDS)
                ),
            }
        )
        asset = route["route_asset"]
        asset_path = Path(str(asset["path"])).resolve()
        within_preflight = preflight_root in asset_path.parents
        asset_ok = (
            within_preflight
            and asset_path.is_file()
            and file_sha256(asset_path) == asset["sha256"]
        )
        checks.append({"name": f"route_asset_sha:{identity}", "passed": asset_ok})
        loaded_ok = False
        if asset_ok:
            loaded = Route.load(asset_path)
            spec = route["route_spec"]
            lanelet_ids = [int(value) for value in spec["lanelet_ids"]]
            loaded_ok = (
                loaded.map_path == route["source_map_path"]
                and loaded.route_lanelet_ids == lanelet_ids
                and loaded.start_lanelet_id == lanelet_ids[0]
                and loaded.goal_lanelet_id == lanelet_ids[-1]
                and np.array_equal(
                    loaded.start_pose,
                    np.asarray(spec["start_pose"], dtype=np.float32),
                )
                and np.array_equal(
                    loaded.goal_pose,
                    np.asarray(spec["goal_pose"], dtype=np.float32),
                )
            )
        checks.append({"name": f"route_asset_payload:{identity}", "passed": loaded_ok})
        map_path = str(route["source_map_path"])
        if map_path not in map_hash_cache:
            path = Path(map_path)
            map_hash_cache[map_path] = file_sha256(path) if path.is_file() else None
        checks.append(
            {
                "name": f"route_source_map:{identity}",
                "passed": map_hash_cache[map_path] == route["source_map_sha256"],
            }
        )
        for seed in TRAIN_SEEDS:
            config = build_expected_run_config(template, route, asset, seed)
            validate_v24_corpus_run_config(config)
            receipt = receipt_by_key.get((record_key, seed), {})
            checks.append(
                {
                    "name": f"run_config:{identity}:{seed}",
                    "passed": receipt.get("route_identity_sha256") == identity
                    and receipt.get("config_sha256") == canonical_sha256(config),
                }
            )

    free_gib = shutil.disk_usage(args.output_dir.parent).free / (1024**3)
    checks.append({"name": "disk_floor", "passed": free_gib > 10.0})
    failed = [check["name"] for check in checks if not check["passed"]]
    result = {
        "schema": "camp_dp_v24_native_corpus_static_preflight_review_v1",
        "status": "passed" if not failed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "source_preflight_root_sha256": args.expected_preflight_root_sha256,
        "corpus_plan_sha256": CORPUS_PLAN_SHA256,
        "corpus_manifest_sha256": CORPUS_MANIFEST_SHA256,
        "route_count": len(corpus_by_key),
        "route_seed_run_count": len(receipt_by_key),
        "source_map_count": len(map_hash_cache),
        "free_disk_gib": free_gib,
        "fixed_dp_head": dp_head,
        "preflight_reexecuted": False,
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
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={dp_head}\n"
        f"SOURCE_PREFLIGHT_ROOT_SHA256={args.expected_preflight_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 native corpus static-preflight independent review\n", encoding="utf-8"
    )
    _write_json(args.output_dir / "review.json", result)
    (args.output_dir / "review.md").write_text(
        "# v24 native corpus static-preflight independent review\n\n"
        f"- status: `{result['status']}`\n"
        f"- checks / failed: `{result['check_count']} / {result['failed_count']}`\n"
        "- train routes / route-seed configs: `375 / 1875`\n"
        "- preflight/model/simulator/candidates/outcomes/holdout: `false/false/false/false/false/false`\n",
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
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
