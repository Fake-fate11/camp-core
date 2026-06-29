#!/usr/bin/env python3
"""Post-implementation static review for the v13 holdout manifest builder.

This gate is read-only. It verifies that the implemented manifest builder and
its materialized manifest artifact stayed default-off and manifest-only before
authorizing the next data-preparation gate. It does not run Diffusion Planner,
prepare data, replay, train CAMP, modify DP, promote artifacts, deploy, or make
safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
TARGET_HOLDOUT_SELECTION_LOGS = 128
TARGET_HOLDOUT_RECORDS = 12800
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
FORMAL_SEEDS = {11, 12, 13}

SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_"
    "post_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_"
    "post_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_"
    "post_implementation_static_contract_review_rejected"
)
SOURCE_BUILDER_SCHEMA_VERSION = (
    "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_v1"
)
SOURCE_BUILDER_STATUS = (
    "dp_camp_v13_nonoverlap_holdout_data_preparation_manifest_builder_complete"
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
    "nonoverlap_holdout_data_preparation_post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
    "nonoverlap_holdout_data_preparation_only"
)

OUTPUT_HASH_FIELDS = {
    "holdout_candidate_request_manifest_sha256": "holdout_candidate_request_manifest.json",
    "nonoverlap_exclusion_registry_manifest_sha256": (
        "nonoverlap_exclusion_registry_manifest.json"
    ),
    "holdout_preparation_runbook_sha256": "holdout_preparation_runbook.sh",
    "expected_holdout_artifact_manifest_sha256": "expected_holdout_artifact_manifest.json",
    "sha256sums_sha256": "SHA256SUMS",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only post-implementation static contract review for the v13 "
            "non-overlap holdout manifest builder."
        )
    )
    parser.add_argument("--manifest_builder_json", type=Path, required=True)
    parser.add_argument("--expected_manifest_builder_json_sha256", required=True)
    parser.add_argument("--manifest_builder_script_py", type=Path, required=True)
    parser.add_argument("--manifest_builder_test_py", type=Path, required=True)
    parser.add_argument("--request_manifest_json", type=Path, required=True)
    parser.add_argument("--exclusion_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_artifact_manifest_json", type=Path, required=True)
    parser.add_argument("--holdout_preparation_runbook_sh", type=Path, required=True)
    parser.add_argument("--sha256sums", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        manifest_builder_json=args.manifest_builder_json,
        expected_manifest_builder_json_sha256=args.expected_manifest_builder_json_sha256,
        manifest_builder_script_py=args.manifest_builder_script_py,
        manifest_builder_test_py=args.manifest_builder_test_py,
        request_manifest_json=args.request_manifest_json,
        exclusion_manifest_json=args.exclusion_manifest_json,
        expected_artifact_manifest_json=args.expected_artifact_manifest_json,
        holdout_preparation_runbook_sh=args.holdout_preparation_runbook_sh,
        sha256sums=args.sha256sums,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_stable(report), indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    manifest_builder_json: Path,
    expected_manifest_builder_json_sha256: str,
    manifest_builder_script_py: Path,
    manifest_builder_test_py: Path,
    request_manifest_json: Path,
    exclusion_manifest_json: Path,
    expected_artifact_manifest_json: Path,
    holdout_preparation_runbook_sh: Path,
    sha256sums: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "manifest_builder_json": manifest_builder_json.resolve(),
        "manifest_builder_script_py": manifest_builder_script_py.resolve(),
        "manifest_builder_test_py": manifest_builder_test_py.resolve(),
        "request_manifest_json": request_manifest_json.resolve(),
        "exclusion_manifest_json": exclusion_manifest_json.resolve(),
        "expected_artifact_manifest_json": expected_artifact_manifest_json.resolve(),
        "holdout_preparation_runbook_sh": holdout_preparation_runbook_sh.resolve(),
        "sha256sums": sha256sums.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    builder_payload = _load_json_dict(paths["manifest_builder_json"])
    request_manifest = _load_json_dict(paths["request_manifest_json"])
    exclusion_manifest = _load_json_dict(paths["exclusion_manifest_json"])
    expected_artifact_manifest = _load_json_dict(paths["expected_artifact_manifest_json"])
    script_text = _read_text(paths["manifest_builder_script_py"])
    test_text = _read_text(paths["manifest_builder_test_py"])
    runbook_text = _read_text(paths["holdout_preparation_runbook_sh"])
    sha256sums_text = _read_text(paths["sha256sums"])
    audit_text = _read_text(paths["v13_audit_md"])

    checks = _checks(
        paths=paths,
        builder_payload=builder_payload,
        request_manifest=request_manifest,
        exclusion_manifest=exclusion_manifest,
        expected_artifact_manifest=expected_artifact_manifest,
        script_text=script_text,
        test_text=test_text,
        runbook_text=runbook_text,
        sha256sums_text=sha256sums_text,
        audit_text=audit_text,
        expected_manifest_builder_json_sha256=expected_manifest_builder_json_sha256,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "read_only": True,
            "static_contract_review_only": True,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {name: str(path) for name, path in paths.items()},
        "source_hashes": {
            f"{name}_sha256": _sha256(path) if path.is_file() else None
            for name, path in paths.items()
        },
        "builder_summary": _builder_summary(builder_payload),
        "manifest_summary": _manifest_summary(
            request_manifest=request_manifest,
            exclusion_manifest=exclusion_manifest,
            expected_artifact_manifest=expected_artifact_manifest,
        ),
        "review_checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    manifest = report["manifest_summary"]
    return "\n".join(
        [
            "# V13 Non-Overlap Holdout Manifest Builder Post-Implementation Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Data preparation authorized next: `{decision['data_preparation_authorized_next']}`",
            f"- Fixed-DP candidate generation authorized next: `{decision['fixed_dp_candidate_generation_authorized_next']}`",
            f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
            f"- Replay authorized next: `{decision['replay_execution_authorized_next']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            "",
            "## Manifest",
            "",
            f"- Request count: `{manifest['request_count']}`",
            f"- Target records: `{manifest['target_holdout_records']}`",
            f"- Formal seed overlap: `{manifest['formal_seed_overlap']}`",
            f"- Score expression: `{SCORE_EXPRESSION}`",
            "",
            "This review is read-only. It does not run DP, prepare data, run "
            "fixed-DP candidate generation, replay, train CAMP, modify DP, "
            "promote, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _checks(
    *,
    paths: dict[str, Path],
    builder_payload: dict[str, Any],
    request_manifest: dict[str, Any],
    exclusion_manifest: dict[str, Any],
    expected_artifact_manifest: dict[str, Any],
    script_text: str,
    test_text: str,
    runbook_text: str,
    sha256sums_text: str,
    audit_text: str,
    expected_manifest_builder_json_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "expected_manifest_builder_json_sha256_valid",
            _is_sha256(expected_manifest_builder_json_sha256),
            expected_manifest_builder_json_sha256,
            "64-char sha256",
        ),
    ]
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file exists"))

    if paths["manifest_builder_json"].is_file():
        checks.append(
            _expect(
                "manifest_builder_json_sha256_matches_expected",
                _sha256(paths["manifest_builder_json"]),
                expected_manifest_builder_json_sha256.lower(),
            )
        )

    checks.extend(_builder_artifact_checks(builder_payload))
    checks.extend(_request_manifest_checks(request_manifest))
    checks.extend(_exclusion_manifest_checks(exclusion_manifest))
    checks.extend(_expected_artifact_manifest_checks(expected_artifact_manifest))
    checks.extend(_output_hash_checks(paths, builder_payload, sha256sums_text))
    checks.extend(_script_contract_checks(script_text))
    checks.extend(_test_contract_checks(test_text))
    checks.extend(_runbook_checks(runbook_text))
    checks.extend(_audit_checks(audit_text, authorized_current_work))
    return checks


def _builder_artifact_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    heads = _dict(payload.get("heads"))
    return [
        _expect("builder_schema_version", payload.get("schema_version"), SOURCE_BUILDER_SCHEMA_VERSION),
        _expect("builder_status_complete", decision.get("status"), SOURCE_BUILDER_STATUS),
        _expect("builder_passed", decision.get("passed"), True),
        _expect("builder_enabled", decision.get("enabled"), True),
        _expect("builder_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("builder_manifest_files_written", decision.get("manifest_files_written"), True),
        _expect("builder_authorizes_current_gate", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect(
            "builder_authorizes_post_review_only",
            decision.get("post_implementation_static_contract_review_authorized_next"),
            True,
        ),
        _expect("builder_blocks_data_preparation", decision.get("data_preparation_authorized_next"), False),
        _expect(
            "builder_blocks_fixed_dp_generation",
            decision.get("fixed_dp_candidate_generation_authorized_next"),
            False,
        ),
        _expect("builder_blocks_training", decision.get("training_execution_authorized_next"), False),
        _expect("builder_blocks_replay", decision.get("replay_execution_authorized_next"), False),
        _expect(
            "builder_blocks_camp_candidate_generation",
            decision.get("candidate_generation_by_camp_authorized"),
            False,
        ),
        _expect("builder_blocks_dp_modification", decision.get("dp_modification_authorized"), False),
        _expect("builder_blocks_selector_promotion", decision.get("selector_promotion_authorized"), False),
        _expect("builder_blocks_atom_promotion", decision.get("atom_promotion_authorized"), False),
        _expect("builder_blocks_deployment", decision.get("deployment_authorized"), False),
        _expect("builder_blocks_safety_claim", decision.get("safety_benefit_claim_authorized"), False),
        _expect("builder_blocks_camp_over_dp_claim", decision.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("builder_did_not_prepare_data", decision.get("data_preparation_executed"), False),
        _expect(
            "builder_did_not_generate_fixed_dp_candidates",
            decision.get("fixed_dp_candidate_generation_executed"),
            False,
        ),
        _expect("builder_did_not_train", decision.get("training_executed"), False),
        _expect("builder_did_not_replay", decision.get("replay_executed"), False),
        _expect("builder_analysis_default_off", analysis.get("default_off"), True),
        _expect("builder_analysis_manifest_only", analysis.get("manifest_builder_only"), True),
        _expect("builder_analysis_candidate_operation", analysis.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("builder_analysis_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
        _check(
            "builder_artifact_camp_head_is_sha",
            _is_git_sha(str(heads.get("current_camp_head", ""))),
            heads.get("current_camp_head"),
            "40-char git sha",
        ),
        _expect(
            "builder_artifact_camp_head_matches_origin",
            heads.get("current_camp_head"),
            heads.get("current_camp_origin_main"),
        ),
        _expect("builder_artifact_dp_head_fixed", heads.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("builder_required_dp_head_fixed", heads.get("required_dp_head"), FIXED_DP_HEAD),
    ]


def _request_manifest_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    requests = _list(payload.get("route_seed_requests"))
    request_ids = [request.get("request_id") for request in requests if isinstance(request, dict)]
    seeds = [request.get("seed") for request in requests if isinstance(request, dict)]
    executions = _dict(payload.get("executions_requested_by_this_manifest"))
    return [
        _expect("request_manifest_schema_version", payload.get("schema_version"), REQUEST_MANIFEST_SCHEMA_VERSION),
        _expect("request_manifest_log_target", payload.get("target_holdout_selection_logs"), TARGET_HOLDOUT_SELECTION_LOGS),
        _expect("request_manifest_record_target", payload.get("target_holdout_records"), TARGET_HOLDOUT_RECORDS),
        _expect("request_manifest_steps_per_log", payload.get("expected_steps_per_log"), EXPECTED_STEPS_PER_LOG),
        _expect("request_manifest_candidate_count", payload.get("expected_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("request_manifest_atom_count", payload.get("expected_atom_count"), EXPECTED_ATOM_COUNT),
        _expect("request_manifest_formal_seeds_excluded", payload.get("formal_seeds_11_12_13_excluded"), True),
        _expect("request_manifest_candidate_operation", payload.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("request_manifest_score_expression", payload.get("score_expression"), SCORE_EXPRESSION),
        _expect("request_manifest_count", len(requests), TARGET_HOLDOUT_SELECTION_LOGS),
        _check("request_manifest_unique_ids", len(set(request_ids)) == len(request_ids) == len(requests), request_ids[:5], "all request ids unique"),
        _check("request_manifest_no_formal_seeds", not (set(seeds) & FORMAL_SEEDS), sorted(set(seeds) & FORMAL_SEEDS), []),
        _expect("request_manifest_requests_no_data_preparation", executions.get("data_preparation"), False),
        _expect("request_manifest_requests_no_fixed_dp_generation", executions.get("fixed_dp_candidate_generation"), False),
        _expect("request_manifest_requests_no_replay", executions.get("replay"), False),
        _expect("request_manifest_requests_no_training", executions.get("training"), False),
    ]


def _exclusion_manifest_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("exclusion_manifest_schema_version", payload.get("schema_version"), EXCLUSION_MANIFEST_SCHEMA_VERSION),
        _expect("exclusion_manifest_candidate_intersection_zero", payload.get("train_eval_candidate_tensor_intersection_must_be_zero"), True),
        _expect("exclusion_manifest_path_intersection_zero", payload.get("train_eval_path_signature_intersection_must_be_zero"), True),
        _expect("exclusion_manifest_record_intersection_zero", payload.get("train_eval_record_identity_intersection_must_be_zero"), True),
        _expect("exclusion_manifest_formal_seeds_excluded", payload.get("formal_seeds_11_12_13_excluded"), True),
    ]


def _expected_artifact_manifest_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    required_outputs = _list(payload.get("required_outputs"))
    must_not = _dict(payload.get("must_not_execute_by_manifest_builder"))
    checks = [
        _expect(
            "expected_artifact_manifest_schema_version",
            payload.get("schema_version"),
            EXPECTED_ARTIFACT_MANIFEST_SCHEMA_VERSION,
        ),
        _expect("expected_artifact_log_count", payload.get("expected_selection_log_count"), TARGET_HOLDOUT_SELECTION_LOGS),
        _expect("expected_artifact_records", payload.get("expected_records"), TARGET_HOLDOUT_RECORDS),
        _expect("expected_artifact_steps_per_log", payload.get("expected_steps_per_log"), EXPECTED_STEPS_PER_LOG),
        _expect("expected_artifact_candidate_count", payload.get("expected_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("expected_artifact_atom_count", payload.get("expected_atom_count"), EXPECTED_ATOM_COUNT),
    ]
    for output_name in (
        "selection_logs",
        "candidate_tensor_hash_registry.json",
        "path_signature_registry.json",
        "record_identity_hash_registry.json",
        "SHA256SUMS",
    ):
        checks.append(_check(f"expected_artifact_requires_{_slug(output_name)}", output_name in required_outputs, required_outputs, output_name))
    for key in (
        "fixed_dp_candidate_generation",
        "data_preparation",
        "replay",
        "training",
        "dp_modification",
    ):
        checks.append(_expect(f"expected_artifact_builder_must_not_{key}", must_not.get(key), True))
    return checks


def _output_hash_checks(
    paths: dict[str, Path],
    builder_payload: dict[str, Any],
    sha256sums_text: str,
) -> list[dict[str, Any]]:
    output_hashes = _dict(builder_payload.get("output_hashes"))
    sha_entries = _sha256sum_entries(sha256sums_text)
    artifact_dir = paths["request_manifest_json"].parent
    checks: list[dict[str, Any]] = []
    for field, filename in OUTPUT_HASH_FIELDS.items():
        if filename == "SHA256SUMS":
            path = paths["sha256sums"]
        else:
            path = artifact_dir / filename
        expected = _sha256(path) if path.is_file() else None
        checks.append(_expect(f"output_hash_{field}_matches_file", output_hashes.get(field), expected))
        if filename != "SHA256SUMS":
            checks.append(_expect(f"sha256sums_entry_{_slug(filename)}", sha_entries.get(filename), expected))
    checks.append(
        _check(
            "sha256sums_excludes_report_json",
            "manifest_builder_report.json" not in sha_entries,
            sorted(sha_entries),
            "no report json entry",
        )
    )
    return checks


def _script_contract_checks(text: str) -> list[dict[str, Any]]:
    needles = {
        "builder_default_off_disabled_status": "default_off_disabled",
        "builder_enable_flag_present": "--enable_v13_nonoverlap_holdout_data_preparation_manifest_builder",
        "builder_returns_before_reads_when_disabled": "if not enabled:\n        return report",
        "builder_manifest_only_analysis": "\"manifest_builder_only\": True",
        "builder_no_data_preparation_execution": "\"data_preparation_execution\": False",
        "builder_no_fixed_dp_generation_execution": "\"fixed_dp_candidate_generation_execution\": False",
        "builder_no_training_execution": "\"training_execution\": False",
        "builder_no_replay_execution": "\"replay_execution\": False",
        "builder_no_dp_modification": "\"dp_modification\": False",
        "builder_no_camp_candidate_generation": "\"candidate_generation_by_camp\": False",
        "builder_score_expression": SCORE_EXPRESSION,
        "builder_formal_seed_constant": "FORMAL_SEEDS = {11, 12, 13}",
        "builder_output_files_constant": "OUTPUT_FILES = (",
        "builder_write_sha256sums_output_files_only": "_write_sha256sums(args.output_dir, list(OUTPUT_FILES))",
        "builder_writes_request_manifest": "holdout_candidate_request_manifest.json",
        "builder_writes_exclusion_manifest": "nonoverlap_exclusion_registry_manifest.json",
        "builder_writes_expected_manifest": "expected_holdout_artifact_manifest.json",
    }
    return [_contains(name, text, needle) for name, needle in needles.items()]


def _test_contract_checks(text: str) -> list[dict[str, Any]]:
    needles = {
        "test_default_off_no_side_effects": "test_manifest_builder_is_default_off_and_has_no_side_effects",
        "test_manifest_only_outputs": "test_manifest_builder_writes_manifest_only_outputs_when_enabled",
        "test_sha256sums_excludes_report": '"manifest_builder_report.json" not in sha_text',
        "test_rejects_wrong_audit_scope": "test_manifest_builder_rejects_wrong_audit_scope",
        "test_rejects_data_preparation_auth": "test_manifest_builder_rejects_source_review_data_preparation_auth",
        "test_rejects_formal_seed": "test_manifest_builder_rejects_formal_seed_request",
        "test_rejects_target_scale_drift": "test_manifest_builder_rejects_target_scale_drift",
        "test_rejects_dp_drift": "test_manifest_builder_rejects_dp_head_drift",
        "test_rejects_output_escape": "test_manifest_builder_rejects_output_path_outside_output_dir",
    }
    return [_contains(name, text, needle) for name, needle in needles.items()]


def _runbook_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains("runbook_validation_only", text, "validation-only runbook"),
        _contains("runbook_no_dp_execution", text, "no DP execution"),
        _contains("runbook_no_candidate_generation", text, "no candidate generation"),
        _contains("runbook_no_replay", text, "no replay"),
        _contains("runbook_no_training", text, "no training"),
    ]


def _audit_checks(text: str, authorized_current_work: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_next_work_target", _latest_audit_value(text, "next_work_target"), authorized_current_work),
        _expect(
            "audit_latest_status_manifest_builder_complete",
            _latest_audit_value(text, "current_v13_status"),
            (
                "static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_"
                "evaluation_nonoverlap_holdout_data_preparation_manifest_builder_complete"
            ),
        ),
        _expect(
            "audit_authorizes_post_review",
            _latest_audit_value(
                text,
                "static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_"
                "evaluation_nonoverlap_holdout_data_preparation_"
                "post_implementation_static_contract_review_authorized",
            ),
            "True",
        ),
        _expect("audit_blocks_data_preparation", _latest_audit_value(text, "data_preparation_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_training", _latest_audit_value(text, "training_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_replay", _latest_audit_value(text, "replay_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_fixed_dp_generation", _latest_audit_value(text, "fixed_dp_candidate_generation_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_camp_candidate_generation", _latest_audit_value(text, "candidate_generation_by_camp_authorized_by_current_boundary"), "False"),
        _expect("audit_blocks_dp_modification", _latest_audit_value(text, "dp_modification_authorized_by_current_boundary"), "False"),
    ]


def _builder_summary(payload: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    output_hashes = _dict(payload.get("output_hashes"))
    return {
        "schema_version": payload.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "enabled": decision.get("enabled"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "manifest_files_written": decision.get("manifest_files_written"),
        "analysis": analysis,
        "output_hashes": output_hashes,
    }


def _manifest_summary(
    *,
    request_manifest: dict[str, Any],
    exclusion_manifest: dict[str, Any],
    expected_artifact_manifest: dict[str, Any],
) -> dict[str, Any]:
    requests = _list(request_manifest.get("route_seed_requests"))
    seeds = [request.get("seed") for request in requests if isinstance(request, dict)]
    return {
        "request_schema_version": request_manifest.get("schema_version"),
        "request_count": len(requests),
        "target_holdout_records": request_manifest.get("target_holdout_records"),
        "formal_seed_overlap": sorted(set(seeds) & FORMAL_SEEDS),
        "exclusion_schema_version": exclusion_manifest.get("schema_version"),
        "expected_artifact_schema_version": expected_artifact_manifest.get("schema_version"),
    }


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "post_implementation_static_contract_review_complete": passed,
        "data_preparation_authorized_next": passed,
        "fixed_dp_candidate_generation_authorized_next": passed,
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


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256sum_entries(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and _is_sha256(parts[0]):
            entries[parts[-1]] = parts[0]
    return entries


def _latest_audit_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    value: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(prefix):
            value = line[len(prefix) :]
    return value


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


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


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.lower())


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.lower()).strip("_")


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value
