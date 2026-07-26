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


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def _sha(path: Path) -> str:
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
    parser.add_argument("--contract-output", type=Path, required=True)
    parser.add_argument("--contract-review-output", type=Path, required=True)
    parser.add_argument("--focused-output", type=Path, required=True)
    parser.add_argument("--audit-output", type=Path, required=True)
    parser.add_argument("--audit-review-output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    fixed_dp = args.fixed_dp.resolve()
    sys.path.insert(0, str(repo / "camp_core"))
    from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
    from camp_core.integrations.diffusion_planner_v25_sequential_latent_source_audit import (
        canonical_json_bytes,
        source_audit_contract,
    )

    exact_dirs = {
        "contract": str(args.contract_output),
        "contract_review": str(args.contract_review_output),
        "focused": str(args.focused_output),
        "audit": str(args.audit_output),
        "audit_review": str(args.audit_review_output),
    }
    source_paths = {
        "camp_diagnostic_materializer": (
            repo
            / "scripts"
            / "integrations"
            / "materialize_diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic.py"
        ),
        "camp_input_manifest_v2": (
            repo
            / "camp_core"
            / "camp_core"
            / "integrations"
            / "diffusion_planner_v25_fair_pool_input_manifest_v2.py"
        ),
        "fixed_dp_model": (
            fixed_dp
            / "diffusion_planner"
            / "diffusion_planner"
            / "model"
            / "diffusion_planner.py"
        ),
        "fixed_dp_decoder": (
            fixed_dp
            / "diffusion_planner"
            / "diffusion_planner"
            / "model"
            / "module"
            / "decoder.py"
        ),
    }
    producer_script = (
        repo
        / "scripts"
        / "integrations"
        / "materialize_diffusion_planner_v25_sequential_latent_source_audit.py"
    )
    reviewer_script = (
        repo
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_v25_sequential_latent_source_audit.py"
    )
    if (
        args.contract_output.exists()
        or _git(repo, "rev-parse", "HEAD") != args.implementation_head
        or _git(repo, "rev-parse", "refs/remotes/origin/main")
        != args.implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(fixed_dp, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("source-audit contract live authority drifted")
    contract = source_audit_contract(
        implementation_head=args.implementation_head,
        exact_dirs=exact_dirs,
        source_sha256={key: _sha(path) for key, path in source_paths.items()},
        producer_source_sha256=_sha(producer_script),
        reviewer_source_sha256=_sha(reviewer_script),
    )
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{args.contract_output.name}.",
            dir=str(args.contract_output.parent),
        )
    )
    try:
        (staging / "contract.json").write_bytes(canonical_json_bytes(contract))
        (staging / "HEADS.json").write_bytes(
            canonical_json_bytes(
                {
                    "camp_head": args.implementation_head,
                    "camp_origin_main": args.implementation_head,
                    "camp_tracked_clean": True,
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "fixed_dp_tracked_clean": True,
                }
            )
        )
        (staging / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (staging / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(staging, label=args.contract_output.name)
        os.replace(staging, args.contract_output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({"root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
