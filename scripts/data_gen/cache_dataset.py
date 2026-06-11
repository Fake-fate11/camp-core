import argparse
import os
import sys
import time
import pickle
import re
import numpy as np
import torch
from pathlib import Path
from tqdm import tqdm

# Work around protobuf/l5kit compatibility in some environments.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
    extract_driver_context,
)
from camp_core.atoms.driver_atoms import compute_atom_bank_vector, compute_feasibility_mask
from camp_core.base_predictor.trajectron_loader import (
    TrajectronLoadConfig,
    build_trajectron_adapter_from_checkpoint,
)


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
            "Please pass --trajectron_epoch explicitly."
        )

    return max(epochs)

def get_top_k_predictions(adapter, batch, k=6, z_mode=False, gmm_mode=True):
    trajectron = adapter.base_model
    
    # [BUGFIX] Force Trajectron++ to actually sample diversely across modes.
    # Without this, pre-trained models default to 'single_mode_multi_sample=True'
    # which collapses all 30 predictions into the exact same trajectory.
    trajectron.hyperparams['single_mode_multi_sample'] = False
    
    ph = trajectron.hyperparams.get("prediction_horizon", 12)
    device = next(trajectron.parameters()).device
    batch.to(device)
    
    with torch.no_grad():
        predictions_dict = trajectron.predict(
            batch,
            prediction_horizon=ph,
            num_samples=k,
            z_mode=z_mode,
            gmm_mode=gmm_mode,
            output_dists=False
        )
        predictions_list = [predictions_dict]
    
    from trajdata import AgentType
    batch_preds = []
    
    for i in range(len(batch.agent_name)):
        node_type = AgentType(batch.agent_type[i].item()) if hasattr(batch, 'agent_type') else 'VEHICLE'
        agent_name = batch.agent_name[i]
        key = f"{str(node_type)}/{agent_name}"
        
        agent_k_preds = []
        for p_dict in predictions_list:
            if key in p_dict:
                 p = p_dict[key]
                 if hasattr(p, 'cpu'): p = p.cpu().numpy()
                 agent_k_preds.append(p)
            else:
                 agent_k_preds.append(np.zeros((1, ph, 2)))
        
        if len(predictions_list) > 1:
            combined = np.concatenate(agent_k_preds, axis=0)
        else:
            combined = agent_k_preds[0]
            
        batch_preds.append(combined)
             
    return batch_preds

def parse_args():
    parser = argparse.ArgumentParser(description="CAMP Module 1: Data Pipeline & Caching")
    parser.add_argument("--data_root", type=str, default="/root/autodl-tmp/dataset")
    parser.add_argument("--cache_dir", type=str, default="/root/autodl-tmp/.unified_data_cache")
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--num_scenarios", type=int, default=-1, help="-1 for all scenarios in the split")
    parser.add_argument("--num_candidates", type=int, default=12, help="Number of Trajectron++ candidates per scenario")
    parser.add_argument(
        "--rebuild_trajdata_cache",
        action="store_true",
        help="force trajdata to rebuild scene metadata/agent cache before caching CAMP scenarios",
    )
    
    parser.add_argument("--embedding_dim", type=int, default=64)
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--output_path", type=str, default="data/cached_batch.pkl")
    
    parser.add_argument("--trajectron_conf", type=str, required=True)
    parser.add_argument("--trajectron_model_dir", type=str, required=True)
    parser.add_argument(
        "--trajectron_epoch",
        type=int,
        default=-1,
        help="Trajectron checkpoint epoch. <=0 means auto-select latest checkpoint.",
    )
    parser.add_argument("--split", type=str, default="nusc_trainval-val")

    return parser.parse_args()

def main():
    args = parse_args()
    device = torch.device(args.device)
    
    print("=== Module 1: Data Pipeline & Caching ===")
    print(f"[CacheDataset] num_candidates={args.num_candidates}", flush=True)
    start_time = time.time()
    
    # Smart Shuffle: True for train, False for val/test
    is_train_split = args.split.endswith("train")
    
    cfg = NuscenesDatasetConfig(
        data_root=args.data_root,
        cache_dir=args.cache_dir,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        split=args.split,
        shuffle=is_train_split, # Automatically infers if shuffling is needed
        use_vector_map=True,
        rebuild_cache=args.rebuild_trajdata_cache,
    )
    bridge = NuscenesTrajdataBridge(cfg)
    dataloader = bridge.get_dataloader()
    map_api = bridge.dataset
    
    resolved_epoch = resolve_trajectron_epoch(
        args.trajectron_model_dir, args.trajectron_epoch
    )
    print(f"[CacheDataset] Using Trajectron checkpoint epoch: {resolved_epoch}")

    traj_cfg = TrajectronLoadConfig(
        conf_path=args.trajectron_conf,
        model_dir=args.trajectron_model_dir,
        epoch=resolved_epoch,
        device=args.device,
    )
    adapter = build_trajectron_adapter_from_checkpoint(
        traj_cfg, 
        embedding_dim=args.embedding_dim,
        mode="encoder"
    )
    adapter.to(device)
    adapter.eval()
    
    print(f"\n[Phase 1] Extracting Trajectron Context & Candidates...")
    
    # We will defer normalization scaling to the Master Optimizer to keep raw atoms in cache.
    # Raw atoms allow the Master Optimization engine to apply scales dynamically if needed.
    # But since original code normalized, we will cache raw, but could normalize downstream.
    
    scenarios = [] 
    map_source_counts = {}
    pbar = tqdm(total=args.num_scenarios if args.num_scenarios > 0 else None)
    for batch in dataloader:
        if args.num_scenarios > 0 and len(scenarios) >= args.num_scenarios:
            break
            
        with torch.no_grad():
            batch.to(device)
            emb_out = adapter.embed_batch(batch) # [B, D]
            batch_embs = emb_out["scene_embeddings"].cpu().numpy()
            
        candidates_batch = get_top_k_predictions(adapter, batch, k=args.num_candidates, gmm_mode=False)
        
        B = len(batch.agent_name)
        for i in range(B):
            if args.num_scenarios > 0 and len(scenarios) >= args.num_scenarios:
                break
                
            try:
                # Get GT trajectory for BT warmup
                fut = batch.agent_fut[i].cpu().numpy()
                fut_xy = fut[:11, :2]
                if np.isnan(fut_xy).any():
                    continue
                curr_pos = np.zeros(2)
                gt_traj = np.concatenate(([curr_pos], fut_xy), axis=0)
                horizon = len(gt_traj)
                
                ctx = extract_driver_context(batch, i, map_api=map_api, horizon=horizon)
                map_source = getattr(ctx, "map_source", "unknown")
                map_source_counts[map_source] = map_source_counts.get(map_source, 0) + 1
                cands = candidates_batch[i]
                
                gt_atoms = compute_atom_bank_vector(ctx, gt_traj) # [R]
                
                atoms_list = []
                feas_list = []
                for k in range(len(cands)):
                    traj = cands[k]
                    at = compute_atom_bank_vector(ctx, traj) # [R] (raw)
                    is_f = compute_feasibility_mask(ctx, traj) # bool
                    atoms_list.append(at)
                    feas_list.append(is_f)
                
                atoms_k = np.stack(atoms_list) # [K, R]
                feas_mask_k = np.array(feas_list, dtype=bool) # [K]
                
                scenarios.append({
                    "id": f"s_{len(scenarios)}",
                    "scene_id": batch.scene_ids[i], # Track actual scene ID from batch
                    "map_source": map_source,
                    "embedding": batch_embs[i], # CPU Numpy
                    "gt_traj": gt_traj, # [H, 2] RAW Numpy
                    "gt_atoms": gt_atoms, # [R] RAW Numpy
                    "atoms": atoms_k, # [K, R] RAW Numpy
                    "feas_mask": feas_mask_k, # [K] Numpy bool
                    "candidates": cands # [K, H, 2]
                })
                pbar.update(1)
            except Exception as e:
                print(f"Error in skipped scenario: {e}", flush=True)
                
    pbar.close()
    print(f"Cached {len(scenarios)} scenarios.")
    print(f"Map source counts: {map_source_counts}")
    if len(scenarios) == 0:
        print("No scenarios collected. Exiting.")
        return

    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, "wb") as f:
        pickle.dump(scenarios, f)
        
    print(f"[{time.strftime('%H:%M:%S')}] Module 1 Loop Finished.")
    print(f"Saved {len(scenarios)} samples to {args.output_path}")
    print(f"Total Time: {(time.time() - start_time)/60:.2f} min")

if __name__ == "__main__":
    main()
