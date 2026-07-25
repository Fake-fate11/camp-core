"""Additive, read-only summary for the V25 fair-pool adaptation hard stop."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

import numpy as np


SCHEMA_VERSION = "camp_dp_v25_fair_nonholdout_adaptation_summary_v1"
SOURCE_SCHEMA = "camp_dp_v25_fair_nonholdout_validation_v1"
ATOL = 1e-5
RTOL = 1e-5
STATE_COUNT = 16
ROW_COUNT = 8
ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
ARMS = ("Static14D", "Scene14D")
PRIMARY_TAXONOMY_PRIORITY = (
    "nonfinite_or_nondiverse",
    "repeat_nondeterminism",
    "trajectory_tolerance",
    "neighbor_tolerance",
    "mask",
    "Static14D_flip",
    "Scene14D_flip",
    "post_pool_call",
    "tensor_mutation",
    "no_failure",
)
EXPECTED_ARRAYS = frozenset(
    {
        "primary_candidates",
        "sequential_candidates",
        "primary_neighbors",
        "sequential_neighbors",
        "primary_atoms",
        "sequential_atoms",
        "primary_source_masks",
        "sequential_source_masks",
        "primary_physical_masks",
        "sequential_physical_masks",
        "atom_scales",
        "static_weights",
    }
)


def _array_sha256(value: Any) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype.hasobject:
        raise ValueError("object arrays are forbidden")
    return hashlib.sha256(array.tobytes()).hexdigest()


def _plain_object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _scores(
    atoms: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
    source_mask: np.ndarray,
) -> tuple[np.ndarray, int]:
    atoms = np.asarray(atoms, dtype=np.float64)
    scales = np.asarray(scales, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    source_mask = np.asarray(source_mask)
    if (
        atoms.shape != (ROW_COUNT, len(ATOM_NAMES))
        or scales.shape != (len(ATOM_NAMES),)
        or weights.shape != (len(ATOM_NAMES),)
        or source_mask.shape != (ROW_COUNT,)
        or source_mask.dtype != np.bool_
        or not np.isfinite(atoms).all()
        or not np.isfinite(scales).all()
        or not np.isfinite(weights).all()
        or np.any(scales <= 0.0)
        or np.any(weights < -1e-12)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-8)
        or not source_mask.any()
    ):
        raise ValueError("score preimage contract failed")
    values = np.clip(atoms / scales, 0.0, 10.0) @ weights
    return values, int(np.argmin(np.where(source_mask, values, np.inf)))


def _row_allclose(left: np.ndarray, right: np.ndarray) -> list[bool]:
    return [
        bool(np.allclose(left[row], right[row], atol=ATOL, rtol=RTOL))
        for row in range(ROW_COUNT)
    ]


def _k8_validity(candidates: np.ndarray, neighbors: np.ndarray) -> dict[str, Any]:
    candidate_row_finite = [
        bool(np.isfinite(candidates[row]).all()) for row in range(ROW_COUNT)
    ]
    neighbor_row_finite = [
        bool(np.isfinite(neighbors[row]).all()) for row in range(ROW_COUNT)
    ]
    row_sha256 = [_array_sha256(candidates[row]) for row in range(ROW_COUNT)]
    unique_row_count = len(set(row_sha256))
    return {
        "candidate_row_finite": candidate_row_finite,
        "neighbor_row_finite": neighbor_row_finite,
        "candidate_row_sha256": row_sha256,
        "unique_candidate_row_count": unique_row_count,
        "finite": all(candidate_row_finite) and all(neighbor_row_finite),
        "diverse": unique_row_count == ROW_COUNT,
        "valid": (
            all(candidate_row_finite)
            and all(neighbor_row_finite)
            and unique_row_count == ROW_COUNT
        ),
    }


def _validate_arrays(arrays: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    if set(arrays) != EXPECTED_ARRAYS:
        raise ValueError("numeric preimage inventory drifted")
    copied = {name: np.asarray(value) for name, value in arrays.items()}
    shapes = {
        "primary_candidates": (STATE_COUNT, ROW_COUNT, 80, 4),
        "sequential_candidates": (STATE_COUNT, ROW_COUNT, 80, 4),
        "primary_neighbors": (STATE_COUNT, ROW_COUNT, 32, 80, 4),
        "sequential_neighbors": (STATE_COUNT, ROW_COUNT, 32, 80, 4),
        "primary_atoms": (STATE_COUNT, ROW_COUNT, len(ATOM_NAMES)),
        "sequential_atoms": (STATE_COUNT, ROW_COUNT, len(ATOM_NAMES)),
        "primary_source_masks": (STATE_COUNT, ROW_COUNT),
        "sequential_source_masks": (STATE_COUNT, ROW_COUNT),
        "primary_physical_masks": (STATE_COUNT, ROW_COUNT),
        "sequential_physical_masks": (STATE_COUNT, ROW_COUNT),
        "atom_scales": (len(ATOM_NAMES),),
        "static_weights": (len(ATOM_NAMES),),
    }
    for name, shape in shapes.items():
        if copied[name].shape != shape:
            raise ValueError(f"{name} shape drifted")
    for name in (
        "primary_source_masks",
        "sequential_source_masks",
        "primary_physical_masks",
        "sequential_physical_masks",
    ):
        if copied[name].dtype != np.bool_:
            raise ValueError(f"{name} dtype drifted")
    return copied


def build_summary(
    source_report: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> dict[str, Any]:
    """Reconstruct the omitted adaptation evidence from sealed preimages."""

    report = _plain_object(source_report, "source report")
    if (
        report.get("schema_version") != SOURCE_SCHEMA
        or report.get("status")
        != "blocked_fair_nonholdout_engineering_validation"
    ):
        raise ValueError("source validation is not the accepted hard-stop artifact")
    replay = _plain_object(report.get("state_matched_replay"), "state replay")
    receipts = replay.get("receipts")
    if (
        replay.get("state_count") != STATE_COUNT
        or type(receipts) is not list
        or len(receipts) != STATE_COUNT
    ):
        raise ValueError("source state denominator drifted")
    a = _validate_arrays(arrays)
    scales = np.asarray(a["atom_scales"], dtype=np.float64)
    static_weights = np.asarray(a["static_weights"], dtype=np.float64)
    state_rows: list[dict[str, Any]] = []
    primary_taxonomy_counts = {name: 0 for name in PRIMARY_TAXONOMY_PRIORITY}
    indicator_state_counts = {
        name: 0 for name in PRIMARY_TAXONOMY_PRIORITY if name != "no_failure"
    }
    indicator_row_counts = {
        "nonfinite_or_nondiverse": 0,
        "trajectory_tolerance": 0,
        "neighbor_tolerance": 0,
        "mask": 0,
    }
    atom_exact_count = 0
    atom_max_abs = 0.0
    atom_aggregate = [
        {"atom_index": index, "atom_name": name, "exact_count": 0, "max_abs_diff": 0.0}
        for index, name in enumerate(ATOM_NAMES)
    ]
    score_exact_counts = {arm: 0 for arm in ARMS}
    score_max_abs = {arm: 0.0 for arm in ARMS}
    selected_flip_counts = {arm: 0 for arm in ARMS}
    k8_valid_state_counts = {"primary": 0, "sequential": 0}

    for state_index, receipt_raw in enumerate(receipts):
        receipt = _plain_object(receipt_raw, f"receipt {state_index}")
        adaptation = _plain_object(receipt.get("adaptation"), "adaptation")
        sequential_summary = _plain_object(
            adaptation.get("sequential"), "sequential summary"
        )
        primary_atoms = np.asarray(a["primary_atoms"][state_index], dtype=np.float64)
        sequential_atoms = np.asarray(
            a["sequential_atoms"][state_index], dtype=np.float64
        )
        atom_delta = primary_atoms - sequential_atoms
        atom_abs = np.abs(atom_delta)
        atom_exact = atom_delta == 0.0
        atom_rows = []
        for row in range(ROW_COUNT):
            atom_rows.append(
                {
                    "row_index": row,
                    "exact_equal_atom_count": int(np.count_nonzero(atom_exact[row])),
                    "nonexact_atom_count": int(
                        len(ATOM_NAMES) - np.count_nonzero(atom_exact[row])
                    ),
                    "max_abs_diff": float(np.max(atom_abs[row])),
                    "per_atom_signed_diff": atom_delta[row].tolist(),
                    "per_atom_abs_diff": atom_abs[row].tolist(),
                    "per_atom_exact_equal": atom_exact[row].tolist(),
                }
            )
        atom_exact_count += int(np.count_nonzero(atom_exact))
        atom_max_abs = max(atom_max_abs, float(np.max(atom_abs)))
        for atom_index, aggregate in enumerate(atom_aggregate):
            aggregate["exact_count"] += int(
                np.count_nonzero(atom_exact[:, atom_index])
            )
            aggregate["max_abs_diff"] = max(
                float(aggregate["max_abs_diff"]),
                float(np.max(atom_abs[:, atom_index])),
            )

        primary_source = np.asarray(a["primary_source_masks"][state_index])
        sequential_source = np.asarray(a["sequential_source_masks"][state_index])
        primary_physical = np.asarray(a["primary_physical_masks"][state_index])
        sequential_physical = np.asarray(
            a["sequential_physical_masks"][state_index]
        )
        source_diff_rows = np.flatnonzero(primary_source != sequential_source).tolist()
        physical_diff_rows = np.flatnonzero(
            primary_physical != sequential_physical
        ).tolist()
        mask_diff_rows = sorted(set(source_diff_rows + physical_diff_rows))
        score_rows: dict[str, Any] = {}
        selected_flips: dict[str, bool] = {}
        for arm in ARMS:
            if arm == "Static14D":
                primary_weights = sequential_weights = static_weights
            else:
                primary_weights = np.asarray(
                    receipt["materialized_summary"]["scene_weights"],
                    dtype=np.float64,
                )
                sequential_weights = np.asarray(
                    sequential_summary["scene_weights"], dtype=np.float64
                )
            primary_scores, primary_selected = _scores(
                primary_atoms, scales, primary_weights, primary_source
            )
            sequential_scores, sequential_selected = _scores(
                sequential_atoms, scales, sequential_weights, sequential_source
            )
            produced = _plain_object(
                receipt["real_selector_receipts"][arm], f"{arm} receipt"
            )
            if (
                produced.get("selected_index") != primary_selected
                or not np.allclose(
                    np.asarray(produced.get("scores"), dtype=np.float64),
                    primary_scores,
                    rtol=0.0,
                    atol=1e-12,
                )
            ):
                raise ValueError(f"{arm} source score binding drifted")
            signed = primary_scores - sequential_scores
            absolute = np.abs(signed)
            exact = signed == 0.0
            flip = primary_selected != sequential_selected
            score_exact_counts[arm] += int(np.count_nonzero(exact))
            score_max_abs[arm] = max(score_max_abs[arm], float(np.max(absolute)))
            selected_flip_counts[arm] += int(flip)
            selected_flips[arm] = flip
            score_rows[arm] = {
                "primary_scores": primary_scores.tolist(),
                "sequential_scores": sequential_scores.tolist(),
                "signed_diff": signed.tolist(),
                "abs_diff": absolute.tolist(),
                "exact_equal": exact.tolist(),
                "max_abs_diff": float(np.max(absolute)),
                "primary_selected_index": primary_selected,
                "sequential_selected_index": sequential_selected,
                "selected_index_flip": flip,
                "primary_source_mask": primary_source.tolist(),
                "sequential_source_mask": sequential_source.tolist(),
                "primary_physical_mask": primary_physical.tolist(),
                "sequential_physical_mask": sequential_physical.tolist(),
            }

        primary_k8 = _k8_validity(
            a["primary_candidates"][state_index],
            a["primary_neighbors"][state_index],
        )
        sequential_k8 = _k8_validity(
            a["sequential_candidates"][state_index],
            a["sequential_neighbors"][state_index],
        )
        k8_valid_state_counts["primary"] += int(primary_k8["valid"])
        k8_valid_state_counts["sequential"] += int(sequential_k8["valid"])
        trajectory_ok = _row_allclose(
            a["primary_candidates"][state_index],
            a["sequential_candidates"][state_index],
        )
        neighbor_ok = _row_allclose(
            a["primary_neighbors"][state_index],
            a["sequential_neighbors"][state_index],
        )
        zero = _plain_object(receipt.get("zero_call_receipt"), "zero-call receipt")
        post_pool_call_count = sum(
            int(zero.get(name, -1))
            for name in (
                "dp_or_model_calls_after_pool",
                "latent_replacements_after_pool",
                "candidate_generations_after_pool",
            )
        )
        tensor_mutation = (
            receipt.get("candidate_tensor_sha256_before")
            != receipt.get("candidate_tensor_sha256_after")
        )
        indicators = {
            "nonfinite_or_nondiverse": not (
                primary_k8["valid"] and sequential_k8["valid"]
            ),
            "repeat_nondeterminism": adaptation.get("repeat_exact_equal") is not True,
            "trajectory_tolerance": not all(trajectory_ok),
            "neighbor_tolerance": not all(neighbor_ok),
            "mask": bool(mask_diff_rows),
            "Static14D_flip": selected_flips["Static14D"],
            "Scene14D_flip": selected_flips["Scene14D"],
            "post_pool_call": post_pool_call_count != 0,
            "tensor_mutation": tensor_mutation,
        }
        primary_failure = next(
            (
                name
                for name in PRIMARY_TAXONOMY_PRIORITY
                if name != "no_failure" and indicators[name]
            ),
            "no_failure",
        )
        primary_taxonomy_counts[primary_failure] += 1
        for name, present in indicators.items():
            indicator_state_counts[name] += int(present)
        indicator_row_counts["nonfinite_or_nondiverse"] += sum(
            not value
            for value in (
                primary_k8["candidate_row_finite"]
                + primary_k8["neighbor_row_finite"]
                + sequential_k8["candidate_row_finite"]
                + sequential_k8["neighbor_row_finite"]
            )
        )
        indicator_row_counts["trajectory_tolerance"] += sum(not x for x in trajectory_ok)
        indicator_row_counts["neighbor_tolerance"] += sum(not x for x in neighbor_ok)
        indicator_row_counts["mask"] += len(mask_diff_rows)
        state_rows.append(
            {
                "state_index": state_index,
                "tick_index": receipt.get("tick_index"),
                "state_sha256": receipt.get("state_sha256"),
                "pool_id": receipt.get("pool_id"),
                "atom_differences": atom_rows,
                "score_differences": score_rows,
                "mask_differences": {
                    "source_row_indices": source_diff_rows,
                    "physical_row_indices": physical_diff_rows,
                    "any_difference": bool(mask_diff_rows),
                },
                "k8_validity": {
                    "primary": primary_k8,
                    "sequential": sequential_k8,
                },
                "trajectory_within_tolerance": trajectory_ok,
                "neighbor_within_tolerance": neighbor_ok,
                "post_pool_forbidden_call_count": post_pool_call_count,
                "candidate_tensor_mutated": tensor_mutation,
                "failure_indicators": indicators,
                "primary_failure_class": primary_failure,
            }
        )

    if sum(primary_taxonomy_counts.values()) != STATE_COUNT:
        raise AssertionError("primary failure taxonomy is not exhaustive")
    source_audit = _plain_object(
        report.get("pool_distribution_adaptation_audit"), "source adaptation audit"
    )
    if (
        source_audit.get("trajectory_row_denominator") != 128
        or source_audit.get("neighbor_row_denominator") != 128
        or source_audit.get("trajectory_equivalent_row_count") != 128
        or source_audit.get("neighbor_equivalent_row_count") != 114
        or source_audit.get("substantive_drift_state_count") != 9
        or indicator_row_counts["trajectory_tolerance"] != 0
        or indicator_row_counts["neighbor_tolerance"] != 14
        or sum(
            count
            for name, count in primary_taxonomy_counts.items()
            if name != "no_failure"
        )
        != 9
    ):
        raise ValueError("accepted hard-stop denominator or classification drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "sealed_additive_adaptation_summary_hard_stop_preserved",
        "source_schema_version": SOURCE_SCHEMA,
        "state_count": STATE_COUNT,
        "candidate_row_denominator": STATE_COUNT * ROW_COUNT,
        "atom_value_denominator": STATE_COUNT * ROW_COUNT * len(ATOM_NAMES),
        "score_value_denominator_per_arm": STATE_COUNT * ROW_COUNT,
        "atom_names": list(ATOM_NAMES),
        "frozen_tolerance": {"atol": ATOL, "rtol": RTOL},
        "state_summaries": state_rows,
        "aggregates": {
            "atom_exact_equal_count": atom_exact_count,
            "atom_nonexact_count": (
                STATE_COUNT * ROW_COUNT * len(ATOM_NAMES) - atom_exact_count
            ),
            "atom_global_max_abs_diff": atom_max_abs,
            "per_atom": atom_aggregate,
            "score_exact_equal_count": score_exact_counts,
            "score_nonexact_count": {
                arm: STATE_COUNT * ROW_COUNT - score_exact_counts[arm]
                for arm in ARMS
            },
            "score_global_max_abs_diff": score_max_abs,
            "selected_index_flip_state_count": selected_flip_counts,
            "mask_difference_state_count": indicator_state_counts["mask"],
            "k8_valid_state_count": k8_valid_state_counts,
            "primary_failure_taxonomy_priority": list(PRIMARY_TAXONOMY_PRIORITY),
            "primary_failure_taxonomy_state_count": primary_taxonomy_counts,
            "failure_indicator_state_count": indicator_state_counts,
            "failure_indicator_row_count": indicator_row_counts,
        },
        "interpretation": {
            "atom_and_score_difference_threshold_added": False,
            "atom_and_score_differences_are_exact_and_absolute_descriptive": True,
            "hard_stop_preserved": True,
            "classification": (
                "overconservative_equivalence_contract_triggered; "
                "functional adaptation risk unresolved"
            ),
            "hard_stop_proves_only_frozen_neighbor_tolerance_rule_triggered": True,
            "neighbor_equivalent_rows": 114,
            "neighbor_row_denominator": 128,
            "substantive_drift_state_count": 9,
            "ego_trajectory_equivalent_rows": 128,
            "ego_trajectory_row_denominator": 128,
            "mask_equal_state_count": 16,
            "static_selected_index_equal_state_count": 16,
            "scene_selected_index_equal_state_count": 16,
            "selector_functional_selection_drift_observed_in_16_states": False,
            "batch8_architecture_failure_proven": False,
            "model_failure_proven": False,
            "training_distribution_or_ood_drift_proven": False,
            "retraining_required_proven": False,
            "closed_loop_started": False,
            "closed_loop_arm_count": 0,
            "closed_loop_tick_count": 0,
            "legacy_source_possible_training_pool_adaptation_required": True,
            "legacy_source_field_is_overconservative_contract_field_not_scientific_conclusion": True,
            "functional_adaptation_risk": "unresolved",
            "retraining_decision": "undecided_not_authorized",
        },
    }
