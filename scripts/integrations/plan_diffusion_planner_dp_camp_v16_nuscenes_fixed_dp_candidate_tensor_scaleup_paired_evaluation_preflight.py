#!/usr/bin/env python3
"""Plan the v16 fixed-DP scale-up paired-evaluation preflight."""

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


SOURCE_REVIEW_MODULE = _load_module(
    "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result.py",
    "v16_scaleup_training_result_review",
)

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
EXPECTED_COUNTS = SOURCE_REVIEW_MODULE.EXPECTED_COUNTS
EXPECTED_K = SOURCE_REVIEW_MODULE.EXPECTED_K
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_SCHEMA_VERSION = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_READY_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
SOURCE_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_rejected"
AUTHORIZED_NEXT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_static_review_only"
)
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan_v1"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan.md"
REQUIRED_SOURCE_FILES = (
    SOURCE_JSON_NAME,
    SOURCE_MD_NAME,
    "HEADS",
    "COMMAND",
    "stdout.txt",
    "stderr.txt",
    "run.exit",
    "SHA256SUMS",
    "ROOT_SHA256SUMS",
)
METRICS_PLANNED = (
    "paired_rows_by_split",
    "better_tie_worse",
    "mean_delta",
    "ci95",
    "dp_top1_metric",
    "camp_selected_metric",
    "non_top1_selection_rate",
    "oracle_gap_closed",
    "selector_latency_mean_median_p95_p99_max",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_summary_json", type=Path, required=True)
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
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_artifact_dir=args.source_artifact_dir,
        source_summary_json=args.source_summary_json,
        source_sha256s=args.source_sha256s,
        source_root_sha256s=args.source_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_preflight_plan,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_artifact_dir: Path,
    source_summary_json: Path,
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
    sha_entries, sha_failures = _verify_sha256s(artifact, source_sha256s)
    root_sha = _read_root_sha(source_root_sha256s)
    audit_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8").split("## Current V15 Status", 1)[0]
    source_decision = source.get("final_decision", {})
    review = source.get("training_result_review", {})
    plan = _paired_evaluation_preflight_plan(review)
    checks = [
        _expect("scaleup_paired_evaluation_preflight_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _check("source_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_schema", source.get("schema_version"), SOURCE_SCHEMA_VERSION),
        _expect("source_status_passed", source.get("status"), SOURCE_READY_STATUS),
        _expect("source_final_passed", source_decision.get("passed"), True),
        _expect("source_authorizes_paired_eval_preflight_plan", source_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_root_sha256", root_sha, expected_source_root_sha256),
        _check("source_sha256s_verified", not sha_failures, sha_failures[:10], []),
        _contains("audit_authorizes_paired_eval_preflight_plan", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_paired_eval_preflight_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_training_result_review", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_training_result_review", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("train_records_6263", review.get("train_records"), EXPECTED_COUNTS["train"]),
        _expect("calibration_records_2156", review.get("calibration_records"), EXPECTED_COUNTS["calibration"]),
        _expect("holdout_records_1581", review.get("holdout_records"), EXPECTED_COUNTS["holdout"]),
        _expect("calibration_not_used_for_training", review.get("calibration_records_used_for_training"), 0),
        _expect("holdout_not_used_for_training", review.get("holdout_records_used_for_training"), 0),
        _expect("scene_zero_overlap", review.get("scene_zero_overlap"), True),
        _expect("sample_zero_overlap", review.get("sample_zero_overlap"), True),
        _expect("k_values_8", review.get("train_k_values"), [EXPECTED_K]),
        _expect("candidate_count_values_8", review.get("train_candidate_count_values"), [EXPECTED_K]),
        _expect("source_dp_head_fixed", review.get("source_dp_head") or source.get("heads", {}).get("dp_head"), FIXED_DP_HEAD),
        _expect("candidate_tensor_not_mutated", review.get("candidate_tensor_mutated_count"), 0),
        _expect("closed_loop_not_used_for_training", review.get("closed_loop_outcomes_used_for_training"), False),
        _expect("score_expression_affine", review.get("score_expression"), SCORE_EXPRESSION),
        _expect("weights_nonnegative", review.get("weights_nonnegative"), True),
        _expect("weights_sum_to_one", review.get("weights_sum_to_one"), True),
        _expect("approved_atoms_only", review.get("approved_atoms_only"), True),
        _expect("plan_primary_eval_splits", plan["primary_eval_splits"], ["calibration", "holdout"]),
        _expect("plan_train_reporting_only", plan["reporting_only_splits"], ["train"]),
        _expect("plan_primary_eval_total", plan["paired_rows_by_split"]["primary_eval_total"], 3737),
        _expect("plan_comparison_baseline", plan["comparison"]["baseline"], "dp_top1"),
        _expect("plan_scaleup_evidence_only", plan["scaleup_evidence_only"], True),
        _expect("plan_no_performance_claim", plan["claims"]["performance_claim_allowed"], False),
        _expect("plan_no_safety_claim", plan["claims"]["safety_claim_allowed"], False),
        _expect("plan_no_camp_over_dp_claim", plan["claims"]["camp_over_dp_claim_allowed"], False),
    ]
    checks.extend(_source_file_checks(artifact, source_summary_json, source_sha256s, source_root_sha256s))
    checks.extend(_no_forbidden_source_work_checks(source_decision))
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
            "training_result_review": review,
            "paired_evaluation_preflight_plan": plan,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "paired_evaluation_preflight_plan_only": True,
                "evaluation_executed": False,
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
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    heads_path = output_dir / "HEADS"
    command_path = output_dir / "COMMAND"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    heads_path.write_text(_render_heads(report), encoding="utf-8")
    command_path.write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _paired_evaluation_preflight_plan(review: dict[str, Any]) -> dict[str, Any]:
    calibration = review.get("calibration_records")
    holdout = review.get("holdout_records")
    train = review.get("train_records")
    return {
        "primary_eval_splits": ["calibration", "holdout"],
        "reporting_only_splits": ["train"],
        "paired_rows_by_split": {
            "calibration": calibration,
            "holdout": holdout,
            "primary_eval_total": calibration + holdout if isinstance(calibration, int) and isinstance(holdout, int) else None,
            "train_reporting_only": train,
        },
        "comparison": {
            "camp_selection": "camp_selected_fixed_dp_candidate",
            "baseline": "dp_top1",
            "candidate_source": "fixed_dp_candidate_tensor",
        },
        "metrics_planned": list(METRICS_PLANNED),
        "scaleup_evidence_only": True,
        "claims": {
            "performance_claim_allowed": False,
            "safety_claim_allowed": False,
            "camp_over_dp_claim_allowed": False,
            "reason": "scale-up calibration+holdout evaluation is planned only; no claim until execution and result review pass",
        },
        "pass_fail_conditions": {
            "no_train_leakage_into_primary_eval": True,
            "k": EXPECTED_K,
            "candidate_count": EXPECTED_K,
            "dp_head_fixed": FIXED_DP_HEAD,
            "candidate_tensor_hashes_present": True,
            "no_candidate_mutation": True,
            "affine_simplex_checks_pass": True,
        },
        "planned_outputs": {
            "plan_json": PLAN_JSON_NAME,
            "plan_md": PLAN_MD_NAME,
            "heads": "HEADS",
            "command": "COMMAND",
            "stdout": "stdout.txt",
            "stderr": "stderr.txt",
            "sha256s": "SHA256SUMS",
        },
        "forbidden_work": [
            "dp_modification",
            "candidate_tensor_mutation",
            "new_candidate_generation",
            "evaluation_execution",
            "promotion",
            "deployment",
            "performance_claim",
            "safety_claim",
            "camp_over_dp_claim",
        ],
    }


def _source_file_checks(
    artifact: Path,
    source_summary_json: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
) -> list[dict[str, Any]]:
    checks = []
    expected_paths = {
        SOURCE_JSON_NAME: source_summary_json.resolve(),
        "SHA256SUMS": source_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_root_sha256s.resolve(),
    }
    for name in REQUIRED_SOURCE_FILES:
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if name in expected_paths:
            checks.append(_expect(f"source_artifact_path_{name}", expected_paths[name], path.resolve()))
    return checks


def _no_forbidden_source_work_checks(final: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        _expect("source_result_review_only", final.get("result_review_only"), True),
        _expect("source_training_executed_by_review_false", final.get("training_executed_by_review"), False),
    ]
    for field in (
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
    plan = report["paired_evaluation_preflight_plan"]
    rows = plan["paired_rows_by_split"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Scale-Up Paired-Evaluation Preflight Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- Scope: plan only; no evaluation execution, claim, promotion, or deployment.",
            f"- Primary eval splits: `{plan['primary_eval_splits']}`",
            f"- Reporting-only splits: `{plan['reporting_only_splits']}`",
            f"- Paired rows calibration/holdout/primary: `{rows['calibration']} / {rows['holdout']} / {rows['primary_eval_total']}`",
            f"- Train reporting-only rows: `{rows['train_reporting_only']}`",
            f"- Comparison: `{plan['comparison']['camp_selection']} vs {plan['comparison']['baseline']}`",
            f"- Metrics planned: `{plan['metrics_planned']}`",
            f"- Scale-up evidence only: `{plan['scaleup_evidence_only']}`",
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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0].split()[0] if lines else None


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
