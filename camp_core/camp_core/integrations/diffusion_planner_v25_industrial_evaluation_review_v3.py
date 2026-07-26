from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import t as student_t

from camp_core.integrations.diffusion_planner_artifact_seal import (
    verify_complete_seal,
)
from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_review_v2 as v2_review,
)


# This separate-role oracle deliberately imports no v3 producer, metric,
# threshold, classification, or decision implementation.
EXPECTED_AUTHORITY = (
    "720e9293f88de92b08bbfab39100baf46b396ca59a5b1c9a089cde5af0bfeca5"
)
EXPECTED_SCHEMA = "camp_dp_v25_industrial_oriented_evaluation_contract_v3"
EXPECTED_CAPABILITY_SCHEMA = (
    "camp_dp_v25_industrial_oriented_evaluation_capability_matrix_v3"
)
EXPECTED_PARENT_COUNT = 56
EXPECTED_LEAF_COUNT = 161
EXPECTED_ALPHA = 0.05
EXPECTED_METHOD = "holm_bonferroni_step_down_within_exact_family"
EXPECTED_PARENT_REGISTRY_SHA256 = (
    "9f20fbbe131d4e4dcbc238bf05efb077e59032352802890f11b7e0dde327ee23"
)
EXPECTED_LEAF_REGISTRY_SHA256 = (
    "7424dc97495da577b2dc7fb612f4d5d3b56518378eb869b601d50056e6e4528e"
)
EXPECTED_CONTRACT_SHA256 = (
    "d8c7ca0ed4e59b6e3887e78cf1dea4116a1cd863ea5bed061a8e7f3afb1177db"
)

MARGIN_AUTHORITY = (
    "future_preregistered_nonnegative_leaf_margin_required_numeric_value_absent"
)
P_VALUE_RULE = (
    "n>=2 finite equal-cluster oriented deltas z; for NI use "
    "t=(mean(z)+M_leaf)/(sample_sd(z)/sqrt(n)), df=n-1, "
    "p=student_t.sf(t,df); if sample_sd=0 then p=0 iff mean(z)+M_leaf>0 "
    "else p=1; missing/nonfinite blocks the complete family"
)
HOLM_RULE = (
    "within the exact family sort by (p_value,leaf_id); at one-based rank i "
    "reject iff p_value<=0.05/(m-i+1); stop at the first non-rejection and "
    "retain that and all later leaves as not rejected; any required missing "
    "or failure blocks the complete family"
)
COLLISION_ID = (
    "safety.collision_onset_relative_closing_speed_kinematic_proxy_mps"
)
COLLISION_FORMULA = (
    "for the first full-OBB false_to_true intersection interval [t-1,t], "
    "reconstruct constant interval velocities u_ego=(p_ego[t]-p_ego[t-1])/dt "
    "and u_actor=(p_actor[t]-p_actor[t-1])/dt; obtain the earliest continuous-SAT "
    "translation entry fraction tau in [0,1] using the t-1 OBB orientations; "
    "r_tau=((1-tau)*p_actor[t-1]+tau*p_actor[t])-"
    "((1-tau)*p_ego[t-1]+tau*p_ego[t]), v_rel_tau=u_actor-u_ego, and return "
    "max(0,-dot(r_tau,v_rel_tau)/max(norm(r_tau),1e-9)); initial overlap, no "
    "preceding interval, nonfinite inputs, no finite unique SAT entry, or "
    "norm(r_tau)<=1e-9 are typed missing and never converted to zero"
)

LEAF_FIELD_ORDER = (
    "leaf_id",
    "parent_id",
    "domain",
    "units",
    "direction",
    "formula",
    "input_shape",
    "applicability",
    "opportunity_denominator",
    "missing_policy",
    "guardrail_role",
    "multiplicity_family",
    "confidence_interval",
    "familywise_method",
    "familywise_alpha",
    "claim_gate_state",
    "btw_applicability",
    "evidence_class",
    "source_binding_id",
    "test_type",
    "symbolic_margin_authority",
    "oriented_cluster_delta",
    "null_hypothesis",
    "alternative_hypothesis",
    "p_value_rule",
    "familywise_decision_rule",
)
LEAF_FIELDS = set(LEAF_FIELD_ORDER)

GROUPED = set(v2_review.GROUPED)
GRIDS = copy.deepcopy(v2_review.GRIDS)
PARENT_IDS = tuple(v2_review.PARENT_IDS)

# Exact local literals for every non-expanded parent leaf. Expanded
# threshold/stat/budget leaves are generated below from reviewer-local grids.
# leaf_id -> units, direction, formula, opportunity denominator
UNGROUPED = {
    "safety.collision_any": ("bool", "lower", "any(full_ego_OBB intersects full_actor_OBB)", "all 64 ticks and all authoritative actors per retained run"),
    "safety.collision_episode_count": ("count", "lower", "count(false_to_true transitions of full_polygon_collision_indicator)", "all 64 ticks and all authoritative actors per retained run"),
    "safety.collision_duration_s": ("s", "lower", "sum(full_polygon_collision_indicator)*0.1", "all 64 ticks and all authoritative actors per retained run"),
    COLLISION_ID: ("m/s", "lower", COLLISION_FORMULA, "one retained run"),
    "safety.collision_delta_v_mps": ("m/s", "lower", "requires authoritative contact-time body velocities and contact dynamics", "one retained run"),
    "safety.collision_contact_severity": ("severity_unit", "lower", "requires authoritative contact-time body velocities and contact dynamics", "one retained run"),
    "safety.min_full_polygon_clearance_m": ("m", "higher", "min_t,actor distance(full ego polygon,full actor polygon); intersection=0", "all authoritative ego-actor pair ticks"),
    "safety.max_closing_speed_mps": ("m/s", "lower", "max max(0,-dot(r,v_rel)/max(norm(r),1e-9))", "all authoritative ego-actor pair ticks"),
    "safety.min_geometry_ttc_s": ("s", "higher", "minimum continuous-SAT entry time for approaching OBBs within frozen 5s horizon", "all authoritative ego-actor pair ticks"),
    "safety.max_drac_mps2": ("m/s^2", "lower", "max closing^2/(2*max(clearance,1e-9)) only closing>0 and clearance>0", "all authoritative ego-actor pair ticks"),
    "safety.time_headway_s": ("s", "higher", "distance_to_unique_same_lane_leader/max(ego_speed,epsilon)", "one retained run"),
    "safety.post_encroachment_time_s": ("s", "higher", "absolute passage-time difference through one frozen conflict zone", "one retained run"),
    "safety.certified_red_crossing_any": ("bool", "lower", "any(unthresholded certified red crossing)", "encounter count and red-phase interval count reported separately and never mixed"),
    "safety.certified_red_crossing_count": ("count", "lower", "count unique certified stop-line encounters with swept crossing", "encounter count and red-phase interval count reported separately and never mixed"),
    "safety.certified_red_crossing_speed_mps": ("m/s", "lower", "interpolated speed at unthresholded swept crossing", "encounter count and red-phase interval count reported separately and never mixed"),
    "safety.certified_red_encounter_opportunity_count": ("encounter_count", "descriptive_unclassified", "count unique certified stopline identity plus contiguous encounter", "encounter count and red-phase interval count reported separately and never mixed"),
    "safety.certified_red_phase_interval_count": ("interval_count", "descriptive_unclassified", "count same-tick certified red-phase intervals", "encounter count and red-phase interval count reported separately and never mixed"),
    "safety.drivable_outside_fraction_max": ("fraction", "lower", "max area(F minus union(D))/area(F)", "64 ticks per retained run"),
    "safety.drivable_outside_duration_s": ("s", "lower", "sum(outside_fraction>1e-9)*0.1", "64 ticks per retained run"),
    "safety.drivable_outside_episode_count": ("count", "lower", "count false_to_true transitions of outside_fraction>1e-9", "64 ticks per retained run"),
    "safety.drivable_signed_clearance_min_m": ("m", "higher", "minimum signed full-footprint clearance to external boundary of union(D)", "64 ticks per retained run"),
    "safety.drivable_penetration_max_m": ("m", "lower", "maximum full-footprint penetration beyond external boundary of union(D)", "64 ticks per retained run"),
    "safety.wrong_way_duration_s": ("s", "lower", "sum(onroad and moving and unique_direction and abs(wrapped_heading_delta)>pi/2)*0.1", "one retained run"),
    "safety.wrong_way_episode_count": ("count", "lower", "false_to_true count of the same unique-direction wrong-way indicator", "one retained run"),
    "operations.speed_excess_max_mps": ("m/s", "lower", "max(max(0,speed-limit))", "one retained run"),
    "operations.speed_excess_mean_positive_mps": ("m/s", "lower", "mean(excess where excess>0), typed missing when no positive excess", "one retained run"),
    "operations.ordered_route_arc_final_m": ("m", "higher", "final stateful ordered reachable route arc s_t", "one retained run"),
    "operations.max_forward_progress_m": ("m", "higher", "max_t(s_t)-s_0 on one stateful adjacent-segment route path", "one retained run"),
    "operations.net_forward_progress_m": ("m", "higher", "s_final-s_0", "one retained run"),
    "operations.completion_fraction": ("fraction", "higher", "clip(max_forward_progress/route_length,0,1); zero route length is typed missing", "one retained run"),
    "operations.goal_distance_final_m": ("m", "lower", "norm(final_position-goal_pose)", "one retained run"),
    "operations.goal_reached": ("bool", "higher", "native runner literal goal_tolerance_m semantics", "one retained run"),
    "operations.goal_passed": ("bool", "lower", "native same-tick/contiguous goal_pass_window_m semantics", "one retained run"),
    "operations.backtracking_duration_s": ("s", "lower", "sum(max(0,s_previous-s_current)>epsilon)*0.1", "one retained run"),
    "operations.backtracking_distance_m": ("m", "lower", "sum(max(0,s_previous-s_current))", "one retained run"),
    "operations.distance_traveled_m": ("m", "descriptive_unclassified", "sum(norm(position[t]-position[t-1]))", "one retained run"),
    "operations.travel_efficiency_ratio": ("ratio", "higher", "max_forward_progress_m/distance_traveled_m; zero denominator is typed missing", "one retained run"),
    "operations.false_stop_duration_s": ("s", "lower", "duration speed<=future_preregistered_threshold during valid motion opportunity", "one retained run"),
    "operations.false_stop_episode_count": ("count", "lower", "episodes meeting future minimum duration after excluding red/obstacle/goal waits", "one retained run"),
    "comfort.planar_kinematic_vdv_like_longitudinal": ("m/s^1.75", "lower", "(sum(abs(a_filtered)^4)*0.1)^(1/4)", "one retained run"),
    "comfort.planar_kinematic_vdv_like_lateral": ("m/s^1.75", "lower", "(sum(abs(a_filtered)^4)*0.1)^(1/4)", "one retained run"),
    "comfort.occupant_seat_iso_sae_conformity": ("not_applicable", "descriptive_unclassified", "requires seat/suspension/human transfer, vertical and rotational channels, frequency weighting and qualified transducer placement", "one retained run"),
}


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


def _source(parent: str) -> str:
    if parent in {"safety.collision_delta_v_mps", "safety.collision_contact_severity"}:
        return "missing_contact_dynamics"
    if parent == "safety.time_headway_s":
        return "missing_unique_leader"
    if parent == "safety.post_encroachment_time_s":
        return "missing_conflict_zone"
    if parent.startswith("operations.false_stop_"):
        return "missing_false_stop_context"
    if parent == "comfort.occupant_seat_iso_sae_conformity":
        return "inapplicable_occupant_conformity"
    if parent.startswith("realtime."):
        return "missing_target_runtime"
    if parent.startswith("comfort."):
        return "execution_planar_motion"
    if parent.startswith("operations.speed_") or parent.startswith("safety.certified_red_"):
        return "execution_red_speed"
    if parent.startswith("operations.") or parent.startswith("safety.drivable_") or parent.startswith("safety.wrong_way_"):
        return "execution_route_map"
    return "execution_kinematics_geometry"


def _evidence_class(binding: str) -> str:
    if binding == "inapplicable_occupant_conformity":
        return "scientifically_inapplicable"
    if binding.startswith("missing_"):
        return "evidence_missing"
    return "reconstructable_with_frozen_transform"


def _role(parent: str, evidence_class: str, direction: str) -> str:
    if evidence_class in {"evidence_missing", "scientifically_inapplicable"}:
        return "evidence_missing_not_testable"
    if parent.startswith(
        (
            "safety.collision_",
            "safety.certified_red_crossing",
            "safety.drivable_",
            "safety.wrong_way_",
        )
    ):
        return "hard_safety"
    if direction == "descriptive_unclassified" or parent.endswith(
        ("opportunity_count", "interval_count", "distance_traveled_m")
    ):
        return "descriptive_only"
    return "guardrail"


def _family(parent: str, role: str) -> str:
    if role == "evidence_missing_not_testable":
        return "not_testable"
    if role == "descriptive_only":
        return "descriptive_only_not_tested"
    if parent.startswith("safety.collision_"):
        return "hard_safety_collision"
    if parent.startswith("safety.certified_red_"):
        return "hard_safety_red"
    if parent.startswith(("safety.drivable_", "safety.wrong_way_")):
        return "hard_safety_containment_direction"
    if parent.startswith("safety."):
        return "safety_dynamic_exposure_guardrails"
    if parent.startswith("operations."):
        return "operations_guardrails"
    if parent.startswith("comfort."):
        return "planar_kinematic_proxy_guardrails"
    if parent.startswith("realtime."):
        return "controlled_benchmark_realtime_guardrails"
    raise ValueError(parent)


def _expanded_semantics() -> dict[str, tuple[str, str, str, str, str]]:
    # leaf -> parent, units, direction, formula, denominator
    result: dict[str, tuple[str, str, str, str, str]] = {
        leaf: (leaf, units, direction, formula, denominator)
        for leaf, (units, direction, formula, denominator) in UNGROUPED.items()
    }
    for parent in (
        "safety.critical_exposure_duration_s",
        "safety.critical_exposure_episode_count",
    ):
        suffix = "duration_s" if parent.endswith("duration_s") else "episode_count"
        units = "s" if suffix == "duration_s" else "count"
        for family, comparator, token_comp, unit in (
            ("clearance_m", "<=", "le", "m"),
            ("ttc_s", "<=", "le", "s"),
            ("closing_mps", ">=", "ge", "mps"),
            ("drac_mps2", ">=", "ge", "mps2"),
        ):
            for token, value in GRIDS[family]:
                leaf = f"safety.{family}_{token_comp}_{token}{unit}_{suffix}"
                formula = (
                    f"{suffix}(per_tick_{family}{comparator}{value}); "
                    "duration uses indicator_count*0.1 and episode uses false_to_true"
                )
                result[leaf] = (
                    parent,
                    units,
                    "lower",
                    formula,
                    "all authoritative ego-actor pair ticks",
                )
    for token, value in GRIDS["speed"]:
        result[f"operations.speed_excess_gt_{token}mps_duration_s"] = (
            "operations.speed_excess_duration_s",
            "s",
            "lower",
            f"sum(I(max(0,speed-limit)>{value}))*0.1",
            "one retained run",
        )
        result[f"operations.speed_excess_magnitude_above_{token}mps_duration_m"] = (
            "operations.speed_excess_magnitude_duration_m",
            "m",
            "lower",
            f"sum(max(0,max(0,speed-limit)-{value}))*0.1",
            "one retained run",
        )
    for axis in ("longitudinal", "lateral"):
        parent = f"comfort.body_{axis}_filtered_acceleration_summary"
        for stat, direction in (
            ("signed_mean", "descriptive_unclassified"),
            ("rms", "lower"),
            ("min", "descriptive_unclassified"),
            ("max", "descriptive_unclassified"),
            ("peak_abs", "lower"),
            ("abs_p50", "lower"),
            ("abs_p90", "lower"),
            ("abs_p95", "lower"),
            ("abs_p99", "lower"),
        ):
            result[f"comfort.body_{axis}_filtered_acceleration_{stat}"] = (
                parent,
                "m/s^2",
                direction,
                f"{stat} over 52 valid-only filtered body-{axis} acceleration samples",
                "52 filtered samples per retained run",
            )
        for token, value in GRIDS["acceleration"]:
            result[f"comfort.body_{axis}_filtered_acceleration_abs_gt_{token}mps2_duration_s"] = (
                parent,
                "s",
                "lower",
                f"sum(I(abs(a_{axis}_filtered)>{value}))*0.1",
                "52 filtered samples per retained run",
            )
        parent = f"comfort.filtered_{axis}_jerk_control_smoothness_summary"
        for stat in ("rms", "peak_abs", "abs_p95"):
            result[f"comfort.filtered_{axis}_jerk_control_smoothness_{stat}"] = (
                parent,
                "m/s^3",
                "lower",
                f"{stat} over 51 diff(filtered body-{axis} acceleration)/0.1 samples",
                "51 filtered-jerk samples per retained run",
            )
        for token, value in GRIDS["jerk"]:
            result[f"comfort.filtered_{axis}_jerk_abs_gt_{token}mps3_duration_s"] = (
                parent,
                "s",
                "lower",
                f"sum(I(abs(jerk_{axis}_filtered)>{value}))*0.1",
                "51 filtered-jerk samples per retained run",
            )
    for stage in (
        "pool_generation",
        "atoms",
        "context_weights",
        "selector_increment",
        "end_to_end",
    ):
        parent = f"realtime.{stage}_latency_ms"
        for stat in ("mean", "median", "p95", "p99", "max"):
            result[f"realtime.{stage}_latency_{stat}_ms"] = (
                parent,
                "ms",
                "lower",
                f"{stat} of empirical per-run {stage} stage timing",
                "64 timed ticks per retained future target-architecture run",
            )
    parent = "realtime.hypothetical_budget_exceedance"
    for token, value in GRIDS["latency"]:
        result[f"realtime.end_to_end_exceedance_rate_{token}ms"] = (
            parent,
            "rate",
            "lower",
            f"count(end_to_end_latency_ms>{value})/64",
            "64 timed ticks per retained future target-architecture run",
        )
        result[f"realtime.end_to_end_max_overrun_{token}ms_ms"] = (
            parent,
            "ms",
            "lower",
            f"max(0,max(end_to_end_latency_ms)-{value})",
            "64 timed ticks per retained future target-architecture run",
        )
    if len(result) != EXPECTED_LEAF_COUNT:
        raise AssertionError(len(result))
    return result


def _expected_test_fields(
    leaf_id: str, parent: str, direction: str, role: str
) -> dict[str, Any]:
    if role in {"hard_safety", "guardrail"}:
        return {
            "multiplicity_family": _family(parent, role),
            "confidence_interval": (
                "unadjusted_one_sided_95pct_oriented_lower_bound_descriptive_only_"
                "not_familywise_claim_evidence"
            ),
            "familywise_method": EXPECTED_METHOD,
            "familywise_alpha": EXPECTED_ALPHA,
            "claim_gate_state": (
                "numeric_margin_not_authorized_until_future_preregistration"
            ),
            "btw_applicability": (
                "future_paired_unit_better_tie_worse_on_oriented_delta_exact_zero_tie"
            ),
            "test_type": "noninferiority",
            "symbolic_margin_authority": (
                f"M[{leaf_id}]>=0;" + MARGIN_AUTHORITY
            ),
            "oriented_cluster_delta": (
                "z_j=baseline_cluster_mean_j-method_cluster_mean_j"
                if direction == "lower"
                else "z_j=method_cluster_mean_j-baseline_cluster_mean_j"
            ),
            "null_hypothesis": "H0:mu_z<=-M_leaf",
            "alternative_hypothesis": "H1:mu_z>-M_leaf",
            "p_value_rule": P_VALUE_RULE,
            "familywise_decision_rule": HOLM_RULE,
        }
    if role == "descriptive_only":
        return {
            "multiplicity_family": "descriptive_only_not_tested",
            "confidence_interval": (
                "unadjusted_two_sided_95pct_equal_cluster_student_t_"
                "descriptive_only_not_familywise"
            ),
            "familywise_method": "none_descriptive_only",
            "familywise_alpha": None,
            "claim_gate_state": "descriptive_only_not_claim_gate",
            "btw_applicability": "not_applicable",
            "test_type": "descriptive",
            "symbolic_margin_authority": "not_applicable",
            "oriented_cluster_delta": "not_applicable",
            "null_hypothesis": "not_applicable",
            "alternative_hypothesis": "not_applicable",
            "p_value_rule": "not_applicable",
            "familywise_decision_rule": "not_applicable",
        }
    return {
        "multiplicity_family": "not_testable",
        "confidence_interval": "none_not_testable",
        "familywise_method": "none_not_testable",
        "familywise_alpha": None,
        "claim_gate_state": "not_testable_evidence_missing",
        "btw_applicability": "not_applicable",
        "test_type": "not_testable",
        "symbolic_margin_authority": "not_applicable",
        "oriented_cluster_delta": "not_applicable",
        "null_hypothesis": "not_applicable",
        "alternative_hypothesis": "not_applicable",
        "p_value_rule": "not_applicable",
        "familywise_decision_rule": "not_applicable",
    }


def review_contract_v3_literal(contract: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(contract))
    if (
        value.get("schema_version") != EXPECTED_SCHEMA
        or value.get("high_authority_sha256") != EXPECTED_AUTHORITY
        or value.get("parent_endpoint_count") != EXPECTED_PARENT_COUNT
        or value.get("scalar_leaf_count") != EXPECTED_LEAF_COUNT
    ):
        raise ValueError("independent v3 authority/count drifted")
    parents = value.get("parent_endpoints")
    if (
        not isinstance(parents, list)
        or [row.get("endpoint_id") for row in parents] != list(PARENT_IDS)
        or _canonical_sha(parents) != EXPECTED_PARENT_REGISTRY_SHA256
    ):
        raise ValueError("independent v3 parent literal registry drifted")
    onset_parent = parents[3]
    if (
        onset_parent.get("formula") != COLLISION_FORMULA
        or "initial overlap" not in onset_parent.get("missing_policy", "")
        or "unique translation-SAT" not in onset_parent.get("applicability", "")
    ):
        raise ValueError("independent v3 collision onset parent drifted")
    parent_map = {row["endpoint_id"]: row for row in parents}
    expected = _expanded_semantics()
    rows = value.get("scalar_leaf_registry")
    if (
        not isinstance(rows, list)
        or len(rows) != EXPECTED_LEAF_COUNT
        or _canonical_sha(rows) != EXPECTED_LEAF_REGISTRY_SHA256
        or value.get("scalar_leaf_required_fields") != list(LEAF_FIELD_ORDER)
    ):
        raise ValueError("independent v3 leaf registry byte/schema drifted")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != LEAF_FIELDS:
            raise ValueError("independent v3 leaf schema drifted")
        leaf_id = row["leaf_id"]
        if leaf_id in seen or leaf_id not in expected:
            raise ValueError("independent v3 leaf unknown/duplicate")
        seen.add(leaf_id)
        parent, units, direction, formula, denominator = expected[leaf_id]
        parent_row = parent_map[parent]
        binding = _source(parent)
        evidence_class = _evidence_class(binding)
        role = _role(parent, evidence_class, direction)
        exact = {
            "parent_id": parent,
            "domain": parent_row["domain"],
            "units": units,
            "direction": direction,
            "formula": formula,
            "input_shape": parent_row["input_shape"],
            "applicability": parent_row["applicability"],
            "opportunity_denominator": denominator,
            "missing_policy": parent_row["missing_policy"],
            "guardrail_role": role,
            "evidence_class": evidence_class,
            "source_binding_id": binding,
            **_expected_test_fields(leaf_id, parent, direction, role),
        }
        for field, expected_value in exact.items():
            if row.get(field) != expected_value:
                raise ValueError(
                    f"independent v3 scalar semantic drift: {leaf_id}/{field}"
                )
    if seen != set(expected):
        raise ValueError("independent v3 scalar leaf omission")
    topology = value.get("decision_topology")
    if (
        topology.get("familywise_method") != EXPECTED_METHOD
        or topology.get("familywise_alpha") != EXPECTED_ALPHA
        or topology.get("holm_order") != "stable_ascending_(p_value,leaf_id)"
        or topology.get("holm_comparison") != "p_value<=alpha/(m-i+1)"
        or topology.get("holm_stop_rule") != "stop_at_first_non_rejection"
        or topology.get("minimum_cluster_count") != 2
        or topology.get("current_claim_gate_authorized") is not False
        or topology.get("weighted_compensation_allowed") is not False
        or topology.get("ordinary_ci_role")
        != (
            "unadjusted 95pct intervals are descriptive only and never familywise "
            "claim evidence; familywise decisions use frozen Holm-adjusted p-values"
        )
    ):
        raise ValueError("independent v3 executable decision topology drifted")
    family_members = {
        leaf_id
        for members in topology["tested_families"].values()
        for leaf_id in members
    }
    expected_tested = {
        row["leaf_id"] for row in rows if row["test_type"] == "noninferiority"
    }
    if family_members != expected_tested:
        raise ValueError("independent v3 exact family membership drifted")
    if (
        value.get("claim_authorized") is not False
        or value.get("outcome_values_read") is not False
        or value.get("model_pool_selector_call_count") != 0
        or value.get("old_artifact_or_cas_write_count") != 0
        or value.get("evaluation_and_selector_training_decoupled") is not True
        or _canonical_sha(value) != EXPECTED_CONTRACT_SHA256
    ):
        raise ValueError("independent v3 no-run/no-claim or payload drifted")
    return value


def local_one_sided_student_t_p_value(
    oriented_deltas: Sequence[float], margin: float
) -> float:
    values = np.asarray(oriented_deltas, dtype=np.float64)
    if values.ndim != 1 or values.size < 2 or not np.all(np.isfinite(values)):
        raise ValueError("independent p-value input invalid")
    if not math.isfinite(margin) or margin < 0:
        raise ValueError("independent NI margin invalid")
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1))
    numerator = mean + margin
    if sd == 0:
        return 0.0 if numerator > 0 else 1.0
    return float(student_t.sf(numerator / (sd / math.sqrt(values.size)), values.size - 1))


def local_holm_step_down(
    p_values: Mapping[str, float], expected_leaf_ids: Sequence[str]
) -> list[tuple[str, bool]]:
    expected = tuple(sorted(expected_leaf_ids))
    if not expected or set(p_values) != set(expected):
        raise ValueError("independent Holm family incomplete")
    rows = sorted((float(value), leaf_id) for leaf_id, value in p_values.items())
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value, _ in rows):
        raise ValueError("independent Holm p invalid")
    stopped = False
    decisions = []
    for index, (p_value, leaf_id) in enumerate(rows, start=1):
        rejected = (not stopped) and p_value <= EXPECTED_ALPHA / (
            len(rows) - index + 1
        )
        if not rejected:
            stopped = True
        decisions.append((leaf_id, rejected))
    return decisions


def _read_inventory(path: Path) -> dict[str, str]:
    result = {}
    for line in (path / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        sha, name = line.split("  ", 1)
        result[name] = sha
    return result


def _pointer(value: Any, pointer: str) -> Any:
    current = value
    for token in pointer.split("/")[1:]:
        if not isinstance(current, Mapping) or token not in current:
            raise ValueError(f"independent v3 missing pointer: {pointer}")
        current = current[token]
    return current


def review_capability_v3_literal(
    matrix: Mapping[str, Any],
    contract: Mapping[str, Any],
    source_dirs: Mapping[str, str | Path],
) -> dict[str, Any]:
    reviewed = review_contract_v3_literal(contract)
    value = copy.deepcopy(dict(matrix))
    if set(source_dirs) != set(v2_review.SOURCE_ROOTS):
        raise ValueError("independent v3 sealed source set drifted")
    inventories = {}
    reports = {}
    for name, (root, entries) in v2_review.SOURCE_ROOTS.items():
        path = Path(source_dirs[name])
        verify_complete_seal(path, root)
        actual = _read_inventory(path)
        if any(actual.get(filename) != sha for filename, sha in entries.items()):
            raise ValueError(f"independent v3 sealed inventory drifted: {name}")
        selected = {filename: actual[filename] for filename in sorted(entries)}
        inventories[name] = {
            "artifact_root_sha256": root,
            "artifact_review_root_sha256": v2_review.SOURCE_REVIEW_ROOTS[name],
            "inventory_manifest_sha256": _canonical_sha(selected),
            "entries": selected,
        }
        if name in {"evaluation_v2_contract", "metric_contract"}:
            reports[name] = json.loads(
                (path / "report.json").read_text(encoding="utf-8")
            )
    if (
        value.get("schema_version") != EXPECTED_CAPABILITY_SCHEMA
        or value.get("contract_sha256") != EXPECTED_CONTRACT_SHA256
        or value.get("scalar_leaf_count") != EXPECTED_LEAF_COUNT
        or value.get("sealed_inventory_audit") != inventories
        or value.get("structure_only") is not True
        or value.get("outcome_values_read") is not False
        or value.get("model_pool_selector_call_count") != 0
        or value.get("old_artifact_or_cas_write_count") != 0
    ):
        raise ValueError("independent v3 capability authority drifted")
    leaves = {row["leaf_id"]: row for row in reviewed["scalar_leaf_registry"]}
    rows = value.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_LEAF_COUNT:
        raise ValueError("independent v3 capability row count drifted")
    seen = set()
    for row in rows:
        leaf_id = row.get("leaf_id")
        if leaf_id in seen or leaf_id not in leaves:
            raise ValueError("independent v3 capability leaf drifted")
        seen.add(leaf_id)
        leaf = leaves[leaf_id]
        binding = _source(leaf["parent_id"])
        if (
            row.get("parent_id") != leaf["parent_id"]
            or row.get("evidence_class") != _evidence_class(binding)
            or row.get("canonical_json_pointers") != list(v2_review.POINTERS[binding])
            or row.get("source_shape") is None
            or row.get("source_units") is None
            or row.get("structure_only") is not True
            or row.get("outcome_values_read") is not False
        ):
            raise ValueError("independent v3 capability semantic drifted")
        for pointer in v2_review.POINTERS[binding]:
            report_name = (
                "metric_contract"
                if pointer.startswith("/contract/body_proxy/")
                else "evaluation_v2_contract"
            )
            _pointer(reports[report_name], pointer)
        expected_evidence = []
        for artifact_name in v2_review.ARTIFACTS_BY_BINDING[binding]:
            inventory = inventories[artifact_name]
            for filename, sha in inventory["entries"].items():
                expected_evidence.append(
                    {
                        "artifact_name": artifact_name,
                        "artifact_root_sha256": inventory["artifact_root_sha256"],
                        "artifact_review_root_sha256": inventory[
                            "artifact_review_root_sha256"
                        ],
                        "inventory_file": filename,
                        "inventory_file_sha256": sha,
                        "inventory_manifest_sha256": inventory[
                            "inventory_manifest_sha256"
                        ],
                    }
                )
        if row.get("evidence_inventory") != expected_evidence:
            raise ValueError("independent v3 capability inventory drifted")
    if seen != set(leaves):
        raise ValueError("independent v3 capability omission")
    return value
