"""Receipt-bound, observed-current-signal adapter for V26 Autoware smoke runs.

The V26 smoke uses real map/route signal authority.  It deliberately does not
fall back to the historical V25 no-signal source chain.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner_v25_semantic_authority import (
    CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
    canonical_json_sha256,
    validate_causal_signal_atom_input,
)


SIDECAR_BINDING_SCHEMA_VERSION = "camp_dp_v26_autoware_sidecar_binding_v1"
SIDECAR_SIGNAL_CHAIN_SCHEMA_VERSION = "camp_dp_v26_autoware_sidecar_signal_chain_v1"
SIDECAR_SIGNAL_RECEIPT_SCHEMA_VERSION = "camp_dp_v26_autoware_sidecar_signal_receipt_v1"
SIDECAR_CONTROLLED_SCENE_SCHEMA_VERSION = "camp_dp_v26_autoware_sidecar_controlled_scene_v1"

_SHA_CHARS = frozenset("0123456789abcdef")
_PHASES = ("green", "yellow", "red")
_PHASE_CHANNELS = {"green": 8, "yellow": 9, "red": 10}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or set(value) - _SHA_CHARS:
        raise ValueError(f"{label} must be a SHA256")
    return value


def _require_int_list(value: Any, label: str, *, nonempty: bool) -> list[int]:
    if (
        type(value) is not list
        or (nonempty and not value)
        or any(type(item) is not int for item in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError(f"{label} must be a unique integer list")
    return list(value)


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_autoware_sidecar_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the immutable route/map/sidecar binding retained in V26 receipts."""

    result = dict(value)
    expected = {
        "schema_version",
        "route_sha256",
        "map_sha256",
        "geometry_copy_sha256",
        "sidecar_index_sha256",
        "sidecar_manifest_sha256",
        "sidecar_source_sha256",
    }
    if set(result) != expected:
        raise ValueError("V26 Autoware sidecar binding field set drifted")
    if result["schema_version"] != SIDECAR_BINDING_SCHEMA_VERSION:
        raise ValueError("V26 Autoware sidecar binding schema drifted")
    for key in expected - {"schema_version"}:
        result[key] = _require_sha256(result[key], f"sidecar binding {key}")
    if result["map_sha256"] != result["geometry_copy_sha256"]:
        raise ValueError("V26 sidecar geometry copy no longer matches bound map")
    return result


def validate_autoware_sidecar_signal_receipt(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the same-tick V26 signal receipt before it reaches atom code."""

    result = dict(value)
    expected = {
        "schema_version",
        "binding",
        "route_lanelet_ids",
        "controlled_lanelet_ids",
        "route_traffic_authority_ids",
        "authority_selection_rule",
        "regulatory_element_id",
        "physical_light_ids",
        "bulb_ids",
        "stop_line_id",
        "stop_line_geometry_sha256",
        "route_graph_sha256",
        "signal_chain_sha256",
        "runtime_receipt_sha256",
        "phase_authority_mode",
        "current_phase",
        "source_valid",
        "future_schedule_consumed",
        "candidate_tensor_consumed",
        "selected_trajectory_consumed",
    }
    if set(result) != expected:
        raise ValueError("V26 Autoware signal receipt field set drifted")
    if result["schema_version"] != SIDECAR_SIGNAL_RECEIPT_SCHEMA_VERSION:
        raise ValueError("V26 Autoware signal receipt schema drifted")
    result["binding"] = validate_autoware_sidecar_binding(result["binding"])
    result["route_lanelet_ids"] = _require_int_list(
        result["route_lanelet_ids"], "sidecar route lanelet IDs", nonempty=True
    )
    result["controlled_lanelet_ids"] = _require_int_list(
        result["controlled_lanelet_ids"], "sidecar controlled lanelet IDs", nonempty=True
    )
    if not set(result["controlled_lanelet_ids"]).issubset(result["route_lanelet_ids"]):
        raise ValueError("V26 sidecar controlled lanelet escaped the route graph")
    result["route_traffic_authority_ids"] = _require_int_list(
        result["route_traffic_authority_ids"], "sidecar route traffic authority IDs", nonempty=True
    )
    if (
        result["authority_selection_rule"]
        != "first_controlled_lanelet_in_frozen_route_order"
    ):
        raise ValueError("V26 sidecar route authority selection rule drifted")
    if type(result["regulatory_element_id"]) is not int:
        raise ValueError("V26 sidecar regulatory element ID is invalid")
    if result["regulatory_element_id"] != result["route_traffic_authority_ids"][0]:
        raise ValueError("V26 sidecar selected traffic authority is not route-order first")
    result["physical_light_ids"] = _require_int_list(
        result["physical_light_ids"], "sidecar physical light IDs", nonempty=True
    )
    result["bulb_ids"] = _require_int_list(
        result["bulb_ids"], "sidecar bulb IDs", nonempty=True
    )
    if type(result["stop_line_id"]) is not int:
        raise ValueError("V26 sidecar stop-line ID is invalid")
    for key in (
        "stop_line_geometry_sha256",
        "route_graph_sha256",
        "signal_chain_sha256",
        "runtime_receipt_sha256",
    ):
        result[key] = _require_sha256(result[key], f"sidecar signal {key}")
    if result["phase_authority_mode"] != "observe_same_tick_request":
        raise ValueError("V26 sidecar cannot override the current signal phase")
    if result["current_phase"] not in _PHASES or result["source_valid"] is not True:
        raise ValueError("V26 sidecar current signal source is invalid")
    if (
        result["future_schedule_consumed"] is not False
        or result["candidate_tensor_consumed"] is not False
        or result["selected_trajectory_consumed"] is not False
    ):
        raise ValueError("V26 sidecar receipt consumed a forbidden input")
    return result


def load_autoware_sidecar_binding(
    probe_config: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and hash-bind the exact sidecar selected by a V26 probe config."""

    config = dict(probe_config)
    route_rows = config.get("routes")
    map_binding = config.get("map")
    sidecar = config.get("regulatory_sidecar")
    if (
        type(route_rows) is not list
        or len(route_rows) != 1
        or type(route_rows[0]) is not dict
        or type(map_binding) is not dict
        or type(sidecar) is not dict
    ):
        raise ValueError("V26 sidecar probe binding is incomplete")
    route_sha256 = _require_sha256(route_rows[0].get("sha256"), "probe route SHA")
    map_sha256 = _require_sha256(map_binding.get("sha256"), "probe map SHA")
    needed = {
        "geometry_copy_sha256",
        "index_path",
        "index_sha256",
        "manifest_path",
        "manifest_sha256",
        "source_sha256",
    }
    if not needed.issubset(sidecar):
        raise ValueError("V26 sidecar probe fields are incomplete")
    index_path = Path(str(sidecar["index_path"])).resolve()
    manifest_path = Path(str(sidecar["manifest_path"])).resolve()
    if (
        not index_path.is_file()
        or not manifest_path.is_file()
        or _sha256_file(index_path) != _require_sha256(sidecar["index_sha256"], "sidecar index SHA")
        or _sha256_file(manifest_path)
        != _require_sha256(sidecar["manifest_sha256"], "sidecar manifest SHA")
    ):
        raise ValueError("V26 Autoware sidecar artifact drifted")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        index.get("schema") != "camp_autoware_lanelet2_regulatory_sidecar_index_v2"
        or index.get("status") != "materialized_zero_model"
        or manifest.get("geometry_copy_sha256") != map_sha256
        or manifest.get("geometry_copy_sha256")
        != _require_sha256(sidecar["geometry_copy_sha256"], "sidecar geometry SHA")
        or manifest.get("source_sha256")
        != _require_sha256(sidecar["source_sha256"], "sidecar source SHA")
    ):
        raise ValueError("V26 Autoware sidecar identity drifted")
    entries = index.get("manifests")
    if type(entries) is not list or not any(
        type(entry) is dict
        and entry.get("manifest_path") == str(manifest_path)
        and entry.get("manifest_sha256") == sidecar["manifest_sha256"]
        and entry.get("geometry_copy_sha256") == map_sha256
        and entry.get("source_sha256") == sidecar["source_sha256"]
        for entry in entries
    ):
        raise ValueError("V26 Autoware sidecar index does not bind the manifest")
    binding = validate_autoware_sidecar_binding(
        {
            "schema_version": SIDECAR_BINDING_SCHEMA_VERSION,
            "route_sha256": route_sha256,
            "map_sha256": map_sha256,
            "geometry_copy_sha256": str(sidecar["geometry_copy_sha256"]),
            "sidecar_index_sha256": str(sidecar["index_sha256"]),
            "sidecar_manifest_sha256": str(sidecar["manifest_sha256"]),
            "sidecar_source_sha256": str(sidecar["source_sha256"]),
        }
    )
    return binding, manifest


class V26AutowareSidecarSignalAdapter:
    """Observe (never override) the current phase from a sealed sidecar route."""

    def __init__(self, *, binding: Mapping[str, Any], sidecar_manifest: Mapping[str, Any]) -> None:
        self.binding = validate_autoware_sidecar_binding(binding)
        manifest = dict(sidecar_manifest)
        if (
            manifest.get("geometry_copy_sha256") != self.binding["map_sha256"]
            or manifest.get("source_sha256") != self.binding["sidecar_source_sha256"]
            or type(manifest.get("lanelets")) is not list
            or type(manifest.get("regulatory_elements")) is not list
        ):
            raise ValueError("V26 sidecar manifest does not match the probe binding")
        self._lanelets = {int(item["id"]): dict(item) for item in manifest["lanelets"]}
        self._regulatory = {
            int(item["id"]): dict(item) for item in manifest["regulatory_elements"]
        }
        if not self._lanelets or not self._regulatory:
            raise ValueError("V26 sidecar manifest has no route/signal inventory")
        self._builder: Any | None = None
        self._route_lanelet_ids: tuple[int, ...] = ()
        self._map_lanelet_ids: tuple[int, ...] = ()
        self._controlled_lanelet_ids: tuple[int, ...] = ()
        self._route_traffic_authority_ids: tuple[int, ...] = ()
        self._signal_record: dict[str, Any] | None = None
        self._chain: dict[str, Any] | None = None
        self._last_runtime: dict[str, Any] | None = None

    def bind_builder(self, builder: Any) -> None:
        if self._builder is not None and self._builder is not builder:
            raise ValueError("V26 sidecar adapter builder binding drifted")
        if not hasattr(builder, "_cache") or not hasattr(builder, "_ll_by_id"):
            raise ValueError("V26 sidecar adapter requires the fixed route graph builder")
        self._builder = builder

    def bind_runtime_lanelet_ids(
        self, *, route_lanelet_ids: Sequence[int], map_lanelet_ids: Sequence[int]
    ) -> None:
        if self._builder is None:
            raise ValueError("V26 sidecar adapter is not bound to the route graph")
        route = tuple(int(value) for value in route_lanelet_ids)
        mapped = tuple(int(value) for value in map_lanelet_ids)
        if (
            not route
            or not mapped
            or len(set(route)) != len(route)
            or len(set(mapped)) != len(mapped)
            or any(value not in self._lanelets for value in route)
        ):
            raise ValueError("V26 sidecar runtime route/map IDs are invalid")
        candidates: list[int] = []
        for lanelet_id in route:
            for regulatory_id in self._lanelets[lanelet_id].get("regulatory_element_ids", []):
                if (
                    type(regulatory_id) is int
                    and self._regulatory.get(regulatory_id, {}).get("runtime_type")
                    == "AutowareTrafficLight"
                    and regulatory_id not in candidates
                ):
                    candidates.append(regulatory_id)
        if not candidates:
            raise ValueError("V26 sidecar route has no traffic-light authority")
        # A frozen route may cross more than one real traffic signal.  The
        # current request is routed in source order, so the first controlled
        # lanelet is the unique causal authority for this planning state; this
        # is deterministic route semantics, not a result-driven choice.
        regulatory_id = candidates[0]
        controlled = tuple(
            lanelet_id
            for lanelet_id in route
            if regulatory_id in self._lanelets[lanelet_id].get("regulatory_element_ids", [])
        )
        if not controlled:
            raise ValueError("V26 sidecar traffic authority has no controlled route lanelet")
        actual = {
            int(element.id)
            for lanelet_id in controlled
            for element in self._builder._ll_by_id[int(lanelet_id)].trafficLights()
        }
        if regulatory_id not in actual:
            raise ValueError("V26 sidecar traffic authority is absent from the live route graph")
        record = self._regulatory[regulatory_id]
        stop_line_id, stop_line = self._stop_line(record)
        physical_ids, bulb_ids = self._physical_ids(record)
        route_world = self._route_world(route)
        route_geometry_sha256 = canonical_json_sha256(route_world.tolist())
        tangent = route_world[1] - route_world[0]
        norm = float(np.linalg.norm(tangent))
        if not math.isfinite(norm) or norm <= 0.0:
            raise ValueError("V26 sidecar route graph has a degenerate tangent")
        tangent = (tangent / norm).astype(np.float64)
        chain_payload = {
            "schema_version": SIDECAR_SIGNAL_CHAIN_SCHEMA_VERSION,
            "binding": self.binding,
            "route_lanelet_ids": list(route),
            "controlled_lanelet_ids": list(controlled),
            "route_traffic_authority_ids": list(candidates),
            "authority_selection_rule": "first_controlled_lanelet_in_frozen_route_order",
            "regulatory_element_id": regulatory_id,
            "physical_light_ids": physical_ids,
            "bulb_ids": bulb_ids,
            "stop_line_id": stop_line_id,
            "stop_line_geometry_sha256": canonical_json_sha256(stop_line.tolist()),
            "route_graph_sha256": route_geometry_sha256,
            "route_tangent_world": tangent.tolist(),
        }
        self._route_lanelet_ids = route
        self._map_lanelet_ids = mapped
        self._controlled_lanelet_ids = controlled
        self._route_traffic_authority_ids = tuple(candidates)
        self._signal_record = {
            "regulatory_element_id": regulatory_id,
            "physical_light_ids": physical_ids,
            "bulb_ids": bulb_ids,
            "stop_line_id": stop_line_id,
            "stop_line_world": stop_line,
            "route_graph_sha256": route_geometry_sha256,
            "route_tangent_world": tangent,
        }
        self._chain = {**chain_payload, "signal_chain_sha256": _canonical_sha256(chain_payload)}

    def __call__(self, scene: Any, tick_index: int) -> Mapping[str, Any]:
        runtime = self._observe_runtime(scene, tick_index)
        return {
            "schema_version": SIDECAR_CONTROLLED_SCENE_SCHEMA_VERSION,
            "signal_authority": self._signal_receipt(runtime),
            "outcome_fields_consumed": [],
            "candidate_tensor_consumed": False,
            "selected_trajectory_consumed": False,
        }

    def sync_model_input_map_cache(
        self, scene: Any, map_cache: Any, tick_index: int
    ) -> Mapping[str, Any]:
        runtime = self._require_runtime(scene, tick_index)
        if map_cache is None or not callable(getattr(map_cache, "sync_tl_state", None)):
            raise ValueError("V26 sidecar requires the fixed-DP MapTensorCache")
        scene_lanes = np.asarray(scene.map_data.lanes)
        cached = np.asarray(getattr(map_cache, "_all_lanes", None))
        if scene_lanes.shape != cached.shape or scene_lanes.ndim != 3 or scene_lanes.shape[-1] < 13:
            raise ValueError("V26 sidecar model cache signal tensors are malformed")
        before = np.ascontiguousarray(cached[:, :, 8:13], dtype=np.float32)
        expected = np.ascontiguousarray(scene_lanes[:, :, 8:13], dtype=np.float32)
        map_cache.sync_tl_state(scene.map_data)
        after = np.ascontiguousarray(np.asarray(map_cache._all_lanes)[:, :, 8:13], dtype=np.float32)
        if not np.array_equal(after, expected):
            raise ValueError("fixed-DP model cache did not consume the observed sidecar phase")
        return {
            "schema_version": "camp_dp_v26_autoware_sidecar_model_cache_v1",
            "tick_index": tick_index,
            "signal_chain_sha256": runtime["signal_chain_sha256"],
            "cache_tl_sha256_before": hashlib.sha256(before.tobytes()).hexdigest(),
            "cache_tl_sha256_after": hashlib.sha256(after.tobytes()).hexdigest(),
            "cache_matches_scene_after": True,
            "phase_authority_mode": "observe_same_tick_request",
            "future_schedule_consumed": False,
        }

    def causal_signal_atom_input(self, scene: Any, tick_index: int) -> Mapping[str, Any]:
        runtime = self._require_runtime(scene, tick_index)
        record = self._require_signal_record()
        ego = scene.ego_agent
        position = np.asarray(ego.current_position, dtype=np.float64)
        heading = float(ego.current_heading)
        if position.shape != (2,) or not np.isfinite(position).all() or not math.isfinite(heading):
            raise ValueError("V26 sidecar ego pose is invalid")
        stop_world = record["stop_line_world"]
        c, s = math.cos(heading), math.sin(heading)
        rotation = np.asarray([[c, s], [-s, c]], dtype=np.float64)
        payload = {
            "schema_version": CAUSAL_SIGNAL_ATOM_INPUT_SCHEMA_VERSION,
            "source_state": "available",
            "source_valid": True,
            "applicable": runtime["current_phase"] == "red",
            "current_phase": runtime["current_phase"],
            "decision_time_s": runtime["decision_time_s"],
            "ego_position_world_m": position.tolist(),
            "ego_heading_rad": heading,
            "regulatory_element_id": record["regulatory_element_id"],
            "stop_line_id": record["stop_line_id"],
            "stop_line_geometry_world_m": stop_world.tolist(),
            "stop_line_geometry_ego_m": (
                (stop_world - position.reshape(1, 2)) @ rotation.T
            ).tolist(),
            "stop_line_geometry_sha256": canonical_json_sha256(stop_world.tolist()),
            "route_tangent_world": record["route_tangent_world"].tolist(),
            "route_tangent_ego": (rotation @ record["route_tangent_world"]).tolist(),
            "route_geometry_sha256": record["route_graph_sha256"],
            "route_arc_m": 0.0,
            "source_chain_sha256": runtime["signal_chain_sha256"],
            "runtime_receipt": runtime,
            "runtime_receipt_sha256": canonical_json_sha256(runtime),
        }
        return validate_causal_signal_atom_input(payload)

    def _require_runtime(self, scene: Any, tick_index: int) -> dict[str, Any]:
        runtime = self._observe_runtime(scene, tick_index)
        if self._last_runtime is not None and runtime != self._last_runtime:
            raise ValueError("V26 sidecar current signal changed within one planning tick")
        self._last_runtime = runtime
        return runtime

    def _observe_runtime(self, scene: Any, tick_index: int) -> dict[str, Any]:
        if type(tick_index) is not int or tick_index < 0:
            raise ValueError("V26 sidecar tick index is invalid")
        record = self._require_signal_record()
        route, mapped = self._runtime_tensors(scene)
        phase = self._phase(route, self._route_lanelet_ids, label="route")
        map_phase = self._phase(mapped, self._map_lanelet_ids, label="map")
        if phase != map_phase:
            raise ValueError("V26 sidecar route/map current phases disagree")
        decision = float(tick_index) * float(scene.dt)
        if not math.isfinite(decision) or decision < 0.0:
            raise ValueError("V26 sidecar decision time is invalid")
        runtime = {
            "schema_version": "camp_dp_v26_autoware_sidecar_runtime_signal_v1",
            "signal_chain_sha256": self._chain["signal_chain_sha256"],
            # The frozen atom validator consumes this generic causal binding;
            # retain the V26 chain ID under its established field name too.
            "source_chain_sha256": self._chain["signal_chain_sha256"],
            "current_phase": phase,
            "decision_time_s": decision,
            "source_time_s": decision,
            "source_age_s": 0.0,
            "freshness": "same_tick",
            "phase_authority_mode": "observe_same_tick_request",
            "regulatory_element_id": record["regulatory_element_id"],
            "stop_line_id": record["stop_line_id"],
            "stop_line_geometry_sha256": canonical_json_sha256(record["stop_line_world"].tolist()),
            "route_graph_sha256": record["route_graph_sha256"],
            "route_geometry_sha256": record["route_graph_sha256"],
            "route_signal_tensor_sha256": hashlib.sha256(
                np.ascontiguousarray(route[:, :, 8:13], dtype=np.float32).tobytes()
            ).hexdigest(),
            "map_signal_tensor_sha256": hashlib.sha256(
                np.ascontiguousarray(mapped[:, :, 8:13], dtype=np.float32).tobytes()
            ).hexdigest(),
            "future_schedule_consumed": False,
            "source_valid": True,
        }
        return runtime

    def _signal_receipt(self, runtime: Mapping[str, Any]) -> dict[str, Any]:
        record = self._require_signal_record()
        return validate_autoware_sidecar_signal_receipt(
            {
                "schema_version": SIDECAR_SIGNAL_RECEIPT_SCHEMA_VERSION,
                "binding": self.binding,
                "route_lanelet_ids": list(self._route_lanelet_ids),
                "controlled_lanelet_ids": list(self._controlled_lanelet_ids),
                "route_traffic_authority_ids": list(self._route_traffic_authority_ids),
                "authority_selection_rule": "first_controlled_lanelet_in_frozen_route_order",
                "regulatory_element_id": record["regulatory_element_id"],
                "physical_light_ids": list(record["physical_light_ids"]),
                "bulb_ids": list(record["bulb_ids"]),
                "stop_line_id": record["stop_line_id"],
                "stop_line_geometry_sha256": canonical_json_sha256(record["stop_line_world"].tolist()),
                "route_graph_sha256": record["route_graph_sha256"],
                "signal_chain_sha256": str(runtime["signal_chain_sha256"]),
                "runtime_receipt_sha256": canonical_json_sha256(runtime),
                "phase_authority_mode": "observe_same_tick_request",
                "current_phase": str(runtime["current_phase"]),
                "source_valid": True,
                "future_schedule_consumed": False,
                "candidate_tensor_consumed": False,
                "selected_trajectory_consumed": False,
            }
        )

    def _runtime_tensors(self, scene: Any) -> tuple[np.ndarray, np.ndarray]:
        ego = scene.ego_agent
        if ego is None or getattr(ego, "route_lanes", None) is None:
            raise ValueError("V26 sidecar route request tensor is unavailable")
        route = np.asarray(ego.route_lanes)
        if route.ndim != 3 or route.shape[-1] < 13 or len(route) < len(self._route_lanelet_ids):
            raise ValueError("V26 sidecar route request tensor is malformed")
        if len(route) > len(self._route_lanelet_ids) and np.any(
            np.abs(route[len(self._route_lanelet_ids) :]) > 0.0
        ):
            raise ValueError("V26 sidecar route request has unmapped nonzero rows")
        if scene.map_data is None or getattr(scene.map_data, "lanes", None) is None:
            raise ValueError("V26 sidecar map request tensor is unavailable")
        mapped = np.asarray(scene.map_data.lanes)
        if (
            mapped.ndim != 3
            or mapped.shape[-1] < 13
            or len(mapped) != len(self._map_lanelet_ids)
            or not np.isfinite(route).all()
            or not np.isfinite(mapped).all()
        ):
            raise ValueError("V26 sidecar map request tensor is malformed")
        return route[: len(self._route_lanelet_ids)], mapped

    def _phase(self, tensor: np.ndarray, lanelet_ids: Sequence[int], *, label: str) -> str:
        rows = []
        for lanelet_id in self._controlled_lanelet_ids:
            try:
                index = list(lanelet_ids).index(lanelet_id)
            except ValueError as exc:
                raise ValueError(f"V26 sidecar {label} omits controlled lanelet") from exc
            state = np.asarray(tensor[index, :, 8:11], dtype=np.float64)
            if state.ndim != 2 or state.shape[1] != 3:
                raise ValueError(f"V26 sidecar {label} signal tensor shape drifted")
            active_rows = np.any(np.abs(state) > 1e-12, axis=1)
            if not np.any(active_rows):
                raise ValueError(f"V26 sidecar {label} current phase is unavailable")
            observed = state[active_rows]
            active = [
                phase
                for phase, column in _PHASE_CHANNELS.items()
                if np.allclose(observed[:, column - 8], 1.0, rtol=0.0, atol=1e-8)
                and all(
                    np.allclose(observed[:, other - 8], 0.0, rtol=0.0, atol=1e-8)
                    for other in _PHASE_CHANNELS.values()
                    if other != column
                )
            ]
            if len(active) != 1:
                raise ValueError(f"V26 sidecar {label} current phase is unavailable")
            rows.append(active[0])
        if not rows or len(set(rows)) != 1:
            raise ValueError(f"V26 sidecar {label} current phase is ambiguous")
        return rows[0]

    def _route_world(self, route: Sequence[int]) -> np.ndarray:
        pieces: list[np.ndarray] = []
        for lanelet_id in route:
            cached = self._builder._cache.get(int(lanelet_id))
            if cached is None:
                raise ValueError("V26 sidecar route graph cache is incomplete")
            line = np.asarray(cached.raw_centerline, dtype=np.float64)
            if line.ndim != 2 or line.shape[1] != 2 or len(line) < 2 or not np.isfinite(line).all():
                raise ValueError("V26 sidecar route graph geometry is invalid")
            pieces.append(line if not pieces else line[1:])
        route_world = np.concatenate(pieces, axis=0)
        if len(route_world) < 2 or not np.isfinite(route_world).all():
            raise ValueError("V26 sidecar route graph is empty")
        return route_world

    @staticmethod
    def _stop_line(record: Mapping[str, Any]) -> tuple[int, np.ndarray]:
        rows = [
            primitive
            for role in record.get("roles", [])
            if type(role) is dict and role.get("role") == "ref_line"
            for primitive in role.get("primitives", [])
            if type(primitive) is dict
        ]
        if len(rows) != 1 or type(rows[0].get("id")) is not int:
            raise ValueError("V26 sidecar traffic light has no unique stop line")
        points = np.asarray(
            [[point.get("x"), point.get("y")] for point in rows[0].get("points", [])],
            dtype=np.float64,
        )
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all():
            raise ValueError("V26 sidecar stop-line geometry is invalid")
        return int(rows[0]["id"]), points

    @staticmethod
    def _physical_ids(record: Mapping[str, Any]) -> tuple[list[int], list[int]]:
        physical = [
            int(primitive["id"])
            for role in record.get("roles", [])
            if type(role) is dict and role.get("role") == "refers"
            for primitive in role.get("primitives", [])
            if type(primitive) is dict and type(primitive.get("id")) is int
        ]
        bulbs = [
            int(point["id"])
            for role in record.get("roles", [])
            if type(role) is dict and role.get("role") == "light_bulbs"
            for primitive in role.get("primitives", [])
            if type(primitive) is dict
            for point in primitive.get("points", [])
            if type(point) is dict and type(point.get("id")) is int
        ]
        return (
            _require_int_list(physical, "sidecar physical light IDs", nonempty=True),
            _require_int_list(bulbs, "sidecar bulb IDs", nonempty=True),
        )

    def _require_signal_record(self) -> dict[str, Any]:
        if self._signal_record is None or self._chain is None:
            raise ValueError("V26 sidecar signal chain is not bound to a route graph")
        return self._signal_record
