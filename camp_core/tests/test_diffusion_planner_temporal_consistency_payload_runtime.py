from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_temporal_consistency_payload import (
    TEMPORAL_CONSISTENCY_PAYLOAD_ATOM_CANDIDATE_NAMES,
    TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES,
    TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS,
    TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION,
    build_temporal_consistency_payload,
)
from scripts.integrations.summarize_diffusion_planner_camp_replay import (
    REPLAY_METADATA_FIELDS,
)


REPLAY_SCRIPT = Path(__file__).resolve().parents[2] / (
    "scripts/integrations/run_diffusion_planner_camp_replay.py"
)


def _current_candidates() -> np.ndarray:
    return np.asarray(
        [
            [[1.0, 0.0, 0.0, 0.0], [2.0, 0.0, 0.0, 0.0], [3.0, 0.0, 0.0, 0.0]],
            [[1.0, 1.0, 0.0, 0.0], [2.0, 1.0, 0.0, 0.0], [3.0, 1.0, 0.0, 0.0]],
        ],
        dtype=np.float64,
    )


def _previous_selected_plan() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0, 0.0],
            [3.0, 0.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )


def test_temporal_consistency_payload_missing_previous_plan_fails_closed() -> None:
    payload = build_temporal_consistency_payload(
        candidates=_current_candidates(),
        previous_selected_plan=None,
        support_steps=3,
        dt_s=0.1,
    )

    assert payload["schema_version"] == TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION
    assert payload["enabled"] is True
    assert payload["default_off"] is True
    assert payload["selection_effect"] is False
    assert payload["future_outcome_leakage"] is False
    assert payload["closed_loop_outcome_fields_read"] is False
    assert payload["online_selector_change"] is False
    assert payload["deployed_atom_vector_change"] is False
    assert payload["classical_benders_claim"] is False
    assert payload["available"] is False
    assert payload["availability_reason"] == "previous_selected_plan_absent"
    assert payload["previous_plan_temporal_consistency_rms_m"] is None
    assert payload["finite_checks"]["payload_valid"] is False
    assert payload["finite_checks"]["previous_selected_plan_available"] is False
    assert set(payload["latency_ms"]) == set(TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS)
    assert all(float(value) >= 0.0 for value in payload["latency_ms"].values())


def test_temporal_consistency_payload_computes_shifted_rms_cost() -> None:
    payload = build_temporal_consistency_payload(
        candidates=_current_candidates(),
        previous_selected_plan=_previous_selected_plan(),
        support_steps=3,
        dt_s=0.1,
        elapsed_steps=1,
        min_overlap_steps=2,
    )

    assert payload["available"] is True
    assert payload["availability_reason"] is None
    assert payload["candidate_count"] == 2
    assert payload["horizons"]["effective_overlap_steps"] == 3
    assert payload["previous_selected_plan_shape"] == [4, 4]
    assert payload["field_shapes"]["previous_plan_temporal_consistency_rms_m"] == [2]
    assert payload["previous_plan_temporal_consistency_rms_m"] == [0.0, 1.0]
    assert payload["atom_candidate_names"] == list(
        TEMPORAL_CONSISTENCY_PAYLOAD_ATOM_CANDIDATE_NAMES
    )
    assert all(payload["finite_checks"].values())
    assert "score_k(w)=a_k^T w" in payload["math_boundary"]


def test_temporal_consistency_payload_short_overlap_fails_closed() -> None:
    payload = build_temporal_consistency_payload(
        candidates=_current_candidates(),
        previous_selected_plan=_previous_selected_plan()[:2],
        support_steps=3,
        elapsed_steps=1,
        min_overlap_steps=2,
    )

    assert payload["available"] is False
    assert payload["availability_reason"] == "overlap_steps_insufficient"
    assert payload["finite_checks"]["overlap_steps_sufficient"] is False
    assert payload["previous_plan_temporal_consistency_rms_m"] is None


def test_temporal_consistency_payload_rejects_invalid_runtime_parameters() -> None:
    with pytest.raises(ValueError, match="dt_s"):
        build_temporal_consistency_payload(
            candidates=_current_candidates(),
            previous_selected_plan=_previous_selected_plan(),
            support_steps=3,
            dt_s=0.0,
        )
    with pytest.raises(ValueError, match="elapsed_steps"):
        build_temporal_consistency_payload(
            candidates=_current_candidates(),
            previous_selected_plan=_previous_selected_plan(),
            support_steps=3,
            elapsed_steps=-1,
        )
    with pytest.raises(ValueError, match="min_overlap_steps"):
        build_temporal_consistency_payload(
            candidates=_current_candidates(),
            previous_selected_plan=_previous_selected_plan(),
            support_steps=3,
            min_overlap_steps=0,
        )


def test_temporal_consistency_payload_does_not_accept_outcome_inputs() -> None:
    signature = inspect.signature(build_temporal_consistency_payload)

    assert "outcome" not in str(signature).lower()
    assert "closed_loop" not in str(signature).lower()
    assert list(signature.parameters) == [
        "candidates",
        "previous_selected_plan",
        "support_steps",
        "dt_s",
        "elapsed_steps",
        "min_overlap_steps",
    ]


def test_replay_script_wires_temporal_consistency_payload_default_off() -> None:
    source = REPLAY_SCRIPT.read_text(encoding="utf-8")

    assert "--camp_temporal_consistency_payload_logging" in source
    assert "build_temporal_consistency_payload(" in source
    assert "previous_selected_plan_memory" in source
    assert "previous_selected_plan=previous_selected_plan_memory" in source
    assert "temporal_consistency_payload_logging=bool(" in source
    assert "args.camp_temporal_consistency_payload_logging" in source
    assert '"temporal_consistency_payload_logging": (' in source
    assert '"camp_temporal_consistency_payload_logging": (' in source
    assert "validation[\"camp_temporal_consistency_payload_logging\"]" in source
    assert "**temporal_consistency_payload_latency_ms" in source
    assert "authorized_stage" in source
    assert "default_off_temporal_consistency_payload_runtime_preflight_only" in source


def test_summary_merges_temporal_consistency_payload_metadata() -> None:
    assert "camp_temporal_consistency_payload_logging" in REPLAY_METADATA_FIELDS
    assert TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES == (
        "previous_plan_temporal_consistency_rms_m",
    )
