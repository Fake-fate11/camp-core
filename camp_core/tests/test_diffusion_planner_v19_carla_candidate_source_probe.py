from __future__ import annotations

import importlib
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.carla_exact_speed_source import LiftingTolerances
from camp_core.integrations.carla_exact_speed_source import canonical_json_sha256
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
            ("1", 5.0, 0.0),
            ("1", 10.0, 5.0),
            ("2", 0.0, 5.0),
            ("2", 5.0, 10.0),
        )
    ]
    corridor = {
        "schema_version": "dp_camp_v20_carla_route_corridor_v1",
        "map_sha256": "a" * 64,
        "route_sample_step_m": 5.0,
        "station_allowance_m": 3.0518578125e-05,
        "contact_tolerance_m": 0.01,
        "route_samples": [
            {
                "road_id": "1",
                "section_id": 0,
                "lane_id": -1,
                "s": 0.0,
                "x": -5.0,
                "y": 0.0,
                "z": 1.0,
                "lane_width": 3.5,
                "is_junction": False,
            },
            *samples,
        ],
        "directed_edges": [(("1", 0, -1), ("2", 0, -1))],
        "identity_directions": [
            [["1", 0, -1], 1],
            [["2", 0, -1], 1],
        ],
    }
    corridor["corridor_sha256"] = canonical_json_sha256(corridor)

    def route_lane(start_x: float) -> dict[str, list[list[float]]]:
        return {
            "centerline": [[start_x + index, 0.0] for index in range(20)],
            "left_boundary": [[start_x + index, 1.75] for index in range(20)],
            "right_boundary": [[start_x + index, -1.75] for index in range(20)],
        }

    return {
        "schema_version": "dp_camp_v20_carla_source_capture_v1",
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
        "route_lanes": [route_lane(0.0), route_lane(19.0)],
        "lifting_corridor": corridor,
        "mission_goal_pose": [10.0, 0.0, 0.0],
        "frames": frames,
    }


def test_materialization_keeps_corridor_out_of_fixed_dp_route() -> None:
    capture = _capture()
    dp_route_before = np.asarray(capture["route_lanes"][0]["centerline"]).copy()

    materialized, context, _ = _probe().build_probe_materialization(
        capture,
        tolerances=LiftingTolerances(
            1.5273609989704584,
            3.0518578125e-05,
            1e-9,
            3.0518578125e-05,
        ),
    )

    assert context.samples[0].x < capture["route_samples"][0]["x"]
    np.testing.assert_array_equal(
        materialized.dp_input["route_lanes"][0, : len(dp_route_before), :2],
        dp_route_before,
    )
    assert materialized.metadata["source_metadata"]["lifting_corridor_sha256"] == (
        capture["lifting_corridor"]["corridor_sha256"]
    )


def test_materialization_rejects_corridor_sha_drift() -> None:
    capture = _capture()
    capture["lifting_corridor"]["route_samples"][0]["x"] -= 1.0

    with pytest.raises(ValueError, match="corridor SHA mismatch"):
        _probe().build_probe_materialization(
            capture,
            tolerances=LiftingTolerances(1.5, 1e-6, 1e-6, 1e-6),
        )


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


def test_frozen_station_tolerance_covers_carla_float32_xodr_api() -> None:
    probe = _probe()
    bound = 3.0517578125e-05
    allowance = 1e-9

    assert probe.FROZEN_LIFTING_TOLERANCES == LiftingTolerances(
        1.5273609989704584,
        bound + allowance,
        1e-9,
        bound + allowance,
    )
    road_length = 966.8900000000001
    assert abs(float(np.float32(road_length)) - road_length) <= bound


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
            camp_head="c" * 40,
            dp_head="d" * 40,
            selector_hashes=("1" * 64, "2" * 64, "3" * 64),
        )


def test_write_probe_requests_rejects_content_digest_as_git_head() -> None:
    output = SimpleNamespace(exists=lambda: False)

    with pytest.raises(ValueError, match="CAMP head Git commit is invalid"):
        _probe().write_probe_requests(
            _capture(),
            tolerances=LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
            camp_request_dir=output,
            default_request_dir=output,
            context_path=output,
            camp_head="c" * 64,
            dp_head="d" * 40,
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
        camp_head="c" * 40,
        dp_head="d" * 40,
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
    assert all(request["camp_head"] == "c" * 40 for request in requests)
    assert all(request["dp_head"] == "d" * 40 for request in requests)
