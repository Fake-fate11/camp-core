from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


DIAGNOSTIC = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_first_state_diagnostic_bacc9d2a_3a72e639"
)
DIAGNOSTIC_ROOT = (
    "685c1529a95409f9f92220ac40d02c054d939bc93410e2ce4c0608e0e6dbffb8"
)
DIAGNOSTIC_REVIEW = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_first_state_diagnostic_review_bacc9d2a_3a72e639"
)
DIAGNOSTIC_REVIEW_ROOT = (
    "8767856884b6597668a22c9c3dc1db8aa3dfacce329d29fe5002b26fa77c95ca"
)
PREFLIGHT = Path(
    "/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c"
)
PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--fixed-dp", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
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
        materialize_source_audit,
        reconstruct_requested_latent,
    )

    if args.output.exists():
        raise RuntimeError("source audit output already exists")
    verify_complete_seal(args.contract, args.contract_root, label="source audit contract")
    verify_complete_seal(
        args.contract_review,
        args.contract_review_root,
        label="source audit contract review",
    )
    verify_complete_seal(DIAGNOSTIC, DIAGNOSTIC_ROOT, label="sealed first-state diagnostic")
    verify_complete_seal(
        DIAGNOSTIC_REVIEW,
        DIAGNOSTIC_REVIEW_ROOT,
        label="sealed first-state diagnostic review",
    )
    verify_complete_seal(PREFLIGHT, PREFLIGHT_ROOT, label="sealed calibration preflight")
    contract = json.loads((args.contract / "contract.json").read_text("utf-8"))
    receipt = json.loads(
        (DIAGNOSTIC / "precondition_receipt.json").read_text("utf-8")
    )
    preflight = json.loads((PREFLIGHT / "receipt.json").read_text("utf-8"))
    first_manifest = next(
        row
        for row in preflight["calibration_manifests"]
        if row["state_spec_id"] == "development_calibration:000"
    )
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
    source_texts = {
        key: path.read_text(encoding="utf-8")
        for key, path in source_paths.items()
    }
    candidate_bytes = (DIAGNOSTIC / "candidate_tensor.f32le").read_bytes()
    neighbor_bytes = (DIAGNOSTIC / "neighbor_tensor.f32le").read_bytes()
    report = materialize_source_audit(
        contract=contract,
        precondition_receipt=receipt,
        first_state_manifest=first_manifest,
        candidate_bytes=candidate_bytes,
        neighbor_bytes=neighbor_bytes,
        source_texts=source_texts,
    )
    report["contract_root_sha256"] = args.contract_root
    report["contract_review_root_sha256"] = args.contract_review_root
    report["diagnostic_root_sha256"] = DIAGNOSTIC_ROOT
    report["diagnostic_review_root_sha256"] = DIAGNOSTIC_REVIEW_ROOT
    report["preflight_root_sha256"] = PREFLIGHT_ROOT
    _latent, latent_bytes, _summary = reconstruct_requested_latent()
    staging = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=str(args.output.parent))
    )
    try:
        (staging / "report.json").write_bytes(canonical_json_bytes(report))
        (staging / "requested_latent_tensor.f32le").write_bytes(latent_bytes)
        (staging / "candidate_tensor.f32le").write_bytes(candidate_bytes)
        (staging / "neighbor_tensor.f32le").write_bytes(neighbor_bytes)
        (staging / "precondition_receipt.json").write_bytes(
            canonical_json_bytes(receipt)
        )
        (staging / "first_state_manifest.json").write_bytes(
            canonical_json_bytes(first_manifest)
        )
        sources_dir = staging / "sources"
        sources_dir.mkdir()
        for key, text in source_texts.items():
            (sources_dir / f"{key}.py").write_text(text, encoding="utf-8")
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
