from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_hard_stop import (
    CLASSIFICATION,
    freeze_calibration_hard_stop_closeout,
    validate_calibration_hard_stop_closeout,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_hard_stop_review import (
    literal_review_calibration_hard_stop,
)


SHA = "1" * 64
REPORTING_HEAD = "2" * 40


def _closeout() -> dict:
    return freeze_calibration_hard_stop_closeout(
        reporting_head=REPORTING_HEAD,
        source_predicate={
            "producer_path": (
                "/root/autodl-tmp/"
                ".camp_dp_v25_calibration_raw_67308ac0_ed0d298c.py"
            ),
            "producer_sha256": SHA,
            "predicate_line_start": 509,
            "predicate_line_end": 514,
            "predicate_sha256": SHA,
            "exception_literal": (
                "calibration K8 invalid: "
                "development_calibration:000/sequential_batch1_x8/0"
            ),
        },
        control_evidence={
            "run_script_path": "/control/run.sh",
            "run_script_sha256": SHA,
            "stdout_path": "/control/stdout",
            "stdout_sha256": SHA,
            "stderr_path": "/control/stderr",
            "stderr_sha256": SHA,
            "exit_path": "/control/exit",
            "exit_sha256": SHA,
            "control_exit": 1,
            "pid_path": "/control/pid",
            "pid_sha256": SHA,
            "pid": 204002,
            "process_running": False,
        },
        artifact_absence={
            "raw_artifact_absent": True,
            "raw_review_artifact_absent": True,
            "threshold_freeze_artifact_absent": True,
            "threshold_freeze_review_artifact_absent": True,
        },
        pre_artifact_diagnostics=[
            {
                "classification": name,
                "control_exit": 1,
                "raw_artifact_created": False,
                "model_call_count_before_failure": 0,
                "stderr_sha256": SHA,
            }
            for name in (
                "lanelet2_projection_compatibility_fixture",
                "causal_map_cache_fixture",
                "sealed_model_input_vs_unpinned_scene_history_fixture",
            )
        ],
    )


def _literal_review(value: dict) -> dict:
    return literal_review_calibration_hard_stop(
        value,
        observed_source_predicate_sha256=SHA,
        observed_file_sha256={
            "producer": SHA,
            "run_script": SHA,
            "stdout": SHA,
            "stderr": SHA,
            "exit": SHA,
            "pid": SHA,
        },
        observed_absence={
            "raw_artifact_absent": True,
            "raw_review_artifact_absent": True,
            "threshold_freeze_artifact_absent": True,
            "threshold_freeze_review_artifact_absent": True,
        },
        process_running=False,
        observed_reporting_head=REPORTING_HEAD,
    )


def test_closeout_is_exact_outcome_blind_and_independently_reviewed() -> None:
    value = _closeout()
    assert validate_calibration_hard_stop_closeout(value) == value
    assert value["classification"] == CLASSIFICATION
    assert value["compound_gate"]["resolved_subcondition"] == "unknown"
    assert value["first_run"]["model_call_count"] == 8
    assert value["first_run"]["selector_call_count"] == 0
    assert value["artifact_state"]["completed_raw_run_count"] == 0
    assert value["artifact_state"]["planned_raw_run_count"] == 640
    assert value["artifact_state"]["threshold_not_formed"] is True
    report = _literal_review(value)
    assert report["status"] == "passed_independent_calibration_hard_stop_review"
    assert report["producer_module_imported"] is False


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("first_run", "model_call_count"), 7),
        (("first_run", "selector_call_count"), 1),
        (("compound_gate", "resolved_subcondition"), "candidate_nonfinite"),
        (
            (
                "compound_gate",
                "exact_subcondition_recoverable_from_preserved_evidence",
            ),
            True,
        ),
        (("artifact_state", "raw_artifact_absent"), False),
        (("artifact_state", "completed_raw_run_count"), 1),
        (("artifact_state", "threshold_not_formed"), False),
        (("forbidden_run_counts", "independent_validation_run_count"), 1),
        (("scientific_interpretation", "model_failure_claimed"), True),
        (
            ("scientific_interpretation", "retraining_required_claimed"),
            True,
        ),
        (
            ("scientific_interpretation", "raw_fresh_or_b4_outcome_inspected"),
            True,
        ),
    ],
)
def test_closeout_mutations_fail_closed(
    path: tuple[str, str], replacement: object
) -> None:
    value = _closeout()
    value[path[0]][path[1]] = replacement
    with pytest.raises(ValueError):
        validate_calibration_hard_stop_closeout(value)
    with pytest.raises(ValueError):
        _literal_review(value)


def test_closeout_unknown_missing_and_candidate_preimage_fields_fail_closed() -> None:
    value = _closeout()
    value["unknown"] = True
    with pytest.raises(ValueError):
        validate_calibration_hard_stop_closeout(value)
    missing = _closeout()
    del missing["control_evidence"]["stderr_sha256"]
    with pytest.raises(ValueError):
        validate_calibration_hard_stop_closeout(missing)
    candidate = _closeout()
    candidate["candidate_bytes"] = "forbidden"
    with pytest.raises(ValueError):
        validate_calibration_hard_stop_closeout(candidate)


def test_reviewer_rejects_observed_byte_absence_and_process_drift() -> None:
    value = _closeout()
    with pytest.raises(ValueError):
        literal_review_calibration_hard_stop(
            value,
            observed_source_predicate_sha256="3" * 64,
            observed_file_sha256={
                "producer": SHA,
                "run_script": SHA,
                "stdout": SHA,
                "stderr": SHA,
                "exit": SHA,
                "pid": SHA,
            },
            observed_absence={
                "raw_artifact_absent": True,
                "raw_review_artifact_absent": True,
                "threshold_freeze_artifact_absent": True,
                "threshold_freeze_review_artifact_absent": True,
            },
            process_running=False,
            observed_reporting_head=REPORTING_HEAD,
        )
    with pytest.raises(ValueError):
        literal_review_calibration_hard_stop(
            value,
            observed_source_predicate_sha256=SHA,
            observed_file_sha256={
                "producer": SHA,
                "run_script": SHA,
                "stdout": SHA,
                "stderr": SHA,
                "exit": SHA,
                "pid": SHA,
            },
            observed_absence={
                "raw_artifact_absent": False,
                "raw_review_artifact_absent": True,
                "threshold_freeze_artifact_absent": True,
                "threshold_freeze_review_artifact_absent": True,
            },
            process_running=True,
            observed_reporting_head=REPORTING_HEAD,
        )


def test_independent_reviewer_does_not_import_producer_module() -> None:
    source = (
        Path(__file__).parents[1]
        / "camp_core/integrations/"
        "diffusion_planner_v25_fair_pool_calibration_hard_stop_review.py"
    ).read_text("utf-8")
    assert (
        "import diffusion_planner_v25_fair_pool_calibration_hard_stop"
        not in source
    )
    assert "freeze_calibration_hard_stop_closeout" not in source
