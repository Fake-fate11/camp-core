from __future__ import annotations

import numpy as np
import pytest

from camp_core.integrations import diffusion_planner_progress_support as support
from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_LATENCY_KEYS,
    _route_progress_profiles,
    _route_progress_profiles_chunked,
    _route_progress_profiles_reference,
    build_progress_support_logging_payload,
)


def _synthetic_inputs(
    *,
    candidate_count: int,
    support_steps: int,
    route_points: int,
    route_shape: str,
) -> tuple[np.ndarray, np.ndarray]:
    route_x = np.linspace(0.0, float(route_points - 1), route_points)
    if route_shape == "straight":
        route_y = np.zeros_like(route_x)
    elif route_shape == "sine":
        route_y = 3.0 * np.sin(route_x / 31.0)
    else:
        raise ValueError(route_shape)
    route = np.column_stack([route_x, route_y]).astype(np.float64)
    horizon_x = np.linspace(
        0.0,
        min(route_x[-1], 2.0 * support_steps),
        support_steps,
    )
    candidates = np.zeros((candidate_count, support_steps, 2), dtype=np.float64)
    for cand_idx in range(candidate_count):
        progress_scale = max(0.35, 1.0 - 0.025 * cand_idx)
        lateral_offset = ((cand_idx % 5) - 2) * 0.15
        x = np.clip(horizon_x * progress_scale + 0.05 * cand_idx, 0.0, route_x[-1])
        if route_shape == "straight":
            y = np.full_like(x, lateral_offset)
        else:
            y = 3.0 * np.sin(x / 31.0) + lateral_offset
        candidates[cand_idx, :, 0] = x
        candidates[cand_idx, :, 1] = y
    return candidates, route


@pytest.mark.parametrize(
    ("candidate_count", "support_steps", "route_points", "route_shape"),
    [
        (8, 10, 256, "straight"),
        (8, 10, 512, "sine"),
        (8, 10, 2048, "sine"),
        (32, 10, 512, "straight"),
    ],
)
def test_route_projection_chunked_matches_reference_for_predeclared_cases(
    candidate_count: int,
    support_steps: int,
    route_points: int,
    route_shape: str,
) -> None:
    candidates, route = _synthetic_inputs(
        candidate_count=candidate_count,
        support_steps=support_steps,
        route_points=route_points,
        route_shape=route_shape,
    )

    expected = _route_progress_profiles_reference(candidates, route)
    actual = _route_progress_profiles(candidates, route)

    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_route_projection_preserves_reference_tie_behavior() -> None:
    route = np.asarray(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 0.0],
        ],
        dtype=np.float64,
    )
    candidates = np.asarray([[[0.5, 0.0], [0.5, 0.0]]], dtype=np.float64)

    expected = _route_progress_profiles_reference(candidates, route)
    actual = _route_progress_profiles(candidates, route)

    np.testing.assert_allclose(expected, [[0.5, 0.5]], rtol=0.0, atol=0.0)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_route_projection_matches_reference_with_degenerate_segments() -> None:
    route = np.asarray(
        [
            [0.0, 0.0],
            [0.0, 0.0],
            [2.0, 0.0],
            [2.0, 0.0],
            [4.0, 0.0],
        ],
        dtype=np.float64,
    )
    candidates = np.asarray(
        [
            [[0.0, 0.0], [1.0, 0.0], [3.0, 0.0]],
            [[0.5, 0.1], [2.0, 0.0], [4.0, 0.0]],
        ],
        dtype=np.float64,
    )

    expected = _route_progress_profiles_reference(candidates, route)
    actual = _route_progress_profiles(candidates, route)

    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)


def test_route_projection_all_degenerate_segments_fail_closed_to_reference() -> None:
    route = np.asarray([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]], dtype=np.float64)
    candidates = np.asarray([[[0.0, 0.0], [2.0, 2.0]]], dtype=np.float64)

    expected = _route_progress_profiles_reference(candidates, route)
    actual = _route_progress_profiles(candidates, route)

    np.testing.assert_allclose(expected, np.zeros((1, 2)), rtol=0.0, atol=0.0)
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=0.0)


def test_route_projection_nonfinite_inputs_fail_closed_to_reference() -> None:
    route = np.asarray([[0.0, 0.0], [1.0, np.nan], [2.0, 0.0]], dtype=np.float64)
    candidates = np.asarray([[[0.0, 0.0], [1.0, 0.0]]], dtype=np.float64)

    expected = _route_progress_profiles_reference(candidates, route)
    actual = _route_progress_profiles(candidates, route)

    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=0.0)


def test_route_projection_memory_guard_raises_before_wrapper_fallback() -> None:
    candidates, route = _synthetic_inputs(
        candidate_count=2,
        support_steps=4,
        route_points=16,
        route_shape="straight",
    )

    with pytest.raises(MemoryError, match="intermediate guard"):
        _route_progress_profiles_chunked(
            candidates,
            route,
            segment_chunk_size=16,
            max_intermediate_elements=1,
        )
    np.testing.assert_allclose(
        _route_progress_profiles(candidates, route),
        _route_progress_profiles_reference(candidates, route),
        rtol=1e-12,
        atol=1e-12,
    )


def test_progress_support_payload_matches_reference_route_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates, route = _synthetic_inputs(
        candidate_count=8,
        support_steps=10,
        route_points=512,
        route_shape="sine",
    )
    optimized_payload = build_progress_support_logging_payload(
        candidates=candidates,
        route_centerline_ego=route,
        support_steps=10,
        dt_s=0.1,
    )
    monkeypatch.setattr(
        support,
        "_route_progress_profiles",
        support._route_progress_profiles_reference,
    )
    reference_payload = build_progress_support_logging_payload(
        candidates=candidates,
        route_centerline_ego=route,
        support_steps=10,
        dt_s=0.1,
    )
    optimized_without_latency = dict(optimized_payload)
    reference_without_latency = dict(reference_payload)
    optimized_without_latency.pop("latency_ms")
    reference_without_latency.pop("latency_ms")

    assert optimized_without_latency == reference_without_latency
    assert set(optimized_payload["latency_ms"]) == set(PROGRESS_SUPPORT_LATENCY_KEYS)
    assert optimized_payload["progress_support_atom_names"] == list(
        PROGRESS_SUPPORT_ATOM_NAMES
    )
    atoms = np.asarray(optimized_payload["progress_support_atoms"], dtype=np.float64)
    assert np.all(np.isfinite(atoms))
    assert np.all(atoms >= -1e-12)
