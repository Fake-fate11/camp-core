from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import (
    paired_run_key,
)
from camp_core.integrations.nuplan_closed_loop_evidence import (
    materialize_closed_loop_evidence,
)


SMOKE_SCHEMA_VERSION = "dp_camp_v19_closed_loop_smoke_config_v1"
SAFETY_COST_PROTOCOL_SHA256 = (
    "5a3f6cd77bb5ff34e002321b1dbd201d2a4fd56af058fa57f7d6b8d06dffe9d3"
)
SAFETY_COST_COMPONENTS = (
    "collision",
    "near_miss",
    "lane_violation",
    "realized_red_light",
    "planned_red_light",
    "mean_jerk",
    "mean_lateral_acceleration",
    "route_completion",
    "route_shortfall",
)
_SAFETY_FIELDS = (
    "obb_collision_rate",
    "near_miss_rate",
    "lane_violation_rate",
    "red_light_violation_rate",
    "planned_red_light_violation_rate",
    "mean_jerk_magnitude_mps3",
    "mean_lateral_acceleration_mps2",
    "route_completion_rate",
)
_FORMAL_SEEDS = frozenset({11, 12, 13})
_ARMS = ("dp_default", "camp")
LATENCY_FIELDS = (
    "causal_conversion",
    "bridge_write",
    "dp_inference",
    "atom_selector",
    "bridge_read",
    "total_planning_path",
)


def validate_smoke_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the frozen two-scenario, existing-data smoke contract."""
    value = dict(config)
    if value.get("schema_version") != SMOKE_SCHEMA_VERSION:
        raise ValueError("smoke config schema mismatch")
    if value.get("simulation_mode") != "closed_loop_nonreactive_agents":
        raise ValueError("only closed_loop_nonreactive_agents is allowed")
    if value.get("source_scope") != "existing_nuplan_mini":
        raise ValueError("smoke must use existing nuPlan mini data")
    if not value.get("zero_log_overlap") or not value.get("zero_scene_overlap"):
        raise ValueError("selected scenarios must have zero overlap")

    scenarios = value.get("selected_scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 2:
        raise ValueError("smoke requires exactly two selected scenarios")
    if value.get("selected_scenario_count") != 2:
        raise ValueError("selected scenario count mismatch")
    required = {
        "bucket",
        "db_path",
        "location",
        "log_token",
        "logfile",
        "scenario_token",
        "scene_token",
        "selection_sha256",
        "timestamp_us",
    }
    for scenario in scenarios:
        if not isinstance(scenario, dict) or required - set(scenario):
            raise ValueError("selected scenario record is incomplete")
        if float(scenario.get("past_span_s", 0.0)) < 3.0:
            raise ValueError("selected scenario lacks three seconds of history")
        if float(scenario.get("future_span_s", 0.0)) < 8.0:
            raise ValueError("selected scenario lacks eight seconds of rollout")
    if {str(row["bucket"]) for row in scenarios} != {"normal", "interaction"}:
        raise ValueError("smoke must contain normal and interaction buckets")
    if len({str(row["logfile"]) for row in scenarios}) != 2:
        raise ValueError("smoke scenarios must use distinct logs")
    if len({str(row["scene_token"]) for row in scenarios}) != 2:
        raise ValueError("smoke scenarios must use distinct scenes")

    seeds = value.get("seeds")
    if not isinstance(seeds, dict):
        raise ValueError("smoke seeds are missing")
    for name in ("scenario", "dp_tick_root", "bootstrap"):
        seed = int(seeds.get(name, -1))
        if seed in _FORMAL_SEEDS:
            raise ValueError(f"formal seed is forbidden: {name}")
    if seeds.get("forbidden") != [11, 12, 13]:
        raise ValueError("formal seed denylist mismatch")
    if float(value.get("simulation_history_buffer_duration_s", 0.0)) != 3.0:
        raise ValueError("history buffer duration must remain 3.0 seconds")

    primary = value.get("primary_metric")
    if (
        not isinstance(primary, dict)
        or primary.get("name") != "SafetyCost v1"
        or primary.get("lower_is_better") is not True
        or primary.get("protocol_sha256") != SAFETY_COST_PROTOCOL_SHA256
        or tuple(primary.get("required_components", ())) != SAFETY_COST_COMPONENTS
    ):
        raise ValueError("SafetyCost v1 contract mismatch")
    arms = value.get("arms")
    if not isinstance(arms, dict):
        raise ValueError("paired arms are missing")
    baseline = arms.get("baseline", {})
    camp = arms.get("camp", {})
    if (
        baseline.get("arm") != "dp_default"
        or baseline.get("baseline_name")
        != "DP-default deterministic/MAP baseline"
        or baseline.get("native_ranked_top1") is not False
        or baseline.get("worker_operation") != "plan_tick"
    ):
        raise ValueError("DP-default baseline provenance mismatch")
    if (
        camp.get("arm") != "camp"
        or camp.get("k") != 8
        or float(camp.get("noise_scale", -1.0)) != 1.0
        or camp.get("worker_operation") != "plan_tick"
    ):
        raise ValueError("CAMP fixed-candidate arm mismatch")
    return value


def build_paired_run_plan(
    config: Mapping[str, Any], output_root: str | Path
) -> list[dict[str, Any]]:
    frozen = validate_smoke_config(config)
    root = Path(output_root)
    scenario_seed = int(frozen["seeds"]["scenario"])
    rows: list[dict[str, Any]] = []
    for scenario in frozen["selected_scenarios"]:
        pair_key = paired_run_key(
            str(scenario["logfile"]), str(scenario["scenario_token"]), scenario_seed
        )
        pair_root = root / pair_key
        for arm in _ARMS:
            rows.append(
                {
                    **scenario,
                    "arm": arm,
                    "pair_run_key": pair_key,
                    "pair_root": str(pair_root),
                    "arm_root": str(pair_root / arm),
                    "scenario_seed": scenario_seed,
                }
            )
    return rows


def compute_safety_cost_v1(components: Mapping[str, Any]) -> float:
    missing = set(_SAFETY_FIELDS) - set(components)
    if missing:
        raise ValueError(f"missing SafetyCost components: {sorted(missing)}")
    values = {name: float(components[name]) for name in _SAFETY_FIELDS}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("SafetyCost components must be finite")

    clip01 = lambda value: min(max(value, 0.0), 1.0)
    clip10 = lambda value: min(max(value, 0.0), 10.0)
    return float(
        100.0 * clip01(values["obb_collision_rate"])
        + 10.0 * clip01(values["near_miss_rate"])
        + 20.0 * clip01(values["lane_violation_rate"])
        + 30.0 * clip01(values["red_light_violation_rate"])
        + 15.0 * clip01(values["planned_red_light_violation_rate"])
        + clip10(values["mean_jerk_magnitude_mps3"] / 10.0)
        + 2.0 * clip10(values["mean_lateral_acceleration_mps2"] / 2.0)
        + 2.0 * clip01(1.0 - values["route_completion_rate"])
    )


def construct_nuplan_scenario(
    record: Mapping[str, Any],
    *,
    data_root: str | Path,
    map_root: str | Path,
    sensor_root: str | Path | None = None,
) -> Any:
    """Construct exactly one selected scenario without Hydra."""
    from nuplan.common.actor_state.vehicle_parameters import (
        get_pacifica_parameters,
    )
    from nuplan.planning.scenario_builder.nuplan_db.nuplan_scenario import (
        NuPlanScenario,
    )
    from nuplan.planning.scenario_builder.nuplan_db.nuplan_scenario_utils import (
        ScenarioExtractionInfo,
    )

    return NuPlanScenario(
        data_root=str(data_root),
        log_file_load_path=str(record["db_path"]),
        initial_lidar_token=str(record["scenario_token"]),
        initial_lidar_timestamp=int(record["timestamp_us"]),
        scenario_type=str(record["selection_tag"]),
        map_root=str(map_root),
        map_version="nuplan-maps-v1.0",
        map_name=str(record.get("map_version", record["location"])),
        scenario_extraction_info=ScenarioExtractionInfo(
            scenario_name=str(record["selection_tag"]),
            scenario_duration=8.0,
            extraction_offset=0.0,
            subsample_ratio=1.0,
        ),
        ego_vehicle_parameters=get_pacifica_parameters(),
        sensor_root=None if sensor_root is None else str(sensor_root),
    )


def construct_simulation(scenario: Any) -> Any:
    """Build official closed-loop-nonreactive components without running them."""
    from nuplan.planning.simulation.controller.perfect_tracking import (
        PerfectTrackingController,
    )
    from nuplan.planning.simulation.observation.tracks_observation import (
        TracksObservation,
    )
    from nuplan.planning.simulation.simulation import Simulation
    from nuplan.planning.simulation.simulation_setup import SimulationSetup
    from nuplan.planning.simulation.simulation_time_controller.step_simulation_time_controller import (
        StepSimulationTimeController,
    )

    setup = SimulationSetup(
        time_controller=StepSimulationTimeController(scenario),
        observations=TracksObservation(scenario),
        ego_controller=PerfectTrackingController(scenario),
        scenario=scenario,
    )
    return Simulation(
        setup,
        callback=None,
        simulation_history_buffer_duration=3.0,
    )


def construct_runner(simulation: Any, planner: Any) -> Any:
    from nuplan.planning.simulation.runner.simulations_runner import (
        SimulationRunner,
    )

    return SimulationRunner(simulation, planner)


def execute_arm(
    *,
    arm: str,
    pair_run_key_value: str,
    arm_root: str | Path,
    scenario: Any,
    simulation: Any,
    runner: Any,
    metric_engine: Any,
    planner_name: str,
) -> dict[str, Any]:
    """Run one arm and retain its history, metrics, bridge, and result evidence."""
    if arm not in _ARMS:
        raise ValueError("unknown arm")
    root = Path(arm_root)
    if root.name != arm or root.parent.name != pair_run_key_value:
        raise ValueError("arm root does not match paired arm identity")
    root.mkdir(parents=True, exist_ok=False)

    try:
        report = runner.run()
        if not bool(getattr(report, "succeeded", False)):
            raise RuntimeError(
                f"scenario arm failed: "
                f"{getattr(report, 'error_message', 'unknown')}"
            )
        history = simulation.history
        metrics = metric_engine.compute_metric_results(history, scenario)
        history_payload = _history_payload(history)
        metric_payload = _jsonable(metrics)
        _write_json(root / "history.json", history_payload)
        _write_json(root / "official_metrics.json", metric_payload)

        receipt_paths = sorted(root.rglob("planning_receipt.json"))
        if not receipt_paths:
            raise ValueError("planning receipt evidence is missing")
        receipts = [
            json.loads(path.read_text(encoding="utf-8")) for path in receipt_paths
        ]
        components = dict(
            materialize_closed_loop_evidence(history, scenario, receipts)
        )
        latency = _mean_latency(receipts)
        cost = compute_safety_cost_v1(components)
        result = {
            "schema_version": "dp_camp_v19_closed_loop_smoke_arm_result_v1",
            "pair_run_key": pair_run_key_value,
            "arm": arm,
            "planner_name": planner_name,
            "native_ranked_top1": False,
            "runner_succeeded": True,
            "safety_cost_protocol_sha256": SAFETY_COST_PROTOCOL_SHA256,
            "safety_cost_components": components,
            "safety_cost_v1": cost,
            "latency_ms": latency,
            "bridge_root": str(root),
        }
        _write_json(root / "result.json", result)
        return result
    except Exception as error:
        _write_json(
            root / "failure.json",
            {
                "schema_version": "dp_camp_v19_closed_loop_smoke_failure_v1",
                "pair_run_key": pair_run_key_value,
                "arm": arm,
                "error_type": type(error).__name__,
                "error": str(error),
                "native_ranked_top1": False,
            },
        )
        raise


def _validate_latency(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping) or set(value) != set(LATENCY_FIELDS):
        raise ValueError("latency evidence is incomplete")
    latency = {name: float(value[name]) for name in LATENCY_FIELDS}
    if not all(math.isfinite(item) and item >= 0.0 for item in latency.values()):
        raise ValueError("latency evidence must be finite and nonnegative")
    return latency


def _mean_latency(receipts: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    values = [_validate_latency(receipt.get("latency_ms")) for receipt in receipts]
    return {
        name: float(np.mean([item[name] for item in values]))
        for name in LATENCY_FIELDS
    }


def _history_payload(history: Any) -> dict[str, Any]:
    samples = []
    for sample in getattr(history, "data", history):
        iteration = getattr(sample, "iteration", None)
        samples.append(
            {
                "iteration_index": int(getattr(iteration, "index", -1)),
                "iteration_time_us": _iteration_time_us(iteration),
                "ego_state": _jsonable(getattr(sample, "ego_state", None)),
                "trajectory": _jsonable(getattr(sample, "trajectory", None)),
                "observation": _jsonable(getattr(sample, "observation", None)),
                "traffic_light_status": _jsonable(
                    getattr(sample, "traffic_light_status", None)
                ),
            }
        )
    return {"sample_count": len(samples), "samples": samples}


def _iteration_time_us(iteration: Any) -> int | None:
    if iteration is None:
        return None
    value = getattr(iteration, "time_us", None)
    if value is None:
        value = getattr(getattr(iteration, "time_point", None), "time_us", None)
    return None if value is None else int(value)


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.name
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_jsonable(item) for item in value]
    if dataclasses.is_dataclass(value):
        return _jsonable(dataclasses.asdict(value))
    serialize = getattr(value, "serialize", None)
    if callable(serialize):
        return _jsonable(serialize())
    fields = getattr(value, "__dict__", None)
    if isinstance(fields, dict):
        return {
            str(key): _jsonable(item)
            for key, item in fields.items()
            if not str(key).startswith("_")
        }
    return repr(value)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = validate_smoke_config(json.loads(args.smoke_config.read_text("utf-8")))
    plan = build_paired_run_plan(config, args.output_root)
    if not args.validate_only:
        raise RuntimeError(
            "execution requires the separately frozen runtime/metric preflight"
        )
    args.output_root.mkdir(parents=True, exist_ok=False)
    _write_json(args.output_root / "paired_run_plan.json", plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
