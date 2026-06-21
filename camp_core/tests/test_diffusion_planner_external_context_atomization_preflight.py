from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_external_context_atomization_preflight import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


def _materiality(*, ready: bool = True, material: bool = True) -> dict[str, object]:
    fields = [
        {
            "family": "route_speed",
            "field": "candidate_speed_limit_excess_integral_mps",
            "material": material,
        },
        {
            "family": "route_speed",
            "field": "candidate_route_speed_limit_min_mps",
            "material": False,
        },
    ]
    return {
        "field_reports": fields,
        "material_families": ["route_speed"] if material else [],
        "final_decision": {
            "status": (
                "external_context_payload_materiality_ready"
                if ready
                else "external_context_payload_materiality_rejected"
            ),
            "passed": ready,
            "authorized_next_work": (
                "external_context_payload_atomization_preflight_existing_smoke_only"
                if ready
                else None
            ),
            "new_replay_authorized": False,
            "closed_loop_replay_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def test_external_context_atomization_preflight_accepts_material_speed_excess() -> None:
    report = build_report(materiality=_materiality(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert decision["selected_atom_candidate_names"] == [
        "route_speed_limit_excess_integral_v1"
    ]
    selected = report["selected_atom_candidates"][0]
    assert selected["source_field"] == "candidate_speed_limit_excess_integral_mps"
    assert selected["math_checks"]["nonnegative_or_hinged"] is True
    assert selected["math_checks"]["affine_score"] is True
    assert selected["math_checks"]["convex_master"] is True
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_external_context_atomization_preflight_rejects_source_not_ready() -> None:
    report = build_report(materiality=_materiality(ready=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["preflight_checks"] if not check["passed"]]
    assert failed == [
        "source_status_ready",
        "source_passed",
        "source_authorizes_atomization_preflight",
    ]


def test_external_context_atomization_preflight_rejects_no_material_fields() -> None:
    report = build_report(materiality=_materiality(material=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["selected_atom_candidate_names"] == []
    failed = [check["name"] for check in report["preflight_checks"] if not check["passed"]]
    assert failed == ["at_least_one_atom_candidate_material"]


def test_external_context_atomization_preflight_rejects_authorization_conflict() -> None:
    materiality = deepcopy(_materiality())
    materiality["final_decision"]["new_replay_authorized"] = True

    report = build_report(materiality=materiality)

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["preflight_checks"] if not check["passed"]]
    assert failed == ["source_blocked_action_conflicts_empty"]


def test_external_context_atomization_preflight_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    materiality_path = tmp_path / "materiality.json"
    output_json = tmp_path / "atomization.json"
    output_md = tmp_path / "atomization.md"
    materiality_path.write_text(json.dumps(_materiality()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-atomization-preflight",
            "--materiality_json",
            str(materiality_path),
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
    assert "External Context Atomization Preflight" in output_md.read_text(
        encoding="utf-8"
    )
