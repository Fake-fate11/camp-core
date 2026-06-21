from __future__ import annotations

import json

import pytest

from scripts.integrations.plan_diffusion_planner_external_context_payload_design import (
    REQUIRED_DESIGN_CANDIDATES,
    build_report,
    main,
    render_markdown,
)


def _inventory(*, status: str = "external_source_visibility_inventory_has_design_candidate"):
    return {
        "final_decision": {
            "status": status,
            "passed": status == "external_source_visibility_inventory_has_design_candidate",
            "authorized_next_work": (
                "predeclare_default_off_external_context_payload_design_only"
            ),
            "design_candidate_names": list(REQUIRED_DESIGN_CANDIDATES),
            "training_execution_authorized": False,
            "closed_loop_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def test_payload_design_ready_from_inventory() -> None:
    report = build_report(inventory=_inventory(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == "external_context_payload_design_ready"
    assert decision["authorized_next_work"] == (
        "default_off_external_context_payload_implementation_unit_tests_only"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    families = {row["family"]: row for row in report["family_reports"]}
    assert set(families) == set(REQUIRED_DESIGN_CANDIDATES)
    assert all(row["passed"] for row in families.values())
    assert "not a classical Benders decomposition" in render_markdown(report)


def test_payload_design_blocks_when_inventory_not_ready() -> None:
    report = build_report(inventory=_inventory(status="wrong_status"))

    decision = report["final_decision"]
    assert decision["status"] == "external_context_payload_design_source_not_ready"
    assert decision["authorized_next_work"] is None
    assert decision["formal_seeds_authorized"] is False


def test_payload_design_blocks_when_required_candidate_missing() -> None:
    source = _inventory()
    source["final_decision"]["design_candidate_names"] = [
        "traffic_signal_phase_timing_or_right_of_way_state"
    ]

    report = build_report(inventory=source)

    decision = report["final_decision"]
    assert decision["status"] == "external_context_payload_design_source_not_ready"
    source_gate = report["source_inventory_gate"]
    assert source_gate["missing_required_design_candidates"] == [
        "route_speed_limit_and_control_context"
    ]


def test_payload_fields_satisfy_math_contract() -> None:
    report = build_report(inventory=_inventory())

    assert report["field_specs"]
    for field in report["field_specs"]:
        assert field["passed"] is True
        checks = field["math_checks"]
        assert checks["default_off"] is True
        assert checks["selection_effect_free"] is True
        assert checks["no_future_outcome_leakage"] is True
        assert checks["no_dp_modification"] is True
        assert checks["candidate_shaped"] is True
        assert checks["has_latency_bucket"] is True
        assert checks["atomization_nonnegative_or_signed_split"] is True
        assert checks["affine_or_convex_note"] is True


def test_payload_design_cli_writes_json_and_markdown(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = tmp_path / "inventory.json"
    output_json = tmp_path / "design.json"
    output_md = tmp_path / "design.md"
    inventory.write_text(json.dumps(_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "payload-design",
            "--inventory_json",
            str(inventory),
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
    assert payload["final_decision"]["status"] == "external_context_payload_design_ready"
    assert "External Context Payload Design" in output_md.read_text(encoding="utf-8")
