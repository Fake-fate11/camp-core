"""Qualify one same-ego K=8 fixed-DP model invocation on nonholdout state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_target_architecture import (  # noqa: E402
    BATCH_SEQUENTIAL_ATOL,
    BATCH_SEQUENTIAL_RTOL,
    CAPABILITY_SCHEMA,
    FIXED_DP_HEAD,
    LEGACY_DECISION,
    array_sha256,
    canonical_sha256,
    freeze_candidate_pool,
    qualify_selector_after_pool,
    validate_capability_report,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    _install_fixed_dp_annotation_compatibility,
    candidate_latents,
)


class _QualificationComplete(RuntimeError):
    pass


def qualify(
    *,
    output: Path,
    contract: Path,
    contract_root: str,
    contract_review: Path,
    contract_review_root: str,
    probe_config: Path,
    fixed_dp_repo: Path,
    device: str,
) -> str:
    verify_complete_seal(contract, contract_root, label="target architecture contract")
    verify_complete_seal(
        contract_review,
        contract_review_root,
        label="target architecture contract review",
    )
    contract_report = _object(contract / "report.json")
    review_report = _object(contract_review / "report.json")
    if (
        contract_report.get("status")
        != "sealed_outcome_independent_target_architecture_amendment"
        or review_report.get("status")
        != "passed_independent_target_architecture_amendment_review"
        or review_report.get("source", {}).get("root_sha256") != contract_root
    ):
        raise ValueError("target architecture authority chain drifted")
    config = _object(probe_config)
    fixed = _object_value(config.get("fixed_dp"), "fixed_dp")
    if (
        fixed.get("head") != FIXED_DP_HEAD
        or Path(str(fixed.get("repo"))).resolve() != fixed_dp_repo.resolve()
        or _git_head(fixed_dp_repo) != FIXED_DP_HEAD
        or _tracked_changes(fixed_dp_repo)
    ):
        raise ValueError("fixed DP authority drifted")
    checkpoint = Path(str(fixed["checkpoint"]["path"]))
    args_path = Path(str(fixed["args_json"]["path"]))
    if (
        _file_sha256(checkpoint) != fixed["checkpoint"]["sha256"]
        or _file_sha256(args_path) != fixed["args_json"]["sha256"]
    ):
        raise ValueError("fixed DP checkpoint/args drifted")
    if config.get("protocol", {}).get("route_role") != (
        "v24_source_only_single_record_probe"
    ):
        raise ValueError("qualification input must be development nonholdout")
    if config.get("protocol", {}).get("holdout_access_authorized") is not False:
        raise ValueError("qualification must not access holdout")

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
        raise RuntimeError("CUDA qualification requested but unavailable")
    model, model_args = _load_model(checkpoint, args_path, device)
    if int(model_args.predicted_neighbor_num) != 320 or int(model_args.future_len) != 80:
        raise ValueError("fixed DP model shape contract drifted")
    model.eval()

    route_spec = config["routes"][0]
    route_path = Path(str(route_spec["path"]))
    if _file_sha256(route_path) != route_spec["sha256"]:
        raise ValueError("development route SHA drifted")
    map_path = Path(str(config["map"]["path"]))
    if _file_sha256(map_path) != config["map"]["sha256"]:
        raise ValueError("development map SHA drifted")
    require_source_preserving_lanelet2_regulatory_adapter(map_path)
    install_lanelet2_projection_fallback(map_path)
    builder = LaneletSceneBuilder(str(map_path))
    route = Route.load(route_path)
    spawn = replay.SpawnConfig(**dict(config["spawn_config"]))
    spawn.max_steps = 1
    spawn.validate()

    captured: dict[str, Any] = {}
    original_predict = replay._predict_batch
    simulator_scratch = Path(
        tempfile.mkdtemp(prefix=".v25_target_arch_scene.", dir=str(output.parent))
    )

    def direct_qualification(
        model_arg: Any,
        model_args_arg: Any,
        scene: Any,
        agent_ids: list[str],
        device_arg: str,
        map_cache: Any = None,
        return_turn_indicators: bool = False,
        inference_delay: int = 0,
        turn_indicator_keep_bias: float = 0.25,
    ) -> Any:
        del return_turn_indicators, turn_indicator_keep_bias
        if captured:
            raise RuntimeError("qualification intercept invoked more than once")
        if model_arg is not model or model_args_arg is not model_args:
            raise ValueError("formal model binding drifted")
        if agent_ids != [scene.ego_agent_id] or agent_ids != ["ego"]:
            raise ValueError("source batch is not the single ego")
        base = tensor_converter.to_model_tensors(
            scene,
            "ego",
            model_args,
            device_arg,
            map_cache=map_cache,
            inference_delay=inference_delay,
        )
        if not base or any(
            not isinstance(value, torch.Tensor) or value.shape[0] != 1
            for value in base.values()
        ):
            raise ValueError("formal model inputs are not a batch-1 tensor dictionary")
        source_input_sha = _tensor_dict_sha256(base)
        source_state = _source_state_receipt(scene, source_input_sha, route_spec)
        expanded = {
            key: value.expand(8, *value.shape[1:]).contiguous()
            for key, value in base.items()
        }
        nonlatent_identical = all(
            all(torch.equal(value[0], value[index]) for index in range(1, 8))
            for key, value in expanded.items()
            if key != "sampled_trajectories"
        )
        latent_np = candidate_latents(
            int(config["seeds"]["candidate"]),
            noise_scale=1.0,
        )
        latent = torch.from_numpy(latent_np).to(
            device=device_arg,
            dtype=expanded["sampled_trajectories"].dtype,
        )
        if tuple(latent.shape) != tuple(expanded["sampled_trajectories"].shape):
            raise ValueError("same-ego K8 latent shape drifted")
        expanded["sampled_trajectories"] = latent.contiguous()
        expanded_input_sha = _tensor_dict_sha256(expanded)
        latent_sha = array_sha256(latent.detach().cpu().numpy())
        invocation_id = canonical_sha256(
            {
                "input_sha256": expanded_input_sha,
                "model_sha256": fixed["checkpoint"]["sha256"],
                "latent_sha256": latent_sha,
                "device": device_arg,
                "candidate_count": 8,
            }
        )
        rng_before = _rng_sha256(torch)
        call_count = 0

        def forward(inputs: dict[str, Any]) -> np.ndarray:
            nonlocal call_count
            call_count += 1
            with torch.no_grad():
                _encoded, outputs = model(inputs)
            prediction = outputs["prediction"]
            if tuple(prediction.shape[:2]) != (
                int(inputs["sampled_trajectories"].shape[0]),
                321,
            ):
                raise ValueError("fixed DP formal prediction shape drifted")
            return prediction[:, 0].detach().cpu().numpy().astype(
                np.float32, copy=False
            )

        primary = forward(expanded)
        primary_call_count = call_count
        repeat = forward(expanded)
        repeat_call_count = call_count - primary_call_count
        sequential_rows: list[np.ndarray] = []
        before_sequential = call_count
        for index in range(8):
            row_inputs = {
                key: value[index : index + 1].contiguous()
                for key, value in expanded.items()
            }
            sequential_rows.append(forward(row_inputs)[0])
        sequential = np.stack(sequential_rows).astype(np.float32, copy=False)
        sequential_call_count = call_count - before_sequential
        rng_after = _rng_sha256(torch)
        row_sha = [array_sha256(row) for row in primary]
        row_errors = [
            float(np.max(np.abs(primary[index].astype(np.float64) - sequential[index].astype(np.float64))))
            for index in range(8)
        ]
        within_tolerance = bool(
            np.allclose(
                primary,
                sequential,
                atol=BATCH_SEQUENTIAL_ATOL,
                rtol=BATCH_SEQUENTIAL_RTOL,
            )
        )
        pairwise_rms = [
            float(np.sqrt(np.mean((primary[left] - primary[right]) ** 2)))
            for left in range(8)
            for right in range(left + 1, 8)
        ]
        pool = freeze_candidate_pool(
            primary,
            input_sha256=expanded_input_sha,
            model_sha256=fixed["checkpoint"]["sha256"],
            forward_invocation_id=invocation_id,
        )
        selector_arms = [
            qualify_selector_after_pool(
                pool,
                arm=arm,
                selector=(lambda _pool, _guard: 0),
            )
            for arm in ("pool_baseline", "Static14D", "Scene14D")
        ]
        report = {
            "schema_version": CAPABILITY_SCHEMA,
            "status": "passed_same_ego_single_invocation_k8_capability",
            "authority": {
                "contract_path": str(contract.resolve()),
                "contract_root_sha256": contract_root,
                "contract_review_path": str(contract_review.resolve()),
                "contract_review_root_sha256": contract_review_root,
            },
            "fixed_dp": {
                "head": FIXED_DP_HEAD,
                "repo": str(fixed_dp_repo.resolve()),
                "checkpoint_path": str(checkpoint.resolve()),
                "checkpoint_sha256": fixed["checkpoint"]["sha256"],
                "args_path": str(args_path.resolve()),
                "args_sha256": fixed["args_json"]["sha256"],
                "model_source_sha256": _file_sha256(
                    fixed_dp_repo
                    / "diffusion_planner/diffusion_planner/model/diffusion_planner.py"
                ),
                "decoder_source_sha256": _file_sha256(
                    fixed_dp_repo
                    / "diffusion_planner/diffusion_planner/model/module/decoder.py"
                ),
                "encoder_source_sha256": _file_sha256(
                    fixed_dp_repo
                    / "diffusion_planner/diffusion_planner/model/module/encoder.py"
                ),
                "source_modified": False,
                "checkpoint_modified": False,
                "model_eval_mode": not model.training,
                "formal_entrypoint": "Diffusion_Planner.forward(inputs)",
            },
            "source_state": source_state,
            "candidate_axis": {
                "semantics": "same_ego_candidate_batch",
                "candidate_count": 8,
                "source_agent_ids": ["ego"],
                "source_batch_size": 1,
                "expanded_model_batch_size": 8,
                "agent_as_ego_batch": False,
                "all_nonlatent_rows_identical": nonlatent_identical,
            },
            "latent": {
                "source": "legacy_candidate_latents_seed24001_noise_scale1",
                "seed": int(config["seeds"]["candidate"]),
                "noise_scale": 1.0,
                "shape": list(latent.shape),
                "dtype": str(latent.detach().cpu().numpy().dtype),
                "sha256": latent_sha,
                "row_sha256": [
                    array_sha256(row) for row in latent.detach().cpu().numpy()
                ],
                "row0_zero": bool(torch.count_nonzero(latent[0]).item() == 0),
                "finite": bool(torch.isfinite(latent).all().item()),
            },
            "temperature": {
                "status": "not_exposed_by_fixed_dp_formal_interface",
                "tensor": None,
                "sha256": None,
            },
            "primary_pool_invocation": {
                "forward_invocation_id": invocation_id,
                "model_call_count": primary_call_count,
                "input_sha256": expanded_input_sha,
                "input_batch_size": 8,
                "output_shape": list(primary.shape),
                "dtype": str(primary.dtype),
                "finite": bool(np.all(np.isfinite(primary))),
                "candidate_tensor_sha256": array_sha256(primary),
                "row_sha256": row_sha,
                "unique_row_sha256_count": len(set(row_sha)),
                "pool_id": pool.pool_id,
                "pairwise_rms_min": min(pairwise_rms),
                "pairwise_rms_max": max(pairwise_rms),
                "diverse": bool(len(set(row_sha)) == 8 and max(pairwise_rms) > 1e-6),
            },
            "determinism": {
                "repeat_model_call_count": repeat_call_count,
                "repeat_tensor_sha256": array_sha256(repeat),
                "exact_equal": bool(np.array_equal(primary, repeat)),
                "max_abs_error": float(
                    np.max(
                        np.abs(
                            primary.astype(np.float64)
                            - repeat.astype(np.float64)
                        )
                    )
                ),
            },
            "batch_vs_sequential": {
                "relationship": (
                    "same_state_same_latent_direct_batch8_vs_eight_batch1_calls"
                ),
                "sequential_model_call_count": sequential_call_count,
                "atol": BATCH_SEQUENTIAL_ATOL,
                "rtol": BATCH_SEQUENTIAL_RTOL,
                "within_frozen_tolerance": within_tolerance,
                "per_row_max_abs_error": row_errors,
                "max_abs_error": max(row_errors),
                "all_sequential_row_sha256": [
                    array_sha256(row) for row in sequential
                ],
                "distribution_equivalent_under_frozen_row_tolerance": (
                    within_tolerance
                ),
            },
            "selector_after_pool": {
                "status": "passed_three_arm_structural_pool_binding_gate",
                "selection_semantics": (
                    "outcome_independent_row0_structural_probe_not_camp_score_evaluation"
                ),
                "arms": selector_arms,
                "all_arms_same_pool": True,
                "selector_model_call_count_total": 0,
            },
            "rng_boundary": {
                "unchanged": rng_before == rng_after,
                "before_sha256": rng_before,
                "after_sha256": rng_after,
            },
            "training_decision": {
                "training_executed": False,
                "batch_vs_sequential_equivalent": within_tolerance,
                "possible_ood_effect_requires_future_adjudication": (
                    not within_tolerance
                ),
            },
            "claim_boundary": {
                "fresh_or_closed_loop_executed": False,
                "scientific_effect_claim_authorized": False,
                "legacy_claim_decision": LEGACY_DECISION,
                "qualification_only": True,
            },
        }
        if (
            primary_call_count != 1
            or repeat_call_count != 1
            or sequential_call_count != 8
            or not nonlatent_identical
            or not np.all(np.isfinite(primary))
            or len(set(row_sha)) != 8
            or not np.array_equal(primary, repeat)
            or not within_tolerance
            or rng_before != rng_after
        ):
            report["status"] = "blocked_same_ego_single_invocation_k8_capability"
        captured.update(
            {
                "report": report,
                "candidate_tensor": primary,
                "sequential_candidate_tensor": sequential,
                "latent_tensor": latent.detach().cpu().numpy(),
            }
        )
        raise _QualificationComplete

    prior_no_png = os.environ.get("REPLAY_NO_PNG")
    replay._predict_batch = direct_qualification
    os.environ["REPLAY_NO_PNG"] = "1"
    try:
        try:
            replay.run_route_replay(
                model=model,
                model_args=model_args,
                builder=builder,
                route=route,
                output_dir=simulator_scratch,
                spawn_config=spawn,
                device=device,
            )
        except _QualificationComplete:
            pass
    finally:
        replay._predict_batch = original_predict
        if prior_no_png is None:
            os.environ.pop("REPLAY_NO_PNG", None)
        else:
            os.environ["REPLAY_NO_PNG"] = prior_no_png
        shutil.rmtree(simulator_scratch, ignore_errors=True)
    if not captured:
        raise RuntimeError("formal model qualification intercept was never reached")
    report = captured["report"]
    if report["status"] == "passed_same_ego_single_invocation_k8_capability":
        validate_capability_report(report)
    return _write_atomic(
        output,
        report,
        candidate_tensor=captured["candidate_tensor"],
        sequential_candidate_tensor=captured["sequential_candidate_tensor"],
        latent_tensor=captured["latent_tensor"],
    )


def _source_state_receipt(
    scene: Any,
    source_input_sha: str,
    route_spec: dict[str, Any],
) -> dict[str, Any]:
    ego = scene.ego_agent
    state = {
        "ego_id": str(ego.id),
        "past_trajectory_sha256": array_sha256(ego.past_trajectory),
        "past_velocities_sha256": array_sha256(ego.past_velocities),
        "goal_pose_sha256": array_sha256(ego.goal_pose),
        "route_lanelet_ids": [int(value) for value in ego.route_lanelet_ids],
        "input_sha256": source_input_sha,
    }
    return {
        "role": "development_nonholdout",
        "route_role": "v24_source_only_single_record_probe",
        "route_sha256": str(route_spec["sha256"]),
        "source_batch_size": 1,
        "state_sha256": canonical_sha256(state),
        "input_sha256": source_input_sha,
        "simulator_steps_advanced": 0,
        "holdout_or_fresh_accessed": False,
    }


def _tensor_dict_sha256(value: dict[str, Any]) -> str:
    rows = []
    for key in sorted(value):
        tensor = value[key].detach().cpu().contiguous()
        rows.append(
            {
                "key": key,
                "dtype": str(tensor.numpy().dtype),
                "shape": list(tensor.shape),
                "sha256": array_sha256(tensor.numpy()),
            }
        )
    return canonical_sha256(rows)


def _rng_sha256(torch: Any) -> str:
    payload = {
        "python": repr(random.getstate()),
        "numpy": repr(np.random.get_state()),
        "torch_cpu": hashlib.sha256(
            torch.get_rng_state().cpu().numpy().tobytes()
        ).hexdigest(),
        "torch_cuda": [
            hashlib.sha256(state.cpu().numpy().tobytes()).hexdigest()
            for state in (
                torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []
            )
        ],
    }
    return canonical_sha256(payload)


def _write_atomic(
    output: Path,
    report: dict[str, Any],
    *,
    candidate_tensor: np.ndarray,
    sequential_candidate_tensor: np.ndarray,
    latent_tensor: np.ndarray,
) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        np.save(staging / "candidate_tensor.npy", candidate_tensor, allow_pickle=False)
        np.save(
            staging / "sequential_candidate_tensor.npy",
            sequential_candidate_tensor,
            allow_pickle=False,
        )
        np.save(staging / "latent_tensor.npy", latent_tensor, allow_pickle=False)
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "role": "same_ego_single_invocation_k8_capability",
                    "implementation_head": _git_head(ROOT),
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        root = seal_artifact(staging, label="V25 same-ego K8 capability")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 same-ego K8 capability")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _object_value(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be an object")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=repo,
            text=True,
        ).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--probe-config", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    print(qualify(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
