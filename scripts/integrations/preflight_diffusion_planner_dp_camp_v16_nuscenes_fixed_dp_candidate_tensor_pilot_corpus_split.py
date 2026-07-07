#!/usr/bin/env python3
"""Preflight the v16 fixed-DP pilot corpus split execution gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_static_review_v1"
)
SOURCE_READY_STATUS = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_static_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_preflight_only"
)
READY_STATUS = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_preflight_ready"
)
REJECT_STATUS = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_execution_only"
)
SOURCE_JSON_NAME = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_static_review.json"
)
SOURCE_MD_NAME = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_plan_static_review.md"
)
PREFLIGHT_JSON_NAME = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_preflight.json"
)
PREFLIGHT_MD_NAME = (
    "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_preflight.md"
)
SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_preflight_v1"
)
SPLIT_EXECUTION_SCRIPT = (
    "scripts/integrations/"
    "split_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus.py"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_static_review_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument("--candidate_records_jsonl", type=Path, required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_preflight",
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
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        candidate_records_jsonl=args.candidate_records_jsonl,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_preflight,
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
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_static_review_root_sha256: str,
    candidate_records_jsonl: Path,
    enabled: bool = False,
) -> dict[str, Any]:
    static_artifact = source_static_review_artifact_dir.resolve()
    source = _read_json(source_static_review_json)
    root_sha = _read_root_sha(source_static_review_root_sha256s)
    sha_entries = _read_sha256s(source_static_review_sha256s)
    sha_failures = _verify_sha256s(static_artifact, sha_entries)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    final = source.get("final_decision", {})
    review = source.get("plan_review", {})
    execution_output_root = output_dir.resolve().parent / (
        output_dir.name.replace("preflight", "execution")
    )

    checks = [
        _expect("preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_static_review_passed", final.get("passed"), True),
        _expect("source_authorizes_preflight", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_root_sha256", root_sha, expected_static_review_root_sha256),
        _check("source_static_review_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _contains("audit_authorizes_split_preflight", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_split_preflight", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_static_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_static_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("records_1024", review.get("records"), 1024),
        _expect("split_train_614", review.get("target_record_counts", {}).get("train"), 614),
        _expect("split_calibration_205", review.get("target_record_counts", {}).get("calibration"), 205),
        _expect("split_holdout_205", review.get("target_record_counts", {}).get("holdout"), 205),
        _expect("scene_overlap_forbidden", review.get("scene_overlap_allowed"), False),
        _expect("sample_overlap_forbidden", review.get("sample_overlap_allowed"), False),
        _expect("candidate_tensor_sha_overlap_forbidden", review.get("candidate_tensor_sha_overlap_allowed"), False),
        _expect("training_from_holdout_forbidden", review.get("training_from_holdout_authorized"), False),
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
            "source_static_review_artifact": {
                "path": str(static_artifact),
                "root_sha256": root_sha,
                "expected_root_sha256": expected_static_review_root_sha256,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "preflight": {
                "records": review.get("records"),
                "target_record_counts": review.get("target_record_counts"),
                "split_unit": review.get("split_unit"),
                "candidate_records_jsonl": str(candidate_records_jsonl),
                "execution_output_root": str(execution_output_root),
                "execution_command": [
                    SPLIT_EXECUTION_SCRIPT,
                    "--candidate_records_jsonl",
                    str(candidate_records_jsonl),
                    "--output_dir",
                    str(execution_output_root),
                ],
                "output_contract": [
                    "JSON summary",
                    "split manifests",
                    "identity overlap report",
                    "HEADS",
                    "COMMAND",
                    "stdout",
                    "stderr",
                    "SHA256SUMS",
                ],
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
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    paths = (json_path, md_path, heads_path, command_path)
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in paths),
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    preflight = report["preflight"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Corpus Split Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Records: `{preflight['records']}`",
            f"- Target record counts: `{preflight['target_record_counts']}`",
            f"- Execution output root: `{preflight['execution_output_root']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    source = report["source_static_review_artifact"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_STATIC_REVIEW_ROOT_SHA256={source['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect(f"source_static_review_{field}_false", final.get(field), False)
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
