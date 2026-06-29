from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from scripts.integrations.audit_diffusion_planner_dp_camp_v13_nonoverlap_holdout_static_dp_reward_training_execution import (
    ATOM_SCHEMA_VERSION,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "2050aa78d506477b79306a4bd731e8595881bbb2"
AUDIT_HEAD = "1234567890abcdef1234567890abcdef12345678"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(tmp_path: Path, *, weights: np.ndarray | None = None) -> dict[str, Path]:
    preflight = tmp_path / "preflight"
    execution = tmp_path / "execution"
    training = tmp_path / "training"
    weights_array = (
        np.full(14, 1.0 / 14.0, dtype=np.float64)
        if weights is None
        else np.asarray(weights, dtype=np.float64)
    )
    trained_records = 8
    total_records = 10
    dropped_records = 2
    training.mkdir(parents=True, exist_ok=True)
    np.save(training / "offline_weights_dp_static.npy", weights_array)
    _write_json(
        training / "atom_scales_dp_static.json",
        {
            "atom_schema_version": ATOM_SCHEMA_VERSION,
            "atom_names": [f"atom_{index}" for index in range(14)],
            "scales": [float(index + 1) for index in range(14)],
        },
    )
    _write_json(
        training / "training_summary.json",
        {
            "training_type": "diffusion_planner_static_candidate_preference",
            "label_source": "dp_reward",
            "reward_key": "quality_without_progress",
            "reward_progress_weight": 2.0,
            "num_records": trained_records,
            "dropped_records_without_feasible_candidate": dropped_records,
            "num_candidates": 8,
            "num_atoms": 14,
            "atom_schema_version": ATOM_SCHEMA_VERSION,
            "atom_schema": {
                "version": ATOM_SCHEMA_VERSION,
                "verified_records": total_records,
                "missing_records": 0,
            },
            "dp_native_training_data_contract": {
                "passed": True,
                "records": total_records,
            },
            "trained_weights": weights_array.tolist(),
            "oracle_match_rate": 0.25,
            "feasible_candidate_rate": 0.8,
            "records_with_any_infeasible": 1,
            "scale_percentile": 95.0,
            "history": [{"epoch": 1.0, "loss": 2.0}, {"epoch": 1000.0, "loss": 1.5}],
            "caveat": "Candidate-level DP rewards are model-based preferences, not counterfactual closed-loop outcomes.",
        },
    )
    _write_json(
        preflight / "preflight.json",
        {
            "final_decision": {
                "passed": True,
                "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            },
            "training_input_summary": {
                "combined": {
                    "selection_log_count": 2,
                    "records_total": total_records,
                },
            },
        },
    )
    _write_json(
        preflight / "training_command_plan.json",
        {"training_execution_performed": False},
    )
    _write(
        execution / "HEADS.txt",
        "\n".join(
            [
                f"camp_head={CAMP_HEAD}",
                f"camp_origin_main={CAMP_HEAD}",
                f"dp_head={FIXED_DP_HEAD}",
                f"preflight_artifact={preflight}",
                f"planned_training_output_dir={training}",
            ]
        )
        + "\n",
    )
    _write(execution / "training.exit", "0\n")
    _write(execution / "training.stdout.txt", "ok\n")
    _write(execution / "training.stderr.txt", "")
    _write(
        execution / "training_output_files.txt",
        "atom_scales_dp_static.json\noffline_weights_dp_static.npy\ntraining_summary.json\n",
    )
    _write_json(execution / "preflight_training_command_plan.json", {"training_execution_performed": False})
    _write_json(execution / "preflight_selection_manifest.json", {"selection_log_count": 2})
    _write(
        execution / "training_output_SHA256SUMS",
        "\n".join(
            [
                f"{_sha(training / 'atom_scales_dp_static.json')}  ./atom_scales_dp_static.json",
                f"{_sha(training / 'offline_weights_dp_static.npy')}  ./offline_weights_dp_static.npy",
                f"{_sha(training / 'training_summary.json')}  ./training_summary.json",
            ]
        )
        + "\n",
    )
    _write(execution / "SHA256SUMS", "placeholder  HEADS.txt\n")
    audit = _write(
        tmp_path / "audit.md",
        "\n".join(
            [
                "current_v13_status=preflight_ready",
                f"next_work_target={AUTHORIZED_CURRENT_WORK}",
                "training_execution_authorized_by_current_boundary=True",
                "replay_execution_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )
    return {
        "preflight": preflight,
        "execution": execution,
        "training": training,
        "audit": audit,
        "total_records": total_records,
        "trained_records": trained_records,
        "dropped_records": dropped_records,
    }


def _report(tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    paths = _artifact(tmp_path, weights=overrides.pop("weights", None))
    params = {
        "training_execution_artifact": paths["execution"],
        "training_output_dir": paths["training"],
        "preflight_artifact": paths["preflight"],
        "v13_audit_md": paths["audit"],
        "current_camp_head": AUDIT_HEAD,
        "current_camp_origin_main": AUDIT_HEAD,
        "current_dp_head": FIXED_DP_HEAD,
        "expected_total_records": paths["total_records"],
        "expected_trained_records": paths["trained_records"],
        "expected_dropped_records": paths["dropped_records"],
        "expected_selection_log_count": 2,
    }
    params.update(overrides)
    return build_report(**params)


def test_training_execution_audit_accepts_static_dp_reward_artifact(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is True
    assert decision["replay_executed"] is False
    assert report["weights"]["nonnegative"] is True
    assert report["weights"]["simplex_close"] is True
    assert report["atom_scales"]["strictly_positive"] is True


def test_training_execution_audit_rejects_non_simplex_weights(tmp_path: Path) -> None:
    bad_weights = np.full(14, 0.2, dtype=np.float64)
    report = _report(tmp_path, weights=bad_weights)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "weights_simplex_sum" in report["final_decision"]["failed_checks"]


def test_training_execution_audit_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, authorized_current_work="wrong_scope")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "preflight_authorized_training_execution" in report["final_decision"][
        "failed_checks"
    ]
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_training_execution_audit_cli_writes_reports(tmp_path: Path) -> None:
    paths = _artifact(tmp_path)
    out_json = tmp_path / "out" / "audit.json"
    out_md = tmp_path / "out" / "audit.md"
    exit_code = main(
        [
            "--training_execution_artifact",
            str(paths["execution"]),
            "--training_output_dir",
            str(paths["training"]),
            "--preflight_artifact",
            str(paths["preflight"]),
            "--v13_audit_md",
            str(paths["audit"]),
            "--current_camp_head",
            AUDIT_HEAD,
            "--current_camp_origin_main",
            AUDIT_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--expected_total_records",
            str(paths["total_records"]),
            "--expected_trained_records",
            str(paths["trained_records"]),
            "--expected_dropped_records",
            str(paths["dropped_records"]),
            "--expected_selection_log_count",
            "2",
            "--output_json",
            str(out_json),
            "--output_md",
            str(out_md),
        ]
    )

    assert exit_code == 0
    assert out_json.is_file()
    assert out_md.is_file()
    assert (out_json.parent / "SHA256SUMS").is_file()
