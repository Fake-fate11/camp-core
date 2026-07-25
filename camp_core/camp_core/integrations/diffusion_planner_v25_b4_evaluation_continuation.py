from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_v25_b4_evaluation_policy_correction import (
    CONTINUATION_STATE_SEQUENCE,
    EXPERIMENT_PROTOCOL_SHA256,
    HOLDOUT_IDENTITY_SHA256,
    OLD_TERMINAL_LEDGER_SHA256,
    OLD_TERMINAL_REASON,
    OPENING_RELEASE_ROOT_SHA256,
    RUN_NONCE,
)
from .diffusion_planner_v25_holdout_contract import strict_equal


SCHEMA_VERSION = "camp_dp_v25_fresh_b4_evaluation_continuation_cas_v1"
IDENTITY_SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_evaluation_continuation_identity_slot_v1"
)
STATES = CONTINUATION_STATE_SEQUENCE
_FIELDS = frozenset(
    {
        "schema_version",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "run_nonce",
        "opening_release_root_sha256",
        "old_terminal_ledger_path",
        "old_terminal_ledger_sha256",
        "old_terminal_reason",
        "correction_authority_root_sha256",
        "correction_authority_review_root_sha256",
        "continuation_key_sha256",
        "state",
        "history",
        "corrected_evaluation_output_dir",
        "corrected_evaluation_review_output_dir",
        "evaluation_root_sha256",
        "evaluation_review_root_sha256",
        "second_authority_allowed",
        "second_evaluation_allowed",
        "fresh_execution_rerun_allowed",
        "old_scientific_ledger_rewrite_allowed",
    }
)
_IDENTITY_FIELDS = frozenset(
    {
        "schema_version",
        "holdout_identity_sha256",
        "old_terminal_ledger_sha256",
        "correction_authority_root_sha256",
        "continuation_key_sha256",
        "continuation_ledger_path",
        "second_authority_allowed",
    }
)


def continuation_key_sha256(
    *,
    holdout_identity_sha256: str,
    old_terminal_ledger_sha256: str,
    correction_authority_root_sha256: str,
) -> str:
    identity = _sha(holdout_identity_sha256, "holdout identity")
    old_ledger = _sha(old_terminal_ledger_sha256, "old terminal ledger")
    authority = _sha(correction_authority_root_sha256, "correction authority")
    return hashlib.sha256(
        f"{identity}:{old_ledger}:{authority}".encode("ascii")
    ).hexdigest()


def continuation_identity_key_sha256(
    *,
    holdout_identity_sha256: str,
    old_terminal_ledger_sha256: str,
) -> str:
    identity = _sha(holdout_identity_sha256, "holdout identity")
    old_ledger = _sha(old_terminal_ledger_sha256, "old terminal ledger")
    return hashlib.sha256(f"{identity}:{old_ledger}".encode("ascii")).hexdigest()


def continuation_ledger_path(
    cas_namespace: Path,
    *,
    holdout_identity_sha256: str,
    old_terminal_ledger_sha256: str,
    correction_authority_root_sha256: str,
) -> Path:
    key = continuation_key_sha256(
        holdout_identity_sha256=holdout_identity_sha256,
        old_terminal_ledger_sha256=old_terminal_ledger_sha256,
        correction_authority_root_sha256=correction_authority_root_sha256,
    )
    return Path(cas_namespace).resolve() / f"{key}.json"


def continuation_identity_slot_path(
    identity_slot_namespace: Path,
    *,
    holdout_identity_sha256: str,
    old_terminal_ledger_sha256: str,
) -> Path:
    key = continuation_identity_key_sha256(
        holdout_identity_sha256=holdout_identity_sha256,
        old_terminal_ledger_sha256=old_terminal_ledger_sha256,
    )
    return Path(identity_slot_namespace).resolve() / f"{key}.json"


def authorize_from_preserved_denominator(
    *,
    cas_namespace: Path,
    identity_slot_namespace: Path,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    run_nonce: str,
    opening_release_root_sha256: str,
    old_terminal_ledger_path: str,
    old_terminal_ledger_sha256: str,
    old_terminal_reason: str,
    correction_authority_root_sha256: str,
    correction_authority_review_root_sha256: str,
    corrected_evaluation_output_dir: str,
    corrected_evaluation_review_output_dir: str,
) -> tuple[Path, dict[str, Any]]:
    identity = _sha(holdout_identity_sha256, "holdout identity")
    protocol = _sha(experiment_protocol_sha256, "experiment protocol")
    nonce = _sha(run_nonce, "run nonce")
    release = _sha(opening_release_root_sha256, "opening release")
    old_path = _absolute_posix(
        old_terminal_ledger_path, "old terminal ledger"
    )
    old_sha = _sha(old_terminal_ledger_sha256, "old terminal ledger")
    authority = _sha(
        correction_authority_root_sha256, "correction authority"
    )
    authority_review = _sha(
        correction_authority_review_root_sha256,
        "correction authority review",
    )
    evaluation_dir = _absolute_posix(
        corrected_evaluation_output_dir, "corrected evaluation output"
    )
    review_dir = _absolute_posix(
        corrected_evaluation_review_output_dir,
        "corrected evaluation review output",
    )
    if (
        identity != HOLDOUT_IDENTITY_SHA256
        or protocol != EXPERIMENT_PROTOCOL_SHA256
        or nonce != RUN_NONCE
        or release != OPENING_RELEASE_ROOT_SHA256
        or old_sha != OLD_TERMINAL_LEDGER_SHA256
        or old_terminal_reason != OLD_TERMINAL_REASON
    ):
        raise ValueError("continuation authority binding drifted")
    ledger_path = continuation_ledger_path(
        cas_namespace,
        holdout_identity_sha256=identity,
        old_terminal_ledger_sha256=old_sha,
        correction_authority_root_sha256=authority,
    )
    slot_path = continuation_identity_slot_path(
        identity_slot_namespace,
        holdout_identity_sha256=identity,
        old_terminal_ledger_sha256=old_sha,
    )
    key = ledger_path.stem
    value = _freeze(
        holdout_identity_sha256=identity,
        experiment_protocol_sha256=protocol,
        run_nonce=nonce,
        opening_release_root_sha256=release,
        old_terminal_ledger_path=old_path,
        old_terminal_ledger_sha256=old_sha,
        old_terminal_reason=old_terminal_reason,
        correction_authority_root_sha256=authority,
        correction_authority_review_root_sha256=authority_review,
        continuation_key=key,
        state="authorized_from_preserved_denominator",
        history=["authorized_from_preserved_denominator"],
        corrected_evaluation_output_dir=evaluation_dir,
        corrected_evaluation_review_output_dir=review_dir,
        evaluation_root_sha256=None,
        evaluation_review_root_sha256=None,
    )
    slot = _freeze_identity_slot(
        holdout_identity_sha256=identity,
        old_terminal_ledger_sha256=old_sha,
        correction_authority_root_sha256=authority,
        continuation_key=key,
        continuation_ledger_path=str(ledger_path),
    )
    lock = _acquire_transition_lock(slot_path)
    try:
        if slot_path.exists():
            raise FileExistsError("Fresh B4 correction authority already exists")
        if ledger_path.exists():
            raise FileExistsError("Fresh B4 continuation ledger already exists")
        _create_exclusive(ledger_path, value)
        try:
            _create_exclusive(slot_path, slot)
        except BaseException:
            ledger_path.unlink(missing_ok=True)
            raise
    finally:
        lock.unlink(missing_ok=True)
    return ledger_path, value


def start_corrected_evaluation(
    path: Path,
    *,
    correction_authority_root_sha256: str,
    corrected_evaluation_output_dir: str,
) -> dict[str, Any]:
    return _transition(
        path,
        expected_state="authorized_from_preserved_denominator",
        next_state="evaluation_started",
        correction_authority_root_sha256=correction_authority_root_sha256,
        corrected_output_dir=corrected_evaluation_output_dir,
        artifact_root_sha256=None,
    )


def mark_corrected_evaluation_artifact_formed(
    path: Path,
    *,
    correction_authority_root_sha256: str,
    corrected_evaluation_output_dir: str,
    evaluation_root_sha256: str,
) -> dict[str, Any]:
    return _transition(
        path,
        expected_state="evaluation_started",
        next_state="evaluation_artifact_formed",
        correction_authority_root_sha256=correction_authority_root_sha256,
        corrected_output_dir=corrected_evaluation_output_dir,
        artifact_root_sha256=evaluation_root_sha256,
    )


def mark_independently_reviewed_terminal(
    path: Path,
    *,
    correction_authority_root_sha256: str,
    corrected_evaluation_review_output_dir: str,
    evaluation_review_root_sha256: str,
) -> dict[str, Any]:
    return _transition(
        path,
        expected_state="evaluation_artifact_formed",
        next_state="independently_reviewed_terminal",
        correction_authority_root_sha256=correction_authority_root_sha256,
        corrected_output_dir=corrected_evaluation_review_output_dir,
        artifact_root_sha256=evaluation_review_root_sha256,
    )


def validate_continuation_ledger(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError("continuation ledger field set drifted")
    expected = _freeze(
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        run_nonce=value["run_nonce"],
        opening_release_root_sha256=value["opening_release_root_sha256"],
        old_terminal_ledger_path=value["old_terminal_ledger_path"],
        old_terminal_ledger_sha256=value["old_terminal_ledger_sha256"],
        old_terminal_reason=value["old_terminal_reason"],
        correction_authority_root_sha256=value[
            "correction_authority_root_sha256"
        ],
        correction_authority_review_root_sha256=value[
            "correction_authority_review_root_sha256"
        ],
        continuation_key=value["continuation_key_sha256"],
        state=value["state"],
        history=value["history"],
        corrected_evaluation_output_dir=value[
            "corrected_evaluation_output_dir"
        ],
        corrected_evaluation_review_output_dir=value[
            "corrected_evaluation_review_output_dir"
        ],
        evaluation_root_sha256=value["evaluation_root_sha256"],
        evaluation_review_root_sha256=value[
            "evaluation_review_root_sha256"
        ],
    )
    if not strict_equal(value, expected):
        raise ValueError("continuation ledger exact value drifted")
    return expected


def validate_continuation_identity_slot(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _IDENTITY_FIELDS:
        raise ValueError("continuation identity field set drifted")
    expected = _freeze_identity_slot(
        holdout_identity_sha256=value["holdout_identity_sha256"],
        old_terminal_ledger_sha256=value["old_terminal_ledger_sha256"],
        correction_authority_root_sha256=value[
            "correction_authority_root_sha256"
        ],
        continuation_key=value["continuation_key_sha256"],
        continuation_ledger_path=value["continuation_ledger_path"],
    )
    if not strict_equal(value, expected):
        raise ValueError("continuation identity exact value drifted")
    return expected


def load_continuation_ledger(path: Path) -> dict[str, Any]:
    return validate_continuation_ledger(_strict_canonical_json(Path(path)))


def _transition(
    path: Path,
    *,
    expected_state: str,
    next_state: str,
    correction_authority_root_sha256: str,
    corrected_output_dir: str,
    artifact_root_sha256: str | None,
) -> dict[str, Any]:
    ledger_path = Path(path).resolve()
    lock = _acquire_transition_lock(ledger_path)
    try:
        current = load_continuation_ledger(ledger_path)
        if current["state"] != expected_state:
            raise FileExistsError("continuation state already advanced")
        allowed = {
            (
                "authorized_from_preserved_denominator",
                "evaluation_started",
            ),
            ("evaluation_started", "evaluation_artifact_formed"),
            (
                "evaluation_artifact_formed",
                "independently_reviewed_terminal",
            ),
        }
        if (expected_state, next_state) not in allowed:
            raise ValueError("continuation transition is not allowed")
        authority = _sha(
            correction_authority_root_sha256, "correction authority"
        )
        if authority != current["correction_authority_root_sha256"]:
            raise ValueError("continuation authority root drifted")
        exact_output = _absolute_posix(
            corrected_output_dir, "corrected output"
        )
        expected_output = (
            current["corrected_evaluation_output_dir"]
            if next_state in {"evaluation_started", "evaluation_artifact_formed"}
            else current["corrected_evaluation_review_output_dir"]
        )
        if exact_output != expected_output:
            raise ValueError("continuation corrected output drifted")
        evaluation_root = current["evaluation_root_sha256"]
        review_root = current["evaluation_review_root_sha256"]
        if next_state == "evaluation_started":
            if artifact_root_sha256 is not None:
                raise ValueError("evaluation start cannot bind an artifact")
        elif next_state == "evaluation_artifact_formed":
            evaluation_root = _sha(
                artifact_root_sha256, "corrected evaluation root"
            )
        else:
            review_root = _sha(
                artifact_root_sha256, "corrected evaluation review root"
            )
        updated = _freeze(
            holdout_identity_sha256=current["holdout_identity_sha256"],
            experiment_protocol_sha256=current[
                "experiment_protocol_sha256"
            ],
            run_nonce=current["run_nonce"],
            opening_release_root_sha256=current[
                "opening_release_root_sha256"
            ],
            old_terminal_ledger_path=current["old_terminal_ledger_path"],
            old_terminal_ledger_sha256=current[
                "old_terminal_ledger_sha256"
            ],
            old_terminal_reason=current["old_terminal_reason"],
            correction_authority_root_sha256=current[
                "correction_authority_root_sha256"
            ],
            correction_authority_review_root_sha256=current[
                "correction_authority_review_root_sha256"
            ],
            continuation_key=current["continuation_key_sha256"],
            state=next_state,
            history=[*current["history"], next_state],
            corrected_evaluation_output_dir=current[
                "corrected_evaluation_output_dir"
            ],
            corrected_evaluation_review_output_dir=current[
                "corrected_evaluation_review_output_dir"
            ],
            evaluation_root_sha256=evaluation_root,
            evaluation_review_root_sha256=review_root,
        )
        _replace_unlocked(ledger_path, updated)
        return updated
    finally:
        lock.unlink(missing_ok=True)


def _freeze(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    run_nonce: str,
    opening_release_root_sha256: str,
    old_terminal_ledger_path: str,
    old_terminal_ledger_sha256: str,
    old_terminal_reason: str,
    correction_authority_root_sha256: str,
    correction_authority_review_root_sha256: str,
    continuation_key: str,
    state: str,
    history: list[str],
    corrected_evaluation_output_dir: str,
    corrected_evaluation_review_output_dir: str,
    evaluation_root_sha256: str | None,
    evaluation_review_root_sha256: str | None,
) -> dict[str, Any]:
    identity = _sha(holdout_identity_sha256, "holdout identity")
    protocol = _sha(experiment_protocol_sha256, "experiment protocol")
    nonce = _sha(run_nonce, "run nonce")
    release = _sha(opening_release_root_sha256, "opening release")
    old_path = _absolute_posix(
        old_terminal_ledger_path, "old terminal ledger"
    )
    old_sha = _sha(old_terminal_ledger_sha256, "old terminal ledger")
    authority = _sha(
        correction_authority_root_sha256, "correction authority"
    )
    authority_review = _sha(
        correction_authority_review_root_sha256,
        "correction authority review",
    )
    key = _sha(continuation_key, "continuation key")
    evaluation_dir = _absolute_posix(
        corrected_evaluation_output_dir, "corrected evaluation output"
    )
    review_dir = _absolute_posix(
        corrected_evaluation_review_output_dir,
        "corrected evaluation review output",
    )
    if (
        identity != HOLDOUT_IDENTITY_SHA256
        or protocol != EXPERIMENT_PROTOCOL_SHA256
        or nonce != RUN_NONCE
        or release != OPENING_RELEASE_ROOT_SHA256
        or old_sha != OLD_TERMINAL_LEDGER_SHA256
        or old_terminal_reason != OLD_TERMINAL_REASON
        or key
        != continuation_key_sha256(
            holdout_identity_sha256=identity,
            old_terminal_ledger_sha256=old_sha,
            correction_authority_root_sha256=authority,
        )
    ):
        raise ValueError("continuation immutable binding drifted")
    if state not in STATES:
        raise ValueError("continuation state drifted")
    expected_history = list(STATES[: STATES.index(state) + 1])
    if type(history) is not list or history != expected_history:
        raise ValueError("continuation history drifted")
    if state in {
        "authorized_from_preserved_denominator",
        "evaluation_started",
    }:
        if evaluation_root_sha256 is not None:
            raise ValueError("pre-artifact continuation carries evaluation root")
    else:
        evaluation_root_sha256 = _sha(
            evaluation_root_sha256, "corrected evaluation root"
        )
    if state == "independently_reviewed_terminal":
        evaluation_review_root_sha256 = _sha(
            evaluation_review_root_sha256,
            "corrected evaluation review root",
        )
    elif evaluation_review_root_sha256 is not None:
        raise ValueError("pre-review continuation carries review root")
    return {
        "schema_version": SCHEMA_VERSION,
        "holdout_identity_sha256": identity,
        "experiment_protocol_sha256": protocol,
        "run_nonce": nonce,
        "opening_release_root_sha256": release,
        "old_terminal_ledger_path": old_path,
        "old_terminal_ledger_sha256": old_sha,
        "old_terminal_reason": old_terminal_reason,
        "correction_authority_root_sha256": authority,
        "correction_authority_review_root_sha256": authority_review,
        "continuation_key_sha256": key,
        "state": state,
        "history": list(history),
        "corrected_evaluation_output_dir": evaluation_dir,
        "corrected_evaluation_review_output_dir": review_dir,
        "evaluation_root_sha256": evaluation_root_sha256,
        "evaluation_review_root_sha256": evaluation_review_root_sha256,
        "second_authority_allowed": False,
        "second_evaluation_allowed": False,
        "fresh_execution_rerun_allowed": False,
        "old_scientific_ledger_rewrite_allowed": False,
    }


def _freeze_identity_slot(
    *,
    holdout_identity_sha256: str,
    old_terminal_ledger_sha256: str,
    correction_authority_root_sha256: str,
    continuation_key: str,
    continuation_ledger_path: str,
) -> dict[str, Any]:
    identity = _sha(holdout_identity_sha256, "holdout identity")
    old_sha = _sha(old_terminal_ledger_sha256, "old terminal ledger")
    authority = _sha(
        correction_authority_root_sha256, "correction authority"
    )
    key = _sha(continuation_key, "continuation key")
    ledger_path = _absolute_posix(
        continuation_ledger_path, "continuation ledger"
    )
    if (
        identity != HOLDOUT_IDENTITY_SHA256
        or old_sha != OLD_TERMINAL_LEDGER_SHA256
        or key
        != continuation_key_sha256(
            holdout_identity_sha256=identity,
            old_terminal_ledger_sha256=old_sha,
            correction_authority_root_sha256=authority,
        )
        or Path(ledger_path).stem != key
    ):
        raise ValueError("continuation identity binding drifted")
    return {
        "schema_version": IDENTITY_SCHEMA_VERSION,
        "holdout_identity_sha256": identity,
        "old_terminal_ledger_sha256": old_sha,
        "correction_authority_root_sha256": authority,
        "continuation_key_sha256": key,
        "continuation_ledger_path": ledger_path,
        "second_authority_allowed": False,
    }


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
            raise FileExistsError("stale continuation temporary exists")
        _create_exclusive(temporary, value)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _strict_canonical_json(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate continuation ledger key: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite continuation token: {token}")
        ),
    )
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"noncanonical continuation ledger: {path}")
    return value


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
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


def _absolute_posix(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value.startswith("/")
        or value.endswith("/")
        or "/../" in f"{value}/"
        or "/./" in f"{value}/"
    ):
        raise ValueError(f"{label} path drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} SHA drifted")
    return value
