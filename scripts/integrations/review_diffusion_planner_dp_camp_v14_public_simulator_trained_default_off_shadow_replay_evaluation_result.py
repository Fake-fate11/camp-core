#!/usr/bin/env python3
"""Read-only v14 trained default-off shadow replay/evaluation result review.

This gate consumes an existing execution artifact and its existing selection
logs. It does not run replay, generate candidates, train CAMP, modify DP,
promote artifacts, deploy, or make safety/CAMP-over-DP claims.
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


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_trained_default_off_shadow_"
    "replay_evaluation_result_review_v1"
)
EXPECTED_CURRENT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_execution_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_result_review"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_decision_plan_only_after_explicit_"
    "user_authorization"
)
EXECUTION_CAMP_HEAD_AUDIT_KEY = (
    "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_camp_head"
)
EXECUTION_CAMP_ORIGIN_AUDIT_KEY = (
    "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_camp_origin_main"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_result_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_result_review_rejected"
)
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
DEFAULT_EXPECTED_SELECTION_LOG_COUNT = 32
DEFAULT_EXPECTED_RECORDS = 3200
DEFAULT_EXPECTED_RECORDS_PER_LOG = 100
DEFAULT_EXPECTED_VALIDATION_SUMMARY_COUNT = 32
DEFAULT_EXPECTED_REPLAY_SUMMARY_COUNT = 32
DEFAULT_EXPECTED_NUM_CANDIDATES = 8
FORMAL_SEED_MARKERS = (
    "seed11",
    "seed_11",
    "seed-11",
    "seed12",
    "seed_12",
    "seed-12",
    "seed13",
    "seed_13",
    "seed-13",
)
FORBIDDEN_PROVENANCE_FLAGS = (
    "generated_by_camp",
    "generation_by_camp",
    "modified_by_camp",
    "mutated_by_camp",
    "rewritten_by_camp",
    "trajectory_generation_by_camp",
    "trajectory_modification_by_camp",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--evaluation_output_dir", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument(
        "--expected_selection_log_count",
        type=int,
        default=DEFAULT_EXPECTED_SELECTION_LOG_COUNT,
    )
    parser.add_argument("--expected_records", type=int, default=DEFAULT_EXPECTED_RECORDS)
    parser.add_argument(
        "--expected_records_per_log",
        type=int,
        default=DEFAULT_EXPECTED_RECORDS_PER_LOG,
    )
    parser.add_argument(
        "--expected_validation_summary_count",
        type=int,
        default=DEFAULT_EXPECTED_VALIDATION_SUMMARY_COUNT,
    )
    parser.add_argument(
        "--expected_replay_summary_count",
        type=int,
        default=DEFAULT_EXPECTED_REPLAY_SUMMARY_COUNT,
    )
    parser.add_argument(
        "--expected_num_candidates",
        type=int,
        default=DEFAULT_EXPECTED_NUM_CANDIDATES,
    )
    parser.add_argument("--expected_atom_schema_version", default=ATOM_SCHEMA_VERSION)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        execution_artifact_dir=args.execution_artifact_dir,
        evaluation_output_dir=args.evaluation_output_dir,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        expected_selection_log_count=args.expected_selection_log_count,
        expected_records=args.expected_records,
        expected_records_per_log=args.expected_records_per_log,
        expected_validation_summary_count=args.expected_validation_summary_count,
        expected_replay_summary_count=args.expected_replay_summary_count,
        expected_num_candidates=args.expected_num_candidates,
        expected_atom_schema_version=args.expected_atom_schema_version,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    execution_artifact_dir: Path,
    evaluation_output_dir: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    expected_selection_log_count: int = DEFAULT_EXPECTED_SELECTION_LOG_COUNT,
    expected_records: int = DEFAULT_EXPECTED_RECORDS,
    expected_records_per_log: int = DEFAULT_EXPECTED_RECORDS_PER_LOG,
    expected_validation_summary_count: int = DEFAULT_EXPECTED_VALIDATION_SUMMARY_COUNT,
    expected_replay_summary_count: int = DEFAULT_EXPECTED_REPLAY_SUMMARY_COUNT,
    expected_num_candidates: int = DEFAULT_EXPECTED_NUM_CANDIDATES,
    expected_atom_schema_version: str = ATOM_SCHEMA_VERSION,
) -> dict[str, Any]:
    execution_artifact_dir = execution_artifact_dir.resolve()
    evaluation_output_dir = evaluation_output_dir.resolve()
    output_dir = output_dir.resolve()
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    heads = _parse_key_values(_read_text(execution_artifact_dir / "HEADS"))
    sha256s = _read_sha256sums(execution_artifact_dir / "SHA256SUMS")
    execution_exit = _read_text(execution_artifact_dir / "exit.code").strip()
    selection_logs = sorted(evaluation_output_dir.rglob("camp_selection_log.json"))
    validation_summaries = sorted(evaluation_output_dir.rglob("*validation*summary*.json"))
    replay_summaries = sorted(evaluation_output_dir.rglob("*replay*summary*.json"))
    record_summary = _summarize_selection_logs(
        selection_logs=selection_logs,
        expected_num_candidates=expected_num_candidates,
        expected_atom_schema_version=expected_atom_schema_version,
    )
    checks = _checks(
        execution_artifact_dir=execution_artifact_dir,
        evaluation_output_dir=evaluation_output_dir,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        sha256s=sha256s,
        execution_exit=execution_exit,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        selection_log_count=len(selection_logs),
        validation_summary_count=len(validation_summaries),
        replay_summary_count=len(replay_summaries),
        record_summary=record_summary,
        expected_selection_log_count=expected_selection_log_count,
        expected_records=expected_records,
        expected_records_per_log=expected_records_per_log,
        expected_validation_summary_count=expected_validation_summary_count,
        expected_replay_summary_count=expected_replay_summary_count,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "result_review_only": True,
            "replay_executed_by_source": True,
            "replay_executed_by_review": False,
            "candidate_generation_executed_by_review": False,
            "training_executed_by_review": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "dp_modification": False,
            "online_selector_change": False,
            "executed_trajectory_change": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "deployable_checkpoint_claim": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "inputs": {
            "execution_artifact_dir": str(execution_artifact_dir),
            "evaluation_output_dir": str(evaluation_output_dir),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "artifact_camp_head": heads.get("CAMP_HEAD"),
            "artifact_camp_origin_main": heads.get("CAMP_ORIGIN_MAIN"),
            "artifact_dp_head": heads.get("DP_HEAD"),
        },
        "artifact_hashes": sha256s,
        "execution": {
            "execution_exit": execution_exit,
            "selection_log_count": len(selection_logs),
            "validation_summary_count": len(validation_summaries),
            "replay_summary_count": len(replay_summaries),
        },
        "records": record_summary,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "result_review_report.json", report)
    (output_dir / "result_review_report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    records = report["records"]
    return "\n".join(
        [
            "# V14 Trained Default-Off Shadow Replay/Evaluation Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Selection logs: `{report['execution']['selection_log_count']}`",
            f"- Records: `{records['records_total']}`",
            f"- Shadow non-Top-1 records: `{records['shadow_selected_index_nonzero_records']}`",
            f"- Executed DP Top-1 records: `{records['executed_top1_records']}`",
            f"- Selection-effect true count: `{records['selection_effect_true_count']}`",
            f"- Online-selector-change true count: `{records['online_change_true_count']}`",
            f"- Formal seed path count: `{records['formal_seed_path_count']}`",
            "",
            "This is a read-only result review. It does not run replay, generate "
            "candidates, train CAMP, modify DP, promote, deploy, or make "
            "safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _summarize_selection_logs(
    *,
    selection_logs: list[Path],
    expected_num_candidates: int,
    expected_atom_schema_version: str,
) -> dict[str, Any]:
    records_total = 0
    records_per_log: list[int] = []
    counters: Counter[str] = Counter()
    atom_schema_versions: Counter[str] = Counter()
    candidate_counts: Counter[int] = Counter()
    weights_sums: Counter[float] = Counter()
    provenance_schema_versions: Counter[str] = Counter()
    failed_closed_reasons: Counter[str] = Counter()
    selected_indices: Counter[str] = Counter()
    shadow_selected_indices: Counter[str] = Counter()
    executed_indices: Counter[str] = Counter()
    route_buckets: set[str] = set()
    seed_buckets: set[str] = set()

    for log_path in selection_logs:
        path_text = " ".join(log_path.parts).lower()
        if any(marker in path_text for marker in FORMAL_SEED_MARKERS):
            counters["formal_seed_path_count"] += 1
        route_buckets.add(_route_bucket(log_path))
        seed = _seed_bucket(log_path)
        if seed:
            seed_buckets.add(seed)
        records = _records_from_log(log_path)
        records_total += len(records)
        records_per_log.append(len(records))
        for record in records:
            if not isinstance(record, dict):
                counters["non_object_records"] += 1
                continue
            _summarize_record(
                record=record,
                counters=counters,
                atom_schema_versions=atom_schema_versions,
                candidate_counts=candidate_counts,
                weights_sums=weights_sums,
                provenance_schema_versions=provenance_schema_versions,
                failed_closed_reasons=failed_closed_reasons,
                selected_indices=selected_indices,
                shadow_selected_indices=shadow_selected_indices,
                executed_indices=executed_indices,
                expected_num_candidates=expected_num_candidates,
                expected_atom_schema_version=expected_atom_schema_version,
            )

    return {
        "records_total": records_total,
        "records_per_log_min": min(records_per_log) if records_per_log else 0,
        "records_per_log_max": max(records_per_log) if records_per_log else 0,
        "route_count": len(route_buckets),
        "seed_count": len(seed_buckets),
        "selected_index_counts": dict(sorted(selected_indices.items())),
        "shadow_selected_index_counts": dict(sorted(shadow_selected_indices.items())),
        "executed_index_counts": dict(sorted(executed_indices.items())),
        "atom_schema_versions": dict(sorted(atom_schema_versions.items())),
        "candidate_counts": {str(k): v for k, v in sorted(candidate_counts.items())},
        "weights_sums": {str(k): v for k, v in sorted(weights_sums.items())},
        "camp_candidate_tensor_provenance_schema_versions": dict(
            sorted(provenance_schema_versions.items())
        ),
        "failed_closed_reasons": dict(sorted(failed_closed_reasons.items())),
        "non_object_records": counters["non_object_records"],
        "selected_index_matches_executed_index_records": counters[
            "selected_index_matches_executed_index_records"
        ],
        "selected_index_differs_from_executed_index_records": counters[
            "selected_index_differs_from_executed_index_records"
        ],
        "shadow_selected_index_nonzero_records": counters[
            "shadow_selected_index_nonzero_records"
        ],
        "shadow_selected_index_differs_from_executed_index_records": counters[
            "shadow_selected_index_differs_from_executed_index_records"
        ],
        "executed_top1_records": counters["executed_top1_records"],
        "default_off_selector_records": counters["default_off_selector_records"],
        "artifact_contract_ready_records": counters["artifact_contract_ready_records"],
        "selection_effect_true_count": counters["selection_effect_true_count"],
        "online_change_true_count": counters["online_change_true_count"],
        "policy_non_top1_count": counters["policy_non_top1_count"],
        "score_bad_count": counters["score_bad_count"],
        "operation_bad_count": counters["operation_bad_count"],
        "candidate_reference_blend_steps_nonzero": counters[
            "candidate_reference_blend_steps_nonzero"
        ],
        "candidate_closed_loop_outcome_weights_nonzero": counters[
            "candidate_closed_loop_outcome_weights_nonzero"
        ],
        "candidate_closed_loop_outcomes_nonzero": counters[
            "candidate_closed_loop_outcomes_nonzero"
        ],
        "splice_shadow_rule_active": counters["splice_shadow_rule_active"],
        "underprogress_relaxation_active": counters["underprogress_relaxation_active"],
        "perfect_tracker_command_postselection_active": counters[
            "perfect_tracker_command_postselection_active"
        ],
        "traffic_light_hybrid_postselection_active": counters[
            "traffic_light_hybrid_postselection_active"
        ],
        "used_fallback_count": counters["used_fallback_count"],
        "formal_seed_path_count": counters["formal_seed_path_count"],
        "camp_provenance_forbidden_effect_count": counters[
            "camp_provenance_forbidden_effect_count"
        ],
        "weights_bad_count": counters["weights_bad_count"],
        "atom_schema_bad_count": counters["atom_schema_bad_count"],
        "candidate_count_bad_count": counters["candidate_count_bad_count"],
    }


def _summarize_record(
    *,
    record: dict[str, Any],
    counters: Counter[str],
    atom_schema_versions: Counter[str],
    candidate_counts: Counter[int],
    weights_sums: Counter[float],
    provenance_schema_versions: Counter[str],
    failed_closed_reasons: Counter[str],
    selected_indices: Counter[str],
    shadow_selected_indices: Counter[str],
    executed_indices: Counter[str],
    expected_num_candidates: int,
    expected_atom_schema_version: str,
) -> None:
    selector = _dict(record.get("default_off_shadow_selector"))
    if selector:
        counters["default_off_selector_records"] += 1
    if selector.get("artifact_contract_ready") is True:
        counters["artifact_contract_ready_records"] += 1
    if _is_true(selector.get("selection_effect")):
        counters["selection_effect_true_count"] += 1
    if _is_true(selector.get("online_selector_change")):
        counters["online_change_true_count"] += 1
    if selector.get("executed_output_policy") != "dp_top1":
        counters["policy_non_top1_count"] += 1
    if selector.get("score_expression") != SCORE_EXPRESSION:
        counters["score_bad_count"] += 1
    if selector.get("candidate_operation") != "fixed DP candidate reranking only":
        counters["operation_bad_count"] += 1
    reason = selector.get("failed_closed_reason")
    if isinstance(reason, str) and reason:
        failed_closed_reasons[reason] += 1

    selected = record.get("selected_index")
    shadow = record.get("shadow_selected_index")
    executed = record.get("executed_index")
    if "shadow_selected_index" in selector:
        shadow = selector.get("shadow_selected_index")
    if "executed_index" in selector:
        executed = selector.get("executed_index")
    selected_indices[str(selected)] += 1
    shadow_selected_indices[str(shadow)] += 1
    executed_indices[str(executed)] += 1
    if _int_or_none(selected) == _int_or_none(executed):
        counters["selected_index_matches_executed_index_records"] += 1
    else:
        counters["selected_index_differs_from_executed_index_records"] += 1
    if _int_or_none(shadow) not in (None, 0):
        counters["shadow_selected_index_nonzero_records"] += 1
    if _int_or_none(shadow) != _int_or_none(executed):
        counters["shadow_selected_index_differs_from_executed_index_records"] += 1
    if _int_or_none(executed) == 0:
        counters["executed_top1_records"] += 1

    if _flat_nonzero(record.get("candidate_reference_blend_steps")):
        counters["candidate_reference_blend_steps_nonzero"] += 1
    if _flat_nonzero(record.get("candidate_closed_loop_outcome_weights")):
        counters["candidate_closed_loop_outcome_weights_nonzero"] += 1
    if _flat_nonzero(record.get("candidate_closed_loop_outcomes")):
        counters["candidate_closed_loop_outcomes_nonzero"] += 1
    if _active(record.get("splice_shadow_rule")):
        counters["splice_shadow_rule_active"] += 1
    if _active(record.get("underprogress_relaxation")):
        counters["underprogress_relaxation_active"] += 1
    if _active(record.get("perfect_tracker_command_postselection")):
        counters["perfect_tracker_command_postselection_active"] += 1
    if _active(record.get("traffic_light_hybrid_postselection")):
        counters["traffic_light_hybrid_postselection_active"] += 1
    if _is_true(record.get("used_fallback")):
        counters["used_fallback_count"] += 1

    atom_schema = record.get("atom_schema_version")
    if isinstance(atom_schema, str):
        atom_schema_versions[atom_schema] += 1
    if atom_schema != expected_atom_schema_version:
        counters["atom_schema_bad_count"] += 1
    num_candidates = record.get("num_candidates")
    if isinstance(num_candidates, int):
        candidate_counts[num_candidates] += 1
    if num_candidates != expected_num_candidates:
        counters["candidate_count_bad_count"] += 1
    weights = record.get("weights")
    if isinstance(weights, list):
        weight_sum = _safe_weight_sum(weights)
        weights_sums[round(weight_sum, 12)] += 1
        if (
            not math.isfinite(weight_sum)
            or abs(weight_sum - 1.0) > 1e-9
            or any(_safe_float(value) < -1e-12 for value in weights)
        ):
            counters["weights_bad_count"] += 1
    else:
        counters["weights_bad_count"] += 1

    provenance = _dict(record.get("camp_candidate_tensor_provenance"))
    schema_version = provenance.get("schema_version")
    if isinstance(schema_version, str):
        provenance_schema_versions[schema_version] += 1
    for flag in FORBIDDEN_PROVENANCE_FLAGS:
        if _is_true(provenance.get(flag)):
            counters["camp_provenance_forbidden_effect_count"] += 1


def _checks(
    *,
    execution_artifact_dir: Path,
    evaluation_output_dir: Path,
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    sha256s: dict[str, str],
    execution_exit: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    selection_log_count: int,
    validation_summary_count: int,
    replay_summary_count: int,
    record_summary: dict[str, Any],
    expected_selection_log_count: int,
    expected_records: int,
    expected_records_per_log: int,
    expected_validation_summary_count: int,
    expected_replay_summary_count: int,
) -> list[dict[str, Any]]:
    return [
        _check("execution_artifact_dir_exists", execution_artifact_dir.is_dir(), str(execution_artifact_dir), "directory"),
        _check("evaluation_output_dir_exists", evaluation_output_dir.is_dir(), str(evaluation_output_dir), "directory"),
        _expect("execution_exit_zero", execution_exit, "0"),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("artifact_dp_head_fixed", heads.get("DP_HEAD"), required_dp_head),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect(
            "artifact_camp_head_matches_audit_execution_head",
            heads.get("CAMP_HEAD"),
            _latest_value(v14_text, EXECUTION_CAMP_HEAD_AUDIT_KEY) or current_camp_head,
        ),
        _expect(
            "artifact_camp_origin_matches_audit_execution_origin",
            heads.get("CAMP_ORIGIN_MAIN"),
            _latest_value(v14_text, EXECUTION_CAMP_ORIGIN_AUDIT_KEY)
            or current_camp_origin_main,
        ),
        _expect(
            "audit_latest_status",
            _latest_value(v14_text, "current_v14_status"),
            EXPECTED_CURRENT_STATUS,
        ),
        _expect(
            "audit_latest_next_work",
            _latest_value(v14_text, "next_work_target"),
            authorized_current_work,
        ),
        _check(
            "status_doc_mentions_current_status",
            EXPECTED_CURRENT_STATUS in status_text,
            EXPECTED_CURRENT_STATUS in status_text,
            True,
        ),
        _check(
            "status_doc_mentions_current_work",
            authorized_current_work in status_text,
            authorized_current_work in status_text,
            True,
        ),
        _expect(
            "selection_log_count",
            selection_log_count,
            expected_selection_log_count,
        ),
        _expect(
            "validation_summary_count",
            validation_summary_count,
            expected_validation_summary_count,
        ),
        _expect(
            "replay_summary_count",
            replay_summary_count,
            expected_replay_summary_count,
        ),
        _expect("records_total", record_summary["records_total"], expected_records),
        _expect(
            "records_per_log_min",
            record_summary["records_per_log_min"],
            expected_records_per_log,
        ),
        _expect(
            "records_per_log_max",
            record_summary["records_per_log_max"],
            expected_records_per_log,
        ),
        _expect("non_object_records", record_summary["non_object_records"], 0),
        _expect(
            "selected_index_matches_executed_index_all_records",
            record_summary["selected_index_matches_executed_index_records"],
            expected_records,
        ),
        _expect("executed_top1_all_records", record_summary["executed_top1_records"], expected_records),
        _expect("default_off_selector_all_records", record_summary["default_off_selector_records"], expected_records),
        _expect("artifact_contract_ready_all_records", record_summary["artifact_contract_ready_records"], expected_records),
        _expect("selection_effect_true_zero", record_summary["selection_effect_true_count"], 0),
        _expect("online_change_true_zero", record_summary["online_change_true_count"], 0),
        _expect("policy_non_top1_zero", record_summary["policy_non_top1_count"], 0),
        _expect("score_bad_zero", record_summary["score_bad_count"], 0),
        _expect("operation_bad_zero", record_summary["operation_bad_count"], 0),
        _expect(
            "candidate_reference_blend_steps_nonzero_zero",
            record_summary["candidate_reference_blend_steps_nonzero"],
            0,
        ),
        _expect(
            "candidate_closed_loop_outcome_weights_nonzero_zero",
            record_summary["candidate_closed_loop_outcome_weights_nonzero"],
            0,
        ),
        _expect(
            "candidate_closed_loop_outcomes_nonzero_zero",
            record_summary["candidate_closed_loop_outcomes_nonzero"],
            0,
        ),
        _expect("splice_shadow_rule_active_zero", record_summary["splice_shadow_rule_active"], 0),
        _expect(
            "underprogress_relaxation_active_zero",
            record_summary["underprogress_relaxation_active"],
            0,
        ),
        _expect(
            "perfect_tracker_command_postselection_active_zero",
            record_summary["perfect_tracker_command_postselection_active"],
            0,
        ),
        _expect(
            "traffic_light_hybrid_postselection_active_zero",
            record_summary["traffic_light_hybrid_postselection_active"],
            0,
        ),
        _expect("formal_seed_path_count_zero", record_summary["formal_seed_path_count"], 0),
        _expect(
            "camp_provenance_forbidden_effect_zero",
            record_summary["camp_provenance_forbidden_effect_count"],
            0,
        ),
        _expect("weights_bad_zero", record_summary["weights_bad_count"], 0),
        _expect("atom_schema_bad_zero", record_summary["atom_schema_bad_count"], 0),
        _expect("candidate_count_bad_zero", record_summary["candidate_count_bad_count"], 0),
        _check("sha256sums_present", bool(sha256s), sorted(sha256s), "non-empty"),
        _check(
            "stdout_hash_recorded",
            "stdout.log" in sha256s,
            sorted(sha256s),
            "stdout.log",
        ),
        _check(
            "stderr_hash_recorded",
            "stderr.log" in sha256s,
            sorted(sha256s),
            "stderr.log",
        ),
    ]


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": sorted(failed),
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "result_review_complete": bool(passed),
        "promotion_decision_plan_authorized_next": bool(passed),
        "replay_executed_by_source": True,
        "replay_executed_by_review": False,
        "candidate_generation_executed_by_review": False,
        "training_executed_by_review": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
    }


def _failure_class(failed: list[str]) -> str:
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    if any("count" in check or "records" in check or "summary" in check for check in failed):
        return "execution_result_shape_or_count_contract_failure"
    default_off_markers = (
        "top1",
        "selection",
        "online",
        "postselection",
        "closed_loop",
        "blend",
        "provenance",
        "score",
        "operation",
    )
    if any(any(marker in check for marker in default_off_markers) for check in failed):
        return "default_off_shadow_contract_failure"
    return "result_review_contract_failure"


def _records_from_log(log_path: Path) -> list[Any]:
    try:
        loaded = json.loads(log_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(loaded, list):
        return loaded
    if isinstance(loaded, dict):
        for key in ("records", "steps", "selection_records", "log"):
            value = loaded.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                return list(value.values())
        return [loaded]
    return []


def _route_bucket(path: Path) -> str:
    parts = list(path.parts)
    if len(parts) >= 5:
        return "/".join(parts[-5:-3])
    return str(path.parent)


def _seed_bucket(path: Path) -> str | None:
    for part in path.parts:
        if part.startswith("seed_") or part.startswith("seed-"):
            return part
    return None


def _read_sha256sums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        parts = line.split()
        if len(parts) >= 2:
            result[parts[-1]] = parts[0]
    return result


def _parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    values = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    return values[-1] if values else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_true(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.lower() == "true")


def _active(value: Any) -> bool:
    return _is_true(value) or _flat_nonzero(value)


def _flat_nonzero(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return math.isfinite(float(value)) and abs(float(value)) > 1e-12
    if isinstance(value, list):
        return any(_flat_nonzero(item) for item in value)
    if isinstance(value, dict):
        return any(_flat_nonzero(item) for item in value.values())
    return False


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _safe_weight_sum(weights: list[Any]) -> float:
    values = [_safe_float(weight) for weight in weights]
    if not all(math.isfinite(value) for value in values):
        return math.nan
    return float(sum(values))


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    lines = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": observed,
        "expected": expected,
    }


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


if __name__ == "__main__":
    raise SystemExit(main())
