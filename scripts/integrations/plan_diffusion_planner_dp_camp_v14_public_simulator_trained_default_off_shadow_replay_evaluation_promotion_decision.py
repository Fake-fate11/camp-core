#!/usr/bin/env python3
"""Planning-only v14 DP-CAMP promotion decision gate.

This gate consumes the existing trained default-off shadow replay/evaluation
result review and emits a conservative promotion-decision plan. It does not
promote, deploy, train, replay, generate candidates, modify DP, change an
online selector, or make safety/CAMP-over-DP claims.
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
    "evaluation_promotion_decision_plan_v1"
)
SOURCE_READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_result_review_passed"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_decision_plan_only_after_explicit_"
    "user_authorization"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_decision_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_decision_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_promotion_evidence_package_preflight_only"
)

DEFAULT_EXPECTED_COUNTS = {
    "selection_log_count": 32,
    "validation_summary_count": 32,
    "replay_summary_count": 32,
    "records_total": 3200,
    "route_count": 16,
    "seed_count": 4,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result_review_json", type=Path, required=True)
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
        "--enable_v14_promotion_decision_planning",
        action="store_true",
        help="Explicit opt-in for planning only; no promotion action is executed.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        result_review_json=args.result_review_json,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_promotion_decision_planning,
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
    result_review_json: Path,
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
    result_review = _read_json_dict(result_review_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    source = _source_summary(result_review, v14_text)
    checks = [
        _expect("planning_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("result_review_json_exists", result_review_json.is_file(), str(result_review_json), "file"),
        _check("v14_audit_md_exists", v14_audit_md.is_file(), str(v14_audit_md), "file"),
        _check("current_status_md_exists", current_status_md.is_file(), str(current_status_md), "file"),
        *_source_checks(source),
        *_artifact_contract_checks(source, expected),
        *_audit_checks(source, v14_text, status_text),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "planning_only": True,
            "result_review_json": str(result_review_json.resolve()),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "selector_promotion": False,
            "deployment": False,
            "dp_modification": False,
            "math_boundary": (
                "DP remains a fixed black-box candidate trajectory generator. "
                "CAMP may only rerank the current tick fixed finite DP candidate "
                "tensor by affine score_k(w)=a_k^T w over approved atoms with "
                "nonnegative simplex weights; simplex/CVaR/L2 master terms must "
                "remain convex."
            ),
        },
        "source_summary": source,
        "promotion_decision_plan": _promotion_decision_plan(),
        "evidence_package_preflight": _evidence_package_preflight(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "promotion_decision_plan.json", report)
    (output_dir / "promotion_decision_plan.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    plan = report["promotion_decision_plan"]
    lines = [
        "# V14 Trained Shadow Replay/Evaluation Promotion-Decision Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Recommendation: `{decision['recommendation']}`",
        f"- Immediate action: `{decision['immediate_action']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        "",
        "## Source",
        "",
        f"- Result-review status: `{source['status']}`",
        f"- Result-review passed: `{source['passed']}`",
        f"- Selection logs / records: `{source['selection_log_count']}` / `{source['records_total']}`",
        f"- Routes / seeds: `{source['route_count']}` / `{source['seed_count']}`",
        f"- Shadow non-Top-1 records: `{source['shadow_selected_index_nonzero_records']}`",
        f"- Executed DP Top-1 records: `{source['executed_top1_records']}`",
        f"- Training records / dropped all-infeasible: `{source['training_records']}` / `{source['dropped_records_without_feasible_candidate']}`",
        f"- First loss / last loss: `{source['first_loss']}` / `{source['last_loss']}`",
        f"- Candidates / atoms: `{source['num_candidates']}` / `{source['num_atoms']}`",
        f"- Score expression: `{source['score_expression']}`",
        "",
        "## Required Evidence Before Any Promotion",
        "",
    ]
    for item in plan["required_evidence_before_promotion"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## No-Go Conditions", ""])
    for item in plan["no_go_conditions"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate is planning-only. It does not promote atoms or selectors, "
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
    for check in report["plan_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_summary(result_review: dict[str, Any], v14_text: str) -> dict[str, Any]:
    decision = _dict(result_review.get("final_decision"))
    records = _dict(result_review.get("records"))
    execution = _dict(result_review.get("execution"))
    analysis = _dict(result_review.get("analysis"))
    return {
        "schema_version": result_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "promotion_decision_plan_authorized_next": bool(
            decision.get("promotion_decision_plan_authorized_next")
        ),
        "selector_promotion_authorized": bool(decision.get("selector_promotion_authorized")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "deployment_authorized": bool(decision.get("deployment_authorized")),
        "deployable_checkpoint_claim_authorized": bool(
            decision.get("deployable_checkpoint_claim_authorized")
        ),
        "safety_benefit_claim_authorized": bool(
            decision.get("safety_benefit_claim_authorized")
        ),
        "camp_over_dp_top1_claim_authorized": bool(
            decision.get("camp_over_dp_top1_claim_authorized")
        ),
        "candidate_generation_by_camp_authorized": bool(
            decision.get("candidate_generation_by_camp_authorized")
        ),
        "trajectory_generation_by_camp_authorized": bool(
            decision.get("trajectory_generation_by_camp_authorized")
        ),
        "trajectory_modification_by_camp_authorized": bool(
            decision.get("trajectory_modification_by_camp_authorized")
        ),
        "dp_modification_authorized": bool(decision.get("dp_modification_authorized")),
        "online_selector_change_authorized": bool(
            decision.get("online_selector_change_authorized")
        ),
        "executed_trajectory_change_authorized": bool(
            decision.get("executed_trajectory_change_authorized")
        ),
        "failed_checks": list(decision.get("failed_checks") or []),
        "selection_log_count": execution.get("selection_log_count"),
        "validation_summary_count": execution.get("validation_summary_count"),
        "replay_summary_count": execution.get("replay_summary_count"),
        "records_total": records.get("records_total"),
        "route_count": records.get("route_count"),
        "seed_count": records.get("seed_count"),
        "shadow_selected_index_nonzero_records": records.get(
            "shadow_selected_index_nonzero_records"
        ),
        "executed_top1_records": records.get("executed_top1_records"),
        "selected_index_matches_executed_index_records": records.get(
            "selected_index_matches_executed_index_records"
        ),
        "selection_effect_true_count": records.get("selection_effect_true_count"),
        "online_change_true_count": records.get("online_change_true_count"),
        "candidate_reference_blend_steps_nonzero": records.get(
            "candidate_reference_blend_steps_nonzero"
        ),
        "candidate_closed_loop_outcome_weights_nonzero": records.get(
            "candidate_closed_loop_outcome_weights_nonzero"
        ),
        "candidate_closed_loop_outcomes_nonzero": records.get(
            "candidate_closed_loop_outcomes_nonzero"
        ),
        "formal_seed_path_count": records.get("formal_seed_path_count"),
        "camp_provenance_forbidden_effect_count": records.get(
            "camp_provenance_forbidden_effect_count"
        ),
        "weights_bad_count": records.get("weights_bad_count"),
        "atom_schema_bad_count": records.get("atom_schema_bad_count"),
        "candidate_count_bad_count": records.get("candidate_count_bad_count"),
        "num_candidates": _single_int_key(records.get("candidate_counts")),
        "num_atoms": _latest_int(v14_text, "v14_public_simulator_fixed_dp_candidate_training_execution_num_atoms"),
        "atom_schema_version": _single_key(records.get("atom_schema_versions")),
        "score_expression": decision.get("score_expression") or analysis.get("score_expression"),
        "training_records": _latest_int(
            v14_text,
            "v14_public_simulator_fixed_dp_candidate_training_execution_num_records",
        ),
        "dropped_records_without_feasible_candidate": _latest_int(
            v14_text,
            "v14_public_simulator_fixed_dp_candidate_training_execution_dropped_records_without_feasible_candidate",
        ),
        "first_loss": _latest_float(
            v14_text,
            "v14_public_simulator_fixed_dp_candidate_training_execution_first_loss",
        ),
        "last_loss": _latest_float(
            v14_text,
            "v14_public_simulator_fixed_dp_candidate_training_execution_last_loss",
        ),
        "oracle_match_rate": _latest_float(
            v14_text,
            "v14_public_simulator_fixed_dp_candidate_training_execution_oracle_match_rate",
        ),
        "feasible_candidate_rate": _latest_float(
            v14_text,
            "v14_public_simulator_fixed_dp_candidate_training_execution_feasible_candidate_rate",
        ),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    blocked = [
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
    ]
    decision_checks = [
        _expect("source_status_ready", source["status"], SOURCE_READY_STATUS),
        _expect("source_passed", source["passed"], True),
        _expect(
            "source_authorizes_this_planning_gate",
            source["authorized_next_work"],
            SOURCE_AUTHORIZED_NEXT_WORK,
        ),
        _expect(
            "source_promotion_decision_plan_authorized_next",
            source["promotion_decision_plan_authorized_next"],
            True,
        ),
        _expect("source_failed_checks_empty", source["failed_checks"], []),
    ]
    return decision_checks + [
        _expect(f"source_{name}_false", source.get(name, False), False)
        for name in blocked
    ]


def _artifact_contract_checks(
    source: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    return [
        _expect("selection_log_count", source["selection_log_count"], expected["selection_log_count"]),
        _expect("validation_summary_count", source["validation_summary_count"], expected["validation_summary_count"]),
        _expect("replay_summary_count", source["replay_summary_count"], expected["replay_summary_count"]),
        _expect("records_total", source["records_total"], expected["records_total"]),
        _expect("route_count", source["route_count"], expected["route_count"]),
        _expect("seed_count", source["seed_count"], expected["seed_count"]),
        _expect("executed_top1_all_records", source["executed_top1_records"], source["records_total"]),
        _expect(
            "selected_index_matches_executed_index_all_records",
            source["selected_index_matches_executed_index_records"],
            source["records_total"],
        ),
        _expect("selection_effect_true_zero", source["selection_effect_true_count"], 0),
        _expect("online_change_true_zero", source["online_change_true_count"], 0),
        _expect(
            "candidate_reference_blend_steps_nonzero_zero",
            source["candidate_reference_blend_steps_nonzero"],
            0,
        ),
        _expect(
            "candidate_closed_loop_outcome_weights_nonzero_zero",
            source["candidate_closed_loop_outcome_weights_nonzero"],
            0,
        ),
        _expect(
            "candidate_closed_loop_outcomes_nonzero_zero",
            source["candidate_closed_loop_outcomes_nonzero"],
            0,
        ),
        _expect("formal_seed_path_count_zero", source["formal_seed_path_count"], 0),
        _expect(
            "camp_provenance_forbidden_effect_zero",
            source["camp_provenance_forbidden_effect_count"],
            0,
        ),
        _expect("weights_bad_zero", source["weights_bad_count"], 0),
        _expect("atom_schema_bad_zero", source["atom_schema_bad_count"], 0),
        _expect("candidate_count_bad_zero", source["candidate_count_bad_count"], 0),
        _expect("num_candidates_fixed", source["num_candidates"], expected["num_candidates"]),
        _expect("num_atoms_expected", source["num_atoms"], expected["num_atoms"]),
        _expect("score_expression_affine", source["score_expression"], SCORE_EXPRESSION),
        _expect("training_records_expected", source["training_records"], expected["training_records"]),
        _expect(
            "dropped_records_expected",
            source["dropped_records_without_feasible_candidate"],
            expected["dropped_records_without_feasible_candidate"],
        ),
        _check(
            "training_loss_not_increased",
            _finite(source["first_loss"]) and _finite(source["last_loss"])
            and source["last_loss"] <= source["first_loss"],
            f"{source['first_loss']} -> {source['last_loss']}",
            "last_loss <= first_loss",
        ),
    ]


def _audit_checks(source: dict[str, Any], v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_READY_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("audit_training_executed", _latest_value(v14_text, "camp_training_executed"), "True"),
        _expect(
            "audit_result_review_passed",
            _latest_value(v14_text, "trained_default_off_shadow_replay_evaluation_result_review_passed"),
            "True",
        ),
        _check("status_doc_mentions_source_status", SOURCE_READY_STATUS in status_text, SOURCE_READY_STATUS in status_text, True),
        _check("status_doc_mentions_source_gate", SOURCE_AUTHORIZED_NEXT_WORK in status_text, SOURCE_AUTHORIZED_NEXT_WORK in status_text, True),
        _check("source_shadow_selection_is_nontrivial", (source["shadow_selected_index_nonzero_records"] or 0) > 0, source["shadow_selected_index_nonzero_records"], "> 0"),
    ]


def _promotion_decision_plan() -> dict[str, Any]:
    return {
        "recommendation": "do_not_promote_from_current_evidence_alone",
        "promotion_class_under_consideration": (
            "future_default_off_shadow_or_development_reranker_candidate"
        ),
        "immediate_action": "build_promotion_evidence_package_preflight_only",
        "required_evidence_before_promotion": [
            "immutable_artifact_manifest_for_weights_scales_training_result_review_and_shadow_logs",
            "fixed_dp_head_and_fixed_candidate_tensor_contract_for_all_evidence",
            "default_off_fail_closed_selector_static_integration_contract",
            "independent_holdout_or_expanded_shadow_replay_evidence_with_zero_forbidden_effects",
            "explicit_metric_thresholds_before_any_safety_or_camp_over_dp_claim",
            "human_authorized_promotion_gate_after_evidence_package_review",
        ],
        "no_go_conditions": [
            "dp_head_differs_from_fixed_tieriv_commit",
            "camp_generates_modifies_blends_or_postprocesses_trajectories",
            "score_expression_not_affine_or_weights_not_nonnegative_simplex",
            "online_selector_change_or_executed_trajectory_change_before_promotion",
            "closed_loop_outcome_used_as_training_or_online_input",
            "formal_seed_11_12_13_or_full36_used_without_explicit_gate",
            "safety_benefit_or_camp_over_dp_top1_claim_without_independent_evidence",
        ],
    }


def _evidence_package_preflight() -> dict[str, Any]:
    return {
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "preflight_only": True,
        "promotion_authorized": False,
        "deployment_authorized": False,
        "training_authorized": False,
        "replay_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = sorted(check["name"] for check in checks if not check["passed"])
    plan = _promotion_decision_plan()
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "promotion_decision_plan_ready": bool(passed),
        "evidence_package_preflight_authorized": bool(passed),
        "recommendation": plan["recommendation"],
        "immediate_action": plan["immediate_action"],
        "promotion_class_under_consideration": plan["promotion_class_under_consideration"],
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "candidate_generation_authorized": False,
        "replay_execution_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "score_expression": SCORE_EXPRESSION,
    }


def _failure_class(failed: list[str]) -> str:
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    if any("planning_enabled" in check for check in failed):
        return "explicit_planning_authorization_missing"
    if any("count" in check or "records" in check for check in failed):
        return "source_result_shape_or_count_contract_failure"
    return "promotion_decision_plan_contract_failure"


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    values = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    return values[-1] if values else None


def _latest_int(text: str, key: str) -> int | None:
    value = _latest_value(text, key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _latest_float(text: str, key: str) -> float | None:
    value = _latest_value(text, key)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _single_int_key(value: Any) -> int | None:
    if not isinstance(value, dict) or len(value) != 1:
        return None
    key = next(iter(value))
    try:
        return int(key)
    except (TypeError, ValueError):
        return None


def _single_key(value: Any) -> str | None:
    if not isinstance(value, dict) or len(value) != 1:
        return None
    key = next(iter(value))
    return key if isinstance(key, str) else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    lines = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": observed,
        "expected": expected,
    }


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
