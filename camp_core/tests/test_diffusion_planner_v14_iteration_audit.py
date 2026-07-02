from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = ROOT / "docs" / "diffusion_planner_v14_iteration_audit.md"
CURRENT_STATUS_DOC = ROOT / "docs" / "diffusion_planner_current_status.md"
README = ROOT / "README.md"


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

    latest_status = text.rsplit("current_v14_status=", maxsplit=1)[1].splitlines()[0]
    latest_target = text.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert (
        latest_status
        == "public_simulator_fixed_dp_candidate_generation_training_execution_passed"
    )
    assert (
        latest_target
        == "public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review"
    )


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


def test_v14_public_simulator_fixed_dp_candidate_training_execution_passed_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Training Preflight Ready After aff9b05"
    )
    section_title = (
        "## Current V14 Public Simulator Fixed-DP Candidate "
        "Training Execution Passed After 67f806"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert "\n## " not in text[text.rfind(section_title) + len(section_title) :]

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

    latest_status = text.rsplit("current_v14_status=", maxsplit=1)[1].splitlines()[0]
    latest_target = text.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert (
        latest_status
        == "public_simulator_fixed_dp_candidate_generation_training_execution_passed"
    )
    assert (
        latest_target
        == "public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review"
    )


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
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in status_text
    assert (
        "public_simulator_fixed_dp_candidate_generation_training_execution_passed"
        in status_text
    )
    assert (
        "public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review"
        in status_text
    )
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
    assert "NuScenes is present and must not be marked missing" in status_text
    assert "/autodl-pub/data/nuScenes" in status_text
    assert "they are not the TIER IV" in status_text
    assert "official rosbag-to-DP `.npz` training source" in status_text
    assert "CAMP training has started and completed" in status_text

    assert "docs/diffusion_planner_current_status.md" in readme_text
    assert "docs/diffusion_planner_v14_iteration_audit.md" in readme_text
    assert "v14 rollover source" in readme_text
