#!/usr/bin/env python3
"""Static review for the v14 runtime artifact manifest plan-only gate."""

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
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_static_contract_review_v1"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_plan_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_static_contract_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_static_contract_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_static_contract_review_rejected"
)
DISABLED_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_static_contract_review_default_off_disabled"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_plan_only"
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
    parser.add_argument("--runtime_artifact_manifest_plan_json", type=Path, required=True)
    parser.add_argument("--runtime_artifact_manifest_plan_script_py", type=Path, required=True)
    parser.add_argument("--runtime_artifact_manifest_plan_test_py", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument(
        "--enable_v14_public_simulator_runtime_artifact_manifest_static_contract_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_artifact_manifest_plan_json=args.runtime_artifact_manifest_plan_json,
        runtime_artifact_manifest_plan_script_py=args.runtime_artifact_manifest_plan_script_py,
        runtime_artifact_manifest_plan_test_py=args.runtime_artifact_manifest_plan_test_py,
        replay_runner_py=args.replay_runner_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_public_simulator_runtime_artifact_manifest_static_contract_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_artifact_manifest_plan_json: Path,
    runtime_artifact_manifest_plan_script_py: Path,
    runtime_artifact_manifest_plan_test_py: Path,
    replay_runner_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
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
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    paths = {
        "runtime_artifact_manifest_plan": runtime_artifact_manifest_plan_json,
        "runtime_artifact_manifest_plan_script": runtime_artifact_manifest_plan_script_py,
        "runtime_artifact_manifest_plan_test": runtime_artifact_manifest_plan_test_py,
        "replay_runner": replay_runner_py,
        "v14_audit": v14_audit_md,
        "current_status": current_status_md,
    }
    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
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

    plan_payload = _dict(payloads.get("runtime_artifact_manifest_plan"))
    checks.extend(_source_plan_checks(plan_payload))
    checks.extend(_source_surface_checks(texts))
    checks.extend(_audit_contract_checks(texts.get("v14_audit", ""), texts.get("current_status", "")))
    passed = all(check["passed"] for check in checks)
    report["contract_summary"] = _contract_summary(plan_payload, report["source_hashes"])
    report["review_scope"] = _review_scope()
    report["forbidden_paths"] = _forbidden_paths()
    report["review_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "runtime_artifact_manifest_static_contract_review.json",
        report,
    )
    (output_dir / "runtime_artifact_manifest_static_contract_review.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("contract_summary", {})
    lines = [
        "# V14 Runtime Artifact Manifest Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Materialization plan authorized: `{decision['runtime_artifact_manifest_materialization_plan_authorized']}`",
        f"- Materialization authorized: `{decision['runtime_artifact_manifest_materialization_authorized']}`",
        f"- Runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Plan",
        "",
        f"- Plan status: `{summary.get('source_plan_status')}`",
        f"- Runtime schema: `{summary.get('runtime_schema_version')}`",
        f"- Source scope: `{summary.get('source_scope')}`",
        f"- Planned runtime manifest path: `{summary.get('planned_runtime_manifest_path')}`",
        f"- Materialized by source plan: `{summary.get('materialized_by_this_gate')}`",
        f"- Required runtime entries: `{summary.get('required_runtime_entries')}`",
        f"- Score expression: `{summary.get('score_expression')}`",
        "",
        "## Review Scope",
        "",
    ]
    for item in report.get("review_scope", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report.get("forbidden_paths", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This review is static only. It does not materialize the runtime "
            "manifest, run replay, train CAMP, generate candidates, modify "
            "Diffusion Planner, promote atoms or selectors, deploy, or "
            "authorize safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report.get("review_checks", []):
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
            "static_review_only": True,
            "runtime_artifact_manifest_materialized": False,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "The source plan must preserve fixed-DP-candidate reranking "
                "only: current-tick K=8 candidate atoms, affine scores "
                "score_k(w)=a_k^T w, approved nonnegative simplex weights, "
                "and no executed trajectory change during default-off shadow."
            ),
        },
        "source_hashes": {},
        "contract_summary": {},
        "review_scope": [],
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "runtime_artifact_manifest_static_contract_review_passed": False,
            "runtime_artifact_manifest_materialization_plan_authorized": False,
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
            "training_executed_by_this_gate": False,
            "runtime_manifest_materialized_by_this_gate": False,
            "failed_checks": [],
            "failure_class": "static_review_gate_disabled",
        },
    }


def _source_plan_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("runtime_artifact_manifest_plan"))
    runtime_entries = _dict(plan.get("required_runtime_entries"))
    atom_entry = _dict(runtime_entries.get("atom_scales"))
    weights_entry = _dict(runtime_entries.get("static_weights"))
    evidence_entries = _dict(plan.get("required_evidence_entries"))
    checks = [
        _expect("source_plan_schema_version", payload.get("schema_version"), PLAN_SCHEMA_VERSION),
        _expect("source_plan_status_ready", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_authorizes_this_review", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_plan_ready_flag", decision.get("runtime_artifact_manifest_plan_ready"), True),
        _expect(
            "source_plan_static_review_authorized",
            decision.get("runtime_artifact_manifest_static_contract_review_authorized"),
            True,
        ),
        _expect("source_plan_materialization_forbidden", decision.get("runtime_artifact_manifest_materialization_authorized"), False),
        _expect("source_plan_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_plan_training_forbidden", decision.get("training_execution_authorized"), False),
        _expect("source_plan_replay_forbidden", decision.get("replay_execution_authorized"), False),
        _expect("source_plan_candidate_generation_forbidden", decision.get("candidate_generation_authorized"), False),
        _expect("source_plan_dp_modification_forbidden", decision.get("dp_modification_authorized"), False),
        _expect("source_plan_selector_promotion_forbidden", decision.get("selector_promotion_authorized"), False),
        _expect("source_plan_atom_promotion_forbidden", decision.get("atom_promotion_authorized"), False),
        _expect("source_plan_deployment_forbidden", decision.get("deployment_authorized"), False),
        _expect("source_plan_safety_claim_forbidden", decision.get("safety_benefit_claim_authorized"), False),
        _expect("source_plan_camp_over_dp_claim_forbidden", decision.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("source_plan_training_not_executed", decision.get("training_executed_by_this_gate"), False),
        _expect("source_plan_runtime_manifest_not_materialized", decision.get("runtime_manifest_materialized_by_this_gate"), False),
        _expect("source_plan_status_no_manifest_materialized", plan.get("status"), "plan_ready_no_runtime_manifest_materialized"),
        _check("source_plan_planned_path_is_json", str(plan.get("planned_runtime_manifest_path", "")).endswith(".json"), plan.get("planned_runtime_manifest_path"), "*.json"),
        _check(
            "source_plan_planned_path_not_materialized",
            not Path(str(plan.get("planned_runtime_manifest_path", ""))).exists(),
            Path(str(plan.get("planned_runtime_manifest_path", ""))).exists(),
            False,
        ),
        _expect("source_plan_runtime_schema", plan.get("runtime_schema_version"), RUNTIME_SCHEMA_VERSION),
        _expect("source_plan_source_scope", plan.get("source_scope"), SOURCE_SCOPE),
        _expect("source_plan_manifest_role", plan.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"),
        _expect("source_plan_this_plan_is_not_runtime_manifest", plan.get("this_plan_is_runtime_manifest"), False),
        _expect("source_plan_materialized_by_this_gate_false", plan.get("materialized_by_this_gate"), False),
        _expect("source_plan_real_runtime_manifest_materialized_false", plan.get("real_runtime_manifest_materialized"), False),
        _expect("source_plan_default_off", plan.get("default_off"), True),
        _expect("source_plan_fail_closed", plan.get("fail_closed"), True),
        _expect("source_plan_selector_mode_static", plan.get("selector_mode"), "static"),
        _expect("source_plan_executed_output_policy", plan.get("executed_output_policy"), "dp_top1"),
        _expect("source_plan_selection_effect_false", plan.get("selection_effect"), False),
        _expect("source_plan_online_selector_change_false", plan.get("online_selector_change"), False),
        _expect("source_plan_candidate_operation", plan.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("source_plan_candidate_count", plan.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("source_plan_atom_count", plan.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("source_plan_atom_schema", plan.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("source_plan_score_expression", plan.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_plan_atom_scales_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("source_plan_atom_scales_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("source_plan_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("source_plan_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _check("source_plan_has_training_summary_evidence", "training_summary" in evidence_entries, list(evidence_entries), "training_summary"),
        _check("source_plan_has_post_static_review_evidence", "post_static_review" in evidence_entries, list(evidence_entries), "post_static_review"),
        _check("source_plan_has_implementation_result_evidence", "implementation_result" in evidence_entries, list(evidence_entries), "implementation_result"),
        _check("source_plan_has_replay_runner_evidence", "replay_runner" in evidence_entries, list(evidence_entries), "replay_runner"),
        _contains_in_list("source_plan_runner_static_mode", plan.get("planned_runner_args"), "--camp_selector_mode static"),
        _contains_in_list("source_plan_runner_future_manifest_placeholder", plan.get("planned_runner_args"), "--camp_shadow_artifact_manifest <future_runtime_manifest_json>"),
        _contains_in_list("source_plan_runner_expected_atom_hash_arg", plan.get("planned_runner_args"), "--camp_shadow_expected_atom_scales_sha256"),
        _contains_in_list("source_plan_runner_expected_weight_hash_arg", plan.get("planned_runner_args"), "--camp_shadow_expected_static_weights_sha256"),
    ]
    for name in BLOCKED_ACTIONS:
        if name in decision:
            checks.append(_expect(f"source_plan_{name}_false", decision.get(name), False))
    return checks


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    script = texts.get("runtime_artifact_manifest_plan_script", "")
    test = texts.get("runtime_artifact_manifest_plan_test", "")
    runner = texts.get("replay_runner", "")
    return [
        _contains("script_schema_constant", script, "SCHEMA_VERSION"),
        _contains_all(
            "script_v14_plan_schema",
            script,
            (
                "dp_camp_v14_public_simulator_default_off_shadow_selector_",
                "runtime_artifact_manifest_plan_v1",
            ),
        ),
        _contains("script_runtime_schema", script, RUNTIME_SCHEMA_VERSION),
        _contains("script_source_scope", script, SOURCE_SCOPE),
        _contains("script_blocks_materialization", script, '"materialized_by_this_gate": False'),
        _contains("script_blocks_real_manifest", script, '"real_runtime_manifest_materialized": False'),
        _contains("script_requires_atom_entry", script, '"atom_scales"'),
        _contains("script_requires_weight_entry", script, '"static_weights"'),
        _contains("script_affine_score", script, SCORE_EXPRESSION),
        _contains_all(
            "script_authorizes_static_review_only",
            script,
            (
                "AUTHORIZED_NEXT_WORK",
                "runtime_artifact_manifest_static_contract_review_only",
            ),
        ),
        _contains("test_ready_case", test, "test_runtime_artifact_manifest_plan_ready_without_materializing"),
        _contains("test_disabled_case", test, "test_runtime_artifact_manifest_plan_is_disabled_until_enabled"),
        _contains("test_rejects_weight_drift", test, "test_runtime_artifact_manifest_plan_rejects_weight_simplex_drift"),
        _contains("test_rejects_stale_schema", test, "test_runtime_artifact_manifest_plan_rejects_stale_v13_runtime_schema"),
        _contains("test_accepts_completed_boundary", test, "test_runtime_artifact_manifest_plan_accepts_completed_boundary"),
        _contains("runner_v14_runtime_schema", runner, RUNTIME_SCHEMA_VERSION),
        _contains("runner_source_scope", runner, SOURCE_SCOPE),
        _contains("runner_fail_closed", runner, "def _mark_shadow_selector_fail_closed"),
        _contains("runner_forces_dp_top1", runner, "selected_index = 0 if default_off_shadow_selector else baseline_selected_index"),
        _contains("runner_score_expression", runner, f'"score_expression": "{SCORE_EXPRESSION}"'),
    ]


def _audit_contract_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    current_pending = (
        f"current_v14_status={SOURCE_PLAN_STATUS}" in eof
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof
    )
    current_complete = (
        f"current_v14_status={READY_STATUS}" in eof
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in eof
    )
    status_pending = (
        f"current_v14_status={SOURCE_PLAN_STATUS}" in status_text
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text
    )
    status_complete = (
        f"current_v14_status={READY_STATUS}" in status_text
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in status_text
    )
    return [
        _check(
            "audit_latest_boundary_matches_static_review_gate",
            current_pending or current_complete,
            {
                "status": _extract_line(eof, "current_v14_status="),
                "next": _extract_line(eof, "next_work_target="),
            },
            "pending static-review gate or completed static-review gate",
        ),
        _check(
            "current_status_boundary_matches_static_review_gate",
            status_pending or status_complete,
            {
                "pending": status_pending,
                "complete": status_complete,
            },
            "pending static-review gate or completed static-review gate",
        ),
        _contains("audit_records_plan_ready", eof, "runtime_artifact_manifest_plan_ready=True"),
        _contains("audit_authorizes_static_review", eof, "runtime_artifact_manifest_static_contract_review_authorized=True"),
        _contains("audit_blocks_materialization", eof, "runtime_artifact_manifest_materialization_authorized=False"),
        _contains("audit_blocks_runtime_execution", eof, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_blocks_training", eof, "training_execution_authorized=False"),
        _contains("audit_blocks_replay", eof, "replay_execution_authorized=False"),
        _contains("audit_blocks_candidate_generation", eof, "candidate_generation_authorized=False"),
        _contains("audit_blocks_dp_modification", eof, "dp_modification_authorized=False"),
        _contains("audit_blocks_safety_claim", eof, "safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _contract_summary(
    payload: dict[str, Any],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("runtime_artifact_manifest_plan"))
    runtime_entries = _dict(plan.get("required_runtime_entries"))
    evidence_entries = _dict(plan.get("required_evidence_entries"))
    return {
        "source_plan_status": decision.get("status"),
        "runtime_schema_version": plan.get("runtime_schema_version"),
        "source_scope": plan.get("source_scope"),
        "planned_runtime_manifest_path": plan.get("planned_runtime_manifest_path"),
        "materialized_by_this_gate": plan.get("materialized_by_this_gate"),
        "required_runtime_entries": sorted(runtime_entries),
        "required_evidence_entries": sorted(evidence_entries),
        "score_expression": plan.get("score_expression"),
        "source_hashes": source_hashes,
    }


def _review_scope() -> list[str]:
    return [
        "prove the source plan is not a materialized runtime manifest",
        "prove future runtime entries are only atom_scales and static_weights",
        "prove the v14 runtime schema and public simulator source scope are pinned",
        "prove default-off fail-closed execution remains DP Top-1",
        "prove scoring remains affine score_k(w)=a_k^T w over fixed K=8 candidates",
        "prove materialization, runtime execution, replay, training, candidate generation, DP modification, promotion, deployment, and safety claims remain unauthorized",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "writing the future runtime manifest in this static-review gate",
        "using the source plan JSON as a runtime manifest",
        "running replay or runtime selection",
        "routing shadow_selected_index into executed trajectory selection",
        "generating, modifying, blending, guiding, or postprocessing trajectories",
        "modifying, retraining, or tuning TiERIV Diffusion Planner",
        "promoting atoms or selector weights",
        "claiming deployment readiness, safety benefit, or CAMP superiority over DP Top-1",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "runtime_artifact_manifest_static_contract_review_passed": bool(passed),
        "runtime_artifact_manifest_materialization_plan_authorized": bool(passed),
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
        "training_executed_by_this_gate": False,
        "runtime_manifest_materialized_by_this_gate": False,
        "score_expression": SCORE_EXPRESSION,
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
    }


def _failure_class(failed: list[str]) -> str:
    if not failed:
        return "unknown"
    if any(name.startswith("source_plan_") for name in failed):
        return "runtime_artifact_manifest_plan_contract_failure"
    if any(name.startswith("audit_") or name.startswith("current_status_") for name in failed):
        return "v14_eof_contract_mismatch"
    return "runtime_artifact_manifest_static_contract_failure"


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


def _contains_all(name: str, text: str, needles: tuple[str, ...]) -> dict[str, Any]:
    missing = [needle for needle in needles if needle not in text]
    return _check(name, not missing, missing or "all present", list(needles))


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
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _latest_text_block(text: str) -> str:
    marker = "\n## "
    index = text.rfind(marker)
    return text[index + 1 :] if index >= 0 else text


def _extract_line(text: str, prefix: str) -> str | None:
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


if __name__ == "__main__":
    raise SystemExit(main())
