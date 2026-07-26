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
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_review import (  # noqa: E402
    EXPECTED_FIXED_DP,
    independent_review_report,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


def review_matrix(
    output: Path,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    matrix_dir: Path,
    matrix_root: str,
) -> str:
    verify_complete_seal(contract_dir, contract_root, label="industrial contract")
    verify_complete_seal(
        contract_review_dir,
        contract_review_root,
        label="industrial contract review",
    )
    verify_complete_seal(matrix_dir, matrix_root, label="industrial capability matrix")
    contract = object_from(contract_dir / "report.json")["contract"]
    matrix = object_from(matrix_dir / "report.json")["capability_matrix"]
    independent = independent_review_report(contract, matrix)
    head = git_head()
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_oriented_evaluation_capability_review_artifact_v1"
        ),
        "status": (
            "passed_independent_literal_industrial_evidence_capability_review"
        ),
        "bindings": {
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "capability_matrix_root_sha256": matrix_root,
        },
        "independent_review": independent,
        "reviewer_head": head,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_write_count": 0,
        "claim_authorized": False,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "independent_industrial_evidence_capability_review",
            "reviewer_head": head,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "capability_matrix_root_sha256": matrix_root,
            "fixed_dp_head": EXPECTED_FIXED_DP,
        },
        label="V25 independent industrial evidence capability review",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-dir", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review-dir", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--matrix-root", required=True)
    args = parser.parse_args()
    print(
        review_matrix(
            args.output,
            args.contract_dir,
            args.contract_root,
            args.contract_review_dir,
            args.contract_review_root,
            args.matrix_dir,
            args.matrix_root,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
