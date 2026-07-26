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
    review_contract_v2_literal,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


def review_contract_v2(
    output: Path, contract_dir: Path, contract_root: str
) -> str:
    verify_complete_seal(contract_dir, contract_root, label="industrial v2 contract")
    source = object_from(contract_dir / "report.json")
    if (
        source.get("schema_version")
        != "camp_dp_v25_industrial_oriented_evaluation_contract_artifact_v2"
        or source.get("status")
        != "sealed_outcome_independent_industrial_evaluation_contract_v2"
    ):
        raise ValueError("industrial v2 contract artifact drifted")
    contract = review_contract_v2_literal(source["contract"])
    head = git_head()
    report = {
        "schema_version": "camp_dp_v25_industrial_oriented_evaluation_contract_review_artifact_v2",
        "status": "passed_independent_literal_industrial_evaluation_contract_review_v2",
        "contract_binding": {
            "path": str(contract_dir.resolve()),
            "root_sha256": contract_root,
        },
        "parent_endpoint_count": contract["parent_endpoint_count"],
        "scalar_leaf_count": contract["scalar_leaf_count"],
        "literal_oracle": {
            "producer_module_imported": False,
            "local_parent_and_leaf_registry_rebuilt": True,
            "local_decision_topology_rebuilt": True,
        },
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
            "role": "independent_industrial_evaluation_contract_review_v2",
            "reviewer_head": head,
            "contract_root_sha256": contract_root,
        },
        label="V25 independent industrial evaluation contract review v2",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-dir", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    args = parser.parse_args()
    print(review_contract_v2(args.output, args.contract_dir, args.contract_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
