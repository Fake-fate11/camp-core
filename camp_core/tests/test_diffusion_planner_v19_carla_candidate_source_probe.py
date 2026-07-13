from __future__ import annotations

import importlib
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.carla_exact_speed_source import LiftingTolerances
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


def _probe():
    return importlib.import_module(
        "scripts.integrations."
        "run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe"
    )


def _capture() -> dict[str, object]:
    frames = [
        {
            "timestamp_us": index * 100_000,
            "ego_state": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "ego_extent": [4.5, 1.8, 1.5],
            "actors": [],
        }
        for index in range(31)
    ]
    samples = [
        {
            "road_id": road,
            "section_id": 0,
            "lane_id": -1,
            "s": s,
            "x": x,
            "y": 0.0,
            "z": 1.0,
            "lane_width": 3.5,
            "is_junction": road == "2",
        }
        for road, s, x in (
            ("1", 0.0, 0.0),
            ("1", 5.0, 5.0),
            ("2", 0.0, 5.0),
            ("2", 5.0, 10.0),
        )
    ]
    return {
        "schema_version": "dp_camp_v19_carla_source_capture_v1",
        "selection_seed": 3411,
        "map_name": "Town01",
        "map_sha256": "a" * 64,
        "source_head": "b" * 64,
        "decision_timestamp_us": 3_000_000,
        "traffic_timestamp_us": None,
        "traffic_light_state_available": False,
        "route_source": "current_map_topology_successors",
        "route_sample_step_m": 5.0,
        "route_samples": samples,
        "directed_edges": [(("1", 0, -1), ("2", 0, -1))],
        "route_lanes": [
            {
                "centerline": [[0.0, 0.0], [5.0, 0.0]],
                "left_boundary": [[0.0, 1.75], [5.0, 1.75]],
                "right_boundary": [[0.0, -1.75], [5.0, -1.75]],
            },
            {
                "centerline": [[5.0, 0.0], [10.0, 0.0]],
                "left_boundary": [[5.0, 1.75], [10.0, 1.75]],
                "right_boundary": [[5.0, -1.75], [10.0, -1.75]],
            },
        ],
        "mission_goal_pose": [10.0, 0.0, 0.0],
        "frames": frames,
    }


def test_build_probe_materialization_reuses_causal_and_lifting_contracts() -> None:
    materialized, context, transform = _probe().build_probe_materialization(
        _capture(),
        tolerances=LiftingTolerances(
            1.5273609989704584,
            1.0000017763568395e-9,
            1e-9,
            1.0000017763568395e-9,
        ),
    )

    assert set(materialized.dp_input) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert not materialized.dp_input["route_lanes_has_speed_limit"].any()
    assert context.edges == ((("1", 0, -1), ("2", 0, -1)),)
    assert len(context.source_sha256) == 64
    np.testing.assert_array_equal(transform, np.eye(3))


def test_build_probe_materialization_rejects_outcomes() -> None:
    capture = _capture()
    capture["safety_outcome"] = 0.0

    with pytest.raises(ValueError, match="forbidden source field"):
        _probe().build_probe_materialization(
            capture,
            tolerances=LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
        )


def test_write_probe_requests_is_exactly_once() -> None:
    output = SimpleNamespace(exists=lambda: True)

    with pytest.raises(FileExistsError, match="already exists"):
        _probe().write_probe_requests(
            _capture(),
            tolerances=LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
            camp_request_dir=output,
            default_request_dir=output,
            context_path=output,
            camp_head="c" * 64,
            dp_head="d" * 64,
            selector_hashes=("1" * 64, "2" * 64, "3" * 64),
        )


def test_write_probe_requests_freezes_source_only_metadata(monkeypatch) -> None:
    probe = _probe()
    output = SimpleNamespace(exists=lambda: False)
    requests = []
    monkeypatch.setattr(
        probe,
        "write_request",
        lambda directory, causal_input, metadata: requests.append(metadata),
    )
    monkeypatch.setattr(probe, "_write_json_atomic", lambda path, value: None)

    probe.write_probe_requests(
        _capture(),
        tolerances=LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
        camp_request_dir=output,
        default_request_dir=output,
        context_path=output,
        camp_head="c" * 64,
        dp_head="d" * 64,
        selector_hashes=("1" * 64, "2" * 64, "3" * 64),
    )

    assert [request["arm"] for request in requests] == ["camp", "dp_default"]
    assert all(request["scenario_seed"] == 3411 for request in requests)
    assert all(request["dp_seed_root"] == 3412 for request in requests)
    assert all(
        request["speed_source_policy"] == "candidate_local_exact_speed"
        for request in requests
    )
    assert requests[0]["selector_hashes"] == ["1" * 64, "2" * 64, "3" * 64]
    assert "selector_hashes" not in requests[1]
    assert all("selected_index" not in request for request in requests)
    assert all("outcome" not in " ".join(request).lower() for request in requests)
