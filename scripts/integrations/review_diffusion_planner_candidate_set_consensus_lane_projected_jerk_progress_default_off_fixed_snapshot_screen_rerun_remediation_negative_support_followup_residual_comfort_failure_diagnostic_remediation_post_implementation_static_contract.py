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
    PLANNED_CONTRACT_TEST,
    PLANNED_ROUTE_TEST,
    PLANNED_SCREEN_SOURCE,
)


IMPLEMENTATION_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_implementation_complete"
)
CURRENT_GATE = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_post_implementation_"
    "static_contract_review_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_post_implementation_"
    "static_contract_review_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_post_implementation_"
    "static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_fixed_snapshot_screen_"
    "rerun_plan_only"
)

DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DEFAULT_SOURCE_PATH = ROOT / PLANNED_SCREEN_SOURCE
DEFAULT_ROUTE_TEST_PATH = ROOT / PLANNED_ROUTE_TEST
DEFAULT_CONTRACT_TEST_PATH = ROOT / PLANNED_CONTRACT_TEST

PLANNED_POLICY = "negative_support_coverage_first_lane_projected_red_stop"
DEFAULT_POLICY = "lane_centerline_red_stop"
TAIL_BYTES = 32000

REQUIRED_CONTRACT_TESTS = (
    "test_residual_comfort_remediation_default_off_preserves_candidate0",
    "test_residual_comfort_remediation_report_only_descriptor_payload",
    "test_residual_comfort_remediation_blocks_candidate_mutation",
    "test_residual_comfort_remediation_blocks_online_selector_and_atoms",
    "test_residual_comfort_remediation_preserves_affine_score_and_convex_master",
    "test_residual_comfort_remediation_blocks_dp_import_reward_tracker_recompute",
    "test_residual_comfort_remediation_blocks_execution_training_replay_formal_seeds",
    "test_residual_comfort_remediation_cli_contract_artifact",
)
REQUIRED_ROUTE_TEST_TOKENS = (
    "test_route_topology_report_rejects_invalid_remediation_candidate_cap",
    "max_remediation_candidates must be positive",
    "negative_support_coverage_first_lane_projected_red_stop",
    "candidate_budget_cap",
)
REQUIRED_DESCRIPTOR_KEYS = (
    "payload_role",
    "descriptor_family",
    "top_comfort_blocker",
    "current_tick_features_only",
    "candidate_local",
    "nonnegative_or_hinge_signed_split_legal",
    "command_jerk_abs_max_mps3",
    "command_jerk_hinge_mps3",
    "score_contract",
    "convex_master_contract",
    "candidate_mutation",
    "selected_index_mutation",
    "fallback_mutation",
    "online_selector_feature",
    "deployed_atom_schema_change",
    "dp_import",
    "reward_recompute",
    "tracker_recompute",
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
            "Read-only post-implementation static contract review for the "
            "residual comfort remediation implementation."
        )
    )
    parser.add_argument("--audit_path", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--source_path", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--route_test_path", type=Path, default=DEFAULT_ROUTE_TEST_PATH)
    parser.add_argument(
        "--contract_test_path",
        type=Path,
        default=DEFAULT_CONTRACT_TEST_PATH,
    )
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
        audit_path=args.audit_path,
        source_path=args.source_path,
        route_test_path=args.route_test_path,
        contract_test_path=args.contract_test_path,
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
    audit_path: Path,
    source_path: Path,
    route_test_path: Path,
    contract_test_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    audit_text = _read_text(audit_path)
    audit_tail = audit_text[-TAIL_BYTES:]
    source_text = _read_text(source_path)
    route_test_text = _read_text(route_test_path)
    contract_test_text = _read_text(contract_test_path)
    source_contract = _source_contract(source_path, source_text)
    route_test_contract = _route_test_contract(route_test_path, route_test_text)
    contract_test_contract = _contract_test_contract(
        contract_test_path,
        contract_test_text,
    )
    checks = [
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_tail),
        *_source_contract_checks(source_contract),
        *_route_test_contract_checks(route_test_contract),
        *_contract_test_contract_checks(contract_test_contract),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostic_"
                "remediation_post_implementation_static_review_v1"
            ),
            "label": label,
            "role": "read-only static review after remediation implementation",
            "read_only": True,
            "source_inspection_only": True,
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
                "This review reads only current CAMP source, route tests, "
                "implementation contract tests, audit tail text, and HEAD "
                "values. It does not edit production code, create candidates, "
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
        "source_contract": source_contract,
        "route_test_contract": route_test_contract,
        "contract_test_contract": contract_test_contract,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Residual Comfort Remediation Post-Implementation Static Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Contracts",
        "",
    ]
    for name, passed in report["source_contract"]["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Route Test Contracts", ""])
    for name, passed in report["route_test_contract"]["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(["", "## Implementation Contract Tests", ""])
    for name, passed in report["contract_test_contract"]["contracts"].items():
        lines.append(f"- `{name}`: `{passed}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- fixed-snapshot screen rerun planning only may follow",
            "- no candidate generation, screen rerun execution, replay, Full36, formal seeds, or training is authorized",
            "- no atom promotion, online selector promotion, safety claim, CAMP-over-DP-Top-1 claim, or DP modification is authorized",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
        _check("formal_seeds_frozen_values", sorted(FORMAL_SEEDS) == [11, 12, 13]),
    ]


def _audit_checks(audit_tail: str) -> list[dict[str, Any]]:
    return [
        _check("audit_tail_present", bool(audit_tail)),
        _check(
            "audit_tail_records_implementation_complete",
            IMPLEMENTATION_READY_STATUS in audit_tail,
        ),
        _check("audit_tail_authorizes_current_gate", CURRENT_GATE in audit_tail),
        _check(
            "audit_tail_records_no_candidate_generation",
            "candidate_generation_execution_authorized=False" in audit_tail,
        ),
        _check(
            "audit_tail_records_no_screen_rerun",
            "fixed_snapshot_screen_rerun_authorized=False" in audit_tail,
        ),
        _check(
            "audit_tail_records_no_formal_seeds",
            "formal_seeds_authorized=False" in audit_tail,
        ),
        _check(
            "audit_tail_records_no_training",
            "training_execution_authorized=False" in audit_tail,
        ),
        _check(
            "audit_tail_records_no_dp_modification",
            "dp_modification_authorized=False" in audit_tail,
        ),
    ]


def _source_contract(path: Path, text: str) -> dict[str, Any]:
    descriptor_body = _function_body(text, "_command_jerk_descriptor_payload")
    build_body = _function_body(text, "build_route_topology_candidates")
    contracts = {
        "source_exists": path.is_file(),
        "default_policy_preserved": (
            f'generator_policy: str = "{DEFAULT_POLICY}"' in text
        ),
        "planned_policy_registered": PLANNED_POLICY in text,
        "max_remediation_candidates_cli": "--max_remediation_candidates" in text,
        "max_remediation_candidates_config": (
            "max_remediation_candidates: int = 12" in text
        ),
        "max_remediation_candidates_fail_closed": (
            "max_remediation_candidates must be positive" in text
        ),
        "descriptor_payload_attached": "remediation_descriptor_payload" in text,
        "descriptor_helper_present": bool(descriptor_body),
        "descriptor_current_tick_role": (
            "report_only_current_tick_descriptor" in descriptor_body
        ),
        "descriptor_family_command_jerk_hinge": (
            '"command_jerk_hinge"' in descriptor_body
        ),
        "descriptor_nonnegative_hinge_legal": (
            '"nonnegative_or_hinge_signed_split_legal": True' in descriptor_body
        ),
        "descriptor_score_affine": '"score_k(w)=a_k^T w"' in descriptor_body,
        "descriptor_convex_master": '"simplex/CVaR/L2 unchanged"' in descriptor_body,
        "descriptor_keys_present": all(key in descriptor_body for key in REQUIRED_DESCRIPTOR_KEYS),
        "descriptor_blocks_mutations": all(
            token in descriptor_body
            for token in (
                '"candidate_mutation": False',
                '"selected_index_mutation": False',
                '"fallback_mutation": False',
                '"online_selector_feature": False',
                '"deployed_atom_schema_change": False',
            )
        ),
        "descriptor_blocks_dp_reward_tracker": all(
            token in descriptor_body
            for token in (
                '"dp_import": False',
                '"reward_recompute": False',
                '"tracker_recompute": False',
            )
        ),
        "descriptor_does_not_call_reward_or_tracker": all(
            token not in descriptor_body
            for token in (
                "_score_trajectories",
                "_tracker_delta",
                "reward_config",
                "replay_module",
            )
        ),
        "descriptor_does_not_import_dp": "Diffusion-Planner" not in descriptor_body,
        "screen_scoring_helpers_remain_outside_descriptor": (
            "_score_trajectories" in text
            and "_tracker_delta" in text
            and "_score_trajectories" not in descriptor_body
            and "_tracker_delta" not in descriptor_body
        ),
        "candidate_builder_does_not_import_dp": "Diffusion-Planner" not in build_body,
    }
    return {
        "path": str(path),
        "sha256": _sha256(path),
        "contracts": contracts,
    }


def _route_test_contract(path: Path, text: str) -> dict[str, Any]:
    contracts = {
        "route_test_exists": path.is_file(),
        "route_required_tokens_present": all(
            token in text for token in REQUIRED_ROUTE_TEST_TOKENS
        ),
        "route_default_policy_pinned": DEFAULT_POLICY in text,
        "route_planned_policy_pinned": PLANNED_POLICY in text,
        "route_invalid_budget_pinned": "max_remediation_candidates=0" in text,
        "route_does_not_use_formal_seed_literals": all(
            token not in text for token in ("seed=11", "seed=12", "seed=13")
        ),
    }
    return {"path": str(path), "sha256": _sha256(path), "contracts": contracts}


def _contract_test_contract(path: Path, text: str) -> dict[str, Any]:
    contracts = {
        "contract_test_exists": path.is_file(),
        "required_contract_tests_present": all(
            name in text for name in REQUIRED_CONTRACT_TESTS
        ),
        "contract_pins_descriptor_payload": "remediation_descriptor_payload" in text,
        "contract_pins_score_affine": "score_k(w)=a_k^T w" in text,
        "contract_pins_convex_master": "simplex/CVaR/L2" in text,
        "contract_blocks_formal_seeds": "formal_seeds" in text,
        "contract_blocks_training": "training" in text,
        "contract_blocks_dp_import_reward_tracker": (
            "dp_import" in text
            and "reward_recompute" in text
            and "tracker_recompute" in text
        ),
        "contract_blocks_formal_seed_execution": (
            "test_residual_comfort_remediation_blocks_execution_training_replay_formal_seeds"
            in text
            and '"seed=11" not in source' in text
            and '"seed=12" not in source' in text
            and '"seed=13" not in source' in text
        ),
    }
    return {"path": str(path), "sha256": _sha256(path), "contracts": contracts}


def _source_contract_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(f"source_contract_{name}", bool(passed))
        for name, passed in source["contracts"].items()
    ]


def _route_test_contract_checks(route_tests: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(f"route_test_contract_{name}", bool(passed))
        for name, passed in route_tests["contracts"].items()
    ]


def _contract_test_contract_checks(contract_tests: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(f"implementation_contract_{name}", bool(passed))
        for name, passed in contract_tests["contracts"].items()
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_plan_only", decision["fixed_snapshot_screen_rerun_plan_authorized"] is True),
        _check("boundary_blocks_implementation_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "remediation_post_implementation_static_contract_review_complete": passed,
        "fixed_snapshot_screen_rerun_plan_authorized": passed,
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


def _function_body(text: str, name: str) -> str:
    marker = f"def {name}"
    start = text.find(marker)
    if start < 0:
        return ""
    next_def = text.find("\ndef ", start + len(marker))
    return text[start:] if next_def < 0 else text[start:next_def]


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
