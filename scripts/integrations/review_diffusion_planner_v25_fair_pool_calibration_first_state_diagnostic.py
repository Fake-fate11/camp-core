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
PREFLIGHT_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c"
)
PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)


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
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--diagnostic-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    fixed_dp = args.fixed_dp.resolve()
    if (
        args.output.exists()
        or _git(repo, "rev-parse", "HEAD") != args.implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(fixed_dp, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("diagnostic review live authority drifted")
    sys.path.insert(0, str(repo / "camp_core"))
    from camp_core.integrations.diffusion_planner_artifact_seal import (
        seal_artifact,
        verify_complete_seal,
    )
    from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic_review import (
        review_contract_literal,
        review_receipt_from_tensor_bytes,
    )

    verify_complete_seal(args.contract, args.contract_root, label="diagnostic contract")
    verify_complete_seal(
        args.contract_review,
        args.contract_review_root,
        label="diagnostic contract review",
    )
    verify_complete_seal(
        args.diagnostic, args.diagnostic_root, label="first-state diagnostic"
    )
    verify_complete_seal(
        PREFLIGHT_DIR, PREFLIGHT_ROOT, label="calibration input-only preflight"
    )
    contract = json.loads((args.contract / "contract.json").read_text("utf-8"))
    review_contract_literal(contract)
    if (
        contract["implementation_head"] != args.implementation_head
        or contract["exact_dirs"]["diagnostic"] != str(args.diagnostic)
        or contract["exact_dirs"]["diagnostic_review"] != str(args.output)
    ):
        raise RuntimeError("review exact-dir/implementation binding drifted")
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
        raise RuntimeError("reviewer source SHA drifted")
    receipt = json.loads(
        (args.diagnostic / "precondition_receipt.json").read_text("utf-8")
    )
    candidate_bytes = (args.diagnostic / "candidate_tensor.f32le").read_bytes()
    neighbor_bytes = (args.diagnostic / "neighbor_tensor.f32le").read_bytes()
    result = review_receipt_from_tensor_bytes(
        receipt,
        candidate_bytes=candidate_bytes,
        neighbor_bytes=neighbor_bytes,
    )
    preflight = json.loads((PREFLIGHT_DIR / "receipt.json").read_text("utf-8"))
    manifest = next(
        row
        for row in preflight["calibration_manifests"]
        if row["state_spec_id"] == "development_calibration:000"
    )
    bindings = receipt["bindings"]
    if (
        bindings["input_manifest_sha256"] != manifest["manifest_sha256"]
        or bindings["actual_input_tensor_bundle_sha256"]
        != manifest["actual_input_tensor_manifest"]["bundle_sha256"]
        or bindings["actual_state_sha256"] != manifest["actual_state_sha256"]
        or bindings["latent_tensor_sha256"]
        != manifest["actual_latent_tensor_manifest"]["tensor_sha256"]
        or bindings["fixed_dp_head"] != FIXED_DP_HEAD
    ):
        raise RuntimeError("review sealed preflight binding drifted")

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
                        "diagnostic_review_artifact_v1"
                    ),
                    "status": "passed",
                    "diagnostic_root_sha256": args.diagnostic_root,
                    "contract_root_sha256": args.contract_root,
                    "contract_review_root_sha256": args.contract_review_root,
                    "classification": (
                        "exact_k8_subcondition_resolved"
                        if result["compound_gate_triggered"]
                        else "compound_gate_not_reproduced_finite_unique_k8"
                    ),
                    "resolved_subconditions": result["resolved_subconditions"],
                    "model_call_count": 8,
                    "selector_call_count": 0,
                    "remaining_639_runs_executed": 0,
                    "threshold_materialized": False,
                    "validation_executed": False,
                    "fresh_or_holdout_executed": False,
                    "training_or_retraining_executed": False,
                    "raw_outcome_read": False,
                    "tensor_bytes_independently_rebuilt": True,
                    "producer_or_model_imported": False,
                }
            )
        )
        (staging / "HEADS.json").write_bytes(
            _canonical(
                {
                    "camp_head": args.implementation_head,
                    "fixed_dp_head": FIXED_DP_HEAD,
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
    print(
        json.dumps(
            {
                "root_sha256": root,
                "classification": (
                    "exact_k8_subcondition_resolved"
                    if result["compound_gate_triggered"]
                    else "compound_gate_not_reproduced_finite_unique_k8"
                ),
                "resolved_subconditions": result["resolved_subconditions"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
