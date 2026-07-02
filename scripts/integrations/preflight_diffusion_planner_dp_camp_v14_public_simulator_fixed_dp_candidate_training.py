#!/usr/bin/env python3
"""V14 public-simulator fixed-DP candidate CAMP training preflight.

This gate validates the data-preparation training input manifest and writes a
guarded static CAMP training command plan. It does not execute training, run
replay, generate candidates, modify DP, promote artifacts, deploy, or make
safety/CAMP-over-DP claims.
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


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = "dp_camp_v14_public_simulator_fixed_dp_candidate_training_preflight_v1"
SELECTION_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_fixed_dp_candidate_training_selection_manifest_v1"
)
COMMAND_PLAN_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_fixed_dp_candidate_training_command_plan_v1"
)
EXPECTED_TRAINING_INPUT_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_fixed_dp_candidate_training_input_manifest_v1"
)
EXPECTED_CURRENT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_ready"
)
AUTHORIZED_CURRENT_WORK = "public_simulator_fixed_dp_candidate_generation_training_preflight"
AUTHORIZED_NEXT_WORK = "public_simulator_fixed_dp_candidate_generation_training_execution"
READY_STATUS = "public_simulator_fixed_dp_candidate_generation_training_preflight_ready"
REJECT_STATUS = "public_simulator_fixed_dp_candidate_generation_training_preflight_rejected"
EXPECTED_LOG_COUNT = 32
EXPECTED_RECORDS = 3200
EXPECTED_NUM_CANDIDATES = 8
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
    "2",
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training_input_manifest_json", type=Path, required=True)
    parser.add_argument("--data_preparation_artifact_dir", type=Path, required=True)
    parser.add_argument("--trainer_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--planned_training_output_dir", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--python_executable", default="python")
    parser.add_argument("--label_source", default="dp_reward")
    parser.add_argument("--reward_key", default="quality_without_progress")
    parser.add_argument("--reward_progress_weight", type=float, default=2.0)
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--lr", type=float, default=0.2)
    parser.add_argument("--l2_reg", type=float, default=0.01)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        training_input_manifest_json=args.training_input_manifest_json,
        data_preparation_artifact_dir=args.data_preparation_artifact_dir,
        trainer_py=args.trainer_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        planned_training_output_dir=args.planned_training_output_dir,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        python_executable=args.python_executable,
        label_source=args.label_source,
        reward_key=args.reward_key,
        reward_progress_weight=args.reward_progress_weight,
        epochs=args.epochs,
        lr=args.lr,
        l2_reg=args.l2_reg,
        scale_percentile=args.scale_percentile,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    training_input_manifest_json: Path,
    data_preparation_artifact_dir: Path,
    trainer_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    planned_training_output_dir: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    python_executable: str = "python",
    label_source: str = "dp_reward",
    reward_key: str = "quality_without_progress",
    reward_progress_weight: float = 2.0,
    epochs: int = 1000,
    lr: float = 0.2,
    l2_reg: float = 0.01,
    scale_percentile: float = 95.0,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    training_input_manifest_json = training_input_manifest_json.resolve()
    data_preparation_artifact_dir = data_preparation_artifact_dir.resolve()
    trainer_py = trainer_py.resolve()
    v14_audit_md = v14_audit_md.resolve()
    current_status_md = current_status_md.resolve()
    planned_training_output_dir = planned_training_output_dir.resolve()
    output_dir = output_dir.resolve()

    manifest = _read_json_dict(training_input_manifest_json)
    selection_logs = [Path(path) for path in manifest.get("selection_logs", []) if isinstance(path, str)]
    clean_contract = validate_logs(selection_logs) if selection_logs else _empty_contract()
    input_summary = _summarize_logs(
        selection_logs=selection_logs,
        source_root=Path(str(manifest.get("source_execution_output_root", ""))),
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
    )
    selection_manifest = _selection_manifest(
        source_manifest_json=training_input_manifest_json,
        source_manifest=manifest,
        selection_logs=selection_logs,
        input_summary=input_summary,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    command_plan = _command_plan(
        python_executable=python_executable,
        trainer_py=trainer_py,
        selection_logs=selection_logs,
        planned_training_output_dir=planned_training_output_dir,
        label_source=label_source,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
        epochs=epochs,
        lr=lr,
        l2_reg=l2_reg,
        scale_percentile=scale_percentile,
    )
    checks = _checks(
        training_input_manifest_json=training_input_manifest_json,
        data_preparation_artifact_dir=data_preparation_artifact_dir,
        trainer_py=trainer_py,
        v14_audit_md=v14_audit_md,
        current_status_md=current_status_md,
        planned_training_output_dir=planned_training_output_dir,
        manifest=manifest,
        selection_logs=selection_logs,
        clean_contract=clean_contract,
        input_summary=input_summary,
        command_plan=command_plan,
        v14_text=_read_text(v14_audit_md),
        status_text=_read_text(current_status_md),
        trainer_text=_read_text(trainer_py),
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        label_source=label_source,
        reward_key=reward_key,
        reward_progress_weight=reward_progress_weight,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "training_preflight_only": True,
            "training_execution": False,
            "selection_manifest_materialized": bool(passed),
            "training_command_plan_materialized": bool(passed),
            "fixed_dp_candidate_generation_executed_by_source": True,
            "data_preparation_preflight_executed_by_source": True,
            "replay_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "inputs": {
            "training_input_manifest_json": str(training_input_manifest_json),
            "data_preparation_artifact_dir": str(data_preparation_artifact_dir),
            "trainer_py": str(trainer_py),
            "v14_audit_md": str(v14_audit_md),
            "current_status_md": str(current_status_md),
            "planned_training_output_dir": str(planned_training_output_dir),
            "output_dir": str(output_dir),
        },
        "source_hashes": {
            "training_input_manifest_json_sha256": _sha256(training_input_manifest_json)
            if training_input_manifest_json.is_file()
            else None,
            "trainer_py_sha256": _sha256(trainer_py) if trainer_py.is_file() else None,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "training_input_summary": input_summary,
        "clean_contract": {
            "passed": bool(clean_contract.get("passed")),
            "records": int(clean_contract.get("records", 0)),
            "failed_records": len(clean_contract.get("failed_records", [])),
            "future_training_input_contract_satisfied": bool(
                clean_contract.get("future_training_input_contract_satisfied")
            ),
        },
        "selection_manifest": selection_manifest,
        "training_command_plan": command_plan,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    passed = bool(report["final_decision"]["passed"])
    if passed:
        _write_json(output_dir / "selection_manifest.json", report["selection_manifest"])
        _write_json(output_dir / "training_command_plan.json", report["training_command_plan"])
    slim = dict(report)
    slim.pop("selection_manifest", None)
    slim.pop("training_command_plan", None)
    _write_json(output_dir / "training_preflight_report.json", slim)
    (output_dir / "training_preflight_report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    if passed:
        (output_dir / "run_training_after_authorization.sh").write_text(
            render_runbook(report),
            encoding="utf-8",
        )
    _write_sha256sums(output_dir)


def _checks(
    *,
    training_input_manifest_json: Path,
    data_preparation_artifact_dir: Path,
    trainer_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    planned_training_output_dir: Path,
    manifest: dict[str, Any],
    selection_logs: list[Path],
    clean_contract: dict[str, Any],
    input_summary: dict[str, Any],
    command_plan: dict[str, Any],
    v14_text: str,
    status_text: str,
    trainer_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    label_source: str,
    reward_key: str,
    reward_progress_weight: float,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    command = str(command_plan.get("command", ""))
    checks = [
        _expect("training_input_manifest_exists", training_input_manifest_json.is_file(), True),
        _expect("data_preparation_artifact_dir_exists", data_preparation_artifact_dir.is_dir(), True),
        _expect("trainer_py_exists", trainer_py.is_file(), True),
        _expect("v14_audit_exists", v14_audit_md.is_file(), True),
        _expect("current_status_exists", current_status_md.is_file(), True),
        _expect("planned_training_output_dir_absent", planned_training_output_dir.exists(), False),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), EXPECTED_CURRENT_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), authorized_current_work),
        _expect("status_doc_current_status", EXPECTED_CURRENT_STATUS in status_text, True),
        _expect("status_doc_next_work", authorized_current_work in status_text, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("manifest_schema", manifest.get("schema_version"), EXPECTED_TRAINING_INPUT_MANIFEST_SCHEMA_VERSION),
        _expect("manifest_fixed_dp_candidate_tensor_only", manifest.get("fixed_dp_candidate_tensor_only"), True),
        _expect("manifest_candidate_operation", manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("manifest_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("manifest_nonnegative_simplex", manifest.get("approved_atoms_nonnegative_simplex_only"), True),
        _expect("manifest_master_convexity", manifest.get("simplex_cvar_l2_master_convexity_preserved"), True),
        _expect("manifest_formal_seeds_excluded", manifest.get("formal_seeds_11_12_13_excluded"), True),
        _expect("manifest_expected_selection_log_count", manifest.get("expected_selection_log_count"), EXPECTED_LOG_COUNT),
        _expect("manifest_expected_records", manifest.get("expected_records"), EXPECTED_RECORDS),
        _expect("manifest_expected_num_candidates", manifest.get("expected_num_candidates"), EXPECTED_NUM_CANDIDATES),
        _expect("selection_log_count", len(selection_logs), EXPECTED_LOG_COUNT),
        _expect("clean_contract_passed", clean_contract.get("passed"), True),
        _expect("clean_contract_records", clean_contract.get("records"), EXPECTED_RECORDS),
        _expect("clean_contract_failed_records_zero", len(clean_contract.get("failed_records", [])), 0),
        _expect("clean_contract_future_training_input", clean_contract.get("future_training_input_contract_satisfied"), True),
        _expect("summary_record_count", input_summary["records_total"], EXPECTED_RECORDS),
        _expect("summary_candidate_count_values", input_summary["candidate_count_values"], {str(EXPECTED_NUM_CANDIDATES): EXPECTED_RECORDS}),
        _expect("summary_formal_seed_records_zero", input_summary["formal_seed_records"], 0),
        _expect("summary_finite_reward_records", input_summary["finite_reward_records"], EXPECTED_RECORDS),
        _expect("summary_default_off_valid_records", input_summary["default_off_shadow_selector_valid_records"], EXPECTED_RECORDS),
        _expect("summary_closed_loop_outcome_records_zero", input_summary["closed_loop_outcome_records"], 0),
        _expect("summary_reference_blend_records_zero", input_summary["reference_blend_enabled_records"], 0),
        _expect("summary_guidance_records_zero", input_summary["guidance_enabled_records"], 0),
        _expect("summary_postselection_records_zero", input_summary["postselection_records"], 0),
        _expect("summary_camp_generation_effect_zero", input_summary["camp_candidate_generation_effect_records"], 0),
        _expect("summary_dp_modification_records_zero", input_summary["dp_modification_records"], 0),
        _expect("summary_selected_index_counts", input_summary["selected_index_counts"], {"0": EXPECTED_RECORDS}),
        _expect("summary_executed_index_counts", input_summary["executed_index_counts"], {"0": EXPECTED_RECORDS}),
        _check("summary_uses_approved_atom_schema", bool(input_summary["atom_schema_versions"]), input_summary["atom_schema_versions"], "nonempty approved schemas"),
        _check("summary_usable_feasible_records_present", input_summary["usable_feasible_records"] > 0, input_summary["usable_feasible_records"], "> 0"),
        _expect("label_source_dp_reward", label_source, "dp_reward"),
        _expect("reward_key_quality_without_progress", reward_key, "quality_without_progress"),
        _expect("reward_progress_weight_2", float(reward_progress_weight), 2.0),
        _expect("command_plan_schema", command_plan.get("schema_version"), COMMAND_PLAN_SCHEMA_VERSION),
        _expect("command_plan_training_not_executed", command_plan.get("training_execution_performed"), False),
        _expect("command_plan_label_source", command_plan.get("label_source"), "dp_reward"),
        _expect("command_plan_reward_key", command_plan.get("reward_key"), "quality_without_progress"),
        _expect("command_plan_requires_contract", command_plan.get("require_dp_native_training_data_contract"), True),
        _expect("command_plan_requires_atom_schema", command_plan.get("require_atom_schema"), True),
        _expect("command_plan_selection_log_count", command_plan.get("selection_log_count"), EXPECTED_LOG_COUNT),
        _check("command_contains_required_training_flags", all(token in command for token in REQUIRED_TRAINING_FLAGS), command, REQUIRED_TRAINING_FLAGS),
        _check("command_excludes_forbidden_tokens", not any(token in command for token in FORBIDDEN_COMMAND_TOKENS), command, "no forbidden tokens"),
        _check("trainer_uses_contract_preflight", "_run_dp_native_training_data_contract_preflight" in trainer_text, "present" if "_run_dp_native_training_data_contract_preflight" in trainer_text else "missing", "present"),
        _check("trainer_validates_atom_schema", "validate_atom_schema" in trainer_text, "present" if "validate_atom_schema" in trainer_text else "missing", "present"),
        _check("trainer_softmax_simplex_weights", "weights = exp_logits / np.sum(exp_logits)" in trainer_text and "weights /= np.sum(weights)" in trainer_text, "softmax/simplex evidence", "present"),
    ]
    forbidden = _dict(manifest.get("forbidden_operations"))
    for name in (
        "candidate_generation_by_camp",
        "trajectory_generation_by_camp",
        "trajectory_modification_by_camp",
        "reference_blend",
        "guidance",
        "postprocess_or_postselection",
        "closed_loop_outcome_input",
        "dp_modification",
        "selector_promotion",
        "atom_promotion",
        "deployment",
        "safety_benefit_claim",
        "camp_over_dp_top1_claim",
    ):
        checks.append(_expect(f"manifest_forbids_{name}", forbidden.get(name), False))
    for log in selection_logs:
        checks.append(_expect("selection_log_exists", log.is_file(), True))
    return checks


def _selection_manifest(
    *,
    source_manifest_json: Path,
    source_manifest: dict[str, Any],
    selection_logs: list[Path],
    input_summary: dict[str, Any],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    entries = []
    for path in selection_logs:
        rows = _load_json_list(path)
        entries.append(
            {
                "path": str(path),
                "sha256": _sha256(path),
                "records": len(rows),
            }
        )
    return {
        "schema_version": SELECTION_MANIFEST_SCHEMA_VERSION,
        "source_training_input_manifest_json": str(source_manifest_json),
        "source_execution_output_root": source_manifest.get("source_execution_output_root"),
        "source_zero_overlap_artifact_dir": source_manifest.get("source_zero_overlap_artifact_dir"),
        "camp_head": current_camp_head,
        "dp_head": current_dp_head,
        "selection_log_count": len(entries),
        "records_total": input_summary["records_total"],
        "usable_feasible_records": input_summary["usable_feasible_records"],
        "all_infeasible_records": input_summary["all_infeasible_records"],
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
    args = [python_executable, str(trainer_py)]
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


def _summarize_logs(
    *,
    selection_logs: list[Path],
    source_root: Path,
    reward_key: str,
    reward_progress_weight: float,
) -> dict[str, Any]:
    records_total = 0
    usable_feasible_records = 0
    all_infeasible_records = 0
    formal_seed_records = 0
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
    candidate_tensor_hash_records = 0

    for log_path in selection_logs:
        meta = _metadata_from_log_path(log_path, source_root)
        for record in _load_json_list(log_path):
            records_total += 1
            if meta["seed"] is not None and int(meta["seed"]) in FORMAL_SEEDS:
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
            else:
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
                candidate_tensor_hash_records += 1

    return {
        "selection_log_count": len(selection_logs),
        "records_total": records_total,
        "usable_feasible_records": usable_feasible_records,
        "all_infeasible_records": all_infeasible_records,
        "records_dropped_without_feasible_candidate_by_static_training": all_infeasible_records,
        "formal_seed_records": formal_seed_records,
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
        "candidate_tensor_hash_records": candidate_tensor_hash_records,
    }


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": sorted(failed),
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "training_preflight_complete": bool(passed),
        "training_execution_authorized_next": bool(passed),
        "training_executed": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
    }


def _failure_class(failed: list[str]) -> str:
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("clean_contract" in check for check in failed):
        return "training_input_contract_failure"
    if any("command" in check or "trainer" in check for check in failed):
        return "training_command_contract_failure"
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    return "training_preflight_contract_failure"


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["training_input_summary"]
    return "\n".join(
        [
            "# V14 Public Simulator Fixed-DP CAMP Training Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Selection logs: `{summary['selection_log_count']}`",
            f"- Records: `{summary['records_total']}`",
            f"- Usable feasible records: `{summary['usable_feasible_records']}`",
            f"- Dropped all-infeasible records: `{summary['all_infeasible_records']}`",
            f"- Atom schemas: `{summary['atom_schema_versions']}`",
            f"- Training execution authorized next: `{decision['training_execution_authorized_next']}`",
            "",
            "This is a preflight-only gate. It writes a fixed selection-log "
            "manifest and a later training command plan. It does not execute "
            "training, replay, candidate generation, DP modification, promotion, "
            "deployment, or any safety/CAMP-over-DP claim.",
            "",
        ]
    )


def render_runbook(report: dict[str, Any]) -> str:
    command = report["training_command_plan"]["command"]
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "# Generated by a preflight-only gate. Execute only after the audit EOF",
            "# authorizes public_simulator_fixed_dp_candidate_generation_training_execution.",
            command,
            "",
        ]
    )


def _empty_contract() -> dict[str, Any]:
    return {
        "passed": False,
        "records": 0,
        "failed_records": [{"errors": ["selection_logs_missing"]}],
        "future_training_input_contract_satisfied": False,
    }


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list) or not all(isinstance(row, dict) for row in loaded):
        raise ValueError(f"{path} must contain a list of JSON objects.")
    return loaded


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    lines = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    matches = [line.split("=", 1)[1].strip() for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": observed,
        "expected": expected,
    }


def _check(name: str, passed: bool, observed: Any, expected: Any = True) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _candidate_count(record: dict[str, Any]) -> int:
    value = record.get("num_candidates")
    if isinstance(value, int):
        return int(value)
    atoms = record.get("atoms")
    return len(atoms) if isinstance(atoms, list) else 0


def _metadata_from_log_path(path: Path, root: Path) -> dict[str, Any]:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    seed = None
    for part in parts:
        if part.startswith("seed_"):
            try:
                seed = int(part.split("_", 1)[1])
            except ValueError:
                seed = None
    return {"seed": seed}


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
    shape = tensor_hash.get("shape")
    return (
        _is_sha256(tensor_hash.get("sha256"))
        and isinstance(shape, list)
        and len(shape) == 3
        and shape[0] == candidate_count
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


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdefABCDEF" for char in value
    )


def _float_arg(value: float) -> str:
    return f"{float(value):g}"


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
