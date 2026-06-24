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
    "followup_implementation"
)
_plan = importlib.import_module(_PLAN_MODULE)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_implementation_"
    "static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_implementation_"
    "static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_unit_tests_"
    "plan_only"
)

DEFAULT_DEVELOPMENT_ROOT = _plan.DEFAULT_DEVELOPMENT_ROOT
DEFAULT_IMPLEMENTATION_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "remediation_followup_implementation_plan_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

IMPLEMENTATION_PLAN_JSON = "implementation_plan.json"
IMPLEMENTATION_PLAN_MD = "implementation_plan.md"
IMPLEMENTATION_PLAN_READY_STATUS = _plan.READY_STATUS
IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK = _plan.AUTHORIZED_NEXT_WORK
EXPECTED_DP_HEAD = _plan.EXPECTED_DP_HEAD
FORMAL_SEEDS = _plan.FORMAL_SEEDS
RESIDUAL_FAMILY = _plan.RESIDUAL_FAMILY
PLANNED_SCREEN_SOURCE = _plan.PLANNED_SCREEN_SOURCE
PLANNED_ROUTE_TEST = _plan.PLANNED_ROUTE_TEST
PLANNED_CONTRACT_TEST = _plan.PLANNED_CONTRACT_TEST
BLOCKED_ACTIONS = _plan.BLOCKED_ACTIONS

REQUIRED_SLICES = (
    "default_off_report_only_descriptor_payload",
    "command_jerk_rollout_lateral_hinge_terms",
    "positive_support_gate_stays_external",
    "worktree_preflight_contract",
)
REQUIRED_FILES = (PLANNED_SCREEN_SOURCE, PLANNED_ROUTE_TEST, PLANNED_CONTRACT_TEST)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Static contract review of the follow-up implementation plan."
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
    source = _plan_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    review = _static_review(source)
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
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_followup_implementation_static_contract_review_v1"
            ),
            "label": label,
            "role": "static contract review of follow-up implementation plan",
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
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "implementation_plan_artifact": _strip_payload(artifact),
        "implementation_plan_summary": source,
        "static_contract_review": review,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# Residual Comfort Remediation Follow-Up Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Findings",
        "",
    ]
    for item in review["findings"]:
        lines.append(f"- `{item['name']}`: {item['finding']}")
    lines.extend(["", "## Required Unit-Test Families", ""])
    for item in review["required_unit_test_families"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Boundaries", ""])
    for item in review["blocked_boundaries"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def _artifact_summary(root: Path) -> dict[str, Any]:
    json_path = root / IMPLEMENTATION_PLAN_JSON
    md_path = root / IMPLEMENTATION_PLAN_MD
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
    plan = _dict(payload.get("implementation_plan"))
    files = _list(plan.get("planned_files"))
    slices = _list(plan.get("implementation_slices"))
    text = json.dumps(plan, sort_keys=True).lower()
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "selection_type": plan.get("selection_type"),
        "plan_authorized_next_work": plan.get("authorized_next_work"),
        "target_contract": _dict(plan.get("target_contract")),
        "planned_files": [
            str(item.get("path"))
            for item in files
            if isinstance(item, dict) and item.get("path")
        ],
        "implementation_slices": [
            str(item.get("name"))
            for item in slices
            if isinstance(item, dict) and item.get("name")
        ],
        "required_tests": _list(plan.get("required_tests")),
        "blocked_boundaries": _list(plan.get("blocked_boundaries")),
        "text": text,
    }


def _static_review(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "findings": [
            {
                "name": "plan_only_to_unit_tests_plan",
                "finding": (
                    "implementation edits remain blocked; the next admissible "
                    "work is a unit-tests plan"
                ),
            },
            {
                "name": "default_off_report_only_payload",
                "finding": (
                    "planned implementation is constrained to default-off "
                    "report-only descriptors"
                ),
            },
            {
                "name": "affine_descriptor_contract",
                "finding": (
                    "planned command-jerk and rollout-lateral terms must be "
                    "nonnegative or legal hinge/signed-split and preserve "
                    "score_k(w)=a_k^T w"
                ),
            },
            {
                "name": "convex_master_unchanged",
                "finding": "simplex/CVaR/L2 master remains unchanged",
            },
            {
                "name": "dp_and_training_blocked",
                "finding": (
                    "DP modification, replay, formal seeds, Full36, and "
                    "training remain blocked"
                ),
            },
        ],
        "required_unit_test_families": [
            "default-off no candidate/score/selection/fallback mutation",
            "opt-in current-tick finite candidate-local descriptor payload",
            "nonnegative or legal hinge/signed-split descriptor contract",
            "affine score and convex master preservation",
            "DP/replay/training/formal-seed blocked-action contract",
            "CLI/report artifact boundary contract",
        ],
        "blocked_boundaries": [
            "implementation edits are not authorized in this review gate",
            "candidate generation and screen rerun are not authorized",
            "replay, Full36, formal seeds 11/12/13, and training are not authorized",
            "atom promotion and online selector promotion are not authorized",
            "DP weights, code, configs, invocation, reward, tracker, and tuning remain fixed",
            "safety and CAMP-over-DP claims remain unauthorized",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("implementation_plan_root_exists", artifact["exists"]),
        _check("implementation_plan_json_exists", artifact["json_exists"]),
        _check("implementation_plan_markdown_exists", artifact["markdown_exists"]),
        _check("implementation_plan_json_parseable", bool(artifact["payload"])),
        _check(
            "implementation_plan_markdown_records_title",
            "Residual Comfort Remediation Follow-Up Implementation Plan"
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
        _check("audit_records_implementation_plan_ready", IMPLEMENTATION_PLAN_READY_STATUS in audit_text),
        _check("audit_authorizes_static_review", IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_blocks_implementation_edit", "implementation_code_edit_authorized=False" in audit_text),
        _check("audit_blocks_candidate_generation", "candidate_generation_execution_authorized=False" in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    files = set(source["planned_files"])
    slices = set(source["implementation_slices"])
    text = source["text"]
    return [
        _check("implementation_plan_status_ready", source["status"] == IMPLEMENTATION_PLAN_READY_STATUS),
        _check("implementation_plan_passed", source["passed"] is True),
        _check("implementation_plan_failed_checks_empty", not source["failed_checks"]),
        _check("implementation_plan_authorizes_this_review", source["authorized_next_work"] == IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK),
        _check("implementation_plan_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check("implementation_plan_selection_type", source["selection_type"] == "residual_comfort_remediation_followup_implementation_plan_only"),
        _check("implementation_plan_inner_next_work", source["plan_authorized_next_work"] == IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK),
        _check("implementation_plan_residual_family", source["target_contract"].get("residual_family") == RESIDUAL_FAMILY),
        *[_check(f"implementation_plan_file_{path}", path in files) for path in REQUIRED_FILES],
        *[_check(f"implementation_plan_slice_{name}", name in slices) for name in REQUIRED_SLICES],
        _check("implementation_plan_mentions_default_off", "default-off" in text),
        _check("implementation_plan_mentions_current_tick", "current-tick" in text),
        _check("implementation_plan_mentions_candidate_local", "candidate-local" in text),
        _check("implementation_plan_mentions_nonnegative", "nonnegative" in text),
        _check("implementation_plan_mentions_hinge", "hinge/signed-split" in text),
        _check("implementation_plan_mentions_score_affine", "score_k(w)=a_k^t w" in text),
        _check("implementation_plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("implementation_plan_mentions_no_selector", "online selector" in text),
        _check("implementation_plan_mentions_no_dp", "dp weights" in text and "dp modification" in text),
        _check("implementation_plan_mentions_formal_seeds", "formal seeds 11/12/13" in text),
        _check("implementation_plan_formal_seed_values", source["target_contract"].get("formal_seeds") == [11, 12, 13]),
    ]


def _review_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    findings = {item["name"] for item in review["findings"]}
    return [
        _check("review_finds_plan_only", "plan_only_to_unit_tests_plan" in findings),
        _check("review_finds_default_off", "default_off_report_only_payload" in findings),
        _check("review_finds_affine_descriptor", "affine_descriptor_contract" in findings),
        _check("review_finds_convex_master", "convex_master_unchanged" in findings),
        _check("review_finds_dp_training_blocked", "dp_and_training_blocked" in findings),
        _check("review_lists_unit_tests", len(review["required_unit_test_families"]) >= 6),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_unit_tests_plan", decision["unit_tests_plan_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
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
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "implementation_static_contract_review_complete": passed,
        "unit_tests_plan_authorized": passed,
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
