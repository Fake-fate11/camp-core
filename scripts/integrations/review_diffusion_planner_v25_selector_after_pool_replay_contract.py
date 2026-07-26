"""Independently review the V25 selector-after-pool replay contract."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
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
    "/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_contract_v1_59874f4a"
)
OUTPUT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_selector_after_pool_replay_contract_review_v1_59874f4a"
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
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        report = {
            "schema_version": (
                "camp_dp_v25_selector_after_pool_replay_contract_review_v1"
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
