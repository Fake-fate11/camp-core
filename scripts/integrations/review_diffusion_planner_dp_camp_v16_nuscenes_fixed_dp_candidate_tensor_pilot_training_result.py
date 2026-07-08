#!/usr/bin/env python3
"""Review the v16 fixed-DP pilot training execution result."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_COUNTS = {"train": 863, "calibration": 14, "holdout": 147}
EXPECTED_K = 8
EXPECTED_ATOM_SCHEMA = "camp_legacy_v1_9d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_v1"
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_passed"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation_preflight_plan_only"
SOURCE_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution.json"
SOURCE_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution.md"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review.md"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_v1"
REQUIRED_SOURCE_FILES = (
    SOURCE_JSON_NAME,
    SOURCE_MD_NAME,
    "static_camp_weights_model.json",
    "pilot_training_config.json",
    "pilot_training_timing.json",
    "pilot_training_timing.md",
    "training_log.jsonl",
    "HEADS",
    "COMMAND",
    "stdout.txt",
    "stderr.txt",
    "run.exit",
    "SHA256SUMS",
    "ROOT_SHA256SUMS",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_summary_json", type=Path, required=True)
    parser.add_argument("--source_sha256s", type=Path, required=True)
    parser.add_argument("--source_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_source_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_artifact_dir=args.source_artifact_dir,
        source_summary_json=args.source_summary_json,
        source_sha256s=args.source_sha256s,
        source_root_sha256s=args.source_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_artifact_dir: Path,
    source_summary_json: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_source_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_artifact_dir.resolve()
    source = _read_json(source_summary_json)
    sha_entries, sha_failures = _verify_sha256s(artifact, source_sha256s)
    root_sha = _read_root_sha(source_root_sha256s)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8").split("## Current V15 Status", 1)[0]
    review = _training_result_review(source)
    final = source.get("final_decision", {})
    checks = [
        _expect("training_result_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", final.get("passed"), True),
        _expect("source_authorizes_result_review", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_root_sha256", root_sha, expected_source_root_sha256),
        _check("source_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _contains("audit_authorizes_result_review", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_result_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_training_execution", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_training_execution", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("train_records_863", review["train_records"], EXPECTED_COUNTS["train"]),
        _expect("calibration_records_14", review["calibration_records"], EXPECTED_COUNTS["calibration"]),
        _expect("holdout_records_147", review["holdout_records"], EXPECTED_COUNTS["holdout"]),
        _expect("calibration_not_used_for_training", review["calibration_records_used_for_training"], 0),
        _expect("holdout_not_used_for_training", review["holdout_records_used_for_training"], 0),
        _expect("scene_zero_overlap", review["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", review["sample_zero_overlap"], True),
        _expect("train_k_values_8", review["train_k_values"], [EXPECTED_K]),
        _expect("train_candidate_count_values_8", review["train_candidate_count_values"], [EXPECTED_K]),
        _expect("source_dp_head_fixed", review["source_dp_head"], FIXED_DP_HEAD),
        _expect("candidate_tensor_not_mutated", review["candidate_tensor_mutated_count"], 0),
        _expect("closed_loop_not_used_for_training", review["closed_loop_outcomes_used_for_training"], False),
        _expect("atom_schema", review["atom_schema_version"], EXPECTED_ATOM_SCHEMA),
        _expect("approved_atoms_only", review["approved_atoms_only"], True),
        _expect("weights_nonnegative", review["weights_nonnegative"], True),
        _expect("weights_sum_to_one", review["weights_sum_to_one"], True),
        _expect("weights_sum", review["weights_sum"], 1.0),
        _expect("score_expression", review["score_expression"], SCORE_EXPRESSION),
        _check("offline_training_wall_clock_recorded", _is_number(review["offline_training_wall_clock_seconds"]), review["offline_training_wall_clock_seconds"], "number"),
        _expect("source_training_executed", final.get("training_executed"), True),
        _expect("source_paired_eval_false", final.get("paired_evaluation_executed"), False),
        _expect("source_claim_false", final.get("performance_claimed"), False),
        _expect("source_promotion_false", final.get("promotion_executed"), False),
        _expect("source_deployment_false", final.get("deployment_executed"), False),
    ]
    checks.extend(_source_file_checks(artifact, source_summary_json, source_sha256s, source_root_sha256s))
    checks.extend(_no_forbidden_work_checks(final, source))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifact": {
                "path": str(artifact),
                "summary_json": str(source_summary_json.resolve()),
                "sha256s": str(source_sha256s.resolve()),
                "root_sha256": root_sha,
                "expected_root_sha256": expected_source_root_sha256,
                "sha256_entry_count": sha_entries,
                "failed_sha256s": sha_failures,
                "sha256s_sha256": _sha256(source_sha256s) if source_sha256s.is_file() else None,
                "root_sha256s_sha256": _sha256(source_root_sha256s) if source_root_sha256s.is_file() else None,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_camp_head": source.get("heads", {}).get("camp_head"),
            },
            "training_result_review": review,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "result_review_only": True,
                "training_executed_by_review": False,
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
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _training_result_review(source: dict[str, Any]) -> dict[str, Any]:
    training = source.get("pilot_training_execution", {})
    record_summary = training.get("record_summary", {})
    atom_summary = training.get("atom_summary", {})
    model = source.get("static_camp_model", {})
    final = source.get("final_decision", {})
    return {
        "train_records": training.get("train_records"),
        "calibration_records": training.get("calibration_records"),
        "holdout_records": training.get("holdout_records"),
        "calibration_records_used_for_training": training.get("calibration_records_used_for_training"),
        "holdout_records_used_for_training": training.get("holdout_records_used_for_training"),
        "scene_zero_overlap": record_summary.get("scene_zero_overlap"),
        "sample_zero_overlap": record_summary.get("sample_zero_overlap"),
        "train_k_values": record_summary.get("train_k_values"),
        "train_candidate_count_values": record_summary.get("train_candidate_count_values"),
        "source_dp_head": source.get("heads", {}).get("dp_head"),
        "candidate_tensor_mutated_count": record_summary.get("train_candidate_tensor_mutated_count"),
        "closed_loop_outcomes_used_for_training": final.get("closed_loop_outcomes_used_for_training"),
        "train_closed_loop_outcome_count": record_summary.get("train_closed_loop_outcome_count"),
        "atom_count": atom_summary.get("atom_count"),
        "atom_schema_version": atom_summary.get("atom_schema_version") or model.get("atom_schema_version"),
        "atom_schema_canonical": atom_summary.get("canonical_schema"),
        "approved_atoms_only": model.get("approved_atoms_only"),
        "weights": model.get("weights"),
        "weights_sum": model.get("weights_sum"),
        "weights_min": model.get("weights_min"),
        "weights_max": model.get("weights_max"),
        "weights_nonnegative": model.get("weights_nonnegative"),
        "weights_sum_to_one": model.get("weights_sum_to_one"),
        "score_expression": model.get("score_expression") or training.get("score_expression"),
        "offline_training_wall_clock_seconds": training.get("offline_training_wall_clock_seconds"),
        "training_start": training.get("training_start"),
        "training_end": training.get("training_end"),
    }


def _source_file_checks(
    artifact: Path,
    source_summary_json: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
) -> list[dict[str, Any]]:
    checks = []
    expected_paths = {
        SOURCE_JSON_NAME: source_summary_json.resolve(),
        "SHA256SUMS": source_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_root_sha256s.resolve(),
    }
    for name in REQUIRED_SOURCE_FILES:
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if name in expected_paths:
            checks.append(_expect(f"source_artifact_path_{name}", expected_paths[name], path.resolve()))
    return checks


def _no_forbidden_work_checks(final: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    training = source.get("pilot_training_execution", {})
    record_summary = training.get("record_summary", {})
    checks = [
        _expect("source_closed_loop_outcomes_used_for_training_false", final.get("closed_loop_outcomes_used_for_training"), False),
        _expect("train_closed_loop_outcome_count_zero", record_summary.get("train_closed_loop_outcome_count"), 0),
    ]
    for field in (
        "paired_evaluation_executed",
        "performance_claimed",
        "promotion_executed",
        "deployment_executed",
        "dp_modified",
        "candidate_tensor_modified",
        "fake_candidate_tensor_generated",
    ):
        checks.append(_expect(f"source_final_{field}_false", final.get(field), False))
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
        name = rel.strip()
        path = root / name
        if not path.is_file():
            failed.append(f"missing:{name}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{name}")
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
    review = report["training_result_review"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Training Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source artifact: `{report['source_artifact']['path']}`",
            f"- Source root SHA256: `{report['source_artifact']['root_sha256']}`",
            f"- Train/calibration/holdout: `{review['train_records']} / {review['calibration_records']} / {review['holdout_records']}`",
            f"- Calibration/holdout used for training: `{review['calibration_records_used_for_training']} / {review['holdout_records_used_for_training']}`",
            f"- K/candidate count: `{review['train_k_values']} / {review['train_candidate_count_values']}`",
            f"- Atom schema/count: `{review['atom_schema_version']} / {review['atom_count']}`",
            f"- Weights sum/min/max: `{review['weights_sum']} / {review['weights_min']} / {review['weights_max']}`",
            f"- Score expression: `{review['score_expression']}`",
            f"- Offline training wall-clock seconds: `{review['offline_training_wall_clock_seconds']}`",
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
            f"SOURCE_CAMP_HEAD={heads['source_camp_head']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
