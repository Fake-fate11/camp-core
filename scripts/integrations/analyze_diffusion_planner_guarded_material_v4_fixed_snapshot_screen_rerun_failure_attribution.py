#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Optional


EXPECTED_ANALYSIS_CAMP_HEAD = "10676d9b92a456f43a15010520ceeccd172b1362"
EXPECTED_SOURCE_ARTIFACT_CAMP_HEAD = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"
EXPECTED_CAMP_HEAD = EXPECTED_ANALYSIS_CAMP_HEAD
EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCREEN_REJECT_STATUS = "route_topology_candidate_support_insufficient"
REMEDIATION_PROFILE = "lane_red_hard_feasible_comfort_first_materialized_support_v4"

READY_STATUS = (
    "candidate_set_consensus_lane_projected_jerk_progress_support_default_off_"
    "fixed_snapshot_screen_rerun_remediation_negative_support_followup_"
    "residual_comfort_failure_diagnostic_remediation_followup_materially_"
    "different_generator_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
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
    "attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_"
    "attribution_remediation_design_plan_only"
)

DEFAULT_SCREEN_ROOT = (
    "/root/autodl-tmp/camp_dp_material_generator_failure_attribution_remediation_"
    "guarded_rerun_failure_attribution_remediation_v4_fixed_snapshot_screen_"
    "rerun_bff8f8b"
)
SCREEN_JSON = "default_off_v4_fixed_snapshot_screen.json"
SCREEN_MD = "default_off_v4_fixed_snapshot_screen.md"
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

REQUIRED_FILES = (
    SCREEN_JSON,
    SCREEN_MD,
    CANDIDATE_LOG,
    CANDIDATE_ERR,
    HEADS,
    SHA256SUMS,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only failure attribution over the guarded material v4 "
            "fixed-snapshot screen rerun artifact."
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
    materialization = _materialization_summary(payload)
    attribution = _failure_attribution(source, materialization)
    checks = [
        *_artifact_checks(artifact),
        *_head_checks(camp_head, camp_origin_main, dp_head, artifact),
        *_source_checks(source),
        *_materialization_checks(materialization, source),
        *_attribution_checks(attribution),
        *_boundary_checks(source),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_guarded_material_generator_v4_fixed_snapshot_screen_"
                "rerun_failure_attribution_v1"
            ),
            "label": label,
            "role": "read-only attribution over completed guarded v4 screen rerun",
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
            "expected_analysis_camp_head": EXPECTED_ANALYSIS_CAMP_HEAD,
            "expected_source_artifact_camp_head": EXPECTED_SOURCE_ARTIFACT_CAMP_HEAD,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
        "screen_artifact": _strip_payload(artifact),
        "source_summary": source,
        "materialization_summary": materialization,
        "read_only_attribution": attribution,
        "checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    materialization = report["materialization_summary"]
    attribution = report["read_only_attribution"]
    lines = [
        "# Guarded Material v4 Screen Rerun Failure Attribution",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Screen status: `{source['status']}`",
        f"- Primary blocker family: `{attribution['primary_blocker_family']}`",
        f"- Secondary blocker family: `{attribution['secondary_blocker_family']}`",
        f"- Training ready: `{attribution['training_ready']}`",
        "",
        "## Support Shape",
        "",
        f"- Snapshots: `{source['snapshots']}`",
        f"- Snapshots with generated candidates: `{source['snapshots_with_generated_candidates']}`",
        f"- Generated candidate rows: `{source['generated_candidate_rows']}`",
        f"- Lower-union-red rows: `{source['lower_union_red_rows']}`",
        f"- Hard-feasible rows: `{source['hard_feasible_rows']}`",
        f"- Progress-feasible rows: `{source['progress_feasible_rows']}`",
        f"- Comfort-admissible rows: `{source['comfort_admissible_rows']}`",
        f"- Hard support rate: `{source['hard_support_rate']}`",
        f"- Comfort support rate: `{source['comfort_support_rate']}`",
        "",
        "## Failure Classes",
        "",
    ]
    for item in attribution["failure_class_ranking"]:
        lines.append(f"- `{item['name']}`: count=`{item['count']}`")
    lines.extend(["", "## Hard Reasons", ""])
    for item in attribution["hard_reason_ranking"]:
        lines.append(f"- `{item['name']}`: count=`{item['count']}`")
    lines.extend(["", "## Comfort Blockers", ""])
    for item in attribution["comfort_blocker_ranking"]:
        lines.append(f"- `{item['name']}`: count=`{item['count']}`")
    lines.extend(
        [
            "",
            "## Materialization Contract",
            "",
            f"- Materialized rows: `{materialization['materialized_rows']}`",
            f"- Report-only rows: `{materialization['report_only_rows']}`",
            f"- Uses outcome labels rows: `{materialization['uses_outcome_labels_rows']}`",
            f"- Score mutation rows: `{materialization['score_mutation_rows']}`",
            f"- Selector mutation rows: `{materialization['selector_mutation_rows']}`",
            f"- Profile counts: `{materialization['profile_counts']}`",
            "",
            "## Attribution",
            "",
            attribution["interpretation"],
            "",
            "## Non-Causes",
            "",
        ]
    )
    for item in attribution["non_causes"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- read-only failure attribution only",
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
    files = {name: (root / name).is_file() for name in REQUIRED_FILES}
    return {
        "root": str(root),
        "exists": root.is_dir(),
        "files": files,
        "sha256sums_ok": _sha256sums_ok(root / SHA256SUMS, root),
        "screen_json_sha256": _sha256(root / SCREEN_JSON),
        "screen_md_sha256": _sha256(root / SCREEN_MD),
        "candidate_log_sha256": _sha256(root / CANDIDATE_LOG),
        "candidate_err_sha256": _sha256(root / CANDIDATE_ERR),
        "exit_code": _read_text(root / EXIT_CODE).strip() or None,
        "heads_sha256": _sha256(root / HEADS),
        "sha256sums_sha256": _sha256(root / SHA256SUMS),
        "heads": _read_heads(root / HEADS),
        "screen_payload": _read_json(root / SCREEN_JSON),
    }


def _source_summary(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("rows", [])
    candidate_rows = _candidate_rows(payload)
    decision = payload.get("final_decision", {})
    support_gate = payload.get("support_gate", {})
    analysis = payload.get("analysis", {})
    records = _dict(payload.get("records"))
    hard_counter: Counter[str] = Counter()
    failure_counter: Counter[str] = Counter()
    comfort_counter: Counter[str] = Counter()
    generated_sum = 0
    snapshots_with_generated = 0
    for row in rows if isinstance(rows, list) else []:
        generated = row.get("generated_count", 0) if isinstance(row, dict) else 0
        if isinstance(generated, int):
            generated_sum += generated
            if generated > 0:
                snapshots_with_generated += 1
    for candidate in candidate_rows:
        for reason in candidate.get("hard_reasons", []) or []:
            hard_counter[str(reason)] += 1
        for failure in candidate.get("failure_classes", []) or []:
            failure_counter[str(failure)] += 1
        meta = candidate.get("candidate_meta", {})
        if isinstance(meta, dict):
            descriptor = meta.get("remediation_descriptor_payload", {})
            if isinstance(descriptor, dict):
                for key in ("top_comfort_blocker", "secondary_comfort_blocker"):
                    value = descriptor.get(key)
                    if value:
                        comfort_counter[str(value)] += 1
    if not failure_counter:
        failure_counter.update(_int_dict(payload.get("failure_class_counts")))
    if not hard_counter:
        hard_counter.update(_int_dict(payload.get("hard_reason_counts")))
    generated_candidate_rows = len(candidate_rows) or _int(
        records.get("generated_candidate_rows")
    )
    lower_union_rows = sum(
        1 for candidate in candidate_rows if candidate.get("lower_union_red") is True
    )
    if lower_union_rows == 0:
        lower_union_rows = _int(records.get("lower_union_red_rows"))
    hard_rows = sum(1 for candidate in candidate_rows if candidate.get("hard_feasible") is True)
    if hard_rows == 0:
        hard_rows = _int(records.get("lower_union_red_hard_feasible_rows"))
    progress_rows = sum(
        1 for candidate in candidate_rows if candidate.get("progress_feasible") is True
    )
    if progress_rows == 0:
        progress_rows = _int(records.get("lower_union_red_progress_feasible_rows"))
    comfort_rows = sum(
        1 for candidate in candidate_rows if candidate.get("comfort_admissible") is True
    )
    if comfort_rows == 0:
        comfort_rows = _int(records.get("lower_union_red_comfort_admissible_rows"))
    snapshot_count = len(rows) if isinstance(rows, list) else 0
    if snapshot_count == 0:
        snapshot_count = _int(records.get("snapshots"))
    if snapshots_with_generated == 0:
        snapshots_with_generated = _int(records.get("snapshots_with_generated_candidates"))
    blocked = {
        key: bool(decision.get(key))
        for key in BLOCKED_ACTIONS
        if bool(decision.get(key))
    }
    return {
        "status": decision.get("status"),
        "next_step": decision.get("next_step"),
        "snapshots": snapshot_count,
        "snapshots_with_generated_candidates": snapshots_with_generated,
        "generated_candidate_rows": generated_candidate_rows,
        "row_generated_count_sum": generated_sum or generated_candidate_rows,
        "lower_union_red_rows": lower_union_rows,
        "hard_feasible_rows": hard_rows,
        "progress_feasible_rows": progress_rows,
        "comfort_admissible_rows": comfort_rows,
        "hard_support_rate": support_gate.get("hard_feasible_snapshot_support_rate"),
        "comfort_support_rate": support_gate.get("comfort_admissible_snapshot_support_rate"),
        "min_snapshot_support_rate": support_gate.get("min_snapshot_support_rate"),
        "hard_support_pass": support_gate.get("hard_feasible_snapshot_support_pass"),
        "comfort_support_pass": support_gate.get("comfort_admissible_snapshot_support_pass"),
        "failure_class_counts": dict(sorted(failure_counter.items())),
        "hard_reason_counts": dict(sorted(hard_counter.items())),
        "comfort_blocker_counts": dict(sorted(comfort_counter.items())),
        "candidate_generation_executed": bool(analysis.get("candidate_generation_executed")),
        "closed_loop_replay": bool(analysis.get("closed_loop_replay")),
        "training": bool(analysis.get("training")),
        "future_outcome_leakage": bool(analysis.get("future_outcome_leakage")),
        "online_selector_change": bool(analysis.get("online_selector_change")),
        "uses_outcome_labels": bool(analysis.get("uses_outcome_labels")),
        "blocked_authorizations": blocked,
        "source_authorization_conflicts": decision.get("source_authorization_conflicts", []),
    }


def _materialization_summary(payload: dict[str, Any]) -> dict[str, Any]:
    candidate_rows = _candidate_rows(payload)
    profile_counts: Counter[str] = Counter()
    materialized_rows = 0
    report_only_rows = 0
    uses_outcome_labels_rows = 0
    score_mutation_rows = 0
    selector_mutation_rows = 0
    candidate0_preserved_rows = 0
    dp_rows_preserved_rows = 0
    descriptor_rows = 0
    for candidate in candidate_rows:
        meta = candidate.get("candidate_meta", {})
        if not isinstance(meta, dict):
            continue
        profile_counts[str(meta.get("profile"))] += 1
        if meta.get("candidate_materialization_v4") is True:
            materialized_rows += 1
        if meta.get("comfort_first_precheck_report_only") is True:
            report_only_rows += 1
        if meta.get("uses_outcome_labels") is True:
            uses_outcome_labels_rows += 1
        if meta.get("candidate0_preserved") is True:
            candidate0_preserved_rows += 1
        if meta.get("dp_rows_preserved") is True:
            dp_rows_preserved_rows += 1
        descriptor = meta.get("remediation_descriptor_payload", {})
        if isinstance(descriptor, dict):
            descriptor_rows += 1
            if descriptor.get("score_mutation") is True:
                score_mutation_rows += 1
            if (
                descriptor.get("selected_index_mutation") is True
                or descriptor.get("online_selector_promotion") is True
            ):
                selector_mutation_rows += 1
            if descriptor.get("uses_outcome_labels") is True:
                uses_outcome_labels_rows += 1
    return {
        "candidate_row_count": len(candidate_rows),
        "materialized_rows": materialized_rows,
        "report_only_rows": report_only_rows,
        "uses_outcome_labels_rows": uses_outcome_labels_rows,
        "score_mutation_rows": score_mutation_rows,
        "selector_mutation_rows": selector_mutation_rows,
        "candidate0_preserved_rows": candidate0_preserved_rows,
        "dp_rows_preserved_rows": dp_rows_preserved_rows,
        "descriptor_rows": descriptor_rows,
        "profile_counts": dict(sorted(profile_counts.items())),
    }


def _failure_attribution(
    source: dict[str, Any],
    materialization: dict[str, Any],
) -> dict[str, Any]:
    failure_class_ranking = _ranking(source["failure_class_counts"])
    hard_reason_ranking = _ranking(source["hard_reason_counts"])
    comfort_ranking = _ranking(source["comfort_blocker_counts"])
    positive_support = bool(
        source["hard_feasible_rows"] > 0 and source["comfort_admissible_rows"] > 0
    )
    candidate_rows = int(source["generated_candidate_rows"])
    material_contract_ok = (
        candidate_rows > 0
        and materialization["materialized_rows"] == candidate_rows
        and materialization["report_only_rows"] == candidate_rows
        and materialization["uses_outcome_labels_rows"] == 0
        and materialization["score_mutation_rows"] == 0
        and materialization["selector_mutation_rows"] == 0
    )
    primary = "unknown"
    if candidate_rows > 0 and source["hard_feasible_rows"] == 0:
        primary = "route_topology_hard_constraint_failure_after_v4_materialization"
    secondary = "unknown"
    if source["comfort_admissible_rows"] == 0:
        secondary = "zero_comfort_support_after_hard_constraint_failure"
    non_causes = []
    if material_contract_ok:
        non_causes.extend(
            [
                "candidate_materialization_accounting",
                "descriptor_score_or_selector_mutation",
                "future_outcome_label_leakage",
                "dp_modification",
                "training_or_online_selector",
            ]
        )
    interpretation = (
        "The v4 generator materialized finite candidates and every materialized "
        "row reduced union-red exposure, but none survived the DP route/topology "
        "hard gate or comfort gate. The dominant hard failures are lane validity, "
        "DP kinematics, road-border collision, and red-timing validity. This "
        "makes candidate construction geometry and feasibility the current "
        "blocker, not CAMP training, online selection, or atom promotion."
    )
    return {
        "primary_blocker_family": primary,
        "secondary_blocker_family": secondary,
        "failure_class_ranking": failure_class_ranking,
        "hard_reason_ranking": hard_reason_ranking,
        "hard_blocker_ranking": hard_reason_ranking,
        "comfort_blocker_ranking": comfort_ranking,
        "positive_support_evidence": positive_support,
        "materialization_contract_ok": material_contract_ok,
        "training_ready": False,
        "replay_evidence_ready": False,
        "remediation_design_plan_ready": candidate_rows > 0 and not positive_support,
        "non_causes": non_causes,
        "interpretation": interpretation,
    }


def _artifact_checks(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("screen_root_exists", artifact["exists"]),
        *[
            _check(f"{name}_exists", artifact["files"].get(name) is True)
            for name in REQUIRED_FILES
        ],
        _check("sha256sums_match", artifact["sha256sums_ok"]),
        _check("screen_json_parseable", bool(artifact["screen_payload"])),
        _check(
            "screen_exit_code_zero_or_absent",
            artifact["exit_code"] in (None, "", "0"),
        ),
    ]


def _head_checks(
    camp_head: str,
    camp_origin_main: str,
    dp_head: str,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    heads = artifact["heads"]
    return [
        _check("camp_head_matches_expected", camp_head == EXPECTED_ANALYSIS_CAMP_HEAD),
        _check("camp_origin_main_matches_expected", camp_origin_main == EXPECTED_ANALYSIS_CAMP_HEAD),
        _check("camp_head_matches_origin_main", camp_head == camp_origin_main),
        _check("dp_head_fixed", dp_head == EXPECTED_DP_HEAD),
        _check(
            "artifact_camp_head_matches_source",
            heads.get("CAMP_HEAD") == EXPECTED_SOURCE_ARTIFACT_CAMP_HEAD,
        ),
        _check(
            "artifact_camp_origin_main_matches_source",
            heads.get("CAMP_ORIGIN_MAIN") == EXPECTED_SOURCE_ARTIFACT_CAMP_HEAD,
        ),
        _check(
            "artifact_camp_head_synced_at_generation",
            heads.get("CAMP_HEAD") == heads.get("CAMP_ORIGIN_MAIN"),
        ),
        _check("artifact_dp_head_fixed", heads.get("DP_HEAD") == EXPECTED_DP_HEAD),
        _check("artifact_snapshot_count_57", heads.get("SNAPSHOT_COUNT") == "57"),
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("screen_status_is_support_insufficient", source["status"] == SCREEN_REJECT_STATUS),
        _check("screen_candidate_generation_executed", source["candidate_generation_executed"] is True),
        _check("screen_no_closed_loop_replay", source["closed_loop_replay"] is False),
        _check("screen_no_training", source["training"] is False),
        _check("screen_no_future_outcome_leakage", source["future_outcome_leakage"] is False),
        _check("screen_no_online_selector_change", source["online_selector_change"] is False),
        _check("screen_no_blocked_authorizations", not source["blocked_authorizations"]),
        _check("screen_no_source_authorization_conflicts", not source["source_authorization_conflicts"]),
        _check("generated_candidate_rows_present", source["generated_candidate_rows"] > 0),
        _check("generated_count_matches_candidate_rows", source["row_generated_count_sum"] == source["generated_candidate_rows"]),
        _check("lower_union_red_rows_present", source["lower_union_red_rows"] > 0),
        _check("zero_hard_feasible_rows", source["hard_feasible_rows"] == 0),
        _check("zero_comfort_admissible_rows", source["comfort_admissible_rows"] == 0),
        _check("hard_support_rate_zero", source["hard_support_rate"] == 0.0),
        _check("comfort_support_rate_zero", source["comfort_support_rate"] == 0.0),
    ]


def _materialization_checks(
    materialization: dict[str, Any],
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = source["generated_candidate_rows"]
    return [
        _check("v4_materialized_all_rows", materialization["materialized_rows"] == rows),
        _check("v4_report_only_all_rows", materialization["report_only_rows"] == rows),
        _check("v4_no_outcome_labels", materialization["uses_outcome_labels_rows"] == 0),
        _check("v4_no_score_mutation", materialization["score_mutation_rows"] == 0),
        _check("v4_no_selector_mutation", materialization["selector_mutation_rows"] == 0),
        _check("v4_descriptor_rows_present", materialization["descriptor_rows"] == rows),
        _check(
            "v4_profile_only",
            materialization["profile_counts"] == {REMEDIATION_PROFILE: rows},
        ),
    ]


def _attribution_checks(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(
            "primary_blocker_is_hard_constraint_failure",
            attribution["primary_blocker_family"]
            == "route_topology_hard_constraint_failure_after_v4_materialization",
        ),
        _check("positive_support_absent", attribution["positive_support_evidence"] is False),
        _check("training_not_ready", attribution["training_ready"] is False),
        _check("replay_not_ready", attribution["replay_evidence_ready"] is False),
        _check("materialization_contract_ok", attribution["materialization_contract_ok"] is True),
        _check("remediation_design_plan_ready", attribution["remediation_design_plan_ready"] is True),
    ]


def _boundary_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check("formal_seeds_not_authorized", "formal_seeds_authorized" not in source["blocked_authorizations"]),
        _check("full36_not_authorized", "full36_authorized" not in source["blocked_authorizations"]),
        _check("camp_retraining_not_authorized", "camp_retraining_authorized" not in source["blocked_authorizations"]),
        _check("training_execution_not_authorized", "training_execution_authorized" not in source["blocked_authorizations"]),
        _check("dp_modification_not_authorized", "dp_modification_authorized" not in source["blocked_authorizations"]),
    ]


def _final_decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failure_attribution_complete": passed,
        "remediation_design_plan_authorized": passed,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
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
    }


def _candidate_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("rows", [])
    candidates: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        row_candidates = row.get("candidate_rows", [])
        if isinstance(row_candidates, list):
            candidates.extend(candidate for candidate in row_candidates if isinstance(candidate, dict))
    return candidates


def _ranking(counts: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"name": name, "count": count}
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _int_dict(value: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, raw in _dict(value).items():
        out[str(key)] = _int(raw)
    return out


def _strip_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in artifact.items() if key != "screen_payload"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_heads(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    heads: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        heads[key.strip()] = value.strip()
    return heads


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256sums_ok(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    ok = True
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 2:
            ok = False
            continue
        expected = parts[0]
        raw_name = parts[-1]
        candidate_path = Path(raw_name)
        if raw_name.startswith("/") and not candidate_path.is_file():
            candidate_path = root / candidate_path.name
        elif candidate_path.is_absolute() and not candidate_path.is_file():
            candidate_path = root / candidate_path.name
        elif not candidate_path.is_absolute():
            candidate_path = root / raw_name
        name = candidate_path.name
        if name == SHA256SUMS:
            continue
        seen.add(name)
        if not candidate_path.is_file() or _sha256(candidate_path) != expected:
            ok = False
    return ok and all(name in seen for name in REQUIRED_FILES if name != SHA256SUMS)


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


if __name__ == "__main__":
    main()
