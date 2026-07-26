from __future__ import annotations

import copy
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_batch8_first_state_diagnostic as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_batch8_first_state_diagnostic_review as reviewer,
)


ROOT = Path(__file__).resolve().parents[2]


def _dirs() -> dict[str, str]:
    return {key: f"/root/autodl-tmp/{key}" for key in producer.EXACT_DIR_KEYS}


def _sources() -> dict[str, str]:
    return {
        key: f"{index + 1:x}".zfill(64)
        for index, key in enumerate(producer.SOURCE_KEYS)
    }


def _contract() -> dict:
    return producer.diagnostic_contract(
        implementation_head="a" * 40,
        exact_dirs=_dirs(),
        source_sha256=_sources(),
    )


def _raw() -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray, np.ndarray]:
    latent = producer.unique_latent()
    arrays = {
        "agent": np.repeat(
            np.arange(12, dtype=np.float32).reshape(1, 3, 4), 8, axis=0
        ),
        "sampled_trajectories": latent.copy(),
    }
    candidate = np.arange(8 * 80 * 4, dtype=np.float32).reshape(8, 80, 4)
    neighbor = np.arange(8 * 32 * 80 * 4, dtype=np.float32).reshape(
        8, 32, 80, 4
    )
    return latent, arrays, candidate, neighbor


def _bindings() -> dict[str, str]:
    result = {
        key: f"{index + 1:x}".zfill(64)
        for index, key in enumerate(producer.BASE_BINDING_KEYS)
    }
    result["fixed_dp_head"] = producer.FIXED_DP_HEAD
    return result


def _receipt(
    *,
    model_calls: int = 1,
    sequential_calls: int = 0,
    selector_calls: int = 0,
) -> tuple[dict, tuple]:
    raw = _raw()
    receipt = producer.build_diagnostic_receipt(
        latent=raw[0],
        expanded_inputs=raw[1],
        candidate=raw[2],
        neighbor=raw[3],
        base_bindings=_bindings(),
        pool_generation_latency_ns=123,
        model_call_count=model_calls,
        sequential_model_call_count=sequential_calls,
        selector_call_count=selector_calls,
    )
    return receipt, raw


def test_authority_exact_and_contract_independently_reviewed() -> None:
    assert (
        hashlib.sha256(producer.HIGH_AUTHORITY_JSON.encode("ascii")).hexdigest()
        == producer.HIGH_AUTHORITY_SHA256
    )
    assert (
        json.dumps(
            json.loads(producer.HIGH_AUTHORITY_JSON),
            sort_keys=True,
            separators=(",", ":"),
        )
        == producer.HIGH_AUTHORITY_JSON
    )
    contract = producer.validate_contract(_contract())
    reviewed = reviewer.independent_contract_review(
        contract,
        implementation_head="a" * 40,
        exact_dirs=_dirs(),
        source_sha256=_sources(),
    )
    assert reviewed["status"] == "passed_independent_literal_contract_review"


def test_unique_latent_is_exact_policy() -> None:
    latent = producer.unique_latent()
    summary = producer.tensor_summary(latent)
    assert latent.shape == (8, 321, 81, 4)
    assert latent.dtype.str == "<f4"
    assert np.count_nonzero(latent[0]) == 0
    assert summary["nonfinite_count"] == 0
    assert summary["unique_row_sha256_count"] == 8
    assert producer.latent_manifest()["unique_row_sha256_count"] == 8


def test_single_rhs_broadcast_and_row_permutation_fail_policy() -> None:
    rng = np.random.Generator(np.random.PCG64(61000))
    broadcast = np.zeros(producer.LATENT_SHAPE, dtype=np.float32)
    broadcast[1:] = rng.standard_normal(broadcast.shape[1:]).astype(np.float32)
    assert producer.tensor_summary(broadcast)["unique_row_sha256_count"] == 2
    original = producer.unique_latent()
    permuted = original[[0, 2, 1, 3, 4, 5, 6, 7]]
    assert producer.tensor_summary(permuted)["tensor_sha256"] != producer.tensor_summary(
        original
    )["tensor_sha256"]


def test_valid_raw_receipt_passes_independent_byte_review() -> None:
    receipt, raw = _receipt()
    assert receipt["taxonomy"] == "batch8_pool_valid_diverse"
    reviewed = reviewer.independent_receipt_review(
        receipt=receipt,
        latent=raw[0],
        expanded_inputs=raw[1],
        candidate=raw[2],
        neighbor=raw[3],
    )
    assert reviewed["taxonomy"] == "batch8_pool_valid_diverse"
    assert reviewed["model_call_count"] == 1
    assert reviewed["sequential_model_call_count"] == 0
    assert reviewed["selector_call_count"] == 0


def test_canonical_json_roundtrip_key_order_does_not_change_receipt_semantics() -> None:
    receipt, raw = _receipt()
    roundtripped = json.loads(producer.canonical_bytes(receipt))
    assert tuple(roundtripped["base_bindings"]) != producer.BASE_BINDING_KEYS
    reviewed = reviewer.independent_receipt_review(
        receipt=roundtripped,
        latent=raw[0],
        expanded_inputs=raw[1],
        candidate=raw[2],
        neighbor=raw[3],
    )
    assert reviewed["status"] == "passed_independent_raw_byte_review"


def test_eight_calls_cannot_impersonate_single_invocation() -> None:
    receipt, raw = _receipt(model_calls=8)
    assert receipt["taxonomy"] == "output_batch_or_binding_invalid"
    reviewed = reviewer.independent_receipt_review(
        receipt=receipt,
        latent=raw[0],
        expanded_inputs=raw[1],
        candidate=raw[2],
        neighbor=raw[3],
    )
    assert reviewed["taxonomy"] == "output_batch_or_binding_invalid"


def test_agent_batch_or_nonidentical_input_is_blocked() -> None:
    latent, arrays, candidate, neighbor = _raw()
    arrays["agent"][1, 0, 0] += 1
    receipt = producer.build_diagnostic_receipt(
        latent=latent,
        expanded_inputs=arrays,
        candidate=candidate,
        neighbor=neighbor,
        base_bindings=_bindings(),
        pool_generation_latency_ns=123,
        model_call_count=1,
        sequential_model_call_count=0,
        selector_call_count=0,
    )
    assert receipt["taxonomy"] == "input_batch_not_same_ego"
    assert (
        reviewer.independent_receipt_review(
            receipt=receipt,
            latent=latent,
            expanded_inputs=arrays,
            candidate=candidate,
            neighbor=neighbor,
        )["taxonomy"]
        == "input_batch_not_same_ego"
    )


@pytest.mark.parametrize("target", ["candidate", "neighbor"])
def test_nonfinite_output_is_classified(target: str) -> None:
    latent, arrays, candidate, neighbor = _raw()
    (candidate if target == "candidate" else neighbor).flat[0] = np.nan
    receipt = producer.build_diagnostic_receipt(
        latent=latent,
        expanded_inputs=arrays,
        candidate=candidate,
        neighbor=neighbor,
        base_bindings=_bindings(),
        pool_generation_latency_ns=123,
        model_call_count=1,
        sequential_model_call_count=0,
        selector_call_count=0,
    )
    assert receipt["taxonomy"] == "candidate_or_neighbor_nonfinite"


def test_duplicate_candidate_rows_are_classified() -> None:
    latent, arrays, candidate, neighbor = _raw()
    candidate[7] = candidate[1]
    receipt = producer.build_diagnostic_receipt(
        latent=latent,
        expanded_inputs=arrays,
        candidate=candidate,
        neighbor=neighbor,
        base_bindings=_bindings(),
        pool_generation_latency_ns=123,
        model_call_count=1,
        sequential_model_call_count=0,
        selector_call_count=0,
    )
    assert receipt["taxonomy"] == "candidate_rows_not_unique"
    assert receipt["candidate_summary"]["duplicate_groups"] == [[1, 7]]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("formal_forward_id", "f" * 64),
        ("pool_id", "e" * 64),
        ("candidate0_row_sha256", "d" * 64),
        ("row0_candidate0_binding", False),
        ("selector_call_count", 1),
    ],
)
def test_resealed_binding_or_topology_mutation_fails_independent_review(
    field: str, value: object
) -> None:
    receipt, raw = _receipt()
    receipt[field] = value
    payload = dict(receipt)
    payload.pop("receipt_sha256")
    receipt["receipt_sha256"] = hashlib.sha256(
        producer.canonical_bytes(payload)
    ).hexdigest()
    with pytest.raises(ValueError):
        reviewer.independent_receipt_review(
            receipt=receipt,
            latent=raw[0],
            expanded_inputs=raw[1],
            candidate=raw[2],
            neighbor=raw[3],
        )


def test_missing_receipt_or_raw_tensor_mutation_fails_review() -> None:
    receipt, raw = _receipt()
    with pytest.raises((TypeError, ValueError)):
        reviewer.independent_receipt_review(
            receipt={},
            latent=raw[0],
            expanded_inputs=raw[1],
            candidate=raw[2],
            neighbor=raw[3],
        )
    candidate = raw[2].copy()
    candidate[0, 0, 0] += 1
    with pytest.raises(ValueError):
        reviewer.independent_receipt_review(
            receipt=receipt,
            latent=raw[0],
            expanded_inputs=raw[1],
            candidate=candidate,
            neighbor=raw[3],
        )


def test_source_mutation_and_old_manifest_reuse_fail_contract() -> None:
    contract = _contract()
    contract["source_sha256"]["diagnostic_script"] = "f" * 64
    with pytest.raises(ValueError):
        producer.validate_contract(contract)
    with pytest.raises(ValueError):
        reviewer.independent_contract_review(
            contract,
            implementation_head="a" * 40,
            exact_dirs=_dirs(),
            source_sha256=_sources(),
        )


def test_reviewer_does_not_import_producer_model_or_selector_oracle() -> None:
    source = (
        ROOT
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_batch8_first_state_diagnostic_review.py"
    ).read_text(encoding="utf-8")
    assert "diffusion_planner_v25_batch8_first_state_diagnostic import" not in source
    assert "run_diffusion_planner_camp_replay import" not in source
    assert "target_architecture import" not in source


def test_formal_diagnostic_source_has_one_unlooped_model_call_and_no_selector() -> None:
    path = (
        ROOT
        / "scripts"
        / "integrations"
        / "materialize_diffusion_planner_v25_batch8_first_state_diagnostic.py"
    )
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "model"
    ]
    assert len(calls) == 1
    cursor = calls[0]
    while cursor in parents:
        cursor = parents[cursor]
        assert not isinstance(cursor, (ast.For, ast.AsyncFor, ast.While))
    assert "select_candidate" not in source
    assert "score_candidate_pool" not in source


def test_preflight_rejects_old_instance_reuse() -> None:
    latent = producer.latent_manifest()
    base = {
        "state_spec_id": producer.STATE_SPEC_ID,
        "latent_seed": producer.LATENT_SEED,
        "manifest_sha256": "1" * 64,
        "clone_key_sha256": "2" * 64,
        "actual_state_sha256": "3" * 64,
        "actual_input_tensor_manifest": {"bundle_sha256": "4" * 64},
        "actual_latent_tensor_manifest": {"tensor_sha256": "5" * 64},
    }
    validation = copy.deepcopy(base)
    validation["state_spec_id"] = "independent_validation:000"
    validation["clone_key_sha256"] = "6" * 64
    old = {
        "status": "passed_before_first_model_pool_selector_call",
        "within_calibration_overlap_count": 0,
        "within_validation_overlap_count": 0,
        "cross_split_overlap_count": 0,
        "b4_overlap_count": 0,
        "model_pool_selector_call_count_before_receipt": 0,
        "no_drop_no_replacement": True,
        "calibration_manifests": [copy.deepcopy(base) for _ in range(64)],
        "validation_manifests": [copy.deepcopy(validation) for _ in range(64)],
        "b4_forbidden_manifest_authority": {
            "derived_inside_validator_from_exact_bytes": True,
            "derived_forbidden_clone_key_count": 100,
        },
    }
    for index, row in enumerate(old["calibration_manifests"]):
        row["state_spec_id"] = f"development_calibration:{index:03d}"
        row["clone_key_sha256"] = f"{1000 + index:064x}"
    old["calibration_manifests"][0]["state_spec_id"] = producer.STATE_SPEC_ID
    for index, row in enumerate(old["validation_manifests"]):
        row["state_spec_id"] = f"independent_validation:{index:03d}"
        row["clone_key_sha256"] = f"{2000 + index:064x}"
    receipt = producer.build_preflight_receipt(
        old_receipt=old,
        contract_root="7" * 64,
        contract_review_root="8" * 64,
    )
    assert receipt["new_manifest"]["actual_latent_tensor_manifest"] == latent
    assert receipt["old_nonholdout_instance_overlap_count"] == 0
    assert receipt["model_pool_selector_call_count_before_receipt"] == 0
    reviewed = reviewer.independent_preflight_review(
        receipt,
        old_receipt=old,
        contract_root="7" * 64,
        contract_review_root="8" * 64,
    )
    assert reviewed["status"] == "passed_independent_input_only_preflight_review"
    assert reviewed["latent_unique_row_count"] == 8


def test_preflight_resealed_latent_or_overlap_mutation_fails_review() -> None:
    base = {
        "state_spec_id": producer.STATE_SPEC_ID,
        "latent_seed": producer.LATENT_SEED,
        "manifest_sha256": "1" * 64,
        "clone_key_sha256": "2" * 64,
        "actual_state_sha256": "3" * 64,
        "actual_input_tensor_manifest": {"bundle_sha256": "4" * 64},
        "actual_latent_tensor_manifest": {"tensor_sha256": "5" * 64},
    }
    old = {
        "status": "passed_before_first_model_pool_selector_call",
        "within_calibration_overlap_count": 0,
        "within_validation_overlap_count": 0,
        "cross_split_overlap_count": 0,
        "b4_overlap_count": 0,
        "model_pool_selector_call_count_before_receipt": 0,
        "no_drop_no_replacement": True,
        "calibration_manifests": [],
        "validation_manifests": [],
        "b4_forbidden_manifest_authority": {
            "derived_inside_validator_from_exact_bytes": True,
            "derived_forbidden_clone_key_count": 100,
        },
    }
    for index in range(64):
        row = copy.deepcopy(base)
        row["state_spec_id"] = f"development_calibration:{index:03d}"
        row["clone_key_sha256"] = f"{1000 + index:064x}"
        old["calibration_manifests"].append(row)
        row = copy.deepcopy(base)
        row["state_spec_id"] = f"independent_validation:{index:03d}"
        row["clone_key_sha256"] = f"{2000 + index:064x}"
        old["validation_manifests"].append(row)
    receipt = producer.build_preflight_receipt(
        old_receipt=old,
        contract_root="7" * 64,
        contract_review_root="8" * 64,
    )
    mutated = copy.deepcopy(receipt)
    mutated["new_manifest"]["actual_latent_tensor_manifest"][
        "unique_row_sha256_count"
    ] = 7
    manifest = dict(mutated["new_manifest"])
    manifest.pop("manifest_sha256")
    mutated["new_manifest"]["manifest_sha256"] = hashlib.sha256(
        producer.canonical_bytes(manifest)
    ).hexdigest()
    payload = dict(mutated)
    payload.pop("receipt_sha256")
    mutated["receipt_sha256"] = hashlib.sha256(
        producer.canonical_bytes(payload)
    ).hexdigest()
    with pytest.raises(ValueError):
        reviewer.independent_preflight_review(
            mutated,
            old_receipt=old,
            contract_root="7" * 64,
            contract_review_root="8" * 64,
        )
