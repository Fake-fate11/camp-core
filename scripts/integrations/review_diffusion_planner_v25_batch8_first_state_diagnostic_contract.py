"""Seal a separate-role literal review of the batch8 diagnostic contract."""

from __future__ import annotations

import argparse
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
from camp_core.integrations.diffusion_planner_v25_batch8_first_state_diagnostic_review import (  # noqa: E402
    independent_contract_review,
)


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True
    ).strip()


def review(*, source: Path, source_root: str, output: Path) -> str:
    verify_complete_seal(source, source_root, label="diagnostic contract")
    contract = json.loads((source / "contract.json").read_text("utf-8"))
    source_report = json.loads((source / "report.json").read_text("utf-8"))
    if (
        source_report.get("status")
        != "sealed_outcome_independent_diagnostic_contract"
        or source_report.get("model_pool_selector_call_count") != 0
        or source_report.get("outcome_read") is not False
        or source_report.get("old_artifact_cas_write_count") != 0
    ):
        raise RuntimeError("producer contract artifact drifted")
    reviewed = independent_contract_review(
        contract,
        implementation_head=contract["implementation_head"],
        exact_dirs=contract["exact_dirs"],
        source_sha256=contract["source_sha256"],
    )
    report = {
        **reviewed,
        "schema_version": (
            "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_"
            "contract_independent_review_artifact_v1"
        ),
        "status": "passed_independent_literal_contract_review",
        "source_root_sha256": source_root,
        "review_head": _git("rev-parse", "HEAD"),
        "model_pool_selector_call_count": 0,
        "outcome_read": False,
        "old_artifact_cas_write_count": 0,
    }
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
                    "implementation_head": contract["implementation_head"],
                    "review_head": report["review_head"],
                    "fixed_dp_head": contract["fixed_dp_head"],
                }
            )
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(staging, label="V25 batch8 diagnostic contract review")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 batch8 diagnostic contract review"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(review(source=args.source, source_root=args.source_root, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
