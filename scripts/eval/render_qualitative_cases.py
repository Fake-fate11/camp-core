import argparse
import json
import os
import pickle
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
if not os.environ.get("OMP_NUM_THREADS", "").isdigit() or int(os.environ.get("OMP_NUM_THREADS", "0") or 0) <= 0:
    os.environ["OMP_NUM_THREADS"] = "1"

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import torch
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[2]))

from camp_core.data_interfaces.nuscenes_trajdata_bridge import (  # noqa: E402
    NuscenesDatasetConfig,
    NuscenesTrajdataBridge,
)
from camp_core.base_predictor.trajectron_loader import (  # noqa: E402
    TrajectronLoadConfig,
    build_trajectron_from_checkpoint,
)

import trajdata.visualization.vis as trajdata_vis  # noqa: E402
from trajdata import AgentType  # noqa: E402


COLORS = {
    "gt": "black",
    "top1": "#D55E00",
    "camp": "#5B5FC7",
    "static": "#E69F00",
    "reranker": "#009E73",
    "oracle": "#7A7A7A",
    "finetune_safe": "#CC79A7",
}

MARKERS = {
    "top1": "o",
    "camp": "s",
    "static": "D",
    "reranker": "^",
    "oracle": "X",
    "finetune_safe": "P",
}

ZORDERS = {
    "top1": 7,
    "static": 8,
    "reranker": 9,
    "oracle": 10,
    "camp": 11,
    "finetune_safe": 12,
}


def parse_pred_arg(text: str) -> Tuple[str, str]:
    if "=" not in text:
        raise argparse.ArgumentTypeError(
            f"Invalid --pred '{text}'. Expected format label=path."
        )
    label, path = text.split("=", 1)
    return label.strip(), path.strip()


def load_json_if_exists(path: str) -> dict:
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def valid_xy(traj: np.ndarray) -> np.ndarray:
    traj = np.asarray(traj, dtype=np.float32)
    if traj.ndim != 2 or traj.shape[1] < 2:
        return np.zeros((0, 2), dtype=np.float32)
    traj = traj[:, :2]
    return traj[~np.isnan(traj).any(axis=1)]


def cache_gt_from_batch(batch, batch_idx: int = 0) -> np.ndarray:
    fut = batch.agent_fut[batch_idx].cpu().numpy()
    fut_xy = fut[:11, :2]
    return np.concatenate(([np.zeros(2, dtype=np.float32)], fut_xy), axis=0)


def gt_match_error(a: np.ndarray, b: np.ndarray) -> float:
    a = valid_xy(a)
    b = valid_xy(b)
    n = min(len(a), len(b))
    if n < 3:
        return float("inf")
    return float(np.mean(np.linalg.norm(a[:n] - b[:n], axis=-1)))


def compute_ade(pred: np.ndarray, gt: np.ndarray) -> float:
    pred = valid_xy(pred)
    gt = valid_xy(gt)
    n = min(len(pred), len(gt))
    if n == 0:
        return float("inf")
    return float(np.mean(np.linalg.norm(pred[:n] - gt[:n], axis=-1)))


def selected_index(label: str, cache_idx: int, sc: dict, preds: Dict[str, Dict[str, int]]) -> int:
    if label == "top1":
        return 0
    if label == "oracle":
        return int(np.argmin([compute_ade(c, sc["gt_traj"]) for c in sc["candidates"]]))
    key = f"sc_{cache_idx}"
    if label in preds:
        return int(preds[label].get(key, 0))
    return 0


def resolve_trajectron_epoch(model_dir: str, requested_epoch: int) -> int:
    if requested_epoch > 0:
        return requested_epoch

    epochs = []
    for ckpt in Path(model_dir).glob("model_registrar-*.pt"):
        match = re.search(r"model_registrar-(\d+)\.pt$", ckpt.name)
        if match:
            epochs.append(int(match.group(1)))
    if not epochs:
        raise FileNotFoundError(f"No model_registrar-*.pt found under {model_dir}")
    return max(epochs)


def maybe_load_finetune_model(args, device):
    if not args.finetuned_model_dir:
        return None

    epoch = resolve_trajectron_epoch(args.finetuned_model_dir, args.base_epoch)
    cfg = TrajectronLoadConfig(
        conf_path=args.traj_conf_path or os.path.join(args.finetuned_model_dir, "config.json"),
        model_dir=args.finetuned_model_dir,
        epoch=epoch,
        device=device.type,
    )
    model = build_trajectron_from_checkpoint(cfg)

    ckpt_path = os.path.join(
        args.finetuned_model_dir,
        f"{args.finetuned_prefix}_{args.finetuned_epoch}.pt",
    )
    if not os.path.exists(ckpt_path):
        print(f"[warn] Finetune checkpoint not found, skipping finetune overlay: {ckpt_path}")
        return None

    model.model_registrar.load_state_dict(
        torch.load(ckpt_path, map_location=device, weights_only=False)
    )
    model.to(device)
    model.eval()
    print(f"[render] Loaded finetuned model: {ckpt_path}")
    return model


def predict_finetune_traj(model, batch, device) -> Optional[np.ndarray]:
    if model is None:
        return None
    batch.to(device)
    agent_name = batch.agent_name[0]
    node_type = (
        AgentType(batch.agent_type[0].item())
        if hasattr(batch, "agent_type")
        else "VEHICLE"
    )
    key = f"{str(node_type)}/{agent_name}"
    ph = model.hyperparams.get("prediction_horizon", 12)
    with torch.no_grad():
        pred = model.predict(
            batch,
            prediction_horizon=ph,
            num_samples=1,
            z_mode=False,
            gmm_mode=True,
            output_dists=False,
        )
    if key not in pred:
        return None
    traj = pred[key][0]
    if hasattr(traj, "cpu"):
        traj = traj.cpu().numpy()
    return np.asarray(traj, dtype=np.float32)


def load_case_targets(path: str, candidate_per_category: int) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    targets = []
    categories = payload.get("categories", {})
    if isinstance(categories, dict):
        for category, items in categories.items():
            for rank, item in enumerate(items[:candidate_per_category], start=1):
                targets.append(
                    {
                        "category": category,
                        "rank": rank,
                        "cache_idx": int(item["cache_idx"]),
                        "score": float(item.get("score", 0.0)),
                        "features": item.get("features", {}),
                    }
                )
    elif "targets" in payload:
        for item in payload["targets"]:
            targets.append(
                {
                    "category": item.get("category", "case"),
                    "rank": int(item.get("rank", 1)),
                    "cache_idx": int(item.get("cache_idx", item.get("scene_idx"))),
                    "score": float(item.get("score", 0.0)),
                    "features": item.get("features", {}),
                }
            )

    if not targets:
        raise ValueError(f"No targets found in {path}")
    return targets


def plot_case(
    args,
    target: dict,
    sc: dict,
    batch,
    match_idx: int,
    preds: Dict[str, Dict[str, int]],
    finetune_model,
    device,
):
    category = target["category"]
    cache_idx = target["cache_idx"]
    rank = target["rank"]
    features = target.get("features", {})

    fig, ax = plt.subplots(figsize=(10, 10), dpi=args.dpi)
    try:
        trajdata_vis.plot_agent_batch(batch, batch_idx=0, ax=ax, show=False, close=False)
    except Exception as exc:
        print(f"[warn] Failed to draw trajdata map for cache_idx={cache_idx}: {exc}")

    cands = np.asarray(sc["candidates"], dtype=np.float32)
    gt = np.asarray(sc["gt_traj"], dtype=np.float32)
    if args.draw_candidates:
        for cand in cands:
            cand_xy = valid_xy(cand)
            if len(cand_xy) > 1:
                ax.plot(
                    cand_xy[:, 0],
                    cand_xy[:, 1],
                    color="#8F8F8F",
                    linewidth=args.candidate_linewidth,
                    alpha=args.candidate_alpha,
                    zorder=2,
                )

    gt_xy = valid_xy(gt)
    if len(gt_xy) > 1:
        ax.plot(
            gt_xy[:, 0],
            gt_xy[:, 1],
            color=COLORS["gt"],
            linewidth=4.0,
            linestyle="--",
            marker="*",
            markersize=8,
            label="Ground Truth",
            zorder=10,
        )

    method_labels = [m.strip() for m in args.methods.split(",") if m.strip()]
    for label in method_labels:
        idx = selected_index(label, cache_idx, sc, preds)
        if idx < 0 or idx >= len(cands):
            continue
        traj = valid_xy(cands[idx])
        if len(traj) <= 1:
            continue
        line = ax.plot(
            traj[:, 0],
            traj[:, 1],
            color=COLORS.get(label, None),
            linewidth=args.selected_linewidth,
            marker=MARKERS.get(label, "o"),
            markersize=args.selected_markersize,
            markeredgecolor="white",
            markeredgewidth=0.9,
            alpha=0.92,
            label=f"{label}#{idx}",
            zorder=ZORDERS.get(label, 8),
        )[0]
        line.set_path_effects(
            [pe.Stroke(linewidth=args.selected_linewidth + 1.8, foreground="white"), pe.Normal()]
        )
        ax.scatter(
            [traj[-1, 0]],
            [traj[-1, 1]],
            color=COLORS.get(label, None),
            marker=MARKERS.get(label, "o"),
            s=args.endpoint_markersize,
            edgecolors="black",
            linewidths=0.8,
            zorder=ZORDERS.get(label, 8) + 1,
        )

    finetune_traj = predict_finetune_traj(finetune_model, batch, device)
    if finetune_traj is not None:
        ft_xy = valid_xy(finetune_traj)
        line = ax.plot(
            ft_xy[:, 0],
            ft_xy[:, 1],
            color=COLORS["finetune_safe"],
            linewidth=args.selected_linewidth,
            marker=MARKERS["finetune_safe"],
            markersize=args.selected_markersize,
            markeredgecolor="white",
            markeredgewidth=0.9,
            alpha=0.95,
            label=f"finetune_safe_e{args.finetuned_epoch}",
            zorder=ZORDERS["finetune_safe"],
        )[0]
        line.set_path_effects(
            [pe.Stroke(linewidth=args.selected_linewidth + 1.8, foreground="white"), pe.Normal()]
        )
        ax.scatter(
            [ft_xy[-1, 0]],
            [ft_xy[-1, 1]],
            color=COLORS["finetune_safe"],
            marker=MARKERS["finetune_safe"],
            s=args.endpoint_markersize,
            edgecolors="black",
            linewidths=0.8,
            zorder=ZORDERS["finetune_safe"] + 1,
        )

    ax.scatter([0], [0], color="red", s=90, edgecolors="black", label="Ego Start", zorder=12)
    ax.set_aspect("equal", adjustable="box")

    all_xy = [gt_xy]
    all_xy.extend([valid_xy(cands[selected_index(label, cache_idx, sc, preds)]) for label in method_labels])
    if finetune_traj is not None:
        all_xy.append(valid_xy(finetune_traj))
    all_xy = [xy for xy in all_xy if len(xy) > 0]
    if all_xy:
        pts = np.concatenate(all_xy, axis=0)
        xmin, ymin = np.nanmin(pts, axis=0) - args.padding
        xmax, ymax = np.nanmax(pts, axis=0) + args.padding
        ax.set_xlim(float(xmin), float(xmax))
        ax.set_ylim(float(ymin), float(ymax))

    title_bits = [
        f"{category} #{rank}",
        f"cache={cache_idx}",
        f"data={match_idx}",
    ]
    if features:
        title_bits.append(
            f"turn={features.get('turn_angle', 0.0):.2f}, "
            f"feas={features.get('feasible_count', 0)}/{features.get('num_candidates', '?')}"
        )
    ax.set_title(" | ".join(title_bits), fontsize=10)
    ax.legend(loc="upper left", fontsize=8, frameon=True)

    out_dir = os.path.join(args.output_dir, category)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{category}_{rank:02d}_cache_{cache_idx}.png")
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[render] Saved {out_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Render selected qualitative cases on trajdata maps.")
    parser.add_argument("--cases_json", required=True)
    parser.add_argument("--cache_path", required=True)
    parser.add_argument("--data_root", default="/root/autodl-tmp/dataset")
    parser.add_argument("--cache_dir", default="/root/autodl-tmp/.unified_data_cache")
    parser.add_argument("--split", default="nusc_trainval-val")
    parser.add_argument("--output_dir", default="figures/qualitative_cases")
    parser.add_argument("--max_per_category", type=int, default=3)
    parser.add_argument(
        "--candidate_per_category",
        type=int,
        default=10,
        help="Load this many candidate cases per category, then render until --max_per_category matches succeed.",
    )
    parser.add_argument("--match_threshold", type=float, default=0.1)
    parser.add_argument("--padding", type=float, default=8.0)
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--draw_candidates", action="store_true")
    parser.add_argument("--candidate_alpha", type=float, default=0.08)
    parser.add_argument("--candidate_linewidth", type=float, default=0.8)
    parser.add_argument("--selected_linewidth", type=float, default=3.2)
    parser.add_argument("--selected_markersize", type=float, default=4.5)
    parser.add_argument("--endpoint_markersize", type=float, default=95.0)
    parser.add_argument("--methods", default="top1,static,reranker,oracle,camp")
    parser.add_argument("--pred", action="append", default=[], type=parse_pred_arg)

    parser.add_argument("--traj_conf_path", default="")
    parser.add_argument("--finetuned_model_dir", default="")
    parser.add_argument("--base_epoch", type=int, default=20)
    parser.add_argument("--finetuned_epoch", type=int, default=20)
    parser.add_argument("--finetuned_prefix", default="finetuned_safe")
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)

    preds = {}
    for label, path in args.pred:
        preds[label] = {str(k): int(v) for k, v in load_json_if_exists(path).items()}

    targets = load_case_targets(args.cases_json, args.candidate_per_category)
    target_by_cache = {int(t["cache_idx"]): t for t in targets}
    unmatched = set(target_by_cache.keys())
    rendered_by_category = {}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    finetune_model = maybe_load_finetune_model(args, device)

    cfg = NuscenesDatasetConfig(
        data_root=args.data_root,
        cache_dir=args.cache_dir,
        batch_size=1,
        num_workers=0,
        shuffle=False,
        split=args.split,
        use_vector_map=True,
        unified_dataset_kwargs={"history_sec": (2.0, 2.0), "future_sec": (6.0, 6.0)},
    )
    bridge = NuscenesTrajdataBridge(cfg)
    dataloader = bridge.get_dataloader()

    print(f"[render] Matching {len(unmatched)} cache cases against unshuffled {args.split} dataloader...")
    rendered = 0
    for data_idx, batch in enumerate(tqdm(dataloader)):
        if not unmatched:
            break
        batch_gt = cache_gt_from_batch(batch, 0)
        matched_cache_idx = None
        for cache_idx in list(unmatched):
            err = gt_match_error(batch_gt, scenarios[cache_idx]["gt_traj"])
            if err <= args.match_threshold:
                matched_cache_idx = cache_idx
                break

        if matched_cache_idx is None:
            continue

        target = target_by_cache[matched_cache_idx]
        category = target["category"]
        if rendered_by_category.get(category, 0) >= args.max_per_category:
            unmatched.remove(matched_cache_idx)
            continue

        target = dict(target)
        target["rank"] = rendered_by_category.get(category, 0) + 1
        plot_case(
            args=args,
            target=target,
            sc=scenarios[matched_cache_idx],
            batch=batch,
            match_idx=data_idx,
            preds=preds,
            finetune_model=finetune_model,
            device=device,
        )
        unmatched.remove(matched_cache_idx)
        rendered_by_category[category] = rendered_by_category.get(category, 0) + 1
        rendered += 1

    if unmatched:
        unresolved = [
            idx
            for idx in sorted(unmatched)
            if rendered_by_category.get(target_by_cache[idx]["category"], 0) < args.max_per_category
        ]
        if unresolved:
            print(f"[warn] Unmatched cache indices still needed for quota: {unresolved}")
    print(f"[render] Rendered by category: {rendered_by_category}")
    print(f"[render] Done. Rendered {rendered}/{len(targets)} cases into {args.output_dir}")


if __name__ == "__main__":
    main()
