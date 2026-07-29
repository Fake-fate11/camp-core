"""Explicit V26 integration identities at the fixed-DP boundary.

This module deliberately separates the V26 same-ego B8 acquisition path from
the historical V25 industrial/fair entry points.  It contains no evaluation
endpoint implementation: Stage 8b writes training evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sys
from typing import Any, Mapping, Sequence

from .diffusion_planner_camp_signal_contract import (
    CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
    canonical_json_sha256,
    validate_causal_signal_atom_input,
)
from .diffusion_planner_v26_autoware_sidecar_signal import (
    V26AutowareSidecarSignalAdapter,
    load_autoware_sidecar_binding,
)
from .diffusion_planner_v26_source_authority import (
    V26_SOURCE_TRAFFIC_SIGNAL_ADAPTER_ID,
    V26_SOURCE_TRAFFIC_SIGNAL_MODE,
    V26SourceMapTrafficSignalAdapter,
)


FROZEN_SIMPLEX_TOLERANCE = 1e-9

V26_NATIVE_RUNNER_ID = "camp_dp_v26_native_same_ego_b8_acquisition_runner_v1"
V26_NATIVE_CALLBACK_ID = "camp_dp_v26_native_same_ego_b8_callback_v1"
V26_FIXED_DP_REPLAY_BRIDGE_ID = "fixed_dp_replay_bridge_v21_api_only_v1"
V26_GENERATOR_ID = "fixed_dp_same_ego_single_invocation_b8_v1"
V26_TRAINING_SOURCE_SCHEMA_VERSION = (
    "camp_dp_v26_same_ego_single_invocation_b8_training_source_v1"
)
V26_TRAINING_ROWS_SCHEMA_VERSION = "camp_dp_v26_same_ego_b8_training_rows_v1"
V25_ZERO_SHOT_REFERENCE_READ_ONLY = "v25_zero_shot_reference_read_only"
V26_ADAPTED_WEIGHTS_SCHEMA_VERSION = "camp_dp_v26_adapted_selector_weights_v1"
V26_TRAINING_EVIDENCE_EVALUATION_SCHEMA = (
    "camp_dp_v26_training_evidence_only_no_formal_evaluation_v1"
)
V26_DEVELOPMENT_COMPARISON_EVALUATION_SCHEMA = (
    "camp_dp_v26_development_nonholdout_industrial_v3_comparison_v1"
)
V26_FUTURE_EFFECT_SCHEMA = "camp_dp_v26_industrial_v3_vector_or_typed_missing_v1"
V26_LEGACY_SAFETYCOST_ROLE = "legacy_only_not_v26_formal_endpoint"
V26_AUTOWARE_SIDECAR_SIGNAL_MODE = "autoware_traffic_light_sidecar"
V26_CERTIFIED_NO_SIGNAL_MODE = "certified_no_signal"
V26_AUTOWARE_SIDECAR_ADAPTER_ID = "camp_dp_v26_autoware_sidecar_signal_adapter_v1"
V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID = "camp_dp_v26_certified_no_signal_absence_adapter_v1"
V26_CERTIFIED_NO_SIGNAL_SCHEMA_VERSION = "camp_dp_v26_certified_no_signal_authority_v1"
V26_INTEGRATION_BOUNDARY_SCHEMA_VERSION = "camp_dp_v26_integration_boundary_v1"
V26_ADAPTED_INTEGRATION_BOUNDARY_SCHEMA_VERSION = (
    "camp_dp_v26_adapted_comparison_integration_boundary_v1"
)
V26_ADAPTED_SELECTOR_RUNTIME_ID = "camp_dp_v26_adapted_selector_runtime_v1"
V26_AUTODL_LAUNCHER_SCHEMA_VERSION = "camp_dp_v26_autodl_launcher_v1"
V26_AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"
V26_DP312_SITE_PACKAGES = "/root/autodl-tmp/dp312_venv/lib/python3.12/site-packages"
V26_DP312_LANELET2_PRECEDENCE = "dp312_site_packages_before_system_lanelet2_v1"

_SHA_CHARS = frozenset("0123456789abcdef")
_FORBIDDEN_HIGH_LEVEL_CONSUMER_TOKENS = (
    "v25_industrial_bounded_closed_loop",
    "v25_fair_nonholdout",
    "summarize_run_v2",
    "safetycost",
)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - _SHA_CHARS:
        raise ValueError(f"{label} must be a lowercase SHA256")
    return value


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(dict(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _int_list(value: Any, label: str, *, nonempty: bool) -> list[int]:
    if (
        type(value) is not list
        or (nonempty and not value)
        or any(type(item) is not int for item in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(f"{label} must be a unique integer list")
    return list(value)


def _require_exact_mapping(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f"{label} field set drifted")
    return dict(value)


def validate_v26_source_map_signal_binding(
    value: Mapping[str, Any],
    *,
    route_sha256: str | None = None,
    map_sha256: str | None = None,
    route_geometry_sha256: str | None = None,
    source_projection_sha256: str | None = None,
    source_inventory_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate the native source-map traffic adapter without sidecar fallback.

    The adapter's own constructor is the authority validator for the frozen
    source-map payload.  Callers with a prepared route may additionally bind
    every source-derived hash to that route's qualification receipt.
    """

    binding = _require_exact_mapping(
        value,
        {
            "schema_version",
            "signal_authority_mode",
            "signal_adapter_id",
            "source_authority",
        },
        "V26 source-map signal binding",
    )
    if (
        binding["schema_version"]
        != "camp_dp_v26_source_map_signal_adapter_binding_v1"
        or binding["signal_authority_mode"] != V26_SOURCE_TRAFFIC_SIGNAL_MODE
        or binding["signal_adapter_id"] != V26_SOURCE_TRAFFIC_SIGNAL_ADAPTER_ID
        or type(binding["source_authority"]) is not dict
    ):
        raise ValueError("V26 source-map signal binding identity drifted")
    adapter = V26SourceMapTrafficSignalAdapter(binding["source_authority"])
    expected = adapter.receipt()
    if binding != expected:
        raise ValueError("V26 source-map signal binding receipt drifted")
    authority = adapter.source_authority
    expected_hashes = {
        "route_sha256": route_sha256,
        "map_sha256": map_sha256,
        "route_geometry_sha256": route_geometry_sha256,
        "source_projection_sha256": source_projection_sha256,
        "source_inventory_sha256": source_inventory_sha256,
    }
    for key, expected_hash in expected_hashes.items():
        if expected_hash is not None and authority[key] != _sha256(
            expected_hash, f"V26 expected source-map {key}"
        ):
            raise ValueError(f"V26 source-map signal {key} drifted from prepared authority")
    return expected


def v26_generator_topology() -> dict[str, Any]:
    """The only generator topology accepted by the V26 acquisition boundary."""

    return {
        "same_ego_batch_size": 8,
        "primary_model_call_count": 1,
        "sequential_forward_count": 0,
        "candidate0_row": 0,
        "unique_latent_rows_required": True,
        "unique_candidate_rows_required": True,
        "post_pool_model_dp_latent_generation_calls": 0,
        "candidate_pool_mutation_count": 0,
        "trajectory_regeneration_count": 0,
    }


@dataclass
class V26NativeHookState:
    """V26-owned replay state consumed by the fixed-DP replay bridge only."""

    receipts: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class V26SignalAdapterBinding:
    mode: str
    adapter_id: str
    adapter: Any
    receipt: dict[str, Any]


class V26CertifiedNoSignalAbsenceAdapter:
    """Explicit certified absence source; it never creates a fake signal runtime."""

    def __init__(self, authority: Mapping[str, Any]) -> None:
        row = _require_exact_mapping(
            authority,
            {
                "schema_version",
                "route_sha256",
                "map_sha256",
                "route_lanelet_ids",
                "route_geometry_sha256",
                "source_chain_sha256",
                "certification_sha256",
                "traffic_light_regulatory_element_ids",
            },
            "V26 certified no-signal authority",
        )
        if row["schema_version"] != V26_CERTIFIED_NO_SIGNAL_SCHEMA_VERSION:
            raise ValueError("V26 certified no-signal authority schema drifted")
        for key in (
            "route_sha256",
            "map_sha256",
            "route_geometry_sha256",
            "source_chain_sha256",
            "certification_sha256",
        ):
            row[key] = _sha256(row[key], f"V26 no-signal {key}")
        row["route_lanelet_ids"] = _int_list(
            row["route_lanelet_ids"], "V26 no-signal route lanelets", nonempty=True
        )
        if row["traffic_light_regulatory_element_ids"] != []:
            raise ValueError("V26 certified no-signal authority cannot retain traffic lights")
        self.authority = row
        self._builder: Any | None = None
        self._runtime_route_ids: tuple[int, ...] = ()

    def bind_builder(self, builder: Any) -> None:
        if self._builder is not None and self._builder is not builder:
            raise ValueError("V26 no-signal builder binding drifted")
        self._builder = builder

    def bind_runtime_lanelet_ids(
        self, *, route_lanelet_ids: Sequence[int], map_lanelet_ids: Sequence[int]
    ) -> None:
        if self._builder is None:
            raise ValueError("V26 no-signal adapter is not bound to a builder")
        route = tuple(int(item) for item in route_lanelet_ids)
        mapped = tuple(int(item) for item in map_lanelet_ids)
        declared = set(self.authority["route_lanelet_ids"])
        if not route or not mapped or not set(route).issubset(declared):
            raise ValueError("V26 no-signal runtime route escaped certified authority")
        live_traffic_lights = {
            int(element.id)
            for lanelet_id in route
            for element in self._builder._ll_by_id[int(lanelet_id)].trafficLights()
        }
        if live_traffic_lights:
            raise ValueError(
                "V26 certified no-signal authority conflicts with the live route graph"
            )
        self._runtime_route_ids = route

    def __call__(self, scene: Any, tick_index: int) -> Mapping[str, Any]:
        self._runtime_receipt(scene, tick_index)
        return {
            "schema_version": "camp_dp_v26_certified_no_signal_controlled_scene_v1",
            "signal_authority_mode": V26_CERTIFIED_NO_SIGNAL_MODE,
            "signal_adapter_id": V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID,
            "absence_authority": dict(self.authority),
            "outcome_fields_consumed": [],
            "candidate_tensor_consumed": False,
            "selected_trajectory_consumed": False,
        }

    def sync_model_input_map_cache(
        self, scene: Any, map_cache: Any, tick_index: int
    ) -> Mapping[str, Any]:
        self._runtime_receipt(scene, tick_index)
        if map_cache is None:
            raise ValueError("V26 no-signal adapter requires the fixed-DP map cache")
        return {
            "schema_version": "camp_dp_v26_certified_no_signal_model_cache_v1",
            "status": "not_applicable_certified_no_signal",
            "mutated": False,
            "future_schedule_consumed": False,
        }

    def causal_signal_atom_input(self, scene: Any, tick_index: int) -> Mapping[str, Any]:
        runtime = self._runtime_receipt(scene, tick_index)
        payload = {
            "schema_version": CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
            "source_state": "not_applicable",
            "source_valid": True,
            "applicable": False,
            "current_phase": "none",
            "decision_time_s": runtime["decision_time_s"],
            "ego_position_world_m": None,
            "ego_heading_rad": None,
            "regulatory_element_id": None,
            "stop_line_id": None,
            "stop_line_geometry_world_m": None,
            "stop_line_geometry_ego_m": None,
            "stop_line_geometry_sha256": None,
            "route_tangent_world": None,
            "route_tangent_ego": None,
            "route_geometry_sha256": self.authority["route_geometry_sha256"],
            "route_arc_m": None,
            "source_chain_sha256": self.authority["source_chain_sha256"],
            "runtime_receipt": runtime,
            # The fixed causal-atom schema defines this hash with its canonical
            # newline-terminated encoding.  Keep the V26 adapter schema
            # distinct, but bind this one field to the frozen causal contract.
            "runtime_receipt_sha256": canonical_json_sha256(runtime),
        }
        return validate_causal_signal_atom_input(payload)

    def receipt(self) -> dict[str, Any]:
        return {
            "schema_version": "camp_dp_v26_certified_no_signal_adapter_receipt_v1",
            "signal_authority_mode": V26_CERTIFIED_NO_SIGNAL_MODE,
            "signal_adapter_id": V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID,
            "authority": dict(self.authority),
        }

    def _runtime_receipt(self, scene: Any, tick_index: int) -> dict[str, Any]:
        if type(tick_index) is not int or tick_index < 0 or not self._runtime_route_ids:
            raise ValueError("V26 no-signal runtime binding is incomplete")
        decision_time_s = float(tick_index) * float(scene.dt)
        if not math.isfinite(decision_time_s) or decision_time_s < 0.0:
            raise ValueError("V26 no-signal decision time is invalid")
        return {
            "schema_version": "camp_dp_v26_certified_no_signal_runtime_v1",
            "source_mode": "same_tick_no_signal_rule_no_v2i",
            "current_phase": "none",
            "decision_time_s": decision_time_s,
            "route_geometry_sha256": self.authority["route_geometry_sha256"],
            "route_lanelet_ids": list(self._runtime_route_ids),
            "traffic_light_regulatory_element_ids": [],
            "source_chain_sha256": self.authority["source_chain_sha256"],
            "certification_sha256": self.authority["certification_sha256"],
            "phase_remaining_available": False,
            "source_valid": True,
            "applicable": False,
            "future_schedule_consumed": False,
        }


def resolve_v26_signal_adapter(probe_config: Mapping[str, Any]) -> V26SignalAdapterBinding:
    """Fail closed on a missing mode, an unknown mode, or an incomplete adapter."""

    config = dict(probe_config)
    mode = config.get("signal_authority_mode")
    if type(mode) is not str:
        raise ValueError("V26 signal_authority_mode is required; no fallback is permitted")
    if mode == V26_AUTOWARE_SIDECAR_SIGNAL_MODE:
        binding, sidecar_manifest = load_autoware_sidecar_binding(config)
        adapter = V26AutowareSidecarSignalAdapter(
            binding=binding, sidecar_manifest=sidecar_manifest
        )
        return V26SignalAdapterBinding(
            mode=mode,
            adapter_id=V26_AUTOWARE_SIDECAR_ADAPTER_ID,
            adapter=adapter,
            receipt={
                "schema_version": "camp_dp_v26_autoware_sidecar_adapter_binding_v1",
                "signal_authority_mode": mode,
                "signal_adapter_id": V26_AUTOWARE_SIDECAR_ADAPTER_ID,
                "binding": binding,
            },
        )
    if mode == V26_CERTIFIED_NO_SIGNAL_MODE:
        authority = config.get("certified_no_signal_authority")
        if type(authority) is not dict:
            raise ValueError("V26 certified no-signal authority is required; no fallback is permitted")
        adapter = V26CertifiedNoSignalAbsenceAdapter(authority)
        routes = config.get("routes")
        map_binding = config.get("map")
        if (
            type(routes) is not list
            or len(routes) != 1
            or type(routes[0]) is not dict
            or type(map_binding) is not dict
            or adapter.authority["route_sha256"] != routes[0].get("sha256")
            or adapter.authority["map_sha256"] != map_binding.get("sha256")
        ):
            raise ValueError("V26 certified no-signal authority does not bind map/route")
        return V26SignalAdapterBinding(
            mode=mode,
            adapter_id=V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID,
            adapter=adapter,
            receipt=adapter.receipt(),
        )
    if mode == V26_SOURCE_TRAFFIC_SIGNAL_MODE:
        authority = config.get("source_map_traffic_authority")
        if type(authority) is not dict:
            raise ValueError("V26 source-map traffic authority is required; no fallback is permitted")
        adapter = V26SourceMapTrafficSignalAdapter(authority)
        routes = config.get("routes")
        map_binding = config.get("map")
        if (
            type(routes) is not list
            or len(routes) != 1
            or type(routes[0]) is not dict
            or type(map_binding) is not dict
            or adapter.source_authority["route_sha256"] != routes[0].get("sha256")
            or adapter.source_authority["map_sha256"] != map_binding.get("sha256")
        ):
            raise ValueError("V26 source-map traffic authority does not bind map/route")
        return V26SignalAdapterBinding(
            mode=mode,
            adapter_id=V26_SOURCE_TRAFFIC_SIGNAL_ADAPTER_ID,
            adapter=adapter,
            receipt=validate_v26_source_map_signal_binding(adapter.receipt()),
        )
    raise ValueError("V26 signal_authority_mode has no certified adapter")


def build_v26_integration_boundary(
    *, signal: V26SignalAdapterBinding, reference_weights_root_sha256: str
) -> dict[str, Any]:
    """Build receipt metadata used by V26 acquisition/profiling reviewers."""

    return validate_v26_integration_boundary(
        {
            "schema_version": V26_INTEGRATION_BOUNDARY_SCHEMA_VERSION,
            "runner_id": V26_NATIVE_RUNNER_ID,
            "callback_id": V26_NATIVE_CALLBACK_ID,
            "replay_bridge_id": V26_FIXED_DP_REPLAY_BRIDGE_ID,
            "signal_authority_mode": signal.mode,
            "signal_adapter_id": signal.adapter_id,
            "signal_adapter_binding": signal.receipt,
            "generator_id": V26_GENERATOR_ID,
            "generator_topology": v26_generator_topology(),
            "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "evaluation_schema": V26_TRAINING_EVIDENCE_EVALUATION_SCHEMA,
            "future_effect_schema": V26_FUTURE_EFFECT_SCHEMA,
            "legacy_safetycost_role": V26_LEGACY_SAFETYCOST_ROLE,
            "weight_sources": {
                "reference": {
                    "role": V25_ZERO_SHOT_REFERENCE_READ_ONLY,
                    "data_eligible": False,
                    "root_sha256": reference_weights_root_sha256,
                },
                "adapted": {
                    "role": "not_present_for_this_run",
                    "data_eligible": False,
                    "schema_version": None,
                },
            },
            "consumer_ids": [
                V26_NATIVE_RUNNER_ID,
                V26_NATIVE_CALLBACK_ID,
                signal.adapter_id,
            ],
        }
    )


def build_v26_adapted_comparison_integration_boundary(
    *,
    signal: V26SignalAdapterBinding,
    reference_manifest_sha256: str,
    adaptation_receipt_sha256: str,
    adapted_asset_manifest_sha256: str,
) -> dict[str, Any]:
    """Bind a V26 adapted selector runtime without promoting V25 consumers.

    The zero-shot source remains a read-only compatibility reference.  The
    exact fitted CAMP adaptation receipt and its asset manifest are separately
    bound for the V26 development comparison runtime.
    """

    return validate_v26_integration_boundary(
        {
            "schema_version": V26_ADAPTED_INTEGRATION_BOUNDARY_SCHEMA_VERSION,
            "runner_id": V26_NATIVE_RUNNER_ID,
            "callback_id": V26_NATIVE_CALLBACK_ID,
            "replay_bridge_id": V26_FIXED_DP_REPLAY_BRIDGE_ID,
            "signal_authority_mode": signal.mode,
            "signal_adapter_id": signal.adapter_id,
            "signal_adapter_binding": signal.receipt,
            "generator_id": V26_GENERATOR_ID,
            "generator_topology": v26_generator_topology(),
            "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "evaluation_schema": V26_DEVELOPMENT_COMPARISON_EVALUATION_SCHEMA,
            "future_effect_schema": V26_FUTURE_EFFECT_SCHEMA,
            "legacy_safetycost_role": V26_LEGACY_SAFETYCOST_ROLE,
            "weight_sources": {
                "reference": {
                    "role": V25_ZERO_SHOT_REFERENCE_READ_ONLY,
                    "data_eligible": False,
                    "reference_manifest_sha256": reference_manifest_sha256,
                },
                "adapted": {
                    "role": V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
                    "data_eligible": False,
                    "schema_version": V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
                    "adaptation_receipt_sha256": adaptation_receipt_sha256,
                    "asset_manifest_sha256": adapted_asset_manifest_sha256,
                },
            },
            "consumer_ids": [
                V26_NATIVE_RUNNER_ID,
                V26_NATIVE_CALLBACK_ID,
                signal.adapter_id,
                V26_ADAPTED_SELECTOR_RUNTIME_ID,
            ],
        }
    )


def validate_v26_integration_boundary(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _require_exact_mapping(
        value,
        {
            "schema_version",
            "runner_id",
            "callback_id",
            "replay_bridge_id",
            "signal_authority_mode",
            "signal_adapter_id",
            "signal_adapter_binding",
            "generator_id",
            "generator_topology",
            "training_source_schema",
            "evaluation_schema",
            "future_effect_schema",
            "legacy_safetycost_role",
            "weight_sources",
            "consumer_ids",
        },
        "V26 integration boundary",
    )
    schema_version = result["schema_version"]
    if (
        schema_version
        not in {
            V26_INTEGRATION_BOUNDARY_SCHEMA_VERSION,
            V26_ADAPTED_INTEGRATION_BOUNDARY_SCHEMA_VERSION,
        }
        or result["runner_id"] != V26_NATIVE_RUNNER_ID
        or result["callback_id"] != V26_NATIVE_CALLBACK_ID
        or result["replay_bridge_id"] != V26_FIXED_DP_REPLAY_BRIDGE_ID
        or result["generator_id"] != V26_GENERATOR_ID
        or result["generator_topology"] != v26_generator_topology()
        or result["training_source_schema"] != V26_TRAINING_SOURCE_SCHEMA_VERSION
        or result["future_effect_schema"] != V26_FUTURE_EFFECT_SCHEMA
        or result["legacy_safetycost_role"] != V26_LEGACY_SAFETYCOST_ROLE
    ):
        raise ValueError("V26 integration boundary identity drifted")
    expected_evaluation = (
        V26_TRAINING_EVIDENCE_EVALUATION_SCHEMA
        if schema_version == V26_INTEGRATION_BOUNDARY_SCHEMA_VERSION
        else V26_DEVELOPMENT_COMPARISON_EVALUATION_SCHEMA
    )
    if result["evaluation_schema"] != expected_evaluation:
        raise ValueError("V26 integration boundary evaluation schema drifted")
    expected_adapter_ids = {
        V26_AUTOWARE_SIDECAR_SIGNAL_MODE: V26_AUTOWARE_SIDECAR_ADAPTER_ID,
        V26_CERTIFIED_NO_SIGNAL_MODE: V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID,
        V26_SOURCE_TRAFFIC_SIGNAL_MODE: V26_SOURCE_TRAFFIC_SIGNAL_ADAPTER_ID,
    }
    if (
        result["signal_authority_mode"] not in expected_adapter_ids
        or result["signal_adapter_id"]
        != expected_adapter_ids[result["signal_authority_mode"]]
    ):
        raise ValueError("V26 integration boundary signal adapter drifted")
    if type(result["signal_adapter_binding"]) is not dict:
        raise ValueError("V26 integration boundary signal binding is required")
    if result["signal_authority_mode"] == V26_SOURCE_TRAFFIC_SIGNAL_MODE:
        result["signal_adapter_binding"] = validate_v26_source_map_signal_binding(
            result["signal_adapter_binding"]
        )
    weights = _require_exact_mapping(
        result["weight_sources"], {"reference", "adapted"}, "V26 weight sources"
    )
    reference_fields = (
        {"role", "data_eligible", "root_sha256"}
        if schema_version == V26_INTEGRATION_BOUNDARY_SCHEMA_VERSION
        else {"role", "data_eligible", "reference_manifest_sha256"}
    )
    reference = _require_exact_mapping(
        weights["reference"], reference_fields, "V26 reference weights"
    )
    if reference["role"] != V25_ZERO_SHOT_REFERENCE_READ_ONLY or reference["data_eligible"] is not False:
        raise ValueError("V25 compatibility weights are reference-only, never V26 data")
    if schema_version == V26_INTEGRATION_BOUNDARY_SCHEMA_VERSION:
        reference["root_sha256"] = _sha256(reference["root_sha256"], "V26 reference root")
    else:
        reference["reference_manifest_sha256"] = _sha256(
            reference["reference_manifest_sha256"], "V26 reference manifest"
        )
    if schema_version == V26_INTEGRATION_BOUNDARY_SCHEMA_VERSION:
        adapted = _require_exact_mapping(
            weights["adapted"], {"role", "data_eligible", "schema_version"}, "V26 adapted weights"
        )
        if adapted != {
            "role": "not_present_for_this_run",
            "data_eligible": False,
            "schema_version": None,
        }:
            raise ValueError("V26 reference run cannot mislabel adapted weights")
    else:
        adapted = _require_exact_mapping(
            weights["adapted"],
            {
                "role",
                "data_eligible",
                "schema_version",
                "adaptation_receipt_sha256",
                "asset_manifest_sha256",
            },
            "V26 adapted comparison weights",
        )
        if (
            adapted["role"] != V26_ADAPTED_WEIGHTS_SCHEMA_VERSION
            or adapted["data_eligible"] is not False
            or adapted["schema_version"] != V26_ADAPTED_WEIGHTS_SCHEMA_VERSION
        ):
            raise ValueError("V26 adapted comparison weight role drifted")
        adapted["adaptation_receipt_sha256"] = _sha256(
            adapted["adaptation_receipt_sha256"], "V26 adaptation receipt"
        )
        adapted["asset_manifest_sha256"] = _sha256(
            adapted["asset_manifest_sha256"], "V26 adapted asset manifest"
        )
    result["weight_sources"] = {"reference": reference, "adapted": adapted}
    consumer_ids = result["consumer_ids"]
    if type(consumer_ids) is list and any(
        type(value) is str
        and any(token in value.lower() for token in _FORBIDDEN_HIGH_LEVEL_CONSUMER_TOKENS)
        for value in consumer_ids
    ):
        raise ValueError("V26 reviewer rejects V25 high-level consumer IDs")
    expected_consumers = [
        V26_NATIVE_RUNNER_ID,
        V26_NATIVE_CALLBACK_ID,
        result["signal_adapter_id"],
    ]
    if schema_version == V26_ADAPTED_INTEGRATION_BOUNDARY_SCHEMA_VERSION:
        expected_consumers.append(V26_ADAPTED_SELECTOR_RUNTIME_ID)
    if type(consumer_ids) is not list or consumer_ids != expected_consumers:
        raise ValueError("V26 integration boundary consumer IDs drifted")
    return result


def v26_autodl_launcher_config() -> dict[str, Any]:
    """Reproducible remote interpreter and lanelet2 precedence configuration."""

    return {
        "schema_version": V26_AUTODL_LAUNCHER_SCHEMA_VERSION,
        "interpreter": V26_AUTODL_INTERPRETER,
        "lanelet2_precedence": V26_DP312_LANELET2_PRECEDENCE,
        "dp312_site_packages": V26_DP312_SITE_PACKAGES,
        "inherit_pythonpath": False,
        "human_shim_required": False,
    }


def validate_v26_autodl_launcher_config(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _require_exact_mapping(
        value,
        {
            "schema_version",
            "interpreter",
            "lanelet2_precedence",
            "dp312_site_packages",
            "inherit_pythonpath",
            "human_shim_required",
        },
        "V26 AutoDL launcher config",
    )
    if result != v26_autodl_launcher_config():
        raise ValueError("V26 AutoDL launcher configuration drifted")
    return result


def load_v26_autodl_launcher_config(path: Path) -> dict[str, Any]:
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    value = json.loads(source.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("V26 AutoDL launcher config must be an object")
    return validate_v26_autodl_launcher_config(value)


def v26_autodl_launcher_environment(
    *, source_checkout: str, fixed_dp_repo: str
) -> dict[str, str]:
    """Return the only supported dp312 import order for V26 remote launchers."""

    source = PurePosixPath(source_checkout)
    dp_repo = PurePosixPath(fixed_dp_repo)
    if (
        not source.is_absolute()
        or not dp_repo.is_absolute()
        or ".." in source.parts
        or ".." in dp_repo.parts
    ):
        raise ValueError("V26 launcher paths must be absolute, normalized POSIX paths")
    paths = (
        V26_DP312_SITE_PACKAGES,
        str(source),
        str(source / "camp_core"),
        str(dp_repo),
    )
    return {
        "PYTHONPATH": ":".join(paths),
        "PYTHONNOUSERSITE": "1",
    }


def enforce_v26_dp312_lanelet2_precedence() -> str:
    """Pin the venv Lanelet2 module before importing V26 route-builder code."""

    site = V26_DP312_SITE_PACKAGES
    sys.path[:] = [path for path in sys.path if path != site]
    sys.path.insert(0, site)
    import lanelet2

    module_path = str(getattr(lanelet2, "__file__", ""))
    if not module_path.startswith(site + "/"):
        raise RuntimeError("V26 launcher loaded Lanelet2 outside the fixed dp312 venv")
    return module_path
