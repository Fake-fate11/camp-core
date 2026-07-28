"""Fit V26 CAMP selector/adaptation layers from reviewed train-only B8 pools.

The entry never calls Diffusion Planner, alters its checkpoint, changes the
generator, or resamples a candidate pool.  It fits only Static/Scene 9D/14D
CAMP selector parameters and writes an ordinary development artifact.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v26_selector_adaptation import (  # noqa: E402
    ADAPTATION_ROLE,
    adapted_model_summary,
    adapted_parameter_arrays,
    build_adaptation_manifest,
    build_adaptation_receipt,
    load_adaptation_config,
    load_train_only_saved_pools,
    load_zero_shot_reference_assets,
    train_selector_adaptation,
)


MIN_FREE_BYTES = 10 * 1024**3


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, encoding="utf-8"
    ).strip()


def _tracked_changes(path: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=path,
            text=True,
            encoding="utf-8",
        ).strip()
    )


@contextmanager
def _exclusive_worker_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"V26 selector-adaptation worker lock already exists: {path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {"pid": os.getpid(), "role": ADAPTATION_ROLE},
                handle,
                sort_keys=True,
                separators=(",", ":"),
            )
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        path.unlink(missing_ok=True)


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _asset_binding(path: Path, expected_sha256: str, label: str) -> dict[str, str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"V26 adaptation {label} is missing: {resolved}")
    observed = _file_sha256(resolved)
    if observed != expected_sha256:
        raise ValueError(f"V26 adaptation {label} SHA256 drifted")
    return {"path": str(resolved), "sha256": observed}


def _prepare(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], Any, Any, Any]:
    if _tracked_changes(ROOT):
        raise ValueError("V26 adaptation requires an exact clean CAMP checkout")
    fixed_dp_repo = args.fixed_dp_repo.resolve()
    if _tracked_changes(fixed_dp_repo):
        raise ValueError("V26 adaptation requires an exact clean fixed-DP checkout")
    config = load_adaptation_config(args.config)
    pools = load_train_only_saved_pools(
        args.training_source, final_population_receipt_path=args.final_population_receipt
    )
    reference = load_zero_shot_reference_assets(args.reference_training)
    if _git_head(fixed_dp_repo) != pools.fixed_dp_head:
        raise ValueError("V26 adaptation fixed-DP head drifted")
    checkpoint = _asset_binding(
        args.fixed_dp_checkpoint, args.fixed_dp_checkpoint_sha256, "fixed-DP checkpoint"
    )
    fixed_dp_args = _asset_binding(
        args.fixed_dp_args, args.fixed_dp_args_sha256, "fixed-DP args"
    )
    manifest = build_adaptation_manifest(
        camp_head=_git_head(ROOT),
        config=config,
        data=pools,
        reference=reference,
        fixed_dp_checkpoint=checkpoint,
        fixed_dp_args=fixed_dp_args,
    )
    return manifest, config, pools, reference


def _write_adapted_assets(
    output_dir: Path, pools: Any, suite: Mapping[str, Any]
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, Any]]]:
    parameter_path = output_dir / "adapted_selector_parameters.npz"
    np.savez_compressed(parameter_path, **adapted_parameter_arrays(pools, suite))
    reports = adapted_model_summary(suite)
    report_path = output_dir / "adapted_model_reports.json"
    _atomic_write_json(report_path, reports)
    scales_path = output_dir / "adapted_runtime_atom_scales.json"
    _atomic_write_json(
        scales_path,
        {
            "schema_version": "camp_dp_v26_adapted_runtime_atom_scales_v1",
            "atom_count": 14,
            "scales": np.asarray(pools.training_scales, dtype=np.float64).tolist(),
            "scale_source": "reviewed_training_only_saved_pools",
            "outcome_or_fresh_consumed": False,
        },
    )
    static14_path = output_dir / "adapted_static14d_runtime_weights.npy"
    np.save(
        static14_path,
        np.asarray(suite["CAMP-Static14D"].theta[:, 0], dtype=np.float64),
    )
    assets = {
        "parameters": {
            "relative_path": parameter_path.name,
            "sha256": _file_sha256(parameter_path),
        },
        "model_reports": {
            "relative_path": report_path.name,
            "sha256": _file_sha256(report_path),
        },
        "runtime_atom_scales": {
            "relative_path": scales_path.name,
            "sha256": _file_sha256(scales_path),
        },
        "static14d_runtime_weights": {
            "relative_path": static14_path.name,
            "sha256": _file_sha256(static14_path),
        },
    }
    return assets, reports


def run(args: argparse.Namespace) -> Path:
    output_dir = args.output_dir.resolve()
    worker_lock = args.worker_lock.resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    if shutil.disk_usage(output_dir.parent).free < MIN_FREE_BYTES:
        raise RuntimeError("V26 adaptation output parent has less than 10 GiB free")
    with _exclusive_worker_lock(worker_lock):
        manifest, config, pools, reference = _prepare(args)
        output_dir.mkdir(parents=True)
        _atomic_write_json(output_dir / "manifest.json", manifest)
        _atomic_write_json(
            output_dir / "input_ledger.json",
            {
                "evidence_role": ADAPTATION_ROLE,
                "input_denominator": {
                    "planned": pools.record_count,
                    "complete": pools.record_count,
                    "failed": 0,
                    "unattempted": 0,
                },
                "training_rows_sha256": pools.rows_sha256,
                "model_dp_latent_generation_calls": 0,
            },
        )
        _atomic_write_json(
            output_dir / "run.status.json",
            {
                "evidence_role": ADAPTATION_ROLE,
                "status": "running_selector_adaptation",
                "model_dp_latent_generation_calls": 0,
                "fit_denominator": {"planned": 1, "complete": 0, "failed": 0, "unattempted": 0},
            },
        )
        try:
            suite = train_selector_adaptation(pools, config)
            assets, reports = _write_adapted_assets(output_dir, pools, suite)
            receipt = build_adaptation_receipt(
                manifest=manifest,
                fitted_models=reports,
                adapted_assets=assets,
                terminal_status="complete",
            )
            _atomic_write_json(output_dir / "receipt.json", receipt)
            _atomic_write_json(
                output_dir / "run.status.json",
                {
                    "evidence_role": ADAPTATION_ROLE,
                    "status": "complete_selector_adaptation",
                    "model_dp_latent_generation_calls": 0,
                    "fit_denominator": {
                        "planned": 1,
                        "complete": 1,
                        "failed": 0,
                        "unattempted": 0,
                    },
                },
            )
            (output_dir / "run.exit").write_text("0\n", encoding="ascii")
            return output_dir
        except BaseException as exc:
            failure = {"type": type(exc).__name__, "reason": str(exc)}
            receipt = build_adaptation_receipt(
                manifest=manifest,
                fitted_models={},
                adapted_assets={},
                terminal_status="typed_failure",
                failure=failure,
            )
            _atomic_write_json(output_dir / "receipt.json", receipt)
            _atomic_write_json(
                output_dir / "run.status.json",
                {
                    "evidence_role": ADAPTATION_ROLE,
                    "status": "typed_failure_selector_adaptation",
                    "failure": failure,
                    "model_dp_latent_generation_calls": 0,
                    "fit_denominator": {
                        "planned": 1,
                        "complete": 0,
                        "failed": 1,
                        "unattempted": 0,
                    },
                },
            )
            (output_dir / "run.exit").write_text("1\n", encoding="ascii")
            raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--worker-lock", type=Path, required=True)
    parser.add_argument("--training-source", type=Path, required=True)
    parser.add_argument("--final-population-receipt", type=Path, required=True)
    parser.add_argument("--reference-training", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--fixed-dp-checkpoint", type=Path, required=True)
    parser.add_argument("--fixed-dp-checkpoint-sha256", required=True)
    parser.add_argument("--fixed-dp-args", type=Path, required=True)
    parser.add_argument("--fixed-dp-args-sha256", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    output = run(parse_args(argv))
    print(json.dumps({"status": "complete", "output_dir": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
