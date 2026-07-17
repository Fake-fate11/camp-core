from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v25_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"
V24_AUDIT = ROOT / "docs" / "diffusion_planner_v24_iteration_audit.md"
V24_PAIRED_CONFIG = (
    ROOT / "configs" / "integrations" / "diffusion_planner_v24_paired_evaluation.json"
)

POINTER = (
    "current_v25_status=v25_s01_correction_preflight_passed_ultra_read_only_review_required",
    "current_v25_source_head=e6ba79a229ea3cc8e3a69d776ea1913cff8e3279",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v25_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_491716fc_20260717T154959CST",
    "current_v25_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481",
    "current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_review_491716fc_20260717T154959CST",
    "current_v25_review_artifact_root_sha256=f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009",
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
    "current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v2.json",
    "current_v25_stage_a_executed=false",
    "current_v25_corrected_full_corpus_started=false",
    "current_v25_old_monitor_status=deleted",
    "v24_legacy_benchmark_status=frozen_read_only_honest_no_claim",
    "v24_holdout_open_count=1",
    "v24_holdout_rerun_authorized=false",
    "current_v25_v24_holdout_read=false",
    "current_v25_fresh_benchmark_b_opened=false",
    "local_origin_github_autodl_aligned=true",
    "minimum_free_disk_gib=10",
    "observed_autodl_free_bytes=48497549312",
    "current_v25_phase=S0_1_correction_preflight_decision_package",
    "next_work_target=ultra_read_only_S0_1_review_required_before_stage_A_or_R",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v25_audit_ends_with_authoritative_pointer() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert text.rstrip().endswith("\n".join(POINTER))


def test_current_status_has_one_v25_pointer_matching_audit() -> None:
    text = STATUS.read_text(encoding="utf-8")
    assert text.count("## Current V25 Status") == 1
    section = text.split("## Current V25 Status", 1)[1].split(
        "## Current V24 Status", 1
    )[0]
    for line in POINTER:
        assert section.count(line) == 1


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
        "ultra_read_only_S0_1_review_required_before_stage_A_or_R",
    ):
        assert phrase in text
