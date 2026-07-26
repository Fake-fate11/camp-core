"""Run the sole authorized 320-call batch8 generator calibration."""

from __future__ import annotations

import argparse
import fcntl
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
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact, verify_complete_seal  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration import (  # noqa: E402
    AUTHORITY_SHA256, BASE_POINTER_HEAD, CANDIDATE_SHAPE, CAPACITY_FLOOR_BYTES,
    CHECKPOINT_SHA256, EXACT_DIRS, FIXED_DP_HEAD, MODEL_SOURCE_SHA256,
    NEIGHBOR_SHAPE, OUTPUT_DTYPE, canonical_bytes, sha256_bytes, sha256_file,
    tensor_summary,
)

CONFIG_PATH = Path("/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_a53d6ee3_20260715T204719CST/prepared/probe_config.json")
LOCK_PATH = Path("/root/autodl-tmp/.camp_dp_v25_batch8_generator_calibration.lock")


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _load_input(path: Path, latent_path: Path) -> tuple[dict[str, np.ndarray], np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        base = {name: np.ascontiguousarray(np.array(archive[name], copy=True)) for name in archive.files}
    latent = np.fromfile(latent_path, dtype="<f4").reshape((8, 321, 81, 4))
    expanded = {}
    for name, value in base.items():
        if value.shape[0] != 1:
            raise RuntimeError("source input is not a single ego state")
        expanded[name] = np.ascontiguousarray(np.repeat(value, 8, axis=0))
    if expanded["sampled_trajectories"].shape != latent.shape:
        raise RuntimeError("latent/input shape drifted")
    expanded["sampled_trajectories"] = np.ascontiguousarray(latent.copy())
    return expanded, latent


def _input_summary(inputs: dict[str, np.ndarray]) -> dict:
    result = {}
    for name, value in sorted(inputs.items()):
        array = np.ascontiguousarray(value)
        result[name] = {
            "shape": list(array.shape),
            "dtype": array.dtype.str,
            "tensor_sha256": sha256_bytes(array.tobytes(order="C")),
            "rows_exact_equal": (
                True if name == "sampled_trajectories"
                else all(np.array_equal(array[0], array[i]) for i in range(1, 8))
            ),
        }
    return result


def materialize(
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

    if output.exists():
        raise FileExistsError(output)
    if (
        _git(repo, "rev-parse", "HEAD") != implementation_head
        or _git(repo, "rev-parse", "refs/remotes/origin/main") != implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(fixed_dp_repo, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("live authority drifted")
    for path, root_sha, label in (
        (contract_dir, contract_root, "contract"),
        (contract_review_dir, contract_review_root, "contract review"),
        (preflight_dir, preflight_root, "preflight"),
        (preflight_review_dir, preflight_review_root, "preflight review"),
    ):
        verify_complete_seal(path, root_sha, label=label)
    if shutil.disk_usage(output.parent).free < CAPACITY_FLOOR_BYTES:
        raise RuntimeError("disk floor failed")
    preflight = json.loads((preflight_dir / "receipt.json").read_text("ascii"))
    if preflight["run_manifest_count"] != 320 or preflight["model_call_count"] != 0:
        raise RuntimeError("preflight denominator drifted")

    config = json.loads(CONFIG_PATH.read_text("utf-8"))
    checkpoint = Path(config["fixed_dp"]["checkpoint"]["path"])
    args_json = Path(config["fixed_dp"]["args_json"]["path"])
    if sha256_file(checkpoint) != CHECKPOINT_SHA256:
        raise RuntimeError("checkpoint drifted")
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable")
    model, _ = _load_model(checkpoint, args_json, device)
    model.eval()
    source_file = Path(inspect.getsourcefile(model.__class__) or "")
    if not source_file.is_file() or sha256_file(source_file) != MODEL_SOURCE_SHA256:
        raise RuntimeError("model source drifted")
    runtime = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": str(torch.__version__),
        "cuda": str(torch.version.cuda),
        "device": device,
        "device_name": torch.cuda.get_device_name(torch.device(device)) if device.startswith("cuda") else "cpu",
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "model_source_sha256": MODEL_SOURCE_SHA256,
    }
    runtime_sha = sha256_bytes(canonical_bytes(runtime))
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent))
    model_calls = 0
    completed = 0
    hard_failures = []
    slot_failures = []
    lock_stream = LOCK_PATH.open("w")
    try:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        (staging / "runs").mkdir()
        receipts = []
        for slot, manifest in enumerate(preflight["run_manifests"]):
            if shutil.disk_usage(output.parent).free < CAPACITY_FLOOR_BYTES:
                raise RuntimeError("disk floor crossed during acquisition")
            if _git(repo, "rev-parse", "HEAD") != implementation_head or _git(fixed_dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD:
                raise RuntimeError("source authority drifted during acquisition")
            inputs, latent = _load_input(
                preflight_dir / manifest["input_npz_relpath"],
                preflight_dir / manifest["latent_relpath"],
            )
            input_before = _input_summary(inputs)
            if any(not row["rows_exact_equal"] for name, row in input_before.items() if name != "sampled_trajectories"):
                raise RuntimeError("same-ego input batch drifted")
            call_inputs = {name: torch.from_numpy(value.copy()).to(device=device) for name, value in inputs.items()}
            forward_id = sha256_bytes(canonical_bytes({
                "authority_sha256": AUTHORITY_SHA256,
                "run_id": manifest["run_id"],
                "runtime_sha256": runtime_sha,
                "input_tensors": input_before,
            }))
            started = time.perf_counter_ns()
            model_calls += 1
            with torch.no_grad():
                _encoded, outputs = model(call_inputs)
            latency_ns = time.perf_counter_ns() - started
            prediction = np.ascontiguousarray(outputs["prediction"].detach().cpu().numpy(), dtype=OUTPUT_DTYPE)
            candidate = np.ascontiguousarray(prediction[:, 0], dtype=OUTPUT_DTYPE)
            neighbor = np.ascontiguousarray(prediction[:, 1:33], dtype=OUTPUT_DTYPE)
            if _input_summary(inputs) != input_before:
                raise RuntimeError("candidate input tensor mutated")
            csum = tensor_summary(candidate)
            nsum = tensor_summary(neighbor)
            reasons = []
            if candidate.shape != CANDIDATE_SHAPE or candidate.dtype != OUTPUT_DTYPE:
                reasons.append("candidate_shape_dtype")
            if csum["nonfinite_count"]:
                reasons.append("candidate_nonfinite")
            if csum["unique_row_sha256_count"] != 8:
                reasons.append("candidate_nondiverse")
            if neighbor.shape != NEIGHBOR_SHAPE or neighbor.dtype != OUTPUT_DTYPE:
                reasons.append("neighbor_shape_dtype")
            if nsum["nonfinite_count"]:
                reasons.append("neighbor_nonfinite")
            run_stage = staging / "runs" / f".{slot:03d}.staging.{uuid.uuid4().hex}"
            run_final = staging / "runs" / f"{slot:03d}"
            run_stage.mkdir()
            candidate.tofile(run_stage / "candidate.f32le")
            neighbor.tofile(run_stage / "neighbor.f32le")
            pool_id = sha256_bytes(canonical_bytes({
                "forward_id": forward_id,
                "candidate_tensor_sha256": csum["tensor_sha256"],
                "neighbor_tensor_sha256": nsum["tensor_sha256"],
            }))
            receipt = {
                "schema_version": "camp_dp_v25_batch8_generator_calibration_run_receipt_v1",
                "slot": slot,
                "run_id": manifest["run_id"],
                "state_index": manifest["state_index"],
                "repeat_index": manifest["repeat_index"],
                "state_spec_sha256": manifest["state_spec"]["state_spec_sha256"],
                "input_npz_sha256": manifest["input_npz_sha256"],
                "latent_manifest": manifest["latent_manifest"],
                "runtime": runtime,
                "runtime_sha256": runtime_sha,
                "forward_id": forward_id,
                "pool_id": pool_id,
                "formal_model_call_count": 1,
                "source_ego_state_count": 1,
                "expanded_batch_size": 8,
                "agent_as_ego_batch": False,
                "sequential_model_call_count": 0,
                "selector_call_count": 0,
                "post_pool_model_dp_latent_candidate_generation_call_count": 0,
                "candidate_relpath": f"runs/{slot:03d}/candidate.f32le",
                "neighbor_relpath": f"runs/{slot:03d}/neighbor.f32le",
                "candidate": csum,
                "neighbor": nsum,
                "candidate_tensor_immutable": True,
                "pool_generation_latency_ns": int(latency_ns),
                "status": "computed" if not reasons else "typed_failure_retained",
                "failure_reasons": reasons,
            }
            (run_stage / "receipt.json").write_bytes(canonical_bytes(receipt))
            os.replace(run_stage, run_final)
            receipts.append(receipt)
            completed += 1
            if reasons:
                slot_failures.append({"slot": slot, "run_id": manifest["run_id"], "reasons": reasons})
        if model_calls != 320 or completed != 320:
            raise RuntimeError("full denominator not formed")
        report = {
            "schema_version": "camp_dp_v25_batch8_generator_calibration_raw_v1",
            "status": "PASS_full_denominator" if not slot_failures else "FULL_DENOMINATOR_WITH_TYPED_FAILURES",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": implementation_head,
            "base_pointer_head": BASE_POINTER_HEAD,
            "fixed_dp_head": FIXED_DP_HEAD,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "preflight_root_sha256": preflight_root,
            "preflight_review_root_sha256": preflight_review_root,
            "runtime": runtime,
            "runtime_sha256": runtime_sha,
            "planned_run_count": 320,
            "completed_run_count": completed,
            "formal_model_call_count": model_calls,
            "sequential_model_call_count": 0,
            "selector_call_count": 0,
            "post_pool_call_count": 0,
            "slot_failure_count": len(slot_failures),
            "slot_failures": slot_failures,
            "hard_integrity_failure_count": len(hard_failures),
            "hard_integrity_failures": hard_failures,
            "outcome_read": False,
            "training_support_or_effect_endpoint_count": 0,
        }
        (staging / "report.json").write_bytes(canonical_bytes(report))
        root_sha = seal_artifact(staging, label="V25 batch8 generator calibration raw")
        os.replace(staging, output)
        verify_complete_seal(output, root_sha, label="V25 batch8 generator calibration raw")
        return root_sha
    except BaseException:
        # Once any model call occurred, preserve staging exactly for High.
        if model_calls == 0 and staging.exists():
            shutil.rmtree(staging)
        raise
    finally:
        try:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
        finally:
            lock_stream.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--fixed-dp-repo", type=Path, required=True)
    p.add_argument("--implementation-head", required=True)
    p.add_argument("--contract-dir", type=Path, default=Path(EXACT_DIRS["contract"]))
    p.add_argument("--contract-root", required=True)
    p.add_argument("--contract-review-dir", type=Path, default=Path(EXACT_DIRS["contract_review"]))
    p.add_argument("--contract-review-root", required=True)
    p.add_argument("--preflight-dir", type=Path, default=Path(EXACT_DIRS["preflight"]))
    p.add_argument("--preflight-root", required=True)
    p.add_argument("--preflight-review-dir", type=Path, default=Path(EXACT_DIRS["preflight_review"]))
    p.add_argument("--preflight-review-root", required=True)
    p.add_argument("--output", type=Path, default=Path(EXACT_DIRS["raw"]))
    p.add_argument("--device", default="cuda:0")
    a = p.parse_args()
    print(materialize(a.repo, a.fixed_dp_repo, a.implementation_head, a.contract_dir, a.contract_root, a.contract_review_dir, a.contract_review_root, a.preflight_dir, a.preflight_root, a.preflight_review_dir, a.preflight_review_root, a.output, a.device))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
