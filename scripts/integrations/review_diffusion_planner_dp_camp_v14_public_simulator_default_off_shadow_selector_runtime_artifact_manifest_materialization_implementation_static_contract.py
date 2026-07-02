#!/usr/bin/env python3
"""Static review for the v14 runtime manifest materializer implementation plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
RUNTIME_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
)
SOURCE_SCOPE = "public_simulator_fixed_dp_candidate_tensor"
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_static_contract_review_v1"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_static_contract_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_static_contract_review_rejected"
)
DISABLED_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_static_contract_review_default_off_disabled"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materializer_implementation_only"
)
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 9
FUTURE_MATERIALIZER = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v14_public_simulator_"
    "default_off_shadow_selector_runtime_artifact_manifest.py"
)
FUTURE_UNIT_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_"
    "default_off_shadow_selector_runtime_artifact_manifest_materializer.py"
)

BLOCKED_ACTIONS = (
    "runtime_artifact_manifest_materialization_authorized",
    "default_off_shadow_selector_runtime_execution_authorized",
    "training_authorized",
    "training_execution_authorized",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
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
    parser.add_argument(
        "--runtime_artifact_manifest_materialization_implementation_plan_json",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--runtime_artifact_manifest_materialization_implementation_plan_script_py",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--runtime_artifact_manifest_materialization_implementation_plan_test_py",
        type=Path,
        required=True,
    )
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument(
        "--enable_v14_public_simulator_runtime_artifact_manifest_materialization_implementation_static_contract_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_artifact_manifest_materialization_implementation_plan_json=(
            args.runtime_artifact_manifest_materialization_implementation_plan_json
        ),
        runtime_artifact_manifest_materialization_implementation_plan_script_py=(
            args.runtime_artifact_manifest_materialization_implementation_plan_script_py
        ),
        runtime_artifact_manifest_materialization_implementation_plan_test_py=(
            args.runtime_artifact_manifest_materialization_implementation_plan_test_py
        ),
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_public_simulator_runtime_artifact_manifest_materialization_implementation_static_contract_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_artifact_manifest_materialization_implementation_plan_json: Path,
    runtime_artifact_manifest_materialization_implementation_plan_script_py: Path,
    runtime_artifact_manifest_materialization_implementation_plan_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
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
        output_dir=output_dir,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    paths = {
        "implementation_plan": (
            runtime_artifact_manifest_materialization_implementation_plan_json
        ),
        "implementation_plan_script": (
            runtime_artifact_manifest_materialization_implementation_plan_script_py
        ),
        "implementation_plan_test": (
            runtime_artifact_manifest_materialization_implementation_plan_test_py
        ),
        "v14_audit": v14_audit_md,
        "current_status": current_status_md,
    }
    checks: list[dict[str, Any]] = [
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
    ]
    payloads: dict[str, Any] = {}
    texts: dict[str, str] = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file"))
        if not path.is_file():
            continue
        report["source_hashes"][f"{name}_sha256"] = _sha256(path)
        if path.suffix == ".json":
            loaded, json_check = _load_json(path, name)
            payloads[name] = loaded
            checks.append(json_check)
        else:
            texts[name] = path.read_text(encoding="utf-8")

    source_plan = _dict(payloads.get("implementation_plan"))
    checks.extend(_source_plan_checks(source_plan))
    checks.extend(_source_surface_checks(texts))
    checks.extend(
        _audit_contract_checks(
            texts.get("v14_audit", ""),
            texts.get("current_status", ""),
        )
    )
    passed = all(check["passed"] for check in checks)
    report["contract_summary"] = _contract_summary(source_plan, report["source_hashes"])
    report["review_scope"] = _review_scope()
    report["future_implementation_contract"] = _future_implementation_contract(source_plan)
    report["forbidden_paths"] = _forbidden_paths()
    report["review_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir
        / "runtime_artifact_manifest_materialization_implementation_static_contract_review.json",
        report,
    )
    (
        output_dir
        / "runtime_artifact_manifest_materialization_implementation_static_contract_review.md"
    ).write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("contract_summary", {})
    contract = report.get("future_implementation_contract", {})
    lines = [
        "# V14 Runtime Manifest Materializer Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Materializer implementation authorized: `{decision['runtime_artifact_manifest_materialization_implementation_authorized']}`",
        f"- Runtime manifest materialization authorized: `{decision['runtime_artifact_manifest_materialization_authorized']}`",
        f"- Runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Plan",
        "",
        f"- Source status: `{summary.get('source_plan_status')}`",
        f"- Planned materializer script: `{contract.get('future_materializer_script')}`",
        f"- Planned materializer test: `{contract.get('future_materializer_test')}`",
        f"- Runtime manifest path: `{contract.get('planned_runtime_manifest_path')}`",
        f"- Runtime schema: `{summary.get('runtime_schema_version')}`",
        f"- Source scope: `{summary.get('source_scope')}`",
        f"- Runtime entries: `{summary.get('runtime_entries')}`",
        f"- Score expression: `{summary.get('score_expression')}`",
        "",
        "## Review Scope",
        "",
    ]
    for item in report.get("review_scope", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Future Implementation Requirements", ""])
    for item in contract.get("required_steps", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Future Unit Tests", ""])
    for item in contract.get("future_unit_tests", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report.get("forbidden_paths", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This review is static only. It does not implement the materializer, "
            "write the runtime manifest, run replay, train CAMP, generate "
            "candidates, modify Diffusion Planner, promote atoms or selectors, "
            "deploy, or authorize safety/CAMP-over-DP claims.",
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
            f"`{_compact(check.get('observed'))}` | `{_compact(check.get('expected'))}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _empty_report(
    *,
    enabled: bool,
    label: str | None,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "output_dir": str(output_dir),
            "enabled": bool(enabled),
            "static_review_only": True,
            "materializer_implemented": False,
            "runtime_artifact_manifest_materialized": False,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "The future materializer may only write an immutable JSON "
                "manifest for existing fixed-DP-candidate reranking artifacts. "
                "It must preserve score_k(w)=a_k^T w and must not generate or "
                "modify trajectories, change DP, train, replay, or route CAMP "
                "into executed selection."
            ),
        },
        "source_hashes": {},
        "contract_summary": {},
        "review_scope": [],
        "future_implementation_contract": {},
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "runtime_artifact_manifest_materialization_implementation_static_contract_review_passed": False,
            "runtime_artifact_manifest_materialization_implementation_authorized": False,
            "runtime_artifact_manifest_materialization_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "runtime_manifest_written_by_this_gate": False,
            "runtime_manifest_materialized_by_this_gate": False,
            "training_executed_by_this_gate": False,
            "failed_checks": [],
            "failure_class": "materialization_implementation_static_review_gate_disabled",
        },
    }


def _source_plan_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    contract = _dict(plan.get("future_materializer_contract"))
    manifest = _dict(contract.get("manifest_required_content"))
    artifacts = _dict(manifest.get("artifacts"))
    aliases = _dict(manifest.get("sha256"))
    atom_entry = _dict(artifacts.get("atom_scales"))
    weights_entry = _dict(artifacts.get("static_weights"))
    steps = _list(contract.get("steps"))
    return [
        _expect("source_plan_schema_version", payload.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status_ready", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_authorizes_this_review", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_plan_ready_flag", decision.get("runtime_artifact_manifest_materialization_implementation_plan_ready"), True),
        _expect("source_plan_static_review_authorized", decision.get("runtime_artifact_manifest_materialization_implementation_static_contract_review_authorized"), True),
        _expect("source_plan_implementation_not_yet_authorized", decision.get("runtime_artifact_manifest_materialization_implementation_authorized"), False),
        _expect("source_plan_materialization_forbidden", decision.get("runtime_artifact_manifest_materialization_authorized"), False),
        _expect("source_plan_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_plan_training_forbidden", decision.get("training_execution_authorized"), False),
        _expect("source_plan_replay_forbidden", decision.get("replay_execution_authorized"), False),
        _expect("source_plan_candidate_generation_forbidden", decision.get("candidate_generation_authorized"), False),
        _expect("source_plan_dp_modification_forbidden", decision.get("dp_modification_authorized"), False),
        _expect("source_plan_manifest_not_written_decision", decision.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_manifest_not_materialized_decision", decision.get("runtime_manifest_materialized_by_this_gate"), False),
        _expect("source_plan_status_no_manifest_written", plan.get("status"), "implementation_plan_ready_no_runtime_manifest_written"),
        _check("source_plan_planned_path_json", str(plan.get("planned_runtime_manifest_path", "")).endswith(".json"), plan.get("planned_runtime_manifest_path"), "*.json"),
        _expect("source_plan_runtime_manifest_not_written", plan.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_runtime_manifest_not_materialized", plan.get("runtime_manifest_materialized_by_this_gate"), False),
        _expect("source_plan_runtime_execution_not_enabled", plan.get("runtime_execution_enabled_by_this_gate"), False),
        _expect("future_write_strategy", contract.get("write_strategy"), "same-directory temp file plus atomic replace"),
        _expect("future_writes_exactly_one_manifest", contract.get("writes_exactly_one_runtime_manifest"), True),
        _expect("future_manifest_output_path_matches", contract.get("planned_output_path"), plan.get("planned_runtime_manifest_path")),
        _expect("future_required_dp_head", contract.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("future_runtime_schema", manifest.get("schema_version"), RUNTIME_SCHEMA_VERSION),
        _expect("future_source_scope", manifest.get("source_scope"), SOURCE_SCOPE),
        _expect("future_manifest_role", manifest.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"),
        _expect("future_default_off", manifest.get("default_off"), True),
        _expect("future_fail_closed", manifest.get("fail_closed"), True),
        _expect("future_selection_effect_false", manifest.get("selection_effect"), False),
        _expect("future_online_selector_change_false", manifest.get("online_selector_change"), False),
        _expect("future_selector_mode", manifest.get("selector_mode"), "static"),
        _expect("future_candidate_operation", manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("future_executed_output_policy", manifest.get("executed_output_policy"), "dp_top1"),
        _expect("future_candidate_count", manifest.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("future_atom_count", manifest.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("future_atom_schema", manifest.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("future_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("future_atom_scales_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("future_atom_scales_path_present", bool(atom_entry.get("path")), atom_entry.get("path"), "nonempty path"),
        _check("future_atom_scales_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("future_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("future_static_weights_path_present", bool(weights_entry.get("path")), weights_entry.get("path"), "nonempty path"),
        _check("future_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _expect("future_atom_logical_alias", aliases.get("atom_scales"), atom_entry.get("sha256")),
        _expect("future_weight_logical_alias", aliases.get("static_weights"), weights_entry.get("sha256")),
        _expect("future_atom_path_alias", aliases.get(atom_entry.get("path")), atom_entry.get("sha256")),
        _expect("future_weight_path_alias", aliases.get(weights_entry.get("path")), weights_entry.get("sha256")),
        _contains_item("future_step_create_parent", steps, "create parent directory for the planned runtime manifest path"),
        _contains_item("future_step_verify_dp_head", steps, "verify DP head equals the fixed TiERIV Diffusion Planner commit"),
        _contains_item("future_step_verify_files_exist", steps, "verify atom_scales and static_weights files exist"),
        _contains_item("future_step_verify_hashes", steps, "verify atom_scales and static_weights sha256 values match the source plan"),
        _contains_item("future_step_build_manifest_only", steps, "build manifest JSON with only atom_scales and static_weights entries plus hash aliases"),
        _contains_item("future_step_validate_contract", steps, "validate manifest schema, source scope, default-off fail-closed policy, K=8, atom_count=9, and affine score expression before write"),
        _contains_item("future_step_atomic_write", steps, "write a temp JSON file in the target directory and fsync before atomic replace"),
        _contains_item("future_step_sha_final", steps, "sha256 the final manifest and emit SHA256SUMS evidence"),
        *[_expect(f"source_plan_{name}_false", decision.get(name), False) for name in BLOCKED_ACTIONS],
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    script = texts.get("implementation_plan_script", "")
    test = texts.get("implementation_plan_test", "")
    return [
        _contains("script_schema_constant", script, "SCHEMA_VERSION"),
        _contains("script_implementation_plan_schema", script, SOURCE_PLAN_SCHEMA_VERSION),
        _contains("script_authorizes_static_review_only", script, SOURCE_AUTHORIZED_NEXT_WORK),
        _contains("script_runtime_schema", script, RUNTIME_SCHEMA_VERSION),
        _contains("script_source_scope", script, SOURCE_SCOPE),
        _contains("script_write_strategy", script, "same-directory temp file plus atomic replace"),
        _contains("script_writes_exactly_one_manifest", script, '"writes_exactly_one_runtime_manifest": True'),
        _contains("script_manifest_written_false", script, '"runtime_manifest_written_by_this_gate": False'),
        _contains("script_manifest_materialized_false", script, '"runtime_manifest_materialized_by_this_gate": False'),
        _contains("script_implementation_forbidden", script, '"runtime_artifact_manifest_materialization_implementation_authorized": False'),
        _contains("script_materialization_forbidden", script, '"runtime_artifact_manifest_materialization_authorized": False'),
        _contains("script_score_expression", script, SCORE_EXPRESSION),
        _contains("test_ready_case", test, "test_runtime_artifact_manifest_materialization_implementation_plan_ready"),
        _contains("test_disabled_case", test, "test_runtime_artifact_manifest_materialization_implementation_plan_disabled"),
        _contains("test_rejects_review_authorization_leak", test, "test_runtime_artifact_manifest_materialization_implementation_plan_rejects_review_authorization_leak"),
        _contains("test_rejects_written_manifest", test, "test_runtime_artifact_manifest_materialization_implementation_plan_rejects_written_manifest"),
        _contains("test_rejects_stale_schema", test, "test_runtime_artifact_manifest_materialization_implementation_plan_rejects_stale_schema"),
        _contains("test_rejects_wrong_eof", test, "test_runtime_artifact_manifest_materialization_implementation_plan_rejects_wrong_eof"),
    ]


def _audit_contract_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    current_pending = (
        f"current_v14_status={SOURCE_PLAN_STATUS}" in eof
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof
    )
    current_complete = (
        f"current_v14_status={READY_STATUS}" in eof
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in eof
    )
    status_pending = (
        f"current_v14_status={SOURCE_PLAN_STATUS}" in status_text
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text
    )
    status_complete = (
        f"current_v14_status={READY_STATUS}" in status_text
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in status_text
    )
    return [
        _check(
            "audit_latest_boundary_matches_materialization_implementation_static_review_gate",
            current_pending or current_complete,
            {
                "status": _extract_line(eof, "current_v14_status="),
                "next": _extract_line(eof, "next_work_target="),
            },
            "pending implementation static-review gate or completed review gate",
        ),
        _check(
            "current_status_boundary_matches_materialization_implementation_static_review_gate",
            status_pending or status_complete,
            {"pending": status_pending, "complete": status_complete},
            "pending implementation static-review gate or completed review gate",
        ),
        _contains("audit_records_implementation_plan_ready", eof, "runtime_artifact_manifest_materialization_implementation_plan_ready=True"),
        _contains("audit_authorizes_static_review", eof, "runtime_artifact_manifest_materialization_implementation_static_contract_review_authorized=True"),
        _contains("audit_blocks_implementation", eof, "runtime_artifact_manifest_materialization_implementation_authorized=False"),
        _contains("audit_blocks_materialization", eof, "runtime_artifact_manifest_materialization_authorized=False"),
        _contains("audit_blocks_runtime_execution", eof, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_blocks_safety_claim", eof, "safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _contract_summary(payload: dict[str, Any], source_hashes: dict[str, str]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    contract = _dict(plan.get("future_materializer_contract"))
    manifest = _dict(contract.get("manifest_required_content"))
    artifacts = _dict(manifest.get("artifacts"))
    return {
        "source_hashes": source_hashes,
        "source_plan_status": decision.get("status"),
        "source_plan_passed": decision.get("passed"),
        "source_plan_authorized_next_work": decision.get("authorized_next_work"),
        "planned_runtime_manifest_path": plan.get("planned_runtime_manifest_path"),
        "runtime_schema_version": manifest.get("schema_version"),
        "source_scope": manifest.get("source_scope"),
        "runtime_entries": sorted(artifacts),
        "score_expression": manifest.get("score_expression"),
    }


def _future_implementation_contract(payload: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(payload.get("implementation_plan"))
    contract = _dict(plan.get("future_materializer_contract"))
    return {
        "future_materializer_script": FUTURE_MATERIALIZER,
        "future_materializer_test": FUTURE_UNIT_TEST,
        "planned_runtime_manifest_path": plan.get("planned_runtime_manifest_path"),
        "required_steps": contract.get("steps", []),
        "future_unit_tests": [
            "test_materializer_is_default_off_and_does_not_read_missing_inputs",
            "test_materializer_writes_exact_runtime_manifest_shape_when_enabled",
            "test_materializer_rejects_hash_mismatch_without_output",
            "test_materializer_rejects_dp_head_drift_without_output",
            "test_materializer_rejects_runtime_or_promotion_authorization_leaks",
            "test_materializer_does_not_run_replay_train_or_touch_dp_sources",
        ],
    }


def _review_scope() -> list[str]:
    return [
        "source materialization implementation plan JSON",
        "source materialization implementation plan script",
        "source materialization implementation plan tests",
        "current v14 audit EOF",
        "current status document",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "implementing the materializer during this static review",
        "writing the runtime manifest during this static review",
        "running replay or enabling shadow runtime execution",
        "training CAMP or changing static weights",
        "generating, modifying, blending, guiding, or postprocessing trajectories",
        "modifying, retraining, or tuning TiERIV Diffusion Planner",
        "promoting atoms, selectors, deployment artifacts, or safety claims",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "runtime_artifact_manifest_materialization_implementation_static_contract_review_passed": bool(passed),
        "runtime_artifact_manifest_materialization_implementation_authorized": bool(passed),
        "runtime_artifact_manifest_materialization_authorized": False,
        "default_off_shadow_selector_runtime_execution_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "runtime_manifest_written_by_this_gate": False,
        "runtime_manifest_materialized_by_this_gate": False,
        "training_executed_by_this_gate": False,
        "score_expression": SCORE_EXPRESSION,
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
    }


def _failure_class(failed: list[str]) -> str:
    if not failed:
        return "unknown"
    if any(name.startswith("source_plan_") or name.startswith("future_") for name in failed):
        return "runtime_manifest_materialization_implementation_plan_contract_failure"
    if any(name.startswith("script_") or name.startswith("test_") for name in failed):
        return "source_surface_contract_failure"
    if any(name.startswith("audit_") or name.startswith("current_status_") for name in failed):
        return "v14_eof_contract_mismatch"
    return "runtime_manifest_materialization_implementation_static_contract_failure"


def _load_json(path: Path, name: str) -> tuple[Any, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, _check(f"{name}_valid_json", False, type(exc).__name__, "valid JSON")
    return payload, _check(f"{name}_json_object", isinstance(payload, dict), type(payload).__name__, "dict")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _contains_item(name: str, values: list[Any], expected: str) -> dict[str, Any]:
    return _check(name, expected in values, values, f"list containing {expected}")


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


def _compact(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 160 else text[:157] + "..."


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value
    )


def _latest_text_block(text: str) -> str:
    marker = "\n## "
    index = text.rfind(marker)
    return text[index + 1 :] if index >= 0 else text


def _extract_line(text: str, prefix: str) -> str | None:
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


if __name__ == "__main__":
    raise SystemExit(main())
