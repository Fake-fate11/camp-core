#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


TARGETED_FAILURE_STATUS = "targeted_failure_attribution_no_current_route"
TARGETED_FAILURE_NEXT_WORK = (
    "predeclare_new_no_leak_targeted_support_source_or_reject_current_route_only"
)
BRIDGE_STATUS = "current_observable_separability_bridge_duplicate_rejected"
INVENTORY_STATUS = "current_tick_no_leak_atom_support_inventory_no_unclosed_fields"
SUPPORT_BOTTLENECK_STATUS = "current_fixed_dp_selector_calibration_exhausted"

READY_STATUS = "new_no_leak_targeted_support_source_predeclared"
REJECT_STATUS = "new_no_leak_targeted_support_source_not_available"
BLOCKED_STATUS = "new_no_leak_targeted_support_source_gate_blocked"

READY_NEXT_WORK = "default_off_new_no_leak_support_payload_design_only"
REJECT_NEXT_WORK = "source_level_targeted_support_discovery_or_pause_current_selector_route_only"

TARGET_BUCKETS = ("traffic_light", "red_light_turn")

CLOSED_SCORE_FAMILIES = (
    "non_turn_interaction_family",
    "observable_interaction_family",
    "progress_lane_hard_context",
    "relaxed_strict_atom_family",
    "revised_context_atom_family",
    "turn_logit_atom_family",
)

CLOSED_ROUTE_NAMES = (
    "generic_selector_label_preflight",
    "offline_convex_training_35fedb8",
    "objective_label_sensitivity",
    "observable_bridge_duplicate",
    "current_tick_support_inventory",
    "tensor_visibility_without_unclosed_runtime_source",
)

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for the post-attribution DP-CAMP step. It decides "
            "whether a genuinely new targeted no-leak support source is "
            "predeclared, or whether the current selector route must remain "
            "paused. It reads existing artifacts only."
        )
    )
    parser.add_argument("--targeted_failure_attribution_json", type=Path, required=True)
    parser.add_argument("--observable_bridge_json", type=Path, required=True)
    parser.add_argument("--support_inventory_json", type=Path, required=True)
    parser.add_argument("--support_bottleneck_json", type=Path, default=None)
    parser.add_argument("--proposal_json", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    proposal_payloads: list[dict[str, Any]] = []
    for path in args.proposal_json:
        proposal_payloads.extend(_load_proposals(path))
    report = build_report(
        targeted_failure_attribution=_load_json(args.targeted_failure_attribution_json),
        observable_bridge=_load_json(args.observable_bridge_json),
        support_inventory=_load_json(args.support_inventory_json),
        support_bottleneck=(
            None
            if args.support_bottleneck_json is None
            else _load_json(args.support_bottleneck_json)
        ),
        proposals=proposal_payloads,
        label=args.label,
        paths={
            "targeted_failure_attribution_json": str(
                args.targeted_failure_attribution_json
            ),
            "observable_bridge_json": str(args.observable_bridge_json),
            "support_inventory_json": str(args.support_inventory_json),
            "support_bottleneck_json": (
                None
                if args.support_bottleneck_json is None
                else str(args.support_bottleneck_json)
            ),
            "proposal_json": [str(path) for path in args.proposal_json],
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


def build_report(
    *,
    targeted_failure_attribution: dict[str, Any],
    observable_bridge: dict[str, Any],
    support_inventory: dict[str, Any],
    support_bottleneck: dict[str, Any] | None = None,
    proposals: list[dict[str, Any]] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proposals = proposals or []
    source_checks = _source_checks(
        targeted_failure_attribution=targeted_failure_attribution,
        observable_bridge=observable_bridge,
        support_inventory=support_inventory,
        support_bottleneck=support_bottleneck,
    )
    closed_support_sources = _closed_support_sources(
        observable_bridge=observable_bridge,
        support_inventory=support_inventory,
        support_bottleneck=support_bottleneck,
    )
    proposal_rows = [
        _proposal_row(proposal, closed_support_sources=closed_support_sources)
        for proposal in proposals
    ]
    final_decision = _final_decision(
        source_checks=source_checks,
        proposal_rows=proposal_rows,
    )
    return {
        "analysis": {
            "name": "dp_camp_new_no_leak_targeted_support_or_reject_v1",
            "label": label,
            "role": (
                "plan-only post-attribution gate that either accepts a genuinely "
                "new no-leak targeted support source for a later default-off "
                "payload design, or pauses the current CAMP-DP selector route"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "paths": paths or {},
            "target_buckets": list(TARGET_BUCKETS),
            "math_boundary": (
                "DP remains a fixed black-box candidate generator. Runtime CAMP "
                "may use only current-tick finite-candidate constants a_k. Any "
                "accepted atom must be nonnegative or signed-split into "
                "nonnegative parts, and the selector score must remain affine "
                "score_k(w)=a_k^T w so the simplex/CVaR/L2 master remains "
                "convex. Closed-loop outcomes and SafetyCost labels are "
                "offline evaluation labels only. This finite-candidate planning "
                "gate is not a DP-side classical Benders decomposition because "
                "it constructs no DP master/subproblem, dual, or valid cuts."
            ),
        },
        "source_checks": source_checks,
        "closed_support_sources": closed_support_sources,
        "future_support_source_contract": _future_support_source_contract(),
        "proposals": proposal_rows,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final_decision,
    }


def _source_checks(
    *,
    targeted_failure_attribution: dict[str, Any],
    observable_bridge: dict[str, Any],
    support_inventory: dict[str, Any],
    support_bottleneck: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    targeted_decision = targeted_failure_attribution.get("final_decision") or {}
    failure_summary = targeted_failure_attribution.get("failure_summary") or {}
    bridge_decision = observable_bridge.get("final_decision") or {}
    bridge_equivalence = observable_bridge.get("equivalence") or {}
    inventory_decision = support_inventory.get("final_decision") or {}
    checks = [
        _check_equal(
            "targeted_failure_status",
            targeted_decision.get("status"),
            TARGETED_FAILURE_STATUS,
        ),
        _check_equal("targeted_failure_passed", targeted_decision.get("passed"), True),
        _check_equal(
            "targeted_route_rejected",
            targeted_decision.get("current_camp_dp_selector_route_rejected"),
            True,
        ),
        _check_equal(
            "targeted_authorizes_only_this_gate",
            targeted_decision.get("authorized_next_work"),
            TARGETED_FAILURE_NEXT_WORK,
        ),
        _check_equal(
            "candidate_pool_opportunity_confirmed",
            failure_summary.get("candidate_pool_opportunity_confirmed"),
            True,
        ),
        _check_equal(
            "new_no_leak_support_missing_in_current_artifacts",
            failure_summary.get("new_no_leak_support_missing_in_current_artifacts"),
            True,
        ),
        _check_equal(
            "observable_bridge_duplicate_rejected",
            bridge_decision.get("status"),
            BRIDGE_STATUS,
        ),
        _check_equal(
            "observable_bridge_not_materially_new",
            bridge_equivalence.get("materially_new_route"),
            False,
        ),
        _check_empty(
            "observable_bridge_no_uncovered_material_fields",
            bridge_equivalence.get("uncovered_current_material_fields") or [],
        ),
        _check_equal(
            "support_inventory_no_unclosed_fields",
            inventory_decision.get("status"),
            INVENTORY_STATUS,
        ),
        _check_empty(
            "support_inventory_no_admissible_unclosed_families",
            inventory_decision.get("admissible_unclosed_candidate_families") or [],
        ),
        *_blocked_action_checks(targeted_decision, "targeted_failure"),
        *_blocked_action_checks(bridge_decision, "observable_bridge"),
        *_blocked_action_checks(inventory_decision, "support_inventory"),
    ]
    if support_bottleneck is not None:
        bottleneck_decision = support_bottleneck.get("final_decision") or {}
        checks.extend(
            [
                _check_equal(
                    "support_bottleneck_exhausted",
                    bottleneck_decision.get("status"),
                    SUPPORT_BOTTLENECK_STATUS,
                ),
                *_blocked_action_checks(bottleneck_decision, "support_bottleneck"),
            ]
        )
    return checks


def _closed_support_sources(
    *,
    observable_bridge: dict[str, Any],
    support_inventory: dict[str, Any],
    support_bottleneck: dict[str, Any] | None,
) -> dict[str, Any]:
    bridge_equivalence = observable_bridge.get("equivalence") or {}
    inventory_decision = support_inventory.get("final_decision") or {}
    support_bottleneck_decision = (
        {} if support_bottleneck is None else support_bottleneck.get("final_decision") or {}
    )
    return {
        "closed_score_families": list(CLOSED_SCORE_FAMILIES),
        "closed_route_names": list(CLOSED_ROUTE_NAMES),
        "available_existing_or_closed_proxy_families": inventory_decision.get(
            "available_existing_or_closed_proxy_families"
        )
        or [],
        "observable_uncovered_material_fields": bridge_equivalence.get(
            "uncovered_current_material_fields"
        )
        or [],
        "support_bottleneck_status": support_bottleneck_decision.get("status"),
        "support_bottleneck_reasons": support_bottleneck_decision.get("reasons") or [],
    }


def _future_support_source_contract() -> dict[str, Any]:
    return {
        "required_properties": [
            "current_tick_available",
            "candidate_level",
            "finite",
            "deterministic",
            "available_before_selection",
            "not_future_outcome_label",
            "not_equivalent_to_closed_score_family",
            "does_not_require_dp_modification",
            "does_not_require_replay_or_training_to_compute",
            "atom_nonnegative_or_signed_split",
            "affine_score_preserved",
        ],
        "offline_labels_allowed_only_for": [
            "source_materiality_evaluation",
            "targeted_separability_screen",
            "post hoc safety score comparison",
        ],
        "explicitly_not_authorized": list(BLOCKED_ACTIONS),
    }


def _proposal_row(
    proposal: dict[str, Any],
    *,
    closed_support_sources: dict[str, Any],
) -> dict[str, Any]:
    name = str(proposal.get("name") or proposal.get("source_name") or "<unnamed>")
    score_family = proposal.get("score_family")
    source_family = proposal.get("source_family")
    closed_families = set(closed_support_sources["closed_score_families"])
    closed_proxies = set(
        closed_support_sources.get("available_existing_or_closed_proxy_families") or []
    )
    checks = [
        _proposal_bool_check(proposal, "current_tick_available", True),
        _proposal_bool_check(proposal, "candidate_level", True),
        _proposal_bool_check(proposal, "finite", True),
        _proposal_bool_check(proposal, "deterministic", True),
        _proposal_bool_check(proposal, "available_before_selection", True),
        _proposal_bool_check(proposal, "uses_future_outcome_labels", False),
        _proposal_bool_check(proposal, "requires_dp_modification", False),
        _proposal_bool_check(proposal, "requires_replay_to_compute", False),
        _proposal_bool_check(proposal, "requires_training_to_compute", False),
        _proposal_bool_check(proposal, "equivalent_to_closed_family", False),
        _proposal_domain_check(proposal),
        _check_not_in(
            "score_family_not_closed",
            score_family,
            closed_families,
        ),
        _check_not_in(
            "source_family_not_closed_proxy",
            source_family,
            closed_proxies,
        ),
    ]
    admissible = all(check["passed"] for check in checks)
    return {
        "name": name,
        "score_family": score_family,
        "source_family": source_family,
        "admissible": admissible,
        "checks": checks,
        "rejection_reasons": [
            check["name"] for check in checks if not check["passed"]
        ],
        "next_gate": (
            "default_off_payload_design_preflight"
            if admissible
            else "reject_or_rewrite_source_proposal"
        ),
    }


def _final_decision(
    *,
    source_checks: list[dict[str, Any]],
    proposal_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    source_ready = all(check["passed"] for check in source_checks)
    admissible = [row for row in proposal_rows if row["admissible"]]
    if not source_ready:
        status = BLOCKED_STATUS
        current_route_rejected = False
        support_source_ready = False
        authorized_next_work = None
        next_step = "Repair source artifacts before deciding the post-attribution route."
    elif admissible:
        status = READY_STATUS
        current_route_rejected = False
        support_source_ready = True
        authorized_next_work = READY_NEXT_WORK
        next_step = (
            "Write a default-off payload/atom design gate for the accepted "
            "support source. Do not train or replay until that gate passes."
        )
    else:
        status = REJECT_STATUS
        current_route_rejected = True
        support_source_ready = False
        authorized_next_work = REJECT_NEXT_WORK
        next_step = (
            "Pause the current selector/training route. Continue only with "
            "source-level discovery for a genuinely new no-leak targeted "
            "candidate support source, or keep the route rejected."
        )
    return {
        "status": status,
        "passed": source_ready,
        "support_source_ready": support_source_ready,
        "admissible_support_sources": [row["name"] for row in admissible],
        "rejected_support_sources": [
            row["name"] for row in proposal_rows if not row["admissible"]
        ],
        "current_camp_dp_selector_route_rejected": current_route_rejected,
        "authorized_next_work": authorized_next_work,
        "next_step": next_step,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# New No-Leak Targeted Support Source Gate",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Support source ready: `{decision['support_source_ready']}`",
        "- Current CAMP-DP selector route rejected: "
        f"`{decision['current_camp_dp_selector_route_rejected']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | {_check_detail(check)} |"
        )
    lines.extend(
        [
            "",
            "## Closed Support Boundary",
            "",
        ]
    )
    closed = report["closed_support_sources"]
    for key in (
        "closed_score_families",
        "closed_route_names",
        "available_existing_or_closed_proxy_families",
        "observable_uncovered_material_fields",
        "support_bottleneck_status",
        "support_bottleneck_reasons",
    ):
        lines.append(f"- `{key}` = `{closed.get(key)}`")
    lines.extend(
        [
            "",
            "## Proposal Assessment",
            "",
            "| Proposal | Admissible | Score family | Source family | Rejection reasons |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if report["proposals"]:
        for row in report["proposals"]:
            reasons = ", ".join(row["rejection_reasons"]) or "none"
            lines.append(
                f"| `{row['name']}` | `{row['admissible']}` | "
                f"`{row['score_family']}` | `{row['source_family']}` | "
                f"`{reasons}` |"
            )
    else:
        lines.append("| `none_provided` | `False` | `n/a` | `n/a` | `no proposal` |")
    lines.extend(
        [
            "",
            "## Future Support Contract",
            "",
        ]
    )
    for item in report["future_support_source_contract"]["required_properties"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Blocked Actions",
            "",
        ]
    )
    for action in BLOCKED_ACTIONS:
        lines.append(f"- `{action}` = `{decision[action]}`")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _blocked_action_checks(decision: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _check_equal(f"{prefix}_{name}_false", decision.get(name, False), False)
        for name in BLOCKED_ACTIONS
    ]


def _proposal_bool_check(
    proposal: dict[str, Any],
    key: str,
    expected: bool,
) -> dict[str, Any]:
    return _check_equal(key, proposal.get(key), expected)


def _proposal_domain_check(proposal: dict[str, Any]) -> dict[str, Any]:
    domain = proposal.get("atom_value_domain")
    allowed = {"nonnegative", "signed_split"}
    return {
        "name": "atom_value_domain_admissible",
        "passed": domain in allowed,
        "observed": domain,
        "expected": sorted(allowed),
    }


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": observed,
        "expected": expected,
    }


def _check_empty(name: str, observed: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": len(observed) == 0,
        "observed": observed,
        "expected": [],
    }


def _check_not_in(name: str, observed: Any, blocked: set[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed is not None and observed not in blocked,
        "observed": observed,
        "expected": f"not in {sorted(blocked)}",
    }


def _check_detail(check: dict[str, Any]) -> str:
    return f"`observed={check.get('observed')}; expected={check.get('expected')}`"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _load_proposals(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        if isinstance(payload.get("proposals"), list):
            proposals = payload["proposals"]
        else:
            proposals = [payload]
    elif isinstance(payload, list):
        proposals = payload
    else:
        raise ValueError(f"{path} must contain a JSON object or list.")
    rows: list[dict[str, Any]] = []
    for index, proposal in enumerate(proposals):
        if not isinstance(proposal, dict):
            raise ValueError(f"{path} proposal {index} must be an object.")
        rows.append(proposal)
    return rows


if __name__ == "__main__":
    main()
