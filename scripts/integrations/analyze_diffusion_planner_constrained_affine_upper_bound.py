#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from dataclasses import dataclass
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
)
from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    FEATURE_SPECS as OBSERVABLE_FEATURE_SPECS,
    FORMAL_SEEDS,
    HARMFUL_BLOCK_RATE_TARGET,
    MIN_BENEFICIAL_CANDIDATES,
    MIN_HARMFUL_CANDIDATES,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PROGRESS_LOSS_BUDGET_M,
    FeatureSpec,
    _candidate_rows as _observable_candidate_rows,
    _class_counts,
    _load_json,
    _path_seeds,
    _ranked_screens,
    _record_seed,
    _screen_metrics,
    _screen_sort_key,
)
from scripts.integrations.analyze_diffusion_planner_route_progress_support_envelope import (  # noqa: E402
    FEATURE_SPECS as ENVELOPE_FEATURE_SPECS,
    REJECT_STATUS as ENVELOPE_REJECT_STATUS,
    _candidate_rows as _envelope_candidate_rows,
)


READY_STATUS = "constrained_affine_upper_bound_ready_for_certificate_design"
REJECT_STATUS = "constrained_affine_upper_bound_rejected"
SOURCE_BLOCKED_STATUS = "constrained_affine_upper_bound_source_not_ready"
FORMAL_SEED_STATUS = "constrained_affine_upper_bound_formal_seed_conflict"

READY_NEXT_WORK = "offline_affine_certificate_design_only"
ENVELOPE_FAILURE_GAP = "route_progress_support_envelope_does_not_separate_candidates"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)

DEFAULT_MAX_TOP_FEATURES = 12
DEFAULT_MAX_TERMS = 3
DEFAULT_SIMPLEX_DENOMINATOR = 4


@dataclass(frozen=True)
class RiskDescriptor:
    name: str
    source_feature: str
    orientation: str
    source_family: str
    rationale: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline constrained affine upper-bound diagnostic over already "
            "logged no-leak DP-CAMP descriptors. This is an oracle screen, not "
            "CAMP training and not an online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--route_envelope_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_value_gain", type=float, default=MIN_VALUE_GAIN)
    parser.add_argument("--min_value_loss", type=float, default=MIN_VALUE_LOSS)
    parser.add_argument("--progress_loss_budget_m", type=float, default=PROGRESS_LOSS_BUDGET_M)
    parser.add_argument("--harmful_block_rate_target", type=float, default=HARMFUL_BLOCK_RATE_TARGET)
    parser.add_argument("--beneficial_retain_rate_target", type=float, default=BENEFICIAL_RETAIN_RATE_TARGET)
    parser.add_argument("--allowed_harmful_rate_target", type=float, default=ALLOWED_HARMFUL_RATE_TARGET)
    parser.add_argument("--min_beneficial_candidates", type=int, default=MIN_BENEFICIAL_CANDIDATES)
    parser.add_argument("--min_harmful_candidates", type=int, default=MIN_HARMFUL_CANDIDATES)
    parser.add_argument("--max_top_features", type=int, default=DEFAULT_MAX_TOP_FEATURES)
    parser.add_argument("--max_terms", type=int, default=DEFAULT_MAX_TERMS)
    parser.add_argument("--simplex_denominator", type=int, default=DEFAULT_SIMPLEX_DENOMINATOR)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        route_envelope_report=_load_json(args.route_envelope_json),
        label=args.label,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
        harmful_block_rate_target=args.harmful_block_rate_target,
        beneficial_retain_rate_target=args.beneficial_retain_rate_target,
        allowed_harmful_rate_target=args.allowed_harmful_rate_target,
        min_beneficial_candidates=args.min_beneficial_candidates,
        min_harmful_candidates=args.min_harmful_candidates,
        max_top_features=args.max_top_features,
        max_terms=args.max_terms,
        simplex_denominator=args.simplex_denominator,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    route_envelope_report: dict[str, Any],
    label: str | None = None,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    max_top_features: int = DEFAULT_MAX_TOP_FEATURES,
    max_terms: int = DEFAULT_MAX_TERMS,
    simplex_denominator: int = DEFAULT_SIMPLEX_DENOMINATOR,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    items = []
    for log_path in log_paths:
        rows = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw in enumerate(rows):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            items.append(
                {
                    "raw": raw,
                    "context": {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "path_seeds": sorted(_path_seeds(log_path)),
                    },
                }
            )
    return analyze_records(
        items,
        route_envelope_report=route_envelope_report,
        label=label,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        max_top_features=max_top_features,
        max_terms=max_terms,
        simplex_denominator=simplex_denominator,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    route_envelope_report: dict[str, Any],
    label: str | None = None,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    max_top_features: int = DEFAULT_MAX_TOP_FEATURES,
    max_terms: int = DEFAULT_MAX_TERMS,
    simplex_denominator: int = DEFAULT_SIMPLEX_DENOMINATOR,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    source = _source_gate(route_envelope_report)
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    for index, item in enumerate(items):
        record_rows, formal_seed = _merged_candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            min_value_gain=min_value_gain,
            min_value_loss=min_value_loss,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        rows.extend(record_rows)
        formal_seed_records += int(formal_seed)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden for this offline gate.")

    alternative_rows = [row for row in rows if int(row["candidate_index"]) != 0]
    class_counts = _class_counts(alternative_rows)
    risk_rows, descriptors, normalization = _risk_oriented_rows(alternative_rows)
    single_screens = _single_descriptor_screens(
        risk_rows,
        descriptors,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    affine_screens = _affine_screens(
        risk_rows,
        single_screens,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        max_top_features=max_top_features,
        max_terms=max_terms,
        simplex_denominator=simplex_denominator,
    )
    ranked = sorted([*single_screens, *affine_screens], key=_screen_sort_key, reverse=True)
    failure_gap = _failure_gap(
        ranked,
        class_counts,
        source,
        formal_seed_records=formal_seed_records,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
    )
    decision = _decision(
        source,
        ranked,
        class_counts,
        formal_seed_records=formal_seed_records,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    return {
        "analysis": {
            "name": "dp_camp_constrained_affine_upper_bound_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_classification": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "descriptor_orientation": (
                "Each runtime descriptor is converted to a low-is-safer affine "
                "risk coordinate. Coefficients are constrained nonnegative and "
                "normalized to a simplex for the diagnostic."
            ),
            "oracle_search": {
                "max_top_features": int(max_top_features),
                "max_terms": int(max_terms),
                "simplex_denominator": int(simplex_denominator),
                "candidate_scalarizations": len(affine_screens),
            },
            "acceptance_targets": {
                "harmful_block_rate": float(harmful_block_rate_target),
                "beneficial_retain_rate": float(beneficial_retain_rate_target),
                "allowed_harmful_rate": float(allowed_harmful_rate_target),
                "min_beneficial_candidates": int(min_beneficial_candidates),
                "min_harmful_candidates": int(min_harmful_candidates),
            },
            "math_boundary": (
                "All scalarized descriptors are fixed current-tick "
                "finite-candidate affine functions of logged no-leak "
                "descriptors. Outcome labels are used only offline to classify "
                "alternatives and score threshold diagnostics. Nonnegative "
                "simplex coefficients preserve affine score_k(w)=a_k^T w after "
                "atomization, and remain compatible with the simplex/CVaR/L2 "
                "convex master. This script constructs no DP-side classical "
                "Benders master, subproblem, dual, or cut."
            ),
        },
        "source_route_envelope_gate": source,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
        "risk_descriptors": [_descriptor_payload(descriptor) for descriptor in descriptors],
        "normalization": normalization,
        "descriptor_coverage": _descriptor_coverage(risk_rows, descriptors),
        "single_descriptor_screens": single_screens[:50],
        "affine_screens": affine_screens[:50],
        "ranked_screens": ranked[:50],
        "failure_gap": failure_gap,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _merged_candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    *,
    min_value_gain: float,
    min_value_loss: float,
    progress_loss_budget_m: float,
) -> tuple[list[dict[str, Any]], bool]:
    observable_rows, observable_formal_seed = _observable_candidate_rows(
        raw,
        context,
        label,
        OBSERVABLE_FEATURE_SPECS,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
    )
    envelope_rows, envelope_formal_seed = _envelope_candidate_rows(
        raw,
        context,
        label,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
    )
    if len(observable_rows) != len(envelope_rows):
        raise ValueError(f"{label} observable/envelope row count mismatch.")
    merged = []
    for obs, env in zip(observable_rows, envelope_rows, strict=True):
        for key in (
            "candidate_index",
            "class",
            "outcome_value_delta_vs_top1",
            "progress_delta_vs_top1_m",
            "hard_violation_delta_vs_top1",
        ):
            if obs[key] != env[key]:
                raise ValueError(f"{label} observable/envelope {key} mismatch.")
        features = {
            f"observable.{name}": value
            for name, value in obs["features"].items()
        }
        features.update(
            {
                f"envelope.{name}": value
                for name, value in env["features"].items()
            }
        )
        merged.append({**obs, "features": features})
    record_seed = _record_seed(raw)
    record_formal_seed = record_seed in FORMAL_SEEDS
    return merged, bool(observable_formal_seed or envelope_formal_seed or record_formal_seed)


def _risk_oriented_rows(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[RiskDescriptor], dict[str, Any]]:
    descriptors = _risk_descriptors()
    raw_values: dict[str, np.ndarray] = {}
    for descriptor in descriptors:
        source = descriptor.source_feature
        values = np.asarray(
            [
                _oriented_value(row["features"].get(source), descriptor.orientation)
                for row in rows
            ],
            dtype=np.float64,
        )
        raw_values[descriptor.name] = values

    normalization: dict[str, Any] = {}
    normalized: dict[str, np.ndarray] = {}
    kept_descriptors: list[RiskDescriptor] = []
    for descriptor in descriptors:
        values = raw_values[descriptor.name]
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            normalization[descriptor.name] = {"kept": False, "reason": "no_finite_values"}
            continue
        min_value = float(np.min(finite))
        shifted = values - min_value
        finite_shifted = shifted[np.isfinite(shifted)]
        scale = float(np.percentile(finite_shifted, 95.0)) if finite_shifted.size else 0.0
        if not math.isfinite(scale) or scale <= 1e-12:
            scale = float(np.max(finite_shifted)) if finite_shifted.size else 0.0
        if not math.isfinite(scale) or scale <= 1e-12:
            normalization[descriptor.name] = {
                "kept": False,
                "reason": "no_variation_after_orientation",
                "offset": min_value,
            }
            continue
        normalized[descriptor.name] = shifted / scale
        kept_descriptors.append(descriptor)
        normalization[descriptor.name] = {
            "kept": True,
            "orientation": descriptor.orientation,
            "offset": min_value,
            "scale": scale,
        }

    risk_rows = []
    for idx, row in enumerate(rows):
        features = {
            descriptor.name: float(normalized[descriptor.name][idx])
            for descriptor in kept_descriptors
            if np.isfinite(normalized[descriptor.name][idx])
        }
        risk_rows.append({**row, "features": features})
    return risk_rows, kept_descriptors, normalization


def _risk_descriptors() -> list[RiskDescriptor]:
    descriptors: list[RiskDescriptor] = []
    for family, specs in (
        ("observable", OBSERVABLE_FEATURE_SPECS),
        ("envelope", ENVELOPE_FEATURE_SPECS),
    ):
        for spec in specs:
            source_name = f"{family}.{spec.name}"
            for orientation, suffix in _orientations(spec):
                descriptors.append(
                    RiskDescriptor(
                        name=f"{source_name}.{suffix}_risk",
                        source_feature=source_name,
                        orientation=orientation,
                        source_family=family,
                        rationale=spec.rationale,
                    )
                )
    return descriptors


def _orientations(spec: FeatureSpec) -> list[tuple[str, str]]:
    if spec.direction_hint == "allow_low":
        return [("identity", "low")]
    if spec.direction_hint == "allow_high":
        return [("negative", "high")]
    if spec.direction_hint == "both":
        return [("identity", "low"), ("negative", "high")]
    raise ValueError(f"Unknown direction hint {spec.direction_hint!r}.")


def _oriented_value(value: Any, orientation: str) -> float:
    if value is None:
        return math.nan
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return math.nan
    if not math.isfinite(numeric):
        return math.nan
    if orientation == "identity":
        return numeric
    if orientation == "negative":
        return -numeric
    raise ValueError(f"Unknown orientation {orientation!r}.")


def _single_descriptor_screens(
    rows: list[dict[str, Any]],
    descriptors: list[RiskDescriptor],
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> list[dict[str, Any]]:
    screens = []
    for descriptor in descriptors:
        screens.extend(
            _threshold_screens(
                rows,
                score_name=descriptor.name,
                screen_name=f"{descriptor.name}:allow_low",
                harmonic=False,
                weights={descriptor.name: 1.0},
                harmful_block_rate_target=harmful_block_rate_target,
                beneficial_retain_rate_target=beneficial_retain_rate_target,
                allowed_harmful_rate_target=allowed_harmful_rate_target,
                min_beneficial_candidates=min_beneficial_candidates,
                min_harmful_candidates=min_harmful_candidates,
            )
        )
    best_by_descriptor = {}
    for screen in screens:
        source = screen["feature_names"][0]
        if source not in best_by_descriptor or _screen_sort_key(screen) > _screen_sort_key(best_by_descriptor[source]):
            best_by_descriptor[source] = screen
    return sorted(best_by_descriptor.values(), key=_screen_sort_key, reverse=True)


def _affine_screens(
    rows: list[dict[str, Any]],
    single_screens: list[dict[str, Any]],
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
    max_top_features: int,
    max_terms: int,
    simplex_denominator: int,
) -> list[dict[str, Any]]:
    feature_names = [
        str(screen["feature_names"][0])
        for screen in sorted(single_screens, key=_screen_sort_key, reverse=True)
    ][: max(1, int(max_top_features))]
    if not feature_names:
        return []
    candidates = []
    max_terms = max(1, int(max_terms))
    denominator = max(1, int(simplex_denominator))
    for term_count in range(2, max_terms + 1):
        for names in itertools.combinations(feature_names, term_count):
            for weights in _simplex_weights(term_count, denominator):
                score_name = _affine_score_name(names, weights)
                score_rows = _rows_with_affine_score(rows, score_name, names, weights)
                screens = _threshold_screens(
                    score_rows,
                    score_name=score_name,
                    screen_name=f"{score_name}:allow_low",
                    harmonic=True,
                    weights=dict(zip(names, weights, strict=True)),
                    harmful_block_rate_target=harmful_block_rate_target,
                    beneficial_retain_rate_target=beneficial_retain_rate_target,
                    allowed_harmful_rate_target=allowed_harmful_rate_target,
                    min_beneficial_candidates=min_beneficial_candidates,
                    min_harmful_candidates=min_harmful_candidates,
                )
                best = max(screens, key=_screen_sort_key) if screens else None
                if best is not None:
                    candidates.append(best)
    return sorted(candidates, key=_screen_sort_key, reverse=True)


def _simplex_weights(term_count: int, denominator: int) -> list[tuple[float, ...]]:
    if term_count == 1:
        return [(1.0,)]
    weights = []
    for ints in itertools.product(range(1, denominator + 1), repeat=term_count):
        if sum(ints) != denominator:
            continue
        weights.append(tuple(float(value) / denominator for value in ints))
    return weights


def _affine_score_name(names: tuple[str, ...], weights: tuple[float, ...]) -> str:
    parts = [
        f"{weight:.3f}*{name}"
        for name, weight in zip(names, weights, strict=True)
    ]
    return "affine_upper_bound(" + "+".join(parts) + ")"


def _rows_with_affine_score(
    rows: list[dict[str, Any]],
    score_name: str,
    names: tuple[str, ...],
    weights: tuple[float, ...],
) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        score = 0.0
        finite = True
        for name, weight in zip(names, weights, strict=True):
            value = row["features"].get(name)
            if value is None or not math.isfinite(float(value)):
                finite = False
                break
            score += float(weight) * float(value)
        features = dict(row["features"])
        if finite:
            features[score_name] = score
        result.append({**row, "features": features})
    return result


def _threshold_screens(
    rows: list[dict[str, Any]],
    *,
    score_name: str,
    screen_name: str,
    harmonic: bool,
    weights: dict[str, float],
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> list[dict[str, Any]]:
    values = np.asarray(
        [row["features"].get(score_name, np.nan) for row in rows],
        dtype=np.float64,
    )
    thresholds = _thresholds(values[np.isfinite(values)])
    screens = []
    for threshold in thresholds:
        screen = _screen_metrics(
            rows,
            feature_names=(score_name,),
            directions=("allow_low",),
            thresholds=(threshold,),
            screen_name=screen_name,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            allowed_harmful_rate_target=allowed_harmful_rate_target,
            min_beneficial_candidates=min_beneficial_candidates,
            min_harmful_candidates=min_harmful_candidates,
        )
        screen["source"] = "affine" if harmonic else "descriptor"
        screen["nonnegative_simplex_weights"] = {
            name: float(weight)
            for name, weight in sorted(weights.items())
        }
        screens.append(screen)
    return screens


def _thresholds(values: np.ndarray) -> list[float]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return []
    percentiles = (0.0, 5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0, 100.0)
    return sorted({float(value) for value in np.percentile(finite, percentiles) if math.isfinite(float(value))})


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    primary_gap = decision.get("primary_gap")
    ready = (
        status == ENVELOPE_REJECT_STATUS
        and primary_gap == ENVELOPE_FAILURE_GAP
        and not bool(decision.get("passed"))
    )
    return {
        "passed": ready,
        "status": status,
        "primary_gap": primary_gap,
        "authorized_next_work": decision.get("authorized_next_work"),
    }


def _decision(
    source: dict[str, Any],
    ranked_screens: list[dict[str, Any]],
    class_counts: dict[str, int],
    *,
    formal_seed_records: int,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    promising = [row for row in ranked_screens if row.get("promising_screen")]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "route_envelope_gate_not_rejected"
        next_work = None
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "beneficial_candidate_support_insufficient"
        next_work = None
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "harmful_candidate_support_insufficient"
        next_work = None
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_constrained_affine_screen_found"
        next_work = READY_NEXT_WORK
    else:
        status = REJECT_STATUS
        primary_gap = "constrained_affine_upper_bound_does_not_separate_candidates"
        next_work = "reject_observable_route_or_design_new_logging_preflight"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": len(promising),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _failure_gap(
    ranked_screens: list[dict[str, Any]],
    class_counts: dict[str, int],
    source: dict[str, Any],
    *,
    formal_seed_records: int,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
) -> dict[str, Any]:
    best = ranked_screens[0] if ranked_screens else None
    if not source["passed"]:
        primary = "route_envelope_gate_not_rejected"
    elif formal_seed_records:
        primary = "formal_seed_conflict"
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        primary = "beneficial_candidate_support_insufficient"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        primary = "harmful_candidate_support_insufficient"
    elif best is None:
        primary = "no_finite_constrained_affine_screen"
    elif best["harmful_block_rate"] < float(harmful_block_rate_target):
        primary = "harmful_block_rate_insufficient"
    elif best["beneficial_retain_rate"] < float(beneficial_retain_rate_target):
        primary = "beneficial_retain_rate_insufficient"
    elif best["allowed_harmful_rate"] > float(allowed_harmful_rate_target):
        primary = "allowed_harmful_rate_too_high"
    else:
        primary = "no_gap_promising_constrained_affine_screen_found"
    return {"primary_gap": primary, "best_screen": best}


def _descriptor_coverage(
    rows: list[dict[str, Any]],
    descriptors: list[RiskDescriptor],
) -> dict[str, Any]:
    return {
        descriptor.name: _coverage(rows, descriptor.name)
        for descriptor in descriptors
    }


def _coverage(rows: list[dict[str, Any]], feature_name: str) -> dict[str, int]:
    finite = [
        row for row in rows
        if feature_name in row["features"] and np.isfinite(float(row["features"][feature_name]))
    ]
    varied = len({round(float(row["features"][feature_name]), 12) for row in finite}) > 1
    return {
        "finite_rows": len(finite),
        "total_rows": len(rows),
        "has_variation": int(varied),
    }


def _descriptor_payload(descriptor: RiskDescriptor) -> dict[str, str]:
    return {
        "name": descriptor.name,
        "source_feature": descriptor.source_feature,
        "orientation": descriptor.orientation,
        "source_family": descriptor.source_family,
        "rationale": descriptor.rationale,
    }


def _top_screen_lines(report: dict[str, Any]) -> list[str]:
    screens = report.get("ranked_screens") or []
    if not screens:
        return ["No finite screen was available."]
    lines = []
    for idx, screen in enumerate(screens[:8], start=1):
        lines.append(
            f"{idx}. `{screen['screen_name']}` "
            f"harmful_block={screen['harmful_block_rate']:.6f}, "
            f"beneficial_retain={screen['beneficial_retain_rate']:.6f}, "
            f"allowed_harmful={screen['allowed_harmful_rate']:.6f}, "
            f"promising={screen['promising_screen']}"
        )
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Constrained Affine Upper-Bound Diagnostic",
        "",
        "This is a read-only offline oracle over already logged no-leak "
        "descriptors. It does not run DP, select online trajectories, train "
        "CAMP, or authorize replay.",
        "",
        "## Decision",
        "",
        f"status=`{decision['status']}`",
        f"passed=`{decision['passed']}`",
        f"primary_gap=`{decision['primary_gap']}`",
        f"authorized_next_work=`{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Oracle Search",
        "",
        "```json",
        json.dumps(report["analysis"]["oracle_search"], indent=2, sort_keys=True),
        "```",
        "",
        "## Top Screens",
        "",
        *_top_screen_lines(report),
        "",
        "## Failure Gap",
        "",
        "```json",
        json.dumps(report["failure_gap"], indent=2, sort_keys=True),
        "```",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
