import argparse
import os
import sys
import json
import time
import pickle
import numpy as np
import torch

def simplex_proj(v: np.ndarray) -> np.ndarray:
    """Project onto probability simplex."""
    v_sorted = np.sort(v)[::-1]
    cssv = np.cumsum(v_sorted) - 1
    ind = np.arange(1, len(v) + 1)
    cond = v_sorted - cssv / ind > 0
    rho = ind[cond][-1]
    theta_sum = cssv[rho - 1] / rho
    return np.maximum(v - theta_sum, 0)

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate CAMP Baseline")
    parser.add_argument("--cache_path", type=str, required=True, help="Path to evaluation cache (.pkl)")
    parser.add_argument("--model_path", type=str, required=True, help="Path to trained Master .pt")
    parser.add_argument("--output_path", type=str, required=True, help="Path to save JSON predictions")
    parser.add_argument("--atom_scales_path", type=str, default="models/production/atom_scales.json")
    parser.add_argument("--atom_clip", type=float, default=10.0, help="Clip normalized atoms for selection; <=0 disables clipping")
    return parser.parse_args()

def main():
    args = parse_args()
    device = torch.device("cpu") # Theta evaluation is fast on CPU

    print("=== Module 3: Inference Engine & Deployment ===")

    # 1. Load Data Cache
    print(f"Loading cached scenarios from {args.cache_path}...")
    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)
        
    if len(scenarios) == 0:
        print("Empty cache.")
        return
        
    print(f"Loaded {len(scenarios)} scenarios.")

    # Load Atom Scales
    sc0 = scenarios[0]
    R = sc0["atoms"].shape[1]
    scale_path = args.atom_scales_path
    if os.path.exists(scale_path):
        with open(scale_path, "r") as f:
            scales = np.array(json.load(f), dtype=np.float32)
    else:
        scales = np.ones(R, dtype=np.float32)

    w_safe = np.ones(R) / R

    # 2. Load Model
    print(f"Loading Master trained parameters from {args.model_path}...")
    checkpoint = torch.load(args.model_path, map_location=device, weights_only=False)
    Theta_w = checkpoint["Theta"] # [R, D+1] from CVXPY
    print(f"Loaded Theta_w shape: {Theta_w.shape}")

    results = {}
    total_latency = 0.0

    # 3. Evaluate
    print("Scoring candidates...")
    for idx, sc in enumerate(scenarios):
        scene_key = f"sc_{idx}"
        
        t_start = time.time()
        phi = sc["embedding"] # [D]
        phi_aug = np.append(phi, 1.0) # [D+1]
        
        w_raw = Theta_w @ phi_aug # [R]
        w = simplex_proj(w_raw) # Projected onto simplex
        
        cands = sc["candidates"]
        atoms = sc["atoms"] / scales # [K, R]
        if args.atom_clip > 0:
            atoms = np.clip(np.nan_to_num(atoms, nan=0.0, posinf=args.atom_clip, neginf=0.0), 0.0, args.atom_clip)
        feas_mask = sc["feas_mask"] # [K]
        
        scores = (atoms * w).sum(axis=-1) # [K]
        
        if feas_mask.any():
            scores[~feas_mask] = float('inf')
            best_idx = int(np.argmin(scores))
        else:
            fallback_scores = (atoms * w_safe).sum(axis=-1)
            best_idx = int(np.argmin(fallback_scores))
            
        total_latency += (time.time() - t_start)
        results[scene_key] = best_idx
            
    # 4. Save
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"Saved CAMP Selection predictions to {args.output_path}.")
    avg_lat = (total_latency / len(scenarios)) * 1000
    print(f"Avg Selection Latency: {avg_lat:.2f} ms")

if __name__ == "__main__":
    main()
