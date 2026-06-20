from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_observable_label_alignment import (
    FORMAL_SEED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    PairSpec,
    analyze,
)


def _payload() -> dict:
    return {
        "schema_version": "dp_camp_observable_state_logging_v1",
        "selection_effect": False,
        "future_outcome_leakage": False,
        "candidate_count": 2,
    }


def _outcomes() -> list[dict]:
    return [
        {
            "candidate_index": 0,
            "progress_m": 10.0,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": False,
            "mean_jerk_mps3": 1.0,
            "mean_lateral_acceleration_mps2": 1.0,
        },
        {
            "candidate_index": 1,
            "progress_m": 9.5,
            "collision": False,
            "near_miss": False,
            "lane_violation": False,
            "red_light_violation": True,
            "mean_jerk_mps3": 1.2,
            "mean_lateral_acceleration_mps2": 1.1,
        },
    ]


def _base_record() -> dict:
    return {
        "selected_index": 0,
        "feasible_mask": [True, True],
        "infeasibility_reasons": [[], []],
        "atom_names": ["progress", "red"],
        "atom_schema_version": "unit",
        "used_fallback": False,
        "atoms": [[1.0, 0.0], [0.5, 1.0]],
        "normalized_atoms": [[1.0, 0.0], [0.5, 1.0]],
        "scores": [0.0, 1.0],
        "selection_scores": [0.0, 1.0],
        "weights": [0.5, 0.5],
        "selection_weights": [0.5, 0.5],
        "candidate_step_reach": [1.0, 0.9],
        "candidate_dp_prior_deviation_cost": [0.0, 0.1],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 1.0],
        "candidate_full_horizon_planned_red_light_cost": [0.0, 1.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.2],
        "candidate_perfect_tracker_first_step_reach_m": [1.0, 0.9],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.8],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [1.0, 1.2],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [1.0, 1.1],
    }


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")


def _roots(tmp_path: Path, *, mismatch: bool = False, missing_labels: bool = False):
    observable_root = tmp_path / "observable"
    label_root = tmp_path / "labels"
    pair = PairSpec(
        run_id="unit",
        observable_rel="unit/camp_selection_log.json",
        label_rel="route/seed_1/npc_0/spawn_0p3/tl_off/static/camp_selection_log.json",
    )
    observable = _base_record()
    observable["observable_state_logging"] = _payload()
    observable["candidate_closed_loop_outcomes"] = None
    labeled = copy.deepcopy(_base_record())
    labeled["observable_state_logging"] = None
    labeled["candidate_closed_loop_outcomes"] = None if missing_labels else _outcomes()
    if mismatch:
        labeled["atoms"][1][1] = 2.0
    _write(observable_root / pair.observable_rel, [observable])
    _write(label_root / pair.label_rel, [labeled])
    return observable_root, label_root, (pair,)


def test_observable_label_alignment_accepts_exact_candidate_match(tmp_path: Path) -> None:
    observable_root, label_root, pairs = _roots(tmp_path)

    report = analyze(
        observable_root=observable_root,
        label_root=label_root,
        records=1,
        pair_specs=pairs,
        fail_on_formal_seeds=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "offline_observable_descriptor_separability_screen_only"
    )
    assert report["counts"]["records_with_mismatch"] == 0
    assert report["analysis"]["future_outcome_labels_used_for_features"] is False


def test_observable_label_alignment_rejects_candidate_mismatch(tmp_path: Path) -> None:
    observable_root, label_root, pairs = _roots(tmp_path, mismatch=True)

    report = analyze(
        observable_root=observable_root,
        label_root=label_root,
        records=1,
        pair_specs=pairs,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "observable_and_label_candidate_sets_not_aligned"
    )
    assert report["final_decision"]["authorized_next_work"] == (
        "predeclare_matched_observable_outcome_label_collection_plan_only"
    )
    assert report["pairs"][0]["numeric_mismatches"]["atoms"] == 1


def test_observable_label_alignment_rejects_missing_outcome_labels(
    tmp_path: Path,
) -> None:
    observable_root, label_root, pairs = _roots(tmp_path, missing_labels=True)

    report = analyze(
        observable_root=observable_root,
        label_root=label_root,
        records=1,
        pair_specs=pairs,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["primary_gap"] == (
        "label_records_missing_candidate_outcomes"
    )


def test_observable_label_alignment_rejects_formal_seed_when_forbidden(
    tmp_path: Path,
) -> None:
    observable_root, label_root, pairs = _roots(tmp_path)
    formal_pair = PairSpec(
        run_id="formal",
        observable_rel=pairs[0].observable_rel,
        label_rel="route/seed_11/npc_0/spawn_0p3/tl_off/static/camp_selection_log.json",
    )
    source = label_root / pairs[0].label_rel
    target = label_root / formal_pair.label_rel
    _write(target, json.loads(source.read_text(encoding="utf-8")))

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze(
            observable_root=observable_root,
            label_root=label_root,
            records=1,
            pair_specs=(formal_pair,),
            fail_on_formal_seeds=True,
        )

    report = analyze(
        observable_root=observable_root,
        label_root=label_root,
        records=1,
        pair_specs=(formal_pair,),
        fail_on_formal_seeds=False,
    )
    assert report["final_decision"]["status"] == FORMAL_SEED_STATUS
