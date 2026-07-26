"""Seal a separate-role literal review of the training-support contract."""

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
from camp_core.integrations.diffusion_planner_v25_batch8_training_support_reference_review import (  # noqa: E402
    review_contract,
)


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def review(*, source: Path, source_root: str, output: Path) -> str:
    verify_complete_seal(
        source,
        source_root,
        label="V25 batch8 training-support reference contract",
    )
    source_report = _object(source / "report.json")
    if (
        output.exists()
        or source_report.get("status") != "sealed_outcome_independent_contract"
        or source_report.get("model_pool_selector_call_count") != 0
        or source_report.get("outcome_read") is not False
        or source_report.get("old_artifact_or_cas_write_count") != 0
        or (source / "run.exit").read_text(encoding="ascii") != "0\n"
    ):
        raise RuntimeError("contract artifact invariant drifted")
    contract = review_contract(_object(source / "contract.json"))
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    report = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_reference_"
            "contract_independent_review_artifact_v1"
        ),
        "status": "passed_independent_literal_contract_review",
        "reviewed_contract_root_sha256": source_root,
        "reviewed_contract_sha256": __import__("hashlib").sha256(
            (source / "contract.json").read_bytes()
        ).hexdigest(),
        "review_head": head,
        "contract": contract,
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
        (staging / "report.json").write_bytes(_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _bytes({"role": "independent_contract_review", "review_head": head})
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(
            staging,
            label="V25 batch8 training-support contract independent review",
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 batch8 training-support contract independent review",
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
