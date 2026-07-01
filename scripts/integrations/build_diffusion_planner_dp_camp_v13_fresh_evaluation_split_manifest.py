#!/usr/bin/env python3
"""Manifest-only builder for the v13 fresh evaluation split gate.

This implementation consumes fixed review, training-manifest, and registry
artifacts and writes manifests for a later fresh evaluation split preflight. It
does not run Diffusion Planner, generate candidates, select executable
trajectories, run replay, train CAMP, modify DP, promote artifacts, deploy, or
make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dp_camp_v13_fresh_evaluation_split_manifest_builder_v1"
DISABLED_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_manifest_builder_default_off_disabled"
)
READY_STATUS = "dp_camp_v13_fresh_evaluation_split_manifest_builder_complete"
REJECT_STATUS = "dp_camp_v13_fresh_evaluation_split_manifest_builder_rejected"
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_static_contract_review_v1"
)
SOURCE_REVIEW_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_"
    "failure_remediation_fresh_evaluation_split_implementation_static_contract_review_passed"
)
TRAINING_SELECTION_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_selection_manifest_v1"
)
SOURCE_REGISTRY_SCHEMA_VERSION = (
    "dp_camp_v13_current_source_result_review_source_registry_manifest_v1"
)
FRESH_SCOPE_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_scope_manifest_v1"
)
NONOVERLAP_REGISTRY_REPORT_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_nonoverlap_registry_report_v1"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_implementation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_implementation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_post_implementation_static_contract_"
    "review_only"
)
EXPECTED_BUILDER_SCRIPT = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_manifest.py"
)
EXPECTED_BUILDER_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
    "fresh_evaluation_split_manifest_builder.py"
)
TARGET_SELECTION_LOGS = 32
TARGET_RECORDS = 3200
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
EXPECTED_ROUTES_MINIMUM = 4
EXPECTED_SEEDS_MINIMUM = 2
EXPECTED_ROUTE_TL_BUCKETS_MINIMUM = 8
TRAINING_SELECTION_LOGS = 416
TRAINING_RECORDS = 41600
FORMAL_SEEDS = {11, 12, 13}
OUTPUT_FILES = (
    "fresh_evaluation_split_scope_manifest.json",
    "fresh_evaluation_split_nonoverlap_registry_report.json",
    "run_fresh_evaluation_split_preflight.sh",
)
SHA256SUMS_NAME = "SHA256SUMS.txt"

REQUIRED_BEHAVIOR = (
    "load_full_76c2_training_manifest_before_selecting_any_split_member",
    "load_recovered_missing_prior_registry_before_selecting_any_split_member",
    "load_rejected_evaluation_source_registry_before_selecting_any_split_member",
    "fail_closed_when_any_required_registry_is_missing_or_empty",
    "prove_zero_candidate_tensor_hash_intersection",
    "prove_zero_path_signature_intersection",
    "prove_zero_record_identity_intersection",
    "prove_zero_split_manifest_root_intersection",
    "exclude_formal_seeds_11_12_13_and_full36",
    "require_default_off_shadow_selector_and_executed_dp_top1",
    "forbid_camp_candidate_generation_or_trajectory_modification",
    "forbid_reference_blend_guidance_postprocess_postselection",
    "forbid_closed_loop_outcomes_as_training_or_online_input",
    "write_immutable_sha256_manifest_for_all_outputs",
)

BLOCKED_SOURCE_FLAGS = (
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "replay_execution_authorized_next",
    "fixed_dp_candidate_generation_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)

AUDIT_FALSE_FLAGS = (
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_by_current_boundary",
    "runtime_shadow_selector_execution_authorized",
    "replay_execution_authorized_by_current_boundary",
    "fixed_dp_candidate_generation_authorized_by_current_boundary",
    "candidate_generation_by_camp_authorized_by_current_boundary",
    "trajectory_generation_by_camp_authorized_by_current_boundary",
    "trajectory_modification_by_camp_authorized_by_current_boundary",
    "dp_modification_authorized_by_current_boundary",
    "formal_seed_11_12_13_execution_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
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
    parser = argparse.ArgumentParser(
        description=(
            "Default-off manifest-only builder for the v13 fresh evaluation "
            "split. It writes manifests but does not run DP, replay, or train."
        )
    )
    parser.add_argument("--implementation_static_contract_review_json", type=Path, required=True)
    parser.add_argument("--expected_static_contract_review_sha256", required=True)
    parser.add_argument("--training_selection_manifest_json", type=Path, required=True)
    parser.add_argument("--recovered_prior_registry_manifest_json", type=Path, required=True)
    parser.add_argument("--rejected_evaluation_source_registry_manifest_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument(
        "--enable_v13_fresh_evaluation_split_manifest_builder",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_manifest_report(
        implementation_static_contract_review_json=args.implementation_static_contract_review_json,
        expected_static_contract_review_sha256=args.expected_static_contract_review_sha256,
        training_selection_manifest_json=args.training_selection_manifest_json,
        recovered_prior_registry_manifest_json=args.recovered_prior_registry_manifest_json,
        rejected_evaluation_source_registry_manifest_json=(
            args.rejected_evaluation_source_registry_manifest_json
        ),
        v13_audit_md=args.v13_audit_md,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_md=args.output_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        enabled=args.enable_v13_fresh_evaluation_split_manifest_builder,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    if report["final_decision"]["manifest_files_written"]:
        _write_sha256sums(args.output_dir, list(OUTPUT_FILES))
        report["output_hashes"]["sha256sums_txt_sha256"] = _sha256(
            args.output_dir / SHA256SUMS_NAME
        )
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["status"] != REJECT_STATUS else 1


def build_manifest_report(
    *,
    implementation_static_contract_review_json: Path,
    expected_static_contract_review_sha256: str,
    training_selection_manifest_json: Path,
    recovered_prior_registry_manifest_json: Path,
    rejected_evaluation_source_registry_manifest_json: Path,
    v13_audit_md: Path,
    output_dir: Path,
    output_json: Path,
    output_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        implementation_static_contract_review_json=implementation_static_contract_review_json,
        training_selection_manifest_json=training_selection_manifest_json,
        recovered_prior_registry_manifest_json=recovered_prior_registry_manifest_json,
        rejected_evaluation_source_registry_manifest_json=(
            rejected_evaluation_source_registry_manifest_json
        ),
        output_dir=output_dir,
        output_json=output_json,
        output_md=output_md,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
        authorized_next_work=authorized_next_work,
    )
    if not enabled:
        return report

    audit_text = _read_text_if_exists(v13_audit_md)
    checks = [
        _check(
            "camp_head_matches_origin_main",
            current_camp_head == current_camp_origin_main,
            current_camp_head,
            current_camp_origin_main,
        ),
        _check(
            "current_dp_head_fixed",
            current_dp_head == required_dp_head == FIXED_DP_HEAD,
            current_dp_head,
            FIXED_DP_HEAD,
        ),
        _check(
            "expected_static_contract_review_sha256_valid",
            _is_sha256(expected_static_contract_review_sha256),
            expected_static_contract_review_sha256,
            "sha256",
        ),
        _check("output_dir_is_not_file", not output_dir.is_file(), str(output_dir), "not a file"),
        _check(
            "output_json_under_output_dir",
            _is_relative_to(output_json, output_dir),
            str(output_json),
            str(output_dir),
        ),
        _check(
            "output_md_under_output_dir",
            _is_relative_to(output_md, output_dir),
            str(output_md),
            str(output_dir),
        ),
        _check(
            "latest_audit_status_authorizes_builder",
            _latest_value(audit_text, "current_v13_status") == LATEST_AUDIT_STATUS,
            _latest_value(audit_text, "current_v13_status"),
            LATEST_AUDIT_STATUS,
        ),
        _check(
            "latest_audit_target_authorizes_builder",
            _latest_value(audit_text, "next_work_target") == authorized_current_work,
            _latest_value(audit_text, "next_work_target"),
            authorized_current_work,
        ),
    ]
    checks.extend(_audit_boundary_checks(audit_text))

    review_payload, review_checks = _load_source_json(
        implementation_static_contract_review_json,
        "implementation_static_contract_review_json",
    )
    training_payload, training_checks = _load_source_json(
        training_selection_manifest_json,
        "training_selection_manifest_json",
    )
    recovered_payload, recovered_checks = _load_source_json(
        recovered_prior_registry_manifest_json,
        "recovered_prior_registry_manifest_json",
    )
    rejected_payload, rejected_checks = _load_source_json(
        rejected_evaluation_source_registry_manifest_json,
        "rejected_evaluation_source_registry_manifest_json",
    )
    checks.extend(review_checks)
    checks.extend(training_checks)
    checks.extend(recovered_checks)
    checks.extend(rejected_checks)

    if implementation_static_contract_review_json.is_file():
        review_sha = _sha256(implementation_static_contract_review_json)
        report["source_hashes"]["implementation_static_contract_review_json_sha256"] = review_sha
        checks.append(
            _check(
                "static_contract_review_sha256_matches_expected",
                review_sha == expected_static_contract_review_sha256.lower(),
                review_sha,
                expected_static_contract_review_sha256.lower(),
            )
        )
    for name, path in (
        ("training_selection_manifest_json", training_selection_manifest_json),
        ("recovered_prior_registry_manifest_json", recovered_prior_registry_manifest_json),
        (
            "rejected_evaluation_source_registry_manifest_json",
            rejected_evaluation_source_registry_manifest_json,
        ),
    ):
        if path.is_file():
            report["source_hashes"][f"{name}_sha256"] = _sha256(path)

    review_summary = _review_summary(review_payload)
    training_summary = _training_manifest_summary(training_payload)
    recovered_summary = _registry_summary(recovered_payload, "recovered_prior")
    rejected_summary = _registry_summary(rejected_payload, "rejected_evaluation")

    checks.extend(_source_review_checks(review_payload, review_summary, authorized_current_work))
    checks.extend(_training_manifest_checks(training_payload, training_summary))
    checks.extend(
        _registry_checks(
            recovered_payload,
            recovered_summary,
            "recovered_prior",
            require_recovered=True,
            require_rejected_overlap=False,
        )
    )
    checks.extend(
        _registry_checks(
            rejected_payload,
            rejected_summary,
            "rejected_evaluation",
            require_recovered=False,
            require_rejected_overlap=True,
        )
    )
    planned = _build_outputs(
        review_payload=review_payload,
        training_selection_manifest_json=training_selection_manifest_json,
        training_summary=training_summary,
        recovered_prior_registry_manifest_json=recovered_prior_registry_manifest_json,
        recovered_summary=recovered_summary,
        rejected_evaluation_source_registry_manifest_json=(
            rejected_evaluation_source_registry_manifest_json
        ),
        rejected_summary=rejected_summary,
        output_dir=output_dir,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    checks.extend(_output_absence_checks(planned, output_json, output_md))

    passed = all(check["passed"] for check in checks)
    report["checks"] = checks
    report["source_summaries"] = {
        "source_static_review": review_summary,
        "training_selection_manifest": training_summary,
        "recovered_prior_registry": recovered_summary,
        "rejected_evaluation_source_registry": rejected_summary,
    }
    report["planned_outputs"] = {key: str(value["path"]) for key, value in planned.items()}
    if passed:
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(planned["scope_manifest"]["path"], planned["scope_manifest"]["payload"])
        _write_json(planned["registry_report"]["path"], planned["registry_report"]["payload"])
        planned["preflight_runbook"]["path"].write_text(
            planned["preflight_runbook"]["text"], encoding="utf-8"
        )
        report["output_hashes"].update(
            {
                "fresh_evaluation_split_scope_manifest_sha256": _sha256(
                    planned["scope_manifest"]["path"]
                ),
                "fresh_evaluation_split_nonoverlap_registry_report_sha256": _sha256(
                    planned["registry_report"]["path"]
                ),
                "run_fresh_evaluation_split_preflight_sha256": _sha256(
                    planned["preflight_runbook"]["path"]
                ),
            }
        )
    report["final_decision"] = _decision(
        passed=passed,
        enabled=True,
        authorized_next_work=authorized_next_work,
        failed=[check["name"] for check in checks if not check["passed"]],
    )
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# V13 Fresh Evaluation Split Manifest Builder",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Enabled: `{decision['enabled']}`",
        f"- Manifest files written: `{decision['manifest_files_written']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        (
            "This builder is manifest-only. It does not run DP, generate "
            "candidates, select trajectories, run replay, train CAMP, modify "
            "DP, promote artifacts, deploy, or authorize safety/CAMP-over-DP "
            "claims."
        ),
        "",
    ]
    summaries = report.get("source_summaries", {})
    if summaries:
        lines.extend(["## Source Summaries", ""])
        for key, value in summaries.items():
            lines.append(f"- `{key}`: `{json.dumps(_stable(value), sort_keys=True)}`")
        lines.append("")
    return "\n".join(lines)


def _empty_report(
    *,
    enabled: bool,
    implementation_static_contract_review_json: Path,
    training_selection_manifest_json: Path,
    recovered_prior_registry_manifest_json: Path,
    rejected_evaluation_source_registry_manifest_json: Path,
    output_dir: Path,
    output_json: Path,
    output_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "default_off": True,
            "enabled": bool(enabled),
            "manifest_builder_only": True,
            "fresh_split_member_selection_executed": False,
            "zero_intersection_proof_executed_by_this_gate": False,
            "future_zero_intersection_preflight_required": True,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "candidate_generation_by_camp": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "implementation_static_contract_review_json": str(
                implementation_static_contract_review_json
            ),
            "training_selection_manifest_json": str(training_selection_manifest_json),
            "recovered_prior_registry_manifest_json": str(
                recovered_prior_registry_manifest_json
            ),
            "rejected_evaluation_source_registry_manifest_json": str(
                rejected_evaluation_source_registry_manifest_json
            ),
            "output_dir": str(output_dir),
            "output_json": str(output_json),
            "output_md": str(output_md),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "authorizations": {
            "authorized_current_work": authorized_current_work,
            "authorized_next_work": authorized_next_work,
        },
        "source_hashes": {},
        "source_summaries": {},
        "output_hashes": {},
        "planned_outputs": {},
        "checks": [],
        "final_decision": _decision(
            passed=False,
            enabled=False,
            authorized_next_work=None,
            failed=[],
        ),
    }


def _source_review_checks(
    payload: dict[str, Any],
    summary: dict[str, Any],
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    behavior = set(_list(summary.get("required_behavior")))
    future_scope = _dict(summary.get("future_scope_contract"))
    math = _dict(summary.get("math_boundary"))
    return [
        _check(
            "source_review_schema_version",
            payload.get("schema_version") == SOURCE_REVIEW_SCHEMA_VERSION,
            payload.get("schema_version"),
            SOURCE_REVIEW_SCHEMA_VERSION,
        ),
        _check(
            "source_review_status_passed",
            summary.get("status") == SOURCE_REVIEW_STATUS,
            summary.get("status"),
            SOURCE_REVIEW_STATUS,
        ),
        _check("source_review_passed", summary.get("passed") is True, summary.get("passed"), True),
        _check(
            "source_review_failed_checks_empty",
            summary.get("failed_checks") == [],
            summary.get("failed_checks"),
            [],
        ),
        _check(
            "source_review_authorizes_current_work",
            summary.get("authorized_next_work") == authorized_current_work,
            summary.get("authorized_next_work"),
            authorized_current_work,
        ),
        _check(
            "source_review_authorizes_implementation_only",
            summary.get("fresh_evaluation_split_implementation_authorized_next") is True
            and summary.get("implementation_authorized_next") is True,
            {
                "fresh_evaluation_split_implementation_authorized_next": summary.get(
                    "fresh_evaluation_split_implementation_authorized_next"
                ),
                "implementation_authorized_next": summary.get("implementation_authorized_next"),
            },
            True,
        ),
        _check(
            "source_review_blocks_forbidden_actions",
            all(summary.get(flag) is False for flag in BLOCKED_SOURCE_FLAGS),
            {flag: summary.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
            False,
        ),
        _check(
            "source_review_expected_builder_paths",
            summary.get("future_builder_script") == EXPECTED_BUILDER_SCRIPT
            and summary.get("future_builder_test") == EXPECTED_BUILDER_TEST,
            {
                "script": summary.get("future_builder_script"),
                "test": summary.get("future_builder_test"),
            },
            {"script": EXPECTED_BUILDER_SCRIPT, "test": EXPECTED_BUILDER_TEST},
        ),
        _check(
            "source_review_required_behavior_present",
            set(REQUIRED_BEHAVIOR) <= behavior,
            sorted(behavior),
            sorted(REQUIRED_BEHAVIOR),
        ),
        _check(
            "source_review_future_scope_expected",
            future_scope.get("selection_log_count") == TARGET_SELECTION_LOGS
            and future_scope.get("record_count") == TARGET_RECORDS
            and future_scope.get("candidate_count") == EXPECTED_CANDIDATE_COUNT
            and future_scope.get("atom_count") == EXPECTED_ATOM_COUNT
            and future_scope.get("routes_minimum", EXPECTED_ROUTES_MINIMUM)
            == EXPECTED_ROUTES_MINIMUM
            and future_scope.get("seeds_minimum", EXPECTED_SEEDS_MINIMUM)
            == EXPECTED_SEEDS_MINIMUM
            and future_scope.get(
                "route_traffic_light_buckets_minimum",
                EXPECTED_ROUTE_TL_BUCKETS_MINIMUM,
            )
            == EXPECTED_ROUTE_TL_BUCKETS_MINIMUM,
            future_scope,
            {
                "selection_log_count": TARGET_SELECTION_LOGS,
                "record_count": TARGET_RECORDS,
                "candidate_count": EXPECTED_CANDIDATE_COUNT,
                "atom_count": EXPECTED_ATOM_COUNT,
            },
        ),
        _check(
            "source_review_math_boundary_affine_simplex",
            math.get("candidate_operation") == "fixed DP candidate reranking only"
            and math.get("score_expression") == SCORE_EXPRESSION
            and math.get("nonnegative_simplex_weights_only") is True,
            math,
            {
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": SCORE_EXPRESSION,
                "nonnegative_simplex_weights_only": True,
            },
        ),
    ]


def _training_manifest_checks(
    payload: dict[str, Any],
    summary: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check(
            "training_manifest_schema_version",
            payload.get("schema_version") == TRAINING_SELECTION_MANIFEST_SCHEMA_VERSION,
            payload.get("schema_version"),
            TRAINING_SELECTION_MANIFEST_SCHEMA_VERSION,
        ),
        _check(
            "training_manifest_full_76c2_log_count",
            summary["selection_log_count"] == TRAINING_SELECTION_LOGS,
            summary["selection_log_count"],
            TRAINING_SELECTION_LOGS,
        ),
        _check(
            "training_manifest_full_76c2_record_count",
            summary["records_total"] == TRAINING_RECORDS,
            summary["records_total"],
            TRAINING_RECORDS,
        ),
        _check(
            "training_manifest_entry_count_matches_header",
            summary["entry_count"] == summary["selection_log_count"],
            summary["entry_count"],
            summary["selection_log_count"],
        ),
        _check(
            "training_manifest_entry_records_sum_matches_header",
            summary["entry_records_sum"] == summary["records_total"],
            summary["entry_records_sum"],
            summary["records_total"],
        ),
        _check(
            "training_manifest_expected_steps_per_log",
            summary["record_count_values"] == {str(EXPECTED_STEPS_PER_LOG): summary["entry_count"]},
            summary["record_count_values"],
            {str(EXPECTED_STEPS_PER_LOG): summary["entry_count"]},
        ),
        _check(
            "training_manifest_sources_present",
            summary["source_counts"].get("prior", 0) > 0
            and summary["source_counts"].get("evaluation", 0) > 0,
            summary["source_counts"],
            {"prior": ">0", "evaluation": ">0"},
        ),
        _check(
            "training_manifest_operation_flags_false",
            payload.get("candidate_generation_executed") is False
            and payload.get("replay_executed") is False
            and payload.get("training_executed") is False,
            {
                "candidate_generation_executed": payload.get("candidate_generation_executed"),
                "replay_executed": payload.get("replay_executed"),
                "training_executed": payload.get("training_executed"),
            },
            False,
        ),
        _check(
            "training_manifest_entries_have_hashes",
            summary["invalid_sha256_count"] == 0,
            summary["invalid_sha256_count"],
            0,
        ),
        _check(
            "training_manifest_no_formal_seeds",
            summary["formal_seed_count"] == 0,
            summary["formal_seed_count"],
            0,
        ),
        _check(
            "training_manifest_no_full36",
            summary["full36_reference_count"] == 0,
            summary["full36_reference_count"],
            0,
        ),
    ]


def _registry_checks(
    payload: dict[str, Any],
    summary: dict[str, Any],
    label: str,
    *,
    require_recovered: bool,
    require_rejected_overlap: bool,
) -> list[dict[str, Any]]:
    checks = [
        _check(
            f"{label}_registry_schema_version",
            payload.get("schema_version") == SOURCE_REGISTRY_SCHEMA_VERSION,
            payload.get("schema_version"),
            SOURCE_REGISTRY_SCHEMA_VERSION,
        ),
        _check(
            f"{label}_registry_referenced_files_nonempty",
            summary["missing_or_empty_referenced_files"] == [],
            summary["missing_or_empty_referenced_files"],
            [],
        ),
        _check(
            f"{label}_registry_no_formal_seed_records",
            summary["formal_seed_count"] == 0,
            summary["formal_seed_count"],
            0,
        ),
        _check(
            f"{label}_registry_no_full36_references",
            summary["full36_reference_count"] == 0,
            summary["full36_reference_count"],
            0,
        ),
    ]
    if require_recovered:
        checks.extend(
            [
                _check(
                    f"{label}_registry_recovered_candidate_hashes_nonempty",
                    summary["recovered_candidate_hash_count"] > 0,
                    summary["recovered_candidate_hash_count"],
                    ">0",
                ),
                _check(
                    f"{label}_registry_recovered_path_signatures_nonempty",
                    summary["recovered_path_signature_count"] > 0,
                    summary["recovered_path_signature_count"],
                    ">0",
                ),
                _check(
                    f"{label}_registry_recovered_record_identities_nonempty",
                    summary["recovered_record_identity_count"] > 0,
                    summary["recovered_record_identity_count"],
                    ">0",
                ),
                _check(
                    f"{label}_registry_training_missing_logs_nonempty",
                    summary["training_missing_log_count"] > 0,
                    summary["training_missing_log_count"],
                    ">0",
                ),
            ]
        )
    if require_rejected_overlap:
        checks.extend(
            [
                _check(
                    f"{label}_registry_evaluation_candidates_nonempty",
                    summary["evaluation_candidate_hash_count"] > 0,
                    summary["evaluation_candidate_hash_count"],
                    ">0",
                ),
                _check(
                    f"{label}_registry_candidate_overlap_positive",
                    summary["candidate_hash_intersection_count"] > 0,
                    summary["candidate_hash_intersection_count"],
                    ">0 rejected-source overlap evidence",
                ),
                _check(
                    f"{label}_registry_path_overlap_positive",
                    summary["path_signature_intersection_count"] > 0,
                    summary["path_signature_intersection_count"],
                    ">0 rejected-source overlap evidence",
                ),
                _check(
                    f"{label}_registry_record_identity_overlap_positive",
                    summary["record_identity_intersection_count"] > 0,
                    summary["record_identity_intersection_count"],
                    ">0 rejected-source overlap evidence",
                ),
            ]
        )
    return checks


def _build_outputs(
    *,
    review_payload: dict[str, Any],
    training_selection_manifest_json: Path,
    training_summary: dict[str, Any],
    recovered_prior_registry_manifest_json: Path,
    recovered_summary: dict[str, Any],
    rejected_evaluation_source_registry_manifest_json: Path,
    rejected_summary: dict[str, Any],
    output_dir: Path,
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, dict[str, Any]]:
    review_summary = _review_summary(review_payload)
    source_review_path = _source_path(review_payload)
    scope_manifest = {
        "schema_version": FRESH_SCOPE_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "fresh_evaluation_split_scope_manifest",
        "target_selection_log_count": TARGET_SELECTION_LOGS,
        "target_record_count": TARGET_RECORDS,
        "expected_steps_per_log": EXPECTED_STEPS_PER_LOG,
        "expected_candidate_count": EXPECTED_CANDIDATE_COUNT,
        "expected_atom_count": EXPECTED_ATOM_COUNT,
        "routes_minimum": EXPECTED_ROUTES_MINIMUM,
        "seeds_minimum": EXPECTED_SEEDS_MINIMUM,
        "route_traffic_light_buckets_minimum": EXPECTED_ROUTE_TL_BUCKETS_MINIMUM,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "nonnegative_simplex_weights_only": True,
        "required_dp_head": current_dp_head,
        "current_camp_head": current_camp_head,
        "source_static_review_json": str(source_review_path),
        "source_static_review_json_sha256": (
            _sha256(source_review_path) if source_review_path and source_review_path.is_file() else None
        ),
        "training_selection_manifest_json": str(training_selection_manifest_json),
        "training_selection_manifest_json_sha256": _sha256(training_selection_manifest_json),
        "recovered_prior_registry_manifest_json": str(recovered_prior_registry_manifest_json),
        "recovered_prior_registry_manifest_json_sha256": _sha256(
            recovered_prior_registry_manifest_json
        ),
        "rejected_evaluation_source_registry_manifest_json": str(
            rejected_evaluation_source_registry_manifest_json
        ),
        "rejected_evaluation_source_registry_manifest_json_sha256": _sha256(
            rejected_evaluation_source_registry_manifest_json
        ),
        "required_future_builder_behavior": review_summary["required_behavior"],
        "fresh_split_members_selected_by_this_builder": False,
        "fresh_split_member_count_selected_by_this_builder": 0,
        "future_preflight_must_prove": {
            "candidate_tensor_hash_intersection_count": 0,
            "path_signature_intersection_count": 0,
            "record_identity_intersection_count": 0,
            "split_manifest_root_intersection_count": 0,
        },
        "must_exclude": {
            "formal_seeds_11_12_13": True,
            "full36": True,
            "training_manifest_entries": True,
            "recovered_prior_registry_entries": True,
            "rejected_evaluation_source_registry_entries": True,
        },
        "required_runtime_contract": {
            "default_off_shadow_selector": True,
            "executed_dp_top1": True,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcomes_as_training_or_online_input": False,
        },
        "executions_requested_by_this_manifest": {
            "fixed_dp_candidate_generation": False,
            "data_preparation": False,
            "replay": False,
            "training": False,
            "dp_modification": False,
            "selector_or_atom_promotion": False,
            "deployment": False,
        },
    }
    registry_report = {
        "schema_version": NONOVERLAP_REGISTRY_REPORT_SCHEMA_VERSION,
        "manifest_role": "fresh_evaluation_split_nonoverlap_registry_report",
        "zero_intersection_proof_executed_by_this_builder": False,
        "future_zero_intersection_preflight_required": True,
        "training_selection_manifest_summary": training_summary,
        "recovered_prior_registry_summary": recovered_summary,
        "rejected_evaluation_source_registry_summary": rejected_summary,
        "nonoverlap_requirements_for_future_fresh_split": {
            "candidate_tensor_hash_intersection_count": 0,
            "path_signature_intersection_count": 0,
            "record_identity_intersection_count": 0,
            "split_manifest_root_intersection_count": 0,
        },
        "rejected_source_overlap_is_exclusion_evidence": {
            "candidate_hash_intersection_count": rejected_summary[
                "candidate_hash_intersection_count"
            ],
            "path_signature_intersection_count": rejected_summary[
                "path_signature_intersection_count"
            ],
            "record_identity_intersection_count": rejected_summary[
                "record_identity_intersection_count"
            ],
        },
        "forbidden_operations": {
            "fixed_dp_candidate_generation": True,
            "candidate_generation_by_camp": True,
            "trajectory_generation_by_camp": True,
            "trajectory_modification_by_camp": True,
            "reference_blend": True,
            "guidance": True,
            "postprocess_or_postselection": True,
            "closed_loop_outcome_input": True,
            "replay": True,
            "training": True,
            "dp_modification": True,
            "promotion": True,
            "claims": True,
        },
    }
    preflight_text = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "echo 'validation-only runbook for v13 fresh evaluation split manifests'",
            "test -f fresh_evaluation_split_scope_manifest.json",
            "test -f fresh_evaluation_split_nonoverlap_registry_report.json",
            "test -f SHA256SUMS.txt",
            "sha256sum -c SHA256SUMS.txt",
            "echo 'no DP execution, no candidate generation, no replay, no training'",
            "",
        ]
    )
    return {
        "scope_manifest": {
            "path": output_dir / "fresh_evaluation_split_scope_manifest.json",
            "payload": scope_manifest,
        },
        "registry_report": {
            "path": output_dir / "fresh_evaluation_split_nonoverlap_registry_report.json",
            "payload": registry_report,
        },
        "preflight_runbook": {
            "path": output_dir / "run_fresh_evaluation_split_preflight.sh",
            "text": preflight_text,
        },
    }


def _review_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    review = _dict(payload.get("static_contract_review"))
    source = _dict(payload.get("source_summary"))
    return {
        "schema_version": payload.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "fresh_evaluation_split_implementation_authorized_next": decision.get(
            "fresh_evaluation_split_implementation_authorized_next"
        ),
        "implementation_authorized_next": decision.get("implementation_authorized_next"),
        **{flag: decision.get(flag) for flag in BLOCKED_SOURCE_FLAGS},
        "future_builder_script": review.get("future_builder_script")
        or source.get("future_builder_script"),
        "future_builder_test": review.get("future_builder_test")
        or source.get("future_builder_test"),
        "required_behavior": _list(
            review.get("required_behavior")
            or source.get("required_future_builder_behavior")
        ),
        "future_scope_contract": _dict(review.get("future_scope_contract")),
        "math_boundary": _dict(review.get("math_boundary")),
    }


def _training_manifest_summary(payload: dict[str, Any]) -> dict[str, Any]:
    entries = [entry for entry in _list(payload.get("entries")) if isinstance(entry, dict)]
    source_counts: dict[str, int] = {}
    record_count_values: dict[str, int] = {}
    invalid_sha_count = 0
    formal_seed_count = 0
    full36_count = 0
    records_sum = 0
    for entry in entries:
        source = str(entry.get("source"))
        source_counts[source] = source_counts.get(source, 0) + 1
        records = entry.get("records")
        if isinstance(records, int):
            records_sum += records
            key = str(records)
            record_count_values[key] = record_count_values.get(key, 0) + 1
        else:
            record_count_values["<missing>"] = record_count_values.get("<missing>", 0) + 1
        if not _is_sha256(str(entry.get("sha256", ""))):
            invalid_sha_count += 1
        text = " ".join(str(entry.get(key, "")) for key in ("path", "relative_path"))
        seeds = _extract_seeds(text)
        if seeds & FORMAL_SEEDS:
            formal_seed_count += 1
        if "full36" in text.lower():
            full36_count += 1
    return {
        "schema_version": payload.get("schema_version"),
        "selection_log_count": payload.get("selection_log_count"),
        "records_total": payload.get("records_total"),
        "entry_count": len(entries),
        "entry_records_sum": records_sum,
        "record_count_values": record_count_values,
        "source_counts": source_counts,
        "invalid_sha256_count": invalid_sha_count,
        "formal_seed_count": formal_seed_count,
        "full36_reference_count": full36_count,
    }


def _registry_summary(payload: dict[str, Any], label: str) -> dict[str, Any]:
    referenced_keys = (
        "candidate_tensor_hash_registry_json",
        "path_signature_registry_json",
        "record_identity_hash_registry_json",
        "split_manifest_json",
        "training_manifest_json",
    )
    missing_or_empty: list[str] = []
    referenced_file_hashes: dict[str, str] = {}
    for key in referenced_keys:
        path_value = payload.get(key)
        if not isinstance(path_value, str) or not path_value:
            missing_or_empty.append(key)
            continue
        path = Path(path_value)
        if not path.is_file() or path.stat().st_size == 0:
            missing_or_empty.append(path_value)
            continue
        referenced_file_hashes[key] = _sha256(path)

    text_values = " ".join(
        str(payload.get(key, ""))
        for key in (
            "evaluation_output_dir",
            "recovery_result_review_dir",
            "split_manifest_json",
            "training_manifest_json",
        )
    )
    for sample in _list(payload.get("training_missing_log_sample")):
        text_values += f" {sample}"
    seeds = _extract_seeds(text_values)
    formal_seed_count = len(seeds & FORMAL_SEEDS)
    full36_reference_count = 1 if "full36" in text_values.lower() else 0
    return {
        "label": label,
        "schema_version": payload.get("schema_version"),
        "training_manifest_log_count": _int(payload.get("training_manifest_log_count")),
        "training_existing_log_count": _int(payload.get("training_existing_log_count")),
        "training_missing_log_count": _int(payload.get("training_missing_log_count")),
        "training_candidate_hash_count": _int(payload.get("training_candidate_hash_count")),
        "evaluation_candidate_hash_count": _int(payload.get("evaluation_candidate_hash_count")),
        "recovered_candidate_hash_count": _int(payload.get("recovered_candidate_hash_count")),
        "recovered_path_signature_count": _int(payload.get("recovered_path_signature_count")),
        "recovered_record_identity_count": _int(payload.get("recovered_record_identity_count")),
        "candidate_hash_intersection_count": _int(payload.get("candidate_hash_intersection_count")),
        "path_signature_intersection_count": _int(payload.get("path_signature_intersection_count")),
        "record_identity_intersection_count": _int(payload.get("record_identity_intersection_count")),
        "candidate_tensor_eval_hashes_in_previous_count": _int(
            payload.get("candidate_tensor_eval_hashes_in_previous_count")
        ),
        "candidate_tensor_eval_hashes_in_previous_rate": payload.get(
            "candidate_tensor_eval_hashes_in_previous_rate"
        ),
        "training_formal_seed_count": _int(payload.get("training_formal_seed_count")),
        "evaluation_formal_seed_count": _int(payload.get("evaluation_formal_seed_count")),
        "formal_seed_count": formal_seed_count
        + _int(payload.get("training_formal_seed_count"))
        + _int(payload.get("evaluation_formal_seed_count")),
        "full36_reference_count": full36_reference_count,
        "missing_or_empty_referenced_files": missing_or_empty,
        "referenced_file_hashes": referenced_file_hashes,
    }


def _audit_boundary_checks(audit_text: str) -> list[dict[str, Any]]:
    checks = []
    for flag in AUDIT_FALSE_FLAGS:
        checks.append(
            _check(
                f"audit_blocks_{flag}",
                _latest_value(audit_text, flag) == "False",
                _latest_value(audit_text, flag),
                "False",
            )
        )
    return checks


def _output_absence_checks(
    planned: dict[str, dict[str, Any]],
    output_json: Path,
    output_md: Path,
) -> list[dict[str, Any]]:
    checks = [
        _check("output_json_absent_before_write", not output_json.exists(), str(output_json), "path absent"),
        _check("output_md_absent_before_write", not output_md.exists(), str(output_md), "path absent"),
    ]
    for key, item in planned.items():
        path = item["path"]
        checks.append(_check(f"{key}_absent_before_write", not path.exists(), str(path), "path absent"))
    checks.append(
        _check(
            "sha256sums_absent_before_write",
            not (planned["scope_manifest"]["path"].parent / SHA256SUMS_NAME).exists(),
            str(planned["scope_manifest"]["path"].parent / SHA256SUMS_NAME),
            "path absent",
        )
    )
    return checks


def _decision(
    *,
    passed: bool,
    enabled: bool,
    authorized_next_work: str | None,
    failed: list[str],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else (REJECT_STATUS if enabled else DISABLED_STATUS),
        "passed": passed,
        "enabled": enabled,
        "failed_checks": failed,
        "manifest_files_written": passed,
        "authorized_next_work": authorized_next_work if passed else None,
        "post_implementation_static_contract_review_authorized_next": passed,
        "fresh_evaluation_split_manifest_builder_implemented": passed,
        "fresh_evaluation_split_members_selected": False,
        "zero_intersection_proof_executed_by_this_gate": False,
        "future_zero_intersection_preflight_required": True,
        "data_preparation_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "data_preparation_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }


def _load_source_json(path: Path, check_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not path.is_file():
        return {}, [_check(f"{check_name}_exists", False, str(path), "file exists")]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [_check(check_name, False, type(exc).__name__, "valid JSON object")]
    if not isinstance(data, dict):
        return {}, [_check(check_name, False, type(data).__name__, "dict")]
    data["_source_path"] = str(path)
    return data, [
        _check(f"{check_name}_exists", True, str(path), "file exists"),
        _check(check_name, True, "dict", "dict"),
    ]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path, names: list[str]) -> None:
    lines = []
    for name in names:
        path = output_dir / name
        if path.is_file():
            lines.append(f"{_sha256(path)}  {name}")
    (output_dir / SHA256SUMS_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _source_path(payload: dict[str, Any]) -> Path | None:
    path = payload.get("_source_path")
    return Path(path) if isinstance(path, str) else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _extract_seeds(text: str) -> set[int]:
    return {int(seed) for seed in re.findall(r"seed_(\d+)", text)}


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value) if key != "_source_path"}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
