"""Seal the outcome-independent single-invocation batch8 diagnostic contract."""

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
from camp_core.integrations.diffusion_planner_v25_batch8_first_state_diagnostic import (  # noqa: E402
    EXACT_DIR_KEYS,
    FIXED_DP_HEAD,
    SOURCE_KEYS,
    canonical_bytes,
    diagnostic_contract,
    validate_contract,
)


SOURCE_PATHS = {
    "producer": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_batch8_first_state_diagnostic.py"
    ),
    "reviewer": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_batch8_first_state_diagnostic_review.py"
    ),
    "freeze_script": (
        "scripts/integrations/"
        "freeze_diffusion_planner_v25_batch8_first_state_diagnostic_contract.py"
    ),
    "contract_review_script": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_batch8_first_state_diagnostic_contract.py"
    ),
    "preflight_script": (
        "scripts/integrations/"
        "materialize_diffusion_planner_v25_batch8_first_state_preflight.py"
    ),
    "preflight_review_script": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_batch8_first_state_preflight.py"
    ),
    "diagnostic_script": (
        "scripts/integrations/"
        "materialize_diffusion_planner_v25_batch8_first_state_diagnostic.py"
    ),
    "diagnostic_review_script": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_batch8_first_state_diagnostic.py"
    ),
    "tests": (
        "camp_core/tests/"
        "test_diffusion_planner_v25_batch8_first_state_diagnostic.py"
    ),
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _atomic(output: Path, files: dict[str, bytes], label: str) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        for name, payload in files.items():
            (staging / name).write_bytes(payload)
        root = seal_artifact(staging, label=label)
        os.replace(staging, output)
        verify_complete_seal(output, root, label=label)
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def freeze(
    *,
    output: Path,
    fixed_dp_repo: Path,
    exact_dirs: dict[str, str],
) -> str:
    implementation_head = _git(ROOT, "rev-parse", "HEAD")
    if (
        _git(ROOT, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(
            fixed_dp_repo,
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
        )
    ):
        raise RuntimeError("tracked authority drifted")
    if set(SOURCE_PATHS) != set(SOURCE_KEYS):
        raise RuntimeError("source keyset drifted")
    source_sha = {
        key: hashlib.sha256((ROOT / value).read_bytes()).hexdigest()
        for key, value in SOURCE_PATHS.items()
    }
    contract = validate_contract(
        diagnostic_contract(
            implementation_head=implementation_head,
            exact_dirs=exact_dirs,
            source_sha256=source_sha,
        )
    )
    report = {
        "schema_version": (
            "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_"
            "contract_artifact_v1"
        ),
        "status": "sealed_outcome_independent_diagnostic_contract",
        "contract_sha256": contract["contract_sha256"],
        "source_paths": SOURCE_PATHS,
        "model_pool_selector_call_count": 0,
        "outcome_read": False,
        "old_artifact_cas_write_count": 0,
    }
    return _atomic(
        output,
        {
            "contract.json": canonical_bytes(contract),
            "report.json": canonical_bytes(report),
            "HEADS.json": canonical_bytes(
                {
                    "implementation_head": implementation_head,
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "tracked_clean": True,
                }
            ),
            "COMMAND": (" ".join(sys.argv) + "\n").encode("utf-8"),
            "run.exit": b"0\n",
        },
        "V25 batch8 first-state diagnostic contract",
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
