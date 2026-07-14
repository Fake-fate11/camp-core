#!/usr/bin/env python3
"""Read the authoritative v19 audit/status controller pointer."""

from __future__ import annotations

from pathlib import Path


POINTER_KEYS = (
    "current_v19_status",
    "current_v19_artifact_scope",
    "current_v19_artifact",
    "current_v19_artifact_root_sha256",
    "next_work_target",
)
V20_POINTER_KEYS = (
    "current_v20_status",
    "camp_github_autodl_head",
    "fixed_dp_head",
    "next_work_target",
)


def _latest_pointer(
    lines: list[str], keys: tuple[str, ...] = POINTER_KEYS
) -> dict[str, str]:
    pointer = {}
    for key in keys:
        matches = [line for line in lines if line.startswith(f"{key}=")]
        if not matches:
            raise ValueError(f"missing {key}")
        pointer[key] = matches[-1].split("=", 1)[1]
    return pointer


def read_v19_status_pointer(
    current_status: Path,
    v19_audit: Path,
) -> dict[str, str]:
    text = current_status.read_text(encoding="utf-8")
    try:
        section = text.split("## Current V19 Status", 1)[1].split("\n## ", 1)[0]
    except IndexError as exc:
        raise ValueError("Current V19 Status section is missing") from exc
    status_pointer = _latest_pointer(section.splitlines())
    audit_pointer = _latest_pointer(v19_audit.read_text(encoding="utf-8").splitlines())
    if status_pointer != audit_pointer:
        raise ValueError("latest v19 status pointer does not match v19 audit EOF")
    return audit_pointer


def read_v20_status_pointer(
    current_status: Path,
    v20_audit: Path,
) -> dict[str, str]:
    text = current_status.read_text(encoding="utf-8")
    try:
        section = text.split("## Current V20 Status", 1)[1].split("\n## ", 1)[0]
    except IndexError as exc:
        raise ValueError("Current V20 Status section is missing") from exc
    status_pointer = _latest_pointer(section.splitlines(), V20_POINTER_KEYS)
    audit_pointer = _latest_pointer(
        v20_audit.read_text(encoding="utf-8").splitlines(), V20_POINTER_KEYS
    )
    if status_pointer != audit_pointer:
        raise ValueError("latest v20 status pointer does not match v20 audit EOF")
    return audit_pointer
