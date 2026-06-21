from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_external_context_guarded_failure_diagnostic import (
    READY_STATUS,
    REJECT_STATUS,
    analyze,
    main,
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    red: bool = False,
) -> dict[str, object]:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": red,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _record() -> dict[str, object]:
    return {
        "num_candidates": 2,
        "selected_index": 1,
        "feasible_mask": [True, True],
        "scores": [2.0, 1.0],
        "selection_scores": [2.0, 1.0],
        "candidate_route_progress": [10.0, 10.0],
        "candidate_horizon_union_planned_red_light_cost": [1.0, 0.0],
        "dp_candidate_rewards": [
            {"total": 1.0, "progress": 8.0, "red_light": -1.0},
            {"total": 5.0, "progress": 8.0, "red_light": 0.0},
        ],
        "candidate_perfect_tracker_open_loop_rollout": {
            "3": {
                "distance_m": [5.0, 5.0],
                "mean_vector_jerk_mps3": [9.0, 2.0],
                "mean_lateral_acceleration_mps2": [4.0, 1.0],
            }
        },
        "external_context_payload_logging": {
            "candidate_count": 2,
            "candidate_first_signal_arrival_time_s": [None, 2.0],
            "candidate_right_of_way_blocked_indicator": [0.0, 1.0],
            "finite_checks": {"payload_valid": True},
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
        },
        "candidate_closed_loop_outcomes": [
            _outcome(0, progress=10.0, jerk=9.0, lateral=4.0, red=True),
            _outcome(1, progress=10.0, jerk=2.0, lateral=1.0),
        ],
    }


def _counterfactual(*, ready: bool = True) -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "external_context_atom_outcome_counterfactual_ready"
                if ready
                else "external_context_atom_outcome_counterfactual_rejected"
            ),
            "passed": ready,
            "promotion_authorized": False,
            "guarded_tiny_counterfactual_noninferior": False,
            "new_replay_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
        },
        "counterfactual_rows": [
            {
                "record_index": 0,
                "selected_index": 1,
                "atom_best_index": 0,
                "guarded_atom_best_index": 0,
            }
        ],
    }


def _atomization() -> dict[str, object]:
    return {
        "selected_atom_candidates": [
            {
                "name": "right_of_way_blocked_indicator_v1",
                "source_field": "candidate_right_of_way_blocked_indicator",
            },
            {
                "name": "signal_arrival_time_reaches_control_v1",
                "source_field": "candidate_first_signal_arrival_time_s",
            },
        ]
    }


def _write_log(root: Path) -> None:
    root.mkdir(parents=True)
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_record()]),
        encoding="utf-8",
    )


def test_guarded_failure_diagnostic_explains_worse_guarded_switch(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root)

    report = analyze(
        counterfactual=_counterfactual(),
        atomization=_atomization(),
        candidate_root=candidate_root,
        record_index=0,
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["new_replay_authorized"] is False
    assert decision["guarded_failure_status"] == "guarded_switch_worsens_safety_cost"
    assert "planned_red_lower_is_better" in decision["fixed_descriptor_explainer_names"]
    assert "h3_mean_vector_jerk_lower_is_better" in decision["fixed_descriptor_explainer_names"]
    diagnostic = report["diagnostic"]
    assert diagnostic["guarded_minus_selected"]["safety_cost_v1"] > 0.0
    assert diagnostic["guarded_minus_selected"]["route_progress"] == 0.0
    assert diagnostic["guarded_minus_selected"]["combined_external_context_atom_score"] < 0.0


def test_guarded_failure_diagnostic_rejects_source_not_ready(tmp_path: Path) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root)

    report = analyze(
        counterfactual=_counterfactual(ready=False),
        atomization=_atomization(),
        candidate_root=candidate_root,
        record_index=0,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "source_counterfactual_ready",
        "source_counterfactual_passed",
    ]


def test_guarded_failure_diagnostic_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate_root = tmp_path / "candidate"
    counterfactual_path = tmp_path / "counterfactual.json"
    atomization_path = tmp_path / "atomization.json"
    output_json = tmp_path / "diagnostic.json"
    output_md = tmp_path / "diagnostic.md"
    _write_log(candidate_root)
    counterfactual_path.write_text(json.dumps(_counterfactual()), encoding="utf-8")
    atomization_path.write_text(json.dumps(_atomization()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-guarded-failure-diagnostic",
            "--counterfactual_json",
            str(counterfactual_path),
            "--atomization_json",
            str(atomization_path),
            "--candidate_root",
            str(candidate_root),
            "--record_index",
            "0",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "External Context Guarded Failure Diagnostic" in output_md.read_text(
        encoding="utf-8"
    )
