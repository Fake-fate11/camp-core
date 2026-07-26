from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_contract as v1,
)
from camp_core.integrations.diffusion_planner_artifact_seal import (
    verify_complete_seal,
)


SCHEMA_VERSION = "camp_dp_v25_industrial_oriented_evaluation_contract_v2"
CAPABILITY_SCHEMA_VERSION = (
    "camp_dp_v25_industrial_oriented_evaluation_capability_matrix_v2"
)
STATUS = "frozen_outcome_independent_industrial_oriented_evaluation_contract_v2"
HIGH_AUTHORITY_SHA256 = v1.HIGH_AUTHORITY_SHA256

SCALAR_LEAF_FIELDS = (
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
)

ROLE_VALUES = (
    "hard_safety",
    "guardrail",
    "descriptive_only",
    "evidence_missing_not_testable",
)

FAMILYWISE_METHOD = "holm_bonferroni_step_down_within_exact_family"
FAMILYWISE_ALPHA = 0.05
CLAIM_MARGIN_STATE = "numeric_margin_not_authorized_until_future_preregistration"

GRID_TOKENS = {
    "clearance_m": (("0", 0.0), ("0p5", 0.5), ("1", 1.0), ("2", 2.0)),
    "ttc_s": (
        ("0p5", 0.5),
        ("1", 1.0),
        ("2", 2.0),
        ("3", 3.0),
        ("5", 5.0),
    ),
    "closing_mps": (
        ("0p5", 0.5),
        ("1", 1.0),
        ("2", 2.0),
        ("5", 5.0),
    ),
    "drac_mps2": (
        ("0p5", 0.5),
        ("1", 1.0),
        ("2", 2.0),
        ("3", 3.0),
        ("5", 5.0),
    ),
    "speed_tolerance_mps": (
        ("0", 0.0),
        ("0p05", 0.05),
        ("0p1", 0.1),
        ("0p2", 0.2),
    ),
    "acceleration_mps2": (
        ("0p5", 0.5),
        ("1", 1.0),
        ("2", 2.0),
        ("3", 3.0),
    ),
    "jerk_mps3": (
        ("0p5", 0.5),
        ("1", 1.0),
        ("2", 2.0),
        ("5", 5.0),
    ),
    "latency_ms": (
        ("50", 50.0),
        ("100", 100.0),
        ("200", 200.0),
        ("500", 500.0),
        ("1000", 1000.0),
    ),
}

SEALED_SOURCES = {
    "execution": {
        "root": v1.EXECUTION_ROOT,
        "review_root": v1.EXECUTION_REVIEW_ROOT,
        "required_inventory": {
            "artifact_report.json": (
                "63483ab8e368e6281f1da63a913a6294e30ee2bd40af5d50a41e08362a95f5db"
            ),
            "report.json": (
                "d7b8214f29b7cb7743876d2c87e2df0dc1e0a35ce6d0242186fb2ca1903bded2"
            ),
            "HEADS": (
                "9623e17b06e35b065653c7b7d47f66c113b4a65a69be4adb7fd4309873fa4f81"
            ),
        },
    },
    "execution_review": {
        "root": v1.EXECUTION_REVIEW_ROOT,
        "review_root": None,
        "required_inventory": {
            "report.json": (
                "2f1e9f0288ac442110ae4f0ecf7c3a10bbdc5f29ebef008465427ec1a288e40a"
            ),
            "HEADS": (
                "9623e17b06e35b065653c7b7d47f66c113b4a65a69be4adb7fd4309873fa4f81"
            ),
        },
    },
    "evaluation_v2_contract": {
        "root": v1.EVALUATION_V2_CONTRACT_ROOT,
        "review_root": v1.EVALUATION_V2_REVIEW_ROOT,
        "required_inventory": {
            "report.json": (
                "e193c5ac2014777ff8d78003ae798bf61151e53ea86b85f1abf6635f5676f8a2"
            ),
            "HEADS": (
                "005c185d95c31df65b0bc7fc87e86add13b78026926780153958680bed3731ef"
            ),
        },
    },
    "evaluation_v2_contract_review": {
        "root": v1.EVALUATION_V2_REVIEW_ROOT,
        "review_root": None,
        "required_inventory": {
            "report.json": (
                "2cd808e5f87e92c21219a887eab3eec9e5d13383599ffea8f032d76d901c6724"
            ),
            "HEADS": (
                "80e6cedb9d321d67c4a9a6f44b682ab93648a55cbbe4e6a995db5a015c6ea360"
            ),
        },
    },
    "evaluation_v2_materialization": {
        "root": v1.EVALUATION_V2_MATERIALIZATION_ROOT,
        "review_root": v1.EVALUATION_V2_MATERIALIZATION_REVIEW_ROOT,
        "required_inventory": {
            "report.json": (
                "26102e5908f4d4f9411dd76e4d89f92d0ab6b1b1da24eff46eb0393094251cbb"
            ),
            "HEADS": (
                "95729027a5123e594d2d8c5df68c3375654852050284bf5817c2deff4091478d"
            ),
        },
    },
    "evaluation_v2_materialization_review": {
        "root": v1.EVALUATION_V2_MATERIALIZATION_REVIEW_ROOT,
        "review_root": None,
        "required_inventory": {
            "report.json": (
                "9a8534888416f88ed13343503461308b38c1a89e7df2679e23a12f537dfd5f4b"
            ),
            "HEADS": (
                "34ed389b296dbeabdf7e98d9df93ea77645fbdf6fac7f9fc84826ed52a7158c1"
            ),
        },
    },
    "metric_contract": {
        "root": v1.METRIC_SEMANTICS_CONTRACT_ROOT,
        "review_root": v1.METRIC_SEMANTICS_REVIEW_ROOT,
        "required_inventory": {
            "report.json": (
                "bcb45030be87dd8e21e3d733cc93f8d5173275689743c302107e1fe31d075565"
            ),
            "HEADS": (
                "78d07b6e7159e5a17df9ee16599024bad912282c4079626b700470ef7f835323"
            ),
        },
    },
    "metric_contract_review": {
        "root": v1.METRIC_SEMANTICS_REVIEW_ROOT,
        "review_root": None,
        "required_inventory": {
            "report.json": (
                "56a270778b7f480464456083873f5732c0572bd49281cf107e1966dd9b6e4f03"
            ),
        },
    },
}

SOURCE_BINDINGS = {
    "execution_kinematics_geometry": {
        "evidence_class": "reconstructable_with_frozen_transform",
        "artifacts": (
            "execution",
            "execution_review",
            "evaluation_v2_contract",
            "evaluation_v2_contract_review",
            "evaluation_v2_materialization",
            "evaluation_v2_materialization_review",
        ),
        "json_pointers": (
            "/source_capability_audit/actor_fields",
            "/source_capability_audit/spawn_fields",
            "/contract/endpoint_catalog/collision",
            "/contract/endpoint_catalog/dynamic_proximity",
        ),
        "shape": "1500 retained runs; 64 ticks; authoritative ego and actor geometry/kinematics",
        "units": "m,rad,s,m/s,m/s^2",
        "prerequisites": "sealed homogeneous run schema and complete full denominator",
        "transform_inputs": "ego/actor pose,length,width,velocity or frozen scalar-speed-heading reconstruction,dt",
        "reason": "sealed source capability contract plus sealed materialization and execution inventories",
    },
    "execution_route_map": {
        "evidence_class": "reconstructable_with_frozen_transform",
        "artifacts": (
            "execution",
            "execution_review",
            "evaluation_v2_contract",
            "evaluation_v2_contract_review",
            "evaluation_v2_materialization",
            "evaluation_v2_materialization_review",
        ),
        "json_pointers": (
            "/source_capability_audit/all_map_assets_present_and_sha_bound",
            "/source_capability_audit/all_route_assets_present_and_sha_bound",
            "/source_capability_audit/full_polygon_capability",
            "/source_capability_audit/ordered_route_capability",
            "/contract/endpoint_catalog/road_containment",
            "/contract/endpoint_catalog/route",
            "/contract/endpoint_catalog/goal",
        ),
        "shape": "1500 retained runs; root-bound map, route, goal, and 64 ego poses",
        "units": "m,rad,fraction,bool,count,s",
        "prerequisites": "unique feasible ordered-route state where required; ambiguity retained missing",
        "transform_inputs": "vehicle footprint, drivable polygons, ordered route, goal config, position,heading,speed",
        "reason": "sealed source capability contract proves exact map/route authorities without reading values",
    },
    "execution_red_speed": {
        "evidence_class": "reconstructable_with_frozen_transform",
        "artifacts": (
            "execution",
            "execution_review",
            "evaluation_v2_contract",
            "evaluation_v2_contract_review",
            "evaluation_v2_materialization",
            "evaluation_v2_materialization_review",
        ),
        "json_pointers": (
            "/contract/endpoint_catalog/certified_red_crossing",
            "/contract/endpoint_catalog/speed",
            "/contract/grids/speed_tolerance_mps",
        ),
        "shape": "1500 retained runs; 64 same-tick phase/stopline/speed-limit observations",
        "units": "bool,count,s,m/s,m",
        "prerequisites": "certified same-tick phase and route-specific stopline for red; map limit for speed",
        "transform_inputs": "phase,stopline,front-edge poses,speed,map speed limit,dt",
        "reason": "sealed source capability contract and materialization inventories",
    },
    "execution_planar_motion": {
        "evidence_class": "reconstructable_with_frozen_transform",
        "artifacts": (
            "execution",
            "execution_review",
            "evaluation_v2_contract",
            "evaluation_v2_contract_review",
            "metric_contract",
            "metric_contract_review",
            "evaluation_v2_materialization",
            "evaluation_v2_materialization_review",
        ),
        "json_pointers": (
            "/contract/geometry/dt_s",
            "/contract/geometry/boxcar_kernel",
            "/contract/endpoint_catalog/vehicle_body_planar_kinematic_proxy",
            "/contract/body_proxy/source_fields",
            "/contract/body_proxy/filter",
        ),
        "shape": "1500 retained runs; 64 position_xy and heading samples",
        "units": "m,s,rad,m/s^2,m/s^3,m/s^1.75",
        "prerequisites": "finite 64-sample planar pose series",
        "transform_inputs": "position_xy,heading_rad,dt=0.1,11-point centered equal-weight valid-only boxcar",
        "reason": "sealed source capability and metric-transform contracts",
    },
    "missing_contact_dynamics": {
        "evidence_class": "evidence_missing",
        "artifacts": (),
        "json_pointers": (),
        "shape": "unavailable contact dynamics",
        "units": "m/s or severity_unit",
        "prerequisites": "contact impulse/delta-v/validated severity sensor",
        "transform_inputs": "none available",
        "reason": "sealed sources contain geometry/kinematics but no contact impulse or delta-v",
    },
    "missing_unique_leader": {
        "evidence_class": "evidence_missing",
        "artifacts": (),
        "json_pointers": (),
        "shape": "unavailable unique leader/following-lane semantics",
        "units": "s",
        "prerequisites": "unique same-lane leader authority",
        "transform_inputs": "none available",
        "reason": "leader/lane relationship is not root-bound",
    },
    "missing_conflict_zone": {
        "evidence_class": "evidence_missing",
        "artifacts": (),
        "json_pointers": (),
        "shape": "unavailable conflict-zone passage authority",
        "units": "s",
        "prerequisites": "frozen conflict zone and both passage times",
        "transform_inputs": "none available",
        "reason": "conflict-zone geometry and passage identities are absent",
    },
    "missing_false_stop_context": {
        "evidence_class": "evidence_missing",
        "artifacts": (),
        "json_pointers": (),
        "shape": "unavailable exclusive stop-opportunity context",
        "units": "s,count",
        "prerequisites": "red/obstacle/goal exclusion contexts and frozen opportunity",
        "transform_inputs": "none available",
        "reason": "sealed source cannot distinguish justified from false stopping",
    },
    "missing_target_runtime": {
        "evidence_class": "evidence_missing",
        "artifacts": (),
        "json_pointers": (),
        "shape": "future same-ego batch8 stage timings",
        "units": "ms,rate",
        "prerequisites": "target-architecture controlled stage instrumentation",
        "transform_inputs": "none available",
        "reason": "legacy timing is not the target same-ego batch8 architecture",
    },
    "inapplicable_occupant_conformity": {
        "evidence_class": "scientifically_inapplicable",
        "artifacts": (),
        "json_pointers": (),
        "shape": "seat/human/vertical/rotational response unavailable",
        "units": "not_applicable",
        "prerequisites": "occupant, seat, suspension, multiaxis frequency-weighted measurements",
        "transform_inputs": "none available",
        "reason": "planar vehicle-body kinematics cannot establish ISO/SAE occupant conformity",
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


def _parents() -> list[dict[str, Any]]:
    parents = copy.deepcopy(v1.evaluation_contract()["endpoints"])
    for row in parents:
        if row["endpoint_id"] == "safety.collision_impact_relative_speed_proxy_mps":
            row["endpoint_id"] = (
                "safety.collision_onset_relative_closing_speed_kinematic_proxy_mps"
            )
            row["formula"] = (
                "at first full-OBB false_to_true intersection, use the last "
                "noncollision interval [t-1,t]; linearly interpolate the signed "
                "centroid closing speed to the first contact fraction; if no "
                "finite preceding noncollision interval, retain typed missing"
            )
            row["input_shape"] = (
                "per-tick ego+actor full polygons and kinematic state around collision onset"
            )
            row["industrial_interpretation"] = (
                "severity-related kinematic proxy only; never delta-v or contact severity"
            )
            row["source"] = "sealed_execution"
            row["source_sha256"] = v1.EXECUTION_ROOT
            row["evidence_class"] = "reconstructable_with_frozen_transform"
            row["status_enum"] = "defined_not_materialized"
    return parents


def _source_binding(parent_id: str) -> str:
    if parent_id in {
        "safety.collision_delta_v_mps",
        "safety.collision_contact_severity",
    }:
        return "missing_contact_dynamics"
    if parent_id == "safety.time_headway_s":
        return "missing_unique_leader"
    if parent_id == "safety.post_encroachment_time_s":
        return "missing_conflict_zone"
    if parent_id.startswith("operations.false_stop_"):
        return "missing_false_stop_context"
    if parent_id == "comfort.occupant_seat_iso_sae_conformity":
        return "inapplicable_occupant_conformity"
    if parent_id.startswith("realtime."):
        return "missing_target_runtime"
    if parent_id.startswith("comfort."):
        return "execution_planar_motion"
    if parent_id.startswith("operations.speed_") or parent_id.startswith(
        "safety.certified_red_"
    ):
        return "execution_red_speed"
    if parent_id.startswith("operations.") or parent_id.startswith(
        "safety.drivable_"
    ) or parent_id.startswith("safety.wrong_way_"):
        return "execution_route_map"
    return "execution_kinematics_geometry"


def _role(parent_id: str, evidence_class: str, direction: str) -> str:
    if evidence_class in {"evidence_missing", "scientifically_inapplicable"}:
        return "evidence_missing_not_testable"
    if parent_id.startswith(
        (
            "safety.collision_",
            "safety.certified_red_crossing",
            "safety.drivable_",
            "safety.wrong_way_",
        )
    ):
        return "hard_safety"
    if direction == "descriptive_unclassified" or parent_id.endswith(
        ("opportunity_count", "interval_count", "distance_traveled_m")
    ):
        return "descriptive_only"
    return "guardrail"


def _family(parent_id: str, role: str) -> str:
    if role == "evidence_missing_not_testable":
        return "not_testable"
    if parent_id.startswith("safety.collision_"):
        return "hard_safety_collision"
    if parent_id.startswith("safety.certified_red_"):
        return "hard_safety_red"
    if parent_id.startswith(("safety.drivable_", "safety.wrong_way_")):
        return "hard_safety_containment_direction"
    if parent_id.startswith("safety."):
        return "safety_dynamic_exposure_guardrails"
    if parent_id.startswith("operations."):
        return "operations_guardrails"
    if parent_id.startswith("comfort."):
        return "planar_kinematic_proxy_guardrails"
    if parent_id.startswith("realtime."):
        return "controlled_benchmark_realtime_guardrails"
    raise ValueError(f"unclassified parent: {parent_id}")


def _leaf(
    parent: Mapping[str, Any],
    leaf_id: str,
    units: str,
    direction: str,
    formula: str,
    denominator: str | None = None,
) -> dict[str, Any]:
    binding_id = _source_binding(str(parent["endpoint_id"]))
    evidence_class = SOURCE_BINDINGS[binding_id]["evidence_class"]
    role = _role(str(parent["endpoint_id"]), str(evidence_class), direction)
    return {
        "leaf_id": leaf_id,
        "parent_id": parent["endpoint_id"],
        "domain": parent["domain"],
        "units": units,
        "direction": direction,
        "formula": formula,
        "input_shape": parent["input_shape"],
        "applicability": parent["applicability"],
        "opportunity_denominator": (
            denominator if denominator is not None else parent["opportunity_denominator"]
        ),
        "missing_policy": parent["missing_policy"],
        "guardrail_role": role,
        "multiplicity_family": _family(str(parent["endpoint_id"]), role),
        "confidence_interval": (
            "none_not_testable"
            if role == "evidence_missing_not_testable"
            else "two_sided_equal_cluster_weight_student_t_ci95"
            if direction == "descriptive_unclassified"
            else "one_sided_equal_cluster_weight_student_t_ci95_in_direction"
        ),
        "familywise_method": (
            "none_not_testable"
            if role == "evidence_missing_not_testable"
            else FAMILYWISE_METHOD
        ),
        "familywise_alpha": (
            None if role == "evidence_missing_not_testable" else FAMILYWISE_ALPHA
        ),
        "claim_gate_state": (
            "not_testable_evidence_missing"
            if role == "evidence_missing_not_testable"
            else "descriptive_only_not_claim_gate"
            if role == "descriptive_only"
            else CLAIM_MARGIN_STATE
        ),
        "btw_applicability": (
            "not_applicable"
            if role == "evidence_missing_not_testable"
            or direction == "descriptive_unclassified"
            else "future_paired_500_unit_better_tie_worse_exact_zero_tie"
        ),
        "evidence_class": evidence_class,
        "source_binding_id": binding_id,
    }


def _scalar_leaves(parents: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    grouped = {
        "safety.critical_exposure_duration_s",
        "safety.critical_exposure_episode_count",
        "operations.speed_excess_duration_s",
        "operations.speed_excess_magnitude_duration_m",
        "comfort.body_longitudinal_filtered_acceleration_summary",
        "comfort.body_lateral_filtered_acceleration_summary",
        "comfort.filtered_longitudinal_jerk_control_smoothness_summary",
        "comfort.filtered_lateral_jerk_control_smoothness_summary",
        "realtime.pool_generation_latency_ms",
        "realtime.atoms_latency_ms",
        "realtime.context_weights_latency_ms",
        "realtime.selector_increment_latency_ms",
        "realtime.end_to_end_latency_ms",
        "realtime.hypothetical_budget_exceedance",
    }
    for parent in parents:
        parent_id = str(parent["endpoint_id"])
        if parent_id not in grouped:
            out.append(
                _leaf(
                    parent,
                    parent_id,
                    str(parent["units"]),
                    str(parent["direction"]),
                    str(parent["formula"]),
                )
            )
            continue
        if parent_id.startswith("safety.critical_exposure_"):
            suffix = (
                "duration_s" if parent_id.endswith("duration_s") else "episode_count"
            )
            units = "s" if suffix == "duration_s" else "count"
            for family, comparator, unit_token in (
                ("clearance_m", "<=", "m"),
                ("ttc_s", "<=", "s"),
                ("closing_mps", ">=", "mps"),
                ("drac_mps2", ">=", "mps2"),
            ):
                for token, value in GRID_TOKENS[family]:
                    leaf_id = f"safety.{family}_{comparator.replace('=', 'e').replace('<', 'l').replace('>', 'g')}_{token}{unit_token}_{suffix}"
                    out.append(
                        _leaf(
                            parent,
                            leaf_id,
                            units,
                            "lower",
                            (
                                f"{suffix}(per_tick_{family}{comparator}{value}); "
                                "duration uses indicator_count*0.1 and episode uses false_to_true"
                            ),
                        )
                    )
            continue
        if parent_id.startswith("operations.speed_excess_"):
            is_duration = parent_id.endswith("duration_s")
            for token, value in GRID_TOKENS["speed_tolerance_mps"]:
                leaf_id = (
                    f"operations.speed_excess_gt_{token}mps_duration_s"
                    if is_duration
                    else f"operations.speed_excess_magnitude_above_{token}mps_duration_m"
                )
                formula = (
                    f"sum(I(max(0,speed-limit)>{value}))*0.1"
                    if is_duration
                    else f"sum(max(0,max(0,speed-limit)-{value}))*0.1"
                )
                out.append(
                    _leaf(
                        parent,
                        leaf_id,
                        "s" if is_duration else "m",
                        "lower",
                        formula,
                    )
                )
            continue
        if "acceleration_summary" in parent_id:
            axis = "longitudinal" if "longitudinal" in parent_id else "lateral"
            for stat, units, direction in (
                ("signed_mean", "m/s^2", "descriptive_unclassified"),
                ("rms", "m/s^2", "lower"),
                ("min", "m/s^2", "descriptive_unclassified"),
                ("max", "m/s^2", "descriptive_unclassified"),
                ("peak_abs", "m/s^2", "lower"),
                ("abs_p50", "m/s^2", "lower"),
                ("abs_p90", "m/s^2", "lower"),
                ("abs_p95", "m/s^2", "lower"),
                ("abs_p99", "m/s^2", "lower"),
            ):
                out.append(
                    _leaf(
                        parent,
                        f"comfort.body_{axis}_filtered_acceleration_{stat}",
                        units,
                        direction,
                        f"{stat} over 52 valid-only filtered body-{axis} acceleration samples",
                        "52 filtered samples per retained run",
                    )
                )
            for token, value in GRID_TOKENS["acceleration_mps2"]:
                out.append(
                    _leaf(
                        parent,
                        f"comfort.body_{axis}_filtered_acceleration_abs_gt_{token}mps2_duration_s",
                        "s",
                        "lower",
                        f"sum(I(abs(a_{axis}_filtered)>{value}))*0.1",
                        "52 filtered samples per retained run",
                    )
                )
            continue
        if "jerk_control_smoothness_summary" in parent_id:
            axis = "longitudinal" if "longitudinal" in parent_id else "lateral"
            for stat in ("rms", "peak_abs", "abs_p95"):
                out.append(
                    _leaf(
                        parent,
                        f"comfort.filtered_{axis}_jerk_control_smoothness_{stat}",
                        "m/s^3",
                        "lower",
                        f"{stat} over 51 diff(filtered body-{axis} acceleration)/0.1 samples",
                        "51 filtered-jerk samples per retained run",
                    )
                )
            for token, value in GRID_TOKENS["jerk_mps3"]:
                out.append(
                    _leaf(
                        parent,
                        f"comfort.filtered_{axis}_jerk_abs_gt_{token}mps3_duration_s",
                        "s",
                        "lower",
                        f"sum(I(abs(jerk_{axis}_filtered)>{value}))*0.1",
                        "51 filtered-jerk samples per retained run",
                    )
                )
            continue
        if parent_id.endswith("_latency_ms"):
            stage = parent_id.removeprefix("realtime.").removesuffix("_latency_ms")
            for stat in ("mean", "median", "p95", "p99", "max"):
                out.append(
                    _leaf(
                        parent,
                        f"realtime.{stage}_latency_{stat}_ms",
                        "ms",
                        "lower",
                        f"{stat} of empirical per-run {stage} stage timing",
                        "64 timed ticks per retained future target-architecture run",
                    )
                )
            continue
        if parent_id == "realtime.hypothetical_budget_exceedance":
            for token, value in GRID_TOKENS["latency_ms"]:
                out.append(
                    _leaf(
                        parent,
                        f"realtime.end_to_end_exceedance_rate_{token}ms",
                        "rate",
                        "lower",
                        f"count(end_to_end_latency_ms>{value})/64",
                        "64 timed ticks per retained future target-architecture run",
                    )
                )
                out.append(
                    _leaf(
                        parent,
                        f"realtime.end_to_end_max_overrun_{token}ms_ms",
                        "ms",
                        "lower",
                        f"max(0,max(end_to_end_latency_ms)-{value})",
                        "64 timed ticks per retained future target-architecture run",
                    )
                )
            continue
        raise AssertionError(parent_id)
    return out


def decision_topology(leaves: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    families: dict[str, list[str]] = {}
    for row in leaves:
        families.setdefault(str(row["multiplicity_family"]), []).append(
            str(row["leaf_id"])
        )
    return {
        "statistical_unit": (
            "future preregistered scenario/corridor-intersection cluster after per-run aggregation"
        ),
        "ticks_rows_arms_seeds_are_independent_n": False,
        "cluster_weighting": "equal_cluster_weight",
        "directed_ci": "one_sided_equal_cluster_weight_student_t_ci95_in_direction",
        "descriptive_ci": "two_sided_equal_cluster_weight_student_t_ci95",
        "familywise_method": FAMILYWISE_METHOD,
        "familywise_alpha": FAMILYWISE_ALPHA,
        "families": {key: sorted(value) for key, value in sorted(families.items())},
        "hard_safety_combination": (
            "intersection_union_all_preregistered_testable_hard_safety_leaves_must_pass"
        ),
        "guardrail_combination": (
            "intersection_union_all_preregistered_testable_guardrail_leaves_must_pass"
        ),
        "hierarchy": (
            "evidence_integrity_then_hard_safety_IUT_then_guardrail_IUT; "
            "descriptive leaves never compensate"
        ),
        "missing_policy": (
            "any required hard-safety or guardrail missing/failure blocks that future "
            "claim; no complete-case substitution"
        ),
        "numeric_margin_state": CLAIM_MARGIN_STATE,
        "current_claim_gate_authorized": False,
        "weighted_compensation_allowed": False,
        "btw_tie_rule": "exact_zero_paired_delta_only",
    }


def evaluation_contract_v2() -> dict[str, Any]:
    parents = _parents()
    leaves = _scalar_leaves(parents)
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "supersedes_schema_version": v1.SCHEMA_VERSION,
        "superseded_v1_role": "immutable_superseded_pre_correction_diagnostic",
        "high_authority": json.loads(v1.HIGH_AUTHORITY_JSON),
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "bindings": copy.deepcopy(v1.evaluation_contract()["bindings"]),
        "parent_endpoint_count": len(parents),
        "parent_endpoints": parents,
        "scalar_leaf_required_fields": list(SCALAR_LEAF_FIELDS),
        "scalar_leaf_count": len(leaves),
        "scalar_leaf_registry": leaves,
        "source_bindings": json.loads(json.dumps(SOURCE_BINDINGS)),
        "sealed_source_requirements": json.loads(json.dumps(SEALED_SOURCES)),
        "decision_topology": decision_topology(leaves),
        "legacy": copy.deepcopy(v1.evaluation_contract()["legacy"]),
        "evaluation_and_selector_training_decoupled": True,
        "claim_authorized": False,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_write_count": 0,
    }
    validate_evaluation_contract_v2(result)
    return result


def validate_evaluation_contract_v2(contract: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(contract))
    expected = evaluation_contract_v2.__wrapped__() if hasattr(
        evaluation_contract_v2, "__wrapped__"
    ) else None
    if set(value) != {
        "schema_version",
        "status",
        "supersedes_schema_version",
        "superseded_v1_role",
        "high_authority",
        "high_authority_sha256",
        "bindings",
        "parent_endpoint_count",
        "parent_endpoints",
        "scalar_leaf_required_fields",
        "scalar_leaf_count",
        "scalar_leaf_registry",
        "source_bindings",
        "sealed_source_requirements",
        "decision_topology",
        "legacy",
        "evaluation_and_selector_training_decoupled",
        "claim_authorized",
        "model_pool_selector_call_count",
        "outcome_values_read",
        "old_artifact_or_cas_write_count",
    }:
        raise ValueError("industrial v2 contract top-level fields drifted")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or value["status"] != STATUS
        or value["supersedes_schema_version"] != v1.SCHEMA_VERSION
        or value["superseded_v1_role"]
        != "immutable_superseded_pre_correction_diagnostic"
        or value["high_authority_sha256"] != HIGH_AUTHORITY_SHA256
        or canonical_sha256(value["high_authority"]).strip()
        != canonical_sha256(json.loads(v1.HIGH_AUTHORITY_JSON)).strip()
        or value["evaluation_and_selector_training_decoupled"] is not True
        or value["claim_authorized"] is not False
        or value["model_pool_selector_call_count"] != 0
        or value["outcome_values_read"] is not False
        or value["old_artifact_or_cas_write_count"] != 0
    ):
        raise ValueError("industrial v2 authority or no-run boundary drifted")
    parents = _parents()
    leaves = _scalar_leaves(parents)
    if (
        value["parent_endpoint_count"] != len(parents)
        or value["parent_endpoints"] != parents
        or value["scalar_leaf_required_fields"] != list(SCALAR_LEAF_FIELDS)
        or value["scalar_leaf_count"] != len(leaves)
        or value["scalar_leaf_registry"] != leaves
    ):
        raise ValueError("industrial v2 parent or scalar leaf registry drifted")
    if len({row["leaf_id"] for row in leaves}) != len(leaves):
        raise ValueError("industrial v2 duplicate scalar leaf")
    for row in value["scalar_leaf_registry"]:
        if set(row) != set(SCALAR_LEAF_FIELDS):
            raise ValueError("industrial v2 scalar leaf schema drifted")
        if row["guardrail_role"] not in ROLE_VALUES:
            raise ValueError("industrial v2 scalar leaf role drifted")
    if (
        value["source_bindings"] != json.loads(json.dumps(SOURCE_BINDINGS))
        or value["sealed_source_requirements"] != json.loads(json.dumps(SEALED_SOURCES))
        or value["decision_topology"] != decision_topology(leaves)
    ):
        raise ValueError("industrial v2 evidence or decision topology drifted")
    if value["decision_topology"]["weighted_compensation_allowed"] is not False:
        raise ValueError("industrial v2 weighted compensation forbidden")
    if any(
        row["claim_gate_state"] not in {
            CLAIM_MARGIN_STATE,
            "descriptive_only_not_claim_gate",
            "not_testable_evidence_missing",
        }
        for row in leaves
    ):
        raise ValueError("industrial v2 claim gate state drifted")
    return value


def _parse_inventory(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in (path / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        sha, name = line.split("  ", 1)
        rows[name] = sha
    return rows


def _pointer(value: Any, pointer: str) -> Any:
    current = value
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, Mapping) or token not in current:
            raise ValueError(f"missing structural JSON pointer: {pointer}")
        current = current[token]
    return current


def audit_sealed_sources(source_dirs: Mapping[str, str | Path]) -> dict[str, Any]:
    if set(source_dirs) != set(SEALED_SOURCES):
        raise ValueError("industrial v2 sealed source directory set drifted")
    inventories: dict[str, Any] = {}
    reports: dict[str, Any] = {}
    for name, expected in SEALED_SOURCES.items():
        path = Path(source_dirs[name])
        verify_complete_seal(path, str(expected["root"]))
        inventory = _parse_inventory(path)
        for filename, sha in expected["required_inventory"].items():
            if inventory.get(filename) != sha:
                raise ValueError(f"sealed inventory entry drifted: {name}/{filename}")
        selected = {
            filename: inventory[filename]
            for filename in sorted(expected["required_inventory"])
        }
        inventories[name] = {
            "artifact_root_sha256": expected["root"],
            "artifact_review_root_sha256": expected["review_root"],
            "inventory_manifest_sha256": canonical_sha256(selected),
            "entries": selected,
        }
        if name in {"evaluation_v2_contract", "metric_contract"}:
            reports[name] = json.loads(
                (path / "report.json").read_text(encoding="utf-8")
            )
        elif name == "execution":
            reports[name] = json.loads(
                (path / "artifact_report.json").read_text(encoding="utf-8")
            )
    if reports["execution"].get("execution_report_sha256") != SEALED_SOURCES[
        "execution"
    ]["required_inventory"]["report.json"]:
        raise ValueError("execution artifact-report binding drifted")
    return {"inventories": inventories, "reports": reports}


def capability_matrix_v2(
    contract: Mapping[str, Any], source_dirs: Mapping[str, str | Path]
) -> dict[str, Any]:
    validated = validate_evaluation_contract_v2(contract)
    audit = audit_sealed_sources(source_dirs)
    rows: list[dict[str, Any]] = []
    for leaf in validated["scalar_leaf_registry"]:
        binding = SOURCE_BINDINGS[leaf["source_binding_id"]]
        evidence: list[dict[str, Any]] = []
        for artifact_name in binding["artifacts"]:
            inventory = audit["inventories"][artifact_name]
            for filename, sha in inventory["entries"].items():
                evidence.append(
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
        for pointer in binding["json_pointers"]:
            report_name = (
                "metric_contract"
                if pointer.startswith("/contract/body_proxy/")
                else "evaluation_v2_contract"
            )
            _pointer(audit["reports"][report_name], pointer)
        rows.append(
            {
                "leaf_id": leaf["leaf_id"],
                "parent_id": leaf["parent_id"],
                "evidence_class": binding["evidence_class"],
                "evidence_inventory": evidence,
                "canonical_json_pointers": list(binding["json_pointers"]),
                "source_shape": binding["shape"],
                "source_units": binding["units"],
                "applicability_prerequisites": binding["prerequisites"],
                "transform_inputs": binding["transform_inputs"],
                "reason": binding["reason"],
                "structure_only": True,
                "outcome_values_read": False,
            }
        )
    result = {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "status": "sealed_structure_only_scalar_leaf_capability_audit",
        "contract_sha256": canonical_sha256(validated),
        "scalar_leaf_count": len(rows),
        "rows": rows,
        "sealed_inventory_audit": audit["inventories"],
        "structure_only": True,
        "outcome_values_read": False,
        "model_pool_selector_call_count": 0,
        "old_artifact_or_cas_write_count": 0,
    }
    validate_capability_matrix_v2(result, validated, source_dirs)
    return result


def validate_capability_matrix_v2(
    matrix: Mapping[str, Any],
    contract: Mapping[str, Any],
    source_dirs: Mapping[str, str | Path],
) -> dict[str, Any]:
    value = copy.deepcopy(dict(matrix))
    validated = validate_evaluation_contract_v2(contract)
    audit = audit_sealed_sources(source_dirs)
    expected = capability_matrix_v2.__wrapped__(validated, source_dirs) if hasattr(
        capability_matrix_v2, "__wrapped__"
    ) else None
    if set(value) != {
        "schema_version",
        "status",
        "contract_sha256",
        "scalar_leaf_count",
        "rows",
        "sealed_inventory_audit",
        "structure_only",
        "outcome_values_read",
        "model_pool_selector_call_count",
        "old_artifact_or_cas_write_count",
    }:
        raise ValueError("industrial v2 capability top-level fields drifted")
    if (
        value["schema_version"] != CAPABILITY_SCHEMA_VERSION
        or value["status"] != "sealed_structure_only_scalar_leaf_capability_audit"
        or value["contract_sha256"] != canonical_sha256(validated)
        or value["scalar_leaf_count"] != len(validated["scalar_leaf_registry"])
        or value["sealed_inventory_audit"] != audit["inventories"]
        or value["structure_only"] is not True
        or value["outcome_values_read"] is not False
        or value["model_pool_selector_call_count"] != 0
        or value["old_artifact_or_cas_write_count"] != 0
    ):
        raise ValueError("industrial v2 capability authority drifted")
    leaf_map = {row["leaf_id"]: row for row in validated["scalar_leaf_registry"]}
    if len(value["rows"]) != len(leaf_map):
        raise ValueError("industrial v2 capability leaf count drifted")
    seen: set[str] = set()
    for row in value["rows"]:
        if set(row) != {
            "leaf_id",
            "parent_id",
            "evidence_class",
            "evidence_inventory",
            "canonical_json_pointers",
            "source_shape",
            "source_units",
            "applicability_prerequisites",
            "transform_inputs",
            "reason",
            "structure_only",
            "outcome_values_read",
        }:
            raise ValueError("industrial v2 capability row schema drifted")
        leaf_id = row["leaf_id"]
        if leaf_id in seen or leaf_id not in leaf_map:
            raise ValueError("industrial v2 capability leaf ID drifted")
        seen.add(leaf_id)
        leaf = leaf_map[leaf_id]
        binding = SOURCE_BINDINGS[leaf["source_binding_id"]]
        if (
            row["parent_id"] != leaf["parent_id"]
            or row["evidence_class"] != binding["evidence_class"]
            or row["canonical_json_pointers"] != list(binding["json_pointers"])
            or row["source_shape"] != binding["shape"]
            or row["source_units"] != binding["units"]
            or row["applicability_prerequisites"] != binding["prerequisites"]
            or row["transform_inputs"] != binding["transform_inputs"]
            or row["reason"] != binding["reason"]
            or row["structure_only"] is not True
            or row["outcome_values_read"] is not False
        ):
            raise ValueError("industrial v2 capability semantic binding drifted")
        expected_evidence = []
        for artifact_name in binding["artifacts"]:
            inventory = audit["inventories"][artifact_name]
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
        if row["evidence_inventory"] != expected_evidence:
            raise ValueError("industrial v2 capability inventory evidence drifted")
        for pointer in binding["json_pointers"]:
            report_name = (
                "metric_contract"
                if pointer.startswith("/contract/body_proxy/")
                else "evaluation_v2_contract"
            )
            _pointer(audit["reports"][report_name], pointer)
    if seen != set(leaf_map):
        raise ValueError("industrial v2 capability omitted scalar leaf")
    return value


# Avoid recursive expected-object construction while retaining strict public validators.
def _build_contract() -> dict[str, Any]:
    parents = _parents()
    leaves = _scalar_leaves(parents)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "supersedes_schema_version": v1.SCHEMA_VERSION,
        "superseded_v1_role": "immutable_superseded_pre_correction_diagnostic",
        "high_authority": json.loads(v1.HIGH_AUTHORITY_JSON),
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "bindings": copy.deepcopy(v1.evaluation_contract()["bindings"]),
        "parent_endpoint_count": len(parents),
        "parent_endpoints": parents,
        "scalar_leaf_required_fields": list(SCALAR_LEAF_FIELDS),
        "scalar_leaf_count": len(leaves),
        "scalar_leaf_registry": leaves,
        "source_bindings": json.loads(json.dumps(SOURCE_BINDINGS)),
        "sealed_source_requirements": json.loads(json.dumps(SEALED_SOURCES)),
        "decision_topology": decision_topology(leaves),
        "legacy": copy.deepcopy(v1.evaluation_contract()["legacy"]),
        "evaluation_and_selector_training_decoupled": True,
        "claim_authorized": False,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_write_count": 0,
    }


evaluation_contract_v2.__wrapped__ = _build_contract  # type: ignore[attr-defined]


def _build_capability(
    contract: Mapping[str, Any], source_dirs: Mapping[str, str | Path]
) -> dict[str, Any]:
    validated = validate_evaluation_contract_v2(contract)
    audit = audit_sealed_sources(source_dirs)
    rows = []
    for leaf in validated["scalar_leaf_registry"]:
        binding = SOURCE_BINDINGS[leaf["source_binding_id"]]
        evidence = []
        for artifact_name in binding["artifacts"]:
            inventory = audit["inventories"][artifact_name]
            for filename, sha in inventory["entries"].items():
                evidence.append(
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
        for pointer in binding["json_pointers"]:
            report_name = (
                "metric_contract"
                if pointer.startswith("/contract/body_proxy/")
                else "evaluation_v2_contract"
            )
            _pointer(audit["reports"][report_name], pointer)
        rows.append(
            {
                "leaf_id": leaf["leaf_id"],
                "parent_id": leaf["parent_id"],
                "evidence_class": binding["evidence_class"],
                "evidence_inventory": evidence,
                "canonical_json_pointers": list(binding["json_pointers"]),
                "source_shape": binding["shape"],
                "source_units": binding["units"],
                "applicability_prerequisites": binding["prerequisites"],
                "transform_inputs": binding["transform_inputs"],
                "reason": binding["reason"],
                "structure_only": True,
                "outcome_values_read": False,
            }
        )
    return {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "status": "sealed_structure_only_scalar_leaf_capability_audit",
        "contract_sha256": canonical_sha256(validated),
        "scalar_leaf_count": len(rows),
        "rows": rows,
        "sealed_inventory_audit": audit["inventories"],
        "structure_only": True,
        "outcome_values_read": False,
        "model_pool_selector_call_count": 0,
        "old_artifact_or_cas_write_count": 0,
    }


capability_matrix_v2.__wrapped__ = _build_capability  # type: ignore[attr-defined]
