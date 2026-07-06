#!/usr/bin/env python3
"""Static review for the objective-3200 outcome continuation plan."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_plan_module():
    plan_path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_outcome_continuation.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_continuation_plan",
        plan_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()

FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PLAN_MODULE.SCORE_EXPRESSION
SOURCE_PLAN_SCHEMA = PLAN_MODULE.SCHEMA_VERSION
SOURCE_PLAN_STATUS = PLAN_MODULE.READY_STATUS
SOURCE_PLAN_JSON_NAME = PLAN_MODULE.PLAN_JSON_NAME
SOURCE_PLAN_MD_NAME = PLAN_MODULE.PLAN_MD_NAME
BLOCKED_ACTIONS = PLAN_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = PLAN_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_outcome_source_inventory_preflight_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_source_inventory_preflight_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_source_inventory_preflight_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_source_inventory_preflight_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_source_inventory_preflight_static_review.md"
)

EXPECTED_PREFLIGHT_STEPS = (
    "inventory_existing_shadow_selected_outputs",
    "inventory_runtime_selection_logs",
    "validate_fixed_candidate_identity_per_record",
    "define_per_record_outcome_source_contract",
    "fail_closed_if_only_run_level_summaries_exist",
    "authorize_next_static_review_only",
)
EXPECTED_NO_GO = (
    "dp_head_drift",
    "camp_generates_repairs_rewrites_or_blends_trajectory",
    "candidate_tensor_not_fixed_dp_source",
    "per_record_outcome_source_missing",
    "closed_loop_outcome_used_for_training_or_online_input",
    "full36_or_formal_seed_11_12_13_present",
    "non_affine_score_or_nonconvex_master",
    "promotion_deployment_online_selector_or_claim",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objective_3200_outcome_continuation_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--objective_3200_outcome_continuation_plan_json", type=Path, required=True)
    parser.add_argument("--objective_3200_outcome_continuation_plan_md", type=Path, required=True)
    parser.add_argument("--objective_3200_outcome_continuation_plan_sha256s", type=Path, required=True)
    parser.add_argument("--continuation_plan_script_py", type=Path, required=True)
    parser.add_argument("--continuation_plan_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        objective_3200_outcome_continuation_plan_artifact_dir=(
            args.objective_3200_outcome_continuation_plan_artifact_dir
        ),
        objective_3200_outcome_continuation_plan_json=(
            args.objective_3200_outcome_continuation_plan_json
        ),
        objective_3200_outcome_continuation_plan_md=(
            args.objective_3200_outcome_continuation_plan_md
        ),
        objective_3200_outcome_continuation_plan_sha256s=(
            args.objective_3200_outcome_continuation_plan_sha256s
        ),
        continuation_plan_script_py=args.continuation_plan_script_py,
        continuation_plan_test_py=args.continuation_plan_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=(
            args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_source_inventory_preflight_static_review
        ),
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PLAN_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    objective_3200_outcome_continuation_plan_artifact_dir: Path,
    objective_3200_outcome_continuation_plan_json: Path,
    objective_3200_outcome_continuation_plan_md: Path,
    objective_3200_outcome_continuation_plan_sha256s: Path,
    continuation_plan_script_py: Path,
    continuation_plan_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = objective_3200_outcome_continuation_plan_artifact_dir.resolve()
    paths = {
        "plan_json": objective_3200_outcome_continuation_plan_json.resolve(),
        "plan_md": objective_3200_outcome_continuation_plan_md.resolve(),
        "plan_sha256s": objective_3200_outcome_continuation_plan_sha256s.resolve(),
        "plan_script_py": continuation_plan_script_py.resolve(),
        "plan_test_py": continuation_plan_test_py.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
        "output_dir": output_dir.resolve(),
    }
    artifact_files = {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "plan_json": artifact_dir / "plan" / SOURCE_PLAN_JSON_NAME,
        "plan_md": artifact_dir / "plan" / SOURCE_PLAN_MD_NAME,
        "plan_sha256s": artifact_dir / "plan" / "SHA256SUMS",
    }

    source_plan = PLAN_MODULE._read_json_dict(paths["plan_json"])
    v14_text = PLAN_MODULE._read_text(paths["v14_audit_md"])
    status_text = PLAN_MODULE._read_text(paths["current_status_md"])
    heads = PLAN_MODULE._parse_key_values(PLAN_MODULE._read_text(artifact_files["heads"]))
    run_exit = PLAN_MODULE._read_text(artifact_files["run_exit"]).strip()
    root_sha256s = _read_sha256sums(artifact_files["root_sha256s"])
    nested_sha256s = _read_sha256sums(paths["plan_sha256s"])
    script_text = PLAN_MODULE._read_text(paths["plan_script_py"])
    test_text = PLAN_MODULE._read_text(paths["plan_test_py"])

    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        artifact_files=artifact_files,
        source_plan=source_plan,
        v14_text=v14_text,
        status_text=status_text,
        heads=heads,
        run_exit=run_exit,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        script_text=script_text,
        test_text=test_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "objective_3200_source_inventory_preflight_static_review_only": True,
            "source_inventory_preflight_executed": False,
            "actual_safetycost_outcome_materialization_executed": False,
            "replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "objective_3200_outcome_continuation_plan_artifact_dir": str(artifact_dir),
            **{name: str(path) for name, path in paths.items()},
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_artifact_camp_head": heads.get("CAMP_HEAD"),
            "source_artifact_camp_origin_main": heads.get("CAMP_ORIGIN_MAIN"),
            "source_artifact_dp_head": PLAN_MODULE._kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_artifact_hashes": {
            name: PLAN_MODULE._sha256(path)
            for name, path in artifact_files.items()
            if path.is_file()
        },
        "source_plan_summary": _source_plan_summary(source_plan),
        "objective_gap_summary": source_plan.get("objective_gap_summary", {}),
        "static_review_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_plan=source_plan),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    artifact_files: dict[str, Path],
    source_plan: dict[str, Any],
    v14_text: str,
    status_text: str,
    heads: dict[str, str],
    run_exit: str,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    script_text: str,
    test_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    decision = _dict(source_plan.get("final_decision"))
    analysis = _dict(source_plan.get("analysis"))
    gap = _dict(source_plan.get("objective_gap_summary"))

    checks.extend(
        [
            _expect("static_review_enabled", enabled, True),
            _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
            _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
            _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
            _expect("audit_latest_status", PLAN_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PLAN_STATUS),
            _expect("audit_latest_next_work", PLAN_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
            _expect("status_doc_latest_status", PLAN_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PLAN_STATUS),
            _expect("status_doc_latest_next_work", PLAN_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
            _check("source_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
        ]
    )
    for name, path in paths.items():
        if name == "output_dir":
            continue
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "file"))
    for name, path in artifact_files.items():
        allow_empty = name == "stderr"
        checks.append(
            _check(
                f"artifact_{name}_exists",
                path.is_file() and (allow_empty or path.stat().st_size >= 0),
                str(path),
                "file",
            )
        )

    checks.extend(
        [
            _expect("plan_json_matches_artifact_layout", paths["plan_json"], artifact_files["plan_json"]),
            _expect("plan_md_matches_artifact_layout", paths["plan_md"], artifact_files["plan_md"]),
            _expect("plan_sha256s_matches_artifact_layout", paths["plan_sha256s"], artifact_files["plan_sha256s"]),
            _expect("source_run_exit_zero", run_exit, "0"),
            _expect("source_artifact_dp_head_fixed", PLAN_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        ]
    )
    checks.extend(_artifact_hash_checks(artifact_files, root_sha256s, nested_sha256s))
    checks.extend(_source_plan_contract_checks(source_plan, decision, analysis, gap))
    checks.extend(_source_surface_checks(script_text, test_text))
    return checks


def _artifact_hash_checks(
    artifact_files: dict[str, Path],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    root_names = {
        "heads": "HEADS",
        "command": "COMMAND",
        "stdout": "stdout",
        "stderr": "stderr",
        "run_exit": "run.exit",
        "plan_json": f"plan/{SOURCE_PLAN_JSON_NAME}",
        "plan_md": f"plan/{SOURCE_PLAN_MD_NAME}",
        "plan_sha256s": "plan/SHA256SUMS",
    }
    for key, root_name in root_names.items():
        path = artifact_files[key]
        checks.append(
            _expect(
                f"root_{key}_sha",
                _sha_from_sums(root_sha256s, root_name, path.name, str(path)),
                PLAN_MODULE._sha256(path),
            )
        )
    checks.extend(
        [
            _expect(
                "nested_plan_json_sha",
                _sha_from_sums(nested_sha256s, SOURCE_PLAN_JSON_NAME, str(artifact_files["plan_json"])),
                PLAN_MODULE._sha256(artifact_files["plan_json"]),
            ),
            _expect(
                "nested_plan_md_sha",
                _sha_from_sums(nested_sha256s, SOURCE_PLAN_MD_NAME, str(artifact_files["plan_md"])),
                PLAN_MODULE._sha256(artifact_files["plan_md"]),
            ),
        ]
    )
    return checks


def _source_plan_contract_checks(
    source_plan: dict[str, Any],
    decision: dict[str, Any],
    analysis: dict[str, Any],
    gap: dict[str, Any],
) -> list[dict[str, Any]]:
    preflight_steps = [
        _dict(item).get("step")
        for item in source_plan.get("preflight_plan", [])
    ]
    no_go = source_plan.get("no_go_register", [])
    artifact_contract = _dict(source_plan.get("artifact_contract"))
    checks = [
        _expect("source_plan_schema", source_plan.get("schema_version"), SOURCE_PLAN_SCHEMA),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_status", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_failed_checks", decision.get("failed_checks"), []),
        _expect("source_plan_authorized_next_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_plan_continuation_ready", decision.get("objective_3200_outcome_continuation_plan_ready"), True),
        _expect("source_plan_static_review_authorized", decision.get("objective_3200_outcome_source_inventory_static_review_authorized"), True),
        _expect("source_plan_plan_only", analysis.get("plan_only"), True),
        _expect("source_plan_preflight_only", analysis.get("preflight_only"), True),
        _expect("source_plan_read_only", analysis.get("read_only"), True),
        _expect("source_plan_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
        _expect("objective_required_records", gap.get("objective_required_records"), PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS),
        _expect("runtime_record_count", gap.get("runtime_record_count"), PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS),
        _expect("runtime_selection_log_count", gap.get("runtime_selection_log_count"), PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET),
        _expect("existing_top1_summary_count", gap.get("existing_top1_summary_count"), PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET),
        _expect("existing_shadow_summary_count", gap.get("existing_shadow_summary_count"), PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET),
        _expect("existing_paired_run_key_count", gap.get("existing_paired_run_key_count"), PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET),
        _expect("existing_delta_count", gap.get("existing_delta_count"), PLAN_MODULE.EXISTING_RUN_LEVEL_PAIR_TARGET),
        _expect("candidate_closed_loop_outcome_records", gap.get("candidate_closed_loop_outcome_records"), 0),
        _expect("missing_candidate_closed_loop_outcome_records", gap.get("missing_candidate_closed_loop_outcome_records"), PLAN_MODULE.OBJECTIVE_REQUIRED_RECORDS),
        _expect("objective_3200_gap_present", gap.get("objective_3200_gap_present"), True),
        _expect("closeout_does_not_satisfy_objective", gap.get("closeout_does_not_satisfy_objective"), True),
        _expect("preflight_steps", preflight_steps, list(EXPECTED_PREFLIGHT_STEPS)),
        _expect("no_go_register", no_go, list(EXPECTED_NO_GO)),
        _expect("artifact_contract_nested_sha256s_required", artifact_contract.get("nested_sha256s_required"), True),
        _expect("artifact_contract_root_sha256s_required", artifact_contract.get("root_sha256s_required"), True),
    ]
    for action in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_plan_decision_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(_expect(f"source_plan_execution_flag_{flag}", decision.get(flag), False))
    for flag in (
        "training_execution",
        "replay_execution",
        "candidate_generation",
        "dp_modification",
        "online_selector_change",
        "promotion_executed",
        "deployment_executed",
        "safety_or_camp_over_dp_claim",
    ):
        checks.append(_expect(f"source_plan_analysis_{flag}", analysis.get(flag), False))
    return checks


def _source_surface_checks(script_text: str, test_text: str) -> list[dict[str, Any]]:
    return [
        _check("script_objective_required_records_constant", "OBJECTIVE_REQUIRED_RECORDS = 3200" in script_text),
        _check("script_fixed_dp_head_constant", FIXED_DP_HEAD in script_text),
        _check(
            "script_authorizes_static_review_only",
            "outcome_source_inventory_preflight_static_review_only" in script_text,
        ),
        _check("script_blocks_promotion", "selector_promotion_authorized" in script_text),
        _check("script_blocks_deployment", "deployment_authorized" in script_text),
        _check("script_blocks_claims", "camp_over_dp_top1_claim_authorized" in script_text),
        _check("script_preserves_affine_score", SCORE_EXPRESSION in script_text),
        _check("test_covers_happy_path", "test_objective_3200_outcome_continuation_plan_passes" in test_text),
        _check("test_covers_enable", "requires_enable" in test_text),
        _check("test_covers_wrong_eof", "rejects_wrong_eof" in test_text),
        _check("test_covers_claim_leak", "rejects_source_claim_leak" in test_text),
        _check("test_covers_absent_gap", "rejects_absent_objective_gap" in test_text),
    ]


def _decision(*, passed: bool, checks: list[dict[str, Any]], source_plan: dict[str, Any]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_objective_3200_source_inventory_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("sha" in name or "artifact" in name for name in failed):
        failure_class = "source_artifact_hash_or_layout_failure"
    elif any(name.startswith("source_plan") for name in failed):
        failure_class = "source_plan_contract_failure"
    else:
        failure_class = "objective_3200_source_inventory_static_review_contract_failure"
    gap = _dict(source_plan.get("objective_gap_summary"))
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_outcome_source_inventory_preflight_static_review_passed": bool(passed),
        "objective_3200_outcome_source_inventory_preflight_authorized": bool(passed),
        "source_plan_consumed_by_this_gate": bool(passed),
        "objective_3200_gap_present": gap.get("objective_3200_gap_present"),
        "candidate_closed_loop_outcome_records": gap.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": gap.get("missing_candidate_closed_loop_outcome_records"),
        "recommendation": "read_only_objective_3200_outcome_source_inventory_preflight" if passed else "repair_or_rerun_same_static_review_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    decision["source_inventory_preflight_executed_by_this_gate"] = False
    return decision


def _source_plan_summary(source_plan: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_plan.get("final_decision"))
    gap = _dict(source_plan.get("objective_gap_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "plan_check_count": len(source_plan.get("plan_checks", [])),
        "failed_check_count": len(decision.get("failed_checks", [])),
        "objective_required_records": gap.get("objective_required_records"),
        "runtime_record_count": gap.get("runtime_record_count"),
        "existing_delta_count": gap.get("existing_delta_count"),
        "candidate_closed_loop_outcome_records": gap.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": gap.get("missing_candidate_closed_loop_outcome_records"),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(PLAN_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{PLAN_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_plan_summary"]
    return "\n".join(
        [
            "# Objective-3200 Outcome Source Inventory Preflight Static Review",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Source Plan",
            "",
            f"- Source status: `{summary['status']}`",
            f"- Objective required records: `{summary['objective_required_records']}`",
            f"- Runtime records: `{summary['runtime_record_count']}`",
            f"- Existing deltas: `{summary['existing_delta_count']}`",
            f"- Per-record shadow outcomes: `{summary['candidate_closed_loop_outcome_records']}`",
            f"- Missing per-record shadow outcomes: `{summary['missing_candidate_closed_loop_outcome_records']}`",
            "",
            "## Boundary",
            "",
            "- Static review only: no source inventory execution, replay, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
            f"- Score expression: `{report['analysis']['score_expression']}`",
        ]
    ) + "\n"


def _read_sha256sums(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in PLAN_MODULE._read_text(path).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        sha, _, name = stripped.partition("  ")
        if not name:
            parts = stripped.split(maxsplit=1)
            if len(parts) != 2:
                continue
            sha, name = parts
        values[name.strip().replace("\\", "/")] = sha.strip()
    return values


def _sha_from_sums(values: dict[str, str], *names: str) -> str | None:
    normalized = {key.replace("\\", "/"): value for key, value in values.items()}
    for name in names:
        key = name.replace("\\", "/")
        if key in normalized:
            return normalized[key]
    return None


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": _jsonable(actual),
        "expected": _jsonable(expected),
    }


def _check(name: str, passed: bool, actual: Any | None = None, expected: Any = True) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "actual": _jsonable(actual if actual is not None else bool(passed)),
        "expected": _jsonable(expected),
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
