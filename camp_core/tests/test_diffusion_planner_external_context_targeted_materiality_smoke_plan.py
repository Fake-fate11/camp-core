from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_external_context_targeted_materiality_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


def _gap(*, ready: bool = True, include_route_gap: bool = True) -> dict:
    gap_names = ["traffic_signal_context_absent"]
    if include_route_gap:
        gap_names.append("route_speed_context_available_but_no_candidate_excess")
    return {
        "final_decision": {
            "status": (
                "external_context_materiality_gap_diagnosed"
                if ready
                else "external_context_materiality_gap_diagnosis_rejected"
            ),
            "passed": ready,
            "authorized_next_work": (
                "external_context_targeted_materiality_smoke_plan_only"
                if ready
                else None
            ),
            "gap_names": gap_names,
            "new_replay_authorized": False,
            "camp_retraining_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
        }
    }


def test_targeted_materiality_smoke_plan_accepts_route_speed_gap() -> None:
    report = build_report(gap=_gap(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is True
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["candidate_noise_scale"] == 2.0
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]
    candidate = report["payload_smoke_plan"]["commands"]["candidate_replay"]
    assert "--camp_external_context_payload_logging" in candidate
    assert "--candidate_noise_scale" in candidate
    noise_index = candidate.index("--candidate_noise_scale")
    assert candidate[noise_index + 1] == "2.0"


def test_targeted_materiality_smoke_plan_rejects_failed_gap_source() -> None:
    report = build_report(gap=_gap(ready=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "source_gap_status_ready",
        "source_gap_passed",
        "source_authorizes_plan_only_targeted_design",
    ]


def test_targeted_materiality_smoke_plan_rejects_without_route_speed_gap() -> None:
    report = build_report(gap=_gap(include_route_gap=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["route_speed_gap_is_targeted"]


def test_targeted_materiality_smoke_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    gap_path = tmp_path / "gap.json"
    output_json = tmp_path / "targeted_plan.json"
    output_md = tmp_path / "targeted_plan.md"
    output_bash = tmp_path / "targeted_plan.sh"
    gap_path.write_text(json.dumps(_gap()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "external-context-targeted-materiality-smoke-plan",
            "--gap_json",
            str(gap_path),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_bash",
            str(output_bash),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "External Context Targeted Materiality Smoke Plan" in output_md.read_text(
        encoding="utf-8"
    )
    assert "candidate_noise_scale 2.0" in output_bash.read_text(encoding="utf-8")
