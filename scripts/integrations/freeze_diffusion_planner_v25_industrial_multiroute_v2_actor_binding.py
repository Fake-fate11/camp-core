from __future__ import annotations

import argparse
import hashlib
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
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_evaluation_actor_binding import (  # noqa: E402
    AFFECTED_LEAF_SET_SHA256,
    AUTHORITY_SHA256,
    EXECUTION_REVIEW_ROOT_SHA256,
    EXECUTION_ROOT_SHA256,
    INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256,
    INDUSTRIAL_CAPABILITY_ROOT_SHA256,
    INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256,
    INDUSTRIAL_CONTRACT_ROOT_SHA256,
    SUPERSEDED_EVALUATION_ROOT_SHA256,
    continuation_sha256,
    correction_contract,
    exact_dirs,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    object_from,
    write_atomic,
)


EXPECTED_REVIEWER_STDERR_SHA256 = (
    "b6f6b4b29f50c0020c9ef65116f69ede3aa3c6b5148043272019f3816c48f124"
)
EXPECTED_FIRST_REJECTION = (
    "cluster0/safety.collision_any/pool_matched_candidate0 reason type drifted"
)


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def freeze_closeout(
    *,
    output: Path,
    implementation_head: str,
    superseded_evaluation_dir: Path,
    reviewer_stderr: Path,
) -> str:
    continuation = continuation_sha256(implementation_head)
    dirs = exact_dirs(implementation_head, continuation)
    if output.resolve() != Path(dirs["failure_closeout"]):
        raise ValueError("failure closeout exact dir drifted")
    old = _verify(
        superseded_evaluation_dir,
        SUPERSEDED_EVALUATION_ROOT_SHA256,
        "superseded evaluation",
    )
    stderr_sha = _sha_file(reviewer_stderr)
    if stderr_sha != EXPECTED_REVIEWER_STDERR_SHA256:
        raise ValueError("failed reviewer stderr SHA drifted")
    stderr_text = reviewer_stderr.read_text(encoding="utf-8", errors="replace")
    if EXPECTED_FIRST_REJECTION not in stderr_text:
        raise ValueError("failed reviewer first rejection drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_failure_closeout_v1"
        ),
        "status": "attempt_stopped_engineering_recoverable",
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "continuation_sha256": continuation,
        "exact_dirs": dirs,
        "classification": (
            "full_denominator_evaluation_sealed_actor_binding_"
            "consumer_wiring_failure"
        ),
        "superseded_evaluation_root_sha256": (
            SUPERSEDED_EVALUATION_ROOT_SHA256
        ),
        "superseded_evaluation_schema_version": old.get("schema_version"),
        "accepted_scientific_result": False,
        "review_artifact_formed": False,
        "first_rejection": EXPECTED_FIRST_REJECTION,
        "reviewer_stderr_sha256": stderr_sha,
        "execution_root_sha256": EXECUTION_ROOT_SHA256,
        "execution_review_root_sha256": EXECUTION_REVIEW_ROOT_SHA256,
        "frozen_denominator": {
            "clusters": 100,
            "arms": 300,
            "ticks": 19_200,
        },
        "execution_or_model_rerun": False,
        "old_evaluation_overwritten_or_countersigned": False,
        "effect_or_outcome_used_to_choose_fix": False,
        "scientific_block": False,
        "project_terminal": False,
        "five_class_flow_policy": True,
        "claim_authorized": False,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "evaluation_actor_binding_failure_closeout",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": implementation_head,
            "superseded_evaluation_root_sha256": (
                SUPERSEDED_EVALUATION_ROOT_SHA256
            ),
        },
        label="V25 multiroute-v2 evaluation failure closeout",
    )


def freeze_contract(
    *,
    output: Path,
    implementation_head: str,
    failure_closeout_dir: Path,
    failure_closeout_root: str,
    failure_closeout_review_dir: Path,
    failure_closeout_review_root: str,
    execution_dir: Path,
    execution_review_dir: Path,
    superseded_evaluation_dir: Path,
    industrial_contract_dir: Path,
    industrial_contract_review_dir: Path,
    industrial_capability_dir: Path,
    industrial_capability_review_dir: Path,
) -> str:
    continuation = continuation_sha256(implementation_head)
    dirs = exact_dirs(implementation_head, continuation)
    if output.resolve() != Path(dirs["correction_contract"]):
        raise ValueError("correction contract exact dir drifted")
    _verify(failure_closeout_dir, failure_closeout_root, "failure closeout")
    _verify(
        failure_closeout_review_dir,
        failure_closeout_review_root,
        "failure closeout review",
    )
    _verify(execution_dir, EXECUTION_ROOT_SHA256, "sealed execution")
    _verify(
        execution_review_dir,
        EXECUTION_REVIEW_ROOT_SHA256,
        "sealed execution review",
    )
    _verify(
        superseded_evaluation_dir,
        SUPERSEDED_EVALUATION_ROOT_SHA256,
        "superseded evaluation",
    )
    _verify(
        industrial_contract_dir,
        INDUSTRIAL_CONTRACT_ROOT_SHA256,
        "industrial v3 contract",
    )
    _verify(
        industrial_contract_review_dir,
        INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256,
        "industrial v3 contract review",
    )
    _verify(
        industrial_capability_dir,
        INDUSTRIAL_CAPABILITY_ROOT_SHA256,
        "industrial v3 capability matrix",
    )
    _verify(
        industrial_capability_review_dir,
        INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256,
        "industrial v3 capability matrix review",
    )
    contract = correction_contract(
        implementation_head, continuation=continuation
    )
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_correction_contract_artifact_v1"
        ),
        "status": "outcome_independent_correction_contract_frozen",
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "continuation_sha256": continuation,
        "exact_dirs": dirs,
        "failure_closeout_root_sha256": failure_closeout_root,
        "failure_closeout_review_root_sha256": failure_closeout_review_root,
        "industrial_roots": {
            "contract": INDUSTRIAL_CONTRACT_ROOT_SHA256,
            "contract_review": INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256,
            "capability": INDUSTRIAL_CAPABILITY_ROOT_SHA256,
            "capability_review": INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256,
        },
        "affected_leaf_set_sha256": AFFECTED_LEAF_SET_SHA256,
        "contract": contract,
        "model_dp_latent_pool_selector_execution_calls": 0,
        "claim_authorized": False,
        "five_class_flow_policy": True,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "evaluation_actor_binding_correction_contract",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": implementation_head,
            "affected_leaf_set_sha256": AFFECTED_LEAF_SET_SHA256,
        },
        label="V25 multiroute-v2 actor-binding correction contract",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    closeout = sub.add_parser("failure-closeout")
    closeout.add_argument("--output", type=Path, required=True)
    closeout.add_argument("--implementation-head", required=True)
    closeout.add_argument(
        "--superseded-evaluation-dir", type=Path, required=True
    )
    closeout.add_argument("--reviewer-stderr", type=Path, required=True)

    contract = sub.add_parser("contract")
    contract.add_argument("--output", type=Path, required=True)
    contract.add_argument("--implementation-head", required=True)
    for name in (
        "failure-closeout-dir",
        "failure-closeout-review-dir",
        "execution-dir",
        "execution-review-dir",
        "superseded-evaluation-dir",
        "industrial-contract-dir",
        "industrial-contract-review-dir",
        "industrial-capability-dir",
        "industrial-capability-review-dir",
    ):
        contract.add_argument(f"--{name}", type=Path, required=True)
    contract.add_argument("--failure-closeout-root", required=True)
    contract.add_argument("--failure-closeout-review-root", required=True)
    args = parser.parse_args()
    if args.command == "failure-closeout":
        root = freeze_closeout(
            output=args.output,
            implementation_head=args.implementation_head,
            superseded_evaluation_dir=args.superseded_evaluation_dir,
            reviewer_stderr=args.reviewer_stderr,
        )
    else:
        root = freeze_contract(
            output=args.output,
            implementation_head=args.implementation_head,
            failure_closeout_dir=args.failure_closeout_dir,
            failure_closeout_root=args.failure_closeout_root,
            failure_closeout_review_dir=args.failure_closeout_review_dir,
            failure_closeout_review_root=args.failure_closeout_review_root,
            execution_dir=args.execution_dir,
            execution_review_dir=args.execution_review_dir,
            superseded_evaluation_dir=args.superseded_evaluation_dir,
            industrial_contract_dir=args.industrial_contract_dir,
            industrial_contract_review_dir=args.industrial_contract_review_dir,
            industrial_capability_dir=args.industrial_capability_dir,
            industrial_capability_review_dir=args.industrial_capability_review_dir,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
