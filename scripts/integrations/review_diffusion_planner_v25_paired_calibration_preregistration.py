#!/usr/bin/env python3
"""Independently review the Fresh-closed V25 calibration preregistration."""

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


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_preregistration_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def review(
    *, preregistration_artifact: Path, preregistration_root_sha256: str, output_dir: Path
) -> str:
    artifact = preregistration_artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"calibration preregistration review exists: {output}")
    seal = verify_complete_seal(
        artifact,
        preregistration_root_sha256,
        label="V25 paired calibration preregistration",
    )
    actual = _canonical_json(artifact / "preregistration.json")
    roots = actual.get("root_artifacts")
    if type(roots) is not dict or set(roots) != set(ROOT_ROLES):
        raise ValueError("calibration preregistration root roles drifted")
    for role in ROOT_ROLES:
        binding = roots[role]
        verify_complete_seal(
            Path(binding["path"]),
            binding["root_sha256"],
            label=f"reviewed calibration preregistration {role}",
        )
    training = Path(roots["training"]["path"])
    training_review = Path(roots["training_review"]["path"])
    assets = load_v25_runtime_selector_assets(
        training_artifact=training,
        training_root_sha256=roots["training"]["root_sha256"],
        training_review_artifact=training_review,
        training_review_root_sha256=roots["training_review"]["root_sha256"],
    )
    models = {
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
    expected = freeze_paired_calibration_preregistration(
        root_artifacts=roots,
        zero_overlap_receipt=overlap,
        model_authority=models,
    )
    if not _strict_equal(actual, expected):
        raise ValueError("calibration preregistration differs from independent freeze")
    producer_report = _canonical_json(artifact / "report.json")
    if (
        producer_report.get("status")
        != "paired_calibration_preregistration_frozen"
        or producer_report.get("preregistration_sha256")
        != _sha256(artifact / "preregistration.json")
        or producer_report.get("root_artifacts") != roots
        or producer_report.get("model_authority") != models
        or producer_report.get("fresh_b2_opened") is not False
        or producer_report.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("calibration preregistration producer report drifted")
    output.mkdir(parents=True, exist_ok=False)
    _write_json(
        output / "report.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_independent_paired_calibration_preregistration_review",
            "camp_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "reviewed_artifact": str(artifact),
            "reviewed_root_sha256": seal["root_sha256"],
            "preregistration_sha256": _sha256(
                artifact / "preregistration.json"
            ),
            "all_root_artifacts_reopened": True,
            "model_authority_recomputed": True,
            "zero_overlap_recomputed": True,
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
    return seal_artifact(output, label="V25 paired calibration preregistration review")


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


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _git_head(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration-artifact", type=Path, required=True)
    parser.add_argument("--preregistration-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
