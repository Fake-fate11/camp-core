"""Run exactly one same-ego B=8 model call and stop before every selector."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_batch8_first_state_diagnostic import (  # noqa: E402
    CHECKPOINT_SHA256,
    FIXED_DP_HEAD,
    MODEL_SOURCE_SHA256,
    STATE_SPEC_ID,
    build_diagnostic_receipt,
    canonical_bytes,
    expanded_input_summary,
    sha256_bytes,
    unique_latent,
    validate_contract,
)


OLD_PREFLIGHT_DIR = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c"
)
OLD_PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)
CONFIG_PATH = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_"
    "a53d6ee3_20260715T204719CST/prepared/probe_config.json"
)
DISK_FLOOR_BYTES = 10 * 1024**3


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain object")
    return value


def _load_old_input() -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    old_receipt = _json(OLD_PREFLIGHT_DIR / "receipt.json")
    manifest = next(
        row
        for row in old_receipt["calibration_manifests"]
        if row["state_spec_id"] == STATE_SPEC_ID
    )
    with np.load(
        OLD_PREFLIGHT_DIR
        / "input_tensors"
        / "development_calibration_000.npz",
        allow_pickle=False,
    ) as archive:
        arrays = {
            name: np.ascontiguousarray(np.array(archive[name], copy=True))
            for name in archive.files
        }
    return arrays, manifest


def _expand_inputs(
    arrays: dict[str, np.ndarray],
    latent: np.ndarray,
) -> dict[str, np.ndarray]:
    expanded: dict[str, np.ndarray] = {}
    for name, value in arrays.items():
        if value.shape[0] != 1:
            raise RuntimeError("sealed source input is not one ego state")
        expanded[name] = np.ascontiguousarray(
            np.repeat(value, 8, axis=0)
        )
    if "sampled_trajectories" not in expanded:
        raise RuntimeError("sealed sampled_trajectories missing")
    if expanded["sampled_trajectories"].shape != latent.shape:
        raise RuntimeError("expanded latent shape drifted")
    expanded["sampled_trajectories"] = np.ascontiguousarray(latent.copy())
    return expanded


def materialize(
    *,
    repo: Path,
    fixed_dp_repo: Path,
    implementation_head: str,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    preflight_dir: Path,
    preflight_root: str,
    preflight_review_dir: Path,
    preflight_review_root: str,
    output: Path,
    device: str,
) -> str:
    import torch

    from scripts.integrations.run_diffusion_planner_camp_replay import _load_model

    repo = repo.resolve()
    fixed_dp_repo = fixed_dp_repo.resolve()
    for import_root in (
        repo,
        repo / "camp_core",
        fixed_dp_repo,
        fixed_dp_repo / "diffusion_planner",
    ):
        if str(import_root) not in sys.path:
            sys.path.insert(0, str(import_root))
    if (
        output.exists()
        or _git(repo, "rev-parse", "HEAD") != implementation_head
        or _git(repo, "rev-parse", "refs/remotes/origin/main")
        != implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(
            fixed_dp_repo,
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
        )
        or shutil.disk_usage(output.parent).free < DISK_FLOOR_BYTES
    ):
        raise RuntimeError("batch8 diagnostic live authority drifted")
    for path, root, label in (
        (contract_dir, contract_root, "diagnostic contract"),
        (contract_review_dir, contract_review_root, "diagnostic contract review"),
        (preflight_dir, preflight_root, "diagnostic input preflight"),
        (
            preflight_review_dir,
            preflight_review_root,
            "diagnostic input preflight review",
        ),
        (OLD_PREFLIGHT_DIR, OLD_PREFLIGHT_ROOT, "sealed v5 input preflight"),
    ):
        verify_complete_seal(path, root, label=label)
    contract = validate_contract(_json(contract_dir / "contract.json"))
    if (
        contract["implementation_head"] != implementation_head
        or contract["exact_dirs"]["diagnostic"] != str(output)
        or _sha_file(Path(__file__))
        != contract["source_sha256"]["diagnostic_script"]
    ):
        raise RuntimeError("diagnostic contract/source binding drifted")
    preflight = _json(preflight_dir / "receipt.json")
    if (
        preflight.get("status") != "passed_before_first_batch8_model_call"
        or preflight.get("model_pool_selector_call_count_before_receipt") != 0
    ):
        raise RuntimeError("batch8 preflight did not authorize the one call")

    arrays, old_manifest = _load_old_input()
    new_manifest = preflight["new_manifest"]
    if (
        old_manifest["actual_input_tensor_manifest"]
        != new_manifest["actual_input_tensor_manifest"]
        or old_manifest["actual_state_sha256"]
        != new_manifest["actual_state_sha256"]
        or old_manifest["clone_key_sha256"] != new_manifest["clone_key_sha256"]
    ):
        raise RuntimeError("state/route/geometry changed across latent amendment")
    latent = unique_latent()
    if (
        sha256_bytes(latent.tobytes(order="C"))
        != new_manifest["actual_latent_tensor_manifest"]["tensor_sha256"]
    ):
        raise RuntimeError("unique latent manifest bytes drifted")
    expanded = _expand_inputs(arrays, latent)
    input_summary_before = expanded_input_summary(expanded, latent=latent)
    if input_summary_before["all_nonlatent_input_rows_exact_equal"] is not True:
        raise RuntimeError("expanded batch is not the same ego input")

    config = _json(CONFIG_PATH)
    checkpoint = Path(config["fixed_dp"]["checkpoint"]["path"])
    args_json = Path(config["fixed_dp"]["args_json"]["path"])
    if _sha_file(checkpoint) != CHECKPOINT_SHA256:
        raise RuntimeError("checkpoint drifted")
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    model, _model_args = _load_model(checkpoint, args_json, device)
    model.eval()
    model_source = Path(inspect.getsourcefile(model.__class__) or "")
    if not model_source.is_file() or _sha_file(model_source) != MODEL_SOURCE_SHA256:
        raise RuntimeError("fixed DP model source drifted")
    runtime = {
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "cuda": str(torch.version.cuda),
        "device": device,
        "device_name": (
            torch.cuda.get_device_name(torch.device(device))
            if device.startswith("cuda")
            else "cpu"
        ),
        "numpy": np.__version__,
    }
    runtime_sha = sha256_bytes(canonical_bytes(runtime))
    call_inputs = {
        name: torch.from_numpy(value.copy()).to(device=device)
        for name, value in expanded.items()
    }
    model_call_count = 0
    started_ns = time.perf_counter_ns()
    model_call_count += 1
    with torch.no_grad():
        _encoded, outputs = model(call_inputs)
    prediction = outputs["prediction"].detach().cpu().numpy()
    prediction = np.ascontiguousarray(prediction, dtype=np.float32)
    candidate = np.ascontiguousarray(prediction[:, 0], dtype=np.float32)
    neighbor = np.ascontiguousarray(prediction[:, 1:33], dtype=np.float32)
    latency_ns = time.perf_counter_ns() - started_ns
    if expanded_input_summary(expanded, latent=latent) != input_summary_before:
        raise RuntimeError("frozen expanded input mutated")

    base_bindings = {
        "input_manifest_sha256": new_manifest["manifest_sha256"],
        "actual_input_tensor_bundle_sha256": new_manifest[
            "actual_input_tensor_manifest"
        ]["bundle_sha256"],
        "actual_state_sha256": new_manifest["actual_state_sha256"],
        "latent_manifest_sha256": new_manifest[
            "actual_latent_tensor_manifest"
        ]["manifest_sha256"],
        "latent_tensor_sha256": new_manifest[
            "actual_latent_tensor_manifest"
        ]["tensor_sha256"],
        "model_source_sha256": MODEL_SOURCE_SHA256,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "fixed_dp_head": FIXED_DP_HEAD,
        "runtime_fingerprint_sha256": runtime_sha,
    }
    receipt = build_diagnostic_receipt(
        latent=latent,
        expanded_inputs=expanded,
        candidate=candidate,
        neighbor=neighbor,
        base_bindings=base_bindings,
        pool_generation_latency_ns=latency_ns,
        model_call_count=model_call_count,
        sequential_model_call_count=0,
        selector_call_count=0,
    )
    report = {
        "schema_version": (
            "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_"
            "artifact_v1"
        ),
        "status": "diagnostic_completed_stop_before_selector",
        "taxonomy": receipt["taxonomy"],
        "receipt_sha256": receipt["receipt_sha256"],
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "preflight_root_sha256": preflight_root,
        "preflight_review_root_sha256": preflight_review_root,
        "runtime": runtime,
        "formal_model_invocation_count": 1,
        "sequential_model_call_count": 0,
        "selector_call_count": 0,
        "source_ego_state_count": 1,
        "expanded_model_batch_size": 8,
        "agent_as_ego_batch": False,
        "remaining_calibration_run_count": 0,
        "threshold_validation_closed_loop_fresh_holdout_training_count": 0,
        "outcome_read": False,
        "old_artifact_cas_write_count": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "latent_tensor.f32le").write_bytes(latent.tobytes(order="C"))
        (staging / "candidate_tensor.f32le").write_bytes(
            candidate.tobytes(order="C")
        )
        (staging / "neighbor_tensor.f32le").write_bytes(
            neighbor.tobytes(order="C")
        )
        np.savez(staging / "expanded_input_tensors.npz", **expanded)
        receipt_path = staging / "receipt.json"
        receipt_path.write_bytes(canonical_bytes(receipt))
        with receipt_path.open("rb") as stream:
            os.fsync(stream.fileno())
        (staging / "report.json").write_bytes(canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "implementation_head": implementation_head,
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "tracked_clean": True,
                }
            )
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(staging, label="V25 batch8 first-state diagnostic")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 batch8 first-state diagnostic"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--preflight-review", type=Path, required=True)
    parser.add_argument("--preflight-review-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    print(
        materialize(
            repo=args.repo,
            fixed_dp_repo=args.fixed_dp_repo,
            implementation_head=args.implementation_head,
            contract_dir=args.contract,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review,
            contract_review_root=args.contract_review_root,
            preflight_dir=args.preflight,
            preflight_root=args.preflight_root,
            preflight_review_dir=args.preflight_review,
            preflight_review_root=args.preflight_review_root,
            output=args.output,
            device=args.device,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
