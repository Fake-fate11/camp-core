#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCREEN_STATUS = "source_visibility_predeclaration_no_admissible_source_paused"
SCREEN_NEXT_WORK = "keep_selector_route_paused_or_submit_new_source_visibility_proposal_only"

PAUSED_STATUS = "post_source_visibility_runtime_inventory_no_new_source_paused"
CANDIDATE_STATUS = "post_source_visibility_runtime_inventory_candidate_requires_predeclaration"
BLOCKED_STATUS = "post_source_visibility_runtime_inventory_blocked"

PAUSED_NEXT_WORK = "keep_selector_route_paused_or_scenario_objective_redesign_only"
CANDIDATE_NEXT_WORK = "submit_source_visibility_predeclaration_proposal_only"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
    "atom_promotion_authorized",
)

DEFAULT_RUNTIME_CANDIDATES: tuple[dict[str, Any], ...] = (
    {
        "name": "intersection_stopline_crosswalk_map_context",
        "source_family": "route_topology",
        "runtime_evidence": [
            "scenario_generation/gui/lanelet_scene_builder.py caches intersection_area polygons",
            "scenario_generation/gui/lanelet_scene_builder.py caches stop_line and road_border line strings",
            "lanelet_to_33dim exposes lane boundary line types including crosswalk/pedestrian markings",
        ],
        "current_tick_available_before_selection": True,
        "candidate_level_or_deterministically_joinable": True,
        "finite_or_fail_closed": True,
        "deterministic": True,
        "uses_future_outcome_or_safetycost_label": False,
        "requires_dp_modification": False,
        "requires_dp_retraining": False,
        "requires_replay_to_compute_runtime_value": False,
        "requires_training_to_compute_runtime_value": False,
        "atom_value_domain": "nonnegative",
        "equivalent_closed_labels": ["route_topology", "progress_lane_hard"],
        "math_note": (
            "A pure map-context coefficient could be nonnegative and affine, "
            "but it is not a materially new source family after route topology "
            "and lane/hard-boundary gates."
        ),
    },
    {
        "name": "candidate_npc_ttc_or_conflict_zone_interaction",
        "source_family": "observable_interaction",
        "runtime_evidence": [
            "scenario state exposes current neighbor/NPC poses and velocities",
            "DP reward/guidance code already consumes neighbor_agents_past for collision proximity",
        ],
        "current_tick_available_before_selection": True,
        "candidate_level_or_deterministically_joinable": True,
        "finite_or_fail_closed": True,
        "deterministic": True,
        "uses_future_outcome_or_safetycost_label": False,
        "requires_dp_modification": False,
        "requires_dp_retraining": False,
        "requires_replay_to_compute_runtime_value": False,
        "requires_training_to_compute_runtime_value": False,
        "atom_value_domain": "nonnegative",
        "equivalent_closed_labels": ["observable_interaction"],
        "math_note": (
            "A TTC hinge could be affine in CAMP weights after fixed-tick "
            "feature extraction, but this family is already closed as "
            "observable interaction support."
        ),
    },
    {
        "name": "traffic_light_phase_or_right_of_way_context",
        "source_family": "external_context",
        "runtime_evidence": [
            "scenario_generation/traffic_light.py exposes TrafficLightController state",
            "signal/right-of-way and route-speed external-context branches were closed",
        ],
        "current_tick_available_before_selection": True,
        "candidate_level_or_deterministically_joinable": True,
        "finite_or_fail_closed": True,
        "deterministic": True,
        "uses_future_outcome_or_safetycost_label": False,
        "requires_dp_modification": False,
        "requires_dp_retraining": False,
        "requires_replay_to_compute_runtime_value": False,
        "requires_training_to_compute_runtime_value": False,
        "atom_value_domain": "nonnegative",
        "equivalent_closed_labels": [
            "external_context",
            "signal_right_of_way",
            "red_clearance_gap_to_best_current_tick",
        ],
        "math_note": (
            "Traffic-signal margins can be valid fixed-tick coefficients, "
            "but the signal/right-of-way and red-clearance routes have already "
            "failed to produce deployable selector evidence."
        ),
    },
    {
        "name": "dp_native_logprob_or_denoising_uncertainty",
        "source_family": "dp_prior_deviation",
        "runtime_evidence": [
            "candidate priors or denoising residuals would need native DP boundary exposure",
            "DP is fixed and must remain a black-box candidate generator",
        ],
        "current_tick_available_before_selection": False,
        "candidate_level_or_deterministically_joinable": True,
        "finite_or_fail_closed": False,
        "deterministic": True,
        "uses_future_outcome_or_safetycost_label": False,
        "requires_dp_modification": True,
        "requires_dp_retraining": False,
        "requires_replay_to_compute_runtime_value": False,
        "requires_training_to_compute_runtime_value": False,
        "atom_value_domain": "nonnegative",
        "equivalent_closed_labels": ["dp_prior_deviation"],
        "math_note": (
            "A native DP prior could be an affine coefficient only if it were "
            "already exposed before selection. It is not admissible under the "
            "fixed-DP black-box boundary."
        ),
    },
    {
        "name": "raw_prefix_or_source_donor_reuse",
        "source_family": "raw_prefix",
        "runtime_evidence": [
            "raw-prefix, donor, and top-1 retention families were previously audited",
            "existing evidence did not authorize selector promotion",
        ],
        "current_tick_available_before_selection": True,
        "candidate_level_or_deterministically_joinable": True,
        "finite_or_fail_closed": True,
        "deterministic": True,
        "uses_future_outcome_or_safetycost_label": False,
        "requires_dp_modification": False,
        "requires_dp_retraining": False,
        "requires_replay_to_compute_runtime_value": False,
        "requires_training_to_compute_runtime_value": False,
        "atom_value_domain": "nonnegative",
        "equivalent_closed_labels": ["raw_prefix", "source_donor", "top1_retention"],
        "math_note": (
            "These are already closed candidate identity/geometry families, not "
            "new safety support."
        ),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only runtime-source inventory after a negative source-visibility "
            "predeclaration screen. It records whether visible simulator/DP "
            "source families are genuinely new or remain closed."
        )
    )
    parser.add_argument("--screen_json", type=Path, required=True)
    parser.add_argument("--candidate_json", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = list(DEFAULT_RUNTIME_CANDIDATES)
    for path in args.candidate_json:
        candidates.extend(_load_candidates(path))
    report = build_report(
        screen=_load_json(args.screen_json),
        candidates=candidates,
        label=args.label,
        paths={
            "screen_json": str(args.screen_json),
            "candidate_json": [str(path) for path in args.candidate_json],
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def build_report(
    *,
    screen: dict[str, Any],
    candidates: list[dict[str, Any]] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = candidates or list(DEFAULT_RUNTIME_CANDIDATES)
    screen_summary = _screen_summary(screen)
    screen_checks = _screen_checks(screen_summary)
    closed_labels = _string_list(screen.get("closed_source_labels"))
    rows = [
        _candidate_row(candidate, closed_labels=closed_labels)
        for candidate in candidates
    ]
    final = _final_decision(screen_checks, rows)
    return {
        "analysis": {
            "name": "dp_camp_post_source_visibility_runtime_inventory_v1",
            "label": label,
            "role": (
                "read-only post-screen inventory of visible runtime source "
                "families for fixed-DP CAMP candidate screening"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "selection_effect": False,
            "paths": paths or {},
            "math_boundary": (
                "This inventory creates no atom and runs no selector. A later "
                "source can enter CAMP only as a fixed current-tick finite-"
                "candidate coefficient a_k, nonnegative, hinged, or signed-"
                "split, so score_k(w)=a_k^T w remains affine and the "
                "simplex/CVaR/L2 master remains convex. No DP-side classical "
                "Benders decomposition is claimed because no DP master/"
                "subproblem, dual, or valid cut is constructed."
            ),
        },
        "screen_summary": screen_summary,
        "screen_checks": screen_checks,
        "closed_source_labels": closed_labels,
        "runtime_source_candidates": rows,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Post Source-Visibility Runtime Inventory",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Support source ready: `{decision['support_source_ready']}`",
        f"- Selector route paused: `{decision['selector_route_paused']}`",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Closed Source Labels",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report["closed_source_labels"])
    lines.extend(
        [
            "",
            "## Runtime Candidate Inventory",
            "",
            "| Candidate | New source candidate | Rejection reasons | Closed equivalents |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in report["runtime_source_candidates"]:
        reasons = ", ".join(f"`{item}`" for item in row["rejection_reasons"]) or "`none`"
        equivalents = ", ".join(
            f"`{item}`" for item in row["equivalent_closed_labels"]
        ) or "`none`"
        lines.append(
            f"| `{row['name']}` | `{row['new_source_candidate']}` | "
            f"{reasons} | {equivalents} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "This gate does not authorize replay, atom promotion, CAMP retraining, "
            "online selector promotion, Full36, formal seeds, DP modification, or "
            "a classical Benders claim.",
            "",
        ]
    )
    return "\n".join(lines)


def _screen_summary(screen: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(screen.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selector_route_paused": bool(decision.get("selector_route_paused")),
        "support_source_ready": bool(decision.get("support_source_ready")),
        "blocked_action_conflicts": _blocked_action_conflicts(decision),
    }


def _screen_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("screen_status", summary["status"], SCREEN_STATUS),
        _check_equal("screen_passed", summary["passed"], True),
        _check_equal("screen_next_work", summary["authorized_next_work"], SCREEN_NEXT_WORK),
        _check_equal("screen_selector_route_paused", summary["selector_route_paused"], True),
        _check_equal("screen_support_source_ready_false", summary["support_source_ready"], False),
        _check_empty(
            "screen_blocked_action_conflicts_empty",
            summary["blocked_action_conflicts"],
        ),
    ]


def _candidate_row(
    candidate: dict[str, Any],
    *,
    closed_labels: list[str],
) -> dict[str, Any]:
    equivalent = sorted(
        set(_string_list(candidate.get("equivalent_closed_labels")))
        | (
            {str(candidate.get("source_family"))}
            if str(candidate.get("source_family") or "") in set(closed_labels)
            else set()
        )
    )
    checks = [
        _bool_check(candidate, "current_tick_available_before_selection", True),
        _bool_check(candidate, "candidate_level_or_deterministically_joinable", True),
        _bool_check(candidate, "finite_or_fail_closed", True),
        _bool_check(candidate, "deterministic", True),
        _bool_check(candidate, "uses_future_outcome_or_safetycost_label", False),
        _bool_check(candidate, "requires_dp_modification", False),
        _bool_check(candidate, "requires_dp_retraining", False),
        _bool_check(candidate, "requires_replay_to_compute_runtime_value", False),
        _bool_check(candidate, "requires_training_to_compute_runtime_value", False),
        _domain_check(candidate),
        _check_empty("not_equivalent_to_closed_source_labels", equivalent),
    ]
    rejection_reasons = [check["name"] for check in checks if not check["passed"]]
    return {
        "name": str(candidate.get("name") or "<unnamed>"),
        "source_family": str(candidate.get("source_family") or ""),
        "runtime_evidence": _string_list(candidate.get("runtime_evidence")),
        "math_note": str(candidate.get("math_note") or ""),
        "atom_value_domain": candidate.get("atom_value_domain"),
        "equivalent_closed_labels": equivalent,
        "checks": checks,
        "new_source_candidate": not rejection_reasons,
        "rejection_reasons": rejection_reasons,
        "next_gate": (
            CANDIDATE_NEXT_WORK
            if not rejection_reasons
            else "keep_rejected_or_rewrite_source_hypothesis"
        ),
    }


def _final_decision(
    screen_checks: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    screen_ready = all(check["passed"] for check in screen_checks)
    open_candidates = [row for row in rows if row["new_source_candidate"]]
    if not screen_ready:
        status = BLOCKED_STATUS
        passed = False
        support_source_ready = False
        selector_route_paused = False
        authorized_next_work = None
        next_step = "Repair the source-visibility predeclaration screen first."
    elif open_candidates:
        status = CANDIDATE_STATUS
        passed = True
        support_source_ready = False
        selector_route_paused = True
        authorized_next_work = CANDIDATE_NEXT_WORK
        next_step = (
            "Convert the open runtime-source candidate into an explicit "
            "source-visibility predeclaration proposal. Do not run replay or "
            "atomization before that screen passes."
        )
    else:
        status = PAUSED_STATUS
        passed = True
        support_source_ready = False
        selector_route_paused = True
        authorized_next_work = PAUSED_NEXT_WORK
        next_step = (
            "Keep the selector route paused. Progress now requires scenario/"
            "objective redesign or a genuinely new current-tick source family."
        )
    return {
        "status": status,
        "passed": passed,
        "support_source_ready": support_source_ready,
        "selector_route_paused": selector_route_paused,
        "authorized_next_work": authorized_next_work,
        "new_runtime_source_candidates": [row["name"] for row in open_candidates],
        "rejected_runtime_source_candidates": [
            row["name"] for row in rows if not row["new_source_candidate"]
        ],
        "failed_screen_checks": [
            check["name"] for check in screen_checks if not check["passed"]
        ],
        "next_step": next_step,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "atom_promotion_authorized": False,
    }


def _load_candidates(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    candidates = payload.get("candidates")
    if candidates is None:
        candidates = [payload]
    if not isinstance(candidates, list):
        raise ValueError(f"{path} candidates must be a list.")
    result: list[dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError(f"{path} candidate entries must be objects.")
        result.append(item)
    return result


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return []


def _blocked_action_conflicts(decision: dict[str, Any]) -> list[str]:
    return [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check_empty(name: str, value: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": len(value) == 0,
        "actual": value,
        "expected": [],
    }


def _bool_check(candidate: dict[str, Any], key: str, expected: bool) -> dict[str, Any]:
    return _check_equal(key, candidate.get(key), expected)


def _domain_check(candidate: dict[str, Any]) -> dict[str, Any]:
    domain = candidate.get("atom_value_domain")
    allowed = {"nonnegative", "hinge", "signed_split"}
    return {
        "name": "atom_value_domain_admissible",
        "passed": domain in allowed,
        "actual": domain,
        "expected": sorted(allowed),
    }


if __name__ == "__main__":
    main()
