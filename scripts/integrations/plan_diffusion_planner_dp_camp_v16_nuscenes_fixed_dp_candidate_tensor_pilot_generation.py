#!/usr/bin/env python3
"""Plan the v16 nuScenes fixed-DP candidate tensor pilot generation gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review_passed"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_review_only"
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review_v1"
)
SOURCE_REVIEW_JSON_NAME = (
    "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_result_review.json"
)
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan.md"
EXPORTER_SCRIPT = (
    "scripts/integrations/"
    "run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py"
)
NUSCENES_SOURCE_ROOT = "/autodl-pub/data/nuScenes"
PER_RECORD_MEAN_SECONDS = 5.31974
SELECTED_TARGET_RECORDS = 1024
ALTERNATE_TARGET_RECORDS = 2048


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_smoke_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_smoke_root_sha256s", type=Path, required=True)
    parser.add_argument("--source_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_review_json", type=Path, required=True)
    parser.add_argument("--source_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_smoke_root_sha256", required=True)
    parser.add_argument("--expected_review_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_smoke_artifact_dir=args.source_smoke_artifact_dir,
        source_smoke_root_sha256s=args.source_smoke_root_sha256s,
        source_review_artifact_dir=args.source_review_artifact_dir,
        source_review_json=args.source_review_json,
        source_review_sha256s=args.source_review_sha256s,
        source_review_root_sha256s=args.source_review_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_smoke_root_sha256=args.expected_smoke_root_sha256,
        expected_review_root_sha256=args.expected_review_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_smoke_artifact_dir: Path,
    source_smoke_root_sha256s: Path,
    source_review_artifact_dir: Path,
    source_review_json: Path,
    source_review_sha256s: Path,
    source_review_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_smoke_root_sha256: str,
    expected_review_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    smoke_root = _read_root_sha(source_smoke_root_sha256s)
    review_root = _read_root_sha(source_review_root_sha256s)
    review = _read_json(source_review_json)
    sha_failures = _verify_sha256s(source_review_artifact_dir.resolve(), _read_sha256s(source_review_sha256s))
    v16_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    checks = [
        _expect("pilot_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("source_review_schema", review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("source_review_status", review.get("status"), SOURCE_READY_STATUS),
        _expect("source_review_passed", review.get("final_decision", {}).get("passed"), True),
        _expect("source_review_authorizes_pilot_plan", review.get("final_decision", {}).get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_smoke_root_sha256", smoke_root, expected_smoke_root_sha256),
        _expect("source_review_root_sha256", review_root, expected_review_root_sha256),
        _expect("source_review_links_smoke_root", review.get("source_artifact", {}).get("root_sha256"), expected_smoke_root_sha256),
        _check("source_review_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _contains("audit_authorizes_pilot_plan", v16_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_pilot_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_result_review", v16_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_result_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_review_records_256", review.get("record_review", {}).get("record_count"), 256),
        _expect("source_review_k_8", review.get("record_review", {}).get("k_values"), [8]),
        _expect("source_review_candidate_count_8", review.get("record_review", {}).get("candidate_count_values"), [8]),
        _expect("source_review_dp_head_fixed", review.get("record_review", {}).get("dp_heads"), [FIXED_DP_HEAD]),
        _expect("source_review_failure_count_zero", review.get("record_review", {}).get("failure_count"), 0),
    ]
    checks.extend(_no_forbidden_work_checks(review))
    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_v1",
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
            "source_artifacts": {
                "smoke_artifact": str(source_smoke_artifact_dir.resolve()),
                "smoke_root_sha256": smoke_root,
                "expected_smoke_root_sha256": expected_smoke_root_sha256,
                "source_smoke_review_artifact": str(source_review_artifact_dir.resolve()),
                "review_root_sha256": review_root,
                "expected_review_root_sha256": expected_review_root_sha256,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "inputs": _inputs(source_review_artifact_dir.resolve()),
            "pilot_plan": {
                "selected_target_records": SELECTED_TARGET_RECORDS,
                "alternate_target_records": ALTERNATE_TARGET_RECORDS,
                "k": 8,
                "candidate_count": 8,
                "plan_only": True,
                "pilot_execution_authorized": False,
                "train_calibration_holdout_split_planning_separate": True,
            },
            "timing_estimates": _timing_estimates(),
            "outputs": [
                "JSON summary",
                "JSONL records",
                "candidate tensor hashes",
                "HEADS",
                "COMMAND",
                "stdout",
                "stderr",
                "SHA256SUMS",
            ],
            "pass_conditions": [
                "records == target_records",
                "K == 8",
                "candidate_count == 8",
                "DP_HEAD fixed",
                "failure_count == 0",
                "all dp_top1_index in [0,7]",
                "all candidate_tensor_sha256 present",
            ],
            "split_provenance_requirements": [
                "scene/sample id present",
                "avoid duplicate sample ids within pilot",
                "keep train/calibration/holdout split planning separate",
                "pilot only generates candidate corpus",
            ],
            "stop_conditions": [
                "output root exists",
                "DP HEAD mismatch",
                "records shortfall",
                "any fake/synthetic candidate tensor",
                "any DP/candidate/trajectory mutation",
            ],
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "plan_only": True,
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


def _inputs(source_review_artifact: Path) -> dict[str, Any]:
    return {
        "source_smoke_review_artifact": str(source_review_artifact),
        "exporter_script": EXPORTER_SCRIPT,
        "nuscenes_source_root": NUSCENES_SOURCE_ROOT,
        "dp_fixed_head": FIXED_DP_HEAD,
    }


def _timing_estimates() -> dict[str, dict[str, float]]:
    return {
        str(records): {
            "target_records": records,
            "per_record_mean_seconds": PER_RECORD_MEAN_SECONDS,
            "wall_clock_seconds": round(records * PER_RECORD_MEAN_SECONDS, 6),
            "wall_clock_hours": round(records * PER_RECORD_MEAN_SECONDS / 3600, 6),
        }
        for records in (SELECTED_TARGET_RECORDS, ALTERNATE_TARGET_RECORDS)
    }


def _no_forbidden_work_checks(review: dict[str, Any]) -> list[dict[str, Any]]:
    final = review.get("final_decision", {})
    checks = []
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
        checks.append(_expect(f"source_review_{field}_false", final.get(field), False))
    return checks


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["pilot_plan"]
    timing = report["timing_estimates"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Pilot Generation Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Selected target records: `{plan['selected_target_records']}`",
            f"- Alternate target records: `{plan['alternate_target_records']}`",
            f"- 1024 estimate hours: `{timing['1024']['wall_clock_hours']}`",
            f"- 2048 estimate hours: `{timing['2048']['wall_clock_hours']}`",
            f"- Source review artifact: `{report['inputs']['source_smoke_review_artifact']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    source = report["source_artifacts"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SMOKE_ROOT_SHA256={source['smoke_root_sha256']}",
            f"REVIEW_ROOT_SHA256={source['review_root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _verify_sha256s(root: Path, entries: dict[str, str]) -> list[str]:
    failed = []
    for name, expected in entries.items():
        path = root / name
        if not path.is_file():
            failed.append(f"missing:{name}")
            continue
        if _sha256(path) != expected:
            failed.append(f"mismatch:{name}")
    return failed


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sha256s(path: Path) -> dict[str, str]:
    entries = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        entries[name.strip()] = digest
    return entries


def _read_root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    line = path.read_text(encoding="utf-8").splitlines()[0]
    return line.split()[0] if line else None


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
