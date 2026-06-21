from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.diagnose_diffusion_planner_external_context_materiality_gap import (
    AUTHORIZED_NEXT_WORK,
    DIAGNOSED_STATUS,
    REJECT_STATUS,
    diagnose,
    main,
)


def _materiality(*, rejected: bool = True) -> dict:
    return {
        "field_reports": [
            {
                "family": "traffic_signal",
                "field": "candidate_first_signal_arrival_time_s",
                "material": False,
                "finite_min": None,
                "finite_max": None,
            },
            {
                "family": "traffic_signal",
                "field": "candidate_signal_phase_change_margin_s",
                "material": False,
                "finite_min": None,
                "finite_max": None,
            },
            {
                "family": "traffic_signal",
                "field": "candidate_right_of_way_blocked_indicator",
                "material": False,
                "finite_min": 0.0,
                "finite_max": 0.0,
            },
            {
                "family": "route_speed",
                "field": "candidate_route_speed_limit_min_mps",
                "material": False,
                "finite_min": 8.333333,
                "finite_max": 8.333333,
            },
            {
                "family": "route_speed",
                "field": "candidate_speed_limit_excess_integral_mps",
                "material": False,
                "finite_min": 0.0,
                "finite_max": 0.0,
            },
            {
                "family": "route_speed",
                "field": "candidate_speed_limit_available_fraction",
                "material": False,
                "finite_min": 1.0,
                "finite_max": 1.0,
            },
        ],
        "family_reports": [
            {"family": "traffic_signal", "material": False, "material_fields": []},
            {"family": "route_speed", "material": False, "material_fields": []},
        ],
        "material_families": [],
        "final_decision": {
            "status": (
                "external_context_payload_materiality_rejected"
                if rejected
                else "external_context_payload_materiality_ready"
            ),
            "passed": not rejected,
            "authorized_next_work": (
                None
                if rejected
                else "external_context_payload_atomization_preflight_existing_smoke_only"
            ),
        },
    }


def _record() -> dict:
    return {
        "selected_index": 2,
        "candidate_closed_loop_outcomes": None,
        "external_context_payload_logging": {
            "candidate_count": 8,
            "route_speed_context_available": True,
            "traffic_signal_context_available": False,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "candidate_route_speed_limit_min_mps": [8.333333] * 8,
            "candidate_speed_limit_excess_integral_mps": [0.0] * 8,
            "candidate_speed_limit_available_fraction": [1.0] * 8,
            "candidate_first_signal_arrival_time_s": None,
            "candidate_signal_phase_change_margin_s": None,
            "candidate_right_of_way_blocked_indicator": None,
        },
    }


def _traffic_signal_constant_record() -> dict:
    record = _record()
    payload = record["external_context_payload_logging"]
    payload["traffic_signal_context_available"] = True
    payload["candidate_right_of_way_blocked_indicator"] = [0.0] * 8
    return record


def _write_log(root: Path, *, records: int = 3) -> None:
    root.mkdir(parents=True)
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_record() for _ in range(records)]),
        encoding="utf-8",
    )


def _write_signal_constant_log(root: Path, *, records: int = 3) -> None:
    root.mkdir(parents=True)
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_traffic_signal_constant_record() for _ in range(records)]),
        encoding="utf-8",
    )


def test_external_context_materiality_gap_diagnoses_real_smoke_shape(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root)

    report = diagnose(
        materiality=_materiality(),
        candidate_root=candidate_root,
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == DIAGNOSED_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert decision["gap_names"] == [
        "traffic_signal_context_absent",
        "route_speed_context_available_but_no_candidate_excess",
        "route_speed_availability_constant",
        "nonmaterial_constant_speed_limit",
    ]
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_external_context_materiality_gap_diagnoses_signal_horizon_gap(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_signal_constant_log(candidate_root)

    report = diagnose(
        materiality=_materiality(),
        candidate_root=candidate_root,
        label="unit_signal",
    )

    assert report["final_decision"]["status"] == DIAGNOSED_STATUS
    assert report["final_decision"]["gap_names"] == [
        "traffic_signal_context_available_but_no_candidate_arrival",
        "traffic_signal_right_of_way_indicator_constant_clear",
        "route_speed_context_available_but_no_candidate_excess",
        "route_speed_availability_constant",
        "nonmaterial_constant_speed_limit",
    ]


def test_external_context_materiality_gap_rejects_ready_source(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root)

    report = diagnose(
        materiality=_materiality(rejected=False),
        candidate_root=candidate_root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "source_status_is_materiality_rejected",
        "source_passed_false",
        "source_authorizes_no_atomization",
    ]


def test_external_context_materiality_gap_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate_root = tmp_path / "candidate"
    materiality_path = tmp_path / "materiality.json"
    output_json = tmp_path / "gap.json"
    output_md = tmp_path / "gap.md"
    _write_log(candidate_root)
    materiality_path.write_text(json.dumps(_materiality()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-materiality-gap",
            "--materiality_json",
            str(materiality_path),
            "--candidate_root",
            str(candidate_root),
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
    assert payload["final_decision"]["status"] == DIAGNOSED_STATUS
    assert "External Context Materiality Gap Diagnosis" in output_md.read_text(
        encoding="utf-8"
    )
