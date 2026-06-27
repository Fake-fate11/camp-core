#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_v1"
DISABLED_STATUS = (
    "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_default_off_disabled"
)
READY_STATUS = "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_ready"
REJECT_STATUS = "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_rejected"
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_promotion_decision_plan_only_after_explicit_user_authorization"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = {11, 12, 13}

FORBIDDEN_TRUE_FLAGS = (
    "Full36_authorized",
    "atom_promotion_authorized",
    "camp_over_dp_top1_claim_authorized",
    "candidate_generation_authorized",
    "closed_loop_outcome_online_input_authorized",
    "deployable_checkpoint_claim_authorized",
    "deployment_authorized",
    "dp_modification_authorized",
    "feasible_ranking_master_change_authorized",
    "formal_seeds_11_12_13_authorized",
    "guidance_authorized",
    "hard_feasibility_relaxation_authorized",
    "online_selector_change_authorized",
    "postprocess_postselection_authorized",
    "production_selector_change_authorized",
    "reference_blend_authorized",
    "replay_execution_authorized",
    "safety_benefit_claim_authorized",
    "selector_promotion_authorized",
)

REVIEW_FORBIDDEN_ACTIONS = (
    "atom_promotion_authorized",
    "camp_over_dp_top1_claim_authorized",
    "candidate_generation_authorized",
    "deployable_checkpoint_claim_authorized",
    "deployment_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "production_selector_change_authorized",
    "replay_execution_authorized",
    "safety_benefit_claim_authorized",
    "selector_promotion_authorized",
    "training_authorized",
    "training_execution_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off result-review gate for the v13 offline nonpromotion "
            "static CAMP reranker. It reads existing fixed-DP candidate-set "
            "artifacts only and does not authorize promotion or deployment."
        )
    )
    parser.add_argument("--collection_summary_json", type=Path, required=True)
    parser.add_argument("--pipeline_summary_json", type=Path, required=True)
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--nonpromotion_audit_json", type=Path, required=True)
    parser.add_argument("--holdout_audit_json", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_default_off_v13_offline_nonpromotion_static_reranker_result_review",
        action="store_true",
        help="Explicit opt-in required before reviewing existing v13 artifacts.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        collection_summary_json=args.collection_summary_json,
        pipeline_summary_json=args.pipeline_summary_json,
        training_summary_json=args.training_summary_json,
        nonpromotion_audit_json=args.nonpromotion_audit_json,
        holdout_audit_json=args.holdout_audit_json,
        current_camp_head=args.current_camp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_default_off_v13_offline_nonpromotion_static_reranker_result_review
        ),
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
    collection_summary_json: Path,
    pipeline_summary_json: Path,
    training_summary_json: Path,
    nonpromotion_audit_json: Path,
    holdout_audit_json: Path,
    current_camp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        label=label,
        current_camp_head=current_camp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    artifacts = {
        "collection_summary": collection_summary_json,
        "pipeline_summary": pipeline_summary_json,
        "training_summary": training_summary_json,
        "nonpromotion_audit": nonpromotion_audit_json,
        "holdout_audit": holdout_audit_json,
    }
    payloads: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    for name, path in artifacts.items():
        exists = path.is_file()
        checks.append(_check(f"{name}_exists", exists, exists, True))
        if exists:
            report["source_hashes"][f"{name}_sha256"] = _sha256(path)
            loaded = _load_json(path)
            payloads[name] = loaded if isinstance(loaded, dict) else {}
            checks.append(_check(f"{name}_json_object", isinstance(loaded, dict), type(loaded).__name__, "dict"))
        else:
            payloads[name] = {}

    checks.extend(
        [
            _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
            _check("required_dp_head_is_fixed", required_dp_head == FIXED_DP_HEAD, required_dp_head, FIXED_DP_HEAD),
        ]
    )
    checks.extend(_collection_checks(payloads["collection_summary"]))
    checks.extend(_pipeline_checks(payloads["pipeline_summary"], report["source_hashes"]))
    checks.extend(_training_checks(payloads["training_summary"]))
    checks.extend(_nonpromotion_checks(payloads["nonpromotion_audit"]))
    checks.extend(_holdout_checks(payloads["holdout_audit"]))
    checks.extend(_cross_artifact_checks(payloads, report["source_hashes"]))
    checks.extend(_forbidden_flag_checks(payloads))

    passed = all(check["passed"] for check in checks)
    report["artifact_summary"] = _artifact_summary(payloads, report["source_hashes"])
    report["review_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("artifact_summary", {})
    lines = [
        "# DP-CAMP V13 Offline Nonpromotion Static Reranker Result Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP over DP Top-1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Evidence",
        "",
        f"- Collection records: `{summary.get('records_total')}`",
        f"- Fallback-risk records: `{summary.get('records_without_feasible_candidate')}`",
        f"- Training records: `{summary.get('training_records')}`",
        f"- Validation records: `{summary.get('validation_records')}`",
        f"- Candidate count: `{summary.get('num_candidates')}`",
        f"- Atom schema: `{summary.get('atom_schema_version')}`",
        f"- Score expression: `{summary.get('score_expression')}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This review does not train CAMP, run replay, generate candidates, modify "
        "Diffusion Planner, change online selection, promote atoms, promote a "
        "selector, mark a checkpoint deployable, or claim safety benefit.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report.get("review_checks", []):
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
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "name": "dp_camp_v13_offline_nonpromotion_static_reranker_result_review",
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "review_only": True,
            "read_only_existing_artifacts": True,
            "fixed_dp_candidate_reranking_only": True,
            "score_expression": "score_k(w)=a_k^T w",
            "current_camp_head": current_camp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "CAMP remains a static reranker over fixed DP candidate "
                "trajectories. This review reads current-tick finite candidate "
                "features and existing audit artifacts only; it preserves "
                "score_k(w)=a_k^T w and does not alter the convex "
                "simplex/CVaR/L2 master."
            ),
        },
        "source_hashes": {},
        "artifact_summary": {},
        "review_checks": [],
        "blocked_actions": {key: False for key in REVIEW_FORBIDDEN_ACTIONS},
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "result_review_ready": False,
            "promotion_decision_plan_authorized": False,
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
            "failed_checks": [],
        },
    }


def _collection_checks(collection: dict[str, Any]) -> list[dict[str, Any]]:
    records_total = _path(collection, "records_total")
    return [
        _expect("collection_status_complete", _path(collection, "status"), "complete"),
        _expect("collection_selection_log_count", _path(collection, "selection_log_count"), 512),
        _expect("collection_expected_replay_commands", _path(collection, "expected_replay_commands"), 512),
        _expect("collection_failed_replay_commands", _path(collection, "failed_replay_commands"), 0),
        _expect("collection_records_total", records_total, 51200),
        _expect("collection_records_without_feasible_candidate", _path(collection, "records_without_feasible_candidate"), 14058),
        _expect("collection_records_with_feasible_candidate", _path(collection, "records_with_feasible_candidate"), 37142),
        _expect("collection_records_bad_feasible_mask", _path(collection, "records_bad_feasible_mask"), 0),
        _expect("collection_candidate_counts", _path(collection, "candidate_counts"), [8]),
        _expect("collection_formal_seed_path_matches", _path(collection, "formal_seed_path_matches"), 0),
        _expect("collection_provenance_present_records", _path(collection, "provenance_present_records"), records_total),
        _expect("collection_provenance_payload_valid_records", _path(collection, "provenance_payload_valid_records"), records_total),
        _expect("collection_provenance_prepost_equal_records", _path(collection, "provenance_prepost_equal_records"), records_total),
        _expect(
            "collection_provenance_reference_blend_separated_records",
            _path(collection, "provenance_reference_blend_separated_records"),
            records_total,
        ),
        _expect("collection_contract_unique_values", _path(collection, "contract_unique_values"), [[8, False, None, False]]),
        _expect("collection_fixed_dp_candidate_generation_authorized", _path(collection, "fixed_dp_candidate_generation_authorized"), True),
        _expect("collection_candidate_generation_by_camp_authorized", _path(collection, "candidate_generation_by_camp_authorized"), False),
        _expect("collection_dp_modification_authorized", _path(collection, "dp_modification_authorized"), False),
    ]


def _pipeline_checks(pipeline: dict[str, Any], source_hashes: dict[str, str]) -> list[dict[str, Any]]:
    return [
        _expect("pipeline_status_complete", _path(pipeline, "status"), "complete"),
        _expect("pipeline_dataset_records_built", _path(pipeline, "dataset_record_counts.records_built"), 14058),
        _expect("pipeline_dataset_records_total", _path(pipeline, "dataset_record_counts.records_total"), 51200),
        _expect("pipeline_training_records", _path(pipeline, "split_record_counts.training_records"), 11262),
        _expect("pipeline_validation_records", _path(pipeline, "split_record_counts.validation_records"), 2796),
        _expect("pipeline_scale_fit_records_used", _path(pipeline, "scale_fit_record_counts.fit_records_used"), 11262),
        _expect("pipeline_scale_training_records_seen", _path(pipeline, "scale_fit_record_counts.training_records_seen"), 11262),
        _expect("pipeline_scale_validation_records_seen", _path(pipeline, "scale_fit_record_counts.validation_records_seen"), 2796),
        _expect("pipeline_preflight_passed", _path(pipeline, "preflight_final_decision.passed"), True),
        _expect("pipeline_validator_passed", _path(pipeline, "validator_final_decision.passed"), True),
        _expect("pipeline_training_passed", _path(pipeline, "training_final_decision.passed"), True),
        _expect("pipeline_training_executed", _path(pipeline, "training_final_decision.training_executed"), True),
        _expect("pipeline_fixed_dp_candidate_reranking_only", _path(pipeline, "training_final_decision.fixed_dp_candidate_reranking_only"), True),
        _expect("pipeline_training_summary_hash_matches_file", _path(pipeline, "sha256.training_summary_json_sha256"), source_hashes.get("training_summary_sha256")),
    ]


def _training_checks(training: dict[str, Any]) -> list[dict[str, Any]]:
    seed = _path(training, "training.training_seed")
    weights_sum = _path(training, "training.weights_sum")
    weights_min = _path(training, "training.weights_min")
    return [
        _expect("training_status_complete", _path(training, "final_decision.status"), "dp_native_fallback_risk_static_camp_training_complete"),
        _expect("training_final_passed", _path(training, "final_decision.passed"), True),
        _expect("training_executed", _path(training, "final_decision.training_executed"), True),
        _expect("training_authorized_for_this_gate", _path(training, "final_decision.training_authorized"), True),
        _expect("training_fixed_dp_candidate_reranking_only", _path(training, "final_decision.fixed_dp_candidate_reranking_only"), True),
        _expect("training_fallback_only", _path(training, "final_decision.fallback_only_training"), True),
        _expect("training_num_candidates", _path(training, "training.num_candidates"), 8),
        _expect("training_num_atoms", _path(training, "training.num_atoms"), 14),
        _expect("training_atom_schema_version", _path(training, "training.atom_schema_version"), "dp_camp_v10_14d"),
        _expect("training_objective", _path(training, "training.objective"), "simplex_hinge_cvar_l2"),
        _expect("training_risk_type", _path(training, "training.risk_type"), "cvar"),
        _expect("training_score_expression", _path(training, "training.score_expression"), "score_k(w)=a_k^T w"),
        _expect("training_records", _path(training, "training.training_records"), 11262),
        _expect("training_validation_records", _path(training, "training.validation_records"), 2796),
        _check("training_seed_not_formal", seed not in FORMAL_SEEDS, seed, "not in {11,12,13}"),
        _check("training_weights_sum_simplex", _almost_equal(weights_sum, 1.0), weights_sum, 1.0),
        _check("training_weights_nonnegative", isinstance(weights_min, int | float) and weights_min >= 0.0, weights_min, ">= 0.0"),
    ]


def _nonpromotion_checks(nonpromotion: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("nonpromotion_audit_passed", _path(nonpromotion, "final_decision.passed"), True),
        _expect("nonpromotion_training_artifacts_nonpromotion", _path(nonpromotion, "final_decision.training_artifacts_nonpromotion"), True),
        _expect("nonpromotion_fixed_dp_candidate_reranking_only", _path(nonpromotion, "final_decision.fixed_dp_candidate_reranking_only"), True),
        _expect("nonpromotion_fallback_only_training_artifact", _path(nonpromotion, "final_decision.fallback_only_training_artifact"), True),
        _expect("nonpromotion_score_expression", _path(nonpromotion, "final_decision.score_expression"), "score_k(w)=a_k^T w"),
        _expect("nonpromotion_training_authorized_false", _path(nonpromotion, "final_decision.training_authorized"), False),
        _expect("nonpromotion_deployment_authorized_false", _path(nonpromotion, "final_decision.deployment_authorized"), False),
    ]


def _holdout_checks(holdout: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("holdout_audit_passed", _path(holdout, "final_decision.passed"), True),
        _expect("holdout_records_scope", _path(holdout, "final_decision.records_scope"), "validation_groups_only"),
        _expect("holdout_fallback_branch_only", _path(holdout, "final_decision.fallback_branch_only"), True),
        _expect("holdout_records_without_feasible_candidate_only", _path(holdout, "final_decision.records_without_feasible_candidate_only"), True),
        _expect("holdout_fixed_dp_candidate_reranking_only", _path(holdout, "final_decision.fixed_dp_candidate_reranking_only"), True),
        _expect("holdout_selection_rule", _path(holdout, "final_decision.selection_rule"), "argmin_k score_k(w)"),
        _expect("holdout_score_expression", _path(holdout, "final_decision.score_expression"), "score_k(w)=a_k^T w"),
        _expect("holdout_training_authorized_false", _path(holdout, "final_decision.training_authorized"), False),
        _expect("holdout_deployment_authorized_false", _path(holdout, "final_decision.deployment_authorized"), False),
    ]


def _cross_artifact_checks(payloads: dict[str, Any], source_hashes: dict[str, str]) -> list[dict[str, Any]]:
    pipeline = payloads["pipeline_summary"]
    nonpromotion = payloads["nonpromotion_audit"]
    training_hash = source_hashes.get("training_summary_sha256")
    return [
        _expect("cross_pipeline_training_summary_hash", _path(pipeline, "sha256.training_summary_json_sha256"), training_hash),
        _expect("cross_nonpromotion_training_summary_hash_match", _path(nonpromotion, "artifact_checks.training_summary_sha256_match"), True),
        _expect("cross_nonpromotion_weights_json_hash_match", _path(nonpromotion, "artifact_checks.weights_json_sha256_match"), True),
        _expect("cross_nonpromotion_weights_npy_hash_match", _path(nonpromotion, "artifact_checks.weights_npy_sha256_match"), True),
        _expect("cross_nonpromotion_atom_scales_hash_match", _path(nonpromotion, "artifact_checks.atom_scales_json_sha256_match"), True),
    ]


def _forbidden_flag_checks(payloads: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for artifact_name, payload in payloads.items():
        for path, value in _walk_dict(payload):
            key = path.rsplit(".", 1)[-1]
            if key in FORBIDDEN_TRUE_FLAGS:
                checks.append(
                    _check(
                        f"{artifact_name}_{path}_false",
                        value is False or value is None,
                        value,
                        False,
                    )
                )
    return checks


def _artifact_summary(payloads: dict[str, Any], source_hashes: dict[str, str]) -> dict[str, Any]:
    collection = payloads["collection_summary"]
    training = payloads["training_summary"]
    return {
        **source_hashes,
        "records_total": _path(collection, "records_total"),
        "records_without_feasible_candidate": _path(collection, "records_without_feasible_candidate"),
        "records_with_feasible_candidate": _path(collection, "records_with_feasible_candidate"),
        "training_records": _path(training, "training.training_records"),
        "validation_records": _path(training, "training.validation_records"),
        "num_candidates": _path(training, "training.num_candidates"),
        "num_atoms": _path(training, "training.num_atoms"),
        "atom_schema_version": _path(training, "training.atom_schema_version"),
        "score_expression": _path(training, "training.score_expression"),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "result_review_ready": passed,
        "promotion_decision_plan_authorized": passed,
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
        "failed_checks": failed,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _path(payload: dict[str, Any], dotted: str) -> Any:
    value: Any = payload
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _walk_dict(payload: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            dotted = f"{prefix}.{key}" if prefix else str(key)
            rows.append((dotted, value))
            rows.extend(_walk_dict(value, dotted))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            rows.extend(_walk_dict(value, f"{prefix}.{index}"))
    return rows


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable_value(observed),
        "expected": _stable_value(expected),
    }


def _stable_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _almost_equal(left: Any, right: float, tol: float = 1e-9) -> bool:
    return isinstance(left, int | float) and abs(float(left) - right) <= tol


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


if __name__ == "__main__":
    raise SystemExit(main())
