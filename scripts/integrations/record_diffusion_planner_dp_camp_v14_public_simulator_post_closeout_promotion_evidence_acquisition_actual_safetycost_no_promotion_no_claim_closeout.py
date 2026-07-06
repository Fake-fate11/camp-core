#!/usr/bin/env python3
"""Record no-promotion/no-claim closeout for actual SafetyCost evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_result_review_module():
    script_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_actual_safetycost_outcome_materialization_execution_result.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_result_review",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RESULT_REVIEW_MODULE = _load_result_review_module()

FIXED_DP_HEAD = RESULT_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = RESULT_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = RESULT_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = RESULT_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = RESULT_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = RESULT_REVIEW_MODULE.REVIEW_MD_NAME
AUTHORIZED_CURRENT_WORK = RESULT_REVIEW_MODULE.NO_PROMOTION_CLOSEOUT_WORK

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "actual_safetycost_no_promotion_no_claim_closeout_record_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_no_promotion_no_claim_closeout_recorded"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_no_promotion_no_claim_closeout_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "no_further_action_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "actual_safetycost_evidence_does_not_support_promotion_or_claim"
)

RECORD_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_no_promotion_no_claim_closeout_record.json"
)
RECORD_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_paired_evaluation_"
    "actual_safetycost_no_promotion_no_claim_closeout_record.md"
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
FALSE_EXECUTION_FLAGS = (
    "training_executed_by_this_gate",
    "replay_executed_by_this_gate",
    "candidate_generation_executed_by_this_gate",
    "dp_modified_by_this_gate",
    "promotion_executed_by_this_gate",
    "deployment_executed_by_this_gate",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_md", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_no_promotion_no_claim_closeout_record",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_md=args.source_result_review_md,
        source_result_review_sha256s=args.source_result_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_no_promotion_no_claim_closeout_record
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    source_result_review_artifact_dir = source_result_review_artifact_dir.resolve()
    source_result_review_json = source_result_review_json.resolve()
    source_result_review_md = source_result_review_md.resolve()
    source_result_review_sha256s = source_result_review_sha256s.resolve()
    output_dir = output_dir.resolve()

    source_review = _read_json_dict(source_result_review_json)
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    heads = _parse_key_values(_read_text(source_result_review_artifact_dir / "HEADS"))
    run_exit = _read_text(source_result_review_artifact_dir / "run.exit").strip()
    root_sha256s = _read_sha256sums(source_result_review_artifact_dir / "SHA256SUMS")
    nested_sha256s = _read_sha256sums(source_result_review_sha256s)
    checks = _checks(
        enabled=enabled,
        source_result_review_artifact_dir=source_result_review_artifact_dir,
        source_result_review_json=source_result_review_json,
        source_result_review_md=source_result_review_md,
        source_result_review_sha256s=source_result_review_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
        source_review=source_review,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    passed = all(check["passed"] for check in checks)
    decision = _decision(passed=passed, checks=checks, source_review=source_review)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "closeout_record_only": True,
            "actual_safetycost_outcome_materialization_executed_by_closeout": False,
            "result_review_executed_by_closeout": False,
            "replay_executed_by_closeout": False,
            "training_executed_by_closeout": False,
            "candidate_generation_executed_by_closeout": False,
            "dp_modified_by_closeout": False,
            "promotion_executed_by_closeout": False,
            "deployment_executed_by_closeout": False,
            "online_selector_change_by_closeout": False,
            "safety_or_camp_over_dp_claim_by_closeout": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_result_review_artifact_dir": str(source_result_review_artifact_dir),
            "source_result_review_json": str(source_result_review_json),
            "source_result_review_md": str(source_result_review_md),
            "source_result_review_sha256s": str(source_result_review_sha256s),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "source_artifact_hashes": _source_hashes(
            source_result_review_artifact_dir=source_result_review_artifact_dir,
            source_result_review_json=source_result_review_json,
            source_result_review_md=source_result_review_md,
            source_result_review_sha256s=source_result_review_sha256s,
        ),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": _kv(heads, "CAMP_HEAD", "camp_head"),
            "source_artifact_camp_origin_main": _kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
            "source_artifact_dp_head": _kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_result_review_summary": _source_result_review_summary(source_review),
        "closeout_summary": _closeout_summary(source_review),
        "closeout_checks": checks,
        "final_decision": decision,
    }


def _checks(
    *,
    enabled: bool,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    source_review: dict[str, Any],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = _dict(source_review.get("final_decision"))
    claim = _dict(source_review.get("actual_safetycost_claim_rule_summary"))

    def expect(name: str, actual: Any, expected: Any) -> None:
        checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})

    def require(name: str, passed: bool, actual: Any = None, expected: Any = True) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "actual": actual if actual is not None else bool(passed),
                "expected": expected,
            }
        )

    latest_audit_status = _latest_value(v14_text, "current_v14_status")
    latest_audit_next = _latest_value(v14_text, "next_work_target")
    latest_status_doc_status = _latest_value(status_text, "current_v14_status")
    latest_status_doc_next = _latest_value(status_text, "next_work_target")

    require("closeout_record_enabled", enabled)
    require("source_result_review_artifact_dir_exists", source_result_review_artifact_dir.is_dir())
    require("source_result_review_json_exists", source_result_review_json.is_file())
    require("source_result_review_md_exists", source_result_review_md.is_file())
    require("source_result_review_sha256s_exists", source_result_review_sha256s.is_file())
    require("source_result_review_heads_exists", (source_result_review_artifact_dir / "HEADS").is_file())
    require("source_result_review_command_exists", (source_result_review_artifact_dir / "COMMAND").is_file())
    require("source_result_review_stdout_exists", (source_result_review_artifact_dir / "stdout").is_file())
    require("source_result_review_stderr_exists", (source_result_review_artifact_dir / "stderr").is_file())
    require("source_result_review_run_exit_exists", (source_result_review_artifact_dir / "run.exit").is_file())
    require("source_result_review_root_sha256s_exists", (source_result_review_artifact_dir / "SHA256SUMS").is_file())

    expect("current_dp_head_fixed", current_dp_head, required_dp_head)
    expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main)
    expect("source_artifact_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head)
    expect("source_result_review_run_exit", run_exit, "0")
    expect("audit_latest_status", latest_audit_status, SOURCE_REVIEW_STATUS)
    expect("audit_latest_next_work", latest_audit_next, AUTHORIZED_CURRENT_WORK)
    expect("status_doc_latest_status", latest_status_doc_status, SOURCE_REVIEW_STATUS)
    expect("status_doc_latest_next_work", latest_status_doc_next, AUTHORIZED_CURRENT_WORK)

    expect("source_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA)
    expect("source_review_passed", decision.get("passed"), True)
    expect("source_review_status", decision.get("status"), SOURCE_REVIEW_STATUS)
    expect("source_review_failed_checks", decision.get("failed_checks"), [])
    expect("source_review_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK)
    expect("source_review_no_promotion_closeout_recommended", decision.get("no_promotion_closeout_recommended"), True)
    expect("source_review_safety_benefit_claim_supported", decision.get("safety_benefit_claim_supported"), False)
    expect("source_review_camp_over_dp_top1_claim_supported", decision.get("camp_over_dp_top1_claim_supported"), False)
    expect("source_review_safety_benefit_claim_authorized", decision.get("safety_benefit_claim_authorized"), False)
    expect("source_review_camp_over_dp_top1_claim_authorized", decision.get("camp_over_dp_top1_claim_authorized"), False)
    expect("source_review_delta_mean_positive", isinstance(claim.get("delta_mean"), (int, float)) and claim.get("delta_mean") > 0.0, True)
    expect("source_review_worse_records_exceed_better", int(claim.get("worse_records") or 0) > int(claim.get("better_records") or 0), True)
    expect("source_review_no_go_failed_count", claim.get("no_go_failed_count"), 0)
    for action in BLOCKED_ACTIONS:
        expect(f"source_review_decision_{action}", decision.get(action), False)
    for flag in FALSE_EXECUTION_FLAGS:
        expect(f"source_review_decision_{flag}", decision.get(flag), False)

    _expect_sha(checks, "nested_review_json_sha", nested_sha256s, [source_result_review_json.name], source_result_review_json)
    _expect_sha(checks, "nested_review_md_sha", nested_sha256s, [source_result_review_md.name], source_result_review_md)
    _expect_sha(
        checks,
        "root_review_json_sha",
        root_sha256s,
        [f"./review/{source_result_review_json.name}", f"review/{source_result_review_json.name}"],
        source_result_review_json,
    )
    _expect_sha(
        checks,
        "root_review_md_sha",
        root_sha256s,
        [f"./review/{source_result_review_md.name}", f"review/{source_result_review_md.name}"],
        source_result_review_md,
    )
    _expect_sha(
        checks,
        "root_review_sha256s_sha",
        root_sha256s,
        ["./review/SHA256SUMS", "review/SHA256SUMS"],
        source_result_review_sha256s,
    )
    return checks


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_review: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "closeout_record_enabled" in failed:
        failure_class = "explicit_actual_safetycost_no_promotion_closeout_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_review_") for name in failed):
        failure_class = "source_actual_safetycost_result_review_contract_failure"
    else:
        failure_class = "artifact_hash_or_closeout_contract_failure"
    source_decision = _dict(source_review.get("final_decision"))
    claim = _dict(source_review.get("actual_safetycost_claim_rule_summary"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_evidence_acquisition_actual_safetycost_no_promotion_no_claim_closeout_recorded": bool(passed),
        "actual_safetycost_result_review_passed": source_decision.get("passed"),
        "actual_safetycost_delta_mean": claim.get("delta_mean"),
        "actual_safetycost_delta_ci95_low": claim.get("delta_ci95_low"),
        "actual_safetycost_delta_ci95_high": claim.get("delta_ci95_high"),
        "actual_safetycost_better_records": claim.get("better_records"),
        "actual_safetycost_worse_records": claim.get("worse_records"),
        "safety_benefit_claim_supported": False,
        "camp_over_dp_top1_claim_supported": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "no_further_action_recommended": bool(passed),
        "direct_promotion_recommendation": False,
        "recommendation": "stop_no_promotion_no_claim_actual_safetycost_closeout" if passed else "repair_or_rerun_same_closeout_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def _source_result_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    source = _dict(source_review.get("source_execution_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "runtime_record_count": source.get("runtime_record_count"),
        "top1_summary_count": source.get("top1_summary_count"),
        "shadow_summary_count": source.get("shadow_summary_count"),
        "delta_count": source.get("delta_count"),
        "delta_mean": source.get("delta_mean"),
        "better_records": source.get("better_records"),
        "worse_records": source.get("worse_records"),
        "safety_benefit_claim_supported": decision.get("safety_benefit_claim_supported"),
        "camp_over_dp_top1_claim_supported": decision.get("camp_over_dp_top1_claim_supported"),
    }


def _closeout_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    claim = _dict(source_review.get("actual_safetycost_claim_rule_summary"))
    return {
        "closeout_reason": "actual_safetycost_shadow_selected_not_better_than_dp_top1",
        "claim_rule": claim.get("claim_rule"),
        "delta_mean": claim.get("delta_mean"),
        "delta_ci95_low": claim.get("delta_ci95_low"),
        "delta_ci95_high": claim.get("delta_ci95_high"),
        "better_records": claim.get("better_records"),
        "worse_records": claim.get("worse_records"),
        "no_promotion_no_claim": True,
    }


def _source_hashes(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
) -> dict[str, Any]:
    root_sha = source_result_review_artifact_dir / "SHA256SUMS"
    return {
        "source_result_review_json_sha256": _sha256_if_file(source_result_review_json),
        "source_result_review_md_sha256": _sha256_if_file(source_result_review_md),
        "source_result_review_sha256s_sha256": _sha256_if_file(source_result_review_sha256s),
        "source_result_review_root_sha256s_sha256": _sha256_if_file(root_sha),
        "heads_sha256": _sha256_if_file(source_result_review_artifact_dir / "HEADS"),
        "command_sha256": _sha256_if_file(source_result_review_artifact_dir / "COMMAND"),
        "stdout_sha256": _sha256_if_file(source_result_review_artifact_dir / "stdout"),
        "stderr_sha256": _sha256_if_file(source_result_review_artifact_dir / "stderr"),
        "run_exit_sha256": _sha256_if_file(source_result_review_artifact_dir / "run.exit"),
    }


def _expect_sha(
    checks: list[dict[str, Any]],
    name: str,
    sums: dict[str, str],
    keys: list[str],
    path: Path,
) -> None:
    actual = next((sums[key] for key in keys if key in sums), None)
    expected = _sha256_if_file(path)
    checks.append({"name": name, "passed": actual == expected, "actual": actual, "expected": expected})


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / RECORD_JSON_NAME
    md_path = output_dir / RECORD_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{_sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    closeout = report["closeout_summary"]
    lines = [
        "# v14 Actual SafetyCost No-Promotion/No-Claim Closeout",
        "",
        f"- Passed: `{decision['passed']}`",
        f"- Status: `{decision['status']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Closeout",
        "",
        f"- Reason: `{closeout['closeout_reason']}`",
        f"- Delta mean: `{closeout['delta_mean']}`",
        f"- Delta CI95: `[{closeout['delta_ci95_low']}, {closeout['delta_ci95_high']}]`",
        f"- Better / worse records: `{closeout['better_records']} / {closeout['worse_records']}`",
        f"- No promotion/no claim: `{closeout['no_promotion_no_claim']}`",
        "",
        "## Boundary",
        "",
        "- Closeout only: no replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
        f"- Score expression: `{report['analysis']['score_expression']}`",
    ]
    return "\n".join(lines) + "\n"


def _read_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_sha256sums(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    sums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if digest and name:
            sums[name.strip()] = digest.strip()
    return sums


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip()
    return values


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0]


def _kv(values: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in values:
            return values[key]
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_if_file(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
