import argparse
import os
import sys
import json
import pickle
import torch
import numpy as np

# We need the class definition of RerankerModel
import torch.nn as nn

class RerankerModel(nn.Module):
    """Must match train_reranker.py architecture exactly"""
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
            B, K, R = atoms.shape
            phi_exp = phi.unsqueeze(1).expand(B, K, -1)
            inp = torch.cat([phi_exp, atoms], dim=-1)
            score = self.net(inp).squeeze(-1)
        else:
            inp = torch.cat([phi, atoms], dim=-1)
            score = self.net(inp).squeeze(-1)
        return score

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Trained Rerankers")
    parser.add_argument("--cache_path", type=str, required=True, help="Path to evaluation cache (.pkl)")
    parser.add_argument("--model_path", type=str, default=None, help="Path to trained reranker .pt")
    parser.add_argument("--reranker_path", type=str, default=None, help="Backward-compatible alias for --model_path")
    parser.add_argument("--output_path", type=str, required=True, help="Path to save JSON predictions")
    parser.add_argument("--atom_scales_path", type=str, default="models/production/atom_scales.json")
    parser.add_argument("--device", type=str, default=None, help="Evaluation device, e.g. cuda or cpu")
    parser.add_argument("--atom_clip", type=float, default=10.0, help="Clip normalized atoms for selection; <=0 disables clipping")
    return parser.parse_args()

def main():
    args = parse_args()
    model_path = args.model_path or args.reranker_path
    if not model_path:
        raise ValueError("Either --model_path or --reranker_path is required.")

    device_name = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    if device_name.startswith("cuda") and not torch.cuda.is_available():
        print(f"[Warn] Requested device {device_name}, but CUDA is unavailable. Falling back to cpu.")
        device_name = "cpu"
    device = torch.device(device_name)
    
    # 1. Load Data Cache
    print(f"Loading cached scenarios from {args.cache_path}...")
    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)
        
    if len(scenarios) == 0:
        print("Empty cache.")
        return
        
    print(f"Loaded {len(scenarios)} scenarios.")
    
    # Setup dimension
    sc0 = scenarios[0]
    D = sc0["embedding"].shape[0]
    R = sc0["atoms"].shape[1]
    
    # Load Atom Scales implicitly?
    scale_path = args.atom_scales_path
    if os.path.exists(scale_path):
        with open(scale_path, "r") as f:
            scales = np.array(json.load(f), dtype=np.float32)
    else:
        scales = np.ones(R, dtype=np.float32)
        
    # 2. Load Model
    print(f"Loading Reranker Model from {model_path}...")
    model = RerankerModel(embedding_dim=D, num_atoms=R).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=False))
    model.eval()
    
    results = {}
    
    # 3. Evaluate
    print("Scoring candidates...")
    with torch.no_grad():
        for idx, sc in enumerate(scenarios):
            scene_key = f"sc_{idx}"
            
            # [D] -> [1, D]
            phi_np = sc["embedding"]
            phi_t = torch.tensor(phi_np, dtype=torch.float32, device=device).unsqueeze(0)
            
            # [K, R] -> [1, K, R] (Normalized)
            atoms_np = sc["atoms"] / scales
            if args.atom_clip > 0:
                atoms_np = np.clip(
                    np.nan_to_num(atoms_np, nan=0.0, posinf=args.atom_clip, neginf=0.0),
                    0.0,
                    args.atom_clip,
                )
            atoms_t = torch.tensor(atoms_np, dtype=torch.float32, device=device).unsqueeze(0)
            
            # Score
            scores_t = model(phi_t, atoms_t) # [1, K]
            scores_np = scores_t.cpu().numpy()[0] # [K]
            
            # Lower score = better
            best_idx = int(np.argmin(scores_np))
            results[scene_key] = best_idx
            
    # 4. Save
    os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
    with open(args.output_path, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"Saved Reranker predictions to {args.output_path}.")
    
if __name__ == "__main__":
    main()
