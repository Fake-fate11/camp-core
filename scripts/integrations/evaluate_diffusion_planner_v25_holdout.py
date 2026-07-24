#!/usr/bin/env python3
"""Evaluate a sealed generic holdout execution under its frozen protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    evaluate_holdout_three_arm,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (  # noqa: E402
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    validate_scientific_ledger,
)
from camp_core.integrations.diffusion_planner_v25_role_provenance import (  # noqa: E402
    freeze_evaluation_dual_head_provenance,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preopen_dispatch import (  # noqa: E402
    holdout_zero_overlap_passed,
    validate_holdout_preopen_authority,
)
from scripts.integrations.run_diffusion_planner_v25_holdout_execution import (  # noqa: E402
    SCHEMA_VERSION as EXECUTION_ARTIFACT_SCHEMA_VERSION,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _git_head,
    _tracked_dirty,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "camp_dp_v25_holdout_evaluation_artifact_v2"
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
    release = validate_production_rc_opening_release(
        _canonical_json(release_root / "decision.json")
    )
    if _tracked_dirty(ROOT):
        raise ValueError("holdout evaluator worktree is dirty")
    evaluation_head = _git_head(ROOT)
    evaluation_manifest = tracked_implementation_manifest(ROOT)
    execution_heads = _heads(execution / "HEADS")
    execution_review_heads = _heads(execution_review / "HEADS")
    execution_head = release["implementation_source_head"]
    if (
        execution_heads
        != {
            "camp_head": execution_head,
            "fixed_dp_head": FIXED_DP_HEAD,
        }
        or execution_review_heads != execution_heads
        or release["pointer_head_at_release"] != execution_head
    ):
        raise ValueError("holdout execution/evaluation role HEAD drifted")
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
    preopen_authority = validate_holdout_preopen_authority(
        _canonical_json(preopen / "preopen_authority.json")
    )
    split = release["holdout_identity"]["split"]
    calibration_binding = _calibration_freeze_binding(preopen_authority)
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
    exposure = artifact_report["opening_consumption"]
    provenance = freeze_evaluation_dual_head_provenance(
        execution_implementation_head=execution_head,
        execution_critical_implementation_manifest_sha256=release[
            "critical_implementation_manifest_sha256"
        ],
        opening_release_root_sha256=opening_release_root_sha256,
        scientific_exposure_ledger_sha256=exposure[
            "scientific_ledger_sha256"
        ],
        execution_root_sha256=execution_root_sha256,
        execution_review_root_sha256=execution_review_root_sha256,
        evaluation_implementation_head=evaluation_head,
        evaluation_critical_implementation_manifest_sha256=(
            evaluation_manifest["manifest_sha256"]
        ),
    )
    scientific = validate_scientific_ledger(
        _strict_canonical_json(Path(release["scientific_ledger_path"]))
    )
    if (
        scientific["state"] != "full_denominator_formed"
        or scientific["opening_release_root_sha256"]
        != opening_release_root_sha256
        or scientific["holdout_identity_sha256"]
        != release["holdout_identity"]["holdout_identity_sha256"]
        or scientific["terminal_artifact_root_sha256"] is not None
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
        "zero_overlap_passed": holdout_zero_overlap_passed(
            preopen_authority, split=split
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
        "dual_head_provenance": provenance,
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
            f"execution_camp_head={execution_head}\n"
            f"evaluation_camp_head={evaluation_head}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 holdout evaluation")


def _calibration_freeze_binding(
    preopen_authority: Mapping[str, Any],
) -> dict[str, str]:
    """Select the exact success role; never reinterpret every upstream exit."""

    bindings = preopen_authority.get("upstream_bindings")
    if type(bindings) is not dict or "calibration_freeze" not in bindings:
        raise ValueError("holdout calibration freeze binding is missing")
    binding = bindings["calibration_freeze"]
    if (
        type(binding) is not dict
        or set(binding) != {"path", "root_sha256"}
        or type(binding["path"]) is not str
        or not Path(binding["path"]).is_absolute()
        or str(Path(binding["path"]).resolve()) != binding["path"]
        or type(binding["root_sha256"]) is not str
        or len(binding["root_sha256"]) != 64
        or any(
            char not in "0123456789abcdef"
            for char in binding["root_sha256"]
        )
    ):
        raise ValueError("holdout calibration freeze binding drifted")
    return dict(binding)


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


def _heads(path: Path) -> dict[str, str]:
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"holdout HEADS is not ASCII: {path}") from exc
    if not text.endswith("\n") or "\r" in text:
        raise ValueError(f"holdout HEADS bytes drifted: {path}")
    result: dict[str, str] = {}
    for line in text[:-1].split("\n"):
        if line.count("=") != 1:
            raise ValueError(f"holdout HEADS row drifted: {path}")
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError(f"duplicate holdout HEADS row: {key}")
        result[key] = value
    if set(result) != {"camp_head", "fixed_dp_head"}:
        raise ValueError(f"holdout HEADS field set drifted: {path}")
    return result


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
