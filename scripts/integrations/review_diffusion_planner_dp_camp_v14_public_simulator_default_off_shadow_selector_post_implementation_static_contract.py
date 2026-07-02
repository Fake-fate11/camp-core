#!/usr/bin/env python3
"""Post-implementation static review for the v14 default-off shadow selector."""

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
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "post_implementation_static_contract_review_v1"
)
SOURCE_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_implementation_passed"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "post_implementation_static_contract_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "post_implementation_static_contract_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "post_implementation_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_plan_only"
)

BLOCKED_ACTIONS = (
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
    parser.add_argument("--implementation_result_json", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--shadow_unit_test_py", type=Path, required=True)
    parser.add_argument("--benders_contract_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_default_off_shadow_selector_post_implementation_static_contract_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        implementation_result_json=args.implementation_result_json,
        replay_runner_py=args.replay_runner_py,
        shadow_unit_test_py=args.shadow_unit_test_py,
        benders_contract_test_py=args.benders_contract_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_default_off_shadow_selector_post_implementation_static_contract_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    implementation_result_json: Path,
    replay_runner_py: Path,
    shadow_unit_test_py: Path,
    benders_contract_test_py: Path,
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
    paths = {
        "implementation_result": implementation_result_json,
        "replay_runner": replay_runner_py,
        "shadow_unit_test": shadow_unit_test_py,
        "benders_contract_test": benders_contract_test_py,
        "v14_audit": v14_audit_md,
        "current_status": current_status_md,
    }
    texts = {
        name: _read_text(path)
        for name, path in paths.items()
        if name != "implementation_result"
    }
    implementation_result = _read_json_dict(implementation_result_json)
    checks = [
        _expect("review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
    ]
    source_hashes = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file"))
        if path.is_file():
            source_hashes[f"{name}_sha256"] = _sha256(path)
    checks.extend(_implementation_result_checks(implementation_result))
    checks.extend(_runner_contract_checks(texts.get("replay_runner", "")))
    checks.extend(_unit_test_contract_checks(texts.get("shadow_unit_test", "")))
    checks.extend(_benders_contract_checks(texts.get("benders_contract_test", "")))
    checks.extend(
        _audit_contract_checks(
            texts.get("v14_audit", ""),
            texts.get("current_status", ""),
        )
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "review_only": True,
            "static_only": True,
            "default_off": True,
            "implementation_result_json": str(implementation_result_json.resolve()),
            "replay_runner_py": str(replay_runner_py.resolve()),
            "shadow_unit_test_py": str(shadow_unit_test_py.resolve()),
            "benders_contract_test_py": str(benders_contract_test_py.resolve()),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "math_boundary": (
                "CAMP remains a fixed-DP-candidate reranker. The default-off "
                "shadow selector may log shadow_selected_index only; executed "
                "trajectory output remains DP Top-1. Scores remain affine: "
                "score_k(w)=a_k^T w over approved nonnegative simplex atoms."
            ),
        },
        "source_hashes": source_hashes,
        "implementation_summary": _implementation_summary(implementation_result),
        "static_contract_review": _static_contract_review(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir
        / "default_off_shadow_selector_post_implementation_static_contract_review.json",
        report,
    )
    (
        output_dir
        / "default_off_shadow_selector_post_implementation_static_contract_review.md"
    ).write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["static_contract_review"]
    lines = [
        "# V14 Default-Off Shadow Selector Post-Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Runtime manifest plan authorized: `{decision['runtime_artifact_manifest_plan_authorized']}`",
        f"- Runtime execution authorized: `{decision['replay_execution_authorized']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        "",
        "## Review",
        "",
        f"- Runtime schema: `{review['runtime_schema_version']}`",
        f"- Source scope: `{review['source_scope']}`",
        f"- Executed output policy: `{review['executed_output_policy']}`",
        f"- Score expression: `{review['score_expression']}`",
        "",
        "## Contracts",
        "",
    ]
    for item in review["contracts"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This review is static only. It does not run replay, generate "
            "candidates, train CAMP, modify Diffusion Planner, change online "
            "selection, promote atoms or selectors, deploy, or authorize "
            "safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _implementation_result_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("implementation_result_passed", payload.get("passed"), True),
        _expect("implementation_result_exit_zero", payload.get("exit"), 0),
        _expect("implementation_result_failure_class", payload.get("failure_class"), "None"),
        _expect("implementation_result_dp_head_fixed", payload.get("dp_head"), FIXED_DP_HEAD),
        _expect(
            "implementation_result_authorized_work",
            payload.get("authorized_work"),
            "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
            "shadow_replay_evaluation_default_off_shadow_selector_"
            "implementation_only_after_explicit_user_authorization",
        ),
        *[_expect(f"implementation_result_{name}_false", payload.get(name), False) for name in (
            "training_executed",
            "replay_executed",
            "candidate_generation_executed",
            "dp_modified",
            "promotion_executed",
            "deployment_executed",
            "safety_claim_authorized",
            "camp_over_dp_top1_claim_authorized",
        )],
    ]


def _runner_contract_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains("runner_schema_constant", text, "DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION"),
        _contains("runner_v14_runtime_schema", text, RUNTIME_SCHEMA_VERSION),
        _check(
            "runner_rejects_v13_runtime_schema",
            "dp_camp_v13_default_off_shadow_selector_runtime_v1" not in text,
            "absent"
            if "dp_camp_v13_default_off_shadow_selector_runtime_v1" not in text
            else "present",
            "absent",
        ),
        _contains("runner_source_scope_constant", text, "DEFAULT_OFF_SHADOW_SELECTOR_SOURCE_SCOPE"),
        _contains("runner_source_scope_value", text, SOURCE_SCOPE),
        _contains("runner_expected_k8_constant", text, "DEFAULT_OFF_SHADOW_SELECTOR_EXPECTED_K = 8"),
        _contains("runner_contract_builder", text, "def _default_off_shadow_selector_contract"),
        _contains("runner_summary_builder", text, "def _summarize_default_off_shadow_selector_records"),
        _contains("runner_artifact_hash_entry", text, "def _shadow_artifact_entry"),
        _contains("runner_fail_closed_marker", text, "def _mark_shadow_selector_fail_closed"),
        _contains("runner_candidate_count_drift_fails_closed", text, "candidate_count_drift"),
        _contains("runner_selector_artifact_load_fails_closed", text, "selector_artifact_load_failed"),
        _contains(
            "runner_shadow_index_logged_from_camp_selection",
            text,
            "shadow_selected_index = (\n            baseline_selected_index if default_off_shadow_selector else None",
        ),
        _contains(
            "runner_executed_index_forced_dp_top1",
            text,
            "selected_index = 0 if default_off_shadow_selector else baseline_selected_index",
        ),
        _contains("runner_selected_trajectory_uses_selected_index", text, "selected_trajectory = candidates[selected_index]"),
        _contains("runner_record_executed_policy", text, "\"executed_output_policy\": \"dp_top1\""),
        _contains("runner_record_selection_effect_false", text, "\"selection_effect\": False"),
        _contains("runner_record_online_selector_change_false", text, "\"online_selector_change\": False"),
        _contains("runner_record_score_expression", text, f"\"score_expression\": \"{SCORE_EXPRESSION}\""),
        _contains("runner_rejects_execution_changing_flags", text, "shadow execution must remain DP Top-1"),
        _contains("runner_rejects_reference_blend_or_postselection_path", text, "--camp_perfect_tracker_command_postselection"),
        _contains("runner_rejects_underprogress_relaxation", text, "--camp_underprogress_relaxation"),
        _contains("runner_rejects_splice_shadow_rule", text, "--camp_splice_shadow_rule"),
        _contains("runner_validation_wires_shadow_summary", text, "validation[\"camp_default_off_shadow_selector\"]"),
    ]


def _unit_test_contract_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains("unit_imports_runtime_schema", text, "DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION"),
        _contains("unit_imports_source_scope", text, "DEFAULT_OFF_SHADOW_SELECTOR_SOURCE_SCOPE"),
        _contains("unit_pins_v14_schema", text, RUNTIME_SCHEMA_VERSION),
        _contains("unit_rejects_v13_schema", text, 'assert "v13" not in DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION'),
        _contains("unit_pins_source_scope", text, SOURCE_SCOPE),
        _contains(
            "unit_default_off_before_artifact_reads",
            text,
            "test_default_off_disabled_contract_returns_dp_top1_before_artifact_reads",
        ),
        _contains("unit_hash_mismatch_fails_closed", text, "test_immutable_artifact_hash_contract_fails_closed_on_mismatch"),
        _contains("unit_fixed_candidate_affine_score", text, "test_fixed_candidate_affine_score_contract_uses_real_selector_matrix_product"),
        _contains("unit_k_drift_fails_closed", text, "test_k_drift_and_selector_mode_drift_fail_closed"),
        _contains("unit_dp_top1_shadow_runtime_contract", text, "test_dp_top1_shadow_runtime_contract_logs_shadow_without_routing"),
        _contains("unit_no_candidate_mutation", text, "test_no_candidate_mutation_contract_keeps_tensor_hash_and_returns_copy"),
        _contains("unit_benders_boundary", text, "test_benders_boundary_keeps_scores_affine_in_simplex_weights"),
        _contains("unit_formal_seed_boundary", text, "test_formal_seed_boundary_is_rejection_only_and_never_replay_execution"),
        _contains("unit_execution_changing_flags_rejected", text, "test_runner_shadow_selector_rejects_execution_changing_flags"),
        _contains("unit_current_source_boundary", text, "test_current_static_source_surfaces_preserve_rerank_boundary"),
    ]


def _benders_contract_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains(
            "benders_test_pins_affine_scores",
            text,
            "test_fixed_candidate_atom_scores_are_affine_in_simplex_weights",
        ),
        _contains(
            "benders_test_rejects_negative_atoms",
            text,
            "test_robust_margin_master_rejects_negative_atom_coefficients",
        ),
    ]


def _audit_contract_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    return [
        _check(
            "audit_latest_status",
            f"current_v14_status={SOURCE_STATUS}" in eof,
            _extract_line(eof, "current_v14_status="),
            f"current_v14_status={SOURCE_STATUS}",
        ),
        _check(
            "audit_latest_next_work",
            f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof,
            _extract_line(eof, "next_work_target="),
            f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}",
        ),
        _contains("audit_records_implementation_passed", eof, "default_off_shadow_selector_implementation_passed=True"),
        _contains("audit_authorizes_post_review", eof, "post_implementation_static_contract_review_authorized=True"),
        _contains("audit_blocks_training", eof, "v14_public_simulator_default_off_shadow_selector_implementation_training_authorized=False"),
        _contains("audit_blocks_replay", eof, "v14_public_simulator_default_off_shadow_selector_implementation_replay_execution_authorized=False"),
        _contains("audit_blocks_candidate_generation", eof, "v14_public_simulator_default_off_shadow_selector_implementation_candidate_generation_authorized=False"),
        _contains("audit_blocks_dp_modification", eof, "v14_public_simulator_default_off_shadow_selector_implementation_dp_modification_authorized=False"),
        _contains("audit_blocks_safety_claim", eof, "v14_public_simulator_default_off_shadow_selector_implementation_safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "v14_public_simulator_default_off_shadow_selector_implementation_camp_over_dp_top1_claim_authorized=False"),
        _contains("audit_pins_score_expression", eof, f"v14_public_simulator_default_off_shadow_selector_implementation_score_expression={SCORE_EXPRESSION}"),
        _contains("audit_pins_v14_schema", eof, f"v14_public_simulator_default_off_shadow_selector_implementation_runtime_schema={RUNTIME_SCHEMA_VERSION}"),
        _contains("audit_pins_source_scope", eof, f"v14_public_simulator_default_off_shadow_selector_implementation_source_scope={SOURCE_SCOPE}"),
        _check(
            "current_status_latest_status",
            f"current_v14_status={SOURCE_STATUS}" in status_text,
            "present" if f"current_v14_status={SOURCE_STATUS}" in status_text else "missing",
            "present",
        ),
        _check(
            "current_status_latest_next_work",
            f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text,
            "present" if f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text else "missing",
            "present",
        ),
    ]


def _implementation_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": payload.get("passed"),
        "exit": payload.get("exit"),
        "failure_class": payload.get("failure_class"),
        "camp_head": payload.get("camp_head"),
        "camp_origin_main": payload.get("camp_origin_main"),
        "dp_head": payload.get("dp_head"),
        "authorized_work": payload.get("authorized_work"),
    }


def _static_contract_review() -> dict[str, Any]:
    return {
        "status": "post_implementation_static_contract_review_passed",
        "runtime_schema_version": RUNTIME_SCHEMA_VERSION,
        "source_scope": SOURCE_SCOPE,
        "runtime_effect": "log shadow_selected_index while executed output remains DP Top-1",
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "candidate_count": 8,
        "score_expression": SCORE_EXPRESSION,
        "selection_rule": "shadow_selected_index = argmin_k score_k(w)",
        "contracts": [
            "v14_runtime_schema_contract",
            "public_simulator_fixed_dp_candidate_source_scope_contract",
            "default_off_fail_closed_contract",
            "immutable_artifact_hash_contract",
            "fixed_candidate_tensor_contract",
            "affine_benders_atom_score_contract",
            "dp_top1_runtime_output_contract",
            "no_promotion_no_claims_contract",
        ],
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "default_off_shadow_selector_post_implementation_static_contract_review_passed": passed,
        "runtime_artifact_manifest_plan_authorized": passed,
        "runtime_artifact_manifest_materialization_authorized": False,
        "default_off_shadow_selector_runtime_execution_authorized": False,
        "score_expression": SCORE_EXPRESSION,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "review_enabled" in failed_set:
        return "explicit_post_implementation_static_review_authorization_missing"
    if {"audit_latest_status", "audit_latest_next_work"} & failed_set:
        return "v14_eof_contract_mismatch"
    if any(name.startswith("implementation_result_") for name in failed):
        return "implementation_artifact_contract_failure"
    if any(name.startswith("runner_") or name.startswith("unit_") or name.startswith("benders_") for name in failed):
        return "source_static_contract_failure"
    return "post_implementation_static_contract_review_failure"


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _latest_text_block(text: str) -> str:
    marker = "\n## Current V14 "
    index = text.rfind(marker)
    return text[index + 1 :] if index >= 0 else text


def _extract_line(text: str, prefix: str) -> str | None:
    for line in reversed(text.splitlines()):
        if line.startswith(prefix):
            return line
    return None


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    lines = []
    for path in sorted(output_dir.iterdir()):
        if path.name == "SHA256SUMS" or not path.is_file():
            continue
        lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compact(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= 160 else text[:157] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
