from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import numpy as np


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CHECKPOINT_SHA256 = (
    "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
)
MODEL_SOURCE_SHA256 = (
    "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
)
AUTHORITY_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_authority_67308ac0_ed0d298c"
)
AUTHORITY_ROOT = (
    "bd6fee62418d062266e8f922d2f2dd3672ced115f9c1065e922db4b207054820"
)
PREFLIGHT_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c"
)
PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)
PREFLIGHT_REVIEW_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_review_67308ac0_ed0d298c"
)
PREFLIGHT_REVIEW_ROOT = (
    "ece7c80b6e764598ff867606f225a29a40f8ddededc641e7f22032b4b5d49ef3"
)
OLD_RAW_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_raw_67308ac0_ed0d298c"
)
OLD_RAW_REVIEW_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_raw_review_67308ac0_ed0d298c"
)
OLD_THRESHOLD_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_threshold_freeze_67308ac0_ed0d298c"
)
OLD_THRESHOLD_REVIEW_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_threshold_freeze_review_67308ac0_ed0d298c"
)
CONFIG_PATH = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_"
    "a53d6ee3_20260715T204719CST/prepared/probe_config.json"
)
DISK_FLOOR_BYTES = 10 * 1024**3


def _canonical(value: Any) -> bytes:
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


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _latent(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    value = np.zeros((8, 321, 81, 4), dtype=np.float32)
    value[1:] = rng.standard_normal(value.shape[1:]).astype(np.float32)
    return value


def _expanded_inputs(
    torch: Any,
    arrays: Mapping[str, np.ndarray],
    latent: np.ndarray,
    device: str,
) -> dict[str, Any]:
    expanded = {}
    for name, raw in arrays.items():
        tensor = torch.from_numpy(np.array(raw, copy=True)).to(device=device)
        expanded[name] = tensor.expand(8, *tensor.shape[1:]).contiguous()
    latent_tensor = torch.from_numpy(np.array(latent, copy=True)).to(
        device=device,
        dtype=expanded["sampled_trajectories"].dtype,
    )
    if tuple(latent_tensor.shape) != tuple(expanded["sampled_trajectories"].shape):
        raise ValueError("diagnostic latent shape drifted")
    expanded["sampled_trajectories"] = latent_tensor.contiguous()
    return expanded


def _forward_id(
    *,
    row_index: int,
    bindings: Mapping[str, Any],
    candidate_row_sha256: str,
    neighbor_row_sha256: str,
) -> str:
    return _sha_bytes(
        _canonical(
            {
                "state_spec_id": "development_calibration:000",
                "mode": "sequential_batch1_x8",
                "repeat_index": 0,
                "row_index": row_index,
                "input_manifest_sha256": bindings["input_manifest_sha256"],
                "actual_input_tensor_bundle_sha256": bindings[
                    "actual_input_tensor_bundle_sha256"
                ],
                "actual_state_sha256": bindings["actual_state_sha256"],
                "latent_tensor_sha256": bindings["latent_tensor_sha256"],
                "model_source_sha256": bindings["model_source_sha256"],
                "checkpoint_sha256": bindings["checkpoint_sha256"],
                "fixed_dp_head": bindings["fixed_dp_head"],
                "candidate_row_sha256": candidate_row_sha256,
                "neighbor_row_sha256": neighbor_row_sha256,
            }
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--fixed-dp", type=Path, required=True)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--prior-closeout", type=Path, required=True)
    parser.add_argument("--prior-closeout-root", required=True)
    parser.add_argument("--prior-closeout-review", type=Path, required=True)
    parser.add_argument("--prior-closeout-review-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review-output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    repo = args.repo.resolve()
    fixed_dp = args.fixed_dp.resolve()
    for path in (repo, repo / "camp_core", fixed_dp, fixed_dp / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from camp_core.integrations.diffusion_planner_artifact_seal import (
        seal_artifact,
        verify_complete_seal,
    )
    from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v5 import (
        adaptation_contract_v5,
    )
    from camp_core.integrations.diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic import (
        build_precondition_receipt,
        canonical_json_bytes,
        enforce_compound_gate_after_receipt,
        validate_diagnostic_contract,
        write_precondition_receipt_atomic,
    )
    from camp_core.integrations.diffusion_planner_v25_fair_pool_input_manifest_v2 import (
        materialize_latent_manifest,
        materialize_tensor_bundle,
    )
    from scripts.integrations.run_diffusion_planner_camp_replay import _load_model
    import torch

    if (
        args.output.exists()
        or args.review_output.exists()
        or _git(repo, "rev-parse", "HEAD") != args.implementation_head
        or _git(repo, "rev-parse", "refs/remotes/origin/main")
        != args.implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(fixed_dp, "status", "--porcelain=v1", "--untracked-files=no")
        or shutil.disk_usage(args.output.parent).free < DISK_FLOOR_BYTES
    ):
        raise RuntimeError("first-state diagnostic live authority drifted")
    if any(
        path.exists()
        for path in (
            OLD_RAW_DIR,
            OLD_RAW_REVIEW_DIR,
            OLD_THRESHOLD_DIR,
            OLD_THRESHOLD_REVIEW_DIR,
        )
    ):
        raise RuntimeError("old failed-attempt downstream artifact unexpectedly exists")
    verify_complete_seal(args.contract, args.contract_root, label="diagnostic contract")
    verify_complete_seal(
        args.contract_review,
        args.contract_review_root,
        label="diagnostic contract review",
    )
    verify_complete_seal(
        args.prior_closeout,
        args.prior_closeout_root,
        label="prior calibration hard-stop closeout",
    )
    verify_complete_seal(
        args.prior_closeout_review,
        args.prior_closeout_review_root,
        label="prior calibration hard-stop closeout review",
    )
    verify_complete_seal(AUTHORITY_DIR, AUTHORITY_ROOT, label="calibration authority")
    verify_complete_seal(PREFLIGHT_DIR, PREFLIGHT_ROOT, label="calibration preflight")
    verify_complete_seal(
        PREFLIGHT_REVIEW_DIR,
        PREFLIGHT_REVIEW_ROOT,
        label="calibration preflight review",
    )
    contract = json.loads((args.contract / "contract.json").read_text("utf-8"))
    validate_diagnostic_contract(contract)
    if (
        contract["implementation_head"] != args.implementation_head
        or contract["exact_dirs"]["diagnostic"] != str(args.output)
        or contract["exact_dirs"]["diagnostic_review"] != str(args.review_output)
        or _sha_file(Path(__file__)) != contract["producer_source_sha256"]
    ):
        raise RuntimeError("diagnostic contract/source binding drifted")

    preflight = json.loads((PREFLIGHT_DIR / "receipt.json").read_text("utf-8"))
    manifests = {
        row["state_spec_id"]: row for row in preflight["calibration_manifests"]
    }
    manifest = manifests["development_calibration:000"]
    with np.load(
        PREFLIGHT_DIR
        / "input_tensors"
        / "development_calibration_000.npz",
        allow_pickle=False,
    ) as archive:
        arrays = {
            name: np.array(archive[name], copy=True, order="C")
            for name in archive.files
        }
    tensor_manifest = materialize_tensor_bundle(
        arrays,
        source_scene_sha256=manifest["source_scene"]["source_scene_sha256"],
    )
    if tensor_manifest != manifest["actual_input_tensor_manifest"]:
        raise RuntimeError("diagnostic sealed input tensor bundle drifted")
    specs = (
        adaptation_contract_v5()["inherited_v4_contract"]["inherited_v3_contract"][
            "state_specifications"
        ]["development_calibration"]
    )
    spec = next(
        row for row in specs if row["state_spec_id"] == "development_calibration:000"
    )
    latent = _latent(int(spec["latent_seed"]))
    latent_manifest = materialize_latent_manifest(int(spec["latent_seed"]))
    if latent_manifest != manifest["actual_latent_tensor_manifest"]:
        raise RuntimeError("diagnostic sealed latent tensor drifted")

    config = json.loads(CONFIG_PATH.read_text("utf-8"))
    checkpoint = Path(config["fixed_dp"]["checkpoint"]["path"])
    args_json = Path(config["fixed_dp"]["args_json"]["path"])
    if _sha_file(checkpoint) != CHECKPOINT_SHA256:
        raise RuntimeError("diagnostic checkpoint drifted")
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("diagnostic CUDA unavailable")
    model, _model_args = _load_model(checkpoint, args_json, args.device)
    model.eval()
    model_source = Path(inspect.getsourcefile(model.__class__) or "")
    if not model_source.is_file() or _sha_file(model_source) != MODEL_SOURCE_SHA256:
        raise RuntimeError("diagnostic model source drifted")
    expanded = _expanded_inputs(torch, arrays, latent, args.device)
    predictions = []
    for row_index in range(8):
        row_inputs = {
            name: value[row_index : row_index + 1].contiguous()
            for name, value in expanded.items()
        }
        with torch.no_grad():
            _encoded, outputs = model(row_inputs)
        prediction = outputs["prediction"]
        if tuple(prediction.shape) != (1, 321, 80, 4):
            raise RuntimeError("diagnostic model output shape drifted")
        predictions.append(
            prediction[0].detach().cpu().numpy().astype(np.float32, copy=False)
        )
    prediction = np.stack(predictions).astype(np.float32, copy=False)
    candidate = np.ascontiguousarray(prediction[:, 0], dtype="<f4")
    neighbor = np.ascontiguousarray(prediction[:, 1:33], dtype="<f4")
    candidate_bytes = candidate.tobytes(order="C")
    neighbor_bytes = neighbor.tobytes(order="C")
    candidate_row_shas = [
        _sha_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in candidate
    ]
    neighbor_row_shas = [
        _sha_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in neighbor
    ]
    base_bindings: dict[str, Any] = {
        "input_manifest_sha256": manifest["manifest_sha256"],
        "actual_input_tensor_bundle_sha256": tensor_manifest["bundle_sha256"],
        "actual_state_sha256": manifest["actual_state_sha256"],
        "latent_tensor_sha256": latent_manifest["tensor_sha256"],
        "model_source_sha256": MODEL_SOURCE_SHA256,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "fixed_dp_head": FIXED_DP_HEAD,
    }
    base_bindings["forward_ids"] = [
        _forward_id(
            row_index=index,
            bindings=base_bindings,
            candidate_row_sha256=candidate_row_shas[index],
            neighbor_row_sha256=neighbor_row_shas[index],
        )
        for index in range(8)
    ]
    receipt = build_precondition_receipt(
        candidate=candidate,
        neighbor=neighbor,
        bindings=base_bindings,
    )

    staging = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=str(args.output.parent))
    )
    try:
        (staging / "candidate_tensor.f32le").write_bytes(candidate_bytes)
        (staging / "neighbor_tensor.f32le").write_bytes(neighbor_bytes)
        receipt_path = staging / "precondition_receipt.json"
        write_precondition_receipt_atomic(receipt_path, receipt)
        gate_exception = None
        try:
            enforce_compound_gate_after_receipt(receipt_path, receipt)
        except RuntimeError as error:
            if str(error) != "calibration K8 invalid":
                raise
            gate_exception = str(error)
        result_class = (
            "exact_k8_subcondition_resolved"
            if receipt["compound_gate_triggered"]
            else "compound_gate_not_reproduced_finite_unique_k8"
        )
        (staging / "report.json").write_bytes(
            canonical_json_bytes(
                {
                    "schema_version": (
                        "camp_dp_v25_fair_pool_calibration_first_state_"
                        "diagnostic_artifact_v1"
                    ),
                    "status": "diagnostic_completed_stop_before_selector",
                    "classification": result_class,
                    "compound_gate_triggered": receipt[
                        "compound_gate_triggered"
                    ],
                    "resolved_subconditions": receipt["resolved_subconditions"],
                    "gate_exception_after_receipt": gate_exception,
                    "receipt_formed_before_any_raise": True,
                    "state_spec_id": "development_calibration:000",
                    "mode": "sequential_batch1_x8",
                    "repeat_index": 0,
                    "model_call_count": 8,
                    "selector_call_count": 0,
                    "remaining_639_runs_executed": 0,
                    "threshold_materialized": False,
                    "validation_executed": False,
                    "fresh_or_holdout_executed": False,
                    "training_or_retraining_executed": False,
                    "raw_outcome_read": False,
                    "contract_root_sha256": args.contract_root,
                    "contract_review_root_sha256": args.contract_review_root,
                    "prior_closeout_root_sha256": args.prior_closeout_root,
                    "prior_closeout_review_root_sha256": (
                        args.prior_closeout_review_root
                    ),
                }
            )
        )
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
                "classification": result_class,
                "resolved_subconditions": receipt["resolved_subconditions"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
