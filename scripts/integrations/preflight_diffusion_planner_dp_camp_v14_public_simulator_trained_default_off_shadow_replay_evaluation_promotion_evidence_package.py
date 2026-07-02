#!/usr/bin/env python3
"""Read-only v14 DP-CAMP promotion evidence-package preflight.

This gate consumes existing promotion-decision, result-review, training-review,
and training artifacts. It emits a manifest plus static integration evidence
requirements. It does not promote, deploy, train, replay, generate candidates,
modify DP, change a selector, or make safety/CAMP-over-DP claims.
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
    "dp_camp_v14_public_simulator_trained_default_off_shadow_replay_"
    "evaluation_promotion_evidence_package_preflight_v1"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_decision_plan_ready"
)
SOURCE_PLAN_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_evidence_package_preflight_only"
)
SOURCE_RESULT_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_result_review_passed"
)
SOURCE_TRAINING_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_training_artifact_"
    "static_contract_review_passed"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_evidence_package_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_evidence_package_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_static_"
    "integration_contract_plan_only"
)

DEFAULT_EXPECTED_COUNTS = {
    "selection_log_count": 32,
    "validation_summary_count": 32,
    "replay_summary_count": 32,
    "records_total": 3200,
    "route_count": 16,
    "seed_count": 4,
    "shadow_selected_index_nonzero_records": 2832,
    "executed_top1_records": 3200,
    "selected_index_matches_executed_index_records": 3200,
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
    "promotion_decision_plan": "source promotion-decision plan",
    "result_review": "source trained default-off result review",
    "training_artifact_static_review": "source training artifact contract review",
    "training_summary": "source training execution summary",
    "offline_weights_npy": "source offline nonnegative simplex weights",
    "atom_scales_json": "source approved atom scale metadata",
    "shadow_execution_sha256s": "source shadow replay/evaluation execution hashes",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promotion_decision_plan_json", type=Path, required=True)
    parser.add_argument("--result_review_json", type=Path, required=True)
    parser.add_argument("--training_artifact_static_review_json", type=Path, required=True)
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--offline_weights_npy", type=Path, required=True)
    parser.add_argument("--atom_scales_json", type=Path, required=True)
    parser.add_argument("--shadow_execution_sha256s", type=Path, required=True)
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
        "--enable_v14_promotion_evidence_package_preflight",
        action="store_true",
        help="Explicit opt-in for this read-only evidence-package preflight.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        promotion_decision_plan_json=args.promotion_decision_plan_json,
        result_review_json=args.result_review_json,
        training_artifact_static_review_json=args.training_artifact_static_review_json,
        training_summary_json=args.training_summary_json,
        offline_weights_npy=args.offline_weights_npy,
        atom_scales_json=args.atom_scales_json,
        shadow_execution_sha256s=args.shadow_execution_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_promotion_evidence_package_preflight,
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
    promotion_decision_plan_json: Path,
    result_review_json: Path,
    training_artifact_static_review_json: Path,
    training_summary_json: Path,
    offline_weights_npy: Path,
    atom_scales_json: Path,
    shadow_execution_sha256s: Path,
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
        "promotion_decision_plan": promotion_decision_plan_json,
        "result_review": result_review_json,
        "training_artifact_static_review": training_artifact_static_review_json,
        "training_summary": training_summary_json,
        "offline_weights_npy": offline_weights_npy,
        "atom_scales_json": atom_scales_json,
        "shadow_execution_sha256s": shadow_execution_sha256s,
    }
    source_hashes = {
        name: _sha256(path) for name, path in source_paths.items() if path.is_file()
    }
    plan = _read_json_dict(promotion_decision_plan_json)
    result_review = _read_json_dict(result_review_json)
    training_review = _read_json_dict(training_artifact_static_review_json)
    training_summary = _read_json_dict(training_summary_json)
    atom_scales = _read_json_dict(atom_scales_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)

    source_summary = _source_summary(plan, result_review, training_review, training_summary)
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
    checks.extend(_promotion_plan_checks(plan, expected))
    checks.extend(_result_review_checks(result_review, expected))
    checks.extend(_training_review_checks(training_review, expected))
    checks.extend(_training_summary_checks(training_summary, expected))
    checks.extend(_atom_scale_checks(atom_scales, expected))
    checks.extend(_audit_eof_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "evidence_package_preflight_only": True,
            "promotion_decision_plan_json": str(promotion_decision_plan_json.resolve()),
            "result_review_json": str(result_review_json.resolve()),
            "training_artifact_static_review_json": str(
                training_artifact_static_review_json.resolve()
            ),
            "training_summary_json": str(training_summary_json.resolve()),
            "offline_weights_npy": str(offline_weights_npy.resolve()),
            "atom_scales_json": str(atom_scales_json.resolve()),
            "shadow_execution_sha256s": str(shadow_execution_sha256s.resolve()),
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
            "math_boundary": (
                "DP remains a fixed black-box candidate trajectory generator. "
                "CAMP may only rerank/select the current tick fixed finite DP "
                "candidate tensor by affine score_k(w)=a_k^T w over approved "
                "atoms with nonnegative simplex weights; simplex/CVaR/L2 "
                "master terms must remain convex."
            ),
        },
        "source_hashes": source_hashes,
        "artifact_manifest": _artifact_manifest(source_paths, source_hashes),
        "source_summary": source_summary,
        "static_integration_contract": _static_integration_contract(),
        "future_evidence_requirements": _future_evidence_requirements(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "preflight_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "promotion_evidence_package_preflight.json", report)
    (output_dir / "promotion_evidence_package_preflight.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    lines = [
        "# V14 Promotion Evidence-Package Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Static contract plan authorized: `{decision['default_off_shadow_selector_contract_plan_authorized']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Training authorized: `{decision['training_authorized']}`",
        f"- Replay authorized: `{decision['replay_execution_authorized']}`",
        f"- Candidate generation authorized: `{decision['candidate_generation_authorized']}`",
        "",
        "## Source Summary",
        "",
        f"- Source promotion plan status: `{source['promotion_plan_status']}`",
        f"- Result-review status: `{source['result_review_status']}`",
        f"- Training-review status: `{source['training_review_status']}`",
        f"- Selection logs / records: `{source['selection_log_count']}` / `{source['records_total']}`",
        f"- Training records / dropped all-infeasible: `{source['training_records']}` / `{source['dropped_records_without_feasible_candidate']}`",
        f"- Shadow non-Top-1 / executed DP Top-1: `{source['shadow_selected_index_nonzero_records']}` / `{source['executed_top1_records']}`",
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
            "## Future Evidence Requirements",
            "",
        ]
    )
    for item in report["future_evidence_requirements"]:
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
    plan: dict[str, Any],
    result_review: dict[str, Any],
    training_review: dict[str, Any],
    training_summary: dict[str, Any],
) -> dict[str, Any]:
    plan_decision = _dict(plan.get("final_decision"))
    plan_source = _dict(plan.get("source_summary"))
    result_decision = _dict(result_review.get("final_decision"))
    result_records = _dict(result_review.get("records"))
    result_execution = _dict(result_review.get("execution"))
    training_decision = _dict(training_review.get("final_decision"))
    artifact_review = _dict(training_review.get("artifact_review"))
    return {
        "promotion_plan_status": plan_decision.get("status"),
        "promotion_plan_passed": plan_decision.get("passed"),
        "promotion_plan_authorized_next_work": plan_decision.get("authorized_next_work"),
        "promotion_plan_recommendation": plan_decision.get("recommendation"),
        "result_review_status": result_decision.get("status"),
        "result_review_passed": result_decision.get("passed"),
        "training_review_status": training_decision.get("status"),
        "training_review_passed": training_decision.get("passed"),
        "selection_log_count": result_execution.get(
            "selection_log_count", plan_source.get("selection_log_count")
        ),
        "validation_summary_count": result_execution.get(
            "validation_summary_count", plan_source.get("validation_summary_count")
        ),
        "replay_summary_count": result_execution.get(
            "replay_summary_count", plan_source.get("replay_summary_count")
        ),
        "records_total": result_records.get("records_total", plan_source.get("records_total")),
        "route_count": result_records.get("route_count", plan_source.get("route_count")),
        "seed_count": result_records.get("seed_count", plan_source.get("seed_count")),
        "shadow_selected_index_nonzero_records": result_records.get(
            "shadow_selected_index_nonzero_records",
            plan_source.get("shadow_selected_index_nonzero_records"),
        ),
        "executed_top1_records": result_records.get(
            "executed_top1_records", plan_source.get("executed_top1_records")
        ),
        "selected_index_matches_executed_index_records": result_records.get(
            "selected_index_matches_executed_index_records",
            plan_source.get("selected_index_matches_executed_index_records"),
        ),
        "selection_effect_true_count": result_records.get(
            "selection_effect_true_count", plan_source.get("selection_effect_true_count")
        ),
        "online_change_true_count": result_records.get(
            "online_change_true_count", plan_source.get("online_change_true_count")
        ),
        "formal_seed_path_count": result_records.get(
            "formal_seed_path_count", plan_source.get("formal_seed_path_count")
        ),
        "camp_provenance_forbidden_effect_count": result_records.get(
            "camp_provenance_forbidden_effect_count",
            plan_source.get("camp_provenance_forbidden_effect_count"),
        ),
        "training_records": training_summary.get(
            "num_records", plan_source.get("training_records")
        ),
        "dropped_records_without_feasible_candidate": training_summary.get(
            "dropped_records_without_feasible_candidate",
            plan_source.get("dropped_records_without_feasible_candidate"),
        ),
        "num_candidates": training_summary.get(
            "num_candidates", plan_source.get("num_candidates")
        ),
        "num_atoms": training_summary.get("num_atoms", plan_source.get("num_atoms")),
        "atom_schema_version": training_summary.get(
            "atom_schema_version", plan_source.get("atom_schema_version")
        ),
        "first_loss": plan_source.get("first_loss"),
        "last_loss": plan_source.get("last_loss"),
        "oracle_match_rate": training_summary.get(
            "oracle_match_rate", plan_source.get("oracle_match_rate")
        ),
        "feasible_candidate_rate": training_summary.get(
            "feasible_candidate_rate", plan_source.get("feasible_candidate_rate")
        ),
        "weights_sum": artifact_review.get("weights_sum"),
        "weights_nonnegative": artifact_review.get("weights_nonnegative"),
        "weights_file_matches_summary": artifact_review.get("weights_file_matches_summary"),
        "scales_all_positive_finite": artifact_review.get("scales_all_positive_finite"),
        "score_expression": plan_decision.get(
            "score_expression", result_decision.get("score_expression")
        ),
    }


def _promotion_plan_checks(plan: dict[str, Any], expected: dict[str, int]) -> list[dict[str, Any]]:
    decision = _dict(plan.get("final_decision"))
    source = _dict(plan.get("source_summary"))
    checks = [
        _expect("promotion_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("promotion_plan_passed", decision.get("passed"), True),
        _expect("promotion_plan_failed_checks", decision.get("failed_checks"), []),
        _expect(
            "promotion_plan_authorized_next_work",
            decision.get("authorized_next_work"),
            SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _expect(
            "promotion_plan_evidence_package_preflight_authorized",
            decision.get("evidence_package_preflight_authorized"),
            True,
        ),
        _expect(
            "promotion_plan_recommendation",
            decision.get("recommendation"),
            "do_not_promote_from_current_evidence_alone",
        ),
        _expect("promotion_plan_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
    ]
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"promotion_plan_{name}", decision.get(name), False))
    for name in (
        "selection_log_count",
        "validation_summary_count",
        "replay_summary_count",
        "records_total",
        "route_count",
        "seed_count",
        "shadow_selected_index_nonzero_records",
        "executed_top1_records",
        "selected_index_matches_executed_index_records",
        "training_records",
        "dropped_records_without_feasible_candidate",
        "num_candidates",
        "num_atoms",
    ):
        checks.append(_expect(f"promotion_plan_source_{name}", source.get(name), expected[name]))
    return checks


def _result_review_checks(
    result_review: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    decision = _dict(result_review.get("final_decision"))
    execution = _dict(result_review.get("execution"))
    records = _dict(result_review.get("records"))
    checks = [
        _expect("result_review_status", decision.get("status"), SOURCE_RESULT_REVIEW_STATUS),
        _expect("result_review_passed", decision.get("passed"), True),
        _expect("result_review_failed_checks", decision.get("failed_checks"), []),
        _expect("result_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("result_review_selection_logs", execution.get("selection_log_count"), expected["selection_log_count"]),
        _expect(
            "result_review_validation_summaries",
            execution.get("validation_summary_count"),
            expected["validation_summary_count"],
        ),
        _expect(
            "result_review_replay_summaries",
            execution.get("replay_summary_count"),
            expected["replay_summary_count"],
        ),
        _expect("result_review_records_total", records.get("records_total"), expected["records_total"]),
        _expect("result_review_route_count", records.get("route_count"), expected["route_count"]),
        _expect("result_review_seed_count", records.get("seed_count"), expected["seed_count"]),
        _expect(
            "result_review_shadow_non_top1",
            records.get("shadow_selected_index_nonzero_records"),
            expected["shadow_selected_index_nonzero_records"],
        ),
        _expect(
            "result_review_executed_top1",
            records.get("executed_top1_records"),
            expected["executed_top1_records"],
        ),
        _expect(
            "result_review_selected_matches_executed",
            records.get("selected_index_matches_executed_index_records"),
            expected["selected_index_matches_executed_index_records"],
        ),
        _expect("result_review_selection_effect_true_count", records.get("selection_effect_true_count"), 0),
        _expect("result_review_online_change_true_count", records.get("online_change_true_count"), 0),
        _expect(
            "result_review_reference_blend_steps",
            records.get("candidate_reference_blend_steps_nonzero"),
            0,
        ),
        _expect(
            "result_review_closed_loop_outcome_weights",
            records.get("candidate_closed_loop_outcome_weights_nonzero"),
            0,
        ),
        _expect(
            "result_review_closed_loop_outcomes",
            records.get("candidate_closed_loop_outcomes_nonzero"),
            0,
        ),
        _expect("result_review_formal_seed_path_count", records.get("formal_seed_path_count"), 0),
        _expect(
            "result_review_forbidden_camp_provenance",
            records.get("camp_provenance_forbidden_effect_count"),
            0,
        ),
        _expect("result_review_weights_bad_count", records.get("weights_bad_count"), 0),
        _expect("result_review_atom_schema_bad_count", records.get("atom_schema_bad_count"), 0),
        _expect("result_review_candidate_count_bad_count", records.get("candidate_count_bad_count"), 0),
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
        "executed_trajectory_change_authorized",
    ):
        checks.append(_expect(f"result_review_{name}", decision.get(name), False))
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
        _expect(
            "training_review_weights_sum",
            _round6(artifact_review.get("weights_sum")),
            1.0,
        ),
        _expect("training_review_weights_nonnegative", artifact_review.get("weights_nonnegative"), True),
        _expect(
            "training_review_weights_file_matches_summary",
            artifact_review.get("weights_file_matches_summary"),
            True,
        ),
        _expect(
            "training_review_scales_all_positive_finite",
            artifact_review.get("scales_all_positive_finite"),
            True,
        ),
        _expect("training_review_num_records", training_summary.get("num_records"), expected["training_records"]),
        _expect("training_review_num_candidates", training_summary.get("num_candidates"), expected["num_candidates"]),
        _expect("training_review_num_atoms", training_summary.get("num_atoms"), expected["num_atoms"]),
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
    ):
        checks.append(_expect(f"training_review_{name}", decision.get(name), False))
    return checks


def _training_summary_checks(
    training_summary: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    weights = training_summary.get("trained_weights")
    checks = [
        _expect("training_summary_num_records", training_summary.get("num_records"), expected["training_records"]),
        _expect(
            "training_summary_dropped_records",
            training_summary.get("dropped_records_without_feasible_candidate"),
            expected["dropped_records_without_feasible_candidate"],
        ),
        _expect("training_summary_num_candidates", training_summary.get("num_candidates"), expected["num_candidates"]),
        _expect("training_summary_num_atoms", training_summary.get("num_atoms"), expected["num_atoms"]),
        _expect(
            "training_summary_contract",
            training_summary.get("dp_native_training_data_contract"),
            "fixed_dp_candidate_tensor",
        ),
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
        _expect("atom_scales_count", len(scales) if isinstance(scales, list) else None, expected["num_atoms"]),
        _check(
            "atom_scales_positive_finite",
            isinstance(scales, list)
            and all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0 for value in scales),
            scales,
            "positive finite scales",
        ),
    ]


def _audit_eof_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    return [
        _check(
            "audit_latest_status",
            f"current_v14_status={SOURCE_PLAN_STATUS}" in eof,
            _extract_line(eof, "current_v14_status="),
            f"current_v14_status={SOURCE_PLAN_STATUS}",
        ),
        _check(
            "audit_latest_next_work",
            f"next_work_target={SOURCE_PLAN_AUTHORIZED_NEXT_WORK}" in eof,
            _extract_line(eof, "next_work_target="),
            f"next_work_target={SOURCE_PLAN_AUTHORIZED_NEXT_WORK}",
        ),
        _check(
            "current_status_latest_status",
            f"current_v14_status={SOURCE_PLAN_STATUS}" in status_text,
            "present" if f"current_v14_status={SOURCE_PLAN_STATUS}" in status_text else "missing",
            "present",
        ),
        _check(
            "current_status_latest_next_work",
            f"next_work_target={SOURCE_PLAN_AUTHORIZED_NEXT_WORK}" in status_text,
            "present" if f"next_work_target={SOURCE_PLAN_AUTHORIZED_NEXT_WORK}" in status_text else "missing",
            "present",
        ),
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
        "status": "preflight_ready_contract_pinned",
        "allowed_operation": "argmin_k score_k(w)",
        "candidate_tensor_source": "fixed_dp_candidate_tensor",
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_master_convex": True,
        "cvar_master_convex": True,
        "l2_master_convex": True,
        "summary": (
            "A future default-off shadow selector may only compute affine "
            "scores over the fixed DP candidate tensor and log the shadow "
            "selected index. Executed trajectory selection must remain DP "
            "Top-1 until a separate promotion gate."
        ),
    }


def _future_evidence_requirements() -> list[dict[str, str]]:
    return [
        {
            "name": "default_off_shadow_selector_wiring",
            "status": "future_static_contract_plan_required_before_implementation",
        },
        {
            "name": "latency_determinism_missing_candidate_handling",
            "status": "future_measurement_required",
        },
        {
            "name": "closed_loop_evaluation",
            "status": "future_nonformal_design_required",
        },
        {
            "name": "metrics_and_thresholds",
            "status": "thresholds_must_be_predeclared_before_evaluation",
        },
        {
            "name": "rollback_observability",
            "status": "future_runtime_contract_required",
        },
        {
            "name": "independent_safety_claim_gate",
            "status": "required_before_any_safety_language",
        },
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "default_off_shadow_selector_contract_plan_authorized": passed,
        "promotion_evidence_package_preflight_ready": passed,
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
    if {"audit_latest_status", "audit_latest_next_work"} & failed_set:
        return "v14_eof_contract_mismatch"
    if any(name.startswith("promotion_plan_") for name in failed):
        return "source_promotion_plan_contract_failure"
    if any(name.startswith("result_review_") for name in failed):
        return "source_result_review_contract_failure"
    if any(name.startswith("training_") for name in failed):
        return "source_training_contract_failure"
    return "promotion_evidence_package_preflight_contract_failure"


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


def _latest_text_block(text: str) -> str:
    marker = "## "
    index = text.rfind(marker)
    return text[index:] if index >= 0 else text


def _extract_line(text: str, prefix: str) -> str | None:
    for line in reversed(text.splitlines()):
        if line.startswith(prefix):
            return line
    return None


def _compact(value: Any) -> str:
    text = json.dumps(_stable(value), ensure_ascii=True, sort_keys=True)
    return text if len(text) <= 96 else text[:93] + "..."


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_sha256sums(output_dir: Path) -> None:
    rows: list[str] = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
