from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_batch8_calibration_contract as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_batch8_calibration_contract_review as reviewer,
)


ROOT = Path(__file__).resolve().parents[2]


def _dirs() -> dict[str, str]:
    return {key: f"/tmp/{key}" for key in producer.EXACT_DIR_KEYS}


def _sources() -> dict[str, str]:
    return {
        key: f"{index + 1:x}".zfill(64)
        for index, key in enumerate(producer.SOURCE_KEYS)
    }


def _contract() -> dict:
    return producer.contract_design(
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


def _hard_receipt() -> dict:
    tensor_sha = "1" * 64
    return {
        "formal_model_invocation_count": 1,
        "source_ego_state_count": 1,
        "expanded_batch_size": 8,
        "agent_as_ego_batch": False,
        "latent_finite": True,
        "latent_unique_count": 8,
        "candidate_finite": True,
        "candidate_unique_count": 8,
        "neighbor_finite": True,
        "fingerprints_exact": True,
        "candidate_tensor_pre_sha256": tensor_sha,
        "candidate_tensor_post_sha256": tensor_sha,
        "post_pool_calls": {
            key: 0 for key in producer.POST_POOL_ZERO_FIELDS
        },
        "static14d": {
            "mask_nonempty": True,
            "selected_index": 0,
            "selected_action_sha256": "2" * 64,
            "pool_id": "pool:static-test",
            "candidate_tensor_sha256": tensor_sha,
        },
        "scene14d": {
            "mask_nonempty": True,
            "selected_index": 1,
            "selected_action_sha256": "3" * 64,
            "pool_id": "pool:scene-test",
            "candidate_tensor_sha256": tensor_sha,
        },
    }


def test_authority_is_canonical_and_design_only() -> None:
    decoded = json.loads(producer.HIGH_AUTHORITY_JSON)
    assert (
        json.dumps(
            decoded,
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
    assert decoded["actual_calibration_acquisition_authorized"] is False
    assert decoded["threshold_materialization_authorized"] is False


def test_contract_passes_both_oracles_without_runs() -> None:
    contract = _contract()
    assert producer.validate_contract_design(contract) == contract
    reviewed = _review(contract)
    assert reviewed["status"] == "passed_independent_literal_contract_review"
    assert reviewed["producer_threshold_endpoint_decision_oracle_imported"] is False
    assert all(value == 0 for value in contract["run_counters"].values())


def test_topology_is_exactly_320_runs_640_pairs_and_640_selector_receipts() -> None:
    contract = _contract()
    topology = contract["calibration_topology"]
    assert len(producer.planned_run_ids()) == 64 * 5 == 320
    assert len(producer.planned_pair_ids()) == 64 * 10 == 640
    assert topology["planned_model_invocation_count"] == 320
    assert topology["planned_pair_receipt_count"] == 640
    assert topology["planned_static_scene_selector_receipt_count"] == 640
    assert topology["statistical_unit"] == "state"
    assert topology["row_tick_as_independent_unit_allowed"] is False


def test_registry_is_exact_old_within_22_without_cross_or_sequential() -> None:
    registry = producer.endpoint_registry()
    ids = [row["endpoint_id"] for row in registry]
    assert len(ids) == len(set(ids)) == 22
    assert ids[-2:] == [
        "score.static14d.abs_delta",
        "score.scene14d.abs_delta",
    ]
    assert all(row["phase"] == "batch8_within" for row in registry)
    assert all(row["mode"] == "single_invocation_batch8" for row in registry)
    assert not any(
        token in endpoint
        for endpoint in ids
        for token in ("margin_ratio", "rank_error", "relative_within", "cross")
    )


def test_q99_and_bootstrap_are_reproducible_and_independent() -> None:
    pairs = np.arange(10, dtype=np.float64)
    states = np.linspace(0.0, 1.0, 64, dtype=np.float64)
    assert producer.empirical_q99_higher(pairs) == 9.0
    assert reviewer.empirical_q99_higher(pairs) == 9.0
    assert producer.bootstrap_ucb(states, resolution_floor=1e-4) == (
        reviewer.bootstrap_ucb(states, 1e-4)
    )
    with pytest.raises(ValueError):
        producer.empirical_q99_higher(pairs[:9])
    with pytest.raises(ValueError):
        producer.bootstrap_ucb(states[:63], resolution_floor=1e-4)


def test_training_support_is_prespecified_missing_not_calibration_derived() -> None:
    audit = _contract()["training_support_audit"]
    assert audit["current_status"] == (
        "evidence_missing_prespecified_training_support_reference"
    )
    assert audit["current_authority_binds_only_atom_normalization_scales"] is True
    assert audit["calibration_may_set_training_support_thresholds"] is False
    assert audit["thresholds_materialized"] is False
    assert audit["no_retraining_conclusion_authorized"] is False
    future = audit["future_reference_schema"]
    assert future["source"] == "sealed_training_artifacts_only"
    assert future["calibration_or_validation_values_allowed"] is False
    assert len(future["continuous_fields"]) == 20
    assert future["multiplicity"] == (
        "all_20_prespecified_fields_must_pass_no_weighted_total"
    )


def test_valid_hard_receipt_has_no_failure() -> None:
    assert producer.hard_gate_failures(_hard_receipt()) == []


@pytest.mark.parametrize(
    ("path", "value", "expected"),
    [
        (("formal_model_invocation_count",), 8, "single_model_call_same_ego_B8"),
        (("source_ego_state_count",), 8, "single_model_call_same_ego_B8"),
        (("agent_as_ego_batch",), True, "single_model_call_same_ego_B8"),
        (("latent_unique_count",), 7, "latent_finite_unique8"),
        (("candidate_finite",), False, "candidate_neighbor_finite"),
        (("candidate_unique_count",), 7, "candidate_unique8"),
        (("fingerprints_exact",), False, "fingerprints_exact"),
        (
            ("candidate_tensor_post_sha256",),
            "f" * 64,
            "candidate_tensor_immutable",
        ),
        (
            ("post_pool_calls", "model_call_count"),
            1,
            "post_pool_model_dp_latent_generation_calls_zero",
        ),
        (
            ("static14d", "mask_nonempty"),
            False,
            "static_scene_masks_nonempty_and_selected_action_bound",
        ),
    ],
)
def test_hard_gate_adversarial_receipts_fail_closed(
    path: tuple[str, ...], value: object, expected: str
) -> None:
    receipt = _hard_receipt()
    cursor = receipt
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    assert expected in producer.hard_gate_failures(receipt)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("calibration_topology", "planned_model_invocation_count"), 640),
        (("calibration_topology", "planned_pair_receipt_count"), 1600),
        (("calibration_topology", "statistical_unit"), "row"),
        (("calibration_topology", "drop_replace_or_complete_case_allowed"), True),
        (("numeric_contract", "within_numeric_endpoint_count"), 73),
        (("numeric_contract", "cross_mode_numeric_endpoint_count"), 22),
        (("threshold_contract", "materialization_authorized"), True),
        (
            ("training_support_audit", "calibration_may_set_training_support_thresholds"),
            True,
        ),
        (
            ("decision_semantics", "no_retraining_conclusion_authorized"),
            True,
        ),
        (("decision_semantics", "weighted_total"), True),
        (("sequential_legacy", "formal_denominator_count"), 320),
        (("sequential_legacy", "numeric_key_count"), 22),
        (("run_counters", "model"), 1),
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
        producer.validate_contract_design(contract)
    with pytest.raises(ValueError):
        _review(contract)


def test_adding_cross_or_removing_endpoint_fails_both_oracles() -> None:
    contract = _contract()
    contract["numeric_contract"]["endpoint_registry"].append(
        {
            **contract["numeric_contract"]["endpoint_registry"][-1],
            "endpoint_id": "score.scene14d.margin_ratio",
        }
    )
    with pytest.raises(ValueError):
        producer.validate_contract_design(contract)
    with pytest.raises(ValueError):
        _review(contract)
    contract = _contract()
    contract["numeric_contract"]["endpoint_registry"].pop()
    with pytest.raises(ValueError):
        producer.validate_contract_design(contract)
    with pytest.raises(ValueError):
        _review(contract)


def test_training_support_threshold_mutation_or_self_materialization_fails() -> None:
    for path, value in (
        (
            ("future_reference_schema", "reference_interval", "upper"),
            "calibration_q0_995",
        ),
        (
            ("future_reference_schema", "calibration_state_coverage", "minimum_per_state"),
            0.90,
        ),
        ("thresholds_materialized", True),
    ):
        contract = _contract()
        audit = contract["training_support_audit"]
        if isinstance(path, tuple):
            cursor = audit
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
        else:
            audit[path] = value
        with pytest.raises(ValueError):
            producer.validate_contract_design(contract)
        with pytest.raises(ValueError):
            _review(contract)


def test_unknown_fields_and_source_bindings_fail_closed() -> None:
    contract = _contract()
    contract["unknown"] = True
    with pytest.raises(ValueError):
        producer.validate_contract_design(contract)
    with pytest.raises(ValueError):
        _review(contract)
    contract = _contract()
    contract["implementation"]["source_sha256"]["producer"] = "f" * 64
    with pytest.raises(ValueError):
        _review(contract)


def test_reviewer_has_no_producer_threshold_selector_or_decision_import() -> None:
    source = (
        ROOT
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_batch8_calibration_contract_review.py"
    ).read_text(encoding="utf-8")
    imports = "\n".join(
        line for line in source.splitlines() if line.startswith(("from ", "import "))
    )
    assert "batch8_calibration_contract import" not in source
    assert "fair_pool_adaptation_contract" not in imports
    assert "selector" not in imports
    assert "threshold" not in imports
    assert "decision" not in imports


def test_original_contract_is_not_mutated_by_adversarial_copy() -> None:
    contract = _contract()
    mutated = copy.deepcopy(contract)
    mutated["sequential_legacy"]["pair_receipt_count"] = 640
    assert contract["sequential_legacy"]["pair_receipt_count"] == 0
