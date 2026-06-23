#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (  # noqa: E402
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (  # noqa: E402
    ABSOLUTE_ERR,
    ABSOLUTE_JSON,
    ABSOLUTE_READY_STATUS,
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    CANDIDATE_ERR,
    DEFAULT_DEVELOPMENT_ROOT,
    DEFAULT_SCREEN_ROOT,
    EXIT_CODE,
    HEADS,
    READY_STATUS as PLAN_READY_STATUS,
    RUNBOOK_EXIT,
    SCREEN_JSON,
    SCREEN_REJECT_STATUS,
    SHA256SUMS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_failure_attribution_read_only_"
    "analysis_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_failure_attribution_read_only_"
    "analysis_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "remediation_fixed_snapshot_screen_rerun_remediation_design_plan_only"
)

DEFAULT_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_"
    "failure_attribution_plan_2e647f4f"
)
PLAN_JSON = "fixed_snapshot_screen_rerun_failure_attribution_plan.json"

BLOCKED_ACTIONS = (
    "candidate_generation_execution_authorized",
    "fixed_snapshot_candidate_generation_authorized",
    "fixed_snapshot_screen_rerun_authorized",
    "fixed_snapshot_screen_rerun_execution_authorized",
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
    "safety_benefit_evidence",
    "camp_over_dp_top1_claim_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only failure attribution analysis for the default-off "
            "remediation fixed-snapshot screen rerun. This reads only "
            "existing screen, guard, and plan artifacts."
        )
    )
    parser.add_argument("--screen_root", type=Path, default=Path(DEFAULT_SCREEN_ROOT))
    parser.add_argument("--plan_root", type=Path, default=Path(DEFAULT_PLAN_ROOT))
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
        plan_root=args.plan_root,
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
    plan_root: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: str | None = None,
) -> dict[str, Any]:
    screen_artifact = _artifact_summary(
        screen_root,
        required_files=(
            SCREEN_JSON,
            ABSOLUTE_JSON,
            CANDIDATE_ERR,
            ABSOLUTE_ERR,
            EXIT_CODE,
            HEADS,
            SHA256SUMS,
        ),
    )
    plan_artifact = _artifact_summary(
        plan_root,
        required_files=(PLAN_JSON, EXIT_CODE, HEADS, SHA256SUMS),
    )
    screen_payload = _load_json_if_present(screen_root / SCREEN_JSON)
    absolute_payload = _load_json_if_present(screen_root / ABSOLUTE_JSON)
    plan_payload = _load_json_if_present(plan_root / PLAN_JSON)
    source = _source_summary(screen_payload, absolute_payload, plan_payload)
    attribution = _attribution_summary(screen_payload, absolute_payload)
    checks = [
        *_artifact_checks("screen", screen_artifact),
        *_artifact_checks("plan", plan_artifact),
        *_screen_execution_checks(screen_artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_plan_authorization_checks(source["plan"]),
        *_source_evidence_checks(source, attribution),
        *_attribution_checks(attribution),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "failure_attribution_read_only_analysis_v1"
            ),
            "label": label,
            "role": "read-only attribution over existing rerun artifacts",
            "read_only": True,
            "plan_only_next": True,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "math_boundary": (
                "This analysis reads only existing fixed-snapshot screen, "
                "absolute-guard, and plan artifacts. It does not create "
                "candidate trajectories, rerun the screen, run DP, run replay, "
                "use formal seeds, recompute outcomes, define runtime atoms, "
                "choose lambda online, alter score_k(w)=a_k^T w, mutate the "
                "convex simplex/CVaR/L2 master, train CAMP, change online "
                "selection, modify DP weights or code, claim safety benefit, "
                "claim CAMP is better than DP Top-1, or claim a DP-side "
                "classical Benders decomposition."
            ),
        },
        "head_audit": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "screen_artifact": screen_artifact,
        "plan_artifact": plan_artifact,
        "source_summary": source,
        "read_only_attribution": attribution,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    attribution = report["read_only_attribution"]
    lines = [
        "# Default-Off Fixed-Snapshot Rerun Failure Attribution Read-Only Analysis",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Evidence",
        "",
        f"- Screen status: `{source['screen']['status']}`",
        f"- Generated candidate rows: `{source['screen']['generated_candidate_rows']}`",
        f"- Hard rows: `{source['screen']['hard_rows']}`",
        f"- Progress rows: `{source['screen']['progress_rows']}`",
        f"- Comfort rows: `{source['screen']['comfort_rows']}`",
        f"- Absolute guard rows: `{source['absolute']['absolute_rows']}`",
        f"- Candidate-build p95 ms: `{source['screen']['candidate_build_p95_ms']}`",
        f"- Total p95 ms: `{source['screen']['total_p95_ms']}`",
        "",
        "## Comfort Blocker Ranking",
        "",
    ]
    for item in attribution["comfort_blocker_ranking"]:
        lines.append(
            f"- `{item['name']}` count=`{item['count']}` "
            f"share=`{item['share_of_generated_rows']}`"
        )
    lines.extend(["", "## Hard Blocker Ranking", ""])
    for item in attribution["hard_blocker_ranking"]:
        lines.append(
            f"- `{item['name']}` count=`{item['count']}` "
            f"share=`{item['share_of_generated_rows']}`"
        )
    lines.extend(["", "## Absolute Guard Failure Ranking", ""])
    for item in attribution["absolute_guard_failure_ranking"]:
        lines.append(
            f"- `{item['name']}` count=`{item['count']}` "
            f"share=`{item['share_of_generated_rows']}`"
        )
    lines.extend(["", "## Latency Ranking", ""])
    for item in attribution["latency_ranking"]:
        lines.append(
            f"- `{item['name']}` p95_ms=`{item['p95_ms']}` "
            f"gate_passed=`{item['gate_passed']}`"
        )
    lines.extend(
        [
            "",
            "## Attribution Conclusion",
            "",
            f"- Primary blocker family: `{attribution['primary_blocker_family']}`",
            f"- Primary comfort blocker: `{attribution['primary_comfort_blocker']}`",
            f"- Primary hard blocker: `{attribution['primary_hard_blocker']}`",
            f"- Primary latency source: `{attribution['primary_latency_source']}`",
            f"- Comfort support gap: `{attribution['comfort_support_gap']}`",
            f"- Absolute lateral guard retained: `{attribution['absolute_lateral_guard_retained']}`",
            "",
            "## Boundaries",
            "",
            "- candidate generation execution is not authorized",
            "- fixed-snapshot screen rerun is not authorized",
            "- replay is not authorized",
            "- formal seeds 11/12/13 remain frozen and unused",
            "- Full36 is not authorized",
            "- atom promotion, CAMP retraining, and online selector changes are not authorized",
            "- DP weights and DP code must remain fixed",
            "- no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            "- no DP-side classical Benders claim is authorized",
            "",
            "## Next Gate",
            "",
            (
                "Only "
                "`candidate_set_consensus_lane_projected_jerk_progress_support_"
                "default_off_remediation_fixed_snapshot_screen_rerun_"
                "remediation_design_plan_only` is authorized if all checks pass."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path, *, required_files: tuple[str, ...]) -> dict[str, Any]:
    files = {name: (root / name).is_file() for name in required_files}
    sha_ok, sha_details = _sha256sum_check(root / SHA256SUMS)
    exit_code_text = _read_text(root / EXIT_CODE).strip()
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "required_files": files,
        "required_files_present": all(files.values()),
        "sha256sums_ok": sha_ok,
        "sha256sums_details": sha_details,
        "exit_code": exit_code_text or None,
        "exit_code_ok": _exit_code_ok(exit_code_text),
        "runbook_exit": _read_text(root / RUNBOOK_EXIT).strip() or None,
        "heads_text_present": bool(_read_text(root / HEADS).strip()),
        "candidate_err_bytes": _file_size(root / CANDIDATE_ERR),
        "absolute_err_bytes": _file_size(root / ABSOLUTE_ERR),
    }


def _source_summary(
    screen_payload: dict[str, Any],
    absolute_payload: dict[str, Any],
    plan_payload: dict[str, Any],
) -> dict[str, Any]:
    screen_decision = _dict(screen_payload.get("final_decision"))
    screen_records = _dict(screen_payload.get("records"))
    support = _dict(screen_payload.get("support_gate"))
    latency = _dict(screen_payload.get("latency_ms"))
    candidate_build = _dict(latency.get("candidate_build"))
    total = _dict(latency.get("total"))
    absolute_decision = _dict(absolute_payload.get("final_decision"))
    absolute_records = _dict(absolute_payload.get("records"))
    absolute_support = _dict(absolute_payload.get("support_gate"))
    plan_decision = _dict(plan_payload.get("final_decision"))
    return {
        "screen": {
            "status": screen_decision.get("status"),
            "blocked_action_conflicts": [
                key for key in BLOCKED_ACTIONS if bool(screen_decision.get(key))
            ],
            "generated_candidate_rows": _int(screen_records.get("generated_candidate_rows")),
            "hard_rows": _int(screen_records.get("lower_union_red_hard_feasible_rows")),
            "progress_rows": _int(screen_records.get("lower_union_red_progress_feasible_rows")),
            "comfort_rows": _int(screen_records.get("lower_union_red_comfort_admissible_rows")),
            "snapshots": _int(screen_records.get("snapshots")),
            "snapshots_with_generated_candidates": _int(
                screen_records.get("snapshots_with_generated_candidates")
            ),
            "hard_support_rate": _float(support.get("hard_feasible_snapshot_support_rate")),
            "hard_support_pass": bool(support.get("hard_feasible_snapshot_support_pass")),
            "comfort_support_rate": _float(
                support.get("comfort_admissible_snapshot_support_rate")
            ),
            "comfort_support_pass": bool(
                support.get("comfort_admissible_snapshot_support_pass")
            ),
            "candidate_build_p95_ms": _float(candidate_build.get("p95")),
            "total_p95_ms": _float(total.get("p95")),
        },
        "absolute": {
            "status": absolute_decision.get("status"),
            "blocked_action_conflicts": [
                key for key in BLOCKED_ACTIONS if bool(absolute_decision.get(key))
            ],
            "absolute_rows": _int(absolute_records.get("absolute_lateral_guard_rows")),
            "hard_progress_rows": _int(absolute_records.get("lower_union_red_hard_progress_rows")),
            "absolute_support_rate": _float(
                absolute_support.get("absolute_lateral_guard_snapshot_support_rate")
            ),
            "absolute_support_pass": bool(
                absolute_support.get("absolute_lateral_guard_snapshot_support_pass")
            ),
        },
        "plan": {
            "status": plan_decision.get("status"),
            "authorized_next_work": plan_decision.get("authorized_next_work"),
            "read_only_failure_attribution_authorized": bool(
                plan_decision.get("read_only_failure_attribution_authorized")
            ),
            "candidate_generation_execution_authorized": bool(
                plan_decision.get("candidate_generation_execution_authorized")
            ),
            "fixed_snapshot_screen_rerun_authorized": bool(
                plan_decision.get("fixed_snapshot_screen_rerun_authorized")
            ),
            "new_replay_authorized": bool(plan_decision.get("new_replay_authorized")),
            "formal_seeds_authorized": bool(plan_decision.get("formal_seeds_authorized")),
            "full36_authorized": bool(plan_decision.get("full36_authorized")),
            "online_selector_authorized": bool(plan_decision.get("online_selector_authorized")),
            "atom_promotion_authorized": bool(plan_decision.get("atom_promotion_authorized")),
            "camp_retraining_authorized": bool(plan_decision.get("camp_retraining_authorized")),
            "dp_modification_authorized": bool(plan_decision.get("dp_modification_authorized")),
            "safety_benefit_evidence": bool(plan_decision.get("safety_benefit_evidence")),
            "camp_over_dp_top1_claim_authorized": bool(
                plan_decision.get("camp_over_dp_top1_claim_authorized")
            ),
            "classic_benders_claim_authorized": bool(
                plan_decision.get("classic_benders_claim_authorized")
            ),
        },
    }


def _attribution_summary(
    screen_payload: dict[str, Any],
    absolute_payload: dict[str, Any],
) -> dict[str, Any]:
    records = _dict(screen_payload.get("records"))
    generated_rows = _int(records.get("generated_candidate_rows"))
    failure_counts = _dict(screen_payload.get("failure_class_counts"))
    hard_counts = _dict(screen_payload.get("hard_reason_counts"))
    latency = _dict(screen_payload.get("latency_ms"))
    absolute_counts = _dict(absolute_payload.get("failure_class_counts"))
    support = _dict(screen_payload.get("support_gate"))
    absolute_records = _dict(absolute_payload.get("records"))
    comfort_support_gap = max(
        0.0,
        _float(support.get("min_snapshot_support_rate", 0.25))
        - _float(support.get("comfort_admissible_snapshot_support_rate")),
    )
    comfort_ranking = _rank_counts(
        {
            key: value
            for key, value in failure_counts.items()
            if key.startswith("route_topology_comfort_blocked_")
        },
        denominator=generated_rows,
    )
    hard_ranking = _rank_counts(hard_counts, denominator=generated_rows)
    absolute_ranking = _rank_counts(absolute_counts, denominator=generated_rows)
    latency_ranking = _latency_ranking(latency)
    latency_failures = [
        item for item in latency_ranking if item["gate_passed"] is False
    ]
    return {
        "comfort_blocker_ranking": comfort_ranking,
        "hard_blocker_ranking": hard_ranking,
        "absolute_guard_failure_ranking": absolute_ranking,
        "latency_ranking": latency_ranking,
        "latency_gate_failures": latency_failures,
        "snapshot_focus": _snapshot_focus(_list(screen_payload.get("by_snapshot"))),
        "primary_blocker_family": (
            "comfort_support_deficit"
            if comfort_support_gap > 0.0 and comfort_ranking
            else _primary_family(comfort_ranking, hard_ranking, latency_failures)
        ),
        "primary_comfort_blocker": comfort_ranking[0]["name"] if comfort_ranking else None,
        "primary_hard_blocker": hard_ranking[0]["name"] if hard_ranking else None,
        "primary_latency_source": latency_failures[0]["name"] if latency_failures else None,
        "comfort_support_gap": comfort_support_gap,
        "absolute_lateral_guard_retained": _int(
            absolute_records.get("absolute_lateral_guard_rows")
        )
        > 0,
        "recommendation_category": (
            "design-new-policy-plan-only"
            if comfort_support_gap > 0.0
            else "implementation-latency-diagnosis-only"
        ),
        "diagnostic_boundary": (
            "Read-only ranking over existing artifact counts and summaries; no "
            "new candidate generation, screen rerun, replay, training, "
            "promotion, formal seeds, claims, or DP modification."
        ),
    }


def _rank_counts(counts: dict[str, Any], *, denominator: int) -> list[dict[str, Any]]:
    ranked = []
    denom = max(denominator, 1)
    for name, value in counts.items():
        count = _int(value)
        ranked.append(
            {
                "name": name,
                "count": count,
                "share_of_generated_rows": count / denom,
            }
        )
    return sorted(ranked, key=lambda item: (-item["count"], item["name"]))


def _latency_ranking(latency: dict[str, Any]) -> list[dict[str, Any]]:
    thresholds = {"candidate_build": 10.0, "total": 100.0}
    ranked = []
    for name, value in latency.items():
        summary = _dict(value)
        p95 = _float(summary.get("p95"))
        threshold = thresholds.get(name)
        ranked.append(
            {
                "name": name,
                "p95_ms": p95,
                "mean_ms": _float(summary.get("mean")),
                "max_ms": _float(summary.get("max")),
                "threshold_ms": threshold,
                "gate_passed": None if threshold is None else p95 <= threshold,
            }
        )
    return sorted(ranked, key=lambda item: (-item["p95_ms"], item["name"]))


def _snapshot_focus(by_snapshot: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for item in by_snapshot:
        row = _dict(item)
        failures = _rank_counts(
            _dict(row.get("failure_class_counts")),
            denominator=max(_int(row.get("candidate_rows")), 1),
        )
        rows.append(
            {
                "selection_step": row.get("selection_step"),
                "candidate_rows": _int(row.get("candidate_rows")),
                "hard_feasible": _int(row.get("lower_union_red_hard_feasible")),
                "progress_feasible": _int(row.get("lower_union_red_progress_feasible")),
                "comfort_admissible": _int(row.get("lower_union_red_comfort_admissible")),
                "top_failure_classes": failures[:3],
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            item["comfort_admissible"],
            -item["hard_feasible"],
            -item["progress_feasible"],
            item["selection_step"] or 0,
        ),
    )[:10]


def _primary_family(
    comfort_ranking: list[dict[str, Any]],
    hard_ranking: list[dict[str, Any]],
    latency_failures: list[dict[str, Any]],
) -> str | None:
    comfort_top = comfort_ranking[0]["count"] if comfort_ranking else -1
    hard_top = hard_ranking[0]["count"] if hard_ranking else -1
    if comfort_top >= hard_top and comfort_top > 0:
        return "comfort_support_deficit"
    if hard_top > 0:
        return "hard_feasibility_support"
    if latency_failures:
        return "latency"
    return None


def _artifact_checks(prefix: str, artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(f"{prefix}_artifact_exists", artifact["exists"], True),
        _check_equal(f"{prefix}_required_files_present", artifact["required_files_present"], True),
        _check_equal(f"{prefix}_sha256sums_ok", artifact["sha256sums_ok"], True),
        _check_equal(f"{prefix}_exit_code_zero", artifact["exit_code_ok"], True),
        _check_equal(f"{prefix}_heads_present", artifact["heads_text_present"], True),
    ]


def _screen_execution_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "screen_runbook_exit_zero_if_present",
            artifact["runbook_exit"] in (None, "0"),
            True,
        ),
        _check_equal("screen_candidate_err_empty", artifact["candidate_err_bytes"], 0),
        _check_equal("screen_absolute_err_empty", artifact["absolute_err_bytes"], 0),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check_equal("camp_head_matches_origin_main", camp_head, camp_origin_main),
        _check_equal("dp_head_fixed", dp_head, EXPECTED_DP_HEAD),
    ]


def _plan_authorization_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    blocked = [
        key
        for key in (
            "candidate_generation_execution_authorized",
            "fixed_snapshot_screen_rerun_authorized",
            "new_replay_authorized",
            "formal_seeds_authorized",
            "full36_authorized",
            "online_selector_authorized",
            "atom_promotion_authorized",
            "camp_retraining_authorized",
            "dp_modification_authorized",
            "safety_benefit_evidence",
            "camp_over_dp_top1_claim_authorized",
            "classic_benders_claim_authorized",
        )
        if plan[key]
    ]
    return [
        _check_equal("plan_status_ready", plan["status"], PLAN_READY_STATUS),
        _check_equal(
            "plan_authorizes_read_only_analysis",
            plan["authorized_next_work"],
            PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _check_equal("plan_read_only_authorized", plan["read_only_failure_attribution_authorized"], True),
        _check_equal("plan_blocked_actions_clear", blocked, []),
    ]


def _source_evidence_checks(
    source: dict[str, Any],
    attribution: dict[str, Any],
) -> list[dict[str, Any]]:
    screen = source["screen"]
    absolute = source["absolute"]
    return [
        _check_equal("screen_status_rejected", screen["status"], SCREEN_REJECT_STATUS),
        _check_equal("screen_no_blocked_actions", screen["blocked_action_conflicts"], []),
        _check_equal("screen_generated_rows_positive", screen["generated_candidate_rows"] > 0, True),
        _check_equal("screen_hard_rows_positive", screen["hard_rows"] > 0, True),
        _check_equal("screen_progress_rows_positive", screen["progress_rows"] > 0, True),
        _check_equal("screen_comfort_rows_zero", screen["comfort_rows"], 0),
        _check_equal("screen_comfort_support_failed", screen["comfort_support_pass"], False),
        _check_equal("absolute_status_ready", absolute["status"], ABSOLUTE_READY_STATUS),
        _check_equal("absolute_no_blocked_actions", absolute["blocked_action_conflicts"], []),
        _check_equal("absolute_guard_rows_positive", absolute["absolute_rows"] > 0, True),
        _check_equal("absolute_support_passed", absolute["absolute_support_pass"], True),
        _check_equal("comfort_support_gap_positive", attribution["comfort_support_gap"] > 0.0, True),
    ]


def _attribution_checks(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("comfort_blocker_ranking_present", bool(attribution["comfort_blocker_ranking"]), True),
        _check_equal("hard_blocker_ranking_present", bool(attribution["hard_blocker_ranking"]), True),
        _check_equal("absolute_guard_failure_ranking_present", bool(attribution["absolute_guard_failure_ranking"]), True),
        _check_equal("latency_ranking_present", bool(attribution["latency_ranking"]), True),
        _check_equal("latency_gate_failure_present", bool(attribution["latency_gate_failures"]), True),
        _check_equal("absolute_lateral_guard_retained", attribution["absolute_lateral_guard_retained"], True),
        _check_equal("primary_blocker_family_set", attribution["primary_blocker_family"] is not None, True),
        _check_equal(
            "recommendation_is_plan_only",
            attribution["recommendation_category"],
            "design-new-policy-plan-only",
        ),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check_equal("boundary_blocks_candidate_generation", decision["candidate_generation_execution_authorized"], False),
        _check_equal("boundary_blocks_screen_rerun", decision["fixed_snapshot_screen_rerun_authorized"], False),
        _check_equal("boundary_blocks_replay", decision["new_replay_authorized"], False),
        _check_equal("boundary_blocks_formal_seeds", decision["formal_seeds_authorized"], False),
        _check_equal("boundary_blocks_dp_modification", decision["dp_modification_authorized"], False),
        _check_equal("boundary_blocks_safety_claim", decision["safety_benefit_evidence"], False),
        _check_equal("boundary_blocks_camp_over_dp_top1_claim", decision["camp_over_dp_top1_claim_authorized"], False),
        _check_equal("boundary_blocks_benders", decision["classic_benders_claim_authorized"], False),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "selected_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "read_only_failure_attribution_analysis_complete": passed,
        "remediation_design_plan_authorized": passed,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_candidate_generation_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
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
        "safety_benefit_evidence": False,
        "camp_over_dp_top1_claim_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _sha256sum_check(path: Path) -> tuple[bool, list[dict[str, Any]]]:
    if not path.is_file():
        return False, []
    root = path.parent
    details = []
    ok = True
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            ok = False
            details.append({"line": line, "ok": False, "reason": "malformed"})
            continue
        expected, name = parts
        item = Path(name.strip())
        if not item.is_absolute():
            item = root / item
        if not item.is_file():
            ok = False
            details.append({"path": str(item), "ok": False, "reason": "missing"})
            continue
        actual = hashlib.sha256(item.read_bytes()).hexdigest()
        matched = actual == expected
        ok = ok and matched
        details.append(
            {
                "path": str(item),
                "expected": expected,
                "actual": actual,
                "ok": matched,
            }
        )
    return ok, details


def _load_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _file_size(path: Path) -> int | None:
    if not path.is_file():
        return None
    return path.stat().st_size


def _exit_code_ok(text: str) -> bool:
    if text == "0":
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    for line in lines:
        if "=" not in line:
            return False
        key, value = line.split("=", 1)
        if not key.endswith("_EXIT") or value.strip() != "0":
            return False
    return True


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "observed": observed, "expected": expected, "passed": observed == expected}


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


if __name__ == "__main__":
    main()
