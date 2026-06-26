from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_design_plan.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_STATIC_REVIEW_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_remediation_static_contract_review_only"
)
NEXT_UNIT_TESTS_PLAN_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_default_off_unit_tests_plan_only"
)


def test_fallback_risk_remediation_design_uses_fixed_artifact_evidence() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "records_without_feasible_candidate=15",
        "dp_red_light_cost_selected_min_count=14/15",
        "dp_red_light_cost_lower_cost_fixed_candidate_available_count=1/15",
        "lane_related_cost_selected_min_count=4/15",
        "lane_related_cost_lower_cost_fixed_candidate_available_count=11/15",
        "dp_reward_quality_cost_selected_min_count=15/15",
        "lower_risk_fixed_candidate_exists_under_logged_costs=True",
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
    ]:
        assert needle in text


def test_fallback_risk_remediation_design_is_default_off_and_separate() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "default_off=True",
        "nondeployable_diagnostic_only=True",
        "fixed_candidate_set_only=True",
        "records_scope=records_without_feasible_candidate_only",
        "all_infeasible_records_relabelled_feasible=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "feasible_ranking_master_change_authorized=False",
        "hard_feasibility_relaxation_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
    ]:
        assert needle in text

    for forbidden in [
        "default_off=False",
        "nondeployable_diagnostic_only=False",
        "all_infeasible_records_relabelled_feasible=True",
        "all_infeasible_records_added_to_feasible_training=True",
        "feasible_ranking_master_change_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in text


def test_fallback_risk_remediation_design_preserves_math_contract() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    for needle in [
        "score_k(w)=a_k^T w",
        "candidate_features_fixed_before_weight_optimization=True",
        "candidate_features_independent_of_w_rank_and_selected_index=True",
        "fallback_cost_targets_nonnegative=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "new_atom_authorized_now=False",
        "training_authorized_now=False",
        "alpha_values_authorized_now=False",
    ]:
        assert needle in text


def test_fallback_risk_remediation_design_forbids_nonpaper_routes() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

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
        "candidate_generation_authorized=True",
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "dp_modification_authorized=True",
        "reference_blend_authorized=True",
        "guidance_authorized=True",
        "postprocess_postselection_authorized=True",
        "closed_loop_outcome_online_input_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_fallback_risk_remediation_design_next_gate_static_review_only() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")

    assert NEXT_STATIC_REVIEW_GATE in text
    assert "It must not implement the extractor" in text
    assert "train CAMP" in text


def test_fallback_risk_remediation_design_current_head_revalidation() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    current_1027_plan_marker = (
        "## Current-Head Revalidation After 9764f12 Ranking Audit Revalidation"
    )
    current_1027_plan = current_1027_plan_marker + text.split(
        current_1027_plan_marker
    )[-1]

    for needle in [
        "camp_head_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "camp_origin_main_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "github_refs_heads_main_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "autodl_CAMP_HEAD_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_ranking_revalidation_status=dp_native_fixed_artifact_fallback_risk_ranking_audit_complete",
        "prior_ranking_revalidation_failed_checks=[]",
        "prior_ranking_revalidation_json_sha256=52bb6f5168483cf6843a98214a21f1d597e31030eb1dbb47387a827e87732fcc",
        "This remains a plan-only gate",
        "camp_head_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4",
        "camp_origin_main_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4",
        "github_refs_heads_main_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4",
        "autodl_CAMP_HEAD_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4",
        "prior_ranking_revalidation_json_sha256=14c5bf7dfb6204ba8c47983f38cc326f5a4cca29ff63fb8f85a23cfef4437dd4",
        "prior_ranking_revalidation_md_sha256=3124737477f1d6b5721dcdf585fcb382096b4e3bf29921283a3ad11695280746",
        "camp_head_at_revalidation=e7315c42398ed095a7df3e2e7ba5bdcbb4b8a0bc",
        "camp_origin_main_at_revalidation=e7315c42398ed095a7df3e2e7ba5bdcbb4b8a0bc",
        "github_refs_heads_main_at_revalidation=e7315c42398ed095a7df3e2e7ba5bdcbb4b8a0bc",
        "autodl_CAMP_HEAD_at_revalidation=e7315c42398ed095a7df3e2e7ba5bdcbb4b8a0bc",
        "prior_ranking_revalidation_json_sha256=160a03e46343862f20e65ea5c0e39724c643a0011a5738bb68609adfef66ccbb",
        "prior_ranking_revalidation_md_sha256=f292a664b5f372a12bbfa350408ded4a29c7f3ed49b1fd638364b8b685ba2979",
        "camp_head_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "camp_origin_main_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "github_refs_heads_main_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "autodl_CAMP_HEAD_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "prior_ranking_revalidation_output_dir=/root/autodl-tmp/camp_dp_native_broader_nonformal_fixed_artifact_fallback_risk_ranking_audit_9764f12_20260625T202954Z",
        "prior_ranking_revalidation_json_sha256=d8c171d4ef2c40a34ab61e4e8bb76286614ec752c56acaed13d89e3e736f6e13",
        "prior_ranking_revalidation_md_sha256=300b8f487e83c4914954f88ed56c181674204dfb935214f96776f59b7c1fdb36",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in text

    for needle in [
        "camp_head_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "autodl_CAMP_HEAD_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "prior_ranking_revalidation_json_sha256=d8c171d4ef2c40a34ab61e4e8bb76286614ec752c56acaed13d89e3e736f6e13",
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in current_1027_plan


def test_iteration_audit_records_remediation_design_plan_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    current_head_marker = (
        "## Current Tail Confirmation After Current HEAD 1027a6b Fallback Risk "
        "Ranking Remediation Design Plan"
    )
    current_head_audit = current_head_marker + audit.split(current_head_marker)[-1]

    for needle in [
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
        "current_head_design_plan_revalidated=True",
        "camp_head_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "simplex_master_convex_if_later_authorized=True",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in audit

    for needle in [
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
        "design_plan=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_design_plan.md",
        "camp_head_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "autodl_CAMP_HEAD_at_revalidation=1027a6b223c7a0ac75c7cbec56639841819bf475",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_ranking_revalidation_json_sha256=d8c171d4ef2c40a34ab61e4e8bb76286614ec752c56acaed13d89e3e736f6e13",
        "current_head_design_plan_revalidated=True",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "local_target_pytest=17 passed",
        "autodl_target_pytest=17 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in current_head_audit


def test_current_head_c049a72_remediation_design_plan_is_pinned() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "camp_head_at_revalidation=c049a7249ff9089c6110bfa3b2aec6f2db201ae8",
        "camp_origin_main_at_revalidation=c049a7249ff9089c6110bfa3b2aec6f2db201ae8",
        "github_refs_heads_main_at_revalidation=c049a7249ff9089c6110bfa3b2aec6f2db201ae8",
        "autodl_CAMP_HEAD_at_revalidation=c049a7249ff9089c6110bfa3b2aec6f2db201ae8",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_ranking_revalidation_output_dir=/root/autodl-tmp/camp_dp_native_broader_nonformal_fixed_artifact_fallback_risk_ranking_audit_b84d64e_20260626T000000Z",
        "prior_ranking_revalidation_json_sha256=6761a3a2bc2e39e5697af9492b67bb3f280068754a1f7ddfd108adde92c1aae5",
        "prior_ranking_revalidation_md_sha256=419aaa0aa6a4e6b33c036007430fe4390daea72e2758c9f5688076279990cc22",
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
        "current_head_design_plan_revalidated=True",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "fixed_dp_candidate_reranking_only=True",
        "candidate_trajectory_rewrite_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_remediation_design_plan_current_head_c049a72_ready_static_contract_review",
        "prior_ranking_revalidation_json_sha256=6761a3a2bc2e39e5697af9492b67bb3f280068754a1f7ddfd108adde92c1aae5",
        "current_head_design_plan_revalidated=True",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in audit


def test_current_head_c0201ee_remediation_design_plan_is_pinned() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "camp_head_at_revalidation=c0201ee26a30e72916a2118251cf857baa316431",
        "camp_origin_main_at_revalidation=c0201ee26a30e72916a2118251cf857baa316431",
        "github_refs_heads_main_at_revalidation=c0201ee26a30e72916a2118251cf857baa316431",
        "autodl_CAMP_HEAD_at_revalidation=c0201ee26a30e72916a2118251cf857baa316431",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_ranking_revalidation_output_dir=/root/autodl-tmp/camp_dp_native_broader_nonformal_fixed_artifact_fallback_risk_ranking_audit_50f2944_20260626T070357Z",
        "prior_ranking_revalidation_json_sha256=d6dcc55b4abe99b32f5b69ce5eec6691ecc4ce660f451a0ad6c57e70f29bd04d",
        "prior_ranking_revalidation_md_sha256=6a2a1b10a0268f1ade6fcec05ef7e5a7c85b4900d3fff66fa28d9689a4457bb0",
        "prior_ranking_revalidation_records_total=60",
        "prior_ranking_revalidation_records_without_feasible_candidate=15",
        "prior_ranking_revalidation_lower_risk_fixed_candidate_exists_under_logged_costs=True",
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
        "current_head_design_plan_revalidated=True",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "fixed_dp_candidate_reranking_only=True",
        "candidate_trajectory_rewrite_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_remediation_design_plan_current_head_c0201ee_ready_static_contract_review",
        "current_camp_head=c0201ee26a30e72916a2118251cf857baa316431",
        "github_refs_heads_main=c0201ee26a30e72916a2118251cf857baa316431",
        "autodl_CAMP_HEAD=c0201ee26a30e72916a2118251cf857baa316431",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_ranking_revalidation_json_sha256=d6dcc55b4abe99b32f5b69ce5eec6691ecc4ce660f451a0ad6c57e70f29bd04d",
        "prior_ranking_revalidation_md_sha256=6a2a1b10a0268f1ade6fcec05ef7e5a7c85b4900d3fff66fa28d9689a4457bb0",
        "current_head_design_plan_revalidated=True",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in audit


def test_current_head_0a5d1af_remediation_design_plan_is_pinned() -> None:
    text = PLAN_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "camp_head_at_revalidation=0a5d1af8b8de26361f079bebf52ffdbfb26fbd67",
        "camp_origin_main_at_revalidation=0a5d1af8b8de26361f079bebf52ffdbfb26fbd67",
        "github_refs_heads_main_at_revalidation=0a5d1af8b8de26361f079bebf52ffdbfb26fbd67",
        "autodl_CAMP_HEAD_at_revalidation=0a5d1af8b8de26361f079bebf52ffdbfb26fbd67",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_ranking_revalidation_output_dir=/root/autodl-tmp/camp_dp_native_broader_nonformal_fixed_artifact_fallback_risk_ranking_audit_ad52f74_20260626T141146Z",
        "prior_ranking_revalidation_json_sha256=149c70556a3b6e55ac05c99fd26d1b3aa33ab7e57acbebd9e0d8aa56da55756a",
        "prior_ranking_revalidation_md_sha256=526b246b5f4fb1208ba245a6e70c43bdd320f492c0507f7bb4fa4f3ddf2c035c",
        "prior_ranking_revalidation_records_total=60",
        "prior_ranking_revalidation_records_without_feasible_candidate=15",
        "prior_ranking_revalidation_lower_risk_fixed_candidate_exists_under_logged_costs=True",
        "status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review",
        "current_head_design_plan_revalidated=True",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "fixed_dp_candidate_reranking_only=True",
        "candidate_trajectory_rewrite_authorized=False",
        "fallback_risk_extractor_implementation_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_remediation_design_plan_current_head_0a5d1af_ready_static_contract_review",
        "current_camp_head=0a5d1af8b8de26361f079bebf52ffdbfb26fbd67",
        "github_refs_heads_main=0a5d1af8b8de26361f079bebf52ffdbfb26fbd67",
        "autodl_CAMP_HEAD=0a5d1af8b8de26361f079bebf52ffdbfb26fbd67",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_ranking_revalidation_json_sha256=149c70556a3b6e55ac05c99fd26d1b3aa33ab7e57acbebd9e0d8aa56da55756a",
        "prior_ranking_revalidation_md_sha256=526b246b5f4fb1208ba245a6e70c43bdd320f492c0507f7bb4fa4f3ddf2c035c",
        "current_head_design_plan_revalidated=True",
        "score_expression=score_k(w)=a_k^T w",
        "fallback_cost_targets_nonnegative=True",
        "fallback_risk_training_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "local_target_pytest=10 passed",
        "autodl_target_pytest=10 passed",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_STATIC_REVIEW_GATE,
    ]:
        assert needle in audit
