#!/usr/bin/env python3
"""Evaluate a sealed generic holdout execution under its frozen protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
    validate_calibration_freeze_payload,
)
from camp_core.integrations.diffusion_planner_v25_evaluation import (  # noqa: E402
    evaluate_holdout_three_arm,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening import (  # noqa: E402
    validate_holdout_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
    validate_tombstone,
)
from scripts.integrations.run_diffusion_planner_v25_holdout_execution import (  # noqa: E402
    SCHEMA_VERSION as EXECUTION_ARTIFACT_SCHEMA_VERSION,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "camp_dp_v25_holdout_evaluation_artifact_v1"
EXECUTION_ARTIFACT_REPORT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "controller_decision_root_sha256",
        "opening_release_root_sha256",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "opening_consumption",
        "execution_report_sha256",
        "fresh_opened_once",
        "training_executed",
        "calibration_executed",
        "claim_authorized_by_artifact",
    }
)


def evaluate(
    *,
    execution_artifact: Path,
    execution_root_sha256: str,
    execution_review_artifact: Path,
    execution_review_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    output_dir: Path,
) -> str:
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    execution = Path(execution_artifact).resolve()
    execution_review = Path(execution_review_artifact).resolve()
    release_root = Path(opening_release_artifact).resolve()
    for label, path, root in (
        ("execution", execution, execution_root_sha256),
        ("execution review", execution_review, execution_review_root_sha256),
        ("opening release", release_root, opening_release_root_sha256),
    ):
        verify_complete_seal(path, root, label=f"holdout {label}")
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"holdout {label} did not pass")
    release = validate_holdout_opening_release(
        _canonical_json(release_root / "decision.json")
    )
    execution_review_report = _canonical_json(
        execution_review / "report.json"
    )
    if (
        execution_review_report.get("status")
        != "passed_independent_holdout_execution_review"
        or execution_review_report.get("reviewed_root_sha256")
        != execution_root_sha256
        or execution_review_report.get("holdout_identity_sha256")
        != release["holdout_identity"]["holdout_identity_sha256"]
    ):
        raise ValueError("holdout execution review binding drifted")
    preopen = Path(release["preopen_authority"]["path"]).resolve()
    verify_complete_seal(
        preopen,
        release["preopen_authority"]["root_sha256"],
        label="holdout preopen",
    )
    preopen_authority = _canonical_json(
        preopen / "preopen_authority.json"
    )
    calibration_binding = preopen_authority["upstream_bindings"][
        "calibration_freeze"
    ]
    calibration_root = Path(calibration_binding["path"]).resolve()
    verify_complete_seal(
        calibration_root,
        calibration_binding["root_sha256"],
        label="holdout calibration freeze",
    )
    calibration_payload = validate_calibration_freeze_payload(
        _canonical_json(calibration_root / "calibration_freeze.json")
    )
    artifact_report = _canonical_json(execution / "artifact_report.json")
    execution_report = _canonical_json(execution / "report.json")
    if (
        set(artifact_report) != EXECUTION_ARTIFACT_REPORT_FIELDS
        or artifact_report["schema_version"]
        != EXECUTION_ARTIFACT_SCHEMA_VERSION
        or artifact_report["status"] != "sealed_holdout_execution"
        or artifact_report["controller_decision_root_sha256"]
        != release["controller_decision_root_sha256"]
        or artifact_report["opening_release_root_sha256"]
        != opening_release_root_sha256
        or artifact_report["holdout_identity_sha256"]
        != release["holdout_identity"]["holdout_identity_sha256"]
        or artifact_report["experiment_protocol_sha256"]
        != release["experiment_protocol"]["experiment_protocol_sha256"]
        or artifact_report["execution_report_sha256"]
        != _canonical_sha(execution_report)
        or artifact_report["fresh_opened_once"] is not True
        or artifact_report["training_executed"] is not False
        or artifact_report["calibration_executed"] is not False
        or artifact_report["claim_authorized_by_artifact"] is not False
    ):
        raise ValueError("holdout execution artifact report drifted")
    tombstone = validate_tombstone(
        _strict_canonical_json(Path(release["cas_tombstone_path"]))
    )
    if (
        tombstone["state"] != "opened_consumed"
        or tombstone["opening_release_root_sha256"]
        != opening_release_root_sha256
        or tombstone["marker_sha256"]
        != artifact_report["opening_consumption"]["marker_sha256"]
        or tombstone["terminal_artifact_root_sha256"] is not None
        or tombstone["outcome_evaluation_completed"] is not False
    ):
        raise ValueError("holdout evaluation CAS state drifted")
    rows = _canonical_value(execution / "evaluation_rows.json")
    if type(rows) is not list:
        raise ValueError("holdout evaluation row inventory drifted")
    root_gates = {
        "failure_denominator_complete": (
            execution_review_report["full_denominator_formed"] is True
        ),
        "immutability_passed": True,
        "zero_overlap_passed": (
            preopen_authority["zero_overlap"]["status"]
            == "passed_train_calibration_b2_b3_zero_overlap"
        ),
    }
    result = evaluate_holdout_three_arm(
        rows,
        calibration_contract=calibration_payload["calibration_contract"],
        calibration_contract_root_sha256=calibration_binding[
            "root_sha256"
        ],
        preopen_qualification_root_sha256=release[
            "preopen_authority"
        ]["root_sha256"],
        opening_release=release,
        opening_release_root_sha256=opening_release_root_sha256,
        opening_consumption_receipt=artifact_report[
            "opening_consumption"
        ],
        root_gates=root_gates,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "sealed_holdout_three_arm_evaluation",
        "execution_artifact": str(execution),
        "execution_root_sha256": execution_root_sha256,
        "execution_review_artifact": str(execution_review),
        "execution_review_root_sha256": execution_review_root_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "holdout_identity_sha256": release["holdout_identity"][
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": release["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "evaluation": result,
        "fresh_outcome_used_to_change_protocol": False,
        "training_executed": False,
        "calibration_executed": False,
        "promotion_deployment_activation_authorized": False,
    }
    output.mkdir(parents=True)
    _write_json(output / "evaluation.json", result)
    _write_json(output / "report.json", report)
    (output / "HEADS").write_bytes(
        (
            f"camp_head={release['pointer_head_at_release']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 holdout evaluation")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-artifact", type=Path, required=True)
    parser.add_argument("--execution-root-sha256", required=True)
    parser.add_argument("--execution-review-artifact", type=Path, required=True)
    parser.add_argument("--execution-review-root-sha256", required=True)
    parser.add_argument("--opening-release-artifact", type=Path, required=True)
    parser.add_argument("--opening-release-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = evaluate(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"holdout evaluation JSON is not an object: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = Path(path).read_bytes()
    value = _strict_parse_json(raw, path)
    if raw != _canonical_bytes(value):
        raise ValueError(f"holdout evaluation JSON is not canonical: {path}")
    return value


def _strict_parse_json(raw: bytes, path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


if __name__ == "__main__":
    raise SystemExit(main())
