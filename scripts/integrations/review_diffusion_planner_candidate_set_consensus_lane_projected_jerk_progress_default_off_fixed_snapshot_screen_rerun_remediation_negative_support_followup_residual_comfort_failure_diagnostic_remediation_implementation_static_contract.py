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
    FORMAL_SEEDS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_implementation_plan import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    PLANNED_CONTRACT_TEST,
    PLANNED_ROUTE_TEST,
    PLANNED_SCREEN_SOURCE,
    READY_STATUS as PLAN_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_implementation_static_"
    "contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_implementation_static_"
    "contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_implementation_only"
)
ALLOWED_NEXT_FILES = (
    PLANNED_SCREEN_SOURCE,
    PLANNED_ROUTE_TEST,
    PLANNED_CONTRACT_TEST,
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_IMPLEMENTATION_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_implementation_plan_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

IMPLEMENTATION_PLAN_JSON = "implementation_plan.json"
IMPLEMENTATION_PLAN_MD = "implementation_plan.md"

REQUIRED_STEPS = (
    "default_off_config_pin",
    "command_jerk_descriptor_payload",
    "support_intervention_guardrails",
    "contract_tests_before_execution",
)
REQUIRED_TESTS = (
    "test_residual_comfort_remediation_default_off_preserves_candidate0",
    "test_residual_comfort_remediation_report_only_descriptor_payload",
    "test_residual_comfort_remediation_blocks_candidate_mutation",
    "test_residual_comfort_remediation_blocks_online_selector_and_atoms",
    "test_residual_comfort_remediation_preserves_affine_score_and_convex_master",
    "test_residual_comfort_remediation_blocks_dp_import_reward_tracker_recompute",
    "test_residual_comfort_remediation_blocks_execution_training_replay_formal_seeds",
    "test_residual_comfort_remediation_cli_contract_artifact",
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
        description="Static contract review for the remediation implementation plan."
    )
    parser.add_argument(
        "--implementation_plan_root",
        type=Path,
        default=Path(DEFAULT_IMPLEMENTATION_PLAN_ROOT),
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
        implementation_plan_root=args.implementation_plan_root,
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
    implementation_plan_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(implementation_plan_root)
    source = _implementation_plan_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_source_checks(source),
        *_implementation_contract_checks(source),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_implementation_static_contract_review_v1"
            ),
            "label": label,
            "role": "read-only static review of remediation implementation plan",
            "read_only": True,
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
                "This review reads only the implementation-plan artifact and "
                "audit text. It does not edit implementation code, create "
                "candidates, rerun the screen, run DP, run replay, use formal "
                "seeds, define runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, modify DP weights or "
                "code, or claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "implementation_plan_artifact": _strip_payload(artifact),
        "implementation_plan_summary": source,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Residual Comfort Remediation Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Allowed Next Files",
        "",
    ]
    for path in decision["next_gate_allowed_files"]:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- the current gate does not edit implementation code",
            "- the next gate may edit only the allowed files listed above",
            "- candidate generation execution, fixed-snapshot screen rerun, replay, Full36, and formal seeds are not authorized",
            "- CAMP retraining, atom promotion, online selector promotion, safety claims, CAMP-over-DP-Top-1 claims, and DP modification are not authorized",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / IMPLEMENTATION_PLAN_JSON
    markdown_path = root / IMPLEMENTATION_PLAN_MD
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


def _implementation_plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("remediation_implementation_plan"))
    scope = _dict(plan.get("implementation_scope"))
    analysis = _dict(payload.get("analysis"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "remediation_implementation_plan_ready": bool(
            decision.get("remediation_implementation_plan_ready")
        ),
        "static_contract_review_authorized": bool(
            decision.get("remediation_implementation_static_contract_review_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "selection_type": plan.get("selection_type"),
        "plan_authorized_next_work": plan.get("authorized_next_work"),
        "planned_files": [str(item) for item in _list(scope.get("planned_files"))],
        "scope": scope,
        "implementation_steps": [
            item.get("name")
            for item in _list(plan.get("implementation_steps"))
            if isinstance(item, dict)
        ],
        "required_tests": [str(item) for item in _list(plan.get("required_tests"))],
        "static_review_requirements": [
            str(item) for item in _list(plan.get("static_review_requirements"))
        ],
        "blocked_boundaries": [str(item) for item in _list(plan.get("blocked_boundaries"))],
        "math_boundary": str(analysis.get("math_boundary") or ""),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("implementation_plan_root_exists", artifact["exists"]),
        _check("implementation_plan_json_exists", artifact["json_exists"]),
        _check("implementation_plan_markdown_exists", artifact["markdown_exists"]),
        _check("implementation_plan_json_parseable", bool(artifact["payload"])),
        _check(
            "implementation_plan_markdown_records_title",
            "Residual Comfort Remediation Implementation Plan"
            in artifact["markdown_text"],
        ),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_present", bool(audit_text)),
        _check("audit_records_plan_ready", PLAN_READY_STATUS in audit_text),
        _check("audit_authorizes_static_review", PLAN_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_no_implementation_edit", "implementation_code_edit_authorized=False" in audit_text),
        _check("audit_records_no_execution", "candidate_generation_execution_authorized=False" in audit_text),
        _check("audit_records_no_training", "training_execution_authorized=False" in audit_text),
        _check("audit_records_no_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("plan_status_ready", source["status"] == PLAN_READY_STATUS),
        _check("plan_passed", source["passed"] is True),
        _check("plan_failed_checks_empty", not source["failed_checks"]),
        _check("plan_authorizes_this_review", source["authorized_next_work"] == PLAN_AUTHORIZED_NEXT_WORK),
        _check("plan_ready_flag", source["remediation_implementation_plan_ready"] is True),
        _check("plan_static_review_authorized", source["static_contract_review_authorized"] is True),
        _check("plan_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("plan_selection_type", source["selection_type"] == "residual_comfort_failure_diagnostic_remediation_implementation_plan_only"),
        _check("plan_internal_next_work", source["plan_authorized_next_work"] == PLAN_AUTHORIZED_NEXT_WORK),
    ]


def _implementation_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    scope = source["scope"]
    files = tuple(source["planned_files"])
    steps = set(source["implementation_steps"])
    tests = set(source["required_tests"])
    requirements = " ".join(source["static_review_requirements"]).lower()
    boundaries = " ".join(source["blocked_boundaries"]).lower()
    return [
        _check("contract_allowed_files_exact", files == ALLOWED_NEXT_FILES),
        _check("contract_default_off", scope.get("default_off") is True),
        _check("contract_report_only_until_execution", scope.get("report_only_until_execution_gate") is True),
        _check("contract_current_tick_finite", scope.get("current_tick_finite_candidate_features_only") is True),
        _check("contract_preserve_candidate_ordering", scope.get("preserve_candidate_ordering") is True),
        _check("contract_preserve_candidate0", scope.get("preserve_candidate0") is True),
        _check("contract_no_candidate_mutation", scope.get("no_candidate_mutation") is True),
        _check("contract_no_selected_index_mutation", scope.get("no_selected_index_mutation") is True),
        _check("contract_no_fallback_mutation", scope.get("no_fallback_mutation") is True),
        _check("contract_no_online_selector_change", scope.get("no_online_selector_change") is True),
        _check("contract_no_atom_schema_change", scope.get("no_deployed_atom_schema_change") is True),
        _check("contract_no_dp_import", scope.get("no_dp_import") is True),
        _check("contract_no_reward_recompute", scope.get("no_reward_recompute") is True),
        _check("contract_no_tracker_recompute", scope.get("no_tracker_recompute") is True),
        *[_check(f"contract_step_{name}", name in steps) for name in REQUIRED_STEPS],
        *[_check(f"contract_test_{name}", name in tests) for name in REQUIRED_TESTS],
        _check("contract_requires_candidate0", "candidate0" in requirements),
        _check("contract_requires_no_mutation", "cannot alter candidates" in requirements),
        _check("contract_requires_atom_legality", "nonnegative" in requirements and "hinge/signed-split" in requirements),
        _check("contract_requires_score_affine", "score_k(w)=a_k^t w" in requirements),
        _check("contract_requires_convex_master", "simplex/cvar/l2" in requirements),
        _check("contract_requires_no_dp_changes", "dp code" in requirements and "dp weights" in requirements),
        _check("contract_blocks_implementation_current_gate", "implementation code edits are not authorized" in boundaries),
        _check("contract_blocks_execution", "candidate generation execution is not authorized" in boundaries),
        _check("contract_blocks_formal_seeds", "formal seeds 11/12/13" in boundaries),
        _check("contract_blocks_claims", "camp-over-dp-top-1" in boundaries),
        _check("contract_formal_seed_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_implementation_only", decision["remediation_implementation_only_authorized"] is True),
        _check("boundary_next_gate_scoped_files", tuple(decision["next_gate_allowed_files"]) == ALLOWED_NEXT_FILES),
        _check("boundary_current_gate_no_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_next_gate_allows_scoped_edit", decision["next_gate_implementation_code_edit_authorized"] is True),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_implementation_static_contract_review_complete": passed,
        "remediation_implementation_only_authorized": passed,
        "next_gate_allowed_files": list(ALLOWED_NEXT_FILES) if passed else [],
        "next_gate_implementation_code_edit_authorized": passed,
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
