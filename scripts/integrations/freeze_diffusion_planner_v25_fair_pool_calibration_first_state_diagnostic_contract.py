from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def _canonical(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--fixed-dp", type=Path, required=True)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract-review-dir", required=True)
    parser.add_argument("--focused-dir", required=True)
    parser.add_argument("--diagnostic-dir", required=True)
    parser.add_argument("--diagnostic-review-dir", required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    fixed_dp = args.fixed_dp.resolve()
    if (
        args.output.exists()
        or _git(repo, "rev-parse", "HEAD") != args.implementation_head
        or _git(repo, "rev-parse", "refs/remotes/origin/main")
        != args.implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp, "rev-parse", "HEAD")
        != "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        or _git(fixed_dp, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("diagnostic contract live authority drifted")
    sys.path.insert(0, str(repo / "camp_core"))
    from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
    from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic import (
        diagnostic_contract,
        validate_diagnostic_contract,
    )

    producer = (
        repo
        / "scripts"
        / "integrations"
        / "materialize_diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic.py"
    )
    reviewer = (
        repo
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic_review.py"
    )
    contract = diagnostic_contract(
        implementation_head=args.implementation_head,
        exact_dirs={
            "contract": str(args.output),
            "contract_review": args.contract_review_dir,
            "focused": args.focused_dir,
            "diagnostic": args.diagnostic_dir,
            "diagnostic_review": args.diagnostic_review_dir,
        },
        producer_source_sha256=_sha_file(producer),
        reviewer_source_sha256=_sha_file(reviewer),
    )
    validate_diagnostic_contract(contract)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=str(args.output.parent))
    )
    try:
        (staging / "contract.json").write_bytes(_canonical(contract))
        (staging / "report.json").write_bytes(
            _canonical(
                {
                    "schema_version": (
                        "camp_dp_v25_fair_pool_calibration_first_state_"
                        "diagnostic_contract_artifact_v1"
                    ),
                    "status": (
                        "outcome_independent_first_state_diagnostic_contract_frozen"
                    ),
                    "high_authority_sha256": contract["high_authority_sha256"],
                    "implementation_head": args.implementation_head,
                    "remaining_639_runs_authorized": False,
                    "selector_call_count": 0,
                    "threshold_materialization_authorized": False,
                    "validation_authorized": False,
                    "fresh_or_holdout_authorized": False,
                    "training_or_retraining_authorized": False,
                    "raw_outcome_read": False,
                }
            )
        )
        (staging / "HEADS.json").write_bytes(
            _canonical(
                {
                    "camp_head": args.implementation_head,
                    "camp_origin_main": args.implementation_head,
                    "camp_tracked_clean": True,
                    "fixed_dp_head": (
                        "7a1d33da277a1992ec474b5383a0c963c72e04e4"
                    ),
                    "fixed_dp_tracked_clean": True,
                }
            )
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (staging / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(staging, label=args.output.name)
        os.replace(staging, args.output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({"root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
