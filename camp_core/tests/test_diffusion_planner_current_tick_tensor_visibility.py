from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_current_tick_tensor_visibility import (
    analyze,
    main,
    render_markdown,
)


def _post_closure(
    status: str = "post_closure_state_remainder_requires_source_visibility_inventory",
    *,
    closed_families: list[str] | None = None,
):
    if closed_families is None:
        closed_families = [
            "non_turn_interaction_family",
            "observable_interaction_family",
            "progress_lane_hard_context",
            "relaxed_strict_atom_family",
            "revised_context_atom_family",
            "turn_logit_atom_family",
        ]
    return {
        "analysis": {"name": "dp_camp_post_closure_state_remainder_v1"},
        "required_closed_score_families": closed_families,
        "final_decision": {
            "status": status,
            "authorized_next_work": "read_only_current_tick_tensor_visibility_inventory_only",
            "missing_closed_score_families": [],
            "new_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
        },
    }


def test_tensor_visibility_finds_unclosed_dp_prior_candidate_source(tmp_path) -> None:
    source = tmp_path / "wrapper.py"
    source.write_text(
        "\n".join(
            [
                "candidate_score = outputs.get('log_prob')",
                "return ego_candidates, predictions[:, 1:], candidate_score",
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
        "predeclare_default_off_dp_prior_score_payload_design_only"
    )
    assert decision["candidate_source_names"] == ["dp_native_log_probability_or_score"]
    assert decision["closed_visible_candidate_source_names"] == []
    assert decision["new_replay_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert "not a classical Benders decomposition" in render_markdown(report)


def test_tensor_visibility_rejects_already_closed_turn_logits_source(tmp_path) -> None:
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
    )

    decision = report["final_decision"]
    assert decision["status"] == "current_tick_tensor_visibility_no_new_candidate_source"
    assert decision["primary_gap"] == "visible_candidate_tensor_sources_already_closed"
    assert decision["candidate_source_names"] == []
    assert decision["closed_visible_candidate_source_names"] == [
        "turn_indicator_logits"
    ]
    rows = {row["name"]: row for row in report["tensor_sources"]}
    assert rows["turn_indicator_logits"]["visibility_status"] == (
        "visible_but_score_family_closed"
    )
    assert rows["turn_indicator_logits"]["closed_by_score_inventory"] is True
    assert decision["online_selector_authorized"] is False


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


def test_tensor_visibility_fails_closed_when_post_closure_is_stale(tmp_path) -> None:
    source = tmp_path / "wrapper.py"
    source.write_text("turn_logits = outputs.get('turn_indicator_logit')", encoding="utf-8")
    stale = _post_closure()
    stale["required_closed_score_families"] = [
        family
        for family in stale["required_closed_score_families"]
        if family != "non_turn_interaction_family"
    ]

    report = analyze(
        post_closure_remainder=stale,
        source_files=[source],
        source_roots=[],
    )

    decision = report["final_decision"]
    assert decision["status"] == "current_tick_tensor_visibility_source_not_ready"
    assert decision["primary_gap"] == (
        "post_closure_remainder_missing_current_score_inventory_closure"
    )
    assert decision["authorized_next_work"] == (
        "refresh_post_closure_remainder_before_tensor_inventory"
    )
    assert decision["new_replay_authorized"] is False
    assert report["source_gate"]["stale"] is True
    assert report["source_gate"]["missing_required_closed_score_families"] == [
        "non_turn_interaction_family"
    ]


def test_tensor_visibility_source_root_excludes_tests_and_analysis_scripts(tmp_path) -> None:
    tests_dir = tmp_path / "camp_core" / "tests"
    scripts_dir = tmp_path / "scripts" / "integrations"
    runtime_dir = tmp_path / "camp_core" / "integrations"
    tests_dir.mkdir(parents=True)
    scripts_dir.mkdir(parents=True)
    runtime_dir.mkdir(parents=True)
    (tests_dir / "test_fake.py").write_text(
        "candidate_score = outputs.get('log_prob')",
        encoding="utf-8",
    )
    (scripts_dir / "analysis_fake.py").write_text(
        "denois = state.residual",
        encoding="utf-8",
    )
    runtime = runtime_dir / "wrapper.py"
    runtime.write_text(
        "turn_logits = outputs.get('turn_indicator_logit')",
        encoding="utf-8",
    )

    report = analyze(
        post_closure_remainder=_post_closure(),
        source_files=[runtime],
        source_roots=[tmp_path],
    )

    decision = report["final_decision"]
    assert decision["status"] == "current_tick_tensor_visibility_no_new_candidate_source"
    assert decision["candidate_source_names"] == []
    assert decision["closed_visible_candidate_source_names"] == [
        "turn_indicator_logits"
    ]
    discovered = report["inputs"]["discovered_python_files"]
    assert str(runtime) in discovered
    assert not any("test_fake.py" in path for path in discovered)
    assert not any("analysis_fake.py" in path for path in discovered)


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
    assert payload["final_decision"]["status"] == (
        "current_tick_tensor_visibility_no_new_candidate_source"
    )
    assert payload["final_decision"]["closed_visible_candidate_source_names"] == [
        "turn_indicator_logits"
    ]
    assert "Current-Tick Tensor Visibility" in output_md.read_text(encoding="utf-8")
