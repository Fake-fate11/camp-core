from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_broader_materiality import (
    AUTHORIZED_NEXT_WORK,
    INSUFFICIENT_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    BroaderMaterialitySpec,
)


def _selector(**overrides: object) -> dict[str, object]:
    report: dict[str, object] = {
        "equivalent": True,
        "paired_logs": 6,
        "records": 60,
        "exact_field_mismatches": {"selected_index": 0, "feasible_mask": 0},
        "numeric_field_mismatches": {"scores": 0, "atoms": 0},
        "numeric_shape_mismatches": {"scores": 0, "atoms": 0},
    }
    report.update(overrides)
    return report


def _payload_audit(**overrides: object) -> dict[str, object]:
    report: dict[str, object] = {
        "errors": [],
        "counts": {
            "baseline_logs": 6,
            "candidate_logs": 6,
            "records": 60,
            "candidate_payload_records": 60,
            "available_payload_records": 60,
            "invalid_payload_records": 0,
        },
        "latency_ms": {
            "latency_ms_candidate_set_consensus_payload": {
                "mean": 0.1,
                "max": 0.4,
            }
        },
        "final_decision": {
            "status": "candidate_set_consensus_payload_smoke_audit_passed",
            "passed": True,
        },
    }
    report.update(overrides)
    return report


def _dataset(**overrides: object) -> dict[str, object]:
    report: dict[str, object] = {
        "passed": True,
        "counts": {"logs": 6, "records": 60, "candidates": 480},
    }
    report.update(overrides)
    return report


def _payload(*, spread: bool = True) -> dict[str, object]:
    costs = [0.01 * idx for idx in range(8)] if spread else [0.1] * 8
    return {
        "available": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_set_consensus_center_rms_m": costs,
        "candidate_set_consensus_center_rms_rank": list(range(8)),
    }


def _record(*, spread: bool = True) -> dict[str, object]:
    return {
        "selected_index": 7,
        "feasible_mask": [True] * 8,
        "selection_scores": [1.0] * 7 + [0.0],
        "candidate_set_consensus_payload_logging": _payload(spread=spread),
    }


def _write_replay_root(root: Path, *, spread: bool = True, formal_seed: bool = False) -> None:
    spec = BroaderMaterialitySpec()
    run_ids = [run.run_id for run in spec.runs]
    if formal_seed:
        run_ids[0] = "sample_tl59_seed11_npc0_tlon"
    for run_id in run_ids:
        run_root = root / "logging_enabled" / run_id
        run_root.mkdir(parents=True)
        rows = [_record(spread=spread) for _ in range(10)]
        (run_root / "camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_broader_materiality_diagnosis_ready_authorizes_atom_design_review_only(
    tmp_path: Path,
) -> None:
    _write_replay_root(tmp_path)

    report = build_report(
        replay_root=tmp_path,
        selector_equivalence=_selector(),
        payload_audit=_payload_audit(),
        dataset_audit=_dataset(),
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["materiality_gate_passed"] is True
    assert decision["signal_present"] is True
    assert decision["atom_design_review_plan_authorized"] is True
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["record_summary"]["records"] == 60
    assert report["record_summary"]["candidate_rows"] == 480
    assert report["record_summary"]["positive_spread_rate"] == 1.0
    assert report["record_summary"]["sample_too_small_for_promotion"] is False


def test_broader_materiality_diagnosis_insufficient_when_spread_absent(
    tmp_path: Path,
) -> None:
    _write_replay_root(tmp_path, spread=False)

    report = build_report(
        replay_root=tmp_path,
        selector_equivalence=_selector(),
        payload_audit=_payload_audit(),
        dataset_audit=_dataset(),
    )

    assert report["final_decision"]["status"] == INSUFFICIENT_STATUS
    assert report["final_decision"]["materiality_gate_passed"] is False
    assert report["final_decision"]["atom_design_review_plan_authorized"] is False
    assert "materiality_positive_spread_rate" in report["final_decision"]["failed_checks"]
    assert "materiality_required_bucket_positive_spread" in report["final_decision"]["failed_checks"]


def test_broader_materiality_diagnosis_rejects_selector_failure(tmp_path: Path) -> None:
    _write_replay_root(tmp_path)

    report = build_report(
        replay_root=tmp_path,
        selector_equivalence=_selector(equivalent=False),
        payload_audit=_payload_audit(),
        dataset_audit=_dataset(),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert "selector_equivalent" in report["final_decision"]["failed_checks"]


def test_broader_materiality_diagnosis_rejects_formal_seed_run(tmp_path: Path) -> None:
    _write_replay_root(tmp_path, formal_seed=True)

    report = build_report(
        replay_root=tmp_path,
        selector_equivalence=_selector(),
        payload_audit=_payload_audit(),
        dataset_audit=_dataset(),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "input_no_formal_seed_runs" in report["final_decision"]["failed_checks"]


def test_broader_materiality_diagnosis_markdown_states_boundaries(tmp_path: Path) -> None:
    _write_replay_root(tmp_path)

    markdown = render_markdown(
        build_report(
            replay_root=tmp_path,
            selector_equivalence=_selector(),
            payload_audit=_payload_audit(),
            dataset_audit=_dataset(),
        )
    )

    assert "Candidate-Set Consensus Broader Nonformal Materiality Diagnosis" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown


def test_broader_materiality_diagnosis_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replay_root = tmp_path / "replay"
    output_json = tmp_path / "materiality.json"
    output_md = tmp_path / "materiality.md"
    _write_replay_root(replay_root)
    audit_root = replay_root / "audit"
    audit_root.mkdir()
    (audit_root / "selector_equivalence.json").write_text(
        json.dumps(_selector()),
        encoding="utf-8",
    )
    (audit_root / "candidate_set_consensus_payload_audit.json").write_text(
        json.dumps(_payload_audit()),
        encoding="utf-8",
    )
    (audit_root / "dataset_audit.json").write_text(
        json.dumps(_dataset()),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-broader-materiality",
            "--replay_root",
            str(replay_root),
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
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Broader Nonformal Materiality Diagnosis" in output_md.read_text(
        encoding="utf-8"
    )
