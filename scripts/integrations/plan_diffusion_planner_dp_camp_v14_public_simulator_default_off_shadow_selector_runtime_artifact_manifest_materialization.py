#!/usr/bin/env python3
"""Plan-only v14 runtime artifact manifest materialization gate."""

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
PLAN_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_plan_v1"
)
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_static_contract_review_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_plan_v1"
)
SOURCE_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_static_contract_review_passed"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_plan_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_plan_rejected"
)
DISABLED_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_plan_default_off_disabled"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_static_contract_review_only"
)
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 9

BLOCKED_ACTIONS = (
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
    parser.add_argument("--runtime_artifact_manifest_static_review_json", type=Path, required=True)
    parser.add_argument("--runtime_artifact_manifest_plan_json", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
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
        "--enable_v14_public_simulator_runtime_artifact_manifest_materialization_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_artifact_manifest_static_review_json=(
            args.runtime_artifact_manifest_static_review_json
        ),
        runtime_artifact_manifest_plan_json=args.runtime_artifact_manifest_plan_json,
        replay_runner_py=args.replay_runner_py,
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
            args.enable_v14_public_simulator_runtime_artifact_manifest_materialization_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_artifact_manifest_static_review_json: Path,
    runtime_artifact_manifest_plan_json: Path,
    replay_runner_py: Path,
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
        "runtime_artifact_manifest_static_review": (
            runtime_artifact_manifest_static_review_json
        ),
        "runtime_artifact_manifest_plan": runtime_artifact_manifest_plan_json,
        "replay_runner": replay_runner_py,
        "v14_audit": v14_audit_md,
        "current_status": current_status_md,
    }
    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
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
            "planned_runtime_manifest_not_preexisting",
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

    source_review = _dict(payloads.get("runtime_artifact_manifest_static_review"))
    source_plan = _dict(payloads.get("runtime_artifact_manifest_plan"))
    checks.extend(_source_review_checks(source_review))
    checks.extend(_source_plan_checks(source_plan, planned_runtime_manifest_path))
    checks.extend(_source_surface_checks(texts))
    checks.extend(_audit_contract_checks(texts.get("v14_audit", ""), texts.get("current_status", "")))
    passed = all(check["passed"] for check in checks)

    report["source_summary"] = _source_summary(
        source_review,
        source_plan,
        report["source_hashes"],
    )
    report["materialization_plan"] = _materialization_plan(
        source_plan=source_plan,
        planned_runtime_manifest_path=planned_runtime_manifest_path,
        source_hashes=report["source_hashes"],
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    report["future_static_review_requirements"] = _future_static_review_requirements()
    report["forbidden_paths"] = _forbidden_paths()
    report["plan_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_artifact_manifest_materialization_plan.json", report)
    (output_dir / "runtime_artifact_manifest_materialization_plan.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report.get("materialization_plan", {})
    future = plan.get("future_manifest_required_content", {})
    lines = [
        "# V14 Runtime Artifact Manifest Materialization Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Materialization static review authorized: `{decision['runtime_artifact_manifest_materialization_static_contract_review_authorized']}`",
        f"- Runtime manifest materialization authorized: `{decision['runtime_artifact_manifest_materialization_authorized']}`",
        f"- Runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Materialization Plan",
        "",
        f"- Planned runtime manifest path: `{plan.get('planned_runtime_manifest_path')}`",
        f"- Runtime manifest written by this gate: `{plan.get('runtime_manifest_written_by_this_gate')}`",
        f"- This plan is runtime manifest: `{plan.get('this_plan_is_runtime_manifest')}`",
        f"- Runtime schema: `{future.get('schema_version')}`",
        f"- Source scope: `{future.get('source_scope')}`",
        f"- Executed output policy: `{future.get('executed_output_policy')}`",
        f"- Score expression: `{future.get('score_expression')}`",
        "",
        "## Required Runtime Entries",
        "",
    ]
    artifacts = future.get("artifacts", {})
    if isinstance(artifacts, dict):
        for name, entry in artifacts.items():
            if isinstance(entry, dict):
                lines.append(
                    f"- `{name}` path=`{entry.get('path')}` sha256=`{entry.get('sha256')}`"
                )
    lines.extend(["", "## Future Static Review Requirements", ""])
    for item in report.get("future_static_review_requirements", []):
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
                "Future runtime manifest materialization must preserve only "
                "immutable artifact paths and hashes for fixed-DP-candidate "
                "reranking. It must not alter DP candidates, scores, weights, "
                "selector routing, or executed trajectory behavior."
            ),
        },
        "source_hashes": {},
        "source_summary": {},
        "materialization_plan": {},
        "future_static_review_requirements": [],
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "runtime_artifact_manifest_materialization_plan_ready": False,
            "runtime_artifact_manifest_materialization_static_contract_review_authorized": False,
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
            "failure_class": "materialization_plan_gate_disabled",
        },
    }


def _source_review_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    summary = _dict(payload.get("contract_summary"))
    return [
        _expect("source_review_schema_version", payload.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        _expect("source_review_passed", decision.get("passed"), True),
        _expect("source_review_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_review_authorizes_this_plan", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_review_passed_flag", decision.get("runtime_artifact_manifest_static_contract_review_passed"), True),
        _expect("source_review_materialization_plan_authorized", decision.get("runtime_artifact_manifest_materialization_plan_authorized"), True),
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
        *[
            _expect(f"source_review_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
            if name in decision
        ],
    ]


def _source_plan_checks(
    payload: dict[str, Any],
    planned_runtime_manifest_path: str,
) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("runtime_artifact_manifest_plan"))
    runtime_entries = _dict(plan.get("required_runtime_entries"))
    evidence_entries = _dict(plan.get("required_evidence_entries"))
    atom_entry = _dict(runtime_entries.get("atom_scales"))
    weights_entry = _dict(runtime_entries.get("static_weights"))
    source_planned_path = str(plan.get("planned_runtime_manifest_path", ""))
    return [
        _expect("source_plan_schema_version", payload.get("schema_version"), PLAN_SCHEMA_VERSION),
        _expect("source_plan_status", decision.get("status"), "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_ready"),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_materialization_forbidden", decision.get("runtime_artifact_manifest_materialization_authorized"), False),
        _expect("source_plan_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_plan_status_no_manifest_written", plan.get("status"), "plan_ready_no_runtime_manifest_materialized"),
        _expect("source_plan_runtime_schema", plan.get("runtime_schema_version"), RUNTIME_SCHEMA_VERSION),
        _expect("source_plan_source_scope", plan.get("source_scope"), SOURCE_SCOPE),
        _expect("source_plan_manifest_role", plan.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"),
        _expect("source_plan_this_plan_is_not_manifest", plan.get("this_plan_is_runtime_manifest"), False),
        _expect("source_plan_materialized_by_this_gate_false", plan.get("materialized_by_this_gate"), False),
        _expect("source_plan_real_runtime_manifest_materialized_false", plan.get("real_runtime_manifest_materialized"), False),
        _expect("source_plan_planned_path_matches_requested", source_planned_path, planned_runtime_manifest_path),
        _expect("source_plan_default_off", plan.get("default_off"), True),
        _expect("source_plan_fail_closed", plan.get("fail_closed"), True),
        _expect("source_plan_selector_mode", plan.get("selector_mode"), "static"),
        _expect("source_plan_executed_output_policy", plan.get("executed_output_policy"), "dp_top1"),
        _expect("source_plan_selection_effect_false", plan.get("selection_effect"), False),
        _expect("source_plan_online_selector_change_false", plan.get("online_selector_change"), False),
        _expect("source_plan_candidate_operation", plan.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("source_plan_candidate_count", plan.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("source_plan_atom_count", plan.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("source_plan_atom_schema", plan.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("source_plan_score_expression", plan.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_plan_atom_scales_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("source_plan_atom_scales_path_present", bool(atom_entry.get("path")), atom_entry.get("path"), "nonempty path"),
        _check("source_plan_atom_scales_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("source_plan_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("source_plan_static_weights_path_present", bool(weights_entry.get("path")), weights_entry.get("path"), "nonempty path"),
        _check("source_plan_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _check("source_plan_has_training_summary_evidence", "training_summary" in evidence_entries, sorted(evidence_entries), "training_summary"),
        _check("source_plan_has_post_static_review_evidence", "post_static_review" in evidence_entries, sorted(evidence_entries), "post_static_review"),
        _check("source_plan_has_implementation_result_evidence", "implementation_result" in evidence_entries, sorted(evidence_entries), "implementation_result"),
        _check("source_plan_has_replay_runner_evidence", "replay_runner" in evidence_entries, sorted(evidence_entries), "replay_runner"),
        _contains_in_list("source_plan_future_manifest_placeholder", plan.get("planned_runner_args"), "--camp_shadow_artifact_manifest <future_runtime_manifest_json>"),
        _contains_in_list("source_plan_expected_atom_hash_arg", plan.get("planned_runner_args"), "--camp_shadow_expected_atom_scales_sha256"),
        _contains_in_list("source_plan_expected_weight_hash_arg", plan.get("planned_runner_args"), "--camp_shadow_expected_static_weights_sha256"),
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    runner = texts.get("replay_runner", "")
    return [
        _contains("runner_manifest_loader_present", runner, "def _load_shadow_artifact_manifest"),
        _contains("runner_manifest_expected_sha_lookup_present", runner, "def _manifest_expected_sha256"),
        _contains("runner_atom_scales_logical_name", runner, 'logical_name="atom_scales"'),
        _contains("runner_static_weights_logical_name", runner, 'logical_name="static_weights"'),
        _contains("runner_hash_mismatch_fails_closed", runner, "hash_mismatch"),
        _contains("runner_v14_runtime_schema", runner, RUNTIME_SCHEMA_VERSION),
        _contains("runner_source_scope", runner, SOURCE_SCOPE),
        _contains("runner_forces_dp_top1", runner, "selected_index = 0 if default_off_shadow_selector else baseline_selected_index"),
        _contains("runner_score_expression", runner, f'"score_expression": "{SCORE_EXPRESSION}"'),
    ]


def _audit_contract_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    current_pending = (
        f"current_v14_status={SOURCE_REVIEW_STATUS}" in eof
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof
    )
    current_complete = (
        f"current_v14_status={READY_STATUS}" in eof
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in eof
    )
    status_pending = (
        f"current_v14_status={SOURCE_REVIEW_STATUS}" in status_text
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text
    )
    status_complete = (
        f"current_v14_status={READY_STATUS}" in status_text
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in status_text
    )
    return [
        _check(
            "audit_latest_boundary_matches_materialization_plan_gate",
            current_pending or current_complete,
            {
                "status": _extract_line(eof, "current_v14_status="),
                "next": _extract_line(eof, "next_work_target="),
            },
            "pending materialization-plan gate or completed materialization-plan gate",
        ),
        _check(
            "current_status_boundary_matches_materialization_plan_gate",
            status_pending or status_complete,
            {"pending": status_pending, "complete": status_complete},
            "pending materialization-plan gate or completed materialization-plan gate",
        ),
        _contains("audit_records_static_review_passed", eof, "runtime_artifact_manifest_static_contract_review_passed=True"),
        _contains("audit_authorizes_materialization_plan", eof, "runtime_artifact_manifest_materialization_plan_authorized=True"),
        _contains("audit_blocks_materialization", eof, "runtime_artifact_manifest_materialization_authorized=False"),
        _contains("audit_blocks_runtime_execution", eof, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_blocks_training", eof, "training_execution_authorized=False"),
        _contains("audit_blocks_replay", eof, "replay_execution_authorized=False"),
        _contains("audit_blocks_candidate_generation", eof, "candidate_generation_authorized=False"),
        _contains("audit_blocks_dp_modification", eof, "dp_modification_authorized=False"),
        _contains("audit_blocks_safety_claim", eof, "safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _source_summary(
    source_review: dict[str, Any],
    source_plan: dict[str, Any],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    review_decision = _dict(source_review.get("final_decision"))
    plan_decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("runtime_artifact_manifest_plan"))
    return {
        "source_hashes": source_hashes,
        "source_review_status": review_decision.get("status"),
        "source_review_passed": review_decision.get("passed"),
        "source_review_authorized_next_work": review_decision.get("authorized_next_work"),
        "source_plan_status": plan_decision.get("status"),
        "source_plan_passed": plan_decision.get("passed"),
        "runtime_schema_version": plan.get("runtime_schema_version"),
        "source_scope": plan.get("source_scope"),
        "required_runtime_entries": sorted(_dict(plan.get("required_runtime_entries"))),
        "required_evidence_entries": sorted(_dict(plan.get("required_evidence_entries"))),
    }


def _materialization_plan(
    *,
    source_plan: dict[str, Any],
    planned_runtime_manifest_path: str,
    source_hashes: dict[str, str],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    plan = _dict(source_plan.get("runtime_artifact_manifest_plan"))
    runtime_entries = _dict(plan.get("required_runtime_entries"))
    evidence_entries = _dict(plan.get("required_evidence_entries"))
    atom_entry = _dict(runtime_entries.get("atom_scales"))
    weights_entry = _dict(runtime_entries.get("static_weights"))
    atom_path = str(atom_entry.get("path"))
    weights_path = str(weights_entry.get("path"))
    atom_sha = atom_entry.get("sha256")
    weights_sha = weights_entry.get("sha256")
    aliases = {
        "atom_scales": atom_sha,
        atom_path: atom_sha,
        Path(atom_path).name: atom_sha,
        "static_weights": weights_sha,
        weights_path: weights_sha,
        Path(weights_path).name: weights_sha,
    }
    return {
        "status": "plan_ready_no_runtime_manifest_written",
        "planned_runtime_manifest_path": planned_runtime_manifest_path,
        "source_planned_runtime_manifest_path": plan.get("planned_runtime_manifest_path"),
        "this_plan_is_runtime_manifest": False,
        "runtime_manifest_written_by_this_gate": False,
        "runtime_manifest_materialized_by_this_gate": False,
        "runtime_execution_enabled_by_this_gate": False,
        "future_manifest_required_content": {
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
            "camp_head_at_plan": current_camp_head,
            "required_dp_head": FIXED_DP_HEAD,
            "dp_head_at_plan": current_dp_head,
            "artifacts": {
                "atom_scales": {
                    "logical_name": "atom_scales",
                    "path": atom_path,
                    "sha256": atom_sha,
                    "required": True,
                },
                "static_weights": {
                    "logical_name": "static_weights",
                    "path": weights_path,
                    "sha256": weights_sha,
                    "required": True,
                },
            },
            "sha256": aliases,
            "evidence": evidence_entries,
            "source_plan_sha256": source_hashes.get("runtime_artifact_manifest_plan_sha256"),
            "source_static_review_sha256": source_hashes.get(
                "runtime_artifact_manifest_static_review_sha256"
            ),
            "forbidden_runtime_claims": {
                "selector_promotion_authorized": False,
                "atom_promotion_authorized": False,
                "deployment_authorized": False,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
            },
        },
        "future_materializer_preconditions": [
            "run only after materialization implementation planning and static review pass",
            "write exactly one runtime manifest file at the planned path",
            "write atom_scales and static_weights entries with logical, absolute-path, and basename hash aliases",
            "verify atom scales and static weights files exist and match planned sha256 before writing",
            "verify DP head remains fixed before writing",
            "do not execute replay or enable runtime selection while writing the manifest",
        ],
        "future_runtime_invocation_template": [
            "--camp_selector_mode static",
            f"--num_candidates {EXPECTED_CANDIDATE_COUNT}",
            "--camp_default_off_shadow_selector",
            f"--camp_atom_scales {atom_path}",
            f"--camp_static_weights {weights_path}",
            f"--camp_shadow_artifact_manifest {planned_runtime_manifest_path}",
            f"--camp_shadow_expected_atom_scales_sha256 {atom_sha}",
            f"--camp_shadow_expected_static_weights_sha256 {weights_sha}",
        ],
    }


def _future_static_review_requirements() -> list[str]:
    return [
        "prove the materialization plan output is not itself a runtime manifest",
        "prove no runtime manifest file was written by the plan-only gate",
        "prove future manifest content pins the v14 runtime schema and source scope",
        "prove future manifest includes atom_scales and static_weights logical entries and sha256 aliases",
        "prove future manifest preserves fixed DP K=8, 9 approved atoms, affine scoring, and DP Top-1 execution policy",
        "prove future materialization still does not execute replay, train CAMP, generate candidates, modify DP, promote, deploy, or claim safety benefit",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "writing the runtime manifest in this plan-only gate",
        "using this plan JSON as --camp_shadow_artifact_manifest",
        "running replay with the planned manifest path",
        "enabling runtime selector effects",
        "training CAMP or changing weights during manifest planning",
        "generating, modifying, blending, guiding, or postprocessing trajectories",
        "modifying, retraining, or tuning TiERIV Diffusion Planner",
        "promoting atoms, selectors, deployment artifacts, or safety claims",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "runtime_artifact_manifest_materialization_plan_ready": bool(passed),
        "runtime_artifact_manifest_materialization_static_contract_review_authorized": bool(passed),
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
    if "planned_runtime_manifest_not_preexisting" in failed:
        return "runtime_manifest_already_materialized_or_path_conflict"
    if any(name.startswith("source_review_") for name in failed):
        return "runtime_artifact_manifest_static_review_contract_failure"
    if any(name.startswith("source_plan_") for name in failed):
        return "runtime_artifact_manifest_plan_contract_failure"
    if any(name.startswith("audit_") or name.startswith("current_status_") for name in failed):
        return "v14_eof_contract_mismatch"
    return "runtime_artifact_manifest_materialization_plan_contract_failure"


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


def _contains_in_list(name: str, value: Any, needle: str) -> dict[str, Any]:
    values = value if isinstance(value, list) else []
    passed = any(needle in str(item) for item in values)
    return _check(name, passed, values, f"contains {needle}")


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
