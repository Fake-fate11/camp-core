#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_SCENE_FEATURE_NAMES,
    CAMPSelector,
    build_context_from_scene,
    extract_dp_scene_features,
    generate_candidate_trajectories,
    install_lanelet2_projection_fallback,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run tier4/Diffusion-Planner route replay with CAMP selecting "
            "one ego trajectory from a stochastic candidate pool."
        )
    )
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--map_path", type=str, default=None)
    parser.add_argument("--route", type=Path, required=True)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument(
        "--model_args",
        type=Path,
        default=None,
        help=(
            "Optional Diffusion Planner parameter JSON. Use this for official "
            "artifacts such as diffusion_planner.param.json; otherwise the "
            "upstream loader expects args.json next to the checkpoint."
        ),
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max_npcs", type=int, default=None)
    parser.add_argument("--spawn_probability", type=float, default=None)

    weights = parser.add_mutually_exclusive_group(required=True)
    weights.add_argument(
        "--camp_checkpoint",
        type=Path,
        help="CAMP-Select .pt checkpoint containing offline_weights.",
    )
    weights.add_argument(
        "--camp_static_weights",
        type=Path,
        help="Standalone offline_weights.npy.",
    )
    parser.add_argument("--camp_atom_scales", type=Path, required=True)
    parser.add_argument(
        "--camp_selector_mode",
        choices=("static", "linear"),
        default="static",
        help=(
            "static uses offline_weights; linear uses Theta from --camp_checkpoint "
            "and per-step Diffusion Planner scene features."
        ),
    )
    parser.add_argument("--camp_atom_clip", type=float, default=10.0)
    parser.add_argument("--camp_safety_radius", type=float, default=2.0)
    parser.add_argument("--camp_clearance_margin", type=float, default=1.0)
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--candidate_noise_scale", type=float, default=1.0)
    return parser.parse_args()


def _install_diffusion_repo(diffusion_repo: Path) -> None:
    repo = diffusion_repo.resolve()
    required = [
        repo / "scenario_generation" / "replay.py",
        repo / "diffusion_planner" / "diffusion_planner" / "model",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"{repo} is not a tier4/Diffusion-Planner checkout; missing: {missing}"
        )
    for path in (repo, repo / "diffusion_planner"):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _load_model(model_path: Path, model_args_path: Path | None, device: str):
    if model_args_path is None:
        import scenario_generation.replay as replay

        return replay.load_model(model_path, device)

    import torch
    from diffusion_planner.model.diffusion_planner import Diffusion_Planner
    from diffusion_planner.utils.config import Config

    args = Config(str(model_args_path))
    model = Diffusion_Planner(args)
    checkpoint = torch.load(str(model_path), map_location=device, weights_only=False)
    state = checkpoint.get("model", checkpoint)
    state = {key.replace("module.", ""): value for key, value in state.items()}
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model, args


def _ego_frame_xy(world_xy: np.ndarray, ego_xy: np.ndarray, ego_heading: float) -> np.ndarray:
    relative = np.asarray(world_xy, dtype=np.float64) - ego_xy.reshape(1, 2)
    c = math.cos(ego_heading)
    s = math.sin(ego_heading)
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    return relative @ rotation.T


def _candidate_obstacles(
    scene: Any,
    ego_agent_id: str,
    neighbor_predictions: np.ndarray,
    is_static_npc,
) -> np.ndarray:
    """Match tensor_converter's distance-sorted neighbor slot order."""
    ego = scene.get_agent(ego_agent_id)
    ego_xy = np.asarray(ego.current_position, dtype=np.float64)
    ego_heading = float(ego.current_heading)

    neighbors = [agent for agent in scene.agents if agent.id != ego_agent_id]
    neighbors.sort(
        key=lambda agent: float(
            np.linalg.norm(np.asarray(agent.current_position) - ego_xy)
        )
    )

    count = min(len(neighbors), neighbor_predictions.shape[1])
    obstacles = neighbor_predictions[:, :count, :, :2].copy()
    for neighbor_idx, agent in enumerate(neighbors[:count]):
        if not is_static_npc(agent.id):
            continue
        static_xy = _ego_frame_xy(
            np.asarray(agent.current_position, dtype=np.float64).reshape(1, 2),
            ego_xy,
            ego_heading,
        )[0]
        obstacles[:, neighbor_idx, :, 0] = static_xy[0]
        obstacles[:, neighbor_idx, :, 1] = static_xy[1]
    return obstacles


def _install_camp_predictor(
    replay_module: Any,
    tensor_converter_module: Any,
    selector: CAMPSelector,
    *,
    num_candidates: int,
    noise_scale: float,
    safety_radius: float,
    clearance_margin: float,
) -> tuple[Any, list[dict[str, Any]]]:
    original_predict = replay_module._predict_batch
    records: list[dict[str, Any]] = []

    def camp_predict(
        model,
        model_args,
        scene,
        agent_ids,
        device,
        map_cache=None,
        return_turn_indicators=False,
        inference_delay=0,
        turn_indicator_keep_bias=0.25,
    ):
        base = original_predict(
            model,
            model_args,
            scene,
            agent_ids,
            device,
            map_cache=map_cache,
            return_turn_indicators=return_turn_indicators,
            inference_delay=inference_delay,
            turn_indicator_keep_bias=turn_indicator_keep_bias,
        )
        if return_turn_indicators:
            predictions, turn_indicators = base
        else:
            predictions = base
            turn_indicators = None

        ego_id = scene.ego_agent_id
        if ego_id not in agent_ids:
            return base

        inputs = tensor_converter_module.to_model_tensors(
            scene,
            ego_id,
            model_args,
            device,
            map_cache=map_cache,
            inference_delay=inference_delay,
        )
        scene_features = extract_dp_scene_features(inputs)
        start = time.perf_counter()
        candidates, neighbor_predictions, turn_logits = generate_candidate_trajectories(
            model,
            model_args,
            inputs,
            num_candidates=num_candidates,
            noise_scale=noise_scale,
            deterministic_first=True,
        )
        context = build_context_from_scene(
            scene,
            ego_id,
            safety_radius=safety_radius,
            clearance_soft_margin=clearance_margin,
        )
        obstacles = _candidate_obstacles(
            scene,
            ego_id,
            neighbor_predictions,
            replay_module.SceneNPCManager.is_static_npc,
        )
        selection = selector.select(
            candidates,
            context,
            scene_embedding=scene_features if selector.mode == "linear" else None,
            candidate_obstacles=obstacles,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        predictions[ego_id] = selection.selected_trajectory
        if return_turn_indicators and turn_logits is not None:
            chosen_logits = turn_logits[selection.selected_index].copy()
            if turn_indicator_keep_bias != 0.0 and chosen_logits.shape[-1] > 4:
                chosen_logits[4] -= turn_indicator_keep_bias
            turn_indicators[ego_id] = int(np.argmax(chosen_logits))

        records.append(
            {
                "selection_step": len(records),
                "selected_index": selection.selected_index,
                "num_candidates": int(num_candidates),
                "used_fallback": selection.used_fallback,
                "feasible_mask": selection.feasible_mask.tolist(),
                "scores": selection.scores.tolist(),
                "weights": selection.weights.tolist(),
                "atoms": selection.atoms.tolist(),
                "normalized_atoms": selection.normalized_atoms.tolist(),
                "dp_scene_features": scene_features.tolist(),
                "dp_scene_feature_names": list(DP_SCENE_FEATURE_NAMES),
                "latency_ms_including_candidate_generation": elapsed_ms,
            }
        )
        if return_turn_indicators:
            return predictions, turn_indicators
        return predictions

    replay_module._predict_batch = camp_predict
    return original_predict, records


def main() -> None:
    args = parse_args()
    if args.num_candidates < 2:
        raise ValueError("--num_candidates must be >= 2 for CAMP candidate selection.")
    if args.candidate_noise_scale <= 0:
        raise ValueError("--candidate_noise_scale must be > 0.")

    _install_diffusion_repo(args.diffusion_repo)

    import torch
    import scenario_generation.replay as replay
    import scenario_generation.tensor_converter as tensor_converter
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route

    selector = CAMPSelector.from_files(
        atom_scales_path=args.camp_atom_scales,
        checkpoint_path=args.camp_checkpoint,
        static_weights_path=args.camp_static_weights,
        mode=args.camp_selector_mode,
        atom_clip=args.camp_atom_clip,
    )

    route = Route.load(args.route)
    map_path = args.map_path or route.map_path
    using_projection_fallback = install_lanelet2_projection_fallback(map_path)
    builder = LaneletSceneBuilder(map_path)
    config = replay.SpawnConfig.from_json(args.config)
    if args.steps is not None:
        config.max_steps = args.steps
    if args.seed is not None:
        config.seed = args.seed
    if args.max_npcs is not None:
        config.max_active_npcs = args.max_npcs
    if args.spawn_probability is not None:
        config.spawn_probability = args.spawn_probability
    config.validate()

    device = args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu"
    model, model_args = _load_model(args.model_path, args.model_args, device)
    original_predict, records = _install_camp_predictor(
        replay,
        tensor_converter,
        selector,
        num_candidates=args.num_candidates,
        noise_scale=args.candidate_noise_scale,
        safety_radius=args.camp_safety_radius,
        clearance_margin=args.camp_clearance_margin,
    )

    try:
        result = replay.run_route_replay(
            model=model,
            model_args=model_args,
            builder=builder,
            route=route,
            output_dir=args.output_dir,
            spawn_config=config,
            device=device,
        )
    finally:
        replay._predict_batch = original_predict

    args.output_dir.mkdir(parents=True, exist_ok=True)
    selection_log = args.output_dir / "camp_selection_log.json"
    selection_log.write_text(json.dumps(records, indent=2), encoding="utf-8")
    summary = {
        "replay_result": result,
        "camp_selection_log": str(selection_log),
        "num_candidates": args.num_candidates,
        "candidate_noise_scale": args.candidate_noise_scale,
        "selector_mode": args.camp_selector_mode,
        "dp_scene_feature_names": list(DP_SCENE_FEATURE_NAMES),
        "model_args": str(args.model_args) if args.model_args is not None else None,
        "using_no_ros_projection_fallback": using_projection_fallback,
    }
    (args.output_dir / "camp_replay_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
