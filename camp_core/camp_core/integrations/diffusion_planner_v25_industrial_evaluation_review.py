from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping


# Deliberately no import of the producer contract, registry, transform, or
# capability-classification module.  This file is the separate-role literal
# oracle.

EXPECTED_AUTHORITY_SHA256 = (
    "720e9293f88de92b08bbfab39100baf46b396ca59a5b1c9a089cde5af0bfeca5"
)
EXPECTED_CONTRACT_SCHEMA = "camp_dp_v25_industrial_oriented_evaluation_contract_v1"
EXPECTED_CAPABILITY_SCHEMA = (
    "camp_dp_v25_industrial_oriented_evaluation_capability_matrix_v1"
)
EXPECTED_FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_BASE_HEAD = "456aabb70308271f4b7b1dcb30550fe5574fc389"
EXPECTED_ROOTS = {
    "execution_root_sha256": (
        "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
    ),
    "execution_review_root_sha256": (
        "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d"
    ),
    "corrected_evaluation_root_sha256": (
        "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f"
    ),
    "corrected_evaluation_review_root_sha256": (
        "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459"
    ),
    "metric_semantics_contract_root_sha256": (
        "318e85f9656a5dd79c9fb0ad6c1dfcd94678b35c4aba455f3909cf3475cca758"
    ),
    "metric_semantics_review_root_sha256": (
        "fc04fd6e45487df6c9bf5313b9ee6d633f91303e0a1aa00f0a3114b8134fea95"
    ),
}
EXPECTED_ENDPOINT_FIELDS = {
    "endpoint_id",
    "domain",
    "direction",
    "formula",
    "input_shape",
    "applicability",
    "finite_rules",
    "status_enum",
    "legacy_alias",
    "industrial_interpretation",
    "source",
    "source_sha256",
    "units",
    "sample_rate",
    "coordinate_frame",
    "filter",
    "window",
    "edge_handling",
    "event_definition",
    "opportunity_denominator",
    "per_run_aggregation",
    "cluster_unit",
    "confidence_interval",
    "multiplicity",
    "noninferiority_or_guardrail",
    "missing_policy",
    "failure_full_denominator_policy",
    "evidence_class",
}
EXPECTED_CLASSES = {
    "directly_reconstructable",
    "reconstructable_with_frozen_transform",
    "evidence_missing",
    "scientifically_inapplicable",
}
EXPECTED_DOMAINS = {
    "safety",
    "operations",
    "vehicle_body_planar_kinematic_comfort_proxy",
    "controlled_benchmark_realtime",
}

# endpoint_id -> domain, direction, units, evidence class, source, required
# formula fragment.  These literals are intentionally reconstructed here.
EXPECTED_CORE = {
    "safety.collision_any": ("safety", "lower", "bool", "reconstructable_with_frozen_transform", "sealed_execution", "full_ego_OBB"),
    "safety.collision_episode_count": ("safety", "lower", "count", "reconstructable_with_frozen_transform", "sealed_execution", "false_to_true"),
    "safety.collision_duration_s": ("safety", "lower", "s", "reconstructable_with_frozen_transform", "sealed_execution", "*0.1"),
    "safety.collision_impact_relative_speed_proxy_mps": ("safety", "lower", "m/s", "evidence_missing", "no_credible_sealed_source", "contact-time"),
    "safety.collision_delta_v_mps": ("safety", "lower", "m/s", "evidence_missing", "no_credible_sealed_source", "contact-time"),
    "safety.collision_contact_severity": ("safety", "lower", "severity_unit", "evidence_missing", "no_credible_sealed_source", "contact-time"),
    "safety.min_full_polygon_clearance_m": ("safety", "higher", "m", "reconstructable_with_frozen_transform", "sealed_execution", "distance(full ego polygon"),
    "safety.max_closing_speed_mps": ("safety", "lower", "m/s", "reconstructable_with_frozen_transform", "sealed_execution", "-dot(r,v_rel)"),
    "safety.min_geometry_ttc_s": ("safety", "higher", "s", "reconstructable_with_frozen_transform", "sealed_execution", "continuous-SAT"),
    "safety.max_drac_mps2": ("safety", "lower", "m/s^2", "reconstructable_with_frozen_transform", "sealed_execution", "closing^2"),
    "safety.critical_exposure_duration_s": ("safety", "lower", "s", "reconstructable_with_frozen_transform", "sealed_execution", "project-descriptive"),
    "safety.critical_exposure_episode_count": ("safety", "lower", "count", "reconstructable_with_frozen_transform", "sealed_execution", "descriptive threshold"),
    "safety.time_headway_s": ("safety", "higher", "s", "evidence_missing", "no_credible_sealed_source", "unique_same_lane_leader"),
    "safety.post_encroachment_time_s": ("safety", "higher", "s", "evidence_missing", "no_credible_sealed_source", "conflict zone"),
    "safety.certified_red_crossing_any": ("safety", "lower", "bool", "reconstructable_with_frozen_transform", "sealed_execution", "unthresholded"),
    "safety.certified_red_crossing_count": ("safety", "lower", "count", "reconstructable_with_frozen_transform", "sealed_execution", "certified stop-line"),
    "safety.certified_red_crossing_speed_mps": ("safety", "lower", "m/s", "reconstructable_with_frozen_transform", "sealed_execution", "interpolated speed"),
    "safety.certified_red_encounter_opportunity_count": ("safety", "descriptive_unclassified", "encounter_count", "reconstructable_with_frozen_transform", "sealed_execution", "unique certified stopline"),
    "safety.certified_red_phase_interval_count": ("safety", "descriptive_unclassified", "interval_count", "reconstructable_with_frozen_transform", "sealed_execution", "same-tick certified"),
    "safety.drivable_outside_fraction_max": ("safety", "lower", "fraction", "reconstructable_with_frozen_transform", "sealed_execution", "area(F minus union(D))"),
    "safety.drivable_outside_duration_s": ("safety", "lower", "s", "reconstructable_with_frozen_transform", "sealed_execution", "outside_fraction>1e-9"),
    "safety.drivable_outside_episode_count": ("safety", "lower", "count", "reconstructable_with_frozen_transform", "sealed_execution", "false_to_true"),
    "safety.drivable_signed_clearance_min_m": ("safety", "higher", "m", "reconstructable_with_frozen_transform", "sealed_execution", "external boundary"),
    "safety.drivable_penetration_max_m": ("safety", "lower", "m", "reconstructable_with_frozen_transform", "sealed_execution", "external boundary"),
    "safety.wrong_way_duration_s": ("safety", "lower", "s", "reconstructable_with_frozen_transform", "sealed_execution", "unique_direction"),
    "safety.wrong_way_episode_count": ("safety", "lower", "count", "reconstructable_with_frozen_transform", "sealed_execution", "unique-direction"),
    "operations.speed_excess_max_mps": ("operations", "lower", "m/s", "reconstructable_with_frozen_transform", "sealed_execution", "speed-limit"),
    "operations.speed_excess_mean_positive_mps": ("operations", "lower", "m/s", "reconstructable_with_frozen_transform", "sealed_execution", "mean(excess"),
    "operations.speed_excess_duration_s": ("operations", "lower", "s", "reconstructable_with_frozen_transform", "sealed_execution", "0/0.05/0.1/0.2"),
    "operations.speed_excess_magnitude_duration_m": ("operations", "lower", "m", "reconstructable_with_frozen_transform", "sealed_execution", "max(0,excess-tolerance)"),
    "operations.ordered_route_arc_final_m": ("operations", "higher", "m", "reconstructable_with_frozen_transform", "sealed_execution", "stateful ordered"),
    "operations.max_forward_progress_m": ("operations", "higher", "m", "reconstructable_with_frozen_transform", "sealed_execution", "max_t(s_t)-s_0"),
    "operations.net_forward_progress_m": ("operations", "higher", "m", "reconstructable_with_frozen_transform", "sealed_execution", "s_final-s_0"),
    "operations.completion_fraction": ("operations", "higher", "fraction", "reconstructable_with_frozen_transform", "sealed_execution", "max_forward_progress/route_length"),
    "operations.goal_distance_final_m": ("operations", "lower", "m", "reconstructable_with_frozen_transform", "sealed_execution", "final_position-goal_pose"),
    "operations.goal_reached": ("operations", "higher", "bool", "reconstructable_with_frozen_transform", "sealed_execution", "goal_tolerance_m"),
    "operations.goal_passed": ("operations", "lower", "bool", "reconstructable_with_frozen_transform", "sealed_execution", "goal_pass_window_m"),
    "operations.backtracking_duration_s": ("operations", "lower", "s", "reconstructable_with_frozen_transform", "sealed_execution", "s_previous-s_current"),
    "operations.backtracking_distance_m": ("operations", "lower", "m", "reconstructable_with_frozen_transform", "sealed_execution", "s_previous-s_current"),
    "operations.distance_traveled_m": ("operations", "descriptive_unclassified", "m", "reconstructable_with_frozen_transform", "sealed_execution", "norm(position"),
    "operations.travel_efficiency_ratio": ("operations", "higher", "ratio", "reconstructable_with_frozen_transform", "sealed_execution", "distance_traveled_m"),
    "operations.false_stop_duration_s": ("operations", "lower", "s", "evidence_missing", "no_credible_sealed_source", "valid motion opportunity"),
    "operations.false_stop_episode_count": ("operations", "lower", "count", "evidence_missing", "no_credible_sealed_source", "excluding red/obstacle/goal"),
    "comfort.body_longitudinal_filtered_acceleration_summary": ("vehicle_body_planar_kinematic_comfort_proxy", "lower", "m/s^2", "reconstructable_with_frozen_transform", "sealed_execution", "signed mean,RMS"),
    "comfort.planar_kinematic_vdv_like_longitudinal": ("vehicle_body_planar_kinematic_comfort_proxy", "lower", "m/s^1.75", "reconstructable_with_frozen_transform", "sealed_execution", "abs(a_filtered)^4"),
    "comfort.filtered_longitudinal_jerk_control_smoothness_summary": ("vehicle_body_planar_kinematic_comfort_proxy", "lower", "m/s^3", "reconstructable_with_frozen_transform", "sealed_execution", "diff(filtered_body_acceleration)"),
    "comfort.body_lateral_filtered_acceleration_summary": ("vehicle_body_planar_kinematic_comfort_proxy", "lower", "m/s^2", "reconstructable_with_frozen_transform", "sealed_execution", "signed mean,RMS"),
    "comfort.planar_kinematic_vdv_like_lateral": ("vehicle_body_planar_kinematic_comfort_proxy", "lower", "m/s^1.75", "reconstructable_with_frozen_transform", "sealed_execution", "abs(a_filtered)^4"),
    "comfort.filtered_lateral_jerk_control_smoothness_summary": ("vehicle_body_planar_kinematic_comfort_proxy", "lower", "m/s^3", "reconstructable_with_frozen_transform", "sealed_execution", "diff(filtered_body_acceleration)"),
    "comfort.occupant_seat_iso_sae_conformity": ("vehicle_body_planar_kinematic_comfort_proxy", "descriptive_unclassified", "not_applicable", "scientifically_inapplicable", "no_credible_sealed_source", "seat/suspension/human transfer"),
    "realtime.pool_generation_latency_ms": ("controlled_benchmark_realtime", "lower", "ms", "evidence_missing", "future_same_ego_batch8_instrumentation", "mean,median,p95,p99,max"),
    "realtime.atoms_latency_ms": ("controlled_benchmark_realtime", "lower", "ms", "evidence_missing", "future_same_ego_batch8_instrumentation", "mean,median,p95,p99,max"),
    "realtime.context_weights_latency_ms": ("controlled_benchmark_realtime", "lower", "ms", "evidence_missing", "future_same_ego_batch8_instrumentation", "mean,median,p95,p99,max"),
    "realtime.selector_increment_latency_ms": ("controlled_benchmark_realtime", "lower", "ms", "evidence_missing", "future_same_ego_batch8_instrumentation", "mean,median,p95,p99,max"),
    "realtime.end_to_end_latency_ms": ("controlled_benchmark_realtime", "lower", "ms", "evidence_missing", "future_same_ego_batch8_instrumentation", "mean,median,p95,p99,max"),
    "realtime.hypothetical_budget_exceedance": ("controlled_benchmark_realtime", "lower", "rate_and_ms", "evidence_missing", "future_same_ego_batch8_instrumentation", "50/100/200/500/1000"),
}

SOURCE_ROOTS = {
    "sealed_execution": (
        "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881",
        "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
    ),
    "sealed_corrected_evaluation": (
        "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f",
        "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459",
    ),
    "sealed_evaluation_v2_contract": (
        "99501763a4a88c9d80fff738054b37593717df0b6d33e3749ad451d9e52a15e0",
        "a7ba686647ccfe64f45a3304a00a392c1a362534833023fe26e0343a374bfac0",
    ),
    "sealed_evaluation_v2_materialization": (
        "4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941",
        "e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b",
    ),
    "sealed_metric_semantics": (
        "99fd5e571160a3ac3d5bb2b6d6f3391c3da5965bf592707ff85c88080ac2dbcf",
        "88b35ab8ef51807c848200675ceeebe6b26e15a4f4b34da51f131e9303f37898",
    ),
    "future_same_ego_batch8_instrumentation": (None, None),
    "no_credible_sealed_source": (None, None),
}


def _canonical_authority_sha(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def review_contract_literal(contract: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(contract))
    if set(value) != {
        "schema_version",
        "status",
        "high_authority",
        "high_authority_sha256",
        "bindings",
        "endpoint_domains",
        "evidence_classes",
        "endpoint_required_fields",
        "endpoint_count",
        "endpoints",
        "source_authorities",
        "comfort_transform",
        "statistics",
        "legacy",
        "evaluation_and_selector_training_decoupled",
        "claim_authorized",
        "model_pool_selector_call_count",
        "outcome_values_read",
        "old_artifact_or_cas_write_count",
        "references",
    }:
        raise ValueError("independent industrial contract top-level fields drifted")
    if (
        value["schema_version"] != EXPECTED_CONTRACT_SCHEMA
        or value["status"]
        != "frozen_outcome_independent_industrial_oriented_evaluation_contract"
        or value["high_authority_sha256"] != EXPECTED_AUTHORITY_SHA256
        or _canonical_authority_sha(value["high_authority"])
        != EXPECTED_AUTHORITY_SHA256
    ):
        raise ValueError("independent industrial authority drifted")
    authority = value["high_authority"]
    if (
        authority.get("legacy_safetycost_role")
        != "immutable_legacy_exploratory_diagnostic_only"
        or authority.get("new_weighted_total_allowed") is not False
        or authority.get("selector_training_and_final_evaluation_decoupled") is not True
        or authority.get("fresh_or_b4_outcome_read_authorized") is not False
        or authority.get("model_pool_selector_training_calibration_validation_closed_loop_fresh_holdout_authorized")
        is not False
    ):
        raise ValueError("independent industrial authority semantics drifted")
    if value["bindings"] != {
        "live_base_head": EXPECTED_BASE_HEAD,
        "fixed_dp_head": EXPECTED_FIXED_DP,
        **EXPECTED_ROOTS,
    }:
        raise ValueError("independent industrial root bindings drifted")
    if set(value["endpoint_domains"]) != EXPECTED_DOMAINS:
        raise ValueError("independent industrial domain topology drifted")
    if set(value["evidence_classes"]) != EXPECTED_CLASSES:
        raise ValueError("independent industrial evidence classes drifted")
    if set(value["endpoint_required_fields"]) != EXPECTED_ENDPOINT_FIELDS:
        raise ValueError("independent industrial endpoint required fields drifted")
    rows = value["endpoints"]
    if (
        type(rows) is not list
        or len(rows) != len(EXPECTED_CORE)
        or value["endpoint_count"] != len(EXPECTED_CORE)
    ):
        raise ValueError("independent industrial endpoint count drifted")
    seen: set[str] = set()
    for row in rows:
        if type(row) is not dict or set(row) != EXPECTED_ENDPOINT_FIELDS:
            raise ValueError("independent industrial endpoint row schema drifted")
        endpoint_id = row["endpoint_id"]
        if endpoint_id in seen or endpoint_id not in EXPECTED_CORE:
            raise ValueError("independent industrial endpoint identity drifted")
        seen.add(endpoint_id)
        domain, direction, units, evidence, source, formula_fragment = EXPECTED_CORE[
            endpoint_id
        ]
        if (
            row["domain"] != domain
            or row["direction"] != direction
            or row["units"] != units
            or row["evidence_class"] != evidence
            or row["source"] != source
            or formula_fragment not in row["formula"]
        ):
            raise ValueError(f"independent endpoint semantic drift: {endpoint_id}")
        _review_common_endpoint_policy(row)
    if seen != set(EXPECTED_CORE):
        raise ValueError("independent industrial endpoint omitted")
    _review_comfort(value["comfort_transform"], rows)
    _review_statistics(value["statistics"])
    _review_legacy(value["legacy"], rows)
    _review_references(value["references"])
    if (
        value["evaluation_and_selector_training_decoupled"] is not True
        or value["claim_authorized"] is not False
        or value["model_pool_selector_call_count"] != 0
        or value["outcome_values_read"] is not False
        or value["old_artifact_or_cas_write_count"] != 0
    ):
        raise ValueError("independent industrial no-run/no-claim boundary drifted")
    return value


def _review_common_endpoint_policy(row: Mapping[str, Any]) -> None:
    expected_sample_rate = (
        "10 Hz (dt=0.1 s)"
        if "tick" in row["input_shape"]
        or "position" in row["input_shape"]
        or "latency" in row["input_shape"]
        else "per_run"
    )
    if (
        "typed evidence_missing" not in row["missing_policy"]
        or "no zero" not in row["missing_policy"]
        or "complete-case claim" not in row["missing_policy"]
        or "full denominator" not in row["failure_full_denominator_policy"]
        or "ticks, rows, arms, and seeds are not independent n" not in row["cluster_unit"]
        or row["noninferiority_or_guardrail"]
        != "numeric_margin_not_authorized_until_future_preregistration"
        or "endpoint vector" not in row["multiplicity"]
        or "Student-t" not in row["confidence_interval"]
        or row["sample_rate"] != expected_sample_rate
    ):
        raise ValueError(f"independent endpoint policy drift: {row['endpoint_id']}")
    if row["domain"] == "vehicle_body_planar_kinematic_comfort_proxy" and row[
        "endpoint_id"
    ] != "comfort.occupant_seat_iso_sae_conformity":
        if (
            row["filter"]
            != "11-point centered equal-weight FIR coefficients [1/11]*11, "
            "zero-phase offline valid convolution"
            or row["window"]
            != "64 positions -> 63 interval velocities -> 62 accelerations -> 52 filtered"
            or row["edge_handling"]
            != "valid-only; no padding, extrapolation, or endpoint replication"
        ):
            raise ValueError("independent comfort row filter/window/edge drifted")
    if row["endpoint_id"].startswith("safety.certified_red_") and (
        "reported separately and never mixed" not in row["opportunity_denominator"]
    ):
        raise ValueError("independent red opportunity denominator drifted")
    if row["evidence_class"] == "evidence_missing":
        if row["status_enum"] != "evidence_missing" or row["source_sha256"] is not None:
            raise ValueError("independent missing endpoint encoding drifted")
    elif row["evidence_class"] == "scientifically_inapplicable":
        if row["status_enum"] != "scientifically_inapplicable":
            raise ValueError("independent inapplicable endpoint encoding drifted")
    else:
        if (
            row["status_enum"] != "defined_not_materialized"
            or row["source_sha256"] != SOURCE_ROOTS[row["source"]][0]
        ):
            raise ValueError("independent reconstructable endpoint binding drifted")


def _review_comfort(transform: Mapping[str, Any], rows: list[dict[str, Any]]) -> None:
    expected_coefficients = [1.0 / 11.0] * 11
    if (
        transform.get("dt_s") != 0.1
        or transform.get("sample_rate_hz") != 10.0
        or transform.get("position_count") != 64
        or transform.get("interval_velocity_count") != 63
        or transform.get("raw_acceleration_count") != 62
        or transform.get("body_heading_indices") != [1, 62]
        or transform.get("filter_coefficients") != expected_coefficients
        or not math.isclose(sum(transform["filter_coefficients"]), 1.0)
        or transform.get("filter_width_samples") != 11
        or transform.get("filter_window_s") != 1.0
        or transform.get("valid_only") is not True
        or transform.get("padding") is not False
        or transform.get("extrapolation") is not False
        or transform.get("filtered_acceleration_count") != 52
        or transform.get("filtered_jerk_count") != 51
        or transform.get("filtered_jerk_formula")
        != "diff(filtered_acceleration)/0.1"
        or transform.get("acceleration_sensitivity_mps2") != [0.5, 1.0, 2.0, 3.0]
        or transform.get("jerk_sensitivity_mps3") != [0.5, 1.0, 2.0, 5.0]
        or transform.get("sensitivity_is_project_descriptive_not_industrial_gate")
        is not True
    ):
        raise ValueError("independent comfort transform drifted")
    comfort = [row for row in rows if row["domain"].startswith("vehicle_body")]
    if any(
        "raw 0.1" in row["formula"].lower()
        or "scalar-speed second" in row["industrial_interpretation"].lower()
        for row in comfort
    ):
        raise ValueError("raw controller chatter was promoted to comfort")
    occupant = next(
        row
        for row in comfort
        if row["endpoint_id"] == "comfort.occupant_seat_iso_sae_conformity"
    )
    if (
        occupant["evidence_class"] != "scientifically_inapplicable"
        or "no ISO 2631 or SAE J2834 conformity"
        not in occupant["industrial_interpretation"]
    ):
        raise ValueError("industrial occupant comfort claim drifted")


def _review_statistics(value: Mapping[str, Any]) -> None:
    if (
        value.get("per_run_first") is not True
        or value.get("ticks_rows_arms_seeds_as_independent_n") is not False
        or value.get("weighted_total") is not False
        or value.get("complete_case_claim_allowed") is not False
        or value.get("full_denominator_missing_retention") is not True
        or value.get("numeric_margin")
        != "numeric_margin_not_authorized_until_future_preregistration"
        or "exact zero delta is tie" not in value.get("better_tie_worse", "")
        or "Student-t" not in value.get("confidence_interval", "")
        or "equal-weight" not in value.get("cluster_aggregation", "")
    ):
        raise ValueError("independent industrial statistics topology drifted")


def _review_legacy(value: Mapping[str, Any], rows: list[dict[str, Any]]) -> None:
    if (
        value.get("role") != "immutable_legacy_exploratory_diagnostic_only"
        or value.get("safetycost_formula")
        != "100*collision_any + 10*near_tick_rate + 20*offroad_tick_rate + "
        "20*wrongway_tick_rate + 30*red_any + 10*speed_tick_rate"
        or value.get("values_or_roots_mutated") is not False
        or any(
            value.get(name) is not False
            for name in (
                "allowed_in_primary",
                "allowed_in_pass_or_claim",
                "allowed_in_training_support_or_adaptation",
            )
        )
    ):
        raise ValueError("independent legacy SafetyCost role drifted")
    if any("safetycost" in row["endpoint_id"].lower() for row in rows):
        raise ValueError("legacy SafetyCost was promoted into primary registry")


def _review_references(rows: Any) -> None:
    expected = {
        ("ISO 2631-1:1997", "https://www.iso.org/standard/7612.html"),
        (
            "SAE J2834_202504",
            "https://saemobilus.sae.org/standards/"
            "j2834_202504-ride-index-structure-development-methodology",
        ),
        ("ISO 34502:2022", "https://www.iso.org/standard/78951.html"),
        (
            "FHWA SSAM report FHWA-HRT-08-051",
            "https://www.fhwa.dot.gov/publications/research/safety/08051/",
        ),
    }
    if type(rows) is not list or {
        (row.get("name"), row.get("url")) for row in rows
    } != expected:
        raise ValueError("independent industrial reference authority drifted")
    if any(
        row.get("accessed") != "2026-07-26"
        or "no copied normative thresholds or conformity" not in row.get("use", "")
        and "not certification" not in row.get("use", "")
        and "scope rationale only" not in row.get("use", "")
        for row in rows
    ):
        raise ValueError("independent industrial reference scope drifted")


def review_capability_matrix_literal(
    matrix: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    reviewed_contract = review_contract_literal(contract)
    value = copy.deepcopy(dict(matrix))
    if (
        value.get("schema_version") != EXPECTED_CAPABILITY_SCHEMA
        or value.get("status")
        != "sealed_structure_only_evidence_capability_matrix"
        or value.get("contract_sha256") != _canonical_sha(reviewed_contract)
        or value.get("endpoint_count") != len(EXPECTED_CORE)
        or value.get("structure_only") is not True
        or value.get("outcome_values_read") is not False
        or value.get("model_pool_selector_call_count") != 0
        or value.get("old_artifact_or_cas_write_count") != 0
    ):
        raise ValueError("independent capability matrix authority drifted")
    contract_rows = {
        row["endpoint_id"]: row for row in reviewed_contract["endpoints"]
    }
    seen: set[str] = set()
    for row in value.get("rows", []):
        endpoint_id = row.get("endpoint_id")
        if endpoint_id in seen or endpoint_id not in EXPECTED_CORE:
            raise ValueError("independent capability endpoint identity drifted")
        seen.add(endpoint_id)
        source = contract_rows[endpoint_id]["source"]
        expected_root, expected_review = SOURCE_ROOTS[source]
        if (
            row.get("evidence_class") != EXPECTED_CORE[endpoint_id][3]
            or row.get("source_artifact_root_sha256") != expected_root
            or row.get("source_artifact_review_root_sha256") != expected_review
            or row.get("source_sha256") != expected_root
            or row.get("outcome_values_read") is not False
        ):
            raise ValueError(f"independent capability binding drift: {endpoint_id}")
        if row["evidence_class"] == "evidence_missing" and (
            "absent" not in row.get("reason", "")
            and "forbidden" not in row.get("reason", "")
        ):
            raise ValueError("independent missing capability reason drifted")
        if row["evidence_class"] == "scientifically_inapplicable" and (
            row.get("permanently_inapplicable_to_current_simulator") is not True
        ):
            raise ValueError("independent inapplicable capability drifted")
    if seen != set(EXPECTED_CORE):
        raise ValueError("independent capability endpoint omission")
    expected_counts = {
        name: sum(core[3] == name for core in EXPECTED_CORE.values())
        for name in EXPECTED_CLASSES
    }
    if value.get("evidence_class_counts") != expected_counts:
        raise ValueError("independent capability class counts drifted")
    return value


def independent_review_report(
    contract: Mapping[str, Any], matrix: Mapping[str, Any]
) -> dict[str, Any]:
    reviewed_contract = review_contract_literal(contract)
    reviewed_matrix = review_capability_matrix_literal(matrix, reviewed_contract)
    return {
        "schema_version": (
            "camp_dp_v25_industrial_oriented_evaluation_independent_review_v1"
        ),
        "status": "passed_independent_local_literal_industrial_evaluation_review",
        "contract_sha256": _canonical_sha(reviewed_contract),
        "capability_matrix_sha256": _canonical_sha(reviewed_matrix),
        "endpoint_count": len(EXPECTED_CORE),
        "literal_oracle": {
            "producer_module_imported": False,
            "producer_endpoint_registry_imported": False,
            "producer_formula_or_filter_imported": False,
            "producer_classification_or_decision_oracle_imported": False,
            "authority_sha_recomputed": True,
            "endpoint_topology_reconstructed": True,
            "formula_units_directions_reconstructed": True,
            "comfort_sample_and_filter_accounting_reconstructed": True,
            "source_roots_and_capability_classes_reconstructed": True,
            "statistics_missing_and_claim_boundaries_reconstructed": True,
        },
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_write_count": 0,
        "claim_authorized": False,
    }
