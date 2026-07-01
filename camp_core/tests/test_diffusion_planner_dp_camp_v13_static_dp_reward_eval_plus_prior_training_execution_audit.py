from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.audit_diffusion_planner_dp_camp_v13_static_dp_reward_eval_plus_prior_training_execution import (
    ATOM_SCHEMA_VERSION,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "091e69dcd23d34d7ab341e056b2f098aa338c03e"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _audit_md(
    path: Path,
    *,
    wrong_scope: bool = False,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"next_work_target={'wrong_scope' if wrong_scope else authorized_current_work}",
                "training_execution_authorized_by_current_boundary=True",
                "replay_execution_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def _make_artifacts(
    tmp_path: Path,
    *,
    wrong_scope: bool = False,
    bad_weights: bool = False,
    label_source: str = "dp_reward",
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    runbook_name: str = "run_training.sh",
) -> dict[str, Path]:
    execution = tmp_path / "execution"
    preflight = tmp_path / "preflight"
    training = tmp_path / "training"
    execution.mkdir()
    preflight.mkdir()
    training.mkdir()
    _write(
        execution / "HEADS.txt",
        "\n".join(
            [
                f"camp_head={CAMP_HEAD}",
                f"camp_origin_main={CAMP_HEAD}",
                f"dp_head={FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    _write(execution / "training.exit", "0\n")
    _write(execution / "training.stdout.log", "{}\n")
    _write(execution / "training.stderr.log", "")
    _write(execution / "SHA256SUMS.txt", "")
    _write_json(
        preflight / "training_command_plan.json",
        {
            "schema_version": "dp_camp_v13_static_dp_reward_eval_plus_prior_training_command_plan_v1",
            "training_execution_performed": False,
            "selection_log_count": 64,
            "planned_training_output_dir": str(training),
            "label_source": "dp_reward",
            "reward_key": "quality_without_progress",
            "reward_progress_weight": 2.0,
            "require_dp_native_training_data_contract": True,
            "require_atom_schema": True,
        },
    )
    _write(preflight / runbook_name, "python train.py\n")
    schema, names = atom_schema_for_dimension(14)
    assert schema == ATOM_SCHEMA_VERSION
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)
    if bad_weights:
        weights[0] = -0.1
    np.save(training / "offline_weights_dp_static.npy", weights)
    _write_json(
        training / "atom_scales_dp_static.json",
        {
            "atom_schema_version": schema,
            "atom_names": list(names),
            "scales": [1.0 + index for index in range(14)],
        },
    )
    _write_json(
        training / "training_summary.json",
        {
            "training_type": "diffusion_planner_static_candidate_preference",
            "label_source": label_source,
            "reward_key": "quality_without_progress",
            "reward_progress_weight": 2.0,
            "selection_logs": [f"/fixed/log/{index}.json" for index in range(64)],
            "num_records": 5299,
            "dropped_records_without_feasible_candidate": 1101,
            "num_candidates": 8,
            "num_atoms": 14,
            "atom_schema_version": schema,
            "atom_schema": {
                "required": True,
                "verified_records": 6400,
            },
            "dp_native_training_data_contract": {
                "passed": True,
                "records": 6400,
                "failed_records": [],
            },
            "trained_weights": weights.tolist(),
            "oracle_match_rate": 0.15,
            "feasible_candidate_rate": 0.97,
            "records_with_any_infeasible": 294,
            "weights_path": str(training / "offline_weights_dp_static.npy"),
            "atom_scales_path": str(training / "atom_scales_dp_static.json"),
        },
    )
    audit_md = _audit_md(
        tmp_path / "audit.md",
        wrong_scope=wrong_scope,
        authorized_current_work=authorized_current_work,
    )
    return {
        "execution": execution,
        "preflight": preflight,
        "training": training,
        "audit": audit_md,
    }


def _report(tmp_path: Path, **kwargs) -> dict:
    paths = _make_artifacts(tmp_path, **kwargs)
    return build_report(
        execution_artifact_dir=paths["execution"],
        preflight_artifact_dir=paths["preflight"],
        training_output_dir=paths["training"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )


def test_training_execution_audit_disabled_is_noop(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = build_report(
        execution_artifact_dir=missing,
        preflight_artifact_dir=missing,
        training_output_dir=missing,
        v13_audit_md=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_training_execution_audit_accepts_nonpromotion_artifact(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_executed_by_audit"] is False
    assert report["training_artifact"]["weights_nonnegative"] is True
    assert report["training_artifact"]["weights_match_summary"] is True
    assert report["training_artifact"]["deployable_checkpoint_claim_authorized"] is False


def test_training_execution_audit_accepts_materialized_training_runbook_name(tmp_path: Path) -> None:
    report = _report(tmp_path, runbook_name="training_runbook.sh")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["source_hashes"]["preflight_runbook_sha256"] is not None


def test_training_execution_audit_accepts_parameterized_current_and_next_work(tmp_path: Path) -> None:
    current_work = (
        "dp_camp_v13_current_source_large_default_off_shadow_selector_static_dp_reward_"
        "eval_plus_prior_nonoverlap_remediation_static_dp_reward_training_execution_only"
    )
    next_work = (
        "dp_camp_v13_current_source_large_default_off_shadow_selector_static_dp_reward_"
        "eval_plus_prior_nonoverlap_remediation_static_dp_reward_training_artifact_"
        "shadow_replay_evaluation_preflight_only"
    )
    paths = _make_artifacts(tmp_path, authorized_current_work=current_work)

    report = build_report(
        execution_artifact_dir=paths["execution"],
        preflight_artifact_dir=paths["preflight"],
        training_output_dir=paths["training"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        authorized_current_work=current_work,
        authorized_next_work=next_work,
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == next_work


def test_training_execution_audit_rejects_wrong_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, wrong_scope=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work_target" in report["final_decision"]["failed_checks"]


def test_training_execution_audit_rejects_bad_weights(tmp_path: Path) -> None:
    report = _report(tmp_path, bad_weights=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "weights_nonnegative" in report["final_decision"]["failed_checks"]


def test_training_execution_audit_rejects_wrong_label_source(tmp_path: Path) -> None:
    report = _report(tmp_path, label_source="closed_loop_outcome")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "summary_label_source" in report["final_decision"]["failed_checks"]


def test_training_execution_audit_cli_writes_outputs(tmp_path: Path) -> None:
    paths = _make_artifacts(tmp_path)
    output_json = tmp_path / "out" / "audit.json"
    output_md = tmp_path / "out" / "audit.md"

    exit_code = main(
        [
            "--execution_artifact_dir",
            str(paths["execution"]),
            "--preflight_artifact_dir",
            str(paths["preflight"]),
            "--training_output_dir",
            str(paths["training"]),
            "--v13_audit_md",
            str(paths["audit"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--enable_v13_static_dp_reward_eval_plus_prior_training_execution_audit",
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"]["passed"] is True
    assert "read-only" in output_md.read_text(encoding="utf-8")
