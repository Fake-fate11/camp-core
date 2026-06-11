import argparse
import json
import os
import pickle
from typing import Dict, List, Tuple

import numpy as np


def parse_pred_arg(text: str) -> Tuple[str, str]:
    if "=" not in text:
        raise argparse.ArgumentTypeError(
            f"Invalid --pred '{text}'. Expected format label=path."
        )
    label, path = text.split("=", 1)
    label = label.strip()
    path = path.strip()
    if not label or not path:
        raise argparse.ArgumentTypeError(
            f"Invalid --pred '{text}'. Expected non-empty label and path."
        )
    return label, path


def load_preds(pred_args: List[Tuple[str, str]]) -> Dict[str, Dict[str, int]]:
    preds = {}
    for label, path in pred_args:
        if not os.path.exists(path):
            print(f"[warn] Missing prediction file for {label}: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        preds[label] = {str(k): int(v) for k, v in payload.items()}
    return preds


def angle_wrap(angle: float) -> float:
    return float((angle + np.pi) % (2 * np.pi) - np.pi)


def valid_xy(traj: np.ndarray) -> np.ndarray:
    traj = np.asarray(traj, dtype=np.float32)
    if traj.ndim != 2 or traj.shape[1] < 2:
        return np.zeros((0, 2), dtype=np.float32)
    traj = traj[:, :2]
    return traj[~np.isnan(traj).any(axis=1)]


def compute_ade(pred: np.ndarray, gt: np.ndarray) -> float:
    pred = valid_xy(pred)
    gt = valid_xy(gt)
    n = min(len(pred), len(gt))
    if n == 0:
        return float("inf")
    return float(np.mean(np.linalg.norm(pred[:n] - gt[:n], axis=-1)))


def trajectory_shape_features(gt: np.ndarray) -> Dict[str, float]:
    gt = valid_xy(gt)
    if len(gt) < 4:
        return {
            "progress": 0.0,
            "path_length": 0.0,
            "turn_angle": 0.0,
            "lateral_deviation": 0.0,
        }

    diffs = np.diff(gt, axis=0)
    step_lens = np.linalg.norm(diffs, axis=1)
    path_length = float(np.sum(step_lens))
    progress = float(np.linalg.norm(gt[-1] - gt[0]))

    nonzero = np.where(step_lens > 1e-3)[0]
    if len(nonzero) >= 2:
        h0 = float(np.arctan2(diffs[nonzero[0], 1], diffs[nonzero[0], 0]))
        h1 = float(np.arctan2(diffs[nonzero[-1], 1], diffs[nonzero[-1], 0]))
        turn_angle = abs(angle_wrap(h1 - h0))
        start_vec = diffs[nonzero[0]]
    else:
        turn_angle = 0.0
        start_vec = gt[-1] - gt[0]

    start_norm = float(np.linalg.norm(start_vec))
    if start_norm > 1e-6:
        rel_end = gt[-1] - gt[0]
        lateral_deviation = float(abs(np.cross(start_vec, rel_end)) / start_norm)
    else:
        lateral_deviation = 0.0

    return {
        "progress": progress,
        "path_length": path_length,
        "turn_angle": float(turn_angle),
        "lateral_deviation": lateral_deviation,
    }


def candidate_diversity_features(cands: np.ndarray) -> Dict[str, float]:
    cands = np.asarray(cands, dtype=np.float32)
    if cands.ndim != 3 or cands.shape[0] == 0:
        return {"endpoint_spread": 0.0, "angle_spread": 0.0}

    endpoints = cands[:, -1, :2]
    endpoints = endpoints[~np.isnan(endpoints).any(axis=1)]
    if len(endpoints) < 2:
        return {"endpoint_spread": 0.0, "angle_spread": 0.0}

    center = np.mean(endpoints, axis=0)
    endpoint_spread = float(np.percentile(np.linalg.norm(endpoints - center, axis=1), 90))

    angles = np.arctan2(endpoints[:, 1], endpoints[:, 0])
    # Circular-ish robust spread for local-frame candidate endpoint headings.
    angles_sorted = np.sort(angles)
    angle_span = float(min(2 * np.pi, angles_sorted[-1] - angles_sorted[0]))
    return {"endpoint_spread": endpoint_spread, "angle_spread": angle_span}


def selected_index(label: str, idx: int, sc: dict, preds: Dict[str, Dict[str, int]]) -> int:
    key = f"sc_{idx}"
    if label == "top1":
        return 0
    if label == "oracle":
        cands = sc["candidates"]
        gt = sc["gt_traj"]
        return int(np.argmin([compute_ade(c, gt) for c in cands]))
    if label in preds:
        return int(preds[label].get(key, 0))
    return 0


def selection_summary(
    idx: int,
    sc: dict,
    preds: Dict[str, Dict[str, int]],
    scales: np.ndarray,
    atom_clip: float,
) -> Dict[str, dict]:
    atoms = np.asarray(sc["atoms"], dtype=np.float32) / scales
    atoms_clip = np.clip(np.nan_to_num(atoms, nan=0.0, posinf=atom_clip, neginf=0.0), 0.0, atom_clip)
    feas = np.asarray(sc["feas_mask"], dtype=bool)
    labels = ["top1", "camp", "static", "reranker", "oracle"]
    out = {}
    for label in labels:
        sel = selected_index(label, idx, sc, preds)
        sel = int(np.clip(sel, 0, len(atoms_clip) - 1))
        safe_cost = float(0.1 * np.sum(atoms_clip[sel, 4:9]))
        out[label] = {
            "selected_idx": sel,
            "feasible": bool(feas[sel]) if sel < len(feas) else False,
            "ade": compute_ade(sc["candidates"][sel], sc["gt_traj"]),
            "safe_cost": safe_cost,
            "lane_atom": float(atoms_clip[sel, 7]) if atoms_clip.shape[1] > 7 else 0.0,
            "clearance_atom": float(atoms_clip[sel, 8]) if atoms_clip.shape[1] > 8 else 0.0,
        }
    return out


def parse_args():
    parser = argparse.ArgumentParser(
        description="Select representative qualitative visualization cases from a CAMP eval cache."
    )
    parser.add_argument("--cache_path", required=True)
    parser.add_argument("--atom_scales_path", required=True)
    parser.add_argument("--output_path", default="results/qualitative_cases.json")
    parser.add_argument("--per_category", type=int, default=4)
    parser.add_argument("--atom_clip", type=float, default=10.0)
    parser.add_argument("--min_progress", type=float, default=6.0)
    parser.add_argument("--pred", action="append", default=[], type=parse_pred_arg)
    parser.add_argument(
        "--allow_duplicates",
        action="store_true",
        help="Allow the same cache index to appear in multiple categories.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)
    with open(args.atom_scales_path, "r", encoding="utf-8") as f:
        scales = np.asarray(json.load(f), dtype=np.float32)

    preds = load_preds(args.pred)
    categories: Dict[str, List[Tuple[float, dict]]] = {
        "straight": [],
        "curve": [],
        "obstacle": [],
        "intersection_like": [],
        "no_feasible_floor": [],
        "camp_improves_top1": [],
    }

    for idx, sc in enumerate(scenarios):
        cands = np.asarray(sc["candidates"], dtype=np.float32)
        atoms = np.asarray(sc["atoms"], dtype=np.float32) / scales
        atoms_clip = np.clip(np.nan_to_num(atoms, nan=0.0, posinf=args.atom_clip, neginf=0.0), 0.0, args.atom_clip)
        feas = np.asarray(sc["feas_mask"], dtype=bool)

        shape = trajectory_shape_features(sc["gt_traj"])
        diversity = candidate_diversity_features(cands)
        selected = selection_summary(idx, sc, preds, scales, args.atom_clip)

        feasible_count = int(np.sum(feas))
        max_clearance = float(np.max(atoms_clip[:, 8])) if atoms_clip.shape[1] > 8 else 0.0
        p90_clearance = float(np.percentile(atoms_clip[:, 8], 90)) if atoms_clip.shape[1] > 8 else 0.0
        top1 = selected["top1"]
        camp = selected["camp"]

        item = {
            "cache_idx": int(idx),
            # Eval cache is built with shuffle=False. With batch_size=1 visualization,
            # this normally maps directly to the unshuffled dataloader index.
            "scene_idx": int(idx),
            "agent_idx": 0,
            "scene_id": str(sc.get("scene_id", "")),
            "map_source": str(sc.get("map_source", "")),
            "features": {
                **shape,
                **diversity,
                "feasible_count": feasible_count,
                "num_candidates": int(len(cands)),
                "max_clearance_atom": max_clearance,
                "p90_clearance_atom": p90_clearance,
            },
            "selected": selected,
        }

        progress = shape["progress"]
        turn = shape["turn_angle"]
        lateral = shape["lateral_deviation"]
        endpoint_spread = diversity["endpoint_spread"]
        angle_spread = diversity["angle_spread"]

        if progress >= args.min_progress and turn < 0.25 and lateral < 1.5:
            score = progress - 2.0 * lateral - 5.0 * turn
            categories["straight"].append((score, item))

        if progress >= args.min_progress and (turn > 0.65 or lateral > 4.0):
            score = 8.0 * turn + lateral + 0.1 * endpoint_spread
            categories["curve"].append((score, item))

        if max_clearance > 0.2 or p90_clearance > 0.05:
            score = max_clearance + p90_clearance + max(0.0, top1["clearance_atom"] - camp["clearance_atom"])
            categories["obstacle"].append((score, item))

        if endpoint_spread > 4.0 and angle_spread > 0.7:
            score = endpoint_spread + 5.0 * angle_spread + 2.0 * turn
            categories["intersection_like"].append((score, item))

        if feasible_count == 0:
            score = max_clearance + endpoint_spread + turn
            categories["no_feasible_floor"].append((score, item))

        if (not top1["feasible"] and camp["feasible"]) or (top1["safe_cost"] - camp["safe_cost"] > 0.3):
            score = (top1["safe_cost"] - camp["safe_cost"]) + (1.0 if camp["feasible"] else 0.0)
            categories["camp_improves_top1"].append((score, item))

    selected_by_category = {}
    flat_targets = []
    used = set()
    for category, scored_items in categories.items():
        scored_items.sort(key=lambda pair: pair[0], reverse=True)
        chosen = []
        for score, item in scored_items:
            if not args.allow_duplicates and item["cache_idx"] in used:
                continue
            item_out = dict(item)
            item_out["category"] = category
            item_out["score"] = float(score)
            chosen.append(item_out)
            flat_targets.append(
                {
                    "category": category,
                    "rank": len(chosen),
                    "scene_idx": item_out["scene_idx"],
                    "agent_idx": item_out["agent_idx"],
                    "cache_idx": item_out["cache_idx"],
                    "scene_id": item_out["scene_id"],
                    "score": float(score),
                }
            )
            used.add(item["cache_idx"])
            if len(chosen) >= args.per_category:
                break
        selected_by_category[category] = chosen

    output = {
        "cache_path": args.cache_path,
        "atom_scales_path": args.atom_scales_path,
        "num_scenarios": len(scenarios),
        "per_category": args.per_category,
        "categories": selected_by_category,
        "targets": flat_targets,
        "notes": [
            "scene_idx is set to cache_idx for direct use with compare_finetune_vis.py on an unshuffled eval dataloader.",
            "intersection_like is a proxy based on candidate endpoint and heading diversity, not a nuScenes map semantic label.",
        ],
    }

    out_dir = os.path.dirname(args.output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved qualitative case list to {args.output_path}")
    for category, items in selected_by_category.items():
        print(f"\n[{category}]")
        for rank, item in enumerate(items, start=1):
            feat = item["features"]
            camp = item["selected"]["camp"]
            top1 = item["selected"]["top1"]
            print(
                f"  {rank:2d}. cache_idx={item['cache_idx']} score={item['score']:.3f} "
                f"progress={feat['progress']:.2f} turn={feat['turn_angle']:.2f} "
                f"feasible={feat['feasible_count']}/{feat['num_candidates']} "
                f"top1_safe={top1['safe_cost']:.2f} camp_safe={camp['safe_cost']:.2f}"
            )


if __name__ == "__main__":
    main()
