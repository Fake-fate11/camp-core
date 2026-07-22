from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .diffusion_planner import atom_schema_for_dimension
from .diffusion_planner_causal_atoms import (
    canonical_normalize_atoms,
    validate_fixed_k8_candidate_tensor,
)
from .diffusion_planner_v25_context import (
    PHI_DIMENSION,
    V25ContextScaler,
    context_weights,
)
from .diffusion_planner_v25_scene_runtime import (
    MODEL_PARAMETER_SCHEMA_VERSION,
    V25Scene14DWeightProvider,
)


SCHEMA_VERSION = "camp_dp_v25_atom_calibration_evidence_v1"
GROUPS = {
    "jerk3": (0, 1, 2),
    "speed3": (4, 5, 6),
    "lane_clearance": (3, 7),
    "progress": (9,),
    "signal2": (10, 12),
    "lateral_acceleration": (11,),
    "dp_prior": (13,),
}


def analyze_calibration_decision_evidence(
    *,
    camp_runs: Sequence[Mapping[str, Any]],
    atom_scales: np.ndarray,
    static14d_weights: np.ndarray,
    scene14d_provider: V25Scene14DWeightProvider,
    training_artifact: Path,
) -> dict[str, Any]:
    scales = _numeric(atom_scales, (14,), "atom_scales")
    static14 = _simplex(static14d_weights, 14, "Static14D weights")
    ablations = _load_ablation_assets(training_artifact)
    atom_schema, atom_names = atom_schema_for_dimension(14)
    if len(atom_names) != 14:
        raise ValueError("atom calibration requires exactly 14 approved atoms")
    raw_by_atom: list[list[float]] = [[] for _ in range(14)]
    ranges: list[list[float]] = [[] for _ in range(14)]
    variances: list[list[float]] = [[] for _ in range(14)]
    source_counts = np.zeros(14, dtype=np.int64)
    applicable_counts = np.zeros(14, dtype=np.int64)
    total_candidate_rows = 0
    saturation_counts = np.zeros(14, dtype=np.int64)
    selection = {
        "official_tick_count": 0,
        "lowest_index_tie_count": 0,
        "producer_vs_diagnostic_layout_selected_flip_count": 0,
        "official_margins": [],
        "static9d_vs_static14d_flip_count": 0,
        "scene9d_vs_scene14d_flip_count": 0,
        "leave_one_atom_flip_count": [0 for _ in range(14)],
        "leave_group_flip_count": {name: 0 for name in GROUPS},
    }
    counts_by_arm: defaultdict[str, int] = defaultdict(int)
    event_family_tick_counts: defaultdict[str, int] = defaultdict(int)
    event_family_source_counts: defaultdict[str, np.ndarray] = defaultdict(
        lambda: np.zeros(14, dtype=np.int64)
    )
    event_family_applicable_counts: defaultdict[str, np.ndarray] = defaultdict(
        lambda: np.zeros(14, dtype=np.int64)
    )
    event_family_positive_counts: defaultdict[str, np.ndarray] = defaultdict(
        lambda: np.zeros(14, dtype=np.int64)
    )
    event_family_distinguishing_counts: defaultdict[str, np.ndarray] = defaultdict(
        lambda: np.zeros(14, dtype=np.int64)
    )
    phase_remaining_available_count = 0
    for run in camp_runs:
        plan_arm = run.get("plan_arm")
        if plan_arm not in {"camp_static14d", "camp_scene14d_no_v2i"}:
            raise ValueError("atom calibration received a non-CAMP arm")
        scenario_family = run.get("scenario_family")
        if type(scenario_family) is not str or not scenario_family:
            raise ValueError("atom calibration scenario family is missing")
        snapshots = run.get("snapshots")
        native_ticks = run.get("native_ticks")
        if (
            type(snapshots) is not list
            or len(snapshots) != 64
            or type(native_ticks) is not list
            or len(native_ticks) != 64
        ):
            raise ValueError("atom calibration requires 64 decision/tick rows per run")
        for tick_index, (snapshot, native_tick) in enumerate(
            zip(snapshots, native_ticks, strict=True)
        ):
            atoms, source, applicable, eligible, stored_scores, stored_index = (
                _decision_snapshot(snapshot, tick_index=tick_index)
            )
            if native_tick.get("tick_index") != tick_index:
                raise ValueError("atom calibration native tick order drifted")
            if (
                native_tick.get("scores") != snapshot["sidecar"]["scores"]
                or native_tick.get("selected_index") != stored_index
                or native_tick.get("source_valid_mask")
                != snapshot["sidecar"]["source_valid_mask"]
            ):
                raise ValueError("atom calibration snapshot/native selection drifted")
            normalized = canonical_normalize_atoms(atoms, scales)
            if plan_arm == "camp_static14d":
                weights = static14
                weights9 = ablations["static9d_weights"]
            else:
                context_payload = native_tick.get("v25_context")
                if type(context_payload) is not dict:
                    raise ValueError("Scene14D calibration context is missing")
                provided = scene14d_provider(context_payload)
                source_complete = context_payload.get("source_complete")
                if type(source_complete) is not dict:
                    raise ValueError("Scene14D source-complete context is missing")
                phase_remaining = source_complete.get(
                    "traffic_signal_phase_remaining_s"
                )
                if type(phase_remaining) is not bool:
                    raise ValueError("Scene14D phase-remaining source flag drifted")
                phase_remaining_available_count += int(phase_remaining)
                weights = _simplex(provided["weights"], 14, "Scene14D weights")
                selector_receipt = native_tick.get("v25_scene_selector")
                if (
                    type(selector_receipt) is not dict
                    or selector_receipt
                    != {key: value for key, value in provided.items() if key != "weights"}
                ):
                    raise ValueError("Scene14D calibration weight receipt drifted")
                weights9 = _scene9_weights(context_payload, ablations)
            official = normalized @ weights
            if not np.array_equal(official, stored_scores):
                raise ValueError("calibration stored scores drifted from producer layout")
            official_index = int(np.argmin(np.where(eligible, official, np.inf)))
            if official_index != stored_index:
                raise ValueError("calibration selected index drifted from affine argmin")
            alternate = np.einsum(
                "ka,a->k", normalized, weights, optimize=True, dtype=np.float64
            )
            alternate_index = int(
                np.argmin(np.where(eligible, alternate, np.inf))
            )
            selection["official_tick_count"] += 1
            selection["producer_vs_diagnostic_layout_selected_flip_count"] += int(
                alternate_index != official_index
            )
            eligible_scores = official[eligible]
            minimum = float(np.min(eligible_scores))
            ties = int(np.sum(eligible_scores == minimum))
            selection["lowest_index_tie_count"] += int(ties > 1)
            ordered = np.sort(eligible_scores)
            margin = 0.0 if ordered.size < 2 else float(ordered[1] - ordered[0])
            selection["official_margins"].append(margin)
            scores9 = normalized[:, :9] @ weights9
            selected9 = int(np.argmin(np.where(eligible, scores9, np.inf)))
            selection[
                "static9d_vs_static14d_flip_count"
                if plan_arm == "camp_static14d"
                else "scene9d_vs_scene14d_flip_count"
            ] += int(selected9 != official_index)
            for atom_index in range(14):
                ablated = _ablated_weights(weights, (atom_index,))
                if ablated is not None:
                    selected = int(
                        np.argmin(np.where(eligible, normalized @ ablated, np.inf))
                    )
                    selection["leave_one_atom_flip_count"][atom_index] += int(
                        selected != official_index
                    )
            for name, indices in GROUPS.items():
                ablated = _ablated_weights(weights, indices)
                if ablated is not None:
                    selected = int(
                        np.argmin(np.where(eligible, normalized @ ablated, np.inf))
                    )
                    selection["leave_group_flip_count"][name] += int(
                        selected != official_index
                    )

            total_candidate_rows += 8
            source_counts += source.sum(axis=0)
            applicable_counts += applicable.sum(axis=0)
            valid = source & applicable
            saturation_counts += ((normalized >= 10.0) & valid).sum(axis=0)
            event_family_tick_counts[scenario_family] += 1
            event_family_source_counts[scenario_family] += source.sum(axis=0)
            event_family_applicable_counts[scenario_family] += applicable.sum(axis=0)
            event_family_positive_counts[scenario_family] += (
                (atoms > 0.0) & valid
            ).sum(axis=0)
            for atom_index in range(14):
                values = atoms[valid[:, atom_index], atom_index]
                raw_by_atom[atom_index].extend(float(value) for value in values)
                candidate_values = atoms[:, atom_index]
                ranges[atom_index].append(
                    float(np.max(candidate_values) - np.min(candidate_values))
                )
                variances[atom_index].append(float(np.var(candidate_values)))
                event_family_distinguishing_counts[scenario_family][atom_index] += int(
                    float(np.max(candidate_values) - np.min(candidate_values)) > 0.0
                )
            counts_by_arm[str(plan_arm)] += 1

    atom_rows = []
    for index, name in enumerate(atom_names):
        values = np.asarray(raw_by_atom[index], dtype=np.float64)
        support = int(values.size)
        positive = int(np.sum(values > 0.0)) if support else 0
        atom_rows.append(
            {
                "index": index,
                "name": name,
                "paper_9d_subset": index < 9,
                "status": "PASS" if support > 0 else "WARN",
                "warning": None if support > 0 else "support_limited_in_calibration",
                "source_coverage": float(source_counts[index] / total_candidate_rows),
                "applicability_coverage": float(
                    applicable_counts[index] / total_candidate_rows
                ),
                "support_count": support,
                "zero_rate": None if not support else float(np.mean(values == 0.0)),
                "positive_rate": None if not support else positive / support,
                "q05": _quantile(values, 0.05),
                "q50": _quantile(values, 0.50),
                "q95": _quantile(values, 0.95),
                "q99": _quantile(values, 0.99),
                "k8_range_mean": float(np.mean(ranges[index])),
                "k8_variance_mean": float(np.mean(variances[index])),
                "clip_saturation_rate": (
                    0.0
                    if support == 0
                    else float(saturation_counts[index] / support)
                ),
                "training_scale": float(scales[index]),
                "calibration_positive_q95": (
                    None
                    if positive == 0
                    else float(np.quantile(values[values > 0.0], 0.95))
                ),
                "calibration_positive_q95_to_training_scale_ratio": (
                    None
                    if positive == 0
                    else float(
                        np.quantile(values[values > 0.0], 0.95) / scales[index]
                    )
                ),
                "scale_changed_by_calibration": False,
                "leave_one_atom_selected_flip_count": selection[
                    "leave_one_atom_flip_count"
                ][index],
            }
        )
    official_count = int(selection.pop("official_tick_count"))
    margins = np.asarray(selection.pop("official_margins"), dtype=np.float64)
    flip_count = int(
        selection["producer_vs_diagnostic_layout_selected_flip_count"]
    )
    selection.update(
        {
            "official_tick_count": official_count,
            "score_margin_q05": float(np.quantile(margins, 0.05)),
            "score_margin_q50": float(np.quantile(margins, 0.50)),
            "score_margin_q95": float(np.quantile(margins, 0.95)),
            "producer_vs_diagnostic_layout_selected_flip_rate": (
                flip_count / official_count
            ),
            "formal_results_use_diagnostic_layout": False,
        }
    )
    event_family_support = {}
    for family in sorted(event_family_tick_counts):
        ticks = event_family_tick_counts[family]
        candidate_rows = ticks * 8
        event_family_support[family] = {
            "decision_tick_count": ticks,
            "candidate_atom_row_count": candidate_rows,
            "source_coverage_by_atom": (
                event_family_source_counts[family] / candidate_rows
            ).astype(float).tolist(),
            "applicability_coverage_by_atom": (
                event_family_applicable_counts[family] / candidate_rows
            ).astype(float).tolist(),
            "positive_count_by_atom": event_family_positive_counts[family].tolist(),
            "k8_distinguishing_tick_count_by_atom": (
                event_family_distinguishing_counts[family].tolist()
            ),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "completed_train_frozen_calibration_atom_audit",
        "atom_schema_version": atom_schema,
        "atom_count": 14,
        "paper_9d_subset_indices": list(range(9)),
        "candidate_count": 8,
        "decision_tick_count_by_arm": dict(sorted(counts_by_arm.items())),
        "decision_tick_count": official_count,
        "candidate_atom_row_count": total_candidate_rows,
        "atoms": atom_rows,
        "event_family_support": event_family_support,
        "selection_sensitivity": selection,
        "weak_support_deletes_atom": False,
        "red_without_legal_source": "unavailable_masked_not_continuous_floor",
        "producer_layout_frozen_for_formal_selection": True,
        "phase_remaining_available_count": phase_remaining_available_count,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def _decision_snapshot(
    value: Mapping[str, Any], *, tick_index: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    if type(value) is not dict or set(value) != {
        "schema_version",
        "feature_payload",
        "sidecar",
    } or value.get("schema_version") != "v22_native_decision_snapshot_v1":
        raise ValueError("calibration decision snapshot schema drifted")
    feature = value["feature_payload"]
    sidecar = value["sidecar"]
    if type(feature) is not dict or type(sidecar) is not dict:
        raise ValueError("calibration decision snapshot payload drifted")
    atoms = _numeric(feature.get("atom_matrix"), (8, 14), "atom_matrix")
    if np.any(atoms < 0.0):
        raise ValueError("calibration atoms must be nonnegative")
    candidates = _numeric(
        feature.get("candidate_tensor"), (8, 80, 4), "candidate_tensor"
    ).astype(np.float32)
    validate_fixed_k8_candidate_tensor(candidates)
    source = _bool_array(feature.get("atom_source_valid_mask"), (8, 14))
    applicable = _bool_array(feature.get("atom_applicable_mask"), (8, 14))
    eligible = _bool_array(feature.get("source_valid_mask"), (8,))
    if not eligible.any() or np.any(applicable & ~source):
        raise ValueError("calibration decision source/applicability drifted")
    scores = _numeric(sidecar.get("scores"), (8,), "scores")
    selected = sidecar.get("selected_index")
    if (
        sidecar.get("tick_index") != tick_index
        or type(selected) is not int
        or not 0 <= selected < 8
        or not eligible[selected]
        or sidecar.get("score_contract")
        != "score_k=clip(a_k/s,0,10)^T w"
        or sidecar.get("tie_break_contract") != "lowest_eligible_candidate_index"
    ):
        raise ValueError("calibration decision selection contract drifted")
    return atoms, source, applicable, eligible, scores, selected


def _load_ablation_assets(training_artifact: Path) -> dict[str, Any]:
    path = Path(training_artifact).resolve() / "model_parameters.npz"
    with np.load(path, allow_pickle=False) as archive:
        schema = np.asarray(archive["schema_version"])
        q05 = _numeric(archive["context_q05"], (26,), "context_q05")
        q95 = _numeric(archive["context_q95"], (26,), "context_q95")
        static9 = _simplex(
            archive["static9d_runtime_weights"], 9, "Static9D weights"
        )
        scene9 = _numeric(
            archive["scene9d_theta"], (9, PHI_DIMENSION), "Scene9D theta"
        )
    if schema.shape != () or str(schema.item()) != MODEL_PARAMETER_SCHEMA_VERSION:
        raise ValueError("calibration ablation model parameter schema drifted")
    if np.any(scene9 < 0.0) or not np.allclose(
        scene9.sum(axis=0), 1.0, rtol=0.0, atol=1e-10
    ):
        raise ValueError("Scene9D theta is not column-simplex")
    return {
        "static9d_weights": static9,
        "scene9d_theta": scene9,
        "context_scaler": V25ContextScaler(q05=q05, q95=q95),
    }


def _scene9_weights(
    context_payload: Mapping[str, Any], ablations: Mapping[str, Any]
) -> np.ndarray:
    raw_context = context_payload.get("raw_context")
    source_complete = context_payload.get("source_complete")
    if type(raw_context) is not dict or type(source_complete) is not dict:
        raise ValueError("Scene9D context payload drifted")
    from .diffusion_planner_v25_context import RAW_FEATURE_NAMES

    raw = np.asarray([raw_context[name] for name in RAW_FEATURE_NAMES], dtype=np.float64)
    source = np.asarray(
        [source_complete[name] for name in RAW_FEATURE_NAMES], dtype=np.bool_
    )
    phi = ablations["context_scaler"].lift(raw, source_complete=source)
    return _simplex(
        context_weights(ablations["scene9d_theta"], phi), 9, "Scene9D weights"
    )


def _ablated_weights(weights: np.ndarray, indices: tuple[int, ...]) -> np.ndarray | None:
    result = np.asarray(weights, dtype=np.float64).copy()
    result[list(indices)] = 0.0
    mass = float(result.sum())
    if not np.isfinite(mass) or mass <= 0.0:
        return None
    return result / mass


def _numeric(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError(f"{name} must be native numeric {shape}")
    result = raw.astype(np.float64, copy=False)
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must be finite")
    return result


def _simplex(value: Any, size: int, name: str) -> np.ndarray:
    result = _numeric(value, (size,), name)
    if np.any(result < 0.0) or not np.isclose(
        result.sum(), 1.0, rtol=0.0, atol=1e-10
    ):
        raise ValueError(f"{name} must be a nonnegative simplex")
    return result


def _bool_array(value: Any, shape: tuple[int, ...]) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype != np.bool_:
        raise ValueError(f"mask must be strict bool {shape}")
    return raw


def _quantile(values: np.ndarray, q: float) -> float | None:
    return None if values.size == 0 else float(np.quantile(values, q))
