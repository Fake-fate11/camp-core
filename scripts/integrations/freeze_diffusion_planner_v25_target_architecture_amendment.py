"""Seal the outcome-independent V25 target-architecture amendment."""

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
from camp_core.integrations.diffusion_planner_v25_target_architecture import (  # noqa: E402
    target_architecture_amendment,
    validate_target_architecture_amendment,
)


ARTIFACT_SCHEMA = "camp_dp_v25_target_architecture_amendment_artifact_v1"
ARTIFACT_STATUS = "sealed_outcome_independent_target_architecture_amendment"
IMPLEMENTATION_PATHS = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_target_architecture.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_target_architecture_review.py",
    "scripts/integrations/freeze_diffusion_planner_v25_target_architecture_amendment.py",
    "scripts/integrations/review_diffusion_planner_v25_target_architecture_amendment.py",
    "scripts/integrations/qualify_diffusion_planner_v25_same_ego_k8.py",
    "scripts/integrations/review_diffusion_planner_v25_same_ego_k8.py",
)


def freeze(*, output: Path, fixed_dp_repo: Path) -> str:
    if _git_head(fixed_dp_repo) != (
        "7a1d33da277a1992ec474b5383a0c963c72e04e4"
    ):
        raise ValueError("fixed DP HEAD drifted")
    if _tracked_changes(fixed_dp_repo):
        raise ValueError("fixed DP tracked worktree is dirty")
    amendment = validate_target_architecture_amendment(
        target_architecture_amendment()
    )
    report = {
        "schema_version": ARTIFACT_SCHEMA,
        "status": ARTIFACT_STATUS,
        "outcome_values_read": False,
        "fresh_or_closed_loop_executed": False,
        "training_executed": False,
        "sealed_artifacts_or_cas_written": False,
        "implementation": _implementation_manifest(),
        "fixed_dp": {
            "path": str(fixed_dp_repo.resolve()),
            "head": _git_head(fixed_dp_repo),
            "tracked_clean": True,
        },
        "amendment": amendment,
    }
    return _write_atomic(output, report)


def _implementation_manifest() -> dict[str, Any]:
    rows = [
        {"path": path, "sha256": _file_sha256(ROOT / path)}
        for path in IMPLEMENTATION_PATHS
    ]
    return {
        "head": _git_head(ROOT),
        "tracked_clean": not _tracked_changes(ROOT),
        "paths": rows,
        "manifest_sha256": hashlib.sha256(_canonical_bytes(rows)).hexdigest(),
    }


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "role": "target_architecture_amendment",
                    "implementation_head": report["implementation"]["head"],
                    "fixed_dp_head": report["fixed_dp"]["head"],
                }
            )
        )
        root = seal_artifact(staging, label="V25 target architecture amendment")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 target architecture amendment"
        )
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    print(freeze(output=args.output, fixed_dp_repo=args.fixed_dp_repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
