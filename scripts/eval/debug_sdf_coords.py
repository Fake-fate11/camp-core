"""
Quick debug script: verify SDF coordinate mapping.
If GT trajectory points (which are ON the road) show SDF > 0,
the coordinate transform is WRONG and needs to be fixed.
"""
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import torch
import torch.nn.functional as F
from scipy.ndimage import distance_transform_edt
from collections import defaultdict
from trajdata import AgentType, UnifiedDataset

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def batch_raster_to_sdf(maps_tensor, drivable_channel=0, drivable_thresh=0.5):
    B = maps_tensor.shape[0]
    sdfs = []
    for i in range(B):
        drivable = (maps_tensor[i, drivable_channel].cpu().numpy() > drivable_thresh)
        dist_inside  = distance_transform_edt(drivable)
        dist_outside = distance_transform_edt(~drivable)
        sdf = dist_outside - dist_inside
        sdfs.append(sdf)
    sdf_batch = np.stack(sdfs, axis=0)
    return torch.tensor(sdf_batch, dtype=torch.float32).unsqueeze(1)

def main():
    px_per_m = 2
    map_size_px = 100
    offset_frac_xy = (-0.75, 0.0)
    
    attention_radius = defaultdict(lambda: 20.0)
    attention_radius[(AgentType.PEDESTRIAN, AgentType.PEDESTRIAN)] = 10.0
    attention_radius[(AgentType.PEDESTRIAN, AgentType.VEHICLE)] = 20.0
    attention_radius[(AgentType.VEHICLE, AgentType.PEDESTRIAN)] = 20.0
    attention_radius[(AgentType.VEHICLE, AgentType.VEHICLE)] = 30.0

    map_params = {"px_per_m": px_per_m, "map_size_px": map_size_px, "offset_frac_xy": offset_frac_xy}
    
    print("Loading dataset...")
    dataset = UnifiedDataset(
        desired_data=["nusc_trainval-val"],
        history_sec=(2.0, 2.0),
        future_sec=(6.0, 6.0),
        agent_interaction_distances=attention_radius,
        incl_robot_future=False,
        incl_raster_map=True,
        raster_map_params=map_params,
        only_predict=[AgentType.VEHICLE],
        no_types=[AgentType.UNKNOWN],
        num_workers=0,
        cache_location=os.path.expanduser("~/.unified_data_cache"),
        data_dirs={"nusc_trainval": "/root/autodl-tmp/dataset"},
        verbose=True,
    )
    
    from torch.utils.data import DataLoader
    dl = DataLoader(dataset, collate_fn=dataset.get_collate_fn(pad_format="right"),
                    batch_size=8, shuffle=False, num_workers=0)
    
    batch = next(iter(dl))
    print(f"\nbatch.maps shape: {batch.maps.shape}")  # [B, C, H, W]
    print(f"batch.maps channels: {batch.maps.shape[1]}")
    print(f"batch.maps value range: [{batch.maps.min():.3f}, {batch.maps.max():.3f}]")
    
    # Show what each channel looks like
    for c in range(min(batch.maps.shape[1], 5)):
        ch = batch.maps[0, c].numpy()
        unique_vals = np.unique(ch)
        print(f"  Channel {c}: min={ch.min():.3f} max={ch.max():.3f} unique_count={len(unique_vals)}")
    
    # Compute SDF
    sdf_field = batch_raster_to_sdf(batch.maps)
    sdf_field_m = sdf_field / px_per_m  # in meters
    
    # === Test 1: Sample SDF at origin (agent's current position) ===
    # Agent is at (0,0) in agent-local coords
    # In pixel coords: px_x = 0 * px_per_m + W * (-offset[0]) = 100 * 0.75 = 75
    #                  px_y = -0 * px_per_m + H * (0.5 - offset[1]) = 100 * 0.5 = 50
    origin_px_x = map_size_px * (-offset_frac_xy[0])
    origin_px_y = map_size_px * (0.5 - offset_frac_xy[1])
    print(f"\nAgent origin in pixel coords: ({origin_px_x}, {origin_px_y})")
    
    # Direct SDF lookup at agent origin
    ox, oy = int(origin_px_x), int(origin_px_y)
    if 0 <= ox < map_size_px and 0 <= oy < map_size_px:
        sdf_at_origin = sdf_field_m[0, 0, oy, ox].item()
        print(f"SDF at agent origin (direct lookup): {sdf_at_origin:.3f} m")
        print(f"  => {'IN ROAD (correct!)' if sdf_at_origin < 0 else 'OFF ROAD (WRONG!)'}")
    
    # === Test 2: Sample SDF at GT trajectory points ===
    gt_traj = batch.agent_fut[0].numpy()[:, :2]  # [T, 2]
    print(f"\nGT trajectory (first 5 points, agent-local meters):")
    for t in range(min(5, len(gt_traj))):
        print(f"  t={t}: x={gt_traj[t, 0]:.2f}, y={gt_traj[t, 1]:.2f}")
    
    # Convert GT points to pixel coords and sample SDF
    print(f"\nSDF values at GT trajectory points:")
    gt_sdf_vals = []
    for t in range(len(gt_traj)):
        x_m, y_m = gt_traj[t]
        if np.isnan(x_m) or np.isnan(y_m):
            break
        px_x = x_m * px_per_m + origin_px_x
        px_y = -y_m * px_per_m + origin_px_y  # y-flip as in training code
        px_xi, px_yi = int(round(px_x)), int(round(px_y))
        if 0 <= px_xi < map_size_px and 0 <= px_yi < map_size_px:
            sdf_val = sdf_field_m[0, 0, px_yi, px_xi].item()
            gt_sdf_vals.append(sdf_val)
            marker = "✓ ROAD" if sdf_val < 0 else "✗ OFF-ROAD"
            if t < 12:
                print(f"  t={t}: pixel=({px_xi},{px_yi}) SDF={sdf_val:+.3f}m {marker}")
        else:
            print(f"  t={t}: pixel=({px_xi},{px_yi}) OUT OF RASTER BOUNDS")
    
    if gt_sdf_vals:
        n_positive = sum(1 for v in gt_sdf_vals if v > 0)
        n_total = len(gt_sdf_vals)
        print(f"\n=== VERDICT ===")
        print(f"GT points with SDF > 0 (off-road): {n_positive}/{n_total}")
        if n_positive > n_total * 0.3:
            print("❌ COORDINATE TRANSFORM IS LIKELY WRONG!")
            print("   GT trajectory should be on-road but SDF says it's off-road.")
        else:
            print("✓ Coordinate transform looks correct.")
            print("  If training still collapsed, lambda_sdf is too large.")
    
    # === Test 3: Also try WITHOUT y-flip to compare ===
    print(f"\n--- Comparison: WITHOUT y-flip ---")
    for t in range(min(5, len(gt_traj))):
        x_m, y_m = gt_traj[t]
        if np.isnan(x_m) or np.isnan(y_m):
            break
        px_x = x_m * px_per_m + origin_px_x
        px_y = y_m * px_per_m + origin_px_y  # NO y-flip
        px_xi, px_yi = int(round(px_x)), int(round(px_y))
        if 0 <= px_xi < map_size_px and 0 <= px_yi < map_size_px:
            sdf_val = sdf_field_m[0, 0, px_yi, px_xi].item()
            marker = "✓ ROAD" if sdf_val < 0 else "✗ OFF-ROAD"
            print(f"  t={t}: pixel=({px_xi},{px_yi}) SDF={sdf_val:+.3f}m {marker}")
    
    # === Visualization: Save debug plot ===
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    # Plot 1: Raster map channel 0
    ax = axes[0]
    ax.imshow(batch.maps[0, 0].numpy(), cmap='gray', origin='upper')
    ax.set_title(f"Raster Map Ch0\n(bright=drivable?)")
    ax.plot(origin_px_x, origin_px_y, 'r*', markersize=15, label='Agent Origin')
    # Plot GT with y-flip
    for t in range(len(gt_traj)):
        if np.isnan(gt_traj[t]).any(): break
        px_x = gt_traj[t, 0] * px_per_m + origin_px_x
        px_y = -gt_traj[t, 1] * px_per_m + origin_px_y
        ax.plot(px_x, px_y, 'g.', markersize=4)
    ax.legend(fontsize=8)
    
    # Plot 2: SDF field
    ax = axes[1]
    sdf_img = sdf_field_m[0, 0].numpy()
    im = ax.imshow(sdf_img, cmap='RdBu_r', vmin=-5, vmax=5, origin='upper')
    ax.set_title("SDF (blue=road, red=off-road)")
    ax.plot(origin_px_x, origin_px_y, 'k*', markersize=15)
    for t in range(len(gt_traj)):
        if np.isnan(gt_traj[t]).any(): break
        px_x = gt_traj[t, 0] * px_per_m + origin_px_x
        px_y = -gt_traj[t, 1] * px_per_m + origin_px_y
        ax.plot(px_x, px_y, 'k.', markersize=4)
    plt.colorbar(im, ax=ax)
    
    # Plot 3: SDF with NO y-flip
    ax = axes[2]
    ax.imshow(sdf_img, cmap='RdBu_r', vmin=-5, vmax=5, origin='upper')
    ax.set_title("SDF + GT (NO y-flip)")
    ax.plot(origin_px_x, origin_px_y, 'k*', markersize=15)
    for t in range(len(gt_traj)):
        if np.isnan(gt_traj[t]).any(): break
        px_x = gt_traj[t, 0] * px_per_m + origin_px_x
        px_y = gt_traj[t, 1] * px_per_m + origin_px_y  # no flip
        ax.plot(px_x, px_y, 'k.', markersize=4)
    
    plt.tight_layout()
    save_path = "results/debug_sdf_coords.png"
    os.makedirs("results", exist_ok=True)
    plt.savefig(save_path, dpi=150)
    print(f"\nSaved debug plot to {save_path}")

if __name__ == "__main__":
    main()
