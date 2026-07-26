"""Seal the input-only zero-overlap preflight for one batch8 diagnostic."""

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
from camp_core.integrations.diffusion_planner_v25_batch8_first_state_diagnostic import (  # noqa: E402
    FIXED_DP_HEAD,
    OLD_PREFLIGHT_REVIEW_ROOT,
    OLD_PREFLIGHT_ROOT,
    build_preflight_receipt,
    canonical_bytes,
    unique_latent,
    validate_contract,
)


OLD_PREFLIGHT_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c"
)
OLD_PREFLIGHT_REVIEW_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_review_67308ac0_ed0d298c"
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain object")
    return value


def materialize(
    *,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    output: Path,
) -> str:
    verify_complete_seal(contract_dir, contract_root, label="diagnostic contract")
    verify_complete_seal(
        contract_review_dir,
        contract_review_root,
        label="diagnostic contract review",
    )
    verify_complete_seal(
        OLD_PREFLIGHT_DIR, OLD_PREFLIGHT_ROOT, label="sealed v5 input preflight"
    )
    verify_complete_seal(
        OLD_PREFLIGHT_REVIEW_DIR,
        OLD_PREFLIGHT_REVIEW_ROOT,
        label="sealed v5 input preflight review",
    )
    contract = validate_contract(_json(contract_dir / "contract.json"))
    if contract["exact_dirs"]["preflight"] != str(output):
        raise RuntimeError("preflight exact-dir binding drifted")
    old_receipt = _json(OLD_PREFLIGHT_DIR / "receipt.json")
    receipt = build_preflight_receipt(
        old_receipt=old_receipt,
        contract_root=contract_root,
        contract_review_root=contract_review_root,
    )
    latent = unique_latent()
    report = {
        "schema_version": (
            "camp_dp_v25_single_invocation_batch8_first_state_input_"
            "preflight_artifact_v1"
        ),
        "status": "passed_input_only_zero_overlap_preflight",
        "receipt_sha256": receipt["receipt_sha256"],
        "new_manifest_sha256": receipt["new_manifest"]["manifest_sha256"],
        "new_instance_key_sha256": receipt["new_instance_key_sha256"],
        "latent_tensor_sha256": receipt["new_manifest"][
            "actual_latent_tensor_manifest"
        ]["tensor_sha256"],
        "latent_unique_row_count": 8,
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
        (staging / "receipt.json").write_bytes(canonical_bytes(receipt))
        (staging / "latent_tensor.f32le").write_bytes(
            latent.tobytes(order="C")
        )
        (staging / "report.json").write_bytes(canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "implementation_head": contract["implementation_head"],
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "old_preflight_root_sha256": OLD_PREFLIGHT_ROOT,
                    "old_preflight_review_root_sha256": OLD_PREFLIGHT_REVIEW_ROOT,
                }
            )
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(staging, label="V25 batch8 first-state preflight")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 batch8 first-state preflight"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        materialize(
            contract_dir=args.contract,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review,
            contract_review_root=args.contract_review_root,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
