from __future__ import annotations

from copy import deepcopy

import pytest

from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract import (
    fair_pool_adaptation_contract,
    sha256_json,
    validate_fair_pool_adaptation_contract,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_review import (
    review_contract_literal,
)


def _rehash(value: dict[str, object]) -> dict[str, object]:
    value = deepcopy(value)
    value.pop("contract_payload_sha256", None)
    value["contract_payload_sha256"] = sha256_json(value)
    return value


def _mutated(path: tuple[object, ...], replacement: object) -> dict[str, object]:
    value: object = deepcopy(fair_pool_adaptation_contract())
    cursor = value
    for key in path[:-1]:
        cursor = cursor[key]  # type: ignore[index]
    cursor[path[-1]] = replacement  # type: ignore[index]
    return _rehash(value)  # type: ignore[arg-type]


def test_contract_and_independent_literal_review_pass() -> None:
    contract = fair_pool_adaptation_contract()
    assert validate_fair_pool_adaptation_contract(contract) == contract
    result = review_contract_literal(contract)
    assert result["status"] == "passed_independent_literal_contract_review"
    assert result["calibration_state_count"] == 64
    assert result["validation_state_count"] == 64


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("threshold_generation", "quantile"), 0.95),
        (
            ("threshold_generation", "confidence_method"),
            "normal_approximation",
        ),
        (("threshold_generation", "confidence_level"), 0.9),
        (
            (
                "threshold_generation",
                "resolution_floors",
                "trajectory_position_m",
            ),
            0.01,
        ),
        (
            (
                "threshold_generation",
                "validation_exceedance",
                "maximum_observed_rate",
            ),
            0.1,
        ),
        (
            ("threshold_generation", "minimum_calibration_state_count"),
            16,
        ),
        (
            ("manifests", "state_count_per_split"),
            16,
        ),
        (
            (
                "manifests",
                "development_calibration",
                0,
                "split",
            ),
            "independent_validation",
        ),
        (
            ("repeat_design", "within_mode_repeat_count_per_state"),
            3,
        ),
        (
            (
                "authority",
                "atom_scale_source",
                "sha256",
            ),
            "0" * 64,
        ),
        (
            (
                "authority",
                "atom_scale_source",
                "index",
                0,
                "index",
            ),
            1,
        ),
        (
            (
                "threshold_generation",
                "score_and_margin",
                "near_tie_comparison",
            ),
            "margin < near_tie_threshold",
        ),
        (
            (
                "threshold_generation",
                "score_and_margin",
                "selected_index_tie_break",
            ),
            "largest_eligible_row_index",
        ),
        (
            (
                "threshold_generation",
                "score_and_margin",
                "rank",
            ),
            "kendall_tau",
        ),
        (
            (
                "functional_action_gate",
                "action_equivalence",
                "position_error",
            ),
            "max_t_l2_xy <= 0.5_m",
        ),
        (
            ("functional_action_gate", "hard_fail"),
            ["mask_or_eligibility_changed"],
        ),
        (
            ("validation_topology", "pass_boolean"),
            "cross_mode_all_endpoints_pass",
        ),
        (
            ("validation_topology", "benefit_claim_forbidden"),
            False,
        ),
        (
            ("claim_and_run_boundary", "acquisition_authorized"),
            True,
        ),
        (
            ("claim_and_run_boundary", "pool_run_count"),
            1,
        ),
    ],
)
def test_adversarial_contract_mutations_fail_both_oracles(
    path: tuple[object, ...], replacement: object
) -> None:
    candidate = _mutated(path, replacement)
    with pytest.raises(ValueError):
        validate_fair_pool_adaptation_contract(candidate)
    with pytest.raises(ValueError):
        review_contract_literal(candidate)


def test_unknown_field_fails_closed_even_when_payload_rehashed() -> None:
    candidate = fair_pool_adaptation_contract()
    candidate["unknown_posthoc_authority"] = True
    candidate = _rehash(candidate)
    with pytest.raises(ValueError):
        validate_fair_pool_adaptation_contract(candidate)
    with pytest.raises(ValueError):
        review_contract_literal(candidate)


def test_manifests_are_exact_and_zero_overlap_by_spec_sha() -> None:
    contract = fair_pool_adaptation_contract()
    manifests = contract["manifests"]
    calibration = manifests["development_calibration"]
    validation = manifests["independent_validation"]
    assert len(calibration) == len(validation) == 64
    assert {x["state_spec_sha256"] for x in calibration}.isdisjoint(
        {x["state_spec_sha256"] for x in validation}
    )
    assert {x["source_state_ordinal"] for x in calibration} == set(range(64))
    assert {x["source_state_ordinal"] for x in validation} == set(
        range(64, 128)
    )


def test_zero_or_nonfinite_training_scale_fails_closed() -> None:
    for replacement in (0.0,):
        candidate = fair_pool_adaptation_contract()
        candidate["authority"]["atom_scale_source"]["index"][0][
            "scale"
        ] = replacement
        candidate["threshold_generation"]["atom_scale_binding"]["index"][0][
            "scale"
        ] = replacement
        candidate = _rehash(candidate)
        with pytest.raises(ValueError):
            validate_fair_pool_adaptation_contract(candidate)
        with pytest.raises((ValueError, TypeError)):
            review_contract_literal(candidate)
    nonfinite = fair_pool_adaptation_contract()
    nonfinite["authority"]["atom_scale_source"]["index"][0]["scale"] = float(
        "inf"
    )
    with pytest.raises(ValueError):
        _rehash(nonfinite)
