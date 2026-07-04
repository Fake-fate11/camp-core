#!/usr/bin/env python3
"""Static contract review for the v14 uncertainty/coverage review artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_review_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_"
    "promotion_readiness_uncertainty_coverage_review_static_review_v1"
)
SOURCE_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_only"
)
SOURCE_REVIEW_JSON_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review.json"
SOURCE_REVIEW_MD_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review.md"
REVIEW_JSON_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review.json"
REVIEW_MD_NAME = "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review.md"

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
FALSE_EXECUTION_FLAGS = (
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
EXPECTED_REVIEW_ITEMS = (
    "fixed_dp_candidate_tensor_boundary",
    "score_margin_uncertainty_surface",
    "coverage_slice_matrix",
    "candidate_tensor_support_coverage",
    "atom_contribution_stability",
    "default_off_fail_closed_boundary",
    "claim_and_promotion_boundary",
)
EXPECTED_EVIDENCE_GAPS = (
    "future_uncertainty_input_manifest",
    "future_coverage_slice_manifest",
    "future_atom_stability_manifest",
    "future_no_go_summary",
    "future_claim_boundary_summary",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review_artifact_dir", type=Path, required=True)
    parser.add_argument("--review_json", type=Path, required=True)
    parser.add_argument("--review_md", type=Path, required=True)
    parser.add_argument("--review_sha256s", type=Path, required=True)
    parser.add_argument("--review_script_py", type=Path, required=True)
    parser.add_argument("--review_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review",
        action="store_true",
        help="Explicit opt-in for read-only static review of the uncertainty/coverage review artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        review_artifact_dir=args.review_artifact_dir,
        review_json=args.review_json,
        review_md=args.review_md,
        review_sha256s=args.review_sha256s,
        review_script_py=args.review_script_py,
        review_test_py=args.review_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    review_artifact_dir: Path,
    review_json: Path,
    review_md: Path,
    review_sha256s: Path,
    review_script_py: Path,
    review_test_py: Path,
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
    artifact_dir = review_artifact_dir.resolve()
    paths = {
        "review_json": review_json.resolve(),
        "review_md": review_md.resolve(),
        "review_sha256s": review_sha256s.resolve(),
        "review_script_py": review_script_py.resolve(),
        "review_test_py": review_test_py.resolve(),
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
        "review_json": artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": artifact_dir / "review" / "SHA256SUMS",
    }
    source_review = _read_json_dict(paths["review_json"])
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    review_sha256s_values = _read_sha256sums(paths["review_sha256s"])
    heads = _parse_key_values(_read_text(artifact_files["heads"]))
    script_text = _read_text(paths["review_script_py"])
    test_text = _read_text(paths["review_test_py"])
    v14_text = _read_text(paths["v14_audit_md"])
    status_text = _read_text(paths["current_status_md"])

    checks: list[dict[str, Any]] = [
        _expect("static_review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _check("review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(_path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(_path_checks(f"artifact_{name}", path, require_file=True, allow_empty=(name == "stderr")))
    checks.extend(
        [
            _expect("review_json_matches_artifact_layout", paths["review_json"], artifact_files["review_json"]),
            _expect("review_md_matches_artifact_layout", paths["review_md"], artifact_files["review_md"]),
            _expect("review_sha256s_matches_artifact_layout", paths["review_sha256s"], artifact_files["review_sha256s"]),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, review_sha256s_values))
    checks.extend(_heads_checks(heads, source_review))
    checks.extend(_source_review_contract_checks(source_review))
    checks.extend(_source_surface_checks(script_text, test_text))
    checks.extend(_audit_checks(v14_text, status_text))

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "read_only": True,
            "review_artifact_dir": str(artifact_dir),
            "review_json": str(paths["review_json"]),
            "review_script_py": str(paths["review_script_py"]),
            "review_test_py": str(paths["review_test_py"]),
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
            "score_expression": SCORE_EXPRESSION,
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in {**paths, **artifact_files}.items()
        },
        "source_review_summary": _source_review_summary(source_review),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / REVIEW_JSON_NAME, report)
    (output_dir / REVIEW_MD_NAME).write_text(_markdown(report), encoding="utf-8")
    _write_sha256sums(output_dir)


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    lines = [
        "# Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Static Review",
        "",
        f"- schema: `{report['schema_version']}`",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- failure_class: `{decision['failure_class']}`",
        f"- authorized_next_work: `{decision['authorized_next_work']}`",
        f"- failed_checks: `{', '.join(failed)}`",
        "",
        "## Source Review Summary",
    ]
    for key, value in report["source_review_summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks"])
    for check in report["review_checks"]:
        status = "pass" if check["passed"] else "fail"
        lines.append(
            f"- {status} `{check['name']}` observed=`{_compact(check['observed'])}` expected=`{_compact(check['expected'])}`"
        )
    lines.extend(
        [
            "",
            "This is a read-only static contract review. It authorizes only a "
            "read-only evidence-gap closure plan and does not run replay, train "
            "CAMP, generate candidates, modify DP, promote, deploy, activate an "
            "online selector, or make safety/CAMP-over-DP claims.",
        ]
    )
    return "\n".join(lines) + "\n"


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    review_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _sha256sums_expect("artifact_command_root_sha", artifact_files["command"], root_sha256s, ("COMMAND", "./COMMAND")),
        _sha256sums_expect("artifact_heads_root_sha", artifact_files["heads"], root_sha256s, ("HEADS", "./HEADS")),
        _sha256sums_expect("artifact_stdout_root_sha", artifact_files["stdout"], root_sha256s, ("stdout.txt", "./stdout.txt")),
        _sha256sums_expect("artifact_stderr_root_sha", artifact_files["stderr"], root_sha256s, ("stderr.txt", "./stderr.txt")),
        _sha256sums_expect("artifact_run_exit_root_sha", artifact_files["run_exit"], root_sha256s, ("run.exit", "./run.exit")),
        _sha256sums_expect("artifact_review_json_root_sha", artifact_files["review_json"], root_sha256s, (f"review/{SOURCE_REVIEW_JSON_NAME}", f"./review/{SOURCE_REVIEW_JSON_NAME}", SOURCE_REVIEW_JSON_NAME)),
        _sha256sums_expect("artifact_review_md_root_sha", artifact_files["review_md"], root_sha256s, (f"review/{SOURCE_REVIEW_MD_NAME}", f"./review/{SOURCE_REVIEW_MD_NAME}", SOURCE_REVIEW_MD_NAME)),
        _sha256sums_expect("artifact_review_sha256s_root_sha", artifact_files["review_sha256s"], root_sha256s, ("review/SHA256SUMS", "./review/SHA256SUMS", "SHA256SUMS")),
        _sha256sums_expect("source_review_json_review_sha", artifact_files["review_json"], review_sha256s, (SOURCE_REVIEW_JSON_NAME, f"./{SOURCE_REVIEW_JSON_NAME}")),
        _sha256sums_expect("source_review_md_review_sha", artifact_files["review_md"], review_sha256s, (SOURCE_REVIEW_MD_NAME, f"./{SOURCE_REVIEW_MD_NAME}")),
        _expect("artifact_run_exit_zero", _read_text(artifact_files["run_exit"]).strip(), "0"),
    ]


def _heads_checks(heads: dict[str, str], source_review: dict[str, Any]) -> list[dict[str, Any]]:
    analysis = _dict(source_review.get("analysis"))
    return [
        _expect("artifact_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD),
        _expect("artifact_heads_camp_matches_origin", heads.get("camp_head"), heads.get("camp_origin_main")),
        _expect("artifact_heads_camp_matches_analysis", heads.get("camp_head"), analysis.get("current_camp_head")),
        _expect("artifact_heads_origin_matches_analysis", heads.get("camp_origin_main"), analysis.get("current_camp_origin_main")),
    ]


def _source_review_contract_checks(source_review: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(source_review.get("final_decision"))
    analysis = _dict(source_review.get("analysis"))
    review_items = _list(source_review.get("uncertainty_coverage_review"))
    evidence_gaps = _list(source_review.get("evidence_gap_matrix"))
    checks = [
        _expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        _expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        _expect("source_review_passed", decision.get("passed"), True),
        _expect("source_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_review_failure_class", decision.get("failure_class"), None),
        _expect("source_review_authorized_current_work", decision.get("authorized_current_work"), SOURCE_REVIEW_STATUS.replace("_passed", "_only")),
        _expect("source_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_review_static_review_authorized", decision.get("uncertainty_coverage_review_static_review_authorized"), True),
        _expect("source_review_direct_promotion_recommendation", decision.get("direct_promotion_recommendation"), False),
        _expect("source_review_promotion_decision_plan_authorized_next", decision.get("promotion_decision_plan_authorized_next"), False),
        _expect("source_review_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_review_analysis_read_only", analysis.get("read_only"), True),
        _expect("source_review_analysis_review_only", analysis.get("uncertainty_coverage_review_only"), True),
        _expect("source_review_check_failures", _failed_source_checks(source_review, "review_checks"), []),
        _expect("source_review_check_count", len(_list(source_review.get("review_checks"))), 227),
        _expect("source_review_item_names", _names(review_items), list(EXPECTED_REVIEW_ITEMS)),
        _expect("source_review_item_count", len(review_items), len(EXPECTED_REVIEW_ITEMS)),
        _expect("source_review_items_no_execution", [item.get("authorizes_execution") for item in review_items], [False] * len(EXPECTED_REVIEW_ITEMS)),
        _expect("source_review_items_no_claim", [item.get("authorizes_claim") for item in review_items], [False] * len(EXPECTED_REVIEW_ITEMS)),
        _expect("source_review_evidence_gap_names", _names(evidence_gaps), list(EXPECTED_EVIDENCE_GAPS)),
        _expect("source_review_evidence_gap_count", len(evidence_gaps), len(EXPECTED_EVIDENCE_GAPS)),
        _expect("source_review_evidence_gaps_block_claim", [item.get("blocks_promotion_or_claim") for item in evidence_gaps], [True] * len(EXPECTED_EVIDENCE_GAPS)),
    ]
    for flag in ANALYSIS_FALSE_FLAGS:
        checks.append(_expect(f"source_review_analysis_{flag}", analysis.get(flag), False))
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_review_decision_{action}", decision.get(action), False))
        checks.append(_expect(f"source_review_blocked_{action}", _dict(source_review.get("blocked_actions")).get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_review_decision_{flag}", decision.get(flag), False))
    return checks


def _source_surface_checks(script_text: str, test_text: str) -> list[dict[str, Any]]:
    return [
        _contains("source_script_schema", script_text, "promotion_readiness_uncertainty_coverage_review_v1"),
        _contains("source_script_next_static_review", script_text, "uncertainty_coverage_review_static_review_only"),
        _contains("source_script_evidence_gap_matrix", script_text, "evidence_gap_matrix"),
        _contains("source_script_direct_promotion_false", script_text, '"direct_promotion_recommendation": False'),
        _contains("source_script_blocks_deployment", script_text, '"deployment_executed": False'),
        _contains("source_test_pass_case", test_text, "test_promotion_readiness_uncertainty_coverage_review_passes"),
        _contains("source_test_requires_enable", test_text, "test_promotion_readiness_uncertainty_coverage_review_requires_enable"),
        _contains("source_test_rejects_wrong_eof", test_text, "test_promotion_readiness_uncertainty_coverage_review_rejects_wrong_eof"),
    ]


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    expected_pair = (SOURCE_REVIEW_STATUS, AUTHORIZED_CURRENT_WORK)
    return [
        _expect("audit_latest_eof_authorizes_static_review", (_latest_value(v14_text, "current_v14_status"), _latest_value(v14_text, "next_work_target")), expected_pair),
        _expect("status_doc_latest_eof_authorizes_static_review", (_latest_value(status_text, "current_v14_status"), _latest_value(status_text, "next_work_target")), expected_pair),
        _expect("audit_uncertainty_coverage_review_passed", _latest_value(v14_text, "post_closeout_promotion_readiness_uncertainty_coverage_review_passed"), "True"),
        _expect("audit_uncertainty_coverage_review_static_review_authorized", _latest_value(v14_text, "uncertainty_coverage_review_static_review_authorized"), "True"),
        _expect("audit_direct_promotion_recommendation", _latest_value(v14_text, "direct_promotion_recommendation"), "False"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _source_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    return {
        "schema_version": source_review.get("schema_version"),
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "review_check_count": len(_list(source_review.get("review_checks"))),
        "review_item_count": len(_list(source_review.get("uncertainty_coverage_review"))),
        "evidence_gap_count": len(_list(source_review.get("evidence_gap_matrix"))),
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
        "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_passed": bool(passed),
        "uncertainty_coverage_evidence_gap_closure_plan_authorized": bool(passed),
        "direct_promotion_recommendation": False,
        "promotion_decision_plan_authorized_next": False,
        "recommendation": "plan_read_only_uncertainty_coverage_evidence_gap_closure_only",
        "immediate_action": "plan_uncertainty_coverage_evidence_gap_closure_only",
        "score_expression": SCORE_EXPRESSION,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "static_review_enabled" in failed_set:
        return "explicit_uncertainty_coverage_review_static_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "artifact_heads_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_sha") or name.endswith("_root_sha") for name in failed):
        return "source_artifact_sha256_mismatch"
    if any(name.startswith("source_review") for name in failed):
        return "source_uncertainty_coverage_review_contract_failure"
    if any(name.startswith("source_script") or name.startswith("source_test") for name in failed):
        return "source_surface_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "promotion_readiness_uncertainty_coverage_review_static_review_failure"


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


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    matches = [line[len(prefix) :].strip() for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


def _names(value: Any) -> list[str]:
    return [
        str(item.get("name"))
        for item in _list(value)
        if isinstance(item, dict) and item.get("name")
    ]


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


def _stable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    return value


def _compact(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    return text if len(text) <= 160 else text[:157] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
