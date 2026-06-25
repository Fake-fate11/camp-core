from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.audit_diffusion_planner_dp_native_fallback_risk_ranking import (
    COMPLETE_STATUS,
    REJECT_STATUS,
    build_report,
)
from scripts.integrations.extract_diffusion_planner_dp_native_fallback_risk_records import (
    DISABLED_STATUS,
    build_extraction_report,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_TESTS_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_AUTHORIZATION_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_default_off_extractor_implementation_"
    "authorization_only"
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
    assert report["final_decision"]["all_infeasible_records_added_to_feasible_training"] is False
    assert report["final_decision"]["feasible_ranking_master_change_authorized"] is False


def test_default_off_extractor_disabled_does_not_read_or_emit_records(
    tmp_path: Path,
) -> None:
    report = build_extraction_report(
        evaluation_root=tmp_path / "missing-artifact",
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["enabled"] is False
    assert report["final_decision"]["fallback_risk_extractor_output_written"] is False
    assert report["fallback_risk_records"] == []
    assert report["record_counts"]["records_total"] == 0
    assert report["record_counts"]["records_without_feasible_candidate"] == 0
    assert report["analysis"]["read_only"] is True
    assert report["analysis"]["replay_executed"] is False
    assert report["analysis"]["candidate_generation_executed"] is False
    assert report["analysis"]["camp_training_executed"] is False


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


def test_default_off_contract_cost_hinges_are_nonnegative_and_finite(
    tmp_path: Path,
) -> None:
    root = _write_root(
        tmp_path,
        [
            _record(
                selected_index=0,
                rewards=[
                    _reward(red_light=2.0, centerline=-3.0, total=5.0),
                    _reward(red_light=-4.0, centerline=1.0, total=-7.0),
                ],
            )
        ],
    )

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    ranking = report["record_audits"][0]["ranking"]

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert ranking["red"]["costs"] == [0.0, 4.0]
    assert ranking["lane"]["costs"] == [3.0, 0.0]
    assert ranking["quality"]["costs"] == [0.0, 7.0]
    for metric in ("red", "lane", "quality"):
        assert all(cost >= 0.0 for cost in ranking[metric]["costs"])


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


def test_default_off_contract_fails_closed_on_missing_total_and_nonfinite_lane(
    tmp_path: Path,
) -> None:
    reward = _reward(centerline=float("nan"))
    del reward["total"]
    root = _write_root(tmp_path, [_record(rewards=[reward, _reward()])])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_required_record_costs_present" in report["final_decision"][
        "failed_checks"
    ]
    assert "dp_candidate_rewards_0_total_missing" in errors
    assert "reward_0_centerline_not_finite" in errors


def test_default_off_contract_rejects_selected_index_and_count_mismatches(
    tmp_path: Path,
) -> None:
    record = _record(selected_index=3)
    record["feasible_mask"] = [False]
    record["dp_candidate_rewards"] = [_reward(), _reward(), _reward()]
    record["atoms"] = [[0.1, 0.2]]
    record["normalized_atoms"] = [[0.1, 0.2]]
    record["scores"] = [0.0]
    record["selection_scores"] = [0.0]
    root = _write_root(tmp_path, [record])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_selected_index_in_range" in report["final_decision"][
        "failed_checks"
    ]
    assert "all_candidate_counts_unchanged" in report["final_decision"][
        "failed_checks"
    ]
    assert "selected_index_out_of_range" in errors
    assert "feasible_mask_candidate_count_mismatch" in errors
    assert "atoms_candidate_count_mismatch" in errors
    assert "scores_candidate_count_mismatch" in errors


def test_default_off_contract_rejects_nonpositive_candidate_count(
    tmp_path: Path,
) -> None:
    record = _record()
    record["num_candidates"] = 0
    root = _write_root(tmp_path, [record])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "num_candidates_not_positive" in errors


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


def test_default_off_contract_requires_provenance_payload(tmp_path: Path) -> None:
    record = _record()
    del record["camp_candidate_tensor_provenance"]
    root = _write_root(tmp_path, [record])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_candidate_counts_unchanged" in report["final_decision"][
        "failed_checks"
    ]
    assert "all_provenance_prepost_hashes_clean" in report["final_decision"][
        "failed_checks"
    ]
    assert "camp_candidate_tensor_provenance_missing" in errors


def test_default_off_contract_rejects_pre_post_hash_mismatch(
    tmp_path: Path,
) -> None:
    root = _write_root(
        tmp_path,
        [
            _record(
                provenance_overrides={
                    "pre_camp_scoring_tensor": {"sha256": "pre"},
                    "post_camp_selector_tensor": {"sha256": "post"},
                }
            )
        ],
    )

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_required_record_costs_present" in report["final_decision"][
        "failed_checks"
    ]
    assert "provenance_pre_post_sha256_match_if_present_failed" in errors


def test_default_off_contract_rejects_candidate_count_change_and_row_append(
    tmp_path: Path,
) -> None:
    record = _record()
    record["camp_candidate_tensor_provenance"].update(
        {
            "candidate_count": 3,
            "post_selector_candidate_count": 3,
            "no_candidate_row_append": False,
            "no_coordinate_heading_speed_rewrite_by_camp": False,
            "selection_effect": True,
            "candidate_generation_effect": True,
        }
    )
    root = _write_root(tmp_path, [record])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_candidate_counts_unchanged" in report["final_decision"][
        "failed_checks"
    ]
    assert "all_no_candidate_rewrite_evidence" in report["final_decision"][
        "failed_checks"
    ]
    assert "provenance_candidate_count_matches_failed" in errors
    assert "provenance_post_selector_candidate_count_matches_failed" in errors
    assert "provenance_no_candidate_row_append_failed" in errors
    assert "provenance_no_coordinate_heading_speed_rewrite_by_camp_failed" in errors
    assert "provenance_selection_effect_false_failed" in errors
    assert "provenance_candidate_generation_effect_false_failed" in errors


def test_default_off_contract_rejects_guidance_postselection_and_splice_paths(
    tmp_path: Path,
) -> None:
    record = _record()
    record["candidate_generation_contract"] = {
        "guidance_enabled": True,
        "guidance": {"enabled": True},
        "changes_diffusion_planner_weights": True,
        "changes_camp_score": True,
        "reference_blend_steps": 2,
    }
    record["candidate_reference_blend_steps"] = [0, 1]
    record["perfect_tracker_command_postselection"] = {"enabled": True}
    record["traffic_light_hybrid_postselection"] = {"postselection_executed": True}
    record["underprogress_relaxation"] = {"relaxation_enabled": True}
    record["splice_shadow_rule"] = {"trajectory_rewrite_authorized": True}
    root = _write_root(tmp_path, [record])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    errors = report["provenance_summary"]["all_record_errors"][0]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_no_candidate_rewrite_evidence" in report["final_decision"][
        "failed_checks"
    ]
    for expected in [
        "candidate_generation_contract_guidance_disabled_failed",
        "candidate_generation_contract_dp_weights_unchanged_failed",
        "candidate_generation_contract_camp_score_unchanged_failed",
        "candidate_generation_contract_guidance_payload_disabled_failed",
        "candidate_generation_contract_reference_blend_disabled_failed",
        "candidate_reference_blend_steps_all_zero_failed",
        "perfect_tracker_command_postselection_disabled_failed",
        "traffic_light_hybrid_postselection_disabled_failed",
        "underprogress_relaxation_disabled_failed",
        "splice_shadow_rule_disabled_failed",
    ]:
        assert expected in errors


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
    assert decision["hard_feasibility_relaxation_authorized"] is False
    assert decision["all_infeasible_records_added_to_feasible_training"] is False
    assert decision["candidate_trajectory_rewrite_authorized"] is False
    assert decision["postprocess_postselection_authorized"] is False


def test_default_off_unit_tests_doc_records_current_head_revalidation() -> None:
    text = UNIT_TESTS_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_current_head_revalidated",
        "camp_head_at_revalidation=fe0ebc23e3ee2b1fcc51b402228262d4b1500bd4",
        "camp_origin_main_at_revalidation=fe0ebc23e3ee2b1fcc51b402228262d4b1500bd4",
        "github_refs_heads_main_at_revalidation=fe0ebc23e3ee2b1fcc51b402228262d4b1500bd4",
        "autodl_CAMP_HEAD_at_revalidation=fe0ebc23e3ee2b1fcc51b402228262d4b1500bd4",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_plan_status=fallback_risk_ranking_default_off_unit_tests_plan_ready_tests_only_gate",
        "camp_head_at_revalidation=3b81b616bd36dd7971390b9846d0f9e45295e634",
        "camp_origin_main_at_revalidation=3b81b616bd36dd7971390b9846d0f9e45295e634",
        "github_refs_heads_main_at_revalidation=3b81b616bd36dd7971390b9846d0f9e45295e634",
        "autodl_CAMP_HEAD_at_revalidation=3b81b616bd36dd7971390b9846d0f9e45295e634",
        "camp_head_at_revalidation=3512ae0e883952ff2342c8ea714fbcd811ac5b37",
        "camp_origin_main_at_revalidation=3512ae0e883952ff2342c8ea714fbcd811ac5b37",
        "github_refs_heads_main_at_revalidation=3512ae0e883952ff2342c8ea714fbcd811ac5b37",
        "autodl_CAMP_HEAD_at_revalidation=3512ae0e883952ff2342c8ea714fbcd811ac5b37",
        "prior_unit_tests_plan_head_at_revalidation=bfa29bd54f3d5a6aa52fa87350f7fe2845b79597",
        "default_off_contract_tests_pinned=True",
        "tests_only=True",
        "synthetic_static_unit_tests_only=True",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        NEXT_AUTHORIZATION_GATE,
    ]:
        assert needle in text


def test_iteration_audit_records_default_off_unit_tests_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_current_head_revalidated",
        "camp_head_at_revalidation=fe0ebc23e3ee2b1fcc51b402228262d4b1500bd4",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_plan_status=fallback_risk_ranking_default_off_unit_tests_plan_ready_tests_only_gate",
        "default_off_contract_tests_pinned=True",
        "tests_only=True",
        "synthetic_static_unit_tests_only=True",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "dp_modification_authorized=False",
        NEXT_AUTHORIZATION_GATE,
    ]:
        assert needle in audit

    for needle in [
        "status=fallback_risk_ranking_default_off_unit_tests_current_head_revalidated",
        "unit_tests_doc=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests.md",
        "unit_tests_contract=camp_core/tests/test_dp_native_fallback_risk_ranking_default_off_contract.py",
        "camp_head_at_revalidation=3512ae0e883952ff2342c8ea714fbcd811ac5b37",
        "autodl_CAMP_HEAD_at_revalidation=3512ae0e883952ff2342c8ea714fbcd811ac5b37",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_plan_status=fallback_risk_ranking_default_off_unit_tests_plan_ready_tests_only_gate",
        "prior_unit_tests_plan_head_at_revalidation=bfa29bd54f3d5a6aa52fa87350f7fe2845b79597",
        "tests_only=True",
        "synthetic_static_unit_tests_only=True",
        "default_off_contract_tests_pinned=True",
        "production_implementation_edit_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in audit

    assert f"`{NEXT_AUTHORIZATION_GATE}`" in audit
