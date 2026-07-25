from __future__ import annotations

from copy import deepcopy

import pytest

from camp_core.integrations.diffusion_planner_v25_fair_nonholdout import (
    fair_nonholdout_contract,
    validate_fair_nonholdout_contract,
    validate_zero_call_receipt,
)
from camp_core.integrations.diffusion_planner_v25_fair_nonholdout_review import (
    review_contract_literal,
)


def test_contract_and_independent_literal_review_pass() -> None:
    value = fair_nonholdout_contract()
    assert validate_fair_nonholdout_contract(value) == value
    assert review_contract_literal(value) == value


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("generator", "name"), "operational_default_k8"),
        (("generator", "model_invocations_per_pool"), 8),
        (("generator", "agent_as_ego_axis"), True),
        (
            ("source_authority", "continuation_ledger_sha256"),
            "0" * 64,
        ),
        (
            ("source_authority", "immutable_roots"),
            {},
        ),
        (("state_matched_selector_replay", "state_count"), 1),
        (
            ("state_matched_selector_replay", "pool_generated_once_per_state_for_three_selectors"),
            False,
        ),
        (
            ("pool_distribution_adaptation_audit", "trajectory_atol"),
            1e-3,
        ),
        (
            ("pool_distribution_adaptation_audit", "single_state_generalization_allowed"),
            True,
        ),
        (("compute_matched_closed_loop", "planned_tick_denominator"), 191),
        (
            ("compute_matched_closed_loop", "post_divergence_cross_arm_tensor_identity_claimed"),
            True,
        ),
        (("latency_accounting", "baseline_includes_pool_generation"), False),
        (("claim_boundary", "fresh_authorized"), True),
        (("claim_boundary", "confirmatory_effect_claim_authorized"), True),
    ],
)
def test_contract_drift_fails_both_oracles(
    path: tuple[str, str], value: object
) -> None:
    candidate = deepcopy(fair_nonholdout_contract())
    candidate[path[0]][path[1]] = value
    with pytest.raises(ValueError):
        validate_fair_nonholdout_contract(candidate)
    with pytest.raises(ValueError):
        review_contract_literal(candidate)


def _zero_call_receipt() -> dict[str, object]:
    return {
        "pool_id": "1" * 64,
        "candidate_tensor_sha256_before": "2" * 64,
        "candidate_tensor_sha256_after": "2" * 64,
        "input_sha256": "3" * 64,
        "model_sha256": "4" * 64,
        "checkpoint_sha256": "5" * 64,
        "forward_invocation_id": "6" * 64,
        "dp_or_model_calls_after_pool": 0,
        "latent_replacements_after_pool": 0,
        "candidate_generations_after_pool": 0,
    }


def test_zero_call_receipt_passes() -> None:
    receipt = _zero_call_receipt()
    assert validate_zero_call_receipt(receipt) == receipt


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_tensor_sha256_after", "7" * 64),
        ("dp_or_model_calls_after_pool", 1),
        ("latent_replacements_after_pool", 1),
        ("candidate_generations_after_pool", 1),
    ],
)
def test_zero_call_receipt_fails_closed(field: str, value: object) -> None:
    receipt = _zero_call_receipt()
    receipt[field] = value
    with pytest.raises(ValueError):
        validate_zero_call_receipt(receipt)


def test_unknown_fields_fail_closed() -> None:
    contract = fair_nonholdout_contract()
    contract["unknown"] = True
    with pytest.raises(ValueError):
        validate_fair_nonholdout_contract(contract)
    with pytest.raises(ValueError):
        review_contract_literal(contract)

    receipt = _zero_call_receipt()
    receipt["unknown"] = True
    with pytest.raises(ValueError):
        validate_zero_call_receipt(receipt)
