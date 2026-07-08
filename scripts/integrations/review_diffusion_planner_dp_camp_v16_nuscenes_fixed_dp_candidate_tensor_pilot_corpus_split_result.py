#!/usr/bin/env python3
"""Review the v16 fixed-DP pilot corpus split execution result."""

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


SOURCE_MODULE = _load_module(
    "split_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus.py",
    "v16_pilot_corpus_split_execution",
)

FIXED_DP_HEAD = SOURCE_MODULE.FIXED_DP_HEAD
EXPECTED_RECORDS = SOURCE_MODULE.EXPECTED_RECORDS
EXPECTED_K = SOURCE_MODULE.EXPECTED_K
EXPECTED_COUNTS = SOURCE_MODULE.EXPECTED_COUNTS
EXPECTED_ASSIGNMENTS = SOURCE_MODULE.EXPECTED_ASSIGNMENTS
SOURCE_SCHEMA_VERSION = SOURCE_MODULE.SCHEMA_VERSION
SOURCE_READY_STATUS = SOURCE_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result_review_v1"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result_review.md"
SOURCE_JSON_NAME = SOURCE_MODULE.REPORT_JSON_NAME
SOURCE_MD_NAME = SOURCE_MODULE.REPORT_MD_NAME
SPLIT_JSONL_NAMES = SOURCE_MODULE.SPLIT_JSONL_NAMES
REQUIRED_SOURCE_FILES = (
    SOURCE_JSON_NAME,
    SOURCE_MD_NAME,
    "split_manifest.json",
    SPLIT_JSONL_NAMES["train"],
    SPLIT_JSONL_NAMES["calibration"],
    SPLIT_JSONL_NAMES["holdout"],
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
    parser.add_argument("--source_split_manifest_json", type=Path, required=True)
    parser.add_argument("--source_train_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_calibration_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_holdout_records_jsonl", type=Path, required=True)
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
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_artifact_dir=args.source_artifact_dir,
        source_summary_json=args.source_summary_json,
        source_split_manifest_json=args.source_split_manifest_json,
        source_train_records_jsonl=args.source_train_records_jsonl,
        source_calibration_records_jsonl=args.source_calibration_records_jsonl,
        source_holdout_records_jsonl=args.source_holdout_records_jsonl,
        source_sha256s=args.source_sha256s,
        source_root_sha256s=args.source_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_artifact_dir: Path,
    source_summary_json: Path,
    source_split_manifest_json: Path,
    source_train_records_jsonl: Path,
    source_calibration_records_jsonl: Path,
    source_holdout_records_jsonl: Path,
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
    manifest = _read_json(source_split_manifest_json)
    records_by_split = {
        "train": _read_jsonl(source_train_records_jsonl),
        "calibration": _read_jsonl(source_calibration_records_jsonl),
        "holdout": _read_jsonl(source_holdout_records_jsonl),
    }
    sha_entries, sha_failures = _verify_sha256s(artifact, source_sha256s)
    root_sha = _read_root_sha(source_root_sha256s)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8").split("## Current V15 Status", 1)[0]
    review = _split_result_review(records_by_split, manifest)
    source_split = source.get("split_execution", {})
    source_final = source.get("final_decision", {})
    checks = [
        _expect("split_result_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", source_final.get("passed"), True),
        _expect("source_authorizes_result_review", source_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_root_sha256", root_sha, expected_source_root_sha256),
        _check("source_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _contains("audit_authorizes_result_review", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_result_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_split_execution", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_split_execution", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_summary_total_records", source_split.get("total_records"), EXPECTED_RECORDS),
        _expect("source_summary_counts", source_split.get("counts"), EXPECTED_COUNTS),
        _expect("source_summary_scene_assignments", source_split.get("scene_assignments"), EXPECTED_ASSIGNMENTS),
        _expect("source_summary_scene_zero_overlap", source_split.get("scene_zero_overlap"), True),
        _expect("source_summary_sample_zero_overlap", source_split.get("sample_zero_overlap"), True),
        _expect("source_summary_k_values", source_split.get("k_values"), [EXPECTED_K]),
        _expect("source_summary_candidate_count_values", source_split.get("candidate_count_values"), [EXPECTED_K]),
        _expect("source_summary_dp_head_values", source_split.get("dp_head_values"), [FIXED_DP_HEAD]),
        _expect("source_summary_candidate_tensor_not_mutated", source_split.get("candidate_tensor_mutated_count"), 0),
        _expect("source_summary_split_policy", source_split.get("split_policy"), "scene_level_greedy_imbalance_tolerant_smoke_split"),
        _expect("source_summary_split_classification", source_split.get("pilot_split_classification"), "imbalance_tolerant_smoke_split"),
        _expect("source_summary_performance_claim_supported", source_split.get("performance_claim_supported"), False),
        _expect("source_summary_record_level_hard_split", source_split.get("record_level_hard_split_executed"), False),
        _expect("source_split_execution_executed", source_final.get("split_execution_executed"), True),
        _expect("review_total_records", review["total_records"], EXPECTED_RECORDS),
        _expect("split_counts_match", review["counts"], EXPECTED_COUNTS),
        _expect("scene_assignments_match", review["scene_assignments"], EXPECTED_ASSIGNMENTS),
        _expect("scene_zero_overlap", review["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", review["sample_zero_overlap"], True),
        _expect("records_all_k_8", review["k_values"], [EXPECTED_K]),
        _expect("records_all_candidate_count_8", review["candidate_count_values"], [EXPECTED_K]),
        _expect("records_all_dp_head_fixed", review["dp_head_values"], [FIXED_DP_HEAD]),
        _expect("candidate_tensor_not_mutated", review["candidate_tensor_mutated_count"], 0),
        _expect("split_policy", review["split_policy"], "scene_level_greedy_imbalance_tolerant_smoke_split"),
        _expect("pilot_split_classification", review["pilot_split_classification"], "imbalance_tolerant_smoke_split"),
        _expect("performance_claim_not_supported", review["performance_claim_supported"], False),
        _expect("record_level_hard_split_not_executed", review["record_level_hard_split_executed"], False),
    ]
    checks.extend(_source_file_checks(artifact, source_summary_json, source_split_manifest_json, source_sha256s, source_root_sha256s))
    checks.extend(_no_forbidden_work_checks(source_final, "source_final"))
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
                "split_manifest_json": str(source_split_manifest_json.resolve()),
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
            "split_result_review": review,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "result_review_only": True,
                "split_execution_executed": False,
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
    _write_sha_manifest(output_dir)


def _split_result_review(records_by_split: dict[str, list[dict[str, Any]]], manifest: dict[str, Any]) -> dict[str, Any]:
    all_records = [record for split in ("train", "calibration", "holdout") for record in records_by_split[split]]
    scene_sets = {
        split: {str(record.get("scene_id")) for record in records}
        for split, records in records_by_split.items()
    }
    sample_sets = {
        split: {str(record.get("sample_id")) for record in records}
        for split, records in records_by_split.items()
    }
    return {
        "split_policy": manifest.get("split_policy"),
        "pilot_split_classification": manifest.get("pilot_split_classification"),
        "performance_claim_supported": manifest.get("performance_claim_supported"),
        "record_level_hard_split_executed": manifest.get("record_level_hard_split_executed"),
        "counts": {split: len(records_by_split[split]) for split in ("train", "calibration", "holdout")},
        "scene_assignments": {split: sorted(scene_sets[split]) for split in ("train", "calibration", "holdout")},
        "scene_zero_overlap": _sets_disjoint(scene_sets.values()),
        "sample_zero_overlap": _sets_disjoint(sample_sets.values()),
        "k_values": _unique(record.get("K") for record in all_records),
        "candidate_count_values": _unique(record.get("candidate_count") for record in all_records),
        "dp_head_values": _unique(record.get("DP_HEAD") for record in all_records),
        "candidate_tensor_mutated_count": sum(
            1
            for record in all_records
            if record.get("candidate_tensor_unchanged_by_camp") is not True
            or (
                "candidate_tensor_pre_sha256" in record
                and "candidate_tensor_post_sha256" in record
                and record.get("candidate_tensor_pre_sha256") != record.get("candidate_tensor_post_sha256")
            )
        ),
        "total_records": len(all_records),
    }


def _source_file_checks(
    artifact: Path,
    source_summary_json: Path,
    source_split_manifest_json: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
) -> list[dict[str, Any]]:
    checks = []
    expected_paths = {
        SOURCE_JSON_NAME: source_summary_json.resolve(),
        "split_manifest.json": source_split_manifest_json.resolve(),
        "SHA256SUMS": source_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_root_sha256s.resolve(),
    }
    for name in REQUIRED_SOURCE_FILES:
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if name in expected_paths:
            checks.append(_expect(f"source_artifact_path_{name}", expected_paths[name], path.resolve()))
    return checks


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
    review = report["split_result_review"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Corpus Split Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source artifact: `{report['source_artifact']['path']}`",
            f"- Source root SHA256: `{report['source_artifact']['root_sha256']}`",
            f"- Split policy: `{review['split_policy']}`",
            f"- Split counts: `{review['counts']}`",
            f"- Scene assignments: `{review['scene_assignments']}`",
            f"- Scene zero-overlap: `{review['scene_zero_overlap']}`",
            f"- Sample zero-overlap: `{review['sample_zero_overlap']}`",
            f"- Records / K / candidate count: `{review['total_records']} / {review['k_values']} / {review['candidate_count_values']}`",
            f"- Performance claim supported: `{review['performance_claim_supported']}`",
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


def _write_sha_manifest(output_dir: Path) -> None:
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path in (sha_path, root_path):
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  {output_dir.name}\n", encoding="utf-8")


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
