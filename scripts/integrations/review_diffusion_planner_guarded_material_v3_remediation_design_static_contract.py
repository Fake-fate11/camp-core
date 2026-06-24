#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations.plan_diffusion_planner_guarded_material_v3_failure_attribution_remediation_design import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    EXPECTED_DP_HEAD,
    READY_STATUS as PLAN_READY_STATUS,
)


DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DEFAULT_PLAN_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "guarded_rerun_failure_attribution_remediation_v3_design_plan_bff8f8b"
)
PLAN_JSON = "design_plan.json"
PLAN_MD = "design_plan.md"

READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_plan_only"
)

REQUIRED_TRACKS = (
    "ready_diagnostic_candidate_materialization",
    "row_generation_accounting_guard",
    "red_stop_distance_window_fail_closed_partition",
    "comfort_first_budget_preservation",
    "positive_support_before_execution_gate",
)
REQUIRED_DESCRIPTORS = (
    "finite_candidate_materialization_flag_v4",
    "stop_window_margin_hinges_v4",
    "lane_progress_comfort_signed_splits_v4",
    "candidate_accounting_gap_report_only_v4",
    "affine_convex_master_preservation",
)
REQUIRED_REJECTED_NON_FIXES = (
    "train_on_zero_support",
    "rerun_v3_as_is",
    "gate_relaxation",
    "formal_seed_probe",
    "dp_side_change",
    "online_selector_or_atom_promotion",
)
REQUIRED_FUTURE_EXIT_CRITERIA = (
    "static_contract_review_complete",
    "implementation_plan_authorized_only_after_static_contract",
    "default_off_implementation_unit_tests_show_positive_materialization",
    "post_implementation_static_contract_review_complete",
    "fixed_snapshot_screen_rerun_plan_before_any_execution",
    "training_execution_authorized_true_before_any_camp_retraining",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Static contract review of the guarded material v3 design plan."
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
    source = _plan_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    review = _static_contract_review(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_source_checks(source),
        *_review_checks(review),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_guarded_material_v3_remediation_design_static_contract_review",
            "label": label,
            "role": "static contract review only",
            "static_review_only": True,
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
                "This review reads only the design-plan artifact and audit. It "
                "does not edit implementation, create candidates, rerun any "
                "screen, run DP, run replay, use formal seeds, train CAMP, "
                "promote atoms, change online selection, or modify DP. The "
                "review requires finite current-tick candidate features, "
                "nonnegative or hinge/signed-split legality, preserved "
                "score_k(w)=a_k^T w, and preserved convex simplex/CVaR/L2 "
                "master before an implementation plan can be considered."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "plan_artifact": _strip_payload(artifact),
        "plan_summary": source,
        "static_contract_review": review,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# Guarded Material v3 Remediation Design Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation plan authorized: `{decision['implementation_plan_authorized']}`",
        f"- Implementation code edit authorized: `{decision['implementation_code_edit_authorized']}`",
        "",
        "## Required Contracts",
        "",
    ]
    for item in review["required_contracts"]:
        lines.append(f"- `{item['name']}`: `{item['passed']}`")
    lines.extend(["", "## Boundaries", ""])
    for item in review["boundaries"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": (root / PLAN_JSON).is_file(),
        "md_exists": (root / PLAN_MD).is_file(),
        "json_sha256": _sha256(root / PLAN_JSON),
        "md_sha256": _sha256(root / PLAN_MD),
        "payload": _read_json(root / PLAN_JSON),
        "markdown": _read_text(root / PLAN_MD),
    }


def _plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    plan = _dict(payload.get("remediation_design_plan"))
    tracks = _items_by_name(plan.get("remediation_tracks"))
    descriptors = _items_by_name(plan.get("descriptor_atom_contract"))
    rejected = _items_by_name(plan.get("rejected_non_fixes"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "remediation_design_plan_ready": bool(decision.get("remediation_design_plan_ready")),
        "static_contract_review_authorized": bool(decision.get("static_contract_review_authorized")),
        "blocked_authorizations": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "analysis": analysis,
        "target_failure": _dict(plan.get("target_failure")),
        "tracks": tracks,
        "descriptors": descriptors,
        "rejected_non_fixes": rejected,
        "future_exit_criteria": _string_set(plan.get("future_exit_criteria")),
        "math_boundary": str(analysis.get("math_boundary") or ""),
    }


def _static_contract_review(source: dict[str, Any]) -> dict[str, Any]:
    descriptors = source["descriptors"]
    contracts = [
        {
            "name": "default_off_plan_only",
            "passed": source["analysis"].get("plan_only") is True
            and source["analysis"].get("implementation_code_edit") is False,
        },
        {
            "name": "finite_candidate_materialization_current_tick",
            "passed": _contains(
                descriptors,
                "finite_candidate_materialization_flag_v4",
                ("current-tick", "affine"),
            ),
        },
        {
            "name": "nonnegative_stop_window_hinges",
            "passed": _contains(
                descriptors,
                "stop_window_margin_hinges_v4",
                ("nonnegative", "hinge"),
            ),
        },
        {
            "name": "signed_split_legality",
            "passed": _contains(
                descriptors,
                "lane_progress_comfort_signed_splits_v4",
                ("signed", "nonnegative"),
            ),
        },
        {
            "name": "diagnostics_report_only_until_promotion",
            "passed": _contains(
                descriptors,
                "candidate_accounting_gap_report_only_v4",
                ("report-only", "cannot alter"),
            ),
        },
        {
            "name": "affine_score_and_convex_master_preserved",
            "passed": _contains(
                descriptors,
                "affine_convex_master_preservation",
                ("score_k(w)=a_k^T w", "convex"),
            ),
        },
        {
            "name": "future_execution_requires_positive_materialization_tests",
            "passed": "default_off_implementation_unit_tests_show_positive_materialization"
            in source["future_exit_criteria"],
        },
        {
            "name": "formal_seed_dp_training_promotions_rejected",
            "passed": all(name in source["rejected_non_fixes"] for name in REQUIRED_REJECTED_NON_FIXES),
        },
    ]
    return {
        "required_contracts": contracts,
        "boundaries": [
            "static review only",
            "no implementation edit",
            "no candidate generation or screen rerun",
            "no replay, formal seeds, Full36, or CAMP retraining",
            "no atom or online selector promotion",
            "no DP modification",
            "no safety or CAMP-over-DP-Top-1 claim",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("plan_root_exists", bool(artifact["exists"])),
        _check("plan_json_exists", bool(artifact["json_exists"])),
        _check("plan_md_exists", bool(artifact["md_exists"])),
        _check("plan_json_parseable", bool(artifact["payload"])),
        _check("plan_md_mentions_design", "Zero Candidate Support Remediation Design Plan" in artifact["markdown"]),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_records_design_plan_ready", PLAN_READY_STATUS in audit_text),
        _check("audit_authorizes_static_contract_review", PLAN_AUTHORIZED_NEXT_WORK in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("plan_status_ready", source["status"] == PLAN_READY_STATUS),
        _check("plan_authorizes_static_review", source["authorized_next_work"] == PLAN_AUTHORIZED_NEXT_WORK),
        _check("plan_ready_flag", source["remediation_design_plan_ready"] is True),
        _check("plan_static_review_authorized", source["static_contract_review_authorized"] is True),
        _check("plan_no_blocked_authorizations", not source["blocked_authorizations"]),
        _check("plan_target_zero_candidate_support", source["target_failure"].get("candidate_rows_sum") == 0),
        *[_check(f"plan_track_{name}", name in source["tracks"]) for name in REQUIRED_TRACKS],
        *[_check(f"plan_descriptor_{name}", name in source["descriptors"]) for name in REQUIRED_DESCRIPTORS],
        *[
            _check(f"plan_rejects_{name}", name in source["rejected_non_fixes"])
            for name in REQUIRED_REJECTED_NON_FIXES
        ],
        *[
            _check(f"plan_exit_{name}", name in source["future_exit_criteria"])
            for name in REQUIRED_FUTURE_EXIT_CRITERIA
        ],
    ]


def _review_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(
            f"review_contract_{item['name']}",
            bool(item["passed"]),
        )
        for item in review["required_contracts"]
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_blocks_implementation_code", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_production_edit", decision["production_implementation_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_full36", decision["full36_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "static_contract_review_complete": passed,
        "implementation_plan_authorized": passed,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


def _contains(items: dict[str, dict[str, Any]], name: str, tokens: tuple[str, ...]) -> bool:
    contract = str(_dict(items.get(name)).get("contract") or "")
    return all(token in contract for token in tokens)


def _items_by_name(value: Any) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    if not isinstance(value, list):
        return items
    for item in value:
        item_dict = _dict(item)
        name = item_dict.get("name")
        if isinstance(name, str):
            items[name] = item_dict
    return items


def _string_set(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({item for item in value if isinstance(item, str)})


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"payload", "markdown"}
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
