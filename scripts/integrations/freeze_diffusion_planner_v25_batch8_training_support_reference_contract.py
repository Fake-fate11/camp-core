"""Seal the outcome-independent V25 batch8 training-support reference contract."""

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
from camp_core.integrations.diffusion_planner_v25_batch8_training_support_reference import (  # noqa: E402
    EXACT_DIR_KEYS,
    FIXED_DP_HEAD,
    HIGH_AUTHORITY_SHA256,
    contract_payload,
    validate_contract,
)


SOURCE_PATHS = {
    "producer": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_batch8_training_support_reference.py"
    ),
    "reviewer": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_batch8_training_support_reference_review.py"
    ),
    "freeze": (
        "scripts/integrations/"
        "freeze_diffusion_planner_v25_batch8_training_support_reference_contract.py"
    ),
    "review_script": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_batch8_training_support_reference_contract.py"
    ),
    "preflight": (
        "scripts/integrations/"
        "materialize_diffusion_planner_v25_batch8_training_support_reference_preflight.py"
    ),
    "preflight_review": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_batch8_training_support_reference_preflight.py"
    ),
    "raw": (
        "scripts/integrations/"
        "materialize_diffusion_planner_v25_batch8_training_support_reference.py"
    ),
    "raw_review": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_batch8_training_support_reference.py"
    ),
    "tests": (
        "camp_core/tests/"
        "test_diffusion_planner_v25_batch8_training_support_reference.py"
    ),
}


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def freeze(
    *,
    output: Path,
    fixed_dp_repo: Path,
    implementation_head: str,
    pointer_head_at_authority: str,
    exact_dirs: dict[str, str],
) -> str:
    if (
        output.exists()
        or _git(ROOT, "rev-parse", "HEAD") != implementation_head
        or _git(ROOT, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(
            fixed_dp_repo, "status", "--porcelain=v1", "--untracked-files=no"
        )
    ):
        raise RuntimeError("contract tracked authority drifted")
    source_sha = {
        key: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for key, path in SOURCE_PATHS.items()
    }
    contract = validate_contract(
        contract_payload(
            implementation_head=implementation_head,
            pointer_head_at_authority=pointer_head_at_authority,
            exact_dirs=exact_dirs,
            source_sha256=source_sha,
        )
    )
    report = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_reference_contract_artifact_v1"
        ),
        "status": "sealed_outcome_independent_contract",
        "contract": contract,
        "source_paths": SOURCE_PATHS,
        "fixed_dp_head": FIXED_DP_HEAD,
        "tracked_authority_clean": True,
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "model_pool_selector_call_count": 0,
        "outcome_read": False,
        "old_artifact_or_cas_write_count": 0,
    }
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "contract.json").write_bytes(_bytes(contract))
        (staging / "report.json").write_bytes(_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _bytes(
                {
                    "implementation_head": implementation_head,
                    "pointer_head_at_authority": pointer_head_at_authority,
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(
            staging, label="V25 batch8 training-support reference contract"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 batch8 training-support reference contract",
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--pointer-head-at-authority", required=True)
    for key in EXACT_DIR_KEYS:
        parser.add_argument(f"--{key.replace('_', '-')}", required=True)
    args = parser.parse_args()
    print(
        freeze(
            output=args.output,
            fixed_dp_repo=args.fixed_dp_repo,
            implementation_head=args.implementation_head,
            pointer_head_at_authority=args.pointer_head_at_authority,
            exact_dirs={key: getattr(args, key) for key in EXACT_DIR_KEYS},
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
