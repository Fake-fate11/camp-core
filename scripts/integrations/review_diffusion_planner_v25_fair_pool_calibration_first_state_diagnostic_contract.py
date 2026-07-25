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
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if (
        args.output.exists()
        or _git(repo, "rev-parse", "HEAD") != args.implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("diagnostic contract review live authority drifted")
    sys.path.insert(0, str(repo / "camp_core"))
    from camp_core.integrations.diffusion_planner_artifact_seal import (
        seal_artifact,
        verify_complete_seal,
    )
    from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic_review import (
        review_contract_literal,
    )

    verify_complete_seal(
        args.contract,
        args.contract_root,
        label="first-state diagnostic contract",
    )
    contract = json.loads((args.contract / "contract.json").read_text("utf-8"))
    reviewer_path = (
        repo
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic_review.py"
    )
    if (
        hashlib.sha256(reviewer_path.read_bytes()).hexdigest()
        != contract["reviewer_source_sha256"]
    ):
        raise RuntimeError("independent diagnostic reviewer source drifted")
    result = review_contract_literal(contract)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=str(args.output.parent))
    )
    try:
        (staging / "review.json").write_bytes(_canonical(result))
        (staging / "report.json").write_bytes(
            _canonical(
                {
                    "schema_version": (
                        "camp_dp_v25_fair_pool_calibration_first_state_"
                        "diagnostic_contract_review_artifact_v1"
                    ),
                    "status": "passed",
                    "contract_root_sha256": args.contract_root,
                    "literal_contract_rebuilt": True,
                    "producer_metric_or_model_imported": False,
                    "implementation_head": args.implementation_head,
                }
            )
        )
        (staging / "HEADS.json").write_bytes(
            _canonical(
                {
                    "camp_head": args.implementation_head,
                    "fixed_dp_head": (
                        "7a1d33da277a1992ec474b5383a0c963c72e04e4"
                    ),
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
