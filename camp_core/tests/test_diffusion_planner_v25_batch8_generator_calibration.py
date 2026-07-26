from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_batch8_generator_calibration as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_batch8_generator_calibration_review as reviewer,
)


def _sources() -> dict[str, str]:
    return {
        key: hashlib.sha256(key.encode("ascii")).hexdigest()
        for key in {
            "producer_module",
            "reviewer_module",
            "freeze_script",
            "contract_review_script",
            "preflight_script",
            "preflight_review_script",
            "raw_script",
            "raw_review_script",
            "threshold_script",
            "threshold_review_script",
            "tests",
        }
    }


def _contract() -> dict:
    return producer.contract(
        implementation_head="1" * 40,
        source_sha256=_sources(),
    )


def test_authority_and_state_manifest_are_exact() -> None:
    assert producer.AUTHORITY_SHA256 == (
        "eba03c38f8eb6272c9cc31de464b88752a94e622ac352ffe349c70726bbe4f77"
    )
    assert producer.sha256_json(producer.source_specs()) == (
        "569718077a1c6c7f5193074ba86e646da4a3a40a2fdc573c7bfa51f3cfaa722f"
    )
    assert reviewer.sha256_json(reviewer.source_specs()) == producer.SOURCE_SPEC_MANIFEST_SHA256


def test_contract_and_independent_literal_review_pass() -> None:
    value = producer.validate_contract(_contract())
    result = reviewer.review_contract(value)
    assert result["status"] == "PASS"
    assert result["run_count"] == 320
    assert result["pair_count"] == 640
    assert result["selector_or_effect_endpoint_count"] == 0


@pytest.mark.parametrize(
    "path,value",
    [
        (("generator", "formal_model_invocations_per_run"), 8),
        (("generator", "agent_as_ego_batch"), True),
        (("generator", "sequential_model_call_count"), 1),
        (("generator", "selector_call_count"), 1),
        (("denominator", "planned_run_count"), 640),
        (("denominator", "pair_receipt_count"), 1600),
        (("run_and_claim_boundary", "safetycost_or_old_ni_endpoint_count"), 1),
        (("run_and_claim_boundary", "claim_authorized"), True),
    ],
)
def test_semantic_mutations_fail_even_when_rehashed(path, value) -> None:
    mutated = deepcopy(_contract())
    mutated[path[0]][path[1]] = value
    payload = dict(mutated)
    payload.pop("contract_payload_sha256")
    mutated["contract_payload_sha256"] = producer.sha256_json(payload)
    with pytest.raises(ValueError):
        reviewer.review_contract(mutated)


def test_endpoint_registry_exact_and_generator_only() -> None:
    assert producer.endpoint_registry() == reviewer.endpoint_registry()
    assert len(producer.endpoint_registry()) == 6
    assert all(
        row["selector_or_effect_endpoint"] is False
        and not row["endpoint_id"].startswith(("safetycost", "atom", "score"))
        for row in producer.endpoint_registry()
    )


def test_one_canonical_latent_is_deterministic_finite_unique_and_repeat_free() -> None:
    state_sha = producer.source_specs()[0]["state_spec_sha256"]
    clone_key = "a" * 64
    left = producer.latent_tensor(clone_key)
    right = reviewer.latent(clone_key)
    assert np.array_equal(left, right)
    summary = producer.tensor_summary(left)
    assert summary["shape"] == [8, 321, 81, 4]
    assert summary["dtype"] == "<f4"
    assert summary["nonfinite_count"] == 0
    assert summary["unique_row_sha256_count"] == 8
    assert summary["duplicate_groups"] == []
    assert np.count_nonzero(left[0]) == 0
    reviewer.review_latent_manifest(
        producer.latent_manifest(state_sha, clone_key), state_sha, clone_key
    )
    assert "repeat_index" not in producer.latent_manifest(state_sha, clone_key)


def test_latent_manifest_mutations_fail_closed() -> None:
    state_sha = producer.source_specs()[0]["state_spec_sha256"]
    clone_key = "b" * 64
    value = producer.latent_manifest(state_sha, clone_key)
    for key, replacement in (
        ("unique_row_sha256_count", 2),
        ("duplicate_groups", [[1, 2, 3, 4, 5, 6, 7]]),
        ("tensor_sha256", "0" * 64),
        ("row_sha256", list(reversed(value["row_sha256"]))),
        ("seed", value["seed"] + 1),
    ):
        mutated = deepcopy(value)
        mutated[key] = replacement
        payload = dict(mutated)
        payload.pop("manifest_sha256")
        mutated["manifest_sha256"] = producer.sha256_json(payload)
        with pytest.raises(ValueError):
            reviewer.review_latent_manifest(mutated, state_sha, clone_key)


def test_repeat_index_cannot_enter_canonical_seed_or_manifest() -> None:
    clone_key = "c" * 64
    seed = producer.canonical_latent_seed(clone_key)
    assert seed == reviewer.canonical_seed(clone_key)
    source = Path(producer.__file__).read_text(encoding="utf-8")
    seed_body = source.split("def canonical_latent_seed", 1)[1].split(
        "\ndef latent_tensor", 1
    )[0]
    assert "repeat_index" not in seed_body
    value = _contract()["latent_policy"]
    assert "repeat_index" in value["forbidden_seed_fields"]
    assert value["same_state_five_repeat_latent_tensor_sha_cardinality"] == 1


def _expansion() -> list[dict]:
    rows = []
    for state in range(64):
        state_sha = hashlib.sha256(f"state:{state}".encode()).hexdigest()
        input_sha = hashlib.sha256(f"input:{state}".encode()).hexdigest()
        latent_sha = hashlib.sha256(f"latent:{state}".encode()).hexdigest()
        record_sha = hashlib.sha256(f"record:{state}".encode()).hexdigest()
        clone_sha = hashlib.sha256(f"clone:{state}".encode()).hexdigest()
        for repeat in range(5):
            rows.append(
                {
                    "state_index": state,
                    "repeat_index": repeat,
                    "input_npz_sha256": input_sha,
                    "canonical_record_sha256": record_sha,
                    "canonical_state_clone_key_sha256": clone_sha,
                    "latent_manifest": {"tensor_sha256": latent_sha},
                    "state_spec_sha256": state_sha,
                }
            )
    return rows


def test_canonical_expansion_requires_same_input_and_latent_for_five_repeats() -> None:
    value = _expansion()
    producer.validate_canonical_expansion(value)
    reviewer.review_canonical_expansion(value)
    for field in (
        "input_npz_sha256",
        "canonical_record_sha256",
        "canonical_state_clone_key_sha256",
    ):
        mutated = deepcopy(value)
        mutated[1][field] = "f" * 64
        with pytest.raises(ValueError):
            producer.validate_canonical_expansion(mutated)
        with pytest.raises(ValueError):
            reviewer.review_canonical_expansion(mutated)
    mutated = deepcopy(value)
    mutated[1]["latent_manifest"]["tensor_sha256"] = "e" * 64
    with pytest.raises(ValueError):
        producer.validate_canonical_expansion(mutated)
    with pytest.raises(ValueError):
        reviewer.review_canonical_expansion(mutated)


def test_pair_errors_independent_rebuild() -> None:
    rng = np.random.default_rng(9)
    c0 = rng.normal(size=(8, 80, 4)).astype("<f4")
    c1 = c0.copy()
    c1[..., 0] += 0.25
    c1[..., 2] += np.float32(2 * np.pi - 0.1)
    n0 = rng.normal(size=(8, 32, 80, 4)).astype("<f4")
    n1 = n0.copy()
    n1[..., 1] += 0.5
    assert producer.pair_errors(c0, n0, c1, n1) == reviewer.pair_errors(
        c0, n0, c1, n1
    )


def test_pair_error_shape_nonfinite_and_dtype_fail_closed() -> None:
    c = np.zeros((8, 80, 4), dtype="<f4")
    n = np.zeros((8, 32, 80, 4), dtype="<f4")
    with pytest.raises(ValueError):
        producer.pair_errors(c.astype("<f8"), n, c, n)
    broken = c.copy()
    broken[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        producer.pair_errors(broken, n, c, n)
    with pytest.raises(ValueError):
        reviewer.pair_errors(c[:, :-1], n, c, n)


def test_state_q99_and_bootstrap_match_independent_oracle() -> None:
    pairs = np.linspace(0.0, 0.9, 10)
    assert producer.state_q99_higher(pairs) == 0.9
    assert reviewer.state_q99(pairs) == 0.9
    states = np.linspace(0.0, 6.3, 64)
    left = producer.bootstrap_ucb(states, resolution_floor=1e-4)
    right = reviewer.bootstrap(states, 1e-4)
    assert left == right


def test_bootstrap_equality_and_resolution_floor() -> None:
    result, ucb, _ = producer.bootstrap_ucb(
        np.zeros(64), resolution_floor=1e-4
    )
    assert ucb == 0.0
    assert result == 1e-4
    assert result <= result


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, -1.0])
def test_numeric_nonfinite_and_negative_fail_closed(bad: float) -> None:
    values = np.zeros(10)
    values[0] = bad
    with pytest.raises(ValueError):
        producer.state_q99_higher(values)
    with pytest.raises(ValueError):
        reviewer.state_q99(values)


def test_typed_missing_never_converts_to_zero() -> None:
    missing = producer.typed_missing("candidate_nonfinite")
    assert missing == {
        "status": "evidence_missing",
        "value": None,
        "reason": "candidate_nonfinite",
    }
    assert producer.validate_typed_scalar(missing) == missing
    with pytest.raises(ValueError):
        producer.validate_typed_scalar(
            {"status": "evidence_missing", "value": 0.0, "reason": "candidate_nonfinite"}
        )
    for bad in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError):
            producer.typed_value(bad)


def test_canonical_json_rejects_nan_inf_and_unknown_typed_reason() -> None:
    for value in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError):
            producer.canonical_bytes({"value": value})
    with pytest.raises(ValueError):
        producer.typed_missing("unknown")


def test_exact_directories_and_no_selector_authority() -> None:
    assert set(producer.EXACT_DIRS) == {
        "contract",
        "contract_review",
        "focused",
        "preflight",
        "preflight_review",
        "raw",
        "raw_review",
        "threshold",
        "threshold_review",
        "final_docs",
    }
    assert len(set(producer.EXACT_DIRS.values())) == 10
    value = _contract()
    assert value["generator"]["selector_call_count"] == 0
    assert value["run_and_claim_boundary"]["training_support_authorized"] is False
    assert value["run_and_claim_boundary"]["outcome_read_authorized"] is False


def test_reviewer_does_not_import_producer_module() -> None:
    source = Path(reviewer.__file__).read_text(encoding="utf-8")
    forbidden = (
        "import diffusion_planner_v25_batch8_generator_calibration as",
        "from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration import",
    )
    assert not any(item in source for item in forbidden)
