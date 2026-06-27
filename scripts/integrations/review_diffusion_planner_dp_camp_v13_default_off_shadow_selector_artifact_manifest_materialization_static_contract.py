#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_rejected"
)
SOURCE_PLAN_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_implementation_plan_only"
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
            "artifact-manifest materialization plan. It reads plan/source/test/"
            "audit text only and verifies the planned runtime manifest path is "
            "not already materialized."
        )
    )
    parser.add_argument("--artifact_manifest_materialization_plan_json", type=Path, required=True)
    parser.add_argument("--artifact_manifest_materialization_plan_script_py", type=Path, required=True)
    parser.add_argument("--artifact_manifest_materialization_plan_test_py", type=Path, required=True)
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
        "--enable_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        artifact_manifest_materialization_plan_json=args.artifact_manifest_materialization_plan_json,
        artifact_manifest_materialization_plan_script_py=args.artifact_manifest_materialization_plan_script_py,
        artifact_manifest_materialization_plan_test_py=args.artifact_manifest_materialization_plan_test_py,
        replay_runner_py=args.replay_runner_py,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review
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
    artifact_manifest_materialization_plan_json: Path,
    artifact_manifest_materialization_plan_script_py: Path,
    artifact_manifest_materialization_plan_test_py: Path,
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
        "artifact_manifest_materialization_plan": artifact_manifest_materialization_plan_json,
        "artifact_manifest_materialization_plan_script": artifact_manifest_materialization_plan_script_py,
        "artifact_manifest_materialization_plan_test": artifact_manifest_materialization_plan_test_py,
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

    materialization_plan = _dict(payloads.get("artifact_manifest_materialization_plan"))
    checks.extend(_source_plan_checks(materialization_plan))
    checks.extend(_planned_runtime_manifest_checks(materialization_plan))
    checks.extend(_source_surface_checks(texts))
    passed = all(check["passed"] for check in checks)

    report["contract_summary"] = _contract_summary(
        materialization_plan,
        texts,
        report["source_hashes"],
    )
    report["review_scope"] = _review_scope()
    report["forbidden_paths"] = _forbidden_paths()
    report["review_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("contract_summary", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Artifact Manifest Materialization Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Implementation plan authorized: `{decision['artifact_manifest_materialization_implementation_plan_authorized']}`",
        f"- Manifest materialization authorized: `{decision['artifact_manifest_materialization_authorized']}`",
        f"- Shadow runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Source Plan",
        "",
        f"- Source status: `{summary.get('source_plan_status')}`",
        f"- Planned runtime manifest path: `{summary.get('planned_runtime_manifest_path')}`",
        f"- Runtime manifest exists now: `{summary.get('planned_runtime_manifest_exists')}`",
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
            "This review is static only. It does not write the runtime manifest, "
            "execute replay, enable the shadow selector, train CAMP, generate "
            "candidates, modify DP, promote atoms or selectors, deploy, or "
            "authorize safety/CAMP-over-DP claims.",
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
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review"
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
                "The materialization implementation plan may be authorized only "
                "if the materialization plan remains plan-only, the planned "
                "runtime manifest is absent, and all future manifest content "
                "preserves fixed-DP-candidate affine reranking with DP Top-1 "
                "execution during the default-off shadow phase."
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
            "artifact_manifest_materialization_static_contract_review_complete": False,
            "artifact_manifest_materialization_implementation_plan_authorized": False,
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
    plan = _dict(payload.get("materialization_plan"))
    future = _dict(plan.get("future_manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    aliases = _dict(future.get("sha256"))
    atom_entry = _dict(artifacts.get("atom_scales"))
    weights_entry = _dict(artifacts.get("static_weights"))
    forbidden = _dict(future.get("forbidden_runtime_claims"))
    return [
        _expect("source_plan_schema_version", payload.get("schema_version"), "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_v1"),
        _expect("source_plan_status_ready", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_authorizes_this_review", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_plan_ready_flag", decision.get("artifact_manifest_materialization_plan_ready"), True),
        _expect("source_plan_static_review_authorized", decision.get("artifact_manifest_materialization_static_contract_review_authorized"), True),
        _expect("source_plan_materialization_forbidden", decision.get("artifact_manifest_materialization_authorized"), False),
        _expect("source_plan_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_plan_training_not_executed", decision.get("training_executed"), False),
        _expect("source_plan_status_no_manifest_written", plan.get("status"), "plan_ready_no_runtime_manifest_written"),
        _expect("source_plan_is_not_runtime_manifest", plan.get("this_plan_is_runtime_manifest"), False),
        _expect("source_plan_runtime_manifest_not_written", plan.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_runtime_not_enabled", plan.get("runtime_execution_enabled_by_this_gate"), False),
        _check("source_plan_runtime_manifest_path_json", str(plan.get("planned_runtime_manifest_path", "")).endswith(".json"), plan.get("planned_runtime_manifest_path"), "*.json"),
        _expect("future_manifest_schema", future.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("future_manifest_default_off", future.get("default_off"), True),
        _expect("future_manifest_selection_effect_false", future.get("selection_effect"), False),
        _expect("future_manifest_selector_mode_static", future.get("selector_mode"), "static"),
        _expect("future_manifest_candidate_operation", future.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("future_manifest_executed_policy", future.get("executed_output_policy"), "dp_top1"),
        _expect("future_manifest_candidate_count", future.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("future_manifest_atom_count", future.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("future_manifest_atom_schema", future.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("future_manifest_score_expression", future.get("score_expression"), SCORE_EXPRESSION),
        _expect("future_manifest_required_dp_head", future.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("future_manifest_atom_entry_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("future_manifest_atom_entry_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("future_manifest_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("future_manifest_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _expect("future_manifest_alias_atom_scales", aliases.get("atom_scales"), atom_entry.get("sha256")),
        _expect("future_manifest_alias_static_weights", aliases.get("static_weights"), weights_entry.get("sha256")),
        *[
            _expect(f"future_manifest_forbidden_{name}", forbidden.get(name), False)
            for name in (
                "selector_promotion_authorized",
                "atom_promotion_authorized",
                "deployment_authorized",
                "safety_benefit_claim_authorized",
                "camp_over_dp_top1_claim_authorized",
            )
        ],
        *[
            _expect(f"source_plan_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
        ],
    ]


def _planned_runtime_manifest_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    plan = _dict(payload.get("materialization_plan"))
    path_value = plan.get("planned_runtime_manifest_path")
    if not isinstance(path_value, str) or not path_value:
        return [
            _check("planned_runtime_manifest_path_absent_now", False, path_value, "nonexistent path")
        ]
    path = Path(path_value)
    return [
        _check(
            "planned_runtime_manifest_path_absent_now",
            not path.exists(),
            str(path),
            "path does not exist",
        )
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    script = texts.get("artifact_manifest_materialization_plan_script", "")
    tests = texts.get("artifact_manifest_materialization_plan_test", "")
    runner = texts.get("replay_runner", "")
    audit = texts.get("v13_audit", "")
    return [
        _contains("plan_script_schema_constant", script, "SCHEMA_VERSION ="),
        _contains("plan_script_future_manifest_content", script, '"future_manifest_required_content"'),
        _contains("plan_script_plan_not_runtime_manifest", script, '"this_plan_is_runtime_manifest": False'),
        _contains("plan_script_runtime_manifest_not_written", script, '"runtime_manifest_written_by_this_gate": False'),
        _contains("plan_script_static_weights_alias", script, '"static_weights": weights_sha'),
        _contains("plan_test_ready_no_write", tests, "test_materialization_plan_ready_but_does_not_write_runtime_manifest"),
        _contains("plan_test_default_off", tests, "test_materialization_plan_is_default_off"),
        _contains("plan_test_rejects_authorization_leak", tests, "test_materialization_plan_rejects_source_review_authorization_leak"),
        _contains("plan_test_rejects_logical_name_drift", tests, "test_materialization_plan_rejects_source_plan_logical_name_drift"),
        _contains("plan_test_rejects_audit_drift", tests, "test_materialization_plan_rejects_audit_target_drift"),
        _contains("runner_manifest_loader_present", runner, "def _load_shadow_artifact_manifest"),
        _contains("runner_manifest_expected_sha_lookup_present", runner, "def _manifest_expected_sha256"),
        _contains("runner_artifacts_lookup_present", runner, 'artifacts = manifest.get("artifacts")'),
        _contains("runner_sha256_lookup_present", runner, 'hashes = manifest.get("sha256")'),
        _contains("runner_atom_scales_logical_name", runner, 'logical_name="atom_scales"'),
        _contains("runner_static_weights_logical_name", runner, 'logical_name="static_weights"'),
        _contains(
            "audit_current_scope_authorizes_static_review_only",
            audit,
            "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only",
        ),
        _contains("audit_materialization_still_blocked", audit, "artifact_manifest_materialization_authorized=False"),
        _contains("audit_runtime_still_blocked", audit, "runtime_shadow_selector_execution_authorized=False"),
        _contains("audit_training_authorization_preserved", audit, "current_v13_all_subsequent_training_tasks_authorized_by_user=True"),
    ]


def _contract_summary(
    payload: dict[str, Any],
    texts: dict[str, str],
    hashes: dict[str, str],
) -> dict[str, Any]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("materialization_plan"))
    future = _dict(plan.get("future_manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    planned_path = plan.get("planned_runtime_manifest_path")
    return {
        "source_hashes": hashes,
        "source_plan_status": decision.get("status"),
        "source_plan_passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "planned_runtime_manifest_path": planned_path,
        "planned_runtime_manifest_exists": Path(str(planned_path)).exists()
        if isinstance(planned_path, str)
        else None,
        "runtime_manifest_schema_version": future.get("schema_version"),
        "runtime_entries": sorted(artifacts),
        "runner_has_manifest_lookup": (
            "def _manifest_expected_sha256" in texts.get("replay_runner", "")
            and 'artifacts = manifest.get("artifacts")' in texts.get("replay_runner", "")
        ),
    }


def _review_scope() -> list[str]:
    return [
        "source materialization plan JSON",
        "materialization plan implementation script",
        "materialization plan focused tests",
        "planned runtime manifest path absence check",
        "default-off replay runner manifest lookup contract",
        "current v13 audit boundary",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "writing the runtime manifest during this static review",
        "running replay with the planned runtime manifest path",
        "enabling the default-off shadow selector runtime",
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
        "artifact_manifest_materialization_static_contract_review_complete": bool(passed),
        "artifact_manifest_materialization_implementation_plan_authorized": bool(passed),
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
