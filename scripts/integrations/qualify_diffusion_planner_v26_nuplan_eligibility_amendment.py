"""Materialize the zero-model V26 nuPlan eligibility amendment manifest.

This entry deliberately reads only official source identity, timestamps, map
topology, route geometry, and traffic-signal applicability metadata.  It does
not construct a DP input, candidate pool, label, trajectory, or endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_nuplan_eligibility import (  # noqa: E402
    V26NuPlanEligibilityError,
    build_v26_eligibility_manifest,
    qualify_saved_state_history_window,
    qualify_v26_authoritative_route,
)
from camp_core.integrations.nuplan_causal_adapter import (  # noqa: E402
    NuPlanCausalSourceError,
    load_nuplan_route_snapshot,
)


CITY_MAP_FAMILY = {
    "boston": "us-ma-boston",
    "pittsburgh": "us-pa-pittsburgh-hazelwood",
    "singapore": "sg-one-north",
}
DEFAULT_CITIES = frozenset({"boston", "pittsburgh"})
DEFAULT_PARTITIONS = frozenset({"train_iid", "val_iid"})
SCHEMA_VERSION = "camp_dp_v26_nuplan_eligibility_amendment_manifest_v1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("frozen result-blind plan must be a JSON object")
    return value


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def _map_path(maps_root: Path, city: str) -> Path:
    family = CITY_MAP_FAMILY[str(city)]
    candidates = sorted((maps_root / family).glob("*/map.gpkg"))
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"official nuPlan maps need exactly one map.gpkg for {city}: {candidates}"
        )
    return candidates[0]


def _source_db_path(anchor: Mapping[str, Any], raw_root: Path) -> Path:
    relative = Path(str(anchor["raw_db_relative_path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("frozen raw DB relative path escaped raw root")
    path = (raw_root / relative).resolve()
    if raw_root.resolve() not in path.parents or not path.is_file():
        raise FileNotFoundError(f"frozen source DB is absent: {path}")
    return path


def _route_failure(error: Exception) -> dict[str, Any]:
    if isinstance(error, V26NuPlanEligibilityError):
        failure_class = error.failure_class
    else:
        failure_class = "ineligible_source_geometry"
    return {
        "schema": SCHEMA_VERSION,
        "kind": "authoritative_route_qualification",
        "eligible": False,
        "classification": failure_class,
        "reason": str(error),
    }


def qualify_anchor(
    *,
    anchor: Mapping[str, Any],
    raw_root: Path,
    maps_root: Path,
) -> dict[str, Any]:
    """Return only source eligibility/applicability records for one anchor."""

    anchor_id = str(anchor["anchor_id"])
    db_path = _source_db_path(anchor, raw_root)
    history = qualify_saved_state_history_window(
        db_path=db_path,
        state_token=str(anchor["state_token"]),
    )
    if not bool(history["eligible"]):
        return {
            "anchor_id": anchor_id,
            "history": history,
            "route": {
                "schema": SCHEMA_VERSION,
                "kind": "authoritative_route_qualification",
                "eligible": True,
                "classification": "not_evaluated_after_history_prefilter",
            },
            "signal": {
                "schema": SCHEMA_VERSION,
                "kind": "signal_presence_phase_applicability",
                "status": "not_evaluated_after_history_prefilter",
            },
        }
    try:
        snapshot = load_nuplan_route_snapshot(
            db_path=db_path,
            map_path=_map_path(maps_root, str(anchor["city"])),
            lidar_pc_token=str(anchor["state_token"]),
        )
        route = qualify_v26_authoritative_route(
            route_lanes=snapshot.route_lanes,
            route_lane_mapping=snapshot.route_lane_mapping,
            mission_roadblock_chain=snapshot.route_roadblock_ids,
        )
        route["adapter_legacy_constraint_diagnostics"] = dict(
            snapshot.legacy_constraint_diagnostics
        )
        signal = {
            "schema": SCHEMA_VERSION,
            "kind": "signal_presence_phase_applicability",
            "signal_presence": (
                "present" if snapshot.traffic_signal_present else "absent"
            ),
            "same_tick_phase_availability": (
                "available"
                if snapshot.same_tick_traffic_light_phase_available
                else ("unavailable" if snapshot.traffic_signal_present else "not_applicable")
            ),
            "red_light_capability": (
                "typed_missing_mask"
                if snapshot.traffic_signal_present
                else "not_applicable_mask"
            ),
        }
    except (NuPlanCausalSourceError, V26NuPlanEligibilityError, FileNotFoundError) as error:
        route = _route_failure(error)
        signal = {
            "schema": SCHEMA_VERSION,
            "kind": "signal_presence_phase_applicability",
            "status": "not_evaluated_after_route_failure",
        }
    return {"anchor_id": anchor_id, "history": history, "route": route, "signal": signal}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--maps-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--cities", nargs="+", default=sorted(DEFAULT_CITIES))
    parser.add_argument("--partitions", nargs="+", default=sorted(DEFAULT_PARTITIONS))
    return parser


def run(args: argparse.Namespace) -> Path:
    plan_path = args.plan.resolve(strict=True)
    raw_root = args.raw_root.resolve(strict=True)
    maps_root = args.maps_root.resolve(strict=True)
    output_root = args.output_root.resolve(strict=False)
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(output_root)
    actual_plan_sha256 = _sha256_file(plan_path)
    if actual_plan_sha256 != str(args.plan_sha256):
        raise ValueError("result-blind plan file SHA drifted")
    plan = _read_json(plan_path)
    plan_identity = str(plan.get("plan_sha256", ""))
    if len(plan_identity) != 64:
        raise ValueError("result-blind plan identity SHA is absent")
    cities = frozenset(str(value) for value in args.cities)
    partitions = frozenset(str(value) for value in args.partitions)
    if not cities <= set(CITY_MAP_FAMILY) or not cities:
        raise ValueError("eligibility cities are invalid")
    anchors = [
        dict(anchor)
        for anchor in plan.get("planned_anchors", ())
        if str(anchor.get("city")) in cities
        and str(anchor.get("partition")) in partitions
    ]
    if not anchors:
        raise ValueError("eligibility scope contains no frozen anchors")
    anchors.sort(key=lambda value: str(value["anchor_id"]))
    if len({str(anchor["anchor_id"]) for anchor in anchors}) != len(anchors):
        raise ValueError("eligibility scope has duplicate frozen anchor IDs")
    records = [
        qualify_anchor(anchor=anchor, raw_root=raw_root, maps_root=maps_root)
        for anchor in anchors
    ]
    manifest = build_v26_eligibility_manifest(
        plan_sha256=plan_identity,
        anchor_records=records,
    )
    result = {
        **manifest,
        "receipt_schema": SCHEMA_VERSION,
        "evidence_role": "development_nonholdout_nuplan_eligibility_amendment",
        "result_blind_plan_file_sha256": actual_plan_sha256,
        "scope": {"cities": sorted(cities), "partitions": sorted(partitions)},
        "raw_source_policy": "timestamp_map_route_signal_identity_only_no_pool_or_outcome",
        "payload_read": False,
        "model_call_count": 0,
        "dp_call_count": 0,
        "gpu_call_count": 0,
        "pool_generation_count": 0,
    }
    output_root.mkdir(parents=True)
    _atomic_write_json(output_root / "eligibility_manifest.json", result)
    _atomic_write_json(
        output_root / "run.exit.json",
        {
            "status": "complete",
            "eligibility_manifest_sha256": result["eligibility_manifest_sha256"],
            "planned_count": result["planned_count"],
            "eligible_count": result["eligible_count"],
            "excluded_count": result["excluded_count"],
            "model_call_count": 0,
            "dp_call_count": 0,
            "gpu_call_count": 0,
            "pool_generation_count": 0,
        },
    )
    return output_root


def main() -> int:
    output_root = run(build_parser().parse_args())
    print(output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
