from __future__ import annotations

import hashlib
import inspect
import pickle
import random
import sys
import time
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from camp_core.integrations.diffusion_planner_v21_native import (
    array_sha256,
    candidate_latents,
    candidate_seed,
    causal_input_receipt,
    verify_candidate_tensor_immutable,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
NATIVE_SOURCE_SHA256 = {
    "scenario_generation/replay.py": (
        "92158e32f8e2626a20aeee1783501d1afad228f06d5948f3426716d93320c5eb"
    ),
    "scenario_generation/simulate.py": (
        "de4542fbc8685718379dbf0626499113d8bca6f7dead1c4456d2d34ffd0b9e4e"
    ),
    "scenario_generation/tensor_converter.py": (
        "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
    ),
    "scenario_generation/mpc_tracker.py": (
        "bf2fdc6398898a42eda4ab3d12045c5204eb5ce8a993dbf96feee975de04395a"
    ),
    "scenario_generation/traffic_light.py": (
        "5a1659fe753102c514528c0bd93c261124bdf8de11bbc00ba5b941c151956af4"
    ),
}
_PREDICT_BATCH_PARAMETERS = (
    "model",
    "model_args",
    "scene",
    "agent_ids",
    "device",
    "map_cache",
    "return_turn_indicators",
    "inference_delay",
    "turn_indicator_keep_bias",
)


@dataclass
class NativeHookState:
    tick_index: int = 0
    receipts: list[dict[str, Any]] = field(default_factory=list)


class NativeCampPredictBatch:
    def __init__(
        self,
        *,
        state: NativeHookState,
        to_model_tensors: Callable[..., Mapping[str, Any]],
        dump_step_npz: Callable[..., Mapping[str, Any]],
        materialize: Callable[..., Mapping[str, Any]],
        select_candidate: Callable[..., Mapping[str, Any]],
        signal_mask: Callable[[np.ndarray, Mapping[str, Any], Any], np.ndarray],
        planned_red_cost: Callable[
            [np.ndarray, Mapping[str, Any], Any], np.ndarray
        ],
        atom_scales: np.ndarray,
        weights: np.ndarray,
        candidate_seed_root: int,
        route_sha256: str,
    ) -> None:
        self.state = state
        self.to_model_tensors = to_model_tensors
        self.dump_step_npz = dump_step_npz
        self.materialize = materialize
        self.select_candidate = select_candidate
        self.signal_mask = signal_mask
        self.planned_red_cost = planned_red_cost
        self.atom_scales = np.asarray(atom_scales, dtype=np.float64)
        self.weights = np.asarray(weights, dtype=np.float64)
        self.candidate_seed_root = candidate_seed_root
        self.route_sha256 = route_sha256
        if self.atom_scales.shape != (14,) or self.weights.shape != (14,):
            raise ValueError("atom scales and weights must each have shape [14]")

    def __call__(
        self,
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
        started_ns = time.perf_counter_ns()
        tick_index = self.state.tick_index
        self.state.tick_index += 1
        receipt: dict[str, Any] = {
            "tick_index": tick_index,
            "status": "running",
            "native_ranked_k8": False,
            "_planning_started_ns": started_ns,
            "latency_ms": {},
        }
        self.state.receipts.append(receipt)
        try:
            if not agent_ids:
                raise ValueError("CAMP hook requires the ego agent")
            if len(agent_ids) != len(set(agent_ids)):
                raise ValueError("agent_ids must be unique")
            ego_id = scene.ego_agent_id
            if ego_id not in agent_ids:
                raise ValueError("CAMP hook agent_ids must contain scene ego")
            if (
                int(model_args.predicted_neighbor_num) != 320
                or int(model_args.future_len) != 80
            ):
                raise ValueError("fixed DP model_args must use 320 neighbors and 80 steps")
            ego_index = agent_ids.index(ego_id)

            input_started = time.perf_counter_ns()
            tensor_dicts = [
                self.to_model_tensors(
                    scene,
                    agent_id,
                    model_args,
                    device,
                    map_cache=map_cache,
                    inference_delay=inference_delay,
                )
                for agent_id in agent_ids
            ]
            batched = _cat_tensor_dicts(tensor_dicts)
            raw_causal = self.dump_step_npz(
                scene,
                map_cache,
                model_args.future_len,
                predicted_neighbor_num=32,
            )
            boundary = causal_input_receipt(
                raw_causal,
                source_observed_frames=_source_observed_frames(scene),
            )
            receipt["causal_input"] = boundary.receipt
            receipt["latency_ms"]["input_materialization"] = _elapsed_ms(
                input_started
            )

            default_started = time.perf_counter_ns()
            outputs = _model_outputs(model, batched)
            prediction = _prediction_array(outputs, len(agent_ids))
            receipt["latency_ms"]["default_inference"] = _elapsed_ms(
                default_started
            )
            direct_predictions = {
                agent_id: prediction[index, 0].copy()
                for index, agent_id in enumerate(agent_ids)
            }
            direct_npc_sha = {
                agent_id: array_sha256(value)
                for agent_id, value in direct_predictions.items()
                if agent_id != ego_id
            }
            turns = _turn_indicators(
                outputs,
                agent_ids,
                turn_indicator_keep_bias,
            )

            default_ego = direct_predictions[ego_id]
            receipt["default_output_sha256"] = array_sha256(default_ego)
            seed = candidate_seed(
                self.candidate_seed_root, self.route_sha256, tick_index
            )
            latents = candidate_latents(seed, noise_scale=1.0)
            receipt["candidate_seed"] = seed
            receipt["candidate_latent_sha256"] = array_sha256(latents)

            candidates = [default_ego.copy()]
            candidate_neighbors = [prediction[ego_index, 1:33].copy()]
            rng_before = _global_rng_digest(batched["sampled_trajectories"])
            candidate_started = time.perf_counter_ns()
            for index in range(1, 8):
                candidate_data = _replace_ego_latent(
                    batched, ego_index, latents[index]
                )
                candidate_output = _prediction_array(
                    _model_outputs(model, candidate_data), len(agent_ids)
                )
                candidates.append(candidate_output[ego_index, 0].copy())
                candidate_neighbors.append(
                    candidate_output[ego_index, 1:33].copy()
                )
            receipt["latency_ms"]["candidate_inference"] = _elapsed_ms(
                candidate_started
            )
            rng_after = _global_rng_digest(batched["sampled_trajectories"])
            if rng_after != rng_before:
                raise ValueError("global RNG state changed during candidate work")
            receipt["global_rng_sha256_before"] = rng_before
            receipt["global_rng_sha256_after"] = rng_after

            candidate_tensor = np.stack(candidates).astype(np.float32, copy=False)
            neighbor_tensor = np.stack(candidate_neighbors).astype(
                np.float32, copy=False
            )
            if neighbor_tensor.shape != (8, 32, 80, 4):
                raise ValueError("candidate neighbor tensor must be [8,32,80,4]")
            before_sha = array_sha256(candidate_tensor)
            receipt["candidate_tensor_sha256_before"] = before_sha
            receipt["candidate_neighbor_sha256"] = array_sha256(neighbor_tensor)
            receipt["candidate_neighbor_shape"] = list(neighbor_tensor.shape)

            causal_input = boundary.causal_input
            neighbor_valid = np.any(
                np.abs(causal_input["neighbor_agents_past"]) > 1e-8,
                axis=(1, 2),
            )
            signals = np.asarray(
                self.signal_mask(candidate_tensor, causal_input, scene), dtype=bool
            )
            red_cost = np.asarray(
                self.planned_red_cost(candidate_tensor, causal_input, scene),
                dtype=np.float64,
            )
            atom_started = time.perf_counter_ns()
            materialized = self.materialize(
                candidates=candidate_tensor,
                causal_input=causal_input,
                neighbor_predictions=neighbor_tensor,
                neighbor_valid_mask=neighbor_valid,
                signal_mask=signals,
                planned_red_light_cost=red_cost,
                dt=float(scene.dt),
            )
            receipt["latency_ms"]["atom_materialization"] = _elapsed_ms(
                atom_started
            )
            immutable = verify_candidate_tensor_immutable(
                candidate_tensor, before_sha
            )
            receipt.update(immutable)

            selector_started = time.perf_counter_ns()
            selection = self.select_candidate(
                candidates=candidate_tensor,
                materialized=materialized,
                atom_scales=self.atom_scales,
                weights=self.weights,
            )
            receipt["latency_ms"]["selector"] = _elapsed_ms(selector_started)
            receipt.update(
                verify_candidate_tensor_immutable(candidate_tensor, before_sha)
            )
            if selection.get("status") != "ok":
                reason = str(selection.get("failure_reason") or "selector_failed")
                raise RuntimeError(reason)
            selected_index = int(selection["selected_index"])
            selected = np.asarray(selection["selected_trajectory"])
            if (
                selected_index < 0
                or selected_index >= 8
                or selected.shape != (80, 4)
                or selected.dtype != np.float32
                or not np.array_equal(selected, candidate_tensor[selected_index])
                or array_sha256(selected)
                != array_sha256(candidate_tensor[selected_index])
            ):
                raise ValueError("selector did not return an exact indexed candidate")

            direct_predictions[ego_id] = selected.copy()
            npc_after_sha = {
                agent_id: array_sha256(value)
                for agent_id, value in direct_predictions.items()
                if agent_id != ego_id
            }
            if npc_after_sha != direct_npc_sha:
                raise ValueError("native NPC operational outputs changed")
            receipt.update(
                {
                    "status": "ok",
                    "selected_index": selected_index,
                    "selected_trajectory_sha256": array_sha256(selected),
                    "npc_operational_outputs_unchanged": True,
                    "default_turn_indicators_retained": True,
                    "physical_feasible_mask": np.asarray(
                        materialized.get("physical_feasible_mask", []), dtype=bool
                    ).tolist(),
                    "source_complete_mask": np.asarray(
                        materialized.get(
                            "route_speed_source_eligible_mask", []
                        ),
                        dtype=bool,
                    ).tolist(),
                }
            )
            if materialized.get("atom_matrix") is not None:
                receipt["atom_matrix_sha256"] = array_sha256(
                    np.asarray(materialized["atom_matrix"])
                )
            if selection.get("scores") is not None:
                receipt["scores"] = np.asarray(
                    selection["scores"], dtype=np.float64
                ).tolist()
            receipt["latency_ms"]["hook_total"] = _elapsed_ms(started_ns)
            return (
                (direct_predictions, turns)
                if return_turn_indicators
                else direct_predictions
            )
        except Exception as exc:
            receipt["status"] = "failed"
            receipt["failure_reason"] = str(exc)
            receipt["latency_ms"]["hook_total"] = _elapsed_ms(started_ns)
            raise


def verify_native_source_hashes(
    dp_repo: str | Path,
    expected: Mapping[str, str] = NATIVE_SOURCE_SHA256,
) -> dict[str, str]:
    root = Path(dp_repo)
    actual: dict[str, str] = {}
    for relative, expected_sha in expected.items():
        path = root / relative
        if not path.is_file():
            raise ValueError(f"missing native source: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected_sha:
            raise ValueError(f"native source SHA256 mismatch: {relative}")
        actual[relative] = digest
    return actual


def verify_predict_batch_signature(predict_batch: Callable[..., Any]) -> None:
    parameters = inspect.signature(predict_batch).parameters
    if tuple(parameters) != _PREDICT_BATCH_PARAMETERS:
        raise ValueError("native _predict_batch signature mismatch")
    defaults = {
        "map_cache": None,
        "return_turn_indicators": False,
        "inference_delay": 0,
        "turn_indicator_keep_bias": 0.25,
    }
    if any(parameters[name].default != value for name, value in defaults.items()):
        raise ValueError("native _predict_batch signature mismatch")


@contextmanager
def patched_native_replay(
    replay_module,
    replacement_predict_batch: Callable[..., Any],
    state: NativeHookState,
    *,
    dp_repo: str | Path | None = None,
    expected_source_hashes: Mapping[str, str] = NATIVE_SOURCE_SHA256,
):
    original_predict = replay_module._predict_batch
    original_tracker = replay_module.advance_scene_mpc
    verify_predict_batch_signature(original_predict)
    if dp_repo is not None:
        verify_native_source_hashes(dp_repo, expected_source_hashes)

    def timed_tracker(*args, **kwargs):
        started = time.perf_counter_ns()
        try:
            return original_tracker(*args, **kwargs)
        finally:
            if state.receipts:
                receipt = state.receipts[-1]
                receipt.setdefault("latency_ms", {})["tracker"] = _elapsed_ms(
                    started
                )
                planning_started = receipt.get("_planning_started_ns")
                if planning_started is not None:
                    receipt["latency_ms"]["total_planning"] = _elapsed_ms(
                        int(planning_started)
                    )

    replay_module._predict_batch = replacement_predict_batch
    replay_module.advance_scene_mpc = timed_tracker
    try:
        yield
    finally:
        replay_module._predict_batch = original_predict
        replay_module.advance_scene_mpc = original_tracker


def _cat_tensor_dicts(dicts: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not dicts:
        raise ValueError("cannot concatenate an empty tensor batch")
    keys = tuple(dicts[0])
    if any(tuple(item) != keys for item in dicts[1:]):
        raise ValueError("native tensor dictionary keys/order changed")
    if len(dicts) == 1:
        return dict(dicts[0])
    result: dict[str, Any] = {}
    for key in keys:
        values = [item[key] for item in dicts]
        if isinstance(values[0], np.ndarray):
            result[key] = np.concatenate(values, axis=0)
        else:
            torch = sys.modules.get("torch")
            if torch is None:
                raise RuntimeError("torch tensors present before torch import")
            result[key] = torch.cat(values, dim=0)
    return result


def _model_outputs(model, data: Mapping[str, Any]) -> Mapping[str, Any]:
    sampled = data["sampled_trajectories"]
    torch = sys.modules.get("torch")
    context = (
        torch.no_grad()
        if torch is not None and sampled.__class__.__module__.startswith("torch")
        else nullcontext()
    )
    with context:
        _, outputs = model(data)
    if not isinstance(outputs, Mapping):
        raise ValueError("fixed DP model outputs must be a mapping")
    return outputs


def _prediction_array(outputs: Mapping[str, Any], batch_size: int) -> np.ndarray:
    if "prediction" not in outputs:
        raise ValueError("fixed DP output is missing prediction")
    prediction = _to_numpy(outputs["prediction"])
    if (
        prediction.shape != (batch_size, 321, 80, 4)
        and prediction.shape != (batch_size, 33, 80, 4)
    ):
        raise ValueError("fixed DP prediction shape changed")
    if prediction.dtype != np.float32 or not np.isfinite(prediction).all():
        raise ValueError("fixed DP prediction must be finite float32")
    if prediction.shape[1] < 33:
        raise ValueError("fixed DP prediction has fewer than 32 neighbors")
    return prediction


def _turn_indicators(
    outputs: Mapping[str, Any], agent_ids: list[str], keep_bias: float
) -> dict[str, int]:
    logits = outputs.get("turn_indicator_logit")
    if logits is None:
        return {}
    values = _to_numpy(logits).copy()
    if values.shape[0] != len(agent_ids) or values.ndim != 2:
        raise ValueError("turn indicator logit shape changed")
    if keep_bias != 0.0 and values.shape[-1] > 4:
        values[..., 4] -= keep_bias
    classes = values.argmax(axis=-1)
    return {agent_id: int(classes[index]) for index, agent_id in enumerate(agent_ids)}


def _replace_ego_latent(
    batched: Mapping[str, Any], ego_index: int, latent: np.ndarray
) -> dict[str, Any]:
    original = batched["sampled_trajectories"]
    if tuple(original.shape[1:]) != tuple(latent.shape):
        raise ValueError("native sampled_trajectories latent shape changed")
    if isinstance(original, np.ndarray):
        sampled = original.copy()
        sampled[ego_index] = latent
    else:
        sampled = original.clone()
        replacement = sampled.new_tensor(latent)
        sampled[ego_index].copy_(replacement)
    result = dict(batched)
    result["sampled_trajectories"] = sampled
    return result


def _to_numpy(value: Any) -> np.ndarray:
    if isinstance(value, np.ndarray):
        return value
    result = value.detach().cpu().numpy()
    return np.asarray(result)


def _source_observed_frames(scene: Any) -> int:
    ego = scene.get_agent(scene.ego_agent_id)
    explicit = getattr(ego, "source_observed_frames", None)
    return int(explicit if explicit is not None else len(ego.past_trajectory))


def _global_rng_digest(sampled_trajectories: Any) -> str:
    digest = hashlib.sha256()
    digest.update(pickle.dumps(random.getstate(), protocol=5))
    digest.update(pickle.dumps(np.random.get_state(), protocol=5))
    torch = sys.modules.get("torch")
    if torch is not None and sampled_trajectories.__class__.__module__.startswith(
        "torch"
    ):
        digest.update(torch.get_rng_state().cpu().numpy().tobytes())
        if torch.cuda.is_available():
            for state in torch.cuda.get_rng_state_all():
                digest.update(state.cpu().numpy().tobytes())
    return digest.hexdigest()


def _elapsed_ms(started_ns: int) -> float:
    return (time.perf_counter_ns() - started_ns) / 1e6
