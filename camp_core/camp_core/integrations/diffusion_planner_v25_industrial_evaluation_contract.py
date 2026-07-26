from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA_VERSION = "camp_dp_v25_industrial_oriented_evaluation_contract_v1"
STATUS = "frozen_outcome_independent_industrial_oriented_evaluation_contract"
CAPABILITY_SCHEMA_VERSION = (
    "camp_dp_v25_industrial_oriented_evaluation_capability_matrix_v1"
)
HIGH_AUTHORITY_SHA256 = (
    "720e9293f88de92b08bbfab39100baf46b396ca59a5b1c9a089cde5af0bfeca5"
)
HIGH_AUTHORITY_JSON = (
    '{"claim_authorized":false,"comfort_claim_scope":"planar_vehicle_body_'
    'kinematic_proxy_not_occupant_seat_iso_sae_conformity","control_source_'
    'thread_id":"019f6eee-8fc2-75f3-843c-75562f610b13","decision":"authorize_'
    'zero_model_zero_outcome_evaluation_system_amendment_and_independent_review",'
    '"deliverables":["versioned_evaluation_contract","sealed_evidence_capability_'
    'matrix","independent_literal_review","adversarial_tdd","migration_matrix",'
    '"future_experiment_endpoint_plan","current_status_and_audit_pointer"],'
    '"endpoint_domains":["safety","operations","vehicle_body_planar_kinematic_'
    'comfort_proxy","controlled_benchmark_realtime"],"evidence_classes":['
    '"directly_reconstructable","reconstructable_with_frozen_transform",'
    '"evidence_missing","scientifically_inapplicable"],"executor_thread_id":'
    '"019f92f5-eb4e-78d1-88ea-8ee1f4335eb3","fixed_dp_head":'
    '"7a1d33da277a1992ec474b5383a0c963c72e04e4","fresh_or_b4_outcome_read_'
    'authorized":false,"legacy_safetycost_role":"immutable_legacy_exploratory_'
    'diagnostic_only","live_base_head":"456aabb70308271f4b7b1dcb30550fe5574fc389",'
    '"model_pool_selector_training_calibration_validation_closed_loop_fresh_'
    'holdout_authorized":false,"new_weighted_total_allowed":false,"old_artifact_'
    'or_cas_write_authorized":false,"old_evaluation_rerun_authorized":false,'
    '"ordinary_engineering_repairs_within_stage_allowed":true,"per_endpoint_'
    'contract_fields":["source","source_sha256","units","sample_rate",'
    '"coordinate_frame","filter","window","edge_handling","event_definition",'
    '"opportunity_denominator","per_run_aggregation","cluster_unit","confidence_'
    'interval","multiplicity","noninferiority_or_guardrail","missing_policy",'
    '"failure_full_denominator_policy","evidence_class"],"producer_reviewer_'
    'shared_metric_or_decision_oracle_allowed":false,"raw_point_one_second_'
    'differencing_as_occupant_jerk_allowed":false,"return_to_control_after_'
    'merged_package":true,"schema_version":"camp_dp_v25_industrial_oriented_'
    'evaluation_system_amendment_high_authority_v1","selector_training_and_'
    'final_evaluation_decoupled":true,"superseded_model_authorities":['
    '"1c3f6c17db7c75883e7f1ffad447c5677dbbaaefa3eb9342dbbc069350dbf86c",'
    '"05bcdc5fe649a9390243588245602402c065bc326d03ad8802704066f590640e"]}'
)

FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
BASE_HEAD = "456aabb70308271f4b7b1dcb30550fe5574fc389"
EXECUTION_ROOT = "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
EXECUTION_REVIEW_ROOT = (
    "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d"
)
CORRECTED_EVALUATION_ROOT = (
    "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f"
)
CORRECTED_EVALUATION_REVIEW_ROOT = (
    "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459"
)
EVALUATION_V2_CONTRACT_ROOT = (
    "99501763a4a88c9d80fff738054b37593717df0b6d33e3749ad451d9e52a15e0"
)
EVALUATION_V2_REVIEW_ROOT = (
    "a7ba686647ccfe64f45a3304a00a392c1a362534833023fe26e0343a374bfac0"
)
EVALUATION_V2_MATERIALIZATION_ROOT = (
    "4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941"
)
EVALUATION_V2_MATERIALIZATION_REVIEW_ROOT = (
    "e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b"
)
METRIC_SEMANTICS_CONTRACT_ROOT = (
    "318e85f9656a5dd79c9fb0ad6c1dfcd94678b35c4aba455f3909cf3475cca758"
)
METRIC_SEMANTICS_REVIEW_ROOT = (
    "fc04fd6e45487df6c9bf5313b9ee6d633f91303e0a1aa00f0a3114b8134fea95"
)
METRIC_SEMANTICS_ROOT = (
    "99fd5e571160a3ac3d5bb2b6d6f3391c3da5965bf592707ff85c88080ac2dbcf"
)
METRIC_SEMANTICS_AMENDMENT_REVIEW_ROOT = (
    "88b35ab8ef51807c848200675ceeebe6b26e15a4f4b34da51f131e9303f37898"
)

DT_S = 0.1
SAMPLE_RATE_HZ = 10.0
TICK_COUNT = 64
INTERVAL_VELOCITY_COUNT = 63
RAW_ACCELERATION_COUNT = 62
FILTER_WIDTH = 11
FILTERED_ACCELERATION_COUNT = 52
FILTERED_JERK_COUNT = 51
BOXCAR_COEFFICIENTS = tuple([1.0 / 11.0] * 11)
ACCELERATION_SENSITIVITY_MPS2 = (0.5, 1.0, 2.0, 3.0)
JERK_SENSITIVITY_MPS3 = (0.5, 1.0, 2.0, 5.0)
LATENCY_BUDGETS_MS = (50.0, 100.0, 200.0, 500.0, 1000.0)

EVIDENCE_CLASSES = (
    "directly_reconstructable",
    "reconstructable_with_frozen_transform",
    "evidence_missing",
    "scientifically_inapplicable",
)
DOMAINS = (
    "safety",
    "operations",
    "vehicle_body_planar_kinematic_comfort_proxy",
    "controlled_benchmark_realtime",
)
STATUS_ENUM = (
    "defined_not_materialized",
    "evidence_missing",
    "scientifically_inapplicable",
)
ENDPOINT_FIELDS = (
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
)

LEGACY_SAFETYCOST_FORMULA = (
    "100*collision_any + 10*near_tick_rate + 20*offroad_tick_rate + "
    "20*wrongway_tick_rate + 30*red_any + 10*speed_tick_rate"
)
LEGACY_FIELDS = {
    "legacy.safetycost": "legacy_project_defined_controlled_benchmark_safetycost",
    "legacy.collision": "simulation_obb_overlap_any",
    "legacy.near_miss": "noncollision_obb_clearance_le_2m_tick_rate",
    "legacy.offroad": "five_point_drivable_coverage_failure_tick_rate",
    "legacy.wrong_way": (
        "nearest_route_segment_heading_opposition_moving_onroad_tick_rate"
    ),
    "legacy.red": "certified_red_phase_stopline_crossing_gt_0_5mps_any",
    "legacy.speed": "onroad_speed_excess_gt_0_1mps_tick_rate",
}

SOURCE_AUTHORITIES = {
    "sealed_execution": {
        "artifact_root_sha256": EXECUTION_ROOT,
        "artifact_review_root_sha256": EXECUTION_REVIEW_ROOT,
        "file": "runs/*/{run_config.json,native receipt JSON}",
        "schema_fields": (
            "position_xy,ego_heading_rad,speed_mps,controlled_scene actors,"
            "map/routes/spawn_config,red phase/stopline,stage_latency_ns"
        ),
        "source_sha256": EXECUTION_ROOT,
    },
    "sealed_corrected_evaluation": {
        "artifact_root_sha256": CORRECTED_EVALUATION_ROOT,
        "artifact_review_root_sha256": CORRECTED_EVALUATION_REVIEW_ROOT,
        "file": "report.json",
        "schema_fields": "aggregate-only legacy values and latency summaries",
        "source_sha256": CORRECTED_EVALUATION_ROOT,
    },
    "sealed_evaluation_v2_contract": {
        "artifact_root_sha256": EVALUATION_V2_CONTRACT_ROOT,
        "artifact_review_root_sha256": EVALUATION_V2_REVIEW_ROOT,
        "file": "report.json",
        "schema_fields": "source capability inventory and frozen transforms",
        "source_sha256": EVALUATION_V2_CONTRACT_ROOT,
    },
    "sealed_evaluation_v2_materialization": {
        "artifact_root_sha256": EVALUATION_V2_MATERIALIZATION_ROOT,
        "artifact_review_root_sha256": EVALUATION_V2_MATERIALIZATION_REVIEW_ROOT,
        "file": "report.json",
        "schema_fields": "exploratory endpoint availability only; values not read",
        "source_sha256": EVALUATION_V2_MATERIALIZATION_ROOT,
    },
    "sealed_metric_semantics": {
        "artifact_root_sha256": METRIC_SEMANTICS_ROOT,
        "artifact_review_root_sha256": METRIC_SEMANTICS_AMENDMENT_REVIEW_ROOT,
        "file": "report.json",
        "schema_fields": "64->63->62->52 planar transform and legacy aliases",
        "source_sha256": METRIC_SEMANTICS_ROOT,
    },
    "future_same_ego_batch8_instrumentation": {
        "artifact_root_sha256": None,
        "artifact_review_root_sha256": None,
        "file": None,
        "schema_fields": None,
        "source_sha256": None,
    },
    "no_credible_sealed_source": {
        "artifact_root_sha256": None,
        "artifact_review_root_sha256": None,
        "file": None,
        "schema_fields": None,
        "source_sha256": None,
    },
}


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _spec(
    endpoint_id: str,
    domain: str,
    direction: str,
    formula: str,
    units: str,
    source: str,
    evidence_class: str,
    *,
    input_shape: str,
    applicability: str = "all retained runs when required inputs are authoritative",
    event_definition: str = "not_an_event_endpoint",
    opportunity_denominator: str = "one retained run",
    aggregation: str = "compute per run before any paired or cluster aggregation",
    legacy_alias: str | None = None,
    industrial_interpretation: str = (
        "controlled_benchmark_endpoint_not_industrial_certification"
    ),
    coordinate_frame: str = "world_xy_or_explicitly_named_scalar",
    filter_name: str = "none",
    window: str = "full retained 64-tick run",
    edge_handling: str = "retain full planned run; typed missing on unavailable input",
    sample_rate: str | None = None,
) -> dict[str, Any]:
    authority = SOURCE_AUTHORITIES[source]
    missing = evidence_class in {"evidence_missing", "scientifically_inapplicable"}
    return {
        "endpoint_id": endpoint_id,
        "domain": domain,
        "direction": direction,
        "formula": formula,
        "input_shape": input_shape,
        "applicability": applicability,
        "finite_rules": (
            "all numeric inputs and outputs finite; nonfinite becomes typed missing, "
            "never zero, clamp, drop, or complete-case"
        ),
        "status_enum": (
            "scientifically_inapplicable"
            if evidence_class == "scientifically_inapplicable"
            else "evidence_missing"
            if missing
            else "defined_not_materialized"
        ),
        "legacy_alias": legacy_alias,
        "industrial_interpretation": industrial_interpretation,
        "source": source,
        "source_sha256": authority["source_sha256"],
        "units": units,
        "sample_rate": (
            sample_rate
            if sample_rate is not None
            else "10 Hz (dt=0.1 s)"
            if "tick" in input_shape or "position" in input_shape or "latency" in input_shape
            else "per_run"
        ),
        "coordinate_frame": coordinate_frame,
        "filter": filter_name,
        "window": window,
        "edge_handling": edge_handling,
        "event_definition": event_definition,
        "opportunity_denominator": opportunity_denominator,
        "per_run_aggregation": aggregation,
        "cluster_unit": (
            "future preregistered scenario/corridor-intersection cluster; "
            "ticks, rows, arms, and seeds are not independent n"
        ),
        "confidence_interval": (
            "future equal-cluster-weight Student-t CI95 after per-run and "
            "within-cluster aggregation"
        ),
        "multiplicity": (
            "endpoint vector; future familywise method must be prospectively "
            "registered before outcome access"
        ),
        "noninferiority_or_guardrail": (
            "numeric_margin_not_authorized_until_future_preregistration"
        ),
        "missing_policy": (
            "typed evidence_missing retained in planned denominator; no zero "
            "substitution and no complete-case claim"
        ),
        "failure_full_denominator_policy": (
            "retain every planned run, failure, and missing opportunity in the "
            "full denominator; paired inference unavailable if either arm is missing"
        ),
        "evidence_class": evidence_class,
    }


def _endpoint_specs() -> list[dict[str, Any]]:
    s: list[dict[str, Any]] = []
    add = s.append
    for endpoint_id, direction, formula, units in (
        ("safety.collision_any", "lower", "any(full_ego_OBB intersects full_actor_OBB)", "bool"),
        (
            "safety.collision_episode_count",
            "lower",
            "count(false_to_true transitions of full_polygon_collision_indicator)",
            "count",
        ),
        (
            "safety.collision_duration_s",
            "lower",
            "sum(full_polygon_collision_indicator)*0.1",
            "s",
        ),
    ):
        add(
            _spec(
                endpoint_id,
                "safety",
                direction,
                formula,
                units,
                "sealed_execution",
                "reconstructable_with_frozen_transform",
                input_shape="per_tick ego and actor pose+length+width",
                event_definition="full OBB polygon intersection, false->true starts episode",
                opportunity_denominator="all 64 ticks and all authoritative actors per retained run",
            )
        )
    for endpoint_id, units, interpretation in (
        (
            "safety.collision_impact_relative_speed_proxy_mps",
            "m/s",
            "kinematic proxy only, never contact severity",
        ),
        ("safety.collision_delta_v_mps", "m/s", "not available from this simulator evidence"),
        (
            "safety.collision_contact_severity",
            "severity_unit",
            "scientifically unavailable; collision_any is not severity",
        ),
    ):
        add(
            _spec(
                endpoint_id,
                "safety",
                "lower",
                "requires authoritative contact-time body velocities and contact dynamics",
                units,
                "no_credible_sealed_source",
                "evidence_missing",
                input_shape="contact-event dynamics unavailable",
                industrial_interpretation=interpretation,
            )
        )
    dynamic = (
        (
            "safety.min_full_polygon_clearance_m",
            "higher",
            "min_t,actor distance(full ego polygon,full actor polygon); intersection=0",
            "m",
        ),
        (
            "safety.max_closing_speed_mps",
            "lower",
            "max max(0,-dot(r,v_rel)/max(norm(r),1e-9))",
            "m/s",
        ),
        (
            "safety.min_geometry_ttc_s",
            "higher",
            "minimum continuous-SAT entry time for approaching OBBs within frozen 5s horizon",
            "s",
        ),
        (
            "safety.max_drac_mps2",
            "lower",
            "max closing^2/(2*max(clearance,1e-9)) only closing>0 and clearance>0",
            "m/s^2",
        ),
        (
            "safety.critical_exposure_duration_s",
            "lower",
            "sum(project-descriptive threshold indicator)*0.1 for each separately reported grid",
            "s",
        ),
        (
            "safety.critical_exposure_episode_count",
            "lower",
            "false_to_true count for each separately reported descriptive threshold grid",
            "count",
        ),
    )
    for endpoint_id, direction, formula, units in dynamic:
        add(
            _spec(
                endpoint_id,
                "safety",
                direction,
                formula,
                units,
                "sealed_execution",
                "reconstructable_with_frozen_transform",
                input_shape="per_tick ego+actor full polygons and kinematic state",
                event_definition=(
                    "descriptive grids only: clearance<=0/0.5/1/2m, TTC<=0.5/1/2/3/5s, "
                    "closing>=0.5/1/2/5m/s, DRAC>=0.5/1/2/3/5m/s2"
                ),
                opportunity_denominator="all authoritative ego-actor pair ticks",
            )
        )
    for endpoint_id, formula in (
        (
            "safety.time_headway_s",
            "distance_to_unique_same_lane_leader/max(ego_speed,epsilon)",
        ),
        (
            "safety.post_encroachment_time_s",
            "absolute passage-time difference through one frozen conflict zone",
        ),
    ):
        add(
            _spec(
                endpoint_id,
                "safety",
                "higher",
                formula,
                "s",
                "no_credible_sealed_source",
                "evidence_missing",
                input_shape="unique leader/lane or conflict-zone passage authority absent",
                applicability="only with unambiguous frozen semantic authority",
            )
        )
    red = (
        ("safety.certified_red_crossing_any", "bool", "any(unthresholded certified red crossing)"),
        (
            "safety.certified_red_crossing_count",
            "count",
            "count unique certified stop-line encounters with swept crossing",
        ),
        (
            "safety.certified_red_crossing_speed_mps",
            "m/s",
            "interpolated speed at unthresholded swept crossing",
        ),
        (
            "safety.certified_red_encounter_opportunity_count",
            "encounter_count",
            "count unique certified stopline identity plus contiguous encounter",
        ),
        (
            "safety.certified_red_phase_interval_count",
            "interval_count",
            "count same-tick certified red-phase intervals",
        ),
    )
    for endpoint_id, units, formula in red:
        add(
            _spec(
                endpoint_id,
                "safety",
                "lower" if "opportunity" not in endpoint_id and "interval" not in endpoint_id else "descriptive_unclassified",
                formula,
                units,
                "sealed_execution",
                "reconstructable_with_frozen_transform",
                input_shape="per_tick certified phase, exact stopline, full front edge pose interval",
                event_definition=(
                    "same-tick certified red plus route-specific stopline swept front/footprint crossing; "
                    "no speed threshold, so 0.4m/s crossing remains a crossing"
                ),
                opportunity_denominator=(
                    "encounter count and red-phase interval count reported separately and never mixed"
                ),
            )
        )
    containment = (
        ("safety.drivable_outside_fraction_max", "fraction", "max area(F minus union(D))/area(F)"),
        ("safety.drivable_outside_duration_s", "s", "sum(outside_fraction>1e-9)*0.1"),
        (
            "safety.drivable_outside_episode_count",
            "count",
            "count false_to_true transitions of outside_fraction>1e-9",
        ),
        (
            "safety.drivable_signed_clearance_min_m",
            "m",
            "minimum signed full-footprint clearance to external boundary of union(D)",
        ),
        (
            "safety.drivable_penetration_max_m",
            "m",
            "maximum full-footprint penetration beyond external boundary of union(D)",
        ),
    )
    for endpoint_id, units, formula in containment:
        add(
            _spec(
                endpoint_id,
                "safety",
                "higher" if "clearance" in endpoint_id else "lower",
                formula,
                units,
                "sealed_execution",
                "reconstructable_with_frozen_transform",
                input_shape="per_tick full ego polygon and root-bound drivable polygon inventory",
                event_definition="outside_fraction>geometric_epsilon_1e-9",
                opportunity_denominator="64 ticks per retained run",
                legacy_alias="five_point_offroad_is_legacy_only_not_a_substitute",
            )
        )
    for endpoint_id, units, formula in (
        (
            "safety.wrong_way_duration_s",
            "s",
            "sum(onroad and moving and unique_direction and abs(wrapped_heading_delta)>pi/2)*0.1",
        ),
        (
            "safety.wrong_way_episode_count",
            "count",
            "false_to_true count of the same unique-direction wrong-way indicator",
        ),
    ):
        add(
            _spec(
                endpoint_id,
                "safety",
                "lower",
                formula,
                units,
                "sealed_execution",
                "reconstructable_with_frozen_transform",
                input_shape="per_tick full containment, speed, heading, ordered route/lane direction",
                applicability="only where lane/route direction is unique; ambiguity is typed missing",
                event_definition="onroad, speed>0.5m/s, unique direction, opposition>90deg",
            )
        )
    speed = (
        ("operations.speed_excess_max_mps", "max(max(0,speed-limit))", "m/s"),
        (
            "operations.speed_excess_mean_positive_mps",
            "mean(excess where excess>0), typed missing when no positive excess",
            "m/s",
        ),
        (
            "operations.speed_excess_duration_s",
            "sum(excess>tolerance)*0.1 for tolerance 0/0.05/0.1/0.2m/s",
            "s",
        ),
        (
            "operations.speed_excess_magnitude_duration_m",
            "sum(max(0,excess-tolerance))*0.1 for tolerance 0/0.05/0.1/0.2m/s",
            "m",
        ),
    )
    for endpoint_id, formula, units in speed:
        add(
            _spec(
                endpoint_id,
                "operations",
                "lower",
                formula,
                units,
                "sealed_execution",
                "reconstructable_with_frozen_transform",
                input_shape="per_tick speed and same-tick map speed limit",
                industrial_interpretation="project operational sensitivity, not legal/type approval",
            )
        )
    route = (
        ("operations.ordered_route_arc_final_m", "higher", "final stateful ordered reachable route arc s_t", "m"),
        (
            "operations.max_forward_progress_m",
            "higher",
            "max_t(s_t)-s_0 on one stateful adjacent-segment route path",
            "m",
        ),
        ("operations.net_forward_progress_m", "higher", "s_final-s_0", "m"),
        (
            "operations.completion_fraction",
            "higher",
            "clip(max_forward_progress/route_length,0,1); zero route length is typed missing",
            "fraction",
        ),
        ("operations.goal_distance_final_m", "lower", "norm(final_position-goal_pose)", "m"),
        (
            "operations.goal_reached",
            "higher",
            "native runner literal goal_tolerance_m semantics",
            "bool",
        ),
        (
            "operations.goal_passed",
            "lower",
            "native same-tick/contiguous goal_pass_window_m semantics",
            "bool",
        ),
        (
            "operations.backtracking_duration_s",
            "lower",
            "sum(max(0,s_previous-s_current)>epsilon)*0.1",
            "s",
        ),
        (
            "operations.backtracking_distance_m",
            "lower",
            "sum(max(0,s_previous-s_current))",
            "m",
        ),
        (
            "operations.distance_traveled_m",
            "descriptive_unclassified",
            "sum(norm(position[t]-position[t-1]))",
            "m",
        ),
        (
            "operations.travel_efficiency_ratio",
            "higher",
            "max_forward_progress_m/distance_traveled_m; zero denominator is typed missing",
            "ratio",
        ),
    )
    for endpoint_id, direction, formula, units in route:
        add(
            _spec(
                endpoint_id,
                "operations",
                direction,
                formula,
                units,
                "sealed_execution",
                "reconstructable_with_frozen_transform",
                input_shape="64 positions plus root-bound ordered route and spawn/goal config",
                applicability=(
                    "unique stateful path using same or adjacent forward/backward segments; "
                    "nonadjacent nearest-segment jumps forbidden"
                ),
            )
        )
    for endpoint_id, units, formula in (
        (
            "operations.false_stop_duration_s",
            "s",
            "duration speed<=future_preregistered_threshold during valid motion opportunity",
        ),
        (
            "operations.false_stop_episode_count",
            "count",
            "episodes meeting future minimum duration after excluding red/obstacle/goal waits",
        ),
    ):
        add(
            _spec(
                endpoint_id,
                "operations",
                "lower",
                formula,
                units,
                "no_credible_sealed_source",
                "evidence_missing",
                input_shape="requires authoritative per-tick motion opportunity and exclusion context",
                applicability="future nonholdout instrumentation and preregistration required",
            )
        )
    comfort_common = {
        "source": "sealed_execution",
        "evidence_class": "reconstructable_with_frozen_transform",
        "input_shape": "position_xy[64,2], ego_heading_rad[64], dt=0.1s",
        "coordinate_frame": (
            "vehicle body at acceleration sample heading: longitudinal forward, "
            "lateral left; planar only"
        ),
        "filter_name": (
            "11-point centered equal-weight FIR coefficients [1/11]*11, "
            "zero-phase offline valid convolution"
        ),
        "window": "64 positions -> 63 interval velocities -> 62 accelerations -> 52 filtered",
        "edge_handling": "valid-only; no padding, extrapolation, or endpoint replication",
    }
    for axis in ("longitudinal", "lateral"):
        add(
            _spec(
                f"comfort.body_{axis}_filtered_acceleration_summary",
                "vehicle_body_planar_kinematic_comfort_proxy",
                "lower",
                (
                    "signed mean,RMS,peak_abs,abs p50/p90/p95/p99 and duration "
                    "above 0.5/1/2/3m/s2 from filtered body acceleration"
                ),
                "m/s^2",
                **comfort_common,
            )
        )
        add(
            _spec(
                f"comfort.planar_kinematic_vdv_like_{axis}",
                "vehicle_body_planar_kinematic_comfort_proxy",
                "lower",
                "(sum(abs(a_filtered)^4)*0.1)^(1/4)",
                "m/s^1.75",
                industrial_interpretation="descriptive planar proxy, not ISO VDV",
                **comfort_common,
            )
        )
        add(
            _spec(
                f"comfort.filtered_{axis}_jerk_control_smoothness_summary",
                "vehicle_body_planar_kinematic_comfort_proxy",
                "lower",
                (
                    "diff(filtered_body_acceleration)/0.1 then RMS,peak_abs,abs p95 "
                    "and duration above 0.5/1/2/5m/s3"
                ),
                "m/s^3",
                aggregation="51 filtered-jerk samples summarized per run before clusters",
                industrial_interpretation=(
                    "control-smoothness auxiliary, not occupant comfort or ISO/SAE jerk"
                ),
                **comfort_common,
            )
        )
    add(
        _spec(
            "comfort.occupant_seat_iso_sae_conformity",
            "vehicle_body_planar_kinematic_comfort_proxy",
            "descriptive_unclassified",
            (
                "requires seat/suspension/human transfer, vertical and rotational channels, "
                "frequency weighting and qualified transducer placement"
            ),
            "not_applicable",
            "no_credible_sealed_source",
            "scientifically_inapplicable",
            input_shape="required occupant/seat channels not modeled",
            industrial_interpretation="not_assessed; no ISO 2631 or SAE J2834 conformity",
        )
    )
    for stage in (
        "pool_generation",
        "atoms",
        "context_weights",
        "selector_increment",
        "end_to_end",
    ):
        add(
            _spec(
                f"realtime.{stage}_latency_ms",
                "controlled_benchmark_realtime",
                "lower",
                "per-run empirical mean,median,p95,p99,max of perf_counter_ns stage duration / 1e6",
                "ms",
                "future_same_ego_batch8_instrumentation",
                "evidence_missing",
                input_shape="per-tick stage latency[64] from target same-ego batch8 architecture",
                industrial_interpretation=(
                    "controlled benchmark timing only; warm-up/load/scheduler evidence absent"
                ),
            )
        )
    add(
        _spec(
            "realtime.hypothetical_budget_exceedance",
            "controlled_benchmark_realtime",
            "lower",
            (
                "for D in 50/100/200/500/1000ms: count(end_to_end>D)/64 and "
                "max(max(end_to_end-D,0))"
            ),
            "rate_and_ms",
            "future_same_ego_batch8_instrumentation",
            "evidence_missing",
            input_shape="end_to_end latency[64]",
            industrial_interpretation=(
                "hypothetical project sensitivity only, including 100ms hypothetical_10Hz_budget; "
                "not a production deadline certification"
            ),
        )
    )
    return s


def evaluation_contract() -> dict[str, Any]:
    authority = json.loads(HIGH_AUTHORITY_JSON)
    if (
        hashlib.sha256(HIGH_AUTHORITY_JSON.encode("utf-8")).hexdigest()
        != HIGH_AUTHORITY_SHA256
    ):
        raise RuntimeError("industrial evaluation High authority SHA drifted")
    endpoints = _endpoint_specs()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "high_authority": authority,
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "bindings": {
            "live_base_head": BASE_HEAD,
            "fixed_dp_head": FIXED_DP_HEAD,
            "execution_root_sha256": EXECUTION_ROOT,
            "execution_review_root_sha256": EXECUTION_REVIEW_ROOT,
            "corrected_evaluation_root_sha256": CORRECTED_EVALUATION_ROOT,
            "corrected_evaluation_review_root_sha256": CORRECTED_EVALUATION_REVIEW_ROOT,
            "metric_semantics_contract_root_sha256": METRIC_SEMANTICS_CONTRACT_ROOT,
            "metric_semantics_review_root_sha256": METRIC_SEMANTICS_REVIEW_ROOT,
        },
        "endpoint_domains": list(DOMAINS),
        "evidence_classes": list(EVIDENCE_CLASSES),
        "endpoint_required_fields": list(ENDPOINT_FIELDS),
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
        "source_authorities": copy.deepcopy(SOURCE_AUTHORITIES),
        "comfort_transform": {
            "dt_s": DT_S,
            "sample_rate_hz": SAMPLE_RATE_HZ,
            "position_count": TICK_COUNT,
            "interval_velocity_count": INTERVAL_VELOCITY_COUNT,
            "raw_acceleration_count": RAW_ACCELERATION_COUNT,
            "body_heading_indices": [1, 62],
            "rotation": (
                "long=ax*cos(h)+ay*sin(h); lateral=-ax*sin(h)+ay*cos(h)"
            ),
            "filter_kind": "centered_equal_weight_boxcar_zero_phase_offline",
            "filter_coefficients": list(BOXCAR_COEFFICIENTS),
            "filter_width_samples": FILTER_WIDTH,
            "filter_window_s": 1.0,
            "valid_only": True,
            "padding": False,
            "extrapolation": False,
            "filtered_acceleration_count": FILTERED_ACCELERATION_COUNT,
            "filtered_jerk_formula": "diff(filtered_acceleration)/0.1",
            "filtered_jerk_count": FILTERED_JERK_COUNT,
            "acceleration_sensitivity_mps2": list(ACCELERATION_SENSITIVITY_MPS2),
            "jerk_sensitivity_mps3": list(JERK_SENSITIVITY_MPS3),
            "sensitivity_is_project_descriptive_not_industrial_gate": True,
        },
        "statistics": {
            "per_run_first": True,
            "future_independent_unit": (
                "preregistered scenario/corridor-intersection cluster"
            ),
            "ticks_rows_arms_seeds_as_independent_n": False,
            "cluster_aggregation": (
                "per-run then within-cluster equal-weight mean, then equal mass across clusters"
            ),
            "confidence_interval": "Student-t two-sided CI95 across cluster values",
            "better_tie_worse": (
                "per paired unit with endpoint direction; exact zero delta is tie"
            ),
            "weighted_total": False,
            "hard_safety_topology": (
                "future prospectively registered collision, certified-red, containment, "
                "and dynamic-critical endpoints; missing is fail-closed"
            ),
            "numeric_margin": (
                "numeric_margin_not_authorized_until_future_preregistration"
            ),
            "multiplicity": (
                "future prospective endpoint-family procedure required; no current claim"
            ),
            "full_denominator_missing_retention": True,
            "complete_case_claim_allowed": False,
        },
        "legacy": {
            "role": "immutable_legacy_exploratory_diagnostic_only",
            "safetycost_formula": LEGACY_SAFETYCOST_FORMULA,
            "fields": dict(LEGACY_FIELDS),
            "values_or_roots_mutated": False,
            "allowed_in_primary": False,
            "allowed_in_pass_or_claim": False,
            "allowed_in_training_support_or_adaptation": False,
        },
        "evaluation_and_selector_training_decoupled": True,
        "claim_authorized": False,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_write_count": 0,
        "references": [
            {
                "name": "ISO 2631-1:1997",
                "url": "https://www.iso.org/standard/7612.html",
                "accessed": "2026-07-26",
                "use": "scope rationale only; no copied normative thresholds or conformity",
            },
            {
                "name": "SAE J2834_202504",
                "url": (
                    "https://saemobilus.sae.org/standards/"
                    "j2834_202504-ride-index-structure-development-methodology"
                ),
                "accessed": "2026-07-26",
                "use": "scope rationale only; no copied normative thresholds or conformity",
            },
            {
                "name": "ISO 34502:2022",
                "url": "https://www.iso.org/standard/78951.html",
                "accessed": "2026-07-26",
                "use": "scenario-based safety evaluation scope rationale only",
            },
            {
                "name": "FHWA SSAM report FHWA-HRT-08-051",
                "url": "https://www.fhwa.dot.gov/publications/research/safety/08051/",
                "accessed": "2026-07-26",
                "use": "TTC/PET terminology rationale, not certification",
            },
        ],
    }


def validate_evaluation_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    actual = copy.deepcopy(dict(value))
    expected = evaluation_contract()
    if actual != expected:
        raise ValueError("industrial evaluation contract literal topology drifted")
    endpoints = actual["endpoints"]
    ids = [row["endpoint_id"] for row in endpoints]
    if len(ids) != len(set(ids)) or len(ids) != actual["endpoint_count"]:
        raise ValueError("industrial evaluation endpoint IDs drifted")
    for row in endpoints:
        if set(row) != set(ENDPOINT_FIELDS):
            raise ValueError(f"industrial evaluation endpoint field drifted: {row.get('endpoint_id')}")
        if row["domain"] not in DOMAINS or row["evidence_class"] not in EVIDENCE_CLASSES:
            raise ValueError("industrial evaluation endpoint classification drifted")
        if row["source"] not in SOURCE_AUTHORITIES:
            raise ValueError("industrial evaluation source authority drifted")
        if row["status_enum"] not in STATUS_ENUM:
            raise ValueError("industrial evaluation status enum drifted")
    if actual["statistics"]["weighted_total"] is not False:
        raise ValueError("industrial evaluation weighted total is forbidden")
    if actual["legacy"]["role"] != "immutable_legacy_exploratory_diagnostic_only":
        raise ValueError("legacy SafetyCost role drifted")
    forbidden_true = (
        actual["claim_authorized"],
        actual["model_pool_selector_call_count"] != 0,
        actual["outcome_values_read"],
        actual["old_artifact_or_cas_write_count"] != 0,
        not actual["evaluation_and_selector_training_decoupled"],
    )
    if any(forbidden_true):
        raise ValueError("industrial evaluation zero-run/claim boundary drifted")
    return actual


def capability_matrix(contract: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_evaluation_contract(contract)
    rows = []
    for endpoint in validated["endpoints"]:
        source = validated["source_authorities"][endpoint["source"]]
        rows.append(
            {
                "endpoint_id": endpoint["endpoint_id"],
                "evidence_class": endpoint["evidence_class"],
                "source_artifact_root_sha256": source["artifact_root_sha256"],
                "source_artifact_review_root_sha256": source[
                    "artifact_review_root_sha256"
                ],
                "source_file": source["file"],
                "source_schema_field": source["schema_fields"],
                "source_sha256": source["source_sha256"],
                "reason": _capability_reason(endpoint),
                "future_same_ego_batch8_use": (
                    "requires_future_nonholdout_instrumentation"
                    if endpoint["source"] == "future_same_ego_batch8_instrumentation"
                    else "available_if_future_preregistered_transform_and_applicability_pass"
                    if endpoint["evidence_class"]
                    in {"directly_reconstructable", "reconstructable_with_frozen_transform"}
                    else "not_available"
                ),
                "permanently_inapplicable_to_current_simulator": (
                    endpoint["evidence_class"] == "scientifically_inapplicable"
                ),
                "outcome_values_read": False,
            }
        )
    result = {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "status": "sealed_structure_only_evidence_capability_matrix",
        "contract_sha256": canonical_sha256(validated),
        "endpoint_count": len(rows),
        "rows": rows,
        "evidence_class_counts": {
            name: sum(row["evidence_class"] == name for row in rows)
            for name in EVIDENCE_CLASSES
        },
        "source_authorities": copy.deepcopy(SOURCE_AUTHORITIES),
        "structure_only": True,
        "outcome_values_read": False,
        "model_pool_selector_call_count": 0,
        "old_artifact_or_cas_write_count": 0,
    }
    validate_capability_matrix(result, validated)
    return result


def _capability_reason(endpoint: Mapping[str, Any]) -> str:
    evidence_class = endpoint["evidence_class"]
    if evidence_class == "directly_reconstructable":
        return "sealed field has direct endpoint semantics"
    if evidence_class == "reconstructable_with_frozen_transform":
        return (
            "sealed structural inputs exist; endpoint requires the exact frozen transform "
            "and remains typed missing when applicability is ambiguous"
        )
    if evidence_class == "evidence_missing":
        return (
            "required authoritative semantic input or target-architecture instrumentation "
            "is absent; legacy proxy substitution is forbidden"
        )
    return (
        "current simulator lacks occupant/seat/vertical/transfer evidence, so industrial "
        "comfort conformity is scientifically inapplicable"
    )


def validate_capability_matrix(
    matrix: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    actual = copy.deepcopy(dict(matrix))
    validated = validate_evaluation_contract(contract)
    if set(actual) != {
        "schema_version",
        "status",
        "contract_sha256",
        "endpoint_count",
        "rows",
        "evidence_class_counts",
        "source_authorities",
        "structure_only",
        "outcome_values_read",
        "model_pool_selector_call_count",
        "old_artifact_or_cas_write_count",
    }:
        raise ValueError("industrial capability matrix fields drifted")
    if (
        actual["schema_version"] != CAPABILITY_SCHEMA_VERSION
        or actual["status"] != "sealed_structure_only_evidence_capability_matrix"
        or actual["contract_sha256"] != canonical_sha256(validated)
        or actual["endpoint_count"] != len(validated["endpoints"])
        or actual["structure_only"] is not True
        or actual["outcome_values_read"] is not False
        or actual["model_pool_selector_call_count"] != 0
        or actual["old_artifact_or_cas_write_count"] != 0
    ):
        raise ValueError("industrial capability matrix authority drifted")
    expected_rows = {
        endpoint["endpoint_id"]: (
            endpoint["evidence_class"],
            endpoint["source"],
            endpoint["source_sha256"],
        )
        for endpoint in validated["endpoints"]
    }
    seen: set[str] = set()
    for row in actual["rows"]:
        if set(row) != {
            "endpoint_id",
            "evidence_class",
            "source_artifact_root_sha256",
            "source_artifact_review_root_sha256",
            "source_file",
            "source_schema_field",
            "source_sha256",
            "reason",
            "future_same_ego_batch8_use",
            "permanently_inapplicable_to_current_simulator",
            "outcome_values_read",
        }:
            raise ValueError("industrial capability row schema drifted")
        endpoint_id = row["endpoint_id"]
        if endpoint_id in seen or endpoint_id not in expected_rows:
            raise ValueError("industrial capability row ID drifted")
        seen.add(endpoint_id)
        evidence_class, source_name, source_sha = expected_rows[endpoint_id]
        authority = SOURCE_AUTHORITIES[source_name]
        if (
            row["evidence_class"] != evidence_class
            or row["source_sha256"] != source_sha
            or row["source_artifact_root_sha256"]
            != authority["artifact_root_sha256"]
            or row["source_artifact_review_root_sha256"]
            != authority["artifact_review_root_sha256"]
            or row["source_file"] != authority["file"]
            or row["source_schema_field"] != authority["schema_fields"]
            or row["outcome_values_read"] is not False
        ):
            raise ValueError("industrial capability source binding drifted")
    if seen != set(expected_rows):
        raise ValueError("industrial capability endpoint omission")
    counts = {
        name: sum(row["evidence_class"] == name for row in actual["rows"])
        for name in EVIDENCE_CLASSES
    }
    if actual["evidence_class_counts"] != counts:
        raise ValueError("industrial capability class counts drifted")
    return actual


def vehicle_body_planar_kinematics(
    position_xy: Sequence[Sequence[float]],
    heading_rad: Sequence[float],
    *,
    dt_s: float = DT_S,
) -> dict[str, np.ndarray]:
    position = np.asarray(position_xy, dtype=np.float64)
    heading = np.asarray(heading_rad, dtype=np.float64)
    if (
        position.shape != (TICK_COUNT, 2)
        or heading.shape != (TICK_COUNT,)
        or not np.isfinite(position).all()
        or not np.isfinite(heading).all()
        or not math.isclose(dt_s, DT_S, rel_tol=0.0, abs_tol=0.0)
    ):
        raise ValueError("industrial comfort transform input drifted")
    interval_velocity = np.diff(position, axis=0) / dt_s
    world_acceleration = np.diff(interval_velocity, axis=0) / dt_s
    h = heading[1:-1]
    c = np.cos(h)
    s = np.sin(h)
    longitudinal = world_acceleration[:, 0] * c + world_acceleration[:, 1] * s
    lateral = -world_acceleration[:, 0] * s + world_acceleration[:, 1] * c
    kernel = np.asarray(BOXCAR_COEFFICIENTS, dtype=np.float64)
    filtered_longitudinal = np.convolve(longitudinal, kernel, mode="valid")
    filtered_lateral = np.convolve(lateral, kernel, mode="valid")
    jerk_longitudinal = np.diff(filtered_longitudinal) / dt_s
    jerk_lateral = np.diff(filtered_lateral) / dt_s
    result = {
        "interval_velocity": interval_velocity,
        "world_acceleration": world_acceleration,
        "body_longitudinal_acceleration": longitudinal,
        "body_lateral_acceleration": lateral,
        "filtered_longitudinal_acceleration": filtered_longitudinal,
        "filtered_lateral_acceleration": filtered_lateral,
        "filtered_longitudinal_jerk": jerk_longitudinal,
        "filtered_lateral_jerk": jerk_lateral,
    }
    expected_shapes = {
        "interval_velocity": (63, 2),
        "world_acceleration": (62, 2),
        "body_longitudinal_acceleration": (62,),
        "body_lateral_acceleration": (62,),
        "filtered_longitudinal_acceleration": (52,),
        "filtered_lateral_acceleration": (52,),
        "filtered_longitudinal_jerk": (51,),
        "filtered_lateral_jerk": (51,),
    }
    if any(result[name].shape != shape for name, shape in expected_shapes.items()):
        raise RuntimeError("industrial comfort transform sample accounting drifted")
    return result


def planar_kinematic_vdv_like(values: Sequence[float], *, dt_s: float = DT_S) -> float:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError("planar kinematic VDV-like input drifted")
    if not math.isclose(dt_s, DT_S, rel_tol=0.0, abs_tol=0.0):
        raise ValueError("planar kinematic VDV-like dt drifted")
    return float((np.sum(np.abs(array) ** 4) * dt_s) ** 0.25)
