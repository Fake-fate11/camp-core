#!/usr/bin/env python3
"""Review the v16 fixed-DP candidate tensor pilot generation result."""

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
EXPECTED_RECORDS = 1024
EXPECTED_K = base.EXPECTED_K
EXPECTED_SHAPE = [EXPECTED_K, 80, 4]
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_v1"
)
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_passed"
AUTHORIZED_CURRENT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_only"
)
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_rejected"
AUTHORIZED_NEXT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_only"
)
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review.md"
SOURCE_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution.json"
SOURCE_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution.md"
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
SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_v1"
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
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review",
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
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(**kwargs: Any) -> dict[str, Any]:
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
        report = base.build_report(**kwargs)
    finally:
        for name, value in old.items():
            setattr(base, name, value)
    report["schema_version"] = SCHEMA_VERSION
    return report


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
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    record_review = report["record_review"]
    timing = report["timing_summary"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Pilot Generation Result Review",
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


if __name__ == "__main__":
    raise SystemExit(main())
