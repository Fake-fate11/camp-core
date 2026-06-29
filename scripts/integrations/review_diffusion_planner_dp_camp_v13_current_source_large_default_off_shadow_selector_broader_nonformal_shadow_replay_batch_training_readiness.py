#!/usr/bin/env python3
"""Review fixed v13 shadow replay logs for static DP-reward training readiness.

This tool is read-only. It inspects an existing replay output directory and
execution artifact, validates the clean DP-native training-data contract, and
decides whether a later static CAMP retraining gate may consume the fixed logs.
It does not run replay, generate candidates, train CAMP, modify Diffusion
Planner, promote selectors/atoms, deploy, or make safety claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    validate_record,
)


SCHEMA_VERSION = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_training_readiness_v1"
)
READY_STATUS = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_training_readiness_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_training_readiness_rejected"
)
AUTHORIZED_REVIEW_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_result_review_and_training_readiness_"
    "preflight_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_static_dp_reward_training_execution_only"
)
LATEST_ALLOWED_STATUS = (
    "current_source_large_default_off_shadow_selector_broader_nonformal_"
    "shadow_replay_batch_execution_passed"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_ATOM_SCHEMA = "dp_camp_v10_14d"
EXPECTED_ATOM_COUNT = 14
EXPECTED_CANDIDATE_COUNT = 8
FORMAL_SEEDS = {11, 12, 13}
REQUIRED_STATIC_AUDIT_CHECKS = (
    "runbook_exit_zero",
    "selection_log_count_32",
    "validation_log_count_32",
    "records_total_3200",
    "summary_shadow_records_3200",
    "executed_indices_dp_top1",
    "selected_indices_dp_top1",
    "missing_shadow_payload_zero",
    "failed_shadow_records_zero",
    "reference_blend_disabled_all_records",
    "guidance_disabled_all_records",
    "candidate_closed_loop_outcomes_absent",
    "score_expression_affine_all_records",
    "candidate_operation_fixed_all_records",
    "executed_policy_dp_top1_all_records",
    "selection_effect_false_all_records",
)
BLOCKED_CLAIMS = (
    "training_executed",
    "candidate_generation_by_camp_executed",
    "trajectory_generation_by_camp_executed",
    "trajectory_modification_by_camp_executed",
    "dp_modified",
    "formal_seeds_executed",
    "selector_promoted",
    "atom_promoted",
    "deployed",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only review of a fixed v13 current-source-large default-off "
            "shadow replay batch for later static DP-reward CAMP training."
        )
    )
    parser.add_argument("--replay_output_dir", type=Path, required=True)
    parser.add_argument("--execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--expected_selection_log_count", type=int, default=32)
    parser.add_argument("--expected_validation_log_count", type=int, default=32)
    parser.add_argument("--expected_records", type=int, default=3200)
    parser.add_argument("--expected_candidate_count", type=int, default=EXPECTED_CANDIDATE_COUNT)
    parser.add_argument("--expected_atom_schema", default=EXPECTED_ATOM_SCHEMA)
    parser.add_argument("--expected_atom_count", type=int, default=EXPECTED_ATOM_COUNT)
    parser.add_argument("--min_routes", type=int, default=4)
    parser.add_argument("--min_seeds", type=int, default=2)
    parser.add_argument("--min_route_tl_buckets", type=int, default=8)
    parser.add_argument("--min_usable_feasible_records", type=int, default=100)
    parser.add_argument("--min_multi_feasible_records", type=int, default=100)
    parser.add_argument("--reward_key", default="quality_without_progress")
    parser.add_argument("--reward_progress_weight", type=float, default=2.0)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        replay_output_dir=args.replay_output_dir,
        execution_artifact_dir=args.execution_artifact_dir,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_validation_log_count=args.expected_validation_log_count,
        expected_records=args.expected_records,
        expected_candidate_count=args.expected_candidate_count,
        expected_atom_schema=args.expected_atom_schema,
        expected_atom_count=args.expected_atom_count,
        min_routes=args.min_routes,
        min_seeds=args.min_seeds,
        min_route_tl_buckets=args.min_route_tl_buckets,
        min_usable_feasible_records=args.min_usable_feasible_records,
        min_multi_feasible_records=args.min_multi_feasible_records,
        reward_key=args.reward_key,
        reward_progress_weight=args.reward_progress_weight,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    replay_output_dir: Path,
    execution_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    expected_selection_log_count: int = 32,
    expected_validation_log_count: int = 32,
    expected_records: int = 3200,
    expected_candidate_count: int = EXPECTED_CANDIDATE_COUNT,
    expected_atom_schema: str = EXPECTED_ATOM_SCHEMA,
    expected_atom_count: int = EXPECTED_ATOM_COUNT,
    min_routes: int = 4,
    min_seeds: int = 2,
    min_route_tl_buckets: int = 8,
    min_usable_feasible_records: int = 100,
    min_multi_feasible_records: int = 100,
    reward_key: str = "quality_without_progress",
    reward_progress_weight: float = 2.0,
) -> dict[str, Any]:
    replay_output_dir = replay_output_dir.resolve()
    execution_artifact_dir = execution_artifact_dir.resolve()
    static_audit_path = execution_artifact_dir / "static_batch_audit.json"
    manifest_path = execution_artifact_dir / "replay_output_hash_manifest.txt"
    selection_logs = sorted(replay_output_dir.rglob("camp_selection_log.json"))
    validation_logs = sorted(replay_output_dir.rglob("camp_validation_summary.json"))
    static_audit = _load_json_dict(static_audit_path)
    audit_text = _read_text(v13_audit_md)
    record_summary = _summarize_records(
        selection_logs=selection_logs,
        replay_output_dir=replay_output_dir,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
    )
    checks = _checks(
        replay_output_dir=replay_output_dir,
        execution_artifact_dir=execution_artifact_dir,
        static_audit_path=static_audit_path,
        manifest_path=manifest_path,
        v13_audit_md=v13_audit_md,
        audit_text=audit_text,
        static_audit=static_audit,
        record_summary=record_summary,
        selection_logs=selection_logs,
        validation_logs=validation_logs,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_selection_log_count=expected_selection_log_count,
        expected_validation_log_count=expected_validation_log_count,
        expected_records=expected_records,
        expected_candidate_count=expected_candidate_count,
        expected_atom_schema=expected_atom_schema,
        expected_atom_count=expected_atom_count,
        min_routes=min_routes,
        min_seeds=min_seeds,
        min_route_tl_buckets=min_route_tl_buckets,
        min_usable_feasible_records=min_usable_feasible_records,
        min_multi_feasible_records=min_multi_feasible_records,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "fixed_source_artifact_only": True,
            "mode": "static",
            "training_scope": "feasible_ranking",
            "label_source": "dp_reward",
            "reward_key": reward_key,
            "reward_progress_weight": reward_progress_weight,
            "score_expression": "score_k(w)=a_k^T w",
            "math_boundary": (
                "The reviewed training input is fixed DP candidate logs only. "
                "A later training gate may fit nonnegative simplex weights over "
                "the approved atom vector, preserving the affine score "
                "score_k(w)=a_k^T w and not changing the Benders master."
            ),
        },
        "source_paths": {
            "replay_output_dir": str(replay_output_dir),
            "execution_artifact_dir": str(execution_artifact_dir),
            "static_batch_audit_json": str(static_audit_path),
            "replay_output_hash_manifest": str(manifest_path),
            "v13_audit_md": str(v13_audit_md),
        },
        "source_hashes": {
            "static_batch_audit_json_sha256": (
                _sha256(static_audit_path) if static_audit_path.is_file() else None
            ),
            "replay_output_hash_manifest_sha256": (
                _sha256(manifest_path) if manifest_path.is_file() else None
            ),
            "v13_audit_md_sha256": _sha256(v13_audit_md) if v13_audit_md.is_file() else None,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "static_batch_audit_evidence": _static_audit_evidence(static_audit),
        "training_readiness": record_summary,
        "review_checks": checks,
        "final_decision": _decision(passed, failed),
    }


def _checks(
    *,
    replay_output_dir: Path,
    execution_artifact_dir: Path,
    static_audit_path: Path,
    manifest_path: Path,
    v13_audit_md: Path,
    audit_text: str,
    static_audit: dict[str, Any],
    record_summary: dict[str, Any],
    selection_logs: list[Path],
    validation_logs: list[Path],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_selection_log_count: int,
    expected_validation_log_count: int,
    expected_records: int,
    expected_candidate_count: int,
    expected_atom_schema: str,
    expected_atom_count: int,
    min_routes: int,
    min_seeds: int,
    min_route_tl_buckets: int,
    min_usable_feasible_records: int,
    min_multi_feasible_records: int,
) -> list[dict[str, Any]]:
    audit_checks = _dict(static_audit.get("checks"))
    blocked_claims = _dict(static_audit.get("blocked_claims"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("replay_output_dir_exists", replay_output_dir.is_dir(), str(replay_output_dir), "directory exists"),
        _check("execution_artifact_dir_exists", execution_artifact_dir.is_dir(), str(execution_artifact_dir), "directory exists"),
        _check("static_batch_audit_json_exists", static_audit_path.is_file(), str(static_audit_path), "file exists"),
        _check("replay_output_hash_manifest_exists", manifest_path.is_file(), str(manifest_path), "file exists"),
        _check("v13_audit_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("audit_latest_scope_allows_review", _latest_audit_value(audit_text, "next_work_target"), AUTHORIZED_REVIEW_WORK),
        _expect("audit_latest_status_allows_review", _latest_audit_value(audit_text, "current_v13_status"), LATEST_ALLOWED_STATUS),
        _expect("audit_latest_training_blocked", _latest_audit_value(audit_text, "training_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_latest_dp_modification_blocked", _latest_audit_value(audit_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("static_audit_passed", static_audit.get("passed"), True),
        _expect("static_audit_status", static_audit.get("status"), "passed"),
        _expect("static_audit_replay_output_dir", static_audit.get("replay_output_dir"), str(replay_output_dir)),
        _expect("static_audit_execution_artifact_dir", static_audit.get("execution_artifact_dir"), str(execution_artifact_dir)),
        _expect("selection_log_count", len(selection_logs), expected_selection_log_count),
        _expect("validation_log_count", len(validation_logs), expected_validation_log_count),
        _expect("records_total", record_summary["records_total"], expected_records),
        _expect("static_audit_records_total", static_audit.get("records_total"), expected_records),
        _expect("static_audit_summary_shadow_records", static_audit.get("summary_shadow_records"), expected_records),
        _expect("records_match_static_audit", record_summary["records_total"], static_audit.get("records_total")),
        _expect("selection_log_count_matches_static_audit", len(selection_logs), static_audit.get("selection_log_count")),
        _expect("validation_log_count_matches_static_audit", len(validation_logs), static_audit.get("validation_log_count")),
        _expect("candidate_count_values", record_summary["candidate_count_values"], {str(expected_candidate_count): expected_records}),
        _expect("atom_schema_versions", record_summary["atom_schema_versions"], {expected_atom_schema: expected_records}),
        _expect("atom_count_values", record_summary["atom_count_values"], {str(expected_atom_count): expected_records}),
        _check("routes_at_least_min", len(record_summary["route_records"]) >= min_routes, record_summary["route_records"], f">= {min_routes} routes"),
        _check("seeds_at_least_min", len(record_summary["seed_records"]) >= min_seeds, record_summary["seed_records"], f">= {min_seeds} seeds"),
        _check("route_tl_buckets_at_least_min", len(record_summary["route_tl_records"]) >= min_route_tl_buckets, record_summary["route_tl_records"], f">= {min_route_tl_buckets} route/tl buckets"),
        _check("formal_seeds_absent", not record_summary["formal_seed_records"], record_summary["formal_seed_records"], 0),
        _check("usable_feasible_records_at_least_min", record_summary["usable_feasible_records"] >= min_usable_feasible_records, record_summary["usable_feasible_records"], f">= {min_usable_feasible_records}"),
        _check("multi_feasible_records_at_least_min", record_summary["multi_feasible_records"] >= min_multi_feasible_records, record_summary["multi_feasible_records"], f">= {min_multi_feasible_records}"),
        _expect("records_available_after_static_dp_reward_drop", record_summary["records_available_for_static_dp_reward_training"], record_summary["usable_feasible_records"]),
        _expect("contract_failed_records_zero", record_summary["contract_failed_record_count"], 0),
        _expect("label_failed_records_zero", record_summary["label_failed_record_count"], 0),
        _expect("closed_loop_outcome_records_zero", record_summary["closed_loop_outcome_records"], 0),
        _expect("reference_blend_enabled_records_zero", record_summary["reference_blend_enabled_records"], 0),
        _expect("guidance_enabled_records_zero", record_summary["guidance_enabled_records"], 0),
        _expect("camp_candidate_generation_effect_records_zero", record_summary["camp_candidate_generation_effect_records"], 0),
        _expect("dp_modification_records_zero", record_summary["dp_modification_records"], 0),
        _expect("selected_index_counts", record_summary["selected_index_counts"], {"0": expected_records}),
        _expect("executed_index_counts", record_summary["executed_index_counts"], {"0": expected_records}),
        _check("shadow_selected_index_nonzero_present", record_summary["nonzero_shadow_selection_count"] > 0, record_summary["shadow_selected_index_counts"], "nonzero shadow selections"),
    ]
    for name in REQUIRED_STATIC_AUDIT_CHECKS:
        checks.append(_expect(f"static_audit_check:{name}", audit_checks.get(name), True))
    for name in BLOCKED_CLAIMS:
        checks.append(_expect(f"static_audit_blocked:{name}", blocked_claims.get(name), False))
    return checks


def _summarize_records(
    *,
    selection_logs: list[Path],
    replay_output_dir: Path,
    reward_key: str,
    reward_progress_weight: float,
) -> dict[str, Any]:
    records_total = 0
    usable_feasible_records = 0
    multi_feasible_records = 0
    all_infeasible_records = 0
    formal_seed_records = 0
    contract_failed: list[dict[str, Any]] = []
    label_failed: list[dict[str, Any]] = []
    route_records: Counter[str] = Counter()
    route_tl_records: Counter[str] = Counter()
    seed_records: Counter[str] = Counter()
    candidate_count_values: Counter[str] = Counter()
    atom_schema_versions: Counter[str] = Counter()
    atom_count_values: Counter[str] = Counter()
    feasible_count_distribution: Counter[str] = Counter()
    selected_index_counts: Counter[str] = Counter()
    executed_index_counts: Counter[str] = Counter()
    shadow_selected_index_counts: Counter[str] = Counter()
    closed_loop_outcome_records = 0
    reference_blend_enabled_records = 0
    guidance_enabled_records = 0
    camp_candidate_generation_effect_records = 0
    dp_modification_records = 0
    finite_quality_records = 0

    for log_path in selection_logs:
        rows = _load_json_list(log_path)
        meta = _metadata_from_log_path(log_path, replay_output_dir)
        for record_index, record in enumerate(rows):
            records_total += 1
            route_records[meta["route"]] += 1
            if meta["traffic_lights"]:
                route_tl_records[f"{meta['route']}|tl_{meta['traffic_lights']}"] += 1
            if meta["seed"] is not None:
                seed_records[str(meta["seed"])] += 1
                if int(meta["seed"]) in FORMAL_SEEDS:
                    formal_seed_records += 1

            atoms = record.get("atoms") if isinstance(record, dict) else None
            atom_names = record.get("atom_names") if isinstance(record, dict) else None
            candidate_count = len(atoms) if isinstance(atoms, list) else 0
            atom_count = len(atom_names) if isinstance(atom_names, list) else 0
            candidate_count_values[str(candidate_count)] += 1
            atom_count_values[str(atom_count)] += 1
            atom_schema_versions[str(record.get("atom_schema_version"))] += 1

            feasible_mask = record.get("feasible_mask")
            feasible_count = (
                sum(1 for value in feasible_mask if value is True)
                if isinstance(feasible_mask, list)
                else 0
            )
            feasible_count_distribution[str(feasible_count)] += 1
            if feasible_count:
                usable_feasible_records += 1
            if feasible_count >= 2:
                multi_feasible_records += 1
            if feasible_count == 0:
                all_infeasible_records += 1

            selected_index_counts[str(record.get("selected_index"))] += 1
            executed_index_counts[str(record.get("executed_index"))] += 1
            shadow_selected_index_counts[str(record.get("shadow_selected_index"))] += 1
            if record.get("candidate_closed_loop_outcomes") is not None:
                closed_loop_outcome_records += 1
            if record.get("candidate_reference_blend_steps") is not None:
                reference_blend_enabled_records += 1
            generation = _dict(record.get("candidate_generation_contract"))
            if bool(generation.get("guidance_enabled")):
                guidance_enabled_records += 1
            provenance = _dict(record.get("camp_candidate_tensor_provenance"))
            if bool(provenance.get("candidate_generation_effect")):
                camp_candidate_generation_effect_records += 1
            if bool(provenance.get("dp_modification_authorized")) or bool(
                generation.get("changes_diffusion_planner_weights")
            ):
                dp_modification_records += 1

            contract_errors = validate_record(record)
            if contract_errors:
                contract_failed.append(
                    {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "errors": sorted(set(contract_errors)),
                    }
                )
            label_errors, finite_quality = _dp_reward_errors(
                record,
                reward_key=reward_key,
                reward_progress_weight=reward_progress_weight,
            )
            if finite_quality:
                finite_quality_records += 1
            if label_errors:
                label_failed.append(
                    {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "errors": sorted(set(label_errors)),
                    }
                )

    return {
        "records_total": records_total,
        "selection_log_count": len(selection_logs),
        "records_available_for_static_dp_reward_training": usable_feasible_records,
        "records_dropped_without_feasible_candidate_by_static_training": all_infeasible_records,
        "usable_feasible_records": usable_feasible_records,
        "multi_feasible_records": multi_feasible_records,
        "all_infeasible_records": all_infeasible_records,
        "formal_seed_records": formal_seed_records,
        "route_records": dict(sorted(route_records.items())),
        "route_tl_records": dict(sorted(route_tl_records.items())),
        "seed_records": dict(sorted(seed_records.items())),
        "candidate_count_values": dict(sorted(candidate_count_values.items())),
        "atom_schema_versions": dict(sorted(atom_schema_versions.items())),
        "atom_count_values": dict(sorted(atom_count_values.items())),
        "feasible_count_distribution": dict(sorted(feasible_count_distribution.items())),
        "selected_index_counts": dict(sorted(selected_index_counts.items())),
        "executed_index_counts": dict(sorted(executed_index_counts.items())),
        "shadow_selected_index_counts": dict(sorted(shadow_selected_index_counts.items())),
        "nonzero_shadow_selection_count": sum(
            count
            for index, count in shadow_selected_index_counts.items()
            if index not in {"0", "None"}
        ),
        "closed_loop_outcome_records": closed_loop_outcome_records,
        "reference_blend_enabled_records": reference_blend_enabled_records,
        "guidance_enabled_records": guidance_enabled_records,
        "camp_candidate_generation_effect_records": camp_candidate_generation_effect_records,
        "dp_modification_records": dp_modification_records,
        "finite_quality_without_progress_records": finite_quality_records,
        "contract_failed_record_count": len(contract_failed),
        "label_failed_record_count": len(label_failed),
        "contract_failed_records": contract_failed[:20],
        "label_failed_records": label_failed[:20],
    }


def _dp_reward_errors(
    record: dict[str, Any],
    *,
    reward_key: str,
    reward_progress_weight: float,
) -> tuple[list[str], bool]:
    atoms = record.get("atoms")
    candidate_count = len(atoms) if isinstance(atoms, list) else 0
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list):
        return ["dp_candidate_rewards_missing"], False
    errors: list[str] = []
    if len(rewards) != candidate_count:
        errors.append("dp_candidate_rewards_candidate_count_mismatch")
    all_finite = True
    for index, reward in enumerate(rewards):
        if not isinstance(reward, dict):
            errors.append(f"dp_candidate_reward_{index}_not_object")
            all_finite = False
            continue
        if reward_key == "quality_without_progress":
            if "total" not in reward or "progress" not in reward:
                errors.append(f"dp_candidate_reward_{index}_missing_total_or_progress")
                all_finite = False
                continue
            value = float(reward["total"]) - float(reward_progress_weight) * float(
                reward["progress"]
            )
        elif reward_key in reward:
            value = float(reward[reward_key])
        else:
            errors.append(f"dp_candidate_reward_{index}_missing_{reward_key}")
            all_finite = False
            continue
        if not math.isfinite(value):
            errors.append(f"dp_candidate_reward_{index}_not_finite")
            all_finite = False
    return errors, all_finite and not errors


def _metadata_from_log_path(path: Path, root: Path) -> dict[str, Any]:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    route = parts[0] if len(parts) >= 1 else "unknown"
    seed: int | None = None
    traffic_lights: str | None = None
    for part in parts:
        if part.startswith("seed_"):
            try:
                seed = int(part.split("_", 1)[1])
            except ValueError:
                seed = None
        if part in {"tl_on", "tl_off"}:
            traffic_lights = part.split("_", 1)[1]
    return {"route": route, "seed": seed, "traffic_lights": traffic_lights}


def _static_audit_evidence(static_audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": static_audit.get("schema_version"),
        "status": static_audit.get("status"),
        "passed": static_audit.get("passed"),
        "selection_log_count": static_audit.get("selection_log_count"),
        "validation_log_count": static_audit.get("validation_log_count"),
        "records_total": static_audit.get("records_total"),
        "summary_shadow_records": static_audit.get("summary_shadow_records"),
        "executed_indices": static_audit.get("executed_indices"),
        "selected_indices": static_audit.get("selected_indices"),
        "shadow_selected_index_counts": static_audit.get("shadow_selected_index_counts"),
        "nonzero_shadow_selection_count_records": static_audit.get(
            "nonzero_shadow_selection_count_records"
        ),
        "route_records": static_audit.get("route_records"),
        "route_tl_records": static_audit.get("route_tl_records"),
        "failed_checks": static_audit.get("failed_checks"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    readiness = report["training_readiness"]
    lines = [
        "# V13 Current-Source Large Shadow Replay Batch Training Readiness",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{','.join(decision['failed_checks'])}`",
        f"- Records: `{readiness['records_total']}`",
        f"- Selection logs: `{readiness['selection_log_count']}`",
        f"- Usable feasible records: `{readiness['usable_feasible_records']}`",
        f"- Multi-feasible records: `{readiness['multi_feasible_records']}`",
        f"- Dropped by static DP-reward training: `{readiness['records_dropped_without_feasible_candidate_by_static_training']}`",
        f"- Nonzero shadow selections: `{readiness['nonzero_shadow_selection_count']}`",
        "",
        "This is a read-only training-readiness review. It does not run replay, "
        "generate candidates, train CAMP, modify DP, promote selectors/atoms, "
        "deploy, or authorize safety/CAMP-over-DP claims.",
        "",
        "## Coverage",
        "",
        "```json",
        json.dumps(
            {
                "route_records": readiness["route_records"],
                "route_tl_records": readiness["route_tl_records"],
                "seed_records": readiness["seed_records"],
                "feasible_count_distribution": readiness["feasible_count_distribution"],
                "shadow_selected_index_counts": readiness["shadow_selected_index_counts"],
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
    ]
    if readiness["contract_failed_records"] or readiness["label_failed_records"]:
        lines.extend(["## Failed Record Examples", ""])
        for row in readiness["contract_failed_records"]:
            lines.append(
                f"- `{row['log_path']}` record `{row['record_index']}`: "
                + ", ".join(f"`{error}`" for error in row["errors"])
            )
        for row in readiness["label_failed_records"]:
            lines.append(
                f"- `{row['log_path']}` record `{row['record_index']}` labels: "
                + ", ".join(f"`{error}`" for error in row["errors"])
            )
        lines.append("")
    return "\n".join(lines)


def _decision(passed: bool, failed_checks: list[str]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed_checks,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "static_dp_reward_training_execution_authorized_next": bool(passed),
        "training_executed": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "formal_seeds_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _load_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list) or not all(
        isinstance(row, dict) for row in loaded
    ):
        raise ValueError(f"{path} must contain a list of JSON objects.")
    return loaded


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _latest_audit_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in reversed(text.splitlines()):
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


if __name__ == "__main__":
    raise SystemExit(main())
