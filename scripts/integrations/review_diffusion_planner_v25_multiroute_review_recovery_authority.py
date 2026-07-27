from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_multiroute_review_recovery_review import (  # noqa: E402
    EXPECTED_AUTHORITY,
    EXPECTED_EVALUATION_ROOT,
    EXPECTED_EXECUTION_REVIEW_ROOT,
    EXPECTED_EXECUTION_ROOT,
    EXPECTED_PREFLIGHT_ROOT,
    EXPECTED_SOURCE_ARTIFACTS,
    review_stage_authority_literal,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    object_from,
    write_atomic,
)
EXECUTION_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_industrial_v3_multiroute_v2_replacement_"
    "8fc8e271_47a47c03_execution"
)
EXECUTION_REVIEW_DIR = Path(str(EXECUTION_DIR) + "_review")
PREFLIGHT_DIR = Path(str(EXECUTION_DIR).replace("_execution", "_preflight"))
EVALUATION_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_industrial_v3_multiroute_v2_"
    "evaluation_actor_binding_replacement_495d3b2b_ca642a15_evaluation"
)


def review(*, output: Path, source_dir: Path, source_root: str) -> str:
    verify_complete_seal(source_dir, source_root, label="stage authority")
    source = object_from(source_dir / "report.json")
    reviewed = review_stage_authority_literal(source)
    if output.resolve() != Path(reviewed["exact_dirs"]["stage_authority_review"]):
        raise ValueError("stage authority review exact dir drifted")
    for row in EXPECTED_SOURCE_ARTIFACTS:
        provenance = next(
            item
            for item in reviewed["source_artifact_provenance"]
            if item["role"] == row["role"]
        )
        path = Path(provenance["exact_dir"])
        seal = verify_complete_seal(
            path, row["root_sha256"], label=f"reviewer {row['role']}"
        )
        if (
            provenance["root_receipt_verified"] is not True
            or provenance["schema_version"] != row["schema_version"]
            or provenance["status"] != row["status"]
            or (path / "ROOT_SHA256SUMS").read_text(encoding="ascii")
            != f"{seal['root_sha256']}  SHA256SUMS\n"
        ):
            raise ValueError(f"reviewer source provenance drifted: {row['role']}")
    for path, root, label in (
        (EXECUTION_DIR, EXPECTED_EXECUTION_ROOT, "execution"),
        (
            EXECUTION_REVIEW_DIR,
            EXPECTED_EXECUTION_REVIEW_ROOT,
            "execution review",
        ),
        (PREFLIGHT_DIR, EXPECTED_PREFLIGHT_ROOT, "preflight"),
        (EVALUATION_DIR, EXPECTED_EVALUATION_ROOT, "evaluation"),
    ):
        verify_complete_seal(path, root, label=f"reviewer {label}")
    evaluation = object_from(EVALUATION_DIR / "report.json")
    authority = reviewed["evaluation_source_authority"]
    if (
        authority["root_sha256"] != EXPECTED_EVALUATION_ROOT
        or authority["preflight_root_sha256_from_source"]
        != EXPECTED_PREFLIGHT_ROOT
        or evaluation.get("preflight_root_sha256") != EXPECTED_PREFLIGHT_ROOT
        or evaluation.get("execution_root_sha256") != EXPECTED_EXECUTION_ROOT
        or evaluation.get("execution_review_root_sha256")
        != EXPECTED_EXECUTION_REVIEW_ROOT
        or authority["fresh_or_holdout_outcome_read"] is not False
        or authority["root_receipt_verified"] is not True
    ):
        raise ValueError("reviewer evaluation source authority drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "merged_review_recovery_stage_authority_review_v1"
        ),
        "status": "independent_complete_external_authority_chain_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "implementation_head": reviewed["implementation_head"],
        "evaluation_root_sha256": EXPECTED_EVALUATION_ROOT,
        "execution_root_sha256": EXPECTED_EXECUTION_ROOT,
        "execution_review_root_sha256": EXPECTED_EXECUTION_REVIEW_ROOT,
        "preflight_root_sha256": EXPECTED_PREFLIGHT_ROOT,
        "source_artifact_count": len(EXPECTED_SOURCE_ARTIFACTS),
        "root_receipts_independently_verified": True,
        "schema_status_head_continuation_exact_dirs_independently_rebuilt": True,
        "producer_stage_authority_oracle_imported": False,
        "producer_evaluator_model_execution_rerun": False,
        "fresh_or_holdout_outcome_read": False,
        "claim_authorized": False,
        "five_class_flow_policy": True,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "merged_review_recovery_stage_authority_review",
            "authority_sha256": EXPECTED_AUTHORITY,
            "source_root_sha256": source_root,
        },
        label="V25 merged review recovery stage authority review",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    print(
        review(
            output=args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
