#!/usr/bin/env python3
"""Execute the v16 fixed-DP scale-up paired-evaluation gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_module(filename: str, name: str):
    path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BASE_MODULE = _load_module(
    "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation.py",
    "v16_pilot_paired_eval_execution_base",
)
PREFLIGHT_MODULE = _load_module(
    "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation.py",
    "v16_scaleup_paired_eval_preflight",
)
PLAN_MODULE = PREFLIGHT_MODULE.PLAN_MODULE
STATIC_REVIEW_MODULE = PREFLIGHT_MODULE.SOURCE_REVIEW_MODULE
TRAINING_MODULE = _load_module(
    "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training.py",
    "v16_scaleup_training_execution",
)
TRAINING_REVIEW_MODULE = _load_module(
    "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result.py",
    "v16_scaleup_training_result_review",
)
SPLIT_MODULE = _load_module(
    "split_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup.py",
    "v16_scaleup_split_execution",
)
SPLIT_REVIEW_MODULE = _load_module(
    "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result.py",
    "v16_scaleup_split_result_review",
)

FIXED_DP_HEAD = TRAINING_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = TRAINING_MODULE.SCORE_EXPRESSION
EXPECTED_COUNTS = TRAINING_MODULE.EXPECTED_COUNTS
EXPECTED_K = TRAINING_MODULE.EXPECTED_K
EVALUATION_SPLITS = ("calibration", "holdout")

SOURCE_PLAN_SCHEMA_VERSION = PLAN_MODULE.SCHEMA_VERSION
SOURCE_PLAN_STATUS = PLAN_MODULE.READY_STATUS
SOURCE_PLAN_JSON_NAME = PLAN_MODULE.PLAN_JSON_NAME
SOURCE_STATIC_REVIEW_SCHEMA_VERSION = STATIC_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_STATIC_REVIEW_STATUS = STATIC_REVIEW_MODULE.READY_STATUS
SOURCE_STATIC_REVIEW_JSON_NAME = STATIC_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_PREFLIGHT_SCHEMA_VERSION = PREFLIGHT_MODULE.SCHEMA_VERSION
SOURCE_PREFLIGHT_STATUS = PREFLIGHT_MODULE.READY_STATUS
SOURCE_PREFLIGHT_JSON_NAME = PREFLIGHT_MODULE.PREFLIGHT_JSON_NAME
SOURCE_TRAINING_SCHEMA_VERSION = TRAINING_MODULE.SCHEMA_VERSION
SOURCE_TRAINING_STATUS = TRAINING_MODULE.READY_STATUS
SOURCE_TRAINING_JSON_NAME = TRAINING_MODULE.REPORT_JSON_NAME
SOURCE_TRAINING_REVIEW_SCHEMA_VERSION = TRAINING_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_TRAINING_REVIEW_STATUS = TRAINING_REVIEW_MODULE.READY_STATUS
SOURCE_TRAINING_REVIEW_JSON_NAME = TRAINING_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_SPLIT_SCHEMA_VERSION = SPLIT_MODULE.SCHEMA_VERSION
SOURCE_SPLIT_STATUS = SPLIT_MODULE.READY_STATUS
SOURCE_SPLIT_JSON_NAME = SPLIT_MODULE.REPORT_JSON_NAME
SOURCE_SPLIT_REVIEW_SCHEMA_VERSION = SPLIT_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_SPLIT_REVIEW_STATUS = SPLIT_REVIEW_MODULE.READY_STATUS
SOURCE_SPLIT_REVIEW_JSON_NAME = SPLIT_REVIEW_MODULE.REVIEW_JSON_NAME

SOURCE_STATIC_REVIEW_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
SOURCE_PREFLIGHT_CURRENT_WORK = STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
AUTHORIZED_CURRENT_WORK = PREFLIGHT_MODULE.AUTHORIZED_NEXT_WORK
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_execution_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_execution_rejected"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_execution_v1"
EXECUTION_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_execution.json"
EXECUTION_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_execution.md"
PAIRED_ROWS_JSONL_NAME = "paired_evaluation_rows.jsonl"
SPLIT_METRICS_JSON_NAME = "paired_evaluation_split_metrics.json"
LATENCY_JSON_NAME = "selector_latency.json"
TIMING_JSON_NAME = "paired_evaluation_execution_timing.json"


for name, value in {
    "TRAINING_MODULE": TRAINING_MODULE,
    "FIXED_DP_HEAD": FIXED_DP_HEAD,
    "SCORE_EXPRESSION": SCORE_EXPRESSION,
    "EXPECTED_COUNTS": EXPECTED_COUNTS,
    "EXPECTED_K": EXPECTED_K,
    "EVALUATION_SPLITS": EVALUATION_SPLITS,
    "AUTHORIZED_CURRENT_WORK": AUTHORIZED_CURRENT_WORK,
    "AUTHORIZED_NEXT_WORK": AUTHORIZED_NEXT_WORK,
    "READY_STATUS": READY_STATUS,
    "REJECT_STATUS": REJECT_STATUS,
}.items():
    setattr(BASE_MODULE, name, value)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_json", type=Path, required=True)
    parser.add_argument("--source_training_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_training_json", type=Path, required=True)
    parser.add_argument("--source_training_model_json", type=Path, required=True)
    parser.add_argument("--source_training_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_training_result_review_json", type=Path, required=True)
    parser.add_argument("--source_split_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_split_execution_json", type=Path, required=True)
    parser.add_argument("--source_calibration_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_holdout_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_train_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_split_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_split_result_review_json", type=Path, required=True)
    parser.add_argument("--source_scaleup_corpus_artifact_dir", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument("--expected_preflight_root_sha256", required=True)
    parser.add_argument("--expected_training_root_sha256", required=True)
    parser.add_argument("--expected_training_result_review_root_sha256", required=True)
    parser.add_argument("--expected_split_execution_root_sha256", required=True)
    parser.add_argument("--expected_split_result_review_root_sha256", required=True)
    parser.add_argument("--expected_scaleup_corpus_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_execution(
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_preflight_artifact_dir=args.source_preflight_artifact_dir,
        source_preflight_json=args.source_preflight_json,
        source_training_artifact_dir=args.source_training_artifact_dir,
        source_training_json=args.source_training_json,
        source_training_model_json=args.source_training_model_json,
        source_training_result_review_artifact_dir=args.source_training_result_review_artifact_dir,
        source_training_result_review_json=args.source_training_result_review_json,
        source_split_execution_artifact_dir=args.source_split_execution_artifact_dir,
        source_split_execution_json=args.source_split_execution_json,
        source_calibration_records_jsonl=args.source_calibration_records_jsonl,
        source_holdout_records_jsonl=args.source_holdout_records_jsonl,
        source_train_records_jsonl=args.source_train_records_jsonl,
        source_split_result_review_artifact_dir=args.source_split_result_review_artifact_dir,
        source_split_result_review_json=args.source_split_result_review_json,
        source_scaleup_corpus_artifact_dir=args.source_scaleup_corpus_artifact_dir,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        expected_training_root_sha256=args.expected_training_root_sha256,
        expected_training_result_review_root_sha256=args.expected_training_result_review_root_sha256,
        expected_split_execution_root_sha256=args.expected_split_execution_root_sha256,
        expected_split_result_review_root_sha256=args.expected_split_result_review_root_sha256,
        expected_scaleup_corpus_root_sha256=args.expected_scaleup_corpus_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_execution,
        command=sys.argv,
    )
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def run_execution(*, command: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
    report = build_report(**kwargs)
    report["command"] = command or []
    write_outputs(kwargs["output_dir"], report)
    return report


def build_report(
    *,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_preflight_artifact_dir: Path,
    source_preflight_json: Path,
    source_training_artifact_dir: Path,
    source_training_json: Path,
    source_training_model_json: Path,
    source_training_result_review_artifact_dir: Path,
    source_training_result_review_json: Path,
    source_split_execution_artifact_dir: Path,
    source_split_execution_json: Path,
    source_calibration_records_jsonl: Path,
    source_holdout_records_jsonl: Path,
    source_train_records_jsonl: Path,
    source_split_result_review_artifact_dir: Path,
    source_split_result_review_json: Path,
    source_scaleup_corpus_artifact_dir: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_plan_root_sha256: str,
    expected_static_review_root_sha256: str,
    expected_preflight_root_sha256: str,
    expected_training_root_sha256: str,
    expected_training_result_review_root_sha256: str,
    expected_split_execution_root_sha256: str,
    expected_split_result_review_root_sha256: str,
    expected_scaleup_corpus_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    plan = _read_json(source_plan_json)
    static_review = _read_json(source_static_review_json)
    preflight = _read_json(source_preflight_json)
    training = _read_json(source_training_json)
    model = _read_json(source_training_model_json)
    training_review = _read_json(source_training_result_review_json)
    split_execution = _read_json(source_split_execution_json)
    split_review = _read_json(source_split_result_review_json)
    train_records = _read_jsonl(source_train_records_jsonl)
    calibration_records = _read_jsonl(source_calibration_records_jsonl)
    holdout_records = _read_jsonl(source_holdout_records_jsonl)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    source_artifacts = {
        "paired_evaluation_plan": _source_artifact(source_plan_artifact_dir, expected_plan_root_sha256),
        "paired_evaluation_plan_static_review": _source_artifact(
            source_static_review_artifact_dir,
            expected_static_review_root_sha256,
        ),
        "paired_evaluation_preflight": _source_artifact(source_preflight_artifact_dir, expected_preflight_root_sha256),
        "training_execution": _source_artifact(source_training_artifact_dir, expected_training_root_sha256),
        "training_result_review": _source_artifact(
            source_training_result_review_artifact_dir,
            expected_training_result_review_root_sha256,
        ),
        "split_execution": _source_artifact(source_split_execution_artifact_dir, expected_split_execution_root_sha256),
        "split_result_review": _source_artifact(
            source_split_result_review_artifact_dir,
            expected_split_result_review_root_sha256,
        ),
        "scaleup_corpus": _source_artifact(source_scaleup_corpus_artifact_dir, expected_scaleup_corpus_root_sha256),
    }
    preflight_body = preflight.get("scaleup_paired_evaluation_preflight", {})
    training_body = training.get("scaleup_training_execution", {})
    primary_splits = preflight_body.get("primary_eval_splits", [])
    reporting_splits = preflight_body.get("reporting_only_splits", [])
    primary_source_records = _tag_records(calibration_records, "calibration") + _tag_records(holdout_records, "holdout")
    enriched_records, atom_derivation = BASE_MODULE._enrich_eval_records(primary_source_records)
    paired_rows, latency = BASE_MODULE._paired_rows(enriched_records, model, current_camp_head, current_dp_head)
    _add_source_fields(paired_rows, enriched_records)
    split_metrics = BASE_MODULE._split_metrics(paired_rows)
    record_summary = BASE_MODULE._record_summary(train_records, calibration_records, holdout_records, paired_rows)
    checks = [
        _expect("paired_evaluation_execution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_paired_eval_execution", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_paired_eval_execution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_preflight", audit_text, f"current_v16_status={SOURCE_PREFLIGHT_STATUS}"),
        _contains("status_records_preflight", status_text, f"current_v16_status={SOURCE_PREFLIGHT_STATUS}"),
        _expect("source_plan_schema", plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", plan.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", plan.get("final_decision", {}).get("passed"), True),
        _expect("source_plan_authorizes_static_review", plan.get("final_decision", {}).get("authorized_next_work"), SOURCE_STATIC_REVIEW_CURRENT_WORK),
        _expect("source_static_review_schema", static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA_VERSION),
        _expect("source_static_review_status", static_review.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", static_review.get("final_decision", {}).get("passed"), True),
        _expect("source_static_review_authorizes_preflight", static_review.get("final_decision", {}).get("authorized_next_work"), SOURCE_PREFLIGHT_CURRENT_WORK),
        _expect("source_preflight_schema", preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA_VERSION),
        _expect("source_preflight_status", preflight.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_passed", preflight.get("final_decision", {}).get("passed"), True),
        _expect("source_preflight_authorizes_execution", preflight.get("final_decision", {}).get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_training_schema", training.get("schema_version"), SOURCE_TRAINING_SCHEMA_VERSION),
        _expect("source_training_status", training.get("status"), SOURCE_TRAINING_STATUS),
        _expect("source_training_passed", training.get("final_decision", {}).get("passed"), True),
        _expect("source_training_result_review_schema", training_review.get("schema_version"), SOURCE_TRAINING_REVIEW_SCHEMA_VERSION),
        _expect("source_training_result_review_status", training_review.get("status"), SOURCE_TRAINING_REVIEW_STATUS),
        _expect("source_training_result_review_passed", training_review.get("final_decision", {}).get("passed"), True),
        _expect("source_split_schema", split_execution.get("schema_version"), SOURCE_SPLIT_SCHEMA_VERSION),
        _expect("source_split_status", split_execution.get("status"), SOURCE_SPLIT_STATUS),
        _expect("source_split_passed", split_execution.get("final_decision", {}).get("passed"), True),
        _expect("source_split_review_schema", split_review.get("schema_version"), SOURCE_SPLIT_REVIEW_SCHEMA_VERSION),
        _expect("source_split_review_status", split_review.get("status"), SOURCE_SPLIT_REVIEW_STATUS),
        _expect("source_split_review_passed", split_review.get("final_decision", {}).get("passed"), True),
        _expect("primary_eval_splits_calibration_holdout", primary_splits, list(EVALUATION_SPLITS)),
        _expect("reporting_only_splits_train", reporting_splits, ["train"]),
        _expect("train_excluded_from_primary_eval", "train" not in primary_splits, True),
        _expect("train_records_reporting_only_6263", len(train_records), EXPECTED_COUNTS["train"]),
        _expect("calibration_records_2156", len(calibration_records), EXPECTED_COUNTS["calibration"]),
        _expect("holdout_records_1581", len(holdout_records), EXPECTED_COUNTS["holdout"]),
        _expect("primary_eval_rows_3737", len(paired_rows), EXPECTED_COUNTS["calibration"] + EXPECTED_COUNTS["holdout"]),
        _expect("preflight_primary_eval_rows_3737", preflight_body.get("paired_rows_by_split", {}).get("primary_eval_total"), 3737),
        _expect("training_calibration_not_used", training_body.get("calibration_records_used_for_training"), 0),
        _expect("training_holdout_not_used", training_body.get("holdout_records_used_for_training"), 0),
        _expect("no_train_rows_in_primary_eval", record_summary["train_rows_in_primary_eval"], 0),
        _expect("scene_zero_overlap", record_summary["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", record_summary["sample_zero_overlap"], True),
        _expect("k_values_8", record_summary["k_values"], [EXPECTED_K]),
        _expect("candidate_count_values_8", record_summary["candidate_count_values"], [EXPECTED_K]),
        _expect("dp_head_values_fixed", record_summary["dp_head_values"], [FIXED_DP_HEAD]),
        _expect("candidate_tensor_sha256_present", record_summary["missing_candidate_tensor_sha256"], 0),
        _expect("candidate_tensor_not_mutated", record_summary["candidate_tensor_mutated_count"], 0),
        _expect("selected_index_in_range", record_summary["selected_index_out_of_range_count"], 0),
        _expect("atom_derivation_failures", atom_derivation["failed_records"], 0),
        _expect("model_score_expression_affine", model.get("score_expression"), SCORE_EXPRESSION),
        _expect("model_weights_nonnegative", model.get("weights_nonnegative"), True),
        _expect("model_weights_sum_to_one", model.get("weights_sum_to_one"), True),
        _expect("model_approved_atoms_only", model.get("approved_atoms_only"), True),
        _check("model_weights_match_atoms", BASE_MODULE._weights_match_records(model, paired_rows), model.get("weights"), "weights match atoms"),
        _expect("latency_count_matches_rows", latency["count"], len(paired_rows)),
    ]
    checks.extend(_forbidden_checks(plan.get("final_decision", {}), "source_plan"))
    checks.extend(_forbidden_checks(static_review.get("final_decision", {}), "source_static_review"))
    checks.extend(_forbidden_checks(preflight.get("final_decision", {}), "source_preflight"))
    checks.extend(_forbidden_checks(training.get("final_decision", {}), "source_training"))
    checks.extend(_forbidden_checks(training_review.get("final_decision", {}), "source_training_review"))
    checks.extend(_forbidden_checks(split_execution.get("final_decision", {}), "source_split"))
    checks.extend(_forbidden_checks(split_review.get("final_decision", {}), "source_split_review"))
    checks.extend(
        _check(
            f"source_{name}_sha256s_verified",
            artifact["sha256s_verified"] and artifact["root_sha256"] == artifact["expected_root_sha256"],
            artifact,
            "verified source artifact",
        )
        for name, artifact in source_artifacts.items()
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifacts": source_artifacts,
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_plan_camp_head": plan.get("heads", {}).get("camp_head"),
                "source_static_review_camp_head": static_review.get("heads", {}).get("camp_head"),
                "source_training_camp_head": training.get("heads", {}).get("camp_head"),
                "source_split_camp_head": split_execution.get("heads", {}).get("camp_head"),
            },
            "scaleup_paired_evaluation_execution": {
                "paired_rows_by_split": {
                    "calibration": len(calibration_records),
                    "holdout": len(holdout_records),
                    "primary_eval_total": len(paired_rows),
                    "train_reporting_only": len(train_records),
                },
                "primary_eval_splits": list(EVALUATION_SPLITS),
                "reporting_only_splits": ["train"],
                "comparison": "camp_selected_fixed_dp_candidate_vs_dp_top1",
                "score_expression": SCORE_EXPRESSION,
                "weights_nonnegative": model.get("weights_nonnegative"),
                "weights_sum_to_one": model.get("weights_sum_to_one"),
                "approved_atoms_only": model.get("approved_atoms_only"),
                "candidate_tensor_mutated_count": record_summary["candidate_tensor_mutated_count"],
                "selected_index_out_of_range_count": record_summary["selected_index_out_of_range_count"],
                "scaleup_evidence_only": True,
                "claims": {
                    "performance_claim_allowed": False,
                    "safety_claim_allowed": False,
                    "camp_over_dp_claim_allowed": False,
                    "reason": "execution gate records descriptive paired metrics only; result-review/claim/promotion are out of scope",
                },
            },
            "atom_derivation": atom_derivation,
            "split_metrics": split_metrics,
            "selector_latency_ms": latency,
            "timing": {"selector_latency_ms": latency, "instrumentation_changes_selector_behavior": False},
            "checks": checks,
            "final_decision": _decision(passed, failed, len(checks)),
            "paired_rows": paired_rows,
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    public_report = {key: value for key, value in report.items() if key != "paired_rows"}
    for name, payload in {
        EXECUTION_JSON_NAME: public_report,
        SPLIT_METRICS_JSON_NAME: report["split_metrics"],
        LATENCY_JSON_NAME: report["selector_latency_ms"],
        TIMING_JSON_NAME: report["timing"],
    }.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / PAIRED_ROWS_JSONL_NAME).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in report["paired_rows"]),
        encoding="utf-8",
    )
    (output_dir / EXECUTION_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    BASE_MODULE._write_sha_manifest(output_dir)


def _add_source_fields(rows: list[dict[str, Any]], records: list[dict[str, Any]]) -> None:
    for row, record in zip(rows, records):
        row.update(
            {
                "source_record_index": record.get("record_index"),
                "source_split": record.get("source_split"),
                "source_scene_id": record.get("source_scene_id"),
                "source_sample_id": record.get("source_sample_id"),
                "camp_atom_table_sha256": record.get("camp_atom_table_sha256"),
                "candidate_npz_sha256": record.get("candidate_npz_sha256"),
                "adapter_input_sha256": record.get("adapter_input_sha256"),
            }
        )


def _forbidden_checks(final: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _expect(f"{prefix}_{field}_false", final.get(field, False), False)
        for field in (
            "evaluation_executed",
            "paired_evaluation_executed",
            "performance_claimed",
            "safety_claimed",
            "camp_over_dp_claimed",
            "promotion_executed",
            "deployment_executed",
            "dp_modified",
            "candidate_tensor_modified",
            "fake_candidate_tensor_generated",
        )
    ]


def _decision(passed: bool, failed: list[str], check_count: int) -> dict[str, Any]:
    decision = BASE_MODULE._decision(passed, failed, check_count)
    decision.update(
        {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "scaleup_evidence_only": True,
        }
    )
    return decision


def _source_artifact(path: Path, expected_root_sha256: str) -> dict[str, Any]:
    artifact = TRAINING_MODULE._source_artifact(path, expected_root_sha256)
    artifact["root_matches_expected"] = artifact.get("root_sha256") == expected_root_sha256
    return artifact


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    metrics = report["split_metrics"]["primary"]
    paired = report["scaleup_paired_evaluation_execution"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Scale-Up Paired-Evaluation Execution",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Primary rows: `{paired['paired_rows_by_split']['primary_eval_total']}`",
            f"- Better/tie/worse: `{metrics['better_tie_worse']}`",
            f"- Mean delta: `{metrics['mean_delta']}`",
            f"- CI95: `{metrics['ci95']}`",
            f"- Non-Top1 selection rate: `{metrics['non_top1_selection_rate']}`",
            f"- Oracle gap closed: `{metrics['oracle_gap_closed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- No performance, safety, or CAMP-over-DP claim is made.",
            "- No promotion or deployment is executed.",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_PLAN_CAMP_HEAD={heads['source_plan_camp_head']}",
            f"SOURCE_STATIC_REVIEW_CAMP_HEAD={heads['source_static_review_camp_head']}",
            f"SOURCE_TRAINING_CAMP_HEAD={heads['source_training_camp_head']}",
            f"SOURCE_SPLIT_CAMP_HEAD={heads['source_split_camp_head']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return BASE_MODULE._read_json(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return BASE_MODULE._read_jsonl(path)


def _read_text(path: Path) -> str:
    return BASE_MODULE._read_text(path)


def _tag_records(records: list[dict[str, Any]], split: str) -> list[dict[str, Any]]:
    return BASE_MODULE._tag_records(records, split)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return BASE_MODULE._contains(name, text, needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return BASE_MODULE._expect(name, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return BASE_MODULE._check(name, passed, actual, expected)


def _stable(value: Any) -> Any:
    return BASE_MODULE._stable(value)


if __name__ == "__main__":
    raise SystemExit(main())
