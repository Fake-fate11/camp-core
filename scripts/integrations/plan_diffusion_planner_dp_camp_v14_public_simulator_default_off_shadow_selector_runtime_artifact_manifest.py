#!/usr/bin/env python3
"""Plan-only runtime artifact manifest gate for v14 DP-CAMP shadow selection."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
RUNTIME_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
)
SOURCE_SCOPE = "public_simulator_fixed_dp_candidate_tensor"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_plan_v1"
)
SOURCE_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "post_implementation_static_contract_review_passed"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_plan_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_plan_rejected"
)
DISABLED_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_plan_default_off_disabled"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_static_contract_review_only"
)
IMPLEMENTATION_AUTHORIZED_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "implementation_only_after_explicit_user_authorization"
)
POST_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "post_implementation_static_contract_review_v1"
)
TRAINING_TYPE = "diffusion_planner_static_candidate_preference"
TRAINING_LABEL_SOURCE = "dp_reward"
TRAINING_REWARD_KEY = "quality_without_progress"
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
EXPECTED_CANDIDATE_COUNT = 8
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
EXPECTED_ATOM_COUNT = len(APPROVED_ATOM_NAMES)
EXPECTED_CONTRACT_RECORDS = 3200
MIN_TRAINING_RECORDS = 1000

BLOCKED_ACTIONS = (
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
    "runtime_artifact_manifest_materialization_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--atom_scales_json", type=Path, required=True)
    parser.add_argument("--static_weights_npy", type=Path, required=True)
    parser.add_argument("--post_static_review_json", type=Path, required=True)
    parser.add_argument("--implementation_result_json", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--planned_runtime_manifest_path", default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument(
        "--enable_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        training_summary_json=args.training_summary_json,
        atom_scales_json=args.atom_scales_json,
        static_weights_npy=args.static_weights_npy,
        post_static_review_json=args.post_static_review_json,
        implementation_result_json=args.implementation_result_json,
        replay_runner_py=args.replay_runner_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        planned_runtime_manifest_path=args.planned_runtime_manifest_path,
        label=args.label,
        enabled=(
            args.enable_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    training_summary_json: Path,
    atom_scales_json: Path,
    static_weights_npy: Path,
    post_static_review_json: Path,
    implementation_result_json: Path,
    replay_runner_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    planned_runtime_manifest_path: str | None = None,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    planned_path = planned_runtime_manifest_path or str(
        output_dir
        / "planned_runtime"
        / "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.json"
    )
    report = _empty_report(
        enabled=enabled,
        label=label,
        output_dir=output_dir,
        planned_runtime_manifest_path=planned_path,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    paths = {
        "training_summary": training_summary_json,
        "atom_scales": atom_scales_json,
        "static_weights_npy": static_weights_npy,
        "post_static_review": post_static_review_json,
        "implementation_result": implementation_result_json,
        "replay_runner": replay_runner_py,
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
            planned_path.endswith(".json"),
            planned_path,
            "*.json",
        ),
        _check(
            "planned_runtime_manifest_not_preexisting",
            not Path(planned_path).exists(),
            Path(planned_path).exists(),
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
        if name == "static_weights_npy":
            continue
        if path.suffix == ".json":
            loaded, json_check = _load_json(path, name)
            payloads[name] = loaded
            checks.append(json_check)
        else:
            texts[name] = path.read_text(encoding="utf-8")

    weights_array, weight_checks = _load_weights(static_weights_npy)
    checks.extend(weight_checks)
    training_summary = _dict(payloads.get("training_summary"))
    atom_scales = _dict(payloads.get("atom_scales"))
    post_review = _dict(payloads.get("post_static_review"))
    implementation_result = _dict(payloads.get("implementation_result"))
    checks.extend(_training_summary_checks(training_summary, weights_array))
    checks.extend(_atom_scales_checks(atom_scales))
    checks.extend(_post_static_review_checks(post_review))
    checks.extend(_implementation_result_checks(implementation_result))
    checks.extend(_runner_contract_checks(texts.get("replay_runner", "")))
    checks.extend(
        _audit_contract_checks(
            texts.get("v14_audit", ""),
            texts.get("current_status", ""),
        )
    )
    passed = all(check["passed"] for check in checks)
    report["artifact_summary"] = _artifact_summary(
        training_summary=training_summary,
        atom_scales=atom_scales,
        weights_array=weights_array,
        source_hashes=report["source_hashes"],
        paths=paths,
    )
    report["runtime_artifact_manifest_plan"] = _runtime_manifest_plan(
        training_summary_json=training_summary_json,
        atom_scales_json=atom_scales_json,
        static_weights_npy=static_weights_npy,
        post_static_review_json=post_static_review_json,
        implementation_result_json=implementation_result_json,
        replay_runner_py=replay_runner_py,
        planned_runtime_manifest_path=planned_path,
        source_hashes=report["source_hashes"],
    )
    report["future_static_review_requirements"] = _future_static_review_requirements()
    report["forbidden_paths"] = _forbidden_paths()
    report["plan_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "default_off_shadow_selector_runtime_artifact_manifest_plan.json",
        report,
    )
    (output_dir / "default_off_shadow_selector_runtime_artifact_manifest_plan.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report.get("runtime_artifact_manifest_plan", {})
    lines = [
        "# V14 Default-Off Shadow Selector Runtime Artifact Manifest Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Runtime manifest static review authorized: `{decision['runtime_artifact_manifest_static_contract_review_authorized']}`",
        f"- Runtime manifest materialization authorized: `{decision['runtime_artifact_manifest_materialization_authorized']}`",
        f"- Runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Planned Runtime Manifest",
        "",
        f"- Planned path: `{plan.get('planned_runtime_manifest_path')}`",
        f"- Runtime schema: `{plan.get('runtime_schema_version')}`",
        f"- Source scope: `{plan.get('source_scope')}`",
        f"- Materialized by this gate: `{plan.get('materialized_by_this_gate')}`",
        f"- Default-off / fail-closed: `{plan.get('default_off')}` / `{plan.get('fail_closed')}`",
        f"- Executed output policy: `{plan.get('executed_output_policy')}`",
        f"- Score expression: `{plan.get('score_expression')}`",
        "",
        "## Required Runtime Entries",
        "",
    ]
    entries = plan.get("required_runtime_entries", {})
    if isinstance(entries, dict):
        for name, entry in entries.items():
            if isinstance(entry, dict):
                lines.append(
                    f"- `{name}` path=`{entry.get('path')}` sha256=`{entry.get('sha256')}`"
                )
    lines.extend(["", "## Evidence Entries", ""])
    evidence = plan.get("required_evidence_entries", {})
    if isinstance(evidence, dict):
        for name, entry in evidence.items():
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
            "This gate is plan-only. It writes only this plan artifact. It does "
            "not write the future runtime manifest, run replay, train CAMP, "
            "generate candidates, modify Diffusion Planner, promote atoms or "
            "selectors, deploy, or authorize safety/CAMP-over-DP claims.",
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
            "plan_only": True,
            "static_only": True,
            "enabled": bool(enabled),
            "output_dir": str(output_dir),
            "planned_runtime_manifest_path": planned_runtime_manifest_path,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "runtime_manifest_materialized": False,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "math_boundary": (
                "CAMP remains a fixed-DP-candidate reranker. The future "
                "default-off shadow selector may only load immutable static "
                "weights and atom scales, compute affine scores "
                "score_k(w)=a_k^T w over current-tick K=8 DP candidates, and "
                "log shadow_selected_index. Executed trajectory output remains "
                "DP Top-1."
            ),
        },
        "source_hashes": {},
        "artifact_summary": {},
        "runtime_artifact_manifest_plan": {},
        "future_static_review_requirements": [],
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "runtime_artifact_manifest_plan_ready": False,
            "runtime_artifact_manifest_static_contract_review_authorized": False,
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
            "failure_class": "plan_gate_disabled",
        },
    }


def _training_summary_checks(
    payload: dict[str, Any],
    weights_array: np.ndarray | None,
) -> list[dict[str, Any]]:
    contract = _dict(payload.get("dp_native_training_data_contract"))
    trained_weights = _float_vector(payload.get("trained_weights"))
    return [
        _expect("training_type", payload.get("training_type"), TRAINING_TYPE),
        _expect("training_label_source", payload.get("label_source"), TRAINING_LABEL_SOURCE),
        _expect("training_reward_key", payload.get("reward_key"), TRAINING_REWARD_KEY),
        _expect("training_reward_progress_weight", payload.get("reward_progress_weight"), 2.0),
        _check(
            "training_records_large_enough",
            _int_at_least(payload.get("num_records"), MIN_TRAINING_RECORDS),
            payload.get("num_records"),
            f">={MIN_TRAINING_RECORDS}",
        ),
        _check(
            "training_dropped_records_nonnegative",
            _int_at_least(payload.get("dropped_records_without_feasible_candidate"), 0),
            payload.get("dropped_records_without_feasible_candidate"),
            ">=0",
        ),
        _expect("training_num_candidates", payload.get("num_candidates"), EXPECTED_CANDIDATE_COUNT),
        _expect("training_num_atoms", payload.get("num_atoms"), EXPECTED_ATOM_COUNT),
        _expect("training_atom_schema_version", payload.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("training_atom_names", tuple(payload.get("atom_names") or ()), APPROVED_ATOM_NAMES),
        _check("training_weights_simplex", _simplex(trained_weights), trained_weights, "finite nonnegative simplex"),
        _check(
            "training_weights_match_npy",
            _matches_array(trained_weights, weights_array),
            trained_weights,
            "same values as static_weights_npy",
        ),
        _check(
            "training_history_present",
            isinstance(payload.get("history"), list) and len(payload["history"]) > 0,
            len(payload.get("history") or []),
            ">0",
        ),
        _check(
            "training_oracle_match_rate_finite",
            _finite_float_in_range(payload.get("oracle_match_rate"), 0.0, 1.0),
            payload.get("oracle_match_rate"),
            "[0,1]",
        ),
        _check(
            "training_feasible_candidate_rate_finite",
            _finite_float_in_range(payload.get("feasible_candidate_rate"), 0.0, 1.0),
            payload.get("feasible_candidate_rate"),
            "[0,1]",
        ),
        _expect("training_contract_schema", contract.get("schema_version"), "clean_dp_native_training_data_contract_validator_v1"),
        _expect("training_contract_records", contract.get("records"), EXPECTED_CONTRACT_RECORDS),
        _expect("training_contract_failed_records", contract.get("failed_records"), []),
        _expect("training_contract_passed", contract.get("passed"), True),
        _expect("training_contract_read_only", contract.get("read_only"), True),
        _expect("training_contract_future_input", contract.get("future_training_input_contract_satisfied"), True),
        _expect("training_contract_replay_not_executed", contract.get("replay_executed"), False),
        _expect("training_contract_candidate_generation_not_executed", contract.get("candidate_generation_executed"), False),
        _expect("training_contract_training_not_authorized_by_contract", contract.get("training_execution_authorized"), False),
        _expect("training_contract_dp_modification_forbidden", contract.get("dp_modification_authorized"), False),
        _expect("training_contract_safety_claim_forbidden", contract.get("safety_benefit_claim_authorized"), False),
        _expect("training_contract_camp_over_dp_claim_forbidden", contract.get("camp_over_dp_top1_claim_authorized"), False),
    ]


def _atom_scales_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("atom_scales_atom_schema_version", payload.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("atom_scales_atom_names", tuple(payload.get("atom_names") or ()), APPROVED_ATOM_NAMES),
        _check(
            "atom_scales_positive_finite",
            _finite_positive_vector(payload.get("scales"), EXPECTED_ATOM_COUNT),
            payload.get("scales"),
            f"{EXPECTED_ATOM_COUNT} positive finite scales",
        ),
    ]


def _post_static_review_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    analysis = _dict(payload.get("analysis"))
    blocked = _dict(payload.get("blocked_actions"))
    checks = [
        _expect("post_review_schema_version", payload.get("schema_version"), POST_REVIEW_SCHEMA_VERSION),
        _expect("post_review_passed", decision.get("passed"), True),
        _expect("post_review_status", decision.get("status"), SOURCE_STATUS),
        _expect("post_review_failed_checks", decision.get("failed_checks"), []),
        _expect("post_review_authorized_next_work", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("post_review_runtime_manifest_plan_authorized", decision.get("runtime_artifact_manifest_plan_authorized"), True),
        _expect("post_review_runtime_manifest_materialization_blocked", decision.get("runtime_artifact_manifest_materialization_authorized"), False),
        _expect("post_review_runtime_execution_blocked", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("post_review_replay_blocked", decision.get("replay_execution_authorized"), False),
        _expect("post_review_training_blocked", decision.get("training_execution_authorized"), False),
        _expect("post_review_candidate_generation_blocked", decision.get("candidate_generation_authorized"), False),
        _expect("post_review_dp_modification_blocked", decision.get("dp_modification_authorized"), False),
        _expect("post_review_selector_promotion_blocked", decision.get("selector_promotion_authorized"), False),
        _expect("post_review_safety_claim_blocked", decision.get("safety_benefit_claim_authorized"), False),
        _expect("post_review_camp_over_dp_claim_blocked", decision.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("post_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("post_review_runtime_schema", review.get("runtime_schema_version"), RUNTIME_SCHEMA_VERSION),
        _expect("post_review_source_scope", review.get("source_scope"), SOURCE_SCOPE),
        _expect("post_review_executed_output_policy", review.get("executed_output_policy"), "dp_top1"),
        _expect("post_review_candidate_count", review.get("candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("post_review_static_only", analysis.get("static_only"), True),
        _expect("post_review_runtime_execution_false", analysis.get("runtime_execution"), False),
    ]
    checks.extend(
        _expect(f"post_review_blocked_{name}", blocked.get(name), False)
        for name in BLOCKED_ACTIONS
        if name in blocked
    )
    return checks


def _implementation_result_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("implementation_result_passed", payload.get("passed"), True),
        _expect("implementation_result_exit_zero", payload.get("exit"), 0),
        _expect("implementation_result_failure_class", payload.get("failure_class"), "None"),
        _expect("implementation_result_dp_head_fixed", payload.get("dp_head"), FIXED_DP_HEAD),
        _expect("implementation_result_authorized_work", payload.get("authorized_work"), IMPLEMENTATION_AUTHORIZED_WORK),
        _expect("implementation_result_training_not_executed", payload.get("training_executed"), False),
        _expect("implementation_result_replay_not_executed", payload.get("replay_executed"), False),
        _expect("implementation_result_candidate_generation_not_executed", payload.get("candidate_generation_executed"), False),
        _expect("implementation_result_dp_not_modified", payload.get("dp_modified"), False),
        _expect("implementation_result_promotion_not_executed", payload.get("promotion_executed"), False),
        _expect("implementation_result_deployment_not_executed", payload.get("deployment_executed"), False),
        _expect("implementation_result_safety_claim_forbidden", payload.get("safety_claim_authorized"), False),
        _expect("implementation_result_camp_over_dp_claim_forbidden", payload.get("camp_over_dp_top1_claim_authorized"), False),
    ]


def _runner_contract_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains("runner_runtime_schema_constant", text, "DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION"),
        _contains("runner_v14_runtime_schema", text, RUNTIME_SCHEMA_VERSION),
        _check(
            "runner_v13_runtime_schema_absent",
            "dp_camp_v13_default_off_shadow_selector_runtime_v1" not in text,
            "present" if "dp_camp_v13_default_off_shadow_selector_runtime_v1" in text else "absent",
            "absent",
        ),
        _contains("runner_source_scope_constant", text, "DEFAULT_OFF_SHADOW_SELECTOR_SOURCE_SCOPE"),
        _contains("runner_source_scope_value", text, SOURCE_SCOPE),
        _contains("runner_expected_k8", text, "DEFAULT_OFF_SHADOW_SELECTOR_EXPECTED_K = 8"),
        _contains("runner_shadow_artifact_entry", text, "def _shadow_artifact_entry"),
        _contains("runner_fail_closed", text, "def _mark_shadow_selector_fail_closed"),
        _contains("runner_forces_dp_top1", text, "selected_index = 0 if default_off_shadow_selector else baseline_selected_index"),
        _contains("runner_logs_dp_top1_policy", text, '"executed_output_policy": "dp_top1"'),
        _contains("runner_logs_selection_effect_false", text, '"selection_effect": False'),
        _contains("runner_logs_online_selector_change_false", text, '"online_selector_change": False'),
        _contains("runner_logs_score_expression", text, f'"score_expression": "{SCORE_EXPRESSION}"'),
    ]


def _audit_contract_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    current_pending = (
        f"current_v14_status={SOURCE_STATUS}" in eof
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof
    )
    current_complete = (
        f"current_v14_status={READY_STATUS}" in eof
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in eof
    )
    status_pending = (
        f"current_v14_status={SOURCE_STATUS}" in status_text
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text
    )
    status_complete = (
        f"current_v14_status={READY_STATUS}" in status_text
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in status_text
    )
    return [
        _check(
            "audit_latest_boundary_matches_manifest_plan_gate",
            current_pending or current_complete,
            {
                "status": _extract_line(eof, "current_v14_status="),
                "next": _extract_line(eof, "next_work_target="),
            },
            "pending plan-only gate or completed plan-ready gate",
        ),
        _check(
            "current_status_boundary_matches_manifest_plan_gate",
            status_pending or status_complete,
            {
                "pending": status_pending,
                "complete": status_complete,
            },
            "pending plan-only gate or completed plan-ready gate",
        ),
        _contains("audit_blocks_materialization", eof, "runtime_artifact_manifest_materialization_authorized=False"),
        _contains("audit_blocks_runtime_execution", eof, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_blocks_replay", eof, "replay_execution_authorized=False"),
        _contains("audit_blocks_training", eof, "training_execution_authorized=False"),
        _contains("audit_blocks_candidate_generation", eof, "candidate_generation_authorized=False"),
        _contains("audit_blocks_dp_modification", eof, "dp_modification_authorized=False"),
        _contains("audit_blocks_safety_claim", eof, "safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _artifact_summary(
    *,
    training_summary: dict[str, Any],
    atom_scales: dict[str, Any],
    weights_array: np.ndarray | None,
    source_hashes: dict[str, str],
    paths: dict[str, Path],
) -> dict[str, Any]:
    return {
        "training_type": training_summary.get("training_type"),
        "label_source": training_summary.get("label_source"),
        "reward_key": training_summary.get("reward_key"),
        "training_records": training_summary.get("num_records"),
        "contract_records": _dict(training_summary.get("dp_native_training_data_contract")).get("records"),
        "candidate_count": training_summary.get("num_candidates"),
        "atom_count": training_summary.get("num_atoms"),
        "atom_schema_version": training_summary.get("atom_schema_version"),
        "atom_names": list(atom_scales.get("atom_names") or []),
        "weights": [] if weights_array is None else weights_array.tolist(),
        "weights_sum": None if weights_array is None else float(np.sum(weights_array)),
        "artifacts": {
            "training_summary": {
                "path": str(paths["training_summary"]),
                "sha256": source_hashes.get("training_summary_sha256"),
            },
            "atom_scales": {
                "path": str(paths["atom_scales"]),
                "sha256": source_hashes.get("atom_scales_sha256"),
            },
            "static_weights": {
                "path": str(paths["static_weights_npy"]),
                "sha256": source_hashes.get("static_weights_npy_sha256"),
            },
        },
    }


def _runtime_manifest_plan(
    *,
    training_summary_json: Path,
    atom_scales_json: Path,
    static_weights_npy: Path,
    post_static_review_json: Path,
    implementation_result_json: Path,
    replay_runner_py: Path,
    planned_runtime_manifest_path: str,
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    return {
        "status": "plan_ready_no_runtime_manifest_materialized",
        "planned_runtime_manifest_path": planned_runtime_manifest_path,
        "runtime_schema_version": RUNTIME_SCHEMA_VERSION,
        "source_scope": SOURCE_SCOPE,
        "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
        "this_plan_is_runtime_manifest": False,
        "materialized_by_this_gate": False,
        "real_runtime_manifest_materialized": False,
        "default_off": True,
        "fail_closed": True,
        "selector_mode": "static",
        "executed_output_policy": "dp_top1",
        "selection_effect": False,
        "online_selector_change": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "required_candidate_count": EXPECTED_CANDIDATE_COUNT,
        "atom_count": EXPECTED_ATOM_COUNT,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "score_expression": SCORE_EXPRESSION,
        "required_runtime_entries": {
            "atom_scales": {
                "logical_name": "atom_scales",
                "path": str(atom_scales_json),
                "sha256": source_hashes.get("atom_scales_sha256"),
            },
            "static_weights": {
                "logical_name": "static_weights",
                "path": str(static_weights_npy),
                "sha256": source_hashes.get("static_weights_npy_sha256"),
            },
        },
        "required_evidence_entries": {
            "training_summary": {
                "path": str(training_summary_json),
                "sha256": source_hashes.get("training_summary_sha256"),
            },
            "post_static_review": {
                "path": str(post_static_review_json),
                "sha256": source_hashes.get("post_static_review_sha256"),
            },
            "implementation_result": {
                "path": str(implementation_result_json),
                "sha256": source_hashes.get("implementation_result_sha256"),
            },
            "replay_runner": {
                "path": str(replay_runner_py),
                "sha256": source_hashes.get("replay_runner_sha256"),
            },
        },
        "future_manifest_required_sha256_aliases": {
            "atom_scales": source_hashes.get("atom_scales_sha256"),
            str(atom_scales_json): source_hashes.get("atom_scales_sha256"),
            atom_scales_json.name: source_hashes.get("atom_scales_sha256"),
            "static_weights": source_hashes.get("static_weights_npy_sha256"),
            str(static_weights_npy): source_hashes.get("static_weights_npy_sha256"),
            static_weights_npy.name: source_hashes.get("static_weights_npy_sha256"),
        },
        "planned_runner_args": [
            "--camp_selector_mode static",
            f"--num_candidates {EXPECTED_CANDIDATE_COUNT}",
            "--camp_default_off_shadow_selector",
            f"--camp_atom_scales {atom_scales_json}",
            f"--camp_static_weights {static_weights_npy}",
            "--camp_shadow_artifact_manifest <future_runtime_manifest_json>",
            f"--camp_shadow_expected_atom_scales_sha256 {source_hashes.get('atom_scales_sha256')}",
            f"--camp_shadow_expected_static_weights_sha256 {source_hashes.get('static_weights_npy_sha256')}",
        ],
        "fail_closed_policy": (
            "If any runtime artifact path is missing, any sha256 differs, K != 8, "
            "the atom schema drifts, weights leave the nonnegative simplex, or "
            "the source scope/schema changes, the selector must fail closed and "
            "the executed trajectory remains DP Top-1."
        ),
    }


def _future_static_review_requirements() -> list[str]:
    return [
        "prove this output is a plan artifact, not a materialized runtime manifest",
        "prove the planned runtime manifest path does not exist before materialization",
        "prove future runtime entries use logical names atom_scales and static_weights",
        "prove static weight and atom scale sha256 values match the v14 training artifact",
        "prove the future manifest pins the v14 runtime schema and public simulator source scope",
        "prove default-off fail-closed behavior keeps executed output as DP Top-1",
        "prove affine scoring score_k(w)=a_k^T w over K=8 fixed DP candidates",
        "prove the 9 approved atom weights are finite, nonnegative, and sum to one",
        "prove no runtime execution, replay, candidate generation, DP modification, promotion, deployment, safety claim, or CAMP-over-DP claim is authorized",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "writing the future runtime manifest in this plan-only gate",
        "using this plan JSON as --camp_shadow_artifact_manifest",
        "running replay or runtime selection from this gate",
        "routing shadow_selected_index into the executed trajectory",
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
        "runtime_artifact_manifest_plan_ready": bool(passed),
        "runtime_artifact_manifest_static_contract_review_authorized": bool(passed),
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
    if "planned_runtime_manifest_not_preexisting" in failed:
        return "runtime_manifest_already_materialized_or_path_conflict"
    if any(name.startswith("post_review_") for name in failed):
        return "post_static_review_contract_failure"
    if any(name.startswith("training_") for name in failed):
        return "training_artifact_contract_failure"
    if any(name.startswith("audit_") or name.startswith("current_status_") for name in failed):
        return "v14_eof_contract_mismatch"
    return "runtime_artifact_manifest_plan_contract_failure"


def _load_json(path: Path, name: str) -> tuple[Any, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, _check(f"{name}_valid_json", False, type(exc).__name__, "valid JSON")
    return payload, _check(f"{name}_json_object", isinstance(payload, dict), type(payload).__name__, "dict")


def _load_weights(path: Path) -> tuple[np.ndarray | None, list[dict[str, Any]]]:
    if not path.is_file():
        return None, [_check("static_weights_npy_loaded", False, str(path), "loadable NPY")]
    try:
        loaded = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        return None, [_check("static_weights_npy_loaded", False, type(exc).__name__, "loadable NPY")]
    array = np.asarray(loaded, dtype=np.float64)
    return array, [
        _check("static_weights_npy_shape", array.shape == (EXPECTED_ATOM_COUNT,), list(array.shape), [EXPECTED_ATOM_COUNT]),
        _check("static_weights_npy_simplex", _simplex(array.tolist()), array.tolist(), "finite nonnegative simplex"),
    ]


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


def _float_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    parsed = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return []
        parsed.append(float(item))
    return parsed


def _simplex(value: Any) -> bool:
    parsed = _float_vector(value)
    return (
        len(parsed) == EXPECTED_ATOM_COUNT
        and all(math.isfinite(item) and item >= 0.0 for item in parsed)
        and math.isclose(sum(parsed), 1.0, rel_tol=0.0, abs_tol=1e-9)
    )


def _finite_positive_vector(value: Any, size: int) -> bool:
    parsed = _float_vector(value)
    return len(parsed) == size and all(math.isfinite(item) and item > 0.0 for item in parsed)


def _matches_array(weights: list[float], weights_array: np.ndarray | None) -> bool:
    if weights_array is None or len(weights) != EXPECTED_ATOM_COUNT:
        return False
    return bool(np.allclose(np.asarray(weights, dtype=np.float64), weights_array, rtol=0.0, atol=1e-12))


def _int_at_least(value: Any, threshold: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= threshold


def _finite_float_in_range(value: Any, lo: float, hi: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and lo <= float(value) <= hi
    )


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


def _latest_text_block(text: str) -> str:
    marker = "\n## "
    index = text.rfind(marker)
    return text[index + 1 :] if index >= 0 else text


def _extract_line(text: str, prefix: str) -> str | None:
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


if __name__ == "__main__":
    raise SystemExit(main())
