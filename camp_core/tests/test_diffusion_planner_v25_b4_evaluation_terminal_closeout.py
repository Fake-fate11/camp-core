from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_b4_evaluation_terminal_closeout import (  # noqa: E501
    ERROR_MESSAGE,
    freeze_b4_evaluation_terminal_closeout,
    validate_b4_evaluation_terminal_closeout,
)
from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    _strict_canonical_json,
    canonical_json_bytes,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (
    mark_full_denominator,
    reserve_operational_attempt,
    scientific_identity_path,
    seal_operational_release,
    start_scientific_exposure,
)


ROOT = Path(__file__).resolve().parents[2]


def _sha(index: int) -> str:
    return f"{index:064x}"


def _binding(name: str, index: int) -> dict[str, str]:
    return {"path": f"/artifact/{name}", "root_sha256": _sha(index)}


def _file(name: str, index: int) -> dict[str, str]:
    return {"path": f"/control/{name}", "sha256": _sha(index)}


def _closeout() -> dict:
    return freeze_b4_evaluation_terminal_closeout(
        holdout_identity_sha256=_sha(1),
        experiment_protocol_sha256=_sha(2),
        execution_plan_sha256=_sha(3),
        run_nonce=_sha(4),
        controller_decision=_binding("controller", 5),
        opening_release=_binding("release", 6),
        execution=_binding("execution", 7),
        execution_review=_binding("execution-review", 8),
        evaluation_output_dir="/artifact/evaluation",
        evaluation_control={
            "directory": "/control",
            "command": _file("run.sh", 9),
            "command_receipt": _file("run.sha256", 10),
            "run_exit_file": _file("run.exit", 11),
            "run_exit": 1,
            "stderr": _file("stderr.log", 12),
        },
        evaluation_review_output_dir="/artifact/evaluation-review",
        implementation_source_head="1" * 40,
        pointer_head_at_release="2" * 40,
        reporting_machinery_head="3" * 40,
        scientific_ledger_before={
            "path": "/cas/scientific/identity.json",
            "sha256": _sha(13),
            "state": "full_denominator_formed",
        },
    )


def _script_module(filename: str):
    path = ROOT / "scripts" / "integrations" / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_b4_evaluation_terminal_closeout_is_exact_and_outcome_blind() -> None:
    closeout = _closeout()
    assert validate_b4_evaluation_terminal_closeout(closeout) == closeout
    assert closeout["benchmark"] == "fresh_b4"
    assert closeout["phase"] == "evaluation"
    assert closeout["evaluation_artifact_created"] is False
    assert closeout["evaluation_root_sha256"] is None
    assert closeout["evaluation_review_started"] is False
    assert closeout["raw_outcome_values_inspected"] is False
    assert closeout["claim_authorized"] is False
    assert closeout["rerun_allowed"] is False
    assert closeout["complete_paired_row_count"] == 500
    assert closeout["complete_arm_run_count"] == 1500
    assert closeout["full_denominator_formed"] is True


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: row.update(benchmark="fresh_b3"),
        lambda row: row.update(error_message="different error"),
        lambda row: row.update(evaluation_artifact_created=True),
        lambda row: row.update(evaluation_root_sha256=_sha(30)),
        lambda row: row.update(evaluation_review_started=True),
        lambda row: row.update(evaluation_review_artifact_created=True),
        lambda row: row.update(complete_paired_row_count=499),
        lambda row: row.update(complete_arm_run_count=1499),
        lambda row: row.update(terminal_arm_run_count=1499),
        lambda row: row.update(full_denominator_formed=False),
        lambda row: row.update(raw_outcome_values_inspected=True),
        lambda row: row.update(outcome_fields_consumed=["SafetyCost"]),
        lambda row: row.update(rerun_allowed=True),
        lambda row: row.update(claim_authorized=True),
        lambda row: row["execution"].update(root_sha256=_sha(31)),
        lambda row: row["execution_review"].update(root_sha256=_sha(32)),
        lambda row: row["evaluation_control"]["command"].update(
            sha256=_sha(33)
        ),
        lambda row: row["evaluation_control"].update(run_exit=0),
        lambda row: row["scientific_ledger_before"].update(
            state="evaluated"
        ),
    ],
)
def test_b4_closeout_rejects_semantic_drift(mutate) -> None:
    closeout = _closeout()
    mutate(closeout)
    with pytest.raises(ValueError):
        validate_b4_evaluation_terminal_closeout(closeout)


def test_b4_closeout_rejects_missing_unknown_and_b3_disguise() -> None:
    missing = _closeout()
    missing.pop("claim_authorized")
    with pytest.raises(ValueError, match="field set"):
        validate_b4_evaluation_terminal_closeout(missing)
    extra = _closeout()
    extra["fresh_b3_compatible"] = True
    with pytest.raises(ValueError, match="field set"):
        validate_b4_evaluation_terminal_closeout(extra)
    with pytest.raises(ValueError, match="run.exit"):
        freeze_b4_evaluation_terminal_closeout(
            **{
                "holdout_identity_sha256": _sha(1),
                "experiment_protocol_sha256": _sha(2),
                "execution_plan_sha256": _sha(3),
                "run_nonce": _sha(4),
                "controller_decision": _binding("controller", 5),
                "opening_release": _binding("release", 6),
                "execution": _binding("execution", 7),
                "execution_review": _binding("execution-review", 8),
                "evaluation_output_dir": "/artifact/evaluation",
                "evaluation_control": {
                    **_closeout()["evaluation_control"],
                    "run_exit": 0,
                },
                "evaluation_review_output_dir": "/artifact/evaluation-review",
                "implementation_source_head": "1" * 40,
                "pointer_head_at_release": "2" * 40,
                "reporting_machinery_head": "3" * 40,
                "scientific_ledger_before": {
                    "path": "/cas/scientific/identity.json",
                    "sha256": _sha(13),
                    "state": "full_denominator_formed",
                },
            }
        )


def test_independent_reviewer_literal_oracle_rejects_same_drifts() -> None:
    reviewer = _script_module(
        "review_diffusion_planner_v25_b4_evaluation_terminal_closeout.py"
    )
    expected = _closeout()
    assert reviewer.validate_closeout_literal(expected, expected) == expected
    for field, value in (
        ("benchmark", "fresh_b3"),
        ("error_message", "other"),
        ("evaluation_artifact_created", True),
        ("evaluation_root_sha256", _sha(40)),
        ("evaluation_review_started", True),
        ("complete_arm_run_count", 1499),
        ("full_denominator_formed", False),
        ("raw_outcome_values_inspected", True),
        ("claim_authorized", True),
    ):
        changed = copy.deepcopy(expected)
        changed[field] = value
        with pytest.raises(ValueError):
            reviewer.validate_closeout_literal(changed, expected)
    changed = copy.deepcopy(expected)
    changed["evaluation_control"]["command"]["sha256"] = _sha(41)
    with pytest.raises(ValueError):
        reviewer.validate_closeout_literal(changed, expected)


def test_strict_json_rejects_duplicate_fields(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text(
        '{"benchmark":"fresh_b4","benchmark":"fresh_b3"}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="duplicate"):
        _strict_canonical_json(path)


def test_error_message_is_frozen() -> None:
    assert ERROR_MESSAGE == "holdout execution/evaluation role HEAD drifted"


def test_cas_finalizer_transitions_once_after_reviewed_closeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = _sha(1)
    protocol = _sha(2)
    nonce = _sha(4)
    controller_root = _sha(5)
    release_root = _sha(6)
    attempt = reserve_operational_attempt(
        tmp_path / "cas",
        holdout_identity_sha256=identity,
        experiment_protocol_sha256=protocol,
        run_nonce=nonce,
        authorized_output_dir=str((tmp_path / "execution").resolve()),
        controller_root_sha256=controller_root,
    )
    seal_operational_release(
        attempt, opening_release_root_sha256=release_root
    )
    start_scientific_exposure(
        tmp_path / "cas",
        operational_attempt=attempt,
        first_unit_ordinal=0,
        first_arm="candidate0",
    )
    scientific = scientific_identity_path(tmp_path / "cas", identity)
    mark_full_denominator(
        scientific,
        planned_arm_run_count=1500,
        terminal_arm_run_count=1500,
    )
    closeout_dir = tmp_path / "closeout"
    closeout_dir.mkdir()
    (closeout_dir / "closeout.json").write_bytes(b"{}\n")
    (closeout_dir / "run.exit").write_bytes(b"0\n")
    closeout_root = seal_artifact(closeout_dir, label="synthetic closeout")
    review = {
        "schema_version": (
            "camp_dp_v25_fresh_b4_post_exposure_evaluation_control_fatal_"
            "closeout_review_v1"
        ),
        "status": (
            "passed_independent_fresh_b4_evaluation_terminal_closeout_review"
        ),
        "reviewed_root_sha256": closeout_root,
        "holdout_identity_sha256": identity,
        "experiment_protocol_sha256": protocol,
        "execution_plan_sha256": _sha(3),
        "run_nonce": nonce,
        "opening_release_root_sha256": release_root,
        "execution_root_sha256": _sha(7),
        "execution_review_root_sha256": _sha(8),
        "implementation_source_head": "1" * 40,
        "pointer_head_at_release": "2" * 40,
        "fixed_dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "reporting_machinery_head": "3" * 40,
        "control_evidence_rehashed": True,
        "accepted_seals_independently_verified": True,
        "evaluation_artifact_created": False,
        "evaluation_root_sha256": None,
        "evaluation_review_started": False,
        "evaluation_review_artifact_created": False,
        "related_process_count": 0,
        "scientific_state_before": "full_denominator_formed",
        "planned_pair_count": 500,
        "complete_paired_row_count": 500,
        "planned_arm_run_count": 1500,
        "complete_arm_run_count": 1500,
        "terminal_arm_run_count": 1500,
        "full_denominator_formed": True,
        "raw_outcome_values_inspected": False,
        "rerun_allowed": False,
        "claim_authorized": False,
        "evaluation_result_status": (
            "unavailable_due_to_post_exposure_evaluation_fatal"
        ),
        "independent_oracle": "reviewer_local_literal_v1",
        "next_authority": "final_report_and_ultra_terminal_review_only",
    }
    review_dir = tmp_path / "review"
    review_dir.mkdir()
    (review_dir / "report.json").write_bytes(canonical_json_bytes(review))
    (review_dir / "run.exit").write_bytes(b"0\n")
    review_root = seal_artifact(review_dir, label="synthetic review")
    closeout = _closeout()
    closeout.update(
        {
            "holdout_identity_sha256": identity,
            "experiment_protocol_sha256": protocol,
            "execution_plan_sha256": _sha(3),
            "run_nonce": nonce,
            "opening_release": {
                "path": "/artifact/release",
                "root_sha256": release_root,
            },
            "execution": {
                "path": "/artifact/execution",
                "root_sha256": _sha(7),
            },
            "execution_review": {
                "path": "/artifact/execution-review",
                "root_sha256": _sha(8),
            },
            "scientific_ledger_before": {
                "path": str(scientific.resolve()),
                "sha256": hashlib.sha256(scientific.read_bytes()).hexdigest(),
                "state": "full_denominator_formed",
            },
        }
    )
    finalizer = _script_module(
        "finalize_diffusion_planner_v25_b4_evaluation_terminal_failure.py"
    )
    monkeypatch.setattr(
        finalizer,
        "validate_b4_evaluation_terminal_closeout",
        lambda _value: closeout,
    )
    result = finalizer.finalize(
        closeout_artifact=closeout_dir,
        closeout_root_sha256=closeout_root,
        closeout_review_artifact=review_dir,
        closeout_review_root_sha256=review_root,
        scientific_ledger_path=scientific,
    )
    assert result["scientific_state"] == "terminal_failure"
    assert result["terminal_artifact_root_sha256"] == closeout_root
    with pytest.raises(ValueError):
        finalizer.finalize(
            closeout_artifact=closeout_dir,
            closeout_root_sha256=closeout_root,
            closeout_review_artifact=review_dir,
            closeout_review_root_sha256=review_root,
            scientific_ledger_path=scientific,
        )
