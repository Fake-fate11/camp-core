from __future__ import annotations

import hashlib
import json
from pathlib import Path

from camp_core.integrations.diffusion_planner_v25_context import RAW_FEATURE_NAMES
from camp_core.integrations.diffusion_planner_v25_evaluation import (
    ARMS,
    LATENCY_STAGES,
    SIGNAL_SAFETY_METRICS,
    STATUSES,
)
from camp_core.integrations.diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
    REQUIRED_CONTROLLED_EVENT_FAMILIES,
    SAFETY_COMPONENTS,
)
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (
    ATOM_NAMES,
    DEFAULT_ABLATION_GROUPS,
    PAPER_9D_INDICES,
)
EXPECTED_SHA256 = "2241c66b74fb1478455630dd3a7295f24608bf14efc8544bbc0e755f8dd990cb"


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _path() -> Path:
    return (
        _root()
        / "configs"
        / "integrations"
        / "diffusion_planner_v25_final_delivery_contract_v1.json"
    )


def _contract() -> dict:
    payload = _path().read_bytes()
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_SHA256
    return json.loads(payload)


def test_final_delivery_contract_matches_live_v25_scientific_constants() -> None:
    value = _contract()
    assert value["status"] == "outcome_blind_frozen_before_fresh_b2_opening"
    assert value["final_package_generated"] is False
    assert value["fresh_b2_opened"] is False
    assert value["outcome_fields_consumed"] == []
    assert tuple(value["atom_audit_table"]["ordered_atom_names"]) == ATOM_NAMES
    assert tuple(value["atom_audit_table"]["paper_9d_indices"]) == PAPER_9D_INDICES
    assert set(value["atom_audit_table"]["required_ablation_groups"]) == set(
        DEFAULT_ABLATION_GROUPS
    )
    assert tuple(value["causal_context_table"]["ordered_raw_features"]) == (
        RAW_FEATURE_NAMES
    )
    assert tuple(value["benchmark_b"]["paired_arms"]) == ARMS
    assert tuple(value["benchmark_b"]["statuses"]) == STATUSES
    assert tuple(value["latency_reporting"]["stages"]) == LATENCY_STAGES
    assert set(value["benchmark_b"]["signal_safety_metrics"]) == set(
        SIGNAL_SAFETY_METRICS
    )
    assert set(value["benchmark_b"]["primary_metrics"][1:]) == set(
        SAFETY_COMPONENTS
    )
    assert set(value["benchmark_b"]["performance_and_comfort_metrics"]) == set(
        NONINFERIORITY_METRICS
    )
    assert set(value["data_and_scenario_reporting"]["required_event_families"]) == set(
        REQUIRED_CONTROLLED_EVENT_FAMILIES
    )
    training_config = json.loads(
        (
            _root()
            / value["frozen_input_contracts"]["training_config"]["path"]
        ).read_text(encoding="utf-8")
    )
    assert set(value["training_reporting"]["main_fair_2x2_models"]) == set(
        training_config["model_registry"]
    )
    assert {
        "selection_eligibility",
        "physical_feasible_mask_consumed_by_training",
    }.issubset(value["training_reporting"]["required_fields_per_model"])


def test_final_delivery_contract_forbids_post_outcome_table_omission_or_role_drift() -> None:
    value = _contract()
    assert value["method_tables"]["primary"] == [
        "DP operational default/candidate0",
        "CAMP-Static14D",
        "CAMP-Scene14D",
    ]
    assert value["method_tables"]["paper_subset_ablation_separate"] == [
        "CAMP-Static9D",
        "CAMP-Scene9D",
    ]
    assert value["method_tables"]["auxiliary_separate"] == [
        "CAMP-Static14D-full"
    ]
    assert (
        value["method_tables"][
            "auxiliary_not_primary_runtime_calibration_fresh_or_claim_eligible"
        ]
        is True
    )
    assert value["benchmark_a"]["role"] == (
        "read_only_legacy_regression_not_fresh_confirmation"
    )
    assert value["benchmark_a"]["required_result"] == "honest_no_claim"
    assert value["claim_decision"]["failed_any_required_gate_decision"] == (
        "honest_no_claim"
    )
    assert value["claim_decision"]["missing_required_section_policy"] == (
        "evidence_package_incomplete_and_no_claim"
    )
    assert value["artifact_and_head_reporting"]["required_camp_heads"] == [
        "local",
        "origin_main",
        "fresh_github_main",
        "autodl",
    ]
    assert "real_world_road_safety" in value["forbidden_claims"]
    assert "native_ranked_top1" in value["forbidden_claims"]


def test_final_delivery_contract_binds_all_referenced_frozen_inputs() -> None:
    value = _contract()
    for receipt in value["frozen_input_contracts"].values():
        source = _root() / receipt["path"]
        assert source.is_file()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt["sha256"]

    required = set(value["required_sections"])
    assert {
        "fourteen_atom_scientific_audit_table",
        "fresh_benchmark_b_primary_three_arm_table",
        "fresh_benchmark_b_signal_safety_table",
        "performance_and_comfort_noninferiority",
        "latency_by_stage",
        "artifact_roots_heads_and_reproducibility",
        "limitations_and_forbidden_claims",
    } <= required
    assert value["candidate_contract"]["candidate_count"] == 8
    assert value["candidate_contract"]["candidate_tensor_modified"] is False
    assert value["causal_context_table"]["no_v2i_phase_remaining_available"] is False
    assert value["causal_context_table"]["future_phase_schedule_allowed"] is False
