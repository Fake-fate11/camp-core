from __future__ import annotations

import importlib

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


def _orchestrator():
    try:
        return importlib.import_module(
            "scripts.integrations.run_diffusion_planner_dp_camp_v18"
        )
    except ModuleNotFoundError:
        pytest.fail("the thin v18 orchestrator is missing")


def _causal_input() -> dict[str, np.ndarray]:
    data = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    data["neighbor_agents_past"][0, 0, 0] = 7.0
    return data


def test_prepare_causal_arrays_pads_only_neighbor_history() -> None:
    module = _orchestrator()

    prepared = module.prepare_causal_arrays(_causal_input())

    assert set(prepared) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert prepared["neighbor_agents_past"].shape == (320, 31, 11)
    assert prepared["neighbor_agents_past"][0, 0, 0] == 7.0
    assert not prepared["neighbor_agents_past"][32:].any()
    assert not any("future" in key for key in prepared)


def test_prepare_causal_arrays_rejects_future_fields() -> None:
    module = _orchestrator()
    data = _causal_input()
    data["ego_agent_future"] = np.zeros((80, 3), dtype=np.float32)

    with pytest.raises(ValueError, match="future|extra"):
        module.prepare_causal_arrays(data)


def test_same_calls_return_paired_ego_and_first_32_neighbors() -> None:
    torch = pytest.importorskip("torch")
    module = _orchestrator()

    class Decoder:
        _guidance_fn = "original"
        _guidance_scale = 9.0

    class Model:
        decoder = Decoder()

        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, _data):
            prediction = torch.zeros((1, 321, 80, 4), dtype=torch.float32)
            prediction[:, :, :, 0] = self.calls
            prediction[:, :, :, 1] = torch.arange(321).reshape(1, 321, 1)
            self.calls += 1
            return None, {"prediction": prediction}

    model = Model()
    context = {
        "torch": torch,
        "device": torch.device("cpu"),
        "model": model,
        "config": type(
            "Config",
            (),
            {
                "predicted_neighbor_num": 320,
                "future_len": 80,
                "observation_normalizer": staticmethod(lambda value: value),
            },
        )(),
        "heading_to_cos_sin": lambda value: value,
        "make_initial_latent": lambda batch, agents, horizon, device, scale: torch.zeros(
            (batch, agents, horizon, 4), device=device
        ),
    }
    data = _causal_input()
    data["neighbor_agents_past"][:3, 0, 0] = 1.0

    candidates, neighbors, valid = module.sample_fixed_dp_sources(data, context)

    assert model.calls == 8
    assert candidates.shape == (8, 80, 4)
    assert neighbors.shape == (8, 32, 80, 4)
    np.testing.assert_array_equal(candidates[:, 0, 0], np.arange(8))
    np.testing.assert_array_equal(neighbors[0, :, 0, 1], np.arange(1, 33))
    np.testing.assert_array_equal(valid[:3], np.ones(3, dtype=bool))
    assert not valid[3:].any()
    assert model.decoder._guidance_fn == "original"
    assert model.decoder._guidance_scale == 9.0


def test_white_signal_mask_is_fail_closed_only_when_reachable() -> None:
    module = _orchestrator()
    candidates = np.zeros((2, 80, 4), dtype=np.float32)
    candidates[:, :, 2] = 1.0
    candidates[0, :, 0] = np.linspace(0.0, 20.0, 80)
    candidates[1, :, 0] = np.linspace(0.0, 2.0, 80)
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :, 0] = np.linspace(10.0, 15.0, 20)
    route[0, :, 2] = 1.0
    route[0, :, 11] = 1.0

    available = module.candidate_signal_source_available_mask(candidates, route)

    np.testing.assert_array_equal(available, [False, True])
