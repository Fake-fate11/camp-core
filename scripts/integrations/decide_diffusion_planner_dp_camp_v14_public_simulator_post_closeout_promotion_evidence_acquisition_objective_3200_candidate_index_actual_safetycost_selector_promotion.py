#!/usr/bin/env python3
"""Audited selector promotion decision for objective-3200 SafetyCost evidence."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    review_path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_candidate_index_"
        "actual_safetycost_selector_promotion_decision_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_selector_promotion_decision_plan_static_review",
        review_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
BASE_MODULE = SOURCE_REVIEW_MODULE.BASE_MODULE

FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = SOURCE_REVIEW_MODULE.SCORE_EXPRESSION
SOURCE_REVIEW_SCHEMA = SOURCE_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = SOURCE_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = SOURCE_REVIEW_MODULE.REVIEW_MD_NAME
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_candidate_index_actual_safetycost_selector_promotion_decision_v1"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_selector_promotion_decision_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_selector_promotion_decision_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_deployment_decision_plan_only"
)
DECISION_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_selector_promotion_decision.json"
)
DECISION_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "candidate_index_actual_safetycost_selector_promotion_decision.md"
)
EXPECTED_SOURCE_REVIEW_CHECK_COUNT = 86


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_selector_promotion_decision",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_selector_promotion_decision
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(BASE_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = source_static_review_artifact_dir.resolve()
    paths = {
        "source_static_review_json": source_static_review_json.resolve(),
        "source_static_review_md": source_static_review_md.resolve(),
        "source_static_review_sha256s": source_static_review_sha256s.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    files = _artifact_files(artifact_dir)
    source_review = BASE_MODULE._read_json_dict(paths["source_static_review_json"])
    heads = BASE_MODULE._parse_key_values(BASE_MODULE._read_text(files["heads"]))
    root_sha256s = BASE_MODULE._read_sha256sums(files["root_sha256s"])
    nested_sha256s = BASE_MODULE._read_sha256sums(paths["source_static_review_sha256s"])
    v14_text = BASE_MODULE._read_text(paths["v14_audit_md"])
    status_text = BASE_MODULE._read_text(paths["current_status_md"])
    promotion_record = _promotion_record(source_review)
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        files=files,
        source_review=source_review,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        promotion_record=promotion_record,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "selector_promotion_decision_gate": True,
            "selector_promotion_execution": False,
            "deployment_execution": False,
            "online_selector_change": False,
            "claim_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "source_static_review_artifact_dir": str(artifact_dir),
            **{name: str(path) for name, path in paths.items()},
            "output_dir": str(output_dir.resolve()),
        },
        "source_hashes": {
            name: BASE_MODULE._sha256(path) if path.is_file() else None
            for name, path in {**paths, **files}.items()
        },
        "source_static_review_summary": _source_static_review_summary(source_review),
        "selector_promotion_record": promotion_record,
        "decision_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_review=source_review),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / DECISION_JSON_NAME
    md_path = output_dir / DECISION_MD_NAME
    json_path.write_text(json.dumps(BASE_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "\n".join(f"{BASE_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)) + "\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failed = decision["failed_checks"] or ["none"]
    record = report["selector_promotion_record"]
    return "\n".join(
        [
            "# Objective-3200 Candidate-Index Actual-SafetyCost Selector Promotion Decision",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failure class: `{decision['failure_class']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Failed checks: `{', '.join(failed)}`",
            f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
            f"- Deployment authorized: `{decision['deployment_authorized']}`",
            f"- Online selector change authorized: `{decision['online_selector_change_authorized']}`",
            "",
            "## Promotion Decision",
            "",
            record["decision_text"],
            "",
            record["scope_limit"],
            "",
        ]
    )


def _artifact_files(artifact_dir: Path) -> dict[str, Path]:
    return {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "review_json": artifact_dir / "review" / SOURCE_REVIEW_JSON_NAME,
        "review_md": artifact_dir / "review" / SOURCE_REVIEW_MD_NAME,
        "review_sha256s": artifact_dir / "review" / "SHA256SUMS",
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    files: dict[str, Path],
    source_review: dict[str, Any],
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    promotion_record: dict[str, Any],
) -> list[dict[str, Any]]:
    decision = BASE_MODULE._dict(source_review.get("final_decision"))
    checks = [
        BASE_MODULE._expect("selector_promotion_decision_enabled", enabled, True),
        BASE_MODULE._check("source_static_review_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        BASE_MODULE._expect("source_static_review_json_path_matches_artifact", paths["source_static_review_json"], files["review_json"]),
        BASE_MODULE._expect("source_static_review_md_path_matches_artifact", paths["source_static_review_md"], files["review_md"]),
        BASE_MODULE._expect("source_static_review_sha256s_path_matches_artifact", paths["source_static_review_sha256s"], files["review_sha256s"]),
        BASE_MODULE._expect("audit_latest_status", BASE_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("audit_latest_next_work", BASE_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("status_doc_latest_status", BASE_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("status_doc_latest_next_work", BASE_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("audit_selector_promotion_decision_authorized", BASE_MODULE._latest_value(v14_text, "objective_3200_candidate_index_actual_safetycost_selector_promotion_decision_authorized"), "True"),
        BASE_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        BASE_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        BASE_MODULE._expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        BASE_MODULE._expect("source_artifact_dp_head_fixed", BASE_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        BASE_MODULE._expect("source_artifact_camp_head_matches_origin", BASE_MODULE._kv(heads, "CAMP_HEAD", "camp_head"), BASE_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main")),
        BASE_MODULE._expect("source_static_review_run_exit", BASE_MODULE._read_text(files["run_exit"]).strip(), "0"),
        BASE_MODULE._expect("source_static_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        BASE_MODULE._expect("source_static_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        BASE_MODULE._expect("source_static_review_passed", decision.get("passed"), True),
        BASE_MODULE._expect("source_static_review_failure_class", decision.get("failure_class"), None),
        BASE_MODULE._expect("source_static_review_failed_checks", decision.get("failed_checks"), []),
        BASE_MODULE._expect("source_static_review_check_count", decision.get("check_count"), EXPECTED_SOURCE_REVIEW_CHECK_COUNT),
        BASE_MODULE._expect("source_static_review_failed_check_count", decision.get("failed_check_count"), 0),
        BASE_MODULE._expect("source_static_review_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        BASE_MODULE._expect("source_selector_promotion_decision_authorized", decision.get("objective_3200_candidate_index_actual_safetycost_selector_promotion_decision_authorized"), True),
        BASE_MODULE._expect("source_claim_executed_false", decision.get("claim_executed_by_this_gate"), False),
        BASE_MODULE._expect("source_safety_claim_true", decision.get("safety_benefit_claim_authorized"), True),
        BASE_MODULE._expect("source_camp_claim_true", decision.get("camp_over_dp_top1_claim_authorized"), True),
        BASE_MODULE._expect("source_selector_promotion_false", decision.get("selector_promotion_authorized"), False),
        BASE_MODULE._expect("source_deployment_false", decision.get("deployment_authorized"), False),
        BASE_MODULE._expect("source_online_selector_false", decision.get("online_selector_change_authorized"), False),
        BASE_MODULE._expect("promotion_record_authorizes_selector", promotion_record.get("selector_promotion_authorized"), True),
        BASE_MODULE._expect("promotion_record_deployment_false", promotion_record.get("deployment_authorized"), False),
        BASE_MODULE._expect("promotion_record_online_false", promotion_record.get("online_selector_change_authorized"), False),
        BASE_MODULE._check("promotion_scope_mentions_default_off", "default-off" in promotion_record.get("scope_limit", ""), promotion_record.get("scope_limit"), "default-off"),
    ]
    for name, path in paths.items():
        checks.extend(BASE_MODULE._path_checks(name, path, allow_empty=False))
    for name, path in files.items():
        checks.extend(BASE_MODULE._path_checks(f"source_artifact_{name}", path, allow_empty=name == "stderr"))
    checks.extend(_sha_checks(root_sha256s=root_sha256s, nested_sha256s=nested_sha256s, files=files))
    return checks


def _sha_checks(
    *,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    files: dict[str, Path],
) -> list[dict[str, Any]]:
    return [
        BASE_MODULE._expect("root_heads_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "HEADS"), BASE_MODULE._sha256(files["heads"])),
        BASE_MODULE._expect("root_command_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "COMMAND"), BASE_MODULE._sha256(files["command"])),
        BASE_MODULE._expect("root_stdout_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "stdout"), BASE_MODULE._sha256(files["stdout"])),
        BASE_MODULE._expect("root_stderr_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "stderr"), BASE_MODULE._sha256(files["stderr"])),
        BASE_MODULE._expect("root_run_exit_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "run.exit"), BASE_MODULE._sha256(files["run_exit"])),
        BASE_MODULE._expect("root_review_json_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"review/{SOURCE_REVIEW_JSON_NAME}"), BASE_MODULE._sha256(files["review_json"])),
        BASE_MODULE._expect("root_review_md_sha", BASE_MODULE._sha_for_suffix(root_sha256s, f"review/{SOURCE_REVIEW_MD_NAME}"), BASE_MODULE._sha256(files["review_md"])),
        BASE_MODULE._expect("root_review_sha256s_sha", BASE_MODULE._sha_for_suffix(root_sha256s, "review/SHA256SUMS"), BASE_MODULE._sha256(files["review_sha256s"])),
        BASE_MODULE._expect("nested_review_json_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_REVIEW_JSON_NAME), BASE_MODULE._sha256(files["review_json"])),
        BASE_MODULE._expect("nested_review_md_sha", BASE_MODULE._sha_for_suffix(nested_sha256s, SOURCE_REVIEW_MD_NAME), BASE_MODULE._sha256(files["review_md"])),
    ]


def _promotion_record(source_review: dict[str, Any]) -> dict[str, Any]:
    source_decision = BASE_MODULE._dict(source_review.get("final_decision"))
    return {
        "decision_text": "Authorize default-off CAMP selector promotion for the audited objective-3200 fixed-DP candidate-tensor evidence package.",
        "scope_limit": "This selector promotion is default-off and limited to fixed Diffusion Planner candidate tensors; it is not deployment, online selector activation, trajectory generation, or DP modification.",
        "source_static_review_status": source_decision.get("status"),
        "selector_promotion_authorized": True,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": source_decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": source_decision.get("camp_over_dp_top1_claim_authorized"),
    }


def _source_static_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = BASE_MODULE._dict(source_review.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "check_count": decision.get("check_count"),
        "failed_check_count": decision.get("failed_check_count"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "selector_promotion_decision_authorized": decision.get("objective_3200_candidate_index_actual_safetycost_selector_promotion_decision_authorized"),
    }


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_review: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    source_decision = BASE_MODULE._dict(source_review.get("final_decision"))
    if passed:
        failure_class = None
    elif "selector_promotion_decision_enabled" in failed:
        failure_class = "explicit_candidate_index_actual_safetycost_selector_promotion_decision_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_drift"
    elif any("sha" in name for name in failed):
        failure_class = "source_artifact_hash_mismatch"
    elif any(name.startswith("source_") for name in failed):
        failure_class = "source_selector_promotion_plan_static_review_contract_failure"
    else:
        failure_class = "selector_promotion_decision_contract_failure"
    return {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(checks),
        "failed_check_count": len(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_candidate_index_actual_safetycost_selector_promotion_decision_passed": bool(passed),
        "objective_3200_candidate_index_actual_safetycost_deployment_decision_plan_authorized": bool(passed),
        "source_static_review_passed": source_decision.get("passed"),
        "claim_executed_by_this_gate": False,
        "selector_promotion_authorized": bool(passed),
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": source_decision.get("safety_benefit_claim_authorized"),
        "camp_over_dp_top1_claim_authorized": source_decision.get("camp_over_dp_top1_claim_authorized"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
