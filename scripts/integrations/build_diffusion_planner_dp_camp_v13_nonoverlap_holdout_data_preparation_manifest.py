#!/usr/bin/env python3
"""Manifest-only builder for v13 non-overlap holdout data preparation.

This implementation writes request and exclusion manifests for a future holdout
data preparation gate. It does not run Diffusion Planner, generate candidates,
prepare data, run replay, train CAMP, modify DP, promote artifacts, deploy, or
make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_v1"
DISABLED_STATUS = (
    "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_default_off_disabled"
)
READY_STATUS = "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_complete"
REJECT_STATUS = "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_rejected"
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_static_contract_review_v1"
)
SOURCE_REVIEW_STATUS = (
    "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_static_contract_review_complete"
)
SOURCE_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_data_preparation_source_manifest_v1"
)
REQUEST_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_candidate_request_manifest_v1"
)
EXCLUSION_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_exclusion_registry_manifest_v1"
)
EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_expected_artifact_manifest_v1"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_implementation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_post_implementation_static_contract_review_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
TARGET_HOLDOUT_SELECTION_LOGS = 128
TARGET_HOLDOUT_RECORDS = 12800
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
FORMAL_SEEDS = {11, 12, 13}
OUTPUT_FILES = (
    "holdout_candidate_request_manifest.json",
    "nonoverlap_exclusion_registry_manifest.json",
    "holdout_preparation_runbook.sh",
    "expected_holdout_artifact_manifest.json",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off manifest-only builder for v13 non-overlap holdout data "
            "preparation. It writes manifests but does not run DP or prepare data."
        )
    )
    parser.add_argument("--implementation_static_contract_review_json", type=Path, required=True)
    parser.add_argument("--expected_static_contract_review_sha256", required=True)
    parser.add_argument("--nonformal_holdout_source_manifest_json", type=Path, required=True)
    parser.add_argument("--previous_training_summary_json", type=Path, required=True)
    parser.add_argument("--rejected_result_readiness_json", type=Path, required=True)
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
        "--enable_v13_nonoverlap_holdout_data_preparation_manifest_builder",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_manifest_report(
        implementation_static_contract_review_json=args.implementation_static_contract_review_json,
        expected_static_contract_review_sha256=args.expected_static_contract_review_sha256,
        nonformal_holdout_source_manifest_json=args.nonformal_holdout_source_manifest_json,
        previous_training_summary_json=args.previous_training_summary_json,
        rejected_result_readiness_json=args.rejected_result_readiness_json,
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
        enabled=args.enable_v13_nonoverlap_holdout_data_preparation_manifest_builder,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    if report["final_decision"]["manifest_files_written"]:
        _write_sha256sums(args.output_dir, list(OUTPUT_FILES))
        report["output_hashes"]["sha256sums_sha256"] = _sha256(args.output_dir / "SHA256SUMS")
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["status"] != REJECT_STATUS else 1


def build_manifest_report(
    *,
    implementation_static_contract_review_json: Path,
    expected_static_contract_review_sha256: str,
    nonformal_holdout_source_manifest_json: Path,
    previous_training_summary_json: Path,
    rejected_result_readiness_json: Path,
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
        nonformal_holdout_source_manifest_json=nonformal_holdout_source_manifest_json,
        previous_training_summary_json=previous_training_summary_json,
        rejected_result_readiness_json=rejected_result_readiness_json,
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

    review_payload: dict[str, Any] = {}
    source_payload: dict[str, Any] = {}
    audit_text = _read_text_if_exists(v13_audit_md)
    checks = [
        _check("camp_head_matches_origin_main", current_camp_head == current_camp_origin_main, current_camp_head, current_camp_origin_main),
        _check("current_dp_head_fixed", current_dp_head == required_dp_head, current_dp_head, required_dp_head),
        _check("required_dp_head_fixed", required_dp_head == FIXED_DP_HEAD, required_dp_head, FIXED_DP_HEAD),
        _check("expected_static_contract_review_sha256_valid", _is_sha256(expected_static_contract_review_sha256), expected_static_contract_review_sha256, "sha256"),
        _check("output_dir_is_not_file", not output_dir.is_file(), str(output_dir), "not a file"),
        _check("output_json_under_output_dir", _is_relative_to(output_json, output_dir), str(output_json), str(output_dir)),
        _check("output_md_under_output_dir", _is_relative_to(output_md, output_dir), str(output_md), str(output_dir)),
        _contains("current_gate_authorized_in_audit", audit_text, f"next_work_target={authorized_current_work}"),
        _contains(
            "current_status_static_review_complete",
            audit_text,
            "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_"
            "shadow_replay_evaluation_nonoverlap_holdout_data_preparation_"
            "implementation_static_contract_review_complete",
        ),
        _contains("audit_blocks_data_preparation", audit_text, "data_preparation_authorized_by_current_boundary=False"),
        _contains("audit_blocks_fixed_dp_generation", audit_text, "fixed_dp_candidate_generation_authorized_by_current_boundary=False"),
        _contains("audit_blocks_training", audit_text, "training_execution_authorized_by_current_boundary=False"),
        _contains("audit_blocks_dp_modification", audit_text, "dp_modification_authorized_by_current_boundary=False"),
    ]
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
        review_payload, review_check = _load_json_dict(
            implementation_static_contract_review_json,
            "implementation_static_contract_review_json",
        )
        checks.append(review_check)
    else:
        checks.append(_check("implementation_static_contract_review_json_exists", False, str(implementation_static_contract_review_json), "file exists"))

    if nonformal_holdout_source_manifest_json.is_file():
        report["source_hashes"]["nonformal_holdout_source_manifest_json_sha256"] = _sha256(
            nonformal_holdout_source_manifest_json
        )
        source_payload, source_check = _load_json_dict(
            nonformal_holdout_source_manifest_json,
            "nonformal_holdout_source_manifest_json",
        )
        checks.append(source_check)
    else:
        checks.append(_check("nonformal_holdout_source_manifest_json_exists", False, str(nonformal_holdout_source_manifest_json), "file exists"))

    for name, path in (
        ("previous_training_summary_json", previous_training_summary_json),
        ("rejected_result_readiness_json", rejected_result_readiness_json),
    ):
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))
        if path.is_file():
            report["source_hashes"][f"{name}_sha256"] = _sha256(path)

    checks.extend(_review_checks(review_payload, authorized_current_work))
    checks.extend(_source_manifest_checks(source_payload))
    planned = _build_outputs(
        source_payload=source_payload,
        review_payload=review_payload,
        previous_training_summary_json=previous_training_summary_json,
        rejected_result_readiness_json=rejected_result_readiness_json,
        output_dir=output_dir,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    checks.extend(_output_absence_checks(planned, output_json, output_md))

    passed = all(check["passed"] for check in checks)
    report["checks"] = checks
    report["planned_outputs"] = {key: str(value["path"]) for key, value in planned.items()}
    if passed:
        output_dir.mkdir(parents=True, exist_ok=True)
        _write_json(planned["request_manifest"]["path"], planned["request_manifest"]["payload"])
        _write_json(planned["exclusion_manifest"]["path"], planned["exclusion_manifest"]["payload"])
        planned["runbook"]["path"].write_text(planned["runbook"]["text"], encoding="utf-8")
        _write_json(
            planned["expected_artifact_manifest"]["path"],
            planned["expected_artifact_manifest"]["payload"],
        )
        report["output_hashes"].update(
            {
                "holdout_candidate_request_manifest_sha256": _sha256(planned["request_manifest"]["path"]),
                "nonoverlap_exclusion_registry_manifest_sha256": _sha256(planned["exclusion_manifest"]["path"]),
                "holdout_preparation_runbook_sha256": _sha256(planned["runbook"]["path"]),
                "expected_holdout_artifact_manifest_sha256": _sha256(planned["expected_artifact_manifest"]["path"]),
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
    return "\n".join(
        [
            "# V13 Non-Overlap Holdout Data Preparation Manifest Builder",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Enabled: `{decision['enabled']}`",
            f"- Manifest files written: `{decision['manifest_files_written']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "This builder is manifest-only. It does not run DP, generate candidates, prepare data, run replay, train CAMP, modify DP, promote, deploy, or authorize claims.",
            "",
        ]
    )


def _empty_report(
    *,
    enabled: bool,
    implementation_static_contract_review_json: Path,
    nonformal_holdout_source_manifest_json: Path,
    previous_training_summary_json: Path,
    rejected_result_readiness_json: Path,
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
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "candidate_generation_by_camp": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "implementation_static_contract_review_json": str(implementation_static_contract_review_json),
            "nonformal_holdout_source_manifest_json": str(nonformal_holdout_source_manifest_json),
            "previous_training_summary_json": str(previous_training_summary_json),
            "rejected_result_readiness_json": str(rejected_result_readiness_json),
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


def _review_checks(payload: dict[str, Any], authorized_current_work: str) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    return [
        _check("source_review_schema_version", payload.get("schema_version") == SOURCE_REVIEW_SCHEMA_VERSION, payload.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _check("source_review_status_complete", decision.get("status") == SOURCE_REVIEW_STATUS, decision.get("status"), SOURCE_REVIEW_STATUS),
        _check("source_review_passed", decision.get("passed") is True, decision.get("passed"), True),
        _check("source_review_failed_checks_empty", decision.get("failed_checks") == [], decision.get("failed_checks"), []),
        _check("source_review_authorizes_current_work", decision.get("authorized_next_work") == authorized_current_work, decision.get("authorized_next_work"), authorized_current_work),
        _check("source_review_authorizes_builder_only", decision.get("builder_implementation_authorized_next") is True, decision.get("builder_implementation_authorized_next"), True),
        _check("source_review_blocks_data_preparation", decision.get("data_preparation_authorized_next") is False, decision.get("data_preparation_authorized_next"), False),
        _check("source_review_blocks_training", decision.get("training_execution_authorized_next") is False, decision.get("training_execution_authorized_next"), False),
        _check("source_review_blocks_replay", decision.get("replay_execution_authorized_next") is False, decision.get("replay_execution_authorized_next"), False),
        _check("source_review_blocks_fixed_dp_generation", decision.get("fixed_dp_candidate_generation_authorized_next") is False, decision.get("fixed_dp_candidate_generation_authorized_next"), False),
        _check("source_review_blocks_camp_candidate_generation", decision.get("candidate_generation_by_camp_authorized") is False, decision.get("candidate_generation_by_camp_authorized"), False),
        _check("source_review_blocks_dp_modification", decision.get("dp_modification_authorized") is False, decision.get("dp_modification_authorized"), False),
        _check("source_review_blocks_promotion", decision.get("selector_promotion_authorized") is False and decision.get("atom_promotion_authorized") is False, {"selector": decision.get("selector_promotion_authorized"), "atom": decision.get("atom_promotion_authorized")}, False),
        _check("source_review_blocks_claims", decision.get("safety_benefit_claim_authorized") is False and decision.get("camp_over_dp_top1_claim_authorized") is False, {"safety": decision.get("safety_benefit_claim_authorized"), "camp_over_dp": decision.get("camp_over_dp_top1_claim_authorized")}, False),
    ]


def _source_manifest_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    requests = _list(payload.get("route_seed_requests"))
    seeds = [request.get("seed") for request in requests if isinstance(request, dict)]
    request_ids = [request.get("request_id") for request in requests if isinstance(request, dict)]
    return [
        _check("source_manifest_schema_version", payload.get("schema_version") == SOURCE_MANIFEST_SCHEMA_VERSION, payload.get("schema_version"), SOURCE_MANIFEST_SCHEMA_VERSION),
        _check("source_manifest_selection_log_target", payload.get("target_holdout_selection_logs") == TARGET_HOLDOUT_SELECTION_LOGS, payload.get("target_holdout_selection_logs"), TARGET_HOLDOUT_SELECTION_LOGS),
        _check("source_manifest_record_target", payload.get("target_holdout_records") == TARGET_HOLDOUT_RECORDS, payload.get("target_holdout_records"), TARGET_HOLDOUT_RECORDS),
        _check("source_manifest_steps_per_log", payload.get("expected_steps_per_log") == EXPECTED_STEPS_PER_LOG, payload.get("expected_steps_per_log"), EXPECTED_STEPS_PER_LOG),
        _check("source_manifest_candidate_count", payload.get("expected_candidate_count") == EXPECTED_CANDIDATE_COUNT, payload.get("expected_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _check("source_manifest_atom_count", payload.get("expected_atom_count") == EXPECTED_ATOM_COUNT, payload.get("expected_atom_count"), EXPECTED_ATOM_COUNT),
        _check("source_manifest_score_expression", payload.get("score_expression") == SCORE_EXPRESSION, payload.get("score_expression"), SCORE_EXPRESSION),
        _check("source_manifest_nonnegative_simplex", payload.get("nonnegative_simplex_weights_only") is True, payload.get("nonnegative_simplex_weights_only"), True),
        _check("source_manifest_formal_seeds_excluded", payload.get("formal_seeds_11_12_13_excluded") is True, payload.get("formal_seeds_11_12_13_excluded"), True),
        _check("source_manifest_request_count", len(requests) == TARGET_HOLDOUT_SELECTION_LOGS, len(requests), TARGET_HOLDOUT_SELECTION_LOGS),
        _check("source_manifest_request_ids_unique", len(set(request_ids)) == len(request_ids) == len(requests), request_ids[:5], "all request ids unique"),
        _check("source_manifest_no_formal_seed_requests", not (set(seeds) & FORMAL_SEEDS), sorted(set(seeds) & FORMAL_SEEDS), []),
    ]


def _build_outputs(
    *,
    source_payload: dict[str, Any],
    review_payload: dict[str, Any],
    previous_training_summary_json: Path,
    rejected_result_readiness_json: Path,
    output_dir: Path,
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, dict[str, Any]]:
    source_requests = _list(source_payload.get("route_seed_requests"))
    request_manifest = {
        "schema_version": REQUEST_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "nonoverlap_holdout_candidate_request_manifest",
        "target_holdout_selection_logs": TARGET_HOLDOUT_SELECTION_LOGS,
        "target_holdout_records": TARGET_HOLDOUT_RECORDS,
        "expected_steps_per_log": EXPECTED_STEPS_PER_LOG,
        "expected_candidate_count": EXPECTED_CANDIDATE_COUNT,
        "expected_atom_count": EXPECTED_ATOM_COUNT,
        "formal_seeds_11_12_13_excluded": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "current_camp_head": current_camp_head,
        "required_dp_head": current_dp_head,
        "route_seed_requests": source_requests,
        "executions_requested_by_this_manifest": {
            "fixed_dp_candidate_generation": False,
            "data_preparation": False,
            "replay": False,
            "training": False,
        },
    }
    exclusion_manifest = {
        "schema_version": EXCLUSION_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "nonoverlap_holdout_exclusion_registry_manifest",
        "train_eval_candidate_tensor_intersection_must_be_zero": True,
        "train_eval_path_signature_intersection_must_be_zero": True,
        "train_eval_record_identity_intersection_must_be_zero": True,
        "formal_seeds_11_12_13_excluded": True,
        "previous_training_summary_json": str(previous_training_summary_json),
        "previous_training_summary_json_sha256": _sha256(previous_training_summary_json) if previous_training_summary_json.is_file() else None,
        "rejected_result_readiness_json": str(rejected_result_readiness_json),
        "rejected_result_readiness_json_sha256": _sha256(rejected_result_readiness_json) if rejected_result_readiness_json.is_file() else None,
        "implementation_static_contract_review_sha256": _sha256_from_payload_path(review_payload),
    }
    expected_manifest = {
        "schema_version": EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "nonoverlap_holdout_expected_artifact_manifest",
        "expected_selection_log_count": TARGET_HOLDOUT_SELECTION_LOGS,
        "expected_records": TARGET_HOLDOUT_RECORDS,
        "expected_steps_per_log": EXPECTED_STEPS_PER_LOG,
        "expected_candidate_count": EXPECTED_CANDIDATE_COUNT,
        "expected_atom_count": EXPECTED_ATOM_COUNT,
        "required_outputs": [
            "selection_logs",
            "candidate_tensor_hash_registry.json",
            "path_signature_registry.json",
            "record_identity_hash_registry.json",
            "SHA256SUMS",
        ],
        "must_not_execute_by_manifest_builder": {
            "fixed_dp_candidate_generation": True,
            "data_preparation": True,
            "replay": True,
            "training": True,
            "dp_modification": True,
        },
    }
    runbook_text = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "echo 'validation-only runbook for non-overlap holdout manifests'",
            "test -f holdout_candidate_request_manifest.json",
            "test -f nonoverlap_exclusion_registry_manifest.json",
            "test -f expected_holdout_artifact_manifest.json",
            "test -f SHA256SUMS",
            "echo 'no DP execution, no candidate generation, no replay, no training'",
            "",
        ]
    )
    return {
        "request_manifest": {
            "path": output_dir / "holdout_candidate_request_manifest.json",
            "payload": request_manifest,
        },
        "exclusion_manifest": {
            "path": output_dir / "nonoverlap_exclusion_registry_manifest.json",
            "payload": exclusion_manifest,
        },
        "runbook": {
            "path": output_dir / "holdout_preparation_runbook.sh",
            "text": runbook_text,
        },
        "expected_artifact_manifest": {
            "path": output_dir / "expected_holdout_artifact_manifest.json",
            "payload": expected_manifest,
        },
    }


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
        "data_preparation_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
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
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path, names: list[str]) -> None:
    lines = []
    for name in names:
        path = output_dir / name
        if path.is_file():
            lines.append(f"{_sha256(path)}  {name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_json_dict(path: Path, check_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, _check(check_name, False, type(exc).__name__, "valid JSON object")
    if not isinstance(data, dict):
        return {}, _check(check_name, False, type(data).__name__, "dict")
    data["_source_path"] = str(path)
    return data, _check(check_name, True, "dict", "dict")


def _read_text_if_exists(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _sha256_from_payload_path(payload: dict[str, Any]) -> str | None:
    path = payload.get("_source_path")
    return _sha256(Path(path)) if isinstance(path, str) and Path(path).is_file() else None


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


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else None, needle)


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


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value) if key != "_source_path"}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
