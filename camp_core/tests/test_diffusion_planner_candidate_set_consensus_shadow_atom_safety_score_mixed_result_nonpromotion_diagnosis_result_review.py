from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _diagnosis_payload(*, worse: int = 7, blocked_action: bool = False) -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_ready"
            ),
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_result_review_only"
            ),
            "mixed_result_nonpromotion_diagnosis_ready": True,
            "mixed_result_nonpromotion_diagnosis_result_review_authorized": True,
            "diagnosis_class": "mixed_nonpromotion",
            "sample_too_small_for_promotion": True,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": blocked_action,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
            "failed_checks": [],
        },
        "diagnosis_summary": {
            "diagnosis_class": "mixed_nonpromotion",
            "records": 60,
            "better_only_lambda_count": 3,
            "worse_lambda_count": 2 if worse else 0,
            "sample_too_small_for_promotion": True,
            "safety_benefit_evidence": False,
            "atom_promotion_recommended": False,
            "by_fallback": {
                "nonfallback": {
                    "changed_records": 23,
                    "better_records": 16,
                    "same_records": 0,
                    "worse_records": worse,
                    "mean_delta": 0.000860317214553384,
                }
            },
        },
    }


def _write_root(
    tmp_path: Path,
    *,
    exit_code: str = "0",
    payload: dict[str, object] | None = None,
) -> Path:
    root = tmp_path / "diagnosis"
    root.mkdir()
    (root / "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_execution.json").write_text(
        json.dumps(payload or _diagnosis_payload()),
        encoding="utf-8",
    )
    (root / "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_execution.md").write_text(
        "# diagnosis\n",
        encoding="utf-8",
    )
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text(f"{exit_code}\n", encoding="utf-8")
    (root / "HEADS.txt").write_text("CAMP_HEAD=head\nDP_HEAD=dp\n", encoding="utf-8")
    _write_sha256sums(
        root,
        (
            "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_execution.json",
            "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_execution.md",
            "COMMAND.log",
            "COMMAND.err",
            "EXIT_CODE",
            "HEADS.txt",
        ),
    )
    return root


def test_diagnosis_result_review_ready(tmp_path: Path) -> None:
    root = _write_root(tmp_path)

    report = build_report(diagnosis_root=root, label="unit")
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["nonpromotion_closeout_plan_authorized"] is True
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert report["result_review"]["closeout_classification"] == (
        "confirmed_mixed_nonpromotion_closeout_needed"
    )


def test_diagnosis_result_review_rejects_sha_mismatch(tmp_path: Path) -> None:
    root = _write_root(tmp_path)
    (root / "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_execution.md").write_text(
        "# mutated\n",
        encoding="utf-8",
    )

    report = build_report(diagnosis_root=root)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "artifact_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_diagnosis_result_review_rejects_nonzero_exit(tmp_path: Path) -> None:
    root = _write_root(tmp_path, exit_code="1")

    report = build_report(diagnosis_root=root)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "artifact_exit_code_zero" in report["final_decision"]["failed_checks"]


def test_diagnosis_result_review_rejects_unconfirmed_mixed(tmp_path: Path) -> None:
    root = _write_root(tmp_path, payload=_diagnosis_payload(worse=0))

    report = build_report(diagnosis_root=root)

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_classification_confirmed" in failed
    assert "review_authorizes_closeout_plan" in failed


def test_diagnosis_result_review_markdown_boundaries(tmp_path: Path) -> None:
    root = _write_root(tmp_path)

    markdown = render_markdown(build_report(diagnosis_root=root))

    assert "Diagnosis Result Review" in markdown
    assert "Safety benefit evidence: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "classical Benders" in markdown


def test_diagnosis_result_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_root(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "diagnosis-result-review",
            "--diagnosis_root",
            str(root),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Diagnosis Result Review" in output_md.read_text(encoding="utf-8")
