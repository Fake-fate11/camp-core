#!/usr/bin/env python3
"""Finalize the Fresh B4 scientific CAS after reviewed honest closeout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_terminal_closeout import (  # noqa: E402,E501
    NEXT_AUTHORITY,
    UNAVAILABLE,
    validate_b4_evaluation_terminal_closeout,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402,E501
    _strict_canonical_json,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    terminate_scientific_identity,
    validate_scientific_ledger,
)


REVIEW_SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_post_exposure_evaluation_control_fatal_closeout_review_v1"
)
REVIEW_STATUS = (
    "passed_independent_fresh_b4_evaluation_terminal_closeout_review"
)
TERMINAL_REASON = "post_exposure_evaluation_control_fatal"
_REVIEW_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "reviewed_root_sha256",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "execution_plan_sha256",
        "run_nonce",
        "opening_release_root_sha256",
        "execution_root_sha256",
        "execution_review_root_sha256",
        "implementation_source_head",
        "pointer_head_at_release",
        "fixed_dp_head",
        "reporting_machinery_head",
        "control_evidence_rehashed",
        "accepted_seals_independently_verified",
        "evaluation_artifact_created",
        "evaluation_root_sha256",
        "evaluation_review_started",
        "evaluation_review_artifact_created",
        "related_process_count",
        "scientific_state_before",
        "planned_pair_count",
        "complete_paired_row_count",
        "planned_arm_run_count",
        "complete_arm_run_count",
        "terminal_arm_run_count",
        "full_denominator_formed",
        "raw_outcome_values_inspected",
        "rerun_allowed",
        "claim_authorized",
        "evaluation_result_status",
        "independent_oracle",
        "next_authority",
    }
)


def finalize(
    *,
    closeout_artifact: Path,
    closeout_root_sha256: str,
    closeout_review_artifact: Path,
    closeout_review_root_sha256: str,
    scientific_ledger_path: Path,
) -> dict[str, object]:
    closeout_path = Path(closeout_artifact).resolve()
    review_path = Path(closeout_review_artifact).resolve()
    scientific_path = Path(scientific_ledger_path).resolve()
    verify_complete_seal(
        closeout_path,
        closeout_root_sha256,
        label="Fresh B4 evaluation terminal closeout",
    )
    verify_complete_seal(
        review_path,
        closeout_review_root_sha256,
        label="Fresh B4 evaluation terminal closeout review",
    )
    if (
        (closeout_path / "run.exit").read_bytes() != b"0\n"
        or (review_path / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("Fresh B4 terminal artifact run.exit drifted")
    closeout = validate_b4_evaluation_terminal_closeout(
        _strict_canonical_json(closeout_path / "closeout.json")
    )
    review = _strict_canonical_json(review_path / "report.json")
    if type(review) is not dict or set(review) != _REVIEW_FIELDS:
        raise ValueError("Fresh B4 terminal review field set drifted")
    if (
        review["schema_version"] != REVIEW_SCHEMA_VERSION
        or review["status"] != REVIEW_STATUS
        or review["reviewed_root_sha256"] != closeout_root_sha256
        or review["holdout_identity_sha256"]
        != closeout["holdout_identity_sha256"]
        or review["experiment_protocol_sha256"]
        != closeout["experiment_protocol_sha256"]
        or review["execution_plan_sha256"] != closeout["execution_plan_sha256"]
        or review["run_nonce"] != closeout["run_nonce"]
        or review["opening_release_root_sha256"]
        != closeout["opening_release"]["root_sha256"]
        or review["execution_root_sha256"]
        != closeout["execution"]["root_sha256"]
        or review["execution_review_root_sha256"]
        != closeout["execution_review"]["root_sha256"]
        or review["implementation_source_head"]
        != closeout["implementation_source_head"]
        or review["pointer_head_at_release"]
        != closeout["pointer_head_at_release"]
        or review["fixed_dp_head"] != closeout["fixed_dp_head"]
        or review["reporting_machinery_head"]
        != closeout["reporting_machinery_head"]
        or review["control_evidence_rehashed"] is not True
        or review["accepted_seals_independently_verified"] is not True
        or review["evaluation_artifact_created"] is not False
        or review["evaluation_root_sha256"] is not None
        or review["evaluation_review_started"] is not False
        or review["evaluation_review_artifact_created"] is not False
        or review["related_process_count"] != 0
        or review["scientific_state_before"] != "full_denominator_formed"
        or review["planned_pair_count"] != 500
        or review["complete_paired_row_count"] != 500
        or review["planned_arm_run_count"] != 1500
        or review["complete_arm_run_count"] != 1500
        or review["terminal_arm_run_count"] != 1500
        or review["full_denominator_formed"] is not True
        or review["raw_outcome_values_inspected"] is not False
        or review["rerun_allowed"] is not False
        or review["claim_authorized"] is not False
        or review["evaluation_result_status"] != UNAVAILABLE
        or review["independent_oracle"] != "reviewer_local_literal_v1"
        or review["next_authority"] != NEXT_AUTHORITY
    ):
        raise ValueError("Fresh B4 terminal review value drifted")
    scientific = validate_scientific_ledger(
        _strict_canonical_json(scientific_path)
    )
    if (
        str(scientific_path) != closeout["scientific_ledger_before"]["path"]
        or _file_sha256(scientific_path)
        != closeout["scientific_ledger_before"]["sha256"]
        or scientific["state"] != "full_denominator_formed"
        or scientific["holdout_identity_sha256"]
        != closeout["holdout_identity_sha256"]
        or scientific["experiment_protocol_sha256"]
        != closeout["experiment_protocol_sha256"]
        or scientific["opening_release_root_sha256"]
        != closeout["opening_release"]["root_sha256"]
        or scientific["run_nonce"] != closeout["run_nonce"]
        or scientific["planned_arm_run_count"] != 1500
        or scientific["terminal_arm_run_count"] != 1500
        or scientific["terminal_artifact_root_sha256"] is not None
    ):
        raise ValueError("Fresh B4 scientific terminal source drifted")
    terminal = terminate_scientific_identity(
        scientific_path,
        expected_state="full_denominator_formed",
        success=False,
        terminal_artifact_root_sha256=closeout_root_sha256,
        terminal_reason=TERMINAL_REASON,
    )
    return {
        "status": "passed",
        "scientific_state": terminal["state"],
        "terminal_artifact_root_sha256": terminal[
            "terminal_artifact_root_sha256"
        ],
        "terminal_reason": terminal["terminal_reason"],
        "closeout_review_root_sha256": closeout_review_root_sha256,
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closeout-artifact", type=Path, required=True)
    parser.add_argument("--closeout-root-sha256", required=True)
    parser.add_argument("--closeout-review-artifact", type=Path, required=True)
    parser.add_argument("--closeout-review-root-sha256", required=True)
    parser.add_argument("--scientific-ledger-path", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    result = finalize(**vars(_arguments()))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
