#!/usr/bin/env python3
"""Preflight the v16 scale-up split execution gate without executing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_v1"
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_passed"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_v1"
SOURCE_STATIC_REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review.json"
SOURCE_STATIC_REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review.md"
SOURCE_PLAN_SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_v1"
SOURCE_PLAN_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_ready"
SOURCE_PLAN_AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_only"
SOURCE_PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan.json"
SOURCE_PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan.md"
PREFLIGHT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight.json"
PREFLIGHT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight.md"
SPLIT_EXECUTION_SCRIPT = (
    "scripts/integrations/"
    "split_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup.py"
)
EXPECTED_RECORDS = 10000
EXPECTED_SCENES = 50
EXPECTED_SCENE_COUNTS = {"train": 30, "calibration": 10, "holdout": 10}
EXPECTED_RECORD_COUNTS = {"train": 6263, "calibration": 2156, "holdout": 1581}
EXPECTED_K = 8


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_corpus_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_corpus_sha256s", type=Path, required=True)
    parser.add_argument("--source_corpus_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--execution_output_root", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument("--expected_corpus_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_static_review_root_sha256s=args.source_static_review_root_sha256s,
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_sha256s=args.source_plan_sha256s,
        source_plan_root_sha256s=args.source_plan_root_sha256s,
        source_corpus_artifact_dir=args.source_corpus_artifact_dir,
        source_corpus_sha256s=args.source_corpus_sha256s,
        source_corpus_root_sha256s=args.source_corpus_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        execution_output_root=args.execution_output_root,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        expected_corpus_root_sha256=args.expected_corpus_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_sha256s: Path,
    source_static_review_root_sha256s: Path,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_sha256s: Path,
    source_plan_root_sha256s: Path,
    source_corpus_artifact_dir: Path,
    source_corpus_sha256s: Path,
    source_corpus_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    execution_output_root: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_static_review_root_sha256: str,
    expected_plan_root_sha256: str,
    expected_corpus_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    static_artifact = source_static_review_artifact_dir.resolve()
    plan_artifact = source_plan_artifact_dir.resolve()
    corpus_artifact = source_corpus_artifact_dir.resolve()
    source = _read_json(source_static_review_json)
    plan = _read_json(source_plan_json)
    static_root = _read_root_sha(source_static_review_root_sha256s)
    plan_root = _read_root_sha(source_plan_root_sha256s)
    corpus_root = _read_root_sha(source_corpus_root_sha256s)
    static_sha_count, static_sha_failures = _verify_sha256s(static_artifact, source_static_review_sha256s)
    plan_sha_count, plan_sha_failures = _verify_sha256s(plan_artifact, source_plan_sha256s)
    corpus_sha_count, corpus_sha_failures = _verify_sha256s(corpus_artifact, source_corpus_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    final = source.get("final_decision", {})
    plan_final = plan.get("final_decision", {})
    review = source.get("plan_review", {})
    plan_split = plan.get("split_plan", {})
    policy = review.get("followup_policy", {})
    execution_root = execution_output_root.resolve()
    execution_command = [
        SPLIT_EXECUTION_SCRIPT,
        "--source_records_jsonl",
        str((corpus_artifact / "records.jsonl").resolve()),
        "--source_split_plan_json",
        str(source_plan_json.resolve()),
        "--output_dir",
        str(execution_root),
    ]

    checks = [
        _expect("preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _check("source_plan_artifact_exists", plan_artifact.is_dir(), str(plan_artifact), "directory"),
        _check("source_corpus_artifact_exists", corpus_artifact.is_dir(), str(corpus_artifact), "directory"),
        _expect("source_static_review_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_static_review_status", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_static_review_passed", final.get("passed"), True),
        _expect("source_static_review_authorizes_preflight", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_plan_schema", plan.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", plan.get("status"), SOURCE_PLAN_READY_STATUS),
        _expect("source_plan_passed", plan_final.get("passed"), True),
        _expect("source_plan_authorizes_static_review", plan_final.get("authorized_next_work"), SOURCE_PLAN_AUTHORIZED_NEXT_WORK),
        _expect("source_static_review_root_sha256", static_root, expected_static_review_root_sha256),
        _expect("source_plan_root_sha256", plan_root, expected_plan_root_sha256),
        _expect("source_corpus_root_sha256", corpus_root, expected_corpus_root_sha256),
        _check("source_static_review_sha256s_verified", not static_sha_failures, static_sha_failures[:10], []),
        _check("source_plan_sha256s_verified", not plan_sha_failures, plan_sha_failures[:10], []),
        _check("source_corpus_sha256s_verified", not corpus_sha_failures, corpus_sha_failures[:10], []),
        _contains("audit_authorizes_split_preflight", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_split_preflight", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_static_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_static_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _check("split_execution_command_constructed", bool(execution_command), execution_command, "nonempty command"),
        _expect("execution_output_root_absent", execution_root.exists(), False),
        _expect("total_records_10000", review.get("records"), EXPECTED_RECORDS),
        _expect("total_scenes_50", review.get("scenes"), EXPECTED_SCENES),
        _expect("planned_scene_split_30_10_10", review.get("planned_scene_counts"), EXPECTED_SCENE_COUNTS),
        _expect("planned_record_split_6263_2156_1581", review.get("planned_record_counts"), EXPECTED_RECORD_COUNTS),
        _expect("scene_sets_disjoint", review.get("scene_zero_overlap"), True),
        _expect("sample_ids_disjoint", review.get("sample_zero_overlap"), True),
        _expect("record_level_hard_split_not_executed", review.get("record_level_hard_split_executed"), False),
        _expect("k_values_8", review.get("k_values"), [EXPECTED_K]),
        _expect("candidate_count_values_8", review.get("candidate_count_values"), [EXPECTED_K]),
        _expect("dp_head_fixed_records", review.get("dp_head_values"), [FIXED_DP_HEAD]),
        _expect("candidate_tensor_mutation_count_0", review.get("candidate_tensor_mutated_count"), 0),
        _expect("training_uses_train_only", policy.get("training"), "train split only"),
        _expect("paired_eval_uses_calibration_holdout", policy.get("paired_eval_primary"), "calibration+holdout"),
        _expect("plan_records_match_review", plan_split.get("source_records"), review.get("records")),
        _expect("plan_scene_counts_match_review", plan_split.get("planned_scene_counts"), review.get("planned_scene_counts")),
        _expect("plan_record_counts_match_review", plan_split.get("planned_record_counts"), review.get("planned_record_counts")),
        _expect("plan_source_corpus_root_matches", plan.get("source_corpus_artifact", {}).get("root_sha256"), corpus_root),
    ]
    checks.extend(_no_forbidden_work_checks(final, "source_static_review"))
    checks.extend(_no_forbidden_work_checks(plan_final, "source_plan"))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "source_static_review_artifact": {
                "path": str(static_artifact),
                "root_sha256": static_root,
                "sha256_entry_count": static_sha_count,
                "failed_sha256s": static_sha_failures,
            },
            "source_plan_artifact": {
                "path": str(plan_artifact),
                "root_sha256": plan_root,
                "sha256_entry_count": plan_sha_count,
                "failed_sha256s": plan_sha_failures,
            },
            "source_corpus_artifact": {
                "path": str(corpus_artifact),
                "root_sha256": corpus_root,
                "sha256_entry_count": corpus_sha_count,
                "failed_sha256s": corpus_sha_failures,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "preflight": {
                "records": review.get("records"),
                "scenes": review.get("scenes"),
                "planned_scene_counts": review.get("planned_scene_counts"),
                "planned_record_counts": review.get("planned_record_counts"),
                "scene_zero_overlap": review.get("scene_zero_overlap"),
                "sample_zero_overlap": review.get("sample_zero_overlap"),
                "record_level_hard_split_executed": review.get("record_level_hard_split_executed"),
                "k_values": review.get("k_values"),
                "candidate_count_values": review.get("candidate_count_values"),
                "dp_head_values": review.get("dp_head_values"),
                "candidate_tensor_mutated_count": review.get("candidate_tensor_mutated_count"),
                "followup_policy": policy,
                "execution_command": execution_command,
                "execution_command_constructed": True,
                "execution_output_root": str(execution_root),
                "execution_output_root_absent": not execution_root.exists(),
            },
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
                "preflight_only": True,
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
    json_path = output_dir / PREFLIGHT_JSON_NAME
    md_path = output_dir / PREFLIGHT_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", []), sort_keys=True) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    preflight = report["preflight"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Split Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Records / scenes: `{preflight['records']} / {preflight['scenes']}`",
            f"- Planned scene counts: `{preflight['planned_scene_counts']}`",
            f"- Planned record counts: `{preflight['planned_record_counts']}`",
            f"- Execution output root: `{preflight['execution_output_root']}`",
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
            f"SOURCE_STATIC_REVIEW_ROOT_SHA256={report['source_static_review_artifact']['root_sha256']}",
            f"SOURCE_PLAN_ROOT_SHA256={report['source_plan_artifact']['root_sha256']}",
            f"SOURCE_CORPUS_ROOT_SHA256={report['source_corpus_artifact']['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0].split()[0] if lines else None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


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
