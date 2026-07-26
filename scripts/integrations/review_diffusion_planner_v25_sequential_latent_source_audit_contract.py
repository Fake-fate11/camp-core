from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    fixed_dp = args.fixed_dp.resolve()
    sys.path.insert(0, str(repo / "camp_core"))
    from camp_core.integrations.diffusion_planner_artifact_seal import (
        seal_artifact,
        verify_complete_seal,
    )
    from camp_core.integrations.diffusion_planner_v25_sequential_latent_source_audit import (
        canonical_json_bytes,
    )
    from camp_core.integrations.diffusion_planner_v25_sequential_latent_source_audit_review import (
        review_source_audit_contract,
    )

    if args.output.exists():
        raise RuntimeError("contract review output already exists")
    verify_complete_seal(args.contract, args.contract_root, label="source audit contract")
    contract = json.loads((args.contract / "contract.json").read_text("utf-8"))
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
    report = review_source_audit_contract(
        contract,
        expected_implementation_head=args.implementation_head,
        expected_exact_dirs=contract["exact_dirs"],
        expected_source_sha256={
            key: _sha(path) for key, path in source_paths.items()
        },
    )
    report["contract_root_sha256"] = args.contract_root
    staging = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=str(args.output.parent))
    )
    try:
        (staging / "report.json").write_bytes(canonical_json_bytes(report))
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
