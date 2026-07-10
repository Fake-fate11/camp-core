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


def test_combine_candidates_requires_exact_k8_shape() -> None:
    module = _orchestrator()
    top1 = np.zeros((1, 80, 4), dtype=np.float32)
    stochastic = np.ones((7, 80, 4), dtype=np.float32)

    combined = module.combine_candidates(top1, stochastic)

    assert combined.shape == (8, 80, 4)
    assert combined.dtype == np.float32
    with pytest.raises(ValueError, match="K=8"):
        module.combine_candidates(top1, stochastic[:6])
