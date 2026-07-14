import random

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


def _native():
    from camp_core.integrations import diffusion_planner_v21_native

    return diffusion_planner_v21_native


def _input(*, neighbors: int = 40) -> dict[str, np.ndarray]:
    data = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    data["version"] = np.array(1, dtype=np.int64)
    data["neighbor_agents_past"] = np.zeros(
        (neighbors, 31, 11), dtype=np.float32
    )
    return data


def _assert_numpy_rng_equal(left, right) -> None:
    assert left[0] == right[0]
    np.testing.assert_array_equal(left[1], right[1])
    assert left[2:] == right[2:]


def test_mapping_sha_is_sorted_and_covers_dtype_shape_and_raw_bytes() -> None:
    module = _native()
    first = {
        "z": np.array([[1.0, 2.0]], dtype=np.float32),
        "a": np.array([3], dtype=np.int64),
    }
    reordered = {"a": first["a"], "z": first["z"]}

    digest = module.deterministic_array_mapping_sha256(first)
    assert digest == module.deterministic_array_mapping_sha256(reordered)
    assert digest != module.deterministic_array_mapping_sha256(
        {**reordered, "z": reordered["z"].astype(np.float64)}
    )
    assert digest != module.deterministic_array_mapping_sha256(
        {**reordered, "z": reordered["z"].reshape(2, 1)}
    )
    changed = reordered["z"].copy()
    changed[0, 0] = np.nextafter(changed[0, 0], np.float32(np.inf))
    assert digest != module.deterministic_array_mapping_sha256(
        {**reordered, "z": changed}
    )


@pytest.mark.parametrize(
    ("source_frames", "observed_frames", "padded_frames", "truncated_frames"),
    ((31, 31, 0, 0), (5, 5, 26, 0), (40, 31, 0, 9)),
)
def test_causal_receipt_records_native_padding_and_truncation(
    source_frames: int,
    observed_frames: int,
    padded_frames: int,
    truncated_frames: int,
) -> None:
    module = _native()
    data = _input()
    if observed_frames:
        data["ego_agent_past"][-observed_frames:] = 1.0
        data["neighbor_agents_past"][:, -observed_frames:] = 2.0
    data["ego_agent_future"] = np.ones((80, 3), dtype=np.float32)
    data["neighbor_agents_future"] = np.ones((40, 80, 3), dtype=np.float32)

    boundary = module.causal_input_receipt(data, source_observed_frames=source_frames)

    assert boundary.receipt["source_observed_frames"] == source_frames
    assert boundary.receipt["observed_frames"] == observed_frames
    assert boundary.receipt["padded_frames"] == padded_frames
    assert boundary.receipt["truncated_frames"] == truncated_frames
    assert (
        boundary.receipt["padding_policy"]
        == "native_zero_left_pad_to_31_v1"
    )
    assert set(boundary.causal_input) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert "ego_agent_future" not in boundary.causal_input
    assert "neighbor_agents_future" not in boundary.causal_input
    assert boundary.causal_input["neighbor_agents_past"].shape == (32, 31, 11)
    assert boundary.receipt["input_sha256"] == (
        module.deterministic_array_mapping_sha256(boundary.causal_input)
    )
    assert list(boundary.receipt["arrays"]) == sorted(CAUSAL_DP_INPUT_SCHEMA)
    for key, receipt in boundary.receipt["arrays"].items():
        array = boundary.causal_input[key]
        assert receipt == {
            "shape": list(array.shape),
            "dtype": array.dtype.str,
            "sha256": module.array_sha256(array),
        }


def test_causal_boundary_does_not_mutate_source_and_copies_first_32_neighbors() -> None:
    module = _native()
    data = _input()
    data["neighbor_agents_past"][:, -1, 0] = np.arange(40, dtype=np.float32)
    data["ego_agent_future"] = np.zeros((80, 3), dtype=np.float32)
    source_keys = set(data)

    boundary = module.causal_input_receipt(data, source_observed_frames=31)

    assert set(data) == source_keys
    np.testing.assert_array_equal(
        boundary.causal_input["neighbor_agents_past"][:, -1, 0],
        np.arange(32, dtype=np.float32),
    )
    boundary.causal_input["neighbor_agents_past"][0, -1, 0] = -1.0
    assert data["neighbor_agents_past"][0, -1, 0] == 0.0


@pytest.mark.parametrize(
    "key",
    (
        "route_future",
        "expert_label",
        "closed_loop_outcome",
        "holdout_token",
        "safety_cost",
        "metric_result",
    ),
)
def test_causal_boundary_rejects_forbidden_sources(key: str) -> None:
    module = _native()
    data = _input(neighbors=32)
    data[key] = np.array(1)

    with pytest.raises(ValueError, match="forbidden causal input key"):
        module.causal_input_receipt(data, source_observed_frames=31)


def test_causal_boundary_rejects_bad_padding_and_schema() -> None:
    module = _native()
    bad_padding = _input(neighbors=32)
    bad_padding["ego_agent_past"][0, 0] = 1.0
    with pytest.raises(ValueError, match="left padding"):
        module.causal_input_receipt(bad_padding, source_observed_frames=5)

    bad_schema = _input(neighbors=31)
    with pytest.raises(ValueError, match="at least 32"):
        module.causal_input_receipt(bad_schema, source_observed_frames=31)

    bad_schema = _input(neighbors=32)
    bad_schema["goal_pose"] = np.zeros(3, dtype=np.float64)
    with pytest.raises(ValueError, match="dtype:goal_pose"):
        module.causal_input_receipt(bad_schema, source_observed_frames=31)


def test_candidate_seed_is_route_tick_deterministic_and_validated() -> None:
    module = _native()
    route = "ab" * 32
    value = module.candidate_seed(3418, route, 7)
    assert value == module.candidate_seed(3418, route, 7)
    assert value != module.candidate_seed(3418, route, 8)
    assert value != module.candidate_seed(3419, route, 7)
    assert 0 <= value < 2**63

    with pytest.raises(ValueError, match="route_sha256"):
        module.candidate_seed(3418, "not-a-sha", 7)
    with pytest.raises(ValueError, match="tick_index"):
        module.candidate_seed(3418, route, -1)


def test_candidate_latents_are_fixed_k8_float32_and_rng_isolated() -> None:
    module = _native()
    random.seed(99)
    np.random.seed(101)
    python_before = random.getstate()
    numpy_before = np.random.get_state()

    latents = module.candidate_latents(123456, noise_scale=1.0)

    assert latents.shape == (8, 321, 81, 4)
    assert latents.dtype == np.float32
    assert np.count_nonzero(latents[0]) == 0
    assert all(np.count_nonzero(latents[index]) > 0 for index in range(1, 8))
    np.testing.assert_array_equal(
        latents, module.candidate_latents(123456, noise_scale=1.0)
    )
    assert random.getstate() == python_before
    _assert_numpy_rng_equal(np.random.get_state(), numpy_before)


def test_default_candidate0_identity_is_exact_and_fails_closed() -> None:
    module = _native()
    default = np.arange(80 * 4, dtype=np.float32).reshape(80, 4)
    receipt = module.verify_default_candidate0_identity(default, default.copy())

    assert receipt["elementwise_equal"] is True
    assert receipt["max_abs_difference"] == 0.0
    assert receipt["default_output_sha256"] == receipt["candidate0_sha256"]
    assert receipt["native_ranked_k8"] is False

    drifted = default.copy()
    drifted[0, 0] = np.nextafter(drifted[0, 0], np.float32(np.inf))
    with pytest.raises(ValueError, match="candidate 0 identity"):
        module.verify_default_candidate0_identity(default, drifted)
    with pytest.raises(ValueError, match="shape and dtype"):
        module.verify_default_candidate0_identity(default, default.astype(np.float64))


def test_candidate_tensor_immutability_receipt_fails_on_changed_bytes() -> None:
    module = _native()
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    before = module.array_sha256(candidates)

    receipt = module.verify_candidate_tensor_immutable(candidates, before)
    assert receipt == {
        "candidate_tensor_sha256_before": before,
        "candidate_tensor_sha256_after": before,
        "candidate_tensor_immutable": True,
    }

    candidates[1, 0, 0] = 1.0
    with pytest.raises(ValueError, match="mutated"):
        module.verify_candidate_tensor_immutable(candidates, before)
