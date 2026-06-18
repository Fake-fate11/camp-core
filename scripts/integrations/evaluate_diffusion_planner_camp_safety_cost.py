#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import CAMPSelector  # noqa: E402
from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    DEFAULT_REQUIRED_BUCKETS,
    FORMAL_SEEDS,
    _aggregate,
    _coverage_gaps,
    _fmt,
    _log_context,
    _opportunity_gate,
    _record_row,
    _record_summary,
    _records_by_bucket,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
    _mean_ci,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a saved CAMP selector on fixed DP candidate-outcome logs "
            "with the frozen candidate-branch SafetyCost v1 audit."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--atom_scales", type=Path, required=True)
    parser.add_argument("--static_weights", type=Path, required=True)
    parser.add_argument("--selector_name", type=str, default="evaluated_camp")
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--fail_on_formal_seeds",
        action="store_true",
        help="Exit nonzero if any selection log belongs to seeds 11, 12, or 13.",
    )
    parser.add_argument(
        "--required_bucket",
        action="append",
        choices=sorted(SUPPORTED_SCENARIO_BUCKETS - {"overall"}),
        default=None,
        help=(
            "Bucket required for coverage. Repeat to override the default "
            "normal+critical bucket list."
        ),
    )
    parser.add_argument(
        "--fail_on_missing_required",
        action="store_true",
        help="Exit nonzero if any required scenario bucket has zero records.",
    )
    return parser.parse_args()


def analyze(
    paths: list[Path],
    *,
    atom_scales: Path,
    static_weights: Path,
    selector_name: str = "evaluated_camp",
    scenario_bucket_manifest: Path | None = None,
    fail_on_formal_seeds: bool = False,
    required_buckets: tuple[str, ...] = DEFAULT_REQUIRED_BUCKETS,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    selector = CAMPSelector.from_files(
        atom_scales_path=atom_scales,
        static_weights_path=static_weights,
        mode="static",
    )
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    logs: list[dict[str, Any]] = []
    evaluated_rows: list[dict[str, Any]] = []
    logged_rows: list[dict[str, Any]] = []
    selection_pairs: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        formal_seed = context["seed"] in FORMAL_SEEDS
        if formal_seed and fail_on_formal_seeds:
            raise ValueError(f"Formal seed log is forbidden: {log_path}")
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        logs.append(
            {
                "path": str(log_path),
                "run_key": context["run_key"],
                "seed": context["seed"],
                "formal_seed": formal_seed,
                "scenario_buckets": context["scenario_buckets"],
                "records": len(payload),
            }
        )
        for record_index, record in enumerate(payload):
            label = f"{log_path} record {record_index}"
            selected_index, selector_scores, used_fallback = _select_record_index(
                record,
                selector,
                label=label,
            )
            evaluated_record = dict(record)
            evaluated_record["selected_index"] = int(selected_index)
            evaluated_row = _record_row(
                evaluated_record,
                label=label,
                log_path=log_path,
                record_index=record_index,
                context=context,
                formal_seed=formal_seed,
            )
            logged_row = _record_row(
                record,
                label=label,
                log_path=log_path,
                record_index=record_index,
                context=context,
                formal_seed=formal_seed,
            )
            evaluated_row["evaluated_selector_scores"] = selector_scores.tolist()
            evaluated_row["evaluated_selector_used_fallback"] = bool(used_fallback)
            evaluated_rows.append(evaluated_row)
            logged_rows.append(logged_row)
            selection_pairs.append(
                {
                    "log_path": str(log_path),
                    "record_index": int(record_index),
                    "run_key": context["run_key"],
                    "scenario_buckets": context["scenario_buckets"],
                    "logged_index": int(logged_row["camp_index"]),
                    "evaluated_index": int(selected_index),
                    "changed": int(logged_row["camp_index"]) != int(selected_index),
                    "evaluated_minus_logged_cost": (
                        evaluated_row["costs"]["camp"] - logged_row["costs"]["camp"]
                    ),
                    "evaluated_minus_top1": evaluated_row["deltas"]["camp_minus_top1"],
                    "logged_minus_top1": logged_row["deltas"]["camp_minus_top1"],
                    "evaluated_minus_hard_guarded_oracle": evaluated_row["deltas"][
                        "camp_minus_hard_guarded_oracle"
                    ],
                    "logged_minus_hard_guarded_oracle": logged_row["deltas"][
                        "camp_minus_hard_guarded_oracle"
                    ],
                }
            )

    formal_seed_logs = [log["path"] for log in logs if log["formal_seed"]]
    evaluated_by_bucket = _bucket_aggregates(evaluated_rows)
    logged_by_bucket = _bucket_aggregates(logged_rows)
    coverage_gaps = _coverage_gaps(evaluated_rows, required_buckets)
    evaluated_overall = _aggregate(evaluated_rows, seed_key=f"{selector_name}:overall")
    logged_overall = _aggregate(logged_rows, seed_key="logged_camp:overall")
    return {
        "analysis": {
            "name": "dp_camp_candidate_branch_safety_cost_v1_selector_eval",
            "role": (
                "offline held-out candidate-branch evaluation for a saved CAMP "
                "selector over fixed DP candidate pools"
            ),
            "training": False,
            "online_selector_change": False,
            "selector_name": selector_name,
            "selector_artifacts": {
                "atom_scales": str(atom_scales),
                "static_weights": str(static_weights),
            },
            "selector_mode": "static",
            "safety_cost_scope": (
                "candidate branch proxy, not full closed-loop run-level "
                "SafetyCost v1"
            ),
            "future_outcome_leakage": (
                "candidate_closed_loop_outcomes are used only for offline "
                "evaluation labels; selector scores use current-tick atoms and "
                "saved simplex weights"
            ),
            "math_boundary": (
                "This evaluation does not change DP, candidate generation, CAMP "
                "atoms, affine score semantics, or the simplex/CVaR/L2 master. "
                "It is not a Benders subproblem and is not a closed-loop proof."
            ),
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "formal_seed_policy": (
                "forbidden" if fail_on_formal_seeds else "reported_only"
            ),
            "formal_seed_logs": formal_seed_logs,
            "required_buckets": list(required_buckets),
        },
        "logs": {
            "total": len(logs),
            "formal_seed_logs": len(formal_seed_logs),
            "items": logs,
        },
        "records": _record_summary(evaluated_rows),
        "evaluated_selector": {
            "overall": evaluated_overall,
            "by_bucket": evaluated_by_bucket,
        },
        "logged_selector": {
            "overall": logged_overall,
            "by_bucket": logged_by_bucket,
        },
        "selector_comparison": _selector_comparison(selection_pairs),
        "coverage_gaps": coverage_gaps,
        "opportunity_gate": _opportunity_gate(
            evaluated_overall,
            evaluated_by_bucket,
            coverage_gaps,
            formal_seed_logs=formal_seed_logs,
            required_buckets=required_buckets,
        ),
    }


def _select_record_index(
    record: dict[str, Any],
    selector: CAMPSelector,
    *,
    label: str,
) -> tuple[int, np.ndarray, bool]:
    atoms = np.asarray(record.get("atoms"), dtype=np.float64)
    if atoms.ndim != 2 or atoms.shape[1] != selector.num_atoms:
        raise ValueError(
            f"{label} atoms must have shape [K,{selector.num_atoms}], got "
            f"{atoms.shape}."
        )
    feasible = np.asarray(record.get("feasible_mask"), dtype=bool).reshape(-1)
    if feasible.shape != (atoms.shape[0],):
        raise ValueError(f"{label} feasible_mask must match candidate count.")

    normalized = atoms / selector.atom_scales.reshape(1, -1)
    positive_inf = (
        selector.atom_clip if selector.atom_clip > 0 else np.finfo(np.float64).max
    )
    normalized = np.nan_to_num(
        normalized,
        nan=0.0,
        posinf=positive_inf,
        neginf=0.0,
    )
    normalized = np.maximum(normalized, 0.0)
    if selector.atom_clip > 0:
        normalized = np.clip(normalized, 0.0, selector.atom_clip)

    weights = selector.weights_for()
    scores = normalized @ weights
    used_fallback = not bool(feasible.any())
    if used_fallback:
        if selector.fallback_mode == "learned" and selector.fallback_static_weights is not None:
            fallback_normalized = atoms / selector.fallback_atom_scales.reshape(1, -1)
            fallback_normalized = np.nan_to_num(
                fallback_normalized,
                nan=0.0,
                posinf=positive_inf,
                neginf=0.0,
            )
            fallback_normalized = np.maximum(fallback_normalized, 0.0)
            if selector.atom_clip > 0:
                fallback_normalized = np.clip(
                    fallback_normalized,
                    0.0,
                    selector.atom_clip,
                )
            selection_scores = fallback_normalized @ selector.fallback_static_weights
        else:
            selection_scores = normalized @ np.full(
                selector.num_atoms,
                1.0 / selector.num_atoms,
                dtype=np.float64,
            )
    else:
        selection_scores = scores.copy()
        selection_scores[~feasible] = np.inf
    if not np.isfinite(selection_scores).any():
        raise ValueError(f"{label} selector scores contain no finite candidate.")
    return int(np.argmin(selection_scores)), selection_scores, used_fallback


def _bucket_aggregates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "bucket": bucket,
            **_aggregate(bucket_rows, seed_key=f"bucket:{bucket}"),
        }
        for bucket, bucket_rows in _records_by_bucket(rows).items()
    ]


def _selector_comparison(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        grouped[str(pair["log_path"])].append(pair)
    run_level = [
        float(np.mean([pair["evaluated_minus_logged_cost"] for pair in log_pairs]))
        for log_pairs in grouped.values()
    ]
    return {
        "records": len(pairs),
        "logs": len(grouped),
        "changed_record_rate": (
            None
            if not pairs
            else float(np.mean([float(pair["changed"]) for pair in pairs]))
        ),
        "evaluated_minus_logged_cost_mean": (
            None
            if not pairs
            else float(
                np.mean([pair["evaluated_minus_logged_cost"] for pair in pairs])
            )
        ),
        "run_level_evaluated_minus_logged_cost_ci": _mean_ci(
            run_level,
            seed_key="evaluated_minus_logged_cost",
        ),
        "examples": pairs[:20],
        "examples_truncated": len(pairs) > 20,
    }


def render_markdown(report: dict[str, Any]) -> str:
    evaluated = report["evaluated_selector"]["overall"]
    logged = report["logged_selector"]["overall"]
    comparison = report["selector_comparison"]
    evaluated_delta = evaluated["run_level_delta_ci"]
    logged_delta = logged["run_level_delta_ci"]
    lines = [
        "# DP-CAMP Candidate-Branch SafetyCost v1 Selector Evaluation",
        "",
        "This is an offline held-out evaluation over fixed DP candidate pools. "
        "The evaluated selector scores current-tick atoms from the logs with "
        "saved CAMP simplex weights; candidate outcomes are used only for "
        "SafetyCost labels.",
        "",
        f"- Selector: `{report['analysis']['selector_name']}`",
        f"- Logs: `{report['logs']['total']}`",
        f"- Records: `{report['records']['total']}`",
        f"- Formal-seed records: `{report['records']['formal_seed_records']}`",
        "",
        "## Overall",
        "",
        "| Metric | Evaluated selector | Logged selector |",
        "| --- | ---: | ---: |",
        f"| Mean branch cost | {_fmt(evaluated['cost_mean']['camp'])} | {_fmt(logged['cost_mean']['camp'])} |",
        f"| Mean delta vs Top-1 | {_fmt(evaluated_delta['camp_minus_top1']['mean'])} | {_fmt(logged_delta['camp_minus_top1']['mean'])} |",
        f"| Delta-vs-Top-1 CI high | {_fmt(evaluated_delta['camp_minus_top1']['ci95_high'])} | {_fmt(logged_delta['camp_minus_top1']['ci95_high'])} |",
        f"| Mean gap to hard-guarded oracle | {_fmt(evaluated_delta['camp_minus_hard_guarded_oracle']['mean'])} | {_fmt(logged_delta['camp_minus_hard_guarded_oracle']['mean'])} |",
        f"| Gap-to-hard-guarded-oracle CI high | {_fmt(evaluated_delta['camp_minus_hard_guarded_oracle']['ci95_high'])} | {_fmt(logged_delta['camp_minus_hard_guarded_oracle']['ci95_high'])} |",
        f"| Beats Top-1 rate | {_fmt(evaluated['record_rates']['camp_beats_top1'])} | {_fmt(logged['record_rates']['camp_beats_top1'])} |",
        f"| Matches hard-guarded oracle rate | {_fmt(evaluated['record_rates']['camp_matches_hard_guarded_oracle'])} | {_fmt(logged['record_rates']['camp_matches_hard_guarded_oracle'])} |",
        "",
        "## Selector-vs-Logged",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Changed record rate | {_fmt(comparison['changed_record_rate'])} |",
        f"| Mean evaluated-minus-logged cost | {_fmt(comparison['evaluated_minus_logged_cost_mean'])} |",
        f"| Run-level evaluated-minus-logged CI high | {_fmt(comparison['run_level_evaluated_minus_logged_cost_ci']['ci95_high'])} |",
        "",
        "## Scenario Buckets",
        "",
        "| Bucket | Records | Eval delta vs Top-1 | Eval CI high | Logged delta vs Top-1 | Logged CI high |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    logged_by_bucket = {
        row["bucket"]: row for row in report["logged_selector"]["by_bucket"]
    }
    for row in report["evaluated_selector"]["by_bucket"]:
        logged_row = logged_by_bucket.get(row["bucket"])
        row_delta = row["run_level_delta_ci"]["camp_minus_top1"]
        logged_row_delta = (
            {}
            if logged_row is None
            else logged_row["run_level_delta_ci"]["camp_minus_top1"]
        )
        lines.append(
            f"| `{row['bucket']}` | "
            f"{row['records']} | "
            f"{_fmt(row_delta.get('mean'))} | "
            f"{_fmt(row_delta.get('ci95_high'))} | "
            f"{_fmt(logged_row_delta.get('mean'))} | "
            f"{_fmt(logged_row_delta.get('ci95_high'))} |"
        )
    lines.extend(
        [
            "",
            "## Coverage Gate",
            "",
            f"- Missing required buckets: `{', '.join(report['coverage_gaps']['missing_required_buckets']) or 'none'}`",
            f"- Hard-guarded oracle opportunity gate passed: `{report['opportunity_gate']['passed']}`",
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    report = analyze(
        paths,
        atom_scales=args.atom_scales,
        static_weights=args.static_weights,
        selector_name=args.selector_name,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
        required_buckets=(
            tuple(args.required_bucket)
            if args.required_bucket is not None
            else DEFAULT_REQUIRED_BUCKETS
        ),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if args.fail_on_missing_required and report["coverage_gaps"][
        "missing_required_buckets"
    ]:
        missing = ", ".join(report["coverage_gaps"]["missing_required_buckets"])
        raise SystemExit(f"Missing required scenario bucket coverage: {missing}")


if __name__ == "__main__":
    main()
