#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_rejected"
)
SOURCE_PLAN_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14

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
            "artifact-manifest plan. This reads plan/source/test/audit text "
            "only. It does not materialize a runtime manifest, execute replay, "
            "enable the shadow selector, train CAMP, generate candidates, "
            "modify DP, promote, deploy, or authorize safety/CAMP-over-DP "
            "claims."
        )
    )
    parser.add_argument("--artifact_manifest_plan_json", type=Path, required=True)
    parser.add_argument("--artifact_manifest_plan_script_py", type=Path, required=True)
    parser.add_argument("--artifact_manifest_plan_test_py", type=Path, required=True)
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
        "--enable_v13_default_off_shadow_selector_artifact_manifest_static_contract_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        artifact_manifest_plan_json=args.artifact_manifest_plan_json,
        artifact_manifest_plan_script_py=args.artifact_manifest_plan_script_py,
        artifact_manifest_plan_test_py=args.artifact_manifest_plan_test_py,
        replay_runner_py=args.replay_runner_py,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v13_default_off_shadow_selector_artifact_manifest_static_contract_review
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
    artifact_manifest_plan_json: Path,
    artifact_manifest_plan_script_py: Path,
    artifact_manifest_plan_test_py: Path,
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
        "artifact_manifest_plan": artifact_manifest_plan_json,
        "artifact_manifest_plan_script": artifact_manifest_plan_script_py,
        "artifact_manifest_plan_test": artifact_manifest_plan_test_py,
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

    plan = _dict(payloads.get("artifact_manifest_plan"))
    checks.extend(_source_plan_checks(plan))
    checks.extend(_source_surface_checks(texts))
    passed = all(check["passed"] for check in checks)

    report["contract_summary"] = _contract_summary(plan, texts, report["source_hashes"])
    report["review_scope"] = _review_scope()
    report["forbidden_paths"] = _forbidden_paths()
    report["review_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("contract_summary", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Artifact Manifest Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Materialization plan authorized: `{decision['artifact_manifest_materialization_plan_authorized']}`",
        f"- Manifest materialization authorized: `{decision['artifact_manifest_materialization_authorized']}`",
        f"- Shadow runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Plan",
        "",
        f"- Plan status: `{summary.get('source_plan_status')}`",
        f"- Runtime schema: `{summary.get('runtime_manifest_schema_version')}`",
        f"- Materialized by plan gate: `{summary.get('materialized_by_this_gate')}`",
        f"- Required runtime entries: `{summary.get('required_runtime_entries')}`",
        f"- Score expression: `{summary.get('score_expression')}`",
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
            "This review is static only. It does not materialize a runtime "
            "manifest, execute replay, enable the shadow selector, train CAMP, "
            "generate candidates, modify DP, promote atoms or selectors, deploy, "
            "or authorize safety/CAMP-over-DP claims.",
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
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review"
            ),
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "static_review_only": True,
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
                "The artifact plan must preserve fixed-DP-candidate reranking "
                "only: current-tick K=8 candidate atoms, affine scores "
                "score_k(w)=a_k^T w, simplex weights, and no executed trajectory "
                "change during the default-off shadow phase."
            ),
        },
        "source_hashes": {},
        "contract_summary": {},
        "review_scope": [],
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "artifact_manifest_static_contract_review_complete": False,
            "artifact_manifest_materialization_plan_authorized": False,
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
    plan = _dict(payload.get("artifact_manifest_plan"))
    runtime_entries = _dict(plan.get("required_runtime_entries"))
    atom_entry = _dict(runtime_entries.get("atom_scales"))
    weights_entry = _dict(runtime_entries.get("static_weights"))
    evidence_entries = _dict(plan.get("required_evidence_entries"))
    checks = [
        _expect("source_plan_schema_version", payload.get("schema_version"), "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_v1"),
        _expect("source_plan_status_ready", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_authorizes_this_review", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_plan_ready_flag", decision.get("artifact_manifest_plan_ready"), True),
        _expect("source_plan_static_review_authorized", decision.get("artifact_manifest_static_contract_review_authorized"), True),
        _expect("source_plan_materialization_forbidden", decision.get("artifact_manifest_materialization_authorized"), False),
        _expect("source_plan_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_plan_replay_forbidden", decision.get("replay_execution_authorized"), False),
        _expect("source_plan_candidate_generation_forbidden", decision.get("candidate_generation_authorized"), False),
        _expect("source_plan_dp_modification_forbidden", decision.get("dp_modification_authorized"), False),
        _expect("source_plan_selector_promotion_forbidden", decision.get("selector_promotion_authorized"), False),
        _expect("source_plan_atom_promotion_forbidden", decision.get("atom_promotion_authorized"), False),
        _expect("source_plan_deployment_forbidden", decision.get("deployment_authorized"), False),
        _expect("source_plan_safety_claim_forbidden", decision.get("safety_benefit_claim_authorized"), False),
        _expect("source_plan_camp_over_dp_claim_forbidden", decision.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("source_plan_training_not_executed", decision.get("training_executed"), False),
        _expect("source_plan_training_authorization_preserved", decision.get("user_camp_training_authorized"), True),
        _expect("source_plan_status_no_manifest_materialized", plan.get("status"), "plan_ready_no_runtime_manifest_materialized"),
        _expect("source_plan_runtime_schema", plan.get("runtime_manifest_schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("source_plan_materialized_by_this_gate_false", plan.get("materialized_by_this_gate"), False),
        _expect("source_plan_selector_mode_static", plan.get("selector_mode"), "static"),
        _expect("source_plan_candidate_count", plan.get("candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("source_plan_atom_count", plan.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("source_plan_atom_schema", plan.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("source_plan_score_expression", plan.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_plan_atom_scales_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("source_plan_atom_scales_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("source_plan_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("source_plan_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _check("source_plan_has_training_summary_evidence", "training_summary" in evidence_entries, list(evidence_entries), "training_summary"),
        _check("source_plan_has_fallback_master_evidence", "fallback_master_config" in evidence_entries, list(evidence_entries), "fallback_master_config"),
        _contains_in_list(
            "source_plan_runner_uses_future_manifest_placeholder",
            plan.get("planned_runner_args"),
            "--camp_shadow_artifact_manifest <future_runtime_manifest_json>",
        ),
        _contains_in_list("source_plan_runner_static_mode", plan.get("planned_runner_args"), "--camp_selector_mode static"),
        _contains_in_list(
            "source_plan_runner_expected_atom_hash_arg",
            plan.get("planned_runner_args"),
            "--camp_shadow_expected_atom_scales_sha256",
        ),
        _contains_in_list(
            "source_plan_runner_expected_weight_hash_arg",
            plan.get("planned_runner_args"),
            "--camp_shadow_expected_static_weights_sha256",
        ),
    ]
    checks.extend(_expect(f"source_plan_{name}_false", decision.get(name), False) for name in BLOCKED_ACTIONS)
    return checks


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    script = texts.get("artifact_manifest_plan_script", "")
    tests = texts.get("artifact_manifest_plan_test", "")
    runner = texts.get("replay_runner", "")
    audit = texts.get("v13_audit", "")
    return [
        _contains("plan_script_schema_constant", script, "SCHEMA_VERSION ="),
        _contains("plan_script_runtime_schema_constant", script, "RUNTIME_MANIFEST_SCHEMA_VERSION"),
        _contains("plan_script_materialized_false", script, '"materialized_by_this_gate": False'),
        _contains("plan_script_required_runtime_entries", script, '"required_runtime_entries"'),
        _contains("plan_script_logical_atom_scales", script, '"logical_name": "atom_scales"'),
        _contains("plan_script_logical_static_weights", script, '"logical_name": "static_weights"'),
        _contains("plan_script_future_manifest_placeholder", script, "--camp_shadow_artifact_manifest <future_runtime_manifest_json>"),
        _contains("plan_script_blocks_runtime_execution", script, "default_off_shadow_selector_runtime_execution_authorized"),
        _contains("plan_script_records_user_training_authorization", script, "--user_camp_training_authorized"),
        _contains("plan_test_ready_no_materialization", tests, "test_artifact_manifest_plan_ready_without_materializing_runtime_manifest"),
        _contains("plan_test_default_off", tests, "test_artifact_manifest_plan_is_default_off_and_does_not_read_missing_inputs"),
        _contains("plan_test_rejects_simplex_drift", tests, "test_artifact_manifest_plan_rejects_weight_simplex_drift"),
        _contains("plan_test_rejects_hash_mismatch", tests, "test_artifact_manifest_plan_rejects_training_summary_hash_mismatch"),
        _contains("plan_test_rejects_audit_drift", tests, "test_artifact_manifest_plan_rejects_audit_boundary_drift"),
        _contains("runner_manifest_expected_sha_lookup", runner, "def _manifest_expected_sha256"),
        _contains("runner_shadow_artifact_entry", runner, "def _shadow_artifact_entry"),
        _contains("runner_reads_atom_scales_logical_name", runner, 'logical_name="atom_scales"'),
        _contains("runner_reads_static_weights_logical_name", runner, 'logical_name="static_weights"'),
        _contains("runner_fail_closed_manifest_missing", runner, "manifest_missing"),
        _contains("runner_fail_closed_hash_mismatch", runner, "hash_mismatch"),
        _contains(
            "audit_current_scope_authorizes_static_review_only",
            audit,
            "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_only",
        ),
        _contains("audit_materialization_still_blocked", audit, "artifact_manifest_materialization_authorized=False"),
        _contains("audit_runtime_still_blocked", audit, "runtime_shadow_selector_execution_authorized=False"),
        _contains("audit_training_authorization_preserved", audit, "current_v13_all_subsequent_training_tasks_authorized_by_user=True"),
    ]


def _contract_summary(
    plan_payload: dict[str, Any],
    texts: dict[str, str],
    hashes: dict[str, str],
) -> dict[str, Any]:
    decision = _dict(plan_payload.get("final_decision"))
    plan = _dict(plan_payload.get("artifact_manifest_plan"))
    runtime_entries = _dict(plan.get("required_runtime_entries"))
    return {
        "source_hashes": hashes,
        "source_plan_status": decision.get("status"),
        "source_plan_passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "runtime_manifest_schema_version": plan.get("runtime_manifest_schema_version"),
        "materialized_by_this_gate": plan.get("materialized_by_this_gate"),
        "required_runtime_entries": sorted(runtime_entries),
        "selector_mode": plan.get("selector_mode"),
        "candidate_count": plan.get("candidate_count"),
        "atom_count": plan.get("atom_count"),
        "atom_schema_version": plan.get("atom_schema_version"),
        "score_expression": plan.get("score_expression"),
        "runner_has_manifest_contract": (
            "def _shadow_artifact_entry" in texts.get("replay_runner", "")
            and "def _manifest_expected_sha256" in texts.get("replay_runner", "")
        ),
        "plan_tests_pin_default_off": (
            "test_artifact_manifest_plan_is_default_off_and_does_not_read_missing_inputs"
            in texts.get("artifact_manifest_plan_test", "")
        ),
    }


def _review_scope() -> list[str]:
    return [
        "source artifact-manifest plan JSON",
        "artifact-manifest plan implementation script",
        "artifact-manifest plan focused tests",
        "default-off replay runner manifest lookup contract",
        "current v13 audit boundary",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "materializing the runtime manifest during this review",
        "running replay or enabling --camp_default_off_shadow_selector",
        "using the shadow-selected index as executed trajectory output",
        "generating or modifying DP candidate trajectories",
        "training CAMP during this static review",
        "modifying, retraining, or tuning Diffusion Planner",
        "promoting atoms, selector weights, or deployment artifacts",
        "claiming safety benefit or CAMP superiority over DP Top-1",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "artifact_manifest_static_contract_review_complete": bool(passed),
        "artifact_manifest_materialization_plan_authorized": bool(passed),
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


def _contains_in_list(name: str, values: Any, needle: str) -> dict[str, Any]:
    if not isinstance(values, list):
        return _check(name, False, type(values).__name__, f"list containing {needle}")
    matched = [value for value in values if isinstance(value, str) and needle in value]
    return _check(name, bool(matched), matched or "missing", f"contains {needle}")


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
