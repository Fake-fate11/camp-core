#!/usr/bin/env python3
"""Independently rebuild a sealed V25 Fresh B2 evaluation artifact."""

from __future__ import annotations

import argparse
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
    evaluate_fresh_b2_three_arm,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    validate_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_fresh_opening import (  # noqa: E402
    validate_fresh_b2_opening_release,
)
from scripts.integrations.evaluate_diffusion_planner_v25_fresh_b2 import (  # noqa: E402
    FIXED_DP_HEAD,
    SCHEMA_VERSION as EVALUATION_ARTIFACT_SCHEMA_VERSION,
    _bind_reviews,
    _canonical_bytes,
    _canonical_json,
    _canonical_json_list,
    _derive_root_gates,
    _git_head,
    _strict_json_value,
    _tracked_dirty,
    _verify_inputs,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _file_sha256,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_evaluation_review_v1"


def review(*, artifact: Path, artifact_root_sha256: str, output_dir: Path) -> str:
    evaluation_root = Path(artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    seal = verify_complete_seal(
        evaluation_root,
        artifact_root_sha256,
        label="Fresh B2 evaluation",
    )
    if (evaluation_root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B2 evaluation did not exit successfully")
    report = _canonical_json(evaluation_root / "report.json")
    recorded = _canonical_json(evaluation_root / "evaluation.json")
    _validate_report(report, evaluation_root=evaluation_root)
    paths = {
        role: Path(path).resolve()
        for role, path in report["input_artifacts"].items()
    }
    roots = _verify_inputs(
        {role: (paths[role], report["input_roots"][role]) for role in paths}
    )
    execution_report = _canonical_json(paths["execution"] / "report.json")
    execution_artifact_report = _canonical_json(
        paths["execution"] / "artifact_report.json"
    )
    execution_review = _canonical_json(paths["execution_review"] / "report.json")
    calibration_payload = validate_calibration_freeze_payload(
        _canonical_json(paths["calibration_freeze"] / "calibration_freeze.json")
    )
    calibration_review = _canonical_json(
        paths["calibration_freeze_review"] / "report.json"
    )
    qualification = validate_preopen_authority(
        _canonical_json(paths["preopen"] / "preopen_authority.json")
    )
    preopen_review = _canonical_json(paths["preopen_review"] / "report.json")
    release = validate_fresh_b2_opening_release(
        _canonical_json(paths["opening_release"] / "decision.json")
    )
    _bind_reviews(
        roots=roots,
        execution_report=execution_report,
        execution_review=execution_review,
        calibration_review=calibration_review,
        preopen_review=preopen_review,
    )
    root_gates = _derive_root_gates(
        execution_report=execution_report,
        execution_review=execution_review,
        qualification=qualification,
    )
    if not _strict_equal(root_gates, report["root_gates"]):
        raise ValueError("Fresh B2 recorded root gates differ from reconstruction")
    rebuilt = evaluate_fresh_b2_three_arm(
        _canonical_json_list(paths["execution"] / "evaluation_rows.json"),
        calibration_contract=calibration_payload["calibration_contract"],
        calibration_contract_root_sha256=roots["calibration_freeze"],
        preopen_qualification_root_sha256=roots["preopen"],
        opening_release=release,
        opening_release_root_sha256=roots["opening_release"],
        opening_consumption_receipt=execution_artifact_report[
            "opening_consumption"
        ],
        root_gates=root_gates,
    )
    if not _strict_equal(recorded, rebuilt):
        raise ValueError("Fresh B2 evaluation differs from independent reconstruction")
    rebuilt_claims = {
        method: {
            "safety_improvement_claim_passed": rebuilt["method_reports"][method][
                "claim_decision"
            ]["safety_improvement_claim_passed"],
            "red_light_improvement_claim_passed": rebuilt["method_reports"][method][
                "claim_decision"
            ]["red_light_improvement_claim_passed"],
        }
        for method in ("static14d", "scene14d")
    }
    if not _strict_equal(report["method_claims"], rebuilt_claims):
        raise ValueError("Fresh B2 evaluation report claim summary drifted")
    output.mkdir(parents=True)
    review_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_fresh_b2_evaluation_review",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(evaluation_root),
        "reviewed_root_sha256": seal["root_sha256"],
        "evaluation_sha256": _file_sha256(evaluation_root / "evaluation.json"),
        "root_gates_independently_rebuilt": True,
        "all_rows_revalidated": True,
        "all_claims_recomputed_from_frozen_margins": True,
        "failure_rows_retained_in_denominator": True,
        "safetycost_imputed_for_failed_pairs": False,
        "promotion_deployment_activation_authorized": False,
    }
    _write_json(output / "report.json", review_report)
    (output / "HEADS").write_bytes(
        f"camp_head={review_report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
            "ascii"
        )
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 Fresh B2 evaluation review")


def _validate_report(report: dict[str, Any], *, evaluation_root: Path) -> None:
    expected_fields = {
        "schema_version",
        "status",
        "camp_head",
        "fixed_dp_head",
        "input_artifacts",
        "input_roots",
        "root_gates",
        "evaluation_sha256",
        "method_claims",
        "failure_rows_retained_in_denominator",
        "safetycost_imputed_for_failed_pairs",
        "promotion_deployment_activation_authorized",
    }
    if type(report) is not dict or set(report) != expected_fields:
        raise ValueError("Fresh B2 evaluation report field set drifted")
    if (
        report.get("schema_version") != EVALUATION_ARTIFACT_SCHEMA_VERSION
        or report.get("status") != "sealed_fresh_b2_three_arm_evaluation"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("camp_head") != _git_head(ROOT)
        or report.get("evaluation_sha256")
        != _file_sha256(evaluation_root / "evaluation.json")
        or report.get("failure_rows_retained_in_denominator") is not True
        or report.get("safetycost_imputed_for_failed_pairs") is not False
        or report.get("promotion_deployment_activation_authorized") is not False
        or type(report.get("input_artifacts")) is not dict
        or type(report.get("input_roots")) is not dict
        or set(report["input_artifacts"]) != set(report["input_roots"])
    ):
        raise ValueError("Fresh B2 evaluation report exact contract drifted")


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


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    digest = review(
        artifact=args.artifact,
        artifact_root_sha256=args.artifact_root_sha256,
        output_dir=args.output_dir,
    )
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
