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

from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract import (  # noqa: E402
    FIXED_DP_HEAD,
    HIGH_AUTHORITY_SHA256,
    evaluation_contract,
    validate_evaluation_contract,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    write_atomic,
)


def freeze_contract(output: Path) -> str:
    contract = validate_evaluation_contract(evaluation_contract())
    head = git_head()
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_oriented_evaluation_contract_artifact_v1"
        ),
        "status": "sealed_outcome_independent_industrial_evaluation_contract",
        "contract": contract,
        "implementation_head": head,
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_write_count": 0,
        "claim_authorized": False,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_oriented_evaluation_contract",
            "implementation_head": head,
            "fixed_dp_head": FIXED_DP_HEAD,
            "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        },
        label="V25 industrial-oriented evaluation contract",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(freeze_contract(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
