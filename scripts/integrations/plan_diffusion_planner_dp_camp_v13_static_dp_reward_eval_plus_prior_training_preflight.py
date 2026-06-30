#!/usr/bin/env python3
"""Preflight static DP-reward CAMP training over fixed prior plus eval logs.

This gate is planning/materialization only. It validates fixed CAMP selection
logs, writes a selection-log manifest, and writes a training command plan for a
later static DP-reward training execution gate. It does not run replay,
generate candidates, train CAMP, modify Diffusion Planner, promote artifacts,
deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shlex
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    validate_logs,
)


SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_preflight_v1"
)
MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_selection_manifest_v1"
)
COMMAND_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_command_plan_v1"
)
READY_STATUS = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_preflight_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_preflight_rejected"
)
DISABLED_STATUS = (
    "dp_camp_v13_static_dp_reward_eval_plus_prior_training_preflight_disabled"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_shadow_replay_eval_plus_prior_static_dp_reward_training_"
    "preflight_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_shadow_replay_eval_plus_prior_static_dp_reward_training_"
    "execution_only"
)
AUDIT_PREFLIGHT_AUTHORIZATION_KEY = (
    "static_dp_reward_shadow_replay_eval_plus_prior_static_dp_reward_training_"
    "preflight_authorized"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
FORMAL_SEEDS = {11, 12, 13}
POSTSELECTION_FIELDS = (
    "perfect_tracker_command_postselection",
    "traffic_light_hybrid_postselection",
    "underprogress_relaxation",
    "splice_shadow_rule",
)
REQUIRED_TRAINING_FLAGS = (
    "--label_source",
    "dp_reward",
    "--reward_key",
    "quality_without_progress",
    "--reward_progress_weight",
    "2.0",
    "--require_dp_native_training_data_contract",
    "--require_atom_schema",
)
FORBIDDEN_COMMAND_TOKENS = (
    "--camp_collect_closed_loop_outcomes",
    "--label_source closed_loop_outcome",
    "--label_source safety_cost_v1_hard_guarded",
    "--outcome_weights",
    "--proxy_weights",
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a static DP-reward training preflight over fixed prior "
            "and evaluation CAMP selection logs."
        )
    )
    parser.add_argument("--prior_output_dir", type=Path, required=True)
    parser.add_argument("--prior_selection_manifest_json", type=Path, default=None)
    parser.add_argument("--evaluation_output_dir", type=Path, required=True)
    parser.add_argument("--trainer_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--planned_training_output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--python_executable", default="python")
    parser.add_argument("--expected_prior_selection_log_count", type=int, default=32)
    parser.add_argument("--expected_evaluation_selection_log_count", type=int, default=32)
    parser.add_argument("--expected_prior_records", type=int, default=3200)
    parser.add_argument("--expected_evaluation_records", type=int, default=3200)
    parser.add_argument("--expected_candidate_count", type=int, default=8)
    parser.add_argument("--expected_atom_count", type=int, default=14)
    parser.add_argument("--max_prior_eval_tensor_overlap_rate", type=float, default=0.0)
    parser.add_argument("--label_source", default="dp_reward")
    parser.add_argument("--reward_key", default="quality_without_progress")
    parser.add_argument("--reward_progress_weight", type=float, default=2.0)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--lr", type=float, default=0.2)
    parser.add_argument("--l2_reg", type=float, default=0.01)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument(
        "--audit_preflight_authorization_key",
        default=AUDIT_PREFLIGHT_AUTHORIZATION_KEY,
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_selection_manifest_json", type=Path, required=True)
    parser.add_argument("--output_command_plan_json", type=Path, required=True)
    parser.add_argument("--output_runbook", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_static_dp_reward_eval_plus_prior_training_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        prior_output_dir=args.prior_output_dir,
        prior_selection_manifest_json=args.prior_selection_manifest_json,
        evaluation_output_dir=args.evaluation_output_dir,
        trainer_py=args.trainer_py,
        v13_audit_md=args.v13_audit_md,
        planned_training_output_dir=args.planned_training_output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        python_executable=args.python_executable,
        expected_prior_selection_log_count=args.expected_prior_selection_log_count,
        expected_evaluation_selection_log_count=args.expected_evaluation_selection_log_count,
        expected_prior_records=args.expected_prior_records,
        expected_evaluation_records=args.expected_evaluation_records,
        expected_candidate_count=args.expected_candidate_count,
        expected_atom_count=args.expected_atom_count,
        max_prior_eval_tensor_overlap_rate=args.max_prior_eval_tensor_overlap_rate,
        label_source=args.label_source,
        reward_key=args.reward_key,
        reward_progress_weight=args.reward_progress_weight,
        epochs=args.epochs,
        lr=args.lr,
        l2_reg=args.l2_reg,
        scale_percentile=args.scale_percentile,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        audit_preflight_authorization_key=args.audit_preflight_authorization_key,
        enabled=bool(args.enable_v13_static_dp_reward_eval_plus_prior_training_preflight),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if report["final_decision"]["passed"]:
        args.output_selection_manifest_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_command_plan_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_runbook.parent.mkdir(parents=True, exist_ok=True)
        args.output_selection_manifest_json.write_text(
            json.dumps(_stable(report["selection_manifest"]), indent=2) + "\n",
            encoding="utf-8",
        )
        args.output_command_plan_json.write_text(
            json.dumps(_stable(report["training_command_plan"]), indent=2) + "\n",
            encoding="utf-8",
        )
        args.output_runbook.write_text(render_runbook(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    prior_output_dir: Path,
    prior_selection_manifest_json: Path | None = None,
    evaluation_output_dir: Path,
    trainer_py: Path,
    v13_audit_md: Path,
    planned_training_output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    python_executable: str = "python",
    expected_prior_selection_log_count: int = 32,
    expected_evaluation_selection_log_count: int = 32,
    expected_prior_records: int = 3200,
    expected_evaluation_records: int = 3200,
    expected_candidate_count: int = 8,
    expected_atom_count: int = 14,
    max_prior_eval_tensor_overlap_rate: float = 0.0,
    label_source: str = "dp_reward",
    reward_key: str = "quality_without_progress",
    reward_progress_weight: float = 2.0,
    epochs: int = 1000,
    lr: float = 0.2,
    l2_reg: float = 0.01,
    scale_percentile: float = 95.0,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    audit_preflight_authorization_key: str = AUDIT_PREFLIGHT_AUTHORIZATION_KEY,
    enabled: bool = False,
) -> dict[str, Any]:
    prior_output_dir = prior_output_dir.resolve()
    prior_selection_manifest_json = (
        prior_selection_manifest_json.resolve()
        if prior_selection_manifest_json is not None
        else None
    )
    evaluation_output_dir = evaluation_output_dir.resolve()
    trainer_py = trainer_py.resolve()
    v13_audit_md = v13_audit_md.resolve()
    planned_training_output_dir = planned_training_output_dir.resolve()
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "preflight_only": True,
            "selection_manifest_materialized": False,
            "training_command_plan_materialized": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "dp_modification_execution": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "math_boundary": (
                "The planned training command fits nonnegative simplex weights "
                "over approved atoms and preserves affine scores "
                "score_k(w)=a_k^T w; it does not alter Benders, DP candidates, "
                "or executed trajectories."
            ),
        },
        "source_paths": {
            "prior_output_dir": str(prior_output_dir),
            "prior_selection_manifest_json": (
                str(prior_selection_manifest_json)
                if prior_selection_manifest_json is not None
                else None
            ),
            "evaluation_output_dir": str(evaluation_output_dir),
            "trainer_py": str(trainer_py),
            "v13_audit_md": str(v13_audit_md),
            "planned_training_output_dir": str(planned_training_output_dir),
        },
        "source_hashes": {},
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "training_input_summary": {},
        "clean_contract": {},
        "candidate_tensor_overlap": {},
        "selection_manifest": {},
        "training_command_plan": {},
        "review_checks": [],
        "final_decision": _decision(
            False,
            [],
            enabled=False,
            authorized_next_work=authorized_next_work,
        ),
    }
    if not enabled:
        return report

    prior_manifest = (
        _load_selection_manifest(prior_selection_manifest_json)
        if prior_selection_manifest_json is not None
        else {}
    )
    prior_manifest_relative_paths = _manifest_relative_paths(prior_manifest)
    prior_logs = (
        _selection_logs_from_manifest(prior_manifest)
        if prior_selection_manifest_json is not None
        else _selection_logs(prior_output_dir)
    )
    eval_logs = _selection_logs(evaluation_output_dir)
    all_logs = prior_logs + eval_logs
    trainer_text = _read_text(trainer_py)
    audit_text = _read_text(v13_audit_md)
    clean_contract = (
        validate_logs(all_logs)
        if all_logs
        else {"passed": False, "records": 0, "failed_records": []}
    )
    input_summary = _summarize_sources(
        prior_logs=prior_logs,
        eval_logs=eval_logs,
        prior_output_dir=prior_output_dir,
        prior_relative_paths=prior_manifest_relative_paths,
        evaluation_output_dir=evaluation_output_dir,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
    )
    overlap = _tensor_overlap(prior_logs, eval_logs)
    selection_manifest = _selection_manifest(
        prior_output_dir=prior_output_dir,
        prior_selection_manifest_json=prior_selection_manifest_json,
        prior_relative_paths=prior_manifest_relative_paths,
        evaluation_output_dir=evaluation_output_dir,
        prior_logs=prior_logs,
        eval_logs=eval_logs,
        input_summary=input_summary,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    command_plan = _command_plan(
        python_executable=python_executable,
        trainer_py=trainer_py,
        selection_logs=all_logs,
        planned_training_output_dir=planned_training_output_dir,
        label_source=label_source,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
        epochs=epochs,
        lr=lr,
        l2_reg=l2_reg,
        scale_percentile=scale_percentile,
    )
    report["source_hashes"] = {
        "trainer_py_sha256": _sha256(trainer_py) if trainer_py.is_file() else None,
        "v13_audit_md_sha256": _sha256(v13_audit_md) if v13_audit_md.is_file() else None,
    }
    report["training_input_summary"] = input_summary
    report["clean_contract"] = {
        "passed": bool(clean_contract.get("passed")),
        "records": int(clean_contract.get("records", 0)),
        "failed_records": int(len(clean_contract.get("failed_records", []))),
        "future_training_input_contract_satisfied": bool(
            clean_contract.get("future_training_input_contract_satisfied")
        ),
    }
    report["candidate_tensor_overlap"] = overlap
    report["selection_manifest"] = selection_manifest
    report["training_command_plan"] = command_plan

    checks = _checks(
        prior_output_dir=prior_output_dir,
        prior_selection_manifest_json=prior_selection_manifest_json,
        prior_manifest=prior_manifest,
        evaluation_output_dir=evaluation_output_dir,
        trainer_py=trainer_py,
        v13_audit_md=v13_audit_md,
        planned_training_output_dir=planned_training_output_dir,
        audit_text=audit_text,
        trainer_text=trainer_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        prior_logs=prior_logs,
        eval_logs=eval_logs,
        clean_contract=clean_contract,
        input_summary=input_summary,
        overlap=overlap,
        command_plan=command_plan,
        expected_prior_selection_log_count=expected_prior_selection_log_count,
        expected_evaluation_selection_log_count=expected_evaluation_selection_log_count,
        expected_prior_records=expected_prior_records,
        expected_evaluation_records=expected_evaluation_records,
        expected_candidate_count=expected_candidate_count,
        expected_atom_count=expected_atom_count,
        max_prior_eval_tensor_overlap_rate=max_prior_eval_tensor_overlap_rate,
        label_source=label_source,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
        authorized_current_work=authorized_current_work,
        audit_preflight_authorization_key=audit_preflight_authorization_key,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    report["review_checks"] = checks
    report["analysis"]["selection_manifest_materialized"] = bool(passed)
    report["analysis"]["training_command_plan_materialized"] = bool(passed)
    report["final_decision"] = _decision(
        passed,
        failed,
        enabled=True,
        authorized_next_work=authorized_next_work,
    )
    return report


def _checks(
    *,
    prior_output_dir: Path,
    prior_selection_manifest_json: Path | None,
    prior_manifest: dict[str, Any],
    evaluation_output_dir: Path,
    trainer_py: Path,
    v13_audit_md: Path,
    planned_training_output_dir: Path,
    audit_text: str,
    trainer_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    prior_logs: list[Path],
    eval_logs: list[Path],
    clean_contract: dict[str, Any],
    input_summary: dict[str, Any],
    overlap: dict[str, Any],
    command_plan: dict[str, Any],
    expected_prior_selection_log_count: int,
    expected_evaluation_selection_log_count: int,
    expected_prior_records: int,
    expected_evaluation_records: int,
    expected_candidate_count: int,
    expected_atom_count: int,
    max_prior_eval_tensor_overlap_rate: float,
    label_source: str,
    reward_key: str,
    reward_progress_weight: float,
    authorized_current_work: str,
    audit_preflight_authorization_key: str,
) -> list[dict[str, Any]]:
    expected_total_logs = (
        expected_prior_selection_log_count + expected_evaluation_selection_log_count
    )
    expected_total_records = expected_prior_records + expected_evaluation_records
    command = str(command_plan.get("command", ""))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("prior_output_dir_exists", prior_output_dir.is_dir(), str(prior_output_dir), "directory exists"),
        _check(
            "prior_selection_manifest_exists",
            prior_selection_manifest_json is None or prior_selection_manifest_json.is_file(),
            str(prior_selection_manifest_json)
            if prior_selection_manifest_json is not None
            else None,
            "file exists when provided",
        ),
        _check(
            "prior_selection_manifest_schema",
            prior_selection_manifest_json is None
            or prior_manifest.get("schema_version") == MANIFEST_SCHEMA_VERSION,
            prior_manifest.get("schema_version")
            if prior_selection_manifest_json is not None
            else None,
            MANIFEST_SCHEMA_VERSION,
        ),
        _check(
            "prior_selection_manifest_log_count",
            prior_selection_manifest_json is None
            or int(prior_manifest.get("selection_log_count", -1))
            == expected_prior_selection_log_count,
            prior_manifest.get("selection_log_count")
            if prior_selection_manifest_json is not None
            else None,
            expected_prior_selection_log_count,
        ),
        _check(
            "prior_selection_manifest_records_total",
            prior_selection_manifest_json is None
            or int(prior_manifest.get("records_total", -1)) == expected_prior_records,
            prior_manifest.get("records_total")
            if prior_selection_manifest_json is not None
            else None,
            expected_prior_records,
        ),
        _check("evaluation_output_dir_exists", evaluation_output_dir.is_dir(), str(evaluation_output_dir), "directory exists"),
        _check("trainer_py_exists", trainer_py.is_file(), str(trainer_py), "file exists"),
        _check("v13_audit_exists", v13_audit_md.is_file(), str(v13_audit_md), "file exists"),
        _check("planned_training_output_dir_absent", not planned_training_output_dir.exists(), str(planned_training_output_dir), "must not already exist"),
        _expect("audit_latest_next_work_target", _latest_audit_value(audit_text, "next_work_target"), authorized_current_work),
        _expect("audit_latest_current_scope", _latest_audit_value(audit_text, "current_v13_next_scope"), authorized_current_work.removeprefix("dp_camp_v13_")),
        _expect("audit_eval_plus_prior_training_preflight_authorized", _latest_audit_value(audit_text, audit_preflight_authorization_key), "True"),
        _expect("audit_training_execution_blocked", _latest_audit_value(audit_text, "training_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_replay_execution_blocked", _latest_audit_value(audit_text, "replay_execution_authorized_by_current_boundary"), "False"),
        _expect("audit_dp_modification_blocked", _latest_audit_value(audit_text, "dp_modification_authorized_by_current_boundary"), "False"),
        _expect("prior_selection_log_count", len(prior_logs), expected_prior_selection_log_count),
        _expect("evaluation_selection_log_count", len(eval_logs), expected_evaluation_selection_log_count),
        _expect("combined_selection_log_count", input_summary["combined"]["selection_log_count"], expected_total_logs),
        _expect("prior_records", input_summary["prior"]["records_total"], expected_prior_records),
        _expect("evaluation_records", input_summary["evaluation"]["records_total"], expected_evaluation_records),
        _expect("combined_records", input_summary["combined"]["records_total"], expected_total_records),
        _expect("clean_contract_passed", clean_contract.get("passed"), True),
        _expect("clean_contract_records", clean_contract.get("records"), expected_total_records),
        _expect("clean_contract_failed_records_zero", len(clean_contract.get("failed_records", [])), 0),
        _expect("candidate_count_values", input_summary["combined"]["candidate_count_values"], {str(expected_candidate_count): expected_total_records}),
        _expect("atom_schema_versions", input_summary["combined"]["atom_schema_versions"], {ATOM_SCHEMA_VERSION: expected_total_records}),
        _expect("atom_count_values", input_summary["combined"]["atom_count_values"], {str(expected_atom_count): expected_total_records}),
        _expect("formal_seed_records_zero", input_summary["combined"]["formal_seed_records"], 0),
        _expect("finite_reward_records", input_summary["combined"]["finite_reward_records"], expected_total_records),
        _expect("default_off_shadow_selector_valid_records", input_summary["combined"]["default_off_shadow_selector_valid_records"], expected_total_records),
        _expect("closed_loop_outcome_records_zero", input_summary["combined"]["closed_loop_outcome_records"], 0),
        _expect("reference_blend_enabled_records_zero", input_summary["combined"]["reference_blend_enabled_records"], 0),
        _expect("guidance_enabled_records_zero", input_summary["combined"]["guidance_enabled_records"], 0),
        _expect("postselection_records_zero", input_summary["combined"]["postselection_records"], 0),
        _expect("camp_candidate_generation_effect_records_zero", input_summary["combined"]["camp_candidate_generation_effect_records"], 0),
        _expect("dp_modification_records_zero", input_summary["combined"]["dp_modification_records"], 0),
        _expect("selected_index_counts", input_summary["combined"]["selected_index_counts"], {"0": expected_total_records}),
        _expect("executed_index_counts", input_summary["combined"]["executed_index_counts"], {"0": expected_total_records}),
        _check("usable_feasible_records_present", input_summary["combined"]["usable_feasible_records"] > 0, input_summary["combined"]["usable_feasible_records"], "> 0"),
        _check("prior_eval_tensor_overlap_within_limit", overlap["prior_hashes_in_evaluation_rate"] <= max_prior_eval_tensor_overlap_rate, overlap["prior_hashes_in_evaluation_rate"], f"<= {max_prior_eval_tensor_overlap_rate}"),
        _expect("label_source_dp_reward", label_source, "dp_reward"),
        _expect("reward_key_quality_without_progress", reward_key, "quality_without_progress"),
        _expect("reward_progress_weight_2", float(reward_progress_weight), 2.0),
        _expect("command_plan_schema", command_plan.get("schema_version"), COMMAND_PLAN_SCHEMA_VERSION),
        _expect("command_plan_training_not_executed", command_plan.get("training_execution_performed"), False),
        _expect("command_plan_label_source", command_plan.get("label_source"), "dp_reward"),
        _expect("command_plan_reward_key", command_plan.get("reward_key"), "quality_without_progress"),
        _expect("command_plan_requires_contract", command_plan.get("require_dp_native_training_data_contract"), True),
        _expect("command_plan_requires_atom_schema", command_plan.get("require_atom_schema"), True),
        _expect("command_plan_selection_log_count", command_plan.get("selection_log_count"), expected_total_logs),
        _check("command_contains_required_training_flags", all(token in command for token in REQUIRED_TRAINING_FLAGS), command, REQUIRED_TRAINING_FLAGS),
        _check("command_excludes_forbidden_tokens", not any(token in command for token in FORBIDDEN_COMMAND_TOKENS), command, "no forbidden tokens"),
        _check("trainer_uses_contract_preflight", "_run_dp_native_training_data_contract_preflight" in trainer_text, "present" if "_run_dp_native_training_data_contract_preflight" in trainer_text else "missing", "present"),
        _check("trainer_validates_atom_schema", "validate_atom_schema" in trainer_text, "present" if "validate_atom_schema" in trainer_text else "missing", "present"),
        _check("trainer_softmax_simplex_weights", "weights = exp_logits / np.sum(exp_logits)" in trainer_text and "weights /= np.sum(weights)" in trainer_text, "softmax/simplex evidence", "present"),
    ]
    return checks


def _summarize_sources(
    *,
    prior_logs: list[Path],
    eval_logs: list[Path],
    prior_output_dir: Path,
    prior_relative_paths: dict[str, str],
    evaluation_output_dir: Path,
    reward_key: str,
    reward_progress_weight: float,
) -> dict[str, Any]:
    prior = _summarize_records(
        logs=prior_logs,
        root=prior_output_dir,
        relative_paths=prior_relative_paths,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
    )
    evaluation = _summarize_records(
        logs=eval_logs,
        root=evaluation_output_dir,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
    )
    combined = _merge_summaries(prior, evaluation)
    return {"prior": prior, "evaluation": evaluation, "combined": combined}


def _summarize_records(
    *,
    logs: list[Path],
    root: Path,
    relative_paths: dict[str, str] | None = None,
    reward_key: str,
    reward_progress_weight: float,
) -> dict[str, Any]:
    records_total = 0
    usable_feasible_records = 0
    multi_feasible_records = 0
    all_infeasible_records = 0
    formal_seed_records = 0
    route_records: Counter[str] = Counter()
    seed_records: Counter[str] = Counter()
    candidate_count_values: Counter[str] = Counter()
    atom_schema_versions: Counter[str] = Counter()
    atom_count_values: Counter[str] = Counter()
    feasible_count_distribution: Counter[str] = Counter()
    selected_index_counts: Counter[str] = Counter()
    executed_index_counts: Counter[str] = Counter()
    closed_loop_outcome_records = 0
    reference_blend_enabled_records = 0
    guidance_enabled_records = 0
    postselection_records = 0
    camp_candidate_generation_effect_records = 0
    dp_modification_records = 0
    finite_reward_records = 0
    default_off_shadow_selector_valid_records = 0
    tensor_hash_count = 0

    for log_path in logs:
        relative_hint = _dict(relative_paths).get(str(log_path))
        meta = _metadata_from_log_path(log_path, root, relative_path=relative_hint)
        for record in _load_json_list(log_path):
            records_total += 1
            route_records[meta["route"]] += 1
            if meta["seed"] is not None:
                seed_records[str(meta["seed"])] += 1
                if int(meta["seed"]) in FORMAL_SEEDS:
                    formal_seed_records += 1
            candidate_count = _candidate_count(record)
            atom_names = record.get("atom_names")
            atom_count = len(atom_names) if isinstance(atom_names, list) else 0
            candidate_count_values[str(candidate_count)] += 1
            atom_schema_versions[str(record.get("atom_schema_version"))] += 1
            atom_count_values[str(atom_count)] += 1

            feasible_mask = record.get("feasible_mask")
            feasible_count = (
                sum(1 for value in feasible_mask if value is True)
                if isinstance(feasible_mask, list)
                else 0
            )
            feasible_count_distribution[str(feasible_count)] += 1
            if feasible_count:
                usable_feasible_records += 1
            if feasible_count >= 2:
                multi_feasible_records += 1
            if feasible_count == 0:
                all_infeasible_records += 1

            selected_index_counts[str(record.get("selected_index"))] += 1
            executed_index_counts[str(record.get("executed_index"))] += 1
            if record.get("candidate_closed_loop_outcomes") is not None:
                closed_loop_outcome_records += 1
            if record.get("candidate_reference_blend_steps") is not None:
                reference_blend_enabled_records += 1
            if any(record.get(field) is not None for field in POSTSELECTION_FIELDS):
                postselection_records += 1
            generation = _dict(record.get("candidate_generation_contract"))
            if bool(generation.get("guidance_enabled")):
                guidance_enabled_records += 1
            provenance = _dict(record.get("camp_candidate_tensor_provenance"))
            if bool(provenance.get("candidate_generation_effect")):
                camp_candidate_generation_effect_records += 1
            if bool(provenance.get("dp_modification_authorized")) or bool(
                generation.get("changes_diffusion_planner_weights")
            ):
                dp_modification_records += 1
            if _default_off_shadow_selector_valid(record, candidate_count=candidate_count):
                default_off_shadow_selector_valid_records += 1
            if _record_has_finite_reward(
                record,
                candidate_count=candidate_count,
                reward_key=reward_key,
                reward_progress_weight=reward_progress_weight,
            ):
                finite_reward_records += 1
            if _candidate_tensor_hash(record) is not None:
                tensor_hash_count += 1

    return {
        "selection_log_count": len(logs),
        "records_total": records_total,
        "usable_feasible_records": usable_feasible_records,
        "multi_feasible_records": multi_feasible_records,
        "all_infeasible_records": all_infeasible_records,
        "records_dropped_without_feasible_candidate_by_static_training": all_infeasible_records,
        "formal_seed_records": formal_seed_records,
        "route_records": dict(sorted(route_records.items())),
        "seed_records": dict(sorted(seed_records.items())),
        "candidate_count_values": dict(sorted(candidate_count_values.items())),
        "atom_schema_versions": dict(sorted(atom_schema_versions.items())),
        "atom_count_values": dict(sorted(atom_count_values.items())),
        "feasible_count_distribution": dict(sorted(feasible_count_distribution.items())),
        "selected_index_counts": dict(sorted(selected_index_counts.items())),
        "executed_index_counts": dict(sorted(executed_index_counts.items())),
        "closed_loop_outcome_records": closed_loop_outcome_records,
        "reference_blend_enabled_records": reference_blend_enabled_records,
        "guidance_enabled_records": guidance_enabled_records,
        "postselection_records": postselection_records,
        "camp_candidate_generation_effect_records": camp_candidate_generation_effect_records,
        "dp_modification_records": dp_modification_records,
        "finite_reward_records": finite_reward_records,
        "default_off_shadow_selector_valid_records": default_off_shadow_selector_valid_records,
        "candidate_tensor_hash_records": tensor_hash_count,
    }


def _merge_summaries(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    additive_keys = (
        "selection_log_count",
        "records_total",
        "usable_feasible_records",
        "multi_feasible_records",
        "all_infeasible_records",
        "records_dropped_without_feasible_candidate_by_static_training",
        "formal_seed_records",
        "closed_loop_outcome_records",
        "reference_blend_enabled_records",
        "guidance_enabled_records",
        "postselection_records",
        "camp_candidate_generation_effect_records",
        "dp_modification_records",
        "finite_reward_records",
        "default_off_shadow_selector_valid_records",
        "candidate_tensor_hash_records",
    )
    counter_keys = (
        "route_records",
        "seed_records",
        "candidate_count_values",
        "atom_schema_versions",
        "atom_count_values",
        "feasible_count_distribution",
        "selected_index_counts",
        "executed_index_counts",
    )
    for key in additive_keys:
        merged[key] = int(left.get(key, 0)) + int(right.get(key, 0))
    for key in counter_keys:
        counter: Counter[str] = Counter()
        counter.update(_dict(left.get(key)))
        counter.update(_dict(right.get(key)))
        merged[key] = dict(sorted(counter.items()))
    return merged


def _selection_manifest(
    *,
    prior_output_dir: Path,
    prior_selection_manifest_json: Path | None,
    prior_relative_paths: dict[str, str],
    evaluation_output_dir: Path,
    prior_logs: list[Path],
    eval_logs: list[Path],
    input_summary: dict[str, Any],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    entries = []
    for source, root, logs in (
        ("prior", prior_output_dir, prior_logs),
        ("evaluation", evaluation_output_dir, eval_logs),
    ):
        for path in logs:
            rows = _load_json_list(path)
            relative_path = (
                prior_relative_paths.get(str(path))
                if source == "prior"
                else None
            )
            entries.append(
                {
                    "source": source,
                    "path": str(path),
                    "relative_path": relative_path or _relative_to_root(path, root),
                    "sha256": _sha256(path),
                    "records": len(rows),
                }
            )
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "camp_head": current_camp_head,
        "dp_head": current_dp_head,
        "prior_output_dir": str(prior_output_dir),
        "prior_selection_manifest_json": (
            str(prior_selection_manifest_json)
            if prior_selection_manifest_json is not None
            else None
        ),
        "evaluation_output_dir": str(evaluation_output_dir),
        "selection_log_count": len(entries),
        "records_total": input_summary["combined"]["records_total"],
        "entries": entries,
        "read_only": True,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "training_executed": False,
    }


def _command_plan(
    *,
    python_executable: str,
    trainer_py: Path,
    selection_logs: list[Path],
    planned_training_output_dir: Path,
    label_source: str,
    reward_key: str,
    reward_progress_weight: float,
    epochs: int,
    lr: float,
    l2_reg: float,
    scale_percentile: float,
) -> dict[str, Any]:
    args = [
        python_executable,
        str(trainer_py),
    ]
    for path in selection_logs:
        args.extend(["--selection_log", str(path)])
    args.extend(
        [
            "--output_dir",
            str(planned_training_output_dir),
            "--label_source",
            label_source,
            "--reward_key",
            reward_key,
            "--reward_progress_weight",
            _float_arg(reward_progress_weight),
            "--epochs",
            str(int(epochs)),
            "--lr",
            _float_arg(lr),
            "--l2_reg",
            _float_arg(l2_reg),
            "--scale_percentile",
            _float_arg(scale_percentile),
            "--require_dp_native_training_data_contract",
            "--require_atom_schema",
        ]
    )
    command = " ".join(shlex.quote(arg) for arg in args)
    return {
        "schema_version": COMMAND_PLAN_SCHEMA_VERSION,
        "training_execution_performed": False,
        "selection_log_count": len(selection_logs),
        "planned_training_output_dir": str(planned_training_output_dir),
        "label_source": label_source,
        "reward_key": reward_key,
        "reward_progress_weight": float(reward_progress_weight),
        "epochs": int(epochs),
        "lr": float(lr),
        "l2_reg": float(l2_reg),
        "scale_percentile": float(scale_percentile),
        "require_dp_native_training_data_contract": True,
        "require_atom_schema": True,
        "command_args": args,
        "command": command,
        "forbidden_tokens_absent": not any(
            token in command for token in FORBIDDEN_COMMAND_TOKENS
        ),
    }


def _tensor_overlap(prior_logs: list[Path], eval_logs: list[Path]) -> dict[str, Any]:
    prior_hashes = _hashes_from_logs(prior_logs)
    eval_hashes = _hashes_from_logs(eval_logs)
    eval_set = set(eval_hashes)
    overlap_count = sum(1 for value in prior_hashes if value in eval_set)
    prior_unique = len(set(prior_hashes))
    eval_unique = len(set(eval_hashes))
    unique_intersection = len(set(prior_hashes).intersection(eval_set))
    return {
        "prior_hash_count": len(prior_hashes),
        "prior_unique_hash_count": prior_unique,
        "evaluation_hash_count": len(eval_hashes),
        "evaluation_unique_hash_count": eval_unique,
        "prior_hashes_in_evaluation_count": overlap_count,
        "prior_hashes_in_evaluation_rate": float(overlap_count / len(prior_hashes))
        if prior_hashes
        else 0.0,
        "unique_intersection_count": unique_intersection,
        "unique_intersection_rate": float(unique_intersection / prior_unique)
        if prior_unique
        else 0.0,
    }


def _hashes_from_logs(logs: list[Path]) -> list[str]:
    hashes: list[str] = []
    for log in logs:
        for record in _load_json_list(log):
            value = _candidate_tensor_hash(record)
            if value is not None:
                hashes.append(value)
    return hashes


def _candidate_tensor_hash(record: dict[str, Any]) -> str | None:
    selector = _dict(record.get("default_off_shadow_selector"))
    tensor_hash = _dict(selector.get("candidate_tensor_hash"))
    value = tensor_hash.get("sha256")
    if _is_sha256(value):
        return value
    provenance = _dict(record.get("camp_candidate_tensor_provenance"))
    for key in ("post_camp_selector_tensor", "pre_camp_scoring_tensor"):
        value = _dict(provenance.get(key)).get("sha256")
        if _is_sha256(value):
            return value
    return None


def _default_off_shadow_selector_valid(
    record: dict[str, Any],
    *,
    candidate_count: int,
) -> bool:
    payload = _dict(record.get("default_off_shadow_selector"))
    tensor_hash = _dict(payload.get("candidate_tensor_hash"))
    expected = {
        "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "enabled": True,
        "default_off": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "score_expression": SCORE_EXPRESSION,
        "selection_effect": False,
        "online_selector_change": False,
        "artifact_contract_ready": True,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False
    if payload.get("failed_closed_reason") is not None:
        return False
    if payload.get("executed_index") != record.get("executed_index"):
        return False
    if payload.get("executed_index") != 0 or record.get("selected_index") != 0:
        return False
    if payload.get("shadow_selected_index") != record.get("shadow_selected_index"):
        return False
    return (
        _is_sha256(tensor_hash.get("sha256"))
        and tensor_hash.get("shape") == [candidate_count, 80, 4]
        and tensor_hash.get("dtype") == "float32"
        and tensor_hash.get("hash_input") == "contiguous_candidate_tensor_bytes"
        and tensor_hash.get("nan_policy") == "preserve_tensor_bytes"
    )


def _record_has_finite_reward(
    record: dict[str, Any],
    *,
    candidate_count: int,
    reward_key: str,
    reward_progress_weight: float,
) -> bool:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        return False
    for reward in rewards:
        if not isinstance(reward, dict):
            return False
        try:
            if reward_key == "quality_without_progress":
                value = float(reward["total"]) - reward_progress_weight * float(
                    reward["progress"]
                )
            else:
                value = float(reward[reward_key])
        except (KeyError, TypeError, ValueError):
            return False
        if not math.isfinite(value):
            return False
    return True


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report.get("training_input_summary", {})
    combined = _dict(summary.get("combined"))
    overlap = _dict(report.get("candidate_tensor_overlap"))
    lines = [
        "# V13 Static DP-Reward Eval Plus Prior Training Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{','.join(decision['failed_checks'])}`",
        f"- Combined selection logs: `{combined.get('selection_log_count')}`",
        f"- Combined records: `{combined.get('records_total')}`",
        f"- Usable feasible records: `{combined.get('usable_feasible_records')}`",
        f"- Dropped without feasible candidate: `{combined.get('all_infeasible_records')}`",
        f"- Prior/eval tensor overlap rate: `{overlap.get('prior_hashes_in_evaluation_rate')}`",
        "",
        "This is a preflight-only gate. It writes a fixed selection-log manifest "
        "and a later training command plan. It does not execute training, replay, "
        "candidate generation, DP modification, promotion, deployment, or any "
        "safety/CAMP-over-DP claim.",
        "",
    ]
    if combined:
        lines.extend(
            [
                "## Combined Summary",
                "",
                "```json",
                json.dumps(
                    {
                        "route_records": combined.get("route_records"),
                        "seed_records": combined.get("seed_records"),
                        "feasible_count_distribution": combined.get(
                            "feasible_count_distribution"
                        ),
                        "candidate_tensor_overlap": overlap,
                    },
                    indent=2,
                    sort_keys=True,
                ),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def render_runbook(report: dict[str, Any]) -> str:
    command = report["training_command_plan"]["command"]
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "# Generated by a preflight-only gate. Execute only after the audit EOF",
            "# authorizes the corresponding training_execution_only gate.",
            command,
            "",
        ]
    )


def _decision(
    passed: bool,
    failed_checks: list[str],
    *,
    enabled: bool,
    authorized_next_work: str,
) -> dict[str, Any]:
    if not enabled:
        status = DISABLED_STATUS
    else:
        status = READY_STATUS if passed else REJECT_STATUS
    return {
        "status": status,
        "passed": bool(passed) if enabled else False,
        "failed_checks": failed_checks,
        "authorized_next_work": authorized_next_work if passed and enabled else None,
        "static_dp_reward_training_preflight_complete": bool(passed and enabled),
        "static_dp_reward_training_execution_authorized_next": bool(passed and enabled),
        "training_executed": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "formal_seeds_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _selection_logs(root: Path) -> list[Path]:
    return sorted(root.rglob("camp_selection_log.json")) if root.exists() else []


def _load_selection_manifest(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return loaded


def _selection_logs_from_manifest(manifest: dict[str, Any]) -> list[Path]:
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return []
    paths: list[Path] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        value = entry.get("path")
        if isinstance(value, str):
            paths.append(Path(value))
    return sorted(paths)


def _manifest_relative_paths(manifest: dict[str, Any]) -> dict[str, str]:
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return {}
    relative_paths: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        relative_path = entry.get("relative_path")
        if isinstance(path, str) and isinstance(relative_path, str):
            relative_paths[str(Path(path))] = relative_path
    return relative_paths


def _relative_to_root(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list) or not all(isinstance(row, dict) for row in loaded):
        raise ValueError(f"{path} must contain a list of JSON objects.")
    return loaded


def _candidate_count(record: dict[str, Any]) -> int:
    value = record.get("num_candidates")
    if isinstance(value, int):
        return int(value)
    atoms = record.get("atoms")
    return len(atoms) if isinstance(atoms, list) else 0


def _metadata_from_log_path(
    path: Path,
    root: Path,
    *,
    relative_path: str | None = None,
) -> dict[str, Any]:
    if relative_path:
        parts = Path(relative_path).parts
    else:
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            parts = path.parts
    route = parts[0] if len(parts) >= 1 else "unknown"
    seed: int | None = None
    for part in parts:
        if part.startswith("seed_"):
            try:
                seed = int(part.split("_", 1)[1])
            except ValueError:
                seed = None
    return {"route": route, "seed": seed}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _latest_audit_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in reversed(text.splitlines()):
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _float_arg(value: float) -> str:
    return str(float(value))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


if __name__ == "__main__":
    raise SystemExit(main())
