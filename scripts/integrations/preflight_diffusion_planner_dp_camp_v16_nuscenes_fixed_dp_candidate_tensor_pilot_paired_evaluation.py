#!/usr/bin/env python3
"""Preflight the v16 fixed-DP pilot paired-evaluation gate."""

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
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v16_pilot_paired_eval_plan_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE
FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PLAN_MODULE.SCORE_EXPRESSION
SOURCE_PLAN_SCHEMA_VERSION = PLAN_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_SCHEMA_VERSION = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_READY_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
TRAINING_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_v1"
TRAINING_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_passed"
TRAINING_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution.json"
TRAINING_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution.md"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_execution_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight_v1"
PREFLIGHT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight.json"
PREFLIGHT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight.md"
DEFAULT_EVALUATION_SCRIPT = (
    "scripts/integrations/"
    "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation.py"
)
REQUIRED_METRICS = SOURCE_REVIEW_MODULE.REQUIRED_METRICS


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
    parser.add_argument("--source_training_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_training_json", type=Path, required=True)
    parser.add_argument("--source_training_sha256s", type=Path, required=True)
    parser.add_argument("--source_training_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--evaluation_output_root", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument("--expected_training_root_sha256", required=True)
    parser.add_argument("--python_executable", default=sys.executable)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight",
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
        source_training_artifact_dir=args.source_training_artifact_dir,
        source_training_json=args.source_training_json,
        source_training_sha256s=args.source_training_sha256s,
        source_training_root_sha256s=args.source_training_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        evaluation_output_root=args.evaluation_output_root,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        expected_training_root_sha256=args.expected_training_root_sha256,
        python_executable=args.python_executable,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight,
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
    source_training_artifact_dir: Path,
    source_training_json: Path,
    source_training_sha256s: Path,
    source_training_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    evaluation_output_root: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_plan_root_sha256: str,
    expected_static_review_root_sha256: str,
    expected_training_root_sha256: str,
    python_executable: str = sys.executable,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    plan_artifact = source_plan_artifact_dir.resolve()
    static_artifact = source_static_review_artifact_dir.resolve()
    training_artifact = source_training_artifact_dir.resolve()
    plan = _read_json(source_plan_json)
    static = _read_json(source_static_review_json)
    training = _read_json(source_training_json)
    plan_root_sha = _read_root_sha(source_plan_root_sha256s)
    static_root_sha = _read_root_sha(source_static_review_root_sha256s)
    training_root_sha = _read_root_sha(source_training_root_sha256s)
    plan_sha_entries, plan_sha_failures = _verify_sha256s(plan_artifact, source_plan_sha256s)
    static_sha_entries, static_sha_failures = _verify_sha256s(static_artifact, source_static_review_sha256s)
    training_sha_entries, training_sha_failures = _verify_sha256s(training_artifact, source_training_sha256s)
    split_artifact = Path(training.get("source_artifacts", {}).get("split_execution", {}).get("path", ""))
    split_records = _load_split_records(split_artifact)
    record_summary = _record_summary(split_records)
    plan_body = plan.get("paired_evaluation_preflight_plan", {})
    static_body = static.get("plan_static_review", {})
    training_body = training.get("pilot_training_execution", {})
    training_model = training.get("static_camp_model", {})
    plan_final = plan.get("final_decision", {})
    static_final = static.get("final_decision", {})
    training_final = training.get("final_decision", {})
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8").split("## Current V15 Status", 1)[0]
    command = _evaluation_command(
        python_executable=python_executable,
        plan_artifact=plan_artifact,
        static_artifact=static_artifact,
        training_artifact=training_artifact,
        split_artifact=split_artifact,
        evaluation_output_root=evaluation_output_root,
    )
    preflight = _preflight_summary(
        plan_root_sha=plan_root_sha,
        static_root_sha=static_root_sha,
        training_root_sha=training_root_sha,
        plan_body=plan_body,
        static_body=static_body,
        training_body=training_body,
        training_model=training_model,
        record_summary=record_summary,
        command=command,
        evaluation_output_root=evaluation_output_root,
    )
    checks = [
        _expect("paired_evaluation_preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_paired_eval_preflight", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_paired_eval_preflight", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_static_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_static_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _check("source_plan_artifact_exists", plan_artifact.is_dir(), str(plan_artifact), "directory"),
        _check("source_static_review_artifact_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _check("source_training_artifact_exists", training_artifact.is_dir(), str(training_artifact), "directory"),
        _expect("source_plan_schema", plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", plan.get("status"), PLAN_MODULE.READY_STATUS),
        _expect("source_plan_passed", plan_final.get("passed"), True),
        _expect("source_plan_authorizes_static_review", plan_final.get("authorized_next_work"), SOURCE_CURRENT_WORK),
        _expect("source_plan_root_sha256", plan_root_sha, expected_plan_root_sha256),
        _check("source_plan_sha256s_verified", not plan_sha_failures, plan_sha_failures[:10], []),
        _check("source_plan_sha256s_complete", plan_sha_entries >= 7, plan_sha_entries, ">=7"),
        _expect("source_static_review_schema", static.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("source_static_review_status", static.get("status"), SOURCE_READY_STATUS),
        _expect("source_static_review_passed", static_final.get("passed"), True),
        _expect("source_static_review_authorizes_preflight", static_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_root_sha256", static_root_sha, expected_static_review_root_sha256),
        _expect("source_static_review_links_plan_root", static_body.get("source_plan_root_sha256"), expected_plan_root_sha256),
        _check("source_static_review_sha256s_verified", not static_sha_failures, static_sha_failures[:10], []),
        _check("source_static_review_sha256s_complete", static_sha_entries >= 7, static_sha_entries, ">=7"),
        _expect("source_training_schema", training.get("schema_version"), TRAINING_SCHEMA_VERSION),
        _expect("source_training_status", training.get("status"), TRAINING_READY_STATUS),
        _expect("source_training_passed", training_final.get("passed"), True),
        _expect("source_training_root_sha256", training_root_sha, expected_training_root_sha256),
        _check("source_training_sha256s_verified", not training_sha_failures, training_sha_failures[:10], []),
        _check("source_training_sha256s_complete", training_sha_entries >= 7, training_sha_entries, ">=7"),
        _check("split_execution_artifact_exists", split_artifact.is_dir(), str(split_artifact), "directory"),
        _expect("primary_eval_splits_calibration_holdout", plan_body.get("primary_eval_splits"), ["calibration", "holdout"]),
        _expect("static_primary_eval_splits_calibration_holdout", static_body.get("primary_eval_splits"), ["calibration", "holdout"]),
        _expect("reporting_only_splits_train", plan_body.get("reporting_only_splits"), ["train"]),
        _expect("primary_eval_rows_161", record_summary["primary_eval_rows"], 161),
        _expect("plan_primary_eval_rows_161", plan_body.get("paired_rows_by_split", {}).get("primary_eval_total"), 161),
        _expect("train_reporting_only_rows_863", record_summary["counts"]["train"], PLAN_MODULE.EXPECTED_COUNTS["train"]),
        _expect("calibration_rows_14", record_summary["counts"]["calibration"], PLAN_MODULE.EXPECTED_COUNTS["calibration"]),
        _expect("holdout_rows_147", record_summary["counts"]["holdout"], PLAN_MODULE.EXPECTED_COUNTS["holdout"]),
        _expect("train_excluded_from_primary_eval", "train" not in plan_body.get("primary_eval_splits", []), True),
        _expect("scene_zero_overlap", record_summary["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", record_summary["sample_zero_overlap"], True),
        _expect("k_values_8", record_summary["k_values"], [PLAN_MODULE.EXPECTED_K]),
        _expect("candidate_count_values_8", record_summary["candidate_count_values"], [PLAN_MODULE.EXPECTED_K]),
        _expect("dp_head_values_fixed", record_summary["dp_head_values"], [FIXED_DP_HEAD]),
        _expect("candidate_tensor_sha256_present", record_summary["missing_candidate_tensor_sha256"], 0),
        _expect("candidate_tensor_not_mutated", record_summary["candidate_tensor_mutated_count"], 0),
        _expect("plan_candidate_tensor_hashes_required", static_body.get("pass_fail_conditions", {}).get("candidate_tensor_hashes_present"), True),
        _expect("plan_no_candidate_mutation_required", static_body.get("pass_fail_conditions", {}).get("no_candidate_mutation"), True),
        _expect("score_expression_affine", preflight["score_expression"], SCORE_EXPRESSION),
        _expect("weights_nonnegative", preflight["weights_nonnegative"], True),
        _expect("weights_sum_to_one", preflight["weights_sum_to_one"], True),
        _expect("approved_atoms_only", preflight["approved_atoms_only"], True),
        _expect("affine_simplex_required", static_body.get("pass_fail_conditions", {}).get("affine_simplex_checks_pass"), True),
        _expect("evaluation_output_root_absent", evaluation_output_root.exists(), False),
        _check("evaluation_command_constructed", bool(command), command, "nonempty"),
    ]
    checks.extend(_metric_checks(static_body.get("metrics_planned", [])))
    checks.extend(_no_forbidden_plan_checks(plan_final, "source_plan"))
    checks.extend(_no_forbidden_plan_checks(static_final, "source_static_review"))
    checks.extend(_no_forbidden_training_checks(training_final, "source_training"))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifacts": {
                "plan": _source_artifact(plan_artifact, plan_root_sha, expected_plan_root_sha256, plan_sha_entries, plan_sha_failures, source_plan_sha256s, source_plan_root_sha256s),
                "static_review": _source_artifact(static_artifact, static_root_sha, expected_static_review_root_sha256, static_sha_entries, static_sha_failures, source_static_review_sha256s, source_static_review_root_sha256s),
                "training": _source_artifact(training_artifact, training_root_sha, expected_training_root_sha256, training_sha_entries, training_sha_failures, source_training_sha256s, source_training_root_sha256s),
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_plan_camp_head": plan.get("heads", {}).get("camp_head"),
                "source_static_review_camp_head": static.get("heads", {}).get("camp_head"),
                "source_training_camp_head": training.get("heads", {}).get("camp_head"),
            },
            "pilot_paired_evaluation_preflight": preflight,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "preflight_only": True,
                "evaluation_command_constructed": bool(command),
                "evaluation_executed": False,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
                "safety_claimed": False,
                "camp_over_dp_claimed": False,
                "promotion_executed": False,
                "deployment_executed": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "fake_candidate_tensor_generated": False,
            },
        }
    )


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


def _preflight_summary(
    *,
    plan_root_sha: str | None,
    static_root_sha: str | None,
    training_root_sha: str | None,
    plan_body: dict[str, Any],
    static_body: dict[str, Any],
    training_body: dict[str, Any],
    training_model: dict[str, Any],
    record_summary: dict[str, Any],
    command: list[str],
    evaluation_output_root: Path,
) -> dict[str, Any]:
    return {
        "source_plan_root_sha256": plan_root_sha,
        "source_static_review_root_sha256": static_root_sha,
        "source_training_root_sha256": training_root_sha,
        "primary_eval_splits": plan_body.get("primary_eval_splits"),
        "reporting_only_splits": plan_body.get("reporting_only_splits"),
        "paired_rows_by_split": plan_body.get("paired_rows_by_split"),
        "primary_eval_rows": record_summary["primary_eval_rows"],
        "scene_zero_overlap": record_summary["scene_zero_overlap"],
        "sample_zero_overlap": record_summary["sample_zero_overlap"],
        "k_values": record_summary["k_values"],
        "candidate_count_values": record_summary["candidate_count_values"],
        "missing_candidate_tensor_sha256": record_summary["missing_candidate_tensor_sha256"],
        "candidate_tensor_mutated_count": record_summary["candidate_tensor_mutated_count"],
        "dp_head": FIXED_DP_HEAD,
        "score_expression": training_body.get("score_expression") or training_model.get("score_expression"),
        "weights_nonnegative": training_model.get("weights_nonnegative"),
        "weights_sum_to_one": training_model.get("weights_sum_to_one"),
        "approved_atoms_only": training_model.get("approved_atoms_only"),
        "metrics_planned": static_body.get("metrics_planned", []),
        "pilot_eval_smoke_only": static_body.get("pilot_eval_smoke_only"),
        "claims": static_body.get("claims", {}),
        "evaluation_output_root": str(evaluation_output_root),
        "evaluation_output_root_absent_or_reserved": not evaluation_output_root.exists(),
        "evaluation_command_template": command,
        "evaluation_command_constructed": bool(command),
        "evaluation_command_executed": False,
    }


def _evaluation_command(
    *,
    python_executable: str,
    plan_artifact: Path,
    static_artifact: Path,
    training_artifact: Path,
    split_artifact: Path,
    evaluation_output_root: Path,
) -> list[str]:
    return [
        python_executable,
        DEFAULT_EVALUATION_SCRIPT,
        "--source_plan_artifact_dir",
        str(plan_artifact),
        "--source_static_review_artifact_dir",
        str(static_artifact),
        "--source_training_artifact_dir",
        str(training_artifact),
        "--source_split_execution_artifact_dir",
        str(split_artifact),
        "--eval_splits",
        "calibration,holdout",
        "--output_dir",
        str(evaluation_output_root),
    ]


def _load_split_records(split_artifact: Path) -> dict[str, list[dict[str, Any]]]:
    return {
        "train": _read_jsonl(split_artifact / "train_records.jsonl"),
        "calibration": _read_jsonl(split_artifact / "calibration_records.jsonl"),
        "holdout": _read_jsonl(split_artifact / "holdout_records.jsonl"),
    }


def _record_summary(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    primary = [*records["calibration"], *records["holdout"]]
    all_records = [*records["train"], *primary]
    scene_sets = {split: {str(record.get("scene_id")) for record in rows} for split, rows in records.items()}
    sample_sets = {split: {str(record.get("sample_id")) for record in rows} for split, rows in records.items()}
    return {
        "counts": {split: len(records[split]) for split in ("train", "calibration", "holdout")},
        "primary_eval_rows": len(primary),
        "scene_zero_overlap": _sets_disjoint(scene_sets.values()),
        "sample_zero_overlap": _sets_disjoint(sample_sets.values()),
        "k_values": _unique(record.get("K") for record in all_records),
        "candidate_count_values": _unique(record.get("candidate_count") for record in all_records),
        "dp_head_values": _unique(record.get("DP_HEAD") for record in all_records),
        "missing_candidate_tensor_sha256": sum(1 for record in all_records if not record.get("candidate_tensor_sha256")),
        "candidate_tensor_mutated_count": sum(
            1 for record in all_records if record.get("candidate_tensor_unchanged_by_camp") is not True
        ),
    }


def _metric_checks(metrics: list[str]) -> list[dict[str, Any]]:
    return [_check(f"metric_planned_{metric}", metric in metrics, metrics, metric) for metric in REQUIRED_METRICS]


def _source_artifact(
    artifact: Path,
    root_sha: str | None,
    expected_root_sha: str,
    sha_entries: int,
    sha_failures: list[str],
    sha_path: Path,
    root_sha_path: Path,
) -> dict[str, Any]:
    return {
        "path": str(artifact),
        "root_sha256": root_sha,
        "expected_root_sha256": expected_root_sha,
        "sha256_entry_count": sha_entries,
        "failed_sha256s": sha_failures,
        "sha256s_sha256": _sha256(sha_path) if sha_path.is_file() else None,
        "root_sha256s_sha256": _sha256(root_sha_path) if root_sha_path.is_file() else None,
    }


def _no_forbidden_plan_checks(final: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _expect(f"{prefix}_{field}_false", final.get(field), False)
        for field in (
            "evaluation_executed",
            "training_executed",
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


def _no_forbidden_training_checks(final: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _expect(f"{prefix}_{field}_false", final.get(field), False)
        for field in (
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


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    preflight = report["pilot_paired_evaluation_preflight"]
    rows = preflight["paired_rows_by_split"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Paired-Evaluation Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source plan root SHA256: `{preflight['source_plan_root_sha256']}`",
            f"- Source static-review root SHA256: `{preflight['source_static_review_root_sha256']}`",
            f"- Source training root SHA256: `{preflight['source_training_root_sha256']}`",
            f"- Train/calibration/holdout/primary rows: `{rows.get('train_reporting_only')} / {rows.get('calibration')} / {rows.get('holdout')} / {preflight['primary_eval_rows']}`",
            f"- Score expression: `{preflight['score_expression']}`",
            "- Evaluation executed in this gate: `False`",
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
            f"SOURCE_TRAINING_ROOT_SHA256={source['training']['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


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
    seen: set[str] = set()
    for values in sets:
        if seen.intersection(values):
            return False
        seen.update(values)
    return True


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _unique(values: Any) -> list[Any]:
    return sorted({_json_key(value): value for value in values}.values(), key=_json_key)


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


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
