#!/usr/bin/env python3
"""Review the v15 offline training execution artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_execution_module():
    path = Path(__file__).resolve().with_name(
        "execute_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_offline_training.py"
    )
    spec = importlib.util.spec_from_file_location("v15_offline_training_execution", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


EXECUTION_MODULE = _load_execution_module()

FIXED_DP_HEAD = EXECUTION_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_offline_training_execution_result_review_v1"
AUTHORIZED_CURRENT_WORK = EXECUTION_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_offline_training_execution_result_review_passed"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_offline_training_execution_result_review_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_plan_only"
REVIEW_JSON_NAME = "v15_broader_nonformal_evidence_expansion_offline_training_execution_result_review.json"
REVIEW_MD_NAME = "v15_broader_nonformal_evidence_expansion_offline_training_execution_result_review.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_execution_json", type=Path, required=True)
    parser.add_argument("--source_execution_md", type=Path, required=True)
    parser.add_argument("--source_manifest_json", type=Path, required=True)
    parser.add_argument("--source_model_manifest_json", type=Path, required=True)
    parser.add_argument("--source_model_json", type=Path, required=True)
    parser.add_argument("--source_config_json", type=Path, required=True)
    parser.add_argument("--source_timing_json", type=Path, required=True)
    parser.add_argument("--source_timing_md", type=Path, required=True)
    parser.add_argument("--source_log", type=Path, required=True)
    parser.add_argument("--source_sha256s", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_offline_training_execution_result_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_execution_artifact_dir=args.source_execution_artifact_dir,
        source_execution_json=args.source_execution_json,
        source_execution_md=args.source_execution_md,
        source_manifest_json=args.source_manifest_json,
        source_model_manifest_json=args.source_model_manifest_json,
        source_model_json=args.source_model_json,
        source_config_json=args.source_config_json,
        source_timing_json=args.source_timing_json,
        source_timing_md=args.source_timing_md,
        source_log=args.source_log,
        source_sha256s=args.source_sha256s,
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_offline_training_execution_result_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_execution_artifact_dir: Path,
    source_execution_json: Path,
    source_execution_md: Path,
    source_manifest_json: Path,
    source_model_manifest_json: Path,
    source_model_json: Path,
    source_config_json: Path,
    source_timing_json: Path,
    source_timing_md: Path,
    source_log: Path,
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
    manifest = _read_json(source_manifest_json)
    model_manifest = _read_json(source_model_manifest_json)
    model = _read_json(source_model_json)
    config = _read_json(source_config_json)
    timing = _read_json(source_timing_json)
    sha256s = _read_sha256s(source_sha256s)
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    decision = execution["final_decision"]
    offline_timing = timing["offline_training"]

    checks = [
        _expect("result_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_execution_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_execution_schema", execution.get("schema_version"), EXECUTION_MODULE.SCHEMA_VERSION),
        _expect("source_execution_passed", decision.get("passed"), True),
        _expect("source_execution_authorized_review", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_execution_executed", decision.get("offline_training_execution_executed"), True),
        _expect("source_training_executed", decision.get("training_executed"), True),
        _expect("source_paired_eval_not_executed", decision.get("paired_evaluation_executed"), False),
        _expect("source_online_latency_not_executed", decision.get("online_selector_latency_executed"), False),
        _expect("source_fallback_latency_not_executed", decision.get("fallback_latency_executed"), False),
        _expect("source_performance_not_claimed", decision.get("performance_claimed"), False),
        _expect("source_full36_not_used", decision.get("full36_used"), False),
        _expect("source_formal_seed_not_used", decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_dp_not_modified", decision.get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", decision.get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", decision.get("trajectory_modified"), False),
        _contains("audit_authorizes_review", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _expect("timing_matches_execution_report", execution.get("offline_training_timing"), timing),
        _expect("timing_training_executed", offline_timing.get("executed"), True),
        _expect("timing_training_sample_count", offline_timing.get("training_sample_count"), 288),
        _check("timing_wall_clock_nonnegative", offline_timing.get("training_wall_clock_seconds", -1) >= 0, offline_timing.get("training_wall_clock_seconds"), ">= 0"),
        _expect("timing_online_latency_not_executed", timing["online_selector_latency"].get("executed"), False),
        _expect("timing_fallback_latency_not_executed", timing["fallback_latency"].get("executed"), False),
        _expect("timing_behavior_unchanged", timing.get("instrumentation_changes_selector_behavior"), False),
        _expect("manifest_training_executed", manifest.get("training_executed"), True),
        _expect("manifest_train_row_count", manifest["training_inputs"].get("train_row_count"), 288),
        _expect("manifest_zero_overlap_duplicate_count", manifest["training_inputs"].get("zero_overlap_duplicate_count"), 0),
        _expect("manifest_paired_eval_not_executed", manifest.get("paired_evaluation_executed"), False),
        _expect("manifest_performance_not_claimed", manifest.get("performance_claim"), False),
        _expect("manifest_full36_not_used", manifest["blocked_inputs"].get("Full36"), False),
        _expect("manifest_formal_seed_not_used", manifest["blocked_inputs"].get("formal_seeds_11_12_13"), False),
        _expect("manifest_dp_not_modified", manifest["mutations"].get("dp_modified"), False),
        _expect("manifest_candidate_tensor_not_modified", manifest["mutations"].get("candidate_tensor_modified"), False),
        _expect("manifest_trajectory_not_modified", manifest["mutations"].get("trajectory_modified"), False),
        _expect("model_atom_schema", model.get("atom_schema_version"), EXECUTION_MODULE.ATOM_SCHEMA_VERSION),
        _expect("model_atom_names", tuple(model.get("atom_names") or ()), EXECUTION_MODULE.APPROVED_ATOM_NAMES),
        _expect("model_score_expression", model.get("score_expression"), EXECUTION_MODULE.SCORE_EXPRESSION),
        _expect("model_train_row_count", model.get("train_row_count"), 288),
        _expect("model_label_source", model.get("label_source"), "nonformal_matrix_coverage_only"),
        _expect("model_performance_not_claimed", model.get("performance_claim"), False),
        _check("model_weights_nonnegative_simplex", _is_nonnegative_simplex(model.get("trained_weights") or []), model.get("trained_weights"), "nonnegative simplex"),
        _expect("config_label_source", config.get("label_source"), "nonformal_matrix_coverage_only"),
        _expect("config_train_split_only", config.get("train_split_only"), True),
        _expect("config_performance_not_claimed", config.get("performance_claim"), False),
        _expect("model_manifest_model_sha", model_manifest.get("model_sha256"), _sha256(source_model_json)),
        _expect("model_manifest_config_sha", model_manifest.get("config_sha256"), _sha256(source_config_json)),
        _expect("model_manifest_log_sha", model_manifest.get("log_sha256"), _sha256(source_log)),
        _expect("timing_artifact_sha", offline_timing.get("training_artifact_sha256"), _sha256(source_model_manifest_json)),
        _expect("timing_model_sha", offline_timing.get("training_model_sha256"), _sha256(source_model_json)),
        _expect("timing_config_sha", offline_timing.get("training_config_sha256"), _sha256(source_config_json)),
        _expect("timing_log_sha", offline_timing.get("training_log_sha256"), _sha256(source_log)),
    ]
    for path in (
        source_execution_json,
        source_execution_md,
        source_manifest_json,
        source_model_manifest_json,
        source_model_json,
        source_config_json,
        source_timing_json,
        source_timing_md,
        source_log,
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
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "reviewed_offline_training_execution": True,
                "offline_training_execution_executed": False,
                "source_training_executed": bool(decision.get("training_executed")),
                "training_executed": False,
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
    return "\n".join(
        [
            "# V15 Offline Training Execution Result Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Reviewed offline training execution: `{decision['reviewed_offline_training_execution']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
