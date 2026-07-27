"""Run the authorized V25 fair nonholdout selector and closed-loop qualification.

The contract and its independent review must already be sealed.  This script
uses development/nonholdout state only, never reads Fresh/B4 outcome values,
does not train, and never writes a scientific or continuation CAS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v21_native import (  # noqa: E402
    array_sha256,
    candidate_latents,
    candidate_seed,
    causal_input_receipt,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    CONTEXT_SCHEMA_VERSION,
    RAW_FEATURE_NAMES,
    build_v25_raw_context,
)
from camp_core.integrations.diffusion_planner_v25_evaluation_v2 import (  # noqa: E402
    summarize_run_v2,
)
from camp_core.integrations.diffusion_planner_v25_fair_nonholdout import (  # noqa: E402
    ARMS,
    ATOL,
    FIXED_DP_HEAD,
    GENERATOR_NAME,
    RTOL,
    STATE_COUNT,
    TICKS_PER_CLOSED_LOOP_ARM,
    canonical_bytes,
    canonical_sha256,
    validate_fair_nonholdout_contract,
    validate_zero_call_receipt,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    TRAINED_SIMPLEX_NONNEGATIVE_ATOL,
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    build_no_signal_causal_atom_input,
    build_runtime_no_signal_receipt,
    build_semantic_clone_payload,
    canonical_json_sha256,
    validate_no_signal_chain,
)
from camp_core.integrations.diffusion_planner_v26_target_bounded_surface import (  # noqa: E402
    build_target_bounded_tick_receipt,
    validate_production_surface_options,
)
from scripts.integrations.materialize_diffusion_planner_v25_evaluation_v2 import (  # noqa: E402
    _load_root_bound_geometry,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    NativeHookState,
    _capture_post_safety,
    _capture_pre_safety,
    _cat_tensor_dicts,
    _install_fixed_dp_annotation_compatibility,
    _prediction_array,
    _source_observed_frames,
    _turn_indicators,
    patched_native_replay,
)


class _RequestedStateCountReached(RuntimeError):
    pass


def _same_ego_batch_metadata(tensors: Mapping[str, Any]) -> dict[str, Any]:
    """Describe, but never materialize, the V26 same-ego B8 model input."""

    torch = sys.modules["torch"]
    metadata: dict[str, dict[str, Any]] = {}
    nonlatent_rows_identical = True
    for key in sorted(tensors):
        value = tensors[key]
        if getattr(value, "ndim", 0) < 1 or int(value.shape[0]) != 8:
            raise ValueError("fair same-ego B8 input batch drifted")
        floating = bool(value.is_floating_point() or value.is_complex())
        finite = bool(torch.isfinite(value).all().item()) if floating else True
        if key != "sampled_trajectories":
            nonlatent_rows_identical = nonlatent_rows_identical and bool(
                torch.equal(value, value[0:1].expand_as(value))
            )
        metadata[key] = {
            "shape": [int(size) for size in value.shape],
            "dtype": str(value.dtype),
            "finite": finite,
        }
    if not nonlatent_rows_identical:
        raise ValueError("fair same-ego nonlatent input rows drifted")
    return {
        "same_ego_batch_size": 8,
        "nonlatent_rows_identical": True,
        "tensor_metadata": metadata,
    }


class _FairPredictBatch:
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
        route_ids: list[int],
        replay: Any,
        assets: Any,
        state: NativeHookState,
        max_ticks: int,
        operational_arm: str,
        evaluate_all_arms: bool,
        adaptation_diagnostics: bool,
        causal_signal_chain: Mapping[str, Any] | None,
        production_surface_id: str | None = None,
        production_surface_options: Mapping[str, Any] | None = None,
        scene_adapter: Any | None = None,
        latent_provider: Callable[[int], np.ndarray] | None = None,
    ) -> None:
        self.model = model
        self.model_args = model_args
        self.tensor_converter = tensor_converter
        self.fixed_dp_repo = fixed_dp_repo
        self.fixed_config = dict(fixed_config)
        self.route_sha256 = route_sha256
        self.builder = builder
        self.route_ids = route_ids
        self.replay = replay
        self.assets = assets
        self.state = state
        self.max_ticks = max_ticks
        self.operational_arm = operational_arm
        if (production_surface_id is None) != (production_surface_options is None):
            raise ValueError("production surface id/options must be supplied together")
        if production_surface_id is None:
            normalized_production_surface_options = None
        else:
            normalized_production_surface_options = validate_production_surface_options(
                production_surface_id=production_surface_id,
                options=production_surface_options,
            )
            if (
                evaluate_all_arms
                is not normalized_production_surface_options["evaluate_all_arms"]
                or adaptation_diagnostics
                is not normalized_production_surface_options["adaptation_diagnostics"]
            ):
                raise ValueError(
                    "V26 production options must exactly bind callback execution flags"
                )
        self.evaluate_all_arms = evaluate_all_arms
        self.adaptation_diagnostics = adaptation_diagnostics
        self.production_surface_id = production_surface_id
        self.production_surface_options = normalized_production_surface_options
        self.causal_signal_chain = (
            None if causal_signal_chain is None else dict(causal_signal_chain)
        )
        self.scene_adapter = scene_adapter
        self.latent_provider = latent_provider
        self.primary_candidates: list[np.ndarray] = []
        self.sequential_candidates: list[np.ndarray] = []
        self.primary_neighbors: list[np.ndarray] = []
        self.sequential_neighbors: list[np.ndarray] = []
        self.primary_atoms: list[np.ndarray] = []
        self.primary_causal_inputs: list[dict[str, np.ndarray]] = []
        self.sequential_atoms: list[np.ndarray] = []
        self.primary_source_masks: list[np.ndarray] = []
        self.sequential_source_masks: list[np.ndarray] = []
        self.primary_physical_masks: list[np.ndarray] = []
        self.sequential_physical_masks: list[np.ndarray] = []
        self.model_call_count = 0

        from camp_core.integrations.diffusion_planner_causal_atoms import (
            materialization_phase_receipt_not_available,
            materialize_canonical_14d,
            validate_fixed_k8_candidate_tensor,
        )
        from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (
            _fixed_dp_red_cost,
            candidate_signal_source_available_mask,
        )
        from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (
            select_camp_candidate,
        )

        self.materialize = materialize_canonical_14d
        self.materialization_phase_receipt_not_available = (
            materialization_phase_receipt_not_available
        )
        self.validate_candidates = validate_fixed_k8_candidate_tensor
        self.red_cost = _fixed_dp_red_cost
        self.signal_mask = candidate_signal_source_available_mask
        self.select_candidate = select_camp_candidate

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
            raise _RequestedStateCountReached
        if model is not self.model or model_args is not self.model_args:
            raise ValueError("fair validation model binding drifted")
        started_ns = time.perf_counter_ns()
        tick = len(self.state.receipts)
        receipt: dict[str, Any] = {
            "tick_index": tick,
            "status": "running",
            "_planning_started_ns": started_ns,
            "latency_ms": {},
            "generator_name": GENERATOR_NAME,
        }
        self.state.receipts.append(receipt)
        causal_signal_atom_input = None
        if self.scene_adapter is not None:
            forward_route_ids = self.builder.select_route_segment_indices(
                self.route_ids,
                scene.ego_agent.current_position,
                max_segments=25,
            ) or self.route_ids[:25]
            forward_route_ids = [
                lanelet_id
                for lanelet_id in forward_route_ids
                if lanelet_id in self.builder._cache
            ][:25]
            self.scene_adapter.bind_runtime_lanelet_ids(
                route_lanelet_ids=forward_route_ids,
                map_lanelet_ids=self.builder._last_map_data_ids,
            )
            receipt["controlled_scene"] = dict(self.scene_adapter(scene, tick))
            receipt["controlled_scene"]["model_input_cache"] = dict(
                self.scene_adapter.sync_model_input_map_cache(
                    scene, map_cache, tick
                )
            )
            causal_signal_atom_input = dict(
                self.scene_adapter.causal_signal_atom_input(scene, tick)
            )
            receipt["causal_signal_atom_input_sha256"] = canonical_sha256(
                causal_signal_atom_input
            )
        _capture_pre_safety(
            receipt,
            scene,
            self.builder,
            self.route_ids,
            self.replay,
            certified_signal_atom_input=causal_signal_atom_input,
        )
        if not agent_ids or scene.ego_agent_id not in agent_ids:
            raise ValueError("fair validation requires ego in agent batch")
        ego_id = scene.ego_agent_id
        ego_index = agent_ids.index(ego_id)
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
        latent_np = (
            candidate_latents(latent_seed, noise_scale=1.0)
            if self.latent_provider is None
            else np.asarray(self.latent_provider(tick))
        )
        if (
            latent_np.shape != (8, 321, 81, 4)
            or latent_np.dtype != np.float32
            or not np.all(np.isfinite(latent_np))
        ):
            raise ValueError("fair same-ego latent contract drifted")
        latent_row_sha = [array_sha256(row) for row in latent_np]
        if len(set(latent_row_sha)) != 8 or np.any(latent_np[0] != 0.0):
            raise ValueError("fair same-ego latent rows are not unique row0-zero K8")
        expanded_ego = {
            key: value.expand(8, *value.shape[1:]).contiguous()
            for key, value in ego_base.items()
        }
        torch = sys.modules["torch"]
        latent_tensor = torch.from_numpy(np.array(latent_np, copy=True)).to(
            device=device,
            dtype=expanded_ego["sampled_trajectories"].dtype,
        )
        if tuple(latent_tensor.shape) != tuple(
            expanded_ego["sampled_trajectories"].shape
        ):
            raise ValueError("fair same-ego latent shape drifted")
        expanded_ego["sampled_trajectories"] = latent_tensor.contiguous()
        other_indices = [index for index in range(len(agent_ids)) if index != ego_index]
        combined = _cat_tensor_dicts(
            [expanded_ego, *[tensor_dicts[index] for index in other_indices]]
        )
        expanded_input_sha = _tensor_dict_sha256(expanded_ego)
        same_ego_batch_metadata = _same_ego_batch_metadata(expanded_ego)
        state_sha = canonical_sha256(
            {
                "tick_index": tick,
                "source_input_sha256": source_input_sha,
                "ego_position_xy": np.asarray(
                    scene.ego_agent.current_position, dtype=np.float64
                ).tolist(),
                "ego_heading_rad": float(scene.ego_agent.current_heading),
                "ego_velocity_xy": np.asarray(
                    scene.ego_agent.current_velocity, dtype=np.float64
                ).tolist(),
            }
        )
        receipt["latency_ms"]["input_materialization"] = _ms(input_started)

        rng_before = _rng_sha256(torch)
        pool_started = time.perf_counter_ns()
        model_calls_before_primary = self.model_call_count
        primary_outputs = self._forward(combined)
        primary_forward_count = self.model_call_count - model_calls_before_primary
        primary_prediction = _prediction_array(
            primary_outputs, 8 + len(other_indices)
        )
        receipt["latency_ms"]["pool_generation"] = _ms(pool_started)
        candidates = primary_prediction[:8, 0].copy()
        neighbors = primary_prediction[:8, 1:33].copy()
        self.validate_candidates(candidates)
        row_sha = [array_sha256(row) for row in candidates]
        if (
            not np.all(np.isfinite(candidates))
            or len(set(row_sha)) != 8
        ):
            raise ValueError("fair batch8 pool is nonfinite or nondiverse")

        repeat_equal = None
        repeat_max_error = None
        sequential = None
        sequential_neighbors = None
        adaptation_latency_ms = None
        calls_before_adaptation = self.model_call_count
        if self.adaptation_diagnostics:
            adaptation_started = time.perf_counter_ns()
            repeat_prediction = _prediction_array(
                self._forward(combined), 8 + len(other_indices)
            )
            repeat_equal = bool(
                np.array_equal(primary_prediction[:8], repeat_prediction[:8])
            )
            repeat_max_error = float(
                np.max(
                    np.abs(
                        primary_prediction[:8].astype(np.float64)
                        - repeat_prediction[:8].astype(np.float64)
                    )
                )
            )
            sequential_rows = []
            sequential_neighbor_rows = []
            for index in range(8):
                row_input = {
                    key: value[index : index + 1].contiguous()
                    for key, value in expanded_ego.items()
                }
                row_prediction = _prediction_array(self._forward(row_input), 1)
                sequential_rows.append(row_prediction[0, 0])
                sequential_neighbor_rows.append(row_prediction[0, 1:33])
            sequential = np.stack(sequential_rows).astype(np.float32, copy=False)
            sequential_neighbors = np.stack(sequential_neighbor_rows).astype(
                np.float32, copy=False
            )
            adaptation_latency_ms = _ms(adaptation_started)
        calls_after_adaptation = self.model_call_count
        rng_after = _rng_sha256(torch)
        if rng_before != rng_after:
            raise ValueError("fair pool generation changed global RNG state")

        candidate_sha = array_sha256(candidates)
        pool_id = canonical_sha256(
            {
                "generator": GENERATOR_NAME,
                "input_sha256": expanded_input_sha,
                "model_sha256": self.fixed_config["checkpoint"]["sha256"],
                "candidate_tensor_sha256": candidate_sha,
                "tick_index": tick,
            }
        )
        forward_id = canonical_sha256(
            {
                "pool_id": pool_id,
                "model_call_ordinal": calls_before_adaptation + 1,
                "state_sha256": state_sha,
            }
        )
        # The authoritative pool is frozen only after all adaptation-only model
        # calls.  From this point through all real selectors, calls must remain 0.
        calls_at_pool_freeze = self.model_call_count
        before_sha = array_sha256(candidates)

        needs_selector_inputs = (
            self.evaluate_all_arms
            or self.operational_arm in ("Static14D", "Scene14D")
        )
        causal = None
        neighbor_valid = None
        signals = None
        red_cost = None
        if needs_selector_inputs:
            causal_started = time.perf_counter_ns()
            raw_causal = self.tensor_converter.dump_step_npz(
                scene,
                map_cache,
                model_args.future_len,
                predicted_neighbor_num=32,
            )
            boundary = causal_input_receipt(
                raw_causal,
                source_observed_frames=_source_observed_frames(scene),
            )
            causal = boundary.causal_input
            receipt["causal_input"] = dict(boundary.receipt)
            neighbor_valid = np.any(
                np.abs(causal["neighbor_agents_past"]) > 1e-8, axis=(1, 2)
            )
            signals = np.asarray(
                self.signal_mask(candidates, causal["route_lanes"]), dtype=bool
            )
            red_cost = np.asarray(
                self.red_cost(
                    candidates,
                    causal,
                    self.fixed_dp_repo,
                    float(scene.dt),
                ),
                dtype=np.float64,
            )
            if causal_signal_atom_input is None:
                if self.causal_signal_chain is None:
                    raise ValueError(
                        "fair selector requires a certified signal source"
                    )
                runtime_signal_receipt = build_runtime_no_signal_receipt(
                    self.causal_signal_chain,
                    scenario_id=str(self.causal_signal_chain["scenario_id"]),
                    tick_index=tick,
                    decision_time_s=float(tick) * float(scene.dt),
                )
                causal_signal_atom_input = build_no_signal_causal_atom_input(
                    self.causal_signal_chain,
                    runtime_signal_receipt,
                )
                receipt["causal_signal_atom_input_sha256"] = canonical_sha256(
                    causal_signal_atom_input
                )
            receipt["latency_ms"]["causal_sources"] = _ms(causal_started)
        else:
            causal_signal_atom_input = None
            receipt["latency_ms"]["causal_sources"] = None
        primary_eval = self._evaluate_pool(
            candidates=candidates,
            neighbors=neighbors,
            causal=causal,
            neighbor_valid=neighbor_valid,
            signals=signals,
            red_cost=red_cost,
            causal_signal_atom_input=causal_signal_atom_input,
            evaluate_arms=(
                list(ARMS) if self.evaluate_all_arms else [self.operational_arm]
            ),
        )
        if self.model_call_count != calls_at_pool_freeze:
            raise ValueError("real selector made a forbidden model call")
        after_sha = array_sha256(candidates)
        zero_call = validate_zero_call_receipt(
            {
                "pool_id": pool_id,
                "candidate_tensor_sha256_before": before_sha,
                "candidate_tensor_sha256_after": after_sha,
                "input_sha256": expanded_input_sha,
                "model_sha256": self.fixed_config["checkpoint"]["sha256"],
                "checkpoint_sha256": self.fixed_config["checkpoint"]["sha256"],
                "forward_invocation_id": forward_id,
                "dp_or_model_calls_after_pool": 0,
                "latent_replacements_after_pool": 0,
                "candidate_generations_after_pool": 0,
            }
        )

        adaptation = None
        if self.adaptation_diagnostics:
            assert sequential is not None and sequential_neighbors is not None
            assert causal is not None
            sequential_signals = np.asarray(
                self.signal_mask(sequential, causal["route_lanes"]), dtype=bool
            )
            sequential_red = np.asarray(
                self.red_cost(
                    sequential,
                    causal,
                    self.fixed_dp_repo,
                    float(scene.dt),
                ),
                dtype=np.float64,
            )
            sequential_eval = self._evaluate_pool(
                candidates=sequential,
                neighbors=sequential_neighbors,
                causal=causal,
                neighbor_valid=neighbor_valid,
                signals=sequential_signals,
                red_cost=sequential_red,
                causal_signal_atom_input=causal_signal_atom_input,
                evaluate_arms=list(ARMS),
            )
            trajectory_errors = _per_row_max_error(candidates, sequential)
            neighbor_errors = _per_row_max_error(neighbors, sequential_neighbors)
            trajectory_ok = [
                bool(np.allclose(candidates[index], sequential[index], atol=ATOL, rtol=RTOL))
                for index in range(8)
            ]
            neighbor_ok = [
                bool(
                    np.allclose(
                        neighbors[index],
                        sequential_neighbors[index],
                        atol=ATOL,
                        rtol=RTOL,
                    )
                )
                for index in range(8)
            ]
            mask_equal = bool(
                np.array_equal(
                    primary_eval["materialized"]["source_valid_mask"],
                    sequential_eval["materialized"]["source_valid_mask"],
                )
                and np.array_equal(
                    primary_eval["materialized"]["physical_feasible_mask"],
                    sequential_eval["materialized"]["physical_feasible_mask"],
                )
            )
            selection_equal = {
                arm: (
                    primary_eval["arms"][arm].get("status")
                    == sequential_eval["arms"][arm].get("status")
                    and primary_eval["arms"][arm].get("selected_index")
                    == sequential_eval["arms"][arm].get("selected_index")
                )
                for arm in ("Static14D", "Scene14D")
            }
            adaptation = {
                "diagnostic_model_call_count": (
                    calls_after_adaptation - calls_before_adaptation
                ),
                "repeat_exact_equal": repeat_equal,
                "repeat_max_abs_error": repeat_max_error,
                "trajectory_per_row_max_abs_error": trajectory_errors,
                "neighbor_per_row_max_abs_error": neighbor_errors,
                "trajectory_within_tolerance": trajectory_ok,
                "neighbor_within_tolerance": neighbor_ok,
                "source_and_eligibility_masks_equal": mask_equal,
                "selected_index_equal": selection_equal,
                "substantive_drift": bool(
                    not repeat_equal
                    or not all(trajectory_ok)
                    or not all(neighbor_ok)
                    or not mask_equal
                    or not all(selection_equal.values())
                ),
                "adaptation_latency_ms": adaptation_latency_ms,
                "sequential": sequential_eval["summary"],
            }
            self.sequential_candidates.append(sequential.copy())
            self.sequential_neighbors.append(sequential_neighbors.copy())
            self.sequential_atoms.append(
                np.asarray(
                    sequential_eval["materialized"]["atom_matrix"], dtype=np.float64
                ).copy()
            )
            self.sequential_source_masks.append(
                np.asarray(
                    sequential_eval["materialized"]["source_valid_mask"], dtype=np.bool_
                ).copy()
            )
            self.sequential_physical_masks.append(
                np.asarray(
                    sequential_eval["materialized"]["physical_feasible_mask"],
                    dtype=np.bool_,
                ).copy()
            )

        selected = primary_eval["arms"][self.operational_arm]
        if selected.get("status") != "ok":
            failure_fields = {
                "status": "typed_selector_failure",
                "failure_class": "selector_functional_failure",
                "failure_reason": selected.get("failure_reason"),
                "state_sha256": state_sha,
                "input_sha256": expanded_input_sha,
                "source_input_sha256": source_input_sha,
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
                "candidate_finite": bool(np.all(np.isfinite(candidates))),
                "candidate_neighbor_sha256": array_sha256(neighbors),
                "pool_id": pool_id,
                "forward_invocation_id": forward_id,
                "primary_pool_model_call_count": primary_forward_count,
                "zero_call_receipt": zero_call,
                "real_selector_receipts": primary_eval["arms"],
            }
            v26_receipt = self._build_v26_production_receipt(
                tick_index=tick,
                state_sha256=state_sha,
                candidate_pool_sha256_before=before_sha,
                candidate_pool_sha256_after=after_sha,
                primary_forward_count=primary_forward_count,
                sequential_forward_count=(
                    calls_after_adaptation - calls_before_adaptation
                ),
                zero_call_receipt=zero_call,
                selector_receipt=selected,
                simulator_selected_row_sha256=None,
                materialization_phase_receipt=primary_eval["summary"].get(
                    "atom_materialization_phase_receipt"
                ),
            )
            if v26_receipt is not None:
                failure_fields["v26_production_surface_receipt"] = v26_receipt
            receipt.update(failure_fields)
            raise RuntimeError(
                f"{self.operational_arm} selector failed: "
                f"{selected.get('failure_reason')}"
            )
        selected_index = int(selected["selected_index"])
        direct_predictions: dict[str, np.ndarray] = {
            ego_id: candidates[selected_index].copy()
        }
        for offset, original_index in enumerate(other_indices):
            direct_predictions[agent_ids[original_index]] = primary_prediction[
                8 + offset, 0
            ].copy()
        expanded_ids = [
            *[f"{ego_id}#candidate{index}" for index in range(8)],
            *[agent_ids[index] for index in other_indices],
        ]
        expanded_turns = _turn_indicators(
            primary_outputs, expanded_ids, turn_indicator_keep_bias
        )
        turns = {}
        if expanded_turns:
            turns[ego_id] = expanded_turns[f"{ego_id}#candidate{selected_index}"]
            for original_index in other_indices:
                other_id = agent_ids[original_index]
                turns[other_id] = expanded_turns[other_id]

        v26_receipt = self._build_v26_production_receipt(
            tick_index=tick,
            state_sha256=state_sha,
            candidate_pool_sha256_before=before_sha,
            candidate_pool_sha256_after=after_sha,
            primary_forward_count=primary_forward_count,
            sequential_forward_count=(
                calls_after_adaptation - calls_before_adaptation
            ),
            zero_call_receipt=zero_call,
            selector_receipt=selected,
            simulator_selected_row_sha256=array_sha256(direct_predictions[ego_id]),
            materialization_phase_receipt=primary_eval["summary"].get(
                "atom_materialization_phase_receipt"
            ),
        )

        success_fields = {
                "status": "ok",
                "state_sha256": state_sha,
                "input_sha256": expanded_input_sha,
                "source_input_sha256": source_input_sha,
                "same_ego_batch_metadata": same_ego_batch_metadata,
                "candidate_seed": candidate_seed(24001, self.route_sha256, tick),
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
                "candidate_finite": bool(np.all(np.isfinite(candidates))),
                "candidate_neighbor_sha256": array_sha256(neighbors),
                "candidate_neighbor_shape": list(neighbors.shape),
                "candidate_neighbor_dtype": str(neighbors.dtype),
                "pool_id": pool_id,
                "forward_invocation_id": forward_id,
                "primary_pool_model_call_count": primary_forward_count,
                "zero_call_receipt": zero_call,
                "real_selector_receipts": primary_eval["arms"],
                "materialized_summary": primary_eval["summary"],
                "adaptation": adaptation,
                "selected_index": selected_index,
                "selected_trajectory_sha256": row_sha[selected_index],
                "default_output_sha256": row_sha[0],
                "selection_flip_vs_row0": selected_index != 0,
                "global_rng_sha256_before": rng_before,
                "global_rng_sha256_after": rng_after,
            }
        if v26_receipt is not None:
            success_fields["v26_production_surface_receipt"] = v26_receipt
        receipt.update(success_fields)
        for name, value in primary_eval["latency_ms"].items():
            receipt["latency_ms"][name] = value
        receipt["latency_ms"]["end_to_end"] = _ms(started_ns)
        receipt["latency_ms"]["total_planning"] = receipt["latency_ms"][
            "end_to_end"
        ]
        receipt["action_available_ns"] = time.perf_counter_ns()
        self.primary_candidates.append(candidates.copy())
        self.primary_neighbors.append(neighbors.copy())
        if primary_eval["materialized"] is not None:
            assert causal is not None
            self.primary_causal_inputs.append(
                {
                    key: np.asarray(value).copy()
                    for key, value in causal.items()
                }
            )
            self.primary_atoms.append(
                np.asarray(
                    primary_eval["materialized"]["atom_matrix"], dtype=np.float64
                ).copy()
            )
            self.primary_source_masks.append(
                np.asarray(
                    primary_eval["materialized"]["source_valid_mask"], dtype=np.bool_
                ).copy()
            )
            self.primary_physical_masks.append(
                np.asarray(
                    primary_eval["materialized"]["physical_feasible_mask"],
                    dtype=np.bool_,
                ).copy()
            )
        return (
            (direct_predictions, turns)
            if return_turn_indicators
            else direct_predictions
        )

    def _forward(self, inputs: Mapping[str, Any]) -> Mapping[str, Any]:
        self.model_call_count += 1
        cloned = {key: value.detach().clone() for key, value in inputs.items()}
        torch = sys.modules["torch"]
        with torch.no_grad():
            _encoded, outputs = self.model(cloned)
        if type(outputs) is not dict:
            outputs = dict(outputs)
        return outputs

    def _build_v26_production_receipt(
        self,
        *,
        tick_index: int,
        state_sha256: str,
        candidate_pool_sha256_before: str,
        candidate_pool_sha256_after: str,
        primary_forward_count: int,
        sequential_forward_count: int,
        zero_call_receipt: Mapping[str, Any],
        selector_receipt: Mapping[str, Any],
        simulator_selected_row_sha256: str | None,
        materialization_phase_receipt: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        if self.production_surface_id is None:
            return None
        assert self.production_surface_options is not None
        return build_target_bounded_tick_receipt(
            production_surface_id=self.production_surface_id,
            options=self.production_surface_options,
            operational_arm=self.operational_arm,
            tick_index=tick_index,
            state_sha256=state_sha256,
            candidate_pool_sha256_before=candidate_pool_sha256_before,
            candidate_pool_sha256_after=candidate_pool_sha256_after,
            primary_forward_count=primary_forward_count,
            sequential_forward_count=sequential_forward_count,
            zero_call_receipt=zero_call_receipt,
            selector_receipt=selector_receipt,
            simulator_selected_row_sha256=simulator_selected_row_sha256,
            materialization_phase_receipt=materialization_phase_receipt,
        )

    def _evaluate_pool(
        self,
        *,
        candidates: np.ndarray,
        neighbors: np.ndarray,
        causal: Mapping[str, Any] | None,
        neighbor_valid: np.ndarray | None,
        signals: np.ndarray | None,
        red_cost: np.ndarray | None,
        causal_signal_atom_input: Mapping[str, Any] | None,
        evaluate_arms: list[str],
    ) -> dict[str, Any]:
        before = array_sha256(candidates)
        selector_arms = [
            arm for arm in evaluate_arms if arm in ("Static14D", "Scene14D")
        ]
        if not selector_arms:
            if evaluate_arms != ["pool_matched_candidate0"]:
                raise ValueError("baseline-only selector arm inventory drifted")
            summary = {
                "atom_matrix": None,
                "atom_matrix_sha256": None,
                "physical_feasible_mask": None,
                "source_valid_mask": None,
                "candidate_reasons": None,
                "canonical_eligible": None,
                "exclusion_reason": None,
                "context": None,
                "scene_weights": None,
                "scene_weights_sha256": None,
                "uncalled_stages": [
                    "atoms",
                    "context",
                    "weights",
                    "selector_incremental",
                ],
            }
            if self.production_surface_id is not None:
                summary["atom_materialization_phase_receipt"] = (
                    self.materialization_phase_receipt_not_available()
                )
            return {
                "materialized": None,
                "arms": {
                    "pool_matched_candidate0": {
                        "status": "ok",
                        "selected_index": 0,
                        "selected_row_sha256": array_sha256(candidates[0]),
                        "scores": None,
                        "physical_feasible_mask": None,
                        "source_valid_mask": None,
                        "baseline_rule": "frozen_row0",
                        "selector_latency_ms": None,
                    }
                },
                "latency_ms": {
                    "atoms": None,
                    "context": None,
                    "weights": None,
                    "selector_incremental": None,
                },
                "summary": summary,
            }
        if (
            causal is None
            or neighbor_valid is None
            or signals is None
            or red_cost is None
            or causal_signal_atom_input is None
        ):
            raise ValueError("selector inputs missing for Static14D/Scene14D")
        atom_started = time.perf_counter_ns()
        phase_receipt: dict[str, Any] | None = (
            {} if self.production_surface_id is not None else None
        )
        materialized = self.materialize(
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
        atom_ms = _ms(atom_started)
        if array_sha256(candidates) != before:
            raise ValueError("atom materialization mutated frozen pool")
        context_payload = None
        scene_weight_receipt = None
        scene_weights = None
        context_ms = None
        weight_ms = None
        if "Scene14D" in evaluate_arms:
            context_started = time.perf_counter_ns()
            context_record = build_v25_raw_context(
                causal_input=causal,
                candidates=candidates,
                source_valid_mask=np.asarray(
                    materialized["source_valid_mask"], dtype=bool
                ),
                causal_signal_atom_input=causal_signal_atom_input,
                v2i_signal_timing=None,
            )
            context_payload = {
                "schema_version": CONTEXT_SCHEMA_VERSION,
                "raw_context": context_record.as_dict(),
                "source_complete": {
                    name: bool(value)
                    for name, value in zip(
                        RAW_FEATURE_NAMES, context_record.source_complete
                    )
                },
                "source_receipt": dict(context_record.source_receipt),
            }
            context_ms = _ms(context_started)
            weight_started = time.perf_counter_ns()
            scene_weight_receipt = self.assets.scene14d_weight_provider(context_payload)
            scene_weights = np.asarray(
                scene_weight_receipt["weights"], dtype=np.float64
            )
            weight_ms = _ms(weight_started)
        arms: dict[str, dict[str, Any]] = {}
        if "pool_matched_candidate0" in evaluate_arms:
            arms["pool_matched_candidate0"] = {
                "status": "ok",
                "selected_index": 0,
                "selected_row_sha256": array_sha256(candidates[0]),
                "scores": None,
                "physical_feasible_mask": np.asarray(
                    materialized["physical_feasible_mask"], dtype=np.bool_
                ).tolist(),
                "source_valid_mask": np.asarray(
                    materialized["source_valid_mask"], dtype=np.bool_
                ).tolist(),
                "baseline_rule": "frozen_row0",
                "selector_latency_ms": None,
            }
        for arm, weights in (
            ("Static14D", self.assets.static14d_weights),
            ("Scene14D", scene_weights),
        ):
            if arm not in evaluate_arms:
                continue
            selector_started = time.perf_counter_ns()
            selection = self.select_candidate(
                candidates=candidates,
                materialized=materialized,
                atom_scales=self.assets.atom_scales,
                weights=weights,
                eligibility_mask_name="source_valid_mask",
                simplex_nonnegative_atol=TRAINED_SIMPLEX_NONNEGATIVE_ATOL,
            )
            selector_ms = _ms(selector_started)
            raw_scores = selection.get("scores")
            source_mask = np.asarray(
                selection["source_valid_mask"], dtype=np.bool_
            )
            tie_set: list[int] | None = None
            margin: float | None = None
            if raw_scores is not None:
                score_array = np.asarray(raw_scores, dtype=np.float64)
                ordered = sorted(
                    (float(score_array[index]), int(index))
                    for index in np.flatnonzero(source_mask)
                )
                if ordered:
                    best = ordered[0][0]
                    tie_set = [
                        index for score, index in ordered if score == best
                    ]
                    margin = (
                        float(ordered[1][0] - best)
                        if len(ordered) >= 2
                        else None
                    )
            receipt = {
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
                "source_valid_mask": np.asarray(
                    selection["source_valid_mask"], dtype=np.bool_
                ).tolist(),
                "weights_sha256": array_sha256(np.asarray(weights, dtype=np.float64)),
                "selector_latency_ms": selector_ms,
                "eligible_count": int(np.count_nonzero(source_mask)),
                "margin_best_vs_runner_up": margin,
                "exact_tie_set": tie_set,
                "tie_break_contract": "lowest_eligible_candidate_index",
            }
            if arm == "Scene14D":
                if (
                    context_payload is None
                    or scene_weight_receipt is None
                    or scene_weights is None
                ):
                    raise ValueError("Scene14D context/weight path was not executed")
                receipt["context"] = context_payload
                receipt["scene_weight_receipt"] = {
                    key: value
                    for key, value in scene_weight_receipt.items()
                    if key != "weights"
                }
            arms[arm] = receipt
        if array_sha256(candidates) != before:
            raise ValueError("real selector mutated frozen pool")
        atom_matrix = np.asarray(materialized["atom_matrix"], dtype=np.float64)
        summary = {
            "atom_matrix": atom_matrix.tolist(),
            "atom_matrix_sha256": array_sha256(atom_matrix),
            "physical_feasible_mask": np.asarray(
                materialized["physical_feasible_mask"], dtype=np.bool_
            ).tolist(),
            "source_valid_mask": np.asarray(
                materialized["source_valid_mask"], dtype=np.bool_
            ).tolist(),
            "candidate_reasons": [
                list(value) for value in materialized["candidate_reasons"]
            ],
            "canonical_eligible": bool(materialized["canonical_eligible"]),
            "exclusion_reason": materialized.get("exclusion_reason"),
            "context": context_payload,
            "scene_weights": (
                None if scene_weights is None else scene_weights.tolist()
            ),
            "scene_weights_sha256": (
                None if scene_weights is None else array_sha256(scene_weights)
            ),
        }
        if self.production_surface_id is not None:
            assert phase_receipt is not None
            summary["atom_materialization_phase_receipt"] = phase_receipt
        return {
            "materialized": materialized,
            "arms": arms,
            "latency_ms": {
                "atoms": atom_ms,
                "context": context_ms,
                "weights": weight_ms,
                "selector_incremental": float(
                    sum(
                        row.get("selector_latency_ms") or 0.0
                        for row in arms.values()
                    )
                ),
            },
            "summary": summary,
        }


def validate(
    *,
    output: Path,
    contract: Path,
    contract_root: str,
    contract_review: Path,
    contract_review_root: str,
    probe_config: Path,
    training: Path,
    training_root: str,
    training_review: Path,
    training_review_root: str,
    fixed_dp_repo: Path,
    device: str,
) -> str:
    verify_complete_seal(contract, contract_root, label="fair contract")
    verify_complete_seal(
        contract_review, contract_review_root, label="fair contract review"
    )
    contract_report = _object(contract / "report.json")
    review_report = _object(contract_review / "report.json")
    frozen = validate_fair_nonholdout_contract(contract_report["contract"])
    if (
        contract_report.get("status")
        != "sealed_outcome_independent_fair_nonholdout_contract"
        or review_report.get("status")
        != "passed_independent_fair_nonholdout_contract_review"
        or review_report.get("source", {}).get("root_sha256") != contract_root
    ):
        raise ValueError("fair contract authority chain drifted")
    config = _object(probe_config)
    if (
        config.get("protocol", {}).get("route_role")
        != "v24_source_only_single_record_probe"
        or config.get("protocol", {}).get("holdout_access_authorized") is not False
        or config["routes"][0]["sha256"]
        != frozen["state_matched_selector_replay"]["route_sha256"]
    ):
        raise ValueError("fair validation nonholdout source drifted")
    fixed_dp_repo = fixed_dp_repo.resolve()
    if (
        _git_head(fixed_dp_repo) != FIXED_DP_HEAD
        or _tracked_changes(fixed_dp_repo)
        or _file_sha256(Path(config["fixed_dp"]["checkpoint"]["path"]))
        != config["fixed_dp"]["checkpoint"]["sha256"]
        or _file_sha256(Path(config["fixed_dp"]["args_json"]["path"]))
        != config["fixed_dp"]["args_json"]["sha256"]
    ):
        raise ValueError("fixed DP source/checkpoint authority drifted")
    for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    _install_fixed_dp_annotation_compatibility(fixed_dp_repo)
    import torch
    import scenario_generation.replay as replay
    import scenario_generation.tensor_converter as tensor_converter
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route

    from camp_core.integrations.diffusion_planner import (
        install_lanelet2_projection_fallback,
        require_source_preserving_lanelet2_regulatory_adapter,
    )
    from scripts.integrations.run_diffusion_planner_camp_replay import _load_model

    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA fair validation requested but unavailable")
    model, model_args = _load_model(
        Path(config["fixed_dp"]["checkpoint"]["path"]),
        Path(config["fixed_dp"]["args_json"]["path"]),
        device,
    )
    model.eval()
    assets = load_v25_runtime_selector_assets(
        training_artifact=training,
        training_root_sha256=training_root,
        training_review_artifact=training_review,
        training_review_root_sha256=training_review_root,
    )
    map_path = Path(config["map"]["path"])
    route_spec = config["routes"][0]
    route_path = Path(route_spec["path"])
    if (
        _file_sha256(map_path) != config["map"]["sha256"]
        or _file_sha256(route_path) != route_spec["sha256"]
    ):
        raise ValueError("fair validation map/route asset drifted")
    require_source_preserving_lanelet2_regulatory_adapter(map_path)
    install_lanelet2_projection_fallback(map_path)
    geometry = _load_root_bound_geometry(config)

    replay_run = _run_one(
        config=config,
        model=model,
        model_args=model_args,
        tensor_converter=tensor_converter,
        replay=replay,
        builder_type=LaneletSceneBuilder,
        route_type=Route,
        fixed_dp_repo=fixed_dp_repo,
        assets=assets,
        device=device,
        max_ticks=STATE_COUNT,
        operational_arm="pool_matched_candidate0",
        evaluate_all_arms=True,
        adaptation_diagnostics=True,
        scratch_parent=output.parent,
    )
    replay_receipts = replay_run["receipts"]
    if len(replay_receipts) != STATE_COUNT:
        raise ValueError("state-matched replay state denominator drifted")
    any_selector_failure = any(
        any(
            receipt["real_selector_receipts"][arm]["status"] != "ok"
            for arm in ARMS
        )
        for receipt in replay_receipts
    )
    any_substantive_drift = any(
        receipt["adaptation"]["substantive_drift"] is True
        for receipt in replay_receipts
    )
    any_zero_call_failure = any(
        any(
            receipt["zero_call_receipt"][field] != 0
            for field in (
                "dp_or_model_calls_after_pool",
                "latent_replacements_after_pool",
                "candidate_generations_after_pool",
            )
        )
        for receipt in replay_receipts
    )
    replay_passed = not any_selector_failure and not any_zero_call_failure
    adaptation_passed = not any_substantive_drift
    closed_loop_runs: list[dict[str, Any]] = []
    closed_loop_arrays: dict[str, np.ndarray] = {}
    if replay_passed and adaptation_passed:
        for arm in ARMS:
            try:
                run = _run_one(
                    config=config,
                    model=model,
                    model_args=model_args,
                    tensor_converter=tensor_converter,
                    replay=replay,
                    builder_type=LaneletSceneBuilder,
                    route_type=Route,
                    fixed_dp_repo=fixed_dp_repo,
                    assets=assets,
                    device=device,
                    max_ticks=TICKS_PER_CLOSED_LOOP_ARM,
                    operational_arm=arm,
                    evaluate_all_arms=False,
                    adaptation_diagnostics=False,
                    scratch_parent=output.parent,
                )
                native = _native_receipt(
                    config=config,
                    route_spec=route_spec,
                    arm=arm,
                    run=run,
                )
                v2_arm = {
                    "pool_matched_candidate0": "candidate0",
                    "Static14D": "static14d",
                    "Scene14D": "scene14d",
                }[arm]
                v2 = summarize_run_v2(
                    native_receipt=native,
                    evaluation_row={
                        "arm": v2_arm,
                        "status": "complete",
                        "pair_key": "development_nonholdout_fair_pool",
                        "inference_cluster_id": "development_nonholdout_cluster",
                        "benchmark_stratum": "development_nonholdout",
                        "scenario_family": "source_only_four_track_highway",
                        "source_class": "development_nonholdout",
                    },
                    run_config={
                        "signal_complete_runtime": {"case": {"actors": []}},
                        "spawn_config": config["spawn_config"],
                    },
                    geometry=geometry,
                    supplementary_receipt=None,
                )
                closed_loop_runs.append(
                    {
                        "arm": arm,
                        "status": "complete",
                        "tick_denominator": len(run["receipts"]),
                        "native_receipt": native,
                        "selector_receipts": run["receipts"],
                        "evaluation_v2_endpoint_vector": v2,
                    }
                )
                key = {
                    "pool_matched_candidate0": "candidate0",
                    "Static14D": "static14d",
                    "Scene14D": "scene14d",
                }[arm]
                closed_loop_arrays[f"closed_loop_{key}_candidates"] = np.stack(
                    run["callback"].primary_candidates
                )
                if run["callback"].primary_atoms:
                    closed_loop_arrays[f"closed_loop_{key}_atoms"] = np.stack(
                        run["callback"].primary_atoms
                    )
                    closed_loop_arrays[
                        f"closed_loop_{key}_source_masks"
                    ] = np.stack(run["callback"].primary_source_masks)
            except Exception as exc:
                closed_loop_runs.append(
                    {
                        "arm": arm,
                        "status": "retained_terminal_failure",
                        "tick_denominator": 0,
                        "failure_class": type(exc).__name__,
                        "failure_reason": str(exc),
                    }
                )
    status = (
        "passed_fair_nonholdout_engineering_validation"
        if replay_passed
        and adaptation_passed
        and len(closed_loop_runs) == 3
        and all(row["status"] == "complete" for row in closed_loop_runs)
        and all(row["tick_denominator"] == TICKS_PER_CLOSED_LOOP_ARM for row in closed_loop_runs)
        else "blocked_fair_nonholdout_engineering_validation"
    )
    report = {
        "schema_version": "camp_dp_v25_fair_nonholdout_validation_v1",
        "status": status,
        "implementation_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "authority": {
            "contract": {"path": str(contract), "root_sha256": contract_root},
            "contract_review": {
                "path": str(contract_review),
                "root_sha256": contract_review_root,
            },
            "training": {"path": str(training), "root_sha256": training_root},
            "training_review": {
                "path": str(training_review),
                "root_sha256": training_review_root,
            },
        },
        "generator_name": GENERATOR_NAME,
        "state_matched_replay": {
            "status": "passed" if replay_passed else "failed",
            "state_count": len(replay_receipts),
            "authoritative_pool_count": len(replay_receipts),
            "real_selector_execution": True,
            "structural_row0_probe_used_as_static_or_scene": False,
            "receipts": replay_receipts,
        },
        "pool_distribution_adaptation_audit": {
            "status": "passed" if adaptation_passed else "substantive_drift",
            "state_count": len(replay_receipts),
            "trajectory_row_denominator": len(replay_receipts) * 8,
            "neighbor_row_denominator": len(replay_receipts) * 8,
            "trajectory_equivalent_row_count": sum(
                sum(receipt["adaptation"]["trajectory_within_tolerance"])
                for receipt in replay_receipts
            ),
            "neighbor_equivalent_row_count": sum(
                sum(receipt["adaptation"]["neighbor_within_tolerance"])
                for receipt in replay_receipts
            ),
            "substantive_drift_state_count": sum(
                receipt["adaptation"]["substantive_drift"] is True
                for receipt in replay_receipts
            ),
            "training_executed": False,
            "possible_training_pool_adaptation_required": not adaptation_passed,
        },
        "compute_matched_closed_loop": {
            "entry_conditions_passed": replay_passed and adaptation_passed,
            "arm_run_denominator": 3,
            "planned_tick_denominator": 3 * TICKS_PER_CLOSED_LOOP_ARM,
            "terminal_arm_run_count": len(closed_loop_runs),
            "complete_arm_run_count": sum(
                row["status"] == "complete" for row in closed_loop_runs
            ),
            "retained_terminal_failure_count": sum(
                row["status"] != "complete" for row in closed_loop_runs
            ),
            "complete_case_shrinkage_used": False,
            "post_divergence_cross_arm_tensor_identity_claimed": False,
            "runs": closed_loop_runs,
        },
        "hard_stop": {
            "selector_failure": any_selector_failure,
            "post_pool_forbidden_call": any_zero_call_failure,
            "adaptation_substantive_drift": any_substantive_drift,
        },
        "boundaries": {
            "development_nonholdout_only": True,
            "fresh_or_holdout_accessed": False,
            "fresh_or_b4_raw_outcome_read": False,
            "fresh_arm_or_dp_k8_rerun": False,
            "old_artifact_or_cas_written": False,
            "fixed_dp_source_or_checkpoint_modified": False,
            "weights_theta_atoms_or_scales_modified": False,
            "training_or_retraining_executed": False,
            "confirmatory_effect_claim_authorized": False,
            "legacy_claim_decision": (
                "honest_no_claim_under_frozen_preregistered_all_gate"
            ),
            "ultra_submission_authorized": False,
        },
    }
    arrays = {
        "primary_candidates": np.stack(replay_run["callback"].primary_candidates),
        "sequential_candidates": np.stack(
            replay_run["callback"].sequential_candidates
        ),
        "primary_neighbors": np.stack(replay_run["callback"].primary_neighbors),
        "sequential_neighbors": np.stack(
            replay_run["callback"].sequential_neighbors
        ),
        "primary_atoms": np.stack(replay_run["callback"].primary_atoms),
        "sequential_atoms": np.stack(replay_run["callback"].sequential_atoms),
        "primary_source_masks": np.stack(
            replay_run["callback"].primary_source_masks
        ),
        "sequential_source_masks": np.stack(
            replay_run["callback"].sequential_source_masks
        ),
        "primary_physical_masks": np.stack(
            replay_run["callback"].primary_physical_masks
        ),
        "sequential_physical_masks": np.stack(
            replay_run["callback"].sequential_physical_masks
        ),
        "atom_scales": np.asarray(assets.atom_scales, dtype=np.float64),
        "static_weights": np.asarray(assets.static14d_weights, dtype=np.float64),
        **closed_loop_arrays,
    }
    return _write_atomic(output, report, arrays)


def _run_one(
    *,
    config: Mapping[str, Any],
    model: Any,
    model_args: Any,
    tensor_converter: Any,
    replay: Any,
    builder_type: Any,
    route_type: Any,
    fixed_dp_repo: Path,
    assets: Any,
    device: str,
    max_ticks: int,
    operational_arm: str,
    evaluate_all_arms: bool,
    adaptation_diagnostics: bool,
    scratch_parent: Path,
    production_surface_id: str | None = None,
    production_surface_options: Mapping[str, Any] | None = None,
    scene_adapter: Any | None = None,
    latent_provider: Callable[[int], np.ndarray] | None = None,
    post_safety_enricher: Callable[[dict[str, Any], Any], None] | None = None,
    retain_runtime_failures: bool = False,
) -> dict[str, Any]:
    builder = builder_type(str(config["map"]["path"]))
    route_spec = config["routes"][0]
    route = route_type.load(Path(route_spec["path"]))
    route_ids = list(route.route_lanelet_ids or ())
    if not route_ids:
        raise ValueError("fair validation route is unresolved")
    causal_signal_chain = (
        _build_no_signal_chain(
            builder=builder,
            route_ids=route_ids,
            map_sha256=str(config["map"]["sha256"]),
            route_sha256=str(route_spec["sha256"]),
        )
        if scene_adapter is None
        else None
    )
    spawn = replay.SpawnConfig(**dict(config["spawn_config"]))
    spawn.max_steps = max_ticks
    spawn.validate()
    state = NativeHookState()
    callback = _FairPredictBatch(
        model=model,
        model_args=model_args,
        tensor_converter=tensor_converter,
        fixed_dp_repo=fixed_dp_repo,
        fixed_config=config["fixed_dp"],
        route_sha256=route_spec["sha256"],
        builder=builder,
        route_ids=route_ids,
        replay=replay,
        assets=assets,
        state=state,
        max_ticks=max_ticks,
        operational_arm=operational_arm,
        evaluate_all_arms=evaluate_all_arms,
        adaptation_diagnostics=adaptation_diagnostics,
        causal_signal_chain=causal_signal_chain,
        production_surface_id=production_surface_id,
        production_surface_options=production_surface_options,
        scene_adapter=scene_adapter,
        latent_provider=latent_provider,
    )

    def after_tracker(receipt: dict[str, Any], scene: Any) -> None:
        _capture_post_safety(receipt, scene, builder, route_ids, replay)
        if post_safety_enricher is not None:
            post_safety_enricher(receipt, scene)

    scratch = Path(
        tempfile.mkdtemp(prefix=".v25_fair_nonholdout.", dir=str(scratch_parent))
    )
    prior_no_png = os.environ.get("REPLAY_NO_PNG")
    os.environ["REPLAY_NO_PNG"] = "1"
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
            except _RequestedStateCountReached:
                native_result = {
                    "reason": "requested_state_count_reached",
                    "goal_reached": False,
                }
            except Exception as exc:
                if not retain_runtime_failures:
                    raise
                native_result = {
                    "reason": "retained_typed_runtime_failure",
                    "goal_reached": False,
                    "failure_class": type(exc).__name__,
                    "failure_reason": str(exc),
                }
    finally:
        if prior_no_png is None:
            os.environ.pop("REPLAY_NO_PNG", None)
        else:
            os.environ["REPLAY_NO_PNG"] = prior_no_png
        shutil.rmtree(scratch, ignore_errors=True)
    return {
        "receipts": state.receipts,
        "native_result": dict(native_result),
        "callback": callback,
    }


def _build_no_signal_chain(
    *,
    builder: Any,
    route_ids: list[int],
    map_sha256: str,
    route_sha256: str,
) -> dict[str, Any]:
    pieces: list[np.ndarray] = []
    regulatory_ids: set[int] = set()
    for lanelet_id in route_ids:
        lanelet = builder._ll_by_id.get(int(lanelet_id))
        cached = builder._cache.get(int(lanelet_id))
        if lanelet is None or cached is None:
            raise ValueError("fair no-signal route lanelet is absent from fixed map")
        regulatory_ids.update(int(value.id) for value in lanelet.trafficLights())
        line = np.asarray(cached.raw_centerline, dtype=np.float64)
        if (
            line.ndim != 2
            or line.shape[1] != 2
            or len(line) < 2
            or not np.isfinite(line).all()
        ):
            raise ValueError("fair no-signal route centerline is invalid")
        pieces.append(line if not pieces else line[1:])
    if regulatory_ids:
        raise ValueError("fair source route unexpectedly has signal authority")
    route_world = np.concatenate(pieces, axis=0)
    semantic = build_semantic_clone_payload(
        {
            "family": "source_only_four_track_highway",
            "tier": "development_qualification",
            "semantic_variant": "fixed_source_route",
            "parameters": {},
            "actors": [],
            "signal": {"phase": "none", "mapped_source_required": False},
        },
        route_polyline_world=route_world,
        stop_line_world=None,
    )
    chain: dict[str, Any] = {
        "schema_version": NO_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": canonical_json_sha256(
            {
                "role": "v25_fair_development_source_only",
                "route_identity_sha256": route_sha256,
                "source_map_sha256": map_sha256,
            }
        ),
        "route_identity_sha256": route_sha256,
        "source_map_sha256": map_sha256,
        "route_lanelet_ids": [int(value) for value in route_ids],
        "route_geometry_sha256": canonical_json_sha256(
            {"route_polyline_local_m": semantic["route_polyline_local_m"]}
        ),
        "traffic_light_regulatory_element_ids": [],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {
            key: value
            for key, value in chain.items()
            if key != "source_chain_sha256"
        }
    )
    return validate_no_signal_chain(chain)


def _native_receipt(
    *,
    config: Mapping[str, Any],
    route_spec: Mapping[str, Any],
    arm: str,
    run: Mapping[str, Any],
) -> dict[str, Any]:
    ticks = []
    for receipt in run["receipts"]:
        safety = receipt.get("_safety_record")
        if type(safety) is not dict:
            raise ValueError("closed-loop tracker safety record missing")
        ticks.append(
            {
                "tick_index": int(receipt["tick_index"]),
                "input_sha256": str(receipt["input_sha256"]),
                "default_output_sha256": str(receipt["default_output_sha256"]),
                "selected_index": int(receipt["selected_index"]),
                "selected_trajectory_sha256": str(
                    receipt["selected_trajectory_sha256"]
                ),
                "safety": dict(safety),
                "latency_ms": {
                    key: float(value)
                    for key, value in receipt["latency_ms"].items()
                    if value is not None
                },
            }
        )
    return {
        "schema_version": "camp_dp_v25_fair_nonholdout_native_receipt_v1",
        "status": "ok",
        "route_name": str(route_spec["name"]),
        "route_sha256": str(route_spec["sha256"]),
        "logical_map_sha256": str(config["map"]["sha256"]),
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": str(config["fixed_dp"]["checkpoint"]["sha256"]),
        "args_sha256": str(config["fixed_dp"]["args_json"]["sha256"]),
        "arm": arm,
        "scenario_seed": int(config["seeds"]["scenario"]),
        "ticks": ticks,
        "native_result": dict(run["native_result"]),
        "claim_authorized": False,
    }


def _tensor_dict_sha256(value: Mapping[str, Any]) -> str:
    rows = []
    for key in sorted(value):
        tensor = value[key].detach().cpu().contiguous().numpy()
        rows.append(
            {
                "key": key,
                "dtype": str(tensor.dtype),
                "shape": list(tensor.shape),
                "sha256": array_sha256(tensor),
            }
        )
    return canonical_sha256(rows)


def _rng_sha256(torch: Any) -> str:
    return canonical_sha256(
        {
            "python": repr(random.getstate()),
            "numpy": repr(np.random.get_state()),
            "torch_cpu": hashlib.sha256(
                torch.get_rng_state().cpu().numpy().tobytes()
            ).hexdigest(),
            "torch_cuda": [
                hashlib.sha256(state.cpu().numpy().tobytes()).hexdigest()
                for state in (
                    torch.cuda.get_rng_state_all()
                    if torch.cuda.is_available()
                    else []
                )
            ],
        }
    )


def _per_row_max_error(left: np.ndarray, right: np.ndarray) -> list[float]:
    return [
        float(
            np.max(
                np.abs(
                    left[index].astype(np.float64)
                    - right[index].astype(np.float64)
                )
            )
        )
        for index in range(8)
    ]


def _ms(started_ns: int) -> float:
    return (time.perf_counter_ns() - started_ns) / 1e6


def _write_atomic(
    output: Path, report: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        (staging / "report.json").write_bytes(canonical_bytes(report))
        np.savez_compressed(
            staging / "replay_preimages.npz",
            **{key: np.asarray(value) for key, value in arrays.items()},
        )
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "implementation_head": report["implementation_head"],
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="V25 fair nonholdout validation")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 fair nonholdout validation")
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text("utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must be an object")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=repo,
            text=True,
        ).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--probe-config", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--training-root", required=True)
    parser.add_argument("--training-review", type=Path, required=True)
    parser.add_argument("--training-review-root", required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    print(validate(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
