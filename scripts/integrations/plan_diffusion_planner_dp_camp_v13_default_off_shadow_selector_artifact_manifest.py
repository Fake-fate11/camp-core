#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_v1"
)
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
TRAINING_SCHEMA_VERSION = "dp_native_fallback_risk_static_camp_training_v1"
TRAINING_COMPLETE_STATUS = "dp_native_fallback_risk_static_camp_training_complete"
FALLBACK_MASTER_SCHEMA_VERSION = "dp_native_fallback_risk_fallback_master_config_v1"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
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
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
EXPECTED_ATOM_COUNT = len(APPROVED_ATOM_NAMES)

BLOCKED_ACTIONS = (
    "artifact_manifest_materialization_authorized",
    "default_off_shadow_selector_runtime_execution_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "production_selector_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for a future immutable artifact manifest that can "
            "wire existing v13 nonpromotion static CAMP weights and atom "
            "scales into the default-off DP-CAMP shadow selector. It does not "
            "materialize a runtime manifest, execute replay, train CAMP, "
            "generate candidates, modify DP, promote, deploy, or authorize "
            "safety/CAMP-over-DP claims."
        )
    )
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--atom_scales_json", type=Path, required=True)
    parser.add_argument("--static_weights_npy", type=Path, required=True)
    parser.add_argument("--static_weights_json", type=Path, required=True)
    parser.add_argument("--fallback_master_config_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--user_camp_training_authorized",
        action="store_true",
        help=(
            "Record the user's standing CAMP training authorization without "
            "executing training in this plan-only gate."
        ),
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_default_off_shadow_selector_artifact_manifest_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        training_summary_json=args.training_summary_json,
        atom_scales_json=args.atom_scales_json,
        static_weights_npy=args.static_weights_npy,
        static_weights_json=args.static_weights_json,
        fallback_master_config_json=args.fallback_master_config_json,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        user_camp_training_authorized=args.user_camp_training_authorized,
        label=args.label,
        enabled=args.enable_v13_default_off_shadow_selector_artifact_manifest_plan,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_report(
    *,
    training_summary_json: Path,
    atom_scales_json: Path,
    static_weights_npy: Path,
    static_weights_json: Path,
    fallback_master_config_json: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    user_camp_training_authorized: bool = False,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        label=label,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        user_camp_training_authorized=user_camp_training_authorized,
    )
    if not enabled:
        return report

    paths = {
        "training_summary": training_summary_json,
        "atom_scales": atom_scales_json,
        "static_weights_npy": static_weights_npy,
        "static_weights_json": static_weights_json,
        "fallback_master_config": fallback_master_config_json,
        "v13_audit": v13_audit_md,
    }
    checks: list[dict[str, Any]] = [
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
    ]
    payloads: dict[str, Any] = {}
    texts: dict[str, str] = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "existing file"))
        if not path.is_file():
            continue
        report["source_hashes"][f"{name}_sha256"] = _sha256(path)
        if path.suffix == ".json":
            loaded, json_check = _load_json(path, name)
            payloads[name] = loaded
            checks.append(json_check)
        elif path.suffix in {".md", ".txt"}:
            texts[name] = path.read_text(encoding="utf-8")

    weights_array, weight_checks = _load_weights_array(static_weights_npy)
    checks.extend(weight_checks)
    training_summary = _dict(payloads.get("training_summary"))
    atom_scales = _dict(payloads.get("atom_scales"))
    static_weights = _dict(payloads.get("static_weights_json"))
    fallback_master = _dict(payloads.get("fallback_master_config"))
    checks.extend(
        _training_summary_checks(
            training_summary=training_summary,
            hashes=report["source_hashes"],
        )
    )
    checks.extend(_atom_scales_checks(atom_scales))
    checks.extend(_static_weights_json_checks(static_weights, weights_array))
    checks.extend(_fallback_master_config_checks(fallback_master))
    checks.extend(_audit_boundary_checks(texts.get("v13_audit", "")))

    passed = all(check["passed"] for check in checks)
    report["artifact_summary"] = _artifact_summary(
        training_summary=training_summary,
        atom_scales=atom_scales,
        static_weights=static_weights,
        weights_array=weights_array,
        hashes=report["source_hashes"],
    )
    report["artifact_manifest_plan"] = _artifact_manifest_plan(
        atom_scales_json=atom_scales_json,
        static_weights_npy=static_weights_npy,
        static_weights_json=static_weights_json,
        training_summary_json=training_summary_json,
        fallback_master_config_json=fallback_master_config_json,
        hashes=report["source_hashes"],
    )
    report["static_review_requirements"] = _static_review_requirements()
    report["forbidden_materialization_paths"] = _forbidden_materialization_paths()
    report["plan_checks"] = checks
    report["final_decision"] = _decision(
        passed,
        checks,
        user_camp_training_authorized=user_camp_training_authorized,
    )
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report.get("artifact_manifest_plan", {})
    artifacts = report.get("artifact_summary", {}).get("artifacts", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Artifact Manifest Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Manifest materialization authorized: `{decision['artifact_manifest_materialization_authorized']}`",
        f"- Shadow runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Training executed: `{decision['training_executed']}`",
        f"- User training authorization recorded: `{decision['user_camp_training_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Planned Runtime Manifest",
        "",
        f"- Status: `{plan.get('status')}`",
        f"- Runtime schema: `{plan.get('runtime_manifest_schema_version')}`",
        f"- Materialized by this gate: `{plan.get('materialized_by_this_gate')}`",
        f"- Selector mode: `{plan.get('selector_mode')}`",
        f"- Candidate count: `{plan.get('candidate_count')}`",
        f"- Score expression: `{plan.get('score_expression')}`",
        "",
        "## Artifact Entries",
        "",
    ]
    for name, artifact in artifacts.items():
        lines.append(
            f"- `{name}` path=`{artifact.get('path')}` sha256=`{artifact.get('sha256')}`"
        )
    lines.extend(["", "## Planned Runner Args", ""])
    for item in plan.get("planned_runner_args", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Static Review Requirements", ""])
    for item in report.get("static_review_requirements", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It validates existing offline nonpromotion "
            "static CAMP artifacts and describes the future immutable runtime "
            "manifest shape. It does not materialize that manifest, execute "
            "replay, train CAMP, generate candidates, modify Diffusion Planner, "
            "promote atoms or selectors, deploy, or authorize safety/CAMP-over-DP "
            "claims.",
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
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _empty_report(
    *,
    enabled: bool,
    label: str | None,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    user_camp_training_authorized: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "name": "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan",
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "plan_only": True,
            "artifact_manifest_materialized": False,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "dp_modification_execution": False,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "user_camp_training_authorized": bool(user_camp_training_authorized),
            "math_boundary": (
                "CAMP remains a fixed-DP-candidate reranker. The future "
                "default-off shadow selector may only read current-tick finite "
                "candidate atom rows and apply affine scores score_k(w)=a_k^T w "
                "with simplex weights. It may log shadow_selected_index, but "
                "the executed trajectory remains DP Top-1 during this shadow "
                "phase."
            ),
        },
        "source_hashes": {},
        "artifact_summary": {},
        "artifact_manifest_plan": {},
        "static_review_requirements": [],
        "forbidden_materialization_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "artifact_manifest_plan_ready": False,
            "artifact_manifest_static_contract_review_authorized": False,
            "artifact_manifest_materialization_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "production_selector_change_authorized": False,
            "training_authorization_changed_by_plan": False,
            "user_camp_training_authorized": bool(user_camp_training_authorized),
            "training_execution_authorized_by_user": bool(user_camp_training_authorized),
            "training_task_may_start_without_extra_user_authorization": bool(
                user_camp_training_authorized
            ),
            "training_executed": False,
            "failed_checks": [],
        },
    }


def _training_summary_checks(
    *,
    training_summary: dict[str, Any],
    hashes: dict[str, str],
) -> list[dict[str, Any]]:
    decision = _dict(training_summary.get("final_decision"))
    analysis = _dict(training_summary.get("analysis"))
    training = _dict(training_summary.get("training"))
    output_artifacts = _dict(training_summary.get("output_artifacts"))
    return [
        _expect("training_summary_schema_version", training_summary.get("schema_version"), TRAINING_SCHEMA_VERSION),
        _expect("training_summary_status_complete", decision.get("status"), TRAINING_COMPLETE_STATUS),
        _expect("training_summary_passed", decision.get("passed"), True),
        _expect("training_summary_errors_empty", decision.get("errors"), []),
        _expect("training_summary_training_executed", decision.get("training_executed"), True),
        _expect("training_summary_fixed_dp_candidate_reranking_only", decision.get("fixed_dp_candidate_reranking_only"), True),
        _expect("training_summary_fallback_only_training", decision.get("fallback_only_training"), True),
        _expect("training_summary_replay_not_authorized", decision.get("replay_execution_authorized"), False),
        _expect("training_summary_candidate_generation_not_authorized", decision.get("candidate_generation_authorized"), False),
        _expect("training_summary_formal_seeds_forbidden", decision.get("formal_seeds_11_12_13_authorized"), False),
        _expect("training_summary_dp_modification_forbidden", decision.get("dp_modification_authorized"), False),
        _expect("training_summary_selector_promotion_forbidden", decision.get("selector_promotion_authorized"), False),
        _expect("training_summary_atom_promotion_forbidden", decision.get("atom_promotion_authorized"), False),
        _expect("training_summary_safety_claim_forbidden", decision.get("safety_benefit_claim_authorized"), False),
        _expect("training_summary_camp_over_dp_claim_forbidden", decision.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("training_analysis_replay_not_executed", analysis.get("replay_executed"), False),
        _expect("training_analysis_candidate_generation_not_executed", analysis.get("candidate_generation_executed"), False),
        _expect("training_analysis_dp_not_modified", analysis.get("diffusion_planner_modified"), False),
        _expect("training_analysis_trajectory_rewrite_not_executed", analysis.get("trajectory_rewrite_executed"), False),
        _expect("training_score_expression", training.get("score_expression"), SCORE_EXPRESSION),
        _expect("training_num_candidates", training.get("num_candidates"), EXPECTED_CANDIDATE_COUNT),
        _expect("training_num_atoms", training.get("num_atoms"), EXPECTED_ATOM_COUNT),
        _expect("training_atom_schema_version", training.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("training_atom_names", tuple(training.get("atom_names") or ()), APPROVED_ATOM_NAMES),
        _check("training_records_positive", _positive_int(training.get("training_records")), training.get("training_records"), "positive int"),
        _check("training_validation_records_positive", _positive_int(training.get("validation_records")), training.get("validation_records"), "positive int"),
        _check("training_weights_sum_simplex", _is_close(training.get("weights_sum"), 1.0), training.get("weights_sum"), 1.0),
        _check("training_weights_min_nonnegative", _finite_float_at_least(training.get("weights_min"), 0.0), training.get("weights_min"), "finite >= 0"),
        _expect(
            "training_output_weights_npy_sha256",
            output_artifacts.get("weights_npy_sha256"),
            hashes.get("static_weights_npy_sha256"),
        ),
        _expect(
            "training_output_weights_json_sha256",
            output_artifacts.get("weights_json_sha256"),
            hashes.get("static_weights_json_sha256"),
        ),
        _expect(
            "training_output_atom_scales_json_sha256",
            output_artifacts.get("atom_scales_json_sha256"),
            hashes.get("atom_scales_sha256"),
        ),
    ]


def _atom_scales_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    scales = payload.get("scales")
    valid_scales = _finite_positive_vector(scales, EXPECTED_ATOM_COUNT)
    return [
        _expect("atom_scales_schema_version", payload.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("atom_scales_atom_names", tuple(payload.get("atom_names") or ()), APPROVED_ATOM_NAMES),
        _check("atom_scales_positive_vector", valid_scales, scales, f"{EXPECTED_ATOM_COUNT} positive finite values"),
    ]


def _static_weights_json_checks(
    payload: dict[str, Any],
    weights_array: np.ndarray | None,
) -> list[dict[str, Any]]:
    weights = _float_vector(payload.get("weights"))
    return [
        _expect("static_weights_schema_version", payload.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("static_weights_atom_names", tuple(payload.get("atom_names") or ()), APPROVED_ATOM_NAMES),
        _expect("static_weights_score_expression", payload.get("score_expression"), SCORE_EXPRESSION),
        _expect("static_weights_fallback_only", payload.get("fallback_only"), True),
        _expect("static_weights_selector_promotion_not_executed", payload.get("selector_promotion_executed"), False),
        _check("static_weights_json_simplex", _simplex(weights), payload.get("weights"), "14 finite nonnegative weights summing to 1"),
        _check("static_weights_json_matches_npy", _matches_array(weights, weights_array), payload.get("weights"), "same values as NPY"),
    ]


def _fallback_master_config_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {
        "fallback_only": True,
        "feasible_branch_records_allowed": False,
        "all_infeasible_records_added_to_feasible_training": False,
        "all_infeasible_records_relabelled_feasible": False,
        "hard_feasibility_relaxation_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "atoms_fixed_nonnegative": True,
        "fallback_label_is_deployed_atom": False,
        "margins_nonnegative": True,
        "simplex_cvar_l2_convex": True,
    }
    checks = [
        _expect("fallback_master_schema_version", payload.get("schema_version"), FALLBACK_MASTER_SCHEMA_VERSION),
        _expect("fallback_master_score_expression", payload.get("score_expression"), SCORE_EXPRESSION),
    ]
    checks.extend(
        _expect(f"fallback_master_{field}", payload.get(field), expected_value)
        for field, expected_value in expected.items()
    )
    return checks


def _audit_boundary_checks(text: str) -> list[dict[str, Any]]:
    current_boundary = _current_v13_boundary(text)
    return [
        _contains(
            "audit_current_scope_authorizes_manifest_plan_only",
            current_boundary,
            "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_only",
        ),
        _contains(
            "audit_artifact_manifest_plan_authorized",
            current_boundary,
            "artifact_manifest_plan_authorized=True",
        ),
        _contains(
            "audit_manifest_materialization_blocked",
            current_boundary,
            "artifact_manifest_materialization_authorized=False",
        ),
        _contains(
            "audit_runtime_shadow_selector_blocked",
            current_boundary,
            "runtime_shadow_selector_execution_authorized=False",
        ),
        _contains(
            "audit_candidate_generation_blocked",
            current_boundary,
            "candidate_generation_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_dp_modification_blocked",
            current_boundary,
            "dp_modification_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_training_authorization_preserved",
            current_boundary,
            "current_v13_training_authorized_by_user=True",
        ),
    ]


def _current_v13_boundary(audit: str) -> str:
    marker = "\n## Current V13 "
    index = audit.rfind(marker)
    return audit[index + 1 :] if index >= 0 else audit


def _artifact_summary(
    *,
    training_summary: dict[str, Any],
    atom_scales: dict[str, Any],
    static_weights: dict[str, Any],
    weights_array: np.ndarray | None,
    hashes: dict[str, str],
) -> dict[str, Any]:
    training = _dict(training_summary.get("training"))
    output_artifacts = _dict(training_summary.get("output_artifacts"))
    weights = _float_vector(static_weights.get("weights"))
    return {
        "training": {
            "training_records": training.get("training_records"),
            "validation_records": training.get("validation_records"),
            "num_candidates": training.get("num_candidates"),
            "num_atoms": training.get("num_atoms"),
            "atom_schema_version": training.get("atom_schema_version"),
            "score_expression": training.get("score_expression"),
        },
        "artifacts": {
            "atom_scales": {
                "logical_name": "atom_scales",
                "path": output_artifacts.get("atom_scales_json"),
                "sha256": hashes.get("atom_scales_sha256"),
                "atom_schema_version": atom_scales.get("atom_schema_version"),
                "atom_count": len(atom_scales.get("atom_names") or ()),
            },
            "static_weights": {
                "logical_name": "static_weights",
                "path": output_artifacts.get("weights_npy"),
                "sha256": hashes.get("static_weights_npy_sha256"),
                "atom_schema_version": static_weights.get("atom_schema_version"),
                "weight_count": len(weights),
                "weights_sum": float(np.sum(weights)) if weights else None,
                "npy_shape": list(weights_array.shape) if weights_array is not None else None,
            },
            "static_weights_json": {
                "logical_name": "static_weights_json_evidence",
                "path": output_artifacts.get("weights_json"),
                "sha256": hashes.get("static_weights_json_sha256"),
            },
            "training_summary": {
                "logical_name": "training_summary_evidence",
                "path": output_artifacts.get("training_summary_json"),
                "sha256": hashes.get("training_summary_sha256"),
            },
            "fallback_master_config": {
                "logical_name": "fallback_master_config_evidence",
                "path": None,
                "sha256": hashes.get("fallback_master_config_sha256"),
            },
        },
    }


def _artifact_manifest_plan(
    *,
    atom_scales_json: Path,
    static_weights_npy: Path,
    static_weights_json: Path,
    training_summary_json: Path,
    fallback_master_config_json: Path,
    hashes: dict[str, str],
) -> dict[str, Any]:
    return {
        "status": "plan_ready_no_runtime_manifest_materialized",
        "runtime_manifest_schema_version": RUNTIME_MANIFEST_SCHEMA_VERSION,
        "materialized_by_this_gate": False,
        "selector_mode": "static",
        "candidate_count": EXPECTED_CANDIDATE_COUNT,
        "atom_count": EXPECTED_ATOM_COUNT,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "score_expression": SCORE_EXPRESSION,
        "runner_manifest_lookup_contract": (
            "runtime manifest must expose sha256 values by logical names "
            "atom_scales and static_weights, with optional basename/path aliases"
        ),
        "required_runtime_entries": {
            "atom_scales": {
                "logical_name": "atom_scales",
                "path": str(atom_scales_json),
                "sha256": hashes.get("atom_scales_sha256"),
            },
            "static_weights": {
                "logical_name": "static_weights",
                "path": str(static_weights_npy),
                "sha256": hashes.get("static_weights_npy_sha256"),
            },
        },
        "required_evidence_entries": {
            "static_weights_json": {
                "path": str(static_weights_json),
                "sha256": hashes.get("static_weights_json_sha256"),
            },
            "training_summary": {
                "path": str(training_summary_json),
                "sha256": hashes.get("training_summary_sha256"),
            },
            "fallback_master_config": {
                "path": str(fallback_master_config_json),
                "sha256": hashes.get("fallback_master_config_sha256"),
            },
        },
        "planned_runner_args": [
            "--camp_selector_mode static",
            f"--num_candidates {EXPECTED_CANDIDATE_COUNT}",
            "--camp_default_off_shadow_selector",
            f"--camp_atom_scales {atom_scales_json}",
            f"--camp_static_weights {static_weights_npy}",
            "--camp_shadow_artifact_manifest <future_runtime_manifest_json>",
            f"--camp_shadow_expected_atom_scales_sha256 {hashes.get('atom_scales_sha256')}",
            f"--camp_shadow_expected_static_weights_sha256 {hashes.get('static_weights_npy_sha256')}",
        ],
        "future_manifest_required_sha256_aliases": {
            "atom_scales": hashes.get("atom_scales_sha256"),
            str(atom_scales_json): hashes.get("atom_scales_sha256"),
            atom_scales_json.name: hashes.get("atom_scales_sha256"),
            "static_weights": hashes.get("static_weights_npy_sha256"),
            str(static_weights_npy): hashes.get("static_weights_npy_sha256"),
            static_weights_npy.name: hashes.get("static_weights_npy_sha256"),
        },
        "fail_closed_policy": (
            "If any path is missing, any hash differs, K != 8, atom schema "
            "drifts, weights leave the simplex, scores are nonfinite, or "
            "source/audit boundaries drift, the default-off shadow selector "
            "must execute DP Top-1 and record no shadow selection."
        ),
    }


def _static_review_requirements() -> list[str]:
    return [
        "prove this output is a plan and not a runtime shadow artifact manifest",
        "prove the future manifest uses logical names atom_scales and static_weights",
        "prove artifact paths and sha256 values match the v13 offline nonpromotion training outputs",
        "prove the planned runner invocation remains default-off and static mode only",
        "prove scoring remains affine score_k(w)=a_k^T w over fixed K=8 DP candidates",
        "prove weights are finite, nonnegative, length 14, and sum to one",
        "prove atom scales are finite, positive, length 14, and use dp_camp_v10_14d",
        "prove no runtime execution, replay, candidate generation, DP modification, promotion, deployment, or safety claim is authorized",
    ]


def _forbidden_materialization_paths() -> list[str]:
    return [
        "writing the future runtime manifest in this gate",
        "using this plan JSON as --camp_shadow_artifact_manifest",
        "running replay with --camp_default_off_shadow_selector",
        "routing shadow_selected_index into the executed trajectory",
        "generating, modifying, blending, guiding, or postprocessing trajectories",
        "modifying, retraining, or tuning TiERIV Diffusion Planner",
        "promoting atoms or selector weights",
        "claiming deployment readiness, safety benefit, or CAMP superiority",
    ]


def _decision(
    passed: bool,
    checks: list[dict[str, Any]],
    *,
    user_camp_training_authorized: bool,
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "artifact_manifest_plan_ready": bool(passed),
        "artifact_manifest_static_contract_review_authorized": bool(passed),
        "artifact_manifest_materialization_authorized": False,
        "default_off_shadow_selector_runtime_execution_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "production_selector_change_authorized": False,
        "training_authorization_changed_by_plan": False,
        "user_camp_training_authorized": bool(user_camp_training_authorized),
        "training_execution_authorized_by_user": bool(user_camp_training_authorized),
        "training_task_may_start_without_extra_user_authorization": bool(user_camp_training_authorized),
        "training_executed": False,
        "failed_checks": failed,
    }


def _load_json(path: Path, name: str) -> tuple[Any, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, _check(f"{name}_valid_json", False, type(exc).__name__, "valid JSON")
    return payload, _check(f"{name}_json_object", isinstance(payload, dict), type(payload).__name__, "dict")


def _load_weights_array(path: Path) -> tuple[np.ndarray | None, list[dict[str, Any]]]:
    if not path.is_file():
        return None, [
            _check("static_weights_npy_loaded", False, str(path), "existing NPY file")
        ]
    try:
        loaded = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        return None, [
            _check("static_weights_npy_loaded", False, type(exc).__name__, "loadable NPY")
        ]
    array = np.asarray(loaded, dtype=np.float64)
    checks = [
        _check("static_weights_npy_shape", array.shape == (EXPECTED_ATOM_COUNT,), list(array.shape), [EXPECTED_ATOM_COUNT]),
        _check("static_weights_npy_simplex", _simplex(array.tolist()), array.tolist(), "14 finite nonnegative weights summing to 1"),
    ]
    return array, checks


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


def _finite_positive_vector(value: Any, size: int) -> bool:
    parsed = _float_vector(value)
    return len(parsed) == size and all(math.isfinite(item) and item > 0.0 for item in parsed)


def _simplex(value: Any) -> bool:
    parsed = _float_vector(value)
    return (
        len(parsed) == EXPECTED_ATOM_COUNT
        and all(math.isfinite(item) and item >= 0.0 for item in parsed)
        and math.isclose(sum(parsed), 1.0, rel_tol=0.0, abs_tol=1e-9)
    )


def _matches_array(weights: list[float], weights_array: np.ndarray | None) -> bool:
    if weights_array is None or len(weights) != EXPECTED_ATOM_COUNT:
        return False
    return bool(np.allclose(np.asarray(weights, dtype=np.float64), weights_array, rtol=0.0, atol=1e-12))


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _finite_float_at_least(value: Any, threshold: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) >= threshold
    )


def _is_close(value: Any, expected: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isclose(float(value), expected, rel_tol=0.0, abs_tol=1e-9)
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


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


if __name__ == "__main__":
    raise SystemExit(main())
