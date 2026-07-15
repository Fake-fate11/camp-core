import hashlib
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


def _runner():
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    return run_diffusion_planner_dp_camp_v21_native


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
            prediction[index, 0] = latent[index, 0, 1:] + base
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
    atom_matrix[:, 0] = np.arange(8, dtype=np.float64)
    atom_matrix[3, 0] = -1.0
    return {
        "canonical_eligible": True,
        "atom_matrix": atom_matrix,
        "physical_feasible_mask": np.ones(8, dtype=bool),
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
):
    state = module.NativeHookState()
    kwargs = {
        "state": state,
        "to_model_tensors": _to_model_tensors,
        "dump_step_npz": _dump_step_npz,
        "materialize": materialize,
        "select_candidate": _select,
        "signal_mask": lambda candidates, causal_input, scene: np.ones(
            8, dtype=bool
        ),
        "planned_red_cost": lambda candidates, causal_input, scene: np.zeros(
            8, dtype=np.float64
        ),
        "atom_scales": np.ones(14, dtype=np.float64),
        "weights": np.eye(1, 14, dtype=np.float64).reshape(14),
        "candidate_seed_root": 3418,
        "route_sha256": "ab" * 32,
    }
    if selection_policy is not None:
        kwargs["selection_policy"] = selection_policy
    if decision_sink is not None:
        kwargs["decision_sink"] = decision_sink
        kwargs["decision_sample_every_ticks"] = decision_sample_every_ticks
    hook = module.NativeCampPredictBatch(**kwargs)
    return hook, state


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
            "candidate_row_sha256",
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
