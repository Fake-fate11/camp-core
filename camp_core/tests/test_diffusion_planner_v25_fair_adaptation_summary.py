from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_fair_adaptation_summary as producer,
)
from scripts.integrations import (
    review_diffusion_planner_v25_fair_adaptation_summary as reviewer,
)


def _fixture():
    candidates = np.zeros((16, 8, 80, 4), dtype=np.float32)
    for state in range(16):
        for row in range(8):
            candidates[state, row, :, 0] = float(row + 1)
            candidates[state, row, :, 1] = float(state)
    sequential_candidates = candidates.copy()
    neighbors = np.zeros((16, 8, 32, 80, 4), dtype=np.float32)
    sequential_neighbors = neighbors.copy()
    failures = [(state, row) for state in range(5) for row in range(2)]
    failures += [(state, 0) for state in range(5, 9)]
    for state, row in failures:
        sequential_neighbors[state, row, 0, 0, 0] = 1e-3
    atoms = np.zeros((16, 8, 14), dtype=np.float64)
    for row in range(8):
        atoms[:, row, :] = float(row)
    sequential_atoms = atoms + 1e-6
    source_masks = np.ones((16, 8), dtype=np.bool_)
    physical_masks = np.ones((16, 8), dtype=np.bool_)
    scales = np.ones(14, dtype=np.float64)
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)
    arrays = {
        "primary_candidates": candidates,
        "sequential_candidates": sequential_candidates,
        "primary_neighbors": neighbors,
        "sequential_neighbors": sequential_neighbors,
        "primary_atoms": atoms,
        "sequential_atoms": sequential_atoms,
        "primary_source_masks": source_masks,
        "sequential_source_masks": source_masks.copy(),
        "primary_physical_masks": physical_masks,
        "sequential_physical_masks": physical_masks.copy(),
        "atom_scales": scales,
        "static_weights": weights,
    }
    receipts = []
    for state in range(16):
        primary_scores, primary_selected = producer._scores(
            atoms[state], scales, weights, source_masks[state]
        )
        receipts.append(
            {
                "tick_index": state,
                "state_sha256": f"{state:064x}",
                "pool_id": f"{state + 16:064x}",
                "candidate_tensor_sha256_before": f"{state + 32:064x}",
                "candidate_tensor_sha256_after": f"{state + 32:064x}",
                "materialized_summary": {"scene_weights": weights.tolist()},
                "real_selector_receipts": {
                    arm: {
                        "scores": primary_scores.tolist(),
                        "selected_index": primary_selected,
                    }
                    for arm in ("Static14D", "Scene14D")
                },
                "zero_call_receipt": {
                    "dp_or_model_calls_after_pool": 0,
                    "latent_replacements_after_pool": 0,
                    "candidate_generations_after_pool": 0,
                },
                "adaptation": {
                    "repeat_exact_equal": True,
                    "sequential": {"scene_weights": weights.tolist()},
                },
            }
        )
    report = {
        "schema_version": "camp_dp_v25_fair_nonholdout_validation_v1",
        "status": "blocked_fair_nonholdout_engineering_validation",
        "state_matched_replay": {"state_count": 16, "receipts": receipts},
        "pool_distribution_adaptation_audit": {
            "trajectory_row_denominator": 128,
            "neighbor_row_denominator": 128,
            "trajectory_equivalent_row_count": 128,
            "neighbor_equivalent_row_count": 114,
            "substantive_drift_state_count": 9,
        },
    }
    return report, arrays


def test_additive_summary_and_independent_literal_review():
    report, arrays = _fixture()
    summary = producer.build_summary(report, arrays)
    rebuilt = reviewer.review_summary(report, arrays, summary)
    assert rebuilt["atom_exact_equal_count"] == 0
    assert rebuilt["selected_index_flip_state_count"] == {
        "Static14D": 0,
        "Scene14D": 0,
    }
    assert rebuilt["k8_valid_state_count"] == {"primary": 16, "sequential": 16}
    assert rebuilt["primary_failure_taxonomy_state_count"][
        "neighbor_tolerance"
    ] == 9
    assert rebuilt["primary_failure_taxonomy_state_count"]["no_failure"] == 7
    assert rebuilt["failure_indicator_row_count"]["neighbor_tolerance"] == 14


def test_summary_unknown_array_fails_closed():
    report, arrays = _fixture()
    arrays["unknown"] = np.zeros(1)
    with pytest.raises(ValueError, match="inventory"):
        producer.build_summary(report, arrays)


def test_independent_review_detects_atom_diff_tamper():
    report, arrays = _fixture()
    summary = producer.build_summary(report, arrays)
    summary["state_summaries"][0]["atom_differences"][0]["max_abs_diff"] = 9.0
    with pytest.raises(ValueError, match="literal reconstruction"):
        reviewer.review_summary(report, arrays, summary)


def test_failure_taxonomy_priority_is_mutually_exclusive_and_exhaustive():
    report, arrays = _fixture()
    report["state_matched_replay"]["receipts"][0]["adaptation"][
        "repeat_exact_equal"
    ] = False
    summary = producer.build_summary(report, arrays)
    counts = summary["aggregates"]["primary_failure_taxonomy_state_count"]
    assert sum(counts.values()) == 16
    assert counts["repeat_nondeterminism"] == 1
    assert counts["neighbor_tolerance"] == 8


def test_k8_validity_rejects_nonfinite_and_nondiverse():
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    neighbors = np.zeros((8, 32, 80, 4), dtype=np.float32)
    result = producer._k8_validity(candidates, neighbors)
    assert result["finite"] is True
    assert result["diverse"] is False
    candidates[0, 0, 0] = np.nan
    result = producer._k8_validity(candidates, neighbors)
    assert result["finite"] is False
    assert result["valid"] is False


def test_reviewer_does_not_import_producer_fairness_or_selector_oracle():
    source = Path(reviewer.__file__).read_text("utf-8")
    forbidden = (
        "diffusion_planner_v25_fair_adaptation_summary import",
        "diffusion_planner_v25_fair_nonholdout import",
        "validate_diffusion_planner_v25_fair_nonholdout import",
        "select_camp_candidate",
        "materialize_canonical_14d",
    )
    assert not any(token in source for token in forbidden)
    assert "def review_summary(" in source


def test_materializer_does_not_import_or_invoke_model_selector_or_pool():
    path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "integrations"
        / "materialize_diffusion_planner_v25_fair_adaptation_summary.py"
    )
    source = path.read_text("utf-8")
    assert "validate_diffusion_planner_v25_fair_nonholdout import" not in source
    assert "select_camp_candidate" not in source
    assert "model(" not in source
    assert '"source_files_read": ["report.json", "replay_preimages.npz"]' in source
