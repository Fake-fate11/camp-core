"""Seal the outcome-independent V25 batch8-only calibration contract."""

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
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_batch8_calibration_contract import (  # noqa: E402
    ARTIFACT_SCHEMA,
    EXACT_DIR_KEYS,
    contract_design,
    validate_contract_design,
)


SOURCE_PATHS = {
    "producer": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_batch8_calibration_contract.py"
    ),
    "reviewer": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_batch8_calibration_contract_review.py"
    ),
    "freeze_script": (
        "scripts/integrations/"
        "freeze_diffusion_planner_v25_batch8_calibration_contract.py"
    ),
    "review_script": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_batch8_calibration_contract.py"
    ),
    "tests": (
        "camp_core/tests/"
        "test_diffusion_planner_v25_batch8_calibration_contract.py"
    ),
}


def freeze(*, output: Path, fixed_dp_repo: Path, exact_dirs: dict[str, str]) -> str:
    head = _git_head(ROOT)
    if _git_head(fixed_dp_repo) != (
        "7a1d33da277a1992ec474b5383a0c963c72e04e4"
    ):
        raise ValueError("fixed DP HEAD drifted")
    if _dirty(ROOT) or _dirty(fixed_dp_repo):
        raise ValueError("tracked authority is dirty")
    source_sha = {
        key: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for key, path in SOURCE_PATHS.items()
    }
    contract = validate_contract_design(
        contract_design(
            implementation_head=head,
            exact_dirs=exact_dirs,
            source_sha256=source_sha,
        )
    )
    report = {
        "schema_version": ARTIFACT_SCHEMA,
        "status": "sealed_outcome_independent_batch8_calibration_contract",
        "contract": contract,
        "fixed_dp": {
            "head": _git_head(fixed_dp_repo),
            "tracked_clean": True,
        },
        "source_paths": SOURCE_PATHS,
        "outcome_values_read": False,
        "new_model_pool_selector_call_count": 0,
        "actual_calibration_acquisition_count": 0,
        "threshold_materialization_count": 0,
        "old_artifact_or_cas_write_count": 0,
    }
    return _atomic(output, report, "V25 batch8 calibration contract")


def _atomic(output: Path, report: dict[str, Any], label: str) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _bytes(
                {
                    "role": "batch8_calibration_contract",
                    "implementation_head": report["contract"]["implementation"][
                        "head"
                    ],
                    "fixed_dp_head": report["fixed_dp"]["head"],
                }
            )
        )
        root = seal_artifact(staging, label=label)
        os.replace(staging, output)
        verify_complete_seal(output, root, label=label)
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _dirty(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=repo,
            text=True,
        ).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    for key in EXACT_DIR_KEYS:
        parser.add_argument(f"--{key.replace('_', '-')}", required=True)
    args = parser.parse_args()
    exact_dirs = {key: getattr(args, key) for key in EXACT_DIR_KEYS}
    print(
        freeze(
            output=args.output,
            fixed_dp_repo=args.fixed_dp_repo,
            exact_dirs=exact_dirs,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
