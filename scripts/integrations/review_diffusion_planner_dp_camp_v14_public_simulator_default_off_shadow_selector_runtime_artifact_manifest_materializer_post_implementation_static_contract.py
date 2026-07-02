#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_"
    "manifest_materializer_post_implementation_static_contract_review_v1"
)
DISABLED_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_"
    "manifest_materializer_post_implementation_static_contract_review_default_off_disabled"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_"
    "manifest_materializer_post_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_"
    "manifest_materializer_post_implementation_static_contract_review_rejected"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_"
    "manifest_materializer_post_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_"
    "manifest_materialization_only"
)
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_"
    "manifest_materialization_implementation_plan_v1"
)
SOURCE_PLAN_READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_"
    "manifest_materialization_implementation_plan_ready"
)
MATERIALIZER_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_"
    "manifest_materializer_v1"
)
RUNTIME_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
)
SOURCE_SCOPE = "public_simulator_fixed_dp_candidate_tensor"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 9
RUNTIME_ENTRIES = ("atom_scales", "static_weights")

BLOCKED_AUTHORIZATIONS = (
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
    "executed_trajectory_change_authorized",
    "training_authorized",
    "training_execution_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Static post-implementation contract review for the v14 public "
            "simulator default-off runtime artifact manifest materializer. "
            "This reads source, tests, plans, and audits only."
        )
    )
    parser.add_argument(
        "--runtime_artifact_manifest_materialization_implementation_plan_json",
        type=Path,
        required=True,
    )
    parser.add_argument("--materializer_script_py", type=Path, required=True)
    parser.add_argument("--materializer_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v14_public_simulator_runtime_artifact_manifest_materializer_post_implementation_static_contract_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_artifact_manifest_materialization_implementation_plan_json=(
            args.runtime_artifact_manifest_materialization_implementation_plan_json
        ),
        materializer_script_py=args.materializer_script_py,
        materializer_test_py=args.materializer_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_public_simulator_runtime_artifact_manifest_materializer_post_implementation_static_contract_review
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
    runtime_artifact_manifest_materialization_implementation_plan_json: Path,
    materializer_script_py: Path,
    materializer_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
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
    )
    if not enabled:
        return report

    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
    ]
    paths = {
        "source_implementation_plan": runtime_artifact_manifest_materialization_implementation_plan_json,
        "materializer_script": materializer_script_py,
        "materializer_test": materializer_test_py,
        "v14_audit": v14_audit_md,
        "current_status": current_status_md,
    }
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
        else:
            texts[name] = path.read_text(encoding="utf-8")

    source_plan = _dict(payloads.get("source_implementation_plan"))
    checks.extend(_source_plan_checks(source_plan))
    checks.extend(_planned_runtime_manifest_checks(source_plan))
    checks.extend(_materializer_source_checks(texts.get("materializer_script", "")))
    checks.extend(_materializer_test_checks(texts.get("materializer_test", "")))
    checks.extend(_audit_checks(texts.get("v14_audit", "")))
    checks.extend(_current_status_checks(texts.get("current_status", "")))

    passed = all(check["passed"] for check in checks)
    report["contract_summary"] = _contract_summary(source_plan, report["source_hashes"])
    report["review_scope"] = _review_scope()
    report["forbidden_paths"] = _forbidden_paths()
    report["review_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("contract_summary", {})
    lines = [
        "# DP-CAMP V14 Default-Off Shadow Selector Runtime Artifact Manifest Materializer Post-Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Runtime manifest materialization authorized: `{decision['runtime_artifact_manifest_materialization_authorized']}`",
        f"- Shadow runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Contract Summary",
        "",
        f"- Planned runtime manifest path: `{summary.get('planned_runtime_manifest_path')}`",
        f"- Planned runtime manifest exists now: `{summary.get('planned_runtime_manifest_exists')}`",
        f"- Runtime schema: `{summary.get('runtime_manifest_schema_version')}`",
        f"- Runtime entries: `{summary.get('runtime_entries')}`",
        "",
        "## Review Scope",
        "",
    ]
    for item in report.get("review_scope", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report.get("forbidden_paths", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This review is static only. It does not materialize the real runtime "
            "manifest, execute replay, enable the shadow selector, train CAMP, "
            "generate candidates, modify DP, promote, deploy, or authorize "
            "safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
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
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "static_review_only": True,
            "real_runtime_manifest_materialized": False,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "dp_modification_execution": False,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "source_hashes": {},
        "contract_summary": {},
        "review_scope": [],
        "forbidden_paths": [],
        "blocked_authorizations": {name: False for name in BLOCKED_AUTHORIZATIONS},
        "review_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed": False,
            "runtime_artifact_manifest_materialization_authorized": False,
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
            "executed_trajectory_change_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "training_executed": False,
            "failed_checks": [],
        },
    }


def _source_plan_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    contract = _dict(plan.get("future_materializer_contract"))
    future = _dict(contract.get("manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    aliases = _dict(future.get("sha256"))
    claims = _dict(future.get("forbidden_runtime_claims"))
    atom_entry = _dict(artifacts.get("atom_scales"))
    weights_entry = _dict(artifacts.get("static_weights"))
    checks = [
        _expect("source_plan_schema_version", payload.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status_ready", decision.get("status"), SOURCE_PLAN_READY_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_not_manifest_written", plan.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_not_manifest_materialized", plan.get("runtime_manifest_materialized_by_this_gate"), False),
        _expect("source_plan_runtime_not_enabled", plan.get("runtime_execution_enabled_by_this_gate"), False),
        _expect("source_plan_write_strategy", contract.get("write_strategy"), "same-directory temp file plus atomic replace"),
        _expect("source_plan_writes_exactly_one_manifest", contract.get("writes_exactly_one_runtime_manifest"), True),
        _check("source_plan_planned_output_json", str(contract.get("planned_output_path", "")).endswith(".json"), contract.get("planned_output_path"), "*.json"),
        _expect("source_plan_required_dp_head", contract.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("future_manifest_schema", future.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("future_manifest_role", future.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"),
        _expect("future_manifest_source_scope", future.get("source_scope"), SOURCE_SCOPE),
        _expect("future_manifest_default_off", future.get("default_off"), True),
        _expect("future_manifest_fail_closed", future.get("fail_closed"), True),
        _expect("future_manifest_selection_effect_false", future.get("selection_effect"), False),
        _expect("future_manifest_online_selector_change_false", future.get("online_selector_change"), False),
        _expect("future_manifest_selector_mode_static", future.get("selector_mode"), "static"),
        _expect("future_manifest_candidate_operation", future.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("future_manifest_executed_policy", future.get("executed_output_policy"), "dp_top1"),
        _expect("future_manifest_candidate_count", future.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("future_manifest_atom_count", future.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("future_manifest_atom_schema", future.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("future_manifest_score_expression", future.get("score_expression"), SCORE_EXPRESSION),
        _expect("future_manifest_artifact_keys", sorted(artifacts), sorted(RUNTIME_ENTRIES)),
        _expect("future_manifest_atom_entry_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("future_manifest_atom_entry_path_present", bool(atom_entry.get("path")), atom_entry.get("path"), "nonempty path"),
        _check("future_manifest_atom_entry_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("future_manifest_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("future_manifest_static_weights_path_present", bool(weights_entry.get("path")), weights_entry.get("path"), "nonempty path"),
        _check("future_manifest_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _expect("future_manifest_alias_atom_scales", aliases.get("atom_scales"), atom_entry.get("sha256")),
        _expect("future_manifest_alias_static_weights", aliases.get("static_weights"), weights_entry.get("sha256")),
        _expect("future_manifest_alias_atom_path", aliases.get(atom_entry.get("path")), atom_entry.get("sha256")),
        _expect("future_manifest_alias_weight_path", aliases.get(weights_entry.get("path")), weights_entry.get("sha256")),
        _expect("future_manifest_alias_atom_basename", aliases.get(Path(str(atom_entry.get("path"))).name), atom_entry.get("sha256")),
        _expect("future_manifest_alias_weight_basename", aliases.get(Path(str(weights_entry.get("path"))).name), weights_entry.get("sha256")),
    ]
    for name in BLOCKED_AUTHORIZATIONS:
        if name in decision:
            checks.append(_expect(f"source_plan_{name}_false", decision.get(name), False))
    for name in (
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "deployment_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
    ):
        checks.append(_expect(f"future_manifest_{name}_false", claims.get(name), False))
    return checks


def _planned_runtime_manifest_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    plan = _dict(payload.get("implementation_plan"))
    contract = _dict(plan.get("future_materializer_contract"))
    path_value = contract.get("planned_output_path")
    if not isinstance(path_value, str) or not path_value:
        return [_check("planned_runtime_manifest_absent_now", False, path_value, "nonexistent path")]
    path = Path(path_value)
    return [_check("planned_runtime_manifest_absent_now", not path.exists(), str(path), "path does not exist")]


def _materializer_source_checks(source: str) -> list[dict[str, Any]]:
    return [
        _contains("materializer_schema_constant", source, MATERIALIZER_SCHEMA_VERSION),
        _contains("materializer_source_plan_schema", source, SOURCE_PLAN_SCHEMA_VERSION),
        _contains("materializer_default_off_status", source, "runtime_artifact_manifest_materializer_default_off_disabled"),
        _contains("materializer_enable_flag", source, "--enable_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer"),
        _contains("materializer_default_off_short_circuit", source, "if not enabled:"),
        _contains("materializer_plan_sha_check", source, "implementation_plan_sha256_matches_expected"),
        _contains("materializer_output_path_check", source, "output_path_matches_source_plan"),
        _contains("materializer_existing_output_check", source, "output_runtime_manifest_absent_before_write"),
        _contains("materializer_fixed_dp_check", source, "current_dp_head_fixed"),
        _contains("materializer_artifact_hash_checks", source, '_expect(f"{logical_name}_sha256_matches"'),
        _contains("materializer_runtime_entries", source, '("atom_scales", "static_weights")'),
        _contains("materializer_atomic_write", source, "_atomic_write_json"),
        _contains("materializer_os_replace", source, "os.replace"),
        _contains("materializer_fsync", source, "os.fsync"),
        _contains("materializer_runtime_manifest_schema", source, RUNTIME_MANIFEST_SCHEMA_VERSION),
        _contains("materializer_source_scope", source, SOURCE_SCOPE),
        _contains("materializer_fail_closed", source, '"fail_closed": True'),
        _contains("materializer_fixed_candidate_boundary", source, "fixed DP candidate reranking only"),
        _contains("materializer_score_expression", source, SCORE_EXPRESSION),
        _contains("materializer_execution_policy", source, "dp_top1"),
        _contains("materializer_authorizations_block", source, '"authorizations"'),
        _contains("materializer_runtime_execution_false", source, '"default_off_shadow_selector_runtime_execution_authorized": False'),
        _contains("materializer_materialization_false", source, '"runtime_artifact_manifest_materialization_authorized": False'),
        _contains("materializer_training_false", source, '"training_executed": False'),
        _not_contains("materializer_no_subprocess", source, "subprocess"),
        _not_contains("materializer_no_replay_runner", source, "run_diffusion_planner"),
        _not_contains("materializer_no_autodl_dp_path", source, "/root/autodl-tmp/Diffusion-Planner"),
        _not_contains("materializer_no_dp_repo_token", source, "Diffusion-Planner"),
    ]


def _materializer_test_checks(source: str) -> list[dict[str, Any]]:
    return [
        _contains("test_default_off", source, "test_materializer_is_default_off_and_does_not_read_missing_inputs"),
        _contains("test_writes_manifest_shape", source, "test_materializer_writes_exact_runtime_manifest_shape_when_enabled"),
        _contains("test_plan_hash_mismatch", source, "test_materializer_rejects_plan_hash_mismatch_without_output"),
        _contains("test_artifact_hash_mismatch", source, "test_materializer_rejects_hash_mismatch_without_output"),
        _contains("test_dp_head_drift", source, "test_materializer_rejects_dp_head_drift_without_output"),
        _contains("test_output_path_drift", source, "test_materializer_rejects_output_path_drift_without_output"),
        _contains("test_existing_output", source, "test_materializer_rejects_existing_output_without_overwrite"),
        _contains("test_schema_candidate_drift", source, "test_materializer_rejects_schema_or_candidate_count_drift_without_output"),
        _contains("test_authorization_leak", source, "test_materializer_rejects_runtime_or_promotion_authorization_leaks"),
        _contains("test_atomic_replace", source, "test_materializer_uses_same_directory_temp_and_atomic_replace"),
        _contains("test_no_replay_or_dp_touch", source, "test_materializer_does_not_run_replay_train_or_touch_dp_sources"),
        _contains("test_cli_writes_manifest", source, "test_materializer_cli_writes_manifest"),
    ]


def _audit_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains("audit_current_scope_authorizes_this_review", text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_implementation_complete", text, "runtime_artifact_manifest_materializer_implementation_complete=True"),
        _contains("audit_post_review_authorized", text, "runtime_artifact_manifest_materializer_post_implementation_static_contract_review_authorized=True"),
        _contains("audit_materialization_blocked", text, "runtime_artifact_manifest_materialization_authorized=False"),
        _contains("audit_runtime_blocked", text, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_no_camp_generation", text, "candidate_generation_by_camp_authorized_by_current_boundary=False"),
        _contains("audit_no_dp_modification", text, "dp_modification_authorized_by_current_boundary=False"),
        _contains("audit_no_safety_claim", text, "safety_benefit_claim_authorized=False"),
        _contains("audit_no_camp_over_dp", text, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _current_status_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains("current_status_latest_status", text, "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_complete"),
        _contains("current_status_next_target", text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("current_status_no_materialization", text, "materialize the real planned runtime manifest"),
        _contains("current_status_post_review_only", text, "post-implementation static contract review only"),
    ]


def _contract_summary(payload: dict[str, Any], hashes: dict[str, str]) -> dict[str, Any]:
    plan = _dict(payload.get("implementation_plan"))
    contract = _dict(plan.get("future_materializer_contract"))
    future = _dict(contract.get("manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    planned_path = contract.get("planned_output_path")
    return {
        "source_hashes": hashes,
        "planned_runtime_manifest_path": planned_path,
        "planned_runtime_manifest_exists": Path(str(planned_path)).exists()
        if isinstance(planned_path, str)
        else None,
        "runtime_manifest_schema_version": future.get("schema_version"),
        "runtime_entries": sorted(artifacts),
    }


def _review_scope() -> list[str]:
    return [
        "runtime artifact manifest materializer implementation source",
        "runtime artifact manifest materializer focused tests",
        "source implementation-plan JSON and planned output path absence",
        "current v14 audit EOF boundary",
        "current status boundary",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "materializing the real runtime manifest during this static review",
        "running replay or enabling the default-off shadow selector runtime",
        "training CAMP or changing static weights",
        "generating or modifying DP candidate trajectories",
        "modifying, retraining, or tuning Diffusion Planner",
        "promoting atoms, selectors, deployment artifacts, or safety claims",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed": bool(passed),
        "runtime_artifact_manifest_materialization_authorized": bool(passed),
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
        "executed_trajectory_change_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "training_executed": False,
        "failed_checks": failed,
    }


def _load_json(path: Path, name: str) -> tuple[Any, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, _check(f"{name}_valid_json", False, type(exc).__name__, "valid JSON")
    return payload, _check(f"{name}_json_object", isinstance(payload, dict), type(payload).__name__, "dict")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _not_contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle not in text, needle if needle in text else "absent", f"no {needle}")


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


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value.lower()
    )


if __name__ == "__main__":
    raise SystemExit(main())
