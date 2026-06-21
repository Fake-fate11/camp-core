from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_turn_logit_payload_design import (
    PayloadFieldSpec,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    main,
    render_markdown,
)


def _visibility(
    status: str = "current_tick_tensor_visibility_has_candidate_source",
    candidate_sources: list[str] | None = None,
    authorized_next_work: str = "predeclare_default_off_turn_logit_candidate_payload_design_only",
) -> dict:
    if candidate_sources is None:
        candidate_sources = ["turn_indicator_logits"]
    return {
        "analysis": {"name": "dp_camp_current_tick_tensor_visibility_v1"},
        "final_decision": {
            "status": status,
            "candidate_source_names": candidate_sources,
            "authorized_next_work": authorized_next_work,
            "new_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
        },
    }


def _write_sources(tmp_path: Path, *, include_hooks: bool = True) -> tuple[Path, Path]:
    replay = tmp_path / "run_diffusion_planner_camp_replay.py"
    integration = tmp_path / "diffusion_planner.py"
    if include_hooks:
        replay.write_text(
            "\n".join(
                [
                    "candidates, neighbor_predictions, turn_logits = generate_candidate_trajectories(",
                    "chosen_logits = turn_logits[selected_index].copy()",
                    "turn_indicators[ego_id] = 1",
                    "records.append({})",
                    "latency_ms_including_candidate_generation = 1.0",
                ]
            ),
            encoding="utf-8",
        )
        integration.write_text(
            "\n".join(
                [
                    "turn_logits = outputs.get(\"turn_indicator_logit\")",
                    "return ego_candidates, predictions[:, 1:], turn_logits",
                ]
            ),
            encoding="utf-8",
        )
    else:
        replay.write_text("records.append({})", encoding="utf-8")
        integration.write_text("return ego_candidates", encoding="utf-8")
    return replay, integration


def test_turn_logit_payload_design_ready(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path)

    report = analyze(
        visibility_report=_visibility(),
        replay_source=replay,
        integration_source=integration,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == (
        "default_off_turn_logit_payload_implementation_unit_tests_only"
    )
    assert decision["new_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["analysis"]["default_off_logging_only"] is True
    assert report["design_checks"]["atom_candidate_count"] == 3
    assert "not a classical Benders decomposition" in render_markdown(report)


def test_turn_logit_payload_design_blocks_wrong_visibility_source(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path)

    report = analyze(
        visibility_report=_visibility(candidate_sources=["turn_indicator_logits", "other"]),
        replay_source=replay,
        integration_source=integration,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_turn_logit_payload_design_rejects_missing_hooks(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path, include_hooks=False)

    report = analyze(
        visibility_report=_visibility(),
        replay_source=replay,
        integration_source=integration,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["design_checks"]["missing_source_hooks"]


def test_turn_logit_payload_design_rejects_outcome_field(tmp_path: Path) -> None:
    replay, integration = _write_sources(tmp_path)
    bad_field = PayloadFieldSpec(
        name="candidate_future_turn_correctness",
        shape="[K]",
        dtype="bool",
        source="candidate_closed_loop_outcomes",
        null_behavior="invalid",
        finite_check="invalid",
        latency_bucket="latency_ms_turn_logit_payload",
        uses_future_outcomes=True,
    )

    report = analyze(
        visibility_report=_visibility(),
        replay_source=replay,
        integration_source=integration,
        payload_fields=(bad_field,),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["design_checks"]["invalid_payload_fields"] == [
        "candidate_future_turn_correctness"
    ]


def test_turn_logit_payload_design_cli_writes_json_and_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay, integration = _write_sources(tmp_path)
    visibility = tmp_path / "visibility.json"
    output_json = tmp_path / "design.json"
    output_md = tmp_path / "design.md"
    visibility.write_text(json.dumps(_visibility()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--tensor_visibility_json",
            str(visibility),
            "--replay_source",
            str(replay),
            "--integration_source",
            str(integration),
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
    assert "Turn-Logit Payload Design" in output_md.read_text(encoding="utf-8")
