from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_current_tick_tensor_visibility import (
    analyze,
    main,
    render_markdown,
)


def _post_closure(status: str = "post_closure_state_remainder_requires_source_visibility_inventory"):
    return {
        "analysis": {"name": "dp_camp_post_closure_state_remainder_v1"},
        "final_decision": {
            "status": status,
            "authorized_next_work": "read_only_current_tick_tensor_visibility_inventory_only",
            "new_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
        },
    }


def test_tensor_visibility_finds_turn_logits_candidate_source(tmp_path) -> None:
    source = tmp_path / "wrapper.py"
    source.write_text(
        "\n".join(
            [
                "turn_logits = outputs.get('turn_indicator_logit')",
                "return ego_candidates, predictions[:, 1:], turn_logits",
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        post_closure_remainder=_post_closure(),
        source_files=[source],
        source_roots=[],
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "current_tick_tensor_visibility_has_candidate_source"
    assert decision["authorized_next_work"] == (
        "predeclare_default_off_turn_logit_candidate_payload_design_only"
    )
    assert decision["candidate_source_names"] == ["turn_indicator_logits"]
    assert decision["new_replay_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "not a classical Benders decomposition" in render_markdown(report)


def test_tensor_visibility_rejects_generator_control_only(tmp_path) -> None:
    source = tmp_path / "wrapper.py"
    source.write_text(
        "latent = torch.randn(1); expanded['sampled_trajectories'] = latent",
        encoding="utf-8",
    )

    report = analyze(
        post_closure_remainder=_post_closure(),
        source_files=[source],
        source_roots=[],
    )

    decision = report["final_decision"]
    assert decision["status"] == "current_tick_tensor_visibility_no_new_candidate_source"
    rows = {row["name"]: row for row in report["tensor_sources"]}
    assert rows["wrapper_sampled_latent_noise"]["visibility_status"] == (
        "visible_but_not_runtime_admissible"
    )
    assert decision["online_selector_authorized"] is False


def test_tensor_visibility_fails_closed_when_post_closure_source_not_ready(tmp_path) -> None:
    source = tmp_path / "wrapper.py"
    source.write_text("turn_logits = outputs.get('turn_indicator_logit')", encoding="utf-8")

    report = analyze(
        post_closure_remainder=_post_closure(status="wrong_status"),
        source_files=[source],
        source_roots=[],
    )

    decision = report["final_decision"]
    assert decision["status"] == "current_tick_tensor_visibility_source_not_ready"
    assert decision["closed_loop_smoke_authorized"] is False


def test_tensor_visibility_cli_writes_json_and_markdown(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    post = tmp_path / "post.json"
    source = tmp_path / "wrapper.py"
    output_json = tmp_path / "visibility.json"
    output_md = tmp_path / "visibility.md"
    post.write_text(json.dumps(_post_closure()), encoding="utf-8")
    source.write_text(
        "turn_logits = outputs.get('turn_indicator_logit')",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze",
            "--post_closure_remainder_json",
            str(post),
            "--source_file",
            str(source),
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
    assert (
        payload["final_decision"]["status"]
        == "current_tick_tensor_visibility_has_candidate_source"
    )
    assert "Current-Tick Tensor Visibility" in output_md.read_text(encoding="utf-8")
