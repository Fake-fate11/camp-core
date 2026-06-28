#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dp_camp_v13_promotion_evidence_package_preflight_v1"
DISABLED_STATUS = "dp_camp_v13_promotion_evidence_package_preflight_default_off_disabled"
READY_STATUS = "dp_camp_v13_promotion_evidence_package_preflight_ready"
REJECT_STATUS = "dp_camp_v13_promotion_evidence_package_preflight_rejected"
SOURCE_PLAN_STATUS = "dp_camp_v13_promotion_decision_plan_ready"
SOURCE_PLAN_AUTHORIZED_NEXT_WORK = "dp_camp_v13_promotion_evidence_package_preflight_only"
RESULT_REVIEW_STATUS = "dp_camp_v13_offline_nonpromotion_static_reranker_result_review_ready"
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_static_integration_contract_plan_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = {11, 12, 13}
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
DEFAULT_EXPECTED_COUNTS = {
    "collection_selection_log_count": 512,
    "collection_expected_replay_commands": 512,
    "collection_records_total": 51200,
    "collection_records_without_feasible_candidate": 14058,
    "collection_records_with_feasible_candidate": 37142,
    "pipeline_dataset_records_built": 14058,
    "pipeline_dataset_records_total": 51200,
    "pipeline_training_records": 11262,
    "pipeline_validation_records": 2796,
    "pipeline_scale_fit_records_used": 11262,
    "training_records": 11262,
    "training_validation_records": 2796,
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
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "production_selector_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off, read-only evidence-package preflight for the v13 "
            "DP-CAMP static reranker. It validates existing artifacts and "
            "emits a manifest plus future default-off integration evidence "
            "requirements; it does not promote, deploy, train, replay, "
            "generate candidates, or modify DP."
        )
    )
    parser.add_argument("--promotion_decision_plan_json", type=Path, required=True)
    parser.add_argument("--result_review_json", type=Path, required=True)
    parser.add_argument("--collection_summary_json", type=Path, required=True)
    parser.add_argument("--pipeline_summary_json", type=Path, required=True)
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--weights_json", type=Path, required=True)
    parser.add_argument("--weights_npy", type=Path, required=True)
    parser.add_argument("--atom_scales_json", type=Path, required=True)
    parser.add_argument("--nonpromotion_audit_json", type=Path, required=True)
    parser.add_argument("--holdout_audit_json", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    for name, default in DEFAULT_EXPECTED_COUNTS.items():
        parser.add_argument(f"--expected_{name}", type=int, default=default)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_promotion_evidence_package_preflight",
        action="store_true",
        help="Explicit opt-in for this read-only preflight gate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        promotion_decision_plan_json=args.promotion_decision_plan_json,
        result_review_json=args.result_review_json,
        collection_summary_json=args.collection_summary_json,
        pipeline_summary_json=args.pipeline_summary_json,
        training_summary_json=args.training_summary_json,
        weights_json=args.weights_json,
        weights_npy=args.weights_npy,
        atom_scales_json=args.atom_scales_json,
        nonpromotion_audit_json=args.nonpromotion_audit_json,
        holdout_audit_json=args.holdout_audit_json,
        current_camp_head=args.current_camp_head,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v13_promotion_evidence_package_preflight,
        expected_counts={
            name: getattr(args, f"expected_{name}") for name in DEFAULT_EXPECTED_COUNTS
        },
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
    promotion_decision_plan_json: Path,
    result_review_json: Path,
    collection_summary_json: Path,
    pipeline_summary_json: Path,
    training_summary_json: Path,
    weights_json: Path,
    weights_npy: Path,
    atom_scales_json: Path,
    nonpromotion_audit_json: Path,
    holdout_audit_json: Path,
    current_camp_head: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
    expected_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    expected = dict(DEFAULT_EXPECTED_COUNTS)
    if expected_counts:
        expected.update(expected_counts)
    paths = {
        "promotion_decision_plan": promotion_decision_plan_json,
        "result_review": result_review_json,
        "collection_summary": collection_summary_json,
        "pipeline_summary": pipeline_summary_json,
        "training_summary": training_summary_json,
        "weights_json": weights_json,
        "weights_npy": weights_npy,
        "atom_scales_json": atom_scales_json,
        "nonpromotion_audit": nonpromotion_audit_json,
        "holdout_audit": holdout_audit_json,
    }
    report = _empty_report(
        enabled=enabled,
        label=label,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    payloads: dict[str, Any] = {}
    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
    ]
    for name, path in paths.items():
        checks.extend(_artifact_file_checks(name, path))
        if path.is_file():
            report["source_hashes"][f"{name}_sha256"] = _sha256(path)
        if path.is_file() and name != "weights_npy":
            loaded = _load_json(path)
            payloads[name] = loaded if isinstance(loaded, dict) else {}
            checks.append(
                _check(
                    f"{name}_json_object",
                    isinstance(loaded, dict),
                    type(loaded).__name__,
                    "dict",
                )
            )
        else:
            payloads[name] = {}

    checks.extend(_promotion_plan_checks(payloads["promotion_decision_plan"]))
    checks.extend(_result_review_checks(payloads["result_review"], expected))
    checks.extend(_collection_checks(payloads["collection_summary"], expected))
    checks.extend(_pipeline_checks(payloads["pipeline_summary"], report["source_hashes"], expected))
    checks.extend(_training_checks(payloads["training_summary"], expected))
    checks.extend(_weights_checks(payloads["weights_json"]))
    checks.extend(_atom_scales_checks(payloads["atom_scales_json"]))
    checks.extend(_nonpromotion_checks(payloads["nonpromotion_audit"]))
    checks.extend(_holdout_checks(payloads["holdout_audit"]))
    checks.extend(_cross_artifact_checks(payloads, report["source_hashes"]))

    passed = all(check["passed"] for check in checks)
    report["artifact_manifest"] = _artifact_manifest(paths, report["source_hashes"])
    report["static_integration_contract"] = _static_integration_contract()
    report["default_off_shadow_selector_wiring_preflight"] = (
        _default_off_shadow_selector_wiring_preflight()
    )
    report["latency_determinism_missing_candidate_preflight"] = (
        _latency_determinism_missing_candidate_preflight()
    )
    report["closed_loop_evaluation_preflight"] = _closed_loop_evaluation_preflight()
    report["metrics_and_thresholds_preflight"] = _metrics_and_thresholds_preflight()
    report["rollback_observability_preflight"] = _rollback_observability_preflight()
    report["independent_safety_claim_gate"] = _independent_safety_claim_gate()
    report["preflight_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    manifest = report.get("artifact_manifest", [])
    lines = [
        "# DP-CAMP V13 Promotion Evidence Package Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Training authorized: `{decision['training_authorized']}`",
        f"- Replay authorized: `{decision['replay_execution_authorized']}`",
        f"- Candidate generation authorized: `{decision['candidate_generation_authorized']}`",
        f"- DP modification authorized: `{decision['dp_modification_authorized']}`",
        "",
        "## Artifact Manifest",
        "",
        "| Artifact | SHA-256 | Role |",
        "| --- | --- | --- |",
    ]
    for item in manifest:
        lines.append(
            f"| `{item['name']}` | `{item['sha256']}` | `{item['role']}` |"
        )
    lines.extend(
        [
            "",
            "## Static Contract",
            "",
            report["static_integration_contract"]["summary"],
            "",
            "## Remaining Evidence Before Any Promotion",
            "",
        ]
    )
    for key in [
        "default_off_shadow_selector_wiring_preflight",
        "latency_determinism_missing_candidate_preflight",
        "closed_loop_evaluation_preflight",
        "metrics_and_thresholds_preflight",
        "rollback_observability_preflight",
        "independent_safety_claim_gate",
    ]:
        item = report.get(key, {})
        lines.append(f"- `{key}`: `{item.get('status')}`")
    lines.extend(
        [
            "",
            "This preflight does not promote atoms or selectors, deploy a "
            "checkpoint, train CAMP, run replay, generate candidates, modify "
            "DP, change an online selector, or authorize safety/CAMP-over-DP "
            "claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report.get("preflight_checks", []):
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
    current_dp_head: str,
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "name": "dp_camp_v13_promotion_evidence_package_preflight",
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "read_only_existing_artifacts": True,
            "preflight_only": True,
            "current_camp_head": current_camp_head,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "CAMP remains a static reranker over fixed DP candidate "
                "trajectories. This preflight only checks existing artifacts "
                "and evidence requirements; it preserves score_k(w)=a_k^T w "
                "and convex simplex/CVaR/L2 master structure."
            ),
        },
        "source_hashes": {},
        "artifact_manifest": [],
        "static_integration_contract": {},
        "default_off_shadow_selector_wiring_preflight": {},
        "latency_determinism_missing_candidate_preflight": {},
        "closed_loop_evaluation_preflight": {},
        "metrics_and_thresholds_preflight": {},
        "rollback_observability_preflight": {},
        "independent_safety_claim_gate": {},
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "preflight_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "promotion_evidence_package_preflight_ready": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "production_selector_change_authorized": False,
            "failed_checks": [],
        },
    }


def _artifact_file_checks(name: str, path: Path) -> list[dict[str, Any]]:
    checks = [_check(f"{name}_exists", path.is_file(), str(path), "existing file")]
    if name != "weights_npy" and path.is_file():
        checks.append(_check(f"{name}_has_json_suffix", path.suffix == ".json", path.suffix, ".json"))
    if name == "weights_npy" and path.is_file():
        checks.append(_check("weights_npy_has_npy_suffix", path.suffix == ".npy", path.suffix, ".npy"))
    return checks


def _promotion_plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(plan.get("final_decision"))
    package = _dict(plan.get("evidence_package_preflight"))
    return [
        _expect("promotion_plan_status_ready", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("promotion_plan_passed", decision.get("passed"), True),
        _expect(
            "promotion_plan_authorizes_this_preflight",
            decision.get("authorized_next_work"),
            SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
        ),
        _expect(
            "promotion_plan_preflight_authorized",
            decision.get("evidence_package_preflight_authorized"),
            True,
        ),
        _expect("promotion_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect(
            "promotion_plan_recommendation_nonpromotion",
            _path(plan, "promotion_decision_plan.recommendation"),
            "do_not_promote_from_current_evidence_alone",
        ),
        _expect(
            "promotion_plan_preflight_status_planned",
            package.get("status"),
            "planned_not_executed",
        ),
        *[
            _expect(f"promotion_plan_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
        ],
    ]


def _result_review_checks(
    review: dict[str, Any], expected_counts: dict[str, int]
) -> list[dict[str, Any]]:
    decision = _dict(review.get("final_decision"))
    return [
        _expect("result_review_status_ready", decision.get("status"), RESULT_REVIEW_STATUS),
        _expect("result_review_passed", decision.get("passed"), True),
        _expect("result_review_failed_checks_empty", decision.get("failed_checks"), []),
        _expect(
            "result_review_records_total",
            _path(review, "artifact_summary.records_total"),
            expected_counts["pipeline_dataset_records_total"],
        ),
        _expect(
            "result_review_records_without_feasible_candidate",
            _path(review, "artifact_summary.records_without_feasible_candidate"),
            expected_counts["pipeline_dataset_records_built"],
        ),
        _expect(
            "result_review_training_records",
            _path(review, "artifact_summary.training_records"),
            expected_counts["training_records"],
        ),
        _expect(
            "result_review_validation_records",
            _path(review, "artifact_summary.validation_records"),
            expected_counts["training_validation_records"],
        ),
        _expect("result_review_num_candidates", _path(review, "artifact_summary.num_candidates"), 8),
        _expect("result_review_num_atoms", _path(review, "artifact_summary.num_atoms"), 14),
        _expect(
            "result_review_score_expression",
            _path(review, "artifact_summary.score_expression"),
            SCORE_EXPRESSION,
        ),
        *[
            _expect(f"result_review_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
            if name in decision
        ],
    ]


def _collection_checks(
    collection: dict[str, Any], expected_counts: dict[str, int]
) -> list[dict[str, Any]]:
    records_total = collection.get("records_total")
    return [
        _expect("collection_status_complete", collection.get("status"), "complete"),
        _expect(
            "collection_selection_log_count",
            collection.get("selection_log_count"),
            expected_counts["collection_selection_log_count"],
        ),
        _expect(
            "collection_expected_replay_commands",
            collection.get("expected_replay_commands"),
            expected_counts["collection_expected_replay_commands"],
        ),
        _expect("collection_failed_replay_commands", collection.get("failed_replay_commands"), 0),
        _expect("collection_records_total", records_total, expected_counts["collection_records_total"]),
        _expect(
            "collection_records_without_feasible_candidate",
            collection.get("records_without_feasible_candidate"),
            expected_counts["collection_records_without_feasible_candidate"],
        ),
        _expect(
            "collection_records_with_feasible_candidate",
            collection.get("records_with_feasible_candidate"),
            expected_counts["collection_records_with_feasible_candidate"],
        ),
        _expect("collection_records_bad_feasible_mask", collection.get("records_bad_feasible_mask"), 0),
        _expect("collection_candidate_counts", collection.get("candidate_counts"), [8]),
        _expect("collection_formal_seed_path_matches", collection.get("formal_seed_path_matches"), 0),
        _expect("collection_provenance_present_records", collection.get("provenance_present_records"), records_total),
        _expect("collection_provenance_payload_valid_records", collection.get("provenance_payload_valid_records"), records_total),
        _expect("collection_provenance_prepost_equal_records", collection.get("provenance_prepost_equal_records"), records_total),
        _expect(
            "collection_provenance_reference_blend_separated_records",
            collection.get("provenance_reference_blend_separated_records"),
            records_total,
        ),
        _expect("collection_contract_unique_values", collection.get("contract_unique_values"), [[8, False, None, False]]),
        _expect("collection_fixed_dp_candidate_generation_authorized", collection.get("fixed_dp_candidate_generation_authorized"), True),
        _expect("collection_candidate_generation_by_camp_authorized", collection.get("candidate_generation_by_camp_authorized"), False),
        _expect("collection_dp_modification_authorized", collection.get("dp_modification_authorized"), False),
        _expect("collection_camp_training_executed", collection.get("camp_training_executed"), False),
    ]


def _pipeline_checks(
    pipeline: dict[str, Any], hashes: dict[str, str], expected_counts: dict[str, int]
) -> list[dict[str, Any]]:
    return [
        _expect("pipeline_status_complete", pipeline.get("status"), "complete"),
        _expect(
            "pipeline_dataset_records_built",
            _path(pipeline, "dataset_record_counts.records_built"),
            expected_counts["pipeline_dataset_records_built"],
        ),
        _expect(
            "pipeline_dataset_records_total",
            _path(pipeline, "dataset_record_counts.records_total"),
            expected_counts["pipeline_dataset_records_total"],
        ),
        _expect(
            "pipeline_training_records",
            _path(pipeline, "split_record_counts.training_records"),
            expected_counts["pipeline_training_records"],
        ),
        _expect(
            "pipeline_validation_records",
            _path(pipeline, "split_record_counts.validation_records"),
            expected_counts["pipeline_validation_records"],
        ),
        _expect(
            "pipeline_scale_fit_records_used",
            _path(pipeline, "scale_fit_record_counts.fit_records_used"),
            expected_counts["pipeline_scale_fit_records_used"],
        ),
        _expect("pipeline_preflight_passed", _path(pipeline, "preflight_final_decision.passed"), True),
        _expect("pipeline_validator_passed", _path(pipeline, "validator_final_decision.passed"), True),
        _expect("pipeline_training_passed", _path(pipeline, "training_final_decision.passed"), True),
        _expect("pipeline_fixed_dp_candidate_reranking_only", _path(pipeline, "training_final_decision.fixed_dp_candidate_reranking_only"), True),
        _expect(
            "pipeline_training_summary_hash_matches_file",
            _path(pipeline, "sha256.training_summary_json_sha256"),
            hashes.get("training_summary_sha256"),
        ),
    ]


def _training_checks(
    training: dict[str, Any], expected_counts: dict[str, int]
) -> list[dict[str, Any]]:
    seed = _path(training, "training.training_seed")
    weights_sum = _path(training, "training.weights_sum")
    weights_min = _path(training, "training.weights_min")
    return [
        _expect("training_status_complete", _path(training, "final_decision.status"), "dp_native_fallback_risk_static_camp_training_complete"),
        _expect("training_final_passed", _path(training, "final_decision.passed"), True),
        _expect("training_fixed_dp_candidate_reranking_only", _path(training, "final_decision.fixed_dp_candidate_reranking_only"), True),
        _expect("training_fallback_only", _path(training, "final_decision.fallback_only_training"), True),
        _expect("training_num_candidates", _path(training, "training.num_candidates"), 8),
        _expect("training_num_atoms", _path(training, "training.num_atoms"), 14),
        _expect("training_atom_schema_version", _path(training, "training.atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("training_objective", _path(training, "training.objective"), "simplex_hinge_cvar_l2"),
        _expect("training_risk_type", _path(training, "training.risk_type"), "cvar"),
        _expect("training_score_expression", _path(training, "training.score_expression"), SCORE_EXPRESSION),
        _expect(
            "training_records",
            _path(training, "training.training_records"),
            expected_counts["training_records"],
        ),
        _expect(
            "training_validation_records",
            _path(training, "training.validation_records"),
            expected_counts["training_validation_records"],
        ),
        _check("training_seed_not_formal", seed not in FORMAL_SEEDS, seed, "not in {11,12,13}"),
        _check("training_weights_sum_simplex", _almost_equal(weights_sum, 1.0), weights_sum, 1.0),
        _check("training_weights_nonnegative", isinstance(weights_min, (int, float)) and weights_min >= 0.0, weights_min, ">= 0.0"),
    ]


def _weights_checks(weights: dict[str, Any]) -> list[dict[str, Any]]:
    values = weights.get("weights")
    atom_names = weights.get("atom_names")
    weights_sum = sum(values) if _is_number_list(values) else None
    weights_min = min(values) if _is_number_list(values) and values else None
    return [
        _expect("weights_atom_schema_version", weights.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("weights_score_expression", weights.get("score_expression"), SCORE_EXPRESSION),
        _expect("weights_fallback_only", weights.get("fallback_only"), True),
        _expect("weights_selector_promotion_executed", weights.get("selector_promotion_executed"), False),
        _check("weights_length_14", isinstance(values, list) and len(values) == 14, len(values) if isinstance(values, list) else None, 14),
        _check("weights_atom_names_length_14", isinstance(atom_names, list) and len(atom_names) == 14, len(atom_names) if isinstance(atom_names, list) else None, 14),
        _check("weights_sum_simplex", _almost_equal(weights_sum, 1.0), weights_sum, 1.0),
        _check("weights_nonnegative", isinstance(weights_min, (int, float)) and weights_min >= 0.0, weights_min, ">= 0.0"),
    ]


def _atom_scales_checks(scales: dict[str, Any]) -> list[dict[str, Any]]:
    values = scales.get("scales")
    atom_names = scales.get("atom_names")
    return [
        _expect("atom_scales_schema_version", scales.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _check("atom_scales_length_14", isinstance(values, list) and len(values) == 14, len(values) if isinstance(values, list) else None, 14),
        _check("atom_scales_atom_names_length_14", isinstance(atom_names, list) and len(atom_names) == 14, len(atom_names) if isinstance(atom_names, list) else None, 14),
        _check(
            "atom_scales_positive",
            _is_number_list(values) and min(values) > 0.0,
            min(values) if _is_number_list(values) and values else None,
            "> 0.0",
        ),
    ]


def _nonpromotion_checks(audit: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("nonpromotion_audit_passed", _path(audit, "final_decision.passed"), True),
        _expect("nonpromotion_training_artifacts_nonpromotion", _path(audit, "final_decision.training_artifacts_nonpromotion"), True),
        _expect("nonpromotion_fixed_dp_candidate_reranking_only", _path(audit, "final_decision.fixed_dp_candidate_reranking_only"), True),
        _expect("nonpromotion_fallback_only_training_artifact", _path(audit, "final_decision.fallback_only_training_artifact"), True),
        _expect("nonpromotion_score_expression", _path(audit, "final_decision.score_expression"), SCORE_EXPRESSION),
        _expect("nonpromotion_training_authorized", _path(audit, "final_decision.training_authorized"), False),
        _expect("nonpromotion_deployment_authorized", _path(audit, "final_decision.deployment_authorized"), False),
    ]


def _holdout_checks(audit: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("holdout_audit_passed", _path(audit, "final_decision.passed"), True),
        _expect("holdout_records_scope", _path(audit, "final_decision.records_scope"), "validation_groups_only"),
        _expect("holdout_fallback_branch_only", _path(audit, "final_decision.fallback_branch_only"), True),
        _expect("holdout_records_without_feasible_candidate_only", _path(audit, "final_decision.records_without_feasible_candidate_only"), True),
        _expect("holdout_fixed_dp_candidate_reranking_only", _path(audit, "final_decision.fixed_dp_candidate_reranking_only"), True),
        _expect("holdout_selection_rule", _path(audit, "final_decision.selection_rule"), "argmin_k score_k(w)"),
        _expect("holdout_score_expression", _path(audit, "final_decision.score_expression"), SCORE_EXPRESSION),
        _expect("holdout_training_authorized", _path(audit, "final_decision.training_authorized"), False),
        _expect("holdout_deployment_authorized", _path(audit, "final_decision.deployment_authorized"), False),
    ]


def _cross_artifact_checks(payloads: dict[str, Any], hashes: dict[str, str]) -> list[dict[str, Any]]:
    training = payloads["training_summary"]
    weights = payloads["weights_json"]
    atom_scales = payloads["atom_scales_json"]
    return [
        _expect("training_output_weights_json_hash_matches_file", _path(training, "output_artifacts.weights_json_sha256"), hashes.get("weights_json_sha256")),
        _expect("training_output_weights_npy_hash_matches_file", _path(training, "output_artifacts.weights_npy_sha256"), hashes.get("weights_npy_sha256")),
        _expect("training_output_atom_scales_hash_matches_file", _path(training, "output_artifacts.atom_scales_json_sha256"), hashes.get("atom_scales_json_sha256")),
        _expect("weights_source_dataset_hash_matches_pipeline", _path(weights, "source_hashes.dataset"), _path(payloads["pipeline_summary"], "sha256.dataset_json_sha256")),
        _expect("weights_source_scale_manifest_hash_matches_pipeline", _path(weights, "source_hashes.scale_manifest"), _path(payloads["pipeline_summary"], "sha256.scale_manifest_json_sha256")),
        _expect("atom_scales_source_manifest_hash_matches_pipeline", atom_scales.get("source_scale_manifest_sha256"), _path(payloads["pipeline_summary"], "sha256.scale_manifest_json_sha256")),
        _expect("promotion_plan_source_records_match_review", _path(payloads["promotion_decision_plan"], "source_summary.records_total"), _path(payloads["result_review"], "artifact_summary.records_total")),
        _expect("promotion_plan_source_score_expression_match_review", _path(payloads["promotion_decision_plan"], "source_summary.score_expression"), _path(payloads["result_review"], "artifact_summary.score_expression")),
    ]


def _artifact_manifest(paths: dict[str, Path], hashes: dict[str, str]) -> list[dict[str, Any]]:
    roles = {
        "promotion_decision_plan": "source authorization for this read-only preflight",
        "result_review": "reviewed v13 offline nonpromotion reranker artifact summary",
        "collection_summary": "fixed DP candidate-set collection contract",
        "pipeline_summary": "dataset, split, scale, preflight, and training pipeline contract",
        "training_summary": "static CAMP reranker training summary",
        "weights_json": "human-readable static CAMP simplex weights",
        "weights_npy": "binary static CAMP weights artifact",
        "atom_scales_json": "atom scaling manifest used by static CAMP weights",
        "nonpromotion_audit": "post-training nonpromotion artifact audit",
        "holdout_audit": "development holdout acceptance audit",
    }
    manifest = []
    for name, path in paths.items():
        manifest.append(
            {
                "name": name,
                "path": str(path),
                "sha256": hashes.get(f"{name}_sha256"),
                "role": roles[name],
                "immutable_for_promotion_decision": True,
            }
        )
    return manifest


def _static_integration_contract() -> dict[str, Any]:
    return {
        "status": "preflight_ready_contract_pinned",
        "summary": (
            "Future integration may only run CAMP as a default-off shadow "
            "reranker over the current tick's fixed K=8 DP candidate tensor, "
            "selecting by argmin_k score_k(w)=a_k^T w. It must not generate, "
            "rewrite, blend, guide, append, delete, or postprocess trajectories."
        ),
        "dp_head": FIXED_DP_HEAD,
        "candidate_count": 8,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "score_expression": SCORE_EXPRESSION,
        "allowed_operation": "argmin_k score_k(w)",
        "candidate_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "simplex_master_convex": True,
        "cvar_master_convex": True,
        "l2_master_convex": True,
    }


def _default_off_shadow_selector_wiring_preflight() -> dict[str, Any]:
    return {
        "status": "future_static_contract_plan_required_before_implementation",
        "default_off_required": True,
        "kill_switch_required": True,
        "shadow_only_required_before_any_online_selector_change": True,
        "production_selector_change_authorized": False,
        "implementation_authorized": False,
    }


def _latency_determinism_missing_candidate_preflight() -> dict[str, Any]:
    return {
        "status": "future_measurement_required",
        "latency_claim_authorized": False,
        "determinism_claim_authorized": False,
        "missing_candidate_behavior_must_fallback_to_dp_top1": True,
        "candidate_count_drift_is_no_go": True,
    }


def _closed_loop_evaluation_preflight() -> dict[str, Any]:
    return {
        "status": "future_nonformal_design_required",
        "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "safety_claim_authorized": False,
    }


def _metrics_and_thresholds_preflight() -> dict[str, Any]:
    return {
        "status": "thresholds_must_be_predeclared_before_evaluation",
        "allowed_claim_scope_now": "artifact_integrity_only",
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "required_no_go_thresholds": [
            "dp_head_must_equal_fixed_tieriv_commit",
            "candidate_counts_must_equal_8",
            "formal_seed_path_matches_must_equal_0",
            "score_expression_must_remain_affine",
            "selector_must_remain_default_off_until_explicit_gate",
        ],
    }


def _rollback_observability_preflight() -> dict[str, Any]:
    return {
        "status": "future_runtime_contract_required",
        "rollback_to_dp_top1_required": True,
        "runtime_observability_required": True,
        "artifact_hash_logging_required": True,
        "deployment_authorized": False,
    }


def _independent_safety_claim_gate() -> dict[str, Any]:
    return {
        "status": "required_before_any_safety_language",
        "current_safety_benefit_claim_authorized": False,
        "current_camp_over_dp_top1_claim_authorized": False,
        "independent_review_required": True,
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "promotion_evidence_package_preflight_ready": passed,
        "immutable_artifact_manifest_ready": passed,
        "static_integration_contract_pinned": passed,
        "default_off_shadow_selector_contract_plan_authorized": passed,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "production_selector_change_authorized": False,
        "failed_checks": failed,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(payload: dict[str, Any], dotted: str) -> Any:
    value: Any = payload
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


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
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_number_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, (int, float)) for item in value)


def _almost_equal(left: Any, right: float, tol: float = 1e-9) -> bool:
    return isinstance(left, (int, float)) and abs(float(left) - right) <= tol


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


if __name__ == "__main__":
    raise SystemExit(main())
