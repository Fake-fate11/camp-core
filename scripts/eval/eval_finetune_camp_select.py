import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import torch
from tqdm import tqdm

# Work around protobuf/l5kit compatibility in some environments.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
if not os.environ.get("OMP_NUM_THREADS", "").isdigit() or int(os.environ.get("OMP_NUM_THREADS", "0") or 0) <= 0:
    os.environ["OMP_NUM_THREADS"] = "1"

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.atoms.driver_atoms import compute_atom_bank_vector, compute_feasibility_mask
from camp_core.base_predictor.trajectron_adapter import TrajectronAdapter, TrajectronAdapterConfig
from camp_core.base_predictor.trajectron_loader import (
    TrajectronLoadConfig,
    build_trajectron_from_checkpoint,
)
from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
    extract_driver_context,
)


def simplex_proj(v: np.ndarray) -> np.ndarray:
    """Project vector onto probability simplex."""
    v_sorted = np.sort(v)[::-1]
    cssv = np.cumsum(v_sorted) - 1.0
    ind = np.arange(1, len(v) + 1)
    cond = v_sorted - cssv / ind > 0
    rho = ind[cond][-1]
    theta_sum = cssv[rho - 1] / rho
    return np.maximum(v - theta_sum, 0.0)


def resolve_trajectron_epoch(model_dir: str, requested_epoch: int, flag_name: str) -> int:
    """Return requested epoch; if <=0, use latest checkpoint epoch in model_dir."""
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
            f"Please pass --{flag_name} explicitly."
        )

    return max(epochs)


def compute_ade(pred: np.ndarray, gt: np.ndarray) -> float:
    min_len = min(len(pred), len(gt))
    if min_len == 0:
        return 0.0
    valid_mask = ~np.isnan(gt[:min_len]).any(axis=-1)
    if not valid_mask.any():
        return float("nan")
    return float(np.mean(np.linalg.norm(pred[:min_len][valid_mask] - gt[:min_len][valid_mask], axis=-1)))


def compute_fde(pred: np.ndarray, gt: np.ndarray) -> float:
    min_len = min(len(pred), len(gt))
    if min_len == 0:
        return 0.0
    valid_mask = ~np.isnan(gt[:min_len]).any(axis=-1)
    if not valid_mask.any():
        return float("nan")
    valid_indices = np.where(valid_mask)[0]
    last_idx = int(valid_indices[-1])
    return float(np.linalg.norm(pred[last_idx] - gt[last_idx]))


def compute_kinematics(traj: np.ndarray, dt: float = 0.5) -> tuple:
    v = np.diff(traj, axis=0) / dt
    if len(v) < 2:
        return 0.0, 0.0
    a = np.diff(v, axis=0) / dt
    if len(a) < 2:
        return float(np.sqrt(np.mean(np.sum(a**2, axis=-1)))), 0.0
    j = np.diff(a, axis=0) / dt
    rms_a = float(np.sqrt(np.mean(np.sum(a**2, axis=-1))))
    rms_j = float(np.sqrt(np.mean(np.sum(j**2, axis=-1))))
    return rms_a, rms_j


def compute_cvar(costs: np.ndarray, alpha: float = 0.9) -> float:
    if len(costs) == 0:
        return 0.0
    sorted_costs = np.sort(costs)[::-1]
    tail_idx = max(1, int((1.0 - alpha) * len(costs)))
    tail_costs = sorted_costs[:tail_idx]
    return float(np.mean(tail_costs))


def safety_cost_variants(atoms_norm: np.ndarray, atom_clip: float = 10.0, safety_weight: float = 0.1) -> tuple:
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


def load_atom_scales(num_atoms: int, scale_path: str = "models/production/atom_scales.json") -> np.ndarray:
    if os.path.exists(scale_path):
        with open(scale_path, "r", encoding="utf-8") as f:
            scales = np.array(json.load(f), dtype=np.float32)
        if len(scales) != num_atoms:
            print(
                f"[Warn] Atom scales length {len(scales)} != num_atoms {num_atoms}. "
                "Will broadcast/truncate to match."
            )
            if len(scales) < num_atoms:
                pad = np.ones(num_atoms - len(scales), dtype=np.float32)
                scales = np.concatenate([scales, pad], axis=0)
            else:
                scales = scales[:num_atoms]
        return scales

    print("[Warn] Atom scales not found, using identity scales.")
    return np.ones(num_atoms, dtype=np.float32)


def load_finetuned_trajectron(
    conf_path: str,
    model_dir: str,
    base_epoch: int,
    finetuned_epoch: int,
    finetuned_prefix: str,
    device: str,
):
    load_cfg = TrajectronLoadConfig(
        conf_path=conf_path,
        model_dir=model_dir,
        epoch=base_epoch,
        device=device,
    )
    model = build_trajectron_from_checkpoint(load_cfg)

    finetuned_ckpt_path = os.path.join(model_dir, f"{finetuned_prefix}_{finetuned_epoch}.pt")
    if not os.path.exists(finetuned_ckpt_path):
        raise FileNotFoundError(f"Finetuned checkpoint not found: {finetuned_ckpt_path}")

    model.model_registrar.load_state_dict(
        torch.load(finetuned_ckpt_path, map_location=device, weights_only=False)
    )
    model.to(torch.device(device))
    model.eval()
    return model


def extract_candidates(
    predictions: Dict,
    key: str,
    num_candidates: int,
    prediction_horizon: int,
) -> np.ndarray:
    if key in predictions:
        cands = predictions[key]
        if hasattr(cands, "cpu"):
            cands = cands.cpu().numpy()
        cands = np.asarray(cands, dtype=np.float32)
        if cands.ndim == 2:
            cands = cands[None, ...]
    else:
        cands = np.zeros((1, prediction_horizon, 2), dtype=np.float32)

    if cands.shape[-1] > 2:
        cands = cands[..., :2]

    if cands.shape[0] < num_candidates:
        pad = np.repeat(cands[-1:, ...], num_candidates - cands.shape[0], axis=0)
        cands = np.concatenate([cands, pad], axis=0)
    elif cands.shape[0] > num_candidates:
        cands = cands[:num_candidates]

    return cands


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate finetuned Trajectron with CAMP-style candidate selection (Finetune + CAMP-Select)."
    )
    parser.add_argument("--data_root", type=str, default="/root/autodl-tmp/dataset")
    parser.add_argument("--cache_dir", type=str, default="/root/autodl-tmp/.unified_data_cache")
    parser.add_argument("--split", type=str, default="nusc_trainval-val")
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--num_workers", type=int, default=0)

    parser.add_argument("--traj_conf_path", type=str, required=True)
    parser.add_argument("--traj_model_dir", type=str, required=True)
    parser.add_argument(
        "--base_epoch",
        type=int,
        default=-1,
        help="Base checkpoint epoch for Trajectron construction. <=0 means latest.",
    )
    parser.add_argument("--finetuned_epoch", type=int, required=True)
    parser.add_argument("--finetuned_prefix", type=str, default="finetuned_safe")
    parser.add_argument("--num_candidates", type=int, default=12)

    parser.add_argument(
        "--camp_model_path",
        type=str,
        required=True,
        help="Path to trained CAMP model checkpoint containing Theta.",
    )

    parser.add_argument(
        "--embed_conf_path",
        type=str,
        default="",
        help="Optional embedding model config path. Defaults to --traj_conf_path.",
    )
    parser.add_argument(
        "--embed_model_dir",
        type=str,
        default="",
        help="Optional embedding model dir. Defaults to --traj_model_dir.",
    )
    parser.add_argument(
        "--embed_base_epoch",
        type=int,
        default=-1,
        help="Base epoch for embedding model. <=0 means latest.",
    )
    parser.add_argument(
        "--embed_finetuned_epoch",
        type=int,
        default=-1,
        help="If >0, load finetuned_safe_<epoch>.pt onto embedding model registrar.",
    )
    parser.add_argument(
        "--embed_finetuned_prefix",
        type=str,
        default="",
        help="Checkpoint prefix for --embed_finetuned_epoch. Defaults to --finetuned_prefix.",
    )

    parser.add_argument(
        "--output_metrics_path",
        type=str,
        default="results/finetune_camp_select_metrics.json",
    )
    parser.add_argument(
        "--output_preds_path",
        type=str,
        default="results/finetune_camp_select_preds.json",
    )
    parser.add_argument("--alpha", type=float, default=0.9)
    parser.add_argument("--atom_scales_path", type=str, default="models/production/atom_scales.json")
    parser.add_argument("--atom_clip", type=float, default=10.0, help="Clip normalized atoms for CAMP selection; <=0 disables clipping")
    parser.add_argument("--safety_weight", type=float, default=0.1, help="Weight applied to speed/lane/clearance atoms for training-consistent CVaR")
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    device = torch.device(args.device)

    print("=== Eval: Finetune + CAMP-Select ===")

    resolved_base_epoch = resolve_trajectron_epoch(
        args.traj_model_dir, args.base_epoch, "base_epoch"
    )
    print(f"[EvalFTCamp] Trajectron base epoch: {resolved_base_epoch}")

    trajectron = load_finetuned_trajectron(
        conf_path=args.traj_conf_path,
        model_dir=args.traj_model_dir,
        base_epoch=resolved_base_epoch,
        finetuned_epoch=args.finetuned_epoch,
        finetuned_prefix=args.finetuned_prefix,
        device=device.type,
    )

    camp_ckpt = torch.load(args.camp_model_path, map_location="cpu", weights_only=False)
    if "Theta" not in camp_ckpt:
        raise KeyError(f"Missing 'Theta' in CAMP checkpoint: {args.camp_model_path}")
    theta = np.asarray(camp_ckpt["Theta"], dtype=np.float32)
    embedding_dim = int(theta.shape[1] - 1)
    num_atoms = int(theta.shape[0])

    print(f"[EvalFTCamp] Loaded Theta shape={theta.shape}, embedding_dim={embedding_dim}, num_atoms={num_atoms}")

    # Build embedding model (can be same as finetuned model or separately specified).
    if args.embed_model_dir:
        embed_conf_path = args.embed_conf_path if args.embed_conf_path else args.traj_conf_path
        embed_base_epoch = resolve_trajectron_epoch(
            args.embed_model_dir, args.embed_base_epoch, "embed_base_epoch"
        )
        print(f"[EvalFTCamp] Embedding model base epoch: {embed_base_epoch}")
        embed_model = build_trajectron_from_checkpoint(
            TrajectronLoadConfig(
                conf_path=embed_conf_path,
                model_dir=args.embed_model_dir,
                epoch=embed_base_epoch,
                device=device.type,
            )
        )
        if args.embed_finetuned_epoch > 0:
            embed_prefix = args.embed_finetuned_prefix or args.finetuned_prefix
            embed_ft_ckpt = os.path.join(
                args.embed_model_dir, f"{embed_prefix}_{args.embed_finetuned_epoch}.pt"
            )
            if not os.path.exists(embed_ft_ckpt):
                raise FileNotFoundError(f"Embedding finetuned checkpoint not found: {embed_ft_ckpt}")
            embed_model.model_registrar.load_state_dict(
                torch.load(embed_ft_ckpt, map_location=device.type, weights_only=False)
            )
        embed_model.to(device)
        embed_model.eval()
    else:
        embed_model = trajectron

    embed_adapter = TrajectronAdapter(
        cfg=TrajectronAdapterConfig(
            device=device.type,
            embedding_dim=embedding_dim,
            mode="encoder",
            use_frozen_trajectron=True,
        ),
        base_model=embed_model,
    )

    scales = load_atom_scales(num_atoms=num_atoms, scale_path=args.atom_scales_path)
    w_safe = np.ones(num_atoms, dtype=np.float32) / max(num_atoms, 1)

    cfg = NuscenesDatasetConfig(
        data_root=args.data_root,
        cache_dir=args.cache_dir,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        shuffle=False,
        split=args.split,
        use_vector_map=True,
        unified_dataset_kwargs={"history_sec": (2.0, 2.0), "future_sec": (6.0, 6.0)},
    )
    bridge = NuscenesTrajdataBridge(cfg)
    dataloader = bridge.get_dataloader()
    map_api = bridge.dataset

    metrics = {
        "ade": [],
        "fde": [],
        "rms_accel": [],
        "rms_jerk": [],
        "safety_violations": [],
        "safety_cost": [],
        "safety_cost_unclipped_sum": [],
        "safety_cost_clipped_sum": [],
        "safety_cost_no_clearance": [],
    }
    preds = {}

    ph = int(trajectron.hyperparams.get("prediction_horizon", 12))
    dt = float(trajectron.hyperparams.get("dt", 0.5))

    scenario_idx = 0
    pbar = tqdm(dataloader, desc="Eval Batch")
    for batch in pbar:
        batch.to(device)

        trajectron.hyperparams["single_mode_multi_sample"] = False
        with torch.no_grad():
            predictions = trajectron.predict(
                batch,
                prediction_horizon=ph,
                num_samples=args.num_candidates,
                z_mode=False,
                gmm_mode=False,
                output_dists=False,
            )
            emb_out = embed_adapter.embed_batch(batch)
            batch_embs = emb_out["scene_embeddings"].detach().cpu().numpy()

        from trajdata import AgentType

        B = batch.curr_agent_state.shape[0]
        for i in range(B):
            scene_key = f"sc_{scenario_idx}"
            scenario_idx += 1

            node_type = AgentType(batch.agent_type[i].item()) if hasattr(batch, "agent_type") else "VEHICLE"
            agent_name = batch.agent_name[i]
            key = f"{str(node_type)}/{agent_name}"

            try:
                cands = extract_candidates(
                    predictions=predictions,
                    key=key,
                    num_candidates=args.num_candidates,
                    prediction_horizon=ph,
                )

                ctx = extract_driver_context(batch, i, map_api=map_api, horizon=ph)
                atoms_list = []
                feas_list = []
                for k in range(len(cands)):
                    traj_k = np.asarray(cands[k], dtype=np.float32)
                    atoms_k = compute_atom_bank_vector(ctx, traj_k)
                    feas_k = compute_feasibility_mask(ctx, traj_k)
                    atoms_list.append(atoms_k)
                    feas_list.append(bool(feas_k))

                atoms = np.stack(atoms_list, axis=0).astype(np.float32)
                if atoms.shape[1] != num_atoms:
                    # Keep compatibility with CAMP checkpoint dimension.
                    if atoms.shape[1] < num_atoms:
                        pad = np.zeros((atoms.shape[0], num_atoms - atoms.shape[1]), dtype=np.float32)
                        atoms = np.concatenate([atoms, pad], axis=1)
                    else:
                        atoms = atoms[:, :num_atoms]

                atoms_scaled = atoms / scales
                atoms_for_score = atoms_scaled
                if args.atom_clip > 0:
                    atoms_for_score = np.clip(
                        np.nan_to_num(atoms_for_score, nan=0.0, posinf=args.atom_clip, neginf=0.0),
                        0.0,
                        args.atom_clip,
                    )
                feas_mask = np.asarray(feas_list, dtype=bool)

                phi = np.asarray(batch_embs[i], dtype=np.float32)
                if phi.shape[0] != embedding_dim:
                    if phi.shape[0] < embedding_dim:
                        phi = np.pad(phi, (0, embedding_dim - phi.shape[0]))
                    else:
                        phi = phi[:embedding_dim]

                phi_aug = np.concatenate([phi, np.ones(1, dtype=np.float32)], axis=0)
                w_raw = theta @ phi_aug
                w = simplex_proj(w_raw)

                scores = (atoms_for_score * w[None, :]).sum(axis=-1)
                if feas_mask.any():
                    scores = scores.copy()
                    scores[~feas_mask] = float("inf")
                    best_idx = int(np.argmin(scores))
                else:
                    fallback = (atoms_for_score * w_safe[None, :]).sum(axis=-1)
                    best_idx = int(np.argmin(fallback))

                preds[scene_key] = best_idx

                pred_traj = np.asarray(cands[best_idx], dtype=np.float32)
                gt_traj = batch.agent_fut[i].detach().cpu().numpy()
                gt_len = int(batch.agent_fut_len[i].item()) if hasattr(batch, "agent_fut_len") else len(gt_traj)
                gt_traj = gt_traj[:gt_len, :2]

                ade = compute_ade(pred_traj, gt_traj)
                fde = compute_fde(pred_traj, gt_traj)
                rms_a, rms_j = compute_kinematics(pred_traj, dt=dt)
                unclip_sum, clip_sum, weighted_clip, no_clearance = safety_cost_variants(
                    atoms_scaled[best_idx],
                    atom_clip=args.atom_clip,
                    safety_weight=args.safety_weight,
                )

                metrics["ade"].append(float(ade))
                metrics["fde"].append(float(fde))
                metrics["rms_accel"].append(float(rms_a))
                metrics["rms_jerk"].append(float(rms_j))
                metrics["safety_violations"].append(1.0 if not feas_mask[best_idx] else 0.0)
                metrics["safety_cost"].append(weighted_clip)
                metrics["safety_cost_unclipped_sum"].append(unclip_sum)
                metrics["safety_cost_clipped_sum"].append(clip_sum)
                metrics["safety_cost_no_clearance"].append(no_clearance)

            except Exception as e:
                print(f"[EvalFTCamp] Exception scene={scene_key}, agent={agent_name}: {e}")
                continue

    ade_valid = [x for x in metrics["ade"] if not np.isnan(x)]
    fde_valid = [x for x in metrics["fde"] if not np.isnan(x)]
    safe_cost_valid = [x for x in metrics["safety_cost"] if not np.isnan(x)]
    safe_unclipped_valid = [x for x in metrics["safety_cost_unclipped_sum"] if not np.isnan(x)]
    safe_clipped_valid = [x for x in metrics["safety_cost_clipped_sum"] if not np.isnan(x)]
    safe_no_clearance_valid = [x for x in metrics["safety_cost_no_clearance"] if not np.isnan(x)]

    summary = {
        "Mean_ADE": float(np.mean(ade_valid)) if len(ade_valid) > 0 else float("nan"),
        "Mean_FDE": float(np.mean(fde_valid)) if len(fde_valid) > 0 else float("nan"),
        "Violation_Rate": float(np.mean(metrics["safety_violations"])) if len(metrics["safety_violations"]) > 0 else float("nan"),
        "RMS_Accel": float(np.mean(metrics["rms_accel"])) if len(metrics["rms_accel"]) > 0 else float("nan"),
        "RMS_Jerk": float(np.mean(metrics["rms_jerk"])) if len(metrics["rms_jerk"]) > 0 else float("nan"),
        "CVaR_0.90_Safety": compute_cvar(np.asarray(safe_cost_valid, dtype=np.float32), alpha=args.alpha)
        if len(safe_cost_valid) > 0
        else float("nan"),
        "CVaR_0.90_Safety_WeightedClipped": compute_cvar(np.asarray(safe_cost_valid, dtype=np.float32), alpha=args.alpha)
        if len(safe_cost_valid) > 0
        else float("nan"),
        "CVaR_0.90_Safety_UnclippedSum": compute_cvar(np.asarray(safe_unclipped_valid, dtype=np.float32), alpha=args.alpha)
        if len(safe_unclipped_valid) > 0
        else float("nan"),
        "CVaR_0.90_Safety_ClippedSum": compute_cvar(np.asarray(safe_clipped_valid, dtype=np.float32), alpha=args.alpha)
        if len(safe_clipped_valid) > 0
        else float("nan"),
        "CVaR_0.90_Safety_NoClearance": compute_cvar(np.asarray(safe_no_clearance_valid, dtype=np.float32), alpha=args.alpha)
        if len(safe_no_clearance_valid) > 0
        else float("nan"),
        "Safety_CVaR_Report": "weighted_clipped",
        "Safety_Atom_Clip": float(args.atom_clip),
        "Safety_Atom_Weight": float(args.safety_weight),
        "Num_Evaluated": int(len(metrics["ade"])),
    }

    print("\n--- Finetune + CAMP-Select Summary ---")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")

    out_metrics_dir = os.path.dirname(args.output_metrics_path)
    if out_metrics_dir:
        os.makedirs(out_metrics_dir, exist_ok=True)
    with open(args.output_metrics_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
    print(f"Saved metrics to {args.output_metrics_path}")

    out_preds_dir = os.path.dirname(args.output_preds_path)
    if out_preds_dir:
        os.makedirs(out_preds_dir, exist_ok=True)
    with open(args.output_preds_path, "w", encoding="utf-8") as f:
        json.dump(preds, f, indent=2)
    print(f"Saved selected indices to {args.output_preds_path}")


if __name__ == "__main__":
    main()
