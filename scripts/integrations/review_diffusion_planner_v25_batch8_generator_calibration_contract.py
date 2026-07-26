"""Independent sealed review of the batch8 generator calibration contract."""

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

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact, verify_complete_seal  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration import EXACT_DIRS  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration_review import review_contract  # noqa: E402


def review(contract_dir: Path, contract_root: str, output: Path) -> str:
    verify_complete_seal(contract_dir, contract_root, label="generator calibration contract")
    source = json.loads((contract_dir / "report.json").read_text(encoding="ascii"))
    result = review_contract(source["contract"])
    report = {
        "schema_version": "camp_dp_v25_batch8_generator_calibration_contract_independent_review_artifact_v1",
        "status": "PASS",
        "review": result,
        "reviewed_contract_root_sha256": contract_root,
        "producer_module_imported": False,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
    }
    return _atomic(output, report)


def _atomic(output: Path, report: dict) -> str:
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent))
    try:
        blob = (json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")
        (staging / "report.json").write_bytes(blob)
        root = seal_artifact(staging, label="V25 batch8 generator calibration contract independent review")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 batch8 generator calibration contract independent review")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-dir", type=Path, default=Path(EXACT_DIRS["contract"]))
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--output", type=Path, default=Path(EXACT_DIRS["contract_review"]))
    args = parser.parse_args()
    print(review(args.contract_dir, args.contract_root, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
