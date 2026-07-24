from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import camp_core.integrations.diffusion_planner_v25_holdout_state as state_module
from camp_core.integrations.diffusion_planner_v25_holdout_state import (
    fail_operational_pre_exposure,
    mark_full_denominator,
    mark_scientific_evaluated,
    operational_identity_path,
    operational_attempt_path,
    qualify_unexposed_operational_state,
    reserve_operational_attempt,
    scientific_identity_path,
    seal_operational_release,
    start_scientific_exposure,
    terminate_scientific_identity,
    validate_operational_attempt,
    validate_operational_identity_reservation,
    validate_scientific_ledger,
)


IDENTITY = "1" * 64
PROTOCOL = "2" * 64
NONCE = "3" * 64
CONTROLLER = "4" * 64
RELEASE = "5" * 64
TERMINAL = "6" * 64


def _reserve(tmp_path: Path) -> Path:
    return reserve_operational_attempt(
        tmp_path,
        holdout_identity_sha256=IDENTITY,
        experiment_protocol_sha256=PROTOCOL,
        run_nonce=NONCE,
        authorized_output_dir=str((tmp_path / "output").resolve()),
        controller_root_sha256=CONTROLLER,
    )


def test_pre_exposure_failure_does_not_consume_scientific_identity(
    tmp_path: Path,
) -> None:
    attempt = _reserve(tmp_path)
    seal_operational_release(
        attempt, opening_release_root_sha256=RELEASE
    )
    failed = fail_operational_pre_exposure(
        attempt, terminal_reason="path_permission_preflight_failed"
    )
    assert failed["state"] == "pre_exposure_failure"
    assert failed["scientific_identity_consumed"] is False
    assert failed["new_attempt_allowed_if_pre_exposure_failure"] is True
    assert not scientific_identity_path(tmp_path, IDENTITY).exists()
    reservation = validate_operational_identity_reservation(
        __import__("json").loads(
            operational_identity_path(tmp_path, IDENTITY).read_text(
                encoding="utf-8"
            )
        )
    )
    assert reservation["state"] == "pre_exposure_released"
    assert reservation["new_attempt_allowed"] is True
    available = qualify_unexposed_operational_state(
        tmp_path,
        holdout_identity_sha256=IDENTITY,
        experiment_protocol_sha256=PROTOCOL,
        requested_run_nonce="7" * 64,
    )
    assert available["new_attempt_allowed"] is True
    assert available["scientific_ledger_exists"] is False
    assert available["active_operational_attempt_exists"] is False
    assert available["prior_pre_exposure_failure"]["run_nonce"] == NONCE
    assert available["requested_operational_attempt_exists"] is False


def test_unexposed_operational_availability_rejects_wrong_chain(
    tmp_path: Path,
) -> None:
    attempt = _reserve(tmp_path)
    fail_operational_pre_exposure(
        attempt,
        expected_state="release_reserved",
        terminal_reason="release_build_failed",
    )
    with pytest.raises(FileExistsError, match="requested operational attempt"):
        qualify_unexposed_operational_state(
            tmp_path,
            holdout_identity_sha256=IDENTITY,
            experiment_protocol_sha256=PROTOCOL,
            requested_run_nonce=NONCE,
        )
    with pytest.raises(FileExistsError, match="not released pre-exposure"):
        qualify_unexposed_operational_state(
            tmp_path,
            holdout_identity_sha256=IDENTITY,
            experiment_protocol_sha256="7" * 64,
            requested_run_nonce="8" * 64,
        )
    attempt.unlink()
    with pytest.raises(ValueError, match="attempt path drifted"):
        qualify_unexposed_operational_state(
            tmp_path,
            holdout_identity_sha256=IDENTITY,
            experiment_protocol_sha256=PROTOCOL,
            requested_run_nonce="8" * 64,
        )


def test_pre_release_failure_also_keeps_scientific_identity_unopened(
    tmp_path: Path,
) -> None:
    attempt = _reserve(tmp_path)
    failed = fail_operational_pre_exposure(
        attempt,
        expected_state="release_reserved",
        terminal_reason="release_seal_failed",
    )
    assert failed["history"] == [
        "release_reserved",
        "pre_exposure_failure",
    ]
    assert not scientific_identity_path(tmp_path, IDENTITY).exists()


def test_exposure_is_atomic_and_replay_rejected(tmp_path: Path) -> None:
    attempt = _reserve(tmp_path)
    seal_operational_release(
        attempt, opening_release_root_sha256=RELEASE
    )
    operational, scientific = start_scientific_exposure(
        tmp_path,
        operational_attempt=attempt,
        first_unit_ordinal=0,
        first_arm="candidate0",
    )
    assert operational["state"] == "exposure_started"
    assert scientific["state"] == "exposure_started"
    with pytest.raises(FileExistsError):
        start_scientific_exposure(
            tmp_path,
            operational_attempt=attempt,
            first_unit_ordinal=0,
            first_arm="candidate0",
        )
    with pytest.raises(FileExistsError):
        reserve_operational_attempt(
            tmp_path,
            holdout_identity_sha256=IDENTITY,
            experiment_protocol_sha256=PROTOCOL,
            run_nonce="7" * 64,
            authorized_output_dir=str((tmp_path / "other").resolve()),
            controller_root_sha256=CONTROLLER,
        )
    reservation = validate_operational_identity_reservation(
        __import__("json").loads(
            operational_identity_path(tmp_path, IDENTITY).read_text(
                encoding="utf-8"
            )
        )
    )
    assert reservation["state"] == "exposure_started"
    assert reservation["new_attempt_allowed"] is False


def test_one_active_operational_attempt_per_identity_and_retry_after_failure(
    tmp_path: Path,
) -> None:
    first = _reserve(tmp_path)
    with pytest.raises(FileExistsError, match="active operational attempt"):
        reserve_operational_attempt(
            tmp_path,
            holdout_identity_sha256=IDENTITY,
            experiment_protocol_sha256=PROTOCOL,
            run_nonce="7" * 64,
            authorized_output_dir=str((tmp_path / "other").resolve()),
            controller_root_sha256=CONTROLLER,
        )
    fail_operational_pre_exposure(
        first,
        expected_state="release_reserved",
        terminal_reason="release_build_failed",
    )
    second = reserve_operational_attempt(
        tmp_path,
        holdout_identity_sha256=IDENTITY,
        experiment_protocol_sha256=PROTOCOL,
        run_nonce="7" * 64,
        authorized_output_dir=str((tmp_path / "other").resolve()),
        controller_root_sha256=CONTROLLER,
    )
    assert second == operational_attempt_path(tmp_path, "7" * 64)


def test_pre_exposure_retry_cannot_change_frozen_protocol(
    tmp_path: Path,
) -> None:
    first = _reserve(tmp_path)
    fail_operational_pre_exposure(
        first,
        expected_state="release_reserved",
        terminal_reason="release_build_failed",
    )
    with pytest.raises(FileExistsError, match="active operational attempt"):
        reserve_operational_attempt(
            tmp_path,
            holdout_identity_sha256=IDENTITY,
            experiment_protocol_sha256="9" * 64,
            run_nonce="7" * 64,
            authorized_output_dir=str((tmp_path / "other").resolve()),
            controller_root_sha256=CONTROLLER,
        )


def test_concurrent_reservation_has_exactly_one_winner(tmp_path: Path) -> None:
    def reserve(nonce: str) -> str:
        reserve_operational_attempt(
            tmp_path,
            holdout_identity_sha256=IDENTITY,
            experiment_protocol_sha256=PROTOCOL,
            run_nonce=nonce,
            authorized_output_dir=str((tmp_path / nonce[:4]).resolve()),
            controller_root_sha256=CONTROLLER,
        )
        return nonce

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(reserve, "7" * 64),
            pool.submit(reserve, "8" * 64),
        ]
    outcomes = []
    for future in futures:
        try:
            outcomes.append(("ok", future.result()))
        except FileExistsError:
            outcomes.append(("blocked", None))
    assert [status for status, _ in outcomes].count("ok") == 1
    assert [status for status, _ in outcomes].count("blocked") == 1


def test_full_scientific_lifecycle_and_success(tmp_path: Path) -> None:
    attempt = _reserve(tmp_path)
    seal_operational_release(
        attempt, opening_release_root_sha256=RELEASE
    )
    start_scientific_exposure(
        tmp_path,
        operational_attempt=attempt,
        first_unit_ordinal=0,
        first_arm="candidate0",
    )
    scientific = scientific_identity_path(tmp_path, IDENTITY)
    full = mark_full_denominator(
        scientific,
        planned_arm_run_count=1500,
        terminal_arm_run_count=1500,
    )
    assert full["state"] == "full_denominator_formed"
    evaluated = mark_scientific_evaluated(scientific)
    assert evaluated["state"] == "evaluated"
    terminal = terminate_scientific_identity(
        scientific,
        expected_state="evaluated",
        success=True,
        terminal_artifact_root_sha256=TERMINAL,
        terminal_reason="evaluation_review_passed",
    )
    assert terminal["state"] == "terminal_success"


@pytest.mark.parametrize(
    "validator,field,bad",
    [
        (validate_operational_attempt, "scientific_identity_consumed", 1),
        (validate_operational_attempt, "run_nonce", None),
        (validate_scientific_ledger, "second_exposure_allowed", 0),
        (validate_scientific_ledger, "terminal_arm_run_count", True),
    ],
)
def test_ledger_exact_schema_and_native_types(
    tmp_path: Path, validator, field: str, bad: object
) -> None:
    attempt = _reserve(tmp_path)
    sealed = seal_operational_release(
        attempt, opening_release_root_sha256=RELEASE
    )
    _, scientific = start_scientific_exposure(
        tmp_path,
        operational_attempt=attempt,
        first_unit_ordinal=0,
        first_arm="candidate0",
    )
    source = sealed if validator is validate_operational_attempt else scientific
    changed = copy.deepcopy(source)
    changed[field] = bad
    with pytest.raises((TypeError, ValueError)):
        validator(changed)
    extra = copy.deepcopy(source)
    extra["futureOutcome"] = True
    with pytest.raises(ValueError):
        validator(extra)


def test_failure_after_exposure_is_permanent(tmp_path: Path) -> None:
    attempt = _reserve(tmp_path)
    seal_operational_release(
        attempt, opening_release_root_sha256=RELEASE
    )
    start_scientific_exposure(
        tmp_path,
        operational_attempt=attempt,
        first_unit_ordinal=0,
        first_arm="candidate0",
    )
    scientific = scientific_identity_path(tmp_path, IDENTITY)
    failed = terminate_scientific_identity(
        scientific,
        expected_state="exposure_started",
        success=False,
        terminal_artifact_root_sha256=TERMINAL,
        terminal_reason="artifact_fatal_before_first_complete_arm",
    )
    assert failed["state"] == "terminal_failure"
    assert failed["second_exposure_allowed"] is False
    assert operational_attempt_path(tmp_path, NONCE).exists()


def test_crash_after_scientific_o_excl_remains_permanently_consumed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt = _reserve(tmp_path)
    seal_operational_release(
        attempt, opening_release_root_sha256=RELEASE
    )
    real_transition = state_module._transition_operational

    def crash_after_scientific_write(*args, **kwargs):
        if kwargs.get("next_state") == "exposure_started":
            raise RuntimeError("injected crash after scientific O_EXCL")
        return real_transition(*args, **kwargs)

    monkeypatch.setattr(
        state_module,
        "_transition_operational",
        crash_after_scientific_write,
    )
    with pytest.raises(RuntimeError, match="injected crash"):
        start_scientific_exposure(
            tmp_path,
            operational_attempt=attempt,
            first_unit_ordinal=0,
            first_arm="candidate0",
        )
    scientific = scientific_identity_path(tmp_path, IDENTITY)
    assert scientific.exists()
    with pytest.raises(FileExistsError, match="already exposed"):
        reserve_operational_attempt(
            tmp_path,
            holdout_identity_sha256=IDENTITY,
            experiment_protocol_sha256=PROTOCOL,
            run_nonce="7" * 64,
            authorized_output_dir=str((tmp_path / "other").resolve()),
            controller_root_sha256=CONTROLLER,
        )
