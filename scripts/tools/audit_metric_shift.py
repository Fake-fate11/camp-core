import argparse
import json
import os
import pickle
from typing import Dict, Iterable, Tuple

import numpy as np


def compute_cvar(costs: np.ndarray, alpha: float = 0.9) -> float:
    costs = np.asarray(costs, dtype=np.float64)
    costs = costs[np.isfinite(costs)]
    if costs.size == 0:
        return float("nan")
    sorted_costs = np.sort(costs)[::-1]
    tail_n = max(1, int((1.0 - alpha) * len(sorted_costs)))
    return float(np.mean(sorted_costs[:tail_n]))


def quantiles(values: np.ndarray) -> Dict[str, float]:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {k: float("nan") for k in ("p50", "p90", "p95", "p99", "max")}
    return {
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
    }


def parse_pred_arg(arg: str) -> Tuple[str, str]:
    if "=" in arg:
        label, path = arg.split("=", 1)
    else:
        path = arg
        label = os.path.basename(path).replace("_preds.json", "")
    return label, path


def load_scales(path: str, num_atoms: int) -> np.ndarray:
    if not path or not os.path.exists(path):
        return np.ones(num_atoms, dtype=np.float32)
    with open(path, "r", encoding="utf-8") as f:
        scales = np.asarray(json.load(f), dtype=np.float32)
    if len(scales) < num_atoms:
        scales = np.concatenate([scales, np.ones(num_atoms - len(scales), dtype=np.float32)])
    return scales[:num_atoms]


def selected_indices(preds: Dict, n: int) -> Iterable[Tuple[int, int]]:
    for i in range(n):
        key = f"sc_{i}"
        if key not in preds:
            continue
        yield i, int(preds[key])


def summarize_prediction(label: str, preds_path: str, scenarios, scales, alpha: float, clip: float) -> Dict:
    with open(preds_path, "r", encoding="utf-8") as f:
        preds = json.load(f)

    selected_feasible = []
    current_cost = []
    clipped_cost = []
    weighted_clipped_cost = []
    no_clearance_cost = []
    clearance_atom = []
    selected_count = 0
    out_of_bounds = 0

    safety_weights = np.zeros(len(scales), dtype=np.float32)
    if len(scales) >= 9:
        safety_weights[4:9] = 0.1
    else:
        safety_weights[:] = 1.0 / max(len(scales), 1)

    for idx, selected_idx in selected_indices(preds, len(scenarios)):
        sc = scenarios[idx]
        atoms = np.asarray(sc["atoms"], dtype=np.float32)
        feas = np.asarray(sc["feas_mask"], dtype=bool)
        if selected_idx < 0 or selected_idx >= len(atoms):
            out_of_bounds += 1
            selected_idx = 0

        atoms_norm = atoms / scales.reshape(1, -1)
        atoms_clip = np.clip(
            np.nan_to_num(atoms_norm, nan=0.0, posinf=clip, neginf=0.0),
            0.0,
            clip,
        )
        a = atoms_norm[selected_idx]
        ac = atoms_clip[selected_idx]

        selected_count += 1
        selected_feasible.append(bool(feas[selected_idx]) if selected_idx < len(feas) else False)

        if len(a) >= 9:
            current_cost.append(float(np.sum(a[4:9])))
            clipped_cost.append(float(np.sum(ac[4:9])))
            weighted_clipped_cost.append(float(np.sum(ac * safety_weights)))
            no_clearance_cost.append(float(np.sum(ac[4:8])))
            clearance_atom.append(float(ac[8]))
        else:
            current_cost.append(float(np.sum(a)))
            clipped_cost.append(float(np.sum(ac)))
            weighted_clipped_cost.append(float(np.sum(ac * safety_weights)))
            no_clearance_cost.append(float(np.sum(ac)))
            clearance_atom.append(float("nan"))

    selected_feasible_arr = np.asarray(selected_feasible, dtype=bool)
    current_cost_arr = np.asarray(current_cost, dtype=np.float64)
    clipped_cost_arr = np.asarray(clipped_cost, dtype=np.float64)
    weighted_arr = np.asarray(weighted_clipped_cost, dtype=np.float64)
    no_clear_arr = np.asarray(no_clearance_cost, dtype=np.float64)
    clearance_arr = np.asarray(clearance_atom, dtype=np.float64)

    return {
        "label": label,
        "preds_path": preds_path,
        "num_predictions": int(selected_count),
        "missing_predictions": int(len(scenarios) - selected_count),
        "out_of_bounds_predictions": int(out_of_bounds),
        "violation_rate_feas_mask": float(1.0 - np.mean(selected_feasible_arr)) if selected_count else float("nan"),
        "cvar_current_unclipped_sum_4_8": compute_cvar(current_cost_arr, alpha=alpha),
        "cvar_clipped_sum_4_8": compute_cvar(clipped_cost_arr, alpha=alpha),
        "cvar_weighted_clipped_0p1_4_8": compute_cvar(weighted_arr, alpha=alpha),
        "cvar_clipped_no_clearance_4_7": compute_cvar(no_clear_arr, alpha=alpha),
        "current_cost_quantiles": quantiles(current_cost_arr),
        "clipped_cost_quantiles": quantiles(clipped_cost_arr),
        "clearance_atom_clipped_quantiles": quantiles(clearance_arr),
    }


def main():
    parser = argparse.ArgumentParser(description="Audit metric shifts across safety-cost definitions.")
    parser.add_argument("--cache_path", required=True)
    parser.add_argument("--atom_scales_path", required=True)
    parser.add_argument("--pred", action="append", default=[], help="Prediction file as label=path or just path. Can repeat.")
    parser.add_argument("--alpha", type=float, default=0.9)
    parser.add_argument("--clip", type=float, default=10.0)
    parser.add_argument("--output_path", default="")
    args = parser.parse_args()

    with open(args.cache_path, "rb") as f:
        scenarios = pickle.load(f)
    if isinstance(scenarios, dict) and "samples" in scenarios:
        scenarios = scenarios["samples"]
    if not scenarios:
        raise ValueError(f"No scenarios found in {args.cache_path}")

    num_atoms = int(np.asarray(scenarios[0]["atoms"]).shape[1])
    scales = load_scales(args.atom_scales_path, num_atoms)

    feas_counts = np.asarray([np.sum(np.asarray(sc["feas_mask"], dtype=bool)) for sc in scenarios], dtype=np.int32)
    pool_summary = {
        "cache_path": args.cache_path,
        "num_scenarios": int(len(scenarios)),
        "num_atoms": int(num_atoms),
        "num_candidates_first": int(np.asarray(scenarios[0]["atoms"]).shape[0]),
        "scene_any_feasible_rate": float(np.mean(feas_counts > 0)),
        "scene_no_feasible_rate": float(np.mean(feas_counts == 0)),
        "feasible_count_p50": float(np.percentile(feas_counts, 50)),
        "feasible_count_p90": float(np.percentile(feas_counts, 90)),
        "feasible_count_max": int(np.max(feas_counts)),
    }

    rows = []
    for pred_arg in args.pred:
        label, path = parse_pred_arg(pred_arg)
        rows.append(summarize_prediction(label, path, scenarios, scales, args.alpha, args.clip))

    result = {"pool": pool_summary, "methods": rows}

    print("\n=== Candidate Pool Summary ===")
    for k, v in pool_summary.items():
        print(f"{k}: {v}")

    if rows:
        print("\n=== Metric Definition Audit ===")
        print(
            "| Method | Viol(feas) | CVaR current | CVaR clipped | "
            "CVaR weighted clipped | CVaR no clearance |"
        )
        print("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for row in rows:
            print(
                f"| {row['label']} | {100.0 * row['violation_rate_feas_mask']:.1f}% | "
                f"{row['cvar_current_unclipped_sum_4_8']:.4f} | "
                f"{row['cvar_clipped_sum_4_8']:.4f} | "
                f"{row['cvar_weighted_clipped_0p1_4_8']:.4f} | "
                f"{row['cvar_clipped_no_clearance_4_7']:.4f} |"
            )

    if args.output_path:
        out_dir = os.path.dirname(args.output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved audit to {args.output_path}")


if __name__ == "__main__":
    main()
