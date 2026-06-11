import json
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import pathlib
import re
import time
from collections import defaultdict
import numpy as np
import torch
from torch import nn, optim
from torch.utils import data
from tqdm import tqdm
from trajdata import AgentType, UnifiedDataset
from trajdata.data_structures.batch import AgentBatch

import sys
from pathlib import Path

# Add project root to path for evaluations
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT))

import trajectron.evaluation as evaluation
from trajectron.model.model_registrar import ModelRegistrar
from trajectron.model.model_utils import UpdateMode
from trajectron.model.trajectron import Trajectron
from trajectron.argument_parser import args as base_args

# ===========================================================================
# Apple-to-Apple: Import the EXACT SAME map safety atoms that CAMP uses
# This ensures Finetune and CAMP see identical road/constraint information.
# The ONLY remaining difference is the optimization mechanism:
#   Finetune -> implicit gradient descent through the neural network
#   CAMP     -> explicit post-hoc convex risk minimization
# ===========================================================================
from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig, NuscenesTrajdataBridge, extract_driver_context
)
from camp_core.atoms.driver_atoms import compute_atom_bank_vector
from scipy.ndimage import distance_transform_edt

def batch_raster_to_sdf(maps_tensor, drivable_channel=0, drivable_thresh=0.5):
    """
    Convert a batch of raster maps [B, C, H, W] to a batch of SDFs [B, 1, H, W].
    SDF > 0 outside drivable area (penalize), SDF < 0 inside (safe).
    Values are in PIXEL units. Divide by px_per_m to get meters.
    """
    B = maps_tensor.shape[0]
    sdfs = []
    for i in range(B):
        drivable = (maps_tensor[i, drivable_channel].cpu().numpy() > drivable_thresh)
        # distance_transform_edt: distance to nearest False pixel
        dist_inside  = distance_transform_edt(drivable)    # dist to boundary from inside
        dist_outside = distance_transform_edt(~drivable)   # dist to boundary from outside
        sdf = dist_outside - dist_inside                    # >0 outside, <0 inside
        sdfs.append(sdf)
    sdf_batch = np.stack(sdfs, axis=0)  # [B, H, W]
    return torch.tensor(sdf_batch, dtype=torch.float32).unsqueeze(1)  # [B, 1, H, W]


def resolve_checkpoint_epoch(model_dir: str, requested_epoch: int) -> int:
    """Resolve checkpoint epoch; if requested_epoch <= 0, use latest available."""
    if requested_epoch > 0:
        return requested_epoch

    model_path = Path(model_dir)
    candidates = []
    for ckpt in model_path.glob("model_registrar-*.pt"):
        match = re.search(r"model_registrar-(\d+)\.pt$", ckpt.name)
        if match:
            candidates.append(int(match.group(1)))

    if not candidates:
        raise FileNotFoundError(
            f"No model_registrar-*.pt checkpoints found under: {model_dir}"
        )
    return max(candidates)


def _fit_vector_length(values: np.ndarray, length: int, fill: float) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32).reshape(-1)
    if values.shape[0] < length:
        pad = np.full(length - values.shape[0], fill, dtype=np.float32)
        values = np.concatenate([values, pad], axis=0)
    elif values.shape[0] > length:
        values = values[:length]
    return values


def resolve_project_path(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if path.is_absolute() or path.exists():
        return str(path)

    project_path = PROJECT_ROOT / path
    if project_path.exists():
        return str(project_path)

    return str(path)


def load_atom_scales(scale_path: str, num_atoms: int = 9) -> np.ndarray:
    scale_path = resolve_project_path(scale_path)
    if os.path.exists(scale_path):
        with open(scale_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        scales = np.asarray(payload, dtype=np.float32)
    else:
        print(f"[CAMP Loss] Atom scales not found at {scale_path}; using identity scales.")
        scales = np.ones(num_atoms, dtype=np.float32)

    scales = _fit_vector_length(scales, num_atoms, fill=1.0)
    scales = np.nan_to_num(scales, nan=1.0, posinf=1.0, neginf=1.0)
    return np.maximum(scales, 1e-6)


def build_atom_weights(args, num_atoms: int = 9) -> np.ndarray:
    weights_path = getattr(args, "finetune_atom_weights_path", "").strip()
    if weights_path:
        weights_path = resolve_project_path(weights_path)
        if weights_path.endswith(".npy"):
            weights = np.load(weights_path)
        else:
            with open(weights_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                if "weights" in payload:
                    payload = payload["weights"]
                elif "atom_weights" in payload:
                    payload = payload["atom_weights"]
                else:
                    raise ValueError(
                        "Atom weight JSON must be a list or contain 'weights'/'atom_weights'."
                    )
            weights = np.asarray(payload, dtype=np.float32)
        return _fit_vector_length(weights, num_atoms, fill=0.0)

    lambda_jerk = float(getattr(args, "finetune_lambda_jerk", 0.0))
    lambda_sdf = float(getattr(args, "finetune_lambda_sdf", 0.1))
    lambda_speed = float(getattr(args, "finetune_lambda_speed", 0.1))
    lambda_clear = float(getattr(args, "finetune_lambda_clear", 0.1))
    return np.asarray(
        [
            lambda_jerk,
            lambda_jerk,
            lambda_jerk,
            lambda_jerk,
            lambda_speed,
            lambda_speed,
            lambda_speed,
            lambda_sdf,
            lambda_clear,
        ],
        dtype=np.float32,
    )


def reduce_safety_risk(costs: torch.Tensor, risk_type: str, alpha: float) -> torch.Tensor:
    if costs.numel() == 0:
        return costs.sum()
    if risk_type == "cvar":
        tail = max(1, int(np.ceil((1.0 - alpha) * costs.numel())))
        return torch.topk(costs.reshape(-1), k=tail, largest=True).values.mean()
    return costs.mean()


def compute_camp_kinematic_atoms(
    pred_traj: torch.Tensor,
    dt: float,
    speed_limits: torch.Tensor,
) -> torch.Tensor:
    """Differentiable version of CAMP atoms 0:7 for [N, T, 2] trajectories."""
    n_traj = pred_traj.shape[0]
    device = pred_traj.device
    dtype = pred_traj.dtype
    zeros = torch.zeros(n_traj, device=device, dtype=dtype)

    if pred_traj.shape[1] < 2:
        return torch.stack([zeros] * 7, dim=1)

    vel = (pred_traj[:, 1:] - pred_traj[:, :-1]) / dt

    if vel.shape[1] >= 2:
        acc = (vel[:, 1:] - vel[:, :-1]) / dt
        acc_sq = torch.sum(acc.pow(2), dim=-1)
        rms_acc = torch.sqrt(acc_sq.mean(dim=1) + 1e-8)
    else:
        acc = pred_traj.new_zeros((n_traj, 0, 2))
        rms_acc = zeros

    if acc.shape[1] >= 2:
        jerk = (acc[:, 1:] - acc[:, :-1]) / dt
        jerk_sq = torch.sum(jerk.pow(2), dim=-1)
        t_j = jerk_sq.shape[1]
        split_idx = max(1, t_j // 3)

        def jerk_window(start: int, end: int) -> torch.Tensor:
            if start < end and start < t_j:
                return dt * jerk_sq[:, start:end].sum(dim=1)
            return zeros

        jerk_early = jerk_window(0, split_idx)
        jerk_late = jerk_window(split_idx, t_j)
        jerk_full = jerk_window(0, t_j)
    else:
        jerk_early = zeros
        jerk_late = zeros
        jerk_full = zeros

    speed = torch.linalg.norm(vel, dim=-1)
    speed_atoms = []
    for margin in (0.0, 0.5, 1.0):
        threshold = speed_limits[:, None] - margin
        viol = torch.relu(speed - threshold)
        speed_atoms.append(dt * viol.pow(2).sum(dim=1))

    return torch.stack(
        [jerk_early, jerk_late, jerk_full, rms_acc, *speed_atoms],
        dim=1,
    )


def compute_lane_deviation_atom(
    pred_traj: torch.Tensor,
    lane_centerlines,
    lane_half_widths,
    dt: float,
) -> torch.Tensor:
    n_traj = pred_traj.shape[0]
    device = pred_traj.device
    dtype = pred_traj.dtype
    if n_traj == 0:
        return pred_traj.new_zeros(0)

    clean_centerlines = []
    for centerline in lane_centerlines:
        if centerline is None:
            arr = np.asarray([[0.0, 0.0], [50.0, 0.0]], dtype=np.float32)
        else:
            arr = np.asarray(centerline, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] < 2 or not np.isfinite(arr[:, :2]).all():
            arr = np.asarray([[0.0, 0.0], [50.0, 0.0]], dtype=np.float32)
        clean_centerlines.append(arr[:, :2])

    max_segments = max(1, max(arr.shape[0] - 1 for arr in clean_centerlines))
    starts = np.zeros((n_traj, max_segments, 2), dtype=np.float32)
    ends = np.zeros((n_traj, max_segments, 2), dtype=np.float32)
    mask = np.zeros((n_traj, max_segments), dtype=bool)

    for i, arr in enumerate(clean_centerlines):
        seg_count = min(arr.shape[0] - 1, max_segments)
        starts[i, :seg_count] = arr[:seg_count]
        ends[i, :seg_count] = arr[1 : seg_count + 1]
        mask[i, :seg_count] = True

    start_t = torch.as_tensor(starts, device=device, dtype=dtype)
    end_t = torch.as_tensor(ends, device=device, dtype=dtype)
    mask_t = torch.as_tensor(mask, device=device)
    widths_t = torch.as_tensor(lane_half_widths, device=device, dtype=dtype).reshape(n_traj, 1)

    seg = end_t - start_t
    seg_len_sq = torch.sum(seg.pow(2), dim=-1).clamp_min(1e-8)
    rel = pred_traj[:, :, None, :] - start_t[:, None, :, :]
    t = torch.sum(rel * seg[:, None, :, :], dim=-1) / seg_len_sq[:, None, :]
    t = torch.clamp(t, 0.0, 1.0)
    closest = start_t[:, None, :, :] + t[..., None] * seg[:, None, :, :]
    dist = torch.linalg.norm(pred_traj[:, :, None, :] - closest, dim=-1)
    dist = dist.masked_fill(~mask_t[:, None, :], float("inf"))
    min_dist = dist.min(dim=-1).values
    lane_viol = torch.relu(min_dist - widths_t)
    return dt * lane_viol.pow(2).sum(dim=1)


def compute_clearance_atom(
    sampled_future: torch.Tensor,
    agent_batch,
    safety_radius: float,
    clearance_soft_margin: float,
    dt: float,
) -> torch.Tensor:
    sample_ct, batch_size, horizon = sampled_future.shape[:3]
    out_size = sample_ct * batch_size
    device = sampled_future.device
    dtype = sampled_future.dtype

    if not hasattr(agent_batch, "neigh_fut") or agent_batch.neigh_fut is None:
        return torch.zeros(out_size, device=device, dtype=dtype)

    neigh = agent_batch.neigh_fut
    if neigh.numel() == 0 or neigh.shape[1] == 0:
        return torch.zeros(out_size, device=device, dtype=dtype)

    neigh_xy = neigh[:batch_size, :, :, :2].to(device=device, dtype=dtype)
    t_min = min(horizon, neigh_xy.shape[2])
    if t_min == 0:
        return torch.zeros(out_size, device=device, dtype=dtype)

    ego = sampled_future[:, :batch_size, :t_min].reshape(-1, t_min, 2).unsqueeze(1)
    neigh_exp = (
        neigh_xy[:, :, :t_min]
        .unsqueeze(0)
        .expand(sample_ct, -1, -1, -1, -1)
        .reshape(-1, neigh_xy.shape[1], t_min, 2)
    )
    valid = torch.isfinite(neigh_exp).all(dim=-1)
    # trajdata pads missing neighbor futures with NaNs. Masking after norm is
    # not enough for autograd because NaNs in the inactive branch can still
    # poison gradients, so replace invalid coordinates before distance math.
    far_neigh = ego.detach().expand_as(neigh_exp) + 999.0
    safe_neigh = torch.where(valid.unsqueeze(-1), neigh_exp, far_neigh)
    dist = torch.linalg.norm(ego - safe_neigh, dim=-1)
    dist = torch.where(valid, dist, torch.full_like(dist, 999.0))
    min_dist = dist.min(dim=1).values
    soft_radius = float(safety_radius) + float(clearance_soft_margin)
    intrusion = torch.relu(soft_radius - min_dist)
    return dt * intrusion.pow(2).sum(dim=1)


def get_agent_source_indices(agent_batch, batch_size: int, device: torch.device) -> torch.Tensor:
    if hasattr(agent_batch, "agent_type_batch_idx"):
        indices = agent_batch.agent_type_batch_idx
        if not torch.is_tensor(indices):
            indices = torch.as_tensor(indices, device=device)
        return indices.to(device=device).long()
    return torch.arange(batch_size, device=device, dtype=torch.long)


def train_finetune():
    base_args.device = "cuda" if torch.cuda.is_available() else "cpu"
    script_start_time = time.time()
    
    from camp_core.base_predictor.trajectron_loader import TrajectronLoadConfig, build_trajectron_from_checkpoint
    
    # Load pretrained model FIRST to get the authoritative hyperparams
    model_dir = os.path.dirname(base_args.conf)
    base_epoch = resolve_checkpoint_epoch(model_dir, int(getattr(base_args, "base_epoch", -1)))
    print(f"Loading Pretrained Model from: {model_dir}")
    print(f"Using base checkpoint epoch: {base_epoch}")
    traj_cfg = TrajectronLoadConfig(
        conf_path=base_args.conf,
        model_dir=model_dir,
        epoch=base_epoch,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )
    trajectron = build_trajectron_from_checkpoint(traj_cfg)
    model_registrar = trajectron.model_registrar
    
    # Get the official hyperparams dictionary that the model is using
    hyperparams = trajectron.hyperparams
    hyperparams["learning_rate"] = 1e-4   # Lower LR for finetuning
    hyperparams["train_epochs"] = 60      # Increased for deeper safety convergence

    lambda_jerk = float(getattr(base_args, "finetune_lambda_jerk", 0.0))
    lambda_sdf = float(getattr(base_args, "finetune_lambda_sdf", 0.1))
    lambda_speed = float(getattr(base_args, "finetune_lambda_speed", 0.1))
    lambda_clear = float(getattr(base_args, "finetune_lambda_clear", 0.1))
    finetune_loss_mode = getattr(base_args, "finetune_loss_mode", "camp_atoms")
    finetune_risk_type = getattr(base_args, "finetune_risk_type", "cvar")
    finetune_cvar_alpha = float(getattr(base_args, "finetune_cvar_alpha", 0.9))
    finetune_checkpoint_prefix = getattr(base_args, "finetune_checkpoint_prefix", "finetuned_safe")
    atom_clip = float(getattr(base_args, "finetune_atom_clip", 10.0))
    
    # Physical constants
    dt = 0.5              # NuScenes prediction timestep (2 Hz)
    speed_limit = float(getattr(base_args, "finetune_speed_limit", 10.0))
    safety_radius = float(getattr(base_args, "finetune_safety_radius", 1.0))
    clearance_soft_margin = float(getattr(base_args, "finetune_clearance_soft_margin", 4.0))
    lane_half_width = float(getattr(base_args, "finetune_lane_half_width", 2.0))
    
    # *** CLAMP values prevent individual outlier points from creating ***
    # *** explosive gradients that overwhelm the NLL loss.             ***
    sdf_clamp   = 2.0     # Max SDF penalty: 2m off-road (prevents relu(50)²=2500)
    speed_clamp = 5.0     # Max speed excess: 5m/s over limit
    
    # *** WARMUP: train NLL-only first, then gradually introduce safety ***
    warmup_epochs = int(getattr(base_args, "finetune_warmup_epochs", 5))
    ramp_epochs = int(getattr(base_args, "finetune_ramp_epochs", 20))
    safety_balance = float(getattr(base_args, "finetune_safety_balance", 0.5))
    safety_balance_min = float(
        getattr(base_args, "finetune_safety_balance_min", 0.1)
    )
    safety_balance_max = float(
        getattr(base_args, "finetune_safety_balance_max", 10.0)
    )
    safety_num_samples = max(
        1, int(getattr(base_args, "finetune_safety_num_samples", 1))
    )
    max_batches_per_epoch = int(
        getattr(base_args, "finetune_max_batches_per_epoch", 0)
    )
    atom_scales_np = load_atom_scales(
        getattr(base_args, "finetune_atom_scales_path", "models/production/atom_scales.json"),
        num_atoms=9,
    )
    atom_weights_np = build_atom_weights(base_args, num_atoms=9)
    atom_scales_t = torch.tensor(atom_scales_np, dtype=torch.float32, device=base_args.device)
    atom_weights_t = torch.tensor(atom_weights_np, dtype=torch.float32, device=base_args.device)
    
    # Map raster parameters for full-coverage SDF
    # Use 400px (200m×200m) to cover the full 6s prediction horizon (~90m).
    # The model's CNN encoder expects 100×100, so we downsample before feeding.
    px_per_m = 2
    epoch_times_s = []
    map_size_px = 400       # Full-coverage raster for SDF (200m × 200m)
    model_map_size = 100    # Downsample target for the model's CNN encoder
    offset_frac_xy = (-0.75, 0.0)
    
    print(f"[SDF Loss] px_per_m={px_per_m}, sdf_map={map_size_px}px, model_map={model_map_size}px")
    print(
        f"[Safety] mode={finetune_loss_mode}, risk={finetune_risk_type}, alpha={finetune_cvar_alpha:.2f}, "
        f"warmup={warmup_epochs}, ramp={ramp_epochs}, "
        f"lambdas(jerk/sdf/speed/clear)=({lambda_jerk:.3f}/{lambda_sdf:.3f}/{lambda_speed:.3f}/{lambda_clear:.3f}), "
        f"samples={safety_num_samples}, balance={safety_balance:.2f}, atom_clip={atom_clip:.2f}, "
        f"clearance_radius={safety_radius + clearance_soft_margin:.2f}, "
        f"max_batches={max_batches_per_epoch if max_batches_per_epoch > 0 else 'full'}"
    )
    if finetune_loss_mode == "camp_atoms":
        print(f"[CAMP Loss] atom_scales={atom_scales_np}")
        print(f"[CAMP Loss] atom_weights={atom_weights_np}")

    for k, v in vars(base_args).items():
        # Overwrite if passed explicitly from CLI by checking sys.argv
        if v is not None:
            # If the hyperparameter is explicitly set by us (like train_epochs=30)
            # we should only overwrite it if the user passed it explicitly in CLI!
            arg_flag = f"--{k}"
            if k in hyperparams and arg_flag not in sys.argv:
                continue
            hyperparams[k] = v
            
    # Also push to NodeModels directly, just in case they cloned the dictionary
    for node_model in trajectron.node_models_dict.values():
        for k, v in vars(base_args).items():
            if v is not None:
                arg_flag = f"--{k}"
                if k in node_model.hyperparams and arg_flag not in sys.argv:
                    continue
                node_model.hyperparams[k] = v
    
    # Init Datasets based purely on authoritative hyperparams
    attention_radius = defaultdict(lambda: 20.0)
    attention_radius[(AgentType.PEDESTRIAN, AgentType.PEDESTRIAN)] = 10.0
    attention_radius[(AgentType.PEDESTRIAN, AgentType.VEHICLE)] = 20.0
    attention_radius[(AgentType.VEHICLE, AgentType.PEDESTRIAN)] = 20.0
    attention_radius[(AgentType.VEHICLE, AgentType.VEHICLE)] = 30.0

    # Utilize the train_data specified dynamically (or fallback to full set)
    train_data = hyperparams.get("train_data", "nusc_trainval-train")
    if train_data == "nusc_mini-mini_train":
        print("Note: Fast-mode training enabled on mini_train.")
    else:
        print(f"Full-Scale Training Enabled! Target Data: {train_data}")

    # Ensure correct cache location
    cache_loc = hyperparams.get("trajdata_cache_dir", os.path.expanduser("~/.unified_data_cache"))
        
    data_dirs = {
        "nusc_trainval": "/root/autodl-tmp/dataset", 
        "nusc_mini": "/root/autodl-tmp/dataset"
    }
    # If user provided a data_loc_dict string in hyperparams, parse it
    if "data_loc_dict" in hyperparams:
        if isinstance(hyperparams["data_loc_dict"], str):
            try:
                parsed_dirs = json.loads(hyperparams["data_loc_dict"])
            except Exception:
                parsed_dirs = {}
        elif isinstance(hyperparams["data_loc_dict"], dict):
            parsed_dirs = hyperparams["data_loc_dict"]
        else:
            parsed_dirs = {}
            
        data_dirs.update(parsed_dirs)
        # If nusc_trainval is provided but not nusc_mini, gracefully copy it
        if "nusc_trainval" in data_dirs and "nusc_mini" not in parsed_dirs:
            data_dirs["nusc_mini"] = data_dirs["nusc_trainval"]

    # FORCE override any hardcoded workspace paths from pretrained checkpoints
    for k, v in data_dirs.items():
        if v.startswith("/workspace"):
            data_dirs[k] = "/root/autodl-tmp/dataset"

    map_params = {"px_per_m": px_per_m, "map_size_px": map_size_px, "offset_frac_xy": offset_frac_xy}
    
    train_dataset = UnifiedDataset(
        desired_data=[hyperparams.get("train_data", "nusc_trainval-train")],
        history_sec=(0.1, hyperparams["history_sec"]),
        future_sec=(0.1, hyperparams["prediction_sec"]),
        agent_interaction_distances=attention_radius,
        incl_robot_future=hyperparams.get("incl_robot_node", False),
        incl_raster_map=True,   # CRITICAL: must include raster maps for SDF
        incl_vector_map=True,
        raster_map_params=map_params,
        only_predict=[AgentType.VEHICLE, AgentType.PEDESTRIAN],
        no_types=[AgentType.UNKNOWN],
        num_workers=hyperparams.get("preprocess_workers", 4),
        cache_location=cache_loc,
        data_dirs=data_dirs,
        verbose=True,
    )
    
    eval_dataset = UnifiedDataset(
        desired_data=[hyperparams["eval_data"]],
        history_sec=(hyperparams["history_sec"], hyperparams["history_sec"]),
        future_sec=(hyperparams["prediction_sec"], hyperparams["prediction_sec"]),
        agent_interaction_distances=attention_radius,
        incl_robot_future=hyperparams.get("incl_robot_node", False),
        incl_raster_map=True,
        incl_vector_map=True,
        raster_map_params=map_params,
        only_predict=[AgentType.VEHICLE],
        no_types=[AgentType.UNKNOWN],
        num_workers=4,
        cache_location=hyperparams.get("trajdata_cache_dir", os.path.expanduser("~/.unified_data_cache")),
        data_dirs=data_dirs,
        verbose=True,
    )

    train_dataloader = data.DataLoader(
        train_dataset,
        collate_fn=train_dataset.get_collate_fn(pad_format="right"),
        pin_memory=True, batch_size=32, shuffle=True, num_workers=8
    )
    
    # UNFREEZE ALL
    for name, param in model_registrar.named_parameters():
        param.requires_grad = True

    optimizer = optim.Adam(model_registrar.parameters(), lr=hyperparams["learning_rate"])

    print("=== Starting Finetuning with CAMP-Aligned Safety Loss ===")
    
    for epoch in range(1, hyperparams["train_epochs"] + 1):
        epoch_start_time = time.time()
        trajectron.train()
        pbar = tqdm(train_dataloader, desc=f"Epoch {epoch} Train")
        
        # Compute safety loss warmup factor for this epoch
        if epoch <= warmup_epochs:
            warmup_factor = 0.0   # Pure NLL, no safety
        elif epoch <= warmup_epochs + ramp_epochs:
            warmup_factor = (epoch - warmup_epochs) / ramp_epochs  # Linear 0→1
        else:
            warmup_factor = 1.0   # Full safety
        
        total_nll = 0.0
        total_jerk = 0.0
        total_sdf = 0.0
        total_speed = 0.0
        total_clear = 0.0
        total_safety = 0.0
        n_batches = 0
        skip_nll_nonfinite = 0
        skip_loss_nonfinite = 0
        skip_grad_nonfinite = 0
        
        for batch_idx, batch in enumerate(pbar):
            if max_batches_per_epoch > 0 and batch_idx >= max_batches_per_epoch:
                break

            optimizer.zero_grad()
            
            batch.to(trajectron.device)
            zero = torch.zeros((), device=trajectron.device)
            nll_loss = zero.clone()
            jerk_loss = zero.clone()
            sdf_loss = zero.clone()
            speed_loss = zero.clone()
            clear_loss = zero.clone()
            camp_atom_loss = zero.clone()
            
            # =============================================================
            # Pre-compute SDF from FULL-SIZE raster maps (done once per batch)
            # batch.maps: [B, C, 400, 400] in [0, 1]
            # SDF computed at full 400px resolution for maximum coverage.
            # Then downsample batch.maps to 100×100 for the model's CNN.
            # =============================================================
            has_maps = (hasattr(batch, 'maps') and batch.maps is not None)
            sdf_field = None
            if has_maps:
                # 1. Compute SDF from full-resolution maps (400×400)
                if finetune_loss_mode == "legacy":
                    sdf_field = batch_raster_to_sdf(batch.maps).to(trajectron.device)
                    sdf_field = sdf_field / px_per_m  # convert pixels to meters
                
                # 2. Downsample maps for the model's CNN encoder (400→100)
                if batch.maps.shape[-1] != model_map_size:
                    batch.maps = torch.nn.functional.interpolate(
                        batch.maps, size=(model_map_size, model_map_size),
                        mode='bilinear', align_corners=False
                    )
            
            for node_type in batch.agent_types():
                model = trajectron.node_models_dict[node_type.name]
                agent_batch = batch.for_agent_type(node_type)
                
                # 1. NLL Generative Loss
                loss = model(agent_batch, trajectron.hyperparams.get("update_mode", 0))
                nll_loss += loss
                
                # 2. Extract predicted trajectory samples (differentiable)
                # Use multiple samples (optional) for safety training to avoid overfitting to a
                # single mode that can bypass map constraints.
                ph = agent_batch.agent_fut.shape[1]
                use_single_mode = safety_num_samples == 1
                _, sampled_future = model.predict(
                    agent_batch,
                    prediction_horizon=ph,
                    num_samples=safety_num_samples,
                    z_mode=use_single_mode,
                    gmm_mode=use_single_mode,
                    full_dist=False,
                    output_dists=True,
                )

                # sampled_future shape:
                # - [S, B, T, 2] when S > 1
                # - [1, B, T, 2] or [B, T, 2] when S == 1
                if sampled_future.dim() == 3:
                    sampled_future = sampled_future.unsqueeze(0)

                sample_ct = sampled_future.shape[0]
                pred_traj = sampled_future.reshape(-1, sampled_future.shape[2], 2)  # [S*B, T, 2]
                
                # 3. Kinematic Jerk Penalty (differentiable)
                vel   = pred_traj[:, 1:] - pred_traj[:, :-1]
                accel = vel[:, 1:] - vel[:, :-1]
                jerk  = accel[:, 1:] - accel[:, :-1]
                jerk_norm = torch.norm(jerk, dim=-1)
                if finetune_loss_mode == "legacy":
                    jerk_loss += torch.relu(jerk_norm - 0.5).pow(2).mean()
                
                # 3b. Speed Violation Penalty (differentiable, CLAMPED)
                # Covers CAMP atoms 5-7 (speed violation at 3 margins)
                speed = torch.norm(vel, dim=-1) / dt  # [B, T-1] in m/s
                speed_excess = torch.clamp(torch.relu(speed - speed_limit), max=speed_clamp)
                if finetune_loss_mode == "legacy":
                    speed_loss += speed_excess.pow(2).mean()
                
                # 3c. Clearance / Collision Avoidance Penalty (differentiable)
                # Covers CAMP atom 9 (clearance soft hinge)
                if finetune_loss_mode == "legacy" and hasattr(agent_batch, 'neigh_fut') and agent_batch.neigh_fut is not None:
                    neigh = agent_batch.neigh_fut  # [B, N_neigh, T, D]
                    if neigh.numel() > 0 and neigh.shape[1] > 0:
                        neigh_xy = neigh[..., :2]  # [B, N, T, 2]
                        B_agent = sampled_future.shape[1]
                        T_min = min(pred_traj.shape[1], neigh_xy.shape[2])

                        ego_exp = (
                            sampled_future[:, :B_agent, :T_min]
                            .reshape(-1, T_min, 2)
                            .unsqueeze(1)
                        )  # [S*B, 1, T, 2]
                        neigh_exp = (
                            neigh_xy[:B_agent, :, :T_min]
                            .unsqueeze(0)
                            .expand(sample_ct, -1, -1, -1, -1)
                            .reshape(-1, neigh_xy.shape[1], T_min, 2)
                        )  # [S*B, N, T, 2]
                        # Replace invalid padded neighbor futures before norm.
                        # Doing this only after norm can still leak NaN gradients.
                        neigh_valid = torch.isfinite(neigh_exp).all(dim=-1)  # [B, N, T]
                        far_neigh = ego_exp.detach().expand_as(neigh_exp) + 999.0
                        safe_neigh = torch.where(
                            neigh_valid.unsqueeze(-1), neigh_exp, far_neigh
                        )
                        dist = torch.norm(ego_exp - safe_neigh, dim=-1)      # [B, N, T]
                        dist = torch.where(
                            neigh_valid,
                            dist,
                            torch.full_like(dist, 999.0),
                        )
                        # Hinge: penalize when closer than the soft clearance radius.
                        intrusion = torch.relu(safety_radius + clearance_soft_margin - dist)  # [B, N, T]
                        clear_loss += intrusion.pow(2).mean()
                
                # ==========================================================
                # 4. DIFFERENTIABLE SDF MAP LOSS
                # Convert pred_traj (agent-local coords) to raster grid
                # coordinates, then sample the SDF using grid_sample.
                # This creates a FULLY DIFFERENTIABLE gradient path:
                #   sdf_val → grid_sample → (x,y) → GMM μ → decoder weights
                # ==========================================================
                if finetune_loss_mode == "legacy" and has_maps and sdf_field is not None:
                    B_agent = sampled_future.shape[1]
                    
                    # Get the agent-type-specific SDF slice
                    # agent_batch stores indices into the original batch
                    if hasattr(agent_batch, 'agent_type_batch_idx'):
                        batch_indices = agent_batch.agent_type_batch_idx
                    else:
                        batch_indices = torch.arange(B_agent, device=pred_traj.device)

                    if not torch.is_tensor(batch_indices):
                        batch_indices = torch.as_tensor(batch_indices, device=pred_traj.device)
                    batch_indices = batch_indices.to(pred_traj.device).long()

                    # Safely index into sdf_field and keep local indices aligned with sampled_future.
                    valid_local_idx = torch.nonzero(
                        batch_indices < sdf_field.shape[0], as_tuple=False
                    ).squeeze(-1)
                    if valid_local_idx.numel() > 0:
                        valid_batch_idx = batch_indices[valid_local_idx]
                        agent_sdf = sdf_field[valid_batch_idx]  # [B_valid, 1, H, W]
                        B_valid = agent_sdf.shape[0]
                        agent_sdf = (
                            agent_sdf.unsqueeze(0)
                            .expand(sample_ct, -1, -1, -1, -1)
                            .reshape(-1, agent_sdf.shape[1], agent_sdf.shape[2], agent_sdf.shape[3])
                        )  # [S*B_valid, 1, H, W]
                        H_map = agent_sdf.shape[2]
                        W_map = agent_sdf.shape[3]
                        
                        # Convert predicted agent-frame trajectories to raster pixels.
                        # Prefer exact transforms from trajdata; fall back to analytic offset mapping.
                        traj_for_sdf = sampled_future[:, valid_local_idx].reshape(
                            -1, sampled_future.shape[2], 2
                        )  # [S*B_valid, ph, 2]

                        if (
                            hasattr(agent_batch, "rasters_from_world_tf")
                            and agent_batch.rasters_from_world_tf is not None
                            and hasattr(agent_batch, "agents_from_world_tf")
                            and agent_batch.agents_from_world_tf is not None
                        ):
                            rasters_from_world = agent_batch.rasters_from_world_tf[valid_local_idx].to(
                                traj_for_sdf.device
                            )  # [B_valid, 3, 3]
                            agents_from_world = agent_batch.agents_from_world_tf[valid_local_idx].to(
                                traj_for_sdf.device
                            )  # [B_valid, 3, 3]
                            world_from_agents = torch.linalg.inv(agents_from_world)  # [B_valid, 3, 3]
                            rasters_from_agents = rasters_from_world @ world_from_agents  # [B_valid, 3, 3]
                            rasters_from_agents = (
                                rasters_from_agents.unsqueeze(0)
                                .expand(sample_ct, -1, -1, -1)
                                .reshape(-1, 3, 3)
                            )  # [S*B_valid, 3, 3]

                            ones = torch.ones(
                                traj_for_sdf.shape[0],
                                traj_for_sdf.shape[1],
                                1,
                                device=traj_for_sdf.device,
                                dtype=traj_for_sdf.dtype,
                            )
                            traj_h = torch.cat([traj_for_sdf, ones], dim=-1)  # [S*B_valid, ph, 3]
                            px_h = torch.matmul(traj_h, rasters_from_agents.transpose(1, 2))
                            px_x = px_h[..., 0]
                            px_y = px_h[..., 1]
                        else:
                            origin_px_x = W_map * (0.5 + 0.5 * offset_frac_xy[0])
                            origin_px_y = H_map * (0.5 - 0.5 * offset_frac_xy[1])
                            px_x = traj_for_sdf[..., 0] * px_per_m + origin_px_x
                            px_y = -traj_for_sdf[..., 1] * px_per_m + origin_px_y  # y-flip
                        
                        # Normalize to [-1, 1] for grid_sample
                        # For align_corners=True, use (size - 1) to map pixel centers.
                        grid_x = 2.0 * px_x / max(W_map - 1, 1) - 1.0
                        grid_y = 2.0 * px_y / max(H_map - 1, 1) - 1.0
                        
                        # CRITICAL: Mask out points that fall outside the raster.
                        # Without this, grid_sample returns border values (likely
                        # off-road SDF) for all out-of-bounds points, causing
                        # massive false penalties that destroy the model.
                        in_bounds = (
                            (grid_x > -1.0) & (grid_x < 1.0) &
                            (grid_y > -1.0) & (grid_y < 1.0)
                        )  # [B, ph] bool mask
                        
                        # grid: [B, ph, 1, 2]
                        grid = torch.stack([grid_x, grid_y], dim=-1).unsqueeze(2)
                        
                        # Sample SDF at trajectory points (DIFFERENTIABLE!)
                        sdf_vals = torch.nn.functional.grid_sample(
                            agent_sdf, grid,
                            mode='bilinear',
                            padding_mode='zeros',   # Out-of-bounds → 0 (no penalty)
                            align_corners=True
                        )  # [B, 1, ph, 1]
                        sdf_vals = sdf_vals.squeeze(1).squeeze(-1)  # [B, ph]
                        
                        # Apply in-bounds mask: only penalize points inside the raster
                        sdf_vals = sdf_vals * in_bounds.float()
                        
                        # Penalize only off-road points (SDF > 0), CLAMPED
                        # Clamp prevents a single 50m off-road point from
                        # contributing relu(50)²=2500 to the loss.
                        if in_bounds.any():
                            sdf_clamped = torch.clamp(torch.relu(sdf_vals), max=sdf_clamp)
                            # Sum across time, average across batch (to match NLL scale)
                            traj_sdf_penalty = (sdf_clamped.pow(2) * in_bounds.float()).sum(dim=-1)
                            sdf_loss += traj_sdf_penalty.mean()

                if finetune_loss_mode == "camp_atoms":
                    B_agent = sampled_future.shape[1]
                    source_indices = get_agent_source_indices(
                        agent_batch, B_agent, pred_traj.device
                    )
                    if source_indices.numel() != B_agent:
                        source_indices = torch.arange(
                            B_agent, device=pred_traj.device, dtype=torch.long
                        )

                    speed_limits = []
                    lane_centerlines = []
                    lane_half_widths = []
                    for src_idx in source_indices.detach().cpu().numpy().tolist():
                        try:
                            ctx = extract_driver_context(
                                batch, int(src_idx), map_api=train_dataset, horizon=ph
                            )
                            ctx_speed = float(ctx.speed_limit)
                            ctx_lane_width = float(ctx.lane_half_width)
                            ctx_centerline = ctx.lane_centerline
                        except Exception:
                            ctx_speed = speed_limit
                            ctx_lane_width = lane_half_width
                            ctx_centerline = np.asarray(
                                [[0.0, 0.0], [50.0, 0.0]], dtype=np.float32
                            )

                        if not np.isfinite(ctx_speed) or ctx_speed <= 0.0:
                            ctx_speed = speed_limit
                        if not np.isfinite(ctx_lane_width) or ctx_lane_width <= 0.0:
                            ctx_lane_width = lane_half_width

                        speed_limits.append(ctx_speed)
                        lane_centerlines.append(ctx_centerline)
                        lane_half_widths.append(ctx_lane_width)

                    flat_speed_limits = torch.as_tensor(
                        speed_limits, device=pred_traj.device, dtype=pred_traj.dtype
                    ).unsqueeze(0).expand(sample_ct, -1).reshape(-1)
                    flat_lane_centerlines = []
                    flat_lane_half_widths = []
                    for _ in range(sample_ct):
                        flat_lane_centerlines.extend(lane_centerlines)
                        flat_lane_half_widths.extend(lane_half_widths)

                    kin_atoms = compute_camp_kinematic_atoms(
                        pred_traj, dt=dt, speed_limits=flat_speed_limits
                    )
                    lane_atom = compute_lane_deviation_atom(
                        pred_traj,
                        flat_lane_centerlines,
                        flat_lane_half_widths,
                        dt=dt,
                    )
                    clearance_atom = compute_clearance_atom(
                        sampled_future,
                        agent_batch,
                        safety_radius=safety_radius,
                        clearance_soft_margin=clearance_soft_margin,
                        dt=dt,
                    )
                    camp_atoms = torch.cat(
                        [kin_atoms, lane_atom[:, None], clearance_atom[:, None]],
                        dim=1,
                    )

                    scales = atom_scales_t.to(
                        device=pred_traj.device, dtype=pred_traj.dtype
                    )
                    weights = atom_weights_t.to(
                        device=pred_traj.device, dtype=pred_traj.dtype
                    )
                    norm_atoms = camp_atoms / scales.clamp_min(1e-6)
                    if atom_clip > 0.0:
                        norm_atoms = torch.clamp(norm_atoms, max=atom_clip)

                    per_traj_cost = torch.sum(norm_atoms * weights, dim=-1)
                    camp_atom_loss = camp_atom_loss + reduce_safety_risk(
                        per_traj_cost,
                        risk_type=finetune_risk_type,
                        alpha=finetune_cvar_alpha,
                    )

                    jerk_loss = jerk_loss + norm_atoms[:, :4].mean()
                    speed_loss = speed_loss + norm_atoms[:, 4:7].mean()
                    sdf_loss = sdf_loss + norm_atoms[:, 7].mean()
                    clear_loss = clear_loss + norm_atoms[:, 8].mean()
                
            if not torch.isfinite(nll_loss):
                skip_nll_nonfinite += 1
                if skip_nll_nonfinite <= 3:
                    print(
                        f"[Finetune][Skip] non-finite NLL at epoch={epoch} "
                        f"batch={batch_idx}: {float(nll_loss.detach().cpu())}",
                        flush=True,
                    )
                continue
            
            # Joint Loss: NLL + warmup-scaled safety terms.
            # camp_atoms uses the same 9 normalized atom dimensions as CAMP-Select.
            if finetune_loss_mode == "camp_atoms":
                safety_raw_loss = camp_atom_loss
            else:
                safety_raw_loss = (
                    lambda_jerk * jerk_loss
                    + lambda_sdf * sdf_loss
                    + lambda_speed * speed_loss
                    + lambda_clear * clear_loss
                )

            if warmup_factor > 0.0:
                # Keep safety gradients meaningful relative to NLL.
                # The scale factor is detached so it only reweights, not backpropagates.
                safety_scale = (
                    (nll_loss.detach().abs() * safety_balance)
                    / (safety_raw_loss.detach().abs() + 1e-6)
                )
                safety_scale = torch.clamp(
                    safety_scale, min=safety_balance_min, max=safety_balance_max
                )
            else:
                safety_scale = torch.tensor(1.0, device=nll_loss.device)

            safety_loss = warmup_factor * safety_scale * safety_raw_loss
            joint_loss = nll_loss + safety_loss
            if not torch.isfinite(joint_loss):
                skip_loss_nonfinite += 1
                if skip_loss_nonfinite <= 3:
                    nll_dbg = float(nll_loss.detach().cpu())
                    safe_dbg = float(safety_raw_loss.detach().cpu())
                    scale_dbg = float(safety_scale.detach().cpu())
                    print(
                        f"[Finetune][Skip] non-finite joint loss at epoch={epoch} "
                        f"batch={batch_idx}: nll={nll_dbg:.6g}, "
                        f"safety={safe_dbg:.6g}, scale={scale_dbg:.6g}",
                        flush=True,
                    )
                continue
            joint_loss.backward()
            
            # Catch silent gradient explosions post-backward!
            grad_norm = nn.utils.clip_grad_norm_(model_registrar.parameters(), max_norm=5.0)
            if not torch.isfinite(grad_norm):
                optimizer.zero_grad()
                skip_grad_nonfinite += 1
                if skip_grad_nonfinite <= 3:
                    nll_dbg = float(nll_loss.detach().cpu())
                    safe_dbg = float(safety_raw_loss.detach().cpu())
                    scale_dbg = float(safety_scale.detach().cpu())
                    print(
                        f"[Finetune][Skip] non-finite grad at epoch={epoch} "
                        f"batch={batch_idx}: nll={nll_dbg:.6g}, "
                        f"safety={safe_dbg:.6g}, scale={scale_dbg:.6g}, "
                        f"grad_norm={float(grad_norm.detach().cpu())}",
                        flush=True,
                    )
                continue
                
            optimizer.step()
            n_batches += 1
            
            # Running averages for tqdm display
            _jerk = jerk_loss.item() if isinstance(jerk_loss, torch.Tensor) else 0.0
            _sdf  = sdf_loss.item() if isinstance(sdf_loss, torch.Tensor) else 0.0
            _spd  = speed_loss.item() if isinstance(speed_loss, torch.Tensor) else 0.0
            _clr  = clear_loss.item() if isinstance(clear_loss, torch.Tensor) else 0.0
            _safe = safety_raw_loss.item() if isinstance(safety_raw_loss, torch.Tensor) else 0.0
            _bal = safety_scale.item() if isinstance(safety_scale, torch.Tensor) else float(safety_scale)
            total_nll   += nll_loss.item()
            total_jerk  += _jerk
            total_sdf   += _sdf
            total_speed += _spd
            total_clear += _clr
            total_safety += _safe
            pbar.set_postfix({
                'NLL': f'{total_nll/n_batches:.3f}', 
                'Safe': f'{total_safety/n_batches:.3f}',
                'Jrk': f'{total_jerk/n_batches:.3f}',
                'SDF': f'{total_sdf/n_batches:.3f}',
                'Spd': f'{total_speed/n_batches:.3f}',
                'Clr': f'{total_clear/n_batches:.3f}',
                'W': f'{warmup_factor:.2f}',
                'Bal': f'{_bal:.2f}'
            })

        # Checkpoint
        save_path = os.path.join(model_dir, f"{finetune_checkpoint_prefix}_{epoch}.pt")
        torch.save(model_registrar.state_dict(), save_path)
        epoch_time_s = time.time() - epoch_start_time
        epoch_times_s.append(epoch_time_s)
        if n_batches > 0:
            print(
                f"[Finetune] Epoch {epoch}/{hyperparams['train_epochs']} done | "
                f"time={epoch_time_s:.2f}s | "
                f"NLL={total_nll/n_batches:.4f} | "
                f"Safe={total_safety/n_batches:.4f} | "
                f"SDF={total_sdf/n_batches:.4f} | "
                f"Spd={total_speed/n_batches:.4f} | "
                f"Clr={total_clear/n_batches:.4f}"
            )
        else:
            print(
                f"[Finetune] Epoch {epoch}/{hyperparams['train_epochs']} done | "
                f"time={epoch_time_s:.2f}s | no valid batches | "
                f"skips(nll/loss/grad)="
                f"{skip_nll_nonfinite}/{skip_loss_nonfinite}/{skip_grad_nonfinite}"
            )

    total_time_s = time.time() - script_start_time
    timing_output_path = os.environ.get("FINETUNE_TIMING_OUTPUT_PATH", "").strip()
    if not timing_output_path:
        timing_output_path = os.path.join(model_dir, "finetune_safe_timing.json")
    timing_parent = os.path.dirname(timing_output_path)
    if timing_parent:
        os.makedirs(timing_parent, exist_ok=True)
    timing_payload = {
        "base_epoch": int(base_epoch),
        "train_epochs": int(hyperparams["train_epochs"]),
        "loss_mode": finetune_loss_mode,
        "checkpoint_prefix": finetune_checkpoint_prefix,
        "risk_type": finetune_risk_type,
        "cvar_alpha": float(finetune_cvar_alpha),
        "atom_clip": float(atom_clip),
        "safety_radius": float(safety_radius),
        "clearance_soft_margin": float(clearance_soft_margin),
        "clearance_radius": float(safety_radius + clearance_soft_margin),
        "atom_scales_path": getattr(base_args, "finetune_atom_scales_path", ""),
        "atom_weights": [float(x) for x in atom_weights_np],
        "total_time_s": float(total_time_s),
        "avg_epoch_time_s": float(np.mean(epoch_times_s)) if epoch_times_s else 0.0,
        "epoch_times_s": [float(x) for x in epoch_times_s],
    }
    with open(timing_output_path, "w", encoding="utf-8") as f:
        json.dump(timing_payload, f, ensure_ascii=False, indent=2)
    print(f"[Finetune] Saved timing to {timing_output_path}")
    print(f"[Finetune] Total training time: {total_time_s/60:.2f} min")
            
if __name__ == "__main__":
    train_finetune()
