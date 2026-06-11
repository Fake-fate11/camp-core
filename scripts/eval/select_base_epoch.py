import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import List

# Work around protobuf/l5kit compatibility in some environments.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import numpy as np
import torch
from tqdm import tqdm

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.base_predictor.trajectron_loader import (  # noqa: E402
    TrajectronLoadConfig,
    build_trajectron_from_checkpoint,
)
from camp_core.data_interfaces.nuscenes_trajdata_bridge import (  # noqa: E402
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
)


def compute_ade(pred: np.ndarray, gt: np.ndarray) -> float:
    min_len = min(len(pred), len(gt))
    if min_len == 0:
        return float("nan")
    valid_mask = ~np.isnan(gt[:min_len]).any(axis=-1)
    if not valid_mask.any():
        return float("nan")
    return float(np.mean(np.linalg.norm(pred[:min_len][valid_mask] - gt[:min_len][valid_mask], axis=-1)))


def compute_fde(pred: np.ndarray, gt: np.ndarray) -> float:
    min_len = min(len(pred), len(gt))
    if min_len == 0:
        return float("nan")
    valid_mask = ~np.isnan(gt[:min_len]).any(axis=-1)
    if not valid_mask.any():
        return float("nan")
    valid_indices = np.where(valid_mask)[0]
    last_idx = int(valid_indices[-1])
    return float(np.linalg.norm(pred[last_idx] - gt[last_idx]))


def list_available_epochs(model_dir: str) -> List[int]:
    path = Path(model_dir)
    epochs = []
    for ckpt in path.glob("model_registrar-*.pt"):
        match = re.search(r"model_registrar-(\d+)\.pt$", ckpt.name)
        if match:
            epochs.append(int(match.group(1)))
    return sorted(set(epochs))


def parse_args():
    parser = argparse.ArgumentParser(description="Scan Trajectron checkpoints and select best base epoch on validation split.")
    parser.add_argument("--data_root", type=str, default="/root/autodl-tmp/dataset")
    parser.add_argument("--cache_dir", type=str, default="/root/autodl-tmp/.unified_data_cache")
    parser.add_argument("--traj_conf_path", type=str, required=True)
    parser.add_argument("--traj_model_dir", type=str, required=True)
    parser.add_argument("--split", type=str, default="nusc_trainval-val")
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--max_scenarios", type=int, default=2000)
    parser.add_argument("--epoch_start", type=int, default=1)
    parser.add_argument("--epoch_end", type=int, default=-1, help="<=0 means latest available epoch.")
    parser.add_argument("--epoch_step", type=int, default=1)
    parser.add_argument(
        "--epochs",
        type=str,
        default="",
        help='Optional explicit epoch list, e.g. "20,40,60,80,100". If provided, overrides start/end/step.',
    )
    parser.add_argument(
        "--objective",
        type=str,
        default="ade",
        choices=["ade", "fde", "ade_fde"],
        help="Metric used to pick best epoch.",
    )
    parser.add_argument("--output_path", type=str, default="results/base_epoch_scan.json")
    return parser.parse_args()


def main():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    available_epochs = list_available_epochs(args.traj_model_dir)
    if not available_epochs:
        raise FileNotFoundError(
            f"No model_registrar-*.pt checkpoints found under {args.traj_model_dir}"
        )

    if args.epochs.strip():
        target_epochs = [int(x.strip()) for x in args.epochs.split(",") if x.strip()]
    else:
        epoch_end = max(available_epochs) if args.epoch_end <= 0 else args.epoch_end
        target_epochs = list(range(args.epoch_start, epoch_end + 1, args.epoch_step))

    target_epochs = [ep for ep in target_epochs if ep in available_epochs]
    if not target_epochs:
        raise ValueError(
            "No target epochs exist in checkpoint directory. "
            f"Available: {available_epochs[:10]}... (total={len(available_epochs)})"
        )

    print(f"[BaseScan] Evaluating epochs: {target_epochs}")

    cfg = NuscenesDatasetConfig(
        data_root=args.data_root,
        cache_dir=args.cache_dir,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        shuffle=False,
        split=args.split,
        use_vector_map=True,
        unified_dataset_kwargs={"history_sec": (2.0, 2.0), "future_sec": (6.0, 6.0)},
    )
    bridge = NuscenesTrajdataBridge(cfg)

    results = []
    for epoch in target_epochs:
        print(f"\n[BaseScan] Epoch {epoch}")
        loader = bridge.get_dataloader()

        load_cfg = TrajectronLoadConfig(
            conf_path=args.traj_conf_path,
            model_dir=args.traj_model_dir,
            epoch=epoch,
            device=device.type,
        )
        model = build_trajectron_from_checkpoint(load_cfg)
        model.to(device).eval()

        ades = []
        fdes = []
        processed = 0

        pbar = tqdm(loader, desc=f"Epoch {epoch}", leave=False)
        for batch in pbar:
            if processed >= args.max_scenarios:
                break

            batch.to(device)
            ph = model.hyperparams.get("prediction_horizon", 12)
            with torch.no_grad():
                preds = model.predict(
                    batch,
                    prediction_horizon=ph,
                    num_samples=1,
                    z_mode=False,
                    gmm_mode=True,
                    output_dists=False,
                )

            from trajdata import AgentType

            B = batch.curr_agent_state.shape[0]
            for i in range(B):
                if processed >= args.max_scenarios:
                    break

                node_type = (
                    AgentType(batch.agent_type[i].item())
                    if hasattr(batch, "agent_type")
                    else "VEHICLE"
                )
                agent_name = batch.agent_name[i]
                key = f"{str(node_type)}/{agent_name}"

                if key in preds:
                    pred_traj = preds[key][0]
                else:
                    pred_traj = np.zeros((ph, 2), dtype=np.float32)

                gt_traj = batch.agent_fut[i].detach().cpu().numpy()
                gt_len = (
                    int(batch.agent_fut_len[i].item())
                    if hasattr(batch, "agent_fut_len")
                    else len(gt_traj)
                )
                gt_traj = gt_traj[:gt_len, :2]

                ade = compute_ade(pred_traj, gt_traj)
                fde = compute_fde(pred_traj, gt_traj)
                if not np.isnan(ade):
                    ades.append(float(ade))
                if not np.isnan(fde):
                    fdes.append(float(fde))
                processed += 1

        mean_ade = float(np.mean(ades)) if ades else float("nan")
        mean_fde = float(np.mean(fdes)) if fdes else float("nan")
        score = (
            mean_ade
            if args.objective == "ade"
            else mean_fde
            if args.objective == "fde"
            else (mean_ade + 0.1 * mean_fde)
        )
        if np.isnan(score):
            score = float("inf")

        print(f"[BaseScan] epoch={epoch} | ADE={mean_ade:.4f} | FDE={mean_fde:.4f} | score={score:.4f}")
        results.append(
            {
                "epoch": epoch,
                "Mean_ADE": mean_ade,
                "Mean_FDE": mean_fde,
                "score": score,
                "num_scenarios": processed,
            }
        )

    results_sorted = sorted(results, key=lambda x: x["score"])
    best = results_sorted[0]
    print(
        f"\n[BaseScan] Best epoch by {args.objective}: {best['epoch']} "
        f"(ADE={best['Mean_ADE']:.4f}, FDE={best['Mean_FDE']:.4f})"
    )

    output = {
        "objective": args.objective,
        "best_epoch": int(best["epoch"]),
        "candidates": results_sorted,
    }

    output_dir = os.path.dirname(args.output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(args.output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"[BaseScan] Saved to {args.output_path}")


if __name__ == "__main__":
    main()
