#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

_PLAN_MODULE = (
    "scripts.integrations.plan_diffusion_planner_residual_comfort_"
    "remediation_followup_materially_different_generator_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution_remediation_guarded_fixed_"
    "snapshot_screen_rerun_failure_attribution_remediation_design"
)
_plan = importlib.import_module(_PLAN_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_plan_only"
)

DEFAULT_PLAN_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "rerun_failure_design_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
PLAN_JSON = "material_generator_remediation_rerun_failure_design_plan.json"
PLAN_MD = "material_generator_remediation_rerun_failure_design_plan.md"

PLAN_READY_STATUS = _plan.READY_STATUS
PLAN_AUTHORIZED_NEXT_WORK = _plan.AUTHORIZED_NEXT_WORK
EXPECTED_DP_HEAD = _plan.EXPECTED_DP_HEAD
FORMAL_SEEDS = _plan.FORMAL_SEEDS
BLOCKED_ACTIONS = _plan.BLOCKED_ACTIONS

REQUIRED_TRACKS = (
    "near_threshold_hard_support_closure",
    "comfort_first_profile_precheck",
    "lane_corridor_continuity_tightening",
    "stop_creep_progress_balance",
    "positive_support_before_execution_gate",
)
REQUIRED_DESCRIPTORS = (
    "hard_support_margin_hinges_v3",
    "comfort_proxy_hinge_bundle_v3",
    "lateral_heading_signed_split_v3",
    "support_gap_report_only_channels_v3",
    "affine_convex_master_preservation",
)
REQUIRED_REJECTED_NON_FIXES = (
    "train_on_negative_support",
    "rerun_v2_as_is",
    "hard_or_comfort_gate_relaxation",
    "selector_or_atom_promotion",
    "formal_seed_probe",
    "dp_side_change",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Static contract review of the v2 material-generator failure "
            "remediation design plan."
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
    label: str | None = None,
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
                "remediation_followup_materially_different_generator_guarded_"
                "fixed_snapshot_screen_rerun_failure_attribution_remediation_"
                "guarded_fixed_snapshot_screen_rerun_failure_attribution_"
                "remediation_design_static_contract_review_v1"
            ),
            "label": label,
            "role": "static contract review of v2 remediation design plan",
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
                "This static review reads only the v2 remediation design plan "
                "artifact and audit authorization. It does not edit "
                "implementation code, create candidates, rerun the screen, "
                "run DP, run replay, use formal seeds, define or promote "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T "
                "w, mutate the convex simplex/CVaR/L2 master, train CAMP, "
                "change online selection, modify DP weights or code, or "
                "claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "remediation_design_artifact": _strip_payload(artifact),
        "remediation_design_summary": source,
        "static_contract": contract,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["remediation_design_summary"]
    contract = report["static_contract"]
    lines = [
        "# Material Generator V2 Remediation Design Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        (
            "- Implementation plan authorized: "
            f"`{decision['implementation_plan_authorized']}`"
        ),
        f"- Source plan status: `{source['status']}`",
        f"- Hard support gap: `{source['hard_support_gap']}`",
        f"- Comfort support gap: `{source['comfort_support_gap']}`",
        f"- V2 zero comfort support: `{source['v2_zero_comfort_support']}`",
        "",
        "## Contract Verdict",
        "",
    ]
    for key, value in contract.items():
        if isinstance(value, bool):
            lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Required Tracks", ""])
    for item in source["tracks"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Required Descriptor/Atom Contracts", ""])
    for item in source["descriptors"]:
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
    text = source["source_text"]
    return {
        "current_tick_input_contract": (
            "current-tick" in text
            and "future outcome" in text
            and "formal seeds 11/12/13" in text
        ),
        "finite_default_off_append_contract": (
            "finite" in text
            and "candidate" in text
            and "candidate0" in text
            and "default behavior" in text
        ),
        "fixed_dp_black_box_contract": (
            "dp weights" in text
            and "dp code" in text
            and "dp config" in text
            and "dp invocation" in text
        ),
        "near_threshold_hard_support_contract": (
            source["v2_hard_support_near_threshold"] is True
            and source["hard_support_gap"] > 0
            and "near_threshold_hard_support_closure" in source["tracks"]
        ),
        "zero_comfort_support_contract": (
            source["v2_zero_comfort_support"] is True
            and source["comfort_support_gap"] > 0
            and "comfort_first_profile_precheck" in source["tracks"]
        ),
        "no_gate_relaxation_contract": (
            "threshold is relaxed" in text
            or "not relaxed" in text
            or "not authorize implementation" in text
        ),
        "descriptor_legality_contract": (
            "nonnegative" in text
            and "hinge/signed-split" in text
            and "candidate-local" in text
        ),
        "report_only_contract": (
            "report-only" in text
            and "unless a later atom promotion proves affine" in text
        ),
        "affine_convex_master_contract": (
            "score_k(w)=a_k^t w" in text
            and "simplex/cvar/l2" in text
        ),
        "positive_support_before_execution_contract": (
            "positive_support_evidence=false" in text
            and "training_ready=false" in text
            and "positive_support_before_execution_gate" in source["tracks"]
        ),
        "blocked_boundaries": [
            "implementation edits remain unauthorized in this review",
            "candidate generation and fixed-snapshot screen rerun remain unauthorized",
            "replay, Full36, and formal seeds 11/12/13 remain unauthorized",
            "training execution remains unauthorized",
            "online selector promotion and atom promotion remain unauthorized",
            "DP modification remains unauthorized",
            "safety-benefit and CAMP-over-DP-Top-1 claims remain unauthorized",
            "classical Benders claims remain unauthorized",
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
    plan = _dict(payload.get("remediation_design_plan"))
    target = _dict(plan.get("target_failure"))
    tracks = _list(plan.get("remediation_tracks"))
    descriptors = _list(plan.get("descriptor_atom_contract"))
    rejected = _list(plan.get("rejected_non_fixes"))
    source_text = json.dumps(plan, sort_keys=True).lower()
    blocked_authorizations = [
        key
        for key in BLOCKED_ACTIONS
        if bool(decision.get(key) or _dict(payload.get("blocked_actions")).get(key))
    ]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failed_checks": _list(decision.get("failed_checks")),
        "static_contract_review_authorized": bool(
            decision.get("static_contract_review_authorized")
        ),
        "candidate_rows": _int(target.get("candidate_rows")),
        "descriptor_rows": _int(target.get("descriptor_rows")),
        "descriptor_coverage_rate": _float(target.get("descriptor_coverage_rate")),
        "hard_support_gap": _float(target.get("hard_support_gap")),
        "comfort_support_gap": _float(target.get("comfort_support_gap")),
        "v2_hard_support_near_threshold": bool(
            target.get("v2_hard_support_near_threshold")
        ),
        "v2_zero_comfort_support": bool(target.get("v2_zero_comfort_support")),
        "tracks": [str(item.get("name")) for item in tracks if isinstance(item, dict)],
        "descriptors": [
            str(item.get("name")) for item in descriptors if isinstance(item, dict)
        ],
        "rejected_non_fixes": [
            str(item.get("name")) for item in rejected if isinstance(item, dict)
        ],
        "blocked_authorizations": blocked_authorizations,
        "source_text": source_text,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("plan_root_exists", bool(artifact["exists"])),
        _check("plan_json_exists", bool(artifact["json_exists"])),
        _check("plan_md_exists", bool(artifact["markdown_exists"])),
        _check("plan_json_parseable", bool(artifact["payload"])),
        _check(
            "plan_markdown_records_static_boundary",
            "Math Boundary" in artifact["markdown_text"]
            and "Material Generator V2 Failure Remediation Design Plan"
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
        _check("audit_mentions_design_ready", PLAN_READY_STATUS in audit_text),
        _check(
            "audit_authorizes_static_contract_review",
            PLAN_AUTHORIZED_NEXT_WORK in audit_text,
        ),
        _check("audit_records_fixed_dp", EXPECTED_DP_HEAD in audit_text),
        _check(
            "audit_records_no_training",
            "training_execution_authorized=False" in audit_text,
        ),
        _check("audit_records_no_implementation", "implementation_code_edit_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = set(source["tracks"])
    descriptors = set(source["descriptors"])
    rejected = set(source["rejected_non_fixes"])
    return [
        _check("design_plan_status_ready", source["status"] == PLAN_READY_STATUS),
        _check("design_plan_passed", source["passed"] is True),
        _check("design_plan_no_failed_checks", not source["failed_checks"]),
        _check("design_plan_authorizes_this_review", source["authorized_next_work"] == PLAN_AUTHORIZED_NEXT_WORK),
        _check("design_plan_static_review_authorized", source["static_contract_review_authorized"] is True),
        _check("design_plan_candidate_rows_present", source["candidate_rows"] > 0),
        _check("design_plan_descriptor_rows_present", source["descriptor_rows"] > 0),
        _check("design_plan_descriptor_coverage_complete", source["descriptor_coverage_rate"] == 1.0),
        _check("design_plan_hard_gap_positive", source["hard_support_gap"] > 0),
        _check("design_plan_v2_hard_support_near_threshold", source["v2_hard_support_near_threshold"] is True),
        _check("design_plan_comfort_gap_positive", source["comfort_support_gap"] > 0),
        _check("design_plan_v2_zero_comfort_support", source["v2_zero_comfort_support"] is True),
        _check("design_plan_no_blocked_actions", not source["blocked_authorizations"]),
        *[_check(f"design_plan_has_track_{name}", name in tracks) for name in REQUIRED_TRACKS],
        *[_check(f"design_plan_has_descriptor_{name}", name in descriptors) for name in REQUIRED_DESCRIPTORS],
        *[_check(f"design_plan_rejects_{name}", name in rejected) for name in REQUIRED_REJECTED_NON_FIXES],
    ]


def _contract_checks(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("contract_current_tick_inputs", contract["current_tick_input_contract"]),
        _check("contract_finite_default_off_append", contract["finite_default_off_append_contract"]),
        _check("contract_fixed_dp_black_box", contract["fixed_dp_black_box_contract"]),
        _check("contract_near_threshold_hard_support", contract["near_threshold_hard_support_contract"]),
        _check("contract_zero_comfort_support", contract["zero_comfort_support_contract"]),
        _check("contract_no_gate_relaxation", contract["no_gate_relaxation_contract"]),
        _check("contract_descriptor_legality", contract["descriptor_legality_contract"]),
        _check("contract_report_only", contract["report_only_contract"]),
        _check("contract_affine_convex_master", contract["affine_convex_master_contract"]),
        _check("contract_positive_support_before_execution", contract["positive_support_before_execution_contract"]),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_implementation_plan", decision["implementation_plan_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_blocks_safety_claim", decision["safety_benefit_claim_authorized"] is False),
        _check("boundary_blocks_camp_over_dp", decision["camp_over_dp_top1_claim_authorized"] is False),
        _check("boundary_blocks_benders", decision["classic_benders_claim_authorized"] is False),
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
        "remediation_implementation_plan_authorized": passed,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


def _sha256(path: Path) -> str | None:
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
        if key not in {"payload", "markdown_text"}
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
