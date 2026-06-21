from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_current_observable_separability_bridge import (
    DUPLICATE_REJECT_STATUS,
    EVIDENCE_MISSING_STATUS,
    MATERIALLY_NEW_READY_STATUS,
    SOURCE_NOT_READY_STATUS,
    build_report,
    main,
)


MATERIAL_FIELDS = [
    "candidate_route_segment_index",
    "candidate_route_projection_s_m",
    "candidate_route_lateral_error_m",
    "candidate_red_stopline_distance_m",
    "candidate_red_heading_alignment",
    "candidate_route_heading_change_rad",
    "candidate_min_obstacle_clearance_lower_bound_m",
]


def _coverage(
    *,
    status: str = "observable_state_payload_coverage_ready_for_offline_separability_design",
    material_fields: list[str] | None = None,
    records: int = 48,
    candidate_rows: int = 384,
) -> dict[str, object]:
    return {
        "counts": {
            "records": records,
            "payload_records": records,
            "candidate_rows": candidate_rows,
        },
        "context": {
            "red_context_records": 24,
            "obstacle_context_records": 4,
        },
        "material_candidate_fields": material_fields or list(MATERIAL_FIELDS),
        "final_decision": {
            "status": status,
            "validation_passed": status.endswith("ready_for_offline_separability_design"),
            "materiality_gate_passed": status.endswith("ready_for_offline_separability_design"),
            "records_total": records,
            "payload_records": records,
            "authorized_next_work": (
                "offline_no_leak_observable_descriptor_separability_design_only"
                if status.endswith("ready_for_offline_separability_design")
                else None
            ),
        },
    }


def _contract(*, status: str = "matched_observable_outcome_contract_passed") -> dict:
    return {
        "counts": {"records": 48, "candidate_rows": 384},
        "final_decision": {
            "status": status,
            "passed": status == "matched_observable_outcome_contract_passed",
            "authorized_next_work": "offline_observable_descriptor_separability_screen_only",
        },
    }


def _observable_separability(
    *,
    status: str = "matched_observable_descriptor_separability_rejected",
    records: int = 48,
    candidate_rows: int = 384,
    source_fields: list[str] | None = None,
    promising_screen_count: int = 0,
    formal_seed_records: int = 0,
) -> dict[str, object]:
    fields = source_fields or list(MATERIAL_FIELDS)
    return {
        "analysis": {
            "feature_specs": [
                {"name": f"{field}_feature", "source_field": field}
                for field in fields
            ]
        },
        "records": {
            "total_records": records,
            "candidate_rows": candidate_rows,
            "formal_seed_records": formal_seed_records,
        },
        "failure_gap": {
            "primary_gap": (
                "observable_descriptors_do_not_separate_beneficial_and_harmful_candidates"
            )
        },
        "final_decision": {
            "status": status,
            "passed": False,
            "primary_gap": (
                "observable_descriptors_do_not_separate_beneficial_and_harmful_candidates"
            ),
            "promising_screen_count": promising_screen_count,
            "authorized_next_work": "diagnose_observable_descriptor_bottleneck_before_new_replay",
        },
    }


def _constrained_affine(
    *, status: str = "constrained_affine_upper_bound_rejected"
) -> dict[str, object]:
    return {
        "failure_gap": {"primary_gap": "allowed_harmful_rate_too_high"},
        "final_decision": {
            "status": status,
            "passed": False,
            "authorized_next_work": "reject_observable_route_or_design_new_logging_preflight",
        },
    }


def _affine_residual(
    *, status: str = "affine_allowed_harmful_residual_diagnosed"
) -> dict[str, object]:
    return {
        "records": {"formal_seed_records": 0},
        "final_decision": {"status": status, "passed": True},
    }


def test_current_observable_bridge_rejects_duplicate_rejected_route() -> None:
    report = build_report(
        current_payload_coverage=_coverage(),
        matched_contract=_contract(),
        observable_separability=_observable_separability(),
        constrained_affine=_constrained_affine(),
        affine_residual=_affine_residual(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == DUPLICATE_REJECT_STATUS
    assert decision["closure_gate_passed"] is True
    assert decision["authorized_next_work"] == (
        "proof_objective_or_new_descriptor_family_design_only"
    )
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert report["equivalence"]["duplicate_route_evidence"] is True
    assert report["equivalence"][
        "current_material_fields_covered_by_old_observable_family"
    ] is True


def test_current_observable_bridge_blocks_when_current_coverage_not_ready() -> None:
    report = build_report(
        current_payload_coverage=_coverage(
            status="observable_state_payload_coverage_insufficient_for_materiality",
            records=3,
            candidate_rows=24,
        ),
        matched_contract=_contract(),
        observable_separability=_observable_separability(),
        constrained_affine=_constrained_affine(),
    )

    assert report["final_decision"]["status"] == SOURCE_NOT_READY_STATUS
    assert report["final_decision"]["closure_gate_passed"] is False
    failed = [
        check["name"]
        for check in report["source_checks"]
        if not check["passed"]
        and check["group"] == "current_payload_coverage"
    ]
    assert "current_coverage_ready_status" in failed


def test_current_observable_bridge_blocks_when_old_matched_evidence_is_incomplete() -> None:
    report = build_report(
        current_payload_coverage=_coverage(),
        matched_contract=_contract(
            status="matched_observable_outcome_contract_rejected"
        ),
        observable_separability=_observable_separability(),
        constrained_affine=_constrained_affine(),
    )

    assert report["final_decision"]["status"] == EVIDENCE_MISSING_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "locate_or_generate_matched_observable_route_evidence_before_rerun"
    )


def test_current_observable_bridge_allows_only_predeclared_new_route_when_field_is_new() -> None:
    fields = [*MATERIAL_FIELDS, "candidate_visibility_margin_m"]
    report = build_report(
        current_payload_coverage=_coverage(material_fields=fields),
        matched_contract=_contract(),
        observable_separability=_observable_separability(source_fields=MATERIAL_FIELDS),
        constrained_affine=_constrained_affine(),
    )

    assert report["final_decision"]["status"] == MATERIALLY_NEW_READY_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["equivalence"]["materially_new_route"] is True
    assert report["equivalence"]["uncovered_current_material_fields"] == [
        "candidate_visibility_margin_m"
    ]


def test_current_observable_bridge_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    coverage_path = tmp_path / "coverage.json"
    contract_path = tmp_path / "contract.json"
    separability_path = tmp_path / "separability.json"
    affine_path = tmp_path / "affine.json"
    residual_path = tmp_path / "residual.json"
    output_json = tmp_path / "bridge.json"
    output_md = tmp_path / "bridge.md"
    coverage_path.write_text(json.dumps(_coverage()), encoding="utf-8")
    contract_path.write_text(json.dumps(_contract()), encoding="utf-8")
    separability_path.write_text(
        json.dumps(_observable_separability()),
        encoding="utf-8",
    )
    affine_path.write_text(json.dumps(_constrained_affine()), encoding="utf-8")
    residual_path.write_text(json.dumps(_affine_residual()), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "current_observable_separability_bridge",
            "--current_payload_coverage_json",
            str(coverage_path),
            "--matched_contract_json",
            str(contract_path),
            "--observable_separability_json",
            str(separability_path),
            "--constrained_affine_json",
            str(affine_path),
            "--affine_residual_json",
            str(residual_path),
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
    assert payload["final_decision"]["status"] == DUPLICATE_REJECT_STATUS
    assert "Current Observable Separability Bridge" in output_md.read_text(
        encoding="utf-8"
    )
