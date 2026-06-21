from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_current_development_gate_state import (
    BLOCKED_STATUS,
    READY_STATUS,
    REQUIRED_BUCKETS,
    build_report,
    main,
    render_markdown,
)


def _decision(status: str, **overrides: object) -> dict[str, object]:
    payload = {
        "status": status,
        "passed": True,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }
    payload.update(overrides)
    return payload


def _source_closure(**overrides: object) -> dict[str, object]:
    return {
        "final_decision": _decision(
            "targeted_source_discovery_route_closed",
            source_discovery_closed=True,
            current_camp_dp_selector_route_rejected=True,
            authorized_next_work="proof_protocol_v2_or_scenario_objective_redesign_only",
            **overrides,
        )
    }


def _proof_v2(buckets: list[str] | None = None) -> dict[str, object]:
    return {
        "protocol": {
            "required_scenario_buckets": list(REQUIRED_BUCKETS)
            if buckets is None
            else buckets,
            "primary_score": {
                "name": "SafetyCost_v1",
                "claim_rule": (
                    "hard_gate_passed and "
                    "ci95_high(SafetyCost_CAMP_minus_DP_Top1) < 0"
                ),
            },
        },
        "final_decision": _decision(
            "proof_protocol_v2_predeclared",
            authorized_next_work="scenario_manifest_and_evidence_matrix_design_only",
        ),
    }


def _scenario_matrix(**overrides: object) -> dict[str, object]:
    matrix = {
        "planned_run_count": 108,
        "bucket_counts": {bucket: 3 for bucket in REQUIRED_BUCKETS},
        "missing_required_buckets": [],
        "formal_seeds": [],
    }
    matrix.update(overrides.pop("matrix_overrides", {}))
    return {
        "matrix_source": matrix,
        "final_decision": _decision(
            "scenario_evidence_matrix_predeclared",
            authorized_next_work="candidate_branch_oracle_input_readiness_gate",
            **overrides,
        ),
    }


def _oracle(**overrides: object) -> dict[str, object]:
    gate = {"passed": True}
    gate.update(overrides.pop("gate_overrides", {}))
    return {
        "opportunity_gate": gate,
        "coverage_gaps": {"missing_required_buckets": []},
        "logs": {"formal_seed_logs": 0},
    }


def _failure_attribution() -> dict[str, object]:
    return {
        "failure_summary": {
            "current_camp_targeted_failure_confirmed": True,
            "old_training_and_sensitivity_routes_closed": True,
        },
        "final_decision": _decision(
            "targeted_failure_attribution_no_current_route",
            current_camp_dp_selector_route_rejected=True,
            authorized_next_work=(
                "predeclare_new_no_leak_targeted_support_source_or_reject_current_route_only"
            ),
        ),
    }


def _support_reject(**overrides: object) -> dict[str, object]:
    return {
        "final_decision": _decision(
            "new_no_leak_targeted_support_source_not_available",
            support_source_ready=False,
            current_camp_dp_selector_route_rejected=True,
            authorized_next_work=(
                "source_level_targeted_support_discovery_or_pause_current_selector_route_only"
            ),
            **overrides,
        )
    }


def _report(**kwargs: object) -> dict[str, object]:
    inputs = {
        "source_closure": _source_closure(),
        "proof_protocol_v2": _proof_v2(),
        "scenario_evidence_matrix": _scenario_matrix(),
        "targeted_oracle": _oracle(),
        "targeted_failure_attribution": _failure_attribution(),
        "support_reject": _support_reject(),
        "label": "unit",
    }
    inputs.update(kwargs)
    return build_report(**inputs)


def test_current_development_state_accepts_no_deployable_route_yet() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["development_gates_complete"] is False
    assert decision["formal_seeds_ready"] is False
    assert decision["authorized_next_work"] == (
        "scenario_objective_redesign_or_external_source_discovery_only"
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert report["development_state"]["blocking_gap"] == (
        "candidate_pool_opportunity_exists_but_no_current_no_leak_deployable_selector_route"
    )


def test_current_development_state_blocks_missing_bucket() -> None:
    buckets = [bucket for bucket in REQUIRED_BUCKETS if bucket != "dense_scene"]
    report = _report(proof_protocol_v2=_proof_v2(buckets=buckets))

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert "proof_protocol_required_buckets" in decision["failed_checks"]
    assert decision["authorized_next_work"] is None


def test_current_development_state_blocks_authorization_conflict() -> None:
    report = _report(
        source_closure=_source_closure(closed_loop_replay_authorized=True)
    )

    decision = report["final_decision"]
    assert decision["status"] == BLOCKED_STATUS
    assert "source_closure_closed_loop_replay_authorized_false" in decision[
        "failed_checks"
    ]
    assert decision["formal_seeds_authorized"] is False


def test_current_development_state_markdown_states_boundary() -> None:
    report = _report()
    markdown = render_markdown(report)

    assert "Current DP-CAMP Development Gate State" in markdown
    assert "SafetyCost_v1" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "No DP-side classical Benders" in markdown


def test_current_development_state_cli_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = {
        "source": tmp_path / "source.json",
        "proof": tmp_path / "proof.json",
        "scenario": tmp_path / "scenario.json",
        "oracle": tmp_path / "oracle.json",
        "failure": tmp_path / "failure.json",
        "support": tmp_path / "support.json",
    }
    payloads = [
        _source_closure(),
        _proof_v2(),
        _scenario_matrix(),
        _oracle(),
        _failure_attribution(),
        _support_reject(),
    ]
    for path, payload in zip(paths.values(), payloads, strict=True):
        path.write_text(json.dumps(payload), encoding="utf-8")
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--source_closure_json",
            str(paths["source"]),
            "--proof_protocol_v2_json",
            str(paths["proof"]),
            "--scenario_evidence_matrix_json",
            str(paths["scenario"]),
            "--targeted_oracle_json",
            str(paths["oracle"]),
            "--targeted_failure_attribution_json",
            str(paths["failure"]),
            "--support_reject_json",
            str(paths["support"]),
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
    assert "Current DP-CAMP Development Gate State" in output_md.read_text(
        encoding="utf-8"
    )
