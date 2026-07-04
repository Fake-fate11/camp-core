#!/usr/bin/env python3
"""Static review for the v14 promotion-readiness uncertainty/coverage review preflight.

This gate reviews a previously materialized read-only preflight artifact. It
verifies fixed-DP provenance, artifact hashes, source contract boundaries, and
EOF authorization. It does not run evaluation, replay, training, candidate
generation, promotion, deployment, online selector activation, DP modification,
or safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_PREFLIGHT_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_review_preflight_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_review_preflight_static_review_v1"
)
SOURCE_PREFLIGHT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_ready"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_only"
)
FAILED_ATTEMPT_STATUS = REJECT_STATUS
AUTHORIZED_RERUN_DECISION_WORK = (
    "user_decision_required_before_public_simulator_post_closeout_promotion_readiness_"
    "uncertainty_coverage_review_preflight_static_review_contract_update_or_rerun"
)
FAILED_ATTEMPT_PREFIX = (
    "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_"
    "preflight_static_review_failed"
)

PREFLIGHT_JSON_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.json"
PREFLIGHT_MD_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight.md"
REVIEW_JSON_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review.json"
REVIEW_MD_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review.md"

BLOCKED_ACTIONS = (
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "training_authorized",
    "training_execution_authorized",
    "candidate_generation_authorized",
    "replay_execution_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
)
EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "replay_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
)
ANALYSIS_FALSE_FLAGS = (
    "training_execution",
    "replay_execution",
    "candidate_generation",
    "dp_modification",
    "online_selector_change",
    "promotion_executed",
    "deployment_executed",
    "safety_or_camp_over_dp_claim",
)
EXPECTED_SOURCE = {
    "preflight_check_count": 190,
    "review_preflight_item_count": 7,
    "artifact_manifest_requirement_count": 7,
    "no_go_count": 7,
    "future_review_requirement_count": 5,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--preflight_md", type=Path, required=True)
    parser.add_argument("--preflight_sha256s", type=Path, required=True)
    parser.add_argument("--preflight_script_py", type=Path, required=True)
    parser.add_argument("--preflight_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review",
        action="store_true",
        help="Explicit opt-in for read-only static review of the preflight artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        preflight_artifact_dir=args.preflight_artifact_dir,
        preflight_json=args.preflight_json,
        preflight_md=args.preflight_md,
        preflight_sha256s=args.preflight_sha256s,
        preflight_script_py=args.preflight_script_py,
        preflight_test_py=args.preflight_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    preflight_artifact_dir: Path,
    preflight_json: Path,
    preflight_md: Path,
    preflight_sha256s: Path,
    preflight_script_py: Path,
    preflight_test_py: Path,
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
    artifact_dir = preflight_artifact_dir.resolve()
    paths = {
        "preflight_json": preflight_json.resolve(),
        "preflight_md": preflight_md.resolve(),
        "preflight_sha256s": preflight_sha256s.resolve(),
        "preflight_script_py": preflight_script_py.resolve(),
        "preflight_test_py": preflight_test_py.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    artifact_files = {
        "command": artifact_dir / "COMMAND",
        "heads": artifact_dir / "HEADS",
        "stdout": artifact_dir / "stdout.txt",
        "stderr": artifact_dir / "stderr.txt",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "preflight_json": artifact_dir / "preflight" / PREFLIGHT_JSON_NAME,
        "preflight_md": artifact_dir / "preflight" / PREFLIGHT_MD_NAME,
        "preflight_sha256s": artifact_dir / "preflight" / "SHA256SUMS",
    }
    source_preflight = _read_json_dict(paths["preflight_json"])
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    preflight_sha256s_values = _read_sha256sums(paths["preflight_sha256s"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    script_text = _read_text(paths["preflight_script_py"])
    test_text = _read_text(paths["preflight_test_py"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("static_review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("preflight_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(_path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("preflight_json_matches_artifact_layout", paths["preflight_json"], artifact_files["preflight_json"]),
            _expect("preflight_md_matches_artifact_layout", paths["preflight_md"], artifact_files["preflight_md"]),
            _expect("preflight_sha256s_matches_artifact_layout", paths["preflight_sha256s"], artifact_files["preflight_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, preflight_sha256s_values))
    checks.extend(_heads_checks(heads, source_preflight))
    checks.extend(_source_preflight_contract_checks(source_preflight))
    checks.extend(_source_surface_checks(script_text, test_text))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "read_only": True,
            "preflight_artifact_dir": str(artifact_dir),
            "preflight_json": str(paths["preflight_json"]),
            "preflight_md": str(paths["preflight_md"]),
            "preflight_sha256s": str(paths["preflight_sha256s"]),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / REVIEW_JSON_NAME, report)
    (output_dir / REVIEW_MD_NAME).write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_preflight_summary"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized current work: `{decision['authorized_current_work']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Source preflight status: `{summary.get('status')}`",
        f"- Source preflight checks: `{summary.get('check_count')}`",
        f"- Source review preflight items: `{summary.get('review_preflight_item_count')}`",
        f"- Source artifact manifest requirements: `{summary.get('artifact_manifest_requirement_count')}`",
        f"- No-go status count: `{summary.get('no_go_status_count')}`",
        f"- Future review requirements: `{summary.get('future_review_requirement_count')}`",
        "",
        "This static review did not run evaluation, replay, training, candidate "
        "generation, promotion, deployment, online selector activation, DP "
        "modification, or safety/CAMP-over-DP claim construction.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _artifact_hash_checks(
    files: dict[str, Path],
    root_sha256s: dict[str, str],
    preflight_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    root_expected = {
        "command": ("COMMAND", "./COMMAND"),
        "heads": ("HEADS", "./HEADS"),
        "stdout": ("stdout.txt", "./stdout.txt"),
        "stderr": ("stderr.txt", "./stderr.txt"),
        "run_exit": ("run.exit", "./run.exit"),
        "preflight_json": (PREFLIGHT_JSON_NAME, f"preflight/{PREFLIGHT_JSON_NAME}", f"./preflight/{PREFLIGHT_JSON_NAME}"),
        "preflight_md": (PREFLIGHT_MD_NAME, f"preflight/{PREFLIGHT_MD_NAME}", f"./preflight/{PREFLIGHT_MD_NAME}"),
        "preflight_sha256s": ("SHA256SUMS", "preflight/SHA256SUMS", "./preflight/SHA256SUMS"),
    }
    checks = [
        _check("artifact_root_sha256s_parseable", bool(root_sha256s), sorted(root_sha256s), "nonempty"),
        _check("artifact_preflight_sha256s_parseable", bool(preflight_sha256s), sorted(preflight_sha256s), "nonempty"),
    ]
    for name, keys in root_expected.items():
        checks.append(_sha256sums_expect(f"artifact_{name}_root_sha", files[name], root_sha256s, keys))
    checks.extend(
        [
            _sha256sums_expect("artifact_preflight_json_preflight_sha", files["preflight_json"], preflight_sha256s, (PREFLIGHT_JSON_NAME, f"./{PREFLIGHT_JSON_NAME}")),
            _sha256sums_expect("artifact_preflight_md_preflight_sha", files["preflight_md"], preflight_sha256s, (PREFLIGHT_MD_NAME, f"./{PREFLIGHT_MD_NAME}")),
            _expect("artifact_run_exit_zero", _read_text(files["run_exit"]).strip(), "0"),
        ]
    )
    return checks


def _heads_checks(heads: dict[str, str], source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = _dict(source_preflight.get("analysis"))
    return [
        _expect("artifact_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _check("artifact_heads_camp_head_is_sha", _is_git_sha(str(heads.get("camp_head", ""))), heads.get("camp_head"), "40-char git sha"),
        _check("artifact_heads_camp_origin_is_sha", _is_git_sha(str(heads.get("camp_origin_main", ""))), heads.get("camp_origin_main"), "40-char git sha"),
        _expect("artifact_heads_camp_matches_origin", heads.get("camp_head"), heads.get("camp_origin_main")),
        _expect("source_preflight_current_dp_fixed", analysis.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("source_preflight_required_dp_fixed", analysis.get("required_dp_head"), FIXED_DP_HEAD),
    ]


def _source_preflight_contract_checks(source_preflight: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_preflight.get("final_decision"))
    analysis = _dict(source_preflight.get("analysis"))
    no_go = _list(source_preflight.get("no_go_status"))
    checks = [
        _expect("source_preflight_schema", source_preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA),
        _expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_passed", decision.get("passed"), True),
        _expect("source_preflight_failed_checks", decision.get("failed_checks"), []),
        _expect("source_preflight_failure_class", decision.get("failure_class"), None),
        _expect("source_preflight_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect(
            "source_preflight_static_review_authorized",
            decision.get("uncertainty_coverage_review_preflight_static_review_authorized"),
            True,
        ),
        _expect("source_preflight_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_preflight_preflight_only", analysis.get("preflight_only"), True),
        _expect("source_preflight_read_only", analysis.get("read_only"), True),
        _expect("source_preflight_check_failures", _failed_source_checks(source_preflight), []),
        _expect("source_preflight_check_count", len(_list(source_preflight.get("preflight_checks"))), EXPECTED_SOURCE["preflight_check_count"]),
        _expect("source_preflight_uncertainty_coverage_review_preflight_count", len(_list(source_preflight.get("uncertainty_coverage_review_preflight"))), EXPECTED_SOURCE["review_preflight_item_count"]),
        _expect("source_preflight_artifact_manifest_requirement_count", len(_list(source_preflight.get("artifact_manifest_requirements"))), EXPECTED_SOURCE["artifact_manifest_requirement_count"]),
        _expect("source_preflight_no_go_status_count", len(no_go), EXPECTED_SOURCE["no_go_count"]),
        _expect("source_preflight_future_review_requirement_count", len(_list(source_preflight.get("future_review_requirements"))), EXPECTED_SOURCE["future_review_requirement_count"]),
        _expect("source_preflight_no_go_triggered", [item.get("name") for item in no_go if isinstance(item, dict) and item.get("triggered")], []),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_preflight_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_preflight_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_preflight_blocked_{action}", _dict(source_preflight.get("blocked_actions")).get(action), False))
    for flag in EXECUTION_FLAGS:
        checks.append(_expect(f"source_preflight_decision_{flag}", decision.get(flag), False))
    return checks


def _source_surface_checks(script: str, test: str) -> list[dict[str, Any]]:
    return [
        _contains("source_surface_script_schema", script, "promotion_readiness_uncertainty_coverage_review_preflight_v1"),
        _contains("source_surface_script_static_review_next", script, "promotion_readiness_uncertainty_coverage_review_preflight_static_review_only"),
        _contains("source_surface_script_static_review_flag", script, "uncertainty_coverage_review_preflight_static_review_authorized"),
        _contains("source_surface_script_affine_score", script, SCORE_EXPRESSION),
        _contains("source_surface_script_blocks_promotion", script, '"promotion_executed": False'),
        _contains("source_surface_script_blocks_deployment", script, '"deployment_executed": False'),
        _contains("source_surface_script_blocks_training", script, '"training_execution": False'),
        _contains("source_surface_script_blocks_replay", script, '"replay_execution": False'),
        _contains("source_surface_script_blocks_candidate_generation", script, '"candidate_generation": False'),
        _contains("source_surface_script_blocks_dp_modification", script, '"dp_modification": False'),
        _contains("source_surface_test_pass_case", test, "test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_passes"),
        _contains("source_surface_test_requires_enable", test, "test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_requires_enable"),
        _contains("source_surface_test_rejects_wrong_eof", test, "test_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_rejects_wrong_eof"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    latest_audit_pair = (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target"))
    latest_status_pair = (
        _latest_value(status_text, "current_v14_status"),
        _latest_value(status_text, "next_work_target"),
    )
    allowed_pairs = (
        (SOURCE_PREFLIGHT_STATUS, AUTHORIZED_CURRENT_WORK),
        (FAILED_ATTEMPT_STATUS, AUTHORIZED_RERUN_DECISION_WORK),
    )
    checks = [
        _check("audit_latest_eof_authorizes_static_review", latest_audit_pair in allowed_pairs, latest_audit_pair, allowed_pairs),
        _check("status_doc_latest_eof_authorizes_static_review", latest_status_pair in allowed_pairs, latest_status_pair, allowed_pairs),
        _expect("audit_preflight_ready", _latest_value(v14_text, "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_ready"), "True"),
        _expect(
            "audit_preflight_static_review_authorized",
            _latest_value_any(
                v14_text,
                (
                    "uncertainty_coverage_review_preflight_static_review_authorized",
                    "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized",
                ),
            ),
            "True",
        ),
        _expect("audit_runtime_execution_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]
    if latest_audit_pair == (FAILED_ATTEMPT_STATUS, AUTHORIZED_RERUN_DECISION_WORK):
        checks.extend(
            [
                _expect(
                    "audit_failed_attempt_failure_class",
                    _latest_value(v14_text, f"{FAILED_ATTEMPT_PREFIX}_failure_class"),
                    "v14_eof_contract_mismatch",
                ),
                _expect(
                    "audit_failed_attempt_failed_checks",
                    _latest_value(v14_text, f"{FAILED_ATTEMPT_PREFIX}_checks"),
                    "audit_preflight_static_review_authorized",
                ),
            ]
        )
    return checks


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_preflight.get("final_decision"))
    return {
        "schema_version": source_preflight.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "check_count": len(_list(source_preflight.get("preflight_checks"))),
        "review_preflight_item_count": len(_list(source_preflight.get("uncertainty_coverage_review_preflight"))),
        "artifact_manifest_requirement_count": len(_list(source_preflight.get("artifact_manifest_requirements"))),
        "no_go_status_count": len(_list(source_preflight.get("no_go_status"))),
        "future_review_requirement_count": len(_list(source_preflight.get("future_review_requirements"))),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_passed": bool(passed),
        "uncertainty_coverage_review_authorized": bool(passed),
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "recommendation": "run_read_only_uncertainty_coverage_review_only",
        "immediate_action": "run_uncertainty_coverage_review_only",
        "score_expression": SCORE_EXPRESSION,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "static_review_enabled" in failed_set:
        return "explicit_preflight_static_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "artifact_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "preflight_artifact_sha256_mismatch"
    if any(name.startswith("source_surface_") for name in failed):
        return "source_surface_contract_failure"
    if any(name.startswith("source_preflight_") for name in failed):
        return "source_preflight_contract_failure"
    if any(name.startswith("artifact_heads_") for name in failed):
        return "artifact_heads_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "promotion_readiness_uncertainty_coverage_review_preflight_static_review_failure"


def _path_checks(name: str, path: Path, *, require_file: bool, allow_empty: bool = False) -> list[dict[str, Any]]:
    exists = path.is_file() if require_file else path.is_dir()
    checks = [_check(f"{name}_exists", exists, str(path), "file" if require_file else "directory")]
    if require_file and not allow_empty:
        checks.append(_check(f"{name}_nonempty", path.is_file() and path.stat().st_size > 0, path.stat().st_size if path.is_file() else None, ">0 bytes"))
    return checks


def _sha256sums_expect(name: str, path: Path, sha256sums: dict[str, str], keys: tuple[str, ...]) -> dict[str, Any]:
    observed = _sha256(path) if path.is_file() else None
    listed = [sha256sums.get(key) for key in keys if key in sha256sums]
    return _check(name, observed is not None and observed in listed, {"observed": observed, "listed": listed, "keys": keys}, "matching sha256 listed in SHA256SUMS")


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "observed": _stable(observed), "expected": _stable(expected)}


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _read_sha256sums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            key = parts[1].strip()
            value = parts[0]
            values[key] = value
            values[key.removeprefix("./")] = value
            values[Path(key).name] = value
    return values


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        values[key] = value
        values[key.lower()] = value
    return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    matches = [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


def _latest_value_any(text: str, keys: tuple[str, ...]) -> str | None:
    matches: list[tuple[int, str]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        for key in keys:
            prefix = f"{key}="
            if line.startswith(prefix):
                matches.append((index, line[len(prefix) :].strip()))
    return matches[-1][1] if matches else None


def _failed_source_checks(source_preflight: dict[str, Any]) -> list[str]:
    return [
        str(check.get("name"))
        for check in _list(source_preflight.get("preflight_checks"))
        if isinstance(check, dict) and not check.get("passed")
    ]


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _compact(value: Any) -> str:
    text = json.dumps(_stable(value), ensure_ascii=True, sort_keys=True)
    return text if len(text) <= 140 else text[:137] + "..."


if __name__ == "__main__":
    raise SystemExit(main())

