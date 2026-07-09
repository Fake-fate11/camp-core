#!/usr/bin/env python3
"""Preflight the v16 fixed-DP scale-up CAMP training gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_source_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v16_scaleup_training_preflight_plan_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE
FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SOURCE_PLAN_SCHEMA_VERSION = SOURCE_REVIEW_MODULE.SOURCE_PLAN_SCHEMA_VERSION
SOURCE_REVIEW_SCHEMA_VERSION = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_READY_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
SOURCE_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_execution_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_v1"
PREFLIGHT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight.json"
PREFLIGHT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight.md"
DEFAULT_TRAINING_SCRIPT = "scripts/integrations/train_diffusion_planner_static_camp.py"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_train_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_calibration_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_holdout_records_jsonl", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--training_script", type=Path, default=Path(DEFAULT_TRAINING_SCRIPT))
    parser.add_argument("--training_output_root", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument("--python_executable", default=sys.executable)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_sha256s=args.source_plan_sha256s,
        source_plan_root_sha256s=args.source_plan_root_sha256s,
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_static_review_root_sha256s=args.source_static_review_root_sha256s,
        source_train_records_jsonl=args.source_train_records_jsonl,
        source_calibration_records_jsonl=args.source_calibration_records_jsonl,
        source_holdout_records_jsonl=args.source_holdout_records_jsonl,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        training_script=args.training_script,
        training_output_root=args.training_output_root,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        python_executable=args.python_executable,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_sha256s: Path,
    source_plan_root_sha256s: Path,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_sha256s: Path,
    source_static_review_root_sha256s: Path,
    source_train_records_jsonl: Path,
    source_calibration_records_jsonl: Path,
    source_holdout_records_jsonl: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    training_script: Path,
    training_output_root: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_plan_root_sha256: str,
    expected_static_review_root_sha256: str,
    python_executable: str = sys.executable,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    plan_artifact = source_plan_artifact_dir.resolve()
    review_artifact = source_static_review_artifact_dir.resolve()
    plan = _read_json(source_plan_json)
    review = _read_json(source_static_review_json)
    plan_root_sha = _read_root_sha(source_plan_root_sha256s)
    review_root_sha = _read_root_sha(source_static_review_root_sha256s)
    plan_sha_entries, plan_sha_failures = _verify_sha256s(plan_artifact, source_plan_sha256s)
    review_sha_entries, review_sha_failures = _verify_sha256s(review_artifact, source_static_review_sha256s)
    records = {
        "train": _read_jsonl(source_train_records_jsonl),
        "calibration": _read_jsonl(source_calibration_records_jsonl),
        "holdout": _read_jsonl(source_holdout_records_jsonl),
    }
    record_summary = _record_summary(records)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8").split("## Current V15 Status", 1)[0]
    plan_final = plan.get("final_decision", {})
    review_final = review.get("final_decision", {})
    plan_body = plan.get("scaleup_training_preflight_plan", {})
    review_body = review.get("plan_static_review", {})
    command = _training_command(
        python_executable=python_executable,
        training_script=training_script,
        train_records=source_train_records_jsonl,
        training_output_root=training_output_root,
    )
    preflight = _preflight_summary(
        plan_root_sha=plan_root_sha,
        review_root_sha=review_root_sha,
        review_body=review_body,
        record_summary=record_summary,
        command=command,
        training_output_root=training_output_root,
    )
    expected_counts = PLAN_MODULE.EXPECTED_RECORD_COUNTS
    training_command = " ".join(command)
    checks = [
        _expect("training_preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_training_preflight", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_training_preflight", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_static_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_static_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _check("source_plan_artifact_exists", plan_artifact.is_dir(), str(plan_artifact), "directory"),
        _check("source_static_review_artifact_exists", review_artifact.is_dir(), str(review_artifact), "directory"),
        _expect("source_plan_schema", plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", plan.get("status"), PLAN_MODULE.READY_STATUS),
        _expect("source_plan_passed", plan_final.get("passed"), True),
        _expect("source_plan_authorizes_static_review", plan_final.get("authorized_next_work"), SOURCE_CURRENT_WORK),
        _expect("source_plan_root_sha256", plan_root_sha, expected_plan_root_sha256),
        _check("source_plan_sha256s_verified", not plan_sha_failures, plan_sha_failures[:10], []),
        _check("source_plan_sha256s_complete", plan_sha_entries >= 7, plan_sha_entries, ">=7"),
        _expect("source_static_review_schema", review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("source_static_review_status", review.get("status"), SOURCE_READY_STATUS),
        _expect("source_static_review_passed", review_final.get("passed"), True),
        _expect("source_static_review_authorizes_preflight", review_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_root_sha256", review_root_sha, expected_static_review_root_sha256),
        _expect("source_static_review_links_plan_root", review_body.get("source_plan_root_sha256"), expected_plan_root_sha256),
        _check("source_static_review_sha256s_verified", not review_sha_failures, review_sha_failures[:10], []),
        _check("source_static_review_sha256s_complete", review_sha_entries >= 7, review_sha_entries, ">=7"),
        _expect("train_records_6263", record_summary["counts"]["train"], expected_counts["train"]),
        _expect("calibration_records_2156", record_summary["counts"]["calibration"], expected_counts["calibration"]),
        _expect("holdout_records_1581", record_summary["counts"]["holdout"], expected_counts["holdout"]),
        _expect("plan_train_records_6263", plan_body.get("training_inputs", {}).get("train_records"), expected_counts["train"]),
        _expect("review_train_records_6263", review_body.get("train_records"), expected_counts["train"]),
        _expect("calibration_records_not_used_for_training", review_body.get("calibration_records_used_for_training"), 0),
        _expect("holdout_records_not_used_for_training", review_body.get("holdout_records_used_for_training"), 0),
        _expect(
            "training_command_uses_train_only",
            str(source_train_records_jsonl) in command
            and "calibration_records.jsonl" not in training_command
            and "holdout_records.jsonl" not in training_command,
            True,
        ),
        _expect("scene_zero_overlap", record_summary["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", record_summary["sample_zero_overlap"], True),
        _expect("train_k_values_8", record_summary["train_k_values"], [PLAN_MODULE.EXPECTED_K]),
        _expect("train_candidate_count_values_8", record_summary["train_candidate_count_values"], [PLAN_MODULE.EXPECTED_K]),
        _expect("train_candidate_tensor_hashes_present", record_summary["missing_train_candidate_tensor_sha256"], 0),
        _expect("train_dp_head_fixed", record_summary["train_dp_head_values"], [FIXED_DP_HEAD]),
        _expect("train_candidate_tensor_not_mutated", record_summary["train_candidate_tensor_mutated_count"], 0),
        _expect("score_expression_affine", review_body.get("score_expression"), PLAN_MODULE.SCORE_EXPRESSION),
        _expect("weights_nonnegative", review_body.get("weights_nonnegative"), True),
        _expect("weights_sum_to_one", review_body.get("weights_sum_to_one"), True),
        _expect("approved_atoms_only", review_body.get("approved_atoms_only"), True),
        _expect("nonnegative_simplex", review_body.get("nonnegative_simplex"), True),
        _expect("no_closed_loop_outcomes_as_training_input", review_body.get("no_closed_loop_outcomes_as_training_input"), True),
        _expect("no_candidate_tensor_mutation", review_body.get("no_candidate_tensor_mutation"), True),
        _expect("no_dp_modification", review_body.get("no_dp_modification"), True),
        _check("training_output_root_absent", not training_output_root.exists(), str(training_output_root), "absent"),
        _check("training_script_exists", training_script.is_file(), str(training_script), "file"),
        _check("training_command_constructed", bool(command), command, "nonempty"),
    ]
    checks.extend(_required_output_checks(review_body.get("planned_outputs", {})))
    checks.extend(_required_stop_condition_checks(review_body.get("stop_conditions", []), plan_body.get("stop_conditions", [])))
    checks.extend(_no_forbidden_work_checks(plan_final, "source_plan"))
    checks.extend(_no_forbidden_work_checks(review_final, "source_static_review"))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifacts": {
                "plan": {
                    "path": str(plan_artifact),
                    "root_sha256": plan_root_sha,
                    "expected_root_sha256": expected_plan_root_sha256,
                    "sha256_entry_count": plan_sha_entries,
                    "failed_sha256s": plan_sha_failures,
                    "sha256s_sha256": _sha256(source_plan_sha256s) if source_plan_sha256s.is_file() else None,
                    "root_sha256s_sha256": _sha256(source_plan_root_sha256s) if source_plan_root_sha256s.is_file() else None,
                },
                "static_review": {
                    "path": str(review_artifact),
                    "root_sha256": review_root_sha,
                    "expected_root_sha256": expected_static_review_root_sha256,
                    "sha256_entry_count": review_sha_entries,
                    "failed_sha256s": review_sha_failures,
                    "sha256s_sha256": _sha256(source_static_review_sha256s) if source_static_review_sha256s.is_file() else None,
                    "root_sha256s_sha256": _sha256(source_static_review_root_sha256s) if source_static_review_root_sha256s.is_file() else None,
                },
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "scaleup_training_preflight": preflight,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "preflight_only": True,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
                "promotion_executed": False,
                "deployment_executed": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "fake_candidate_tensor_generated": False,
            },
        }
    )


def _preflight_summary(
    *,
    plan_root_sha: str | None,
    review_root_sha: str | None,
    review_body: dict[str, Any],
    record_summary: dict[str, Any],
    command: list[str],
    training_output_root: Path,
) -> dict[str, Any]:
    return {
        "source_plan_root_sha256": plan_root_sha,
        "source_static_review_root_sha256": review_root_sha,
        "train_records": record_summary["counts"]["train"],
        "calibration_records": record_summary["counts"]["calibration"],
        "holdout_records": record_summary["counts"]["holdout"],
        "calibration_records_used_for_training": review_body.get("calibration_records_used_for_training"),
        "holdout_records_used_for_training": review_body.get("holdout_records_used_for_training"),
        "scene_zero_overlap": record_summary["scene_zero_overlap"],
        "sample_zero_overlap": record_summary["sample_zero_overlap"],
        "train_k_values": record_summary["train_k_values"],
        "train_candidate_count_values": record_summary["train_candidate_count_values"],
        "missing_train_candidate_tensor_sha256": record_summary["missing_train_candidate_tensor_sha256"],
        "dp_head": FIXED_DP_HEAD,
        "score_expression": review_body.get("score_expression"),
        "weights_nonnegative": review_body.get("weights_nonnegative"),
        "weights_sum_to_one": review_body.get("weights_sum_to_one"),
        "approved_atoms_only": review_body.get("approved_atoms_only"),
        "nonnegative_simplex": review_body.get("nonnegative_simplex"),
        "no_closed_loop_outcomes_as_training_input": review_body.get("no_closed_loop_outcomes_as_training_input"),
        "no_candidate_tensor_mutation": review_body.get("no_candidate_tensor_mutation"),
        "no_dp_modification": review_body.get("no_dp_modification"),
        "planned_outputs": _normalized_outputs(review_body.get("planned_outputs", {})),
        "stop_conditions": _normalized_stop_conditions(review_body.get("stop_conditions", [])),
        "training_output_root": str(training_output_root),
        "training_output_root_absent": not training_output_root.exists(),
        "training_command_template": command,
        "training_command_constructed": bool(command),
        "training_command_executed": False,
    }


def _training_command(
    *,
    python_executable: str,
    training_script: Path,
    train_records: Path,
    training_output_root: Path,
) -> list[str]:
    return [
        python_executable,
        str(training_script),
        "--selection_log",
        str(train_records),
        "--output_dir",
        str(training_output_root),
        "--epochs",
        "1",
    ]


def _record_summary(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    scene_sets = {
        split: {str(record.get("source_scene_id") or record.get("scene_id")) for record in rows}
        for split, rows in records.items()
    }
    sample_sets = {
        split: {str(record.get("source_sample_id") or record.get("sample_id")) for record in rows}
        for split, rows in records.items()
    }
    train = records["train"]
    return {
        "counts": {split: len(records[split]) for split in ("train", "calibration", "holdout")},
        "scene_zero_overlap": _sets_disjoint(scene_sets.values()),
        "sample_zero_overlap": _sets_disjoint(sample_sets.values()),
        "train_k_values": _unique(record.get("K") for record in train),
        "train_candidate_count_values": _unique(record.get("candidate_count") for record in train),
        "train_dp_head_values": _unique(record.get("DP_HEAD") for record in train),
        "missing_train_candidate_tensor_sha256": sum(1 for record in train if not record.get("candidate_tensor_sha256")),
        "train_candidate_tensor_mutated_count": sum(
            1 for record in train if record.get("candidate_tensor_unchanged_by_camp") is not True
        ),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    preflight = report["scaleup_training_preflight"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Scale-Up Training Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source plan root SHA256: `{preflight['source_plan_root_sha256']}`",
            f"- Source static-review root SHA256: `{preflight['source_static_review_root_sha256']}`",
            f"- Train/calibration/holdout records: `{preflight['train_records']} / {preflight['calibration_records']} / {preflight['holdout_records']}`",
            f"- Calibration/holdout used for training: `{preflight['calibration_records_used_for_training']} / {preflight['holdout_records_used_for_training']}`",
            f"- Score expression: `{preflight['score_expression']}`",
            "- Training executed in this gate: `False`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    source = report["source_artifacts"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_PLAN_ROOT_SHA256={source['plan']['root_sha256']}",
            f"SOURCE_STATIC_REVIEW_ROOT_SHA256={source['static_review']['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _required_output_checks(outputs: dict[str, Any]) -> list[dict[str, Any]]:
    required = {
        "model_weights": "static_camp_weights_model.json",
        "config": "scaleup_training_config.json",
        "timing_json": "scaleup_training_timing.json",
        "timing_md": "scaleup_training_timing.md",
        "training_log": "scaleup_training.log",
        "approved_atoms_check": "approved_atoms_check.json",
        "nonnegative_simplex_check": "nonnegative_simplex_check.json",
        "heads": "HEADS",
        "command": "COMMAND",
        "stdout": "stdout.txt",
        "stderr": "stderr.txt",
        "sha256s": "SHA256SUMS",
        "root_sha256s": "ROOT_SHA256SUMS",
    }
    normalized = _normalized_outputs(outputs)
    return [_expect(f"planned_output_{name}", normalized.get(name), expected) for name, expected in required.items()]


def _required_stop_condition_checks(review_conditions: list[str], plan_conditions: list[str]) -> list[dict[str, Any]]:
    normalized = _normalized_stop_conditions([*review_conditions, *plan_conditions])
    required = (
        "dp_head_mismatch",
        "split_overlap",
        "missing_candidate_tensor_hashes",
        "k_or_candidate_count_drift",
        "candidate_tensor_mutation",
        "non_affine_score",
        "non_simplex_weights",
        "calibration_or_holdout_training_use",
    )
    return [
        _check(f"stop_condition_{condition}", condition in normalized, condition if condition in normalized else "missing", condition)
        for condition in required
    ]


def _normalized_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_weights": outputs.get("static_camp_weights_model_artifact"),
        "config": outputs.get("training_config"),
        "timing_json": outputs.get("timing_json"),
        "timing_md": outputs.get("timing_md"),
        "heads": outputs.get("heads"),
        "command": outputs.get("command"),
        "stdout": outputs.get("stdout"),
        "stderr": outputs.get("stderr"),
        "sha256s": outputs.get("sha256s"),
        "root_sha256s": outputs.get("root_sha256s"),
        "training_log": outputs.get("training_log"),
        "approved_atoms_check": outputs.get("approved_atoms_check"),
        "nonnegative_simplex_check": outputs.get("nonnegative_simplex_check"),
    }


def _normalized_stop_conditions(conditions: list[str]) -> list[str]:
    normalized = set()
    for condition in conditions:
        if condition == "k_or_candidate_count_not_8":
            normalized.add("k_or_candidate_count_drift")
        elif condition == "k_or_candidate_count_drift":
            normalized.add("k_or_candidate_count_drift")
        elif condition == "split_overlap":
            normalized.add("split_overlap")
        elif condition in ("missing_candidate_tensor_hashes", "missing_candidate_hashes"):
            normalized.add("missing_candidate_tensor_hashes")
        elif condition == "dp_head_mismatch":
            normalized.add("dp_head_mismatch")
        elif condition in ("calibration_or_holdout_training_use", "calibration_or_holdout_leakage"):
            normalized.add("calibration_or_holdout_training_use")
        elif condition == "non_affine_score":
            normalized.add("non_affine_score")
        elif condition == "non_simplex_weights":
            normalized.add("non_simplex_weights")
    normalized.add("candidate_tensor_mutation")
    return sorted(normalized)


def _no_forbidden_work_checks(final: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _expect(f"{prefix}_{field}_false", final.get(field), False)
        for field in (
            "training_executed",
            "paired_evaluation_executed",
            "performance_claimed",
            "promotion_executed",
            "deployment_executed",
            "dp_modified",
            "candidate_tensor_modified",
            "fake_candidate_tensor_generated",
        )
    ]


def _verify_sha256s(root: Path, manifest: Path) -> tuple[int, list[str]]:
    if not manifest.is_file():
        return 0, ["missing_SHA256SUMS"]
    failed = []
    count = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        count += 1
        expected, rel = line.split(maxsplit=1)
        path = root / rel.strip()
        if not path.is_file() or _sha256(path) != expected:
            failed.append(rel.strip())
    return count, failed


def _write_sha_manifest(output_dir: Path) -> None:
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path in (sha_path, root_path):
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0].split()[0] if lines else None


def _sets_disjoint(sets: Any) -> bool:
    seen: set[Any] = set()
    for values in sets:
        if seen.intersection(values):
            return False
        seen.update(values)
    return True


def _unique(values: Any) -> list[Any]:
    return sorted({_json_key(value): value for value in values}.values(), key=_json_key)


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())

