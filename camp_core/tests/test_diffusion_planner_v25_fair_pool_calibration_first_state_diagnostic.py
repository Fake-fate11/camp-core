from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic import (
    HIGH_AUTHORITY_JSON,
    HIGH_AUTHORITY_SHA256,
    build_precondition_receipt,
    canonical_json_bytes,
    diagnostic_contract,
    enforce_compound_gate_after_receipt,
    validate_diagnostic_contract,
    validate_precondition_receipt,
    write_precondition_receipt_atomic,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic_review import (
    review_contract_literal,
    review_receipt_from_tensor_bytes,
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _arrays() -> tuple[np.ndarray, np.ndarray]:
    candidate = np.arange(8 * 80 * 4, dtype="<f4").reshape(8, 80, 4)
    neighbor = (
        np.arange(8 * 32 * 80 * 4, dtype="<f4").reshape(8, 32, 80, 4)
        / np.float32(1000.0)
    )
    return candidate, neighbor


def _bindings(
    candidate: np.ndarray | None = None,
    neighbor: np.ndarray | None = None,
) -> dict[str, object]:
    if candidate is None or neighbor is None:
        candidate, neighbor = _arrays()
    result: dict[str, object] = {
        "input_manifest_sha256": _sha("input-manifest"),
        "actual_input_tensor_bundle_sha256": _sha("input-bundle"),
        "actual_state_sha256": _sha("state"),
        "latent_tensor_sha256": _sha("latent"),
        "model_source_sha256": _sha("model"),
        "checkpoint_sha256": _sha("checkpoint"),
        "fixed_dp_head": "7" * 40,
    }
    candidate_shas = [
        hashlib.sha256(_bytes(row)).hexdigest() for row in candidate
    ]
    neighbor_shas = [
        hashlib.sha256(_bytes(row)).hexdigest() for row in neighbor
    ]
    result["forward_ids"] = [
        hashlib.sha256(
            canonical_json_bytes(
                {
                    "state_spec_id": "development_calibration:000",
                    "mode": "sequential_batch1_x8",
                    "repeat_index": 0,
                    "row_index": index,
                    "input_manifest_sha256": result["input_manifest_sha256"],
                    "actual_input_tensor_bundle_sha256": result[
                        "actual_input_tensor_bundle_sha256"
                    ],
                    "actual_state_sha256": result["actual_state_sha256"],
                    "latent_tensor_sha256": result["latent_tensor_sha256"],
                    "model_source_sha256": result["model_source_sha256"],
                    "checkpoint_sha256": result["checkpoint_sha256"],
                    "fixed_dp_head": result["fixed_dp_head"],
                    "candidate_row_sha256": candidate_shas[index],
                    "neighbor_row_sha256": neighbor_shas[index],
                }
            )
        ).hexdigest()
        for index in range(8)
    ]
    return result


def _bytes(value: np.ndarray) -> bytes:
    return np.ascontiguousarray(value).tobytes(order="C")


def _contract() -> dict[str, object]:
    return diagnostic_contract(
        implementation_head="a" * 40,
        exact_dirs={
            "contract": "/root/contract",
            "contract_review": "/root/contract_review",
            "focused": "/root/focused",
            "diagnostic": "/root/diagnostic",
            "diagnostic_review": "/root/diagnostic_review",
        },
        producer_source_sha256=_sha("producer"),
        reviewer_source_sha256=_sha("reviewer"),
    )


def test_high_authority_is_exact_canonical_bytes() -> None:
    assert (
        hashlib.sha256(HIGH_AUTHORITY_JSON.encode("ascii")).hexdigest()
        == HIGH_AUTHORITY_SHA256
    )
    authority = json.loads(HIGH_AUTHORITY_JSON)
    assert list(authority) == sorted(authority)
    assert authority["remaining_639_runs_authorized"] is False
    assert authority["receipt_must_precede_raise"] is True


def test_contract_and_independent_literal_review_pass() -> None:
    contract = _contract()
    validate_diagnostic_contract(contract)
    review = review_contract_literal(contract)
    assert review["status"] == "passed"
    assert review["producer_metric_or_model_imported"] is False


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (
            lambda candidate, neighbor: candidate.__setitem__((1, 2, 3), np.nan),
            "candidate_tensor_contains_nonfinite_value",
        ),
        (
            lambda candidate, neighbor: neighbor.__setitem__((4, 5, 6, 2), np.inf),
            "neighbor_tensor_contains_nonfinite_value",
        ),
        (
            lambda candidate, neighbor: candidate.__setitem__(1, candidate[0]),
            "candidate_row_sha256_not_unique_across_k8",
        ),
    ],
)
def test_exact_subconditions_are_rebuilt_from_tensor_bytes(
    mutator, expected: str
) -> None:
    candidate, neighbor = _arrays()
    mutator(candidate, neighbor)
    receipt = build_precondition_receipt(
        candidate=candidate, neighbor=neighbor, bindings=_bindings(candidate, neighbor)
    )
    assert receipt["compound_gate_triggered"] is True
    assert expected in receipt["resolved_subconditions"]
    validate_precondition_receipt(
        receipt,
        candidate_bytes=_bytes(candidate),
        neighbor_bytes=_bytes(neighbor),
        expected_bindings=_bindings(candidate, neighbor),
    )
    review = review_receipt_from_tensor_bytes(
        receipt,
        candidate_bytes=_bytes(candidate),
        neighbor_bytes=_bytes(neighbor),
    )
    assert expected in review["resolved_subconditions"]


def test_valid_finite_diverse_receipt_stops_before_selector() -> None:
    candidate, neighbor = _arrays()
    receipt = build_precondition_receipt(
        candidate=candidate, neighbor=neighbor, bindings=_bindings(candidate, neighbor)
    )
    assert receipt["compound_gate_triggered"] is False
    assert receipt["resolved_subconditions"] == []
    assert receipt["candidate_row_sha256_unique_cardinality"] == 8
    assert receipt["model_call_count"] == 8
    assert receipt["selector_call_count"] == 0
    assert receipt["remaining_calibration_run_count_authorized"] == 0


@pytest.mark.parametrize(
    "candidate,neighbor",
    [
        (np.zeros((7, 80, 4), dtype="<f4"), np.zeros((8, 32, 80, 4), dtype="<f4")),
        (np.zeros((8, 80, 4), dtype="<f8"), np.zeros((8, 32, 80, 4), dtype="<f4")),
        (np.zeros((8, 80, 4), dtype="<f4"), np.zeros((8, 31, 80, 4), dtype="<f4")),
        (np.zeros((8, 80, 4), dtype="<f4"), np.zeros((8, 32, 80, 4), dtype="<f8")),
    ],
)
def test_shape_and_dtype_drift_fail_closed(
    candidate: np.ndarray, neighbor: np.ndarray
) -> None:
    with pytest.raises(ValueError, match="shape/dtype"):
        build_precondition_receipt(
            candidate=candidate,
            neighbor=neighbor,
            bindings=_bindings(),
        )


def test_receipt_is_durable_before_compound_gate_raise(tmp_path: Path) -> None:
    candidate, neighbor = _arrays()
    candidate[2, 3, 1] = np.nan
    receipt = build_precondition_receipt(
        candidate=candidate, neighbor=neighbor, bindings=_bindings(candidate, neighbor)
    )
    path = tmp_path / "precondition_receipt.json"
    write_precondition_receipt_atomic(path, receipt)
    with pytest.raises(RuntimeError, match="calibration K8 invalid"):
        enforce_compound_gate_after_receipt(path, receipt)
    assert path.read_bytes() == canonical_json_bytes(receipt)


def test_missing_receipt_blocks_raise_path(tmp_path: Path) -> None:
    candidate, neighbor = _arrays()
    candidate[2, 3, 1] = np.nan
    receipt = build_precondition_receipt(
        candidate=candidate, neighbor=neighbor, bindings=_bindings(candidate, neighbor)
    )
    with pytest.raises(RuntimeError, match="not durably formed"):
        enforce_compound_gate_after_receipt(
            tmp_path / "missing_receipt.json", receipt
        )


def test_forged_receipt_resealed_against_same_tensors_blocks() -> None:
    candidate, neighbor = _arrays()
    candidate[2, 3, 1] = np.nan
    receipt = build_precondition_receipt(
        candidate=candidate, neighbor=neighbor, bindings=_bindings(candidate, neighbor)
    )
    forged = copy.deepcopy(receipt)
    forged["candidate_nonfinite_count"] = 0
    forged["candidate_nonfinite_indices"] = []
    forged["subconditions"][
        "candidate_tensor_contains_nonfinite_value"
    ] = False
    forged["compound_gate_triggered"] = False
    forged["resolved_subconditions"] = []
    payload = dict(forged)
    payload.pop("receipt_sha256")
    forged["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(payload)
    ).hexdigest()
    with pytest.raises(ValueError, match="tensor-byte preimage"):
        validate_precondition_receipt(
            forged,
            candidate_bytes=_bytes(candidate),
            neighbor_bytes=_bytes(neighbor),
            expected_bindings=_bindings(candidate, neighbor),
        )
    with pytest.raises(ValueError, match="semantic reconstruction"):
        review_receipt_from_tensor_bytes(
            forged,
            candidate_bytes=_bytes(candidate),
            neighbor_bytes=_bytes(neighbor),
        )


def test_unknown_receipt_field_and_forward_binding_drift_block() -> None:
    candidate, neighbor = _arrays()
    receipt = build_precondition_receipt(
        candidate=candidate, neighbor=neighbor, bindings=_bindings(candidate, neighbor)
    )
    unknown = copy.deepcopy(receipt)
    unknown["posthoc_override"] = True
    with pytest.raises(ValueError, match="tensor-byte preimage"):
        validate_precondition_receipt(
            unknown,
            candidate_bytes=_bytes(candidate),
            neighbor_bytes=_bytes(neighbor),
            expected_bindings=_bindings(candidate, neighbor),
        )
    duplicate_forward = _bindings(candidate, neighbor)
    duplicate_forward["forward_ids"][7] = duplicate_forward["forward_ids"][0]
    with pytest.raises(ValueError, match="forward ID"):
        build_precondition_receipt(
            candidate=candidate,
            neighbor=neighbor,
            bindings=duplicate_forward,
        )
    wrong_fixed_dp = _bindings(candidate, neighbor)
    wrong_fixed_dp["fixed_dp_head"] = _sha("not-a-git-head")
    with pytest.raises(ValueError, match="fixed-DP git HEAD"):
        build_precondition_receipt(
            candidate=candidate,
            neighbor=neighbor,
            bindings=wrong_fixed_dp,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("remaining_639_runs_authorized", True),
        ("threshold_materialization_authorized", True),
        ("validation_authorized", True),
        ("fresh_or_holdout_authorized", True),
        ("training_or_retraining_authorized", True),
    ],
)
def test_contract_prohibited_scope_mutations_block(field: str, value: object) -> None:
    contract = _contract()
    contract[field] = value
    with pytest.raises(ValueError, match="contract drifted"):
        validate_diagnostic_contract(contract)
    with pytest.raises(ValueError, match="prohibited field"):
        review_contract_literal(contract)
