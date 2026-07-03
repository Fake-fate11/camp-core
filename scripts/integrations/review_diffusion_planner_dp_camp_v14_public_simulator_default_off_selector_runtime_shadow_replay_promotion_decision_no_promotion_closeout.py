#!/usr/bin/env python3
"""Read-only review for the v14 no-promotion closeout record.

This gate consumes the already-recorded no-promotion closeout artifact. It
does not train, replay, generate candidates, modify Diffusion Planner, change
an online selector, promote atoms or selectors, deploy, or make
safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from scripts.integrations.record_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_decision_no_promotion_closeout import (  # noqa: E501
    AUTHORIZED_NEXT_WORK as SOURCE_RECORD_AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    FIXED_DP_HEAD,
    READY_STATUS as SOURCE_RECORD_READY_STATUS,
    SCORE_EXPRESSION,
    SOURCE_AUTHORIZED_NEXT_WORK as SOURCE_RECORD_AUTHORIZED_CURRENT_WORK,
)


SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_decision_no_promotion_closeout_review_v1"
)
SOURCE_RECORD_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_decision_no_promotion_closeout_record_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_no_promotion_closeout_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_no_promotion_closeout_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_closed_no_further_action_"
    "without_new_eof_authorization"
)

RECORD_JSON_NAME = "runtime_no_promotion_closeout_record.json"
RECORD_MD_NAME = "runtime_no_promotion_closeout_record.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closeout_artifact_dir", type=Path, required=True)
    parser.add_argument("--closeout_record_json", type=Path, required=True)
    parser.add_argument("--closeout_record_md", type=Path, required=True)
    parser.add_argument("--closeout_record_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_runtime_no_promotion_closeout_review",
        action="store_true",
        help="Explicit opt-in for read-only no-promotion closeout review.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        closeout_artifact_dir=args.closeout_artifact_dir,
        closeout_record_json=args.closeout_record_json,
        closeout_record_md=args.closeout_record_md,
        closeout_record_sha256s=args.closeout_record_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_runtime_no_promotion_closeout_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    closeout_artifact_dir: Path,
    closeout_record_json: Path,
    closeout_record_md: Path,
    closeout_record_sha256s: Path,
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
    closeout_artifact_dir = closeout_artifact_dir.resolve()
    closeout_record_json = closeout_record_json.resolve()
    closeout_record_md = closeout_record_md.resolve()
    closeout_record_sha256s = closeout_record_sha256s.resolve()
    output_dir = output_dir.resolve()
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    source_record = _read_json_dict(closeout_record_json)
    source_decision = _dict(source_record.get("final_decision"))
    source_analysis = _dict(source_record.get("analysis"))
    source_closeout = _dict(source_record.get("no_promotion_closeout_record"))
    source_blocked = _dict(source_record.get("blocked_actions"))
    source_checks = _list(source_record.get("record_checks"))
    source_heads = _parse_key_values(_read_text(closeout_artifact_dir / "HEADS"))
    source_run_exit = _read_text(closeout_artifact_dir / "run.exit").strip()
    source_record_sha256s = _read_sha256sums(closeout_record_sha256s)
    artifact_sha256s = _read_sha256sums(closeout_artifact_dir / "SHA256SUMS")
    checks = _checks(
        enabled=enabled,
        closeout_artifact_dir=closeout_artifact_dir,
        closeout_record_json=closeout_record_json,
        closeout_record_md=closeout_record_md,
        closeout_record_sha256s=closeout_record_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        source_record=source_record,
        source_decision=source_decision,
        source_analysis=source_analysis,
        source_closeout=source_closeout,
        source_blocked=source_blocked,
        source_checks=source_checks,
        source_heads=source_heads,
        source_run_exit=source_run_exit,
        source_record_sha256s=source_record_sha256s,
        artifact_sha256s=artifact_sha256s,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "review_only": True,
            "closeout_record_json": str(closeout_record_json),
            "closeout_record_md": str(closeout_record_md),
            "closeout_record_sha256s": str(closeout_record_sha256s),
            "closeout_artifact_dir": str(closeout_artifact_dir),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
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
                "This review only checks the no-promotion closeout artifact. "
                "CAMP remains a default-off shadow reranker over fixed DP "
                f"candidate tensors with affine {SCORE_EXPRESSION} over "
                "approved atoms and nonnegative simplex weights."
            ),
        },
        "source_hashes": {
            "closeout_record_json": _sha256(closeout_record_json)
            if closeout_record_json.is_file()
            else None,
            "closeout_record_md": _sha256(closeout_record_md)
            if closeout_record_md.is_file()
            else None,
            "closeout_record_sha256s": _sha256(closeout_record_sha256s)
            if closeout_record_sha256s.is_file()
            else None,
            "artifact_heads": _sha256(closeout_artifact_dir / "HEADS")
            if (closeout_artifact_dir / "HEADS").is_file()
            else None,
            "artifact_command": _sha256(closeout_artifact_dir / "COMMAND")
            if (closeout_artifact_dir / "COMMAND").is_file()
            else None,
            "artifact_stdout": _sha256(closeout_artifact_dir / "stdout.txt")
            if (closeout_artifact_dir / "stdout.txt").is_file()
            else None,
            "artifact_stderr": _sha256(closeout_artifact_dir / "stderr.txt")
            if (closeout_artifact_dir / "stderr.txt").is_file()
            else None,
            "artifact_run_exit": _sha256(closeout_artifact_dir / "run.exit")
            if (closeout_artifact_dir / "run.exit").is_file()
            else None,
            "artifact_sha256s": _sha256(closeout_artifact_dir / "SHA256SUMS")
            if (closeout_artifact_dir / "SHA256SUMS").is_file()
            else None,
            "v14_audit_md": _sha256(v14_audit_md) if v14_audit_md.is_file() else None,
            "current_status_md": _sha256(current_status_md)
            if current_status_md.is_file()
            else None,
        },
        "source_artifact": {
            "heads": source_heads,
            "run_exit": source_run_exit,
            "record_sha256s_entries": sorted(source_record_sha256s.keys()),
            "artifact_sha256s_entries": sorted(artifact_sha256s.keys()),
        },
        "source_summary": {
            "schema_version": source_record.get("schema_version"),
            "status": source_decision.get("status"),
            "passed": source_decision.get("passed"),
            "failed_checks": source_decision.get("failed_checks"),
            "recommendation": source_decision.get("recommendation"),
            "authorized_current_work": source_decision.get("authorized_current_work"),
            "authorized_next_work": source_decision.get("authorized_next_work"),
            "record_decision": source_closeout.get("record_decision"),
            "final_selector_state": source_closeout.get("final_selector_state"),
            "evidence_class": source_closeout.get("evidence_class"),
        },
        "closeout_review": {
            "review_class": "read_only_no_promotion_closeout_review",
            "source_record_passed": source_decision.get("passed") is True,
            "closeout_complete": passed,
            "future_promotion_requires_new_eof_and_explicit_authorization": bool(passed),
            "next_gate_authorization": AUTHORIZED_NEXT_WORK if passed else None,
        },
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_no_promotion_closeout_review.json", report)
    (output_dir / "runtime_no_promotion_closeout_review.md").write_text(
        _render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def _checks(
    *,
    enabled: bool,
    closeout_artifact_dir: Path,
    closeout_record_json: Path,
    closeout_record_md: Path,
    closeout_record_sha256s: Path,
    v14_text: str,
    status_text: str,
    source_record: dict[str, Any],
    source_decision: dict[str, Any],
    source_analysis: dict[str, Any],
    source_closeout: dict[str, Any],
    source_blocked: dict[str, Any],
    source_checks: list[Any],
    source_heads: dict[str, str],
    source_run_exit: str,
    source_record_sha256s: dict[str, str],
    artifact_sha256s: dict[str, str],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = [
        _expect("no_promotion_closeout_review_enabled", enabled, True),
        _expect("current_camp_head_origin_match", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
    ]
    for name, path in [
        ("closeout_record_json", closeout_record_json),
        ("closeout_record_md", closeout_record_md),
        ("closeout_record_sha256s", closeout_record_sha256s),
        ("artifact_heads", closeout_artifact_dir / "HEADS"),
        ("artifact_command", closeout_artifact_dir / "COMMAND"),
        ("artifact_stdout", closeout_artifact_dir / "stdout.txt"),
        ("artifact_run_exit", closeout_artifact_dir / "run.exit"),
        ("artifact_sha256s", closeout_artifact_dir / "SHA256SUMS"),
    ]:
        checks.extend(_file_checks(name, path))
    checks.append(
        _check(
            "artifact_stderr_exists",
            (closeout_artifact_dir / "stderr.txt").is_file(),
            str(closeout_artifact_dir / "stderr.txt"),
            "file",
        )
    )
    checks.extend(
        [
            _expect("artifact_run_exit_zero", source_run_exit, "0"),
            _expect("artifact_head_dp_fixed", source_heads.get("dp_head"), FIXED_DP_HEAD),
            _expect("artifact_head_camp_origin_match", source_heads.get("camp_head"), source_heads.get("camp_origin_main")),
            _check("artifact_head_camp_is_sha", _is_git_sha(source_heads.get("camp_head", "")), source_heads.get("camp_head"), "40-char git sha"),
            _expect("source_analysis_artifact_camp_head", source_analysis.get("current_camp_head"), source_heads.get("camp_head")),
            _expect("source_analysis_artifact_origin", source_analysis.get("current_camp_origin_main"), source_heads.get("camp_origin_main")),
            _expect("source_analysis_dp_fixed", source_analysis.get("current_dp_head"), FIXED_DP_HEAD),
            _expect("record_sha256s_json", source_record_sha256s.get(RECORD_JSON_NAME), _sha256(closeout_record_json) if closeout_record_json.is_file() else None),
            _expect("record_sha256s_md", source_record_sha256s.get(RECORD_MD_NAME), _sha256(closeout_record_md) if closeout_record_md.is_file() else None),
            _expect("artifact_sha256s_json", artifact_sha256s.get(f"./record/{RECORD_JSON_NAME}"), _sha256(closeout_record_json) if closeout_record_json.is_file() else None),
            _expect("artifact_sha256s_md", artifact_sha256s.get(f"./record/{RECORD_MD_NAME}"), _sha256(closeout_record_md) if closeout_record_md.is_file() else None),
            _expect("artifact_sha256s_record_sha256s", artifact_sha256s.get("./record/SHA256SUMS"), _sha256(closeout_record_sha256s) if closeout_record_sha256s.is_file() else None),
            _expect("artifact_sha256s_heads", artifact_sha256s.get("./HEADS"), _sha256(closeout_artifact_dir / "HEADS") if (closeout_artifact_dir / "HEADS").is_file() else None),
            _expect("artifact_sha256s_command", artifact_sha256s.get("./COMMAND"), _sha256(closeout_artifact_dir / "COMMAND") if (closeout_artifact_dir / "COMMAND").is_file() else None),
            _expect("artifact_sha256s_stdout", artifact_sha256s.get("./stdout.txt"), _sha256(closeout_artifact_dir / "stdout.txt") if (closeout_artifact_dir / "stdout.txt").is_file() else None),
            _expect("artifact_sha256s_stderr", artifact_sha256s.get("./stderr.txt"), _sha256(closeout_artifact_dir / "stderr.txt") if (closeout_artifact_dir / "stderr.txt").is_file() else None),
            _expect("artifact_sha256s_run_exit", artifact_sha256s.get("./run.exit"), _sha256(closeout_artifact_dir / "run.exit") if (closeout_artifact_dir / "run.exit").is_file() else None),
        ]
    )
    checks.extend(_source_record_checks(source_record, source_decision, source_analysis, source_closeout, source_blocked, source_checks))
    checks.extend(_audit_checks(v14_text, status_text))
    return checks


def _source_record_checks(
    source_record: dict[str, Any],
    source_decision: dict[str, Any],
    source_analysis: dict[str, Any],
    source_closeout: dict[str, Any],
    source_blocked: dict[str, Any],
    source_checks: list[Any],
) -> list[dict[str, Any]]:
    failed_source_checks = [
        _dict(check).get("name")
        for check in source_checks
        if _dict(check).get("passed") is not True
    ]
    checks = [
        _expect("source_record_schema", source_record.get("schema_version"), SOURCE_RECORD_SCHEMA),
        _expect("source_record_status", source_decision.get("status"), SOURCE_RECORD_READY_STATUS),
        _expect("source_record_passed", source_decision.get("passed"), True),
        _expect("source_record_failed_checks", source_decision.get("failed_checks"), []),
        _expect("source_record_checks_failed", failed_source_checks, []),
        _expect("source_record_authorized_current_work", source_decision.get("authorized_current_work"), SOURCE_RECORD_AUTHORIZED_CURRENT_WORK),
        _expect("source_record_authorized_next_work", source_decision.get("authorized_next_work"), SOURCE_RECORD_AUTHORIZED_NEXT_WORK),
        _expect("source_record_review_authorized", source_decision.get("no_promotion_closeout_review_authorized"), True),
        _expect("source_record_recorded", source_decision.get("no_promotion_closeout_recorded"), True),
        _expect("source_record_promotion_recommended", source_decision.get("promotion_recommended"), False),
        _expect("source_record_recommendation", source_decision.get("recommendation"), "do_not_promote_from_current_evidence_package_alone"),
        _expect("source_record_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_analysis_record_only", source_analysis.get("record_only"), True),
        _expect("source_analysis_training_false", source_analysis.get("training_execution"), False),
        _expect("source_analysis_replay_false", source_analysis.get("replay_execution"), False),
        _expect("source_analysis_candidate_generation_false", source_analysis.get("candidate_generation"), False),
        _expect("source_analysis_dp_modification_false", source_analysis.get("dp_modification"), False),
        _expect("source_analysis_online_selector_false", source_analysis.get("online_selector_change"), False),
        _expect("source_analysis_promotion_executed_false", source_analysis.get("promotion_executed"), False),
        _expect("source_analysis_deployment_executed_false", source_analysis.get("deployment_executed"), False),
        _expect("source_analysis_safety_claim_false", source_analysis.get("safety_or_camp_over_dp_claim"), False),
        _expect("source_closeout_record_decision", source_closeout.get("record_decision"), "close_current_evidence_package_without_promotion"),
        _expect("source_closeout_final_selector_state", source_closeout.get("final_selector_state"), "default_off_shadow_only_not_promoted"),
        _expect("source_closeout_promotion_recommended", source_closeout.get("promotion_recommended"), False),
    ]
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_decision_{name}", source_decision.get(name), False))
        checks.append(_expect(f"source_blocked_{name}", source_blocked.get(name), False))
    for name in [
        "training_executed_by_this_gate",
        "replay_executed_by_this_gate",
        "candidate_generation_executed_by_this_gate",
        "dp_modified_by_this_gate",
        "promotion_executed_by_this_gate",
        "deployment_executed_by_this_gate",
    ]:
        checks.append(_expect(f"source_decision_{name}", source_decision.get(name), False))
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), SOURCE_RECORD_READY_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), SOURCE_RECORD_AUTHORIZED_NEXT_WORK),
        _expect("audit_recorded", _latest_value(v14_text, "default_off_shadow_selector_runtime_no_promotion_closeout_recorded"), "True"),
        _expect("audit_review_authorized", _latest_value(v14_text, "default_off_shadow_selector_runtime_no_promotion_closeout_review_authorized"), "True"),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), SOURCE_RECORD_READY_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), SOURCE_RECORD_AUTHORIZED_NEXT_WORK),
        _check("audit_mentions_review_only", "no-promotion closeout review" in v14_text, True, True),
        _check("status_mentions_review_only", "no-promotion closeout review" in status_text, True, True),
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_RECORD_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "no_promotion_closeout_review_passed": bool(passed),
        "no_promotion_closeout_complete": bool(passed),
        "future_promotion_requires_new_eof_and_explicit_authorization": bool(passed),
        "promotion_recommended": False,
        "recommendation": "keep_default_off_no_promotion_from_current_evidence_package",
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
    if "no_promotion_closeout_review_enabled" in failed_set:
        return "explicit_no_promotion_closeout_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed", "artifact_head_dp_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.startswith("record_sha256s_") or name.startswith("artifact_sha256s_") for name in failed):
        return "source_closeout_hash_mismatch"
    if any(name.startswith("source_record_") or name.startswith("source_closeout_") for name in failed):
        return "source_closeout_record_contract_failure"
    if any(name.startswith("source_analysis_") or name.startswith("source_decision_") or name.startswith("source_blocked_") for name in failed):
        return "boundary_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "no_promotion_closeout_review_failure"


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_summary"]
    lines = [
        "# Runtime No-Promotion Closeout Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized current work: `{decision['authorized_current_work']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- No-promotion closeout complete: `{decision['no_promotion_closeout_complete']}`",
        f"- Future promotion requires new EOF and explicit authorization: `{decision['future_promotion_requires_new_eof_and_explicit_authorization']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP Top-1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Source Closeout Record",
        "",
        f"- Source status: `{source['status']}`",
        f"- Source passed: `{source['passed']}`",
        f"- Source recommendation: `{source['recommendation']}`",
        f"- Record decision: `{source['record_decision']}`",
        f"- Final selector state: `{source['final_selector_state']}`",
        f"- Evidence class: `{source['evidence_class']}`",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "This review is read-only. It does not train, replay, generate "
        "candidates, modify DP, change an online selector, promote atoms or "
        "selectors, deploy, or authorize safety/CAMP-over-DP claims.",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check.get('observed'))}` | `{_compact(check.get('expected'))}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _file_checks(name: str, path: Path) -> list[dict[str, Any]]:
    return [
        _check(f"{name}_exists", path.is_file(), str(path), "file"),
        _check(
            f"{name}_nonempty",
            path.is_file() and path.stat().st_size > 0,
            path.stat().st_size if path.is_file() else None,
            ">0 bytes",
        ),
    ]


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


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


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _read_sha256sums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            values[parts[1].strip()] = parts[0]
            values[Path(parts[1].strip()).name] = parts[0]
    return values


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    values = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    return values[-1] if values else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


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
    text = json.dumps(_stable(value), sort_keys=True)
    return text if len(text) <= 140 else text[:137] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
