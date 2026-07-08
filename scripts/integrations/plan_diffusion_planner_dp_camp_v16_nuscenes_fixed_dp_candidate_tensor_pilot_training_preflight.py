#!/usr/bin/env python3
"""Plan the v16 fixed-DP pilot candidate-tensor training preflight."""

from __future__ import annotations

import argparse
import hashlib
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


SOURCE_REVIEW_MODULE = _load_module(
    "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result.py",
    "v16_pilot_corpus_split_result_review",
)
SPLIT_EXECUTION_MODULE = SOURCE_REVIEW_MODULE.SOURCE_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
EXPECTED_COUNTS = SOURCE_REVIEW_MODULE.EXPECTED_COUNTS
EXPECTED_K = SOURCE_REVIEW_MODULE.EXPECTED_K
SOURCE_REVIEW_SCHEMA_VERSION = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_READY_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
SOURCE_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK
SPLIT_EXECUTION_SCHEMA_VERSION = SPLIT_EXECUTION_MODULE.SCHEMA_VERSION
SPLIT_EXECUTION_READY_STATUS = SPLIT_EXECUTION_MODULE.READY_STATUS
SPLIT_EXECUTION_JSON_NAME = SPLIT_EXECUTION_MODULE.REPORT_JSON_NAME
SPLIT_EXECUTION_MD_NAME = SPLIT_EXECUTION_MODULE.REPORT_MD_NAME
PILOT_CORPUS_ROOT_SHA = "57779ea5d6aa2d9f1e7a5962cbbd551238ec1500136bd82e972714d479da7432"
PILOT_CORPUS_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_candidates_"
    "mini_train_d799ada8_20260708T013202CST"
)
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_v1"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan.md"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_split_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_split_result_review_json", type=Path, required=True)
    parser.add_argument("--source_split_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_split_result_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_split_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_split_execution_json", type=Path, required=True)
    parser.add_argument("--source_train_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_calibration_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_holdout_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_split_execution_sha256s", type=Path, required=True)
    parser.add_argument("--source_split_execution_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_split_result_review_root_sha256", required=True)
    parser.add_argument("--expected_split_execution_root_sha256", required=True)
    parser.add_argument("--score_expression", default=SCORE_EXPRESSION)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_split_result_review_artifact_dir=args.source_split_result_review_artifact_dir,
        source_split_result_review_json=args.source_split_result_review_json,
        source_split_result_review_sha256s=args.source_split_result_review_sha256s,
        source_split_result_review_root_sha256s=args.source_split_result_review_root_sha256s,
        source_split_execution_artifact_dir=args.source_split_execution_artifact_dir,
        source_split_execution_json=args.source_split_execution_json,
        source_train_records_jsonl=args.source_train_records_jsonl,
        source_calibration_records_jsonl=args.source_calibration_records_jsonl,
        source_holdout_records_jsonl=args.source_holdout_records_jsonl,
        source_split_execution_sha256s=args.source_split_execution_sha256s,
        source_split_execution_root_sha256s=args.source_split_execution_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_split_result_review_root_sha256=args.expected_split_result_review_root_sha256,
        expected_split_execution_root_sha256=args.expected_split_execution_root_sha256,
        score_expression=args.score_expression,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_split_result_review_artifact_dir: Path,
    source_split_result_review_json: Path,
    source_split_result_review_sha256s: Path,
    source_split_result_review_root_sha256s: Path,
    source_split_execution_artifact_dir: Path,
    source_split_execution_json: Path,
    source_train_records_jsonl: Path,
    source_calibration_records_jsonl: Path,
    source_holdout_records_jsonl: Path,
    source_split_execution_sha256s: Path,
    source_split_execution_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_split_result_review_root_sha256: str,
    expected_split_execution_root_sha256: str,
    score_expression: str = SCORE_EXPRESSION,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    review_artifact = source_split_result_review_artifact_dir.resolve()
    split_artifact = source_split_execution_artifact_dir.resolve()
    review = _read_json(source_split_result_review_json)
    split_execution = _read_json(source_split_execution_json)
    records = {
        "train": _read_jsonl(source_train_records_jsonl),
        "calibration": _read_jsonl(source_calibration_records_jsonl),
        "holdout": _read_jsonl(source_holdout_records_jsonl),
    }
    review_sha_entries, review_sha_failures = _verify_sha256s(review_artifact, source_split_result_review_sha256s)
    split_sha_entries, split_sha_failures = _verify_sha256s(split_artifact, source_split_execution_sha256s)
    review_root_sha = _read_root_sha(source_split_result_review_root_sha256s)
    split_root_sha = _read_root_sha(source_split_execution_root_sha256s)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8").split("## Current V15 Status", 1)[0]
    review_decision = review.get("final_decision", {})
    split_decision = split_execution.get("final_decision", {})
    split_summary = review.get("split_result_review", {})
    source_artifacts = split_execution.get("source_artifacts", {})
    plan = _training_preflight_plan(
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
        review_artifact=review_artifact,
        review_root_sha=review_root_sha,
        split_artifact=split_artifact,
        split_root_sha=split_root_sha,
        split_execution=split_execution,
        records=records,
        score_expression=score_expression,
    )
    record_checks = _record_checks(records)
    checks = [
        _expect("pilot_training_preflight_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("split_result_review_artifact_exists", review_artifact.is_dir(), str(review_artifact), "directory"),
        _check("split_execution_artifact_exists", split_artifact.is_dir(), str(split_artifact), "directory"),
        _expect("split_result_review_schema", review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("split_result_review_status", review.get("status"), SOURCE_READY_STATUS),
        _expect("split_result_review_passed", review_decision.get("passed"), True),
        _expect("split_result_review_authorizes_plan", review_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("split_execution_schema", split_execution.get("schema_version"), SPLIT_EXECUTION_SCHEMA_VERSION),
        _expect("split_execution_status", split_execution.get("status"), SPLIT_EXECUTION_READY_STATUS),
        _expect("split_execution_passed", split_decision.get("passed"), True),
        _expect("split_execution_authorized_review", split_decision.get("authorized_next_work"), SOURCE_CURRENT_WORK),
        _expect("split_result_review_root_sha256", review_root_sha, expected_split_result_review_root_sha256),
        _expect("split_execution_root_sha256", split_root_sha, expected_split_execution_root_sha256),
        _check("split_result_review_sha256s_verified", not review_sha_failures, review_sha_failures[:10], []),
        _check("split_execution_sha256s_verified", not split_sha_failures, split_sha_failures[:10], []),
        _contains("audit_authorizes_plan", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_split_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_split_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("review_train_records_863", split_summary.get("counts", {}).get("train"), EXPECTED_COUNTS["train"]),
        _expect("review_calibration_records_14", split_summary.get("counts", {}).get("calibration"), EXPECTED_COUNTS["calibration"]),
        _expect("review_holdout_records_147", split_summary.get("counts", {}).get("holdout"), EXPECTED_COUNTS["holdout"]),
        _expect("review_scene_zero_overlap", split_summary.get("scene_zero_overlap"), True),
        _expect("review_sample_zero_overlap", split_summary.get("sample_zero_overlap"), True),
        _expect("review_k_values", split_summary.get("k_values"), [EXPECTED_K]),
        _expect("review_candidate_count_values", split_summary.get("candidate_count_values"), [EXPECTED_K]),
        _expect("review_dp_head_values", split_summary.get("dp_head_values"), [FIXED_DP_HEAD]),
        _expect("review_candidate_tensor_not_mutated", split_summary.get("candidate_tensor_mutated_count"), 0),
        _expect("review_performance_claim_unsupported", split_summary.get("performance_claim_supported"), False),
        _expect("train_records_863", record_checks["counts"]["train"], EXPECTED_COUNTS["train"]),
        _expect("calibration_records_not_used_for_training", review_decision.get("calibration_records_used_for_training", 0), 0),
        _expect("holdout_records_not_used_for_training", review_decision.get("holdout_records_used_for_training", 0), 0),
        _expect("calibration_records_not_used_for_training", plan["training_inputs"]["calibration_records_used_for_training"], 0),
        _expect("holdout_records_not_used_for_training", plan["training_inputs"]["holdout_records_used_for_training"], 0),
        _expect("candidate_tensor_hashes_present", record_checks["missing_candidate_tensor_sha256"], 0),
        _expect("record_k_values", record_checks["k_values"], [EXPECTED_K]),
        _expect("record_candidate_count_values", record_checks["candidate_count_values"], [EXPECTED_K]),
        _expect("record_dp_head_values", record_checks["dp_head_values"], [FIXED_DP_HEAD]),
        _expect("record_candidate_tensor_not_mutated", record_checks["candidate_tensor_mutated_count"], 0),
        _expect("score_expression_affine", plan["math_contract"]["score_expression"], SCORE_EXPRESSION),
        _expect("weights_nonnegative", plan["math_contract"]["weights_nonnegative"], True),
        _expect("weights_sum_to_one", plan["math_contract"]["weights_sum_to_one"], True),
        _expect("approved_atoms_only", plan["math_contract"]["approved_atoms_only"], True),
        _expect("pilot_corpus_artifact", plan["training_inputs"]["pilot_corpus_artifact"], source_artifacts.get("pilot_corpus", {}).get("path")),
        _expect("pilot_corpus_root_sha256", plan["training_inputs"]["pilot_corpus_root_sha256"], PILOT_CORPUS_ROOT_SHA),
    ]
    checks.extend(_no_forbidden_work_checks(review_decision, "split_review"))
    checks.extend(_no_forbidden_work_checks(split_decision, "split_execution"))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifacts": {
                "split_result_review": {
                    "path": str(review_artifact),
                    "root_sha256": review_root_sha,
                    "expected_root_sha256": expected_split_result_review_root_sha256,
                    "sha256_entry_count": review_sha_entries,
                    "failed_sha256s": review_sha_failures,
                    "sha256s_sha256": _sha256(source_split_result_review_sha256s) if source_split_result_review_sha256s.is_file() else None,
                    "root_sha256s_sha256": _sha256(source_split_result_review_root_sha256s) if source_split_result_review_root_sha256s.is_file() else None,
                },
                "split_execution": {
                    "path": str(split_artifact),
                    "root_sha256": split_root_sha,
                    "expected_root_sha256": expected_split_execution_root_sha256,
                    "sha256_entry_count": split_sha_entries,
                    "failed_sha256s": split_sha_failures,
                    "sha256s_sha256": _sha256(source_split_execution_sha256s) if source_split_execution_sha256s.is_file() else None,
                    "root_sha256s_sha256": _sha256(source_split_execution_root_sha256s) if source_split_execution_root_sha256s.is_file() else None,
                },
                "pilot_corpus": {
                    "path": plan["training_inputs"]["pilot_corpus_artifact"],
                    "root_sha256": plan["training_inputs"]["pilot_corpus_root_sha256"],
                },
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "pilot_training_preflight_plan": plan,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "pilot_training_preflight_plan_executed": True,
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


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _training_preflight_plan(
    *,
    current_camp_head: str,
    current_dp_head: str,
    review_artifact: Path,
    review_root_sha: str | None,
    split_artifact: Path,
    split_root_sha: str | None,
    split_execution: dict[str, Any],
    records: dict[str, list[dict[str, Any]]],
    score_expression: str,
) -> dict[str, Any]:
    source_artifacts = split_execution.get("source_artifacts", {})
    pilot = source_artifacts.get("pilot_corpus", {})
    train_records = len(records["train"])
    return {
        "camp_head": current_camp_head,
        "fixed_dp_head": current_dp_head,
        "training_scope": "pilot_smoke_training_only_no_performance_claim",
        "training_inputs": {
            "split_result_review_artifact": str(review_artifact),
            "split_result_review_root_sha256": review_root_sha,
            "split_execution_artifact": str(split_artifact),
            "split_execution_root_sha256": split_root_sha,
            "pilot_corpus_artifact": pilot.get("path") or PILOT_CORPUS_ARTIFACT,
            "pilot_corpus_root_sha256": pilot.get("root_sha256"),
            "dp_head": current_dp_head,
            "candidate_tensor_schema": {
                "k": EXPECTED_K,
                "candidate_count": EXPECTED_K,
                "candidate_tensor_shape": [EXPECTED_K, 80, 4],
            },
            "training_splits": ["train"],
            "forbidden_training_splits": ["calibration", "holdout"],
            "train_records": train_records,
            "calibration_records_available": len(records["calibration"]),
            "holdout_records_available": len(records["holdout"]),
            "calibration_records_used_for_training": 0,
            "holdout_records_used_for_training": 0,
        },
        "planned_outputs": {
            "static_camp_weights_model_artifact": "static_camp_weights_model.json",
            "training_config": "pilot_training_config.json",
            "timing_json": "pilot_training_timing.json",
            "timing_md": "pilot_training_timing.md",
            "affine_scoring_check": "affine_scoring_check.json",
            "nonnegative_simplex_check": "nonnegative_simplex_check.json",
            "approved_atoms_check": "approved_atoms_check.json",
            "heads": "HEADS",
            "command": "COMMAND",
            "stdout": "stdout.txt",
            "stderr": "stderr.txt",
            "sha256s": "SHA256SUMS",
        },
        "math_contract": {
            "score_expression": score_expression,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
            "approved_atoms_only": True,
            "nonnegative_simplex": True,
        },
        "pass_conditions": {
            "train_records": EXPECTED_COUNTS["train"],
            "calibration_records_used_for_training": 0,
            "holdout_records_used_for_training": 0,
            "score_expression": SCORE_EXPRESSION,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
            "dp_unchanged": True,
            "candidate_tensor_mutated_count": 0,
        },
        "stop_conditions": [
            "split_overlap",
            "missing_candidate_tensor_hashes",
            "k_or_candidate_count_not_8",
            "dp_head_mismatch",
            "calibration_or_holdout_training_use",
            "non_affine_score",
            "non_simplex_weights",
        ],
    }


def _record_checks(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    all_records = [record for split in ("train", "calibration", "holdout") for record in records[split]]
    return {
        "counts": {split: len(records[split]) for split in ("train", "calibration", "holdout")},
        "missing_candidate_tensor_sha256": sum(1 for record in all_records if not record.get("candidate_tensor_sha256")),
        "k_values": _unique(record.get("K") for record in all_records),
        "candidate_count_values": _unique(record.get("candidate_count") for record in all_records),
        "dp_head_values": _unique(record.get("DP_HEAD") for record in all_records),
        "candidate_tensor_mutated_count": sum(
            1 for record in all_records if record.get("candidate_tensor_unchanged_by_camp") is not True
        ),
    }


def _no_forbidden_work_checks(final: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    checks = [
        _expect(f"{prefix}_{field}_false", final.get(field), False)
        for field in (
            "candidate_generation_executed",
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
    checks.append(_expect(f"{prefix}_holdout_records_used_for_training_false", final.get("holdout_records_used_for_training", 0), 0))
    checks.append(_expect(f"{prefix}_calibration_records_used_for_training_false", final.get("calibration_records_used_for_training", 0), 0))
    return checks


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


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["pilot_training_preflight_plan"]
    inputs = plan["training_inputs"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Training Preflight Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- Scope: pilot smoke training plan only; no training, evaluation, or performance claim.",
            f"- Train/calibration/holdout records: `{inputs['train_records']} / {inputs['calibration_records_available']} / {inputs['holdout_records_available']}`",
            f"- Training splits: `{inputs['training_splits']}`",
            f"- Forbidden training splits: `{inputs['forbidden_training_splits']}`",
            f"- Score expression: `{plan['math_contract']['score_expression']}`",
            f"- Static weights constraints: nonnegative `{plan['math_contract']['weights_nonnegative']}`, sum-to-one `{plan['math_contract']['weights_sum_to_one']}`",
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
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


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


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unique(values: Any) -> list[Any]:
    return sorted({_json_key(value): value for value in values}.values(), key=_json_key)


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


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
