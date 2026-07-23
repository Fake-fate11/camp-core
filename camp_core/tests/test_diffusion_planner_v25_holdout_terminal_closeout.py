from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    freeze_fatal_artifact,
    freeze_tombstone,
)
from camp_core.integrations.diffusion_planner_v25_holdout_terminal_closeout import (
    REVIEW_STATUS,
    STATUS,
    freeze_terminal_failure_closeout,
    independent_terminal_failure_review,
    validate_terminal_failure_closeout,
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _fixture() -> tuple[dict, dict]:
    identity = _sha(1)
    protocol = _sha(2)
    controller = {"path": "/artifact/controller", "root_sha256": _sha(3)}
    release = {"path": "/artifact/release", "root_sha256": _sha(4)}
    failure = {"path": "/artifact/failure", "root_sha256": _sha(5)}
    failure_review = {
        "path": "/artifact/failure-review",
        "root_sha256": _sha(6),
    }
    tombstone = freeze_tombstone(
        holdout_identity_sha256=identity,
        experiment_protocol_sha256=protocol,
        reservation_commitment_sha256=_sha(7),
        state="terminal_failure",
        history=[
            {"state": "reserved"},
            {"state": "opened_consumed"},
            {"state": "terminal_failure"},
        ],
        opening_attempt_count=1,
        opening_release_root_sha256=release["root_sha256"],
        marker_sha256=_sha(8),
        terminal_artifact_root_sha256=failure["root_sha256"],
        terminal_reason="artifact_fatal",
        outcome_evaluation_completed=False,
    )
    fatal = freeze_fatal_artifact(
        block_class="holdout_execution_artifact_fatal",
        reason="'candidate_tensor_sha256_before'",
        controller_decision_root_sha256=controller["root_sha256"],
        opening_release_root_sha256=release["root_sha256"],
        marker_path=f"/root/autodl-tmp/.cas/{identity}.json",
        marker_sha256=tombstone["marker_sha256"],
        holdout_identity_sha256=identity,
        experiment_protocol_sha256=protocol,
        attempted_unit_ordinal=0,
        attempted_arm="candidate0",
        planned_arm_run_count=1500,
        attempted_arm_run_count=1,
        complete_arm_run_count=0,
        outcome_fields_consumed=[],
        fresh_opened_once=True,
    )
    closeout = freeze_terminal_failure_closeout(
        benchmark="fresh_b3",
        holdout_identity_sha256=identity,
        experiment_protocol_sha256=protocol,
        run_nonce=_sha(9),
        controller_decision=controller,
        opening_release=release,
        failure_artifact=failure,
        failure_review=failure_review,
        cas_tombstone_path=f"/root/autodl-tmp/.cas/{identity}.json",
        cas_tombstone_sha256=_sha(10),
        cas_tombstone=tombstone,
        worker_stderr={"path": "/artifact/worker.stderr", "sha256": _sha(11)},
        fatal_artifact=fatal,
    )
    return closeout, fatal


def test_terminal_failure_closeout_is_exact_and_no_claim() -> None:
    closeout, fatal = _fixture()
    assert validate_terminal_failure_closeout(closeout) == closeout
    assert closeout["status"] == STATUS
    assert closeout["planned_arm_run_count"] == 1500
    assert closeout["attempted_arm_run_count"] == 1
    assert closeout["complete_arm_run_count"] == 0
    assert closeout["unattempted_arm_run_count"] == 1499
    assert closeout["complete_paired_row_count"] == 0
    assert closeout["outcome_fields_consumed"] == []
    assert closeout["raw_outcome_values_inspected"] is False
    assert closeout["claim_authorized"] is False
    report = independent_terminal_failure_review(
        closeout,
        fatal_artifact=fatal,
        reviewed_root_sha256=_sha(12),
    )
    assert report["status"] == REVIEW_STATUS
    assert report["fresh_evaluation_authorized"] is False
    assert report["b4_engineering_recovery_preopen_only"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("complete_arm_run_count", 1),
        ("unattempted_arm_run_count", 1498),
        ("full_denominator_formed", True),
        ("outcome_fields_consumed", ["safety_cost"]),
        ("raw_outcome_values_inspected", True),
        ("resume_allowed", True),
        ("new_nonce_allowed", True),
        ("suffix_allowed", True),
        ("claim_authorized", True),
    ],
)
def test_terminal_failure_closeout_rejects_drift(
    field: str, value: object
) -> None:
    closeout, _fatal = _fixture()
    mutated = copy.deepcopy(closeout)
    mutated[field] = value
    with pytest.raises(ValueError):
        validate_terminal_failure_closeout(mutated)


def test_terminal_failure_closeout_rejects_missing_or_extra_fields() -> None:
    closeout, _fatal = _fixture()
    missing = copy.deepcopy(closeout)
    del missing["failure_signature"]
    with pytest.raises(ValueError):
        validate_terminal_failure_closeout(missing)
    extra = copy.deepcopy(closeout)
    extra["raw_result"] = 1
    with pytest.raises(ValueError):
        validate_terminal_failure_closeout(extra)
