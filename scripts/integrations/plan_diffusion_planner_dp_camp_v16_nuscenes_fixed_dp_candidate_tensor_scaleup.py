#!/usr/bin/env python3
"""Plan the v16 nuScenes fixed-DP candidate tensor scale-up gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


def _load_source_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result.py"
    )
    spec = importlib.util.spec_from_file_location("v16_package_result_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_MODULE = _load_source_module()
FIXED_DP_HEAD = SOURCE_MODULE.FIXED_DP_HEAD
SOURCE_SCHEMA_VERSION = SOURCE_MODULE.SCHEMA_VERSION
SOURCE_READY_STATUS = SOURCE_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_MODULE.AUTHORIZED_NEXT_WORK
SOURCE_JSON_NAME = SOURCE_MODULE.REVIEW_JSON_NAME
SOURCE_MD_NAME = SOURCE_MODULE.REVIEW_MD_NAME
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan_static_review_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan_v1"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan.md"
PER_RECORD_SECONDS = 5.31974
PILOT_RECORDS = 1024
PILOT_DISTINCT_SCENES = 4
SELECTED_TARGET_RECORDS = 10000
SELECTED_MINIMUM_SCENES = 30
OPTIONAL_STAGES = ((32000, 90), (100000, 90))


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
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan", action="store_true")
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
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan,
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
    source_artifact = source_result_review_artifact_dir.resolve()
    source = _read_json(source_result_review_json)
    source_final = source.get("final_decision", {})
    review = source.get("pilot_evidence_package_result_review", {})
    source_sha_entries, source_sha_failures = _verify_sha256s(source_artifact, source_result_review_sha256s)
    source_root_sha = _read_root_sha(source_result_review_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    plan = _scaleup_plan(review)
    checks = [
        _expect("scaleup_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_result_review_artifact_exists", source_artifact.is_dir(), str(source_artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", source_final.get("passed"), True),
        _expect("source_authorizes_scaleup_plan", source_final.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_result_review_root_sha256", source_root_sha, expected_source_root_sha256),
        _check("source_result_review_sha256s_verified", not source_sha_failures, source_sha_failures[:10], []),
        _contains("audit_authorizes_scaleup_plan", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_scaleup_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_package_result_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_package_result_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("source_artifact_count_10", review.get("source_artifact_count"), 10),
        _expect("source_sha_verified", review.get("all_source_artifact_sha_verified"), True),
        _expect("source_dp_heads_fixed", review.get("all_source_dp_heads_fixed"), True),
        _expect("source_candidate_unmodified", review.get("candidate_tensor_unmodified"), True),
        _expect("source_k_candidate_count", review.get("k_candidate_count"), [8, 8]),
        _expect("source_train_rows_excluded", review.get("train_rows_in_primary_eval"), 0),
        _expect("source_affine_simplex_preserved", review.get("affine_simplex_preserved"), True),
        _expect("selected_target_records", plan["selected_stage"]["target_records"], SELECTED_TARGET_RECORDS),
        _expect("selected_minimum_scenes", plan["selected_stage"]["minimum_distinct_scenes"], SELECTED_MINIMUM_SCENES),
        _expect("selected_k", plan["selected_stage"]["k"], 8),
        _expect("selected_candidate_count", plan["selected_stage"]["candidate_count"], 8),
        _expect("selected_hours", plan["selected_stage"]["estimated_wall_clock_hours"], 14.8),
        _expect("optional_32k_hours", plan["optional_stages"][0]["estimated_wall_clock_hours"], 47.3),
        _expect("optional_100k_hours", plan["optional_stages"][1]["estimated_wall_clock_hours"], 147.8),
        _expect("source_policy_prefers_scenes", plan["source_selection_policy"]["prefer_more_scenes_over_more_records_per_scene"], True),
        _expect("split_scene_level_zero_overlap", plan["split_policy"]["scene_level_zero_overlap"], True),
        _expect("split_no_record_leakage", plan["split_policy"]["record_level_leakage_allowed"], False),
        _expect("pass_checks_dp_head_fixed", plan["pass_checks"]["dp_head_fixed"], FIXED_DP_HEAD),
        _expect("pass_checks_k_candidate", plan["pass_checks"]["k_candidate_count"], [8, 8]),
        _expect("pass_checks_failure_count", plan["pass_checks"]["failure_count"], 0),
        _expect("pass_checks_min_scenes", plan["pass_checks"]["minimum_distinct_scenes"], SELECTED_MINIMUM_SCENES),
        _expect("pass_checks_source_sha", plan["pass_checks"]["source_artifact_sha_verified"], True),
    ]
    checks.extend(_source_file_checks(source_artifact, source_result_review_json, source_result_review_sha256s, source_result_review_root_sha256s))
    checks.extend(_no_forbidden_work_checks(source_final))
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifact": {
                "path": str(source_artifact),
                "summary_json": str(source_result_review_json.resolve()),
                "root_sha256": source_root_sha,
                "expected_root_sha256": expected_source_root_sha256,
                "sha256_entry_count": source_sha_entries,
                "failed_sha256s": source_sha_failures,
                "sha256s_sha256": _sha256(source_result_review_sha256s) if source_result_review_sha256s.is_file() else None,
                "root_sha256s_sha256": _sha256(source_result_review_root_sha256s) if source_result_review_root_sha256s.is_file() else None,
            },
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
                "source_camp_head": source.get("heads", {}).get("camp_head"),
            },
            "scaleup_plan": plan,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "scaleup_plan_only": True,
                "scale_up_executed": False,
                "candidate_generation_executed": False,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
                "safety_claimed": False,
                "camp_over_dp_claimed": False,
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
    (output_dir / PLAN_JSON_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / PLAN_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _scaleup_plan(review: dict[str, Any]) -> dict[str, Any]:
    selected = _stage(SELECTED_TARGET_RECORDS, SELECTED_MINIMUM_SCENES)
    optional_32k = _stage(32000, 90)
    optional_100k = {
        "target_records": 100000,
        "minimum_distinct_scenes": 90,
        "k": 8,
        "candidate_count": 8,
        "estimated_wall_clock_hours": _hours(100000),
        "condition": "only if runtime and cost are acceptable after the 32k review",
    }
    return {
        "baseline": {
            "pilot_records": PILOT_RECORDS,
            "pilot_distinct_scenes": PILOT_DISTINCT_SCENES,
            "pilot_primary_eval_rows": review.get("smoke_metrics_summary", {}).get("primary_eval_rows"),
            "pilot_better_tie_worse": review.get("smoke_metrics_summary", {}).get("better_tie_worse"),
            "pilot_mean_delta": review.get("smoke_metrics_summary", {}).get("mean_delta"),
            "pilot_ci95": review.get("smoke_metrics_summary", {}).get("ci95"),
            "pilot_oracle_gap_closed": review.get("smoke_metrics_summary", {}).get("oracle_gap_closed"),
        },
        "per_record_timing_seconds": PER_RECORD_SECONDS,
        "selected_stage": selected,
        "optional_stages": [optional_32k, optional_100k],
        "source_selection_policy": {
            "prefer_more_scenes_over_more_records_per_scene": True,
            "cap_records_per_scene": True,
            "keep_scene_ids_unique": True,
            "keep_sample_ids_unique": True,
            "avoid_four_scene_imbalance_repeat": True,
        },
        "split_policy": {
            "scene_level_zero_overlap": True,
            "target_ratio": "60/20/20",
            "apply_ratio_only_when_scene_count_sufficient": True,
            "record_level_leakage_allowed": False,
        },
        "pass_checks": {
            "dp_head_fixed": FIXED_DP_HEAD,
            "no_dp_modification": True,
            "no_candidate_tensor_mutation": True,
            "k_candidate_count": [8, 8],
            "failure_count": 0,
            "minimum_distinct_scenes": SELECTED_MINIMUM_SCENES,
            "source_artifact_sha_verified": review.get("all_source_artifact_sha_verified") is True,
        },
        "stop_conditions": [
            "output root exists",
            "DP HEAD mismatch",
            "records shortfall",
            "scene count shortfall",
            "candidate tensor mutation",
            "fake/synthetic candidate tensor",
            "runtime/cost too high",
        ],
    }


def _stage(records: int, minimum_scenes: int) -> dict[str, Any]:
    return {
        "target_records": records,
        "minimum_distinct_scenes": minimum_scenes,
        "k": 8,
        "candidate_count": 8,
        "estimated_wall_clock_hours": _hours(records),
        "max_records_per_scene": math.ceil(records / minimum_scenes),
    }


def _hours(records: int) -> float:
    return round(records * PER_RECORD_SECONDS / 3600.0, 1)


def _source_file_checks(
    artifact: Path,
    source_summary_json: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
) -> list[dict[str, Any]]:
    expected_paths = {
        SOURCE_JSON_NAME: source_summary_json.resolve(),
        "SHA256SUMS": source_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_root_sha256s.resolve(),
    }
    checks = []
    for name in (SOURCE_JSON_NAME, SOURCE_MD_NAME, "HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", "SHA256SUMS", "ROOT_SHA256SUMS"):
        path = artifact / name
        checks.append(_check(f"source_result_review_has_{name}", path.is_file(), str(path), "file"))
        if name in expected_paths:
            checks.append(_expect(f"source_result_review_path_{name}", expected_paths[name], path.resolve()))
    return checks


def _no_forbidden_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [_expect("source_result_review_only", final.get("result_review_only"), True)]
    for field in (
        "scale_up_executed",
        "training_executed",
        "paired_evaluation_executed",
        "performance_claimed",
        "safety_claimed",
        "camp_over_dp_claimed",
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
        name = rel.strip()
        path = root / name
        if not path.is_file():
            failed.append(f"missing:{name}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{name}")
    return count, failed


def _write_sha_manifest(output_dir: Path) -> None:
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path in (sha_path, root_path):
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["scaleup_plan"]
    selected = plan["selected_stage"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Scale-Up Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- Scope: plan only. No scale-up execution, candidate corpus generation, training, evaluation, claim, promotion, or deployment.",
            f"- Selected target: `{selected['target_records']}` records, minimum `{selected['minimum_distinct_scenes']}` distinct scenes, K/candidate_count `8/8`.",
            f"- Estimated wall-clock: `10k={selected['estimated_wall_clock_hours']}h`, `32k={plan['optional_stages'][0]['estimated_wall_clock_hours']}h`, `100k={plan['optional_stages'][1]['estimated_wall_clock_hours']}h`.",
            "- Source policy: prefer more scenes over more records per scene; cap records per scene; keep scene/sample IDs unique.",
            "- Split policy: scene-level zero-overlap; 60/20/20 only when scene count is sufficient; no record-level leakage.",
            f"- Stop conditions: `{plan['stop_conditions']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    source = report["source_artifact"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"SOURCE_CAMP_HEAD={heads['source_camp_head']}",
            f"SOURCE_ROOT_SHA256={source['root_sha256']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


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
