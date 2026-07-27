from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (
    evaluation_contract_v3,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_evaluation_actor_binding import (
    AFFECTED_LEAF_SET_SHA256,
    EXECUTION_ROOT_SHA256,
    affected_leaf_ids,
    correction_contract,
    validate_sealed_actor_binding,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_evaluation_actor_binding_review import (
    expected_affected_leaf_ids,
    rebuild_actor_binding_literal,
    review_contract_literal,
)


CLUSTER_ROOT = "a" * 64


def _actor(actor_id: str = "actor-0") -> dict:
    return {
        "id": actor_id,
        "position_xy": [10.0, 1.0],
        "velocity_xy_mps": [2.0, 0.0],
        "heading_rad": 0.0,
        "length_m": 4.5,
        "width_m": 1.8,
        "wheelbase_m": 2.7,
    }


def _arm(name: str) -> dict:
    return {
        "arm": name,
        "legacy_header": {
            "spawn_config_sha256": "drifted",
            "initial_state_sha256": None,
            "initial_input_sha256": "absent",
        },
        "ticks": [
            {
                "tick_index": index,
                "_safety_record": {"actors": [_actor()]},
            }
            for index in range(64)
        ],
    }


def _bind(arm: dict) -> dict:
    return validate_sealed_actor_binding(
        arm,
        execution_root_sha256=EXECUTION_ROOT_SHA256,
        cluster_root_sha256=CLUSTER_ROOT,
        cluster_index=0,
        expected_arm=arm["arm"],
    )


def _review_bind(arm: dict) -> dict:
    return rebuild_actor_binding_literal(
        arm,
        execution_root_sha256=EXECUTION_ROOT_SHA256,
        cluster_root_sha256=CLUSTER_ROOT,
        cluster_index=0,
        expected_arm=arm["arm"],
    )


def test_exact_43_leaf_set_and_118_unaffected_regression() -> None:
    affected = affected_leaf_ids()
    assert affected == expected_affected_leaf_ids()
    assert len(affected) == 43
    contract = evaluation_contract_v3()
    all_ids = {row["leaf_id"] for row in contract["scalar_leaf_registry"]}
    assert len(all_ids) == 161
    assert set(affected).issubset(all_ids)
    assert len(all_ids - set(affected)) == 118
    assert (
        "safety.collision_onset_relative_closing_speed_kinematic_proxy_mps"
        not in affected
    )
    assert AFFECTED_LEAF_SET_SHA256 == (
        "7d0a406b00ce2b7b86cce50f89d6cfa24714c37493100278b55bcb567efb33af"
    )


def test_contract_is_independently_reviewed() -> None:
    contract = correction_contract("1" * 40)
    assert review_contract_literal(contract) == contract
    for field, value in (
        ("candidate0_special_case_allowed", True),
        ("legacy_supplementary_header_gate_allowed", True),
        ("three_arm_identical_qualification_rule", False),
    ):
        changed = copy.deepcopy(contract)
        changed["binding"][field] = value
        with pytest.raises(ValueError):
            review_contract_literal(changed)


def test_legacy_header_absence_or_drift_does_not_gate_actor_stream() -> None:
    arm = _arm("pool_matched_candidate0")
    expected = _bind(arm)
    assert expected == _review_bind(arm)
    assert expected["candidate0_special_case_used"] is False
    assert expected["legacy_supplementary_header_gate_used"] is False
    del arm["legacy_header"]
    assert _bind(arm) == expected


@pytest.mark.parametrize("arm_name", ["pool_matched_candidate0", "Static14D", "Scene14D"])
def test_three_arms_use_one_actor_binding_rule(arm_name: str) -> None:
    arm = _arm(arm_name)
    producer = _bind(arm)
    reviewer = _review_bind(arm)
    assert producer == reviewer
    assert producer["actor_count_per_tick"] == [1] * 64


@pytest.mark.parametrize(
    "mutation",
    (
        lambda arm: arm["ticks"][0]["_safety_record"]["actors"][0].pop(
            "velocity_xy_mps"
        ),
        lambda arm: arm["ticks"][0]["_safety_record"]["actors"][0].__setitem__(
            "heading_rad", float("nan")
        ),
        lambda arm: arm["ticks"][0]["_safety_record"]["actors"][0].__setitem__(
            "length_m", float("inf")
        ),
        lambda arm: arm["ticks"][0]["_safety_record"]["actors"][0].__setitem__(
            "position_xy", [1.0, 2.0, 3.0]
        ),
        lambda arm: arm["ticks"][0].__setitem__("tick_index", 9),
    ),
)
def test_actor_field_nan_inf_dimension_and_tick_attacks_fail(mutation) -> None:
    arm = _arm("Static14D")
    mutation(arm)
    with pytest.raises(ValueError):
        _bind(arm)
    with pytest.raises(ValueError):
        _review_bind(arm)


def test_wrong_arm_and_execution_root_bindings_fail() -> None:
    arm = _arm("Scene14D")
    with pytest.raises(ValueError):
        validate_sealed_actor_binding(
            arm,
            execution_root_sha256="0" * 64,
            cluster_root_sha256=CLUSTER_ROOT,
            cluster_index=0,
            expected_arm="Scene14D",
        )
    with pytest.raises(ValueError):
        validate_sealed_actor_binding(
            arm,
            execution_root_sha256=EXECUTION_ROOT_SHA256,
            cluster_root_sha256=CLUSTER_ROOT,
            cluster_index=0,
            expected_arm="Static14D",
        )


def test_actor_binding_reseal_does_not_hide_semantic_mutation() -> None:
    arm = _arm("Static14D")
    original = _bind(arm)
    arm["ticks"][0]["_safety_record"]["actors"][0]["width_m"] = 2.1
    mutated = _bind(arm)
    reviewed = _review_bind(arm)
    assert mutated == reviewed
    assert mutated["binding_sha256"] != original["binding_sha256"]
