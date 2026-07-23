from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .diffusion_planner_v25_controlled_scenarios import (
    SCHEMA_VERSION as CONTROLLED_CASE_SCHEMA_VERSION,
    V25ControlledSceneAdapter,
    _materialize_semantics,
    validate_controlled_scenario_case,
)
from .diffusion_planner_v25_route_signal_authority import (
    MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
    validate_mapped_signal_chain,
)
from .diffusion_planner_v25_signal_complete_plan import (
    NATURALISTIC_SCENARIO_FAMILY,
    NATURALISTIC_TIER,
)
from .diffusion_planner_v25_semantic_authority import (
    build_semantic_clone_payload,
    canonical_json_sha256,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_runtime_case_v1"


class V25SignalCompleteBackgroundAdapter(V25ControlledSceneAdapter):
    """No-script mapped-signal adapter for the disclosed background stratum."""

    def __init__(
        self, case: Mapping[str, Any], *, mapped_signal_authority: Mapping[str, Any]
    ) -> None:
        _validate_naturalistic_background_case(case)
        chain = validate_mapped_signal_chain(mapped_signal_authority)
        if (
            case.get("signal_source_class") != "mapped_signal"
            or case.get("phase_authority_mode") != "observe_same_tick_request"
            or chain["phase_authority_mode"] != "observe_same_tick_request"
            or chain["scenario_id"] != case["scenario_id"]
            or chain["route_identity_sha256"] != case["route_identity_sha256"]
            or chain["source_map_sha256"] != case["source_map_sha256"]
        ):
            raise ValueError("naturalistic background signal authority drifted")
        self.case = dict(case)
        self.mapped_signal_authority = chain
        self.no_signal_authority = None
        self._route_lanelet_ids = ()
        self._map_lanelet_ids = ()
        self.receipts = []


def build_signal_complete_scene_adapter(
    prepared: Mapping[str, Any],
) -> V25ControlledSceneAdapter:
    """Construct the production adapter without changing the 7-family grammar."""

    if (
        type(prepared) is not dict
        or prepared.get("schema_version") != SCHEMA_VERSION
        or prepared.get("status")
        != "signal_complete_runtime_case_source_qualified"
        or prepared.get("model_loaded") is not False
        or prepared.get("candidate_generation_executed") is not False
        or prepared.get("fresh_b2_opened") is not False
        or prepared.get("outcome_fields_consumed") != []
    ):
        raise ValueError("signal-complete prepared runtime authority drifted")
    case = prepared.get("case")
    mapped = prepared.get("mapped_signal_authority")
    if type(case) is not dict or type(mapped) is not dict:
        raise ValueError("signal-complete prepared runtime source is missing")
    if case.get("family") == NATURALISTIC_SCENARIO_FAMILY:
        return V25SignalCompleteBackgroundAdapter(
            case, mapped_signal_authority=mapped
        )
    return V25ControlledSceneAdapter(case, mapped_signal_authority=mapped)


def build_signal_complete_runtime_case(
    identity: Mapping[str, Any], *, map_artifact: Path, seeds: list[int]
) -> dict[str, Any]:
    """Bind one frozen plan identity to a materialized map and source chain.

    This is source/geometry preparation only.  It does not load fixed DP,
    generate candidates, execute calibration, or open Fresh B2.
    """

    if type(identity) is not dict:
        raise ValueError("signal-complete identity must be a native mapping")
    if (
        type(seeds) is not list
        or not seeds
        or any(type(seed) is not int or seed < 0 for seed in seeds)
        or len(seeds) != len(set(seeds))
    ):
        raise ValueError("signal-complete runtime seeds are invalid")
    map_root = map_artifact.resolve()
    map_path = (map_root / str(identity.get("map_relative_path"))).resolve()
    if map_root not in map_path.parents or not map_path.is_file():
        raise ValueError("signal-complete runtime map path escaped or is missing")
    if _sha256(map_path) != identity.get("map_sha256"):
        raise ValueError("signal-complete runtime map SHA drifted")

    route_world = _route_polyline_world(identity)
    route_headings = _polyline_headings(route_world)
    source_chain = identity.get("source_chain")
    physical = identity.get("physical_payload")
    if type(source_chain) is not dict or type(physical) is not dict:
        raise ValueError("signal-complete runtime physical source is missing")
    branch = max(abs(float(value)) for value in physical["turn_angles_rad"]) >= 0.08
    route_record = {
        "identity_sha256": identity["route_identity_sha256"],
        "record_key": identity["route_identity_sha256"],
        "map_family_id": identity["map_sha256"],
        "route_serialization_sha256": identity["route_family_sha256"],
        "source_map_path": str(map_path),
        "source_map_sha256": identity["map_sha256"],
        "route_spec": identity["route_spec"],
        "source_stratum": {
            "traffic_light": True,
            "branch_intersection": branch,
        },
        "centerline_samples_m": route_world.tolist(),
        "centerline_headings_rad": route_headings.tolist(),
        "source_route_length_m": float(identity["route_length_m"]),
    }
    parameters = dict(identity["parameters"])
    if identity.get("benchmark_stratum") == "naturalistic":
        actors = []
        signal = {"phase": "none", "mapped_source_required": False}
    else:
        actors, signal = _materialize_semantics(
            route=route_record,
            family=str(identity["scenario_family"]),
            tier=str(identity["risk_tier"]),
            semantic_variant=str(identity["semantic_variant"]),
            params=parameters,
        )
    signal = dict(signal)
    signal.pop("phase_remaining_s", None)
    if identity["phase_authority_mode"] == "controlled_same_tick_override":
        if signal.get("phase") != identity["controlled_current_phase"]:
            raise ValueError("controlled current phase differs from frozen plan")
        signal["mapped_source_required"] = True
    else:
        if signal.get("phase") != "none" or identity["controlled_current_phase"] is not None:
            raise ValueError("observed current-phase identity drifted")
        signal["mapped_source_required"] = False

    case_identity_payload = {
        "schema_version": CONTROLLED_CASE_SCHEMA_VERSION,
        "split": identity["split"] if "split" in identity else "unknown",
        "family": identity["scenario_family"],
        "tier": identity["risk_tier"],
        "semantic_variant": identity["semantic_variant"],
        "parameter_block_id": identity["semantic_parameter_block_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "seeds": seeds,
        "parameters": parameters,
        "actors": actors,
        "signal": signal,
    }
    scenario_id = _canonical_sha(case_identity_payload)
    case = {
        **case_identity_payload,
        "scenario_id": scenario_id,
        "record_key": identity["route_identity_sha256"],
        "map_family_id": identity["map_sha256"],
        "corridor_group_sha256": identity["corridor_sha256"],
        "route_family_id": identity["route_family_sha256"],
        "source_map_path": str(map_path),
        "source_map_sha256": identity["map_sha256"],
        "route_spec": identity["route_spec"],
        "source_stratum": route_record["source_stratum"],
        "source_availability": {"mapped_traffic_light": True},
        "runner_eligible": True,
        "source_requirements": [
            "fixed_dp_current_request",
            "fixed_k8",
            "explicit_lanelet2_route",
            "mapped_traffic_light_regulatory_source",
        ],
        "outcome_blind": True,
        "outcome_fields_consumed": [],
        "holdout_outcome_consumed": False,
        "signal_source_class": "mapped_signal",
        "phase_authority_mode": identity["phase_authority_mode"],
    }
    if identity.get("benchmark_stratum") == "naturalistic":
        _validate_naturalistic_background_case(case)
    else:
        validate_controlled_scenario_case(case)
    mapped = _mapped_signal_authority(
        case=case,
        identity=identity,
        route_world=route_world,
    )
    case["mapped_signal_authority"] = mapped
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "signal_complete_runtime_case_source_qualified",
        "identity_ordinal": identity["identity_ordinal"],
        "scenario_identity_sha256": identity["scenario_identity_sha256"],
        "map_artifact": str(map_root),
        "case": case,
        "mapped_signal_authority": mapped,
        "route_polyline_world_m": route_world.tolist(),
        "model_loaded": False,
        "candidate_generation_executed": False,
        "training_executed": False,
        "calibration_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _validate_naturalistic_background_case(case: Mapping[str, Any]) -> None:
    """Validate the no-script Fresh stratum without changing the 7-family grammar.

    ``naturalistic_background`` means only that the deterministic benchmark
    supplies no scripted stress actor or phase override.  It is intentionally
    not added to ``SCENARIO_FAMILIES`` because doing so would change the frozen
    controlled-train denominator.
    """

    if case.get("schema_version") != CONTROLLED_CASE_SCHEMA_VERSION:
        raise ValueError("naturalistic background schema mismatch")
    if (
        case.get("split") not in {"fresh_b2", "fresh_b3"}
        or case.get("family") != NATURALISTIC_SCENARIO_FAMILY
        or case.get("tier") != NATURALISTIC_TIER
        or case.get("actors") != []
        or case.get("signal")
        != {"phase": "none", "mapped_source_required": False}
        or case.get("phase_authority_mode") != "observe_same_tick_request"
        or case.get("signal_source_class") != "mapped_signal"
        or case.get("runner_eligible") is not True
        or case.get("outcome_blind") is not True
        or case.get("outcome_fields_consumed") != []
        or case.get("holdout_outcome_consumed") is not False
    ):
        raise ValueError("naturalistic background runtime contract drifted")
    scenario_id = case.get("scenario_id")
    seeds = case.get("seeds")
    if (
        type(scenario_id) is not str
        or len(scenario_id) != 64
        or set(scenario_id) - set("0123456789abcdef")
        or type(seeds) is not list
        or not seeds
        or any(type(seed) is not int or seed < 0 for seed in seeds)
        or len(seeds) != len(set(seeds))
    ):
        raise ValueError("naturalistic background identity or seeds drifted")


def _mapped_signal_authority(
    *, case: Mapping[str, Any], identity: Mapping[str, Any], route_world: np.ndarray
) -> dict[str, Any]:
    source = identity["source_chain"]
    stop = np.asarray(source["certified_stop_line_geometry_m"], dtype=np.float64)
    semantic = build_semantic_clone_payload(
        case,
        route_polyline_world=route_world,
        stop_line_world=stop,
    )
    tangent = route_world[1] - route_world[0]
    tangent = tangent / np.linalg.norm(tangent)
    expected_phase = identity["controlled_current_phase"]
    mode = identity["phase_authority_mode"]
    without_hash = {
        "schema_version": MAPPED_SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "source_map_sha256": identity["map_sha256"],
        "phase_authority_mode": mode,
        "expected_current_phase": expected_phase,
        "formal_phase": expected_phase if expected_phase is not None else "none",
        "formal_mapped_source_required": expected_phase is not None,
        "formal_route_mapped_traffic_light": True,
        "phase_remaining_available": False,
        "regulatory_element_ids": [source["traffic_light_regulatory_element_id"]],
        "physical_light_ids": [source["physical_traffic_light_id"]],
        "bulb_ids": [source["light_bulb_linestring_id"]],
        "controlled_lanelet_ids": [source["controlled_lanelet_id"]],
        "route_lanelet_ids": list(source["route_lanelet_ids"]),
        "route_geometry_sha256": canonical_json_sha256(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        ),
        "stop_line_id": source["certified_stop_line_id"],
        "stop_line_geometry_m": stop.tolist(),
        "stop_line_geometry_sha256": canonical_json_sha256(stop.tolist()),
        "stop_line_route_distance_m": _point_polyline_distance(stop.mean(axis=0), route_world),
        "route_arc_m": float(source["stop_line_route_arc_m"]),
        "route_length_m": float(identity["route_length_m"]),
        "route_tangent_world": tangent.tolist(),
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
    }
    chain = {**without_hash, "source_chain_sha256": canonical_json_sha256(without_hash)}
    return validate_mapped_signal_chain(chain)


def _route_polyline_world(identity: Mapping[str, Any]) -> np.ndarray:
    local = np.asarray(
        identity["physical_payload"]["centerline_route_local_m"], dtype=np.float64
    )
    pose = np.asarray(identity["initial_pose"], dtype=np.float64)
    if local.ndim != 2 or local.shape[1] != 2 or pose.shape != (3,):
        raise ValueError("signal-complete route geometry is malformed")
    c = math.cos(float(pose[2]))
    s = math.sin(float(pose[2]))
    rotation = np.asarray([[c, s], [-s, c]], dtype=np.float64)
    world = local @ rotation + pose[:2]
    if not np.isfinite(world).all() or len(world) < 2:
        raise ValueError("signal-complete route geometry is nonfinite")
    return world


def _polyline_headings(points: np.ndarray) -> np.ndarray:
    delta = np.diff(points, axis=0)
    if np.any(np.linalg.norm(delta, axis=1) <= 1e-9):
        raise ValueError("signal-complete route contains a degenerate segment")
    headings = np.arctan2(delta[:, 1], delta[:, 0])
    return np.concatenate((headings, headings[-1:]))


def _point_polyline_distance(point: np.ndarray, line: np.ndarray) -> float:
    best = math.inf
    for start, end in zip(line[:-1], line[1:], strict=True):
        delta = end - start
        ratio = float(np.clip(np.dot(point - start, delta) / np.dot(delta, delta), 0.0, 1.0))
        best = min(best, float(np.linalg.norm(point - (start + ratio * delta))))
    return best


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()
