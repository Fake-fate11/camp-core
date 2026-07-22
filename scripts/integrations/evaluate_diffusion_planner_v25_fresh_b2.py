#!/usr/bin/env python3
"""Seal the frozen V25 Fresh B2 SafetyCost/NI/latency evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Mapping


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
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    FIXED_DP_HEAD,
    _canonical_json,
    _file_sha256,
    _git_head,
    _tracked_dirty,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_evaluation_artifact_v1"


def evaluate(
    *,
    execution_artifact: Path,
    execution_root_sha256: str,
    execution_review_artifact: Path,
    execution_review_root_sha256: str,
    calibration_freeze_artifact: Path,
    calibration_freeze_root_sha256: str,
    calibration_freeze_review_artifact: Path,
    calibration_freeze_review_root_sha256: str,
    preopen_artifact: Path,
    preopen_root_sha256: str,
    preopen_review_artifact: Path,
    preopen_review_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    output_dir: Path,
) -> str:
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    inputs = {
        "execution": (execution_artifact, execution_root_sha256),
        "execution_review": (
            execution_review_artifact,
            execution_review_root_sha256,
        ),
        "calibration_freeze": (
            calibration_freeze_artifact,
            calibration_freeze_root_sha256,
        ),
        "calibration_freeze_review": (
            calibration_freeze_review_artifact,
            calibration_freeze_review_root_sha256,
        ),
        "preopen": (preopen_artifact, preopen_root_sha256),
        "preopen_review": (preopen_review_artifact, preopen_review_root_sha256),
        "opening_release": (
            opening_release_artifact,
            opening_release_root_sha256,
        ),
    }
    roots = _verify_inputs(inputs)
    paths = {name: Path(value[0]).resolve() for name, value in inputs.items()}
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
    rows = _canonical_json_list(paths["execution"] / "evaluation_rows.json")
    root_gates = _derive_root_gates(
        execution_report=execution_report,
        execution_review=execution_review,
        qualification=qualification,
    )
    result = evaluate_fresh_b2_three_arm(
        rows,
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
    output.mkdir(parents=True)
    _write_json(output / "evaluation.json", result)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "sealed_fresh_b2_three_arm_evaluation",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "input_artifacts": {name: str(path) for name, path in paths.items()},
        "input_roots": roots,
        "root_gates": root_gates,
        "evaluation_sha256": _file_sha256(output / "evaluation.json"),
        "method_claims": {
            method: {
                "safety_improvement_claim_passed": result["method_reports"][method][
                    "claim_decision"
                ]["safety_improvement_claim_passed"],
                "red_light_improvement_claim_passed": result["method_reports"][method][
                    "claim_decision"
                ]["red_light_improvement_claim_passed"],
            }
            for method in ("static14d", "scene14d")
        },
        "failure_rows_retained_in_denominator": True,
        "safetycost_imputed_for_failed_pairs": False,
        "promotion_deployment_activation_authorized": False,
    }
    _write_json(output / "report.json", report)
    (output / "HEADS").write_bytes(
        f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
            "ascii"
        )
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 Fresh B2 evaluation")


def _verify_inputs(values: Mapping[str, tuple[Path, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for role, (raw_path, digest) in values.items():
        path = Path(raw_path).resolve()
        seal = verify_complete_seal(path, str(digest), label=f"Fresh B2 {role}")
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"Fresh B2 {role} run.exit drifted")
        result[role] = seal["root_sha256"]
    return result


def _bind_reviews(
    *,
    roots: Mapping[str, str],
    execution_report: Mapping[str, Any],
    execution_review: Mapping[str, Any],
    calibration_review: Mapping[str, Any],
    preopen_review: Mapping[str, Any],
) -> None:
    if (
        execution_review.get("status")
        != "passed_independent_fresh_b2_three_arm_execution_review"
        or execution_review.get("reviewed_root_sha256") != roots["execution"]
        or calibration_review.get("status")
        != "passed_independent_calibration_freeze_review"
        or calibration_review.get("reviewed_root_sha256")
        != roots["calibration_freeze"]
        or preopen_review.get("status")
        != "passed_independent_outcome_blind_fresh_b2_preopen_review"
        or preopen_review.get("reviewed_root_sha256") != roots["preopen"]
        or execution_report.get("candidate_tensor_modified") is not False
        or execution_report.get("fresh_outcome_used_to_change_protocol") is not False
    ):
        raise ValueError("Fresh B2 reviewed evaluation authority drifted")


def _derive_root_gates(
    *,
    execution_report: Mapping[str, Any],
    execution_review: Mapping[str, Any],
    qualification: Mapping[str, Any],
) -> dict[str, bool]:
    planned = execution_report.get("planned_arm_run_count")
    terminal = execution_report.get("terminal_arm_run_count")
    reviewed = execution_review.get("reviewed_arm_run_count")
    zero_overlap = qualification.get("zero_overlap_receipt")
    return {
        "failure_denominator_complete": bool(
            type(planned) is int
            and type(terminal) is int
            and type(reviewed) is int
            and planned == terminal == reviewed
        ),
        "immutability_passed": bool(
            execution_report.get("candidate_tensor_modified") is False
            and execution_review.get("candidate_tensor_modified") is False
        ),
        "zero_overlap_passed": bool(
            type(zero_overlap) is dict
            and zero_overlap.get("status") == "passed"
            and zero_overlap.get("fresh_outcome_consumed") is False
        ),
    }


def _canonical_json_list(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    value = _strict_json_value(raw)
    if (
        type(value) is not list
        or any(type(row) is not dict for row in value)
        or raw != _canonical_bytes(value)
    ):
        raise ValueError(f"Fresh B2 authority JSON list is not canonical: {path}")
    return value


def _strict_json_value(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Fresh B2 evaluation JSON has a duplicate key")
            result[key] = value
        return result

    import json

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _canonical_bytes(value: Any) -> bytes:
    import json

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


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for role in (
        "execution",
        "execution_review",
        "calibration_freeze",
        "calibration_freeze_review",
        "preopen",
        "preopen_review",
        "opening_release",
    ):
        option = role.replace("_", "-")
        parser.add_argument(f"--{option}-artifact", type=Path, required=True)
        parser.add_argument(f"--{option}-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    digest = evaluate(
        execution_artifact=args.execution_artifact,
        execution_root_sha256=args.execution_root_sha256,
        execution_review_artifact=args.execution_review_artifact,
        execution_review_root_sha256=args.execution_review_root_sha256,
        calibration_freeze_artifact=args.calibration_freeze_artifact,
        calibration_freeze_root_sha256=args.calibration_freeze_root_sha256,
        calibration_freeze_review_artifact=args.calibration_freeze_review_artifact,
        calibration_freeze_review_root_sha256=args.calibration_freeze_review_root_sha256,
        preopen_artifact=args.preopen_artifact,
        preopen_root_sha256=args.preopen_root_sha256,
        preopen_review_artifact=args.preopen_review_artifact,
        preopen_review_root_sha256=args.preopen_review_root_sha256,
        opening_release_artifact=args.opening_release_artifact,
        opening_release_root_sha256=args.opening_release_root_sha256,
        output_dir=args.output_dir,
    )
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
