from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_tier4_npz import (
    OBSERVATION_KEYS, load_native_observation, native_camp_tick, native_model_inputs,
)


def test_loader_never_reads_future_and_does_not_invent_missing_fields(tmp_path):
    raw = {key: np.ones(1) for key in OBSERVATION_KEYS}
    path = tmp_path / "frame.npz"
    # Pickled object would fail allow_pickle=False if the loader accessed it.
    np.savez(path, **raw, ego_agent_future=np.array([SimpleNamespace()], dtype=object))
    result = load_native_observation(path)
    assert set(result) == set(OBSERVATION_KEYS)
    for key in raw:
        np.testing.assert_array_equal(result[key], raw[key])
    del raw["route_lanes_has_speed_limit"]
    np.savez(path, **raw)
    with pytest.raises(KeyError):
        load_native_observation(path)


def test_tick_keeps_actor_order_and_marks_map_context_unavailable():
    raw = {key: np.ones(1) for key in OBSERVATION_KEYS}
    raw.update(neighbor_agents_past=np.arange(32*31*11).reshape(32, 31, 11),
               ego_current_state=np.zeros(10), ego_shape=np.array([2.79, 4.34, 1.7]),
               route_lanes=np.zeros((25,20,33)), polygons=np.zeros((10,40,3)))
    tick = native_camp_tick(raw, np.ones((8, 33, 80, 4)), identity={"anchor_id": "sample"})
    assert tick.neighbor_history is raw["neighbor_agents_past"]
    assert tick.route_atom_context["route_objects"] == ()
    assert tick.signal_authority["source_state"] == "typed_missing"
    assert tick.drivable_area_geometry is None


def test_noise_scale_preserves_default_and_shared_standard_noise():
    pytest.importorskip('torch')
    raw = {key: np.ones(1, dtype=np.float32) for key in OBSERVATION_KEYS}
    raw.update(neighbor_agents_past=np.ones((32,31,11), dtype=np.float32),
               ego_agent_past=np.ones((31,3), dtype=np.float32),
               goal_pose=np.ones(3, dtype=np.float32))
    config = SimpleNamespace(time_len=31, future_len=80, predicted_neighbor_num=320,
                             observation_normalizer=lambda x:x)
    standard = native_model_inputs(raw,config,device='cpu',route_identity='0'*64)['sampled_trajectories'].numpy()
    for scale in (.5,1.,1.5,2.):
        scaled = native_model_inputs(raw,config,device='cpu',route_identity='0'*64,noise_scale=scale)['sampled_trajectories'].numpy()
        np.testing.assert_array_equal(scaled,standard*np.float32(scale))
        assert not np.any(scaled[0])


def test_native_geometry_retains_lanelet_boundaries_and_intersection_type():
    from camp_core.integrations.diffusion_planner_tier4_npz import _native_route_objects
    from camp_core.integrations.diffusion_planner_v26_expert_atom_pair import _ttc_lateral_relevance_mask
    from shapely.geometry import box
    lanes=np.zeros((3,20,33))
    for i,(start,end) in enumerate(((-10.,0.),(0.,20.))):
        lanes[i,:,0]=np.linspace(start,end,20)
        lanes[i,:,5]=2.;lanes[i,:,7]=-2.
    polygons=np.zeros((2,40,3))
    # Four actual points with native one-hot; remaining points are padding.
    polygons[0,:4,:2]=[[5.,-3.],[10.,-3.],[10.,3.],[5.,3.]]
    polygons[0,:4,2]=1.
    objects=_native_route_objects({'route_lanes':lanes,'polygons':polygons})
    assert [o['kind'] for o in objects]==['lane','lane','intersection_area']
    assert objects[0]['geometry'].equals(box(-10,-2,0,2))
    assert objects[1]['geometry'].equals(box(0,-2,20,2))
    xyh=np.zeros((1,80,3))
    xyh[0,:20,0]=-5  # wholly inside lanelet
    xyh[0,20:40,0]=-.5  # footprint spans retained lanelet boundary, not a road-exit atom
    xyh[0,40:60,0]=7  # inside source-labelled intersection
    xyh[0,60:,0]=15
    mask=_ttc_lateral_relevance_mask(xyh,np.array([2.,4.,1.]),{'route_objects':objects})
    np.testing.assert_array_equal(mask[0],np.repeat([False,True,True,False],20))
