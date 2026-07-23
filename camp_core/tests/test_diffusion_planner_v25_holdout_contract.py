from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    ARMS,
    HoldoutArtifactFatalError,
    canonical_json_bytes,
    freeze_experiment_protocol,
    freeze_fatal_artifact,
    freeze_forward_binding,
    freeze_holdout_identity,
    freeze_latency_namespaces,
    freeze_tombstone,
    freeze_unit_terminal,
    install_terminal_tombstone,
    normative_holdout_contract,
    reserve_holdout_identity,
    transition_holdout_identity,
    validate_experiment_protocol,
    validate_fatal_artifact,
    validate_forward_binding,
    validate_holdout_identity,
    validate_latency_namespaces,
    validate_tombstone,
    validate_unit_terminal,
)


def _identity() -> dict:
    return freeze_holdout_identity(
        split="fresh_b3",
        scenario_manifest_sha256="1" * 64,
        map_suite_payload_sha256="2" * 64,
        route_census_sha256="3" * 64,
        corridor_census_sha256="4" * 64,
        semantic_census_sha256="5" * 64,
        execution_plan_sha256="6" * 64,
        seeds=[25501, 25502, 25503, 25504, 25505],
        arm_order_commit_sha256="7" * 64,
        paired_unit_count=500,
        arm_run_count=1500,
        tick_capacity=96_000,
    )


def _protocol() -> dict:
    return freeze_experiment_protocol(
        model_registry_sha256="1" * 64,
        training_scale_sha256="2" * 64,
        context_scaler_sha256="3" * 64,
        atom_contract_sha256="4" * 64,
        threshold_contract_sha256="5" * 64,
        noninferiority_contract_sha256="6" * 64,
        multiplicity_contract_sha256="7" * 64,
        claim_contract_sha256="8" * 64,
        failure_contract_sha256="9" * 64,
        candidate0_semantics=(
            "action_equivalent_operational_default_first_default_output_alias"
        ),
        same_forward_contract=(
            "forward_execution_id_plus_input_model_action_digest"
        ),
        latency_contract=(
            "online_operational_plus_supplementary_evidence_plus_runtime_total_v1"
        ),
        terminal_truth_table="exclusive_scientific_terminal_or_artifact_fatal_v1",
    )


def _zeros(fields: tuple[str, ...]) -> dict[str, float]:
    return {field: 0.0 for field in fields}


def _latency(arm: str) -> dict:
    online = _zeros(
        (
            "dp_operational_default",
            "additional_k8_generation",
            "atoms",
            "context",
            "scene_weight",
            "selector",
        )
    )
    supplementary = _zeros(
        (
            "candidate_pool_generation",
            "atoms",
            "context",
            "scene_weight",
            "receipt_hashing",
        )
    )
    online["dp_operational_default"] = 1.0
    if arm == "candidate0":
        supplementary["candidate_pool_generation"] = 7.0
        supplementary["atoms"] = 0.3
    else:
        online["additional_k8_generation"] = 7.0
        online["atoms"] = 0.3
        online["selector"] = 0.1
    if arm == "scene14d":
        online["context"] = 0.2
        online["scene_weight"] = 0.05
    total = sum(online.values()) + sum(supplementary.values()) + 0.5
    return freeze_latency_namespaces(
        arm=arm,
        online_operational_latency_ms=online,
        supplementary_evidence_latency_ms=supplementary,
        runtime_total_observed_ms=total,
        runtime_nondecision_overhead_ms=0.5,
        action_available_timestamp_ns=100,
        supplementary_started_timestamp_ns=101,
    )


def test_holdout_identity_and_protocol_are_nonce_head_and_path_independent() -> None:
    first = _identity()
    second = _identity()
    assert first == second
    assert validate_holdout_identity(first) == first
    assert validate_experiment_protocol(_protocol()) == _protocol()

    changed = copy.deepcopy(first)
    changed["seeds"][0] = 25506
    with pytest.raises(ValueError, match="exact value"):
        validate_holdout_identity(changed)


def test_tracked_normative_contract_matches_runtime_exactly() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "integrations"
        / "diffusion_planner_v25_holdout_normative_contract_v2.json"
    )
    expected = normative_holdout_contract()
    assert path.read_bytes() == canonical_json_bytes(expected)


def test_cas_tombstone_rejects_second_nonce_directory_or_repackaging(tmp_path) -> None:
    target = reserve_holdout_identity(
        tmp_path,
        holdout_identity=_identity(),
        experiment_protocol=_protocol(),
        reservation_commitment_sha256="d" * 64,
    )
    with pytest.raises(FileExistsError):
        reserve_holdout_identity(
            tmp_path,
            holdout_identity=_identity(),
            experiment_protocol=_protocol(),
            reservation_commitment_sha256="e" * 64,
        )
    opened = transition_holdout_identity(
        target,
        expected_state="reserved",
        next_state="opened_consumed",
        opening_release_root_sha256="a" * 64,
        marker_sha256="b" * 64,
    )
    assert opened["state"] == "opened_consumed"
    terminal = transition_holdout_identity(
        target,
        expected_state="opened_consumed",
        next_state="terminal_failure",
        terminal_artifact_root_sha256="c" * 64,
        terminal_reason="engineering failure",
    )
    assert validate_tombstone(terminal)["second_opening_allowed"] is False
    with pytest.raises(FileExistsError):
        transition_holdout_identity(
            target,
            expected_state="reserved",
            next_state="opened_consumed",
            opening_release_root_sha256="d" * 64,
            marker_sha256="e" * 64,
        )


def test_historical_terminal_tombstone_is_persistent_and_exclusive(tmp_path) -> None:
    tombstone = freeze_tombstone(
        holdout_identity_sha256=_identity()["holdout_identity_sha256"],
        experiment_protocol_sha256=_protocol()["experiment_protocol_sha256"],
        reservation_commitment_sha256="d" * 64,
        state="terminal_failure",
        history=[
            {"state": "reserved"},
            {"state": "opened_consumed"},
            {"state": "terminal_failure"},
        ],
        opening_attempt_count=1,
        opening_release_root_sha256="a" * 64,
        marker_sha256="b" * 64,
        terminal_artifact_root_sha256="c" * 64,
        terminal_reason="consumed historical engineering failure",
        outcome_evaluation_completed=False,
    )
    target = install_terminal_tombstone(tmp_path, tombstone=tombstone)
    assert validate_tombstone(
        json.loads(target.read_text(encoding="utf-8"))
    ) == tombstone
    with pytest.raises(FileExistsError):
        install_terminal_tombstone(tmp_path, tombstone=tombstone)


def test_candidate0_pool_latency_is_supplementary_not_online() -> None:
    candidate0 = _latency("candidate0")
    assert validate_latency_namespaces(candidate0) == candidate0
    assert candidate0["online_operational_latency_ms"]["atoms"] == 0.0
    assert candidate0["supplementary_evidence_latency_ms"]["atoms"] == 0.3

    wrong = copy.deepcopy(candidate0)
    wrong["online_operational_latency_ms"]["atoms"] = 0.3
    wrong["supplementary_evidence_latency_ms"]["atoms"] = 0.0
    with pytest.raises(ValueError, match="forbidden"):
        validate_latency_namespaces(wrong)


def test_three_arm_latency_matrix_and_total_reconciliation() -> None:
    for arm in ARMS:
        value = _latency(arm)
        assert validate_latency_namespaces(value) == value
    static = _latency("static14d")
    assert static["online_operational_latency_ms"]["context"] == 0.0
    assert static["online_operational_latency_ms"]["scene_weight"] == 0.0
    scene = _latency("scene14d")
    assert scene["online_operational_latency_ms"]["context"] > 0.0
    assert scene["online_operational_latency_ms"]["scene_weight"] > 0.0

    bad = copy.deepcopy(scene)
    bad["runtime_total_observed_ms"] += 0.01
    with pytest.raises(ValueError, match="does not reconcile"):
        validate_latency_namespaces(bad)


def test_forward_binding_rejects_input_model_action_or_execution_id_mutation() -> None:
    value = freeze_forward_binding(
        tick_index=0,
        input_sha256="1" * 64,
        model_sha256="2" * 64,
        action_sha256="3" * 64,
        candidate_pool_sha256="4" * 64,
    )
    assert validate_forward_binding(value) == value
    for field in (
        "forward_execution_id",
        "input_sha256",
        "model_sha256",
        "action_sha256",
        "candidate_pool_sha256",
    ):
        changed = copy.deepcopy(value)
        changed[field] = "f" * 64
        with pytest.raises(ValueError, match="exact value"):
            validate_forward_binding(changed)


def test_terminal_truth_table_is_exclusive_and_artifact_errors_are_fatal() -> None:
    complete = freeze_unit_terminal(
        status="complete", failure_class=None, all_k_bad=True
    )
    assert validate_unit_terminal(complete)["evaluation_eligible"] is True
    fixed = freeze_unit_terminal(
        status="fixed_dp_candidate_generation_capability_failure",
        failure_class="invalid_k8_heading_norm_envelope",
        all_k_bad=False,
    )
    assert validate_unit_terminal(fixed)["planned_denominator_retained"] is True
    source = freeze_unit_terminal(
        status="source_ineligible",
        failure_class="preregistered_source_ineligible",
        all_k_bad=False,
    )
    assert validate_unit_terminal(source)["evaluation_eligible"] is False
    with pytest.raises(HoldoutArtifactFatalError):
        freeze_unit_terminal(
            status="execution_failure",
            failure_class="schema_error",
            all_k_bad=False,
        )


def test_fatal_partial_is_strict_and_never_claims_full_denominator() -> None:
    fatal = freeze_fatal_artifact(
        block_class="receipt_projection_contract_failure",
        reason="candidate0 latency namespace mismatch",
        controller_decision_root_sha256="1" * 64,
        opening_release_root_sha256="2" * 64,
        marker_path="/root/autodl-tmp/.cas/marker.json",
        marker_sha256="3" * 64,
        holdout_identity_sha256="4" * 64,
        experiment_protocol_sha256="5" * 64,
        attempted_unit_ordinal=0,
        attempted_arm="candidate0",
        planned_arm_run_count=1500,
        attempted_arm_run_count=1,
        complete_arm_run_count=0,
        outcome_fields_consumed=[],
        fresh_opened_once=True,
    )
    assert validate_fatal_artifact(fatal) == fatal
    assert fatal["unattempted_arm_run_count"] == 1499
    assert fatal["full_denominator_formed"] is False
    assert fatal["new_nonce_allowed"] is False
    for mutation in (
        lambda row: row.pop("reason"),
        lambda row: row.update(extra=True),
        lambda row: row.update(planned_arm_run_count=1500.0),
        lambda row: row.update(complete_arm_run_count=2),
        lambda row: row.update(new_nonce_allowed=True),
    ):
        changed = copy.deepcopy(fatal)
        mutation(changed)
        with pytest.raises((ValueError, TypeError)):
            validate_fatal_artifact(changed)
