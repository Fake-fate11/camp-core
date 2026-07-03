#!/usr/bin/env python3
"""Read-only v14 runtime promotion evidence-package preflight.

This gate packages immutable evidence for the default-off runtime shadow
selector path. It only reads existing artifacts and checks their hashes and
contracts. It does not promote, deploy, train, replay, generate candidates,
modify Diffusion Planner, change a selector, or make safety/CAMP-over-DP
claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_preflight_v1"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_promotion_decision_plan_ready"
)
SOURCE_PLAN_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_promotion_evidence_package_preflight_only"
)
SOURCE_RESULT_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_replay_result_review_passed"
)
SOURCE_DELTA_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_shadow_vs_top1_delta_review_passed"
)
SOURCE_RUNTIME_MANIFEST_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
)
SOURCE_TRAINING_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_training_artifact_"
    "static_contract_review_passed"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_static_review_only"
)
PROMOTION_PLAN_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_plan_only_after_explicit_user_authorization"
)

DEFAULT_EXPECTED_COUNTS = {
    "selection_log_count": 32,
    "validation_summary_count": 32,
    "replay_summary_count": 32,
    "records": 3200,
    "default_off_selector_records": 3200,
    "artifact_contract_ready_records": 3200,
    "shadow_selected_index_nonzero_records": 2832,
    "shadow_selected_index_differs_from_executed_index_records": 2832,
    "executed_top1_records": 3200,
    "selected_index_matches_executed_index_records": 3200,
    "feasible_records": 2914,
    "used_fallback_records": 286,
    "selection_score_better_records": 2832,
    "selection_score_tie_records": 368,
    "selection_score_worse_records": 0,
    "selection_score_uncomparable_records": 0,
    "shadow_diff_selection_score_better_records": 2832,
    "shadow_diff_selection_score_worse_records": 0,
    "training_records": 2914,
    "dropped_records_without_feasible_candidate": 286,
    "num_candidates": 8,
    "num_atoms": 9,
}

BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "training_authorized",
    "training_execution_authorized",
    "candidate_generation_authorized",
    "replay_execution_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
)

SOURCE_FILE_ROLES = {
    "runtime_promotion_decision_plan": "source runtime promotion-decision plan",
    "runtime_result_review": "source runtime shadow replay result review",
    "shadow_vs_top1_delta_review": "source read-only shadow-vs-Top1 delta review",
    "runtime_manifest": "source default-off runtime artifact manifest",
    "training_artifact_static_review": "source training artifact static review",
    "training_summary": "source training execution summary",
    "offline_weights_npy": "source nonnegative simplex weights",
    "atom_scales_json": "source approved atom scale metadata",
    "runtime_shadow_execution_sha256s": "source runtime shadow execution hashes",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime_promotion_decision_plan_json", type=Path, required=True)
    parser.add_argument("--runtime_result_review_json", type=Path, required=True)
    parser.add_argument("--shadow_vs_top1_delta_review_json", type=Path, required=True)
    parser.add_argument("--runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--training_artifact_static_review_json", type=Path, required=True)
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--offline_weights_npy", type=Path, required=True)
    parser.add_argument("--atom_scales_json", type=Path, required=True)
    parser.add_argument("--runtime_shadow_execution_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    for name, default in DEFAULT_EXPECTED_COUNTS.items():
        parser.add_argument(f"--expected_{name}", type=int, default=default)
    parser.add_argument(
        "--enable_v14_runtime_promotion_evidence_package_preflight",
        action="store_true",
        help="Explicit opt-in for this read-only evidence-package preflight.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_promotion_decision_plan_json=args.runtime_promotion_decision_plan_json,
        runtime_result_review_json=args.runtime_result_review_json,
        shadow_vs_top1_delta_review_json=args.shadow_vs_top1_delta_review_json,
        runtime_manifest_json=args.runtime_manifest_json,
        training_artifact_static_review_json=args.training_artifact_static_review_json,
        training_summary_json=args.training_summary_json,
        offline_weights_npy=args.offline_weights_npy,
        atom_scales_json=args.atom_scales_json,
        runtime_shadow_execution_sha256s=args.runtime_shadow_execution_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_runtime_promotion_evidence_package_preflight,
        expected_counts={
            name: getattr(args, f"expected_{name}")
            for name in DEFAULT_EXPECTED_COUNTS
        },
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_promotion_decision_plan_json: Path,
    runtime_result_review_json: Path,
    shadow_vs_top1_delta_review_json: Path,
    runtime_manifest_json: Path,
    training_artifact_static_review_json: Path,
    training_summary_json: Path,
    offline_weights_npy: Path,
    atom_scales_json: Path,
    runtime_shadow_execution_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
    expected_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    expected = dict(DEFAULT_EXPECTED_COUNTS)
    if expected_counts:
        expected.update(expected_counts)

    source_paths = {
        "runtime_promotion_decision_plan": runtime_promotion_decision_plan_json,
        "runtime_result_review": runtime_result_review_json,
        "shadow_vs_top1_delta_review": shadow_vs_top1_delta_review_json,
        "runtime_manifest": runtime_manifest_json,
        "training_artifact_static_review": training_artifact_static_review_json,
        "training_summary": training_summary_json,
        "offline_weights_npy": offline_weights_npy,
        "atom_scales_json": atom_scales_json,
        "runtime_shadow_execution_sha256s": runtime_shadow_execution_sha256s,
    }
    source_hashes = {
        name: _sha256(path) for name, path in source_paths.items() if path.is_file()
    }
    promotion_plan = _read_json_dict(runtime_promotion_decision_plan_json)
    result_review = _read_json_dict(runtime_result_review_json)
    delta_review = _read_json_dict(shadow_vs_top1_delta_review_json)
    runtime_manifest = _read_json_dict(runtime_manifest_json)
    training_review = _read_json_dict(training_artifact_static_review_json)
    training_summary = _read_json_dict(training_summary_json)
    atom_scales = _read_json_dict(atom_scales_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)

    source_summary = _source_summary(
        promotion_plan,
        result_review,
        delta_review,
        runtime_manifest,
        training_review,
        training_summary,
    )
    checks = [
        _expect("preflight_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _check("v14_audit_md_exists", v14_audit_md.is_file(), str(v14_audit_md), "file"),
        _check(
            "current_status_md_exists",
            current_status_md.is_file(),
            str(current_status_md),
            "file",
        ),
    ]
    for name, path in source_paths.items():
        checks.extend(_artifact_file_checks(name, path))
    checks.extend(_promotion_plan_checks(promotion_plan, source_hashes, expected))
    checks.extend(_result_review_checks(result_review, expected))
    checks.extend(_delta_review_checks(delta_review, expected))
    checks.extend(_runtime_manifest_checks(runtime_manifest, source_hashes, expected))
    checks.extend(_training_review_checks(training_review, expected))
    checks.extend(_training_summary_checks(training_summary, expected))
    checks.extend(_atom_scale_checks(atom_scales, expected))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "preflight_only": True,
            "runtime_promotion_decision_plan_json": str(
                runtime_promotion_decision_plan_json.resolve()
            ),
            "runtime_result_review_json": str(runtime_result_review_json.resolve()),
            "shadow_vs_top1_delta_review_json": str(
                shadow_vs_top1_delta_review_json.resolve()
            ),
            "runtime_manifest_json": str(runtime_manifest_json.resolve()),
            "training_artifact_static_review_json": str(
                training_artifact_static_review_json.resolve()
            ),
            "training_summary_json": str(training_summary_json.resolve()),
            "offline_weights_npy": str(offline_weights_npy.resolve()),
            "atom_scales_json": str(atom_scales_json.resolve()),
            "runtime_shadow_execution_sha256s": str(
                runtime_shadow_execution_sha256s.resolve()
            ),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "promotion_executed": False,
            "deployment_executed": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "dp_modification": False,
            "safety_or_camp_over_dp_claim": False,
            "math_boundary": (
                "DP remains a fixed black-box candidate trajectory generator. "
                "CAMP may only shadow-rerank/select the current tick fixed "
                "finite DP candidate tensor by affine score_k(w)=a_k^T w over "
                "approved atoms with nonnegative simplex weights. This preflight "
                "does not authorize selector promotion, atom promotion, "
                "deployment, online selector changes, trajectory changes, or "
                "safety/CAMP-over-DP claims."
            ),
        },
        "source_hashes": source_hashes,
        "artifact_manifest": _artifact_manifest(source_paths, source_hashes),
        "source_summary": source_summary,
        "static_integration_contract": _static_integration_contract(),
        "future_review_requirements": _future_review_requirements(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "preflight_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_promotion_evidence_package_preflight.json", report)
    (output_dir / "runtime_promotion_evidence_package_preflight.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    lines = [
        "# V14 Runtime Promotion Evidence-Package Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Evidence-package static review authorized: `{decision['evidence_package_static_review_authorized']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP-Top1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Source Summary",
        "",
        f"- Promotion plan status: `{source['promotion_plan_status']}`",
        f"- Runtime result-review status: `{source['runtime_result_review_status']}`",
        f"- Shadow-vs-Top1 delta status: `{source['shadow_vs_top1_delta_status']}`",
        f"- Runtime manifest schema: `{source['runtime_manifest_schema_version']}`",
        f"- Training-review status: `{source['training_review_status']}`",
        f"- Selection logs / records: `{source['selection_log_count']}` / `{source['records']}`",
        f"- Executed DP Top-1 / shadow non-Top-1 records: `{source['executed_top1_records']}` / `{source['shadow_selected_index_nonzero_records']}`",
        f"- Feasible / fallback records: `{source['feasible_records']}` / `{source['used_fallback_records']}`",
        f"- Static masked objective better/tie/worse/uncomparable: `{source['selection_score_better_records']}` / `{source['selection_score_tie_records']}` / `{source['selection_score_worse_records']}` / `{source['selection_score_uncomparable_records']}`",
        f"- Training records / dropped all-infeasible: `{source['training_records']}` / `{source['dropped_records_without_feasible_candidate']}`",
        f"- Candidates / atoms: `{source['num_candidates']}` / `{source['num_atoms']}`",
        f"- Score expression: `{source['score_expression']}`",
        "",
        "## Artifact Manifest",
        "",
        "| Artifact | SHA-256 | Role |",
        "| --- | --- | --- |",
    ]
    for item in report["artifact_manifest"]:
        lines.append(f"| `{item['name']}` | `{item['sha256']}` | `{item['role']}` |")
    lines.extend(
        [
            "",
            "## Static Integration Contract",
            "",
            report["static_integration_contract"]["summary"],
            "",
            "## Future Review Requirements",
            "",
        ]
    )
    for item in report["future_review_requirements"]:
        lines.append(f"- `{item['name']}`: `{item['status']}`")
    lines.extend(
        [
            "",
            "This preflight is read-only. It does not promote atoms or selectors, "
            "deploy a checkpoint, train CAMP, run replay, generate candidates, "
            "modify DP, change online selection, or authorize safety/CAMP-over-DP "
            "claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["preflight_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_summary(
    promotion_plan: dict[str, Any],
    result_review: dict[str, Any],
    delta_review: dict[str, Any],
    runtime_manifest: dict[str, Any],
    training_review: dict[str, Any],
    training_summary: dict[str, Any],
) -> dict[str, Any]:
    plan_decision = _dict(promotion_plan.get("final_decision"))
    result_decision = _dict(result_review.get("final_decision"))
    result_execution = _dict(result_review.get("execution"))
    result_records = _dict(result_review.get("records"))
    delta_decision = _dict(delta_review.get("final_decision"))
    delta_records = _dict(delta_review.get("records"))
    selection_delta = _dict(delta_records.get("selection_score_comparison"))
    training_decision = _dict(training_review.get("final_decision"))
    training_artifact = _dict(training_review.get("artifact_review"))
    return {
        "promotion_plan_status": plan_decision.get("status"),
        "promotion_plan_passed": plan_decision.get("passed"),
        "promotion_plan_authorized_next_work": plan_decision.get("authorized_next_work"),
        "promotion_plan_recommendation": plan_decision.get("recommendation"),
        "runtime_result_review_status": result_decision.get("status"),
        "runtime_result_review_passed": result_decision.get("passed"),
        "shadow_vs_top1_delta_status": delta_decision.get("status"),
        "shadow_vs_top1_delta_passed": delta_decision.get("passed"),
        "runtime_manifest_schema_version": runtime_manifest.get("schema_version"),
        "runtime_manifest_artifacts": sorted(_dict(runtime_manifest.get("artifacts")).keys()),
        "training_review_status": training_decision.get("status"),
        "training_review_passed": training_decision.get("passed"),
        "selection_log_count": result_execution.get("selection_log_count"),
        "validation_summary_count": result_execution.get("validation_summary_count"),
        "replay_summary_count": result_execution.get("replay_summary_count"),
        "records": result_records.get("record_count"),
        "default_off_selector_records": result_records.get("default_off_selector_records"),
        "artifact_contract_ready_records": result_records.get("artifact_contract_ready_records"),
        "executed_top1_records": result_records.get("executed_top1_records"),
        "selected_index_matches_executed_index_records": result_records.get(
            "selected_index_matches_executed_index_records"
        ),
        "shadow_selected_index_nonzero_records": result_records.get(
            "shadow_selected_index_nonzero_records"
        ),
        "shadow_selected_index_differs_from_executed_index_records": result_records.get(
            "shadow_selected_index_differs_from_executed_index_records"
        ),
        "feasible_records": result_records.get("feasible_records"),
        "used_fallback_records": result_records.get("used_fallback_records"),
        "selection_score_better_records": selection_delta.get("better_records"),
        "selection_score_tie_records": selection_delta.get("tie_records"),
        "selection_score_worse_records": selection_delta.get("worse_records"),
        "selection_score_uncomparable_records": selection_delta.get("uncomparable_records"),
        "training_records": training_summary.get("num_records"),
        "dropped_records_without_feasible_candidate": training_summary.get(
            "dropped_records_without_feasible_candidate"
        ),
        "num_candidates": training_summary.get("num_candidates"),
        "num_atoms": training_summary.get("num_atoms"),
        "atom_schema_version": training_summary.get("atom_schema_version"),
        "weights_sum": training_artifact.get("weights_sum"),
        "weights_nonnegative": training_artifact.get("weights_nonnegative"),
        "scales_all_positive_finite": training_artifact.get("scales_all_positive_finite"),
        "score_expression": plan_decision.get("score_expression") or SCORE_EXPRESSION,
    }


def _promotion_plan_checks(
    plan: dict[str, Any],
    source_hashes: dict[str, str],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    decision = _dict(plan.get("final_decision"))
    result_summary = _dict(plan.get("runtime_result_review_summary"))
    delta_summary = _dict(plan.get("shadow_vs_top1_delta_review_summary"))
    plan_hashes = _dict(plan.get("source_hashes"))
    checks = [
        _expect("promotion_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("promotion_plan_passed", decision.get("passed"), True),
        _expect("promotion_plan_failed_checks", decision.get("failed_checks"), []),
        _expect(
            "promotion_plan_authorized_current_work",
            decision.get("authorized_current_work"),
            PROMOTION_PLAN_CURRENT_WORK,
        ),
        _expect(
            "promotion_plan_authorized_next_work",
            decision.get("authorized_next_work"),
            SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _expect(
            "promotion_plan_evidence_preflight_authorized",
            decision.get("evidence_package_preflight_authorized"),
            True,
        ),
        _expect(
            "promotion_plan_recommendation",
            decision.get("recommendation"),
            "do_not_promote_from_current_evidence_alone",
        ),
        _expect(
            "promotion_plan_immediate_action",
            decision.get("immediate_action"),
            "build_runtime_promotion_evidence_package_preflight_only",
        ),
        _expect("promotion_plan_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect(
            "promotion_plan_source_result_review_sha",
            plan_hashes.get("runtime_result_review_json"),
            source_hashes.get("runtime_result_review"),
        ),
        _expect(
            "promotion_plan_source_delta_review_sha",
            plan_hashes.get("shadow_vs_top1_delta_review_json"),
            source_hashes.get("shadow_vs_top1_delta_review"),
        ),
        _expect(
            "promotion_plan_result_records",
            result_summary.get("records"),
            expected["records"],
        ),
        _expect(
            "promotion_plan_result_shadow_nonzero",
            result_summary.get("shadow_selected_index_nonzero_records"),
            expected["shadow_selected_index_nonzero_records"],
        ),
        _expect(
            "promotion_plan_delta_static_objective_supported",
            delta_summary.get("static_objective_delta_supported"),
            True,
        ),
        _expect(
            "promotion_plan_delta_selection_score_worse",
            delta_summary.get("selection_score_worse_records"),
            expected["selection_score_worse_records"],
        ),
    ]
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"promotion_plan_{name}", decision.get(name), False))
    return checks


def _result_review_checks(
    result_review: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    decision = _dict(result_review.get("final_decision"))
    execution = _dict(result_review.get("execution"))
    records = _dict(result_review.get("records"))
    heads = _dict(result_review.get("heads"))
    analysis = _dict(result_review.get("analysis"))
    checks = [
        _expect("result_review_status", decision.get("status"), SOURCE_RESULT_REVIEW_STATUS),
        _expect("result_review_passed", decision.get("passed"), True),
        _expect("result_review_failed_checks", decision.get("failed_checks"), []),
        _expect(
            "result_review_authorized_next_work",
            decision.get("authorized_next_work"),
            PROMOTION_PLAN_CURRENT_WORK,
        ),
        _expect(
            "result_review_promotion_decision_plan_authorized",
            decision.get("promotion_decision_plan_authorized_next"),
            True,
        ),
        _expect("result_review_current_dp_head", heads.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("result_review_required_dp_head", heads.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("result_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("result_review_candidate_operation", decision.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("result_review_executed_output_policy", decision.get("executed_output_policy"), "dp_top1"),
        _expect("result_review_selection_logs", execution.get("selection_log_count"), expected["selection_log_count"]),
        _expect("result_review_validation_summaries", execution.get("validation_summary_count"), expected["validation_summary_count"]),
        _expect("result_review_replay_summaries", execution.get("replay_summary_count"), expected["replay_summary_count"]),
        _expect("result_review_formal_seed_path_count", execution.get("formal_seed_path_count"), 0),
        _expect("result_review_records", records.get("record_count"), expected["records"]),
        _expect("result_review_default_off_records", records.get("default_off_selector_records"), expected["default_off_selector_records"]),
        _expect("result_review_artifact_ready_records", records.get("artifact_contract_ready_records"), expected["artifact_contract_ready_records"]),
        _expect("result_review_executed_top1", records.get("executed_top1_records"), expected["executed_top1_records"]),
        _expect(
            "result_review_selected_matches_executed",
            records.get("selected_index_matches_executed_index_records"),
            expected["selected_index_matches_executed_index_records"],
        ),
        _expect(
            "result_review_shadow_nonzero",
            records.get("shadow_selected_index_nonzero_records"),
            expected["shadow_selected_index_nonzero_records"],
        ),
        _expect(
            "result_review_shadow_differs",
            records.get("shadow_selected_index_differs_from_executed_index_records"),
            expected["shadow_selected_index_differs_from_executed_index_records"],
        ),
        _expect("result_review_feasible", records.get("feasible_records"), expected["feasible_records"]),
        _expect("result_review_fallback", records.get("used_fallback_records"), expected["used_fallback_records"]),
        _expect("result_review_review_generated_no_candidates", analysis.get("candidate_generation_executed_by_review"), False),
        _expect("result_review_review_trained_no_camp", analysis.get("training_executed_by_review"), False),
        _expect("result_review_review_ran_no_replay", analysis.get("replay_executed_by_review"), False),
    ]
    for name, value in _dict(records.get("violation_counts")).items():
        checks.append(_expect(f"result_review_violation_{name}", value, 0))
    for name in (
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "deployment_authorized",
        "deployable_checkpoint_claim_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
        "candidate_generation_by_camp_authorized",
        "trajectory_generation_by_camp_authorized",
        "trajectory_modification_by_camp_authorized",
        "dp_modification_authorized",
        "online_selector_change_authorized",
        "executed_trajectory_change_authorized",
        "reference_blend_authorized",
        "guidance_authorized",
        "postprocess_or_postselection_authorized",
        "closed_loop_outcome_authorized",
    ):
        checks.append(_expect(f"result_review_{name}", decision.get(name), False))
    return checks


def _delta_review_checks(
    delta_review: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    decision = _dict(delta_review.get("final_decision"))
    records = _dict(delta_review.get("records"))
    heads = _dict(delta_review.get("heads"))
    analysis = _dict(delta_review.get("analysis"))
    selection = _dict(records.get("selection_score_comparison"))
    shadow_diff = _dict(records.get("selection_score_comparison_among_shadow_diff_records"))
    checks = [
        _expect("delta_review_status", decision.get("status"), SOURCE_DELTA_REVIEW_STATUS),
        _expect("delta_review_passed", decision.get("passed"), True),
        _expect("delta_review_failed_checks", decision.get("failed_checks"), []),
        _expect("delta_review_authorized_next_work", decision.get("authorized_next_work"), PROMOTION_PLAN_CURRENT_WORK),
        _expect("delta_review_static_objective_supported", decision.get("static_objective_delta_supported"), True),
        _expect("delta_review_current_dp_head", heads.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("delta_review_required_dp_head", heads.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("delta_review_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
        _check(
            "delta_review_claim_scope_not_safety",
            "does not prove safety" in str(analysis.get("claim_scope")),
            analysis.get("claim_scope"),
            "static objective only, no safety claim",
        ),
        _expect("delta_review_selection_logs", records.get("selection_log_count"), expected["selection_log_count"]),
        _expect("delta_review_records", records.get("record_count"), expected["records"]),
        _expect("delta_review_executed_top1", records.get("executed_top1_records"), expected["executed_top1_records"]),
        _expect(
            "delta_review_selected_matches_executed",
            records.get("selected_matches_executed_records"),
            expected["selected_index_matches_executed_index_records"],
        ),
        _expect(
            "delta_review_shadow_nonzero",
            records.get("shadow_selected_index_nonzero_records"),
            expected["shadow_selected_index_nonzero_records"],
        ),
        _expect(
            "delta_review_shadow_differs",
            records.get("shadow_selected_index_differs_from_executed_index_records"),
            expected["shadow_selected_index_differs_from_executed_index_records"],
        ),
        _expect("delta_review_formal_seed_path_count", records.get("formal_seed_path_count"), 0),
        _expect("delta_review_selection_score_better", selection.get("better_records"), expected["selection_score_better_records"]),
        _expect("delta_review_selection_score_tie", selection.get("tie_records"), expected["selection_score_tie_records"]),
        _expect("delta_review_selection_score_worse", selection.get("worse_records"), expected["selection_score_worse_records"]),
        _expect("delta_review_selection_score_uncomparable", selection.get("uncomparable_records"), expected["selection_score_uncomparable_records"]),
        _expect(
            "delta_review_shadow_diff_selection_score_better",
            shadow_diff.get("better_records"),
            expected["shadow_diff_selection_score_better_records"],
        ),
        _expect(
            "delta_review_shadow_diff_selection_score_worse",
            shadow_diff.get("worse_records"),
            expected["shadow_diff_selection_score_worse_records"],
        ),
    ]
    for name in (
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "deployment_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
        "candidate_generation_authorized",
        "training_authorized",
        "replay_execution_authorized",
        "dp_modification_authorized",
    ):
        checks.append(_expect(f"delta_review_{name}", decision.get(name), False))
    return checks


def _runtime_manifest_checks(
    manifest: dict[str, Any],
    source_hashes: dict[str, str],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    artifacts = _dict(manifest.get("artifacts"))
    atom_scales = _dict(artifacts.get("atom_scales"))
    static_weights = _dict(artifacts.get("static_weights"))
    authorizations = _dict(manifest.get("authorizations"))
    checks = [
        _expect("runtime_manifest_schema", manifest.get("schema_version"), SOURCE_RUNTIME_MANIFEST_SCHEMA),
        _expect("runtime_manifest_role", manifest.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"),
        _expect("runtime_manifest_source_scope", manifest.get("source_scope"), "public_simulator_fixed_dp_candidate_tensor"),
        _expect("runtime_manifest_default_off", manifest.get("default_off"), True),
        _expect("runtime_manifest_fail_closed", manifest.get("fail_closed"), True),
        _expect("runtime_manifest_selection_effect", manifest.get("selection_effect"), False),
        _expect("runtime_manifest_online_selector_change", manifest.get("online_selector_change"), False),
        _expect("runtime_manifest_selector_mode", manifest.get("selector_mode"), "static"),
        _expect("runtime_manifest_candidate_operation", manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("runtime_manifest_executed_output_policy", manifest.get("executed_output_policy"), "dp_top1"),
        _expect("runtime_manifest_required_candidate_count", manifest.get("required_candidate_count"), expected["num_candidates"]),
        _expect("runtime_manifest_atom_count", manifest.get("atom_count"), expected["num_atoms"]),
        _expect("runtime_manifest_atom_schema", manifest.get("atom_schema_version"), "camp_legacy_v1_9d"),
        _expect("runtime_manifest_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("runtime_manifest_required_dp_head", manifest.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("runtime_manifest_current_dp_head", manifest.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("runtime_manifest_artifact_names", sorted(artifacts), ["atom_scales", "static_weights"]),
        _expect("runtime_manifest_atom_scales_required", atom_scales.get("required"), True),
        _expect("runtime_manifest_static_weights_required", static_weights.get("required"), True),
        _expect("runtime_manifest_atom_scales_sha", atom_scales.get("sha256"), source_hashes.get("atom_scales_json")),
        _expect("runtime_manifest_static_weights_sha", static_weights.get("sha256"), source_hashes.get("offline_weights_npy")),
    ]
    for name, value in authorizations.items():
        if name.endswith("_authorized") or name in {"training_executed"}:
            checks.append(_expect(f"runtime_manifest_{name}", value, False))
    return checks


def _training_review_checks(
    training_review: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    decision = _dict(training_review.get("final_decision"))
    artifact_review = _dict(training_review.get("artifact_review"))
    training_summary = _dict(training_review.get("training_summary"))
    checks = [
        _expect("training_review_status", decision.get("status"), SOURCE_TRAINING_REVIEW_STATUS),
        _expect("training_review_passed", decision.get("passed"), True),
        _expect("training_review_failed_checks", decision.get("failed_checks"), []),
        _expect("training_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("training_review_weights_sum", _round6(artifact_review.get("weights_sum")), 1.0),
        _expect("training_review_weights_nonnegative", artifact_review.get("weights_nonnegative"), True),
        _expect("training_review_weights_file_matches_summary", artifact_review.get("weights_file_matches_summary"), True),
        _expect("training_review_scales_all_positive_finite", artifact_review.get("scales_all_positive_finite"), True),
        _expect("training_review_num_records", training_summary.get("num_records"), expected["training_records"]),
        _expect("training_review_dropped_records", training_summary.get("dropped_records_without_feasible_candidate"), expected["dropped_records_without_feasible_candidate"]),
        _expect("training_review_num_candidates", training_summary.get("num_candidates"), expected["num_candidates"]),
        _expect("training_review_num_atoms", training_summary.get("num_atoms"), expected["num_atoms"]),
        _expect("training_review_atom_schema", training_summary.get("atom_schema_version"), "camp_legacy_v1_9d"),
        _expect("training_review_training_executed_by_review", decision.get("training_executed_by_review"), False),
        _expect("training_review_replay_executed", decision.get("replay_executed"), False),
        _expect("training_review_candidate_generation_executed", decision.get("candidate_generation_executed"), False),
    ]
    for name in (
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "deployment_authorized",
        "deployable_checkpoint_claim_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
        "candidate_generation_by_camp_authorized",
        "trajectory_generation_by_camp_authorized",
        "trajectory_modification_by_camp_authorized",
        "dp_modification_authorized",
        "online_selector_change_authorized",
        "reference_blend_authorized",
        "guidance_authorized",
        "postprocess_or_postselection_authorized",
        "closed_loop_outcome_authorized",
    ):
        checks.append(_expect(f"training_review_{name}", decision.get(name), False))
    return checks


def _training_summary_checks(
    training_summary: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    weights = training_summary.get("trained_weights")
    contract = _dict(training_summary.get("dp_native_training_data_contract"))
    selection_logs = contract.get("selection_logs")
    checks = [
        _expect("training_summary_num_records", training_summary.get("num_records"), expected["training_records"]),
        _expect("training_summary_dropped_records", training_summary.get("dropped_records_without_feasible_candidate"), expected["dropped_records_without_feasible_candidate"]),
        _expect("training_summary_num_candidates", training_summary.get("num_candidates"), expected["num_candidates"]),
        _expect("training_summary_num_atoms", training_summary.get("num_atoms"), expected["num_atoms"]),
        _expect("training_summary_atom_schema", training_summary.get("atom_schema_version"), "camp_legacy_v1_9d"),
        _expect("training_summary_contract_schema", contract.get("schema_version"), "clean_dp_native_training_data_contract_validator_v1"),
        _expect("training_summary_contract_passed", contract.get("passed"), True),
        _expect("training_summary_contract_read_only", contract.get("read_only"), True),
        _expect("training_summary_contract_records", contract.get("records"), expected["records"]),
        _expect("training_summary_contract_selection_log_count", len(selection_logs) if isinstance(selection_logs, list) else None, expected["selection_log_count"]),
        _expect("training_summary_future_training_input_contract", contract.get("future_training_input_contract_satisfied"), True),
        _expect("training_summary_contract_candidate_generation_executed", contract.get("candidate_generation_executed"), False),
        _expect("training_summary_contract_replay_executed", contract.get("replay_executed"), False),
        _expect("training_summary_contract_dp_modification", contract.get("dp_modification_authorized"), False),
        _expect("training_summary_contract_safety_claim", contract.get("safety_benefit_claim_authorized"), False),
        _expect("training_summary_contract_camp_over_dp_claim", contract.get("camp_over_dp_top1_claim_authorized"), False),
        _check(
            "training_summary_weights_nonnegative_simplex",
            _nonnegative_simplex(weights, expected["num_atoms"]),
            weights,
            "length num_atoms, finite, nonnegative, sum=1",
        ),
    ]
    return checks


def _atom_scale_checks(atom_scales: dict[str, Any], expected: dict[str, int]) -> list[dict[str, Any]]:
    scales = atom_scales.get("scales")
    return [
        _expect("atom_scales_schema", atom_scales.get("atom_schema_version"), "camp_legacy_v1_9d"),
        _expect("atom_scales_count", len(scales) if isinstance(scales, list) else None, expected["num_atoms"]),
        _check(
            "atom_scales_positive_finite",
            isinstance(scales, list)
            and all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0 for value in scales),
            scales,
            "positive finite scales",
        ),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), SOURCE_PLAN_AUTHORIZED_NEXT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_PLAN_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), SOURCE_PLAN_AUTHORIZED_NEXT_WORK),
    ]


def _artifact_file_checks(name: str, path: Path) -> list[dict[str, Any]]:
    return [
        _check(f"{name}_exists", path.is_file(), str(path), "file"),
        _check(
            f"{name}_nonempty",
            path.is_file() and path.stat().st_size > 0,
            path.stat().st_size if path.is_file() else None,
            ">0 bytes",
        ),
    ]


def _artifact_manifest(paths: dict[str, Path], hashes: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "path": str(path.resolve()),
            "sha256": hashes.get(name),
            "role": SOURCE_FILE_ROLES[name],
        }
        for name, path in paths.items()
    ]


def _static_integration_contract() -> dict[str, Any]:
    return {
        "status": "runtime_promotion_evidence_package_preflight_ready_contract_pinned",
        "allowed_operation": "argmin_k score_k(w)",
        "candidate_tensor_source": "fixed_dp_candidate_tensor",
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "default_off": True,
        "fail_closed": True,
        "executed_output_policy": "dp_top1",
        "simplex_master_convex": True,
        "cvar_master_convex": True,
        "l2_master_convex": True,
        "summary": (
            "The runtime evidence package may only support review of a "
            "default-off shadow selector that computes affine scores over the "
            "fixed DP candidate tensor and logs the shadow selected index. "
            "Executed trajectory selection remains DP Top-1 unless a separate "
            "future promotion gate explicitly changes that boundary."
        ),
    }


def _future_review_requirements() -> list[dict[str, str]]:
    return [
        {
            "name": "immutable_hash_review",
            "status": "required_before_any_future_promotion_discussion",
        },
        {
            "name": "runtime_contract_review",
            "status": "must_confirm_default_off_fail_closed_dp_top1_execution",
        },
        {
            "name": "independent_or_expanded_evidence_review",
            "status": "required_before_safety_or_camp_over_dp_claims",
        },
        {
            "name": "explicit_human_promotion_gate",
            "status": "required_before_selector_or_atom_promotion",
        },
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "runtime_promotion_evidence_package_preflight_ready": bool(passed),
        "evidence_package_static_review_authorized": bool(passed),
        "score_expression": SCORE_EXPRESSION,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "preflight_enabled" in failed_set:
        return "explicit_preflight_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.startswith("promotion_plan_") for name in failed):
        return "source_promotion_plan_contract_failure"
    if any(name.startswith("result_review_") for name in failed):
        return "source_result_review_contract_failure"
    if any(name.startswith("delta_review_") for name in failed):
        return "source_delta_review_contract_failure"
    if any(name.startswith("runtime_manifest_") for name in failed):
        return "source_runtime_manifest_contract_failure"
    if any(name.startswith("training_") for name in failed):
        return "source_training_contract_failure"
    if any(name.startswith("atom_scales_") for name in failed):
        return "source_atom_scales_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_artifact_file_missing_or_empty"
    return "runtime_promotion_evidence_package_preflight_contract_failure"


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _nonnegative_simplex(values: Any, expected_len: int) -> bool:
    if not isinstance(values, list) or len(values) != expected_len:
        return False
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in values):
        return False
    if any(value < -1e-12 for value in values):
        return False
    return abs(sum(values) - 1.0) <= 1e-6


def _round6(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value), 6)


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    values = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    return values[-1] if values else None


def _compact(value: Any) -> str:
    text = json.dumps(_stable(value), ensure_ascii=True, sort_keys=True)
    return text if len(text) <= 96 else text[:93] + "..."


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows: list[str] = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
