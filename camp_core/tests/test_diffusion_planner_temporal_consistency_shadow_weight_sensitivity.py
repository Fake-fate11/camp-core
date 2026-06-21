from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_temporal_consistency_shadow_weight_sensitivity import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    analyze,
    main,
)


def _dry_run(**decision_overrides: object) -> dict:
    decision = {
        "status": "temporal_consistency_shadow_atom_dry_run_ready",
        "passed": True,
        "shadow_atom_dry_run_ready": True,
        "authorized_next_work": (
            "temporal_consistency_shadow_weight_sensitivity_existing_smoke_only"
        ),
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "max_shadow_zero_weight_score_abs_diff": 0.0,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "dry_run_summary": {
            "records": 4,
            "available_records": 2,
            "ranking_signal_records": 2,
        },
    }


def _record(*, available: bool) -> dict:
    payload = {
        "available": available,
        "candidate_count": 2,
        "previous_plan_temporal_consistency_rms_m": [1.0, 0.0] if available else None,
    }
    return {
        "selected_index": 0,
        "selection_scores": [0.0, 0.05],
        "feasible_mask": [True, True],
        "temporal_consistency_payload_logging": payload,
    }


def _write_logs(root: Path) -> None:
    for run_idx in range(2):
        run = root / f"run_{run_idx}"
        run.mkdir(parents=True)
        rows = [_record(available=False), _record(available=True)]
        run.joinpath("camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_temporal_consistency_shadow_weight_sensitivity_accepts_grid(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        shadow_dry_run=_dry_run(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
        weight_grid=(0.0, 0.01, 0.1),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["safety_benefit_evidence"] is False
    assert report["final_decision"]["atom_promotion_authorized"] is False
    assert report["final_decision"]["max_changed_records"] == 2
    by_weight = {item["weight"]: item for item in report["sensitivity_summary"]["by_weight"]}
    assert by_weight[0.0]["changed_records"] == 0
    assert by_weight[0.1]["changed_records"] == 2
    assert report["sensitivity_summary"]["min_critical_positive_weight"] == 0.05
    assert "score'_k = selection_score_k + lambda * a_temporal,k" in report[
        "analysis"
    ]["math_boundary"]


def test_temporal_consistency_shadow_weight_sensitivity_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        shadow_dry_run=_dry_run(
            status="temporal_consistency_shadow_atom_dry_run_rejected",
            passed=False,
            authorized_next_work=None,
        ),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
        weight_grid=(0.0, 0.1),
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "source_status" in report["final_decision"]["failed_checks"]
    assert "source_passed" in report["final_decision"]["failed_checks"]


def test_temporal_consistency_shadow_weight_sensitivity_rejects_grid_without_zero(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        shadow_dry_run=_dry_run(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
        weight_grid=(0.1,),
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "grid_contains_zero" in report["final_decision"]["failed_checks"]


def test_temporal_consistency_shadow_weight_sensitivity_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "logging_enabled"
    dry_run = tmp_path / "dry_run.json"
    output_json = tmp_path / "sensitivity.json"
    output_md = tmp_path / "sensitivity.md"
    _write_logs(root)
    dry_run.write_text(json.dumps(_dry_run()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "temporal-weight-sensitivity",
            "--shadow_dry_run_json",
            str(dry_run),
            "--candidate_root",
            str(root),
            "--expected_logs",
            "2",
            "--expected_records",
            "4",
            "--expected_candidates",
            "2",
            "--expected_available_records",
            "2",
            "--shadow_weight",
            "0.0",
            "--shadow_weight",
            "0.1",
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_pass",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Temporal Consistency Shadow Weight Sensitivity" in output_md.read_text(
        encoding="utf-8"
    )
