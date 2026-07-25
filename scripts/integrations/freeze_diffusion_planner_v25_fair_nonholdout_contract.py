"""Seal the outcome-independent V25 fair nonholdout validation contract."""

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
from camp_core.integrations.diffusion_planner_v25_fair_nonholdout import (  # noqa: E402
    FIXED_DP_HEAD,
    canonical_bytes,
    fair_nonholdout_contract,
    validate_fair_nonholdout_contract,
)


def freeze(*, output: Path, fixed_dp_repo: Path) -> str:
    fixed_dp_repo = fixed_dp_repo.resolve()
    if (
        _git_head(fixed_dp_repo) != FIXED_DP_HEAD
        or _tracked_changes(fixed_dp_repo)
    ):
        raise ValueError("fixed DP authority drifted before fair contract freeze")
    contract = validate_fair_nonholdout_contract(fair_nonholdout_contract())
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        report = {
            "schema_version": "camp_dp_v25_fair_nonholdout_contract_artifact_v1",
            "status": "sealed_outcome_independent_fair_nonholdout_contract",
            "contract": contract,
            "implementation_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "fresh_or_b4_raw_outcome_read": False,
            "model_loaded_or_forward_called": False,
            "selector_replay_or_closed_loop_started": False,
            "training_executed": False,
            "claim_authorized": False,
        }
        (staging / "report.json").write_bytes(canonical_bytes(report))
        (staging / "contract.json").write_bytes(canonical_bytes(contract))
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "implementation_head": report["implementation_head"],
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="V25 fair nonholdout contract")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 fair nonholdout contract")
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _tracked_changes(repo: Path) -> bool:
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
