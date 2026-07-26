"""Seal the separate-role literal input-only preflight review."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
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
    independent_preflight_review,
)


OLD_PREFLIGHT_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c"
)
OLD_PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain object")
    return value


def review(
    *,
    source: Path,
    source_root: str,
    contract_root: str,
    contract_review_root: str,
    output: Path,
) -> str:
    verify_complete_seal(source, source_root, label="batch8 first-state preflight")
    verify_complete_seal(
        OLD_PREFLIGHT_DIR, OLD_PREFLIGHT_ROOT, label="sealed v5 input preflight"
    )
    result = independent_preflight_review(
        _json(source / "receipt.json"),
        old_receipt=_json(OLD_PREFLIGHT_DIR / "receipt.json"),
        contract_root=contract_root,
        contract_review_root=contract_review_root,
    )
    report = {
        **result,
        "schema_version": (
            "camp_dp_v25_single_invocation_batch8_first_state_input_"
            "preflight_independent_review_artifact_v1"
        ),
        "source_root_sha256": source_root,
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
        (staging / "report.json").write_bytes(
            (
                json.dumps(
                    report,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            ).encode("ascii")
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(
            staging, label="V25 batch8 first-state preflight review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 batch8 first-state preflight review"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        review(
            source=args.source,
            source_root=args.source_root,
            contract_root=args.contract_root,
            contract_review_root=args.contract_review_root,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
