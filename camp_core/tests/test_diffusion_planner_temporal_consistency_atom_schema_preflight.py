from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_temporal_consistency_atom_schema_preflight import (
    ATOM_NAME,
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    build_report,
    main,
)


def _materiality(**decision_overrides: object) -> dict:
    decision = {
        "status": "temporal_consistency_materiality_diagnosis_ready",
        "passed": True,
        "source_materiality_evidence": True,
        "safety_benefit_evidence": False,
        "atom_schema_preflight_authorized": True,
        "atom_promotion_authorized": False,
        "authorized_next_work": "temporal_consistency_atom_schema_preflight_only",
        "available_records": 45,
        "lower_feasible_candidate_records": 37,
        "mean_feasible_gap_m": 0.0919,
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
        "materiality_summary": {
            "valid_records": 45,
            "invalid_records": 0,
            "nonzero_range_records": 45,
        },
    }


def test_temporal_consistency_atom_schema_preflight_accepts_material_source() -> None:
    report = build_report(materiality=_materiality(), label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["atom_schema_preflight_ready"] is True
    assert report["final_decision"]["atom_promotion_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["atom_schema"]["atom_name"] == ATOM_NAME
    assert report["atom_schema"]["nonnegative_by_definition"] is True
    assert report["atom_schema"]["signed_split_required"] is False
    assert report["atom_schema"]["affine_score_compatible"] is True
    assert report["atom_schema"]["convex_master_compatible"] is True
    assert report["atom_schema"]["classic_benders_claim"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_temporal_consistency_atom_schema_preflight_rejects_weak_materiality() -> None:
    report = build_report(
        materiality=_materiality(
            source_materiality_evidence=False,
            lower_feasible_candidate_records=0,
        )
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "source_materiality_evidence" in report["final_decision"]["failed_checks"]
    assert "source_has_lower_feasible_alternatives" in report["final_decision"][
        "failed_checks"
    ]


def test_temporal_consistency_atom_schema_preflight_rejects_blocked_action() -> None:
    report = build_report(materiality=_materiality(camp_retraining_authorized=True))

    assert report["final_decision"]["status"] != READY_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_temporal_consistency_atom_schema_preflight_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    materiality_json = tmp_path / "materiality.json"
    output_json = tmp_path / "schema.json"
    output_md = tmp_path / "schema.md"
    materiality_json.write_text(json.dumps(_materiality()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "temporal-schema-preflight",
            "--materiality_json",
            str(materiality_json),
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
    assert "Temporal Consistency Atom Schema Preflight" in output_md.read_text(
        encoding="utf-8"
    )
