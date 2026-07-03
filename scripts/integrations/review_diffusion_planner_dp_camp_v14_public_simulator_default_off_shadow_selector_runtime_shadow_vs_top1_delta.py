#!/usr/bin/env python3
"""Read-only v14 shadow-selected versus DP Top-1 delta review.

This gate consumes existing runtime shadow replay selection logs and the
already-passed runtime shadow replay result review. It does not run replay,
generate candidates, train CAMP, modify Diffusion Planner, promote artifacts,
deploy, or make safety/CAMP-over-DP claims.

The only positive claim this script can support is narrower: under the logged
masked CAMP selection objective for the fixed DP candidate tensor, the
default-off shadow-selected candidate is no worse than the executed DP Top-1
candidate. That is a static objective delta, not an outcome or safety proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_shadow_vs_top1_delta_review_v1"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CURRENT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_passed"
)
EXPECTED_CURRENT_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_promotion_decision_plan_only_after_explicit_"
    "user_authorization"
)
AUTHORIZED_INSERTED_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_vs_top1_delta_review_only_after_explicit_user_authorization"
)
AUTHORIZED_NEXT_WORK = EXPECTED_CURRENT_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_vs_top1_delta_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_vs_top1_delta_review_rejected"
)
SOURCE_RESULT_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_passed"
)
DEFAULT_EXPECTED_LOG_COUNT = 32
DEFAULT_EXPECTED_RECORDS = 3200
DEFAULT_EXPECTED_RECORDS_PER_LOG = 100
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
COMPARISON_TOLERANCE = 1e-12


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution_output_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_md", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--expected_log_count", type=int, default=DEFAULT_EXPECTED_LOG_COUNT)
    parser.add_argument("--expected_records", type=int, default=DEFAULT_EXPECTED_RECORDS)
    parser.add_argument(
        "--expected_records_per_log",
        type=int,
        default=DEFAULT_EXPECTED_RECORDS_PER_LOG,
    )
    parser.add_argument(
        "--expected_num_candidates",
        type=int,
        default=DEFAULT_EXPECTED_NUM_CANDIDATES,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        execution_output_dir=args.execution_output_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_md=args.source_result_review_md,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_next_work=args.authorized_next_work,
        expected_log_count=args.expected_log_count,
        expected_records=args.expected_records,
        expected_records_per_log=args.expected_records_per_log,
        expected_num_candidates=args.expected_num_candidates,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    execution_output_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    expected_log_count: int = DEFAULT_EXPECTED_LOG_COUNT,
    expected_records: int = DEFAULT_EXPECTED_RECORDS,
    expected_records_per_log: int = DEFAULT_EXPECTED_RECORDS_PER_LOG,
    expected_num_candidates: int = DEFAULT_EXPECTED_NUM_CANDIDATES,
) -> dict[str, Any]:
    execution_output_dir = execution_output_dir.resolve()
    source_result_review_json = source_result_review_json.resolve()
    source_result_review_md = source_result_review_md.resolve()
    output_dir = output_dir.resolve()
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    source_result = _read_json(source_result_review_json)
    source_decision = _dict(source_result.get("final_decision"))
    source_records = _dict(source_result.get("records"))
    source_execution = _dict(source_result.get("execution"))
    source_heads = _dict(source_result.get("heads"))
    selection_logs = sorted(execution_output_dir.rglob("camp_selection_log.json"))
    records = _summarize_selection_logs(
        selection_logs=selection_logs,
        expected_num_candidates=expected_num_candidates,
    )
    checks = _checks(
        execution_output_dir=execution_output_dir,
        source_result_review_json=source_result_review_json,
        source_result_review_md=source_result_review_md,
        v14_text=v14_text,
        status_text=status_text,
        source_decision=source_decision,
        source_records=source_records,
        source_execution=source_execution,
        source_heads=source_heads,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        records=records,
        expected_log_count=expected_log_count,
        expected_records=expected_records,
        expected_records_per_log=expected_records_per_log,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    static_objective = records["selection_score_comparison"]
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "delta_review_only": True,
            "replay_executed_by_review": False,
            "candidate_generation_executed_by_review": False,
            "training_executed_by_review": False,
            "dp_modified_by_review": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": SCORE_EXPRESSION,
            "comparison_scope": (
                "logged masked CAMP selection score and normalized atom deltas only"
            ),
            "comparison_direction": "lower static CAMP objective value is better",
            "claim_scope": (
                "Supports static objective delta only; does not prove safety, "
                "closed-loop outcome, deployability, or CAMP superiority over DP Top-1."
            ),
        },
        "inputs": {
            "execution_output_dir": str(execution_output_dir),
            "source_result_review_json": str(source_result_review_json),
            "source_result_review_md": str(source_result_review_md),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_result_current_camp_head": source_heads.get("current_camp_head"),
            "source_result_current_dp_head": source_heads.get("current_dp_head"),
        },
        "source_hashes": {
            "source_result_review_json": _sha256(source_result_review_json)
            if source_result_review_json.is_file()
            else None,
            "source_result_review_md": _sha256(source_result_review_md)
            if source_result_review_md.is_file()
            else None,
        },
        "records": records,
        "source_result_review": {
            "passed": source_decision.get("passed"),
            "status": source_decision.get("status"),
            "failed_checks": source_decision.get("failed_checks"),
            "authorized_next_work": source_decision.get("authorized_next_work"),
            "selection_log_count": source_execution.get("selection_log_count"),
            "record_count": source_records.get("record_count"),
            "executed_top1_records": source_records.get("executed_top1_records"),
            "shadow_selected_index_differs_from_executed_index_records": (
                source_records.get(
                    "shadow_selected_index_differs_from_executed_index_records"
                )
            ),
        },
        "review_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed_checks=failed,
            authorized_next_work=authorized_next_work,
            static_objective_delta_supported=(
                passed
                and static_objective["better_records"] > 0
                and static_objective["worse_records"] == 0
            ),
        ),
    }


def _checks(
    *,
    execution_output_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    v14_text: str,
    status_text: str,
    source_decision: dict[str, Any],
    source_records: dict[str, Any],
    source_execution: dict[str, Any],
    source_heads: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    records: dict[str, Any],
    expected_log_count: int,
    expected_records: int,
    expected_records_per_log: int,
) -> list[dict[str, Any]]:
    latest_status = _latest_value(v14_text, "current_v14_status")
    latest_next_work = _latest_value(v14_text, "next_work_target")
    latest_status_doc_status = _latest_value(status_text, "current_v14_status")
    latest_status_doc_next_work = _latest_value(status_text, "next_work_target")
    selection_score = records["selection_score_comparison"]
    shadow_diff_selection_score = records[
        "selection_score_comparison_among_shadow_diff_records"
    ]
    checks: list[dict[str, Any]] = []

    def expect(name: str, actual: Any, expected: Any) -> None:
        checks.append(
            {
                "name": name,
                "passed": actual == expected,
                "actual": actual,
                "expected": expected,
            }
        )

    def require(name: str, passed: bool, actual: Any = None, expected: Any = True) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "actual": actual if actual is not None else bool(passed),
                "expected": expected,
            }
        )

    require("execution_output_dir_exists", execution_output_dir.is_dir(), execution_output_dir)
    require(
        "source_result_review_json_exists",
        source_result_review_json.is_file(),
        source_result_review_json,
    )
    require(
        "source_result_review_md_exists",
        source_result_review_md.is_file(),
        source_result_review_md,
    )
    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("audit_latest_status", latest_status, EXPECTED_CURRENT_STATUS)
    expect("audit_latest_next_work", latest_next_work, EXPECTED_CURRENT_NEXT_WORK)
    expect("status_doc_latest_status", latest_status_doc_status, EXPECTED_CURRENT_STATUS)
    expect(
        "status_doc_latest_next_work",
        latest_status_doc_next_work,
        EXPECTED_CURRENT_NEXT_WORK,
    )
    expect("source_result_review_passed", source_decision.get("passed"), True)
    expect("source_result_review_status", source_decision.get("status"), SOURCE_RESULT_REVIEW_STATUS)
    expect("source_result_review_failed_checks", source_decision.get("failed_checks"), [])
    expect(
        "source_result_review_authorized_next_work",
        source_decision.get("authorized_next_work"),
        EXPECTED_CURRENT_NEXT_WORK,
    )
    expect("source_result_current_dp_head_fixed", source_heads.get("current_dp_head"), required_dp_head)
    expect("source_selection_log_count", source_execution.get("selection_log_count"), expected_log_count)
    expect("source_record_count", source_records.get("record_count"), expected_records)
    expect("source_executed_top1_records", source_records.get("executed_top1_records"), expected_records)
    expect("selection_log_count", records["selection_log_count"], expected_log_count)
    expect("record_count", records["record_count"], expected_records)
    expect("records_per_log_min", records["records_per_log_min"], expected_records_per_log)
    expect("records_per_log_max", records["records_per_log_max"], expected_records_per_log)
    expect("executed_top1_records", records["executed_top1_records"], expected_records)
    expect("selected_matches_executed_records", records["selected_matches_executed_records"], expected_records)
    expect("default_off_selector_records", records["default_off_selector_records"], expected_records)
    expect("artifact_contract_ready_records", records["artifact_contract_ready_records"], expected_records)
    expect("score_expression_records", records["score_expression_records"], expected_records)
    expect("candidate_operation_records", records["candidate_operation_records"], expected_records)
    expect("candidate_count_bad_records", records["candidate_count_bad_records"], 0)
    expect("formal_seed_path_count", records["formal_seed_path_count"], 0)
    expect("selection_score_uncomparable_records", selection_score["uncomparable_records"], 0)
    expect("selection_score_worse_records", selection_score["worse_records"], 0)
    expect(
        "shadow_diff_selection_score_uncomparable_records",
        shadow_diff_selection_score["uncomparable_records"],
        0,
    )
    expect(
        "shadow_diff_selection_score_worse_records",
        shadow_diff_selection_score["worse_records"],
        0,
    )
    expect(
        "shadow_diff_selection_score_better_records",
        shadow_diff_selection_score["better_records"],
        records["shadow_selected_index_differs_from_executed_index_records"],
    )
    require(
        "static_objective_delta_supported",
        selection_score["better_records"] > 0 and selection_score["worse_records"] == 0,
        {
            "better_records": selection_score["better_records"],
            "worse_records": selection_score["worse_records"],
        },
    )
    return checks


def _summarize_selection_logs(
    *,
    selection_logs: list[Path],
    expected_num_candidates: int,
) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    per_log_counts: list[int] = []
    selected_indices: Counter[str] = Counter()
    shadow_indices: Counter[str] = Counter()
    executed_indices: Counter[str] = Counter()
    feasible_pairs: Counter[str] = Counter()
    selection_score_comp = _new_comparison_summary()
    selection_score_shadow_diff_comp = _new_comparison_summary()
    raw_score_comp = _new_comparison_summary()
    raw_score_shadow_diff_comp = _new_comparison_summary()
    atom_names: list[str] = []
    atom_deltas: defaultdict[str, list[float]] = defaultdict(list)

    for log in selection_logs:
        if _path_has_formal_seed(log):
            counters["formal_seed_path_count"] += 1
        payload = _read_json(log)
        records = _records_from_payload(payload)
        per_log_counts.append(len(records))
        for record in records:
            counters["record_count"] += 1
            selector = _dict(record.get("default_off_shadow_selector"))
            selected = _int_or_none(record.get("selected_index"))
            executed = _int_or_none(record.get("executed_index"))
            shadow = _int_or_none(selector.get("shadow_selected_index"))
            if shadow is None:
                shadow = _int_or_none(record.get("shadow_selected_index"))
            selected_indices[str(selected)] += 1
            shadow_indices[str(shadow)] += 1
            executed_indices[str(executed)] += 1
            if selected == executed:
                counters["selected_matches_executed_records"] += 1
            if executed == 0:
                counters["executed_top1_records"] += 1
            if shadow not in (None, 0):
                counters["shadow_selected_index_nonzero_records"] += 1
            if shadow != executed:
                counters["shadow_selected_index_differs_from_executed_index_records"] += 1
            if _default_off_selector_contract_ready(selector):
                counters["default_off_selector_records"] += 1
            if selector.get("artifact_contract_ready") is True:
                counters["artifact_contract_ready_records"] += 1
            if selector.get("score_expression") == SCORE_EXPRESSION:
                counters["score_expression_records"] += 1
            if selector.get("candidate_operation") == "fixed DP candidate reranking only":
                counters["candidate_operation_records"] += 1
            if record.get("num_candidates") != expected_num_candidates:
                counters["candidate_count_bad_records"] += 1

            feasible = record.get("feasible_mask")
            if (
                isinstance(feasible, list)
                and executed is not None
                and shadow is not None
                and len(feasible) > max(executed, shadow)
            ):
                pair = f"top1_{bool(feasible[executed])}_shadow_{bool(feasible[shadow])}"
                feasible_pairs[pair] += 1

            _add_comparison(
                selection_score_comp,
                record.get("selection_scores"),
                challenger_index=shadow,
                baseline_index=executed,
            )
            if shadow != executed:
                _add_comparison(
                    selection_score_shadow_diff_comp,
                    record.get("selection_scores"),
                    challenger_index=shadow,
                    baseline_index=executed,
                )
            _add_comparison(
                raw_score_comp,
                record.get("scores"),
                challenger_index=shadow,
                baseline_index=executed,
            )
            if shadow != executed:
                _add_comparison(
                    raw_score_shadow_diff_comp,
                    record.get("scores"),
                    challenger_index=shadow,
                    baseline_index=executed,
                )

            names = record.get("atom_names")
            atoms = record.get("selection_normalized_atoms", record.get("normalized_atoms"))
            if isinstance(names, list) and not atom_names:
                atom_names = [str(name) for name in names]
            if (
                isinstance(names, list)
                and isinstance(atoms, list)
                and executed is not None
                and shadow is not None
                and len(atoms) > max(executed, shadow)
                and isinstance(atoms[executed], list)
                and isinstance(atoms[shadow], list)
            ):
                for index, name in enumerate(names):
                    try:
                        atom_deltas[str(name)].append(
                            float(atoms[shadow][index]) - float(atoms[executed][index])
                        )
                    except (TypeError, ValueError, IndexError):
                        counters["atom_delta_uncomparable_records"] += 1

    return {
        "selection_log_count": len(selection_logs),
        "record_count": counters["record_count"],
        "records_per_log_min": min(per_log_counts) if per_log_counts else 0,
        "records_per_log_max": max(per_log_counts) if per_log_counts else 0,
        "selected_index_counts": dict(sorted(selected_indices.items())),
        "shadow_selected_index_counts": dict(sorted(shadow_indices.items())),
        "executed_index_counts": dict(sorted(executed_indices.items())),
        "feasible_pair_counts": dict(sorted(feasible_pairs.items())),
        "executed_top1_records": counters["executed_top1_records"],
        "selected_matches_executed_records": counters[
            "selected_matches_executed_records"
        ],
        "shadow_selected_index_nonzero_records": counters[
            "shadow_selected_index_nonzero_records"
        ],
        "shadow_selected_index_differs_from_executed_index_records": counters[
            "shadow_selected_index_differs_from_executed_index_records"
        ],
        "default_off_selector_records": counters["default_off_selector_records"],
        "artifact_contract_ready_records": counters["artifact_contract_ready_records"],
        "score_expression_records": counters["score_expression_records"],
        "candidate_operation_records": counters["candidate_operation_records"],
        "candidate_count_bad_records": counters["candidate_count_bad_records"],
        "formal_seed_path_count": counters["formal_seed_path_count"],
        "atom_delta_uncomparable_records": counters["atom_delta_uncomparable_records"],
        "atom_names": atom_names,
        "selection_score_comparison": _finalize_comparison(selection_score_comp),
        "selection_score_comparison_among_shadow_diff_records": _finalize_comparison(
            selection_score_shadow_diff_comp
        ),
        "raw_affine_score_comparison": _finalize_comparison(raw_score_comp),
        "raw_affine_score_comparison_among_shadow_diff_records": _finalize_comparison(
            raw_score_shadow_diff_comp
        ),
        "normalized_atom_delta_summaries": {
            name: _summarize_deltas(atom_deltas[name]) for name in atom_names
        },
    }


def _new_comparison_summary() -> dict[str, Any]:
    return {
        "records": 0,
        "better_records": 0,
        "worse_records": 0,
        "tie_records": 0,
        "uncomparable_records": 0,
        "finite_deltas": [],
        "nonfinite_better_records": 0,
        "nonfinite_worse_records": 0,
        "comparison_direction": "lower_is_better",
    }


def _add_comparison(
    summary: dict[str, Any],
    values: Any,
    *,
    challenger_index: int | None,
    baseline_index: int | None,
) -> None:
    summary["records"] += 1
    outcome, delta = _compare_lower(values, challenger_index, baseline_index)
    if outcome == "better":
        summary["better_records"] += 1
        if delta is None:
            summary["nonfinite_better_records"] += 1
    elif outcome == "worse":
        summary["worse_records"] += 1
        if delta is None:
            summary["nonfinite_worse_records"] += 1
    elif outcome == "tie":
        summary["tie_records"] += 1
    else:
        summary["uncomparable_records"] += 1
    if delta is not None and math.isfinite(delta):
        summary["finite_deltas"].append(delta)


def _compare_lower(
    values: Any,
    challenger_index: int | None,
    baseline_index: int | None,
) -> tuple[str, float | None]:
    if (
        not isinstance(values, list)
        or challenger_index is None
        or baseline_index is None
        or challenger_index < 0
        or baseline_index < 0
        or len(values) <= max(challenger_index, baseline_index)
    ):
        return "uncomparable", None
    challenger = _number_or_none(values[challenger_index])
    baseline = _number_or_none(values[baseline_index])
    if challenger is None or baseline is None:
        return "uncomparable", None
    if math.isnan(challenger) or math.isnan(baseline):
        return "uncomparable", None
    if math.isinf(challenger) or math.isinf(baseline):
        if challenger == baseline:
            return "tie", None
        if math.isfinite(challenger) and math.isinf(baseline) and baseline > 0:
            return "better", None
        if math.isinf(challenger) and challenger > 0 and math.isfinite(baseline):
            return "worse", None
        return "uncomparable", None
    delta = challenger - baseline
    if delta < -COMPARISON_TOLERANCE:
        return "better", delta
    if delta > COMPARISON_TOLERANCE:
        return "worse", delta
    return "tie", delta


def _finalize_comparison(summary: dict[str, Any]) -> dict[str, Any]:
    deltas = list(summary.pop("finite_deltas"))
    finalized = dict(summary)
    finalized.update(_summarize_deltas(deltas))
    return finalized


def _summarize_deltas(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        return {
            "finite_delta_count": 0,
            "finite_delta_mean": None,
            "finite_delta_median": None,
            "finite_delta_min": None,
            "finite_delta_max": None,
            "finite_delta_lower_better_wins": 0,
            "finite_delta_lower_better_losses": 0,
            "finite_delta_ties": 0,
        }
    wins = sum(1 for delta in deltas if delta < -COMPARISON_TOLERANCE)
    losses = sum(1 for delta in deltas if delta > COMPARISON_TOLERANCE)
    ties = len(deltas) - wins - losses
    return {
        "finite_delta_count": len(deltas),
        "finite_delta_mean": sum(deltas) / len(deltas),
        "finite_delta_median": statistics.median(deltas),
        "finite_delta_min": min(deltas),
        "finite_delta_max": max(deltas),
        "finite_delta_lower_better_wins": wins,
        "finite_delta_lower_better_losses": losses,
        "finite_delta_ties": ties,
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "shadow_vs_top1_delta_review_report.json"
    md_path = output_dir / "shadow_vs_top1_delta_review_report.md"
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = []
    for path in (json_path, md_path):
        sums.append(f"{_sha256(path)}  {path.name}")
    sums_path = output_dir / "SHA256SUMS"
    sums_path.write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    records = report["records"]
    selection = records["selection_score_comparison"]
    shadow_diff = records["selection_score_comparison_among_shadow_diff_records"]
    raw_score = records["raw_affine_score_comparison"]
    lines = [
        "# v14 Shadow-vs-Top1 Delta Review",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Static objective delta supported: `{decision['static_objective_delta_supported']}`",
        "",
        "## Scope",
        "",
        "- Review only: no replay, candidate generation, training, DP modification, promotion, or deployment.",
        "- CAMP remains a default-off shadow reranker over the fixed DP candidate tensor.",
        "- The executed trajectory remains DP Top-1.",
        "- Positive claim scope is limited to the logged masked CAMP selection objective.",
        "- This is not a safety benefit or CAMP-over-DP Top-1 claim.",
        "",
        "## Counts",
        "",
        f"- Selection logs: `{records['selection_log_count']}`",
        f"- Records: `{records['record_count']}`",
        f"- Executed DP Top-1 records: `{records['executed_top1_records']}`",
        f"- Shadow differs from executed records: `{records['shadow_selected_index_differs_from_executed_index_records']}`",
        f"- Formal seed path count: `{records['formal_seed_path_count']}`",
        "",
        "## Masked Selection Score Delta",
        "",
        f"- Better records: `{selection['better_records']}`",
        f"- Worse records: `{selection['worse_records']}`",
        f"- Tie records: `{selection['tie_records']}`",
        f"- Uncomparable records: `{selection['uncomparable_records']}`",
        f"- Finite delta mean: `{selection['finite_delta_mean']}`",
        f"- Finite delta median: `{selection['finite_delta_median']}`",
        "",
        "## Shadow-Different Subset",
        "",
        f"- Better records: `{shadow_diff['better_records']}`",
        f"- Worse records: `{shadow_diff['worse_records']}`",
        f"- Tie records: `{shadow_diff['tie_records']}`",
        f"- Uncomparable records: `{shadow_diff['uncomparable_records']}`",
        "",
        "## Raw Affine Score Delta",
        "",
        f"- Better records: `{raw_score['better_records']}`",
        f"- Worse records: `{raw_score['worse_records']}`",
        f"- Tie records: `{raw_score['tie_records']}`",
        f"- Uncomparable records: `{raw_score['uncomparable_records']}`",
        "",
        "## Feasibility",
        "",
        f"- Feasible pair counts: `{json.dumps(records['feasible_pair_counts'], sort_keys=True)}`",
        "",
        "## Boundary",
        "",
        f"- Score expression: `{report['analysis']['score_expression']}`",
        f"- Claim scope: {report['analysis']['claim_scope']}",
    ]
    return "\n".join(lines) + "\n"


def _decision(
    *,
    passed: bool,
    failed_checks: list[str],
    authorized_next_work: str,
    static_objective_delta_supported: bool,
) -> dict[str, Any]:
    return {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failed_checks": failed_checks,
        "authorized_inserted_work": AUTHORIZED_INSERTED_WORK,
        "authorized_next_work": authorized_next_work,
        "static_objective_delta_supported": bool(static_objective_delta_supported),
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "candidate_generation_authorized": False,
        "replay_execution_authorized": False,
        "dp_modification_authorized": False,
        "failure_class": None if passed else _failure_class(failed_checks),
    }


def _failure_class(failed_checks: list[str]) -> str:
    if any(check.startswith("audit_latest") or check.startswith("status_doc") for check in failed_checks):
        return "v14_eof_contract_mismatch"
    if any("head" in check for check in failed_checks):
        return "head_or_fixed_dp_contract_failure"
    if any("selection_score" in check or "static_objective" in check for check in failed_checks):
        return "static_objective_delta_failure"
    return "shadow_vs_top1_delta_review_failure"


def _default_off_selector_contract_ready(selector: dict[str, Any]) -> bool:
    return (
        selector.get("schema_version")
        == "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
        and selector.get("enabled") is True
        and selector.get("default_off") is True
        and selector.get("source_scope") == "public_simulator_fixed_dp_candidate_tensor"
        and selector.get("selection_effect") is False
        and selector.get("online_selector_change") is False
        and selector.get("candidate_operation") == "fixed DP candidate reranking only"
        and selector.get("score_expression") == SCORE_EXPRESSION
        and selector.get("executed_index") == 0
        and selector.get("executed_output_policy") == "dp_top1"
        and isinstance(selector.get("shadow_selected_index"), int)
    )


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [_dict(item) for item in payload]
    if isinstance(payload, dict):
        for key in ("records", "selection_records", "steps"):
            value = payload.get(key)
            if isinstance(value, list):
                return [_dict(item) for item in value]
    return []


def _latest_value(text: str, key: str) -> str | None:
    prefix = key + "="
    values = [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]
    return values[-1] if values else None


def _path_has_formal_seed(path: Path) -> bool:
    lowered = str(path).lower().replace("\\", "/")
    return any(marker in lowered for marker in FORMAL_SEED_MARKERS)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_or_none(value: Any) -> int | None:
    try:
        if isinstance(value, bool):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _number_or_none(value: Any) -> float | None:
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
