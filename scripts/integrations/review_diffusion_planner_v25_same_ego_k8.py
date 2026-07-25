"""Independent review of the development/nonholdout same-ego K=8 artifact."""

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
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_target_architecture_review import (  # noqa: E402
    independently_review_capability,
)


def review(
    *,
    source: Path,
    source_root: str,
    contract: Path,
    contract_root: str,
    contract_review: Path,
    contract_review_root: str,
    fixed_dp_repo: Path,
    output: Path,
) -> str:
    verify_complete_seal(source, source_root, label="same-ego K8 capability")
    verify_complete_seal(contract, contract_root, label="architecture contract")
    verify_complete_seal(
        contract_review,
        contract_review_root,
        label="architecture contract review",
    )
    report = _object(source / "report.json")
    independently_review_capability(report)
    if report["authority"] != {
        "contract_path": str(contract.resolve()),
        "contract_root_sha256": contract_root,
        "contract_review_path": str(contract_review.resolve()),
        "contract_review_root_sha256": contract_review_root,
    }:
        raise ValueError("capability authority binding drifted")
    fixed = report["fixed_dp"]
    if (
        _git_head(fixed_dp_repo)
        != "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        or _tracked_changes(fixed_dp_repo)
        or _file_sha256(Path(fixed["checkpoint_path"]))
        != fixed["checkpoint_sha256"]
        or _file_sha256(Path(fixed["args_path"])) != fixed["args_sha256"]
    ):
        raise ValueError("live fixed DP authority drifted")
    expected_sources = {
        "model_source_sha256": (
            "diffusion_planner/diffusion_planner/model/diffusion_planner.py"
        ),
        "decoder_source_sha256": (
            "diffusion_planner/diffusion_planner/model/module/decoder.py"
        ),
        "encoder_source_sha256": (
            "diffusion_planner/diffusion_planner/model/module/encoder.py"
        ),
    }
    for field, relative in expected_sources.items():
        if _file_sha256(fixed_dp_repo / relative) != fixed[field]:
            raise ValueError(f"fixed DP {field} drifted")

    candidate = np.load(source / "candidate_tensor.npy", allow_pickle=False)
    sequential = np.load(
        source / "sequential_candidate_tensor.npy", allow_pickle=False
    )
    latent = np.load(source / "latent_tensor.npy", allow_pickle=False)
    if (
        candidate.shape != (8, 80, 4)
        or candidate.dtype != np.float32
        or sequential.shape != candidate.shape
        or latent.shape != (8, 321, 81, 4)
        or not np.all(np.isfinite(candidate))
        or not np.all(np.isfinite(sequential))
        or not np.all(np.isfinite(latent))
    ):
        raise ValueError("sealed tensor shape/dtype/finite contract drifted")
    primary = report["primary_pool_invocation"]
    row_sha = [_array_sha256(row) for row in candidate]
    if (
        _array_sha256(candidate) != primary["candidate_tensor_sha256"]
        or row_sha != primary["row_sha256"]
        or len(set(row_sha)) != 8
        or _array_sha256(latent) != report["latent"]["sha256"]
        or [_array_sha256(row) for row in latent]
        != report["latent"]["row_sha256"]
        or np.count_nonzero(latent[0]) != 0
    ):
        raise ValueError("sealed candidate/latent hashes drifted")
    errors = [
        float(
            np.max(
                np.abs(
                    candidate[index].astype(np.float64)
                    - sequential[index].astype(np.float64)
                )
            )
        )
        for index in range(8)
    ]
    if (
        not np.allclose(candidate, sequential, atol=1e-5, rtol=1e-5)
        or errors != report["batch_vs_sequential"]["per_row_max_abs_error"]
        or [_array_sha256(row) for row in sequential]
        != report["batch_vs_sequential"]["all_sequential_row_sha256"]
    ):
        raise ValueError("batch/sequential literal reconstruction failed")
    pairwise = [
        float(np.sqrt(np.mean((candidate[left] - candidate[right]) ** 2)))
        for left in range(8)
        for right in range(left + 1, 8)
    ]
    if (
        min(pairwise) != primary["pairwise_rms_min"]
        or max(pairwise) != primary["pairwise_rms_max"]
        or max(pairwise) <= 1e-6
    ):
        raise ValueError("candidate diversity reconstruction failed")
    pool_id = _canonical_sha256(
        {
            "tensor_sha256": primary["candidate_tensor_sha256"],
            "input_sha256": primary["input_sha256"],
            "model_sha256": fixed["checkpoint_sha256"],
            "forward_invocation_id": primary["forward_invocation_id"],
        }
    )
    if pool_id != primary["pool_id"]:
        raise ValueError("candidate pool ID reconstruction failed")
    arms = report["selector_after_pool"]["arms"]
    if any(
        arm["pool_id"] != pool_id
        or arm["candidate_tensor_sha256"] != primary["candidate_tensor_sha256"]
        or arm["input_sha256"] != primary["input_sha256"]
        or arm["model_sha256"] != fixed["checkpoint_sha256"]
        or arm["forward_invocation_id"] != primary["forward_invocation_id"]
        or arm["model_call_count_after_pool"] != 0
        or arm["latent_replacement_count_after_pool"] != 0
        or arm["trajectory_generation_count_after_pool"] != 0
        or arm["candidate_tensor_immutable"] is not True
        for arm in arms
    ):
        raise ValueError("selector-after-pool literal reconstruction failed")
    producer_source = (
        ROOT / "scripts/integrations/qualify_diffusion_planner_v25_same_ego_k8.py"
    ).read_text(encoding="utf-8")
    if (
        "_encoded, outputs = model(call_inputs)" not in producer_source
        or "value.detach().clone() for key, value in inputs.items()" not in producer_source
        or "latent_preimage_np = latent_preimage.detach().cpu().numpy().copy()"
        not in producer_source
        or "replay._predict_batch = direct_qualification" not in producer_source
        or '"simulator_steps_advanced": 0' not in producer_source
        or "qualify_selector_after_pool" not in producer_source
    ):
        raise ValueError("producer direct-formal-interface static proof drifted")
    reviewer_source = Path(__file__).read_text(encoding="utf-8")
    forbidden_import = (
        "diffusion_planner_v25_target_" + "architecture import"
    )
    if forbidden_import in reviewer_source:
        raise ValueError("reviewer imported producer metric/contract oracle")
    review_report = {
        "schema_version": (
            "camp_dp_v25_same_ego_single_invocation_k8_independent_review_v1"
        ),
        "status": "passed_independent_same_ego_single_invocation_k8_review",
        "source": {"path": str(source.resolve()), "root_sha256": source_root},
        "contract": {
            "path": str(contract.resolve()),
            "root_sha256": contract_root,
        },
        "contract_review": {
            "path": str(contract_review.resolve()),
            "root_sha256": contract_review_root,
        },
        "reviewer_role": "separate_literal_capability_reconstruction",
        "producer_capability_module_imported": False,
        "formal_fixed_dp_source_and_checkpoint_rehashed": True,
        "candidate_tensor_and_eight_rows_rehashed": True,
        "latent_tensor_and_eight_rows_rehashed": True,
        "batch_sequential_relation_rebuilt": True,
        "candidate_diversity_rebuilt": True,
        "pool_id_rebuilt": True,
        "selector_three_arm_zero_call_bindings_rebuilt": True,
        "same_ego_axis_verified": True,
        "agent_as_ego_batch_rejected": True,
        "simulator_steps_advanced": 0,
        "fresh_or_holdout_accessed": False,
        "training_executed": False,
        "claim_authorized": False,
        "review_head": _git_head(ROOT),
    }
    return _write_atomic(output, review_report)


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(_canonical_bytes(list(array.shape)))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "role": "same_ego_single_invocation_k8_review",
                    "review_head": report["review_head"],
                    "fixed_dp_head": (
                        "7a1d33da277a1992ec474b5383a0c963c72e04e4"
                    ),
                }
            )
        )
        root = seal_artifact(staging, label="V25 same-ego K8 review")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 same-ego K8 review")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=repo,
            text=True,
        ).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(review(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
