from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (PACKAGE_ROOT, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (  # noqa: E402
    HIGH_AUTHORITY_SHA256,
    evaluation_contract_v3,
    validate_evaluation_contract_v3,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    write_atomic,
)


def freeze_contract_v3(output: Path) -> str:
    contract = validate_evaluation_contract_v3(evaluation_contract_v3())
    head = git_head()
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_oriented_evaluation_contract_artifact_v3"
            ),
            "status": (
                "sealed_outcome_independent_industrial_evaluation_contract_v3"
            ),
            "contract": contract,
            "implementation_head": head,
            "high_authority_sha256": HIGH_AUTHORITY_SHA256,
            "model_pool_selector_call_count": 0,
            "outcome_values_read": False,
            "old_artifact_or_cas_write_count": 0,
            "claim_authorized": False,
        },
        {
            "role": "industrial_oriented_evaluation_contract_v3",
            "implementation_head": head,
            "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        },
        label="V25 industrial-oriented evaluation contract v3",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(freeze_contract_v3(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
