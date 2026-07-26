"""Independently review the exact training-support input-only preflight."""

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
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_batch8_training_support_reference_review import (  # noqa: E402
    review_selected_manifest,
)


AUTHORITY_SHA = (
    "1c3f6c17db7c75883e7f1ffad447c5677dbbaaefa3eb9342dbbc069350dbf86c"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
LAYERS = ("route_geometry", "source", "state", "seed", "latent_instance")


def _bytes(value: Any) -> bytes:
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


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} is not SHA256")
    return value


def _tensor_manifest(arrays: Mapping[str, np.ndarray]) -> dict[str, Any]:
    rows = []
    for name in sorted(arrays):
        value = np.ascontiguousarray(np.asarray(arrays[name]))
        if (
            value.dtype.kind not in "biuf"
            or value.shape[0] != 1
            or not np.isfinite(value).all()
        ):
            raise ValueError("review input tensor invalid")
        rows.append(
            {
                "name": name,
                "dtype": value.dtype.str,
                "shape": list(value.shape),
                "tensor_sha256": _digest(value.tobytes(order="C")),
            }
        )
    result = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_actual_input_bundle_v1"
        ),
        "tensor_order": [row["name"] for row in rows],
        "tensors": rows,
    }
    result["bundle_sha256"] = _digest(_bytes(result))
    return result


def _review_entry(
    entry: Mapping[str, Any], pool: Path
) -> dict[str, Any]:
    if type(entry) is not dict:
        raise ValueError("review manifest entry must be object")
    payload = {key: value for key, value in entry.items() if key != "manifest_entry_sha256"}
    if _digest(_bytes(payload)) != entry.get("manifest_entry_sha256"):
        raise ValueError("review manifest entry SHA drifted")
    with np.load(pool / "model_input.npz", allow_pickle=False) as archive:
        arrays = {
            name: np.ascontiguousarray(np.asarray(archive[name]))
            for name in archive.files
        }
    if _tensor_manifest(arrays) != entry["actual_input_tensor_manifest"]:
        raise ValueError("review actual input bytes drifted")
    latent = np.frombuffer(
        (pool / "latent_tensor.f32le").read_bytes(), dtype="<f4"
    ).reshape(8, 321, 81, 4)
    latent_rows = [
        _digest(np.ascontiguousarray(row).tobytes(order="C"))
        for row in latent
    ]
    latent_manifest = entry["latent_manifest"]
    if (
        not np.isfinite(latent).all()
        or np.count_nonzero(latent[0]) != 0
        or len(set(latent_rows)) != 8
        or latent_rows != latent_manifest["row_sha256"]
        or _digest(latent.tobytes(order="C"))
        != latent_manifest["tensor_sha256"]
    ):
        raise ValueError("review latent bytes drifted")
    clone = entry["clone_payload"]
    if (
        clone
        != {
            "schema_version": (
                "camp_dp_v25_batch8_training_support_id_free_clone_payload_v2"
            ),
            "route_geometry_sha256": entry["source_record"][
                "route_geometry_sha256"
            ],
            "source_record_sha256": entry["source_record_sha256"],
            "scenario_seed": 25001,
            "actual_state_sha256": entry["actual_state_sha256"],
            "latent_instance_sha256": latent_manifest["manifest_sha256"],
        }
        or _digest(_bytes(clone)) != entry["clone_key_sha256"]
    ):
        raise ValueError("review clone payload drifted")
    if _json(pool / "causal_signal_atom_input.json") is None:
        raise ValueError("review causal signal evidence missing")
    with np.load(pool / "causal_input.npz", allow_pickle=False) as causal:
        if not causal.files:
            raise ValueError("review causal input bundle empty")
        for name in causal.files:
            value = np.asarray(causal[name])
            if value.dtype.kind not in "biuf" or not np.isfinite(value).all():
                raise ValueError("review causal input invalid")
    return {
        "pool_id": entry["pool_id"],
        "clone_key_sha256": entry["clone_key_sha256"],
        "actual_state_sha256": entry["actual_state_sha256"],
    }


def review(
    *,
    source: Path,
    source_root: str,
    contract_root: str,
    contract_review_root: str,
    output: Path,
) -> str:
    verify_complete_seal(
        source, source_root, label="V25 batch8 training-support input preflight"
    )
    report = _json(source / "report.json")
    manifest = _json(source / "manifest.json")
    eligible = _json(source / "eligible_manifest_entries.json")
    if (
        output.exists()
        or report.get("status")
        != "passed_before_first_training_support_model_call"
        or report.get("contract_root_sha256") != contract_root
        or report.get("contract_review_root_sha256") != contract_review_root
        or report.get("model_pool_selector_call_count_before_receipt") != 0
        or report.get("outcome_read") is not False
        or report.get("old_artifact_or_cas_write_count") != 0
        or report.get("eligible_manifest_entries_sha256")
        != _digest(_bytes(eligible))
    ):
        raise RuntimeError("review preflight producer invariant drifted")
    literal = review_selected_manifest(manifest, eligible_entries=eligible)
    reviewed = []
    for entry in manifest["entries"]:
        pool = source / "pools" / entry["pool_id"].replace(":", "_")
        reviewed.append(_review_entry(entry, pool))
    if (
        len(reviewed) != 1000
        or len({row["clone_key_sha256"] for row in reviewed}) != 1000
        or len({row["actual_state_sha256"] for row in reviewed}) != 1000
    ):
        raise ValueError("review selected denominator or state uniqueness drifted")
    overlap = report.get("zero_overlap")
    if type(overlap) is not dict or set(overlap) != {
        "development_calibration",
        "independent_validation",
        "legacy_nonholdout",
        "Fresh_B2",
        "Fresh_B3",
        "Fresh_B4",
    }:
        raise ValueError("review zero-overlap split registry drifted")
    for split, value in overlap.items():
        if (
            type(value) is not dict
            or set(value.get("intersection_counts", {})) != set(LAYERS)
            or any(value["intersection_counts"].values())
        ):
            raise ValueError(f"review overlap evidence failed for {split}")
    capacity = report.get("capacity")
    if (
        type(capacity) is not dict
        or capacity.get("passed") is not True
        or capacity.get("floor_bytes") != 10 * 1024**3
        or capacity.get("projected_end_free_bytes", -1)
        < capacity.get("floor_bytes", 0)
    ):
        raise ValueError("review capacity qualification drifted")
    review_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    result = {
        "schema_version": (
            "camp_dp_v25_batch8_training_support_reference_"
            "preflight_independent_review_v1"
        ),
        "status": "passed_independent_input_preflight_review",
        "reviewed_source_root_sha256": source_root,
        "reviewed_contract_root_sha256": contract_root,
        "reviewed_contract_review_root_sha256": contract_review_root,
        "authority_sha256": AUTHORITY_SHA,
        "manifest_review": literal,
        "reviewed_pool_count": len(reviewed),
        "reviewed_clone_key_count": len(
            {row["clone_key_sha256"] for row in reviewed}
        ),
        "reviewed_actual_state_count": len(
            {row["actual_state_sha256"] for row in reviewed}
        ),
        "zero_overlap": overlap,
        "capacity": capacity,
        "model_pool_selector_call_count": 0,
        "outcome_read": False,
        "old_artifact_or_cas_write_count": 0,
        "review_head": review_head,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_bytes(result))
        (staging / "HEADS.json").write_bytes(
            _bytes({"review_head": review_head, "fixed_dp_head": FIXED_DP_HEAD})
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(
            staging,
            label="V25 batch8 training-support preflight independent review",
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 batch8 training-support preflight independent review",
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        review(
            source=args.source,
            source_root=args.source_root,
            contract_root=args.contract_root,
            contract_review_root=args.contract_review_root,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
