#!/usr/bin/env python3
"""Freeze V25 paired-calibration thresholds and authorities before outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_calibration_preregistration import (  # noqa: E402
    ROOT_ROLES,
    freeze_paired_calibration_preregistration,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    build_signal_complete_execution_plan,
    validate_calibration_fresh_zero_overlap,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_preregistration_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def freeze(*, output_dir: Path, **values: Any) -> str:
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"calibration preregistration output exists: {output}")
    roots = _root_bindings(values)
    for role, binding in roots.items():
        verify_complete_seal(
            Path(binding["path"]),
            binding["root_sha256"],
            label=f"V25 calibration preregistration {role}",
        )
    training = Path(roots["training"]["path"])
    training_review = Path(roots["training_review"]["path"])
    assets = load_v25_runtime_selector_assets(
        training_artifact=training,
        training_root_sha256=roots["training"]["root_sha256"],
        training_review_artifact=training_review,
        training_review_root_sha256=roots["training_review"]["root_sha256"],
    )
    model_authority = {
        "model_registry_sha256": _sha256(training / "model_registry.json"),
        "training_scale_sha256": assets.atom_scales_sha256,
        "context_scaler_sha256": assets.scene14d_weight_provider.context_scaler_sha256,
        "atom_scales_file_sha256": assets.atom_scales_sha256,
        "static14d_weights_file_sha256": assets.static14d_weights_sha256,
        "scene14d_theta_sha256": assets.scene14d_weight_provider.theta_sha256,
    }
    overlap = validate_calibration_fresh_zero_overlap(
        build_signal_complete_execution_plan("calibration"),
        build_signal_complete_execution_plan("fresh_b2"),
    )
    payload = freeze_paired_calibration_preregistration(
        root_artifacts=roots,
        zero_overlap_receipt=overlap,
        model_authority=model_authority,
    )
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "preregistration.json", payload)
    _write_json(
        output / "report.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "paired_calibration_preregistration_frozen",
            "camp_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "preregistration_sha256": _sha256(output / "preregistration.json"),
            "root_artifacts": roots,
            "model_authority": model_authority,
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        },
    )
    (output / "HEADS").write_text(
        f"camp_head={_git_head(ROOT)}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 paired calibration preregistration")


def _root_bindings(values: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for role in ROOT_ROLES:
        artifact = Path(values.pop(f"{role}_artifact")).resolve()
        digest = values.pop(f"{role}_root_sha256")
        result[role] = {"path": str(artifact), "root_sha256": digest}
    if values:
        raise ValueError(f"unexpected calibration preregistration inputs: {sorted(values)}")
    return result


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"noncanonical JSON object: {path}")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for role in ROOT_ROLES:
        cli = role.replace("_", "-")
        parser.add_argument(f"--{cli}-artifact", type=Path, required=True)
        parser.add_argument(f"--{cli}-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = freeze(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
