from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_result import (
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


def _execution_payload(
    *,
    status: str = "candidate_set_consensus_shadow_atom_safety_score_evaluation_ready",
    passed: bool = True,
    blocked_action: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_result_review_only"
            )
            if passed
            else None,
            "failed_checks": [],
            "safety_score_evaluation_ready": passed,
            "safety_score_evaluation_result_review_authorized": passed,
            "max_changed_records": 11,
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
        },
        "evaluation_summary": {
            "log_count": 6,
            "records": 60,
            "valid_records": 60,
            "outcome_available_records": 60,
            "fallback_retained_records": 12,
            "formal_seed_log_count": 0,
            "record_error_counts": {},
            "max_changed_records": 11,
            "by_run": {"run": {"records": 10}},
            "by_lambda": [
                {
                    "lambda": 0.0,
                    "changed_records": 0,
                    "changed_cost_better_records": 0,
                    "changed_cost_same_records": 0,
                    "changed_cost_worse_records": 0,
                    "changed_hard_worse_records": 0,
                    "changed_safety_cost_delta_mean": None,
                },
                {
                    "lambda": 0.05,
                    "changed_records": 1,
                    "changed_cost_better_records": 1,
                    "changed_cost_same_records": 0,
                    "changed_cost_worse_records": 0,
                    "changed_hard_worse_records": 0,
                    "changed_safety_cost_delta_mean": -0.02,
                },
                {
                    "lambda": 0.5,
                    "changed_records": 6,
                    "changed_cost_better_records": 4,
                    "changed_cost_same_records": 0,
                    "changed_cost_worse_records": 2,
                    "changed_hard_worse_records": 0,
                    "changed_safety_cost_delta_mean": 0.02,
                },
                {
                    "lambda": 1.0,
                    "changed_records": 11,
                    "changed_cost_better_records": 6,
                    "changed_cost_same_records": 0,
                    "changed_cost_worse_records": 5,
                    "changed_hard_worse_records": 0,
                    "changed_safety_cost_delta_mean": 0.005,
                },
            ],
        },
    }


def _write_execution_root(
    tmp_path: Path,
    *,
    exit_code: str = "0",
    payload: dict[str, object] | None = None,
) -> Path:
    root = tmp_path / "execution"
    root.mkdir()
    (root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_execution.json").write_text(
        json.dumps(payload or _execution_payload()),
        encoding="utf-8",
    )
    (root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_execution.md").write_text(
        "# execution\n",
        encoding="utf-8",
    )
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text(f"{exit_code}\n", encoding="utf-8")
    (root / "HEADS.txt").write_text("CAMP_HEAD=head\nDP_HEAD=dp\n", encoding="utf-8")
    _write_sha256sums(
        root,
        (
            "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_execution.json",
            "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_execution.md",
            "COMMAND.log",
            "COMMAND.err",
            "EXIT_CODE",
            "HEADS.txt",
        ),
    )
    return root


def test_safety_score_evaluation_result_review_ready(tmp_path: Path) -> None:
    root = _write_execution_root(tmp_path)

    report = build_report(execution_root=root, label="unit")
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["result_classification"] == "mixed_nonpromotion"
    assert decision["mixed_result_nonpromotion_diagnosis_plan_authorized"] is True
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert report["result_classification"]["worse_lambda_count"] == 2
    assert report["evaluation_summary"]["max_changed_records"] == 11


def test_safety_score_evaluation_result_review_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    root = _write_execution_root(tmp_path)
    (root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_execution.md").write_text(
        "# mutated\n",
        encoding="utf-8",
    )

    report = build_report(execution_root=root)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "artifact_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_safety_score_evaluation_result_review_rejects_nonzero_exit(
    tmp_path: Path,
) -> None:
    root = _write_execution_root(tmp_path, exit_code="1")

    report = build_report(execution_root=root)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "artifact_exit_code_zero" in report["final_decision"]["failed_checks"]


def test_safety_score_evaluation_result_review_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    root = _write_execution_root(
        tmp_path,
        payload=_execution_payload(blocked_action=True),
    )

    report = build_report(execution_root=root)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "evaluation_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_safety_score_evaluation_result_review_markdown_boundaries(
    tmp_path: Path,
) -> None:
    root = _write_execution_root(tmp_path)

    markdown = render_markdown(build_report(execution_root=root))

    assert "Safety-Score Evaluation Result Review" in markdown
    assert "Result classification: `mixed_nonpromotion`" in markdown
    assert "Safety benefit evidence: `False`" in markdown
    assert "Atom promotion authorized: `False`" in markdown
    assert "classical Benders" in markdown


def test_safety_score_evaluation_result_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_execution_root(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "safety-score-evaluation-result-review",
            "--execution_root",
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
    assert "Result Review" in output_md.read_text(encoding="utf-8")
