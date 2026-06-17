from __future__ import annotations

import json

import pytest

from scripts.integrations.audit_diffusion_planner_candidate_availability_inputs import (
    audit_inputs,
    main,
)


def _outcome(index: int) -> dict[str, object]:
    return {
        "candidate_index": index,
        "progress_m": 10.0 - index,
        "mean_jerk_mps3": 4.0 + index,
        "mean_lateral_acceleration_mps2": 2.0 + index,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
    }


def _record(*, outcomes: bool = True) -> dict[str, object]:
    return {
        "num_candidates": 2,
        "selected_index": 0,
        "feasible_mask": [True, True],
        "atom_names": [
            "progress_shortfall",
            "planned_lateral_acceleration_cost",
            "planned_red_light_cost",
            "red_stopping_margin_cost",
            "dp_prior_jerk_excess_cost",
        ],
        "atoms": [
            [0.0, 1.0, 0.0, 0.0, 0.5],
            [0.1, 0.5, 0.0, 0.0, 0.2],
        ],
        "candidate_closed_loop_outcomes": (
            [_outcome(0), _outcome(1)] if outcomes else None
        ),
    }


def _write_log(tmp_path, record: dict[str, object]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps([record]), encoding="utf-8")
    return path


def test_candidate_availability_inputs_ready_with_atom_fallbacks(tmp_path) -> None:
    report = audit_inputs([_write_log(tmp_path, _record())])

    assert report["readiness"]["candidate_availability_oracle_ready"] is True
    assert report["readiness"]["outcome_labels_ready"] is True
    assert report["readiness"]["current_tick_proxy_inputs_ready"] is True
    assert report["proxy_sources"]["proxy_lateral"] == {
        "atom:planned_lateral_acceleration_cost": 1
    }
    assert report["field_coverage"]["candidate_closed_loop_outcomes_complete"][
        "records"
    ] == 1


def test_candidate_availability_inputs_block_oracle_without_outcome_labels(
    tmp_path,
) -> None:
    report = audit_inputs([_write_log(tmp_path, _record(outcomes=False))])

    assert report["readiness"]["candidate_availability_oracle_ready"] is False
    assert report["readiness"]["outcome_labels_ready"] is False
    assert report["readiness"]["current_tick_proxy_inputs_ready"] is True
    assert (
        report["readiness"]["next_step"]
        == "generate_or_attach_candidate_closed_loop_outcomes_before_running_oracle"
    )
    assert "candidate_closed_loop_outcomes" in report["missing_examples"]


def test_candidate_availability_inputs_cli_fails_when_requested(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = _write_log(tmp_path, _record(outcomes=False))
    output_json = tmp_path / "readiness.json"
    output_md = tmp_path / "readiness.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_diffusion_planner_candidate_availability_inputs.py",
            "--selection_log",
            str(log_path),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--fail_on_not_ready",
        ],
    )

    with pytest.raises(SystemExit, match="candidate_closed_loop_outcomes"):
        main()
    assert output_json.is_file()
    assert output_md.is_file()
