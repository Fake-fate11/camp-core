#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Optional


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DEFAULT_FAILURE_ATTRIBUTION_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "guarded_rerun_failure_attribution_remediation_v3_failure_attribution_bff8f8b"
)
FAILURE_ATTRIBUTION_JSON = "failure_attribution.json"
FAILURE_ATTRIBUTION_MD = "failure_attribution.md"

EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FAILURE_ATTRIBUTION_READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_complete"
)
FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_only"
)
READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_static_contract_review_only"
)

PRIMARY_ATTRIBUTION = "zero_lower_union_red_support_after_v3_candidate_construction"
SECONDARY_ATTRIBUTION = "red_stop_distance_window_fail_closed"

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
            "Plan-only remediation design for the guarded material v3 zero "
            "finite-candidate support failure."
        )
    )
    parser.add_argument(
        "--failure_attribution_root",
        type=Path,
        default=Path(DEFAULT_FAILURE_ATTRIBUTION_ROOT),
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
        failure_attribution_root=args.failure_attribution_root,
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
    failure_attribution_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(failure_attribution_root)
    source = _failure_attribution_summary(artifact["payload"])
    audit_text = _read_text(audit_path)
    plan = _design_plan(source)
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
            "name": "dp_camp_guarded_material_v3_zero_candidate_support_remediation_design_plan",
            "label": label,
            "role": "plan-only remediation design after v3 zero candidate support attribution",
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
                "This plan consumes only the completed v3 failure-attribution "
                "artifact and audit authorization. It does not edit production "
                "implementation, create candidates, rerun the fixed-snapshot "
                "screen, run DP, run replay, use formal seeds, define or promote "
                "runtime atoms, choose lambda online, alter score_k(w)=a_k^T w, "
                "mutate the convex simplex/CVaR/L2 master, train CAMP, change "
                "online selection, modify DP weights/code/config, or claim CAMP "
                "over DP Top-1. Any later descriptor proposal must prove "
                "current-tick availability, finite-candidate locality, "
                "nonnegative or legal hinge/signed-split form, and affine "
                "contribution to score_k(w)=a_k^T w."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "failure_attribution_artifact": _strip_payload(artifact),
        "failure_attribution_summary": source,
        "remediation_design_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["failure_attribution_summary"]
    plan = report["remediation_design_plan"]
    lines = [
        "# Guarded Material v3 Zero Candidate Support Remediation Design Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Static contract review authorized: `{decision['static_contract_review_authorized']}`",
        f"- Primary attribution: `{source['primary_attribution']}`",
        f"- Secondary attribution: `{source['secondary_attribution']}`",
        f"- Training ready: `{source['training_ready']}`",
        "",
        "## Design Position",
        "",
        plan["design_position"],
        "",
        "## Remediation Tracks",
        "",
    ]
    for item in plan["remediation_tracks"]:
        lines.append(f"### {item['name']}")
        lines.append("")
        lines.append(item["purpose"])
        lines.append("")
        lines.append(f"- Evidence driver: `{item['evidence_driver']}`")
        lines.append(f"- Contract: `{item['contract']}`")
        lines.append("")
    lines.extend(["## Descriptor And Atom Contract", ""])
    for item in plan["descriptor_atom_contract"]:
        lines.append(f"- `{item['name']}`: {item['contract']}")
    lines.extend(["", "## Rejected Non-Fixes", ""])
    for item in plan["rejected_non_fixes"]:
        lines.append(f"- `{item['name']}`: {item['reason']}")
    lines.extend(
        [
            "",
            "## Exit Criteria For Future Implementation Gate",
            "",
        ]
    )
    for item in plan["future_exit_criteria"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- design plan only",
            "- no production implementation edit",
            "- no candidate generation, screen rerun, replay, Full36, formal seeds, or CAMP retraining",
            "- no atom promotion, online selector promotion, safety claim, or DP modification",
            "- no CAMP-over-DP-Top-1 claim",
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
        "json_exists": (root / FAILURE_ATTRIBUTION_JSON).is_file(),
        "md_exists": (root / FAILURE_ATTRIBUTION_MD).is_file(),
        "json_sha256": _sha256(root / FAILURE_ATTRIBUTION_JSON),
        "md_sha256": _sha256(root / FAILURE_ATTRIBUTION_MD),
        "payload": _read_json(root / FAILURE_ATTRIBUTION_JSON),
        "markdown": _read_text(root / FAILURE_ATTRIBUTION_MD),
    }


def _failure_attribution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    attribution = _dict(payload.get("read_only_attribution"))
    construction = _dict(payload.get("construction_summary"))
    source = _dict(payload.get("source_summary"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "failure_attribution_complete": bool(decision.get("failure_attribution_complete")),
        "remediation_design_plan_authorized": bool(decision.get("remediation_design_plan_authorized")),
        "positive_support_evidence": bool(decision.get("positive_support_evidence")),
        "training_ready": bool(decision.get("training_ready")),
        "replay_evidence_ready": bool(decision.get("replay_evidence_ready")),
        "blocked_authorizations": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "primary_attribution": attribution.get("primary_attribution"),
        "secondary_attribution": attribution.get("secondary_attribution"),
        "zero_support_evidence": bool(attribution.get("zero_support_evidence")),
        "diagnostic_windows_present_without_candidate_rows": bool(
            attribution.get("diagnostic_windows_present_without_candidate_rows")
        ),
        "ready_rows": _int(attribution.get("ready_rows")),
        "red_stop_distance_window_failures": _int(
            attribution.get("red_stop_distance_window_failures")
        ),
        "candidate_count_sum": _int(construction.get("candidate_count_sum")),
        "feasible_stop_windows_sum": _int(construction.get("feasible_stop_windows_sum")),
        "row_generated_count_sum": _int(construction.get("row_generated_count_sum")),
        "candidate_rows_sum": _int(construction.get("candidate_rows_sum")),
        "generated_candidate_rows": _int(source.get("generated_candidate_rows")),
        "lower_union_red_rows": _int(source.get("lower_union_red_rows")),
        "hard_support_rate": _float(source.get("hard_support_rate")),
        "comfort_support_rate": _float(source.get("comfort_support_rate")),
    }


def _design_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "design_position": (
            "The next remediation must bridge ready construction diagnostics into "
            "the finite candidate table used by the support gate. The failure is "
            "not a reason to train, rerun v3 as-is, relax hard/comfort gates, or "
            "touch DP. A future implementation gate should add a default-off "
            "materialization path that emits current-tick finite candidates only "
            "when the existing hard/progress/comfort prechecks prove the row is "
            "eligible, while preserving fail-closed behavior for red-stop-distance "
            "rows that have no legal window."
        ),
        "target_failure": {
            "primary_attribution": source["primary_attribution"],
            "secondary_attribution": source["secondary_attribution"],
            "ready_rows": source["ready_rows"],
            "red_stop_distance_window_failures": source["red_stop_distance_window_failures"],
            "candidate_count_sum": source["candidate_count_sum"],
            "candidate_rows_sum": source["candidate_rows_sum"],
            "row_generated_count_sum": source["row_generated_count_sum"],
        },
        "remediation_tracks": [
            {
                "name": "ready_diagnostic_candidate_materialization",
                "purpose": (
                    "Convert ready-row diagnostic stop-window candidates into "
                    "the finite candidate_rows payload consumed by the existing "
                    "support gate."
                ),
                "evidence_driver": "21 ready rows, candidate_count_sum=456, candidate_rows_sum=0",
                "contract": (
                    "default-off, current-tick only, deterministic, preserves "
                    "candidate0 and never fabricates future outcome labels"
                ),
            },
            {
                "name": "row_generation_accounting_guard",
                "purpose": (
                    "Make generated_count, candidate_rows, and records counters "
                    "agree so diagnostic candidates cannot silently disappear."
                ),
                "evidence_driver": "row_generated_count_sum=0 while ready diagnostics report candidates",
                "contract": "static/unit tests must fail on diagnostic-count positive but candidate_rows empty",
            },
            {
                "name": "red_stop_distance_window_fail_closed_partition",
                "purpose": (
                    "Keep rows with no legal red-stop-distance window fail-closed, "
                    "but report them separately from materialization bugs."
                ),
                "evidence_driver": "36 red_stop_distance_window failures",
                "contract": "no gate relaxation, no DP-side change, no formal-seed probing",
            },
            {
                "name": "comfort_first_budget_preservation",
                "purpose": (
                    "Preserve exact zero jerk/lateral comfort budgets for emitted "
                    "candidates and keep comfort evidence report-only until a "
                    "future contract review approves atomization."
                ),
                "evidence_driver": "v3 was comfort-first but emitted zero support rows",
                "contract": "no weaker comfort floors, no safety or superiority claim",
            },
            {
                "name": "positive_support_before_execution_gate",
                "purpose": (
                    "Require synthetic/static evidence that the implementation "
                    "can produce positive finite candidate support before any "
                    "fixed-snapshot rerun plan is authorized."
                ),
                "evidence_driver": "current fixed snapshot support rate is 0.0",
                "contract": "next gate is static contract review only, not implementation or rerun",
            },
        ],
        "descriptor_atom_contract": [
            {
                "name": "finite_candidate_materialization_flag_v4",
                "contract": "binary/current-tick diagnostic; nonnegative and affine as a fixed candidate feature",
            },
            {
                "name": "stop_window_margin_hinges_v4",
                "contract": "nonnegative hinge channels from current red distance and stop-window margins",
            },
            {
                "name": "lane_progress_comfort_signed_splits_v4",
                "contract": "signed values must be split into nonnegative positive/negative parts before atom use",
            },
            {
                "name": "candidate_accounting_gap_report_only_v4",
                "contract": "report-only until promotion; cannot alter candidates, selected index, fallback, or online selector",
            },
            {
                "name": "affine_convex_master_preservation",
                "contract": "all candidate scores remain score_k(w)=a_k^T w and simplex/CVaR/L2 master remains convex",
            },
        ],
        "rejected_non_fixes": [
            {
                "name": "train_on_zero_support",
                "reason": "no positive finite candidate support and training_ready=False",
            },
            {
                "name": "rerun_v3_as_is",
                "reason": "failure attribution already shows zero candidate_rows from the same family",
            },
            {
                "name": "gate_relaxation",
                "reason": "would weaken hard/comfort contracts rather than fix materialization",
            },
            {
                "name": "formal_seed_probe",
                "reason": "formal seeds remain frozen and this gate has no formal authorization",
            },
            {
                "name": "dp_side_change",
                "reason": "DP is fixed black-box candidate trajectory generator",
            },
            {
                "name": "online_selector_or_atom_promotion",
                "reason": "promotion requires later evidence and explicit gate authorization",
            },
        ],
        "future_exit_criteria": [
            "static_contract_review_complete",
            "implementation_plan_authorized_only_after_static_contract",
            "default_off_implementation_unit_tests_show_positive_materialization",
            "post_implementation_static_contract_review_complete",
            "fixed_snapshot_screen_rerun_plan_before_any_execution",
            "training_execution_authorized_true_before_any_camp_retraining",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_root_exists", bool(artifact["exists"])),
        _check("failure_attribution_json_exists", bool(artifact["json_exists"])),
        _check("failure_attribution_md_exists", bool(artifact["md_exists"])),
        _check("failure_attribution_json_parseable", bool(artifact["payload"])),
        _check("failure_attribution_md_mentions_v3", "Guarded Material v3" in artifact["markdown"]),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_records_failure_attribution_complete", FAILURE_ATTRIBUTION_READY_STATUS in audit_text),
        _check("audit_authorizes_this_design_plan", FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_zero_candidate_support", PRIMARY_ATTRIBUTION in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("failure_attribution_status_ready", source["status"] == FAILURE_ATTRIBUTION_READY_STATUS),
        _check("failure_attribution_authorizes_this_plan", source["authorized_next_work"] == FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK),
        _check("failure_attribution_complete", source["failure_attribution_complete"] is True),
        _check("failure_attribution_primary_zero_candidate", source["primary_attribution"] == PRIMARY_ATTRIBUTION),
        _check("failure_attribution_secondary_red_window", source["secondary_attribution"] == SECONDARY_ATTRIBUTION),
        _check("failure_attribution_zero_support_evidence", source["zero_support_evidence"] is True),
        _check("failure_attribution_diagnostic_windows_present", source["diagnostic_windows_present_without_candidate_rows"] is True),
        _check("failure_attribution_ready_rows_expected", source["ready_rows"] == 21),
        _check("failure_attribution_red_window_failures_expected", source["red_stop_distance_window_failures"] == 36),
        _check("failure_attribution_candidate_count_sum_expected", source["candidate_count_sum"] == 456),
        _check("failure_attribution_candidate_rows_zero", source["candidate_rows_sum"] == 0),
        _check("failure_attribution_no_positive_support", source["positive_support_evidence"] is False),
        _check("failure_attribution_training_not_ready", source["training_ready"] is False),
        _check("failure_attribution_replay_not_ready", source["replay_evidence_ready"] is False),
        _check("failure_attribution_no_blocked_authorizations", not source["blocked_authorizations"]),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = {item["name"] for item in plan["remediation_tracks"]}
    descriptors = {item["name"] for item in plan["descriptor_atom_contract"]}
    rejected = {item["name"] for item in plan["rejected_non_fixes"]}
    return [
        _check("plan_targets_primary_failure", plan["target_failure"]["primary_attribution"] == PRIMARY_ATTRIBUTION),
        _check("plan_has_materialization_track", "ready_diagnostic_candidate_materialization" in tracks),
        _check("plan_has_accounting_guard", "row_generation_accounting_guard" in tracks),
        _check("plan_preserves_red_fail_closed", "red_stop_distance_window_fail_closed_partition" in tracks),
        _check("plan_preserves_comfort_budgets", "comfort_first_budget_preservation" in tracks),
        _check("plan_requires_positive_support_before_execution", "positive_support_before_execution_gate" in tracks),
        _check("plan_has_nonnegative_hinges", "stop_window_margin_hinges_v4" in descriptors),
        _check("plan_has_signed_split_contract", "lane_progress_comfort_signed_splits_v4" in descriptors),
        _check("plan_keeps_accounting_gap_report_only", "candidate_accounting_gap_report_only_v4" in descriptors),
        _check("plan_preserves_affine_convex_contract", "affine_convex_master_preservation" in descriptors),
        _check("plan_rejects_training_on_zero_support", "train_on_zero_support" in rejected),
        _check("plan_rejects_rerun_as_is", "rerun_v3_as_is" in rejected),
        _check("plan_rejects_gate_relaxation", "gate_relaxation" in rejected),
        _check("plan_rejects_formal_seed_probe", "formal_seed_probe" in rejected),
        _check("plan_rejects_dp_side_change", "dp_side_change" in rejected),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_blocks_implementation", decision["implementation_code_edit_authorized"] is False),
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
        "remediation_design_plan_ready": passed,
        "static_contract_review_authorized": passed,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


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
