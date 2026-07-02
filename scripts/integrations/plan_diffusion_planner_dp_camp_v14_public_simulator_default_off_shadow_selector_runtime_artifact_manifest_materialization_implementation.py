#!/usr/bin/env python3
"""Plan-only v14 runtime manifest materialization implementation gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
RUNTIME_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
)
SOURCE_SCOPE = "public_simulator_fixed_dp_candidate_tensor"
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_static_contract_review_v1"
)
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_plan_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_v1"
)
SOURCE_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_static_contract_review_passed"
)
SOURCE_REVIEW_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_only"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_plan_ready"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_rejected"
)
DISABLED_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_default_off_disabled"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_static_contract_review_only"
)
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 9

BLOCKED_ACTIONS = (
    "runtime_artifact_manifest_materialization_implementation_authorized",
    "runtime_artifact_manifest_materialization_authorized",
    "default_off_shadow_selector_runtime_execution_authorized",
    "training_authorized",
    "training_execution_authorized",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime_artifact_manifest_materialization_static_review_json",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--runtime_artifact_manifest_materialization_plan_json",
        type=Path,
        required=True,
    )
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--planned_runtime_manifest_path", required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument(
        "--enable_v14_public_simulator_runtime_artifact_manifest_materialization_implementation_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_artifact_manifest_materialization_static_review_json=(
            args.runtime_artifact_manifest_materialization_static_review_json
        ),
        runtime_artifact_manifest_materialization_plan_json=(
            args.runtime_artifact_manifest_materialization_plan_json
        ),
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        planned_runtime_manifest_path=args.planned_runtime_manifest_path,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_public_simulator_runtime_artifact_manifest_materialization_implementation_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_artifact_manifest_materialization_static_review_json: Path,
    runtime_artifact_manifest_materialization_plan_json: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    planned_runtime_manifest_path: str,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        label=label,
        output_dir=output_dir,
        planned_runtime_manifest_path=planned_runtime_manifest_path,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    paths = {
        "materialization_static_review": (
            runtime_artifact_manifest_materialization_static_review_json
        ),
        "materialization_plan": runtime_artifact_manifest_materialization_plan_json,
        "v14_audit": v14_audit_md,
        "current_status": current_status_md,
    }
    checks: list[dict[str, Any]] = [
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "planned_runtime_manifest_path_is_json",
            planned_runtime_manifest_path.endswith(".json"),
            planned_runtime_manifest_path,
            "*.json",
        ),
        _check(
            "planned_runtime_manifest_absent",
            not Path(planned_runtime_manifest_path).exists(),
            Path(planned_runtime_manifest_path).exists(),
            False,
        ),
    ]
    payloads: dict[str, Any] = {}
    texts: dict[str, str] = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file"))
        if not path.is_file():
            continue
        report["source_hashes"][f"{name}_sha256"] = _sha256(path)
        if path.suffix == ".json":
            loaded, json_check = _load_json(path, name)
            payloads[name] = loaded
            checks.append(json_check)
        else:
            texts[name] = path.read_text(encoding="utf-8")

    source_review = _dict(payloads.get("materialization_static_review"))
    source_plan = _dict(payloads.get("materialization_plan"))
    checks.extend(_source_review_checks(source_review))
    checks.extend(_source_plan_checks(source_plan, planned_runtime_manifest_path))
    checks.extend(_audit_contract_checks(texts.get("v14_audit", ""), texts.get("current_status", "")))
    passed = all(check["passed"] for check in checks)

    report["source_summary"] = _source_summary(
        source_review=source_review,
        source_plan=source_plan,
        source_hashes=report["source_hashes"],
    )
    report["implementation_plan"] = _implementation_plan(
        source_plan=source_plan,
        planned_runtime_manifest_path=planned_runtime_manifest_path,
        source_hashes=report["source_hashes"],
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    report["static_review_requirements"] = _static_review_requirements()
    report["forbidden_paths"] = _forbidden_paths()
    report["plan_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "runtime_artifact_manifest_materialization_implementation_plan.json",
        report,
    )
    (
        output_dir
        / "runtime_artifact_manifest_materialization_implementation_plan.md"
    ).write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report.get("implementation_plan", {})
    future = _dict(plan.get("future_materializer_contract"))
    manifest = _dict(future.get("manifest_required_content"))
    lines = [
        "# V14 Runtime Manifest Materialization Implementation Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation static review authorized: `{decision['runtime_artifact_manifest_materialization_implementation_static_contract_review_authorized']}`",
        f"- Implementation authorized: `{decision['runtime_artifact_manifest_materialization_implementation_authorized']}`",
        f"- Materialization authorized: `{decision['runtime_artifact_manifest_materialization_authorized']}`",
        f"- Runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Implementation Plan",
        "",
        f"- Planned runtime manifest path: `{plan.get('planned_runtime_manifest_path')}`",
        f"- Runtime manifest written by this gate: `{plan.get('runtime_manifest_written_by_this_gate')}`",
        f"- Runtime manifest materialized by this gate: `{plan.get('runtime_manifest_materialized_by_this_gate')}`",
        f"- Future write strategy: `{future.get('write_strategy')}`",
        f"- Runtime schema: `{manifest.get('schema_version')}`",
        f"- Source scope: `{manifest.get('source_scope')}`",
        f"- Executed output policy: `{manifest.get('executed_output_policy')}`",
        f"- Score expression: `{manifest.get('score_expression')}`",
        "",
        "## Future Materializer Steps",
        "",
    ]
    for item in future.get("steps", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Static Review Requirements", ""])
    for item in report.get("static_review_requirements", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report.get("forbidden_paths", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It does not write the runtime manifest, "
            "run replay, train CAMP, generate candidates, modify Diffusion "
            "Planner, promote atoms or selectors, deploy, or authorize "
            "safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report.get("plan_checks", []):
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check.get('observed'))}` | `{_compact(check.get('expected'))}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _empty_report(
    *,
    enabled: bool,
    label: str | None,
    output_dir: Path,
    planned_runtime_manifest_path: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "output_dir": str(output_dir),
            "enabled": bool(enabled),
            "plan_only": True,
            "runtime_artifact_manifest_materialized": False,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "planned_runtime_manifest_path": planned_runtime_manifest_path,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "The future materializer may only write immutable artifact "
                "paths and hashes for fixed DP candidate reranking. It must "
                "preserve affine score_k(w)=a_k^T w, approved atom weights, "
                "and DP Top-1 execution behavior."
            ),
        },
        "source_hashes": {},
        "source_summary": {},
        "implementation_plan": {},
        "static_review_requirements": [],
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "runtime_artifact_manifest_materialization_implementation_plan_ready": False,
            "runtime_artifact_manifest_materialization_implementation_static_contract_review_authorized": False,
            "runtime_artifact_manifest_materialization_implementation_authorized": False,
            "runtime_artifact_manifest_materialization_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "runtime_manifest_written_by_this_gate": False,
            "runtime_manifest_materialized_by_this_gate": False,
            "training_executed_by_this_gate": False,
            "failed_checks": [],
            "failure_class": "materialization_implementation_plan_gate_disabled",
        },
    }


def _source_review_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    summary = _dict(payload.get("contract_summary"))
    checks = [
        _expect("source_review_schema_version", payload.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        _expect("source_review_passed", decision.get("passed"), True),
        _expect("source_review_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_review_authorizes_this_plan", decision.get("authorized_next_work"), SOURCE_REVIEW_AUTHORIZED_NEXT_WORK),
        _expect("source_review_passed_flag", decision.get("runtime_artifact_manifest_materialization_static_contract_review_passed"), True),
        _expect("source_review_implementation_plan_authorized", decision.get("runtime_artifact_manifest_materialization_implementation_plan_authorized"), True),
        _expect("source_review_materialization_forbidden", decision.get("runtime_artifact_manifest_materialization_authorized"), False),
        _expect("source_review_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_review_training_forbidden", decision.get("training_execution_authorized"), False),
        _expect("source_review_replay_forbidden", decision.get("replay_execution_authorized"), False),
        _expect("source_review_candidate_generation_forbidden", decision.get("candidate_generation_authorized"), False),
        _expect("source_review_dp_modification_forbidden", decision.get("dp_modification_authorized"), False),
        _expect("source_review_selector_promotion_forbidden", decision.get("selector_promotion_authorized"), False),
        _expect("source_review_deployment_forbidden", decision.get("deployment_authorized"), False),
        _expect("source_review_safety_claim_forbidden", decision.get("safety_benefit_claim_authorized"), False),
        _expect("source_review_camp_over_dp_claim_forbidden", decision.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("source_review_runtime_manifest_not_materialized", decision.get("runtime_manifest_materialized_by_this_gate"), False),
        _expect("source_review_runtime_schema", summary.get("runtime_schema_version"), RUNTIME_SCHEMA_VERSION),
        _expect("source_review_source_scope", summary.get("source_scope"), SOURCE_SCOPE),
        _expect("source_review_required_runtime_entries", summary.get("required_runtime_entries"), ["atom_scales", "static_weights"]),
        _expect("source_review_score_expression", summary.get("score_expression"), SCORE_EXPRESSION),
    ]
    for name in BLOCKED_ACTIONS:
        if name in decision:
            checks.append(_expect(f"source_review_{name}_false", decision.get(name), False))
    return checks


def _source_plan_checks(
    payload: dict[str, Any],
    planned_runtime_manifest_path: str,
) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("materialization_plan"))
    future = _dict(plan.get("future_manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    aliases = _dict(future.get("sha256"))
    atom_entry = _dict(artifacts.get("atom_scales"))
    weights_entry = _dict(artifacts.get("static_weights"))
    checks = [
        _expect("source_plan_schema_version", payload.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_manifest_plan_ready", decision.get("runtime_artifact_manifest_materialization_plan_ready"), True),
        _expect("source_plan_static_review_authorized", decision.get("runtime_artifact_manifest_materialization_static_contract_review_authorized"), True),
        _expect("source_plan_materialization_forbidden", decision.get("runtime_artifact_manifest_materialization_authorized"), False),
        _expect("source_plan_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_plan_training_forbidden", decision.get("training_execution_authorized"), False),
        _expect("source_plan_replay_forbidden", decision.get("replay_execution_authorized"), False),
        _expect("source_plan_candidate_generation_forbidden", decision.get("candidate_generation_authorized"), False),
        _expect("source_plan_dp_modification_forbidden", decision.get("dp_modification_authorized"), False),
        _expect("source_plan_runtime_manifest_not_written", decision.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_runtime_manifest_not_materialized", decision.get("runtime_manifest_materialized_by_this_gate"), False),
        _expect("source_plan_status_no_manifest_written", plan.get("status"), "plan_ready_no_runtime_manifest_written"),
        _expect("source_plan_planned_path_matches", plan.get("planned_runtime_manifest_path"), planned_runtime_manifest_path),
        _expect("source_plan_this_plan_is_not_manifest", plan.get("this_plan_is_runtime_manifest"), False),
        _expect("source_plan_manifest_written_false", plan.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_manifest_materialized_false", plan.get("runtime_manifest_materialized_by_this_gate"), False),
        _expect("source_plan_runtime_execution_false", plan.get("runtime_execution_enabled_by_this_gate"), False),
        _expect("future_runtime_schema", future.get("schema_version"), RUNTIME_SCHEMA_VERSION),
        _expect("future_source_scope", future.get("source_scope"), SOURCE_SCOPE),
        _expect("future_manifest_role", future.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"),
        _expect("future_default_off", future.get("default_off"), True),
        _expect("future_fail_closed", future.get("fail_closed"), True),
        _expect("future_selector_mode", future.get("selector_mode"), "static"),
        _expect("future_candidate_operation", future.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("future_executed_output_policy", future.get("executed_output_policy"), "dp_top1"),
        _expect("future_candidate_count", future.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("future_atom_count", future.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("future_atom_schema", future.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("future_score_expression", future.get("score_expression"), SCORE_EXPRESSION),
        _expect("future_required_dp_head", future.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("future_atom_scales_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("future_atom_scales_path_present", bool(atom_entry.get("path")), atom_entry.get("path"), "nonempty path"),
        _check("future_atom_scales_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("future_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("future_static_weights_path_present", bool(weights_entry.get("path")), weights_entry.get("path"), "nonempty path"),
        _check("future_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _expect("future_atom_logical_alias", aliases.get("atom_scales"), atom_entry.get("sha256")),
        _expect("future_weight_logical_alias", aliases.get("static_weights"), weights_entry.get("sha256")),
        _expect("future_atom_path_alias", aliases.get(atom_entry.get("path")), atom_entry.get("sha256")),
        _expect("future_weight_path_alias", aliases.get(weights_entry.get("path")), weights_entry.get("sha256")),
        _expect("future_atom_basename_alias", aliases.get(Path(str(atom_entry.get("path"))).name), atom_entry.get("sha256")),
        _expect("future_weight_basename_alias", aliases.get(Path(str(weights_entry.get("path"))).name), weights_entry.get("sha256")),
    ]
    for name in BLOCKED_ACTIONS:
        if name in decision:
            checks.append(_expect(f"source_plan_{name}_false", decision.get(name), False))
    return checks


def _audit_contract_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    current_pending = (
        f"current_v14_status={SOURCE_REVIEW_STATUS}" in eof
        and f"next_work_target={SOURCE_REVIEW_AUTHORIZED_NEXT_WORK}" in eof
    )
    current_complete = (
        f"current_v14_status={READY_STATUS}" in eof
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in eof
    )
    status_pending = (
        f"current_v14_status={SOURCE_REVIEW_STATUS}" in status_text
        and f"next_work_target={SOURCE_REVIEW_AUTHORIZED_NEXT_WORK}" in status_text
    )
    status_complete = (
        f"current_v14_status={READY_STATUS}" in status_text
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in status_text
    )
    return [
        _check(
            "audit_latest_boundary_matches_materialization_implementation_plan_gate",
            current_pending or current_complete,
            {
                "status": _extract_line(eof, "current_v14_status="),
                "next": _extract_line(eof, "next_work_target="),
            },
            "pending implementation-plan gate or completed implementation-plan gate",
        ),
        _check(
            "current_status_boundary_matches_materialization_implementation_plan_gate",
            status_pending or status_complete,
            {"pending": status_pending, "complete": status_complete},
            "pending implementation-plan gate or completed implementation-plan gate",
        ),
        _contains("audit_records_static_review_passed", eof, "runtime_artifact_manifest_materialization_static_contract_review_passed=True"),
        _contains("audit_authorizes_implementation_plan", eof, "runtime_artifact_manifest_materialization_implementation_plan_authorized=True"),
        _contains("audit_blocks_materialization", eof, "runtime_artifact_manifest_materialization_authorized=False"),
        _contains("audit_blocks_runtime_execution", eof, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_blocks_candidate_generation", eof, "candidate_generation_by_camp_authorized_by_current_boundary=False"),
        _contains("audit_blocks_dp_modification", eof, "dp_modification_authorized_by_current_boundary=False"),
        _contains("audit_blocks_safety_claim", eof, "safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _source_summary(
    *,
    source_review: dict[str, Any],
    source_plan: dict[str, Any],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    review_decision = _dict(source_review.get("final_decision"))
    plan_decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("materialization_plan"))
    future = _dict(plan.get("future_manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    return {
        "source_hashes": source_hashes,
        "source_review_status": review_decision.get("status"),
        "source_review_passed": review_decision.get("passed"),
        "source_review_authorized_next_work": review_decision.get("authorized_next_work"),
        "source_plan_status": plan_decision.get("status"),
        "source_plan_passed": plan_decision.get("passed"),
        "planned_runtime_manifest_path": plan.get("planned_runtime_manifest_path"),
        "runtime_schema_version": future.get("schema_version"),
        "source_scope": future.get("source_scope"),
        "required_runtime_entries": sorted(artifacts),
        "score_expression": future.get("score_expression"),
    }


def _implementation_plan(
    *,
    source_plan: dict[str, Any],
    planned_runtime_manifest_path: str,
    source_hashes: dict[str, str],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    plan = _dict(source_plan.get("materialization_plan"))
    future = _dict(plan.get("future_manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    aliases = _dict(future.get("sha256"))
    return {
        "status": "implementation_plan_ready_no_runtime_manifest_written",
        "planned_runtime_manifest_path": planned_runtime_manifest_path,
        "runtime_manifest_written_by_this_gate": False,
        "runtime_manifest_materialized_by_this_gate": False,
        "runtime_execution_enabled_by_this_gate": False,
        "source_plan_sha256": source_hashes.get("materialization_plan_sha256"),
        "source_static_review_sha256": source_hashes.get(
            "materialization_static_review_sha256"
        ),
        "future_materializer_contract": {
            "write_strategy": "same-directory temp file plus atomic replace",
            "writes_exactly_one_runtime_manifest": True,
            "planned_output_path": planned_runtime_manifest_path,
            "current_camp_head_at_plan": current_camp_head,
            "required_dp_head": FIXED_DP_HEAD,
            "current_dp_head_at_plan": current_dp_head,
            "manifest_required_content": {
                "schema_version": RUNTIME_SCHEMA_VERSION,
                "source_scope": SOURCE_SCOPE,
                "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
                "default_off": True,
                "fail_closed": True,
                "selection_effect": False,
                "online_selector_change": False,
                "selector_mode": "static",
                "candidate_operation": "fixed DP candidate reranking only",
                "executed_output_policy": "dp_top1",
                "required_candidate_count": EXPECTED_CANDIDATE_COUNT,
                "atom_count": EXPECTED_ATOM_COUNT,
                "atom_schema_version": ATOM_SCHEMA_VERSION,
                "score_expression": SCORE_EXPRESSION,
                "artifacts": artifacts,
                "sha256": aliases,
                "forbidden_runtime_claims": {
                    "selector_promotion_authorized": False,
                    "atom_promotion_authorized": False,
                    "deployment_authorized": False,
                    "safety_benefit_claim_authorized": False,
                    "camp_over_dp_top1_claim_authorized": False,
                },
            },
            "steps": [
                "create parent directory for the planned runtime manifest path",
                "verify DP head equals the fixed TiERIV Diffusion Planner commit",
                "verify atom_scales and static_weights files exist",
                "verify atom_scales and static_weights sha256 values match the source plan",
                "build manifest JSON with only atom_scales and static_weights entries plus hash aliases",
                "validate manifest schema, source scope, default-off fail-closed policy, K=8, atom_count=9, and affine score expression before write",
                "write a temp JSON file in the target directory and fsync before atomic replace",
                "sha256 the final manifest and emit SHA256SUMS evidence",
            ],
        },
    }


def _static_review_requirements() -> list[str]:
    return [
        "prove the implementation plan did not write or materialize the runtime manifest",
        "prove the future materializer writes exactly one JSON manifest at the planned path",
        "prove future writes use same-directory temp file plus atomic replace",
        "prove future materializer verifies fixed DP head before write",
        "prove future materializer verifies atom_scales and static_weights existence and sha256 before write",
        "prove future manifest preserves schema, source scope, default-off fail-closed policy, K=8, 9 atoms, affine scoring, and DP Top-1 execution",
        "prove implementation and materialization remain unauthorized until a later explicit gate",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "writing the runtime manifest in this implementation-plan gate",
        "using the implementation-plan JSON as a runtime manifest",
        "implementing or running the materializer before static review",
        "running replay or runtime selector execution",
        "training CAMP or changing learned weights",
        "generating, modifying, blending, guiding, or postprocessing trajectories",
        "modifying, retraining, or tuning TiERIV Diffusion Planner",
        "using formal seeds 11/12/13",
        "promoting atoms, selectors, deployment artifacts, or safety claims",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_current_work": SOURCE_REVIEW_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "runtime_artifact_manifest_materialization_implementation_plan_ready": bool(passed),
        "runtime_artifact_manifest_materialization_implementation_static_contract_review_authorized": bool(passed),
        "runtime_artifact_manifest_materialization_implementation_authorized": False,
        "runtime_artifact_manifest_materialization_authorized": False,
        "default_off_shadow_selector_runtime_execution_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "runtime_manifest_written_by_this_gate": False,
        "runtime_manifest_materialized_by_this_gate": False,
        "training_executed_by_this_gate": False,
        "score_expression": SCORE_EXPRESSION,
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
    }


def _failure_class(failed: list[str]) -> str:
    if not failed:
        return "unknown"
    if "planned_runtime_manifest_absent" in failed:
        return "runtime_manifest_already_materialized_or_path_conflict"
    if any(name.startswith("source_review_") for name in failed):
        return "runtime_manifest_materialization_static_review_contract_failure"
    if any(name.startswith("source_plan_") or name.startswith("future_") for name in failed):
        return "runtime_manifest_materialization_plan_contract_failure"
    if any(name.startswith("audit_") or name.startswith("current_status_") for name in failed):
        return "v14_eof_contract_mismatch"
    return "runtime_manifest_materialization_implementation_plan_contract_failure"


def _load_json(path: Path, name: str) -> tuple[Any, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, _check(f"{name}_valid_json", False, type(exc).__name__, "valid JSON")
    return payload, _check(f"{name}_json_object", isinstance(payload, dict), type(payload).__name__, "dict")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


def _stable(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return value


def _compact(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 160 else text[:157] + "..."


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value
    )


def _latest_text_block(text: str) -> str:
    marker = "\n## "
    index = text.rfind(marker)
    return text[index + 1 :] if index >= 0 else text


def _extract_line(text: str, prefix: str) -> str | None:
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


if __name__ == "__main__":
    raise SystemExit(main())
