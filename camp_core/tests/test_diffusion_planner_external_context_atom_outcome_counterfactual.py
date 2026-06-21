from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_external_context_atom_outcome_counterfactual import (
    READY_STATUS,
    REJECT_STATUS,
    analyze,
    main,
)
from scripts.integrations.plan_diffusion_planner_external_context_atomization_preflight import (
    build_report as build_atomization_report,
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


def _atomization(*, ready: bool = True) -> dict:
    report = build_atomization_report(
        materiality={
            "field_reports": [
                {
                    "family": "traffic_signal",
                    "field": "candidate_first_signal_arrival_time_s",
                    "material": True,
                },
                {
                    "family": "traffic_signal",
                    "field": "candidate_right_of_way_blocked_indicator",
                    "material": True,
                },
            ],
            "material_families": ["traffic_signal"],
            "final_decision": {
                "status": "external_context_payload_materiality_ready",
                "passed": True,
                "authorized_next_work": (
                    "external_context_payload_atomization_preflight_existing_smoke_only"
                ),
                "new_replay_authorized": False,
                "closed_loop_replay_authorized": False,
                "camp_retraining_authorized": False,
                "formal_seeds_authorized": False,
                "dp_modification_authorized": False,
                "classic_benders_claim_authorized": False,
            },
        }
    )
    if not ready:
        report["final_decision"]["status"] = "external_context_atomization_preflight_rejected"
        report["final_decision"]["passed"] = False
        report["final_decision"]["authorized_next_work"] = None
    return report


def _record(*, seed: int = 1) -> dict[str, object]:
    return {
        "seed": seed,
        "num_candidates": 2,
        "selected_index": 1,
        "feasible_mask": [True, True],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 1.0],
        "candidate_route_progress": [10.0, 10.0],
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
            _outcome(0, progress=10.0, jerk=1.0, lateral=0.5),
            _outcome(1, progress=10.0, jerk=1.0, lateral=0.5, red=True),
        ],
    }


def _write_log(root: Path, record: dict[str, object]) -> None:
    root.mkdir(parents=True)
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([record]),
        encoding="utf-8",
    )


def test_external_context_atom_outcome_counterfactual_scores_atom_best(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root, _record())

    report = analyze(
        atomization=_atomization(),
        candidate_root=candidate_root,
        expected_records=1,
        expected_candidates=2,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["promotion_authorized"] is False
    assert decision["tiny_counterfactual_noninferior"] is True
    assert decision["camp_retraining_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["analysis"]["future_outcome_labels_used_for_evaluation"] is True
    assert report["summary"]["atom_best_better_records"] == 1
    assert report["summary"]["guarded_atom_best_better_records"] == 1
    assert report["summary"]["atom_best_minus_selected_cost_mean"] < 0.0
    assert report["summary"]["guarded_atom_best_minus_selected_cost_mean"] < 0.0
    row = report["counterfactual_rows"][0]
    assert row["selected_index"] == 1
    assert row["atom_best_index"] == 0
    assert row["guarded_atom_best_index"] == 0
    assert row["relations"]["atom_best_hard_nonworse_than_selected"] is True


def test_external_context_atom_outcome_counterfactual_progress_guard_retains_selected(
    tmp_path: Path,
) -> None:
    record = _record()
    record["candidate_route_progress"] = [0.0, 10.0]
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root, record)

    report = analyze(
        atomization=_atomization(),
        candidate_root=candidate_root,
        expected_records=1,
        expected_candidates=2,
        progress_loss_budget_m=0.1,
    )

    row = report["counterfactual_rows"][0]
    assert row["atom_best_index"] == 0
    assert row["guarded_atom_best_index"] == 1
    assert row["guarded_would_change_selected_index"] is False
    assert report["summary"]["guarded_changed_records"] == 0
    assert report["final_decision"]["guarded_tiny_counterfactual_noninferior"] is True


def test_external_context_atom_outcome_counterfactual_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root, _record())

    report = analyze(
        atomization=_atomization(ready=False),
        candidate_root=candidate_root,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "source_status_ready",
        "source_passed",
        "source_authorized_atom_dry_run",
    ]


def test_external_context_atom_outcome_counterfactual_rejects_formal_seed(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root, _record(seed=11))

    report = analyze(
        atomization=_atomization(),
        candidate_root=candidate_root,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["record_checks"] if not check["passed"]]
    assert failed == ["record_0_formal_seed"]


def test_external_context_atom_outcome_counterfactual_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate_root = tmp_path / "candidate"
    atomization_path = tmp_path / "atomization.json"
    output_json = tmp_path / "counterfactual.json"
    output_md = tmp_path / "counterfactual.md"
    _write_log(candidate_root, _record())
    atomization_path.write_text(json.dumps(_atomization()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-atom-outcome-counterfactual",
            "--atomization_json",
            str(atomization_path),
            "--candidate_root",
            str(candidate_root),
            "--expected_records",
            "1",
            "--expected_candidates",
            "2",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "External Context Atom Outcome Counterfactual" in output_md.read_text(
        encoding="utf-8"
    )
