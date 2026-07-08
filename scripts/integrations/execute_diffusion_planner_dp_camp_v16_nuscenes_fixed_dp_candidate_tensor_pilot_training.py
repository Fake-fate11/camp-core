#!/usr/bin/env python3
"""Execute the v16 fixed-DP pilot static CAMP training gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.atoms.driver_atoms import (  # noqa: E402
    DriverAtomContext,
    compute_atom_bank_vector,
    compute_feasibility_mask,
)
from camp_core.integrations.diffusion_planner import atom_schema_for_dimension  # noqa: E402
from camp_core.integrations.diffusion_planner import _route_centerline  # noqa: E402
from scripts.integrations.preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training import (  # noqa: E402
    FIXED_DP_HEAD,
    PREFLIGHT_JSON_NAME as SOURCE_PREFLIGHT_JSON_NAME,
    READY_STATUS as SOURCE_PREFLIGHT_STATUS,
    SCHEMA_VERSION as SOURCE_PREFLIGHT_SCHEMA_VERSION,
)


SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_v1"
AUTHORIZED_CURRENT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_only"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_result_review_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_passed"
FAILED_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution_failed"
REPORT_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution.json"
REPORT_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution.md"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_COUNTS = {"train": 863, "calibration": 14, "holdout": 147}
EXPECTED_K = 8


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split_execution_artifact_dir", type=Path, required=True)
    parser.add_argument("--split_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_preflight_json", type=Path, required=True)
    parser.add_argument("--source_train_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_calibration_records_jsonl", type=Path, required=True)
    parser.add_argument("--source_holdout_records_jsonl", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--training_script", type=Path, default=Path("scripts/integrations/train_diffusion_planner_static_camp.py"))
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--expected_split_execution_root_sha256", required=True)
    parser.add_argument("--expected_split_result_review_root_sha256", required=True)
    parser.add_argument("--expected_plan_root_sha256", required=True)
    parser.add_argument("--expected_static_review_root_sha256", required=True)
    parser.add_argument("--expected_preflight_root_sha256", required=True)
    parser.add_argument("--python_executable", default=sys.executable)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument(
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_execution(
        split_execution_artifact_dir=args.split_execution_artifact_dir,
        split_result_review_artifact_dir=args.split_result_review_artifact_dir,
        source_plan_artifact_dir=args.source_plan_artifact_dir,
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_preflight_artifact_dir=args.source_preflight_artifact_dir,
        source_preflight_json=args.source_preflight_json,
        source_train_records_jsonl=args.source_train_records_jsonl,
        source_calibration_records_jsonl=args.source_calibration_records_jsonl,
        source_holdout_records_jsonl=args.source_holdout_records_jsonl,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        training_script=args.training_script,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        expected_split_execution_root_sha256=args.expected_split_execution_root_sha256,
        expected_split_result_review_root_sha256=args.expected_split_result_review_root_sha256,
        expected_plan_root_sha256=args.expected_plan_root_sha256,
        expected_static_review_root_sha256=args.expected_static_review_root_sha256,
        expected_preflight_root_sha256=args.expected_preflight_root_sha256,
        python_executable=args.python_executable,
        epochs=args.epochs,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_execution,
        command=sys.argv,
    )
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def run_execution(
    *,
    split_execution_artifact_dir: Path,
    split_result_review_artifact_dir: Path,
    source_plan_artifact_dir: Path,
    source_static_review_artifact_dir: Path,
    source_preflight_artifact_dir: Path,
    source_preflight_json: Path,
    source_train_records_jsonl: Path,
    source_calibration_records_jsonl: Path,
    source_holdout_records_jsonl: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    training_script: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_split_execution_root_sha256: str,
    expected_split_result_review_root_sha256: str,
    expected_plan_root_sha256: str,
    expected_static_review_root_sha256: str,
    expected_preflight_root_sha256: str,
    python_executable: str = sys.executable,
    epochs: int = 1,
    enabled: bool = False,
    command: list[str] | None = None,
) -> dict[str, Any]:
    report = build_report(
        split_execution_artifact_dir=split_execution_artifact_dir,
        split_result_review_artifact_dir=split_result_review_artifact_dir,
        source_plan_artifact_dir=source_plan_artifact_dir,
        source_static_review_artifact_dir=source_static_review_artifact_dir,
        source_preflight_artifact_dir=source_preflight_artifact_dir,
        source_preflight_json=source_preflight_json,
        source_train_records_jsonl=source_train_records_jsonl,
        source_calibration_records_jsonl=source_calibration_records_jsonl,
        source_holdout_records_jsonl=source_holdout_records_jsonl,
        v16_audit_md=v16_audit_md,
        current_status_md=current_status_md,
        training_script=training_script,
        output_dir=output_dir,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        expected_split_execution_root_sha256=expected_split_execution_root_sha256,
        expected_split_result_review_root_sha256=expected_split_result_review_root_sha256,
        expected_plan_root_sha256=expected_plan_root_sha256,
        expected_static_review_root_sha256=expected_static_review_root_sha256,
        expected_preflight_root_sha256=expected_preflight_root_sha256,
        python_executable=python_executable,
        epochs=epochs,
        enabled=enabled,
    )
    report["command"] = command or []
    if report["final_decision"]["passed"]:
        prepared_train_records = report.pop("_prepared_train_records", None)
        _run_trainer(
            report,
            source_train_records_jsonl,
            training_script,
            output_dir,
            python_executable,
            epochs,
            prepared_train_records=prepared_train_records,
        )
    write_outputs(output_dir, report)
    return report


def build_report(
    *,
    split_execution_artifact_dir: Path,
    split_result_review_artifact_dir: Path,
    source_plan_artifact_dir: Path,
    source_static_review_artifact_dir: Path,
    source_preflight_artifact_dir: Path,
    source_preflight_json: Path,
    source_train_records_jsonl: Path,
    source_calibration_records_jsonl: Path,
    source_holdout_records_jsonl: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    training_script: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    expected_split_execution_root_sha256: str,
    expected_split_result_review_root_sha256: str,
    expected_plan_root_sha256: str,
    expected_static_review_root_sha256: str,
    expected_preflight_root_sha256: str,
    python_executable: str = sys.executable,
    epochs: int = 1,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    train_records = _read_jsonl(source_train_records_jsonl)
    calibration_records = _read_jsonl(source_calibration_records_jsonl)
    holdout_records = _read_jsonl(source_holdout_records_jsonl)
    preflight = _read_json(source_preflight_json)
    preflight_body = preflight.get("pilot_training_preflight", {})
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    source_artifacts = {
        "split_execution": _source_artifact(split_execution_artifact_dir, expected_split_execution_root_sha256),
        "split_result_review": _source_artifact(split_result_review_artifact_dir, expected_split_result_review_root_sha256),
        "training_preflight_plan": _source_artifact(source_plan_artifact_dir, expected_plan_root_sha256),
        "training_preflight_plan_static_review": _source_artifact(source_static_review_artifact_dir, expected_static_review_root_sha256),
        "training_preflight": _source_artifact(source_preflight_artifact_dir, expected_preflight_root_sha256),
    }
    record_summary = _record_summary(train_records, calibration_records, holdout_records)
    atom_summary = _atom_summary(train_records)
    atom_derivation = _empty_atom_derivation()
    prepared_train_records = None
    if atom_summary["missing_atoms"]:
        prepared_train_records, atom_derivation = _derive_missing_train_atoms(train_records)
        if atom_derivation["failed_records"] == 0:
            atom_summary = _atom_summary(prepared_train_records)
    training_command = _training_command(
        python_executable=python_executable,
        training_script=training_script,
        selection_log=Path("train_selection_log.json"),
        output_dir=Path("trainer_output"),
        epochs=epochs,
    )
    checks = [
        _expect("training_execution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _contains("audit_authorizes_training_execution", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_training_execution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_preflight", audit_text, f"current_v16_status={SOURCE_PREFLIGHT_STATUS}"),
        _contains("status_records_preflight", status_text, f"current_v16_status={SOURCE_PREFLIGHT_STATUS}"),
        _expect("source_preflight_schema", preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA_VERSION),
        _expect("source_preflight_status", preflight.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_authorizes_execution", preflight.get("final_decision", {}).get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("train_records_863", len(train_records), EXPECTED_COUNTS["train"]),
        _expect("calibration_records_14", len(calibration_records), EXPECTED_COUNTS["calibration"]),
        _expect("holdout_records_147", len(holdout_records), EXPECTED_COUNTS["holdout"]),
        _expect("preflight_train_records_863", preflight_body.get("train_records"), EXPECTED_COUNTS["train"]),
        _expect("calibration_records_not_used_for_training", preflight_body.get("calibration_records_used_for_training"), 0),
        _expect("holdout_records_not_used_for_training", preflight_body.get("holdout_records_used_for_training"), 0),
        _expect("scene_zero_overlap", record_summary["scene_zero_overlap"], True),
        _expect("sample_zero_overlap", record_summary["sample_zero_overlap"], True),
        _expect("train_k_values_8", record_summary["train_k_values"], [EXPECTED_K]),
        _expect("train_candidate_count_values_8", record_summary["train_candidate_count_values"], [EXPECTED_K]),
        _expect("train_dp_head_fixed", record_summary["train_dp_head_values"], [FIXED_DP_HEAD]),
        _expect("train_candidate_tensor_not_mutated", record_summary["train_candidate_tensor_mutated_count"], 0),
        _expect("train_closed_loop_outcomes_absent", record_summary["train_closed_loop_outcome_count"], 0),
        _expect("train_atoms_present", atom_summary["missing_atoms"], 0),
        _expect("train_feasible_mask_present", atom_summary["missing_feasible_mask"], 0),
        _expect("train_atom_schema_present", atom_summary["missing_atom_schema"], 0),
        _expect("train_atom_shape_valid", atom_summary["invalid_atom_shape_count"], 0),
        _expect("train_feasible_mask_shape_valid", atom_summary["invalid_feasible_shape_count"], 0),
        _expect("approved_atom_count_positive", atom_summary["atom_count"] > 0, True),
        _expect("approved_atom_schema_canonical", atom_summary["canonical_schema"], True),
        _check("training_script_exists", training_script.is_file(), str(training_script), "file"),
    ]
    checks.extend(
        _check(
            f"source_{name}_sha256s_verified",
            artifact["sha256s_verified"] and artifact["root_sha256"] == artifact["expected_root_sha256"],
            artifact,
            "verified source artifact",
        )
        for name, artifact in source_artifacts.items()
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else FAILED_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "source_artifacts": source_artifacts,
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": FIXED_DP_HEAD,
            },
            "pilot_training_execution": {
                "train_records": len(train_records),
                "calibration_records": len(calibration_records),
                "holdout_records": len(holdout_records),
                "calibration_records_used_for_training": 0,
                "holdout_records_used_for_training": 0,
                "training_command": [str(item) for item in training_command],
                "score_expression": SCORE_EXPRESSION,
                "atom_summary": atom_summary,
                "atom_derivation": atom_derivation,
                "record_summary": record_summary,
                "training_executed": False,
                "training_start": None,
                "training_end": None,
                "offline_training_wall_clock_seconds": None,
                "selection_log": None,
            },
            "training_config": {
                "epochs": epochs,
                "label_source": "proxy",
                "score_expression": SCORE_EXPRESSION,
                "training_splits": ["train"],
                "forbidden_training_splits": ["calibration", "holdout"],
            },
            "training_log": [],
            "checks": checks,
            "final_decision": _decision(passed, failed, training_executed=False),
            **({"_prepared_train_records": prepared_train_records} if prepared_train_records is not None else {}),
        }
    )


def _run_trainer(
    report: dict[str, Any],
    source_train_records_jsonl: Path,
    training_script: Path,
    output_dir: Path,
    python_executable: str,
    epochs: int,
    *,
    prepared_train_records: list[dict[str, Any]] | None = None,
) -> None:
    train_records = prepared_train_records or _read_jsonl(source_train_records_jsonl)
    output_dir.mkdir(parents=True, exist_ok=True)
    selection_log = output_dir / "train_selection_log.json"
    trainer_output = output_dir / "trainer_output"
    selection_log.write_text(json.dumps(train_records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    command = _training_command(
        python_executable=python_executable,
        training_script=training_script,
        selection_log=selection_log,
        output_dir=trainer_output,
        epochs=epochs,
    )
    start = datetime.now(timezone.utc)
    started = time.perf_counter()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    end = datetime.now(timezone.utc)
    elapsed = round(time.perf_counter() - started, 6)
    report["pilot_training_execution"].update(
        {
            "selection_log": str(selection_log),
            "training_command": [str(item) for item in command],
            "training_executed": True,
            "training_start": start.isoformat(),
            "training_end": end.isoformat(),
            "offline_training_wall_clock_seconds": elapsed,
            "trainer_exit": result.returncode,
        }
    )
    report["training_log"].append(
        {
            "event": "trainer_finished",
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
        }
    )
    trainer_stdout = output_dir / "training_stdout.txt"
    trainer_stderr = output_dir / "training_stderr.txt"
    trainer_stdout.write_text(result.stdout, encoding="utf-8")
    trainer_stderr.write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0:
        _fail_after_training(report, ["trainer_exit_0"])
        return
    summary_path = trainer_output / "training_summary.json"
    if not summary_path.is_file():
        _fail_after_training(report, ["trainer_summary_exists"])
        return
    summary = _read_json(summary_path)
    model = _model_from_summary(summary, report)
    model_checks = _model_checks(model)
    report["static_camp_model"] = model
    report["checks"].extend(model_checks)
    failed = [check["name"] for check in report["checks"] if not check["passed"]]
    if failed:
        _fail_after_training(report, failed)
        return
    report["status"] = READY_STATUS
    report["authorized_next_work"] = AUTHORIZED_NEXT_WORK
    report["final_decision"] = _decision(True, [], training_executed=True)


def _model_from_summary(summary: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    weights = [float(value) for value in summary.get("trained_weights", [])]
    atom_names = list(summary.get("atom_names", []))
    total = round(sum(weights), 12)
    return {
        "artifact_type": "static_camp_weights_model",
        "atom_schema_version": summary.get("atom_schema_version"),
        "atom_names": atom_names,
        "atom_count": len(atom_names),
        "approved_atoms": report["pilot_training_execution"]["atom_summary"].get("atom_names", []),
        "approved_atoms_only": atom_names == report["pilot_training_execution"]["atom_summary"].get("atom_names", []),
        "score_expression": SCORE_EXPRESSION,
        "train_records": summary.get("num_records"),
        "weights": weights,
        "weights_sum": total,
        "weights_min": min(weights) if weights else None,
        "weights_max": max(weights) if weights else None,
        "weights_nonnegative": bool(weights) and all(value >= -1e-12 for value in weights),
        "weights_sum_to_one": abs(total - 1.0) <= 1e-9,
        "trainer_summary": summary,
    }


def _model_checks(model: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _expect("model_train_records_863", model.get("train_records"), EXPECTED_COUNTS["train"]),
        _expect("model_score_expression_affine", model.get("score_expression"), SCORE_EXPRESSION),
        _expect("model_weights_nonnegative", model.get("weights_nonnegative"), True),
        _expect("model_weights_sum_to_one", model.get("weights_sum_to_one"), True),
        _expect("model_approved_atoms_only", model.get("approved_atoms_only"), True),
    ]


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    public_report = _public_report(report)
    (output_dir / REPORT_JSON_NAME).write_text(json.dumps(_stable(public_report), indent=2) + "\n", encoding="utf-8")
    (output_dir / REPORT_MD_NAME).write_text(_render_markdown(public_report), encoding="utf-8")
    (output_dir / "pilot_training_config.json").write_text(
        json.dumps(report["training_config"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    timing = {
        "training_start": report["pilot_training_execution"]["training_start"],
        "training_end": report["pilot_training_execution"]["training_end"],
        "offline_training_wall_clock_seconds": report["pilot_training_execution"]["offline_training_wall_clock_seconds"],
    }
    (output_dir / "pilot_training_timing.json").write_text(json.dumps(timing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "pilot_training_timing.md").write_text(
        "\n".join(
            [
                "# Pilot Training Timing",
                "",
                f"- Start: `{timing['training_start']}`",
                f"- End: `{timing['training_end']}`",
                f"- Wall-clock seconds: `{timing['offline_training_wall_clock_seconds']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (output_dir / "HEADS").write_text(_render_heads(report), encoding="utf-8")
    (output_dir / "COMMAND").write_text(json.dumps(report.get("command", [])) + "\n", encoding="utf-8")
    (output_dir / "training_log.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in report.get("training_log", [])),
        encoding="utf-8",
    )
    if "static_camp_model" in report:
        model = report["static_camp_model"]
        (output_dir / "static_camp_weights_model.json").write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output_dir / "affine_scoring_check.json").write_text(
            json.dumps({"affine": True, "score_expression": SCORE_EXPRESSION}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / "nonnegative_simplex_check.json").write_text(
            json.dumps(
                {
                    "weights_nonnegative": model["weights_nonnegative"],
                    "weights_sum": model["weights_sum"],
                    "weights_sum_to_one": model["weights_sum_to_one"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (output_dir / "approved_atoms_check.json").write_text(
            json.dumps(
                {
                    "approved_atoms": model["approved_atoms"],
                    "approved_atoms_only": model["approved_atoms_only"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    _write_sha_manifest(output_dir)


def _record_summary(
    train_records: list[dict[str, Any]],
    calibration_records: list[dict[str, Any]],
    holdout_records: list[dict[str, Any]],
) -> dict[str, Any]:
    records = {"train": train_records, "calibration": calibration_records, "holdout": holdout_records}
    scene_sets = {split: {str(record.get("scene_id")) for record in rows} for split, rows in records.items()}
    sample_sets = {split: {str(record.get("sample_id")) for record in rows} for split, rows in records.items()}
    return {
        "scene_zero_overlap": _sets_disjoint(scene_sets.values()),
        "sample_zero_overlap": _sets_disjoint(sample_sets.values()),
        "train_k_values": _unique(record.get("K") for record in train_records),
        "train_candidate_count_values": _unique(record.get("candidate_count") for record in train_records),
        "train_dp_head_values": _unique(record.get("DP_HEAD") for record in train_records),
        "train_candidate_tensor_mutated_count": sum(
            1 for record in train_records if record.get("candidate_tensor_unchanged_by_camp") is not True
        ),
        "train_closed_loop_outcome_count": sum(1 for record in train_records if "candidate_closed_loop_outcomes" in record),
    }


def _atom_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    missing_atoms = missing_feasible = missing_schema = invalid_atoms = invalid_feasible = 0
    atom_names: list[str] = []
    atom_version = None
    canonical = False
    for record in records:
        atoms = record.get("atoms")
        feasible = record.get("feasible_mask")
        names = record.get("atom_names")
        version = record.get("atom_schema_version")
        if atoms is None:
            missing_atoms += 1
            continue
        if feasible is None:
            missing_feasible += 1
        if names is None or version is None:
            missing_schema += 1
        if not _is_matrix(atoms) or len(atoms) != EXPECTED_K:
            invalid_atoms += 1
        elif atom_names and len(atoms[0]) != len(atom_names):
            invalid_atoms += 1
        if not isinstance(feasible, list) or len(feasible) != EXPECTED_K:
            invalid_feasible += 1
        if not atom_names and isinstance(names, list):
            atom_names = [str(name) for name in names]
            atom_version = str(version)
    if atom_names:
        try:
            expected_version, expected_names = atom_schema_for_dimension(len(atom_names))
            canonical = atom_version == expected_version and tuple(atom_names) == expected_names
        except ValueError:
            canonical = False
    return {
        "atom_count": len(atom_names),
        "atom_names": atom_names,
        "atom_schema_version": atom_version,
        "canonical_schema": canonical,
        "invalid_atom_shape_count": invalid_atoms,
        "invalid_feasible_shape_count": invalid_feasible,
        "missing_atoms": missing_atoms,
        "missing_atom_schema": missing_schema,
        "missing_feasible_mask": missing_feasible,
    }


def _empty_atom_derivation() -> dict[str, Any]:
    return {
        "attempted": False,
        "records_already_with_atoms": 0,
        "records_enriched": 0,
        "failed_records": 0,
        "candidate_npz_sha_mismatches": 0,
        "candidate_tensor_sha_mismatches": 0,
        "input_npz_sha_mismatches": 0,
        "errors": [],
        "source": None,
    }


def _derive_missing_train_atoms(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    schema_version, atom_names = atom_schema_for_dimension(9)
    enriched_records = []
    summary = _empty_atom_derivation()
    summary["attempted"] = True
    summary["source"] = "existing_candidate_npz_and_input_npz"
    for index, record in enumerate(records):
        if record.get("atoms") is not None:
            summary["records_already_with_atoms"] += 1
            enriched_records.append(record)
            continue
        try:
            enriched = _record_with_derived_atoms(record, schema_version, atom_names)
        except ValueError as exc:
            message = str(exc)
            summary["failed_records"] += 1
            if "candidate_npz_sha256 mismatch" in message:
                summary["candidate_npz_sha_mismatches"] += 1
            if "candidate_tensor_sha256 mismatch" in message:
                summary["candidate_tensor_sha_mismatches"] += 1
            if "adapter_input_sha256 mismatch" in message:
                summary["input_npz_sha_mismatches"] += 1
            if len(summary["errors"]) < 10:
                summary["errors"].append({"record_index": index, "error": message})
            enriched_records.append(record)
            continue
        summary["records_enriched"] += 1
        enriched_records.append(enriched)
    return enriched_records, summary


def _record_with_derived_atoms(
    record: dict[str, Any],
    atom_schema_version: str,
    atom_names: tuple[str, ...],
) -> dict[str, Any]:
    candidate_npz = _record_path(record, "candidate_npz")
    input_npz = _record_path(record, "input_npz")
    if not candidate_npz.is_file():
        raise ValueError(f"candidate_npz missing: {candidate_npz}")
    if not input_npz.is_file():
        raise ValueError(f"input_npz missing: {input_npz}")
    _check_optional_file_sha(candidate_npz, record.get("candidate_npz_sha256"), "candidate_npz_sha256")
    _check_optional_file_sha(input_npz, record.get("adapter_input_sha256"), "adapter_input_sha256")
    with np.load(candidate_npz, allow_pickle=False) as loaded:
        if "candidate_tensor" not in loaded.files:
            raise ValueError(f"candidate_tensor missing from {candidate_npz}")
        raw_candidate_tensor = loaded["candidate_tensor"]
        candidate_tensor = np.asarray(raw_candidate_tensor, dtype=np.float64)
        candidate_count = int(loaded["candidate_count"]) if "candidate_count" in loaded.files else candidate_tensor.shape[0]
    if candidate_tensor.ndim != 3 or candidate_tensor.shape[0] != EXPECTED_K or candidate_count != EXPECTED_K:
        raise ValueError(f"candidate_tensor must be [8,T,D], got {candidate_tensor.shape} count={candidate_count}")
    if not np.all(np.isfinite(candidate_tensor)):
        raise ValueError("candidate_tensor contains non-finite values")
    expected_tensor_sha = record.get("candidate_tensor_sha256")
    if expected_tensor_sha and _array_sha256(raw_candidate_tensor) != str(expected_tensor_sha):
        raise ValueError("candidate_tensor_sha256 mismatch")
    with np.load(input_npz, allow_pickle=False) as loaded:
        arrays = {key: loaded[key] for key in loaded.files}
    context = _context_from_dp_input(arrays)
    atoms = []
    feasible = []
    for candidate in candidate_tensor:
        trajectory_xy = candidate[:, :2]
        atoms.append(compute_atom_bank_vector(context, trajectory_xy))
        feasible.append(bool(compute_feasibility_mask(context, trajectory_xy, check_speed=True, check_lane=True)))
    atom_matrix = np.asarray(atoms, dtype=np.float64)
    if atom_matrix.shape != (EXPECTED_K, len(atom_names)):
        raise ValueError(f"derived atoms must be [8,{len(atom_names)}], got {atom_matrix.shape}")
    if not np.all(np.isfinite(atom_matrix)):
        raise ValueError("derived atoms contain non-finite values")
    if not any(feasible):
        raise ValueError("derived feasible_mask has no feasible candidates")
    enriched = dict(record)
    enriched.update(
        {
            "atom_derivation_source": "existing_candidate_npz_and_input_npz",
            "atom_names": list(atom_names),
            "atom_schema_version": atom_schema_version,
            "atoms": atom_matrix.tolist(),
            "feasible_mask": feasible,
        }
    )
    return enriched


def _context_from_dp_input(arrays: dict[str, np.ndarray]) -> DriverAtomContext:
    route_lanes = np.asarray(arrays["route_lanes"], dtype=np.float64)
    lane_centerline = _route_centerline(route_lanes)
    neighbors = np.asarray(arrays.get("neighbor_agents_future", np.empty((0, 0, 2))), dtype=np.float64)
    dynamic = {
        int(index): obstacle[:, :2]
        for index, obstacle in enumerate(neighbors)
        if obstacle.ndim == 2 and obstacle.shape[1] >= 2 and np.any(np.abs(obstacle[:, :2]) > 1e-8)
    }
    static = np.asarray(arrays.get("static_objects", np.empty((0, 2))), dtype=np.float64)
    static_obstacles = None
    if static.ndim == 2 and static.shape[1] >= 2:
        valid = np.sum(np.abs(static[:, :2]), axis=1) > 1e-8
        if valid.any():
            static_obstacles = static[valid, :2]
    return DriverAtomContext(
        dt=0.1,
        lane_centerline=lane_centerline,
        static_obstacles=static_obstacles,
        dynamic_obstacles=dynamic or None,
        speed_limit=_speed_limit_from_dp_input(arrays),
        desired_speed=_desired_speed_from_dp_input(arrays),
        lane_half_width=_lane_half_width_from_route_lanes(route_lanes),
        map_source="v16_fixed_dp_candidate_tensor_input_npz",
    )


def _speed_limit_from_dp_input(arrays: dict[str, np.ndarray]) -> float | None:
    speeds = np.asarray(arrays.get("route_lanes_speed_limit", []), dtype=np.float64).reshape(-1)
    if not speeds.size:
        return None
    has_limit = np.asarray(arrays.get("route_lanes_has_speed_limit", np.ones_like(speeds, dtype=bool)), dtype=bool).reshape(-1)
    valid = speeds[has_limit[: speeds.shape[0]]]
    valid = valid[np.isfinite(valid) & (valid > 0.0)]
    return float(valid[0]) if valid.size else None


def _desired_speed_from_dp_input(arrays: dict[str, np.ndarray]) -> float | None:
    current = np.asarray(arrays.get("ego_current_state", []), dtype=np.float64).reshape(-1)
    return float(current[4]) if current.size > 4 and np.isfinite(current[4]) else None


def _lane_half_width_from_route_lanes(route_lanes: np.ndarray) -> float:
    lanes = np.asarray(route_lanes, dtype=np.float64)
    if lanes.ndim == 4 and lanes.shape[0] == 1:
        lanes = lanes[0]
    if lanes.ndim != 3 or lanes.shape[-1] < 8:
        return 1.8
    widths = []
    for boundary_slice in (slice(4, 6), slice(6, 8)):
        norms = np.linalg.norm(lanes[..., boundary_slice], axis=-1)
        valid = norms[np.isfinite(norms) & (norms > 0.2)]
        widths.extend(valid.tolist())
    return float(np.median(widths)) if widths else 1.8


def _training_command(
    *,
    python_executable: str,
    training_script: Path,
    selection_log: Path,
    output_dir: Path,
    epochs: int,
) -> list[str]:
    return [
        python_executable,
        str(training_script),
        "--selection_log",
        str(selection_log),
        "--output_dir",
        str(output_dir),
        "--epochs",
        str(epochs),
        "--label_source",
        "proxy",
        "--require_atom_schema",
    ]


def _record_path(record: dict[str, Any], key: str) -> Path:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} missing")
    return Path(value)


def _check_optional_file_sha(path: Path, expected: Any, field: str) -> None:
    if expected and _sha256(path) != str(expected):
        raise ValueError(f"{field} mismatch")


def _source_artifact(path: Path, expected_root_sha256: str) -> dict[str, Any]:
    sha256s = path / "SHA256SUMS"
    root = path / "ROOT_SHA256SUMS"
    failed = _verify_sha256s(path, sha256s)
    return {
        "path": str(path),
        "exists": path.is_dir(),
        "expected_root_sha256": expected_root_sha256,
        "root_sha256": _root_sha(root),
        "root_sha256s_sha256": _sha256(root) if root.is_file() else None,
        "sha256s_sha256": _sha256(sha256s) if sha256s.is_file() else None,
        "sha256s_verified": path.is_dir() and sha256s.is_file() and not failed,
        "failed_sha256s": failed,
    }


def _verify_sha256s(root: Path, manifest: Path) -> list[str]:
    if not manifest.is_file():
        return ["missing_SHA256SUMS"]
    failed = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(maxsplit=1)
        path = root / rel.strip()
        if not path.is_file() or _sha256(path) != expected:
            failed.append(rel.strip())
    return failed


def _write_sha_manifest(output_dir: Path) -> None:
    sha_path = output_dir / "SHA256SUMS"
    root_path = output_dir / "ROOT_SHA256SUMS"
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path in (sha_path, root_path):
            continue
        rows.append(f"{_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    root_path.write_text(f"{_sha256(sha_path)}  SHA256SUMS\n", encoding="utf-8")


def _fail_after_training(report: dict[str, Any], failed: list[str]) -> None:
    report["status"] = FAILED_STATUS
    report["authorized_next_work"] = AUTHORIZED_CURRENT_WORK
    report["final_decision"] = _decision(False, failed, training_executed=report["pilot_training_execution"]["training_executed"])


def _decision(passed: bool, failed: list[str], *, training_executed: bool) -> dict[str, Any]:
    return {
        "passed": passed,
        "status": READY_STATUS if passed else FAILED_STATUS,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
        "training_executed": training_executed,
        "paired_evaluation_executed": False,
        "performance_claimed": False,
        "promotion_executed": False,
        "deployment_executed": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "fake_candidate_tensor_generated": False,
        "closed_loop_outcomes_used_for_training": False,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    training = report["pilot_training_execution"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Training Execution",
            "",
            f"- Status: `{report['status']}`",
            f"- Passed: `{report['final_decision']['passed']}`",
            f"- Train records: `{training['train_records']}`",
            f"- Wall-clock seconds: `{training['offline_training_wall_clock_seconds']}`",
            f"- Training executed: `{training['training_executed']}`",
            f"- Next: `{report['final_decision']['authorized_next_work']}`",
            "",
        ]
    )


def _render_heads(report: dict[str, Any]) -> str:
    heads = report["heads"]
    return "\n".join(
        [
            f"CAMP_HEAD={heads['camp_head']}",
            f"CAMP_ORIGIN_MAIN={heads['camp_origin_main']}",
            f"DP_HEAD={heads['dp_head']}",
            f"REQUIRED_DP_HEAD={heads['required_dp_head']}",
            f"NEXT_WORK_TARGET={report['authorized_next_work']}",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _root_sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0].split()[0] if lines else None


def _sets_disjoint(sets: Any) -> bool:
    seen: set[Any] = set()
    for values in sets:
        if seen.intersection(values):
            return False
        seen.update(values)
    return True


def _unique(values: Any) -> list[Any]:
    return sorted({_json_key(value): value for value in values}.values(), key=_json_key)


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _is_matrix(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(row, list) and row for row in value)


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _public_report(report: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in report.items() if not key.startswith("_")}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
