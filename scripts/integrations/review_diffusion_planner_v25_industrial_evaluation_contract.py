from __future__ import annotations

import argparse
import hashlib
import json
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
    review_contract_literal,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


def review_contract(output: Path, contract_dir: Path, contract_root: str) -> str:
    verify_complete_seal(
        contract_dir, contract_root, label="industrial evaluation contract"
    )
    producer = object_from(contract_dir / "report.json")
    if (
        producer.get("schema_version")
        != "camp_dp_v25_industrial_oriented_evaluation_contract_artifact_v1"
        or producer.get("status")
        != "sealed_outcome_independent_industrial_evaluation_contract"
    ):
        raise ValueError("industrial contract producer artifact drifted")
    contract = review_contract_literal(producer["contract"])
    # The matrix is not yet formed; use a marker in the contract-only review.
    review = {
        "contract_sha256": hashlib.sha256(
            (
                json.dumps(
                    contract,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                )
                + "\n"
            ).encode("utf-8")
        ).hexdigest(),
        "endpoint_count": len(contract["endpoints"]),
        "literal_oracle": {
            "producer_module_imported": False,
            "producer_registry_formula_filter_classification_imported": False,
            "authority_endpoint_statistics_legacy_and_claim_reconstructed": True,
        },
    }
    head = git_head()
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_oriented_evaluation_contract_review_artifact_v1"
        ),
        "status": "passed_independent_literal_industrial_evaluation_contract_review",
        "contract_binding": {
            "path": str(contract_dir.resolve()),
            "root_sha256": contract_root,
        },
        "independent_review": review,
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
            "role": "independent_industrial_evaluation_contract_review",
            "reviewer_head": head,
            "contract_root_sha256": contract_root,
            "fixed_dp_head": EXPECTED_FIXED_DP,
        },
        label="V25 independent industrial evaluation contract review",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-dir", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    args = parser.parse_args()
    print(review_contract(args.output, args.contract_dir, args.contract_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
