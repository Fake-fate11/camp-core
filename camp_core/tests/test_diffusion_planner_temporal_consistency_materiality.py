from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_temporal_consistency_materiality import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    build_report,
    main,
)


def _smoke_result() -> dict:
    return {
        "final_decision": {
            "status": "temporal_consistency_broader_nonformal_smoke_result_ready",
            "passed": True,
            "authorized_next_work": (
                "temporal_consistency_materiality_diagnosis_existing_broader_smoke_only"
            ),
            "coverage_ready_for_materiality_diagnosis": True,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _record(*, values: list[float], selected_index: int = 1) -> dict:
    return {
        "selected_index": selected_index,
        "feasible_mask": [True for _ in values],
        "candidate_closed_loop_outcomes": None,
        "temporal_consistency_payload_logging": {
            "available": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "deployed_atom_vector_change": False,
            "classical_benders_claim": False,
            "previous_plan_temporal_consistency_rms_m": values,
        },
    }


def _write_logs(root: Path, *, values: list[float]) -> None:
    for run_idx in range(5):
        run = root / f"run_{run_idx}"
        run.mkdir(parents=True)
        rows = [_record(values=values) for _ in range(9)]
        run.joinpath("camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_temporal_consistency_materiality_accepts_existing_smoke(
    tmp_path: Path,
) -> None:
    _write_logs(tmp_path / "logging_enabled", values=[0.0, 0.1, 0.2])

    report = build_report(
        smoke_result=_smoke_result(),
        logging_root=tmp_path / "logging_enabled",
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["source_materiality_evidence"] is True
    assert report["final_decision"]["safety_benefit_evidence"] is False
    assert report["final_decision"]["atom_schema_preflight_authorized"] is True
    assert report["final_decision"]["atom_promotion_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["materiality_summary"]["available_records"] == 45
    assert report["materiality_summary"]["lower_feasible_candidate_records"] == 45
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_temporal_consistency_materiality_rejects_no_lower_feasible_candidate(
    tmp_path: Path,
) -> None:
    _write_logs(tmp_path / "logging_enabled", values=[0.2, 0.0, 0.1])

    report = build_report(
        smoke_result=_smoke_result(),
        logging_root=tmp_path / "logging_enabled",
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "lower_feasible_alternatives_material" in report["final_decision"][
        "failed_checks"
    ]
    assert "mean_feasible_gap_material" in report["final_decision"]["failed_checks"]


def test_temporal_consistency_materiality_rejects_future_outcome_leakage(
    tmp_path: Path,
) -> None:
    run = tmp_path / "logging_enabled" / "run_0"
    run.mkdir(parents=True)
    rows = [_record(values=[0.0, 0.1, 0.2]) for _ in range(45)]
    rows[0]["temporal_consistency_payload_logging"]["future_outcome_leakage"] = True
    run.joinpath("camp_selection_log.json").write_text(json.dumps(rows), encoding="utf-8")

    report = build_report(
        smoke_result=_smoke_result(),
        logging_root=tmp_path / "logging_enabled",
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["materiality_summary"]["invalid_records"] == 1
    assert "invalid_records_zero" in report["final_decision"]["failed_checks"]


def test_temporal_consistency_materiality_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    smoke_result = tmp_path / "smoke_result.json"
    output_json = tmp_path / "materiality.json"
    output_md = tmp_path / "materiality.md"
    logging_root = tmp_path / "logging_enabled"
    smoke_result.write_text(json.dumps(_smoke_result()), encoding="utf-8")
    _write_logs(logging_root, values=[0.0, 0.1, 0.2])
    monkeypatch.setattr(
        "sys.argv",
        [
            "temporal-materiality",
            "--smoke_result_json",
            str(smoke_result),
            "--logging_root",
            str(logging_root),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Temporal Consistency Materiality Diagnosis" in output_md.read_text(
        encoding="utf-8"
    )
