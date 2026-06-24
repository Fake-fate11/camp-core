#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Optional


EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_CAMP_HEAD = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"
SCREEN_REJECT_STATUS = "route_topology_candidate_support_insufficient"
PLANNED_POLICY = "lane_red_hard_feasible_comfort_first_material_support"
REMEDIATION_PROFILE = "lane_red_hard_feasible_comfort_first_support_v3"

READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_only"
)

DEFAULT_SCREEN_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "guarded_rerun_failure_attribution_remediation_v3_fixed_snapshot_screen_"
    "rerun_bff8f8b"
)
SCREEN_JSON = "guarded_material_v3_fixed_snapshot_screen.json"
SCREEN_MD = "guarded_material_v3_fixed_snapshot_screen.md"
CANDIDATE_LOG = "CANDIDATE_SCREEN.log"
CANDIDATE_ERR = "CANDIDATE_SCREEN.err"
EXIT_CODE = "EXIT_CODE"
HEADS = "HEADS.txt"
SHA256SUMS = "SHA256SUMS"

BLOCKED_ACTIONS = (
    "offline_selector_screen_authorized",
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
            "Read-only attribution over the guarded material v3 fixed-snapshot "
            "screen rerun result."
        )
    )
    parser.add_argument("--screen_root", type=Path, default=Path(DEFAULT_SCREEN_ROOT))
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
        screen_root=args.screen_root,
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
    screen_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(screen_root)
    payload = artifact["screen_payload"]
    source = _source_summary(payload)
    construction = _construction_summary(payload)
    attribution = _failure_attribution(source, construction)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head, artifact),
        *_source_checks(source),
        *_construction_checks(construction),
        *_attribution_checks(attribution),
        *_boundary_checks(source),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_guarded_material_generator_v3_fixed_snapshot_screen_"
                "rerun_failure_attribution_v1"
            ),
            "label": label,
            "role": "read-only failure attribution over completed v3 screen rerun",
            "read_only": True,
            "failure_attribution_only": True,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This gate reads only completed fixed-snapshot screen artifacts. "
                "It does not create candidates, rerun the screen, run replay, "
                "use formal seeds, define or promote runtime atoms, choose "
                "lambda online, alter score_k(w)=a_k^T w, mutate the convex "
                "simplex/CVaR/L2 master, train CAMP, change online selection, "
                "modify DP weights/code/config, or claim CAMP over DP Top-1."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "expected_camp_head": EXPECTED_CAMP_HEAD,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "screen_artifact": _strip_payload(artifact),
        "source_summary": source,
        "construction_summary": construction,
        "read_only_attribution": attribution,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    construction = report["construction_summary"]
    attribution = report["read_only_attribution"]
    lines = [
        "# Guarded Material v3 Screen Rerun Failure Attribution",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Screen status: `{source['status']}`",
        f"- Primary attribution: `{attribution['primary_attribution']}`",
        f"- Secondary attribution: `{attribution['secondary_attribution']}`",
        f"- Training ready: `{attribution['training_ready']}`",
        "",
        "## Support Shape",
        "",
        f"- Snapshots: `{source['snapshots']}`",
        f"- Rows: `{construction['row_count']}`",
        f"- Selected-union-red rows: `{construction['selected_union_red_count']}`",
        f"- Candidate generation executed: `{source['candidate_generation_executed']}`",
        f"- Records generated candidate rows: `{source['generated_candidate_rows']}`",
        f"- Row generated-count sum: `{construction['row_generated_count_sum']}`",
        f"- Candidate row sum: `{construction['candidate_rows_sum']}`",
        f"- Lower-union-red rows: `{source['lower_union_red_rows']}`",
        f"- Hard support rate: `{source['hard_support_rate']}`",
        f"- Comfort support rate: `{source['comfort_support_rate']}`",
        "",
        "## Construction Diagnostics",
        "",
        f"- Construction status counts: `{construction['construction_status_counts']}`",
        f"- Failure reason counts: `{construction['failure_reason_counts']}`",
        f"- Hard precheck pass count: `{construction['hard_precheck_pass_count']}`",
        f"- Comfort precheck pass count: `{construction['comfort_precheck_pass_count']}`",
        f"- Diagnostic candidate-count values: `{construction['candidate_count_values']}`",
        f"- Diagnostic candidate-count sum: `{construction['candidate_count_sum']}`",
        f"- Feasible stop-window values: `{construction['feasible_stop_windows_values']}`",
        f"- Feasible stop-window sum: `{construction['feasible_stop_windows_sum']}`",
        "",
        "## Attribution",
        "",
        attribution["interpretation"],
        "",
        "## Non-Causes",
        "",
    ]
    for item in attribution["non_causes"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- read-only failure attribution only",
            "- no new screen rerun, replay, Full36, formal seeds, or CAMP retraining",
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
    required = (SCREEN_JSON, SCREEN_MD, CANDIDATE_LOG, CANDIDATE_ERR, EXIT_CODE, HEADS, SHA256SUMS)
    files = {name: (root / name).is_file() for name in required}
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "files": files,
        "sha256sums_ok": _sha256sums_ok(root / SHA256SUMS),
        "screen_json_sha256": _sha256(root / SCREEN_JSON),
        "screen_md_sha256": _sha256(root / SCREEN_MD),
        "candidate_log_sha256": _sha256(root / CANDIDATE_LOG),
        "candidate_err_sha256": _sha256(root / CANDIDATE_ERR),
        "exit_code_sha256": _sha256(root / EXIT_CODE),
        "heads_sha256": _sha256(root / HEADS),
        "screen_payload": _read_json(root / SCREEN_JSON),
        "screen_markdown": _read_text(root / SCREEN_MD),
        "candidate_log": _read_text(root / CANDIDATE_LOG),
        "candidate_err": _read_text(root / CANDIDATE_ERR),
        "exit_code": _read_text(root / EXIT_CODE).strip(),
        "heads": _parse_heads(_read_text(root / HEADS)),
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    records = _dict(payload.get("records"))
    support = _dict(payload.get("support_gate"))
    config = _dict(payload.get("config"))
    return {
        "status": decision.get("status"),
        "next_step": decision.get("next_step"),
        "snapshots": _int(records.get("snapshots")),
        "snapshots_with_generated_candidates": _int(records.get("snapshots_with_generated_candidates")),
        "generated_candidate_rows": _int(records.get("generated_candidate_rows")),
        "lower_union_red_rows": _int(records.get("lower_union_red_rows")),
        "hard_feasible_rows": _int(records.get("lower_union_red_hard_feasible_rows")),
        "progress_feasible_rows": _int(records.get("lower_union_red_progress_feasible_rows")),
        "comfort_admissible_rows": _int(records.get("lower_union_red_comfort_admissible_rows")),
        "support_snapshots": _int(support.get("snapshots")),
        "hard_support_rate": _float(support.get("hard_feasible_snapshot_support_rate")),
        "comfort_support_rate": _float(support.get("comfort_admissible_snapshot_support_rate")),
        "min_snapshot_support_rate": _float(support.get("min_snapshot_support_rate")),
        "hard_support_pass": bool(support.get("hard_feasible_snapshot_support_pass")),
        "comfort_support_pass": bool(support.get("comfort_admissible_snapshot_support_pass")),
        "candidate_generation_executed": bool(analysis.get("candidate_generation_executed")),
        "future_outcome_leakage": bool(analysis.get("future_outcome_leakage")),
        "closed_loop_replay": bool(analysis.get("closed_loop_replay")),
        "training": bool(analysis.get("training")),
        "online_selector_change": bool(analysis.get("online_selector_change")),
        "dp_modification": bool(
            analysis.get("diffusion_planner_modification")
            or decision.get("dp_modification_authorized")
        ),
        "generator_policy": config.get("generator_policy"),
        "default_off_remediation_profile": config.get("default_off_remediation_profile"),
        "red_stop_margins_m": _list(config.get("red_stop_margins_m")),
        "backup_stop_offsets_m": _list(config.get("backup_stop_offsets_m")),
        "prefix_steps": _list(config.get("prefix_steps")),
        "bridge_steps": _list(config.get("bridge_steps")),
        "lane_projected_offset_scales": _list(config.get("lane_projected_offset_scales")),
        "max_remediation_candidates": _int(config.get("max_remediation_candidates")),
        "command_jerk_worse_budget_mps3": _float(config.get("command_jerk_worse_budget_mps3")),
        "rollout_jerk_worse_budget_mps3": _float(config.get("rollout_jerk_worse_budget_mps3")),
        "rollout_lateral_worse_budget_mps2": _float(config.get("rollout_lateral_worse_budget_mps2")),
        "blocked_authorizations": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
        "source_authorization_conflicts": _list(decision.get("source_authorization_conflicts")),
    }


def _construction_summary(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _list(payload.get("rows"))
    diagnostics = [_dict(row).get("candidate_construction_diagnostics") for row in rows]
    diagnostics = [_dict(item) for item in diagnostics]
    selected_union_red = [
        _float(_dict(row).get("selected_union_red"))
        for row in rows
        if _dict(row).get("selected_union_red") is not None
    ]
    generated_counts = [_int(_dict(row).get("generated_count")) for row in rows]
    candidate_rows = [_list(_dict(row).get("candidate_rows")) for row in rows]
    red_distances = [
        _float(item.get("red_distance_m"))
        for item in diagnostics
        if item.get("red_distance_m") is not None
    ]
    speeds = [
        _float(item.get("current_speed_mps"))
        for item in diagnostics
        if item.get("current_speed_mps") is not None
    ]
    candidate_counts = [
        _int(item.get("candidate_count"))
        for item in diagnostics
        if item.get("candidate_count") is not None
    ]
    feasible_windows = [
        _int(item.get("feasible_stop_windows"))
        for item in diagnostics
        if item.get("feasible_stop_windows") is not None
    ]
    return {
        "row_count": len(rows),
        "selected_union_red_count": len(selected_union_red),
        "selected_union_red_min": min(selected_union_red) if selected_union_red else None,
        "selected_union_red_max": max(selected_union_red) if selected_union_red else None,
        "row_generated_count_values": sorted(set(generated_counts)),
        "row_generated_count_sum": sum(generated_counts),
        "candidate_rows_sum": sum(len(items) for items in candidate_rows),
        "construction_status_counts": _count_values(
            item.get("construction_status") for item in diagnostics
        ),
        "failure_reason_counts": _count_values(
            item.get("failure_reason") for item in diagnostics
        ),
        "fail_closed_partitions": _count_values(
            item.get("fail_closed_partition") for item in diagnostics
        ),
        "hard_precheck_pass_count": sum(
            1 for item in diagnostics if item.get("hard_feasibility_precheck_passed")
        ),
        "comfort_precheck_pass_count": sum(
            1 for item in diagnostics if item.get("comfort_first_precheck_passed")
        ),
        "candidate_count_values": sorted(set(candidate_counts)),
        "candidate_count_sum": sum(candidate_counts),
        "feasible_stop_windows_values": sorted(set(feasible_windows)),
        "feasible_stop_windows_sum": sum(feasible_windows),
        "red_distance_min": min(red_distances) if red_distances else None,
        "red_distance_max": max(red_distances) if red_distances else None,
        "current_speed_min": min(speeds) if speeds else None,
        "current_speed_max": max(speeds) if speeds else None,
    }


def _failure_attribution(
    source: dict[str, Any],
    construction: dict[str, Any],
) -> dict[str, Any]:
    ready_rows = construction["construction_status_counts"].get("ready", 0)
    red_window_failures = construction["failure_reason_counts"].get(
        "red_stop_distance_window", 0
    )
    primary = "zero_lower_union_red_support_after_v3_candidate_construction"
    secondary = "red_stop_distance_window_fail_closed"
    interpretation = (
        "The guarded material v3 rerun executed candidate generation over the "
        "fixed nonformal seed-2 snapshot corpus, but the screen artifact contains "
        "zero generated candidate rows, zero candidate rows, zero lower-union-red "
        "rows, and zero hard/progress/comfort support. The diagnostic payload is "
        "more specific than a runtime or DP-head failure: 21 rows reached a ready "
        "construction partition with diagnostic stop-window support, while 36 "
        "rows failed closed at the red stop distance window. No row entered the "
        "finite candidate table used by the support gate, so replay, online "
        "promotion, and CAMP retraining remain unsupported."
    )
    return {
        "primary_attribution": primary,
        "secondary_attribution": secondary,
        "interpretation": interpretation,
        "ready_rows": ready_rows,
        "red_stop_distance_window_failures": red_window_failures,
        "zero_support_evidence": (
            source["generated_candidate_rows"] == 0
            and source["lower_union_red_rows"] == 0
            and source["hard_support_rate"] == 0.0
            and source["comfort_support_rate"] == 0.0
            and construction["candidate_rows_sum"] == 0
            and construction["row_generated_count_sum"] == 0
        ),
        "diagnostic_windows_present_without_candidate_rows": (
            ready_rows > 0
            and construction["candidate_count_sum"] > 0
            and construction["candidate_rows_sum"] == 0
        ),
        "positive_support_evidence": False,
        "training_ready": False,
        "replay_evidence_ready": False,
        "non_causes": [
            "runtime_preflight",
            "fixed_dp_head",
            "formal_seeds",
            "closed_loop_replay",
            "training",
            "online_selector",
            "descriptor_math_contract",
            "convex_master_contract",
            "global_hard_or_comfort_precheck_absence",
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    files = _dict(artifact.get("files"))
    return [
        _check("screen_root_exists", bool(artifact["exists"])),
        *[_check(f"{name}_exists", bool(files.get(name))) for name in files],
        _check("sha256sums_match", bool(artifact["sha256sums_ok"])),
        _check("screen_json_parseable", bool(artifact["screen_payload"])),
        _check("screen_markdown_records_verdict", "## Verdict" in artifact["screen_markdown"]),
        _check("candidate_screen_err_empty", artifact["candidate_err"].strip() == ""),
        _check("screen_exit_code_zero", artifact["exit_code"] == "0"),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    heads = _dict(artifact.get("heads"))
    return [
        _check("camp_head_matches_expected", camp_head == EXPECTED_CAMP_HEAD),
        _check("camp_origin_main_matches_expected", camp_origin_main == EXPECTED_CAMP_HEAD),
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("camp_head_file_matches_arg", heads.get("CAMP_HEAD") == camp_head),
        _check("camp_origin_main_file_matches_arg", heads.get("CAMP_ORIGIN_MAIN") == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
        _check("dp_head_file_fixed", heads.get("DP_HEAD") == EXPECTED_DP_HEAD),
        _check("snapshot_count_file", heads.get("SNAPSHOT_COUNT") == "57"),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("screen_status_is_support_insufficient", source["status"] == SCREEN_REJECT_STATUS),
        _check("screen_policy_is_guarded_material_v3", source["generator_policy"] == PLANNED_POLICY),
        _check("screen_profile_is_guarded_material_v3", source["default_off_remediation_profile"] == REMEDIATION_PROFILE),
        _check("screen_snapshots_present", source["snapshots"] == 57),
        _check("screen_candidate_generation_executed", source["candidate_generation_executed"] is True),
        _check("screen_generated_candidate_rows_zero", source["generated_candidate_rows"] == 0),
        _check("screen_lower_union_red_rows_zero", source["lower_union_red_rows"] == 0),
        _check("screen_hard_rows_zero", source["hard_feasible_rows"] == 0),
        _check("screen_progress_rows_zero", source["progress_feasible_rows"] == 0),
        _check("screen_comfort_rows_zero", source["comfort_admissible_rows"] == 0),
        _check("screen_support_snapshots_zero", source["support_snapshots"] == 0),
        _check("screen_hard_support_zero", source["hard_support_rate"] == 0.0),
        _check("screen_comfort_support_zero", source["comfort_support_rate"] == 0.0),
        _check("screen_hard_support_below_required", source["hard_support_pass"] is False),
        _check("screen_comfort_support_below_required", source["comfort_support_pass"] is False),
        _check("screen_no_source_authorization_conflicts", not source["source_authorization_conflicts"]),
        _check("screen_no_blocked_authorizations", not source["blocked_authorizations"]),
        _check("screen_no_future_outcome_leakage", source["future_outcome_leakage"] is False),
        _check("screen_no_closed_loop_replay", source["closed_loop_replay"] is False),
        _check("screen_no_training", source["training"] is False),
        _check("screen_no_dp_modification", source["dp_modification"] is False),
        _check("screen_zero_comfort_budgets", source["command_jerk_worse_budget_mps3"] == 0.0),
        _check("screen_zero_rollout_jerk_budget", source["rollout_jerk_worse_budget_mps3"] == 0.0),
        _check("screen_zero_rollout_lateral_budget", source["rollout_lateral_worse_budget_mps2"] == 0.0),
    ]


def _construction_checks(construction: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("construction_rows_match_snapshots", construction["row_count"] == 57),
        _check("construction_selected_union_red_all_rows", construction["selected_union_red_count"] == 57),
        _check("construction_row_generated_zero", construction["row_generated_count_sum"] == 0),
        _check("construction_candidate_rows_zero", construction["candidate_rows_sum"] == 0),
        _check("construction_ready_count_expected", construction["construction_status_counts"].get("ready") == 21),
        _check("construction_fail_closed_count_expected", construction["construction_status_counts"].get("fail_closed") == 36),
        _check("construction_red_window_failures_expected", construction["failure_reason_counts"].get("red_stop_distance_window") == 36),
        _check("construction_hard_precheck_partial_ready", construction["hard_precheck_pass_count"] == 21),
        _check("construction_comfort_precheck_partial_ready", construction["comfort_precheck_pass_count"] == 21),
        _check("construction_diagnostic_candidate_count_present", construction["candidate_count_sum"] == 456),
        _check("construction_feasible_stop_windows_present", construction["feasible_stop_windows_sum"] == 92),
    ]


def _attribution_checks(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(
            "attribution_primary_expected",
            attribution["primary_attribution"]
            == "zero_lower_union_red_support_after_v3_candidate_construction",
        ),
        _check("attribution_secondary_expected", attribution["secondary_attribution"] == "red_stop_distance_window_fail_closed"),
        _check("attribution_zero_support_evidence", attribution["zero_support_evidence"] is True),
        _check("attribution_diagnostic_windows_present", attribution["diagnostic_windows_present_without_candidate_rows"] is True),
        _check("attribution_positive_support_absent", attribution["positive_support_evidence"] is False),
        _check("attribution_training_not_ready", attribution["training_ready"] is False),
        _check("attribution_replay_not_ready", attribution["replay_evidence_ready"] is False),
    ]


def _boundary_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
        _check("boundary_blocks_full36", decision["full36_authorized"] is False),
        _check("boundary_blocks_training", decision["training_execution_authorized"] is False),
        _check("boundary_blocks_online_selector", decision["online_selector_authorized"] is False),
        _check("boundary_blocks_dp_modification", decision["dp_modification_authorized"] is False),
        _check("boundary_no_training_ready_claim", source["comfort_admissible_rows"] == 0),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failure_attribution_complete": passed,
        "remediation_design_plan_authorized": passed,
        "positive_support_evidence": False,
        "training_ready": False,
        "replay_evidence_ready": False,
    }
    decision.update({key: False for key in BLOCKED_ACTIONS})
    return decision


def _sha256sums_ok(path: Path) -> bool:
    if not path.is_file():
        return False
    for raw in path.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) < 2:
            return False
        expected, name = parts[0], parts[-1]
        target = Path(name)
        if not target.is_absolute():
            target = path.parent / target
        if not target.is_file() or _sha256(target) != expected:
            return False
    return True


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


def _parse_heads(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in artifact.items()
        if key not in {"screen_payload", "screen_markdown", "candidate_log", "candidate_err"}
    }


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = "null" if value is None else str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


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
