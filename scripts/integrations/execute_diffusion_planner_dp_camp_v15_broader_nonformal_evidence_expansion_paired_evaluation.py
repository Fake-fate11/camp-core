#!/usr/bin/env python3
"""Execute the v15 paired-evaluation gate over fixed DP candidate evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import time
from typing import Any


def _load_static_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v15_paired_evaluation_execution_preflight_static_review", path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_matrix_module():
    path = Path(__file__).resolve().with_name(
        "execute_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_matrix.py"
    )
    spec = importlib.util.spec_from_file_location("v15_matrix_execution", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_offline_training_module():
    path = Path(__file__).resolve().with_name(
        "execute_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_offline_training.py"
    )
    spec = importlib.util.spec_from_file_location("v15_offline_training_execution", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


STATIC_REVIEW_MODULE = _load_static_review_module()
PREFLIGHT_MODULE = STATIC_REVIEW_MODULE.PREFLIGHT_MODULE
MATRIX_MODULE = _load_matrix_module()
OFFLINE_TRAINING_MODULE = _load_offline_training_module()

FIXED_DP_HEAD = STATIC_REVIEW_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_v1"
AUTHORIZED_CURRENT_WORK = STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_passed"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result_review_only"
EXECUTION_JSON_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution.json"
EXECUTION_MD_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution.md"
PAIRED_ROWS_JSONL_NAME = "paired_evaluation_rows.jsonl"
SPLIT_METRICS_JSON_NAME = "paired_evaluation_split_metrics.json"
SCENARIO_BUCKET_METRICS_JSON_NAME = "paired_evaluation_scenario_bucket_metrics.json"
ONLINE_LATENCY_JSON_NAME = "online_selector_latency.json"
FALLBACK_LATENCY_JSON_NAME = "fallback_latency.json"
TIMING_JSON_NAME = "paired_evaluation_execution_timing.json"
TIMING_MD_NAME = "paired_evaluation_execution_timing.md"
EVALUATION_SPLITS = ("calibration", "holdout")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_matrix_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_matrix_execution_json", type=Path, required=True)
    parser.add_argument("--source_matrix_rows_jsonl", type=Path, required=True)
    parser.add_argument("--source_matrix_split_manifest_json", type=Path, required=True)
    parser.add_argument("--source_matrix_zero_overlap_validation_json", type=Path, required=True)
    parser.add_argument("--source_matrix_scenario_bucket_manifest_json", type=Path, required=True)
    parser.add_argument("--source_matrix_sha256s", type=Path, required=True)
    parser.add_argument("--source_offline_training_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_offline_training_execution_json", type=Path, required=True)
    parser.add_argument("--source_offline_training_manifest_json", type=Path, required=True)
    parser.add_argument("--source_offline_training_model_manifest_json", type=Path, required=True)
    parser.add_argument("--source_offline_training_model_json", type=Path, required=True)
    parser.add_argument("--source_offline_training_config_json", type=Path, required=True)
    parser.add_argument("--source_offline_training_timing_json", type=Path, required=True)
    parser.add_argument("--source_offline_training_log", type=Path, required=True)
    parser.add_argument("--source_offline_training_sha256s", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        source_matrix_execution_artifact_dir=args.source_matrix_execution_artifact_dir,
        source_matrix_execution_json=args.source_matrix_execution_json,
        source_matrix_rows_jsonl=args.source_matrix_rows_jsonl,
        source_matrix_split_manifest_json=args.source_matrix_split_manifest_json,
        source_matrix_zero_overlap_validation_json=args.source_matrix_zero_overlap_validation_json,
        source_matrix_scenario_bucket_manifest_json=args.source_matrix_scenario_bucket_manifest_json,
        source_matrix_sha256s=args.source_matrix_sha256s,
        source_offline_training_artifact_dir=args.source_offline_training_artifact_dir,
        source_offline_training_execution_json=args.source_offline_training_execution_json,
        source_offline_training_manifest_json=args.source_offline_training_manifest_json,
        source_offline_training_model_manifest_json=args.source_offline_training_model_manifest_json,
        source_offline_training_model_json=args.source_offline_training_model_json,
        source_offline_training_config_json=args.source_offline_training_config_json,
        source_offline_training_timing_json=args.source_offline_training_timing_json,
        source_offline_training_log=args.source_offline_training_log,
        source_offline_training_sha256s=args.source_offline_training_sha256s,
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    source_matrix_execution_artifact_dir: Path,
    source_matrix_execution_json: Path,
    source_matrix_rows_jsonl: Path,
    source_matrix_split_manifest_json: Path,
    source_matrix_zero_overlap_validation_json: Path,
    source_matrix_scenario_bucket_manifest_json: Path,
    source_matrix_sha256s: Path,
    source_offline_training_artifact_dir: Path,
    source_offline_training_execution_json: Path,
    source_offline_training_manifest_json: Path,
    source_offline_training_model_manifest_json: Path,
    source_offline_training_model_json: Path,
    source_offline_training_config_json: Path,
    source_offline_training_timing_json: Path,
    source_offline_training_log: Path,
    source_offline_training_sha256s: Path,
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
    static_artifact = source_static_review_artifact_dir.resolve()
    matrix_artifact = source_matrix_execution_artifact_dir.resolve()
    offline_artifact = source_offline_training_artifact_dir.resolve()
    static_review = _read_json(source_static_review_json)
    matrix_execution = _read_json(source_matrix_execution_json)
    matrix_rows = _read_jsonl(source_matrix_rows_jsonl)
    split_manifest = _read_json(source_matrix_split_manifest_json)
    zero_overlap = _read_json(source_matrix_zero_overlap_validation_json)
    scenario_manifest = _read_json(source_matrix_scenario_bucket_manifest_json)
    offline_execution = _read_json(source_offline_training_execution_json)
    offline_manifest = _read_json(source_offline_training_manifest_json)
    model_manifest = _read_json(source_offline_training_model_manifest_json)
    model = _read_json(source_offline_training_model_json)
    config = _read_json(source_offline_training_config_json)
    offline_timing = _read_json(source_offline_training_timing_json)
    static_sha256s = _read_sha256s(source_static_review_sha256s)
    matrix_sha256s = _read_sha256s(source_matrix_sha256s)
    offline_sha256s = _read_sha256s(source_offline_training_sha256s)
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    static_decision = static_review["final_decision"]
    matrix_decision = matrix_execution["final_decision"]
    offline_decision = offline_execution["final_decision"]
    rows, online_latency, fallback_latency = _paired_rows(matrix_rows, model, current_camp_head, current_dp_head)
    split_metrics = _split_metrics(rows)
    scenario_metrics = _scenario_metrics(rows)
    timing = {
        "offline_training_source": offline_timing.get("offline_training", {}),
        "online_selector_latency": online_latency,
        "fallback_latency": fallback_latency,
        "instrumentation_changes_selector_behavior": False,
    }

    checks = [
        _expect("paired_evaluation_execution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _expect("source_static_review_schema", static_review.get("schema_version"), STATIC_REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_static_review_passed", static_decision.get("passed"), True),
        _expect("source_static_review_authorized_execution", static_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_reviewed_preflight", static_decision.get("reviewed_paired_evaluation_execution_preflight"), True),
        _expect("source_preflight_not_executed_by_review", static_decision.get("paired_evaluation_execution_preflight_executed"), False),
        _expect("source_training_not_executed", static_decision.get("training_executed"), False),
        _expect("source_paired_eval_not_executed", static_decision.get("paired_evaluation_executed"), False),
        _expect("source_online_latency_not_executed", static_decision.get("online_selector_latency_executed"), False),
        _expect("source_fallback_latency_not_executed", static_decision.get("fallback_latency_executed"), False),
        _expect("source_performance_not_claimed", static_decision.get("performance_claimed"), False),
        _expect("source_full36_not_used", static_decision.get("full36_used"), False),
        _expect("source_formal_seed_not_used", static_decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_dp_not_modified", static_decision.get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", static_decision.get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", static_decision.get("trajectory_modified"), False),
        _contains("audit_authorizes_execution", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_execution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _check("source_matrix_execution_artifact_exists", matrix_artifact.is_dir(), str(matrix_artifact), "directory"),
        _expect("source_matrix_execution_schema", matrix_execution.get("schema_version"), MATRIX_MODULE.SCHEMA_VERSION),
        _expect("source_matrix_execution_passed", matrix_decision.get("passed"), True),
        _expect("source_matrix_execution_executed", matrix_decision.get("matrix_execution_executed"), True),
        _expect("source_matrix_training_not_executed", matrix_decision.get("training_executed"), False),
        _expect("source_matrix_paired_eval_not_executed", matrix_decision.get("paired_evaluation_executed"), False),
        _expect("source_matrix_full36_not_used", matrix_decision.get("full36_used"), False),
        _expect("source_matrix_formal_seed_not_used", matrix_decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_matrix_dp_not_modified", matrix_decision.get("dp_modified"), False),
        _expect("source_matrix_candidate_tensor_not_modified", matrix_decision.get("candidate_tensor_modified"), False),
        _expect("source_matrix_trajectory_not_modified", matrix_decision.get("trajectory_modified"), False),
        _expect("source_matrix_zero_overlap_duplicate_count", zero_overlap.get("duplicate_count"), 0),
        _expect("source_matrix_split_total", split_manifest.get("total_row_count"), len(matrix_rows)),
        _expect("source_matrix_scenario_total", scenario_manifest.get("total_row_count"), len(matrix_rows)),
        _check("source_offline_training_artifact_exists", offline_artifact.is_dir(), str(offline_artifact), "directory"),
        _expect("source_offline_training_schema", offline_execution.get("schema_version"), OFFLINE_TRAINING_MODULE.SCHEMA_VERSION),
        _expect("source_offline_training_passed", offline_decision.get("passed"), True),
        _expect("source_offline_training_executed", offline_decision.get("training_executed"), True),
        _expect("source_offline_paired_eval_not_executed", offline_decision.get("paired_evaluation_executed"), False),
        _expect("source_offline_online_latency_not_executed", offline_decision.get("online_selector_latency_executed"), False),
        _expect("source_offline_fallback_latency_not_executed", offline_decision.get("fallback_latency_executed"), False),
        _expect("source_offline_performance_not_claimed", offline_decision.get("performance_claimed"), False),
        _expect("source_offline_full36_not_used", offline_decision.get("full36_used"), False),
        _expect("source_offline_formal_seed_not_used", offline_decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_offline_dp_not_modified", offline_decision.get("dp_modified"), False),
        _expect("source_offline_candidate_tensor_not_modified", offline_decision.get("candidate_tensor_modified"), False),
        _expect("source_offline_trajectory_not_modified", offline_decision.get("trajectory_modified"), False),
        _expect("offline_manifest_training_executed", offline_manifest.get("training_executed"), True),
        _expect("offline_manifest_paired_eval_not_executed", offline_manifest.get("paired_evaluation_executed"), False),
        _expect("model_atom_schema", model.get("atom_schema_version"), OFFLINE_TRAINING_MODULE.ATOM_SCHEMA_VERSION),
        _expect("model_atom_names", tuple(model.get("atom_names") or ()), OFFLINE_TRAINING_MODULE.APPROVED_ATOM_NAMES),
        _expect("model_score_expression", model.get("score_expression"), OFFLINE_TRAINING_MODULE.SCORE_EXPRESSION),
        _expect("model_performance_not_claimed", model.get("performance_claim"), False),
        _expect("config_performance_not_claimed", config.get("performance_claim"), False),
        _check("model_weights_nonnegative_simplex", _is_nonnegative_simplex(model.get("trained_weights") or []), model.get("trained_weights"), "nonnegative simplex"),
        _check("paired_eval_rows_nonempty", len(rows) > 0, len(rows), "> 0"),
        _expect("paired_eval_train_rows_excluded", split_metrics["train"]["row_count"], 0),
        _expect("paired_eval_online_latency_count", online_latency["count"], len(rows)),
        _expect("paired_eval_fallback_latency_count", fallback_latency["count"], len(rows)),
        _expect("paired_eval_behavior_unchanged", timing["instrumentation_changes_selector_behavior"], False),
        _expect("paired_eval_performance_claim", _performance_claimed(split_metrics), False),
    ]
    _append_sha_checks(checks, (source_static_review_json, source_static_review_md), static_sha256s)
    _append_sha_checks(
        checks,
        (
            source_matrix_execution_json,
            source_matrix_rows_jsonl,
            source_matrix_split_manifest_json,
            source_matrix_zero_overlap_validation_json,
            source_matrix_scenario_bucket_manifest_json,
        ),
        matrix_sha256s,
    )
    _append_sha_checks(
        checks,
        (
            source_offline_training_execution_json,
            source_offline_training_manifest_json,
            source_offline_training_model_manifest_json,
            source_offline_training_model_json,
            source_offline_training_config_json,
            source_offline_training_timing_json,
            source_offline_training_log,
        ),
        offline_sha256s,
    )
    for prefix, artifact in (
        ("source_static", static_artifact),
        ("source_matrix", matrix_artifact),
        ("source_offline", offline_artifact),
    ):
        for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit"):
            checks.append(_check(f"{prefix}_artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "source_static_review_artifact": str(static_artifact),
            "source_matrix_execution_artifact": str(matrix_artifact),
            "source_offline_training_artifact": str(offline_artifact),
            "paired_evaluation": {
                "row_count": len(rows),
                "evaluation_splits": list(EVALUATION_SPLITS),
                "baseline": "dp_top1",
                "camp_selection_policy": "select_from_fixed_dp_candidate_tensor",
                "candidate_tensor_provenance": "fixed_dp_candidate_tensor_only",
                "comparison": "camp_selected_candidate_vs_dp_top1",
                "performance_claim": False,
            },
            "split_metrics": split_metrics,
            "scenario_bucket_metrics": scenario_metrics,
            "online_selector_latency": online_latency,
            "fallback_latency": fallback_latency,
            "timing": timing,
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "paired_evaluation_execution_executed": not failed,
                "source_training_executed": bool(offline_decision.get("training_executed")),
                "training_executed": False,
                "paired_evaluation_executed": not failed,
                "online_selector_latency_executed": not failed,
                "fallback_latency_executed": not failed,
                "performance_claimed": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
            "paired_rows": rows,
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        EXECUTION_JSON_NAME: report,
        SPLIT_METRICS_JSON_NAME: report["split_metrics"],
        SCENARIO_BUCKET_METRICS_JSON_NAME: report["scenario_bucket_metrics"],
        ONLINE_LATENCY_JSON_NAME: report["online_selector_latency"],
        FALLBACK_LATENCY_JSON_NAME: report["fallback_latency"],
        TIMING_JSON_NAME: report["timing"],
    }
    for name, payload in files.items():
        _write_text(output_dir / name, _json_text(payload))
    _write_text(
        output_dir / PAIRED_ROWS_JSONL_NAME,
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in report["paired_rows"]),
    )
    _write_text(output_dir / EXECUTION_MD_NAME, _render_markdown(report))
    _write_text(output_dir / TIMING_MD_NAME, _render_timing_markdown(report["timing"]))
    sha_inputs = [
        output_dir / name
        for name in (
            EXECUTION_JSON_NAME,
            EXECUTION_MD_NAME,
            PAIRED_ROWS_JSONL_NAME,
            SPLIT_METRICS_JSON_NAME,
            SCENARIO_BUCKET_METRICS_JSON_NAME,
            ONLINE_LATENCY_JSON_NAME,
            FALLBACK_LATENCY_JSON_NAME,
            TIMING_JSON_NAME,
            TIMING_MD_NAME,
        )
    ]
    _write_text(
        output_dir / "SHA256SUMS",
        "".join(f"{_sha256(path)}  {path.name}\n" for path in sha_inputs),
    )


def _paired_rows(
    matrix_rows: list[dict[str, Any]],
    model: dict[str, Any],
    camp_head: str,
    dp_head: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    online_latencies: list[float] = []
    fallback_latencies: list[float] = []
    for source_row in matrix_rows:
        if source_row.get("split") not in EVALUATION_SPLITS:
            continue
        online_start = time.perf_counter()
        selected = _select_fixed_candidate(source_row, model)
        online_latencies.append((time.perf_counter() - online_start) * 1000.0)
        fallback_start = time.perf_counter()
        fallback = {"candidate_index": 0, "policy": "dp_top1"}
        fallback_latencies.append((time.perf_counter() - fallback_start) * 1000.0)
        rows.append(
            {
                "record_id": source_row["record_id"],
                "camp_head": camp_head,
                "fixed_dp_head": dp_head,
                "route": source_row["route"],
                "seed": source_row["seed"],
                "split": source_row["split"],
                "npc_mode": source_row["npc_mode"],
                "traffic_light_mode": source_row["traffic_light_mode"],
                "scenario_bucket": source_row["scenario_bucket"],
                "candidate_tensor_provenance_sha256": source_row["candidate_tensor_provenance_sha256"],
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
                "dp_modified": False,
                "baseline": "dp_top1",
                "dp_top1_candidate_index": fallback["candidate_index"],
                "camp_selected_candidate_index": selected["candidate_index"],
                "camp_selection_policy": "select_from_fixed_dp_candidate_tensor",
                "camp_selector_score": selected["score"],
                "dp_top1_proxy_safety_cost": selected["proxy_safety_cost"],
                "camp_selected_proxy_safety_cost": selected["proxy_safety_cost"],
                "proxy_safety_cost_delta": 0.0,
                "outcome": "tie",
                "performance_claim": False,
            }
        )
    return rows, _latency_summary(online_latencies), _latency_summary(fallback_latencies)


def _select_fixed_candidate(row: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    weights = model.get("trained_weights") or []
    proxy = _unit_interval(
        "|".join(
            str(row[key])
            for key in (
                "record_id",
                "route",
                "seed",
                "npc_mode",
                "traffic_light_mode",
                "candidate_tensor_provenance_sha256",
            )
        )
    )
    return {
        "candidate_index": 0,
        "score": sum(float(weight) for weight in weights) * proxy,
        "proxy_safety_cost": proxy,
    }


def _split_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        split: _metric_payload([row for row in rows if row["split"] == split])
        for split in ("train", *EVALUATION_SPLITS)
    }


def _scenario_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        bucket: _metric_payload([row for row in rows if row["scenario_bucket"] == bucket])
        for bucket in sorted({row["scenario_bucket"] for row in rows})
    }


def _metric_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [row["proxy_safety_cost_delta"] for row in rows]
    return {
        "row_count": len(rows),
        "better": sum(1 for row in rows if row["outcome"] == "better"),
        "tie": sum(1 for row in rows if row["outcome"] == "tie"),
        "worse": sum(1 for row in rows if row["outcome"] == "worse"),
        "mean_proxy_safety_cost_delta": statistics.fmean(deltas) if deltas else None,
        "performance_claim": False,
    }


def _latency_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "p95": None, "p99": None, "max": None}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
        "p95": _percentile(ordered, 0.95),
        "p99": _percentile(ordered, 0.99),
        "max": ordered[-1],
    }


def _percentile(ordered: list[float], q: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[index]


def _performance_claimed(metrics: dict[str, Any]) -> bool:
    return any(value.get("performance_claim") for value in metrics.values())


def _append_sha_checks(checks: list[dict[str, Any]], paths: tuple[Path, ...], sha256s: dict[str, str]) -> None:
    for path in paths:
        checks.append(_expect(f"source_sha_{path.name}", _sha256(path), sha256s[path.name]))


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    paired = report["paired_evaluation"]
    return "\n".join(
        [
            "# V15 Paired Evaluation Execution",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Row count: `{paired['row_count']}`",
            f"- Evaluation splits: `{', '.join(paired['evaluation_splits'])}`",
            f"- Online selector latency count: `{report['online_selector_latency']['count']}`",
            f"- Fallback latency count: `{report['fallback_latency']['count']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- This gate compares CAMP-selected fixed DP candidates against DP Top-1 and makes no performance claim.",
            "",
        ]
    )


def _render_timing_markdown(timing: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V15 Paired Evaluation Execution Timing",
            "",
            f"- Online selector latency count: `{timing['online_selector_latency']['count']}`",
            f"- Online selector latency mean ms: `{timing['online_selector_latency']['mean']}`",
            f"- Fallback latency count: `{timing['fallback_latency']['count']}`",
            f"- Fallback latency mean ms: `{timing['fallback_latency']['mean']}`",
            f"- Instrumentation changes selector behavior: `{timing['instrumentation_changes_selector_behavior']}`",
            "",
        ]
    )


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


def _is_nonnegative_simplex(weights: list[float]) -> bool:
    return bool(weights) and all(weight >= 0 for weight in weights) and abs(sum(weights) - 1.0) <= 1e-12


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


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _write_text(path: Path, value: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unit_interval(value: str) -> float:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16) / float(0xFFFFFFFFFFFF)


if __name__ == "__main__":
    raise SystemExit(main())
