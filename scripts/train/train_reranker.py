
import argparse
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
# Force sync execution for debugging CUDA errors
os.environ['CUDA_LAUNCH_BLOCKING'] = '1' 

import sys
import time
import json
import re
import pickle
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from pathlib import Path
from tqdm import tqdm

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
    extract_driver_context,
)
from camp_core.atoms.driver_atoms import compute_atom_bank_vector
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

class RerankerModel(nn.Module):
    """
    Score s(xi, y) = MLP([phi(xi), A(xi, y)])
    Output scalar score (lower is better).
    """
    def __init__(self, embedding_dim, num_atoms, hidden_dim=64):
        super().__init__()
        input_dim = embedding_dim + num_atoms
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        
    def forward(self, phi, atoms):
        # phi: [B, D]
        # atoms: [B, K, R] or [B, R]
        
        if atoms.dim() == 3:
            # Broadcast phi for K candidates
            B, K, R = atoms.shape
            phi_exp = phi.unsqueeze(1).expand(B, K, -1) # [B, K, D]
            inp = torch.cat([phi_exp, atoms], dim=-1) # [B, K, D+R]
            score = self.net(inp).squeeze(-1) # [B, K]
        else:
            # Single pair
            inp = torch.cat([phi, atoms], dim=-1)
            score = self.net(inp).squeeze(-1)
            
        return score

def compute_ade(pred, gt):
    # pred: [T, 2]
    # gt: [T, 2]
    min_len = min(len(pred), len(gt))
    if min_len == 0:
        return float("nan")
    pred_xy = pred[:min_len]
    gt_xy = gt[:min_len]
    valid = ~np.isnan(gt_xy).any(axis=-1)
    if not valid.any():
        return float("nan")
    return float(np.mean(np.linalg.norm(pred_xy[valid] - gt_xy[valid], axis=1)))

def get_top_k_predictions(adapter, batch, k=12, gmm_mode=True):
    trajectron = adapter.base_model
    
    # [BUGFIX] Force Trajectron++ to actually sample diversely across modes.
    # Without this, pre-trained models default to 'single_mode_multi_sample=True'
    # which collapses all 30 predictions into the exact same trajectory.
    trajectron.hyperparams['single_mode_multi_sample'] = False
    
    ph = trajectron.hyperparams.get("prediction_horizon", 12)
    device = next(trajectron.parameters()).device
    batch.to(device)
    
    with torch.no_grad():
         predictions = trajectron.predict(
             batch,
             prediction_horizon=ph,
             num_samples=k,
             z_mode=False,
             gmm_mode=gmm_mode,
             output_dists=False
         )
    
    from trajdata import AgentType
    batch_preds = []
    
    for i in range(len(batch.agent_name)):
        node_type = AgentType(batch.agent_type[i].item()) if hasattr(batch, 'agent_type') else 'VEHICLE'
        agent_name = batch.agent_name[i]
        key = f"{str(node_type)}/{agent_name}"
        
        if key in predictions:
             p = predictions[key] # [K, H, 2]
             if hasattr(p, 'cpu'): p = p.cpu().numpy()
             batch_preds.append(p)
        else:
             batch_preds.append(np.zeros((k, ph, 2)))
             
    return batch_preds

def load_atom_scales(scale_path: str, device: torch.device) -> torch.Tensor:
    if os.path.exists(scale_path):
        print(f"Loading Atom Scales from {scale_path}")
        with open(scale_path, "r") as f:
            scales = json.load(f)
        return torch.tensor(scales, dtype=torch.float32, device=device)
    else:
        return torch.ones(9, dtype=torch.float32, device=device)

def as_numpy(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().numpy()
    return np.asarray(value)

def load_train_data_from_cache(args, atom_scales: np.ndarray):
    print(f"[INFO] Loading reranker train data from CAMP cache: {args.cache_path}", flush=True)
    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)
    if isinstance(scenarios, dict) and "samples" in scenarios:
        scenarios = scenarios["samples"]
    if not isinstance(scenarios, list) or len(scenarios) == 0:
        raise ValueError(f"Cache {args.cache_path} must contain a non-empty list.")

    total = len(scenarios)
    if args.num_scenarios > 0 and args.num_scenarios < total:
        scenarios = scenarios[: args.num_scenarios]
        print(f"[INFO] Using first {len(scenarios)}/{total} cached scenarios.", flush=True)

    embeddings = []
    atoms = []
    ades = []
    for idx, sc in enumerate(scenarios):
        for key in ("embedding", "atoms", "candidates", "gt_traj"):
            if key not in sc:
                raise ValueError(f"Scenario {idx} in {args.cache_path} is missing {key}.")

        emb = as_numpy(sc["embedding"]).astype(np.float32).reshape(-1)
        atoms_raw = as_numpy(sc["atoms"]).astype(np.float32)
        cands = as_numpy(sc["candidates"]).astype(np.float32)
        gt = as_numpy(sc["gt_traj"]).astype(np.float32)
        if atoms_raw.ndim != 2:
            raise ValueError(f"Scenario {idx} atoms must be [K, R], got {atoms_raw.shape}")
        if atoms_raw.shape[1] != len(atom_scales):
            raise ValueError(f"Scenario {idx} atom dim {atoms_raw.shape[1]} != scales dim {len(atom_scales)}")

        atoms_norm = atoms_raw / atom_scales.reshape(1, -1)
        atoms_norm = np.clip(np.nan_to_num(atoms_norm, nan=0.0, posinf=10.0, neginf=0.0), 0.0, 10.0)
        ade = np.array([compute_ade(cand, gt) for cand in cands], dtype=np.float32)
        if np.isnan(ade).all():
            continue
        ade = np.nan_to_num(ade, nan=np.nanmax(ade[np.isfinite(ade)]) if np.isfinite(ade).any() else 1e6)

        embeddings.append(emb)
        atoms.append(atoms_norm)
        ades.append(ade)

    if not embeddings:
        raise ValueError(f"No valid reranker training samples found in {args.cache_path}.")

    data = {
        "embedding": np.stack(embeddings).astype(np.float32),
        "atoms": np.stack(atoms).astype(np.float32),
        "ades": np.stack(ades).astype(np.float32),
    }
    print(
        f"[INFO] Loaded cache reranker tensors: embeddings={data['embedding'].shape}, "
        f"atoms={data['atoms'].shape}, ades={data['ades'].shape}",
        flush=True,
    )
    return data

def parse_args():
    parser = argparse.ArgumentParser(description="Train Reranker Baseline")
    parser.add_argument("--data_root", type=str, default="/ocean/projects/tra250008p/slin24/datasets/nuscenes")
    parser.add_argument("--cache_dir", type=str, default=os.path.expanduser("~/.unified_data_cache"))
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--num_scenarios", type=int, default=100, help="Number of scenarios to use; <=0 means all")
    parser.add_argument("--cache_path", type=str, default=None, help="Optional prebuilt CAMP train cache")
    
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--train_batch_size", type=int, default=256)
    parser.add_argument("--lambda_safe", type=float, default=0.0, help="Safety Regularization Strength")
    parser.add_argument("--safety_temp", type=float, default=1.0, help="Temperature for Soft Selection")
    parser.add_argument("--seed", type=int, default=None, help="Optional random seed for reproducible ablations")
    
    parser.add_argument("--output_path", type=str, default="models/reranker_gt.pt")
    parser.add_argument("--atom_scales_path", type=str, default="models/production/atom_scales.json")
    
    # Trajectron
    parser.add_argument("--trajectron_conf", type=str, required=True)
    parser.add_argument("--trajectron_model_dir", type=str, required=True)
    parser.add_argument(
        "--trajectron_epoch",
        type=int,
        default=-1,
        help="Trajectron checkpoint epoch. <=0 means auto-select latest checkpoint.",
    )
    parser.add_argument("--embedding_dim", type=int, default=64)
    parser.add_argument("--split", type=str, default="nusc_trainval-train")

    return parser.parse_args()

def main():
    args = parse_args()
    if args.seed is not None:
        print(f"[Seed] Using seed={args.seed}", flush=True)
        np.random.seed(args.seed)
        torch.manual_seed(args.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print(f"=== Reranker Training ===")
    print(f"Epochs: {args.epochs}, Lambda Safe: {args.lambda_safe}")
    
    # 2. Collect Data (Online or Cache?)
    # Data Checkpointing
    data_cache_path = os.path.join(os.path.dirname(args.output_path), "reranker_train_data.pt")
    
    # Load Scales
    atom_scales_t = load_atom_scales(args.atom_scales_path, device)
    atom_scales = atom_scales_t.cpu().numpy()
    
    if args.cache_path:
        train_data = load_train_data_from_cache(args, atom_scales)
    elif os.path.exists(data_cache_path):
        print(f"[INFO] Loading cached training data from {data_cache_path}...", flush=True)
        train_data = torch.load(data_cache_path, weights_only=False)
        print(f"[INFO] Loaded {len(train_data)} samples.", flush=True)
    else:
        resolved_epoch = resolve_trajectron_epoch(
            args.trajectron_model_dir, args.trajectron_epoch
        )
        print(f"[Reranker] Using Trajectron checkpoint epoch: {resolved_epoch}")

        cfg = NuscenesDatasetConfig(
            data_root=args.data_root,
            cache_dir=args.cache_dir,
            batch_size=args.batch_size,
            num_workers=args.num_workers,
            split=args.split,
            shuffle=False, # [DEBUG] Disable shuffle to prevent hang
            use_vector_map=True,
        )
        bridge = NuscenesTrajdataBridge(cfg)
        dataloader = bridge.get_dataloader()
        map_api = bridge.dataset

        # Initialize Trajectron ONLY if we need to collect data
        print(f"[INFO] Cache not found. Initializing Trajectron for data collection...", flush=True)
        traj_cfg = TrajectronLoadConfig(
            conf_path=args.trajectron_conf,
            model_dir=args.trajectron_model_dir,
            epoch=resolved_epoch,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )
        adapter = build_trajectron_adapter_from_checkpoint(
            traj_cfg, 
            embedding_dim=args.embedding_dim,
            mode="encoder"
        )
        adapter.eval()

        train_data = []
        collect_all = args.num_scenarios <= 0
        target_label = "all" if collect_all else str(args.num_scenarios)
        print(f"[DEBUG] Starting loop. Goal: {target_label}", flush=True)
        batch_idx = 0
        for batch in dataloader:
            if (not collect_all) and len(train_data) >= args.num_scenarios:
                break
                
            print(f"[DEBUG] Batch {batch_idx} loaded.", flush=True)
            
            try:
                with torch.no_grad():
                    batch.to(device)
                    print(f"[DEBUG] Embedding batch {batch_idx}...", flush=True)
                    t0 = time.time()
                    emb_out = adapter.embed_batch(batch)
                    torch.cuda.synchronize()
                    embs = emb_out["scene_embeddings"]
                    print(f"[DEBUG] Embedding done in {time.time()-t0:.2f}s", flush=True)
                    
                print(f"[DEBUG] Predicting k={12}...", flush=True)
                t0 = time.time()
                k_preds = get_top_k_predictions(adapter, batch, k=30, gmm_mode=False)
                torch.cuda.synchronize()
                print(f"[DEBUG] Prediction done in {time.time()-t0:.2f}s", flush=True)
            except RuntimeError as e:
                print(f"[ERROR] CUDA Error during Trajectron inference in Batch {batch_idx}: {e}", flush=True)
                print("[DEBUG] Skipping this batch and terminating collection to save progress.", flush=True)
                break
            
            B = len(batch.agent_name)
            for i in range(B):
                if (not collect_all) and len(train_data) >= args.num_scenarios:
                    break
                    
                try:
                    # GT Trajectory
                    gt_raw = batch.agent_fut[i].cpu().numpy() # [H_gt, D]
                    # Slice to match prediction horizon (12) and XY dims (2)
                    if gt_raw.shape[0] < 12:
                         continue
                    gt = gt_raw[:12, :2]
                    
                    # Context & Atoms
                    ctx = extract_driver_context(batch, i, map_api=map_api)
                    preds = k_preds[i] # [K, H, 2]
                    
                    # Compute Atoms [K, R]
                    atoms_list = []
                    for traj in preds:
                        feat = compute_atom_bank_vector(ctx, traj) 
                        atoms_list.append(feat)
                    
                    atoms_np = np.stack(atoms_list) # [K, R]
                    
                    # Normalize to match eval_reranker.py inputs.
                    atoms_np = atoms_np / atom_scales
                    atoms_np = np.clip(np.nan_to_num(atoms_np, nan=0.0, posinf=10.0, neginf=0.0), 0.0, 10.0)
                    
                    # Labels (ADE)
                    ades = np.array([compute_ade(p, gt) for p in preds])
                    
                    train_data.append({
                        "embedding": embs[i].cpu().numpy(),
                        "atoms": atoms_np,
                        "ades": ades
                    })
                    print(f"[DEBUG] Collected Sample {len(train_data)}/{target_label}", flush=True)
                except Exception as e:
                    print(f"[ERROR] Failed to process agent {i}: {e}", flush=True)
                    pass
            
            batch_idx += 1
            
        # Checkpoint immediately after collection
        os.makedirs(os.path.dirname(data_cache_path), exist_ok=True)
        print(f"[INFO] Saving training data to {data_cache_path}...", flush=True)
        torch.save(train_data, data_cache_path)
        print(f"[INFO] Checkpoint saved. Run the script again if it crashes now.", flush=True)
    
    if len(train_data) == 0:
        print("No training data collected.")
        return

    # 3. Model
    if isinstance(train_data, dict):
        D = train_data["embedding"].shape[1]
        R = train_data["atoms"].shape[2]
    else:
        sample = train_data[0]
        D = sample["embedding"].shape[0]
        R = sample["atoms"].shape[1]
    
    model = RerankerModel(embedding_dim=D, num_atoms=R).to(device)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    
    # Define Safe Weights for Regularization
    # Atoms R=9:
    # 0-2: Jerk (3)
    # 3: RMS (1)
    # 4-6: Speed (3)
    # 7: Lane (1)
    # 8: Clearance (1)
    
    w_safe = torch.zeros(R, device=device)
    # Penalize Safety Violations
    if R >= 9:
        w_safe[4] = 1.0 # Speed 0.0 margin
        w_safe[5] = 1.0 # Speed 0.5 margin
        w_safe[6] = 1.0 # Speed 1.0 margin
        w_safe[7] = 1.0 # Lane Deviation
        w_safe[8] = 1.0 # Clearance (Soft)
    elif R >= 4:
         # Fallback for old bank
         w_safe[3] = 1.0
    
    # 4. Train Loop
    print("Starting Training...")
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-5)
    
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        total_rank_loss = 0.0
        total_reg_loss = 0.0
        
        if isinstance(train_data, dict):
            embeddings_np = train_data["embedding"]
            atoms_np = train_data["atoms"]
            ades_np = train_data["ades"]
            num_samples = embeddings_np.shape[0]
            order = np.random.permutation(num_samples)
            seen = 0

            for start in range(0, num_samples, args.train_batch_size):
                batch_idx = order[start : start + args.train_batch_size]
                if len(batch_idx) == 0:
                    continue

                phi = torch.from_numpy(embeddings_np[batch_idx]).float().to(device)
                atoms = torch.from_numpy(atoms_np[batch_idx]).float().to(device)
                ades = ades_np[batch_idx]
                B, K, _ = atoms.shape
                if K < 2:
                    continue

                k_best = np.argmin(ades, axis=1)
                k_neg = np.random.randint(0, K, size=B)
                k_neg = np.where(k_neg == k_best, (k_neg + 1) % K, k_neg)

                optimizer.zero_grad()
                scores = model(phi, atoms)
                row_idx = torch.arange(B, device=device)
                best_t = torch.tensor(k_best, dtype=torch.long, device=device)
                neg_t = torch.tensor(k_neg, dtype=torch.long, device=device)
                s_pos = scores[row_idx, best_t]
                s_neg = scores[row_idx, neg_t]
                rank_loss = torch.nn.functional.softplus(s_pos - s_neg).mean()

                reg_loss = 0.0
                if args.lambda_safe > 0:
                    q_safe = (atoms * w_safe).sum(dim=-1)
                    probs = torch.softmax(-scores / args.safety_temp, dim=1)
                    reg_loss = args.lambda_safe * (probs * q_safe).sum(dim=1).mean()

                loss = rank_loss + reg_loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                total_loss += loss.item() * B
                total_rank_loss += rank_loss.item() * B
                reg_value = reg_loss.item() if hasattr(reg_loss, "item") else float(reg_loss)
                total_reg_loss += reg_value * B
                seen += B

            epoch_den = max(seen, 1)
        else:
            # Shuffle
            np.random.shuffle(train_data)
            epoch_den = len(train_data)

            for sc in train_data:
            # Prepare Inputs
                phi = torch.from_numpy(sc["embedding"]).float().to(device).unsqueeze(0) # [1, D]
                atoms = torch.from_numpy(sc["atoms"]).float().to(device).unsqueeze(0) # [1, K, R]
                ades = sc["ades"]

                k_best = np.argmin(ades)

                sorted_idx = np.argsort(ades)
                candidates = sorted_idx[1:min(5, len(ades))]
                if len(candidates) > 0:
                    k_hard = np.random.choice(candidates)
                else:
                    k_hard = np.random.choice([x for x in range(len(ades)) if x != k_best])

                k_rand = np.random.randint(0, len(ades))
                while k_rand == k_best:
                    k_rand = np.random.randint(0, len(ades))

                k_neg = k_hard if np.random.rand() < 0.5 else k_rand

                optimizer.zero_grad()
                scores = model(phi, atoms) # [1, K]
                s_pos = scores[0, k_best]
                s_neg = scores[0, k_neg]
                rank_loss = torch.nn.functional.softplus(s_pos - s_neg)

                reg_loss = 0.0
                if args.lambda_safe > 0:
                    q_safe = (atoms * w_safe).sum(dim=-1) # [1, K]
                    probs = torch.softmax(-scores / args.safety_temp, dim=1) # [1, K]
                    expected_safety_cost = (probs * q_safe).sum()
                    reg_loss = args.lambda_safe * expected_safety_cost

                loss = rank_loss + reg_loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                optimizer.step()

                total_loss += loss.item()
                total_rank_loss += rank_loss.item()
                reg_value = reg_loss.item() if hasattr(reg_loss, "item") else float(reg_loss)
                total_reg_loss += reg_value
            
        # [CRITICAL UPDATE] Decay learning rate to escape noise-floor oscillation
        scheduler.step()
            
        print(
            f"Epoch {epoch+1}, Avg Loss: {total_loss / epoch_den:.4f}, "
            f"Avg Rank: {total_rank_loss / epoch_den:.4f}, "
            f"Avg SafeReg: {total_reg_loss / epoch_den:.4f}",
            flush=True,
        )
        
    # 5. Save
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    torch.save(model.state_dict(), args.output_path)
    print(f"Saved Reranker to {args.output_path}")

if __name__ == "__main__":
    main()
