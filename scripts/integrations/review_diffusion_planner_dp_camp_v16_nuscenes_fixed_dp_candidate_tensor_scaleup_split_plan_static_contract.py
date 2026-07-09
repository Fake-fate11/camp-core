#!/usr/bin/env python3
"""Static-review the v16 scale-up scene-level split plan."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def _load_plan_module():
    path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split.py"
    )
    spec = importlib.util.spec_from_file_location("v16_scaleup_split_plan", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SOURCE_PLAN_SCHEMA_VERSION = PLAN_MODULE.SCHEMA_VERSION
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_preflight_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_v1"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review.md"
EXPECTED_RECORDS = 10000
EXPECTED_SCENES = 50
EXPECTED_SCENE_COUNTS = {"train": 30, "calibration": 10, "holdout": 10}
EXPECTED_RECORD_COUNTS = {"train": 6263, "calibration": 2156, "holdout": 1581}
EXPECTED_K = 8


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_json", type=Path, required=True)
    parser.add_argument("--source_plan_md", type=Path, required=True)
    parser.add_argument("--source_plan_sha256s", type=Path, required=True)
    parser.add_argument("--source_plan_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_plan_json=args.source_plan_json,
        source_plan_md=args.source_plan_md,
        source_plan_sha256s=args.source_plan_sha256s,
        source_plan_root_sha256s=args.source_plan_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_plan_artifact_dir: Path,
    source_plan_json: Path,
    source_plan_md: Path,
    source_plan_sha256s: Path,
    source_plan_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_plan_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_plan_artifact_dir.resolve()
    source = _read_json(source_plan_json)
    root_sha = _read_root_sha(source_plan_root_sha256s)
    sha_entries = _read_sha256s(source_plan_sha256s)
    sha_failures = _verify_sha256s(artifact, sha_entries)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    final = source.get("final_decision", {})
    split = source.get("split_plan", {})
    policy = split.get("followup_policy", {})

    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_plan_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_plan_json_path", source_plan_json.resolve(), artifact / PLAN_MODULE.PLAN_JSON_NAME),
        _expect("source_plan_md_path", source_plan_md.resolve(), artifact / PLAN_MODULE.PLAN_MD_NAME),
        _expect("source_plan_root_sha256", root_sha, expected_plan_root_sha256),
        _check("source_plan_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _expect("source_plan_schema", source.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", source.get("status"), PLAN_MODULE.READY_STATUS),
        _expect("source_plan_passed", final.get("passed"), True),
        _expect("source_plan_authorizes_static_review", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _contains("audit_authorizes_static_review", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_static_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_split_plan", audit_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _contains("status_records_split_plan", status_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _expect("total_records_10000", split.get("source_records"), EXPECTED_RECORDS),
        _expect("total_scenes_50", split.get("source_scene_count"), EXPECTED_SCENES),
        _expect("unique_samples_10000", split.get("source_unique_sample_count"), EXPECTED_RECORDS),
        _expect("planned_scene_split_30_10_10", split.get("planned_scene_counts"), EXPECTED_SCENE_COUNTS),
        _expect("expected_record_split_6263_2156_1581", split.get("planned_record_counts"), EXPECTED_RECORD_COUNTS),
        _expect("scene_sets_disjoint", split.get("scene_zero_overlap"), True),
        _expect("sample_ids_disjoint", split.get("sample_zero_overlap"), True),
        _expect("split_policy_scene_level_zero_overlap", split.get("target_ratio"), "60/20/20"),
        _expect("record_level_hard_split_not_executed", split.get("record_level_hard_split_executed"), False),
        _expect("k_values_8", split.get("k_values"), [EXPECTED_K]),
        _expect("candidate_count_values_8", split.get("candidate_count_values"), [EXPECTED_K]),
        _expect("record_dp_head_fixed", split.get("dp_head_values"), [FIXED_DP_HEAD]),
        _expect("source_head_dp_fixed", source.get("heads", {}).get("dp_head"), FIXED_DP_HEAD),
        _expect("candidate_tensor_mutation_count_0", split.get("candidate_tensor_mutated_count"), 0),
        _expect("training_uses_train_only", policy.get("training"), "train split only"),
        _expect("paired_eval_uses_calibration_holdout", policy.get("paired_eval_primary"), "calibration+holdout"),
        _expect(
            "claim_blocked_until_review_and_scale_sufficiency",
            policy.get("claim"),
            "blocked until result review and scale sufficiency checks",
        ),
        _expect("source_split_plan_only", final.get("split_plan_only"), True),
        _expect("source_split_execution_false", final.get("split_executed"), False),
    ]
    checks.extend(_no_forbidden_work_checks(final))
    for name in (PLAN_MODULE.PLAN_JSON_NAME, PLAN_MODULE.PLAN_MD_NAME, "HEADS", "COMMAND"):
        checks.append(_check(f"source_artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))

    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "source_plan_artifact": str(artifact),
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "plan_review": {
                "source_plan_root_sha256": root_sha,
                "records": split.get("source_records"),
                "scenes": split.get("source_scene_count"),
                "unique_samples": split.get("source_unique_sample_count"),
                "planned_scene_counts": split.get("planned_scene_counts"),
                "planned_record_counts": split.get("planned_record_counts"),
                "scene_zero_overlap": split.get("scene_zero_overlap"),
                "sample_zero_overlap": split.get("sample_zero_overlap"),
                "record_level_hard_split_executed": split.get("record_level_hard_split_executed"),
                "k_values": split.get("k_values"),
                "candidate_count_values": split.get("candidate_count_values"),
                "dp_head_values": split.get("dp_head_values"),
                "candidate_tensor_mutated_count": split.get("candidate_tensor_mutated_count"),
                "followup_policy": policy,
            },
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
                "static_review_only": True,
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
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", []), sort_keys=True) + "\n", encoding="utf-8")
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in (json_path, md_path, heads_path, command_path):
        rows.append(f"{_sha256(path)}  {path.name}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["plan_review"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Split Plan Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source plan artifact: `{report['source_plan_artifact']}`",
            f"- Source plan root SHA256: `{review['source_plan_root_sha256']}`",
            f"- Records / scenes: `{review['records']} / {review['scenes']}`",
            f"- Planned scene counts: `{review['planned_scene_counts']}`",
            f"- Planned record counts: `{review['planned_record_counts']}`",
            f"- Overlap checks: scene=`{review['scene_zero_overlap']}`, sample=`{review['sample_zero_overlap']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    review = report["plan_review"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_PLAN_ROOT_SHA256={review['source_plan_root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect(f"source_plan_{field}_false", final.get(field), False)
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
    if not path.is_file():
        return entries
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
