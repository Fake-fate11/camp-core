"""Seal the outcome-independent fair-pool adaptation contract v3."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v3 import (  # noqa: E402
    FIXED_DP_HEAD,
    adaptation_contract_v3,
    validate_contract_v3,
)


def _canonical(value: object) -> bytes:
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


def freeze(*, output: Path, fixed_dp_repo: Path) -> str:
    if _git_head(fixed_dp_repo) != FIXED_DP_HEAD or _tracked(fixed_dp_repo):
        raise ValueError("fixed DP authority drifted")
    contract = validate_contract_v3(adaptation_contract_v3())
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        report = {
            "schema_version": (
                "camp_dp_v25_fair_pool_adaptation_contract_artifact_v3"
            ),
            "status": (
                "sealed_executable_design_only_acquisition_unauthorized"
            ),
            "contract": contract,
            "implementation_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "superseded_v2_contract_root_sha256": (
                "f2314088f25c601ae80fa022dd0b4a513c29d07a54b7008c17be6644c078e9e1"
            ),
            "superseded_v2_review_root_sha256": (
                "ca0bd63c057f0e58dc88d278c4f45b713f93b408b22ab33c122dfa4567ecab6b"
            ),
            "acquisition_authorized": False,
            "actual_input_manifest_materialization_count": 0,
            "calibration_run_count": 0,
            "repeat_model_run_count": 0,
            "pool_run_count": 0,
            "selector_run_count": 0,
            "closed_loop_run_count": 0,
            "fresh_run_count": 0,
            "holdout_run_count": 0,
            "training_run_count": 0,
            "fresh_or_b4_outcome_read": False,
            "old_artifact_or_cas_written": False,
            "claim_authorized": False,
        }
        (staging / "report.json").write_bytes(_canonical(report))
        (staging / "contract.json").write_bytes(_canonical(contract))
        (staging / "HEADS.json").write_bytes(
            _canonical(
                {
                    "implementation_head": report["implementation_head"],
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging,
            label="V25 fair-pool adaptation contract v3",
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 fair-pool adaptation contract v3",
        )
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
    ).strip()


def _tracked(repo: Path) -> bool:
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
    args = parser.parse_args()
    print(freeze(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
