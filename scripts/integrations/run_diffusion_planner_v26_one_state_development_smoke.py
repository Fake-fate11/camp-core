"""Run one nonholdout, same-ego B8 Static14D capability smoke for V26."""

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
from typing import Any, Iterator, Mapping


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v26_one_state_development_smoke import (  # noqa: E402
    EVIDENCE_ROLE,
    SMOKE_ARM,
    build_development_smoke_manifest,
    build_development_smoke_receipt,
)
from camp_core.integrations.diffusion_planner_v26_target_bounded_surface import (  # noqa: E402
    PRODUCTION_SURFACE_ID,
    validate_target_bounded_tick_receipt,
)


MIN_FREE_BYTES = 10 * 1024**3
V26_TARGET_OPTIONS = {
    "adaptation_diagnostics": False,
    "sequential_forward_enabled": False,
    "replay_extra_forward_enabled": False,
    "guidance_policy": "disabled",
    "evaluate_all_arms": False,
}


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
        raise RuntimeError(f"V26 smoke worker lock already exists: {path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "role": EVIDENCE_ROLE}, handle)
            handle.flush()
        yield
    finally:
        path.unlink(missing_ok=True)


def _require_single_nonholdout_config(config: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(config)
    protocol = result.get("protocol")
    routes = result.get("routes")
    seeds = result.get("seeds")
    if type(protocol) is not dict or protocol.get("holdout_access_authorized") is not False:
        raise ValueError("V26 smoke rejects holdout identity")
    if "holdout" in str(protocol.get("route_role", "")).lower():
        raise ValueError("V26 smoke route role must be nonholdout")
    if type(routes) is not list or len(routes) != 1 or type(routes[0]) is not dict:
        raise ValueError("V26 smoke requires exactly one nonholdout route")
    if type(seeds) is not dict or type(seeds.get("scenario")) is not int:
        raise ValueError("V26 smoke scenario seed is required")
    fixed_dp = result.get("fixed_dp")
    if type(fixed_dp) is not dict:
        raise ValueError("V26 smoke fixed_dp config is required")
    for key in ("checkpoint", "args_json"):
        item = fixed_dp.get(key)
        if type(item) is not dict or type(item.get("path")) is not str or type(item.get("sha256")) is not str:
            raise ValueError(f"V26 smoke fixed_dp.{key} binding is required")
    return result


def _validate_file_binding(item: Mapping[str, Any], label: str) -> None:
    path = Path(str(item["path"]))
    if not path.is_file() or _file_sha256(path) != str(item["sha256"]):
        raise ValueError(f"V26 smoke {label} asset drifted")


def _prepare_manifest(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], Any]:
    if _tracked_changes(ROOT):
        raise ValueError("V26 smoke requires an exact clean CAMP checkout")
    config_path = args.probe_config.resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    config = _require_single_nonholdout_config(
        json.loads(config_path.read_text(encoding="utf-8"))
    )
    route = dict(config["routes"][0])
    if type(route.get("path")) is not str or type(route.get("sha256")) is not str:
        raise ValueError("V26 smoke route binding is required")
    _validate_file_binding(route, "route")
    map_binding = config.get("map")
    if type(map_binding) is not dict:
        raise ValueError("V26 smoke map binding is required")
    _validate_file_binding(map_binding, "map")
    fixed_dp = dict(config["fixed_dp"])
    _validate_file_binding(fixed_dp["checkpoint"], "checkpoint")
    _validate_file_binding(fixed_dp["args_json"], "args")

    fixed_dp_repo = args.fixed_dp_repo.resolve()
    if _tracked_changes(fixed_dp_repo):
        raise ValueError("V26 smoke requires an exact clean fixed-DP checkout")
    from camp_core.integrations.diffusion_planner_v25_fair_nonholdout import (
        FIXED_DP_HEAD,
        array_sha256,
        load_v25_runtime_selector_assets,
    )

    if _git_head(fixed_dp_repo) != FIXED_DP_HEAD:
        raise ValueError("V26 smoke fixed-DP head drifted")
    assets = load_v25_runtime_selector_assets(
        training_artifact=args.training.resolve(),
        training_root_sha256=args.training_root,
        training_review_artifact=args.training_review.resolve(),
        training_review_root_sha256=args.training_review_root,
    )
    import numpy as np

    manifest = build_development_smoke_manifest(
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
        training_root_sha256=args.training_root,
        training_review_root_sha256=args.training_review_root,
        atom_scales_sha256=array_sha256(
            np.asarray(assets.atom_scales, dtype=np.float64)
        ),
        static14d_weights_sha256=array_sha256(
            np.asarray(assets.static14d_weights, dtype=np.float64)
        ),
    )
    return manifest, config, assets


def _resource_precheck(output_dir: Path, device: str, torch: Any) -> None:
    if device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("V26 one-state smoke requires an available CUDA GPU")
    if shutil.disk_usage(output_dir.parent).free < MIN_FREE_BYTES:
        raise RuntimeError("V26 one-state smoke requires at least 10 GiB free disk")
    probe = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if probe.returncode:
        raise RuntimeError("V26 smoke cannot verify GPU conflict via nvidia-smi")
    if any(line.strip() for line in probe.stdout.splitlines()):
        raise RuntimeError("V26 smoke GPU conflict detected before model load")


def _atomic_write_ledger(output_dir: Path, receipt: Mapping[str, Any]) -> Path:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"V26 smoke output already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging.", dir=output_dir.parent))
    try:
        (staging / "ledger.json").write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(staging, output_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return output_dir / "ledger.json"


def _completed_unit(raw: Mapping[str, Any], callback: Any) -> dict[str, Any]:
    import numpy as np

    v26_tick = validate_target_bounded_tick_receipt(
        raw["v26_production_surface_receipt"]
    )
    if (
        v26_tick["production_surface_id"] != PRODUCTION_SURFACE_ID
        or v26_tick["selector"]["operational_arm"] != SMOKE_ARM
        or len(callback.primary_candidates) != 1
    ):
        raise ValueError("V26 one-state smoke runtime surface drifted")
    candidates = np.asarray(callback.primary_candidates[0])
    rows = [str(item) for item in raw["candidate_row_sha256"]]
    selector = dict(v26_tick["selector"])
    simulator = dict(v26_tick["simulator_selected_row"])
    metadata = dict(raw["same_ego_batch_metadata"])
    forward = dict(v26_tick["forward_topology"])
    return {
        "unit_index": 0,
        "operational_arm": SMOKE_ARM,
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
            "shape": list(candidates.shape),
            "dtype": str(candidates.dtype),
            "finite": bool(np.isfinite(candidates).all()),
            "pool_sha256": str(raw["candidate_tensor_sha256_after"]),
            "row_sha256": rows,
            "candidate0": {
                "index": 0,
                "row_sha256": rows[0],
                "default_output_sha256": str(raw["default_output_sha256"]),
            },
        },
        "forward_calls": {
            "model_call_count_before": 0,
            "model_call_count_after": int(callback.model_call_count),
            "model_call_delta": int(callback.model_call_count),
            "primary_forward_count": int(forward["primary_forward_count"]),
            "sequential_forward_count": int(forward["sequential_forward_count"]),
            "post_pool_model_forward_count": int(forward["post_pool_model_forward_count"]),
            "post_pool_dp_forward_count": int(forward["post_pool_dp_forward_count"]),
            "post_pool_latent_replacement_count": int(
                forward["post_pool_latent_replacement_count"]
            ),
            "post_pool_candidate_generation_count": int(
                forward["post_pool_candidate_generation_count"]
            ),
            "candidate_pool_mutation_count": int(
                v26_tick["candidate_pool"]["candidate_pool_mutation_count"]
            ),
            "trajectory_regeneration_count": int(
                forward["trajectory_regeneration_count"]
            ),
        },
        "selection": {
            "selected_index": int(selector["selected_index"]),
            "selected_row_sha256": str(selector["selected_row_sha256"]),
        },
        "simulator": {"selected_row_sha256": str(simulator["simulator_row_sha256"])},
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
    }


def _failed_unit(
    *, raw: Mapping[str, Any] | None, callback: Any | None, failure_class: str, failure_reason: str
) -> dict[str, Any]:
    model_calls = 0 if callback is None else int(callback.model_call_count)
    primary = 0 if raw is None else int(raw.get("primary_pool_model_call_count", 0))
    return {
        "unit_index": 0,
        "operational_arm": SMOKE_ARM,
        "state_sha256": None if raw is None else raw.get("state_sha256"),
        "input": None
        if raw is None
        else {
            "source_input_sha256": raw.get("source_input_sha256"),
            "expanded_input_sha256": raw.get("input_sha256"),
        },
        "latent": None
        if raw is None
        else {
            "seed": raw.get("latent_seed"),
            "tensor_sha256": raw.get("latent_tensor_sha256"),
            "row_sha256": raw.get("latent_row_sha256"),
        },
        "candidate_pool": None
        if raw is None
        else {
            "pool_sha256": raw.get("candidate_tensor_sha256_after"),
            "row_sha256": raw.get("candidate_row_sha256"),
        },
        "forward_calls": {
            "model_call_count_before": 0,
            "model_call_count_after": model_calls,
            "model_call_delta": model_calls,
            "primary_forward_count": primary,
            "sequential_forward_count": 0,
            "post_pool_model_forward_count": 0,
            "post_pool_dp_forward_count": 0,
            "post_pool_latent_replacement_count": 0,
            "post_pool_candidate_generation_count": 0,
            "candidate_pool_mutation_count": 0,
            "trajectory_regeneration_count": 0,
        },
        "selection": None,
        "simulator": None,
        "terminal": {
            "status": "typed_failure",
            "failure_class": failure_class,
            "failure_reason": failure_reason,
        },
    }


def run(args: argparse.Namespace) -> Path:
    if args.arm != SMOKE_ARM:
        raise ValueError("V26 one-state smoke arm must be Static14D")
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"V26 smoke output already exists: {output_dir}")
    with _exclusive_worker_lock(args.worker_lock.resolve()):
        manifest, config, assets = _prepare_manifest(args)
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
        from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import (
            _run_one,
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
        run_result = _run_one(
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
            max_ticks=1,
            operational_arm=SMOKE_ARM,
            evaluate_all_arms=False,
            adaptation_diagnostics=False,
            scratch_parent=output_dir.parent,
            production_surface_id=PRODUCTION_SURFACE_ID,
            production_surface_options=V26_TARGET_OPTIONS,
            retain_runtime_failures=True,
        )
        receipts = list(run_result["receipts"])
        if len(receipts) > 1:
            raise ValueError("V26 one-state smoke produced more than one unit")
        raw = receipts[0] if receipts else None
        callback = run_result["callback"]
        if raw is not None and raw.get("status") == "ok":
            unit = _completed_unit(raw, callback)
        else:
            native = dict(run_result["native_result"])
            unit = _failed_unit(
                raw=raw,
                callback=callback,
                failure_class=str(native.get("failure_class", "RuntimeFailure")),
                failure_reason=str(native.get("failure_reason", native.get("reason", "unknown"))),
            )
        receipt = build_development_smoke_receipt(manifest=manifest, unit=unit)
        return _atomic_write_ledger(output_dir, receipt)


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
    parser.add_argument("--arm", choices=(SMOKE_ARM,), required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ledger = run(parse_args(argv))
    print(ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
