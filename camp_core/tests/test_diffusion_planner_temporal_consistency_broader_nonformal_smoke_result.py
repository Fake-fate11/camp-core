from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.summarize_diffusion_planner_temporal_consistency_broader_nonformal_smoke_result import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    build_report,
    main,
)


def _plan() -> dict:
    runs = [{"run_id": f"run_{idx}"} for idx in range(5)]
    return {
        "final_decision": {
            "status": "temporal_consistency_broader_nonformal_smoke_plan_ready",
            "passed": True,
            "authorized_next_work": (
                "default_off_temporal_consistency_broader_nonformal_paired_smoke_only"
            ),
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
            "atom_promotion_authorized": False,
        },
        "plan_spec": {"runs": runs, "steps": 10, "num_candidates": 8},
        "coverage_targets": {
            "planned_records": 50,
            "planned_candidate_rows": 400,
            "expected_payload_records_per_run": 10,
            "expected_available_payload_records_min_per_run": 9,
            "expected_first_tick_fail_closed_per_run": 1,
            "max_payload_latency_ms": 2.0,
            "scenario_bucket_counts": {
                "traffic_light": 2,
                "red_light_turn": 2,
                "sharp_turn": 3,
                "npc_interaction": 3,
                "normal": 1,
                "lane_change": 1,
            },
        },
    }


def _selector(*, equivalent: bool = True, records: int = 50) -> dict:
    mismatch = 0 if equivalent else 1
    return {
        "equivalent": equivalent,
        "records": records,
        "exact_field_mismatches": {"selected_index": mismatch},
        "numeric_field_mismatches": {"scores": 0},
        "numeric_shape_mismatches": {"scores": 0},
        "numeric_nonexact_entries": {"scores": 0},
    }


def _dataset(*, passed: bool = True) -> dict:
    return {"passed": passed, "errors": [] if passed else ["bad_dataset"]}


def _payload(run_id: str, *, latency_max: float = 0.1, passed: bool = True) -> dict:
    return {
        "analysis": {
            "candidate_root": (
                "/root/autodl-tmp/camp_dp_temporal_consistency/"
                f"logging_enabled/{run_id}"
            )
        },
        "counts": {
            "candidate_records": 10,
            "candidate_payload_records": 10,
            "available_payload_records": 9,
            "first_tick_fail_closed_records": 1,
        },
        "latency_ms": {
            "latency_ms_temporal_consistency_payload": {
                "count": 10,
                "mean": 0.05,
                "max": latency_max,
            }
        },
        "errors": [],
        "final_decision": {
            "status": (
                "temporal_consistency_payload_smoke_audit_passed"
                if passed
                else "temporal_consistency_payload_smoke_audit_rejected"
            ),
            "passed": passed,
        },
    }


def _payloads(**kwargs: object) -> list[dict]:
    return [_payload(f"run_{idx}", **kwargs) for idx in range(5)]


def test_temporal_consistency_broader_result_accepts_passed_smoke() -> None:
    report = build_report(
        plan=_plan(),
        selector_equivalence=_selector(),
        dataset_audit=_dataset(),
        payload_audits=_payloads(),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["runtime_equivalence_ready"] is True
    assert report["final_decision"]["coverage_ready_for_materiality_diagnosis"] is True
    assert report["final_decision"]["safety_benefit_evidence"] is False
    assert report["final_decision"]["atom_promotion_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["payload_summary"]["total_records"] == 50
    assert report["payload_summary"]["total_available_records"] == 45
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_temporal_consistency_broader_result_rejects_selector_mismatch() -> None:
    report = build_report(
        plan=_plan(),
        selector_equivalence=_selector(equivalent=False),
        dataset_audit=_dataset(),
        payload_audits=_payloads(),
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "selector_equivalent" in report["final_decision"]["failed_checks"]
    assert "selector_exact_mismatch_total" in report["final_decision"]["failed_checks"]


def test_temporal_consistency_broader_result_rejects_payload_latency() -> None:
    report = build_report(
        plan=_plan(),
        selector_equivalence=_selector(),
        dataset_audit=_dataset(),
        payload_audits=_payloads(latency_max=2.5),
    )

    assert report["final_decision"]["status"] != READY_STATUS
    assert "payload_latency_within_broader_budget" in report["final_decision"][
        "failed_checks"
    ]


def test_temporal_consistency_broader_result_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    plan_json = tmp_path / "plan.json"
    selector_json = tmp_path / "selector.json"
    dataset_json = tmp_path / "dataset.json"
    output_json = tmp_path / "result.json"
    output_md = tmp_path / "result.md"
    payload_paths = []
    plan_json.write_text(json.dumps(_plan()), encoding="utf-8")
    selector_json.write_text(json.dumps(_selector()), encoding="utf-8")
    dataset_json.write_text(json.dumps(_dataset()), encoding="utf-8")
    for idx, payload in enumerate(_payloads()):
        path = tmp_path / f"payload_{idx}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        payload_paths.append(path)

    argv = [
        "temporal-broader-result",
        "--plan_json",
        str(plan_json),
        "--selector_equivalence_json",
        str(selector_json),
        "--dataset_audit_json",
        str(dataset_json),
        "--label",
        "unit_cli",
        "--output_json",
        str(output_json),
        "--output_md",
        str(output_md),
    ]
    for path in payload_paths:
        argv.extend(["--payload_audit_json", str(path)])
    monkeypatch.setattr("sys.argv", argv)

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Temporal Consistency Broader Nonformal Smoke Result" in output_md.read_text(
        encoding="utf-8"
    )
