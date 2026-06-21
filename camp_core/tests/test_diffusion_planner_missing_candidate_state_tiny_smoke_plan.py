from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from scripts.integrations.audit_diffusion_planner_missing_candidate_state_logging_implementation import (
    AUTHORIZED_NEXT_WORK as IMPLEMENTATION_NEXT_WORK,
    READY_STATUS as IMPLEMENTATION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_missing_candidate_state_tiny_smoke import (
    AUTHORIZED_NEXT_WORK,
    DEFAULT_SMOKE,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


def _implementation_report(
    *,
    status: str = IMPLEMENTATION_READY_STATUS,
    authorized_next_work: str | None = IMPLEMENTATION_NEXT_WORK,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": status == IMPLEMENTATION_READY_STATUS,
            "authorized_next_work": authorized_next_work,
            "recommended_first_action": (
                "predeclare_default_off_missing_candidate_state_tiny_smoke_plan"
                if status == IMPLEMENTATION_READY_STATUS
                else None
            ),
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def test_missing_candidate_state_tiny_smoke_plan_authorizes_exact_scope() -> None:
    report = build_report(implementation_report=_implementation_report(), label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["closed_loop_replay_authorized"] is True
    assert decision["tiny_smoke_authorized"] is True
    assert decision["full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]

    baseline = report["commands"]["baseline_replay"]
    candidate = report["commands"]["candidate_replay"]
    assert "--camp_observable_state_logging" not in baseline
    assert "--camp_observable_state_logging" in candidate
    assert baseline[baseline.index("--steps") + 1] == "3"
    assert candidate[candidate.index("--seed") + 1] == "1"
    assert candidate[candidate.index("--num_candidates") + 1] == "8"
    assert "missing_candidate_state_logging_tiny_smoke" in report["smoke_spec"]["root"]


def test_missing_candidate_state_tiny_smoke_plan_rejects_wrong_source_gate() -> None:
    report = build_report(
        implementation_report=_implementation_report(
            status="missing_candidate_state_logging_implementation_blocked",
            authorized_next_work=None,
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is False
    assert report["source_implementation_gate"]["passed"] is False


def test_missing_candidate_state_tiny_smoke_plan_rejects_formal_seed() -> None:
    report = build_report(
        implementation_report=_implementation_report(),
        smoke=replace(DEFAULT_SMOKE, seed=11),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    formal_check = next(
        check for check in report["plan_checks"] if check["name"] == "scope_seed_is_nonformal"
    )
    assert formal_check["passed"] is False
    assert report["final_decision"]["closed_loop_replay_authorized"] is False


def test_missing_candidate_state_tiny_smoke_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_report=_implementation_report(),
        payload_audit_source=tmp_path / "missing.py",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == ["payload_audit_available"]


def test_missing_candidate_state_tiny_smoke_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    implementation_path = tmp_path / "implementation.json"
    output_json = tmp_path / "tiny_smoke_plan.json"
    output_md = tmp_path / "tiny_smoke_plan.md"
    implementation_path.write_text(
        json.dumps(_implementation_report()),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "tiny_smoke_plan",
            "--implementation_json",
            str(implementation_path),
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
    assert "Tiny Smoke Plan" in output_md.read_text(encoding="utf-8")
