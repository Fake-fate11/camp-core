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

from scripts.integrations.review_diffusion_planner_guarded_material_v3_remediation_design_static_contract import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    EXPECTED_DP_HEAD,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
)


DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DEFAULT_STATIC_REVIEW_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "guarded_rerun_failure_attribution_remediation_v3_design_static_contract_bff8f8b"
)
STATIC_REVIEW_JSON = "static_contract_review.json"
STATIC_REVIEW_MD = "static_contract_review.md"

READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_implementation_only"
)

PRODUCTION_FILE = "scripts/integrations/analyze_diffusion_planner_route_topology_candidate_screen.py"
ROUTE_TEST_FILE = "camp_core/tests/test_diffusion_planner_route_topology_candidate_screen.py"
IMPLEMENTATION_TEST_FILE = (
    "camp_core/tests/test_diffusion_planner_guarded_material_v4_materialization_accounting.py"
)
NEW_POLICY = "lane_red_hard_feasible_comfort_first_materialized_support"
NEW_PROFILE = "lane_red_hard_feasible_comfort_first_materialized_support_v4"

REQUIRED_STATIC_CONTRACTS = (
    "default_off_plan_only",
    "finite_candidate_materialization_current_tick",
    "nonnegative_stop_window_hinges",
    "signed_split_legality",
    "diagnostics_report_only_until_promotion",
    "affine_score_and_convex_master_preserved",
    "future_execution_requires_positive_materialization_tests",
    "formal_seed_dp_training_promotions_rejected",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only implementation plan for the guarded material v3 zero "
            "candidate support remediation."
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
            "name": "dp_camp_guarded_material_v4_materialization_implementation_plan",
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
            "math_boundary": (
                "This plan reads only the completed static contract review "
                "artifact and audit authorization. It does not edit "
                "implementation code, create candidates, rerun any screen, run "
                "DP, run replay, use formal seeds, define or promote runtime "
                "atoms, choose lambda online, alter score_k(w)=a_k^T w, mutate "
                "the convex simplex/CVaR/L2 master, train CAMP, change online "
                "selection, modify DP weights/code/config, or claim CAMP over "
                "DP Top-1."
            ),
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
        "# Guarded Material v4 Materialization Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation-only authorized: `{decision['implementation_only_authorized']}`",
        f"- Implementation code edit authorized now: `{decision['implementation_code_edit_authorized']}`",
        f"- New policy: `{plan['new_generator_policy']}`",
        f"- New profile: `{plan['new_default_off_profile']}`",
        "",
        "## Allowed Files For Next Gate",
        "",
    ]
    for item in plan["allowed_files"]:
        lines.append(f"- `{item}`")
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
        lines.append(f"- `{item['name']}`: {item['contract']}")
    lines.extend(["", "## Post-Implementation Gates", ""])
    for item in plan["post_implementation_gates"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Rollback Conditions", ""])
    for item in plan["rollback_conditions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _implementation_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "guarded_material_v4_materialization_implementation_plan_only",
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "new_default_off_profile": NEW_PROFILE,
        "new_generator_policy": NEW_POLICY,
        "allowed_files": [
            PRODUCTION_FILE,
            ROUTE_TEST_FILE,
            IMPLEMENTATION_TEST_FILE,
        ],
        "implementation_slices": [
            {
                "name": "explicit_v4_profile_policy_pair",
                "purpose": (
                    "Add a new default-off policy/profile pair so v1, v2, and "
                    "v3 behavior remains byte-for-byte out of scope unless the "
                    "caller explicitly requests v4."
                ),
                "contract": (
                    "activate only for the exact v4 policy/profile pair; no "
                    "online selector or deployed atom schema change"
                ),
            },
            {
                "name": "ready_diagnostic_candidate_materialization",
                "purpose": (
                    "Convert ready-row diagnostic stop-window candidates into "
                    "finite candidate_rows consumed by the existing support gate."
                ),
                "contract": (
                    "current-tick lane/red/baseline features only; preserve "
                    "candidate0; no future outcome labels"
                ),
            },
            {
                "name": "row_generation_accounting_guard",
                "purpose": (
                    "Keep generated_count, row candidate_rows, and records-level "
                    "generated candidate counters mutually consistent."
                ),
                "contract": (
                    "positive diagnostic candidate_count with empty candidate_rows "
                    "must fail unit tests"
                ),
            },
            {
                "name": "red_stop_distance_window_fail_closed_partition",
                "purpose": (
                    "Keep rows without legal red-stop-distance windows fail-closed "
                    "and separate them from materialization/accounting defects."
                ),
                "contract": "no gate relaxation and no DP-side workaround",
            },
            {
                "name": "comfort_first_budget_preservation",
                "purpose": (
                    "Preserve exact zero jerk/lateral comfort budgets and hard/"
                    "progress/comfort gate semantics for v4 emitted candidates."
                ),
                "contract": "no weaker comfort floors and no safety benefit claim",
            },
            {
                "name": "descriptor_payload_report_only",
                "purpose": (
                    "Attach only report-only descriptor diagnostics to emitted "
                    "candidate rows until a later atom-promotion gate exists."
                ),
                "contract": (
                    "diagnostic payload cannot alter scores, selected index, "
                    "fallback, online selector, or deployed atom schema"
                ),
            },
        ],
        "required_tests": [
            {
                "name": "v4_explicit_pair_required",
                "contract": "v4 materialization is unreachable under v1/v2/v3 or default profiles",
            },
            {
                "name": "ready_diagnostics_materialize_candidate_rows",
                "contract": "ready diagnostics with feasible windows produce finite candidate_rows",
            },
            {
                "name": "generated_count_matches_candidate_rows",
                "contract": "generated_count and records counters equal row candidate materialization",
            },
            {
                "name": "red_stop_distance_fail_closed_no_candidates",
                "contract": "red_stop_distance_window rows remain fail_closed with zero candidates",
            },
            {
                "name": "candidate0_and_dp_rows_preserved",
                "contract": "baseline/DP candidate rows are not mutated or reordered",
            },
            {
                "name": "finite_current_tick_inputs_only",
                "contract": "descriptor payload proves no future outcomes or labels",
            },
            {
                "name": "descriptor_legality_and_affine_contract",
                "contract": "nonnegative/hinge/signed-split legality and score_k(w)=a_k^T w preserved",
            },
        ],
        "post_implementation_gates": [
            "post_implementation_static_contract_review_only",
            "fixed_snapshot_screen_rerun_plan_only_after_post_review",
            "guarded_fixed_snapshot_screen_rerun_only_after_plan",
            "failure_attribution_only_if_support_is_insufficient",
        ],
        "rollback_conditions": [
            "v1/v2/v3 default-off behavior changes",
            "candidate0 or DP rows are not preserved",
            "generated_count disagrees with candidate_rows",
            "red_stop_distance_window rows emit candidates",
            "future outcome labels or replay data enter candidate features",
            "score_k(w)=a_k^T w or convex master preservation is violated",
        ],
        "blocked_boundaries": [
            "no implementation code edit in this gate",
            "no candidate generation or screen rerun in this gate",
            "no replay, formal seeds, Full36, or CAMP retraining",
            "no atom or online selector promotion",
            "no DP modification",
            "no safety or CAMP-over-DP-Top-1 claim",
        ],
        "static_review_source": {
            "status": source["status"],
            "authorized_next_work": source["authorized_next_work"],
            "contracts_passed": source["contracts_passed"],
        },
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": (root / STATIC_REVIEW_JSON).is_file(),
        "md_exists": (root / STATIC_REVIEW_MD).is_file(),
        "json_sha256": _sha256(root / STATIC_REVIEW_JSON),
        "md_sha256": _sha256(root / STATIC_REVIEW_MD),
        "payload": _read_json(root / STATIC_REVIEW_JSON),
        "markdown": _read_text(root / STATIC_REVIEW_MD),
    }


def _static_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    contracts = _items_by_name(review.get("required_contracts"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "static_contract_review_complete": bool(decision.get("static_contract_review_complete")),
        "implementation_plan_authorized": bool(decision.get("implementation_plan_authorized")),
        "blocked_authorizations": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "contracts": contracts,
        "contracts_passed": [
            name for name, item in contracts.items() if bool(item.get("passed"))
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_root_exists", bool(artifact["exists"])),
        _check("static_review_json_exists", bool(artifact["json_exists"])),
        _check("static_review_md_exists", bool(artifact["md_exists"])),
        _check("static_review_json_parseable", bool(artifact["payload"])),
        _check("static_review_md_mentions_contract", "Static Contract Review" in artifact["markdown"]),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_records_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_implementation_plan", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_status_complete", source["status"] == STATIC_REVIEW_READY_STATUS),
        _check("static_review_authorizes_this_plan", source["authorized_next_work"] == STATIC_REVIEW_AUTHORIZED_NEXT_WORK),
        _check("static_review_complete_flag", source["static_contract_review_complete"] is True),
        _check("static_review_implementation_plan_authorized", source["implementation_plan_authorized"] is True),
        _check("static_review_no_blocked_authorizations", not source["blocked_authorizations"]),
        *[
            _check(f"static_review_contract_{name}", name in source["contracts_passed"])
            for name in REQUIRED_STATIC_CONTRACTS
        ],
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    slices = {item["name"] for item in plan["implementation_slices"]}
    tests = {item["name"] for item in plan["required_tests"]}
    return [
        _check("plan_selection_type_v4", plan["selection_type"] == "guarded_material_v4_materialization_implementation_plan_only"),
        _check("plan_authorizes_implementation_only", plan["authorized_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_new_policy_named", plan["new_generator_policy"] == NEW_POLICY),
        _check("plan_new_profile_named", plan["new_default_off_profile"] == NEW_PROFILE),
        _check("plan_allows_production_file", PRODUCTION_FILE in plan["allowed_files"]),
        _check("plan_allows_route_test_file", ROUTE_TEST_FILE in plan["allowed_files"]),
        _check("plan_allows_new_impl_test_file", IMPLEMENTATION_TEST_FILE in plan["allowed_files"]),
        _check("plan_slice_explicit_pair", "explicit_v4_profile_policy_pair" in slices),
        _check("plan_slice_materialization", "ready_diagnostic_candidate_materialization" in slices),
        _check("plan_slice_accounting_guard", "row_generation_accounting_guard" in slices),
        _check("plan_slice_red_fail_closed", "red_stop_distance_window_fail_closed_partition" in slices),
        _check("plan_slice_comfort_preservation", "comfort_first_budget_preservation" in slices),
        _check("plan_slice_report_only_descriptors", "descriptor_payload_report_only" in slices),
        _check("plan_test_explicit_pair", "v4_explicit_pair_required" in tests),
        _check("plan_test_materialization", "ready_diagnostics_materialize_candidate_rows" in tests),
        _check("plan_test_accounting", "generated_count_matches_candidate_rows" in tests),
        _check("plan_test_red_fail_closed", "red_stop_distance_fail_closed_no_candidates" in tests),
        _check("plan_test_current_tick", "finite_current_tick_inputs_only" in tests),
        _check("plan_test_affine_contract", "descriptor_legality_and_affine_contract" in tests),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_current_gate_blocks_code_edit", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
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
        "remediation_implementation_plan_ready": passed,
        "implementation_only_authorized": passed,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


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
