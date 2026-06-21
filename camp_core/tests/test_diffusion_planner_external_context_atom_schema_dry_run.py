from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import numpy as np

from camp_core.integrations.diffusion_planner_external_context_payload import (
    EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS,
    build_external_context_payload,
)
from scripts.integrations.analyze_diffusion_planner_external_context_atom_schema_dry_run import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    analyze,
    main,
)
from scripts.integrations.plan_diffusion_planner_external_context_atomization_preflight import (
    build_report as build_atomization_report,
)


def _candidates(*, fast_second: bool = True) -> np.ndarray:
    second = [[0.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0], [4.0, 0.0, 1.0, 0.0]]
    if not fast_second:
        second = [[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0]]
    return np.asarray(
        [
            [[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 1.0, 0.0], [2.0, 0.0, 1.0, 0.0]],
            second,
        ],
        dtype=np.float64,
    )


def _route() -> np.ndarray:
    return np.asarray(
        [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0], [3.0, 0.0]],
        dtype=np.float64,
    )


def _payload(*, material: bool = True) -> dict:
    return build_external_context_payload(
        candidates=_candidates(fast_second=material),
        route_centerline_ego=_route(),
        route_speed_limit_mps=1.5 if material else 3.0,
        route_has_speed_limit=True,
        support_steps=3,
        dt_s=1.0,
    )


def _record(payload: dict) -> dict:
    record = {
        "selected_index": 0,
        "candidate_closed_loop_outcomes": None,
        "external_context_payload_logging": payload,
    }
    record.update(
        {key: float(payload["latency_ms"][key]) for key in EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS}
    )
    return record


def _write_log(root: Path, *, payload: dict | None = None, records: int = 2) -> None:
    root.mkdir(parents=True)
    payload = _payload(material=True) if payload is None else payload
    root.joinpath("camp_selection_log.json").write_text(
        json.dumps([_record(payload) for _ in range(records)]),
        encoding="utf-8",
    )


def _materiality(*, material: bool = True) -> dict[str, object]:
    return {
        "field_reports": [
            {
                "family": "route_speed",
                "field": "candidate_speed_limit_excess_integral_mps",
                "material": material,
            }
        ],
        "material_families": ["route_speed"] if material else [],
        "final_decision": {
            "status": "external_context_payload_materiality_ready",
            "passed": True,
            "authorized_next_work": (
                "external_context_payload_atomization_preflight_existing_smoke_only"
            ),
            "new_replay_authorized": False,
            "closed_loop_replay_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def _signal_arrival_atomization() -> dict:
    atomization = build_atomization_report(
        materiality={
            "field_reports": [
                {
                    "family": "traffic_signal",
                    "field": "candidate_first_signal_arrival_time_s",
                    "material": True,
                }
            ],
            "material_families": ["traffic_signal"],
            "final_decision": {
                "status": "external_context_payload_materiality_ready",
                "passed": True,
                "authorized_next_work": (
                    "external_context_payload_atomization_preflight_existing_smoke_only"
                ),
                "new_replay_authorized": False,
                "closed_loop_replay_authorized": False,
                "camp_retraining_authorized": False,
                "formal_seeds_authorized": False,
                "dp_modification_authorized": False,
                "classic_benders_claim_authorized": False,
            },
        }
    )
    assert atomization["final_decision"]["selected_atom_candidate_names"] == [
        "signal_arrival_time_reaches_control_v1"
    ]
    return atomization


def _atomization(*, ready: bool = True, material: bool = True) -> dict:
    report = build_atomization_report(materiality=_materiality(material=material))
    if not ready:
        report = deepcopy(report)
        report["final_decision"]["status"] = "external_context_atomization_preflight_rejected"
        report["final_decision"]["passed"] = False
        report["final_decision"]["authorized_next_work"] = None
    return report


def test_external_context_atom_schema_dry_run_accepts_route_speed_atom(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root)

    report = analyze(
        atomization=_atomization(),
        candidate_root=candidate_root,
        expected_records=2,
        expected_candidates=2,
        label="unit",
    )

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
    assert report["dry_run_summary"]["ranking_signal_records"] == 2
    assert report["dry_run_summary"]["top1_preservation_rate"] == 1.0
    assert report["dry_run_records"][0]["combined_atom_score"] == [0.0, 1.0]
    assert report["dry_run_records"][0]["atom_best_index"] == 0
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_external_context_atom_schema_dry_run_maps_missing_signal_arrival_to_zero(
    tmp_path: Path,
) -> None:
    payload = _payload(material=False)
    payload["candidate_first_signal_arrival_time_s"] = [None, 2.0]
    payload["field_shapes"]["candidate_first_signal_arrival_time_s"] = [2]
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root, payload=payload, records=1)

    report = analyze(
        atomization=_signal_arrival_atomization(),
        candidate_root=candidate_root,
        expected_records=1,
        expected_candidates=2,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["selected_atom_candidate_names"] == [
        "signal_arrival_time_reaches_control_v1"
    ]
    assert report["dry_run_records"][0]["atom_scores"][
        "signal_arrival_time_reaches_control_v1"
    ] == [0.0, 1.0]
    assert report["dry_run_records"][0]["atom_best_index"] == 0


def test_external_context_atom_schema_dry_run_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root)

    report = analyze(
        atomization=_atomization(ready=False),
        candidate_root=candidate_root,
        expected_records=2,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "source_status_ready",
        "source_passed",
        "source_authorizes_dry_run",
    ]


def test_external_context_atom_schema_dry_run_rejects_no_selected_atoms(
    tmp_path: Path,
) -> None:
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root)
    atomization = _atomization()
    atomization["final_decision"]["selected_atom_candidate_names"] = []
    atomization["selected_atom_candidates"] = []

    report = analyze(
        atomization=atomization,
        candidate_root=candidate_root,
        expected_records=2,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed_source = [
        check["name"] for check in report["source_checks"] if not check["passed"]
    ]
    failed_dry_run = [
        check["name"] for check in report["dry_run_checks"] if not check["passed"]
    ]
    assert failed_source == ["source_selected_atoms_nonempty"]
    assert failed_dry_run == [
        "selected_atom_specs_nonempty",
        "all_records_have_valid_atom_scores",
    ]


def test_external_context_atom_schema_dry_run_rejects_leaky_payload(
    tmp_path: Path,
) -> None:
    payload = _payload(material=True)
    payload["future_outcome_leakage"] = True
    candidate_root = tmp_path / "candidate"
    _write_log(candidate_root, payload=payload)

    report = analyze(
        atomization=_atomization(),
        candidate_root=candidate_root,
        expected_records=2,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["record_checks"] if not check["passed"]]
    assert failed == [
        "record_0_future_outcome_leakage",
        "record_1_future_outcome_leakage",
    ]


def test_external_context_atom_schema_dry_run_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate_root = tmp_path / "candidate"
    atomization_path = tmp_path / "atomization.json"
    output_json = tmp_path / "dry_run.json"
    output_md = tmp_path / "dry_run.md"
    _write_log(candidate_root)
    atomization_path.write_text(json.dumps(_atomization()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-atom-schema-dry-run",
            "--atomization_json",
            str(atomization_path),
            "--candidate_root",
            str(candidate_root),
            "--expected_records",
            "2",
            "--expected_candidates",
            "2",
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
    assert "External Context Atom Schema Dry Run" in output_md.read_text(
        encoding="utf-8"
    )
