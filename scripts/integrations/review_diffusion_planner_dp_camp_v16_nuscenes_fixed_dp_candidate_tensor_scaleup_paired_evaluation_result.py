#!/usr/bin/env python3
"""Review the v16 fixed-DP scale-up paired-evaluation execution result."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
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
    "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation.py",
    "v16_scaleup_paired_eval_execution",
)

FIXED_DP_HEAD = SOURCE_MODULE.FIXED_DP_HEAD
EXPECTED_COUNTS = SOURCE_MODULE.EXPECTED_COUNTS
EXPECTED_K = SOURCE_MODULE.EXPECTED_K
SCORE_EXPRESSION = SOURCE_MODULE.SCORE_EXPRESSION
SOURCE_SCHEMA_VERSION = SOURCE_MODULE.SCHEMA_VERSION
SOURCE_READY_STATUS = SOURCE_MODULE.READY_STATUS
AUTHORIZED_CURRENT_WORK = SOURCE_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_only"
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review_v1"
SOURCE_JSON_NAME = SOURCE_MODULE.EXECUTION_JSON_NAME
SOURCE_MD_NAME = SOURCE_MODULE.EXECUTION_MD_NAME
SOURCE_ROWS_JSONL_NAME = SOURCE_MODULE.PAIRED_ROWS_JSONL_NAME
SOURCE_SPLIT_METRICS_JSON_NAME = SOURCE_MODULE.SPLIT_METRICS_JSON_NAME
SOURCE_LATENCY_JSON_NAME = SOURCE_MODULE.LATENCY_JSON_NAME
SOURCE_TIMING_JSON_NAME = SOURCE_MODULE.TIMING_JSON_NAME
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review.md"
EXPECTED_BETTER_TIE_WORSE = {"better": 3365, "tie": 359, "worse": 13}
EXPECTED_MEAN_DELTA = -0.01762098077036227
EXPECTED_NON_TOP1_SELECTION_RATE = 0.903933636606904
EXPECTED_ORACLE_GAP_CLOSED = 0.9619006786247026
REQUIRED_SOURCE_FILES = (
    SOURCE_JSON_NAME,
    SOURCE_MD_NAME,
    SOURCE_ROWS_JSONL_NAME,
    SOURCE_SPLIT_METRICS_JSON_NAME,
    SOURCE_LATENCY_JSON_NAME,
    SOURCE_TIMING_JSON_NAME,
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
    parser.add_argument("--source_rows_jsonl", type=Path, required=True)
    parser.add_argument("--source_split_metrics_json", type=Path, required=True)
    parser.add_argument("--source_latency_json", type=Path, required=True)
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
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_artifact_dir=args.source_artifact_dir,
        source_summary_json=args.source_summary_json,
        source_rows_jsonl=args.source_rows_jsonl,
        source_split_metrics_json=args.source_split_metrics_json,
        source_latency_json=args.source_latency_json,
        source_sha256s=args.source_sha256s,
        source_root_sha256s=args.source_root_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_source_root_sha256=args.expected_source_root_sha256,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_paired_evaluation_result_review,
    )
    report["command"] = sys.argv
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_artifact_dir: Path,
    source_summary_json: Path,
    source_rows_jsonl: Path,
    source_split_metrics_json: Path,
    source_latency_json: Path,
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
    rows = _read_jsonl(source_rows_jsonl)
    split_metrics = _read_json(source_split_metrics_json)
    latency = _read_json(source_latency_json)
    sha_entries, sha_failures = _verify_sha256s(artifact, source_sha256s)
    root_sha = _read_root_sha(source_root_sha256s)
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    review = _paired_evaluation_result_review(source, rows, split_metrics, latency)
    source_final = source.get("final_decision", {})
    source_execution = source.get("scaleup_paired_evaluation_execution", {})
    primary_metrics = review["primary_metrics"]
    checks = [
        _expect("paired_evaluation_result_review_enabled", enabled, True),
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
        _contains("audit_records_paired_eval_execution", audit_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _contains("status_records_paired_eval_execution", status_text, f"current_v16_status={SOURCE_READY_STATUS}"),
        _expect("primary_eval_rows_3737", review["primary_eval_rows"], EXPECTED_COUNTS["calibration"] + EXPECTED_COUNTS["holdout"]),
        _expect("calibration_rows_2156", review["calibration_rows"], EXPECTED_COUNTS["calibration"]),
        _expect("holdout_rows_1581", review["holdout_rows"], EXPECTED_COUNTS["holdout"]),
        _expect("train_reporting_only_rows_6263", review["train_reporting_only_rows"], EXPECTED_COUNTS["train"]),
        _expect("train_rows_excluded_from_primary_eval", review["train_rows_in_primary_eval"], 0),
        _expect("source_primary_rows_3737", source_execution.get("paired_rows_by_split", {}).get("primary_eval_total"), 3737),
        _expect("source_calibration_rows_2156", source_execution.get("paired_rows_by_split", {}).get("calibration"), 2156),
        _expect("source_holdout_rows_1581", source_execution.get("paired_rows_by_split", {}).get("holdout"), 1581),
        _expect("source_train_reporting_only_6263", source_execution.get("paired_rows_by_split", {}).get("train_reporting_only"), 6263),
        _expect("primary_eval_splits_calibration_holdout", source_execution.get("primary_eval_splits"), ["calibration", "holdout"]),
        _expect("reporting_only_splits_train", source_execution.get("reporting_only_splits"), ["train"]),
        _expect("k_values_8", review["k_values"], [EXPECTED_K]),
        _expect("candidate_count_values_8", review["candidate_count_values"], [EXPECTED_K]),
        _expect("dp_head_values_fixed", review["dp_head_values"], [FIXED_DP_HEAD]),
        _expect("candidate_tensor_hashes_present", review["candidate_tensor_missing_hash_count"], 0),
        _expect("candidate_tensor_not_mutated", review["candidate_tensor_mutated_count"], 0),
        _expect("selected_index_in_range", review["selected_index_out_of_range_count"], 0),
        _expect("score_expression", review["score_expression"], SCORE_EXPRESSION),
        _expect("weights_nonnegative", review["weights_nonnegative"], True),
        _expect("weights_sum_to_one", review["weights_sum_to_one"], True),
        _expect("approved_atoms_only", review["approved_atoms_only"], True),
        _expect("better_tie_worse", primary_metrics.get("better_tie_worse"), EXPECTED_BETTER_TIE_WORSE),
        _approx("mean_delta", primary_metrics.get("mean_delta"), EXPECTED_MEAN_DELTA),
        _check("ci95_high_negative", _number(primary_metrics.get("ci95", {}).get("high")) < 0.0, primary_metrics.get("ci95"), "high < 0"),
        _approx("non_top1_selection_rate", primary_metrics.get("non_top1_selection_rate"), EXPECTED_NON_TOP1_SELECTION_RATE),
        _approx("oracle_gap_closed", primary_metrics.get("oracle_gap_closed"), EXPECTED_ORACLE_GAP_CLOSED),
        _expect("latency_count_3737", review["latency_summary"].get("count"), 3737),
        _check("latency_summary_present", all(key in review["latency_summary"] for key in ("mean", "median", "p95", "p99", "max")), review["latency_summary"], "latency summary"),
        _expect("rows_better_tie_worse_match_metrics", review["rows_better_tie_worse"], primary_metrics.get("better_tie_worse")),
        _approx("rows_mean_delta_matches_metrics", review["rows_mean_delta"], primary_metrics.get("mean_delta")),
        _expect("descriptive_paired_metrics_only", review["descriptive_paired_metrics_only"], True),
    ]
    checks.extend(_source_file_checks(artifact, source_summary_json, source_rows_jsonl, source_split_metrics_json, source_latency_json, source_sha256s, source_root_sha256s))
    checks.extend(_no_claim_checks(source_final, source_execution))
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
                "rows_jsonl": str(source_rows_jsonl.resolve()),
                "split_metrics_json": str(source_split_metrics_json.resolve()),
                "latency_json": str(source_latency_json.resolve()),
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
            "paired_evaluation_result_review": review,
            "checks": checks,
            "final_decision": {
                "passed": passed,
                "status": READY_STATUS if passed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
                "result_review_only": True,
                "paired_evaluation_executed_by_review": False,
                "training_executed": False,
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
    (output_dir / REVIEW_JSON_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / REVIEW_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    _write_sha_manifest(output_dir)


def _paired_evaluation_result_review(
    source: dict[str, Any],
    rows: list[dict[str, Any]],
    split_metrics: dict[str, Any],
    latency: dict[str, Any],
) -> dict[str, Any]:
    execution = source.get("scaleup_paired_evaluation_execution", {})
    primary = split_metrics.get("primary", {})
    rows_by_split = {
        "calibration": [row for row in rows if row.get("split") == "calibration"],
        "holdout": [row for row in rows if row.get("split") == "holdout"],
        "train": [row for row in rows if row.get("split") == "train"],
    }
    return {
        "source_summary_metrics_match_file": source.get("split_metrics", {}).get("primary") == primary,
        "primary_eval_rows": len(rows_by_split["calibration"]) + len(rows_by_split["holdout"]),
        "calibration_rows": len(rows_by_split["calibration"]),
        "holdout_rows": len(rows_by_split["holdout"]),
        "train_reporting_only_rows": execution.get("paired_rows_by_split", {}).get("train_reporting_only"),
        "train_rows_in_primary_eval": len(rows_by_split["train"]),
        "k_values": _unique(row.get("k", row.get("K")) for row in rows),
        "candidate_count_values": _unique(row.get("candidate_count") for row in rows),
        "dp_head_values": _unique(row.get("fixed_dp_head", row.get("DP_HEAD")) for row in rows),
        "candidate_tensor_missing_hash_count": sum(1 for row in rows if not row.get("candidate_tensor_sha256")),
        "candidate_tensor_mutated_count": sum(1 for row in rows if row.get("candidate_tensor_unchanged_by_camp") is not True),
        "selected_index_out_of_range_count": sum(1 for row in rows if not _selected_index_in_range(row)),
        "score_expression": execution.get("score_expression"),
        "weights_nonnegative": execution.get("weights_nonnegative"),
        "weights_sum_to_one": execution.get("weights_sum_to_one"),
        "approved_atoms_only": execution.get("approved_atoms_only"),
        "primary_metrics": primary,
        "rows_better_tie_worse": {
            "better": sum(1 for row in rows if row.get("outcome") == "better"),
            "tie": sum(1 for row in rows if row.get("outcome") == "tie"),
            "worse": sum(1 for row in rows if row.get("outcome") == "worse"),
        },
        "rows_mean_delta": _mean(row.get("delta") for row in rows),
        "latency_summary": latency,
        "descriptive_paired_metrics_only": execution.get("scaleup_evidence_only") is True,
        "no_performance_claim": source.get("final_decision", {}).get("performance_claimed") is False,
        "no_safety_claim": source.get("final_decision", {}).get("safety_claimed") is False,
        "no_camp_over_dp_claim": source.get("final_decision", {}).get("camp_over_dp_claimed") is False,
        "no_promotion": source.get("final_decision", {}).get("promotion_executed") is False,
        "no_deployment": source.get("final_decision", {}).get("deployment_executed") is False,
        "recommended_next_gate": AUTHORIZED_NEXT_WORK,
    }


def _source_file_checks(
    artifact: Path,
    source_summary_json: Path,
    source_rows_jsonl: Path,
    source_split_metrics_json: Path,
    source_latency_json: Path,
    source_sha256s: Path,
    source_root_sha256s: Path,
) -> list[dict[str, Any]]:
    expected_paths = {
        SOURCE_JSON_NAME: source_summary_json.resolve(),
        SOURCE_ROWS_JSONL_NAME: source_rows_jsonl.resolve(),
        SOURCE_SPLIT_METRICS_JSON_NAME: source_split_metrics_json.resolve(),
        SOURCE_LATENCY_JSON_NAME: source_latency_json.resolve(),
        "SHA256SUMS": source_sha256s.resolve(),
        "ROOT_SHA256SUMS": source_root_sha256s.resolve(),
    }
    checks = []
    for name in REQUIRED_SOURCE_FILES:
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if name in expected_paths:
            checks.append(_expect(f"source_artifact_path_{name}", expected_paths[name], path.resolve()))
    return checks


def _no_claim_checks(final: dict[str, Any], execution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("source_paired_evaluation_executed", final.get("paired_evaluation_executed"), True),
        _expect("source_training_executed_false", final.get("training_executed"), False),
        _expect("source_performance_claim_false", final.get("performance_claimed"), False),
        _expect("source_safety_claim_false", final.get("safety_claimed"), False),
        _expect("source_camp_over_dp_claim_false", final.get("camp_over_dp_claimed"), False),
        _expect("source_promotion_false", final.get("promotion_executed"), False),
        _expect("source_deployment_false", final.get("deployment_executed"), False),
        _expect("source_dp_modified_false", final.get("dp_modified"), False),
        _expect("source_candidate_tensor_modified_false", final.get("candidate_tensor_modified"), False),
        _expect("source_fake_candidate_tensor_generated_false", final.get("fake_candidate_tensor_generated"), False),
        _expect("source_scaleup_evidence_only_true", execution.get("scaleup_evidence_only"), True),
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
        name = rel.strip()
        path = root / name
        if not path.is_file():
            failed.append(f"missing:{name}")
        elif _sha256(path) != expected:
            failed.append(f"mismatch:{name}")
    return count, failed


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["paired_evaluation_result_review"]
    metrics = review["primary_metrics"]
    latency = review["latency_summary"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Scale-Up Paired-Evaluation Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Source artifact: `{report['source_artifact']['path']}`",
            f"- Source root SHA256: `{report['source_artifact']['root_sha256']}`",
            f"- Rows: `calibration={review['calibration_rows']}, holdout={review['holdout_rows']}, primary={review['primary_eval_rows']}`",
            f"- Train rows: `{review['train_reporting_only_rows']}` reporting-only",
            f"- Better/tie/worse: `{metrics.get('better_tie_worse')}`",
            f"- Mean delta: `{metrics.get('mean_delta')}`",
            f"- CI95: `{metrics.get('ci95')}`",
            f"- Non-Top1 selection rate: `{metrics.get('non_top1_selection_rate')}`",
            f"- Oracle gap closed: `{metrics.get('oracle_gap_closed')}`",
            f"- Latency mean/median/p95/p99/max ms: `{latency.get('mean')} / {latency.get('median')} / {latency.get('p95')} / {latency.get('p99')} / {latency.get('max')}`",
            "- Descriptive paired metrics only. No performance, safety, or CAMP-over-DP claim is made.",
            "- No promotion or deployment is authorized.",
            "- Recommended next gate: scale-up evidence package plan only.",
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
    root_path.write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _selected_index_in_range(row: dict[str, Any]) -> bool:
    if row.get("selected_index_in_range") is False:
        return False
    selected = row.get("selected_index")
    count = row.get("candidate_count")
    return isinstance(selected, int) and isinstance(count, int) and 0 <= selected < count


def _mean(values: Any) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    return statistics.fmean(numbers) if numbers else None


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def _approx(name: str, actual: Any, expected: Any, *, abs_tol: float = 1e-12) -> dict[str, Any]:
    actual_value = _number(actual)
    expected_value = _number(expected)
    return _check(name, abs(actual_value - expected_value) <= abs_tol, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _unique(values: Any) -> list[Any]:
    return sorted({_json_key(value): value for value in values}.values(), key=_json_key)


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


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
