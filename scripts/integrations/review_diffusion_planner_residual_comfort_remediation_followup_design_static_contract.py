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
    "followup_design"
)
_plan = importlib.import_module(_PLAN_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_design_static_"
    "contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_design_static_"
    "contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_implementation_"
    "plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = _plan.DEFAULT_DEVELOPMENT_ROOT
DEFAULT_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_followup_design_plan_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

PLAN_JSON = "followup_design_plan.json"
PLAN_MD = "followup_design_plan.md"
PLAN_READY_STATUS = _plan.READY_STATUS
PLAN_AUTHORIZED_NEXT_WORK = _plan.AUTHORIZED_NEXT_WORK
EXPECTED_DP_HEAD = _plan.EXPECTED_DP_HEAD
FORMAL_SEEDS = _plan.FORMAL_SEEDS
RESIDUAL_FAMILY = _plan.RESIDUAL_FAMILY

REQUIRED_TRACKS = (
    "comfort_gap_blocker_partition",
    "command_jerk_rollout_lateral_descriptor_family",
    "support_intervention_static_boundary",
    "positive_support_before_training_gate",
    "dp_fixed_black_box_boundary",
)
REQUIRED_REJECTED_NON_FIXES = (
    "train_on_negative_support",
    "rerun_without_static_contract",
    "relax_comfort_acceptance",
    "selector_or_atom_promotion",
    "dp_side_change",
)
BLOCKED_ACTIONS = _plan.BLOCKED_ACTIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Static contract review of the residual comfort remediation "
            "follow-up design plan."
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
                "remediation_followup_design_static_contract_review_v1"
            ),
            "label": label,
            "role": "static contract review of follow-up design plan",
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
                "This static review reads only the follow-up design plan and "
                "audit text. It does not edit implementation code, create "
                "candidates, rerun the screen, run DP, run replay, use formal "
                "seeds, define runtime atoms, choose lambda online, alter "
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
        "plan_artifact": _strip_payload(artifact),
        "plan_summary": source,
        "static_contract_review": contract,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    contract = report["static_contract_review"]
    lines = [
        "# Residual Comfort Remediation Follow-Up Design Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Residual family: `{contract['residual_family']}`",
        "",
        "## Contract Findings",
        "",
    ]
    for item in contract["contract_findings"]:
        lines.append(f"- `{item['name']}`: {item['finding']}")
    lines.extend(["", "## Required Tracks", ""])
    for item in contract["required_tracks"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Rejected Non-Fixes", ""])
    for item in contract["rejected_non_fixes"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Boundaries", ""])
    for item in contract["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


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
    plan = _dict(payload.get("followup_design_plan"))
    analysis = _dict(payload.get("analysis"))
    tracks = _list(plan.get("tracks"))
    rejected = _list(plan.get("rejected_non_fixes"))
    text = json.dumps(plan, sort_keys=True).lower()
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "analysis": analysis,
        "selection_type": plan.get("selection_type"),
        "plan_authorized_next_work": plan.get("authorized_next_work"),
        "target_failure": _dict(plan.get("target_failure")),
        "tracks": tracks,
        "track_names": [
            str(item.get("name"))
            for item in tracks
            if isinstance(item, dict) and item.get("name")
        ],
        "static_review_requirements": _list(plan.get("static_review_requirements")),
        "rejected_non_fixes": [
            str(item.get("name"))
            for item in rejected
            if isinstance(item, dict) and item.get("name")
        ],
        "blocked_boundaries": _list(plan.get("blocked_boundaries")),
        "text": text,
    }


def _static_contract(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "residual_family": source["target_failure"].get("residual_family"),
        "required_tracks": list(REQUIRED_TRACKS),
        "rejected_non_fixes": list(REQUIRED_REJECTED_NON_FIXES),
        "contract_findings": [
            {
                "name": "default_off_plan_only",
                "finding": (
                    "the design is plan-only and authorizes only static review "
                    "before any implementation planning"
                ),
            },
            {
                "name": "current_tick_finite_candidate_features",
                "finding": (
                    "the design requires finite current-tick candidate-local "
                    "features and forbids outcome labels"
                ),
            },
            {
                "name": "affine_convex_math_boundary",
                "finding": (
                    "descriptor proposals must be nonnegative or legal "
                    "hinge/signed-split terms preserving score_k(w)=a_k^T w "
                    "and the convex simplex/CVaR/L2 master"
                ),
            },
            {
                "name": "positive_support_before_training",
                "finding": (
                    "training remains blocked until positive fixed-snapshot or "
                    "nonformal support exists under a separate contract"
                ),
            },
            {
                "name": "fixed_dp_black_box",
                "finding": (
                    "DP stays fixed at the pinned commit with no code, weight, "
                    "config, invocation, reward, tracker, or tuning change"
                ),
            },
        ],
        "blocked_boundaries": [
            "implementation edits remain unauthorized",
            "candidate generation and screen rerun remain unauthorized",
            "replay, closed-loop smoke, Full36, and formal seeds remain unauthorized",
            "CAMP retraining and training execution remain unauthorized",
            "atom promotion and online selector promotion remain unauthorized",
            "DP modification and safety or CAMP-over-DP claims remain unauthorized",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("plan_root_exists", artifact["exists"]),
        _check("plan_json_exists", artifact["json_exists"]),
        _check("plan_markdown_exists", artifact["markdown_exists"]),
        _check("plan_json_parseable", bool(artifact["payload"])),
        _check(
            "plan_markdown_records_title",
            "Residual Comfort Remediation Follow-Up Design Plan"
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
        _check("audit_records_design_plan_ready", PLAN_READY_STATUS in audit_text),
        _check(
            "audit_authorizes_static_review",
            PLAN_AUTHORIZED_NEXT_WORK in audit_text,
        ),
        _check("audit_blocks_candidate_generation", "candidate_generation_execution_authorized=False" in audit_text),
        _check("audit_blocks_screen_rerun", "fixed_snapshot_screen_rerun_authorized=False" in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    track_names = set(source["track_names"])
    rejected = set(source["rejected_non_fixes"])
    text = source["text"]
    return [
        _check("plan_status_ready", source["status"] == PLAN_READY_STATUS),
        _check("plan_passed", source["passed"] is True),
        _check("plan_failed_checks_empty", not source["failed_checks"]),
        _check("plan_authorizes_this_review", source["authorized_next_work"] == PLAN_AUTHORIZED_NEXT_WORK),
        _check("plan_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("plan_selection_type", source["selection_type"] == "residual_comfort_remediation_followup_design_plan_only"),
        _check("plan_inner_next_work", source["plan_authorized_next_work"] == PLAN_AUTHORIZED_NEXT_WORK),
        _check("plan_residual_family", source["target_failure"].get("residual_family") == RESIDUAL_FAMILY),
        *[_check(f"plan_track_{name}", name in track_names) for name in REQUIRED_TRACKS],
        *[_check(f"plan_rejects_{name}", name in rejected) for name in REQUIRED_REJECTED_NON_FIXES],
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_finite_candidate", "finite candidate" in text),
        _check("plan_mentions_candidate_local", "candidate-local" in text),
        _check("plan_mentions_no_mutation", "no candidate, score" in text),
        _check("plan_mentions_nonnegative", "nonnegative" in text),
        _check("plan_mentions_hinge_signed_split", "hinge/signed-split" in text),
        _check("plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_formal_seeds", "formal seeds 11/12/13" in text),
        _check("plan_mentions_dp_fixed", "dp weights" in text and "dp code" in text),
        _check("plan_formal_seed_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _contract_checks(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings = {item["name"] for item in contract["contract_findings"]}
    return [
        _check("contract_residual_family", contract["residual_family"] == RESIDUAL_FAMILY),
        _check("contract_default_off_plan_only", "default_off_plan_only" in findings),
        _check("contract_current_tick_features", "current_tick_finite_candidate_features" in findings),
        _check("contract_affine_convex", "affine_convex_math_boundary" in findings),
        _check("contract_training_blocked", "positive_support_before_training" in findings),
        _check("contract_dp_fixed", "fixed_dp_black_box" in findings),
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
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "static_contract_review_complete": passed,
        "implementation_plan_authorized": passed,
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
