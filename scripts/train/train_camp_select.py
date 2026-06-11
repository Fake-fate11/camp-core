#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import json
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.append(path_str)

from camp_core.mapping_heads.linear_head import LinearMappingHead
from camp_core.outer_master.benders_master import BendersCut
from camp_core.outer_master.parametric_cvxpy_master import (
    ParametricCVXPYMaster,
    ParametricCVXPYMasterConfig,
)


DEFAULT_MASTER_BATCH_SIZE = 500
ATOM_CLIP = 10.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CAMP Module 2: CVXPY Master Optimization Engine")
    parser.add_argument("--cache_path", type=str, default="data/cached_train_batch.pkl")
    parser.add_argument("--num_scenarios", type=int, default=-1, help="Max cached scenarios to use. <=0 means all.")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--output_path", type=str, default="models/camp_select_linear.pt")
    parser.add_argument("--atom_scales_path", type=str, default="models/production/atom_scales.json")
    parser.add_argument("--timing_output_path", type=str, default="")
    parser.add_argument(
        "--cache_atoms_normalized",
        action="store_true",
        help="Treat cached atoms and gt_atoms as already normalized by atom scales.",
    )

    parser.add_argument("--num_atoms", type=int, default=9)
    parser.add_argument("--embedding_dim", type=int, default=64)

    parser.add_argument("--risk_type", type=str, default="cvar", choices=["mean", "cvar"])
    parser.add_argument("--alpha", type=float, default=0.9)
    parser.add_argument("--solver", type=str, default="CLARABEL", help="CVXPY solver: ECOS, SCS, CLARABEL, GUROBI, COPT")
    parser.add_argument(
        "--master_batch_size",
        type=int,
        default=DEFAULT_MASTER_BATCH_SIZE,
        help="Max scenarios per Benders master step. <=0 uses min(N, 500).",
    )
    parser.add_argument("--max_iter", type=int, default=100, help="Number of Benders outer iterations.")
    parser.add_argument(
        "--max_cuts_per_scene",
        type=int,
        default=120,
        help="Keep at most this many cuts per scenario. <=0 disables pruning.",
    )

    parser.add_argument("--prior_reg", type=float, default=1.0, help="L2 trust-region strength on Theta.")
    parser.add_argument("--anchor_weight", type=float, default=0.0, help="Regularize mean weights toward BT anchor.")

    parser.add_argument("--bt_epochs", type=int, default=20000)
    parser.add_argument("--bt_lr", type=float, default=0.01)

    # Kept so existing pipelines that pass this argument do not break. CAMP-Select
    # uses BT warmup from gt_atoms instead of loading offline weights.
    parser.add_argument("--offline_weights_path", type=str, default="models/offline_weights.npy")
    return parser.parse_args()


def as_numpy(value: Any) -> np.ndarray:
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().numpy()
    return np.asarray(value)


def load_atom_scales(scale_path: Optional[str], num_atoms: int, device: torch.device) -> torch.Tensor:
    if scale_path and os.path.exists(scale_path):
        print(f"Loading Atom Scales from {scale_path}", flush=True)
        with open(scale_path, "r", encoding="utf-8") as f:
            scales = np.asarray(json.load(f), dtype=np.float32)
        if scales.ndim != 1 or scales.shape[0] < num_atoms:
            raise ValueError(f"Expected at least {num_atoms} atom scales, got shape {scales.shape}")
        scales = scales[:num_atoms]
    else:
        print(f"Warning: Scale file {scale_path} not found. Using identity scales.", flush=True)
        scales = np.ones(num_atoms, dtype=np.float32)

    scales = np.nan_to_num(scales, nan=1.0, posinf=1.0, neginf=1.0)
    scales = np.maximum(scales, 1e-6)
    print(f"Loaded Atom Scales: {scales}", flush=True)
    return torch.tensor(scales, dtype=torch.float32, device=device)


def extract_embedding(sample: dict[str, Any], fallback_dim: int) -> torch.Tensor:
    for key in ("embedding", "scene_embedding", "scene_embeddings", "emb", "phi", "features"):
        if key in sample:
            emb = torch.as_tensor(as_numpy(sample[key]), dtype=torch.float32).reshape(-1)
            if emb.numel() > 0:
                return emb
    return torch.zeros(fallback_dim, dtype=torch.float32)


def effective_master_batch_size(num_scenarios: int, requested: int) -> int:
    if requested <= 0:
        return min(num_scenarios, DEFAULT_MASTER_BATCH_SIZE)
    return min(num_scenarios, requested)


def prune_scene_cuts(master: ParametricCVXPYMaster, scene_idx: int, max_cuts_per_scene: int) -> None:
    if max_cuts_per_scene <= 0:
        return
    scene_cuts = master.cuts[scene_idx]
    if len(scene_cuts) > max_cuts_per_scene:
        del scene_cuts[: len(scene_cuts) - max_cuts_per_scene]


def load_cached_tensors(
    args: argparse.Namespace,
    atom_scales: torch.Tensor,
    device: torch.device,
) -> tuple[list[dict[str, Any]], torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    print(f"Loading cached scenarios from {args.cache_path}...", flush=True)
    if not os.path.exists(args.cache_path):
        raise FileNotFoundError(f"Cache not found at {args.cache_path}. Run Module 1 first.")

    with open(args.cache_path, "rb") as f:
        payload = pickle.load(f)
    if isinstance(payload, dict) and "samples" in payload:
        payload = payload["samples"]
    if not isinstance(payload, list) or len(payload) == 0:
        raise ValueError(f"Cache {args.cache_path} must contain a non-empty list.")
    total_cached = len(payload)
    if args.num_scenarios > 0 and args.num_scenarios < total_cached:
        payload = payload[: args.num_scenarios]
        print(f"Using first {len(payload)}/{total_cached} cached scenarios.", flush=True)

    scales_np = atom_scales.detach().cpu().numpy()
    scenarios: list[dict[str, Any]] = []
    missing_gt = 0

    for idx, sample in enumerate(payload):
        if "gt_atoms" not in sample:
            missing_gt += 1
            continue

        atoms = as_numpy(sample["atoms"]).astype(np.float32)
        gt_atoms = as_numpy(sample["gt_atoms"]).astype(np.float32).reshape(-1)
        if atoms.ndim != 2:
            raise ValueError(f"Scenario {idx} atoms must be [K, R], got {atoms.shape}")
        if atoms.shape[1] != len(scales_np):
            raise ValueError(f"Scenario {idx} atom dim {atoms.shape[1]} != scales dim {len(scales_np)}")
        if gt_atoms.shape[0] != len(scales_np):
            raise ValueError(f"Scenario {idx} gt_atoms dim {gt_atoms.shape[0]} != scales dim {len(scales_np)}")

        if args.cache_atoms_normalized:
            atoms_norm = atoms
            gt_norm = gt_atoms
        else:
            atoms_norm = atoms / scales_np.reshape(1, -1)
            gt_norm = gt_atoms / scales_np

        atoms_norm = np.nan_to_num(atoms_norm, nan=0.0, posinf=ATOM_CLIP, neginf=0.0)
        gt_norm = np.nan_to_num(gt_norm, nan=0.0, posinf=ATOM_CLIP, neginf=0.0)
        atoms_norm = np.clip(atoms_norm, a_min=0.0, a_max=ATOM_CLIP)
        gt_norm = np.clip(gt_norm, a_min=0.0, a_max=ATOM_CLIP)

        if "feas_mask" in sample:
            feas_mask = as_numpy(sample["feas_mask"]).astype(bool).reshape(-1)
            if feas_mask.shape[0] != atoms.shape[0]:
                raise ValueError(
                    f"Scenario {idx} feas_mask length {feas_mask.shape[0]} != candidates {atoms.shape[0]}"
                )
        else:
            feas_mask = np.ones(atoms.shape[0], dtype=bool)
        if not feas_mask.any():
            feas_mask[:] = True

        scenarios.append(
            {
                "id": sample.get("id", sample.get("scene_id", f"s_{idx}")),
                "embedding": extract_embedding(sample, args.embedding_dim),
                "atoms": atoms_norm,
                "gt_atoms": gt_norm,
                "feas_mask": torch.tensor(feas_mask, dtype=torch.bool),
            }
        )

    if missing_gt:
        raise ValueError(
            f"Cache {args.cache_path} is missing gt_atoms for {missing_gt} scenarios. "
            "CAMP-Select CVXPY training requires gt_atoms for BT warmup; rebuild the cache with scripts/data_gen/cache_dataset.py."
        )
    if len(scenarios) == 0:
        raise ValueError(f"No usable scenarios found in cache {args.cache_path}.")

    embedding_dim = max(int(s["embedding"].numel()) for s in scenarios)
    num_atoms = int(scenarios[0]["atoms"].shape[1])
    max_candidates = max(int(s["atoms"].shape[0]) for s in scenarios)

    all_embeddings = torch.zeros((len(scenarios), embedding_dim), dtype=torch.float32)
    all_atoms = torch.zeros((len(scenarios), max_candidates, num_atoms), dtype=torch.float32)
    all_masks = torch.zeros((len(scenarios), max_candidates), dtype=torch.bool)
    gts = torch.zeros((len(scenarios), num_atoms), dtype=torch.float32)

    for i, scenario in enumerate(scenarios):
        emb = torch.as_tensor(scenario["embedding"], dtype=torch.float32).reshape(-1)
        atoms_i = torch.as_tensor(scenario["atoms"], dtype=torch.float32)
        gt_i = torch.as_tensor(scenario["gt_atoms"], dtype=torch.float32).reshape(-1)
        mask_i = torch.as_tensor(scenario["feas_mask"], dtype=torch.bool).reshape(-1)

        all_embeddings[i, : emb.numel()] = emb
        all_atoms[i, : atoms_i.shape[0], :] = atoms_i
        all_masks[i, : mask_i.numel()] = mask_i
        gts[i, :] = gt_i

    print(f"Loaded {len(scenarios)} cached scenarios.", flush=True)
    print(f"Embeddings shape: {tuple(all_embeddings.shape)}", flush=True)
    print(f"Atoms shape: {tuple(all_atoms.shape)}", flush=True)
    print(f"GT atoms shape: {tuple(gts.shape)}", flush=True)
    return (
        scenarios,
        all_embeddings.to(device),
        all_atoms.to(device),
        all_masks.to(device),
        gts.to(device),
    )


def run_bt_warmup(gts: torch.Tensor, cands: torch.Tensor, args: argparse.Namespace) -> np.ndarray:
    print("\n[Warmup] Running Bradley-Terry Offline Preference Learning...", flush=True)
    device = gts.device
    num_atoms = int(gts.shape[1])

    w_logits = nn.Parameter(torch.zeros(num_atoms, device=device))
    optimizer = optim.Adam([w_logits], lr=args.bt_lr)

    for epoch in range(args.bt_epochs):
        optimizer.zero_grad()
        weights = torch.softmax(w_logits, dim=0)
        delta = gts.unsqueeze(1) - cands
        diffs = (delta * weights).sum(dim=-1)
        loss = torch.nn.functional.softplus(diffs).mean()
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 50 == 0:
            print(f"  BT Epoch {epoch + 1}/{args.bt_epochs} | Loss: {loss.item():.4f}", flush=True)

    final_w = torch.softmax(w_logits, dim=0).detach().cpu().numpy()
    print(f"[Warmup] Completed. Global Anchor Weights: {final_w}", flush=True)
    return final_w


def write_timing(path: str, payload: dict[str, Any]) -> None:
    if not path:
        return
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved timing to {path}", flush=True)


def main() -> None:
    args = parse_args()
    device = torch.device(args.device)
    script_start_time = time.time()

    print("=== Module 2: Master Optimization Engine ===", flush=True)
    print("[CAMP] backend=cvxpy", flush=True)
    print(f"Cache path: {args.cache_path}", flush=True)
    print(f"Atom scales path: {args.atom_scales_path}", flush=True)
    print(f"Risk: {args.risk_type}, Alpha: {args.alpha}", flush=True)
    print(f"Solver: {args.solver}", flush=True)
    print(f"Regularization: Prior={args.prior_reg}, Anchor={args.anchor_weight}", flush=True)
    print(f"Master batch size: {args.master_batch_size}", flush=True)
    print(f"Max cuts per scene: {args.max_cuts_per_scene}", flush=True)

    atom_scales = load_atom_scales(args.atom_scales_path, args.num_atoms, device)
    scenarios, all_embeddings, all_atoms, all_masks, gts = load_cached_tensors(args, atom_scales, device)

    args.embedding_dim = int(all_embeddings.shape[1])
    args.num_atoms = int(all_atoms.shape[2])

    warmup_start_time = time.time()
    anchor_weights = run_bt_warmup(gts, all_atoms, args)
    warmup_time_s = time.time() - warmup_start_time

    mapping_head = LinearMappingHead(
        embedding_dim=args.embedding_dim,
        num_atoms=args.num_atoms,
        use_bias=True,
    ).to(device)

    print("\nInitializing CVXPY Master...", flush=True)
    master_config = ParametricCVXPYMasterConfig(
        num_atoms=args.num_atoms,
        embedding_dim=args.embedding_dim,
        risk_type=args.risk_type,
        alpha=args.alpha,
        prior_reg_strength=args.prior_reg,
        offline_anchor_weight=args.anchor_weight,
        device="cpu",
        solver=args.solver,
    )
    master = ParametricCVXPYMaster(
        config=master_config,
        scene_embeddings=all_embeddings.detach().cpu().numpy(),
    )
    master.update_head_weights(mapping_head, master.theta_value)

    print("\nStarting CVXPY Benders Iterations...", flush=True)
    benders_start_time = time.time()
    iter_times_s: list[float] = []
    iter_inner_times_s: list[float] = []
    iter_cut_times_s: list[float] = []
    iter_master_times_s: list[float] = []
    history: list[dict[str, Any]] = []
    batch_indices = torch.arange(len(scenarios), device=device)
    master_batch_size = effective_master_batch_size(len(scenarios), args.master_batch_size)

    for iteration in range(1, args.max_iter + 1):
        print(f"\n--- Iteration {iteration} ---", flush=True)
        iter_start_time = time.time()

        inner_start_time = time.time()
        mapping_head.eval()
        with torch.no_grad():
            w_curr_raw = mapping_head(all_embeddings)
            w_curr_t = torch.relu(w_curr_raw)
            w_curr_t = w_curr_t / (w_curr_t.sum(dim=1, keepdim=True) + 1e-8)

        mean_w = w_curr_t.mean(dim=0).detach().cpu().numpy()
        print(f"Mean Weights: {mean_w}", flush=True)

        scores_raw = (all_atoms * w_curr_t.unsqueeze(1)).sum(dim=-1)
        scores_cut = scores_raw.clone()
        scores_cut[~all_masks] = float("-inf")

        worst_vals, worst_idxs = torch.max(scores_cut, dim=1)
        all_inf_mask = torch.isinf(worst_vals)
        if all_inf_mask.any():
            fallback_vals, fallback_idxs = torch.max(scores_raw[all_inf_mask], dim=1)
            worst_vals[all_inf_mask] = fallback_vals
            worst_idxs[all_inf_mask] = fallback_idxs

        total_q = worst_vals.mean().item()
        gradients = all_atoms[batch_indices, worst_idxs]
        inner_time_s = time.time() - inner_start_time

        cut_start_time = time.time()
        w_curr_np = w_curr_t.detach().cpu().numpy()
        worst_vals_np = worst_vals.detach().cpu().numpy()
        gradients_np = gradients.detach().cpu().numpy()

        for i, scenario in enumerate(scenarios):
            cut = BendersCut(
                scenario_id=scenario["id"],
                w_anchor=w_curr_np[i],
                value=worst_vals_np[i],
                gradient=gradients_np[i],
            )
            master.add_cut(i, cut)
            prune_scene_cuts(master, i, args.max_cuts_per_scene)
        cut_time_s = time.time() - cut_start_time

        active_indices = None
        if len(scenarios) > master_batch_size:
            active_indices = np.random.choice(len(scenarios), master_batch_size, replace=False)

        print(f"  Inner Max Obj (Avg Worst-Case Cost): {total_q:.4f}", flush=True)
        print(f"  Master Batch Size: {master_batch_size}", flush=True)

        master_start_time = time.time()
        res = master.solve(verbose=False, active_indices=active_indices, prior_weights=anchor_weights)
        master_time_s = time.time() - master_start_time

        if res["status"] in ["optimal", "optimal_inaccurate"]:
            print(f"  Master Solve Status: {res['status']} | Loss: {res['loss']:.4f}", flush=True)
            master.update_head_weights(mapping_head, res["Theta"])
        else:
            print(f"  Master Failed: {res['status']}", flush=True)
            if "error" in res:
                print(f"  Error: {res['error']}", flush=True)

        iter_time_s = time.time() - iter_start_time
        iter_times_s.append(iter_time_s)
        iter_inner_times_s.append(inner_time_s)
        iter_cut_times_s.append(cut_time_s)
        iter_master_times_s.append(master_time_s)

        active_for_stats = active_indices if active_indices is not None else np.arange(len(scenarios))
        cut_counts = [len(master.cuts[int(i)]) for i in active_for_stats]
        history.append(
            {
                "iter": iteration,
                "seconds": iter_time_s,
                "inner_seconds": inner_time_s,
                "cut_seconds": cut_time_s,
                "master_seconds": master_time_s,
                "master_batch_size": int(master_batch_size),
                "avg_cuts_active": float(np.mean(cut_counts)),
                "max_cuts_active": int(np.max(cut_counts)),
                "inner_max_obj": total_q,
                "master_loss": float(res.get("loss", np.nan)) if isinstance(res, dict) else np.nan,
                "status": res.get("status") if isinstance(res, dict) else None,
            }
        )
        print(
            f"  Iter Time: {iter_time_s:.2f}s "
            f"(inner={inner_time_s:.2f}s, cuts={cut_time_s:.2f}s, master={master_time_s:.2f}s)",
            flush=True,
        )
        gc.collect()

    benders_time_s = time.time() - benders_start_time

    print("\n[Phase 3] Saving Model...", flush=True)
    out_dir = os.path.dirname(args.output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    torch.save(
        {
            "head": mapping_head.state_dict(),
            "config": vars(args),
            "offline_weights": anchor_weights,
            "Theta": master.theta_value,
        },
        args.output_path,
    )

    total_time_s = time.time() - script_start_time
    print(f"Saved to {args.output_path}", flush=True)
    print(f"Total Time: {total_time_s / 60:.2f} min", flush=True)

    write_timing(
        args.timing_output_path,
        {
            "total_seconds": total_time_s,
            "total_minutes": total_time_s / 60.0,
            "warmup_seconds": warmup_time_s,
            "benders_seconds": benders_time_s,
            "num_scenarios": len(scenarios),
            "num_atoms": args.num_atoms,
            "embedding_dim": args.embedding_dim,
            "max_iter": args.max_iter,
            "master_batch_size": master_batch_size,
            "max_cuts_per_scene": args.max_cuts_per_scene,
            "risk_type": args.risk_type,
            "alpha": args.alpha,
            "solver": args.solver,
            "backend": "cvxpy",
            "atom_scales_path": args.atom_scales_path,
            "cache_path": args.cache_path,
            "iter_times_s": iter_times_s,
            "iter_inner_times_s": iter_inner_times_s,
            "iter_cut_times_s": iter_cut_times_s,
            "iter_master_times_s": iter_master_times_s,
            "history": history,
        },
    )


if __name__ == "__main__":
    main()
