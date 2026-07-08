#!/usr/bin/env python3
"""Static-review the v16 pilot corpus split remediation plan."""

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
        "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation.py"
    )
    spec = importlib.util.spec_from_file_location("v16_split_remediation_plan", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SOURCE_REMEDIATION_SCHEMA_VERSION = PLAN_MODULE.SCHEMA_VERSION
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_static_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_static_review_v1"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_static_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_remediation_static_review.md"
EXPECTED_ASSIGNMENTS = {
    "train": ["scene-0553", "scene-0655"],
    "calibration": ["scene-0061"],
    "holdout": ["scene-0757"],
}
EXPECTED_COUNTS = {"train": 863, "calibration": 14, "holdout": 147}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_remediation_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_remediation_json", type=Path, required=True)
    parser.add_argument("--source_remediation_md", type=Path, required=True)
    parser.add_argument("--source_remediation_sha256s", type=Path, required=True)
    parser.add_argument("--source_remediation_root_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_remediation_root_sha256", required=True)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_remediation_artifact_dir=args.source_remediation_artifact_dir,
        source_remediation_json=args.source_remediation_json,
        source_remediation_md=args.source_remediation_md,
        source_remediation_sha256s=args.source_remediation_sha256s,
        source_remediation_root_sha256s=args.source_remediation_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_remediation_root_sha256=args.expected_remediation_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation_static_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_remediation_artifact_dir: Path,
    source_remediation_json: Path,
    source_remediation_md: Path,
    source_remediation_sha256s: Path,
    source_remediation_root_sha256s: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_remediation_root_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_remediation_artifact_dir.resolve()
    source = _read_json(source_remediation_json)
    root_sha = _read_root_sha(source_remediation_root_sha256s)
    sha_entries = _read_sha256s(source_remediation_sha256s)
    sha_failures = _verify_sha256s(artifact, sha_entries)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    final = source.get("final_decision", {})
    plan = source.get("remediation_plan", {})
    assignments = plan.get("scene_assignments", {})
    preconditions = plan.get("larger_corpus_preconditions", {})

    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_remediation_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_remediation_json_path", source_remediation_json.resolve(), artifact / PLAN_MODULE.PLAN_JSON_NAME),
        _expect("source_remediation_md_path", source_remediation_md.resolve(), artifact / PLAN_MODULE.PLAN_MD_NAME),
        _expect("source_remediation_root_sha256", root_sha, expected_remediation_root_sha256),
        _check("source_remediation_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _expect("source_remediation_schema", source.get("schema_version"), SOURCE_REMEDIATION_SCHEMA_VERSION),
        _expect("source_remediation_status", source.get("status"), PLAN_MODULE.READY_STATUS),
        _expect("source_remediation_passed", final.get("passed"), True),
        _expect("source_authorizes_static_review", final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _contains("audit_authorizes_static_review", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_static_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_remediation", audit_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _contains("status_records_remediation", status_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _expect("policy_is_scene_level_smoke_split", plan.get("split_policy"), "scene_level_greedy_imbalance_tolerant_smoke_split"),
        _expect("split_unit_scene_level", plan.get("split_unit"), "scene_id"),
        _expect("record_level_split_not_executed", plan.get("record_level_split_executed"), False),
        _expect("exact_record_targets_rejected", plan.get("exact_record_count_targets_rejected"), True),
        _expect("scene_zero_overlap", plan.get("scene_zero_overlap"), True),
        _expect("sample_zero_overlap", plan.get("sample_zero_overlap"), True),
        _expect("assignments_match_expected", assignments, EXPECTED_ASSIGNMENTS),
        _expect("record_counts_match_expected", plan.get("actual_record_counts"), EXPECTED_COUNTS),
        _expect("train_has_scene", len(assignments.get("train", [])) >= 1, True),
        _expect("calibration_has_scene", len(assignments.get("calibration", [])) >= 1, True),
        _expect("holdout_has_scene", len(assignments.get("holdout", [])) >= 1, True),
        _expect("scene_sets_disjoint", _sets_disjoint(map(set, assignments.values())), True),
        _expect("pilot_split_is_smoke_only", plan.get("pilot_split_classification"), "imbalance_tolerant_smoke_split"),
        _expect("ten_k_requires_scene_diversity", preconditions.get("ten_k_generation_must_increase_scene_diversity"), True),
        _expect("min_scene_count_30", preconditions.get("minimum_scene_count_before_ratio_tracking"), 30),
        _expect("near_ratio_scene_count_30", preconditions.get("near_60_20_20_requires_scene_count_at_least"), 30),
    ]
    checks.extend(_no_forbidden_work_checks(final))
    for name in (
        PLAN_MODULE.PLAN_JSON_NAME,
        PLAN_MODULE.PLAN_MD_NAME,
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
    ):
        checks.append(_check(f"source_artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))

    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "source_remediation_artifact": str(artifact),
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "remediation_review": {
                "source_remediation_root_sha256": root_sha,
                "split_policy": plan.get("split_policy"),
                "split_unit": plan.get("split_unit"),
                "pilot_split_classification": plan.get("pilot_split_classification"),
                "record_level_split_executed": plan.get("record_level_split_executed"),
                "scene_zero_overlap": plan.get("scene_zero_overlap"),
                "sample_zero_overlap": plan.get("sample_zero_overlap"),
                "scene_assignments": assignments,
                "actual_record_counts": plan.get("actual_record_counts"),
                "actual_record_ratios": plan.get("actual_record_ratios"),
                "larger_corpus_preconditions": preconditions,
                "four_scene_split_formal_performance_proof_authorized": False,
            },
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
                "static_review_only": True,
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
    paths = (json_path, md_path, heads_path, command_path)
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in paths),
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["remediation_review"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Corpus Split Remediation Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source remediation artifact: `{report['source_remediation_artifact']}`",
            f"- Source remediation root SHA256: `{review['source_remediation_root_sha256']}`",
            f"- Split policy: `{review['split_policy']}`",
            f"- Scene assignments: `{review['scene_assignments']}`",
            f"- Actual record counts: `{review['actual_record_counts']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    review = report["remediation_review"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_REMEDIATION_ROOT_SHA256={review['source_remediation_root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect(f"source_remediation_{field}_false", final.get(field), False)
        for field in (
            "split_execution_executed",
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


def _sets_disjoint(sets: Any) -> bool:
    seen: set[Any] = set()
    for values in sets:
        if seen.intersection(values):
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
