#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


POST_PAUSE_STATUS = "post_pause_deployability_proof_objective_predeclared"
POST_PAUSE_NEXT_WORK = "new_current_tick_source_family_proposal_only"
SOURCE_REJECT_STATUS = "new_no_leak_targeted_support_source_not_available"
SOURCE_REJECT_NEXT_WORK = (
    "source_level_targeted_support_discovery_or_pause_current_selector_route_only"
)
EXTERNAL_CONTEXT_CLOSURE_STATUS = "post_external_context_source_route_closed"

READY_STATUS = "post_pause_source_family_ledger_ready"
BLOCKED_STATUS = "post_pause_source_family_ledger_blocked"
READY_NEXT_WORK = "materially_new_current_tick_source_family_discovery_or_keep_paused_only"

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

PREDECLARED_CLOSED_FAMILY_LABELS = (
    "route_speed",
    "signal_right_of_way",
    "turn_logit",
    "dp_prior_deviation",
    "top1_retention",
    "progress_lane_hard",
    "observable_interaction",
    "route_topology",
    "mode_seeking",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only post-pause source-family ledger for CAMP-on-DP. It "
            "records the current closed families and the fail-closed contract "
            "for any next source proposal."
        )
    )
    parser.add_argument("--post_pause_objective_json", type=Path, required=True)
    parser.add_argument("--latest_source_gate_json", type=Path, required=True)
    parser.add_argument("--post_external_context_closure_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        post_pause_objective=_load_json(args.post_pause_objective_json),
        latest_source_gate=_load_json(args.latest_source_gate_json),
        post_external_context_closure=(
            None
            if args.post_external_context_closure_json is None
            else _load_json(args.post_external_context_closure_json)
        ),
        label=args.label,
        paths={
            "post_pause_objective_json": str(args.post_pause_objective_json),
            "latest_source_gate_json": str(args.latest_source_gate_json),
            "post_external_context_closure_json": (
                None
                if args.post_external_context_closure_json is None
                else str(args.post_external_context_closure_json)
            ),
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
    post_pause_objective: dict[str, Any],
    latest_source_gate: dict[str, Any],
    post_external_context_closure: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    objective_summary = _objective_summary(post_pause_objective)
    source_summary = _source_gate_summary(latest_source_gate)
    closure_summary = (
        None
        if post_external_context_closure is None
        else _external_context_closure_summary(post_external_context_closure)
    )
    checks = _checks(
        objective_summary=objective_summary,
        source_summary=source_summary,
        closure_summary=closure_summary,
    )
    ledger = _ledger(
        objective_summary=objective_summary,
        source_summary=source_summary,
        closure_summary=closure_summary,
    )
    final = _final_decision(checks)
    return {
        "analysis": {
            "name": "dp_camp_post_pause_source_family_ledger_v1",
            "label": label,
            "role": (
                "read-only ledger after the post-pause deployability objective "
                "and the latest source proposal rejection"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "This ledger creates no atom, runs no selector, trains no "
                "weights, and uses no closed-loop outcomes as runtime features. "
                "Any later source must be a current-tick finite-candidate "
                "coefficient a_k, nonnegative, hinged, or signed-split, so "
                "score_k(w)=a_k^T w stays affine and the simplex/CVaR/L2 "
                "robust master remains convex. This is not a DP-side "
                "classical Benders decomposition because no DP master, "
                "subproblem, dual, or valid cut is constructed."
            ),
        },
        "objective_summary": objective_summary,
        "latest_source_gate_summary": source_summary,
        "post_external_context_closure_summary": closure_summary,
        "source_family_ledger": ledger,
        "ledger_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "next_source_proposal_contract": _next_source_proposal_contract(),
        "final_decision": final,
    }


def _objective_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    objective = report.get("deployability_first_objective") or {}
    observed = objective.get("observed_gap") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "objective_only_reopening_allowed": bool(
            decision.get("objective_only_reopening_allowed")
        ),
        "deployability_first_objective_ready": bool(
            decision.get("deployability_first_objective_ready")
        ),
        "new_no_leak_support_missing": bool(observed.get("new_no_leak_support_missing")),
        "candidate_pool_opportunity_confirmed": bool(
            observed.get("candidate_pool_opportunity_confirmed")
        ),
        "next_source_family_requirements": list(
            objective.get("next_source_family_requirements") or []
        ),
        "required_preconditions_before_replay": list(
            objective.get("required_preconditions_before_replay") or []
        ),
        "forbidden_shortcuts": list(objective.get("forbidden_shortcuts") or []),
        "blocked_action_conflicts": _blocked_action_conflicts(decision),
    }


def _source_gate_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "support_source_ready": bool(decision.get("support_source_ready")),
        "current_selector_route_rejected": bool(
            decision.get("current_camp_dp_selector_route_rejected")
        ),
        "admissible_support_sources": list(
            decision.get("admissible_support_sources") or []
        ),
        "rejected_support_sources": list(decision.get("rejected_support_sources") or []),
        "closed_support_sources": report.get("closed_support_sources") or {},
        "proposal_rows": [
            _proposal_summary(row) for row in report.get("proposals") or []
        ],
        "blocked_action_conflicts": _blocked_action_conflicts(decision),
    }


def _proposal_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": row.get("name"),
        "score_family": row.get("score_family"),
        "source_family": row.get("source_family"),
        "admissible": bool(row.get("admissible")),
        "rejection_reasons": list(row.get("rejection_reasons") or []),
        "next_gate": row.get("next_gate"),
    }


def _external_context_closure_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "external_context_source_route_closed": bool(
            decision.get("external_context_source_route_closed")
        ),
        "current_selector_route_rejected": bool(
            decision.get("current_camp_dp_selector_route_rejected")
        ),
        "authorized_next_work": decision.get("authorized_next_work"),
        "blocked_action_conflicts": _blocked_action_conflicts(decision),
    }


def _ledger(
    *,
    objective_summary: dict[str, Any],
    source_summary: dict[str, Any],
    closure_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    closed = source_summary.get("closed_support_sources") or {}
    rejected_proposals = source_summary.get("proposal_rows") or []
    closed_source_labels = set(PREDECLARED_CLOSED_FAMILY_LABELS)
    if closure_summary is not None:
        closed_source_labels.update({"external_context", "route_speed", "signal_right_of_way"})
    for row in rejected_proposals:
        if "equivalent_to_closed_family" in row.get("rejection_reasons", []):
            if row.get("score_family"):
                closed_source_labels.add(str(row["score_family"]))
            if row.get("source_family"):
                closed_source_labels.add(str(row["source_family"]))
    return {
        "closed_source_family_labels": sorted(closed_source_labels),
        "closed_score_families": sorted(
            set(str(item) for item in closed.get("closed_score_families") or [])
        ),
        "closed_route_names": sorted(
            set(str(item) for item in closed.get("closed_route_names") or [])
        ),
        "closed_or_existing_proxy_families": sorted(
            set(
                str(item)
                for item in closed.get("available_existing_or_closed_proxy_families") or []
            )
        ),
        "rejected_source_proposals": rejected_proposals,
        "objective_forbidden_shortcuts": objective_summary.get("forbidden_shortcuts") or [],
        "required_preconditions_before_replay": objective_summary.get(
            "required_preconditions_before_replay"
        )
        or [],
        "next_policy": (
            "Only a materially new current-tick, candidate-level or "
            "deterministically joinable source family may reopen design work. "
            "Otherwise keep the current selector route paused."
        ),
    }


def _checks(
    *,
    objective_summary: dict[str, Any],
    source_summary: dict[str, Any],
    closure_summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    checks = [
        _check_equal("post_pause_status", objective_summary["status"], POST_PAUSE_STATUS),
        _check_equal("post_pause_passed", objective_summary["passed"], True),
        _check_equal(
            "post_pause_authorizes_source_proposal_only",
            objective_summary["authorized_next_work"],
            POST_PAUSE_NEXT_WORK,
        ),
        _check_equal(
            "objective_only_reopening_disallowed",
            objective_summary["objective_only_reopening_allowed"],
            False,
        ),
        _check_equal(
            "new_no_leak_support_missing",
            objective_summary["new_no_leak_support_missing"],
            True,
        ),
        _check_empty(
            "post_pause_no_blocked_actions",
            objective_summary["blocked_action_conflicts"],
        ),
        _check_equal("latest_source_gate_status", source_summary["status"], SOURCE_REJECT_STATUS),
        _check_equal("latest_source_gate_passed", source_summary["passed"], True),
        _check_equal(
            "latest_source_gate_authorizes_discovery_or_pause",
            source_summary["authorized_next_work"],
            SOURCE_REJECT_NEXT_WORK,
        ),
        _check_equal("support_source_not_ready", source_summary["support_source_ready"], False),
        _check_empty(
            "no_admissible_support_sources",
            source_summary["admissible_support_sources"],
        ),
        _check_equal(
            "current_selector_route_rejected",
            source_summary["current_selector_route_rejected"],
            True,
        ),
        _check_empty(
            "latest_source_gate_no_blocked_actions",
            source_summary["blocked_action_conflicts"],
        ),
    ]
    if closure_summary is not None:
        checks.extend(
            [
                _check_equal(
                    "external_context_closure_status",
                    closure_summary["status"],
                    EXTERNAL_CONTEXT_CLOSURE_STATUS,
                ),
                _check_equal("external_context_closure_passed", closure_summary["passed"], True),
                _check_equal(
                    "external_context_source_route_closed",
                    closure_summary["external_context_source_route_closed"],
                    True,
                ),
                _check_empty(
                    "external_context_closure_no_blocked_actions",
                    closure_summary["blocked_action_conflicts"],
                ),
            ]
        )
    return checks


def _final_decision(checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(check["passed"] for check in checks)
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "source_family_ledger_ready": passed,
        "support_source_ready": False,
        "current_camp_dp_selector_route_rejected": True,
        "authorized_next_work": READY_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Search for a materially new current-tick source family, or keep "
            "the current CAMP-DP selector route paused. Do not train, replay, "
            "promote an online selector, modify DP, use formal seeds, or claim "
            "DP-side classical Benders."
            if passed
            else "Repair stale or contradictory source artifacts before any next proposal."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _next_source_proposal_contract() -> dict[str, Any]:
    return {
        "required_properties": [
            "current_tick_available_before_selection",
            "candidate_level_or_deterministically_joinable",
            "finite_for_every_candidate_or_fail_closed",
            "deterministic",
            "not_future_outcome_or_safetycost_proxy",
            "not_equivalent_to_closed_source_or_score_family",
            "does_not_require_dp_modification",
            "does_not_require_replay_or_training_to_compute_runtime_value",
            "nonnegative_hinge_or_signed_split_atomization",
            "affine_score_preserved",
            "existing_log_materiality_noninferiority_screen_predeclared",
            "default_off_latency_budget_predeclared",
        ],
        "mathematical_form": (
            "For candidate k, the runtime value must be a fixed coefficient "
            "a_k computed before selection; CAMP may score a_k with weights w "
            "as score_k(w)=a_k^T w. The simplex/CVaR/L2 master remains convex "
            "because it optimizes over w, not DP trajectory coordinates."
        ),
        "explicitly_not_authorized": list(BLOCKED_ACTIONS),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    ledger = report["source_family_ledger"]
    lines = [
        "# Post-Pause Source-Family Ledger",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Closed Sources",
        "",
        f"- Closed source-family labels: `{ledger['closed_source_family_labels']}`",
        f"- Closed score families: `{ledger['closed_score_families']}`",
        f"- Closed routes: `{ledger['closed_route_names']}`",
        f"- Closed/existing proxies: `{ledger['closed_or_existing_proxy_families']}`",
        "",
        "## Rejected Proposals",
        "",
        "| Name | Score family | Source family | Reasons |",
        "| --- | --- | --- | --- |",
    ]
    for row in ledger["rejected_source_proposals"]:
        lines.append(
            f"| `{row.get('name')}` | `{row.get('score_family')}` | "
            f"`{row.get('source_family')}` | `{row.get('rejection_reasons')}` |"
        )
    if not ledger["rejected_source_proposals"]:
        lines.append("| `none` | `none` | `none` | `none` |")
    lines.extend(
        [
            "",
            "## Next Proposal Contract",
            "",
        ]
    )
    for item in report["next_source_proposal_contract"]["required_properties"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            report["next_source_proposal_contract"]["mathematical_form"],
            "",
            "This ledger does not authorize training, replay, Full36, formal "
            "seeds, DP modification, online selector promotion, or a DP-side "
            "classical Benders claim.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["ledger_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _blocked_action_conflicts(decision: dict[str, Any]) -> list[str]:
    return [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_empty(name: str, observed: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {
        "name": name,
        "observed": value,
        "expected": [],
        "passed": len(value) == 0,
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise TypeError(f"Expected object JSON at {path}")
    return payload


if __name__ == "__main__":
    main()
