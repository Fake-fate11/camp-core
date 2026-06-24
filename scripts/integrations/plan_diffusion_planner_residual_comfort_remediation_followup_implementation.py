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

_REVIEW_MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_"
    "remediation_followup_design_static_contract"
)
_review = importlib.import_module(_REVIEW_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_implementation_"
    "plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_implementation_"
    "plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_implementation_"
    "static_contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = _review.DEFAULT_DEVELOPMENT_ROOT
DEFAULT_STATIC_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_followup_design_static_contract_review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

STATIC_REVIEW_JSON = "static_contract_review.json"
STATIC_REVIEW_MD = "static_contract_review.md"
STATIC_REVIEW_READY_STATUS = _review.READY_STATUS
STATIC_REVIEW_AUTHORIZED_NEXT_WORK = _review.AUTHORIZED_NEXT_WORK
EXPECTED_DP_HEAD = _review.EXPECTED_DP_HEAD
FORMAL_SEEDS = _review.FORMAL_SEEDS
RESIDUAL_FAMILY = _review.RESIDUAL_FAMILY

PLANNED_SCREEN_SOURCE = (
    "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py"
)
PLANNED_ROUTE_TEST = "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py"
PLANNED_CONTRACT_TEST = (
    "camp_core/tests/test_diffusion_planner_residual_comfort_remediation_"
    "followup_implementation_contract.py"
)

BLOCKED_ACTIONS = _review.BLOCKED_ACTIONS
REQUIRED_STATIC_FINDINGS = (
    "default_off_plan_only",
    "current_tick_finite_candidate_features",
    "affine_convex_math_boundary",
    "positive_support_before_training",
    "fixed_dp_black_box",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation plan after follow-up design static "
            "contract review."
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
    source = _static_review_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    plan = _implementation_plan(source)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_source_checks(source),
        *_plan_checks(plan),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_followup_implementation_plan_v1"
            ),
            "label": label,
            "role": "plan-only implementation plan after static contract review",
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
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "static_review_artifact": _strip_payload(artifact),
        "static_review_summary": source,
        "implementation_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    lines = [
        "# Residual Comfort Remediation Follow-Up Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Residual family: `{plan['target_contract']['residual_family']}`",
        "",
        "## Planned Files",
        "",
    ]
    for item in plan["planned_files"]:
        lines.append(f"- `{item['path']}`: {item['purpose']}")
    lines.extend(["", "## Implementation Slices", ""])
    for item in plan["implementation_slices"]:
        lines.append(f"### {item['name']}")
        lines.append("")
        lines.append(item["purpose"])
        lines.append("")
        lines.append(f"- Contract: `{item['contract']}`")
        lines.append("")
    lines.extend(["## Required Tests", ""])
    for item in plan["required_tests"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    json_path = root / STATIC_REVIEW_JSON
    md_path = root / STATIC_REVIEW_MD
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


def _static_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    findings = _list(review.get("contract_findings"))
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
        "residual_family": review.get("residual_family"),
        "findings": [
            str(item.get("name"))
            for item in findings
            if isinstance(item, dict) and item.get("name")
        ],
    }


def _implementation_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "residual_comfort_remediation_followup_implementation_plan_only",
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "target_contract": {
            "residual_family": source["residual_family"],
            "fixed_dp_head": EXPECTED_DP_HEAD,
            "formal_seeds": sorted(FORMAL_SEEDS),
            "score_contract": "score_k(w)=a_k^T w",
            "master_contract": "convex simplex/CVaR/L2 master unchanged",
        },
        "planned_files": [
            {
                "path": PLANNED_SCREEN_SOURCE,
                "purpose": (
                    "future implementation-only gate may add default-off "
                    "report-only descriptor payloads for the residual comfort "
                    "follow-up family"
                ),
            },
            {
                "path": PLANNED_ROUTE_TEST,
                "purpose": (
                    "future implementation-only gate may extend route screen "
                    "tests to pin default-off behavior and no candidate mutation"
                ),
            },
            {
                "path": PLANNED_CONTRACT_TEST,
                "purpose": (
                    "future implementation-only gate should add focused "
                    "contract tests for current-tick finite candidate-local "
                    "features, nonnegative or hinge/signed-split descriptors, "
                    "affine scoring, convex master preservation, and blocked "
                    "actions"
                ),
            },
        ],
        "implementation_slices": [
            {
                "name": "default_off_report_only_descriptor_payload",
                "purpose": (
                    "Expose residual comfort blocker descriptors only in an "
                    "opt-in diagnostic payload."
                ),
                "contract": (
                    "default path must preserve candidates, scores, selected "
                    "index, fallback, online selector, and deployed atom schema"
                ),
            },
            {
                "name": "command_jerk_rollout_lateral_hinge_terms",
                "purpose": (
                    "Define candidate-local command-jerk and rollout-lateral "
                    "gap descriptors for later static review."
                ),
                "contract": (
                    "terms must be nonnegative or legal hinge/signed-split and "
                    "must preserve score_k(w)=a_k^T w"
                ),
            },
            {
                "name": "positive_support_gate_stays_external",
                "purpose": (
                    "Keep any future candidate-support intervention behind a "
                    "separate execution gate."
                ),
                "contract": (
                    "no candidate generation, screen rerun, replay, training, "
                    "formal seeds, Full36, promotion, or DP modification"
                ),
            },
            {
                "name": "worktree_preflight_contract",
                "purpose": (
                    "Future implementation must reconcile any in-scope partial "
                    "test or symbol drift before claiming implementation ready."
                ),
                "contract": (
                    "do not handle unrelated untracked files; only touch files "
                    "listed by this plan or separately authorized by audit"
                ),
            },
        ],
        "required_tests": [
            "default-off preserves candidate0/candidates/scores/selected index/fallback",
            "opt-in descriptor payload uses only current-tick finite candidate-local features",
            "command-jerk and rollout-lateral descriptors are nonnegative or legal hinge/signed-split",
            "score_k(w)=a_k^T w and convex simplex/CVaR/L2 master remain unchanged",
            "no online selector or deployed atom schema mutation",
            "no DP import, DP reward recompute, tracker recompute, DP tuning, or DP modification",
            "no replay, Full36, formal seeds 11/12/13, CAMP retraining, or training execution",
            "CLI/report artifact records blocked actions and next static review boundary",
        ],
        "blocked_boundaries": [
            "this gate is plan-only and cannot edit implementation code",
            "candidate generation and screen rerun are not authorized",
            "replay, closed-loop smoke, Full36, and formal seeds are not authorized",
            "CAMP retraining and training execution are not authorized",
            "atom promotion and online selector promotion are not authorized",
            "DP weights, code, config, invocation, reward, tracker, and tuning remain fixed",
            "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
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
            "Residual Comfort Remediation Follow-Up Design Static Contract Review"
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
        _check("audit_records_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_implementation_plan", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_blocks_implementation_edit", "implementation_code_edit_authorized=False" in audit_text),
        _check("audit_blocks_candidate_generation", "candidate_generation_execution_authorized=False" in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    findings = set(source["findings"])
    return [
        _check("static_review_status_complete", source["status"] == STATIC_REVIEW_READY_STATUS),
        _check("static_review_passed", source["passed"] is True),
        _check("static_review_failed_checks_empty", not source["failed_checks"]),
        _check(
            "static_review_authorizes_this_plan",
            source["authorized_next_work"] == STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check("static_review_implementation_plan_authorized", source["implementation_plan_authorized"] is True),
        _check("static_review_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("static_review_residual_family", source["residual_family"] == RESIDUAL_FAMILY),
        *[_check(f"static_review_finding_{name}", name in findings) for name in REQUIRED_STATIC_FINDINGS],
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    files = {item["path"] for item in plan["planned_files"]}
    slices = {item["name"] for item in plan["implementation_slices"]}
    return [
        _check("plan_selection_type", plan["selection_type"] == "residual_comfort_remediation_followup_implementation_plan_only"),
        _check("plan_selects_static_review", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_targets_screen_source", PLANNED_SCREEN_SOURCE in files),
        _check("plan_targets_route_test", PLANNED_ROUTE_TEST in files),
        _check("plan_targets_contract_test", PLANNED_CONTRACT_TEST in files),
        _check("plan_has_descriptor_payload_slice", "default_off_report_only_descriptor_payload" in slices),
        _check("plan_has_hinge_terms_slice", "command_jerk_rollout_lateral_hinge_terms" in slices),
        _check("plan_keeps_support_gate_external", "positive_support_gate_stays_external" in slices),
        _check("plan_has_worktree_preflight", "worktree_preflight_contract" in slices),
        _check("plan_mentions_default_off", "default-off" in text),
        _check("plan_mentions_current_tick", "current-tick" in text),
        _check("plan_mentions_candidate_local", "candidate-local" in text),
        _check("plan_mentions_nonnegative_or_hinge", "nonnegative" in text and "hinge/signed-split" in text),
        _check("plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_mentions_no_selector", "online selector" in text),
        _check("plan_mentions_no_dp", "dp weights" in text and "dp modification" in text),
        _check("plan_mentions_formal_seeds", "formal seeds 11/12/13" in text),
        _check("plan_formal_seed_values", plan["target_contract"]["formal_seeds"] == [11, 12, 13]),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_static_review", decision["implementation_static_contract_review_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_full36", decision["full36_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_blocks_claims", decision["safety_benefit_claim_authorized"] is False and decision["camp_over_dp_top1_claim_authorized"] is False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "implementation_plan_ready": passed,
        "implementation_static_contract_review_authorized": passed,
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
