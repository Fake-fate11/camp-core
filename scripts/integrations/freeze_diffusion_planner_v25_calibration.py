#!/usr/bin/env python3
"""Seal the V25 candidate0-only calibration freeze before Fresh B2 opens."""

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
from camp_core.integrations.diffusion_planner_v25_calibration_artifact import (  # noqa: E402
    build_calibration_freeze_payload_from_corpus,
    validate_calibration_freeze_payload,
)
from camp_core.integrations.diffusion_planner_v25_calibration_corpus import (  # noqa: E402
    validate_candidate0_calibration_corpus,
)


SCHEMA_VERSION = "camp_dp_v25_calibration_freeze_artifact_v2"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def build(
    *,
    inputs_path: Path,
    calibration_artifact: Path,
    calibration_root_sha256: str,
    calibration_review_artifact: Path,
    calibration_review_root_sha256: str,
    output_dir: Path,
) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    inputs = _canonical_json(inputs_path)
    calibration_root = calibration_artifact.resolve()
    calibration_review_root = calibration_review_artifact.resolve()
    verify_complete_seal(
        calibration_root,
        calibration_root_sha256,
        label="candidate0 calibration execution",
    )
    verify_complete_seal(
        calibration_review_root,
        calibration_review_root_sha256,
        label="candidate0 calibration execution review",
    )
    if (
        (calibration_root / "run.exit").read_bytes() != b"0\n"
        or (calibration_review_root / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("candidate0 calibration execution/review exit drifted")
    calibration_corpus = validate_candidate0_calibration_corpus(
        _canonical_json(calibration_root / "calibration_corpus.json")
    )
    calibration_review = _canonical_json(calibration_review_root / "report.json")
    expected_fields = {
        "schema_version",
        "root_bindings",
        "inventory",
        "frozen_model_registry_sha256",
        "training_scale_sha256",
        "context_scaler_sha256",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
    }
    if (
        set(inputs) != expected_fields
        or inputs.get("schema_version")
        != "camp_dp_v25_calibration_freeze_inputs_v1"
        or inputs.get("fresh_b2_opened") is not False
        or inputs.get("fresh_outcome_fields_consumed") != []
        or inputs["root_bindings"].get("calibration_corpus_root")
        != calibration_root_sha256
        or inputs["root_bindings"].get("calibration_review_root")
        != calibration_review_root_sha256
        or calibration_review.get("status")
        != "passed_independent_candidate0_calibration_execution_review"
        or calibration_review.get("reviewed_root_sha256")
        != calibration_root_sha256
        or calibration_review.get("fresh_b2_opened") is not False
        or calibration_review.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("calibration freeze input authority drifted")
    output_dir.mkdir(parents=True)
    try:
        payload = validate_calibration_freeze_payload(
            build_calibration_freeze_payload_from_corpus(
                root_bindings=inputs["root_bindings"],
                calibration_corpus=calibration_corpus,
                frozen_model_registry_sha256=inputs[
                    "frozen_model_registry_sha256"
                ],
                training_scale_sha256=inputs["training_scale_sha256"],
                context_scaler_sha256=inputs["context_scaler_sha256"],
            )
        )
        if payload["inventory"] != inputs["inventory"]:
            raise ValueError("calibration freeze inventory differs from reviewed corpus")
        _write_json(output_dir / "calibration_freeze.json", payload)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": payload["status"],
            "camp_head": _git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "inputs_path": str(inputs_path.resolve()),
            "inputs_sha256": _sha256(inputs_path),
            "calibration_artifact": str(calibration_root),
            "calibration_root_sha256": calibration_root_sha256,
            "calibration_review_artifact": str(calibration_review_root),
            "calibration_review_root_sha256": calibration_review_root_sha256,
            "calibration_freeze_sha256": _sha256(
                output_dir / "calibration_freeze.json"
            ),
            "candidate0_row_count": payload["candidate0_row_count"],
            "heterogeneity_cluster_count": payload[
                "noninferiority_resolvability"
            ]["heterogeneity_cluster_count"],
            "repeatability_status": payload["noninferiority_resolvability"][
                "repeatability_status"
            ],
            "exact_duplicate_repeatability_group_count": payload[
                "noninferiority_resolvability"
            ]["exact_duplicate_group_count"],
            "margin_enlargement_authorized": False,
            "camp_method_outcomes_consumed": False,
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
            "fresh_open_authorized": False,
        }
        _write_json(output_dir / "report.json", report)
        (output_dir / "HEADS").write_bytes(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode()
        )
        (output_dir / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
        (output_dir / "run.exit").write_bytes(b"0\n")
        return seal_artifact(output_dir, label="V25 calibration freeze")
    except BaseException as exc:
        _write_json(
            output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (output_dir / "run.exit").write_bytes(b"1\n")
        seal_artifact(output_dir, label="failed V25 calibration freeze")
        raise


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=no"],
            text=True,
        ).strip()
    )


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError("calibration authority JSON must be a mapping")
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    expected = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()
    if raw != expected:
        raise ValueError("calibration authority JSON is not canonical")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--calibration-artifact", type=Path, required=True)
    parser.add_argument("--calibration-root-sha256", required=True)
    parser.add_argument("--calibration-review-artifact", type=Path, required=True)
    parser.add_argument("--calibration-review-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = build(
        inputs_path=args.inputs,
        calibration_artifact=args.calibration_artifact,
        calibration_root_sha256=args.calibration_root_sha256,
        calibration_review_artifact=args.calibration_review_artifact,
        calibration_review_root_sha256=args.calibration_review_root_sha256,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
