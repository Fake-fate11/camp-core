from __future__ import annotations

import json

import pytest

from scripts.integrations.plan_diffusion_planner_no_leak_score_family_inventory import (
    build_report,
    main,
    render_markdown,
)


def _evidence(
    name: str,
    status: str,
    *,
    authorized_next_work: str | None = None,
    **flags: bool,
) -> dict[str, object]:
    decision = {
        "status": status,
        "authorized_next_work": authorized_next_work,
        "closed_loop_smoke_authorized": False,
        "new_replay_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    decision.update(flags)
    return {
        "name": name,
        "path": f"/fake/{name}.json",
        "payload": {
            "analysis": {"name": f"{name}_analysis"},
            "final_decision": decision,
        },
    }


def _all_rejected_evidence() -> list[dict[str, object]]:
    return [
        _evidence(
            "progress_lane_hard_context_descriptor",
            "progress_lane_hard_context_descriptor_separability_rejected",
        ),
        _evidence(
            "revised_context_atom_separability",
            "revised_progress_lane_hard_context_atom_separability_rejected",
        ),
        _evidence(
            "relaxed_strict_atom_limit",
            "relaxed_strict_atom_observability_limit_recorded",
        ),
        _evidence(
            "observable_interaction_route",
            "observable_interaction_route_support_discovery_rejected",
        ),
        _evidence(
            "turn_logit_atom_bottleneck",
            "turn_logit_atom_bottleneck_diagnosed",
        ),
        _evidence(
            "non_turn_logit_interaction_bottleneck",
            "non_turn_logit_interaction_bottleneck_diagnosed",
        ),
    ]


def test_inventory_requires_new_design_when_known_score_families_are_closed() -> None:
    report = build_report(_all_rejected_evidence(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == "no_leak_score_family_inventory_requires_new_design"
    assert decision["authorized_next_work"] == (
        "predeclare_new_current_tick_no_leak_descriptor_family_or_"
        "observable_state_inventory_design_only"
    )
    assert decision["new_replay_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert decision["missing_or_inconclusive_families"] == []

    families = {row["name"]: row for row in report["score_families"]}
    assert families["progress_lane_hard_context"]["status"] == "rejected_or_limited"
    assert families["revised_context_atom_family"]["status"] == "rejected_or_limited"
    assert families["relaxed_strict_atom_family"]["status"] == "rejected_or_limited"
    assert families["observable_interaction_family"]["status"] == "rejected_or_limited"
    assert families["turn_logit_atom_family"]["status"] == "rejected_or_limited"
    assert families["non_turn_interaction_family"]["status"] == "rejected_or_limited"

    markdown = render_markdown(report)
    assert "No-Leak Score-Family Inventory" in markdown
    assert "not a classical Benders decomposition" in markdown


def test_inventory_fails_closed_with_missing_family_evidence() -> None:
    report = build_report(
        [
            _evidence(
                "progress_lane_hard_context_descriptor",
                "progress_lane_hard_context_descriptor_separability_rejected",
            ),
            _evidence(
                "observable_interaction_route",
                "observable_interaction_route_support_discovery_rejected",
            ),
            _evidence(
                "non_turn_logit_interaction_bottleneck",
                "non_turn_logit_interaction_bottleneck_diagnosed",
            ),
        ]
    )

    decision = report["final_decision"]
    assert decision["status"] == "no_leak_score_family_inventory_incomplete_evidence"
    assert "revised_context_atom_family" in decision["missing_or_inconclusive_families"]
    assert "relaxed_strict_atom_family" in decision["missing_or_inconclusive_families"]
    assert "turn_logit_atom_family" in decision["missing_or_inconclusive_families"]
    assert decision["closed_loop_smoke_authorized"] is False


def test_inventory_fails_closed_with_unclosed_support_family() -> None:
    report = build_report(
        [
            _evidence(
                "progress_lane_hard_context_descriptor",
                "progress_lane_hard_context_descriptor_separability_rejected",
            ),
            _evidence(
                "revised_context_atom_preflight",
                "revised_context_atom_schema_preflight_ready",
            ),
            _evidence(
                "relaxed_strict_atom_limit",
                "relaxed_strict_atom_observability_limit_recorded",
            ),
            _evidence(
                "observable_interaction_route",
                "observable_interaction_route_support_discovery_rejected",
            ),
            _evidence(
                "turn_logit_atom_bottleneck",
                "turn_logit_atom_bottleneck_diagnosed",
            ),
            _evidence(
                "non_turn_logit_interaction_bottleneck",
                "non_turn_logit_interaction_bottleneck_diagnosed",
            ),
        ]
    )

    decision = report["final_decision"]
    assert decision["status"] == "no_leak_score_family_inventory_has_unclosed_support"
    assert decision["unclosed_support_families"] == ["revised_context_atom_family"]
    assert decision["new_replay_authorized"] is False


def test_inventory_rejects_source_authorization_conflict() -> None:
    report = build_report(
        [
            *_all_rejected_evidence()[:-1],
            _evidence(
                "observable_interaction_route",
                "observable_interaction_route_support_discovery_rejected",
                online_selector_authorized=True,
            ),
        ]
    )

    decision = report["final_decision"]
    assert decision["status"] == "no_leak_score_family_inventory_source_conflict"
    assert decision["source_authorization_conflicts"] == [
        "observable_interaction_route:online_selector_authorized"
    ]


def test_inventory_cli_writes_json_and_markdown(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths: list[str] = []
    for item in _all_rejected_evidence():
        path = tmp_path / f"{item['name']}.json"
        path.write_text(json.dumps(item["payload"]), encoding="utf-8")
        paths.extend(["--family_json", f"{item['name']}={path}"])

    output_json = tmp_path / "inventory.json"
    output_md = tmp_path / "inventory.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            *paths,
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
        == "no_leak_score_family_inventory_requires_new_design"
    )
    assert "No-Leak Score-Family Inventory" in output_md.read_text(encoding="utf-8")
