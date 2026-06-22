from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    analyze,
    main,
    render_markdown,
)


RUN_IDS = (
    "sample_tl59_seed1_npc0_tlon",
    "sample_tl59_seed2_npc4_tlon",
    "sample_tl59_seed3_npc4_tloff",
    "sample_normal2_seed1_npc0_tloff",
    "nishi_release_seed2_npc4_tlon",
    "nishi_lanechange_seed4_npc4_tloff",
)


def _outcome(
    index: int,
    *,
    progress: float,
    jerk: float,
    lateral: float,
    collision: bool = False,
    near_miss: bool = False,
    lane_violation: bool = False,
    red_light_violation: bool = False,
) -> dict[str, object]:
    return {
        "candidate_index": index,
        "progress_m": progress,
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane_violation,
        "red_light_violation": red_light_violation,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _record(*, fallback: bool = False, missing_outcome_field: bool = False) -> dict[str, object]:
    outcomes = [
        _outcome(0, progress=10.0, jerk=8.0, lateral=2.0, red_light_violation=True),
        _outcome(1, progress=9.8, jerk=1.0, lateral=0.5),
    ]
    outcomes.extend(
        _outcome(index, progress=7.0, jerk=6.0, lateral=1.0)
        for index in range(2, 8)
    )
    if missing_outcome_field:
        outcomes[1].pop("progress_m")
    return {
        "num_candidates": 8,
        "selected_index": 0,
        "feasible_mask": [not fallback] * 8,
        "candidate_horizon_union_planned_red_light_cost": [1.0, 0.0, *([0.0] * 6)],
        "candidate_closed_loop_outcomes": outcomes,
    }


def _write_logs(
    root: Path,
    *,
    formal_seed: bool = False,
    missing_outcome_field: bool = False,
) -> None:
    for run_id in RUN_IDS:
        actual_run_id = "sample_tl59_seed11_npc0_tlon" if formal_seed and run_id == RUN_IDS[0] else run_id
        run_root = root / actual_run_id
        run_root.mkdir(parents=True)
        fallback = run_id == "nishi_release_seed2_npc4_tlon"
        rows = [
            _record(
                fallback=fallback,
                missing_outcome_field=missing_outcome_field and index == 0,
            )
            for index in range(10)
        ]
        (run_root / "camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def _weight_sensitivity(
    *,
    include_records: bool = True,
    max_changed: int = 10,
) -> dict[str, object]:
    sensitivity_records = []
    for run_id in RUN_IDS:
        fallback = run_id == "nishi_release_seed2_npc4_tlon"
        for record_index in range(10):
            changed = (
                run_id == "sample_normal2_seed1_npc0_tloff"
                and record_index < max_changed
            )
            sensitivity_records.append(
                {
                    "run_id": run_id,
                    "record_index": record_index,
                    "global_index": len(sensitivity_records),
                    "selected_index": 0,
                    "fallback_retained": fallback,
                    "lambda_results": [
                        {
                            "lambda": 0.0,
                            "shadow_selected_index": 0,
                            "changed_selected_index": False,
                        },
                        {
                            "lambda": 1.0,
                            "shadow_selected_index": 1 if changed else 0,
                            "changed_selected_index": changed,
                        },
                    ],
                }
            )
    return {
        "final_decision": {
            "status": "candidate_set_consensus_shadow_atom_weight_sensitivity_ready",
            "passed": True,
            "weight_sensitivity_ready": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_weight_sensitivity_result_review_only"
            ),
            "max_changed_records": max_changed,
            "min_critical_positive_lambda": 0.25,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "lambda_grid": [0.0, 1.0],
        "sensitivity_summary": {
            "log_count": 6,
            "records": 60,
            "valid_records": 60,
            "available_records": 60,
            "ranking_signal_records": 50,
            "fallback_retained_records": 10,
            "formal_seed_log_count": 0,
            "record_error_counts": {},
            "critical_positive_lambda_records": 50,
            "min_critical_positive_lambda": 0.25,
            "lambda_grid": [0.0, 1.0],
            "by_lambda": [
                {"lambda": 0.0, "changed_records": 0, "changed_rate": 0.0},
                {"lambda": 1.0, "changed_records": max_changed, "changed_rate": max_changed / 60.0},
            ],
            "by_run": {
                run_id: {
                    "records": 10,
                    "ranking_signal_records": 0 if "release" in run_id else 10,
                    "fallback_retained_records": 10 if "release" in run_id else 0,
                    "max_changed_records": max_changed if "normal2" in run_id else 0,
                }
                for run_id in RUN_IDS
            },
        },
        "sensitivity_records": sensitivity_records if include_records else [],
    }


def test_shadow_atom_safety_score_evaluation_ready_on_synthetic_logs(tmp_path: Path) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        weight_sensitivity=_weight_sensitivity(),
        candidate_root=root,
    )
    decision = report["final_decision"]
    summary = report["evaluation_summary"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert summary["records"] == 60
    assert summary["outcome_available_records"] == 60
    assert summary["fallback_retained_records"] == 10
    assert summary["by_lambda"][0]["changed_records"] == 0
    assert summary["by_lambda"][1]["changed_records"] == 10
    assert summary["by_lambda"][1]["changed_cost_better_records"] == 10
    assert summary["by_lambda"][1]["changed_safety_cost_delta_mean"] < 0.0
    assert "nishi_release_seed2_npc4_tlon" in summary["no_change_runs"]
    assert "candidate_closed_loop_outcomes" in report["analysis"]["math_boundary"]


def test_shadow_atom_safety_score_evaluation_rejects_missing_source_records(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        weight_sensitivity=_weight_sensitivity(include_records=False),
        candidate_root=root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "all_records_valid" in failed
    assert "record_errors_empty" in failed
    assert report["evaluation_summary"]["record_error_counts"] == {
        "source_sensitivity_record_missing": 60
    }


def test_shadow_atom_safety_score_evaluation_rejects_missing_outcome_field(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, missing_outcome_field=True)

    report = analyze(
        weight_sensitivity=_weight_sensitivity(),
        candidate_root=root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_records_have_outcome_labels" in report["final_decision"]["failed_checks"]
    assert any(
        key.startswith("outcome_evaluation_error:")
        for key in report["evaluation_summary"]["record_error_counts"]
    )


def test_shadow_atom_safety_score_evaluation_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, formal_seed=True)

    report = analyze(
        weight_sensitivity=_weight_sensitivity(),
        candidate_root=root,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "no_formal_seed_logs" in failed
    assert "all_records_valid" in failed


def test_shadow_atom_safety_score_evaluation_markdown_states_boundaries(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)
    markdown = render_markdown(
        analyze(weight_sensitivity=_weight_sensitivity(), candidate_root=root)
    )

    assert "Candidate-Set Consensus Shadow Atom Safety-Score Evaluation" in markdown
    assert "Safety benefit evidence: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "result review only" in markdown
    assert "classical Benders" in markdown


def test_shadow_atom_safety_score_evaluation_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)
    source_json = tmp_path / "weight_sensitivity.json"
    output_json = tmp_path / "evaluation.json"
    output_md = tmp_path / "evaluation.md"
    source_json.write_text(json.dumps(_weight_sensitivity()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-shadow-atom-safety-score-evaluation",
            "--weight_sensitivity_json",
            str(source_json),
            "--candidate_root",
            str(root),
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
    assert payload["evaluation_summary"]["by_lambda"][1][
        "changed_cost_better_records"
    ] == 10
    assert "Safety-Score Evaluation" in output_md.read_text(encoding="utf-8")
