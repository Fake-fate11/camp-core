from __future__ import annotations

import copy
import hashlib
import json

import pytest

from camp_core.integrations.diffusion_planner_v25_calibration import (
    CALIBRATION_ROOT_BINDINGS,
    estimate_v25_noninferiority_margin_resolvability,
    freeze_v25_calibration_contract,
)
from camp_core.integrations.diffusion_planner_v25_fresh_b2 import (
    FROZEN_ROOT_BINDINGS,
    TIERS,
    qualify_fresh_b2_preopen,
    validate_fresh_b2_preopen_qualification,
)
from camp_core.integrations.diffusion_planner_v25_statistics import (
    NONINFERIORITY_METRICS,
    REQUIRED_CONTROLLED_EVENT_FAMILIES,
)


def _eligible_calibration_contract() -> dict:
    performance = {name: 0.0 for name in NONINFERIORITY_METRICS}
    rows = []
    for index in range(95):
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
        rows.append(
            {
                "schema_version": "camp_dp_v25_candidate0_ni_calibration_row_v2",
                "arm": "candidate0_operational_default",
                "heterogeneity_cluster_id": f"map-{index % 5}",
                "run_instance_sha256": f"{index + 7000:064x}",
                "repeatability_identity": identity,
                "repeatability_identity_sha256": identity_sha,
                "measurement_sha256": f"{index + 8000:064x}",
                "performance": dict(performance),
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
            "paired_eligible_run_count": 95,
            "retained_failure_run_count": 5,
            "paired_eligible_rate": 0.95,
        },
        noninferiority_resolvability=(
            estimate_v25_noninferiority_margin_resolvability(rows)
        ),
        frozen_model_registry_sha256="b" * 64,
        training_scale_sha256="c" * 64,
        context_scaler_sha256="d" * 64,
    )


def _power_pilot_receipt(root: str = "f" * 64) -> dict:
    return {
        "schema_version": "camp_dp_v25_power_pilot_variance_receipt_v1",
        "status": "sealed_train_or_calibration_pilot_variance",
        "source_artifact_root_sha256": root,
        "source_split": "calibration_pilot",
        "calibration_arm": "candidate0_operational_default",
        "cluster_estimator": "equal_mass_independent_cluster_standard_deviation",
        "variance_target": "candidate0_safety_cost_proxy_disclosed_not_paired_delta",
        "safety_cost_cluster_standard_deviation": 0.2,
        "red_component_cluster_standard_deviation": 0.1,
        "total_independent_cluster_count": 5,
        "red_independent_cluster_count": 3,
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def test_fresh_b2_qualification_requires_all_families_signal_and_real_clusters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    split_rows = []
    fresh_rows = []
    license_rows = []
    for family_index, family in enumerate(REQUIRED_CONTROLLED_EVENT_FAMILIES):
        for tier_index, tier in enumerate(TIERS):
            index = family_index * len(TIERS) + tier_index
            mapped = family == "red_light_phase_timing"
            route = f"{index + 1:064x}"
            map_geometry = f"{100 + family_index:064x}"
            map_file = f"{200 + family_index:064x}"
            intersection = f"{300 + tier_index:064x}" if mapped else None
            corridor = f"{400 + index:064x}"
            split_rows.append(
                {
                    "split": "fresh_b2",
                    "source_family": "project_authored_signal_complete",
                    "map_geometry_sha256": map_geometry,
                    "intersection_sha256": intersection,
                    "corridor_sha256": corridor,
                    "route_family_sha256": f"{500 + index:064x}",
                    "semantic_parameter_block_sha256": f"{600 + index:064x}",
                    "seed_namespace": "fresh-b2",
                    "route_identity_sha256": route,
                    "scenario_family": family,
                }
            )
            fresh_rows.append(
                {
                    key: value
                    for key, value in {
                        **split_rows[-1],
                        "map_file_sha256": map_file,
                        "benchmark_stratum": "controlled_stress",
                        "tier": tier,
                        "signal_source_class": "mapped_signal" if mapped else "no_signal",
                        "phase_authority_mode": (
                            "controlled_same_tick_override" if mapped else None
                        ),
                        "source_chain": {"kind": "mapped" if mapped else "none"},
                        "route_length_m": 80.0,
                        "speed_source_sha256": f"{700 + index:064x}",
                        "static_signal_chain_qualified": True,
                        "runtime_same_tick_signal_receipt_required": True,
                        "runtime_fixed_dp_k8_support_required": True,
                        "preopen_dp_forward_executed": False,
                        "outcome_fields_consumed": [],
                    }.items()
                    if key
                    not in {"split", "seed_namespace"}
                }
            )
            if not any(row["map_file_sha256"] == map_file for row in license_rows):
                license_rows.append(
                    {
                        "map_path": f"maps/{map_file}.osm",
                        "map_file_sha256": map_file,
                        "map_geometry_sha256": map_geometry,
                        "source_kind": "project_authored_synthetic",
                        "source_reference": "repo MIT source",
                        "license_spdx": "MIT",
                        "license_evidence_sha256": f"{800 + family_index:064x}",
                        "project_authored": True,
                    }
                )
    natural_split = copy.deepcopy(split_rows[0])
    natural_split.update(
        corridor_sha256=f"{901:064x}",
        route_family_sha256=f"{902:064x}",
        semantic_parameter_block_sha256=f"{903:064x}",
        route_identity_sha256=f"{904:064x}",
        scenario_family="naturalistic_background",
    )
    split_rows.append(natural_split)
    natural = copy.deepcopy(fresh_rows[0])
    natural.update(
        corridor_sha256=natural_split["corridor_sha256"],
        route_family_sha256=natural_split["route_family_sha256"],
        semantic_parameter_block_sha256=natural_split[
            "semantic_parameter_block_sha256"
        ],
        route_identity_sha256=natural_split["route_identity_sha256"],
        benchmark_stratum="naturalistic",
        scenario_family="naturalistic_background",
        tier="naturalistic",
    )
    fresh_rows.append(natural)
    train = copy.deepcopy(split_rows[0])
    train.update(
        split="train",
        map_geometry_sha256="a" * 64,
        intersection_sha256=None,
        corridor_sha256="b" * 64,
        route_family_sha256="c" * 64,
        semantic_parameter_block_sha256="d" * 64,
        seed_namespace="train",
        route_identity_sha256="e" * 64,
    )
    calibration = copy.deepcopy(train)
    calibration.update(
        split="calibration",
        map_geometry_sha256="1" * 64,
        corridor_sha256="2" * 64,
        route_family_sha256="3" * 64,
        semantic_parameter_block_sha256="4" * 64,
        seed_namespace="cal",
        route_identity_sha256="5" * 64,
    )
    split_rows.extend([train, calibration])

    def mapped(chain):
        assert chain == {"kind": "mapped"}
        return {
            "phase_authority_mode": "controlled_same_tick_override",
            "route_identity_sha256": current["route_identity_sha256"],
            "source_map_sha256": current["map_file_sha256"],
        }

    def no_signal(chain):
        assert chain == {"kind": "none"}
        return {
            "route_identity_sha256": current["route_identity_sha256"],
            "source_map_sha256": current["map_file_sha256"],
        }

    # Keep this test focused on the qualification join/count contract. The
    # route-level validators have their own exact source-chain fixture suite.
    current = {}
    from camp_core.integrations import diffusion_planner_v25_fresh_b2 as module

    def mapped_dispatch(chain):
        current.update(next(row for row in fresh_rows if row["source_chain"] is chain))
        return mapped(chain)

    def no_signal_dispatch(chain):
        current.update(next(row for row in fresh_rows if row["source_chain"] is chain))
        return no_signal(chain)

    monkeypatch.setattr(module, "validate_mapped_signal_chain", mapped_dispatch)
    monkeypatch.setattr(module, "validate_no_signal_chain", no_signal_dispatch)
    result = qualify_fresh_b2_preopen(
        split_rows=split_rows,
        map_license_rows=license_rows,
        fresh_rows=fresh_rows,
        frozen_root_bindings={name: "f" * 64 for name in FROZEN_ROOT_BINDINGS},
        calibration_contract=_eligible_calibration_contract(),
        calibration_contract_root_sha256="f" * 64,
        power_pilot_receipt=_power_pilot_receipt(),
    )
    assert result["fresh_b2_opened"] is False
    assert result["calibration_contract_status"] == "calibration_freeze_passed"
    assert result["outcome_fields_consumed"] == []
    assert result["family_tier_counts"] == {
        f"{family}/{tier}": 1
        for family in REQUIRED_CONTROLLED_EVENT_FAMILIES
        for tier in TIERS
    }
    assert result["independent_unit_counts"]["red_power_clusters"] == 3
    assert result["real_inventory_ceiling_below_target"] is True
    assert result["benchmark_stratum_counts"] == {
        "controlled_stress": 21,
        "naturalistic": 1,
    }
    assert validate_fresh_b2_preopen_qualification(copy.deepcopy(result)) == result

    mutations = []
    mutated = copy.deepcopy(result)
    mutated["unexpected"] = False
    mutations.append((mutated, "field set drifted"))
    mutated = copy.deepcopy(result)
    mutated["fresh_row_count"] = float(mutated["fresh_row_count"])
    mutations.append((mutated, "row count is invalid"))
    mutated = copy.deepcopy(result)
    mutated["independent_unit_counts"]["total_power_clusters"] += 1
    mutations.append((mutated, "does not independently recompute"))
    mutated = copy.deepcopy(result)
    mutated["safety_cost_power"]["normal_approximation_mde"] += 1.0
    mutations.append((mutated, "does not independently recompute"))
    mutated = copy.deepcopy(result)
    mutated["power_pilot_receipt"]["source_artifact_root_sha256"] = "e" * 64
    mutations.append((mutated, "exact value drifted"))
    mutated = copy.deepcopy(result)
    mutated["power_pilot_receipt"]["safety_cost_cluster_standard_deviation"] = 0.3
    mutations.append((mutated, "power variance differs from the sealed pilot"))
    mutated = copy.deepcopy(result)
    mutated["signal_source_class_counts"]["no_signal"] += 1
    mutations.append((mutated, "signal-source denominator drifted"))
    mutated = copy.deepcopy(result)
    mutated["real_inventory_ceiling_below_target"] = False
    mutations.append((mutated, "inventory-ceiling status drifted"))
    mutated = copy.deepcopy(result)
    mutated["calibration_contract_root_sha256"] = "e" * 64
    mutations.append((mutated, "calibration root drifted"))
    mutated = copy.deepcopy(result)
    mutated["zero_overlap_receipt"]["split_row_counts"]["fresh_b2"] += 1
    mutations.append((mutated, "zero-overlap split accounting drifted"))
    mutated = copy.deepcopy(result)
    mutated["zero_overlap_receipt"]["independent_unit_counts"]["route_identity"][
        "fresh_b2"
    ] -= 1
    mutations.append((mutated, "zero-overlap route denominator drifted"))
    mutated = copy.deepcopy(result)
    source_kind = next(iter(mutated["map_license_receipt"]["source_kind_counts"]))
    mutated["map_license_receipt"]["source_kind_counts"][source_kind] += 1
    mutations.append((mutated, "map-license receipt accounting drifted"))
    for mutated, match in mutations:
        with pytest.raises(ValueError, match=match):
            validate_fresh_b2_preopen_qualification(mutated)

    bad = copy.deepcopy(fresh_rows)
    bad[0]["outcome_fields_consumed"] = ["collision"]
    with pytest.raises(ValueError, match="qualification values"):
        qualify_fresh_b2_preopen(
            split_rows=split_rows,
            map_license_rows=license_rows,
            fresh_rows=bad,
            frozen_root_bindings={name: "f" * 64 for name in FROZEN_ROOT_BINDINGS},
            calibration_contract=_eligible_calibration_contract(),
            calibration_contract_root_sha256="f" * 64,
            power_pilot_receipt=_power_pilot_receipt(),
        )

    failed_calibration = _eligible_calibration_contract()
    failed_calibration["inventory"]["route_count"] = 49
    failed_calibration["independent_unit_target_passed"] = False
    failed_calibration["status"] = "calibration_freeze_scientifically_ineligible"
    failed_calibration["fresh_preopen_qualification_allowed"] = False
    with pytest.raises(ValueError, match="eligible unopened calibration"):
        qualify_fresh_b2_preopen(
            split_rows=split_rows,
            map_license_rows=license_rows,
            fresh_rows=fresh_rows,
            frozen_root_bindings={name: "f" * 64 for name in FROZEN_ROOT_BINDINGS},
            calibration_contract=failed_calibration,
            calibration_contract_root_sha256="f" * 64,
            power_pilot_receipt=_power_pilot_receipt(),
        )

    with pytest.raises(ValueError, match="root binding drifted"):
        qualify_fresh_b2_preopen(
            split_rows=split_rows,
            map_license_rows=license_rows,
            fresh_rows=fresh_rows,
            frozen_root_bindings={name: "f" * 64 for name in FROZEN_ROOT_BINDINGS},
            calibration_contract=_eligible_calibration_contract(),
            calibration_contract_root_sha256="e" * 64,
            power_pilot_receipt=_power_pilot_receipt(),
        )
