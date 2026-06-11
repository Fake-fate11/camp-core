import argparse
import json
import os
import glob


def fmt_duration(seconds):
    if seconds is None:
        return "-"
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return "-"
    minutes = seconds / 60.0
    hours = seconds / 3600.0
    if hours >= 1:
        return f"{hours:.2f} h"
    return f"{minutes:.2f} min"


def fmt_ratio(value):
    if value is None:
        return "-"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"{value:.3f}"


def get_report_cvar(metrics):
    return metrics.get(
        "CVaR_0.90_Safety_WeightedClipped",
        metrics.get("CVaR_0.90_Safety", 0),
    )


def infer_run_tags(metric_files):
    tags = set()
    for path in metric_files:
        name = os.path.basename(path)
        if not name.endswith("_metrics.json"):
            continue
        stem = name[: -len("_metrics.json")]
        if stem.startswith("camp_select_it"):
            parts = stem.split("_", 3)
            if len(parts) == 4:
                tags.add(parts[3])
        elif stem.startswith("finetune_safe_e"):
            parts = stem.split("_", 3)
            if len(parts) == 4:
                tags.add(parts[3])
        elif stem.startswith("finetune_camp_select_e"):
            parts = stem.split("_", 4)
            if len(parts) == 5:
                tags.add(parts[4])
    return sorted(tags)


def discover_timing_files(results_dir, metric_files):
    discovered = []
    for tag in infer_run_tags(metric_files):
        discovered.extend(glob.glob(os.path.join(results_dir, f"training_time_compare_*_{tag}.json")))
    if not discovered:
        all_timing = glob.glob(os.path.join(results_dir, "training_time_compare_*.json"))
        if len(all_timing) == 1:
            discovered = all_timing
    return sorted(set(discovered))


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Table 2 Markdown from Evaluation Metrics")
    parser.add_argument("--results_dir", type=str, default="results", help="Directory containing metric JSON files")
    parser.add_argument(
        "--metric_files",
        nargs="*",
        default=None,
        help="Optional explicit metric JSON files to print, avoiding unrelated runs in results_dir",
    )
    parser.add_argument(
        "--timing_compare_files",
        nargs="*",
        default=None,
        help="Optional training_time_compare JSON files to append as a timing table",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    if args.metric_files:
        json_files = [p for p in args.metric_files if os.path.exists(p)]
        missing = [p for p in args.metric_files if not os.path.exists(p)]
        for p in missing:
            print(f"Warning: metric file not found, skipping: {p}")
    else:
        json_files = glob.glob(os.path.join(args.results_dir, "*_metrics.json"))
    
    if not json_files:
        print(f"No metric files found in {args.results_dir}")
        return
        
    print(f"Found {len(json_files)} metric files.")
    
    # Table Header
    print("\n### Table 2: Quantitative Evaluation of Adaptation Methods")
    print("| Method | ADE↓ | FDE↓ | Violation Rate↓ | RMS Accel↓ | RMS Jerk↓ | Safety CVaR (w+clip)↓ |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    # Process files
    for jf in sorted(json_files):
        # Extract method name
        filename = os.path.basename(jf)
        method_name = filename.replace("_metrics.json", "").replace("_", " ").title()
        
        with open(jf, "r") as f:
            metrics = json.load(f)
            
        ade = metrics.get("Mean_ADE", 0)
        fde = metrics.get("Mean_FDE", 0)
        viol = metrics.get("Violation_Rate", 0) * 100 # percentage
        accel = metrics.get("RMS_Accel", 0)
        jerk = metrics.get("RMS_Jerk", 0)
        cvar = get_report_cvar(metrics)
        
        row = f"| **{method_name}** | {ade:.2f} | {fde:.2f} | {viol:.1f}% | {accel:.2f} | {jerk:.2f} | {cvar:.2f} |"
        print(row)

    timing_files = args.timing_compare_files or discover_timing_files(args.results_dir, json_files)
    timing_files = [p for p in timing_files if os.path.exists(p)]
    if timing_files:
        print("\n### Training Time Comparison")
        print("| Run | CAMP Wall Time | Finetune Wall Time | Parallel Stage Wall Time | CAMP/Finetune | Finetune/CAMP |")
        print("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for tf in timing_files:
            with open(tf, "r") as f:
                timing = json.load(f)

            run_name = timing.get("run_tag") or os.path.basename(tf).replace("training_time_compare_", "").replace(".json", "")
            camp_s = timing.get("camp_train_wall_time_s")
            ft_s = timing.get("finetune_train_wall_time_s")
            stage_s = timing.get("parallel_train_stage_wall_time_s")
            ratio = timing.get("camp_vs_finetune_ratio")
            inv_ratio = None
            try:
                if ratio is not None and float(ratio) > 0:
                    inv_ratio = 1.0 / float(ratio)
            except (TypeError, ValueError):
                inv_ratio = None

            print(
                f"| **{run_name}** | {fmt_duration(camp_s)} | {fmt_duration(ft_s)} | "
                f"{fmt_duration(stage_s)} | {fmt_ratio(ratio)} | {fmt_ratio(inv_ratio)} |"
            )
        
if __name__ == "__main__":
    main()
