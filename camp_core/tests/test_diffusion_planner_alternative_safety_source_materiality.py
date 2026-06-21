from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_alternative_safety_source_materiality import (
    EXISTING_SOURCE_NEXT_WORK,
    READY_STATUS,
    TARGETED_SUPPORT_NEXT_WORK,
    analyze,
    main,
)


def _safety_proxy_report(**overrides: object) -> dict:
    decision = {
        "status": "temporal_consistency_shadow_safety_proxy_ready",
        "passed": True,
        "authorized_next_work": (
            "reject_temporal_consistency_as_safety_source_or_predeclare_alternative_no_leak_atom_only"
        ),
        "safety_proxy_evidence": False,
        "safety_benefit_evidence": False,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
    }
    decision.update(overrides)
    return {"final_decision": decision}


def _record(
    *,
    available: bool,
    selected_index: int = 0,
    red_values: list[float] | None = None,
    closed_loop: object | None = None,
) -> dict:
    payload = {"available": available}
    if not available:
        return {
            "selected_index": selected_index,
            "candidate_closed_loop_outcomes": None,
            "temporal_consistency_payload_logging": payload,
        }
    red = red_values or [0.0, 1.0]
    return {
        "selected_index": selected_index,
        "candidate_closed_loop_outcomes": closed_loop,
        "temporal_consistency_payload_logging": payload,
        "candidate_horizon_union_planned_red_light_cost": red,
        "candidate_full_horizon_planned_red_light_cost": red,
        "candidate_red_stopping_margin_cost": [value / 10.0 for value in red],
        "candidate_obstacle_clearance": {
            "soft_clearance_violation_cost": [0.0 for _ in red],
            "near_miss_violation_cost": [0.0 for _ in red],
        },
    }


def _write_logs(
    root: Path,
    *,
    selected_index: int = 0,
    red_values: list[float] | None = None,
    closed_loop: bool = False,
) -> None:
    for run_idx in range(2):
        run = root / f"run_{run_idx}"
        run.mkdir(parents=True)
        rows = [
            _record(available=False),
            _record(
                available=True,
                selected_index=selected_index,
                red_values=red_values,
                closed_loop=[{"leak": True}] if closed_loop and run_idx == 0 else None,
            ),
        ]
        run.joinpath("camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_alternative_safety_source_materiality_finds_existing_actionable_source(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logs"
    _write_logs(root, selected_index=0, red_values=[1.0, 0.0])

    report = analyze(
        safety_proxy_report=_safety_proxy_report(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == EXISTING_SOURCE_NEXT_WORK
    assert decision["has_actionable_existing_safety_source"] is True
    assert "h30_union_planned_red_light_cost" in (
        decision["actionable_existing_safety_sources"]
    )
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_alternative_safety_source_materiality_routes_to_targeted_support_when_current_best(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logs"
    _write_logs(root, selected_index=0, red_values=[0.0, 1.0])

    report = analyze(
        safety_proxy_report=_safety_proxy_report(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == TARGETED_SUPPORT_NEXT_WORK
    assert decision["has_material_safety_source"] is True
    assert decision["has_actionable_existing_safety_source"] is False
    assert "h30_union_planned_red_light_cost" in (
        decision["material_but_current_selection_already_best"]
    )


def test_alternative_safety_source_materiality_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logs"
    _write_logs(root)

    report = analyze(
        safety_proxy_report=_safety_proxy_report(
            status="temporal_consistency_shadow_safety_proxy_rejected",
            passed=False,
            authorized_next_work=None,
        ),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "source_status" in report["final_decision"]["failed_checks"]


def test_alternative_safety_source_materiality_rejects_future_outcomes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logs"
    _write_logs(root, selected_index=0, red_values=[1.0, 0.0], closed_loop=True)

    report = analyze(
        safety_proxy_report=_safety_proxy_report(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        expected_available_records=2,
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert report["materiality_summary"]["record_error_counts"] == {
        "candidate_closed_loop_outcomes_present": 1
    }


def test_alternative_safety_source_materiality_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "logs"
    source = tmp_path / "safety_proxy.json"
    output_json = tmp_path / "materiality.json"
    output_md = tmp_path / "materiality.md"
    _write_logs(root, selected_index=0, red_values=[1.0, 0.0])
    source.write_text(json.dumps(_safety_proxy_report()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "alternative-safety-source",
            "--safety_proxy_json",
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
    assert "Alternative Safety Source Materiality" in output_md.read_text(
        encoding="utf-8"
    )
