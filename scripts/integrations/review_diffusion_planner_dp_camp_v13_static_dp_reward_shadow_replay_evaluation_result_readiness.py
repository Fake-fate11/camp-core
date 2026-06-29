#!/usr/bin/env python3
"""Review fixed v13 static DP-reward shadow replay evaluation logs.

This tool is read-only. It consumes an existing evaluation output directory and
an existing execution audit, then decides whether the fixed logs are ready for
a later static DP-reward training preflight. It does not run replay, generate
candidates, train CAMP, modify Diffusion Planner, promote artifacts, deploy, or
make safety/CAMP-over-DP claims.
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
    validate_logs,
)


SCHEMA_VERSION = "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_v1"
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_"
    "ready_for_training_preflight"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_rejected"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_broader_"
    "nonformal_shadow_replay_batch_static_dp_reward_training_artifact_"
    "shadow_replay_evaluation_result_review_and_training_readiness_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_shadow_replay_eval_plus_prior_static_dp_reward_training_"
    "preflight_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
FORMAL_SEEDS = {11, 12, 13}
POSTSELECTION_FIELDS = (
    "perfect_tracker_command_postselection",
    "traffic_light_hybrid_postselection",
    "underprogress_relaxation",
    "splice_shadow_rule",
)
REQUIRED_EXECUTION_VIOLATION_ZERO_FIELDS = (
    "default_off_contract",
    "executed_index",
    "postselection",
    "reference_blend",
    "guidance",
    "closed_loop_outcomes",
    "atom_schema",
    "affine_score",
    "selection_score_mask",
    "shape",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only review of fixed v13 static DP-reward shadow replay "
            "evaluation logs for a later training-preflight gate."
        )
    )
    parser.add_argument("--evaluation_output_dir", type=Path, required=True)
    parser.add_argument("--execution_audit_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--previous_training_output_dir", type=Path, default=None)
    parser.add_argument("--expected_selection_log_count", type=int, default=32)
    parser.add_argument("--expected_records", type=int, default=3200)
    parser.add_argument("--expected_candidate_count", type=int, default=8)
    parser.add_argument("--expected_atom_count", type=int, default=14)
    parser.add_argument("--min_routes", type=int, default=4)
    parser.add_argument("--min_seeds", type=int, default=2)
    parser.add_argument("--min_route_tl_buckets", type=int, default=8)
    parser.add_argument("--min_usable_feasible_records", type=int, default=100)
    parser.add_argument("--min_multi_feasible_records", type=int, default=100)
    parser.add_argument("--max_previous_overlap_rate", type=float, default=0.0)
    parser.add_argument("--reward_key", default="quality_without_progress")
    parser.add_argument("--reward_progress_weight", type=float, default=2.0)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument(
        "--training_blocked_audit_key",
        default="camp_training_authorized_by_current_boundary",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        evaluation_output_dir=args.evaluation_output_dir,
        execution_audit_json=args.execution_audit_json,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        previous_training_output_dir=args.previous_training_output_dir,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_records=args.expected_records,
        expected_candidate_count=args.expected_candidate_count,
        expected_atom_count=args.expected_atom_count,
        min_routes=args.min_routes,
        min_seeds=args.min_seeds,
        min_route_tl_buckets=args.min_route_tl_buckets,
        min_usable_feasible_records=args.min_usable_feasible_records,
        min_multi_feasible_records=args.min_multi_feasible_records,
        max_previous_overlap_rate=args.max_previous_overlap_rate,
        reward_key=args.reward_key,
        reward_progress_weight=args.reward_progress_weight,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        training_blocked_audit_key=args.training_blocked_audit_key,
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
    evaluation_output_dir: Path,
    execution_audit_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    previous_training_output_dir: Path | None = None,
    expected_selection_log_count: int = 32,
    expected_records: int = 3200,
    expected_candidate_count: int = 8,
    expected_atom_count: int = 14,
    min_routes: int = 4,
    min_seeds: int = 2,
    min_route_tl_buckets: int = 8,
    min_usable_feasible_records: int = 100,
    min_multi_feasible_records: int = 100,
    max_previous_overlap_rate: float = 0.0,
    reward_key: str = "quality_without_progress",
    reward_progress_weight: float = 2.0,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    training_blocked_audit_key: str = "camp_training_authorized_by_current_boundary",
) -> dict[str, Any]:
    evaluation_output_dir = evaluation_output_dir.resolve()
    execution_audit_json = execution_audit_json.resolve()
    v13_audit_md = v13_audit_md.resolve()
    previous_training_output_dir = (
        previous_training_output_dir.resolve()
        if previous_training_output_dir is not None
        else None
    )
    selection_logs = sorted(evaluation_output_dir.rglob("camp_selection_log.json"))
    execution_audit = _load_json_dict(execution_audit_json)
    audit_text = _read_text(v13_audit_md)
    clean_contract = (
        validate_logs(selection_logs)
        if selection_logs
        else {
            "passed": False,
            "records": 0,
            "failed_records": [{"errors": ["selection_logs_missing"]}],
            "future_training_input_contract_satisfied": False,
        }
    )
    record_summary = _summarize_records(
        selection_logs=selection_logs,
        evaluation_output_dir=evaluation_output_dir,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
    )
    overlap = _compare_candidate_tensor_hashes(
        evaluation_output_dir=evaluation_output_dir,
        previous_training_output_dir=previous_training_output_dir,
    )
    checks = _checks(
        evaluation_output_dir=evaluation_output_dir,
        execution_audit_json=execution_audit_json,
        v13_audit_md=v13_audit_md,
        previous_training_output_dir=previous_training_output_dir,
        audit_text=audit_text,
        execution_audit=execution_audit,
        clean_contract=clean_contract,
        record_summary=record_summary,
        overlap=overlap,
        selection_logs=selection_logs,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        expected_selection_log_count=expected_selection_log_count,
        expected_records=expected_records,
        expected_candidate_count=expected_candidate_count,
        expected_atom_count=expected_atom_count,
        min_routes=min_routes,
        min_seeds=min_seeds,
        min_route_tl_buckets=min_route_tl_buckets,
        min_usable_feasible_records=min_usable_feasible_records,
        min_multi_feasible_records=min_multi_feasible_records,
        max_previous_overlap_rate=max_previous_overlap_rate,
        authorized_current_work=authorized_current_work,
        training_blocked_audit_key=training_blocked_audit_key,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "fixed_artifact_only": True,
            "mode": "static",
            "training_scope": "feasible_ranking",
            "label_source": "dp_reward",
            "reward_key": reward_key,
            "reward_progress_weight": reward_progress_weight,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "math_boundary": (
                "A later training gate may fit nonnegative simplex weights over "
                "the approved atom vector and keep scores affine as "
                "score_k(w)=a_k^T w. This review does not alter Benders, DP "
                "candidates, executed trajectories, or online selection."
            ),
            "training_executed": False,
            "replay_executed_by_this_review": False,
            "candidate_generation_executed_by_this_review": False,
            "dp_modified_by_this_review": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
        "source_paths": {
            "evaluation_output_dir": str(evaluation_output_dir),
            "execution_audit_json": str(execution_audit_json),
            "v13_audit_md": str(v13_audit_md),
            "previous_training_output_dir": (
                str(previous_training_output_dir)
                if previous_training_output_dir is not None
                else None
            ),
        },
        "source_hashes": {
            "execution_audit_json_sha256": (
                _sha256(execution_audit_json)
                if execution_audit_json.is_file()
                else None
            ),
            "v13_audit_md_sha256": _sha256(v13_audit_md)
            if v13_audit_md.is_file()
            else None,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "execution_audit_evidence": _execution_audit_evidence(execution_audit),
        "clean_contract": {
            "passed": bool(clean_contract.get("passed")),
            "records": int(clean_contract.get("records", 0)),
            "failed_records": int(len(clean_contract.get("failed_records", []))),
            "future_training_input_contract_satisfied": bool(
                clean_contract.get("future_training_input_contract_satisfied")
            ),
        },
        "training_readiness": record_summary,
        "candidate_tensor_overlap": overlap,
        "review_checks": checks,
        "final_decision": _decision(
            passed,
            failed,
            authorized_next_work=authorized_next_work,
        ),
    }


def _checks(
    *,
    evaluation_output_dir: Path,
    execution_audit_json: Path,
    v13_audit_md: Path,
    previous_training_output_dir: Path | None,
    audit_text: str,
    execution_audit: dict[str, Any],
    clean_contract: dict[str, Any],
    record_summary: dict[str, Any],
    overlap: dict[str, Any],
    selection_logs: list[Path],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    expected_selection_log_count: int,
    expected_records: int,
    expected_candidate_count: int,
    expected_atom_count: int,
    min_routes: int,
    min_seeds: int,
    min_route_tl_buckets: int,
    min_usable_feasible_records: int,
    min_multi_feasible_records: int,
    max_previous_overlap_rate: float,
    authorized_current_work: str,
    training_blocked_audit_key: str,
) -> list[dict[str, Any]]:
    decision = _dict(execution_audit.get("final_decision"))
    execution = _dict(execution_audit.get("execution"))
    records = _dict(execution_audit.get("records"))
    violation_counts = _dict(records.get("violation_counts"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("evaluation_output_dir_exists", evaluation_output_dir.is_dir(), str(evaluation_output_dir), "directory exists"),
        _check("execution_audit_json_exists", execution_audit_json.is_file(), str(execution_audit_json), "file exists"),
        _check("v13_audit_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _expect("audit_latest_next_work_target", _latest_audit_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_latest_training_blocked", _latest_audit_value(audit_text, training_blocked_audit_key), "False"),
        _expect("audit_latest_dp_modification_blocked", _latest_audit_value(audit_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_latest_formal_seeds_blocked", _latest_audit_value(audit_text, "formal_seed_11_12_13_execution_authorized"), "False"),
        _expect("execution_audit_passed", decision.get("passed"), True),
        _expect("execution_audit_authorized_current_work", decision.get("authorized_next_work"), authorized_current_work),
        _expect("execution_audit_result_review_authorized", decision.get("result_review_and_training_readiness_authorized_next"), True),
        _expect("execution_audit_training_not_performed", decision.get("training_performed_by_this_audit"), False),
        _expect("execution_audit_candidate_generation_not_performed", decision.get("candidate_generation_performed_by_this_audit"), False),
        _expect("execution_audit_replay_not_performed_by_audit", decision.get("replay_execution_performed_by_this_audit"), False),
        _expect("execution_audit_dp_not_modified", decision.get("dp_modification_authorized"), False),
        _expect("execution_audit_safety_claim_blocked", decision.get("safety_benefit_claim_authorized"), False),
        _expect("execution_audit_camp_over_dp_claim_blocked", decision.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("selection_log_count", len(selection_logs), expected_selection_log_count),
        _expect("records_total", record_summary["records_total"], expected_records),
        _expect("clean_contract_passed", clean_contract.get("passed"), True),
        _expect("clean_contract_records", clean_contract.get("records"), expected_records),
        _expect("clean_contract_failed_records_zero", len(clean_contract.get("failed_records", [])), 0),
        _expect("future_training_input_contract_satisfied", clean_contract.get("future_training_input_contract_satisfied"), True),
        _expect("candidate_count_values", record_summary["candidate_count_values"], {str(expected_candidate_count): expected_records}),
        _expect("atom_schema_versions", record_summary["atom_schema_versions"], {ATOM_SCHEMA_VERSION: expected_records}),
        _expect("atom_count_values", record_summary["atom_count_values"], {str(expected_atom_count): expected_records}),
        _check("routes_at_least_min", len(record_summary["route_records"]) >= min_routes, record_summary["route_records"], f">= {min_routes} routes"),
        _check("seeds_at_least_min", len(record_summary["seed_records"]) >= min_seeds, record_summary["seed_records"], f">= {min_seeds} seeds"),
        _check("route_tl_buckets_at_least_min", len(record_summary["route_tl_records"]) >= min_route_tl_buckets, record_summary["route_tl_records"], f">= {min_route_tl_buckets} route/tl buckets"),
        _expect("formal_seed_records_zero", record_summary["formal_seed_records"], 0),
        _check("usable_feasible_records_at_least_min", record_summary["usable_feasible_records"] >= min_usable_feasible_records, record_summary["usable_feasible_records"], f">= {min_usable_feasible_records}"),
        _check("multi_feasible_records_at_least_min", record_summary["multi_feasible_records"] >= min_multi_feasible_records, record_summary["multi_feasible_records"], f">= {min_multi_feasible_records}"),
        _expect("finite_reward_records", record_summary["finite_reward_records"], expected_records),
        _expect("closed_loop_outcome_records_zero", record_summary["closed_loop_outcome_records"], 0),
        _expect("reference_blend_enabled_records_zero", record_summary["reference_blend_enabled_records"], 0),
        _expect("guidance_enabled_records_zero", record_summary["guidance_enabled_records"], 0),
        _expect("postselection_records_zero", record_summary["postselection_records"], 0),
        _expect("camp_candidate_generation_effect_records_zero", record_summary["camp_candidate_generation_effect_records"], 0),
        _expect("dp_modification_records_zero", record_summary["dp_modification_records"], 0),
        _expect("default_off_shadow_selector_valid_records", record_summary["default_off_shadow_selector_valid_records"], expected_records),
        _expect("selected_index_counts", record_summary["selected_index_counts"], {"0": expected_records}),
        _expect("executed_index_counts", record_summary["executed_index_counts"], {"0": expected_records}),
        _check("shadow_differs_from_dp_top1_present", record_summary["shadow_differs_from_dp_top1_records"] > 0, record_summary["shadow_differs_from_dp_top1_records"], "> 0"),
        _expect("execution_audit_selection_log_count", execution.get("selection_log_count"), expected_selection_log_count),
        _expect("execution_audit_record_count", records.get("record_count"), expected_records),
        _expect("execution_audit_feasible_records_match", records.get("feasible_records"), record_summary["usable_feasible_records"]),
        _expect("execution_audit_used_fallback_records_match", records.get("used_fallback_records"), record_summary["all_infeasible_records"]),
        _expect("execution_audit_shadow_differs_match", records.get("shadow_differs_from_dp_top1_records"), record_summary["shadow_differs_from_dp_top1_records"]),
    ]
    for field in REQUIRED_EXECUTION_VIOLATION_ZERO_FIELDS:
        checks.append(_expect(f"execution_audit_violation_zero:{field}", violation_counts.get(field), 0))
    if previous_training_output_dir is not None:
        checks.extend(
            [
                _check("previous_training_output_dir_exists", previous_training_output_dir.is_dir(), str(previous_training_output_dir), "directory exists"),
                _expect("eval_candidate_tensor_hashes_complete", overlap["eval_hash_count"], expected_records),
                _check("previous_candidate_tensor_hashes_present", overlap["previous_hash_count"] > 0, overlap["previous_hash_count"], "> 0"),
                _check(
                    "candidate_tensor_overlap_rate_within_limit",
                    overlap["eval_hashes_in_previous_rate"] <= max_previous_overlap_rate,
                    overlap["eval_hashes_in_previous_rate"],
                    f"<= {max_previous_overlap_rate}",
                ),
            ]
        )
    return checks


def _summarize_records(
    *,
    selection_logs: list[Path],
    evaluation_output_dir: Path,
    reward_key: str,
    reward_progress_weight: float,
) -> dict[str, Any]:
    records_total = 0
    usable_feasible_records = 0
    multi_feasible_records = 0
    all_infeasible_records = 0
    formal_seed_records = 0
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
    postselection_records = 0
    camp_candidate_generation_effect_records = 0
    dp_modification_records = 0
    finite_reward_records = 0
    default_off_shadow_selector_valid_records = 0
    shadow_differs_from_dp_top1_records = 0

    for log_path in selection_logs:
        rows = _load_json_list(log_path)
        meta = _metadata_from_log_path(log_path, evaluation_output_dir)
        for record in rows:
            records_total += 1
            route_records[meta["route"]] += 1
            if meta["traffic_lights"]:
                route_tl_records[f"{meta['route']}|tl_{meta['traffic_lights']}"] += 1
            if meta["seed"] is not None:
                seed_records[str(meta["seed"])] += 1
                if int(meta["seed"]) in FORMAL_SEEDS:
                    formal_seed_records += 1

            atoms = record.get("atoms")
            atom_names = record.get("atom_names")
            candidate_count = _candidate_count(record)
            atom_count = len(atom_names) if isinstance(atom_names, list) else 0
            candidate_count_values[str(candidate_count)] += 1
            atom_schema_versions[str(record.get("atom_schema_version"))] += 1
            atom_count_values[str(atom_count)] += 1

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

            selected_index = record.get("selected_index")
            executed_index = record.get("executed_index")
            shadow_selected_index = record.get("shadow_selected_index")
            selected_index_counts[str(selected_index)] += 1
            executed_index_counts[str(executed_index)] += 1
            shadow_selected_index_counts[str(shadow_selected_index)] += 1
            if shadow_selected_index != executed_index:
                shadow_differs_from_dp_top1_records += 1

            if record.get("candidate_closed_loop_outcomes") is not None:
                closed_loop_outcome_records += 1
            if record.get("candidate_reference_blend_steps") is not None:
                reference_blend_enabled_records += 1
            if any(record.get(field) is not None for field in POSTSELECTION_FIELDS):
                postselection_records += 1
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

            if _default_off_shadow_selector_valid(record, candidate_count=candidate_count):
                default_off_shadow_selector_valid_records += 1
            if _record_has_finite_reward(
                record,
                candidate_count=candidate_count,
                reward_key=reward_key,
                reward_progress_weight=reward_progress_weight,
            ):
                finite_reward_records += 1

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
        "closed_loop_outcome_records": closed_loop_outcome_records,
        "reference_blend_enabled_records": reference_blend_enabled_records,
        "guidance_enabled_records": guidance_enabled_records,
        "postselection_records": postselection_records,
        "camp_candidate_generation_effect_records": camp_candidate_generation_effect_records,
        "dp_modification_records": dp_modification_records,
        "finite_reward_records": finite_reward_records,
        "default_off_shadow_selector_valid_records": default_off_shadow_selector_valid_records,
        "shadow_differs_from_dp_top1_records": shadow_differs_from_dp_top1_records,
    }


def _compare_candidate_tensor_hashes(
    *,
    evaluation_output_dir: Path,
    previous_training_output_dir: Path | None,
) -> dict[str, Any]:
    eval_hashes = _candidate_tensor_hashes(evaluation_output_dir)
    previous_hashes = (
        _candidate_tensor_hashes(previous_training_output_dir)
        if previous_training_output_dir is not None
        else []
    )
    previous_set = set(previous_hashes)
    overlap_count = sum(1 for value in eval_hashes if value in previous_set)
    eval_count = len(eval_hashes)
    eval_unique = len(set(eval_hashes))
    previous_unique = len(set(previous_hashes))
    intersection_unique = len(set(eval_hashes).intersection(previous_set))
    return {
        "previous_output_dir": (
            str(previous_training_output_dir)
            if previous_training_output_dir is not None
            else None
        ),
        "eval_hash_count": eval_count,
        "eval_unique_hash_count": eval_unique,
        "previous_hash_count": len(previous_hashes),
        "previous_unique_hash_count": previous_unique,
        "intersection_unique_hash_count": intersection_unique,
        "eval_hashes_in_previous_count": overlap_count,
        "eval_hashes_in_previous_rate": float(overlap_count / eval_count)
        if eval_count
        else 0.0,
        "unique_intersection_rate": float(intersection_unique / eval_unique)
        if eval_unique
        else 0.0,
    }


def _candidate_tensor_hashes(root: Path | None) -> list[str]:
    if root is None or not root.exists():
        return []
    hashes: list[str] = []
    for log_path in sorted(root.rglob("camp_selection_log.json")):
        for record in _load_json_list(log_path):
            value = _candidate_tensor_hash(record)
            if value is not None:
                hashes.append(value)
    return hashes


def _candidate_tensor_hash(record: dict[str, Any]) -> str | None:
    selector = _dict(record.get("default_off_shadow_selector"))
    tensor_hash = _dict(selector.get("candidate_tensor_hash"))
    value = tensor_hash.get("sha256")
    if _is_sha256(value):
        return value
    provenance = _dict(record.get("camp_candidate_tensor_provenance"))
    for key in ("post_camp_selector_tensor", "pre_camp_scoring_tensor"):
        value = _dict(provenance.get(key)).get("sha256")
        if _is_sha256(value):
            return value
    return None


def _default_off_shadow_selector_valid(
    record: dict[str, Any],
    *,
    candidate_count: int,
) -> bool:
    payload = _dict(record.get("default_off_shadow_selector"))
    tensor_hash = _dict(payload.get("candidate_tensor_hash"))
    expected = {
        "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "enabled": True,
        "default_off": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "score_expression": SCORE_EXPRESSION,
        "selection_effect": False,
        "online_selector_change": False,
        "artifact_contract_ready": True,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if payload.get("failed_closed_reason") is not None:
        return False
    if payload.get("executed_index") != record.get("executed_index"):
        return False
    if payload.get("executed_index") != 0 or record.get("selected_index") != 0:
        return False
    if payload.get("shadow_selected_index") != record.get("shadow_selected_index"):
        return False
    if not _is_sha256(tensor_hash.get("sha256")):
        return False
    return (
        tensor_hash.get("shape") == [candidate_count, 80, 4]
        and tensor_hash.get("dtype") == "float32"
        and tensor_hash.get("hash_input") == "contiguous_candidate_tensor_bytes"
        and tensor_hash.get("nan_policy") == "preserve_tensor_bytes"
    )


def _record_has_finite_reward(
    record: dict[str, Any],
    *,
    candidate_count: int,
    reward_key: str,
    reward_progress_weight: float,
) -> bool:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        return False
    for reward in rewards:
        if not isinstance(reward, dict):
            return False
        try:
            if reward_key == "quality_without_progress":
                value = float(reward["total"]) - reward_progress_weight * float(
                    reward["progress"]
                )
            else:
                value = float(reward[reward_key])
        except (KeyError, TypeError, ValueError):
            return False
        if not math.isfinite(value):
            return False
    return True


def _candidate_count(record: dict[str, Any]) -> int:
    value = record.get("num_candidates")
    if isinstance(value, int):
        return int(value)
    atoms = record.get("atoms")
    return len(atoms) if isinstance(atoms, list) else 0


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


def _execution_audit_evidence(execution_audit: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(execution_audit.get("final_decision"))
    execution = _dict(execution_audit.get("execution"))
    records = _dict(execution_audit.get("records"))
    return {
        "schema_version": execution_audit.get("schema_version"),
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selection_log_count": execution.get("selection_log_count"),
        "record_count": records.get("record_count"),
        "feasible_records": records.get("feasible_records"),
        "used_fallback_records": records.get("used_fallback_records"),
        "shadow_differs_from_dp_top1_records": records.get(
            "shadow_differs_from_dp_top1_records"
        ),
        "violation_counts": records.get("violation_counts"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    readiness = report["training_readiness"]
    overlap = report["candidate_tensor_overlap"]
    lines = [
        "# V13 Static DP-Reward Shadow Replay Evaluation Result Readiness",
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
        f"- Shadow differs from DP Top-1 records: `{readiness['shadow_differs_from_dp_top1_records']}`",
        f"- Eval hashes in previous training logs: `{overlap['eval_hashes_in_previous_count']}`",
        "",
        "This is a read-only result review. It does not run replay, generate "
        "candidates, train CAMP, modify DP, promote selectors/atoms, deploy, "
        "or authorize safety/CAMP-over-DP claims.",
        "",
        "## Coverage",
        "",
        "```json",
        json.dumps(
            {
                "route_records": readiness["route_records"],
                "route_tl_records": readiness["route_tl_records"],
                "seed_records": readiness["seed_records"],
                "feasible_count_distribution": readiness[
                    "feasible_count_distribution"
                ],
                "shadow_selected_index_counts": readiness[
                    "shadow_selected_index_counts"
                ],
                "candidate_tensor_overlap": overlap,
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
    ]
    return "\n".join(lines)


def _decision(
    passed: bool,
    failed_checks: list[str],
    *,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed_checks,
        "authorized_next_work": authorized_next_work if passed else None,
        "static_dp_reward_training_preflight_authorized_next": bool(passed),
        "static_dp_reward_training_execution_authorized_next": False,
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
    if not isinstance(loaded, list) or not all(isinstance(row, dict) for row in loaded):
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


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


if __name__ == "__main__":
    raise SystemExit(main())
