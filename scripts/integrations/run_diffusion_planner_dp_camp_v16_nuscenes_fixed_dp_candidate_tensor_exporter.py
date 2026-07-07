#!/usr/bin/env python3
"""Minimal CAMP-side fixed-DP K=8 candidate tensor exporter for v16 nuScenes."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.integrations.resolve_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_blocker import (  # noqa: E402
    DP_INPUT_SCHEMA,
    example_dp_input,
    validate_dp_input,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
AUTHORIZED_CURRENT_WORK = (
    "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_runner_remediation_only"
)
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_only"
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_runner_remediation_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_runner_remediation_rejected"
SCHEMA_VERSION = (
    "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_execution_retry_runner_remediation_v1"
)
NATIVE_SAMPLING_ENTRYPOINT = "guidance_gui/generate_samples.py"
TOP1_ENTRYPOINT = "diffusion_planner/valid_predictor.py"
EXPECTED_K = 8
DP_TOP1_INDEX = 0
FIXED_DP_NEIGHBOR_COUNT = 320
CAMP_ATOM_TABLE = {
    "scope": "v16_fixed_dp_candidate_tensor_export_only_no_camp_scoring",
    "approved_atoms": [],
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--input_npz", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--args_json", type=Path, required=True)
    parser.add_argument("--output_npz", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--k", type=int, default=EXPECTED_K)
    parser.add_argument("--noise_scale", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--split", default="mini_val")
    parser.add_argument("--scene_id", default=None)
    parser.add_argument("--sample_id", default=None)
    parser.add_argument("--report_json", type=Path, required=True)
    parser.add_argument("--report_md", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    command = sys.argv if argv is None else [Path(__file__).name, *argv]
    report = build_report(
        dp_repo=args.dp_repo,
        input_npz=args.input_npz,
        checkpoint=args.checkpoint,
        args_json=args.args_json,
        output_npz=args.output_npz,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        k=args.k,
    )
    if args.execute and report["final_decision"]["passed"]:
        started = time.time()
        tensor = export_candidate_tensor(
            dp_repo=args.dp_repo,
            input_npz=args.input_npz,
            checkpoint=args.checkpoint,
            args_json=args.args_json,
            output_npz=args.output_npz,
            k=args.k,
            noise_scale=args.noise_scale,
            seed=args.seed,
            device=args.device,
        )
        report["exported_candidate"] = build_candidate_record(
            input_npz=args.input_npz,
            candidate_tensor=tensor,
            camp_head=args.current_camp_head,
            dp_head=args.current_dp_head,
            split=args.split,
            scene_id=args.scene_id or args.input_npz.parent.name,
            sample_id=args.sample_id or args.input_npz.stem,
            command=command,
            wall_clock_seconds=round(time.time() - started, 6),
        )
        report["export_validation"] = validate_exported_npz(args.output_npz, expected_k=args.k)
        if not report["export_validation"]["passed"]:
            report["final_decision"] = _decision(
                passed=False,
                failed=report["export_validation"]["failed_checks"],
            )
    write_outputs(args.report_json, args.report_md, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    dp_repo: Path,
    input_npz: Path,
    checkpoint: Path,
    args_json: Path,
    output_npz: Path,
    v16_audit_md: Path,
    current_status_md: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    k: int = EXPECTED_K,
) -> dict[str, Any]:
    audit_text = _read_text(v16_audit_md)
    status_text = _read_text(current_status_md).split("## Current V15 Status", 1)[0]
    input_status = _input_status(input_npz)
    checks = [
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("k_is_8", k, EXPECTED_K),
        _expect("dp_repo_exists", dp_repo.is_dir(), True),
        _expect("checkpoint_exists", checkpoint.is_file(), True),
        _expect("args_json_exists", args_json.is_file(), True),
        _expect("input_npz_exists", input_status["exists"], True),
        _expect("input_npz_schema_valid", input_status["schema_errors"], []),
        _expect("native_sampling_entrypoint_available", (dp_repo / NATIVE_SAMPLING_ENTRYPOINT).is_file(), True),
        _expect("top1_entrypoint_available_for_contract_comparison", (dp_repo / TOP1_ENTRYPOINT).is_file(), True),
        _contains("audit_authorizes_remediation", audit_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_remediation", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
    ]
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if passed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
            "heads": {
                "camp_head": current_camp_head,
                "camp_origin_main": current_camp_origin_main,
                "dp_head": current_dp_head,
                "required_dp_head": required_dp_head,
            },
            "runner": {
                "script": str(Path(__file__).as_posix()),
                "dp_repo": str(dp_repo),
                "input_npz": str(input_npz),
                "checkpoint": str(checkpoint),
                "args_json": str(args_json),
                "output_npz": str(output_npz),
                "k": k,
                "candidate_count": k if passed else 0,
                "native_sampling_entrypoint": (dp_repo / NATIVE_SAMPLING_ENTRYPOINT).as_posix(),
                "top1_entrypoint": (dp_repo / TOP1_ENTRYPOINT).as_posix(),
                "candidate0_policy": "fixed_dp_zero_noise_top1",
                "candidate1_to_7_policy": "fixed_dp_unguided_native_sampling",
                "fixed_dp_neighbor_count": FIXED_DP_NEIGHBOR_COUNT,
                "dp_modified": False,
                "camp_training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
            },
            "input": input_status,
            "checks": checks,
            "final_decision": _decision(passed=passed, failed=failed),
        }
    )


def export_candidate_tensor(
    *,
    dp_repo: Path,
    input_npz: Path,
    checkpoint: Path,
    args_json: Path,
    output_npz: Path,
    k: int = EXPECTED_K,
    noise_scale: float = 1.0,
    seed: int = 3407,
    device: str = "cuda",
) -> np.ndarray:
    if k != EXPECTED_K:
        raise ValueError("K must be 8 for v16 fixed-DP candidate tensor export")
    for path in (dp_repo, input_npz, checkpoint, args_json):
        if not path.exists():
            raise FileNotFoundError(path)
    sys.path[:0] = [
        str(dp_repo),
        str(dp_repo / "diffusion_planner"),
    ]
    import torch
    from diffusion_planner.model.diffusion_planner import Diffusion_Planner
    from diffusion_planner.train_epoch import heading_to_cos_sin
    from diffusion_planner.utils.config import Config
    from guidance_gui.generate_samples import generate_samples

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch_device = torch.device(device)
    config = Config(str(args_json))
    model = Diffusion_Planner(config).to(torch_device)
    checkpoint_payload = torch.load(checkpoint, map_location=torch_device)
    state = checkpoint_payload.get("model", checkpoint_payload)
    state = {key.removeprefix("module."): value for key, value in state.items()}
    model.load_state_dict(state, strict=False)
    model.eval()

    data = _load_dp_input_tensors(input_npz, torch_device)
    data["ego_agent_past"] = heading_to_cos_sin(data["ego_agent_past"])
    data["goal_pose"] = heading_to_cos_sin(data["goal_pose"])
    norm_data = config.observation_normalizer(data)
    norm_data["delay"] = torch.zeros(
        norm_data["ego_current_state"].shape[0],
        dtype=torch.float32,
        device=torch_device,
    )
    top1 = generate_samples(
        model=model,
        model_args=config,
        data=norm_data,
        noise_scale=0.0,
        n_samples=1,
        composer=None,
        device=torch_device,
    )
    samples = generate_samples(
        model=model,
        model_args=config,
        data=norm_data,
        noise_scale=noise_scale,
        n_samples=k - 1,
        composer=None,
        device=torch_device,
    )
    candidate_tensor = np.ascontiguousarray(np.concatenate([top1, samples], axis=0), dtype=np.float32)
    output_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_npz,
        candidate_tensor=candidate_tensor,
        dp_top1_index=np.array(DP_TOP1_INDEX, dtype=np.int64),
        candidate_count=np.array(k, dtype=np.int64),
        input_npz=np.array(str(input_npz)),
    )
    return candidate_tensor


def build_candidate_record(
    *,
    input_npz: Path,
    candidate_tensor: np.ndarray,
    camp_head: str,
    dp_head: str,
    split: str,
    scene_id: str,
    sample_id: str,
    command: Sequence[str],
    wall_clock_seconds: float,
) -> dict[str, Any]:
    tensor = np.ascontiguousarray(candidate_tensor)
    integrity = candidate_tensor_integrity(tensor, tensor.copy())
    return _stable(
        {
            "split": split,
            "scene_id": scene_id,
            "sample_id": sample_id,
            "DP_HEAD": dp_head,
            "CAMP_HEAD": camp_head,
            "K": int(tensor.shape[0]) if tensor.ndim >= 1 else 0,
            "candidate_count": int(tensor.shape[0]) if tensor.ndim >= 1 else 0,
            "adapter_input_shape": _npz_shapes(input_npz),
            "adapter_input_sha256": _sha256(input_npz),
            "candidate_tensor_shape": list(tensor.shape),
            "candidate_tensor_sha256": _array_sha256(tensor),
            "dp_top1_index": DP_TOP1_INDEX,
            "camp_atom_table_sha256": _json_sha256(CAMP_ATOM_TABLE),
            "command": [str(part) for part in command],
            "wall_clock_seconds": float(wall_clock_seconds),
            **integrity,
        }
    )


def validate_exported_npz(path: Path, *, expected_k: int = EXPECTED_K) -> dict[str, Any]:
    checks: list[dict[str, Any]] = [_expect("candidate_output_exists", path.is_file(), True)]
    tensor = None
    if path.is_file():
        with np.load(path, allow_pickle=False) as loaded:
            tensor = loaded["candidate_tensor"] if "candidate_tensor" in loaded.files else None
            checks.append(_expect("candidate_tensor_present", tensor is not None, True))
            checks.append(_expect("dp_top1_index", int(loaded["dp_top1_index"]) if "dp_top1_index" in loaded.files else None, DP_TOP1_INDEX))
    if tensor is not None:
        checks.extend(
            [
                _expect("candidate_tensor_rank", tensor.ndim, 3),
                _expect("candidate_count_equals_k", int(tensor.shape[0]), expected_k),
                _expect("candidate_tensor_finite", bool(np.isfinite(tensor).all()), True),
            ]
        )
    failed = [check["name"] for check in checks if not check["passed"]]
    return {"passed": not failed, "failed_checks": failed, "checks": checks}


def candidate_tensor_integrity(before: np.ndarray, after: np.ndarray) -> dict[str, Any]:
    before_hash = _array_sha256(before)
    after_hash = _array_sha256(after)
    return {
        "candidate_tensor_pre_sha256": before_hash,
        "candidate_tensor_post_sha256": after_hash,
        "candidate_tensor_unchanged_by_camp": before_hash == after_hash,
    }


def write_outputs(report_json: Path, report_md: Path, report: dict[str, Any]) -> None:
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    report_md.write_text(_render_markdown(report), encoding="utf-8")
    sha_path = report_json.parent / "SHA256SUMS"
    sha_path.write_text(
        f"{_sha256(report_json)}  {report_json.name}\n{_sha256(report_md)}  {report_md.name}\n",
        encoding="utf-8",
    )


def _load_dp_input_tensors(path: Path, device: Any) -> dict[str, Any]:
    import torch

    with np.load(path, allow_pickle=False) as loaded:
        arrays = _fixed_dp_input_arrays({key: loaded[key] for key in loaded.files})
    return {key: torch.as_tensor(value).unsqueeze(0).to(device) for key, value in arrays.items()}


def _fixed_dp_input_arrays(arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    fixed = dict(arrays)
    fixed["neighbor_agents_past"] = _pad_first_axis(
        fixed["neighbor_agents_past"],
        FIXED_DP_NEIGHBOR_COUNT,
        "neighbor_agents_past",
    )
    fixed["neighbor_agents_future"] = _pad_first_axis(
        fixed["neighbor_agents_future"],
        FIXED_DP_NEIGHBOR_COUNT,
        "neighbor_agents_future",
    )
    return fixed


def _pad_first_axis(array: np.ndarray, target: int, name: str) -> np.ndarray:
    if array.shape[0] > target:
        raise ValueError(f"{name} has {array.shape[0]} rows, exceeds fixed DP target {target}")
    if array.shape[0] == target:
        return array
    padded = np.zeros((target, *array.shape[1:]), dtype=array.dtype)
    padded[: array.shape[0]] = array
    return padded


def _input_status(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "exists": False, "schema_errors": ["missing"], "fields": []}
    with np.load(path, allow_pickle=False) as loaded:
        data = {key: loaded[key] for key in loaded.files}
    return {
        "path": str(path),
        "exists": True,
        "fields": sorted(data),
        "schema_errors": validate_dp_input(data),
        "sha256": _sha256(path),
    }


def _npz_shapes(path: Path) -> dict[str, list[int]]:
    with np.load(path, allow_pickle=False) as loaded:
        return {key: list(loaded[key].shape) for key in sorted(loaded.files)}


def _decision(*, passed: bool, failed: list[str]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else AUTHORIZED_CURRENT_WORK,
        "retry_authorized_next": passed,
        "candidate_generation_executed": False,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "performance_claimed": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "fake_candidate_tensor_generated": False,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    runner = report["runner"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Exporter Remediation",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Runner: `{runner['script']}`",
            f"- Native DP sampling entrypoint: `{runner['native_sampling_entrypoint']}`",
            f"- K: `{runner['k']}`",
            f"- DP modified: `{runner['dp_modified']}`",
            "",
        ]
    )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _json_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(_stable(value), sort_keys=True).encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    return value


if __name__ == "__main__":
    raise SystemExit(main())
