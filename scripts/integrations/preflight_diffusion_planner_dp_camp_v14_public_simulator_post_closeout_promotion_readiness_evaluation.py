#!/usr/bin/env python3
"""Read-only v14 post-closeout promotion-readiness evaluation preflight.

This gate consumes the audited preflight-plan static review and the source
preflight plan. It checks the fixed-DP boundary, source artifact hashes, EOF
authorization, and no-go conditions for a future promotion-readiness evaluation
discussion. It does not run evaluation, replay, training, candidate generation,
promotion, deployment, online selector activation, DP modification, or
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

SOURCE_STATIC_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_preflight_plan_static_review_v1"
)
SOURCE_PLAN_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_preflight_plan_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_evaluation_preflight_v1"
)
SOURCE_STATIC_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_passed"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_preflight_plan_ready"
)
SOURCE_PLAN_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_only"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_preflight_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_evaluation_preflight_static_review_only"
)

STATIC_REVIEW_JSON_NAME = (
    "post_closeout_promotion_readiness_evaluation_preflight_plan_static_review.json"
)
STATIC_REVIEW_MD_NAME = (
    "post_closeout_promotion_readiness_evaluation_preflight_plan_static_review.md"
)
PLAN_JSON_NAME = "post_closeout_promotion_readiness_evaluation_preflight_plan.json"
PREFLIGHT_JSON_NAME = "post_closeout_promotion_readiness_evaluation_preflight.json"
PREFLIGHT_MD_NAME = "post_closeout_promotion_readiness_evaluation_preflight.md"

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
EXPECTED_PREFLIGHT_PLAN_NAMES = (
    "claim_boundary_preflight",
    "default_off_selector_preflight",
    "fixed_dp_provenance_preflight",
    "split_and_seed_preflight",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight_plan_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--preflight_plan_static_review_json", type=Path, required=True)
    parser.add_argument("--preflight_plan_static_review_md", type=Path, required=True)
    parser.add_argument("--preflight_plan_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_json", type=Path, required=True)
    parser.add_argument("--source_preflight_plan_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_evaluation_preflight",
        action="store_true",
        help="Explicit opt-in for the read-only promotion-readiness evaluation preflight.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        preflight_plan_static_review_artifact_dir=args.preflight_plan_static_review_artifact_dir,
        preflight_plan_static_review_json=args.preflight_plan_static_review_json,
        preflight_plan_static_review_md=args.preflight_plan_static_review_md,
        preflight_plan_static_review_sha256s=args.preflight_plan_static_review_sha256s,
        source_preflight_plan_artifact_dir=args.source_preflight_plan_artifact_dir,
        source_preflight_plan_json=args.source_preflight_plan_json,
        source_preflight_plan_sha256s=args.source_preflight_plan_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_evaluation_preflight,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    preflight_plan_static_review_artifact_dir: Path,
    preflight_plan_static_review_json: Path,
    preflight_plan_static_review_md: Path,
    preflight_plan_static_review_sha256s: Path,
    source_preflight_plan_artifact_dir: Path,
    source_preflight_plan_json: Path,
    source_preflight_plan_sha256s: Path,
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
    static_artifact = preflight_plan_static_review_artifact_dir.resolve()
    plan_artifact = source_preflight_plan_artifact_dir.resolve()
    paths = {
        "preflight_plan_static_review_json": preflight_plan_static_review_json.resolve(),
        "preflight_plan_static_review_md": preflight_plan_static_review_md.resolve(),
        "preflight_plan_static_review_sha256s": preflight_plan_static_review_sha256s.resolve(),
        "source_preflight_plan_json": source_preflight_plan_json.resolve(),
        "source_preflight_plan_sha256s": source_preflight_plan_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    static_artifact_files = {
        "command": static_artifact / "COMMAND",
        "heads": static_artifact / "HEADS",
        "stdout": static_artifact / "stdout.txt",
        "stderr": static_artifact / "stderr.txt",
        "run_exit": static_artifact / "run.exit",
        "root_sha256s": static_artifact / "SHA256SUMS",
        "review_json": static_artifact / "review" / STATIC_REVIEW_JSON_NAME,
        "review_md": static_artifact / "review" / STATIC_REVIEW_MD_NAME,
        "review_sha256s": static_artifact / "review" / "SHA256SUMS",
    }

    static_review = _read_json_dict(paths["preflight_plan_static_review_json"])
    source_plan = _read_json_dict(paths["source_preflight_plan_json"])
    static_root_sha256s = _read_sha256sums(static_artifact_files["root_sha256s"])
    static_review_sha256s = _read_sha256sums(paths["preflight_plan_static_review_sha256s"])
    source_plan_sha256s = _read_sha256sums(paths["source_preflight_plan_sha256s"])
    heads = _parse_key_values(_read_text(static_artifact_files["heads"]))
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("preflight_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("static_review_artifact_dir_exists", static_artifact.is_dir(), str(static_artifact), "directory"),
        _check("source_plan_artifact_dir_exists", plan_artifact.is_dir(), str(plan_artifact), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in static_artifact_files.items():
        checks.extend(_path_checks(f"static_review_artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("static_review_json_matches_artifact_layout", paths["preflight_plan_static_review_json"], static_artifact_files["review_json"]),
            _expect("static_review_md_matches_artifact_layout", paths["preflight_plan_static_review_md"], static_artifact_files["review_md"]),
            _expect("static_review_sha256s_matches_artifact_layout", paths["preflight_plan_static_review_sha256s"], static_artifact_files["review_sha256s"]),
            _expect("source_plan_json_matches_artifact_layout", paths["source_preflight_plan_json"], plan_artifact / "plan" / PLAN_JSON_NAME),
            _expect("source_plan_sha256s_matches_artifact_layout", paths["source_preflight_plan_sha256s"], plan_artifact / "plan" / "SHA256SUMS"),
        ]
    )
    checks.extend(_static_review_artifact_hash_checks(static_artifact_files, static_root_sha256s, static_review_sha256s))
    checks.extend(_source_plan_hash_checks(paths["source_preflight_plan_json"], source_plan_sha256s))
    checks.extend(_heads_checks(heads, static_review, plan_artifact))
    checks.extend(_static_review_contract_checks(static_review))
    checks.extend(_source_plan_contract_checks(source_plan))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "preflight_only": True,
            "read_only": True,
            "preflight_plan_static_review_artifact_dir": str(static_artifact),
            "source_preflight_plan_artifact_dir": str(plan_artifact),
            "preflight_plan_static_review_json": str(paths["preflight_plan_static_review_json"]),
            "source_preflight_plan_json": str(paths["source_preflight_plan_json"]),
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
            "math_boundary": (
                "This read-only preflight verifies that any later promotion-"
                "readiness evaluation discussion remains scoped to fixed DP "
                "candidate tensors. CAMP remains default-off shadow reranking "
                f"by affine {SCORE_EXPRESSION} over approved atoms and "
                "nonnegative simplex weights; simplex/CVaR/L2 masters remain convex."
            ),
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **static_artifact_files}.items()
        },
        "source_static_review_summary": _static_review_summary(static_review),
        "source_preflight_plan_summary": _source_plan_summary(source_plan),
        "evaluation_preflight": _evaluation_preflight(),
        "no_go_status": _no_go_status(),
        "future_review_requirements": _future_review_requirements(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "preflight_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / PREFLIGHT_JSON_NAME, report)
    (output_dir / PREFLIGHT_MD_NAME).write_text(render_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["source_static_review_summary"]
    plan = report["source_preflight_plan_summary"]
    lines = [
        "# Post-Closeout Promotion-Readiness Evaluation Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized current work: `{decision['authorized_current_work']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Source static review status: `{review.get('status')}`",
        f"- Source preflight plan status: `{plan.get('status')}`",
        f"- Evaluation preflight checks: `{len(report['evaluation_preflight'])}`",
        f"- No-go conditions false: `{all(not item['triggered'] for item in report['no_go_status'])}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP Top-1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Evaluation Preflight",
        "",
    ]
    for item in report["evaluation_preflight"]:
        lines.append(f"- `{item['name']}`: `{item['status']}`")
    lines.extend(["", "## No-Go Status", ""])
    for item in report["no_go_status"]:
        lines.append(f"- `{item['name']}`: triggered=`{item['triggered']}`")
    lines.extend(["", "## Future Review Requirements", ""])
    for item in report["future_review_requirements"]:
        lines.append(f"- `{item['name']}`: `{item['status']}`")
    lines.extend(
        [
            "",
            "This preflight did not run evaluation, replay, training, candidate "
            "generation, promotion, deployment, online selector activation, DP "
            "modification, or safety/CAMP-over-DP claim construction.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["preflight_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _static_review_artifact_hash_checks(
    files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    root_expected = {
        "command": ("COMMAND", "./COMMAND"),
        "heads": ("HEADS", "./HEADS"),
        "stdout": ("stdout.txt", "./stdout.txt"),
        "stderr": ("stderr.txt", "./stderr.txt"),
        "run_exit": ("run.exit", "./run.exit"),
        "review_json": (STATIC_REVIEW_JSON_NAME, f"review/{STATIC_REVIEW_JSON_NAME}", f"./review/{STATIC_REVIEW_JSON_NAME}"),
        "review_md": (STATIC_REVIEW_MD_NAME, f"review/{STATIC_REVIEW_MD_NAME}", f"./review/{STATIC_REVIEW_MD_NAME}"),
        "review_sha256s": ("SHA256SUMS", "review/SHA256SUMS", "./review/SHA256SUMS"),
    }
    checks = [
        _check("static_review_root_sha256s_parseable", bool(root_sha256s), sorted(root_sha256s), "nonempty"),
        _check("static_review_review_sha256s_parseable", bool(review_sha256s), sorted(review_sha256s), "nonempty"),
    ]
    for name, keys in root_expected.items():
        checks.append(_sha256sums_expect(f"static_review_artifact_{name}_root_sha", files[name], root_sha256s, keys))
    checks.extend(
        [
            _sha256sums_expect(
                "static_review_report_json_review_sha",
                files["review_json"],
                review_sha256s,
                (STATIC_REVIEW_JSON_NAME, f"./{STATIC_REVIEW_JSON_NAME}"),
            ),
            _sha256sums_expect(
                "static_review_report_md_review_sha",
                files["review_md"],
                review_sha256s,
                (STATIC_REVIEW_MD_NAME, f"./{STATIC_REVIEW_MD_NAME}"),
            ),
            _expect("static_review_artifact_run_exit_zero", _read_text(files["run_exit"]).strip(), "0"),
        ]
    )
    return checks


def _source_plan_hash_checks(source_plan_json: Path, sha256sums: dict[str, str]) -> list[dict[str, Any]]:
    return [
        _check("source_plan_sha256s_parseable", bool(sha256sums), sorted(sha256sums), "nonempty"),
        _sha256sums_expect(
            "source_preflight_plan_json_sha",
            source_plan_json,
            sha256sums,
            (PLAN_JSON_NAME, f"./{PLAN_JSON_NAME}"),
        ),
    ]


def _heads_checks(
    heads: dict[str, str],
    static_review: dict[str, Any],
    source_plan_artifact: Path,
) -> list[dict[str, Any]]:
    analysis = _dict(static_review.get("analysis"))
    return [
        _expect("static_review_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _check("static_review_heads_camp_head_is_sha", _is_git_sha(str(heads.get("camp_head", ""))), heads.get("camp_head"), "40-char git sha"),
        _check("static_review_heads_camp_origin_is_sha", _is_git_sha(str(heads.get("camp_origin_main", ""))), heads.get("camp_origin_main"), "40-char git sha"),
        _expect("static_review_heads_camp_matches_origin", heads.get("camp_head"), heads.get("camp_origin_main")),
        _expect("static_review_heads_source_plan_artifact", heads.get("source_preflight_plan_artifact"), str(source_plan_artifact)),
        _expect("static_review_analysis_source_plan_artifact", analysis.get("preflight_plan_artifact_dir"), str(source_plan_artifact)),
    ]


def _static_review_contract_checks(static_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(static_review.get("final_decision"))
    analysis = _dict(static_review.get("analysis"))
    checks = [
        _expect("source_static_review_schema", static_review.get("schema_version"), SOURCE_STATIC_REVIEW_SCHEMA),
        _expect("source_static_review_status", decision.get("status"), SOURCE_STATIC_REVIEW_STATUS),
        _expect("source_static_review_passed", decision.get("passed"), True),
        _expect("source_static_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_static_review_failure_class", decision.get("failure_class"), None),
        _expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_preflight_authorized", decision.get("promotion_readiness_evaluation_preflight_authorized"), True),
        _expect("source_static_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_static_review_static_review_only", analysis.get("static_review_only"), True),
        _expect("source_static_review_read_only", analysis.get("read_only"), True),
        _expect("source_static_review_check_failures", _failed_source_checks(static_review, "review_checks"), []),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_static_review_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_static_review_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_static_review_blocked_{action}", _dict(static_review.get("blocked_actions")).get(action), False))
    for flag in EXECUTION_FLAGS:
        checks.append(_expect(f"source_static_review_decision_{flag}", decision.get(flag), False))
    return checks


def _source_plan_contract_checks(source_plan: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_plan.get("final_decision"))
    analysis = _dict(source_plan.get("analysis"))
    preflight_names = sorted(
        str(item.get("name"))
        for item in _list(source_plan.get("preflight_plan"))
        if isinstance(item, dict) and item.get("name")
    )
    checks = [
        _expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        _expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks", decision.get("failed_checks"), []),
        _expect("source_plan_failure_class", decision.get("failure_class"), None),
        _expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), SOURCE_PLAN_AUTHORIZED_NEXT_WORK),
        _expect("source_plan_static_review_authorized", decision.get("preflight_plan_static_review_authorized"), True),
        _expect("source_plan_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_plan_preflight_names", preflight_names, sorted(EXPECTED_PREFLIGHT_PLAN_NAMES)),
        _check("source_plan_no_go_conditions_present", len(_list(source_plan.get("no_go_conditions"))) >= 7, len(_list(source_plan.get("no_go_conditions"))), ">=7"),
        _check("source_plan_forbidden_actions_present", len(_list(source_plan.get("forbidden_actions"))) >= 6, len(_list(source_plan.get("forbidden_actions"))), ">=6"),
        _expect("source_plan_check_failures", _failed_source_checks(source_plan, "plan_checks"), []),
        _expect("source_plan_plan_only", analysis.get("plan_only"), True),
        _expect("source_plan_read_only", analysis.get("read_only"), True),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_plan_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_plan_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_plan_blocked_{action}", _dict(source_plan.get("blocked_actions")).get(action), False))
    for flag in EXECUTION_FLAGS:
        checks.append(_expect(f"source_plan_decision_{flag}", decision.get(flag), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    expected_pair = (SOURCE_STATIC_REVIEW_STATUS, AUTHORIZED_CURRENT_WORK)
    return [
        _expect(
            "audit_latest_eof_authorizes_preflight",
            (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target")),
            expected_pair,
        ),
        _expect(
            "status_doc_latest_eof_authorizes_preflight",
            (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target")),
            expected_pair,
        ),
        _expect("audit_plan_static_review_passed", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_passed"), "True"),
        _expect("audit_preflight_authorized", _latest_value(v14_text, "post_closeout_promotion_readiness_evaluation_preflight_authorized"), "True"),
        _expect("audit_runtime_execution_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_execution_authorized"), "False"),
        _expect("audit_dp_modification_authorized", _latest_value(v14_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _evaluation_preflight() -> list[dict[str, str]]:
    return [
        {
            "name": "fixed_dp_candidate_source",
            "status": "ready_for_static_review_only",
            "requirement": "all future evaluation candidates must be preexisting fixed DP tensors",
        },
        {
            "name": "split_seed_boundary",
            "status": "ready_for_static_review_only",
            "requirement": "Full36 and formal seeds 11/12/13 remain out of scope",
        },
        {
            "name": "default_off_execution_policy",
            "status": "ready_for_static_review_only",
            "requirement": "executed output remains DP Top-1 unless a later EOF explicitly authorizes activation",
        },
        {
            "name": "claim_boundary",
            "status": "ready_for_static_review_only",
            "requirement": "no safety, deployability, or CAMP-over-DP Top-1 claim is authorized",
        },
        {
            "name": "artifact_immutability",
            "status": "ready_for_static_review_only",
            "requirement": "source plan and review artifacts remain SHA-pinned before any next gate",
        },
    ]


def _no_go_status() -> list[dict[str, Any]]:
    return [
        {"name": "dp_head_drift", "triggered": False},
        {"name": "camp_candidate_generation_or_repair", "triggered": False},
        {"name": "closed_loop_outcome_input", "triggered": False},
        {"name": "full36_or_formal_seed_11_12_13", "triggered": False},
        {"name": "non_affine_score", "triggered": False},
        {"name": "non_simplex_or_nonconvex_master", "triggered": False},
        {"name": "promotion_deployment_online_or_claim_bundled", "triggered": False},
    ]


def _future_review_requirements() -> list[dict[str, str]]:
    return [
        {
            "name": "preflight_static_review",
            "status": "required_before_any_evaluation_or_promotion_readiness_decision",
        },
        {
            "name": "immutable_artifact_hash_review",
            "status": "must_confirm_source plan and source static review artifacts",
        },
        {
            "name": "authorization_boundary_review",
            "status": "must keep promotion, deployment, online selector, and claims false",
        },
        {
            "name": "split_seed_dp_boundary_review",
            "status": "must confirm fixed DP, allowed split, and formal seed exclusions",
        },
    ]


def _static_review_summary(static_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(static_review.get("final_decision"))
    return {
        "schema_version": static_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(_list(static_review.get("review_checks"))),
    }


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    return {
        "schema_version": source_plan.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "preflight_plan_count": len(_list(source_plan.get("preflight_plan"))),
        "no_go_condition_count": len(_list(source_plan.get("no_go_conditions"))),
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
        "post_closeout_promotion_readiness_evaluation_preflight_ready": bool(passed),
        "preflight_static_review_authorized": bool(passed),
        "recommendation": "static_review_this_preflight_only",
        "immediate_action": "static_review_promotion_readiness_evaluation_preflight_only",
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
    if "preflight_enabled" in failed_set:
        return "explicit_preflight_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "static_review_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "source_artifact_sha256_mismatch"
    if any(name.startswith("source_static_review_") for name in failed):
        return "source_static_review_contract_failure"
    if any(name.startswith("source_plan_") for name in failed):
        return "source_preflight_plan_contract_failure"
    if any(name.startswith("static_review_heads_") for name in failed):
        return "source_artifact_heads_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "promotion_readiness_evaluation_preflight_failure"


def _path_checks(name: str, path: Path, *, require_file: bool, allow_empty: bool = False) -> list[dict[str, Any]]:
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


def _sha256sums_expect(name: str, path: Path, sha256sums: dict[str, str], keys: tuple[str, ...]) -> dict[str, Any]:
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
    return {"name": name, "passed": bool(passed), "observed": _stable(observed), "expected": _stable(expected)}


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


def _failed_source_checks(payload: dict[str, Any], field: str) -> list[str]:
    return [
        str(check.get("name"))
        for check in _list(payload.get(field))
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
