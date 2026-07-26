"""Seal the zero-model V25 selector-after-pool replay contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os
import shutil


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_selector_after_pool_replay import (  # noqa: E402
    EXACT_DIRS,
    assert_python_runtime,
    canonical_bytes,
    contract,
    sha256_file,
    validate_contract,
)


SOURCE_PATHS = {
    "contract_module": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_selector_after_pool_replay.py"
    ),
    "contract_reviewer": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_selector_after_pool_replay_review.py"
    ),
    "contract_freezer": (
        "scripts/integrations/"
        "freeze_diffusion_planner_v25_selector_after_pool_replay_contract.py"
    ),
    "contract_review_runner": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_selector_after_pool_replay_contract.py"
    ),
    "preflight_producer": (
        "scripts/integrations/"
        "materialize_diffusion_planner_v25_selector_after_pool_replay_preflight.py"
    ),
    "preflight_reviewer": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_selector_after_pool_replay_preflight.py"
    ),
    "replay_producer": (
        "scripts/integrations/"
        "materialize_diffusion_planner_v25_selector_after_pool_replay.py"
    ),
    "replay_reviewer": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_selector_after_pool_replay.py"
    ),
}


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True
    ).strip()


def freeze(*, implementation_head: str, output: Path) -> str:
    assert_python_runtime(
        executable=sys.executable,
        version_info=sys.version_info[:3],
        prefix=sys.prefix,
        expected_executable="/root/autodl-tmp/dp312_venv/bin/python",
        expected_prefix="/root/autodl-tmp/dp312_venv",
        expected_exact_version=(3, 12, 3),
    )
    if (
        output != Path(EXACT_DIRS["contract"])
        or output.exists()
        or _git("rev-parse", "HEAD") != implementation_head
        or _git("rev-parse", "refs/remotes/origin/main") != implementation_head
        or _git("status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("selector replay contract live authority drifted")
    source_hashes = {}
    for name, relative in SOURCE_PATHS.items():
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        source_hashes[name] = sha256_file(path)
    payload = validate_contract(
        contract(
            implementation_head=implementation_head,
            source_hashes=source_hashes,
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        (staging / "contract.json").write_bytes(canonical_bytes(payload))
        report = {
            "schema_version": (
                "camp_dp_v25_selector_after_pool_replay_contract_report_v1"
            ),
            "status": "PASS_contract_frozen_before_selector_replay",
            "implementation_head": implementation_head,
            "contract_payload_sha256": payload["contract_payload_sha256"],
            "model_dp_latent_candidate_generation_call_count": 0,
            "selector_call_count": 0,
            "fresh_or_holdout_outcome_read": False,
            "old_artifact_or_cas_write": False,
            "python": {
                "executable": sys.executable,
                "version": list(sys.version_info[:3]),
                "prefix": sys.prefix,
            },
        }
        (staging / "report.json").write_bytes(canonical_bytes(report))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="V25 selector-after-pool replay contract")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 selector-after-pool replay contract"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument(
        "--output", type=Path, default=Path(EXACT_DIRS["contract"])
    )
    args = parser.parse_args()
    print(freeze(implementation_head=args.implementation_head, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
