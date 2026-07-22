from __future__ import annotations

import copy

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_context import RAW_FEATURE_NAMES
from camp_core.integrations.diffusion_planner_v25_train_corpus import (
    FIXED_DP_HEAD,
    extract_training_row,
    validate_reviewed_train_corpus_reports,
)


SHA = "a" * 64


def _snapshot() -> tuple[dict, dict]:
    atom_source = np.ones((8, 14), dtype=np.bool_)
    payload = {
        "schema_version": "snapshot-v1",
        "feature_payload": {
            "atom_matrix": np.zeros((8, 14), dtype=np.float64).tolist(),
            "source_valid_mask": [True] * 8,
            "atom_source_valid_mask": atom_source.tolist(),
            "atom_applicable_mask": atom_source.tolist(),
            "physical_feasible_mask": [True] * 8,
            "raw_context": {name: float(index) for index, name in enumerate(RAW_FEATURE_NAMES)},
            "context_source_complete": {name: name != "traffic_signal_phase_remaining_s" for name in RAW_FEATURE_NAMES},
        },
        "sidecar": {
            "scenario_id": SHA,
            "tick_index": 7,
            "fresh_b_opened": False,
            "outcome_fields_consumed": [],
            "offline_label_provenance": "pending_train_only_causal_label",
            "canonical_semantic_clone_sha256": "b" * 64,
            "route_identity_sha256": "c" * 64,
            "corridor_group_sha256": "d" * 64,
            "map_family_id": "map-family",
            "family": "lead_brake",
            "tier": "borderline",
            "seed": 25001,
            "generation_behavior_scale_sha256": "e" * 64,
        },
    }
    index = {
        "scenario_id": SHA,
        "tick_index": 7,
        "relative_path": "snapshots/unused.json.xz",
        "sha256": "f" * 64,
    }
    return payload, index


def test_extract_training_row_preserves_context_order_and_offline_ids_only() -> None:
    snapshot, index = _snapshot()
    row = extract_training_row(snapshot, index)
    assert row["raw_atoms"].shape == (8, 14)
    assert row["raw_context"].shape == (len(RAW_FEATURE_NAMES),)
    assert row["context_source_complete"].dtype == np.bool_
    assert row["context_source_complete"][-1] == (
        RAW_FEATURE_NAMES[-1] != "traffic_signal_phase_remaining_s"
    )
    assert row["semantic_block_ids"] == "b" * 64
    assert row["family_tier"] == "lead_brake/borderline"
    assert row["seeds"] == 25001
    assert row["ticks"] == 7


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda s: s["sidecar"].__setitem__("fresh_b_opened", True), "train-only"),
        (lambda s: s["sidecar"].__setitem__("outcome_fields_consumed", ["collision"]), "train-only"),
        (lambda s: s["feature_payload"]["source_valid_mask"].__setitem__(0, 1), "native bool"),
        (lambda s: s["feature_payload"]["raw_context"].__setitem__("route_id", 1.0), "feature set"),
        (lambda s: s["sidecar"].__setitem__("canonical_semantic_clone_sha256", None), "native string"),
    ],
)
def test_extract_training_row_fails_closed_on_leakage_or_schema_drift(
    mutation, message: str
) -> None:
    snapshot, index = _snapshot()
    changed = copy.deepcopy(snapshot)
    mutation(changed)
    with pytest.raises(ValueError, match=message):
        extract_training_row(changed, index)


def _terminal_reports(corpus_path) -> tuple[dict, dict]:
    support = {"passed": True, "overall_complete_rate": 0.96}
    corpus = {
        "status": "passed",
        "mode": "execute",
        "fixed_dp_head": FIXED_DP_HEAD,
        "attempted_identity_count": 1500,
        "retained_identity_count": 1500,
        "complete_identity_count": 1440,
        "failed_identity_count": 60,
        "snapshot_count": 1440 * 64,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
        "training_snapshot_outcome_fields": [],
        "runtime_outcomes_not_read_or_copied_to_training_snapshots": True,
        "candidate_tensors_modified": False,
        "selector_training_executed": False,
        "calibration_executed": False,
        "claim_authorized": False,
        "fixed_dp_support_coverage": support,
    }
    review = {
        "status": "passed_independent_full_corpus_review",
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(corpus_path),
        "reviewed_root_sha256": SHA,
        "identity_denominator": 1500,
        "complete_identity_count": 1440,
        "typed_retained_failure_count": 60,
        "snapshot_count": 1440 * 64,
        "partial_snapshot_count": 0,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    return corpus, review


def test_reviewed_train_corpus_admission_binds_full_denominator_and_support(
    tmp_path,
) -> None:
    corpus_path = tmp_path / "corpus"
    corpus_path.mkdir()
    corpus, review = _terminal_reports(corpus_path)
    result = validate_reviewed_train_corpus_reports(
        corpus,
        review,
        corpus_artifact=corpus_path,
        corpus_root_sha256=SHA,
    )
    assert result["identity_denominator"] == 1500
    assert result["complete_identity_count"] == 1440
    assert result["fixed_dp_support_coverage"]["passed"] is True


@pytest.mark.parametrize(
    ("target", "field", "value", "message"),
    [
        ("review", "fixed_dp_head", "b" * 40, "review authority"),
        ("review", "complete_identity_count", 1424, "review authority"),
        ("corpus", "candidate_tensors_modified", True, "scientific support"),
        (
            "corpus",
            "fixed_dp_support_coverage",
            {"passed": False},
            "scientific support",
        ),
    ],
)
def test_reviewed_train_corpus_admission_rejects_authority_or_coverage_drift(
    tmp_path, target: str, field: str, value, message: str
) -> None:
    corpus_path = tmp_path / "corpus"
    corpus_path.mkdir()
    corpus, review = _terminal_reports(corpus_path)
    (corpus if target == "corpus" else review)[field] = value
    with pytest.raises(ValueError, match=message):
        validate_reviewed_train_corpus_reports(
            corpus,
            review,
            corpus_artifact=corpus_path,
            corpus_root_sha256=SHA,
        )
