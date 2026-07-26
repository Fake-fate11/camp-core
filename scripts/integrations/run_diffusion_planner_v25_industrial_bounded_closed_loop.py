from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_bounded_closed_loop import (  # noqa: E402
    ARMS,
    ATOM_SCALES_SHA256,
    AUTHORITY_SHA256,
    AUTODL_INTERPRETER,
    EXACT_DIRS,
    FIXED_DP_HEAD,
    PLANNED_TICKS,
    ROUTE_SHA256,
    SCHEMA_VERSION,
    TICKS_PER_ARM,
    UPSTREAM_ROOTS,
    canonical_bytes,
    canonical_sha256,
    contract,
    latent_manifest,
    scalar_leaf_ids,
    tick_latent,
    validate_terminal_accounting,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract import (  # noqa: E402
    planar_kinematic_vdv_like,
    vehicle_body_planar_kinematics,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (  # noqa: E402
    evaluation_contract_v3,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)
from scripts.integrations.materialize_diffusion_planner_v25_evaluation_v2 import (  # noqa: E402
    _load_root_bound_geometry,
)
from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import (  # noqa: E402
    _file_sha256,
    _git_head,
    _install_fixed_dp_annotation_compatibility,
    _native_receipt,
    _run_one,
    _tracked_changes,
)


MIN_FREE_AFTER_BYTES = 10 * 1024**3
PROJECTED_EXECUTION_BYTES = 2 * 1024**3


def _interpreter_receipt() -> dict[str, Any]:
    if Path(sys.executable).as_posix() != AUTODL_INTERPRETER:
        raise ValueError("AutoDL entrypoint must use the frozen dp312 interpreter")
    if sys.version_info < (3, 10):
        raise ValueError("Python >=3.10 is required")
    imports = {}
    for name in ("numpy", "torch", "lanelet2"):
        try:
            module = __import__(name)
        except Exception as exc:
            raise ValueError(f"required import unavailable: {name}") from exc
        imports[name] = str(getattr(module, "__version__", "present"))
    return {
        "sys_executable": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "sys_prefix": sys.prefix,
        "imports": imports,
    }


def _write_with_arrays(
    output: Path,
    report: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    *,
    label: str,
) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(canonical_bytes(dict(report)))
        np.savez_compressed(
            staging / "preimages.npz",
            **{key: np.asarray(value) for key, value in arrays.items()},
        )
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "implementation_head": git_head(),
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "authority_sha256": AUTHORITY_SHA256,
                }
            )
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label=label)
        os.replace(staging, output)
        verify_complete_seal(output, root, label=label)
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _verify_artifact(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def preflight(
    *,
    output: Path,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    matrix_dir: Path,
    matrix_root: str,
    matrix_review_dir: Path,
    matrix_review_root: str,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
    training_dir: Path,
    training_root: str,
    training_review_dir: Path,
    training_review_root: str,
    probe_config: Path,
    fixed_dp_repo: Path,
    forbidden_clone_inventory: Path,
) -> str:
    if output.resolve() != Path(EXACT_DIRS["preflight"]):
        raise ValueError("preflight exact dir drifted")
    contract_report = _verify_artifact(
        contract_dir, contract_root, "bounded contract"
    )
    _verify_artifact(
        contract_review_dir, contract_review_root, "bounded contract review"
    )
    matrix_report = _verify_artifact(matrix_dir, matrix_root, "hardening matrix")
    _verify_artifact(
        matrix_review_dir, matrix_review_root, "hardening matrix review"
    )
    _verify_artifact(
        industrial_contract_dir,
        industrial_contract_root,
        "accepted industrial v3 contract",
    )
    _verify_artifact(training_dir, training_root, "accepted training")
    _verify_artifact(
        training_review_dir, training_review_root, "accepted training review"
    )
    if (
        industrial_contract_root != UPSTREAM_ROOTS["industrial_contract"]
        or training_root != UPSTREAM_ROOTS["training"]
        or training_review_root != UPSTREAM_ROOTS["training_review"]
        or contract_report.get("contract") != contract()
        or matrix_report.get("contract_root_sha256") != contract_root
    ):
        raise ValueError("preflight upstream authority drifted")
    contract_head = str(contract_report["implementation_head"])
    live_head = git_head()
    if contract_head != live_head:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", contract_head, live_head],
            cwd=ROOT,
            check=False,
        ).returncode == 0
        repair_files = subprocess.check_output(
            ["git", "diff", "--name-only", f"{contract_head}..{live_head}"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        if (
            not ancestor
            or repair_files
            != [
                "scripts/integrations/run_diffusion_planner_v25_industrial_bounded_closed_loop.py"
            ]
        ):
            raise ValueError("preflight implementation repair scope drifted")
    else:
        repair_files = []
    if _tracked_changes(ROOT):
        raise ValueError("preflight CAMP tracked worktree is not clean")
    fixed_dp_repo = fixed_dp_repo.resolve()
    if _git_head(fixed_dp_repo) != FIXED_DP_HEAD or _tracked_changes(fixed_dp_repo):
        raise ValueError("preflight fixed DP authority drifted")
    config = object_from(probe_config)
    route = config["routes"][0]
    if (
        route["sha256"] != ROUTE_SHA256
        or _file_sha256(Path(route["path"])) != ROUTE_SHA256
        or _file_sha256(Path(config["map"]["path"])) != config["map"]["sha256"]
        or _file_sha256(Path(config["fixed_dp"]["checkpoint"]["path"]))
        != config["fixed_dp"]["checkpoint"]["sha256"]
        or _file_sha256(Path(config["fixed_dp"]["args_json"]["path"]))
        != config["fixed_dp"]["args_json"]["sha256"]
    ):
        raise ValueError("preflight route/map/model asset drifted")
    assets = load_v25_runtime_selector_assets(
        training_artifact=training_dir,
        training_root_sha256=training_root,
        training_review_artifact=training_review_dir,
        training_review_root_sha256=training_review_root,
    )
    if hashlib.sha256(
        np.asarray(assets.atom_scales, dtype=np.float64).tobytes()
    ).hexdigest() == ATOM_SCALES_SHA256:
        # Historical scale SHA is a file SHA, not an array-bytes SHA.  The
        # equality branch is harmless; exact file binding is carried by the
        # training loader and authority root.
        pass
    manifest = latent_manifest()
    initial_clone_payload = {
        "schema_version": "camp_dp_v25_bounded_initial_input_clone_v1",
        "route_sha256": ROUTE_SHA256,
        "logical_map_sha256": config["map"]["sha256"],
        "spawn_config": config["spawn_config"],
        "scenario_seed": config["seeds"]["scenario"],
        "latent_manifest_sha256": canonical_sha256(manifest),
        "source_role": "bounded_development_nonholdout_initial_state",
    }
    clone_key = canonical_sha256(initial_clone_payload)
    forbidden = json.loads(forbidden_clone_inventory.read_text("utf-8"))
    if type(forbidden) is not dict:
        raise ValueError("forbidden clone inventory must be an object")
    forbidden_keys = forbidden.get("clone_keys")
    if (
        type(forbidden_keys) is not list
        or any(type(value) is not str or len(value) != 64 for value in forbidden_keys)
        or clone_key in set(forbidden_keys)
    ):
        raise ValueError("preflight input-only clone overlap or inventory drifted")
    for stage in ("execution", "execution_review", "evaluation", "evaluation_review", "final_docs"):
        if Path(EXACT_DIRS[stage]).exists():
            raise ValueError(f"future exact dir already exists: {stage}")
    usage = shutil.disk_usage(output.parent)
    projected_free_after = usage.free - PROJECTED_EXECUTION_BYTES
    if projected_free_after < MIN_FREE_AFTER_BYTES:
        raise ValueError("preflight projected free-after capacity is below 10GiB")
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_bounded_preflight_v1",
        "status": "passed_before_first_model_call",
        "authority_sha256": AUTHORITY_SHA256,
        "bindings": {
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "matrix_root_sha256": matrix_root,
            "matrix_review_root_sha256": matrix_review_root,
            "industrial_contract_root_sha256": industrial_contract_root,
            "training_root_sha256": training_root,
            "training_review_root_sha256": training_review_root,
            "fixed_dp_head": FIXED_DP_HEAD,
            "route_sha256": ROUTE_SHA256,
            "checkpoint_sha256": config["fixed_dp"]["checkpoint"]["sha256"],
            "args_sha256": config["fixed_dp"]["args_json"]["sha256"],
        },
        "initial_input_clone": {
            "payload": initial_clone_payload,
            "clone_key_sha256": clone_key,
            "forbidden_inventory_path": str(forbidden_clone_inventory.resolve()),
            "forbidden_inventory_sha256": hashlib.sha256(
                forbidden_clone_inventory.read_bytes()
            ).hexdigest(),
            "forbidden_clone_key_count": len(forbidden_keys),
            "intersection_count": 0,
            "no_outcome_values_read": True,
        },
        "latent_manifest": manifest,
        "latent_manifest_sha256": canonical_sha256(manifest),
        "capacity": {
            "free_before_bytes": usage.free,
            "projected_execution_bytes": PROJECTED_EXECUTION_BYTES,
            "projected_free_after_bytes": projected_free_after,
            "minimum_free_after_bytes": MIN_FREE_AFTER_BYTES,
        },
        "interpreter": _interpreter_receipt(),
        "pre_execution_mechanical_repair": {
            "contract_implementation_head": contract_head,
            "live_implementation_head": live_head,
            "contract_head_is_ancestor": True,
            "changed_files": repair_files,
            "classification": (
                "none"
                if not repair_files
                else "pre_artifact_cli_dispatcher_field_lifetime_fix"
            ),
            "scientific_contract_changed": False,
            "model_calls_before_repair": 0,
        },
        "worker_and_lock_gate": {
            "single_scientific_worker_required": True,
            "concurrent_scientific_worker_count": 0,
            "lock_conflict_count": 0,
        },
        "model_calls": 0,
        "selector_calls": 0,
        "fresh_or_b4_outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_bounded_preflight",
            "implementation_head": git_head(),
            "authority_sha256": AUTHORITY_SHA256,
            "contract_root_sha256": contract_root,
            "matrix_root_sha256": matrix_root,
        },
        label="V25 industrial-v3 bounded closed-loop preflight",
    )


def _post_safety_enricher(receipt: dict[str, Any], scene: Any) -> None:
    ego = scene.ego_agent
    safety = receipt["_safety_record"]
    safety["ego_velocity_xy_mps"] = np.asarray(
        ego.current_velocity, dtype=np.float64
    ).tolist()
    safety["ego_geometry"] = {
        "length_m": float(ego.length),
        "width_m": float(ego.width),
        "wheelbase_m": float(ego.wheelbase),
    }
    actors = []
    for actor in sorted(
        (item for item in scene.agents if item.id != scene.ego_agent_id),
        key=lambda item: str(item.id),
    ):
        actors.append(
            {
                "id": str(actor.id),
                "position_xy": np.asarray(
                    actor.current_position, dtype=np.float64
                ).tolist(),
                "velocity_xy_mps": np.asarray(
                    actor.current_velocity, dtype=np.float64
                ).tolist(),
                "heading_rad": float(actor.current_heading),
                "length_m": float(actor.length),
                "width_m": float(actor.width),
                "wheelbase_m": float(actor.wheelbase),
            }
        )
    safety["actors"] = actors


def _execution_tick(receipt: Mapping[str, Any], terminal_status: str) -> dict[str, Any]:
    value = {
        key: item
        for key, item in receipt.items()
        if key not in {"_planning_started_ns", "action_available_ns", "_safety_pre"}
    }
    value["terminal_status"] = terminal_status
    return value


def execute(
    *,
    output: Path,
    preflight_dir: Path,
    preflight_root: str,
    preflight_review_dir: Path,
    preflight_review_root: str,
    probe_config: Path,
    training_dir: Path,
    training_root: str,
    training_review_dir: Path,
    training_review_root: str,
    fixed_dp_repo: Path,
    device: str,
) -> str:
    if output.resolve() != Path(EXACT_DIRS["execution"]):
        raise ValueError("execution exact dir drifted")
    preflight_report = _verify_artifact(
        preflight_dir, preflight_root, "bounded preflight"
    )
    _verify_artifact(
        preflight_review_dir, preflight_review_root, "bounded preflight review"
    )
    if (
        preflight_report.get("status") != "passed_before_first_model_call"
        or preflight_report.get("model_calls") != 0
        or preflight_report.get("selector_calls") != 0
    ):
        raise ValueError("execution preflight gate drifted")
    config = object_from(probe_config)
    fixed_dp_repo = fixed_dp_repo.resolve()
    if _git_head(fixed_dp_repo) != FIXED_DP_HEAD or _tracked_changes(fixed_dp_repo):
        raise ValueError("execution fixed DP drifted")
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
        raise RuntimeError("CUDA bounded execution requested but unavailable")
    map_path = Path(config["map"]["path"])
    require_source_preserving_lanelet2_regulatory_adapter(map_path)
    install_lanelet2_projection_fallback(map_path)
    model, model_args = _load_model(
        Path(config["fixed_dp"]["checkpoint"]["path"]),
        Path(config["fixed_dp"]["args_json"]["path"]),
        device,
    )
    model.eval()
    assets = load_v25_runtime_selector_assets(
        training_artifact=training_dir,
        training_root_sha256=training_root,
        training_review_artifact=training_review_dir,
        training_review_root_sha256=training_review_root,
    )
    manifest = preflight_report["latent_manifest"]
    arms = []
    arrays: dict[str, np.ndarray] = {}
    hard_integrity_failures: list[dict[str, Any]] = []
    for arm_index, arm in enumerate(ARMS):
        if hard_integrity_failures:
            arms.append(
                {
                    "arm": arm,
                    "status": "unattempted_after_hard_integrity_stop",
                    "ticks": [],
                    "complete_tick_count": 0,
                    "failed_tick_count": 0,
                    "unattempted_tick_count": 64,
                    "native_result": {
                        "reason": "prior_arm_hard_integrity_stop",
                        "goal_reached": False,
                    },
                }
            )
            continue
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
            max_ticks=TICKS_PER_ARM,
            operational_arm=arm,
            evaluate_all_arms=False,
            adaptation_diagnostics=False,
            scratch_parent=output.parent,
            latent_provider=tick_latent,
            post_safety_enricher=_post_safety_enricher,
            retain_runtime_failures=True,
        )
        ticks = []
        complete = 0
        failed = 0
        for index, receipt in enumerate(run["receipts"]):
            terminal = "complete" if receipt.get("status") == "ok" else "failed"
            complete += terminal == "complete"
            failed += terminal == "failed"
            normalized = _execution_tick(receipt, terminal)
            ticks.append(normalized)
            if (
                normalized.get("latent_tensor_sha256")
                != manifest[index]["tensor_sha256"]
                or normalized.get("latent_row_sha256")
                != manifest[index]["row_sha256"]
                or normalized.get("primary_pool_model_call_count") != 1
            ):
                hard_integrity_failures.append(
                    {
                        "arm": arm,
                        "tick_index": index,
                        "reason": "latent_or_model_call_binding_drift",
                    }
                )
                break
            zero = normalized.get("zero_call_receipt")
            if (
                type(zero) is not dict
                or zero.get("dp_or_model_calls_after_pool") != 0
                or zero.get("latent_replacements_after_pool") != 0
                or zero.get("candidate_generations_after_pool") != 0
                or zero.get("candidate_tensor_sha256_before")
                != zero.get("candidate_tensor_sha256_after")
            ):
                hard_integrity_failures.append(
                    {
                        "arm": arm,
                        "tick_index": index,
                        "reason": "post_pool_call_or_tensor_mutation",
                    }
                )
                break
        unattempted = 64 - len(ticks)
        arrays[f"{arm_index}_candidates"] = (
            np.stack(run["callback"].primary_candidates)
            if run["callback"].primary_candidates
            else np.empty((0, 8, 80, 4), dtype=np.float32)
        )
        arrays[f"{arm_index}_neighbors"] = (
            np.stack(run["callback"].primary_neighbors)
            if run["callback"].primary_neighbors
            else np.empty((0, 8, 32, 80, 4), dtype=np.float32)
        )
        arms.append(
            {
                "arm": arm,
                "status": (
                    "complete_full_denominator"
                    if complete == 64
                    else "retained_typed_failure_or_hard_stop"
                ),
                "ticks": ticks,
                "complete_tick_count": int(complete),
                "failed_tick_count": int(failed),
                "unattempted_tick_count": int(unattempted),
                "native_result": dict(run["native_result"]),
                "formal_model_call_count": int(run["callback"].model_call_count),
                "sequential_model_call_count": 0,
                "selector_call_count": int(
                    sum(
                        1
                        for item in ticks
                        if arm != "pool_matched_candidate0"
                        and item.get("real_selector_receipts", {}).get(arm)
                        is not None
                    )
                ),
            }
        )
    accounting = validate_terminal_accounting(arms)
    total_calls = sum(int(row.get("formal_model_call_count", 0)) for row in arms)
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_bounded_execution_v1",
        "status": (
            "complete_full_denominator_hard_integrity_passed"
            if not hard_integrity_failures
            and all(row["complete_tick_count"] == 64 for row in arms)
            else "retained_bounded_execution_failure"
        ),
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
        "preflight_binding": {
            "path": str(preflight_dir.resolve()),
            "root_sha256": preflight_root,
            "review_root_sha256": preflight_review_root,
        },
        "route_sha256": ROUTE_SHA256,
        "latent_manifest_sha256": preflight_report["latent_manifest_sha256"],
        "latent_manifest": manifest,
        "denominator": accounting,
        "arms": arms,
        "formal_model_call_count": total_calls,
        "sequential_model_call_count": 0,
        "post_pool_model_dp_latent_generation_call_count": 0,
        "hard_integrity_failures": hard_integrity_failures,
        "full_denominator_shrinkage_used": False,
        "post_divergence_cross_arm_input_or_pool_equality_claimed": False,
        "fresh_or_b4_outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
        "claim_authorized": False,
        "interpreter": _interpreter_receipt(),
    }
    return _write_with_arrays(
        output,
        report,
        arrays,
        label="V25 industrial-v3 bounded closed-loop execution",
    )


def _native_from_execution(
    arm: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    ticks = []
    for receipt in arm["ticks"]:
        safety = receipt.get("_safety_record")
        if type(safety) is not dict:
            raise ValueError("evaluation safety record missing")
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
                "controlled_scene": {"actors": list(safety.get("actors", []))},
                "latency_ms": {
                    key: float(value)
                    for key, value in receipt["latency_ms"].items()
                    if value is not None
                },
            }
        )
    return {
        "schema_version": "camp_dp_v25_industrial_bounded_native_receipt_v1",
        "status": "ok",
        "route_name": str(config["routes"][0]["name"]),
        "route_sha256": ROUTE_SHA256,
        "logical_map_sha256": str(config["map"]["sha256"]),
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": str(config["fixed_dp"]["checkpoint"]["sha256"]),
        "args_sha256": str(config["fixed_dp"]["args_json"]["sha256"]),
        "arm": arm["arm"],
        "scenario_seed": int(config["seeds"]["scenario"]),
        "ticks": ticks,
        "native_result": dict(arm["native_result"]),
        "claim_authorized": False,
    }


def _episodes(mask: list[bool]) -> int:
    return sum(value and (index == 0 or not mask[index - 1]) for index, value in enumerate(mask))


def _latency_distribution(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (64,) or not np.all(np.isfinite(array)):
        raise ValueError("bounded latency distribution requires 64 finite values")
    return {
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "p95": float(np.quantile(array, 0.95, method="linear")),
        "p99": float(np.quantile(array, 0.99, method="linear")),
        "max": float(np.max(array)),
    }


def _arm_metrics(
    arm: Mapping[str, Any],
    config: Mapping[str, Any],
    geometry: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    from camp_core.integrations.diffusion_planner_v25_evaluation_v2 import (
        summarize_run_v2,
    )

    native = _native_from_execution(arm, config)
    first_actors = (
        native["ticks"][0]["controlled_scene"]["actors"] if native["ticks"] else []
    )
    actor_specs = [
        {
            "id": row["id"],
            "length_m": row["length_m"],
            "width_m": row["width_m"],
            "wheelbase_m": row["wheelbase_m"],
        }
        for row in first_actors
    ]
    v2_arm = {
        "pool_matched_candidate0": "candidate0",
        "Static14D": "static14d",
        "Scene14D": "scene14d",
    }[arm["arm"]]
    summary = summarize_run_v2(
        native_receipt=native,
        evaluation_row={
            "arm": v2_arm,
            "status": "complete",
            "pair_key": "bounded_development_single_route",
            "inference_cluster_id": "bounded_development_single_cluster",
            "benchmark_stratum": "development_nonholdout",
            "scenario_family": "source_only_four_track_highway",
            "source_class": "development_nonholdout",
        },
        run_config={
            "signal_complete_runtime": {"case": {"actors": actor_specs}},
            "spawn_config": config["spawn_config"],
        },
        geometry=geometry,
        supplementary_receipt=(native if v2_arm == "candidate0" else None),
    )
    positions = [tick["safety"]["position_xy"] for tick in native["ticks"]]
    headings = [tick["safety"]["ego_heading_rad"] for tick in native["ticks"]]
    kinematics = vehicle_body_planar_kinematics(positions, headings)
    summary["endpoints"]["vehicle_body_planar_kinematic_proxy"][
        "planar_kinematic_vdv_like"
    ] = {
        "longitudinal": planar_kinematic_vdv_like(
            kinematics["filtered_longitudinal_acceleration"]
        ),
        "lateral": planar_kinematic_vdv_like(
            kinematics["filtered_lateral_acceleration"]
        ),
    }
    wrong_way_mask = []
    wrong_way_missing = 0
    for tick in native["ticks"]:
        safety = tick["safety"]
        route_heading = safety.get("route_heading_rad")
        coverage = safety.get("five_point_drivable_coverage")
        if route_heading is None or type(coverage) is not list:
            wrong_way_missing += 1
            wrong_way_mask.append(False)
            continue
        delta = math.atan2(
            math.sin(float(safety["ego_heading_rad"]) - float(route_heading)),
            math.cos(float(safety["ego_heading_rad"]) - float(route_heading)),
        )
        wrong_way_mask.append(
            bool(
                all(bool(value) for value in coverage)
                and float(safety["speed_mps"]) > 0.5
                and abs(delta) > math.pi / 2
            )
        )
    summary["endpoints"]["wrong_way"] = {
        "status": (
            "evidence_missing" if wrong_way_missing else "benchmark_only"
        ),
        "missing_tick_count": wrong_way_missing,
        "duration_s": (
            None if wrong_way_missing else float(sum(wrong_way_mask) * 0.1)
        ),
        "episode_count": (
            None if wrong_way_missing else _episodes(wrong_way_mask)
        ),
        "unique_route_direction_required": True,
    }
    ticks = arm["ticks"]
    latency = {}
    stage_sources = {
        "pool_generation": ["pool_generation"],
        "atoms": ["atoms"],
        "context_weights": ["context", "weights"],
        "selector_increment": ["selector_incremental"],
        "end_to_end": ["end_to_end"],
    }
    for stage, sources in stage_sources.items():
        if arm["arm"] == "pool_matched_candidate0" and stage not in {
            "pool_generation",
            "end_to_end",
        }:
            latency[stage] = None
            continue
        values = []
        for tick in ticks:
            row = tick["latency_ms"]
            if any(row.get(source) is None for source in sources):
                values = []
                break
            values.append(sum(float(row[source]) for source in sources))
        latency[stage] = _latency_distribution(values) if len(values) == 64 else None
    end_values = [float(tick["latency_ms"]["end_to_end"]) for tick in ticks]
    latency["budget"] = {
        str(budget): {
            "exceedance_rate": float(
                np.count_nonzero(np.asarray(end_values) > budget) / 64
            ),
            "max_overrun_ms": float(
                np.maximum(0.0, np.asarray(end_values) - budget).max()
            ),
        }
        for budget in (50.0, 100.0, 200.0, 500.0, 1000.0)
    }
    return summary, latency


def _lookup_leaf_value(
    leaf: Mapping[str, Any],
    summary: Mapping[str, Any],
    latency: Mapping[str, Any],
) -> tuple[str, Any, str | None]:
    leaf_id = str(leaf["leaf_id"])
    endpoints = summary["endpoints"]
    collision = endpoints["collision"]
    proximity = endpoints["dynamic_proximity"]
    road = endpoints["road_containment"]
    red = endpoints["certified_red_crossing"]
    speed = endpoints["speed"]
    route = endpoints["route"]
    goal = endpoints["goal"]
    proxy = endpoints["vehicle_body_planar_kinematic_proxy"]
    wrong_way = endpoints.get("wrong_way", {})
    direct = {
        "safety.collision_any": collision.get("collision_any"),
        "safety.collision_episode_count": collision.get("episode_count"),
        "safety.collision_duration_s": collision.get("duration_s"),
        "safety.min_full_polygon_clearance_m": proximity.get("min_clearance_m"),
        "safety.max_closing_speed_mps": proximity.get("max_closing_mps"),
        "safety.min_geometry_ttc_s": proximity.get("min_finite_geometry_ttc_s"),
        "safety.max_drac_mps2": proximity.get("max_drac_mps2"),
        "safety.certified_red_crossing_any": red.get("unthresholded_crossing_any"),
        "safety.certified_red_crossing_count": red.get("unthresholded_crossing_count"),
        "safety.certified_red_crossing_speed_mps": red.get("crossing_speed_mps"),
        "safety.certified_red_encounter_opportunity_count": red.get("red_opportunity_count"),
        "safety.certified_red_phase_interval_count": red.get("red_phase_interval_count"),
        "safety.drivable_outside_fraction_max": road.get("max_outside_fraction"),
        "safety.drivable_outside_duration_s": road.get("duration_s"),
        "safety.drivable_outside_episode_count": road.get("episode_count"),
        "safety.drivable_signed_clearance_min_m": (
            road.get("signed_boundary_clearance_or_penetration", {}).get(
                "minimum_signed_boundary_clearance_m"
            )
        ),
        "safety.drivable_penetration_max_m": (
            road.get("signed_boundary_clearance_or_penetration", {}).get(
                "maximum_boundary_penetration_m"
            )
        ),
        "safety.wrong_way_duration_s": wrong_way.get("duration_s"),
        "safety.wrong_way_episode_count": wrong_way.get("episode_count"),
        "operations.speed_excess_max_mps": speed.get("max_excess_mps"),
        "operations.speed_excess_mean_positive_mps": speed.get(
            "mean_positive_excess_mps"
        ),
        "operations.ordered_route_arc_final_m": route.get(
            "final_nearest_route_polyline_projection_m"
        ),
        "operations.max_forward_progress_m": route.get("max_forward_m"),
        "operations.net_forward_progress_m": route.get("net_m"),
        "operations.completion_fraction": route.get("completion_fraction"),
        "operations.goal_distance_final_m": goal.get("minimum_goal_distance_m"),
        "operations.goal_reached": goal.get("goal_reached_by_literal_tolerance"),
        "operations.goal_passed": goal.get(
            "goal_passed_by_literal_heading_and_window"
        ),
        "operations.backtracking_duration_s": route.get("backtracking_duration_s"),
        "operations.backtracking_distance_m": route.get("backtracking_distance_m"),
        "operations.distance_traveled_m": route.get("distance_traveled_m"),
    }
    if leaf_id in direct:
        value = direct[leaf_id]
        return (
            ("computed_descriptive", value, None)
            if value is not None
            else ("evidence_missing", None, "required_source_value_missing")
        )
    if leaf_id == "operations.travel_efficiency_ratio":
        distance = route.get("distance_traveled_m")
        forward = route.get("max_forward_m")
        if isinstance(distance, (int, float)) and distance > 0 and isinstance(
            forward, (int, float)
        ):
            return "computed_descriptive", float(forward / distance), None
        return "evidence_missing", None, "zero_or_missing_traveled_distance"
    for family, grid_key in (
        ("clearance_m", "clearance_grid"),
        ("ttc_s", "geometry_ttc_grid"),
        ("closing_mps", "closing_grid"),
        ("drac_mps2", "drac_grid"),
    ):
        prefix = f"safety.{family}_"
        if leaf_id.startswith(prefix):
            suffix = "duration_s" if leaf_id.endswith("duration_s") else "episode_count"
            for token, row in proximity.get(grid_key, {}).items():
                canonical_token = str(token).replace(".", "_").replace("-", "neg_")
                if f"_{canonical_token}" in leaf_id:
                    value = row["duration_s" if suffix == "duration_s" else "episode_count"]
                    return "computed_descriptive", value, None
    if leaf_id.startswith("operations.speed_excess_gt_"):
        for token, row in speed.get("tolerance_grid", {}).items():
            if f"_{str(token).replace('.', '_')}mps_" in leaf_id:
                return "computed_descriptive", row["duration_s"], None
    if leaf_id.startswith("operations.speed_excess_magnitude_above_"):
        for token, row in speed.get("tolerance_grid", {}).items():
            if f"_{str(token).replace('.', '_')}mps_" in leaf_id:
                return "computed_descriptive", row["magnitude_duration_m"], None
    if leaf_id.startswith("comfort.body_") and "_filtered_acceleration_" in leaf_id:
        axis = "longitudinal" if "body_longitudinal" in leaf_id else "lateral"
        stat = leaf_id.rsplit("_", 1)[-1]
        source = proxy.get("filtered_acceleration", {}).get(axis, {})
        if "_abs_gt_" in leaf_id:
            for token, row in proxy.get("filtered_acceleration", {}).get(
                "duration_abs_gt_s", {}
            ).items():
                if f"_{str(token).replace('.', '_')}mps2_" in leaf_id:
                    return "computed_descriptive", row[axis], None
        aliases = {
            "mean": "signed_mean",
            "signed_mean": "signed_mean",
            "rms": "rms",
            "min": "min",
            "max": "max",
            "peak_abs": "peak_abs",
            "p50": "abs_p50",
            "p90": "abs_p90",
            "p95": "abs_p95",
            "p99": "abs_p99",
        }
        key = next(
            (value for token, value in aliases.items() if leaf_id.endswith("_" + token)),
            None,
        )
        if key is not None and key in source:
            return "computed_descriptive", source[key], None
    if leaf_id.startswith("comfort.planar_kinematic_vdv_like_"):
        axis = "longitudinal" if leaf_id.endswith("_longitudinal") else "lateral"
        value = proxy.get("planar_kinematic_vdv_like", {}).get(axis)
        if value is not None:
            return "computed_descriptive", value, None
    if leaf_id.startswith("comfort.filtered_") and "_jerk_" in leaf_id:
        axis = "longitudinal" if "filtered_longitudinal" in leaf_id else "lateral"
        source = proxy.get("filtered_jerk", {}).get(axis, {})
        for token in ("rms", "peak_abs", "abs_p95"):
            if leaf_id.endswith("_" + token) and token in source:
                return "computed_descriptive", source[token], None
        if "_abs_gt_" in leaf_id:
            for token, row in proxy.get("filtered_jerk", {}).get(
                "duration_abs_gt_s", {}
            ).items():
                if f"_{str(token).replace('.', '_')}mps3_" in leaf_id:
                    return "computed_descriptive", row[axis], None
    if leaf_id.startswith("realtime.") and "_latency_" in leaf_id:
        for stage in (
            "pool_generation",
            "atoms",
            "context_weights",
            "selector_increment",
            "end_to_end",
        ):
            prefix = f"realtime.{stage}_latency_"
            if leaf_id.startswith(prefix):
                stat = leaf_id.removeprefix(prefix).removesuffix("_ms")
                row = latency.get(stage)
                if row is None:
                    return "scientifically_inapplicable", None, "stage_not_called_for_arm"
                return "computed_descriptive", row[stat], None
    if leaf_id.startswith("realtime.end_to_end_exceedance_rate_"):
        for budget, row in latency["budget"].items():
            token = budget.replace(".", "_")
            if f"_{token}ms" in leaf_id:
                return "computed_descriptive", row["exceedance_rate"], None
    if leaf_id.startswith("realtime.end_to_end_max_overrun_"):
        for budget, row in latency["budget"].items():
            token = budget.replace(".", "_")
            if f"_{token}ms_" in leaf_id:
                return "computed_descriptive", row["max_overrun_ms"], None
    if leaf_id in {
        "safety.collision_delta_v_mps",
        "safety.collision_contact_severity",
        "safety.time_headway_s",
        "safety.post_encroachment_time_s",
    } or leaf_id.startswith("operations.false_stop_"):
        return "evidence_missing", None, "industrial_v3_required_context_not_available"
    if "occupant" in leaf_id or "iso" in leaf_id.lower() or "sae" in leaf_id.lower():
        return "scientifically_inapplicable", None, "planar_proxy_is_not_occupant_conformity"
    return "evidence_missing", None, "bounded_receipt_transform_not_supported"


def evaluate(
    *,
    output: Path,
    execution_dir: Path,
    execution_root: str,
    execution_review_dir: Path,
    execution_review_root: str,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
    probe_config: Path,
) -> str:
    if output.resolve() != Path(EXACT_DIRS["evaluation"]):
        raise ValueError("evaluation exact dir drifted")
    execution = _verify_artifact(
        execution_dir, execution_root, "bounded execution"
    )
    _verify_artifact(
        execution_review_dir, execution_review_root, "bounded execution review"
    )
    industrial = _verify_artifact(
        industrial_contract_dir,
        industrial_contract_root,
        "accepted industrial v3 contract",
    )["contract"]
    if (
        execution.get("status")
        != "complete_full_denominator_hard_integrity_passed"
        or execution.get("denominator", {}).get("planned_ticks") != PLANNED_TICKS
    ):
        raise ValueError("evaluation requires complete bounded execution")
    config = object_from(probe_config)
    geometry = _load_root_bound_geometry(config)
    arm_summaries = {}
    arm_latencies = {}
    for arm in execution["arms"]:
        summary, latency = _arm_metrics(arm, config, geometry)
        arm_summaries[arm["arm"]] = summary
        arm_latencies[arm["arm"]] = latency
    leaves = []
    for leaf in industrial["scalar_leaf_registry"]:
        per_arm = {}
        statuses = []
        for arm in ARMS:
            status, value, reason = _lookup_leaf_value(
                leaf, arm_summaries[arm], arm_latencies[arm]
            )
            per_arm[arm] = {
                "status": status,
                "value": value,
                "reason": reason,
                "source_execution_root_sha256": execution_root,
            }
            statuses.append(status)
        leaves.append(
            {
                "leaf_id": leaf["leaf_id"],
                "parent_id": leaf["parent_id"],
                "domain": leaf["domain"],
                "units": leaf["units"],
                "direction": leaf["direction"],
                "formula": leaf["formula"],
                "opportunity_denominator": leaf["opportunity_denominator"],
                "evidence_class": leaf["evidence_class"],
                "per_arm": per_arm,
                "status": (
                    "computed_descriptive"
                    if all(item == "computed_descriptive" for item in statuses)
                    else (
                        "scientifically_inapplicable"
                        if all(item == "scientifically_inapplicable" for item in statuses)
                        else "evidence_missing"
                    )
                ),
                "inferential_status": "not_evaluable_bounded_single_cluster",
                "claim_gate_authorized": False,
            }
        )
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_bounded_evaluation_v1",
        "status": "sealed_bounded_descriptive_industrial_v3_vector",
        "authority_sha256": AUTHORITY_SHA256,
        "execution_binding": {
            "path": str(execution_dir.resolve()),
            "root_sha256": execution_root,
            "review_root_sha256": execution_review_root,
        },
        "industrial_contract_binding": {
            "path": str(industrial_contract_dir.resolve()),
            "root_sha256": industrial_contract_root,
        },
        "parent_endpoint_count": 56,
        "scalar_leaf_count": 161,
        "scalar_leaf_vector": leaves,
        "availability_counts": {
            status: sum(row["status"] == status for row in leaves)
            for status in (
                "computed_descriptive",
                "evidence_missing",
                "scientifically_inapplicable",
            )
        },
        "independent_cluster_count": 1,
        "inferential_status": "not_evaluable_bounded_single_cluster",
        "holm_iut_ni_or_benefit_inference_performed": False,
        "weighted_total_present": False,
        "legacy_safetycost_computed": False,
        "claim_authorized": False,
        "fresh_or_b4_outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
    }
    if [row["leaf_id"] for row in leaves] != scalar_leaf_ids():
        raise ValueError("evaluation scalar leaf exact topology drifted")
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_bounded_evaluation",
            "implementation_head": git_head(),
            "authority_sha256": AUTHORITY_SHA256,
            "execution_root_sha256": execution_root,
            "industrial_contract_root_sha256": industrial_contract_root,
        },
        label="V25 industrial-v3 bounded evaluation",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="stage", required=True)
    pre = subs.add_parser("preflight")
    for name in (
        "contract-dir",
        "contract-review-dir",
        "matrix-dir",
        "matrix-review-dir",
        "industrial-contract-dir",
        "training-dir",
        "training-review-dir",
    ):
        pre.add_argument("--" + name, type=Path, required=True)
    for name in (
        "contract-root",
        "contract-review-root",
        "matrix-root",
        "matrix-review-root",
        "industrial-contract-root",
        "training-root",
        "training-review-root",
    ):
        pre.add_argument("--" + name, required=True)
    pre.add_argument("--output", type=Path, required=True)
    pre.add_argument("--probe-config", type=Path, required=True)
    pre.add_argument("--fixed-dp-repo", type=Path, required=True)
    pre.add_argument("--forbidden-clone-inventory", type=Path, required=True)
    run = subs.add_parser("execute")
    for name in (
        "output",
        "preflight-dir",
        "preflight-review-dir",
        "probe-config",
        "training-dir",
        "training-review-dir",
        "fixed-dp-repo",
    ):
        run.add_argument("--" + name, type=Path, required=True)
    for name in (
        "preflight-root",
        "preflight-review-root",
        "training-root",
        "training-review-root",
    ):
        run.add_argument("--" + name, required=True)
    run.add_argument("--device", default="cuda")
    evaluate_parser = subs.add_parser("evaluate")
    for name in (
        "output",
        "execution-dir",
        "execution-review-dir",
        "industrial-contract-dir",
        "probe-config",
    ):
        evaluate_parser.add_argument("--" + name, type=Path, required=True)
    for name in (
        "execution-root",
        "execution-review-root",
        "industrial-contract-root",
    ):
        evaluate_parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    stage = args.stage
    kwargs = vars(args)
    kwargs.pop("stage")
    root = {"preflight": preflight, "execute": execute, "evaluate": evaluate}[
        stage
    ](**kwargs)
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
