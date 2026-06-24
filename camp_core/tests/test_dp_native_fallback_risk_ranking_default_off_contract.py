from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.audit_diffusion_planner_dp_native_fallback_risk_ranking import (
    COMPLETE_STATUS,
    REJECT_STATUS,
    build_report,
)


def _reward(
    *,
    red_light: object = -1.0,
    lane_crossing: object = False,
    centerline: object = 0.0,
    total: object = -50.0,
) -> dict[str, object]:
    return {
        "red_light": red_light,
        "lane_crossing": lane_crossing,
        "static_crossing": False,
        "off_road_fraction": 0.0,
        "lane_near_frac": 0.0,
        "lane_wide_frac": 0.0,
        "centerline": centerline,
        "total": total,
    }


def _provenance(
    *,
    candidate_count: int,
    selected_index: int,
    **overrides: object,
) -> dict[str, object]:
    tensor = {"sha256": "fixed"}
    payload: dict[str, object] = {
        "payload_valid": True,
        "candidate_count": candidate_count,
        "post_selector_candidate_count": candidate_count,
        "selected_index": selected_index,
        "selected_index_in_range": True,
        "pre_post_tensor_hash_equal": True,
        "no_candidate_row_append": True,
        "no_coordinate_heading_speed_rewrite_by_camp": True,
        "selection_effect": False,
        "candidate_generation_effect": False,
        "candidate_tensor_mutation_effect": False,
        "outcome_label_input": False,
        "closed_loop_outcome_fields_read": False,
        "reference_blend_present": False,
        "pre_camp_scoring_tensor": tensor,
        "post_camp_selector_tensor": tensor,
    }
    payload.update(overrides)
    return payload


def _record(
    *,
    feasible_mask: list[bool] | None = None,
    selected_index: int = 0,
    rewards: list[dict[str, object]] | None = None,
    provenance_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    if rewards is None:
        rewards = [_reward(red_light=-1.0), _reward(red_light=-2.0)]
    if feasible_mask is None:
        feasible_mask = [False for _ in rewards]
    candidate_count = len(rewards)
    return {
        "selection_step": 0,
        "selected_index": selected_index,
        "num_candidates": candidate_count,
        "feasible_mask": feasible_mask,
        "infeasibility_reasons": [["dp_red_light"] for _ in rewards],
        "dp_candidate_rewards": rewards,
        "atoms": [[0.1, 0.2] for _ in rewards],
        "normalized_atoms": [[0.1, 0.2] for _ in rewards],
        "scores": [float(index) for index in range(candidate_count)],
        "selection_scores": [float(index) for index in range(candidate_count)],
        "camp_candidate_tensor_provenance": _provenance(
            candidate_count=candidate_count,
            selected_index=selected_index,
            **(provenance_overrides or {}),
        ),
        "candidate_generation_contract": {
            "guidance_enabled": False,
            "guidance": {"enabled": False},
            "changes_diffusion_planner_weights": False,
            "changes_camp_score": False,
            "reference_blend_steps": None,
        },
        "candidate_reference_blend_steps": None,
        "perfect_tracker_command_postselection": None,
        "traffic_light_hybrid_postselection": None,
        "underprogress_relaxation": None,
        "splice_shadow_rule": None,
    }


def _write_root(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    root = tmp_path / "eval"
    run = root / "sample_tl_seed109_tl_on_static"
    run.mkdir(parents=True)
    (run / "camp_selection_log.json").write_text(
        json.dumps(records),
        encoding="utf-8",
    )
    no_feasible = sum(
        1
        for record in records
        if isinstance(record.get("feasible_mask"), list)
        and not any(record["feasible_mask"])
    )
    summary = {
        "schema_version": "synthetic_default_off_contract_v1",
        "run_count": 1,
        "total_selection_records": len(records),
        "total_records_with_feasible_candidate": len(records) - no_feasible,
        "total_records_without_feasible_candidate": no_feasible,
    }
    (root / "broader_nonformal_eval_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    return root


def test_default_off_contract_scopes_to_records_without_feasible_candidate(
    tmp_path: Path,
) -> None:
    root = _write_root(
        tmp_path,
        [
            _record(feasible_mask=[False, False]),
            _record(feasible_mask=[True, False]),
        ],
    )

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["record_counts"]["records_total"] == 2
    assert report["record_counts"]["records_without_feasible_candidate"] == 1
    assert report["record_counts"]["records_with_feasible_candidate"] == 1


def test_default_off_contract_reports_ties_and_lower_cost_candidates(
    tmp_path: Path,
) -> None:
    root = _write_root(
        tmp_path,
        [
            _record(
                selected_index=1,
                rewards=[
                    _reward(red_light=-1.0, lane_crossing=True),
                    _reward(red_light=-1.0, lane_crossing=True),
                    _reward(red_light=-3.0, lane_crossing=False),
                ],
            )
        ],
    )

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    ranking = report["record_audits"][0]["ranking"]

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert ranking["red"]["min_indices"] == [0, 1]
    assert ranking["red"]["selected_is_min"] is True
    assert ranking["lane"]["lower_cost_candidate_indices"] == [2]


def test_default_off_contract_fails_closed_on_missing_or_invalid_costs(
    tmp_path: Path,
) -> None:
    reward = _reward(red_light="bad")
    del reward["centerline"]
    root = _write_root(tmp_path, [_record(rewards=[reward, _reward()])])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_required_record_costs_present" in report["final_decision"][
        "failed_checks"
    ]
    assert "reward_0_red_light_not_numeric" in errors
    assert "dp_candidate_rewards_0_lane_fields_missing:centerline" in errors


def test_default_off_contract_rejects_provenance_mutation_paths(
    tmp_path: Path,
) -> None:
    root = _write_root(
        tmp_path,
        [
            _record(
                provenance_overrides={
                    "reference_blend_present": True,
                    "closed_loop_outcome_fields_read": True,
                    "candidate_tensor_mutation_effect": True,
                }
            )
        ],
    )

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_no_candidate_rewrite_evidence" in report["final_decision"][
        "failed_checks"
    ]
    assert "provenance_reference_blend_present_false_failed" in errors
    assert "provenance_closed_loop_outcome_fields_read_false_failed" in errors
    assert "provenance_candidate_tensor_mutation_effect_false_failed" in errors


def test_default_off_contract_keeps_training_and_promotion_forbidden(
    tmp_path: Path,
) -> None:
    root = _write_root(tmp_path, [_record()])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    decision = report["final_decision"]

    assert decision["status"] == COMPLETE_STATUS
    for flag in [
        "replay_execution_authorized",
        "candidate_generation_authorized",
        "camp_training_authorized",
        "camp_retraining_authorized",
        "dp_modification_authorized",
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
    ]:
        assert decision[flag] is False
