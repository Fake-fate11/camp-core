from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from scripts.integrations.run_diffusion_planner_camp_replay import (
    CANDIDATE_TENSOR_PROVENANCE_PRE_SCORING_STAGE,
    CANDIDATE_TENSOR_PROVENANCE_SCHEMA_VERSION,
    _build_candidate_tensor_provenance_payload,
    _candidate_tensor_hash_payload,
    _summarize_candidate_tensor_provenance_records,
)


def _candidate_tensor() -> np.ndarray:
    return np.asarray(
        [
            [[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0]],
            [[0.0, 0.0, 1.0, 0.0], [0.8, 0.2, 0.98, 0.1]],
        ],
        dtype=np.float32,
    )


def test_candidate_tensor_hash_payload_preserves_tensor_bytes() -> None:
    candidates = _candidate_tensor()
    candidates[1, 1, 3] = np.nan

    payload = _candidate_tensor_hash_payload(
        candidates.T,
        stage=CANDIDATE_TENSOR_PROVENANCE_PRE_SCORING_STAGE,
    )
    contiguous = np.ascontiguousarray(candidates.T)

    assert payload["stage"] == CANDIDATE_TENSOR_PROVENANCE_PRE_SCORING_STAGE
    assert payload["shape"] == list(contiguous.shape)
    assert payload["dtype"] == str(contiguous.dtype)
    assert payload["byte_count"] == contiguous.nbytes
    assert payload["nan_policy"] == "preserve_tensor_bytes"
    assert payload["sha256"] == hashlib.sha256(
        contiguous.view(np.uint8)
    ).hexdigest()


def test_candidate_tensor_provenance_payload_proves_immutable_selector_input() -> None:
    candidates = _candidate_tensor()

    payload = _build_candidate_tensor_provenance_payload(
        candidates.copy(),
        candidates,
        selected_index=1,
    )

    assert payload["schema_version"] == CANDIDATE_TENSOR_PROVENANCE_SCHEMA_VERSION
    assert payload["selection_effect"] is False
    assert payload["candidate_generation_effect"] is False
    assert payload["candidate_tensor_mutation_effect"] is False
    assert payload["candidate_count"] == 2
    assert payload["post_selector_candidate_count"] == 2
    assert payload["pre_camp_scoring_tensor"]["sha256"]
    assert payload["post_camp_selector_tensor"]["sha256"]
    assert payload["selected_index_in_range"] is True
    assert payload["pre_post_tensor_hash_equal"] is True
    assert payload["no_candidate_row_append"] is True
    assert payload["no_coordinate_heading_speed_rewrite_by_camp"] is True
    assert payload["reference_blend_stage_hash_separated"] is True
    assert payload["outcome_label_input"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["payload_valid"] is True


def test_candidate_tensor_provenance_payload_detects_tensor_rewrite() -> None:
    pre = _candidate_tensor()
    post = pre.copy()
    post[1, 1, 0] += 0.25

    payload = _build_candidate_tensor_provenance_payload(
        pre,
        post,
        selected_index=0,
    )

    assert payload["selected_index_in_range"] is True
    assert payload["no_candidate_row_append"] is True
    assert payload["pre_post_tensor_hash_equal"] is False
    assert payload["no_coordinate_heading_speed_rewrite_by_camp"] is False
    assert payload["payload_valid"] is False


def test_candidate_tensor_provenance_payload_detects_row_append_and_bad_index() -> None:
    pre = _candidate_tensor()
    post = np.concatenate([pre, pre[:1]], axis=0)

    payload = _build_candidate_tensor_provenance_payload(
        pre,
        post,
        selected_index=2,
    )

    assert payload["candidate_count"] == 2
    assert payload["post_selector_candidate_count"] == 3
    assert payload["selected_index_in_range"] is False
    assert payload["no_candidate_row_append"] is False
    assert payload["payload_valid"] is False


def test_reference_blend_stage_requires_separate_raw_dp_hash_when_present() -> None:
    candidates = _candidate_tensor()

    missing_raw = _build_candidate_tensor_provenance_payload(
        candidates,
        candidates,
        selected_index=0,
        reference_blend_steps=3,
    )
    with_raw = _build_candidate_tensor_provenance_payload(
        candidates,
        candidates,
        selected_index=0,
        raw_dp_candidates=candidates.copy(),
        reference_blend_steps=3,
    )

    assert missing_raw["reference_blend_stage_hash_separated"] is False
    assert missing_raw["payload_valid"] is False
    assert with_raw["reference_blend_stage_hash_separated"] is True
    assert with_raw["raw_dp_tensor_before_reference_blend"] is not None
    assert with_raw["payload_valid"] is True


def test_outcome_label_inputs_fail_closed() -> None:
    candidates = _candidate_tensor()

    payload = _build_candidate_tensor_provenance_payload(
        candidates,
        candidates,
        selected_index=0,
        outcome_label_input=True,
    )

    assert payload["outcome_label_input"] is True
    assert payload["closed_loop_outcome_fields_read"] is True
    assert payload["payload_valid"] is False


def test_online_selector_path_does_not_receive_outcome_label_inputs() -> None:
    source = Path(
        "scripts/integrations/run_diffusion_planner_camp_replay.py"
    ).read_text(encoding="utf-8")
    select_start = source.index("selection = selector.select(")
    select_end = source.index(")\n        camp_selection_done", select_start)
    selector_call = source[select_start:select_end]
    provenance_start = source.index("_build_candidate_tensor_provenance_payload(")
    provenance_end = source.index("elapsed_ms =", provenance_start)
    provenance_call = source[provenance_start:provenance_end]

    assert "candidate_outcomes" not in selector_call
    assert "outcome_label_input=False" in provenance_call


def test_candidate_tensor_provenance_summary_tracks_static_contract() -> None:
    candidates = _candidate_tensor()
    payload = _build_candidate_tensor_provenance_payload(
        candidates,
        candidates,
        selected_index=0,
    )

    summary = _summarize_candidate_tensor_provenance_records(
        [{"camp_candidate_tensor_provenance": payload}],
        enabled=True,
    )

    assert summary == {
        "schema_version": CANDIDATE_TENSOR_PROVENANCE_SCHEMA_VERSION,
        "enabled": True,
        "selection_effect": False,
        "candidate_generation_effect": False,
        "candidate_tensor_mutation_effect": False,
        "records": 1,
        "payload_records": 1,
        "all_payloads_present": True,
        "all_payloads_valid": True,
        "all_selected_index_in_range": True,
        "all_pre_post_tensor_hash_equal": True,
        "all_candidate_count_unchanged": True,
        "all_no_coordinate_heading_speed_rewrite_by_camp": True,
        "all_reference_blend_stage_hash_separated": True,
        "outcome_label_input": False,
        "closed_loop_outcome_fields_read": False,
    }


def test_candidate_tensor_hash_rejects_non_numeric_payloads() -> None:
    with pytest.raises(ValueError, match="numeric tensor"):
        _candidate_tensor_hash_payload(
            np.asarray([["not", "a", "candidate"]], dtype=object),
            stage=CANDIDATE_TENSOR_PROVENANCE_PRE_SCORING_STAGE,
        )
