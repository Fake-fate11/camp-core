from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_external_context_alternative_atom_search import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    analyze_records,
    main,
    render_markdown,
)


def _outcome(
    *,
    progress: float = 10.0,
    jerk: float = 1.0,
    lateral: float = 1.0,
    collision: bool = False,
    near_miss: bool = False,
    lane: bool = False,
    red: bool = False,
) -> dict:
    return {
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane,
        "red_light_violation": red,
        "progress_m": progress,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _payload(*, speed_excess: list[float], row_blocked: list[float] | None = None) -> dict:
    return {
        "schema_version": "dp_camp_external_context_payload_v1",
        "enabled": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "candidate_count": 2,
        "horizons": {"support_steps": 10, "dt_s": 0.1},
        "candidate_first_signal_arrival_time_s": [None, None],
        "candidate_right_of_way_blocked_indicator": row_blocked or [0.0, 0.0],
        "candidate_speed_limit_excess_integral_mps": speed_excess,
        "candidate_speed_limit_available_fraction": [1.0, 1.0],
    }


def _record(
    *,
    speed_excess: list[float],
    selected: int = 0,
    candidate1_progress: float = 10.0,
    candidate1_collision: bool = False,
) -> dict:
    return {
        "num_candidates": 2,
        "selected_index": selected,
        "seed": 1,
        "feasible_mask": [True, True],
        "candidate_route_progress": [10.0, 10.0],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [1.0, 1.0],
        "external_context_payload_logging": _payload(speed_excess=speed_excess),
        "candidate_closed_loop_outcomes": [
            _outcome(jerk=3.0, lateral=2.0),
            _outcome(
                progress=candidate1_progress,
                jerk=1.0,
                lateral=1.0,
                collision=candidate1_collision,
            ),
        ],
    }


def test_external_context_alternative_atom_search_accepts_noninferior_change() -> None:
    report = analyze_records(
        [_record(speed_excess=[1.0, 0.0])],
        expected_records=1,
        expected_candidates=2,
        fail_on_formal_seeds=True,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "route_speed_limit_excess_integral_v1" in decision["passing_candidates"]
    assert decision["online_selector_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]

    markdown = render_markdown(report)
    assert "External Context Alternative Atom Search" in markdown


def test_external_context_alternative_atom_search_rejects_hard_regression() -> None:
    report = analyze_records(
        [_record(speed_excess=[1.0, 0.0], candidate1_collision=True)],
        expected_records=1,
        expected_candidates=2,
    )

    decision = report["final_decision"]
    assert decision["status"] == REJECT_STATUS
    assert decision["authorized_next_work"] is None
    candidate = next(
        row
        for row in report["candidate_reports"]
        if row["name"] == "route_speed_limit_excess_integral_v1"
    )
    assert candidate["changed_records"] == 1
    assert candidate["changed_all_gate_records"] == 0


def test_external_context_alternative_atom_search_rejects_no_change() -> None:
    report = analyze_records(
        [_record(speed_excess=[0.0, 0.0])],
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["ranked_candidates"][0]["changed_records"] == 0


def test_external_context_alternative_atom_search_rejects_leaky_payload() -> None:
    record = _record(speed_excess=[1.0, 0.0])
    record["external_context_payload_logging"]["future_outcome_leakage"] = True

    report = analyze_records(
        [record],
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["record_checks"] if not check["passed"]]
    assert failed == ["record_0_future_outcome_leakage"]


def test_external_context_alternative_atom_search_rejects_formal_seed() -> None:
    record = _record(speed_excess=[1.0, 0.0])
    record["seed"] = 11

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records([record], fail_on_formal_seeds=True)


def test_external_context_alternative_atom_search_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    output_json = tmp_path / "search.json"
    output_md = tmp_path / "search.md"
    log_path.write_text(
        json.dumps([_record(speed_excess=[1.0, 0.0])]),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-alternative-atom-search",
            "--selection_log",
            str(log_path),
            "--expected_records",
            "1",
            "--expected_candidates",
            "2",
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
    assert "External Context Alternative Atom Search" in output_md.read_text(
        encoding="utf-8"
    )


def test_external_context_alternative_atom_search_is_outcome_independent_for_selection() -> None:
    base = _record(speed_excess=[1.0, 0.0])
    mutated = deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][1]["collision"] = True
    mutated["candidate_closed_loop_outcomes"][1]["progress_m"] = 0.0

    base_report = analyze_records([base], expected_records=1, expected_candidates=2)
    mutated_report = analyze_records([mutated], expected_records=1, expected_candidates=2)

    base_effect = next(
        row for row in base_report["candidate_reports"]
        if row["name"] == "route_speed_limit_excess_integral_v1"
    )["record_effects"][0]
    mutated_effect = next(
        row for row in mutated_report["candidate_reports"]
        if row["name"] == "route_speed_limit_excess_integral_v1"
    )["record_effects"][0]
    assert base_effect["chosen_index"] == mutated_effect["chosen_index"] == 1
    assert base_report["final_decision"]["status"] == READY_STATUS
    assert mutated_report["final_decision"]["status"] == REJECT_STATUS
