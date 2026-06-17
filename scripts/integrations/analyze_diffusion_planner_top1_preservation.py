#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
    parse_selection_log_metadata,
)
from scripts.integrations.analyze_diffusion_planner_candidate_availability import (  # noqa: E402
    PROGRESS_BUDGETS_M,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    SUPPORTED_SCENARIO_BUCKETS,
    _load_scenario_bucket_manifest,
    _run_key,
    _scenario_buckets,
)


BOOL_OUTCOMES = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
TOL = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Top-1 preservation attribution for fixed DP candidate "
            "pools. Candidate outcomes are offline labels only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument(
        "--progress_budget_m",
        type=float,
        action="append",
        default=[],
        help="Repeat to override default budgets 0, 0.05, 0.10, 0.25.",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--max_examples", type=int, default=20)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    budgets = (
        tuple(args.progress_budget_m)
        if args.progress_budget_m
        else PROGRESS_BUDGETS_M
    )
    report = analyze(
        paths,
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        progress_budgets_m=budgets,
        label=args.label,
        max_examples=args.max_examples,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(
    paths: list[Path],
    *,
    scenario_bucket_manifest: Path | None = None,
    progress_budgets_m: tuple[float, ...] = PROGRESS_BUDGETS_M,
    label: str | None = None,
    max_examples: int = 20,
) -> dict[str, Any]:
    budgets = tuple(_canonical_budget(value) for value in progress_budgets_m)
    if len(set(budgets)) != len(budgets):
        raise ValueError("Progress budgets must be unique.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)

    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(payload):
            loaded = _load_record(record, f"{log_path} record {record_index}")
            loaded["context"] = context
            loaded["selection_step"] = int(record.get("selection_step", record_index))
            loaded["record_index"] = int(record_index)
            records.append(loaded)

    category_counts = Counter(_preservation_category(record) for record in records)
    active_overrides = [
        record
        for record in records
        if record["feasible"].any()
        and bool(record["feasible"][0])
        and int(record["selected_index"]) != 0
    ]
    by_bucket = _records_by_bucket(records)
    report = {
        "analysis": {
            "name": "dp_camp_top1_preservation_attribution_v1",
            "label": label,
            "role": (
                "offline Top-1 preservation audit for fixed finite DP "
                "candidate sets"
            ),
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are offline labels only",
            "classical_benders_claim": False,
            "scenario_bucket_manifest": (
                None
                if scenario_bucket_manifest is None
                else str(scenario_bucket_manifest)
            ),
            "progress_budgets_m": list(budgets),
            "math_boundary": (
                "DP remains a black-box candidate generator. This report reads "
                "fixed current-tick candidate atoms, feasibility masks, scores, "
                "and offline outcome labels. Atom contribution deltas use the "
                "actual finite-candidate affine selection score and do not make "
                "the DP sampler, tracker, closed-loop simulator, SafetyCost "
                "evaluator, or trajectory coordinates part of a Benders "
                "subproblem."
            ),
        },
        "records": _record_summary(records, category_counts, len(log_paths)),
        "preservation_categories": dict(sorted(category_counts.items())),
        "candidate0_feasible_active_override": _active_override_report(
            active_overrides,
            max_examples=max_examples,
        ),
        "candidate_availability_oracle": [
            _availability_report(records, budget) for budget in budgets
        ],
        "by_bucket": [
            {
                "bucket": bucket,
                "records": _record_summary(
                    bucket_records,
                    Counter(
                        _preservation_category(record) for record in bucket_records
                    ),
                    logs=None,
                ),
                "candidate0_feasible_active_override": _active_override_report(
                    [
                        record
                        for record in bucket_records
                        if record["feasible"].any()
                        and bool(record["feasible"][0])
                        and int(record["selected_index"]) != 0
                    ],
                    max_examples=0,
                ),
                "candidate_availability_oracle": [
                    _availability_report(bucket_records, budget) for budget in budgets
                ],
            }
            for bucket, bucket_records in by_bucket.items()
        ],
    }
    return report


def _log_context(log_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    metadata = parse_selection_log_metadata(log_path)
    validation_summary = _read_json_if_exists(
        log_path.with_name("camp_validation_summary.json")
    )
    benchmark = validation_summary.get("benchmark", {})
    if not isinstance(benchmark, dict):
        benchmark = {}
    route = benchmark.get("route")
    route_name = Path(str(route)).stem if route is not None else metadata.route
    traffic_lights = benchmark.get("traffic_lights")
    if traffic_lights is None:
        traffic_lights = metadata.traffic_light == "on"
    max_npcs = benchmark.get("max_npcs")
    if max_npcs is None:
        max_npcs = metadata.npc_count
    seed = benchmark.get("seed")
    if seed is None:
        seed = metadata.seed
    row = {
        "run_key": _run_key(validation_summary, log_path.parent),
        "route": route,
        "route_name": route_name,
        "seed": seed,
        "max_npcs": max_npcs,
        "traffic_lights": bool(traffic_lights),
        "advance_mode": benchmark.get(
            "advance_mode",
            validation_summary.get("advance_mode"),
        ),
        "log_path": str(log_path),
    }
    return {**row, "scenario_buckets": _scenario_buckets(row, manifest)}


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")

    atom_names = tuple(record.get("atom_names") or ())
    if not atom_names:
        raise ValueError(f"{label} is missing atom_names.")
    atoms = _matrix(record.get("atoms"), candidate_count, len(atom_names), f"{label} atoms")
    normalized_atoms = _matrix(
        record.get("selection_normalized_atoms", record.get("normalized_atoms")),
        candidate_count,
        len(atom_names),
        f"{label} selection_normalized_atoms",
    )
    weights = _finite_vector(
        record.get("selection_weights", record.get("weights")),
        len(atom_names),
        f"{label} selection_weights",
        nonnegative=True,
    )
    scores = _score_vector(
        record.get("selection_scores", record.get("scores")),
        candidate_count,
        f"{label} selection_scores",
    )
    feasible = _bool_vector(
        record.get("feasible_mask"),
        candidate_count,
        f"{label} feasible_mask",
    )
    outcomes = _outcomes(
        record.get("candidate_closed_loop_outcomes"),
        candidate_count,
        label,
    )
    return {
        "candidate_count": candidate_count,
        "selected_index": selected_index,
        "used_fallback": bool(record.get("used_fallback", not feasible.any())),
        "feasible": feasible,
        "atom_names": atom_names,
        "atoms": atoms,
        "normalized_atoms": normalized_atoms,
        "weights": weights,
        "scores": scores,
        "outcomes": outcomes,
        "progress_shortfall": _atom_vector(
            atoms,
            atom_names,
            "progress_shortfall",
            label,
        ),
        "proxy_jerk": _vector(
            record.get("candidate_dp_prior_jerk_excess_cost"),
            candidate_count,
            f"{label} candidate_dp_prior_jerk_excess_cost",
        ),
        "proxy_lateral": _vector(
            record.get("candidate_horizon_lateral_acceleration_cost"),
            candidate_count,
            f"{label} candidate_horizon_lateral_acceleration_cost",
        ),
        "union_red": _vector(
            record.get("candidate_horizon_union_planned_red_light_cost"),
            candidate_count,
            f"{label} candidate_horizon_union_planned_red_light_cost",
        ),
        "red_stopping": _vector(
            record.get("candidate_red_stopping_margin_cost"),
            candidate_count,
            f"{label} candidate_red_stopping_margin_cost",
        ),
    }


def _record_summary(
    records: list[dict[str, Any]],
    category_counts: Counter[str],
    logs: int | None,
) -> dict[str, Any]:
    total = len(records)
    nonfallback = sum(int(record["feasible"].any()) for record in records)
    selected_nonzero = sum(int(int(record["selected_index"]) != 0) for record in records)
    candidate0_feasible = sum(
        int(record["feasible"].any() and bool(record["feasible"][0]))
        for record in records
    )
    active_overrides = int(category_counts.get("candidate0_feasible_selected_nonzero", 0))
    summary = {
        "total": total,
        "nonfallback": nonfallback,
        "fallback": total - nonfallback,
        "selected_candidate0": total - selected_nonzero,
        "selected_nonzero": selected_nonzero,
        "selected_nonzero_rate": selected_nonzero / max(total, 1),
        "candidate0_feasible": candidate0_feasible,
        "candidate0_feasible_rate": candidate0_feasible / max(nonfallback, 1),
        "candidate0_feasible_active_override": active_overrides,
        "candidate0_feasible_active_override_rate": (
            active_overrides / max(candidate0_feasible, 1)
        ),
        "candidate0_infeasible_selected_nonzero": int(
            category_counts.get("candidate0_infeasible_selected_nonzero", 0)
        ),
        "all_infeasible_selected_nonzero": int(
            category_counts.get("all_infeasible_selected_nonzero", 0)
        ),
    }
    if logs is not None:
        summary = {"logs": logs, **summary}
    return summary


def _preservation_category(record: dict[str, Any]) -> str:
    selected = int(record["selected_index"])
    feasible = record["feasible"]
    if not feasible.any():
        return (
            "all_infeasible_selected_candidate0"
            if selected == 0
            else "all_infeasible_selected_nonzero"
        )
    if bool(feasible[0]):
        return (
            "candidate0_feasible_selected_candidate0"
            if selected == 0
            else "candidate0_feasible_selected_nonzero"
        )
    return (
        "candidate0_infeasible_selected_candidate0"
        if selected == 0
        else "candidate0_infeasible_selected_nonzero"
    )


def _active_override_report(
    records: list[dict[str, Any]],
    *,
    max_examples: int,
) -> dict[str, Any]:
    score_deltas: list[float] = []
    residuals: list[float] = []
    outcome_deltas: dict[str, list[float]] = {
        "progress_m": [],
        "mean_jerk_mps3": [],
        "mean_lateral_acceleration_mps2": [],
    }
    bool_worse = Counter()
    bool_better = Counter()
    atom_stats: dict[str, dict[str, Any]] = {}
    examples: list[dict[str, Any]] = []

    for record in records:
        selected = int(record["selected_index"])
        scores = record["scores"]
        score_delta = float(scores[selected] - scores[0])
        contributions = (
            (record["normalized_atoms"][selected] - record["normalized_atoms"][0])
            * record["weights"]
        )
        contribution_sum = float(np.sum(contributions))
        score_deltas.append(score_delta)
        residuals.append(score_delta - contribution_sum)
        for index, name in enumerate(record["atom_names"]):
            stats = atom_stats.setdefault(
                str(name),
                {
                    "contributions": [],
                    "raw_deltas": [],
                    "normalized_deltas": [],
                    "weight": [],
                    "attractive": 0,
                    "repulsive": 0,
                },
            )
            contribution = float(contributions[index])
            stats["contributions"].append(contribution)
            stats["raw_deltas"].append(
                float(record["atoms"][selected, index] - record["atoms"][0, index])
            )
            stats["normalized_deltas"].append(
                float(
                    record["normalized_atoms"][selected, index]
                    - record["normalized_atoms"][0, index]
                )
            )
            stats["weight"].append(float(record["weights"][index]))
            stats["attractive"] += int(contribution < -TOL)
            stats["repulsive"] += int(contribution > TOL)

        for field in outcome_deltas:
            outcome_deltas[field].append(
                _outcome_float(record, selected, field)
                - _outcome_float(record, 0, field)
            )
        for field in BOOL_OUTCOMES:
            selected_value = bool(record["outcomes"][selected].get(field))
            candidate0_value = bool(record["outcomes"][0].get(field))
            bool_worse[field] += int(selected_value and not candidate0_value)
            bool_better[field] += int(candidate0_value and not selected_value)
        if len(examples) < max_examples:
            examples.append(_example_row(record, contributions))

    return {
        "records": len(records),
        "selection_score_delta_selected_minus_candidate0": _stats(score_deltas),
        "score_contribution_residual": _stats(residuals),
        "top_attractive_atoms": _atom_table(atom_stats, attractive=True),
        "top_repulsive_atoms": _atom_table(atom_stats, attractive=False),
        "outcome_delta_selected_minus_candidate0": {
            key: _stats(values) for key, values in outcome_deltas.items()
        },
        "outcome_bool_worse_than_candidate0": dict(sorted(bool_worse.items())),
        "outcome_bool_better_than_candidate0": dict(sorted(bool_better.items())),
        "examples": examples,
    }


def _availability_report(
    records: list[dict[str, Any]],
    budget: float,
) -> dict[str, Any]:
    candidate0_feasible = 0
    active_overrides = 0
    outcome_available = 0
    proxy_available = 0
    hidden_outcome = 0
    proxy_only = 0
    selected_matches_outcome = 0
    selected_matches_proxy = 0
    selected_nonzero_without_outcome = 0
    selected_nonzero_without_proxy = 0
    outcome_available_but_selected_not_matching = 0

    for record in records:
        if not record["feasible"].any() or not bool(record["feasible"][0]):
            continue
        candidate0_feasible += 1
        selected_nonzero = int(record["selected_index"]) != 0
        active_overrides += int(selected_nonzero)
        outcome_mask = _outcome_mask_vs_candidate0(record, budget)
        proxy_mask = _proxy_mask_vs_candidate0(record, budget)
        outcome_has = bool(outcome_mask.any())
        proxy_has = bool(proxy_mask.any())
        selected_in_outcome = bool(outcome_mask[int(record["selected_index"])])
        selected_in_proxy = bool(proxy_mask[int(record["selected_index"])])
        outcome_available += int(outcome_has)
        proxy_available += int(proxy_has)
        hidden_outcome += int(outcome_has and not proxy_has)
        proxy_only += int(proxy_has and not outcome_has)
        selected_matches_outcome += int(selected_in_outcome)
        selected_matches_proxy += int(selected_in_proxy)
        selected_nonzero_without_outcome += int(selected_nonzero and not outcome_has)
        selected_nonzero_without_proxy += int(selected_nonzero and not proxy_has)
        outcome_available_but_selected_not_matching += int(
            outcome_has and selected_nonzero and not selected_in_outcome
        )

    denom = max(candidate0_feasible, 1)
    override_denom = max(active_overrides, 1)
    return {
        "progress_budget_m": float(budget),
        "candidate0_feasible_records": candidate0_feasible,
        "active_override_records": active_overrides,
        "outcome_override_available_records": outcome_available,
        "outcome_override_available_rate": outcome_available / denom,
        "proxy_override_available_records": proxy_available,
        "proxy_override_available_rate": proxy_available / denom,
        "hidden_outcome_records": hidden_outcome,
        "hidden_outcome_rate": hidden_outcome / denom,
        "proxy_only_records": proxy_only,
        "proxy_only_rate": proxy_only / denom,
        "selected_matches_outcome_records": selected_matches_outcome,
        "selected_matches_outcome_rate_among_overrides": (
            selected_matches_outcome / override_denom
        ),
        "selected_matches_proxy_records": selected_matches_proxy,
        "selected_matches_proxy_rate_among_overrides": (
            selected_matches_proxy / override_denom
        ),
        "selected_nonzero_without_outcome_records": selected_nonzero_without_outcome,
        "selected_nonzero_without_outcome_rate_among_overrides": (
            selected_nonzero_without_outcome / override_denom
        ),
        "selected_nonzero_without_proxy_records": selected_nonzero_without_proxy,
        "selected_nonzero_without_proxy_rate_among_overrides": (
            selected_nonzero_without_proxy / override_denom
        ),
        "outcome_available_but_selected_not_matching_records": (
            outcome_available_but_selected_not_matching
        ),
        "outcome_available_but_selected_not_matching_rate_among_overrides": (
            outcome_available_but_selected_not_matching / override_denom
        ),
    }


def _outcome_mask_vs_candidate0(record: dict[str, Any], budget: float) -> np.ndarray:
    size = int(record["candidate_count"])
    mask = record["feasible"].copy()
    mask[0] = False
    candidate0_progress = _outcome_float(record, 0, "progress_m")
    mask &= np.asarray(
        [
            _outcome_float(record, index, "progress_m")
            >= candidate0_progress - budget - TOL
            for index in range(size)
        ],
        dtype=bool,
    )
    strict = np.zeros(size, dtype=bool)
    for field in BOOL_OUTCOMES:
        reference = bool(record["outcomes"][0].get(field))
        values = np.asarray(
            [bool(record["outcomes"][index].get(field)) for index in range(size)],
            dtype=bool,
        )
        mask &= values.astype(float) <= float(reference)
        strict |= reference & ~values

    jerk = np.asarray(
        [_outcome_float(record, index, "mean_jerk_mps3") for index in range(size)]
    )
    lateral = np.asarray(
        [
            _outcome_float(record, index, "mean_lateral_acceleration_mps2")
            for index in range(size)
        ]
    )
    mask &= jerk <= jerk[0] + TOL
    mask &= lateral <= lateral[0] + TOL
    strict |= jerk < jerk[0] - TOL
    strict |= lateral < lateral[0] - TOL
    return mask & strict


def _proxy_mask_vs_candidate0(record: dict[str, Any], budget: float) -> np.ndarray:
    mask = record["feasible"].copy()
    mask[0] = False
    mask &= record["progress_shortfall"] <= record["progress_shortfall"][0] + budget + TOL
    mask &= record["union_red"] <= record["union_red"][0] + TOL
    mask &= record["red_stopping"] <= record["red_stopping"][0] + TOL
    mask &= record["proxy_jerk"] <= record["proxy_jerk"][0] + TOL
    mask &= record["proxy_lateral"] <= record["proxy_lateral"][0] + TOL
    strict = (
        (record["union_red"] < record["union_red"][0] - TOL)
        | (record["red_stopping"] < record["red_stopping"][0] - TOL)
        | (record["proxy_jerk"] < record["proxy_jerk"][0] - TOL)
        | (record["proxy_lateral"] < record["proxy_lateral"][0] - TOL)
    )
    return mask & strict


def _example_row(record: dict[str, Any], contributions: np.ndarray) -> dict[str, Any]:
    selected = int(record["selected_index"])
    order = np.argsort(contributions)
    attractive = [
        {
            "atom": str(record["atom_names"][index]),
            "contribution": float(contributions[index]),
            "raw_delta": float(record["atoms"][selected, index] - record["atoms"][0, index]),
            "normalized_delta": float(
                record["normalized_atoms"][selected, index]
                - record["normalized_atoms"][0, index]
            ),
            "weight": float(record["weights"][index]),
        }
        for index in order[:3]
    ]
    context = record["context"]
    return {
        "route_name": context["route_name"],
        "scenario_buckets": context["scenario_buckets"],
        "seed": context["seed"],
        "max_npcs": context["max_npcs"],
        "traffic_lights": context["traffic_lights"],
        "selection_step": record["selection_step"],
        "selected_index": selected,
        "selection_score_delta": float(record["scores"][selected] - record["scores"][0]),
        "top_attractive_atoms": attractive,
        "outcome_delta_selected_minus_candidate0": {
            "progress_m": _outcome_float(record, selected, "progress_m")
            - _outcome_float(record, 0, "progress_m"),
            "mean_jerk_mps3": _outcome_float(record, selected, "mean_jerk_mps3")
            - _outcome_float(record, 0, "mean_jerk_mps3"),
            "mean_lateral_acceleration_mps2": _outcome_float(
                record,
                selected,
                "mean_lateral_acceleration_mps2",
            )
            - _outcome_float(record, 0, "mean_lateral_acceleration_mps2"),
        },
        "run_key": context["run_key"],
        "log_path": context["log_path"],
    }


def _atom_table(
    atom_stats: dict[str, dict[str, Any]],
    *,
    attractive: bool,
) -> list[dict[str, Any]]:
    rows = []
    for atom, stats in atom_stats.items():
        contributions = [float(value) for value in stats["contributions"]]
        row = {
            "atom": atom,
            "n": len(contributions),
            "mean_contribution": _mean(contributions),
            "sum_contribution": float(np.sum(np.asarray(contributions, dtype=np.float64)))
            if contributions
            else 0.0,
            "attractive_count": int(stats["attractive"]),
            "repulsive_count": int(stats["repulsive"]),
            "mean_raw_delta": _mean([float(value) for value in stats["raw_deltas"]]),
            "mean_normalized_delta": _mean(
                [float(value) for value in stats["normalized_deltas"]]
            ),
            "mean_weight": _mean([float(value) for value in stats["weight"]]),
        }
        rows.append(row)
    if attractive:
        rows.sort(key=lambda row: (float(row["sum_contribution"]), row["atom"]))
    else:
        rows.sort(key=lambda row: (-float(row["sum_contribution"]), row["atom"]))
    return rows[:10]


def _records_by_bucket(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        buckets = record["context"].get("scenario_buckets")
        if not isinstance(buckets, list) or not buckets:
            buckets = ["overall"]
        for bucket in buckets:
            if bucket not in SUPPORTED_SCENARIO_BUCKETS:
                raise ValueError(f"Unsupported scenario bucket: {bucket}")
            grouped[str(bucket)].append(record)
    return {bucket: grouped[bucket] for bucket in _ordered_buckets(grouped)}


def _ordered_buckets(grouped: dict[str, list[dict[str, Any]]]) -> list[str]:
    order = [
        "overall",
        "normal",
        "traffic_light",
        "red_light_turn",
        "sharp_turn",
        "npc_interaction",
        "dense_scene",
        "lane_change_or_merge",
    ]
    return [bucket for bucket in order if bucket in grouped] + sorted(
        bucket for bucket in grouped if bucket not in order
    )


def _atom_vector(
    atoms: np.ndarray,
    atom_names: tuple[str, ...],
    atom_name: str,
    label: str,
) -> np.ndarray:
    if atom_name not in atom_names:
        raise ValueError(f"{label} is missing {atom_name} atom.")
    return atoms[:, atom_names.index(atom_name)]


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _outcome_float(record: dict[str, Any], index: int, field: str) -> float:
    value = float(record["outcomes"][index].get(field))
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"Outcome {field} must be finite and nonnegative.")
    return value


def _matrix(values: Any, rows: int, cols: int, label: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.shape != (rows, cols):
        raise ValueError(f"{label} must have shape [{rows},{cols}].")
    if not np.all(np.isfinite(matrix)) or np.any(matrix < 0.0):
        raise ValueError(f"{label} must be finite and nonnegative.")
    return matrix


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    return _finite_vector(values, size, label, nonnegative=True)


def _finite_vector(
    values: Any,
    size: int,
    label: str,
    *,
    nonnegative: bool,
) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}].")
    if not np.all(np.isfinite(vector)):
        raise ValueError(f"{label} must be finite.")
    if nonnegative and np.any(vector < 0.0):
        raise ValueError(f"{label} must be nonnegative.")
    return vector


def _score_vector(values: Any, size: int, label: str) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}].")
    if np.any(np.isnan(vector)) or np.any(vector == -np.inf):
        raise ValueError(f"{label} may contain finite values or +inf only.")
    return vector


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(
        isinstance(value, (bool, np.bool_)) for value in raw
    ):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _canonical_budget(value: float) -> float:
    budget = round(float(value), 8)
    if budget < -TOL:
        raise ValueError("Progress budgets must be nonnegative.")
    return budget


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean": None, "p50": None, "p90": None}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    active = report["candidate0_feasible_active_override"]
    lines = [
        "# DP CAMP Top-1 Preservation Attribution",
        "",
        "This is a read-only offline audit. Candidate outcomes are labels for "
        "diagnosis only and are not online selector inputs.",
        "",
        "## Records",
        "",
        f"- Logs: `{records.get('logs', 'n/a')}`",
        f"- Records: `{records['total']}`",
        f"- Nonfallback / fallback: `{records['nonfallback']}` / `{records['fallback']}`",
        f"- Selected nonzero: `{records['selected_nonzero']}` "
        f"({records['selected_nonzero_rate']:.6f})",
        f"- Candidate0 feasible active overrides: "
        f"`{records['candidate0_feasible_active_override']}` "
        f"({records['candidate0_feasible_active_override_rate']:.6f})",
        f"- Candidate0 infeasible selected nonzero: "
        f"`{records['candidate0_infeasible_selected_nonzero']}`",
        f"- All-infeasible selected nonzero: "
        f"`{records['all_infeasible_selected_nonzero']}`",
        "",
        "## Preservation Categories",
        "",
        "| Category | Records |",
        "| --- | ---: |",
    ]
    for category, count in report["preservation_categories"].items():
        lines.append(f"| `{category}` | {count} |")

    score = active["selection_score_delta_selected_minus_candidate0"]
    residual = active["score_contribution_residual"]
    lines.extend(
        [
            "",
            "## Active Override Score Attribution",
            "",
            f"- Active override records: `{active['records']}`",
            f"- Mean selection score delta selected-candidate0: "
            f"`{_fmt(score['mean'])}`",
            f"- Mean affine contribution residual: `{_fmt(residual['mean'])}`",
            "",
            "### Top Attractive Atoms",
            "",
            _atom_markdown_table(active["top_attractive_atoms"]),
            "### Top Repulsive Atoms",
            "",
            _atom_markdown_table(active["top_repulsive_atoms"]),
            "### Outcome Delta Selected Minus Candidate0",
            "",
            "| Field | n | mean | p50 | p90 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for field, stats in active["outcome_delta_selected_minus_candidate0"].items():
        lines.append(
            f"| `{field}` | {stats['n']} | {_fmt(stats['mean'])} | "
            f"{_fmt(stats['p50'])} | {_fmt(stats['p90'])} |"
        )

    lines.extend(
        [
            "",
            "## Candidate Availability Oracle",
            "",
            "| Progress budget | Candidate0 feasible | Outcome available | "
            "Proxy available | Hidden outcome | Proxy only | "
            "Selected matches outcome | Selected without outcome |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["candidate_availability_oracle"]:
        lines.append(
            f"| {row['progress_budget_m']:.2f} | "
            f"{row['candidate0_feasible_records']} | "
            f"{row['outcome_override_available_records']} "
            f"({row['outcome_override_available_rate']:.6f}) | "
            f"{row['proxy_override_available_records']} "
            f"({row['proxy_override_available_rate']:.6f}) | "
            f"{row['hidden_outcome_records']} "
            f"({row['hidden_outcome_rate']:.6f}) | "
            f"{row['proxy_only_records']} "
            f"({row['proxy_only_rate']:.6f}) | "
            f"{row['selected_matches_outcome_records']} "
            f"({row['selected_matches_outcome_rate_among_overrides']:.6f}) | "
            f"{row['selected_nonzero_without_outcome_records']} "
            f"({row['selected_nonzero_without_outcome_rate_among_overrides']:.6f}) |"
        )

    lines.extend(
        [
            "",
            "## Scenario Buckets",
            "",
            "| Bucket | Records | Active overrides | Override rate |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for bucket in report["by_bucket"]:
        row = bucket["records"]
        lines.append(
            f"| `{bucket['bucket']}` | {row['total']} | "
            f"{row['candidate0_feasible_active_override']} | "
            f"{row['candidate0_feasible_active_override_rate']:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _atom_markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No active overrides._\n"
    lines = [
        "| Atom | Sum contribution | Mean contribution | Attractive | Repulsive | Mean raw delta | Mean weight |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['atom']}` | {_fmt(row['sum_contribution'])} | "
            f"{_fmt(row['mean_contribution'])} | "
            f"{row['attractive_count']} | {row['repulsive_count']} | "
            f"{_fmt(row['mean_raw_delta'])} | {_fmt(row['mean_weight'])} |"
        )
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


if __name__ == "__main__":
    main()
