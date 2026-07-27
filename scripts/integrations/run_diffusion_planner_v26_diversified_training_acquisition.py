"""Acquire V26-only, same-ego B8 development training pools.

Stage 8b is an acquisition endpoint, not a V25 evaluation endpoint.  Every
planned route receives a fresh one-tick own-state replay, exactly one B8 model
forward, and an atomic unit receipt.  Candidate0 remains frozen row 0; all
four CAMP selectors are same-pool counterfactuals only.  No outcome, holdout,
or V25 training-row input is consumed.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v21_native import array_sha256  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_context import RAW_FEATURE_NAMES  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_scene_runtime import FIXED_DP_HEAD  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (  # noqa: E402
    build_train_only_causal_labels,
    fit_train_only_atom_scales,
    hierarchical_snapshot_weights,
)
from camp_core.integrations.diffusion_planner_v26_development_profiling import (  # noqa: E402
    ATOM_SET_BY_ARM,
    OPERATIONAL_ARM,
    PROFILE_ARMS,
)
from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (  # noqa: E402
    ROUTE_PLAN_EVIDENCE_ROLE,
    ROUTE_PLAN_SCHEMA_VERSION,
    canonical_json_sha256,
    validate_diversified_route_plan,
)
from camp_core.integrations.diffusion_planner_v26_diversified_plan_revision import (  # noqa: E402
    PLAN_REVISION_SCHEMA_VERSION,
    load_verified_revised_plan,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (  # noqa: E402
    FROZEN_SIMPLEX_TOLERANCE,
    V26_AUTOWARE_SIDECAR_SIGNAL_MODE,
    V26_CERTIFIED_NO_SIGNAL_MODE,
    V26_GENERATOR_ID,
    V26_TRAINING_ROWS_SCHEMA_VERSION,
    V26_TRAINING_SOURCE_SCHEMA_VERSION,
    build_v26_integration_boundary,
    enforce_v26_dp312_lanelet2_precedence,
    resolve_v26_signal_adapter,
    v26_generator_topology,
)
from camp_core.integrations.diffusion_planner_v26_native_runner import (  # noqa: E402
    run_v26_native_same_ego_b8_replay,
)
from camp_core.integrations.diffusion_planner_v26_source_authority import (  # noqa: E402
    build_v26_source_signal_config,
    v26_source_bound_projection,
    v26_source_projection_binding,
)
from scripts.integrations.run_diffusion_planner_v26_development_profiling import (  # noqa: E402
    _load_zero_shot_reference_selector_assets,
)


EVIDENCE_ROLE = "development_training_same_ego_b8_acquisition"
MANIFEST_SCHEMA_VERSION = "camp_dp_v26_diversified_training_acquisition_manifest_v1"
UNIT_SCHEMA_VERSION = "camp_dp_v26_diversified_training_unit_v1"
RECEIPT_SCHEMA_VERSION = "camp_dp_v26_diversified_training_acquisition_receipt_v1"
LABEL_SIDECAR_SCHEMA_VERSION = "camp_dp_v26_causal_policy_distillation_label_sidecar_v1"
MIN_FREE_BYTES = 10 * 1024**3
SCENARIO_SEED_BASE = 46001


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, encoding="utf-8"
    ).strip()


def _tracked_changes(path: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=path,
            text=True,
            encoding="utf-8",
        ).strip()
    )


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        staging.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def _json_native(value: Any) -> Any:
    """Convert numpy diagnostics to JSON-native values without changing data."""

    import numpy as np

    if isinstance(value, np.ndarray):
        return [_json_native(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_native(value.item())
    if isinstance(value, Mapping):
        return {str(key): _json_native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_native(item) for item in value]
    return value


def _atomic_write_npz(path: Path, **arrays: Any) -> None:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.stem}.", suffix=".npz", dir=path.parent, delete=False
    ) as handle:
        staging = Path(handle.name)
    try:
        np.savez_compressed(staging, **arrays)
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


@contextmanager
def _exclusive_worker_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"V26 Stage8b worker lock already exists: {path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "role": EVIDENCE_ROLE}, handle)
            handle.flush()
        yield
    finally:
        path.unlink(missing_ok=True)


def _require_file_binding(value: Any, label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "sha256"}:
        raise ValueError(f"V26 Stage8b {label} binding is required")
    path = Path(str(value["path"])).resolve()
    expected = str(value["sha256"])
    if not path.is_file() or _file_sha256(path) != expected:
        raise ValueError(f"V26 Stage8b {label} asset drifted")
    return {"path": str(path), "sha256": expected}


def _load_base_probe_config(path: Path) -> dict[str, Any]:
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    value = json.loads(source.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("V26 Stage8b base probe must be an object")
    protocol = value.get("protocol")
    fixed_dp = value.get("fixed_dp")
    spawn = value.get("spawn_config")
    seeds = value.get("seeds")
    if (
        type(protocol) is not dict
        or protocol.get("route_role") != "development_nonholdout"
        or protocol.get("holdout_access_authorized") is not False
        or type(fixed_dp) is not dict
        or fixed_dp.get("head") != FIXED_DP_HEAD
        or type(fixed_dp.get("native_source_sha256")) is not dict
        or type(spawn) is not dict
        or type(seeds) is not dict
    ):
        raise ValueError("V26 Stage8b base probe identity drifted")
    checkpoint = _require_file_binding(fixed_dp.get("checkpoint"), "checkpoint")
    args_json = _require_file_binding(fixed_dp.get("args_json"), "args")
    source_hashes = {
        str(key): str(item) for key, item in dict(fixed_dp["native_source_sha256"]).items()
    }
    if not source_hashes or any(len(item) != 64 for item in source_hashes.values()):
        raise ValueError("V26 Stage8b native fixed-DP sources are incomplete")
    return {
        "source_path": str(source),
        "source_sha256": _file_sha256(source),
        "fixed_dp": {
            "head": FIXED_DP_HEAD,
            "checkpoint": checkpoint,
            "args_json": args_json,
            "native_source_sha256": source_hashes,
        },
        "spawn_config": dict(spawn),
        "seed_template": {str(key): value for key, value in seeds.items()},
    }


def _require_pre_model_qualification(
    path: Path, *, route_plan: Mapping[str, Any], camp_head: str
) -> dict[str, Any]:
    """Require the full V26-native zero-model qualification before CUDA import."""

    receipt_path = path.resolve()
    if not receipt_path.is_file():
        raise FileNotFoundError(receipt_path)
    root = receipt_path.parent
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("V26 Stage8b pre-model qualification manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_zero = {
        "model_forward_count": 0,
        "dp_forward_count": 0,
        "gpu_invocation_count": 0,
        "latent_generation_count": 0,
        "candidate_generation_count": 0,
        "sequential_forward_count": 0,
    }
    if (
        receipt.get("schema_version")
        != "camp_dp_v26_stage8b_pre_model_qualification_receipt_v1"
        or receipt.get("evidence_role")
        != "development_training_same_ego_b8_pre_model_qualification"
        or receipt.get("status") != "passed"
        or receipt.get("route_plan_sha256") != route_plan["route_plan_sha256"]
        or receipt.get("denominator")
        != {"planned": 1786, "complete": 1786, "failed": 0, "unattempted": 0}
        or receipt.get("identity") != {"family_count": 6, "corridor_count": 155, "route_count": 1786}
        or receipt.get("zero_model_totals") != expected_zero
        or receipt.get("acquisition_authorized") is not True
        or manifest.get("camp_head") != camp_head
        or manifest.get("route_plan_sha256") != route_plan["route_plan_sha256"]
    ):
        raise ValueError("V26 Stage8b pre-model qualification is not admissible")
    qualified: dict[int, dict[str, Any]] = {}
    for index, schedule in enumerate(route_plan["routes"]):
        unit_path = root / "units" / f"{index:04d}.json"
        if not unit_path.is_file():
            raise ValueError("V26 Stage8b pre-model qualification unit is missing")
        unit = json.loads(unit_path.read_text(encoding="utf-8"))
        route = dict(unit.get("route", {}))
        if (
            unit.get("unit_index") != index
            or unit.get("terminal", {}).get("status") != "qualified"
            or route.get("route_id") != schedule["route_id"]
            or route.get("corridor_id") != schedule["corridor_id"]
            or route.get("route_identity_sha256")
            != schedule["route_record"]["identity_sha256"]
            or unit.get("forward_calls") != expected_zero
            or not isinstance(unit.get("source_projection"), dict)
            or not isinstance(unit.get("parsed_geometry"), dict)
            or not isinstance(unit.get("signal", {}).get("source_provenance"), dict)
            or unit.get("scene14d_reference", {}).get("simplex_tolerance")
            != FROZEN_SIMPLEX_TOLERANCE
        ):
            raise ValueError("V26 Stage8b pre-model qualification unit drifted")
        qualified[index] = unit
    return {
        "path": str(receipt_path),
        "sha256": _file_sha256(receipt_path),
        "manifest_sha256": _file_sha256(manifest_path),
        "status": "passed_1786_of_1786_zero_model",
        "parent_plan_sha256": route_plan["route_plan_sha256"],
        "units": qualified,
    }


def _resource_precheck(output_dir: Path, device: str, torch: Any) -> None:
    if device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("V26 Stage8b requires an available CUDA GPU")
    if shutil.disk_usage(output_dir.parent).free < MIN_FREE_BYTES:
        raise RuntimeError("V26 Stage8b requires at least 10 GiB free disk")
    probe = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if probe.returncode:
        raise RuntimeError("V26 Stage8b cannot verify GPU conflict via nvidia-smi")
    if any(line.strip() for line in probe.stdout.splitlines()):
        raise RuntimeError("V26 Stage8b GPU conflict detected before model load")


def _unit_id(*, route_plan_sha256: str, unit_index: int, route_id: str, scenario_seed: int) -> str:
    return canonical_json_sha256(
        {
            "route_plan_sha256": route_plan_sha256,
            "unit_index": int(unit_index),
            "route_id": str(route_id),
            "scenario_seed": int(scenario_seed),
            "state_topology": "fresh_own_state_one_tick_same_ego_b8",
        }
    )


def _source_ordinal(schedule: Mapping[str, Any], unit_index: int) -> int:
    """Keep the parent route identity/seed when a forward plan omits rows."""

    value = schedule.get("parent_ordinal", unit_index)
    if type(value) is not int or value < 0:
        raise ValueError("V26 Stage8b route source ordinal is invalid")
    return value


def _route_asset(route_type: Any, record: Mapping[str, Any], path: Path) -> str:
    import numpy as np

    spec = dict(record["route_spec"])
    lanelets = [int(item) for item in spec["lanelet_ids"]]
    route = route_type(
        str(spec["map_path"]),
        np.asarray(spec["start_pose"], dtype=np.float64),
        np.asarray(spec["goal_pose"], dtype=np.float64),
        int(lanelets[0]),
        int(lanelets[-1]),
        route_lanelet_ids=lanelets,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    route.save(path)
    return _file_sha256(path)


def _signal_config(
    *, schedule: Mapping[str, Any], family: Mapping[str, Any], route_sha256: str
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return build_v26_source_signal_config(
            schedule=schedule, family=family, route_sha256=route_sha256
        ), None
    except ValueError as exc:
        return None, str(exc)


def _route_probe_config(
    *,
    base: Mapping[str, Any],
    schedule: Mapping[str, Any],
    route_path: Path,
    route_sha256: str,
    scenario_seed: int,
    signal: Mapping[str, Any],
) -> dict[str, Any]:
    record = dict(schedule["route_record"])
    seeds = dict(base["seed_template"])
    seeds["scenario"] = int(scenario_seed)
    spawn = dict(base["spawn_config"])
    spawn["seed"] = int(scenario_seed)
    config = {
        "schema_version": "camp_dp_v26_diversified_training_probe_config_v1",
        "evidence_role": EVIDENCE_ROLE,
        "protocol": {
            "route_role": "development_nonholdout",
            "holdout_access_authorized": False,
            "claim_authorized": False,
            "training_evidence_only": True,
            "route_id": schedule["route_id"],
        },
        "routes": [
            {
                "name": schedule["route_id"],
                "path": str(route_path),
                "sha256": route_sha256,
            }
        ],
        "map": {
            "path": record["source_map_path"],
            "sha256": record["source_map_sha256"],
        },
        "seeds": seeds,
        "spawn_config": spawn,
        "fixed_dp": dict(base["fixed_dp"]),
        **dict(signal),
    }
    return config


def _zero_forward_calls(*, before: int = 0, after: int = 0, primary: int = 0) -> dict[str, int]:
    return {
        "model_call_count_before": int(before),
        "model_call_count_after": int(after),
        "model_call_delta": int(primary),
        "primary_forward_count": int(primary),
        "sequential_forward_count": 0,
        "post_pool_model_forward_count": 0,
        "post_pool_dp_forward_count": 0,
        "post_pool_latent_replacement_count": 0,
        "post_pool_candidate_generation_count": 0,
        "candidate_pool_mutation_count": 0,
        "trajectory_regeneration_count": 0,
    }


def _completed_unit(
    raw: Mapping[str, Any],
    callback: Any,
    *,
    unit_index: int,
    route_plan_sha256: str,
    schedule: Mapping[str, Any],
    scenario_seed: int,
) -> dict[str, Any]:
    import numpy as np

    if raw.get("status") != "ok":
        raise ValueError("V26 Stage8b completed unit requires an ok native receipt")
    rows = [str(item) for item in raw["candidate_row_sha256"]]
    if len(rows) != 8 or len(set(rows)) != 8:
        raise ValueError("V26 Stage8b completed unit requires eight unique candidate rows")
    if raw.get("candidate_tensor_sha256_before") != raw.get("candidate_tensor_sha256_after"):
        raise ValueError("V26 Stage8b candidate pool mutated after its primary forward")
    zero = dict(raw["zero_call_receipt"])
    if any(
        int(zero.get(name, -1)) != 0
        for name in (
            "dp_or_model_calls_after_pool",
            "latent_replacements_after_pool",
            "candidate_generations_after_pool",
        )
    ):
        raise ValueError("V26 Stage8b post-pool call receipt drifted")
    primary = int(raw["primary_pool_model_call_count"])
    after = int(callback.model_call_count)
    before = after - primary
    if primary != 1 or before < 0:
        raise ValueError("V26 Stage8b requires exactly one primary same-ego B8 forward")
    metadata = dict(raw["same_ego_batch_metadata"])
    if int(metadata.get("same_ego_batch_size", -1)) != 8 or metadata.get("nonlatent_rows_identical") is not True:
        raise ValueError("V26 Stage8b same-ego B8 input topology drifted")
    if int(raw["selected_index"]) != 0 or str(raw["selected_trajectory_sha256"]) != rows[0]:
        raise ValueError("V26 Stage8b simulator did not retain frozen candidate0 row0")
    summary = dict(raw["materialized_summary"])
    atoms = np.asarray(summary["atom_matrix"], dtype=np.float64)
    atom_source = np.asarray(summary["atom_source_valid_mask"], dtype=np.bool_)
    atom_applicable = np.asarray(summary["atom_applicable_mask"], dtype=np.bool_)
    source_valid = np.asarray(summary["source_valid_mask"], dtype=np.bool_)
    physical = np.asarray(summary["physical_feasible_mask"], dtype=np.bool_)
    if (
        atoms.shape != (8, 14)
        or atom_source.shape != (8, 14)
        or atom_applicable.shape != (8, 14)
        or source_valid.shape != (8,)
        or physical.shape != (8,)
        or not np.all(np.isfinite(atoms))
        or np.any(atoms < 0.0)
        or np.any(atom_applicable & ~atom_source)
        or not np.array_equal(source_valid, np.all(atom_source, axis=1))
        or np.any(physical & ~source_valid)
        or not np.any(source_valid)
    ):
        raise ValueError("V26 Stage8b causal training-pool masks drifted")
    context = dict(summary["context"])
    raw_context = dict(context["raw_context"])
    source_complete = dict(context["source_complete"])
    if set(raw_context) != set(RAW_FEATURE_NAMES) or set(source_complete) != set(RAW_FEATURE_NAMES):
        raise ValueError("V26 Stage8b raw context receipt drifted")
    arms = dict(raw["real_selector_receipts"])
    if tuple(arms) != PROFILE_ARMS:
        raise ValueError("V26 Stage8b five-arm selector inventory drifted")
    selected_arms: dict[str, dict[str, Any]] = {}
    for arm_id, arm in arms.items():
        item = dict(arm)
        selected = item.get("selected_index")
        selected_row = item.get("selected_row_sha256")
        if arm_id == OPERATIONAL_ARM:
            if selected != 0 or selected_row != rows[0]:
                raise ValueError("V26 Stage8b candidate0 selector identity drifted")
        elif item.get("status") == "ok":
            if type(selected) is not int or not 0 <= selected < 8 or selected_row != rows[selected]:
                raise ValueError("V26 Stage8b selector selected-row binding drifted")
        selected_arms[arm_id] = {
            "atom_set": ATOM_SET_BY_ARM[arm_id],
            "status": item.get("status"),
            "failure_reason": item.get("failure_reason"),
            "selected_index": selected,
            "selected_row_sha256": selected_row,
            "source_valid_mask": item.get("source_valid_mask"),
            "physical_feasible_mask": item.get("physical_feasible_mask"),
            "margin_best_vs_runner_up": item.get("margin_best_vs_runner_up"),
            "exact_tie_set": item.get("exact_tie_set"),
        }
    record = dict(schedule["route_record"])
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "unit_index": int(unit_index),
        "planned_unit_id_sha256": _unit_id(
            route_plan_sha256=route_plan_sha256,
            unit_index=unit_index,
            route_id=str(schedule["route_id"]),
            scenario_seed=scenario_seed,
        ),
        "route": {
            "family_id": schedule["family_id"],
            "route_id": schedule["route_id"],
            "corridor_id": schedule["corridor_id"],
            "revised_plan_ordinal": int(schedule.get("revised_plan_ordinal", unit_index)),
            "parent_ordinal": _source_ordinal(schedule, unit_index),
            "route_identity_sha256": record["identity_sha256"],
            "map_sha256": record["source_map_sha256"],
            "source_artifact_sha256": schedule["source_artifact_sha256"],
            "event_manifest_sha256": schedule["event_manifest_sha256"],
            "scenario_seed": int(scenario_seed),
            "source_stratum": dict(record["source_stratum"]),
        },
        "input": {
            "state_sha256": str(raw["state_sha256"]),
            "source_input_sha256": str(raw["source_input_sha256"]),
            "expanded_input_sha256": str(raw["input_sha256"]),
            "same_ego_batch_size": 8,
            "nonlatent_rows_identical": True,
            "tensor_metadata": dict(metadata["tensor_metadata"]),
        },
        "latent": {
            "seed": int(raw["latent_seed"]),
            "shape": list(raw["latent_shape"]),
            "dtype": str(raw["latent_dtype"]),
            "finite": True,
            "tensor_sha256": str(raw["latent_tensor_sha256"]),
            "row_sha256": [str(item) for item in raw["latent_row_sha256"]],
            "row0_zero": True,
        },
        "candidate_pool": {
            "shape": list(raw["candidate_shape"]),
            "dtype": str(raw["candidate_dtype"]),
            "finite": bool(raw["candidate_finite"]),
            "pool_sha256": str(raw["candidate_tensor_sha256_after"]),
            "row_sha256": rows,
            "candidate0": {
                "index": 0,
                "row_sha256": rows[0],
                "default_output_sha256": str(raw["default_output_sha256"]),
            },
        },
        "forward_calls": _zero_forward_calls(before=before, after=after, primary=primary),
        "action": {
            "selector_arms": selected_arms,
            "simulator_selected_index": 0,
            "simulator_selected_row_sha256": rows[0],
        },
        "training_pool": {
            "atom_matrix": atoms.tolist(),
            "atom_matrix_sha256": str(summary["atom_matrix_sha256"]),
            "atom_source_valid_mask": atom_source.tolist(),
            "atom_applicable_mask": atom_applicable.tolist(),
            "source_valid_mask": source_valid.tolist(),
            "physical_feasible_mask": physical.tolist(),
            "raw_context": raw_context,
            "context_source_complete": source_complete,
            "atom_phase_receipt": dict(summary["atom_materialization_phase_receipt"]),
        },
        "signal": {
            "integration_boundary": dict(raw["integration_boundary"]),
            "controlled_scene": dict(raw["controlled_scene"]),
            "causal_signal_atom_input_sha256": str(raw["causal_signal_atom_input_sha256"]),
        },
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
    }


def _typed_failure_unit(
    *,
    unit_index: int,
    route_plan_sha256: str,
    schedule: Mapping[str, Any],
    scenario_seed: int,
    failure_class: str,
    failure_reason: str,
    callback: Any | None = None,
    raw: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record = dict(schedule["route_record"])
    primary = 0 if raw is None else int(raw.get("primary_pool_model_call_count", 0))
    after = 0 if callback is None else int(callback.model_call_count)
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "unit_index": int(unit_index),
        "planned_unit_id_sha256": _unit_id(
            route_plan_sha256=route_plan_sha256,
            unit_index=unit_index,
            route_id=str(schedule["route_id"]),
            scenario_seed=scenario_seed,
        ),
        "route": {
            "family_id": schedule["family_id"],
            "route_id": schedule["route_id"],
            "corridor_id": schedule["corridor_id"],
            "revised_plan_ordinal": int(schedule.get("revised_plan_ordinal", unit_index)),
            "parent_ordinal": _source_ordinal(schedule, unit_index),
            "route_identity_sha256": record["identity_sha256"],
            "map_sha256": record["source_map_sha256"],
            "source_artifact_sha256": schedule["source_artifact_sha256"],
            "event_manifest_sha256": schedule["event_manifest_sha256"],
            "scenario_seed": int(scenario_seed),
            "source_stratum": dict(record["source_stratum"]),
        },
        "input": None,
        "latent": None,
        "candidate_pool": None,
        "forward_calls": _zero_forward_calls(
            before=max(0, after - primary), after=after, primary=primary
        ),
        "action": None,
        "training_pool": None,
        "signal": None,
        "terminal": {
            "status": "typed_failure",
            "failure_class": str(failure_class),
            "failure_reason": str(failure_reason),
        },
    }


def _unattempted_unit(
    *, unit_index: int, route_plan_sha256: str, schedule: Mapping[str, Any], scenario_seed: int
) -> dict[str, Any]:
    result = _typed_failure_unit(
        unit_index=unit_index,
        route_plan_sha256=route_plan_sha256,
        schedule=schedule,
        scenario_seed=scenario_seed,
        failure_class="unattempted",
        failure_reason="run_terminated_before_this_planned_unit",
    )
    result["terminal"] = {"status": "unattempted", "failure_class": None, "failure_reason": None}
    return result


def _manifest(
    *,
    route_plan: Mapping[str, Any],
    base: Mapping[str, Any],
    camp_head: str,
    assets: Any,
    pre_model_qualification: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "camp_head": str(camp_head),
        "fixed_dp_head": FIXED_DP_HEAD,
        "route_plan_schema_version": route_plan["schema_version"],
        "route_plan_evidence_role": route_plan["evidence_role"],
        "route_plan_sha256": str(route_plan["route_plan_sha256"]),
        "planned_unit_count": int(route_plan["denominator"]["planned"]),
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "generator_id": V26_GENERATOR_ID,
        "generator_topology": v26_generator_topology(),
        "fixed_dp": dict(base["fixed_dp"]),
        "base_probe": {
            "path": base["source_path"],
            "sha256": base["source_sha256"],
        },
        "pre_model_qualification": {
            "path": pre_model_qualification["path"],
            "sha256": pre_model_qualification["sha256"],
            "manifest_sha256": pre_model_qualification["manifest_sha256"],
            "status": pre_model_qualification["status"],
            "parent_plan_sha256": pre_model_qualification.get("parent_plan_sha256"),
            "revision_review_path": pre_model_qualification.get("review_path"),
            "revision_review_sha256": pre_model_qualification.get("review_sha256"),
        },
        "selector": {
            "reference_role": "v25_zero_shot_reference_read_only",
            "reference_weights_root_sha256": assets.reference_weights_root_sha256,
            "reference_weights_review_root_sha256": assets.reference_weights_review_root_sha256,
            "atom_scales_sha256": assets.atom_scales_sha256,
            "static9d_weights_sha256": assets.static9d_weights_sha256,
            "scene9d_theta_sha256": assets.scene9d_theta_sha256,
            "static14d_weights_sha256": assets.static14d_weights_sha256,
            "scene14d_theta_sha256": assets.scene14d_theta_sha256,
            "context_scaler_sha256": assets.context_scaler_sha256,
            "simplex_nonnegative_atol": FROZEN_SIMPLEX_TOLERANCE,
        },
        "execution_topology": {
            "route_state": "fresh_own_state_per_planned_route",
            "state_ticks": 1,
            "pool_generation": "one_same_ego_b8_forward_per_unit",
            "candidate0": "frozen_row0_default_output_and_simulator_action",
            "selector": "five_same_pool_counterfactual_selectors_only",
            "post_pool_model_dp_latent_generation_mutation_regeneration": 0,
        },
    }


class _AcquisitionLedger:
    def __init__(self, *, output_dir: Path, manifest: Mapping[str, Any], route_plan: Mapping[str, Any]) -> None:
        self.output_dir = output_dir.resolve()
        if self.output_dir.exists():
            raise FileExistsError(f"V26 Stage8b output already exists: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.manifest = dict(manifest)
        self.route_plan = dict(route_plan)
        self.units: list[dict[str, Any] | None] = [None] * int(route_plan["denominator"]["planned"])
        _atomic_write_json(self.output_dir / "manifest.json", self.manifest)
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {"evidence_role": EVIDENCE_ROLE, "status": "running", "planned": len(self.units)},
        )

    def record(self, unit: Mapping[str, Any]) -> None:
        index = int(unit["unit_index"])
        if not 0 <= index < len(self.units) or self.units[index] is not None:
            raise ValueError("V26 Stage8b unit ledger index is invalid or already recorded")
        materialized = dict(unit)
        self.units[index] = materialized
        _atomic_write_json(self.output_dir / "units" / f"{index:04d}.json", materialized)

    def record_parent_exception_boundary(
        self,
        *,
        unit_index: int,
        route_plan_sha256: str,
        schedule: Mapping[str, Any],
        scenario_seed: int,
        phase: str,
        exc: Exception,
        callback: Any | None = None,
        raw: Mapping[str, Any] | None = None,
    ) -> bool:
        """Atomically retain the first unrecorded boundary of an outer stop.

        A parent-level exception must not leave only an aggregate terminal
        error: the route at which execution stopped receives its own typed
        receipt before ``finalize`` marks later routes unattempted.
        """

        if not 0 <= int(unit_index) < len(self.units):
            raise ValueError("V26 Stage8b parent-exception boundary index is invalid")
        if self.units[int(unit_index)] is not None:
            return False
        unit = _typed_failure_unit(
            unit_index=int(unit_index),
            route_plan_sha256=route_plan_sha256,
            schedule=schedule,
            scenario_seed=int(scenario_seed),
            failure_class="ParentExecutionException",
            failure_reason=f"{type(exc).__name__}: {exc}",
            callback=callback,
            raw=raw,
        )
        unit["parent_exception_boundary"] = {
            "phase": str(phase),
            "exception_class": type(exc).__name__,
            "exception_message": str(exc),
            "revised_plan_ordinal": int(schedule.get("revised_plan_ordinal", unit_index)),
        }
        self.record(unit)
        return True

    def finalize(self, *, terminal_error: str | None = None) -> Path:
        routes = list(self.route_plan["routes"])
        plan_sha = str(self.route_plan["route_plan_sha256"])
        for index, unit in enumerate(self.units):
            if unit is None:
                self.record(
                    _unattempted_unit(
                        unit_index=index,
                        route_plan_sha256=plan_sha,
                        schedule=routes[index],
                        scenario_seed=SCENARIO_SEED_BASE + _source_ordinal(routes[index], index),
                    )
                )
        finalized = [unit for unit in self.units if unit is not None]
        complete = [unit for unit in finalized if unit["terminal"]["status"] == "complete"]
        failed = [unit for unit in finalized if unit["terminal"]["status"] == "typed_failure"]
        unattempted = [unit for unit in finalized if unit["terminal"]["status"] == "unattempted"]
        denominator = {
            "planned": len(finalized),
            "complete": len(complete),
            "failed": len(failed),
            "unattempted": len(unattempted),
        }
        rows_sha, scales_sha, label_sha = self._write_training_artifacts(complete)
        report = {
            "schema_version": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "evidence_role": EVIDENCE_ROLE,
            "status": "terminal_training_evidence" if complete else "terminal_no_trainable_pools",
            "fixed_dp_head": FIXED_DP_HEAD,
            "camp_head": self.manifest["camp_head"],
            "route_plan_sha256": self.manifest["route_plan_sha256"],
            "generator_id": V26_GENERATOR_ID,
            "generator_topology": v26_generator_topology(),
            "runner_id": "camp_dp_v26_native_same_ego_b8_acquisition_runner_v1",
            "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "training_rows_schema_version": V26_TRAINING_ROWS_SCHEMA_VERSION,
            "evaluation_schema": "camp_dp_v26_training_evidence_only_no_formal_evaluation_v1",
            "outcome_fields_consumed": [],
            "holdout_accessed": False,
            "source_manifest_sha256": self.manifest["route_plan_sha256"],
            "training_rows_sha256": rows_sha,
            "training_scales_sha256": scales_sha,
            "label_sidecar_sha256": label_sha,
            "snapshot_count": len(complete),
            "candidate_count": len(complete) * 8,
            "denominator": denominator,
            "failure_denominator_complete": True,
            "terminal_error": terminal_error,
        }
        _atomic_write_json(self.output_dir / "report.json", report)
        _atomic_write_json(
            self.output_dir / "raw_receipt.json",
            {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "evidence_role": EVIDENCE_ROLE,
                "manifest_sha256": _file_sha256(self.output_dir / "manifest.json"),
                "route_plan_sha256": self.manifest["route_plan_sha256"],
                "denominator": denominator,
                "terminal_error": terminal_error,
            },
        )
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {"evidence_role": EVIDENCE_ROLE, "status": "terminal", "denominator": denominator},
        )
        (self.output_dir / "run.exit").write_bytes(b"0\n")
        return self.output_dir / "report.json"

    def _write_training_artifacts(self, complete: Sequence[Mapping[str, Any]]) -> tuple[str, str, str]:
        import numpy as np

        count = len(complete)
        rows_path = self.output_dir / "training_rows.npz"
        scales_path = self.output_dir / "training_scales.json"
        label_path = self.output_dir / "label_sidecar.json"
        if count:
            atoms = np.asarray([unit["training_pool"]["atom_matrix"] for unit in complete], dtype=np.float64)
            atom_source = np.asarray(
                [unit["training_pool"]["atom_source_valid_mask"] for unit in complete], dtype=np.bool_
            )
            applicable = np.asarray(
                [unit["training_pool"]["atom_applicable_mask"] for unit in complete], dtype=np.bool_
            )
            source = np.asarray(
                [unit["training_pool"]["source_valid_mask"] for unit in complete], dtype=np.bool_
            )
            physical = np.asarray(
                [unit["training_pool"]["physical_feasible_mask"] for unit in complete], dtype=np.bool_
            )
            route_ids = np.asarray([unit["route"]["route_id"] for unit in complete], dtype="U256")
            corridor_ids = np.asarray([unit["route"]["corridor_id"] for unit in complete], dtype="U64")
            family_ids = np.asarray([unit["route"]["family_id"] for unit in complete], dtype="U128")
            seeds = np.asarray([unit["route"]["scenario_seed"] for unit in complete], dtype=np.int64)
            parent_ordinals = np.asarray(
                [unit["route"]["parent_ordinal"] for unit in complete], dtype=np.int64
            )
            scenario_ids = np.asarray(
                [unit["planned_unit_id_sha256"] for unit in complete], dtype="U64"
            )
            weights = hierarchical_snapshot_weights(
                route_ids.tolist(), corridor_ids.tolist(), seeds.tolist(), [0] * count
            )
            scale_receipt = fit_train_only_atom_scales(
                atoms, source, atom_source, applicable, weights, corridor_ids.tolist()
            )
            scales = np.asarray(scale_receipt["scales"], dtype=np.float64)
            labels = build_train_only_causal_labels(
                atoms, source, atom_source, applicable, physical, scales
            )
            raw_context = np.asarray(
                [
                    [unit["training_pool"]["raw_context"][name] for name in RAW_FEATURE_NAMES]
                    for unit in complete
                ],
                dtype=np.float64,
            )
            context_source = np.asarray(
                [
                    [unit["training_pool"]["context_source_complete"][name] for name in RAW_FEATURE_NAMES]
                    for unit in complete
                ],
                dtype=np.bool_,
            )
            latent_hashes = np.asarray(
                [unit["latent"]["row_sha256"] for unit in complete], dtype="U64"
            )
            candidate_hashes = np.asarray(
                [unit["candidate_pool"]["row_sha256"] for unit in complete], dtype="U64"
            )
        else:
            atoms = np.zeros((0, 8, 14), dtype=np.float64)
            atom_source = np.zeros((0, 8, 14), dtype=np.bool_)
            applicable = np.zeros((0, 8, 14), dtype=np.bool_)
            source = np.zeros((0, 8), dtype=np.bool_)
            physical = np.zeros((0, 8), dtype=np.bool_)
            route_ids = np.asarray([], dtype="U1")
            corridor_ids = np.asarray([], dtype="U1")
            family_ids = np.asarray([], dtype="U1")
            seeds = np.asarray([], dtype=np.int64)
            parent_ordinals = np.asarray([], dtype=np.int64)
            scenario_ids = np.asarray([], dtype="U1")
            raw_context = np.zeros((0, len(RAW_FEATURE_NAMES)), dtype=np.float64)
            context_source = np.zeros((0, len(RAW_FEATURE_NAMES)), dtype=np.bool_)
            latent_hashes = np.zeros((0, 8), dtype="U64")
            candidate_hashes = np.zeros((0, 8), dtype="U64")
            scales = np.ones(14, dtype=np.float64)
            labels = {
                "normalized_atoms": atoms,
                "oracle_indices": np.zeros((0,), dtype=np.int64),
                "margins": np.zeros((0, 8), dtype=np.float64),
            }
            weights = np.zeros((0,), dtype=np.float64)
            scale_receipt = {
                "schema_version": "camp_dp_v26_no_trainable_pool_scales_v1",
                "scales": scales.tolist(),
                "status": "not_evaluated_no_complete_pools",
            }
        _atomic_write_json(scales_path, _json_native(scale_receipt))
        _atomic_write_npz(
            rows_path,
            schema_version=np.asarray(V26_TRAINING_ROWS_SCHEMA_VERSION),
            normalized_atoms_14d=np.asarray(labels["normalized_atoms"], dtype=np.float64),
            raw_context=raw_context,
            context_source_complete=context_source,
            oracle_indices=np.asarray(labels["oracle_indices"], dtype=np.int64),
            margins=np.asarray(labels["margins"], dtype=np.float64),
            source_valid_mask=source,
            atom_source_valid_mask=atom_source,
            atom_applicable_mask=applicable,
            physical_feasible_mask=physical,
            record_weights=weights,
            route_ids=route_ids,
            corridor_ids=corridor_ids,
            map_family_ids=family_ids,
            seeds=seeds,
            parent_ordinals=parent_ordinals,
            scenario_ids=scenario_ids,
            source_manifest_sha256=np.asarray(self.manifest["route_plan_sha256"]),
            event_manifest_sha256=np.asarray(
                [unit["route"]["event_manifest_sha256"] for unit in complete], dtype="U64"
            ),
            model_call_count=np.ones((count,), dtype=np.int64),
            sequential_forward_count=np.zeros((count,), dtype=np.int64),
            candidate0_row=np.zeros((count,), dtype=np.int64),
            post_pool_model_dp_latent_generation_calls=np.zeros((count,), dtype=np.int64),
            candidate_pool_mutation_count=np.zeros((count,), dtype=np.int64),
            trajectory_regeneration_count=np.zeros((count,), dtype=np.int64),
            latent_row_sha256=latent_hashes,
            candidate_row_sha256=candidate_hashes,
            training_scales=scales,
        )
        label = {
            "schema_version": LABEL_SIDECAR_SCHEMA_VERSION,
            "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "label_contract": "causal_policy_distillation_no_outcome",
            "fresh_or_outcome_consumed": False,
            "identity_fields_used_as_label_or_feature": False,
            "source_manifest_sha256": self.manifest["route_plan_sha256"],
            "training_scales_sha256": _file_sha256(scales_path),
        }
        _atomic_write_json(label_path, label)
        return _file_sha256(rows_path), _file_sha256(scales_path), _file_sha256(label_path)

    @classmethod
    def write_training_artifacts_from_atomic_units(
        cls,
        *,
        output_dir: Path,
        manifest: Mapping[str, Any],
        complete: Sequence[Mapping[str, Any]],
    ) -> tuple[str, str, str]:
        """Reuse the exact no-model artifact writer during a ledger-only recovery."""

        writer = object.__new__(cls)
        writer.output_dir = Path(output_dir).resolve()
        writer.manifest = dict(manifest)
        return cls._write_training_artifacts(writer, complete)


def _prepare_route(
    *,
    route_type: Any,
    output_dir: Path,
    unit_index: int,
    schedule: Mapping[str, Any],
    family_by_id: Mapping[str, Mapping[str, Any]],
    base: Mapping[str, Any],
    qualified_unit: Mapping[str, Any],
    source_ordinal: int,
) -> tuple[dict[str, Any] | None, str | None]:
    route_path = output_dir / "route_assets" / f"{unit_index:04d}.pkl"
    route_sha = _route_asset(route_type, schedule["route_record"], route_path)
    record = dict(schedule["route_record"])
    projection = v26_source_projection_binding(
        Path(str(record["source_map_path"])), str(record["source_map_sha256"])
    )
    signal, failure = _signal_config(
        schedule=schedule,
        family=family_by_id[str(schedule["family_id"])],
        route_sha256=route_sha,
    )
    if failure is not None:
        return None, failure
    if (
        projection["projection_sha256"]
        != qualified_unit["source_projection"].get("projection_sha256")
        or signal["source_signal_authority"]["source_signal_authority_identity_sha256"]
        != qualified_unit["signal"]["source_provenance"].get(
            "source_signal_authority_identity_sha256"
        )
    ):
        return None, "pre_model_qualification_source_binding_drifted"
    seed = SCENARIO_SEED_BASE + source_ordinal
    config = _route_probe_config(
        base=base,
        schedule=schedule,
        route_path=route_path,
        route_sha256=route_sha,
        scenario_seed=seed,
        signal=signal,
    )
    config["source_projection"] = projection
    signal_binding = resolve_v26_signal_adapter(config)
    _atomic_write_json(output_dir / "route_configs" / f"{unit_index:04d}.json", config)
    return {
        "config": config,
        "signal": signal_binding,
        "projection": projection,
        "scenario_seed": seed,
    }, None


def run(args: argparse.Namespace) -> Path:
    output_dir = args.output_dir.resolve()
    plan_path = args.route_plan.resolve()
    if not plan_path.is_file():
        raise FileNotFoundError(plan_path)
    raw_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if raw_plan.get("schema_version") == PLAN_REVISION_SCHEMA_VERSION:
        if args.parent_route_plan is None or args.route_plan_revision_review is None:
            raise ValueError("V26 Stage8b revised plan requires parent plan and revision review")
        authority = load_verified_revised_plan(
            parent_plan_path=args.parent_route_plan,
            revised_plan_path=plan_path,
            revision_review_path=args.route_plan_revision_review,
            qualification_receipt_path=args.pre_model_qualification,
        )
        route_plan = authority["route_plan"]
        qualification = authority["qualification"]
    else:
        if args.parent_route_plan is not None or args.route_plan_revision_review is not None:
            raise ValueError("V26 Stage8b original plan rejects revision authority arguments")
        route_plan = validate_diversified_route_plan(raw_plan)
        qualification = _require_pre_model_qualification(
            args.pre_model_qualification,
            route_plan=route_plan,
            camp_head=args.expected_camp_head,
        )
    if route_plan["fixed_dp_head"] != FIXED_DP_HEAD:
        raise ValueError("V26 Stage8b route plan fixed-DP identity drifted")
    base = _load_base_probe_config(args.base_probe_config)
    if _tracked_changes(ROOT) or _git_head(ROOT) != args.expected_camp_head:
        raise ValueError("V26 Stage8b requires an exact clean CAMP checkout")
    fixed_dp_repo = args.fixed_dp_repo.resolve()
    if _tracked_changes(fixed_dp_repo) or _git_head(fixed_dp_repo) != FIXED_DP_HEAD:
        raise ValueError("V26 Stage8b requires an exact clean fixed-DP checkout")
    assets = _load_zero_shot_reference_selector_assets(args)
    manifest = _manifest(
        route_plan=route_plan,
        base=base,
        camp_head=args.expected_camp_head,
        assets=assets,
        pre_model_qualification=qualification,
    )
    if output_dir.exists():
        raise FileExistsError(f"V26 Stage8b output already exists: {output_dir}")
    with _exclusive_worker_lock(args.worker_lock.resolve()):
        import torch

        _resource_precheck(output_dir, args.device, torch)
        for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        enforce_v26_dp312_lanelet2_precedence()
        from scripts.integrations.run_diffusion_planner_camp_replay import _load_model  # noqa: PLC0415
        from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: PLC0415
            _install_fixed_dp_annotation_compatibility,
        )
        import scenario_generation.replay as replay  # noqa: PLC0415
        import scenario_generation.tensor_converter as tensor_converter  # noqa: PLC0415
        from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder  # noqa: PLC0415
        from scenario_generation.route import Route  # noqa: PLC0415

        ledger = _AcquisitionLedger(output_dir=output_dir, manifest=manifest, route_plan=route_plan)
        prepared: dict[int, dict[str, Any]] = {}
        family_by_id = {
            str(item["family_id"]): item for item in route_plan["family_projections"]
        }
        route_plan_sha = str(route_plan["route_plan_sha256"])
        terminal_error: str | None = None
        active_boundary: tuple[int, Mapping[str, Any], int, str] | None = None
        try:
            # Every route and its signal binding is prepared before the model is
            # loaded.  A missing traffic authority is therefore a typed
            # pre-forward failure rather than an implicit no-signal fallback.
            for index, schedule in enumerate(route_plan["routes"]):
                source_ordinal = _source_ordinal(schedule, index)
                seed = SCENARIO_SEED_BASE + source_ordinal
                active_boundary = (index, schedule, seed, "pre_model_preparation")
                try:
                    prepared_item, failure = _prepare_route(
                        route_type=Route,
                        output_dir=output_dir,
                        unit_index=index,
                        schedule=schedule,
                        family_by_id=family_by_id,
                        base=base,
                        qualified_unit=qualification["units"][index],
                        source_ordinal=source_ordinal,
                    )
                    if failure is not None:
                        ledger.record(
                            _typed_failure_unit(
                                unit_index=index,
                                route_plan_sha256=route_plan_sha,
                                schedule=schedule,
                                scenario_seed=seed,
                                failure_class="PreModelSignalAuthorityUnavailable",
                                failure_reason=failure,
                            )
                        )
                    else:
                        assert prepared_item is not None
                        prepared[index] = prepared_item
                except Exception as exc:
                    ledger.record(
                        _typed_failure_unit(
                            unit_index=index,
                            route_plan_sha256=route_plan_sha,
                            schedule=schedule,
                            scenario_seed=seed,
                            failure_class=type(exc).__name__,
                            failure_reason=str(exc),
                        )
                    )
            if prepared:
                first_prepared = min(prepared)
                first_schedule = route_plan["routes"][first_prepared]
                active_boundary = (
                    first_prepared,
                    first_schedule,
                    SCENARIO_SEED_BASE + _source_ordinal(first_schedule, first_prepared),
                    "model_initialization",
                )
                _install_fixed_dp_annotation_compatibility(fixed_dp_repo)
                model, model_args = _load_model(
                    Path(base["fixed_dp"]["checkpoint"]["path"]),
                    Path(base["fixed_dp"]["args_json"]["path"]),
                    args.device,
                )
                model.eval()
                for index, prepared_item in prepared.items():
                    if ledger.units[index] is not None:
                        continue
                    schedule = route_plan["routes"][index]
                    seed = int(prepared_item["scenario_seed"])
                    active_boundary = (index, schedule, seed, "native_same_ego_b8_replay")
                    callback_box: dict[str, Any] = {}

                    def on_completed(raw: Mapping[str, Any], callback: Any) -> None:
                        callback_box["callback"] = callback
                        ledger.record(
                            _completed_unit(
                                raw,
                                callback,
                                unit_index=index,
                                route_plan_sha256=route_plan_sha,
                                schedule=schedule,
                                scenario_seed=seed,
                            )
                        )

                    with v26_source_bound_projection(prepared_item["projection"]):
                        receipts, callback, native_result = run_v26_native_same_ego_b8_replay(
                            config=prepared_item["config"],
                            model=model,
                            model_args=model_args,
                            tensor_converter=tensor_converter,
                            replay=replay,
                            builder_type=LaneletSceneBuilder,
                            route_type=Route,
                            fixed_dp_repo=fixed_dp_repo,
                            selector_assets=assets,
                            signal_adapter=prepared_item["signal"].adapter,
                            integration_boundary=build_v26_integration_boundary(
                                signal=prepared_item["signal"],
                                reference_weights_root_sha256=assets.reference_weights_root_sha256,
                            ),
                            device=args.device,
                            max_ticks=1,
                            scratch_parent=output_dir.parent,
                            on_completed_unit=on_completed,
                        )
                    if ledger.units[index] is None:
                        raw = receipts[0] if receipts else None
                        ledger.record(
                            _typed_failure_unit(
                                unit_index=index,
                                route_plan_sha256=route_plan_sha,
                                schedule=schedule,
                                scenario_seed=seed,
                                failure_class=str(native_result.get("failure_class", "NativeReplayFailure")),
                                failure_reason=str(native_result.get("failure_reason", native_result.get("reason", "no_terminal_receipt"))),
                                callback=callback,
                                raw=raw,
                            )
                        )
        except Exception as exc:
            terminal_error = f"{type(exc).__name__}: {exc}"
            if active_boundary is not None:
                index, schedule, seed, phase = active_boundary
                ledger.record_parent_exception_boundary(
                    unit_index=index,
                    route_plan_sha256=route_plan_sha,
                    schedule=schedule,
                    scenario_seed=seed,
                    phase=phase,
                    exc=exc,
                )
        return ledger.finalize(terminal_error=terminal_error)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--worker-lock", type=Path, required=True)
    parser.add_argument("--route-plan", type=Path, required=True)
    parser.add_argument("--base-probe-config", type=Path, required=True)
    parser.add_argument("--reference-weights", type=Path, required=True)
    parser.add_argument("--reference-weights-root", required=True)
    parser.add_argument("--reference-weights-review", type=Path, required=True)
    parser.add_argument("--reference-weights-review-root", required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--expected-camp-head", required=True)
    parser.add_argument("--pre-model-qualification", type=Path, required=True)
    parser.add_argument("--parent-route-plan", type=Path)
    parser.add_argument("--route-plan-revision-review", type=Path)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    receipt = run(parse_args(argv))
    print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
