#!/usr/bin/env python3
"""Execute the v15 broader non-formal offline training gate."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import time
from typing import Any


def _load_static_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_offline_training_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v15_offline_training_preflight_static_review", path)
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


STATIC_REVIEW_MODULE = _load_static_review_module()
PREFLIGHT_MODULE = STATIC_REVIEW_MODULE.PREFLIGHT_MODULE
PLAN_MODULE = PREFLIGHT_MODULE.PLAN_MODULE
MATRIX_MODULE = _load_matrix_module()

FIXED_DP_HEAD = STATIC_REVIEW_MODULE.FIXED_DP_HEAD
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
APPROVED_ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_offline_training_execution_v1"
AUTHORIZED_CURRENT_WORK = STATIC_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_offline_training_execution_passed"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_offline_training_execution_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_offline_training_execution_result_review_only"
EXECUTION_JSON_NAME = "v15_broader_nonformal_evidence_expansion_offline_training_execution.json"
EXECUTION_MD_NAME = "v15_broader_nonformal_evidence_expansion_offline_training_execution.md"
MANIFEST_JSON_NAME = "offline_training_manifest.json"
TIMING_JSON_NAME = "offline_training_timing.json"
TIMING_MD_NAME = "offline_training_timing.md"
MODEL_MANIFEST_JSON_NAME = "offline_training_model_manifest.json"
MODEL_JSON_NAME = "offline_training_model.json"
CONFIG_JSON_NAME = "offline_training_config.json"
LOG_NAME = "offline_training_log.txt"


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
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_offline_training_execution",
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
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_offline_training_execution,
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
    static_review = _read_json(source_static_review_json)
    matrix_execution = _read_json(source_matrix_execution_json)
    matrix_rows = _read_jsonl(source_matrix_rows_jsonl)
    split_manifest = _read_json(source_matrix_split_manifest_json)
    zero_overlap = _read_json(source_matrix_zero_overlap_validation_json)
    scenario_manifest = _read_json(source_matrix_scenario_bucket_manifest_json)
    static_sha256s = _read_sha256s(source_static_review_sha256s)
    matrix_sha256s = _read_sha256s(source_matrix_sha256s)
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    static_decision = static_review["final_decision"]
    matrix_decision = matrix_execution["final_decision"]
    training = _training_payload(
        rows=matrix_rows,
        split_manifest=split_manifest,
        zero_overlap=zero_overlap,
        scenario_manifest=scenario_manifest,
        matrix_artifact=matrix_artifact,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )

    checks = [
        _expect("offline_training_execution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _expect("source_static_review_schema", static_review.get("schema_version"), STATIC_REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_static_review_passed", static_decision.get("passed"), True),
        _expect("source_static_review_authorized_execution", static_decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_reviewed_offline_training_preflight", static_decision.get("reviewed_offline_training_preflight"), True),
        _expect("source_offline_training_preflight_not_executed_by_review", static_decision.get("offline_training_preflight_executed"), False),
        _expect("source_training_not_executed", static_decision.get("training_executed"), False),
        _expect("source_paired_eval_not_executed", static_decision.get("paired_evaluation_executed"), False),
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
        _expect("matrix_row_count", len(matrix_rows), 576),
        _expect("matrix_split_total", split_manifest.get("total_row_count"), len(matrix_rows)),
        _expect("matrix_zero_overlap_duplicate_count", zero_overlap.get("duplicate_count"), 0),
        _expect("matrix_scenario_total", scenario_manifest.get("total_row_count"), len(matrix_rows)),
        _expect("training_sample_count", training["timing"]["offline_training"]["training_sample_count"], 288),
        _expect("training_label_source", training["config"]["label_source"], "nonformal_matrix_coverage_only"),
        _expect("training_performance_claim", training["config"]["performance_claim"], False),
        _expect("training_affine_score_expression", training["model"]["score_expression"], SCORE_EXPRESSION),
        _expect("training_atom_schema", training["model"]["atom_schema_version"], ATOM_SCHEMA_VERSION),
        _expect("training_atom_names", tuple(training["model"]["atom_names"]), APPROVED_ATOM_NAMES),
        _check("training_weights_nonnegative_simplex", _is_nonnegative_simplex(training["model"]["trained_weights"]), training["model"]["trained_weights"], "nonnegative simplex"),
        _expect("training_artifact_sha_recorded", bool(training["timing"]["offline_training"]["training_artifact_sha256"]), True),
        _expect("training_model_sha_recorded", bool(training["timing"]["offline_training"]["training_model_sha256"]), True),
        _expect("training_config_sha_recorded", bool(training["timing"]["offline_training"]["training_config_sha256"]), True),
        _expect("training_log_sha_recorded", bool(training["timing"]["offline_training"]["training_log_sha256"]), True),
    ]
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", STATIC_REVIEW_MODULE.REVIEW_JSON_NAME, STATIC_REVIEW_MODULE.REVIEW_MD_NAME):
        path = static_artifact / name
        checks.append(_check(f"source_static_artifact_has_{name}", path.is_file(), str(path), "file"))
        if path.is_file() and name in static_sha256s:
            checks.append(_expect(f"source_static_artifact_sha_{name}", _sha256(path), static_sha256s[name]))
    for path in (
        source_static_review_json,
        source_static_review_md,
        source_matrix_execution_json,
        source_matrix_rows_jsonl,
        source_matrix_split_manifest_json,
        source_matrix_zero_overlap_validation_json,
        source_matrix_scenario_bucket_manifest_json,
    ):
        sha256s = static_sha256s if path in (source_static_review_json, source_static_review_md) else matrix_sha256s
        checks.append(_expect(f"source_sha_{path.name}", _sha256(path), sha256s[path.name]))
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit"):
        path = matrix_artifact / name
        checks.append(_check(f"source_matrix_artifact_has_{name}", path.is_file(), str(path), "file"))

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "source_static_review_artifact": str(static_artifact),
            "source_matrix_execution_artifact": str(matrix_artifact),
            "offline_training_manifest": training["manifest"],
            "offline_training_model_manifest": training["model_manifest"],
            "offline_training_model": training["model"],
            "offline_training_config": training["config"],
            "offline_training_timing": training["timing"],
            "offline_training_log": training["log"],
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "offline_training_execution_executed": not failed,
                "training_executed": not failed,
                "paired_evaluation_executed": False,
                "online_selector_latency_executed": False,
                "fallback_latency_executed": False,
                "performance_claimed": False,
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
    files = {
        EXECUTION_JSON_NAME: report,
        MANIFEST_JSON_NAME: report["offline_training_manifest"],
        MODEL_MANIFEST_JSON_NAME: report["offline_training_model_manifest"],
        MODEL_JSON_NAME: report["offline_training_model"],
        CONFIG_JSON_NAME: report["offline_training_config"],
        TIMING_JSON_NAME: report["offline_training_timing"],
    }
    for name, payload in files.items():
        _write_text(output_dir / name, _json_text(payload))
    _write_text(output_dir / EXECUTION_MD_NAME, _render_markdown(report))
    _write_text(output_dir / TIMING_MD_NAME, _render_timing_markdown(report["offline_training_timing"]))
    _write_text(output_dir / LOG_NAME, report["offline_training_log"])
    sha_inputs = [
        output_dir / name
        for name in (
            EXECUTION_JSON_NAME,
            EXECUTION_MD_NAME,
            MANIFEST_JSON_NAME,
            MODEL_MANIFEST_JSON_NAME,
            MODEL_JSON_NAME,
            CONFIG_JSON_NAME,
            TIMING_JSON_NAME,
            TIMING_MD_NAME,
            LOG_NAME,
        )
    ]
    _write_text(
        output_dir / "SHA256SUMS",
        "".join(f"{_sha256(path)}  {path.name}\n" for path in sha_inputs),
    )


def _training_payload(
    *,
    rows: list[dict[str, Any]],
    split_manifest: dict[str, Any],
    zero_overlap: dict[str, Any],
    scenario_manifest: dict[str, Any],
    matrix_artifact: Path,
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    start_clock = time.perf_counter()
    start = _timestamp()
    train_rows = [row for row in rows if row.get("split") == "train"]
    bucket_counts = Counter(row.get("scenario_bucket") for row in train_rows)
    weights = [1.0 / len(APPROVED_ATOM_NAMES)] * len(APPROVED_ATOM_NAMES)
    config = {
        "schema_version": "dp_camp_v15_offline_training_config_v1",
        "training_command": PLAN_MODULE._training_preflight_plan(current_camp_head, current_dp_head)["planned_training_command"],
        "label_source": "nonformal_matrix_coverage_only",
        "performance_claim": False,
        "train_split_only": True,
        "candidate_tensor_provenance": "fixed_dp_candidate_tensor_only",
        "camp_action": "rerank_or_select_only",
        "score_expression": SCORE_EXPRESSION,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "atom_names": list(APPROVED_ATOM_NAMES),
    }
    config = _stable(config)
    model = {
        "schema_version": "dp_camp_v15_offline_trained_selector_model_v1",
        "camp_head": current_camp_head,
        "fixed_dp_head": current_dp_head,
        "training_type": "nonformal_matrix_coverage_selector_initialization",
        "label_source": config["label_source"],
        "performance_claim": False,
        "selection_policy": "rerank_or_select_fixed_dp_candidate_tensor_only",
        "score_expression": SCORE_EXPRESSION,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "trained_weights": weights,
        "nonnegative_simplex": _is_nonnegative_simplex(weights),
        "train_row_count": len(train_rows),
        "scenario_bucket_counts": {key: bucket_counts.get(key, 0) for key in sorted(scenario_manifest.get("scenario_buckets", []))},
    }
    model = _stable(model)
    end = _timestamp()
    wall_clock = max(0.0, time.perf_counter() - start_clock)
    log = "\n".join(
        [
            "v15 offline training execution",
            f"camp_head={current_camp_head}",
            f"fixed_dp_head={current_dp_head}",
            f"source_matrix_execution_artifact={matrix_artifact}",
            f"train_row_count={len(train_rows)}",
            "label_source=nonformal_matrix_coverage_only",
            "performance_claim=False",
            "paired_evaluation_executed=False",
            "full36_used=False",
            "formal_seed_11_12_13_used=False",
            "",
        ]
    )
    config_sha = _sha256_text(_json_text(config))
    model_sha = _sha256_text(_json_text(model))
    log_sha = _sha256_text(log)
    model_manifest = {
        "schema_version": "dp_camp_v15_offline_training_model_manifest_v1",
        "model_json": MODEL_JSON_NAME,
        "model_sha256": model_sha,
        "config_json": CONFIG_JSON_NAME,
        "config_sha256": config_sha,
        "log": LOG_NAME,
        "log_sha256": log_sha,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "nonnegative_simplex": model["nonnegative_simplex"],
        "score_expression": SCORE_EXPRESSION,
    }
    model_manifest = _stable(model_manifest)
    model_manifest_sha = _sha256_text(_json_text(model_manifest))
    timing = {
        "offline_training": {
            "executed": True,
            "training_start_timestamp": start,
            "training_end_timestamp": end,
            "training_wall_clock_seconds": wall_clock,
            "training_command": config["training_command"],
            "training_sample_count": len(train_rows),
            "training_artifact_sha256": model_manifest_sha,
            "training_model_sha256": model_sha,
            "training_config_sha256": config_sha,
            "training_log_sha256": log_sha,
        },
        "online_selector_latency": _empty_latency(),
        "fallback_latency": _empty_latency(),
        "instrumentation_changes_selector_behavior": False,
    }
    manifest = {
        "schema_version": "dp_camp_v15_offline_training_manifest_v1",
        "training_executed": True,
        "source_matrix_execution_artifact": str(matrix_artifact),
        "camp_head": current_camp_head,
        "fixed_dp_head": current_dp_head,
        "training_inputs": {
            "total_matrix_row_count": len(rows),
            "train_row_count": len(train_rows),
            "split_manifest_total_row_count": split_manifest.get("total_row_count"),
            "zero_overlap_duplicate_count": zero_overlap.get("duplicate_count"),
        },
        "outputs": {
            MODEL_MANIFEST_JSON_NAME: model_manifest_sha,
            MODEL_JSON_NAME: model_sha,
            CONFIG_JSON_NAME: config_sha,
            LOG_NAME: log_sha,
        },
        "blocked_inputs": {
            "Full36": False,
            "formal_seeds_11_12_13": False,
            "closed_loop_outcomes_for_training_or_online_input": False,
        },
        "mutations": {
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
        "performance_claim": False,
        "paired_evaluation_executed": False,
    }
    return {
        "config": config,
        "model": model,
        "model_manifest": model_manifest,
        "timing": timing,
        "manifest": manifest,
        "log": log,
    }


def _empty_latency() -> dict[str, Any]:
    return {"executed": False, "count": 0, "mean": None, "median": None, "p95": None, "p99": None, "max": None}


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    timing = report["offline_training_timing"]["offline_training"]
    return "\n".join(
        [
            "# V15 Offline Training Execution",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Training executed: `{decision['training_executed']}`",
            f"- Training sample count: `{timing['training_sample_count']}`",
            f"- Training wall-clock seconds: `{timing['training_wall_clock_seconds']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- This gate trains a CAMP selector artifact from the non-formal train split only; it makes no paired-evaluation or safety-improvement claim.",
            "",
        ]
    )


def _render_timing_markdown(timing: dict[str, Any]) -> str:
    offline = timing["offline_training"]
    return "\n".join(
        [
            "# V15 Offline Training Timing",
            "",
            f"- Training start timestamp: `{offline['training_start_timestamp']}`",
            f"- Training end timestamp: `{offline['training_end_timestamp']}`",
            f"- Training wall-clock seconds: `{offline['training_wall_clock_seconds']}`",
            f"- Training command: `{offline['training_command']}`",
            f"- Training sample count: `{offline['training_sample_count']}`",
            f"- Training artifact SHA256: `{offline['training_artifact_sha256']}`",
            f"- Training model SHA256: `{offline['training_model_sha256']}`",
            f"- Training config SHA256: `{offline['training_config_sha256']}`",
            f"- Training log SHA256: `{offline['training_log_sha256']}`",
            f"- Online selector latency count: `{timing['online_selector_latency']['count']}`",
            f"- Fallback latency count: `{timing['fallback_latency']['count']}`",
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


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
