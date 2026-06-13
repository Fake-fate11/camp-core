from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner import (
    CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES,
    DP_CAMP_ATOM_NAMES_V8,
    summarize_selection_records,
)


@dataclass(frozen=True)
class SelectionLogMetadata:
    log_path: str
    run_root: str
    route: str
    seed: int | None
    npc_count: int | None
    spawn: str
    traffic_light: str
    mode: str


TARGET_SPECS: dict[str, tuple[str, str, bool]] = {
    "closed_loop_value": ("outcome", "value", True),
    "dp_total_reward": ("reward", "total", True),
    "planned_red_light_cost": ("reward", "red_light", False),
    "closed_loop_red_light_violation": ("outcome", "red_light_violation", False),
    "closed_loop_lateral_acceleration": (
        "outcome",
        "mean_lateral_acceleration_mps2",
        False,
    ),
}


def atom_names_for_dimension(num_atoms: int) -> tuple[str, ...]:
    if num_atoms == len(CAMP_ATOM_NAMES):
        return CAMP_ATOM_NAMES
    if num_atoms == len(DP_CAMP_ATOM_NAMES):
        return DP_CAMP_ATOM_NAMES
    if num_atoms == len(DP_CAMP_ATOM_NAMES_V8):
        return DP_CAMP_ATOM_NAMES_V8
    return tuple(f"atom_{idx}" for idx in range(num_atoms))


def iter_selection_log_paths(paths: Sequence[Path]) -> list[Path]:
    logs: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file():
            if path.name != "camp_selection_log.json":
                raise ValueError(f"Expected camp_selection_log.json, got {path}.")
            logs.append(path)
        elif path.is_dir():
            logs.extend(sorted(path.rglob("camp_selection_log.json")))
        else:
            raise FileNotFoundError(path)
    return sorted(dict.fromkeys(logs))


def parse_selection_log_metadata(log_path: Path) -> SelectionLogMetadata:
    path = Path(log_path)
    parents = list(path.parents)

    def parent_name(idx: int, default: str = "unknown") -> str:
        return parents[idx].name if idx < len(parents) else default

    route = parent_name(5)
    run_root = parent_name(6)
    seed = _parse_prefixed_int(parent_name(4), "seed_")
    npc_count = _parse_prefixed_int(parent_name(3), "npc_")
    spawn = parent_name(2)
    traffic_light = parent_name(1)
    if traffic_light.startswith("tl_"):
        traffic_light = traffic_light[3:]
    mode = parent_name(0)
    return SelectionLogMetadata(
        log_path=str(path),
        run_root=run_root,
        route=route,
        seed=seed,
        npc_count=npc_count,
        spawn=spawn,
        traffic_light=traffic_light,
        mode=mode,
    )


def compute_atom_coverage_report(
    paths: Sequence[Path],
    *,
    mode_filter: set[str] | None = None,
    extra_scale_percentile: float = 95.0,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if mode_filter:
        log_paths = [
            path
            for path in log_paths
            if parse_selection_log_metadata(path).mode in mode_filter
        ]
    if not log_paths:
        raise ValueError("No camp_selection_log.json files matched the inputs.")

    logs: list[dict[str, Any]] = []
    record_infos: list[dict[str, Any]] = []
    red_light_values: list[np.ndarray] = []
    lateral_values: list[np.ndarray] = []

    for log_path in log_paths:
        metadata = parse_selection_log_metadata(log_path)
        records = _load_selection_log(log_path)
        validation_summary = _load_validation_summary(log_path)
        selection_summary = summarize_selection_records(records)
        log_info = {
            "metadata": asdict(metadata),
            "selection_summary": selection_summary,
            "validation_summary": validation_summary,
        }
        logs.append(log_info)

        log_red_light_exposed = _summary_red_light_exposed(validation_summary)
        for record_idx, record in enumerate(records):
            info = _record_info(
                metadata,
                record_idx,
                record,
                log_red_light_exposed=log_red_light_exposed,
            )
            record_infos.append(info)
            if info["red_light_cost"] is not None:
                red_light_values.append(info["red_light_cost"])
            if info["lateral_acceleration_cost"] is not None:
                lateral_values.append(info["lateral_acceleration_cost"])

    red_scale = _robust_positive_scale(red_light_values, extra_scale_percentile)
    lateral_scale = _robust_positive_scale(lateral_values, extra_scale_percentile)
    extra_scales = {
        "planned_red_light_cost": red_scale,
        "lateral_acceleration_proxy": lateral_scale,
    }

    score_variants = _score_variant_metrics(record_infos, extra_scales)
    report = {
        "analysis": {
            "name": "diffusion_planner_camp_atom_coverage",
            "extra_scale_percentile": float(extra_scale_percentile),
            "mode_filter": sorted(mode_filter) if mode_filter else None,
        },
        "summary": _global_summary(logs, record_infos),
        "shadow_red_stopping_margin": _shadow_red_stopping_margin_coverage(
            record_infos
        ),
        "extra_feature_scales": extra_scales,
        "alignment": score_variants,
        "atom_target_correlations": _atom_target_correlations(record_infos),
        "scenario_breakdown": {
            "by_run_root": _group_records(record_infos, "run_root"),
            "by_route": _group_records(record_infos, "route"),
            "by_npc_count": _group_records(record_infos, "npc_count"),
            "by_traffic_light": _group_records(record_infos, "traffic_light"),
            "by_mode": _group_records(record_infos, "mode"),
            "by_red_light_exposed": _group_records(
                record_infos,
                "red_light_exposed",
            ),
            "by_fallback_mode": _group_records(record_infos, "fallback_mode"),
            "by_used_fallback": _group_records(record_infos, "used_fallback"),
        },
        "log_summaries": logs,
        "consistency_checks": _consistency_checks(record_infos),
    }
    return _json_safe(report)


def render_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Diffusion Planner CAMP Atom Coverage",
        "",
        "## Dataset",
        "",
        f"- Logs: {summary['log_count']}",
        f"- Records: {summary['record_count']}",
        f"- Candidates: {summary['candidate_count']}",
        f"- Atom dimensions: {summary['atom_dimensions']}",
        f"- Fallback rate: {_fmt(summary['fallback_rate'])}",
        f"- Candidate feasible rate: {_fmt(summary['candidate_feasible_rate'])}",
        "",
        "## Closed-Loop Oracle Alignment",
        "",
        "| score variant | match rate | mean regret | selected value | selected red-light | selected lateral accel |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    alignment = report["alignment"].get("closed_loop_value", {})
    red_alignment = report["alignment"].get("closed_loop_red_light_violation", {})
    lat_alignment = report["alignment"].get("closed_loop_lateral_acceleration", {})
    for variant in [
        "base",
        "plus_planned_red_light",
        "plus_lateral_acceleration_proxy",
        "plus_both",
    ]:
        closed = alignment.get(variant, {})
        red = red_alignment.get(variant, {})
        lat = lat_alignment.get(variant, {})
        lines.append(
            "| "
            + " | ".join(
                [
                    variant,
                    _fmt(closed.get("oracle_match_rate")),
                    _fmt(closed.get("mean_regret")),
                    _fmt(closed.get("mean_selected_value")),
                    _fmt(red.get("mean_selected_value")),
                    _fmt(lat.get("mean_selected_value")),
                ]
            )
            + " |"
        )

    shadow = report.get("shadow_red_stopping_margin", {})
    lines.extend(
        [
            "",
            "## Shadow Red Stopping-Margin Coverage",
            "",
            f"- Record availability: {_fmt(shadow.get('record_availability_rate'))}",
            f"- Records with red route points: {shadow.get('red_route_exposed_records', 0)}",
            f"- Feasible records with candidate variation: {shadow.get('feasible_records_with_variation', 0)}",
            f"- Feasible candidates with nonzero cost: {shadow.get('feasible_candidates_nonzero', 0)}",
            f"- All-infeasible records with candidate variation: {shadow.get('fallback_records_with_variation', 0)}",
            "",
            "## Scenario Breakdown",
            "",
            "| group | value | records | fallback rate | selected red-light | selected lateral accel |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for group_name in [
        "by_route",
        "by_npc_count",
        "by_traffic_light",
        "by_red_light_exposed",
        "by_fallback_mode",
        "by_used_fallback",
    ]:
        for row in report["scenario_breakdown"].get(group_name, []):
            lines.append(
                "| "
                + " | ".join(
                    [
                        group_name,
                        str(row["value"]),
                        str(row["record_count"]),
                        _fmt(row.get("fallback_rate")),
                        _fmt(row.get("selected_red_light_violation_rate")),
                        _fmt(row.get("mean_selected_lateral_acceleration")),
                    ]
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `plus_planned_red_light` uses the online DP `red_light` penalty magnitude (negative reward clipped to severity) as a diagnostic cost.",
            "- `plus_lateral_acceleration_proxy` uses the logged closed-loop lateral acceleration label only as an offline proxy; the deployable v8 atom must be computed from candidate trajectory kinematics.",
            "- Closed-loop outcomes are treated as labels for evaluation/oracle construction, not as online selector inputs.",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_prefixed_int(value: str, prefix: str) -> int | None:
    if not value.startswith(prefix):
        return None
    try:
        return int(value[len(prefix) :])
    except ValueError:
        return None


def _load_selection_log(path: Path) -> list[dict[str, Any]]:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"{path} must contain a JSON list.")
    return records


def _load_validation_summary(log_path: Path) -> dict[str, Any] | None:
    summary_path = Path(log_path).with_name("camp_validation_summary.json")
    if not summary_path.is_file():
        return None
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError(f"{summary_path} must contain a JSON object.")
    return summary


def _summary_red_light_exposed(summary: dict[str, Any] | None) -> bool | None:
    if summary is None:
        return None
    value = summary.get("red_light_exposure_steps")
    if value is None:
        value = summary.get("planned_red_light_violation_steps")
    if value is None:
        return None
    return float(value) > 0.0


def _record_info(
    metadata: SelectionLogMetadata,
    record_idx: int,
    record: dict[str, Any],
    *,
    log_red_light_exposed: bool | None,
) -> dict[str, Any]:
    feasible_mask = np.asarray(record.get("feasible_mask", []), dtype=bool).reshape(-1)
    scores = _record_scores(record)
    if feasible_mask.size == 0:
        feasible_mask = np.ones(scores.shape, dtype=bool)
    if feasible_mask.shape != scores.shape:
        raise ValueError(
            f"{metadata.log_path} record {record_idx} has mismatched feasible mask "
            f"{feasible_mask.shape} and scores {scores.shape}."
        )
    if "selected_index" in record:
        selected_index = int(record["selected_index"])
    else:
        selected_index = _select_index(scores, feasible_mask)

    red_light_cost = _candidate_cost_values(record, "reward", "red_light")
    red_stopping_margin_cost = record.get(
        "candidate_red_stopping_margin_cost"
    )
    if red_stopping_margin_cost is not None:
        red_stopping_margin_cost = np.asarray(
            red_stopping_margin_cost,
            dtype=float,
        ).reshape(-1)
        if red_stopping_margin_cost.shape != scores.shape:
            raise ValueError(
                f"{metadata.log_path} record {record_idx} has red stopping-margin "
                f"shape {red_stopping_margin_cost.shape}, expected {scores.shape}."
            )
        if (
            not np.all(np.isfinite(red_stopping_margin_cost))
            or np.any(red_stopping_margin_cost < 0.0)
        ):
            raise ValueError(
                f"{metadata.log_path} record {record_idx} has invalid red "
                "stopping-margin costs."
            )
    lateral_acceleration = _candidate_values(
        record,
        "outcome",
        "mean_lateral_acceleration_mps2",
    )
    closed_loop_value = _candidate_values(record, "outcome", "value")
    red_light_violation = _candidate_values(record, "outcome", "red_light_violation")
    red_light_exposed = log_red_light_exposed
    if red_light_exposed is None:
        exposed_parts = []
        if red_light_cost is not None:
            exposed_parts.append(bool(np.nanmax(red_light_cost) > 0.0))
        if red_light_violation is not None:
            exposed_parts.append(bool(np.nanmax(red_light_violation) > 0.0))
        red_light_exposed = any(exposed_parts) if exposed_parts else None

    atoms = np.asarray(record.get("normalized_atoms", record.get("atoms")), dtype=float)
    if atoms.ndim != 2 or atoms.shape[0] != scores.shape[0]:
        raise ValueError(
            f"{metadata.log_path} record {record_idx} has invalid atoms shape "
            f"{atoms.shape} for scores {scores.shape}."
        )
    return {
        "log_path": metadata.log_path,
        "run_root": metadata.run_root,
        "route": metadata.route,
        "seed": metadata.seed,
        "npc_count": metadata.npc_count,
        "spawn": metadata.spawn,
        "traffic_light": metadata.traffic_light,
        "mode": metadata.mode,
        "fallback_mode": record.get("camp_fallback_mode"),
        "record_index": record_idx,
        "selection_step": record.get("selection_step", record_idx),
        "selected_index": selected_index,
        "used_fallback": bool(record.get("used_fallback", False)),
        "feasible_any": bool(feasible_mask.any()),
        "feasible_mask": feasible_mask,
        "scores": scores,
        "atoms": atoms,
        "red_light_cost": red_light_cost,
        "red_stopping_margin_cost": red_stopping_margin_cost,
        "red_route_point_count": int(record.get("red_route_point_count", 0)),
        "lateral_acceleration_cost": lateral_acceleration,
        "closed_loop_value": closed_loop_value,
        "red_light_violation": red_light_violation,
        "red_light_exposed": red_light_exposed,
        "candidate_count": int(scores.size),
        "raw_record": record,
    }


def _shadow_red_stopping_margin_coverage(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    available = [
        info for info in records if info["red_stopping_margin_cost"] is not None
    ]
    if not records:
        return {"record_availability_rate": None, "records": 0}
    if not available:
        return {
            "record_availability_rate": 0.0,
            "records": 0,
            "candidate_count": 0,
            "red_route_exposed_records": 0,
            "records_with_nonzero_cost": 0,
            "feasible_records_with_variation": 0,
            "feasible_candidates_nonzero": 0,
            "fallback_records_with_variation": 0,
        }

    candidate_count = 0
    nonzero_candidates = 0
    records_with_nonzero = 0
    feasible_records = 0
    feasible_candidates = 0
    feasible_candidates_nonzero = 0
    feasible_records_with_variation = 0
    fallback_records = 0
    fallback_records_with_variation = 0
    all_values = []
    latencies = []
    for info in available:
        values = np.asarray(info["red_stopping_margin_cost"], dtype=float)
        feasible = np.asarray(info["feasible_mask"], dtype=bool)
        all_values.append(values)
        candidate_count += int(values.size)
        nonzero_candidates += int(np.count_nonzero(values > 1e-12))
        records_with_nonzero += int(np.any(values > 1e-12))
        latency = info["raw_record"].get(
            "latency_ms_shadow_red_stopping_margin"
        )
        if latency is not None and np.isfinite(float(latency)):
            latencies.append(float(latency))
        if feasible.any():
            feasible_records += 1
            feasible_values = values[feasible]
            feasible_candidates += int(feasible_values.size)
            feasible_candidates_nonzero += int(
                np.count_nonzero(feasible_values > 1e-12)
            )
            feasible_records_with_variation += int(
                float(np.ptp(feasible_values)) > 1e-12
            )
        else:
            fallback_records += 1
            fallback_records_with_variation += int(
                float(np.ptp(values)) > 1e-12
            )

    flat = np.concatenate(all_values)
    positive = flat[flat > 1e-12]
    return {
        "record_availability_rate": float(len(available) / len(records)),
        "records": int(len(available)),
        "candidate_count": int(candidate_count),
        "red_route_exposed_records": int(
            sum(info["red_route_point_count"] > 0 for info in available)
        ),
        "records_with_nonzero_cost": int(records_with_nonzero),
        "nonzero_candidates": int(nonzero_candidates),
        "feasible_records": int(feasible_records),
        "feasible_candidates": int(feasible_candidates),
        "feasible_candidates_nonzero": int(feasible_candidates_nonzero),
        "feasible_records_with_variation": int(
            feasible_records_with_variation
        ),
        "fallback_records": int(fallback_records),
        "fallback_records_with_variation": int(
            fallback_records_with_variation
        ),
        "positive_cost_p50": (
            float(np.percentile(positive, 50)) if positive.size else None
        ),
        "positive_cost_p95": (
            float(np.percentile(positive, 95)) if positive.size else None
        ),
        "maximum_cost": float(np.max(flat)) if flat.size else None,
        "mean_shadow_latency_ms": (
            float(np.mean(latencies)) if latencies else None
        ),
        "p95_shadow_latency_ms": (
            float(np.percentile(latencies, 95)) if latencies else None
        ),
    }


def _record_scores(record: dict[str, Any]) -> np.ndarray:
    if "selection_scores" in record:
        return np.asarray(record["selection_scores"], dtype=float).reshape(-1)
    if "scores" in record:
        return np.asarray(record["scores"], dtype=float).reshape(-1)
    normalized = np.asarray(record["normalized_atoms"], dtype=float)
    weights = np.asarray(record["weights"], dtype=float).reshape(-1)
    return normalized @ weights


def _candidate_values(
    record: dict[str, Any],
    source: str,
    key: str,
) -> np.ndarray | None:
    if source == "reward":
        candidates = record.get("dp_candidate_rewards")
    elif source == "outcome":
        candidates = record.get("candidate_closed_loop_outcomes")
    else:
        raise ValueError(f"Unknown candidate source {source!r}.")
    if not isinstance(candidates, list):
        return None
    values = []
    for candidate in candidates:
        if not isinstance(candidate, dict) or key not in candidate:
            return None
        values.append(float(candidate[key]))
    return np.asarray(values, dtype=float)


def _candidate_cost_values(
    record: dict[str, Any],
    source: str,
    key: str,
) -> np.ndarray | None:
    values = _candidate_values(record, source, key)
    if values is None:
        return None
    if source == "reward" and key == "red_light":
        return np.maximum(-values, 0.0)
    return values


def _target_values(
    record: dict[str, Any],
    source: str,
    key: str,
) -> np.ndarray | None:
    if source == "reward" and key == "red_light":
        return _candidate_cost_values(record, source, key)
    return _candidate_values(record, source, key)


def _select_index(scores: np.ndarray, feasible_mask: np.ndarray) -> int:
    finite = np.isfinite(scores)
    valid = finite & feasible_mask if feasible_mask.any() else finite
    if not valid.any():
        raise ValueError("Cannot select a candidate without finite scores.")
    masked = np.where(valid, scores, np.inf)
    return int(np.argmin(masked))


def _oracle_index(
    values: np.ndarray,
    feasible_mask: np.ndarray,
    *,
    maximize: bool,
) -> int | None:
    finite = np.isfinite(values)
    valid = finite & feasible_mask if feasible_mask.any() else finite
    if not valid.any():
        return None
    masked = np.where(valid, values, -np.inf if maximize else np.inf)
    return int(np.argmax(masked) if maximize else np.argmin(masked))


def _robust_positive_scale(values: Sequence[np.ndarray], percentile: float) -> float:
    if not values:
        return 1.0
    flat = np.concatenate([np.asarray(value, dtype=float).reshape(-1) for value in values])
    finite = np.abs(flat[np.isfinite(flat)])
    positive = finite[finite > 1e-12]
    if positive.size == 0:
        return 1.0
    scale = float(np.percentile(positive, percentile))
    if not np.isfinite(scale) or scale <= 0.0:
        return 1.0
    return scale


def _score_variant_metrics(
    records: list[dict[str, Any]],
    extra_scales: dict[str, float],
) -> dict[str, dict[str, dict[str, Any]]]:
    variants = {
        "base": lambda info: info["scores"],
        "plus_planned_red_light": lambda info: _augmented_score(
            info,
            "red_light_cost",
            extra_scales["planned_red_light_cost"],
        ),
        "plus_lateral_acceleration_proxy": lambda info: _augmented_score(
            info,
            "lateral_acceleration_cost",
            extra_scales["lateral_acceleration_proxy"],
        ),
        "plus_both": lambda info: _augmented_score(
            _with_scores(
                info,
                _augmented_score(
                    info,
                    "red_light_cost",
                    extra_scales["planned_red_light_cost"],
                ),
            ),
            "lateral_acceleration_cost",
            extra_scales["lateral_acceleration_proxy"],
        ),
    }
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for target_name, (source, key, maximize) in TARGET_SPECS.items():
        result[target_name] = {}
        for variant_name, score_fn in variants.items():
            result[target_name][variant_name] = _alignment_summary(
                records,
                score_fn,
                source=source,
                key=key,
                maximize=maximize,
            )
    return result


def _with_scores(info: dict[str, Any], scores: np.ndarray) -> dict[str, Any]:
    updated = dict(info)
    updated["scores"] = scores
    return updated


def _augmented_score(
    info: dict[str, Any],
    feature_key: str,
    scale: float,
) -> np.ndarray:
    base = np.asarray(info["scores"], dtype=float)
    feature = info.get(feature_key)
    if feature is None:
        return base
    feature_values = np.asarray(feature, dtype=float)
    if feature_values.shape != base.shape:
        return base
    safe_scale = max(float(scale), 1e-6)
    normalized = np.nan_to_num(feature_values / safe_scale, nan=0.0, posinf=10.0)
    normalized = np.maximum(normalized, 0.0)
    return base + normalized


def _alignment_summary(
    records: list[dict[str, Any]],
    score_fn,
    *,
    source: str,
    key: str,
    maximize: bool,
) -> dict[str, Any]:
    rows = []
    for info in records:
        values = _target_values(info["raw_record"], source, key)
        if values is None:
            continue
        scores = np.asarray(score_fn(info), dtype=float)
        feasible = np.asarray(info["feasible_mask"], dtype=bool)
        if values.shape != scores.shape:
            continue
        selected = _select_index(scores, feasible)
        oracle = _oracle_index(values, feasible, maximize=maximize)
        if oracle is None:
            continue
        selected_value = float(values[selected])
        oracle_value = float(values[oracle])
        regret = oracle_value - selected_value if maximize else selected_value - oracle_value
        valid = np.isfinite(values) & np.isfinite(scores)
        valid = valid & feasible if feasible.any() else valid
        preference_values = values if maximize else -values
        rows.append(
            {
                "match": float(selected == oracle),
                "regret": max(float(regret), 0.0),
                "selected_value": selected_value,
                "oracle_value": oracle_value,
                "used_fallback": float(info["used_fallback"]),
                "feasible_any": float(info["feasible_any"]),
                "correlation": _safe_corr(-scores[valid], preference_values[valid]),
            }
        )
    return _summarize_alignment_rows(rows)


def _summarize_alignment_rows(rows: list[dict[str, float | None]]) -> dict[str, Any]:
    if not rows:
        return {
            "records": 0,
            "oracle_match_rate": None,
            "mean_regret": None,
            "median_regret": None,
            "p90_regret": None,
            "mean_selected_value": None,
            "mean_oracle_value": None,
            "mean_score_target_correlation": None,
            "fallback_rate": None,
            "feasible_any_rate": None,
        }
    regrets = np.asarray([row["regret"] for row in rows], dtype=float)
    correlations = [
        row["correlation"]
        for row in rows
        if row["correlation"] is not None and np.isfinite(row["correlation"])
    ]
    return {
        "records": int(len(rows)),
        "oracle_match_rate": float(np.mean([row["match"] for row in rows])),
        "mean_regret": float(np.mean(regrets)),
        "median_regret": float(np.median(regrets)),
        "p90_regret": float(np.percentile(regrets, 90)),
        "mean_selected_value": float(np.mean([row["selected_value"] for row in rows])),
        "mean_oracle_value": float(np.mean([row["oracle_value"] for row in rows])),
        "mean_score_target_correlation": (
            float(np.mean(correlations)) if correlations else None
        ),
        "fallback_rate": float(np.mean([row["used_fallback"] for row in rows])),
        "feasible_any_rate": float(np.mean([row["feasible_any"] for row in rows])),
    }


def _atom_target_correlations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paired_by_dim_target: dict[tuple[int, str], list[tuple[np.ndarray, np.ndarray]]] = {}
    for info in records:
        atoms = np.asarray(info["atoms"], dtype=float)
        atom_dim = atoms.shape[1]
        for target_name, (source, key, maximize) in TARGET_SPECS.items():
            values = _target_values(info["raw_record"], source, key)
            if values is None or values.shape != atoms.shape[:1]:
                continue
            preference = values if maximize else -values
            paired_by_dim_target.setdefault((atom_dim, target_name), []).append(
                (atoms, preference)
            )

    rows: list[dict[str, Any]] = []
    for (atom_dim, target_key), chunks in sorted(paired_by_dim_target.items()):
        atom_values = np.concatenate([chunk[0] for chunk in chunks], axis=0)
        targets = np.concatenate([chunk[1] for chunk in chunks], axis=0)
        atom_names = atom_names_for_dimension(atom_dim)
        for atom_idx, atom_name in enumerate(atom_names):
            rows.append(
                {
                    "atom_dimension": atom_dim,
                    "atom": atom_name,
                    "target": target_key,
                    "preference_correlation": _safe_corr(
                        -atom_values[:, atom_idx],
                        targets,
                    ),
                }
            )
    return rows


def _global_summary(
    logs: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    record_count = len(records)
    candidate_count = int(sum(info["candidate_count"] for info in records))
    atom_dimensions = sorted({int(info["atoms"].shape[1]) for info in records})
    feasible_candidates = 0
    for info in records:
        feasible_candidates += int(np.asarray(info["feasible_mask"], dtype=bool).sum())
    return {
        "log_count": int(len(logs)),
        "record_count": int(record_count),
        "candidate_count": candidate_count,
        "atom_dimensions": atom_dimensions,
        "fallback_rate": (
            float(np.mean([info["used_fallback"] for info in records]))
            if records
            else None
        ),
        "candidate_feasible_rate": (
            feasible_candidates / candidate_count if candidate_count else None
        ),
        "closed_loop_outcome_record_rate": _record_availability_rate(
            records,
            "outcome",
            "value",
        ),
        "dp_reward_record_rate": _record_availability_rate(records, "reward", "total"),
    }


def _record_availability_rate(
    records: list[dict[str, Any]],
    source: str,
    key: str,
) -> float | None:
    if not records:
        return None
    available = [
        _candidate_values(info["raw_record"], source, key) is not None
        for info in records
    ]
    return float(np.mean(available))


def _group_records(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for info in records:
        value = info.get(key)
        grouped.setdefault(str(value), []).append(info)
    rows = []
    for value, group in sorted(grouped.items(), key=lambda item: item[0]):
        selected_red_light = []
        selected_lateral = []
        for info in group:
            selected = int(info["selected_index"])
            red = info.get("red_light_violation")
            lat = info.get("lateral_acceleration_cost")
            if red is not None and selected < len(red):
                selected_red_light.append(float(red[selected]))
            if lat is not None and selected < len(lat):
                selected_lateral.append(float(lat[selected]))
        rows.append(
            {
                "value": value,
                "record_count": int(len(group)),
                "fallback_rate": float(np.mean([g["used_fallback"] for g in group])),
                "feasible_any_rate": float(np.mean([g["feasible_any"] for g in group])),
                "selected_red_light_violation_rate": (
                    float(np.mean(selected_red_light)) if selected_red_light else None
                ),
                "mean_selected_lateral_acceleration": (
                    float(np.mean(selected_lateral)) if selected_lateral else None
                ),
            }
        )
    return rows


def _consistency_checks(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {}
    fallback_matches = [
        bool(info["used_fallback"]) == (not bool(info["feasible_any"]))
        for info in records
    ]
    selected_matches_scores = []
    for info in records:
        try:
            selected_matches_scores.append(
                int(info["selected_index"])
                == _select_index(info["scores"], info["feasible_mask"])
            )
        except ValueError:
            selected_matches_scores.append(False)
    return {
        "fallback_flag_matches_all_infeasible_rate": float(np.mean(fallback_matches)),
        "selected_index_matches_logged_scores_rate": float(
            np.mean(selected_matches_scores)
        ),
    }


def _safe_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    x_values = np.asarray(x, dtype=float).reshape(-1)
    y_values = np.asarray(y, dtype=float).reshape(-1)
    mask = np.isfinite(x_values) & np.isfinite(y_values)
    if int(mask.sum()) < 2:
        return None
    x_values = x_values[mask]
    y_values = y_values[mask]
    if float(np.std(x_values)) <= 1e-12 or float(np.std(y_values)) <= 1e-12:
        return None
    return float(np.corrcoef(x_values, y_values)[0, 1])


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)
