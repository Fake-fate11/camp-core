"""Fail-closed, nonsecret connection receipts for V26 remote observation.

The receipt binds a monitor to the secure connection wrapper that launched an
existing V26 worker.  It intentionally contains no password, private key,
token, or executable command.  Consumers must use its exact wrapper reference
and reject endpoint rediscovery or overrides.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any


CONNECTION_RECEIPT_SCHEMA_VERSION = "camp_dp_v26_launch_connection_receipt_v1"
CONNECTION_RECEIPT_EVIDENCE_ROLE = "development_nonholdout_launch_connection_identity"

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "evidence_role",
    "connection_profile_id",
    "secure_wrapper",
    "username",
    "endpoint_identity",
    "host_key",
    "canonical_remote",
    "launch_worker",
    "created_at",
    "forbid_endpoint_rediscovery",
    "secrets_reference_only",
    "connection_receipt_content_sha256",
}
_SECRET_FIELD_NAMES = {
    "password",
    "private_key",
    "token",
    "secret",
    "credential_blob",
    "full_command",
    "command",
}


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_nonempty_string(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _require_sha256(value: Any, label: str) -> str:
    value = _require_nonempty_string(value, label)
    if len(value) != 64:
        raise ValueError(f"{label} must be a SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a SHA256") from exc
    return value


def _require_git_head(value: Any, label: str) -> str:
    value = _require_nonempty_string(value, label)
    if len(value) != 40:
        raise ValueError(f"{label} must be a Git SHA1")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be a Git SHA1") from exc
    return value


def _require_absolute_remote_path(value: Any, label: str) -> str:
    value = _require_nonempty_string(value, label)
    if not value.startswith("/"):
        raise ValueError(f"{label} must be an absolute remote path")
    return value


def _reject_secret_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if type(key) is not str:
                raise ValueError("connection receipt keys must be strings")
            if key.casefold() in _SECRET_FIELD_NAMES:
                raise ValueError("connection receipt must not serialize secrets or commands")
            _reject_secret_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secret_fields(child)


def _receipt_content_sha256(value: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop("connection_receipt_content_sha256", None)
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _validate_created_at(value: Any) -> str:
    value = _require_nonempty_string(value, "created_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("created_at must include a timezone")
    return value


def build_connection_receipt(
    *,
    connection_profile_id: str,
    secure_wrapper_reference: str,
    secure_wrapper_sha256: str,
    credential_target_reference: str,
    username: str,
    endpoint_hostname: str,
    endpoint_port: int,
    host_key_algorithm: str,
    host_key_fingerprint_sha256: str,
    camp_checkout: str,
    fixed_dp_repo: str,
    acquisition_root: str,
    union_root: str,
    worker_lock: str,
    worker_pid: int,
    worker_identity: str,
    camp_head: str,
    fixed_dp_head: str,
    launch_record_reference: str,
    created_at: str,
) -> dict[str, Any]:
    """Build a complete nonsecret receipt before atomically serializing it."""

    if type(endpoint_port) is not int or endpoint_port <= 0 or endpoint_port > 65535:
        raise ValueError("endpoint_port must be a valid integer TCP port")
    if type(worker_pid) is not int or worker_pid <= 0:
        raise ValueError("worker_pid must be a positive integer")
    value: dict[str, Any] = {
        "schema_version": CONNECTION_RECEIPT_SCHEMA_VERSION,
        "evidence_role": CONNECTION_RECEIPT_EVIDENCE_ROLE,
        "connection_profile_id": connection_profile_id,
        "secure_wrapper": {
            "reference": secure_wrapper_reference,
            "sha256": secure_wrapper_sha256,
            "credential_target_reference": credential_target_reference,
        },
        "username": username,
        "endpoint_identity": {"hostname": endpoint_hostname, "port": endpoint_port},
        "host_key": {
            "algorithm": host_key_algorithm,
            "fingerprint_sha256": host_key_fingerprint_sha256,
        },
        "canonical_remote": {
            "camp_checkout": camp_checkout,
            "fixed_dp_repo": fixed_dp_repo,
            "acquisition_root": acquisition_root,
            "union_root": union_root,
            "worker_lock": worker_lock,
        },
        "launch_worker": {
            "pid": worker_pid,
            "identity": worker_identity,
            "camp_head": camp_head,
            "fixed_dp_head": fixed_dp_head,
            "launch_record_reference": launch_record_reference,
        },
        "created_at": created_at,
        "forbid_endpoint_rediscovery": True,
        "secrets_reference_only": True,
    }
    value["connection_receipt_content_sha256"] = _receipt_content_sha256(value)
    return validate_connection_receipt(value)


def validate_connection_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate receipt schema and prohibit secrets or endpoint rediscovery."""

    if not isinstance(value, Mapping):
        raise ValueError("connection receipt must be a mapping")
    receipt = copy.deepcopy(dict(value))
    if set(receipt) != _TOP_LEVEL_FIELDS:
        raise ValueError("connection receipt fields drifted")
    _reject_secret_fields(receipt)
    if receipt["schema_version"] != CONNECTION_RECEIPT_SCHEMA_VERSION:
        raise ValueError("connection receipt schema version drifted")
    if receipt["evidence_role"] != CONNECTION_RECEIPT_EVIDENCE_ROLE:
        raise ValueError("connection receipt evidence role drifted")
    _require_nonempty_string(receipt["connection_profile_id"], "connection_profile_id")
    if receipt["forbid_endpoint_rediscovery"] is not True:
        raise ValueError("connection receipt must forbid endpoint rediscovery")
    if receipt["secrets_reference_only"] is not True:
        raise ValueError("connection receipt must use secret references only")
    _validate_created_at(receipt["created_at"])

    wrapper = receipt["secure_wrapper"]
    if type(wrapper) is not dict or set(wrapper) != {
        "reference",
        "sha256",
        "credential_target_reference",
    }:
        raise ValueError("secure wrapper binding drifted")
    _require_nonempty_string(wrapper["reference"], "secure wrapper reference")
    _require_sha256(wrapper["sha256"], "secure wrapper SHA")
    _require_nonempty_string(wrapper["credential_target_reference"], "credential target reference")

    _require_nonempty_string(receipt["username"], "username")
    endpoint = receipt["endpoint_identity"]
    if type(endpoint) is not dict or set(endpoint) != {"hostname", "port"}:
        raise ValueError("endpoint identity drifted")
    _require_nonempty_string(endpoint["hostname"], "endpoint hostname")
    if type(endpoint["port"]) is not int or not 0 < endpoint["port"] <= 65535:
        raise ValueError("endpoint port drifted")
    host_key = receipt["host_key"]
    if type(host_key) is not dict or set(host_key) != {"algorithm", "fingerprint_sha256"}:
        raise ValueError("host key binding drifted")
    _require_nonempty_string(host_key["algorithm"], "host key algorithm")
    fingerprint = _require_nonempty_string(
        host_key["fingerprint_sha256"], "host key fingerprint"
    )
    if not fingerprint.startswith("SHA256:"):
        raise ValueError("host key fingerprint must use SHA256 form")

    remote = receipt["canonical_remote"]
    required_remote = {
        "camp_checkout",
        "fixed_dp_repo",
        "acquisition_root",
        "union_root",
        "worker_lock",
    }
    if type(remote) is not dict or set(remote) != required_remote:
        raise ValueError("canonical remote bindings drifted")
    for key in sorted(required_remote):
        _require_absolute_remote_path(remote[key], f"canonical remote {key}")

    worker = receipt["launch_worker"]
    required_worker = {
        "pid",
        "identity",
        "camp_head",
        "fixed_dp_head",
        "launch_record_reference",
    }
    if type(worker) is not dict or set(worker) != required_worker:
        raise ValueError("launch worker binding drifted")
    if type(worker["pid"]) is not int or worker["pid"] <= 0:
        raise ValueError("launch worker PID drifted")
    _require_nonempty_string(worker["identity"], "launch worker identity")
    _require_git_head(worker["camp_head"], "launch CAMP head")
    _require_git_head(worker["fixed_dp_head"], "launch fixed-DP head")
    _require_nonempty_string(worker["launch_record_reference"], "launch record reference")

    expected_hash = _receipt_content_sha256(receipt)
    if receipt["connection_receipt_content_sha256"] != expected_hash:
        raise ValueError("connection receipt content SHA drifted")
    return receipt


def write_connection_receipt(*, path: Path, receipt: Mapping[str, Any]) -> str:
    """Atomically write a validated receipt and return its file SHA256."""

    validated = validate_connection_receipt(receipt)
    target = path.resolve()
    if target.exists():
        raise FileExistsError(f"connection receipt already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        staging.write_text(
            json.dumps(validated, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, target)
    finally:
        staging.unlink(missing_ok=True)
    return _file_sha256(target)


def load_verified_monitor_binding(
    *,
    receipt_path: Path,
    expected_receipt_sha256: str,
    expected_connection_profile_id: str,
    endpoint_override: str | None = None,
) -> dict[str, Any]:
    """Load the exact receipt-bound wrapper; endpoint overrides are fatal."""

    if endpoint_override is not None:
        raise ValueError("endpoint rediscovery or override is forbidden")
    expected_receipt_sha256 = _require_sha256(
        expected_receipt_sha256, "expected connection receipt SHA"
    )
    expected_connection_profile_id = _require_nonempty_string(
        expected_connection_profile_id, "expected connection profile ID"
    )
    path = receipt_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if _file_sha256(path) != expected_receipt_sha256:
        raise ValueError("connection receipt file SHA drifted")
    receipt = validate_connection_receipt(json.loads(path.read_text(encoding="utf-8")))
    if receipt["connection_profile_id"] != expected_connection_profile_id:
        raise ValueError("connection profile ID drifted")
    wrapper_path = Path(receipt["secure_wrapper"]["reference"])
    if not wrapper_path.is_file():
        raise FileNotFoundError(wrapper_path)
    if _file_sha256(wrapper_path) != receipt["secure_wrapper"]["sha256"]:
        raise ValueError("secure wrapper SHA drifted")
    return receipt
