#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BOUNDARY_STATUS = "post_targeted_safety_support_boundary_ready"
BOUNDARY_NEXT_WORK = (
    "new_current_tick_source_visibility_predeclaration_or_keep_selector_route_paused_only"
)

READY_STATUS = "source_visibility_predeclaration_ready"
PAUSED_STATUS = "source_visibility_predeclaration_no_admissible_source_paused"
BLOCKED_STATUS = "source_visibility_predeclaration_blocked"
AUTHORIZED_NEXT_WORK = "default_off_source_visibility_payload_design_only"
PAUSED_NEXT_WORK = "keep_selector_route_paused_or_submit_new_source_visibility_proposal_only"

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Screen explicit source-visibility predeclarations after the "
            "post-targeted-safety boundary. With no admissible proposal it "
            "records that the fixed-DP CAMP selector route remains paused."
        )
    )
    parser.add_argument("--boundary_json", type=Path, required=True)
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
        boundary=_load_json(args.boundary_json),
        proposals=proposals,
        label=args.label,
        paths={
            "boundary_json": str(args.boundary_json),
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
    boundary: dict[str, Any],
    proposals: list[dict[str, Any]] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proposals = proposals or []
    boundary_summary = _boundary_summary(boundary)
    closed_labels = _string_list(boundary.get("closed_source_labels"))
    boundary_checks = _boundary_checks(boundary_summary)
    proposal_rows = [
        _proposal_row(proposal, closed_labels=closed_labels) for proposal in proposals
    ]
    final = _final_decision(boundary_checks, proposal_rows)
    return {
        "analysis": {
            "name": "dp_camp_source_visibility_predeclaration_screen_v1",
            "label": label,
            "role": (
                "read-only post-boundary screen for a genuinely new current-tick "
                "source visibility proposal"
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
                "This screen creates no atom and runs no selector. A later "
                "accepted source must become a fixed current-tick finite-candidate "
                "coefficient a_k, nonnegative, hinged, or signed-split, so "
                "score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 "
                "master remains convex. No DP-side classical Benders "
                "decomposition is claimed because no DP master/subproblem, "
                "dual, or valid cut is constructed."
            ),
        },
        "boundary_summary": boundary_summary,
        "closed_source_labels": closed_labels,
        "proposal_contract": _proposal_contract(),
        "proposals": proposal_rows,
        "screen_checks": boundary_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _boundary_summary(boundary: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(boundary.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selector_route_paused": bool(decision.get("selector_route_paused")),
        "support_source_ready": bool(decision.get("support_source_ready")),
        "current_selector_route_rejected": bool(
            decision.get("current_camp_dp_selector_route_rejected")
        ),
        "blocked_action_conflicts": _blocked_action_conflicts(decision),
    }


def _boundary_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("boundary_status", summary["status"], BOUNDARY_STATUS),
        _check_equal("boundary_passed", summary["passed"], True),
        _check_equal(
            "boundary_authorizes_source_visibility_or_pause",
            summary["authorized_next_work"],
            BOUNDARY_NEXT_WORK,
        ),
        _check_equal("boundary_selector_route_paused", summary["selector_route_paused"], True),
        _check_equal("boundary_support_source_ready_false", summary["support_source_ready"], False),
        _check_equal(
            "boundary_current_route_rejected",
            summary["current_selector_route_rejected"],
            True,
        ),
        _check_empty(
            "boundary_blocked_action_conflicts_empty",
            summary["blocked_action_conflicts"],
        ),
    ]


def _proposal_row(
    proposal: dict[str, Any],
    *,
    closed_labels: list[str],
) -> dict[str, Any]:
    name = str(proposal.get("name") or proposal.get("source_name") or "<unnamed>")
    source_family = str(proposal.get("source_family") or "")
    score_family = str(proposal.get("score_family") or "")
    claimed_non_equivalent = _string_list(proposal.get("non_equivalence_evidence"))
    checks = [
        _proposal_bool_check(proposal, "current_tick_available_before_selection", True),
        _proposal_bool_check(
            proposal, "candidate_level_or_deterministically_joinable", True
        ),
        _proposal_bool_check(proposal, "finite_or_fail_closed", True),
        _proposal_bool_check(proposal, "deterministic", True),
        _proposal_bool_check(proposal, "uses_future_outcome_or_safetycost_label", False),
        _proposal_bool_check(proposal, "requires_dp_modification", False),
        _proposal_bool_check(proposal, "requires_dp_retraining", False),
        _proposal_bool_check(proposal, "requires_replay_to_compute_runtime_value", False),
        _proposal_bool_check(proposal, "requires_training_to_compute_runtime_value", False),
        _proposal_bool_check(proposal, "default_off_latency_accounted", True),
        _proposal_domain_check(proposal),
        _check_not_in("source_family_not_closed", source_family, set(closed_labels)),
        _check_not_in("score_family_not_closed", score_family, set(closed_labels)),
        _check_nonempty("non_equivalence_evidence_nonempty", claimed_non_equivalent),
    ]
    admissible = all(check["passed"] for check in checks)
    return {
        "name": name,
        "source_family": source_family,
        "score_family": score_family,
        "admissible": admissible,
        "checks": checks,
        "rejection_reasons": [
            check["name"] for check in checks if not check["passed"]
        ],
        "next_gate": (
            "default_off_source_visibility_payload_design"
            if admissible
            else "reject_or_rewrite_source_visibility_proposal"
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
            "atom_value_domain in {nonnegative, hinge, signed_split}",
            "source_family and score_family not in closed_source_labels",
            "non_equivalence_evidence",
        ],
        "explicitly_not_authorized": list(BLOCKED_ACTIONS),
    }


def _final_decision(
    boundary_checks: list[dict[str, Any]],
    proposals: list[dict[str, Any]],
) -> dict[str, Any]:
    boundary_ready = all(check["passed"] for check in boundary_checks)
    admissible = [row for row in proposals if row["admissible"]]
    if not boundary_ready:
        status = BLOCKED_STATUS
        passed = False
        support_ready = False
        selector_paused = False
        authorized_next_work = None
        next_step = "Repair the post-targeted safety support boundary first."
    elif admissible:
        status = READY_STATUS
        passed = True
        support_ready = True
        selector_paused = True
        authorized_next_work = AUTHORIZED_NEXT_WORK
        next_step = (
            "Write a default-off payload design for the accepted source. Do not "
            "run replay, train CAMP, or change online selection before that gate."
        )
    else:
        status = PAUSED_STATUS
        passed = True
        support_ready = False
        selector_paused = True
        authorized_next_work = PAUSED_NEXT_WORK
        next_step = (
            "Keep the selector route paused unless a materially new source "
            "visibility proposal is supplied and passes this screen."
        )
    return {
        "status": status,
        "passed": passed,
        "selector_route_paused": selector_paused,
        "support_source_ready": support_ready,
        "admissible_sources": [row["name"] for row in admissible],
        "rejected_sources": [row["name"] for row in proposals if not row["admissible"]],
        "authorized_next_work": authorized_next_work,
        "next_step": next_step,
        "failed_checks": [check["name"] for check in boundary_checks if not check["passed"]],
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Source Visibility Predeclaration Screen",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Selector route paused: `{decision['selector_route_paused']}`",
        f"- Support source ready: `{decision['support_source_ready']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Boundary",
        "",
    ]
    for key, value in report["boundary_summary"].items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(["", "## Closed Source Labels", ""])
    lines.extend(f"- `{item}`" for item in report["closed_source_labels"])
    lines.extend(
        [
            "",
            "## Proposal Assessment",
            "",
            "| Proposal | Admissible | Source family | Score family | Rejection reasons |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    if report["proposals"]:
        for row in report["proposals"]:
            reasons = ", ".join(row["rejection_reasons"]) or "none"
            lines.append(
                f"| `{row['name']}` | `{row['admissible']}` | "
                f"`{row['source_family']}` | `{row['score_family']}` | "
                f"`{reasons}` |"
            )
    else:
        lines.append("| `none_provided` | `False` | `n/a` | `n/a` | `no proposal` |")
    lines.extend(["", "## Proposal Contract", ""])
    for item in report["proposal_contract"]["required_properties"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON at {path}")
    return payload


def _load_proposals(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    proposals = payload.get("proposals")
    if proposals is None:
        proposals = [payload]
    if not isinstance(proposals, list):
        raise ValueError(f"{path} proposals must be a list.")
    rows = []
    for item in proposals:
        if not isinstance(item, dict):
            raise ValueError(f"{path} proposal entries must be objects.")
        rows.append(item)
    return rows


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _blocked_action_conflicts(decision: dict[str, Any]) -> list[str]:
    return [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]


def _proposal_bool_check(
    proposal: dict[str, Any],
    key: str,
    expected: bool,
) -> dict[str, Any]:
    return _check_equal(key, proposal.get(key), expected)


def _proposal_domain_check(proposal: dict[str, Any]) -> dict[str, Any]:
    domain = proposal.get("atom_value_domain")
    allowed = {"nonnegative", "hinge", "signed_split"}
    return {
        "name": "atom_value_domain_admissible",
        "passed": domain in allowed,
        "actual": domain,
        "expected": sorted(allowed),
    }


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check_empty(name: str, actual: list[Any]) -> dict[str, Any]:
    return {"name": name, "passed": len(actual) == 0, "actual": actual, "expected": []}


def _check_nonempty(name: str, actual: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": len(actual) > 0,
        "actual": actual,
        "expected": "nonempty",
    }


def _check_not_in(name: str, actual: Any, blocked: set[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(actual) and actual not in blocked,
        "actual": actual,
        "expected": f"not in {sorted(blocked)}",
    }


if __name__ == "__main__":
    main()
