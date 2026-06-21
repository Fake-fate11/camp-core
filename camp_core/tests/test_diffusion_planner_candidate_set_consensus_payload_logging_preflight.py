from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_payload_logging_preflight import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _materiality(**overrides: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_existing_log_materiality_insufficient",
        "screen_completed": True,
        "materiality_gate_passed": False,
        "authorized_next_work": "candidate_set_consensus_default_off_payload_logging_preflight_only",
        "primary_gap": "too_few_existing_candidate_prefix_records",
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
        "record_summary": {
            "valid_records": 0,
            "missing_prefix_records": 72002,
        },
    }


def _write_replay(path: Path, *, include_hooks: bool = True) -> None:
    if include_hooks:
        path.write_text(
            "\n".join(
                [
                    "candidates, neighbor_predictions, turn_logits = generate_candidate_trajectories(",
                    "candidate_generation_done = time.perf_counter()",
                    "external_context_payload_logging_payload = None",
                    "temporal_consistency_payload_logging_payload = None",
                    "if temporal_consistency_payload_logging:",
                    "phase_latencies_ms = {",
                    "**external_context_payload_latency_ms",
                    "**temporal_consistency_payload_latency_ms",
                    "records.append(",
                    '"selected_index": selected_index',
                    '"candidate_trajectory_horizon_steps": int(candidates.shape[1])',
                    '"camp_external_context_payload_logging": (',
                    '"camp_temporal_consistency_payload_logging": (',
                    '"selection_effect": False',
                ]
            ),
            encoding="utf-8",
        )
    else:
        path.write_text("records.append({})", encoding="utf-8")


def test_candidate_set_consensus_payload_logging_preflight_ready(
    tmp_path: Path,
) -> None:
    replay = tmp_path / "run_diffusion_planner_camp_replay.py"
    _write_replay(replay)

    report = build_report(
        materiality=_materiality(),
        replay_source=replay,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["payload_implementation_authorized"] is True
    assert decision["new_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False


def test_candidate_set_consensus_payload_logging_preflight_blocks_bad_materiality(
    tmp_path: Path,
) -> None:
    replay = tmp_path / "run_diffusion_planner_camp_replay.py"
    _write_replay(replay)

    report = build_report(
        materiality=_materiality(
            status="candidate_set_consensus_existing_log_materiality_ready",
            materiality_gate_passed=True,
        ),
        replay_source=replay,
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert "materiality_status" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_candidate_set_consensus_payload_logging_preflight_blocks_missing_hook(
    tmp_path: Path,
) -> None:
    replay = tmp_path / "run_diffusion_planner_camp_replay.py"
    _write_replay(replay, include_hooks=False)

    report = build_report(materiality=_materiality(), replay_source=replay)

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert any(
        check.startswith("source_hook_")
        for check in report["final_decision"]["failed_checks"]
    )


def test_candidate_set_consensus_payload_logging_preflight_markdown_boundary(
    tmp_path: Path,
) -> None:
    replay = tmp_path / "run_diffusion_planner_camp_replay.py"
    _write_replay(replay)

    report = build_report(materiality=_materiality(), replay_source=replay)
    markdown = render_markdown(report)

    assert "Candidate-Set Consensus Payload Logging Preflight" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown
    assert "does not authorize replay" in markdown


def test_candidate_set_consensus_payload_logging_preflight_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    materiality = tmp_path / "materiality.json"
    replay = tmp_path / "run_diffusion_planner_camp_replay.py"
    output_json = tmp_path / "preflight.json"
    output_md = tmp_path / "preflight.md"
    materiality.write_text(json.dumps(_materiality()), encoding="utf-8")
    _write_replay(replay)

    monkeypatch.setattr(
        "sys.argv",
        [
            "preflight",
            "--materiality_json",
            str(materiality),
            "--replay_source",
            str(replay),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Candidate-Set Consensus Payload Logging Preflight" in (
        output_md.read_text(encoding="utf-8")
    )
