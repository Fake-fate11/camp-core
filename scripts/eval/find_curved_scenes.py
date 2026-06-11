import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

# Work around protobuf/l5kit compatibility in some environments.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Find high-curvature validation scenes for qualitative visualization")
    parser.add_argument("--data_root", type=str, default="/root/autodl-tmp/dataset")
    parser.add_argument("--cache_dir", type=str, default="/root/autodl-tmp/.unified_data_cache")
    parser.add_argument("--split", type=str, default="nusc_trainval-val")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--top_k", type=int, default=10)
    parser.add_argument("--min_valid_points", type=int, default=10)
    parser.add_argument("--min_start_speed_m", type=float, default=1.0)
    parser.add_argument("--output_path", type=str, default="results/curved_targets.json")
    return parser.parse_args()


def main():
    args = parse_args()

    print("Initializing unshuffled dataloader...")
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
    dataloader = bridge.get_dataloader()

    print("Scanning for sharp turns in the unshuffled validation set...")
    turn_magnitudes = []

    for idx, batch in enumerate(dataloader):
        num_agents = batch.agent_fut.shape[0]
        for agent_idx in range(num_agents):
            gt = batch.agent_fut[agent_idx].cpu().numpy()
            valid = ~np.isnan(gt).any(axis=-1)
            if valid.sum() < args.min_valid_points:
                continue

            gt_valid = gt[valid]
            v_start = gt_valid[2, :2] - gt_valid[0, :2]
            norm_start = np.linalg.norm(v_start)
            if norm_start < args.min_start_speed_m:
                continue

            # True lateral deviation from initial heading line.
            vector_to_end = gt_valid[-1, :2] - gt_valid[0, :2]
            lateral_dev = np.abs(np.cross(v_start, vector_to_end)) / norm_start
            turn_magnitudes.append((idx, agent_idx, float(lateral_dev), str(batch.agent_name[agent_idx])))

    turn_magnitudes.sort(key=lambda x: x[2], reverse=True)
    top_items = turn_magnitudes[: args.top_k]

    print(f"\nTop {len(top_items)} unshuffled scene indices:")
    targets = []
    for rank, (scene_idx, agent_idx, lat_dev, name) in enumerate(top_items, start=1):
        print(
            f"Rank {rank:2d} | Scene Index: {scene_idx:4d} | "
            f"Agent Index: {agent_idx} ({name}) | Lateral Dev: {lat_dev:.2f} m"
        )
        targets.append(
            {
                "rank": rank,
                "scene_idx": int(scene_idx),
                "agent_idx": int(agent_idx),
                "agent_name": name,
                "lateral_dev": float(lat_dev),
            }
        )

    output = {
        "split": args.split,
        "top_k": int(args.top_k),
        "targets": targets,
    }

    if args.output_path:
        output_dir = os.path.dirname(args.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(args.output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\nSaved target list to {args.output_path}")


if __name__ == "__main__":
    main()
