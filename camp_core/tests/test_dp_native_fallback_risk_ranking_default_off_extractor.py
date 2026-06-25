from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.extract_diffusion_planner_dp_native_fallback_risk_records import (
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    build_extraction_report,
    main,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_implementation.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_STATIC_CONTRACT_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_default_off_extractor_"
    "post_implementation_static_contract_only"
)


def _reward(*, red_light: object = -1.0, centerline: object = 0.0) -> dict[str, object]:
    return {
        "red_light": red_light,
        "lane_crossing": False,
        "static_crossing": False,
        "off_road_fraction": 0.0,
        "lane_near_frac": 0.0,
        "lane_wide_frac": 0.0,
        "centerline": centerline,
        "total": -50.0,
    }


def _record(
    *,
    selected_index: int = 0,
    rewards: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    rewards = rewards or [_reward(red_light=-1.0), _reward(red_light=-2.0)]
    candidate_count = len(rewards)
    tensor = {"sha256": "fixed"}
    return {
        "selection_step": 0,
        "selected_index": selected_index,
        "num_candidates": candidate_count,
        "feasible_mask": [False for _ in rewards],
        "infeasibility_reasons": [["dp_red_light"] for _ in rewards],
        "dp_candidate_rewards": rewards,
        "atoms": [[0.1, 0.2] for _ in rewards],
        "normalized_atoms": [[0.1, 0.2] for _ in rewards],
        "scores": [0.0 for _ in rewards],
        "selection_scores": [0.0 for _ in rewards],
        "camp_candidate_tensor_provenance": {
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
        },
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
    summary = {
        "schema_version": "synthetic_extractor_v1",
        "run_count": 1,
        "total_selection_records": len(records),
        "total_records_with_feasible_candidate": 0,
        "total_records_without_feasible_candidate": len(records),
    }
    (root / "broader_nonformal_eval_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    return root


def test_extractor_is_default_off_and_does_not_read_missing_root(
    tmp_path: Path,
) -> None:
    report = build_extraction_report(
        evaluation_root=tmp_path / "missing",
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["fallback_risk_records"] == []
    assert report["record_counts"]["records_without_feasible_candidate"] == 0


def test_extractor_enabled_emits_slim_records(tmp_path: Path) -> None:
    root = _write_root(
        tmp_path,
        [
            _record(
                selected_index=1,
                rewards=[
                    _reward(red_light=-1.0),
                    _reward(red_light=-1.0),
                    _reward(red_light=-3.0),
                ],
            )
        ],
    )

    report = build_extraction_report(
        evaluation_root=root,
        enabled=True,
        expected_no_feasible_records=1,
    )
    record = report["fallback_risk_records"][0]

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["record_counts"]["records_without_feasible_candidate"] == 1
    assert record["selected_index"] == 1
    assert record["ranking"]["red"]["min_indices"] == [0, 1]
    assert record["ranking"]["red"]["selected_is_min"] is True


def test_extractor_enabled_fails_closed_on_bad_cost_fields(tmp_path: Path) -> None:
    bad = _reward(red_light="bad")
    root = _write_root(tmp_path, [_record(rewards=[bad, _reward()])])

    report = build_extraction_report(
        evaluation_root=root,
        enabled=True,
        expected_no_feasible_records=1,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_required_record_costs_present" in report["final_decision"][
        "failed_checks"
    ]


def test_extractor_markdown_records_nonpromotion_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(
        build_extraction_report(evaluation_root=tmp_path / "missing", enabled=False)
    )

    assert "status=dp_native_fallback_risk_extractor_default_off_disabled" in markdown
    assert "training_authorized=False" in markdown
    assert "candidate_generation_authorized=False" in markdown
    assert "dp_modification_authorized=False" in markdown
    assert "camp_over_dp_top1_claim_authorized=False" in markdown


def test_extractor_cli_writes_outputs_when_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_root(tmp_path, [_record()])
    output_json = tmp_path / "out" / "extractor.json"
    output_md = tmp_path / "out" / "extractor.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "extractor",
            "--evaluation_root",
            str(root),
            "--enable_default_off_fallback_risk_extractor",
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
    assert "training_authorized=False" in output_md.read_text(encoding="utf-8")


def test_implementation_doc_records_current_head_revalidation() -> None:
    text = IMPLEMENTATION_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_current_head_revalidated_latest",
        "camp_head_at_revalidation=848040bd08c4361af2eb88972615f3147b9bce58",
        "camp_origin_main_at_revalidation=848040bd08c4361af2eb88972615f3147b9bce58",
        "github_refs_heads_main_at_revalidation=848040bd08c4361af2eb88972615f3147b9bce58",
        "autodl_CAMP_HEAD_before_gate=848040bd08c4361af2eb88972615f3147b9bce58",
        "autodl_CAMP_origin_main_before_gate=848040bd08c4361af2eb88972615f3147b9bce58",
        "autodl_DP_HEAD_before_gate=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_authorization_status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head",
        "prior_authorization_autodl_verified=True",
        "implementation_change_required=False",
        "existing_extractor_revalidated=True",
        "default_off_required=True",
        "enabled_default=False",
        "explicit_enable_flag=--enable_default_off_fallback_risk_extractor",
        "read_only_selection_log_input_only=True",
        "records_scope=records_without_feasible_candidate_only",
        "output_json_or_markdown_only=True",
        "fallback_risk_records_are_diagnostic_only=True",
        "local_py_compile_exit=0",
        "local_target_pytest=60 passed",
        "local_git_diff_check_exit=0",
        "autodl_CAMP_HEAD_after_sync=60249743c5658db73626c17ac5125ab1b5ef39a2",
        "autodl_CAMP_origin_main_after_sync=60249743c5658db73626c17ac5125ab1b5ef39a2",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=60 passed",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_gate=dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_post_implementation_static_contract_only",
        NEXT_STATIC_CONTRACT_GATE,
    ]:
        assert needle in text


def test_iteration_audit_tail_records_extractor_implementation() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-120:])

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_current_head_revalidated_latest",
        "camp_head_at_revalidation=848040bd08c4361af2eb88972615f3147b9bce58",
        "autodl_DP_HEAD_before_gate=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_authorization_status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head",
        "prior_authorization_autodl_verified=True",
        "implementation_change_required=False",
        "existing_extractor_revalidated=True",
        "default_off_required=True",
        "enabled_default=False",
        "local_py_compile_exit=0",
        "local_target_pytest=60 passed",
        "local_git_diff_check_exit=0",
        "autodl_CAMP_HEAD_after_sync=60249743c5658db73626c17ac5125ab1b5ef39a2",
        "autodl_CAMP_origin_main_after_sync=60249743c5658db73626c17ac5125ab1b5ef39a2",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=60 passed",
        "autodl_git_diff_check_exit=0",
        "autodl_audit_tail_gate=dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_post_implementation_static_contract_only",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_CONTRACT_GATE,
    ]:
        assert needle in tail

    assert tail.rstrip().endswith(f"`{NEXT_STATIC_CONTRACT_GATE}`")
