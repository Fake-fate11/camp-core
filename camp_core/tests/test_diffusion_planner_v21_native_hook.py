import copy
import hashlib
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (
    FixedDpCandidateGenerationCapabilityFailure,
    INVALID_K8_HEADING_NORM_REASON,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    canonical_json_sha256,
)


def _runner():
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    return run_diffusion_planner_dp_camp_v21_native


def _mapped_signal_input(phase: str, stop_x_m: float = 12.0) -> dict:
    stop = [[stop_x_m, -2.0], [stop_x_m, 2.0]]
    stop_sha = canonical_json_sha256(stop)
    runtime = {
        "source_chain_sha256": "1" * 64,
        "stop_line_geometry_sha256": stop_sha,
        "route_geometry_sha256": "2" * 64,
        "regulatory_element_id": 101,
        "stop_line_id": 401,
        "current_phase": phase,
        "decision_timestamp_s": 0.0,
    }
    return {
        "schema_version": "camp_dp_v25_causal_signal_atom_input_v2",
        "source_state": "available",
        "source_valid": True,
        "applicable": phase == "red",
        "current_phase": phase,
        "decision_time_s": 0.0,
        "ego_position_world_m": [0.0, 0.0],
        "ego_heading_rad": 0.0,
        "regulatory_element_id": 101,
        "stop_line_id": 401,
        "stop_line_geometry_world_m": stop,
        "stop_line_geometry_ego_m": stop,
        "stop_line_geometry_sha256": stop_sha,
        "route_tangent_world": [1.0, 0.0],
        "route_tangent_ego": [1.0, 0.0],
        "route_geometry_sha256": "2" * 64,
        "route_arc_m": 10.0,
        "source_chain_sha256": "1" * 64,
        "runtime_receipt": runtime,
        "runtime_receipt_sha256": canonical_json_sha256(runtime),
    }


def _no_signal_input() -> dict:
    runtime = {
        "source_mode": "same_tick_no_signal_rule_no_v2i",
        "current_phase": "none",
        "source_chain_sha256": "3" * 64,
        "route_geometry_sha256": "4" * 64,
        "decision_time_s": 0.0,
    }
    return {
        "schema_version": "camp_dp_v25_causal_signal_atom_input_v2",
        "source_state": "not_applicable",
        "source_valid": True,
        "applicable": False,
        "current_phase": "none",
        "decision_time_s": 0.0,
        "ego_position_world_m": None,
        "ego_heading_rad": None,
        "regulatory_element_id": None,
        "stop_line_id": None,
        "stop_line_geometry_world_m": None,
        "stop_line_geometry_ego_m": None,
        "stop_line_geometry_sha256": None,
        "route_tangent_world": None,
        "route_tangent_ego": None,
        "route_geometry_sha256": "4" * 64,
        "route_arc_m": None,
        "source_chain_sha256": "3" * 64,
        "runtime_receipt": runtime,
        "runtime_receipt_sha256": canonical_json_sha256(runtime),
    }


class _Agent:
    def __init__(self, observed_frames: int = 31):
        self.past_trajectory = np.zeros((observed_frames, 3), dtype=np.float32)
        self.source_observed_frames = observed_frames


class _Scene:
    ego_agent_id = "ego"
    dt = 0.1

    def __init__(self, observed_frames: int = 31):
        self.ego_agent = _Agent(observed_frames)

    def get_agent(self, agent_id: str):
        assert agent_id == "ego"
        return self.ego_agent


class _FakeModel:
    def __init__(self):
        self.calls: list[np.ndarray] = []

    def __call__(self, data):
        latent = np.asarray(data["sampled_trajectories"], dtype=np.float32)
        markers = np.asarray(data["marker"], dtype=np.float32).reshape(-1)
        self.calls.append(latent.copy())
        batch = latent.shape[0]
        prediction = np.zeros((batch, 33, 80, 4), dtype=np.float32)
        for index in range(batch):
            base = np.float32(markers[index] * 10.0)
            ego_prediction = latent[index, 0, 1:] + base
            heading = ego_prediction[:, 2].copy()
            ego_prediction[:, 2] = np.cos(heading)
            ego_prediction[:, 3] = np.sin(heading)
            prediction[index, 0] = ego_prediction
            interaction = np.float32(latent[index, 0].mean())
            for neighbor in range(32):
                prediction[index, neighbor + 1] = base + neighbor + interaction
        logits = np.tile(
            np.array([[0.0, 0.0, 0.0, 2.0, 2.1]], dtype=np.float32),
            (batch, 1),
        )
        return None, {
            "prediction": prediction,
            "turn_indicator_logit": logits,
        }


def _to_model_tensors(
    scene,
    agent_id,
    model_args,
    device,
    map_cache=None,
    inference_delay=0,
):
    del scene, model_args, device, map_cache, inference_delay
    marker = 0.0 if agent_id == "ego" else 1.0
    return {
        "marker": np.array([[marker]], dtype=np.float32),
        "sampled_trajectories": np.zeros(
            (1, 321, 81, 4), dtype=np.float32
        ),
    }


def _native_predict_batch(
    model,
    model_args,
    scene,
    agent_ids,
    device,
    map_cache=None,
    return_turn_indicators=False,
    inference_delay=0,
    turn_indicator_keep_bias=0.25,
):
    tensors = [
        _to_model_tensors(
            scene,
            agent_id,
            model_args,
            device,
            map_cache=map_cache,
            inference_delay=inference_delay,
        )
        for agent_id in agent_ids
    ]
    batched = {
        key: np.concatenate([item[key] for item in tensors], axis=0)
        for key in tensors[0]
    }
    _, outputs = model(batched)
    predictions = {
        agent_id: outputs["prediction"][index, 0].copy()
        for index, agent_id in enumerate(agent_ids)
    }
    if not return_turn_indicators:
        return predictions
    logits = outputs["turn_indicator_logit"].copy()
    logits[:, 4] -= turn_indicator_keep_bias
    turns = {
        agent_id: int(logits[index].argmax())
        for index, agent_id in enumerate(agent_ids)
    }
    return predictions, turns


def _dump_step_npz(scene, map_cache, future_len, predicted_neighbor_num=32):
    del scene, map_cache, future_len
    data = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    data["version"] = np.array(1, dtype=np.int64)
    data["neighbor_agents_past"] = np.zeros(
        (predicted_neighbor_num, 31, 11), dtype=np.float32
    )
    data["ego_agent_future"] = np.zeros((80, 3), dtype=np.float32)
    data["neighbor_agents_future"] = np.zeros(
        (predicted_neighbor_num, 80, 3), dtype=np.float32
    )
    return data


def _materialize(**kwargs):
    candidates = kwargs["candidates"]
    atom_matrix = np.ones((8, 14), dtype=np.float64)
    atom_matrix[:, 0] = np.arange(1, 9, dtype=np.float64)
    atom_matrix[3, 0] = 0.0
    return {
        "canonical_eligible": True,
        "atom_matrix": atom_matrix,
        "source_valid_mask": np.ones(8, dtype=bool),
        "atom_source_valid_mask": np.ones((8, 14), dtype=bool),
        "atom_applicable_mask": np.ones((8, 14), dtype=bool),
        "physical_feasible_mask": np.ones(8, dtype=bool),
        "all_k_high_risk": False,
        "candidate_reasons": tuple(() for _ in range(8)),
        "signal_mask": np.ones(8, dtype=bool),
        "route_speed_source_eligible_mask": np.ones(8, dtype=bool),
        "candidate_shape": candidates.shape,
    }


def _select(**kwargs):
    from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (
        select_camp_candidate,
    )

    return select_camp_candidate(**kwargs)


def _hook(
    module,
    model,
    *,
    materialize=_materialize,
    selection_policy: str | None = None,
    decision_sink=None,
    decision_sample_every_ticks: int = 5,
    scene_adapter=None,
    scene_adapter_model_input_sync=None,
    to_model_tensors=_to_model_tensors,
    causal_input_sink=None,
    causal_input_receipt_sink=None,
    candidate_tensor_sink=None,
    v25_context_sink=None,
    v25_weight_provider=None,
    select_candidate=_select,
    static_weights=None,
    selector_nonnegative_atol: float = 0.0,
):
    state = module.NativeHookState()
    kwargs = {
        "state": state,
        "to_model_tensors": to_model_tensors,
        "dump_step_npz": _dump_step_npz,
        "validate_candidates": validate_fixed_k8_candidate_tensor,
        "materialize": materialize,
        "select_candidate": select_candidate,
        "signal_mask": lambda candidates, causal_input, scene: np.ones(
            8, dtype=bool
        ),
        "planned_red_cost": lambda candidates, causal_input, scene: np.zeros(
            8, dtype=np.float64
        ),
        "atom_scales": np.ones(14, dtype=np.float64),
        "weights": (
            None
            if v25_weight_provider is not None
            else (
                np.eye(1, 14, dtype=np.float64).reshape(14)
                if static_weights is None
                else static_weights
            )
        ),
        "candidate_seed_root": 3418,
        "route_sha256": "ab" * 32,
    }
    if selection_policy is not None:
        kwargs["selection_policy"] = selection_policy
        if selection_policy == "v22_source_valid":
            kwargs["causal_signal_atom_input_provider"] = (
                lambda scene, tick_index: {
                    "scene": scene,
                    "tick_index": tick_index,
                    "source_valid": True,
                }
            )
    if decision_sink is not None:
        kwargs["decision_sink"] = decision_sink
        kwargs["decision_sample_every_ticks"] = decision_sample_every_ticks
    if scene_adapter is not None:
        kwargs["scene_adapter"] = scene_adapter
    if scene_adapter_model_input_sync is not None:
        kwargs["scene_adapter_model_input_sync"] = scene_adapter_model_input_sync
    if causal_input_sink is not None:
        kwargs["causal_input_sink"] = causal_input_sink
    if causal_input_receipt_sink is not None:
        kwargs["causal_input_receipt_sink"] = causal_input_receipt_sink
    if candidate_tensor_sink is not None:
        kwargs["candidate_tensor_sink"] = candidate_tensor_sink
    if v25_context_sink is not None:
        kwargs["v25_context_sink"] = v25_context_sink
    if v25_weight_provider is not None:
        kwargs["v25_weight_provider"] = v25_weight_provider
    if selector_nonnegative_atol > 0.0:
        kwargs["selector_nonnegative_atol"] = selector_nonnegative_atol
    hook = module.NativeCampPredictBatch(**kwargs)
    return hook, state


def test_v25_selector_forwards_frozen_solver_feasibility_tolerance() -> None:
    module = _runner()
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)
    weights[1] += weights[0] + 5e-18
    weights[0] = -5e-18
    captured = []

    def select_with_tolerance(**kwargs):
        captured.append(kwargs.get("simplex_nonnegative_atol"))
        return _select(**kwargs)

    hook, state = _hook(
        module,
        _FakeModel(),
        static_weights=weights,
        selector_nonnegative_atol=1e-9,
        select_candidate=select_with_tolerance,
    )
    hook(
        _FakeModel(),
        SimpleNamespace(predicted_neighbor_num=320, future_len=80),
        _Scene(),
        ["ego"],
        "cpu",
    )
    assert captured == [1e-9]
    assert state.receipts[-1]["selected_index"] == 0


def test_scene_weight_provider_runs_before_affine_selection(monkeypatch) -> None:
    module = _runner()
    from camp_core.integrations import diffusion_planner_v25_context as context_module

    timing_index = context_module.RAW_FEATURE_NAMES.index(
        "traffic_signal_phase_remaining_s"
    )
    source_complete = [True] * context_module.RAW_FEATURE_COUNT
    source_complete[timing_index] = False
    record = context_module.V25ContextRecord(
        raw=np.zeros(context_module.RAW_FEATURE_COUNT, dtype=np.float64),
        source_complete=tuple(source_complete),
        source_receipt={
            "mode": "no_v2i",
            "phase_remaining_available": False,
            "regulatory_signal_mapped": False,
        },
    )
    monkeypatch.setattr(
        context_module,
        "build_v25_raw_context",
        lambda **_kwargs: record,
    )
    events = []

    def provider(payload):
        events.append(("provider", payload))
        weights = np.zeros(14, dtype=np.float64)
        weights[1] = 1.0
        return {
            "schema_version": "camp_dp_v25_scene_weight_receipt_v3",
            "model_name": "CAMP-Scene14D",
            "fixed_dp_head": module.FIXED_DP_HEAD,
            "training_root_sha256": "4" * 64,
            "training_review_root_sha256": "5" * 64,
            "theta_sha256": "1" * 64,
            "context_scaler_sha256": "2" * 64,
            "phi_sha256": "3" * 64,
            "weights_sha256": module.array_sha256(weights),
            "weights": weights.tolist(),
            "runtime_projection": False,
            "softmax": False,
        }

    def select_after_provider(**kwargs):
        assert events and events[-1][0] == "provider"
        events.append(("select", np.asarray(kwargs["weights"]).copy()))
        return _select(**kwargs)

    contexts = []
    hook, state = _hook(
        module,
        _FakeModel(),
        v25_context_sink=contexts.append,
        v25_weight_provider=provider,
        select_candidate=select_after_provider,
    )
    hook(
        _FakeModel(),
        SimpleNamespace(predicted_neighbor_num=320, future_len=80),
        _Scene(),
        ["ego"],
        "cpu",
    )
    receipt = state.receipts[-1]
    assert [event[0] for event in events] == ["provider", "select"]
    assert receipt["selected_index"] == 0
    assert receipt["v25_context"] == contexts[0]
    assert receipt["v25_scene_selector"] == {
        "schema_version": "camp_dp_v25_scene_weight_receipt_v3",
        "model_name": "CAMP-Scene14D",
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "training_root_sha256": "4" * 64,
        "training_review_root_sha256": "5" * 64,
        "theta_sha256": "1" * 64,
        "context_scaler_sha256": "2" * 64,
        "phi_sha256": "3" * 64,
        "weights_sha256": module.array_sha256(events[1][1]),
        "runtime_projection": False,
        "softmax": False,
    }
    assert receipt["latency_ms"]["context"] >= 0.0
    assert receipt["latency_ms"]["scene_weight"] >= 0.0
    receipt["_safety_record"] = {"source_complete": True}
    receipt["_safety_pre"] = {"pre_decision_speed_mps": 0.0}
    receipt["tracker"] = {"status": "ok"}
    public = module._public_tick_receipt(receipt, "camp")
    assert public["v25_scene_selector"] == receipt["v25_scene_selector"]


def test_same_forward_known_heading_failure_is_typed_before_materialization() -> None:
    module = _runner()
    materialized = []
    captured = []

    class Run155PatternModel(_FakeModel):
        def __call__(self, data):
            result = super().__call__(data)
            # Default is call 1; latent candidate 5 is call 6.  Reproduce the
            # audited run155/tick32 invalid block without changing K or shape.
            if len(self.calls) == 6:
                result[1]["prediction"][0, 0, 10:16, 2] = np.float32(
                    0.06830171230455423
                )
                result[1]["prediction"][0, 0, 10:16, 3] = np.float32(0.0)
            return result

    model = Run155PatternModel()

    def must_not_materialize(**kwargs):
        materialized.append(kwargs)
        return _materialize(**kwargs)

    hook, state = _hook(
        module,
        model,
        materialize=must_not_materialize,
        candidate_tensor_sink=lambda *values: captured.append(values),
    )
    with pytest.raises(
        FixedDpCandidateGenerationCapabilityFailure,
        match=INVALID_K8_HEADING_NORM_REASON,
    ) as caught:
        hook(
            model,
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            _Scene(),
            ["ego"],
            "cpu",
        )
    failure = caught.value
    assert failure.tick_index == 0
    assert failure.invalid_indices == tuple((5, step) for step in range(10, 16))
    assert failure.minimum_heading_norm == pytest.approx(0.06830171230455423)
    assert len(captured) == 1
    assert materialized == []
    assert state.receipts[-1]["status"] == "failed"
    assert state.receipts[-1]["default_candidate0_identity"]["elementwise_equal"] is True


def test_fresh_heading_failure_binds_actual_reset_and_same_tick_signal_authority() -> None:
    module = _runner()

    class InvalidHeadingModel(_FakeModel):
        def __call__(self, data):
            result = super().__call__(data)
            if len(self.calls) == 2:
                result[1]["prediction"][0, 0, 3, 2:4] = np.float32(0.0)
            return result

    hook, state = _hook(module, InvalidHeadingModel())
    with pytest.raises(FixedDpCandidateGenerationCapabilityFailure) as caught:
        hook(
            InvalidHeadingModel(),
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            _Scene(),
            ["ego"],
            "cpu",
        )
    failure = caught.value
    state.receipts[0]["_safety_pre"] = {
        "signal_phase_at_interval_start": "red"
    }
    config = {
        "signal_complete_plan_authority": {
            "route_identity_sha256": "a" * 64,
            "semantic_parameter_block_sha256": "b" * 64,
        },
        "map": {"sha256": "c" * 64},
        "seeds": {"scenario": 25401},
        "spawn_config": {"seed": 25401},
    }
    module._bind_fresh_fixed_dp_failure_authority(
        failure,
        config=config,
        route={"sha256": "d" * 64},
        max_steps=64,
        state=state,
    )
    authority = failure.canonical_fresh_failure_authority()
    assert authority["signal_phase"] == "red"
    assert authority["pair_authority"]["initial_input_sha256"] == state.receipts[0][
        "causal_input"
    ]["input_sha256"]
    assert authority["pair_authority"]["route_identity_sha256"] == "a" * 64

    unbound = copy.deepcopy(state)
    unbound.receipts[0]["_safety_pre"].pop("signal_phase_at_interval_start")
    with pytest.raises(ValueError, match="causal authority drifted"):
        module._bind_fresh_fixed_dp_failure_authority(
            failure,
            config=config,
            route={"sha256": "d" * 64},
            max_steps=64,
            state=unbound,
        )


def test_v25_sink_captures_scene_materialization_not_batched_forward_input() -> None:
    module = _runner()
    captured = []

    class OrderedModel(_FakeModel):
        def __call__(self, data):
            assert captured, "scene materialization must be captured before DP forward"
            return super().__call__(data)

    model = OrderedModel()
    hook, _ = _hook(
        module,
        model,
        causal_input_sink=lambda tick, arrays: captured.append((tick, arrays)),
    )
    hook(
        model,
        SimpleNamespace(predicted_neighbor_num=320, future_len=80),
        _Scene(),
        ["ego"],
        "cpu",
    )
    assert len(captured) == 1
    tick, arrays = captured[0]
    assert tick == 0
    assert set(arrays) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert arrays["neighbor_agents_past"].shape[0] == 32
    for name, (shape, dtype_name) in CAUSAL_DP_INPUT_SCHEMA.items():
        assert arrays[name].shape == shape
        assert arrays[name].dtype == np.dtype(dtype_name)


def test_v25_diagnostic_receipt_sink_is_same_tick_and_strictly_copied() -> None:
    module = _runner()
    model = _FakeModel()
    materializations = []
    receipts = []

    def capture_receipt(tick_index, receipt):
        receipts.append((tick_index, receipt))
        receipt["input_sha256"] = "f" * 64
        receipt["arrays"]["goal_pose"]["sha256"] = "e" * 64

    hook, state = _hook(
        module,
        model,
        causal_input_sink=lambda tick, arrays: materializations.append(
            (tick, arrays)
        ),
        causal_input_receipt_sink=capture_receipt,
    )
    hook(
        model,
        SimpleNamespace(predicted_neighbor_num=320, future_len=80),
        _Scene(),
        ["ego"],
        "cpu",
    )

    assert [item[0] for item in materializations] == [0]
    assert [item[0] for item in receipts] == [0]
    native = state.receipts[0]["causal_input"]
    assert native["input_sha256"] != "f" * 64
    assert native["arrays"]["goal_pose"]["sha256"] != "e" * 64
    assert set(native["arrays"]) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert "causal_input_sink" in module.NativeCampPredictBatch.__init__.__code__.co_varnames
    assert (
        "causal_input_receipt_sink"
        in module.NativeCampPredictBatch.__init__.__code__.co_varnames
    )


def test_candidate_tensor_sink_precedes_materialization_and_is_strictly_copied() -> None:
    module = _runner()
    model = _FakeModel()
    captured = []

    def capture(tick_index, candidates, metadata):
        captured.append((tick_index, candidates.copy(), copy.deepcopy(metadata)))
        candidates.fill(0.0)
        metadata["candidate_tensor_sha256"] = "f" * 64

    def fail_after_boundary(**kwargs):
        assert np.any(kwargs["candidates"] != 0.0)
        raise ValueError("materialization sentinel")

    hook, state = _hook(
        module,
        model,
        materialize=fail_after_boundary,
        candidate_tensor_sink=capture,
    )
    with pytest.raises(ValueError, match="materialization sentinel"):
        hook(
            model,
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            _Scene(),
            ["ego"],
            "cpu",
        )
    assert len(captured) == 1
    tick_index, candidates, metadata = captured[0]
    assert tick_index == 0
    assert candidates.shape == (8, 80, 4)
    assert candidates.dtype == np.float32
    assert metadata["candidate_tensor_sha256"] != "f" * 64
    assert metadata["candidate_row_sha256"][0] == metadata["default_output_sha256"]
    assert state.receipts[0]["candidate_tensor_sha256_before"] != "f" * 64
    assert "candidate_tensor_sink" in module.NativeCampPredictBatch.__init__.__code__.co_varnames


def test_v25_scene_adapter_runs_before_fixed_k8_input_materialization() -> None:
    module = _runner()
    model = _FakeModel()
    calls = []

    def scene_adapter(scene, tick_index):
        scene.controlled_marker = "injected"
        calls.append(tick_index)
        return {"tick_index": tick_index, "injected": True}

    hook, state = _hook(module, model, scene_adapter=scene_adapter)
    scene = _Scene()
    hook(
        model,
        SimpleNamespace(predicted_neighbor_num=320, future_len=80),
        scene,
        ["ego"],
        "cpu",
    )

    assert calls == [0]
    assert scene.controlled_marker == "injected"
    assert state.receipts[-1]["controlled_scene"] == {
        "tick_index": 0,
        "injected": True,
    }


def test_v25_same_tick_cache_sync_precedes_model_tensor_materialization_and_is_deterministic() -> None:
    module = _runner()

    class Cache:
        def __init__(self):
            self._all_lanes = np.zeros((1, 20, 33), dtype=np.float32)
            self._all_lanes[:, :, 8] = 1.0

        def sync_tl_state(self, map_data):
            self._all_lanes[:, :, 8:13] = map_data.lanes[:, :, 8:13]

    class Adapter:
        def __call__(self, scene, tick_index):
            scene.map_data.lanes[:, :, 8:13] = 0.0
            scene.map_data.lanes[:, :, 10] = 1.0
            scene.ego_agent.route_lanes[:, :, 8:13] = 0.0
            scene.ego_agent.route_lanes[:, :, 10] = 1.0
            return {"tick_index": tick_index, "signal": "red"}

        def sync_model_input_map_cache(self, scene, cache, tick_index):
            assert tick_index == 0
            cache.sync_tl_state(scene.map_data)
            return {"tick_index": tick_index, "cache_matches_scene_after": True}

    def tensors(scene, agent_id, model_args, device, map_cache=None, inference_delay=0):
        assert np.all(map_cache._all_lanes[:, :, 10] == 1.0)
        assert np.all(scene.ego_agent.route_lanes[:, :, 10] == 1.0)
        result = _to_model_tensors(
            scene,
            agent_id,
            model_args,
            device,
            map_cache=map_cache,
            inference_delay=inference_delay,
        )
        result["marker"][:] = map_cache._all_lanes[0, 0, 10]
        return result

    def run_once():
        scene = _Scene()
        scene.map_data = SimpleNamespace(
            lanes=np.pad(
                np.ones((1, 20, 1), dtype=np.float32), ((0, 0), (0, 0), (8, 24))
            )
        )
        scene.ego_agent.route_lanes = scene.map_data.lanes.copy()
        cache = Cache()
        adapter = Adapter()
        model = _FakeModel()
        hook, state = _hook(
            module,
            model,
            scene_adapter=adapter,
            scene_adapter_model_input_sync=adapter.sync_model_input_map_cache,
            to_model_tensors=tensors,
        )
        hook(
            model,
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            scene,
            ["ego"],
            "cpu",
            map_cache=cache,
        )
        return state.receipts[-1]

    first = run_once()
    second = run_once()
    assert first["controlled_scene"]["model_input_cache"] == {
        "tick_index": 0,
        "cache_matches_scene_after": True,
    }
    assert first["default_output_sha256"] == second["default_output_sha256"]
    assert first["candidate_tensor_sha256_before"] == second[
        "candidate_tensor_sha256_before"
    ]


def test_v24_dp_candidate0_mode_generates_immutable_k8_and_returns_default() -> None:
    module = _runner()
    scene = _Scene()
    args = SimpleNamespace(predicted_neighbor_num=320, future_len=80)
    agent_ids = ["npc", "ego"]
    native_model = _FakeModel()
    native_predictions = _native_predict_batch(
        native_model, args, scene, agent_ids, "cpu"
    )
    state = module.NativeHookState()
    model = _FakeModel()
    hook = module.NativeCampPredictBatch(
        state=state,
        to_model_tensors=_to_model_tensors,
        dump_step_npz=_dump_step_npz,
        validate_candidates=validate_fixed_k8_candidate_tensor,
        materialize=None,
        select_candidate=None,
        signal_mask=None,
        planned_red_cost=None,
        atom_scales=None,
        weights=None,
        candidate_seed_root=3418,
        route_sha256="ab" * 32,
        operational_mode="dp_candidate0",
    )
    predictions = hook(model, args, scene, agent_ids, "cpu")
    receipt = state.receipts[-1]
    np.testing.assert_array_equal(predictions["ego"], native_predictions["ego"])
    np.testing.assert_array_equal(predictions["npc"], native_predictions["npc"])
    assert len(model.calls) == 8
    assert receipt["selected_index"] == 0
    assert receipt["candidate0_operational_default"] is True
    assert receipt["candidate_tensor_sha256_before"] == receipt[
        "candidate_tensor_sha256_after"
    ]
    assert receipt["default_candidate0_identity"]["elementwise_equal"] is True
    assert receipt["selected_trajectory_sha256"] == receipt["default_output_sha256"]
    assert receipt["selection_policy"] == "candidate0_operational_default"
    assert "atom_matrix_sha256" not in receipt
    receipt["_safety_record"] = {"source_complete": True}
    receipt["_safety_pre"] = {"pre_decision_speed_mps": 0.0}
    receipt["tracker"] = {"status": "ok"}
    public = module._public_tick_receipt(receipt, "dp")
    assert public["candidate_row_sha256"][0] == public["default_output_sha256"]
    assert "tie_break_contract" not in public
    assert "causal_evidence_sha256" not in public
    module._validate_arm_receipt(
        {
            "status": "ok",
            "arm": "dp",
            "route_name": "candidate0-test",
            "route_sha256": "a" * 64,
            "initial_state_sha256": "b" * 64,
            "initial_input_sha256": public["input_sha256"],
            "claim_authorized": False,
            "ticks": [public],
        },
        "dp",
        expected_ticks=1,
        require_summary=False,
    )


def test_holdout_candidate0_action_first_returns_before_pool_generation() -> None:
    module = _runner()
    scene = _Scene()
    args = SimpleNamespace(predicted_neighbor_num=320, future_len=80)
    agent_ids = ["npc", "ego"]
    native_model = _FakeModel()
    native_predictions = _native_predict_batch(
        native_model, args, scene, agent_ids, "cpu"
    )
    state = module.NativeHookState()
    model = _FakeModel()
    hook = module.NativeCampPredictBatch(
        state=state,
        to_model_tensors=_to_model_tensors,
        dump_step_npz=_dump_step_npz,
        validate_candidates=validate_fixed_k8_candidate_tensor,
        materialize=None,
        select_candidate=None,
        signal_mask=None,
        planned_red_cost=None,
        atom_scales=None,
        weights=None,
        candidate_seed_root=3418,
        route_sha256="ab" * 32,
        operational_mode="dp_candidate0",
        candidate0_action_first=True,
    )
    predictions = hook(model, args, scene, agent_ids, "cpu")
    receipt = state.receipts[-1]
    np.testing.assert_array_equal(predictions["ego"], native_predictions["ego"])
    np.testing.assert_array_equal(predictions["npc"], native_predictions["npc"])
    assert len(model.calls) == 1
    assert receipt["selected_index"] == 0
    assert receipt["candidate0_operational_default"] is True
    assert receipt["candidate0_pool_evidence_collected_online"] is False
    assert receipt["candidate0_pool_evidence_required_post_action"] is True
    assert receipt["same_forward_claimed"] is False
    assert type(receipt["action_available_ns"]) is int
    assert "candidate_tensor_sha256_before" not in receipt
    assert "candidate_seed" not in receipt
    assert "candidate_inference" not in receipt["latency_ms"]


def test_fresh_candidate0_pool_diagnostics_preserve_default_and_expose_masks() -> None:
    module = _runner()
    scene = _Scene()
    args = SimpleNamespace(predicted_neighbor_num=320, future_len=80)
    agent_ids = ["npc", "ego"]
    native_model = _FakeModel()
    native_predictions = _native_predict_batch(
        native_model, args, scene, agent_ids, "cpu"
    )
    state = module.NativeHookState()
    source = np.asarray([True] * 8, dtype=np.bool_)
    physical = np.asarray([True] + [False] * 7, dtype=np.bool_)

    def materialize(**_kwargs):
        return {
            "atom_matrix": np.zeros((8, 14), dtype=np.float64),
            "physical_feasible_mask": physical,
            "source_valid_mask": source,
            "route_speed_source_eligible_mask": source,
            "candidate_reasons": [[] for _ in range(8)],
        }

    model = _FakeModel()
    hook = module.NativeCampPredictBatch(
        state=state,
        to_model_tensors=_to_model_tensors,
        dump_step_npz=_dump_step_npz,
        validate_candidates=validate_fixed_k8_candidate_tensor,
        materialize=materialize,
        select_candidate=None,
        signal_mask=lambda candidates, _causal, _scene: np.zeros(
            len(candidates), dtype=np.bool_
        ),
        planned_red_cost=lambda candidates, _causal, _scene: np.zeros(
            len(candidates), dtype=np.float64
        ),
        atom_scales=None,
        weights=None,
        candidate_seed_root=3418,
        route_sha256="ab" * 32,
        operational_mode="dp_candidate0",
        causal_signal_atom_input_provider=lambda _scene, _tick: {
            "schema_version": "test_same_tick_signal_v1"
        },
        candidate0_pool_diagnostics=True,
    )
    predictions = hook(model, args, scene, agent_ids, "cpu")
    receipt = state.receipts[-1]
    np.testing.assert_array_equal(predictions["ego"], native_predictions["ego"])
    np.testing.assert_array_equal(predictions["npc"], native_predictions["npc"])
    assert receipt["selected_index"] == 0
    assert receipt["candidate0_operational_default"] is True
    assert receipt["source_valid_mask"] == source.tolist()
    assert receipt["physical_feasible_mask"] == physical.tolist()
    assert receipt["all_k_high_risk"] is False
    assert receipt["candidate_tensor_sha256_before"] == receipt[
        "candidate_tensor_sha256_after"
    ]
    assert "atom_matrix_sha256" in receipt


def test_hook_matches_native_default_and_changes_only_selected_ego() -> None:
    module = _runner()
    scene = _Scene()
    args = SimpleNamespace(predicted_neighbor_num=320, future_len=80)
    agent_ids = ["npc", "ego"]
    native_model = _FakeModel()
    native_predictions, native_turns = _native_predict_batch(
        native_model,
        args,
        scene,
        agent_ids,
        "cpu",
        return_turn_indicators=True,
    )
    model = _FakeModel()
    hook, state = _hook(module, model)

    predictions, turns = hook(
        model,
        args,
        scene,
        agent_ids,
        "cpu",
        return_turn_indicators=True,
    )

    assert len(model.calls) == 8
    assert np.count_nonzero(model.calls[0]) == 0
    for call in model.calls[1:]:
        assert np.count_nonzero(call[0]) == 0
        assert np.count_nonzero(call[1]) > 0
    np.testing.assert_array_equal(predictions["npc"], native_predictions["npc"])
    assert turns == native_turns
    receipt = state.receipts[-1]
    assert receipt["selected_index"] == 3
    assert receipt["default_output_sha256"] == module.array_sha256(
        native_predictions["ego"]
    )
    assert receipt["selected_trajectory_sha256"] == module.array_sha256(
        predictions["ego"]
    )
    assert receipt["candidate_tensor_sha256_before"] == receipt[
        "candidate_tensor_sha256_after"
    ]
    assert receipt["candidate_neighbor_shape"] == [8, 32, 80, 4]
    assert receipt["npc_operational_outputs_unchanged"] is True
    assert receipt["default_turn_indicators_retained"] is True
    assert all(
        np.isfinite(value) and value >= 0.0
        for value in receipt["latency_ms"].values()
    )


@pytest.mark.parametrize("failure", ("missing_atom_source", "all_k_infeasible"))
def test_hook_fails_closed_without_candidate0_fallback(failure: str) -> None:
    module = _runner()
    model = _FakeModel()

    def unavailable(**kwargs):
        result = _materialize(**kwargs)
        result["canonical_eligible"] = False
        result["exclusion_reason"] = failure
        if failure == "all_k_infeasible":
            result["canonical_eligible"] = True
            result["physical_feasible_mask"][:] = False
        return result

    hook, state = _hook(module, model, materialize=unavailable)
    with pytest.raises(RuntimeError, match=failure):
        hook(
            model,
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            _Scene(),
            ["ego"],
            "cpu",
            return_turn_indicators=True,
        )
    assert state.receipts[-1]["status"] == "failed"
    assert "selected_index" not in state.receipts[-1]
    expected_feasible = [False] * 8 if failure == "all_k_infeasible" else [True] * 8
    assert state.receipts[-1]["physical_feasible_mask"] == expected_feasible
    assert state.receipts[-1]["source_complete_mask"] == [True] * 8
    assert state.receipts[-1]["candidate_reasons"] == [[] for _ in range(8)]
    assert "selector_diagnostics=" in state.receipts[-1]["failure_reason"]


def test_v22_hook_selects_all_k_high_risk_without_fallback() -> None:
    module = _runner()
    model = _FakeModel()

    def all_k_high_risk(**kwargs):
        result = _materialize(**kwargs)
        result["source_valid_mask"] = np.ones(8, dtype=bool)
        result["physical_feasible_mask"] = np.zeros(8, dtype=bool)
        result["all_k_high_risk"] = True
        return result

    hook, state = _hook(
        module,
        model,
        materialize=all_k_high_risk,
        selection_policy="v22_source_valid",
    )
    predictions = hook(
        model,
        SimpleNamespace(predicted_neighbor_num=320, future_len=80),
        _Scene(),
        ["ego"],
        "cpu",
    )

    receipt = state.receipts[-1]
    assert receipt["status"] == "ok"
    assert receipt["selected_index"] == 3
    assert receipt["selected_index"] != 0
    assert receipt["selection_policy"] == "v22_source_valid"
    assert receipt["all_k_high_risk"] is True
    assert receipt["source_valid_mask"] == [True] * 8
    assert receipt["physical_feasible_mask"] == [False] * 8
    assert receipt["candidate_tensor_sha256_before"] == receipt[
        "candidate_tensor_sha256_after"
    ]
    assert receipt["selected_trajectory_sha256"] == module.array_sha256(
        predictions["ego"]
    )


def test_v22_decision_sink_samples_every_five_ticks_after_immutability() -> None:
    module = _runner()
    model = _FakeModel()
    snapshots = []
    hook, _ = _hook(
        module,
        model,
        selection_policy="v22_source_valid",
        decision_sink=snapshots.append,
    )

    for _ in range(11):
        hook(
            model,
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            _Scene(),
            ["ego"],
            "cpu",
        )

    assert [item["sidecar"]["tick_index"] for item in snapshots] == [0, 5, 10]
    for snapshot in snapshots:
        assert set(snapshot["feature_payload"]) == {
            "atom_matrix",
            "source_valid_mask",
            "atom_source_valid_mask",
            "atom_applicable_mask",
            "candidate_row_sha256",
                "candidate_tensor",
                "default_output",
                "causal_evidence",
            }
        assert np.asarray(snapshot["feature_payload"]["atom_matrix"]).shape == (8, 14)
        assert snapshot["feature_payload"]["source_valid_mask"] == [True] * 8
        assert len(snapshot["feature_payload"]["candidate_row_sha256"]) == 8
        candidate0_sha = snapshot["feature_payload"]["candidate_row_sha256"][0]
        assert snapshot["sidecar"]["default_output_sha256"] == candidate0_sha
        assert snapshot["sidecar"]["candidate0_sha256"] == candidate0_sha
        assert snapshot["sidecar"]["default_candidate0_identity"] == {
            "elementwise_equal": True,
            "max_abs_difference": 0.0,
            "default_output_sha256": candidate0_sha,
            "candidate0_sha256": candidate0_sha,
            "native_ranked_k8": False,
        }
        assert snapshot["sidecar"]["candidate_tensor_sha256_before"] == snapshot[
            "sidecar"
        ]["candidate_tensor_sha256_after"]
        assert snapshot["sidecar"]["causal_input_sha256"]
        assert snapshot["sidecar"]["offline_label_provenance"] == (
            "pending_train_only_offline_supervision_sidecar"
        )


def test_v24_decision_sink_can_sample_every_tick_after_immutability() -> None:
    module = _runner()
    model = _FakeModel()
    snapshots = []
    hook, _ = _hook(
        module,
        model,
        selection_policy="v22_source_valid",
        decision_sink=snapshots.append,
        decision_sample_every_ticks=1,
    )

    for _ in range(4):
        hook(
            model,
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            _Scene(),
            ["ego"],
            "cpu",
        )

    assert [item["sidecar"]["tick_index"] for item in snapshots] == [0, 1, 2, 3]


@pytest.mark.parametrize("cadence", (0, -1, True))
def test_decision_sink_rejects_invalid_sampling_cadence(cadence) -> None:
    module = _runner()
    with pytest.raises(ValueError, match="sample cadence"):
        _hook(
            module,
            _FakeModel(),
            selection_policy="v22_source_valid",
            decision_sink=lambda _snapshot: None,
            decision_sample_every_ticks=cadence,
        )


def test_v22_decision_sink_is_not_called_after_candidate_mutation() -> None:
    module = _runner()
    model = _FakeModel()
    snapshots = []

    def mutate(**kwargs):
        result = _materialize(**kwargs)
        kwargs["candidates"][0, 0, 0] = 99.0
        return result

    hook, _ = _hook(
        module,
        model,
        materialize=mutate,
        selection_policy="v22_source_valid",
        decision_sink=snapshots.append,
    )
    with pytest.raises(ValueError, match="mutated"):
        hook(
            model,
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            _Scene(),
            ["ego"],
            "cpu",
        )
    assert snapshots == []


def test_hook_detects_candidate_mutation() -> None:
    module = _runner()
    model = _FakeModel()

    def mutate(**kwargs):
        result = _materialize(**kwargs)
        kwargs["candidates"][0, 0, 0] = 99.0
        return result

    hook, state = _hook(module, model, materialize=mutate)
    with pytest.raises(ValueError, match="mutated"):
        hook(
            model,
            SimpleNamespace(predicted_neighbor_num=320, future_len=80),
            _Scene(),
            ["ego"],
            "cpu",
        )
    assert state.receipts[-1]["status"] == "failed"


def test_native_source_hash_and_signature_guards_fail_before_model_call(
    tmp_path,
) -> None:
    module = _runner()
    source = tmp_path / "native.py"
    source.write_text("frozen\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert module.verify_native_source_hashes(
        tmp_path, {"native.py": digest}
    ) == {"native.py": digest}
    with pytest.raises(ValueError, match="source SHA256 mismatch"):
        module.verify_native_source_hashes(tmp_path, {"native.py": "0" * 64})

    replay = SimpleNamespace(
        _predict_batch=lambda: None,
        advance_scene_mpc=lambda *args, **kwargs: None,
    )
    model = _FakeModel()
    hook, state = _hook(module, model)
    with pytest.raises(ValueError, match="signature mismatch"):
        with module.patched_native_replay(replay, hook, state):
            pass
    assert model.calls == []


def test_patch_restores_predictor_and_tracker_on_success_and_exception() -> None:
    module = _runner()

    def original_predict(
        model,
        model_args,
        scene,
        agent_ids,
        device,
        map_cache=None,
        return_turn_indicators=False,
        inference_delay=0,
        turn_indicator_keep_bias=0.25,
    ):
        del (
            model,
            model_args,
            scene,
            agent_ids,
            device,
            map_cache,
            return_turn_indicators,
            inference_delay,
            turn_indicator_keep_bias,
        )

    def original_tracker(*args, **kwargs):
        return args, kwargs

    replay = SimpleNamespace(
        _predict_batch=original_predict,
        advance_scene_mpc=original_tracker,
    )
    state = module.NativeHookState(receipts=[{"latency_ms": {}}])
    replacement = lambda *args, **kwargs: None

    with module.patched_native_replay(replay, replacement, state):
        assert replay._predict_batch is replacement
        assert replay.advance_scene_mpc is not original_tracker
        replay.advance_scene_mpc("scene", value=1)
    assert replay._predict_batch is original_predict
    assert replay.advance_scene_mpc is original_tracker
    assert state.receipts[-1]["latency_ms"]["tracker"] >= 0.0

    with pytest.raises(RuntimeError, match="boom"):
        with module.patched_native_replay(replay, replacement, state):
            raise RuntimeError("boom")
    assert replay._predict_batch is original_predict
    assert replay.advance_scene_mpc is original_tracker


def test_v25_safety_capture_uses_exact_certified_stop_line_not_legacy_proximity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _runner()
    ego = SimpleNamespace(
        current_position=np.array([0.0, 0.0], dtype=np.float64),
        current_heading=0.0,
        current_velocity=np.array([2.0, 0.0], dtype=np.float64),
        length=4.5,
        width=1.8,
        wheelbase=2.7,
        route_lanes=np.zeros((1, 20, 12), dtype=np.float32),
    )
    ego.route_lanes[0, :, 10] = 1.0
    scene = SimpleNamespace(ego_agent=ego)
    builder = SimpleNamespace(
        select_route_segment_indices=lambda *_args, **_kwargs: [101]
    )
    replay = SimpleNamespace(
        _ego_obb_corners=lambda *_args, **_kwargs: np.array(
            [[-2.0, -1.0], [2.0, -1.0], [2.0, 1.0], [-2.0, 1.0]],
            dtype=np.float64,
        )
    )
    wrong_nearby = np.array([[[3.0, -3.0], [3.0, 3.0]]], dtype=np.float64)
    monkeypatch.setattr(
        module,
        "_legacy_matching_red_stop_lines",
        lambda *_args, **_kwargs: wrong_nearby,
    )
    legacy_receipt = {"tick_index": 0}
    module._capture_pre_safety(
        legacy_receipt, scene, builder, [101], replay
    )
    assert legacy_receipt["_safety_pre"]["red_stop_lines"] == wrong_nearby.tolist()

    monkeypatch.setattr(
        module,
        "_legacy_matching_red_stop_lines",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy proximity matching must not run")
        ),
    )
    certified_receipt = {"tick_index": 0}
    module._capture_pre_safety(
        certified_receipt,
        scene,
        builder,
        [101],
        replay,
        certified_signal_atom_input=_mapped_signal_input("red", 12.0),
    )
    assert certified_receipt["_safety_pre"] == {
        "pre_decision_speed_mps": 2.0,
        "front_center_prev_xy": [2.0, 0.0],
        "red_light_at_interval_start": True,
        "red_stop_lines": [[[12.0, -2.0], [12.0, 2.0]]],
        "red_source_complete": True,
        "signal_phase_at_interval_start": "red",
        "certified_signal_stop_lines": [[[12.0, -2.0], [12.0, 2.0]]],
    }

    green_receipt = {"tick_index": 1}
    module._capture_pre_safety(
        green_receipt,
        scene,
        builder,
        [101],
        replay,
        certified_signal_atom_input=_mapped_signal_input("green", 12.0),
    )
    assert green_receipt["_safety_pre"]["signal_phase_at_interval_start"] == "green"
    assert green_receipt["_safety_pre"]["red_stop_lines"] == []
    assert green_receipt["_safety_pre"]["certified_signal_stop_lines"] == [
        [[12.0, -2.0], [12.0, 2.0]]
    ]


@pytest.mark.parametrize("phase", ["green", "yellow"])
def test_certified_nonred_phase_has_complete_zero_red_event(phase: str) -> None:
    module = _runner()
    actual_phase, stop_lines = module._certified_signal_safety_source(
        _mapped_signal_input(phase)
    )
    assert actual_phase == phase
    assert stop_lines.tolist() == [[[12.0, -2.0], [12.0, 2.0]]]


def test_certified_no_signal_is_complete_not_applicable_zero_event() -> None:
    module = _runner()
    phase, stop_lines = module._certified_signal_safety_source(_no_signal_input())
    assert phase == "none"
    assert stop_lines.shape == (0, 2, 2)


def test_invalid_mapped_signal_source_fails_closed() -> None:
    module = _runner()
    invalid = _mapped_signal_input("red")
    invalid["source_valid"] = False
    with pytest.raises(ValueError, match="source state"):
        module._certified_signal_safety_source(invalid)
