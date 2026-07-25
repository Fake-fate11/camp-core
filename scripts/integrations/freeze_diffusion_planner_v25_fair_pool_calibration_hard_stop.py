#!/usr/bin/env python3
"""Seal the outcome-blind V25 fair-pool calibration hard-stop closeout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path("/root/autodl-tmp")
CAMP = ROOT / "camp_core"
DP = ROOT / "Diffusion-Planner"
STAGE_ID = "67308ac0_ed0d298c"
EXPECTED_OUTPUT = ROOT / (
    "camp_dp_v25_fair_pool_adaptation_calibration_hard_stop_"
    f"{STAGE_ID}"
)
AUTHORITY = ROOT / f"camp_dp_v25_fair_pool_calibration_authority_{STAGE_ID}"
PREFLIGHT = ROOT / f"camp_dp_v25_fair_pool_calibration_preflight_{STAGE_ID}"
PREFLIGHT_REVIEW = ROOT / (
    f"camp_dp_v25_fair_pool_calibration_preflight_review_{STAGE_ID}"
)
RAW = ROOT / f"camp_dp_v25_fair_pool_calibration_raw_{STAGE_ID}"
RAW_REVIEW = ROOT / f"camp_dp_v25_fair_pool_calibration_raw_review_{STAGE_ID}"
THRESHOLD = ROOT / (
    f"camp_dp_v25_fair_pool_calibration_threshold_freeze_{STAGE_ID}"
)
THRESHOLD_REVIEW = ROOT / (
    f"camp_dp_v25_fair_pool_calibration_threshold_freeze_review_{STAGE_ID}"
)
CONTROL = ROOT / (
    ".camp_dp_v25_calibration_raw_67308ac0_ed0d298c_from_sealed_preflight"
)
PRODUCER = ROOT / ".camp_dp_v25_calibration_raw_67308ac0_ed0d298c.py"
RUN_SCRIPT = ROOT / (
    ".camp_dp_v25_calibration_run_raw_67308ac0_ed0d298c_from_sealed_preflight.sh"
)
AUTHORITY_ROOT = "bd6fee62418d062266e8f922d2f2dd3672ced115f9c1065e922db4b207054820"
PREFLIGHT_ROOT = "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
PREFLIGHT_REVIEW_ROOT = (
    "ece7c80b6e764598ff867606f225a29a40f8ddededc641e7f22032b4b5d49ef3"
)
EXPECTED_PRODUCER_SHA = (
    "4657750607c80b748c7ee59be96095510ccc73be87a1a4aa77c9f69afff69408"
)


def _install() -> None:
    for path in (CAMP / "camp_core",):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _process_running(pid: int) -> bool:
    cmdline = Path(f"/proc/{pid}/cmdline")
    if not cmdline.is_file():
        return False
    return b"calibration_raw_67308ac0_ed0d298c.py" in cmdline.read_bytes()


def freeze(output: Path) -> str:
    _install()
    from camp_core.integrations.diffusion_planner_artifact_seal import (
        seal_artifact,
        verify_complete_seal,
    )
    from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_hard_stop import (
        freeze_calibration_hard_stop_closeout,
        validate_calibration_hard_stop_closeout,
    )

    if output != EXPECTED_OUTPUT or output.exists():
        raise ValueError("calibration hard-stop exact output drifted")
    reporting_head = _git(CAMP, "rev-parse", "HEAD")
    if (
        _git(CAMP, "rev-parse", "refs/remotes/origin/main") != reporting_head
        or _git(CAMP, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(DP, "rev-parse", "HEAD")
        != "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        or _git(DP, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("calibration hard-stop live authority drifted")
    verify_complete_seal(AUTHORITY, AUTHORITY_ROOT, label="calibration authority")
    verify_complete_seal(PREFLIGHT, PREFLIGHT_ROOT, label="calibration preflight")
    verify_complete_seal(
        PREFLIGHT_REVIEW,
        PREFLIGHT_REVIEW_ROOT,
        label="calibration preflight independent review",
    )
    absence = {
        "raw_artifact_absent": not RAW.exists(),
        "raw_review_artifact_absent": not RAW_REVIEW.exists(),
        "threshold_freeze_artifact_absent": not THRESHOLD.exists(),
        "threshold_freeze_review_artifact_absent": not THRESHOLD_REVIEW.exists(),
    }
    if not all(absence.values()):
        raise RuntimeError("calibration downstream artifact unexpectedly exists")
    producer_lines = PRODUCER.read_text("utf-8").splitlines()
    predicate = "\n".join(producer_lines[508:514]) + "\n"
    if (
        _sha(PRODUCER) != EXPECTED_PRODUCER_SHA
        or "not np.isfinite(candidate).all()" not in predicate
        or "not np.isfinite(neighbor).all()" not in predicate
        or "len(set(row_shas)) != 8" not in predicate
        or "calibration K8 invalid" not in predicate
    ):
        raise RuntimeError("calibration compound predicate source drifted")
    pid = int((Path(str(CONTROL) + ".pid")).read_text("ascii").strip())
    if _process_running(pid):
        raise RuntimeError("calibration producer is still running")
    exit_path = Path(str(CONTROL) + ".exit")
    stdout_path = Path(str(CONTROL) + ".stdout")
    stderr_path = Path(str(CONTROL) + ".stderr")
    pid_path = Path(str(CONTROL) + ".pid")
    if exit_path.read_text("ascii") != "1\n":
        raise RuntimeError("calibration control exit drifted")
    exception = (
        "calibration K8 invalid: "
        "development_calibration:000/sequential_batch1_x8/0"
    )
    if exception not in stderr_path.read_text("utf-8"):
        raise RuntimeError("calibration failure literal missing")
    closeout = freeze_calibration_hard_stop_closeout(
        reporting_head=reporting_head,
        source_predicate={
            "producer_path": str(PRODUCER),
            "producer_sha256": _sha(PRODUCER),
            "predicate_line_start": 509,
            "predicate_line_end": 514,
            "predicate_sha256": hashlib.sha256(
                predicate.encode("utf-8")
            ).hexdigest(),
            "exception_literal": exception,
        },
        control_evidence={
            "run_script_path": str(RUN_SCRIPT),
            "run_script_sha256": _sha(RUN_SCRIPT),
            "stdout_path": str(stdout_path),
            "stdout_sha256": _sha(stdout_path),
            "stderr_path": str(stderr_path),
            "stderr_sha256": _sha(stderr_path),
            "exit_path": str(exit_path),
            "exit_sha256": _sha(exit_path),
            "control_exit": 1,
            "pid_path": str(pid_path),
            "pid_sha256": _sha(pid_path),
            "pid": pid,
            "process_running": False,
        },
        artifact_absence=absence,
        pre_artifact_diagnostics=[
            {
                "classification": "lanelet2_projection_compatibility_fixture",
                "control_exit": 1,
                "raw_artifact_created": False,
                "model_call_count_before_failure": 0,
                "stderr_sha256": (
                    "c06a5f2188f95c6c12f9deb036e4e90161f502660960d0cc673350d30cbbbaa4"
                ),
            },
            {
                "classification": "causal_map_cache_fixture",
                "control_exit": 1,
                "raw_artifact_created": False,
                "model_call_count_before_failure": 0,
                "stderr_sha256": (
                    "b203552516ff05fce0c3a8b9049cb642e835e0cfe1814b8aa6533a5ff6d4b4ce"
                ),
            },
            {
                "classification": (
                    "sealed_model_input_vs_unpinned_scene_history_fixture"
                ),
                "control_exit": 1,
                "raw_artifact_created": False,
                "model_call_count_before_failure": 0,
                "stderr_sha256": (
                    "851254056e48ef78ec366ccad92ca1ea9b941262677d80da07de6ec96ade17db"
                ),
            },
        ],
    )
    validate_calibration_hard_stop_closeout(closeout)
    output.mkdir(parents=False)
    (output / "closeout.json").write_bytes(_canonical(closeout))
    (output / "source_predicate.txt").write_text(predicate, encoding="utf-8")
    (output / "stderr_tail.txt").write_text(
        "\n".join(stderr_path.read_text("utf-8").splitlines()[-14:]) + "\n",
        encoding="utf-8",
    )
    (output / "HEADS.json").write_bytes(
        _canonical(closeout["authority_bindings"])
    )
    (output / "report.json").write_bytes(
        _canonical(
            {
                "schema_version": (
                    "camp_dp_v25_fair_pool_adaptation_calibration_"
                    "hard_stop_report_v1"
                ),
                "status": closeout["status"],
                "classification": closeout["classification"],
                "closeout_content_root_sha256": closeout["root_sha256"],
                "model_call_count": 8,
                "selector_call_count": 0,
                "completed_raw_run_count": 0,
                "planned_raw_run_count": 640,
                "threshold_not_formed": True,
                "validation_execution_count": 0,
                "raw_outcome_inspected": False,
            }
        )
    )
    (output / "COMMAND").write_text(
        "python freeze_diffusion_planner_v25_fair_pool_calibration_hard_stop.py "
        f"--output-dir {output}\n",
        encoding="ascii",
    )
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 fair-pool calibration hard stop")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({"root_sha256": freeze(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
