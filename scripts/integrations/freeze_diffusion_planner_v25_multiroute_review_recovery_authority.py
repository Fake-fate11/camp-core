from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_multiroute_review_recovery import (  # noqa: E402
    AUTHORITY_SHA256,
    BASE_HEAD,
    CORRECTION_CONTINUATION,
    EVALUATION_ROOT,
    EXECUTION_REVIEW_ROOT,
    EXECUTION_ROOT,
    INDUSTRIAL_CAPABILITY_REVIEW_ROOT,
    INDUSTRIAL_CAPABILITY_ROOT,
    INDUSTRIAL_CONTRACT_REVIEW_ROOT,
    INDUSTRIAL_CONTRACT_ROOT,
    PREFLIGHT_ROOT,
    SOURCE_ARTIFACTS,
    exact_dirs,
    old_exact_dirs,
    stage_authority_payload,
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
EVALUATION_DIR = Path(old_exact_dirs()["evaluation"])
INDUSTRIAL_DIRS = {
    "contract": Path(
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_evaluation_contract_v3_c197c1e5_720e9293"
    ),
    "contract_review": Path(
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_evaluation_contract_v3_review_c197c1e5_720e9293"
    ),
    "capability": Path(
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_evaluation_capability_matrix_v3_"
        "c197c1e5_720e9293"
    ),
    "capability_review": Path(
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_evaluation_capability_matrix_v3_"
        "review_c197c1e5_720e9293"
    ),
}


def _verified_report(path: Path, root: str, label: str) -> dict[str, Any]:
    seal = verify_complete_seal(path, root, label=label)
    receipt = (path / "ROOT_SHA256SUMS").read_text(encoding="ascii")
    if receipt != f"{seal['root_sha256']}  SHA256SUMS\n":
        raise ValueError(f"{label} literal root receipt drifted")
    return object_from(path / "report.json")


def freeze(*, output: Path, implementation_head: str) -> str:
    dirs = exact_dirs(implementation_head)
    if output.resolve() != Path(dirs["stage_authority"]):
        raise ValueError("stage authority exact dir drifted")
    old_dirs = old_exact_dirs()
    sources = []
    for role, expected_root, schema, status in SOURCE_ARTIFACTS:
        path = Path(old_dirs[role])
        report = _verified_report(path, expected_root, role)
        if (
            report.get("schema_version") != schema
            or report.get("status") != status
            or report.get("implementation_head") != BASE_HEAD
            or report.get("continuation_sha256") != CORRECTION_CONTINUATION
        ):
            raise ValueError(f"stage source identity drifted: {role}")
        sources.append(
            {
                "role": role,
                "root_sha256": expected_root,
                "schema_version": schema,
                "status": status,
                "implementation_head": BASE_HEAD,
                "continuation_sha256": CORRECTION_CONTINUATION,
                "exact_dir": str(path),
                "root_receipt_verified": True,
            }
        )
    _verified_report(EXECUTION_DIR, EXECUTION_ROOT, "execution")
    _verified_report(
        EXECUTION_REVIEW_DIR, EXECUTION_REVIEW_ROOT, "execution review"
    )
    _verified_report(PREFLIGHT_DIR, PREFLIGHT_ROOT, "preflight")
    evaluation = _verified_report(
        EVALUATION_DIR, EVALUATION_ROOT, "corrected evaluation"
    )
    if (
        evaluation.get("implementation_head") != BASE_HEAD
        or evaluation.get("continuation_sha256") != CORRECTION_CONTINUATION
        or evaluation.get("preflight_root_sha256") != PREFLIGHT_ROOT
        or evaluation.get("execution_root_sha256") != EXECUTION_ROOT
        or evaluation.get("execution_review_root_sha256")
        != EXECUTION_REVIEW_ROOT
        or evaluation.get("fresh_or_b4_outcome_values_read") is not False
        or evaluation.get("claim_authorized") is not False
    ):
        raise ValueError("corrected evaluation authority binding drifted")
    for role, path, root in (
        ("industrial contract", INDUSTRIAL_DIRS["contract"], INDUSTRIAL_CONTRACT_ROOT),
        (
            "industrial contract review",
            INDUSTRIAL_DIRS["contract_review"],
            INDUSTRIAL_CONTRACT_REVIEW_ROOT,
        ),
        (
            "industrial capability",
            INDUSTRIAL_DIRS["capability"],
            INDUSTRIAL_CAPABILITY_ROOT,
        ),
        (
            "industrial capability review",
            INDUSTRIAL_DIRS["capability_review"],
            INDUSTRIAL_CAPABILITY_REVIEW_ROOT,
        ),
    ):
        _verified_report(path, root, role)
    payload = stage_authority_payload(implementation_head, [
        {
            "role": row["role"],
            "root_sha256": row["root_sha256"],
            "schema_version": row["schema_version"],
            "status": row["status"],
        }
        for row in sources
    ])
    report = {
        **payload,
        "source_artifact_provenance": sources,
        "evaluation_source_authority": {
            "exact_dir": str(EVALUATION_DIR),
            "root_sha256": EVALUATION_ROOT,
            "schema_version": evaluation["schema_version"],
            "status": evaluation["status"],
            "implementation_head": evaluation["implementation_head"],
            "continuation_sha256": evaluation["continuation_sha256"],
            "preflight_root_sha256_from_source": evaluation[
                "preflight_root_sha256"
            ],
            "fresh_or_holdout_outcome_read": False,
            "root_receipt_verified": True,
        },
    }
    return write_atomic(
        output,
        report,
        {
            "role": "merged_review_recovery_stage_authority",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": implementation_head,
            "evaluation_root_sha256": EVALUATION_ROOT,
        },
        label="V25 merged review recovery stage authority",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--implementation-head", required=True)
    args = parser.parse_args()
    print(freeze(output=args.output, implementation_head=args.implementation_head))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
