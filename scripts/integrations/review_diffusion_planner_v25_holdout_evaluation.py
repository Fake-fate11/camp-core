#!/usr/bin/env python3
"""Independently rebuild a sealed generic holdout evaluation."""

from __future__ import annotations

import argparse
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
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    strict_equal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (  # noqa: E402
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preopen_dispatch import (  # noqa: E402
    holdout_zero_overlap_passed,
    validate_holdout_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    mark_scientific_evaluated,
    terminate_scientific_identity,
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "camp_dp_v25_holdout_evaluation_review_artifact_v1"
EVALUATION_REPORT_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "execution_artifact",
        "execution_root_sha256",
        "execution_review_artifact",
        "execution_review_root_sha256",
        "opening_release_root_sha256",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "evaluation",
        "fresh_outcome_used_to_change_protocol",
        "training_executed",
        "calibration_executed",
        "promotion_deployment_activation_authorized",
    }
)


def review(
    *,
    evaluation_artifact: Path,
    evaluation_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    output_dir: Path,
) -> str:
    evaluation_root = Path(evaluation_artifact).resolve()
    release_root = Path(opening_release_artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    for label, path, root in (
        ("evaluation", evaluation_root, evaluation_root_sha256),
        ("opening release", release_root, opening_release_root_sha256),
    ):
        verify_complete_seal(path, root, label=f"holdout {label}")
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"holdout {label} did not pass")
    release = validate_production_rc_opening_release(
        _canonical_json(release_root / "decision.json")
    )
    report = _canonical_json(evaluation_root / "report.json")
    execution = Path(report["execution_artifact"]).resolve()
    execution_review = Path(report["execution_review_artifact"]).resolve()
    verify_complete_seal(
        execution,
        report["execution_root_sha256"],
        label="reviewed holdout execution",
    )
    verify_complete_seal(
        execution_review,
        report["execution_review_root_sha256"],
        label="reviewed holdout execution review",
    )
    if (
        (execution / "run.exit").read_bytes() != b"0\n"
        or (execution_review / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("reviewed holdout execution chain did not pass")
    execution_review_report = _canonical_json(
        execution_review / "report.json"
    )
    preopen = Path(release["preopen_authority"]["path"]).resolve()
    verify_complete_seal(
        preopen,
        release["preopen_authority"]["root_sha256"],
        label="reviewed holdout preopen",
    )
    if (preopen / "run.exit").read_bytes() != b"0\n":
        raise ValueError("reviewed holdout preopen did not pass")
    preopen_authority = validate_holdout_preopen_authority(
        _canonical_json(preopen / "preopen_authority.json")
    )
    split = release["holdout_identity"]["split"]
    calibration_binding = preopen_authority["upstream_bindings"][
        "calibration_freeze"
    ]
    calibration_root = Path(calibration_binding["path"]).resolve()
    verify_complete_seal(
        calibration_root,
        calibration_binding["root_sha256"],
        label="reviewed calibration freeze",
    )
    calibration = validate_calibration_freeze_payload(
        _canonical_json(calibration_root / "calibration_freeze.json")
    )
    artifact_report = _canonical_json(execution / "artifact_report.json")
    rows = _canonical_value(execution / "evaluation_rows.json")
    rebuilt = evaluate_holdout_three_arm(
        rows,
        calibration_contract=calibration["calibration_contract"],
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
        root_gates={
            "failure_denominator_complete": (
                execution_review_report["full_denominator_formed"] is True
            ),
            "immutability_passed": True,
            "zero_overlap_passed": holdout_zero_overlap_passed(
                preopen_authority, split=split
            ),
        },
    )
    stored = _canonical_json(evaluation_root / "evaluation.json")
    if (
        not strict_equal(stored, rebuilt)
        or set(report) != EVALUATION_REPORT_FIELDS
        or report.get("schema_version")
        != "camp_dp_v25_holdout_evaluation_artifact_v1"
        or report.get("status") != "sealed_holdout_three_arm_evaluation"
        or not strict_equal(report.get("evaluation"), stored)
        or Path(report.get("execution_artifact", "")).resolve() != execution
        or Path(report.get("execution_review_artifact", "")).resolve()
        != execution_review
        or report.get("opening_release_root_sha256")
        != opening_release_root_sha256
        or report.get("holdout_identity_sha256")
        != release["holdout_identity"]["holdout_identity_sha256"]
        or report.get("experiment_protocol_sha256")
        != release["experiment_protocol"]["experiment_protocol_sha256"]
        or report.get("fresh_outcome_used_to_change_protocol") is not False
        or report.get("training_executed") is not False
        or report.get("calibration_executed") is not False
        or report.get("promotion_deployment_activation_authorized")
        is not False
    ):
        raise ValueError("holdout evaluation differs from independent rebuild")
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_holdout_evaluation_review",
        "reviewed_root_sha256": evaluation_root_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "holdout_identity_sha256": release["holdout_identity"][
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": release["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "full_denominator_independently_rebuilt": True,
        "claim_rule_independently_rebuilt": True,
        "fresh_outcome_used_to_change_protocol": False,
        "promotion_deployment_activation_authorized": False,
    }
    output.mkdir(parents=True)
    _write_json(output / "report.json", result)
    (output / "HEADS").write_bytes(
        (
            f"camp_head={release['pointer_head_at_release']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(
        output, label="independent V25 holdout evaluation review"
    )
    scientific_path = Path(release["scientific_ledger_path"])
    mark_scientific_evaluated(scientific_path)
    terminate_scientific_identity(
        scientific_path,
        expected_state="evaluated",
        success=True,
        terminal_artifact_root_sha256=root,
        terminal_reason="passed_independent_holdout_evaluation_review",
    )
    return root


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-artifact", type=Path, required=True)
    parser.add_argument("--evaluation-root-sha256", required=True)
    parser.add_argument("--opening-release-artifact", type=Path, required=True)
    parser.add_argument("--opening-release-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"reviewed evaluation JSON is not an object: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = Path(path).read_bytes()
    value = _strict_parse_json(raw, path)
    if raw != _canonical_bytes(value):
        raise ValueError(f"reviewed evaluation JSON is not canonical: {path}")
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


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


if __name__ == "__main__":
    raise SystemExit(main())
