from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = ROOT / "docs" / "diffusion_planner_v14_iteration_audit.md"
CURRENT_STATUS_DOC = ROOT / "docs" / "diffusion_planner_current_status.md"
README = ROOT / "README.md"
LATEST_V14_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_ready"
)
LATEST_V14_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_static_review_only"
)


def _assert_latest_v14_status(text: str) -> None:
    latest_status = text.rsplit("current_v14_status=", maxsplit=1)[1].splitlines()[0]
    latest_target = text.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert latest_status == LATEST_V14_STATUS
    assert latest_target == LATEST_V14_NEXT_WORK


def test_v14_audit_rollover_points_forward() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    section_title = "## Current V14 Audit Rollover"
    next_section_title = (
        "## Current V14 Approved Source Manifest Remediation Validated "
        "Rejected No Nonfixture DP-Native Source After 040f1f0"
    )

    assert text.count(section_title) == 1
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "current_authoritative_audit=docs/diffusion_planner_v14_iteration_audit.md",
        "previous_authoritative_audit=docs/diffusion_planner_v13_iteration_audit.md",
        "previous_authoritative_audit_sha256=646abee98570de8d6e614b2f6f22d1a037fd8ed8e9b5ac0c6e4f171bb2dded09",
        "camp_local_head_at_v14_launch=040f1f007d4f972f52d49d0155466e073ada7b6b",
        "autodl_camp_head_at_v14_launch=040f1f007d4f972f52d49d0155466e073ada7b6b",
        "autodl_dp_head_at_v14_launch=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_rollover_preserves_v13_as_historical_evidence=True",
        "v14_rollover_executes_fixed_dp_candidate_generation=False",
        "v14_rollover_executes_training=False",
        "v14_rollover_modifies_dp=False",
        "fixed_dp_candidate_generation_execution_approved_source_manifest_remediation_authorized_next=True",
        "fixed_dp_candidate_generation_authorized_next=False",
        "fixed_dp_candidate_generation_execution_authorized_next=False",
        "fixed_dp_candidate_generation_executed=False",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

def test_v14_approved_source_manifest_remediation_rejected_no_nonfixture_source_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Current V14 Audit Rollover"
    section_title = (
        "## Current V14 Approved Source Manifest Remediation Validated "
        "Rejected No Nonfixture DP-Native Source After 040f1f0"
    )
    next_section_title = (
        "## Current V14 Source Data Availability Audit Rejected Missing "
        "Raw DP Source After 6f5bf60"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_approved_source_manifest_remediation_validated_scan_artifact=/root/autodl-tmp/camp_dp_v14_approved_source_manifest_remediation_validated_scan_040f1f0_20260702T144603CST",
        "v14_approved_source_manifest_remediation_validated_scan_exit=0",
        "v14_approved_source_manifest_remediation_validated_scan_json_sha256=911b572d6e2db7929db02ecdde8951d1bcaa56bec9eb6d351c36c67a911f5ba7",
        "v14_approved_source_manifest_remediation_validated_scan_status=approved_source_manifest_remediation_rejected_no_valid_nonfixture_dp_native_npz_source_or_manifest",
        "v14_approved_source_manifest_remediation_validated_scan_passed=False",
        "v14_approved_source_manifest_remediation_validated_scan_failure_class=missing_valid_nonfixture_approved_fixed_dp_source_npz_manifest",
        "v14_approved_source_manifest_remediation_validated_scan_npz_total_count=415",
        "v14_approved_source_manifest_remediation_validated_scan_valid_nonfixture_dp_native_npz_source_count=0",
        "v14_approved_source_manifest_remediation_validated_scan_dp_native_core_key_record_count=1",
        "v14_approved_source_manifest_remediation_validated_scan_valid_exact_approved_source_manifest_count=0",
        "v14_approved_source_manifest_remediation_validated_scan_invalid_exact_approved_source_manifest_count=1",
        "v14_approved_source_manifest_remediation_validated_scan_invalid_exact_manifest_reason=non_source_test_or_fixture_path_marker",
        "v14_approved_source_manifest_remediation_validated_scan_only_dp_core_key_npz=/root/autodl-tmp/Diffusion-Planner/scenario_generation/tests/test_data/fixture_scene.npz",
        "v14_approved_source_manifest_remediation_validated_scan_approved_manifest_path=None",
        "v14_approved_source_manifest_remediation_validated_scan_fixed_dp_candidate_generation_executed=False",
        "v14_approved_source_manifest_remediation_validated_scan_training_authorized_next=False",
        "v14_approved_source_manifest_remediation_validated_scan_dp_modification=False",
        "v14_approved_source_manifest_remediation_validated_scan_camp_generation=False",
        "fixed_dp_candidate_generation_execution_approved_source_manifest_remediation_passed=False",
        "fixed_dp_candidate_generation_authorized_next=False",
        "fixed_dp_candidate_generation_execution_authorized_next=False",
        "fixed_dp_candidate_generation_executed=False",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=external_valid_nonfixture_dp_native_npz_source_manifest_required_before_fixed_dp_candidate_generation_execution",
    ]:
        assert needle in text


def test_v14_source_data_availability_audit_rejected_missing_raw_source_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Approved Source Manifest Remediation Validated "
        "Rejected No Nonfixture DP-Native Source After 040f1f0"
    )
    section_title = (
        "## Current V14 Source Data Availability Audit Rejected Missing "
        "Raw DP Source After 6f5bf60"
    )
    next_section_title = (
        "## Current V14 Public Simulator Source Reclassification Unblocked "
        "Candidate Tensor Preflight After 88fd3ca"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_source_data_availability_audit_artifact=/root/autodl-tmp/camp_dp_v14_source_data_availability_audit_6f5bf60_20260702T145358CST",
        "v14_source_data_availability_audit_exit=0",
        "v14_source_data_availability_audit_json_sha256=48c0250881e09b4c2d58a2765d3305ba1ac0381966a3e53d4d2d816356e266df",
        "v14_source_data_availability_audit_status=source_data_unavailable_external_nonfixture_dp_native_npz_required",
        "v14_source_data_availability_audit_passed=False",
        "v14_source_data_availability_audit_failure_class=missing_raw_dp_source_data_for_nonfixture_npz_generation",
        "v14_source_data_availability_audit_bag_metadata_count=0",
        "v14_source_data_availability_audit_rosbag_db3_count=0",
        "v14_source_data_availability_audit_mcap_count=0",
        "v14_source_data_availability_audit_lanelet_map_count=2",
        "v14_source_data_availability_audit_cpp_training_binary_candidate_count=0",
        "v14_source_data_availability_audit_route_pickle_count=7",
        "v14_source_data_availability_audit_standard_rosbag_to_npz_possible_now=False",
        "v14_source_data_availability_audit_cpp_binary_to_npz_possible_now=False",
        "v14_source_data_availability_audit_replay_dump_npz_disallowed_as_training_or_online_input=True",
        "v14_source_data_availability_audit_synthetic_static_source_manifest_not_authorized_by_current_eof=True",
        "v14_source_data_availability_audit_fixed_dp_candidate_generation_executed=False",
        "v14_source_data_availability_audit_training_authorized_next=False",
        "v14_source_data_availability_audit_dp_modification=False",
        "v14_source_data_availability_audit_camp_generation=False",
        "current_v14_status=source_data_unavailable_external_nonfixture_dp_native_npz_required",
        "valid_nonfixture_dp_native_source_manifest_available=False",
        "raw_dp_source_data_available=False",
        "fixed_dp_candidate_generation_authorized_next=False",
        "fixed_dp_candidate_generation_execution_authorized_next=False",
        "fixed_dp_candidate_generation_executed=False",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "closed_loop_outcome_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=external_valid_nonfixture_dp_native_npz_source_manifest_required_before_fixed_dp_candidate_generation_execution",
    ]:
        assert needle in text


def test_v14_public_simulator_source_reclassification_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Source Data Availability Audit Rejected Missing "
        "Raw DP Source After 6f5bf60"
    )
    section_title = (
        "## Current V14 Public Simulator Source Reclassification Unblocked "
        "Candidate Tensor Preflight After 88fd3ca"
    )
    next_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Preflight Ready After 1ffff59"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_source_reclassification_remote_timestamp=2026-07-02T16:48:03CST",
        "v14_public_simulator_source_reclassification_local_head=88fd3cac6722aedfd4ca13b41f904b4a3331c219",
        "v14_public_simulator_source_reclassification_autodl_camp_head=88fd3cac6722aedfd4ca13b41f904b4a3331c219",
        "v14_public_simulator_source_reclassification_autodl_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_source_reclassification_official_dp_internal_training_data_available=False",
        "v14_public_simulator_source_reclassification_official_rosbag_to_npz_source_available=False",
        "v14_public_simulator_source_reclassification_public_simulator_assets_available=True",
        "v14_public_simulator_source_reclassification_public_nuscenes_archives_available=True",
        "v14_public_simulator_source_reclassification_public_nuscenes_archives_root=/autodl-pub/data/nuScenes",
        "v14_public_simulator_source_reclassification_nuscenes_marked_missing=False",
        "v14_public_simulator_source_reclassification_nuscenes_available_but_not_dp_native=True",
        "v14_public_simulator_source_reclassification_public_nuscenes_direct_dp_source=False",
        "v14_public_simulator_source_reclassification_nuscenes_adapter_authorized_by_current_gate=False",
        "v14_public_simulator_source_reclassification_diffusion_planner_pth_sha256=4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75",
        "v14_public_simulator_source_reclassification_diffusion_planner_param_json_sha256=ee3145b68fd1e1e44e532933dfe66cfee4384fbd637382c87ab5190c66a8e268",
        "v14_public_simulator_source_reclassification_sample_map_no_ros_sha256=a81f937c00158324c83688adc5459e90478f5b3c69a51225ad7f965b80d58036",
        "v14_public_simulator_source_reclassification_sample_tl_route_sha256=dc9b3906bace09ee9e99062ac702df1c5b2d2f4620d0a7fa14022faa9a39e4c4",
        "v14_public_simulator_source_reclassification_sample_normal_route_sha256=489980fd79458695db68b30e91d4fcfc3efb80aca9e82ee9858a94cf2822ae35",
        "v14_public_simulator_source_reclassification_nishishinjuku_no_ros_sha256=bf1ff35bfb7562b6ab15e62b1ac55770bb84352b00af5204c3601bd47f079b81",
        "v14_public_simulator_source_reclassification_nishishinjuku_release_route_sha256=fef5f2be64fb9d043d4cdf46672d28cf8d3445d67bb6b2c6c1bb7570621e4337",
        "v14_public_simulator_source_reclassification_nishishinjuku_lane_change_route_sha256=4d03a3f99f3d39d51e53389064c83f2a942921b7ddea437c9ed3730ae0fd033b",
        "v14_public_simulator_source_reclassification_external_dp_native_source_npz_gate_too_strict_for_camp=True",
        "v14_public_simulator_source_reclassification_fixed_dp_candidate_tensor_source_is_public_simulator=True",
        "v14_public_simulator_source_reclassification_fixed_dp_candidate_generation_preflight_authorized_next=True",
        "v14_public_simulator_source_reclassification_fixed_dp_candidate_generation_executed=False",
        "v14_public_simulator_source_reclassification_training_authorized_next=False",
        "v14_public_simulator_source_reclassification_dp_modification=False",
        "v14_public_simulator_source_reclassification_camp_generation=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_source_available_preflight_required",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_preflight",
        "tier4_rosbag_dp_training_source_available=False",
        "official_tier4_dp_training_data_available=False",
        "public_nuscenes_archives_available=True",
        "public_simulator_fixed_dp_candidate_tensor_source_available=True",
        "public_simulator_fixed_dp_candidate_generation_preflight_authorized_next=True",
        "fixed_dp_candidate_generation_authorized_next=False",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "closed_loop_outcome_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_preflight",
    ]:
        assert needle in text


def test_v14_public_simulator_fixed_dp_candidate_generation_preflight_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Source Reclassification Unblocked "
        "Candidate Tensor Preflight After 88fd3ca"
    )
    section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Preflight Ready After 1ffff59"
    )
    next_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Execution Passed After 458c66c"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_preflight_1ffff597eb_20260702T172252CST",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_planned_execution_output_root=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_1ffff597eb_20260702T172252CST",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_camp_head=1ffff597ebdc0cc598daff7db2150df2d5d898ab",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_camp_origin_main=1ffff597ebdc0cc598daff7db2150df2d5d898ab",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_exit=0",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_status=public_simulator_fixed_dp_candidate_generation_preflight_ready",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_passed=True",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_failed_checks=[]",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_check_count=318",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_failed_check_count=0",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_json_sha256=4ca4126455a4e7d55110e8be265575d7a48578a4455ecd62794b84b331bdea14",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_runbook_sha256=af3d92f01b292439ea51a267c44cc11c5f21fb53fdf9e9208829e329b31993ba",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_planned_command_count=32",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_expected_steps_per_command=100",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_expected_records=3200",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_num_candidates=8",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_candidate_output_root_exists=False",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_default_off_shadow_selector=True",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_candidate_tensor_provenance_logging=True",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_executed_output_policy=dp_top1",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_fixed_dp_candidate_generation_executed=False",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_training_execution_authorized_next=False",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_dp_modification_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_safety_benefit_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_preflight_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_execution",
        "public_simulator_fixed_dp_candidate_generation_preflight_passed=True",
        "fixed_dp_candidate_generation_authorized_next=True",
        "fixed_dp_candidate_generation_execution_authorized_next=True",
        "fixed_dp_candidate_generation_executed=False",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "closed_loop_outcome_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_execution",
    ]:
        assert needle in text


def test_v14_public_simulator_fixed_dp_candidate_generation_execution_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Preflight Ready After 1ffff59"
    )
    section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Execution Passed After 458c66c"
    )
    next_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Zero-Overlap Validation Passed After 2e17d11"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_fixed_dp_candidate_generation_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_458c66c8ae_20260702T173540CST_artifact",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_output_root=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_1ffff597eb_20260702T172252CST",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_camp_head=458c66c8aeac8b9eb15ba3f06a7f87e5c9ef0740",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_camp_origin_main=458c66c8aeac8b9eb15ba3f06a7f87e5c9ef0740",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_exit=0",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_status=public_simulator_fixed_dp_candidate_generation_execution_passed",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_passed=True",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_command_count=32",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_commands_started=32",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_commands_succeeded=32",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_first_failed_command=None",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_validation_summary_count=32",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_replay_summary_count=32",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_default_off_shadow_selector_summary_count=32",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_candidate_tensor_provenance_summary_count=32",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_unique_seeds=1,2,3,4",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_formal_seed_intersection=[]",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_unique_steps=100",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_route_count=4",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_closed_loop_collect_count=0",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_report_sha256=66207d1620b9fa24304b7f545a8c2f536f2c0e8a88fb5f52c604685d385f0ae1",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_post_execution_sha256s_sha256=41c1e038fa9f6e26da404b111c451facb4aa6a8d3547921c0efd5facc8350840",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_fixed_dp_candidate_generation_executed=True",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_fixed_dp_candidate_generation_execution_passed=True",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_zero_overlap_validation_authorized_next=True",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_training_execution_authorized_next=False",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_dp_modification_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_safety_benefit_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_execution_score_expression=score_k(w)=a_k^T w",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_execution_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_zero_overlap_validation",
        "public_simulator_fixed_dp_candidate_generation_execution_passed=True",
        "fixed_dp_candidate_generation_executed=True",
        "zero_overlap_validation_authorized_next=True",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "closed_loop_outcome_authorized=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_zero_overlap_validation",
    ]:
        assert needle in text


def test_v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Execution Passed After 458c66c"
    )
    section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Zero-Overlap Validation Passed After 2e17d11"
    )
    next_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Data-Preparation Preflight Ready After 356ce63"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_incomplete_reference_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_2e17d11994_20260702T190418CST",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_incomplete_reference_exit=1",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_incomplete_reference_status=public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_rejected",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_incomplete_reference_failure_class=reference_training_registry_missing_or_empty",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_2e17d11994_20260702T190542CST_complete_reference",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_execution_output_root=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_1ffff597eb_20260702T172252CST",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_reference_registry_root=/root/autodl-tmp/camp_dp_v13_default_off_member_source_generation_implementation_7ca9b6848b_20260702T061630CST/generated_outputs",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_camp_head=2e17d119941b8134fc4adb7b607204d7ee95899e",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_exit=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_status=public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed=True",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_selection_log_count=32",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_record_count=3200",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_unique_candidate_tensor_hash_count=3080",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_unique_path_signature_count=32",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_unique_record_identity_hash_count=3200",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_unique_split_manifest_root_count=4",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_formal_seed_intersection=[]",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_tensor_hash_mismatches=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_executed_non_top1=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_closed_loop_collect_count=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_forbidden_runtime_flags=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_reference_counts_candidate_tensor_hashes=1",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_reference_counts_path_signatures=1",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_reference_counts_record_identity_hashes=1",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_reference_counts_split_manifest_roots=1",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_candidate_tensor_hash_intersection_count=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_path_signature_intersection_count=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_record_identity_intersection_count=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_split_manifest_root_intersection_count=0",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_report_sha256=d33f110143482f09216d686f905c5ee0e7015f0d4c522e5597f536bde03d5ef8",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_post_execution_sha256s_sha256=0bfb38a24a7c10a17263176dbd3c1076916fa2814ffb1e1eac574822d5cb355e",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_data_preparation_preflight_authorized_next=True",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_training_preflight_authorized_next=False",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_training_execution_authorized_next=False",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_dp_modification_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_safety_benefit_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_score_expression=score_k(w)=a_k^T w",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_data_preparation_preflight",
        "zero_overlap_validation_passed=True",
        "data_preparation_preflight_authorized_next=True",
        "training_preflight_authorized_next=False",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_data_preparation_preflight",
    ]:
        assert needle in text


def test_v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Generation "
        "Zero-Overlap Validation Passed After 2e17d11"
    )
    section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Data-Preparation Preflight Ready After 356ce63"
    )
    next_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Training Preflight Ready After aff9b05"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_356ce6301c_20260702T192546CST",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_execution_output_root=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_1ffff597eb_20260702T172252CST",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_zero_overlap_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_2e17d11994_20260702T190542CST_complete_reference",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_camp_head=356ce6301cd02a59dedb971f85aac8481be0a7fd",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_camp_origin_main=356ce6301cd02a59dedb971f85aac8481be0a7fd",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_exit=0",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_status=public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_ready",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_passed=True",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_failed_checks=[]",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_selection_log_count=32",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_records=3200",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_failed_records=0",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_future_training_input_contract_satisfied=True",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_zero_overlap_record_count=3200",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_zero_overlap_candidate_tensor_hash_intersection_count=0",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_zero_overlap_path_signature_intersection_count=0",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_zero_overlap_record_identity_intersection_count=0",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_zero_overlap_split_manifest_root_intersection_count=0",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_training_input_manifest=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_356ce6301c_20260702T192546CST/training_input_manifest.json",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_report_json_sha256=49775ba22bc399603f78f29afe1c1b3dad3126159fa4304f66b95805a3f21334",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_training_input_manifest_sha256=98c63d7f5907615b864a0acc867bb15589bbd5d6bed47783fc673b6f856e2500",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_post_execution_sha256s_sha256=d0d53f2602d7f2a8257772e643d1e964b39e74621065465172329bc91875dcda",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_training_preflight_authorized_next=True",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_training_execution_authorized_next=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_data_preparation_executed=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_trajectory_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_reference_blend_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_guidance_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_postprocess_or_postselection_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_closed_loop_outcome_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_dp_modification_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_selector_promotion_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_deployment_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_safety_benefit_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_approved_atoms_nonnegative_simplex_only=True",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_simplex_cvar_l2_master_convexity_preserved=True",
        "v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_score_expression=score_k(w)=a_k^T w",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_training_preflight",
        "data_preparation_preflight_passed=True",
        "training_preflight_authorized_next=True",
        "training_execution_authorized_by_current_boundary=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_training_preflight",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_public_simulator_fixed_dp_candidate_training_preflight_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Data-Preparation Preflight Ready After 356ce63"
    )
    section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Training Preflight Ready After aff9b05"
    )
    next_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Training Execution Passed After 67f806"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_fixed_dp_candidate_training_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_preflight_aff9b0533f_20260702T194544CST",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_data_preparation_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_356ce6301c_20260702T192546CST",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_planned_training_output_dir=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_aff9b0533f_20260702T194544CST_planned",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_camp_head=aff9b0533ff63172f834dfede3836e5553bb05e0",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_camp_origin_main=aff9b0533ff63172f834dfede3836e5553bb05e0",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_exit=0",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_status=public_simulator_fixed_dp_candidate_generation_training_preflight_ready",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_passed=True",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_failed_checks=[]",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_selection_log_count=32",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_records=3200",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_clean_contract_failed_records=0",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_future_training_input_contract_satisfied=True",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_usable_feasible_records=2914",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_all_infeasible_records=286",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_atom_schema_versions={'camp_legacy_v1_9d': 3200}",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_selected_index_counts={'0': 3200}",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_executed_index_counts={'0': 3200}",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_finite_reward_records=3200",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_default_off_shadow_selector_valid_records=3200",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_command_forbidden_tokens_absent=True",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_report_json_sha256=d5d4b28c90961289a74e067257d49a1f3b71bb4b6d55f6d87d3ce7d359e4b641",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_command_plan_sha256=28cb10c5d14c35ad9a52266f21bb25937b908404ac917a5f7d9afeb5075053d0",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_runbook_sha256=1b17d9d3d99dd55c776306a35bb69a26ab2b8846bdf9b201de52ef171c23a6ae",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_training_execution_authorized_next=True",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_training_executed=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_replay_executed=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_candidate_generation_executed=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_trajectory_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_reference_blend_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_guidance_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_postprocess_or_postselection_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_closed_loop_outcome_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_dp_modification_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_selector_promotion_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_deployment_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_safety_benefit_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_approved_atoms_nonnegative_simplex_only=True",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_simplex_cvar_l2_master_convexity_preserved=True",
        "v14_public_simulator_fixed_dp_candidate_training_preflight_score_expression=score_k(w)=a_k^T w",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_training_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_training_execution",
        "training_preflight_passed=True",
        "training_execution_authorized_by_current_boundary=True",
        "camp_training_executed=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_training_execution",
    ]:
        assert needle in text


def test_v14_public_simulator_fixed_dp_candidate_training_execution_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Training Preflight Ready After aff9b05"
    )
    section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Training Execution Passed After 67f806"
    )
    next_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Training "
        "Artifact Static Contract Review Passed After b075ec"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_fixed_dp_candidate_training_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_67f8062de6_20260702T195230CST",
        "v14_public_simulator_fixed_dp_candidate_training_execution_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_preflight_aff9b0533f_20260702T194544CST",
        "v14_public_simulator_fixed_dp_candidate_training_execution_output_dir=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_aff9b0533f_20260702T194544CST_planned",
        "v14_public_simulator_fixed_dp_candidate_training_execution_camp_head=67f8062de6cd36fc9f0480223ad262b1f3f09af5",
        "v14_public_simulator_fixed_dp_candidate_training_execution_camp_origin_main=67f8062de6cd36fc9f0480223ad262b1f3f09af5",
        "v14_public_simulator_fixed_dp_candidate_training_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_fixed_dp_candidate_training_execution_exit=0",
        "v14_public_simulator_fixed_dp_candidate_training_execution_training_type=diffusion_planner_static_candidate_preference",
        "v14_public_simulator_fixed_dp_candidate_training_execution_label_source=dp_reward",
        "v14_public_simulator_fixed_dp_candidate_training_execution_reward_key=quality_without_progress",
        "v14_public_simulator_fixed_dp_candidate_training_execution_num_records=2914",
        "v14_public_simulator_fixed_dp_candidate_training_execution_dropped_records_without_feasible_candidate=286",
        "v14_public_simulator_fixed_dp_candidate_training_execution_num_candidates=8",
        "v14_public_simulator_fixed_dp_candidate_training_execution_num_atoms=9",
        "v14_public_simulator_fixed_dp_candidate_training_execution_atom_schema_version=camp_legacy_v1_9d",
        "v14_public_simulator_fixed_dp_candidate_training_execution_oracle_match_rate=0.22786547700754975",
        "v14_public_simulator_fixed_dp_candidate_training_execution_first_loss=2.0419425862497667",
        "v14_public_simulator_fixed_dp_candidate_training_execution_last_loss=2.036233432086801",
        "v14_public_simulator_fixed_dp_candidate_training_execution_weights_sum=0.9999999999999999",
        "v14_public_simulator_fixed_dp_candidate_training_execution_weights_min=0.059347218886831296",
        "v14_public_simulator_fixed_dp_candidate_training_execution_contract_failed_records=0",
        "v14_public_simulator_fixed_dp_candidate_training_execution_output_files=atom_scales_dp_static.json,offline_weights_dp_static.npy,training_summary.json",
        "v14_public_simulator_fixed_dp_candidate_training_execution_training_summary_sha256=783684d1fd7038587efc43a47e4ca4f88eb392267187eb4e0042ed346b9fc6a0",
        "v14_public_simulator_fixed_dp_candidate_training_execution_atom_scales_sha256=2239fb09e2231405dbc58b1a79486ff3f3c111a9bab96c24d88e6832f2325b8b",
        "v14_public_simulator_fixed_dp_candidate_training_execution_offline_weights_sha256=5bfe692465c0e0cdbf2fb937737674e53b3f41a31ea932a65f65a6321f4c0dde",
        "v14_public_simulator_fixed_dp_candidate_training_execution_training_executed=True",
        "v14_public_simulator_fixed_dp_candidate_training_execution_replay_executed=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_candidate_generation_executed=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_trajectory_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_reference_blend_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_guidance_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_postprocess_or_postselection_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_closed_loop_outcome_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_dp_modification_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_selector_promotion_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_deployment_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_deployable_checkpoint_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_safety_benefit_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_execution_approved_atoms_nonnegative_simplex_only=True",
        "v14_public_simulator_fixed_dp_candidate_training_execution_simplex_cvar_l2_master_convexity_preserved=True",
        "v14_public_simulator_fixed_dp_candidate_training_execution_score_expression=score_k(w)=a_k^T w",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_training_execution_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review",
        "training_execution_passed=True",
        "camp_training_executed=True",
        "training_artifact_static_contract_review_authorized_next=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Training Execution Passed After 67f806"
    )
    section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Training "
        "Artifact Static Contract Review Passed After b075ec"
    )
    next_section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Preflight Ready After adc714"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_b075ec0854_20260702T200227CST",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_training_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_67f8062de6_20260702T195230CST",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_current_camp_head=b075ec0854dc7f9d6522fbf6423f8ec1ae00539c",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_artifact_camp_head=67f8062de6cd36fc9f0480223ad262b1f3f09af5",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_artifact_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_exit=0",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_status=public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_passed",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_passed=True",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_failed_checks=[]",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_num_records=2914",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_dropped_records_without_feasible_candidate=286",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_atom_schema_version=camp_legacy_v1_9d",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_weights_sum=1.0",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_weights_nonnegative=True",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_weights_file_matches_summary=True",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_scales_all_positive_finite=True",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_report_json_sha256=928c0997ef76ee406a47c4f0b2eabd46b9e011497b50063d48bd00facb6df8f0",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_report_md_sha256=0c0c43543d2ed8d84d200bd56537fe77de647ad107a9507d0d2902a98712dba3",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_training_artifact_static_contract_review_complete=True",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_trained_default_off_shadow_replay_evaluation_preflight_authorized_next=True",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_training_executed_by_source=True",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_training_executed_by_review=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_replay_executed=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_candidate_generation_executed=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_trajectory_generation_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_closed_loop_outcome_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_dp_modification_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_selector_promotion_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_deployment_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_score_expression=score_k(w)=a_k^T w",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight",
        "training_artifact_static_contract_review_passed=True",
        "trained_default_off_shadow_replay_evaluation_preflight_authorized_next=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight",
    ]:
        assert needle in text


def test_v14_public_simulator_trained_default_off_shadow_replay_preflight_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate Training "
        "Artifact Static Contract Review Passed After b075ec"
    )
    section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Preflight Ready After adc714"
    )
    next_section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Execution Passed After 72fdb3"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_failed_import_path_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_bedc10752b_20260702T202857CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_failed_import_path_failure_class=script_import_path_missing",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_import_path_remediation_commit=adc71422af56711f8baec545259fe47626f955ef",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_adc71422af_20260702T203050CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_training_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_67f8062de6_20260702T195230CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_training_artifact_static_contract_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_b075ec0854_20260702T200227CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_camp_head=adc71422af56711f8baec545259fe47626f955ef",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_exit=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight_ready",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_passed=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_failed_checks=[]",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_execution",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_planned_command_count=32",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_expected_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_check_count=392",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_failed_check_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_runtime_schema=dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_runtime_default_off=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_runtime_fail_closed=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_executed_output_policy=dp_top1",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_candidate_operation=fixed DP candidate reranking only",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_atom_schema_version=camp_legacy_v1_9d",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_weights_sha256=5bfe692465c0e0cdbf2fb937737674e53b3f41a31ea932a65f65a6321f4c0dde",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_atom_scales_sha256=2239fb09e2231405dbc58b1a79486ff3f3c111a9bab96c24d88e6832f2325b8b",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_commands_contain_closed_loop_outcomes=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_formal_seeds_11_12_13_excluded=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_runbook_sha256=4644ea5625bb23d24541b52e0e9621262fa4d2dc90d0df2e6a26f5f3f0dde928",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_runtime_manifest_sha256=d6b73453579c71962ca1fa7e0706b28dd18e5269fad12b5f4ec3caf38cac5490",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_report_json_sha256=e5e50eba92103eafc3c740d3df5edce383678d76ebe53476fd0dbd348b0ce343",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_complete=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_authorized_next=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_only=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_replay_executed=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_candidate_generation_executed=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_training_executed=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_trajectory_generation_by_camp_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_closed_loop_outcome_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_dp_modification_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_online_selector_change_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_executed_trajectory_change_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_selector_promotion_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_deployment_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_safety_benefit_claim_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_approved_atoms_nonnegative_simplex_only=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_simplex_cvar_l2_master_convexity_preserved=True",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_execution",
        "trained_default_off_shadow_replay_evaluation_preflight_passed=True",
        "trained_default_off_shadow_replay_evaluation_execution_authorized_next=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_execution",
    ]:
        assert needle in text


def test_v14_public_simulator_trained_default_off_shadow_replay_execution_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Preflight Ready After adc714"
    )
    section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Execution Passed After 72fdb3"
    )
    next_section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Result Review Passed After 2dd27b"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_stale_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_artifact_5b23ae8f25_20260702T204229CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_stale_execution_exit=41",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_stale_execution_failure_class=stale_runbook_camp_head_mismatch",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_stale_execution_output_root_exists=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_current_head_preflight_refresh_commit=72fdb3e4c880751948a47d25b0330e3818975162",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_current_head_preflight_refresh_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_refresh_72fdb3e4c8_20260702T204702CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_current_head_preflight_refresh_exit=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_current_head_preflight_refresh_failed_checks=[]",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_current_head_preflight_refresh_planned_output_root=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_72fdb3e4c8_20260702T204702CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_current_head_preflight_refresh_runbook_sha256=67da338711919141f0b076fd1012830054bd1ebe751d9c79f9d37b99704fc58f",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_artifact_72fdb3e4c8_20260702T204752CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_output_root=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_72fdb3e4c8_20260702T204702CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_camp_head=72fdb3e4c880751948a47d25b0330e3818975162",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_exit=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_execution_passed",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_passed=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_selection_log_count=32",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_validation_summary_count=32",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_replay_summary_count=32",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_records_total=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_records_per_log_min=100",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_records_per_log_max=100",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_shadow_selected_index_nonzero_records=2832",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_executed_top1_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_selected_index_matches_executed_index_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_shadow_selected_index_differs_from_executed_index_records=2832",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_default_off_selector_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_artifact_contract_ready_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_selection_effect_true_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_online_change_true_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_policy_non_top1_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_score_bad_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_operation_bad_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_candidate_reference_blend_steps_nonzero=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_candidate_closed_loop_outcome_weights_nonzero=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_candidate_closed_loop_outcomes_nonzero=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_perfect_tracker_command_postselection_active=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_traffic_light_hybrid_postselection_active=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_used_fallback_count=286",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_formal_seed_path_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_camp_candidate_tensor_provenance_schema=dp_native_candidate_tensor_provenance_payload_v1",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_camp_provenance_forbidden_effects=[]",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_atom_schema_version=camp_legacy_v1_9d",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_num_candidates=8",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_weights_sum=1.0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_candidate_operation=fixed DP candidate reranking only",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_executed_output_policy=dp_top1",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_sha256s_sha256=5bb414a4a0cc8d3013ade90be55efa9608ced26c7a0ca6c9056d722a137bfeca",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_replay_executed=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_candidate_generation_executed=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_training_executed=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_trajectory_generation_by_camp_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_closed_loop_outcome_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_dp_modification_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_online_selector_change_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_executed_trajectory_change_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_selector_promotion_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_deployment_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_safety_benefit_claim_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_approved_atoms_nonnegative_simplex_only=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_simplex_cvar_l2_master_convexity_preserved=True",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_execution_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_result_review",
        "trained_default_off_shadow_replay_evaluation_execution_passed=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "formal_seed_11_12_13_execution_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_result_review",
    ]:
        assert needle in text


def test_v14_public_simulator_trained_default_off_shadow_replay_result_review_passed_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Execution Passed After 72fdb3"
    )
    section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Result Review Passed After 2dd27b"
    )
    next_section_title = (
        "## Current V14 Trained Shadow Replay/Evaluation Promotion-Decision "
        "Plan Ready After 4b17b3"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_initial_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_3642c74a10_20260702T222136CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_initial_exit=1",
        'v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_initial_failed_checks=["artifact_camp_head_matches_current","artifact_camp_origin_matches_current"]',
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_initial_failure_class=head_or_fixed_dp_contract_failure",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_head_contract_remediation_commit=2dd27b50b8172fb6f31df9a154e55c329f6ae2f9",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_2dd27b50b8_20260702T222425CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_source_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_artifact_72fdb3e4c8_20260702T204752CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_camp_head=2dd27b50b8172fb6f31df9a154e55c329f6ae2f9",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_source_execution_camp_head=72fdb3e4c880751948a47d25b0330e3818975162",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_exit=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_result_review_passed",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_passed=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_failed_checks=[]",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_only_after_explicit_user_authorization",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_promotion_decision_plan_authorized_next=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_selection_log_count=32",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_records_total=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_records_per_log_min=100",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_records_per_log_max=100",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_route_count=16",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_seed_count=4",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_shadow_selected_index_nonzero_records=2832",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_executed_top1_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_selected_index_matches_executed_index_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_selection_effect_true_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_online_change_true_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_candidate_reference_blend_steps_nonzero=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_candidate_closed_loop_outcome_weights_nonzero=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_candidate_closed_loop_outcomes_nonzero=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_formal_seed_path_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_camp_provenance_forbidden_effect_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_weights_bad_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_atom_schema_bad_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_candidate_count_bad_count=0",
        'v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_atom_schema_versions={"camp_legacy_v1_9d":3200}',
        'v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_candidate_counts={"8":3200}',
        'v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_weights_sums={"1.0":3200}',
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_replay_executed_by_review=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_candidate_generation_executed_by_review=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_training_executed_by_review=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_selector_promotion_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_deployment_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_json_sha256=41484dde58c3e89b4f2a9a644f3c8f1700e3f198f76e6f20fae8a7c254a17e78",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_sha256s_sha256=9ba54de606c2aff79a2a85cb5015af3ef59468b963492dc3f2e763bbe930f3fe",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_result_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_only_after_explicit_user_authorization",
        "trained_default_off_shadow_replay_evaluation_result_review_passed=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_only_after_explicit_user_authorization",
    ]:
        assert needle in text


def test_v14_public_simulator_trained_shadow_promotion_decision_plan_ready_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Trained Default-Off Shadow "
        "Replay/Evaluation Result Review Passed After 2dd27b"
    )
    section_title = (
        "## Current V14 Trained Shadow Replay/Evaluation Promotion-Decision "
        "Plan Ready After 4b17b3"
    )
    next_section_title = (
        "## Current V14 Trained Shadow Replay/Evaluation Promotion "
        "Evidence-Package Preflight Ready After 9aea47"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_initial_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_4b17b35302_20260702T231157CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_initial_exit=127",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_initial_failure_class=python_alias_missing_in_runbook",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_4b17b35302_20260702T231416CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_source_result_review_json=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_2dd27b50b8_20260702T222425CST/review/result_review_report.json",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_source_result_review_json_sha256=41484dde58c3e89b4f2a9a644f3c8f1700e3f198f76e6f20fae8a7c254a17e78",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_camp_head=4b17b353024a45b2f89d360f3e63c20ae76eac01",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_exit=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_py_compile_exit=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_pytest_exit=1",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_pytest_failure_class=autodl_python_environment_missing_pytest",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_ready",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_passed=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_failed_checks=[]",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_recommendation=do_not_promote_from_current_evidence_alone",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_immediate_action=build_promotion_evidence_package_preflight_only",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_only",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_evidence_package_preflight_authorized=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_selector_promotion_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_atom_promotion_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_deployment_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_training_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_candidate_generation_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_replay_execution_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_dp_modification_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_online_selector_change_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_records_total=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_training_records=2914",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_shadow_selected_index_nonzero_records=2832",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_executed_top1_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_selection_effect_true_count=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_json_sha256=c33a5c47b532fb22d73d82e47a6c80094a308e07837a5e96f560dd85b7bcdd77",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_sha256s_sha256=18a3059edc457835635e51f4fc21228fdf19b2bce5db607d8fe832df7ab79bb1",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_only",
        "promotion_decision_plan_ready=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_only",
    ]:
        assert needle in text


def test_v14_public_simulator_trained_shadow_promotion_evidence_package_preflight_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Trained Shadow Replay/Evaluation Promotion-Decision "
        "Plan Ready After 4b17b3"
    )
    section_title = (
        "## Current V14 Trained Shadow Replay/Evaluation Promotion "
        "Evidence-Package Preflight Ready After 9aea47"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Static Integration "
        "Contract Plan Ready After 8fe12a"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_initial_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_2aa96d0f16_20260702T234535CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_initial_exit=1",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_initial_failure_class=source_training_contract_failure",
        'v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_initial_failed_checks=["training_summary_contract"]',
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_contract_remediation_commit=9aea47cc48aad4be26d8221e3c6c40dcf612d9d1",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_9aea47cc48_20260702T234739CST",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_camp_head=9aea47cc48aad4be26d8221e3c6c40dcf612d9d1",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_py_compile_exit=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_exit=0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_ready",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_passed=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_failed_checks=[]",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_only",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_default_off_shadow_selector_contract_plan_authorized=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_manifest_count=7",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_manifest_entries=promotion_decision_plan,result_review,training_artifact_static_review,training_summary,offline_weights_npy,atom_scales_json,shadow_execution_sha256s",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_promotion_decision_plan_sha256=c33a5c47b532fb22d73d82e47a6c80094a308e07837a5e96f560dd85b7bcdd77",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_result_review_sha256=41484dde58c3e89b4f2a9a644f3c8f1700e3f198f76e6f20fae8a7c254a17e78",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_training_artifact_static_review_sha256=928c0997ef76ee406a47c4f0b2eabd46b9e011497b50063d48bd00facb6df8f0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_training_summary_sha256=783684d1fd7038587efc43a47e4ca4f88eb392267187eb4e0042ed346b9fc6a0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_offline_weights_npy_sha256=5bfe692465c0e0cdbf2fb937737674e53b3f41a31ea932a65f65a6321f4c0dde",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_atom_scales_json_sha256=2239fb09e2231405dbc58b1a79486ff3f3c111a9bab96c24d88e6832f2325b8b",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_shadow_execution_sha256s_sha256=5bb414a4a0cc8d3013ade90be55efa9608ced26c7a0ca6c9056d722a137bfeca",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_selection_log_count=32",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_records_total=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_training_records=2914",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_dropped_records_without_feasible_candidate=286",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_shadow_selected_index_nonzero_records=2832",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_executed_top1_records=3200",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_weights_sum=1.0",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_static_integration_contract_status=preflight_ready_contract_pinned",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_simplex_master_convex=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_cvar_master_convex=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_l2_master_convex=True",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_default_off_shadow_selector_wiring_status=future_static_contract_plan_required_before_implementation",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_selector_promotion_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_deployment_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_training_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_replay_execution_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_candidate_generation_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_dp_modification_authorized=False",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_json_sha256=dc4e5bcd3ef41380c91a1911510821ea8fecbdc37a4ac2f9f319c5ee73b2053f",
        "v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_sha256s_sha256=0c874c1b4b5c7814fc67933dcb1af72504e30ceacd3e3168afbfd96457fbf10d",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_only",
        "promotion_evidence_package_preflight_ready=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_static_integration_contract_plan_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Trained Shadow Replay/Evaluation Promotion "
        "Evidence-Package Preflight Ready After 9aea47"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Static Integration "
        "Contract Plan Ready After 8fe12a"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Plan "
        "Ready After 55c360"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_8fe12a0fba_20260702T235910CST",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_camp_head=8fe12a0fbaa2083613cfaf83f5d0f8693423e6c1",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_exit=0",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_passed=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_only",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_static_contract_plan_ready=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_implementation_plan_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_implementation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_source_preflight_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_ready",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_source_preflight_sha256=dc4e5bcd3ef41380c91a1911510821ea8fecbdc37a4ac2f9f319c5ee73b2053f",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_source_manifest_count=7",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_source_records_total=3200",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_source_training_records=2914",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_source_num_candidates=8",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_source_num_atoms=9",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_source_static_contract_status=preflight_ready_contract_pinned",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_camp_integration_py_sha256=6b964595bcd50cf10e5edfbdebef2a8cc6b1494990103f6f66bc76d6498fcde7",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_replay_runner_py_sha256=1d5e116cb2c7c473b9c79906a17bc01683dc9b7595a6006c129cc135dedf4813",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_benders_contract_test_py_sha256=bbed165a710f91087b963c6df235764e4ad9c553ff43eed26f4263d51545d301",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_camp_selector_surface_present=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_runner_selector_mode_present=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_runner_finite_candidate_contract_present=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_runner_dp_top1_shadow_policy_present=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_benders_affine_score_test_present=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_benders_negative_atom_rejection_test_present=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_selector_phase=default_off_shadow_only",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_runtime_effect=must_log_shadow_selected_index_without_changing_dp_top1_output",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_candidate_source=fixed current-tick DP candidate tensor before CAMP scoring",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_candidate_count=8",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_selection_rule=argmin_k score_k(w) over finite feasible candidate rows",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_default_off_required=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_kill_switch_required=True",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_trajectory_mutation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_postselection_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_formal_seed_usage_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_json_sha256=2389f0bf1d2a08e2453e1944c940108fa8997a123fa65e2981397f34d5775951",
        "v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_sha256s_sha256=f5e52d9645cf3b8e1505c3ab63fdda0f5da47c86361a4de504e53007d0d13697",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_only",
        "default_off_shadow_selector_static_contract_plan_ready=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_implementation_plan_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Static Integration "
        "Contract Plan Ready After 8fe12a"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Plan "
        "Ready After 55c360"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Static "
        "Contract Review Passed After 5687ee"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_script=scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_plan.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_local_pytest=13 passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_plan_55c360b804_20260703T001423CST",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_failed_exit=1",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_failed_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_rejected",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_failed_failure_class=source_static_contract_plan_failure",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_failed_failed_checks_include=static_contract_plan_exists",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_failed_json_sha256=b15ddfebb3c529efff11b134e0e0b6b72135de7bf50584b2f7e98110c310d39b",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_plan_55c360b804_20260703T001526CST",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_camp_head=55c360b8047834271a1667a2ebd3353e914358c6",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_camp_origin_main=55c360b8047834271a1667a2ebd3353e914358c6",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_source_static_contract_plan=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_8fe12a0fba_20260702T235910CST/report/default_off_shadow_selector_static_integration_contract_plan.json",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_passed=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_only",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_ready=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_static_contract_review_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_implementation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_source_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_source_candidate_count=8",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_source_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_runtime_effect=log shadow_selected_index while executed output remains DP Top-1",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_candidate_source=fixed current-tick DP candidate tensor before CAMP scoring",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_selection_rule=shadow_selected_index = argmin_k score_k(w)",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_heads_sha256=393edb83fdd2b02b01d2914251278609464f90da1b239bb505766f436d17e500",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_command_sha256=af900895b65845d2a799b64097c41fa7bc328759755a47000ae79127069936a6",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_stdout_sha256=398e7dadc6316d0e5fa8b142a242a0640e268cb503033e8b8f81818da8354744",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_json_sha256=553c09c55ae87cb65dcfce6e0497a0b1773b1b68e4c574b34f93ff03e15df398",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_md_sha256=d3bad2e0ae50cf1c1fc8078410593566e69d17c7a1bfa246bd971755743f5fdb",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_sha256s_sha256=08fdb3c7eae8d89708ae229151248c24724eb1b283fe7cef2a4c3b12360ae88e",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_executed_trajectory_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_plan_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_only",
        "default_off_shadow_selector_static_contract_plan_ready=True",
        "default_off_shadow_selector_implementation_plan_ready=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_implementation_static_contract_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Plan "
        "Ready After 55c360"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Static "
        "Contract Review Passed After 5687ee"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Unit "
        "Tests Plan Ready After 0152e7"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_local_pytest=16 passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_5687ee3ee6_20260703T002900CST",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_camp_head=5687ee3ee608651da4bab7646d8a45c1eb631b75",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_camp_origin_main=5687ee3ee608651da4bab7646d8a45c1eb631b75",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_source_plan=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_plan_55c360b804_20260703T001526CST/default_off_shadow_selector_implementation_plan.json",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_passed=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_only",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_passed_flag=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_unit_tests_plan_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_implementation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_source_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_source_candidate_count=8",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_source_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_runtime_effect=executed output remains DP Top-1 during shadow phase",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_candidate_operation=fixed DP candidate reranking only",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_selection_rule=shadow_selected_index = argmin_k score_k(w)",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_contracts=default_off_flag_contract,immutable_artifact_hash_contract,fixed_candidate_tensor_contract,affine_benders_atom_score_contract,dp_top1_runtime_output_contract,fail_closed_observability_contract,no_promotion_no_claims_contract",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_heads_sha256=fdfae96c315e129c2467400944596c40f6a7eb4a7f63b040c3b21eb96043cbfd",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_command_sha256=0019acc37d04f48a0d6656ca93fc1028230046f9cfc50cba4d9218e1618a9b6e",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_stdout_sha256=e9bf3777087899f5345ddc2e2da78880c1f9e47e4cacd3acd0f78c31564cb002",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_json_sha256=8eceaef8bf837e9450acda594c37b8e2021e6a92f02d338336c5887c2f2342ef",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_md_sha256=dd961f331672720e1a494985721f8091e554af68478e39bf4e4458b47f63cca1",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_sha256s_sha256=d0078e0a716fb1a66425837ec5885d1482ba9504f37ced24477f413c662b1b24",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_executed_trajectory_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_only",
        "default_off_shadow_selector_static_contract_plan_ready=True",
        "default_off_shadow_selector_implementation_plan_ready=True",
        "default_off_shadow_selector_implementation_static_contract_review_passed=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_implementation_unit_tests_plan_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Static "
        "Contract Review Passed After 5687ee"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Unit "
        "Tests Plan Ready After 0152e7"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Unit "
        "Tests Passed After 154663"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_script=scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_local_pytest=15 passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_0152e7bd81_20260703T003918CST",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_camp_head=0152e7bd81dcbbd0962b35a96df5392028b53f47",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_camp_origin_main=0152e7bd81dcbbd0962b35a96df5392028b53f47",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_source_review=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_5687ee3ee6_20260703T002900CST/default_off_shadow_selector_implementation_static_contract_review.json",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_passed=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_only",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_only",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_ready=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_unit_tests_only_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_implementation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_source_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_source_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_source_contract_count=7",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_target_test_file=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_test_groups=default_off_disabled_contract,immutable_artifact_hash_contract,fixed_candidate_affine_score_contract,dp_top1_shadow_runtime_contract,no_candidate_mutation_contract,benders_and_seed_boundary_contract",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_heads_sha256=05e0c9de39562ea6344cc79cd8b3e25450e2fdbc5bfc1c57f7534a26e5ac8ee0",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_command_sha256=13e13ecb733cad82cdb6820873a04b0c37a97c0cf8d402dfdd73df3566807963",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_stdout_sha256=4783be553a081b04963ac5b6905057961ad54ae67f306e79de6e504eb6ce540e",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_json_sha256=499c4da63d66818ac7ab3a16bcd5bea8af2086cc64df10dab759c2c0d451ee44",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_md_sha256=5479b4852ed35bdc904bf3709dde4410464c9c69b18e709402271eb55252f9e2",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_sha256s_sha256=cebaea57596b233271e857e35a4908de07c80b734b06111c8460b0a9ad897194",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_training_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_atom_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_deployable_checkpoint_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_only",
        "default_off_shadow_selector_implementation_unit_tests_plan_ready=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_implementation_unit_tests_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Unit "
        "Tests Plan Ready After 0152e7"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Unit "
        "Tests Passed After 154663"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Passed "
        "After 98e495"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_file=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_source_plan_script=scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_local_pytest=20 passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_commit=1546633d50750358379694243b3629ac08aabe3c",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_failure_artifact_1=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_1546633d50_20260703T005637CST",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_failure_artifact_1_exit=127",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_failure_artifact_1_failure_class=python312_alias_missing",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_failure_artifact_2=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_rerun_1546633d50_20260703T005806CST",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_failure_artifact_2_exit=1",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_failure_artifact_2_failure_class=base_python_pytest_missing",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_rerun_dp312_1546633d50_20260703T005948CST",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_camp_head=1546633d50750358379694243b3629ac08aabe3c",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_camp_origin_main=1546633d50750358379694243b3629ac08aabe3c",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_python=/root/autodl-tmp/dp312_venv/bin/python",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_python_version=Python 3.12.3",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_pytest_version=pytest 8.3.5",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_autodl_pytest=20 passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_only",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_passed=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_groups=default_off_disabled_contract,immutable_artifact_hash_contract,fixed_candidate_affine_score_contract,dp_top1_shadow_runtime_contract,no_candidate_mutation_contract,benders_and_seed_boundary_contract",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_heads_sha256=3e30c79f2c10e7cffef6f7205045c2f0799004fcbcdf78e6acd3d9100f9d871c",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_command_sha256=42c505aad6a624912075885a30d6493bbd0ab8266cbe318ba0997513c7d0f9e3",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_runbook_sha256=18bcddb68e9945c5e94ada7d6874b01f58f4e74ea0ed520a853748a448adcc30",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_stdout_sha256=ad0dc4e03f578b11e385fa9e13d6dc87c7951e135f3a5d393ab7a2756d369943",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_sha256s_sha256=1ebe8b8e528e3fc8861f94cda963465f4a95bd365ad72d4bab57a488654eed47",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_executed_trajectory_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
        "default_off_shadow_selector_implementation_unit_tests_passed=True",
        "implementation_only_requires_explicit_user_authorization=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_implementation_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Unit "
        "Tests Passed After 154663"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Passed "
        "After 98e495"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Post-Implementation Static "
        "Review Passed After 2610c4"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_implementation_source_file=scripts/integrations/run_diffusion_planner_camp_replay.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_test_file=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py",
        "v14_public_simulator_default_off_shadow_selector_implementation_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_implementation_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_implementation_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_local_pytest=42 passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_commit=98e495749e605304f1094bff62e47ab7c8317775",
        "v14_public_simulator_default_off_shadow_selector_implementation_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_98e495749e_20260703T011920CST",
        "v14_public_simulator_default_off_shadow_selector_implementation_camp_head=98e495749e605304f1094bff62e47ab7c8317775",
        "v14_public_simulator_default_off_shadow_selector_implementation_camp_origin_main=98e495749e605304f1094bff62e47ab7c8317775",
        "v14_public_simulator_default_off_shadow_selector_implementation_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_implementation_python=/root/autodl-tmp/dp312_venv/bin/python",
        "v14_public_simulator_default_off_shadow_selector_implementation_exit=0",
        "v14_public_simulator_default_off_shadow_selector_implementation_autodl_pytest=42 passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_passed",
        "v14_public_simulator_default_off_shadow_selector_implementation_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_implementation_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_implementation_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_only_after_explicit_user_authorization",
        "v14_public_simulator_default_off_shadow_selector_implementation_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_implementation_passed=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_default_off=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_fail_closed=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_executed_output_policy=dp_top1",
        "v14_public_simulator_default_off_shadow_selector_implementation_selection_effect=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_online_selector_change=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_implementation_schema_v14_pinned=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_schema_v13_rejected=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_result_json_valid=True",
        "v14_public_simulator_default_off_shadow_selector_implementation_heads_sha256=7d91c71a83101d131305e2f507ccce4a83a4c6c322d4987bfa2fd3daa998e520",
        "v14_public_simulator_default_off_shadow_selector_implementation_command_sha256=b03091209592a1dc359a84ddb05d3af35364fb2396da013be4d754b31a51c18d",
        "v14_public_simulator_default_off_shadow_selector_implementation_runbook_sha256=9e6ce4a1795e780fa6b21280cfa062cbe260ec47d94cb39d88aeaf8759524bbb",
        "v14_public_simulator_default_off_shadow_selector_implementation_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_default_off_shadow_selector_implementation_stdout_sha256=f862c57a601f60bb0105c16f19eb1fde57c14b83120c1633a204aa197e08e9e3",
        "v14_public_simulator_default_off_shadow_selector_implementation_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_shadow_selector_implementation_result_json_sha256=f8ea96f8775f3460fd1ba625ac5f545062230afad4f1ca6182c3e4ff92b4c84c",
        "v14_public_simulator_default_off_shadow_selector_implementation_result_md_sha256=b419178eabf9784c195ecf44b070d08a6a53941bf8abd9cdc0102a91c4f27d8d",
        "v14_public_simulator_default_off_shadow_selector_implementation_sha256s_sha256=d0be444a9e3454545ce0cacbf0828007d33ae4dfaff8b8d0aab5cae77e9ae3ea",
        "v14_public_simulator_default_off_shadow_selector_implementation_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_executed_trajectory_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_implementation_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_only",
        "default_off_shadow_selector_implementation_passed=True",
        "post_implementation_static_contract_review_authorized=True",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_post_static_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Implementation Passed "
        "After 98e495"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Post-Implementation Static "
        "Review Passed After 2610c4"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Plan Ready After 2456037"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_post_static_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_post_implementation_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_post_implementation_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_local_pytest=44 passed",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_commit=2610c4a89f20f86a4ffbe8a8f275ae56a6b85b3a",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_post_implementation_static_contract_review_2610c4a89f_20260703T013539CST",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_source_implementation_result=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_98e495749e_20260703T011920CST/result.json",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_camp_head=2610c4a89f20f86a4ffbe8a8f275ae56a6b85b3a",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_camp_origin_main=2610c4a89f20f86a4ffbe8a8f275ae56a6b85b3a",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_python=/root/autodl-tmp/dp312_venv/bin/python",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_exit=0",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_autodl_pytest=44 passed",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_passed",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_only",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_passed=True",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_default_off=True",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_fail_closed=True",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_executed_output_policy=dp_top1",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_selection_effect=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_online_selector_change=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_runtime_artifact_manifest_plan_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_runtime_artifact_manifest_materialization_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_runtime_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_heads_sha256=5561159d1c0411ff87e05ae5b24d389771a7740e710adccc07e3b8c55e3d7f5d",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_command_sha256=86c66d151605327d526c69dd3cca2f8c27d06cfee8c5f33bbbfc8f5e500faca1",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_runbook_sha256=a5cea524932665b60b22ca00f8153967b04bb45884d47354b6a17a55e4460012",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_stdout_sha256=5b58ed1dedca9cfe19cb24f141ffc1a7f9c344436a946b995690f428ef4b4636",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_result_json_sha256=326d7262f6b4feaf504969bed4c699ee2052cda679ed2abca0aa41a7fc5868f2",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_result_md_sha256=6d5076a9d5324def4a115b1719d40fbecad793e05469493afe130a30ee6b23aa",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_report_json_sha256=7f41814b1e5843e77b67708d8b235306512cad61993d54c3ed92579ce27641e3",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_report_md_sha256=e95c8623cce5ec333468be6faa28c9a3932b57e9e9083d1c6120a8b74e51dc59",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_report_sha256s_sha256=63fb3272bf25cf1802eb3590efa69ffbc45143ad31b8becddf1c15d80f060751",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_sha256s_sha256=706ce66d9f9bfa5a9dc75c2053d3dd0689e304e508b64240346d9f13b87da705",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_executed_trajectory_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_post_static_review_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_only",
        "default_off_shadow_selector_post_implementation_static_contract_review_passed=True",
        "runtime_artifact_manifest_plan_authorized=True",
        "runtime_artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_plan_ready_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Post-Implementation Static "
        "Review Passed After 2610c4"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Plan Ready After 2456037"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Static Review Passed After 11f1f7"
    )
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_script=scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_script_sha256=0efc8063f5281c7d5672760962a7358ec345771936772930c566fe06e4925f32",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_test_sha256=85690a5f2f5b728b75257c3bab45f468c86c3cfb13dfce0da102472632fe337e",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_local_pytest=8 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_commit=2456037d6f3b214f31ea5991a28732aa52e7bed4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_report_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST/report/default_off_shadow_selector_runtime_artifact_manifest_plan.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_result_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST/result.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_camp_head=2456037d6f3b214f31ea5991a28732aa52e7bed4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_camp_origin_main=2456037d6f3b214f31ea5991a28732aa52e7bed4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_python=/root/autodl-tmp/dp312_venv/bin/python",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_autodl_pytest=8 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_ready=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_check_count=121",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_manifest_role=default_off_shadow_selector_runtime_artifact_manifest",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_materialized_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_real_runtime_manifest_materialized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_default_off=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_fail_closed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_selector_mode=static",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_executed_output_policy=dp_top1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_selection_effect=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_online_selector_change=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_candidate_operation=fixed DP candidate reranking only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_required_candidate_count=8",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_atom_count=9",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_atom_schema_version=camp_legacy_v1_9d",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_required_runtime_entries=atom_scales,static_weights",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_required_evidence_entries=training_summary,post_static_review,implementation_result,replay_runner",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_training_summary_sha256=783684d1fd7038587efc43a47e4ca4f88eb392267187eb4e0042ed346b9fc6a0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_atom_scales_sha256=2239fb09e2231405dbc58b1a79486ff3f3c111a9bab96c24d88e6832f2325b8b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_static_weights_sha256=5bfe692465c0e0cdbf2fb937737674e53b3f41a31ea932a65f65a6321f4c0dde",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_post_static_review_sha256=7f41814b1e5843e77b67708d8b235306512cad61993d54c3ed92579ce27641e3",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_implementation_result_sha256=f8ea96f8775f3460fd1ba625ac5f545062230afad4f1ca6182c3e4ff92b4c84c",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_replay_runner_sha256=1aa0bb0cbddd0b5eb09725b08e41190d828523d9e08074d789e80559ef5f8da0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_heads_sha256=69385db22c7eb097a35592c9fb5e3c8207abddcf13f5f645c27657bebe89caa5",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_command_sha256=4c578371109a203935d4db30adebe4118acaf79549d8ba44f2471e257f5527a5",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_runbook_sha256=b76a58d92f3df2ea583512d42f19317bbae57114ae12fa6de0970b06b921a6e7",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_stdout_sha256=d5936850ae099ef792526a6f0b8e86e5e90fe93bc78ddc1a7ef593178c162d5e",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_report_json_sha256=be3734e2d897c85c797ad6cb03ccf3f7af6c88202a0db26954dc9e4e1f984b74",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_report_md_sha256=2d15e8e288684e31e6cc7e4fc209df8a91aa09d7cb1e5e853d72dedfbb7c8291",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_result_json_sha256=014a97c01e24c9b08c6b6405335ca488c9dd453b2e182deb99d105836e31dcc8",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_result_md_sha256=f2fb5c9850acadb1a371d6b38872c50db50a9d24fa448dfbafa33072c9419ebf",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_sha256s_sha256=321998d25ec45bfee32890636a4acae76a0b7ce342cae17ca7efd55f7d1e995b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_training_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_executed_trajectory_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_atom_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_deployable_checkpoint_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_only",
        "runtime_artifact_manifest_plan_ready=True",
        "runtime_artifact_manifest_static_contract_review_authorized=True",
        "runtime_artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "online_selector_change_authorized=False",
        "executed_trajectory_change_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_static_review_passed_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Plan Ready After 2456037"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Static Review Passed After 11f1f7"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Plan Ready After ddce7a"
    )
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_script_sha256=3be08a737a20fd0957697b586e72fee50dfbf9dafd024aa58fb28d3222fcf8b8",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_test_sha256=05cdbbf8df6ca469e7b939142d5a545b6da88f88f4fa3e4bb4e171a059923309",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_initial_failed_commit=e8fd20270e9a8993c78d34c4e55086749eba07a5",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_initial_failed_failure_class=runtime_artifact_manifest_static_contract_failure",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_initial_failed_checks=script_v14_plan_schema,script_authorizes_static_review_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_remediation_commit=11f1f7f853e66eec5327184479fb24ab133cb5bc",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_success_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_11f1f7f853_20260703T021546CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_camp_head=11f1f7f853e66eec5327184479fb24ab133cb5bc",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_autodl_pytest=9 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_passed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_check_count=110",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_source_plan_materialized_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_required_runtime_entries=atom_scales,static_weights",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_required_evidence_entries=implementation_result,post_static_review,replay_runner,training_summary",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_report_json_sha256=e9bbd2f62de4bbc06f740bef784c3fec5f7cf768c9878ddb5da3ad12b3e4d7cb",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_sha256s_sha256=554384a654840f5bfcc5ea4d9b4d6e6ba550a0b314e5daccd64cd7238bc05fb6",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_materialization_plan_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_materialization_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_runtime_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_review_runtime_manifest_materialized_by_this_gate=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_only",
        "runtime_artifact_manifest_static_contract_review_passed=True",
        "runtime_artifact_manifest_materialization_plan_authorized=True",
        "runtime_artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ready_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Static Review Passed After 11f1f7"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Plan Ready After ddce7a"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Static Review Passed After 844e46"
    )
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_script=scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_script_sha256=f86cefc1c828edeb7db00d99d825879622c5eb2bfea4504eded180614ad23200",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_test_sha256=aa646e89a763c87dc26f31a1e0ce6b79c9313fed5f6e0e1bc5cbdd6639d539ac",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_support_commit=ddce7a172512060ec990f6d01b1269888ca72024",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_local_pytest=7 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_autodl_pytest=7 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ddce7a1725_20260703T023207CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_source_static_review_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_11f1f7f853_20260703T021546CST/report/runtime_artifact_manifest_static_contract_review.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_source_plan_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST/report/default_off_shadow_selector_runtime_artifact_manifest_plan.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_planned_runtime_manifest_exists_after_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_camp_head=ddce7a172512060ec990f6d01b1269888ca72024",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_passed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_check_count=109",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_schema_version=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_future_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_future_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_future_candidate_operation=fixed DP candidate reranking only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_future_executed_output_policy=dp_top1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_future_required_candidate_count=8",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_future_atom_count=9",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_future_atom_schema_version=camp_legacy_v1_9d",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_future_artifacts=atom_scales,static_weights",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_runtime_manifest_written_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_runtime_manifest_materialized_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_runtime_execution_enabled_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_source_static_review_sha256=e9bbd2f62de4bbc06f740bef784c3fec5f7cf768c9878ddb5da3ad12b3e4d7cb",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_source_plan_sha256=be3734e2d897c85c797ad6cb03ccf3f7af6c88202a0db26954dc9e4e1f984b74",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_heads_sha256=681bd4ee380d047ecc4f6372ca105d9ba32812476905f570b235c5ed6ab4de24",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_command_sha256=05c8b8b747c724be85b6a4c27b533be1ec4ed7e210c8df70d8b6a483ad020bc0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_report_json_sha256=bac353cb142af137a03e3fa96c21892f57ef3cfe3a3f280d311b1e80a504693d",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_report_md_sha256=5defbd0560c4ae3d86bafb131ecf1d2317ab3aa0a71b16169c8e75be5b9aa030",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_sha256s_sha256=23179ca81f45cfd997af9953b8a1d129b458e324c38d6ac23fe720395576aa2e",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_materialization_static_review_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_materialization_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_runtime_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_camp_over_dp_top1_claim_authorized=False",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_only",
        "runtime_artifact_manifest_materialization_plan_ready=True",
        "runtime_artifact_manifest_materialization_static_contract_review_authorized=True",
        "runtime_artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Plan Ready After ddce7a"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Static Review Passed After 844e46"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Implementation Plan Ready After 3aeb54"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_script_sha256=cbe8e81c9bbca21d1e5c45326899a2fdcd294a8cb1c6e731c46b4e0af8579491",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_test_sha256=b28d6a8fa5033faf700c0eaca471511c5ba9b688f22b1d31ea955a5f7bede3c3",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_support_commit=844e46604c460027fc0c8602903b7c365ef91d6b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_local_pytest=8 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_autodl_pytest=8 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_844e46604c_20260703T024304CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_source_plan_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ddce7a1725_20260703T023207CST/report/runtime_artifact_manifest_materialization_plan.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_planned_runtime_manifest_exists_after_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_camp_head=844e46604c460027fc0c8602903b7c365ef91d6b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_passed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_check_count=114",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_schema_version=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_source_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_required_runtime_entries=atom_scales,static_weights",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_runtime_manifest_written_by_source_plan=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_runtime_manifest_materialized_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_materialization_implementation_plan_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_materialization_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_runtime_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_source_plan_sha256=bac353cb142af137a03e3fa96c21892f57ef3cfe3a3f280d311b1e80a504693d",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_heads_sha256=91df210cf67eb337f7ce74e1042e6f9700551c6c279b448da7edfdfa7eb528f9",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_command_sha256=b56d5987fecc740de1305ad69bc708c9ab68696e1edbd9af5a3fd43d893d63e8",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_exit_code_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_report_json_sha256=aa3b096059d671cd42d888f7929114800fecd8c50b65af319dbb6e28b52b7134",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_report_md_sha256=38e22d57a3022c246b7e2aaec9dad8be45d50cca6f90f70150fa018d1269b335",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_review_sha256s_sha256=b3a34cfbaaedd8493c3a91f550d358e52a8190ff67065217bfe2ff757ee6f746",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_only",
        "runtime_artifact_manifest_materialization_static_contract_review_passed=True",
        "runtime_artifact_manifest_materialization_implementation_plan_authorized=True",
        "runtime_artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Static Review Passed After 844e46"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Implementation Plan Ready After 3aeb54"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Implementation Static Review Passed After af4064"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_script=scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_script_sha256=202a57d0b8dca149dcd4505090453ffc50ce84ee793dfe03a212eb0674a1249d",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_test_sha256=a87c25229a1c6160028a7013bc67cd322d04410418504700d1d1766e61b1b452",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_support_commit=3aeb54ec0bdf6e9c24d22ddf102b7ac4d828c790",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_local_pytest=8 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_autodl_py312_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_autodl_camp_env_pytest=8 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_3aeb54ec0b_20260703T030149CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_source_static_review_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_844e46604c_20260703T024304CST/report/runtime_artifact_manifest_materialization_static_contract_review.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_source_plan_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ddce7a1725_20260703T023207CST/report/runtime_artifact_manifest_materialization_plan.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_planned_runtime_manifest_exists_after_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_camp_head=3aeb54ec0bdf6e9c24d22ddf102b7ac4d828c790",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_ready",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_passed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_check_count=119",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_schema_version=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_source_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_required_runtime_entries=atom_scales,static_weights",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_write_strategy=same-directory temp file plus atomic replace",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_writes_exactly_one_runtime_manifest=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_runtime_manifest_written_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_runtime_manifest_materialized_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_implementation_static_contract_review_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_implementation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_materialization_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_runtime_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_training_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_source_plan_sha256=bac353cb142af137a03e3fa96c21892f57ef3cfe3a3f280d311b1e80a504693d",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_source_static_review_sha256=aa3b096059d671cd42d888f7929114800fecd8c50b65af319dbb6e28b52b7134",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_heads_sha256=fd2f88f7b272648304a579441bce52b8ca68a1376dbac1ba88b8c997e493304e",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_command_sha256=7dfe34390f96d142bc68637f3cc964af1b0280921e25013cf33b8739c5282e6b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_report_json_sha256=8b15be1ccd3be99f0924e71d5ed3befdd57a3416e6ebaa00a1f8986aee68ff59",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_report_md_sha256=ed972c85f26ad597480197aba4c6c40a944c0acc765d4250ce1c73f7ec003e68",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_sha256s_sha256=391438fb49d63de0139d85bbb9d7cff1ffbeb62fad52dd735ff60e59dd4e51b0",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_only",
        "runtime_artifact_manifest_materialization_implementation_plan_ready=True",
        "runtime_artifact_manifest_materialization_implementation_static_contract_review_authorized=True",
        "runtime_artifact_manifest_materialization_implementation_authorized=False",
        "runtime_artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Implementation Plan Ready After 3aeb54"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Implementation Static Review Passed After af4064"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materializer Implementation Complete After 9b772d"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_script_sha256=2e0f1b6c532f92288b69d1b3ea08b05178d77a05582a865e9941f3d36a573d2f",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_test_sha256=9f3660e94b5df7e83d188d6c4c50683e72b81c23cf0600be374b877d4df881e3",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_initial_support_commit=1fcbfe36806367a1d0658677eb3186cf041e4d5b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_support_commit=af4064d7baacb7f073a8aded89a588233e4e80ce",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_local_pytest=10 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_autodl_py312_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_autodl_camp_env_pytest=10 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_first_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_1fcbfe3680_20260703T031832CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_first_failed_exit=1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_first_failed_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_rejected",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_first_failed_checks=script_implementation_plan_schema,script_authorizes_static_review_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_first_failed_failure_class=source_surface_contract_failure",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_first_failed_report_json_sha256=7c118d4be873113f7f836e8233d70897e9d09037ea1c1646e64af539ad940dbb",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_first_failed_sha256s_sha256=9aec6143de64db4362fe814fa3c71bd5b235539c0f5fedacae0242f7d88ab0cc",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_first_failed_remediation=replace_contiguous_long_constant_source_surface_checks_with_contract_suffix_checks",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_af4064d7ba_20260703T032021CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_report_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_af4064d7ba_20260703T032021CST/report/runtime_artifact_manifest_materialization_implementation_static_contract_review.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_source_implementation_plan_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_3aeb54ec0b_20260703T030149CST/report/runtime_artifact_manifest_materialization_implementation_plan.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_camp_head=af4064d7baacb7f073a8aded89a588233e4e80ce",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_passed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_failure_class=None",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_check_count=109",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_schema_version=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_required_runtime_entries=atom_scales,static_weights",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_future_materializer_script=scripts/integrations/build_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_future_materializer_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_runtime_manifest_written_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_runtime_manifest_materialized_by_this_gate=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_materializer_implementation_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_materialization_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_runtime_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_training_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_source_plan_sha256=8b15be1ccd3be99f0924e71d5ed3befdd57a3416e6ebaa00a1f8986aee68ff59",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_heads_sha256=a8e58b70677972d7ae119725a24edf5f8ef8f52ce57168ab1ebdeedb33ff8583",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_command_sha256=177c26c175cffaef56b2cf60efdc85ac3116cac09bd3850fff67352bcd5af8e8",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_report_json_sha256=30ba6e44ec75dacf5fb1fea5ee096bc5f333c1f6087d01cfd0a48e58e273c775",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_report_md_sha256=0263b3dd4893bbd1c5a2e61b4f50d4bd1a81590c646209fe0524e00c4b8dc2fa",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_review_sha256s_sha256=6077c3aa952e4b2a15f01d89330fd018eb2058b19e52aeb29bd4478977129798",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only",
        "runtime_artifact_manifest_materialization_implementation_static_contract_review_passed=True",
        "runtime_artifact_manifest_materializer_implementation_authorized=True",
        "runtime_artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_complete_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialization Implementation Static Review Passed After af4064"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materializer Implementation Complete After 9b772d"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materializer Post-Implementation Static Review Passed After 97754f"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_status=implemented_tests_passed_no_real_manifest_materialized",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_script=scripts/integrations/build_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_script_sha256=9219b03efe692b00eb92ed7d9af9ceaa372937ead1afbe957a9edc48e855ae89",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_test_sha256=95b7e1dc6ceffc9c4093facc4f73f807b635c37d1e07e0599383334802e22af7",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_commit=9b772d78233cafe508fd2f140188b3f391382d11",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_github_refs_heads_main_after_push=9b772d78233cafe508fd2f140188b3f391382d11",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_autodl_camp_head_after_sync=9b772d78233cafe508fd2f140188b3f391382d11",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_autodl_camp_origin_main_after_sync=9b772d78233cafe508fd2f140188b3f391382d11",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_autodl_dp_head_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_local_pytest=12 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_autodl_py312_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_autodl_camp_env_pytest=12 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_default_off_before_reading_inputs=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_fail_closed_without_output=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_implementation_plan_sha256=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_fixed_dp_head=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_output_path_equals_plan=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_runtime_schema=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_default_off_fail_closed_static_selector=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_score_expression_affine=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_atom_scales_sha256=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_verifies_static_weights_sha256=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_uses_same_directory_temp_file=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_uses_atomic_replace=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_writes_exactly_one_manifest_when_enabled=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_no_replay_train_or_dp_source_touch=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_real_runtime_manifest_materialized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_real_replay_executed=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_training_executed=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_candidate_generation_executed=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_dp_modified=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_selector_promoted=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_deployed=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_safety_benefit_claimed=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_camp_over_dp_top1_claimed=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_complete",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only",
        "runtime_artifact_manifest_materializer_implementation_complete=True",
        "runtime_artifact_manifest_materializer_post_implementation_static_contract_review_authorized=True",
        "runtime_artifact_manifest_materialization_authorized=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materializer Implementation Complete After 9b772d"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materializer Post-Implementation Static Review Passed After 97754f"
    )
    next_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialized After bae519"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_script=scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_test=camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract.py",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_script_sha256=018a5545ee01c64cf025e5f94976b25558b362c428cef07975f0598dffb6bf3b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_test_sha256=7d30a023ee0d3f2fed83557a8f1539046bf99a5fe20b89ec9464472e3bb0c35b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_initial_support_commit=169e5d10c41f50882c3990b336c79a566739a875",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_support_commit=97754f14ee1f5511ba3e779520a186600a63bfca",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_local_pytest=10 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_autodl_py312_py_compile_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_autodl_camp_env_pytest=10 passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_first_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_169e5d10c4_20260703T035722CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_first_failed_exit=1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_first_failed_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_rejected",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_first_failed_checks=materializer_schema_constant,materializer_source_plan_schema",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_first_failed_failure_class=source_surface_contract_failure",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_first_failed_report_json_sha256=556f1f1dbed1f8ba45f049a5f53b030ce2bf061d7e297dbee024693273d90ca4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_first_failed_sha256s_sha256=58d62cfd1614f1b494d33d2209eeffdb0aaec69b4dfa76eb25188273113ebc6b",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_first_failed_remediation=replace_contiguous_long_schema_source_surface_checks_with_contract_suffix_checks",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_97754f14ee_20260703T035849CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_report_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_97754f14ee_20260703T035849CST/report/runtime_artifact_manifest_materializer_post_implementation_static_contract_review.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_source_implementation_plan_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_3aeb54ec0b_20260703T030149CST/report/runtime_artifact_manifest_materialization_implementation_plan.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_camp_head=97754f14ee1f5511ba3e779520a186600a63bfca",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_passed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_check_count=121",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_runtime_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_runtime_entries=atom_scales,static_weights",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_planned_runtime_manifest_exists=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_runtime_artifact_manifest_materialization_authorized=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_runtime_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_training_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_report_json_sha256=5c6056f4f25574ec44de05eac017022f4dcc3827daee6cd69695f14956835886",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_report_md_sha256=1e19b1043b2c14e1e9a42ce199f66922494da71fcb6fc6f3fba167998b9f7625",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_static_review_sha256s_sha256=72d87c7b27d160a2ffbb03b02c4089fab4ec39783c5e60f3221f122f4e66a68f",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_only",
        "runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed=True",
        "runtime_artifact_manifest_materialization_authorized=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_only",
    ]:
        assert needle in text


def test_v14_default_off_shadow_selector_runtime_artifact_manifest_materialized_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materializer Post-Implementation Static Review Passed After 97754f"
    )
    section_title = (
        "## Current V14 Default-Off Shadow Selector Runtime Artifact Manifest "
        "Materialized After bae519"
    )
    next_section_title = "## Default-Off Selector Runtime Shadow Replay Preflight"

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_bae51947d2_20260703T040546CST",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_camp_head=bae51947d2ce4e51937da823703181fbf095a333",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_camp_origin_main=bae51947d2ce4e51937da823703181fbf095a333",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_source_implementation_plan_sha256=8b15be1ccd3be99f0924e71d5ed3befdd57a3416e6ebaa00a1f8986aee68ff59",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_output_existed_before=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_output_runtime_manifest=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST/report/planned_runtime/dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.json",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_output_runtime_manifest_sha256=92e82fbf2e7bb26847b6f24b8ccc9d78242addb451bc7301aa77997592569bd2",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_runtime_manifest_summary_sha256=6e5cdae55b3fccdefd9bd2081e47d4f5a3e88cd7c0b08356117ec47a519945d2",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_sha256s_sha256=c33f265c9c278a3e03a6c15f601ea31e97810116b536ee6e4d0d40ed8818cfd4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_exit=0",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialized",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_passed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_failed_checks=[]",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_schema_version=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_manifest_role=default_off_shadow_selector_runtime_artifact_manifest",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_source_scope=public_simulator_fixed_dp_candidate_tensor",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_default_off=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_fail_closed=True",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_selection_effect=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_online_selector_change=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_selector_mode=static",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_candidate_operation=fixed DP candidate reranking only",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_executed_output_policy=dp_top1",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_required_candidate_count=8",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_atom_count=9",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_atom_schema_version=camp_legacy_v1_9d",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_artifact_logical_names=atom_scales,static_weights",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_runtime_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_replay_execution_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_training_executed=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_dp_modification_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_deployment_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_preflight_only",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialized",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_preflight_only",
        "runtime_artifact_manifest_materialized=True",
        "default_off_shadow_selector_runtime_shadow_replay_preflight_authorized=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_preflight_only",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_shadow_replay_result_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Default-Off Selector Runtime Shadow Replay Execution"
    section_title = "## Default-Off Selector Runtime Shadow Replay Result Review"
    next_section_title = "## Default-Off Selector Runtime Shadow-vs-Top1 Delta Review"

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_source_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_artifact_dbd5b539a0_20260703T090930CST",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_source_execution_audit_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_artifact_dbd5b539a0_20260703T090930CST/report/runtime_shadow_replay_execution_audit.json",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_camp_head=9e86ec1fb2bb9f22df578712b8003414694131f1",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_camp_origin_main=9e86ec1fb2bb9f22df578712b8003414694131f1",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_exit=0",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_result_review_passed",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_passed=True",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_only_after_explicit_user_authorization",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_promotion_decision_plan_authorized_next=True",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_selection_logs=32",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_validation_summaries=32",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_replay_summaries=32",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_records=3200",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_default_off_selector_records=3200",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_executed_top1_records=3200",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_shadow_selected_index_nonzero_records=2832",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_used_fallback_records=286",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_formal_seed_path_count=0",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_max_affine_score_error=4.440892098500626e-16",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_source_execution_audit_json_sha256=1277624d6ff07b4a02f73c18af10f68a84a6e999b1483a5d654adafebc9cba7c",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_report_json_sha256=627fe492c69bbc422a798f025e2cb632008b61dd193b3fa59e1c5c84fbb603ab",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_sha256s_sha256=27bc90bf3f55add804ab6535f44cf02b879cabd7262a27da9df4547552ded6d0",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_replay_executed_by_review=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_candidate_generation_executed_by_review=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_training_executed_by_review=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_candidate_generation_by_camp_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_trajectory_modification_by_camp_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_dp_modification_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_approved_atoms_nonnegative_simplex_only=True",
        "v14_public_simulator_default_off_selector_runtime_shadow_replay_result_review_simplex_cvar_l2_master_convexity_preserved=True",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_result_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_only_after_explicit_user_authorization",
        "default_off_shadow_selector_runtime_shadow_replay_result_review_passed=True",
        "default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_authorized_next=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_only_after_explicit_user_authorization",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_shadow_vs_top1_delta_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Default-Off Selector Runtime Shadow Replay Result Review"
    section_title = "## Default-Off Selector Runtime Shadow-vs-Top1 Delta Review"
    next_section_title = "## Default-Off Selector Runtime Promotion-Decision Plan"

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_vs_top1_delta_review_04f4b68421_20260703T103434CST",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_source_execution_output_root=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_dbd5b539a0_20260703T090512CST",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_source_result_review_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST/review/result_review_report.json",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_camp_head=04f4b6842178204717051209e0b106c67332d420",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_camp_origin_main=04f4b6842178204717051209e0b106c67332d420",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_exit=0",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_passed",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_passed=True",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_static_objective_delta_supported=True",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_authorized_inserted_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_only_after_explicit_user_authorization",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_only_after_explicit_user_authorization",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_selection_logs=32",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_records=3200",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_executed_top1_records=3200",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_selected_index_matches_executed_index_records=3200",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_shadow_selected_index_nonzero_records=2832",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_shadow_selected_index_differs_from_executed_index_records=2832",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_selection_score_better_records=2832",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_selection_score_tie_records=368",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_selection_score_worse_records=0",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_selection_score_uncomparable_records=0",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_shadow_diff_selection_score_better_records=2832",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_shadow_diff_selection_score_tie_records=0",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_shadow_diff_selection_score_worse_records=0",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_selection_score_finite_delta_mean=-0.044903412834032194",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_raw_affine_score_better_records=2804",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_raw_affine_score_worse_records=28",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_feasible_pair_counts={'top1_False_shadow_False': 286, 'top1_False_shadow_True': 58, 'top1_True_shadow_True': 2856}",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_formal_seed_path_count=0",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_source_result_review_json_sha256=627fe492c69bbc422a798f025e2cb632008b61dd193b3fa59e1c5c84fbb603ab",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_source_result_review_md_sha256=914896b623c554c7d07b3ce8429ea6f7dc94e9885efa02ff1fc6399fff8ce551",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_heads_sha256=4e2fa49eb62aff28c8e899596365711ff495b4d380ef4d64526a01f38d1f0947",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_command_sha256=99bc14ab5d6b66089af10c06df5f0d20d12b4abd68745b6df11dac2c7fa74599",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_stdout_sha256=9fc97843f5edd143e4a8a33e3b9d1ada42b0620a9b142ea4f584e39544384df2",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_report_json_sha256=2bdfbce1e89db54465d895148f3dc3ecae2a511b3db889a29f693cb4cdfebc62",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_report_md_sha256=177b291d90b6a2e06f5f37358b5b4e9238c1543c7f23d732c22168dd8b1a01b4",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_sha256s_sha256=24b24b26ad644076ec2952b575b840068e44e13ee12abcf78416655f799722bd",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_replay_executed_by_review=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_candidate_generation_executed_by_review=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_training_executed_by_review=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_dp_modification_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_selector_runtime_shadow_vs_top1_delta_review_claim_scope=static_objective_delta_only_not_safety_or_camp_over_dp_top1",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_only_after_explicit_user_authorization",
        "default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_passed=True",
        "default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_static_objective_delta_supported=True",
        "default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_authorized_next=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_only_after_explicit_user_authorization",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_promotion_decision_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Default-Off Selector Runtime Shadow-vs-Top1 Delta Review"
    section_title = "## Default-Off Selector Runtime Promotion-Decision Plan"
    next_section_title = "## Default-Off Selector Runtime Promotion Evidence-Package Preflight"

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_decision_plan_192d2928b2_20260703T110247CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_source_runtime_result_review_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST/review/result_review_report.json",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_source_shadow_vs_top1_delta_review_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_vs_top1_delta_review_04f4b68421_20260703T103434CST/review/shadow_vs_top1_delta_review_report.json",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_camp_head=192d2928b2c9bbe22275f02c3c1532e713b1542f",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_camp_origin_main=192d2928b2c9bbe22275f02c3c1532e713b1542f",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_ready",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_passed=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_check_count=80",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_failed_check_count=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_recommendation=do_not_promote_from_current_evidence_alone",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_immediate_action=build_runtime_promotion_evidence_package_preflight_only",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_only",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_evidence_package_preflight_authorized=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_atom_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_deployable_checkpoint_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_training_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_replay_execution_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_dp_modification_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_executed_trajectory_change_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_runtime_result_records=3200",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_runtime_result_executed_top1_records=3200",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_runtime_result_shadow_selected_index_nonzero_records=2832",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_runtime_result_feasible_records=2914",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_runtime_result_used_fallback_records=286",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_static_objective_supported=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_selection_score_better_records=2832",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_selection_score_tie_records=368",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_selection_score_worse_records=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_selection_score_uncomparable_records=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_shadow_diff_selection_score_better_records=2832",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_shadow_diff_selection_score_worse_records=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_raw_affine_score_better_records=2804",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_delta_raw_affine_score_worse_records=28",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_source_runtime_result_review_json_sha256=627fe492c69bbc422a798f025e2cb632008b61dd193b3fa59e1c5c84fbb603ab",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_source_shadow_vs_top1_delta_review_json_sha256=2bdfbce1e89db54465d895148f3dc3ecae2a511b3db889a29f693cb4cdfebc62",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_heads_sha256=97a003617d68b631d014d2c03a3ba424a26d8dcdbcd71f93f2972b393e041b61",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_command_sha256=ed80c806005a2493daa0099738ca865912f3ad34222916979c73ff6e67eee562",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_stdout_sha256=3f96c41167211b357f127d4556c3517df7c1cf2c98b9124b7249ea1f95625bfd",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_report_json_sha256=16394aebd9cf92025fc36613f196d6f0728c1a60ec12768474e459d48e88eb44",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_report_md_sha256=ad6b48b9284aff63d86e18cdbe09e05b00f58e9629c4dc55bfd73a9511a4f396",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_plan_sha256s_sha256=978e6f39dff643f69d91378c775cebc4b60cdc6d16e2cf5a4e956767b9d76d7b",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_artifact_sha256s_sha256=c025186948924debf7e43b26c2d2d3025e649e167cf37c7301e8c5cfe312a811",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_plan_static_delta_is_not_safety_claim=True",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_only",
        "default_off_shadow_selector_runtime_promotion_decision_plan_ready=True",
        "default_off_shadow_selector_runtime_promotion_evidence_package_preflight_authorized=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_only",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_promotion_evidence_package_preflight_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Default-Off Selector Runtime Promotion-Decision Plan"
    section_title = "## Default-Off Selector Runtime Promotion Evidence-Package Preflight"
    next_section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Static Review "
        "Failed Attempt"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_promotion_decision_plan_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_decision_plan_192d2928b2_20260703T110247CST/plan/runtime_promotion_decision_plan.json",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_runtime_result_review_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST/review/result_review_report.json",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_shadow_vs_top1_delta_review_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_vs_top1_delta_review_04f4b68421_20260703T103434CST/review/shadow_vs_top1_delta_review_report.json",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_runtime_manifest_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST/report/planned_runtime/dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.json",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_camp_head=1758ea83eaf61ada32f60b7bbd15e97479b2e1e5",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_camp_origin_main=1758ea83eaf61ada32f60b7bbd15e97479b2e1e5",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_ready",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_passed=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_check_count=229",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_failed_check_count=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_manifest_entries=runtime_promotion_decision_plan,runtime_result_review,shadow_vs_top1_delta_review,runtime_manifest,training_artifact_static_review,training_summary,offline_weights_npy,atom_scales_json,runtime_shadow_execution_sha256s",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_only",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_static_review_authorized=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_atom_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_deployable_checkpoint_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_training_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_replay_execution_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_dp_modification_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_records=3200",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_selection_log_count=32",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_validation_summary_count=32",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_replay_summary_count=32",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_executed_top1_records=3200",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_shadow_selected_index_nonzero_records=2832",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_feasible_records=2914",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_used_fallback_records=286",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_delta_selection_score_better_records=2832",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_delta_selection_score_tie_records=368",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_delta_selection_score_worse_records=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_delta_selection_score_uncomparable_records=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_training_records=2914",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_dropped_records_without_feasible_candidate=286",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_num_candidates=8",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_num_atoms=9",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_runtime_manifest_schema=dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_promotion_decision_plan_json_sha256=16394aebd9cf92025fc36613f196d6f0728c1a60ec12768474e459d48e88eb44",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_runtime_result_review_json_sha256=627fe492c69bbc422a798f025e2cb632008b61dd193b3fa59e1c5c84fbb603ab",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_shadow_vs_top1_delta_review_json_sha256=2bdfbce1e89db54465d895148f3dc3ecae2a511b3db889a29f693cb4cdfebc62",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_runtime_manifest_json_sha256=92e82fbf2e7bb26847b6f24b8ccc9d78242addb451bc7301aa77997592569bd2",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_training_artifact_static_review_json_sha256=928c0997ef76ee406a47c4f0b2eabd46b9e011497b50063d48bd00facb6df8f0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_training_summary_sha256=783684d1fd7038587efc43a47e4ca4f88eb392267187eb4e0042ed346b9fc6a0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_offline_weights_npy_sha256=5bfe692465c0e0cdbf2fb937737674e53b3f41a31ea932a65f65a6321f4c0dde",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_atom_scales_json_sha256=2239fb09e2231405dbc58b1a79486ff3f3c111a9bab96c24d88e6832f2325b8b",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_source_runtime_shadow_execution_sha256s_sha256=55be6fa553f180dd2be565e2206c69285e4cd8850eab1832b8db10224e4c72ac",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_report_json_sha256=0cda58e1e95b36c867d9208ed51e4e23f24d1106f4460e5d932515eff976b6be",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_report_md_sha256=2381d1fa2f1213cc97d12b9f0ad798ec3432ce01b32fdfd35d0ac1576d7d911d",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_preflight_sha256s_sha256=e310582b40fc91cdaef7ad8c65284fc35beaed082b29411f949912a53b8b3065",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_artifact_sha256s_sha256=5e277729fe2c0690c599c006a02f221d94d553acdc164f2000e29dbc16283149",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_heads_sha256=3035a5fe450848672b47c4ea0d0595d6bd435e971ea6e82251b0a1e1fa5889bb",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_command_sha256=254e2232b09ef6a3fc2853aa9039ca86550ffe037a132a47c304c5d332359ba9",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_stdout_sha256=b2923bf971394da5cbf353f27764641fa8096ba7a472c9f408a8b7af497b6fc9",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_preflight_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_only",
        "default_off_shadow_selector_runtime_promotion_evidence_package_preflight_ready=True",
        "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_authorized=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_only",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_promotion_evidence_package_static_review_failure_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Default-Off Selector Runtime Promotion Evidence-Package Preflight"
    section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Static Review "
        "Failed Attempt"
    )
    next_section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Static Review "
        "Authorized Rerun"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_e870358da5_20260703T160217CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_actual_preflight_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST/preflight/runtime_promotion_evidence_package_preflight.json",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_camp_head=e870358da583e851b6ef3dd8033242165681c2a9",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_camp_origin_main=e870358da583e851b6ef3dd8033242165681c2a9",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_exit=1",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rejected",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_passed=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failure_class=source_preflight_sha256s_mismatch",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failure_attribution=preflight_artifact_path_mismatch_json_md_under_preflight_subdir",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_representative_failed_checks=runtime_promotion_evidence_package_preflight_json_exists,runtime_promotion_evidence_package_preflight_md_exists,source_preflight_sha256s_json_hash,source_preflight_schema,artifact_manifest_names",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_local_harness_passed=5",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_autodl_pytest_passed=5",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_report_json_sha256=4c19c3162cb9488169e9b555a8095617ab6f4f4530f0e160066d1c77ef809458",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_report_md_sha256=d026bee419488f2fd80f9690cd648418609aa50063ad2595e0e1f00de641dfee",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_artifact_sha256s_sha256=0f3db6b1cf249e1537d60b49b365397903561d67f92ed3508a038ed9bd93a0b6",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rejected",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rerun_requires_user_decision",
        "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_failed=True",
        "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_rerun_requires_user_decision=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rerun_requires_user_decision",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_promotion_evidence_package_static_review_authorized_rerun_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Static Review "
        "Failed Attempt"
    )
    section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Static Review "
        "Authorized Rerun"
    )
    next_section_title = "## Default-Off Selector Runtime Promotion Evidence-Package Construction"

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert text.rfind(next_section_title) > text.rfind(section_title)

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failed_path_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_e870358da5_20260703T160217CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failed_rerun_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_rerun_177c297fee_20260703T163834CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_rerun_9c9dccdd4d_20260703T164818CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_corrected_preflight_json=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST/preflight/runtime_promotion_evidence_package_preflight.json",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_camp_head=9c9dccdd4d3e6583c6d9bf52945ae82ee5e12956",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_camp_origin_main=9c9dccdd4d3e6583c6d9bf52945ae82ee5e12956",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_passed",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_passed=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_check_count=163",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failed_check_count=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_only",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_evidence_package_construction_authorized=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_local_direct_harness_passed=45",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_autodl_pytest_passed=45",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_report_json_sha256=614b7082ae51a60cf9288c70826530b8212d7d0059d86bf7c1bc2baf7f6ec445",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_report_md_sha256=a358466d90452873176e38205decab283f302e2b058c468be658cde469c6425d",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_report_sha256s_sha256=763fade5a5e0aad6b99d0326193009b83d23dade6208c73f2af9c316d0a620bd",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_artifact_sha256s_sha256=295d90d7ec777053d1fa64da91385e106675e8415d02f6cd6fb0aa012775f92f",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_heads_sha256=4676e2954767a56981cd0cdc4a57ec35492b09d07df72bb51f6ddde10cbe98a3",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_command_sha256=10a4a35d6e857002b230262d4e3a342bad0aba895fac8913a6ccbc632621d1fe",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_stdout_sha256=e07d0dd22070cd61ec652950b9dc8cfe450552ce3a20af5f65fb38464659aef5",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failed_rerun_exit=1",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failed_rerun_failure_class=v14_eof_contract_mismatch",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_static_review_failed_rerun_failed_checks=audit_latest_boundary_matches_static_review_gate,current_status_boundary_matches_static_review_gate,audit_records_preflight_ready,audit_authorizes_static_review",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_only",
        "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_passed=True",
        "default_off_shadow_selector_runtime_promotion_evidence_package_construction_authorized=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_only",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_promotion_evidence_package_construction_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Static Review "
        "Authorized Rerun"
    )
    section_title = "## Default-Off Selector Runtime Promotion Evidence-Package Construction"
    next_section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Construction "
        "Static Review"
    )
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > text.rfind(previous_section_title)
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_69a3ff3a04_20260703T170856CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_rerun_9c9dccdd4d_20260703T164818CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_camp_head=69a3ff3a04a7bf1f26d47687a4b7ec26209e107c",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_camp_origin_main=69a3ff3a04a7bf1f26d47687a4b7ec26209e107c",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_constructed",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_passed=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_check_count=95",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_failed_check_count=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_package_entry_count=15",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_static_review_only",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_authorized=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_local_direct_harness_passed=51",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_autodl_pytest_passed=51",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_report_json_sha256=dd5813ce4af9b0235648eae3b78cabec953e512b51d20fb153a6d9027e9b5d55",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_report_md_sha256=39bd274bb3abcd66799304134273fcf58b9d88dbc0316a3e121d15b20be2e126",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_sha256s_sha256=689d1ba062f55186c97747d2f18908f383e5300c60a5a277047c9caeafa777ac",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_evidence_package_sha256s_sha256=ed633d45bcefe76b15993556da52d9901cebd3ae5f16a0605ff6e2b16d7fc828",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_evidence_manifest_sha256=b214191018907aa29b8f522e63b448ee661b55a7683877a329e85d1cd6597929",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_heads_sha256=b8984ccebd4f6a35c4a7ed696c6020e5f03900ed7cdadef60e2b2dab7791001a",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_command_sha256=d33967a08099beb3ab5f60588286b41fa164cc8ef30f3246abdb9d34e613cf37",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_stdout_sha256=f5ccda4817abac77bcf03a40c745ded730d27d52225cbd53eabecfe8b8b734b5",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_constructed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_static_review_only",
        "default_off_shadow_selector_runtime_promotion_evidence_package_constructed=True",
        "default_off_shadow_selector_runtime_promotion_evidence_package_construction_static_review_authorized=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_static_review_only",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_promotion_evidence_package_construction_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Default-Off Selector Runtime Promotion Evidence-Package Construction"
    section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Construction "
        "Static Review"
    )
    next_section_title = (
        "## Default-Off Selector Runtime Promotion Decision From Evidence "
        "Package Plan"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_static_review_d411ca5dc0_20260703T173614CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_source_construction_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_69a3ff3a04_20260703T170856CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_camp_head=d411ca5dc02ae29d20c9f4a5d1bbf942cf7427e9",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_camp_origin_main=d411ca5dc02ae29d20c9f4a5d1bbf942cf7427e9",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_static_review_passed",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_passed=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_check_count=244",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_from_evidence_package_only",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_promotion_decision_planning_authorized=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_local_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_local_pytest_passed=51",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_autodl_pytest_passed=51",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_report_json_sha256=57a52859e676041e47a46eec24638befff57fb48c093d1b7e978c7e068488c2b",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_report_md_sha256=99204c27b427c230bf64fca8b00b6f800f6a30c75dfb46417b21e6aadb221c21",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_report_sha256s_sha256=192558cb21b549ce944a9271163cdacba7c753110668dc845f03631faac86678",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_artifact_sha256s_sha256=8888a9b4a040cb664fe5bd7d5d660734f5b5e4c888f4342f9b1e4c7cffeb1e36",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_heads_sha256=da2e0a2864832e2f3ad44d5a967fbeca4f99981499b0babea060cc68305ddc67",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_command_sha256=9ba1a4dea162472da8c37a176a041d0980fff893d6fb15bf122b938640769da1",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_stdout_sha256=9cec345c5d3a67455f028697e909ff344860eafb7135357898e7644e317e4ba6",
        "v14_public_simulator_default_off_selector_runtime_promotion_evidence_package_construction_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_from_evidence_package_only",
        "default_off_shadow_selector_runtime_promotion_evidence_package_construction_static_review_passed=True",
        "default_off_shadow_selector_runtime_promotion_decision_plan_from_evidence_package_authorized=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_from_evidence_package_only",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Default-Off Selector Runtime Promotion Evidence-Package Construction "
        "Static Review"
    )
    section_title = (
        "## Default-Off Selector Runtime Promotion Decision From Evidence "
        "Package Plan"
    )
    next_section_title = "## Default-Off Selector Runtime No-Promotion Closeout Record"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_decision_from_evidence_package_plan_592d57e223_20260703T174714CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_source_construction_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_static_review_d411ca5dc0_20260703T173614CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_source_construction_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_69a3ff3a04_20260703T170856CST",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_camp_head=592d57e2232b598597e686b576190ce155845376",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_camp_origin_main=592d57e2232b598597e686b576190ce155845376",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_from_evidence_package_ready",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_passed=True",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_check_count=131",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_recommendation=do_not_promote_from_current_evidence_package_alone",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_only",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_local_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_local_pytest_passed=52",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_autodl_pytest_passed=52",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_report_json_sha256=dd3fd82b62243cb7860329337e5e87da003988109d9c8489f24d0a5c66e52f9a",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_report_md_sha256=3c8d611c37afb735f19f2580cf9b388769c976da9daa7c340cc7833de40035cf",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_report_sha256s_sha256=51e8dc4da0434f3627d63a2cbf5a9ae78e7edeeafcd44c002dfa5d3f36f236a5",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_artifact_sha256s_sha256=eb9cbe1782a771879ae2e6b2c649ce547a3acfe4b27c7583a3a176c35440c584",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_heads_sha256=2470b293fb1b71b72e856746c63ed6a4cc8ce8df11225d948544d96620069621",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_command_sha256=703ec706355c185cdc1e0a6248f0ae64ebb03e17e3891b645a2313bb516fc3df",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_stdout_sha256=d82a49f0be40f6ce5ab6a11143f50abd9b0f45a913f3d01bb9d6af8555ecaddb",
        "v14_public_simulator_default_off_selector_runtime_promotion_decision_from_evidence_package_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_from_evidence_package_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_only",
        "default_off_shadow_selector_runtime_promotion_decision_from_evidence_package_plan_ready=True",
        "default_off_shadow_selector_runtime_promotion_from_evidence_package_recommended=False",
        "default_off_shadow_selector_runtime_promotion_no_promotion_closeout_authorized=True",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_only",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_no_promotion_closeout_record_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Default-Off Selector Runtime Promotion Decision From Evidence "
        "Package Plan"
    )
    section_title = "## Default-Off Selector Runtime No-Promotion Closeout Record"
    next_section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review Failed "
        "Attempt"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_record_4e16075a8b_20260703T180106CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_decision_from_evidence_package_plan_592d57e223_20260703T174714CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_camp_head=4e16075a8b21189660f2abe94648e88040510945",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_camp_origin_main=4e16075a8b21189660f2abe94648e88040510945",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_schema_version=dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_decision_no_promotion_closeout_record_v1",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_recorded",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_passed=True",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_failed_checks=[]",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_check_count=65",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_failed_check_count=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_recommendation=do_not_promote_from_current_evidence_package_alone",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_only",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_only",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_ready=True",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_recorded=True",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_review_authorized=True",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_promotion_recommended=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_selector_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_atom_promotion_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_deployment_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_deployable_checkpoint_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_safety_benefit_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_camp_over_dp_top1_claim_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_training_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_training_execution_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_replay_execution_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_candidate_generation_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_dp_modification_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_online_selector_change_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_executed_trajectory_change_authorized=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_training_executed_by_this_gate=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_replay_executed_by_this_gate=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_candidate_generation_executed_by_this_gate=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_dp_modified_by_this_gate=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_promotion_executed_by_this_gate=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_deployment_executed_by_this_gate=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_score_expression=score_k(w)=a_k^T w",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_source_plan_report_json_sha256=dd3fd82b62243cb7860329337e5e87da003988109d9c8489f24d0a5c66e52f9a",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_source_plan_report_md_sha256=3c8d611c37afb735f19f2580cf9b388769c976da9daa7c340cc7833de40035cf",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_source_plan_sha256s_sha256=51e8dc4da0434f3627d63a2cbf5a9ae78e7edeeafcd44c002dfa5d3f36f236a5",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_source_current_status_md_sha256=7ab36e0d13e8f685ed5a58440e3c720015c1d11bf27e89c92897816a06dfebe2",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_source_v14_audit_md_sha256=a07e3b8e415475bee2bf147f48480d1f04489e5da1f3a3b9230c1cb26ed1e7d5",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_local_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_local_pytest_passed=52",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_local_git_diff_check_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_autodl_pytest_passed=52",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_report_json_sha256=47d70a2a423a1b4fda6f6726261ca9495de1b448e7cad30056e512d4abb24876",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_report_md_sha256=e10a7268538aebef31dd7d4d0310a6b51b137dbc80fdd4e28b8f934d2970e881",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_report_sha256s_sha256=34a95940bf3c9b97a5e5194e0a48c7cc45778531e4d3bc195565e4ed52950c87",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_artifact_sha256s_sha256=b01d0a7eafc89691c7d3a150b6eba84bb967f352defd4e45a799da040a322bd4",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_heads_sha256=2b4febb0624b5a9bc705eba35abd546581ec711146f28dfaede2aeb6a6d99094",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_command_sha256=f1378a7552cd819face0cc3ead16bc1f23586b039f09c600dd5e08867a9a0010",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_stdout_sha256=8f22ec8c44e18b2891253de3adacc35bfe1797c9eff1aaa20782ce9c30151e75",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_record_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_recorded",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_only",
        "default_off_shadow_selector_runtime_no_promotion_closeout_recorded=True",
        "default_off_shadow_selector_runtime_no_promotion_closeout_review_authorized=True",
        "default_off_shadow_selector_runtime_promotion_from_evidence_package_recommended=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_only",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_no_promotion_closeout_review_failed_attempt_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Default-Off Selector Runtime No-Promotion Closeout Record"
    section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review Failed "
        "Attempt"
    )
    next_section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review Rerun "
        "Failed Attempt"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_1f00a091f9_20260703T182026CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_source_record_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_record_4e16075a8b_20260703T180106CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_camp_head=1f00a091f9615de3272b460060a307ba6337c486",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_camp_origin_main=1f00a091f9615de3272b460060a307ba6337c486",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_exit=1",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_rejected",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_passed=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_failure_class=script_import_path_missing",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_failure_attribution=ModuleNotFoundError_No_module_named_scripts",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_report_json_present=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_report_md_present=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_report_sha256s_present=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_local_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_local_pytest_passed=54",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_local_git_diff_check_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_autodl_pytest_passed=54",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_autodl_git_diff_check_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_heads_sha256=5554b6458c6842f559b88cf33b4b715dc06bade1ae98aeae227d3118a0807333",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_command_sha256=6cdacb4cc8d4a335ae12a15b4ee14e8fc04705e198ef09cd4e1722d9dcf399ca",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_stdout_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_stderr_sha256=5648fa205f1b101852f5e22c21d3ef14b7b462e8dbe173fbbfe8daa5b1dcb742",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_run_exit_sha256=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_artifact_sha256s_sha256=9856d3fc226bc07066593106996f4bdd8266b1e5ffadfd54466e82feec9eb75f",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_rejected",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_rerun_requires_user_decision",
        "default_off_shadow_selector_runtime_no_promotion_closeout_review_passed=False",
        "default_off_shadow_selector_runtime_no_promotion_closeout_review_rerun_requires_user_decision=True",
        "default_off_shadow_selector_runtime_promotion_from_evidence_package_recommended=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_rerun_requires_user_decision",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_no_promotion_closeout_review_rerun_failed_attempt_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review Failed "
        "Attempt"
    )
    section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review Rerun "
        "Failed Attempt"
    )
    next_section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review "
        "Contract-Update Rerun"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_rerun_0c629925d2_20260703T212231CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_source_record_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_record_4e16075a8b_20260703T180106CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_previous_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_1f00a091f9_20260703T182026CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_camp_head=0c629925d2957fac3e851bc3a689cfa29c2de467",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_camp_origin_main=0c629925d2957fac3e851bc3a689cfa29c2de467",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_exit=1",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_rejected",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_passed=False",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_failure_class=v14_eof_contract_mismatch",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_failed_checks=artifact_sha256s_record_sha256s,audit_latest_status,audit_latest_next_work,status_doc_latest_status,status_doc_latest_next_work",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_check_count=103",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_failed_check_count=5",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_source_record_sha256s_sha256=34a95940bf3c9b97a5e5194e0a48c7cc45778531e4d3bc195565e4ed52950c87",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_local_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_local_pytest_passed=50",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_local_git_diff_check_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_autodl_pytest_passed=50",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_autodl_git_diff_check_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_report_json_sha256=f9aeef3fde5f656288b3f4f2e01518ac2c1eb27d6dee567935e9fdee828b7899",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_report_md_sha256=48c5cf631a27bb0ebf2e20b175fd3c827b31d0b74c866bb4742489495182c9a7",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_report_sha256s_sha256=30825711ef63e6a71cae6fadf8ecab05b163e184e653ebf913da4868674ea1f7",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_heads_sha256=75c18e72c72ca283be547ec8ab6fec7e4b879991a2e383e7e3f8620d9896e8e9",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_command_sha256=9a13cea75e4f0c8a38c1a064fe862f1da5f6c0ab9819f9dd1536039172320879",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_stdout_sha256=26ea1963bc90f80e62e3656eadbcd53de992684dc0cb362ab8f96f8ce870305c",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_run_exit_sha256=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_rerun_artifact_sha256s_sha256=bc77f6128e209c33b9a687dd3644e080f0e15f533cfb08fc8ded0c7f951a8bf0",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_rejected",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_contract_update_rerun_requires_user_decision",
        "default_off_shadow_selector_runtime_no_promotion_closeout_review_passed=False",
        "default_off_shadow_selector_runtime_no_promotion_closeout_review_contract_update_rerun_requires_user_decision=True",
        "default_off_shadow_selector_runtime_promotion_from_evidence_package_recommended=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_contract_update_rerun_requires_user_decision",
    ]:
        assert needle in text


def test_v14_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review Rerun "
        "Failed Attempt"
    )
    section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review "
        "Contract-Update Rerun"
    )
    next_section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Failed Attempt"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index
    assert "\n## " not in text[section_index + len(section_title) : next_section_index]

    for needle in [
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_contract_update_rerun_74d34a7949_20260703T221152CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_source_record_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_record_4e16075a8b_20260703T180106CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_previous_import_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_1f00a091f9_20260703T182026CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_previous_contract_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_rerun_0c629925d2_20260703T212231CST",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_camp_head=74d34a7949c115ee61294c97aae9c81a111465cb",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_camp_origin_main=74d34a7949c115ee61294c97aae9c81a111465cb",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_passed",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_passed=True",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_failure_class=None",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_contract_update_rerun_requires_user_decision",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_closed_no_further_action_without_new_eof_authorization",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_check_count=104",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_failed_check_count=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_source_record_sha256s_sha256=34a95940bf3c9b97a5e5194e0a48c7cc45778531e4d3bc195565e4ed52950c87",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_source_artifact_sha256s_sha256=b01d0a7eafc89691c7d3a150b6eba84bb967f352defd4e45a799da040a322bd4",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_local_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_local_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_local_pytest_passed=52",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_autodl_py_compile_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_autodl_pytest_exit=0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_autodl_pytest_passed=52",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_report_json_sha256=c30f59e5dd44bab5ecb0770df763ae45aed85b035d5c69b066d73a592ba28ced",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_report_md_sha256=88731c96cabf5618a6d53063aaf21c8aebafa6d37b58ec847bf66c42a5f50837",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_report_sha256s_sha256=61cc00a8edfc72f07502c3834ea0d7743a73f904a4b245612d48f834ba292ca0",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_heads_sha256=09d8b684d23346c59945792bddb2c7d83553a283d0b07afc41fe8721182520c8",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_command_sha256=df1d4ec10c293527fb89f8f63a108b6c6ae60d266cc25b08b778c75732f65bdd",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_stdout_sha256=ff4a5b801cb5d7dc0412f8d7a9d19a7446aa5b93470cd46a2f878df971adffc4",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_default_off_selector_runtime_no_promotion_closeout_review_contract_update_rerun_artifact_sha256s_sha256=732489dbc7d0be079506b42a819eba4efdf302e162fefd7fc219d46d2a2c0a9a",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_closed_no_further_action_without_new_eof_authorization",
        "default_off_shadow_selector_runtime_no_promotion_closeout_review_passed=True",
        "default_off_shadow_selector_runtime_no_promotion_closeout_complete=True",
        "future_promotion_requires_new_eof_and_explicit_authorization=True",
        "default_off_shadow_selector_runtime_promotion_from_evidence_package_recommended=False",
        "default_off_shadow_selector_runtime_execution_authorized=False",
        "candidate_generation_by_camp_authorized_by_current_boundary=False",
        "trajectory_modification_by_camp_authorized_by_current_boundary=False",
        "dp_modification_authorized_by_current_boundary=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_closed_no_further_action_without_new_eof_authorization",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_gap_analysis_failed_attempt_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Default-Off Selector Runtime No-Promotion Closeout Review "
        "Contract-Update Rerun"
    )
    section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Failed Attempt"
    next_section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Contract-Fix Rerun"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index
    assert "\n## " not in text[section_index + len(section_title) : next_section_index]

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_plan_068223a31b_20260703T224120CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_source_evidence_package_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_69a3ff3a04_20260703T170856CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_source_result_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_source_delta_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_vs_top1_delta_review_04f4b68421_20260703T103434CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_source_promotion_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_decision_from_evidence_package_plan_592d57e223_20260703T174714CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_source_closeout_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_contract_update_rerun_74d34a7949_20260703T221152CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_camp_head=068223a31be5b1e659a3f507ea31a4f7f017c090",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_camp_origin_main=068223a31be5b1e659a3f507ea31a4f7f017c090",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_exit=1",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_plan_rejected",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_passed=False",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_failure_class=post_closeout_promotion_readiness_gap_analysis_failure",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_failure_attribution=source_review_heads_key_case_contract_mismatch",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_failed_checks=result_review_heads_dp_fixed,delta_review_heads_dp_fixed",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_check_count=400",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_failed_check_count=2",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_local_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_local_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_local_pytest_passed=52",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_autodl_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_autodl_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_autodl_pytest_passed=52",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_report_json_sha256=2866457c1bbb63baee3a4217f856075b4063feedaafd0f68f276d1f6f09bcf7a",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_report_md_sha256=f37fc2b6e165a592b608e33170466a96bf9e0871c3cd0e2a97dfd8c39b7ddd97",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_report_sha256s_sha256=7376f2137a1b95af018a277e2fa8dd54874883ae6c87ca6881a7772069a565d5",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_heads_sha256=f927e38bb4171d17ba673440a8ef82f94f8562c83ddee4615d3f467dc0461605",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_command_sha256=6a316ea0edf18f1c2a4abf2c441909c3eab184f3088b23c1cac59b1f6f58bd7f",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_stdout_sha256=0dd76764c11da5340bd02f10f5f0e296e2bb3edb3f329c992bca42b71cac126f",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_run_exit_sha256=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_artifact_sha256s_sha256=595114d8c63d4d0913dda9b095cb13fada4aa1e855ac490dec8588f739e307db",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_plan_rejected",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_requires_user_decision",
        "post_closeout_promotion_readiness_gap_analysis_passed=False",
        "post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_requires_user_decision=True",
        "default_off_shadow_selector_runtime_no_promotion_closeout_complete=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_requires_user_decision",
    ]:
        assert needle in text

def test_v14_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Failed Attempt"
    section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Contract-Fix Rerun"
    next_section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_cd54951760_20260703T233911CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_previous_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_plan_068223a31b_20260703T224120CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_source_evidence_package_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_69a3ff3a04_20260703T170856CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_source_result_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_source_delta_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_vs_top1_delta_review_04f4b68421_20260703T103434CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_source_promotion_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_decision_from_evidence_package_plan_592d57e223_20260703T174714CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_source_closeout_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_contract_update_rerun_74d34a7949_20260703T221152CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_camp_head=cd54951760bc94b4ecaf16eeff316176f7c46556",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_camp_origin_main=cd54951760bc94b4ecaf16eeff316176f7c46556",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_recommendation=do_not_promote_or_deploy_from_current_evidence_package",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_immediate_action=static_review_this_gap_analysis_only",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_check_count=404",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_local_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_local_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_local_pytest_passed=55",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_autodl_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_autodl_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_autodl_pytest_passed=55",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_report_json_sha256=9851ee0e59b497e2091d4dd24e48e126f15cef8b0a7f04b2ec9da8cde433a558",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_report_md_sha256=cf19638b77fa520630b8468560111eda51def4f36a7af24c00b17f20d35fa604",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_report_sha256s_sha256=21ed74e7bfed83002712e9d22adfd83d4235217293583a534077afae7fe10e5f",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_heads_sha256=97172fbf9ee02030f2cde9f533aa4ddc8627c0d0f5e6eb73035614218a747712",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_command_sha256=82bf32a04c4c32811009a6ea0dc669de7786c8e1fdd541e4baf470aee0b094f4",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_stdout_sha256=2b6f7913c3ea53385e02f7123cca48ad512b6e946d59ac4f51d6a969cff10585",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_artifact_sha256s_sha256=4127f87d685aea571d056310e3018896d950eaba9d747f93a69e215e1aeda641",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_static_review_only",
        "post_closeout_promotion_readiness_gap_analysis_passed=True",
        "post_closeout_promotion_readiness_gap_analysis_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_static_review_only",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_gap_analysis_static_review_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Contract-Fix Rerun"
    section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_f0836545b4_20260703T235643CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_source_gap_analysis_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_cd54951760_20260703T233911CST",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_camp_head=f0836545b481e627a801aeda8d8ab020df2eb161",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_camp_origin_main=f0836545b481e627a801aeda8d8ab020df2eb161",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_recommendation=keep_no_promotion_and_plan_readiness_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_immediate_action=plan_promotion_readiness_evaluation_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_check_count=181",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_gap_categories=active_selector_promotion,deployment_fail_closed,safety_claim,camp_over_dp_top1_claim,evaluation_coverage,governance_authorization",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_readiness_surfaces=promotion_readiness,deployment_readiness,safety_or_superiority_claim",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_local_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_local_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_local_pytest_passed=63",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_autodl_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_autodl_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_autodl_pytest_passed=63",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_report_json_sha256=1ebfcae38f4a963324b4d45313178e66519bfa875750b3b0bd4815888719e3aa",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_report_md_sha256=378190e3e0d5a9ef3572cfca0ff1ec69f5516011f74a39b38ecc7d0020ea3f52",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_report_sha256s_sha256=52005bae8778c90db4621a06a1308bd53eec65810c8ec6a4667216c8bc2a1c98",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_heads_sha256=ca633c1299a71c60ef58e19f9f5421f5c129b9007792a8279b407e272178fdc0",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_command_sha256=27a5001e344e5eedfb6e9df25467a1b9677a33505c63397227d9a605e736afa7",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_stdout_sha256=06008d6d72c64358006c2bf275b644eb60a9ac5cd5b50506b9e0e3152e3a032d",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_artifact_sha256s_sha256=b394ee54aa70ee388d73c7d22e09530a9b8013e4ee6fe1598a9dc0c382753d62",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_only",
        "post_closeout_promotion_readiness_gap_analysis_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_preflight_plan_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_only",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_evaluation_preflight_plan_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Gap Analysis Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_763a0f5612_20260704T000918CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_source_gap_analysis_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_f0836545b4_20260703T235643CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_source_gap_analysis_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_cd54951760_20260703T233911CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_camp_head=763a0f56124c16c3b295ce78a0ae7832508ff377",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_camp_origin_main=763a0f56124c16c3b295ce78a0ae7832508ff377",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_recommendation=static_review_this_preflight_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_immediate_action=static_review_promotion_readiness_evaluation_preflight_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_check_count=171",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_preflight_plan_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_no_go_condition_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_local_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_local_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_local_pytest_passed=71",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_autodl_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_autodl_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_autodl_pytest_passed=71",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_report_json_sha256=607ab3a34cd9e685422ede50726c6f218a440e6715be2f34b442ed5cb86b2c8a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_report_md_sha256=a6752413e9cd72010123405a8c23f882254f250cb429129cd5e49d6c029cf4e2",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_report_sha256s_sha256=1e75bf316eda161bfafaf52ab85fba5962e447d9115300f78c29f84c5a7449ea",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_heads_sha256=3d24680860848a7e0511c2e084ba0ea9a9b39100186ea06728a1c1bef28acd2a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_command_sha256=df59b4db32ab076ffc6d664060903f6d5af22aa1de34ceb67dbd8a3f0ed7c3f4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_stdout_sha256=2d58f3ab70fbbdb370927652e0b906d06d5bd227a7b0e1d70b00e30ae39b4829",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_artifact_sha256s_sha256=c3a0a5409faf534d9ca87d84e5c6040c7e8e3a974d5b78bd065a58aa1fac560a",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_only",
        "post_closeout_promotion_readiness_evaluation_preflight_plan_ready=True",
        "post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_only",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Plan"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_28958edc70_20260704T001942CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_source_preflight_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_763a0f5612_20260704T000918CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_camp_head=28958edc70bc645c9e8b1d7f6ab051ea9f35a063",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_camp_origin_main=28958edc70bc645c9e8b1d7f6ab051ea9f35a063",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_recommendation=run_promotion_readiness_evaluation_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_immediate_action=execute_read_only_promotion_readiness_evaluation_preflight",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_check_count=137",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_local_pytest_passed=78",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_autodl_pytest_passed=78",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_report_json_sha256=a50fcc6a9834d17df02686f4e7b9d7b95726cad61e48afd06c39268ab7fc96f9",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_report_md_sha256=3010277ab0c747826547803229c8bc7bcd9311f84a18ba6925b41c057903cb3c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_report_sha256s_sha256=0cb14b8ad0f12b4e854ec2d157d0b2c24be75a284706f6f89086a5fbc1c9f3d6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_heads_sha256=57e4850a7e6d5179f5130100db4fdf2e1415b92b36ae8f1f68be249eec00e866",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_command_sha256=0ee47f092b6c7e2d821bff84744ab0fc4cc768fa9feee63d42cf80c738497915",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_stdout_sha256=d50afb2e8a822e0e1c080fe14a78d9b791bf7804d700974b87eda89f32994043",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_artifact_sha256s_sha256=82702c311a9dda374ceaa1840544eecaa544b108c9b487827787ae303c7eea5d",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_only",
        "post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_preflight_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_preflight_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_c65da3c60f_20260704T003848CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_source_preflight_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_28958edc70_20260704T001942CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_source_preflight_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_763a0f5612_20260704T000918CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_camp_head=c65da3c60f1415cd8f2599e1aa6be5384e43ed30",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_camp_origin_main=c65da3c60f1415cd8f2599e1aa6be5384e43ed30",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_recommendation=static_review_this_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_immediate_action=static_review_promotion_readiness_evaluation_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_check_count=179",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_evaluation_preflight_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_no_go_status_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_future_review_requirement_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_local_pytest_passed=85",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_autodl_pytest_passed=85",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_report_json_sha256=2c0a7bbc6a9e5574ad57d6bf5626070d3db755480a2b0e87a0de24d1dd56039d",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_report_md_sha256=0d4e537a1d3ce672cb6a5dbc96c688ba5a7c85e1f9809853409eefb4d2f9ebb9",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_report_sha256s_sha256=95b85d670956cffee1eb11159388a7d56a791f4a60415961ce677e7f62388b92",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_heads_sha256=d95fad0be9678b1c38135eadc47aa4df7d906a72c3dd6f2f9ef7022f91dc417c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_command_sha256=0dfe9dd08abbb21c8a90283808e83d0a449aefe558bf689cd3e1c998786e8a40",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_stdout_sha256=193366892527558274d8c88daf46f4109e61db168c9f4071c6d2eb3479eb077f",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_artifact_sha256s_sha256=288c67da6e66b3844033be27f56a478a08c813ad82f7da8482456a8f741a3bbd",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_static_review_only",
        "post_closeout_promotion_readiness_evaluation_preflight_ready=True",
        "post_closeout_promotion_readiness_evaluation_preflight_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_preflight_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_9fd860b1d1_20260704T005150CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_c65da3c60f_20260704T003848CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_camp_head=9fd860b1d102691ef251d71f0270750b640d270c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_camp_origin_main=9fd860b1d102691ef251d71f0270750b640d270c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_recommendation=plan_promotion_readiness_evaluation_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_immediate_action=plan_read_only_promotion_readiness_evaluation_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_source_preflight_check_count=179",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_source_preflight_no_go_status_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_local_pytest_passed=92",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_autodl_pytest_passed=92",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_report_json_sha256=942e486c5d4d1fdf4e0cc2827fb11834d7a2f42fe7e6c5bef465024581168cbc",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_report_md_sha256=c5205b118e56d3950691c8479b92a309943afa53e1099c744cd2af687272f414",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_report_sha256s_sha256=3311e251cb1131556a7cb0784c6472264d33e8d9f0d0e813e59b3137ed953648",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_heads_sha256=6cd225697f3c4909c2e817fc948b325b8c92f2ee06c18b052947245023348478",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_command_sha256=b3ca062442b5ca6438c8ea2b9c284fdca02685bc0d32fe7fc6f4a83d92c2d573",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_stdout_sha256=c6ef0606fdb3ae9c9614cfa80efa644ca3548b0da4644faccfb422dc08aafab3",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_artifact_sha256s_sha256=6643ff956ac432b2af039c89a4c9626f310b921a4acfc100fafc18ff479c096e",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_only",
        "post_closeout_promotion_readiness_evaluation_preflight_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_plan_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_only",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_evaluation_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Preflight Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index
    assert "\n## " not in text[section_index + len(section_title) : next_section_index]

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_3da03ab5d3_20260704T011126CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_source_preflight_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_9fd860b1d1_20260704T005150CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_c65da3c60f_20260704T003848CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_camp_head=3da03ab5d320cac5d349f23e67f95bef29462947",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_camp_origin_main=3da03ab5d320cac5d349f23e67f95bef29462947",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_recommendation=static_review_this_evaluation_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_immediate_action=static_review_promotion_readiness_evaluation_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_check_count=224",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_decision_surface_count=3",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_evidence_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_no_go_condition_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_future_review_requirement_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_source_static_review_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_source_preflight_check_count=179",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_source_preflight_no_go_status_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_heads_case_insensitive_dp_key_contract=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_local_pytest_passed=101",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_autodl_pytest_passed=101",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_report_json_sha256=1263efc7c163eda2080b2332be267a449a9d34546e2dd583ba29aeca2784aa39",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_report_md_sha256=d7cf65a34ec56512c213db6efc49fc385886eeccf386118fd3bdf5108309c4f7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_report_sha256s_sha256=4c0930f856d20cec2e59456ae6415f746d3a0178090b5cba9670bfb0b0bcfa58",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_heads_sha256=1cb0a1bed1fbfef78f2b1fd9273067a73ccdea34368ff2ffc6208264c30a4c8b",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_command_sha256=567c2e6bdb3414c94654a0b7ed22b88c6f4e8a9633153ca1eb43d6f3d0f83e48",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_stdout_sha256=e84dc18f260c477237d039de9aa971940bc521b8c425962b61da7b3aae4cacb5",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_artifact_sha256s_sha256=6f9f715fb6c4fe7702c2d2f349d3fcacaa7f3610c681fff78846969f6155cfec",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_static_review_only",
        "post_closeout_promotion_readiness_evaluation_plan_ready=True",
        "post_closeout_promotion_readiness_evaluation_plan_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_plan_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Plan"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index
    assert "\n## " not in text[section_index + len(section_title) : next_section_index]

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_494072d472_20260704T012428CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_3da03ab5d3_20260704T011126CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_camp_head=494072d472db17ceef3c8e97e1e76981f6b39f0e",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_camp_origin_main=494072d472db17ceef3c8e97e1e76981f6b39f0e",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_recommendation=plan_follow_on_evaluation_runbook_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_immediate_action=plan_read_only_evaluation_runbook_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_check_count=141",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_failed_checks=",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_source_plan_check_count=224",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_source_decision_surface_count=3",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_source_evidence_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_local_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_local_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_local_pytest_passed=109",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_local_git_diff_check_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_autodl_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_autodl_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_autodl_pytest_passed=109",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_autodl_git_diff_check_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_report_json_sha256=dc9cf9a0f5773033c972d29b5442166ddfa35a27e224ed9de1f79a48e8c1a55c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_report_md_sha256=e8c072667b16c1433fbfd6877c462c88fa5c8af73f357a31adb2567d51e4665d",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_report_sha256s_sha256=245db13d1e0c09445613c168c211a34d83cf98138de313256c8c5f5d9cfdf02f",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_heads_sha256=cc6f714823aa72cb860196a18b7e11545103dfe806d2c8ff562e3cdb563cf436",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_command_sha256=befb8cb4edd290ad2c46ea6adcfd2b404d43c2675ba8c4c1e4e7c96b7028b6ca",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_stdout_sha256=d752569924b84b4a710e9595bb56662b564e436dd7d5b0bc394d36a2d256dfd2",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_artifact_sha256s_sha256=0f058dcef5f5de3501e6259c258031821a9902f695271335a58f1175a3b1271e",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_only",
        "post_closeout_promotion_readiness_evaluation_plan_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index
    assert "\n## " not in text[section_index + len(section_title) : next_section_index]

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_554c3244b1_20260704T014204CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_494072d472_20260704T012428CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_3da03ab5d3_20260704T011126CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_camp_head=554c3244b1592c3c08f9b76a00695283bb870738",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_camp_origin_main=554c3244b1592c3c08f9b76a00695283bb870738",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_recommendation=static_review_this_runbook_preflight_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_immediate_action=static_review_promotion_readiness_evaluation_runbook_preflight_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_check_count=223",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_failed_checks=",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_step_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_no_go_condition_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_forbidden_action_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_source_static_review_check_count=141",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_source_plan_check_count=224",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_source_decision_surface_count=3",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_source_evidence_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_local_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_local_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_local_pytest_passed=117",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_local_git_diff_check_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_autodl_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_autodl_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_autodl_pytest_passed=117",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_autodl_git_diff_check_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_report_json_sha256=ea29aeed0b76812a33cdc6449e293dc4b7872719319f47f9f6720b5d92f60b68",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_report_md_sha256=5a24aed0ea00f1f0edb75d72710ad089ce35fc22f0c4063d4c6cbb55afb7e32d",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_report_sha256s_sha256=98ffcd91449cae3f525445fb288e053786ca80c96f83ee056aa1a962bdd1c623",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_heads_sha256=577a4799d03227a66bac6aeeb6378d91a1c0ce41f82ac8830f6a9a989a3080ea",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_command_sha256=c5ab36ea301afb56001c10663722504bfd9021db29597d50a1994e855381fd78",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_stdout_sha256=394a6573453bb3f01564c45dec9e978d2e5d72276e2aaf7f045d52327314674a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_artifact_sha256s_sha256=580762b10d50735654d803e26ff54032a7ea6930928a6d182e257c1f96382607",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_only",
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_ready=True",
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Plan"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_41539b4bed_20260704T015353CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_554c3244b1_20260704T014204CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_camp_head=41539b4bed1f0e532a5147b61263f96a6a193bbe",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_camp_origin_main=41539b4bed1f0e532a5147b61263f96a6a193bbe",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_recommendation=run_read_only_evaluation_runbook_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_immediate_action=run_promotion_readiness_evaluation_runbook_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_failed_checks=",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_source_plan_check_count=223",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_source_runbook_preflight_step_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_source_no_go_condition_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_source_forbidden_action_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_local_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_local_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_local_pytest_passed=125",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_local_git_diff_check_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_autodl_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_autodl_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_autodl_pytest_passed=125",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_autodl_git_diff_check_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_report_json_sha256=c84e0e9a533cf4427908022c64a122561e2e9b45f1137c619992bf2716b58b9b",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_report_md_sha256=eac3bd0cefb2efdb24fae15bc3346bf831a3e543e35ac20718a01a881c69d18a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_report_sha256s_sha256=b555a7116895f43338b1814a0ed42f11350dfbbb13a3cee0af5b6c6c9d7f8e74",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_heads_sha256=a35c48205531898b938dcd5e73fe5ee5f55d1ae179b1863b5c83ef9aeabf93d8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_command_sha256=de0c174c2aefeee67d84a1b47647c32098a38808e19ea2baa1977cfdf3810eb4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_stdout_sha256=129d133213b0df2c16c44d59d6214267d25b64bb07dfc9b33197b204c63f5519",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_artifact_sha256s_sha256=046f6efbd5657c057ee3a29b25c97cc562a8e5c9225ca1d075423c71c6f434cf",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_only",
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_preflight_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_3062b4f4a5_20260704T020713CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_41539b4bed_20260704T015353CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_554c3244b1_20260704T014204CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_camp_head=3062b4f4a5f6d19ebb99f965467aa89f19933ba2",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_camp_origin_main=3062b4f4a5f6d19ebb99f965467aa89f19933ba2",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_recommendation=static_review_this_runbook_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_immediate_action=static_review_promotion_readiness_evaluation_runbook_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_check_count=218",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_failed_checks=",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_step_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_artifact_manifest_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_no_go_status_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_future_review_requirement_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_source_static_review_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_source_plan_check_count=223",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_source_runbook_preflight_step_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_source_no_go_condition_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_report_json_sha256=666137790e2e4fdd77d31004a732428c3f15e712c6e40815fbfddfff3f909243",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_report_md_sha256=1e41dc49c5d8c184d1716a0643505d701a61b82e589bb1c1faab3fe4d3b8a133",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_report_sha256s_sha256=0a41486d5b11806d0fbabd1d23e2e85ef5cd4403a4d24f455f63c5f516cd2c13",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_heads_sha256=4f6db5414ef11bfdeedbe9a3b8a6a13d3c14c9d53c3bc98f723f72d736ca5f86",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_command_sha256=5f64761020c19b9d1977b466a3952f81b8e30d66d9d6b6f37e6901ce80205e2f",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_stdout_sha256=52f443065424eb4dcb835f3218ae31b4d9e2eb6ce62b3e9cb6f12539af713b9b",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_artifact_sha256s_sha256=14a31db3b3cc8b30a5378004309927bb2d5443e74f1ed2709bc0ada1d65ff6c2",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_only",
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_ready=True",
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_c2443f45ef_20260704T022733CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_3062b4f4a5_20260704T020713CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_camp_head=c2443f45ef67e8477da9d932dcbbc07cdb2c34fd",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_camp_origin_main=c2443f45ef67e8477da9d932dcbbc07cdb2c34fd",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_recommendation=plan_read_only_promotion_readiness_evaluation_runbook_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_immediate_action=plan_promotion_readiness_evaluation_runbook_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_check_count=141",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_failed_checks=",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_source_preflight_check_count=218",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_source_runbook_preflight_step_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_source_artifact_manifest_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_source_no_go_status_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_source_future_review_requirement_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_local_py_compile_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_local_pytest_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_local_pytest_passed=143",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_autodl_pytest_passed=143",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_report_json_sha256=fdd1954bbff79b6dbe4c5793d0af912ab535936b1881d4ea96f4b9ce3f0827e9",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_report_md_sha256=c17af0f8bd0c8f5228ce1b1d72ad143545bb752ce517517f42d9afbdb757bea3",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_report_sha256s_sha256=0fa44b0bf9ffbcbab8714ee2dff2d3e08ce7af73b6e2f24d50f7d4519d638f78",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_heads_sha256=151b924760cfb3f28626b3a463e7fa8070fd6700fd3a98b62eac09e2b073b075",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_command_sha256=247a97e0d2179a8ce64096d2e807f505810cc1414ce504ca811779bdfcc926e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_stdout_sha256=85eb76b6c3e433d636d2b2017f22e04d49ad69fde409c0bd014741c99bb64813",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_artifact_sha256s_sha256=c68151f656e8f28eb9e9d56aa02fd425d509260ea8066f1389b776150edd1dc6",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_only",
        "post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_plan_authorized=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_c83a4bdc90_20260704T023923CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_c2443f45ef_20260704T022733CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_3062b4f4a5_20260704T020713CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_camp_head=c83a4bdc905de7df46edd5f718987753972bb535",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_camp_origin_main=c83a4bdc905de7df46edd5f718987753972bb535",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_recommendation=static_review_this_evaluation_runbook_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_immediate_action=static_review_promotion_readiness_evaluation_runbook_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_check_count=186",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_failed_checks=",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_step_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_artifact_count=9",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_metrics_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_decision_criteria_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_no_go_condition_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_forbidden_action_count=10",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_future_review_requirement_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_local_pytest_passed=152",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_autodl_pytest_passed=152",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_report_json_sha256=e1a189540c205022e723b333a76bb3337ed463da7258fa3f2c46c9d877c270c4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_report_md_sha256=2bb1646d0d57481298a331904414deb7715b873e89b17948e3a723aa9006a5dd",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_report_sha256s_sha256=2e70454965073e272c9ea1b626e0364e68d5c6eab4594df75142372dfba719d4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_heads_sha256=df3ec2e8ae66d639ab239bea6120b0420e245ced1ffec544b61322785607a1f1",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_command_sha256=6af2a48403212fa7286bf8c4f686360de302b197ea1f3c4deda21c22a63ea95c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_stdout_sha256=ebae24a54b94341f4b51ef52b17279514cd8716abe75e6e2e0d61c2da56c26e5",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_artifact_sha256s_sha256=659ea5e856c809a6342b9e91104105e9e52ab5baaf4bfb52529c3fc962e2e471",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_only",
        "post_closeout_promotion_readiness_evaluation_runbook_plan_ready=True",
        "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_authorized=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Plan"
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Plan Static Review"
    next_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Failed Attempt"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_dc6b804a9d_20260704T025255CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_c83a4bdc90_20260704T023923CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_camp_head=dc6b804a9d732f2ca29fd3a278a7ef22ecd0954c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_camp_origin_main=dc6b804a9d732f2ca29fd3a278a7ef22ecd0954c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_authorized_current_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_recommendation=preflight_read_only_promotion_readiness_evaluation_runbook_execution_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_immediate_action=preflight_promotion_readiness_evaluation_runbook_execution_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_check_count=145",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_failed_checks=",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_plan_check_count=186",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_runbook_step_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_artifact_count=9",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_metrics_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_decision_criteria_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_no_go_condition_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_forbidden_action_count=10",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_source_future_review_requirement_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_local_pytest_passed=160",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_autodl_pytest_passed=160",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_report_json_sha256=22a3d92d6c8d700d4d16b9743e446c618f025c41e7931d260a79627ab8696251",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_report_md_sha256=86faba07848e9cf1d6e08d32443d6a41c35345447e9ff9df204b28d4a191796f",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_report_sha256s_sha256=f503b8791abf940758b1b99b7a24f54ac96ffd6a1664fcbf56f4eb01bb5e8f72",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_heads_sha256=f87548b45935ac83bc43d160d22bc9238238319afdd9d10edc3879b6b655d088",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_command_sha256=5311ee0e4348d5ce732c35d047285de699f1cb54f079dfc66b7d18f9ddaccef6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_stdout_sha256=b02c37da6613f29dd8c848f336da6c18a2a7dc869e0c5419e209d76ea0330ba1",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_artifact_sha256s_sha256=0f6241357467e9a9d4ea5dfcff78f6945b096707ec3dcb326f8b7c2253901b06",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_only",
        "post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_authorized=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_attempt_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Plan Static Review"
    section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Failed Attempt"
    )
    next_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Authorized Rerun"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_e015b6b57b_20260704T030343CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_dc6b804a9d_20260704T025255CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_c83a4bdc90_20260704T023923CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_camp_head=e015b6b57be6d0dfffd0aa6b14546bd9c92e9e4f",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_exit=1",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_rejected",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_failure_class=source_artifact_sha256_mismatch",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_check_count=226",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_failed_check_count=2",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_failed_checks=static_review_artifact_review_sha256s_root_sha,source_static_review_analysis_evaluation_runbook_execution",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_local_pytest_passed=168",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_autodl_pytest_passed=168",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_report_json_sha256=41b8d4fee277c5192e2cd52c2792314d4a7f22b23591ab5ba4f4f5bb764939f8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_report_md_sha256=68d6a3adebb27709e34857a80e5786f30b04b2b16812ea3d9d39b9cb5032916a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_report_sha256s_sha256=94be3ee40e4c7ee81fb1107eb330f1ceb300618f4bbc6765c4b4301db489c1b9",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_heads_sha256=d03091c62c684339d1ef840f17f1f2e0f6450465b9dd66382b6d4a96f07eb0c4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_command_sha256=b3234a3ea65970b0c39d74141a732cdd92230404b3e95b9c7d65316f079fb076",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_stdout_sha256=c97c71c22f12bd548608782cea03e49ec766571b4c474657062bcc11c80221a3",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_run_exit_sha256=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_artifact_sha256s_sha256=d8ea62b8b628eee1f279c652233fa0c3c8fdf26e566872da73872357d9640508",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_rejected",
        "current_v14_next_scope=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_contract_fix_or_rerun",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_passed=False",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_authorized=False",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_contract_fix_or_rerun",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_authorized_rerun_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Failed Attempt"
    )
    section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Authorized Rerun"
    )
    next_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review Failed Attempt"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_12cd3dc982_20260704T104156CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_dc6b804a9d_20260704T025255CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_c83a4bdc90_20260704T023923CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_camp_head=12cd3dc982ef2099fb04aa2914cd459062955cdb",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_check_count=226",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_runbook_step_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_artifact_manifest_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_no_go_condition_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_future_review_requirement_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_local_pytest_passed=172",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_autodl_pytest_passed=172",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_report_json_sha256=f94c6edfeb909bebcc85cb5aea95b1c9d1cdd4fc3aaea414b8f9f9434a51238f",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_report_md_sha256=c652819e2b4738089c392cae2cda72dc18557b06b4481e162417f6d42c6f0c82",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_report_sha256s_sha256=ca5508d83187cdeaaa22794a69e960ce5c79cc08ba0cd1cfd4597be7e255b2a2",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_heads_sha256=cb605167cc10cf6e0a816f80d73cc6e6d07eb6d567c9bddfb8c8e6c7acbab19a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_command_sha256=0e871823a49ab2b04c58dc974eef5ae14bc8449982efc92a462f8eeb697e2de9",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_stdout_sha256=531dc5f2f3fef9507db5a8922cd14c093f02389a0c745a644f78bd247900709d",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_artifact_sha256s_sha256=9ff6d3c38c054e0eac9dced0ff5ce09f6facf27bf1cf4a9a01e9751ef99f7a3f",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_only",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_authorized=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_only",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_attempt_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Authorized Rerun"
    )
    section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review Failed Attempt"
    )
    next_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review Authorized Rerun"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_92fab53910_20260704T105546CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_12cd3dc982_20260704T104156CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_camp_head=92fab539101db586877d2685f1d99b758d24037c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_exit=1",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_rejected",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_failure_class=v14_eof_contract_mismatch",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_check_count=155",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_failed_check_count=2",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_failed_checks=source_preflight_analysis_evaluation_runbook_execution,audit_runbook_execution_preflight_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_source_preflight_check_count=226",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_source_preflight_step_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_local_pytest_passed=181",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_autodl_pytest_passed=181",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_report_json_sha256=b7e2c112a53472f3444c0758cd96d10aa1a473bae18fa189305db4ab96d20040",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_report_md_sha256=dea9e6fd9f100fc97365aab97555cdc5de41e7e7a81bcb3fc82d38c202378ce9",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_report_sha256s_sha256=7128febc040ac057901314bd290230a8598a1d3038e6debcff11ab8f2bc7d3ae",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_heads_sha256=bb39c1eb1dae5a5debd24a43217c73f8bcaf471b2abd7833fa5fe055bf13ec67",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_command_sha256=fe988dbc65d7c3fc4096e27c92e8182ec0c249599a91f997d1893f160d6474b4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_stdout_sha256=953037947e42c64b79962a68573bf9f0328ed2527ddf5807808b429ed422bfdc",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_run_exit_sha256=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_artifact_sha256s_sha256=b936a7b8b00bd2871c0c3b11fbbd2197edbf6998dea034625315db4b1eeb1939",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_rejected",
        "current_v14_next_scope=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_contract_fix_or_rerun",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_passed=False",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_contract_fix_or_rerun",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_authorized_rerun_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review Failed Attempt"
    )
    section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review Authorized Rerun"
    )
    next_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_39e05a250c_20260704T112434CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_12cd3dc982_20260704T104156CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_camp_head=39e05a250c515708ced4db44db38cc2d90232d44",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_check_count=155",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_source_preflight_check_count=226",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_source_preflight_step_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_local_pytest_passed=185",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_autodl_pytest_passed=185",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_report_json_sha256=72388f7b2c1a5c08d838cf5bc3f95d973e57745e4113ca7c414d2f7c24f5b264",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_report_md_sha256=bd3de2d399f8cc2fe9a9324b6e71aafe7260fc037e19ec6ca07c92ebb8cc704b",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_report_sha256s_sha256=7d13f2b4ae3e112c56820fc526dfccf5425de6e2146b5801f8a0da387931613a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_heads_sha256=74a2389a9f2b516c4e9b5655fc927370b50b5efbf4e462e546b4236051de209c",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_command_sha256=6b90bb7dfd41877f70f69e686d6589ae5dd9eb9e89633f483ed9806936fd07b2",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_stdout_sha256=51af4fc420efa9192145f7ab9f4cf6f86fde8f8acd1a75a0bd1a00e45675cfe6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_artifact_sha256s_sha256=5a9bf7357f76e8fa817a1d6fea257abfc0ccb8ffa998d2f1bade0727dbd48f73",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_only",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_only",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review Authorized Rerun"
    )
    section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution"
    next_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Static Review"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert text.rfind(next_section_title + "\n") > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_705f669eb5_20260704T114256CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_39e05a250c_20260704T112434CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_12cd3dc982_20260704T104156CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_camp_head=705f669eb548ed945a62bfeff299fc4fe20c2cc3",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_check_count=216",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_metrics_manifest_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_no_go_summary_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_evidence_matrix_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_local_pytest_passed=191",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_autodl_pytest_passed=191",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_report_json_sha256=4e249d44ef58f590b78c062f652b70d6830e629e852aa5d114d9783e6a5be76d",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_report_md_sha256=e6e8d07dfe90b29d8eca707ff1b2c38dbb41d7a1982f31d51e4737ec8722d44d",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_report_sha256s_sha256=92a4dd56fb4746aefd8b43cf0c2ead33beae348dd03615d8c875ec9e7746d2c4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_heads_sha256=57e8fef8aa1e65a7f7e78227c5518644be0339aa424d892b70919a11a5d13059",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_command_sha256=49c8fc54e8e33c3d992a2df0d26561b23037cf5f074a9acac8c214bc02458912",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_stdout_sha256=7a891c9725a207d04166d59fc9718a4f780508baacd62f48fb5993f8f7f86f8a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_artifact_sha256s_sha256=67ada09453d62c4842e8263db8e62b5dffe8ba520d17d18e09a44b574695e61e",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_only",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_authorized=True",
        "evaluation_runbook_executed_by_this_gate=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_only",
    ]:
        assert needle in text

def test_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution"
    section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Static Review"
    )
    next_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Result Review"
    )
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert text.rfind(next_section_title + "\n") > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_f5d5b4cbf4_20260704T115712CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_source_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_705f669eb5_20260704T114256CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_camp_head=f5d5b4cbf4990b982c97e4b0d7885141a0f911d1",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_check_count=136",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_source_execution_check_count=216",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_source_metrics_manifest_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_source_no_go_summary_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_source_evidence_matrix_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_local_pytest_passed=197",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_autodl_pytest_passed=197",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_report_json_sha256=cf47d7e9c99481ad9333634a8f87e4052553c9a73f09cf2fce2b58e5bc836e14",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_report_md_sha256=4ef1c1b9a2be66197bcb536aec60c89910c3cf04db453a5b63ab6d59e9a9f581",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_report_sha256s_sha256=18ecdf3ac9197f2c7b02d999beb9ae3d36dc82a4850a58135d69fdf5c26201d8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_heads_sha256=3675729046dcc923bfc61349145ab03a2c87dc3bab5ef6e6dc9d84499759b4fe",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_command_sha256=b62dcaf7b5655eb92055f594f6b5d1db0c3423e0c6675e89287817490b6089e6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_stdout_sha256=239bd8af578426c373b53d74008d14b309b8863e674eb95fc36a8f82744010eb",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_artifact_sha256s_sha256=0ceae80cd45e1642aad1035322cbb847067eaa3b603b7064759ef8c855668274",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_only",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_authorized=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
        "evaluation_runbook_executed_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_only",
    ]:
        assert needle in text

def test_v14_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Static Review"
    )
    section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Result Review"
    )
    next_section_title = "## Post-Closeout Promotion-Readiness Follow-Up Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert text.rfind(next_section_title + "\n") > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_b7853716a3_20260704T120906CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_f5d5b4cbf4_20260704T115712CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_source_execution_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_705f669eb5_20260704T114256CST",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_camp_head=b7853716a3731ada094b30837692b6e081469726",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_check_count=219",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_source_static_review_check_count=136",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_source_execution_check_count=216",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_source_metrics_manifest_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_source_no_go_summary_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_source_evidence_matrix_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_direct_promotion_recommendation=False",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_promotion_decision_plan_authorized_next=False",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_followup_requires_explicit_user_decision=True",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_local_pytest_passed=204",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_autodl_pytest_passed=204",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_report_json_sha256=01db8beb60d1701b0d39fd952837d2ecd439163c1446254689f48abad6714a7a",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_report_md_sha256=27899aebaed717d33647ea515de3475930e5eed557d8bf59175585170924012e",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_report_sha256s_sha256=510937bb43ac432048d8f6733deda5fe8dd262ad2d4ba54de41d4bce549e4b53",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_heads_sha256=0f4755fed931348fa18eef8990688135fbd5bcecc96cd3bb265b9b91eb1dbaf4",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_command_sha256=6fc5d3b3d1eb097d06e5b59fff0d3ae4c33b01ce366b20a4d229cae1ccc87027",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_stdout_sha256=71ec2c62dbdda240ef2b2222693fe2a8688069c19750a6c412f3798697b0dc7d",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_artifact_sha256s_sha256=da84ec74ff9cebb5adaa25c99dc3f25ccde9b5981e10f9142e77765347dcc562",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_passed",
        "current_v14_next_scope=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_evaluation_followup_or_promotion_authorization",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_passed=True",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_authorized=False",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_static_review_authorized=False",
        "post_closeout_promotion_readiness_evaluation_runbook_execution_authorized=False",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "followup_requires_explicit_user_decision=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_evaluation_followup_or_promotion_authorization",
    ]:
        assert needle in text

def test_v14_post_closeout_promotion_readiness_followup_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Post-Closeout Promotion-Readiness Evaluation Runbook Execution Result Review"
    )
    section_title = "## Post-Closeout Promotion-Readiness Follow-Up Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Follow-Up Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_followup_plan_dfeb575c78_20260704T123010CST",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_source_result_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_result_review_b7853716a3_20260704T120906CST",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_camp_head=dfeb575c78d35249a6ef1ee58549a4fadbc38393",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_followup_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_check_count=128",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_items=authorization_boundary,fixed_dp_candidate_tensor_provenance,shadow_score_to_decision_gap,uncertainty_and_coverage_gap,fail_closed_runtime_acceptance_gap,safety_claim_gap,camp_over_dp_top1_claim_gap",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_local_pytest_passed=210",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_autodl_pytest_passed=210",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_report_json_sha256=da5db972e613f09dd6ebfa618bfdc127a70d708855c24a38468706f545468516",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_report_md_sha256=528ffb5ed8a6d466ef6e4645cdaf88c69a659c03467c02fb08cd6ff2c41343f7",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_report_sha256s_sha256=3029dca804444ba09a1c1ec40522a2e405d99d2ec023811008a03752dcdfa5cd",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_heads_sha256=b852a745b53a4157c9eb1e26163649690c87142925fe69510140a9dffb935141",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_command_sha256=71a50fa93ae9f0843af25cf74b43a6f39899d1df93394691f53838c63cb0fb04",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_stdout_sha256=150d71a5a41e4815793dbfdc28a65aa53977888c6e454f6d768282ce2b7e340d",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_artifact_sha256s_sha256=f3a739fae08143402c9fbffd45b284cb43a32f6c50a79b0c6eb8f3df07850b18",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_followup_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_followup_plan_static_review_only",
        "post_closeout_promotion_readiness_followup_plan_ready=True",
        "post_closeout_promotion_readiness_followup_plan_static_review_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_followup_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_followup_plan_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Follow-Up Plan"
    section_title = "## Post-Closeout Promotion-Readiness Follow-Up Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_f6e7122d1d_20260704T123957CST",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_followup_plan_dfeb575c78_20260704T123010CST",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_camp_head=f6e7122d1d1d198b02da2beb89802852e79f007f",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_followup_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_check_count=134",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_source_plan_check_count=128",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_source_followup_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_local_pytest_passed=216",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_autodl_pytest_passed=216",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_report_json_sha256=5cf0d1c2af9b668bbd7827043f3efa8a87f80606d74da60140836c004ef942cf",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_report_md_sha256=20ea4d9f5aeb21f465e9d89867bd04a1f5656f13f8a05fb73da77d070c2cb8c4",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_report_sha256s_sha256=3a868ea576f1368e426a79a1245eb7b03d574396d98d611d5b7032799311c4c8",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_heads_sha256=a8dd14702fdec3023fd170ebe5b5805708e806e5b782637588a2f7f2b44bc718",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_command_sha256=fb00eb24de30ac6af800a2fdc39825e58bef9eb3bccbdfe12fc018d477b395cd",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_stdout_sha256=47459e6ff7e5291a47c85d877c2f7bd60feb2d73539328499ee533f578a75922",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_artifact_sha256s_sha256=85aad8b3984386cbbf503c2a60f5907f69e6ddf93c17f28d6d7d71a91a3c3716",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_followup_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_only",
        "post_closeout_promotion_readiness_followup_plan_static_review_passed=True",
        "uncertainty_coverage_review_plan_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Follow-Up Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_b7738a2795_20260704T125644CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_f6e7122d1d_20260704T123957CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_camp_head=b7738a2795c4d123ec87a5ebda832cd8a26842a0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_check_count=124",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_source_static_review_check_count=134",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_source_plan_check_count=128",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_source_followup_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_items=score_margin_uncertainty_surface,coverage_slice_matrix,candidate_tensor_support_coverage,atom_contribution_stability,default_off_fail_closed_uncertainty_boundary,claim_boundary,promotion_thresholds_tbd",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_local_new_pytest_passed=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_local_readiness_pytest_passed=152",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_local_v14_audit_pytest_passed=70",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_autodl_new_pytest_passed=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_autodl_readiness_pytest_passed=152",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_autodl_v14_audit_pytest_passed=70",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_report_json_sha256=e54c1dbd7690339a0c62d4529d85e5b11565065e66446f089c61fbb023654276",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_report_md_sha256=ea876fd5c53141443843f67817421d8bc8fa51660a5d0b9887d1a8277e7424a1",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_report_sha256s_sha256=0b98964d3342ebbb60ddf308e5057796fef15567466c9082db0507ffff573827",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_heads_sha256=84b485994db38452ab59b52caf6cd53fe08408fccea2724b4f5a9413a6aeb9b7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_command_sha256=f2642df67a10754ff2386eb78f2078c7facc4d481db182b5ec6ea5e00e0b216d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_stdout_sha256=f390a036c70d064176ac87b3e0f7eea11908c97dbb84778cbe71693e31cba385",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_artifact_sha256s_sha256=8698abb5ece03dae91c383f81281dc4a01d1ddbb9d4dbf106e7a2a5f3e9ac3af",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_only",
        "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_ready=True",
        "uncertainty_coverage_review_plan_static_review_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_ffcdeabd52_20260704T130813CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_b7738a2795_20260704T125644CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_camp_head=ffcdeabd52df1416fa1e2329860aede37711b608",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_check_count=140",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_source_plan_check_count=124",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_source_plan_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_local_new_pytest_passed=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_local_readiness_pytest_passed=157",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_local_v14_audit_pytest_passed=71",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_autodl_new_pytest_passed=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_autodl_readiness_pytest_passed=157",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_autodl_v14_audit_pytest_passed=71",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_report_json_sha256=0e71ea1e2843b76e562107f54f0a151b30976fce9ca19e359fd234e7c4df7fb5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_report_md_sha256=3cddd61d806a524abd99a32cbe2030179f041d750155da3181da729626e4f1ed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_report_sha256s_sha256=1ee7f5e0e53e9a839ce53fb9d91a944422d877c2aad2147388b1eecf8904f8f3",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_heads_sha256=1c0eb12244ecb45f31fe3422e482a1c32187ac81eefe32352ecda901ce854587",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_command_sha256=710280627a9450eb48b5a405c34d762ffb3bfd8d5ab07c544f798e045d9fe3c3",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_stdout_sha256=99ff699a3ac51eefdb9f9ea74e09e6931280582f45638d053c724fbbd83d0cca",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_artifact_sha256s_sha256=e3a8d25dc506132bc3bca1e9cf2a27f76e0f76addda9e2b3e1315b6974b5eab2",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_only",
        "post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_passed=True",
        "uncertainty_coverage_review_preflight_plan_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_5add991571_20260704T132654CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_ffcdeabd52_20260704T130813CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_camp_head=5add9915714f54d0a8bcec8e4cde97f80c83f79e",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_check_count=123",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_source_review_check_count=140",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_source_plan_check_count=124",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_source_plan_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_items=source_artifact_inventory,fixed_dp_candidate_tensor_boundary,uncertainty_input_manifest,coverage_slice_manifest,atom_stability_input_manifest,default_off_fail_closed_boundary,claim_and_promotion_no_go_boundary",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_local_new_pytest_passed=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_local_readiness_pytest_passed=162",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_local_v14_audit_pytest_passed=72",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_autodl_new_pytest_passed=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_autodl_readiness_pytest_passed=162",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_autodl_v14_audit_pytest_passed=72",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_report_json_sha256=b6767ec6d89cc0f06657b524a38e02e7412176a141079e2888f7ed77eb64eb91",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_report_md_sha256=01387171bcbb6937d396b2c09ec38ce6fa341def8d9e2e0cced7a1174e9fc118",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_report_sha256s_sha256=f178f72d21c52b1348234ac0cf4dfc55b75bf61fc983106fcf268431a905a79b",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_heads_sha256=7c1233a3d6764aadd390bbe642944534c2334bcd555f3f9bae8a14fd7b2ca278",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_command_sha256=8b7766a1e326de1c3e54f1fddb43b1943a17c1560638a55b0f66a243e9b936e5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_stdout_sha256=04e4f40abdc6cddb3c6b0af5db55dbb65b4e45d95fd8adfb3ddf39d12f452fa3",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_artifact_sha256s_sha256=b8f30962b9754f4dac6077be5d92de3b7d089a317131d45c3c0b378fe5023f57",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_only",
        "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_ready=True",
        "uncertainty_coverage_review_preflight_plan_static_review_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Plan"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_36e691f3e3_20260704T134054CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_source_preflight_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_5add991571_20260704T132654CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_camp_head=36e691f3e3f12f9679f9975b10cfabe518e24e06",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_check_count=142",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_source_preflight_plan_check_count=123",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_source_preflight_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_source_review_check_count=140",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_source_plan_check_count=124",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_source_plan_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_local_new_pytest_passed=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_local_readiness_pytest_passed=167",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_local_v14_audit_pytest_passed=73",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_autodl_new_pytest_passed=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_autodl_readiness_pytest_passed=167",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_autodl_v14_audit_pytest_passed=73",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_report_json_sha256=61ed4b27c7a08a12c2fe95b7b09e621b3e80aa45e48cba698932b87c0d46aa4c",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_report_md_sha256=3291be876dd32bf3375420fd8da383bc4ce377f10627329df7ea809ef3d8c506",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_report_sha256s_sha256=2a267460d42c5ce94b9e1138f01b5fabfa01896a9b72c9916cf1e582803df1a4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_heads_sha256=cb614270717c7ed34b4c488ba4bef531cdd7c087e3055f0ff04c0ed3b98adc58",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_command_sha256=6f56e8c49b840a8e43b9124eca02d57389cf069c11251269862f6be898f1d38d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_stdout_sha256=629b0b6357e5677987b588bc4f023eb380efad525a6b42440df0c150365eba7e",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_artifact_sha256s_sha256=d8d2bad56aaa5811f1000ec1a4de39b4b9eab6a6c074fd87dd1e48c19017b2de",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_only",
        "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_passed=True",
        "uncertainty_coverage_review_preflight_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review Failed Attempt"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_e3fa0b0aa1_20260704T140146CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_source_preflight_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_36e691f3e3_20260704T134054CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_source_preflight_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_5add991571_20260704T132654CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_camp_head=e3fa0b0aa12e0f4e846f0bfb61bb88f61b0c425c",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_check_count=190",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_artifact_manifest_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_no_go_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_future_review_requirement_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_source_static_review_check_count=142",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_source_preflight_plan_check_count=123",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_source_preflight_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_local_new_pytest_passed=6",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_local_readiness_pytest_passed=173",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_local_v14_audit_pytest_passed=74",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_autodl_new_pytest_passed=6",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_autodl_readiness_pytest_passed=173",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_autodl_v14_audit_pytest_passed=74",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_report_json_sha256=7020065887967debf04413339f35b61ab3beacf21e8dea4547ed6637294633b7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_report_md_sha256=576d7e205c3fbaea8a829ecf17ff06b747672999431b73b596f986dfb8dca26f",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_report_sha256s_sha256=78eb395ce59704af95fe42122d9aca98fe537c07e95e81a966ddf530905205b3",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_heads_sha256=bc7fc4108c3fa188d7d26741fdf763576f1fcc9ce1976250d593704ae397dca7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_command_sha256=ee91443e7df48aeb57d8d3dda3b9ac4dd4001b691ac5598740f3afa436ba42c0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_stdout_sha256=6d8fec746241af0f1712cdac7f7846df9ac6972d8c3f8d93317a297d035cae31",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_artifact_sha256s_sha256=550e0e4f959490ad4edd4b41b8ca607127072603390c996c549718523a2e0e23",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_only",
        "post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_ready=True",
        "uncertainty_coverage_review_preflight_static_review_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_attempt_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review Failed Attempt"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review Authorized Rerun"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_f1b6f46eb6_20260704T142410CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_e3fa0b0aa1_20260704T140146CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_camp_head=f1b6f46eb62bfcd0abd614430a89c0f3791f8d84",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_exit=1",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_rejected",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_failure_class=v14_eof_contract_mismatch",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_checks=audit_preflight_static_review_authorized",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_review_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_failed_check_count=1",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_source_preflight_check_count=190",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_source_review_preflight_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_source_artifact_manifest_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_source_no_go_status_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_source_future_review_requirement_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_report_json_sha256=dff6c80361bdebcd3c2fbec341cb5214eab615421c9a9dd43abddab166fa4b4a",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_report_md_sha256=4338d914879dbc16abaa14f6ba28a3a203d404a025e961c662667fdb9c79ea91",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_report_sha256s_sha256=29ef504cb53c40bf81effc06285e15fba93b78eae96f3938a13dc1b1d9746ea7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_heads_sha256=7d851342fcbe24a67e9f16e258b96f982a8f08411e918f183ebebc5d9df80c6c",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_command_sha256=20d0c05b89a38fc6858f7f65f22c4058a5b029927d754cfdc39212b1b947af10",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_stdout_sha256=bc0308a632ecbae8e01e9e94270551160708686540dcaebe87e8e959d33d428e",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_run_exit_sha256=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_artifact_sha256s_sha256=4772fb3d5ec88f82ab3586884bf187aed119384d5c65edd074935f3bd382b620",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_failed_check_observed=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_failed_failed_check_expected=True",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_rejected",
        "current_v14_next_scope=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_contract_update_or_rerun",
        "uncertainty_coverage_review_preflight_static_review_passed=False",
        "uncertainty_coverage_review_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_contract_update_or_rerun",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review Failed Attempt"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review Authorized Rerun"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_contract_update_rerun_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_947199c5fc_20260704T165923CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_contract_update_rerun_failed_failure_class=v14_eof_contract_mismatch",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_contract_update_rerun_failed_checks=audit_failed_attempt_failed_checks",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_contract_update_rerun_failed_report_json_sha256=f978c7317d4d06d3dc442c11e60ee23837b93d661a15d879347e6d78c572277d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_contract_update_rerun_failed_artifact_sha256s_sha256=5b7b9a776e8376adba20c16b81b8460388ba8b131ec5caec4ef4cb0739040b7d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_6156533717_20260704T170306CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_e3fa0b0aa1_20260704T140146CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_camp_head=61565337174dc697f610b709eb2b50a3f86c0415",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_review_check_count=141",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_source_preflight_check_count=190",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_source_review_preflight_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_source_artifact_manifest_requirement_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_source_no_go_status_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_source_future_review_requirement_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_local_new_pytest_passed=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_local_readiness_pytest_passed=180",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_local_v14_audit_pytest_passed=76",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_autodl_new_pytest_passed=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_autodl_readiness_pytest_passed=180",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_autodl_v14_audit_pytest_passed=76",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_report_json_sha256=942b9c253e1157c134a37f9302c39ad864bc259d7d93a0f856d75e69e0ab37d0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_report_md_sha256=b5d947bb5f0628a86f948d20a72ffe8d209a9a2450dc6e43b092874fa2f9b066",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_report_sha256s_sha256=eaf716f442446d8d5a67bc0e1d8da3751c2d9bacb608415ab45eca32f7950f6f",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_heads_sha256=44f90d0bdfb21d482133e04beb1fa37d588adfea3ea31a0881acd0ac7ab48677",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_command_sha256=3280a39414678179fe648bbd284283ab7368414d4a5edff4cf3992d98f9def1a",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_stdout_sha256=9be22e853521bb52b25d618f7241ae2bddf2f7d382ed16748dc35668f1053ced",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
    ]:
        assert needle in text

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_authorized_rerun_artifact_sha256s_sha256=0dbe49ba3a8ec2787f683e102b19916c89e21041cb196934e2d26970ee811caa",
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_only",
        "uncertainty_coverage_review_preflight_static_review_passed=True",
        "uncertainty_coverage_review_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review Authorized Rerun"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_aa52033244_20260704T173104CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_source_preflight_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_6156533717_20260704T170306CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_source_preflight_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_e3fa0b0aa1_20260704T140146CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_camp_head=aa52033244edd6932ec6b1ec19f82530415659ac",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_check_count=227",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_evidence_gap_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_evidence_gaps=future_uncertainty_input_manifest,future_coverage_slice_manifest,future_atom_stability_manifest,future_no_go_summary,future_claim_boundary_summary",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_direct_promotion_recommendation=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_report_json_sha256=155e75843dc7c9309c7c87a7536cabc0e93561ea24208798b4e9136e45dd7edf",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_report_md_sha256=63b7cbe448d70cbfb1319dcd5d8e336f021638992e2ec1dfcd0e06ccd90bb8dd",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_report_sha256s_sha256=69aba1564b54866e064fe6e1b5ff300118a09245a966cac7fccec35a4cb67b9d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_heads_sha256=879694a56330dfafd30fff4ea346e101055034e8a42415ebe9350a01e21e5bba",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_command_sha256=c0e9bfef05fbb1e8a1526adbc08d0193f56eb4f9c22121d7f84b8e317e3139ba",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_stdout_sha256=8f7e81cb9bea515c44a3b63c4faea14742866e3c79ba56557e34e1b5968010e7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_artifact_sha256s_sha256=ba38b942a768a060b6d1bd5d01d6add71e6472649e5a5df73ff3cb56d64afa3e",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_only",
        "post_closeout_promotion_readiness_uncertainty_coverage_review_passed=True",
        "uncertainty_coverage_review_static_review_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_cacedef80a_20260704T174554CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_source_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_aa52033244_20260704T173104CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_camp_head=cacedef80aa8c123a205c938da5512cadd0a06c0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_check_count=134",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_source_review_check_count=227",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_source_review_item_count=7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_source_evidence_gap_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_report_json_sha256=0cdbd53a61526d43d5154f5e396ea883f578098216f49f88760c3a3f93c21641",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_report_md_sha256=0aa31f5869d7d30c55d4e289846dacaf101b7b3c274952d0773b6315048c0245",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_report_sha256s_sha256=2059e0e2b2af4e4023c931634dd13290577cd8e3f103739958bc6ad9e60ef546",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_heads_sha256=f7c21d9e2409de0ecb58cc84db6eb6837e4b08f2b553f71f09d181e296e345fd",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_command_sha256=a93b7ad2218857562f68b93b1c3241b81b2b0e25c82b36019e0f6f9d7e7cccae",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_stdout_sha256=4be9a75f842137c4c04ad273be9fc9ccdf4e5a6b5701e01816f2820dcfc99d82",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_artifact_sha256s_sha256=272ea05d4931e46d11020ccb68f6978f105aa312dfe1bf2b5cd3b80447fd649e",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_only",
        "post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_passed=True",
        "uncertainty_coverage_evidence_gap_closure_plan_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Failed Attempt"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_63d41f1ce9_20260704T180522CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_cacedef80a_20260704T174554CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_camp_head=63d41f1ce9b548cc3ad981a4950dfd5a7ca29ff8",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_check_count=143",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_items=future_uncertainty_input_manifest,future_coverage_slice_manifest,future_atom_stability_manifest,future_no_go_summary,future_claim_boundary_summary",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_source_static_review_check_count=134",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_source_review_gap_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_report_json_sha256=101665e562f3a65ca112de8e9ede61d1b86753930530084df5ebc765d51812eb",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_report_md_sha256=61cda9ac9139b9c337c157846148edacc97c9c1fb5f010041a7f53411aab2155",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_report_sha256s_sha256=7c7970a791ade7dcd99f4526affbea137fd1358d8c3aef50b52db2299fad8d7c",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_heads_sha256=48ce09fa026f729478c5444f679d71f3291f0bb289ce4d39abffc7fdd9b2a0b9",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_command_sha256=06f8889a044d364cc2d8147ff51cc76e71e9e8c4be7a233d00911733a3709c23",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_stdout_sha256=6fe7bf7eebe827eb5e120e025a736bd56ca4e36e0237a769ecb3681799d21913",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_stderr_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_run_exit_sha256=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_artifact_sha256s_sha256=8cb495ffb5b181b7889fbc454b92cc20d48076278bc15392b2b1d79113e42866",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_only",
        "post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_ready=True",
        "uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized=True",
        "direct_promotion_recommendation=False",
        "promotion_decision_plan_authorized_next=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_attempt_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Failed Attempt"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Authorized Import-Path Rerun Failed"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_da3f193bfd_20260704T182013CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_63d41f1ce9_20260704T180522CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_camp_head=da3f193bfdff11531370f4c0be247ac34a98d219",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_exit=1",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_failure_class=python_import_path_failure",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_error=ModuleNotFoundError: No module named 'scripts'",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_artifact_sha256s_sha256=1b2c38b0cda2b167218e4a7ad4ec087c9519d745d775130581d41d10e881fc89",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_command_sha256=99ea16393f57e9a208491a344404b9d31670b9aba4995fbf87d4b44a0e274146",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_heads_sha256=75898fb2ab6ed6bfbb797ba3575c06ffcfee3255c3c8091ef663572288833f9b",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_stdout_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_stderr_sha256=445e8f4a0dfbf258433dbea9d0d3dc61521893338a419da606b596dd7934f5d9",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed_run_exit_sha256=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_failed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_import_path_fix_decision_required",
        "uncertainty_coverage_evidence_gap_closure_plan_static_review_passed=False",
        "uncertainty_coverage_evidence_manifest_materialization_plan_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_import_path_fix_decision_required",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Failed Attempt"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Authorized Import-Path Rerun Failed"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Authorized Contract-Update Rerun"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_a8b480bd40_20260704T210802CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_63d41f1ce9_20260704T180522CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_camp_head=a8b480bd4053a15cf33734faaafcbd4cbb79ad69",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_exit=1",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_rejected",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_failure_class=v14_eof_contract_mismatch",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_failed_checks=audit_latest_status_is_source_plan_ready,audit_latest_eof_authorizes_static_review,status_doc_latest_status_is_source_plan_ready,status_doc_latest_eof_authorizes_static_review",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_check_count=151",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_failed_check_count=4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_report_json_sha256=6e0113eb1e5c108fefc336759b34fe0469de8f0b79bec64d31581c94ae8b869d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_report_md_sha256=10fc6b24ca8665ba2df01716052f8e66c546b55c9ad99219c3249c94e22d6c9f",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_report_sha256s_sha256=d3109180162c06ee4bb914a7f7fe525bf0d612a393081d43322d00541aa0d49a",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_artifact_sha256s_sha256=ff6f4f7cda8f5bed0c7a7e2d9d25f2c82627cf753d5cd051b56ca5c74e1c593f",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_import_path_rerun_failed_stdout_sha256=013b226d87af0e1472c311f4d0e2811b10a4d04d7959d201e89e19d1f650c11d",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_rejected",
        "current_v14_next_scope=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_contract_update_or_rerun",
        "uncertainty_coverage_evidence_gap_closure_plan_static_review_import_path_fixed=True",
        "uncertainty_coverage_evidence_gap_closure_plan_static_review_passed=False",
        "uncertainty_coverage_evidence_manifest_materialization_plan_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_contract_update_or_rerun",
    ]:
        assert needle in text


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_passed_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Authorized Import-Path Rerun Failed"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Authorized Contract-Update Rerun"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_f14aeb8301_20260704T230602CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_63d41f1ce9_20260704T180522CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_prior_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_a8b480bd40_20260704T210802CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_camp_head=f14aeb8301b79b9c4f20860f2889e69bde01bb47",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_check_count=157",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_report_json_sha256=48bbe2477ca81ba397d8fd9693a273669324c68ca50d1f9dc2f505c15bb50dfb",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_report_md_sha256=c4992fe84d141502336385ffdb7ddee2ae9bd355bab3d2666b17f5c79b8d35ed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_report_sha256s_sha256=50dff8d47babbbb16900fbec5d43e69ddbf7c4ebc831c957e5adc335c3dd4a23",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_authorized_contract_update_rerun_artifact_sha256s_sha256=f614295156b780ec48f3a3367299eb43585a0e78389991a00faac3239b4313ed",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_only",
        "uncertainty_coverage_evidence_gap_closure_plan_static_review_passed=True",
        "uncertainty_coverage_evidence_manifest_materialization_plan_authorized=True",
        "read_only_contract_compatibility_remediation_standing_authorized=True",
        "read_only_same_gate_rerun_after_audited_contract_failure_authorized=True",
        "standing_authorization_scope=audited_eof_or_existing_source_artifact_layout_read_only_contract_compatibility_only",
        "standing_authorization_excludes=evidence_materialization,replay,training,candidate_generation,dp_modification,selector_promotion,deployment,online_selector_activation,deployable_checkpoint_claim,safety_benefit_claim,camp_over_dp_top1_claim,trajectory_generation_or_modification,postprocess,guidance,reference_blend",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_ready_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Authorized Contract-Update Rerun"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_c90db9ccaf_20260704T233139CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_f14aeb8301_20260704T230602CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_prior_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_efee0ea10c_20260704T232749CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_prior_failed_failure_class=artifact_contract_failure",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_prior_failed_failed_checks=artifact_review_sha256s_root_sha",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_camp_head=c90db9ccaf97bbc1ddd2a22abf21cfa3bac1a869",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_manifest_plan_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_manifest_names=uncertainty_input_manifest,coverage_slice_manifest,atom_stability_manifest,no_go_summary,claim_boundary_summary",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_source_static_review_check_count=157",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_source_plan_check_count=143",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_source_plan_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_source_static_review_source_check_count=134",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_source_review_gap_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_report_json_sha256=355f6c426ba4304e793bf8371ae1557cd7ce807f89b8922f44110bc07f59944e",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_report_md_sha256=87b6b56d9a391dae5593857b1e49edc8eeff5c14cc312d2c3463b057a1fff7e2",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_report_sha256s_sha256=147b37795924a2e4548917bed660587797ed104a93def8d6be65e4998c5fb7ed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_artifact_sha256s_sha256=e430a7b192e0caaa62d5ff034961ec448831db2f1812572c1c2dbf1fc46eb65c",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_only",
        "uncertainty_coverage_evidence_manifest_materialization_plan_ready=True",
        "uncertainty_coverage_evidence_manifest_materialization_plan_static_review_authorized=True",
        "evidence_manifest_materialization_authorized=False",
        "plan_only_contract_compatibility_remediation_standing_authorized=True",
        "standing_authorization_scope=audited_eof_or_existing_source_artifact_layout_read_only_or_plan_only_contract_compatibility_only",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_passed_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Plan"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_4c5560efd3_20260704T235337CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_c90db9ccaf_20260704T233139CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_prior_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_fa4e043a78_20260704T235059CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_prior_failed_failure_class=source_evidence_manifest_materialization_plan_contract_failure",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_prior_failed_failed_checks=plan_script_schema_constant,plan_script_static_review_next",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_camp_head=4c5560efd36bc3d1171eb617e84bb14227843ded",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_check_count=153",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_source_plan_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_source_manifest_plan_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_report_json_sha256=1048ab3d2f849fdb08754413e09f066b25cee23bfe2643f92c9e805c3250240d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_report_md_sha256=97f140e196feef522c644806e9d2d755f57a01999881023d360d187dc7ff2f3e",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_report_sha256s_sha256=de28ede9e8a1b70387fd3dd496f72e17e431a89b5f17ba571dbf518cb44d707d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_artifact_sha256s_sha256=667ca528491d2665f637225bfd9a10fefb18cb64ef68adc53fa8f827993f48eb",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_only",
        "uncertainty_coverage_evidence_manifest_materialization_plan_static_review_passed=True",
        "uncertainty_coverage_evidence_manifest_materialization_authorized=True",
        "evidence_manifest_materialization_authorized=True",
        "evidence_manifest_materialized_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialized_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_d0a8ebf7ca_20260705T000751CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_static_review_4c5560efd3_20260704T235337CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_plan_c90db9ccaf_20260704T233139CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_camp_head=d0a8ebf7caad48cc9370ad3eda9a66efb4a49e2c",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialized",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_check_count=200",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_manifest_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_uncertainty_input_manifest_sha256=365c9433e06d134a77df985912f897f61b9f4050f94b54891788e42a36c4329c",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_coverage_slice_manifest_sha256=c53eeb246ea1fe14d17b5b5c13c6ccfae18a87e35f03be5284d2725c6fe1a58f",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_atom_stability_manifest_sha256=e0b1fa2505c1968a8629b89f9aef2f0c5d4296f9949dc380efeec59703b9d664",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_no_go_summary_sha256=882b17c64d53ad2ba967b5cf60887b4b37245827038c9103365590c5643c8b18",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_claim_boundary_summary_sha256=4e464040a00c77cd48395f0a418f57ca792ec5c358b254f011e6c0daf16d062b",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_report_json_sha256=1fd3253f00df3c433b308b5fdb3d22bf1149364cac8d28800b9a41f18e9f2b8e",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_artifact_sha256s_sha256=0113bf49d7fab35fbc87ca36c03d8c2c514c176626c3ecc8e59a2fb08fb170ec",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialized",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_only",
        "uncertainty_coverage_evidence_manifest_materialized=True",
        "evidence_manifest_materialized_by_this_gate=True",
        "evidence_manifest_materialization_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_800733f6db_20260705T002303CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_source_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_d0a8ebf7ca_20260705T000751CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_camp_head=800733f6dbcf735bdcba53fbd35860175cd91205",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_check_count=234",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_manifest_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_all_no_execution=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_all_no_claim=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_source_materialization_check_count=200",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_report_json_sha256=b2b353488cdfe4b5c42cc95a59d90aa8ac12dcac1fe1ec8c5fa689b24932884a",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_report_md_sha256=c67b346e66657b6f6a5ff43a3aee67583b7cadb4d37f15905487c0abee063d7d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_report_sha256s_sha256=889d158fea4ed5ef5c2ed868bb18c640396acc65c3746ee51f628a46ee6aa88a",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_artifact_sha256s_sha256=60efd215d46e127e86fe8df275fb0c83de55a5d11886d1315265f9aea9476ad6",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_only",
        "uncertainty_coverage_evidence_manifest_materialization_static_review_passed=True",
        "uncertainty_coverage_evidence_package_construction_plan_authorized=True",
        "evidence_package_construction_plan_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Manifest Materialization Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_4dccc210b3_20260705T004110CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_800733f6db_20260705T002303CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_source_materialization_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_d0a8ebf7ca_20260705T000751CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_camp_head=4dccc210b3b9ad091185c19de1b165d583839235",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_check_count=186",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_package_plan_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_source_review_check_count=234",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_source_materialization_check_count=200",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_report_json_sha256=e64786a806abd1b1657447d419800584cedc9198c1d64bca1fa969bd517d3908",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_report_md_sha256=ee589140bf6af905be8d9f0b197c656b079fc96b262b0e0e3abda5ba1bf37683",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_report_sha256s_sha256=3678571d8bdab1fb579b011b2f85e335bfb9840735fe339404a43e70feacffc1",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_artifact_sha256s_sha256=d2e1ba572844861cc5e41d063c166c4d0e85024cfc8995193609d41e2f850533",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_only",
        "uncertainty_coverage_evidence_package_construction_plan_ready=True",
        "uncertainty_coverage_evidence_package_construction_plan_static_review_authorized=True",
        "evidence_package_constructed_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Plan"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Failed Attempt"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_f13558e2b7_20260705T005644CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_4dccc210b3_20260705T004110CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_camp_head=f13558e2b74957ff4894d7115dc63cc32f42fb61",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_source_plan_check_count=186",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_package_plan_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_all_no_construction=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_all_no_execution=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_all_no_claim=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_report_json_sha256=47d21286d6639bad8009c9feaf1967981b8391b5b78210cba8c1032e92eb81ce",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_report_md_sha256=b02e561f45c7c5a83b9a1628eb034738868f31bab633f35f9ace3e6c308655b0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_report_sha256s_sha256=87c46572693d30bda7a7997478c9e50788f1a80317f37f12d6c1f3a8d4d94f53",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_artifact_sha256s_sha256=cf30a9a14f785bc8309ba5dff2cdbc4f234cb4e000621f14fb0474fa8334fce7",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_only",
        "uncertainty_coverage_evidence_package_construction_plan_static_review_passed=True",
        "uncertainty_coverage_evidence_package_construction_authorized=True",
        "evidence_package_construction_authorized=True",
        "evidence_package_constructed_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_failed_attempt_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Failed Attempt"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Authorized Rerun"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_22ad3c4810_20260705T011927CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_f13558e2b7_20260705T005644CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_4dccc210b3_20260705T004110CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_materialization_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_800733f6db_20260705T002303CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_materialization_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_d0a8ebf7ca_20260705T000751CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_camp_head=22ad3c4810ad3111091d75f44c060553c0b6444e",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_exit=1",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_rejected",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_passed=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_failure_class=fixed_dp_head_mismatch",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_failed_checks=current_dp_head_fixed,current_camp_head_is_sha",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_failure_root_cause=command_harness_single_quoted_heredoc_did_not_expand_head_origin_dp_head_out",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_report_json_sha256=5f8597740f3fedfc2de91aa96426905a3e09c5f39e07b4bdef7fca24bdc5d539",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_report_md_sha256=11cbd97282d93cfde9c8a8d803d095bb7fefac19277a239e935dbc9cccf82f77",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_misdirected_sha256s_sha256=b43656e0ed8e90026573e1539a2061f5b59129732589a803c89037ff66414276",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_artifact_sha256s_sha256=771e976039631d27a31801925a3ff65d3c27e2b2087750f66e3adfb20bea1073",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_rejected",
        "current_v14_next_scope=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_command_harness_fix_or_rerun",
        "uncertainty_coverage_evidence_package_construction_passed=False",
        "uncertainty_coverage_evidence_package_constructed=False",
        "evidence_package_constructed_by_this_gate=False",
        "uncertainty_coverage_evidence_package_construction_static_review_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=user_decision_required_before_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_command_harness_fix_or_rerun",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_authorized_rerun_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Failed Attempt"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Authorized Rerun"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_bae3730925_20260705T102630CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_static_review_f13558e2b7_20260705T005644CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_plan_4dccc210b3_20260705T004110CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_materialization_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_static_review_800733f6db_20260705T002303CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_materialization_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_manifest_materialization_d0a8ebf7ca_20260705T000751CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_prior_failed_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_22ad3c4810_20260705T011927CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_camp_head=bae3730925f6792277fc09d0c337e1750936f4da",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_constructed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_check_count=376",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_static_review_check_count=139",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_plan_check_count=186",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_materialization_static_review_check_count=234",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_materialization_check_count=200",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_source_manifest_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_package_file_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_package_payload_file_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_report_json_sha256=cf993441c045cff7b2e0b5cdbb1e01afcdae701ae6c3fc47037b5bb0ee0444b2",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_report_md_sha256=d5e862e23604a75e7d7e78c739f955099e8fa90b9d34c2208c1f7049c0408769",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_package_sha256s_sha256=8b28333491ac4018b35300ea244b34dcff8f2e802f74cf4f546b41d6766bde7b",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_artifact_sha256s_sha256=d29b3049a96c2787723bd5b8dfbd87ca19d4460df6ce8e36a7e9bc5fd893ef47",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_constructed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_only",
        "uncertainty_coverage_evidence_package_construction_passed=True",
        "uncertainty_coverage_evidence_package_constructed=True",
        "evidence_package_constructed_by_this_gate=True",
        "uncertainty_coverage_evidence_package_construction_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Authorized Rerun"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_6b46a96493_20260705T104019CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_source_construction_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_bae3730925_20260705T102630CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_camp_head=6b46a964935a545391724f7250914b1faa629e4f",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_check_count=233",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_source_construction_check_count=376",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_package_file_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_package_payload_file_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_package_manifest_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_package_all_no_execution=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_package_all_no_claim=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_package_all_no_promotion=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_report_json_sha256=72287bbfcb931b2cc9e2a1163796cc5120fff8dc424489e1182bae0bdd9cdbb4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_report_md_sha256=0ef0cf1a24fff69053a7c149ec5031423fe340cbad5dad88685505be858bc3d7",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_report_sha256s_sha256=2f383d8872f444268f41ea5ab808749d5e3424972c457bf288e6b3005cd8988d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_artifact_sha256s_sha256=191f41a7e2a4f3075097502db1306ff09114242c7bf16ebee42e5ef9a4706240",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_only",
        "uncertainty_coverage_evidence_package_construction_static_review_passed=True",
        "uncertainty_coverage_evidence_package_closeout_plan_authorized=True",
        "evidence_package_constructed_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_ready_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Construction Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Plan"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Plan Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_f5ffa807d7_20260705T105733CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_construction_static_review_6b46a96493_20260705T104019CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_camp_head=f5ffa807d7af724bd908e6a20299a52e721c015d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_check_count=124",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_closeout_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_static_review_check_count=233",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_package_file_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_package_payload_file_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_package_manifest_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_package_all_no_execution=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_package_all_no_claim=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_source_package_all_no_promotion=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_items=package_scope_lock,source_artifact_hash_register,claim_boundary_closeout,promotion_readiness_residual_gap_register,next_review_contract",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_all_no_execution=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_all_no_claim=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_all_no_promotion=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_all_no_deployment=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_report_json_sha256=f26f474d6bc2a10201c89adf7d2b3566d229fc88ed5381a6123b966f90e3ae89",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_report_md_sha256=374c26d8d7a221a8c69d52eeaab2b40473603bf02b5db91337a780973610ba92",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_report_sha256s_sha256=76cac381d5db48b8ede7c25f74f6f8b640ac2bba83945f20ef78c5ced4d7bf6c",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_artifact_sha256s_sha256=c9cc3cd470e87b9798cdc96aa02cd1210064d0a8999365e38c8637459b535914",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_only",
        "uncertainty_coverage_evidence_package_closeout_plan_ready=True",
        "uncertainty_coverage_evidence_package_closeout_plan_static_review_authorized=True",
        "evidence_package_closed_by_this_gate=False",
        "evidence_package_constructed_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_passed_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Plan"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Plan Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Record"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_9a95abeb13_20260705T110947CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_source_closeout_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_f5ffa807d7_20260705T105733CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_camp_head=9a95abeb13a4f5878f33a53c776430c1ade98dbe",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_check_count=145",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_source_plan_check_count=124",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_source_package_file_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_source_package_payload_file_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_source_package_manifest_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_source_package_all_no_execution=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_source_package_all_no_claim=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_source_package_all_no_promotion=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_closeout_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_all_no_closeout_record=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_all_no_execution=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_all_no_claim=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_all_no_promotion=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_all_no_deployment=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_report_json_sha256=782dd391ba65a1aa18aede9c86a4e498deaa67a0febd0285559cb54d3d4bbee4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_report_md_sha256=0a211cf4542297fdac0f208a053d74100db79e3defb15d839240f65d767de2d0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_report_sha256s_sha256=1afcc4c677c807696363b75506dea02276a92f3f4083ad3379613b26ed98cbac",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_artifact_sha256s_sha256=3fc49dbaca3dadba544b3c6c22a78c45e350854d2520f884dafa07d89ebcd5e2",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_only",
        "uncertainty_coverage_evidence_package_closeout_plan_static_review_passed=True",
        "uncertainty_coverage_evidence_package_closeout_record_authorized=True",
        "evidence_package_closed_by_this_gate=False",
        "evidence_package_constructed_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_recorded_is_historical() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Plan Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Record"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Record Static Review"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_bfc036f654_20260705T112006CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_plan_static_review_9a95abeb13_20260705T110947CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_camp_head=bfc036f654cb7d3f66cee0a2120632441dc87e7f",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_recorded",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_check_count=135",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_source_static_review_check_count=145",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_source_package_file_count=8",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_source_package_payload_file_count=6",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_source_package_manifest_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_source_package_all_no_execution=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_source_package_all_no_claim=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_source_package_all_no_promotion=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_decision=close_uncertainty_coverage_evidence_package_stage_without_promotion",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_final_package_state=audit_evidence_only_closed_no_promotion_no_deployment_no_claim",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_promotion_recommended=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_selector_promotion=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_deployment=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_safety_claim=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_camp_over_dp=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_only",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_report_json_sha256=866913140f8281bd6a59e34a4484d846122cd2f48494979ba3af67b4135033c0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_report_md_sha256=8915a85cab01a16107c2ce357fa9dbac5c7dff387a4b624e7113669fad4a0d61",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_report_sha256s_sha256=ded998ceae6baca51639e914b0eb8069bd9c84a48f69b281354dcf1a092e6c68",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_artifact_sha256s_sha256=234282b357470f24d1ac0512a04a1fbd27810bad9de959a13bf1b0def3d99ca9",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_recorded",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_only",
        "uncertainty_coverage_evidence_package_closeout_recorded=True",
        "uncertainty_coverage_evidence_package_closeout_record_static_review_authorized=True",
        "evidence_package_closed_by_this_gate=True",
        "evidence_package_constructed_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_passed_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Record"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Record Static Review"
    next_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Continuation Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")
    next_section_index = text.rfind(next_section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert next_section_index > section_index
    assert "\n## " not in text[section_index + len(section_title) : next_section_index]

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_4ad91af64a_20260705T113031CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_source_closeout_record_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_bfc036f654_20260705T112006CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_camp_head=4ad91af64a394b0c3afad889d91f3ebf42633ec9",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_passed",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_check_count=136",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_source_record_check_count=135",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_source_record_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_record_decision=close_uncertainty_coverage_evidence_package_stage_without_promotion",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_final_package_state=audit_evidence_only_closed_no_promotion_no_deployment_no_claim",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_promotion_recommended=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_selector_promotion=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_deployment=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_safety_claim=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_camp_over_dp=False",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_authorized_next_work=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closed_no_further_action_without_new_eof_authorization",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_report_json_sha256=788798b04e21b18b3eb3a4a55cda6c9da3111f396131b1a6d478b5e966fa5a6e",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_report_md_sha256=f06aba9c9ef7f2c8b434c69fff471268feab78ad55ff727155bedd74864fc2a8",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_report_sha256s_sha256=cbd46be2b95250fa30b42df90c1a711c39b0b32c4f4780e254c6323d3cfcfa7f",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_artifact_sha256s_sha256=31f9e96a9b4fed5adbbe94c647126937be64120000da9c26421cf706f68a2097",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_passed",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closed_no_further_action_without_new_eof_authorization",
        "uncertainty_coverage_evidence_package_closeout_record_static_review_passed=True",
        "uncertainty_coverage_evidence_package_closed=True",
        "evidence_package_closed_by_this_gate=False",
        "evidence_package_constructed_by_this_gate=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closed_no_further_action_without_new_eof_authorization",
    ]:
        assert needle in text

def test_v14_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_ready_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Closeout Record Static Review"
    section_title = "## Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence Package Continuation Plan"
    previous_section_index = text.rfind(previous_section_title + "\n")
    section_index = text.rfind(section_title + "\n")

    assert text.count(section_title + "\n") == 1
    assert section_index > previous_section_index
    assert "\n## " not in text[section_index + len(section_title) :]

    for needle in [
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_010337e3f4_20260705T124852CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_source_static_review_artifact=/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_closeout_record_static_review_4ad91af64a_20260705T113031CST",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_camp_head=010337e3f48ab45700100b9a339206bde2e5390d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_exit=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_ready",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_passed=True",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_failure_class=None",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_check_count=122",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_failed_check_count=0",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_source_static_review_check_count=136",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_continuation_item_count=5",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_report_json_sha256=6b4616fa29eca47f3af8cb9f85d2b5698fc8cf26b9743db09e7c7bdc70e7f35d",
        "v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_artifact_sha256s_sha256=c66292e8777cbd7c7a5221bc932da4b63b2c72f4dd7adafdd62d91c78d6a21cc",
    ]:
        assert needle in text

    for needle in [
        "current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_ready",
        "current_v14_next_scope=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_static_review_only",
        "post_closeout_continuation_plan_ready=True",
        "post_closeout_continuation_plan_static_review_authorized=True",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_uncertainty_coverage_evidence_package_continuation_plan_static_review_only",
    ]:
        assert needle in text

    _assert_latest_v14_status(text)


def test_current_status_and_readme_point_to_v14() -> None:
    status_text = CURRENT_STATUS_DOC.read_text(encoding="utf-8")
    readme_text = README.read_text(encoding="utf-8")

    assert "docs/diffusion_planner_v14_iteration_audit.md" in status_text
    assert "do not keep appending current\nwork to v13" in status_text
    assert "88fd3cac6722aedfd4ca13b41f904b4a3331c219" in status_text
    assert "1ffff597ebdc0cc598daff7db2150df2d5d898ab" in status_text
    assert "458c66c8aeac8b9eb15ba3f06a7f87e5c9ef0740" in status_text
    assert "2e17d119941b8134fc4adb7b607204d7ee95899e" in status_text
    assert "356ce6301cd02a59dedb971f85aac8481be0a7fd" in status_text
    assert "aff9b0533ff63172f834dfede3836e5553bb05e0" in status_text
    assert "67f8062de6cd36fc9f0480223ad262b1f3f09af5" in status_text
    assert "b075ec0854dc7f9d6522fbf6423f8ec1ae00539c" in status_text
    assert "adc71422af56711f8baec545259fe47626f955ef" in status_text
    assert "72fdb3e4c880751948a47d25b0330e3818975162" in status_text
    assert "2dd27b50b8172fb6f31df9a154e55c329f6ae2f9" in status_text
    assert "4b17b353024a45b2f89d360f3e63c20ae76eac01" in status_text
    assert "9aea47cc48aad4be26d8221e3c6c40dcf612d9d1" in status_text
    assert "8fe12a0fbaa2083613cfaf83f5d0f8693423e6c1" in status_text
    assert "55c360b8047834271a1667a2ebd3353e914358c6" in status_text
    assert "5687ee3ee608651da4bab7646d8a45c1eb631b75" in status_text
    assert "0152e7bd81dcbbd0962b35a96df5392028b53f47" in status_text
    assert "1546633d50750358379694243b3629ac08aabe3c" in status_text
    assert "98e495749e605304f1094bff62e47ab7c8317775" in status_text
    assert "2610c4a89f20f86a4ffbe8a8f275ae56a6b85b3a" in status_text
    assert "2456037d6f3b214f31ea5991a28732aa52e7bed4" in status_text
    assert "11f1f7f853e66eec5327184479fb24ab133cb5bc" in status_text
    assert "ddce7a172512060ec990f6d01b1269888ca72024" in status_text
    assert "844e46604c460027fc0c8602903b7c365ef91d6b" in status_text
    assert "3aeb54ec0bdf6e9c24d22ddf102b7ac4d828c790" in status_text
    assert "af4064d7baacb7f073a8aded89a588233e4e80ce" in status_text
    assert "9b772d78233cafe508fd2f140188b3f391382d11" in status_text
    assert "169e5d10c41f50882c3990b336c79a566739a875" in status_text
    assert "97754f14ee1f5511ba3e779520a186600a63bfca" in status_text
    assert "bae51947d2ce4e51937da823703181fbf095a333" in status_text
    assert "b4f312801c5256f73ae6b4f97a6638ce47441bb0" in status_text
    assert "dbd5b539a0117c47ea0809e923940619ec41214a" in status_text
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_execution_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_result_review"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_result_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_only_after_explicit_user_authorization"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_only_after_explicit_user_authorization"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_complete"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialized"
        in status_text
    )
    assert (
        "Default-Off Selector Runtime Shadow Replay Preflight"
        in status_text
    )
    assert (
        "default-off selector runtime shadow replay preflight and"
        in status_text
    )
    assert (
        "runtime promotion evidence-package static review authorized rerun"
        in status_text
    )
    assert (
        "fresh execution completed the"
        in status_text
    )
    assert (
        "The result review only inspected the passed execution audit"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_result_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_only"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_artifact_dbd5b539a0_20260703T090930CST"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_vs_top1_delta_review_04f4b68421_20260703T103434CST"
        in status_text
    )
    assert "04f4b6842178204717051209e0b106c67332d420" in status_text
    assert "Default-Off Selector Runtime Shadow-vs-Top1 Delta Review" in status_text
    assert "Static objective delta supported:" in status_text
    assert "`better=2832`, `tie=368`, `worse=0`, `uncomparable=0`" in status_text
    assert "Raw affine score before feasibility masking:" in status_text
    assert "2bdfbce1e89db54465d895148f3dc3ecae2a511b3db889a29f693cb4cdfebc62" in status_text
    assert "24b24b26ad644076ec2952b575b840068e44e13ee12abcf78416655f799722bd" in status_text
    assert "shadow-vs-Top1\ndelta review has also passed" in status_text
    assert "static masked-objective delta" in status_text
    assert "not a safety or CAMP-over-DP claim" in status_text
    assert "Default-Off Selector Runtime Promotion-Decision Plan" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_decision_plan_192d2928b2_20260703T110247CST"
        in status_text
    )
    assert "192d2928b2c9bbe22275f02c3c1532e713b1542f" in status_text
    assert "do_not_promote_from_current_evidence_alone" in status_text
    assert "build_runtime_promotion_evidence_package_preflight_only" in status_text
    assert "no-promotion closeout record only" in status_text
    assert "Default-Off Selector Runtime Promotion Decision From Evidence Package Plan" in status_text
    assert "592d57e2232b598597e686b576190ce155845376" in status_text
    assert "do_not_promote_from_current_evidence_package_alone" in status_text
    assert "record_no_promotion_closeout_only" in status_text
    assert "dd3fd82b62243cb7860329337e5e87da003988109d9c8489f24d0a5c66e52f9a" in status_text
    assert "eb9cbe1782a771879ae2e6b2c649ce547a3acfe4b27c7583a3a176c35440c584" in status_text
    assert "Default-Off Selector Runtime No-Promotion Closeout Record" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_record_4e16075a8b_20260703T180106CST"
        in status_text
    )
    assert "4e16075a8b21189660f2abe94648e88040510945" in status_text
    assert (
        "dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_decision_no_promotion_closeout_record_v1"
        in status_text
    )
    assert "`65 / 0`" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_recorded"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_only"
        in status_text
    )
    assert "47d70a2a423a1b4fda6f6726261ca9495de1b448e7cad30056e512d4abb24876" in status_text
    assert "b01d0a7eafc89691c7d3a150b6eba84bb967f352defd4e45a799da040a322bd4" in status_text
    assert "read-only no-promotion closeout review only" in status_text
    assert (
        "Default-Off Selector Runtime No-Promotion Closeout Review Failed Attempt"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_1f00a091f9_20260703T182026CST"
        in status_text
    )
    assert "1f00a091f9615de3272b460060a307ba6337c486" in status_text
    assert "script_import_path_missing" in status_text
    assert "ModuleNotFoundError: No module named 'scripts'" in status_text
    assert "False / False / False" in status_text
    assert "5648fa205f1b101852f5e22c21d3ef14b7b462e8dbe173fbbfe8daa5b1dcb742" in status_text
    assert "9856d3fc226bc07066593106996f4bdd8266b1e5ffadfd54466e82feec9eb75f" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_rejected"
        in status_text
    )
    assert "16394aebd9cf92025fc36613f196d6f0728c1a60ec12768474e459d48e88eb44" in status_text
    assert "c025186948924debf7e43b26c2d2d3025e649e167cf37c7301e8c5cfe312a811" in status_text
    assert (
        "Default-Off Selector Runtime No-Promotion Closeout Review Rerun Failed Attempt"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_rerun_0c629925d2_20260703T212231CST"
        in status_text
    )
    assert "0c629925d2957fac3e851bc3a689cfa29c2de467" in status_text
    assert "v14_eof_contract_mismatch" in status_text
    assert "artifact_sha256s_record_sha256s" in status_text
    assert "audit_latest_status" in status_text
    assert "status_doc_latest_next_work" in status_text
    assert "`103 / 5`" in status_text
    assert "f9aeef3fde5f656288b3f4f2e01518ac2c1eb27d6dee567935e9fdee828b7899" in status_text
    assert "bc77f6128e209c33b9a687dd3644e080f0e15f533cfb08fc8ded0c7f951a8bf0" in status_text
    assert (
        "Default-Off Selector Runtime No-Promotion Closeout Review Contract-Update Rerun"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_no_promotion_closeout_review_contract_update_rerun_74d34a7949_20260703T221152CST"
        in status_text
    )
    assert "74d34a7949c115ee61294c97aae9c81a111465cb" in status_text
    assert "`104 / 0`" in status_text
    assert "c30f59e5dd44bab5ecb0770df763ae45aed85b035d5c69b066d73a592ba28ced" in status_text
    assert "88731c96cabf5618a6d53063aaf21c8aebafa6d37b58ec847bf66c42a5f50837" in status_text
    assert "61cc00a8edfc72f07502c3834ea0d7743a73f904a4b245612d48f834ba292ca0" in status_text
    assert "732489dbc7d0be079506b42a819eba4efdf302e162fefd7fc219d46d2a2c0a9a" in status_text
    assert "current evidence package is\nclosed with no promotion" in status_text
    assert "Post-Closeout Promotion-Readiness Gap Analysis Failed Attempt" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_plan_068223a31b_20260703T224120CST"
        in status_text
    )
    assert "source_review_heads_key_case_contract_mismatch" in status_text
    assert "`400 / 2`" in status_text
    assert "result_review_heads_dp_fixed" in status_text
    assert "delta_review_heads_dp_fixed" in status_text
    assert "2866457c1bbb63baee3a4217f856075b4063feedaafd0f68f276d1f6f09bcf7a" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_plan_rejected"
        in status_text
    )
    assert "Post-Closeout Promotion-Readiness Gap Analysis Contract-Fix Rerun" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_contract_fix_rerun_cd54951760_20260703T233911CST"
        in status_text
    )
    assert "cd54951760bc94b4ecaf16eeff316176f7c46556" in status_text
    assert "`404 / 0`" in status_text
    assert "do_not_promote_or_deploy_from_current_evidence_package" in status_text
    assert "static_review_this_gap_analysis_only" in status_text
    assert "9851ee0e59b497e2091d4dd24e48e126f15cef8b0a7f04b2ec9da8cde433a558" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_static_review_only"
        in status_text
    )
    assert "Post-Closeout Promotion-Readiness Gap Analysis Static Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_gap_analysis_static_review_f0836545b4_20260703T235643CST"
        in status_text
    )
    assert "f0836545b481e627a801aeda8d8ab020df2eb161" in status_text
    assert "`181 / 0`" in status_text
    assert "keep_no_promotion_and_plan_readiness_preflight_only" in status_text
    assert "plan_promotion_readiness_evaluation_preflight_only" in status_text
    assert "1ebfcae38f4a963324b4d45313178e66519bfa875750b3b0bd4815888719e3aa" in status_text
    assert "378190e3e0d5a9ef3572cfca0ff1ec69f5516011f74a39b38ecc7d0020ea3f52" in status_text
    assert "52005bae8778c90db4621a06a1308bd53eec65810c8ec6a4667216c8bc2a1c98" in status_text
    assert "b394ee54aa70ee388d73c7d22e09530a9b8013e4ee6fe1598a9dc0c382753d62" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_gap_analysis_static_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_only"
        in status_text
    )
    assert "Post-Closeout Promotion-Readiness Evaluation Preflight Plan" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_763a0f5612_20260704T000918CST"
        in status_text
    )
    assert "763a0f56124c16c3b295ce78a0ae7832508ff377" in status_text
    assert "`171 / 0`" in status_text
    assert "static_review_this_preflight_plan_only" in status_text
    assert "static_review_promotion_readiness_evaluation_preflight_plan_only" in status_text
    assert "607ab3a34cd9e685422ede50726c6f218a440e6715be2f34b442ed5cb86b2c8a" in status_text
    assert "a6752413e9cd72010123405a8c23f882254f250cb429129cd5e49d6c029cf4e2" in status_text
    assert "1e75bf316eda161bfafaf52ab85fba5962e447d9115300f78c29f84c5a7449ea" in status_text
    assert "c3a0a5409faf534d9ca87d84e5c6040c7e8e3a974d5b78bd065a58aa1fac560a" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_only"
        in status_text
    )
    assert "Post-Closeout Promotion-Readiness Evaluation Preflight Plan Static Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_28958edc70_20260704T001942CST"
        in status_text
    )
    assert "28958edc70bc645c9e8b1d7f6ab051ea9f35a063" in status_text
    assert "`137 / 0`" in status_text
    assert "run_promotion_readiness_evaluation_preflight_only" in status_text
    assert "execute_read_only_promotion_readiness_evaluation_preflight" in status_text
    assert "a50fcc6a9834d17df02686f4e7b9d7b95726cad61e48afd06c39268ab7fc96f9" in status_text
    assert "3010277ab0c747826547803229c8bc7bcd9311f84a18ba6925b41c057903cb3c" in status_text
    assert "0cb14b8ad0f12b4e854ec2d157d0b2c24be75a284706f6f89086a5fbc1c9f3d6" in status_text
    assert "82702c311a9dda374ceaa1840544eecaa544b108c9b487827787ae303c7eea5d" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_plan_static_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_only"
        in status_text
    )
    assert "Post-Closeout Promotion-Readiness Evaluation Preflight" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_c65da3c60f_20260704T003848CST"
        in status_text
    )
    assert "c65da3c60f1415cd8f2599e1aa6be5384e43ed30" in status_text
    assert "`179 / 0`" in status_text
    assert "`5 / 7 / 4`" in status_text
    assert "static_review_this_preflight_only" in status_text
    assert "static_review_promotion_readiness_evaluation_preflight_only" in status_text
    assert "2c0a7bbc6a9e5574ad57d6bf5626070d3db755480a2b0e87a0de24d1dd56039d" in status_text
    assert "0d4e537a1d3ce672cb6a5dbc96c688ba5a7c85e1f9809853409eefb4d2f9ebb9" in status_text
    assert "95b85d670956cffee1eb11159388a7d56a791f4a60415961ce677e7f62388b92" in status_text
    assert "288c67da6e66b3844033be27f56a478a08c813ad82f7da8482456a8f741a3bbd" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_static_review_only"
        in status_text
    )
    assert "Post-Closeout Promotion-Readiness Evaluation Preflight Static Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_preflight_static_review_9fd860b1d1_20260704T005150CST"
        in status_text
    )
    assert "9fd860b1d102691ef251d71f0270750b640d270c" in status_text
    assert "`139 / 0`" in status_text
    assert "`179 / 7`" in status_text
    assert "plan_promotion_readiness_evaluation_only" in status_text
    assert "plan_read_only_promotion_readiness_evaluation_only" in status_text
    assert "942e486c5d4d1fdf4e0cc2827fb11834d7a2f42fe7e6c5bef465024581168cbc" in status_text
    assert "c5205b118e56d3950691c8479b92a309943afa53e1099c744cd2af687272f414" in status_text
    assert "3311e251cb1131556a7cb0784c6472264d33e8d9f0d0e813e59b3137ed953648" in status_text
    assert "6643ff956ac432b2af039c89a4c9626f310b921a4acfc100fafc18ff479c096e" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_preflight_static_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_only"
        in status_text
    )
    assert "Post-Closeout Promotion-Readiness Evaluation Plan" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_3da03ab5d3_20260704T011126CST"
        in status_text
    )
    assert "3da03ab5d320cac5d349f23e67f95bef29462947" in status_text
    assert "`224 / 0`" in status_text
    assert "`3 / 7 / 7 / 4`" in status_text
    assert "`139 / 179 / 7`" in status_text
    assert "static_review_this_evaluation_plan_only" in status_text
    assert "static_review_promotion_readiness_evaluation_plan_only" in status_text
    assert "1263efc7c163eda2080b2332be267a449a9d34546e2dd583ba29aeca2784aa39" in status_text
    assert "d7cf65a34ec56512c213db6efc49fc385886eeccf386118fd3bdf5108309c4f7" in status_text
    assert "4c0930f856d20cec2e59456ae6415f746d3a0178090b5cba9670bfb0b0bcfa58" in status_text
    assert "6f9f715fb6c4fe7702c2d2f349d3fcacaa7f3610c681fff78846969f6155cfec" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_post_closeout_promotion_readiness_evaluation_plan_static_review_only"
        in status_text
    )
    assert "Post-Closeout Promotion-Readiness Evaluation Plan Static Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_plan_static_review_494072d472_20260704T012428CST"
        in status_text
    )
    assert "494072d472db17ceef3c8e97e1e76981f6b39f0e" in status_text
    assert "`141 / 0`" in status_text
    assert "`224 / 3 / 7`" in status_text
    assert "plan_follow_on_evaluation_runbook_preflight_only" in status_text
    assert "plan_read_only_evaluation_runbook_preflight_only" in status_text
    assert "dc9cf9a0f5773033c972d29b5442166ddfa35a27e224ed9de1f79a48e8c1a55c" in status_text
    assert "e8c072667b16c1433fbfd6877c462c88fa5c8af73f357a31adb2567d51e4665d" in status_text
    assert "245db13d1e0c09445613c168c211a34d83cf98138de313256c8c5f5d9cfdf02f" in status_text
    assert "0f058dcef5f5de3501e6259c258031821a9902f695271335a58f1175a3b1271e" in status_text
    assert "Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Plan" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_554c3244b1_20260704T014204CST"
        in status_text
    )
    assert "554c3244b1592c3c08f9b76a00695283bb870738" in status_text
    assert "`223 / 0`" in status_text
    assert "`6 / 8 / 6`" in status_text
    assert "`141 / 224 / 3 / 7`" in status_text
    assert "static_review_this_runbook_preflight_plan_only" in status_text
    assert "static_review_promotion_readiness_evaluation_runbook_preflight_plan_only" in status_text
    assert "ea29aeed0b76812a33cdc6449e293dc4b7872719319f47f9f6720b5d92f60b68" in status_text
    assert "5a24aed0ea00f1f0edb75d72710ad089ce35fc22f0c4063d4c6cbb55afb7e32d" in status_text
    assert "98ffcd91449cae3f525445fb288e053786ca80c96f83ee056aa1a962bdd1c623" in status_text
    assert "580762b10d50735654d803e26ff54032a7ea6930928a6d182e257c1f96382607" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Plan Static Review"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_plan_static_review_41539b4bed_20260704T015353CST"
        in status_text
    )
    assert "41539b4bed1f0e532a5147b61263f96a6a193bbe" in status_text
    assert "`139 / 0`" in status_text
    assert "`223 / 6 / 8 / 6`" in status_text
    assert "run_read_only_evaluation_runbook_preflight_only" in status_text
    assert "run_promotion_readiness_evaluation_runbook_preflight_only" in status_text
    assert "c84e0e9a533cf4427908022c64a122561e2e9b45f1137c619992bf2716b58b9b" in status_text
    assert "eac3bd0cefb2efdb24fae15bc3346bf831a3e543e35ac20718a01a881c69d18a" in status_text
    assert "b555a7116895f43338b1814a0ed42f11350dfbbb13a3cee0af5b6c6c9d7f8e74" in status_text
    assert "046f6efbd5657c057ee3a29b25c97cc562a8e5c9225ca1d075423c71c6f434cf" in status_text
    assert "Post-Closeout Promotion-Readiness Evaluation Runbook Preflight" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_3062b4f4a5_20260704T020713CST"
        in status_text
    )
    assert "3062b4f4a5f6d19ebb99f965467aa89f19933ba2" in status_text
    assert "`218 / 0`" in status_text
    assert "`6 / 7 / 8 / 4`" in status_text
    assert "`139 / 223 / 6 / 8`" in status_text
    assert "static_review_this_runbook_preflight_only" in status_text
    assert "static_review_promotion_readiness_evaluation_runbook_preflight_only" in status_text
    assert "666137790e2e4fdd77d31004a732428c3f15e712c6e40815fbfddfff3f909243" in status_text
    assert "1e41dc49c5d8c184d1716a0643505d701a61b82e589bb1c1faab3fe4d3b8a133" in status_text
    assert "0a41486d5b11806d0fbabd1d23e2e85ef5cd4403a4d24f455f63c5f516cd2c13" in status_text
    assert "14a31db3b3cc8b30a5378004309927bb2d5443e74f1ed2709bc0ada1d65ff6c2" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Evaluation Runbook Preflight Static Review"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_preflight_static_review_c2443f45ef_20260704T022733CST"
        in status_text
    )
    assert "c2443f45ef67e8477da9d932dcbbc07cdb2c34fd" in status_text
    assert "`141 / 0`" in status_text
    assert "`218 / 6 / 7 / 8 / 4`" in status_text
    assert "plan_read_only_promotion_readiness_evaluation_runbook_only" in status_text
    assert "plan_promotion_readiness_evaluation_runbook_only" in status_text
    assert "fdd1954bbff79b6dbe4c5793d0af912ab535936b1881d4ea96f4b9ce3f0827e9" in status_text
    assert "c17af0f8bd0c8f5228ce1b1d72ad143545bb752ce517517f42d9afbdb757bea3" in status_text
    assert "0fa44b0bf9ffbcbab8714ee2dff2d3e08ce7af73b6e2f24d50f7d4519d638f78" in status_text
    assert "c68151f656e8f28eb9e9d56aa02fd425d509260ea8066f1389b776150edd1dc6" in status_text
    assert "Post-Closeout Promotion-Readiness Evaluation Runbook Plan" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_c83a4bdc90_20260704T023923CST"
        in status_text
    )
    assert "c83a4bdc905de7df46edd5f718987753972bb535" in status_text
    assert "`186 / 0`" in status_text
    assert "`7 / 9 / 6 / 6 / 8 / 10 / 4`" in status_text
    assert "static_review_this_evaluation_runbook_plan_only" in status_text
    assert "static_review_promotion_readiness_evaluation_runbook_plan_only" in status_text
    assert "e1a189540c205022e723b333a76bb3337ed463da7258fa3f2c46c9d877c270c4" in status_text
    assert "2bb1646d0d57481298a331904414deb7715b873e89b17948e3a723aa9006a5dd" in status_text
    assert "2e70454965073e272c9ea1b626e0364e68d5c6eab4594df75142372dfba719d4" in status_text
    assert "659ea5e856c809a6342b9e91104105e9e52ab5baaf4bfb52529c3fc962e2e471" in status_text
    assert "Post-Closeout Promotion-Readiness Evaluation Runbook Plan Static Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_plan_static_review_dc6b804a9d_20260704T025255CST"
        in status_text
    )
    assert "dc6b804a9d732f2ca29fd3a278a7ef22ecd0954c" in status_text
    assert "`145 / 0`" in status_text
    assert "`186 / 7 / 9 / 6 / 6 / 8 / 10 / 4`" in status_text
    assert "preflight_read_only_promotion_readiness_evaluation_runbook_execution_only" in status_text
    assert "preflight_promotion_readiness_evaluation_runbook_execution_only" in status_text
    assert "22a3d92d6c8d700d4d16b9743e446c618f025c41e7931d260a79627ab8696251" in status_text
    assert "86faba07848e9cf1d6e08d32443d6a41c35345447e9ff9df204b28d4a191796f" in status_text
    assert "f503b8791abf940758b1b99b7a24f54ac96ffd6a1664fcbf56f4eb01bb5e8f72" in status_text
    assert "0f6241357467e9a9d4ea5dfcff78f6945b096707ec3dcb326f8b7c2253901b06" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Failed Attempt"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_e015b6b57b_20260704T030343CST"
        in status_text
    )
    assert "e015b6b57be6d0dfffd0aa6b14546bd9c92e9e4f" in status_text
    assert "`226 / 2`" in status_text
    assert "source_artifact_sha256_mismatch" in status_text
    assert "static_review_artifact_review_sha256s_root_sha" in status_text
    assert "source_static_review_analysis_evaluation_runbook_execution" in status_text
    assert "41b8d4fee277c5192e2cd52c2792314d4a7f22b23591ab5ba4f4f5bb764939f8" in status_text
    assert "68d6a3adebb27709e34857a80e5786f30b04b2b16812ea3d9d39b9cb5032916a" in status_text
    assert "94be3ee40e4c7ee81fb1107eb330f1ceb300618f4bbc6765c4b4301db489c1b9" in status_text
    assert "d8ea62b8b628eee1f279c652233fa0c3c8fdf26e566872da73872357d9640508" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Authorized Rerun"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_12cd3dc982_20260704T104156CST"
        in status_text
    )
    assert "12cd3dc982ef2099fb04aa2914cd459062955cdb" in status_text
    assert "`226 / 0`" in status_text
    assert "static_review_this_runbook_execution_preflight_only" in status_text
    assert "static_review_promotion_readiness_evaluation_runbook_execution_preflight_only" in status_text
    assert "f94c6edfeb909bebcc85cb5aea95b1c9d1cdd4fc3aaea414b8f9f9434a51238f" in status_text
    assert "c652819e2b4738089c392cae2cda72dc18557b06b4481e162417f6d42c6f0c82" in status_text
    assert "ca5508d83187cdeaaa22794a69e960ce5c79cc08ba0cd1cfd4597be7e255b2a2" in status_text
    assert "9ff6d3c38c054e0eac9dced0ff5ce09f6facf27bf1cf4a9a01e9751ef99f7a3f" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review Failed Attempt"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_92fab53910_20260704T105546CST"
        in status_text
    )
    assert "92fab539101db586877d2685f1d99b758d24037c" in status_text
    assert "`155 / 2`" in status_text
    assert "source_preflight_analysis_evaluation_runbook_execution" in status_text
    assert "audit_runbook_execution_preflight_ready" in status_text
    assert "v14_eof_contract_mismatch" in status_text
    assert "b7e2c112a53472f3444c0758cd96d10aa1a473bae18fa189305db4ab96d20040" in status_text
    assert "dea9e6fd9f100fc97365aab97555cdc5de41e7e7a81bcb3fc82d38c202378ce9" in status_text
    assert "7128febc040ac057901314bd290230a8598a1d3038e6debcff11ab8f2bc7d3ae" in status_text
    assert "b936a7b8b00bd2871c0c3b11fbbd2197edbf6998dea034625315db4b1eeb1939" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Evaluation Runbook Execution Preflight Static Review Authorized Rerun"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_preflight_static_review_39e05a250c_20260704T112434CST"
        in status_text
    )
    assert "39e05a250c515708ced4db44db38cc2d90232d44" in status_text
    assert "`155 / 0`" in status_text
    assert "execute_read_only_promotion_readiness_evaluation_runbook_only" in status_text
    assert "execute_promotion_readiness_evaluation_runbook_only" in status_text
    assert "72388f7b2c1a5c08d838cf5bc3f95d973e57745e4113ca7c414d2f7c24f5b264" in status_text
    assert "bd3de2d399f8cc2fe9a9324b6e71aafe7260fc037e19ec6ca07c92ebb8cc704b" in status_text
    assert "7d13f2b4ae3e112c56820fc526dfccf5425de6e2146b5801f8a0da387931613a" in status_text
    assert "5a9bf7357f76e8fa817a1d6fea257abfc0ccb8ffa998d2f1bade0727dbd48f73" in status_text
    assert "Post-Closeout Promotion-Readiness Evaluation Runbook Execution" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_evaluation_runbook_execution_705f669eb5_20260704T114256CST"
        in status_text
    )
    assert "705f669eb548ed945a62bfeff299fc4fe20c2cc3" in status_text
    assert "`216 / 0`" in status_text
    assert "`6 / 8 / 6`" in status_text
    assert "4e249d44ef58f590b78c062f652b70d6830e629e852aa5d114d9783e6a5be76d" in status_text
    assert "e6e8d07dfe90b29d8eca707ff1b2c38dbb41d7a1982f31d51e4737ec8722d44d" in status_text
    assert "92a4dd56fb4746aefd8b43cf0c2ead33beae348dd03615d8c875ec9e7746d2c4" in status_text
    assert "67ada09453d62c4842e8263db8e62b5dffe8ba520d17d18e09a44b574695e61e" in status_text
    assert "Post-Closeout Promotion-Readiness Follow-Up Plan" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_followup_plan_dfeb575c78_20260704T123010CST"
        in status_text
    )
    assert "dfeb575c78d35249a6ef1ee58549a4fadbc38393" in status_text
    assert "`128 / 0`" in status_text
    assert "da5db972e613f09dd6ebfa618bfdc127a70d708855c24a38468706f545468516" in status_text
    assert "f3a739fae08143402c9fbffd45b284cb43a32f6c50a79b0c6eb8f3df07850b18" in status_text
    assert "Post-Closeout Promotion-Readiness Follow-Up Plan Static Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_followup_plan_static_review_f6e7122d1d_20260704T123957CST"
        in status_text
    )
    assert "f6e7122d1d1d198b02da2beb89802852e79f007f" in status_text
    assert "`134 / 0`" in status_text
    assert "`128 / 7`" in status_text
    assert "5cf0d1c2af9b668bbd7827043f3efa8a87f80606d74da60140836c004ef942cf" in status_text
    assert "85aad8b3984386cbbf503c2a60f5907f69e6ddf93c17f28d6d7d71a91a3c3716" in status_text
    assert "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_b7738a2795_20260704T125644CST"
        in status_text
    )
    assert "b7738a2795c4d123ec87a5ebda832cd8a26842a0" in status_text
    assert "`124 / 0`" in status_text
    assert "`134 / 128 / 7`" in status_text
    assert "e54c1dbd7690339a0c62d4529d85e5b11565065e66446f089c61fbb023654276" in status_text
    assert "8698abb5ece03dae91c383f81281dc4a01d1ddbb9d4dbf106e7a2a5f3e9ac3af" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Plan Static Review"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_plan_static_review_ffcdeabd52_20260704T130813CST"
        in status_text
    )
    assert "ffcdeabd52df1416fa1e2329860aede37711b608" in status_text
    assert "`140 / 0`" in status_text
    assert "`124 / 7`" in status_text
    assert "0e71ea1e2843b76e562107f54f0a151b30976fce9ca19e359fd234e7c4df7fb5" in status_text
    assert "e3a8d25dc506132bc3bca1e9cf2a27f76e0f76addda9e2b3e1315b6974b5eab2" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Plan"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_5add991571_20260704T132654CST"
        in status_text
    )
    assert "5add9915714f54d0a8bcec8e4cde97f80c83f79e" in status_text
    assert "`123 / 0`" in status_text
    assert "`140 / 124 / 7`" in status_text
    assert "b6767ec6d89cc0f06657b524a38e02e7412176a141079e2888f7ed77eb64eb91" in status_text
    assert "b8f30962b9754f4dac6077be5d92de3b7d089a317131d45c3c0b378fe5023f57" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Plan Static Review"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_plan_static_review_36e691f3e3_20260704T134054CST"
        in status_text
    )
    assert "36e691f3e3f12f9679f9975b10cfabe518e24e06" in status_text
    assert "`142 / 0`" in status_text
    assert "`123 / 7`" in status_text
    assert "61ed4b27c7a08a12c2fe95b7b09e621b3e80aa45e48cba698932b87c0d46aa4c" in status_text
    assert "d8d2bad56aaa5811f1000ec1a4de39b4b9eab6a6c074fd87dd1e48c19017b2de" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_e3fa0b0aa1_20260704T140146CST"
        in status_text
    )
    assert "e3fa0b0aa12e0f4e846f0bfb61bb88f61b0c425c" in status_text
    assert "`190 / 0`" in status_text
    assert "`142 / 123 / 7`" in status_text
    assert "7020065887967debf04413339f35b61ab3beacf21e8dea4547ed6637294633b7" in status_text
    assert "550e0e4f959490ad4edd4b41b8ca607127072603390c996c549718523a2e0e23" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review Failed Attempt"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_f1b6f46eb6_20260704T142410CST"
        in status_text
    )
    assert "f1b6f46eb62bfcd0abd614430a89c0f3791f8d84" in status_text
    assert "`v14_eof_contract_mismatch`" in status_text
    assert "`audit_preflight_static_review_authorized`" in status_text
    assert "dff6c80361bdebcd3c2fbec341cb5214eab615421c9a9dd43abddab166fa4b4a" in status_text
    assert "4772fb3d5ec88f82ab3586884bf187aed119384d5c65edd074935f3bd382b620" in status_text
    assert (
        "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Preflight Static Review Authorized Rerun"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_947199c5fc_20260704T165923CST"
        in status_text
    )
    assert "947199c5fc566af41e2898a0ba21a0acd4c599e7" in status_text
    assert "`v14_eof_contract_mismatch` / `audit_failed_attempt_failed_checks`" in status_text
    assert "f978c7317d4d06d3dc442c11e60ee23837b93d661a15d879347e6d78c572277d" in status_text
    assert "5b7b9a776e8376adba20c16b81b8460388ba8b131ec5caec4ef4cb0739040b7d" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_preflight_static_review_6156533717_20260704T170306CST"
        in status_text
    )
    assert "61565337174dc697f610b709eb2b50a3f86c0415" in status_text
    assert "`141 / 0`" in status_text
    assert "942b9c253e1157c134a37f9302c39ad864bc259d7d93a0f856d75e69e0ab37d0" in status_text
    assert "0dbe49ba3a8ec2787f683e102b19916c89e21041cb196934e2d26970ee811caa" in status_text
    assert "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_aa52033244_20260704T173104CST"
        in status_text
    )
    assert "aa52033244edd6932ec6b1ec19f82530415659ac" in status_text
    assert "`227 / 0`" in status_text
    assert "`7 / 5`" in status_text
    assert "future_uncertainty_input_manifest,future_coverage_slice_manifest,future_atom_stability_manifest,future_no_go_summary,future_claim_boundary_summary" in status_text
    assert "155e75843dc7c9309c7c87a7536cabc0e93561ea24208798b4e9136e45dd7edf" in status_text
    assert "ba38b942a768a060b6d1bd5d01d6add71e6472649e5a5df73ff3cb56d64afa3e" in status_text
    assert "Post-Closeout Promotion-Readiness Uncertainty/Coverage Review Static Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_review_static_review_cacedef80a_20260704T174554CST"
        in status_text
    )
    assert "cacedef80aa8c123a205c938da5512cadd0a06c0" in status_text
    assert "`134 / 0`" in status_text
    assert "`227 / 7 / 5`" in status_text
    assert "0cdbd53a61526d43d5154f5e396ea883f578098216f49f88760c3a3f93c21641" in status_text
    assert "272ea05d4931e46d11020ccb68f6978f105aa312dfe1bf2b5cd3b80447fd649e" in status_text
    assert "Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_63d41f1ce9_20260704T180522CST"
        in status_text
    )
    assert "63d41f1ce9b548cc3ad981a4950dfd5a7ca29ff8" in status_text
    assert "`143 / 0`" in status_text
    assert "`5`" in status_text
    assert "101665e562f3a65ca112de8e9ede61d1b86753930530084df5ebc765d51812eb" in status_text
    assert "8cb495ffb5b181b7889fbc454b92cc20d48076278bc15392b2b1d79113e42866" in status_text
    assert "Post-Closeout Promotion-Readiness Uncertainty/Coverage Evidence-Gap Closure Plan Static Review Failed Attempt" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_post_closeout_promotion_readiness_uncertainty_coverage_evidence_gap_closure_plan_static_review_da3f193bfd_20260704T182013CST"
        in status_text
    )
    assert "ModuleNotFoundError: No module named 'scripts'" in status_text
    assert "445e8f4a0dfbf258433dbea9d0d3dc61521893338a419da606b596dd7934f5d9" in status_text
    assert "1b2c38b0cda2b167218e4a7ad4ec087c9519d745d775130581d41d10e881fc89" in status_text
    assert LATEST_V14_STATUS in status_text
    assert LATEST_V14_NEXT_WORK in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_from_evidence_package_no_promotion_closeout_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_ready"
        in status_text
    )
    assert "Default-Off Selector Runtime Promotion Evidence-Package Preflight" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST"
        in status_text
    )
    assert "1758ea83eaf61ada32f60b7bbd15e97479b2e1e5" in status_text
    assert "Check count / failed check count:" in status_text
    assert "`229 / 0`" in status_text
    assert (
        "runtime_promotion_decision_plan,runtime_result_review,shadow_vs_top1_delta_review,runtime_manifest,training_artifact_static_review,training_summary,offline_weights_npy,atom_scales_json,runtime_shadow_execution_sha256s"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_ready"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_only"
        in status_text
    )
    assert "Evidence-package static review authorized:" in status_text
    assert "0cda58e1e95b36c867d9208ed51e4e23f24d1106f4460e5d932515eff976b6be" in status_text
    assert "5e277729fe2c0690c599c006a02f221d94d553acdc164f2000e29dbc16283149" in status_text
    assert "Default-Off Selector Runtime Promotion Evidence-Package Static Review Failed Attempt" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_e870358da5_20260703T160217CST"
        in status_text
    )
    assert "e870358da583e851b6ef3dd8033242165681c2a9" in status_text
    assert "source_preflight_sha256s_mismatch" in status_text
    assert "preflight_artifact_path_mismatch_json_md_under_preflight_subdir" in status_text
    assert "4c19c3162cb9488169e9b555a8095617ab6f4f4530f0e160066d1c77ef809458" in status_text
    assert "0f3db6b1cf249e1537d60b49b365397903561d67f92ed3508a038ed9bd93a0b6" in status_text
    assert "Default-Off Selector Runtime Promotion Evidence-Package Static Review" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_rerun_9c9dccdd4d_20260703T164818CST"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_rerun_177c297fee_20260703T163834CST"
        in status_text
    )
    assert "9c9dccdd4d3e6583c6d9bf52945ae82ee5e12956" in status_text
    assert "Check count / failed check count:" in status_text
    assert "`163 / 0`" in status_text
    assert "614b7082ae51a60cf9288c70826530b8212d7d0059d86bf7c1bc2baf7f6ec445" in status_text
    assert "295d90d7ec777053d1fa64da91385e106675e8415d02f6cd6fb0aa012775f92f" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_only"
        in status_text
    )
    assert "Default-Off Selector Runtime Promotion Evidence-Package Construction" in status_text
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_69a3ff3a04_20260703T170856CST"
        in status_text
    )
    assert "69a3ff3a04a7bf1f26d47687a4b7ec26209e107c" in status_text
    assert "`95 / 0`" in status_text
    assert "Evidence package entry count:" in status_text
    assert "`15`" in status_text
    assert "dd5813ce4af9b0235648eae3b78cabec953e512b51d20fb153a6d9027e9b5d55" in status_text
    assert "b214191018907aa29b8f522e63b448ee661b55a7683877a329e85d1cd6597929" in status_text
    assert "689d1ba062f55186c97747d2f18908f383e5300c60a5a277047c9caeafa777ac" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_constructed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_static_review_only"
        in status_text
    )
    assert (
        "Default-Off Selector Runtime Promotion Evidence-Package Construction Static Review"
        in status_text
    )
    assert (
        "/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_construction_static_review_d411ca5dc0_20260703T173614CST"
        in status_text
    )
    assert "d411ca5dc02ae29d20c9f4a5d1bbf942cf7427e9" in status_text
    assert "`244 / 0`" in status_text
    assert "57a52859e676041e47a46eec24638befff57fb48c093d1b7e978c7e068488c2b" in status_text
    assert "8888a9b4a040cb664fe5bd7d5d660734f5b5e4c888f4342f9b1e4c7cffeb1e36" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_construction_static_review_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_decision_plan_from_evidence_package_only"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rejected"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rerun_requires_user_decision"
        in status_text
    )
    assert "Runbook exit / audit exit:" in status_text
    assert "`0 / 0`" in status_text
    assert "Result review exit:" in status_text
    assert "Result review report JSON SHA256:" in status_text
    assert "Executed DP Top-1 records:" in status_text
    assert "Feasible / fail-closed fallback records:" in status_text
    assert "1277624d6ff07b4a02f73c18af10f68a84a6e999b1483a5d654adafebc9cba7c" in status_text
    assert "627fe492c69bbc422a798f025e2cb632008b61dd193b3fa59e1c5c84fbb603ab" in status_text
    assert "Planned command count / expected records:" in status_text
    assert "`32 / 3200`" in status_text
    assert "Check count:" in status_text
    assert "`470`" in status_text
    assert "default-off shadow reranker over fixed DP candidate tensors" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_preflight"
        in status_text
    )
    assert "Commands started/succeeded: `32/32`" in status_text
    assert "Default-off shadow selector summaries: `32`" in status_text
    assert "Candidate tensor provenance summaries: `32`" in status_text
    assert "Closed-loop outcome collection count: `0`" in status_text
    assert "## Zero-Overlap Validation Result" in status_text
    assert "Selection logs: `32`" in status_text
    assert "Records: `3200`" in status_text
    assert "Overlap counts:" in status_text
    assert "`candidate_tensor_hash=0`, `path_signature=0`" in status_text
    assert "`record_identity=0`, `split_manifest_root=0`" in status_text
    assert "reference_training_registry_missing_or_empty" in status_text
    assert "## Data-Preparation Preflight Result" in status_text
    assert "Failed records: `0`" in status_text
    assert "Future training input contract satisfied: `True`" in status_text
    assert "training_input_manifest.json" in status_text
    assert "## Training Preflight Result" in status_text
    assert "Usable feasible records: `2914`" in status_text
    assert "Dropped all-infeasible records: `286`" in status_text
    assert "Training execution authorized next: `True`" in status_text
    assert "CAMP training executed: `False`" in status_text
    assert "## Training Execution Result" in status_text
    assert "Records used / dropped all-infeasible:" in status_text
    assert "`2914 / 286`" in status_text
    assert "Weights sum / min / max:" in status_text
    assert "offline_weights_dp_static.npy" in status_text
    assert "not a deployable checkpoint claim" in status_text
    assert "## Training Artifact Static Contract Review" in status_text
    assert "Weight file matches summary:" in status_text
    assert "Atom scales positive finite:" in status_text
    assert "This review did not train, replay, generate candidates" in status_text
    assert "## Trained Shadow Replay/Evaluation Preflight" in status_text
    assert "script_import_path_missing" in status_text
    assert "Planned command count / expected records:" in status_text
    assert "`32 / 3200`" in status_text
    assert "Runtime manifest default-off / fail-closed:" in status_text
    assert "`True / True`" in status_text
    assert "Executed output policy:" in status_text
    assert "`dp_top1`" in status_text
    assert "Closed-loop outcome command flag present:" in status_text
    assert "## Trained Shadow Replay/Evaluation Execution" in status_text
    assert "stale_runbook_camp_head_mismatch / 41" in status_text
    assert "Shadow selected non-Top-1 records:" in status_text
    assert "Executed DP Top-1 records:" in status_text
    assert "Selection-effect / online-selector-change counts:" in status_text
    assert "Reference-blend steps, closed-loop outcome weights, and postselection active" in status_text
    assert "Forbidden CAMP provenance effects:" in status_text
    assert "5bb414a4a0cc8d3013ade90be55efa9608ced26c7a0ca6c9056d722a137bfeca" in status_text
    assert "CAMP\ncomputed shadow scores and shadow selected indices over fixed DP candidate" in status_text
    assert "## Trained Shadow Replay/Evaluation Result Review" in status_text
    assert "First rejected failure class:" in status_text
    assert "head_or_fixed_dp_contract_failure" in status_text
    assert "Result review JSON SHA256:" in status_text
    assert "41484dde58c3e89b4f2a9a644f3c8f1700e3f198f76e6f20fae8a7c254a17e78" in status_text
    assert "Artifact SHA256SUMS SHA256:" in status_text
    assert "9ba54de606c2aff79a2a85cb5015af3ef59468b963492dc3f2e763bbe930f3fe" in status_text
    assert "The result review is read-only" in status_text
    assert "It authorizes only a future\npromotion-decision plan gate, not promotion itself" in status_text
    assert "## Trained Shadow Replay/Evaluation Promotion-Decision Plan" in status_text
    assert "python_alias_missing_in_runbook" in status_text
    assert "do_not_promote_from_current_evidence_alone" in status_text
    assert "build_promotion_evidence_package_preflight_only" in status_text
    assert "Evidence-package preflight authorized:" in status_text
    assert "Plan JSON SHA256:" in status_text
    assert "c33a5c47b532fb22d73d82e47a6c80094a308e07837a5e96f560dd85b7bcdd77" in status_text
    assert "The conservative\ndecision is that the current evidence is sufficient" in status_text
    assert "## Trained Shadow Replay/Evaluation Promotion Evidence-Package Preflight" in status_text
    assert "source_training_contract_failure" in status_text
    assert "training_summary_contract" in status_text
    assert "Artifact manifest entries:" in status_text
    assert "Static integration contract status:" in status_text
    assert "preflight_ready_contract_pinned" in status_text
    assert "dc4e5bcd3ef41380c91a1911510821ea8fecbdc37a4ac2f9f319c5ee73b2053f" in status_text
    assert "0c874c1b4b5c7814fc67933dcb1af72504e30ceacd3e3168afbfd96457fbf10d" in status_text
    assert "## Default-Off Shadow Selector Static Integration Contract Plan" in status_text
    assert "must_log_shadow_selected_index_without_changing_dp_top1_output" in status_text
    assert "Implementation authorized:" in status_text
    assert "2389f0bf1d2a08e2453e1944c940108fa8997a123fa65e2981397f34d5775951" in status_text
    assert "f5e52d9645cf3b8e1505c3ab63fdda0f5da47c86361a4de504e53007d0d13697" in status_text
    assert "## Default-Off Shadow Selector Implementation Unit-Tests Plan" in status_text
    assert "Target test file:" in status_text
    assert (
        "camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py"
        in status_text
    )
    assert "Unit-tests-only authorized:" in status_text
    assert "499c4da63d66818ac7ab3a16bcd5bea8af2086cc64df10dab759c2c0d451ee44" in status_text
    assert "cebaea57596b233271e857e35a4908de07c80b734b06111c8460b0a9ad897194" in status_text
    assert "## Default-Off Shadow Selector Implementation Unit Tests" in status_text
    assert "Successful artifact:" in status_text
    assert "AutoDL pytest:" in status_text
    assert "`20 passed`" in status_text
    assert "python312_alias_missing" in status_text
    assert "base_python_pytest_missing" in status_text
    assert "1ebe8b8e528e3fc8861f94cda963465f4a95bd365ad72d4bab57a488654eed47" in status_text
    assert "## Default-Off Shadow Selector Implementation" in status_text
    assert "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1" in status_text
    assert "public_simulator_fixed_dp_candidate_tensor" in status_text
    assert "d0be444a9e3454545ce0cacbf0828007d33ae4dfaff8b8d0aab5cae77e9ae3ea" in status_text
    assert "## Default-Off Shadow Selector Post-Implementation Static Review" in status_text
    assert "706ce66d9f9bfa5a9dc75c2053d3dd0689e304e508b64240346d9f13b87da705" in status_text
    assert "Runtime Artifact Manifest Plan" in status_text
    assert "## Default-Off Shadow Selector Runtime Artifact Manifest Plan" in status_text
    assert "321998d25ec45bfee32890636a4acae76a0b7ce342cae17ca7efd55f7d1e995b" in status_text
    assert "be3734e2d897c85c797ad6cb03ccf3f7af6c88202a0db26954dc9e4e1f984b74" in status_text
    assert "Plan checks:" in status_text
    assert "`121`" in status_text
    assert "did not\nwrite the future runtime manifest" in status_text
    assert "## Default-Off Shadow Selector Runtime Artifact Manifest Static Review" in status_text
    assert "554384a654840f5bfcc5ea4d9b4d6e6ba550a0b314e5daccd64cd7238bc05fb6" in status_text
    assert "e9bbd2f62de4bbc06f740bef784c3fec5f7cf768c9878ddb5da3ad12b3e4d7cb" in status_text
    assert "First failed artifact:" in status_text
    assert "runtime_artifact_manifest_static_contract_failure" in status_text
    assert "script_v14_plan_schema,script_authorizes_static_review_only" in status_text
    assert "## Default-Off Shadow Selector Runtime Artifact Manifest Materialization Plan" in status_text
    assert "bac353cb142af137a03e3fa96c21892f57ef3cfe3a3f280d311b1e80a504693d" in status_text
    assert "23179ca81f45cfd997af9953b8a1d129b458e324c38d6ac23fe720395576aa2e" in status_text
    assert "Plan checks:" in status_text
    assert "`109`" in status_text
    assert "Planned runtime manifest exists after this gate:" in status_text
    assert "`False`" in status_text
    assert "## Default-Off Shadow Selector Runtime Artifact Manifest Materialization Static Review" in status_text
    assert "aa3b096059d671cd42d888f7929114800fecd8c50b65af319dbb6e28b52b7134" in status_text
    assert "b3a34cfbaaedd8493c3a91f550d358e52a8190ff67065217bfe2ff757ee6f746" in status_text
    assert "Review checks:" in status_text
    assert "`114`" in status_text
    assert "## Default-Off Shadow Selector Runtime Artifact Manifest Materialization Implementation Plan" in status_text
    assert "8b15be1ccd3be99f0924e71d5ed3befdd57a3416e6ebaa00a1f8986aee68ff59" in status_text
    assert "391438fb49d63de0139d85bbb9d7cff1ffbeb62fad52dd735ff60e59dd4e51b0" in status_text
    assert "`119`" in status_text
    assert "same-directory temp\nfile plus atomic replace" in status_text
    assert (
        "## Default-Off Shadow Selector Runtime Artifact Manifest Materialization Implementation Static Review"
        in status_text
    )
    assert "source_surface_contract_failure" in status_text
    assert "script_implementation_plan_schema" in status_text
    assert "script_authorizes_static_review_only" in status_text
    assert "30ba6e44ec75dacf5fb1fea5ee096bc5f333c1f6087d01cfd0a48e58e273c775" in status_text
    assert "6077c3aa952e4b2a15f01d89330fd018eb2058b19e52aeb29bd4478977129798" in status_text
    assert (
        "## Default-Off Shadow Selector Runtime Artifact Manifest Materializer Implementation"
        in status_text
    )
    assert "9219b03efe692b00eb92ed7d9af9ceaa372937ead1afbe957a9edc48e855ae89" in status_text
    assert "95b7e1dc6ceffc9c4093facc4f73f807b635c37d1e07e0599383334802e22af7" in status_text
    assert "`12 passed`" in status_text
    assert "same-directory temp file plus\natomic replace" in status_text
    assert (
        "## Default-Off Shadow Selector Runtime Artifact Manifest Materializer Post-Implementation Static Review"
        in status_text
    )
    assert "018a5545ee01c64cf025e5f94976b25558b362c428cef07975f0598dffb6bf3b" in status_text
    assert "7d30a023ee0d3f2fed83557a8f1539046bf99a5fe20b89ec9464472e3bb0c35b" in status_text
    assert "materializer_schema_constant`, `materializer_source_plan_schema" in status_text
    assert "5c6056f4f25574ec44de05eac017022f4dcc3827daee6cd69695f14956835886" in status_text
    assert "72d87c7b27d160a2ffbb03b02c4089fab4ec39783c5e60f3221f122f4e66a68f" in status_text
    assert "Review checks:" in status_text
    assert "`121`" in status_text
    assert "Authorized next work:" in status_text
    assert "runtime_artifact_manifest_materialization_only" in status_text
    assert (
        "## Default-Off Shadow Selector Runtime Artifact Manifest Materialization"
        in status_text
    )
    assert "92e82fbf2e7bb26847b6f24b8ccc9d78242addb451bc7301aa77997592569bd2" in status_text
    assert "6e5cdae55b3fccdefd9bd2081e47d4f5a3e88cd7c0b08356117ec47a519945d2" in status_text
    assert "c33f265c9c278a3e03a6c15f601ea31e97810116b536ee6e4d0d40ed8818cfd4" in status_text
    assert "Output existed before:" in status_text
    assert "`False`" in status_text
    assert "Materializer status:" in status_text
    assert "It contains only `atom_scales` and `static_weights`" in status_text
    assert "runtime execution, replay, candidate\ngeneration, DP modification" in status_text
    assert "NuScenes is present and must not be marked missing" in status_text
    assert "/autodl-pub/data/nuScenes" in status_text
    assert "they are not the TIER IV" in status_text
    assert "official rosbag-to-DP `.npz` training source" in status_text
    assert (
        "The training artifact static contract review, trained default-off shadow"
        in status_text
    )
    assert "promotion evidence-package preflight have also passed" in status_text
    assert (
        "selector static integration contract plan, implementation plan, and"
        in status_text
    )
    assert "implementation static contract review have passed" in status_text
    assert (
        "implementation unit-test\nplan, implementation unit-tests-only gate, and implementation-only gate have"
        in status_text
    )
    assert (
        "The post-implementation static contract review and runtime\n"
        "artifact manifest plan-only/static-review/materialization-plan-only/static-review\n"
        "and materialization implementation-plan/static-review gates have passed"
        in status_text
    )
    assert (
        "runtime artifact manifest materializer implementation and post-implementation\n"
        "static contract review are complete"
        in status_text
    )
    assert (
        "the runtime artifact manifest has been\n"
        "materialized"
        in status_text
    )
    assert (
        "default-off selector runtime shadow replay preflight and\n"
        "fresh execution audit/result review have passed"
        in status_text
    )
    assert (
        "the rerun used the corrected preflight subdirectory inputs and\n"
        "passed"
        in status_text
    )

    assert "docs/diffusion_planner_current_status.md" in readme_text
    assert "docs/diffusion_planner_v14_iteration_audit.md" in readme_text
    assert "v14 rollover source" in readme_text
