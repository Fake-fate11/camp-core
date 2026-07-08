#!/usr/bin/env python3
"""Materialize the v16 pilot corpus scene-level split manifests."""

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


PLAN_MODULE = _load_module(
    "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation.py",
    "v16_split_remediation_plan",
)
REVIEW_MODULE = _load_module(
    "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation_static_contract.py",
    "v16_split_remediation_static_review",
)

FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
REMEDIATION_SCHEMA_VERSION = PLAN_MODULE.SCHEMA_VERSION
REMEDIATION_READY_STATUS = PLAN_MODULE.READY_STATUS
REMEDIATION_REVIEW_SCHEMA_VERSION = REVIEW_MODULE.SCHEMA_VERSION
SOURCE_READY_STATUS = REVIEW_MODULE.READY_STATUS
SOURCE_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
AUTHORIZED_CURRENT_WORK = REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_passed"
FAILED_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_failed"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_v1"
REPORT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution.json"
REPORT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution.md"
REMEDIATION_JSON_NAME = PLAN_MODULE.PLAN_JSON_NAME
REMEDIATION_REVIEW_JSON_NAME = REVIEW_MODULE.REVIEW_JSON_NAME
EXPECTED_ASSIGNMENTS = {
    "train": ["scene-0553", "scene-0655"],
    "calibration": ["scene-0061"],
    "holdout": ["scene-0757"],
}
EXPECTED_COUNTS = {"train": 863, "calibration": 14, "holdout": 147}
EXPECTED_RECORDS = 1024
EXPECTED_K = 8
SPLIT_JSONL_NAMES = {
    "train": "train_records.jsonl",
    "calibration": "calibration_records.jsonl",
    "holdout": "holdout_records.jsonl",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot_corpus_artifact_dir", type=Path, required=True)
    parser.add_argument("--pilot_records_jsonl", type=Path, required=True)
    parser.add_argument("--pilot_corpus_sha256s", type=Path, required=True)
    parser.add_argument("--pilot_corpus_root_sha256s", type=Path, required=True)
    parser.add_argument("--split_blocker_artifact_dir", type=Path, required=True)
    parser.add_argument("--split_blocker_sha256s", type=Path, required=True)
    parser.add_argument("--split_blocker_root_sha256s", type=Path, required=True)
    parser.add_argument("--remediation_artifact_dir", type=Path, required=True)
    parser.add_argument("--remediation_json", type=Path, required=True)
    parser.add_argument("--remediation_sha256s", type=Path, required=True)
    parser.add_argument("--remediation_root_sha256s", type=Path, required=True)
    parser.add_argument("--remediation_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--remediation_review_json", type=Path, required=True)
    parser.add_argument("--remediation_review_sha256s", type=Path, required=True)
    parser.add_argument("--remediation_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_pilot_corpus_root_sha256", required=True)
    parser.add_argument("--expected_split_blocker_root_sha256", required=True)
    parser.add_argument("--expected_remediation_root_sha256", required=True)
    parser.add_argument("--expected_remediation_review_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        pilot_corpus_artifact_dir=args.pilot_corpus_artifact_dir,
        pilot_records_jsonl=args.pilot_records_jsonl,
        pilot_corpus_sha256s=args.pilot_corpus_sha256s,
        pilot_corpus_root_sha256s=args.pilot_corpus_root_sha256s,
        split_blocker_artifact_dir=args.split_blocker_artifact_dir,
        split_blocker_sha256s=args.split_blocker_sha256s,
        split_blocker_root_sha256s=args.split_blocker_root_sha256s,
        remediation_artifact_dir=args.remediation_artifact_dir,
        remediation_json=args.remediation_json,
        remediation_sha256s=args.remediation_sha256s,
        remediation_root_sha256s=args.remediation_root_sha256s,
        remediation_review_artifact_dir=args.remediation_review_artifact_dir,
        remediation_review_json=args.remediation_review_json,
        remediation_review_sha256s=args.remediation_review_sha256s,
        remediation_review_root_sha256s=args.remediation_review_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_pilot_corpus_root_sha256=args.expected_pilot_corpus_root_sha256,
        expected_split_blocker_root_sha256=args.expected_split_blocker_root_sha256,
        expected_remediation_root_sha256=args.expected_remediation_root_sha256,
        expected_remediation_review_root_sha256=args.expected_remediation_review_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    pilot_corpus_artifact_dir: Path,
    pilot_records_jsonl: Path,
    pilot_corpus_sha256s: Path,
    pilot_corpus_root_sha256s: Path,
    split_blocker_artifact_dir: Path,
    split_blocker_sha256s: Path,
    split_blocker_root_sha256s: Path,
    remediation_artifact_dir: Path,
    remediation_json: Path,
    remediation_sha256s: Path,
    remediation_root_sha256s: Path,
    remediation_review_artifact_dir: Path,
    remediation_review_json: Path,
    remediation_review_sha256s: Path,
    remediation_review_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_pilot_corpus_root_sha256: str,
    expected_split_blocker_root_sha256: str,
    expected_remediation_root_sha256: str,
    expected_remediation_review_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8").split("## Current V15 Status", 1)[0]
    remediation = _read_json(remediation_json)
    review = _read_json(remediation_review_json)
    records = _read_records(pilot_records_jsonl)
    source_artifacts = {
        "pilot_corpus": _source_artifact(
            pilot_corpus_artifact_dir,
            pilot_corpus_sha256s,
            pilot_corpus_root_sha256s,
            expected_pilot_corpus_root_sha256,
        ),
        "split_blocker": _source_artifact(
            split_blocker_artifact_dir,
            split_blocker_sha256s,
            split_blocker_root_sha256s,
            expected_split_blocker_root_sha256,
        ),
        "remediation": _source_artifact(
            remediation_artifact_dir,
            remediation_sha256s,
            remediation_root_sha256s,
            expected_remediation_root_sha256,
        ),
        "remediation_static_review": _source_artifact(
            remediation_review_artifact_dir,
            remediation_review_sha256s,
            remediation_review_root_sha256s,
            expected_remediation_review_root_sha256,
        ),
    }
    split_records = _split_records(records, EXPECTED_ASSIGNMENTS)
    split_summary = _split_summary(split_records, remediation, review)

    checks = [
        _expect("split_execution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_split_execution", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_split_execution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_static_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_static_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("remediation_schema", remediation.get("schema_version"), REMEDIATION_SCHEMA_VERSION),
        _expect("remediation_status", remediation.get("status"), REMEDIATION_READY_STATUS),
        _expect("remediation_authorizes_static_review", remediation.get("final_decision", {}).get("authorized_next_work"), SOURCE_CURRENT_WORK),
        _expect("review_schema", review.get("schema_version"), REMEDIATION_REVIEW_SCHEMA_VERSION),
        _expect("review_status", review.get("status"), SOURCE_READY_STATUS),
        _expect("review_authorizes_split_execution", review.get("final_decision", {}).get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("record_count_1024", len(records), EXPECTED_RECORDS),
        _expect("split_counts_match", split_summary["counts"], EXPECTED_COUNTS),
        _expect("scene_assignments_match", split_summary["scene_assignments"], EXPECTED_ASSIGNMENTS),
        _expect("scene_zero_overlap", split_summary["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", split_summary["sample_zero_overlap"], True),
        _expect("records_all_k_8", split_summary["k_values"], [EXPECTED_K]),
        _expect("records_all_candidate_count_8", split_summary["candidate_count_values"], [EXPECTED_K]),
        _expect("records_all_dp_head_fixed", split_summary["dp_head_values"], [FIXED_DP_HEAD]),
        _expect("candidate_tensor_not_mutated", split_summary["candidate_tensor_mutated_count"], 0),
        _expect("record_level_hard_split_not_executed", split_summary["record_level_hard_split_executed"], False),
        _expect("performance_claim_not_supported", split_summary["performance_claim_supported"], False),
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
    checks.extend(_no_forbidden_work_checks(remediation.get("final_decision", {}), "source_remediation"))
    checks.extend(_no_forbidden_work_checks(review.get("final_decision", {}), "source_review"))

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
    (output_dir / REPORT_JSON_NAME).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / REPORT_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _split_records(records: list[dict[str, Any]], assignments: dict[str, list[str]]) -> dict[str, list[dict[str, Any]]]:
    scene_to_split = {scene: split for split, scenes in assignments.items() for scene in scenes}
    result = {split: [] for split in assignments}
    for record in records:
        split = scene_to_split.get(record.get("scene_id"))
        if split is not None:
            result[split].append(record)
    return result


def _split_summary(
    split_records: dict[str, list[dict[str, Any]]],
    remediation: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    plan = remediation.get("remediation_plan", {})
    review_plan = review.get("remediation_review", {})
    scene_assignments = review_plan.get("scene_assignments") or plan.get("scene_assignments") or EXPECTED_ASSIGNMENTS
    sample_sets = {
        split: {str(record.get("sample_id")) for record in records}
        for split, records in split_records.items()
    }
    scene_sets = {split: set(scenes) for split, scenes in scene_assignments.items()}
    records = [record for split in ("train", "calibration", "holdout") for record in split_records[split]]
    return {
        "split_policy": review_plan.get("split_policy") or plan.get("split_policy"),
        "split_unit": review_plan.get("split_unit") or plan.get("split_unit"),
        "pilot_split_classification": review_plan.get("pilot_split_classification") or plan.get("pilot_split_classification"),
        "performance_claim_supported": False,
        "record_level_hard_split_executed": False,
        "scene_assignments": scene_assignments,
        "counts": {split: len(split_records[split]) for split in ("train", "calibration", "holdout")},
        "scene_zero_overlap": _sets_disjoint(scene_sets.values()),
        "sample_zero_overlap": _sets_disjoint(sample_sets.values()),
        "k_values": sorted({record.get("K") for record in records}),
        "candidate_count_values": sorted({record.get("candidate_count") for record in records}),
        "dp_head_values": sorted({record.get("DP_HEAD") for record in records}),
        "candidate_tensor_mutated_count": sum(
            1
            for record in records
            if record.get("candidate_tensor_unchanged_by_camp") is not True
            or (
                "candidate_tensor_pre_sha256" in record
                and "candidate_tensor_post_sha256" in record
                and record.get("candidate_tensor_pre_sha256") != record.get("candidate_tensor_post_sha256")
            )
        ),
        "total_records": len(records),
        "larger_corpus_preconditions": review_plan.get("larger_corpus_preconditions")
        or plan.get("larger_corpus_preconditions"),
    }


def _source_artifact(root: Path, sha256s: Path, root_sha256s: Path, expected_root_sha: str) -> dict[str, Any]:
    entries, failed = _verify_sha256s(root, sha256s)
    root_sha = _read_root_sha(root_sha256s)
    return {
        "path": str(root),
        "exists": root.is_dir(),
        "sha256_entry_count": entries,
        "failed_sha256s": failed,
        "sha256s_verified": root.is_dir() and sha256s.is_file() and not failed,
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
        if not path.is_file() or _sha256(path) != expected:
            failed.append(rel.strip())
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


def _read_records(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _render_markdown(report: dict[str, Any]) -> str:
    split = report["split_execution"]
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Corpus Split Execution",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Split policy: `{split['split_policy']}`",
            f"- Split counts: `{split['counts']}`",
            f"- Scene assignments: `{split['scene_assignments']}`",
            f"- Scene zero-overlap: `{split['scene_zero_overlap']}`",
            f"- Sample zero-overlap: `{split['sample_zero_overlap']}`",
            f"- Performance claim supported: `{split['performance_claim_supported']}`",
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
    root_path.write_text(f"{_sha256(sha_path)}  {output_dir.name}\n", encoding="utf-8")


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
