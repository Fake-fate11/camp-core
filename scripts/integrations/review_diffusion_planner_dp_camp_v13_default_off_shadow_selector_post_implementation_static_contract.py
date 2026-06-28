#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"

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
            "Post-implementation static contract review for the v13 "
            "default-off DP-CAMP shadow selector. This reads source, focused "
            "tests, and audit text only. It does not run replay, generate "
            "candidates, train CAMP, modify DP, promote, deploy, or authorize "
            "safety/CAMP-over-DP claims."
        )
    )
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--shadow_unit_test_py", type=Path, required=True)
    parser.add_argument("--benders_contract_test_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_default_off_shadow_selector_post_implementation_static_contract_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        replay_runner_py=args.replay_runner_py,
        shadow_unit_test_py=args.shadow_unit_test_py,
        benders_contract_test_py=args.benders_contract_test_py,
        v13_audit_md=args.v13_audit_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v13_default_off_shadow_selector_post_implementation_static_contract_review
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
    replay_runner_py: Path,
    shadow_unit_test_py: Path,
    benders_contract_test_py: Path,
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
        "replay_runner": replay_runner_py,
        "shadow_unit_test": shadow_unit_test_py,
        "benders_contract_test": benders_contract_test_py,
        "v13_audit": v13_audit_md,
    }
    texts: dict[str, str] = {}
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
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "existing file"))
        if path.is_file():
            report["source_hashes"][f"{name}_sha256"] = _sha256(path)
            texts[name] = path.read_text(encoding="utf-8")
        else:
            texts[name] = ""

    checks.extend(_runner_contract_checks(texts["replay_runner"]))
    checks.extend(_unit_test_contract_checks(texts["shadow_unit_test"]))
    checks.extend(_benders_contract_checks(texts["benders_contract_test"]))
    checks.extend(_audit_contract_checks(texts["v13_audit"]))
    passed = all(check["passed"] for check in checks)

    report["contract_summary"] = _contract_summary(texts, report["source_hashes"])
    report["review_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("contract_summary", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Post-Implementation Static Contract Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Artifact manifest materialization authorized: `{decision['artifact_manifest_materialization_authorized']}`",
        f"- Shadow runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Contract",
        "",
        f"- Runtime flag: `{summary.get('runtime_flag_present')}`",
        f"- Default-off/fail-closed: `{summary.get('default_off_fail_closed_present')}`",
        f"- DP Top-1 execution override: `{summary.get('dp_top1_override_present')}`",
        f"- Shadow index logging: `{summary.get('shadow_index_logging_present')}`",
        f"- Artifact hash contract: `{summary.get('artifact_hash_contract_present')}`",
        f"- Score expression: `{SCORE_EXPRESSION}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This review is static only. It does not run replay, generate candidates, "
        "train CAMP, modify Diffusion Planner, change online selection, promote "
        "atoms or selectors, deploy, or authorize safety/CAMP-over-DP claims.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
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
                "dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review"
            ),
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "static_review_only": True,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "CAMP remains a fixed-DP-candidate reranker. The implemented "
                "shadow selector may compute and log shadow_selected_index, "
                "but the executed trajectory remains DP candidate 0. Scores "
                "remain affine in simplex weights: score_k(w)=a_k^T w."
            ),
        },
        "source_hashes": {},
        "contract_summary": {},
        "review_checks": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "post_implementation_static_contract_review_complete": False,
            "artifact_manifest_plan_authorized": False,
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
            "training_authorization_changed": False,
            "training_executed": False,
            "failed_checks": [],
        },
    }


def _runner_contract_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains("runner_shadow_flag_present", text, "--camp_default_off_shadow_selector"),
        _contains("runner_shadow_flag_default_off", text, "action=\"store_true\""),
        _contains("runner_schema_constant_present", text, "DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION"),
        _contains("runner_expected_k8_constant", text, "DEFAULT_OFF_SHADOW_SELECTOR_EXPECTED_K = 8"),
        _contains("runner_contract_builder_present", text, "def _default_off_shadow_selector_contract"),
        _contains("runner_hash_normalizer_present", text, "def _normalize_sha256"),
        _contains("runner_manifest_loader_present", text, "def _load_shadow_artifact_manifest"),
        _contains("runner_artifact_entry_present", text, "def _shadow_artifact_entry"),
        _contains("runner_records_expected_hash", text, "\"expected_sha256\""),
        _contains("runner_records_actual_hash", text, "\"actual_sha256\""),
        _contains("runner_records_hash_match", text, "\"hash_match\""),
        _contains("runner_candidate_count_drift_fails_closed", text, "candidate_count_drift"),
        _contains("runner_selector_artifact_load_fails_closed", text, "selector_artifact_load_failed"),
        _contains("runner_fail_closed_marker_present", text, "def _mark_shadow_selector_fail_closed"),
        _contains(
            "runner_missing_contract_disables_selector",
            text,
            "if args.camp_default_off_shadow_selector and not bool(",
        ),
        _contains("runner_shadow_summary_present", text, "def _summarize_default_off_shadow_selector_records"),
        _contains(
            "runner_shadow_index_from_baseline",
            text,
            "shadow_selected_index = (\n            baseline_selected_index if default_off_shadow_selector else None",
        ),
        _contains(
            "runner_dp_top1_execution_override",
            text,
            "selected_index = 0 if default_off_shadow_selector else baseline_selected_index",
        ),
        _contains("runner_selected_trajectory_uses_selected_index", text, "selected_trajectory = candidates[selected_index]"),
        _contains("runner_record_executed_index", text, "\"executed_index\": selected_index"),
        _contains("runner_record_shadow_selected_index", text, "\"shadow_selected_index\": shadow_selected_index"),
        _contains("runner_shadow_record_dp_top1_policy", text, "\"executed_output_policy\": \"dp_top1\""),
        _contains("runner_shadow_record_selection_effect_false", text, "\"selection_effect\": False"),
        _contains("runner_shadow_record_score_expression", text, "\"score_expression\": \"score_k(w)=a_k^T w\""),
        _contains("runner_incompatible_flags_rejected", text, "shadow execution must remain DP Top-1"),
        _contains("runner_rejects_perfect_tracker_postselection", text, "--camp_perfect_tracker_command_postselection"),
        _contains("runner_rejects_traffic_light_postselection", text, "--camp_traffic_light_hybrid_postselection"),
        _contains("runner_rejects_underprogress_relaxation", text, "--camp_underprogress_relaxation"),
        _contains("runner_rejects_splice_shadow_rule", text, "--camp_splice_shadow_rule"),
        _contains("runner_summary_wires_shadow_summary", text, "\"camp_default_off_shadow_selector\": camp_default_off_shadow_selector"),
        _contains("runner_validation_wires_shadow_summary", text, "validation[\"camp_default_off_shadow_selector\"]"),
    ]


def _unit_test_contract_checks(text: str) -> list[dict[str, Any]]:
    needles = {
        "unit_default_off_before_artifact_reads": "test_default_off_disabled_contract_returns_dp_top1_before_artifact_reads",
        "unit_hash_mismatch_fails_closed": "test_immutable_artifact_hash_contract_fails_closed_on_mismatch",
        "unit_fixed_candidate_affine_score": "test_fixed_candidate_affine_score_contract_uses_k8_matrix_product",
        "unit_dp_top1_runtime_contract": "test_dp_top1_shadow_runtime_contract_never_routes_shadow_argmin",
        "unit_no_candidate_mutation": "test_no_candidate_mutation_contract_keeps_tensor_hash_and_shape",
        "unit_benders_affine_boundary": "test_benders_boundary_keeps_scores_affine_in_simplex_weights",
        "unit_formal_seeds_rejected": "test_formal_seed_boundary_rejects_frozen_seeds_without_selection",
        "unit_runner_missing_artifacts_fail_closed": "test_runner_shadow_contract_missing_artifacts_fail_closed",
        "unit_runner_hash_manifest_accepts_clean": "test_runner_shadow_contract_accepts_clean_hash_manifest",
        "unit_runner_execution_flags_rejected": "test_runner_shadow_selector_rejects_execution_changing_flags",
        "unit_runner_summary_records_dp_top1": "test_runner_shadow_summary_records_dp_top1_execution",
        "unit_source_surface_boundary": "test_current_static_source_surfaces_preserve_rerank_boundary",
    }
    return [_contains(name, text, needle) for name, needle in needles.items()]


def _benders_contract_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains(
            "benders_test_pins_affine_scores",
            text,
            "test_fixed_candidate_atom_scores_are_affine_in_simplex_weights",
        ),
        _contains(
            "benders_test_rejects_negative_atom_coefficients",
            text,
            "test_robust_margin_master_rejects_negative_atom_coefficients",
        ),
    ]


def _audit_contract_checks(text: str) -> list[dict[str, Any]]:
    current_boundary = _current_v13_boundary(text)
    return [
        _contains(
            "audit_records_implementation_complete",
            current_boundary,
            "current_v13_status=default_off_shadow_selector_implementation_complete",
        ),
        _contains(
            "audit_authorizes_post_implementation_review",
            current_boundary,
            "v13_default_off_shadow_selector_post_implementation_static_contract_review_authorized=True",
        ),
        _contains_any(
            "audit_current_or_completed_post_review",
            current_boundary,
            (
                "next_work_target=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_only",
                "v13_default_off_shadow_selector_post_implementation_static_contract_review_status=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_complete",
            ),
        ),
        _contains(
            "audit_pins_runtime_default_off",
            current_boundary,
            "v13_default_off_shadow_selector_runtime_default_off=True",
        ),
        _contains(
            "audit_pins_runtime_effect",
            current_boundary,
            "selected_index and executed_index remain DP candidate 0",
        ),
        _contains(
            "audit_pins_incompatible_flags",
            current_boundary,
            "v13_default_off_shadow_selector_runtime_incompatible_flags_rejected=",
        ),
        _contains(
            "audit_pins_score_expression",
            current_boundary,
            "v13_default_off_shadow_selector_score_expression=score_k(w)=a_k^T w",
        ),
        _contains(
            "audit_blocks_online_selector_change",
            current_boundary,
            "online_selector_change_authorized=False",
        ),
        _contains(
            "audit_blocks_executed_trajectory_change",
            current_boundary,
            "executed_trajectory_change_authorized=False",
        ),
        _contains(
            "audit_blocks_candidate_generation",
            current_boundary,
            "candidate_generation_authorized_by_current_boundary=False",
        ),
        _contains(
            "audit_training_authorization_update_preserved",
            current_boundary,
            "current_v13_training_authorized_by_user=True",
        ),
    ]


def _current_v13_boundary(audit: str) -> str:
    marker = "\n## Current V13 "
    index = audit.rfind(marker)
    return audit[index + 1 :] if index >= 0 else audit


def _contract_summary(texts: dict[str, str], hashes: dict[str, str]) -> dict[str, Any]:
    runner = texts.get("replay_runner", "")
    tests = texts.get("shadow_unit_test", "")
    return {
        "source_hashes": hashes,
        "runtime_flag_present": "--camp_default_off_shadow_selector" in runner,
        "default_off_fail_closed_present": (
            "action=\"store_true\"" in runner
            and "selector_artifact_load_failed" in runner
            and "def _mark_shadow_selector_fail_closed" in runner
        ),
        "dp_top1_override_present": (
            "selected_index = 0 if default_off_shadow_selector else baseline_selected_index"
            in runner
        ),
        "shadow_index_logging_present": (
            "\"shadow_selected_index\": shadow_selected_index" in runner
            and "_summarize_default_off_shadow_selector_records" in runner
        ),
        "artifact_hash_contract_present": (
            "\"expected_sha256\"" in runner
            and "\"actual_sha256\"" in runner
            and "\"hash_match\"" in runner
        ),
        "focused_tests_present": (
            "test_dp_top1_shadow_runtime_contract_never_routes_shadow_argmin" in tests
            and "test_runner_shadow_selector_rejects_execution_changing_flags" in tests
        ),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_implementation_static_contract_review_complete": bool(passed),
        "artifact_manifest_plan_authorized": bool(passed),
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
        "training_authorization_changed": False,
        "training_executed": False,
        "failed_checks": failed,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _contains_any(name: str, text: str, needles: tuple[str, ...]) -> dict[str, Any]:
    matched = [needle for needle in needles if needle in text]
    return _check(name, bool(matched), matched or "missing", list(needles))


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


if __name__ == "__main__":
    raise SystemExit(main())
