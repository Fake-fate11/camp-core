"""V26-native same-ego B8 callback and fixed-DP replay boundary.

The only non-V26 runtime dependency here is the narrow fixed-DP replay API
bridge.  In particular this module does not import the V25 industrial runner,
the V25 fair validator, its callback, or its evaluation/safety consumers.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .diffusion_planner_causal_atoms import materialize_canonical_14d, validate_fixed_k8_candidate_tensor
from .diffusion_planner_v21_native import (
    array_sha256,
    candidate_latents,
    candidate_seed,
    causal_input_receipt,
)
from .diffusion_planner_v25_context import RAW_FEATURE_NAMES, build_v25_raw_context, context_weights
from .diffusion_planner_v26_development_profiling import (
    ACTIVE_ATOM_INDICES_BY_ARM,
    ATOM_SET_BY_ARM,
    OPERATIONAL_ARM,
    PROFILE_ARMS,
)
from .diffusion_planner_v26_integration_boundary import (
    FROZEN_SIMPLEX_TOLERANCE,
    V26_NATIVE_CALLBACK_ID,
    V26_NATIVE_RUNNER_ID,
    V26NativeHookState,
)


class V26RequestedStateCountReached(RuntimeError):
    """Normal terminal for an exact V26 planned-state denominator."""


def _elapsed_ms(started_ns: int) -> float:
    return (time.perf_counter_ns() - started_ns) / 1e6


def _tensor_dict_sha256(value: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    for key in sorted(value):
        tensor = value[key]
        array = tensor.detach().cpu().contiguous().numpy()
        digest.update(key.encode("utf-8"))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(json.dumps(list(array.shape), separators=(",", ":")).encode("ascii"))
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def _same_ego_batch_metadata(tensors: Mapping[str, Any]) -> dict[str, Any]:
    torch = __import__("torch")
    metadata: dict[str, dict[str, Any]] = {}
    for key, value in sorted(tensors.items()):
        if getattr(value, "ndim", 0) < 1 or int(value.shape[0]) != 8:
            raise ValueError("V26 same-ego B8 input topology drifted")
        floating = bool(value.is_floating_point() or value.is_complex())
        if floating and not bool(torch.isfinite(value).all().item()):
            raise ValueError("V26 same-ego B8 input became nonfinite")
        if key != "sampled_trajectories" and not bool(
            torch.equal(value, value[0:1].expand_as(value))
        ):
            raise ValueError("V26 same-ego nonlatent rows drifted")
        metadata[key] = {
            "shape": [int(size) for size in value.shape],
            "dtype": str(value.dtype),
            "finite": True,
        }
    return {
        "same_ego_batch_size": 8,
        "nonlatent_rows_identical": True,
        "tensor_metadata": metadata,
    }


def _tie_and_margin(scores: Any, source_mask: Any) -> tuple[list[int] | None, float | None]:
    if scores is None:
        return None, None
    values = np.asarray(scores, dtype=np.float64)
    mask = np.asarray(source_mask, dtype=np.bool_)
    ordered = sorted((float(values[index]), int(index)) for index in np.flatnonzero(mask))
    if not ordered:
        return None, None
    best = ordered[0][0]
    return (
        [index for score, index in ordered if score == best],
        None if len(ordered) < 2 else float(ordered[1][0] - best),
    )


class V26NativeSameEgoB8Callback:
    """One model forward per state; all five selectors consume its frozen pool."""

    def __init__(
        self,
        *,
        model: Any,
        model_args: Any,
        tensor_converter: Any,
        fixed_dp_repo: Path,
        fixed_config: Mapping[str, Any],
        route_sha256: str,
        builder: Any,
        route_ids: Sequence[int],
        state: V26NativeHookState,
        max_ticks: int,
        selector_assets: Any,
        signal_adapter: Any,
        integration_boundary: Mapping[str, Any],
        simplex_nonnegative_atol: float = FROZEN_SIMPLEX_TOLERANCE,
    ) -> None:
        if simplex_nonnegative_atol != FROZEN_SIMPLEX_TOLERANCE:
            raise ValueError("V26 callback requires frozen simplex tolerance 1e-9")
        self.model = model
        self.model_args = model_args
        self.tensor_converter = tensor_converter
        self.fixed_dp_repo = Path(fixed_dp_repo)
        self.fixed_config = dict(fixed_config)
        self.route_sha256 = str(route_sha256)
        self.builder = builder
        self.route_ids = tuple(int(value) for value in route_ids)
        self.state = state
        self.max_ticks = int(max_ticks)
        self.selector_assets = selector_assets
        self.signal_adapter = signal_adapter
        self.integration_boundary = dict(integration_boundary)
        self.simplex_nonnegative_atol = float(simplex_nonnegative_atol)
        self.model_call_count = 0
        self.primary_candidates: list[np.ndarray] = []
        self.signal_adapter.bind_builder(builder)

        from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (
            _fixed_dp_red_cost,
            candidate_signal_source_available_mask,
        )
        from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (
            select_camp_candidate,
        )

        self._fixed_dp_red_cost = _fixed_dp_red_cost
        self._signal_mask = candidate_signal_source_available_mask
        self._select_candidate = select_camp_candidate

    def __call__(
        self,
        model: Any,
        model_args: Any,
        scene: Any,
        agent_ids: list[str],
        device: str,
        map_cache: Any = None,
        return_turn_indicators: bool = False,
        inference_delay: int = 0,
        turn_indicator_keep_bias: float = 0.25,
    ) -> Any:
        if len(self.state.receipts) >= self.max_ticks:
            raise V26RequestedStateCountReached
        if model is not self.model or model_args is not self.model_args:
            raise ValueError("V26 callback model binding drifted")
        if not agent_ids or scene.ego_agent_id not in agent_ids:
            raise ValueError("V26 callback requires the ego in the fixed-DP batch")
        from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
            _cat_tensor_dicts,
            _prediction_array,
            _source_observed_frames,
            _turn_indicators,
        )

        started_ns = time.perf_counter_ns()
        tick = len(self.state.receipts)
        receipt: dict[str, Any] = {
            "tick_index": tick,
            "status": "running",
            "runner_id": V26_NATIVE_RUNNER_ID,
            "callback_id": V26_NATIVE_CALLBACK_ID,
            "generator_id": self.integration_boundary["generator_id"],
            "generator_topology": dict(self.integration_boundary["generator_topology"]),
            "integration_boundary": dict(self.integration_boundary),
            "latency_ms": {},
        }
        self.state.receipts.append(receipt)
        ego_id = scene.ego_agent_id
        ego_index = agent_ids.index(ego_id)
        try:
            forward_route_ids = self.builder.select_route_segment_indices(
                list(self.route_ids),
                scene.ego_agent.current_position,
                max_segments=25,
            ) or list(self.route_ids[:25])
            forward_route_ids = [
                int(lanelet_id)
                for lanelet_id in forward_route_ids
                if int(lanelet_id) in self.builder._cache
            ][:25]
            self.signal_adapter.bind_runtime_lanelet_ids(
                route_lanelet_ids=forward_route_ids,
                map_lanelet_ids=self.builder._last_map_data_ids,
            )
            receipt["controlled_scene"] = dict(self.signal_adapter(scene, tick))
            receipt["controlled_scene"]["model_input_cache"] = dict(
                self.signal_adapter.sync_model_input_map_cache(scene, map_cache, tick)
            )
            causal_signal_atom_input = dict(
                self.signal_adapter.causal_signal_atom_input(scene, tick)
            )
            receipt["causal_signal_atom_input_sha256"] = hashlib.sha256(
                json.dumps(causal_signal_atom_input, sort_keys=True, separators=(",", ":")).encode(
                    "utf-8"
                )
            ).hexdigest()

            input_started = time.perf_counter_ns()
            tensor_dicts = [
                self.tensor_converter.to_model_tensors(
                    scene,
                    agent_id,
                    model_args,
                    device,
                    map_cache=map_cache,
                    inference_delay=inference_delay,
                )
                for agent_id in agent_ids
            ]
            ego_base = tensor_dicts[ego_index]
            source_input_sha = _tensor_dict_sha256(ego_base)
            latent_seed = candidate_seed(24001, self.route_sha256, tick)
            latent_np = candidate_latents(latent_seed, noise_scale=1.0)
            if (
                latent_np.shape != (8, 321, 81, 4)
                or latent_np.dtype != np.float32
                or not np.all(np.isfinite(latent_np))
                or np.any(latent_np[0] != 0.0)
            ):
                raise ValueError("V26 native latent policy drifted")
            latent_row_sha = [array_sha256(row) for row in latent_np]
            if len(set(latent_row_sha)) != 8:
                raise ValueError("V26 native latent rows are not unique")
            expanded_ego = {
                key: value.expand(8, *value.shape[1:]).contiguous()
                for key, value in ego_base.items()
            }
            torch = __import__("torch")
            latent_tensor = torch.from_numpy(np.array(latent_np, copy=True)).to(
                device=device,
                dtype=expanded_ego["sampled_trajectories"].dtype,
            )
            if tuple(latent_tensor.shape) != tuple(expanded_ego["sampled_trajectories"].shape):
                raise ValueError("V26 native latent shape drifted")
            expanded_ego["sampled_trajectories"] = latent_tensor.contiguous()
            other_indices = [index for index in range(len(agent_ids)) if index != ego_index]
            combined = _cat_tensor_dicts(
                [expanded_ego, *[tensor_dicts[index] for index in other_indices]]
            )
            expanded_input_sha = _tensor_dict_sha256(expanded_ego)
            same_ego_batch_metadata = _same_ego_batch_metadata(expanded_ego)
            state_sha = hashlib.sha256(
                json.dumps(
                    {
                        "tick_index": tick,
                        "source_input_sha256": source_input_sha,
                        "ego_position_xy": np.asarray(
                            scene.ego_agent.current_position, dtype=np.float64
                        ).tolist(),
                        "ego_heading_rad": float(scene.ego_agent.current_heading),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            receipt["latency_ms"]["input_materialization"] = _elapsed_ms(input_started)

            pool_started = time.perf_counter_ns()
            calls_before = self.model_call_count
            primary_outputs = self._forward(combined)
            primary_forward_count = self.model_call_count - calls_before
            primary_prediction = _prediction_array(primary_outputs, 8 + len(other_indices))
            receipt["latency_ms"]["pool_generation"] = _elapsed_ms(pool_started)
            candidates = primary_prediction[:8, 0].copy()
            neighbors = primary_prediction[:8, 1:33].copy()
            validate_fixed_k8_candidate_tensor(candidates)
            row_sha = [array_sha256(row) for row in candidates]
            if not np.all(np.isfinite(candidates)) or len(set(row_sha)) != 8:
                raise ValueError("V26 native B8 pool is nonfinite or nondiverse")
            before_sha = array_sha256(candidates)

            causal_started = time.perf_counter_ns()
            raw_causal = self.tensor_converter.dump_step_npz(
                scene,
                map_cache,
                model_args.future_len,
                predicted_neighbor_num=32,
            )
            boundary = causal_input_receipt(
                raw_causal, source_observed_frames=_source_observed_frames(scene)
            )
            causal = boundary.causal_input
            receipt["causal_input"] = dict(boundary.receipt)
            neighbor_valid = np.any(
                np.abs(causal["neighbor_agents_past"]) > 1e-8, axis=(1, 2)
            )
            signals = np.asarray(
                self._signal_mask(candidates, causal["route_lanes"]), dtype=bool
            )
            red_cost = np.asarray(
                self._fixed_dp_red_cost(
                    candidates, causal, self.fixed_dp_repo, float(scene.dt)
                ),
                dtype=np.float64,
            )
            receipt["latency_ms"]["causal_sources"] = _elapsed_ms(causal_started)
            evaluation = self._evaluate_pool(
                candidates=candidates,
                neighbors=neighbors,
                causal=causal,
                neighbor_valid=neighbor_valid,
                signals=signals,
                red_cost=red_cost,
                causal_signal_atom_input=causal_signal_atom_input,
            )
            after_sha = array_sha256(candidates)
            if after_sha != before_sha:
                raise ValueError("V26 selector mutated the frozen candidate pool")
            if self.model_call_count != calls_before + 1:
                raise ValueError("V26 selector made a forbidden post-pool model call")
            selected_index = 0
            direct_predictions: dict[str, np.ndarray] = {ego_id: candidates[0].copy()}
            for offset, original_index in enumerate(other_indices):
                direct_predictions[agent_ids[original_index]] = primary_prediction[8 + offset, 0].copy()
            expanded_ids = [
                *[f"{ego_id}#candidate{index}" for index in range(8)],
                *[agent_ids[index] for index in other_indices],
            ]
            expanded_turns = _turn_indicators(
                primary_outputs, expanded_ids, turn_indicator_keep_bias
            )
            turns: dict[str, Any] = {}
            if expanded_turns:
                turns[ego_id] = expanded_turns[f"{ego_id}#candidate{selected_index}"]
                for original_index in other_indices:
                    agent_id = agent_ids[original_index]
                    turns[agent_id] = expanded_turns[agent_id]
            zero_call = {
                "dp_or_model_calls_after_pool": 0,
                "latent_replacements_after_pool": 0,
                "candidate_generations_after_pool": 0,
            }
            receipt.update(
                {
                    "status": "ok",
                    "state_sha256": state_sha,
                    "input_sha256": expanded_input_sha,
                    "source_input_sha256": source_input_sha,
                    "same_ego_batch_metadata": same_ego_batch_metadata,
                    "latent_seed": latent_seed,
                    "latent_shape": list(latent_np.shape),
                    "latent_dtype": str(latent_np.dtype),
                    "latent_tensor_sha256": array_sha256(latent_np),
                    "latent_row_sha256": latent_row_sha,
                    "candidate_tensor_sha256_before": before_sha,
                    "candidate_tensor_sha256_after": after_sha,
                    "candidate_row_sha256": row_sha,
                    "candidate_shape": list(candidates.shape),
                    "candidate_dtype": str(candidates.dtype),
                    "candidate_finite": True,
                    "candidate_neighbor_sha256": array_sha256(neighbors),
                    "primary_pool_model_call_count": primary_forward_count,
                    "zero_call_receipt": zero_call,
                    "real_selector_receipts": evaluation["arms"],
                    "materialized_summary": evaluation["summary"],
                    "selected_index": selected_index,
                    "selected_trajectory_sha256": row_sha[selected_index],
                    "default_output_sha256": row_sha[0],
                    "selection_flip_vs_row0": False,
                }
            )
            receipt["latency_ms"].update(evaluation["latency_ms"])
            receipt["latency_ms"]["end_to_end"] = _elapsed_ms(started_ns)
            receipt["latency_ms"]["total_planning"] = receipt["latency_ms"]["end_to_end"]
            self.primary_candidates.append(candidates.copy())
            return (direct_predictions, turns) if return_turn_indicators else direct_predictions
        except Exception as exc:
            receipt["status"] = "failed"
            receipt["failure_reason"] = str(exc)
            receipt["latency_ms"]["end_to_end"] = _elapsed_ms(started_ns)
            raise

    def _forward(self, inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        self.model_call_count += 1
        cloned = {key: value.detach().clone() for key, value in inputs.items()}
        torch = __import__("torch")
        with torch.no_grad():
            _encoded, outputs = self.model(cloned)
        return dict(outputs)

    def _profile_selector(
        self,
        *,
        arm_id: str,
        candidates: np.ndarray,
        materialized: Mapping[str, Any],
        weights: np.ndarray,
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        started_ns = time.perf_counter_ns()
        selection = self._select_candidate(
            candidates=candidates,
            materialized=materialized,
            atom_scales=self.selector_assets.atom_scales,
            weights=weights,
            eligibility_mask_name="source_valid_mask",
            simplex_nonnegative_atol=self.simplex_nonnegative_atol,
        )
        source_mask = np.asarray(selection["source_valid_mask"], dtype=np.bool_)
        tie_set, margin = _tie_and_margin(selection.get("scores"), source_mask)
        result = {
            "status": str(selection["status"]),
            "failure_reason": selection.get("failure_reason"),
            "selected_index": selection.get("selected_index"),
            "selected_row_sha256": (
                None
                if selection.get("selected_index") is None
                else array_sha256(candidates[int(selection["selected_index"])])
            ),
            "scores": (
                None
                if selection.get("scores") is None
                else np.asarray(selection["scores"], dtype=np.float64).tolist()
            ),
            "physical_feasible_mask": np.asarray(
                selection["physical_feasible_mask"], dtype=np.bool_
            ).tolist(),
            "source_valid_mask": source_mask.tolist(),
            "weights_sha256": array_sha256(np.asarray(weights[:9], dtype=np.float64)),
            "scoring_weights_sha256": array_sha256(np.asarray(weights, dtype=np.float64)),
            "weight_parameter_sha256": (
                self.selector_assets.static9d_weights_sha256
                if arm_id == "Static9D"
                else self.selector_assets.scene9d_theta_sha256
                if arm_id == "Scene9D"
                else self.selector_assets.static14d_weights_sha256
                if arm_id == "Static14D"
                else self.selector_assets.scene14d_theta_sha256
            ),
            "selector_latency_ms": _elapsed_ms(started_ns),
            "eligible_count": int(np.count_nonzero(source_mask)),
            "margin_best_vs_runner_up": margin,
            "exact_tie_set": tie_set,
            "tie_break_contract": "lowest_eligible_candidate_index",
            "atom_set": ATOM_SET_BY_ARM[arm_id],
            "active_atom_indices": ACTIVE_ATOM_INDICES_BY_ARM[arm_id],
            "simplex_nonnegative_atol": self.simplex_nonnegative_atol,
        }
        if context is not None:
            result["context"] = dict(context)
        return result

    def _evaluate_pool(
        self,
        *,
        candidates: np.ndarray,
        neighbors: np.ndarray,
        causal: Mapping[str, Any],
        neighbor_valid: np.ndarray,
        signals: np.ndarray,
        red_cost: np.ndarray,
        causal_signal_atom_input: Mapping[str, Any],
    ) -> dict[str, Any]:
        before = array_sha256(candidates)
        phase_receipt: dict[str, Any] = {}
        atom_started = time.perf_counter_ns()
        materialized = materialize_canonical_14d(
            candidates=candidates,
            causal_input=causal,
            neighbor_predictions=neighbors,
            neighbor_valid_mask=neighbor_valid,
            signal_mask=signals,
            planned_red_light_cost=red_cost,
            causal_signal_atom_input=causal_signal_atom_input,
            dt=0.1,
            eligibility_policy="v22_source_valid",
            phase_receipt=phase_receipt,
        )
        atom_ms = _elapsed_ms(atom_started)
        if array_sha256(candidates) != before:
            raise ValueError("V26 atom materialization mutated the frozen pool")
        context_started = time.perf_counter_ns()
        context_record = build_v25_raw_context(
            causal_input=causal,
            candidates=candidates,
            source_valid_mask=np.asarray(materialized["source_valid_mask"], dtype=bool),
            causal_signal_atom_input=causal_signal_atom_input,
            v2i_signal_timing=None,
        )
        context = {
            "raw_context": context_record.as_dict(),
            "source_complete": {
                name: bool(value)
                for name, value in zip(RAW_FEATURE_NAMES, context_record.source_complete)
            },
            "source_receipt": dict(context_record.source_receipt),
        }
        context_ms = _elapsed_ms(context_started)
        weights_started = time.perf_counter_ns()
        static9 = np.zeros(14, dtype=np.float64)
        static9[:9] = np.asarray(self.selector_assets.static9d_weights, dtype=np.float64)
        scene9 = np.zeros(14, dtype=np.float64)
        scene9[:9] = np.asarray(self.selector_assets.scene9d_weights(context), dtype=np.float64)
        static14 = np.asarray(self.selector_assets.static14d_weights, dtype=np.float64)
        scene14_receipt = self.selector_assets.scene14d_weight_provider(context)
        scene14 = np.asarray(scene14_receipt["weights"], dtype=np.float64)
        weights_ms = _elapsed_ms(weights_started)
        arms = {
            OPERATIONAL_ARM: {
                "status": "ok",
                "failure_reason": None,
                "selected_index": 0,
                "selected_row_sha256": array_sha256(candidates[0]),
                "scores": None,
                "physical_feasible_mask": np.asarray(
                    materialized["physical_feasible_mask"], dtype=np.bool_
                ).tolist(),
                "source_valid_mask": np.asarray(
                    materialized["source_valid_mask"], dtype=np.bool_
                ).tolist(),
                "weights_sha256": None,
                "scoring_weights_sha256": None,
                "weight_parameter_sha256": None,
                "selector_latency_ms": None,
                "eligible_count": int(
                    np.count_nonzero(materialized["source_valid_mask"])
                ),
                "margin_best_vs_runner_up": None,
                "exact_tie_set": [0],
                "tie_break_contract": "frozen_row0",
                "atom_set": ATOM_SET_BY_ARM[OPERATIONAL_ARM],
                "active_atom_indices": ACTIVE_ATOM_INDICES_BY_ARM[OPERATIONAL_ARM],
            },
            "Static9D": self._profile_selector(
                arm_id="Static9D", candidates=candidates, materialized=materialized, weights=static9
            ),
            "Scene9D": self._profile_selector(
                arm_id="Scene9D", candidates=candidates, materialized=materialized, weights=scene9, context=context
            ),
            "Static14D": self._profile_selector(
                arm_id="Static14D", candidates=candidates, materialized=materialized, weights=static14
            ),
            "Scene14D": self._profile_selector(
                arm_id="Scene14D", candidates=candidates, materialized=materialized, weights=scene14, context=context
            ),
        }
        if tuple(arms) != PROFILE_ARMS or array_sha256(candidates) != before:
            raise ValueError("V26 five-arm same-pool selector inventory drifted")
        return {
            "arms": arms,
            "latency_ms": {
                "atoms": atom_ms,
                "context": context_ms,
                "weights": weights_ms,
                "selector_incremental": float(
                    sum(row.get("selector_latency_ms") or 0.0 for row in arms.values())
                ),
            },
            "summary": {
                "atom_matrix": np.asarray(materialized["atom_matrix"], dtype=np.float64).tolist(),
                "atom_matrix_sha256": array_sha256(
                    np.asarray(materialized["atom_matrix"], dtype=np.float64)
                ),
                "physical_feasible_mask": np.asarray(
                    materialized["physical_feasible_mask"], dtype=np.bool_
                ).tolist(),
                "source_valid_mask": np.asarray(
                    materialized["source_valid_mask"], dtype=np.bool_
                ).tolist(),
                "candidate_reasons": [list(value) for value in materialized["candidate_reasons"]],
                "canonical_eligible": bool(materialized["canonical_eligible"]),
                "exclusion_reason": materialized.get("exclusion_reason"),
                "context": context,
                "scene_weights": scene14.tolist(),
                "scene_weights_sha256": array_sha256(scene14),
                "scene14d_weight_receipt": {
                    key: value for key, value in scene14_receipt.items() if key != "weights"
                },
                "atom_materialization_phase_receipt": phase_receipt,
                "simplex_nonnegative_atol": self.simplex_nonnegative_atol,
            },
        }


def run_v26_native_same_ego_b8_replay(
    *,
    config: Mapping[str, Any],
    model: Any,
    model_args: Any,
    tensor_converter: Any,
    replay: Any,
    builder_type: Any,
    route_type: Any,
    fixed_dp_repo: Path,
    selector_assets: Any,
    signal_adapter: Any,
    integration_boundary: Mapping[str, Any],
    device: str,
    max_ticks: int,
    scratch_parent: Path,
    on_completed_unit: Callable[[Mapping[str, Any], V26NativeSameEgoB8Callback], None],
) -> tuple[list[dict[str, Any]], V26NativeSameEgoB8Callback, dict[str, Any]]:
    """Run only the V26 callback through the narrow fixed-DP replay bridge."""

    from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import patched_native_replay

    builder = builder_type(str(config["map"]["path"]))
    route_spec = config["routes"][0]
    route = route_type.load(Path(route_spec["path"]))
    route_ids = list(route.route_lanelet_ids or ())
    if not route_ids:
        raise ValueError("V26 native runner route is unresolved")
    spawn = replay.SpawnConfig(**dict(config["spawn_config"]))
    spawn.max_steps = int(max_ticks)
    spawn.validate()
    state = V26NativeHookState()
    callback = V26NativeSameEgoB8Callback(
        model=model,
        model_args=model_args,
        tensor_converter=tensor_converter,
        fixed_dp_repo=fixed_dp_repo,
        fixed_config=config["fixed_dp"],
        route_sha256=str(route_spec["sha256"]),
        builder=builder,
        route_ids=route_ids,
        state=state,
        max_ticks=max_ticks,
        selector_assets=selector_assets,
        signal_adapter=signal_adapter,
        integration_boundary=integration_boundary,
    )

    def after_tracker(receipt: dict[str, Any], _scene: Any) -> None:
        on_completed_unit(receipt, callback)

    scratch = Path(tempfile.mkdtemp(prefix=".v26_native_acquisition.", dir=str(scratch_parent)))
    try:
        with patched_native_replay(
            replay,
            callback,
            state,
            dp_repo=fixed_dp_repo,
            expected_source_hashes=config["fixed_dp"]["native_source_sha256"],
            after_tracker=after_tracker,
        ):
            try:
                native_result = replay.run_route_replay(
                    model=model,
                    model_args=model_args,
                    builder=builder,
                    route=route,
                    output_dir=scratch,
                    spawn_config=spawn,
                    device=device,
                )
            except V26RequestedStateCountReached:
                native_result = {"reason": "requested_state_count_reached", "goal_reached": False}
            except Exception as exc:
                native_result = {
                    "reason": "retained_typed_runtime_failure",
                    "goal_reached": False,
                    "failure_class": type(exc).__name__,
                    "failure_reason": str(exc),
                }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return state.receipts, callback, dict(native_result)
