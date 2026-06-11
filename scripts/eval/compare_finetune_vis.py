import argparse
import os

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
if not os.environ.get("OMP_NUM_THREADS", "").isdigit() or int(os.environ.get("OMP_NUM_THREADS", "0") or 0) <= 0:
    os.environ["OMP_NUM_THREADS"] = "1"

import sys
import json
import re
from pathlib import Path

import numpy as np
import torch
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
)
from camp_core.base_predictor.trajectron_loader import (
    TrajectronLoadConfig,
    build_trajectron_from_checkpoint,
)
import trajdata.visualization.vis as trajdata_vis
from trajdata import AgentType


def resolve_trajectron_epoch(model_dir: str, requested_epoch: int) -> int:
    """Return requested epoch; if <=0, automatically use latest checkpoint epoch."""
    if requested_epoch > 0:
        return requested_epoch

    model_path = Path(model_dir)
    epochs = []
    for ckpt in model_path.glob("model_registrar-*.pt"):
        match = re.search(r"model_registrar-(\d+)\.pt$", ckpt.name)
        if match:
            epochs.append(int(match.group(1)))

    if not epochs:
        raise FileNotFoundError(
            f"No model_registrar-*.pt found under {model_dir}. "
            "Please pass --base_epoch explicitly."
        )
    return max(epochs)


def parse_int_csv(text: str) -> list:
    if text is None:
        return []
    text = text.strip()
    if not text:
        return []
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def load_targets_from_json(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        if "targets" in payload and isinstance(payload["targets"], list):
            items = payload["targets"]
        elif "candidates" in payload and isinstance(payload["candidates"], list):
            items = payload["candidates"]
        else:
            raise ValueError("Unsupported targets_json format: expected a list or {'targets': [...]}.")
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("Unsupported targets_json format.")

    pairs = []
    for item in items:
        if not isinstance(item, dict):
            continue
        scene_idx = (
            item.get("scene_idx")
            if item.get("scene_idx") is not None
            else item.get("target_scene_idx")
        )
        if scene_idx is None:
            scene_idx = item.get("scene")
        agent_idx = (
            item.get("agent_idx")
            if item.get("agent_idx") is not None
            else item.get("target_agent_idx")
        )
        if agent_idx is None:
            agent_idx = item.get("agent", 0)

        if scene_idx is None:
            continue
        pairs.append((int(scene_idx), int(agent_idx)))

    return pairs


def parse_target_pairs(args) -> list:
    if args.targets_json:
        pairs = load_targets_from_json(args.targets_json)
    elif args.target_pairs.strip():
        pairs = []
        for part in args.target_pairs.split(","):
            token = part.strip()
            if not token:
                continue
            if ":" not in token:
                raise ValueError(
                    f"Invalid token '{token}' in --target_pairs. Expected format scene:agent."
                )
            scene_s, agent_s = token.split(":", 1)
            pairs.append((int(scene_s), int(agent_s)))
    elif args.target_scene_indices.strip():
        scene_indices = parse_int_csv(args.target_scene_indices)
        if not scene_indices:
            raise ValueError("--target_scene_indices is provided but no valid indices were parsed.")

        agent_indices = parse_int_csv(args.target_agent_indices)
        if not agent_indices:
            agent_indices = [0] * len(scene_indices)
        elif len(agent_indices) == 1 and len(scene_indices) > 1:
            agent_indices = agent_indices * len(scene_indices)
        elif len(agent_indices) != len(scene_indices):
            raise ValueError(
                "--target_scene_indices and --target_agent_indices length mismatch. "
                "Use same length or provide one agent index."
            )
        pairs = list(zip(scene_indices, agent_indices))
    else:
        pairs = [(args.target_scene_idx, args.target_agent_idx)]

    if args.max_targets > 0:
        pairs = pairs[: args.max_targets]

    if not pairs:
        raise ValueError("No valid target (scene, agent) pairs found.")

    return pairs


def build_output_path(args, scene_idx: int, agent_idx: int, multi_target: bool) -> str:
    if not multi_target and not args.output_dir:
        return args.output_path

    out_dir = args.output_dir
    if not out_dir:
        out_dir = os.path.dirname(args.output_path)
        if not out_dir:
            out_dir = "figures"

    filename = f"compare_scene_{scene_idx}_agent_{agent_idx}_ft{args.finetuned_epoch}.png"
    return os.path.join(out_dir, filename)


def load_json_if_exists(path: str) -> dict:
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def collect_target_batches(dataloader, scene_indices: list) -> dict:
    required = set(scene_indices)
    collected = {}
    total_required = len(required)

    for idx, batch in enumerate(dataloader):
        if idx in required:
            collected[idx] = batch
            print(f"[CompareVis] Collected scene {idx} ({len(collected)}/{total_required})")
            if len(collected) == total_required:
                break

    missing = sorted(required.difference(collected.keys()))
    if missing:
        print(f"[CompareVis] Warning: Missing scene indices: {missing}")

    return collected


def match_cached_scenario(scenarios, batch, agent_idx: int, scene_idx: int):
    if not scenarios:
        return None, -1

    fut = batch.agent_fut[agent_idx].cpu().numpy()
    fut_xy = fut[:11, :2]
    gt_fut_batch = np.concatenate(([np.zeros(2)], fut_xy), axis=0)

    for sc_idx, sc in enumerate(scenarios):
        gt_sc = sc["gt_traj"]
        min_len = min(len(gt_sc), len(gt_fut_batch))
        valid = ~np.isnan(gt_fut_batch[:min_len]).any(axis=-1)
        valid = valid & ~np.isnan(gt_sc[:min_len]).any(axis=-1)

        if valid.sum() > 2:
            diff = np.mean(
                np.linalg.norm(
                    gt_sc[:min_len][valid] - gt_fut_batch[:min_len][valid], axis=-1
                )
            )
            if diff < 0.1:
                print(
                    f"Matched Unshuffled Dataloader Batch {scene_idx} to Shuffled Cache Scene {sc_idx}!"
                )
                return sc, sc_idx

    print(
        f"Warning: Could not match scene {scene_idx}, agent {agent_idx} to shuffled cache. "
        "Plotting only model predictions."
    )
    return None, -1


def render_target(
    args,
    batch,
    scene_idx: int,
    agent_idx: int,
    base_model,
    finetune_model,
    device,
    scenarios,
    camp_preds,
    reranker_preds,
    static_preds,
    output_path: str,
):
    if agent_idx >= len(batch.agent_name):
        print(
            f"Warning: scene {scene_idx} requested agent_idx={agent_idx}, "
            f"but batch has {len(batch.agent_name)} agents. Using 0."
        )
        agent_idx = 0

    agent_name = batch.agent_name[agent_idx]
    node_type = (
        AgentType(batch.agent_type[agent_idx].item())
        if hasattr(batch, "agent_type")
        else "VEHICLE"
    )
    key = f"{str(node_type)}/{agent_name}"

    print(f"[CompareVis] Plotting scene={scene_idx}, agent={agent_idx} ({key})")
    fig, ax = plt.subplots(figsize=(12, 12), dpi=200)

    # Plot map/history on CPU batch before any device transfer.
    trajdata_vis.plot_agent_batch(batch, batch_idx=agent_idx, ax=ax, show=False, close=False)

    gt_fut = batch.agent_fut[agent_idx].cpu().numpy()
    valid_gt = ~np.isnan(gt_fut).any(axis=-1)
    ax.plot(
        gt_fut[valid_gt, 0],
        gt_fut[valid_gt, 1],
        color="black",
        linewidth=4,
        linestyle="--",
        marker="*",
        label="Ground Truth",
    )

    # NOTE: trajdata StateTensor subclasses do not support copy.deepcopy().
    # Move the batch in-place after CPU-side plotting is finished.
    pred_batch = batch
    pred_batch.to(device)
    ph = base_model.hyperparams.get("prediction_horizon", 12)

    with torch.no_grad():
        base_preds = base_model.predict(
            pred_batch,
            prediction_horizon=ph,
            num_samples=1,
            z_mode=False,
            gmm_mode=True,
            output_dists=False,
        )
        safe_preds = finetune_model.predict(
            pred_batch,
            prediction_horizon=ph,
            num_samples=1,
            z_mode=False,
            gmm_mode=True,
            output_dists=False,
        )

    base_traj = base_preds[key][0] if key in base_preds else np.zeros((ph, 2), dtype=np.float32)
    if hasattr(base_traj, "cpu"):
        base_traj = base_traj.cpu().numpy()

    safe_traj = safe_preds[key][0] if key in safe_preds else np.zeros((ph, 2), dtype=np.float32)
    if hasattr(safe_traj, "cpu"):
        safe_traj = safe_traj.cpu().numpy()

    camp_traj = None
    reranker_traj = None
    oracle_traj = None
    select_static_traj = None

    target_sc, target_sc_idx = match_cached_scenario(scenarios, batch, agent_idx, scene_idx)
    if target_sc is not None:
        cands = target_sc["candidates"]
        gt = target_sc["gt_traj"]

        # Pred Top1 from cache for consistency with table metrics.
        base_traj = cands[0]

        ade_costs = []
        for c in cands:
            min_len = min(len(c), len(gt))
            valid = ~np.isnan(gt[:min_len]).any(axis=-1)
            ade = (
                np.mean(np.linalg.norm(c[:min_len][valid] - gt[:min_len][valid], axis=-1))
                if valid.any()
                else 0.0
            )
            ade_costs.append(ade)
        oracle_traj = cands[int(np.argmin(ade_costs))]

        if camp_preds:
            camp_idx = int(camp_preds.get(f"sc_{target_sc_idx}", 0))
            if 0 <= camp_idx < len(cands):
                camp_traj = cands[camp_idx]

        if reranker_preds:
            rerank_idx = int(reranker_preds.get(f"sc_{target_sc_idx}", 0))
            if 0 <= rerank_idx < len(cands):
                reranker_traj = cands[rerank_idx]

        if static_preds:
            static_idx = int(static_preds.get(f"sc_{target_sc_idx}", 0))
            if 0 <= static_idx < len(cands):
                select_static_traj = cands[static_idx]

    plots = [
        (base_traj, "Pred Top1", "#DD9787", "-"),
        (camp_traj, "Camp Select", "#9F9FED", "-"),
        (select_static_traj, "Select Static", "#E8B86D", "--"),
        (reranker_traj, "Reranker Safe", "#A6C48A", "-"),
        (oracle_traj, "Oracle MinADE", "#A2999E", "--"),
        (safe_traj, "Finetune Safe", "#AA7C85", "-"),
    ]

    for traj, name, color, style in plots:
        if traj is not None:
            ax.plot(
                traj[:, 0],
                traj[:, 1],
                color=color,
                linewidth=5,
                linestyle=style,
                marker="o" if "Finetune" not in name else "X",
                markersize=6,
                alpha=0.9,
                label=name,
            )

    ax.legend(bbox_to_anchor=(1.04, 1.0), loc="upper left", borderaxespad=0, frameon=True)
    ax.set_title(f"Scene {scene_idx} | Agent {agent_name}")

    plot_radius = 50
    ax.set_xlim((-plot_radius, plot_radius))
    ax.set_ylim((-plot_radius, plot_radius))

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[CompareVis] Saved: {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize Finetuned Trajectron++ vs Base Model")
    parser.add_argument("--data_root", type=str, default="/root/autodl-tmp/dataset")
    parser.add_argument("--cache_dir", type=str, default="/root/autodl-tmp/.unified_data_cache")
    parser.add_argument("--base_model_dir", type=str, required=True, help="Base model for comparison")
    parser.add_argument("--finetuned_model_dir", type=str, required=True, help="Finetuned model dir")
    parser.add_argument(
        "--base_epoch",
        type=int,
        default=-1,
        help="Base checkpoint epoch. <=0 means latest checkpoint in --base_model_dir.",
    )
    parser.add_argument("--finetuned_epoch", type=int, default=60)
    parser.add_argument("--finetuned_prefix", type=str, default="finetuned_safe")
    parser.add_argument("--split", type=str, default="nusc_trainval-val")

    # Single-target backward-compatible args.
    parser.add_argument("--output_path", type=str, default="figures/compare_crash_vs_safe.png")
    parser.add_argument("--target_scene_idx", type=int, default=0, help="Single mode: scene index")
    parser.add_argument("--target_agent_idx", type=int, default=0, help="Single mode: agent index")

    # Multi-target args.
    parser.add_argument(
        "--target_pairs",
        type=str,
        default="",
        help='Comma-separated scene:agent pairs, e.g. "2120:0,1987:1"',
    )
    parser.add_argument(
        "--target_scene_indices",
        type=str,
        default="",
        help='Comma-separated scene indices, e.g. "2120,1987,1501"',
    )
    parser.add_argument(
        "--target_agent_indices",
        type=str,
        default="",
        help='Comma-separated agent indices (same length as scenes) or single value, e.g. "0,1,0" or "0"',
    )
    parser.add_argument(
        "--targets_json",
        type=str,
        default="",
        help="Optional JSON file containing target pairs. Supports list or {'targets': [...]}.",
    )
    parser.add_argument(
        "--max_targets",
        type=int,
        default=-1,
        help="Use only first K targets after parsing. <=0 means all.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="",
        help="If provided (or multiple targets), saves one file per target in this directory.",
    )

    # Optional external prediction artifacts.
    parser.add_argument("--cache_path", type=str, default="data/cached_eval_batch.pkl")
    parser.add_argument("--camp_preds_path", type=str, default="results/camp_select_preds.json")
    parser.add_argument("--reranker_preds_path", type=str, default="results/reranker_safe_preds.json")
    parser.add_argument("--select_static_preds_path", type=str, default="results/select_static_preds.json")

    return parser.parse_args()


def main():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    resolved_base_epoch = resolve_trajectron_epoch(args.base_model_dir, args.base_epoch)
    print(f"[CompareVis] Using base checkpoint epoch: {resolved_base_epoch}")

    target_pairs = parse_target_pairs(args)
    print(f"[CompareVis] Targets: {target_pairs}")

    print(f"Loading {args.split} dataset...")
    cfg = NuscenesDatasetConfig(
        data_root=args.data_root,
        cache_dir=args.cache_dir,
        batch_size=1,
        num_workers=0,
        shuffle=False,
        split=args.split,
        use_vector_map=True,
        unified_dataset_kwargs={"history_sec": (2.0, 2.0), "future_sec": (6.0, 6.0)},
    )
    bridge = NuscenesTrajdataBridge(cfg)
    dataloader = bridge.get_dataloader()

    target_scene_indices = [scene_idx for scene_idx, _ in target_pairs]
    scene_batches = collect_target_batches(dataloader, target_scene_indices)

    print("Loading Base Model...")
    base_cfg = TrajectronLoadConfig(
        conf_path=os.path.join(args.base_model_dir, "config.json"),
        model_dir=args.base_model_dir,
        epoch=resolved_base_epoch,
        device=device.type,
    )
    base_model = build_trajectron_from_checkpoint(base_cfg)
    base_model.to(device)
    base_model.eval()

    print("Loading Finetuned Model...")
    finetune_cfg = TrajectronLoadConfig(
        conf_path=os.path.join(args.finetuned_model_dir, "config.json"),
        model_dir=args.finetuned_model_dir,
        epoch=resolved_base_epoch,
        device=device.type,
    )
    finetune_model = build_trajectron_from_checkpoint(finetune_cfg)

    finetuned_ckpt_path = os.path.join(
        args.finetuned_model_dir, f"{args.finetuned_prefix}_{args.finetuned_epoch}.pt"
    )
    if os.path.exists(finetuned_ckpt_path):
        finetune_model.model_registrar.load_state_dict(
            torch.load(finetuned_ckpt_path, map_location=device, weights_only=False)
        )
    else:
        print(
            f"Warning: {finetuned_ckpt_path} not found. "
            "Proceeding with un-finetuned model weights for testing."
        )

    finetune_model.to(device)
    finetune_model.eval()

    scenarios = []
    if args.cache_path and os.path.exists(args.cache_path):
        import pickle

        with open(args.cache_path, "rb") as f:
            scenarios = pickle.load(f)
        print(f"[CompareVis] Loaded cache scenarios: {len(scenarios)}")
    else:
        print(f"[CompareVis] Cache file not found: {args.cache_path}")

    camp_preds = load_json_if_exists(args.camp_preds_path)
    reranker_preds = load_json_if_exists(args.reranker_preds_path)
    static_preds = load_json_if_exists(args.select_static_preds_path)

    multi_target = len(target_pairs) > 1 or bool(args.output_dir)
    rendered = 0
    for scene_idx, agent_idx in target_pairs:
        if scene_idx not in scene_batches:
            print(f"[CompareVis] Skipping missing scene {scene_idx}")
            continue

        output_path = build_output_path(args, scene_idx, agent_idx, multi_target)
        render_target(
            args=args,
            batch=scene_batches[scene_idx],
            scene_idx=scene_idx,
            agent_idx=agent_idx,
            base_model=base_model,
            finetune_model=finetune_model,
            device=device,
            scenarios=scenarios,
            camp_preds=camp_preds,
            reranker_preds=reranker_preds,
            static_preds=static_preds,
            output_path=output_path,
        )
        rendered += 1

    print(f"[CompareVis] Done. Rendered {rendered} figure(s).")


if __name__ == "__main__":
    main()
