#!/usr/bin/env python3
"""Plan the v16 scale-up corpus scene-level train/calibration/holdout split."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_v1"
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review_passed"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_v1"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan.md"
SOURCE_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review.json"
SOURCE_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result_review.md"
EXPECTED_RECORDS = 10000
EXPECTED_SCENES = 50
EXPECTED_K = 8
TARGET_SCENE_COUNTS = {"train": 30, "calibration": 10, "holdout": 10}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_result_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_corpus_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_scene_distribution_json", type=Path, required=True)
    parser.add_argument("--source_corpus_sha256s", type=Path, required=True)
    parser.add_argument("--source_corpus_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_source_root_sha256", required=True)
    parser.add_argument("--expected_source_corpus_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan",
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
        source_corpus_artifact_dir=args.source_corpus_artifact_dir,
        source_records_jsonl=args.source_records_jsonl,
        source_scene_distribution_json=args.source_scene_distribution_json,
        source_corpus_sha256s=args.source_corpus_sha256s,
        source_corpus_root_sha256s=args.source_corpus_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        expected_source_corpus_root_sha256=args.expected_source_corpus_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_sha256s: Path,
    source_result_review_root_sha256s: Path,
    source_corpus_artifact_dir: Path,
    source_records_jsonl: Path,
    source_scene_distribution_json: Path,
    source_corpus_sha256s: Path,
    source_corpus_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_source_root_sha256: str,
    expected_source_corpus_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    review_artifact = source_result_review_artifact_dir.resolve()
    corpus_artifact = source_corpus_artifact_dir.resolve()
    source = _read_json(source_result_review_json)
    records = _read_jsonl(source_records_jsonl)
    scene_distribution = _read_json(source_scene_distribution_json)
    source_final = source.get("final_decision", {})
    source_review = source.get("record_review", {})
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    review_root = _read_root_sha(source_result_review_root_sha256s)
    corpus_root = _read_root_sha(source_corpus_root_sha256s)
    review_sha_count, review_sha_failures = _verify_sha256s(review_artifact, source_result_review_sha256s)
    corpus_sha_count, corpus_sha_failures = _verify_sha256s(corpus_artifact, source_corpus_sha256s)
    split_plan = _split_plan(records, scene_distribution)
    checks = [
        _expect("split_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_result_review_artifact_exists", review_artifact.is_dir(), str(review_artifact), "directory"),
        _check("source_corpus_artifact_exists", corpus_artifact.is_dir(), str(corpus_artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", source_final.get("passed"), True),
        _expect("source_authorizes_split_plan", source_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_result_review_root_sha256", review_root, expected_source_root_sha256),
        _expect("source_corpus_root_sha256", corpus_root, expected_source_corpus_root_sha256),
        _check("source_result_review_sha256s_verified", not review_sha_failures, review_sha_failures[:10], []),
        _check("source_corpus_sha256s_verified", not corpus_sha_failures, corpus_sha_failures[:10], []),
        _contains("audit_authorizes_split_plan", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_split_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_result_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_result_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_review_records_10000", source_review.get("record_count"), EXPECTED_RECORDS),
        _expect("records_count_10000", len(records), EXPECTED_RECORDS),
        _expect("source_review_distinct_scenes_50", source_review.get("distinct_scene_count"), EXPECTED_SCENES),
        _expect("records_distinct_scenes_50", split_plan["source_scene_count"], EXPECTED_SCENES),
        _expect("source_review_unique_samples_10000", source_review.get("unique_sample_count"), EXPECTED_RECORDS),
        _expect("records_unique_samples_10000", split_plan["source_unique_sample_count"], EXPECTED_RECORDS),
        _expect("scene_distribution_distinct_scenes_50", scene_distribution.get("distinct_scene_count"), EXPECTED_SCENES),
        _expect("target_train_scenes_30", split_plan["planned_scene_counts"]["train"], 30),
        _expect("target_calibration_scenes_10", split_plan["planned_scene_counts"]["calibration"], 10),
        _expect("target_holdout_scenes_10", split_plan["planned_scene_counts"]["holdout"], 10),
        _expect("scene_zero_overlap", split_plan["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", split_plan["sample_zero_overlap"], True),
        _expect("planned_record_level_hard_split_not_executed", split_plan["record_level_hard_split_executed"], False),
        _expect(
            "record_level_hard_split_not_executed",
            source.get("split_plan", {}).get("record_level_hard_split_executed", False),
            False,
        ),
        _expect("k_values_8", split_plan["k_values"], [EXPECTED_K]),
        _expect("candidate_count_values_8", split_plan["candidate_count_values"], [EXPECTED_K]),
        _expect("dp_head_fixed_records", split_plan["dp_head_values"], [FIXED_DP_HEAD]),
        _expect("candidate_tensor_not_mutated", split_plan["candidate_tensor_mutated_count"], 0),
        _expect("source_review_failure_count_0", source_review.get("failure_count"), 0),
    ]
    checks.extend(_source_file_checks(review_artifact, source_result_review_json, source_result_review_sha256s, source_result_review_root_sha256s))
    checks.extend(_source_corpus_file_checks(corpus_artifact, source_records_jsonl, source_scene_distribution_json, source_corpus_sha256s, source_corpus_root_sha256s))
    checks.extend(_no_forbidden_work_checks(source_final))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_result_review_artifact": {
                "path": str(review_artifact),
                "json": str(source_result_review_json.resolve()),
                "root_sha256": review_root,
                "expected_root_sha256": expected_source_root_sha256,
                "sha256_entry_count": review_sha_count,
                "failed_sha256s": review_sha_failures,
            },
            "source_corpus_artifact": {
                "path": str(corpus_artifact),
                "records_jsonl": str(source_records_jsonl.resolve()),
                "scene_distribution_json": str(source_scene_distribution_json.resolve()),
                "root_sha256": corpus_root,
                "expected_root_sha256": expected_source_corpus_root_sha256,
                "sha256_entry_count": corpus_sha_count,
                "failed_sha256s": corpus_sha_failures,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_dp_head": source.get("heads", {}).get("dp_head"),
            },
            "split_plan": split_plan,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "split_plan_only": True,
                "split_executed": False,
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
    command_path.write_text(json.dumps(report.get("command", []), sort_keys=True) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _split_plan(records: list[dict[str, Any]], scene_distribution: dict[str, Any]) -> dict[str, Any]:
    scenes = sorted({str(record.get("source_scene_id") or record.get("scene_id")) for record in records})
    assignments = {
        "train": scenes[: TARGET_SCENE_COUNTS["train"]],
        "calibration": scenes[TARGET_SCENE_COUNTS["train"] : TARGET_SCENE_COUNTS["train"] + TARGET_SCENE_COUNTS["calibration"]],
        "holdout": scenes[TARGET_SCENE_COUNTS["train"] + TARGET_SCENE_COUNTS["calibration"] :],
    }
    scene_to_split = {scene: split for split, values in assignments.items() for scene in values}
    records_by_split = {"train": [], "calibration": [], "holdout": []}
    for record in records:
        scene = str(record.get("source_scene_id") or record.get("scene_id"))
        records_by_split[scene_to_split[scene]].append(record)
    scene_sets = {split: set(values) for split, values in assignments.items()}
    sample_sets = {
        split: {str(record.get("source_sample_id") or record.get("sample_id")) for record in values}
        for split, values in records_by_split.items()
    }
    scene_counts = scene_distribution.get("scene_counts", {})
    return {
        "source_records": len(records),
        "source_scene_count": len(scenes),
        "source_unique_sample_count": len(set().union(*sample_sets.values())) if sample_sets else 0,
        "target_ratio": "60/20/20",
        "target_scene_counts": TARGET_SCENE_COUNTS,
        "planned_scene_counts": {split: len(assignments[split]) for split in ("train", "calibration", "holdout")},
        "planned_record_counts": {split: len(records_by_split[split]) for split in ("train", "calibration", "holdout")},
        "scene_assignments": assignments,
        "scene_zero_overlap": _sets_disjoint(scene_sets.values()),
        "sample_zero_overlap": _sets_disjoint(sample_sets.values()),
        "record_level_hard_split_executed": False,
        "record_count_exact_60_20_20_required": False,
        "scene_distribution_counts": {scene: scene_counts.get(scene) for scene in scenes},
        "k_values": _unique(record.get("K") for record in records),
        "candidate_count_values": _unique(record.get("candidate_count") for record in records),
        "dp_head_values": _unique(record.get("DP_HEAD") for record in records),
        "candidate_tensor_mutated_count": sum(
            1 for record in records if record.get("candidate_tensor_unchanged_by_camp") is not True
        ),
        "followup_policy": {
            "training": "train split only",
            "paired_eval_primary": "calibration+holdout",
            "claim": "blocked until result review and scale sufficiency checks",
        },
    }


def _source_file_checks(
    artifact: Path,
    source_json: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
) -> list[dict[str, Any]]:
    expected = {
        SOURCE_JSON_NAME: source_json.resolve(),
        "SHA256SUMS": source_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_root_sha256s.resolve(),
    }
    checks = []
    for name in (SOURCE_JSON_NAME, SOURCE_MD_NAME, "HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", "SHA256SUMS", "ROOT_SHA256SUMS"):
        path = artifact / name
        checks.append(_check(f"source_result_review_has_{name}", path.is_file(), str(path), "file"))
        if name in expected:
            checks.append(_expect(f"source_result_review_path_{name}", expected[name], path.resolve()))
    return checks


def _source_corpus_file_checks(
    artifact: Path,
    records_jsonl: Path,
    scene_distribution_json: Path,
    sha256s: Path,
    root_sha256s: Path,
) -> list[dict[str, Any]]:
    expected = {
        "records.jsonl": records_jsonl.resolve(),
        "scene_distribution.json": scene_distribution_json.resolve(),
        "SHA256SUMS": sha256s.resolve(),
        "ROOT_SHA256SUMS": root_sha256s.resolve(),
    }
    checks = []
    for name in (
        "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution.json",
        "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution.md",
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
    ):
        path = artifact / name
        checks.append(_check(f"source_corpus_has_{name}", path.is_file(), str(path), "file"))
        if name in expected:
            checks.append(_expect(f"source_corpus_path_{name}", expected[name], path.resolve()))
    return checks


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [_expect("source_result_review_only", final.get("result_review_only"), True)]
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
    ):
        checks.append(_expect(f"source_{field}_false", final.get(field), False))
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
        if not path.is_file():
            failed.append(f"missing:{rel.strip()}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{rel.strip()}")
    return count, failed


def _write_sha_manifest(output_dir: Path) -> None:
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path not in (sha_path, root_path):
            rows.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    split = report["split_plan"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Split Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Planned scene counts: `{split['planned_scene_counts']}`",
            f"- Planned record counts: `{split['planned_record_counts']}`",
            "- Policy: scene-level zero-overlap, no record-level hard split.",
            "- Follow-up: training uses train only; paired evaluation uses calibration+holdout; no claim until result review and scale sufficiency checks.",
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
            f"SOURCE_RESULT_REVIEW_ROOT_SHA256={report['source_result_review_artifact']['root_sha256']}",
            f"SOURCE_CORPUS_ROOT_SHA256={report['source_corpus_artifact']['root_sha256']}",
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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _sets_disjoint(values: Any) -> bool:
    seen = set()
    for value in values:
        if seen & value:
            return False
        seen.update(value)
    return True


def _unique(values: Any) -> list[Any]:
    return sorted({_json_key(value): value for value in values}.values(), key=_json_key)


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


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
