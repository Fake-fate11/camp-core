from __future__ import annotations

from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_holdout_contract import canonical_sha256


PLAN_ARMS = (
    "candidate0_operational_default",
    "camp_static14d",
    "camp_scene14d_no_v2i",
)
SIGNAL_COMPLETE_PLAN_SCHEMA_VERSION = (
    "camp_dp_v25_signal_complete_execution_plan_v1"
)


NONFRESH_CANARY_SPLIT = "fresh_b4_nonfresh_production_canary"
NONFRESH_CANARY_PLAN_SCHEMA_VERSION = (
    "camp_dp_v25_nonfresh_production_equivalence_plan_v1"
)
NONFRESH_SCENARIO_CLASSES = (
    "mapped_controlled_override",
    "mapped_observe",
    "no_signal",
)

_IDENTITY_FIELDS = {
    "identity_ordinal",
    "split",
    "scenario_identity_sha256",
    "map_sha256",
    "map_geometry_sha256",
    "map_relative_path",
    "corridor_sha256",
    "intersection_sha256",
    "route_identity_sha256",
    "route_family_sha256",
    "source_independent_geometry_sha256",
    "physical_payload",
    "source_chain_sha256",
    "source_chain",
    "initial_pose",
    "goal_pose",
    "route_spec",
    "route_length_m",
    "scenario_family",
    "risk_tier",
    "benchmark_stratum",
    "semantic_variant",
    "variant_index",
    "parameters",
    "semantic_parameter_block_sha256",
    "signal_source_class",
    "phase_authority_mode",
    "controlled_current_phase",
    "future_phase_program_present",
    "same_tick_current_phase_required",
    "phase_remaining_available",
    "source_timestamp_required",
    "decision_timestamp_required",
    "fresh_b2_opened",
    "outcome_fields_consumed",
    "nonfresh_scenario_class",
    "source_fixture_root_sha256",
}
_UNIT_FIELDS = {
    "unit_ordinal",
    "scenario_identity_sha256",
    "seed",
    "ordered_arms",
    "unit_sha256",
}
_PLAN_FIELDS = {
    "schema_version",
    "status",
    "split",
    "source_family",
    "map_count",
    "intersection_count",
    "corridor_count",
    "route_count",
    "identity_count",
    "seeds",
    "seeds_counted_as_independent",
    "execution_unit_count",
    "planned_arm_run_count",
    "ticks_per_arm_run",
    "identities",
    "execution_units",
    "scenario_family_counts",
    "risk_tier_counts",
    "benchmark_stratum_counts",
    "family_tier_counts",
    "paired_arms",
    "paper_subset_ablations",
    "candidate_count",
    "candidate0_semantics",
    "candidate_tensor_modified",
    "sequential_fixed_k8",
    "phase_remaining_available",
    "online_context_phase_program_consumed",
    "online_context_forbidden_fields",
    "failed_run_policy",
    "fresh_b2_opened",
    "outcome_fields_consumed",
    "training_executed",
    "calibration_outcomes_consumed",
    "nonfresh_provider_only",
    "real_b4_identity_or_rows_used",
    "plan_payload_sha256",
}


def validate_holdout_execution_plan(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("holdout execution plan must be an object")
    if value.get("schema_version") == SIGNAL_COMPLETE_PLAN_SCHEMA_VERSION:
        from .diffusion_planner_v25_signal_complete_plan import (
            validate_signal_complete_execution_plan,
        )

        return validate_signal_complete_execution_plan(value)
    if value.get("schema_version") == NONFRESH_CANARY_PLAN_SCHEMA_VERSION:
        return validate_nonfresh_production_equivalence_plan(value)
    raise ValueError("holdout execution plan schema drifted")


def freeze_nonfresh_production_equivalence_plan(
    *,
    identities: Sequence[Mapping[str, Any]],
    execution_units: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    identity_rows = [dict(row) for row in identities]
    units = [dict(row) for row in execution_units]
    result = {
        "schema_version": NONFRESH_CANARY_PLAN_SCHEMA_VERSION,
        "status": "frozen_nonfresh_actual_native_production_equivalence_plan",
        "split": NONFRESH_CANARY_SPLIT,
        "source_family": "accepted_nonfresh_actual_native_fixture",
        "map_count": len({row["map_sha256"] for row in identity_rows}),
        "intersection_count": len(
            {
                row["intersection_sha256"]
                for row in identity_rows
                if row["intersection_sha256"] is not None
            }
        ),
        "corridor_count": len(
            {row["corridor_sha256"] for row in identity_rows}
        ),
        "route_count": len(
            {row["route_identity_sha256"] for row in identity_rows}
        ),
        "identity_count": len(identity_rows),
        "seeds": sorted({row["seed"] for row in units}),
        "seeds_counted_as_independent": False,
        "execution_unit_count": len(units),
        "planned_arm_run_count": sum(
            len(row["ordered_arms"]) for row in units
        ),
        "ticks_per_arm_run": 64,
        "identities": identity_rows,
        "execution_units": units,
        "scenario_family_counts": _counts(identity_rows, "scenario_family"),
        "risk_tier_counts": _counts(identity_rows, "risk_tier"),
        "benchmark_stratum_counts": _counts(
            identity_rows, "benchmark_stratum"
        ),
        "family_tier_counts": _pair_counts(
            identity_rows, "scenario_family", "risk_tier"
        ),
        "paired_arms": list(PLAN_ARMS),
        "paper_subset_ablations": [],
        "candidate_count": 8,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "candidate_tensor_modified": False,
        "sequential_fixed_k8": True,
        "phase_remaining_available": False,
        "online_context_phase_program_consumed": False,
        "online_context_forbidden_fields": [
            "map_id",
            "route_id",
            "scenario_id",
            "split_id",
            "seed_id",
            "future_phase_program",
            "closed_loop_outcome",
            "fresh_outcome",
            "private_dp_latent",
        ],
        "failed_run_policy": "retain_denominator_no_replacement_no_imputation",
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "training_executed": False,
        "calibration_outcomes_consumed": False,
        "nonfresh_provider_only": True,
        "real_b4_identity_or_rows_used": False,
    }
    result["plan_payload_sha256"] = canonical_sha256(result)
    return validate_nonfresh_production_equivalence_plan(result)


def validate_nonfresh_production_equivalence_plan(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PLAN_FIELDS:
        raise ValueError("nonFresh production-equivalence plan fields drifted")
    result = dict(value)
    identities = result["identities"]
    units = result["execution_units"]
    if (
        result["status"]
        != "frozen_nonfresh_actual_native_production_equivalence_plan"
        or result["split"] != NONFRESH_CANARY_SPLIT
        or type(identities) is not list
        or type(units) is not list
        or len(identities) != 3
        or len(units) != 3
    ):
        raise ValueError("nonFresh production-equivalence denominator drifted")
    scenario_classes: list[str] = []
    scenario_ids: list[str] = []
    for index, row in enumerate(identities):
        if (
            type(row) is not dict
            or set(row) != _IDENTITY_FIELDS
            or row["identity_ordinal"] != index
            or row["split"] != NONFRESH_CANARY_SPLIT
            or row["outcome_fields_consumed"] != []
            or row["fresh_b2_opened"] is not False
            or row["future_phase_program_present"] is not False
            or row["phase_remaining_available"] is not False
        ):
            raise ValueError("nonFresh production-equivalence identity drifted")
        for name in (
            "scenario_identity_sha256",
            "map_sha256",
            "map_geometry_sha256",
            "corridor_sha256",
            "route_identity_sha256",
            "route_family_sha256",
            "source_independent_geometry_sha256",
            "source_chain_sha256",
            "semantic_parameter_block_sha256",
            "source_fixture_root_sha256",
        ):
            _sha(row[name], name)
        if row["intersection_sha256"] is not None:
            _sha(row["intersection_sha256"], "intersection_sha256")
        scenario_class = row["nonfresh_scenario_class"]
        if scenario_class not in NONFRESH_SCENARIO_CLASSES:
            raise ValueError("nonFresh production-equivalence class drifted")
        if scenario_class == "no_signal":
            if (
                row["signal_source_class"] != "no_signal"
                or row["phase_authority_mode"] is not None
            ):
                raise ValueError("nonFresh no-signal identity drifted")
        elif (
            row["signal_source_class"] != "mapped_signal"
            or row["phase_authority_mode"]
            != {
                "mapped_observe": "observe_same_tick_request",
                "mapped_controlled_override": "controlled_same_tick_override",
            }[scenario_class]
        ):
            raise ValueError("nonFresh mapped identity drifted")
        scenario_classes.append(scenario_class)
        scenario_ids.append(row["scenario_identity_sha256"])
    if sorted(scenario_classes) != sorted(NONFRESH_SCENARIO_CLASSES):
        raise ValueError("nonFresh scenario-class coverage drifted")
    for index, row in enumerate(units):
        if (
            type(row) is not dict
            or set(row) != _UNIT_FIELDS
            or row["unit_ordinal"] != index
            or row["scenario_identity_sha256"] != scenario_ids[index]
            or type(row["seed"]) is not int
            or row["seed"] < 0
            or row["ordered_arms"] != list(PLAN_ARMS[index:] + PLAN_ARMS[:index])
        ):
            raise ValueError("nonFresh production-equivalence unit drifted")
        payload = {
            "scenario_identity_sha256": row["scenario_identity_sha256"],
            "seed": row["seed"],
            "ordered_arms": row["ordered_arms"],
        }
        if row["unit_sha256"] != canonical_sha256(payload):
            raise ValueError("nonFresh production-equivalence unit SHA drifted")
    payload = dict(result)
    stored = payload.pop("plan_payload_sha256")
    if stored != canonical_sha256(payload):
        raise ValueError("nonFresh production-equivalence plan SHA drifted")
    exact = {
        "schema_version": NONFRESH_CANARY_PLAN_SCHEMA_VERSION,
        "status": "frozen_nonfresh_actual_native_production_equivalence_plan",
        "split": NONFRESH_CANARY_SPLIT,
        "source_family": "accepted_nonfresh_actual_native_fixture",
        "identity_count": 3,
        "execution_unit_count": 3,
        "planned_arm_run_count": 9,
        "ticks_per_arm_run": 64,
        "paired_arms": list(PLAN_ARMS),
        "paper_subset_ablations": [],
        "candidate_count": 8,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "candidate_tensor_modified": False,
        "sequential_fixed_k8": True,
        "phase_remaining_available": False,
        "online_context_phase_program_consumed": False,
        "online_context_forbidden_fields": [
            "map_id",
            "route_id",
            "scenario_id",
            "split_id",
            "seed_id",
            "future_phase_program",
            "closed_loop_outcome",
            "fresh_outcome",
            "private_dp_latent",
        ],
        "failed_run_policy": "retain_denominator_no_replacement_no_imputation",
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "training_executed": False,
        "calibration_outcomes_consumed": False,
        "nonfresh_provider_only": True,
        "real_b4_identity_or_rows_used": False,
    }
    for name, expected_value in exact.items():
        if result[name] != expected_value:
            raise ValueError(
                f"nonFresh production-equivalence plan {name} drifted"
            )
    count_contract = {
        "map_count": len({row["map_sha256"] for row in identities}),
        "intersection_count": len(
            {
                row["intersection_sha256"]
                for row in identities
                if row["intersection_sha256"] is not None
            }
        ),
        "corridor_count": len(
            {row["corridor_sha256"] for row in identities}
        ),
        "route_count": len(
            {row["route_identity_sha256"] for row in identities}
        ),
        "seeds": sorted({row["seed"] for row in units}),
        "scenario_family_counts": _counts(identities, "scenario_family"),
        "risk_tier_counts": _counts(identities, "risk_tier"),
        "benchmark_stratum_counts": _counts(
            identities, "benchmark_stratum"
        ),
        "family_tier_counts": _pair_counts(
            identities, "scenario_family", "risk_tier"
        ),
    }
    for name, expected_value in count_contract.items():
        if result[name] != expected_value:
            raise ValueError(
                f"nonFresh production-equivalence plan {name} drifted"
            )
    if result["seeds_counted_as_independent"] is not False:
        raise ValueError("nonFresh seeds cannot be independent clusters")
    return result


def _counts(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    names = sorted({str(row[field]) for row in rows})
    return {
        name: sum(str(row[field]) == name for row in rows)
        for name in names
    }


def _pair_counts(
    rows: Sequence[Mapping[str, Any]], left: str, right: str
) -> dict[str, int]:
    names = sorted({f"{row[left]}/{row[right]}" for row in rows})
    return {
        name: sum(f"{row[left]}/{row[right]}" == name for row in rows)
        for name in names
    }


def _sha(value: Any, name: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
