from __future__ import annotations

import argparse
import __future__
import hashlib
import io
import importlib.abc
import importlib.machinery
import inspect
import json
import os
import pickle
import random
import subprocess
import sys
import time
from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from camp_core.integrations.diffusion_planner_v21_native import (
    aggregate_paired_safety,
    array_sha256,
    candidate_latents,
    candidate_seed,
    causal_input_receipt,
    diagnostic_constant_velocity_circle_ttc_s,
    paired_safety_delta,
    safety_cost_native_v1,
    summarize_route_comfort_native,
    summarize_safety_cost_native_v1,
    verify_candidate_tensor_immutable,
    verify_default_candidate0_identity,
)
from camp_core.integrations.diffusion_planner_v22_native import (
    summarize_safety_cost_native_v22,
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


def _v25_causal_evidence_sha256(value: Mapping[str, Any]) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
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
SPAWN_CONFIG_FIELDS = frozenset(
    {
        "spawn_period_steps",
        "max_active_npcs",
        "spawn_probability",
        "min_spawn_distance",
        "max_spawn_distance",
        "despawn_distance",
        "forward_bias",
        "min_npc_separation",
        "goal_tolerance_m",
        "max_steps",
        "seed",
        "ego_overlap_ratio",
        "npc_min_speed",
        "npc_max_speed",
        "npc_route_length_m",
        "npc_goal_min_dist_from_ego_route",
        "curvature_threshold",
        "goal_pass_window_m",
        "map_refresh_steps",
        "max_map_lanelets",
        "map_mask_range_m",
        "sg_smooth_enabled",
        "sg_filter_window",
        "sg_filter_order",
        "advance_mode",
        "mpc_horizon_steps",
        "mpc_n_knots",
        "ego_length",
        "ego_width",
        "ego_wheelbase",
        "ego_max_steer",
        "inference_delay",
        "enable_traffic_lights",
        "overlay_metrics_on_png",
        "dump_npz_dir",
        "dump_neighbor_count",
        "reward_config_path",
        "ego_init_speed",
        "sequential_inference",
        "static_npc_count",
        "static_npc_spacing_m",
        "static_npc_shoulder_margin_m",
        "static_npc_seed",
        "parked_vehicles_yaml",
        "parked_vehicle_visibility_m",
        "turn_indicator_keep_bias",
        "turn_indicator_hold_steps",
    }
)
_ROUTE_SHA256 = {
    "sample_map_smoke_route": (
        "b8b5417c3269bbdbe72efe49388d32af04751b25cffcec297a04b25a50140c13"
    ),
    "sample_map_tl_route_59_to_86": (
        "dc9b3906bace09ee9e99062ac702df1c5b2d2f4620d0a7fa14022faa9a39e4c4"
    ),
}
_SHA256_HEX = frozenset("0123456789abcdef")
V21_PHYSICAL_SELECTION = "v21_physical"
V22_SOURCE_VALID_SELECTION = "v22_source_valid"
_SELECTION_POLICIES = frozenset(
    {V21_PHYSICAL_SELECTION, V22_SOURCE_VALID_SELECTION}
)


def _compile_fixed_dp_with_postponed_annotations(
    source: bytes, path: str
) -> Any:
    return compile(
        source,
        path,
        "exec",
        flags=__future__.annotations.compiler_flag,
        dont_inherit=True,
    )


class _FixedDpPostponedAnnotationsLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname: str) -> Any:
        path = self.get_filename(fullname)
        return self.source_to_code(self.get_data(path), path)

    def source_to_code(
        self, data: bytes, path: str, *, _optimize: int = -1
    ) -> Any:
        return compile(
            data,
            path,
            "exec",
            flags=__future__.annotations.compiler_flag,
            dont_inherit=True,
            optimize=_optimize,
        )


class _FixedDpPostponedAnnotationsFinder(importlib.abc.MetaPathFinder):
    def __init__(self, dp_repo: str | Path) -> None:
        self.dp_repo = Path(dp_repo).resolve()

    def loader_for(
        self, path: str | Path, fullname: str = "fixed_dp_compat"
    ) -> _FixedDpPostponedAnnotationsLoader | None:
        resolved = Path(path).resolve()
        try:
            resolved.relative_to(self.dp_repo)
        except ValueError:
            return None
        if resolved.suffix != ".py":
            return None
        return _FixedDpPostponedAnnotationsLoader(fullname, str(resolved))

    def find_spec(
        self,
        fullname: str,
        path: Any = None,
        target: Any = None,
    ) -> Any:
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or spec.origin is None:
            return spec
        loader = self.loader_for(spec.origin, fullname)
        if loader is not None:
            spec.loader = loader
        return spec


def _install_fixed_dp_annotation_compatibility(
    dp_repo: str | Path,
) -> _FixedDpPostponedAnnotationsFinder | None:
    if sys.version_info >= (3, 10):
        return None
    resolved = Path(dp_repo).resolve()
    for finder in sys.meta_path:
        if (
            isinstance(finder, _FixedDpPostponedAnnotationsFinder)
            and finder.dp_repo == resolved
        ):
            return finder
    finder = _FixedDpPostponedAnnotationsFinder(resolved)
    sys.meta_path.insert(0, finder)
    return finder


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
        materialize: Callable[..., Mapping[str, Any]] | None,
        select_candidate: Callable[..., Mapping[str, Any]] | None,
        signal_mask: Callable[[np.ndarray, Mapping[str, Any], Any], np.ndarray] | None,
        planned_red_cost: Callable[
            [np.ndarray, Mapping[str, Any], Any], np.ndarray
        ] | None,
        atom_scales: np.ndarray | None,
        weights: np.ndarray | None,
        candidate_seed_root: int,
        route_sha256: str,
        pre_safety: Callable[[dict[str, Any], Any], None] | None = None,
        selection_policy: str = V21_PHYSICAL_SELECTION,
        operational_mode: str = "camp_selector",
        decision_sink: Callable[[Mapping[str, Any]], None] | None = None,
        decision_sample_every_ticks: int = 5,
        scene_adapter: Callable[[Any, int], Mapping[str, Any]] | None = None,
        scene_adapter_model_input_sync: Callable[
            [Any, Any, int], Mapping[str, Any]
        ]
        | None = None,
        v25_context_sink: Callable[[Mapping[str, Any]], None] | None = None,
        v25_v2i_signal_timing: Mapping[str, Any] | None = None,
        causal_signal_atom_input_provider: Callable[
            [Any, int], Mapping[str, Any]
        ]
        | None = None,
        causal_input_sink: Callable[
            [int, Mapping[str, Any]], None
        ]
        | None = None,
    ) -> None:
        self.state = state
        self.to_model_tensors = to_model_tensors
        self.dump_step_npz = dump_step_npz
        self.materialize = materialize
        self.select_candidate = select_candidate
        self.signal_mask = signal_mask
        self.planned_red_cost = planned_red_cost
        if operational_mode not in {"camp_selector", "dp_candidate0"}:
            raise ValueError("unknown native K8 operational mode")
        self.operational_mode = operational_mode
        self.atom_scales = (
            None
            if atom_scales is None
            else np.asarray(atom_scales, dtype=np.float64)
        )
        self.weights = (
            None if weights is None else np.asarray(weights, dtype=np.float64)
        )
        self.candidate_seed_root = candidate_seed_root
        self.route_sha256 = route_sha256
        self.pre_safety = pre_safety
        if operational_mode == "camp_selector" and selection_policy not in _SELECTION_POLICIES:
            raise ValueError("unknown selection policy")
        self.selection_policy = (
            selection_policy
            if operational_mode == "camp_selector"
            else "candidate0_operational_default"
        )
        if decision_sink is not None and selection_policy != V22_SOURCE_VALID_SELECTION:
            raise ValueError("decision sink requires v22 source-valid selection")
        if decision_sink is not None and operational_mode != "camp_selector":
            raise ValueError("DP candidate-0 mode cannot emit CAMP decision snapshots")
        if (
            isinstance(decision_sample_every_ticks, bool)
            or not isinstance(decision_sample_every_ticks, int)
            or decision_sample_every_ticks <= 0
        ):
            raise ValueError("decision sample cadence must be a positive integer")
        self.decision_sink = decision_sink
        self.decision_sample_every_ticks = decision_sample_every_ticks
        self.scene_adapter = scene_adapter
        self.scene_adapter_model_input_sync = scene_adapter_model_input_sync
        self.v25_context_sink = v25_context_sink
        self.v25_v2i_signal_timing = v25_v2i_signal_timing
        self.causal_signal_atom_input_provider = causal_signal_atom_input_provider
        self.causal_input_sink = causal_input_sink
        if operational_mode == "camp_selector" and (
            self.atom_scales is None
            or self.weights is None
            or self.atom_scales.shape != (14,)
            or self.weights.shape != (14,)
            or self.materialize is None
            or self.select_candidate is None
            or self.signal_mask is None
            or self.planned_red_cost is None
            or (
                selection_policy == V22_SOURCE_VALID_SELECTION
                and self.causal_signal_atom_input_provider is None
            )
        ):
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
            "selection_policy": self.selection_policy,
            "_planning_started_ns": started_ns,
            "latency_ms": {},
        }
        self.state.receipts.append(receipt)
        try:
            if self.scene_adapter is not None:
                receipt["controlled_scene"] = dict(
                    self.scene_adapter(scene, tick_index)
                )
            if self.scene_adapter_model_input_sync is not None:
                if "controlled_scene" not in receipt:
                    raise ValueError("model-input cache sync requires a scene adapter")
                receipt["controlled_scene"]["model_input_cache"] = dict(
                    self.scene_adapter_model_input_sync(scene, map_cache, tick_index)
                )
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
            if self.causal_input_sink is not None:
                self.causal_input_sink(
                    tick_index,
                    {
                        key: np.array(value, copy=True, order="C")
                        for key, value in boundary.causal_input.items()
                    },
                )
            if self.pre_safety is not None:
                self.pre_safety(receipt, scene)
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
            receipt["candidate_row_sha256"] = [
                array_sha256(candidate_tensor[index]) for index in range(8)
            ]
            receipt["default_candidate0_identity"] = (
                verify_default_candidate0_identity(default_ego, candidate_tensor[0])
            )
            receipt["candidate_tensor_sha256_before"] = before_sha
            receipt["candidate_neighbor_sha256"] = array_sha256(neighbor_tensor)
            receipt["candidate_neighbor_shape"] = list(neighbor_tensor.shape)

            if self.operational_mode == "dp_candidate0":
                receipt.update(
                    verify_candidate_tensor_immutable(candidate_tensor, before_sha)
                )
                selected = candidate_tensor[0].copy()
                if (
                    not np.array_equal(selected, default_ego)
                    or array_sha256(selected) != receipt["default_output_sha256"]
                ):
                    raise ValueError("DP candidate 0 differs from operational default")
                direct_predictions[ego_id] = selected
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
                        "selected_index": 0,
                        "selected_trajectory_sha256": array_sha256(selected),
                        "score_contract": "candidate0_operational_default",
                        "eligibility_mask_name": "candidate0_operational_default",
                        "candidate0_operational_default": True,
                        "npc_operational_outputs_unchanged": True,
                        "default_turn_indicators_retained": True,
                        "post_divergence_cross_arm_tensor_identity_required": False,
                    }
                )
                receipt["latency_ms"]["hook_total"] = _elapsed_ms(started_ns)
                return (
                    (direct_predictions, turns)
                    if return_turn_indicators
                    else direct_predictions
                )

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
            causal_evidence = {
                "schema_version": "camp_dp_v25_bounded_causal_evidence_v1",
                "ego_current_state": np.asarray(
                    causal_input["ego_current_state"], dtype=np.float32
                ).tolist(),
                "ego_shape": np.asarray(
                    causal_input["ego_shape"], dtype=np.float32
                ).tolist(),
                "neighbor_agents_past": np.asarray(
                    causal_input["neighbor_agents_past"], dtype=np.float32
                ).tolist(),
                "neighbor_valid_mask": np.asarray(
                    neighbor_valid, dtype=np.bool_
                ).tolist(),
                "candidate_neighbor_predictions": neighbor_tensor.tolist(),
                "static_objects": np.asarray(
                    causal_input["static_objects"], dtype=np.float32
                ).tolist(),
                "route_lanes": np.asarray(
                    causal_input["route_lanes"], dtype=np.float32
                ).tolist(),
                "route_lanes_speed_limit": np.asarray(
                    causal_input["route_lanes_speed_limit"], dtype=np.float32
                ).tolist(),
                "route_lanes_has_speed_limit": np.asarray(
                    causal_input["route_lanes_has_speed_limit"], dtype=np.bool_
                ).tolist(),
                "signal_mask": np.asarray(signals, dtype=np.bool_).tolist(),
                "fixed_dp_planned_red_light_cost": red_cost.tolist(),
            }
            causal_evidence_sha256 = _v25_causal_evidence_sha256(causal_evidence)
            receipt.update(
                {
                    "causal_evidence_sha256": causal_evidence_sha256,
                    "route_lanes_sha256": array_sha256(
                        np.asarray(causal_input["route_lanes"], dtype=np.float32)
                    ),
                    "route_lanes_speed_limit_sha256": array_sha256(
                        np.asarray(
                            causal_input["route_lanes_speed_limit"], dtype=np.float32
                        )
                    ),
                    "route_lanes_has_speed_limit_sha256": array_sha256(
                        np.asarray(
                            causal_input["route_lanes_has_speed_limit"], dtype=np.bool_
                        )
                    ),
                }
            )
            causal_signal_atom_input = (
                self.causal_signal_atom_input_provider(scene, tick_index)
                if self.causal_signal_atom_input_provider is not None
                else None
            )
            atom_started = time.perf_counter_ns()
            materialized = self.materialize(
                candidates=candidate_tensor,
                causal_input=causal_input,
                neighbor_predictions=neighbor_tensor,
                neighbor_valid_mask=neighbor_valid,
                signal_mask=signals,
                planned_red_light_cost=red_cost,
                causal_signal_atom_input=causal_signal_atom_input,
                dt=float(scene.dt),
                eligibility_policy=self.selection_policy,
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
                eligibility_mask_name=(
                    "source_valid_mask"
                    if self.selection_policy == V22_SOURCE_VALID_SELECTION
                    else "physical_feasible_mask"
                ),
            )
            receipt["latency_ms"]["selector"] = _elapsed_ms(selector_started)
            receipt.update(
                verify_candidate_tensor_immutable(candidate_tensor, before_sha)
            )
            for mask_key in ("physical_feasible_mask", "source_valid_mask"):
                if mask_key not in selection:
                    raise ValueError(f"selector omitted required {mask_key}")
                raw_mask = np.asarray(selection[mask_key])
                if raw_mask.dtype != np.bool_ or raw_mask.shape != (8,):
                    raise ValueError(
                        f"selector {mask_key} must be strict bool [8]"
                    )
            selected_physical = np.asarray(selection["physical_feasible_mask"])
            selected_source = np.asarray(selection["source_valid_mask"])
            if np.any(selected_physical & ~selected_source):
                raise ValueError(
                    "selector physical feasible mask is not a source-valid subset"
                )
            if not selected_source.any():
                raise ValueError("selector source-valid set is empty")
            selector_diagnostics = {
                "candidate_reasons": [
                    list(value) for value in selection.get("candidate_reasons", [])
                ],
                "physical_feasible_mask": selected_physical.tolist(),
                "source_valid_mask": selected_source.tolist(),
                "source_complete_mask": np.asarray(
                    materialized.get("route_speed_source_eligible_mask", []),
                    dtype=bool,
                ).tolist(),
                "all_k_high_risk": bool(
                    selection.get("all_k_high_risk", False)
                ),
            }
            receipt.update(selector_diagnostics)
            if self.v25_context_sink is not None:
                from camp_core.integrations.diffusion_planner_v25_context import (
                    CONTEXT_SCHEMA_VERSION,
                    RAW_FEATURE_NAMES,
                    build_v25_raw_context,
                )

                context_record = build_v25_raw_context(
                    causal_input=causal_input,
                    candidates=candidate_tensor,
                    source_valid_mask=np.asarray(
                        receipt["source_valid_mask"], dtype=bool
                    ),
                    v2i_signal_timing=self.v25_v2i_signal_timing,
                )
                if len(context_record.source_complete) != len(RAW_FEATURE_NAMES):
                    raise ValueError("V25 context source-complete dimension drifted")
                context_payload = {
                    "schema_version": CONTEXT_SCHEMA_VERSION,
                    "raw_context": context_record.as_dict(),
                    "source_complete": {
                        name: bool(value)
                        for name, value in zip(
                            RAW_FEATURE_NAMES,
                            context_record.source_complete,
                        )
                    },
                    "source_receipt": dict(context_record.source_receipt),
                }
                receipt["v25_context"] = context_payload
                self.v25_context_sink(context_payload)
            if selection.get("status") != "ok":
                reason = str(selection.get("failure_reason") or "selector_failed")
                raise RuntimeError(
                    f"{reason}; selector_diagnostics="
                    f"{json.dumps(selector_diagnostics, sort_keys=True)}"
                )
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
                    "score_contract": str(selection["score_contract"]),
                    "tie_break_contract": str(
                        selection["tie_break_contract"]
                    ),
                    "eligibility_mask_name": str(
                        selection["eligibility_mask_name"]
                    ),
                    "npc_operational_outputs_unchanged": True,
                    "default_turn_indicators_retained": True,
                    "physical_feasible_mask": np.asarray(
                        materialized["physical_feasible_mask"]
                    ).tolist(),
                    "source_valid_mask": np.asarray(
                        materialized["source_valid_mask"]
                    ).tolist(),
                    "source_complete_mask": np.asarray(
                        materialized.get(
                            "route_speed_source_eligible_mask", []
                        ),
                        dtype=bool,
                    ).tolist(),
                    "all_k_high_risk": bool(
                        selection.get("all_k_high_risk", False)
                    ),
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
            if selection.get("normalized_atoms") is not None:
                receipt["normalized_atom_matrix_sha256"] = array_sha256(
                    np.asarray(selection["normalized_atoms"], dtype=np.float64)
                )
            if (
                self.decision_sink is not None
                and tick_index % self.decision_sample_every_ticks == 0
            ):
                atom_matrix = np.asarray(
                    materialized.get("atom_matrix"), dtype=np.float64
                )
                source_valid = np.asarray(
                    receipt["source_valid_mask"]
                )
                atom_source_valid = np.asarray(
                    materialized["atom_source_valid_mask"]
                )
                atom_applicable = np.asarray(
                    materialized["atom_applicable_mask"]
                )
                candidate_row_sha256 = [
                    array_sha256(candidate_tensor[index]) for index in range(8)
                ]
                if atom_matrix.shape != (8, 14) or not np.isfinite(atom_matrix).all():
                    raise ValueError("decision snapshot atom matrix must be finite [8,14]")
                if source_valid.dtype != np.bool_ or source_valid.shape != (8,):
                    raise ValueError("decision snapshot source-valid mask must be strict bool [8]")
                if (
                    atom_source_valid.dtype != np.bool_
                    or atom_applicable.dtype != np.bool_
                    or atom_source_valid.shape != (8, 14)
                    or atom_applicable.shape != (8, 14)
                ):
                    raise ValueError("decision snapshot atom masks must be strict bool [8,14]")
                snapshot = {
                    "schema_version": "v22_native_decision_snapshot_v1",
                    "feature_payload": {
                        "atom_matrix": atom_matrix.tolist(),
                        "source_valid_mask": source_valid.tolist(),
                        "atom_source_valid_mask": atom_source_valid.tolist(),
                        "atom_applicable_mask": atom_applicable.tolist(),
                        "candidate_row_sha256": candidate_row_sha256,
                        "candidate_tensor": candidate_tensor.tolist(),
                        "default_output": np.asarray(default_ego).tolist(),
                        "causal_evidence": causal_evidence,
                    },
                    "sidecar": {
                        "tick_index": tick_index,
                        "route_sha256": self.route_sha256,
                        "default_output_sha256": str(
                            receipt["default_output_sha256"]
                        ),
                        "candidate0_sha256": candidate_row_sha256[0],
                        "default_candidate0_identity": dict(
                            _mapping(receipt, "default_candidate0_identity")
                        ),
                        "candidate_tensor_sha256_before": before_sha,
                        "candidate_tensor_sha256_after": str(
                            receipt["candidate_tensor_sha256_after"]
                        ),
                        "normalized_atom_matrix_sha256": str(
                            receipt["normalized_atom_matrix_sha256"]
                        ),
                        "selected_index": int(receipt["selected_index"]),
                        "selected_trajectory_sha256": str(
                            receipt["selected_trajectory_sha256"]
                        ),
                        "score_contract": str(receipt["score_contract"]),
                        "tie_break_contract": str(
                            selection["tie_break_contract"]
                        ),
                        "scores": list(receipt["scores"]),
                        "causal_input_sha256": str(
                            boundary.receipt["input_sha256"]
                        ),
                        "causal_evidence_sha256": causal_evidence_sha256,
                        "route_lanes_sha256": str(receipt["route_lanes_sha256"]),
                        "route_lanes_speed_limit_sha256": str(
                            receipt["route_lanes_speed_limit_sha256"]
                        ),
                        "route_lanes_has_speed_limit_sha256": str(
                            receipt["route_lanes_has_speed_limit_sha256"]
                        ),
                        "physical_feasible_mask": list(
                            receipt["physical_feasible_mask"]
                        ),
                        "candidate_reasons": [
                            list(value) for value in materialized["candidate_reasons"]
                        ],
                        "source_valid_mask": list(
                            receipt["source_valid_mask"]
                        ),
                        "all_k_high_risk": bool(receipt["all_k_high_risk"]),
                        "causal_signal_atom_input": (
                            None
                            if causal_signal_atom_input is None
                            else dict(causal_signal_atom_input)
                        ),
                        "offline_label_provenance": (
                            "pending_train_only_offline_supervision_sidecar"
                        ),
                    },
                }
                self.decision_sink(snapshot)
                receipt["decision_snapshot_emitted"] = True
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


class NativeDpObserveBatch:
    def __init__(
        self,
        *,
        original_predict_batch: Callable[..., Any],
        state: NativeHookState,
        dump_step_npz: Callable[..., Mapping[str, Any]],
        pre_safety: Callable[[dict[str, Any], Any], None] | None = None,
        scene_adapter: Callable[[Any, int], Mapping[str, Any]] | None = None,
        scene_adapter_model_input_sync: Callable[
            [Any, Any, int], Mapping[str, Any]
        ]
        | None = None,
    ) -> None:
        verify_predict_batch_signature(original_predict_batch)
        self.original_predict_batch = original_predict_batch
        self.state = state
        self.dump_step_npz = dump_step_npz
        self.pre_safety = pre_safety
        self.scene_adapter = scene_adapter
        self.scene_adapter_model_input_sync = scene_adapter_model_input_sync

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
        receipt: dict[str, Any] = {
            "tick_index": self.state.tick_index,
            "status": "running",
            "native_ranked_k8": False,
            "_planning_started_ns": started_ns,
            "latency_ms": {},
        }
        self.state.tick_index += 1
        self.state.receipts.append(receipt)
        try:
            if self.scene_adapter is not None:
                receipt["controlled_scene"] = dict(
                    self.scene_adapter(scene, int(receipt["tick_index"]))
                )
            if self.scene_adapter_model_input_sync is not None:
                if "controlled_scene" not in receipt:
                    raise ValueError("model-input cache sync requires a scene adapter")
                receipt["controlled_scene"]["model_input_cache"] = dict(
                    self.scene_adapter_model_input_sync(
                        scene, map_cache, int(receipt["tick_index"])
                    )
                )
            raw = self.dump_step_npz(
                scene,
                map_cache,
                model_args.future_len,
                predicted_neighbor_num=32,
            )
            boundary = causal_input_receipt(
                raw,
                source_observed_frames=_source_observed_frames(scene),
            )
            receipt["causal_input"] = boundary.receipt
            if self.pre_safety is not None:
                self.pre_safety(receipt, scene)
            inference_started = time.perf_counter_ns()
            result = self.original_predict_batch(
                model,
                model_args,
                scene,
                agent_ids,
                device,
                map_cache=map_cache,
                return_turn_indicators=return_turn_indicators,
                inference_delay=inference_delay,
                turn_indicator_keep_bias=turn_indicator_keep_bias,
            )
            receipt["latency_ms"]["default_inference"] = _elapsed_ms(
                inference_started
            )
            predictions = result[0] if return_turn_indicators else result
            ego_prediction = np.asarray(predictions[scene.ego_agent_id])
            receipt["default_output_sha256"] = array_sha256(ego_prediction)
            receipt["status"] = "ok"
            receipt["latency_ms"]["hook_total"] = _elapsed_ms(started_ns)
            return result
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
    after_tracker: Callable[[dict[str, Any], Any], None] | None = None,
):
    original_predict = replay_module._predict_batch
    original_tracker = replay_module.advance_scene_mpc
    verify_predict_batch_signature(original_predict)
    if dp_repo is not None:
        verify_native_source_hashes(dp_repo, expected_source_hashes)

    def timed_tracker(*args, **kwargs):
        started = time.perf_counter_ns()
        try:
            result = original_tracker(*args, **kwargs)
            if state.receipts:
                receipt = state.receipts[-1]
                if after_tracker is not None:
                    if not args:
                        raise ValueError("native tracker call is missing SceneContext")
                    after_tracker(receipt, args[0])
                receipt["tracker"] = {"status": "ok"}
            return result
        except Exception as exc:
            if state.receipts:
                state.receipts[-1]["tracker"] = {
                    "status": "failed",
                    "failure_reason": str(exc),
                }
            raise
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


def validate_smoke_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "camp_dp_v21_native_smoke_v1":
        raise ValueError("v21 smoke config schema mismatch")
    fixed_dp = _mapping(config, "fixed_dp")
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    if fixed_dp.get("native_source_sha256") != NATIVE_SOURCE_SHA256:
        raise ValueError("fixed DP native source hashes mismatch")
    _asset_entry(fixed_dp, "checkpoint")
    _asset_entry(fixed_dp, "args_json")
    selector = _mapping(config, "selector")
    if selector.get("root_sha256") != (
        "afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7"
    ):
        raise ValueError("selector root mismatch")
    _asset_entry(selector, "atom_scales")
    _asset_entry(selector, "weights")
    if (
        selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
        or selector.get("candidate_k") != 8
    ):
        raise ValueError("selector contract mismatch")
    _asset_entry(config, "map")

    routes = config.get("routes")
    if not isinstance(routes, list) or len(routes) != 2:
        raise ValueError("smoke config requires exactly two routes")
    route_hashes = {route.get("name"): route.get("sha256") for route in routes}
    if route_hashes != _ROUTE_SHA256:
        raise ValueError("frozen route names or hashes mismatch")
    for route in routes:
        _asset_entry_value(route, "route")

    seeds = _mapping(config, "seeds")
    if seeds != {
        "scenario": 3417,
        "candidate": 3418,
        "bootstrap": 3419,
        "formal_forbidden": [11, 12, 13],
    }:
        raise ValueError("frozen seed schedule mismatch")
    if {seeds["scenario"], seeds["candidate"], seeds["bootstrap"]} & {
        11,
        12,
        13,
    }:
        raise ValueError("formal seed is forbidden")

    spawn = _mapping(config, "spawn_config")
    if set(spawn) != SPAWN_CONFIG_FIELDS:
        raise ValueError("SpawnConfig fields do not exactly match native source")
    critical = {
        "seed": 3417,
        "max_steps": 64,
        "advance_mode": "mpc",
        "mpc_horizon_steps": 20,
        "mpc_n_knots": 5,
        "sequential_inference": False,
        "sg_smooth_enabled": False,
        "dump_npz_dir": None,
        "reward_config_path": None,
        "enable_traffic_lights": True,
        "map_refresh_steps": 5,
    }
    if any(spawn.get(name) != value for name, value in critical.items()):
        raise ValueError("critical native SpawnConfig value mismatch")
    protocol = _mapping(config, "protocol")
    if protocol.get("arm_order") != ["dp", "camp"]:
        raise ValueError("paired arm order must be DP then CAMP")
    if protocol.get("route_order") != list(_ROUTE_SHA256):
        raise ValueError("paired route order mismatch")
    if (
        protocol.get("capability_route") != "sample_map_smoke_route"
        or protocol.get("capability_steps") != 1
        or protocol.get("paired_steps") != 64
        or protocol.get("padding_policy") != "native_zero_left_pad_to_31_v1"
        or protocol.get("safety_schema") != "safety_cost_native_v1"
    ):
        raise ValueError("smoke protocol mismatch")
    for name in (
        "claim_authorized",
        "training_authorized",
        "holdout_access_authorized",
        "formal_seeds_authorized",
    ):
        if protocol.get(name) is not False:
            raise ValueError(f"{name} must remain false")


def _v21_compatible_capability_config(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = json.loads(json.dumps(config))
    if normalized.get("schema_version") != "camp_dp_v22_native_capability_v1":
        raise ValueError("v22 capability config schema mismatch")
    selector = _mapping(normalized, "selector")
    if selector.get("selection_policy") != V22_SOURCE_VALID_SELECTION:
        raise ValueError("v22 capability must use source-valid selection")
    if selector.get("role") != "v18_ablation_capability_only":
        raise ValueError("v22 capability selector role mismatch")
    protocol = _mapping(normalized, "protocol")
    if protocol.get("safety_schema") != "safety_cost_native_v22":
        raise ValueError("v22 capability safety schema mismatch")
    if protocol.get("tiny_steps") != 4:
        raise ValueError("v22 tiny capability step count mismatch")
    if protocol.get("route_role") != "diagnostic_v21_observed_not_holdout":
        raise ValueError("v22 capability route role mismatch")

    normalized["schema_version"] = "camp_dp_v21_native_smoke_v1"
    selector.pop("selection_policy")
    selector.pop("role")
    protocol["safety_schema"] = "safety_cost_native_v1"
    protocol.pop("tiny_steps")
    protocol.pop("route_role")
    return normalized


def validate_v22_capability_config(config: Mapping[str, Any]) -> None:
    validate_smoke_config(_v21_compatible_capability_config(config))


def validate_v22_corpus_run_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "camp_dp_v22_native_corpus_run_v1":
        raise ValueError("v22 corpus run config schema mismatch")
    fixed_dp = _mapping(config, "fixed_dp")
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    if fixed_dp.get("native_source_sha256") != NATIVE_SOURCE_SHA256:
        raise ValueError("fixed DP native source hashes mismatch")
    _asset_entry(fixed_dp, "checkpoint")
    _asset_entry(fixed_dp, "args_json")

    selector = _mapping(config, "selector")
    if selector.get("root_sha256") != (
        "afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7"
    ):
        raise ValueError("selector root mismatch")
    _asset_entry(selector, "atom_scales")
    _asset_entry(selector, "weights")
    if (
        selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
        or selector.get("candidate_k") != 8
        or selector.get("selection_policy") != V22_SOURCE_VALID_SELECTION
        or selector.get("role") != "v18_ablation_corpus_collection_only"
    ):
        raise ValueError("v22 corpus selector contract mismatch")
    _asset_entry(config, "map")

    routes = config.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise ValueError("v22 corpus run requires exactly one route")
    route = _asset_entry_value(routes[0], "route")
    if not _is_sha256(route.get("name")):
        raise ValueError("v22 corpus route name must be its identity SHA256")

    seeds = _mapping(config, "seeds")
    seed = seeds.get("scenario")
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or seed < 0
        or seed in {11, 12, 13}
        or seeds
        != {
            "scenario": seed,
            "candidate": seed,
            "bootstrap": seed,
            "formal_forbidden": [11, 12, 13],
        }
    ):
        raise ValueError("v22 corpus seed schedule mismatch")

    spawn = _mapping(config, "spawn_config")
    if set(spawn) != SPAWN_CONFIG_FIELDS:
        raise ValueError("SpawnConfig fields do not exactly match native source")
    critical = {
        "seed": seed,
        "max_steps": 64,
        "advance_mode": "mpc",
        "mpc_horizon_steps": 20,
        "mpc_n_knots": 5,
        "sequential_inference": False,
        "sg_smooth_enabled": False,
        "dump_npz_dir": None,
        "reward_config_path": None,
        "enable_traffic_lights": True,
        "map_refresh_steps": 5,
    }
    if any(spawn.get(name) != value for name, value in critical.items()):
        raise ValueError("critical v22 corpus SpawnConfig value mismatch")

    protocol = _mapping(config, "protocol")
    route_role = protocol.get("route_role")
    corpus_split = {
        "train_corpus_collection": "train",
        "calibration_corpus_collection": "calibration",
    }.get(route_role)
    if (
        protocol.get("corpus_steps") != 64
        or protocol.get("sample_every_ticks") != 5
        or protocol.get("safety_schema") != "safety_cost_native_v22"
        or corpus_split is None
        or protocol.get("training_authorized") is not (corpus_split == "train")
        or protocol.get("calibration_authorized")
        is not (corpus_split == "calibration")
        or protocol.get("holdout_access_authorized") is not False
        or protocol.get("formal_seeds_authorized") is not False
        or protocol.get("claim_authorized") is not False
    ):
        raise ValueError("v22 corpus protocol mismatch")


def validate_v24_corpus_run_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "camp_dp_v24_native_corpus_run_v1":
        raise ValueError("v24 corpus run config schema mismatch")

    seeds = _mapping(config, "seeds")
    seed = seeds.get("scenario")
    if (
        isinstance(seed, bool)
        or seed not in {24001, 24002, 24003, 24004, 24005}
        or seeds
        != {
            "scenario": seed,
            "candidate": seed,
            "bootstrap": seed,
            "formal_forbidden": [11, 12, 13],
        }
    ):
        raise ValueError("v24 corpus seed namespace mismatch")

    routes = config.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise ValueError("v24 corpus run requires exactly one route")
    route = _asset_entry_value(routes[0], "route")
    expected_protocol = {
        "arm_order": ["camp"],
        "route_order": [route.get("name")],
        "corpus_steps": 64,
        "sample_every_ticks": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v24_train_corpus_collection",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_authorized": True,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
    }
    if _mapping(config, "protocol") != expected_protocol:
        raise ValueError("v24 corpus protocol mismatch")
    if _mapping(config, "selector").get("role") != (
        "v24_train_corpus_collection_only"
    ):
        raise ValueError("v24 corpus selector role mismatch")

    normalized = json.loads(json.dumps(config))
    normalized["schema_version"] = "camp_dp_v22_native_corpus_run_v1"
    normalized["selector"]["role"] = "v18_ablation_corpus_collection_only"
    normalized["protocol"]["route_role"] = "train_corpus_collection"
    normalized["protocol"]["sample_every_ticks"] = 5
    validate_v22_corpus_run_config(normalized)


def validate_v24_single_record_source_probe_config(
    config: Mapping[str, Any],
) -> None:
    if config.get("schema_version") != "camp_dp_v24_single_record_source_probe_v1":
        raise ValueError("v24 single-record source-probe schema mismatch")
    fixed_dp = _mapping(config, "fixed_dp")
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    if fixed_dp.get("native_source_sha256") != NATIVE_SOURCE_SHA256:
        raise ValueError("fixed DP native source hashes mismatch")
    _asset_entry(fixed_dp, "checkpoint")
    _asset_entry(fixed_dp, "args_json")

    selector = _mapping(config, "selector")
    if selector.get("root_sha256") != (
        "afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7"
    ):
        raise ValueError("v24 probe baseline root mismatch")
    _asset_entry(selector, "atom_scales")
    _asset_entry(selector, "weights")
    if (
        selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
        or selector.get("candidate_k") != 8
        or selector.get("selection_policy") != V22_SOURCE_VALID_SELECTION
        or selector.get("role") != "v24_read_only_baseline_source_probe"
    ):
        raise ValueError("v24 probe selector contract mismatch")
    _asset_entry(config, "map")

    routes = config.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise ValueError("v24 probe requires exactly one route")
    route = _asset_entry_value(routes[0], "route")
    if not _is_sha256(route.get("name")):
        raise ValueError("v24 probe route name must be its identity SHA256")

    seeds = _mapping(config, "seeds")
    if seeds != {
        "scenario": 24001,
        "candidate": 24001,
        "bootstrap": 24001,
        "formal_forbidden": [11, 12, 13],
    }:
        raise ValueError("v24 probe seed namespace mismatch")

    spawn = _mapping(config, "spawn_config")
    if set(spawn) != SPAWN_CONFIG_FIELDS:
        raise ValueError("SpawnConfig fields do not exactly match native source")
    critical = {
        "seed": 24001,
        "max_steps": 1,
        "advance_mode": "mpc",
        "mpc_horizon_steps": 20,
        "mpc_n_knots": 5,
        "sequential_inference": False,
        "sg_smooth_enabled": False,
        "dump_npz_dir": None,
        "reward_config_path": None,
        "enable_traffic_lights": True,
        "map_refresh_steps": 5,
    }
    if any(spawn.get(name) != value for name, value in critical.items()):
        raise ValueError("critical v24 probe SpawnConfig value mismatch")

    protocol = _mapping(config, "protocol")
    expected_protocol = {
        "arm_order": ["camp"],
        "route_order": [route["name"]],
        "capability_route": route["name"],
        "capability_steps": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v24_source_only_single_record_probe",
        "route_selection_rule": "lexicographic_map_family_identity_record_key",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_authorized": False,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
    }
    if protocol != expected_protocol:
        raise ValueError("v24 single-record source-probe protocol mismatch")


def validate_v25_controlled_capability_config(
    config: Mapping[str, Any],
) -> None:
    if config.get("schema_version") != "camp_dp_v25_controlled_capability_v1":
        raise ValueError("v25 controlled capability schema mismatch")
    fixed_dp = _mapping(config, "fixed_dp")
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    if fixed_dp.get("native_source_sha256") != NATIVE_SOURCE_SHA256:
        raise ValueError("fixed DP native source hashes mismatch")
    _asset_entry(fixed_dp, "checkpoint")
    _asset_entry(fixed_dp, "args_json")

    selector = _mapping(config, "selector")
    _asset_entry(selector, "atom_scales")
    _asset_entry(selector, "weights")
    if (
        selector.get("root_sha256")
        != "afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7"
        or selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
        or selector.get("candidate_k") != 8
        or selector.get("selection_policy") != V22_SOURCE_VALID_SELECTION
        or selector.get("role") != "v25_controlled_capability_probe_only"
    ):
        raise ValueError("v25 controlled capability selector contract mismatch")
    _asset_entry(config, "map")

    routes = config.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise ValueError("v25 controlled capability requires exactly one route")
    route = _asset_entry_value(routes[0], "route")
    if not _is_sha256(route.get("name")):
        raise ValueError("v25 controlled capability route name must be SHA256")

    controlled = _mapping(config, "controlled_scenario")
    from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
        validate_controlled_scenario_case,
    )

    validate_controlled_scenario_case(controlled)
    if controlled.get("split") != "pilot_development":
        raise ValueError("v25 controlled capability may use only pilot development")
    if controlled.get("runner_eligible") is not True:
        raise ValueError("v25 controlled capability scenario is source-ineligible")

    seeds = _mapping(config, "seeds")
    if seeds != {
        "scenario": 25991,
        "candidate": 25991,
        "bootstrap": 25991,
        "formal_forbidden": [11, 12, 13, 24001, 24002, 24003, 24004, 24005],
    }:
        raise ValueError("v25 controlled capability seed namespace mismatch")

    spawn = _mapping(config, "spawn_config")
    if set(spawn) != SPAWN_CONFIG_FIELDS:
        raise ValueError("SpawnConfig fields do not exactly match native source")
    critical = {
        "seed": 25991,
        "max_steps": 1,
        "advance_mode": "mpc",
        "mpc_horizon_steps": 20,
        "mpc_n_knots": 5,
        "sequential_inference": False,
        "sg_smooth_enabled": False,
        "dump_npz_dir": None,
        "reward_config_path": None,
        "enable_traffic_lights": True,
        "map_refresh_steps": 5,
        "max_active_npcs": 0,
        "spawn_probability": 0.0,
        "static_npc_count": 0,
        "parked_vehicles_yaml": None,
    }
    if any(spawn.get(name) != value for name, value in critical.items()):
        raise ValueError("critical v25 controlled SpawnConfig value mismatch")

    protocol = _mapping(config, "protocol")
    expected_protocol = {
        "arm_order": ["camp"],
        "route_order": [route["name"]],
        "capability_route": route["name"],
        "capability_steps": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v25_controlled_outcome_blind_coverage_pilot",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
        "outcomes_used_for_selection": False,
    }
    if protocol != expected_protocol:
        raise ValueError("v25 controlled capability protocol mismatch")


def validate_v25_controlled_train_config(config: Mapping[str, Any]) -> None:
    """Validate a frozen outcome-blind controlled-train corpus run."""
    if config.get("schema_version") != "camp_dp_v25_controlled_train_v2":
        raise ValueError("v25 controlled train schema mismatch")
    controlled = _mapping(config, "controlled_scenario")
    from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
        validate_controlled_scenario_case,
    )

    validate_controlled_scenario_case(controlled)
    if (
        controlled.get("split") != "train"
        or controlled.get("runner_eligible") is not True
        or controlled.get("retention_role") != "executable"
        or controlled.get("seeds") != [25001]
    ):
        raise ValueError("v25 controlled train case is outside the frozen split")

    routes = config.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise ValueError("v25 controlled train requires exactly one route")
    route = _asset_entry_value(routes[0], "route")
    seeds = _mapping(config, "seeds")
    if seeds != {
        "scenario": 25001,
        "candidate": 25001,
        "bootstrap": 25001,
        "formal_forbidden": [11, 12, 13, 24001, 24002, 24003, 24004, 24005],
    }:
        raise ValueError("v25 controlled train seed namespace mismatch")
    selector = _mapping(config, "selector")
    if (
        selector.get("role")
        != "v25_controlled_train_fixed_static_behavior_policy"
        or selector.get("normalization_contract")
        != "z=clip(raw_atom/generation_behavior_scale,0,10)"
        or selector.get("tie_break_contract")
        != "lowest_eligible_candidate_index"
        or selector.get("atom_scale_contract")
        != "camp_dp_v25_generation_behavior_atom_scales_v2"
    ):
        raise ValueError("v25 controlled train behavior-policy role mismatch")
    spawn = _mapping(config, "spawn_config")
    if (
        set(spawn) != SPAWN_CONFIG_FIELDS
        or spawn.get("seed") != 25001
        or spawn.get("max_steps") != 64
        or spawn.get("max_active_npcs") != 0
        or spawn.get("spawn_probability") != 0.0
        or spawn.get("static_npc_count") != 0
        or spawn.get("parked_vehicles_yaml") is not None
    ):
        raise ValueError("critical v25 controlled train SpawnConfig value mismatch")
    protocol = _mapping(config, "protocol")
    expected_protocol = {
        "arm_order": ["camp"],
        "route_order": [route["name"]],
        "corpus_steps": 64,
        "sample_every_ticks": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v25_controlled_outcome_blind_train_corpus",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_data_generation_authorized": True,
        "selector_training_execution_authorized": False,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "fresh_b_opened": False,
        "outcomes_used_for_selection": False,
        "context_schema_version": "camp_dp_v25_causal_context_raw_v2",
        "context_mode": "no_v2i",
    }
    if protocol != expected_protocol:
        raise ValueError("v25 controlled train protocol mismatch")

    # Reuse the already-audited common fixed-DP/selector/route contract by
    # normalizing only the train-specific fields to the capability contract.
    normalized = json.loads(json.dumps(config))
    normalized["schema_version"] = "camp_dp_v25_controlled_capability_v1"
    normalized["selector"]["role"] = "v25_controlled_capability_probe_only"
    normalized["controlled_scenario"]["split"] = "pilot_development"
    normalized["seeds"] = {
        "scenario": 25991,
        "candidate": 25991,
        "bootstrap": 25991,
        "formal_forbidden": [11, 12, 13, 24001, 24002, 24003, 24004, 24005],
    }
    normalized["spawn_config"]["seed"] = 25991
    normalized["spawn_config"]["max_steps"] = 1
    normalized["protocol"] = {
        "arm_order": ["camp"],
        "route_order": [route["name"]],
        "capability_route": route["name"],
        "capability_steps": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v25_controlled_outcome_blind_coverage_pilot",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "formal_seeds_authorized": False,
        "outcomes_used_for_selection": False,
    }
    validate_v25_controlled_capability_config(normalized)


def _validate_native_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") == "camp_dp_v25_controlled_train_v2":
        validate_v25_controlled_train_config(config)
        return
    if config.get("schema_version") == "camp_dp_v25_controlled_capability_v1":
        validate_v25_controlled_capability_config(config)
        return
    if config.get("schema_version") == "camp_dp_v24_single_record_source_probe_v1":
        validate_v24_single_record_source_probe_config(config)
        return
    if config.get("schema_version") == "camp_dp_v22_native_capability_v1":
        validate_v22_capability_config(config)
        return
    if config.get("schema_version") == "camp_dp_v22_native_corpus_run_v1":
        validate_v22_corpus_run_config(config)
        return
    if config.get("schema_version") == "camp_dp_v24_native_corpus_run_v1":
        validate_v24_corpus_run_config(config)
        return
    if config.get("schema_version") == "camp_dp_v22_native_evaluation_run_v1":
        validate_v22_evaluation_run_config(config)
        return
    if config.get("schema_version") == "camp_dp_v24_native_evaluation_run_v1":
        validate_v24_evaluation_run_config(config)
        return
    validate_smoke_config(config)


def validate_v22_evaluation_run_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "camp_dp_v22_native_evaluation_run_v1":
        raise ValueError("v22 evaluation run schema mismatch")
    fixed_dp = _mapping(config, "fixed_dp")
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    if fixed_dp.get("native_source_sha256") != NATIVE_SOURCE_SHA256:
        raise ValueError("fixed DP native source hashes mismatch")
    _asset_entry(fixed_dp, "checkpoint")
    _asset_entry(fixed_dp, "args_json")
    _asset_entry(config, "map")
    selector = _mapping(config, "selector")
    _asset_entry(selector, "atom_scales")
    _asset_entry(selector, "weights")
    if (
        not _is_sha256(selector.get("root_sha256"))
        or not _is_sha256(selector.get("model_sha256"))
        or selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
        or selector.get("candidate_k") != 8
        or selector.get("selection_policy") != V22_SOURCE_VALID_SELECTION
        or selector.get("role") != "v22_primary_frozen"
    ):
        raise ValueError("v22 evaluation selector contract mismatch")
    routes = config.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise ValueError("v22 evaluation requires exactly one route")
    _asset_entry_value(routes[0], "route")
    seeds = _mapping(config, "seeds")
    seed = seeds.get("scenario")
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or seed < 0
        or seed in {11, 12, 13}
        or seeds
        != {
            "scenario": seed,
            "candidate": seed,
            "bootstrap": seed,
            "formal_forbidden": [11, 12, 13],
        }
    ):
        raise ValueError("v22 evaluation seed schedule mismatch")
    protocol = _mapping(config, "protocol")
    split = protocol.get("evaluation_split")
    mode = protocol.get("evaluation_mode")
    steps = protocol.get("evaluation_steps")
    if (
        split not in {"calibration", "holdout"}
        or mode not in {"capability", "pilot", "main"}
        or isinstance(steps, bool)
        or not isinstance(steps, int)
        or steps not in {1, 4, 64}
        or protocol.get("arm_order") != ["dp", "camp"]
        or protocol.get("safety_schema") != "safety_cost_native_v22"
        or protocol.get("route_retention")
        != "all_preregistered_routes_and_failures"
        or protocol.get("training_authorized") is not False
        or protocol.get("formal_seeds_authorized") is not False
        or protocol.get("claim_authorized") is not False
        or protocol.get("holdout_access_authorized") is not (mode == "main")
        or (mode == "main") is not (split == "holdout")
    ):
        raise ValueError("v22 evaluation protocol mismatch")
    spawn = _mapping(config, "spawn_config")
    if set(spawn) != SPAWN_CONFIG_FIELDS:
        raise ValueError("SpawnConfig fields do not exactly match native source")
    critical = {
        "seed": seed,
        "max_steps": steps,
        "advance_mode": "mpc",
        "mpc_horizon_steps": 20,
        "mpc_n_knots": 5,
        "sequential_inference": False,
        "sg_smooth_enabled": False,
        "dump_npz_dir": None,
        "reward_config_path": None,
        "enable_traffic_lights": True,
        "map_refresh_steps": 5,
    }
    if any(spawn.get(name) != value for name, value in critical.items()):
        raise ValueError("critical v22 evaluation SpawnConfig value mismatch")


def validate_v24_evaluation_run_config(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "camp_dp_v24_native_evaluation_run_v1":
        raise ValueError("v24 evaluation run schema mismatch")
    fixed_dp = _mapping(config, "fixed_dp")
    if fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    if fixed_dp.get("native_source_sha256") != NATIVE_SOURCE_SHA256:
        raise ValueError("fixed DP native source hashes mismatch")
    _asset_entry(fixed_dp, "checkpoint")
    _asset_entry(fixed_dp, "args_json")
    map_asset = _asset_entry(config, "map")
    if (
        not isinstance(map_asset.get("map_family_id"), str)
        or not map_asset.get("map_family_id")
        or not _is_sha256(map_asset.get("logical_map_sha256"))
        or not _is_sha256(map_asset.get("corridor_group_sha256"))
    ):
        raise ValueError("v24 evaluation map-family/corridor metadata mismatch")
    selector = _mapping(config, "selector")
    _asset_entry(selector, "atom_scales")
    _asset_entry(selector, "weights")
    if (
        not _is_sha256(selector.get("root_sha256"))
        or not _is_sha256(selector.get("model_sha256"))
        or selector.get("score_contract") != "score_k(w)=a_k^T w"
        or selector.get("nonnegative_simplex") is not True
        or selector.get("candidate_k") != 8
        or selector.get("selection_policy") != V22_SOURCE_VALID_SELECTION
        or selector.get("role") != "v24_primary_frozen_train_only"
    ):
        raise ValueError("v24 evaluation selector contract mismatch")
    routes = config.get("routes")
    if not isinstance(routes, list) or len(routes) != 1:
        raise ValueError("v24 evaluation requires exactly one route")
    route = _asset_entry_value(routes[0], "route")
    if not _is_sha256(route.get("name")):
        raise ValueError("v24 evaluation route name must be its identity SHA256")
    seeds = _mapping(config, "seeds")
    seed = seeds.get("scenario")
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or seed < 0
        or seed in {11, 12, 13}
        or seeds
        != {
            "scenario": seed,
            "candidate": seed,
            "bootstrap": seed,
            "formal_forbidden": [11, 12, 13],
        }
    ):
        raise ValueError("v24 evaluation seed schedule mismatch")
    protocol = _mapping(config, "protocol")
    mode = protocol.get("evaluation_mode")
    split = protocol.get("evaluation_split")
    steps = protocol.get("evaluation_steps")
    allowed_seeds = {
        "capability": {24101},
        "pilot": {24101},
        "main": {24201, 24202, 24203, 24204, 24205},
    }
    expected_split = {
        "capability": "calibration",
        "pilot": "calibration",
        "main": "holdout",
    }
    expected_steps = {"capability": 1, "pilot": 64, "main": 64}
    arm_order = protocol.get("arm_order")
    execution_authorized = protocol.get("execution_authorized")
    holdout_authorized = protocol.get("holdout_access_authorized")
    if (
        mode not in allowed_seeds
        or split != expected_split.get(mode)
        or seed not in allowed_seeds.get(mode, set())
        or steps != expected_steps.get(mode)
        or arm_order not in (["dp", "camp"], ["camp", "dp"])
        or not _is_sha256(protocol.get("arm_order_rank_sha256"))
        or protocol.get("independent_reset_per_arm") is not True
        or protocol.get("same_initial_state_and_exogenous_seed_per_pair")
        is not True
        or protocol.get("safety_schema") != "safety_cost_native_v22"
        or protocol.get("route_retention")
        != "all_preregistered_routes_and_failures_no_replacement"
        or protocol.get("training_authorized") is not False
        or protocol.get("calibration_tuning_authorized") is not False
        or not isinstance(execution_authorized, bool)
        or not isinstance(holdout_authorized, bool)
        or protocol.get("formal_seeds_authorized") is not False
        or protocol.get("candidate_tensor_modification_authorized") is not False
        or protocol.get("trajectory_postprocess_authorized") is not False
        or protocol.get("per_arm_candidate_tensor_immutability_required")
        is not True
        or protocol.get("per_arm_candidate0_default_identity_required")
        is not True
        or protocol.get("t0_cross_arm_input_and_candidate_hash_identity_required")
        is not True
        or protocol.get("post_divergence_cross_arm_tensor_identity_required")
        is not False
        or protocol.get("native_ranked_k8_provenance_claim_authorized")
        is not False
        or protocol.get("latency_comparison_authorized") is not False
        or protocol.get("latency_reporting_role")
        != "descriptive_instrumented_only"
        or protocol.get("claim_authorized") is not False
        or (not execution_authorized and holdout_authorized)
        or (execution_authorized and mode == "main") is not holdout_authorized
        or (mode != "main" and holdout_authorized)
    ):
        raise ValueError("v24 evaluation protocol mismatch")
    spawn = _mapping(config, "spawn_config")
    if set(spawn) != SPAWN_CONFIG_FIELDS:
        raise ValueError("SpawnConfig fields do not exactly match native source")
    critical = {
        "seed": seed,
        "max_steps": steps,
        "advance_mode": "mpc",
        "mpc_horizon_steps": 20,
        "mpc_n_knots": 5,
        "sequential_inference": False,
        "sg_smooth_enabled": False,
        "dump_npz_dir": None,
        "reward_config_path": None,
        "enable_traffic_lights": True,
        "map_refresh_steps": 5,
    }
    if any(spawn.get(name) != value for name, value in critical.items()):
        raise ValueError("critical v24 evaluation SpawnConfig value mismatch")


def _selection_policy(config: Mapping[str, Any]) -> str:
    policy = _mapping(config, "selector").get(
        "selection_policy", V21_PHYSICAL_SELECTION
    )
    if policy not in _SELECTION_POLICIES:
        raise ValueError("unknown selection policy")
    return str(policy)


def verify_config_assets(config: Mapping[str, Any]) -> dict[str, str]:
    _validate_native_config(config)
    fixed_dp = _mapping(config, "fixed_dp")
    dp_repo = Path(str(fixed_dp["repo"]))
    head = subprocess.run(
        ["git", "-C", str(dp_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD mismatch")
    tracked = subprocess.run(
        ["git", "-C", str(dp_repo), "status", "--short", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if tracked:
        raise ValueError("fixed DP tracked worktree is dirty")
    verified = verify_native_source_hashes(
        dp_repo, fixed_dp["native_source_sha256"]
    )
    for entry in (
        fixed_dp["checkpoint"],
        fixed_dp["args_json"],
        config["map"],
        _mapping(config, "selector")["atom_scales"],
        _mapping(config, "selector")["weights"],
        *config["routes"],
    ):
        path = Path(str(entry["path"]))
        digest = _file_sha256(path)
        if digest != entry["sha256"]:
            raise ValueError(f"asset SHA256 mismatch: {path}")
        verified[str(path)] = digest
    selector = _mapping(config, "selector")
    scales, _scale_contract = _load_frozen_selector_scales(
        Path(str(selector["atom_scales"]["path"]))
    )
    if config.get("schema_version") == "camp_dp_v25_controlled_train_v2":
        from camp_core.integrations.diffusion_planner_causal_atoms import (
            validate_v25_atom_scales,
        )

        validate_v25_atom_scales(scales)
    _load_frozen_selector_weights(Path(str(selector["weights"]["path"])))
    selector_sums = Path(str(selector["root"])) / "SHA256SUMS"
    selector_root = _file_sha256(selector_sums)
    if selector_root != selector["root_sha256"]:
        raise ValueError("selector root SHA256 mismatch")
    verified[str(selector_sums)] = selector_root
    verified["fixed_dp_head"] = head
    return verified


def validate_pair_receipts(
    dp_receipt: Mapping[str, Any], camp_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    _validate_arm_receipt(dp_receipt, "dp")
    _validate_arm_receipt(camp_receipt, "camp")
    if dp_receipt["route_name"] != camp_receipt["route_name"] or dp_receipt[
        "route_sha256"
    ] != camp_receipt["route_sha256"]:
        raise ValueError("paired route mismatch")
    if (
        dp_receipt["initial_state_sha256"]
        != camp_receipt["initial_state_sha256"]
        or dp_receipt["initial_input_sha256"]
        != camp_receipt["initial_input_sha256"]
    ):
        raise ValueError("paired initial state/input mismatch")
    delta = paired_safety_delta(
        float(dp_receipt["safety"]["safety_cost"]),
        float(camp_receipt["safety"]["safety_cost"]),
    )
    return {
        "schema_version": "v21_native_pair_receipt_v1",
        "route_name": dp_receipt["route_name"],
        "route_sha256": dp_receipt["route_sha256"],
        "initial_state_sha256": dp_receipt["initial_state_sha256"],
        "initial_input_sha256": dp_receipt["initial_input_sha256"],
        "dp_safety": dp_receipt["safety"],
        "camp_safety": camp_receipt["safety"],
        "paired_delta": delta,
        "claim_authorized": False,
    }


def execute_smoke(
    config: Mapping[str, Any],
    output_dir: str | Path,
    *,
    mode: str,
    run_arm: Callable[..., Mapping[str, Any]] | None,
    verified_assets: Mapping[str, str] | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    _validate_native_config(config)
    if mode not in {
        "preflight",
        "capability-smoke",
        "tiny-capability-smoke",
        "paired-smoke",
    }:
        raise ValueError("unsupported v21 native smoke mode")
    output = Path(output_dir)
    staging = output.with_name(output.name + ".tmp")
    if output.exists() or staging.exists():
        raise FileExistsError(f"evidence target already exists: {output}")
    staging.mkdir(parents=True)
    arms: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    expected_selection_policy = (
        _selection_policy(config)
        if config.get("schema_version")
        in {
            "camp_dp_v22_native_capability_v1",
            "camp_dp_v24_single_record_source_probe_v1",
        }
        else None
    )
    try:
        routes = {route["name"]: route for route in config["routes"]}
        if mode == "capability-smoke":
            if run_arm is None:
                raise ValueError("capability smoke requires a native arm runner")
            route = routes[config["protocol"]["capability_route"]]
            receipt = dict(
                run_arm(
                    route=route,
                    arm="camp",
                    config=config,
                    output_dir=staging / "native_runs" / route["name"] / "camp",
                    max_steps=1,
                )
            )
            _validate_arm_receipt(
                receipt,
                "camp",
                expected_ticks=1,
                require_summary=False,
                expected_selection_policy=expected_selection_policy,
            )
            arms.append(receipt)
        elif mode == "tiny-capability-smoke":
            if config.get("schema_version") != "camp_dp_v22_native_capability_v1":
                raise ValueError("tiny capability requires the v22 config")
            if run_arm is None:
                raise ValueError("tiny capability requires a native arm runner")
            tiny_steps = int(config["protocol"]["tiny_steps"])
            for route_name in config["protocol"]["route_order"]:
                route = routes[route_name]
                receipt = dict(
                    run_arm(
                        route=route,
                        arm="camp",
                        config=config,
                        output_dir=staging
                        / "native_runs"
                        / route_name
                        / "camp",
                        max_steps=tiny_steps,
                    )
                )
                _validate_arm_receipt(
                    receipt,
                    "camp",
                    expected_ticks=tiny_steps,
                    expected_selection_policy=expected_selection_policy,
                    expected_safety_schema=str(
                        config["protocol"]["safety_schema"]
                    ),
                )
                arms.append(receipt)
        elif mode == "paired-smoke":
            if run_arm is None:
                raise ValueError("paired smoke requires a native arm runner")
            for route_name in config["protocol"]["route_order"]:
                route = routes[route_name]
                route_arms = {}
                for arm in config["protocol"]["arm_order"]:
                    receipt = dict(
                        run_arm(
                            route=route,
                            arm=arm,
                            config=config,
                            output_dir=staging
                            / "native_runs"
                            / route_name
                            / arm,
                            max_steps=64,
                        )
                    )
                    _validate_arm_receipt(
                        receipt,
                        arm,
                        expected_selection_policy=(
                            expected_selection_policy if arm == "camp" else None
                        ),
                    )
                    route_arms[arm] = receipt
                    arms.append(receipt)
                pairs.append(
                    validate_pair_receipts(route_arms["dp"], route_arms["camp"])
                )

        padding = {"0": 0, "1-5": 0, "6-15": 0, "16-30": 0}
        for arm in arms:
            for tick in arm["ticks"]:
                padded = int(tick["padding"]["padded_frames"])
                padding[_padding_stratum(padded)] += 1
        result: dict[str, Any] = {
            "schema_version": "camp_dp_v21_native_smoke_result_v1",
            "mode": mode,
            "status": "passed",
            "fixed_dp_head": config["fixed_dp"]["head"],
            "route_count": len(pairs) if pairs else len(arms),
            "arm_count": len(arms),
            "padding_strata": padding,
            "claim_authorized": False,
        }
        if verified_assets is not None:
            result["verified_assets"] = dict(verified_assets)
        if pairs:
            result["pairs"] = pairs
            result["aggregate"] = aggregate_paired_safety(
                [pair["paired_delta"] for pair in pairs]
            )
        elif len(arms) == 1:
            result["capability_arm"] = arms[0]
        elif arms:
            result["capability_arms"] = arms
        else:
            result["preflight"] = {"config_valid": True, "asset_checks": "external"}

        arms = _rewrite_evidence_root_paths(arms, staging, output)
        pairs = _rewrite_evidence_root_paths(pairs, staging, output)
        result = _rewrite_evidence_root_paths(result, staging, output)
        _write_evidence_payloads(
            staging,
            config,
            result,
            arms,
            pairs,
            command=command,
        )
        root_sha = _seal_evidence(staging)
        staging.replace(output)
        result["root_sha256"] = root_sha
        return result
    except Exception as exc:
        failure = {
            "schema_version": "camp_dp_v21_native_smoke_failure_v1",
            "mode": mode,
            "status": "failed",
            "failure_reason": str(exc),
            "completed_arm_count": len(arms),
            "completed_pair_count": len(pairs),
            "claim_authorized": False,
        }
        repo_root = Path(__file__).resolve().parents[2]
        camp_head = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        (staging / "HEADS").write_text(
            f"camp_source_head={camp_head}\n"
            f"fixed_dp_head={config['fixed_dp']['head']}\n",
            encoding="ascii",
        )
        (staging / "COMMAND").write_text(
            f"mode={mode}\n{command or 'execute_smoke(injected_run_arm=true)'}\n",
            encoding="utf-8",
        )
        _write_json(staging / "smoke_config.json", config)
        _write_json(staging / "failure.json", failure)
        for arm_receipt in arms:
            route_root = staging / "receipts" / str(arm_receipt["route_name"])
            arm_name = str(arm_receipt["arm"])
            _write_json(route_root / f"{arm_name}.json", arm_receipt)
            for tick in arm_receipt["ticks"]:
                _write_json(
                    route_root
                    / arm_name
                    / f"tick_{int(tick['tick_index']):04d}.json",
                    tick,
                )
        for pair_receipt in pairs:
            _write_json(
                staging
                / "receipts"
                / str(pair_receipt["route_name"])
                / "pair.json",
                pair_receipt,
            )
        (staging / "stderr.txt").write_text(str(exc) + "\n", encoding="utf-8")
        (staging / "stdout.txt").write_text("", encoding="utf-8")
        (staging / "run.exit").write_text("1\n", encoding="ascii")
        _seal_evidence(staging)
        staging.replace(output)
        raise


def _rewrite_evidence_root_paths(value: Any, source: Path, target: Path) -> Any:
    source_text = str(source.resolve())
    target_text = str(target.resolve())
    if isinstance(value, str):
        if value == source_text:
            return target_text
        prefix = source_text + os.sep
        if value.startswith(prefix):
            return target_text + value[len(source_text) :]
        return value
    if isinstance(value, Mapping):
        return {
            key: _rewrite_evidence_root_paths(item, source, target)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_rewrite_evidence_root_paths(item, source, target) for item in value]
    if isinstance(value, tuple):
        return tuple(
            _rewrite_evidence_root_paths(item, source, target) for item in value
        )
    return value


def verify_evidence_hashes(root: str | Path) -> dict[str, Any]:
    directory = Path(root)
    sums = directory / "SHA256SUMS"
    for line in sums.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if _file_sha256(directory / relative) != digest:
            raise ValueError(f"evidence SHA256 mismatch: {relative}")
    root_line = (directory / "ROOT_SHA256SUMS").read_text(encoding="utf-8").strip()
    root_sha, relative = root_line.split("  ", 1)
    if relative != "SHA256SUMS" or _file_sha256(sums) != root_sha:
        raise ValueError("evidence root SHA256 mismatch")
    return {"root_sha256": root_sha, "payload_count": len(sums.read_text().splitlines())}


def _load_frozen_selector_scales(
    path: str | Path,
) -> tuple[np.ndarray, dict[str, Any]]:
    from camp_core.integrations.diffusion_planner import atom_schema_for_dimension

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("selector scale payload must be a mapping")
    scales = np.asarray(payload.get("scales"), dtype=np.float64)
    expected_version, expected_names = atom_schema_for_dimension(14)
    declared_version = payload.get("atom_schema_version")
    if (
        scales.shape != (14,)
        or not np.isfinite(scales).all()
        or np.any(scales <= 0.0)
        or tuple(payload.get("atom_names") or ()) != expected_names
        or declared_version not in {None, expected_version}
    ):
        raise ValueError("frozen selector scale schema mismatch")
    return scales, {
        "declared_atom_schema_version": declared_version,
        "effective_atom_schema_version": expected_version,
        "compatibility_policy": "exact_atom_names_on_frozen_sha_v1",
    }


def _load_frozen_selector_weights(path: str | Path) -> np.ndarray:
    weights = np.load(Path(path), allow_pickle=False)
    if (
        weights.shape != (14,)
        or not np.isfinite(weights).all()
        or np.any(weights < 0.0)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-8)
    ):
        raise ValueError("frozen selector weights must be a nonnegative simplex [14]")
    return np.asarray(weights, dtype=np.float64)


def _mapping(container: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = container.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _asset_entry(container: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    return _asset_entry_value(_mapping(container, name), name)


def _asset_entry_value(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an asset mapping")
    path = value.get("path")
    digest = value.get("sha256")
    if not isinstance(path, str) or not path:
        raise ValueError(f"{name}.path must be nonempty")
    if not _is_sha256(digest):
        raise ValueError(f"{name}.sha256 must be lowercase SHA256")
    return value


def _validate_arm_receipt(
    receipt: Mapping[str, Any],
    arm: str,
    *,
    expected_ticks: int | None = None,
    require_summary: bool = True,
    expected_selection_policy: str | None = None,
    expected_safety_schema: str = "safety_cost_native_v1",
) -> None:
    if receipt.get("status") != "ok":
        raise ValueError(f"{arm} arm failed")
    if receipt.get("arm") != arm:
        raise ValueError(f"arm identity mismatch: expected {arm}")
    if not isinstance(receipt.get("route_name"), str) or not receipt["route_name"]:
        raise ValueError("route_name must be nonempty")
    for name in ("route_sha256", "initial_state_sha256", "initial_input_sha256"):
        value = receipt.get(name)
        if not _is_sha256(value):
            raise ValueError(f"{name} must be lowercase SHA256")
    if receipt.get("claim_authorized") is not False:
        raise ValueError("arm receipt must not authorize a claim")

    ticks = receipt.get("ticks")
    if not isinstance(ticks, list) or not ticks:
        raise ValueError("ticks must be a nonempty list")
    if expected_ticks is not None and len(ticks) != expected_ticks:
        raise ValueError("tick count mismatch")
    indices = [tick.get("tick_index") for tick in ticks if isinstance(tick, Mapping)]
    if indices != list(range(len(ticks))):
        raise ValueError("tick indices must be complete, ordered, and unique")
    if ticks[0].get("input_sha256") != receipt["initial_input_sha256"]:
        raise ValueError("initial input does not match first tick")
    for tick in ticks:
        for name in ("input_sha256",):
            value = tick.get(name)
            if not _is_sha256(value):
                raise ValueError(f"tick {name} must be lowercase SHA256")
        padding = _mapping(tick, "padding")
        observed = padding.get("observed_frames")
        padded = padding.get("padded_frames")
        if (
            not isinstance(observed, int)
            or isinstance(observed, bool)
            or not isinstance(padded, int)
            or isinstance(padded, bool)
            or observed < 1
            or observed > 31
            or padded != 31 - observed
            or padding.get("padding_policy") != "native_zero_left_pad_to_31_v1"
        ):
            raise ValueError("invalid causal padding receipt")
        if _mapping(tick, "tracker").get("status") != "ok":
            raise ValueError("tracker receipt is not ok")
        if (
            require_summary
            and _mapping(tick, "safety").get("source_complete") is not True
        ):
            raise ValueError("safety sources are incomplete")
        latency = _mapping(tick, "latency_ms")
        if not latency:
            raise ValueError("latency receipt is empty")
        for value in latency.values():
            number = float(value)
            if not np.isfinite(number) or number < 0.0:
                raise ValueError("latency must be finite and nonnegative")
        if arm == "camp":
            for name in (
                "candidate_tensor_sha256_before",
                "candidate_tensor_sha256_after",
                "atom_matrix_sha256",
                "normalized_atom_matrix_sha256",
                "selected_trajectory_sha256",
            ):
                value = tick.get(name)
                if not _is_sha256(value):
                    raise ValueError(f"CAMP tick {name} must be lowercase SHA256")
            if (
                tick["candidate_tensor_sha256_before"]
                != tick["candidate_tensor_sha256_after"]
            ):
                raise ValueError("CAMP candidate tensor was modified")
            if expected_selection_policy is not None:
                if tick.get("selection_policy") != expected_selection_policy:
                    raise ValueError("CAMP selection policy mismatch")
                selected_index = tick.get("selected_index")
                if (
                    isinstance(selected_index, bool)
                    or not isinstance(selected_index, int)
                    or not 0 <= selected_index < 8
                ):
                    raise ValueError("CAMP selected index is outside fixed K=8")
                masks = {}
                for name in (
                    "source_valid_mask",
                    "physical_feasible_mask",
                    "source_complete_mask",
                ):
                    values = tick.get(name)
                    if (
                        not isinstance(values, list)
                        or len(values) != 8
                        or any(not isinstance(value, bool) for value in values)
                    ):
                        raise ValueError(f"CAMP {name} must be a boolean K=8 mask")
                    masks[name] = values
                if not masks["source_valid_mask"][selected_index]:
                    raise ValueError("CAMP selected a source-invalid candidate")
                expected_mask_name = (
                    "source_valid_mask"
                    if expected_selection_policy == V22_SOURCE_VALID_SELECTION
                    else "physical_feasible_mask"
                )
                scores = np.asarray(tick.get("scores"), dtype=np.float64)
                row_sha256 = tick.get("candidate_row_sha256")
                if (
                    tick.get("score_contract")
                    != "score_k=clip(a_k/s,0,10)^T w"
                    or tick.get("tie_break_contract")
                    != "lowest_eligible_candidate_index"
                    or tick.get("eligibility_mask_name") != expected_mask_name
                    or scores.shape != (8,)
                    or not np.isfinite(scores).all()
                    or not isinstance(row_sha256, list)
                    or len(row_sha256) != 8
                    or any(not _is_sha256(value) for value in row_sha256)
                ):
                    raise ValueError("CAMP affine score receipt is invalid")
                eligible = np.asarray(masks[expected_mask_name], dtype=bool)
                expected_index = int(np.argmin(np.where(eligible, scores, np.inf)))
                if selected_index != expected_index:
                    raise ValueError("CAMP selected index is not the affine argmin")
                if tick["selected_trajectory_sha256"] != row_sha256[selected_index]:
                    raise ValueError("CAMP selected trajectory is not the indexed row")
                identity = _mapping(tick, "default_candidate0_identity")
                default_sha = tick.get("default_output_sha256")
                if (
                    identity.get("elementwise_equal") is not True
                    or float(identity.get("max_abs_difference", float("nan"))) != 0.0
                    or identity.get("native_ranked_k8") is not False
                    or not _is_sha256(default_sha)
                    or identity.get("default_output_sha256") != default_sha
                    or identity.get("candidate0_sha256") != default_sha
                ):
                    raise ValueError("DP operational default/candidate 0 identity failed")
                expected_high_risk = bool(
                    np.asarray(masks["source_valid_mask"], dtype=bool).all()
                    and not np.asarray(
                        masks["physical_feasible_mask"], dtype=bool
                    ).any()
                )
                if (
                    not isinstance(tick.get("all_k_high_risk"), bool)
                    or tick["all_k_high_risk"] != expected_high_risk
                ):
                    raise ValueError("all_k_high_risk receipt mismatch")

    if not require_summary:
        return
    safety = _mapping(receipt, "safety")
    if safety.get("schema_version") != expected_safety_schema:
        raise ValueError("safety schema mismatch")
    components = _mapping(safety, "components")
    expected_cost = safety_cost_native_v1(components)
    actual_cost = float(safety.get("safety_cost"))
    if not np.isfinite(actual_cost) or not np.isclose(
        actual_cost, expected_cost, rtol=0.0, atol=1e-12
    ):
        raise ValueError("safety cost does not match components")
    if expected_safety_schema == "safety_cost_native_v22":
        speed = _mapping(safety, "speed_protocol")
        if (
            speed.get("schema_version") != "speed_protocol_v22"
            or float(speed.get("operational_tolerance_mps", float("nan"))) != 0.1
        ):
            raise ValueError("v22 operational speed protocol mismatch")
    _mapping(receipt, "secondary")
    _mapping(receipt, "latency")


def validate_native_arm_receipt(
    receipt: Mapping[str, Any],
    arm: str,
    *,
    expected_ticks: int,
    require_summary: bool = True,
    expected_selection_policy: str | None = None,
    expected_safety_schema: str = "safety_cost_native_v22",
) -> None:
    _validate_arm_receipt(
        receipt,
        arm,
        expected_ticks=expected_ticks,
        require_summary=require_summary,
        expected_selection_policy=expected_selection_policy,
        expected_safety_schema=expected_safety_schema,
    )


def canonical_spawn_config_sha256(
    config: Mapping[str, Any], max_steps: int
) -> str:
    return hashlib.sha256(
        json.dumps(
            {**config["spawn_config"], "max_steps": int(max_steps)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _padding_stratum(padded_frames: int) -> str:
    if padded_frames == 0:
        return "0"
    if 1 <= padded_frames <= 5:
        return "1-5"
    if 6 <= padded_frames <= 15:
        return "6-15"
    if 16 <= padded_frames <= 30:
        return "16-30"
    raise ValueError("padded_frames is outside [0, 30]")


def _write_evidence_payloads(
    root: Path,
    config: Mapping[str, Any],
    result: Mapping[str, Any],
    arms: list[Mapping[str, Any]],
    pairs: list[Mapping[str, Any]],
    *,
    command: str | None,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    camp_head = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (root / "HEADS").write_text(
        f"camp_source_head={camp_head}\nfixed_dp_head={config['fixed_dp']['head']}\n",
        encoding="ascii",
    )
    (root / "COMMAND").write_text(
        f"mode={result['mode']}\n{command or 'execute_smoke(injected_run_arm=true)'}\n",
        encoding="utf-8",
    )
    _write_json(root / "smoke_config.json", config)
    _write_json(root / "summary.json", result)
    summary = (
        "# CAMP/DP v21 native simulator smoke\n\n"
        f"- mode: `{result['mode']}`\n"
        f"- status: `{result['status']}`\n"
        f"- routes: `{result['route_count']}`\n"
        f"- arms: `{result['arm_count']}`\n"
        "- claim authorized: `false`\n"
    )
    (root / "summary.md").write_text(summary, encoding="utf-8")
    (root / "stdout.txt").write_text(
        json.dumps(result, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    (root / "stderr.txt").write_text("", encoding="utf-8")
    (root / "run.exit").write_text("0\n", encoding="ascii")
    for arm in arms:
        route_name = str(arm["route_name"])
        arm_name = str(arm["arm"])
        route_root = root / "receipts" / route_name
        _write_json(route_root / f"{arm_name}.json", arm)
        for tick in arm["ticks"]:
            _write_json(
                route_root / arm_name / f"tick_{int(tick['tick_index']):04d}.json",
                tick,
            )
    for pair in pairs:
        _write_json(root / "receipts" / str(pair["route_name"]) / "pair.json", pair)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _seal_evidence(root: Path) -> str:
    excluded = {"SHA256SUMS", "ROOT_SHA256SUMS"}
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in excluded
    )
    lines = [f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}" for path in files]
    sums = root / "SHA256SUMS"
    with sums.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    root_sha = _file_sha256(sums)
    with (root / "ROOT_SHA256SUMS").open(
        "w", encoding="ascii", newline="\n"
    ) as handle:
        handle.write(f"{root_sha}  SHA256SUMS\n")
    return root_sha


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256_HEX


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


def build_native_arm_runner(
    config: Mapping[str, Any], *, device: str
) -> Callable[..., Mapping[str, Any]]:
    _validate_native_config(config)
    if device not in {"cpu", "cuda"}:
        raise ValueError("device must be cpu or cuda")
    runtime: dict[str, Any] = {}

    def ensure_runtime() -> Mapping[str, Any]:
        if runtime:
            return runtime
        fixed_dp = _mapping(config, "fixed_dp")
        dp_repo = Path(str(fixed_dp["repo"]))
        for path in (dp_repo, dp_repo / "diffusion_planner"):
            value = str(path)
            if value not in sys.path:
                sys.path.insert(0, value)
        annotation_compatibility = _install_fixed_dp_annotation_compatibility(
            dp_repo
        )
        import torch
        import scenario_generation.replay as replay
        import scenario_generation.tensor_converter as tensor_converter
        from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
        from scenario_generation.route import Route

        from camp_core.integrations.diffusion_planner import (
            install_lanelet2_projection_fallback,
            require_source_preserving_lanelet2_regulatory_adapter,
        )
        from camp_core.integrations.diffusion_planner_causal_atoms import (
            materialize_canonical_14d,
        )
        from scripts.integrations.run_diffusion_planner_camp_replay import (
            _load_model,
        )
        from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (
            _fixed_dp_red_cost,
            candidate_signal_source_available_mask,
        )
        from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (
            select_camp_candidate,
        )

        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable")
        model, model_args = _load_model(
            Path(str(fixed_dp["checkpoint"]["path"])),
            Path(str(fixed_dp["args_json"]["path"])),
            device,
        )
        runtime.update(
            {
                "torch": torch,
                "replay": replay,
                "tensor_converter": tensor_converter,
                "LaneletSceneBuilder": LaneletSceneBuilder,
                "Route": Route,
                "install_projection": install_lanelet2_projection_fallback,
                "prepare_regulatory": (
                    require_source_preserving_lanelet2_regulatory_adapter
                ),
                "materialize": materialize_canonical_14d,
                "red_cost": _fixed_dp_red_cost,
                "signal_mask": candidate_signal_source_available_mask,
                "select": select_camp_candidate,
                "model": model,
                "model_args": model_args,
                "annotation_compatibility": (
                    "process_local_postponed_annotations_fixed_dp_source_only"
                    if annotation_compatibility is not None
                    else "not_required_python310_or_newer"
                ),
            }
        )
        return runtime

    def run_arm(
        *,
        route: Mapping[str, Any],
        arm: str,
        config: Mapping[str, Any],
        output_dir: Path,
        max_steps: int,
        decision_sink: Callable[[Mapping[str, Any]], None] | None = None,
        scene_adapter: Callable[[Any, int], Mapping[str, Any]] | None = None,
        v25_context_sink: Callable[[Mapping[str, Any]], None] | None = None,
        causal_input_sink: Callable[
            [int, Mapping[str, Any]], None
        ]
        | None = None,
    ) -> Mapping[str, Any]:
        if arm not in {"dp", "camp"}:
            raise ValueError("arm must be dp or camp")
        protocol = _mapping(config, "protocol")
        if config.get("schema_version") in {
            "camp_dp_v24_single_record_source_probe_v1",
            "camp_dp_v25_controlled_capability_v1",
        }:
            allowed_steps = {1}
        elif config.get("schema_version") == "camp_dp_v25_controlled_train_v2":
            allowed_steps = {int(protocol["corpus_steps"])}
        elif config.get("schema_version") in {
            "camp_dp_v22_native_corpus_run_v1",
            "camp_dp_v24_native_corpus_run_v1",
        }:
            allowed_steps = {int(protocol["corpus_steps"])}
        elif config.get("schema_version") in {
            "camp_dp_v22_native_evaluation_run_v1",
            "camp_dp_v24_native_evaluation_run_v1",
        }:
            allowed_steps = {int(protocol["evaluation_steps"])}
        else:
            allowed_steps = {1, int(protocol["paired_steps"])}
            if "tiny_steps" in protocol:
                allowed_steps.add(int(protocol["tiny_steps"]))
        if max_steps not in allowed_steps:
            raise ValueError("native smoke step count is not frozen")
        if (
            config.get("schema_version") == "camp_dp_v24_native_evaluation_run_v1"
            and protocol.get("execution_authorized") is not True
        ):
            raise ValueError("v24 evaluation run config is static-preflight disabled")
        context = ensure_runtime()
        replay = context["replay"]
        route_object = context["Route"].load(Path(str(route["path"])))
        map_path = Path(str(config["map"]["path"]))
        context["prepare_regulatory"](map_path)
        context["install_projection"](map_path)
        builder = context["LaneletSceneBuilder"](str(map_path))
        spawn_config = replay.SpawnConfig(**dict(config["spawn_config"]))
        spawn_config.max_steps = max_steps
        spawn_config.validate()
        state = NativeHookState()
        route_ids = list(route_object.route_lanelet_ids or ())
        if not route_ids:
            raise ValueError("frozen smoke route is unresolved")

        def pre_safety(receipt: dict[str, Any], scene: Any) -> None:
            _capture_pre_safety(receipt, scene, builder, route_ids, replay)

        def after_tracker(receipt: dict[str, Any], scene: Any) -> None:
            _capture_post_safety(receipt, scene, builder, route_ids, replay)

        runtime_scene_adapter = scene_adapter
        if scene_adapter is not None and hasattr(
            scene_adapter, "bind_runtime_lanelet_ids"
        ):
            def runtime_scene_adapter(scene: Any, tick_index: int) -> Mapping[str, Any]:
                forward_route_ids = builder.select_route_segment_indices(
                    route_ids,
                    scene.ego_agent.current_position,
                    max_segments=25,
                ) or route_ids[:25]
                forward_route_ids = [
                    lanelet_id
                    for lanelet_id in forward_route_ids
                    if lanelet_id in builder._cache
                ][:25]
                scene_adapter.bind_runtime_lanelet_ids(
                    route_lanelet_ids=forward_route_ids,
                    map_lanelet_ids=builder._last_map_data_ids,
                )
                return scene_adapter(scene, tick_index)

        selector_scale_contract = None
        if arm == "camp":
            scales, selector_scale_contract = _load_frozen_selector_scales(
                Path(str(config["selector"]["atom_scales"]["path"]))
            )
            if config.get("schema_version") == "camp_dp_v25_controlled_train_v2":
                from camp_core.integrations.diffusion_planner_causal_atoms import (
                    validate_v25_atom_scales,
                )

                scales = validate_v25_atom_scales(scales)
            weights = _load_frozen_selector_weights(
                Path(str(config["selector"]["weights"]["path"]))
            )
            replacement = NativeCampPredictBatch(
                state=state,
                to_model_tensors=context["tensor_converter"].to_model_tensors,
                dump_step_npz=context["tensor_converter"].dump_step_npz,
                materialize=context["materialize"],
                select_candidate=context["select"],
                signal_mask=lambda candidates, causal, _scene: context[
                    "signal_mask"
                ](candidates, causal["route_lanes"]),
                planned_red_cost=lambda candidates, causal, scene: context[
                    "red_cost"
                ](candidates, causal, Path(str(config["fixed_dp"]["repo"])), scene.dt),
                atom_scales=scales,
                weights=weights,
                candidate_seed_root=int(config["seeds"]["candidate"]),
                route_sha256=str(route["sha256"]),
                pre_safety=pre_safety,
                selection_policy=_selection_policy(config),
                decision_sink=decision_sink,
                decision_sample_every_ticks=int(
                    protocol.get("sample_every_ticks", 5)
                ),
                scene_adapter=runtime_scene_adapter,
                scene_adapter_model_input_sync=(
                    scene_adapter.sync_model_input_map_cache
                    if scene_adapter is not None
                    and hasattr(scene_adapter, "sync_model_input_map_cache")
                    else None
                ),
                v25_context_sink=v25_context_sink,
                v25_v2i_signal_timing=None,
                causal_signal_atom_input_provider=(
                    scene_adapter.causal_signal_atom_input
                    if scene_adapter is not None
                    and hasattr(scene_adapter, "causal_signal_atom_input")
                    else None
                ),
                causal_input_sink=causal_input_sink,
            )
        elif config.get("schema_version") == "camp_dp_v24_native_evaluation_run_v1":
            replacement = NativeCampPredictBatch(
                state=state,
                to_model_tensors=context["tensor_converter"].to_model_tensors,
                dump_step_npz=context["tensor_converter"].dump_step_npz,
                materialize=None,
                select_candidate=None,
                signal_mask=None,
                planned_red_cost=None,
                atom_scales=None,
                weights=None,
                candidate_seed_root=int(config["seeds"]["candidate"]),
                route_sha256=str(route["sha256"]),
                pre_safety=pre_safety,
                operational_mode="dp_candidate0",
                scene_adapter=runtime_scene_adapter,
                scene_adapter_model_input_sync=(
                    scene_adapter.sync_model_input_map_cache
                    if scene_adapter is not None
                    and hasattr(scene_adapter, "sync_model_input_map_cache")
                    else None
                ),
                v25_context_sink=v25_context_sink,
                v25_v2i_signal_timing=None,
            )
        else:
            replacement = NativeDpObserveBatch(
                original_predict_batch=replay._predict_batch,
                state=state,
                dump_step_npz=context["tensor_converter"].dump_step_npz,
                pre_safety=pre_safety,
                scene_adapter=runtime_scene_adapter,
                scene_adapter_model_input_sync=(
                    scene_adapter.sync_model_input_map_cache
                    if scene_adapter is not None
                    and hasattr(scene_adapter, "sync_model_input_map_cache")
                    else None
                ),
            )

        output_dir = Path(output_dir)
        stdout = io.StringIO()
        stderr = io.StringIO()
        prior_no_png = os.environ.get("REPLAY_NO_PNG")
        os.environ["REPLAY_NO_PNG"] = "1"
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                with patched_native_replay(
                    replay,
                    replacement,
                    state,
                    dp_repo=Path(str(config["fixed_dp"]["repo"])),
                    expected_source_hashes=config["fixed_dp"][
                        "native_source_sha256"
                    ],
                    after_tracker=after_tracker,
                ):
                    native_result = replay.run_route_replay(
                        model=context["model"],
                        model_args=context["model_args"],
                        builder=builder,
                        route=route_object,
                        output_dir=output_dir,
                        spawn_config=spawn_config,
                        device=device,
                    )
        finally:
            if prior_no_png is None:
                os.environ.pop("REPLAY_NO_PNG", None)
            else:
                os.environ["REPLAY_NO_PNG"] = prior_no_png
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "native.stdout.txt").write_text(
                stdout.getvalue(), encoding="utf-8"
            )
            (output_dir / "native.stderr.txt").write_text(
                stderr.getvalue(), encoding="utf-8"
            )
        receipt = _build_native_arm_receipt(
            route=route,
            arm=arm,
            config=config,
            max_steps=max_steps,
            state=state,
            native_result=native_result,
            builder=builder,
            route_ids=route_ids,
            selector_scale_contract=selector_scale_contract,
        )
        receipt["runtime_annotation_compatibility"] = context[
            "annotation_compatibility"
        ]
        return receipt

    return run_arm


def _capture_pre_safety(
    receipt: dict[str, Any],
    scene: Any,
    builder: Any,
    route_ids: list[int],
    replay: Any,
) -> None:
    ego = scene.ego_agent
    corners = replay._ego_obb_corners(
        float(ego.current_position[0]),
        float(ego.current_position[1]),
        float(ego.current_heading),
        float(ego.length),
        float(ego.width),
        wheelbase=float(ego.wheelbase),
    )
    forward_ids = builder.select_route_segment_indices(
        route_ids, ego.current_position, max_segments=25
    ) or route_ids[:25]
    red_ids = [
        lanelet_id
        for index, lanelet_id in enumerate(forward_ids)
        if index < ego.route_lanes.shape[0]
        and bool(np.any(ego.route_lanes[index, :, 10] > 0.5))
    ]
    stop_lines = _matching_red_stop_lines(scene, builder, red_ids)
    receipt["_safety_pre"] = {
        "pre_decision_speed_mps": float(
            np.linalg.norm(np.asarray(ego.current_velocity, dtype=np.float64))
        ),
        "front_center_prev_xy": corners[[1, 2]].mean(axis=0).tolist(),
        "red_light_at_interval_start": bool(red_ids),
        "red_stop_lines": stop_lines.tolist(),
        "red_source_complete": not red_ids or bool(stop_lines.size),
    }


def _capture_post_safety(
    receipt: dict[str, Any],
    scene: Any,
    builder: Any,
    route_ids: list[int],
    replay: Any,
) -> None:
    pre = _mapping(receipt, "_safety_pre")
    ego = scene.ego_agent
    position = np.asarray(ego.current_position, dtype=np.float64)
    heading = float(ego.current_heading)
    velocity = np.asarray(ego.current_velocity, dtype=np.float64)
    corners = replay._ego_obb_corners(
        float(position[0]),
        float(position[1]),
        heading,
        float(ego.length),
        float(ego.width),
        wheelbase=float(ego.wheelbase),
    )
    projection = _route_projection(builder, route_ids, position)
    coverage = _five_point_lanelet_coverage(builder, position, corners)
    nearest = []
    for finder in (replay._ego_nearest_static_npc, replay._ego_nearest_moving_npc):
        value = finder(scene, threshold_m=1_000_000.0)
        if value is not None:
            nearest.append(value)
    clearance = min((float(value[2]) for value in nearest), default=1_000_000.0)
    ttc_values = []
    ego_radius = 0.5 * float(np.hypot(ego.length, ego.width))
    for other in scene.agents:
        if other.id == scene.ego_agent_id:
            continue
        diagnostic = diagnostic_constant_velocity_circle_ttc_s(
            ego_position_xy=position,
            ego_velocity_xy=velocity,
            ego_radius_m=ego_radius,
            other_position_xy=other.current_position,
            other_velocity_xy=other.current_velocity,
            other_radius_m=0.5 * float(np.hypot(other.length, other.width)),
        )
        if diagnostic["ttc_s"] is not None:
            ttc_values.append(float(diagnostic["ttc_s"]))
    speed_limit = projection["speed_limit_mps"]
    source_complete = bool(
        pre["red_source_complete"]
        and coverage["source_complete"]
        and speed_limit is not None
    )
    receipt["_safety_record"] = {
        "tick_index": int(receipt["tick_index"]),
        "position_xy": position.tolist(),
        "speed_mps": float(np.linalg.norm(velocity)),
        "ego_heading_rad": heading,
        "route_heading_rad": projection["heading_rad"],
        "route_progress_m": projection["progress_m"],
        "five_point_drivable_coverage": coverage["covered"],
        "min_obb_clearance_m": clearance,
        "red_light_at_interval_start": bool(pre["red_light_at_interval_start"]),
        "front_center_prev_xy": list(pre["front_center_prev_xy"]),
        "front_center_xy": corners[[1, 2]].mean(axis=0).tolist(),
        "red_stop_lines": list(pre["red_stop_lines"]),
        "speed_limit_mps": speed_limit,
        "constant_velocity_circle_ttc_diagnostic_s": (
            min(ttc_values) if ttc_values else None
        ),
        "source_complete": source_complete,
    }


def _matching_red_stop_lines(
    scene: Any, builder: Any, red_lanelet_ids: list[int]
) -> np.ndarray:
    if not red_lanelet_ids:
        return np.empty((0, 2, 2), dtype=np.float64)
    line_strings = np.asarray(scene.map_data.line_strings, dtype=np.float64)
    if line_strings.ndim != 3 or line_strings.shape[2] < 3:
        raise ValueError("native line_strings tensor shape changed")
    candidates = line_strings[np.any(line_strings[:, :, 2] > 0.5, axis=1)]
    result = []
    for line in candidates:
        points = line[:, :2]
        distance = min(
            float(
                np.linalg.norm(
                    points[:, None, :] - builder._cache[lanelet_id].raw_centerline,
                    axis=2,
                ).min()
            )
            for lanelet_id in red_lanelet_ids
            if lanelet_id in builder._cache
        )
        if distance <= 10.0:
            result.append(np.stack((points[0], points[-1])))
    return (
        np.stack(result).astype(np.float64)
        if result
        else np.empty((0, 2, 2), dtype=np.float64)
    )


def _route_projection(
    builder: Any, route_ids: list[int], position_xy: np.ndarray
) -> dict[str, Any]:
    offset = 0.0
    best: dict[str, Any] | None = None
    for lanelet_id in route_ids:
        cached = builder._cache[lanelet_id]
        points = np.asarray(cached.raw_centerline, dtype=np.float64)
        for index, (start, end) in enumerate(zip(points[:-1], points[1:])):
            vector = end - start
            length_sq = float(vector @ vector)
            fraction = (
                0.0
                if length_sq <= 1e-15
                else float(np.clip(((position_xy - start) @ vector) / length_sq, 0, 1))
            )
            projected = start + fraction * vector
            distance = float(np.linalg.norm(position_xy - projected))
            if best is None or distance < best["distance_m"]:
                segment_length = float(np.sqrt(length_sq))
                best = {
                    "distance_m": distance,
                    "heading_rad": float(np.arctan2(vector[1], vector[0])),
                    "progress_m": offset
                    + float(cached.cum_arc_lengths[index])
                    + fraction * segment_length,
                    "speed_limit_mps": (
                        float(cached.speed_limit_mps)
                        if cached.has_speed_limit and cached.speed_limit_mps > 0.0
                        else None
                    ),
                }
        offset += float(cached.arc_length)
    if best is None:
        raise ValueError("route projection source is empty")
    return best


def _five_point_lanelet_coverage(
    builder: Any, center: np.ndarray, corners: np.ndarray
) -> dict[str, Any]:
    points = np.concatenate((center.reshape(1, 2), corners), axis=0)
    candidate_ids = builder.lanelets_near_point(center, radius=15.0)
    if not candidate_ids:
        return {"covered": False, "source_complete": True}
    covered = all(
        any(_point_in_lanelet(point, builder._cache[lanelet_id]) for lanelet_id in candidate_ids)
        for point in points
    )
    return {"covered": bool(covered), "source_complete": True}


def _point_in_lanelet(point: np.ndarray, cached: Any) -> bool:
    polygon = np.concatenate((cached.raw_left, cached.raw_right[::-1]), axis=0)
    x, y = map(float, point)
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = map(float, previous)
        x2, y2 = map(float, current)
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) <= 1e-9 and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 and min(
            y1, y2
        ) - 1e-9 <= y <= max(y1, y2) + 1e-9:
            return True
        if (y1 > y) != (y2 > y):
            intersection_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < intersection_x:
                inside = not inside
        previous = current
    return inside


def _build_native_arm_receipt(
    *,
    route: Mapping[str, Any],
    arm: str,
    config: Mapping[str, Any],
    max_steps: int,
    state: NativeHookState,
    native_result: Mapping[str, Any],
    builder: Any,
    route_ids: list[int],
    selector_scale_contract: Mapping[str, Any] | None,
) -> dict[str, Any]:
    executed = [receipt for receipt in state.receipts if "_safety_record" in receipt]
    if not executed:
        raise ValueError("native replay produced no executed tracker tick")
    ticks = [_public_tick_receipt(receipt, arm) for receipt in executed]
    first_input = ticks[0]["input_sha256"]
    initial_state_sha = hashlib.sha256(
        ("v21_native_scene_context_v1\0" + first_input).encode("ascii")
    ).hexdigest()
    records = [dict(receipt["_safety_record"]) for receipt in executed]
    route_length = sum(float(builder._cache[value].arc_length) for value in route_ids)
    result: dict[str, Any] = {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "route_name": str(route["name"]),
        "route_sha256": str(route["sha256"]),
        "logical_map_sha256": str(config["map"]["sha256"]),
        "fixed_dp_head": str(config["fixed_dp"]["head"]),
        "checkpoint_sha256": str(config["fixed_dp"]["checkpoint"]["sha256"]),
        "args_sha256": str(config["fixed_dp"]["args_json"]["sha256"]),
        "arm": arm,
        "scenario_seed": int(config["seeds"]["scenario"]),
        "spawn_config_sha256": canonical_spawn_config_sha256(config, max_steps),
        "initial_state_sha256": initial_state_sha,
        "initial_input_sha256": first_input,
        "ticks": ticks,
        "native_result": dict(native_result),
        "claim_authorized": False,
    }
    if max_steps > 1:
        if not all(bool(record["source_complete"]) for record in records):
            raise ValueError("native safety metric source is incomplete")
        result["safety"] = _summarize_safety_records(
            records, str(config["protocol"]["safety_schema"])
        )
        result["secondary"] = summarize_route_comfort_native(
            records,
            dt=0.1,
            route_progress_m=float(records[-1]["route_progress_m"]),
            route_length_m=route_length,
            termination_reason=str(native_result["reason"]),
        )
        result["latency"] = _summarize_latency(ticks)
    if selector_scale_contract is not None:
        result["selector_scale_contract"] = dict(selector_scale_contract)
    return result


def _summarize_safety_records(
    records: list[Mapping[str, Any]], safety_schema: str
) -> dict[str, Any]:
    if safety_schema == "safety_cost_native_v1":
        return summarize_safety_cost_native_v1(records)
    if safety_schema == "safety_cost_native_v22":
        return summarize_safety_cost_native_v22(records)
    raise ValueError("unknown native safety schema")


def _public_tick_receipt(receipt: Mapping[str, Any], arm: str) -> dict[str, Any]:
    causal = _mapping(receipt, "causal_input")
    safety = _mapping(receipt, "_safety_record")
    tick: dict[str, Any] = {
        "tick_index": int(receipt["tick_index"]),
        "status": str(receipt["status"]),
        "input_sha256": str(causal["input_sha256"]),
        "padding": {
            "observed_frames": int(causal["observed_frames"]),
            "padded_frames": int(causal["padded_frames"]),
            "padding_policy": str(causal["padding_policy"]),
        },
        "tracker": dict(_mapping(receipt, "tracker")),
        "safety": dict(safety),
        "latency_ms": {
            key: float(value)
            for key, value in _mapping(receipt, "latency_ms").items()
        },
        "pre_decision_speed_mps": float(
            _mapping(receipt, "_safety_pre")["pre_decision_speed_mps"]
        ),
        "default_output_sha256": str(receipt["default_output_sha256"]),
    }
    if "candidate_tensor_sha256_before" in receipt:
        for name in (
            "candidate_tensor_sha256_before",
            "candidate_tensor_sha256_after",
            "candidate_neighbor_sha256",
            "selected_trajectory_sha256",
            "global_rng_sha256_before",
            "global_rng_sha256_after",
            "causal_evidence_sha256",
            "route_lanes_sha256",
            "route_lanes_speed_limit_sha256",
            "route_lanes_has_speed_limit_sha256",
        ):
            tick[name] = str(receipt[name])
        tick["candidate_row_sha256"] = list(receipt["candidate_row_sha256"])
        tick.update(
            {
                "selection_policy": str(receipt["selection_policy"]),
                "score_contract": str(receipt["score_contract"]),
                "tie_break_contract": str(receipt["tie_break_contract"]),
                "eligibility_mask_name": str(receipt["eligibility_mask_name"]),
                "selected_index": int(receipt["selected_index"]),
                "default_candidate0_identity": dict(
                    _mapping(receipt, "default_candidate0_identity")
                ),
            }
        )
        for name in (
            "atom_matrix_sha256",
            "normalized_atom_matrix_sha256",
            "candidate0_operational_default",
            "post_divergence_cross_arm_tensor_identity_required",
            "npc_operational_outputs_unchanged",
        ):
            if name in receipt:
                tick[name] = receipt[name]
        for name in (
            "scores",
            "physical_feasible_mask",
            "source_valid_mask",
            "source_complete_mask",
        ):
            if name in receipt:
                tick[name] = list(receipt[name])
        if "candidate_reasons" in receipt:
            tick["candidate_reasons"] = [
                list(value) for value in receipt["candidate_reasons"]
            ]
        if "all_k_high_risk" in receipt:
            tick["all_k_high_risk"] = bool(receipt["all_k_high_risk"])
        if "controlled_scene" in receipt:
            tick["controlled_scene"] = json.loads(
                json.dumps(receipt["controlled_scene"], allow_nan=False)
            )
        if "v25_context" in receipt:
            tick["v25_context"] = json.loads(
                json.dumps(receipt["v25_context"], allow_nan=False)
            )
    return tick


def _summarize_latency(ticks: list[Mapping[str, Any]]) -> dict[str, Any]:
    names = sorted({name for tick in ticks for name in tick["latency_ms"]})
    result = {}
    for name in names:
        values = np.asarray(
            [tick["latency_ms"][name] for tick in ticks if name in tick["latency_ms"]],
            dtype=np.float64,
        )
        result[name] = {
            "count": int(values.size),
            "mean": float(values.mean()),
            "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95.0)),
            "p99": float(np.percentile(values, 99.0)),
            "max": float(values.max()),
        }
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auditable CAMP/DP v21 native scenario_generation smoke runner."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--preflight", dest="mode", action="store_const", const="preflight"
    )
    modes.add_argument(
        "--capability-smoke",
        dest="mode",
        action="store_const",
        const="capability-smoke",
    )
    modes.add_argument(
        "--tiny-capability-smoke",
        dest="mode",
        action="store_const",
        const="tiny-capability-smoke",
    )
    modes.add_argument(
        "--paired-smoke",
        dest="mode",
        action="store_const",
        const="paired-smoke",
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    verified_assets = verify_config_assets(config)
    run_arm = None
    if args.mode != "preflight":
        run_arm = build_native_arm_runner(config, device=args.device)
    return execute_smoke(
        config,
        args.output_dir,
        mode=args.mode,
        run_arm=run_arm,
        verified_assets=verified_assets,
        command=(
            f"{sys.executable} {Path(__file__).resolve()} --{args.mode} "
            f"--config {args.config.resolve()} --output-dir {args.output_dir.resolve()} "
            f"--device {args.device}"
        ),
    )


if __name__ == "__main__":
    main()
