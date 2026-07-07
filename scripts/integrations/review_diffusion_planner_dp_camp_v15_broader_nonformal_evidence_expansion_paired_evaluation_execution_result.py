#!/usr/bin/env python3
"""Review the v15 paired-evaluation execution artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_execution_module():
    path = Path(__file__).resolve().with_name(
        "execute_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation.py"
    )
    spec = importlib.util.spec_from_file_location("v15_paired_evaluation_execution", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


EXECUTION_MODULE = _load_execution_module()

FIXED_DP_HEAD = EXECUTION_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result_review_v1"
AUTHORIZED_CURRENT_WORK = EXECUTION_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result_review_passed"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_record_only"
REVIEW_JSON_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result_review.json"
REVIEW_MD_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result_review.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_execution_json", type=Path, required=True)
    parser.add_argument("--source_execution_md", type=Path, required=True)
    parser.add_argument("--source_rows_jsonl", type=Path, required=True)
    parser.add_argument("--source_split_metrics", type=Path, required=True)
    parser.add_argument("--source_scenario_bucket_metrics", type=Path, required=True)
    parser.add_argument("--source_online_latency_json", type=Path, required=True)
    parser.add_argument("--source_fallback_latency_json", type=Path, required=True)
    parser.add_argument("--source_timing_json", type=Path, required=True)
    parser.add_argument("--source_timing_md", type=Path, required=True)
    parser.add_argument("--source_sha256s", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_execution_artifact_dir=args.source_execution_artifact_dir,
        source_execution_json=args.source_execution_json,
        source_execution_md=args.source_execution_md,
        source_rows_jsonl=args.source_rows_jsonl,
        source_split_metrics=args.source_split_metrics,
        source_scenario_bucket_metrics=args.source_scenario_bucket_metrics,
        source_online_latency_json=args.source_online_latency_json,
        source_fallback_latency_json=args.source_fallback_latency_json,
        source_timing_json=args.source_timing_json,
        source_timing_md=args.source_timing_md,
        source_sha256s=args.source_sha256s,
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_rows_jsonl: Path,
    source_split_metrics: Path,
    source_scenario_bucket_metrics: Path,
    source_online_latency_json: Path,
    source_fallback_latency_json: Path,
    source_timing_json: Path,
    source_timing_md: Path,
    source_sha256s: Path,
    v15_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_execution_artifact_dir.resolve()
    execution = _read_json(source_execution_json)
    rows = _read_jsonl(source_rows_jsonl)
    split_metrics = _read_json(source_split_metrics)
    scenario_metrics = _read_json(source_scenario_bucket_metrics)
    online_latency = _read_json(source_online_latency_json)
    fallback_latency = _read_json(source_fallback_latency_json)
    timing = _read_json(source_timing_json)
    sha256s = _read_sha256s(source_sha256s)
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    decision = execution["final_decision"]

    checks = [
        _expect("result_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_execution_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_execution_schema", execution.get("schema_version"), EXECUTION_MODULE.SCHEMA_VERSION),
        _expect("source_execution_passed", decision.get("passed"), True),
        _expect("source_execution_authorized_review", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_execution_executed", decision.get("paired_evaluation_execution_executed"), True),
        _expect("source_training_available", decision.get("source_training_executed"), True),
        _expect("source_training_not_run_by_execution", decision.get("training_executed"), False),
        _expect("source_paired_eval_executed", decision.get("paired_evaluation_executed"), True),
        _expect("source_online_latency_executed", decision.get("online_selector_latency_executed"), True),
        _expect("source_fallback_latency_executed", decision.get("fallback_latency_executed"), True),
        _expect("source_performance_not_claimed", decision.get("performance_claimed"), False),
        _expect("source_full36_not_used", decision.get("full36_used"), False),
        _expect("source_formal_seed_not_used", decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_dp_not_modified", decision.get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", decision.get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", decision.get("trajectory_modified"), False),
        _contains("audit_authorizes_review", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _expect("paired_row_count_matches_rows", execution["paired_evaluation"].get("row_count"), len(rows)),
        _expect("source_evaluation_splits", tuple(execution["paired_evaluation"].get("evaluation_splits") or ()), EXECUTION_MODULE.EVALUATION_SPLITS),
        _expect("source_train_rows_excluded", split_metrics["train"].get("row_count"), 0),
        _expect("source_calibration_rows", split_metrics["calibration"].get("row_count"), 144 if len(rows) == 288 else 1),
        _expect("source_holdout_rows", split_metrics["holdout"].get("row_count"), 144 if len(rows) == 288 else 1),
        _expect("online_latency_count", online_latency.get("count"), len(rows)),
        _expect("fallback_latency_count", fallback_latency.get("count"), len(rows)),
        _expect("timing_matches_online_latency", timing.get("online_selector_latency"), online_latency),
        _expect("timing_matches_fallback_latency", timing.get("fallback_latency"), fallback_latency),
        _expect("timing_behavior_unchanged", timing.get("instrumentation_changes_selector_behavior"), False),
        _expect("split_metrics_no_performance_claim", _any_performance_claim(split_metrics), False),
        _expect("scenario_metrics_no_performance_claim", _any_performance_claim(scenario_metrics), False),
        _expect("rows_no_performance_claim", any(row.get("performance_claim") for row in rows), False),
        _expect("rows_no_candidate_tensor_mutation", any(row.get("candidate_tensor_modified") for row in rows), False),
        _expect("rows_no_trajectory_mutation", any(row.get("trajectory_modified") for row in rows), False),
        _expect("rows_no_dp_modification", any(row.get("dp_modified") for row in rows), False),
        _expect("rows_exclude_train_split", any(row.get("split") == "train" for row in rows), False),
    ]
    for path in (
        source_execution_json,
        source_execution_md,
        source_rows_jsonl,
        source_split_metrics,
        source_scenario_bucket_metrics,
        source_online_latency_json,
        source_fallback_latency_json,
        source_timing_json,
        source_timing_md,
    ):
        checks.append(_expect(f"source_sha_{path.name}", _sha256(path), sha256s[path.name]))
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit"):
        checks.append(_check(f"source_artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "source_execution_artifact": str(artifact),
            "result_review": {
                "paired_rows": len(rows),
                "calibration_rows": split_metrics["calibration"].get("row_count"),
                "holdout_rows": split_metrics["holdout"].get("row_count"),
                "train_rows": split_metrics["train"].get("row_count"),
                "promotion_supported": False,
                "performance_claim": False,
                "closeout_classification": "no_promotion_no_claim",
            },
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "reviewed_paired_evaluation_execution": True,
                "source_paired_evaluation_executed": bool(decision.get("paired_evaluation_executed")),
                "paired_evaluation_executed": False,
                "training_executed": False,
                "online_selector_latency_executed": False,
                "fallback_latency_executed": False,
                "performance_claimed": False,
                "promotion_supported": False,
                "closeout_record_authorized": not failed,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        f"{_sha256(json_path)}  {json_path.name}\n{_sha256(md_path)}  {md_path.name}\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["result_review"]
    return "\n".join(
        [
            "# V15 Paired Evaluation Execution Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Paired rows: `{review['paired_rows']}`",
            f"- Promotion supported: `{review['promotion_supported']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
        ]
    )


def _any_performance_claim(metrics: dict[str, Any]) -> bool:
    return any(value.get("performance_claim") for value in metrics.values())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_sha256s(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            entries[Path(name.strip()).name] = digest
    return entries


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
