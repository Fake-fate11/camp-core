from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_matched_observable_outcomes import (
    analyze,
)


def _outcome(value: float = 0.0) -> dict[str, object]:
    return {
        "value": value,
        "feasible": True,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
        "mean_jerk_mps3": 0.1,
        "mean_lateral_acceleration_mps2": 0.2,
    }


def _record(*, seed: int = 1, include_outcomes: bool = True) -> dict[str, object]:
    record = {
        "seed": seed,
        "observable_state_logging": {
            "schema_version": "dp_camp_observable_state_logging_v1",
            "enabled": True,
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "candidate_count": 2,
            "finite_checks": {
                "candidate_route_projection_s_m": True,
                "candidate_route_lateral_error_m": True,
            },
        },
    }
    if include_outcomes:
        record["candidate_closed_loop_outcomes"] = [_outcome(1.0), _outcome(2.0)]
    return record


def _write_log(tmp_path, records: list[dict[str, object]]):
    path = tmp_path / "run" / "camp_selection_log.json"
    path.parent.mkdir()
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_matched_contract_passes_same_record_payload_and_outcomes(tmp_path) -> None:
    log_path = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [log_path],
        expected_logs=1,
        expected_records=2,
        expected_candidates=2,
    )

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["status"] == (
        "matched_observable_outcome_contract_passed"
    )
    assert report["counts"]["observable_records"] == 2
    assert report["counts"]["outcome_records"] == 2
    assert report["counts"]["candidate_rows"] == 4


def test_matched_contract_rejects_missing_outcomes(tmp_path) -> None:
    log_path = _write_log(tmp_path, [_record(include_outcomes=False)])

    report = analyze([log_path], expected_logs=1, expected_records=1, expected_candidates=2)

    assert report["final_decision"]["passed"] is False
    assert any(
        "candidate_closed_loop_outcomes incomplete" in error
        for error in report["validation"]["errors"]
    )


def test_matched_contract_rejects_formal_seed(tmp_path) -> None:
    log_path = _write_log(tmp_path, [_record(seed=11)])

    report = analyze([log_path], expected_logs=1, expected_records=1, expected_candidates=2)

    assert report["final_decision"]["passed"] is False
    assert "formal_seed_records=1" in report["validation"]["errors"]


def test_matched_contract_rejects_payload_that_embeds_outcomes(tmp_path) -> None:
    record = _record()
    payload = record["observable_state_logging"]
    assert isinstance(payload, dict)
    payload["candidate_closed_loop_outcomes"] = []
    log_path = _write_log(tmp_path, [record])

    report = analyze([log_path], expected_logs=1, expected_records=1, expected_candidates=2)

    assert report["final_decision"]["passed"] is False
    assert any(
        "observable payload contains candidate outcomes" in error
        for error in report["validation"]["errors"]
    )


def test_matched_contract_cli_require_pass_fails_on_rejection(
    tmp_path,
    monkeypatch,
) -> None:
    from scripts.integrations.analyze_diffusion_planner_matched_observable_outcomes import (
        main,
    )

    log_path = _write_log(tmp_path, [_record(include_outcomes=False)])
    output_json = tmp_path / "audit.json"
    output_md = tmp_path / "audit.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze_diffusion_planner_matched_observable_outcomes.py",
            "--selection_log",
            str(log_path),
            "--expected_logs",
            "1",
            "--expected_records",
            "1",
            "--expected_candidates",
            "2",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_pass",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 2
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"][
        "passed"
    ] is False
    assert "candidate_closed_loop_outcomes incomplete" in output_md.read_text(
        encoding="utf-8"
    )
