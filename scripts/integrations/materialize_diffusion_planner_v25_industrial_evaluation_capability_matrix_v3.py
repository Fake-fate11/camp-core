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
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v2 import (  # noqa: E402
    SEALED_SOURCES,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (  # noqa: E402
    capability_matrix_v3,
    validate_capability_matrix_v3,
    validate_evaluation_contract_v3,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


def materialize_v3(
    output: Path,
    contract_dir: Path,
    contract_root: str,
    review_dir: Path,
    review_root: str,
    source_dirs: dict[str, Path],
) -> str:
    verify_complete_seal(contract_dir, contract_root, label="industrial v3 contract")
    verify_complete_seal(review_dir, review_root, label="industrial v3 contract review")
    review = object_from(review_dir / "report.json")
    if review.get("status") != (
        "passed_independent_literal_industrial_evaluation_contract_review_v3"
    ):
        raise ValueError("industrial v3 contract review did not pass")
    contract = validate_evaluation_contract_v3(
        object_from(contract_dir / "report.json")["contract"]
    )
    matrix = validate_capability_matrix_v3(
        capability_matrix_v3(contract, source_dirs), contract, source_dirs
    )
    head = git_head()
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_oriented_evaluation_capability_artifact_v3"
            ),
            "status": "sealed_structure_only_scalar_leaf_capability_audit_v3",
            "contract_binding": {
                "path": str(contract_dir.resolve()),
                "root_sha256": contract_root,
            },
            "contract_review_binding": {
                "path": str(review_dir.resolve()),
                "root_sha256": review_root,
            },
            "source_dirs": {
                key: str(value.resolve()) for key, value in sorted(source_dirs.items())
            },
            "capability_matrix": matrix,
            "implementation_head": head,
            "model_pool_selector_call_count": 0,
            "outcome_values_read": False,
            "old_artifact_or_cas_write_count": 0,
            "claim_authorized": False,
        },
        {
            "role": "industrial_evaluation_scalar_leaf_capability_audit_v3",
            "implementation_head": head,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": review_root,
        },
        label="V25 industrial evaluation scalar leaf capability audit v3",
    )


def _source_args(parser: argparse.ArgumentParser) -> None:
    for key in SEALED_SOURCES:
        parser.add_argument(f"--{key.replace('_', '-')}-dir", type=Path, required=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-dir", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--review-root", required=True)
    _source_args(parser)
    args = parser.parse_args()
    source_dirs = {key: getattr(args, f"{key}_dir") for key in SEALED_SOURCES}
    print(
        materialize_v3(
            args.output,
            args.contract_dir,
            args.contract_root,
            args.review_dir,
            args.review_root,
            source_dirs,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
