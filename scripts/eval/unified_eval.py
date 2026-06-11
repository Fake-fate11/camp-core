import argparse
import json
import os
import pickle

if not os.environ.get("OMP_NUM_THREADS", "").isdigit() or int(os.environ.get("OMP_NUM_THREADS", "0") or 0) <= 0:
    os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

def compute_ade(pred, gt):
    min_len = min(len(pred), len(gt))
    if min_len == 0: return 0.0
    valid_mask = ~np.isnan(gt[:min_len]).any(axis=-1)
    if not valid_mask.any(): return np.nan
    return np.mean(np.linalg.norm(pred[:min_len][valid_mask] - gt[:min_len][valid_mask], axis=-1))

def compute_fde(pred, gt):
    min_len = min(len(pred), len(gt))
    if min_len == 0: return 0.0
    valid_mask = ~np.isnan(gt[:min_len]).any(axis=-1)
    if not valid_mask.any(): return np.nan
    valid_indices = np.where(valid_mask)[0]
    last_idx = valid_indices[-1]
    return np.linalg.norm(pred[last_idx] - gt[last_idx])

def compute_kinematics(traj, dt=0.5):
    # traj: [H, 2]
    # v: [H-1, 2], a: [H-2, 2], j: [H-3, 2]
    v = np.diff(traj, axis=0) / dt
    if len(v) < 2: return 0.0, 0.0 # Fallback
    a = np.diff(v, axis=0) / dt
    if len(a) < 2: return np.sqrt(np.mean(np.sum(a**2, axis=-1))), 0.0
    j = np.diff(a, axis=0) / dt
    
    rms_a = np.sqrt(np.mean(np.sum(a**2, axis=-1)))
    rms_j = np.sqrt(np.mean(np.sum(j**2, axis=-1)))
    return rms_a, rms_j

def compute_cvar(costs, alpha=0.9):
    if len(costs) == 0: return 0.0
    sorted_costs = np.sort(costs)[::-1] # descending
    tail_idx = max(1, int((1.0 - alpha) * len(costs)))
    tail_costs = sorted_costs[:tail_idx]
    return np.mean(tail_costs)

def safety_cost_variants(atoms_norm, atom_clip=10.0, safety_weight=0.1):
    atoms_norm = np.asarray(atoms_norm, dtype=np.float32)
    atoms_clip = np.clip(
        np.nan_to_num(atoms_norm, nan=0.0, posinf=atom_clip, neginf=0.0),
        0.0,
        atom_clip,
    )
    if len(atoms_norm) >= 9:
        unclip_sum = float(np.sum(atoms_norm[4:9]))
        clip_sum = float(np.sum(atoms_clip[4:9]))
        weighted_clip = float(safety_weight * np.sum(atoms_clip[4:9]))
        no_clearance = float(np.sum(atoms_clip[4:8]))
    else:
        unclip_sum = float(np.sum(atoms_norm))
        clip_sum = float(np.sum(atoms_clip))
        weighted_clip = float(safety_weight * np.sum(atoms_clip))
        no_clearance = clip_sum
    return unclip_sum, clip_sum, weighted_clip, no_clearance

def parse_args():
    parser = argparse.ArgumentParser(description="Unified Evaluation Engine")
    parser.add_argument("--cache_path", type=str, required=True, help="Path to evaluation cache (.pkl)")
    parser.add_argument("--preds_path", type=str, required=True, help="Path to model predictions (.json mapping scene_id to selected_idx)")
    parser.add_argument("--output_path", type=str, required=True, help="Path to save the metrics summary JSON")
    parser.add_argument("--dt", type=float, default=0.5, help="Time step for kinematic derivation")
    parser.add_argument("--atom_scales_path", type=str, default="models/production/atom_scales.json")
    parser.add_argument("--atom_clip", type=float, default=10.0, help="Clip normalized atoms for Safety CVaR reporting")
    parser.add_argument("--safety_weight", type=float, default=0.1, help="Weight applied to speed/lane/clearance atoms for training-consistent CVaR")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # 1. Load Data
    print(f"Loading cache from {args.cache_path}...")
    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)
        
    print(f"Loading predictions from {args.preds_path}...")
    with open(args.preds_path, "r") as f:
        preds = json.load(f)
        
    # Scale loading
    scale_path = args.atom_scales_path
    if os.path.exists(scale_path):
        with open(scale_path, "r") as f:
            scales = np.array(json.load(f), dtype=np.float32)
    else:
        scales = None

    metrics = {
        "ade": [],
        "fde": [],
        "rms_accel": [],
        "rms_jerk": [],
        "safety_violations": [],
        "safety_cost": [],
        "safety_cost_unclipped_sum": [],
        "safety_cost_clipped_sum": [],
        "safety_cost_weighted_clipped": [],
        "safety_cost_no_clearance": [],
    }
    
    missing_preds = 0
    total_scenes = len(scenarios)
    
    for idx, sc in enumerate(scenarios):
        scene_key = f"sc_{idx}"
        if scene_key not in preds:
            missing_preds += 1
            continue
            
        selected_idx = preds[scene_key]
        cands = sc["candidates"]
        gt_traj = sc["gt_traj"]
        feas_mask = sc["feas_mask"]
        atoms = sc["atoms"]
        
        if scales is not None:
             atoms = atoms / scales
        
        # Guard bounds
        if selected_idx >= len(cands):
            selected_idx = 0
            
        pred_traj = cands[selected_idx]
        
        # Prediction Error
        ade = compute_ade(pred_traj, gt_traj)
        metrics["ade"].append(ade)
        fde = compute_fde(pred_traj, gt_traj)
        metrics["fde"].append(fde)
        
        # Comfort
        rms_a, rms_j = compute_kinematics(pred_traj, dt=args.dt)
        metrics["rms_accel"].append(rms_a)
        metrics["rms_jerk"].append(rms_j)
        
        # Safety / Feasibility (Independent wrapper)
        # feas_mask encodes hard bounds (collisions, road edges). 
        # If the selected candidate is False, it's a violation.
        is_safe = feas_mask[selected_idx]
        metrics["safety_violations"].append(1.0 if not is_safe else 0.0)
        
        raw_atom = atoms[selected_idx]
        unclip_sum, clip_sum, weighted_clip, no_clearance = safety_cost_variants(
            raw_atom,
            atom_clip=args.atom_clip,
            safety_weight=args.safety_weight,
        )
        # Main safety_cost is training-consistent: normalized, clipped, and weighted.
        metrics["safety_cost"].append(weighted_clip)
        metrics["safety_cost_unclipped_sum"].append(unclip_sum)
        metrics["safety_cost_clipped_sum"].append(clip_sum)
        metrics["safety_cost_weighted_clipped"].append(weighted_clip)
        metrics["safety_cost_no_clearance"].append(no_clearance)

    if missing_preds > 0:
        print(f"Warning: Missing predictions for {missing_preds}/{total_scenes} scenes.")
        
    # Aggregate
    if len(metrics["ade"]) == 0:
        print("No valid predictions evaluated.")
        return
        
    # Filter out NaNs for aggregation
    ade_valid = [x for x in metrics["ade"] if not np.isnan(x)]
    fde_valid = [x for x in metrics["fde"] if not np.isnan(x)]
    safe_cost_valid = [x for x in metrics["safety_cost"] if not np.isnan(x)]
    safe_unclipped_valid = [x for x in metrics["safety_cost_unclipped_sum"] if not np.isnan(x)]
    safe_clipped_valid = [x for x in metrics["safety_cost_clipped_sum"] if not np.isnan(x)]
    safe_no_clearance_valid = [x for x in metrics["safety_cost_no_clearance"] if not np.isnan(x)]
    
    summary = {
        "Mean_ADE": float(np.mean(ade_valid)) if len(ade_valid) > 0 else float('nan'),
        "Mean_FDE": float(np.mean(fde_valid)) if len(fde_valid) > 0 else float('nan'),
        "Violation_Rate": float(np.mean(metrics["safety_violations"])),
        "RMS_Accel": float(np.mean(metrics["rms_accel"])),
        "RMS_Jerk": float(np.mean(metrics["rms_jerk"])),
        "CVaR_0.90_Safety": float(compute_cvar(np.array(safe_cost_valid), alpha=0.9)) if len(safe_cost_valid) > 0 else float('nan'),
        "CVaR_0.90_Safety_WeightedClipped": float(compute_cvar(np.array(safe_cost_valid), alpha=0.9)) if len(safe_cost_valid) > 0 else float('nan'),
        "CVaR_0.90_Safety_UnclippedSum": float(compute_cvar(np.array(safe_unclipped_valid), alpha=0.9)) if len(safe_unclipped_valid) > 0 else float('nan'),
        "CVaR_0.90_Safety_ClippedSum": float(compute_cvar(np.array(safe_clipped_valid), alpha=0.9)) if len(safe_clipped_valid) > 0 else float('nan'),
        "CVaR_0.90_Safety_NoClearance": float(compute_cvar(np.array(safe_no_clearance_valid), alpha=0.9)) if len(safe_no_clearance_valid) > 0 else float('nan'),
        "Safety_CVaR_Report": "weighted_clipped",
        "Safety_Atom_Clip": float(args.atom_clip),
        "Safety_Atom_Weight": float(args.safety_weight),
    }
    
    print("\n--- Evaluation Summary ---")
    for k, v in summary.items():
        if isinstance(v, (float, int, np.floating, np.integer)):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")
        
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, "w") as f:
        json.dump(summary, f, indent=4)
        
    print(f"\nSaved metrics to {args.output_path}")

if __name__ == "__main__":
    main()
