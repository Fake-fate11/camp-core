#!/usr/bin/env python3
"""Plan the v16 pilot corpus split remediation after scene-count conflict."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_blocker_v1"
)
SOURCE_READY_STATUS = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_execution_blocked_scene_granularity_target_count_conflict"
)
AUTHORIZED_CURRENT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_user_decision_required"
)
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_rejected"
AUTHORIZED_NEXT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_static_review_only"
)
SOURCE_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_blocker.json"
SOURCE_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_blocker.md"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation.md"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_v1"
EXPECTED_RECORDS = 1024
EXPECTED_SCENES = 4
EXPECTED_SCENE_COUNTS_DESC = [495, 368, 147, 14]
ORIGINAL_TARGET_COUNTS = {"train": 614, "calibration": 205, "holdout": 205}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_blocker_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_blocker_json", type=Path, required=True)
    parser.add_argument("--source_blocker_sha256s", type=Path, required=True)
    parser.add_argument("--source_blocker_root_sha256s", type=Path, required=True)
    parser.add_argument("--candidate_records_jsonl", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_blocker_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_blocker_artifact_dir=args.source_blocker_artifact_dir,
        source_blocker_json=args.source_blocker_json,
        source_blocker_sha256s=args.source_blocker_sha256s,
        source_blocker_root_sha256s=args.source_blocker_root_sha256s,
        candidate_records_jsonl=args.candidate_records_jsonl,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_blocker_root_sha256=args.expected_blocker_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation_plan,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_blocker_artifact_dir: Path,
    source_blocker_json: Path,
    source_blocker_sha256s: Path,
    source_blocker_root_sha256s: Path,
    candidate_records_jsonl: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_blocker_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    blocker_artifact = source_blocker_artifact_dir.resolve()
    source = _read_json(source_blocker_json)
    root_sha = _read_root_sha(source_blocker_root_sha256s)
    sha_entries = _read_sha256s(source_blocker_sha256s)
    sha_failures = _verify_sha256s(blocker_artifact, sha_entries)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    record_summary = _summarize_records(candidate_records_jsonl)
    remediation_plan = _build_remediation_plan(record_summary)

    checks = [
        _expect("split_remediation_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_blocker_artifact_exists", blocker_artifact.is_dir(), str(blocker_artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_blocked", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_authorizes_split_remediation", source.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_blocker_root_sha256", root_sha, expected_blocker_root_sha256),
        _check("source_blocker_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _contains("audit_authorizes_split_remediation", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_split_remediation", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_blocker", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_blocker", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_records_1024", source.get("record_count"), EXPECTED_RECORDS),
        _expect("source_unique_scene_count_4", source.get("unique_scene_count"), EXPECTED_SCENES),
        _expect("source_unique_sample_count_1024", source.get("unique_sample_count"), EXPECTED_RECORDS),
        _expect("source_duplicate_sample_count_zero", source.get("duplicate_sample_count"), 0),
        _expect("source_scene_counts_desc", source.get("scene_record_counts_desc"), EXPECTED_SCENE_COUNTS_DESC),
        _expect("source_target_counts_unreachable", source.get("target_counts_reachable_with_scene_zero_overlap"), False),
        _expect("source_exact_scene_split_blocked", source.get("scene_zero_overlap_exact_614_205_205_executable"), False),
        _expect(
            "source_record_level_split_would_leak_scene",
            source.get("record_level_exact_split_would_violate_scene_zero_overlap"),
            True,
        ),
        _expect("records_jsonl_count_1024", record_summary["record_count"], EXPECTED_RECORDS),
        _expect("records_jsonl_unique_scene_count_4", record_summary["unique_scene_count"], EXPECTED_SCENES),
        _expect("records_jsonl_unique_sample_count_1024", record_summary["unique_sample_count"], EXPECTED_RECORDS),
        _expect("records_jsonl_duplicate_sample_count_zero", record_summary["duplicate_sample_count"], 0),
        _expect("records_jsonl_scene_counts_match_blocker", record_summary["scene_counts_desc"], EXPECTED_SCENE_COUNTS_DESC),
        _expect("plan_train_has_two_scenes", len(remediation_plan["scene_assignments"]["train"]), 2),
        _expect("plan_calibration_has_one_scene", len(remediation_plan["scene_assignments"]["calibration"]), 1),
        _expect("plan_holdout_has_one_scene", len(remediation_plan["scene_assignments"]["holdout"]), 1),
        _expect("plan_scene_zero_overlap", remediation_plan["scene_zero_overlap"], True),
        _expect("plan_sample_zero_overlap", remediation_plan["sample_zero_overlap"], True),
        _expect("plan_record_level_split_not_executed", remediation_plan["record_level_split_executed"], False),
    ]
    checks.extend(_no_forbidden_work_checks(source))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed

    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "source_blocker_artifact": {
                "path": str(blocker_artifact),
                "json": str(source_blocker_json.resolve()),
                "root_sha256": root_sha,
                "expected_root_sha256": expected_blocker_root_sha256,
                "sha256_entry_count": len(sha_entries),
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_blocker_camp_head": source.get("camp_head"),
                "source_blocker_dp_head": source.get("dp_head"),
            },
            "source_blocker": source,
            "record_summary": record_summary,
            "remediation_plan": remediation_plan,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
                "split_plan_remediation_only": True,
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
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    paths = (json_path, md_path, heads_path, command_path)
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in paths),
        encoding="utf-8",
    )


def _summarize_records(path: Path) -> dict[str, Any]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    scenes = collections.Counter(record.get("scene_id") for record in records)
    samples_by_scene: dict[str, set[str]] = collections.defaultdict(set)
    sample_ids: list[str] = []
    for record in records:
        scene_id = str(record.get("scene_id"))
        sample_id = str(record.get("sample_id"))
        samples_by_scene[scene_id].add(sample_id)
        sample_ids.append(sample_id)
    return {
        "record_count": len(records),
        "unique_scene_count": len(scenes),
        "unique_sample_count": len(set(sample_ids)),
        "duplicate_sample_count": len(sample_ids) - len(set(sample_ids)),
        "scene_counts": dict(scenes),
        "scene_counts_desc": sorted(scenes.values(), reverse=True),
        "samples_by_scene": {scene: sorted(samples) for scene, samples in samples_by_scene.items()},
    }


def _build_remediation_plan(record_summary: dict[str, Any]) -> dict[str, Any]:
    sorted_scenes = sorted(
        record_summary["scene_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    )
    train = [scene for scene, _ in sorted_scenes[:2]]
    holdout = [sorted_scenes[2][0]] if len(sorted_scenes) > 2 else []
    calibration = [sorted_scenes[3][0]] if len(sorted_scenes) > 3 else []
    assignments = {"train": train, "calibration": calibration, "holdout": holdout}
    counts = {
        split: sum(record_summary["scene_counts"][scene] for scene in scenes)
        for split, scenes in assignments.items()
    }
    total = record_summary["record_count"] or 1
    sample_sets = {
        split: {
            sample
            for scene in scenes
            for sample in record_summary["samples_by_scene"].get(scene, [])
        }
        for split, scenes in assignments.items()
    }
    return {
        "source_records": record_summary["record_count"],
        "split_policy": "scene_level_greedy_imbalance_tolerant_smoke_split",
        "split_unit": "scene_id",
        "pilot_split_classification": "imbalance_tolerant_smoke_split",
        "original_exact_record_targets": ORIGINAL_TARGET_COUNTS,
        "exact_record_count_targets_rejected": True,
        "record_level_split_executed": False,
        "scene_counts": record_summary["scene_counts"],
        "scene_assignments": assignments,
        "actual_record_counts": counts,
        "actual_record_ratios": {split: counts[split] / total for split in ("train", "calibration", "holdout")},
        "scene_zero_overlap": _sets_disjoint(map(set, assignments.values())),
        "sample_zero_overlap": _sets_disjoint(sample_sets.values()),
        "assignment_rationale": (
            "Use the two largest scenes for train, keep the larger remaining scene as holdout, "
            "and accept the smallest scene as calibration for a scene-pure smoke split."
        ),
        "larger_corpus_preconditions": {
            "ten_k_generation_must_increase_scene_diversity": True,
            "minimum_scene_count_before_ratio_tracking": 30,
            "near_60_20_20_requires_scene_count_at_least": 30,
        },
    }


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["remediation_plan"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Corpus Split Plan Remediation",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Split policy: `{plan['split_policy']}`",
            f"- Scene assignments: `{plan['scene_assignments']}`",
            f"- Actual record counts: `{plan['actual_record_counts']}`",
            f"- Actual record ratios: `{plan['actual_record_ratios']}`",
            f"- Source blocker artifact: `{report['source_blocker_artifact']['path']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    source = report["source_blocker_artifact"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_BLOCKER_ROOT_SHA256={source['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _no_forbidden_work_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect(f"source_blocker_{field}_false", source.get(field), False)
        for field in (
            "split_execution_executed",
            "candidate_generation_executed",
            "training_executed",
            "paired_evaluation_executed",
            "dp_modified",
            "candidate_tensor_modified",
        )
    ]


def _sets_disjoint(sets: Any) -> bool:
    seen: set[Any] = set()
    for values in sets:
        overlap = seen.intersection(values)
        if overlap:
            return False
        seen.update(values)
    return True


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
