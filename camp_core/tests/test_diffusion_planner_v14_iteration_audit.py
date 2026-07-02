from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = ROOT / "docs" / "diffusion_planner_v14_iteration_audit.md"
CURRENT_STATUS_DOC = ROOT / "docs" / "diffusion_planner_current_status.md"
README = ROOT / "README.md"


def test_v14_audit_rollover_is_current_eof() -> None:
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

    latest_status = text.rsplit("current_v14_status=", maxsplit=1)[1].splitlines()[0]
    latest_target = text.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert (
        latest_status
        == "approved_source_manifest_remediation_rejected_no_valid_nonfixture_dp_native_npz_source_or_manifest"
    )
    assert (
        latest_target
        == "external_valid_nonfixture_dp_native_npz_source_manifest_required_before_fixed_dp_candidate_generation_execution"
    )


def test_v14_approved_source_manifest_remediation_rejected_no_nonfixture_source_is_eof() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")
    previous_section_title = "## Current V14 Audit Rollover"
    section_title = (
        "## Current V14 Approved Source Manifest Remediation Validated "
        "Rejected No Nonfixture DP-Native Source After 040f1f0"
    )

    assert text.count(section_title) == 1
    assert text.rfind(section_title) > text.rfind(previous_section_title)
    assert "\n## " not in text[text.rfind(section_title) + len(section_title) :]

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

    latest_status = text.rsplit("current_v14_status=", maxsplit=1)[1].splitlines()[0]
    latest_target = text.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert (
        latest_status
        == "approved_source_manifest_remediation_rejected_no_valid_nonfixture_dp_native_npz_source_or_manifest"
    )
    assert (
        latest_target
        == "external_valid_nonfixture_dp_native_npz_source_manifest_required_before_fixed_dp_candidate_generation_execution"
    )


def test_current_status_and_readme_point_to_v14() -> None:
    status_text = CURRENT_STATUS_DOC.read_text(encoding="utf-8")
    readme_text = README.read_text(encoding="utf-8")

    assert "docs/diffusion_planner_v14_iteration_audit.md" in status_text
    assert "do not keep appending current\nwork to v13" in status_text
    assert "040f1f007d4f972f52d49d0155466e073ada7b6b" in status_text
    assert "7a1d33da277a1992ec474b5383a0c963c72e04e4" in status_text
    assert (
        "external_valid_nonfixture_dp_native_npz_source_manifest_required_before_fixed_dp_candidate_generation_execution"
        in status_text
    )

    assert "docs/diffusion_planner_current_status.md" in readme_text
    assert "docs/diffusion_planner_v14_iteration_audit.md" in readme_text
    assert "v14 rollover source" in readme_text
