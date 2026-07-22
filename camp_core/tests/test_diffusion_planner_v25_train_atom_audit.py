from __future__ import annotations

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (
    ATOM_COUNT,
    ATOM_NAMES,
    DEFAULT_ABLATION_GROUPS,
    build_train_only_causal_labels,
    compute_train_atom_audit,
    fit_train_only_atom_scales,
    hierarchical_snapshot_weights,
    weighted_quantile,
)


def _fixture(
    snapshots: int = 4,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw = np.empty((snapshots, 8, ATOM_COUNT), dtype=np.float64)
    for record in range(snapshots):
        for candidate in range(8):
            raw[record, candidate] = (
                np.arange(1, ATOM_COUNT + 1, dtype=np.float64)
                * (1.0 + 0.1 * record + 0.03 * candidate)
            )
    raw[:, :, 2] = raw[:, :, 0] + raw[:, :, 1]
    raw[:, :, 9] = np.arange(7, -1, -1, dtype=np.float64)[None, :]
    raw[:, :, 13] = np.arange(8, dtype=np.float64)[None, :]
    atom_source = np.ones(raw.shape, dtype=np.bool_)
    source = np.all(atom_source, axis=2)
    applicable = np.ones(raw.shape, dtype=np.bool_)
    physical = np.ones(raw.shape[:2], dtype=np.bool_)
    return raw, source, atom_source, applicable, physical


def test_hierarchical_snapshot_weights_are_route_block_seed_tick_macro_equal() -> None:
    weights = hierarchical_snapshot_weights(
        ["route-a", "route-a", "route-a", "route-b"],
        ["block-1", "block-1", "block-2", "block-3"],
        [25001, 25001, 25001, 25001],
        [0, 1, 0, 0],
    )
    np.testing.assert_allclose(weights, [0.125, 0.125, 0.25, 0.5], rtol=0.0, atol=1e-12)
    assert float(weights.sum()) == pytest.approx(1.0)


def test_hierarchical_snapshot_weights_share_duplicate_tick_leaf() -> None:
    weights = hierarchical_snapshot_weights(
        ["route", "route"],
        ["block", "block"],
        [25001, 25001],
        [7, 7],
    )
    np.testing.assert_allclose(weights, [0.5, 0.5], rtol=0.0, atol=0.0)


@pytest.mark.parametrize(
    ("values", "weights", "quantile", "expected"),
    [
        ([1.0, 2.0, 9.0], [0.8, 0.1, 0.1], 0.50, 1.0),
        ([1.0, 2.0, 9.0], [0.8, 0.1, 0.1], 0.95, 9.0),
        ([3.0, 1.0, 2.0], [0.2, 0.5, 0.3], 0.50, 1.0),
    ],
)
def test_weighted_quantile_uses_frozen_inverse_empirical_cdf(
    values: list[float], weights: list[float], quantile: float, expected: float
) -> None:
    assert weighted_quantile(
        np.asarray(values, dtype=np.float64),
        np.asarray(weights, dtype=np.float64),
        quantile,
    ) == expected


def test_train_scales_use_positive_applicable_support_and_keep_red_binary_alternative() -> None:
    raw, source, atom_source, applicable, _physical = _fixture(2)
    raw[0, :, 10] = 0.0
    applicable[0, :, 10] = False
    raw[0, :, 12] = 0.0
    applicable[0, :, 12] = False
    result = fit_train_only_atom_scales(
        raw,
        source,
        atom_source,
        applicable,
        np.asarray([0.5, 0.5], dtype=np.float64),
        ["block-a", "block-b"],
        minimum_positive_rows=1,
        minimum_positive_blocks=1,
    )
    assert result["schema_version"] == "camp_dp_v25_train_only_atom_scales_v2"
    assert np.all(np.isfinite(result["scales"]))
    assert np.all(result["scales"] > 0.0)
    planned = result["atom_rows"][10]
    stopping = result["atom_rows"][12]
    assert planned["positive_candidate_row_count"] == 8
    assert stopping["positive_candidate_row_count"] == 8
    assert planned["red_binary_alternative_scale"] == 1.0
    assert stopping["red_binary_alternative_scale"] == 1.0
    assert all(row["generation_floor_used_as_training_scale"] is False for row in result["atom_rows"])


def test_train_scales_warn_without_silently_dropping_support_limited_atom() -> None:
    raw, source, atom_source, applicable, _physical = _fixture(1)
    raw[:, :, 12] = 0.0
    result = fit_train_only_atom_scales(
        raw,
        source,
        atom_source,
        applicable,
        np.asarray([1.0], dtype=np.float64),
        ["block"],
        minimum_positive_rows=2,
        minimum_positive_blocks=1,
    )
    stopping = result["atom_rows"][12]
    assert stopping["status"] == "WARN"
    assert stopping["warning"] == "support_limited"
    assert stopping["training_scale"] == 1.0
    assert stopping["training_scale_estimator"] == "masked_zero_support_neutral_unit_scale"
    assert stopping["training_scale_is_empirical"] is False
    assert result["scales"][12] == 1.0
    assert len(result["atom_rows"]) == 14


def test_support_limited_red_uses_binary_not_continuous_generation_floor() -> None:
    raw, source, atom_source, applicable, _physical = _fixture(1)
    raw[:, :, 12] = 0.0004952895923795447
    result = fit_train_only_atom_scales(
        raw,
        source,
        atom_source,
        applicable,
        np.asarray([1.0], dtype=np.float64),
        ["block"],
        minimum_positive_rows=100,
        minimum_positive_blocks=20,
    )
    row = result["atom_rows"][12]
    assert row["positive_quantile_scale"] == pytest.approx(0.0004952895923795447)
    assert row["training_scale"] == 1.0
    assert row["training_scale_estimator"] == "support_limited_red_binary_scale"
    assert row["generation_floor_used_as_training_scale"] is False


def test_causal_labels_use_source_valid_lowest_index_and_physical_penalty() -> None:
    raw, source, atom_source, applicable, physical = _fixture(1)
    raw[:] = 0.0
    raw[0, 0, 4] = 5.0
    physical[0, 1] = False
    labels = build_train_only_causal_labels(
        raw,
        source,
        atom_source,
        applicable,
        physical,
        np.ones(ATOM_COUNT, dtype=np.float64),
    )
    assert labels["oracle_indices"].tolist() == [2]
    assert labels["candidate_costs"][0, 1] == 100.0
    assert labels["candidate_costs"][0, 2] == 0.0
    assert labels["margins"][0, 2] == 0.0
    assert labels["margins"][0, 1] == 2.0


def test_causal_labels_fail_closed_on_empty_source_valid_set() -> None:
    raw, _source, atom_source, applicable, physical = _fixture(1)
    atom_source[:] = False
    source = np.all(atom_source, axis=2)
    applicable[:] = False
    physical[:] = False
    with pytest.raises(ValueError, match="nonempty source-valid"):
        build_train_only_causal_labels(
            raw,
            source,
            atom_source,
            applicable,
            physical,
            np.ones(ATOM_COUNT, dtype=np.float64),
        )


@pytest.mark.parametrize("bad", [0, 1, 1.0, "true", None])
def test_audit_rejects_non_boolean_source_mask_elements(bad: object) -> None:
    raw, source, atom_source, applicable, physical = _fixture(1)
    source_values = source.astype(object)
    source_values[0, 0] = bad
    with pytest.raises(ValueError, match="source_valid_mask must be native bool"):
        compute_train_atom_audit(
            raw,
            source_values,
            atom_source,
            applicable,
            physical,
            np.ones(1, dtype=np.float64),
            ["block"],
            ["route"],
            ["family/tier"],
            np.ones(ATOM_COUNT, dtype=np.float64),
            minimum_positive_rows=1,
            minimum_positive_blocks=1,
        )


def test_audit_requires_source_valid_to_equal_atom_source_conjunction() -> None:
    raw, source, atom_source, applicable, physical = _fixture(1)
    source[0, 3] = False
    with pytest.raises(ValueError, match="atom-source conjunction"):
        compute_train_atom_audit(
            raw,
            source,
            atom_source,
            applicable,
            physical,
            np.ones(1, dtype=np.float64),
            ["block"],
            ["route"],
            ["family/tier"],
            np.ones(ATOM_COUNT, dtype=np.float64),
            minimum_positive_rows=1,
            minimum_positive_blocks=1,
        )


def test_train_atom_audit_reports_14d_9d_groups_rank_and_label_minus_atom() -> None:
    raw, source, atom_source, applicable, physical = _fixture(4)
    physical[3] = False
    weights = hierarchical_snapshot_weights(
        ["route-a", "route-a", "route-a", "route-b"],
        ["block-1", "block-1", "block-2", "block-3"],
        [25001, 25001, 25001, 25001],
        [0, 1, 0, 0],
    )
    report = compute_train_atom_audit(
        raw,
        source,
        atom_source,
        applicable,
        physical,
        weights,
        ["block-1", "block-1", "block-2", "block-3"],
        ["route-a", "route-a", "route-a", "route-b"],
        ["lead/easy", "lead/easy", "lead/high", "red/high"],
        np.ones(ATOM_COUNT, dtype=np.float64),
        generation_scales=np.full(ATOM_COUNT, 2.0, dtype=np.float64),
        minimum_positive_rows=1,
        minimum_positive_blocks=1,
    )
    assert report["schema_version"] == "camp_dp_v25_train_only_atom_empirical_audit_v1"
    assert report["paper_9d_prefix_indices"] == list(range(9))
    assert report["snapshot_count"] == 4
    assert report["candidate_count"] == 32
    assert report["all_k_high_risk_snapshot_count"] == 1
    assert len(report["atom_rows"]) == 14
    assert all(row["status"] == "PASS" for row in report["atom_rows"])
    assert all("spearman_with_label_minus_atom" in row for row in report["atom_rows"])
    assert all(
        "spearman_with_full_label_disclosed_direct_component" in row
        for row in report["atom_rows"]
    )
    assert all(
        row["candidate_distinction"]["eligible_snapshot_count"] == 4
        for row in report["atom_rows"]
    )
    assert all(
        row["candidate_distinction"]["positive_range_weight"] == pytest.approx(1.0)
        for row in report["atom_rows"]
    )
    assert all(
        len(row["family_tier_route_drift"]["family_tier_rows"]) == 3
        and row["family_tier_route_drift"]["route_group_count"] == 2
        for row in report["atom_rows"]
    )
    assert np.asarray(report["weighted_spearman_correlation_matrix"]).shape == (14, 14)
    assert report["atom_delta_effective_rank"]["candidate_delta_row_count"] == 32
    comparisons = report["ablations"]["comparisons"]
    assert "paper_9d_vs_14d" in comparisons
    assert all(f"14d_minus_{name}" in comparisons for name in ATOM_NAMES)
    assert all(
        f"14d_minus_group_{name}" in comparisons for name in DEFAULT_ABLATION_GROUPS
    )
    assert report["status_counts"] == {"PASS": 14, "WARN": 0, "FAIL": 0}
    assert report["fresh_or_outcome_consumed"] is False


def test_training_and_generation_scales_remain_separate_in_audit() -> None:
    raw, source, atom_source, applicable, physical = _fixture(1)
    report = compute_train_atom_audit(
        raw,
        source,
        atom_source,
        applicable,
        physical,
        np.ones(1, dtype=np.float64),
        ["block"],
        ["route"],
        ["family/tier"],
        np.full(ATOM_COUNT, 4.0, dtype=np.float64),
        generation_scales=np.full(ATOM_COUNT, 2.0, dtype=np.float64),
        minimum_positive_rows=1,
        minimum_positive_blocks=1,
    )
    assert all(row["training_scale"] == 4.0 for row in report["atom_rows"])
    assert all(row["generation_scale"] == 2.0 for row in report["atom_rows"])


def test_audit_warns_when_supported_atom_cannot_distinguish_k8_candidates() -> None:
    raw, source, atom_source, applicable, physical = _fixture(2)
    raw[:, :, 7] = 2.0
    report = compute_train_atom_audit(
        raw,
        source,
        atom_source,
        applicable,
        physical,
        np.asarray([0.5, 0.5], dtype=np.float64),
        ["block-a", "block-b"],
        ["route-a", "route-b"],
        ["narrow/easy", "narrow/high"],
        np.ones(ATOM_COUNT, dtype=np.float64),
        minimum_positive_rows=1,
        minimum_positive_blocks=1,
    )
    lane = report["atom_rows"][7]
    assert lane["positive_candidate_count"] == 16
    assert lane["candidate_distinction"]["positive_range_weight"] == 0.0
    assert lane["status"] == "WARN"
    assert lane["warning"] == "candidate_indistinguishable"
    assert lane["warning_reasons"] == ["candidate_indistinguishable"]
    assert lane["remediation_class"] == "expected_redundancy"
    assert lane["remediation_classes"] == ["expected_redundancy"]
    assert "14d_minus_lane_deviation" in report["ablations"]["comparisons"]
    assert report["status_counts"] == {"PASS": 13, "WARN": 1, "FAIL": 0}


@pytest.mark.parametrize(
    ("mutate", "failed_indices", "reason"),
    [
        (
            lambda raw, applicable: raw.__setitem__((0, 0, 2), raw[0, 0, 2] + 1.0),
            (0, 1, 2),
            "jerk_full_not_equal_early_plus_late",
        ),
        (
            lambda raw, applicable: raw.__setitem__((0, 0, 4), raw[0, 0, 6] + 1.0),
            (4, 5, 6),
            "speed_margin_costs_not_monotone_0_0_le_0_5_le_1_0",
        ),
        (
            lambda raw, applicable: (
                applicable.__setitem__((0, 0, 8), False),
                raw.__setitem__((0, 0, 8), 1.0),
            ),
            (8,),
            "nonapplicable_atom_must_be_exact_zero",
        ),
        (
            lambda raw, applicable: raw.__setitem__((0, slice(None), 9), 1.0),
            (9,),
            "progress_shortfall_source_valid_reference_has_no_zero_cost_candidate",
        ),
        (
            lambda raw, applicable: raw.__setitem__((0, 0, 13), 1.0),
            (13,),
            "candidate0_dp_prior_jerk_excess_must_be_zero",
        ),
    ],
)
def test_audit_marks_independently_recomputable_correctness_violations_fail(
    mutate, failed_indices: tuple[int, ...], reason: str
) -> None:
    raw, source, atom_source, applicable, physical = _fixture(2)
    mutate(raw, applicable)
    report = compute_train_atom_audit(
        raw,
        source,
        atom_source,
        applicable,
        physical,
        np.asarray([0.5, 0.5], dtype=np.float64),
        ["block-a", "block-b"],
        ["route-a", "route-b"],
        ["family/easy", "family/high"],
        np.ones(ATOM_COUNT, dtype=np.float64),
        minimum_positive_rows=1,
        minimum_positive_blocks=1,
    )
    for index in failed_indices:
        row = report["atom_rows"][index]
        assert row["status"] == "FAIL"
        assert reason in row["failure_reasons"]
        assert row["remediation_classes"][0] == "implementation_correctness"
    assert report["status_counts"]["FAIL"] == len(failed_indices)
