#!/usr/bin/env python3
"""Review the v16 nuScenes fixed-DP candidate tensor smoke retry result."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_RECORDS = 256
EXPECTED_K = 8
EXPECTED_SHAPE = [EXPECTED_K, 80, 4]
SOURCE_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_v1"
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_passed"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_only"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review.md"
SOURCE_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry.json"
SOURCE_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry.md"
REQUIRED_SOURCE_FILES = (
    SOURCE_JSON_NAME,
    SOURCE_MD_NAME,
    "records.jsonl",
    "HEADS",
    "COMMAND",
    "stdout.txt",
    "stderr.txt",
    "SHA256SUMS",
    "ROOT_SHA256SUMS",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_summary_json", type=Path, required=True)
    parser.add_argument("--source_records_jsonl", type=Path, required=True)
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
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_artifact_dir=args.source_artifact_dir,
        source_summary_json=args.source_summary_json,
        source_records_jsonl=args.source_records_jsonl,
        source_sha256s=args.source_sha256s,
        source_root_sha256s=args.source_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_artifact_dir: Path,
    source_summary_json: Path,
    source_records_jsonl: Path,
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
    records = _read_jsonl(source_records_jsonl)
    sha_entries = _read_sha256s(source_sha256s)
    root_sha = _read_root_sha(source_root_sha256s)
    v16_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    record_review = _record_review(records)
    sha_failures = _verify_sha256s(artifact, sha_entries)
    checks = [
        _expect("result_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", source.get("final_decision", {}).get("passed"), True),
        _expect("source_authorizes_result_review", source.get("final_decision", {}).get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_root_sha256", root_sha, expected_source_root_sha256),
        _check("source_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _contains("audit_authorizes_result_review", v16_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_result_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_retry_passed", v16_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_retry_passed", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_summary_records_256", source.get("record_count"), EXPECTED_RECORDS),
        _expect("source_runner_target_records_256", source.get("runner", {}).get("target_records"), EXPECTED_RECORDS),
        _expect("source_runner_k_8", source.get("runner", {}).get("k"), EXPECTED_K),
        _expect("source_dp_head_fixed", source.get("heads", {}).get("dp_head"), FIXED_DP_HEAD),
        _expect("records_count_256", record_review["record_count"], EXPECTED_RECORDS),
        _expect("records_k_all_8", record_review["k_values"], [EXPECTED_K]),
        _expect("records_candidate_count_all_8", record_review["candidate_count_values"], [EXPECTED_K]),
        _expect("records_dp_head_fixed", record_review["dp_heads"], [FIXED_DP_HEAD]),
        _expect("records_shape_fixed", record_review["candidate_tensor_shapes"], [EXPECTED_SHAPE]),
        _expect("records_candidate_sha_present", record_review["missing_candidate_tensor_sha256"], 0),
        _expect("records_top1_in_range", record_review["top1_out_of_range"], 0),
        _expect("records_adapter_shape_present", record_review["missing_adapter_input_shape"], 0),
        _expect("records_adapter_hash_present", record_review["missing_adapter_input_sha256"], 0),
        _expect("records_scene_sample_present", record_review["missing_scene_or_sample_id"], 0),
        _expect("records_candidate_tensor_not_mutated", record_review["candidate_tensor_mutated_count"], 0),
        _expect("records_exporter_success", record_review["exporter_failure_count"], 0),
    ]
    checks.extend(_source_file_checks(artifact, source_summary_json, source_records_jsonl, source_sha256s, source_root_sha256s))
    checks.extend(_no_forbidden_work_checks(source))
    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review_v1",
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
            "source_artifact": {
                "path": str(artifact),
                "summary_json": str(source_summary_json.resolve()),
                "records_jsonl": str(source_records_jsonl.resolve()),
                "sha256s": str(source_sha256s.resolve()),
                "root_sha256": root_sha,
                "expected_root_sha256": expected_source_root_sha256,
                "sha256_entry_count": len(sha_entries),
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_camp_head": source.get("heads", {}).get("camp_head"),
            },
            "record_review": record_review,
            "timing_summary": _timing_summary(source, records, record_review),
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "result_review_only": True,
                "candidate_generation_executed": False,
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
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    lines = []
    for path in (json_path, md_path, heads_path, command_path):
        lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _record_review(records: list[dict[str, Any]]) -> dict[str, Any]:
    top1_bad = 0
    missing_sha = 0
    missing_shape = 0
    missing_hash = 0
    missing_ids = 0
    mutated = 0
    exporter_failures = 0
    for record in records:
        top1 = record.get("dp_top1_index")
        if isinstance(top1, bool) or not isinstance(top1, int) or not 0 <= top1 < EXPECTED_K:
            top1_bad += 1
        if not record.get("candidate_tensor_sha256"):
            missing_sha += 1
        if not record.get("adapter_input_shape"):
            missing_shape += 1
        if not record.get("adapter_input_sha256"):
            missing_hash += 1
        if not record.get("scene_id") or not record.get("sample_id"):
            missing_ids += 1
        if record.get("candidate_tensor_unchanged_by_camp") is not True:
            mutated += 1
        if record.get("exporter_exit") != 0:
            exporter_failures += 1
    return {
        "record_count": len(records),
        "k_values": _unique(record.get("K") for record in records),
        "candidate_count_values": _unique(record.get("candidate_count") for record in records),
        "dp_heads": _unique(record.get("DP_HEAD") for record in records),
        "candidate_tensor_shapes": _unique(record.get("candidate_tensor_shape") for record in records),
        "top1_values": _unique(record.get("dp_top1_index") for record in records),
        "missing_candidate_tensor_sha256": missing_sha,
        "top1_out_of_range": top1_bad,
        "missing_adapter_input_shape": missing_shape,
        "missing_adapter_input_sha256": missing_hash,
        "missing_scene_or_sample_id": missing_ids,
        "candidate_tensor_mutated_count": mutated,
        "exporter_failure_count": exporter_failures,
        "failure_count": sum(
            value
            for value in (
                missing_sha,
                top1_bad,
                missing_shape,
                missing_hash,
                missing_ids,
                mutated,
                exporter_failures,
            )
        ),
    }


def _timing_summary(source: dict[str, Any], records: list[dict[str, Any]], review: dict[str, Any]) -> dict[str, Any]:
    timings = [float(record["wall_clock_seconds"]) for record in records if _is_number(record.get("wall_clock_seconds"))]
    per_record = {"count": len(timings), "min": None, "max": None, "mean": None}
    if timings:
        per_record = {
            "count": len(timings),
            "min": round(min(timings), 6),
            "max": round(max(timings), 6),
            "mean": round(statistics.fmean(timings), 6),
        }
    return {
        "source_wall_clock_seconds": source.get("wall_clock_seconds"),
        "per_record_seconds": per_record,
        "failure_count": review["failure_count"],
    }


def _source_file_checks(
    artifact: Path,
    source_summary_json: Path,
    source_records_jsonl: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
) -> list[dict[str, Any]]:
    checks = []
    expected_paths = {
        SOURCE_JSON_NAME: source_summary_json.resolve(),
        "records.jsonl": source_records_jsonl.resolve(),
        "SHA256SUMS": source_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_root_sha256s.resolve(),
    }
    for name in REQUIRED_SOURCE_FILES:
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if name in expected_paths:
            checks.append(_expect(f"source_artifact_path_{name}", expected_paths[name], path.resolve()))
    return checks


def _no_forbidden_work_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    final = source.get("final_decision", {})
    runner = source.get("runner", {})
    checks = []
    for field in (
        "training_executed",
        "paired_evaluation_executed",
        "performance_claimed",
        "promotion_executed",
        "deployment_executed",
        "dp_modified",
        "candidate_tensor_modified",
        "fake_candidate_tensor_generated",
    ):
        checks.append(_expect(f"source_final_{field}_false", final.get(field), False))
        checks.append(_expect(f"source_runner_{field}_false", runner.get(field), False))
    return checks


def _verify_sha256s(root: Path, entries: dict[str, str]) -> list[str]:
    failed = []
    for name, expected in entries.items():
        path = root / name
        if not path.is_file():
            failed.append(f"missing:{name}")
            continue
        actual = _sha256(path)
        if actual != expected:
            failed.append(f"mismatch:{name}")
    return failed


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    record_review = report["record_review"]
    timing = report["timing_summary"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Smoke Execution Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source artifact: `{report['source_artifact']['path']}`",
            f"- Source root SHA256: `{report['source_artifact']['root_sha256']}`",
            f"- Records / K / candidate count: `{record_review['record_count']} / {record_review['k_values']} / {record_review['candidate_count_values']}`",
            f"- Candidate tensor shapes: `{record_review['candidate_tensor_shapes']}`",
            f"- Source wall-clock seconds: `{timing['source_wall_clock_seconds']}`",
            f"- Per-record seconds: `{timing['per_record_seconds']}`",
            f"- Failure count: `{timing['failure_count']}`",
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
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_sha256s(path: Path) -> dict[str, str]:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        entries[name.strip()] = digest
    return entries


def _read_root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    line = path.read_text(encoding="utf-8").splitlines()[0]
    return line.split()[0] if line else None


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


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
