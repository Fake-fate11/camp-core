import argparse
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
if not os.environ.get("OMP_NUM_THREADS", "").isdigit() or int(os.environ.get("OMP_NUM_THREADS", "0") or 0) <= 0:
    os.environ["OMP_NUM_THREADS"] = "1"
import sys
import json
import time
import re
from pathlib import Path
import numpy as np
import torch
from tqdm import tqdm

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
    extract_driver_context,
)
from camp_core.base_predictor.trajectron_loader import (
    TrajectronLoadConfig,
    build_trajectron_from_checkpoint,
)
from camp_core.atoms.driver_atoms import compute_atom_bank_vector, compute_feasibility_mask


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
    v = np.diff(traj, axis=0) / dt
    if len(v) < 2: return 0.0, 0.0
    a = np.diff(v, axis=0) / dt
    if len(a) < 2: return np.sqrt(np.mean(np.sum(a**2, axis=-1))), 0.0
    j = np.diff(a, axis=0) / dt
    rms_a = np.float64(np.sqrt(np.mean(np.sum(a**2, axis=-1))))
    rms_j = np.float64(np.sqrt(np.mean(np.sum(j**2, axis=-1))))
    return rms_a, rms_j

def compute_cvar(costs, alpha=0.9):
    if len(costs) == 0: return 0.0
    sorted_costs = np.sort(costs)[::-1]
    tail_idx = max(1, int((1.0 - alpha) * len(costs)))
    tail_costs = sorted_costs[:tail_idx]
    return float(np.mean(tail_costs))

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
    parser = argparse.ArgumentParser(description="Evaluate Finetuned Trajectron++ directly into JSON metrics")
    parser.add_argument("--data_root", type=str, default="/root/autodl-tmp/dataset")
    parser.add_argument("--cache_dir", type=str, default="/root/autodl-tmp/.unified_data_cache")
    parser.add_argument("--traj_conf_path", type=str, required=True)
    parser.add_argument("--traj_model_dir", type=str, required=True)
    parser.add_argument(
        "--base_epoch",
        type=int,
        default=-1,
        help="Base checkpoint epoch used to construct Trajectron. <=0 means latest checkpoint.",
    )
    parser.add_argument("--finetuned_epoch", type=int, default=1)
    parser.add_argument("--finetuned_prefix", type=str, default="finetuned_safe")
    parser.add_argument("--split", type=str, default="nusc_trainval-val")
    parser.add_argument("--output_path", type=str, default="results/finetune_safe_metrics.json")
    parser.add_argument("--atom_scales_path", type=str, default="models/production/atom_scales.json")
    parser.add_argument("--atom_clip", type=float, default=10.0, help="Clip normalized atoms for Safety CVaR reporting")
    parser.add_argument("--safety_weight", type=float, default=0.1, help="Weight applied to speed/lane/clearance atoms for training-consistent CVaR")
    return parser.parse_args()

def main():
    args = parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print("=== Module 3: Evaluating Finetune Baseline ===")
    resolved_base_epoch = resolve_trajectron_epoch(args.traj_model_dir, args.base_epoch)
    print(f"[EvalFinetune] Using base checkpoint epoch: {resolved_base_epoch}")
    
    cfg = NuscenesDatasetConfig(
        data_root=args.data_root,
        cache_dir=args.cache_dir,
        batch_size=4,
        num_workers=0,
        shuffle=False, 
        split=args.split,
        use_vector_map=True,
        unified_dataset_kwargs={"history_sec": (2.0, 2.0), "future_sec": (6.0, 6.0)} 
    )
    bridge = NuscenesTrajdataBridge(cfg)
    dataloader = bridge.get_dataloader()
    map_api = bridge.dataset
    
    traj_cfg = TrajectronLoadConfig(
        conf_path=args.traj_conf_path,
        model_dir=args.traj_model_dir,
        epoch=resolved_base_epoch,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )
    
    # Needs full trajectron to do generation natively
    trajectron = build_trajectron_from_checkpoint(traj_cfg)
    
    # Load the finetuned checkpoint
    finetuned_ckpt_path = os.path.join(args.traj_model_dir, f"{args.finetuned_prefix}_{args.finetuned_epoch}.pt")
    if not os.path.exists(finetuned_ckpt_path):
        print(f"Error: Finetuned checkpoint {finetuned_ckpt_path} not found!")
        return
        
    print(f"Loading finetuned weights from {finetuned_ckpt_path}...")
    trajectron.model_registrar.load_state_dict(torch.load(finetuned_ckpt_path, map_location=device, weights_only=False))
    trajectron.to(device)
    trajectron.eval()
    
    metrics = {
        "ade": [], "fde": [], "rms_accel": [], "rms_jerk": [], 
        "safety_violations": [], "safety_cost": [],
        "safety_cost_unclipped_sum": [],
        "safety_cost_clipped_sum": [],
        "safety_cost_no_clearance": [],
    }
    
    # Helper scales
    scale_path = args.atom_scales_path
    if os.path.exists(scale_path):
        with open(scale_path, "r") as f:
            scales = np.array(json.load(f))
    else:
        scales = np.ones(9)
        
    ph = trajectron.hyperparams.get("prediction_horizon", 12)
    dt = trajectron.hyperparams.get("dt", 0.5)
        
    print("Generating trajectories and evaluating constraints...")
    pbar = tqdm(dataloader, desc="Eval Batch")
    scenarios_eval = 0
    
    for batch in pbar:
        batch.to(device)
        with torch.no_grad():
            from trajdata import AgentType
            # Output dict with node format keys
            predictions = trajectron.predict(
                 batch,
                 prediction_horizon=ph,
                 num_samples=1,
                 z_mode=False,
                 gmm_mode=True,
                 output_dists=False
            )
            
            B = batch.curr_agent_state.shape[0]
            for i in range(B):
                node_type = AgentType(batch.agent_type[i].item()) if hasattr(batch, 'agent_type') else 'VEHICLE'
                agent_name = batch.agent_name[i]
                key = f"{str(node_type)}/{agent_name}"
                
                if key in predictions:
                    # Select the Top-1 generated trajectory
                    pred_traj = predictions[key][0] # [H, 2]
                else:
                    pred_traj = np.zeros((ph, 2))
                    
                gt_traj = batch.agent_fut[i].cpu().numpy()
                gt_len = int(batch.agent_fut_len[i].item()) if hasattr(batch, 'agent_fut_len') else len(gt_traj)
                gt_traj = gt_traj[:gt_len, :2]
                
                # Context parsing for safety atom extraction
                try:
                    ctx = extract_driver_context(batch, i, map_api=map_api)
                    is_safe = compute_feasibility_mask(ctx, pred_traj)
                    atoms = compute_atom_bank_vector(ctx, pred_traj) / scales
                    
                    ade = compute_ade(pred_traj, gt_traj)
                    fde = compute_fde(pred_traj, gt_traj)
                    rms_a, rms_j = compute_kinematics(pred_traj, dt=dt)
                    
                    metrics["ade"].append(float(ade))
                    metrics["fde"].append(float(fde))
                    metrics["rms_accel"].append(float(rms_a))
                    metrics["rms_jerk"].append(float(rms_j))
                    metrics["safety_violations"].append(1.0 if not is_safe else 0.0)
                    unclip_sum, clip_sum, weighted_clip, no_clearance = safety_cost_variants(
                        atoms,
                        atom_clip=args.atom_clip,
                        safety_weight=args.safety_weight,
                    )
                    metrics["safety_cost"].append(weighted_clip)
                    metrics["safety_cost_unclipped_sum"].append(unclip_sum)
                    metrics["safety_cost_clipped_sum"].append(clip_sum)
                    metrics["safety_cost_no_clearance"].append(no_clearance)
                    
                    scenarios_eval += 1
                except Exception as e:
                    print(f"Exception during evaluation of agent {agent_name}: {e}")
                    continue
                    
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
        "CVaR_0.90_Safety": float(compute_cvar(np.array(safe_cost_valid))) if len(safe_cost_valid) > 0 else float('nan'),
        "CVaR_0.90_Safety_WeightedClipped": float(compute_cvar(np.array(safe_cost_valid))) if len(safe_cost_valid) > 0 else float('nan'),
        "CVaR_0.90_Safety_UnclippedSum": float(compute_cvar(np.array(safe_unclipped_valid))) if len(safe_unclipped_valid) > 0 else float('nan'),
        "CVaR_0.90_Safety_ClippedSum": float(compute_cvar(np.array(safe_clipped_valid))) if len(safe_clipped_valid) > 0 else float('nan'),
        "CVaR_0.90_Safety_NoClearance": float(compute_cvar(np.array(safe_no_clearance_valid))) if len(safe_no_clearance_valid) > 0 else float('nan'),
        "Safety_CVaR_Report": "weighted_clipped",
        "Safety_Atom_Clip": float(args.atom_clip),
        "Safety_Atom_Weight": float(args.safety_weight),
    }
    
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, "w") as f:
        json.dump(summary, f, indent=4)
        
    print(f"Saved Finetune Safe metrics to {args.output_path}")

if __name__ == "__main__":
    main()
