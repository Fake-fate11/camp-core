from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--audit-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    sys.path.insert(0, str(repo / "camp_core"))
    from camp_core.integrations.diffusion_planner_artifact_seal import (
        seal_artifact,
        verify_complete_seal,
    )
    from camp_core.integrations.diffusion_planner_v25_sequential_latent_source_audit import (
        canonical_json_bytes,
    )
    from camp_core.integrations.diffusion_planner_v25_sequential_latent_source_audit_review import (
        review_source_audit,
    )

    if args.output.exists():
        raise RuntimeError("source audit review output already exists")
    verify_complete_seal(args.contract, args.contract_root, label="source audit contract")
    verify_complete_seal(
        args.contract_review,
        args.contract_review_root,
        label="source audit contract review",
    )
    verify_complete_seal(args.audit, args.audit_root, label="source audit")
    contract = json.loads((args.contract / "contract.json").read_text("utf-8"))
    report = json.loads((args.audit / "report.json").read_text("utf-8"))
    receipt = json.loads(
        (args.audit / "precondition_receipt.json").read_text("utf-8")
    )
    manifest = json.loads(
        (args.audit / "first_state_manifest.json").read_text("utf-8")
    )
    source_texts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((args.audit / "sources").glob("*.py"))
    }
    reviewed = review_source_audit(
        contract=contract,
        audit_report=report,
        requested_latent_bytes=(
            args.audit / "requested_latent_tensor.f32le"
        ).read_bytes(),
        candidate_bytes=(args.audit / "candidate_tensor.f32le").read_bytes(),
        neighbor_bytes=(args.audit / "neighbor_tensor.f32le").read_bytes(),
        precondition_receipt=receipt,
        first_state_manifest=manifest,
        source_texts=source_texts,
    )
    reviewed["contract_root_sha256"] = args.contract_root
    reviewed["contract_review_root_sha256"] = args.contract_review_root
    reviewed["audit_root_sha256"] = args.audit_root
    staging = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=str(args.output.parent))
    )
    try:
        (staging / "report.json").write_bytes(canonical_json_bytes(reviewed))
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
