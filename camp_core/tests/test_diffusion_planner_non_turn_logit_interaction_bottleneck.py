from __future__ import annotations

import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (
    build_non_turn_logit_interaction_payload,
)
from scripts.integrations.analyze_diffusion_planner_non_turn_logit_interaction_bottleneck import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    main,
)


def _outcome(
    value: float,
    *,
    feasible: bool = True,
    progress_m: float = 10.0,
    collision: bool = False,
    near_miss: bool = False,
    lane: bool = False,
    red: bool = False,
) -> dict:
    return {
        "value": value,
        "feasible": feasible,
        "progress_m": progress_m,
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane,
        "red_light_violation": red,
        "mean_jerk_mps3": 1.0,
        "mean_lateral_acceleration_mps2": 0.2,
    }


def _payload() -> dict:
    return build_non_turn_logit_interaction_payload(
        candidate_route_progress=[10.0, 10.0, 8.0],
        candidate_dp_prior_jerk_excess_cost=[0.0, 0.0, 5.0],
        candidate_count=3,
    )


def _record(seed: int = 1) -> dict:
    payload = _payload()
    record = {
        "seed": seed,
        "num_candidates": 3,
        "non_turn_logit_interaction_payload_logging": payload,
        "candidate_closed_loop_outcomes": [
            _outcome(0.0, progress_m=10.0),
            _outcome(1.0, progress_m=10.0),
            _outcome(-1.0, feasible=False, progress_m=8.0, lane=True),
        ],
    }
    record.update(payload["latency_ms"])
    return record


def _write_log(tmp_path: Path, rows: list[dict]) -> Path:
    root = tmp_path / "run_seed_1"
    root.mkdir()
    (root / "camp_selection_log.json").write_text(
        json.dumps(rows),
        encoding="utf-8",
    )
    return root


def _separability_report(*, rejected: bool = True) -> dict:
    return {
        "final_decision": {
            "status": (
                "non_turn_logit_interaction_outcome_separability_rejected"
                if rejected
                else "non_turn_logit_interaction_outcome_separability_promising_for_certificate_design"
            ),
            "passed": not rejected,
            "primary_gap": "comfort_progress_interaction_does_not_separate_candidates",
            "authorized_next_work": (
                "diagnose_non_turn_logit_interaction_bottleneck_before_retraining"
            ),
            "promising_screen_count": 0,
        },
        "ranked_screens": [
            {
                "screen_name": "comfort_progress_interaction_cost >= 0",
                "descriptor": "comfort_progress_interaction_cost",
                "threshold": 0.0,
                "atom_candidate_eligible": True,
                "harmful_block_rate": 1.0,
                "beneficial_retain_rate": 0.0,
                "allowed_harmful_rate": 0.0,
                "blocked_count": 2,
                "allowed_count": 0,
            },
            {
                "screen_name": "comfort_progress_interaction_cost >= 1",
                "descriptor": "comfort_progress_interaction_cost",
                "threshold": 1.0,
                "atom_candidate_eligible": True,
                "harmful_block_rate": 1.0,
                "beneficial_retain_rate": 1.0,
                "allowed_harmful_rate": 0.0,
                "blocked_count": 1,
                "allowed_count": 1,
            },
        ],
    }


def test_non_turn_interaction_bottleneck_diagnoses_rejected_screen(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [root],
        separability_report=_separability_report(),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["records"]["class_counts"]["beneficial_alternative"] == 2
    assert report["records"]["class_counts"]["harmful_alternative"] == 2
    assert report["diagnosis"]["primary_bottleneck"] == (
        "zero_threshold_blocks_all_beneficial"
    )
    assert report["diagnosis"]["harmful_reason_counts"]["infeasible"] == 2
    assert report["diagnosis"]["harmful_reason_counts"]["lane_worse"] == 2
    assert "comfort_progress_interaction_cost" in report["feature_summaries"]


def test_non_turn_interaction_bottleneck_blocks_when_source_not_rejected(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [root],
        separability_report=_separability_report(rejected=False),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["source_gate"]["passed"] is False


def test_non_turn_interaction_bottleneck_rejects_outcome_inside_payload(
    tmp_path: Path,
) -> None:
    record = _record()
    record["non_turn_logit_interaction_payload_logging"][
        "candidate_closed_loop_outcomes"
    ] = []
    root = _write_log(tmp_path, [record])

    with pytest.raises(ValueError, match="embeds outcome labels"):
        analyze(
            [root],
            separability_report=_separability_report(),
            expected_logs=1,
            expected_records=1,
            expected_candidates=3,
        )


def test_non_turn_interaction_bottleneck_forbids_formal_seed(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path, [_record(seed=11)])

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze(
            [root],
            separability_report=_separability_report(),
            expected_logs=1,
            expected_records=1,
            expected_candidates=3,
            fail_on_formal_seeds=True,
        )


def test_non_turn_interaction_bottleneck_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = _write_log(tmp_path, [_record(), _record()])
    separability_path = tmp_path / "separability.json"
    output_json = tmp_path / "bottleneck.json"
    output_md = tmp_path / "bottleneck.md"
    separability_path.write_text(
        json.dumps(_separability_report()),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze_diffusion_planner_non_turn_logit_interaction_bottleneck.py",
            "--root",
            str(root),
            "--separability_json",
            str(separability_path),
            "--expected_logs",
            "1",
            "--expected_records",
            "2",
            "--expected_candidates",
            "3",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    markdown = output_md.read_text(encoding="utf-8")
    assert "Non-Turn-Logit Interaction Bottleneck Diagnosis" in markdown
    assert "comfort_progress_interaction_cost" in markdown
