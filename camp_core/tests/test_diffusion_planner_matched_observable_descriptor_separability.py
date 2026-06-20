from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _contract(status: str = "matched_observable_outcome_contract_passed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "matched_observable_outcome_contract_passed",
            "authorized_next_work": "offline_observable_descriptor_separability_screen_only",
        }
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _outcome(value: float, progress: float = 10.0, *, red: bool = False) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": red,
    }


def _payload(lateral: list[float]) -> dict:
    return {
        "schema_version": "dp_camp_observable_state_logging_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "candidate_count": 2,
        "finite_checks": {
            "candidate_route_projection_s_m": True,
            "candidate_route_lateral_error_m": True,
            "candidate_route_segment_index": True,
            "candidate_route_heading_change_rad": True,
            "candidate_min_obstacle_clearance_lower_bound_m": True,
            "candidate_obstacle_slot_count": True,
            "route_curvature_context_abs": True,
        },
        "candidate_route_projection_s_m": [0.0, 0.0],
        "candidate_route_lateral_error_m": lateral,
        "candidate_route_segment_index": [0.0, 0.0],
        "candidate_route_heading_change_rad": [0.0, 0.0],
        "candidate_min_obstacle_clearance_lower_bound_m": [5.0, 5.0],
        "candidate_obstacle_slot_count": [0.0, 0.0],
        "candidate_red_stopline_distance_m": None,
        "candidate_red_heading_alignment": None,
        "route_curvature_context_abs": [0.0, 0.0],
    }


def _record(*, beneficial: bool, lateral: float) -> dict:
    candidate = _outcome(2.0 if beneficial else -2.0)
    return {
        "num_candidates": 2,
        "seed": 1,
        "observable_state_logging": _payload([0.0, lateral]),
        "candidate_closed_loop_outcomes": [
            _outcome(0.0),
            candidate,
        ],
    }


def test_observable_descriptor_screen_finds_toy_lateral_separator() -> None:
    items = [
        {"raw": _record(beneficial=True, lateral=0.1), "context": _context()},
        {"raw": _record(beneficial=True, lateral=0.2), "context": _context()},
        {"raw": _record(beneficial=False, lateral=2.0), "context": _context()},
        {"raw": _record(beneficial=False, lateral=3.0), "context": _context()},
    ]

    report = analyze_records(
        items,
        matched_contract_report=_contract(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_descriptors"] is False
    assert report["analysis"]["thresholds_are_offline_oracle_diagnostics"] is True
    assert report["final_decision"]["online_selector_authorized"] is False
    best = report["ranked_screens"][0]
    assert best["promising_screen"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0


def test_observable_descriptor_screen_blocks_when_contract_not_ready() -> None:
    report = analyze_records(
        [{"raw": _record(beneficial=True, lateral=0.1), "context": _context()}],
        matched_contract_report=_contract("matched_observable_outcome_contract_rejected"),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_matched_observable_outcome_contract_before_separability"
    )


def test_observable_descriptor_screen_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(beneficial=True, lateral=0.1), "context": _context(seed=11)}],
            matched_contract_report=_contract(),
            fail_on_formal_seeds=True,
            min_beneficial_candidates=1,
            min_harmful_candidates=1,
        )


def test_observable_descriptor_values_are_outcome_independent() -> None:
    base = _record(beneficial=True, lateral=0.1)
    mutated = _record(beneficial=True, lateral=0.1)
    mutated["candidate_closed_loop_outcomes"][1]["mean_jerk_mps3"] = 99.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        matched_contract_report=_contract(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert base_report["feature_coverage"] == mutated_report["feature_coverage"]
    assert base_report["feature_reports"] == mutated_report["feature_reports"]


def test_observable_descriptor_cli_reads_selection_log(tmp_path) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            [
                _record(beneficial=True, lateral=0.1),
                _record(beneficial=False, lateral=2.0),
            ]
        ),
        encoding="utf-8",
    )
    contract_path = tmp_path / "contract.json"
    output_json = tmp_path / "screen.json"
    output_md = tmp_path / "screen.md"
    contract_path.write_text(json.dumps(_contract()), encoding="utf-8")

    report = analyze(
        [log_path],
        matched_contract_report=json.loads(contract_path.read_text(encoding="utf-8")),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
        fail_on_formal_seeds=True,
    )
    output_json.write_text(json.dumps(report), encoding="utf-8")

    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"][
        "status"
    ] == READY_STATUS
