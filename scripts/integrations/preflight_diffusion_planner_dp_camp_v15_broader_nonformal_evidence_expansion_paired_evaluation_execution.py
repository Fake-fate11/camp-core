#!/usr/bin/env python3
"""Preflight the v15 paired-evaluation execution gate without executing it."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v15_paired_evaluation_execution_plan_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
PLAN_MODULE = SOURCE_REVIEW_MODULE.PLAN_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight_v1"
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight_ready"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight_static_review_only"
PREFLIGHT_JSON_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight.json"
PREFLIGHT_MD_NAME = "v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight.md"
TIMING_JSON_NAME = "paired_evaluation_execution_timing_contract.json"
TIMING_MD_NAME = "paired_evaluation_execution_timing_contract.md"


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
        "--enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight",
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
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_preflight,
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
    preflight = _paired_evaluation_execution_preflight(current_camp_head, current_dp_head)
    timing = preflight["timing_contract"]

    checks = [
        _expect("execution_preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_authorized_preflight", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_reviewed_plan", decision.get("reviewed_paired_evaluation_execution_plan"), True),
        _expect("source_plan_not_executed_by_review", decision.get("paired_evaluation_execution_plan_executed"), False),
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
        _contains("audit_authorizes_preflight", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_preflight", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _expect("preflight_baseline", preflight["paired_protocol"]["baseline"], "dp_top1"),
        _expect("preflight_camp_policy", preflight["paired_protocol"]["camp_selection_policy"], "select_from_fixed_dp_candidate_tensor"),
        _expect("preflight_candidate_tensor_provenance", preflight["paired_protocol"]["candidate_tensor_provenance"], "fixed_dp_candidate_tensor_only"),
        _check("preflight_eval_splits", set(preflight["required_inputs"]["evaluation_splits"]) == {"calibration", "holdout"}, preflight["required_inputs"]["evaluation_splits"], "calibration and holdout"),
        _check("preflight_train_split_not_evaluated", "train" not in preflight["required_inputs"]["evaluation_splits"], preflight["required_inputs"]["evaluation_splits"], "no train split"),
        _expect("timing_online_latency_fields", tuple(timing["online_selector_latency_required_fields"]), PLAN_MODULE.PLAN_MODULE.LATENCY_FIELDS),
        _expect("timing_fallback_latency_fields", tuple(timing["fallback_latency_required_fields"]), PLAN_MODULE.PLAN_MODULE.LATENCY_FIELDS),
        _expect("timing_behavior_unchanged", timing["instrumentation_changes_selector_behavior"], False),
        _expect("blocked_full36", preflight["blocked_inputs"]["Full36"], False),
        _expect("blocked_formal_seeds", preflight["blocked_inputs"]["formal_seeds_11_12_13"], False),
        _expect("mutation_dp", preflight["mutations"]["dp_modified"], False),
        _expect("mutation_candidate_tensor", preflight["mutations"]["candidate_tensor_modified"], False),
        _expect("mutation_trajectory", preflight["mutations"]["trajectory_modified"], False),
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
            "paired_evaluation_execution_preflight": preflight,
            "timing_contract": timing,
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "paired_evaluation_execution_preflight_executed": not failed,
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


def _paired_evaluation_execution_preflight(camp_head: str, dp_head: str) -> dict[str, Any]:
    plan = PLAN_MODULE._paired_evaluation_execution_plan(camp_head, dp_head)
    return {
        "camp_head": camp_head,
        "fixed_dp_head": dp_head,
        "required_inputs": plan["required_inputs"],
        "paired_protocol": plan["paired_protocol"],
        "execution_steps": plan["execution_steps"],
        "timing_contract": plan["timing_contract"],
        "planned_command": plan["planned_command"],
        "planned_outputs": plan["planned_outputs"],
        "blocked_inputs": plan["blocked_inputs"],
        "mutations": plan["mutations"],
        "preflight_checks": (
            "all_required_artifacts_present",
            "fixed_dp_candidate_tensor_manifest_readable",
            "trained_camp_weight_manifest_readable",
            "calibration_and_holdout_pairs_planned",
            "no_train_split_or_formal_seed_inputs",
            "latency_outputs_declared",
        ),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        PREFLIGHT_JSON_NAME: report,
        TIMING_JSON_NAME: report["timing_contract"],
    }
    for name, payload in files.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / PREFLIGHT_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / TIMING_MD_NAME).write_text(_render_timing_markdown(report["timing_contract"]), encoding="utf-8")
    sha_inputs = [output_dir / name for name in (*files.keys(), PREFLIGHT_MD_NAME, TIMING_MD_NAME)]
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in sha_inputs),
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V15 Paired Evaluation Execution Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- This gate preflights paired evaluation execution only; it does not execute.",
            "",
        ]
    )


def _render_timing_markdown(timing: dict[str, Any]) -> str:
    lines = ["# V15 Paired Evaluation Execution Timing Contract", ""]
    lines.extend(f"- Online `{field}`" for field in timing["online_selector_latency_required_fields"])
    lines.extend(f"- Fallback `{field}`" for field in timing["fallback_latency_required_fields"])
    lines.append("")
    return "\n".join(lines)


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
