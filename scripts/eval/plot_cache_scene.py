import argparse
import os
import json
import pickle
import numpy as np
import matplotlib.pyplot as plt

def parse_args():
    parser = argparse.ArgumentParser(description="Plot Trajectories directly from Evaluation Cache")
    parser.add_argument("--cache_path", type=str, default="data/cached_eval_batch.pkl")
    parser.add_argument("--target_scene_idx", type=int, default=3525, help="Index of the scene in the cache")
    parser.add_argument("--output_path", type=str, default="figures/cache_trajectory_plot.png")
    return parser.parse_args()

def main():
    args = parse_args()
    
    if not os.path.exists(args.cache_path):
        print(f"Error: Cache file {args.cache_path} not found.")
        return

    # 1. Load Cache
    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)
        
    if args.target_scene_idx >= len(scenarios):
        print(f"Error: Target scene index {args.target_scene_idx} out of bounds (Max {len(scenarios)-1}).")
        return
        
    sc = scenarios[args.target_scene_idx]
    cands = sc["candidates"]   # [K, H, 2]
    gt = sc["gt_traj"]         # [H, 2]
    
    # 2. Identify Selected Candidate Paths
    # Pred Top1
    base_traj = cands[0]
    
    # Oracle MinADE
    ade_costs = []
    for c in cands:
        min_len = min(len(c), len(gt))
        valid = ~np.isnan(gt[:min_len]).any(axis=-1)
        ade = np.mean(np.linalg.norm(c[:min_len][valid] - gt[:min_len][valid], axis=-1)) if valid.any() else 0.0
        ade_costs.append(ade)
    oracle_traj = cands[np.argmin(ade_costs)]
    
    # Camp Select
    camp_traj = None
    if os.path.exists("results/camp_select_preds.json"):
        with open("results/camp_select_preds.json", "r") as f:
            camp_idx = json.load(f).get(f"sc_{args.target_scene_idx}", 0)
            camp_traj = cands[camp_idx]
            
    # Reranker Safe
    reranker_traj = None
    if os.path.exists("results/reranker_safe_preds.json"):
        with open("results/reranker_safe_preds.json", "r") as f:
            rerank_idx = json.load(f).get(f"sc_{args.target_scene_idx}", 0)
            reranker_traj = cands[rerank_idx]

    # 3. Plotting
    print(f"Plotting Pure Trajectories for Scene {args.target_scene_idx}...")
    fig, ax = plt.subplots(figsize=(10, 10), dpi=200)
    
    # Plot Valid Ground Truth
    min_len_gt = len(gt)
    valid_gt = ~np.isnan(gt[:min_len_gt]).any(axis=-1)
    ax.plot(gt[valid_gt, 0], gt[valid_gt, 1], color='black', linewidth=5, linestyle='--', marker='*', label="Ground Truth (125\u00b0 Turn)")
    
    # Plot Trajectories
    plots = [
        (base_traj, "Pred Top1", "#DD9787", "-"),           # Light Red
        (camp_traj, "Camp Select", "#9F9FED", "-"),         # Purple
        (reranker_traj, "Reranker Safe", "#A6C48A", "-"),   # Green
        (oracle_traj, "Oracle MinADE", "#A2999E", "--"),      # Gray Dashed
    ]
    
    for traj, name, color, style in plots:
        if traj is not None:
            ax.plot(
                traj[:, 0], traj[:, 1],
                color=color, linewidth=4, linestyle=style,
                marker="o", markersize=8, alpha=0.8,
                label=name
            )
            
    # Draw Origin
    ax.scatter([0], [0], color='red', s=200, edgecolors='black', zorder=5, label="Ego Start (0,0)")
    
    ax.legend(bbox_to_anchor=(1.04, 1.0), loc="upper left", borderaxespad=0, frameon=True)
    ax.set_title(f"Cache Candidates vs Ground Truth (Scene Index: {args.target_scene_idx})")
    
    # Square aspect ratio for true scaling
    ax.set_aspect("equal", adjustable="box")
    
    plot_radius = 50
    ax.set_xlim((-10, plot_radius))
    ax.set_ylim((-plot_radius, plot_radius))
    
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    fig.savefig(args.output_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Successfully saved cache trajectory visualization to {args.output_path}!")

if __name__ == "__main__":
    main()
