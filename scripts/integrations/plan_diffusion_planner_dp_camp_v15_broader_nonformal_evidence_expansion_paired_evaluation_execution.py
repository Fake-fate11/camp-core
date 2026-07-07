#!/usr/bin/env python3
"""Plan the v15 paired-evaluation execution gate without executing it."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v15_paired_evaluation_preflight_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
PREFLIGHT_MODULE = SOURCE_REVIEW_MODULE.PREFLIGHT_MODULE
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan_v1"
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan_ready"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan_static_review_only"
PLAN_JSON_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan.json"
PLAN_MD_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan",
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
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan,
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
    artifact = source_static_review_artifact_dir.resolve()
    source_review = _read_json(source_static_review_json)
    sha256s = _read_sha256s(source_static_review_sha256s)
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    decision = source_review["final_decision"]
    plan = _paired_evaluation_execution_plan(current_camp_head, current_dp_head)

    checks = [
        _expect("execution_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_authorized_plan", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_reviewed_preflight", decision.get("reviewed_paired_evaluation_preflight"), True),
        _expect("source_preflight_not_executed_by_review", decision.get("paired_evaluation_preflight_executed"), False),
        _expect("source_training_not_executed", decision.get("training_executed"), False),
        _expect("source_paired_eval_not_executed", decision.get("paired_evaluation_executed"), False),
        _expect("source_online_latency_not_executed", decision.get("online_selector_latency_executed"), False),
        _expect("source_fallback_latency_not_executed", decision.get("fallback_latency_executed"), False),
        _expect("source_performance_not_claimed", decision.get("performance_claimed"), False),
        _expect("source_full36_not_used", decision.get("full36_used"), False),
        _expect("source_formal_seed_not_used", decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_dp_not_modified", decision.get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", decision.get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", decision.get("trajectory_modified"), False),
        _contains("audit_authorizes_plan", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_plan", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _expect("plan_baseline", plan["paired_protocol"]["baseline"], "dp_top1"),
        _expect("plan_camp_policy", plan["paired_protocol"]["camp_selection_policy"], "select_from_fixed_dp_candidate_tensor"),
        _expect("plan_candidate_tensor_provenance", plan["paired_protocol"]["candidate_tensor_provenance"], "fixed_dp_candidate_tensor_only"),
        _check("plan_eval_splits", set(plan["required_inputs"]["evaluation_splits"]) == {"calibration", "holdout"}, plan["required_inputs"]["evaluation_splits"], "calibration and holdout"),
        _check("plan_train_split_not_evaluated", "train" not in plan["required_inputs"]["evaluation_splits"], plan["required_inputs"]["evaluation_splits"], "no train split"),
        _expect("plan_online_latency_fields", tuple(plan["timing_contract"]["online_selector_latency_required_fields"]), PLAN_MODULE.LATENCY_FIELDS),
        _expect("plan_fallback_latency_fields", tuple(plan["timing_contract"]["fallback_latency_required_fields"]), PLAN_MODULE.LATENCY_FIELDS),
        _expect("plan_timing_behavior_unchanged", plan["timing_contract"]["instrumentation_changes_selector_behavior"], False),
        _expect("plan_full36_used", plan["blocked_inputs"]["Full36"], False),
        _expect("plan_formal_seed_used", plan["blocked_inputs"]["formal_seeds_11_12_13"], False),
        _expect("plan_dp_modified", plan["mutations"]["dp_modified"], False),
        _expect("plan_candidate_tensor_modified", plan["mutations"]["candidate_tensor_modified"], False),
        _expect("plan_trajectory_modified", plan["mutations"]["trajectory_modified"], False),
    ]
    for path in (source_static_review_json, source_static_review_md):
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
            "source_static_review_artifact": str(artifact),
            "paired_evaluation_execution_plan": plan,
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "paired_evaluation_execution_plan_executed": False,
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


def _paired_evaluation_execution_plan(camp_head: str, dp_head: str) -> dict[str, Any]:
    return {
        "camp_head": camp_head,
        "fixed_dp_head": dp_head,
        "required_inputs": {
            "paired_evaluation_preflight_static_review_artifact": "v15_broader_nonformal_evidence_expansion_paired_evaluation_preflight_static_review",
            "offline_training_execution_artifact": "v15_broader_nonformal_evidence_expansion_offline_training_execution",
            "offline_training_model_manifest": "offline_training_model_manifest.json",
            "matrix_execution_artifact": "v15_broader_nonformal_evidence_expansion_matrix_execution",
            "fixed_dp_candidate_tensor_manifest": "fixed_dp_candidate_tensor_manifest",
            "evaluation_splits": ("calibration", "holdout"),
            "forbidden_evaluation_splits": ("train",),
        },
        "paired_protocol": {
            "baseline": "dp_top1",
            "camp_selection_policy": "select_from_fixed_dp_candidate_tensor",
            "candidate_tensor_provenance": "fixed_dp_candidate_tensor_only",
            "pairing_keys": ("route", "seed", "npc_mode", "traffic_light_mode", "record_id"),
            "comparison": "camp_selected_candidate_vs_dp_top1",
        },
        "execution_steps": (
            "load_fixed_dp_candidate_tensor_manifest",
            "load_trained_nonnegative_simplex_camp_weights",
            "rerank_fixed_dp_candidates_without_mutation",
            "pair_camp_selected_candidate_against_dp_top1",
            "emit_split_bucket_metrics_and_latency_summaries",
            "fail_closed_on_missing_pairs_or_boundary_violation",
        ),
        "timing_contract": {
            "online_selector_latency_required_fields": PLAN_MODULE.LATENCY_FIELDS,
            "fallback_latency_required_fields": PLAN_MODULE.LATENCY_FIELDS,
            "instrumentation_changes_selector_behavior": False,
        },
        "planned_command": (
            "python scripts/integrations/execute_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation.py"
        ),
        "planned_outputs": (
            "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution.json",
            "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution.md",
            "online_selector_latency.json",
            "fallback_latency.json",
            "SHA256SUMS",
        ),
        "blocked_inputs": {
            "Full36": False,
            "formal_seeds_11_12_13": False,
            "train_split_for_evaluation": False,
            "dp_generated_or_mutated_candidates": False,
        },
        "mutations": {
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        f"{_sha256(json_path)}  {json_path.name}\n{_sha256(md_path)}  {md_path.name}\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["paired_evaluation_execution_plan"]
    return "\n".join(
        [
            "# V15 Paired Evaluation Execution Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Evaluation splits: `{', '.join(plan['required_inputs']['evaluation_splits'])}`",
            f"- Baseline: `{plan['paired_protocol']['baseline']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- This gate plans paired evaluation execution only; it does not execute.",
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
