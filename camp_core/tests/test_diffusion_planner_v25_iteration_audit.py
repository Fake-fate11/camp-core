from __future__ import annotations

import hashlib
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v25_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"
FINAL_REPORT = ROOT / "docs" / "diffusion_planner_v25_final_honest_no_claim_report.md"
FINAL_INDEX = ROOT / "docs" / "diffusion_planner_v25_final_evidence_index.md"
CORRECTED_FINAL_REPORT = (
    ROOT / "docs" / "diffusion_planner_v25_final_corrected_evaluation_report.md"
)
CORRECTED_FINAL_INDEX = (
    ROOT / "docs" / "diffusion_planner_v25_final_corrected_evidence_index.md"
)
METRIC_SEMANTICS_REPORT = (
    ROOT / "docs" / "diffusion_planner_v25_metric_semantics_amendment_report.md"
)
METRIC_SEMANTICS_INDEX = (
    ROOT
    / "docs"
    / "diffusion_planner_v25_metric_semantics_amendment_evidence_index.md"
)
V24_AUDIT = ROOT / "docs" / "diffusion_planner_v24_iteration_audit.md"
V24_PAIRED_CONFIG = (
    ROOT / "configs" / "integrations" / "diffusion_planner_v24_paired_evaluation.json"
)

LEGACY_POINTER = (
    "current_v25_status=v25_a11_r01_bounded_pass_ultra_read_only_review_required",
    "current_v25_source_head=de1a21ee2a96a48e3f2e854156538bda5177b477",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v25_artifact=/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_de1a21ee_20260717T223934CST",
    "current_v25_artifact_root_sha256=a520f86c2930fb3c2535efb730bf2e2a1b33db11c77f50535926f1971dbcf07c",
    "current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_review_de1a21ee_20260717T225227CST",
    "current_v25_review_artifact_root_sha256=81a0c1acf7f5c5b76315659b7c917fb641013db20b5a130c27e2402a6560fb6b",
    "current_v25_s01_failed_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_e6ba79a2_20260717T184132CST",
    "current_v25_s01_failed_preflight_artifact_root_sha256=c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a",
    "current_v25_correction_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_retry_e6ba79a2_20260717T184256CST",
    "current_v25_correction_preflight_artifact_root_sha256=bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451",
    "current_v25_correction_preflight_review_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_review_e6ba79a2_20260717T184530CST",
    "current_v25_correction_preflight_review_artifact_root_sha256=facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d",
    "current_v25_correction_preflight_probe_count=3",
    "current_v25_correction_preflight_tick_count=192",
    "current_v25_correction_preflight_check_count=12",
    "current_v25_correction_preflight_review_check_count=28",
    "current_v25_correction_preflight_identity0_deterministic=true",
    "current_v25_correction_preflight_native_canonical_equal=true",
    "current_v25_correction_preflight_candidate_immutability=true",
    "current_v25_correction_preflight_candidate0_operational_default_alias=true",
    "current_v25_s01_remote_focused_test_count=65",
    "current_v25_s01_remote_pointer_test_count=10",
    "current_v25_stage_a0_failed_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_f40b6152_20260717T192912CST",
    "current_v25_stage_a0_failed_artifact_root_sha256=025dcd686ee44a681b14cc3ad8b5e64e885316b0f334d89096fda19d6cd8b810",
    "current_v25_stage_a0_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_01073398_20260717T193038CST",
    "current_v25_stage_a0_artifact_root_sha256=b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41",
    "current_v25_stage_a_superseded_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_v2_01073398_20260717T193052CST",
    "current_v25_stage_a_superseded_ledger_artifact_root_sha256=05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2",
    "current_v25_stage_a_superseded_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_v2_e07da58f_20260717T193156CST",
    "current_v25_stage_a_superseded_validation_artifact_root_sha256=e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72",
    "current_v25_ultra_stage_a_decision_artifact=/root/autodl-tmp/camp_dp_v25_ultra_stage_a11_r01_decision_de1a21ee_20260717T223757CST",
    "current_v25_ultra_stage_a_decision_artifact_root_sha256=d98929000c09cbe1f3bcdc7f57290091e0be31e67726f4920d201bc98292897e",
    "current_v25_atom_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a11_de1a21ee_20260717T223757CST",
    "current_v25_atom_ledger_artifact_root_sha256=836d5468fd05cdbd837037352d14cd20fb21a6b653ece41272bb85b30c42ad82",
    "current_v25_atom_ledger_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a11_de1a21ee_20260717T223757CST",
    "current_v25_atom_ledger_validation_artifact_root_sha256=a37fd179db35ab51b4ca08c99e669c3b62ecb5804a3679fafd9b35450d618352",
    "current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_r01_authority_source_de1a21ee_20260717T223757CST",
    "current_v25_r0_authority_source_artifact_root_sha256=e099837be509085fd761244ca676d387ee4debfe0214cf22057b631ba4dff1fa",
    "current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_r01_authority_source_review_de1a21ee_20260717T223757CST",
    "current_v25_r0_authority_source_review_artifact_root_sha256=e28c5851d15a0d313afe2f577c13ed9207686fa0a724d1738514675aae0fbb1e",
    "current_v25_r0_bounded_k8_artifact=/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_de1a21ee_20260717T223934CST",
    "current_v25_r0_bounded_k8_artifact_root_sha256=a520f86c2930fb3c2535efb730bf2e2a1b33db11c77f50535926f1971dbcf07c",
    "current_v25_r0_bounded_k8_review_artifact=/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_review_de1a21ee_20260717T225227CST",
    "current_v25_r0_bounded_k8_review_artifact_root_sha256=81a0c1acf7f5c5b76315659b7c917fb641013db20b5a130c27e2402a6560fb6b",
    "current_v25_a11_failed_validation_artifact_root_sha256=4d51394f8f4f61680fb65bd82062096fbaa72149862c4a6289f7f46927402b20",
    "current_v25_r01_failed_signature_artifact_root_sha256=b491a1fd8c82fd7165bf08763cc1e12f9a1bfe5e89cb7e2b6e8133a2f0958d87",
    "current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06",
    "current_v25_stage_a_atom_pass_count=9",
    "current_v25_stage_a_atom_warn_count=5",
    "current_v25_stage_a_atom_fail_count=0",
    "current_v25_stage_a_progress_reference=source_valid_candidate_set_reference",
    "current_v25_stage_a_progress_reference_frozen=true",
    "current_v25_stage_a_s01_per_atom_raw_statistics_available=false",
    "current_v25_a1_r0_local_test_result=90_passed_2_skipped_126_deselected_plus_67_passed_1_skipped",
    "current_v25_a1_r0_remote_test_result=68_passed_plus_23_passed_126_deselected",
    "current_v25_atom_schema=dp_camp_v10_14d",
    "current_v25_paper_subset=camp_legacy_v1_9d",
    "current_v25_context_schema=camp_dp_v25_causal_context_raw_v2",
    "current_v25_context_raw_feature_count=26",
    "current_v25_phi_dimension=53",
    "current_v25_scene_conditioned_mode=context_simplex_column_simplex_no_softmax_no_runtime_projection",
    "current_v25_normalization_contract=z_clip_raw_atom_over_scale_0_10",
    "current_v25_heading_norm_envelope_min=0.5",
    "current_v25_heading_norm_envelope_max=1.5",
    "current_v25_official_scenario_source_head=e22f01093fa6516c0552549ada302270329c59a4",
    "current_v25_controlled_pilot_case_count=147",
    "current_v25_controlled_pilot_passed_count=85",
    "current_v25_controlled_pilot_retained_failure_count=62",
    "current_v25_controlled_train_executable_identity_count=1500",
    "current_v25_controlled_train_source_ineligible_retained_count=153",
    "current_v25_combined_train_snapshot_capacity_at_64_ticks=163796",
    "current_v25_stopped_train_attempted_identity_count=122",
    "current_v25_stopped_train_complete_identity_count=121",
    "current_v25_stopped_train_failed_identity_count=1",
    "current_v25_stopped_train_snapshot_count=7748",
    "current_v25_stopped_train_illegal_partial_snapshot_count=4",
    "current_v25_stopped_train_all_k_high_risk_snapshot_count=1121",
    "current_v25_stopped_train_training_eligible=false",
    "current_v25_stopped_train_calibration_eligible=false",
    "current_v25_stopped_train_evaluation_eligible=false",
    "current_v25_fresh_b_identity_count=120",
    "current_v25_fresh_b_paired_run_count=600",
    "current_v25_fresh_b_independent_route_ceiling=24",
    "current_v25_fresh_b_independent_corridor_ceiling=3",
    "current_v25_fresh_b_v1_status=superseded_before_opening",
    "current_v25_fresh_b2_opened=false",
    "current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v4.json",
    "current_v25_stage_a_executed=true",
    "current_v25_stage_a1_executed=true",
    "current_v25_r0_source_executed=true",
    "current_v25_r0_bounded_k8_executed=true",
    "current_v25_r0_source_identity_count=21",
    "current_v25_r0_source_map_count=4",
    "current_v25_r0_probe_identity_count=22",
    "current_v25_r0_probe_tick_count=1408",
    "current_v25_r0_non_signal_identity_count=1",
    "current_v25_r0_physical_signature_count=9",
    "current_v25_r0_stop_line_geometry_sha256_count=5",
    "current_v25_corrected_full_corpus_started=false",
    "current_v25_full_config_preflight_started=false",
    "current_v25_full_r_authorized=false",
    "current_v25_old_monitor_status=deleted",
    "v24_legacy_benchmark_status=frozen_read_only_honest_no_claim",
    "v24_holdout_open_count=1",
    "v24_holdout_rerun_authorized=false",
    "current_v25_v24_holdout_read=false",
    "current_v25_fresh_benchmark_b_opened=false",
    "local_origin_github_autodl_aligned=true",
    "minimum_free_disk_gib=10",
    "observed_autodl_free_bytes=48252592128",
    "current_v25_phase=A1_1_R0_1_bounded_decision_package",
    "next_work_target=ultra_read_only_A1_1_R0_1_review_before_full_config_preflight_release",
)

PREVIOUS_POINTER = (
    "current_v25_status=v25_a164_static_source_plan_package_passed_ultra_bounded_execute_release_review_required",
    "current_v25_source_head=ac70c354fc9dcd8bfaadb97abc79392627f72cd9",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_ac70c354_20260718T150655CST",
    "current_v25_artifact_root_sha256=273a60489abc1c065ef4fe6112f07fd4c0309f1ee0f0e24a01f09efe061a9583",
    "current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_review_ac70c354_20260718T150655CST",
    "current_v25_review_artifact_root_sha256=f8debcc856a869f6f776e2a5ec88d8a3b3c41216f0338895fa1623c8cd36e6c6",
    "current_v25_a16_old_source_machine_authority_eligible=false",
    "current_v25_a16_old_source_scientific_diagnostic=true",
    "current_v25_a16_old_source_artifact_root_sha256=c93af9687c0c4c50e62d396311d3d10e0b8e953453186b0dde6b1aa21ecf51db",
    "current_v25_a16_old_source_review_artifact_root_sha256=0797f4dfbbe947eed7296249e0b904ed91cfde323f1e775f2e189100e3e2c73e",
    "current_v25_a161_failed_census_artifact=/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_census_4d0cfe6e_20260718T115300CST",
    "current_v25_a161_failed_census_root_sha256=1b8b2dfebaccd9e7071ff04f8e3b1f30c2f2af3677abac6bd02183a94c28064e",
    "current_v25_a161_failed_census_machine_authority_eligible=false",
    "current_v25_a161_failed_review_reason=source_census_report_exact_check_key_contract_drift",
    "current_v25_full_config_preflight_release_artifact=/root/autodl-tmp/camp_dp_v25_ultra_full_config_preflight_release_1e1c32c7_5f919a54290957e2",
    "current_v25_full_config_preflight_release_artifact_root_sha256=cb8733b4c81a2071a82c37caf74fa06586f51d7d9c1b7c3c0722f824029b33b1",
    "current_v25_full_config_preflight_consumed_nonce=5f919a54290957e2decfc662804db6ff320ca9582b62ea2869b67a13926fe37e",
    "current_v25_full_config_preflight_consumed_marker_sha256=0b62753b0b07ea987d78e309fde4ed9d9aeda5e2cf0b25d1107f7c446a1b864d",
    "current_v25_full_config_preflight_failure=non_red_identity_lacks_qualified_same_tick_mapped_signal_source",
    "current_v25_r05_failed_review_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053400CST",
    "current_v25_r05_failed_review_artifact_root_sha256=d3cf28b2f62814b89e9b6debace6e3f87a14d5a3b9c38eabd92a50e059b1cab5",
    "current_v25_s01_failed_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_e6ba79a2_20260717T184132CST",
    "current_v25_s01_failed_preflight_artifact_root_sha256=c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a",
    "current_v25_correction_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_retry_e6ba79a2_20260717T184256CST",
    "current_v25_correction_preflight_artifact_root_sha256=bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451",
    "current_v25_correction_preflight_review_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_review_e6ba79a2_20260717T184530CST",
    "current_v25_correction_preflight_review_artifact_root_sha256=facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d",
    "current_v25_correction_preflight_probe_count=3",
    "current_v25_correction_preflight_tick_count=192",
    "current_v25_correction_preflight_check_count=12",
    "current_v25_correction_preflight_review_check_count=28",
    "current_v25_correction_preflight_identity0_deterministic=true",
    "current_v25_correction_preflight_native_canonical_equal=true",
    "current_v25_correction_preflight_candidate_immutability=true",
    "current_v25_correction_preflight_candidate0_operational_default_alias=true",
    "current_v25_s01_remote_focused_test_count=65",
    "current_v25_s01_remote_pointer_test_count=10",
    "current_v25_stage_a0_failed_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_f40b6152_20260717T192912CST",
    "current_v25_stage_a0_failed_artifact_root_sha256=025dcd686ee44a681b14cc3ad8b5e64e885316b0f334d89096fda19d6cd8b810",
    "current_v25_stage_a0_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_01073398_20260717T193038CST",
    "current_v25_stage_a0_artifact_root_sha256=b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41",
    "current_v25_stage_a_superseded_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_v2_01073398_20260717T193052CST",
    "current_v25_stage_a_superseded_ledger_artifact_root_sha256=05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2",
    "current_v25_stage_a_superseded_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_v2_e07da58f_20260717T193156CST",
    "current_v25_stage_a_superseded_validation_artifact_root_sha256=e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72",
    "current_v25_ultra_stage_a_decision_artifact=/root/autodl-tmp/camp_dp_v25_ultra_stage_a15_r05_decision_1e1c32c7_20260718T051807CST",
    "current_v25_ultra_stage_a_decision_artifact_root_sha256=0f48f22861721258be945ae42fb10d3fec7f90992addb386c535a1b8001b3e5a",
    "current_v25_atom_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a15_1e1c32c7_20260718T051807CST",
    "current_v25_atom_ledger_artifact_root_sha256=5e762a14b53c6c81f6bb3bfa67c6aeeb7fa5fe603bb95fa0776d75035cb8311c",
    "current_v25_atom_ledger_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a15_1e1c32c7_20260718T051807CST",
    "current_v25_atom_ledger_validation_artifact_root_sha256=641fadb24926cb7e6fc49c98d66f6a0a9528f41856b0417aae9e6fb9a80fa469",
    "current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_census_ac70c354_20260718T150655CST",
    "current_v25_r0_authority_source_artifact_root_sha256=0541fbc52373e0851160e36da6d202153df26fa4dde26b9c8d3461554a9d72f3",
    "current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_review_ac70c354_20260718T150655CST",
    "current_v25_r0_authority_source_review_artifact_root_sha256=81c59e1babf8a82d4edbad64d22f8dcd6654425ea8f2d7d8dc975b2ee8866db3",
    "current_v25_r0_bounded_k8_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_1e1c32c7_20260718T051807CST",
    "current_v25_r0_bounded_k8_artifact_root_sha256=694ddcde9bd5972c4fb95eeb45da7f46663bb3a6acb87ca5b4cc18abbf97b79c",
    "current_v25_r0_bounded_k8_review_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053800CST",
    "current_v25_r0_bounded_k8_review_artifact_root_sha256=7dc54a3d9baa3d818284ffdcb3ed1192c0805d93ea7019c6975c86cba20fe47f",
    "current_v25_seven_root_bindings_sha256=4c3410f5c4f123e08e63a18cef10c366911fef7f454f74dbc2532d20db3dd396",
    "current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3",
    "current_v25_canonical_json_byte_spec=camp_dp_v25_canonical_json_utf8_lf_v1",
    "current_v25_execution_schema=camp_dp_v25_controlled_training_corpus_execution_v7",
    "current_v25_snapshot_schema=camp_dp_v25_controlled_train_snapshot_v7",
    "current_v25_route_source_receipts_schema=camp_dp_v25_a161_route_signal_source_receipts_v2",
    "current_v25_bounded_coverage_design_schema=camp_dp_v25_bounded_coverage_design_v1",
    "current_v25_bounded_execution_plan_schema=camp_dp_v25_a162_route_level_bounded_execution_plan_v2",
    "current_v25_a11_failed_validation_artifact_root_sha256=4d51394f8f4f61680fb65bd82062096fbaa72149862c4a6289f7f46927402b20",
    "current_v25_r01_failed_signature_artifact_root_sha256=b491a1fd8c82fd7165bf08763cc1e12f9a1bfe5e89cb7e2b6e8133a2f0958d87",
    "current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06",
    "current_v25_rejected_partial_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_491716fc_20260717T154959CST",
    "current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481",
    "current_v25_rejected_partial_review_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_review_491716fc_20260717T154959CST",
    "current_v25_rejected_partial_review_artifact_root_sha256=f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009",
    "current_v25_stage_a_atom_pass_count=9",
    "current_v25_stage_a_atom_warn_count=5",
    "current_v25_stage_a_atom_fail_count=0",
    "current_v25_stage_a_progress_reference=source_valid_candidate_set_reference",
    "current_v25_stage_a_progress_reference_frozen=true",
    "current_v25_stage_a_s01_per_atom_raw_statistics_available=false",
    "current_v25_a1_r0_local_test_result=132_v25_non_torch_passed_2_skipped",
    "current_v25_a1_r0_remote_test_result=165_v25_passed_after_A1_6_source_authority_sync",
    "current_v25_real_flock_test_result=1_passed",
    "current_v25_atom_schema=dp_camp_v10_14d",
    "current_v25_paper_subset=camp_legacy_v1_9d",
    "current_v25_context_schema=camp_dp_v25_causal_context_raw_v2",
    "current_v25_context_raw_feature_count=26",
    "current_v25_phi_dimension=53",
    "current_v25_scene_conditioned_mode=context_simplex_column_simplex_no_softmax_no_runtime_projection",
    "current_v25_normalization_contract=z_clip_raw_atom_over_scale_0_10",
    "current_v25_heading_norm_envelope_min=0.5",
    "current_v25_heading_norm_envelope_max=1.5",
    "current_v25_official_scenario_source_head=e22f01093fa6516c0552549ada302270329c59a4",
    "current_v25_controlled_pilot_case_count=147",
    "current_v25_controlled_pilot_passed_count=85",
    "current_v25_controlled_pilot_retained_failure_count=62",
    "current_v25_controlled_train_executable_identity_count=1500",
    "current_v25_controlled_train_source_ineligible_retained_count=153",
    "current_v25_combined_train_snapshot_capacity_at_64_ticks=163796",
    "current_v25_stopped_train_attempted_identity_count=122",
    "current_v25_stopped_train_complete_identity_count=121",
    "current_v25_stopped_train_failed_identity_count=1",
    "current_v25_stopped_train_snapshot_count=7748",
    "current_v25_stopped_train_illegal_partial_snapshot_count=4",
    "current_v25_stopped_train_all_k_high_risk_snapshot_count=1121",
    "current_v25_stopped_train_training_eligible=false",
    "current_v25_stopped_train_calibration_eligible=false",
    "current_v25_stopped_train_evaluation_eligible=false",
    "current_v25_fresh_b_identity_count=120",
    "current_v25_fresh_b_paired_run_count=600",
    "current_v25_fresh_b_independent_route_ceiling=24",
    "current_v25_fresh_b_independent_corridor_ceiling=3",
    "current_v25_fresh_b_v1_status=superseded_before_opening",
    "current_v25_fresh_b2_opened=false",
    "current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v6.json",
    "current_v25_stage_a_executed=true",
    "current_v25_stage_a1_executed=true",
    "current_v25_r0_source_executed=true",
    "current_v25_r0_bounded_k8_executed=true",
    "current_v25_r0_source_identity_count=21",
    "current_v25_r0_source_map_count=4",
    "current_v25_r0_probe_identity_count=22",
    "current_v25_r0_probe_tick_count=1408",
    "current_v25_r0_non_signal_identity_count=1",
    "current_v25_r0_physical_signature_count=9",
    "current_v25_r0_stop_line_geometry_sha256_count=5",
    "current_v25_a16_formal_train_identity_count=1653",
    "current_v25_a16_executable_identity_count=1500",
    "current_v25_a16_retained_identity_count=153",
    "current_v25_a16_mapped_signal_identity_count=146",
    "current_v25_a16_no_signal_identity_count=1354",
    "current_v25_a16_controlled_same_tick_override_count=21",
    "current_v25_a16_observe_same_tick_request_count=125",
    "current_v25_a16_source_failure_count=0",
    "current_v25_a16_source_only_no_model_simulator_candidate_dp_forward=true",
    "current_v25_a16_independent_review_passed=true",
    "current_v25_a161_local_non_torch_test_result=185_passed_2_skipped",
    "current_v25_a161_targeted_test_result=117_passed_1_skipped",
    "current_v25_a161_schema_regression_test_result=43_passed",
    "current_v25_a161_autodl_v25_test_result=193_passed",
    "current_v25_a161_pointer_test_result=18_passed",
    "current_v25_a161_windows_full_collection=torch_dll_abort_not_counted",
    "current_v25_a161_source_census_started=true",
    "current_v25_a161_source_census_completed=true",
    "current_v25_a161_source_review_started=true",
    "current_v25_a161_source_review_completed=true",
    "current_v25_a161_source_census_review_passed=true",
    "current_v25_a161_bounded_coverage_design_identity_count=243",
    "current_v25_a161_bounded_k8_executed=false",
    "current_v25_a162_source_artifact=/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_census_ac70c354_20260718T150655CST",
    "current_v25_a162_source_artifact_root_sha256=0541fbc52373e0851160e36da6d202153df26fa4dde26b9c8d3461554a9d72f3",
    "current_v25_a162_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_review_ac70c354_20260718T150655CST",
    "current_v25_a162_source_review_artifact_root_sha256=81c59e1babf8a82d4edbad64d22f8dcd6654425ea8f2d7d8dc975b2ee8866db3",
    "current_v25_a162_failed_unsealed_plan_artifact=/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_eafe96e4_20260718T130620CST",
    "current_v25_a162_failed_sealed_plan_artifact=/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_7e1d5be3_20260718T131240CST",
    "current_v25_a162_failed_sealed_plan_artifact_root_sha256=d1cdc934d385da3b53884a89b4e4d819740dac7f046f3dd167d495890872690a",
    "current_v25_a162_bounded_plan_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_ac70c354_20260718T150655CST",
    "current_v25_a162_bounded_plan_artifact_root_sha256=273a60489abc1c065ef4fe6112f07fd4c0309f1ee0f0e24a01f09efe061a9583",
    "current_v25_a162_bounded_plan_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_review_ac70c354_20260718T150655CST",
    "current_v25_a162_bounded_plan_review_artifact_root_sha256=f8debcc856a869f6f776e2a5ec88d8a3b3c41216f0338895fa1623c8cd36e6c6",
    "current_v25_a162_unique_identity_count=243",
    "current_v25_a162_run_count=244",
    "current_v25_a162_snapshot_capacity=15616",
    "current_v25_a162_tie_proof_count=4",
    "current_v25_a162_all_tie_proofs_equivalent=true",
    "current_v25_a162_identity0_repeat_positions=0,243",
    "current_v25_a162_local_targeted_test_result=123_passed_3_skipped",
    "current_v25_a162_autodl_targeted_test_result=126_passed",
    "current_v25_a162_pointer_test_result=18_passed",
    "current_v25_a162_bounded_k8_executed=false",
    "current_v25_a162_candidate_generation_started=false",
    "current_v25_a162_model_loaded=false",
    "current_v25_a162_simulator_started=false",
    "current_v25_a163_four_roots_machine_authority_eligible=false",
    "current_v25_a164_execution_assets_sha256=c59222c920dcb25e8ec18219f7eb683c0e9867f36c026e329e01a16c6cfb9c47",
    "current_v25_a164_four_root_bindings_sha256=365b18fcb914ce55d2dd934fffb7a173679f653c4e871ed95d00a75dd0c1c0ef",
    "current_v25_a164_local_targeted_test_result=136_passed_1_skipped",
    "current_v25_a164_autodl_targeted_test_result=137_passed",
    "current_v25_a164_bounded_release_created=false",
    "current_v25_a164_bounded_nonce_created=false",
    "current_v25_a164_bounded_k8_executed=false",
    "current_v25_corrected_full_corpus_started=false",
    "current_v25_full_config_preflight_release_created=true_diagnostic_consumed",
    "current_v25_full_config_preflight_started=true_failed_closed_before_receipts",
    "current_v25_full_r_authorized=false",
    "current_v25_monitor_started=false",
    "current_v25_worker_count=0",
    "current_v25_gpu_compute_count=0",
    "current_v25_lock_state=free",
    "current_v25_training_started=false",
    "current_v25_calibration_started=false",
    "current_v25_fresh_outcome_opened=false",
    "current_v25_old_monitor_status=deleted",
    "v24_legacy_benchmark_status=frozen_read_only_honest_no_claim",
    "v24_holdout_open_count=1",
    "v24_holdout_rerun_authorized=false",
    "current_v25_v24_holdout_read=false",
    "current_v25_fresh_benchmark_b_opened=false",
    "local_origin_github_autodl_aligned=true",
    "minimum_free_disk_gib=10",
    "observed_autodl_free_bytes=46918983680",
    "current_v25_phase=A1_6_4_bounded_authority_and_independent_reviewer_corrected_static_four_root_review_required_k8_closed",
    "next_work_target=ultra_read_only_A1_6_4_review_before_any_bounded_execute_release",
)

POINTER = (
    "current_v25_status=v25_a1611_r3_bounded_execution_failed_closed_ultra_result_review_required",
    "current_v25_source_head=0a07183913844dd9ab0c1e7c619c42be81c579ab",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_036bee497270ef5c",
    "current_v25_artifact_root_sha256=872982b9de4404ae1340235b9117dbcee2ef811563a89c699506972413e774fb",
    "current_v25_review_artifact=none_execution_failed_before_independent_review",
    "current_v25_review_artifact_root_sha256=none",
    "current_v25_a1611_bounded_plan_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_plan_0a071839_20260719T001726CST",
    "current_v25_a1611_bounded_plan_artifact_root_sha256=27bc6cd53da17535ab573016102d26d6d21d26b951bb16739d56bc5c8720b7b8",
    "current_v25_a1611_bounded_plan_review_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_plan_review_0a071839_20260719T001726CST",
    "current_v25_a1611_bounded_plan_review_artifact_root_sha256=44453e0ad2220b29bbd9bb473d41f927429a6ed899cecb6c1e990f8c8bcf96f4",
    "current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_route_signal_source_census_0a071839_20260719T001726CST",
    "current_v25_r0_authority_source_artifact_root_sha256=944f07399616f8870385827204ac2dcfef29637828e0a40112cb266a908aa3aa",
    "current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_route_signal_source_review_0a071839_20260719T001726CST",
    "current_v25_r0_authority_source_review_artifact_root_sha256=4bef57a9bcea8b911cbbf3880f2c29d575b5fc1c9696e222a587eae675c1a989",
    "current_v25_a16_formal_train_identity_count=1653",
    "current_v25_a16_executable_identity_count=1500",
    "current_v25_a16_retained_identity_count=153",
    "current_v25_a16_mapped_signal_identity_count=146",
    "current_v25_a16_no_signal_identity_count=1354",
    "current_v25_a16_controlled_same_tick_override_count=21",
    "current_v25_a16_observe_same_tick_request_count=125",
    "current_v25_a16_source_failure_count=0",
    "current_v25_a162_unique_identity_count=243",
    "current_v25_a162_run_count=244",
    "current_v25_a162_snapshot_capacity=15616",
    "current_v25_a162_identity0_repeat_positions=0,243",
    "current_v25_a169_four_roots_machine_authority_eligible=false",
    "current_v25_a1611_release_schema=camp_dp_v25_ultra_a1610_bounded_execute_release_v8",
    "current_v25_a1611_device=cuda",
    "current_v25_a1611_four_root_bindings_sha256=163c4fd7c67d924a27c7cf9b47ec986e915d3db1fe0f54ff10a7077fe344b5eb",
    "current_v25_a1611_four_roots_machine_authority_eligible=true_for_consumed_release_only",
    "current_v25_a1611_local_targeted_test_result=238_passed_5_skipped",
    "current_v25_a1611_autodl_targeted_test_result=243_passed",
    "current_v25_a1611_r2_status=fail_closed_stopped_before_test_execution",
    "current_v25_a1611_r2_nonce_status=permanently_revoked_unconsumed",
    "current_v25_a1611_r3_interpreter=/root/autodl-tmp/dp312_venv/bin/python",
    "current_v25_a1611_r3_interpreter_realpath=/root/miniconda3/bin/python3.12",
    "current_v25_a1611_r3_python_version=3.12.3",
    "current_v25_a1611_r3_pytest_version=8.3.5",
    "current_v25_a1611_bounded_release_created=true",
    "current_v25_a1611_bounded_release_artifact=/root/autodl-tmp/camp_dp_v25_ultra_a1611r3_bounded_execute_release_036bee497270ef5c",
    "current_v25_a1611_bounded_release_artifact_root_sha256=1b9e8b7d6587c816359c97a821324c6e411ab9d5b5e79064a824240ef990965e",
    "current_v25_a1611_bounded_nonce_created=true_consumed_once",
    "current_v25_a1611_bounded_nonce_marker_sha256=49f8558e444114d5ba65db3c22f0afb745090b8d44169ec586a9f7360726a1f5",
    "current_v25_a1611_bounded_k8_executed=started_not_accepted",
    "current_v25_a1611_bounded_execution_completed=false",
    "current_v25_a1611_bounded_execution_run_exit=1",
    "current_v25_a1611_bounded_execution_failure_type=ValueError",
    "current_v25_a1611_bounded_execution_failure_reason=bounded_scene_materialization_digest_drifted_before_projection",
    "current_v25_a1611_bounded_execution_accepted_run_count=0",
    "current_v25_a1611_bounded_execution_accepted_tick_count=0",
    "current_v25_a1611_bounded_independent_review_started=false",
    "current_v25_corrected_full_corpus_started=false",
    "current_v25_full_config_preflight_release_created=true_diagnostic_consumed",
    "current_v25_full_config_preflight_started=true_failed_closed_before_receipts",
    "current_v25_full_r_authorized=false",
    "current_v25_monitor_started=false",
    "current_v25_worker_count=0",
    "current_v25_gpu_compute_count=0",
    "current_v25_lock_state=free",
    "current_v25_training_started=false",
    "current_v25_calibration_started=false",
    "current_v25_fresh_outcome_opened=false",
    "current_v25_fresh_b2_opened=false",
    "local_origin_github_autodl_aligned=true",
    "minimum_free_disk_gib=10",
    "observed_autodl_free_bytes=46844665856",
    "current_v25_phase=A1_6_11_R3_bounded_execution_failed_closed_after_nonce_consumption_before_independent_review",
    "next_work_target=ultra_read_only_A1_6_11_R3_failed_bounded_execution_result_review_and_decision",
)

# The current pointer is deliberately reassigned here so the long historical
# tuple above remains a byte-visible regression record while the active reader
# contract tracks only the latest Fresh holdout state.
POINTER = (
    "current_v25_status=v25_fresh_b4_post_exposure_evaluation_control_fatal_honest_no_claim_terminal",
    "current_v25_execution_source_head=7be93df20deee03587b9898e8560909662df972c",
    "current_v25_execution_pointer_head=06d3a1f3a37061f93f5c9788312ae59d1356d126",
    "current_v25_reporting_machinery_head=77b735dcb24ed17e5a897f98f430ca1c536d787c",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v25_artifact=/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_terminal_closeout_7be93df2_8680c1b19ce0620b",
    "current_v25_artifact_root_sha256=a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398",
    "current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_fresh_b4_evaluation_terminal_closeout_review_7be93df2_8680c1b19ce0620b",
    "current_v25_review_artifact_root_sha256=86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062",
    "current_v25_b4_controller_root_sha256=06f2bf198b9983e0e15f9e0feaba52bc0d595fdd5703d73d98e21c1e8c4f08a2",
    "current_v25_b4_opening_release_root_sha256=7deec7b81a1ad20dd9eb4657c0c3066ce695bc797349def843c0e7152f85851b",
    "current_v25_b4_execution_root_sha256=e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881",
    "current_v25_b4_execution_review_root_sha256=f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
    "current_v25_b4_evaluation_artifact_created=false",
    "current_v25_b4_evaluation_root_sha256=none",
    "current_v25_b4_evaluation_review_started=false",
    "current_v25_b4_evaluation_review_root_sha256=none",
    "current_v25_b4_planned_pair_count=500",
    "current_v25_b4_complete_paired_row_count=500",
    "current_v25_b4_planned_arm_run_count=1500",
    "current_v25_b4_complete_arm_run_count=1500",
    "current_v25_b4_terminal_arm_run_count=1500",
    "current_v25_b4_tick_count=96000",
    "current_v25_b4_full_denominator_formed=true",
    "current_v25_b4_scientific_state=terminal_failure",
    "current_v25_b4_scientific_history=exposure_started,full_denominator_formed,terminal_failure",
    "current_v25_b4_scientific_terminal_reason=post_exposure_evaluation_control_fatal",
    "current_v25_b4_scientific_ledger_sha256=c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4",
    "current_v25_b4_raw_outcome_values_inspected=false",
    "current_v25_b4_claim_authorized=false",
    "current_v25_b4_rerun_allowed=false",
    "current_v25_b4_result_status=unavailable_due_to_post_exposure_evaluation_fatal",
    "current_v25_final_claim_decision=honest_no_claim",
    "current_v25_final_report=docs/diffusion_planner_v25_final_honest_no_claim_report.md",
    "current_v25_final_evidence_index=docs/diffusion_planner_v25_final_evidence_index.md",
    "local_origin_github_autodl_aligned=true",
    "current_v25_phase=fresh_b4_terminal_honest_no_claim_final_report_ready",
    "next_work_target=high_incremental_terminal_package_review_before_ultra",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _machine_tuple(section: str) -> dict[str, str]:
    lines = [
        line
        for line in section.splitlines()
        if re.fullmatch(r"[a-z][a-z0-9_]*=.*", line)
    ]
    result = dict(line.split("=", 1) for line in lines)
    assert len(result) == len(lines)
    return result


def _current_v25_section(text: str) -> str:
    heading = (
        "## Current V25 Status - Metric Semantics Amendment "
        "Independently Reviewed"
    )
    assert text.count("## Current V25 Status") == 1
    assert text.count(heading) == 1
    return text.split(heading, 1)[1].split(
        "## Historical V25 Status Through A1.6.11", 1
    )[0]


def _audit_v25_eof(text: str) -> str:
    heading = "## 2026-07-25 - Metric Semantics Amendment Independently Reviewed"
    assert text.count(heading) == 1
    return text.split(heading, 1)[1]


def test_v25_audit_ends_with_authoritative_pointer() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    pointer = _machine_tuple(_audit_v25_eof(text))
    assert pointer["current_v25_status"] == (
        "v25_metric_semantics_amendment_independently_reviewed_honest_no_claim"
    )
    assert pointer["current_v25_phase"] == (
        "metric_semantics_amendment_independently_reviewed_terminal"
    )
    assert text.rstrip().endswith(
        "next_work_target=high_metric_semantics_amendment_package_review"
    )


def test_current_status_has_one_v25_pointer_matching_audit() -> None:
    status_text = STATUS.read_text(encoding="utf-8")
    audit_text = AUDIT.read_text(encoding="utf-8")
    current_section = _current_v25_section(status_text)
    status_pointer = _machine_tuple(current_section)
    audit_pointer = _machine_tuple(_audit_v25_eof(audit_text))
    assert status_pointer == audit_pointer
    assert current_section.count("current_v25_status=") == 1
    assert (
        "current_v25_status="
        "v25_fresh_b4_post_exposure_evaluation_control_fatal_honest_no_claim_terminal"
    ) not in current_section
    assert "Preserved superseded engineering diagnostic" in current_section
    assert status_pointer["current_v25_final_corrected_report_sha256"] == _sha256(
        CORRECTED_FINAL_REPORT
    )
    assert status_pointer[
        "current_v25_final_corrected_evidence_index_sha256"
    ] == _sha256(CORRECTED_FINAL_INDEX)
    assert status_pointer["current_v25_metric_semantics_report_sha256"] == _sha256(
        METRIC_SEMANTICS_REPORT
    )
    assert status_pointer[
        "current_v25_metric_semantics_evidence_index_sha256"
    ] == _sha256(METRIC_SEMANTICS_INDEX)


def test_v25_corrected_evaluation_eof_and_reports_are_consistent() -> None:
    status = STATUS.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    report = CORRECTED_FINAL_REPORT.read_text(encoding="utf-8")
    index = CORRECTED_FINAL_INDEX.read_text(encoding="utf-8")
    normalized_report = " ".join(report.split())
    status_pointer = _current_v25_section(status)
    audit_eof = _audit_v25_eof(audit)
    required = (
        "7be93df20deee03587b9898e8560909662df972c",
        "06d3a1f3a37061f93f5c9788312ae59d1356d126",
        "7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881",
        "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
        "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f",
        "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459",
        "c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4",
        "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392",
        "7c01cd9ea5176da889186d3beffec38d6e9ab5d04e40d3fa2b4a47eea8713437",
        "58c241ec562a570c72f3d96bc2b85e32079f367e9d9d2e30e2835b20e49f8205",
        "honest_no_claim_under_frozen_preregistered_all_gate",
    )
    for phrase in required:
        assert phrase in status_pointer
        assert phrase in audit_eof
        assert phrase in report
        assert phrase in index
    assert audit.rstrip().endswith(
        "next_work_target=high_metric_semantics_amendment_package_review"
    )
    assert "| 1 | 14D atom table |" in index
    assert "| 11 | Provenance, claim boundary, paper-grade report |" in index
    assert "Fresh execution rerun: `false`" in report
    assert "Static14D safety_improvement_claim_passed=false" in report
    assert "Scene14D safety_improvement_claim_passed=false" in report
    assert "overall and within each independent inference cluster" in normalized_report
    assert (
        "does not claim exact balance within every scenario family"
        in normalized_report
    )
    assert "101/101" in index
    assert "102/102" in index
    for text in (status_pointer, audit_eof, report, index):
        assert "literal-oracle" not in text
        assert (
            "separate-role sealed deterministic replay using the frozen "
            "canonical evaluation core"
        ) in " ".join(text.split())
    pointer = _machine_tuple(status_pointer)
    assert pointer["current_v25_b4_evaluation_review_mode"] == (
        "separate_role_sealed_deterministic_replay_frozen_canonical_evaluation_core"
    )
    assert pointer[
        "current_v25_b4_reviewer_local_independent_statistical_implementation_claimed"
    ] == "false"


def test_v25_corrected_latency_checklist_uses_sealed_complete_summaries() -> None:
    report = CORRECTED_FINAL_REPORT.read_text(encoding="utf-8")
    normalized_report = " ".join(report.split())
    index = CORRECTED_FINAL_INDEX.read_text(encoding="utf-8")
    status_pointer = _machine_tuple(
        _current_v25_section(STATUS.read_text(encoding="utf-8"))
    )
    expected_cells = (
        "51.985414/51.472995/54.386444/56.967885/401.075010",
        "358.990532/358.009244/373.918668/388.722123/461.924196",
        "35.932418/26.206801/93.213820/139.693299/255.957926",
        "3.169737/3.147744/3.300608/3.704798/11.938545",
        "0.284847/0.281420/0.301724/0.361152/2.773259",
        "0.199182/0.197558/0.209259/0.243650/1.084602",
        "68.800894/68.348749/72.232599/75.897811/518.258393",
        "531.782756/518.678487/607.223826/755.545621/993.904560",
        "536.456213/522.531789/613.830395/755.155321/1072.831110",
    )
    for cell in expected_cells:
        assert cell in report
    assert "mean/median/p95/p99/max" in normalized_report
    assert "no raw row was read" in normalized_report
    assert "zero-valued placeholders" in normalized_report
    assert (
        "n/a (candidate0 does not invoke the additional-K8 branch)"
        in normalized_report
    )
    assert "n/a (Static14D has no scene-context stage)" in normalized_report
    assert (
        "| 9 | Latency | complete from sealed corrected-evaluation summary |"
        in index
    )
    assert status_pointer["current_v25_b4_latency_summary_source"] == (
        "sealed_corrected_evaluation_summary"
    )
    assert status_pointer["current_v25_b4_latency_raw_rows_read_for_reporting"] == (
        "false"
    )
    assert status_pointer["current_v25_b4_latency_summary_metrics"] == (
        "mean,median,p95,p99,max"
    )
    assert status_pointer["current_v25_b4_latency_checklist_complete"] == "true"


def test_v25_metric_semantics_amendment_is_additive_and_fail_closed() -> None:
    report = METRIC_SEMANTICS_REPORT.read_text(encoding="utf-8")
    index = METRIC_SEMANTICS_INDEX.read_text(encoding="utf-8")
    current = _current_v25_section(STATUS.read_text(encoding="utf-8"))
    audit_eof = _audit_v25_eof(AUDIT.read_text(encoding="utf-8"))
    pointer = _machine_tuple(current)

    assert _machine_tuple(audit_eof) == pointer
    assert pointer["current_v25_metric_semantics_schema"] == (
        "camp_dp_v25_metric_semantics_amendment_v1"
    )
    assert pointer["current_v25_metric_semantics_report_sha256"] == _sha256(
        METRIC_SEMANTICS_REPORT
    )
    assert pointer[
        "current_v25_metric_semantics_evidence_index_sha256"
    ] == _sha256(METRIC_SEMANTICS_INDEX)
    assert pointer["current_v25_metric_semantics_filtered_samples_per_run"] == "52"
    assert pointer["current_v25_metric_semantics_per_run_before_pair_and_cluster"] == (
        "true"
    )
    assert pointer["current_v25_metric_semantics_new_ni_or_claim_gate"] == "false"
    assert pointer["current_v25_metric_semantics_sealed_source_artifacts_written"] == (
        "false"
    )
    assert pointer[
        "current_v25_metric_semantics_scientific_or_continuation_cas_written"
    ] == "false"
    assert pointer[
        "current_v25_metric_semantics_industrial_occupant_comfort_status"
    ] == "evidence_missing_not_assessed"

    roots = (
        "318e85f9656a5dd79c9fb0ad6c1dfcd94678b35c4aba455f3909cf3475cca758",
        "fc04fd6e45487df6c9bf5313b9ee6d633f91303e0a1aa00f0a3114b8134fea95",
        "99fd5e571160a3ac3d5bb2b6d6f3391c3da5965bf592707ff85c88080ac2dbcf",
        "88b35ab8ef51807c848200675ceeebe6b26e15a4f4b34da51f131e9303f37898",
        "896fa3858a427462ecd4d3b206208605864fb34f3a4a5dd43ca723ec30445e95",
        "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392",
    )
    for root in roots:
        assert root in report
        assert root in index
        assert root in current
        assert root in audit_eof

    exact_terms = (
        "legacy_project_defined_controlled_benchmark_safetycost",
        "noncollision_obb_clearance_le_2m_tick_rate",
        "five_point_drivable_coverage_failure_tick_rate",
        "nearest_route_segment_heading_opposition_moving_onroad_tick_rate",
        "certified_red_phase_stopline_crossing_gt_0_5mps_any",
        "onroad_speed_excess_gt_0_1mps_tick_rate",
        "final_nearest_route_polyline_projection_m",
        "clipped_final_route_projection_fraction",
        "raw_longitudinal_speed_second_difference_chatter_diagnostic",
        "raw_speed_times_heading_rate_lateral_kinematic_diagnostic",
        "raw_same_tick_scalar_speed_drop_peak_deceleration_diagnostic",
        "vehicle_body_kinematic_comfort_proxy",
        "filtered_vehicle_body_acceleration",
        "evidence_missing_not_assessed",
        "honest_no_claim_under_frozen_preregistered_all_gate",
    )
    combined = report + "\n" + index
    normalized_combined = " ".join(combined.split())
    for term in exact_terms:
        assert term in combined

    for class_value in ("PASS", "benchmark-only", "FAIL-industrial", "evidence-missing"):
        assert class_value in report
        assert class_value in index
    for boundary in (
        "64->63->62->52",
        "not industrial comfort",
        "not a comfort gate",
        "Fresh rerun=false",
        "corrected-evaluation rerun=false",
        "scientific or continuation CAS written=false",
    ):
        assert boundary in normalized_combined
    assert "real-road safety" in normalized_combined
    assert "production-readiness claim is authorized" in normalized_combined


def test_v25_training_and_independent_review_are_accepted_before_calibration() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Fair Static/Scene 14D Training and Independent Review PASS",
        "same 95,616 rows",
        "Static14D and Scene14D are the two primary methods",
        "Static9D and Scene9D are paper-subset ablations",
        "context_q05[19]=neighbor_closing_speed_mps",
        "34 Static14D, 16 Scene14D, 40 Static9D, and one Scene9D",
        "active-cut envelope gap is not the frozen optimized-master-loss gap",
        "all 38 focused scene/training tests",
        "ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9",
        "Calibration, Scene runtime, V2I, Fresh B2, and outcome evaluation remain closed",
    ):
        assert phrase in text


def test_v25_calibration_recovery_is_reviewed_without_a_safety_claim() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Paired Calibration Recovery and Independent Review PASS",
        "300/300 arms before its terminal analyzer failed closed",
        "input_materialization",
        "No arm was rerun",
        "5cd071b6ac9dd805422d7fe572f3db273abe9fce5cd4f910a0cf6fa9296e8249",
        "9d67e57bfa4a96ff3bf318c5aafd17f024207645344f076963fc5f756caa6551",
        "650e6749bda63f23b073a5491c0f57dd9f97136a644be8ab7c918a48a3f609f7",
        "e6f8cf6cb37c3acd964502f04c12a6e15af1fb3d946048ea4abc18c8741f5d55",
        "235a99323be75476b7d8d31d9458ddd6f583d6a5d6593901e492addfe40c69e6",
        "100 paired units and 300/300 complete arms",
        "CAMP-Static14D | 17.6921953923 | -1.5290645589",
        "CAMP-Scene14D no-V2I | 18.4856536131 | -0.7356063381",
        "all-NI gate is false for both primary CAMP methods",
        "All 14 approved atoms are PASS",
        "Fresh B2 and all Fresh outcomes remain unopened",
        "does not authorize a V25 safety claim",
    ):
        assert phrase in text


def test_v25_fresh_b2_preopen_authority_is_reviewed_and_stays_unopened() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Fresh B2 Consolidated Outcome-Blind Pre-Open Authority and Independent Review PASS",
        "25 immutable project-authored MIT Lanelet2 maps",
        "500 paired units, 1,500 balanced three-arm runs",
        "All 100 static regulatory-element -> physical light/bulbs",
        "1,500 train, 50 calibration, and 100 Fresh route rows",
        "69,991,287,914",
        "12,800 accepted calibration decision ticks",
        "38cf4d4837cd018b463e4044f34020bd57c1eefb176a11e565d6b1ef3594228d",
        "09f67b804bb880a861682b87f2a577fad658505a26ba65005b3a9c074a3fd802",
        "fresh_open_authorized=false",
        "outcome_fields_consumed=[]",
        "Ultra's final one-time Fresh B2 opening release review",
    ):
        assert phrase in text


def test_v25_a17_failure_regression_matrix_has_all_ten_machine_checks() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert "## A1.7 one-time failure-regression control matrix" in text
    signatures = (
        "stale_heartbeat_exited_worker",
        "readonly_parent_misread_as_capacity",
        "logical_vs_allocated_or_hardlink_confusion",
        "external_legacy_json_forced_canonical",
        "operator_short_sha_or_interpreter_realpath_assertion",
        "formal_nonce_consumed_before_real_entry_pass",
        "docs_pointer_vs_live_implementation_drift",
        "scenario_family_drives_signal_source",
        "confirmed_unused_artifact_archived_locally",
        "unchanged_status_visible_polling",
    )
    for signature in signatures:
        assert text.count(f"`{signature}`") == 1
    for column in (
        "Failure signature",
        "Current forbidden behavior",
        "Unique machine check",
        "Regression test or command",
    ):
        assert column in text


def test_v24_authority_files_remain_byte_frozen() -> None:
    assert _sha256(V24_AUDIT) == (
        "cd9a33655e1919182f33256dd07d3bd7a6bdbe7fd8aab1107199859ccf39f228"
    )
    assert _sha256(V24_PAIRED_CONFIG) == (
        "9dc0ab9415239211f16e65495362d83c2a11ffe04a96f4ddd2881b12fc193c0f"
    )


def test_v25_startup_record_bounds_legacy_evidence_and_baseline_language() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "Legacy Benchmark A",
        "67,796 causal K=8 snapshots",
        "1,054 complete and 821 retained failures",
        "lane_deviation, clearance, and dp_prior_jerk_excess_cost",
        "only near_miss_noncollision_rate had a nonzero primary-component delta",
        "candidate 0 is the DP operational default",
        "not native-ranked Top-1",
        "must not tune V25 atoms, weights, thresholds, margins, or sample composition",
    ):
        assert phrase in text


def test_v25_phase2_atom_context_audit_is_sealed_and_bounded() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Phase 2: Atom and Causal-Context Audit/Freeze",
        "67,796 snapshots and 542,368 candidate rows",
        "4 high-redundancy pairs",
        "candidate 0 DP operational-default reference",
        "native ranking is not claimed",
        "26 raw features",
        "53-dimensional complement-lift",
        "candidate_source_valid_fraction was exactly 1.0",
        "phase 3 outcome-blind capability pilot",
        "5135bebe8a78942fb91ec72957db5e0386b15f99bcf4e8bca35be2a98d00241c",
    ):
        assert phrase in text


def test_v25_phase3_scene_conditioned_capability_is_sealed_and_bounded() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Phase 3: Scene-Conditioned CAMP and Capability Pilot",
        "35 outcome-blind current-request cases",
        "all 26 raw features varied",
        "every column of Theta is a nonnegative simplex",
        "strict CLARABEL",
        "17 passed",
        "d2b88b7f6d91b9b7465a37d8bb00c1b46e8ef1a5fd1bef30e97be712caafbf08",
        "not a trained or calibrated model",
        "does not establish scene-conditioned utility or safety improvement",
    ):
        assert phrase in text


def test_v25_phase4_controlled_protocol_is_sealed_and_bounded() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Phase 4: Controlled Scenario Corpus and Split Freeze",
        "All 147 attempts were retained: 85 passed and 62 remained failed",
        "61 routes without a complete positive speed-limit source",
        "all 401 inventory routes",
        "1,500 executable controlled-train identities",
        "153 source-ineligible retained train records",
        "163,796-snapshot training capacity",
        "exactly 600 three-arm paired runs",
        "only 24 independent routes across three corridor groups",
        "Fresh B has no legal mapped-signal source",
        "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531",
    ):
        assert phrase in text


def test_v25_ultra_correction_gate_stops_and_quarantines_invalid_corpus() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Phase 5: Ultra Scientific-Contract Correction Gate",
        "122 attempted identities, 121 complete identities, one failed identity",
        "7,748 snapshots",
        "four illegal partial snapshots",
        "1,121 all-K-high-risk snapshots",
        "clip(a/s, 0, 10)",
        "superseded before opening",
        "a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481",
        "f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009",
    ):
        assert phrase in text


def test_v25_s0_correction_preflight_is_sealed_and_waits_for_ultra() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Phase 5 S0: Correction/Preflight Decision Package",
        "all 12 checks over 192 ticks",
        "passed all 18 checks",
        "839, 839, and 1,536 raw atom values above 10 times scale",
        "Stage A and R are both unexecuted",
        "d76a772ff15497a13e72538382a99e1027fb9ef53561270523bdc8975afc4fa9",
        "2465fa31b52891ab9130a47bc6f77d1191a83be807eb8b7f2c31c8c8ef1f3138",
        "configs/integrations/diffusion_planner_v25_atom_ledger_plan_v2.json",
        "ultra_read_only_review_required_before_stage_A_or_R",
    ):
        assert phrase in text


def test_v25_s01_authority_correction_is_sealed_and_waits_for_ultra() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Phase 5 S0.1: Fail-Closed Authority Correction",
        "undefined `positive_inf`",
        "passed all 28 checks",
        "65 focused correctness tests plus 10 pointer tests",
        "candidate0 is the operational-default alias from the same forward",
        "Stage A=false, R=false",
        "c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a",
        "bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451",
        "facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d",
        "The next gate is Ultra's read-only S0.1",
    ):
        assert phrase in text


def test_v25_stage_a_ledger_is_sealed_independent_and_stops_before_r() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Stage A: Static 14D Atom Ledger and Independent Validation",
        "8 PASS, 6 WARN, 0 FAIL",
        "did not import producer score results",
        "jerk_full=jerk_early+jerk_late",
        "source_valid_candidate_set_reference",
        "21/21 retained capability failures",
        "b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41",
        "05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2",
        "e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72",
        "ultra_read_only_stage_A_review_and_progress_reference_decision_before_R",
    ):
        assert phrase in text


def test_v25_stage_a1_r0_is_sealed_independent_and_stops_before_full_r() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Stage A1/R0: Frozen Semantics, Signal Authority, and Bounded K8 Preflight",
        "9 PASS, 5 WARN, 0 FAIL",
        "source_valid_candidate_set_reference",
        "all 21 formal red identities over four source maps",
        "one easy, one borderline, and one high-risk red identity",
        "exactly 64 ticks each",
        "full R, a 1,500-identity worker/monitor, training, calibration, Scene runtime, V2I, and Fresh remained closed",
        "f8ecaf1a9235753245cad736cef4172e8a553143a0eff45bf179add2b4ecdac5",
        "c8b8b926bd63a0a8185d7ea3f422e7b94bc0c40921560e6576ac9e4b0ca786e9",
        "e948eb17e3561a93c803ec8485d725d47e341b129a794bcf1c2c6e9593cef946",
        "ultra_read_only_A1_R0_review_before_full_R",
    ):
        assert phrase in text


def test_v25_stage_a11_r01_is_sealed_independent_and_stops_before_full_config() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Stage A1.1/R0.1: Stop-Line Authority, Cross-Map Correctness, and Full Bounded Coverage",
        "nine SE(2)-invariant source/ID-independent physical signatures",
        "22 identities and 1,408 ticks",
        "process-local no-ROS Lanelet2 projector retained the previous source-map origin",
        "d98929000c09cbe1f3bcdc7f57290091e0be31e67726f4920d201bc98292897e",
        "836d5468fd05cdbd837037352d14cd20fb21a6b653ece41272bb85b30c42ad82",
        "e099837be509085fd761244ca676d387ee4debfe0214cf22057b631ba4dff1fa",
        "a520f86c2930fb3c2535efb730bf2e2a1b33db11c77f50535926f1971dbcf07c",
        "81a0c1acf7f5c5b76315659b7c917fb641013db20b5a130c27e2402a6560fb6b",
        "ultra_read_only_A1_1_R0_1_review_before_full_config_preflight_release",
    ):
        assert phrase in text


def test_v25_semantic_v3_and_full_r_authority_correction_is_bounded() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Stage A1.1/R0.1 Semantic-v3 and Full-R Authority Correction",
        "93 of the 201 audited rotations mismatched",
        "route-local heading unit vector",
        "raw atom column 12",
        "unique nonce and exact output directory",
        "deliberately minimal self-signed 1,500-ID artifact is rejected",
        "0c84450c216032686d667209b781cc9b39e68554fd5868eac0aaf0ef725e37ff",
        "b7dc7fe00d21af71caba172eac9edf5500fb967e7379b712024600c62b9e5458",
        "6eee9f157d1668ad37120b3a9542f1e5b5661f9077b0fb15cdb5e4a4b43f35d2",
        "full-config preflight remains blocked until an explicit separate release",
    ):
        assert phrase in text


def test_v25_a13_r03_canonical_writer_and_exact_authority_are_bounded() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Stage A1.3/R0.3 Canonical Snapshot and Exact Authority Correction",
        "real snapshot writer",
        "exactly one trailing LF",
        "one-identity, 64-tick write/read/index/seal regression",
        "1,653 train rows: 1,500 executable plus 153 retained-ineligible",
        "seed 25001",
        "1b2dd591e342fdfa0d88f05a2d2537bc8f51292d71502a22e701147cee15488c",
        "50ae46bb76f76e07bac6a91405e30cade7bdfd715cf417a6e7d5931cdaaa3878",
        "c07e1c4cd63db8aaa21118925e7a78bbb2b6c1687ecbaf4939047057863979b1",
        "4c9a4a666506195aef0ff556858a1fda942cf094c9824abdde827e47e83cc9f5",
        "all 150 integration tests",
        "full-config preflight remains blocked until an explicit separate Ultra release",
        "ultra_read_only_A1_3_R0_3_review_before_full_config_preflight_release",
    ):
        assert phrase in text


def test_v25_a14_r04_type_exact_authority_and_snapshot_schema_are_bounded() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Stage A1.4/R0.4 Type-Exact Authority and Snapshot Schema Correction",
        "recursive JSON-native type equality",
        "hash(actual receipts)",
        "config_authority_sha256",
        "future/outcome/label/holdout/ID-proxy fields",
        "contract_checks.r_and_fresh_closed",
        "baaf879f1eac5579a1029c2eb046dc125d8c82e7677f904b2b41dd8bfcd00947",
        "1afd6ccfe1dda380be1b3d912515cb112e8c315e1cf9a9a1e45bbbe069666106",
        "55ff4688dc4926348e26b8e9e161f4203c816eb8829dea974396f4f0aaa32b88",
        "6fc039adb7aa21bed58a8ca6aa97dae944332566b37b471be015a4a7a933e066",
        "all `134` V25 tests",
        "Full-config preflight remains blocked",
        "ultra_read_only_A1_4_R0_4_review_before_full_config_preflight_release",
    ):
        assert phrase in text


def test_v25_a15_r05_nested_control_and_corpus_schema_are_bounded() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Stage A1.5/R0.5 Nested-Control, Corpus-Schema, and Release-Authority Correction",
        "all five `a11_validation.contract_checks` keys",
        "snake_case, camelCase, and hyphenated spellings",
        "Actual receipts, independently rebuilt receipts, and the reported root",
        "exact 26-feature raw-context/source-completeness keys",
        "native 64-hex strings",
        "Critical-manifest raw keys",
        "0f48f22861721258be945ae42fb10d3fec7f90992addb386c535a1b8001b3e5a",
        "694ddcde9bd5972c4fb95eeb45da7f46663bb3a6acb87ca5b4cc18abbf97b79c",
        "7dc54a3d9baa3d818284ffdcb3ed1192c0805d93ea7019c6975c86cba20fe47f",
        "4c3410f5c4f123e08e63a18cef10c366911fef7f454f74dbc2532d20db3dd396",
        "all 139 V25 tests",
        "No full-config release nonce or output",
        "The next gate is Ultra read-only A1.5/R0.5 review",
    ):
        assert phrase in text


def test_v25_a16_r06_source_census_and_independent_review_are_bounded() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Stage A1.6/R0.6 Route-Level Signal-Authority Source-Only Correction",
        "53b07e309c03d8d0a491121b4b135f80fccbbc3d",
        "all 165 V25 tests",
        "c93af9687c0c4c50e62d396311d3d10e0b8e953453186b0dde6b1aa21ecf51db",
        "0797f4dfbbe947eed7296249e0b904ed91cfde323f1e775f2e189100e3e2c73e",
        "all 1,653 formal train identities",
        "1,500 executable and 153 retained",
        "146 mapped-signal routes and 1,354 no-signal routes",
        "21 controlled-same-tick overrides plus 125 observed-same-tick request phases",
        "Source failures are zero",
        "Neither loaded a model, started a simulator, generated a candidate, executed a DP forward",
        "Bounded K8 and all later gates remain closed",
        "ultra_read_only_A1_6_R0_6_source_package_review_before_bounded_coverage_gate",
    ):
        assert phrase in text


def test_v25_b4_terminal_pointer_and_honest_no_claim_report_are_consistent() -> None:
    status = " ".join(
        _current_v25_section(STATUS.read_text(encoding="utf-8")).split()
    )
    audit = " ".join(AUDIT.read_text(encoding="utf-8").split())
    report = " ".join(FINAL_REPORT.read_text(encoding="utf-8").split())
    index = " ".join(FINAL_INDEX.read_text(encoding="utf-8").split())
    preserved = (
        "7be93df20deee03587b9898e8560909662df972c",
        "06d3a1f3a37061f93f5c9788312ae59d1356d126",
        "77b735dcb24ed17e5a897f98f430ca1c536d787c",
        "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881",
        "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
        "a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398",
        "86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062",
        "c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4",
        "post_exposure_evaluation_control_fatal",
    )
    old_terminal_only = (
        "Fresh B4 Post-Exposure Evaluation-Control Fatal and Honest-No-Claim Terminal",
        "unavailable_due_to_post_exposure_evaluation_fatal",
        "honest_no_claim",
        "current_v25_b4_complete_paired_row_count=500",
        "current_v25_b4_complete_arm_run_count=1500",
        "current_v25_b4_terminal_arm_run_count=1500",
        "current_v25_b4_full_denominator_formed=true",
        "current_v25_b4_raw_outcome_values_inspected=false",
        "current_v25_b4_claim_authorized=false",
        "current_v25_b4_rerun_allowed=false",
        "next_work_target=high_incremental_terminal_package_review_before_ultra",
    )
    for phrase in preserved:
        assert phrase in status
        assert phrase in audit
        assert phrase in report
        assert phrase in index
    for phrase in old_terminal_only:
        assert phrase in audit
    for phrase in old_terminal_only[1:3]:
        assert phrase in report
        assert phrase in index
    assert (
        "current_v25_status="
        "v25_fresh_b4_post_exposure_evaluation_control_fatal_honest_no_claim_terminal"
    ) not in status
    assert "Preserved superseded engineering diagnostic" in status
    assert "## Eleven-item acceptance checklist" in index
    assert index.count("| 1 |") == 1
    assert index.count("| 11 |") == 1
    assert "No V25 scientific claim is authorized." in report
