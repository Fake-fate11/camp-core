#!/usr/bin/env python3
"""Run and seal the single B4 production-RC focused test batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _git_head,
    _tracked_dirty,
)


TEST_FILES = (
    "camp_core/tests/test_diffusion_planner_v25_actual_native_receipt_contract.py",
    "camp_core/tests/test_diffusion_planner_v25_b4_preopen.py",
    "camp_core/tests/test_diffusion_planner_v25_evaluation.py",
    "camp_core/tests/test_diffusion_planner_v25_holdout_contract.py",
    "camp_core/tests/test_diffusion_planner_v25_holdout_preimages.py",
    "camp_core/tests/test_diffusion_planner_v25_holdout_opening.py",
    "camp_core/tests/test_diffusion_planner_v25_holdout_state.py",
    "camp_core/tests/test_diffusion_planner_v25_production_equivalence.py",
    "camp_core/tests/test_diffusion_planner_v25_role_provenance.py",
    (
        "camp_core/tests/"
        "test_diffusion_planner_v25_production_equivalence_fixture.py"
    ),
    "camp_core/tests/test_diffusion_planner_v25_signal_complete_execution.py",
    "camp_core/tests/test_diffusion_planner_v25_signal_complete_maps.py",
    "camp_core/tests/test_diffusion_planner_v25_signal_complete_plan.py",
    "camp_core/tests/test_diffusion_planner_v25_signal_complete_runtime.py",
    "camp_core/tests/test_diffusion_planner_v25_split.py",
)


def run(
    *,
    expected_head: str,
    output_dir: Path,
    sealed_actual_native_fixture_artifact: Path | None = None,
    sealed_actual_native_fixture_root_sha256: str | None = None,
) -> str:
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    if _tracked_dirty(ROOT) or _git_head(ROOT) != expected_head:
        raise ValueError("B4 production-RC focused test HEAD/clean drifted")
    command = [sys.executable, "-m", "pytest", "-q", *TEST_FILES]
    env = dict(os.environ)
    python_path = str(PACKAGE_ROOT)
    if env.get("PYTHONPATH"):
        python_path = python_path + os.pathsep + env["PYTHONPATH"]
    env["PYTHONPATH"] = python_path
    if (sealed_actual_native_fixture_artifact is None) is not (
        sealed_actual_native_fixture_root_sha256 is None
    ):
        raise ValueError(
            "sealed actual-native fixture path/root must be supplied together"
        )
    if sealed_actual_native_fixture_artifact is not None:
        env["CAMP_V25_SEALED_ACTUAL_NATIVE_FIXTURE_ARTIFACT"] = str(
            Path(sealed_actual_native_fixture_artifact).resolve()
        )
        env["CAMP_V25_SEALED_ACTUAL_NATIVE_FIXTURE_ROOT_SHA256"] = str(
            sealed_actual_native_fixture_root_sha256
        )
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=False,
        check=False,
        env=env,
    )
    output.mkdir(parents=True)
    (output / "stdout").write_bytes(completed.stdout)
    (output / "stderr").write_bytes(completed.stderr)
    report = {
        "schema_version": (
            "camp_dp_v25_b4_production_rc_focused_test_receipt_v1"
        ),
        "status": (
            "passed_b4_production_rc_focused_suite"
            if completed.returncode == 0
            else "failed_b4_production_rc_focused_suite"
        ),
        "implementation_head": expected_head,
        "python_executable": str(Path(sys.executable).resolve()),
        "test_files": list(TEST_FILES),
        "test_file_sha256": {
            relative: _sha256(ROOT / relative) for relative in TEST_FILES
        },
        "pytest_exit_code": completed.returncode,
        "serial_execution": True,
        "sealed_actual_native_fixture_artifact": (
            str(Path(sealed_actual_native_fixture_artifact).resolve())
            if sealed_actual_native_fixture_artifact is not None
            else None
        ),
        "sealed_actual_native_fixture_root_sha256": (
            sealed_actual_native_fixture_root_sha256
        ),
        "fresh_rows_or_outcomes_used": False,
    }
    _write(output / "report.json", report)
    (output / "HEADS").write_bytes(
        (
            f"camp_head={expected_head}\n"
            "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes(
        (" ".join(sys.argv) + "\n").encode("utf-8")
    )
    (output / "run.exit").write_bytes(
        b"0\n" if completed.returncode == 0 else b"1\n"
    )
    root = seal_artifact(
        output, label="V25 B4 production-RC focused test receipt"
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"B4 production-RC focused suite failed; sealed root={root}"
        )
    return root


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--sealed-actual-native-fixture-artifact",
        type=Path,
    )
    parser.add_argument(
        "--sealed-actual-native-fixture-root-sha256",
    )
    return parser.parse_args()


def main() -> int:
    root = run(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
