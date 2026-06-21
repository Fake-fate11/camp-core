from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_materiality import (
    INSUFFICIENT_STATUS,
    READY_STATUS,
    build_report,
    compute_candidate_set_consensus_center_rms,
    main,
    render_markdown,
)


def _design(**overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_payload_design_ready",
        "passed": True,
        "payload_design_ready": True,
        "authorized_next_work": "candidate_set_consensus_existing_log_materiality_screen_only",
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(overrides)
    return {
        "final_decision": decision,
        "coefficient_contract": {
            "primary_coefficient_name": "candidate_set_consensus_center_rms_cost_v1",
            "domain": "nonnegative_finite_scalar_per_candidate",
        },
    }


def _prefix(offset: float) -> list[list[list[float]]]:
    return [
        [[0.0 + offset, 0.0, 1.0, 0.0], [1.0 + offset, 0.0, 1.0, 0.0]],
        [[0.2 + offset, 0.0, 1.0, 0.0], [1.2 + offset, 0.0, 1.0, 0.0]],
        [[4.0 + offset, 0.0, 1.0, 0.0], [5.0 + offset, 0.0, 1.0, 0.0]],
    ]


def _write_log(path: Path, *, records: int = 12, include_prefix: bool = True) -> None:
    rows = []
    for idx in range(records):
        row: dict[str, object] = {"selected_index": 2}
        if include_prefix:
            row["candidate_raw_trajectory_prefix"] = _prefix(float(idx) * 0.01)
            row["candidate_raw_trajectory_prefix_steps"] = 2
        rows.append(row)
    path.write_text(json.dumps(rows), encoding="utf-8")


def test_candidate_set_consensus_center_rms_is_nonnegative() -> None:
    costs = compute_candidate_set_consensus_center_rms(_prefix(0.0))

    assert costs.shape == (3,)
    assert np.all(np.isfinite(costs))
    assert np.all(costs >= 0.0)
    assert costs[2] > costs[0]


def test_candidate_set_consensus_materiality_ready(tmp_path: Path) -> None:
    log = tmp_path / "camp_selection_log.json"
    _write_log(log)

    report = build_report(
        payload_design=_design(),
        selection_log_paths=[log],
        search_roots=[],
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["materiality_gate_passed"] is True
    assert decision["payload_implementation_authorized"] is True
    assert decision["new_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["record_summary"]["valid_records"] == 12
    assert report["record_summary"]["nonzero_spread_rate"] == 1.0
    assert report["record_summary"]["lower_than_selected_rate"] == 1.0


def test_candidate_set_consensus_materiality_insufficient_without_prefix(
    tmp_path: Path,
) -> None:
    log = tmp_path / "camp_selection_log.json"
    _write_log(log, include_prefix=False)

    report = build_report(
        payload_design=_design(),
        selection_log_paths=[log],
        search_roots=[],
    )
    decision = report["final_decision"]

    assert decision["status"] == INSUFFICIENT_STATUS
    assert decision["materiality_gate_passed"] is False
    assert decision["payload_implementation_authorized"] is False
    assert decision["authorized_next_work"] == (
        "candidate_set_consensus_default_off_payload_logging_preflight_only"
    )
    assert report["record_summary"]["missing_prefix_records"] == 12


def test_candidate_set_consensus_materiality_blocks_bad_design(tmp_path: Path) -> None:
    log = tmp_path / "camp_selection_log.json"
    _write_log(log)

    report = build_report(
        payload_design=_design(status="candidate_set_consensus_payload_design_blocked"),
        selection_log_paths=[log],
        search_roots=[],
    )

    assert report["final_decision"]["status"] == (
        "candidate_set_consensus_existing_log_materiality_blocked"
    )
    assert "design_status" in report["final_decision"]["failed_checks"]


def test_candidate_set_consensus_materiality_markdown_states_boundary(
    tmp_path: Path,
) -> None:
    log = tmp_path / "camp_selection_log.json"
    _write_log(log)

    report = build_report(
        payload_design=_design(),
        selection_log_paths=[log],
        search_roots=[],
    )
    markdown = render_markdown(report)

    assert "Candidate-Set Consensus Existing-Log Materiality" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown
    assert "does not authorize replay" in markdown


def test_candidate_set_consensus_materiality_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design.json"
    log = tmp_path / "camp_selection_log.json"
    output_json = tmp_path / "materiality.json"
    output_md = tmp_path / "materiality.md"
    design.write_text(json.dumps(_design()), encoding="utf-8")
    _write_log(log)

    monkeypatch.setattr(
        "sys.argv",
        [
            "materiality",
            "--payload_design_json",
            str(design),
            "--selection_log_json",
            str(log),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_materiality",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Candidate-Set Consensus Existing-Log Materiality" in (
        output_md.read_text(encoding="utf-8")
    )
