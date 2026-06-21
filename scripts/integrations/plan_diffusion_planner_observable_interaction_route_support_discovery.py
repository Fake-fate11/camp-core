#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import pickle
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SOURCE_STATUS = "observable_interaction_support_preflight_current_route_rejected"
SOURCE_NEXT_WORK = "predeclare_observable_interaction_route_support_discovery_only"
REJECT_STATUS = "observable_interaction_route_support_discovery_rejected"
READY_STATUS = "observable_interaction_route_support_discovery_plan_ready"
AUTHORIZED_REJECT_NEXT_WORK = (
    "return_to_alternative_no_leak_candidate_support_or_score_family"
)
AUTHORIZED_PLAN_NEXT_WORK = (
    "observable_interaction_narrow_support_smoke_plan_review_only"
)
FORMAL_SEEDS = frozenset({11, 12, 13})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only route/support discovery after observable-interaction "
            "support preflight. It inspects existing route metadata and optional "
            "documented simulator configuration, but never runs replay."
        )
    )
    parser.add_argument("--support_preflight_json", type=Path, required=True)
    parser.add_argument("--route", type=Path, action="append", default=[])
    parser.add_argument("--route_root", type=Path, action="append", default=[])
    parser.add_argument("--sim_config", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        support_preflight_report=_read_json(args.support_preflight_json),
        routes=[*args.route, *_discover_routes(args.route_root)],
        sim_configs=args.sim_config,
        label=args.label,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_finite_json(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    support_preflight_report: dict[str, Any],
    routes: list[Path] | None = None,
    sim_configs: list[Path] | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    routes = routes or []
    sim_configs = sim_configs or []
    source = _source_gate(support_preflight_report)
    route_summaries = [_route_summary(path) for path in sorted(set(routes))]
    config_summaries = [_config_summary(path) for path in sorted(set(sim_configs))]
    evidence = _evidence_assessment(
        support_preflight_report=support_preflight_report,
        route_summaries=route_summaries,
        config_summaries=config_summaries,
    )
    candidate_proposals: list[dict[str, Any]] = []
    can_plan_smoke = bool(source["passed"] and candidate_proposals)
    can_reject = bool(source["passed"] and not candidate_proposals)
    final_status = READY_STATUS if can_plan_smoke else REJECT_STATUS
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_route_support_discovery_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "closed_loop_outcome_labels_used": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "This is a design-only route/support discovery artifact. It "
                "does not execute Diffusion Planner, inspect outcome labels, "
                "create a selector, train CAMP, or construct Benders cuts. "
                "It can only justify future current-tick finite-candidate "
                "coefficients that would preserve affine score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 convex master."
            ),
        },
        "source_gate": source,
        "route_inventory": {
            "route_count": len(route_summaries),
            "routes": route_summaries,
        },
        "sim_config_inventory": {
            "config_count": len(config_summaries),
            "configs": config_summaries,
        },
        "evidence_assessment": evidence,
        "candidate_proposals": candidate_proposals,
        "blocked_actions": {
            "run_replay_now": True,
            "new_replay": True,
            "offline_separability": True,
            "Full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "CAMP_retraining": True,
            "DP_modification": True,
            "classic_Benders_claim": True,
        },
        "final_decision": {
            "status": final_status if source["passed"] else "observable_interaction_route_support_discovery_source_not_ready",
            "passed": can_plan_smoke or can_reject,
            "observable_interaction_route_family_rejected": can_reject,
            "support_smoke_predeclared": can_plan_smoke,
            "authorized_next_work": (
                AUTHORIZED_PLAN_NEXT_WORK
                if can_plan_smoke
                else AUTHORIZED_REJECT_NEXT_WORK
                if can_reject
                else None
            ),
            "new_replay_authorized": False,
            "offline_separability_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "classic_Benders_claim_authorized": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    final = report["final_decision"]
    evidence = report["evidence_assessment"]
    lines = [
        "# Observable Interaction Route/Support Discovery",
        "",
        f"- status: `{final['status']}`",
        f"- passed: `{final['passed']}`",
        f"- route family rejected: `{final['observable_interaction_route_family_rejected']}`",
        f"- support smoke predeclared: `{final['support_smoke_predeclared']}`",
        f"- authorized next work: `{final['authorized_next_work']}`",
        "",
        "## Evidence Assessment",
        "",
        f"- can justify positive reduced red alignment: `{evidence['can_justify_positive_reduced_red_alignment']}`",
        f"- can justify 2m near clearance: `{evidence['can_justify_near_clearance_support']}`",
        f"- rejection reason: `{evidence['rejection_reason']}`",
        "",
        "## Routes",
        "",
        *_route_table(report["route_inventory"]["routes"]),
        "",
        "## Simulator Configs",
        "",
        *_config_table(report["sim_config_inventory"]["configs"]),
        "",
        "## Candidate Proposals",
        "",
        "No candidate proposals were justified from the permitted read-only inputs."
        if not report["candidate_proposals"]
        else json.dumps(report["candidate_proposals"], indent=2),
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") if isinstance(report, dict) else {}
    final = final if isinstance(final, dict) else {}
    return {
        "expected_status": SOURCE_STATUS,
        "actual_status": final.get("status"),
        "expected_authorized_next_work": SOURCE_NEXT_WORK,
        "actual_authorized_next_work": final.get("authorized_next_work"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and final.get("current_observable_interaction_route_rejected") is True
            and final.get("support_smoke_predeclared") is False
            and final.get("new_replay_authorized") is False
            and final.get("offline_separability_authorized") is False
            and final.get("CAMP_retraining_authorized") is False
        ),
    }


def _evidence_assessment(
    *,
    support_preflight_report: dict[str, Any],
    route_summaries: list[dict[str, Any]],
    config_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    rejection = support_preflight_report.get("route_rejection")
    rejection = rejection if isinstance(rejection, dict) else {}
    routes_with_map = sum(int(route.get("map_exists") is True) for route in route_summaries)
    configs_with_spawn = sum(
        int(config.get("has_spawn_configuration") is True) for config in config_summaries
    )
    can_red = False
    can_clearance = False
    reasons = []
    if int(rejection.get("red_reduced_positive_alignment_candidates") or 0) <= 0:
        reasons.append("no_existing_positive_reduced_red_alignment")
    if int(rejection.get("clearance_inside_budget_candidates") or 0) <= 0:
        reasons.append("no_existing_clearance_inside_fixed_budget")
    if routes_with_map <= 0:
        reasons.append("no_route_with_loadable_map_metadata")
    if configs_with_spawn <= 0:
        reasons.append("no_documented_spawn_configuration_supporting_near_clearance")
    return {
        "can_justify_positive_reduced_red_alignment": can_red,
        "can_justify_near_clearance_support": can_clearance,
        "routes_with_map_metadata": routes_with_map,
        "configs_with_spawn_configuration": configs_with_spawn,
        "preflight_red_reason": rejection.get("red_reason"),
        "preflight_clearance_reason": rejection.get("clearance_reason"),
        "rejection_reason": ",".join(reasons) if reasons else None,
        "explanation": (
            "The permitted read-only inputs do not prove any route/support "
            "candidate will activate both positive reduced red alignment and "
            "the fixed 2m clearance budget. Predeclaring a support smoke would "
            "therefore be a guess rather than a justified gate."
        ),
    }


def _discover_routes(roots: list[Path]) -> list[Path]:
    routes: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".pkl":
            routes.append(root)
        elif root.is_dir():
            routes.extend(sorted(root.rglob("*.pkl")))
    return routes


def _route_summary(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {"route_path": str(path), "route_exists": path.exists()}
    if not path.exists():
        return summary
    try:
        with path.open("rb") as handle:
            route = pickle.load(handle)
    except Exception as exc:  # pragma: no cover - depends on external pickle classes
        summary["route_load_error"] = f"{type(exc).__name__}: {exc}"
        return summary
    map_path = Path(str(getattr(route, "map_path", ""))) if getattr(route, "map_path", None) else None
    lanelet_ids = [int(item) for item in getattr(route, "route_lanelet_ids", [])]
    start_pose = _pose_list(getattr(route, "start_pose", None))
    goal_pose = _pose_list(getattr(route, "goal_pose", None))
    summary.update(
        {
            "map_path": str(map_path) if map_path else None,
            "map_exists": bool(map_path and map_path.exists()),
            "start_lanelet_id": _optional_int(getattr(route, "start_lanelet_id", None)),
            "goal_lanelet_id": _optional_int(getattr(route, "goal_lanelet_id", None)),
            "route_lanelet_count": len(lanelet_ids),
            "route_lanelet_ids_head": lanelet_ids[:8],
            "start_pose": start_pose,
            "goal_pose": goal_pose,
            "start_to_goal_distance_m": _pose_distance(start_pose, goal_pose),
            "start_to_goal_heading_rad": _pose_heading(start_pose, goal_pose),
            "route_start_heading_rad": start_pose[2] if len(start_pose) >= 3 else None,
            "route_goal_heading_rad": goal_pose[2] if len(goal_pose) >= 3 else None,
        }
    )
    if map_path and map_path.exists() and lanelet_ids:
        summary["map_route_relation_hits"] = _count_map_relation_hits(map_path, lanelet_ids)
    return _finite_json(summary)


def _config_summary(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {"config_path": str(path), "config_exists": path.exists()}
    if not path.exists():
        return summary
    try:
        payload = _read_json(path)
    except ValueError as exc:
        summary["config_load_error"] = str(exc)
        return summary
    text = json.dumps(payload, sort_keys=True).lower()
    summary.update(
        {
            "top_level_keys": sorted(str(key) for key in payload.keys()),
            "has_spawn_configuration": "spawn" in text or "npc" in text,
            "mentions_clearance": "clearance" in text,
            "mentions_traffic_light": "traffic" in text or "light" in text,
        }
    )
    return summary


def _count_map_relation_hits(map_path: Path, lanelet_ids: list[int]) -> int:
    targets = {str(item) for item in lanelet_ids}
    hits = 0
    try:
        for _, elem in ET.iterparse(map_path, events=("end",)):
            if elem.tag == "relation" and elem.attrib.get("id") in targets:
                hits += 1
            elem.clear()
    except ET.ParseError:
        return 0
    return hits


def _route_table(routes: list[dict[str, Any]]) -> list[str]:
    if not routes:
        return ["No route pickles were provided."]
    lines = [
        "| Route | Exists | Map | Lanelets | Map Hits | Start | Goal |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for route in routes:
        lines.append(
            "| "
            f"`{route.get('route_path')}` | "
            f"`{route.get('route_exists')}` | "
            f"`{route.get('map_exists')}` | "
            f"{route.get('route_lanelet_count', 'n/a')} | "
            f"{route.get('map_route_relation_hits', 'n/a')} | "
            f"`{route.get('start_lanelet_id')}` | "
            f"`{route.get('goal_lanelet_id')}` |"
        )
    return lines


def _config_table(configs: list[dict[str, Any]]) -> list[str]:
    if not configs:
        return ["No simulator config files were provided."]
    lines = [
        "| Config | Exists | Spawn/NPC | Clearance | Traffic Light |",
        "| --- | --- | --- | --- | --- |",
    ]
    for config in configs:
        lines.append(
            "| "
            f"`{config.get('config_path')}` | "
            f"`{config.get('config_exists')}` | "
            f"`{config.get('has_spawn_configuration')}` | "
            f"`{config.get('mentions_clearance')}` | "
            f"`{config.get('mentions_traffic_light')}` |"
        )
    return lines


def _pose_list(value: Any) -> list[float]:
    if value is None:
        return []
    try:
        return [float(item) for item in value]
    except TypeError:
        return []


def _pose_distance(start: list[float], goal: list[float]) -> float | None:
    if len(start) < 2 or len(goal) < 2:
        return None
    return math.hypot(goal[0] - start[0], goal[1] - start[1])


def _pose_heading(start: list[float], goal: list[float]) -> float | None:
    if len(start) < 2 or len(goal) < 2:
        return None
    return math.atan2(goal[1] - start[1], goal[0] - start[0])


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _finite_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _finite_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_finite_json(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    main()
