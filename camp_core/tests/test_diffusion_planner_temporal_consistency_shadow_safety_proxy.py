from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_temporal_consistency_shadow_safety_proxy import (
    NO_EVIDENCE_NEXT_WORK,
    READY_STATUS,
    SAFETY_EVIDENCE_NEXT_WORK,
    analyze,
    main,
)


def _source_report(*, changed: bool = True) -> dict:
    decision = {
        "status": "temporal_consistency_shadow_weight_sensitivity_ready",
        "passed": True,
        "authorized_next_work": "temporal_consistency_shadow_safety_proxy_existing_smoke_only",
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "max_changed_records": 2 if changed else 0,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
    }
    return {
        "final_decision": decision,
        "sensitivity_summary": {
            "available_records": 2,
            "valid_available_records": 2,
            "zero_weight_changed_records": 0,
            "positive_weight_any_change": changed,
            "by_weight": [
                {"weight": 0.0, "changed_records": 0},
                {"weight": 0.1, "changed_records": 2 if changed else 0},
            ],
        },
        "sensitivity_records": [
            {
                "global_index": 0,
                "available": False,
                "weight_results": [],
            },
            _source_record(1, changed=changed),
            {
                "global_index": 2,
                "available": False,
                "weight_results": [],
            },
            _source_record(3, changed=changed),
        ],
    }


def _source_record(global_index: int, *, changed: bool) -> dict:
    return {
        "global_index": global_index,
        "available": True,
        "selected_index": 0,
        "passed": True,
        "weight_results": [
            {
                "weight": 0.1,
                "shadow_selected_index": 1 if changed else 0,
                "changed_selected_index": changed,
            }
        ],
    }


def _candidate_record(
    *,
    available: bool,
    safety_improves: bool = True,
    closed_loop_outcome: object | None = None,
) -> dict:
    payload = {
        "available": available,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
    }
    if not available:
        return {
            "selected_index": 0,
            "candidate_closed_loop_outcomes": None,
            "temporal_consistency_payload_logging": payload,
        }
    selected_red = 1.0 if safety_improves else 0.0
    shadow_red = 0.0
    return {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": closed_loop_outcome,
        "temporal_consistency_payload_logging": payload,
        "candidate_horizon_union_planned_red_light_cost": [selected_red, shadow_red],
        "candidate_full_horizon_planned_red_light_cost": [selected_red, shadow_red],
        "candidate_red_stopping_margin_cost": [0.2 if safety_improves else 0.0, 0.0],
        "candidate_obstacle_clearance": {
            "soft_clearance_violation_cost": [0.1 if safety_improves else 0.0, 0.0],
            "near_miss_violation_cost": [0.0, 0.0],
        },
        "candidate_horizon_lateral_acceleration_cost": [0.3, 0.2],
        "candidate_horizon_yaw_rate_cost": [0.4, 0.3],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [5.0, 4.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [0.7, 0.6],
        "candidate_route_progress": [10.0, 9.9],
    }


def _write_logs(root: Path, *, safety_improves: bool = True, closed_loop: bool = False) -> None:
    for run_idx in range(2):
        run = root / f"run_{run_idx}"
        run.mkdir(parents=True)
        rows = [
            _candidate_record(available=False),
            _candidate_record(
                available=True,
                safety_improves=safety_improves,
                closed_loop_outcome=[{"leak": True}] if closed_loop and run_idx == 0 else None,
            ),
        ]
        run.joinpath("camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_temporal_consistency_shadow_safety_proxy_accepts_safety_evidence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, safety_improves=True)

    report = analyze(
        weight_sensitivity=_source_report(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
        weight_grid=(0.1,),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["safety_proxy_evidence"] is True
    assert decision["authorized_next_work"] == SAFETY_EVIDENCE_NEXT_WORK
    by_weight = report["proxy_summary"]["by_weight"][0]
    assert by_weight["changed_records"] == 2
    assert by_weight["family_summary"]["safety"]["improved_records"] == 2
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_temporal_consistency_shadow_safety_proxy_passes_without_safety_evidence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, safety_improves=False)

    report = analyze(
        weight_sensitivity=_source_report(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
        weight_grid=(0.1,),
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["safety_proxy_evidence"] is False
    assert decision["authorized_next_work"] == NO_EVIDENCE_NEXT_WORK
    safety = report["proxy_summary"]["by_weight"][0]["family_summary"]["safety"]
    assert safety["improved_records"] == 0
    assert safety["worsened_records"] == 0


def test_temporal_consistency_shadow_safety_proxy_rejects_future_outcomes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, safety_improves=True, closed_loop=True)

    report = analyze(
        weight_sensitivity=_source_report(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
        weight_grid=(0.1,),
    )

    decision = report["final_decision"]
    assert decision["status"] != READY_STATUS
    assert "record_errors_empty" in decision["failed_checks"]
    assert report["proxy_summary"]["record_error_counts"] == {
        "candidate_closed_loop_outcomes_present": 1
    }


def test_temporal_consistency_shadow_safety_proxy_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "logging_enabled"
    source = tmp_path / "weight_sensitivity.json"
    output_json = tmp_path / "safety_proxy.json"
    output_md = tmp_path / "safety_proxy.md"
    _write_logs(root, safety_improves=True)
    source.write_text(json.dumps(_source_report()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "temporal-safety-proxy",
            "--weight_sensitivity_json",
            str(source),
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
    assert "Temporal Consistency Shadow Safety Proxy" in output_md.read_text(
        encoding="utf-8"
    )
