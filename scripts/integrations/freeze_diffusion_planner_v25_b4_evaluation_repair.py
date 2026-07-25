#!/usr/bin/env python3
"""Freeze an additive pre-artifact Fresh B4 evaluation consumer repair."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact, verify_complete_seal  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_continuation import load_continuation_ledger  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_policy_correction import (  # noqa: E402
    correction_implementation_manifest,
    validate_correction_authority,
    validate_correction_authority_review,
)
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_repair import (  # noqa: E402
    ALLOWED_CHANGED_PATHS,
    ERROR,
    file_sha256,
    freeze_repair,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import _strict_canonical_json, canonical_json_bytes  # noqa: E402


def freeze(
    *,
    authority_artifact: Path,
    authority_root_sha256: str,
    authority_review_artifact: Path,
    authority_review_root_sha256: str,
    continuation_ledger: Path,
    failed_evaluation_control: Path,
    focused_tests_artifact: Path,
    focused_tests_root_sha256: str,
    output_dir: Path,
) -> str:
    authority_path = Path(authority_artifact).resolve()
    review_path = Path(authority_review_artifact).resolve()
    focused_path = Path(focused_tests_artifact).resolve()
    output = Path(output_dir).resolve()
    head = _git_head()
    expected = Path(
        "/root/autodl-tmp/"
        f"camp_dp_v25_fresh_b4_evaluation_policy_correction_repair_{head[:8]}_8680c1b19ce0620b"
    )
    if output != expected or output.exists() or _tracked_changes():
        raise ValueError("Fresh B4 evaluation repair repository/output drifted")
    for label, path, root in (
        ("correction authority", authority_path, authority_root_sha256),
        ("correction authority review", review_path, authority_review_root_sha256),
        ("repair focused tests", focused_path, focused_tests_root_sha256),
    ):
        verify_complete_seal(path, root, label=label)
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"{label} did not pass")
    authority = validate_correction_authority(_object(authority_path / "authority.json"))
    authority_review = validate_correction_authority_review(_object(review_path / "report.json"))
    if authority_review["reviewed_authority"] != {
        "path": str(authority_path),
        "root_sha256": authority_root_sha256,
    }:
        raise ValueError("Fresh B4 repair authority review binding drifted")
    continuation_path = Path(continuation_ledger).resolve()
    continuation = load_continuation_ledger(continuation_path)
    if (
        continuation["state"] != "evaluation_started"
        or continuation["correction_authority_root_sha256"] != authority_root_sha256
        or continuation["correction_authority_review_root_sha256"]
        != authority_review_root_sha256
        or continuation["evaluation_root_sha256"] is not None
        or Path(authority["corrected_evaluation_output_dir"]).exists()
        or Path(authority["corrected_evaluation_review_output_dir"]).exists()
    ):
        raise ValueError("Fresh B4 repair pre-artifact continuation drifted")
    control = Path(failed_evaluation_control).resolve()
    stderr = control / "stderr.log"
    run_script = control / "run.sh"
    run_receipt = control / "run.sha256"
    run_exit = control / "run.exit"
    if (
        run_exit.read_bytes() != b"1\n"
        or ERROR not in stderr.read_text(encoding="utf-8")
        or run_receipt.read_bytes()
        != f"{file_sha256(run_script)}  {run_script}\n".encode("utf-8")
    ):
        raise ValueError("Fresh B4 repair failed-control evidence drifted")
    old_head = authority["correction_implementation"]["head"]
    changed = tuple(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-only", old_head, head, "--"],
            text=True,
        ).splitlines()
    )
    if changed != ALLOWED_CHANGED_PATHS:
        raise ValueError("Fresh B4 repair implementation diff drifted")
    manifest = correction_implementation_manifest(ROOT)
    payload = freeze_repair(
        original_correction_authority={"path": str(authority_path), "root_sha256": authority_root_sha256},
        original_correction_authority_review={"path": str(review_path), "root_sha256": authority_review_root_sha256},
        continuation_ledger={"path": str(continuation_path), "sha256": file_sha256(continuation_path)},
        failed_evaluation_control={
            "directory": str(control),
            "run_exit": 1,
            "stderr": {"path": str(stderr), "sha256": file_sha256(stderr)},
            "run_script": {"path": str(run_script), "sha256": file_sha256(run_script)},
            "run_receipt": {"path": str(run_receipt), "sha256": file_sha256(run_receipt)},
        },
        old_correction_head=old_head,
        old_correction_manifest_sha256=authority["correction_implementation"]["manifest_sha256"],
        new_correction_head=head,
        new_correction_manifest_sha256=manifest["manifest_sha256"],
        focused_tests={"path": str(focused_path), "root_sha256": focused_tests_root_sha256},
        changed_paths=list(changed),
        corrected_evaluation_output_dir=authority["corrected_evaluation_output_dir"],
        corrected_evaluation_review_output_dir=authority["corrected_evaluation_review_output_dir"],
    )
    return _write_atomic(output, payload)


def _write_atomic(output: Path, payload: dict[str, Any]) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "repair.json").write_bytes(canonical_json_bytes(payload))
        (staging / "HEADS").write_bytes(
            (
                f"old_correction_head={payload['old_correction_head']}\n"
                f"new_correction_head={payload['new_correction_head']}\n"
            ).encode("ascii")
        )
        (staging / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="Fresh B4 pre-artifact evaluation repair")
        os.rename(staging, output)
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _object(path: Path) -> dict[str, Any]:
    value = _strict_canonical_json(path)
    if type(value) is not dict:
        raise ValueError(f"Fresh B4 repair JSON object drifted: {path}")
    return value


def _git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def _tracked_changes() -> bool:
    return bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], text=True).strip())


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority-artifact", type=Path, required=True)
    parser.add_argument("--authority-root-sha256", required=True)
    parser.add_argument("--authority-review-artifact", type=Path, required=True)
    parser.add_argument("--authority-review-root-sha256", required=True)
    parser.add_argument("--continuation-ledger", type=Path, required=True)
    parser.add_argument("--failed-evaluation-control", type=Path, required=True)
    parser.add_argument("--focused-tests-artifact", type=Path, required=True)
    parser.add_argument("--focused-tests-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = freeze(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
