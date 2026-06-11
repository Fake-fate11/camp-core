import argparse
import os
import sys
import pickle
import json
import numpy as np

def compute_ade(pred, gt):
    """Compute Average Displacement Error over the sequence length"""
    # Align lengths if mismatched due to early termination or different horizon setups
    min_len = min(len(pred), len(gt))
    if min_len == 0: return 0.0
    return np.mean(np.linalg.norm(pred[:min_len] - gt[:min_len], axis=-1))

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Heuristics and Oracle Baselines")
    parser.add_argument("--cache_path", type=str, required=True, help="Path to cached scenarios (.pkl)")
    parser.add_argument("--output_dir", type=str, default="results", help="Directory to save the prediction JSONs")
    parser.add_argument("--offline_weights_path", type=str, default="models/offline_weights.npy", help="Path to bt_warmup weights for Select-Static")
    parser.add_argument("--atom_scales_path", type=str, default="models/production/atom_scales.json")
    parser.add_argument("--atom_clip", type=float, default=10.0, help="Clip normalized atoms for selection; <=0 disables clipping")
    return parser.parse_args()

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 1. Load Data Cache
    print(f"Loading cached scenarios from {args.cache_path}...")
    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)
        
    print(f"Loaded {len(scenarios)} scenarios.")
    
    # We output a dictionary: {scene_index: selected_candidate_index}
    # Scene IDs might not be unique if sampled, so we use list index as ID for mapping.
    
    results = {
        "pred_top1": {},
        "select_static": {},
        "oracle_minade": {}
    }
    
    # 2. Load Select-Static Weights
    static_weights = None
    if os.path.exists(args.offline_weights_path):
        static_weights = np.load(args.offline_weights_path)
        print(f"Loaded Static Weights from {args.offline_weights_path}: {static_weights}")
    elif os.path.exists("models/camp_select_linear.pt"):
        import torch
        print("Extracting offline static weights from models/camp_select_linear.pt...")
        ckpt = torch.load("models/camp_select_linear.pt", map_location="cpu", weights_only=False)
        static_weights = ckpt.get("offline_weights", None)
        if static_weights is not None:
            print(f"Loaded Embedded Static Weights: {static_weights}")
        
    if static_weights is None:
        # Uniform fallback
        if len(scenarios) > 0:
            num_atoms = scenarios[0]["atoms"].shape[1]
            static_weights = np.ones(num_atoms) / num_atoms
            print("Warning: offline weights not found. Using uniform weights for Select-Static.")
            
    # Load Atom Scales implicitly?
    # At deployment, Select-Static scores need to use normalized atoms
    scale_path = args.atom_scales_path
    if os.path.exists(scale_path):
        with open(scale_path, "r") as f:
            scales = np.array(json.load(f), dtype=np.float32)
    else:
        scales = np.ones(static_weights.shape[0], dtype=np.float32)
    
    print("Evaluating Baselines...")
    for idx, sc in enumerate(scenarios):
        scene_key = f"sc_{idx}"
        
        cands = sc["candidates"] # [K, H, 2]
        gt_traj = sc["gt_traj"] # [H, 2]
        atoms = sc["atoms"] / scales # [K, R] normalized
        if args.atom_clip > 0:
            atoms = np.clip(np.nan_to_num(atoms, nan=0.0, posinf=args.atom_clip, neginf=0.0), 0.0, args.atom_clip)
        feas_mask = sc["feas_mask"] # [K]
        
        K = len(cands)
        
        # --- Pred-Top1 ---
        # The Trajectron model returns predictions in order of probability, so index 0 is Top-1
        results["pred_top1"][scene_key] = 0
        
        # --- Select-Static ---
        # w_off @ atoms
        scores = (atoms * static_weights).sum(axis=-1)
        # Apply hard constraints if available
        scores_inf = scores.copy()
        scores_inf[~feas_mask] = float('inf')
        
        if np.isinf(scores_inf).all():
            best_idx = int(np.argmin(scores)) # Fallback to unmasked
        else:
            best_idx = int(np.argmin(scores_inf))
        
        results["select_static"][scene_key] = best_idx
        
        # --- Oracle-MinADE ---
        ade_list = []
        for k in range(K):
            ade = compute_ade(cands[k], gt_traj)
            ade_list.append(ade)
            
        best_oracle_idx = int(np.argmin(ade_list))
        results["oracle_minade"][scene_key] = best_oracle_idx
        
    # Save the output dictionaries
    for method, preds in results.items():
        out_path = os.path.join(args.output_dir, f"{method}_preds.json")
        with open(out_path, "w") as f:
            json.dump(preds, f, indent=4)
        print(f"Saved {method} predictions to {out_path}.")
        
if __name__ == "__main__":
    main()
