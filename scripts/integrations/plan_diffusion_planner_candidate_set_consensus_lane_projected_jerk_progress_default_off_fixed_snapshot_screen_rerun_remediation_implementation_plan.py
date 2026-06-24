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
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_implementation_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_STATIC_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "static_contract_review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

STATIC_REVIEW_JSON = "static_contract_review.json"
STATIC_REVIEW_MD = "static_contract_review.md"

ALLOWED_NEXT_FILES = (
    "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py",
    "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py",
)

REQUIRED_STATIC_CONTRACTS = (
    "source_failure_mode_coverage_contract",
    "default_off_selection_neutral_contract",
    "current_tick_feature_contract",
    "dp_black_box_fixed_contract",
    "rejected_non_fix_contract",
    "math_boundary_contract",
    "execution_block_contract",
)

PLANNED_POLICY = "comfort_first_lane_projected_red_stop"

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
            "Plan-only implementation gate for the default-off "
            "fixed-snapshot screen rerun remediation. It authorizes only a "
            "later scoped implementation-only gate."
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
    static_review = _static_review_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    plan = _implementation_plan()
    checks = [
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_artifact_checks(artifact),
        *_audit_checks(audit_text),
        *_static_review_checks(static_review),
        *_plan_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_"
                "implementation_plan_v1"
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
        "static_review_summary": static_review,
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
        "# Default-Off Fixed-Snapshot Screen Rerun Remediation Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Static Review",
        "",
        f"- Static-review status: `{review['status']}`",
        f"- Static-review next work: `{review['authorized_next_work']}`",
        f"- Static contracts: `{review['contract_names']}`",
        "",
        "## Allowed Next Files",
        "",
    ]
    for path in plan["allowed_next_files"]:
        lines.append(f"- `{path}`")
    lines.extend(["", "## Planned Policy", "", f"- `{plan['planned_policy']}`", ""])
    lines.extend(["## Components", ""])
    for item in plan["components"]:
        lines.append(f"- `{item['name']}`")
        lines.append(f"  - purpose: {item['purpose']}")
        lines.append(f"  - required behavior: `{item['required_behavior']}`")
        lines.append(f"  - forbidden behavior: {item['forbidden_behavior']}")
    lines.extend(["", "## Verification Plan", ""])
    for item in plan["verification_plan"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundaries", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "## Next Gate",
            "",
            (
                "Only "
                "`candidate_set_consensus_lane_projected_jerk_progress_support_"
                "default_off_fixed_snapshot_screen_rerun_remediation_"
                "implementation_only` is authorized if all checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _implementation_plan() -> dict[str, Any]:
    return {
        "selection_type": "default_off_fixed_snapshot_screen_rerun_remediation_implementation_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "allowed_next_files": list(ALLOWED_NEXT_FILES),
        "planned_policy": PLANNED_POLICY,
        "components": [
            {
                "name": "cli_policy_registration",
                "target_file": ALLOWED_NEXT_FILES[0],
                "purpose": (
                    "register a new opt-in generator_policy without changing "
                    "the current default policy"
                ),
                "required_behavior": "default generator_policy remains lane_centerline_red_stop",
                "forbidden_behavior": "no change to deployed defaults, DP invocation, or online selector",
            },
            {
                "name": "red_stop_distance_window_coverage_partition",
                "target_file": ALLOWED_NEXT_FILES[0],
                "purpose": (
                    "avoid the hard zero-candidate red_stop_distance_window "
                    "partition by emitting bounded eligibility diagnostics and "
                    "a current-tick fallback stop support candidate when safe"
                ),
                "required_behavior": "uses only finite current ego, lane, route, red-stop, and candidate features",
                "forbidden_behavior": "no future outcomes, replay labels, DP edits, or formal seed data",
            },
            {
                "name": "comfort_first_lane_projected_retiming",
                "target_file": ALLOWED_NEXT_FILES[0],
                "purpose": (
                    "construct jerk-limited lane-station stop support before "
                    "existing hard/progress/comfort gates classify candidates"
                ),
                "required_behavior": "candidate trajectories remain finite and deterministic",
                "forbidden_behavior": "no comfort gate relaxation and no hard/progress gate bypass",
            },
            {
                "name": "comfort_blocker_split_diagnostics",
                "target_file": ALLOWED_NEXT_FILES[0],
                "purpose": (
                    "pin command jerk, rollout jerk, command lateral, rollout "
                    "lateral, and progress-loss blocker labels for future "
                    "fixed-snapshot attribution"
                ),
                "required_behavior": "diagnostics are payload-only and do not affect selection",
                "forbidden_behavior": "no selector score, candidate0, fallback, atom schema, or lambda mutation",
            },
            {
                "name": "latency_bounded_candidate_budget",
                "target_file": ALLOWED_NEXT_FILES[0],
                "purpose": (
                    "cap added candidate count and provide deterministic "
                    "bailout metadata for latency attribution"
                ),
                "required_behavior": "bounded loops over margins, offsets, prefix, and bridge grids",
                "forbidden_behavior": "no unbounded search, stochastic sampling, or DP-side expansion",
            },
            {
                "name": "contract_unit_tests",
                "target_file": ALLOWED_NEXT_FILES[1],
                "purpose": (
                    "pin default-off behavior, red-stop partition coverage, "
                    "comfort-first retiming, blocker diagnostics, latency "
                    "budgeting, and math boundaries"
                ),
                "required_behavior": "focused synthetic/static tests only",
                "forbidden_behavior": "no fixed-snapshot rerun, replay, formal seeds, or training in tests",
            },
        ],
        "verification_plan": [
            "py_compile the implementation and route-topology tests",
            "run focused route-topology candidate screen unit tests",
            "run this implementation-plan test and the static-review test",
            "confirm git diff only touches the two allowed next files during implementation-only gate",
            "confirm disabled/default behavior preserves candidate0 and current generator defaults",
        ],
        "blocked_boundaries": [
            "current gate is plan-only; implementation edits are not authorized now",
            "next gate may edit only the allowed CAMP product/test files",
            "candidate generation execution is not authorized by this plan",
            "fixed-snapshot screen rerun is not authorized by this plan",
            "replay, Full36, closed-loop smoke, and formal seeds 11/12/13 remain frozen",
            "CAMP retraining and training execution are not authorized",
            "atom promotion and online selector promotion are not authorized",
            "safety-benefit and CAMP-over-DP-Top-1 claims are not authorized",
            "DP weights, DP code, DP configs, and DP invocation must remain fixed",
            "future atom proposals must prove nonnegative or legal hinge/signed-split score linearity",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / STATIC_REVIEW_JSON
    markdown_path = root / STATIC_REVIEW_MD
    payload = _read_json(payload_path)
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": payload_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "json_sha256": _sha256(payload_path),
        "markdown_sha256": _sha256(markdown_path),
        "payload": payload,
        "markdown_text": _read_text(markdown_path),
    }


def _static_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    contracts = _list(review.get("contracts"))
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
        "contract_names": [str(_dict(item).get("name")) for item in contracts],
        "contract_statuses": {
            str(_dict(item).get("name")): _dict(item).get("status")
            for item in contracts
        },
        "all_contracts_pass": bool(review.get("all_contracts_pass")),
    }


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
) -> list[dict[str, Any]]:
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
        _check("static_review_markdown_records_next_gate", "Next Gate" in artifact["markdown_text"]),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_exists", bool(audit_text)),
        _check("audit_authorizes_implementation_plan", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
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
        _check(
            "static_review_implementation_plan_authorized",
            review["implementation_plan_authorized"] is True,
        ),
        _check("static_review_no_blocked_actions", not review["blocked_action_conflicts"]),
        _check("static_review_all_contracts_pass", review["all_contracts_pass"] is True),
        *[
            _check(
                f"static_review_contract_{name}",
                name in contract_names and review["contract_statuses"].get(name) == "pass",
            )
            for name in REQUIRED_STATIC_CONTRACTS
        ],
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    component_names = {item["name"] for item in plan["components"]}
    component_files = {item["target_file"] for item in plan["components"]}
    return [
        _check("plan_selected_next_work", plan["selected_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_selection_type_plan_only", plan["selection_type"].endswith("_plan_only")),
        _check("plan_allowed_files_exact", tuple(plan["allowed_next_files"]) == ALLOWED_NEXT_FILES),
        _check("plan_components_use_allowed_files", component_files <= set(ALLOWED_NEXT_FILES)),
        _check("plan_registers_opt_in_policy", "cli_policy_registration" in component_names),
        _check("plan_covers_red_stop_partition", "red_stop_distance_window_coverage_partition" in component_names),
        _check("plan_covers_comfort_retiming", "comfort_first_lane_projected_retiming" in component_names),
        _check("plan_covers_blocker_diagnostics", "comfort_blocker_split_diagnostics" in component_names),
        _check("plan_covers_latency_budget", "latency_bounded_candidate_budget" in component_names),
        _check("plan_covers_tests", "contract_unit_tests" in component_names),
        _check("plan_policy_named", plan["planned_policy"] == PLANNED_POLICY),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = "\n".join(plan["blocked_boundaries"])
    return [
        _check("boundary_blocks_current_implementation", "implementation edits are not authorized now" in text),
        _check("boundary_blocks_candidate_generation", "candidate generation execution is not authorized" in text),
        _check("boundary_blocks_screen_rerun", "fixed-snapshot screen rerun is not authorized" in text),
        _check("boundary_blocks_formal_seeds", "formal seeds 11/12/13 remain frozen" in text),
        _check("boundary_blocks_training", "CAMP retraining" in text),
        _check("boundary_blocks_dp_modification", "DP weights" in text),
        _check("boundary_records_math_constraint", "hinge/signed-split" in text),
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
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "implementation_plan_ready": passed,
        "implementation_code_edit_authorized": False,
        "production_implementation_edit_authorized": False,
        "next_gate_implementation_code_edit_authorized": passed,
        "next_gate_allowed_files": plan["allowed_next_files"] if passed else [],
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


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"payload", "markdown_text"}
    }


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
