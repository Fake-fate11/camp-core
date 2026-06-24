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
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_implementation_plan import (  # noqa: E402
    PLANNED_POLICY,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostics import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as PLAN_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_implementation_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_plan_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

PLAN_JSON = "residual_comfort_failure_diagnostic_plan.json"
PLAN_MD = "residual_comfort_failure_diagnostic_plan.md"

REQUIRED_TABLES = (
    "comfort_blocker_by_snapshot",
    "comfort_blocker_by_red_stop_partition",
    "comfort_blocker_by_offset_margin",
    "hard_progress_survivor_distribution",
    "comfort_delta_quantiles",
    "diagnostic_decision_boundary",
)
REQUIRED_AXES = (
    "failure_class",
    "snapshot_name",
    "red_stop_distance_partition",
    "lateral_offset_scale",
    "red_stop_margin_m",
    "backup_stop_offset_m",
    "hard_feasible",
    "progress_feasible",
    "comfort_admissible",
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
            "Read-only static contract review for the residual comfort-failure "
            "diagnostic plan."
        )
    )
    parser.add_argument("--plan_root", type=Path, default=Path(DEFAULT_PLAN_ROOT))
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
        plan_root=args.plan_root,
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
    plan_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(plan_root)
    audit_text = _read_text(audit_path)
    plan = _plan_summary(artifact["payload"])
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_plan_source_checks(plan),
        *_diagnostic_contract_checks(plan),
        *_boundary_checks(plan),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_static_"
                "contract_review_v1"
            ),
            "label": label,
            "role": "read-only static review of diagnostic plan contracts",
            "read_only": True,
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
                "This review reads only the diagnostic plan artifact and audit "
                "text. It does not edit implementation code, create candidates, "
                "rerun the screen, run DP, run replay, use formal seeds, define "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, change "
                "online selection, modify DP weights or code, or claim a "
                "DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "plan_artifact": _strip_payload(artifact),
        "plan_summary": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["plan_summary"]
    lines = [
        "# Residual Comfort Diagnostic Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Planned policy: `{plan['planned_policy']}`",
        "",
        "## Diagnostic Tables",
        "",
    ]
    for name in plan["diagnostic_tables"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Correlation Axes", ""])
    for name in plan["correlation_axes"]:
        lines.append(f"- `{name}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- implementation edits are not authorized",
            "- candidate generation and screen rerun are not authorized",
            "- replay, Full36, formal seeds, CAMP training, promotion, safety claims, and DP modification are not authorized",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / PLAN_JSON
    markdown_path = root / PLAN_MD
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


def _plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("residual_comfort_diagnostic_plan"))
    scope = _dict(plan.get("diagnostic_scope"))
    observed = _dict(plan.get("observed_gap"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_contract_review_authorized": bool(
            decision.get("static_contract_review_authorized")
        ),
        "planned_policy": scope.get("planned_policy"),
        "read_only_existing_artifacts": bool(scope.get("read_only_existing_artifacts")),
        "no_candidate_reconstruction": bool(scope.get("no_candidate_reconstruction")),
        "json_serializable_scalars_only": bool(
            scope.get("json_serializable_scalars_only")
        ),
        "primary_blocker_family": observed.get("primary_blocker_family"),
        "hard_support_positive": bool(observed.get("hard_support_positive")),
        "comfort_support_positive": bool(observed.get("comfort_support_positive")),
        "positive_support_evidence": bool(observed.get("positive_support_evidence")),
        "replay_evidence_ready": bool(observed.get("replay_evidence_ready")),
        "training_ready": bool(observed.get("training_ready")),
        "diagnostic_tables": [
            str(item.get("name"))
            for item in _list(plan.get("diagnostic_tables"))
            if isinstance(item, dict)
        ],
        "correlation_axes": [str(item) for item in _list(plan.get("correlation_axes"))],
        "static_review_requirements": [
            str(item) for item in _list(plan.get("static_review_requirements"))
        ],
        "blocked_boundaries": [str(item) for item in _list(plan.get("blocked_boundaries"))],
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("plan_root_exists", artifact["exists"]),
        _check("plan_json_exists", artifact["json_exists"]),
        _check("plan_markdown_exists", artifact["markdown_exists"]),
        _check("plan_json_parseable", bool(artifact["payload"])),
        _check("plan_markdown_records_title", "Diagnostic Plan" in artifact["markdown_text"]),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_present", bool(audit_text)),
        _check("audit_records_plan_ready", PLAN_READY_STATUS in audit_text),
        _check("audit_authorizes_static_review", PLAN_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_no_execution", "candidate_generation_execution_authorized=False" in audit_text),
        _check("audit_records_no_training", "training_execution_authorized=False" in audit_text),
        _check("audit_records_no_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _plan_source_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("plan_status_ready", plan["status"] == PLAN_READY_STATUS),
        _check("plan_passed", plan["passed"] is True),
        _check("plan_failed_checks_empty", not plan["failed_checks"]),
        _check("plan_authorizes_this_review", plan["authorized_next_work"] == PLAN_AUTHORIZED_NEXT_WORK),
        _check("plan_static_review_authorized", plan["static_contract_review_authorized"] is True),
        _check("plan_no_blocked_actions", not plan["blocked_action_conflicts"]),
    ]


def _diagnostic_contract_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    tables = set(plan["diagnostic_tables"])
    axes = set(plan["correlation_axes"])
    requirements = " ".join(plan["static_review_requirements"]).lower()
    boundaries = " ".join(plan["blocked_boundaries"]).lower()
    return [
        _check("contract_policy_matches", plan["planned_policy"] == PLANNED_POLICY),
        _check("contract_primary_blocker_matches", plan["primary_blocker_family"] == "comfort_support_zero_after_hard_support_pass"),
        _check("contract_hard_positive", plan["hard_support_positive"] is True),
        _check("contract_comfort_absent", plan["comfort_support_positive"] is False),
        _check("contract_no_positive_support", plan["positive_support_evidence"] is False),
        _check("contract_replay_not_ready", plan["replay_evidence_ready"] is False),
        _check("contract_training_not_ready", plan["training_ready"] is False),
        _check("contract_read_only_artifacts", plan["read_only_existing_artifacts"] is True),
        _check("contract_no_candidate_reconstruction", plan["no_candidate_reconstruction"] is True),
        _check("contract_json_scalars_only", plan["json_serializable_scalars_only"] is True),
        *[_check(f"contract_table_{name}", name in tables) for name in REQUIRED_TABLES],
        *[_check(f"contract_axis_{name}", name in axes) for name in REQUIRED_AXES],
        _check("contract_requires_no_dp_import", "no dp import" in requirements or "dp import" in requirements),
        _check("contract_preserves_score", "score_k(w)=a_k^t w" in requirements),
        _check("contract_preserves_convex_master", "simplex/cvar/l2" in requirements),
        _check("contract_blocks_execution", "candidate generation execution is not authorized" in boundaries),
        _check("contract_blocks_formal_seeds", "formal seeds 11/12/13" in boundaries),
        _check("contract_blocks_claims", "camp-over-dp-top-1" in boundaries),
    ]


def _boundary_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("boundary_blocks_implementation", True),
        _check("boundary_blocks_candidate_generation", True),
        _check("boundary_blocks_screen_rerun", True),
        _check("boundary_blocks_replay", True),
        _check("boundary_blocks_training", plan["training_ready"] is False),
        _check("boundary_blocks_dp_modification", True),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "diagnostic_implementation_plan_authorized": passed,
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
