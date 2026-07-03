#!/usr/bin/env python3
"""Static review for the v14 post-closeout promotion-readiness gap analysis.

This gate reviews the already-materialized, plan-only gap-analysis artifact. It
checks artifact hashes, fixed-DP provenance, the no-promotion boundary, and the
current EOF contract. It does not promote, deploy, train, replay, generate
candidates, modify Diffusion Planner, change an online selector, or make
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

SOURCE_GAP_ANALYSIS_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_gap_analysis_plan_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_gap_analysis_static_review_v1"
)
SOURCE_READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_gap_analysis_plan_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_gap_analysis_static_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_gap_analysis_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_gap_analysis_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_preflight_plan_only"
)

GAP_JSON_NAME = "post_closeout_promotion_readiness_gap_analysis.json"
GAP_MD_NAME = "post_closeout_promotion_readiness_gap_analysis.md"

EXPECTED_GAP_CATEGORIES = (
    "active_selector_promotion",
    "camp_over_dp_top1_claim",
    "deployment_fail_closed",
    "evaluation_coverage",
    "governance_authorization",
    "safety_claim",
)
EXPECTED_DECISION_SURFACES = (
    "deployment_readiness",
    "promotion_readiness",
    "safety_or_superiority_claim",
)
EXPECTED_SOURCE_ARTIFACT_DIR_KEYS = (
    "closeout_review",
    "delta_review",
    "evidence_package",
    "promotion_plan",
    "result_review",
)
EXPECTED_HEAD_SOURCE_KEYS = (
    "previous_failed_gap_analysis_artifact",
    "source_evidence_package_artifact",
    "source_result_review_artifact",
    "source_shadow_vs_top1_delta_review_artifact",
    "source_promotion_decision_plan_artifact",
    "source_no_promotion_closeout_review_artifact",
)

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
ANALYSIS_BLOCK_FLAGS = (
    "training_execution",
    "replay_execution",
    "candidate_generation",
    "dp_modification",
    "online_selector_change",
    "promotion_executed",
    "deployment_executed",
    "safety_or_camp_over_dp_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gap_analysis_artifact_dir", type=Path, required=True)
    parser.add_argument("--gap_analysis_json", type=Path, required=True)
    parser.add_argument("--gap_analysis_md", type=Path, required=True)
    parser.add_argument("--gap_analysis_sha256s", type=Path, required=True)
    parser.add_argument("--gap_analysis_script_py", type=Path, required=True)
    parser.add_argument("--gap_analysis_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_gap_analysis_static_review",
        action="store_true",
        help="Explicit opt-in for read-only gap-analysis static review.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        gap_analysis_artifact_dir=args.gap_analysis_artifact_dir,
        gap_analysis_json=args.gap_analysis_json,
        gap_analysis_md=args.gap_analysis_md,
        gap_analysis_sha256s=args.gap_analysis_sha256s,
        gap_analysis_script_py=args.gap_analysis_script_py,
        gap_analysis_test_py=args.gap_analysis_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_gap_analysis_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    gap_analysis_artifact_dir: Path,
    gap_analysis_json: Path,
    gap_analysis_md: Path,
    gap_analysis_sha256s: Path,
    gap_analysis_script_py: Path,
    gap_analysis_test_py: Path,
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
    artifact_dir = gap_analysis_artifact_dir.resolve()
    paths = {
        "gap_analysis_json": gap_analysis_json.resolve(),
        "gap_analysis_md": gap_analysis_md.resolve(),
        "gap_analysis_sha256s": gap_analysis_sha256s.resolve(),
        "gap_analysis_script_py": gap_analysis_script_py.resolve(),
        "gap_analysis_test_py": gap_analysis_test_py.resolve(),
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
        "plan_json": artifact_dir / "plan" / GAP_JSON_NAME,
        "plan_md": artifact_dir / "plan" / GAP_MD_NAME,
        "plan_sha256s": artifact_dir / "plan" / "SHA256SUMS",
    }

    gap_analysis = _read_json_dict(paths["gap_analysis_json"])
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    plan_sha256s = _read_sha256sums(paths["gap_analysis_sha256s"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    script_text = _read_text(paths["gap_analysis_script_py"])
    test_text = _read_text(paths["gap_analysis_test_py"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("static_review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("gap_analysis_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(
            _path_checks(
                f"artifact_{name}",
                path,
                require_file=True,
                allow_empty=(name == "stderr"),
            )
        )
    checks.extend(
        [
            _expect("gap_analysis_json_matches_artifact_layout", paths["gap_analysis_json"], artifact_files["plan_json"]),
            _expect("gap_analysis_md_matches_artifact_layout", paths["gap_analysis_md"], artifact_files["plan_md"]),
            _expect("gap_analysis_sha256s_matches_artifact_layout", paths["gap_analysis_sha256s"], artifact_files["plan_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, plan_sha256s))
    checks.extend(_artifact_head_checks(heads, gap_analysis))
    checks.extend(_gap_analysis_contract_checks(gap_analysis))
    checks.extend(_source_surface_checks(script_text, test_text))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "read_only": True,
            "gap_analysis_artifact_dir": str(artifact_dir),
            "gap_analysis_json": str(paths["gap_analysis_json"]),
            "gap_analysis_md": str(paths["gap_analysis_md"]),
            "gap_analysis_sha256s": str(paths["gap_analysis_sha256s"]),
            "gap_analysis_script_py": str(paths["gap_analysis_script_py"]),
            "gap_analysis_test_py": str(paths["gap_analysis_test_py"]),
            "v14_audit_md": str(paths["v14_audit_md"]),
            "current_status_md": str(paths["current_status_md"]),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "artifact_camp_head": heads.get("camp_head"),
            "artifact_camp_origin_main": heads.get("camp_origin_main"),
            "artifact_dp_head": heads.get("dp_head"),
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "math_boundary": (
                "This static review audits the post-closeout gap-analysis "
                "artifact only. CAMP remains a default-off shadow reranker "
                f"over fixed DP candidate tensors with affine {SCORE_EXPRESSION} "
                "over approved atoms and nonnegative simplex weights."
            ),
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_gap_analysis_summary": _source_summary(gap_analysis),
        "gap_categories": _gap_categories(gap_analysis),
        "readiness_surfaces": _readiness_surfaces(gap_analysis),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "post_closeout_promotion_readiness_gap_analysis_static_review.json", report)
    (output_dir / "post_closeout_promotion_readiness_gap_analysis_static_review.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_gap_analysis_summary"]
    lines = [
        "# Post-Closeout Promotion-Readiness Gap Analysis Static Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized current work: `{decision['authorized_current_work']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Recommendation: `{decision['recommendation']}`",
        f"- Immediate action: `{decision['immediate_action']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP Top-1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Source Gap Analysis",
        "",
        f"- Schema: `{summary.get('schema_version')}`",
        f"- Status: `{summary.get('status')}`",
        f"- Passed: `{summary.get('passed')}`",
        f"- Authorized next work: `{summary.get('authorized_next_work')}`",
        f"- Recommendation: `{summary.get('recommendation')}`",
        f"- Immediate action: `{summary.get('immediate_action')}`",
        f"- Gap categories: `{','.join(report['gap_categories'])}`",
        f"- Readiness surfaces: `{','.join(report['readiness_surfaces'])}`",
        "",
        "This static review did not promote atoms or selectors, deploy, train "
        "CAMP, run replay, generate candidates, modify DP, change online "
        "selection, or authorize safety/CAMP-over-DP claims.",
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
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    plan_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    root_expected = {
        "command": ("COMMAND", "./COMMAND"),
        "heads": ("HEADS", "./HEADS"),
        "stdout": ("stdout.txt", "./stdout.txt"),
        "stderr": ("stderr.txt", "./stderr.txt"),
        "run_exit": ("run.exit", "./run.exit"),
        "plan_json": (GAP_JSON_NAME, f"plan/{GAP_JSON_NAME}", f"./plan/{GAP_JSON_NAME}"),
        "plan_md": (GAP_MD_NAME, f"plan/{GAP_MD_NAME}", f"./plan/{GAP_MD_NAME}"),
    }
    checks = [
        _check("artifact_root_sha256s_parseable", bool(root_sha256s), sorted(root_sha256s), "nonempty"),
        _check("artifact_plan_sha256s_parseable", bool(plan_sha256s), sorted(plan_sha256s), "nonempty"),
    ]
    for name, keys in root_expected.items():
        checks.append(
            _sha256sums_expect(
                f"artifact_{name}_root_sha",
                artifact_files[name],
                root_sha256s,
                keys,
            )
        )
    checks.extend(
        [
            _sha256sums_expect(
                "artifact_plan_json_plan_sha",
                artifact_files["plan_json"],
                plan_sha256s,
                (GAP_JSON_NAME, f"./{GAP_JSON_NAME}"),
            ),
            _sha256sums_expect(
                "artifact_plan_md_plan_sha",
                artifact_files["plan_md"],
                plan_sha256s,
                (GAP_MD_NAME, f"./{GAP_MD_NAME}"),
            ),
            _expect("artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
        ]
    )
    return checks


def _artifact_head_checks(heads: dict[str, str], gap_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = _dict(gap_analysis.get("analysis"))
    artifact_dirs = _dict(analysis.get("artifact_dirs"))
    checks = [
        _expect("artifact_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _check("artifact_heads_camp_head_is_sha", _is_git_sha(str(heads.get("camp_head", ""))), heads.get("camp_head"), "40-char git sha"),
        _check("artifact_heads_camp_origin_is_sha", _is_git_sha(str(heads.get("camp_origin_main", ""))), heads.get("camp_origin_main"), "40-char git sha"),
        _expect("artifact_heads_camp_matches_origin", heads.get("camp_head"), heads.get("camp_origin_main")),
        _expect("gap_analysis_analysis_dp_fixed", analysis.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("gap_analysis_analysis_required_dp_fixed", analysis.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("gap_analysis_analysis_camp_matches_origin", analysis.get("current_camp_head"), analysis.get("current_camp_origin_main")),
        _expect("gap_analysis_analysis_camp_matches_artifact_head", analysis.get("current_camp_head"), heads.get("camp_head")),
    ]
    for key in EXPECTED_HEAD_SOURCE_KEYS:
        checks.append(_check(f"artifact_heads_{key}_present", bool(heads.get(key)), heads.get(key), "nonempty path"))
    checks.append(
        _expect(
            "gap_analysis_artifact_dir_keys",
            sorted(artifact_dirs),
            sorted(EXPECTED_SOURCE_ARTIFACT_DIR_KEYS),
        )
    )
    for key in EXPECTED_SOURCE_ARTIFACT_DIR_KEYS:
        path = Path(str(artifact_dirs.get(key, "")))
        checks.append(_check(f"gap_analysis_source_artifact_{key}_dir_exists", path.is_dir(), str(path), "directory"))
    return checks


def _gap_analysis_contract_checks(gap_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(gap_analysis.get("final_decision"))
    analysis = _dict(gap_analysis.get("analysis"))
    blocked = _dict(gap_analysis.get("blocked_actions"))
    checks = [
        _expect("source_gap_analysis_schema", gap_analysis.get("schema_version"), SOURCE_GAP_ANALYSIS_SCHEMA),
        _expect("source_gap_analysis_status", decision.get("status"), SOURCE_READY_STATUS),
        _expect("source_gap_analysis_passed", decision.get("passed"), True),
        _expect("source_gap_analysis_failed_checks", decision.get("failed_checks"), []),
        _expect("source_gap_analysis_failure_class", decision.get("failure_class"), None),
        _expect("source_gap_analysis_authorized_next_work", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_gap_analysis_recommendation", decision.get("recommendation"), "do_not_promote_or_deploy_from_current_evidence_package"),
        _expect("source_gap_analysis_immediate_action", decision.get("immediate_action"), "static_review_this_gap_analysis_only"),
        _expect("source_gap_analysis_ready_flag", decision.get("post_closeout_promotion_readiness_gap_analysis_ready"), True),
        _expect("source_gap_analysis_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_gap_analysis_plan_only", analysis.get("plan_only"), True),
        _expect("source_gap_analysis_read_only", analysis.get("read_only"), True),
        _expect("source_gap_categories", sorted(_gap_categories(gap_analysis)), sorted(EXPECTED_GAP_CATEGORIES)),
        _expect("source_gap_readiness_surfaces", sorted(_readiness_surfaces(gap_analysis)), sorted(EXPECTED_DECISION_SURFACES)),
        _expect("source_gap_check_failures", _failed_source_checks(gap_analysis), []),
    ]
    for flag in ANALYSIS_BLOCK_FLAGS:
        checks.append(_expect(f"source_gap_analysis_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_gap_analysis_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_gap_analysis_blocked_{action}", blocked.get(action), False))
    for flag in EXECUTION_FLAGS:
        checks.append(_expect(f"source_gap_analysis_decision_{flag}", decision.get(flag), False))
    checks.extend(_gap_category_checks(gap_analysis))
    checks.extend(_readiness_matrix_checks(gap_analysis))
    return checks


def _gap_category_checks(gap_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    by_category = {
        gap.get("category"): gap
        for gap in _list(gap_analysis.get("evidence_gaps"))
        if isinstance(gap, dict)
    }
    for category in EXPECTED_GAP_CATEGORIES:
        gap = _dict(by_category.get(category))
        checks.extend(
            [
                _expect(f"source_gap_{category}_status_open", gap.get("gap_status"), "open"),
                _check(f"source_gap_{category}_limit_present", bool(gap.get("current_evidence_limit")), gap.get("current_evidence_limit"), "nonempty"),
                _check(f"source_gap_{category}_future_evidence_present", bool(_list(gap.get("required_future_evidence"))), gap.get("required_future_evidence"), "nonempty list"),
            ]
        )
    return checks


def _readiness_matrix_checks(gap_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    by_surface = {
        row.get("decision_surface"): row
        for row in _list(gap_analysis.get("promotion_readiness_matrix"))
        if isinstance(row, dict)
    }
    expectations = {
        "promotion_readiness": {
            "current_state": "not_ready_for_active_promotion",
            "promotion_authorized": False,
        },
        "deployment_readiness": {
            "current_state": "not_ready_for_deployment",
            "deployment_authorized": False,
        },
        "safety_or_superiority_claim": {
            "current_state": "not_ready_for_claim",
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    for surface, fields in expectations.items():
        row = _dict(by_surface.get(surface))
        checks.append(_expect(f"readiness_{surface}_next_allowed_gate", row.get("next_allowed_gate"), SOURCE_AUTHORIZED_NEXT_WORK))
        for key, expected in fields.items():
            checks.append(_expect(f"readiness_{surface}_{key}", row.get(key), expected))
    return checks


def _source_surface_checks(script: str, test: str) -> list[dict[str, Any]]:
    return [
        _contains("source_surface_script_gap_schema", script, "promotion_readiness_gap_analysis_plan_v1"),
        _contains(
            "source_surface_script_static_review_next",
            script,
            "post_closeout_promotion_readiness_gap_analysis_static_review_only",
        ),
        _contains("source_surface_script_affine_score", script, SCORE_EXPRESSION),
        _contains("source_surface_script_plan_only", script, '"plan_only": True'),
        _contains("source_surface_script_read_only", script, '"read_only": True'),
        _contains("source_surface_script_blocks_promotion", script, '"promotion_executed": False'),
        _contains("source_surface_script_blocks_deployment", script, '"deployment_executed": False'),
        _contains("source_surface_script_blocks_training", script, '"training_execution": False'),
        _contains("source_surface_script_blocks_replay", script, '"replay_execution": False'),
        _contains("source_surface_script_blocks_candidate_generation", script, '"candidate_generation": False'),
        _contains("source_surface_script_blocks_dp_modification", script, '"dp_modification": False'),
        _contains("source_surface_script_blocks_safety_claim", script, '"safety_or_camp_over_dp_claim": False'),
        _contains("source_surface_test_pass_case", test, "test_post_closeout_promotion_readiness_gap_analysis_passes"),
        _contains("source_surface_test_uppercase_heads_case", test, "test_post_closeout_promotion_readiness_gap_analysis_accepts_uppercase_heads"),
        _contains("source_surface_test_contract_rerun_case", test, "test_post_closeout_promotion_readiness_gap_analysis_accepts_contract_fix_rerun_eof"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    audit_pair = (
        _latest_value(v14_text, "current_v14_status"),
        _latest_value(v14_text, "next_work_target"),
    )
    status_pair = (
        _latest_value(status_text, "current_v14_status"),
        _latest_value(status_text, "next_work_target"),
    )
    expected_pair = (SOURCE_READY_STATUS, SOURCE_AUTHORIZED_NEXT_WORK)
    return [
        _expect("audit_latest_eof_authorizes_static_review", audit_pair, expected_pair),
        _expect("status_doc_latest_eof_authorizes_static_review", status_pair, expected_pair),
        _expect("audit_gap_analysis_passed", _latest_value(v14_text, "post_closeout_promotion_readiness_gap_analysis_passed"), "True"),
        _expect("audit_gap_analysis_static_review_authorized", _latest_value(v14_text, "post_closeout_promotion_readiness_gap_analysis_static_review_authorized"), "True"),
        _expect("audit_no_promotion_closeout_complete", _latest_value(v14_text, "default_off_shadow_selector_runtime_no_promotion_closeout_complete"), "True"),
        _expect("audit_runtime_execution_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _source_summary(gap_analysis: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(gap_analysis.get("final_decision"))
    return {
        "schema_version": gap_analysis.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "failed_checks": decision.get("failed_checks"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "recommendation": decision.get("recommendation"),
        "immediate_action": decision.get("immediate_action"),
        "score_expression": decision.get("score_expression"),
    }


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_readiness_gap_analysis_static_review_passed": bool(passed),
        "promotion_readiness_evaluation_preflight_plan_authorized": bool(passed),
        "recommendation": "keep_no_promotion_and_plan_readiness_preflight_only",
        "immediate_action": "plan_promotion_readiness_evaluation_preflight_only",
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
        return "explicit_gap_analysis_static_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "artifact_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") or name.endswith("_plan_sha") for name in failed):
        return "gap_analysis_artifact_sha256_mismatch"
    if any(name.startswith("source_surface_") for name in failed):
        return "source_surface_contract_failure"
    if any(name.startswith("source_gap_") or name.startswith("readiness_") for name in failed):
        return "source_gap_analysis_contract_failure"
    if any(name.startswith("artifact_heads_") or name.startswith("gap_analysis_analysis_") for name in failed):
        return "gap_analysis_artifact_head_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "post_closeout_promotion_readiness_gap_analysis_static_review_failure"


def _path_checks(
    name: str,
    path: Path,
    *,
    require_file: bool,
    allow_empty: bool = False,
) -> list[dict[str, Any]]:
    exists = path.is_file() if require_file else path.is_dir()
    checks = [_check(f"{name}_exists", exists, str(path), "file" if require_file else "directory")]
    if require_file and not allow_empty:
        checks.append(
            _check(
                f"{name}_nonempty",
                path.is_file() and path.stat().st_size > 0,
                path.stat().st_size if path.is_file() else None,
                ">0 bytes",
            )
        )
    return checks


def _sha256sums_expect(
    name: str,
    path: Path,
    sha256sums: dict[str, str],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    observed = _sha256(path) if path.is_file() else None
    listed = [sha256sums.get(key) for key in keys if key in sha256sums]
    return _check(
        name,
        observed is not None and observed in listed,
        {"observed": observed, "listed": listed, "keys": keys},
        "matching sha256 listed in SHA256SUMS",
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


def _gap_categories(gap_analysis: dict[str, Any]) -> list[str]:
    return [
        str(gap.get("category"))
        for gap in _list(gap_analysis.get("evidence_gaps"))
        if isinstance(gap, dict) and gap.get("category")
    ]


def _readiness_surfaces(gap_analysis: dict[str, Any]) -> list[str]:
    return [
        str(row.get("decision_surface"))
        for row in _list(gap_analysis.get("promotion_readiness_matrix"))
        if isinstance(row, dict) and row.get("decision_surface")
    ]


def _failed_source_checks(gap_analysis: dict[str, Any]) -> list[str]:
    return [
        str(check.get("name"))
        for check in _list(gap_analysis.get("gap_analysis_checks"))
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
