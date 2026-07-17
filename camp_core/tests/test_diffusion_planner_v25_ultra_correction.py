from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import (
    CANONICAL_NORMALIZED_ATOM_CLIP,
    canonical_normalize_atoms,
    canonical_score_atoms,
    validate_fixed_k8_candidate_tensor,
    validate_v25_atom_scales,
)
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)
from camp_core.integrations.diffusion_planner_v25_context import (
    CONTEXT_SCHEMA_VERSION,
    RAW_FEATURE_NAMES,
    build_v25_raw_context,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (
    select_camp_candidate,
)
from scripts.integrations import (
    run_diffusion_planner_v25_controlled_training_corpus as corpus,
)


def _candidate_tensor() -> np.ndarray:
    values = np.zeros((8, 80, 4), dtype=np.float32)
    values[..., 0] = np.arange(80, dtype=np.float32)
    values[..., 1] = np.arange(8, dtype=np.float32)[:, None]
    values[..., 2] = 1.0
    return values


def _materialized(atoms: np.ndarray) -> dict[str, object]:
    return {
        "canonical_eligible": True,
        "exclusion_reason": None,
        "atom_matrix": atoms,
        "candidate_reasons": [[] for _ in range(8)],
        "physical_feasible_mask": np.ones(8, dtype=bool),
        "source_valid_mask": np.ones(8, dtype=bool),
    }


def _causal_input() -> dict[str, np.ndarray]:
    data = {
        key: np.zeros(shape, dtype=dtype)
        for key, (shape, dtype) in CAUSAL_DP_INPUT_SCHEMA.items()
    }
    data["version"] = np.array(1, dtype=np.int64)
    data["ego_current_state"] = np.array(
        [0.0, 0.0, 1.0, 0.0, 8.0, 0.0, -1.5, 0.0, 0.1, 0.2],
        dtype=np.float32,
    )
    route = np.zeros((25, 20, 33), dtype=np.float32)
    for lane_index, start_x in enumerate((0.0, 19.0)):
        x = np.linspace(start_x, start_x + 19.0, 20)
        route[lane_index, :, 0] = x
        route[lane_index, :, 2] = 1.0
        route[lane_index, :, 5] = 2.0
        route[lane_index, :, 7] = -2.0
        route[lane_index, :, 10] = 1.0  # current red source
        route[lane_index, :, 13] = 1.0
        route[lane_index, :, 23] = 1.0
    data["route_lanes"] = route
    data["lanes"][:2] = route[:2]
    data["route_lanes_has_speed_limit"][:2] = True
    data["route_lanes_speed_limit"][:2, 0] = [12.0, 15.0]
    data["lanes_has_speed_limit"][:2] = True
    data["lanes_speed_limit"][:2, 0] = [12.0, 15.0]
    return data


def test_shared_canonical_clip_changes_the_registered_counterexample() -> None:
    atoms = np.zeros((8, 14), dtype=np.float64)
    atoms[0, 0] = 100.0  # >10x scale: must saturate at ten
    atoms[1, :2] = 9.0
    atoms[2:, :2] = 10.0
    scales = np.ones(14, dtype=np.float64)
    weights = np.zeros(14, dtype=np.float64)
    weights[:2] = 0.5

    normalized = canonical_normalize_atoms(atoms, scales)
    canonical_z, canonical_scores = canonical_score_atoms(atoms, scales, weights)
    native = select_camp_candidate(
        candidates=_candidate_tensor(),
        materialized=_materialized(atoms),
        atom_scales=scales,
        weights=weights,
        eligibility_mask_name="source_valid_mask",
    )

    assert CANONICAL_NORMALIZED_ATOM_CLIP == 10.0
    np.testing.assert_array_equal(normalized, canonical_z)
    assert canonical_scores[0] == 5.0
    assert canonical_scores[1] == 9.0
    assert int(np.argmin((atoms / scales) @ weights)) == 1
    assert native["selected_index"] == 0
    np.testing.assert_array_equal(native["normalized_atoms"], canonical_z)
    np.testing.assert_array_equal(native["scores"], canonical_scores)
    assert native["score_contract"] == "score_k=clip(a_k/s,0,10)^T w"


def test_canonical_score_is_fail_closed_and_tie_breaks_by_lowest_index() -> None:
    atoms = np.zeros((8, 14), dtype=np.float64)
    scales = np.ones(14, dtype=np.float64)
    weights = np.full(14, 1.0 / 14.0)
    materialized = _materialized(atoms)
    materialized["source_valid_mask"] = np.array(
        [False, False, False, True, False, True, False, False]
    )
    selected = select_camp_candidate(
        candidates=_candidate_tensor(),
        materialized=materialized,
        atom_scales=scales,
        weights=weights,
        eligibility_mask_name="source_valid_mask",
    )
    assert selected["selected_index"] == 3

    bad = atoms.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        canonical_score_atoms(bad, scales, weights)
    with pytest.raises(ValueError, match="positive"):
        canonical_score_atoms(atoms, np.zeros(14), weights)
    with pytest.raises(ValueError, match="simplex"):
        canonical_score_atoms(atoms, scales, np.ones(14))


def test_candidate_heading_unit_vector_is_a_hard_invariant() -> None:
    candidates = _candidate_tensor()
    before = candidates.copy()
    validated = validate_fixed_k8_candidate_tensor(candidates)
    np.testing.assert_array_equal(validated, before)

    candidates[0, 0, 2:] = 0.0
    with pytest.raises(ValueError, match="unit vectors"):
        validate_fixed_k8_candidate_tensor(candidates)
    with pytest.raises(ValueError, match="unit vectors"):
        select_camp_candidate(
            candidates=candidates,
            materialized=_materialized(np.zeros((8, 14))),
            atom_scales=np.ones(14),
            weights=np.full(14, 1.0 / 14.0),
        )


def test_v25_red_light_scale_has_a_non_degenerate_semantic_floor() -> None:
    scales = np.ones(14, dtype=np.float64)
    validate_v25_atom_scales(scales)
    scales[10] = 1e-6
    with pytest.raises(ValueError, match="planned_red_light_cost"):
        validate_v25_atom_scales(scales)


def test_context_v2_masks_no_v2i_and_receipts_fresh_current_time_v2i() -> None:
    candidates = _candidate_tensor().astype(np.float64)
    no_v2i = build_v25_raw_context(
        causal_input=_causal_input(),
        candidates=candidates,
        source_valid_mask=np.ones(8, dtype=bool),
    )
    timing_index = RAW_FEATURE_NAMES.index("traffic_signal_phase_remaining_s")
    assert CONTEXT_SCHEMA_VERSION == "camp_dp_v25_causal_context_raw_v2"
    assert no_v2i.raw[timing_index] == 0.0
    assert no_v2i.source_complete[timing_index] is False
    assert no_v2i.source_receipt == {
        "mode": "no_v2i",
        "phase_remaining_available": False,
        "regulatory_signal_mapped": True,
    }

    v2i = build_v25_raw_context(
        causal_input=_causal_input(),
        candidates=candidates,
        source_valid_mask=np.ones(8, dtype=bool),
        v2i_signal_timing={
            "source_id": "v2i-signal-controller-A",
            "phase_remaining_s": 4.5,
            "decision_timestamp_s": 100.0,
            "source_timestamp_s": 99.8,
            "maximum_age_s": 0.5,
            "valid": True,
        },
    )
    assert v2i.raw[timing_index] == 4.5
    assert v2i.source_complete[timing_index] is True
    assert v2i.source_receipt["mode"] == "v2i_current_time"
    assert v2i.source_receipt["source_id"] == "v2i-signal-controller-A"
    assert v2i.source_receipt["age_s"] == pytest.approx(0.2)
    assert v2i.source_receipt["fresh"] is True

    stale = {
        "source_id": "v2i-signal-controller-A",
        "phase_remaining_s": 4.5,
        "decision_timestamp_s": 100.0,
        "source_timestamp_s": 99.0,
        "maximum_age_s": 0.5,
        "valid": True,
    }
    with pytest.raises(ValueError, match="stale"):
        build_v25_raw_context(
            causal_input=_causal_input(),
            candidates=candidates,
            source_valid_mask=np.ones(8, dtype=bool),
            v2i_signal_timing=stale,
        )


def test_training_master_rejects_values_outside_shared_clip_contract() -> None:
    pytest.importorskip("cvxpy")
    from camp_core.outer_master.parametric_cvxpy_master import (
        _validate_v25_problem,
    )

    atoms = np.zeros((1, 2, 14), dtype=np.float64)
    atoms[0, 0, 0] = 10.0
    phi = np.full((1, 53), 1.0 / 53.0)
    oracle = np.array([0])
    feasible = np.ones((1, 2), dtype=bool)
    _validate_v25_problem(atoms, phi, oracle, feasible, margins=None)
    atoms[0, 0, 0] = 10.0001
    with pytest.raises(ValueError, match="clip"):
        _validate_v25_problem(atoms, phi, oracle, feasible, margins=None)


def test_identity_and_terminal_acceptance_reject_all_partial_snapshots() -> None:
    assert corpus.validate_identity_terminal(
        status="complete",
        receipt_tick_count=64,
        snapshot_count=64,
        context_count=64,
        failure_type=None,
        failure_reason=None,
    ) == "complete"
    with pytest.raises(corpus.ArtifactContractViolation, match="exactly 64"):
        corpus.validate_identity_terminal(
            status="complete",
            receipt_tick_count=63,
            snapshot_count=63,
            context_count=63,
            failure_type=None,
            failure_reason=None,
        )
    with pytest.raises(corpus.ArtifactContractViolation, match="partial"):
        corpus.validate_identity_terminal(
            status="failed",
            receipt_tick_count=4,
            snapshot_count=4,
            context_count=4,
            failure_type="ValueError",
            failure_reason="candidate headings must be valid cos/sin vectors",
        )
    assert corpus.validate_identity_terminal(
        status="failed",
        receipt_tick_count=0,
        snapshot_count=0,
        context_count=0,
        failure_type="RetainedScenarioCapabilityFailure",
        failure_reason="preregistered_scenario_capability: no runtime support",
    ) == "retained_capability_failure"

    results = [
        {"status": "complete", "snapshot_count": 64},
        {
            "status": "failed",
            "snapshot_count": 0,
            "failure_type": "RetainedScenarioCapabilityFailure",
            "failure_reason": "preregistered_scenario_capability: unsupported",
        },
    ]
    summary = corpus.validate_terminal_acceptance(
        results, snapshot_index_count=64, expected_identity_count=2
    )
    assert summary == {
        "complete_identity_count": 1,
        "retained_capability_failure_count": 1,
        "training_snapshot_count": 64,
    }


def test_execute_lock_remains_held_through_report_exit_and_seal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    held = False

    @contextmanager
    def fake_lock(_path: Path):
        nonlocal held
        held = True
        events.append("lock_enter")
        try:
            yield
        finally:
            events.append("lock_exit")
            held = False

    output = tmp_path / "evidence"
    args = argparse.Namespace(
        probe_template=tmp_path / "probe.json",
        dp_repo=tmp_path / "dp",
        output_dir=output,
        device="cpu",
        preflight_artifact=tmp_path / "preflight",
        preflight=False,
        execute=True,
    )
    monkeypatch.setattr(corpus, "parse_args", lambda: args)
    monkeypatch.setattr(corpus, "_exclusive_lock", fake_lock)
    monkeypatch.setattr(
        corpus,
        "_run",
        lambda _args: events.append("run")
        or {"status": "passed", "mode": "execute"},
    )

    original_write = corpus._write_json

    def record_write(path: Path, payload: dict[str, object]) -> None:
        assert held
        events.append("report")
        original_write(path, payload)

    monkeypatch.setattr(corpus, "_write_json", record_write)

    def fake_seal(path: Path) -> str:
        assert held
        assert (path / "run.exit").read_text(encoding="ascii") == "0\n"
        events.append("seal")
        return "a" * 64

    monkeypatch.setattr(corpus, "_seal", fake_seal)
    corpus.main()
    assert events == ["lock_enter", "run", "report", "seal", "lock_exit"]


def test_atom_ledger_is_only_a_versioned_s0_path_plan() -> None:
    plan = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "configs"
            / "integrations"
            / "diffusion_planner_v25_atom_ledger_plan_v2.json"
        ).read_text(encoding="utf-8")
    )
    assert plan["stage"] == "A_not_executed_s0_path_plan_only"
    assert plan["atom_count"] == 14
    assert plan["paper_subset_indices"] == list(range(9))
    assert plan["rejected_roots"] == [
        "a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481"
    ]
    assert plan["ledger_artifact_template"].endswith("{HEAD}_{CST}")
    assert plan["validation_artifact_template"].endswith("{HEAD}_{CST}")
