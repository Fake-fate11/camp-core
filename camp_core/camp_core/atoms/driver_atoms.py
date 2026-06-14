from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Sequence

import numpy as np


@dataclass
class DriverAtomContext:
    """
    Minimal geometric/kinematic context needed to evaluate driver atoms.
    """
    dt: float
    lane_centerline: np.ndarray
    static_obstacles: Optional[np.ndarray] = None
    dynamic_obstacles: Optional[Dict[int, np.ndarray]] = None
    speed_limit: Optional[float] = None
    desired_speed: Optional[float] = None
    lane_half_width: float = 1.8
    lane_corridor_buffer: float = 1.0
    safety_radius: float = 2.0
    clearance_soft_margin: float = 1.0
    map_source: str = "fallback"
    
    # Scale parameters
    jerk_scale: float = 1.0 
    acc_scale: float = 1.0 # Added for Acc Energy
    rms_scale: float = 1.0 # Added for RMS Acc
    speed_limit_scale: float = 1.0
    # Aux scales
    progress_scale: float = 1.0
    clearance_scale: float = 1.0
    lane_scale: float = 1.0
    
    eps: float = 1e-6

@dataclass
class AtomBankConfig:
    """
    Configuration for strict Atom Bank construction.
    Default: one window [0, T], one margin [0].
    """
    # List of (start, end) tuples for windows. If None, uses [(0, T)].
    windows: Optional[List[Tuple[int, int]]] = None
    # List of speed margins. Default [0.0].
    speed_margins: List[float] = field(default_factory=lambda: [0.0])


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _finite_difference_vel(traj_xy: np.ndarray, dt: float) -> np.ndarray:
    if traj_xy.shape[0] < 2: return np.zeros((0, 2))
    return np.diff(traj_xy, axis=0) / dt

def _finite_difference_acc(vel_xy: np.ndarray, dt: float) -> np.ndarray:
    if vel_xy.shape[0] < 2: return np.zeros((0, 2))
    return np.diff(vel_xy, axis=0) / dt

def _finite_difference_jerk(acc_xy: np.ndarray, dt: float) -> np.ndarray:
    if acc_xy.shape[0] < 2: return np.zeros((0, 2))
    return np.diff(acc_xy, axis=0) / dt

def _project_point_onto_polyline(p, centerline):
    # Simplified projection for brevity (matches existing logic)
    seg_vecs = centerline[1:] - centerline[:-1]
    seg_lens = np.maximum(np.linalg.norm(seg_vecs, axis=1), 1e-6)
    seg_dirs = seg_vecs / seg_lens[:, None]
    
    rel = p - centerline[:-1]
    t = np.einsum("md,md->m", rel, seg_dirs)
    t = np.clip(t, 0.0, seg_lens)
    projs = centerline[:-1] + seg_dirs * t[:, None]
    dists = np.linalg.norm(p - projs, axis=1)
    
    idx = np.argmin(dists)
    # Lateral calc
    best_dir = seg_dirs[idx]
    diff = p - projs[idx]
    cross = best_dir[0]*diff[1] - best_dir[1]*diff[0]
    return float(np.sign(cross)*dists[idx])

def _project_onto_centerline(
    traj_xy: np.ndarray, centerline: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Project all trajectory points onto a lane centerline polyline.
    Restored for backward compatibility with camp_core.metrics.driver_atoms.

    Returns
    -------
    s : [H]
    d : [H]
    """
    # Simply loop _project_point_onto_polyline if we assume it returns (s, d).
    # BUT my simplified _project_point_onto_polyline above ONLY returns d (float).
    # The legacy code expects (s, d).
    # So I must either:
    # 1. Update _project_point_onto_polyline to return both s, d.
    # 2. Or re-implement the full logic here.
    
    # Let's restore full logic for valid S and D.
    
    traj_xy = np.asarray(traj_xy, dtype=float)
    centerline = np.asarray(centerline, dtype=float)
    
    seg_vecs = centerline[1:] - centerline[:-1]
    seg_lens = np.linalg.norm(seg_vecs, axis=1)
    seg_lens = np.maximum(seg_lens, 1e-6)
    seg_dirs = seg_vecs / seg_lens[:, None]
    cum_s = np.concatenate([[0.0], np.cumsum(seg_lens)])

    rel = traj_xy[:, np.newaxis, :] - centerline[np.newaxis, :-1, :]
    along = np.einsum("hmd,md->hm", rel, seg_dirs)
    along = np.clip(along, 0.0, seg_lens[np.newaxis, :])
    projections = (
        centerline[np.newaxis, :-1, :]
        + seg_dirs[np.newaxis, :, :] * along[:, :, np.newaxis]
    )
    differences = traj_xy[:, np.newaxis, :] - projections
    distance_sq = np.sum(differences**2, axis=2)
    segment_indices = np.argmin(distance_sq, axis=1)
    row_indices = np.arange(traj_xy.shape[0])
    best_differences = differences[row_indices, segment_indices]
    best_directions = seg_dirs[segment_indices]
    cross = (
        best_directions[:, 0] * best_differences[:, 1]
        - best_directions[:, 1] * best_differences[:, 0]
    )
    s_values = cum_s[segment_indices] + along[row_indices, segment_indices]
    d_values = np.sign(cross) * np.sqrt(
        distance_sq[row_indices, segment_indices]
    )
    return s_values, d_values

# ---------------------------------------------------------------------------
# Strict Atom Bank Logic
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Strict Atom Bank Logic (Refactored Phase 3)
# ---------------------------------------------------------------------------

def compute_atom_bank_vector(
    ctx: DriverAtomContext, 
    traj_xy: np.ndarray, 
    config: Optional[AtomBankConfig] = None
) -> np.ndarray:
    """
    Compute the strict Atom Bank vector A(xi, y) of dimension R=9 (default).
    
    Structure:
    1-3. Jerk Energy (Early, Late, Full)
    4.   RMS Acc (Full)
    5-7. Speed Violation (Margins 0.0, 0.5, 1.0)
    8.   Lane Deviation (Hinge)
    9.   Clearance (Soft Hinge)
    
    Returns: Vector [R] (Not Normalized - Normalization happens in Training Loop)
    """
    traj_xy = np.asarray(traj_xy, dtype=float)
    T = traj_xy.shape[0]
    dt = ctx.dt
    
    # 1. Kinematics
    vel = _finite_difference_vel(traj_xy, dt) # T-1
    acc = _finite_difference_acc(vel, dt)     # T-2
    jerk = _finite_difference_jerk(acc, dt)   # T-3
    
    atoms = []
    
    # --- Group 1: Jerk Energy [3 Atoms] ---
    # Windows: Early (0-0.25s), Late (0.25s-End), Full
    # 0.25s is rough. If dt=0.5, step 0 is 0-0.5.
    # If dt=0.5s, T=12 (6s).
    # "Early" usually means first few steps. Let's define Early as first 1/3 (approx 1-2s), Late as rest?
    # User said: "Early (0-0.25s), Late (0.25-0.5s)".
    # Wait, user example: "early (0-0.25s)". That is extremely short!
    # If dt=0.5, 0.25s is HALF a step.
    # Maybe user meant relative to horizon? Or user is thinking 10hz (dt=0.1)?
    # NuScenes prediction is often 2Hz (dt=0.5).
    # If dt=0.5, then "Early" must cover at least index 0.
    # Let's interpret "Early" as "First 2 steps" (1.0s) and "Late" as "Rest"?
    # Or strictly follow indices.
    # Assuming T=12 (6s).
    # Let's use proportional windows if not specified.
    # W1 (Early): [0, T//3]
    # W2 (Late):  [T//3, T]
    # W3 (Full):  [0, T]
    
    jerk_sq = np.sum(jerk**2, axis=1) if jerk.shape[0] > 0 else np.zeros(0) # [T-3]
    T_j = len(jerk_sq)
    
    # Define Split Indices
    # For T=12, T_j=9. Split at 3 (1.5s).
    split_idx = max(1, T_j // 3)
    
    windows = [
        (0, split_idx),    # Early
        (split_idx, T_j),  # Late
        (0, T_j)           # Full
    ]
    
    for (s, e) in windows:
        if s < e and s < T_j:
            val = dt * np.sum(jerk_sq[s:e])
        else:
            val = 0.0
        atoms.append(val)
        
    # --- Group 2: RMS Acc [1 Atom] ---
    # Full Window Only
    acc_sq = np.sum(acc**2, axis=1) if acc.shape[0] > 0 else np.zeros(0)
    if len(acc_sq) > 0:
        # RMS = sqrt( Sum(a^2)*dt / Duration )
        # Duration = len * dt
        # -> sqrt( Sum(a^2) / len )
        mean_acc_sq = np.mean(acc_sq)
        val = np.sqrt(mean_acc_sq)
    else:
        val = 0.0
    atoms.append(val)
    
    # --- Group 3: Speed Violation [3 Atoms] ---
    # Margins: 0.0, 0.5, 1.0 m/s
    speed_vals = np.linalg.norm(vel, axis=1) if vel.shape[0] > 0 else np.zeros(0)
    limit = ctx.speed_limit if ctx.speed_limit is not None else 100.0
    margins = [0.0, 0.5, 1.0]
    
    for tau in margins:
        thresh = limit - tau
        if len(speed_vals) > 0:
            viol = np.maximum(0.0, speed_vals - thresh)
            val = dt * np.sum(viol**2)
        else:
            val = 0.0
        atoms.append(val)
        
    # --- Group 4: Lane Deviation [1 Atom] ---
    # Hinge Loss: max(0, |d| - lane_width)^2
    # Project points
    d_vals = []
    # Optimization: project only if centerline exists
    if ctx.lane_centerline is not None:
        _, signed_offsets = _project_onto_centerline(
            traj_xy,
            ctx.lane_centerline,
        )
        d_vals = np.abs(signed_offsets)
    else:
        d_vals = np.zeros(T, dtype=float)
    # Hinge
    lane_viol = np.maximum(0.0, d_vals - ctx.lane_half_width)
    atom_lane = dt * np.sum(lane_viol**2)
    atoms.append(atom_lane)

    # --- Group 5: Clearance (Soft Hinge) [1 Atom] ---
    # max(0, soft_clearance_radius - min_dist)^2
    # Reuse auxiliary function logic or simplify
    # We want atom to be "Sum of intrusion over time"? 
    # Or just "min dist" based?
    # Definition in prompt: "dt * sum (max(0, d_safe - d_t))^2"
    
    # Calc dists
    # Simplified: Distance to closest static/dynamic at each step
    # This is expensive. Let's do a rough pass.
    
    d_safe = ctx.safety_radius + ctx.clearance_soft_margin
    total_clearance_cost = 0.0

    has_static = ctx.static_obstacles is not None and len(ctx.static_obstacles) > 0
    has_dynamic = bool(ctx.dynamic_obstacles)

    if has_static or has_dynamic:
        min_distances = np.full(T, 999.0, dtype=float)
        if has_dynamic:
            for obs_traj in ctx.dynamic_obstacles.values():
                obstacle_xy = np.asarray(obs_traj, dtype=float)[:, :2]
                horizon = min(T, len(obstacle_xy))
                if horizon == 0:
                    continue
                distances = np.linalg.norm(
                    traj_xy[:horizon] - obstacle_xy[:horizon],
                    axis=1,
                )
                distances = np.where(np.isfinite(distances), distances, 999.0)
                min_distances[:horizon] = np.minimum(
                    min_distances[:horizon],
                    distances,
                )
        if has_static:
            static_distances = np.linalg.norm(
                traj_xy[:, np.newaxis, :]
                - np.asarray(ctx.static_obstacles, dtype=float)[
                    np.newaxis, :, :2
                ],
                axis=2,
            )
            closest_static = np.min(static_distances, axis=1)
            closest_static = np.where(
                np.isfinite(closest_static),
                closest_static,
                999.0,
            )
            min_distances = np.minimum(min_distances, closest_static)
        intrusions = np.maximum(0.0, d_safe - min_distances)
        total_clearance_cost = float(np.sum(intrusions**2))
            
    atoms.append(total_clearance_cost * dt)
    
    return np.array(atoms, dtype=float)


def _project_batch_onto_centerline(
    traj_xy: np.ndarray,
    centerline: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    trajectories = np.asarray(traj_xy, dtype=float)
    line = np.asarray(centerline, dtype=float)
    if trajectories.ndim != 3 or trajectories.shape[-1] != 2:
        raise ValueError(
            "traj_xy must have shape [K, T, 2], "
            f"got {trajectories.shape}."
        )
    if line.ndim != 2 or line.shape[0] < 2 or line.shape[1] < 2:
        raise ValueError(
            "centerline must have shape [N, 2+] with at least two points, "
            f"got {line.shape}."
        )

    points = line[:, :2]
    seg_vecs = points[1:] - points[:-1]
    seg_lens = np.linalg.norm(seg_vecs, axis=1)
    seg_lens = np.maximum(seg_lens, 1e-6)
    seg_dirs = seg_vecs / seg_lens[:, None]
    cum_s = np.concatenate([[0.0], np.cumsum(seg_lens)])

    rel = trajectories[:, :, np.newaxis, :] - points[np.newaxis, np.newaxis, :-1, :]
    along = np.einsum("ktmd,md->ktm", rel, seg_dirs)
    along = np.clip(along, 0.0, seg_lens[np.newaxis, np.newaxis, :])
    projections = (
        points[np.newaxis, np.newaxis, :-1, :]
        + seg_dirs[np.newaxis, np.newaxis, :, :] * along[:, :, :, np.newaxis]
    )
    differences = trajectories[:, :, np.newaxis, :] - projections
    distance_sq = np.sum(differences**2, axis=3)
    segment_indices = np.argmin(distance_sq, axis=2)
    gather_idx = segment_indices[:, :, np.newaxis, np.newaxis]
    best_differences = np.take_along_axis(
        differences,
        gather_idx,
        axis=2,
    )[:, :, 0, :]
    best_directions = seg_dirs[segment_indices]
    best_along = np.take_along_axis(
        along,
        segment_indices[:, :, np.newaxis],
        axis=2,
    )[:, :, 0]
    best_distance_sq = np.take_along_axis(
        distance_sq,
        segment_indices[:, :, np.newaxis],
        axis=2,
    )[:, :, 0]
    cross = (
        best_directions[:, :, 0] * best_differences[:, :, 1]
        - best_directions[:, :, 1] * best_differences[:, :, 0]
    )
    s_values = cum_s[segment_indices] + best_along
    d_values = np.sign(cross) * np.sqrt(best_distance_sq)
    return s_values, d_values


def compute_atom_bank_matrix(
    ctx: DriverAtomContext,
    trajectories_xy: np.ndarray,
    *,
    candidate_dynamic_obstacles: Optional[np.ndarray] = None,
    config: Optional[AtomBankConfig] = None,
) -> np.ndarray:
    """Compute CAMP base atoms for a batch of candidates.

    The result is numerically equivalent to stacking ``compute_atom_bank_vector``
    over candidates. The batched path keeps the atom definitions unchanged while
    avoiding repeated centerline projection setup in DP replay.
    """
    trajectories = np.asarray(trajectories_xy, dtype=float)
    if trajectories.ndim != 3 or trajectories.shape[-1] != 2:
        raise ValueError(
            "trajectories_xy must have shape [K, T, 2], "
            f"got {trajectories.shape}."
        )
    if config is not None:
        return np.vstack(
            [
                compute_atom_bank_vector(ctx, trajectory, config)
                for trajectory in trajectories
            ]
        )

    candidate_count, horizon_steps = trajectories.shape[:2]
    dt = float(ctx.dt)
    atoms = np.zeros((candidate_count, 9), dtype=float)

    vel = np.diff(trajectories, axis=1) / dt if horizon_steps >= 2 else np.zeros(
        (candidate_count, 0, 2),
        dtype=float,
    )
    acc = np.diff(vel, axis=1) / dt if vel.shape[1] >= 2 else np.zeros(
        (candidate_count, 0, 2),
        dtype=float,
    )
    jerk = np.diff(acc, axis=1) / dt if acc.shape[1] >= 2 else np.zeros(
        (candidate_count, 0, 2),
        dtype=float,
    )

    jerk_sq = np.sum(jerk**2, axis=2) if jerk.shape[1] > 0 else np.zeros(
        (candidate_count, 0),
        dtype=float,
    )
    jerk_steps = jerk_sq.shape[1]
    split_idx = max(1, jerk_steps // 3)
    windows = ((0, split_idx), (split_idx, jerk_steps), (0, jerk_steps))
    for atom_idx, (start, end) in enumerate(windows):
        if start < end and start < jerk_steps:
            atoms[:, atom_idx] = dt * np.sum(jerk_sq[:, start:end], axis=1)

    acc_sq = np.sum(acc**2, axis=2) if acc.shape[1] > 0 else np.zeros(
        (candidate_count, 0),
        dtype=float,
    )
    if acc_sq.shape[1] > 0:
        atoms[:, 3] = np.sqrt(np.mean(acc_sq, axis=1))

    speeds = np.linalg.norm(vel, axis=2) if vel.shape[1] > 0 else np.zeros(
        (candidate_count, 0),
        dtype=float,
    )
    limit = ctx.speed_limit if ctx.speed_limit is not None else 100.0
    for offset, margin in enumerate((0.0, 0.5, 1.0), start=4):
        if speeds.shape[1] > 0:
            violation = np.maximum(0.0, speeds - (float(limit) - margin))
            atoms[:, offset] = dt * np.sum(violation**2, axis=1)

    if ctx.lane_centerline is not None:
        _, signed_offsets = _project_batch_onto_centerline(
            trajectories,
            ctx.lane_centerline,
        )
        lateral_offsets = np.abs(signed_offsets)
    else:
        lateral_offsets = np.zeros((candidate_count, horizon_steps), dtype=float)
    lane_violation = np.maximum(0.0, lateral_offsets - ctx.lane_half_width)
    atoms[:, 7] = dt * np.sum(lane_violation**2, axis=1)

    d_safe = ctx.safety_radius + ctx.clearance_soft_margin
    min_distances = np.full((candidate_count, horizon_steps), 999.0, dtype=float)
    has_clearance_source = False

    if candidate_dynamic_obstacles is not None:
        obstacles = np.asarray(candidate_dynamic_obstacles, dtype=float)
        if (
            obstacles.ndim != 4
            or obstacles.shape[0] != candidate_count
            or obstacles.shape[-1] < 2
        ):
            raise ValueError(
                "candidate_dynamic_obstacles must have shape [K, M, T, D>=2], "
                f"got {obstacles.shape}."
            )
        obstacle_horizon = min(horizon_steps, obstacles.shape[2])
        if obstacle_horizon > 0 and obstacles.shape[1] > 0:
            obstacle_xy = obstacles[:, :, :obstacle_horizon, :2]
            valid_obstacle = np.any(np.abs(obstacle_xy) > 1e-8, axis=(2, 3))
            if valid_obstacle.any():
                distances = np.linalg.norm(
                    trajectories[:, np.newaxis, :obstacle_horizon, :]
                    - obstacle_xy,
                    axis=3,
                )
                distances = np.where(np.isfinite(distances), distances, 999.0)
                distances = np.where(
                    valid_obstacle[:, :, np.newaxis],
                    distances,
                    999.0,
                )
                min_distances[:, :obstacle_horizon] = np.minimum(
                    min_distances[:, :obstacle_horizon],
                    np.min(distances, axis=1),
                )
                has_clearance_source = True
    elif ctx.dynamic_obstacles:
        for obstacle in ctx.dynamic_obstacles.values():
            obstacle_xy = np.asarray(obstacle, dtype=float)[:, :2]
            obstacle_horizon = min(horizon_steps, len(obstacle_xy))
            if obstacle_horizon == 0:
                continue
            distances = np.linalg.norm(
                trajectories[:, :obstacle_horizon, :]
                - obstacle_xy[np.newaxis, :obstacle_horizon, :],
                axis=2,
            )
            distances = np.where(np.isfinite(distances), distances, 999.0)
            min_distances[:, :obstacle_horizon] = np.minimum(
                min_distances[:, :obstacle_horizon],
                distances,
            )
            has_clearance_source = True

    has_static = ctx.static_obstacles is not None and len(ctx.static_obstacles) > 0
    if has_static:
        static_xy = np.asarray(ctx.static_obstacles, dtype=float)[:, :2]
        static_distances = np.linalg.norm(
            trajectories[:, :, np.newaxis, :]
            - static_xy[np.newaxis, np.newaxis, :, :],
            axis=3,
        )
        closest_static = np.min(static_distances, axis=2)
        closest_static = np.where(np.isfinite(closest_static), closest_static, 999.0)
        min_distances = np.minimum(min_distances, closest_static)
        has_clearance_source = True

    if has_clearance_source:
        intrusions = np.maximum(0.0, d_safe - min_distances)
        atoms[:, 8] = dt * np.sum(intrusions**2, axis=1)

    return atoms


def compute_feasibility_mask(
    ctx: DriverAtomContext, 
    traj_xy: np.ndarray,
    check_speed: bool = True,
    check_lane: bool = True
) -> bool:
    """
    Check if a trajectory satisfies HARD Feasibility Constraints.
    Returns True if Feasible.
    """
    traj_xy = np.asarray(traj_xy, dtype=float)
    dt = ctx.dt
    
    # 1. Lane Corridor (Hard Constraint)
    # Must stay within lane_width + buffer
    # Buffer: e.g. 0.5m extra
    if check_lane and ctx.lane_centerline is not None:
        _, signed_offsets = _project_onto_centerline(
            traj_xy,
            ctx.lane_centerline,
        )
        max_dev = float(np.max(np.abs(signed_offsets), initial=0.0))
        
        if max_dev > (ctx.lane_half_width + ctx.lane_corridor_buffer):
            return False
            
    # 2. Speed Cap (Hard Constraint)
    # Must not exceed limit + 5.0m/s (Hard buffer)
    if check_speed and ctx.speed_limit is not None:
        vel = _finite_difference_vel(traj_xy, dt)
        speeds = np.linalg.norm(vel, axis=1)
        if len(speeds) > 0:
            max_v = np.max(speeds)
            if max_v > (ctx.speed_limit + 5.0): # Tolerant hard cap
                return False
                
    # 3. Collision (Already in atoms? No, hard mask)
    # If collision (d < r_collision), Infeasible.
    # r_collision usually small (e.g. 0.5m overlap)
    # Let's check auxiliary
    # aux = compute_aux_metrics(ctx, traj_xy)
    # if not aux.is_feasible: return False
    
    return True

# ---------------------------------------------------------------------------
# Non-Atom Signals (Auxiliary)
# ---------------------------------------------------------------------------

@dataclass
class AuxiliaryMetrics:
    lane_deviation: float
    clearance: float
    progress: float
    is_feasible: bool

def compute_aux_metrics(
    ctx: DriverAtomContext, traj_xy: np.ndarray
) -> AuxiliaryMetrics:
    """
    Compute Progress, Clearance, Lane Deviation, etc.
    These are just for reporting/filtering, NOT optimization atoms.
    """
    traj_xy = np.asarray(traj_xy, dtype=float)
    T = traj_xy.shape[0]
    
    # 1. Lane
    d_vals = []
    if ctx.lane_centerline is not None:
        _, signed_offsets = _project_onto_centerline(
            traj_xy,
            ctx.lane_centerline,
        )
        d_vals = signed_offsets
    else: 
        d_vals = np.zeros(T, dtype=float)
    d_vals = np.abs(np.array(d_vals))
    lane_mean = float(np.mean(d_vals))
    
    # 2. Clearance
    # Simplified check
    min_dist = 999.0
    # Dynamic
    if ctx.dynamic_obstacles:
        for obs_traj in ctx.dynamic_obstacles.values():
            # Check overlap len
            l = min(len(traj_xy), len(obs_traj))
            if l > 0:
                d = np.linalg.norm(traj_xy[:l] - obs_traj[:l], axis=1).min()
                min_dist = min(min_dist, d)
                
    thresh = ctx.safety_radius
    is_feasible = (min_dist >= thresh)
    clearance_val = float(min_dist)
    
    # 3. Progress
    progress_val = np.linalg.norm(traj_xy[-1] - traj_xy[0])
    
    return AuxiliaryMetrics(
        lane_deviation=lane_mean,
        clearance=clearance_val,
        progress=progress_val,
        is_feasible=is_feasible
    )

# ---------------------------------------------------------------------------
# Legacy Compatibility (Restored for train_offline_preference.py / metrics)
# ---------------------------------------------------------------------------

@dataclass
class DriverAtomFeatures:
    """
    Legacy wrapper for atom features.
    Used by metrics/driver_atoms.py and offline preference training.
    """
    jerk: float
    smoothness: float
    lane_deviation: float
    clearance: float
    speed_limit_violation: float
    progress_deficit: float

    def as_vector(self) -> np.ndarray:
        return np.array(
            [
                self.jerk, 
                self.smoothness,
                self.lane_deviation,
                self.speed_limit_violation,
                self.progress_deficit,
                self.clearance,
            ],
            dtype=float,
        )

def compute_driver_atom_features(ctx: DriverAtomContext, traj_xy: np.ndarray) -> DriverAtomFeatures:
    """
    Compute 'legacy' atoms using the new helpers or reimplementation.
    Matches the signature expected by legacy code.
    """
    # 1. Use new atomic helpers if possible, or re-compute.
    # New helpers return normalized/summed values in compute_atom_bank_vector.
    # We need Raw values for legacy features (which applied scaling later).
    
    traj_xy = np.asarray(traj_xy, dtype=float)
    dt = ctx.dt
    
    # Kinematics
    vel = _finite_difference_vel(traj_xy, dt)
    acc = _finite_difference_acc(vel, dt)
    jerk = _finite_difference_jerk(acc, dt)
    
    # Jerk (Mean Sq)
    if jerk.shape[0] > 0:
        jerk_val = float(np.mean(np.sum(jerk**2, axis=1)))
    else:
        jerk_val = 0.0
        
    # Smoothness (Mean Sq Acc)
    if acc.shape[0] > 0:
        smooth_val = float(np.mean(np.sum(acc**2, axis=1)))
    else:
        smooth_val = 0.0
        
    # Lane Deviation
    aux = compute_aux_metrics(ctx, traj_xy)
    lane_val = aux.lane_deviation
    clear_val = aux.clearance
    
    # Speed Limit
    # Legacy: Sum of squared violations? Or Mean?
    # Original code: Mean(violation^2)
    speeds = np.linalg.norm(vel, axis=1) if vel.shape[0] > 0 else np.zeros(0)
    limit = ctx.speed_limit if ctx.speed_limit is not None else 100.0
    if len(speeds) > 0:
        viol = np.maximum(0.0, speeds - limit)
        speed_val = float(np.mean(viol**2))
    else:
        speed_val = 0.0
        
    # Progress Deficit
    # Legacy: (Desired - Actual)^2
    # aux.progress is Actual Distance.
    if ctx.desired_speed is None: d_speed = 1.0
    else: d_speed = float(ctx.desired_speed)
    
    # Horizon time
    H = traj_xy.shape[0]
    horizon = (H - 1) * dt
    desired_dist = d_speed * horizon
    actual_dist = aux.progress # Approximation
    shortfall = max(0.0, desired_dist - actual_dist)
    prog_val = float(shortfall**2)
    
    return DriverAtomFeatures(
        jerk=jerk_val,
        smoothness=smooth_val,
        lane_deviation=lane_val,
        clearance=clear_val,
        speed_limit_violation=speed_val,
        progress_deficit=prog_val
    )
