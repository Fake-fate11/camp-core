"""Independently review the V25 selector-after-pool replay contract."""

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


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_selector_after_pool_replay_review import (  # noqa: E402
    review_contract,
)


CONTRACT_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_selector_after_pool_replay_replacement_contract_v1_"
    "4c412870_e6579ca7"
)
OUTPUT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_selector_after_pool_replay_replacement_contract_review_v1_"
    "4c412870_e6579ca7"
)
FAILURE_CLOSEOUT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_selector_after_pool_replay_failure_closeout_v1_"
    "4c412870_e6579ca7"
)
FAILURE_CLOSEOUT_REVIEW = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_selector_after_pool_replay_failure_closeout_review_v1_"
    "4c412870_e6579ca7"
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
    "failure_closeout_producer": (
        "scripts/integrations/"
        "freeze_diffusion_planner_v25_selector_after_pool_replay_failure_closeout.py"
    ),
    "failure_closeout_reviewer": (
        "scripts/integrations/"
        "review_diffusion_planner_v25_selector_after_pool_replay_failure_closeout.py"
    ),
    "scene_runtime": (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_scene_runtime.py"
    ),
}


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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True
    ).strip()


def review(*, contract_root: str, output: Path = OUTPUT) -> str:
    if (
        sys.executable != "/root/autodl-tmp/dp312_venv/bin/python"
        or sys.version_info[:3] != (3, 12, 3)
        or sys.prefix != "/root/autodl-tmp/dp312_venv"
    ):
        raise RuntimeError("contract reviewer Python authority drifted")
    verify_complete_seal(
        CONTRACT_DIR,
        contract_root,
        label="V25 selector-after-pool replay contract",
    )
    if output != OUTPUT or output.exists():
        raise RuntimeError("contract review exact output drifted")
    value = json.loads((CONTRACT_DIR / "contract.json").read_text("ascii"))
    reviewed = review_contract(value)
    verify_complete_seal(
        FAILURE_CLOSEOUT,
        reviewed["sealed_inputs"]["failure_closeout_root_sha256"],
        label="V25 selector replay failure closeout",
    )
    verify_complete_seal(
        FAILURE_CLOSEOUT_REVIEW,
        reviewed["sealed_inputs"]["failure_closeout_review_root_sha256"],
        label="V25 selector replay failure closeout review",
    )
    if (
        reviewed["implementation_head"] != _git("rev-parse", "HEAD")
        or reviewed["implementation_head"]
        != _git("rev-parse", "refs/remotes/origin/main")
        or _git("status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("contract reviewer live implementation drifted")
    rebuilt_source_hashes = {
        name: _file_sha256(ROOT / relative)
        for name, relative in SOURCE_PATHS.items()
    }
    if rebuilt_source_hashes != reviewed["source_hashes"]:
        raise RuntimeError("contract reviewer source hash reconstruction drifted")
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        report = {
            "schema_version": (
                "camp_dp_v25_selector_after_pool_replay_replacement_"
                "contract_review_v1"
            ),
            "status": "PASS_independent_literal_contract_review",
            "contract_root_sha256": contract_root,
            "contract_payload_sha256": reviewed["contract_payload_sha256"],
            "reviewer_imported_producer_contract_or_selector_oracle": False,
            "reviewed_atom_count": 14,
            "reviewed_run_count": 320,
            "model_dp_latent_candidate_generation_call_count": 0,
            "selector_call_count": 0,
            "outcome_read": False,
        }
        (staging / "report.json").write_bytes(_canonical(report))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 selector-after-pool replay contract review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 selector-after-pool replay contract review",
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(review(contract_root=args.contract_root, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
