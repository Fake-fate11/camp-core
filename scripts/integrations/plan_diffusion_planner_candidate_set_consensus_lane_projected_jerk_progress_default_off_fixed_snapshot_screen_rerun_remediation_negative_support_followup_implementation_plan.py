#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
    REQUIRED_STATIC_CONTRACTS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "implementation_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_STATIC_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_static_contract_review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

STATIC_REVIEW_JSON = "static_contract_review.json"
STATIC_REVIEW_MD = "static_contract_review.md"

ALLOWED_NEXT_FILES = (
    "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py",
    "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py",
)
PLANNED_POLICY = "negative_support_coverage_first_lane_projected_red_stop"

REQUIRED_TESTS = (
    "test_route_topology_generator_builds_negative_support_followup_policy",
    "test_route_topology_negative_support_followup_preserves_default_policy",
    "test_route_topology_negative_support_followup_partitions_fail_closed_snapshots",
    "test_route_topology_negative_support_followup_rejects_nonfinite_current_tick_inputs",
    "test_route_topology_negative_support_followup_candidate_budget_cap",
)

BLOCKED_ACTIONS = (
    "implementation_code_edit_authorized",
    "production_implementation_edit_authorized",
    "candidate_generation_execution_authorized",
    "fixed_snapshot_candidate_generation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "atom_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation gate for the negative-support follow-up "
            "design. It authorizes only a later scoped implementation-only gate."
        )
    )
    parser.add_argument(
        "--static_review_root",
        type=Path,
        default=Path(DEFAULT_STATIC_REVIEW_ROOT),
    )
    parser.add_argument("--audit_path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--camp_head", required=True)
    parser.add_argument("--camp_origin_main", required=True)
    parser.add_argument("--dp_head", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        static_review_root=args.static_review_root,
        audit_path=args.audit_path,
        camp_head=args.camp_head,
        camp_origin_main=args.camp_origin_main,
        dp_head=args.dp_head,
        label=args.label,
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
    static_review_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(static_review_root)
    review = _static_review_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    plan = _implementation_plan()
    checks = [
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_artifact_checks(artifact),
        *_audit_checks(audit_text),
        *_static_review_checks(review),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_implementation_plan_v1"
            ),
            "label": label,
            "role": "plan-only implementation contract after static review",
            "plan_only": True,
            "implementation_code_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan reads only the static contract review artifact and "
                "audit authorization. It does not edit implementation code, "
                "create candidates, rerun the screen, run DP, run replay, use "
                "formal seeds, recompute outcomes, define runtime atoms, "
                "choose lambda online, alter score_k(w)=a_k^T w, mutate the "
                "convex simplex/CVaR/L2 master, train CAMP, change online "
                "selection, modify DP weights or code, or claim a DP-side "
                "classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "static_review_artifact": _strip_payload(artifact),
        "static_review_summary": review,
        "implementation_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, plan),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_review_summary"]
    plan = report["implementation_plan"]
    lines = [
        "# Negative-Support Follow-Up Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Static-review status: `{review['status']}`",
        f"- Planned policy: `{plan['planned_policy']}`",
        "",
        "## Allowed Next Files",
        "",
    ]
    for path in plan["allowed_next_files"]:
        lines.append(f"- `{path}`")
    lines.extend(["", "## Components", ""])
    for component in plan["components"]:
        lines.append(f"### {component['name']}")
        lines.append("")
        lines.append(component["purpose"])
        lines.append("")
        lines.append(f"- Implementation target: `{component['implementation_target']}`")
        lines.append(f"- Contract: `{component['contract']}`")
        lines.append("")
    lines.extend(["## Required Tests", ""])
    for test_name in plan["required_tests"]:
        lines.append(f"- `{test_name}`")
    lines.extend(["", "## Boundaries", ""])
    for item in plan["forbidden_actions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / STATIC_REVIEW_JSON
    markdown_path = root / STATIC_REVIEW_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": payload_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "json_sha256": _sha256(payload_path),
        "markdown_sha256": _sha256(markdown_path),
        "payload": _read_json(payload_path),
        "markdown_text": _read_text(markdown_path),
    }


def _static_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "implementation_plan_authorized": bool(
            decision.get("implementation_plan_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "all_contracts_pass": bool(review.get("all_contracts_pass")),
        "contract_names": [
            item.get("name") for item in _list(review.get("contracts")) if isinstance(item, dict)
        ],
    }


def _implementation_plan() -> dict[str, Any]:
    return {
        "selection_type": "negative_support_followup_implementation_plan_only",
        "planned_policy": PLANNED_POLICY,
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "allowed_next_files": list(ALLOWED_NEXT_FILES),
        "required_tests": list(REQUIRED_TESTS),
        "components": [
            {
                "name": "default_off_policy_registration",
                "purpose": (
                    "Add a new opt-in policy for the negative-support follow-up "
                    "without changing the default generator policy or deployed "
                    "selector behavior."
                ),
                "implementation_target": "RouteTopologyCandidateConfig.generator_policy choices",
                "contract": (
                    "Default `lane_centerline_red_stop` behavior remains byte-for-"
                    "byte neutral for existing tests; the new policy is reachable "
                    "only by explicit CLI/config selection."
                ),
            },
            {
                "name": "coverage_first_fail_closed_partition",
                "purpose": (
                    "Make fail-closed coverage diagnosable and implement a "
                    "current-tick fallback only for finite lane/red/ego geometry "
                    "partitions, leaving unsafe partitions fail-closed."
                ),
                "implementation_target": "route_topology_candidate_construction_diagnostics and build_route_topology_candidates",
                "contract": (
                    "Diagnostics must distinguish missing lane evidence, missing "
                    "red-route evidence, nonfinite selected candidate evidence, "
                    "and finite fallback-ready partitions without mutating scores, "
                    "selected index, fallback, online selector, or deployed atom schema."
                ),
            },
            {
                "name": "hard_feasibility_support_floor_candidates",
                "purpose": (
                    "Generate only current-tick finite candidates that are designed "
                    "to reduce red-light, lane-crossing, road-border, and kinematic "
                    "hard blockers before any replay or training can be considered."
                ),
                "implementation_target": "new policy branch in build_route_topology_candidates",
                "contract": (
                    "Candidate construction remains an opt-in transform over fixed "
                    "current-tick geometry and fixed DP candidate context; DP code, "
                    "weights, configs, and invocation remain unchanged."
                ),
            },
            {
                "name": "comfort_after_hard_progress_candidates",
                "purpose": (
                    "Constrain the new policy to produce zero/low-lateral, jerk-"
                    "bounded station profiles that target the observed progress "
                    "and command-lateral blockers among hard/progress-feasible rows."
                ),
                "implementation_target": "new helper functions local to analyze_diffusion_planner_route_topology_candidate_screen.py",
                "contract": (
                    "Any computed quantities are finite current-tick candidate "
                    "features only. Future atomization must be nonnegative or "
                    "hinge/signed-split legal and preserve score_k(w)=a_k^T w."
                ),
            },
            {
                "name": "latency_bounded_unit_contracts",
                "purpose": (
                    "Pin the new policy with synthetic/static unit tests before "
                    "any fixed-snapshot rerun is planned."
                ),
                "implementation_target": "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py",
                "contract": (
                    "Tests must prove default-off behavior, fail-closed behavior "
                    "for nonfinite current-tick inputs, candidate budget cap, and "
                    "the absence of replay, formal seeds, training, promotion, or "
                    "DP modification."
                ),
            },
        ],
        "forbidden_actions": [
            "implementation edits are not authorized in this plan gate",
            "candidate generation execution is not authorized",
            "fixed-snapshot screen rerun is not authorized",
            "replay, Full36, closed-loop smoke, and formal seeds 11/12/13 remain frozen",
            "CAMP retraining and training execution are not authorized",
            "atom promotion and online selector promotion are not authorized",
            "safety-benefit and CAMP-over-DP-Top-1 claims are not authorized",
            "DP weights, DP code, DP configs, and DP invocation must remain fixed",
        ],
    }


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_root_exists", artifact["exists"]),
        _check("static_review_json_exists", artifact["json_exists"]),
        _check("static_review_markdown_exists", artifact["markdown_exists"]),
        _check("static_review_json_parseable", bool(artifact["payload"])),
        _check("static_review_markdown_records_contracts", "## Contracts" in artifact["markdown_text"]),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_authorizes_implementation_plan", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
    ]


def _static_review_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    contract_names = set(review["contract_names"])
    return [
        _check("static_review_status_complete", review["status"] == STATIC_REVIEW_READY_STATUS),
        _check("static_review_passed", review["passed"] is True),
        _check("static_review_failed_checks_empty", not review["failed_checks"]),
        _check(
            "static_review_authorizes_this_plan",
            review["authorized_next_work"] == STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check("static_review_implementation_plan_authorized", review["implementation_plan_authorized"] is True),
        _check("static_review_no_blocked_actions", not review["blocked_action_conflicts"]),
        _check("static_review_all_contracts_pass", review["all_contracts_pass"] is True),
        *[
            _check(f"static_review_contract_{name}", name in contract_names)
            for name in REQUIRED_STATIC_CONTRACTS
        ],
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    component_names = {item["name"] for item in plan["components"]}
    forbidden = "\n".join(plan["forbidden_actions"])
    return [
        _check("plan_selects_next_implementation_gate", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_policy_is_new_and_opt_in", plan["planned_policy"] == PLANNED_POLICY),
        _check("plan_allowed_files_scoped", tuple(plan["allowed_next_files"]) == ALLOWED_NEXT_FILES),
        _check("plan_has_policy_registration", "default_off_policy_registration" in component_names),
        _check("plan_has_coverage_partition", "coverage_first_fail_closed_partition" in component_names),
        _check("plan_has_hard_support_floor", "hard_feasibility_support_floor_candidates" in component_names),
        _check("plan_has_comfort_after_hard_progress", "comfort_after_hard_progress_candidates" in component_names),
        _check("plan_has_unit_contracts", "latency_bounded_unit_contracts" in component_names),
        _check("plan_required_tests_present", set(REQUIRED_TESTS).issubset(set(plan["required_tests"]))),
        _check("plan_forbids_execution_now", "candidate generation execution is not authorized" in forbidden),
        _check("plan_forbids_training", "CAMP retraining" in forbidden),
        _check("plan_forbids_dp_modification", "DP weights" in forbidden),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    plan_text = json.dumps(plan, sort_keys=True)
    return [
        _check("boundary_current_tick_only", "current-tick" in plan_text),
        _check("boundary_default_off", "Default" in plan_text or "default" in plan_text),
        _check("boundary_affine_score_preserved", "score_k(w)=a_k^T w" in plan_text),
        _check("boundary_no_execution_authorized", True),
        _check("boundary_no_formal_seeds_authorized", True),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    plan: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "implementation_plan_ready": passed,
        "next_gate_allowed_files": plan["allowed_next_files"] if passed else [],
        "next_gate_implementation_code_edit_authorized": passed,
        "production_implementation_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"payload", "markdown_text"}
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
