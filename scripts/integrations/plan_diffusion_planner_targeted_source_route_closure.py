#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUPPORT_REJECT_STATUS = "new_no_leak_targeted_support_source_not_available"
SCORE_INVENTORY_STATUS = "no_leak_score_family_inventory_requires_new_design"
TENSOR_VISIBILITY_STATUS = "current_tick_tensor_visibility_no_new_candidate_source"
TENSOR_VISIBILITY_GAP = "visible_candidate_tensor_sources_already_closed"
PROOF_PROTOCOL_STATUS = "proof_protocol_redesign_required"

CLOSED_STATUS = "targeted_source_discovery_route_closed"
BLOCKED_STATUS = "targeted_source_discovery_route_source_blocked"
AUTHORIZED_NEXT_WORK = "proof_protocol_v2_or_scenario_objective_redesign_only"

REQUIRED_CLOSED_SCORE_FAMILIES = (
    "non_turn_interaction_family",
    "observable_interaction_family",
    "progress_lane_hard_context",
    "relaxed_strict_atom_family",
    "revised_context_atom_family",
    "turn_logit_atom_family",
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
            "Read-only closure gate for the targeted CAMP-on-DP source "
            "discovery route. It connects the latest no-leak support rejection "
            "with the refreshed score-family and tensor-visibility closures."
        )
    )
    parser.add_argument("--support_reject_json", type=Path, required=True)
    parser.add_argument("--score_family_inventory_json", type=Path, required=True)
    parser.add_argument("--tensor_visibility_json", type=Path, required=True)
    parser.add_argument("--proof_protocol_redesign_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        support_reject=_load_json(args.support_reject_json),
        score_family_inventory=_load_json(args.score_family_inventory_json),
        tensor_visibility=_load_json(args.tensor_visibility_json),
        proof_protocol_redesign=(
            None
            if args.proof_protocol_redesign_json is None
            else _load_json(args.proof_protocol_redesign_json)
        ),
        label=args.label,
        paths={
            "support_reject_json": str(args.support_reject_json),
            "score_family_inventory_json": str(args.score_family_inventory_json),
            "tensor_visibility_json": str(args.tensor_visibility_json),
            "proof_protocol_redesign_json": (
                None
                if args.proof_protocol_redesign_json is None
                else str(args.proof_protocol_redesign_json)
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
    support_reject: dict[str, Any],
    score_family_inventory: dict[str, Any],
    tensor_visibility: dict[str, Any],
    proof_protocol_redesign: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    checks = _source_checks(
        support_reject=support_reject,
        score_family_inventory=score_family_inventory,
        tensor_visibility=tensor_visibility,
        proof_protocol_redesign=proof_protocol_redesign,
    )
    final = _final_decision(checks)
    return {
        "analysis": {
            "name": "dp_camp_targeted_source_route_closure_v1",
            "label": label,
            "role": (
                "read-only closure gate proving the targeted source-discovery "
                "path has no currently admissible no-leak candidate-level "
                "runtime source"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "paths": paths or {},
            "math_boundary": (
                "This gate only reads prior JSON artifacts and source-visibility "
                "decisions. It creates no atom, trains no weights, runs no DP, "
                "and uses no outcome label as a runtime input. CAMP's future "
                "runtime score must remain affine score_k(w)=a_k^T w over "
                "fixed current-tick finite-candidate coefficients, preserving "
                "the convex simplex/CVaR/L2 master. No DP-side classical "
                "Benders master/subproblem, dual, or cut is constructed."
            ),
        },
        "closed_score_families": _closed_score_families(score_family_inventory),
        "tensor_visibility_summary": _tensor_summary(tensor_visibility),
        "source_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_checks(
    *,
    support_reject: dict[str, Any],
    score_family_inventory: dict[str, Any],
    tensor_visibility: dict[str, Any],
    proof_protocol_redesign: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    support_decision = support_reject.get("final_decision") or {}
    score_decision = score_family_inventory.get("final_decision") or {}
    tensor_decision = tensor_visibility.get("final_decision") or {}
    tensor_source_gate = tensor_visibility.get("source_gate") or {}
    closed_families = _closed_score_families(score_family_inventory)
    missing_closed = sorted(set(REQUIRED_CLOSED_SCORE_FAMILIES) - set(closed_families))
    checks = [
        _check_equal("support_reject_status", support_decision.get("status"), SUPPORT_REJECT_STATUS),
        _check_equal("support_reject_passed", support_decision.get("passed"), True),
        _check_equal(
            "support_source_not_ready",
            support_decision.get("support_source_ready"),
            False,
        ),
        _check_equal(
            "support_rejects_current_route",
            support_decision.get("current_camp_dp_selector_route_rejected"),
            True,
        ),
        _check_equal(
            "score_inventory_status",
            score_decision.get("status"),
            SCORE_INVENTORY_STATUS,
        ),
        _check_empty("score_inventory_missing_required_closed", missing_closed),
        _check_empty(
            "score_inventory_unclosed_support",
            score_decision.get("unclosed_support_families") or [],
        ),
        _check_equal(
            "tensor_visibility_status",
            tensor_decision.get("status"),
            TENSOR_VISIBILITY_STATUS,
        ),
        _check_equal(
            "tensor_visibility_primary_gap",
            tensor_decision.get("primary_gap"),
            TENSOR_VISIBILITY_GAP,
        ),
        _check_empty(
            "tensor_visibility_no_candidate_sources",
            tensor_decision.get("candidate_source_names") or [],
        ),
        _check_contains(
            "tensor_visibility_closes_turn_indicator_logits",
            tensor_decision.get("closed_visible_candidate_source_names") or [],
            "turn_indicator_logits",
        ),
        _check_equal("tensor_visibility_source_not_stale", tensor_source_gate.get("stale"), False),
        *_blocked_action_checks(support_decision, "support_reject"),
        *_blocked_action_checks(score_decision, "score_inventory"),
        *_blocked_action_checks(tensor_decision, "tensor_visibility"),
    ]
    if proof_protocol_redesign is not None:
        proof_decision = proof_protocol_redesign.get("final_decision") or {}
        checks.extend(
            [
                _check_equal(
                    "proof_protocol_redesign_status",
                    proof_decision.get("status"),
                    PROOF_PROTOCOL_STATUS,
                ),
                *_blocked_action_checks(proof_decision, "proof_protocol_redesign"),
            ]
        )
    return checks


def _closed_score_families(report: dict[str, Any]) -> list[str]:
    rows = report.get("score_families")
    closed: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("status") == "rejected_or_limited" and row.get("name"):
                closed.append(str(row["name"]))
    return sorted(set(closed))


def _tensor_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    rows = report.get("tensor_sources") or []
    if not isinstance(rows, list):
        rows = []
    return {
        "status": decision.get("status"),
        "primary_gap": decision.get("primary_gap"),
        "candidate_source_names": decision.get("candidate_source_names") or [],
        "closed_visible_candidate_source_names": (
            decision.get("closed_visible_candidate_source_names") or []
        ),
        "tensor_sources": [
            {
                "name": row.get("name"),
                "visibility_status": row.get("visibility_status"),
                "closed_by_score_inventory": row.get("closed_by_score_inventory"),
            }
            for row in rows
            if isinstance(row, dict)
        ],
    }


def _final_decision(checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(check["passed"] for check in checks)
    if passed:
        status = CLOSED_STATUS
        authorized_next_work = AUTHORIZED_NEXT_WORK
        next_step = (
            "Do not reopen closed atom/source families. Continue only with "
            "ProofProtocol v2 or scenario-objective redesign, or keep the "
            "current CAMP-DP selector route paused."
        )
    else:
        status = BLOCKED_STATUS
        authorized_next_work = None
        next_step = (
            "Repair or refresh the failed source artifacts before claiming "
            "targeted source discovery is closed."
        )
    return {
        "status": status,
        "passed": passed,
        "source_discovery_closed": passed,
        "current_camp_dp_selector_route_rejected": passed,
        "authorized_next_work": authorized_next_work,
        "next_step": next_step,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Targeted Source Route Closure",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Source discovery closed: `{decision['source_discovery_closed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Closed Score Families",
        "",
    ]
    for family in report["closed_score_families"]:
        lines.append(f"- `{family}`")
    tensor = report["tensor_visibility_summary"]
    lines.extend(
        [
            "",
            "## Tensor Visibility",
            "",
            f"- Status: `{tensor['status']}`",
            f"- Primary gap: `{tensor['primary_gap']}`",
            f"- Candidate sources: `{tensor['candidate_source_names']}`",
            f"- Closed visible sources: `{tensor['closed_visible_candidate_source_names']}`",
            "",
            "| Source | Visibility | Closed |",
            "| --- | --- | ---: |",
        ]
    )
    for row in tensor["tensor_sources"]:
        lines.append(
            f"| `{row['name']}` | `{row['visibility_status']}` | "
            f"`{row['closed_by_score_inventory']}` |"
        )
    lines.extend(
        [
            "",
            "## Source Checks",
            "",
            "| Check | Passed | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["source_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | {_check_detail(check)} |"
        )
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


def _check_contains(name: str, observed: list[Any], expected_item: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": expected_item in observed,
        "observed": observed,
        "expected": f"contains {expected_item}",
    }


def _check_detail(check: dict[str, Any]) -> str:
    return f"`observed={check.get('observed')}; expected={check.get('expected')}`"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
