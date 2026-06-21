from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_temporal_consistency_shadow_atom_dry_run import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    analyze,
    main,
)


def _schema_preflight(**decision_overrides: object) -> dict:
    decision = {
        "status": "temporal_consistency_atom_schema_preflight_ready",
        "passed": True,
        "atom_schema_preflight_ready": True,
        "atom_promotion_authorized": False,
        "safety_benefit_evidence": False,
        "authorized_next_work": "temporal_consistency_shadow_atom_dry_run_only",
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
        "atom_schema": {
            "atom_name": "previous_plan_temporal_consistency_rms_m",
            "payload_key": "temporal_consistency_payload_logging",
            "coefficient_key": "previous_plan_temporal_consistency_rms_m",
            "affine_score_compatible": True,
            "convex_master_compatible": True,
            "nonnegative_by_definition": True,
            "uses_future_outcomes": False,
            "classic_benders_claim": False,
        },
    }


def _record(*, available: bool, bad_score: bool = False) -> dict:
    normalized_atoms = [[0.0, 1.0], [1.0, 0.0]]
    weights = [0.2, 0.8]
    scores = [0.8, 0.2]
    if bad_score:
        scores = [0.7, 0.2]
    payload = {
        "available": available,
        "availability_reason": (
            "available" if available else "previous_selected_plan_absent"
        ),
        "candidate_count": 2,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
    }
    if available:
        payload["previous_plan_temporal_consistency_rms_m"] = [0.5, 0.1]
    return {
        "selected_index": 1,
        "candidate_closed_loop_outcomes": None,
        "temporal_consistency_payload_logging": payload,
        "atom_names": ["a", "b"],
        "atoms": normalized_atoms,
        "normalized_atoms": normalized_atoms,
        "weights": weights,
        "selection_weights": weights,
        "scores": scores,
        "selection_scores": scores,
        "feasible_mask": [True, True],
    }


def _write_logs(root: Path, *, bad_score: bool = False) -> None:
    for run_idx in range(2):
        run = root / f"run_{run_idx}"
        run.mkdir(parents=True)
        rows = [
            _record(available=False),
            _record(available=True, bad_score=bad_score and run_idx == 0),
        ]
        run.joinpath("camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_temporal_consistency_shadow_atom_dry_run_accepts_zero_weight_append(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        schema_preflight=_schema_preflight(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["dry_run_summary"]["available_records"] == 2
    assert report["dry_run_summary"]["fail_closed_unavailable_records"] == 2
    assert report["dry_run_summary"]["shadow_appended_records"] == 2
    assert report["dry_run_summary"]["ranking_signal_records"] == 2
    assert report["dry_run_summary"]["max_shadow_zero_weight_score_abs_diff"] == 0.0
    assert report["dry_run_records"][1]["shadow_atom_count"] == 3
    assert report["dry_run_records"][1]["shadow_weight_last"] == 0.0
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_temporal_consistency_shadow_atom_dry_run_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        schema_preflight=_schema_preflight(
            status="temporal_consistency_atom_schema_preflight_rejected",
            passed=False,
            authorized_next_work=None,
        ),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "source_status" in report["final_decision"]["failed_checks"]
    assert "source_passed" in report["final_decision"]["failed_checks"]


def test_temporal_consistency_shadow_atom_dry_run_rejects_bad_base_score(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, bad_score=True)

    report = analyze(
        schema_preflight=_schema_preflight(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "all_records_valid" in report["final_decision"]["failed_checks"]
    assert (
        report["dry_run_summary"]["record_error_counts"]["base_affine_score_mismatch"]
        == 1
    )


def test_temporal_consistency_shadow_atom_dry_run_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "logging_enabled"
    schema = tmp_path / "schema.json"
    output_json = tmp_path / "dry_run.json"
    output_md = tmp_path / "dry_run.md"
    _write_logs(root)
    schema.write_text(json.dumps(_schema_preflight()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "temporal-shadow-dry-run",
            "--schema_preflight_json",
            str(schema),
            "--candidate_root",
            str(root),
            "--expected_logs",
            "2",
            "--expected_records",
            "4",
            "--expected_candidates",
            "2",
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
    assert "Temporal Consistency Shadow Atom Dry Run" in output_md.read_text(
        encoding="utf-8"
    )
