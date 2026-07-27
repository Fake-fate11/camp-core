from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Sequence

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def artifact_root(path: Path, expected_root: str | None = None) -> str:
    seal = verify_complete_seal(path, expected_root, label="orchestration artifact")
    root = str(seal["root_sha256"])
    receipt = (path / "ROOT_SHA256SUMS").read_bytes()
    if not _SHA256.fullmatch(root) or receipt != (
        f"{root}  SHA256SUMS\n".encode("ascii")
    ):
        raise ValueError("artifact root receipt is not canonical")
    return root


def _validate_command(command: Sequence[str], expected_interpreter: str) -> list[str]:
    value = [str(item) for item in command]
    if (
        not value
        or not Path(value[0]).is_absolute()
        or value[0] != expected_interpreter
        or Path(expected_interpreter).name not in {"python", "python.exe"}
    ):
        raise ValueError("command must use the exact authorized interpreter")
    return value


def _run(
    command: list[str],
    *,
    stdout_path: Path,
    stderr_path: Path,
    cwd: Path,
) -> int:
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            check=False,
        )
    return int(completed.returncode)


def execute_orchestration(
    *,
    output: Path,
    mode: str,
    implementation_head: str,
    authority_sha256: str,
    expected_interpreter: str,
    cwd: Path,
    source_dir: Path | None,
    source_root: str | None,
    producer_command: Sequence[str] | None,
    producer_target_dir: Path | None,
    reviewer_command: Sequence[str],
    reviewer_target_dir: Path,
) -> tuple[str, dict[str, Any]]:
    if mode not in {"producer-and-reviewer", "review-only"}:
        raise ValueError("unknown orchestration mode")
    if not _COMMIT.fullmatch(implementation_head):
        raise ValueError("implementation HEAD must be lowercase 40-hex")
    if not _SHA256.fullmatch(authority_sha256):
        raise ValueError("authority must be lowercase 64-hex")
    output = output.resolve()
    if output.exists():
        raise ValueError("operation output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        producer_started = False
        producer_exit: int | None = None
        producer_root: str | None = None
        verified_source_root: str | None = None
        if mode == "review-only":
            if (
                source_dir is None
                or source_root is None
                or producer_command is not None
                or producer_target_dir is not None
            ):
                raise ValueError("review-only topology drifted")
            if not _SHA256.fullmatch(source_root):
                raise ValueError("review-only source root must be lowercase SHA256")
            verified_source_root = artifact_root(source_dir, source_root)
            (staging / "producer.status.json").write_bytes(
                _canonical_bytes(
                    {
                        "producer_skipped_reuse_sealed": True,
                        "verified_source_root_sha256": verified_source_root,
                    }
                )
            )
        else:
            if (
                producer_command is None
                or producer_target_dir is None
                or source_dir is not None
                or source_root is not None
            ):
                raise ValueError("producer-reviewer topology drifted")
            producer = _validate_command(producer_command, expected_interpreter)
            producer_started = True
            producer_exit = _run(
                producer,
                stdout_path=staging / "producer.stdout",
                stderr_path=staging / "producer.stderr",
                cwd=cwd,
            )
            (staging / "producer.exit").write_text(
                f"{producer_exit}\n", encoding="ascii"
            )
            if producer_exit == 0:
                producer_root = artifact_root(producer_target_dir)
                verified_source_root = producer_root
        reviewer_started = False
        reviewer_exit: int | None = None
        reviewer_root: str | None = None
        if verified_source_root is not None:
            reviewer = _validate_command(reviewer_command, expected_interpreter)
            reviewer = [
                verified_source_root if item == "__SOURCE_ROOT__" else item
                for item in reviewer
            ]
            if "__SOURCE_ROOT__" in reviewer:
                raise ValueError("reviewer source-root placeholder was not resolved")
            reviewer_started = True
            reviewer_exit = _run(
                reviewer,
                stdout_path=staging / "reviewer.stdout",
                stderr_path=staging / "reviewer.stderr",
                cwd=cwd,
            )
            (staging / "reviewer.exit").write_text(
                f"{reviewer_exit}\n", encoding="ascii"
            )
            if reviewer_exit == 0:
                reviewer_root = artifact_root(reviewer_target_dir)
                (staging / "target_root.txt").write_text(
                    f"{reviewer_root}\n", encoding="ascii"
                )
        overall_exit = (
            producer_exit
            if producer_started and producer_exit != 0
            else (reviewer_exit if reviewer_exit is not None else 0)
        )
        if overall_exit is None:
            overall_exit = 0
        result = {
            "schema_version": "camp_dp_v25_machine_stage_orchestration_result_v1",
            "status": "passed" if overall_exit == 0 else "failed",
            "mode": mode,
            "authority_sha256": authority_sha256,
            "implementation_head": implementation_head,
            "producer_skipped_reuse_sealed": mode == "review-only",
            "producer_started": producer_started,
            "producer_exit_code": producer_exit,
            "producer_root_sha256": producer_root,
            "reviewer_started": reviewer_started,
            "reviewer_exit_code": reviewer_exit,
            "reviewer_root_sha256": reviewer_root,
            "overall_exit_code": overall_exit,
            "stdout_root_parsing_used": False,
            "verified_source_root_sha256": verified_source_root,
        }
        (staging / "machine_result.json").write_bytes(_canonical_bytes(result))
        (staging / "operation_receipt.json").write_bytes(
            _canonical_bytes(
                {
                    **result,
                    "expected_interpreter": expected_interpreter,
                    "cwd": str(cwd.resolve()),
                    "producer_command": (
                        None
                        if producer_command is None
                        else [str(item) for item in producer_command]
                    ),
                    "reviewer_command": [str(item) for item in reviewer_command],
                }
            )
        )
        operation_root = seal_artifact(staging, label="machine orchestration")
        os.replace(staging, output)
        verify_complete_seal(
            output, operation_root, label="machine orchestration"
        )
        if reviewer_root is not None:
            root_receipt = (output / "target_root.txt").read_text(
                encoding="ascii"
            )
            if root_receipt != f"{reviewer_root}\n":
                raise ValueError("machine target root receipt drifted")
        return operation_root, result
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


__all__ = ["artifact_root", "execute_orchestration"]
