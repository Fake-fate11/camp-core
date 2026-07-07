#!/usr/bin/env python3
"""Plan the v16 fixed-DP pilot corpus train/calibration/holdout split."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_v1"
)
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_passed"
AUTHORIZED_CURRENT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_only"
)
READY_STATUS = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_ready"
)
REJECT_STATUS = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_static_review_only"
)
SOURCE_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review.json"
SOURCE_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review.md"
PLAN_JSON_NAME = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan.json"
)
PLAN_MD_NAME = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan.md"
)
SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_v1"
)
EXPECTED_RECORDS = 1024
EXPECTED_K = 8
EXPECTED_SHAPE = [[8, 80, 4]]
SPLIT_COUNTS = {"train": 614, "calibration": 205, "holdout": 205}
SPLIT_RATIOS = {"train": 0.6, "calibration": 0.2, "holdout": 0.2}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_result_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_source_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan",
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
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan,
    )
    report["command"] = vars(args)
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_sha256s: Path,
    source_result_review_root_sha256s: Path,
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
    artifact = source_result_review_artifact_dir.resolve()
    source = _read_json(source_result_review_json)
    root_sha = _read_root_sha(source_result_review_root_sha256s)
    sha_entries = _read_sha256s(source_result_review_sha256s)
    sha_failures = _verify_sha256s(artifact, sha_entries)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    final = source.get("final_decision", {})
    record_review = source.get("record_review", {})
    timing = source.get("timing_summary", {})
    source_artifact = source.get("source_artifact", {})

    checks = [
        _expect("split_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", final.get("passed"), True),
        _expect("source_authorizes_split_plan", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_root_sha256", root_sha, expected_source_root_sha256),
        _check("source_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _contains("audit_authorizes_split_plan", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_split_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_result_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_result_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("record_count_1024", record_review.get("record_count"), EXPECTED_RECORDS),
        _expect("k_values_8", record_review.get("k_values"), [EXPECTED_K]),
        _expect("candidate_count_8", record_review.get("candidate_count_values"), [EXPECTED_K]),
        _expect("candidate_tensor_shape_fixed", record_review.get("candidate_tensor_shapes"), EXPECTED_SHAPE),
        _expect("failure_count_zero", record_review.get("failure_count"), 0),
        _expect("exporter_failure_count_zero", record_review.get("exporter_failure_count"), 0),
        _expect("candidate_tensor_not_mutated", record_review.get("candidate_tensor_mutated_count"), 0),
        _expect("top1_in_range", record_review.get("top1_out_of_range"), 0),
        _expect("source_sha_entries_4105", source_artifact.get("sha256_entry_count"), 4105),
        _expect("split_counts_sum_to_records", sum(SPLIT_COUNTS.values()), EXPECTED_RECORDS),
        _expect("split_ratio_sum", round(sum(SPLIT_RATIOS.values()), 6), 1.0),
    ]
    checks.extend(_no_forbidden_work_checks(final))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed

    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "source_result_review_artifact": {
                "path": str(artifact),
                "json": str(source_result_review_json.resolve()),
                "root_sha256": root_sha,
                "expected_root_sha256": expected_source_root_sha256,
                "sha256_entry_count": len(sha_entries),
                "pilot_execution_artifact": source_artifact.get("path"),
                "pilot_execution_root_sha256": source_artifact.get("root_sha256"),
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_camp_head": source.get("heads", {}).get("camp_head"),
                "source_pilot_execution_camp_head": source.get("heads", {}).get("source_camp_head"),
            },
            "source_record_review": record_review,
            "source_timing_summary": timing,
            "split_plan": _split_plan(),
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
                "split_plan_only": True,
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
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", {}), sort_keys=True) + "\n", encoding="utf-8")
    paths = (json_path, md_path, heads_path, command_path)
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in paths),
        encoding="utf-8",
    )


def _split_plan() -> dict[str, Any]:
    return {
        "source_records": EXPECTED_RECORDS,
        "ratios": SPLIT_RATIOS,
        "target_record_counts": SPLIT_COUNTS,
        "assignment_policy": {
            "split_unit": "scene_id_primary_sample_id_fallback",
            "stable_sort_key": "sha256(split_salt + scene_id_or_sample_id)",
            "split_salt": "camp_v16_nuscenes_fixed_dp_pilot_corpus_split_v1",
            "tie_breakers": ["scene_id", "sample_id", "record_index"],
        },
        "zero_overlap_requirements": {
            "scene_overlap_allowed": False,
            "sample_overlap_allowed": False,
            "candidate_tensor_sha_overlap_allowed": False,
            "adapter_input_sha_overlap_allowed": False,
            "record_identity_overlap_allowed": False,
        },
        "split_roles": {
            "train": "fit CAMP selector weights only",
            "calibration": "tune selector thresholds or regularization only",
            "holdout": "sealed reporting split; no training or tuning",
        },
        "holdout_policy": {
            "training_from_holdout_authorized": False,
            "calibration_from_holdout_authorized": False,
            "promotion_claim_from_holdout_authorized": False,
            "holdout_consumption_requires_future_gate": True,
        },
        "expansion_preconditions": {
            "10k": [
                "pilot_split_execution_result_review_passed",
                "scene_sample_candidate_tensor_zero_overlap_verified",
                "DP_HEAD_fixed",
                "failure_count_zero",
                "no_training_on_holdout",
            ],
            "32k": [
                "10k_corpus_result_review_passed",
                "10k_train_calibration_holdout_split_review_passed",
                "wall_clock_budget_reconfirmed",
                "no_10k_holdout_consumption_for_training",
            ],
        },
    }


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    split = report["split_plan"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Corpus Split Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source records: `{split['source_records']}`",
            f"- Target split counts: `{split['target_record_counts']}`",
            f"- Split unit: `{split['assignment_policy']['split_unit']}`",
            f"- Source result review artifact: `{report['source_result_review_artifact']['path']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    source = report["source_result_review_artifact"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_RESULT_REVIEW_ROOT_SHA256={source['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect(f"source_result_review_{field}_false", final.get(field), False)
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


def _verify_sha256s(root: Path, entries: dict[str, str]) -> list[str]:
    failed = []
    for name, expected in entries.items():
        path = root / name
        if not path.is_file():
            failed.append(f"missing:{name}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{name}")
    return failed


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sha256s(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        entries[Path(name.strip()).as_posix()] = digest
    return entries


def _read_root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0].split()[0] if lines else None


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
