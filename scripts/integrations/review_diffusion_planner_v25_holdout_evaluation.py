#!/usr/bin/env python3
"""Independently rebuild a sealed generic holdout evaluation."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
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
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_continuation import (  # noqa: E402,E501
    load_continuation_ledger,
    mark_independently_reviewed_terminal,
)
from camp_core.integrations.diffusion_planner_v25_role_provenance_review import (  # noqa: E402
    independent_canonicalize_persisted_json,
    independent_validate_evaluation_dual_head_provenance,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _git_head,
    _tracked_dirty,
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
IMPLEMENTATION_SOURCE_HEAD = "7be93df20deee03587b9898e8560909662df972c"
POINTER_HEAD = "06d3a1f3a37061f93f5c9788312ae59d1356d126"
CRITICAL_IMPLEMENTATION_MANIFEST_SHA256 = (
    "f3b707d480b30e1d37d2c10355d8a824df4cff8230af7d78d803dd4504ef6c2b"
)
OLD_TERMINAL_LEDGER_SHA256 = (
    "c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4"
)
HOLDOUT_IDENTITY_SHA256 = (
    "5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a"
)
EXPERIMENT_PROTOCOL_SHA256 = (
    "aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f"
)
EXECUTION_PLAN_SHA256 = (
    "41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0"
)
RUN_NONCE = "8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42"
OPENING_RELEASE_ROOT_SHA256 = (
    "7deec7b81a1ad20dd9eb4657c0c3066ce695bc797349def843c0e7152f85851b"
)
EXECUTION_ROOT_SHA256 = (
    "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
)
EXECUTION_REVIEW_ROOT_SHA256 = (
    "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d"
)
POINTER_ONLY_PATHS = (
    "camp_core/tests/test_diffusion_planner_v25_iteration_audit.py",
    "docs/diffusion_planner_current_status.md",
    "docs/diffusion_planner_v25_iteration_audit.md",
)
SCHEMA_VERSION = "camp_dp_v25_holdout_evaluation_review_artifact_v2"
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
        "dual_head_provenance",
        "evaluation",
        "fresh_outcome_used_to_change_protocol",
        "training_executed",
        "calibration_executed",
        "promotion_deployment_activation_authorized",
    }
)
CORRECTED_EVALUATION_REPORT_FIELDS = EVALUATION_REPORT_FIELDS | frozenset(
    {
        "correction_authority_artifact",
        "correction_authority_root_sha256",
        "correction_authority_review_artifact",
        "correction_authority_review_root_sha256",
        "continuation_ledger",
        "old_terminal_diagnostic_preserved",
        "fresh_execution_reused",
        "fresh_execution_rerun",
        "scientific_contract_changed",
        "release_dual_head_contract",
        "evaluation_role_provenance",
    }
)
CORRECTED_REPAIR_FIELDS = frozenset(
    {
        "correction_repair_artifact",
        "correction_repair_root_sha256",
        "correction_repair_review_artifact",
        "correction_repair_review_root_sha256",
    }
)
CORRECTION_IMPLEMENTATION_PATHS = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_b4_evaluation_continuation.py",
    "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_evaluation.py",
    "scripts/integrations/freeze_diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "scripts/integrations/review_diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "scripts/integrations/authorize_diffusion_planner_v25_b4_evaluation_continuation.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_evaluation.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_b4_evaluation_repair.py",
    "scripts/integrations/freeze_diffusion_planner_v25_b4_evaluation_repair.py",
    "scripts/integrations/review_diffusion_planner_v25_b4_evaluation_repair.py",
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
    if _tracked_dirty(ROOT):
        raise ValueError("holdout evaluation reviewer worktree is dirty")
    evaluation_head = _git_head(ROOT)
    evaluation_manifest_sha256 = tracked_implementation_manifest(ROOT)[
        "manifest_sha256"
    ]
    report = _canonical_json(evaluation_root / "report.json")
    corrected = (
        report.get("schema_version")
        == "camp_dp_v25_holdout_evaluation_artifact_v3_corrected"
    )
    repaired = corrected and "correction_repair_artifact" in report
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
    calibration_binding = _calibration_freeze_binding_independent(
        preopen_authority
    )
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
    execution_head = release["implementation_source_head"]
    release_dual_head = _independent_verify_release_dual_head(
        release=release,
        execution_heads=_heads(execution / "HEADS"),
        execution_review_heads=_heads(execution_review / "HEADS"),
    )
    correction_bindings: dict[str, Any] | None = None
    if corrected:
        correction_bindings = _independent_correction_bindings(
            report=report,
            release=release,
            evaluation_artifact=evaluation_root,
            evaluation_review_output=output,
            evaluation_root_sha256=evaluation_root_sha256,
            evaluation_head=evaluation_head,
        )
    provenance = independent_validate_evaluation_dual_head_provenance(
        report.get("dual_head_provenance")
    )
    expected_provenance = {
        "schema_version": "camp_dp_v25_evaluation_dual_head_provenance_v1",
        "execution_implementation_head": execution_head,
        "execution_critical_implementation_manifest_sha256": release[
            "critical_implementation_manifest_sha256"
        ],
        "opening_release_root_sha256": opening_release_root_sha256,
        "scientific_exposure_ledger_sha256": artifact_report[
            "opening_consumption"
        ]["scientific_ledger_sha256"],
        "execution_root_sha256": report["execution_root_sha256"],
        "execution_review_root_sha256": report[
            "execution_review_root_sha256"
        ],
        "evaluation_implementation_head": evaluation_head,
        "evaluation_critical_implementation_manifest_sha256": (
            evaluation_manifest_sha256
        ),
    }
    if (
        not strict_equal(provenance, expected_provenance)
        or release_dual_head["implementation_source_head"] != execution_head
        or _evaluation_heads(evaluation_root / "HEADS")
        != {
            "execution_camp_head": execution_head,
            "evaluation_camp_head": evaluation_head,
            "fixed_dp_head": FIXED_DP_HEAD,
        }
    ):
        raise ValueError("holdout evaluation dual-HEAD provenance drifted")
    rows = _canonical_value(execution / "evaluation_rows.json")
    rebuilt = independent_canonicalize_persisted_json(
        evaluate_holdout_three_arm(
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
    )
    stored = _canonical_json(evaluation_root / "evaluation.json")
    if (
        not strict_equal(stored, rebuilt)
        or set(report)
        != (
            (
                CORRECTED_EVALUATION_REPORT_FIELDS | CORRECTED_REPAIR_FIELDS
                if repaired
                else CORRECTED_EVALUATION_REPORT_FIELDS
            )
            if corrected
            else EVALUATION_REPORT_FIELDS
        )
        or report.get("schema_version")
        != (
            "camp_dp_v25_holdout_evaluation_artifact_v3_corrected"
            if corrected
            else "camp_dp_v25_holdout_evaluation_artifact_v2"
        )
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
    if corrected and (
        report["release_dual_head_contract"] != release_dual_head
        or report["evaluation_role_provenance"]
        != {
            "implementation_head": evaluation_head,
            "implementation_manifest_sha256": _correction_manifest_sha256(),
        }
        or report["old_terminal_diagnostic_preserved"] is not True
        or report["fresh_execution_reused"] is not True
        or report["fresh_execution_rerun"] is not False
        or report["scientific_contract_changed"] is not False
    ):
        raise ValueError("corrected evaluation provenance drifted")
    result = {
        "schema_version": (
            "camp_dp_v25_holdout_evaluation_review_artifact_v3_corrected"
            if corrected
            else SCHEMA_VERSION
        ),
        "status": "passed_independent_holdout_evaluation_review",
        "reviewed_root_sha256": evaluation_root_sha256,
        "opening_release_root_sha256": opening_release_root_sha256,
        "holdout_identity_sha256": release["holdout_identity"][
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": release["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "dual_head_provenance": provenance,
        "full_denominator_independently_rebuilt": True,
        "claim_rule_independently_rebuilt": True,
        "fresh_outcome_used_to_change_protocol": False,
        "promotion_deployment_activation_authorized": False,
    }
    if corrected:
        result.update(
            {
                "correction_authority_root_sha256": report[
                    "correction_authority_root_sha256"
                ],
                "correction_authority_review_root_sha256": report[
                    "correction_authority_review_root_sha256"
                ],
                "continuation_ledger": report["continuation_ledger"],
                "old_terminal_diagnostic_preserved": True,
                "fresh_execution_reused": True,
                "fresh_execution_rerun": False,
                "scientific_contract_changed": False,
            }
        )
        if repaired:
            result.update(
                {
                    "correction_repair_root_sha256": report[
                        "correction_repair_root_sha256"
                    ],
                    "correction_repair_review_root_sha256": report[
                        "correction_repair_review_root_sha256"
                    ],
                }
            )
    output.mkdir(parents=True)
    _write_json(output / "report.json", result)
    (output / "HEADS").write_bytes(
        (
            f"execution_camp_head={execution_head}\n"
            f"evaluation_camp_head={evaluation_head}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(
        output, label="independent V25 holdout evaluation review"
    )
    if corrected:
        mark_independently_reviewed_terminal(
            Path(report["continuation_ledger"]),
            correction_authority_root_sha256=report[
                "correction_authority_root_sha256"
            ],
            corrected_evaluation_review_output_dir=str(output),
            evaluation_review_root_sha256=root,
        )
    else:
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


def _calibration_freeze_binding_independent(
    preopen_authority: Mapping[str, Any],
) -> dict[str, str]:
    """Independently select only the frozen successful calibration role."""

    bindings = preopen_authority.get("upstream_bindings")
    if type(bindings) is not dict or "calibration_freeze" not in bindings:
        raise ValueError("reviewed calibration freeze binding is missing")
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
        raise ValueError("reviewed calibration freeze binding drifted")
    return dict(binding)


def _independent_verify_release_dual_head(
    *,
    release: Mapping[str, Any],
    execution_heads: Mapping[str, Any],
    execution_review_heads: Mapping[str, Any],
) -> dict[str, Any]:
    source = release.get("implementation_source_head")
    pointer = release.get("pointer_head_at_release")
    manifest_sha = release.get("critical_implementation_manifest_sha256")
    if (
        source != IMPLEMENTATION_SOURCE_HEAD
        or pointer != POINTER_HEAD
        or manifest_sha != CRITICAL_IMPLEMENTATION_MANIFEST_SHA256
        or execution_heads
        != {"camp_head": pointer, "fixed_dp_head": FIXED_DP_HEAD}
        or execution_review_heads != execution_heads
    ):
        raise ValueError("reviewed release dual-HEAD binding drifted")
    changed = tuple(
        line
        for line in subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-only", source, pointer, "--"],
            text=True,
        ).splitlines()
        if line
    )
    if changed != POINTER_ONLY_PATHS:
        raise ValueError("reviewed release pointer-only allowlist drifted")
    if _historical_critical_manifest_sha256(source) != manifest_sha:
        raise ValueError("reviewed release historical manifest drifted")
    return {
        "implementation_source_head": source,
        "pointer_head_at_release": pointer,
        "pointer_only_changed_paths": list(changed),
        "critical_implementation_manifest_sha256": manifest_sha,
        "fixed_dp_head": FIXED_DP_HEAD,
    }


def _historical_critical_manifest_sha256(source: str) -> str:
    authority_path = (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_fresh_preopen_authority.py"
    )
    source_text = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{source}:{authority_path}"],
        text=True,
    )
    tree = ast.parse(source_text, filename=f"{source}:{authority_path}")
    paths: tuple[str, ...] | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "TRACKED_AUTHORITY_FILES"
        ):
            candidate = ast.literal_eval(node.value)
            if (
                type(candidate) is not tuple
                or not candidate
                or any(type(item) is not str for item in candidate)
            ):
                raise ValueError("reviewer historical manifest path set drifted")
            paths = candidate
            break
    if paths is None:
        raise ValueError("reviewer historical manifest path set is absent")
    rows: list[dict[str, str]] = []
    for relative in paths:
        blob = subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{source}:{relative}"]
        )
        rows.append(
            {"path": relative, "sha256": hashlib.sha256(blob).hexdigest()}
        )
    return hashlib.sha256(_canonical_bytes(rows)).hexdigest()


def _correction_manifest_sha256() -> str:
    rows: list[dict[str, str]] = []
    for relative in CORRECTION_IMPLEMENTATION_PATHS:
        path = (ROOT / relative).resolve()
        if ROOT not in path.parents or not path.is_file() or path.is_symlink():
            raise ValueError("reviewer correction implementation path drifted")
        rows.append({"path": relative, "sha256": _file_sha256(path)})
    return hashlib.sha256(_canonical_bytes(rows)).hexdigest()


def _independent_correction_bindings(
    *,
    report: Mapping[str, Any],
    release: Mapping[str, Any],
    evaluation_artifact: Path,
    evaluation_review_output: Path,
    evaluation_root_sha256: str,
    evaluation_head: str,
) -> dict[str, Any]:
    authority_path = Path(report["correction_authority_artifact"]).resolve()
    authority_review_path = Path(
        report["correction_authority_review_artifact"]
    ).resolve()
    authority_root = report["correction_authority_root_sha256"]
    authority_review_root = report[
        "correction_authority_review_root_sha256"
    ]
    for label, path, root in (
        ("correction authority", authority_path, authority_root),
        ("correction authority review", authority_review_path, authority_review_root),
    ):
        verify_complete_seal(path, root, label=label)
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"{label} did not pass")
    authority = _canonical_json(authority_path / "authority.json")
    authority_review = _canonical_json(authority_review_path / "report.json")
    expected_paths = list(POINTER_ONLY_PATHS)
    if (
        authority.get("holdout_identity_sha256") != HOLDOUT_IDENTITY_SHA256
        or authority.get("experiment_protocol_sha256")
        != EXPERIMENT_PROTOCOL_SHA256
        or authority.get("execution_plan_sha256") != EXECUTION_PLAN_SHA256
        or authority.get("run_nonce") != RUN_NONCE
        or authority.get("opening_release", {}).get("root_sha256")
        != OPENING_RELEASE_ROOT_SHA256
        or authority.get("execution", {}).get("root_sha256")
        != EXECUTION_ROOT_SHA256
        or authority.get("execution_review", {}).get("root_sha256")
        != EXECUTION_REVIEW_ROOT_SHA256
        or authority.get("implementation_source_head")
        != IMPLEMENTATION_SOURCE_HEAD
        or authority.get("pointer_head_at_release") != POINTER_HEAD
        or authority.get("pointer_only_changed_paths") != expected_paths
        or authority.get("critical_implementation_manifest_sha256")
        != CRITICAL_IMPLEMENTATION_MANIFEST_SHA256
        or authority.get("old_scientific_ledger", {}).get("sha256")
        != OLD_TERMINAL_LEDGER_SHA256
        or authority.get("corrected_evaluation_output_dir")
        != str(evaluation_artifact)
        or authority.get("corrected_evaluation_review_output_dir")
        != str(evaluation_review_output)
        or authority_review.get("reviewed_authority", {}).get("path")
        != str(authority_path)
        or authority_review.get("reviewed_authority", {}).get("root_sha256")
        != authority_root
        or authority_review.get("status")
        != "passed_independent_fresh_b4_evaluator_policy_correction_authority_review"
        or authority_review.get("raw_outcome_values_inspected") is not False
        or authority_review.get("fresh_execution_rerun") is not False
        or authority_review.get("scientific_contract_changed") is not False
    ):
        raise ValueError("reviewer correction authority binding drifted")
    original_head = authority.get("correction_implementation", {}).get("head")
    current_manifest = _correction_manifest_sha256()
    repaired = "correction_repair_artifact" in report
    if not repaired and (
        original_head != evaluation_head
        or authority.get("correction_implementation", {}).get(
            "manifest_sha256"
        )
        != current_manifest
    ):
        raise ValueError("reviewer correction implementation drifted")
    if repaired:
        repair_path = Path(report["correction_repair_artifact"]).resolve()
        repair_review_path = Path(
            report["correction_repair_review_artifact"]
        ).resolve()
        for label, path, root in (
            ("evaluation repair", repair_path, report["correction_repair_root_sha256"]),
            (
                "evaluation repair review",
                repair_review_path,
                report["correction_repair_review_root_sha256"],
            ),
        ):
            verify_complete_seal(path, root, label=label)
            if (path / "run.exit").read_bytes() != b"0\n":
                raise ValueError(f"{label} did not pass")
        repair = _canonical_json(repair_path / "repair.json")
        repair_review = _canonical_json(repair_review_path / "report.json")
        if (
            repair.get("original_correction_authority", {}).get(
                "root_sha256"
            )
            != authority_root
            or repair.get("original_correction_authority_review", {}).get(
                "root_sha256"
            )
            != authority_review_root
            or repair.get("old_correction_head") != original_head
            or repair.get("new_correction_head") != evaluation_head
            or repair.get("new_correction_manifest_sha256")
            != current_manifest
            or repair.get("corrected_evaluation_output_dir")
            != str(evaluation_artifact)
            or repair.get("corrected_evaluation_review_output_dir")
            != str(evaluation_review_output)
            or repair.get("raw_outcome_values_inspected") is not False
            or repair.get("fresh_execution_rerun") is not False
            or repair.get("scientific_contract_changed") is not False
            or repair_review.get("reviewed_repair")
            != {
                "path": str(repair_path),
                "root_sha256": report["correction_repair_root_sha256"],
            }
            or repair_review.get("status")
            != "passed_independent_outcome_blind_pre_artifact_evaluation_repair_review"
        ):
            raise ValueError("reviewer evaluation repair binding drifted")
    continuation = load_continuation_ledger(Path(report["continuation_ledger"]))
    if (
        continuation["state"] != "evaluation_artifact_formed"
        or continuation["correction_authority_root_sha256"] != authority_root
        or continuation["correction_authority_review_root_sha256"]
        != authority_review_root
        or continuation["evaluation_root_sha256"] != evaluation_root_sha256
        or continuation["old_terminal_ledger_sha256"]
        != OLD_TERMINAL_LEDGER_SHA256
    ):
        raise ValueError("reviewer correction continuation CAS drifted")
    return {
        "authority": authority,
        "authority_review": authority_review,
        "continuation": continuation,
    }


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


def _heads(path: Path) -> dict[str, str]:
    return _heads_with_fields(path, {"camp_head", "fixed_dp_head"})


def _evaluation_heads(path: Path) -> dict[str, str]:
    return _heads_with_fields(
        path,
        {"execution_camp_head", "evaluation_camp_head", "fixed_dp_head"},
    )


def _heads_with_fields(path: Path, fields: set[str]) -> dict[str, str]:
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"reviewed HEADS is not ASCII: {path}") from exc
    if not text.endswith("\n") or "\r" in text:
        raise ValueError(f"reviewed HEADS bytes drifted: {path}")
    result: dict[str, str] = {}
    for line in text[:-1].split("\n"):
        if line.count("=") != 1:
            raise ValueError(f"reviewed HEADS row drifted: {path}")
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError(f"duplicate reviewed HEADS row: {key}")
        result[key] = value
    if set(result) != fields:
        raise ValueError(f"reviewed HEADS field set drifted: {path}")
    return result


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
