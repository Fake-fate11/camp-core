from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (PACKAGE_ROOT, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import verify_complete_seal  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_review_v2 import (  # noqa: E402
    SOURCE_ROOTS,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_review_v3 import (  # noqa: E402
    review_capability_v3_literal,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


def review_matrix_v3(
    output: Path,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    matrix_dir: Path,
    matrix_root: str,
    source_dirs: dict[str, Path],
) -> str:
    verify_complete_seal(contract_dir, contract_root, label="industrial v3 contract")
    verify_complete_seal(
        contract_review_dir, contract_review_root, label="industrial v3 contract review"
    )
    verify_complete_seal(matrix_dir, matrix_root, label="industrial v3 capability")
    contract = object_from(contract_dir / "report.json")["contract"]
    matrix = object_from(matrix_dir / "report.json")["capability_matrix"]
    review_capability_v3_literal(matrix, contract, source_dirs)
    head = git_head()
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_oriented_evaluation_capability_review_artifact_v3"
            ),
            "status": (
                "passed_independent_scalar_leaf_capability_audit_review_v3"
            ),
            "contract_binding": {
                "path": str(contract_dir.resolve()),
                "root_sha256": contract_root,
            },
            "contract_review_binding": {
                "path": str(contract_review_dir.resolve()),
                "root_sha256": contract_review_root,
            },
            "capability_binding": {
                "path": str(matrix_dir.resolve()),
                "root_sha256": matrix_root,
            },
            "scalar_leaf_count": 161,
            "literal_oracle": {
                "producer_module_imported": False,
                "sealed_inventories_reverified": True,
                "json_pointers_rebuilt": True,
                "classifications_rebuilt": True,
                "v3_leaf_semantics_rebuilt": True,
            },
            "reviewer_head": head,
            "model_pool_selector_call_count": 0,
            "outcome_values_read": False,
            "old_artifact_or_cas_write_count": 0,
            "claim_authorized": False,
        },
        {
            "role": "independent_industrial_capability_review_v3",
            "reviewer_head": head,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "capability_root_sha256": matrix_root,
        },
        label="V25 independent industrial capability review v3",
    )


def _source_args(parser: argparse.ArgumentParser) -> None:
    for key in SOURCE_ROOTS:
        parser.add_argument(f"--{key.replace('_', '-')}-dir", type=Path, required=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-dir", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review-dir", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--matrix-root", required=True)
    _source_args(parser)
    args = parser.parse_args()
    source_dirs = {key: getattr(args, f"{key}_dir") for key in SOURCE_ROOTS}
    print(
        review_matrix_v3(
            args.output,
            args.contract_dir,
            args.contract_root,
            args.contract_review_dir,
            args.contract_review_root,
            args.matrix_dir,
            args.matrix_root,
            source_dirs,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
