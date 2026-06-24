#!/usr/bin/env python3
from __future__ import annotations

import argparse
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

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_guarded_fixed_snapshot_screen_rerun_failure_attribution import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as FAILURE_ATTRIBUTION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
    FORMAL_SEEDS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_implementation_plan import (  # noqa: E402
    PLANNED_POLICY,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_plan_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_static_contract_review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_ATTRIBUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_guarded_fixed_snapshot_screen_rerun_"
    "failure_attribution_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

ATTRIBUTION_JSON = "failure_attribution.json"
ATTRIBUTION_MD = "failure_attribution.md"

PRIMARY_BLOCKER_FAMILY = "comfort_support_zero_after_hard_support_pass"

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
            "Plan-only residual comfort-failure diagnostics for the "
            "negative-support follow-up screen result."
        )
    )
    parser.add_argument(
        "--attribution_root",
        type=Path,
        default=Path(DEFAULT_ATTRIBUTION_ROOT),
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
        attribution_root=args.attribution_root,
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
    attribution_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    artifact = _artifact_summary(attribution_root)
    audit_text = _read_text(audit_path)
    source = _attribution_summary(artifact["payload"])
    plan = _diagnostic_plan(source)
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
                "support_followup_residual_comfort_failure_diagnostic_plan_v1"
            ),
            "label": label,
            "role": "plan-only residual comfort-failure diagnostic contract",
            "plan_only": True,
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
                "This plan reads only audit text and completed attribution "
                "artifacts. It does not edit implementation code, create "
                "candidates, rerun the screen, run DP, run replay, use formal "
                "seeds, define runtime atoms, choose lambda online, alter "
                "score_k(w)=a_k^T w, mutate the convex simplex/CVaR/L2 master, "
                "train CAMP, change online selection, modify DP weights or "
                "code, or claim a DP-side classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "attribution_artifact": _strip_payload(artifact),
        "attribution_summary": source,
        "residual_comfort_diagnostic_plan": plan,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["attribution_summary"]
    plan = report["residual_comfort_diagnostic_plan"]
    lines = [
        "# Negative-Support Residual Comfort Diagnostic Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary blocker family: `{source['primary_blocker_family']}`",
        f"- Hard support positive: `{source['hard_support_positive']}`",
        f"- Comfort support positive: `{source['comfort_support_positive']}`",
        "",
        "## Observed Gap",
        "",
    ]
    for key, value in plan["observed_gap"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Diagnostic Tables", ""])
    for item in plan["diagnostic_tables"]:
        lines.append(f"- `{item['name']}`: {item['contract']}")
    lines.extend(["", "## Correlation Axes", ""])
    for item in plan["correlation_axes"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Required Static Review", ""])
    for item in plan["static_review_requirements"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden Work", ""])
    for item in plan["blocked_boundaries"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _diagnostic_plan(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_type": "negative_support_residual_comfort_failure_diagnostic_plan_only",
        "selected_next_work": AUTHORIZED_NEXT_WORK,
        "observed_gap": {
            "primary_blocker_family": source["primary_blocker_family"],
            "hard_support_positive": source["hard_support_positive"],
            "comfort_support_positive": source["comfort_support_positive"],
            "positive_support_evidence": source["positive_support_evidence"],
            "replay_evidence_ready": source["replay_evidence_ready"],
            "training_ready": source["training_ready"],
            "top_comfort_blockers": source["comfort_blocker_names"],
        },
        "diagnostic_scope": {
            "planned_policy": PLANNED_POLICY,
            "source_artifact": "failure_attribution.json",
            "diagnostic_inputs": "existing fixed-snapshot screen JSON and attribution JSON",
            "current_tick_only": True,
            "read_only_existing_artifacts": True,
            "no_candidate_reconstruction": True,
            "json_serializable_scalars_only": True,
            "score_contract": "score_k(w)=a_k^T w remains unchanged",
            "convex_master_contract": "simplex/CVaR/L2 master remains unchanged",
        },
        "diagnostic_tables": [
            {
                "name": "comfort_blocker_by_snapshot",
                "contract": (
                    "summarize command jerk, command lateral, rollout jerk, "
                    "rollout lateral, progress loss, rollout distance, and "
                    "smoothness blockers per snapshot using only existing row "
                    "failure_classes"
                ),
            },
            {
                "name": "comfort_blocker_by_red_stop_partition",
                "contract": (
                    "correlate residual comfort blockers with existing "
                    "red_stop_distance_partition and fail_closed_partition "
                    "metadata when present"
                ),
            },
            {
                "name": "comfort_blocker_by_offset_margin",
                "contract": (
                    "correlate blockers with existing lateral_offset_scale, "
                    "red_stop_margin_m, backup_stop_offset_m, stop_distance_m, "
                    "and red_distance_m scalar metadata"
                ),
            },
            {
                "name": "hard_progress_survivor_distribution",
                "contract": (
                    "isolate rows that are hard_feasible and progress_feasible "
                    "then report the comfort failure intersection; no rows may "
                    "be re-scored or regenerated"
                ),
            },
            {
                "name": "comfort_delta_quantiles",
                "contract": (
                    "reuse existing progress_comfort_delta aggregate fields "
                    "to report command and rollout quantiles without rerunning "
                    "reward, tracker, DP, or screen code"
                ),
            },
            {
                "name": "diagnostic_decision_boundary",
                "contract": (
                    "decide whether the residual blocker is construction-shape "
                    "comfort failure, screen-contract overconstraint, or "
                    "insufficient current-tick separability; this remains "
                    "diagnostic-only and cannot authorize training"
                ),
            },
        ],
        "correlation_axes": [
            "failure_class",
            "snapshot_name",
            "red_stop_distance_partition",
            "fail_closed_partition",
            "lateral_offset_scale",
            "red_stop_margin_m",
            "backup_stop_offset_m",
            "stop_distance_m",
            "red_distance_m",
            "current_speed_mps",
            "hard_feasible",
            "progress_feasible",
            "comfort_admissible",
        ],
        "static_review_requirements": [
            "prove the diagnostic reads only completed screen and attribution artifacts",
            "prove no DP import, reward recompute, tracker recompute, candidate generation, screen rerun, or replay is required",
            "prove all diagnostic tables are JSON-serializable scalar summaries",
            "prove diagnostics cannot modify candidate rows, generated counts, scores, support gates, selected index, fallback, atoms, or online selector inputs",
            "prove formal seeds 11/12/13 and Full36 remain unused",
            "prove the next executable work is not authorized by this plan gate",
            "prove no safety-benefit, CAMP-over-DP-Top-1, or classical Benders claim is implied",
            "prove score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master remain unchanged",
        ],
        "acceptance_criteria": [
            "attribution artifact is present and complete",
            "primary blocker is comfort_support_zero_after_hard_support_pass",
            "hard support is positive but comfort support is absent",
            "next gate is static contract review only",
            "all execution, training, promotion, safety claim, and DP modification flags remain false",
        ],
        "blocked_boundaries": [
            "implementation edits are not authorized in this plan gate",
            "candidate generation execution is not authorized",
            "fixed-snapshot screen rerun is not authorized",
            "replay and closed-loop smoke are not authorized",
            "formal seeds 11/12/13 remain frozen and unused",
            "Full36 is not authorized",
            "atom promotion, CAMP retraining, and online selector changes are not authorized",
            "DP weights, DP code, DP config, and DP invocation must remain fixed",
            "no safety-benefit claim, CAMP-over-DP-Top-1 claim, or classical Benders claim is authorized",
        ],
    }


def _artifact_summary(root: Path) -> dict[str, Any]:
    payload_path = root / ATTRIBUTION_JSON
    markdown_path = root / ATTRIBUTION_MD
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "json_exists": payload_path.is_file(),
        "markdown_exists": markdown_path.is_file(),
        "json_sha256": _sha256(payload_path),
        "markdown_sha256": _sha256(markdown_path),
        "payload": _read_json(payload_path),
        "markdown_text": _read_text(markdown_path),
    }


def _attribution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    attribution = _dict(payload.get("read_only_attribution"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "hard_support_positive": bool(decision.get("hard_support_positive")),
        "comfort_support_positive": bool(decision.get("comfort_support_positive")),
        "positive_support_evidence": bool(decision.get("positive_support_evidence")),
        "replay_evidence_ready": bool(decision.get("replay_evidence_ready")),
        "training_ready": bool(decision.get("training_ready")),
        "comfort_blocker_names": [
            str(item.get("name"))
            for item in _list(attribution.get("comfort_blocker_ranking"))
            if isinstance(item, dict)
        ],
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("attribution_root_exists", artifact["exists"]),
        _check("attribution_json_exists", artifact["json_exists"]),
        _check("attribution_markdown_exists", artifact["markdown_exists"]),
        _check("attribution_json_parseable", bool(artifact["payload"])),
        _check(
            "attribution_markdown_records_failure_attribution",
            "Failure Attribution" in artifact["markdown_text"],
        ),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_present", bool(audit_text)),
        _check("audit_records_failure_attribution_complete", FAILURE_ATTRIBUTION_READY_STATUS in audit_text),
        _check("audit_authorizes_this_plan", FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_primary_blocker", PRIMARY_BLOCKER_FAMILY in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    comfort = set(source["comfort_blocker_names"])
    return [
        _check("attribution_status_complete", source["status"] == FAILURE_ATTRIBUTION_READY_STATUS),
        _check("attribution_passed", source["passed"] is True),
        _check("attribution_failed_checks_empty", not source["failed_checks"]),
        _check("attribution_authorizes_this_plan", source["authorized_next_work"] == FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK),
        _check("attribution_primary_blocker", source["primary_blocker_family"] == PRIMARY_BLOCKER_FAMILY),
        _check("attribution_hard_support_positive", source["hard_support_positive"] is True),
        _check("attribution_comfort_support_absent", source["comfort_support_positive"] is False),
        _check("attribution_no_positive_support", source["positive_support_evidence"] is False),
        _check("attribution_replay_not_ready", source["replay_evidence_ready"] is False),
        _check("attribution_training_not_ready", source["training_ready"] is False),
        _check("attribution_no_blocked_actions", not source["blocked_action_conflicts"]),
        _check(
            "attribution_top_comfort_blockers_present",
            "route_topology_comfort_blocked_command_jerk" in comfort
            and "route_topology_comfort_blocked_rollout_lateral" in comfort,
        ),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    text = json.dumps(plan, sort_keys=True).lower()
    table_names = {item["name"] for item in plan["diagnostic_tables"]}
    axes = set(plan["correlation_axes"])
    return [
        _check("plan_selected_next_work", plan["selected_next_work"] == AUTHORIZED_NEXT_WORK),
        _check("plan_selection_type", plan["selection_type"] == "negative_support_residual_comfort_failure_diagnostic_plan_only"),
        _check("plan_policy", plan["diagnostic_scope"]["planned_policy"] == PLANNED_POLICY),
        _check("plan_reads_existing_artifacts", plan["diagnostic_scope"]["read_only_existing_artifacts"] is True),
        _check("plan_no_candidate_reconstruction", plan["diagnostic_scope"]["no_candidate_reconstruction"] is True),
        _check("plan_json_scalars", plan["diagnostic_scope"]["json_serializable_scalars_only"] is True),
        _check("plan_has_snapshot_table", "comfort_blocker_by_snapshot" in table_names),
        _check("plan_has_partition_table", "comfort_blocker_by_red_stop_partition" in table_names),
        _check("plan_has_offset_margin_table", "comfort_blocker_by_offset_margin" in table_names),
        _check("plan_has_survivor_table", "hard_progress_survivor_distribution" in table_names),
        _check("plan_has_delta_quantiles", "comfort_delta_quantiles" in table_names),
        _check("plan_has_decision_boundary", "diagnostic_decision_boundary" in table_names),
        _check("plan_has_failure_axis", "failure_class" in axes),
        _check("plan_has_partition_axis", "red_stop_distance_partition" in axes),
        _check("plan_has_offset_axis", "lateral_offset_scale" in axes),
        _check("plan_mentions_score_linear", "score_k(w)=a_k^t w" in text),
        _check("plan_mentions_convex_master", "simplex/cvar/l2" in text),
        _check("plan_blocks_execution", "candidate generation execution is not authorized" in text),
        _check("plan_blocks_formal_seeds", "formal seeds 11/12/13 remain frozen" in text),
        _check("plan_blocks_claims", "camp-over-dp-top-1" in text),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_authorizes_static_review", decision["static_contract_review_authorized"] is True),
        _check("boundary_blocks_implementation", decision["implementation_code_edit_authorized"] is False),
        _check("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"] is False),
        _check("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"] is False),
        _check("boundary_blocks_replay", decision["new_replay_authorized"] is False),
        _check("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"] is False),
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
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "static_contract_review_authorized": passed,
        "residual_comfort_diagnostic_plan_ready": passed,
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
    import hashlib

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
