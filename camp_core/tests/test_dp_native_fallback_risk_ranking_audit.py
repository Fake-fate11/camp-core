from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.audit_diffusion_planner_dp_native_fallback_risk_ranking import (
    COMPLETE_STATUS,
    NEXT_DESIGN_GATE,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_audit.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _reward(
    *,
    red_light: float = -25.0,
    lane_crossing: bool = False,
    centerline: float = -0.01,
    total: float = -50.0,
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
    candidate_count: int = 3,
    selected_index: int = 1,
    post_candidate_count: int | None = None,
) -> dict[str, object]:
    if post_candidate_count is None:
        post_candidate_count = candidate_count
    tensor = {"sha256": "abc123"}
    return {
        "payload_valid": True,
        "candidate_count": candidate_count,
        "post_selector_candidate_count": post_candidate_count,
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


def _record(
    *,
    selected_index: int = 1,
    post_candidate_count: int | None = None,
    rewards: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if rewards is None:
        rewards = [
            _reward(red_light=-4.0, lane_crossing=True, centerline=-0.02),
            _reward(red_light=-1.0, lane_crossing=True, centerline=-0.05),
            _reward(red_light=-3.0, lane_crossing=False, centerline=0.0),
        ]
    candidate_count = len(rewards)
    return {
        "selection_step": 0,
        "selected_index": selected_index,
        "num_candidates": candidate_count,
        "feasible_mask": [False for _ in rewards],
        "infeasibility_reasons": [["dp_lane_crossing"] for _ in rewards],
        "dp_candidate_rewards": rewards,
        "atoms": [[0.1, 0.2] for _ in rewards],
        "normalized_atoms": [[0.1, 0.2] for _ in rewards],
        "scores": [0.3, 0.2, 0.1][:candidate_count],
        "selection_scores": [0.3, 0.2, 0.1][:candidate_count],
        "camp_candidate_tensor_provenance": _provenance(
            candidate_count=candidate_count,
            selected_index=selected_index,
            post_candidate_count=post_candidate_count,
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


def _write_eval_root(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    root = tmp_path / "eval"
    run = root / "sample_tl_seed109_tl_on_static"
    run.mkdir(parents=True)
    (run / "camp_selection_log.json").write_text(
        json.dumps(records),
        encoding="utf-8",
    )
    summary = {
        "schema_version": "dp_native_static_dp_reward_broader_nonformal_eval_development_result_v1",
        "run_count": 1,
        "total_selection_records": len(records),
        "total_records_with_feasible_candidate": 0,
        "total_records_without_feasible_candidate": len(records),
        "total_selected_index_in_range_records": len(records),
        "total_provenance_records": len(records),
        "total_payload_valid_records": len(records),
        "total_prepost_equal_records": len(records),
        "total_no_candidate_row_append_records": len(records),
        "total_no_coordinate_heading_speed_rewrite_records": len(records),
    }
    (root / "broader_nonformal_eval_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    return root


def test_fallback_risk_audit_counts_least_bad_metrics(tmp_path: Path) -> None:
    root = _write_eval_root(tmp_path, [_record()])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)
    decision = report["final_decision"]

    assert decision["status"] == COMPLETE_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == NEXT_DESIGN_GATE
    assert decision["existing_fallback_uniformly_least_bad_red"] is True
    assert decision["existing_fallback_uniformly_least_bad_lane"] is False
    assert decision["lower_risk_fixed_candidate_exists_under_logged_costs"] is True
    assert report["ranking_summary"]["lane"]["selected_not_min_count"] == 1
    assert decision["camp_training_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False


def test_fallback_risk_audit_rejects_selected_index_out_of_range(
    tmp_path: Path,
) -> None:
    root = _write_eval_root(tmp_path, [_record(selected_index=4)])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_selected_index_in_range" in report["final_decision"]["failed_checks"]
    assert "all_required_record_costs_present" in report["final_decision"]["failed_checks"]


def test_fallback_risk_audit_rejects_missing_cost_field(tmp_path: Path) -> None:
    bad_rewards = [_reward(), _reward(), _reward()]
    del bad_rewards[1]["red_light"]
    root = _write_eval_root(tmp_path, [_record(rewards=bad_rewards)])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_required_record_costs_present" in report["final_decision"]["failed_checks"]


def test_fallback_risk_audit_rejects_candidate_count_mutation(
    tmp_path: Path,
) -> None:
    root = _write_eval_root(tmp_path, [_record(post_candidate_count=4)])

    report = build_report(evaluation_root=root, expected_no_feasible_records=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_candidate_counts_unchanged" in report["final_decision"]["failed_checks"]
    assert "all_required_record_costs_present" in report["final_decision"]["failed_checks"]


def test_fallback_risk_audit_markdown_keeps_nonpromotion_boundary(
    tmp_path: Path,
) -> None:
    root = _write_eval_root(tmp_path, [_record()])
    markdown = render_markdown(
        build_report(evaluation_root=root, expected_no_feasible_records=1)
    )

    assert "DP Native Fixed-Artifact Fallback Risk Ranking Audit" in markdown
    assert "candidate_generation_authorized=False" in markdown
    assert "camp_training_authorized=False" in markdown
    assert "does not claim safety benefit" in markdown


def test_fallback_risk_audit_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_eval_root(tmp_path, [_record()])
    output_json = tmp_path / "out" / "audit.json"
    output_md = tmp_path / "out" / "audit.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit",
            "--evaluation_root",
            str(root),
            "--expected_no_feasible_records",
            "1",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert "candidate_generation_authorized=False" in output_md.read_text(
        encoding="utf-8"
    )


def test_fallback_risk_audit_doc_pins_real_artifact_result() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=dp_native_fixed_artifact_fallback_risk_ranking_audit_complete",
        "passed=True",
        "records_without_feasible_candidate=15",
        'route_records_without_feasible_candidate={"nishishinjuku_lane_change": 4, "sample_tl": 11}',
        "| `dp_red_light_cost` | 15 | 14 | 1 |",
        "| `lane_related_cost` | 15 | 4 | 11 |",
        "| `dp_reward_quality_cost` | 15 | 15 | 0 |",
        "lower_risk_fixed_candidate_exists_under_logged_costs=True",
        "selected_index_in_range_all_no_feasible_records=True",
        "candidate_count_unchanged_all_no_feasible_records=True",
        "pre_post_tensor_hash_equal_all_no_feasible_records=True",
        "no_coordinate_heading_speed_rewrite_by_camp_all_no_feasible_records=True",
        "candidate_tensor_mutation_effect_all_no_feasible_records=False",
        "candidate_generation_effect_all_no_feasible_records=False",
        "fallback_risk_training_authorized_now=False",
        "camp_head_at_revalidation=61fc5256d6496626cbfa826445fdfc7317bead7a",
        "camp_origin_main_at_revalidation=61fc5256d6496626cbfa826445fdfc7317bead7a",
        "dp_head_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "remote_output_dir=/root/autodl-tmp/camp_dp_native_broader_nonformal_fixed_artifact_fallback_risk_ranking_audit_61fc525_20260625T053215Z",
        "remote_audit_json_sha256=52bb6f5168483cf6843a98214a21f1d597e31030eb1dbb47387a827e87732fcc",
        "remote_audit_md_sha256=843236dd8f0cdfaad4a3c52252bce922faed04aa0c8a05c97ddadc9276f5e75c",
        "remote_artifact_audit_exit=0",
        NEXT_DESIGN_GATE,
    ]:
        assert needle in text


def test_fallback_risk_audit_doc_forbids_nonpaper_routes() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "replay_execution_authorized=True",
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "dp_modification_authorized=True",
        "reference_blend_authorized=True",
        "guidance_authorized=True",
        "postprocess_postselection_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_iteration_audit_tail_records_current_head_ranking_audit_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-120:])

    for needle in [
        "status=dp_native_fixed_artifact_fallback_risk_ranking_audit_complete",
        "passed=True",
        "camp_head_at_revalidation=61fc5256d6496626cbfa826445fdfc7317bead7a",
        "dp_head_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "remote_audit_json_sha256=52bb6f5168483cf6843a98214a21f1d597e31030eb1dbb47387a827e87732fcc",
        "records_without_feasible_candidate=15",
        "lower_risk_fixed_candidate_exists_under_logged_costs=True",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_DESIGN_GATE,
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_design_plan_only`"
    )
