#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
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

_PLAN_MODULE = (
    "scripts.integrations.plan_diffusion_planner_residual_comfort_remediation_"
    "followup_materially_different_generator_design"
)
_plan = importlib.import_module(_PLAN_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_implementation_plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = _plan.DEFAULT_DEVELOPMENT_ROOT
DEFAULT_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_followup_materially_different_generator_design_plan_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

PLAN_JSON = "materially_different_generator_design_plan.json"
PLAN_MD = "materially_different_generator_design_plan.md"
PLAN_READY_STATUS = _plan.READY_STATUS
PLAN_AUTHORIZED_NEXT_WORK = _plan.AUTHORIZED_NEXT_WORK
EXPECTED_DP_HEAD = _plan.EXPECTED_DP_HEAD
FORMAL_SEEDS = _plan.FORMAL_SEEDS
RESIDUAL_FAMILY = _plan.RESIDUAL_FAMILY

REQUIRED_TRACKS = (
    "lane_station_jerk_limited_stop_synthesis",
    "lateral_heading_continuity_projection",
    "red_timing_progress_guard",
    "hard_progress_comfort_gate_passthrough",
)
REQUIRED_DESCRIPTORS = (
    "command_jerk_hinge",
    "rollout_jerk_hinge",
    "lateral_error_signed_split",
    "progress_retention_hinge",
    "lane_projection_residual_hinge",
)
REQUIRED_REJECTED_NON_FIXES = (
    "comfort_budget_relaxation",
    "rerun_unchanged_generator",
    "train_on_negative_support",
    "selector_or_atom_promotion",
    "dp_side_change",
)
BLOCKED_ACTIONS = _plan.BLOCKED_ACTIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Static contract review of the follow-up materially different "
            "generator design plan."
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
    source = _plan_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    contract = _static_contract(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_source_checks(source),
        *_contract_checks(contract),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_followup_materially_different_generator_static_"
                "contract_review_v1"
            ),
            "label": label,
            "role": "static contract review of materially different generator design",
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
                "This static review reads only the materially different "
                "generator design artifact and audit authorization. It does "
                "not edit implementation code, create candidates, rerun the "
                "screen, run DP, run replay, use formal seeds, define or "
                "promote runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 "
                "master, train CAMP, change online selection, modify DP "
                "weights or code, or claim a DP-side classical Benders "
                "decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "design_plan_artifact": _strip_payload(artifact),
        "design_plan_summary": source,
        "static_contract": contract,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["design_plan_summary"]
    contract = report["static_contract"]
    lines = [
        "# Residual Comfort Materially Different Generator Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        (
            "- Implementation plan authorized: "
            f"`{decision['implementation_plan_authorized']}`"
        ),
        f"- Source plan status: `{source['status']}`",
        f"- Residual family: `{source['residual_family']}`",
        "",
        "## Contract Verdict",
        "",
    ]
    for key, value in contract.items():
        if isinstance(value, bool):
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Required Tracks", ""])
    for item in source["generator_tracks"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Required Descriptor/Atom Contracts", ""])
    for item in source["descriptor_contracts"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Rejected Non-Fixes", ""])
    for item in source["rejected_non_fixes"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Work", ""])
    for item in contract["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _static_contract(source: dict[str, Any]) -> dict[str, Any]:
    source_text = source["source_text"]
    return {
        "current_tick_input_contract": (
            source["has_current_tick_boundary"]
            and "future outcomes" in source_text
            and "formal seeds 11/12/13" in source_text
        ),
        "finite_default_off_append_contract": (
            source["has_finite_candidate_boundary"]
            and "candidate0" in source_text
            and "default behavior" in source_text
        ),
        "material_difference_contract": (
            "comfort-budget relaxation" in source_text
            and "candidate construction" in source_text
        ),
        "hard_progress_comfort_gate_contract": (
            "hard/progress" in source_text
            and "comfort gates" in source_text
            and (
                "earn support" in source_text
                or "support under those gates" in source_text
            )
        ),
        "descriptor_legality_contract": (
            source["has_nonnegative_boundary"]
            and source["has_hinge_signed_split_boundary"]
            and source["has_candidate_local_boundary"]
        ),
        "affine_convex_master_contract": (
            source["has_score_affine_boundary"] and source["has_convex_master_boundary"]
        ),
        "dp_fixed_black_box_contract": (
            "DP weights" in source["source_json_text"]
            and "DP code" in source["source_json_text"]
            and "DP config" in source["source_json_text"]
            and "DP invocation" in source["source_json_text"]
        ),
        "execution_boundary_contract": not source["blocked_action_conflicts"],
        "positive_support_before_training_contract": (
            "positive offline support" in source_text
            or "positive comfort-admissible snapshot support" in source_text
        ),
        "blocked_boundaries": [
            "implementation edits are not authorized by this review",
            "candidate generation execution is not authorized by this review",
            "fixed-snapshot screen rerun is not authorized by this review",
            "closed-loop replay is not authorized by this review",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "CAMP retraining and training execution are not authorized",
            "online selector promotion and atom promotion are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "no DP-side classical Benders claim is authorized",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    json_path = root / PLAN_JSON
    md_path = root / PLAN_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": json_path.is_file(),
        "markdown_exists": md_path.is_file(),
        "json_sha256": _sha256(json_path),
        "markdown_sha256": _sha256(md_path),
        "payload": _read_json(json_path),
        "markdown_text": _read_text(md_path),
    }


def _plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("materially_different_generator_design_plan"))
    target = _dict(plan.get("target_failure"))
    tracks = _names(plan.get("generator_tracks"))
    descriptors = _names(plan.get("descriptor_atom_contract"))
    rejected = _names(plan.get("rejected_non_fixes"))
    source_json_text = json.dumps(payload, sort_keys=True)
    source_text = source_json_text.lower()
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_contract_review_authorized": decision.get("static_contract_review_authorized"),
        "residual_family": target.get("residual_family"),
        "primary_blocker_family": target.get("primary_blocker_family"),
        "generator_tracks": tracks,
        "descriptor_contracts": descriptors,
        "rejected_non_fixes": rejected,
        "source_json_text": source_json_text,
        "source_text": source_text,
        "has_current_tick_boundary": "current-tick" in source_text,
        "has_finite_candidate_boundary": "finite current-tick candidate" in source_text,
        "has_candidate_local_boundary": "candidate-local" in source_text,
        "has_nonnegative_boundary": "nonnegative" in source_text,
        "has_hinge_signed_split_boundary": "hinge/signed-split" in source_text,
        "has_score_affine_boundary": "score_k(w)=a_k^t w" in source_text,
        "has_convex_master_boundary": "simplex/cvar/l2" in source_text,
        "blocked_action_conflicts": sorted(
            key for key in BLOCKED_ACTIONS if decision.get(key) is True
        ),
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("design_plan_root_exists", artifact["exists"]),
        _check("design_plan_json_exists", artifact["json_exists"]),
        _check("design_plan_markdown_exists", artifact["markdown_exists"]),
        _check("design_plan_json_parseable", bool(artifact["payload"])),
        _check(
            "design_plan_markdown_records_title",
            "Materially Different Generator Design Plan" in artifact["markdown_text"],
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
        _check("audit_records_design_plan_ready", PLAN_READY_STATUS in audit_text),
        _check(
            "audit_authorizes_static_contract_review",
            PLAN_AUTHORIZED_NEXT_WORK in audit_text,
        ),
        _check("audit_records_residual_family", RESIDUAL_FAMILY in audit_text),
        _check("audit_records_static_review_authorized", "static_contract_review_authorized=True" in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = set(source["generator_tracks"])
    descriptors = set(source["descriptor_contracts"])
    rejected = set(source["rejected_non_fixes"])
    return [
        _check("design_plan_status_ready", source["status"] == PLAN_READY_STATUS),
        _check("design_plan_passed", source["passed"] is True),
        _check("design_plan_failed_checks_empty", not source["failed_checks"]),
        _check("design_plan_authorizes_this_review", source["authorized_next_work"] == PLAN_AUTHORIZED_NEXT_WORK),
        _check("design_plan_static_review_authorized", source["static_contract_review_authorized"] is True),
        _check("design_plan_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("design_plan_residual_family", source["residual_family"] == RESIDUAL_FAMILY),
        _check("design_plan_primary_blocker", source["primary_blocker_family"] == _plan.PRIMARY_BLOCKER_FAMILY),
        *[_check(f"design_plan_has_track_{name}", name in tracks) for name in REQUIRED_TRACKS],
        *[
            _check(f"design_plan_has_descriptor_{name}", name in descriptors)
            for name in REQUIRED_DESCRIPTORS
        ],
        *[
            _check(f"design_plan_rejects_{name}", name in rejected)
            for name in REQUIRED_REJECTED_NON_FIXES
        ],
        _check("design_plan_current_tick_boundary", source["has_current_tick_boundary"]),
        _check("design_plan_finite_candidate_boundary", source["has_finite_candidate_boundary"]),
        _check("design_plan_candidate_local_boundary", source["has_candidate_local_boundary"]),
        _check("design_plan_nonnegative_boundary", source["has_nonnegative_boundary"]),
        _check("design_plan_hinge_signed_split_boundary", source["has_hinge_signed_split_boundary"]),
        _check("design_plan_score_affine_boundary", source["has_score_affine_boundary"]),
        _check("design_plan_convex_master_boundary", source["has_convex_master_boundary"]),
    ]


def _contract_checks(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("contract_current_tick_inputs", contract["current_tick_input_contract"]),
        _check("contract_finite_default_off_append", contract["finite_default_off_append_contract"]),
        _check("contract_material_difference", contract["material_difference_contract"]),
        _check("contract_hard_progress_comfort_gate", contract["hard_progress_comfort_gate_contract"]),
        _check("contract_descriptor_legality", contract["descriptor_legality_contract"]),
        _check("contract_affine_convex_master", contract["affine_convex_master_contract"]),
        _check("contract_dp_fixed_black_box", contract["dp_fixed_black_box_contract"]),
        _check("contract_execution_boundary", contract["execution_boundary_contract"]),
        _check("contract_positive_support_before_training", contract["positive_support_before_training_contract"]),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_implementation_plan", decision["implementation_plan_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_production_edit", decision["production_implementation_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_full36", decision["full36_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_blocks_safety_claim", decision["safety_benefit_claim_authorized"] is False),
        _check("boundary_blocks_camp_over_dp", decision["camp_over_dp_top1_claim_authorized"] is False),
        _check("boundary_blocks_benders", decision["classic_benders_claim_authorized"] is False),
        _check("boundary_formal_seed_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "materially_different_generator_static_contract_review_complete": passed,
        "implementation_plan_authorized": passed,
        "materially_different_generator_implementation_plan_authorized": passed,
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


def _names(value: Any) -> tuple[str, ...]:
    return tuple(
        item.get("name")
        for item in _list(value)
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
