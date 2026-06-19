#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_observable_state_inventory import (  # noqa: E402
    REJECT_STATUS as INVENTORY_REJECT_STATUS,
)


READY_STATUS = "observable_state_logging_preflight_design_ready"
REJECT_STATUS = "observable_state_logging_preflight_design_rejected"
SOURCE_BLOCKED_STATUS = "observable_state_logging_preflight_source_not_rejected"

INVENTORY_REQUIRED_BOTTLENECK = "missing_logged_candidate_state"

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


@dataclass(frozen=True)
class FieldSpec:
    name: str
    family: str
    shape: str
    dtype: str
    source: str
    derivation: str
    finite_check: str
    latency_bucket: str
    atomization: str
    convexity_note: str
    candidate_level: bool = True
    default_off: bool = True
    selection_effect: bool = False
    uses_future_outcomes: bool = False
    requires_dp_modification: bool = False


@dataclass(frozen=True)
class SourceHook:
    name: str
    file_role: str
    required_tokens: tuple[str, ...]
    rationale: str


FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        name="candidate_route_segment_index",
        family="candidate_lane_topology",
        shape="[K,H_support]",
        dtype="int32",
        source="candidates[:, :H_support, :2] + route_centerline in ego frame",
        derivation=(
            "nearest route-centerline segment index for each candidate support "
            "point; this is a route-topology proxy, not a Lanelet ID"
        ),
        finite_check="all indices in [0, num_route_segments)",
        latency_bucket="latency_ms_observable_state_route_topology",
        atomization=(
            "summaries such as segment span, monotonicity deficit, or support "
            "envelope excess may become fixed nonnegative candidate atoms"
        ),
        convexity_note=(
            "segment indices are discrete logged descriptors; any downstream "
            "atom is a fixed coefficient and does not make the master nonlinear"
        ),
    ),
    FieldSpec(
        name="candidate_route_projection_s_m",
        family="candidate_lane_topology",
        shape="[K,H_support]",
        dtype="float32",
        source="candidates[:, :H_support, :2] + route_centerline in ego frame",
        derivation="arc-length projection of candidate support points onto the route",
        finite_check="finite projection values and nonnegative per-candidate max span",
        latency_bucket="latency_ms_observable_state_route_topology",
        atomization=(
            "progress shortfall, reverse-motion hinge, or support-span deficit "
            "can be fixed nonnegative candidate atoms"
        ),
        convexity_note=(
            "projection summaries are computed before selection; CAMP score "
            "remains affine in weights"
        ),
    ),
    FieldSpec(
        name="candidate_route_lateral_error_m",
        family="candidate_lane_topology",
        shape="[K,H_support]",
        dtype="float32",
        source="candidates[:, :H_support, :2] + route_centerline in ego frame",
        derivation="signed or absolute lateral distance to nearest route segment",
        finite_check="finite values and finite per-candidate max/mean summaries",
        latency_bucket="latency_ms_observable_state_route_topology",
        atomization="absolute lateral envelope excess can be a nonnegative fixed atom",
        convexity_note=(
            "although the nearest-segment operation is not a trajectory-space "
            "convexity claim, the logged atom coefficient is fixed before CAMP"
        ),
    ),
    FieldSpec(
        name="candidate_red_stopline_distance_m",
        family="candidate_traffic_light_path_relation",
        shape="[K,H_tl]",
        dtype="float32",
        source="candidates[:, :H_tl, :2] + red_route_points_from_scene(scene, ego_id)",
        derivation=(
            "distance from candidate support points to aligned red route points "
            "ahead of the vehicle"
        ),
        finite_check=(
            "finite when red_route_point_count > 0; empty-red scenes record "
            "null summaries plus red_route_point_count=0"
        ),
        latency_bucket="latency_ms_observable_state_traffic_light_relation",
        atomization="red approach hinge or red-distance deficit can be fixed atoms",
        convexity_note=(
            "uses current route-light state only; downstream score remains affine"
        ),
    ),
    FieldSpec(
        name="candidate_red_heading_alignment",
        family="candidate_traffic_light_path_relation",
        shape="[K,H_tl]",
        dtype="float32",
        source="candidate headings + red route point direction vectors",
        derivation="cosine alignment between candidate heading and red-light route direction",
        finite_check="finite values in [-1,1] for nonempty red route points",
        latency_bucket="latency_ms_observable_state_traffic_light_relation",
        atomization="aligned red approach severity can be a fixed nonnegative atom",
        convexity_note="fixed alignment summaries do not alter convexity in weights",
    ),
    FieldSpec(
        name="candidate_route_heading_change_rad",
        family="route_curvature_turn_context",
        shape="[K,H_turn-1]",
        dtype="float32",
        source="candidate heading vectors or postprocessed references",
        derivation="candidate heading delta over the support horizon",
        finite_check="finite wrapped heading deltas",
        latency_bucket="latency_ms_observable_state_route_turn",
        atomization="turn-severity-conditioned comfort or support hinges can be fixed atoms",
        convexity_note="heading-change summaries are fixed coefficients before optimization",
    ),
    FieldSpec(
        name="route_curvature_context_abs",
        family="route_curvature_turn_context",
        shape="[H_turn-1]",
        dtype="float32",
        source="route_centerline in ego frame",
        derivation="record-level absolute route heading change around the current ego pose",
        finite_check="finite wrapped heading deltas for available route segments",
        latency_bucket="latency_ms_observable_state_route_turn",
        atomization="may condition candidate atoms offline but is not candidate-selected alone",
        convexity_note="record-level conditioning is fixed at the tick",
        candidate_level=False,
    ),
    FieldSpec(
        name="candidate_min_obstacle_clearance_lower_bound_m",
        family="neighbor_interaction_clearance",
        shape="[K]",
        dtype="float32",
        source=(
            "compute_candidate_obstacle_clearance_diagnostics(candidates, context, "
            "candidate_obstacles=obstacles)"
        ),
        derivation="minimum current-tick predicted obstacle clearance lower bound",
        finite_check=(
            "finite for candidates with obstacles; null allowed only when no "
            "valid obstacle slots exist and must be counted separately"
        ),
        latency_bucket="latency_ms_observable_state_neighbor_clearance",
        atomization="soft clearance hinge can be a fixed nonnegative candidate atom",
        convexity_note=(
            "clearance is computed from fixed candidate and predicted obstacle "
            "geometry before outcome labels"
        ),
    ),
    FieldSpec(
        name="candidate_obstacle_slot_count",
        family="neighbor_interaction_clearance",
        shape="[K]",
        dtype="int32",
        source="candidate obstacle tensor produced from neighbor_predictions",
        derivation="number of valid predicted obstacle slots used by clearance diagnostics",
        finite_check="integer count >= 0 for every candidate",
        latency_bucket="latency_ms_observable_state_neighbor_clearance",
        atomization="diagnostic coverage guard, not a direct safety atom by default",
        convexity_note="fixed diagnostic metadata only",
    ),
)


SOURCE_HOOKS: tuple[SourceHook, ...] = (
    SourceHook(
        name="candidate_generation_available",
        file_role="replay",
        required_tokens=(
            "generate_candidate_trajectories(",
            "candidates, neighbor_predictions, turn_logits",
        ),
        rationale="the logging preflight must run after DP candidate generation",
    ),
    SourceHook(
        name="route_projection_available",
        file_role="replay",
        required_tokens=("_candidate_route_progress", "_ego_frame_xy", "route_centerline"),
        rationale="route-relative support fields need an ego-frame route centerline",
    ),
    SourceHook(
        name="red_route_points_available",
        file_role="replay",
        required_tokens=("red_route_points_from_scene", "red_route_points"),
        rationale="traffic-light path relation fields need current red route points",
    ),
    SourceHook(
        name="neighbor_prediction_available",
        file_role="replay",
        required_tokens=("_candidate_obstacles", "neighbor_predictions", "obstacles"),
        rationale="neighbor clearance fields need predicted obstacle tensors",
    ),
    SourceHook(
        name="selection_log_append_available",
        file_role="replay",
        required_tokens=("records.append", "latency_ms_", "candidate_obstacle_clearance"),
        rationale="default-off fields need a stable selection-log append site and latency slots",
    ),
    SourceHook(
        name="clearance_diagnostic_available",
        file_role="integration",
        required_tokens=(
            "compute_candidate_obstacle_clearance_diagnostics",
            "future_outcome_leakage",
            "selection_effect",
        ),
        rationale="neighbor clearance should reuse the existing no-leak diagnostic contract",
    ),
    SourceHook(
        name="route_lane_context_available",
        file_role="integration",
        required_tokens=("_route_centerline", "ego.route_lanes", "DriverAtomContext"),
        rationale="route-lane state is already available without DP retraining",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for default-off no-leak observable-state "
            "logging after the observable-state inventory rejection."
        )
    )
    parser.add_argument("--observable_state_inventory_json", type=Path, required=True)
    parser.add_argument(
        "--replay_source",
        type=Path,
        default=ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py",
    )
    parser.add_argument(
        "--integration_source",
        type=Path,
        default=ROOT / "camp_core/camp_core/integrations/diffusion_planner.py",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        inventory_report=_load_json(args.observable_state_inventory_json),
        replay_source=args.replay_source,
        integration_source=args.integration_source,
        label=args.label,
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
    *,
    inventory_report: dict[str, Any],
    replay_source: Path,
    integration_source: Path,
    label: str | None = None,
    field_specs: tuple[FieldSpec, ...] = FIELD_SPECS,
    source_hooks: tuple[SourceHook, ...] = SOURCE_HOOKS,
) -> dict[str, Any]:
    source = _source_gate(inventory_report)
    replay_text = _read_source(replay_source)
    integration_text = _read_source(integration_source)
    hook_reports = [
        _hook_report(hook, replay_text, integration_text)
        for hook in source_hooks
    ]
    field_reports = [_field_report(field) for field in field_specs]
    family_reports = _family_reports(field_reports)
    design_checks = _design_checks(field_reports, hook_reports, family_reports)
    decision = _decision(source, design_checks, family_reports)
    return {
        "analysis": {
            "name": "dp_camp_observable_state_logging_preflight_design_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "default_off_logging_only": True,
            "replay_source": str(replay_source),
            "integration_source": str(integration_source),
            "accept_criteria": {
                "source_inventory_status": INVENTORY_REJECT_STATUS,
                "source_inventory_bottleneck": INVENTORY_REQUIRED_BOTTLENECK,
                "all_required_source_hooks_found": True,
                "all_fields_default_off": True,
                "all_fields_no_outcome_leakage": True,
                "all_fields_no_selection_effect": True,
                "all_fields_no_dp_modification": True,
                "required_families": sorted(_required_families()),
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. The proposed "
                "logging fields are computed from fixed current-tick candidates, "
                "route state, traffic-light route points, and predicted neighbor "
                "state before closed-loop outcome labels are consulted. They do "
                "not affect candidate generation, feasibility, scoring, or "
                "selection. If a logged descriptor is later atomized, it is a "
                "fixed finite-candidate coefficient a_k, so CAMP scoring remains "
                "affine score_k(w)=a_k^T w and the simplex/CVaR/L2 master remains "
                "convex in w. No DP-side classical Benders decomposition, dual, "
                "or valid cut is claimed."
            ),
        },
        "source_observable_state_inventory_gate": source,
        "field_specs": field_reports,
        "family_reports": family_reports,
        "source_hook_reports": hook_reports,
        "design_checks": design_checks,
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
        "passed": status == INVENTORY_REJECT_STATUS
        and bottleneck == INVENTORY_REQUIRED_BOTTLENECK,
        "authorized_next_work": decision.get("authorized_next_work"),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
    }


def _field_report(field: FieldSpec) -> dict[str, Any]:
    payload = asdict(field)
    payload["valid_for_design"] = (
        field.default_off
        and not field.selection_effect
        and not field.uses_future_outcomes
        and not field.requires_dp_modification
    )
    return payload


def _hook_report(
    hook: SourceHook,
    replay_text: str,
    integration_text: str,
) -> dict[str, Any]:
    if hook.file_role == "replay":
        source_text = replay_text
    elif hook.file_role == "integration":
        source_text = integration_text
    else:
        raise ValueError(f"Unknown source hook file_role: {hook.file_role}")
    missing = [token for token in hook.required_tokens if token not in source_text]
    return {
        "name": hook.name,
        "file_role": hook.file_role,
        "required_tokens": list(hook.required_tokens),
        "rationale": hook.rationale,
        "found": not missing,
        "missing_tokens": missing,
    }


def _family_reports(field_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for field in field_reports:
        by_family.setdefault(str(field["family"]), []).append(field)
    result = []
    for family, fields in sorted(by_family.items()):
        result.append(
            {
                "family": family,
                "field_count": len(fields),
                "candidate_level_field_count": sum(
                    int(bool(field["candidate_level"])) for field in fields
                ),
                "valid_field_count": sum(
                    int(bool(field["valid_for_design"])) for field in fields
                ),
                "fields": [field["name"] for field in fields],
                "status": (
                    "ready"
                    if fields and all(bool(field["valid_for_design"]) for field in fields)
                    else "invalid"
                ),
            }
        )
    return result


def _design_checks(
    field_reports: list[dict[str, Any]],
    hook_reports: list[dict[str, Any]],
    family_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    required_families = _required_families()
    present_families = {str(report["family"]) for report in family_reports}
    missing_families = sorted(required_families - present_families)
    invalid_fields = [
        str(field["name"])
        for field in field_reports
        if not bool(field["valid_for_design"])
    ]
    missing_hooks = [
        str(hook["name"]) for hook in hook_reports if not bool(hook["found"])
    ]
    noncandidate_required = [
        str(report["family"])
        for report in family_reports
        if report["family"] in required_families
        and int(report["candidate_level_field_count"]) == 0
    ]
    return {
        "required_families": sorted(required_families),
        "missing_required_families": missing_families,
        "invalid_fields": invalid_fields,
        "missing_source_hooks": missing_hooks,
        "required_families_without_candidate_level_field": noncandidate_required,
        "all_fields_default_off": all(bool(field["default_off"]) for field in field_reports),
        "all_fields_no_outcome_leakage": all(
            not bool(field["uses_future_outcomes"]) for field in field_reports
        ),
        "all_fields_no_selection_effect": all(
            not bool(field["selection_effect"]) for field in field_reports
        ),
        "all_fields_no_dp_modification": all(
            not bool(field["requires_dp_modification"]) for field in field_reports
        ),
        "passed": (
            not missing_families
            and not invalid_fields
            and not missing_hooks
            and not noncandidate_required
        ),
    }


def _decision(
    source: dict[str, Any],
    checks: dict[str, Any],
    family_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        bottleneck = "source_inventory_not_missing_logged_candidate_state"
        authorized_next_work = None
        next_step = (
            "Run this design only after observable-state inventory rejects the "
            "existing logs for missing logged candidate state."
        )
    elif checks["passed"]:
        status = READY_STATUS
        bottleneck = "default_off_logging_design_ready"
        authorized_next_work = "default_off_logging_preflight_implementation_unit_tests_only"
        next_step = (
            "Implement the default-off logging preflight with unit tests, finite "
            "coverage checks, no-outcome leakage checks, and latency accounting. "
            "Replay and selector changes remain blocked until that implementation "
            "gate passes."
        )
    else:
        status = REJECT_STATUS
        bottleneck = "logging_design_incomplete"
        authorized_next_work = None
        next_step = (
            "Do not implement logging yet; fix the missing source hooks, required "
            "families, or field contracts in the design first."
        )
    return {
        "status": status,
        "primary_bottleneck": bottleneck,
        "families": [report["family"] for report in family_reports],
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": authorized_next_work,
        "next_step": next_step,
    }


def _required_families() -> set[str]:
    return {
        "candidate_lane_topology",
        "candidate_traffic_light_path_relation",
        "route_curvature_turn_context",
        "neighbor_interaction_clearance",
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Observable State Logging Preflight Design",
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
        "| Family | Fields | Candidate-Level Fields | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in report["family_reports"]:
        lines.append(
            f"| `{row['family']}` | `{row['field_count']}` | "
            f"`{row['candidate_level_field_count']}` | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "## Source Hooks",
            "",
            "| Hook | Source | Found | Missing Tokens |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in report["source_hook_reports"]:
        missing = ", ".join(f"`{token}`" for token in row["missing_tokens"])
        lines.append(
            f"| `{row['name']}` | `{row['file_role']}` | "
            f"`{row['found']}` | {missing or '`none`'} |"
        )
    lines.extend(
        [
            "",
            "## Proposed Fields",
            "",
            "| Field | Family | Shape | Latency Bucket |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in report["field_specs"]:
        lines.append(
            f"| `{row['name']}` | `{row['family']}` | "
            f"`{row['shape']}` | `{row['latency_bucket']}` |"
        )
    lines.extend(
        [
            "",
            "This is a design-only artifact. It does not train weights, change "
            "online selection, run replay, modify DP, or authorize formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _read_source(path: Path) -> str:
    if not path.exists():
        raise ValueError(f"Source file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
