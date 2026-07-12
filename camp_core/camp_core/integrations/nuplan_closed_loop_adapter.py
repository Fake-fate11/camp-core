from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import (
    build_request_metadata,
    read_response,
    write_request,
)
from camp_core.integrations.nuplan_causal_adapter import (
    materialize_nuplan_planner_input,
)

try:
    from nuplan.planning.simulation.observation.observation_type import (
        DetectionsTracks,
        Observation,
    )
    from nuplan.planning.simulation.planner.abstract_planner import (
        AbstractPlanner,
        PlannerInitialization,
        PlannerInput,
    )
    from nuplan.planning.simulation.planner.ml_planner.transform_utils import (
        transform_predictions_to_states,
    )
    from nuplan.planning.simulation.trajectory.abstract_trajectory import (
        AbstractTrajectory,
    )
    from nuplan.planning.simulation.trajectory.interpolated_trajectory import (
        InterpolatedTrajectory,
    )
except ModuleNotFoundError:
    AbstractPlanner = object  # type: ignore[assignment,misc]
    AbstractTrajectory = Any  # type: ignore[assignment,misc]
    DetectionsTracks = object  # type: ignore[assignment,misc]
    Observation = Any  # type: ignore[assignment,misc]
    PlannerInitialization = Any  # type: ignore[assignment,misc]
    PlannerInput = Any  # type: ignore[assignment,misc]
    InterpolatedTrajectory = None  # type: ignore[assignment]
    transform_predictions_to_states = None  # type: ignore[assignment]


def dp_trajectory_to_relative_poses(trajectory: np.ndarray) -> np.ndarray:
    values = np.asarray(trajectory)
    if values.shape != (80, 4) or values.dtype != np.float32:
        raise ValueError("DP trajectory must be float32 [80,4]")
    if not np.isfinite(values).all():
        raise ValueError("DP trajectory must be finite")
    heading_norm = np.linalg.norm(values[:, 2:4], axis=1)
    if np.any(heading_norm < 0.5):
        raise ValueError("DP trajectory heading vectors are invalid")
    return np.column_stack(
        [values[:, :2].copy(), np.arctan2(values[:, 3], values[:, 2])]
    ).astype(np.float32)


class NuPlanCAMPPlanner(AbstractPlanner):  # type: ignore[misc]
    """Official nuPlan planner shell for an isolated fixed-DP worker."""

    requires_scenario = False

    def __init__(
        self,
        *,
        arm: str,
        bridge_root: str | Path,
        worker_command: Sequence[str],
        log_name: str,
        scenario_token: str,
        camp_head: str,
        dp_head: str,
        nuplan_head: str,
        selector_hashes: tuple[str, str, str] | None = None,
        scenario_seed: int = 3411,
        dp_seed_root: int = 3412,
        worker_timeout_s: float = 120.0,
    ) -> None:
        if arm not in {"dp_default", "camp"}:
            raise ValueError("arm must be dp_default or camp")
        if not worker_command:
            raise ValueError("worker_command must not be empty")
        if arm == "camp" and selector_hashes is None:
            raise ValueError("CAMP arm requires frozen selector hashes")
        if arm == "dp_default" and selector_hashes is not None:
            raise ValueError("DP-default arm must not carry selector hashes")
        self._arm = arm
        self._bridge_root = Path(bridge_root)
        self._worker_command = tuple(str(value) for value in worker_command)
        self._log_name = log_name
        self._scenario_token = scenario_token
        self._camp_head = camp_head
        self._dp_head = dp_head
        self._nuplan_head = nuplan_head
        self._selector_hashes = selector_hashes
        self._scenario_seed = int(scenario_seed)
        self._dp_seed_root = int(dp_seed_root)
        self._worker_timeout_s = float(worker_timeout_s)
        self._initialization: Any | None = None

    def name(self) -> str:
        return (
            "DP-default deterministic/MAP baseline"
            if self._arm == "dp_default"
            else "CAMP fixed-DP K=8 selector"
        )

    def initialize(self, initialization: PlannerInitialization) -> None:
        self._initialization = initialization

    def observation_type(self) -> type[Observation]:
        return DetectionsTracks

    def compute_planner_trajectory(
        self, current_input: PlannerInput
    ) -> AbstractTrajectory:
        if self._initialization is None:
            raise RuntimeError("planner must be initialized before compute")
        if transform_predictions_to_states is None or InterpolatedTrajectory is None:
            raise RuntimeError("official nuPlan v1.2 runtime is unavailable")
        total_start = time.perf_counter_ns()
        causal_start = time.perf_counter_ns()
        materialized = materialize_nuplan_planner_input(
            current_input, self._initialization
        )
        causal_ms = (time.perf_counter_ns() - causal_start) / 1e6
        iteration = int(current_input.iteration.index)
        simulation_time_us = getattr(current_input.iteration, "time_us", None)
        if simulation_time_us is None:
            simulation_time_us = current_input.iteration.time_point.time_us
        simulation_time_us = int(simulation_time_us)
        metadata = build_request_metadata(
            arm=self._arm,
            log_name=self._log_name,
            scenario_token=self._scenario_token,
            iteration_index=iteration,
            simulation_time_us=simulation_time_us,
            scenario_seed=self._scenario_seed,
            dp_seed_root=self._dp_seed_root,
            camp_head=self._camp_head,
            dp_head=self._dp_head,
            nuplan_head=self._nuplan_head,
            causal_input=materialized.dp_input,
            selector_hashes=self._selector_hashes,
        )
        tick_dir = (
            self._bridge_root
            / str(metadata["pair_run_key"])
            / self._arm
            / f"{iteration:06d}"
        )
        receipt_path = tick_dir / "planning_receipt.json"
        if receipt_path.exists():
            raise FileExistsError("planning receipt already exists")
        write_start = time.perf_counter_ns()
        write_request(tick_dir, materialized.dp_input, metadata)
        write_ms = (time.perf_counter_ns() - write_start) / 1e6
        completed = subprocess.run(
            [*self._worker_command, "--request-dir", str(tick_dir)],
            check=False,
            timeout=self._worker_timeout_s,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"fixed-DP worker exited {completed.returncode}")
        read_start = time.perf_counter_ns()
        response = read_response(
            tick_dir,
            expected_run_key=str(metadata["run_key"]),
            expected_iteration_index=iteration,
        )
        read_ms = (time.perf_counter_ns() - read_start) / 1e6
        if response.metadata["status"] != "ok":
            raise RuntimeError(
                f"fixed-DP/CAMP planning failed: "
                f"{response.metadata.get('failure_reason', 'unknown')}"
            )
        poses = dp_trajectory_to_relative_poses(
            response.arrays["selected_trajectory"]
        )
        states = transform_predictions_to_states(
            poses,
            current_input.history.ego_states,
            8.0,
            0.1,
        )
        trajectory = InterpolatedTrajectory(states)
        worker_latency = response.metadata.get("worker_latency_ms", {})
        latency = {
            "causal_conversion": causal_ms,
            "bridge_write": write_ms,
            "dp_inference": float(worker_latency["dp_inference"]),
            "atom_selector": float(worker_latency["atom_selector"]),
            "bridge_read": read_ms,
            "total_planning_path": (time.perf_counter_ns() - total_start) / 1e6,
        }
        if latency["total_planning_path"] < max(
            value
            for name, value in latency.items()
            if name != "total_planning_path"
        ):
            raise RuntimeError("total planning-path latency is inconsistent")
        _write_receipt(
            receipt_path,
            {
                "schema_version": "dp_camp_v19_nuplan_planning_receipt_v1",
                "pair_run_key": metadata["pair_run_key"],
                "run_key": metadata["run_key"],
                "arm": self._arm,
                "iteration_index": iteration,
                "simulation_time_us": simulation_time_us,
                "causal_input_sha256": metadata["causal_input_sha256"],
                "request_json_sha256": _sha256(tick_dir / "request.json"),
                "request_npz_sha256": _sha256(tick_dir / "request.npz"),
                "response_json_sha256": _sha256(tick_dir / "response.json"),
                "response_npz_sha256": _sha256(tick_dir / "response.npz"),
                "selected_trajectory_sha256": response.metadata[
                    "selected_trajectory_sha256"
                ],
                "selected_planned_red_light_cost": response.metadata.get(
                    "selected_planned_red_light_cost"
                ),
                "planned_red_source": response.metadata.get("planned_red_source"),
                "worker_exit_code": completed.returncode,
                "latency_ms": latency,
                "native_ranked_top1": False,
            },
        )
        return trajectory


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError("planning receipt already exists")
    temporary = path.with_suffix(".json.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
