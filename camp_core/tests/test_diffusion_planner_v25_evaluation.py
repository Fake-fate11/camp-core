from __future__ import annotations

import copy
import hashlib
import json

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_calibration import (
    CALIBRATION_ROOT_BINDINGS,
    estimate_v25_noninferiority_margin_resolvability,
    freeze_v25_calibration_contract,
)
from camp_core.integrations.diffusion_planner_v25_evaluation import (
    ARMS,
    LATENCY_STAGES,
    SIGNAL_SAFETY_METRICS,
    evaluate_fresh_b2_three_arm,
    evaluate_holdout_three_arm,
)
from camp_core.integrations.diffusion_planner_v25_fresh_opening import (
    freeze_fresh_b2_opening_consumption,
    freeze_fresh_b2_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    freeze_experiment_protocol,
    freeze_holdout_identity,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening import (
    freeze_holdout_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
    REQUIRED_CONTROLLED_EVENT_FAMILIES,
    SAFETY_COMPONENTS,
)


def _signal_evidence(phase: str, method: bool) -> tuple[dict, dict, dict]:
    metrics = {name: 0.0 for name in SIGNAL_SAFETY_METRICS}
    counts = {
        "red_crossing_intervals": 0,
        "red_violation_intervals": 0,
        "green_false_stop_intervals": 0,
    }
    denominators = {
        "red_phase_intervals": 0,
        "green_phase_intervals": 0,
        "green_unblocked_approach_intervals": 0,
        "yellow_phase_intervals": 0,
    }
    if phase == "red":
        denominators["red_phase_intervals"] = 100
        counts["red_violation_intervals"] = 18 if method else 20
        counts["red_crossing_intervals"] = 28 if method else 30
        metrics.update(
            red_light_violation_rate=counts["red_violation_intervals"] / 100,
            stop_line_crossing_rate=counts["red_crossing_intervals"] / 100,
            stop_line_margin_m=1.1 if method else 1.0,
            crossing_speed_mps=1.9 if method else 2.0,
        )
    elif phase == "green":
        denominators.update(
            green_phase_intervals=100,
            green_unblocked_approach_intervals=100,
        )
        counts["green_false_stop_intervals"] = 9 if method else 10
        metrics["false_stop_on_green_rate"] = (
            counts["green_false_stop_intervals"] / 100
        )
    elif phase != "none":  # pragma: no cover - helper only uses red/green/none
        raise AssertionError(phase)
    return metrics, counts, denominators


def _rows() -> list[dict]:
    rows = []
    pair_index = 0
    for family in REQUIRED_CONTROLLED_EVENT_FAMILIES:
        source = "mapped_signal" if family == "red_light_phase_timing" else "no_signal"
        for tier in ("easy", "borderline", "high_risk"):
            for replicate in range(3):
                order = ARMS[pair_index % 3 :] + ARMS[: pair_index % 3]
                for arm in ARMS:
                    method = arm != "candidate0"
                    signal_phase = (
                        "green"
                        if family == "red_light_phase_timing" and replicate == 0
                        else "red"
                        if family == "red_light_phase_timing"
                        else "none"
                    )
                    signal_safety, signal_counts, signal_denominators = (
                        _signal_evidence(signal_phase, method)
                    )
                    safety = {
                        "total": 2.0 - (0.2 if method else 0.0),
                        **{
                            name: 0.2 - (0.01 if method else 0.0)
                            for name in SAFETY_COMPONENTS
                        },
                    }
                    rows.append(
                        {
                            "pair_key": f"pair-{pair_index}",
                            "arm": arm,
                            "arm_order_index": order.index(arm),
                            "route_identity_sha256": f"{10000 + pair_index:064x}",
                            "semantic_parameter_block_sha256": f"{10500 + pair_index:064x}",
                            "native_route_sha256": f"{11000 + pair_index:064x}",
                            "logical_map_sha256": f"{12000 + pair_index:064x}",
                            "scenario_seed": 25001 + pair_index,
                            "spawn_config_sha256": f"{13000 + pair_index:064x}",
                            "initial_state_sha256": f"{14000 + pair_index:064x}",
                            "initial_input_sha256": f"{15000 + pair_index:064x}",
                            "inference_cluster_id": f"{family}-{tier}",
                            "benchmark_stratum": "controlled_stress",
                            "scenario_family": family,
                            "tier": tier,
                            "source_class": source,
                            "phase_authority_mode": (
                                "controlled_same_tick_override"
                                if source == "mapped_signal"
                                else None
                            ),
                            "signal_phase": signal_phase,
                            "status": "complete",
                            "failure_class": None,
                            "candidate_tensor_modified": False,
                            "selected_index_sequence": [1 if method else 0] * 64,
                            "source_valid_candidate_count_sequence": [8] * 64,
                            "all_k_high_risk_tick_count": 0,
                            "candidate_pool_has_safe_candidate_tick_count": 64,
                            "safety": safety,
                            "performance": {
                                name: 1.0 for name in NONINFERIORITY_METRICS
                            },
                            "signal_safety": signal_safety,
                            "signal_safety_counts": signal_counts,
                            "signal_safety_denominators": signal_denominators,
                            "latency_ms": {
                                stage: [float(index + 1)] * 64
                                for index, stage in enumerate(LATENCY_STAGES)
                            },
                        }
                    )
                pair_index += 1
    return rows


def _calibration_contract() -> dict:
    candidate0_rows = []
    for cluster in range(5):
        for repeat in range(20):
            index = cluster * 20 + repeat
            identity = {
                "schema_version": "camp_dp_v25_exact_candidate0_repeatability_identity_v1",
                "route_identity_sha256": f"{index + 1000:064x}",
                "scenario_identity_sha256": f"{index + 2000:064x}",
                "semantic_parameter_block_sha256": f"{index + 3000:064x}",
                "scenario_seed": 25001 + index,
                "spawn_config_sha256": f"{index + 4000:064x}",
                "initial_state_sha256": f"{index + 5000:064x}",
                "initial_input_sha256": f"{index + 6000:064x}",
                "same_initial_state_and_exogenous_schedule_per_pair": True,
            }
            identity_sha = hashlib.sha256(
                (
                    json.dumps(identity, sort_keys=True, separators=(",", ":"))
                    + "\n"
                ).encode()
            ).hexdigest()
            candidate0_rows.append(
                {
                    "schema_version": "camp_dp_v25_candidate0_ni_calibration_row_v2",
                    "arm": "candidate0_operational_default",
                    "heterogeneity_cluster_id": f"cal-map-{cluster}",
                    "run_instance_sha256": f"{index + 7000:064x}",
                    "repeatability_identity": identity,
                    "repeatability_identity_sha256": identity_sha,
                    "measurement_sha256": f"{index + 8000:064x}",
                    "performance": {
                        name: 1.0 for name in NONINFERIORITY_METRICS
                    },
                    "fresh_b2_opened": False,
                    "fresh_outcome_fields_consumed": [],
                }
            )
    return freeze_v25_calibration_contract(
        root_bindings={name: "a" * 64 for name in CALIBRATION_ROOT_BINDINGS},
        inventory={
            "map_count": 5,
            "intersection_count": 5,
            "corridor_count": 5,
            "route_count": 50,
            "planned_paired_run_count": 100,
            "paired_eligible_run_count": 100,
            "retained_failure_run_count": 0,
            "paired_eligible_rate": 1.0,
        },
        noninferiority_resolvability=(
            estimate_v25_noninferiority_margin_resolvability(candidate0_rows)
        ),
        frozen_model_registry_sha256="b" * 64,
        training_scale_sha256="c" * 64,
        context_scaler_sha256="d" * 64,
    )


def _opening_authority() -> tuple[dict, dict]:
    release = freeze_fresh_b2_opening_release(
        implementation_source_head="6" * 40,
        pointer_head_at_release="7" * 40,
        controller_decision_root_sha256="4" * 64,
        calibration_contract_root_sha256="e" * 64,
        preopen_qualification_root_sha256="1" * 64,
        model_registry_sha256="b" * 64,
        training_scale_sha256="c" * 64,
        context_scaler_sha256="d" * 64,
        scenario_manifest_root_sha256="5" * 64,
        run_nonce="8" * 64,
        authorized_output_dir="/root/autodl-tmp/camp_dp_v25_fresh_b2_test",
    )
    consumption = freeze_fresh_b2_opening_consumption(
        opening_release=release,
        release_root_sha256="2" * 64,
        marker_sha256="3" * 64,
    )
    return release, consumption


def _evaluate(rows):
    calibration = _calibration_contract()
    release, consumption = _opening_authority()
    return evaluate_fresh_b2_three_arm(
        rows,
        calibration_contract=calibration,
        calibration_contract_root_sha256="e" * 64,
        preopen_qualification_root_sha256="1" * 64,
        opening_release=release,
        opening_release_root_sha256="2" * 64,
        opening_consumption_receipt=consumption,
        root_gates={
            "failure_denominator_complete": True,
            "immutability_passed": True,
            "zero_overlap_passed": True,
        },
    )


def _evaluate_holdout(rows):
    calibration = _calibration_contract()
    pair_count = len(rows) // 3
    identity = freeze_holdout_identity(
        split="fresh_b3_nonfresh_evaluation_test",
        scenario_manifest_sha256="1" * 64,
        map_suite_payload_sha256="2" * 64,
        route_census_sha256="3" * 64,
        corridor_census_sha256="4" * 64,
        semantic_census_sha256="5" * 64,
        execution_plan_sha256="6" * 64,
        seeds=[25501],
        arm_order_commit_sha256="7" * 64,
        paired_unit_count=pair_count,
        arm_run_count=len(rows),
        tick_capacity=len(rows) * 64,
    )
    protocol = freeze_experiment_protocol(
        model_registry_sha256="b" * 64,
        training_scale_sha256="c" * 64,
        context_scaler_sha256="d" * 64,
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
        terminal_truth_table=(
            "exclusive_scientific_terminal_or_artifact_fatal_v1"
        ),
    )
    binding = lambda name, char: {
        "path": f"/root/autodl-tmp/{name}",
        "root_sha256": char * 64,
    }
    cas_path = (
        "/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/"
        f"{identity['holdout_identity_sha256']}.json"
    )
    release = freeze_holdout_opening_release(
        implementation_source_head="6" * 40,
        pointer_head_at_release="7" * 40,
        critical_implementation_manifest_sha256="a" * 64,
        controller_decision_root_sha256="4" * 64,
        preopen_authority=binding("preopen", "1"),
        preopen_review=binding("preopen-review", "2"),
        production_composition_preflight=binding("preflight", "3"),
        production_composition_preflight_review=binding(
            "preflight-review", "4"
        ),
        b2_tombstone=binding("b2-tombstone", "5"),
        b2_failure_review=binding("b2-failure-review", "6"),
        holdout_identity=identity,
        experiment_protocol=protocol,
        run_nonce="8" * 64,
        authorized_output_dir="/root/autodl-tmp/fresh_b3_test",
        cas_tombstone_path=cas_path,
    )
    release_root = "2" * 64
    consumption = {
        "schema_version": "camp_dp_v25_holdout_opening_consumption_v1",
        "status": "holdout_opened_consumed",
        "opening_release_root_sha256": release_root,
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol[
            "experiment_protocol_sha256"
        ],
        "reservation_commitment_sha256": release[
            "reservation_commitment_sha256"
        ],
        "cas_tombstone_path": cas_path,
        "marker_sha256": "3" * 64,
        "consumed_before_outcome_capable_operation": True,
        "second_opening_allowed": False,
        "new_nonce_allowed": False,
        "suffix_allowed": False,
        "outcome_fields_consumed_before_opening": [],
    }
    return evaluate_holdout_three_arm(
        rows,
        calibration_contract=calibration,
        calibration_contract_root_sha256="e" * 64,
        preopen_qualification_root_sha256="1" * 64,
        opening_release=release,
        opening_release_root_sha256=release_root,
        opening_consumption_receipt=consumption,
        root_gates={
            "failure_denominator_complete": True,
            "immutability_passed": True,
            "zero_overlap_passed": True,
        },
    )


def test_three_arm_evaluation_preserves_denominator_claims_and_latency() -> None:
    rows = _rows()
    result = _evaluate(rows)
    assert result["full_plan_arm_run_count"] == 3 * result["full_plan_pair_count"]
    assert result["shared_three_arm_paired_eligible_count"] == result[
        "full_plan_pair_count"
    ]
    assert result["method_comparisons_use_identical_pair_set"] is True
    assert result["arm_order_balanced"] is True
    assert set(result["arm_order_position_counts"]) == {
        "overall",
        "benchmark_stratum",
        "scenario_family",
        "independent_cluster",
    }
    assert result["method_reports"]["static14d"]["claim_decision"][
        "safety_improvement_claim_passed"
    ] is True
    assert result["method_reports"]["scene14d"]["claim_decision"][
        "red_light_improvement_claim_passed"
    ] is True
    assert result["latency_ms"]["scene14d"]["selector"]["p99"] > 0.0
    assert result["latency_ms"]["scene14d"]["selector"]["run_count"] == (
        result["full_plan_pair_count"]
    )
    assert result["latency_ms"]["scene14d"]["selector"]["tick_count"] == (
        64 * result["full_plan_pair_count"]
    )
    assert result["v2i_reporting"] == {
        "primary_mode": "no_v2i",
        "no_v2i_full_plan_pair_count": result["full_plan_pair_count"],
        "no_v2i_shared_three_arm_paired_eligible_count": result[
            "shared_three_arm_paired_eligible_count"
        ],
        "v2i_full_plan_pair_count": 0,
        "v2i_separate_evaluation_authorized": False,
        "phase_remaining_consumed": False,
    }
    v2i = result["method_reports"]["scene14d"]["stratified_safety_cost"][
        "v2i_mode"
    ]
    assert v2i["no_v2i"]["observation_count"] == result[
        "shared_three_arm_paired_eligible_count"
    ]
    assert v2i["v2i"]["status"] == "not_authorized_not_evaluated"
    assert v2i["v2i"]["phase_remaining_consumed"] is False
    signal = result["method_reports"]["scene14d"]["signal_safety"]
    assert set(signal) == set(SIGNAL_SAFETY_METRICS)
    assert signal["red_light_violation_rate"]["paired_harm_delta"]["mean_delta"] < 0.0
    assert signal["stop_line_margin_m"]["paired_harm_delta"]["mean_delta"] < 0.0
    assert signal["false_stop_on_green_rate"]["required_signal_phase"] == "green"
    paired = result["method_reports"]["scene14d"]["paired_arm_summaries"]
    assert paired["candidate0"]["selected_nonzero_tick_count"] == 0
    assert paired["scene14d"]["selected_nonzero_tick_rate"] == 1.0
    assert paired["scene14d"]["candidate_pool_has_safe_candidate_tick_rate"] == 1.0
    assert paired["scene14d"]["safety_mean"]["total"] < paired["candidate0"][
        "safety_mean"
    ]["total"]
    assert result["promotion_deployment_activation_authorized"] is False
    assert result["calibration_contract_root_sha256"] == "e" * 64
    assert result["preopen_qualification_root_sha256"] == "1" * 64
    assert result["opening_release_root_sha256"] == "2" * 64
    assert result["fresh_b2_opened_once_after_nonce_consumption"] is True
    assert result["noninferiority_margins_from_calibration_contract"] is True


def test_generic_holdout_evaluation_uses_generic_identity_and_schema() -> None:
    rows = _rows()
    result = _evaluate_holdout(rows)
    assert result["schema_version"] == (
        "camp_dp_v25_holdout_three_arm_evaluation_v1"
    )
    assert result["holdout_split"] == "fresh_b3_nonfresh_evaluation_test"
    assert result["holdout_opened_once_after_cas_consumption"] is True
    assert result["full_plan_arm_run_count"] == len(rows)
    assert result["fresh_outcome_used_to_change_protocol"] is False


def test_three_arm_evaluation_rejects_calibration_contract_drift() -> None:
    calibration = _calibration_contract()
    calibration["noninferiority"]["margins"]["progress"] = 99.0
    release, consumption = _opening_authority()
    with pytest.raises(ValueError, match="frozen reconstruction"):
        evaluate_fresh_b2_three_arm(
            _rows(),
            calibration_contract=calibration,
            calibration_contract_root_sha256="e" * 64,
            preopen_qualification_root_sha256="1" * 64,
            opening_release=release,
            opening_release_root_sha256="2" * 64,
            opening_consumption_receipt=consumption,
            root_gates={
                "failure_denominator_complete": True,
                "immutability_passed": True,
                "zero_overlap_passed": True,
            },
        )


def test_three_arm_evaluation_retains_fixed_dp_failure_without_imputation() -> None:
    rows = _rows()
    pair_key = rows[0]["pair_key"]
    for row in rows:
        if row["pair_key"] == pair_key and row["arm"] == "scene14d":
            row.update(
                status="fixed_dp_candidate_generation_capability_failure",
                failure_class="invalid_k8_heading_norm_envelope",
                safety=None,
                performance=None,
                signal_safety=None,
                signal_safety_counts=None,
                signal_safety_denominators=None,
                latency_ms=None,
                selected_index_sequence=None,
                source_valid_candidate_count_sequence=None,
                all_k_high_risk_tick_count=None,
                candidate_pool_has_safe_candidate_tick_count=None,
            )
    result = _evaluate(rows)
    report = result["method_reports"]["scene14d"]
    assert report["paired_eligible_count"] == result["full_plan_pair_count"] - 1
    assert result["method_reports"]["static14d"]["paired_eligible_count"] == (
        result["full_plan_pair_count"] - 1
    )
    assert result["shared_three_arm_paired_eligible_count"] == (
        result["full_plan_pair_count"] - 1
    )
    assert result["failure_accounting"]["all_status_counts"] == {
        "complete": result["full_plan_arm_run_count"] - 1,
        "fixed_dp_candidate_generation_capability_failure": 1,
        "source_ineligible": 0,
    }
    assert result["failure_accounting"]["by_arm"]["scene14d"][
        "fixed_dp_candidate_generation_capability_failure"
    ] == 1
    assert result["failure_accounting"]["failed_rows_retained"] is True
    assert result["safetycost_imputed_for_failed_pairs"] is False


def test_generic_holdout_evaluation_retains_unit_source_ineligible() -> None:
    rows = _rows()
    pair_key = rows[0]["pair_key"]
    for row in rows:
        if row["pair_key"] != pair_key:
            continue
        row.update(
            status="source_ineligible",
            failure_class="preregistered_source_ineligible",
            safety=None,
            performance=None,
            signal_safety=None,
            signal_safety_counts=None,
            signal_safety_denominators=None,
            latency_ms=None,
            selected_index_sequence=None,
            source_valid_candidate_count_sequence=None,
            all_k_high_risk_tick_count=None,
            candidate_pool_has_safe_candidate_tick_count=None,
        )
        if row["source_class"] == "mapped_signal":
            row["signal_phase"] = "unavailable"
    result = _evaluate_holdout(rows)
    assert result["shared_three_arm_paired_eligible_count"] == (
        result["full_plan_pair_count"] - 1
    )
    assert result["failure_accounting"]["all_status_counts"][
        "source_ineligible"
    ] == 3
    assert result["failure_accounting"]["failed_rows_retained"] is True
    assert result["safetycost_imputed_for_failed_pairs"] is False


def test_three_arm_evaluation_seals_honest_no_claim_when_shared_support_is_empty() -> None:
    rows = _rows()
    for row in rows:
        if row["arm"] != "scene14d":
            continue
        row.update(
            status="fixed_dp_candidate_generation_capability_failure",
            failure_class="invalid_k8_heading_norm_envelope",
            safety=None,
            performance=None,
            signal_safety=None,
            signal_safety_counts=None,
            signal_safety_denominators=None,
            latency_ms=None,
            selected_index_sequence=None,
            source_valid_candidate_count_sequence=None,
            all_k_high_risk_tick_count=None,
            candidate_pool_has_safe_candidate_tick_count=None,
        )
    result = _evaluate(rows)
    assert result["shared_three_arm_paired_eligible_count"] == 0
    for method in ("static14d", "scene14d"):
        claim = result["method_reports"][method]["claim_decision"]
        assert claim["status"] == "honest_no_claim_insufficient_shared_paired_evidence"
        assert claim["safety_improvement_claim_passed"] is False
        assert claim["red_light_improvement_claim_passed"] is False
        assert claim["safetycost_imputed"] is False
    latency = result["latency_ms"]["scene14d"]["selector"]
    assert latency == {
        "status": "no_complete_runs",
        "run_count": 0,
        "tick_count": 0,
        "mean": None,
        "median": None,
        "p95": None,
        "p99": None,
        "max": None,
    }


def test_three_arm_evaluation_rejects_fixed_order_and_metadata_drift() -> None:
    rows = _rows()
    fixed = copy.deepcopy(rows)
    for row in fixed:
        row["arm_order_index"] = ARMS.index(row["arm"])
    with pytest.raises(ValueError, match="not balanced"):
        _evaluate(fixed)

    mismatched = copy.deepcopy(rows)
    mismatched[1]["inference_cluster_id"] = "wrong-cluster"
    with pytest.raises(ValueError, match="metadata drifted"):
        _evaluate(mismatched)

    mismatched_authority = copy.deepcopy(rows)
    mismatched_authority[1]["initial_state_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="metadata drifted"):
        _evaluate(mismatched_authority)

    duplicated_authority = copy.deepcopy(rows)
    authority_fields = (
        "route_identity_sha256",
        "semantic_parameter_block_sha256",
        "native_route_sha256",
        "logical_map_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    )
    for row in duplicated_authority[3:6]:
        for field in authority_fields:
            row[field] = duplicated_authority[0][field]
    with pytest.raises(ValueError, match="duplicated under multiple pair keys"):
        _evaluate(duplicated_authority)


def test_three_arm_evaluation_rejects_cluster_correlated_arm_order() -> None:
    rows = _rows()
    for row in rows:
        replicate = int(row["pair_key"].split("-")[-1]) % 3
        row["inference_cluster_id"] = f"{row['scenario_family']}-{replicate}"
    with pytest.raises(ValueError, match="inference_cluster_id"):
        _evaluate(rows)


def test_three_arm_evaluation_rejects_signal_source_phase_drift() -> None:
    rows = _rows()
    red = next(row for row in rows if row["scenario_family"] == "red_light_phase_timing")
    red["signal_phase"] = "none"
    with pytest.raises(ValueError, match="requires a same-tick phase"):
        _evaluate(rows)

    rows = _rows()
    nonsignal = next(row for row in rows if row["source_class"] == "no_signal")
    nonsignal["signal_safety"]["stop_line_crossing_rate"] = 0.1
    with pytest.raises(ValueError, match="disagrees with counts"):
        _evaluate(rows)


def test_three_arm_evaluation_binds_signal_counts_denominators_and_mixed_phase() -> None:
    rows = _rows()
    red_pair_key = next(
        row["pair_key"]
        for row in rows
        if row["scenario_family"] == "red_light_phase_timing"
        and row["signal_phase"] == "red"
    )
    for row in rows:
        if row["pair_key"] != red_pair_key:
            continue
        row["signal_phase"] = "mixed"
        row["signal_safety_denominators"].update(
            green_phase_intervals=4,
            green_unblocked_approach_intervals=2,
        )
    result = _evaluate(rows)
    assert result["method_reports"]["scene14d"]["signal_safety"][
        "red_light_violation_rate"
    ]["required_positive_denominator"] == "red_phase_intervals"

    bad = _rows()
    mapped = next(row for row in bad if row["signal_phase"] == "red")
    mapped["signal_safety_counts"]["red_crossing_intervals"] += 1
    with pytest.raises(ValueError, match="disagrees with counts"):
        _evaluate(bad)

    bad = _rows()
    mapped = next(row for row in bad if row["signal_phase"] == "red")
    mapped["signal_safety_denominators"]["red_phase_intervals"] = 100.0
    with pytest.raises(ValueError, match="signal safety denominators"):
        _evaluate(bad)


def test_signal_rate_pairing_requires_positive_denominator_in_both_arms() -> None:
    baseline = _evaluate(_rows())
    baseline_count = baseline["method_reports"]["scene14d"]["signal_safety"][
        "false_stop_on_green_rate"
    ]["paired_observation_count"]

    rows = _rows()
    green_pair_key = next(
        row["pair_key"]
        for row in rows
        if row["arm"] == "candidate0" and row["signal_phase"] == "green"
    )
    candidate0 = next(
        row
        for row in rows
        if row["pair_key"] == green_pair_key and row["arm"] == "candidate0"
    )
    candidate0["signal_safety_denominators"][
        "green_unblocked_approach_intervals"
    ] = 0
    candidate0["signal_safety_counts"]["green_false_stop_intervals"] = 0
    candidate0["signal_safety"]["false_stop_on_green_rate"] = 0.0

    result = _evaluate(rows)
    signal = result["method_reports"]["scene14d"]["signal_safety"][
        "false_stop_on_green_rate"
    ]
    assert signal["candidate0_positive_denominator_count"] == baseline_count - 1
    assert signal["method_positive_denominator_count"] == baseline_count
    assert signal["paired_observation_count"] == baseline_count - 1
    assert signal["either_arm_positive_denominator_count"] == baseline_count
    assert signal["excluded_pair_count_one_sided_denominator"] == 1


def test_three_arm_evaluation_requires_complete_tick_latency_series() -> None:
    rows = _rows()
    rows[0]["latency_ms"]["selector"] = 1.0
    with pytest.raises(ValueError, match="exactly 64 tick values"):
        _evaluate(rows)

    rows = _rows()
    rows[0]["latency_ms"]["selector"] = [1.0] * 63
    with pytest.raises(ValueError, match="exactly 64 tick values"):
        _evaluate(rows)

    for invalid in (-1.0, True, "1.0"):
        rows = _rows()
        rows[0]["latency_ms"]["selector"][32] = invalid
        with pytest.raises(ValueError, match="invalid tick"):
            _evaluate(rows)


def test_three_arm_evaluation_requires_tick_level_candidate_accounting() -> None:
    rows = _rows()
    rows[0]["selected_index_sequence"] = [0] * 63
    with pytest.raises(ValueError, match="selected index.*exactly 64"):
        _evaluate(rows)

    rows = _rows()
    rows[0]["source_valid_candidate_count_sequence"][1] = True
    with pytest.raises(ValueError, match="source-valid candidate count.*invalid"):
        _evaluate(rows)

    rows = _rows()
    rows[0]["all_k_high_risk_tick_count"] = 1
    rows[0]["candidate_pool_has_safe_candidate_tick_count"] = 64
    with pytest.raises(ValueError, match="candidate-pool evidence"):
        _evaluate(rows)

    rows = _rows()
    candidate0 = next(row for row in rows if row["arm"] == "candidate0")
    candidate0["selected_index_sequence"][63] = 1
    with pytest.raises(ValueError, match="index zero every tick"):
        _evaluate(rows)


def test_three_arm_evaluation_keeps_naturalistic_as_a_separate_stratum() -> None:
    rows = _rows()
    pair_key = rows[0]["pair_key"]
    for row in rows:
        if row["pair_key"] == pair_key:
            row.update(
                benchmark_stratum="naturalistic",
                scenario_family="naturalistic_background",
                tier="naturalistic",
            )
    result = _evaluate(rows)
    natural = result["method_reports"]["scene14d"]["stratified_safety_cost"][
        "benchmark_stratum"
    ]["naturalistic"]
    assert natural["status"] == "descriptive_only_fewer_than_two_independent_clusters"

    rows = _rows()
    rows[0].update(
        benchmark_stratum="naturalistic",
        scenario_family="lead_vehicle_hard_brake",
        tier="easy",
    )
    with pytest.raises(ValueError, match="naturalistic.*metadata"):
        _evaluate(rows)
