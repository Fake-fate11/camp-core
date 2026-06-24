#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
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
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_implementation_static_contract import (  # noqa: E402
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
)


READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_implementation_complete"
)
REJECT_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_implementation_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_post_implementation_static_contract_"
    "review_only"
)

DEFAULT_DEVELOPMENT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263"
)
DEFAULT_SCREEN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_fixed_snapshot_screen_rerun_bff8f8b"
)
DEFAULT_ATTRIBUTION_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_guarded_fixed_snapshot_screen_rerun_"
    "failure_attribution_bff8f8b"
)
DEFAULT_IMPLEMENTATION_PLAN_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "implementation_plan_bff8f8b"
)
DEFAULT_STATIC_REVIEW_ROOT = (
    f"{DEFAULT_DEVELOPMENT_ROOT}/candidate_set_consensus_lane_projected_"
    "jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_"
    "negative_support_followup_residual_comfort_failure_diagnostic_"
    "implementation_static_contract_review_bff8f8b"
)
DEFAULT_AUDIT_PATH = ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"

SCREEN_JSON = "negative_support_followup_fixed_snapshot_screen.json"
ATTRIBUTION_JSON = "failure_attribution.json"
PLAN_JSON = "implementation_plan.json"
STATIC_REVIEW_JSON = "static_contract_review.json"

REQUIRED_TABLES = (
    "comfort_blocker_by_snapshot",
    "comfort_blocker_by_red_stop_partition",
    "comfort_blocker_by_offset_margin",
    "hard_progress_survivor_distribution",
    "comfort_delta_quantiles",
    "diagnostic_decision_boundary",
)

COMFORT_PREFIX = "route_topology_comfort_blocked_"

BLOCKED_ACTIONS = (
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
            "Read-only residual comfort-failure diagnostics over completed "
            "fixed-snapshot screen artifacts."
        )
    )
    parser.add_argument("--screen_root", type=Path, default=Path(DEFAULT_SCREEN_ROOT))
    parser.add_argument(
        "--attribution_root",
        type=Path,
        default=Path(DEFAULT_ATTRIBUTION_ROOT),
    )
    parser.add_argument(
        "--implementation_plan_root",
        type=Path,
        default=Path(DEFAULT_IMPLEMENTATION_PLAN_ROOT),
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
        screen_root=args.screen_root,
        attribution_root=args.attribution_root,
        implementation_plan_root=args.implementation_plan_root,
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
    screen_root: Path,
    attribution_root: Path,
    implementation_plan_root: Path,
    static_review_root: Path,
    audit_path: Path,
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    label: Optional[str] = None,
) -> dict[str, Any]:
    screen_artifact = _artifact_summary(screen_root, SCREEN_JSON)
    attribution_artifact = _artifact_summary(attribution_root, ATTRIBUTION_JSON)
    plan_artifact = _artifact_summary(implementation_plan_root, PLAN_JSON)
    static_review_artifact = _artifact_summary(static_review_root, STATIC_REVIEW_JSON)
    audit_text = _read_text(audit_path)
    screen = _screen_summary(screen_artifact["payload"])
    attribution = _attribution_summary(attribution_artifact["payload"])
    plan = _plan_summary(plan_artifact["payload"])
    static_review = _static_review_summary(static_review_artifact["payload"])
    rows = _candidate_rows(screen_artifact["payload"])
    diagnostics = _diagnostic_tables(screen_artifact["payload"], attribution, rows)
    checks = [
        *_artifact_checks("screen", screen_artifact),
        *_artifact_checks("attribution", attribution_artifact),
        *_artifact_checks("implementation_plan", plan_artifact),
        *_artifact_checks("static_review", static_review_artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head),
        *_audit_checks(audit_text),
        *_authorization_checks(static_review),
        *_plan_checks(plan),
        *_screen_checks(screen, rows),
        *_attribution_checks(attribution),
        *_diagnostic_checks(diagnostics),
        *_boundary_checks(),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_lane_projected_jerk_progress_"
                "default_off_fixed_snapshot_screen_rerun_remediation_negative_"
                "support_followup_residual_comfort_failure_diagnostics_v1"
            ),
            "label": label,
            "role": "read-only residual comfort-failure diagnostics",
            "read_only": True,
            "implementation_code_edit": True,
            "production_implementation_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "reward_recompute": False,
            "tracker_recompute": False,
            "candidate_reconstruction": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": (
                "This diagnostic reads only completed screen, attribution, "
                "implementation-plan, static-review, and audit artifacts. It "
                "does not import DP, reconstruct candidates, recompute rewards "
                "or tracker proxies, rerun the screen, run replay, use formal "
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
        "source_artifacts": {
            "screen": _strip_payload(screen_artifact),
            "attribution": _strip_payload(attribution_artifact),
            "implementation_plan": _strip_payload(plan_artifact),
            "static_review": _strip_payload(static_review_artifact),
        },
        "source_summary": {
            "screen": screen,
            "attribution": attribution,
            "implementation_plan": plan,
            "static_review": static_review,
        },
        "diagnostic_tables": diagnostics,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    diagnostics = report["diagnostic_tables"]
    source = report["source_summary"]
    boundary = diagnostics["diagnostic_decision_boundary"]
    lines = [
        "# Residual Comfort Failure Diagnostics",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary blocker: `{boundary['primary_blocker_family']}`",
        f"- Candidate rows: `{source['screen']['generated_candidate_rows']}`",
        f"- Hard/progress survivors: `{boundary['hard_progress_survivor_rows']}`",
        f"- Comfort-admissible rows: `{boundary['comfort_admissible_rows']}`",
        "",
        "## Comfort Blockers By Snapshot",
        "",
    ]
    for item in diagnostics["comfort_blocker_by_snapshot"][:12]:
        lines.append(
            f"- `{item['snapshot_name']}`: rows=`{item['candidate_rows']}`, "
            f"hard_progress=`{item['hard_progress_rows']}`, "
            f"comfort=`{item['comfort_admissible_rows']}`, "
            f"top=`{item['top_comfort_blocker']}`"
        )
    lines.extend(["", "## Red Stop Partitions", ""])
    for item in diagnostics["comfort_blocker_by_red_stop_partition"]:
        lines.append(
            f"- `{item['red_stop_distance_partition']}`: rows=`{item['candidate_rows']}`, "
            f"hard_progress=`{item['hard_progress_rows']}`, "
            f"comfort=`{item['comfort_admissible_rows']}`"
        )
    lines.extend(["", "## Decision Boundary", ""])
    for key, value in boundary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- read-only diagnostic aggregation only",
            "- no DP import, reward recompute, tracker recompute, candidate reconstruction, screen rerun, replay, or training",
            "- no formal seeds, Full36, atom promotion, online selector promotion, safety claim, or DP modification",
            "- no CAMP-over-DP-Top-1 claim",
            "",
            "## Math Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_summary(root: Path, filename: str) -> dict[str, Any]:
    path = root / filename
    return {
        "root": str(root),
        "path": str(path),
        "root_exists": root.is_dir(),
        "json_exists": path.is_file(),
        "json_sha256": _sha256(path),
        "payload": _read_json(path),
    }


def _screen_summary(payload: dict[str, Any]) -> dict[str, Any]:
    records = _dict(payload.get("records"))
    support = _dict(payload.get("support_gate"))
    analysis = _dict(payload.get("analysis"))
    config = _dict(payload.get("config"))
    return {
        "status": _dict(payload.get("final_decision")).get("status"),
        "generator_policy": config.get("generator_policy"),
        "snapshots": _int(records.get("snapshots")),
        "snapshots_with_generated_candidates": _int(
            records.get("snapshots_with_generated_candidates")
        ),
        "generated_candidate_rows": _int(records.get("generated_candidate_rows")),
        "lower_union_red_rows": _int(records.get("lower_union_red_rows")),
        "hard_feasible_rows": _int(records.get("lower_union_red_hard_feasible_rows")),
        "progress_feasible_rows": _int(
            records.get("lower_union_red_progress_feasible_rows")
        ),
        "comfort_admissible_rows": _int(
            records.get("lower_union_red_comfort_admissible_rows")
        ),
        "hard_support_pass": bool(support.get("hard_feasible_snapshot_support_pass")),
        "comfort_support_pass": bool(
            support.get("comfort_admissible_snapshot_support_pass")
        ),
        "hard_support_rate": _float(support.get("hard_feasible_snapshot_support_rate")),
        "comfort_support_rate": _float(
            support.get("comfort_admissible_snapshot_support_rate")
        ),
        "future_outcome_leakage": bool(analysis.get("future_outcome_leakage")),
        "online_selector_change": bool(analysis.get("online_selector_change")),
        "closed_loop_replay": bool(analysis.get("closed_loop_replay")),
        "training": bool(analysis.get("training")),
    }


def _attribution_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    attribution = _dict(payload.get("read_only_attribution"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "primary_blocker_family": attribution.get("primary_blocker_family"),
        "hard_support_positive": bool(attribution.get("hard_support_positive")),
        "comfort_support_positive": bool(attribution.get("comfort_support_positive")),
        "positive_support_evidence": bool(attribution.get("positive_support_evidence")),
        "replay_evidence_ready": bool(attribution.get("replay_evidence_ready")),
        "training_ready": bool(attribution.get("training_ready")),
        "comfort_support_gap": _float(attribution.get("comfort_support_gap")),
        "comfort_blocker_ranking": [
            {"name": str(item.get("name")), "count": _int(item.get("count"))}
            for item in _list(attribution.get("comfort_blocker_ranking"))
            if isinstance(item, dict)
        ],
    }


def _plan_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("diagnostic_implementation_plan"))
    scope = _dict(plan.get("implementation_scope"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "planned_script": scope.get("planned_script"),
        "planned_test": scope.get("planned_test"),
        "read_only_existing_artifacts": bool(scope.get("read_only_existing_artifacts")),
        "no_candidate_reconstruction": bool(scope.get("no_candidate_reconstruction")),
        "no_reward_recompute": bool(scope.get("no_reward_recompute")),
        "no_tracker_recompute": bool(scope.get("no_tracker_recompute")),
        "no_dp_import": bool(scope.get("no_dp_import")),
        "required_tables": [str(item) for item in _list(plan.get("required_tables"))],
    }


def _static_review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "failed_checks": _list(decision.get("failed_checks")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "diagnostic_implementation_only_authorized": bool(
            decision.get("diagnostic_implementation_only_authorized")
        ),
        "next_gate_allowed_files": [
            str(item) for item in _list(decision.get("next_gate_allowed_files"))
        ],
        "next_gate_implementation_code_edit_authorized": bool(
            decision.get("next_gate_implementation_code_edit_authorized")
        ),
        "blocked_action_conflicts": [
            key for key in BLOCKED_ACTIONS if bool(decision.get(key))
        ],
    }


def _candidate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for snapshot in _list(payload.get("rows")):
        if not isinstance(snapshot, dict):
            continue
        for row in _list(snapshot.get("candidate_rows")):
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _diagnostic_tables(
    screen_payload: dict[str, Any],
    attribution: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "comfort_blocker_by_snapshot": _comfort_blocker_by_snapshot(screen_payload),
        "comfort_blocker_by_red_stop_partition": _group_by_meta(
            rows,
            ("red_stop_distance_partition",),
        ),
        "comfort_blocker_by_offset_margin": _group_by_meta(
            rows,
            ("lateral_offset_scale", "red_stop_margin_m", "backup_stop_offset_m"),
        ),
        "hard_progress_survivor_distribution": _survivor_distribution(rows),
        "comfort_delta_quantiles": _dict(screen_payload.get("progress_comfort_delta")),
        "diagnostic_decision_boundary": _decision_boundary(
            screen_payload,
            attribution,
            rows,
        ),
    }


def _comfort_blocker_by_snapshot(payload: dict[str, Any]) -> list[dict[str, Any]]:
    by_snapshot: list[dict[str, Any]] = []
    rows_by_path = {
        str(item.get("snapshot_path")): item
        for item in _list(payload.get("rows"))
        if isinstance(item, dict)
    }
    for item in _list(payload.get("by_snapshot")):
        if not isinstance(item, dict):
            continue
        snapshot_path = str(item.get("snapshot_path", ""))
        counts = _counter_from_mapping(_dict(item.get("failure_class_counts")))
        row = rows_by_path.get(snapshot_path, {})
        candidate_rows = _list(row.get("candidate_rows")) if isinstance(row, dict) else []
        hard_progress = [
            candidate
            for candidate in candidate_rows
            if isinstance(candidate, dict)
            and bool(candidate.get("hard_feasible"))
            and bool(candidate.get("progress_feasible"))
        ]
        by_snapshot.append(
            {
                "snapshot_name": Path(snapshot_path).name,
                "snapshot_path": snapshot_path,
                "selection_step": _int(item.get("selection_step")),
                "candidate_rows": len(candidate_rows),
                "hard_progress_rows": len(hard_progress),
                "comfort_admissible_rows": sum(
                    1 for candidate in hard_progress if bool(candidate.get("comfort_admissible"))
                ),
                "comfort_blocker_counts": _comfort_counts(counts),
                "top_comfort_blocker": _top_name(_comfort_counts(counts)),
            }
        )
    return by_snapshot


def _group_by_meta(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        meta = _dict(row.get("candidate_meta"))
        groups[tuple(_scalar(meta.get(key)) for key in keys)].append(row)
    result = []
    for values, members in sorted(groups.items(), key=lambda item: str(item[0])):
        counts = Counter()
        for row in members:
            counts.update(str(name) for name in _list(row.get("failure_classes")))
        hard_progress = [
            row
            for row in members
            if bool(row.get("hard_feasible")) and bool(row.get("progress_feasible"))
        ]
        entry = {
            key: values[index]
            for index, key in enumerate(keys)
        }
        entry.update(
            {
                "candidate_rows": len(members),
                "hard_progress_rows": len(hard_progress),
                "comfort_admissible_rows": sum(
                    1 for row in hard_progress if bool(row.get("comfort_admissible"))
                ),
                "comfort_blocker_counts": _comfort_counts(counts),
                "top_comfort_blocker": _top_name(_comfort_counts(counts)),
                "mean_progress_loss_m": _mean(
                    _float(row.get("progress_loss_m")) for row in members
                ),
            }
        )
        result.append(entry)
    return result


def _survivor_distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    survivors = [
        row
        for row in rows
        if bool(row.get("hard_feasible")) and bool(row.get("progress_feasible"))
    ]
    counts = Counter()
    for row in survivors:
        counts.update(str(name) for name in _list(row.get("failure_classes")))
    return {
        "hard_progress_survivor_rows": len(survivors),
        "comfort_admissible_rows": sum(
            1 for row in survivors if bool(row.get("comfort_admissible"))
        ),
        "comfort_blocker_counts": _comfort_counts(counts),
        "mean_progress_loss_m": _mean(_float(row.get("progress_loss_m")) for row in survivors),
        "mean_smoothness_loss": _mean(_float(row.get("smoothness_loss")) for row in survivors),
    }


def _decision_boundary(
    payload: dict[str, Any],
    attribution: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    records = _dict(payload.get("records"))
    support = _dict(payload.get("support_gate"))
    survivor_rows = [
        row
        for row in rows
        if bool(row.get("hard_feasible")) and bool(row.get("progress_feasible"))
    ]
    return {
        "primary_blocker_family": attribution["primary_blocker_family"],
        "generated_candidate_rows": _int(records.get("generated_candidate_rows")),
        "hard_progress_survivor_rows": len(survivor_rows),
        "comfort_admissible_rows": sum(
            1 for row in survivor_rows if bool(row.get("comfort_admissible"))
        ),
        "hard_support_positive": bool(attribution["hard_support_positive"]),
        "comfort_support_positive": bool(attribution["comfort_support_positive"]),
        "positive_support_evidence": bool(attribution["positive_support_evidence"]),
        "replay_evidence_ready": bool(attribution["replay_evidence_ready"]),
        "training_ready": bool(attribution["training_ready"]),
        "comfort_support_gap": attribution["comfort_support_gap"],
        "min_snapshot_support_rate": _float(support.get("min_snapshot_support_rate")),
        "diagnostic_recommendation": (
            "inspect comfort blockers before any replay or training authorization"
        ),
    }


def _artifact_checks(name: str, artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(f"{name}_root_exists", artifact["root_exists"]),
        _check(f"{name}_json_exists", artifact["json_exists"]),
        _check(f"{name}_json_parseable", bool(artifact["payload"])),
    ]


def _head_checks(camp_head: str, camp_origin_main: str, dp_head: str) -> list[dict[str, Any]]:
    return [
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
    ]


def _audit_checks(audit_text: str) -> list[dict[str, Any]]:
    return [
        _check("audit_present", bool(audit_text)),
        _check("audit_records_static_review_complete", STATIC_REVIEW_READY_STATUS in audit_text),
        _check("audit_authorizes_implementation", STATIC_REVIEW_AUTHORIZED_NEXT_WORK in audit_text),
        _check("audit_records_allowed_files", ALLOWED_NEXT_FILES[0] in audit_text and ALLOWED_NEXT_FILES[1] in audit_text),
        _check("audit_blocks_training", "training_execution_authorized=False" in audit_text),
        _check("audit_blocks_dp_modification", "dp_modification_authorized=False" in audit_text),
    ]


def _authorization_checks(static_review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("static_review_status_complete", static_review["status"] == STATIC_REVIEW_READY_STATUS),
        _check("static_review_passed", static_review["passed"] is True),
        _check("static_review_failed_checks_empty", not static_review["failed_checks"]),
        _check(
            "static_review_authorizes_this_implementation",
            static_review["authorized_next_work"] == STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
        ),
        _check("static_review_implementation_only_authorized", static_review["diagnostic_implementation_only_authorized"] is True),
        _check("static_review_next_gate_scoped_files", tuple(static_review["next_gate_allowed_files"]) == ALLOWED_NEXT_FILES),
        _check("static_review_next_gate_edit_authorized", static_review["next_gate_implementation_code_edit_authorized"] is True),
        _check("static_review_no_blocked_actions", not static_review["blocked_action_conflicts"]),
    ]


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("plan_passed", plan["passed"] is True),
        _check("plan_targets_script", plan["planned_script"] == ALLOWED_NEXT_FILES[0]),
        _check("plan_targets_test", plan["planned_test"] == ALLOWED_NEXT_FILES[1]),
        _check("plan_read_only_artifacts", plan["read_only_existing_artifacts"] is True),
        _check("plan_no_candidate_reconstruction", plan["no_candidate_reconstruction"] is True),
        _check("plan_no_reward_recompute", plan["no_reward_recompute"] is True),
        _check("plan_no_tracker_recompute", plan["no_tracker_recompute"] is True),
        _check("plan_no_dp_import", plan["no_dp_import"] is True),
        _check("plan_required_tables_present", set(REQUIRED_TABLES).issubset(set(plan["required_tables"]))),
    ]


def _screen_checks(screen: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _check("screen_has_rows", bool(rows)),
        _check("screen_hard_support_pass", screen["hard_support_pass"] is True),
        _check("screen_comfort_support_absent", screen["comfort_support_pass"] is False),
        _check("screen_generated_candidate_rows_positive", screen["generated_candidate_rows"] > 0),
        _check("screen_hard_feasible_rows_positive", screen["hard_feasible_rows"] > 0),
        _check("screen_comfort_admissible_rows_zero", screen["comfort_admissible_rows"] == 0),
        _check("screen_no_future_outcome_leakage", screen["future_outcome_leakage"] is False),
        _check("screen_no_online_selector_change", screen["online_selector_change"] is False),
        _check("screen_no_closed_loop_replay", screen["closed_loop_replay"] is False),
        _check("screen_no_training", screen["training"] is False),
    ]


def _attribution_checks(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("attribution_passed", attribution["passed"] is True),
        _check("attribution_primary_blocker", attribution["primary_blocker_family"] == "comfort_support_zero_after_hard_support_pass"),
        _check("attribution_hard_positive", attribution["hard_support_positive"] is True),
        _check("attribution_comfort_absent", attribution["comfort_support_positive"] is False),
        _check("attribution_no_positive_support", attribution["positive_support_evidence"] is False),
        _check("attribution_replay_not_ready", attribution["replay_evidence_ready"] is False),
        _check("attribution_training_not_ready", attribution["training_ready"] is False),
    ]


def _diagnostic_checks(diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    boundary = diagnostics["diagnostic_decision_boundary"]
    return [
        *[_check(f"diagnostic_table_{name}", name in diagnostics) for name in REQUIRED_TABLES],
        _check("diagnostic_snapshot_table_nonempty", bool(diagnostics["comfort_blocker_by_snapshot"])),
        _check("diagnostic_partition_table_nonempty", bool(diagnostics["comfort_blocker_by_red_stop_partition"])),
        _check("diagnostic_offset_table_nonempty", bool(diagnostics["comfort_blocker_by_offset_margin"])),
        _check("diagnostic_survivors_positive", diagnostics["hard_progress_survivor_distribution"]["hard_progress_survivor_rows"] > 0),
        _check("diagnostic_boundary_primary_blocker", boundary["primary_blocker_family"] == "comfort_support_zero_after_hard_support_pass"),
        _check("diagnostic_boundary_blocks_training", boundary["training_ready"] is False),
    ]


def _boundary_checks() -> list[dict[str, Any]]:
    decision = _final_decision(True, [])
    return [
        _check("boundary_current_gate_code_edit_scoped", decision["implementation_code_edit_authorized"] is True),
        _check("boundary_blocks_production_edit", decision["production_implementation_edit_authorized"] is False),
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
        "residual_comfort_diagnostics_complete": passed,
        "post_implementation_static_contract_review_authorized": passed,
        "implementation_code_edit_authorized": passed,
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


def _comfort_counts(counts: Counter[str]) -> dict[str, int]:
    return {
        name: int(count)
        for name, count in sorted(counts.items())
        if name.startswith(COMFORT_PREFIX) and int(count) > 0
    }


def _counter_from_mapping(value: dict[str, Any]) -> Counter[str]:
    return Counter({str(key): _int(count) for key, count in value.items()})


def _top_name(counts: dict[str, int]) -> Optional[str]:
    if not counts:
        return None
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def _mean(values: Any) -> Optional[float]:
    finite = [value for value in values if isinstance(value, float) and math.isfinite(value)]
    if not finite:
        return None
    return sum(finite) / len(finite)


def _scalar(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return str(value)


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and math.isfinite(value):
        return int(value)
    return 0


def _float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


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
    return {key: value for key, value in artifact.items() if key != "payload"}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
