from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_v25_holdout_contract import canonical_sha256, strict_equal


OPERATIONAL_SCHEMA_VERSION = "camp_dp_v25_holdout_operational_attempt_v1"
OPERATIONAL_IDENTITY_SCHEMA_VERSION = (
    "camp_dp_v25_holdout_operational_identity_reservation_v1"
)
SCIENTIFIC_SCHEMA_VERSION = "camp_dp_v25_holdout_scientific_ledger_v1"
OPERATIONAL_STATES = (
    "release_reserved",
    "release_sealed",
    "pre_exposure_failure",
    "exposure_started",
)
SCIENTIFIC_STATES = (
    "exposure_started",
    "full_denominator_formed",
    "evaluated",
    "terminal_success",
    "terminal_failure",
)


def operational_attempt_path(cas_root: Path, run_nonce: str) -> Path:
    _sha(run_nonce, "run_nonce")
    return Path(cas_root).resolve() / "operational" / f"{run_nonce}.json"


def scientific_identity_path(
    cas_root: Path, holdout_identity_sha256: str
) -> Path:
    _sha(holdout_identity_sha256, "holdout_identity_sha256")
    return (
        Path(cas_root).resolve()
        / "scientific"
        / f"{holdout_identity_sha256}.json"
    )


def operational_identity_path(
    cas_root: Path, holdout_identity_sha256: str
) -> Path:
    _sha(holdout_identity_sha256, "holdout_identity_sha256")
    return (
        Path(cas_root).resolve()
        / "operational_identity"
        / f"{holdout_identity_sha256}.json"
    )


def reserve_operational_attempt(
    cas_root: Path,
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    run_nonce: str,
    authorized_output_dir: str,
    controller_root_sha256: str,
) -> Path:
    for name, value in {
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "run_nonce": run_nonce,
        "controller_root_sha256": controller_root_sha256,
    }.items():
        _sha(value, name)
    output = _absolute_output(authorized_output_dir)
    scientific = scientific_identity_path(cas_root, holdout_identity_sha256)
    if scientific.exists():
        raise FileExistsError("holdout scientific identity is already exposed")
    path = operational_attempt_path(cas_root, run_nonce)
    identity_path = operational_identity_path(cas_root, holdout_identity_sha256)
    value = _freeze_operational(
        holdout_identity_sha256=holdout_identity_sha256,
        experiment_protocol_sha256=experiment_protocol_sha256,
        run_nonce=run_nonce,
        authorized_output_dir=output,
        controller_root_sha256=controller_root_sha256,
        opening_release_root_sha256=None,
        state="release_reserved",
        history=["release_reserved"],
        terminal_reason=None,
    )
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_lock = _acquire_transition_lock(identity_path)
    try:
        if scientific.exists():
            raise FileExistsError("holdout scientific identity is already exposed")
        if identity_path.exists():
            current = validate_operational_identity_reservation(
                _strict_canonical_json(identity_path)
            )
            if (
                current["state"] != "pre_exposure_released"
                or current["experiment_protocol_sha256"]
                != experiment_protocol_sha256
            ):
                raise FileExistsError(
                    "holdout identity already has an active operational attempt"
                )
            prior = validate_operational_attempt(
                _strict_canonical_json(Path(current["operational_attempt_path"]))
            )
            if (
                prior["state"] != "pre_exposure_failure"
                or prior["run_nonce"] != current["run_nonce"]
                or prior["holdout_identity_sha256"] != holdout_identity_sha256
            ):
                raise ValueError(
                    "released operational identity lacks its failed attempt"
                )
        identity = _freeze_operational_identity_reservation(
            holdout_identity_sha256=holdout_identity_sha256,
            experiment_protocol_sha256=experiment_protocol_sha256,
            run_nonce=run_nonce,
            operational_attempt_path=str(path),
            state="active",
        )
        if identity_path.exists():
            _replace_unlocked(identity_path, identity)
        else:
            _create_exclusive(identity_path, identity)
        try:
            _create_exclusive(path, value)
        except BaseException:
            released = _freeze_operational_identity_reservation(
                holdout_identity_sha256=holdout_identity_sha256,
                experiment_protocol_sha256=experiment_protocol_sha256,
                run_nonce=run_nonce,
                operational_attempt_path=str(path),
                state="reservation_failed",
            )
            _replace_unlocked(identity_path, released)
            raise
    finally:
        identity_lock.unlink(missing_ok=True)
    return path


def seal_operational_release(
    path: Path, *, opening_release_root_sha256: str
) -> dict[str, Any]:
    _sha(opening_release_root_sha256, "opening_release_root_sha256")
    return _transition_operational(
        path,
        expected_state="release_reserved",
        next_state="release_sealed",
        opening_release_root_sha256=opening_release_root_sha256,
        terminal_reason=None,
    )


def fail_operational_pre_exposure(
    path: Path, *, terminal_reason: str, expected_state: str = "release_sealed"
) -> dict[str, Any]:
    if expected_state not in {"release_reserved", "release_sealed"}:
        raise ValueError("pre-exposure failure source state drifted")
    updated = _transition_operational(
        path,
        expected_state=expected_state,
        next_state="pre_exposure_failure",
        opening_release_root_sha256=None,
        terminal_reason=_reason(terminal_reason),
    )
    _transition_operational_identity(
        path,
        expected_state="active",
        next_state="pre_exposure_released",
    )
    return updated


def start_scientific_exposure(
    cas_root: Path,
    *,
    operational_attempt: Path,
    first_unit_ordinal: int,
    first_arm: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Atomically consume the identity immediately before the first real run.

    The scientific O_EXCL write happens first.  A crash before the operational
    ledger update is therefore conservatively post-exposure and cannot reopen
    the identity.
    """

    operational = validate_operational_attempt(
        _strict_canonical_json(Path(operational_attempt))
    )
    if operational["state"] != "release_sealed":
        raise FileExistsError("operational attempt is not ready for exposure")
    if type(first_unit_ordinal) is not int or first_unit_ordinal < 0:
        raise ValueError("first_unit_ordinal must be a native nonnegative int")
    if type(first_arm) is not str or not first_arm:
        raise ValueError("first_arm must be a nonempty string")
    scientific_path = scientific_identity_path(
        cas_root, operational["holdout_identity_sha256"]
    )
    scientific = _freeze_scientific(
        holdout_identity_sha256=operational["holdout_identity_sha256"],
        experiment_protocol_sha256=operational[
            "experiment_protocol_sha256"
        ],
        opening_release_root_sha256=operational[
            "opening_release_root_sha256"
        ],
        run_nonce=operational["run_nonce"],
        state="exposure_started",
        history=["exposure_started"],
        first_unit_ordinal=first_unit_ordinal,
        first_arm=first_arm,
        planned_arm_run_count=None,
        terminal_arm_run_count=0,
        terminal_artifact_root_sha256=None,
        terminal_reason=None,
    )
    _create_exclusive(scientific_path, scientific)
    updated = _transition_operational(
        operational_attempt,
        expected_state="release_sealed",
        next_state="exposure_started",
        opening_release_root_sha256=None,
        terminal_reason=None,
    )
    _transition_operational_identity(
        operational_attempt,
        expected_state="active",
        next_state="exposure_started",
    )
    return updated, scientific


def mark_full_denominator(
    path: Path,
    *,
    planned_arm_run_count: int,
    terminal_arm_run_count: int,
) -> dict[str, Any]:
    if (
        type(planned_arm_run_count) is not int
        or planned_arm_run_count <= 0
        or type(terminal_arm_run_count) is not int
        or terminal_arm_run_count != planned_arm_run_count
    ):
        raise ValueError("full denominator counts drifted")
    return _transition_scientific(
        path,
        expected_state="exposure_started",
        next_state="full_denominator_formed",
        planned_arm_run_count=planned_arm_run_count,
        terminal_arm_run_count=terminal_arm_run_count,
        terminal_artifact_root_sha256=None,
        terminal_reason=None,
    )


def mark_scientific_evaluated(path: Path) -> dict[str, Any]:
    return _transition_scientific(
        path,
        expected_state="full_denominator_formed",
        next_state="evaluated",
        planned_arm_run_count=None,
        terminal_arm_run_count=None,
        terminal_artifact_root_sha256=None,
        terminal_reason=None,
    )


def terminate_scientific_identity(
    path: Path,
    *,
    expected_state: str,
    success: bool,
    terminal_artifact_root_sha256: str,
    terminal_reason: str,
) -> dict[str, Any]:
    next_state = "terminal_success" if success else "terminal_failure"
    allowed_success = expected_state == "evaluated"
    if success and not allowed_success:
        raise ValueError("scientific success requires completed evaluation")
    if expected_state not in {
        "exposure_started",
        "full_denominator_formed",
        "evaluated",
    }:
        raise ValueError("scientific terminal source state drifted")
    _sha(terminal_artifact_root_sha256, "terminal_artifact_root_sha256")
    return _transition_scientific(
        path,
        expected_state=expected_state,
        next_state=next_state,
        planned_arm_run_count=None,
        terminal_arm_run_count=None,
        terminal_artifact_root_sha256=terminal_artifact_root_sha256,
        terminal_reason=_reason(terminal_reason),
    )


def validate_operational_attempt(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "run_nonce",
        "authorized_output_dir",
        "controller_root_sha256",
        "opening_release_root_sha256",
        "state",
        "history",
        "terminal_reason",
        "scientific_identity_consumed",
        "new_attempt_allowed_if_pre_exposure_failure",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("operational attempt field set drifted")
    expected = _freeze_operational(
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        run_nonce=value["run_nonce"],
        authorized_output_dir=value["authorized_output_dir"],
        controller_root_sha256=value["controller_root_sha256"],
        opening_release_root_sha256=value["opening_release_root_sha256"],
        state=value["state"],
        history=value["history"],
        terminal_reason=value["terminal_reason"],
    )
    if not strict_equal(value, expected):
        raise ValueError("operational attempt value drifted")
    return expected


def validate_operational_identity_reservation(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "run_nonce",
        "operational_attempt_path",
        "state",
        "new_attempt_allowed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("operational identity reservation field set drifted")
    expected = _freeze_operational_identity_reservation(
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        run_nonce=value["run_nonce"],
        operational_attempt_path=value["operational_attempt_path"],
        state=value["state"],
    )
    if not strict_equal(value, expected):
        raise ValueError("operational identity reservation value drifted")
    return expected


def validate_scientific_ledger(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "schema_version",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "opening_release_root_sha256",
        "run_nonce",
        "state",
        "history",
        "first_unit_ordinal",
        "first_arm",
        "planned_arm_run_count",
        "terminal_arm_run_count",
        "terminal_artifact_root_sha256",
        "terminal_reason",
        "second_exposure_allowed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("scientific ledger field set drifted")
    expected = _freeze_scientific(
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        opening_release_root_sha256=value["opening_release_root_sha256"],
        run_nonce=value["run_nonce"],
        state=value["state"],
        history=value["history"],
        first_unit_ordinal=value["first_unit_ordinal"],
        first_arm=value["first_arm"],
        planned_arm_run_count=value["planned_arm_run_count"],
        terminal_arm_run_count=value["terminal_arm_run_count"],
        terminal_artifact_root_sha256=value[
            "terminal_artifact_root_sha256"
        ],
        terminal_reason=value["terminal_reason"],
    )
    if not strict_equal(value, expected):
        raise ValueError("scientific ledger value drifted")
    return expected


def _freeze_operational_identity_reservation(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    run_nonce: str,
    operational_attempt_path: str,
    state: str,
) -> dict[str, Any]:
    for name, value in {
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "run_nonce": run_nonce,
    }.items():
        _sha(value, name)
    if state not in {
        "active",
        "pre_exposure_released",
        "exposure_started",
        "reservation_failed",
    }:
        raise ValueError("operational identity reservation state drifted")
    attempt = Path(operational_attempt_path)
    if not attempt.is_absolute() or str(attempt) != str(attempt.resolve()):
        raise ValueError("operational attempt path must be exact and absolute")
    return {
        "schema_version": OPERATIONAL_IDENTITY_SCHEMA_VERSION,
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "run_nonce": run_nonce,
        "operational_attempt_path": str(attempt),
        "state": state,
        "new_attempt_allowed": state == "pre_exposure_released",
    }


def _freeze_operational(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    run_nonce: str,
    authorized_output_dir: str,
    controller_root_sha256: str,
    opening_release_root_sha256: str | None,
    state: str,
    history: list[str],
    terminal_reason: str | None,
) -> dict[str, Any]:
    for name, value in {
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "run_nonce": run_nonce,
        "controller_root_sha256": controller_root_sha256,
    }.items():
        _sha(value, name)
    if state not in OPERATIONAL_STATES:
        raise ValueError("operational attempt state drifted")
    expected_histories = {
        "release_reserved": ["release_reserved"],
        "release_sealed": ["release_reserved", "release_sealed"],
        "pre_exposure_failure": None,
        "exposure_started": [
            "release_reserved",
            "release_sealed",
            "exposure_started",
        ],
    }
    if type(history) is not list:
        raise ValueError("operational attempt history drifted")
    if state == "pre_exposure_failure":
        if history not in (
            ["release_reserved", "pre_exposure_failure"],
            [
                "release_reserved",
                "release_sealed",
                "pre_exposure_failure",
            ],
        ):
            raise ValueError("operational pre-exposure history drifted")
    elif history != expected_histories[state]:
        raise ValueError("operational attempt history drifted")
    released = "release_sealed" in history
    if released:
        _sha(opening_release_root_sha256, "opening_release_root_sha256")
    elif opening_release_root_sha256 is not None:
        raise ValueError("reserved attempt carries a release root")
    failed = state == "pre_exposure_failure"
    if failed != (terminal_reason is not None):
        raise ValueError("pre-exposure failure reason drifted")
    if terminal_reason is not None:
        _reason(terminal_reason)
    consumed = state in {
        "exposure_started",
    }
    return {
        "schema_version": OPERATIONAL_SCHEMA_VERSION,
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "run_nonce": run_nonce,
        "authorized_output_dir": _absolute_output(authorized_output_dir),
        "controller_root_sha256": controller_root_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "state": state,
        "history": list(history),
        "terminal_reason": terminal_reason,
        "scientific_identity_consumed": consumed,
        "new_attempt_allowed_if_pre_exposure_failure": failed,
    }


def _freeze_scientific(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    opening_release_root_sha256: str,
    run_nonce: str,
    state: str,
    history: list[str],
    first_unit_ordinal: int,
    first_arm: str,
    planned_arm_run_count: int | None,
    terminal_arm_run_count: int,
    terminal_artifact_root_sha256: str | None,
    terminal_reason: str | None,
) -> dict[str, Any]:
    for name, value in {
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "run_nonce": run_nonce,
    }.items():
        _sha(value, name)
    if state not in SCIENTIFIC_STATES:
        raise ValueError("scientific state drifted")
    allowed_histories = {
        "exposure_started": ["exposure_started"],
        "full_denominator_formed": [
            "exposure_started",
            "full_denominator_formed",
        ],
        "evaluated": [
            "exposure_started",
            "full_denominator_formed",
            "evaluated",
        ],
        "terminal_success": [
            "exposure_started",
            "full_denominator_formed",
            "evaluated",
            "terminal_success",
        ],
        "terminal_failure": None,
    }
    if type(history) is not list or not history or history[-1] != state:
        raise ValueError("scientific history/current state drifted")
    if state == "terminal_failure":
        if history[0] != "exposure_started" or history[-1] != state:
            raise ValueError("scientific failure history drifted")
        middle = history[1:-1]
        if middle not in (
            [],
            ["full_denominator_formed"],
            ["full_denominator_formed", "evaluated"],
        ):
            raise ValueError("scientific failure transition order drifted")
    elif history != allowed_histories[state]:
        raise ValueError("scientific transition order drifted")
    if type(first_unit_ordinal) is not int or first_unit_ordinal < 0:
        raise ValueError("scientific first unit drifted")
    if type(first_arm) is not str or not first_arm:
        raise ValueError("scientific first arm drifted")
    denominator = state in {
        "full_denominator_formed",
        "evaluated",
        "terminal_success",
    } or (
        state == "terminal_failure"
        and "full_denominator_formed" in history
    )
    if denominator:
        if (
            type(planned_arm_run_count) is not int
            or planned_arm_run_count <= 0
            or type(terminal_arm_run_count) is not int
            or terminal_arm_run_count != planned_arm_run_count
        ):
            raise ValueError("scientific denominator drifted")
    elif planned_arm_run_count is not None or terminal_arm_run_count != 0:
        raise ValueError("pre-denominator scientific counts drifted")
    terminal = state in {"terminal_success", "terminal_failure"}
    if terminal:
        _sha(
            terminal_artifact_root_sha256,
            "terminal_artifact_root_sha256",
        )
        _reason(terminal_reason)
    elif terminal_artifact_root_sha256 is not None or terminal_reason is not None:
        raise ValueError("nonterminal scientific ledger carries terminal data")
    return {
        "schema_version": SCIENTIFIC_SCHEMA_VERSION,
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "run_nonce": run_nonce,
        "state": state,
        "history": list(history),
        "first_unit_ordinal": first_unit_ordinal,
        "first_arm": first_arm,
        "planned_arm_run_count": planned_arm_run_count,
        "terminal_arm_run_count": terminal_arm_run_count,
        "terminal_artifact_root_sha256": terminal_artifact_root_sha256,
        "terminal_reason": terminal_reason,
        "second_exposure_allowed": False,
    }


def _transition_operational(
    path: Path,
    *,
    expected_state: str,
    next_state: str,
    opening_release_root_sha256: str | None,
    terminal_reason: str | None,
) -> dict[str, Any]:
    path = Path(path)
    lock = _acquire_transition_lock(path)
    try:
        current = validate_operational_attempt(_strict_canonical_json(path))
        if current["state"] != expected_state:
            raise FileExistsError("operational attempt state already advanced")
        allowed = {
            ("release_reserved", "release_sealed"),
            ("release_reserved", "pre_exposure_failure"),
            ("release_sealed", "pre_exposure_failure"),
            ("release_sealed", "exposure_started"),
        }
        if (expected_state, next_state) not in allowed:
            raise ValueError("operational attempt transition is not allowed")
        root = (
            opening_release_root_sha256
            if expected_state == "release_reserved"
            else current["opening_release_root_sha256"]
        )
        updated = _freeze_operational(
            holdout_identity_sha256=current["holdout_identity_sha256"],
            experiment_protocol_sha256=current["experiment_protocol_sha256"],
            run_nonce=current["run_nonce"],
            authorized_output_dir=current["authorized_output_dir"],
            controller_root_sha256=current["controller_root_sha256"],
            opening_release_root_sha256=root,
            state=next_state,
            history=[*current["history"], next_state],
            terminal_reason=terminal_reason,
        )
        _replace_unlocked(path, updated)
        return updated
    finally:
        lock.unlink(missing_ok=True)


def _transition_scientific(
    path: Path,
    *,
    expected_state: str,
    next_state: str,
    planned_arm_run_count: int | None,
    terminal_arm_run_count: int | None,
    terminal_artifact_root_sha256: str | None,
    terminal_reason: str | None,
) -> dict[str, Any]:
    path = Path(path)
    lock = _acquire_transition_lock(path)
    try:
        current = validate_scientific_ledger(_strict_canonical_json(path))
        if current["state"] != expected_state:
            raise FileExistsError("scientific identity state already advanced")
        allowed = {
            ("exposure_started", "full_denominator_formed"),
            ("full_denominator_formed", "evaluated"),
            ("evaluated", "terminal_success"),
            ("exposure_started", "terminal_failure"),
            ("full_denominator_formed", "terminal_failure"),
            ("evaluated", "terminal_failure"),
        }
        if (expected_state, next_state) not in allowed:
            raise ValueError("scientific transition is not allowed")
        planned = (
            planned_arm_run_count
            if expected_state == "exposure_started"
            and next_state == "full_denominator_formed"
            else current["planned_arm_run_count"]
        )
        terminal = (
            terminal_arm_run_count
            if expected_state == "exposure_started"
            and next_state == "full_denominator_formed"
            else current["terminal_arm_run_count"]
        )
        updated = _freeze_scientific(
            holdout_identity_sha256=current["holdout_identity_sha256"],
            experiment_protocol_sha256=current["experiment_protocol_sha256"],
            opening_release_root_sha256=current[
                "opening_release_root_sha256"
            ],
            run_nonce=current["run_nonce"],
            state=next_state,
            history=[*current["history"], next_state],
            first_unit_ordinal=current["first_unit_ordinal"],
            first_arm=current["first_arm"],
            planned_arm_run_count=planned,
            terminal_arm_run_count=terminal,
            terminal_artifact_root_sha256=terminal_artifact_root_sha256,
            terminal_reason=terminal_reason,
        )
        _replace_unlocked(path, updated)
        return updated
    finally:
        lock.unlink(missing_ok=True)


def _transition_operational_identity(
    operational_attempt: Path,
    *,
    expected_state: str,
    next_state: str,
) -> dict[str, Any]:
    attempt = validate_operational_attempt(
        _strict_canonical_json(Path(operational_attempt))
    )
    cas_root = Path(operational_attempt).resolve().parent.parent
    path = operational_identity_path(cas_root, attempt["holdout_identity_sha256"])
    lock = _acquire_transition_lock(path)
    try:
        current = validate_operational_identity_reservation(
            _strict_canonical_json(path)
        )
        if (
            current["state"] != expected_state
            or current["run_nonce"] != attempt["run_nonce"]
            or Path(current["operational_attempt_path"]).resolve()
            != Path(operational_attempt).resolve()
        ):
            raise FileExistsError(
                "operational identity reservation already advanced"
            )
        allowed = {
            ("active", "pre_exposure_released"),
            ("active", "exposure_started"),
        }
        if (expected_state, next_state) not in allowed:
            raise ValueError("operational identity transition is not allowed")
        updated = _freeze_operational_identity_reservation(
            holdout_identity_sha256=current["holdout_identity_sha256"],
            experiment_protocol_sha256=current[
                "experiment_protocol_sha256"
            ],
            run_nonce=current["run_nonce"],
            operational_attempt_path=current["operational_attempt_path"],
            state=next_state,
        )
        _replace_unlocked(path, updated)
        return updated
    finally:
        lock.unlink(missing_ok=True)


def _create_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        raw = _canonical_bytes(value)
        os.write(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _acquire_transition_lock(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(path.suffix + ".transition.lock")
    descriptor = os.open(
        lock,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    os.close(descriptor)
    return lock


def _replace_unlocked(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        if temporary.exists():
            raise FileExistsError("stale holdout ledger temporary exists")
        _create_exclusive(temporary, value)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _strict_canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate holdout ledger key: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite holdout ledger token: {token}")
        ),
    )
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"noncanonical holdout ledger: {path}")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _absolute_output(value: Any) -> str:
    if type(value) is not str or not value:
        raise ValueError("authorized output must be a nonempty string")
    path = Path(value)
    if not path.is_absolute() or str(path) != str(path.resolve()):
        raise ValueError("authorized output must be an exact absolute path")
    return str(path)


def _sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value


def _reason(value: Any) -> str:
    if type(value) is not str or not value:
        raise ValueError("terminal reason must be a nonempty string")
    return value
