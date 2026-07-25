#!/usr/bin/env python3
"""Independently review the V25 fair-pool calibration hard-stop closeout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path("/root/autodl-tmp")
CAMP = ROOT / "camp_core"
DP = ROOT / "Diffusion-Planner"
STAGE_ID = "67308ac0_ed0d298c"
SOURCE = ROOT / (
    "camp_dp_v25_fair_pool_adaptation_calibration_hard_stop_"
    f"{STAGE_ID}"
)
EXPECTED_OUTPUT = ROOT / (
    "camp_dp_v25_fair_pool_adaptation_calibration_hard_stop_review_"
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


def _install() -> None:
    path = CAMP / "camp_core"
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
    path = Path(f"/proc/{pid}/cmdline")
    return path.is_file() and b"calibration_raw_67308ac0_ed0d298c.py" in path.read_bytes()


def review(output: Path, source_root: str) -> str:
    _install()
    from camp_core.integrations.diffusion_planner_artifact_seal import (
        seal_artifact,
        verify_complete_seal,
    )
    from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_hard_stop_review import (
        literal_review_calibration_hard_stop,
    )

    if output != EXPECTED_OUTPUT or output.exists():
        raise ValueError("calibration hard-stop review exact output drifted")
    verify_complete_seal(SOURCE, source_root, label="calibration hard stop")
    verify_complete_seal(AUTHORITY, AUTHORITY_ROOT, label="calibration authority")
    verify_complete_seal(PREFLIGHT, PREFLIGHT_ROOT, label="calibration preflight")
    verify_complete_seal(
        PREFLIGHT_REVIEW,
        PREFLIGHT_REVIEW_ROOT,
        label="calibration preflight independent review",
    )
    reporting_head = _git(CAMP, "rev-parse", "HEAD")
    if (
        _git(CAMP, "rev-parse", "refs/remotes/origin/main") != reporting_head
        or _git(CAMP, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(DP, "rev-parse", "HEAD")
        != "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        or _git(DP, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("calibration hard-stop review live authority drifted")
    closeout = json.loads((SOURCE / "closeout.json").read_text("ascii"))
    lines = PRODUCER.read_text("utf-8").splitlines()
    predicate = "\n".join(lines[508:514]) + "\n"
    observed_absence = {
        "raw_artifact_absent": not RAW.exists(),
        "raw_review_artifact_absent": not RAW_REVIEW.exists(),
        "threshold_freeze_artifact_absent": not THRESHOLD.exists(),
        "threshold_freeze_review_artifact_absent": not THRESHOLD_REVIEW.exists(),
    }
    pid_path = Path(str(CONTROL) + ".pid")
    pid = int(pid_path.read_text("ascii").strip())
    report = literal_review_calibration_hard_stop(
        closeout,
        observed_source_predicate_sha256=hashlib.sha256(
            predicate.encode("utf-8")
        ).hexdigest(),
        observed_file_sha256={
            "producer": _sha(PRODUCER),
            "run_script": _sha(RUN_SCRIPT),
            "stdout": _sha(Path(str(CONTROL) + ".stdout")),
            "stderr": _sha(Path(str(CONTROL) + ".stderr")),
            "exit": _sha(Path(str(CONTROL) + ".exit")),
            "pid": _sha(pid_path),
        },
        observed_absence=observed_absence,
        process_running=_process_running(pid),
        observed_reporting_head=reporting_head,
    )
    report.update(
        {
            "source_artifact_root_sha256": source_root,
            "authority_root_sha256": AUTHORITY_ROOT,
            "preflight_root_sha256": PREFLIGHT_ROOT,
            "preflight_review_root_sha256": PREFLIGHT_REVIEW_ROOT,
            "reporting_head": reporting_head,
            "fixed_dp_head": (
                "7a1d33da277a1992ec474b5383a0c963c72e04e4"
            ),
            "camp_tracked_clean": True,
            "fixed_dp_tracked_clean": True,
        }
    )
    output.mkdir(parents=False)
    (output / "report.json").write_bytes(_canonical(report))
    (output / "HEADS.json").write_bytes(
        _canonical(
            {
                "reporting_head": reporting_head,
                "fixed_dp_head": report["fixed_dp_head"],
                "camp_tracked_clean": True,
                "fixed_dp_tracked_clean": True,
            }
        )
    )
    (output / "COMMAND").write_text(
        "python review_diffusion_planner_v25_fair_pool_calibration_hard_stop.py "
        f"--source-root {source_root} --output-dir {output}\n",
        encoding="ascii",
    )
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(
        output, label="independent V25 fair-pool calibration hard-stop review"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            {"root_sha256": review(args.output_dir, args.source_root)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
