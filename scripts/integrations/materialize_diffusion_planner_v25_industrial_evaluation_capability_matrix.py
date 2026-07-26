from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract import (  # noqa: E402
    FIXED_DP_HEAD,
    capability_matrix,
    validate_capability_matrix,
    validate_evaluation_contract,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


def materialize(
    output: Path,
    contract_dir: Path,
    contract_root: str,
    review_dir: Path,
    review_root: str,
) -> str:
    verify_complete_seal(contract_dir, contract_root, label="industrial contract")
    verify_complete_seal(review_dir, review_root, label="industrial contract review")
    contract_report = object_from(contract_dir / "report.json")
    review_report = object_from(review_dir / "report.json")
    if review_report.get("status") != (
        "passed_independent_literal_industrial_evaluation_contract_review"
    ):
        raise ValueError("industrial contract review did not pass")
    contract = validate_evaluation_contract(contract_report["contract"])
    matrix = validate_capability_matrix(capability_matrix(contract), contract)
    head = git_head()
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_oriented_evaluation_capability_artifact_v1"
        ),
        "status": "sealed_structure_only_industrial_evidence_capability_matrix",
        "contract_binding": {
            "path": str(contract_dir.resolve()),
            "root_sha256": contract_root,
        },
        "contract_review_binding": {
            "path": str(review_dir.resolve()),
            "root_sha256": review_root,
        },
        "capability_matrix": matrix,
        "implementation_head": head,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_write_count": 0,
        "claim_authorized": False,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_evaluation_evidence_capability_matrix",
            "implementation_head": head,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": review_root,
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        label="V25 industrial evaluation evidence capability matrix",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-dir", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--review-root", required=True)
    args = parser.parse_args()
    print(
        materialize(
            args.output,
            args.contract_dir,
            args.contract_root,
            args.review_dir,
            args.review_root,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
