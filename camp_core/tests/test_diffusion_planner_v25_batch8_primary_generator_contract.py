from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_batch8_primary_generator_contract as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_batch8_primary_generator_contract_review as reviewer,
)


ROOT = Path(__file__).resolve().parents[2]


def _dirs() -> dict[str, str]:
    return {key: f"/tmp/{key}" for key in producer.EXACT_DIR_KEYS}


def _sources() -> dict[str, str]:
    return {key: f"{index + 1:x}".zfill(64) for index, key in enumerate(producer.SOURCE_KEYS)}


def _contract() -> dict:
    return producer.contract_amendment(
        implementation_head="a" * 40,
        exact_dirs=_dirs(),
        source_sha256=_sources(),
    )


def _review(value: dict) -> dict:
    return reviewer.independent_literal_review(
        value,
        expected_implementation_head="a" * 40,
        expected_exact_dirs=_dirs(),
        expected_source_sha256=_sources(),
    )


def test_authority_is_canonical_and_supersedes_model_execution() -> None:
    authority = json.loads(producer.HIGH_AUTHORITY_JSON)
    assert (
        json.dumps(
            authority,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        == producer.HIGH_AUTHORITY_JSON
    )
    assert (
        hashlib.sha256(producer.HIGH_AUTHORITY_JSON.encode("ascii")).hexdigest()
        == producer.HIGH_AUTHORITY_SHA256
    )
    assert authority["superseded_authority_model_execution_allowed"] is False
    assert authority["amendment_new_model_pool_selector_call_count"] == 0


def test_contract_passes_producer_and_independent_literal_review() -> None:
    contract = _contract()
    assert producer.validate_contract_amendment(contract) == contract
    reviewed = _review(contract)
    assert reviewed["status"] == "passed_independent_literal_contract_review"
    assert reviewed["producer_oracle_imported"] is False


def test_prefrozen_latent_policy_is_batch8_and_unique() -> None:
    receipt = producer.latent_policy_receipt(61000)
    assert receipt["shape"] == [8, 321, 81, 4]
    assert receipt["dtype"] == "<f4"
    assert receipt["row0_all_zero"] is True
    assert receipt["rows1_7_draw_shape"] == [7, 321, 81, 4]
    assert receipt["unique_row_sha256_count"] == 8


def test_single_rhs_broadcast_regression_is_detected() -> None:
    rng = np.random.Generator(np.random.PCG64(61000))
    latent = np.zeros((8, 321, 81, 4), dtype=np.float32)
    latent[1:] = rng.standard_normal(latent.shape[1:]).astype(np.float32)
    rows = [hashlib.sha256(row.tobytes()).hexdigest() for row in latent]
    assert len(set(rows)) == 2
    assert producer.latent_policy_receipt(61000)["unique_row_sha256_count"] == 8


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("primary_generator_contract", "formal_model_invocation_count_per_pool"), 8),
        (("primary_generator_contract", "agent_as_ego_batch"), True),
        (("primary_generator_contract", "operational_batch_size_1_already_has_k8"), True),
        (("pool_binding_contract", "candidate0_rule"), "candidate_tensor_row1"),
        (("pool_binding_contract", "candidate_tensor_immutable_after_freeze"), False),
        (("latency_contract", "common_pool_generation_cost_included_for_all_three_arms"), False),
        (("latency_contract", "operational_batch1_may_be_called_pool_baseline"), True),
        (("decision_topology", "claim_authorized"), True),
    ],
)
def test_semantic_mutations_fail_both_oracles(
    path: tuple[str, ...], value: object
) -> None:
    contract = _contract()
    cursor = contract
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(ValueError):
        producer.validate_contract_amendment(contract)
    with pytest.raises(ValueError):
        _review(contract)


def test_sequential_cannot_reenter_any_gating_role() -> None:
    for field, value in (
        ("contributes_thresholds", True),
        ("contributes_denominator", True),
        ("may_pass_or_block_primary_generator", True),
        ("may_contribute_primary_latency", True),
    ):
        contract = _contract()
        contract["sequential_legacy_contract"][field] = value
        with pytest.raises(ValueError):
            producer.validate_contract_amendment(contract)
        with pytest.raises(ValueError):
            _review(contract)


def test_post_pool_call_topology_is_exact_and_zero_only() -> None:
    contract = _contract()
    fields = contract["pool_binding_contract"][
        "post_pool_required_zero_call_fields"
    ]
    assert fields == list(producer.POST_POOL_ZERO_CALL_FIELDS)
    contract["pool_binding_contract"]["post_pool_required_zero_call_fields"] = fields[:-1]
    with pytest.raises(ValueError):
        producer.validate_contract_amendment(contract)
    with pytest.raises(ValueError):
        _review(contract)


def test_run_counter_or_unknown_field_fails_closed() -> None:
    contract = _contract()
    contract["run_counters"]["model"] = 1
    with pytest.raises(ValueError):
        producer.validate_contract_amendment(contract)
    with pytest.raises(ValueError):
        _review(contract)
    contract = _contract()
    contract["unknown"] = True
    with pytest.raises(ValueError):
        producer.validate_contract_amendment(contract)
    with pytest.raises(ValueError):
        _review(contract)


def test_source_or_exact_dir_binding_drift_fails_closed() -> None:
    contract = _contract()
    contract["implementation"]["source_sha256"]["producer"] = "f" * 64
    with pytest.raises(ValueError):
        _review(contract)
    contract = _contract()
    contract["implementation"]["exact_dirs"]["contract"] = "/tmp/other"
    with pytest.raises(ValueError):
        _review(contract)


def test_reviewer_does_not_import_producer_or_selector_or_fairness_oracle() -> None:
    source = (
        ROOT
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_batch8_primary_generator_contract_review.py"
    ).read_text(encoding="utf-8")
    assert "diffusion_planner_v25_batch8_primary_generator_contract import" not in source
    assert "diffusion_planner_v25_target_architecture import" not in source
    assert "diffusion_planner_v25_fair_nonholdout import" not in source
    assert "selector" not in "\n".join(
        line for line in source.splitlines() if line.startswith("from ")
    )


def test_old_sequential_finding_is_preserved_but_not_decisive() -> None:
    contract = _contract()
    sequential = contract["sequential_legacy_contract"]
    assert sequential["known_rows1_7_repeated_finding_preserved"] is True
    assert sequential["scope"] == "legacy_non_gating_diagnostic_reference_only"
    assert set(sequential["excluded_from"]) == set(producer.SEQUENTIAL_EXCLUSIONS)
    assert contract["decision_topology"]["runtime_qualification_status"] == (
        "not_run_not_authorized"
    )
