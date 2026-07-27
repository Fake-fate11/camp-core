"""Run the V26 20-state, same-pool development profiling description.

The simulator advances candidate0 only.  Static9D, Scene9D, Static14D, and
Scene14D are counterfactual selectors of that exact frozen B8 pool, not
closed-loop arms and not effectiveness or safety evaluation.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Iterator, Mapping


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v21_native import array_sha256  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    PHI_DIMENSION,
    RAW_FEATURE_NAMES,
    context_weights,
    validate_column_simplex_theta,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    FIXED_DP_HEAD,
    TRAINED_SIMPLEX_NONNEGATIVE_ATOL,
    TRAINED_SIMPLEX_SUM_ATOL,
    training_parameter_array_sha256,
)
from camp_core.integrations.diffusion_planner_v26_development_profiling import (  # noqa: E402
    ACTIVE_ATOM_INDICES_BY_ARM,
    ATOM_PHASE_NAMES,
    ATOM_SET_BY_ARM,
    EVIDENCE_ROLE,
    OPERATIONAL_ARM,
    PROFILE_ARMS,
    PROFILE_STATE_COUNT,
    build_development_profiling_manifest,
    build_development_profiling_receipt,
)


MIN_FREE_BYTES = 10 * 1024**3


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


@contextmanager
def _exclusive_worker_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"V26 profiling worker lock already exists: {path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "role": EVIDENCE_ROLE}, handle)
            handle.flush()
        yield
    finally:
        path.unlink(missing_ok=True)


def _require_nonholdout_config(config: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(config)
    protocol = result.get("protocol")
    routes = result.get("routes")
    seeds = result.get("seeds")
    if type(protocol) is not dict or protocol.get("holdout_access_authorized") is not False:
        raise ValueError("V26 profiling rejects holdout identity")
    if protocol.get("route_role") != "development_nonholdout":
        raise ValueError("V26 profiling route role must be development_nonholdout")
    if type(routes) is not list or len(routes) != 1 or type(routes[0]) is not dict:
        raise ValueError("V26 profiling requires exactly one nonholdout route")
    if type(seeds) is not dict or type(seeds.get("scenario")) is not int:
        raise ValueError("V26 profiling scenario seed is required")
    fixed_dp = result.get("fixed_dp")
    if type(fixed_dp) is not dict:
        raise ValueError("V26 profiling fixed_dp config is required")
    for key in ("checkpoint", "args_json"):
        item = fixed_dp.get(key)
        if type(item) is not dict or type(item.get("path")) is not str or type(item.get("sha256")) is not str:
            raise ValueError(f"V26 profiling fixed_dp.{key} binding is required")
    return result


def _validate_file_binding(item: Mapping[str, Any], label: str) -> None:
    path = Path(str(item["path"]))
    if not path.is_file() or _file_sha256(path) != str(item["sha256"]):
        raise ValueError(f"V26 profiling {label} asset drifted")


def _require_simplex(value: Any, *, size: int, label: str):
    import numpy as np

    result = np.asarray(value)
    if result.shape != (size,) or result.dtype.kind not in "fiu" or result.dtype.kind == "b":
        raise ValueError(f"V26 profiling {label} must be numeric [{size}]")
    result = result.astype(np.float64, copy=False)
    if (
        not np.all(np.isfinite(result))
        or np.any(result < -TRAINED_SIMPLEX_NONNEGATIVE_ATOL)
        or not np.isclose(result.sum(), 1.0, rtol=0.0, atol=TRAINED_SIMPLEX_SUM_ATOL)
    ):
        raise ValueError(f"V26 profiling {label} violated its frozen simplex")
    return result.copy()


def _require_model_report(
    report: Mapping[str, Any], *, name: str, mode: str, atom_count: int, theta: Any
) -> None:
    if (
        type(report) is not dict
        or report.get("model_name") != name
        or report.get("mode") != mode
        or report.get("active_atom_indices") != list(range(atom_count))
        or report.get("theta_column_simplex") is not True
        or report.get("runtime_projection") is not False
        or report.get("softmax") is not False
        or report.get("outcome_or_fresh_consumed") is not False
        or report.get("theta_sha256") != training_parameter_array_sha256(theta)
    ):
        raise ValueError(f"V26 profiling {name} model report drifted")


@dataclass(frozen=True)
class _ProfilingSelectorAssets:
    """Verified V25 selectors used only for the explicit 9D/14D description."""

    atom_scales: Any
    static14d_weights: Any
    scene14d_weight_provider: Any
    static9d_weights: Any
    scene9d_theta: Any
    training_root_sha256: str
    training_review_root_sha256: str
    atom_scales_sha256: str
    static9d_weights_sha256: str
    scene9d_theta_sha256: str
    static14d_weights_sha256: str
    scene14d_theta_sha256: str
    context_scaler_sha256: str

    def scene9d_weights(self, context_payload: Mapping[str, Any]):
        import numpy as np

        raw_context = context_payload.get("raw_context")
        source_complete = context_payload.get("source_complete")
        if type(raw_context) is not dict or type(source_complete) is not dict:
            raise ValueError("V26 profiling Scene9D context payload drifted")
        raw = np.asarray([raw_context[name] for name in RAW_FEATURE_NAMES], dtype=np.float64)
        source = np.asarray([source_complete[name] for name in RAW_FEATURE_NAMES], dtype=np.bool_)
        phi = self.scene14d_weight_provider.context_scaler.lift(
            raw, source_complete=source
        )
        weights = context_weights(self.scene9d_theta, phi)
        return _require_simplex(weights, size=9, label="Scene9D runtime weights")


def _load_profiling_selector_assets(args: argparse.Namespace) -> _ProfilingSelectorAssets:
    import numpy as np
    from camp_core.integrations import diffusion_planner_v25_scene_runtime as scene_runtime

    primary = scene_runtime.load_v25_runtime_selector_assets(
        training_artifact=args.training.resolve(),
        training_root_sha256=args.training_root,
        training_review_artifact=args.training_review.resolve(),
        training_review_root_sha256=args.training_review_root,
    )
    parameter_path = args.training.resolve() / "model_parameters.npz"
    with np.load(parameter_path, allow_pickle=False) as archive:
        static9 = _require_simplex(
            archive["static9d_runtime_weights"], size=9, label="Static9D runtime weights"
        )
        static9_theta = np.asarray(archive["static9d_theta"], dtype=np.float64)
        scene9_theta = np.asarray(archive["scene9d_theta"], dtype=np.float64)
    if static9_theta.shape != (9, PHI_DIMENSION) or not np.all(np.isfinite(static9_theta)):
        raise ValueError("V26 profiling Static9D theta drifted")
    if not np.array_equal(static9, static9_theta[:, 0]):
        raise ValueError("V26 profiling Static9D runtime weights drifted from theta")
    scene9_theta = validate_column_simplex_theta(scene9_theta, num_atoms=9, atol=1e-10)
    if np.any(scene9_theta < 0.0):
        raise ValueError("V26 profiling Scene9D theta must be exactly nonnegative")
    reports = json.loads((args.training.resolve() / "model_reports.json").read_text(encoding="utf-8"))
    if type(reports) is not dict:
        raise ValueError("V26 profiling model reports must be an object")
    _require_model_report(
        reports.get("CAMP-Static9D"),
        name="CAMP-Static9D",
        mode="static",
        atom_count=9,
        theta=static9_theta,
    )
    _require_model_report(
        reports.get("CAMP-Scene9D"),
        name="CAMP-Scene9D",
        mode="scene",
        atom_count=9,
        theta=scene9_theta,
    )
    scene14_theta = np.asarray(primary.scene14d_weight_provider.theta, dtype=np.float64)
    return _ProfilingSelectorAssets(
        atom_scales=np.asarray(primary.atom_scales, dtype=np.float64).copy(),
        static14d_weights=np.asarray(primary.static14d_weights, dtype=np.float64).copy(),
        scene14d_weight_provider=primary.scene14d_weight_provider,
        static9d_weights=static9.copy(),
        scene9d_theta=scene9_theta.copy(),
        training_root_sha256=primary.training_root_sha256,
        training_review_root_sha256=primary.training_review_root_sha256,
        atom_scales_sha256=array_sha256(np.asarray(primary.atom_scales, dtype=np.float64)),
        static9d_weights_sha256=array_sha256(static9),
        scene9d_theta_sha256=array_sha256(scene9_theta),
        static14d_weights_sha256=array_sha256(np.asarray(primary.static14d_weights, dtype=np.float64)),
        scene14d_theta_sha256=array_sha256(scene14_theta),
        context_scaler_sha256=str(primary.scene14d_weight_provider.context_scaler_sha256),
    )


def _prepare_manifest(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], _ProfilingSelectorAssets]:
    if _tracked_changes(ROOT):
        raise ValueError("V26 profiling requires an exact clean CAMP checkout")
    config_path = args.probe_config.resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    config = _require_nonholdout_config(json.loads(config_path.read_text(encoding="utf-8")))
    route = dict(config["routes"][0])
    if type(route.get("path")) is not str or type(route.get("sha256")) is not str:
        raise ValueError("V26 profiling route binding is required")
    _validate_file_binding(route, "route")
    map_binding = config.get("map")
    if type(map_binding) is not dict:
        raise ValueError("V26 profiling map binding is required")
    _validate_file_binding(map_binding, "map")
    fixed_dp = dict(config["fixed_dp"])
    _validate_file_binding(fixed_dp["checkpoint"], "checkpoint")
    _validate_file_binding(fixed_dp["args_json"], "args")
    fixed_dp_repo = args.fixed_dp_repo.resolve()
    if _tracked_changes(fixed_dp_repo):
        raise ValueError("V26 profiling requires an exact clean fixed-DP checkout")
    if _git_head(fixed_dp_repo) != FIXED_DP_HEAD:
        raise ValueError("V26 profiling fixed-DP head drifted")
    assets = _load_profiling_selector_assets(args)
    manifest = build_development_profiling_manifest(
        camp_head=_git_head(ROOT),
        probe_config_sha256=_file_sha256(config_path),
        route_sha256=str(route["sha256"]),
        scenario_seed=int(config["seeds"]["scenario"]),
        spawn_config=dict(config["spawn_config"]),
        fixed_dp_head=FIXED_DP_HEAD,
        checkpoint_path=str(fixed_dp["checkpoint"]["path"]),
        checkpoint_sha256=str(fixed_dp["checkpoint"]["sha256"]),
        args_path=str(fixed_dp["args_json"]["path"]),
        args_sha256=str(fixed_dp["args_json"]["sha256"]),
        training_root_sha256=assets.training_root_sha256,
        training_review_root_sha256=assets.training_review_root_sha256,
        atom_scales_sha256=assets.atom_scales_sha256,
        static9d_weights_sha256=assets.static9d_weights_sha256,
        scene9d_theta_sha256=assets.scene9d_theta_sha256,
        static14d_weights_sha256=assets.static14d_weights_sha256,
        scene14d_theta_sha256=assets.scene14d_theta_sha256,
        context_scaler_sha256=assets.context_scaler_sha256,
    )
    return manifest, config, assets


def _resource_precheck(output_dir: Path, device: str, torch: Any) -> None:
    if device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("V26 profiling requires an available CUDA GPU")
    if shutil.disk_usage(output_dir.parent).free < MIN_FREE_BYTES:
        raise RuntimeError("V26 profiling requires at least 10 GiB free disk")
    probe = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if probe.returncode:
        raise RuntimeError("V26 profiling cannot verify GPU conflict via nvidia-smi")
    if any(line.strip() for line in probe.stdout.splitlines()):
        raise RuntimeError("V26 profiling GPU conflict detected before model load")


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        staging.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def _zero_forward_calls(*, before: int = 0, after: int = 0, primary: int = 0) -> dict[str, int]:
    return {
        "model_call_count_before": before,
        "model_call_count_after": after,
        "model_call_delta": primary,
        "primary_forward_count": primary,
        "sequential_forward_count": 0,
        "post_pool_model_forward_count": 0,
        "post_pool_dp_forward_count": 0,
        "post_pool_latent_replacement_count": 0,
        "post_pool_candidate_generation_count": 0,
        "candidate_pool_mutation_count": 0,
        "trajectory_regeneration_count": 0,
    }


def _arm_receipt(raw: Mapping[str, Any], arm_id: str, rows: list[str]) -> dict[str, Any]:
    source = dict(raw)
    status = str(source.get("status"))
    selected = source.get("selected_index")
    source_mask = [bool(value) for value in source["source_valid_mask"]]
    physical_mask = [bool(value) for value in source["physical_feasible_mask"]]
    if arm_id == OPERATIONAL_ARM:
        return {
            "arm_id": arm_id,
            "atom_set": ATOM_SET_BY_ARM[arm_id],
            "active_atom_indices": ACTIVE_ATOM_INDICES_BY_ARM[arm_id],
            "weights_sha256": None,
            "scoring_weights_sha256": None,
            "weight_parameter_sha256": None,
            "status": "ok",
            "failure_reason": None,
            "selected_index": 0,
            "selected_row_sha256": rows[0],
            "scores": None,
            "physical_feasible_mask": physical_mask,
            "source_valid_mask": source_mask,
            "eligible_count": int(sum(source_mask)),
            "margin_best_vs_runner_up": None,
            "exact_tie_set": [0],
            "weight_input_source_complete": None,
        }
    context = source.get("context")
    source_complete = None
    if arm_id.startswith("Scene"):
        if type(context) is not dict or type(context.get("source_complete")) is not dict:
            raise ValueError(f"V26 profiling {arm_id} context receipt is missing")
        source_complete = {key: bool(value) for key, value in context["source_complete"].items()}
    return {
        "arm_id": arm_id,
        "atom_set": ATOM_SET_BY_ARM[arm_id],
        "active_atom_indices": ACTIVE_ATOM_INDICES_BY_ARM[arm_id],
        "weights_sha256": source.get("weights_sha256"),
        "scoring_weights_sha256": source.get("scoring_weights_sha256"),
        "weight_parameter_sha256": source.get("weight_parameter_sha256"),
        "status": status,
        "failure_reason": source.get("failure_reason"),
        "selected_index": None if selected is None else int(selected),
        "selected_row_sha256": source.get("selected_row_sha256"),
        "scores": None if source.get("scores") is None else [float(value) for value in source["scores"]],
        "physical_feasible_mask": physical_mask,
        "source_valid_mask": source_mask,
        "eligible_count": int(source["eligible_count"]),
        "margin_best_vs_runner_up": source.get("margin_best_vs_runner_up"),
        "exact_tie_set": source.get("exact_tie_set"),
        "weight_input_source_complete": source_complete,
    }


class _ProfilingPredictBatch:
    """Thin V26 profile adapter over the fixed-DP B8 callback."""

    def __new__(cls, *args: Any, **kwargs: Any):
        from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import _FairPredictBatch

        class Implementation(_FairPredictBatch):
            def __init__(self, *inner_args: Any, profiling_assets: _ProfilingSelectorAssets, **inner_kwargs: Any) -> None:
                self.profiling_assets = profiling_assets
                super().__init__(*inner_args, **inner_kwargs)

            @staticmethod
            def _pad_9d(weights: Any):
                import numpy as np

                result = np.zeros(14, dtype=np.float64)
                result[:9] = np.asarray(weights, dtype=np.float64)
                return result

            @staticmethod
            def _tie_and_margin(scores: Any, source_mask: Any) -> tuple[list[int] | None, float | None]:
                import numpy as np

                if scores is None:
                    return None, None
                values = np.asarray(scores, dtype=np.float64)
                mask = np.asarray(source_mask, dtype=np.bool_)
                ordered = sorted((float(values[index]), int(index)) for index in np.flatnonzero(mask))
                if not ordered:
                    return None, None
                best = ordered[0][0]
                return (
                    [index for score, index in ordered if score == best],
                    None if len(ordered) < 2 else float(ordered[1][0] - best),
                )

            def _profile_selector(self, *, arm_id: str, candidates: Any, materialized: Mapping[str, Any], weights: Any, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
                import numpy as np

                selection_started = time.perf_counter_ns()
                selection = self.select_candidate(
                    candidates=candidates,
                    materialized=materialized,
                    atom_scales=self.profiling_assets.atom_scales,
                    weights=weights,
                    eligibility_mask_name="source_valid_mask",
                    simplex_nonnegative_atol=TRAINED_SIMPLEX_NONNEGATIVE_ATOL,
                )
                selector_latency_ms = (time.perf_counter_ns() - selection_started) / 1e6
                source_mask = np.asarray(selection["source_valid_mask"], dtype=np.bool_)
                tie_set, margin = self._tie_and_margin(selection.get("scores"), source_mask)
                result = {
                    "status": str(selection["status"]),
                    "failure_reason": selection.get("failure_reason"),
                    "selected_index": selection.get("selected_index"),
                    "selected_row_sha256": None if selection.get("selected_index") is None else array_sha256(candidates[int(selection["selected_index"])]),
                    "scores": None if selection.get("scores") is None else np.asarray(selection["scores"], dtype=np.float64).tolist(),
                    "physical_feasible_mask": np.asarray(selection["physical_feasible_mask"], dtype=np.bool_).tolist(),
                    "source_valid_mask": source_mask.tolist(),
                    "weights_sha256": array_sha256(np.asarray(weights[:9], dtype=np.float64)),
                    "scoring_weights_sha256": array_sha256(np.asarray(weights, dtype=np.float64)),
                    "weight_parameter_sha256": (
                        self.profiling_assets.static9d_weights_sha256
                        if arm_id == "Static9D"
                        else self.profiling_assets.scene9d_theta_sha256
                    ),
                    "selector_latency_ms": selector_latency_ms,
                    "eligible_count": int(np.count_nonzero(source_mask)),
                    "margin_best_vs_runner_up": margin,
                    "exact_tie_set": tie_set,
                    "tie_break_contract": "lowest_eligible_candidate_index",
                    "atom_set": ATOM_SET_BY_ARM[arm_id],
                    "active_atom_indices": ACTIVE_ATOM_INDICES_BY_ARM[arm_id],
                }
                if context is not None:
                    result["context"] = dict(context)
                return result

            def _evaluate_pool(self, *, candidates: Any, neighbors: Any, causal: Mapping[str, Any] | None, neighbor_valid: Any, signals: Any, red_cost: Any, causal_signal_atom_input: Mapping[str, Any] | None, evaluate_arms: list[str]) -> dict[str, Any]:
                import numpy as np

                if tuple(evaluate_arms) != PROFILE_ARMS:
                    raise ValueError("V26 profiling requires the exact five-arm inventory")
                before = array_sha256(candidates)
                result = super()._evaluate_pool(
                    candidates=candidates,
                    neighbors=neighbors,
                    causal=causal,
                    neighbor_valid=neighbor_valid,
                    signals=signals,
                    red_cost=red_cost,
                    causal_signal_atom_input=causal_signal_atom_input,
                    evaluate_arms=[OPERATIONAL_ARM, "Static14D", "Scene14D"],
                )
                materialized = result["materialized"]
                if materialized is None:
                    raise ValueError("V26 profiling requires canonical atom materialization")
                context = result["summary"].get("context")
                if type(context) is not dict:
                    raise ValueError("V26 profiling requires one shared scene context")
                static9 = self._pad_9d(self.profiling_assets.static9d_weights)
                scene9 = self._pad_9d(self.profiling_assets.scene9d_weights(context))
                result["arms"]["Static9D"] = self._profile_selector(
                    arm_id="Static9D",
                    candidates=candidates,
                    materialized=materialized,
                    weights=static9,
                )
                result["arms"]["Scene9D"] = self._profile_selector(
                    arm_id="Scene9D",
                    candidates=candidates,
                    materialized=materialized,
                    weights=scene9,
                    context=context,
                )
                for arm_id in ("Static14D", "Scene14D"):
                    arm = result["arms"][arm_id]
                    arm["atom_set"] = ATOM_SET_BY_ARM[arm_id]
                    arm["active_atom_indices"] = ACTIVE_ATOM_INDICES_BY_ARM[arm_id]
                    arm["scoring_weights_sha256"] = arm["weights_sha256"]
                    arm["weight_parameter_sha256"] = (
                        self.profiling_assets.static14d_weights_sha256
                        if arm_id == "Static14D"
                        else self.profiling_assets.scene14d_theta_sha256
                    )
                    if arm_id == "Scene14D":
                        arm["context"] = dict(context)
                baseline = result["arms"][OPERATIONAL_ARM]
                baseline["atom_set"] = ATOM_SET_BY_ARM[OPERATIONAL_ARM]
                baseline["active_atom_indices"] = ACTIVE_ATOM_INDICES_BY_ARM[OPERATIONAL_ARM]
                baseline["eligible_count"] = int(np.count_nonzero(baseline["source_valid_mask"]))
                baseline["margin_best_vs_runner_up"] = None
                baseline["exact_tie_set"] = [0]
                result["latency_ms"]["selector_incremental"] = float(
                    sum(arm.get("selector_latency_ms") or 0.0 for arm in result["arms"].values())
                )
                if array_sha256(candidates) != before:
                    raise ValueError("V26 profiling selector mutated frozen pool")
                return result

        return Implementation(*args, **kwargs)


def _completed_unit(raw: Mapping[str, Any], callback: Any, *, unit_index: int, manifest: Mapping[str, Any]) -> dict[str, Any]:
    if raw.get("status") != "ok":
        raise ValueError("V26 profiling completed unit requires a successful runtime tick")
    rows = [str(item) for item in raw["candidate_row_sha256"]]
    if raw.get("candidate_tensor_sha256_before") != raw.get("candidate_tensor_sha256_after"):
        raise ValueError("V26 profiling pool changed after forward")
    zero = dict(raw["zero_call_receipt"])
    if any(int(zero.get(key, -1)) != 0 for key in ("dp_or_model_calls_after_pool", "latent_replacements_after_pool", "candidate_generations_after_pool")):
        raise ValueError("V26 profiling zero-call receipt drifted")
    primary = int(raw["primary_pool_model_call_count"])
    after = int(callback.model_call_count)
    before = after - primary
    if primary != 1 or before < 0:
        raise ValueError("V26 profiling primary B8 forward count drifted")
    raw_arms = raw["real_selector_receipts"]
    if type(raw_arms) is not dict or set(raw_arms) != set(PROFILE_ARMS):
        raise ValueError("V26 profiling runtime five-arm receipts are missing")
    arms = {arm_id: _arm_receipt(raw_arms[arm_id], arm_id, rows) for arm_id in PROFILE_ARMS}
    comparisons = {
        "selection_disagrees_with_candidate0": {
            arm_id: None if arms[arm_id]["status"] != "ok" else bool(arms[arm_id]["selected_index"] != 0)
            for arm_id in ("Static9D", "Scene9D", "Static14D", "Scene14D")
        },
        "static9d_vs_static14d_flip": None if arms["Static9D"]["status"] != "ok" or arms["Static14D"]["status"] != "ok" else bool(arms["Static9D"]["selected_index"] != arms["Static14D"]["selected_index"]),
        "scene9d_vs_scene14d_flip": None if arms["Scene9D"]["status"] != "ok" or arms["Scene14D"]["status"] != "ok" else bool(arms["Scene9D"]["selected_index"] != arms["Scene14D"]["selected_index"]),
    }
    phase = dict(raw["materialized_summary"].get("atom_materialization_phase_receipt", {}))
    if set(phase) != set(ATOM_PHASE_NAMES):
        raise ValueError("V26 profiling atom phase timing receipt is missing")
    metadata = dict(raw["same_ego_batch_metadata"])
    if int(raw["selected_index"]) != 0 or raw["selected_trajectory_sha256"] != rows[0]:
        raise ValueError("V26 profiling simulator did not retain candidate0 progression")
    return {
        "unit_index": unit_index,
        "planned_state_id_sha256": manifest["state_plan"][unit_index]["planned_state_id_sha256"],
        "state_sha256": str(raw["state_sha256"]),
        "input": {
            "source_input_sha256": str(raw["source_input_sha256"]),
            "expanded_input_sha256": str(raw["input_sha256"]),
            "same_ego_batch_size": int(metadata["same_ego_batch_size"]),
            "nonlatent_rows_identical": bool(metadata["nonlatent_rows_identical"]),
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
        "arms": arms,
        "comparison": comparisons,
        "atom_phase_timings": phase,
        "simulator": {"operational_arm": OPERATIONAL_ARM, "selected_index": 0, "selected_row_sha256": rows[0]},
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
    }


def _noncomplete_unit(
    *,
    unit_index: int,
    manifest: Mapping[str, Any],
    status: str,
    failure_class: str | None = None,
    failure_reason: str | None = None,
    raw: Mapping[str, Any] | None = None,
    callback: Any | None = None,
) -> dict[str, Any]:
    if status not in {"typed_failure", "unattempted"}:
        raise ValueError("unknown V26 profiling terminal status")
    after = 0 if callback is None else int(callback.model_call_count)
    primary = 0 if raw is None else int(raw.get("primary_pool_model_call_count", 0))
    return {
        "unit_index": unit_index,
        "planned_state_id_sha256": manifest["state_plan"][unit_index]["planned_state_id_sha256"],
        "state_sha256": None if raw is None else raw.get("state_sha256"),
        "input": None,
        "latent": None,
        "candidate_pool": None,
        "forward_calls": _zero_forward_calls(before=max(0, after - primary), after=after, primary=primary),
        "arms": None,
        "comparison": None,
        "atom_phase_timings": None,
        "simulator": None,
        "terminal": {
            "status": status,
            "failure_class": failure_class if status == "typed_failure" else None,
            "failure_reason": failure_reason if status == "typed_failure" else None,
        },
    }


class _IncrementalLedger:
    def __init__(self, *, output_dir: Path, manifest: Mapping[str, Any]) -> None:
        self.output_dir = output_dir.resolve()
        if self.output_dir.exists():
            raise FileExistsError(f"V26 profiling output already exists: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.manifest = dict(manifest)
        self.units: list[dict[str, Any] | None] = [None] * PROFILE_STATE_COUNT
        _atomic_write_json(self.output_dir / "manifest.json", self.manifest)
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {"evidence_role": EVIDENCE_ROLE, "status": "running", "planned": PROFILE_STATE_COUNT},
        )

    def record(self, unit: Mapping[str, Any]) -> None:
        index = int(unit["unit_index"])
        if self.units[index] is not None:
            raise ValueError("V26 profiling unit ledger was already recorded")
        materialized = dict(unit)
        self.units[index] = materialized
        _atomic_write_json(self.output_dir / "units" / f"{index:02d}.json", materialized)

    def finalize(self, *, native_result: Mapping[str, Any]) -> Path:
        first_missing = next((index for index, unit in enumerate(self.units) if unit is None), None)
        if first_missing is not None:
            failure_class = native_result.get("failure_class")
            failure_reason = native_result.get("failure_reason")
            if type(failure_class) is str and failure_class and type(failure_reason) is str and failure_reason:
                self.record(
                    _noncomplete_unit(
                        unit_index=first_missing,
                        manifest=self.manifest,
                        status="typed_failure",
                        failure_class=failure_class,
                        failure_reason=failure_reason,
                    )
                )
        for index, unit in enumerate(self.units):
            if unit is None:
                self.record(
                    _noncomplete_unit(
                        unit_index=index,
                        manifest=self.manifest,
                        status="unattempted",
                    )
                )
        receipt = build_development_profiling_receipt(
            manifest=self.manifest,
            units=[unit for unit in self.units if unit is not None],
        )
        _atomic_write_json(self.output_dir / "native_result.json", dict(native_result))
        _atomic_write_json(self.output_dir / "raw_receipt.json", receipt)
        _atomic_write_json(self.output_dir / "summary.json", receipt["descriptive_summary"])
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {"evidence_role": EVIDENCE_ROLE, "status": "terminal", "denominator": receipt["denominator"]},
        )
        (self.output_dir / "run.exit").write_bytes(b"0\n")
        return self.output_dir / "raw_receipt.json"


def _run_profiled_states(
    *,
    config: Mapping[str, Any],
    model: Any,
    model_args: Any,
    tensor_converter: Any,
    replay: Any,
    builder_type: Any,
    route_type: Any,
    fixed_dp_repo: Path,
    assets: _ProfilingSelectorAssets,
    device: str,
    scratch_parent: Path,
    on_completed_unit: Callable[[Mapping[str, Any], Any], None],
) -> tuple[list[dict[str, Any]], Any, dict[str, Any]]:
    from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import (
        NativeHookState,
        _RequestedStateCountReached,
        _build_no_signal_chain,
        patched_native_replay,
    )

    builder = builder_type(str(config["map"]["path"]))
    route_spec = config["routes"][0]
    route = route_type.load(Path(route_spec["path"]))
    route_ids = list(route.route_lanelet_ids or ())
    if not route_ids:
        raise ValueError("V26 profiling route is unresolved")
    causal_signal_chain = _build_no_signal_chain(
        builder=builder,
        route_ids=route_ids,
        map_sha256=str(config["map"]["sha256"]),
        route_sha256=str(route_spec["sha256"]),
    )
    spawn = replay.SpawnConfig(**dict(config["spawn_config"]))
    spawn.max_steps = PROFILE_STATE_COUNT
    spawn.validate()
    state = NativeHookState()
    callback = _ProfilingPredictBatch(
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
        max_ticks=PROFILE_STATE_COUNT,
        operational_arm=OPERATIONAL_ARM,
        evaluate_all_arms=False,
        adaptation_diagnostics=False,
        causal_signal_chain=causal_signal_chain,
        evaluation_arms=PROFILE_ARMS,
        record_materialization_phases=True,
        profiling_assets=assets,
    )

    def after_tracker(receipt: dict[str, Any], _scene: Any) -> None:
        on_completed_unit(receipt, callback)

    scratch = Path(tempfile.mkdtemp(prefix=".v26_profiling.", dir=str(scratch_parent)))
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
                native_result = {"reason": "requested_state_count_reached", "goal_reached": False}
            except Exception as exc:
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
    return state.receipts, callback, dict(native_result)


def run(args: argparse.Namespace) -> Path:
    output_dir = args.output_dir.resolve()
    with _exclusive_worker_lock(args.worker_lock.resolve()):
        manifest, config, assets = _prepare_manifest(args)
        ledger = _IncrementalLedger(output_dir=output_dir, manifest=manifest)
        import torch

        _resource_precheck(output_dir, args.device, torch)
        fixed_dp_repo = args.fixed_dp_repo.resolve()
        for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from camp_core.integrations.diffusion_planner import (
            install_lanelet2_projection_fallback,
            require_source_preserving_lanelet2_regulatory_adapter,
        )
        from scripts.integrations.run_diffusion_planner_camp_replay import _load_model
        from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
            _install_fixed_dp_annotation_compatibility,
        )
        import scenario_generation.replay as replay
        import scenario_generation.tensor_converter as tensor_converter
        from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
        from scenario_generation.route import Route

        _install_fixed_dp_annotation_compatibility(fixed_dp_repo)
        map_path = Path(config["map"]["path"])
        require_source_preserving_lanelet2_regulatory_adapter(map_path)
        install_lanelet2_projection_fallback(map_path)
        model, model_args = _load_model(
            Path(config["fixed_dp"]["checkpoint"]["path"]),
            Path(config["fixed_dp"]["args_json"]["path"]),
            args.device,
        )
        model.eval()

        def on_completed(raw: Mapping[str, Any], callback: Any) -> None:
            ledger.record(
                _completed_unit(
                    raw,
                    callback,
                    unit_index=int(raw["tick_index"]),
                    manifest=manifest,
                )
            )

        receipts, callback, native_result = _run_profiled_states(
            config=config,
            model=model,
            model_args=model_args,
            tensor_converter=tensor_converter,
            replay=replay,
            builder_type=LaneletSceneBuilder,
            route_type=Route,
            fixed_dp_repo=fixed_dp_repo,
            assets=assets,
            device=args.device,
            scratch_parent=output_dir.parent,
            on_completed_unit=on_completed,
        )
        for raw in receipts:
            index = int(raw["tick_index"])
            if ledger.units[index] is None:
                ledger.record(
                    _noncomplete_unit(
                        unit_index=index,
                        manifest=manifest,
                        status="typed_failure",
                        failure_class=str(native_result.get("failure_class", "RuntimeFailure")),
                        failure_reason=str(native_result.get("failure_reason", raw.get("status", "unknown"))),
                        raw=raw,
                        callback=callback,
                    )
                )
        return ledger.finalize(native_result=native_result)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--worker-lock", type=Path, required=True)
    parser.add_argument("--probe-config", type=Path, required=True)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--training-root", required=True)
    parser.add_argument("--training-review", type=Path, required=True)
    parser.add_argument("--training-review-root", required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    receipt = run(parse_args(argv))
    print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
