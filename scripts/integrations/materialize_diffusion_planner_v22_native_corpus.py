#!/usr/bin/env python3
"""Preflight and materialize the v22 native decision corpus.

The execution implementation reuses ``build_native_arm_runner``. This first
gate is intentionally static: it validates the frozen train-only inputs and
does not build the runner, load the model, or execute the simulator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from camp_core.integrations.diffusion_planner_v22_split import (
    validate_feature_fields,
    validate_split_manifest,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    build_native_arm_runner,
    validate_v22_capability_config,
    verify_config_assets,
)


FEATURE_PAYLOAD_FIELDS = (
    "atom_matrix",
    "source_valid_mask",
    "candidate_row_sha256",
)
IDENTITY_FIELDS = frozenset(
    {
        "logical_map_sha256",
        "map_id",
        "route_id",
        "route_identity_sha256",
        "group_sha256",
        "split",
        "seed",
    }
)
FORMAL_SEEDS = frozenset({11, 12, 13})


def validate_corpus_preflight(
    config: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    if config.get("schema_version") != "camp_dp_v22_native_corpus_v1":
        raise ValueError("corpus config schema mismatch")
    validate_split_manifest(manifest)
    if manifest.get("source_only") is not True:
        raise ValueError("split manifest must remain source-only")
    if manifest.get("outcome_fields_consumed") != []:
        raise ValueError("split manifest consumed outcomes")

    source_split = _mapping(config, "source_split")
    if source_split.get("split_freeze_sha256") != manifest.get(
        "split_freeze_sha256"
    ):
        raise ValueError("split freeze SHA256 mismatch")

    collection = _mapping(config, "collection")
    if collection.get("execution_splits") != ["train"]:
        raise ValueError("corpus preflight is train-only")
    if (
        collection.get("sample_every_ticks") != 5
        or float(collection.get("native_dt_s", -1.0)) != 0.1
        or float(collection.get("snapshot_interval_s", -1.0)) != 0.5
        or collection.get("max_steps") != 64
    ):
        raise ValueError("native corpus cadence mismatch")
    if (
        collection.get("candidate_k") != 8
        or collection.get("selection_policy") != "v22_source_valid"
        or collection.get("score_contract") != "score_k(w)=a_k^T w"
        or collection.get("nonnegative_simplex") is not True
        or collection.get("behavior_policy")
        != "v18_ablation_corpus_collection_only"
    ):
        raise ValueError("native corpus candidate or behavior contract mismatch")

    fields = list(config.get("feature_payload_fields", []))
    if fields != list(FEATURE_PAYLOAD_FIELDS) or IDENTITY_FIELDS.intersection(fields):
        raise ValueError("feature payload must contain only approved non-identity fields")
    validate_feature_fields(fields)
    receipt_fields = set(config.get("receipt_only_identity_fields", []))
    if not {
        "logical_map_sha256",
        "route_identity_sha256",
        "group_sha256",
        "split",
        "seed",
    }.issubset(receipt_fields):
        raise ValueError("receipt-only identity fields are incomplete")

    for name in (
        "holdout_execution_authorized",
        "calibration_execution_authorized",
        "formal_seeds_authorized",
        "full36_authorized",
        "claim_authorized",
    ):
        if config.get(name) is not False:
            raise ValueError(f"{name} must be false in train preflight")

    splits = _mapping(manifest, "splits")
    route_counts = {
        split: len(_mapping(splits, split).get("routes", []))
        for split in ("train", "calibration", "holdout")
    }
    seed_counts = {
        split: len(_mapping(splits, split).get("seed_namespace", []))
        for split in ("train", "calibration", "holdout")
    }
    if route_counts != dict(_mapping(collection, "expected_route_counts")):
        raise ValueError("route counts differ from frozen corpus config")
    if seed_counts != dict(_mapping(collection, "expected_seed_counts")):
        raise ValueError("seed counts differ from frozen corpus config")
    all_seeds = {
        int(seed)
        for split in ("train", "calibration", "holdout")
        for seed in _mapping(splits, split).get("seed_namespace", [])
    }
    if all_seeds.intersection(FORMAL_SEEDS):
        raise ValueError("formal seed is forbidden")

    train_runs = route_counts["train"] * seed_counts["train"]
    if train_runs != collection.get("expected_train_route_seed_runs"):
        raise ValueError("train route-seed run count mismatch")
    snapshots_per_run = (
        (int(collection["max_steps"]) - 1)
        // int(collection["sample_every_ticks"])
        + 1
    )
    theoretical_max = train_runs * snapshots_per_run
    if theoretical_max != collection.get("theoretical_max_train_snapshots"):
        raise ValueError("theoretical train snapshot ceiling mismatch")

    for route in _mapping(splits, "train").get("routes", []):
        asset = _mapping(route, "route_asset")
        path = Path(str(asset.get("path", "")))
        if not path.is_file() or _file_sha256(path) != asset.get("sha256"):
            raise ValueError(f"route asset SHA256 mismatch: {path}")

    levels = [int(value) for value in collection.get("learning_curve_levels", [])]
    if levels != [5000, 10000, 20000, 50000]:
        raise ValueError("learning curve levels mismatch")
    reachable = [level for level in levels if level <= theoretical_max]
    return {
        "schema_version": "camp_dp_v22_native_corpus_preflight_summary_v1",
        "status": (
            "passed" if reachable else "passed_with_sub_5k_training_ceiling"
        ),
        "route_counts": route_counts,
        "seed_counts": seed_counts,
        "train_route_seed_runs": train_runs,
        "snapshots_per_complete_run": snapshots_per_run,
        "theoretical_max_train_snapshots": theoretical_max,
        "reachable_learning_curve_levels": reachable,
        "run_all_available_snapshots": not reachable,
        "behavior_policy": collection["behavior_policy"],
        "feature_payload_fields": fields,
        "model_loaded": False,
        "simulator_executed": False,
        "calibration_executed": False,
        "holdout_executed": False,
        "holdout_outcomes_read": False,
        "claim_authorized": False,
        "next_work_target": "v22_native_decision_sink_and_corpus_writer_tdd_only",
    }


def run_static_preflight(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = _mapping(config, "source_split")
    manifest_path = Path(str(source["manifest_path"]))
    if _file_sha256(manifest_path) != source.get("manifest_sha256"):
        raise ValueError("source split manifest SHA256 mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    base = _mapping(config, "base_native_config")
    base_path = Path(str(base["path"]))
    if _file_sha256(base_path) != base.get("sha256"):
        raise ValueError("base native config SHA256 mismatch")
    base_config = json.loads(base_path.read_text(encoding="utf-8"))
    validate_v22_capability_config(base_config)
    verified_assets = verify_config_assets(base_config)

    summary = validate_corpus_preflight(config, manifest)
    summary.update(
        {
            "source_manifest": str(manifest_path),
            "source_manifest_sha256": source["manifest_sha256"],
            "split_freeze_sha256": source["split_freeze_sha256"],
            "base_native_config_sha256": base["sha256"],
            "verified_base_asset_count": len(verified_assets),
            "runner_factory": build_native_arm_runner.__name__,
        }
    )
    return summary


def _mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    result = value.get(name)
    if not isinstance(result, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return result


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run_static_preflight(args.config), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
