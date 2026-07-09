#!/usr/bin/env python3
"""Review the v16 fixed-DP candidate tensor scale-up execution result."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations import (  # noqa: E402
    review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_result as base,
)


FIXED_DP_HEAD = base.FIXED_DP_HEAD
EXPECTED_RECORDS = 10000
EXPECTED_DISTINCT_SCENES = 50
MINIMUM_DISTINCT_SCENES = 30
MAX_RECORDS_PER_SCENE = 334
EXPECTED_K = base.EXPECTED_K
EXPECTED_SHAPE = [EXPECTED_K, 80, 4]
SOURCE_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_v1"
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution_passed"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_v1"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review.md"
SOURCE_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution.json"
SOURCE_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution.md"
REQUIRED_SOURCE_FILES = (
    SOURCE_JSON_NAME,
    SOURCE_MD_NAME,
    "records.jsonl",
    "scene_distribution.json",
    "timing.json",
    "timing.md",
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
    parser.add_argument("--source_scene_distribution_json", type=Path, required=True)
    parser.add_argument("--source_timing_json", type=Path, required=True)
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
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_artifact_dir=args.source_artifact_dir,
        source_summary_json=args.source_summary_json,
        source_records_jsonl=args.source_records_jsonl,
        source_scene_distribution_json=args.source_scene_distribution_json,
        source_timing_json=args.source_timing_json,
        source_sha256s=args.source_sha256s,
        source_root_sha256s=args.source_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review,
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
    source_scene_distribution_json: Path,
    source_timing_json: Path,
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
    patch = {
        "EXPECTED_RECORDS": EXPECTED_RECORDS,
        "EXPECTED_K": EXPECTED_K,
        "EXPECTED_SHAPE": EXPECTED_SHAPE,
        "SOURCE_SCHEMA_VERSION": SOURCE_SCHEMA_VERSION,
        "SOURCE_READY_STATUS": SOURCE_READY_STATUS,
        "AUTHORIZED_CURRENT_WORK": AUTHORIZED_CURRENT_WORK,
        "READY_STATUS": READY_STATUS,
        "REJECT_STATUS": REJECT_STATUS,
        "AUTHORIZED_NEXT_WORK": AUTHORIZED_NEXT_WORK,
        "SOURCE_JSON_NAME": SOURCE_JSON_NAME,
        "SOURCE_MD_NAME": SOURCE_MD_NAME,
        "REQUIRED_SOURCE_FILES": REQUIRED_SOURCE_FILES,
    }
    old = {name: getattr(base, name) for name in patch}
    try:
        for name, value in patch.items():
            setattr(base, name, value)
        report = base.build_report(
            source_artifact_dir=source_artifact_dir,
            source_summary_json=source_summary_json,
            source_records_jsonl=source_records_jsonl,
            source_sha256s=source_sha256s,
            source_root_sha256s=source_root_sha256s,
            v16_audit_md=v16_audit_md,
            current_status_md=current_status_md,
            output_dir=Path("."),
            current_camp_head=current_camp_head,
            current_camp_origin_main=current_camp_origin_main,
            current_dp_head=current_dp_head,
            expected_source_root_sha256=expected_source_root_sha256,
            enabled=enabled,
        )
    finally:
        for name, value in old.items():
            setattr(base, name, value)

    source = base._read_json(source_summary_json)
    records = base._read_jsonl(source_records_jsonl)
    scene_distribution = base._read_json(source_scene_distribution_json)
    timing = base._read_json(source_timing_json)
    for check in report["checks"]:
        check["name"] = check["name"].replace("_256", "_10000")
    record_review = _scaleup_record_review(records, scene_distribution)
    report["schema_version"] = SCHEMA_VERSION
    base_failure_count = report["record_review"]["failure_count"]
    report["record_review"].update(record_review)
    scaleup_failure_count = (
        report["record_review"]["duplicate_sample_count"]
        + report["record_review"]["scene_count_over_cap"]
        + report["record_review"]["fake_or_synthetic_candidate_tensor_count"]
        + (0 if report["record_review"]["scene_distribution_matches_records"] else 1)
    )
    report["record_review"]["failure_count"] = base_failure_count + scaleup_failure_count
    report["scene_distribution_review"] = _scene_distribution_review(scene_distribution)
    report["timing_summary"] = _scaleup_timing_summary(source, timing, records, report["record_review"])
    report["source_artifact"]["scene_distribution_json"] = str(source_scene_distribution_json.resolve())
    report["source_artifact"]["timing_json"] = str(source_timing_json.resolve())
    report["source_artifact"]["root_sha256s_sha256"] = (
        base._sha256(source_root_sha256s) if source_root_sha256s.is_file() else None
    )

    checks = report["checks"]
    checks.extend(
        [
            base._expect("source_runner_target_records_10000", source.get("runner", {}).get("target_records"), EXPECTED_RECORDS),
            base._expect("source_summary_distinct_scenes_50", source.get("scene_distribution", {}).get("distinct_scene_count"), EXPECTED_DISTINCT_SCENES),
            base._check(
                "source_summary_distinct_scenes_at_least_30",
                source.get("scene_distribution", {}).get("distinct_scene_count") >= MINIMUM_DISTINCT_SCENES,
                source.get("scene_distribution", {}).get("distinct_scene_count"),
                ">=30",
            ),
            base._expect("records_distinct_scenes_50", record_review["distinct_scene_count"], EXPECTED_DISTINCT_SCENES),
            base._expect("records_unique_samples_10000", record_review["unique_sample_count"], EXPECTED_RECORDS),
            base._expect("records_scene_count_over_cap", record_review["scene_count_over_cap"], 0),
            base._expect("records_scene_distribution_matches_source", record_review["scene_distribution_matches_records"], True),
            base._expect(
                "records_no_fake_or_synthetic_candidate_tensors",
                record_review["fake_or_synthetic_candidate_tensor_count"],
                0,
            ),
            base._expect("records_failure_count_0", report["record_review"]["failure_count"], 0),
            base._expect("scene_distribution_distinct_scenes_50", report["scene_distribution_review"]["distinct_scene_count"], EXPECTED_DISTINCT_SCENES),
            base._expect("scene_distribution_over_cap", report["scene_distribution_review"]["scene_count_over_cap"], 0),
            base._expect("timing_wall_clock_recorded", report["timing_summary"]["source_wall_clock_seconds"], source.get("wall_clock_seconds")),
            base._expect("timing_per_record_count_10000", report["timing_summary"]["per_record_seconds"].get("count"), EXPECTED_RECORDS),
        ]
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    report["status"] = READY_STATUS if passed else REJECT_STATUS
    report["authorized_next_work"] = AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK
    report["final_decision"] = {
        "passed": passed,
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failed_checks": failed,
        "check_count": len(checks),
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
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
    }
    return base._stable(report)


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(base._render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    rows = [f"{base._sha256(path)}  {path.name}" for path in (json_path, md_path, heads_path, command_path)]
    sha_path = output_dir / "SHA256SUMS"
    sha_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    (output_dir / "ROOT_SHA256SUMS").write_text(f"{base._sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _scaleup_record_review(records: list[dict[str, Any]], scene_distribution: dict[str, Any]) -> dict[str, Any]:
    scene_counts: dict[str, int] = {}
    samples = set()
    synthetic_count = 0
    for record in records:
        scene = record.get("source_scene_id") or record.get("scene_id")
        sample = record.get("source_sample_id") or record.get("sample_id")
        if scene:
            scene_counts[str(scene)] = scene_counts.get(str(scene), 0) + 1
        if sample:
            samples.add(str(sample))
        provenance = json.dumps(record.get("provenance", {}), sort_keys=True).lower()
        if "fake" in provenance or "synthetic" in provenance:
            synthetic_count += 1
    max_seen = max(scene_counts.values(), default=0)
    return {
        "distinct_scene_count": len(scene_counts),
        "unique_sample_count": len(samples),
        "duplicate_sample_count": len(records) - len(samples),
        "max_records_per_scene": max_seen,
        "scene_count_over_cap": sum(1 for count in scene_counts.values() if count > MAX_RECORDS_PER_SCENE),
        "scene_distribution_matches_records": scene_distribution.get("scene_counts") == dict(sorted(scene_counts.items())),
        "fake_or_synthetic_candidate_tensor_count": synthetic_count,
        "failure_count": 0,
    }


def _scene_distribution_review(scene_distribution: dict[str, Any]) -> dict[str, Any]:
    counts = scene_distribution.get("scene_counts", {})
    return {
        "distinct_scene_count": scene_distribution.get("distinct_scene_count"),
        "max_records_per_scene": scene_distribution.get("max_records_per_scene"),
        "scene_count_over_cap": sum(1 for count in counts.values() if count > MAX_RECORDS_PER_SCENE),
    }


def _scaleup_timing_summary(
    source: dict[str, Any],
    timing: dict[str, Any],
    records: list[dict[str, Any]],
    review: dict[str, Any],
) -> dict[str, Any]:
    summary = base._timing_summary(source, records, review)
    summary["source_wall_clock_seconds"] = timing.get("wall_clock_seconds", summary["source_wall_clock_seconds"])
    summary["per_record_seconds"] = timing.get("per_record_seconds", summary["per_record_seconds"])
    return summary


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["record_review"]
    timing = report["timing_summary"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source artifact: `{report['source_artifact']['path']}`",
            f"- Source root SHA256: `{report['source_artifact']['root_sha256']}`",
            f"- Records / scenes / unique samples: `{review['record_count']} / {review['distinct_scene_count']} / {review['unique_sample_count']}`",
            f"- K / candidate count: `{review['k_values']} / {review['candidate_count_values']}`",
            f"- Candidate tensor shapes: `{review['candidate_tensor_shapes']}`",
            f"- Source wall-clock seconds: `{timing['source_wall_clock_seconds']}`",
            f"- Per-record seconds: `{timing['per_record_seconds']}`",
            f"- Failure count: `{review['failure_count']}`",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
