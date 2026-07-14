#!/usr/bin/env python3
"""Preflight and materialize the v22 native decision corpus.

The execution implementation reuses ``build_native_arm_runner``. This first
gate is intentionally static: it validates the frozen train-only inputs and
does not build the runner, load the model, or execute the simulator.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner_v22_split import (
    validate_feature_fields,
    validate_split_manifest,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    build_native_arm_runner,
    validate_v22_capability_config,
    validate_v22_corpus_run_config,
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


class CorpusSnapshotWriter:
    def __init__(
        self,
        *,
        output_dir: Path,
        split: str,
        logical_map_sha256: str,
        route_identity_sha256: str,
        group_sha256: str,
        seed: int,
        source_stratum: Mapping[str, Any] | None = None,
    ) -> None:
        if split not in {"train", "calibration"}:
            raise ValueError("holdout snapshots are forbidden")
        for name, value in (
            ("logical_map_sha256", logical_map_sha256),
            ("route_identity_sha256", route_identity_sha256),
            ("group_sha256", group_sha256),
        ):
            if not _is_sha256(value):
                raise ValueError(f"{name} must be lowercase SHA256")
        if (
            isinstance(seed, bool)
            or not isinstance(seed, int)
            or seed < 0
            or seed in FORMAL_SEEDS
        ):
            raise ValueError("seed must be non-formal nonnegative integer")
        self.output_dir = Path(output_dir)
        self.split = split
        self.logical_map_sha256 = logical_map_sha256
        self.route_identity_sha256 = route_identity_sha256
        self.group_sha256 = group_sha256
        self.seed = seed
        self.source_stratum = {
            str(name): bool(value)
            for name, value in (source_stratum or {}).items()
        }
        self.snapshot_sha256: list[str] = []
        self.all_k_high_risk_snapshot_count = 0
        (self.output_dir / "snapshots").mkdir(parents=True, exist_ok=True)

    def __call__(self, snapshot: Mapping[str, Any]) -> str:
        payload = json.loads(json.dumps(snapshot, allow_nan=False))
        if payload.get("schema_version") != "v22_native_decision_snapshot_v1":
            raise ValueError("decision snapshot schema mismatch")
        features = _mapping(payload, "feature_payload")
        if list(features) != list(FEATURE_PAYLOAD_FIELDS):
            raise ValueError("feature payload schema mismatch")
        if IDENTITY_FIELDS.intersection(features):
            raise ValueError("identity is forbidden in feature payload")
        atoms = np.asarray(features["atom_matrix"], dtype=np.float64)
        if atoms.shape != (8, 14) or not np.isfinite(atoms).all():
            raise ValueError("atom matrix must be finite [8,14]")
        source_valid = features["source_valid_mask"]
        if (
            not isinstance(source_valid, list)
            or len(source_valid) != 8
            or any(not isinstance(value, bool) for value in source_valid)
        ):
            raise ValueError("source-valid mask must contain eight booleans")
        row_sha = features["candidate_row_sha256"]
        if (
            not isinstance(row_sha, list)
            or len(row_sha) != 8
            or any(not _is_sha256(value) for value in row_sha)
        ):
            raise ValueError("candidate row SHA256 receipt mismatch")

        sidecar = dict(_mapping(payload, "sidecar"))
        before = sidecar.get("candidate_tensor_sha256_before")
        after = sidecar.get("candidate_tensor_sha256_after")
        if not _is_sha256(before) or before != after:
            raise ValueError("candidate tensor SHA256 mismatch")
        if not _is_sha256(sidecar.get("causal_input_sha256")):
            raise ValueError("causal input SHA256 mismatch")
        physical = sidecar.get("physical_feasible_mask")
        if (
            not isinstance(physical, list)
            or len(physical) != 8
            or any(not isinstance(value, bool) for value in physical)
        ):
            raise ValueError("physical-risk mask must contain eight booleans")
        sidecar.update(
            {
                "logical_map_sha256": self.logical_map_sha256,
                "route_identity_sha256": self.route_identity_sha256,
                "group_sha256": self.group_sha256,
                "split": self.split,
                "seed": self.seed,
                "source_stratum": dict(self.source_stratum),
            }
        )
        payload["sidecar"] = sidecar

        content = _canonical_json_bytes(payload)
        digest = hashlib.sha256(content).hexdigest()
        path = self.output_dir / "snapshots" / f"{digest}.json"
        if path.exists():
            if path.read_bytes() != content:
                raise ValueError("content-addressed snapshot collision")
        else:
            temporary = path.with_suffix(".json.tmp")
            temporary.write_bytes(content)
            temporary.replace(path)
        if digest not in self.snapshot_sha256:
            self.snapshot_sha256.append(digest)
            if bool(sidecar.get("all_k_high_risk")):
                self.all_k_high_risk_snapshot_count += 1
        return digest

    def write_run_receipt(
        self,
        *,
        status: str,
        failure_stage: str | None = None,
        failure_reason: str | None = None,
        wall_clock_s: float | None = None,
    ) -> Path:
        if status not in {"ok", "failed"}:
            raise ValueError("run receipt status must be ok or failed")
        if status == "failed" and (not failure_stage or not failure_reason):
            raise ValueError("failed run receipt requires stage and reason")
        receipt = {
            "schema_version": "v22_native_corpus_run_receipt_v1",
            "status": status,
            "split": self.split,
            "logical_map_sha256": self.logical_map_sha256,
            "route_identity_sha256": self.route_identity_sha256,
            "group_sha256": self.group_sha256,
            "seed": self.seed,
            "snapshot_sha256": list(self.snapshot_sha256),
            "failure_stage": failure_stage,
            "failure_reason": failure_reason,
            "retained_in_denominator": True,
            "wall_clock_s": wall_clock_s,
        }
        path = (
            self.output_dir
            / "receipts"
            / self.split
            / self.route_identity_sha256
            / f"seed_{self.seed}.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        content = _canonical_json_bytes(receipt)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(content)
        temporary.replace(path)
        return path


def build_corpus_run_config(
    base_config: Mapping[str, Any],
    route: Mapping[str, Any],
    *,
    seed: int,
    max_steps: int,
) -> dict[str, Any]:
    validate_v22_capability_config(base_config)
    if max_steps != 64:
        raise ValueError("v22 corpus run must use 64 steps")
    asset = _mapping(route, "route_asset")
    route_spec = _mapping(route, "route_spec")
    if route.get("logical_map_sha256") != _mapping(base_config, "map").get(
        "sha256"
    ) or route_spec.get("map_path") != _mapping(base_config, "map").get("path"):
        raise ValueError("train route logical map differs from native base config")

    config = deepcopy(dict(base_config))
    config["schema_version"] = "camp_dp_v22_native_corpus_run_v1"
    config["selector"]["role"] = "v18_ablation_corpus_collection_only"
    config["routes"] = [
        {
            "name": str(route["identity_sha256"]),
            "path": str(asset["path"]),
            "sha256": str(asset["sha256"]),
        }
    ]
    config["seeds"] = {
        "scenario": seed,
        "candidate": seed,
        "bootstrap": seed,
        "formal_forbidden": [11, 12, 13],
    }
    config["spawn_config"]["seed"] = seed
    config["spawn_config"]["max_steps"] = max_steps
    config["protocol"] = {
        "corpus_steps": max_steps,
        "sample_every_ticks": 5,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "train_corpus_collection",
        "training_authorized": True,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
        "claim_authorized": False,
    }
    validate_v22_corpus_run_config(config)
    return config


def execute_train_manifest(
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
    base_config: Mapping[str, Any],
    *,
    output_dir: Path,
    run_arm: Callable[..., Mapping[str, Any]],
) -> dict[str, Any]:
    preflight = validate_corpus_preflight(config, manifest)
    validate_v22_capability_config(base_config)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)

    collection = _mapping(config, "collection")
    max_steps = int(collection["max_steps"])
    train = _mapping(_mapping(manifest, "splits"), "train")
    routes = sorted(train.get("routes", []), key=lambda item: item["identity_sha256"])
    seeds = sorted(int(value) for value in train.get("seed_namespace", []))
    complete = 0
    failed = 0
    failures = []
    run_timings = []
    snapshot_count_by_source_stratum: dict[str, int] = {}
    all_k_high_risk_snapshot_count = 0
    execution_started = time.perf_counter()
    for route in routes:
        for seed in seeds:
            writer = CorpusSnapshotWriter(
                output_dir=output_dir,
                split="train",
                logical_map_sha256=str(route["logical_map_sha256"]),
                route_identity_sha256=str(route["identity_sha256"]),
                group_sha256=str(route["group_sha256"]),
                seed=seed,
                source_stratum=route.get("source_stratum", {}),
            )
            native_output = (
                output_dir
                / "native_runs"
                / str(route["identity_sha256"])
                / f"seed_{seed}"
            )
            run_started = time.perf_counter()
            try:
                run_config = build_corpus_run_config(
                    base_config, route, seed=seed, max_steps=max_steps
                )
                native_route = run_config["routes"][0]
                result = run_arm(
                    route=native_route,
                    arm="camp",
                    config=run_config,
                    output_dir=native_output,
                    max_steps=max_steps,
                    decision_sink=writer,
                )
                if result.get("status") != "ok":
                    raise RuntimeError(
                        str(result.get("failure_reason") or "native arm failed")
                    )
            except Exception as exc:
                wall_clock_s = time.perf_counter() - run_started
                failed += 1
                failure = {
                    "route_identity_sha256": route["identity_sha256"],
                    "seed": seed,
                    "failure_stage": "native_arm_execution",
                    "failure_reason": str(exc),
                }
                failures.append(failure)
                writer.write_run_receipt(
                    status="failed",
                    failure_stage=failure["failure_stage"],
                    failure_reason=failure["failure_reason"],
                    wall_clock_s=wall_clock_s,
                )
                run_timings.append(
                    {
                        "route_identity_sha256": route["identity_sha256"],
                        "seed": seed,
                        "status": "failed",
                        "wall_clock_s": wall_clock_s,
                    }
                )
                continue
            wall_clock_s = time.perf_counter() - run_started
            complete += 1
            writer.write_run_receipt(status="ok", wall_clock_s=wall_clock_s)
            run_timings.append(
                {
                    "route_identity_sha256": route["identity_sha256"],
                    "seed": seed,
                    "status": "ok",
                    "wall_clock_s": wall_clock_s,
                }
            )
            snapshot_count = len(writer.snapshot_sha256)
            strata = {
                str(name): bool(value)
                for name, value in route.get("source_stratum", {}).items()
            }
            active_strata = [name for name, value in strata.items() if value]
            if not active_strata:
                active_strata = ["normal"]
            for stratum in active_strata:
                snapshot_count_by_source_stratum[stratum] = (
                    snapshot_count_by_source_stratum.get(stratum, 0)
                    + snapshot_count
                )
            all_k_high_risk_snapshot_count += (
                writer.all_k_high_risk_snapshot_count
            )

    planned = len(routes) * len(seeds)
    summary = {
        "schema_version": "camp_dp_v22_native_train_corpus_summary_v1",
        "status": (
            "complete" if failed == 0 else "complete_with_retained_failures"
        ),
        "planned_route_seed_runs": planned,
        "complete_route_seed_runs": complete,
        "failed_route_seed_runs": failed,
        "retained_route_seed_runs": complete + failed,
        "route_coverage": (complete + failed) / planned if planned else 0.0,
        "snapshot_count": len(list((output_dir / "snapshots").glob("*.json"))),
        "snapshot_count_by_source_stratum": dict(
            sorted(snapshot_count_by_source_stratum.items())
        ),
        "all_k_high_risk_snapshot_count": all_k_high_risk_snapshot_count,
        "theoretical_max_train_snapshots": preflight[
            "theoretical_max_train_snapshots"
        ],
        "failures": failures,
        "route_seed_timings": run_timings,
        "wall_clock_s": time.perf_counter() - execution_started,
        "calibration_executed": False,
        "holdout_executed": False,
        "holdout_outcomes_read": False,
        "claim_authorized": False,
    }
    (output_dir / "corpus_summary.json").write_bytes(
        _canonical_json_bytes(summary)
    )
    return summary


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
        "next_work_target": "v22_native_train_corpus_execution_only",
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
    train = _mapping(_mapping(manifest, "splits"), "train")
    routes = sorted(train.get("routes", []), key=lambda item: item["identity_sha256"])
    seeds = sorted(int(value) for value in train.get("seed_namespace", []))
    run_configs = [
        build_corpus_run_config(
            base_config,
            route,
            seed=seed,
            max_steps=int(_mapping(config, "collection")["max_steps"]),
        )
        for route in routes
        for seed in seeds
    ]
    summary.update(
        {
            "source_manifest": str(manifest_path),
            "source_manifest_sha256": source["manifest_sha256"],
            "split_freeze_sha256": source["split_freeze_sha256"],
            "base_native_config_sha256": base["sha256"],
            "verified_base_asset_count": len(verified_assets),
            "runner_factory": build_native_arm_runner.__name__,
            "validated_run_config_count": len(run_configs),
            "execution_arm": "camp",
            "execute_train_mode_available": True,
        }
    )
    return summary


def execute_train_corpus(
    config_path: Path, output_dir: Path, *, device: str
) -> dict[str, Any]:
    run_static_preflight(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = _mapping(config, "source_split")
    manifest = json.loads(
        Path(str(source["manifest_path"])).read_text(encoding="utf-8")
    )
    base = _mapping(config, "base_native_config")
    base_config = json.loads(
        Path(str(base["path"])).read_text(encoding="utf-8")
    )
    train = _mapping(_mapping(manifest, "splits"), "train")
    routes = sorted(train.get("routes", []), key=lambda item: item["identity_sha256"])
    seeds = sorted(int(value) for value in train.get("seed_namespace", []))
    if not routes or not seeds:
        raise ValueError("frozen train split must contain routes and seeds")
    first_config = build_corpus_run_config(
        base_config,
        routes[0],
        seed=seeds[0],
        max_steps=int(_mapping(config, "collection")["max_steps"]),
    )
    run_arm = build_native_arm_runner(first_config, device=device)
    return execute_train_manifest(
        config,
        manifest,
        base_config,
        output_dir=output_dir,
        run_arm=run_arm,
    )


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= set("0123456789abcdef")
    )


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
    parser.add_argument(
        "--mode",
        choices=("static-preflight", "execute-train"),
        default="static-preflight",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    if args.mode == "execute-train":
        if args.output is None:
            parser.error("--output is required for execute-train")
        summary = execute_train_corpus(args.config, args.output, device=args.device)
    else:
        if args.output is not None:
            parser.error("--output is only valid for execute-train")
        summary = run_static_preflight(args.config)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
