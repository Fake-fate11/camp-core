#!/usr/bin/env python3
"""Materialize the v16 scale-up corpus scene-level split manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_RESULT_REVIEW_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_v1"
SOURCE_RESULT_REVIEW_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_passed"
SOURCE_RESULT_REVIEW_AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_only"
SOURCE_PLAN_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_v1"
SOURCE_PLAN_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_ready"
SOURCE_PLAN_AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_only"
SOURCE_STATIC_REVIEW_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_v1"
SOURCE_STATIC_REVIEW_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_passed"
SOURCE_STATIC_REVIEW_AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_only"
SOURCE_PREFLIGHT_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_v1"
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_ready"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_passed"
FAILED_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_failed"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_v1"

SOURCE_RESULT_REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review.json"
SOURCE_RESULT_REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review.md"
SOURCE_PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan.json"
SOURCE_PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan.md"
SOURCE_STATIC_REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review.json"
SOURCE_STATIC_REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review.md"
SOURCE_PREFLIGHT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight.json"
SOURCE_PREFLIGHT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight.md"
REPORT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution.json"
REPORT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution.md"

EXPECTED_RECORDS = 10000
EXPECTED_SCENES = 50
EXPECTED_SCENE_COUNTS = {"train": 30, "calibration": 10, "holdout": 10}
EXPECTED_RECORD_COUNTS = {"train": 6263, "calibration": 2156, "holdout": 1581}
EXPECTED_K = 8
SPLIT_JSONL_NAMES = {
    "train": "train_records.jsonl",
    "calibration": "calibration_records.jsonl",
    "holdout": "holdout_records.jsonl",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_result_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_json", type=Path, required=True)
    parser.add_argument("--source_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--source_preflight_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_corpus_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_corpus_sha256s", type=Path, required=True)
    parser.add_argument("--source_corpus_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_result_review_root_sha256", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument("--expected_preflight_root_sha256", required=True)
    parser.add_argument("--expected_corpus_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_sha256s=args.source_result_review_sha256s,
        source_result_review_root_sha256s=args.source_result_review_root_sha256s,
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_sha256s=args.source_plan_sha256s,
        source_plan_root_sha256s=args.source_plan_root_sha256s,
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_static_review_root_sha256s=args.source_static_review_root_sha256s,
        source_preflight_artifact_dir=args.source_preflight_artifact_dir,
        source_preflight_json=args.source_preflight_json,
        source_preflight_sha256s=args.source_preflight_sha256s,
        source_preflight_root_sha256s=args.source_preflight_root_sha256s,
        source_corpus_artifact_dir=args.source_corpus_artifact_dir,
        source_records_jsonl=args.source_records_jsonl,
        source_corpus_sha256s=args.source_corpus_sha256s,
        source_corpus_root_sha256s=args.source_corpus_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_result_review_root_sha256=args.expected_result_review_root_sha256,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        expected_corpus_root_sha256=args.expected_corpus_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution,
    )
    report["command"] = sys.argv
    if not args.output_dir.exists():
        write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_sha256s: Path,
    source_result_review_root_sha256s: Path,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_sha256s: Path,
    source_plan_root_sha256s: Path,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_sha256s: Path,
    source_static_review_root_sha256s: Path,
    source_preflight_artifact_dir: Path,
    source_preflight_json: Path,
    source_preflight_sha256s: Path,
    source_preflight_root_sha256s: Path,
    source_corpus_artifact_dir: Path,
    source_records_jsonl: Path,
    source_corpus_sha256s: Path,
    source_corpus_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_result_review_root_sha256: str,
    expected_plan_root_sha256: str,
    expected_static_review_root_sha256: str,
    expected_preflight_root_sha256: str,
    expected_corpus_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    output_root_absent = not output_dir.exists()
    result_review = _read_json(source_result_review_json)
    plan = _read_json(source_plan_json)
    static_review = _read_json(source_static_review_json)
    preflight = _read_json(source_preflight_json)
    records = _read_jsonl(source_records_jsonl)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    source_artifacts = {
        "result_review": _source_artifact(
            source_result_review_artifact_dir,
            source_result_review_sha256s,
            source_result_review_root_sha256s,
            expected_result_review_root_sha256,
        ),
        "split_plan": _source_artifact(
            source_plan_artifact_dir,
            source_plan_sha256s,
            source_plan_root_sha256s,
            expected_plan_root_sha256,
        ),
        "static_review": _source_artifact(
            source_static_review_artifact_dir,
            source_static_review_sha256s,
            source_static_review_root_sha256s,
            expected_static_review_root_sha256,
        ),
        "preflight": _source_artifact(
            source_preflight_artifact_dir,
            source_preflight_sha256s,
            source_preflight_root_sha256s,
            expected_preflight_root_sha256,
        ),
        "corpus": _source_artifact(
            source_corpus_artifact_dir,
            source_corpus_sha256s,
            source_corpus_root_sha256s,
            expected_corpus_root_sha256,
        ),
    }
    assignments = _scene_assignments(plan)
    split_records = _split_records(records, assignments)
    split_summary = _split_summary(split_records, assignments, output_root_absent)
    result_final = result_review.get("final_decision", {})
    plan_final = plan.get("final_decision", {})
    static_final = static_review.get("final_decision", {})
    preflight_final = preflight.get("final_decision", {})
    plan_split = plan.get("split_plan", {})
    static_split = static_review.get("plan_review", {})
    preflight_split = preflight.get("preflight", {})
    result_record_review = result_review.get("record_review", {})

    checks = [
        _expect("split_execution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_split_execution", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_split_execution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_preflight", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_preflight", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("output_root_absent", output_root_absent, True),
        _expect("result_review_schema", result_review.get("schema_version"), SOURCE_RESULT_REVIEW_SCHEMA_VERSION),
        _expect("result_review_status", result_review.get("status"), SOURCE_RESULT_REVIEW_READY_STATUS),
        _expect("result_review_passed", result_final.get("passed"), True),
        _expect("result_review_authorizes_split_plan", result_final.get("authorized_next_work"), SOURCE_RESULT_REVIEW_AUTHORIZED_NEXT_WORK),
        _expect("plan_schema", plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("plan_status", plan.get("status"), SOURCE_PLAN_READY_STATUS),
        _expect("plan_passed", plan_final.get("passed"), True),
        _expect("plan_authorizes_static_review", plan_final.get("authorized_next_work"), SOURCE_PLAN_AUTHORIZED_NEXT_WORK),
        _expect("static_review_schema", static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA_VERSION),
        _expect("static_review_status", static_review.get("status"), SOURCE_STATIC_REVIEW_READY_STATUS),
        _expect("static_review_passed", static_final.get("passed"), True),
        _expect("static_review_authorizes_preflight", static_final.get("authorized_next_work"), SOURCE_STATIC_REVIEW_AUTHORIZED_NEXT_WORK),
        _expect("preflight_schema", preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA_VERSION),
        _expect("preflight_status", preflight.get("status"), SOURCE_READY_STATUS),
        _expect("preflight_passed", preflight_final.get("passed"), True),
        _expect("preflight_authorizes_execution", preflight_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_result_review_records", result_record_review.get("record_count"), EXPECTED_RECORDS),
        _expect("source_result_review_scenes", result_record_review.get("distinct_scene_count"), EXPECTED_SCENES),
        _expect("source_result_review_unique_samples", result_record_review.get("unique_sample_count"), EXPECTED_RECORDS),
        _expect("records_count_10000", split_summary["records"], EXPECTED_RECORDS),
        _expect("scenes_count_50", split_summary["scenes"], EXPECTED_SCENES),
        _expect("unique_samples_10000", split_summary["unique_samples"], EXPECTED_RECORDS),
        _expect("scene_counts_30_10_10", split_summary["scene_counts"], EXPECTED_SCENE_COUNTS),
        _expect("record_counts_6263_2156_1581", split_summary["record_counts"], EXPECTED_RECORD_COUNTS),
        _expect("plan_scene_counts_match", plan_split.get("planned_scene_counts"), EXPECTED_SCENE_COUNTS),
        _expect("plan_record_counts_match", plan_split.get("planned_record_counts"), EXPECTED_RECORD_COUNTS),
        _expect("static_scene_counts_match", static_split.get("planned_scene_counts"), EXPECTED_SCENE_COUNTS),
        _expect("static_record_counts_match", static_split.get("planned_record_counts"), EXPECTED_RECORD_COUNTS),
        _expect("preflight_scene_counts_match", preflight_split.get("planned_scene_counts"), EXPECTED_SCENE_COUNTS),
        _expect("preflight_record_counts_match", preflight_split.get("planned_record_counts"), EXPECTED_RECORD_COUNTS),
        _expect("scene_zero_overlap", split_summary["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", split_summary["sample_zero_overlap"], True),
        _expect("record_level_hard_split_not_executed", split_summary["record_level_hard_split_executed"], False),
        _expect("k_values_8", split_summary["k_values"], [EXPECTED_K]),
        _expect("candidate_count_values_8", split_summary["candidate_count_values"], [EXPECTED_K]),
        _expect("records_all_dp_head_fixed", split_summary["dp_head_values"], [FIXED_DP_HEAD]),
        _expect("candidate_tensor_not_mutated", split_summary["candidate_tensor_mutated_count"], 0),
        _expect("unassigned_records_zero", split_summary["unassigned_record_count"], 0),
        _expect("training_uses_train_only", plan_split.get("followup_policy", {}).get("training"), "train split only"),
        _expect("paired_eval_uses_calibration_holdout", plan_split.get("followup_policy", {}).get("paired_eval_primary"), "calibration+holdout"),
        _expect("plan_record_level_hard_split_not_executed", plan_split.get("record_level_hard_split_executed"), False),
        _expect("static_record_level_hard_split_not_executed", static_split.get("record_level_hard_split_executed"), False),
        _expect("preflight_record_level_hard_split_not_executed", preflight_split.get("record_level_hard_split_executed"), False),
    ]
    checks.extend(
        _check(
            f"source_{name}_sha256s_verified",
            artifact["sha256s_verified"] and artifact["root_sha256"] == artifact["expected_root_sha256"],
            artifact,
            "verified source artifact",
        )
        for name, artifact in source_artifacts.items()
    )
    checks.extend(_no_forbidden_work_checks(result_final, "source_result_review"))
    checks.extend(_no_forbidden_work_checks(plan_final, "source_plan"))
    checks.extend(_no_forbidden_work_checks(static_final, "source_static_review"))
    checks.extend(_no_forbidden_work_checks(preflight_final, "source_preflight"))

    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else FAILED_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifacts": source_artifacts,
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "split_execution": split_summary,
            "split_records": split_records,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else FAILED_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "split_execution_only": True,
                "split_execution_executed": passed,
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
    for split, name in SPLIT_JSONL_NAMES.items():
        (output_dir / name).write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in report["split_records"][split]),
            encoding="utf-8",
        )
    (output_dir / "split_manifest.json").write_text(
        json.dumps(report["split_execution"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {key: value for key, value in report.items() if key != "split_records"}
    (output_dir / REPORT_JSON_NAME).write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / REPORT_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", []), sort_keys=True) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _scene_assignments(plan: dict[str, Any]) -> dict[str, list[str]]:
    assignments = plan.get("split_plan", {}).get("scene_assignments", {})
    return {split: [str(scene) for scene in assignments.get(split, [])] for split in ("train", "calibration", "holdout")}


def _split_records(records: list[dict[str, Any]], assignments: dict[str, list[str]]) -> dict[str, list[dict[str, Any]]]:
    scene_to_split = {scene: split for split, scenes in assignments.items() for scene in scenes}
    split_records = {split: [] for split in ("train", "calibration", "holdout")}
    split_records["_unassigned"] = []
    for record in records:
        scene = str(record.get("source_scene_id") or record.get("scene_id"))
        split = scene_to_split.get(scene)
        if split is None:
            split_records["_unassigned"].append(record)
        else:
            split_records[split].append(record)
    return split_records


def _split_summary(
    split_records: dict[str, list[dict[str, Any]]],
    assignments: dict[str, list[str]],
    output_root_absent: bool,
) -> dict[str, Any]:
    ordered_splits = ("train", "calibration", "holdout")
    assigned_records = [record for split in ordered_splits for record in split_records[split]]
    sample_sets = {
        split: {str(record.get("source_sample_id") or record.get("sample_id")) for record in split_records[split]}
        for split in ordered_splits
    }
    scene_sets = {
        split: {str(record.get("source_scene_id") or record.get("scene_id")) for record in split_records[split]}
        for split in ordered_splits
    }
    assignment_sets = {split: set(assignments[split]) for split in ordered_splits}
    return {
        "records": len(assigned_records),
        "scenes": len(set().union(*scene_sets.values())) if scene_sets else 0,
        "unique_samples": len(set().union(*sample_sets.values())) if sample_sets else 0,
        "scene_assignments": assignments,
        "scene_counts": {split: len(scene_sets[split]) for split in ordered_splits},
        "record_counts": {split: len(split_records[split]) for split in ordered_splits},
        "scene_zero_overlap": _sets_disjoint(scene_sets.values()) and _sets_disjoint(assignment_sets.values()),
        "sample_zero_overlap": _sets_disjoint(sample_sets.values()),
        "record_level_hard_split_executed": False,
        "k_values": _unique(record.get("K") for record in assigned_records),
        "candidate_count_values": _unique(record.get("candidate_count") for record in assigned_records),
        "dp_head_values": _unique(record.get("DP_HEAD") for record in assigned_records),
        "candidate_tensor_mutated_count": sum(
            1
            for record in assigned_records
            if record.get("candidate_tensor_unchanged_by_camp") is not True
            or (
                "candidate_tensor_pre_sha256" in record
                and "candidate_tensor_post_sha256" in record
                and record.get("candidate_tensor_pre_sha256") != record.get("candidate_tensor_post_sha256")
            )
        ),
        "unassigned_record_count": len(split_records["_unassigned"]),
        "output_root_absent_at_start": output_root_absent,
        "split_manifest_materialized": True,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "performance_claimed": False,
        "promotion_executed": False,
        "deployment_executed": False,
    }


def _source_artifact(root: Path, sha256s: Path, root_sha256s: Path, expected_root_sha: str) -> dict[str, Any]:
    root_resolved = root.resolve()
    entries, failed = _verify_sha256s(root_resolved, sha256s)
    root_sha = _read_root_sha(root_sha256s)
    return {
        "path": str(root_resolved),
        "exists": root_resolved.is_dir(),
        "sha256_entry_count": entries,
        "failed_sha256s": failed,
        "sha256s_verified": root_resolved.is_dir() and sha256s.is_file() and not failed,
        "root_sha256": root_sha,
        "expected_root_sha256": expected_root_sha,
        "root_sha256s_sha256": _sha256(root_sha256s) if root_sha256s.is_file() else None,
        "sha256s_sha256": _sha256(sha256s) if sha256s.is_file() else None,
    }


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
        if not path.is_file():
            failed.append(f"missing:{rel.strip()}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{rel.strip()}")
    return count, failed


def _no_forbidden_work_checks(final: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
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


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    split = report["split_execution"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Split Execution",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Records / scenes: `{split['records']} / {split['scenes']}`",
            f"- Scene counts: `{split['scene_counts']}`",
            f"- Record counts: `{split['record_counts']}`",
            f"- Scene zero-overlap: `{split['scene_zero_overlap']}`",
            f"- Sample zero-overlap: `{split['sample_zero_overlap']}`",
            "- Boundary: split manifest only; no training, paired evaluation, claim, promotion, or deployment.",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    artifacts = report["source_artifacts"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_RESULT_REVIEW_ROOT_SHA256={artifacts['result_review']['root_sha256']}",
            f"SOURCE_PLAN_ROOT_SHA256={artifacts['split_plan']['root_sha256']}",
            f"SOURCE_STATIC_REVIEW_ROOT_SHA256={artifacts['static_review']['root_sha256']}",
            f"SOURCE_PREFLIGHT_ROOT_SHA256={artifacts['preflight']['root_sha256']}",
            f"SOURCE_CORPUS_ROOT_SHA256={artifacts['corpus']['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _write_sha_manifest(output_dir: Path) -> None:
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path not in (sha_path, root_path):
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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _sets_disjoint(sets: Any) -> bool:
    seen: set[Any] = set()
    for values in sets:
        if seen.intersection(values):
            return False
        seen.update(values)
    return True


def _unique(values: Any) -> list[Any]:
    return sorted({value for value in values})


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


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
