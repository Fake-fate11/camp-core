#!/usr/bin/env python3
"""Static review for the objective-3200 outcome acquisition preflight."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_preflight_module():
    preflight_path = Path(__file__).resolve().with_name(
        "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_"
        "promotion_evidence_acquisition_objective_3200_outcome_acquisition.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight",
        preflight_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PREFLIGHT_MODULE = _load_preflight_module()

FIXED_DP_HEAD = PREFLIGHT_MODULE.FIXED_DP_HEAD
SCORE_EXPRESSION = PREFLIGHT_MODULE.SCORE_EXPRESSION
SOURCE_PREFLIGHT_SCHEMA = PREFLIGHT_MODULE.SCHEMA_VERSION
SOURCE_PREFLIGHT_STATUS = PREFLIGHT_MODULE.READY_STATUS
SOURCE_PREFLIGHT_JSON_NAME = PREFLIGHT_MODULE.PREFLIGHT_JSON_NAME
SOURCE_PREFLIGHT_MD_NAME = PREFLIGHT_MODULE.PREFLIGHT_MD_NAME
BLOCKED_ACTIONS = PREFLIGHT_MODULE.BLOCKED_ACTIONS
FALSE_EXECUTION_FLAGS = PREFLIGHT_MODULE.FALSE_EXECUTION_FLAGS

SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_"
    "objective_3200_outcome_acquisition_preflight_static_review_v1"
)
AUTHORIZED_CURRENT_WORK = PREFLIGHT_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_preflight_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_preflight_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_execution_only"
)

REVIEW_JSON_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_preflight_static_review.json"
)
REVIEW_MD_NAME = (
    "post_closeout_promotion_evidence_acquisition_objective_3200_"
    "outcome_acquisition_preflight_static_review.md"
)

EXPECTED_PREFLIGHT_ITEM_COUNT = len(PREFLIGHT_MODULE.EXPECTED_PREFLIGHT_ITEMS)
EXPECTED_PLANNED_OUTPUT_COUNT = len(PREFLIGHT_MODULE.EXPECTED_PLANNED_OUTPUTS)
EXPECTED_NO_GO_COUNT = len(PREFLIGHT_MODULE.PREFLIGHT_NO_GO)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outcome_acquisition_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--outcome_acquisition_preflight_json", type=Path, required=True)
    parser.add_argument("--outcome_acquisition_preflight_md", type=Path, required=True)
    parser.add_argument("--outcome_acquisition_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--outcome_acquisition_preflight_script_py", type=Path, required=True)
    parser.add_argument("--outcome_acquisition_preflight_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        outcome_acquisition_preflight_artifact_dir=args.outcome_acquisition_preflight_artifact_dir,
        outcome_acquisition_preflight_json=args.outcome_acquisition_preflight_json,
        outcome_acquisition_preflight_md=args.outcome_acquisition_preflight_md,
        outcome_acquisition_preflight_sha256s=args.outcome_acquisition_preflight_sha256s,
        outcome_acquisition_preflight_script_py=args.outcome_acquisition_preflight_script_py,
        outcome_acquisition_preflight_test_py=args.outcome_acquisition_preflight_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(PREFLIGHT_MODULE._stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    outcome_acquisition_preflight_artifact_dir: Path,
    outcome_acquisition_preflight_json: Path,
    outcome_acquisition_preflight_md: Path,
    outcome_acquisition_preflight_sha256s: Path,
    outcome_acquisition_preflight_script_py: Path,
    outcome_acquisition_preflight_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact_dir = outcome_acquisition_preflight_artifact_dir.resolve()
    paths = {
        "outcome_acquisition_preflight_json": outcome_acquisition_preflight_json.resolve(),
        "outcome_acquisition_preflight_md": outcome_acquisition_preflight_md.resolve(),
        "outcome_acquisition_preflight_sha256s": outcome_acquisition_preflight_sha256s.resolve(),
        "outcome_acquisition_preflight_script_py": outcome_acquisition_preflight_script_py.resolve(),
        "outcome_acquisition_preflight_test_py": outcome_acquisition_preflight_test_py.resolve(),
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    artifact_files = {
        "heads": artifact_dir / "HEADS",
        "command": artifact_dir / "COMMAND",
        "stdout": artifact_dir / "stdout",
        "stderr": artifact_dir / "stderr",
        "run_exit": artifact_dir / "run.exit",
        "root_sha256s": artifact_dir / "SHA256SUMS",
        "preflight_json": artifact_dir / "preflight" / SOURCE_PREFLIGHT_JSON_NAME,
        "preflight_md": artifact_dir / "preflight" / SOURCE_PREFLIGHT_MD_NAME,
        "preflight_sha256s": artifact_dir / "preflight" / "SHA256SUMS",
    }
    source_preflight = PREFLIGHT_MODULE._read_json_dict(paths["outcome_acquisition_preflight_json"])
    v14_text = PREFLIGHT_MODULE._read_text(paths["v14_audit_md"])
    status_text = PREFLIGHT_MODULE._read_text(paths["current_status_md"])
    script_text = PREFLIGHT_MODULE._read_text(paths["outcome_acquisition_preflight_script_py"])
    test_text = PREFLIGHT_MODULE._read_text(paths["outcome_acquisition_preflight_test_py"])
    heads = PREFLIGHT_MODULE._parse_key_values(PREFLIGHT_MODULE._read_text(artifact_files["heads"]))
    root_sha256s = PREFLIGHT_MODULE._read_sha256sums(artifact_files["root_sha256s"])
    nested_sha256s = PREFLIGHT_MODULE._read_sha256sums(paths["outcome_acquisition_preflight_sha256s"])
    run_exit = PREFLIGHT_MODULE._read_text(artifact_files["run_exit"]).strip()
    checks = _checks(
        enabled=enabled,
        artifact_dir=artifact_dir,
        paths=paths,
        artifact_files=artifact_files,
        source_preflight=source_preflight,
        v14_text=v14_text,
        status_text=status_text,
        script_text=script_text,
        test_text=test_text,
        heads=heads,
        root_sha256s=root_sha256s,
        nested_sha256s=nested_sha256s,
        run_exit=run_exit,
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
            "objective_3200_outcome_acquisition_preflight_static_review_only": True,
            "outcome_acquisition_execution": False,
            "outcome_acquisition_executed": False,
            "closed_loop_replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "candidate_tensor_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "inputs": {
            "outcome_acquisition_preflight_artifact_dir": str(artifact_dir),
            **{name: str(path) for name, path in paths.items()},
            "output_dir": str(output_dir.resolve()),
        },
        "source_artifact_hashes": _source_hashes(
            artifact_dir=artifact_dir,
            preflight_json=paths["outcome_acquisition_preflight_json"],
            preflight_md=paths["outcome_acquisition_preflight_md"],
            preflight_sha256s=paths["outcome_acquisition_preflight_sha256s"],
        ),
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "source_preflight_camp_head": PREFLIGHT_MODULE._kv(heads, "CAMP_HEAD", "camp_head"),
            "source_preflight_camp_origin_main": PREFLIGHT_MODULE._kv(
                heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main"
            ),
            "source_preflight_dp_head": PREFLIGHT_MODULE._kv(heads, "DP_HEAD", "dp_head"),
        },
        "source_preflight_summary": _source_preflight_summary(source_preflight),
        "static_review_checks": checks,
        "final_decision": _decision(passed=passed, checks=checks, source_preflight=source_preflight),
    }


def _checks(
    *,
    enabled: bool,
    artifact_dir: Path,
    paths: dict[str, Path],
    artifact_files: dict[str, Path],
    source_preflight: dict[str, Any],
    v14_text: str,
    status_text: str,
    script_text: str,
    test_text: str,
    heads: dict[str, str],
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    run_exit: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    decision = PREFLIGHT_MODULE._dict(source_preflight.get("final_decision"))
    analysis = PREFLIGHT_MODULE._dict(source_preflight.get("analysis"))
    objective = PREFLIGHT_MODULE._dict(source_preflight.get("objective_3200_summary"))
    future_contract = PREFLIGHT_MODULE._dict(source_preflight.get("future_acquisition_execution_contract"))
    checks = [
        PREFLIGHT_MODULE._expect("static_review_enabled", enabled, True),
        PREFLIGHT_MODULE._expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        PREFLIGHT_MODULE._expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        PREFLIGHT_MODULE._expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        PREFLIGHT_MODULE._check("current_camp_head_is_sha", PREFLIGHT_MODULE._is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        PREFLIGHT_MODULE._expect("audit_latest_status", PREFLIGHT_MODULE._latest_value(v14_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS),
        PREFLIGHT_MODULE._expect("audit_latest_next_work", PREFLIGHT_MODULE._latest_value(v14_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PREFLIGHT_MODULE._expect("status_doc_latest_status", PREFLIGHT_MODULE._latest_value(status_text, "current_v14_status"), SOURCE_PREFLIGHT_STATUS),
        PREFLIGHT_MODULE._expect("status_doc_latest_next_work", PREFLIGHT_MODULE._latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        PREFLIGHT_MODULE._check("outcome_acquisition_preflight_artifact_dir_exists", artifact_dir.is_dir(), str(artifact_dir), "directory"),
    ]
    for name, path in paths.items():
        checks.extend(PREFLIGHT_MODULE._path_checks(name, path, require_file=True))
    for name, path in artifact_files.items():
        checks.extend(
            PREFLIGHT_MODULE._path_checks(
                f"artifact_{name}", path, require_file=True, allow_empty=name == "stderr"
            )
        )
    checks.extend(
        [
            PREFLIGHT_MODULE._expect("source_preflight_run_exit", run_exit, "0"),
            PREFLIGHT_MODULE._expect("source_preflight_schema", source_preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA),
            PREFLIGHT_MODULE._expect("source_preflight_passed", decision.get("passed"), True),
            PREFLIGHT_MODULE._expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
            PREFLIGHT_MODULE._expect("source_preflight_authorized_next", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
            PREFLIGHT_MODULE._expect("source_preflight_ready", decision.get("objective_3200_outcome_acquisition_preflight_ready"), True),
            PREFLIGHT_MODULE._expect("source_preflight_static_review_authorized", decision.get("objective_3200_outcome_acquisition_preflight_static_review_authorized"), True),
            PREFLIGHT_MODULE._expect("source_preflight_direct_acquisition_execution_authorized", decision.get("direct_acquisition_execution_authorized"), False),
            PREFLIGHT_MODULE._expect("source_preflight_direct_replay_execution_authorized", decision.get("direct_replay_execution_authorized"), False),
            PREFLIGHT_MODULE._expect("source_preflight_read_only", analysis.get("read_only"), True),
            PREFLIGHT_MODULE._expect("source_preflight_preflight_only", analysis.get("objective_3200_outcome_acquisition_preflight_only"), True),
            PREFLIGHT_MODULE._expect("source_preflight_outcome_acquisition_execution", analysis.get("outcome_acquisition_execution"), False),
            PREFLIGHT_MODULE._expect("source_preflight_replay_execution", analysis.get("closed_loop_replay_execution"), False),
            PREFLIGHT_MODULE._expect("source_preflight_training_execution", analysis.get("training_execution"), False),
            PREFLIGHT_MODULE._expect("source_preflight_candidate_generation", analysis.get("candidate_generation"), False),
            PREFLIGHT_MODULE._expect("source_preflight_dp_modification", analysis.get("dp_modification"), False),
            PREFLIGHT_MODULE._expect("source_preflight_score_expression", analysis.get("score_expression"), SCORE_EXPRESSION),
            PREFLIGHT_MODULE._expect("source_preflight_dp_head_fixed", PREFLIGHT_MODULE._kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
            PREFLIGHT_MODULE._expect("source_preflight_camp_head_matches_origin", PREFLIGHT_MODULE._kv(heads, "CAMP_HEAD", "camp_head"), PREFLIGHT_MODULE._kv(heads, "CAMP_ORIGIN_MAIN", "CAMP_ORIGIN", "camp_origin_main")),
            PREFLIGHT_MODULE._expect("objective_required_records", objective.get("objective_required_records"), PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS),
            PREFLIGHT_MODULE._expect("runtime_record_count", objective.get("runtime_record_count"), PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS),
            PREFLIGHT_MODULE._expect("candidate_closed_loop_outcome_records", objective.get("candidate_closed_loop_outcome_records"), 0),
            PREFLIGHT_MODULE._expect("missing_candidate_closed_loop_outcome_records", objective.get("missing_candidate_closed_loop_outcome_records"), PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS),
            PREFLIGHT_MODULE._expect("requires_acquisition_execution", objective.get("requires_acquisition_execution"), True),
            PREFLIGHT_MODULE._expect("preflight_item_count", len(source_preflight.get("preflight_items") or []), EXPECTED_PREFLIGHT_ITEM_COUNT),
            PREFLIGHT_MODULE._expect("planned_output_count", len(source_preflight.get("planned_outputs") or []), EXPECTED_PLANNED_OUTPUT_COUNT),
            PREFLIGHT_MODULE._expect("no_go_count", len(source_preflight.get("no_go_register") or []), EXPECTED_NO_GO_COUNT),
            PREFLIGHT_MODULE._expect("future_execution_requires_static_review", future_contract.get("future_execution_requires_static_review"), True),
            PREFLIGHT_MODULE._expect("future_execution_authorized_by_this_gate", future_contract.get("future_execution_authorized_by_this_gate"), False),
            PREFLIGHT_MODULE._expect("future_execution_candidate_source", future_contract.get("candidate_source"), "fixed_dp_candidate_tensor_only"),
            PREFLIGHT_MODULE._expect("future_execution_camp_action", future_contract.get("camp_action"), "read_shadow_selected_index_and_select_existing_candidate_only"),
            PREFLIGHT_MODULE._check("script_mentions_static_review_boundary", "future_execution_requires_static_review" in script_text),
            PREFLIGHT_MODULE._check("script_blocks_direct_execution", "direct_acquisition_execution_authorized" in script_text),
            PREFLIGHT_MODULE._check("test_asserts_no_direct_execution", "direct_acquisition_execution_authorized\"] is False" in test_text),
        ]
    )
    checks.extend(
        _sha_checks(
            root_sha256s=root_sha256s,
            nested_sha256s=nested_sha256s,
            json_path=paths["outcome_acquisition_preflight_json"],
            md_path=paths["outcome_acquisition_preflight_md"],
            sha256s_path=paths["outcome_acquisition_preflight_sha256s"],
        )
    )
    for action in BLOCKED_ACTIONS:
        checks.append(PREFLIGHT_MODULE._expect(f"source_preflight_{action}", decision.get(action), False))
    for flag in FALSE_EXECUTION_FLAGS:
        checks.append(PREFLIGHT_MODULE._expect(f"source_preflight_{flag}", decision.get(flag), False))
    return checks


def _sha_checks(
    *,
    root_sha256s: dict[str, str],
    nested_sha256s: dict[str, str],
    json_path: Path,
    md_path: Path,
    sha256s_path: Path,
) -> list[dict[str, Any]]:
    json_sha = PREFLIGHT_MODULE._sha256(json_path)
    md_sha = PREFLIGHT_MODULE._sha256(md_path)
    sha_sha = PREFLIGHT_MODULE._sha256(sha256s_path)
    return [
        PREFLIGHT_MODULE._expect(
            "root_preflight_json_sha",
            PREFLIGHT_MODULE._sha_for_suffix(root_sha256s, f"preflight/{SOURCE_PREFLIGHT_JSON_NAME}"),
            json_sha,
        ),
        PREFLIGHT_MODULE._expect(
            "root_preflight_md_sha",
            PREFLIGHT_MODULE._sha_for_suffix(root_sha256s, f"preflight/{SOURCE_PREFLIGHT_MD_NAME}"),
            md_sha,
        ),
        PREFLIGHT_MODULE._expect(
            "root_preflight_sha256s_sha",
            PREFLIGHT_MODULE._sha_for_suffix(root_sha256s, "preflight/SHA256SUMS"),
            sha_sha,
        ),
        PREFLIGHT_MODULE._expect(
            "nested_preflight_json_sha",
            PREFLIGHT_MODULE._sha_for_suffix(nested_sha256s, json_path.name),
            json_sha,
        ),
        PREFLIGHT_MODULE._expect(
            "nested_preflight_md_sha",
            PREFLIGHT_MODULE._sha_for_suffix(nested_sha256s, md_path.name),
            md_sha,
        ),
    ]


def _source_hashes(
    *,
    artifact_dir: Path,
    preflight_json: Path,
    preflight_md: Path,
    preflight_sha256s: Path,
) -> dict[str, str]:
    return {
        "root_sha256s": PREFLIGHT_MODULE._sha256(artifact_dir / "SHA256SUMS"),
        "preflight_json": PREFLIGHT_MODULE._sha256(preflight_json),
        "preflight_md": PREFLIGHT_MODULE._sha256(preflight_md),
        "preflight_sha256s": PREFLIGHT_MODULE._sha256(preflight_sha256s),
    }


def _source_preflight_summary(source_preflight: dict[str, Any]) -> dict[str, Any]:
    decision = PREFLIGHT_MODULE._dict(source_preflight.get("final_decision"))
    objective = PREFLIGHT_MODULE._dict(source_preflight.get("objective_3200_summary"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "objective_required_records": objective.get("objective_required_records"),
        "runtime_record_count": objective.get("runtime_record_count"),
        "candidate_closed_loop_outcome_records": objective.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": objective.get("missing_candidate_closed_loop_outcome_records"),
        "preflight_item_count": len(source_preflight.get("preflight_items") or []),
        "planned_output_count": len(source_preflight.get("planned_outputs") or []),
        "no_go_count": len(source_preflight.get("no_go_register") or []),
    }


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    source_preflight: dict[str, Any],
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    source_decision = PREFLIGHT_MODULE._dict(source_preflight.get("final_decision"))
    objective = PREFLIGHT_MODULE._dict(source_preflight.get("objective_3200_summary"))
    if passed:
        failure_class = None
    elif "static_review_enabled" in failed:
        failure_class = "explicit_objective_3200_outcome_acquisition_preflight_static_review_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v14_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_preflight") for name in failed):
        failure_class = "source_preflight_contract_failure"
    elif any(name.endswith("_sha") for name in failed):
        failure_class = "source_preflight_hash_contract_failure"
    else:
        failure_class = "objective_3200_outcome_acquisition_preflight_static_review_contract_failure"
    decision = {
        "passed": bool(passed),
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "objective_3200_outcome_acquisition_preflight_static_review_passed": bool(passed),
        "objective_3200_outcome_acquisition_execution_authorized": bool(passed),
        "objective_required_records": objective.get("objective_required_records"),
        "runtime_record_count": objective.get("runtime_record_count"),
        "candidate_closed_loop_outcome_records": objective.get("candidate_closed_loop_outcome_records"),
        "missing_candidate_closed_loop_outcome_records": objective.get("missing_candidate_closed_loop_outcome_records"),
        "requires_acquisition_execution": bool(source_decision.get("requires_acquisition_execution")) if passed else False,
        "direct_acquisition_execution_authorized": False,
        "direct_replay_execution_authorized": False,
        "recommendation": "objective_3200_outcome_acquisition_execution_only_after_static_review" if passed else "repair_or_rerun_same_static_review_gate",
        "score_expression": SCORE_EXPRESSION,
    }
    for action in BLOCKED_ACTIONS:
        decision[action] = False
    for flag in FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return decision


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(PREFLIGHT_MODULE._stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    sums = [f"{PREFLIGHT_MODULE._sha256(path)}  {path.name}" for path in (json_path, md_path)]
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_preflight_summary"]
    return "\n".join(
        [
            "# Objective-3200 Outcome Acquisition Preflight Static Review",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Source Preflight",
            "",
            f"- Objective required records: `{summary['objective_required_records']}`",
            f"- Runtime records: `{summary['runtime_record_count']}`",
            f"- Missing per-record shadow-selected outcomes: `{summary['missing_candidate_closed_loop_outcome_records']}`",
            f"- Preflight items / planned outputs / no-go checks: `{summary['preflight_item_count']} / {summary['planned_output_count']} / {summary['no_go_count']}`",
            "",
            "## Boundary",
            "",
            "- Static review only: no outcome acquisition, replay execution, training, candidate generation, DP modification, promotion, deployment, online selector activation, or claim.",
            f"- Score expression: `{report['analysis']['score_expression']}`",
        ]
    ) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
