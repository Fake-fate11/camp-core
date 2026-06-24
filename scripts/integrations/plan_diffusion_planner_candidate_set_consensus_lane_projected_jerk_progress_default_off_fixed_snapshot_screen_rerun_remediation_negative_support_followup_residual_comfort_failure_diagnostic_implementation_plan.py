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
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
    REQUIRED_AXES,
    REQUIRED_TABLES,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_implementation_static_contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_STATIC_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "static_contract_review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

STATIC_REVIEW_JSON = "static_contract_review.json"
STATIC_REVIEW_MD = "static_contract_review.md"

PLANNED_DIAGNOSTIC_SCRIPT = (
    "scripts/integrations/analyze_diffusion_planner_candidate_set_consensus_"
    "lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_"
    "remediation_negative_support_followup_residual_comfort_failure_"
    "diagnostics.py"
)
PLANNED_DIAGNOSTIC_TEST = (
    "camp_core/tests/test_diffusion_planner_candidate_set_consensus_lane_"
    "projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_"
    "remediation_negative_support_followup_residual_comfort_failure_"
    "diagnostics.py"
)

REQUIRED_TESTS = (
    "test_residual_comfort_failure_diagnostics_reads_existing_artifacts_only",
    "test_residual_comfort_failure_diagnostics_emits_required_tables",
    "test_residual_comfort_failure_diagnostics_rejects_missing_artifacts",
    "test_residual_comfort_failure_diagnostics_blocks_execution_flags",
    "test_residual_comfort_failure_diagnostics_preserves_math_boundary",
    "test_residual_comfort_failure_diagnostics_cli_writes_outputs",
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
            "Plan-only gate for the read-only residual comfort-failure "
            "diagnostic implementation."
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
    audit_text = _read_text(audit_path)
    review = _static_review_summary(artifact["payload"])
    plan = _implementation_plan(review)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
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
                "support_followup_residual_comfort_failure_diagnostic_"
                "implementation_plan_v1"
            ),
            "label": label,
            "role": "plan-only contract for read-only residual comfort diagnostics",
            "plan_only": True,
            "implementation_code_edit": False,
            "production_implementation_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This plan reads only the completed residual diagnostic static "
                "review artifact and audit authorization. It does not edit "
                "implementation code, create candidates, rerun the screen, run "
                "DP, run replay, use formal seeds, define runtime atoms, choose "
                "lambda online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "modify DP weights or code, or claim a DP-side classical "
                "Benders decomposition."
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
        "diagnostic_implementation_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_review_summary"]
    plan = report["diagnostic_implementation_plan"]
    lines = [
        "# Residual Comfort Diagnostic Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Static-review status: `{review['status']}`",
        "",
        "## Planned Files",
        "",
        f"- `{plan['implementation_scope']['planned_script']}`",
        f"- `{plan['implementation_scope']['planned_test']}`",
        "",
        "## Diagnostic Components",
        "",
    ]
    for component in plan["components"]:
        lines.append(f"### {component['name']}")
        lines.append("")
        lines.append(component["purpose"])
        lines.append("")
        lines.append(f"- Contract: `{component['contract']}`")
        lines.append("")
    lines.extend(["## Required Tables", ""])
    for name in plan["required_tables"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Required Tests", ""])
    for name in plan["required_tests"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Forbidden Work", ""])
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
    plan = _dict(payload.get("plan_summary"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "diagnostic_implementation_plan_authorized": bool(
            decision.get("diagnostic_implementation_plan_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "primary_blocker_family": plan.get("primary_blocker_family"),
        "hard_support_positive": bool(plan.get("hard_support_positive")),
        "comfort_support_positive": bool(plan.get("comfort_support_positive")),
        "positive_support_evidence": bool(plan.get("positive_support_evidence")),
        "replay_evidence_ready": bool(plan.get("replay_evidence_ready")),
        "training_ready": bool(plan.get("training_ready")),
        "read_only_existing_artifacts": bool(plan.get("read_only_existing_artifacts")),
        "no_candidate_reconstruction": bool(plan.get("no_candidate_reconstruction")),
        "json_serializable_scalars_only": bool(
            plan.get("json_serializable_scalars_only")
        ),
        "diagnostic_tables": [str(item) for item in _list(plan.get("diagnostic_tables"))],
        "correlation_axes": [str(item) for item in _list(plan.get("correlation_axes"))],
    }


def _implementation_plan(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "residual_comfort_failure_diagnostic_implementation_plan_only",
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "implementation_scope": {
            "planned_script": PLANNED_DIAGNOSTIC_SCRIPT,
            "planned_test": PLANNED_DIAGNOSTIC_TEST,
            "source_screen_artifact": "negative_support_followup_fixed_snapshot_screen.json",
            "source_attribution_artifact": "failure_attribution.json",
            "source_plan_artifact": "residual_comfort_failure_diagnostic_plan.json",
            "read_only_existing_artifacts": True,
            "current_tick_only": True,
            "json_serializable_scalars_only": True,
            "no_candidate_reconstruction": True,
            "no_reward_recompute": True,
            "no_tracker_recompute": True,
            "no_dp_import": True,
            "score_contract": "score_k(w)=a_k^T w remains unchanged",
            "convex_master_contract": "simplex/CVaR/L2 master remains unchanged",
        },
        "observed_gap": {
            "primary_blocker_family": review["primary_blocker_family"],
            "hard_support_positive": review["hard_support_positive"],
            "comfort_support_positive": review["comfort_support_positive"],
            "positive_support_evidence": review["positive_support_evidence"],
            "replay_evidence_ready": review["replay_evidence_ready"],
            "training_ready": review["training_ready"],
        },
        "components": [
            {
                "name": "artifact_loader_contract",
                "purpose": (
                    "Load only completed fixed-snapshot screen, attribution, "
                    "and diagnostic-plan artifacts, rejecting missing or "
                    "non-parseable inputs without falling back to execution."
                ),
                "contract": "no DP import, no candidate generation, no replay",
            },
            {
                "name": "row_scalar_projection_contract",
                "purpose": (
                    "Project existing candidate-row and snapshot metadata into "
                    "finite scalar fields used by the diagnostic tables."
                ),
                "contract": "no mutation of candidates, scores, selected index, or fallback",
            },
            {
                "name": "comfort_blocker_tables_contract",
                "purpose": (
                    "Emit the required residual comfort blocker tables by "
                    "snapshot, red-stop partition, offset margin, hard/progress "
                    "survivors, comfort deltas, and decision boundary."
                ),
                "contract": "JSON-serializable scalar summaries only",
            },
            {
                "name": "authorization_boundary_contract",
                "purpose": (
                    "Carry explicit false flags for screen rerun, replay, "
                    "formal seeds, Full36, training, promotion, claims, and DP "
                    "modification."
                ),
                "contract": "diagnostic output cannot authorize execution",
            },
        ],
        "required_tables": list(REQUIRED_TABLES),
        "required_axes": list(REQUIRED_AXES),
        "required_tests": list(REQUIRED_TESTS),
        "forbidden_actions": [
            "implementation edits are not authorized in this plan gate",
            "production implementation edits are not authorized",
            "candidate generation execution is not authorized",
            "fixed-snapshot screen rerun is not authorized",
            "replay and closed-loop smoke are not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "CAMP retraining and training execution are not authorized",
            "atom promotion and online selector promotion are not authorized",
            "safety-benefit and CAMP-over-DP-Top-1 claims are not authorized",
            "DP weights, DP code, DP configs, and DP invocation must remain fixed",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_root_exists", artifact["exists"]),
        _check("static_review_json_exists", artifact["json_exists"]),
        _check("static_review_markdown_exists", artifact["markdown_exists"]),
        _check("static_review_json_parseable", bool(artifact["payload"])),
        _check(
            "static_review_markdown_records_title",
            "Static Contract Review" in artifact["markdown_text"],
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_present", bool(audit_text)),
        _check("audit_records_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_implementation_plan", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_no_execution", "candidate_generation_execution_authorized=False" in audit_text),
        _check("audit_records_no_training", "training_execution_authorized=False" in audit_text),
        _check("audit_records_no_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _static_review_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    tables = set(review["diagnostic_tables"])
    axes = set(review["correlation_axes"])
    return [
        _check("static_review_status_complete", review["status"] == STATIC_REVIEW_READY_STATUS),
        _check("static_review_passed", review["passed"] is True),
        _check("static_review_failed_checks_empty", not review["failed_checks"]),
        _check(
            "static_review_authorizes_this_plan",
            review["authorized_next_work"] == STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check(
            "static_review_diagnostic_implementation_plan_authorized",
            review["diagnostic_implementation_plan_authorized"] is True,
        ),
        _check("static_review_no_blocked_actions", not review["blocked_action_conflicts"]),
        _check(
            "static_review_primary_blocker",
            review["primary_blocker_family"] == "comfort_support_zero_after_hard_support_pass",
        ),
        _check("static_review_hard_positive", review["hard_support_positive"] is True),
        _check("static_review_comfort_absent", review["comfort_support_positive"] is False),
        _check("static_review_no_positive_support", review["positive_support_evidence"] is False),
        _check("static_review_replay_not_ready", review["replay_evidence_ready"] is False),
        _check("static_review_training_not_ready", review["training_ready"] is False),
        _check("static_review_read_only", review["read_only_existing_artifacts"] is True),
        _check("static_review_no_candidate_reconstruction", review["no_candidate_reconstruction"] is True),
        _check("static_review_json_scalars", review["json_serializable_scalars_only"] is True),
        *[_check(f"static_review_table_{name}", name in tables) for name in REQUIRED_TABLES],
        *[_check(f"static_review_axis_{name}", name in axes) for name in REQUIRED_AXES],
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    scope = plan["implementation_scope"]
    component_names = {item["name"] for item in plan["components"]}
    text = json.dumps(plan, sort_keys=True).lower()
    return [
        _check("plan_selects_static_review_next", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_selection_type", plan["selection_type"] == "residual_comfort_failure_diagnostic_implementation_plan_only"),
        _check("plan_targets_script", scope["planned_script"] == PLANNED_DIAGNOSTIC_SCRIPT),
        _check("plan_targets_test", scope["planned_test"] == PLANNED_DIAGNOSTIC_TEST),
        _check("plan_reads_existing_artifacts", scope["read_only_existing_artifacts"] is True),
        _check("plan_current_tick_only", scope["current_tick_only"] is True),
        _check("plan_json_scalars", scope["json_serializable_scalars_only"] is True),
        _check("plan_no_candidate_reconstruction", scope["no_candidate_reconstruction"] is True),
        _check("plan_no_reward_recompute", scope["no_reward_recompute"] is True),
        _check("plan_no_tracker_recompute", scope["no_tracker_recompute"] is True),
        _check("plan_no_dp_import", scope["no_dp_import"] is True),
        _check("plan_has_loader_component", "artifact_loader_contract" in component_names),
        _check("plan_has_projection_component", "row_scalar_projection_contract" in component_names),
        _check("plan_has_tables_component", "comfort_blocker_tables_contract" in component_names),
        _check("plan_has_boundary_component", "authorization_boundary_contract" in component_names),
        _check("plan_required_tables_present", set(REQUIRED_TABLES).issubset(set(plan["required_tables"]))),
        _check("plan_required_axes_present", set(REQUIRED_AXES).issubset(set(plan["required_axes"]))),
        _check("plan_required_tests_present", set(REQUIRED_TESTS).issubset(set(plan["required_tests"]))),
        _check("plan_preserves_score", "score_k(w)=a_k^t w" in text),
        _check("plan_preserves_convex_master", "simplex/cvar/l2" in text),
        _check("plan_blocks_execution", "candidate generation execution is not authorized" in text),
        _check("plan_blocks_training", "camp retraining" in text),
        _check("plan_blocks_dp_modification", "dp weights" in text),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    text = json.dumps(plan, sort_keys=True)
    return [
        _check("boundary_authorizes_static_review", decision["diagnostic_implementation_static_contract_review_authorized"] is True),
        _check("boundary_blocks_implementation", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_mentions_no_online_selector", "online selector" in text),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "diagnostic_implementation_plan_ready": passed,
        "diagnostic_implementation_static_contract_review_authorized": passed,
        "implementation_code_edit_authorized": False,
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
