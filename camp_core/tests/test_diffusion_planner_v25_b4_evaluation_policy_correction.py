from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess

import pytest

from camp_core.integrations.diffusion_planner_v25_b4_evaluation_continuation import (
    authorize_from_preserved_denominator,
    load_continuation_ledger,
    mark_corrected_evaluation_artifact_formed,
    mark_independently_reviewed_terminal,
    start_corrected_evaluation,
    validate_continuation_ledger,
)
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_policy_correction import (
    CONTROLLER_ROOT_SHA256,
    CORRECTION_IMPLEMENTATION_PATHS,
    CRITICAL_IMPLEMENTATION_MANIFEST_SHA256,
    EXECUTION_PLAN_SHA256,
    EXECUTION_REVIEW_ROOT_SHA256,
    EXECUTION_ROOT_SHA256,
    EXPERIMENT_PROTOCOL_SHA256,
    FIXED_DP_HEAD,
    HOLDOUT_IDENTITY_SHA256,
    IMPLEMENTATION_SOURCE_HEAD,
    OLD_CLOSEOUT_REVIEW_ROOT_SHA256,
    OLD_CLOSEOUT_ROOT_SHA256,
    OLD_CONTROL_COMMAND_SHA256,
    OLD_CONTROL_RUN_EXIT_SHA256,
    OLD_CONTROL_STDERR_SHA256,
    OLD_EVALUATION_ERROR,
    OLD_TERMINAL_HISTORY,
    OLD_TERMINAL_LEDGER_SHA256,
    OLD_TERMINAL_REASON,
    OPENING_RELEASE_ROOT_SHA256,
    POINTER_HEAD,
    POINTER_ONLY_PATHS,
    RUN_NONCE,
    freeze_correction_authority,
    manifest_at_git_head,
    validate_correction_authority,
    verify_release_dual_head_contract,
)


REPO = Path(__file__).resolve().parents[2]
HEX_A = "a" * 64
HEX_B = "b" * 64


def _heads(head: str = IMPLEMENTATION_SOURCE_HEAD) -> dict[str, str]:
    return {"camp_head": head, "fixed_dp_head": FIXED_DP_HEAD}


def test_real_b4_dual_head_contract_passes() -> None:
    result = verify_release_dual_head_contract(
        REPO,
        implementation_source_head=IMPLEMENTATION_SOURCE_HEAD,
        pointer_head_at_release=POINTER_HEAD,
        critical_implementation_manifest_sha256=(
            CRITICAL_IMPLEMENTATION_MANIFEST_SHA256
        ),
        execution_heads=_heads(POINTER_HEAD),
        execution_review_heads=_heads(POINTER_HEAD),
    )
    assert result["pointer_only_changed_paths"] == list(POINTER_ONLY_PATHS)


def test_same_head_contract_remains_valid() -> None:
    manifest = manifest_at_git_head(
        REPO, git_head=IMPLEMENTATION_SOURCE_HEAD
    )
    result = verify_release_dual_head_contract(
        REPO,
        implementation_source_head=IMPLEMENTATION_SOURCE_HEAD,
        pointer_head_at_release=IMPLEMENTATION_SOURCE_HEAD,
        critical_implementation_manifest_sha256=manifest["manifest_sha256"],
        execution_heads=_heads(),
        execution_review_heads=_heads(),
    )
    assert result["pointer_only_changed_paths"] == []


@pytest.mark.parametrize(
    "mutation",
    ["source", "pointer", "manifest", "execution_heads", "review_heads", "fixed_dp"],
)
def test_dual_head_drift_fails_closed(mutation: str) -> None:
    kwargs = {
        "implementation_source_head": IMPLEMENTATION_SOURCE_HEAD,
        "pointer_head_at_release": POINTER_HEAD,
        "critical_implementation_manifest_sha256": (
            CRITICAL_IMPLEMENTATION_MANIFEST_SHA256
        ),
        "execution_heads": _heads(POINTER_HEAD),
        "execution_review_heads": _heads(POINTER_HEAD),
        "fixed_dp_head": FIXED_DP_HEAD,
    }
    current = subprocess.check_output(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
    ).strip()
    if mutation == "source":
        kwargs["implementation_source_head"] = current
    elif mutation == "pointer":
        kwargs["pointer_head_at_release"] = current
    elif mutation == "manifest":
        kwargs["critical_implementation_manifest_sha256"] = HEX_A
    elif mutation == "execution_heads":
        kwargs["execution_heads"] = _heads(IMPLEMENTATION_SOURCE_HEAD)
    elif mutation == "review_heads":
        kwargs["execution_review_heads"] = _heads(IMPLEMENTATION_SOURCE_HEAD)
    else:
        kwargs["fixed_dp_head"] = HEX_A
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        verify_release_dual_head_contract(REPO, **kwargs)


def _authority() -> dict[str, object]:
    correction_head = subprocess.check_output(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True
    ).strip()
    head8 = correction_head[:8]
    return freeze_correction_authority(
        holdout_identity_sha256=HOLDOUT_IDENTITY_SHA256,
        experiment_protocol_sha256=EXPERIMENT_PROTOCOL_SHA256,
        execution_plan_sha256=EXECUTION_PLAN_SHA256,
        run_nonce=RUN_NONCE,
        controller_decision={"path": "/controller", "root_sha256": CONTROLLER_ROOT_SHA256},
        opening_release={"path": "/release", "root_sha256": OPENING_RELEASE_ROOT_SHA256},
        execution={"path": "/execution", "root_sha256": EXECUTION_ROOT_SHA256},
        execution_review={"path": "/execution-review", "root_sha256": EXECUTION_REVIEW_ROOT_SHA256},
        implementation_source_head=IMPLEMENTATION_SOURCE_HEAD,
        pointer_head_at_release=POINTER_HEAD,
        pointer_only_changed_paths=POINTER_ONLY_PATHS,
        critical_implementation_manifest_sha256=CRITICAL_IMPLEMENTATION_MANIFEST_SHA256,
        old_evaluation_control={
            "directory": "/control",
            "run_exit": 1,
            "error_type": "ValueError",
            "error_message": OLD_EVALUATION_ERROR,
            "command": {"path": "/control/run.sh", "sha256": OLD_CONTROL_COMMAND_SHA256},
            "run_exit_file": {"path": "/control/run.exit", "sha256": OLD_CONTROL_RUN_EXIT_SHA256},
            "stderr": {"path": "/control/stderr.log", "sha256": OLD_CONTROL_STDERR_SHA256},
        },
        old_terminal_closeout={"path": "/closeout", "root_sha256": OLD_CLOSEOUT_ROOT_SHA256},
        old_terminal_closeout_review={"path": "/closeout-review", "root_sha256": OLD_CLOSEOUT_REVIEW_ROOT_SHA256},
        old_scientific_ledger={
            "path": "/scientific.json",
            "sha256": OLD_TERMINAL_LEDGER_SHA256,
            "state": "terminal_failure",
            "history": list(OLD_TERMINAL_HISTORY),
            "terminal_reason": OLD_TERMINAL_REASON,
            "terminal_artifact_root_sha256": OLD_CLOSEOUT_ROOT_SHA256,
        },
        correction_implementation={
            "head": correction_head,
            "manifest_sha256": HEX_A,
            "manifest_paths": list(CORRECTION_IMPLEMENTATION_PATHS),
        },
        focused_tests={"path": "/focused", "root_sha256": HEX_B},
        corrected_evaluation_output_dir=(
            "/root/autodl-tmp/"
            f"camp_dp_v25_fresh_b4_evaluation_corrected_{head8}_8680c1b19ce0620b"
        ),
        corrected_evaluation_review_output_dir=(
            "/root/autodl-tmp/"
            f"camp_dp_v25_fresh_b4_evaluation_corrected_review_{head8}_8680c1b19ce0620b"
        ),
        continuation_cas_namespace="/root/autodl-tmp/b4-correction-cas",
        continuation_identity_slot_namespace="/root/autodl-tmp/b4-correction-slots",
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("benchmark",), "fresh_b3"),
        (("fresh_execution_rerun",), True),
        (("raw_outcome_inspected_before_authority",), True),
        (("scientific_contract_changed",), True),
        (("old_evaluation_control", "run_exit"), 0),
        (("execution", "root_sha256"), HEX_A),
        (("pointer_only_changed_paths",), ["docs/other.md"]),
    ],
)
def test_authority_mutations_fail_closed(
    path: tuple[str, ...], value: object
) -> None:
    authority = copy.deepcopy(_authority())
    target = authority
    for key in path[:-1]:
        target = target[key]  # type: ignore[index,assignment]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValueError):
        validate_correction_authority(authority)


def test_authority_unknown_field_fails_closed() -> None:
    authority = _authority()
    authority["outcome"] = {"benefit": 1.0}
    with pytest.raises(ValueError):
        validate_correction_authority(authority)


@pytest.mark.skipif(os.name == "nt", reason="continuation CAS stores POSIX authority paths")
def test_continuation_is_exclusive_and_monotonic(tmp_path: Path) -> None:
    cas = tmp_path / "cas"
    slots = tmp_path / "slots"
    kwargs = {
        "cas_namespace": cas,
        "identity_slot_namespace": slots,
        "holdout_identity_sha256": HOLDOUT_IDENTITY_SHA256,
        "experiment_protocol_sha256": EXPERIMENT_PROTOCOL_SHA256,
        "run_nonce": RUN_NONCE,
        "opening_release_root_sha256": OPENING_RELEASE_ROOT_SHA256,
        "old_terminal_ledger_path": "/preserved/scientific.json",
        "old_terminal_ledger_sha256": OLD_TERMINAL_LEDGER_SHA256,
        "old_terminal_reason": OLD_TERMINAL_REASON,
        "correction_authority_root_sha256": HEX_A,
        "correction_authority_review_root_sha256": HEX_B,
        "corrected_evaluation_output_dir": "/corrected/evaluation",
        "corrected_evaluation_review_output_dir": "/corrected/review",
    }
    path, first = authorize_from_preserved_denominator(**kwargs)
    assert first["state"] == "authorized_from_preserved_denominator"
    with pytest.raises(FileExistsError):
        authorize_from_preserved_denominator(**kwargs)
    started = start_corrected_evaluation(
        path,
        correction_authority_root_sha256=HEX_A,
        corrected_evaluation_output_dir="/corrected/evaluation",
    )
    assert started["state"] == "evaluation_started"
    formed = mark_corrected_evaluation_artifact_formed(
        path,
        correction_authority_root_sha256=HEX_A,
        corrected_evaluation_output_dir="/corrected/evaluation",
        evaluation_root_sha256="c" * 64,
    )
    assert formed["state"] == "evaluation_artifact_formed"
    terminal = mark_independently_reviewed_terminal(
        path,
        correction_authority_root_sha256=HEX_A,
        corrected_evaluation_review_output_dir="/corrected/review",
        evaluation_review_root_sha256="d" * 64,
    )
    assert terminal["state"] == "independently_reviewed_terminal"
    assert validate_continuation_ledger(load_continuation_ledger(path)) == terminal
    with pytest.raises(FileExistsError):
        start_corrected_evaluation(
            path,
            correction_authority_root_sha256=HEX_A,
            corrected_evaluation_output_dir="/corrected/evaluation",
        )


def test_reviewer_does_not_import_correction_producer_validator() -> None:
    source = (
        REPO / "scripts/integrations/review_diffusion_planner_v25_holdout_evaluation.py"
    ).read_text(encoding="utf-8")
    authority_review = (
        REPO
        / "scripts/integrations/review_diffusion_planner_v25_b4_evaluation_policy_correction.py"
    ).read_text(encoding="utf-8")
    assert "validate_correction_authority" not in authority_review
    assert "verify_release_dual_head_contract" not in authority_review
    assert "validate_correction_authority" not in source
    assert "if corrected:" in source
    assert "mark_independently_reviewed_terminal" in source
