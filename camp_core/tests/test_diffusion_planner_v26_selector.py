import numpy as np
from shapely import box

import camp_core.integrations.diffusion_planner_v26_selector as selector_module
from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    V26_CAMP_ATOM_NAMES,
    V26_DP_MASKED_TOKEN_TYPES,
    V26_TRANSITION_ATOM_NAME,
)
from camp_core.integrations.diffusion_planner_v26_selector import (
    DiffusionPlannerCAMPSelector,
    DiffusionPlannerCAMPTick,
)


def _base_candidate_artifact():
    statuses = (
        *(["observed"] * 6),
        "not_applicable",
        "not_applicable",
        *(["observed"] * 7),
    )
    names = V26_CAMP_ATOM_NAMES[:15]
    observed = tuple(name for name, status in zip(names, statuses) if status == "observed")
    raw = np.zeros((8, len(observed)), dtype=np.float64)
    return {
        "observed_atom_names": list(observed),
        "candidate_atoms_raw": raw,
        "atom_states": [
            {"name": name, "status": status}
            for name, status in zip(names, statuses)
        ],
    }


def _tick(origin_seconds, *, with_scene=False):
    prediction = np.zeros((8, 33, 80, 4), dtype=np.float64)
    prediction[:, 0, :, 0] = 0.1 * np.arange(1, 81)[None, :]
    prediction[:, 0, :, 0] += 0.01 * np.arange(8)[:, None]
    prediction[:, 0, :, 2] = 1.0
    token_masks = None
    encoder_tokens = None
    if with_scene:
        encoder_tokens = np.ones((len(V26_DP_MASKED_TOKEN_TYPES), 256))
        token_masks = {
            name: np.zeros(1, dtype=bool) for name in V26_DP_MASKED_TOKEN_TYPES
        }
    return DiffusionPlannerCAMPTick(
        identity={"anchor_id": f"tick-{origin_seconds}"},
        prediction=prediction,
        neighbor_history=np.zeros((32, 31, 11)),
        static_objects=np.zeros((5, 10)),
        ego_shape=np.asarray([2.79, 4.34, 1.70]),
        route_lanes=np.zeros((25, 20, 33)),
        route_speed_limits=np.ones(25),
        route_has_speed_limits=np.ones(25, dtype=bool),
        route_atom_context={},
        signal_authority={"source_state": "not_applicable"},
        origin_seconds=origin_seconds,
        ego_x=origin_seconds,
        ego_y=0.0,
        ego_yaw=0.0,
        current_speed_mps=1.0,
        encoder_tokens=encoder_tokens,
        token_masks=token_masks,
    )


def test_one_call_selector_materializes_scores_and_keeps_continuity(monkeypatch):
    monkeypatch.setattr(
        selector_module,
        "build_observable_obbs",
        lambda *args, **kwargs: np.zeros((8, 1, 80, 5)),
    )
    monkeypatch.setattr(
        selector_module,
        "materialize_v26_same_tick_full_atom_bank_pair",
        lambda **kwargs: _base_candidate_artifact(),
    )
    selector = DiffusionPlannerCAMPSelector.from_directory(
        "artifacts/camp_v26_k8_50k"
    )

    fixed = selector.select(_tick(0.0), mode="fixed")
    assert fixed.atom_artifact["atom_states"][-1]["status"] == "not_applicable"
    np.testing.assert_array_equal(
        fixed.selected_trajectory,
        _tick(0.0).prediction[fixed.selected_row, 0],
    )

    scene = selector.select(_tick(0.1, with_scene=True), mode="scene")
    assert scene.atom_artifact["atom_states"][-1]["name"] == V26_TRANSITION_ATOM_NAME
    assert scene.atom_artifact["atom_states"][-1]["status"] == "observed"
    assert scene.atom_artifact["transition_overlap_sample_count"] == 79
    assert scene.rerank.continuous_scene_representation_read is True

    selector.reset()
    reset = selector.select(_tick(0.2), mode="fixed")
    assert reset.atom_artifact["atom_states"][-1]["status"] == "not_applicable"


def test_selector_runs_real_atom_materializer_end_to_end():
    prediction = np.zeros((8, 33, 80, 4), dtype=np.float64)
    prediction[:, :, :, 2] = 1.0
    prediction[:, 1, :, 1] = 20.0
    history = np.zeros((32, 31, 11), dtype=np.float64)
    history[0, :, 1] = 20.0
    history[0, :, 2] = 1.0
    history[0, :, 6:8] = (2.0, 5.0)
    route = np.zeros((25, 20, 33), dtype=np.float64)
    route[0, :, 0] = np.linspace(-10.0, 100.0, 20)
    route[0, :, 2] = 1.0
    route[0, :, 5] = 5.0
    route[0, :, 7] = -5.0
    speed_limits = np.zeros(25, dtype=np.float64)
    speed_limits[0] = 10.0
    has_speed_limits = np.zeros(25, dtype=bool)
    has_speed_limits[0] = True
    lane_geometry = box(-20.0, -6.0, 120.0, 6.0)
    tick = DiffusionPlannerCAMPTick(
        identity={"anchor_id": "real-materializer"},
        prediction=prediction,
        neighbor_history=history,
        static_objects=np.zeros((5, 10)),
        ego_shape=np.asarray([3.0, 5.0, 2.0]),
        route_lanes=route,
        route_speed_limits=speed_limits,
        route_has_speed_limits=has_speed_limits,
        route_atom_context={
            "route_objects": (
                {"kind": "lane", "fid": 1, "geometry": lane_geometry},
            ),
            "red_movements": (),
            "signal_source_state": "not_applicable",
            "signal_reason": "fixture_no_signal",
        },
        signal_authority={"source_state": "not_applicable"},
        drivable_area_geometry=box(-20.0, -20.0, 120.0, 20.0),
        drivable_area_source_authority="fixture_full_drivable_polygon",
        origin_seconds=0.0,
        ego_x=0.0,
        ego_y=0.0,
        ego_yaw=0.0,
        current_speed_mps=0.0,
    )
    selector = DiffusionPlannerCAMPSelector.from_directory(
        "artifacts/camp_v26_k8_50k"
    )
    decision = selector.select(tick, mode="fixed")

    assert decision.selected_trajectory.shape == (80, 4)
    assert decision.atom_artifact["bank_atom_names"] == list(V26_CAMP_ATOM_NAMES)
    assert decision.atom_artifact["atom_states"][-1]["status"] == "not_applicable"
    assert decision.rerank.active_atom_names == tuple(
        decision.atom_artifact["observed_atom_names"]
    )
