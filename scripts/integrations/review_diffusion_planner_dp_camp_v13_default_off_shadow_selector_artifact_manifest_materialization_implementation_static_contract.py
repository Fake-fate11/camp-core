#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_rejected"
)
SOURCE_PLAN_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14
FUTURE_MATERIALIZER = (
    "scripts/integrations/build_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest.py"
)
FUTURE_UNIT_TEST = (
    "camp_core/tests/test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer.py"
)

BLOCKED_ACTIONS = (
    "artifact_manifest_materialization_authorized",
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
    "production_selector_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Static contract review for the v13 default-off shadow selector "
            "runtime artifact manifest materializer implementation plan. This "
            "review is read-only: it does not implement the materializer, write "
            "the runtime manifest, run replay, train CAMP, generate candidates, "
            "modify DP, promote, deploy, or authorize safety/CAMP-over-DP claims."
        )
    )
    parser.add_argument("--artifact_manifest_materialization_implementation_plan_json", type=Path, required=True)
    parser.add_argument("--artifact_manifest_materialization_implementation_plan_script_py", type=Path, required=True)
    parser.add_argument("--artifact_manifest_materialization_implementation_plan_test_py", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        artifact_manifest_materialization_implementation_plan_json=(
            args.artifact_manifest_materialization_implementation_plan_json
        ),
        artifact_manifest_materialization_implementation_plan_script_py=(
            args.artifact_manifest_materialization_implementation_plan_script_py
        ),
        artifact_manifest_materialization_implementation_plan_test_py=(
            args.artifact_manifest_materialization_implementation_plan_test_py
        ),
        replay_runner_py=args.replay_runner_py,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review
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
    artifact_manifest_materialization_implementation_plan_json: Path,
    artifact_manifest_materialization_implementation_plan_script_py: Path,
    artifact_manifest_materialization_implementation_plan_test_py: Path,
    replay_runner_py: Path,
    v13_audit_md: Path,
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

    paths = {
        "artifact_manifest_materialization_implementation_plan": (
            artifact_manifest_materialization_implementation_plan_json
        ),
        "artifact_manifest_materialization_implementation_plan_script": (
            artifact_manifest_materialization_implementation_plan_script_py
        ),
        "artifact_manifest_materialization_implementation_plan_test": (
            artifact_manifest_materialization_implementation_plan_test_py
        ),
        "replay_runner": replay_runner_py,
        "v13_audit": v13_audit_md,
    }
    checks: list[dict[str, Any]] = [
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
    ]
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

    source_plan = _dict(payloads.get("artifact_manifest_materialization_implementation_plan"))
    checks.extend(_source_plan_checks(source_plan))
    checks.extend(_source_surface_checks(texts))
    passed = all(check["passed"] for check in checks)

    report["contract_summary"] = _contract_summary(source_plan, report["source_hashes"])
    report["review_scope"] = _review_scope()
    report["future_implementation_contract"] = _future_implementation_contract(source_plan)
    report["forbidden_paths"] = _forbidden_paths()
    report["review_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("contract_summary", {})
    contract = report.get("future_implementation_contract", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Runtime Artifact Manifest Materializer Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Materializer implementation authorized: `{decision['artifact_manifest_materialization_implementation_authorized']}`",
        f"- Runtime manifest materialization authorized: `{decision['artifact_manifest_materialization_authorized']}`",
        f"- Shadow runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Plan",
        "",
        f"- Source status: `{summary.get('source_plan_status')}`",
        f"- Planned materializer script: `{contract.get('future_materializer_script')}`",
        f"- Planned materializer test: `{contract.get('future_materializer_test')}`",
        f"- Runtime manifest path: `{contract.get('planned_runtime_manifest_path')}`",
        f"- Runtime schema: `{summary.get('runtime_manifest_schema_version')}`",
        f"- Runtime entries: `{summary.get('runtime_entries')}`",
        "",
        "## Review Scope",
        "",
    ]
    for item in report.get("review_scope", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Future Implementation Requirements", ""])
    for item in contract.get("required_implementation_steps", []):
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
            "write the runtime manifest, execute replay, enable the shadow "
            "selector, train CAMP, generate candidates, modify DP, promote, "
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
            "name": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review"
            ),
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "static_review_only": True,
            "materializer_implemented": False,
            "artifact_manifest_materialized": False,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "dp_modification_execution": False,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "The future materializer may only write an immutable JSON "
                "manifest for existing fixed-DP-candidate reranking artifacts. "
                "It must preserve score_k(w)=a_k^T w and must not generate or "
                "modify trajectories, change DP, train, or route CAMP into "
                "executed selection."
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
            "artifact_manifest_materialization_implementation_static_contract_review_complete": False,
            "artifact_manifest_materialization_implementation_authorized": False,
            "artifact_manifest_materialization_authorized": False,
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
            "production_selector_change_authorized": False,
            "training_authorization_changed_by_review": False,
            "training_executed": False,
            "failed_checks": [],
        },
    }


def _source_plan_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    entries = _dict(plan.get("future_manifest_entries"))
    atom_entry = _dict(entries.get("atom_scales"))
    weights_entry = _dict(entries.get("static_weights"))
    source_summary = _dict(payload.get("source_summary"))
    return [
        _expect("source_plan_schema_version", payload.get("schema_version"), "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_v1"),
        _expect("source_plan_status_ready", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_authorizes_this_review", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_plan_ready_flag", decision.get("artifact_manifest_materialization_implementation_plan_ready"), True),
        _expect("source_plan_static_review_authorized", decision.get("artifact_manifest_materialization_implementation_static_contract_review_authorized"), True),
        _expect("source_plan_implementation_not_yet_authorized", decision.get("artifact_manifest_materialization_implementation_authorized"), False),
        _expect("source_plan_materialization_forbidden", decision.get("artifact_manifest_materialization_authorized"), False),
        _expect("source_plan_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_plan_training_not_executed", decision.get("training_executed"), False),
        _expect("source_plan_contract_status", plan.get("status"), "plan_ready_no_materializer_implemented"),
        _expect("future_materializer_script", plan.get("future_materializer_script"), FUTURE_MATERIALIZER),
        _expect("future_materializer_test", plan.get("future_materializer_test"), FUTURE_UNIT_TEST),
        _expect("source_plan_materializer_not_implemented", plan.get("materializer_implemented_by_this_gate"), False),
        _expect("source_plan_runtime_manifest_not_written", plan.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_runtime_not_enabled", plan.get("runtime_execution_enabled_by_this_gate"), False),
        _check("source_plan_runtime_manifest_path_json", str(plan.get("planned_runtime_manifest_path", "")).endswith(".json"), plan.get("planned_runtime_manifest_path"), "*.json"),
        _contains_in_list(
            "future_cli_requires_plan_json",
            plan.get("future_cli_contract"),
            "--artifact_manifest_materialization_plan_json",
        ),
        _contains_in_list(
            "future_cli_requires_expected_plan_sha",
            plan.get("future_cli_contract"),
            "--expected_materialization_plan_sha256",
        ),
        _contains_in_list(
            "future_cli_requires_output_runtime_manifest",
            plan.get("future_cli_contract"),
            "--output_runtime_manifest_json",
        ),
        _contains_in_list(
            "future_cli_requires_enable_flag",
            plan.get("future_cli_contract"),
            "--enable_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer",
        ),
        _contains_in_list(
            "implementation_step_default_off_before_reading",
            plan.get("required_implementation_steps"),
            "remain default-off and do not read source plan or artifact files unless enable flag is present",
        ),
        _contains_in_list(
            "implementation_step_verify_plan_sha",
            plan.get("required_implementation_steps"),
            "load exactly one materialization plan JSON and verify its expected SHA256",
        ),
        _contains_in_list(
            "implementation_step_verify_dp_head",
            plan.get("required_implementation_steps"),
            "verify current DP head equals the fixed TiERIV Diffusion Planner commit",
        ),
        _contains_in_list(
            "implementation_step_write_one_manifest",
            plan.get("required_implementation_steps"),
            "write exactly one JSON runtime manifest with schema dp_camp_v13_default_off_shadow_selector_runtime_v1",
        ),
        _contains_in_list(
            "implementation_step_no_replay_logs",
            plan.get("required_implementation_steps"),
            "write no replay logs, no candidate artifacts, no weights, and no DP files",
        ),
        _contains_in_list(
            "implementation_step_fail_closed",
            plan.get("required_implementation_steps"),
            "fail closed without output on any missing file, hash mismatch, K drift, schema drift, or DP head drift",
        ),
        _contains_in_list(
            "future_test_default_off",
            plan.get("future_unit_tests"),
            "test_materializer_is_default_off_and_does_not_read_missing_inputs",
        ),
        _contains_in_list(
            "future_test_writes_shape",
            plan.get("future_unit_tests"),
            "test_materializer_writes_exact_runtime_manifest_shape_when_enabled",
        ),
        _contains_in_list(
            "future_test_hash_mismatch",
            plan.get("future_unit_tests"),
            "test_materializer_rejects_hash_mismatch_without_output",
        ),
        _contains_in_list(
            "future_test_dp_drift",
            plan.get("future_unit_tests"),
            "test_materializer_rejects_dp_head_drift_without_output",
        ),
        _contains_in_list(
            "future_test_authorization_leak",
            plan.get("future_unit_tests"),
            "test_materializer_rejects_runtime_or_promotion_authorization_leaks",
        ),
        _contains_in_list(
            "future_test_no_replay_or_dp_touch",
            plan.get("future_unit_tests"),
            "test_materializer_does_not_run_replay_or_touch_dp_sources",
        ),
        _expect("future_manifest_atom_entry_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("future_manifest_atom_entry_path_present", bool(atom_entry.get("path")), atom_entry.get("path"), "nonempty path"),
        _check("future_manifest_atom_entry_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("future_manifest_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("future_manifest_static_weights_path_present", bool(weights_entry.get("path")), weights_entry.get("path"), "nonempty path"),
        _check("future_manifest_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _expect("source_summary_runtime_schema", source_summary.get("runtime_manifest_schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("source_summary_runtime_entries", source_summary.get("runtime_entries"), ["atom_scales", "static_weights"]),
        *[
            _expect(f"source_plan_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
        ],
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    script = texts.get("artifact_manifest_materialization_implementation_plan_script", "")
    tests = texts.get("artifact_manifest_materialization_implementation_plan_test", "")
    runner = texts.get("replay_runner", "")
    audit = texts.get("v13_audit", "")
    return [
        _contains("plan_script_schema_constant", script, "SCHEMA_VERSION ="),
        _contains("plan_script_future_materializer_path", script, FUTURE_MATERIALIZER),
        _contains("plan_script_future_unit_test_path", script, FUTURE_UNIT_TEST),
        _contains("plan_script_authorizes_static_review_only", script, SOURCE_AUTHORIZED_NEXT_WORK),
        _contains("plan_script_materializer_not_implemented", script, '"materializer_implemented_by_this_gate": False'),
        _contains("plan_script_runtime_manifest_not_written", script, '"runtime_manifest_written_by_this_gate": False'),
        _contains("plan_script_required_hash_step", script, "verify atom_scales and static_weights files exist and match planned SHA256 before writing"),
        _contains("plan_test_ready_no_implementation", tests, "test_materialization_implementation_plan_ready_but_does_not_implement"),
        _contains("plan_test_default_off", tests, "test_materialization_implementation_plan_is_default_off"),
        _contains("plan_test_rejects_source_review_drift", tests, "test_materialization_implementation_plan_rejects_source_review_gate_drift"),
        _contains("plan_test_rejects_runtime_schema_drift", tests, "test_materialization_implementation_plan_rejects_runtime_schema_drift"),
        _contains("plan_test_rejects_dp_head_drift", tests, "test_materialization_implementation_plan_rejects_dp_head_drift"),
        _contains("runner_manifest_loader_present", runner, "def _load_shadow_artifact_manifest"),
        _contains("runner_manifest_expected_sha_lookup_present", runner, "def _manifest_expected_sha256"),
        _contains("runner_artifacts_lookup_present", runner, 'artifacts = manifest.get("artifacts")'),
        _contains("runner_sha256_lookup_present", runner, 'hashes = manifest.get("sha256")'),
        _contains("runner_atom_scales_logical_name", runner, 'logical_name="atom_scales"'),
        _contains("runner_static_weights_logical_name", runner, 'logical_name="static_weights"'),
        _contains(
            "audit_current_scope_authorizes_implementation_static_review_only",
            audit,
            "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_static_contract_review_only",
        ),
        _contains("audit_implementation_static_review_authorized", audit, "artifact_manifest_materialization_implementation_static_contract_review_authorized=True"),
        _contains("audit_implementation_still_blocked", audit, "artifact_manifest_materialization_implementation_authorized=False"),
        _contains("audit_materialization_still_blocked", audit, "artifact_manifest_materialization_authorized=False"),
        _contains("audit_runtime_still_blocked", audit, "runtime_shadow_selector_execution_authorized=False"),
        _contains("audit_training_authorization_preserved", audit, "current_v13_all_subsequent_training_tasks_authorized_by_user=True"),
    ]


def _contract_summary(payload: dict[str, Any], hashes: dict[str, str]) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    summary = _dict(payload.get("source_summary"))
    return {
        "source_hashes": hashes,
        "source_plan_status": decision.get("status"),
        "source_plan_passed": decision.get("passed"),
        "source_plan_authorized_next_work": decision.get("authorized_next_work"),
        "planned_runtime_manifest_path": plan.get("planned_runtime_manifest_path"),
        "future_materializer_script": plan.get("future_materializer_script"),
        "future_materializer_test": plan.get("future_materializer_test"),
        "runtime_manifest_schema_version": summary.get("runtime_manifest_schema_version"),
        "runtime_entries": summary.get("runtime_entries"),
    }


def _future_implementation_contract(payload: dict[str, Any]) -> dict[str, Any]:
    plan = _dict(payload.get("implementation_plan"))
    return {
        "future_materializer_script": plan.get("future_materializer_script"),
        "future_materializer_test": plan.get("future_materializer_test"),
        "planned_runtime_manifest_path": plan.get("planned_runtime_manifest_path"),
        "required_implementation_steps": plan.get("required_implementation_steps", []),
        "future_unit_tests": plan.get("future_unit_tests", []),
    }


def _review_scope() -> list[str]:
    return [
        "source materialization implementation plan JSON",
        "source materialization implementation plan script",
        "source materialization implementation plan tests",
        "default-off replay runner manifest lookup contract",
        "current v13 audit boundary",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "implementing the materializer during this static review",
        "writing the runtime manifest during this static review",
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
        "artifact_manifest_materialization_implementation_static_contract_review_complete": bool(passed),
        "artifact_manifest_materialization_implementation_authorized": bool(passed),
        "artifact_manifest_materialization_authorized": False,
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
        "production_selector_change_authorized": False,
        "training_authorization_changed_by_review": False,
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


def _contains_in_list(name: str, values: Any, expected: str) -> dict[str, Any]:
    return _check(
        name,
        isinstance(values, list) and expected in values,
        values,
        f"list containing {expected}",
    )


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
