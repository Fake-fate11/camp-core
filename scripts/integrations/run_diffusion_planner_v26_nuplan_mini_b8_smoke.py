#!/usr/bin/env python3
"""Run a V26-native official-nuPlan same-ego B8 adapter smoke.

The adapter mode runs with the nuPlan devkit interpreter and serializes only
the causal fixed-DP input.  The smoke mode runs with the fixed-DP interpreter,
loads that input, performs exactly one B8 forward, and lets the adapted
Static14D/Scene14D selectors consume the resulting frozen pool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    DP_CAMP_ATOM_NAMES_V10,
    canonical_score_atoms,
)
from camp_core.integrations.diffusion_planner_causal_materializer import (  # noqa: E402
    validate_causal_dp_input,
)
from camp_core.integrations.diffusion_planner_v21_native import array_sha256  # noqa: E402
from camp_core.integrations.diffusion_planner_camp_context_math import (  # noqa: E402
    CAMPContextScaler,
    context_weights,
)
from camp_core.integrations.diffusion_planner_v26_source_capabilities import (  # noqa: E402
    build_v26_camp_raw_context,
    materialize_v26_camp_atoms,
    v26_source_capabilities,
)
from camp_core.integrations.diffusion_planner_v26_nuplan import (  # noqa: E402
    FIXED_DP_HEAD,
    NUPLAN_V26_ADAPTER_ID,
    NUPLAN_V26_RUNNER_ID,
    bind_v26_nuplan_same_pool_selectors,
    canonical_json_bytes,
    materialize_v26_nuplan_planner_input,
    run_v26_nuplan_single_invocation_b8,
    validate_v26_nuplan_source_record,
)


SCHEMA = "camp_dp_v26_official_nuplan_same_ego_b8_smoke_v2"
EVIDENCE_ROLE = "development_nonholdout_official_nuplan_adapter_smoke"
ZERO_CALLS = {"model_calls": 0, "dp_calls": 0, "gpu_calls": 0}
V26_NUPLAN_NO_SIGNAL_ADAPTER_ID = (
    "camp_dp_v26_official_nuplan_no_signal_adapter_v1"
)
FROZEN_CAUSAL_SIGNAL_INPUT_SCHEMA = "camp_dp_v25_causal_signal_atom_input_v2"
_CITY_BY_MAP = {
    "us-ma-boston": "boston",
    "us-pa-pittsburgh-hazelwood": "pittsburgh",
    "sg-one-north": "singapore",
    "us-nv-las-vegas-strip": "las_vegas",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_arrays(arrays: Mapping[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for key in sorted(arrays):
        value = np.ascontiguousarray(np.asarray(arrays[key]))
        digest.update(key.encode("utf-8"))
        digest.update(value.dtype.str.encode("ascii"))
        digest.update(json.dumps(list(value.shape), separators=(",", ":")).encode("ascii"))
        digest.update(value.tobytes())
    return digest.hexdigest()


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_bytes(canonical_json_bytes(dict(value)))
    os.replace(temporary, path)


def _write_npz_atomic(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    with temporary.open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    os.replace(temporary, path)


def _status(status: str, reason: str, **calls: int) -> dict[str, Any]:
    return {"schema": SCHEMA, "status": status, "reason": reason, **ZERO_CALLS, **calls}


def _completed_smoke_status(model_calls: int) -> dict[str, Any]:
    if isinstance(model_calls, bool) or not isinstance(model_calls, int) or model_calls < 0:
        raise ValueError("completed smoke model call count is invalid")
    return _status(
        "complete",
        "same_ego_b8",
        model_calls=model_calls,
        dp_calls=model_calls,
        gpu_calls=int(model_calls > 0),
    )


def _map_path(
    data_root: Path,
    location: str,
    map_name: str,
    *,
    maps_root: Path | None = None,
) -> Path:
    """Resolve the actual official mini archive map layout without guessing.

    The DB ``location`` is a city label (for example ``las_vegas``), while the
    assembled v1.1 archive is laid out as ``maps/<map_name>/<map_revision>``.
    A source map must therefore have exactly one archive-provided revision.
    """

    directory = (maps_root if maps_root is not None else data_root / "maps") / map_name
    candidates = sorted(directory.glob("*/map.gpkg"))
    if len(candidates) != 1:
        raise FileNotFoundError(
            "official map layout must contain exactly one map.gpkg for "
            f"location={location!r}, map_name={map_name!r}: {candidates}"
        )
    return candidates[0]


def _source_route_identity(
    *, location: str, map_version: str, roadblock_chain: str
) -> dict[str, str]:
    """Hash the authoritative DB roadblock-chain representation.

    The three-city identity inventory and full-population sampling manifest use
    ``scene.roadblock_ids`` as the source-authoritative route representation.
    A ScenarioBuilder initialization may expand that route for runtime use, so
    its generated lanelet sequence is recorded separately rather than being
    substituted into the source identity.
    """

    normalized = str(roadblock_chain or "")
    if not normalized:
        raise ValueError("official source scene has no roadblock chain")
    route_sha256 = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    geometry_clone_group_sha256 = hashlib.sha256(
        canonical_json_bytes(
            {
                "location": str(location),
                "map_version": str(map_version),
                "roadblock_chain": normalized,
            }
        )
    ).hexdigest()
    return {
        "mission_route_roadblock_chain_sha256": route_sha256,
        "corridor_id": f"{location}:{route_sha256[:20]}",
        "geometry_clone_group_sha256": geometry_clone_group_sha256,
    }


def _decision_time_s(current_input: Any) -> float:
    """Read the same-tick official planner time without a fallback/default."""

    iteration = getattr(current_input, "iteration", None)
    time_point = getattr(iteration, "time_point", None)
    time_us = getattr(time_point, "time_us", None)
    if isinstance(time_us, (int, float)) and not isinstance(time_us, bool):
        decision_time_s = float(time_us) / 1e6
        if np.isfinite(decision_time_s) and decision_time_s >= 0.0:
            return decision_time_s
    raise ValueError("official mini planner input lacks a finite same-tick time")


def _build_v26_no_signal_authority(
    *,
    source: Mapping[str, Any],
    route_lanes: np.ndarray,
    traffic_light_data: Any,
    decision_time_s: float,
) -> dict[str, Any]:
    """Bind an explicit official empty traffic-light list to the shared atom API.

    No signal observation is represented as a source-valid, not-applicable
    red-light atom.  ``None`` or a nonempty list is deliberately rejected: the
    former is unknown and the latter requires the separate stop-line mapping.
    """

    if type(traffic_light_data) is not list:
        raise ValueError("official traffic-light authority must be an explicit list")
    if traffic_light_data:
        raise ValueError(
            "official nonempty traffic-light authority requires a V26 stop-line adapter"
        )
    if not np.isfinite(decision_time_s) or decision_time_s < 0.0:
        raise ValueError("official no-signal decision time is invalid")
    validated_source = validate_v26_nuplan_source_record(source)
    route_geometry_sha256 = array_sha256(np.ascontiguousarray(route_lanes))
    source_binding = {
        "adapter_id": V26_NUPLAN_NO_SIGNAL_ADAPTER_ID,
        "source_identity_sha256": validated_source["source_identity_sha256"],
        "source_db_sha256": validated_source["source_db_sha256"],
        "map_sha256": validated_source["map_sha256"],
        "route_geometry_sha256": route_geometry_sha256,
        "traffic_light_status_count": 0,
        "source_state": "not_applicable",
    }
    source_chain_sha256 = hashlib.sha256(canonical_json_bytes(source_binding)).hexdigest()
    runtime_receipt = {
        "schema_version": "camp_dp_v26_nuplan_signal_runtime_receipt_v1",
        "scenario_id": validated_source["scenario_token"],
        "tick_index": 0,
        "decision_time_s": float(decision_time_s),
        "source_mode": "same_tick_no_signal_rule_no_v2i",
        "current_phase": "none",
        "route_geometry_sha256": route_geometry_sha256,
        "source_chain_sha256": source_chain_sha256,
        "source_valid": True,
        "applicable": False,
        "traffic_light_status_count": 0,
        "adapter_id": V26_NUPLAN_NO_SIGNAL_ADAPTER_ID,
    }
    causal_signal_atom_input = {
        "schema_version": FROZEN_CAUSAL_SIGNAL_INPUT_SCHEMA,
        "source_state": "not_applicable",
        "source_valid": True,
        "applicable": False,
        "current_phase": "none",
        "decision_time_s": float(decision_time_s),
        "ego_position_world_m": None,
        "ego_heading_rad": None,
        "regulatory_element_id": None,
        "stop_line_id": None,
        "stop_line_geometry_world_m": None,
        "stop_line_geometry_ego_m": None,
        "stop_line_geometry_sha256": None,
        "route_tangent_world": None,
        "route_tangent_ego": None,
        "route_geometry_sha256": route_geometry_sha256,
        "route_arc_m": None,
        "source_chain_sha256": source_chain_sha256,
        "runtime_receipt": runtime_receipt,
        "runtime_receipt_sha256": hashlib.sha256(
            canonical_json_bytes(runtime_receipt)
        ).hexdigest(),
    }
    return {
        **source_binding,
        "typed_missing_atoms": [
            "planned_red_light_cost",
            "red_stopping_margin_cost",
        ],
        "red_light_endpoint_status": "missing_or_inapplicable",
        "causal_signal_atom_input": causal_signal_atom_input,
    }


def _require_v26_no_signal_authority(
    value: Mapping[str, Any], *, source: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V26 mini signal authority must be a mapping")
    required = {
        "adapter_id",
        "source_identity_sha256",
        "source_db_sha256",
        "map_sha256",
        "route_geometry_sha256",
        "traffic_light_status_count",
        "source_state",
        "typed_missing_atoms",
        "red_light_endpoint_status",
        "causal_signal_atom_input",
    }
    if set(value) != required:
        raise ValueError("V26 mini signal authority field set drifted")
    if (
        value.get("adapter_id") != V26_NUPLAN_NO_SIGNAL_ADAPTER_ID
        or value.get("source_identity_sha256") != source["source_identity_sha256"]
        or value.get("source_db_sha256") != source["source_db_sha256"]
        or value.get("map_sha256") != source["map_sha256"]
        or value.get("traffic_light_status_count") != 0
        or value.get("source_state") != "not_applicable"
        or value.get("typed_missing_atoms")
        != ["planned_red_light_cost", "red_stopping_margin_cost"]
        or value.get("red_light_endpoint_status") != "missing_or_inapplicable"
    ):
        raise ValueError("V26 mini no-signal authority drifted")
    return dict(value)


def _build_mini_scenario(
    data_root: Path,
    db_path: Path,
    *,
    maps_root: Path | None = None,
    scenario_token: str | None = None,
) -> tuple[Any, Any, Any]:
    """Use the official ScenarioBuilder and direct official simulation components."""

    from nuplan.planning.scenario_builder.nuplan_db.nuplan_scenario_builder import (
        NuPlanScenarioBuilder,
    )
    from nuplan.planning.scenario_builder.scenario_filter import ScenarioFilter
    from nuplan.planning.simulation.controller.perfect_tracking import PerfectTrackingController
    from nuplan.planning.simulation.observation.tracks_observation import TracksObservation
    from nuplan.planning.simulation.simulation import Simulation
    from nuplan.planning.simulation.simulation_setup import SimulationSetup
    from nuplan.planning.simulation.simulation_time_controller.step_simulation_time_controller import (
        StepSimulationTimeController,
    )
    from nuplan.planning.utils.multithreading.worker_parallel import (
        SingleMachineParallelExecutor,
    )

    builder = NuPlanScenarioBuilder(
        data_root=str(data_root),
        map_root=str(maps_root if maps_root is not None else data_root / "maps"),
        sensor_root=str(data_root),
        db_files=[str(db_path)],
        map_version="nuplan-maps-v1.0",
        include_cameras=False,
        max_workers=1,
        verbose=False,
    )
    scenario_filter = ScenarioFilter(
        scenario_types=None,
        scenario_tokens=None if scenario_token is None else [scenario_token],
        log_names=None,
        map_names=None,
        num_scenarios_per_type=None,
        limit_total_scenarios=1,
        timestamp_threshold_s=None,
        ego_displacement_minimum_m=None,
        expand_scenarios=False,
        remove_invalid_goals=True,
        shuffle=False,
    )
    scenarios = builder.get_scenarios(
        scenario_filter,
        SingleMachineParallelExecutor(use_process_pool=False, max_workers=1),
    )
    if len(scenarios) != 1:
        raise ValueError("official ScenarioBuilder did not return one deterministic scenario")
    scenario = scenarios[0]
    if scenario_token is not None and str(getattr(scenario, "token", "")).lower() != scenario_token.lower():
        raise ValueError("official ScenarioBuilder source scenario token drifted")
    simulation = Simulation(
        SimulationSetup(
            time_controller=StepSimulationTimeController(scenario),
            observations=TracksObservation(scenario),
            ego_controller=PerfectTrackingController(scenario),
            scenario=scenario,
        ),
        callback=None,
        simulation_history_buffer_duration=3.0,
    )
    initialization = simulation.initialize()
    return scenario, initialization, simulation.get_planner_input()


def _source_identity(
    *,
    data_root: Path,
    db_path: Path,
    scenario: Any,
    initialization: Any,
    maps_root: Path | None = None,
    expected_source: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], Path, dict[str, str]]:
    token = str(getattr(scenario, "token"))
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as db:
        log = db.execute(
            "SELECT lower(hex(token)), location, map_version FROM log"
        ).fetchone()
        scene = db.execute(
            "SELECT lower(hex(scene_token)) FROM lidar_pc WHERE lower(hex(token))=?",
            (token.lower(),),
        ).fetchone()
        source_route = (
            None
            if scene is None
            else db.execute(
                "SELECT roadblock_ids FROM scene WHERE lower(hex(token))=?",
                (str(scene[0]).lower(),),
            ).fetchone()
        )
    if log is None or scene is None or source_route is None:
        raise ValueError("official mini source identity is incomplete")
    log_token, location, map_version = map(str, log)
    map_path = _map_path(data_root, location, map_version, maps_root=maps_root)
    source_route_identity = _source_route_identity(
        location=location,
        map_version=map_version,
        roadblock_chain=str(source_route[0] or ""),
    )
    runtime_route = tuple(str(value) for value in initialization.route_roadblock_ids)
    if not runtime_route:
        raise ValueError("official mini scenario has no runtime route")
    runtime_route_sha256 = hashlib.sha256(
        "\0".join(runtime_route).encode("utf-8")
    ).hexdigest()
    db_sha = _sha256_file(db_path)
    map_sha = _sha256_file(map_path)
    derived = {
        "record_id": f"mini:{log_token}:{token}",
        "official_split": "mini",
        "log_token": log_token,
        "scenario_token": token,
        "scene_token": str(scene[0]),
        "state_token": token,
        **source_route_identity,
        "city": _CITY_BY_MAP.get(location, location),
        "map_family": location,
        "source_db_sha256": db_sha,
        "map_sha256": map_sha,
        "event_strata": [
            f"scenario_type:{str(getattr(scenario, 'scenario_type', 'unknown'))}"
        ],
    }
    runtime_assets = {
        "runtime_source_db_sha256": db_sha,
        "runtime_map_sha256": map_sha,
        "runtime_map_relative_path": str(
            map_path.relative_to(maps_root if maps_root is not None else data_root / "maps")
        ),
        "source_route_roadblock_chain_sha256": source_route_identity[
            "mission_route_roadblock_chain_sha256"
        ],
        "runtime_route_roadblock_chain_sha256": runtime_route_sha256,
    }
    if expected_source is None:
        return validate_v26_nuplan_source_record(derived), map_path, runtime_assets
    expected = validate_v26_nuplan_source_record(expected_source)
    derived["official_split"] = expected["official_split"]
    expected_fields = (
        "official_split",
        "log_token",
        "scenario_token",
        "scene_token",
        "state_token",
        "mission_route_roadblock_chain_sha256",
        "corridor_id",
        "geometry_clone_group_sha256",
        "city",
        "map_family",
    )
    for field in expected_fields:
        if expected[field] != derived[field]:
            raise ValueError(f"official source manifest binding drifted for {field}")
    return expected, map_path, runtime_assets


def _manifest_source_record(args: argparse.Namespace) -> tuple[dict[str, Any] | None, str | None]:
    """Read one identity-only selected record from a frozen source manifest."""

    if args.source_manifest is None and args.source_record_id is None:
        return None, None
    if args.source_manifest is None or args.source_record_id is None:
        raise ValueError("official source manifest and source record id must be supplied together")
    manifest_path = args.source_manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("records") if isinstance(manifest, Mapping) else None
    if not isinstance(records, list):
        raise ValueError("official source manifest records are missing")
    matching = [
        record
        for record in records
        if isinstance(record, Mapping) and record.get("record_id") == args.source_record_id
    ]
    if len(matching) != 1:
        raise ValueError("official source record id does not select exactly one source record")
    selected = dict(matching[0])
    validate_v26_nuplan_source_record(selected)
    return selected, _sha256_file(manifest_path)


def run_adapter(args: argparse.Namespace) -> dict[str, Any]:
    data_root = args.data_root.resolve(strict=True)
    db_path = args.db_file.resolve(strict=True)
    maps_root = (
        args.maps_root.resolve(strict=True)
        if args.maps_root is not None
        else data_root / "maps"
    )
    output_root = args.output_root.resolve(strict=False)
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(output_root)
    output_root.mkdir(parents=True)
    try:
        _write_json_atomic(output_root / "run.status.json", _status("running", "scenario_builder"))
        expected_source, source_manifest_sha256 = _manifest_source_record(args)
        scenario_token = (
            str(expected_source["scenario_token"]) if expected_source is not None else None
        )
        scenario, initialization, current_input = _build_mini_scenario(
            data_root,
            db_path,
            maps_root=maps_root,
            scenario_token=scenario_token,
        )
        source, map_path, runtime_assets = _source_identity(
            data_root=data_root,
            db_path=db_path,
            scenario=scenario,
            initialization=initialization,
            maps_root=maps_root,
            expected_source=expected_source,
        )
        materialized = materialize_v26_nuplan_planner_input(
            current_input, initialization, source_identity=source
        )
        arrays = {key: np.asarray(value) for key, value in materialized["dp_input"].items()}
        errors = validate_causal_dp_input(arrays)
        if errors:
            raise ValueError("V26 mini adapter causal input invalid: " + "; ".join(errors))
        signal_authority = _build_v26_no_signal_authority(
            source=source,
            route_lanes=arrays["route_lanes"],
            traffic_light_data=getattr(current_input, "traffic_light_data", None),
            decision_time_s=_decision_time_s(current_input),
        )
        npz_path = output_root / "causal_input.npz"
        _write_npz_atomic(npz_path, arrays)
        receipt = {
            "schema": SCHEMA,
            "evidence_role": EVIDENCE_ROLE,
            "stage": "official_mini_scenario_builder_v26_adapter",
            "scenario_builder_id": "NuPlanScenarioBuilder",
            "adapter_id": NUPLAN_V26_ADAPTER_ID,
            "source_identity": source,
            "source_db_path": str(db_path),
            "map_path": str(map_path),
            "source_manifest_binding": (
                None
                if source_manifest_sha256 is None
                else {
                    "source_manifest_sha256": source_manifest_sha256,
                    "source_record_id": source["record_id"],
                    "partition": expected_source.get("academic_partition"),
                }
            ),
            "runtime_asset_identity": runtime_assets,
            "route_roadblock_count": len(initialization.route_roadblock_ids),
            "causal_input_sha256": _sha256_arrays(arrays),
            "causal_input_relative_path": npz_path.name,
            "endpoint_applicability": dict(materialized["endpoint_applicability"]),
            "signal_authority": signal_authority,
            "outcome_fields_consumed": [],
            **ZERO_CALLS,
        }
        _write_json_atomic(output_root / "adapter_receipt.json", receipt)
        _write_json_atomic(output_root / "run.status.json", _status("complete", "adapter_ready"))
        _write_json_atomic(
            output_root / "run.exit",
            {"schema": SCHEMA, "terminal_status": "adapter_ready", **ZERO_CALLS},
        )
        return receipt
    except Exception as error:
        _write_json_atomic(output_root / "run.status.json", _status("typed_failure", type(error).__name__))
        _write_json_atomic(
            output_root / "run.exit",
            {"schema": SCHEMA, "terminal_status": "typed_failure", "reason": type(error).__name__, **ZERO_CALLS},
        )
        raise


def _load_fixed_dp_context(dp_repo: Path, checkpoint: Path, args_json: Path) -> dict[str, Any]:
    if not dp_repo.is_dir() or not checkpoint.is_file() or not args_json.is_file():
        raise FileNotFoundError("fixed-DP source/checkpoint/args binding is missing")
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dp_repo, text=True).strip() != FIXED_DP_HEAD:
        raise ValueError("fixed-DP head drifted")
    sys.path[:0] = [str(dp_repo), str(dp_repo / "diffusion_planner")]
    import torch
    from diffusion_planner.model.diffusion_planner import Diffusion_Planner
    from diffusion_planner.train_epoch import heading_to_cos_sin
    from diffusion_planner.utils.config import Config
    from rlvr.closed_loop.batched_rollout import make_initial_latent

    if not torch.cuda.is_available():
        raise RuntimeError("V26 mini B8 smoke requires CUDA")
    device = torch.device("cuda")
    config = Config(str(args_json))
    model = Diffusion_Planner(config).to(device)
    payload = torch.load(checkpoint, map_location=device)
    state = payload.get("model", payload)
    model.load_state_dict({key.removeprefix("module."): value for key, value in state.items()}, strict=False)
    model.eval()
    return {
        "torch": torch,
        "device": device,
        "config": config,
        "model": model,
        "heading_to_cos_sin": heading_to_cos_sin,
        "make_initial_latent": make_initial_latent,
    }


def _normalized_single_input(
    causal_input: Mapping[str, np.ndarray], context: Mapping[str, Any]
) -> dict[str, Any]:
    torch = context["torch"]
    device = context["device"]
    config = context["config"]
    arrays = {key: np.asarray(value) for key, value in causal_input.items()}
    neighbors = arrays["neighbor_agents_past"]
    limit = int(config.predicted_neighbor_num)
    if neighbors.shape[0] > limit:
        raise ValueError("causal mini source exceeds fixed-DP neighbor capacity")
    padded = np.zeros((limit, *neighbors.shape[1:]), dtype=neighbors.dtype)
    padded[: neighbors.shape[0]] = neighbors
    arrays["neighbor_agents_past"] = padded
    tensors = {key: torch.as_tensor(value).unsqueeze(0).to(device) for key, value in arrays.items()}
    tensors["ego_agent_past"] = context["heading_to_cos_sin"](tensors["ego_agent_past"])
    tensors["goal_pose"] = context["heading_to_cos_sin"](tensors["goal_pose"])
    normalized = dict(config.observation_normalizer(tensors))
    normalized["delay"] = torch.zeros(
        normalized["ego_current_state"].shape[0], dtype=torch.float32, device=device
    )
    normalized["sampled_trajectories"] = context["make_initial_latent"](
        1,
        1 + int(config.predicted_neighbor_num),
        int(config.future_len),
        device,
        1.0,
    )
    return normalized


class _CapturingModel:
    def __init__(self, model: Any) -> None:
        self._model = model
        self.calls = 0
        self.full_prediction: np.ndarray | None = None

    def __call__(self, inputs: Mapping[str, Any]) -> Any:
        self.calls += 1
        result = self._model(inputs)
        outputs = result[1] if isinstance(result, tuple) and len(result) == 2 else result
        self.full_prediction = np.ascontiguousarray(
            outputs["prediction"].detach().cpu().numpy(), dtype=np.float32
        )
        return result


def _planned_red_cost(candidates: np.ndarray, causal_input: Mapping[str, np.ndarray]) -> np.ndarray:
    import torch
    from rlvr.reward import RewardConfig, compute_red_light_score_batch

    with torch.no_grad():
        scores = compute_red_light_score_batch(
            torch.from_numpy(np.asarray(candidates)).float(),
            {"route_lanes": torch.from_numpy(np.asarray(causal_input["route_lanes"])).float()},
            RewardConfig(dt=0.1),
        )
    costs = np.maximum(-scores.detach().cpu().numpy().astype(np.float64).reshape(-1), 0.0)
    if costs.shape != (8,) or not np.isfinite(costs).all():
        raise ValueError("fixed-DP planned red-light cost must be finite [8]")
    return costs


def _select(scores: np.ndarray, mask: np.ndarray, rows: Sequence[str]) -> dict[str, Any]:
    values = np.asarray(scores, dtype=np.float64).reshape(-1)
    eligible = np.asarray(mask, dtype=bool).reshape(-1)
    if values.shape != (8,) or eligible.shape != (8,):
        raise ValueError("selector score or eligibility shape drifted")
    ordered = sorted((float(values[index]), int(index)) for index in np.flatnonzero(eligible))
    if not ordered:
        raise ValueError("selector has no eligible same-pool candidate")
    best_score, selected = ordered[0]
    ties = [index for score, index in ordered if score == best_score]
    return {
        "status": "ok",
        "selected_index": selected,
        "selected_row_sha256": str(rows[selected]),
        "candidate_pool_sha256": None,
        "mask_count": int(eligible.sum()),
        "margin": None if len(ordered) < 2 else float(ordered[1][0] - best_score),
        "tie_indices": ties,
    }


def _score_applicable_atoms(
    atom_matrix: np.ndarray,
    atom_scales: np.ndarray,
    weights: np.ndarray,
    atom_applicable_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Score only source-applicable atom entries without altering weights."""

    matrix = np.asarray(atom_matrix, dtype=np.float64)
    applicable = np.asarray(atom_applicable_mask)
    if matrix.shape != (8, 14) or applicable.dtype != np.bool_ or applicable.shape != (8, 14):
        raise ValueError("V26 atom applicability mask must be strict bool [8,14]")
    if np.any(np.abs(matrix[~applicable]) > 1e-12):
        raise ValueError("inapplicable V26 atom values must be exact legal zero")
    return canonical_score_atoms(
        np.where(applicable, matrix, 0.0),
        atom_scales,
        weights,
        simplex_nonnegative_atol=1e-9,
    )


def _atom_applicability_receipt(
    atoms: Mapping[str, Any], signal_authority: Mapping[str, Any]
) -> dict[str, Any]:
    source = np.asarray(atoms["atom_source_valid_mask"])
    applicable = np.asarray(atoms["atom_applicable_mask"])
    if source.dtype != np.bool_ or applicable.dtype != np.bool_ or source.shape != (8, 14) or applicable.shape != (8, 14):
        raise ValueError("V26 atom source/applicability masks drifted")
    if np.any(applicable & ~source):
        raise ValueError("V26 atom applicability exceeds source validity")
    active = applicable.all(axis=0)
    typed_missing = [
        name for index, name in enumerate(DP_CAMP_ATOM_NAMES_V10) if not active[index]
    ]
    route_speed_source = np.asarray(atoms["route_speed_source_eligible_mask"])
    if route_speed_source.dtype != np.bool_ or route_speed_source.shape != (8,):
        raise ValueError("V26 route-speed source mask drifted")
    speed_missing = (
        []
        if route_speed_source.all()
        else list(DP_CAMP_ATOM_NAMES_V10[4:7])
    )
    expected_missing = speed_missing + list(signal_authority["typed_missing_atoms"])
    if typed_missing != expected_missing:
        raise ValueError("V26 source applicability and typed-missing atoms disagree")
    return {
        "atom_names": list(DP_CAMP_ATOM_NAMES_V10),
        "availability": dict(atoms["availability"]),
        "atom_source_valid_mask": source.tolist(),
        "atom_applicable_mask": applicable.tolist(),
        "scoring_active_atom_indices": np.flatnonzero(active).astype(int).tolist(),
        "typed_missing_atoms": typed_missing,
        "speed_limit_endpoint_status": (
            "available" if not speed_missing else "missing_or_inapplicable"
        ),
        "red_light_endpoint_status": signal_authority["red_light_endpoint_status"],
    }


def _selector_assets(
    root: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, CAMPContextScaler, dict[str, str]]:
    receipt_path = root / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("weight_roles", {}).get("adapted") != "camp_dp_v26_adapted_selector_weights_v1":
        raise ValueError("V26 adapted selector weight role drifted")
    assets = receipt.get("adapted_assets", {})
    parameters = root / str(assets.get("parameters", {}).get("relative_path", ""))
    scales = root / str(assets.get("runtime_atom_scales", {}).get("relative_path", ""))
    for path, label in ((parameters, "parameters"), (scales, "runtime scales")):
        expected = str(assets.get("parameters" if label == "parameters" else "runtime_atom_scales", {}).get("sha256", ""))
        if not path.is_file() or _sha256_file(path) != expected:
            raise ValueError(f"adapted selector {label} asset drifted")
    with np.load(parameters, allow_pickle=False) as archive:
        static = np.asarray(archive["static14d_runtime_weights"], dtype=np.float64)
        scene_theta = np.asarray(archive["scene14d_theta"], dtype=np.float64)
        scaler = CAMPContextScaler(
            np.asarray(archive["context_q05"], dtype=np.float64),
            np.asarray(archive["context_q95"], dtype=np.float64),
        )
    scale_payload = json.loads(scales.read_text(encoding="utf-8"))
    atom_scales = np.asarray(scale_payload.get("scales"), dtype=np.float64)
    if static.shape != (14,) or scene_theta.shape != (14, 53) or atom_scales.shape != (14,):
        raise ValueError("adapted Static14D/Scene14D asset shape drifted")
    return static, scene_theta, atom_scales, scaler, {
        "parameters_sha256": _sha256_file(parameters),
        "runtime_scales_sha256": _sha256_file(scales),
        "weight_role": str(receipt["weight_roles"]["adapted"]),
    }


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.resolve(strict=False)
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError(output_root)
    output_root.mkdir(parents=True)
    model_calls = 0
    capture: _CapturingModel | None = None
    try:
        _write_json_atomic(output_root / "run.status.json", _status("running", "fixed_dp_initialization"))
        adapter_root = args.adapter_root.resolve(strict=True)
        adapter_receipt = json.loads((adapter_root / "adapter_receipt.json").read_text(encoding="utf-8"))
        if adapter_receipt.get("adapter_id") != NUPLAN_V26_ADAPTER_ID:
            raise ValueError("V26 mini adapter receipt drifted")
        source = validate_v26_nuplan_source_record(adapter_receipt.get("source_identity", {}))
        signal_authority = _require_v26_no_signal_authority(
            adapter_receipt.get("signal_authority", {}), source=source
        )
        with np.load(adapter_root / "causal_input.npz", allow_pickle=False) as archive:
            causal_input = {key: np.asarray(archive[key]) for key in archive.files}
        errors = validate_causal_dp_input(causal_input)
        if errors:
            raise ValueError("serialized V26 mini causal input invalid: " + "; ".join(errors))
        dp_repo = args.fixed_dp_repo.resolve(strict=True)
        checkpoint = args.checkpoint.resolve(strict=True)
        args_json = args.args_json.resolve(strict=True)
        if _sha256_file(checkpoint) != args.checkpoint_sha256 or _sha256_file(args_json) != args.args_sha256:
            raise ValueError("fixed-DP checkpoint or args identity drifted")
        if args.fixed_dp_head != FIXED_DP_HEAD:
            raise ValueError("fixed-DP scientific head drifted")
        context = _load_fixed_dp_context(dp_repo, checkpoint, args_json)
        normalized = _normalized_single_input(causal_input, context)
        capture = _CapturingModel(context["model"])
        decoder = context["model"].decoder
        prior_guidance_fn, prior_guidance_scale = decoder._guidance_fn, decoder._guidance_scale
        decoder._guidance_fn, decoder._guidance_scale = None, 0.5
        try:
            pool = run_v26_nuplan_single_invocation_b8(
                model=capture,
                normalized_single_input=normalized,
                route_identity_sha256=str(source["mission_route_roadblock_chain_sha256"]),
                tick_index=0,
                root_seed=int(args.seed),
                torch_module=context["torch"],
            )
        finally:
            decoder._guidance_fn, decoder._guidance_scale = prior_guidance_fn, prior_guidance_scale
        model_calls = capture.calls
        if capture.calls != 1 or capture.full_prediction is None:
            raise ValueError("V26 mini smoke did not make exactly one fixed-DP forward")
        candidates = np.asarray(pool["candidate_tensor"], dtype=np.float32)
        neighbor_valid = np.any(
            np.abs(np.asarray(causal_input["neighbor_agents_past"])) > 1e-8,
            axis=tuple(range(1, np.asarray(causal_input["neighbor_agents_past"]).ndim)),
        )
        phase_receipt: dict[str, Any] = {}
        planned_red_light_cost = (
            np.zeros(8, dtype=np.float64)
            if signal_authority["source_state"] == "not_applicable"
            else _planned_red_cost(candidates, causal_input)
        )
        capabilities = v26_source_capabilities(
            speed_limit_status="typed_missing",
            signal_authority=signal_authority,
        )
        atoms = materialize_v26_camp_atoms(
            candidates=candidates,
            causal_input=causal_input,
            neighbor_predictions=np.asarray(capture.full_prediction[:, 1:33]),
            neighbor_valid_mask=neighbor_valid,
            signal_mask=np.ones(8, dtype=bool),
            planned_red_light_cost=planned_red_light_cost,
            signal_authority=signal_authority,
            capabilities=capabilities,
            dt=0.1,
            phase_receipt=phase_receipt,
        )
        if atoms.get("atom_matrix") is None:
            raise ValueError(f"V26 mini selector atom materialization unavailable: {atoms.get('exclusion_reason')}")
        static, scene_theta, atom_scales, scaler, asset_hashes = _selector_assets(
            args.selector_root.resolve(strict=True)
        )
        atom_matrix = np.asarray(atoms["atom_matrix"], dtype=np.float64)
        eligible = np.asarray(atoms["physical_feasible_mask"], dtype=bool)
        atom_applicability = _atom_applicability_receipt(atoms, signal_authority)
        atom_applicable_mask = np.asarray(atoms["atom_applicable_mask"], dtype=bool)
        rows = [str(value) for value in pool["candidate_row_sha256"]]
        _, static_scores = _score_applicable_atoms(
            atom_matrix,
            atom_scales,
            static,
            atom_applicable_mask,
        )
        context_record = build_v26_camp_raw_context(
            causal_input=causal_input,
            candidates=candidates,
            source_valid_mask=np.asarray(atoms["source_valid_mask"], dtype=bool),
            signal_authority=signal_authority,
            capabilities=capabilities,
        )
        scene_weights = context_weights(
            scene_theta,
            scaler.lift(
                context_record.raw,
                source_complete=np.asarray(context_record.source_complete, dtype=bool),
            ),
        )
        _, scene_scores = _score_applicable_atoms(
            atom_matrix,
            atom_scales,
            scene_weights,
            atom_applicable_mask,
        )
        selector_receipts = {
            "candidate0": {
                "status": "ok",
                "selected_index": 0,
                "selected_row_sha256": rows[0],
                "candidate_pool_sha256": pool["candidate_tensor_sha256_before"],
                "mask_count": 8,
                "margin": None,
                "tie_indices": [0],
            },
            "Static14D": {**_select(static_scores, eligible, rows), "candidate_pool_sha256": pool["candidate_tensor_sha256_before"]},
            "Scene14D": {**_select(scene_scores, eligible, rows), "candidate_pool_sha256": pool["candidate_tensor_sha256_before"]},
        }
        bound = bind_v26_nuplan_same_pool_selectors(pool, selector_receipts)
        receipt = {
            "schema": SCHEMA,
            "evidence_role": EVIDENCE_ROLE,
            "runner_id": NUPLAN_V26_RUNNER_ID,
            "adapter_id": NUPLAN_V26_ADAPTER_ID,
            "fixed_dp": {
                "head": args.fixed_dp_head,
                "checkpoint_sha256": args.checkpoint_sha256,
                "args_sha256": args.args_sha256,
                "guidance_policy": "disabled",
            },
            "source": {
                "adapter_receipt_sha256": _sha256_file(adapter_root / "adapter_receipt.json"),
                "identity": source,
                "endpoint_applicability": dict(adapter_receipt["endpoint_applicability"]),
                "signal_authority": signal_authority,
            },
            "selector_assets": asset_hashes,
            "pool": {
                "shape": list(candidates.shape),
                "dtype": str(candidates.dtype),
                "finite": bool(np.isfinite(candidates).all()),
                "candidate0_row": 0,
                "candidate0_default_identity": dict(pool["candidate0"]),
                "row_sha256": rows,
                "latent_shape": list(pool["latent_shape"]),
                "latent_row_sha256": list(pool["latent_row_sha256"]),
                "latent_unique": len(set(pool["latent_row_sha256"])) == 8,
            },
            "forward_topology": {
                "model_calls": capture.calls,
                "dp_calls": capture.calls,
                "primary_forward_count": int(pool["primary_forward_count"]),
                "sequential_forward_count": int(pool["sequential_forward_count"]),
                **bound["post_pool_call_counts"],
            },
            "selectors": bound["selector_receipts"],
            "atom_phase_receipt": phase_receipt,
            "atom_applicability": atom_applicability,
            "simulator": {"status": "not_invoked_open_loop_smoke"},
            "endpoint_capture": {"status": "applicability_only_no_endpoint_values"},
            "outcome_fields_consumed": [],
            "denominator": {"planned": 1, "complete": 1, "typed_failure": 0, "unattempted": 0},
            "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
        }
        _write_json_atomic(output_root / "smoke_receipt.json", receipt)
        _write_json_atomic(
            output_root / "run.status.json", _completed_smoke_status(capture.calls)
        )
        _write_json_atomic(output_root / "run.exit", {"schema": SCHEMA, "terminal_status": "complete", "model_calls": capture.calls, "dp_calls": capture.calls, "gpu_calls": 1})
        return receipt
    except Exception as error:
        observed_calls = model_calls if capture is None else capture.calls
        _write_json_atomic(
            output_root / "run.status.json",
            _status(
                "typed_failure",
                type(error).__name__,
                model_calls=observed_calls,
                dp_calls=observed_calls,
                gpu_calls=int(observed_calls > 0),
            ),
        )
        _write_json_atomic(
            output_root / "run.exit",
            {
                "schema": SCHEMA,
                "terminal_status": "typed_failure",
                "reason": type(error).__name__,
                "model_calls": observed_calls,
                "dp_calls": observed_calls,
                "gpu_calls": int(observed_calls > 0),
            },
        )
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("adapter", "smoke"), required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--maps-root", type=Path)
    parser.add_argument("--db-file", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--source-record-id")
    parser.add_argument("--adapter-root", type=Path)
    parser.add_argument("--fixed-dp-repo", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--checkpoint-sha256")
    parser.add_argument("--args-json", type=Path)
    parser.add_argument("--args-sha256")
    parser.add_argument("--fixed-dp-head")
    parser.add_argument("--selector-root", type=Path)
    parser.add_argument("--seed", type=int, default=3407)
    args = parser.parse_args(argv)
    required = (
        ("data_root", "db_file")
        if args.mode == "adapter"
        else (
            "adapter_root",
            "fixed_dp_repo",
            "checkpoint",
            "checkpoint_sha256",
            "args_json",
            "args_sha256",
            "fixed_dp_head",
            "selector_root",
        )
    )
    for field in required:
        if getattr(args, field) is None:
            parser.error(f"--{field.replace('_', '-')} is required for {args.mode}")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_adapter(args) if args.mode == "adapter" else run_smoke(args)
    print(json.dumps({"terminal": result.get("terminal", {"status": "adapter_ready"}), "output_root": str(args.output_root)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
