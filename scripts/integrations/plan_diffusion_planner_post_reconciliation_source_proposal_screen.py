#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


GOAL_STATE_STATUS = "post_reconciliation_current_goal_state_paused"
GOAL_STATE_NEXT_WORK = "submit_new_current_tick_source_proposal_or_keep_paused_only"

READY_STATUS = "post_reconciliation_source_proposal_screen_ready"
PAUSED_STATUS = "post_reconciliation_source_proposal_screen_paused"
BLOCKED_STATUS = "post_reconciliation_source_proposal_screen_blocked"
READY_NEXT_WORK = "default_off_current_tick_source_payload_design_only"
PAUSED_NEXT_WORK = "submit_new_current_tick_source_proposal_or_keep_paused_only"

DEFAULT_CLOSED_LABELS = (
    "dp_prior_deviation",
    "external_context",
    "mode_seeking",
    "observable_interaction",
    "postprocess_tracker_descriptor_family",
    "postprocess_tracker_descriptor_signal",
    "progress_lane_hard",
    "raw_prefix",
    "red_clearance_gap_to_best_current_tick",
    "route_speed",
    "route_topology",
    "signal_right_of_way",
    "source_donor",
    "targeted_red_clearance",
    "temporal_consistency_atom_family",
    "top1_retention",
    "turn_logit",
)

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
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only source-proposal screen after the post-reconciliation "
            "current goal state. It checks whether an explicit current-tick "
            "candidate-level source proposal is materially outside closed "
            "families before any payload design, replay, or training."
        )
    )
    parser.add_argument("--goal_state_json", type=Path, required=True)
    parser.add_argument("--source_family_ledger_json", type=Path, default=None)
    parser.add_argument("--proposal_json", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    proposals: list[dict[str, Any]] = []
    for path in args.proposal_json:
        proposals.extend(_load_proposals(path))
    report = build_report(
        goal_state=_load_json(args.goal_state_json),
        source_family_ledger=(
            None
            if args.source_family_ledger_json is None
            else _load_json(args.source_family_ledger_json)
        ),
        proposals=proposals,
        label=args.label,
        paths={
            "goal_state_json": str(args.goal_state_json),
            "source_family_ledger_json": (
                None
                if args.source_family_ledger_json is None
                else str(args.source_family_ledger_json)
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
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def build_report(
    *,
    goal_state: dict[str, Any],
    source_family_ledger: dict[str, Any] | None = None,
    proposals: list[dict[str, Any]] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proposals = proposals or []
    goal = _goal_summary(goal_state)
    closed = _closed_summary(source_family_ledger)
    goal_checks = _goal_checks(goal)
    proposal_rows = [_proposal_row(row, closed_labels=closed["closed_labels"]) for row in proposals]
    decision = _final_decision(goal_checks, proposal_rows)
    return {
        "analysis": {
            "name": "dp_camp_post_reconciliation_source_proposal_screen_v1",
            "label": label,
            "role": (
                "read-only post-reconciliation screen for a materially new "
                "current-tick candidate-level CAMP source proposal"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "This screen creates no atom, trains no weight, runs no DP, "
                "and changes no selector. An accepted source only authorizes a "
                "future default-off payload design. The runtime value must be "
                "a fixed current-tick finite-candidate coefficient a_k, "
                "nonnegative, hinged, or signed-split, preserving "
                "score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master. "
                "No DP-side classical Benders master/subproblem, dual, or "
                "valid cut is constructed."
            ),
        },
        "goal_state_summary": goal,
        "closed_source_summary": closed,
        "proposal_contract": _proposal_contract(),
        "proposal_rows": proposal_rows,
        "screen_checks": goal_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Post-Reconciliation Source Proposal Screen",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Selector route paused: `{decision['selector_route_paused']}`",
        f"- Support source ready: `{decision['support_source_ready']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Goal State",
        "",
    ]
    for key, value in report["goal_state_summary"].items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(["", "## Closed Labels", ""])
    lines.extend(f"- `{item}`" for item in report["closed_source_summary"]["closed_labels"])
    lines.extend(
        [
            "",
            "## Proposal Rows",
            "",
            "| Proposal | Admissible | Source family | Score family | Rejection reasons |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    if report["proposal_rows"]:
        for row in report["proposal_rows"]:
            reasons = ", ".join(row["rejection_reasons"]) or "none"
            lines.append(
                f"| `{row['name']}` | `{row['admissible']}` | "
                f"`{row['source_family']}` | `{row['score_family']}` | "
                f"`{reasons}` |"
            )
    else:
        lines.append("| `none_provided` | `False` | `n/a` | `n/a` | `no proposal` |")
    lines.extend(["", "## Proposal Contract", ""])
    lines.extend(f"- `{item}`" for item in report["proposal_contract"]["required_properties"])
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["screen_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.extend(["", "## Blocked Actions", ""])
    for action, value in report["blocked_actions"].items():
        lines.append(f"- `{action}` = `{value}`")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _goal_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    goal = _dict(report.get("goal_state"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "selector_route_paused": bool(final.get("selector_route_paused")),
        "deployable_route_exists": bool(final.get("deployable_camp_dp_selector_route_exists")),
        "candidate_pool_opportunity_exists": bool(goal.get("candidate_pool_opportunity_exists")),
        "no_new_runtime_source_available": bool(goal.get("no_new_runtime_source_available")),
        "development_gates_complete": bool(final.get("development_gates_complete")),
        "formal_seeds_ready": bool(final.get("formal_seeds_ready")),
        "blocked_action_conflicts": _blocked_conflicts(final),
    }


def _closed_summary(ledger: dict[str, Any] | None) -> dict[str, Any]:
    labels = set(DEFAULT_CLOSED_LABELS)
    if ledger is not None:
        source_ledger = _dict(ledger.get("source_family_ledger"))
        labels.update(_string_list(source_ledger.get("closed_source_family_labels")))
        labels.update(_string_list(source_ledger.get("closed_score_families")))
        labels.update(_string_list(source_ledger.get("closed_or_existing_proxy_families")))
    return {"closed_labels": sorted(labels)}


def _goal_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("goal_status", summary["status"], GOAL_STATE_STATUS),
        _check_equal("goal_passed", summary["passed"], True),
        _check_equal("goal_authorizes_source_or_pause", summary["authorized_next_work"], GOAL_STATE_NEXT_WORK),
        _check_equal("goal_selector_route_paused", summary["selector_route_paused"], True),
        _check_equal("goal_deployable_route_absent", summary["deployable_route_exists"], False),
        _check_equal("goal_candidate_pool_opportunity_exists", summary["candidate_pool_opportunity_exists"], True),
        _check_equal("goal_no_new_runtime_source_available", summary["no_new_runtime_source_available"], True),
        _check_equal("goal_development_incomplete", summary["development_gates_complete"], False),
        _check_equal("goal_formal_seeds_not_ready", summary["formal_seeds_ready"], False),
        _check_empty("goal_no_blocked_action_conflicts", summary["blocked_action_conflicts"]),
    ]


def _proposal_row(proposal: dict[str, Any], *, closed_labels: list[str]) -> dict[str, Any]:
    name = str(proposal.get("name") or proposal.get("source_name") or "<unnamed>")
    source_family = str(proposal.get("source_family") or "")
    score_family = str(proposal.get("score_family") or "")
    non_equivalence = _string_list(proposal.get("non_equivalence_evidence"))
    checks = [
        _proposal_bool_check(proposal, "current_tick_available_before_selection", True),
        _proposal_bool_check(proposal, "candidate_level_or_deterministically_joinable", True),
        _proposal_bool_check(proposal, "finite_or_fail_closed", True),
        _proposal_bool_check(proposal, "deterministic", True),
        _proposal_bool_check(proposal, "uses_future_outcome_or_safetycost_label", False),
        _proposal_bool_check(proposal, "requires_dp_modification", False),
        _proposal_bool_check(proposal, "requires_dp_retraining", False),
        _proposal_bool_check(proposal, "requires_replay_to_compute_runtime_value", False),
        _proposal_bool_check(proposal, "requires_training_to_compute_runtime_value", False),
        _proposal_bool_check(proposal, "default_off_latency_accounted", True),
        _proposal_bool_check(proposal, "existing_log_materiality_predeclared", True),
        _proposal_domain_check(proposal),
        _check_not_in("source_family_not_closed", source_family, set(closed_labels)),
        _check_not_in("score_family_not_closed", score_family, set(closed_labels)),
        _check_nonempty("non_equivalence_evidence_nonempty", non_equivalence),
    ]
    admissible = all(check["passed"] for check in checks)
    return {
        "name": name,
        "source_family": source_family,
        "score_family": score_family,
        "admissible": admissible,
        "checks": checks,
        "rejection_reasons": [check["name"] for check in checks if not check["passed"]],
        "next_gate": (
            "default_off_current_tick_source_payload_design"
            if admissible
            else "reject_or_rewrite_source_proposal"
        ),
    }


def _proposal_contract() -> dict[str, Any]:
    return {
        "required_properties": [
            "current_tick_available_before_selection",
            "candidate_level_or_deterministically_joinable",
            "finite_or_fail_closed",
            "deterministic",
            "uses_future_outcome_or_safetycost_label=false",
            "requires_dp_modification=false",
            "requires_dp_retraining=false",
            "requires_replay_to_compute_runtime_value=false",
            "requires_training_to_compute_runtime_value=false",
            "default_off_latency_accounted",
            "existing_log_materiality_predeclared",
            "atom_value_domain in {nonnegative, hinge, signed_split}",
            "source_family and score_family not in closed labels",
            "non_equivalence_evidence",
        ],
        "explicitly_not_authorized": list(BLOCKED_ACTIONS),
    }


def _final_decision(goal_checks: list[dict[str, Any]], proposal_rows: list[dict[str, Any]]) -> dict[str, Any]:
    goal_ready = all(check["passed"] for check in goal_checks)
    admissible = [row for row in proposal_rows if row["admissible"]]
    if not goal_ready:
        status = BLOCKED_STATUS
        passed = False
        support_source_ready = False
        selector_paused = False
        authorized_next = None
        next_step = "Repair the post-reconciliation current goal-state artifact first."
    elif admissible:
        status = READY_STATUS
        passed = True
        support_source_ready = True
        selector_paused = True
        authorized_next = READY_NEXT_WORK
        next_step = (
            "Write a default-off payload design for the accepted current-tick "
            "source. Do not run replay, train CAMP, or change online selection."
        )
    else:
        status = PAUSED_STATUS
        passed = True
        support_source_ready = False
        selector_paused = True
        authorized_next = PAUSED_NEXT_WORK
        next_step = (
            "Keep the selector route paused unless a materially new current-tick "
            "source proposal is supplied and passes this screen."
        )
    return {
        "status": status,
        "passed": passed,
        "selector_route_paused": selector_paused,
        "support_source_ready": support_source_ready,
        "admissible_sources": [row["name"] for row in admissible],
        "rejected_sources": [row["name"] for row in proposal_rows if not row["admissible"]],
        "deployable_camp_dp_selector_route_exists": False,
        "authorized_next_work": authorized_next,
        "failed_checks": [check["name"] for check in goal_checks if not check["passed"]],
        "next_step": next_step,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _blocked_conflicts(decision: dict[str, Any]) -> list[str]:
    return [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]


def _proposal_bool_check(proposal: dict[str, Any], key: str, expected: bool) -> dict[str, Any]:
    return _check_equal(key, proposal.get(key), expected)


def _proposal_domain_check(proposal: dict[str, Any]) -> dict[str, Any]:
    allowed = {"nonnegative", "hinge", "signed_split"}
    value = proposal.get("atom_value_domain")
    return {
        "name": "atom_value_domain_admissible",
        "passed": value in allowed,
        "observed": value,
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
    return {"name": name, "passed": len(observed) == 0, "observed": observed, "expected": []}


def _check_nonempty(name: str, observed: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": len(observed) > 0,
        "observed": observed,
        "expected": "nonempty",
    }


def _check_not_in(name: str, observed: str, blocked: set[str]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(observed) and observed not in blocked,
        "observed": observed,
        "expected": f"not in {sorted(blocked)}",
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _load_proposals(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    proposals = payload.get("proposals")
    if proposals is None:
        proposals = [payload]
    if not isinstance(proposals, list):
        raise ValueError(f"{path} proposals must be a list.")
    rows: list[dict[str, Any]] = []
    for item in proposals:
        if not isinstance(item, dict):
            raise ValueError(f"{path} proposal entries must be objects.")
        rows.append(item)
    return rows


if __name__ == "__main__":
    main()
