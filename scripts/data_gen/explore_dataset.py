import os
import sys
import torch
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge
)

def explore_split(split_name, desc):
    print(f"\n--- Exploring Split: {split_name} ({desc}) ---")
    cfg = NuscenesDatasetConfig(
        data_root="/root/autodl-tmp/dataset",
        cache_dir="/root/autodl-tmp/.unified_data_cache",
        batch_size=1,
        num_workers=0,
        split=split_name,
        use_vector_map=True,
        unified_dataset_kwargs={"history_sec": (0.0, 0.0), "future_sec": (0.0, 0.0)}
    )
    try:
        bridge = NuscenesTrajdataBridge(cfg)
        dataset = bridge.dataset
        # Number of samples is length of dataset
        num_samples = len(dataset)
        print(f"[{split_name}] Total valid scenarios (samples): {num_samples}")
        
    except Exception as e:
        print(f"Error loading {split_name}: {e}")

if __name__ == "__main__":
    print("=== NuScenes Dataset Explorer ===")
    
    # Check all common splits
    splits = [
        ("nusc_trainval-train", "Full Official Training Set"),
        ("nusc_trainval-val", "Full Official Validation Set"),
        ("nusc_mini-mini_train", "Mini Training Subset"),
        ("nusc_mini-mini_val", "Mini Validation Subset")
    ]
    
    for spl, desc in splits:
        explore_split(spl, desc)
