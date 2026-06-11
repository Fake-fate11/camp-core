import argparse
import os
import sys
from pathlib import Path

import numpy as np
from tqdm import tqdm

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.atoms.driver_atoms import compute_atom_bank_vector
from camp_core.data_interfaces.nuscenes_trajdata_bridge import (
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
    _radius_lookup,
    default_nuscenes_attention_radius,
    extract_driver_context,
)


def parse_thresholds(text):
    return [float(x.strip()) for x in text.split(",") if x.strip()]


def min_distance_series(ctx, traj_xy: np.ndarray) -> np.ndarray:
    traj_xy = np.asarray(traj_xy, dtype=float)
    per_t = np.full(traj_xy.shape[0], np.inf, dtype=float)

    if ctx.dynamic_obstacles:
        for obs_traj in ctx.dynamic_obstacles.values():
            obs_traj = np.asarray(obs_traj, dtype=float)
            length = min(len(traj_xy), len(obs_traj))
            if length <= 0:
                continue
            dist = np.linalg.norm(traj_xy[:length] - obs_traj[:length, :2], axis=1)
            per_t[:length] = np.minimum(per_t[:length], dist)

    if ctx.static_obstacles is not None and len(ctx.static_obstacles) > 0:
        obs_xy = np.asarray(ctx.static_obstacles, dtype=float)[:, :2]
        for t, ego_p in enumerate(traj_xy):
            per_t[t] = min(per_t[t], np.linalg.norm(obs_xy - ego_p, axis=1).min())

    return per_t


def soft_clearance_cost(min_dists: np.ndarray, threshold: float, dt: float) -> float:
    finite = min_dists[np.isfinite(min_dists)]
    if finite.size == 0:
        return 0.0
    intrusion = np.maximum(0.0, float(threshold) - finite)
    return float(dt) * float(np.sum(intrusion**2))


def pct(values: np.ndarray, q: float) -> float:
    return float(np.nanpercentile(values, q)) if values.size else float("nan")


def probe_scene_index(dataset, num_items: int = 32) -> None:
    try:
        from trajdata.caching import EnvCache
        from trajdata.data_structures.scene import SceneTimeAgent
        from trajdata.utils import scene_utils
    except Exception as exc:
        print(f"Scene index probe unavailable: {exc}")
        return

    presence_counts = []
    manual_neighbor_counts = []
    examples = []
    radius_map = getattr(dataset, "agent_interaction_distances", None)
    if radius_map is None:
        radius_map = default_nuscenes_attention_radius()

    for data_i in range(min(num_items, len(dataset))):
        try:
            scene_path, agent_id, ts = dataset._data_index[data_i]
            scene = EnvCache.load(scene_path)
            scene_utils.enforce_desired_dt(scene, getattr(dataset, "desired_dt", None))
            scene_cache = dataset.cache_class(
                dataset.cache_path,
                scene,
                getattr(dataset, "augmentations", None),
            )
            scene_cache.set_obs_format(getattr(dataset, "obs_format", "x,y,xd,yd,xdd,ydd,s,c"))
            scene_time_agent = SceneTimeAgent.from_cache(
                scene,
                ts,
                agent_id,
                scene_cache,
                only_types=getattr(dataset, "only_types", None),
                no_types=getattr(dataset, "no_types", None),
                incl_robot_future=getattr(dataset, "incl_robot_future", False),
            )
            if scene_time_agent.agent is None:
                continue

            agents = scene_time_agent.agents
            dists = scene_time_agent.get_agent_distances_to(scene_time_agent.agent)
            near_count = 0
            nearest = []
            for agent, dist in zip(agents, dists):
                if agent.name == scene_time_agent.agent.name or not np.isfinite(dist):
                    continue
                radius = _radius_lookup(radius_map, agent.type, scene_time_agent.agent.type)
                if float(dist) <= radius:
                    near_count += 1
                nearest.append(float(dist))

            presence_counts.append(len(agents))
            manual_neighbor_counts.append(near_count)
            if len(examples) < 3:
                nearest = sorted(nearest)[:5]
                examples.append(
                    f"scene={scene.name}, ts={ts}, agent={agent_id}, "
                    f"presence={len(agents)}, near={near_count}, nearest={np.round(nearest, 2).tolist()}"
                )
        except Exception as exc:
            if len(examples) < 3:
                examples.append(f"probe error at data_i={data_i}: {exc}")

    pres = np.asarray(presence_counts, dtype=float)
    near = np.asarray(manual_neighbor_counts, dtype=float)
    print(
        "Scene index probe presence: "
        f"P50={pct(pres, 50):.1f}, P90={pct(pres, 90):.1f}, Max={np.nanmax(pres) if pres.size else 0:.0f}"
    )
    print(
        "Scene index probe manual neighbors: "
        f">0={int(np.sum(near > 0))}/{len(near)}, "
        f"P50={pct(near, 50):.1f}, P90={pct(near, 90):.1f}, Max={np.nanmax(near) if near.size else 0:.0f}"
    )
    for ex in examples:
        print(f"  Probe example: {ex}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Debug why clearance atoms do or do not trigger.")
    parser.add_argument("--data_root", type=str, default="/root/autodl-tmp/dataset")
    parser.add_argument("--cache_dir", type=str, default="/root/autodl-tmp/.unified_data_cache")
    parser.add_argument("--split", type=str, default="nusc_trainval-train")
    parser.add_argument("--num_samples", type=int, default=2000)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--num_workers", type=int, default=0)
    parser.add_argument("--rebuild_cache", action="store_true")
    parser.add_argument(
        "--thresholds",
        type=parse_thresholds,
        default=parse_thresholds("1,2,3,5"),
        help="comma-separated center-distance thresholds in meters",
    )
    args = parser.parse_args()

    cfg = NuscenesDatasetConfig(
        data_root=args.data_root,
        cache_dir=args.cache_dir,
        split=args.split,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        shuffle=False,
        use_vector_map=True,
        rebuild_cache=args.rebuild_cache,
    )
    bridge = NuscenesTrajdataBridge(cfg)
    loader = bridge.get_dataloader()
    probe_scene_index(bridge.dataset)

    total = 0
    with_dynamic = 0
    raw_with_neighbors = 0
    raw_with_neighbor_future = 0
    map_source_counts = {}
    raw_neighbor_counts = []
    dyn_counts = []
    min_dists = []
    current_atom_values = []
    threshold_hits = {thr: 0 for thr in args.thresholds}
    threshold_cost_pos = {thr: 0 for thr in args.thresholds}

    pbar = tqdm(total=args.num_samples if args.num_samples > 0 else None)
    for batch in loader:
        batch_size = len(batch.agent_name)
        for i in range(batch_size):
            if args.num_samples > 0 and total >= args.num_samples:
                break

            fut = batch.agent_fut[i].cpu().numpy()
            fut_xy = fut[:, :2]
            fut_xy = fut_xy[~np.isnan(fut_xy).any(axis=1)]
            if len(fut_xy) < 2:
                continue

            raw_n = int(batch.num_neigh[i]) if hasattr(batch, "num_neigh") else 0
            raw_neighbor_counts.append(raw_n)
            if raw_n > 0:
                raw_with_neighbors += 1
                if hasattr(batch, "neigh_fut_len") and batch.neigh_fut_len is not None:
                    fut_lens = batch.neigh_fut_len[i][:raw_n]
                    if hasattr(fut_lens, "detach"):
                        fut_lens_np = fut_lens.detach().cpu().numpy()
                    else:
                        fut_lens_np = np.asarray(fut_lens)
                    if fut_lens_np.size > 0 and np.nanmax(fut_lens_np) > 0:
                        raw_with_neighbor_future += 1

            gt_traj = np.concatenate([np.zeros((1, 2), dtype=float), fut_xy], axis=0)
            ctx = extract_driver_context(batch, i, map_api=bridge.dataset, horizon=len(gt_traj))
            map_source = getattr(ctx, "map_source", "unknown")
            map_source_counts[map_source] = map_source_counts.get(map_source, 0) + 1

            dyn_n = len(ctx.dynamic_obstacles or {})
            dyn_counts.append(dyn_n)
            if dyn_n > 0:
                with_dynamic += 1

            per_t = min_distance_series(ctx, gt_traj)
            finite = per_t[np.isfinite(per_t)]
            min_dist = float(np.min(finite)) if finite.size else float("inf")
            if np.isfinite(min_dist):
                min_dists.append(min_dist)
                for thr in args.thresholds:
                    if min_dist < thr:
                        threshold_hits[thr] += 1
                    if soft_clearance_cost(per_t, thr, ctx.dt) > 1e-6:
                        threshold_cost_pos[thr] += 1

            current_atom = compute_atom_bank_vector(ctx, gt_traj)[-1]
            current_atom_values.append(float(current_atom))

            total += 1
            pbar.update(1)

        if args.num_samples > 0 and total >= args.num_samples:
            break
    pbar.close()

    min_arr = np.asarray(min_dists, dtype=float)
    raw_arr = np.asarray(raw_neighbor_counts, dtype=float)
    dyn_arr = np.asarray(dyn_counts, dtype=float)
    atom_arr = np.asarray(current_atom_values, dtype=float)

    print(f"Total analyzed: {total}")
    print(f"Map source counts: {map_source_counts}")
    print(f"Raw batch num_neigh > 0: {raw_with_neighbors}/{total} ({raw_with_neighbors / max(total, 1):.3f})")
    print(f"Raw batch neigh_fut_len > 0: {raw_with_neighbor_future}/{total} ({raw_with_neighbor_future / max(total, 1):.3f})")
    print(
        "Raw batch num_neigh per scene: "
        f"P50={pct(raw_arr, 50):.1f}, P90={pct(raw_arr, 90):.1f}, Max={np.nanmax(raw_arr) if raw_arr.size else 0:.0f}"
    )
    print(f"Scenes with dynamic obstacles: {with_dynamic}/{total} ({with_dynamic / max(total, 1):.3f})")
    print(
        "Dynamic obstacle count per scene: "
        f"P50={pct(dyn_arr, 50):.1f}, P90={pct(dyn_arr, 90):.1f}, Max={np.nanmax(dyn_arr) if dyn_arr.size else 0:.0f}"
    )

    if min_arr.size:
        print(
            "Min center distance to obstacles (m): "
            f"P01={pct(min_arr, 1):.2f}, P05={pct(min_arr, 5):.2f}, "
            f"P10={pct(min_arr, 10):.2f}, P50={pct(min_arr, 50):.2f}, "
            f"P90={pct(min_arr, 90):.2f}"
        )
    else:
        print("No finite obstacle distances found.")

    for thr in args.thresholds:
        print(
            f"Threshold {thr:.1f}m: min_dist hits={threshold_hits[thr]}/{total}, "
            f"positive soft-cost scenes={threshold_cost_pos[thr]}/{total}"
        )

    positive_atoms = int(np.sum(atom_arr > 1e-6))
    print(f"Current compute_atom_bank_vector clearance > 0: {positive_atoms}/{len(atom_arr)}")
    if atom_arr.size:
        print(
            "Current clearance atom distribution: "
            f"P50={pct(atom_arr, 50):.4f}, P95={pct(atom_arr, 95):.4f}, Max={np.nanmax(atom_arr):.4f}"
        )


if __name__ == "__main__":
    main()
