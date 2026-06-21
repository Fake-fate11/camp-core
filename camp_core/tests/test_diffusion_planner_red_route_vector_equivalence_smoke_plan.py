from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_red_route_vector_equivalence_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    RedRouteVectorEquivalencePlanSpec,
    RedRouteVectorEquivalenceRunSpec,
    build_report,
)


def _source_report(
    *,
    status: str = "red_route_vector_logging_plan_ready",
    passed: bool = True,
    next_work: str = "implement_default_off_red_route_vector_logging_unit_tests_only",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": next_work,
            "new_replay_authorized": False,
            "offline_separability_authorized": False,
            "formal_seeds_authorized": False,
        }
    }


def _replay_script(tmp_path: Path, *, include_tokens: bool = True) -> Path:
    path = tmp_path / "run_diffusion_planner_camp_replay.py"
    if include_tokens:
        path.write_text(
            "\n".join(
                [
                    "--camp_red_route_vector_logging",
                    "RED_ROUTE_VECTOR_LOGGING_SCHEMA_VERSION",
                    "red_route_vector_logging",
                    "camp_red_route_vector_logging",
                    "latency_ms_red_route_vector_logging",
                    '"selection_effect": False',
                    '"future_outcome_leakage": False',
                ]
            ),
            encoding="utf-8",
        )
    else:
        path.write_text("def placeholder(): pass\n", encoding="utf-8")
    return path


def test_red_route_vector_equivalence_plan_authorizes_next_gate_only(
    tmp_path: Path,
) -> None:
    report = build_report(
        red_vector_plan_report=_source_report(),
        replay_script=_replay_script(tmp_path),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["paired_smoke_execution_authorized"] is False
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["offline_separability_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["classic_Benders_claim_authorized"] is False
    assert report["analysis"]["diffusion_planner_execution"] is False
    assert report["analysis"]["closed_loop_outcome_labels_used"] is False

    commands = report["commands"]["paired_replays"]
    assert len(commands) == 2
    baseline, logging = commands
    assert baseline["variant"] == "baseline"
    assert logging["variant"] == "red_route_vector_logging_enabled"
    assert "--camp_red_route_vector_logging" not in baseline["command"]
    assert "--camp_red_route_vector_logging" in logging["command"]
    assert "--camp_observable_state_logging" not in baseline["command"]
    assert "--camp_observable_state_logging" not in logging["command"]

    contract = report["equivalence_contract"]
    assert "selected_index" in contract["exact_fields"]
    assert "atoms" in contract["exact_fields"]
    assert "normalized_atoms" in contract["exact_fields"]
    assert "weights" in contract["exact_fields"]
    assert "perfect_tracker_command_inputs" in contract["exact_fields"]
    assert "red_route_vector_logging" in contract["allowed_differences"]

    payload = report["payload_contract"]
    assert payload["required_flags"]["default_off"] is True
    assert payload["required_flags"]["selection_effect"] is False
    assert payload["required_flags"]["future_outcome_leakage"] is False


def test_red_route_vector_equivalence_plan_rejects_invalid_source(
    tmp_path: Path,
) -> None:
    report = build_report(
        red_vector_plan_report=_source_report(
            status="red_route_vector_logging_plan_rejected",
            passed=False,
            next_work=None,
        ),
        replay_script=_replay_script(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["source_plan_ready_and_authorized_implementation_only"]


def test_red_route_vector_equivalence_plan_rejects_missing_implementation(
    tmp_path: Path,
) -> None:
    report = build_report(
        red_vector_plan_report=_source_report(),
        replay_script=_replay_script(tmp_path, include_tokens=False),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [
        check["name"]
        for check in report["implementation_checks"]
        if not check["passed"]
    ]
    assert failed == ["red_route_vector_logging_tokens_present"]


def test_red_route_vector_equivalence_plan_rejects_formal_seed(tmp_path: Path) -> None:
    base = RedRouteVectorEquivalencePlanSpec()
    report = build_report(
        red_vector_plan_report=_source_report(),
        replay_script=_replay_script(tmp_path),
        spec=replace(base, run=replace(base.run, seed=11)),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    formal_check = next(
        check for check in report["plan_checks"] if check["name"] == "formal_seeds_excluded"
    )
    assert formal_check["passed"] is False


def test_red_route_vector_equivalence_plan_rejects_non_tiny_scope(
    tmp_path: Path,
) -> None:
    report = build_report(
        red_vector_plan_report=_source_report(),
        replay_script=_replay_script(tmp_path),
        spec=RedRouteVectorEquivalencePlanSpec(steps=12),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    scope_check = next(
        check
        for check in report["plan_checks"]
        if check["name"] == "paired_scope_is_tiny_and_nonformal"
    )
    assert scope_check["passed"] is False


def test_red_route_vector_equivalence_plan_rejects_non_red_route(
    tmp_path: Path,
) -> None:
    base = RedRouteVectorEquivalencePlanSpec()
    report = build_report(
        red_vector_plan_report=_source_report(),
        replay_script=_replay_script(tmp_path),
        spec=replace(
            base,
            run=replace(
                base.run,
                scenario_buckets=("normal_control",),
                traffic_lights="off",
            ),
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    route_check = next(
        check for check in report["plan_checks"] if check["name"] == "route_targets_red_context"
    )
    assert route_check["passed"] is False


def test_red_route_vector_equivalence_run_spec_defaults_nonformal() -> None:
    run = RedRouteVectorEquivalenceRunSpec()
    assert run.seed not in {11, 12, 13}
    assert run.traffic_lights == "on"
    assert "red_light" in run.scenario_buckets
