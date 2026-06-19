#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (  # noqa: E402
    FORMAL_SEEDS,
    _log_context,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)


READY_STATUS = "observable_state_inventory_has_new_logged_state"
REJECT_STATUS = "observable_state_inventory_missing_new_logged_state"
SOURCE_BLOCKED_STATUS = "observable_state_inventory_source_not_rejected"
FORMAL_SEED_STATUS = "observable_state_inventory_formal_seed_conflict"

SOURCE_REQUIRED_STATUS = "candidate_set_observable_support_rejected"
SOURCE_REQUIRED_BOTTLENECK = "missing_observable_state_or_descriptor_information"

MIN_COMPLETE_RECORD_RATE = 0.95
MIN_NEW_CANDIDATE_STATE_FAMILIES = 1

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


@dataclass(frozen=True)
class Probe:
    family: str
    name: str
    path: str
    role: str
    candidate_level: bool
    description: str


PROBES: tuple[Probe, ...] = (
    Probe(
        "candidate_lane_topology",
        "candidate_lanelet_ids",
        "candidate_lanelet_ids",
        "new_candidate_state",
        True,
        "candidate-specific lanelet or route-lane identifiers",
    ),
    Probe(
        "candidate_lane_topology",
        "candidate_lane_ids",
        "candidate_lane_ids",
        "new_candidate_state",
        True,
        "candidate-specific lane identifiers",
    ),
    Probe(
        "candidate_lane_topology",
        "candidate_route_lane_ids",
        "candidate_route_lane_ids",
        "new_candidate_state",
        True,
        "candidate-specific route-lane identifiers",
    ),
    Probe(
        "candidate_lane_topology",
        "candidate_lane_sequence",
        "candidate_lane_sequence",
        "new_candidate_state",
        True,
        "candidate lane sequence or lane-change topology",
    ),
    Probe(
        "candidate_traffic_light_path_relation",
        "candidate_traffic_light_state",
        "candidate_traffic_light_state",
        "new_candidate_state",
        True,
        "candidate-specific traffic-light state on the path",
    ),
    Probe(
        "candidate_traffic_light_path_relation",
        "candidate_red_light_distance_m",
        "candidate_red_light_distance_m",
        "new_candidate_state",
        True,
        "candidate-specific distance to red stop line or red route point",
    ),
    Probe(
        "candidate_traffic_light_path_relation",
        "candidate_tl_stopline_distance_m",
        "candidate_tl_stopline_distance_m",
        "new_candidate_state",
        True,
        "candidate-specific traffic-light stop-line distance",
    ),
    Probe(
        "route_curvature_turn_context",
        "candidate_route_curvature",
        "candidate_route_curvature",
        "new_candidate_state",
        True,
        "candidate-specific route curvature",
    ),
    Probe(
        "route_curvature_turn_context",
        "candidate_turn_angle_rad",
        "candidate_turn_angle_rad",
        "new_candidate_state",
        True,
        "candidate-specific heading or turn-angle context",
    ),
    Probe(
        "route_curvature_turn_context",
        "route_heading_change_rad",
        "route_heading_change_rad",
        "new_record_state",
        False,
        "record-level route heading change before candidate selection",
    ),
    Probe(
        "neighbor_interaction_clearance",
        "candidate_obstacle_clearance",
        "candidate_obstacle_clearance",
        "new_candidate_state",
        True,
        "candidate-specific obstacle clearance computed before outcomes",
    ),
    Probe(
        "neighbor_interaction_clearance",
        "candidate_neighbor_clearance_m",
        "candidate_neighbor_clearance_m",
        "new_candidate_state",
        True,
        "candidate-specific neighbor clearance",
    ),
    Probe(
        "neighbor_interaction_clearance",
        "candidate_time_to_collision_s",
        "candidate_time_to_collision_s",
        "new_candidate_state",
        True,
        "candidate-specific time-to-collision proxy",
    ),
    Probe(
        "reward_context_tensors",
        "reward_input_route_lanes",
        "reward_input__route_lanes",
        "new_record_state",
        False,
        "raw route-lane reward tensor snapshot",
    ),
    Probe(
        "reward_context_tensors",
        "reward_input_neighbor_future",
        "reward_input__neighbor_agents_future",
        "new_record_state",
        False,
        "raw neighbor future reward tensor snapshot",
    ),
    Probe(
        "reward_context_tensors",
        "reward_input_traffic_lights",
        "reward_input__traffic_lights",
        "new_record_state",
        False,
        "raw traffic-light reward tensor snapshot",
    ),
    Probe(
        "existing_shape_support_proxy",
        "top1_shape_deviation",
        "candidate_dp_prior_deviation_cost",
        "existing_candidate_proxy",
        True,
        "already audited Top-1 shape deviation proxy",
    ),
    Probe(
        "existing_shape_support_proxy",
        "step_reach",
        "candidate_step_reach",
        "existing_candidate_proxy",
        True,
        "already audited step-reach support proxy",
    ),
    Probe(
        "existing_comfort_proxy",
        "perfect_tracker_lateral",
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
        "existing_candidate_proxy",
        True,
        "already audited candidate lateral comfort proxy",
    ),
    Probe(
        "existing_comfort_proxy",
        "perfect_tracker_jerk",
        "candidate_perfect_tracker_jerk_magnitude_mps3",
        "existing_candidate_proxy",
        True,
        "already audited candidate jerk proxy",
    ),
    Probe(
        "existing_traffic_proxy",
        "planned_red_cost",
        "candidate_horizon_union_planned_red_light_cost",
        "existing_candidate_proxy",
        True,
        "already audited planned red-light cost",
    ),
    Probe(
        "existing_traffic_proxy",
        "red_stopping_margin",
        "candidate_red_stopping_margin_cost",
        "existing_candidate_proxy",
        True,
        "already audited red-stopping margin cost",
    ),
    Probe(
        "dp_reward_lane_proxy",
        "dp_reward_centerline",
        "dp_candidate_rewards.centerline",
        "existing_candidate_proxy",
        True,
        "DP reward centerline proxy, not lane topology",
    ),
    Probe(
        "dp_reward_lane_proxy",
        "dp_reward_lane_crossing",
        "dp_candidate_rewards.lane_crossing",
        "existing_candidate_proxy",
        True,
        "DP reward lane-crossing boolean, not lane topology",
    ),
    Probe(
        "dp_reward_neighbor_proxy",
        "dp_reward_soft_collision_min_dist",
        "dp_candidate_rewards.sc_min_dist",
        "existing_candidate_proxy",
        True,
        "DP reward soft-collision minimum distance proxy",
    ),
    Probe(
        "dp_reward_neighbor_proxy",
        "dp_reward_road_boundary_min_dist",
        "dp_candidate_rewards.rb_min_dist",
        "existing_candidate_proxy",
        True,
        "DP reward road-boundary minimum distance proxy",
    ),
    Probe(
        "dp_scene_aggregate",
        "route_lanes_present",
        "dp_scene_features.route_lanes.present",
        "existing_record_proxy",
        False,
        "aggregate record-level route-lanes presence",
    ),
    Probe(
        "dp_scene_aggregate",
        "traffic_lights_present",
        "dp_scene_features.traffic_lights.present",
        "existing_record_proxy",
        False,
        "aggregate record-level traffic-light tensor presence",
    ),
    Probe(
        "dp_scene_aggregate",
        "neighbor_agents_past_present",
        "dp_scene_features.neighbor_agents_past.present",
        "existing_record_proxy",
        False,
        "aggregate record-level neighbor history presence",
    ),
    Probe(
        "scenario_bucket_context",
        "scenario_buckets",
        "context.scenario_buckets",
        "diagnostic_only",
        False,
        "offline scenario bucket labels, not a candidate selector feature",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory which no-leak current-tick state fields are already "
            "logged after the candidate-set observable-support rejection."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--candidate_set_support_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--min_complete_record_rate", type=float, default=MIN_COMPLETE_RECORD_RATE)
    parser.add_argument(
        "--min_new_candidate_state_families",
        type=int,
        default=MIN_NEW_CANDIDATE_STATE_FAMILIES,
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        candidate_set_support_report=_load_json(args.candidate_set_support_json),
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
        min_complete_record_rate=args.min_complete_record_rate,
        min_new_candidate_state_families=args.min_new_candidate_state_families,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(
    paths: list[Path],
    *,
    candidate_set_support_report: dict[str, Any],
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    min_complete_record_rate: float = MIN_COMPLETE_RECORD_RATE,
    min_new_candidate_state_families: int = MIN_NEW_CANDIDATE_STATE_FAMILIES,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {index} must be an object.")
            items.append({"raw": raw, "context": {**context, "record_index": index}})
    return analyze_records(
        items,
        candidate_set_support_report=candidate_set_support_report,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        fail_on_formal_seeds=fail_on_formal_seeds,
        min_complete_record_rate=min_complete_record_rate,
        min_new_candidate_state_families=min_new_candidate_state_families,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    candidate_set_support_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    fail_on_formal_seeds: bool = False,
    probes: tuple[Probe, ...] = PROBES,
    min_complete_record_rate: float = MIN_COMPLETE_RECORD_RATE,
    min_new_candidate_state_families: int = MIN_NEW_CANDIDATE_STATE_FAMILIES,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    if not 0.0 <= min_complete_record_rate <= 1.0:
        raise ValueError("min_complete_record_rate must be in [0, 1].")
    if min_new_candidate_state_families < 0:
        raise ValueError("min_new_candidate_state_families must be nonnegative.")
    source = _source_gate(candidate_set_support_report)
    formal_seed_records = sum(int(_is_formal_seed(item["context"])) for item in items)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    probe_reports = [
        _probe_report(probe, items)
        for probe in probes
    ]
    family_reports = _family_reports(probe_reports, min_complete_record_rate)
    decision = _decision(
        source,
        family_reports,
        formal_seed_records=formal_seed_records,
        min_new_candidate_state_families=min_new_candidate_state_families,
    )
    return {
        "analysis": {
            "name": "dp_camp_observable_state_inventory_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_inspected": False,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "min_complete_record_rate": float(min_complete_record_rate),
            "min_new_candidate_state_families": int(min_new_candidate_state_families),
            "accept_criteria": {
                "source_gate": (
                    f"{SOURCE_REQUIRED_STATUS} with primary bottleneck "
                    f"{SOURCE_REQUIRED_BOTTLENECK}"
                ),
                "new_candidate_state_family_count": (
                    f">= {min_new_candidate_state_families}"
                ),
                "family_complete_record_rate": f">= {min_complete_record_rate}",
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. This audit "
                "only inventories fields logged before closed-loop outcome "
                "labels are consulted. It does not construct selection features "
                "from outcomes and does not change online behavior. If a future "
                "logged field is atomized, it is a fixed finite-candidate "
                "coefficient a_k, so CAMP scoring remains affine score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 master remains convex in w. No DP-side "
                "classical Benders decomposition, dual, or valid cut is claimed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_candidate_set_support_gate": source,
        "records": _record_summary(items, formal_seed_records),
        "probe_reports": probe_reports,
        "family_reports": family_reports,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    bottleneck = decision.get("primary_bottleneck")
    return {
        "status": status,
        "primary_bottleneck": bottleneck,
        "passed": (
            status == SOURCE_REQUIRED_STATUS
            and bottleneck == SOURCE_REQUIRED_BOTTLENECK
        ),
        "authorized_next_work": decision.get("authorized_next_work"),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
    }


def _probe_report(probe: Probe, items: list[dict[str, Any]]) -> dict[str, Any]:
    records_present = 0
    records_complete = 0
    usable_candidate_values = 0
    candidate_values = 0
    examples: list[str] = []
    for item in items:
        raw = item["raw"]
        context = item["context"]
        candidate_count = _candidate_count(raw)
        values = _probe_values(raw, context, probe.path)
        usable = [_is_usable(value) for value in values]
        present = bool(values and any(usable))
        complete = present
        if probe.candidate_level:
            candidate_values += candidate_count
            usable_candidate_values += sum(usable[:candidate_count])
            complete = len(values) >= candidate_count and all(usable[:candidate_count])
        if present:
            records_present += 1
            if len(examples) < 3:
                examples.append(_example_value(values))
        if complete:
            records_complete += 1
    total = max(len(items), 1)
    candidate_total = max(candidate_values, 1)
    return {
        "family": probe.family,
        "name": probe.name,
        "path": probe.path,
        "role": probe.role,
        "candidate_level": probe.candidate_level,
        "description": probe.description,
        "records_total": len(items),
        "records_present": records_present,
        "record_present_rate": records_present / total,
        "records_complete": records_complete,
        "record_complete_rate": records_complete / total,
        "candidate_values_total": candidate_values,
        "usable_candidate_values": usable_candidate_values,
        "usable_candidate_value_rate": usable_candidate_values / candidate_total,
        "examples": examples,
    }


def _family_reports(
    probe_reports: list[dict[str, Any]],
    min_complete_record_rate: float,
) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for report in probe_reports:
        by_family.setdefault(str(report["family"]), []).append(report)
    result = []
    for family, reports in sorted(by_family.items()):
        best = max(
            reports,
            key=lambda report: (
                float(report["record_complete_rate"]),
                float(report["record_present_rate"]),
                str(report["name"]),
            ),
        )
        roles = sorted({str(report["role"]) for report in reports})
        candidate_level = any(bool(report["candidate_level"]) for report in reports)
        complete_rate = float(best["record_complete_rate"])
        present_rate = float(best["record_present_rate"])
        if complete_rate >= min_complete_record_rate:
            status = "available"
        elif present_rate > 0.0:
            status = "partial"
        else:
            status = "missing"
        result.append(
            {
                "family": family,
                "roles": roles,
                "candidate_level": candidate_level,
                "status": status,
                "best_probe": best["name"],
                "best_path": best["path"],
                "best_record_complete_rate": complete_rate,
                "best_record_present_rate": present_rate,
                "probes": reports,
            }
        )
    return result


def _decision(
    source: dict[str, Any],
    family_reports: list[dict[str, Any]],
    *,
    formal_seed_records: int,
    min_new_candidate_state_families: int,
) -> dict[str, Any]:
    available_new_candidate = [
        report
        for report in family_reports
        if "new_candidate_state" in report["roles"]
        and report["candidate_level"]
        and report["status"] == "available"
    ]
    partial_new_candidate = [
        report
        for report in family_reports
        if "new_candidate_state" in report["roles"]
        and report["candidate_level"]
        and report["status"] == "partial"
    ]
    available_existing = [
        report
        for report in family_reports
        if any(str(role).startswith("existing_") for role in report["roles"])
        and report["status"] == "available"
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        bottleneck = "source_gate_not_candidate_support_rejection"
        next_step = (
            "Run this inventory only after candidate-set observable support is "
            "rejected for missing observable state or descriptor information."
        )
        authorized_next_work = None
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        bottleneck = "formal_seed_conflict"
        next_step = "Exclude formal seeds before using this inventory as evidence."
        authorized_next_work = None
    elif len(available_new_candidate) >= min_new_candidate_state_families:
        status = READY_STATUS
        bottleneck = "new_candidate_state_available"
        next_step = (
            "Design an offline separability audit over the newly logged "
            "candidate-state families only; replay, online selector promotion, "
            "formal seeds, and retraining remain blocked."
        )
        authorized_next_work = "offline_new_descriptor_separability_audit_design_only"
    else:
        status = REJECT_STATUS
        bottleneck = "missing_logged_candidate_state"
        if partial_new_candidate:
            next_step = (
                "Existing logs contain only partial new candidate-state fields. "
                "Design a default-off logging preflight with complete candidate "
                "coverage before another descriptor or weight screen."
            )
        else:
            next_step = (
                "Existing logs expose only previously audited aggregate or reward "
                "proxy fields. Design a default-off logging preflight for "
                "candidate lane topology, traffic-light path relation, route "
                "curvature/turn context, and neighbor interaction state."
            )
        authorized_next_work = "default_off_logging_preflight_design_only"
    return {
        "status": status,
        "primary_bottleneck": bottleneck,
        "available_new_candidate_state_families": [
            report["family"] for report in available_new_candidate
        ],
        "partial_new_candidate_state_families": [
            report["family"] for report in partial_new_candidate
        ],
        "available_existing_proxy_families": [
            report["family"] for report in available_existing
        ],
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": authorized_next_work,
        "next_step": next_step,
    }


def _probe_values(raw: dict[str, Any], context: dict[str, Any], path: str) -> list[Any]:
    if path.startswith("dp_candidate_rewards."):
        field = path.split(".", 1)[1]
        rewards = raw.get("dp_candidate_rewards")
        if not isinstance(rewards, list):
            return []
        return [
            reward.get(field)
            for reward in rewards
            if isinstance(reward, dict)
        ]
    if path.startswith("dp_scene_features."):
        feature_name = path.split(".", 1)[1]
        names = raw.get("dp_scene_feature_names")
        values = raw.get("dp_scene_features")
        if not isinstance(names, list) or not isinstance(values, list):
            return []
        try:
            index = names.index(feature_name)
        except ValueError:
            return []
        if index >= len(values):
            return []
        return [values[index]]
    if path.startswith("context."):
        key = path.split(".", 1)[1]
        value = context.get(key)
    else:
        value = raw.get(path)
    if isinstance(value, list):
        return value
    return [value] if value is not None else []


def _candidate_count(raw: dict[str, Any]) -> int:
    for key in ("num_candidates", "candidate_count"):
        value = raw.get(key)
        if isinstance(value, int) and value > 0:
            return int(value)
    feasible = raw.get("feasible_mask")
    if isinstance(feasible, list) and feasible:
        return len(feasible)
    atoms = raw.get("atoms")
    if isinstance(atoms, list) and atoms:
        return len(atoms)
    raise ValueError("Selection record does not expose candidate count.")


def _is_usable(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, str):
        return bool(value)
    if isinstance(value, dict):
        return any(_is_usable(inner) for inner in value.values())
    if isinstance(value, list):
        return any(_is_usable(inner) for inner in value)
    return True


def _example_value(values: list[Any]) -> str:
    for value in values:
        if _is_usable(value):
            text = repr(value)
            return text[:120] + ("..." if len(text) > 120 else "")
    return "None"


def _record_summary(items: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    candidate_counts = [_candidate_count(item["raw"]) for item in items]
    return {
        "logs": len({item["context"].get("log_path") for item in items}),
        "total": len(items),
        "candidate_rows": int(sum(candidate_counts)),
        "candidate_count_values": sorted(set(candidate_counts)),
        "formal_seed_records": int(formal_seed_records),
    }


def _is_formal_seed(context: dict[str, Any]) -> bool:
    if "formal_seed" in context:
        return bool(context["formal_seed"])
    seed = context.get("seed")
    try:
        return int(seed) in FORMAL_SEEDS
    except (TypeError, ValueError):
        return False


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Observable State Inventory Audit",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Primary bottleneck: `{decision['primary_bottleneck']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Families",
        "",
        "| Family | Roles | Status | Best Probe | Complete | Present |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for row in report["family_reports"]:
        lines.append(
            f"| `{row['family']}` | `{','.join(row['roles'])}` | "
            f"`{row['status']}` | `{row['best_probe']}` | "
            f"{_fmt(row['best_record_complete_rate'])} | "
            f"{_fmt(row['best_record_present_rate'])} |"
        )
    lines.extend(
        [
            "",
            "This is a no-leak field inventory only. It does not train weights, "
            "change online selection, run replay, modify DP, or authorize formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return "`n/a`"
    if not math.isfinite(result):
        return "`n/a`"
    return f"`{result:.6g}`"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
