#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _validate_scenario_buckets,
)


BENCHMARK_FIELDS = (
    "route",
    "route_name",
    "seed",
    "steps",
    "max_npcs",
    "spawn_probability",
    "traffic_lights",
    "advance_mode",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an explicit-only scenario bucket manifest skeleton from a "
            "DP-CAMP SafetyCost comparison JSON. The tool never infers critical "
            "labels from metrics; optional labels must be supplied explicitly."
        )
    )
    parser.add_argument("--comparison_json", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument(
        "--include_run_keys",
        action="store_true",
        help="Include every run key in manifest['run_keys'] with empty labels.",
    )
    parser.add_argument(
        "--route_bucket",
        type=_parse_bucket_assignment,
        action="append",
        default=[],
        metavar="ROUTE=BUCKET[,BUCKET]",
        help="Explicit route labels after route inspection. May repeat.",
    )
    parser.add_argument(
        "--run_key_bucket",
        type=_parse_bucket_assignment,
        action="append",
        default=[],
        metavar="RUN_KEY=BUCKET[,BUCKET]",
        help="Explicit exact-run labels after scenario inspection. May repeat.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison = _read_json(args.comparison_json)
    manifest = build_manifest(
        comparison,
        comparison_path=args.comparison_json,
        include_run_keys=args.include_run_keys,
        route_bucket_assignments=dict(args.route_bucket),
        run_key_bucket_assignments=dict(args.run_key_bucket),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(_summary(manifest), indent=2, sort_keys=True))


def build_manifest(
    comparison: dict[str, Any],
    *,
    comparison_path: Path | None = None,
    include_run_keys: bool = False,
    route_bucket_assignments: dict[str, list[str]] | None = None,
    run_key_bucket_assignments: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    rows = comparison.get("runs")
    if not isinstance(rows, list) or not rows:
        raise ValueError("comparison JSON must contain a nonempty runs list.")
    route_bucket_assignments = route_bucket_assignments or {}
    run_key_bucket_assignments = run_key_bucket_assignments or {}
    _validate_assignment_buckets(route_bucket_assignments)
    _validate_assignment_buckets(run_key_bucket_assignments)

    route_names = sorted({_route_name(row) for row in rows})
    run_keys = sorted({str(row.get("run_key")) for row in rows})
    unknown_routes = sorted(set(route_bucket_assignments) - set(route_names))
    if unknown_routes:
        raise ValueError(f"Route label(s) not present in comparison: {unknown_routes}")
    unknown_run_keys = sorted(set(run_key_bucket_assignments) - set(run_keys))
    if unknown_run_keys:
        raise ValueError(
            f"Run-key label(s) not present in comparison: {unknown_run_keys}"
        )

    route_manifest = {
        route_name: list(route_bucket_assignments.get(route_name, []))
        for route_name in route_names
    }
    run_key_manifest = {
        run_key: list(run_key_bucket_assignments.get(run_key, []))
        for run_key in (run_keys if include_run_keys else run_key_bucket_assignments)
    }
    metadata_by_run_key = _run_key_metadata(rows)
    unlabeled_routes = [
        route for route, buckets in route_manifest.items() if not buckets
    ]
    unlabeled_run_keys = [
        run_key
        for run_key in run_keys
        if not run_key_manifest.get(run_key)
        and not route_manifest.get(str(metadata_by_run_key[run_key].get("route_name")))
    ]
    return {
        "metadata": {
            "schema_version": "dp_camp_scenario_buckets_v1",
            "source_comparison_json": (
                None if comparison_path is None else str(comparison_path)
            ),
            "generated_from": "dp_camp_safety_cost_comparison_json",
            "explicit_labeling_only": True,
            "labels_are_not_inferred_from_metrics": True,
            "route_count": len(route_names),
            "run_key_count": len(run_keys),
            "variant_count": len({str(row.get("variant")) for row in rows}),
            "inspection_required_before_claims": True,
        },
        "supported_buckets": sorted(SUPPORTED_SCENARIO_BUCKETS),
        "routes": route_manifest,
        "run_keys": run_key_manifest,
        "default_buckets": [],
        "unlabeled_routes": unlabeled_routes,
        "unlabeled_run_keys": unlabeled_run_keys,
        "run_key_metadata": metadata_by_run_key,
    }


def _run_key_metadata(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        run_key = str(row.get("run_key"))
        entry = {field: row.get(field) for field in BENCHMARK_FIELDS}
        entry["route_name"] = _route_name(row)
        if run_key in metadata and metadata[run_key] != entry:
            raise ValueError(f"Conflicting metadata for run key: {run_key}")
        metadata[run_key] = entry
    return {key: metadata[key] for key in sorted(metadata)}


def _route_name(row: dict[str, Any]) -> str:
    route_name = row.get("route_name")
    if route_name is not None:
        return str(route_name)
    route = row.get("route")
    if route is not None:
        return Path(str(route)).stem
    raise ValueError(f"Run row is missing route_name and route: {row}")


def _parse_bucket_assignment(value: str) -> tuple[str, list[str]]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "bucket assignment must have the form KEY=BUCKET[,BUCKET]"
        )
    key, raw_buckets = value.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError("bucket assignment key must be nonempty")
    buckets = [bucket.strip() for bucket in raw_buckets.split(",") if bucket.strip()]
    if not buckets:
        raise argparse.ArgumentTypeError("bucket assignment must include a bucket")
    try:
        _validate_scenario_buckets(buckets)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return key, buckets


def _validate_assignment_buckets(assignments: dict[str, list[str]]) -> None:
    for key, buckets in assignments.items():
        if not isinstance(key, str):
            raise ValueError("bucket assignment keys must be strings.")
        _validate_scenario_buckets(buckets)


def _summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": manifest["metadata"]["schema_version"],
        "route_count": manifest["metadata"]["route_count"],
        "run_key_count": manifest["metadata"]["run_key_count"],
        "unlabeled_route_count": len(manifest["unlabeled_routes"]),
        "unlabeled_run_key_count": len(manifest["unlabeled_run_keys"]),
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
