#!/usr/bin/env python3
"""Post-implementation static review for v13 default-off member-source generation.

This gate is read-only. It verifies that the implemented builder stayed bounded
to existing fixed-DP candidate-member inputs and fail-closed zero-overlap
outputs before authorizing only a future fixed-DP candidate-generation plan. It
does not run Diffusion Planner, generate candidates, prepare data, replay, train
CAMP, modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v13_default_off_member_source_generation_"
    "post_implementation_static_contract_review_v1"
)
READY_STATUS = (
    "dp_camp_v13_default_off_member_source_generation_"
    "post_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_member_source_generation_"
    "post_implementation_static_contract_review_rejected"
)
SOURCE_BUILDER_SCHEMA_VERSION = (
    "dp_camp_v13_default_off_member_source_generation_builder_v1"
)
SOURCE_BUILDER_STATUS = (
    "dp_camp_v13_default_off_member_source_generation_builder_complete"
)
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_default_off_"
    "member_source_generation_implementation_complete"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_default_off_member_source_generation_"
    "post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_plan_only"
)
ZERO_INTERSECTION_KEYS = (
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
REQUIRED_BUILDER_TERMS = (
    SOURCE_BUILDER_SCHEMA_VERSION,
    SOURCE_BUILDER_STATUS,
    "--enable_default_off_member_source_generation_builder",
    "DISABLED_STATUS",
    "REJECT_STATUS",
    "fixed DP candidate reranking only",
    SCORE_EXPRESSION,
    "selected_index",
    "executed_index",
    "shadow_selected_index",
    "fixed_dp_candidate_generation_execution",
    "fixed_dp_candidate_generation_executed",
    "candidate_generation_by_camp",
    "trajectory_generation_by_camp",
    "trajectory_modification_by_camp",
    "training_execution",
    "training_executed",
    "dp_modification",
    "FORMAL_SEEDS = {11, 12, 13}",
    "ZERO_INTERSECTION_KEYS",
    "candidate_tensor_hash_intersection_count",
    "path_signature_intersection_count",
    "record_identity_intersection_count",
    "split_manifest_root_intersection_count",
)
REQUIRED_TEST_TERMS = (
    "test_default_off_member_source_generation_builder_passes_and_writes_outputs",
    "test_default_off_member_source_generation_builder_is_default_disabled",
    "test_default_off_member_source_generation_builder_rejects_default_off_contract_break",
    "test_default_off_member_source_generation_builder_rejects_wrong_audit_target",
    "test_default_off_member_source_generation_builder_main_writes_outputs",
)
FALSE_DECISION_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_executed",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "replay_execution_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "training_executed",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fresh_member_source_materialization_execution_authorized_next",
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "fresh_evaluation_split_evaluation_result_review_authorized_next",
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builder_script_py", type=Path, required=True)
    parser.add_argument("--builder_test_py", type=Path, required=True)
    parser.add_argument("--implementation_artifact_dir", type=Path, required=True)
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
        builder_script_py=args.builder_script_py,
        builder_test_py=args.builder_test_py,
        implementation_artifact_dir=args.implementation_artifact_dir,
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
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    builder_script_py: Path,
    builder_test_py: Path,
    implementation_artifact_dir: Path,
    v13_audit_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    paths = {
        "builder_script_py": builder_script_py.resolve(),
        "builder_test_py": builder_test_py.resolve(),
        "implementation_artifact_dir": implementation_artifact_dir.resolve(),
        "v13_audit_md": v13_audit_md.resolve(),
    }
    artifact_paths = _artifact_paths(paths["implementation_artifact_dir"])
    builder_payload = _load_json_dict(artifact_paths["report_json"])
    manifest_payload = _load_json_dict(artifact_paths["manifest_json"])
    preflight_payload = _load_json_dict(artifact_paths["preflight_inputs_json"])
    script_text = _read_text(paths["builder_script_py"])
    test_text = _read_text(paths["builder_test_py"])
    audit_text = _read_text(paths["v13_audit_md"])
    heads_text = _read_text(artifact_paths["heads"])
    checks = _checks(
        paths=paths,
        artifact_paths=artifact_paths,
        builder_payload=builder_payload,
        manifest_payload=manifest_payload,
        preflight_payload=preflight_payload,
        script_text=script_text,
        test_text=test_text,
        audit_text=audit_text,
        heads_text=heads_text,
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
            "post_implementation_static_contract_review_only": True,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "data_preparation_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "dp_modification": False,
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
        "paths": {key: str(value) for key, value in paths.items()},
        "artifact_paths": {key: str(value) for key, value in artifact_paths.items()},
        "artifact_summary": _artifact_summary(
            builder_payload=builder_payload,
            manifest_payload=manifest_payload,
            preflight_payload=preflight_payload,
            artifact_paths=artifact_paths,
            heads_text=heads_text,
        ),
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def _checks(
    *,
    paths: dict[str, Path],
    artifact_paths: dict[str, Path],
    builder_payload: dict[str, Any],
    manifest_payload: dict[str, Any],
    preflight_payload: dict[str, Any],
    script_text: str,
    test_text: str,
    audit_text: str,
    heads_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    decision = _dict(builder_payload.get("final_decision"))
    summary = _dict(builder_payload.get("selection_summary"))
    zero_counts = _dict(summary.get("zero_intersection_counts"))
    checks = [
        _check("builder_script_exists", paths["builder_script_py"].is_file(), str(paths["builder_script_py"]), "file exists"),
        _check("builder_test_exists", paths["builder_test_py"].is_file(), str(paths["builder_test_py"]), "file exists"),
        _check("implementation_artifact_exists", paths["implementation_artifact_dir"].is_dir(), str(paths["implementation_artifact_dir"]), "directory exists"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("artifact_dp_head_fixed", _heads_value(heads_text, "dp_head"), required_dp_head),
        _expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS),
        _expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_authorizes_post_review", _latest_value(audit_text, "default_off_member_source_generation_post_implementation_static_contract_review_authorized_next"), "True"),
    ]
    checks.extend(
        _expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False")
        for flag in AUDIT_FALSE_FLAGS
    )
    checks.extend(
        _check(f"builder_contains_{_slug(term)}", term in script_text, term if term in script_text else "missing", term)
        for term in REQUIRED_BUILDER_TERMS
    )
    checks.extend(
        _check(f"test_contains_{_slug(term)}", term in test_text, term if term in test_text else "missing", term)
        for term in REQUIRED_TEST_TERMS
    )
    checks.extend(
        _check(f"artifact_path_exists_{name}", path.exists(), str(path), "exists")
        for name, path in artifact_paths.items()
    )
    checks.extend(
        [
            _expect("implementation_artifact_exit_zero", _read_text(artifact_paths["run_exit"]).strip(), "0"),
            _expect("implementation_artifact_sha_check_exit_zero", _read_text(artifact_paths["sha_check_exit"]).strip(), "0"),
            _expect("source_schema_version", builder_payload.get("schema_version"), SOURCE_BUILDER_SCHEMA_VERSION),
            _expect("source_decision_status", decision.get("status"), SOURCE_BUILDER_STATUS),
            _expect("source_decision_passed", decision.get("passed"), True),
            _expect("source_failed_checks_empty", decision.get("failed_checks"), []),
            _expect("source_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            _expect("source_implementation_complete", decision.get("implementation_complete"), True),
            _expect("source_post_review_authorized", decision.get("post_implementation_static_contract_review_authorized_next"), True),
            _expect("source_candidate_operation", decision.get("candidate_operation"), "fixed DP candidate reranking only"),
            _expect("source_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
            _check("selected_member_count_positive", _as_int(summary.get("selected_member_count")) is not None and _as_int(summary.get("selected_member_count")) > 0, summary.get("selected_member_count"), "> 0"),
            _check("manifest_written", summary.get("manifest_written") is True, summary.get("manifest_written"), True),
            _expect("manifest_candidate_operation", manifest_payload.get("candidate_operation"), "fixed DP candidate reranking only"),
            _expect("manifest_score_expression", manifest_payload.get("score_expression"), SCORE_EXPRESSION),
            _expect("manifest_fixed_dp_candidate_generation_not_executed", manifest_payload.get("fixed_dp_candidate_generation_executed"), False),
            _expect("manifest_training_not_executed", manifest_payload.get("training_executed"), False),
        ]
    )
    checks.extend(
        _expect(f"source_forbids_{flag}", decision.get(flag), False)
        for flag in FALSE_DECISION_FLAGS
    )
    checks.extend(
        _expect(f"zero_{key}", zero_counts.get(key), 0) for key in ZERO_INTERSECTION_KEYS
    )
    checks.extend(
        _expect(f"preflight_zero_{key}", _dict(preflight_payload.get("zero_intersection_counts")).get(key), 0)
        for key in ZERO_INTERSECTION_KEYS
    )
    return checks


def _artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "heads": root / "HEADS",
        "command": root / "COMMAND.sh",
        "stdout": root / "stdout.log",
        "stderr": root / "stderr.log",
        "run_exit": root / "run.exit",
        "report_json": root / "default_off_member_source_generation_builder_report.json",
        "report_md": root / "default_off_member_source_generation_builder_report.md",
        "manifest_json": root / "generated_outputs" / "default_off_member_source_generation_manifest.json",
        "preflight_inputs_json": root / "generated_outputs" / "zero_overlap_preflight_inputs.json",
        "sha256sums": root / "SHA256SUMS",
        "sha_check_exit": root / "SHA256SUMS.check.exit",
    }


def _artifact_summary(
    *,
    builder_payload: dict[str, Any],
    manifest_payload: dict[str, Any],
    preflight_payload: dict[str, Any],
    artifact_paths: dict[str, Path],
    heads_text: str,
) -> dict[str, Any]:
    decision = _dict(builder_payload.get("final_decision"))
    summary = _dict(builder_payload.get("selection_summary"))
    return {
        "dp_head": _heads_value(heads_text, "dp_head"),
        "schema_version": builder_payload.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selected_member_count": summary.get("selected_member_count"),
        "rejected_member_count": summary.get("rejected_member_count"),
        "zero_intersection_counts": summary.get("zero_intersection_counts"),
        "manifest_member_count": len(_list(manifest_payload.get("members"))),
        "preflight_schema_version": preflight_payload.get("schema_version"),
        "artifact_hashes": {
            name: _sha256(path) for name, path in artifact_paths.items() if path.is_file()
        },
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
        "fixed_dp_candidate_generation_plan_authorized_next": passed,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "replay_execution_authorized_next": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["artifact_summary"]
    lines = [
        "# Default-Off Member-Source Generation Post-Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized current work: `{decision['authorized_current_work']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Fixed-DP candidate generation plan authorized next: `{decision['fixed_dp_candidate_generation_plan_authorized_next']}`",
        f"- Fixed-DP candidate generation execution authorized next: `{decision['fixed_dp_candidate_generation_execution_authorized_next']}`",
        f"- Training authorized next: `{decision['training_execution_authorized_next']}`",
        f"- DP modification authorized: `{decision['dp_modification_authorized']}`",
        f"- Candidate operation: `{decision['candidate_operation']}`",
        f"- Score expression: `{decision['score_expression']}`",
        f"- Source selected member count: `{summary['selected_member_count']}`",
        f"- Source zero intersections: `{summary['zero_intersection_counts']}`",
        "",
        "This review is read-only and does not execute DP, generate candidates, train, replay, promote, deploy, or make safety/CAMP-over-DP claims.",
        "",
    ]
    return "\n".join(lines)


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _latest_value(text: str, key: str) -> str | None:
    matches = re.findall(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return matches[-1].strip() if matches else None


def _heads_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}=(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


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
    if isinstance(value, set):
        return sorted(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
