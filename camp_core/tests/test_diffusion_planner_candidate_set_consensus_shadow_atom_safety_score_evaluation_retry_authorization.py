from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.authorize_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_retry import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)


RUN_IDS = (
    "sample_tl59_seed1_npc0_tlon",
    "sample_tl59_seed2_npc4_tlon",
    "sample_tl59_seed3_npc4_tloff",
    "sample_normal2_seed1_npc0_tloff",
    "nishi_release_seed2_npc4_tlon",
    "nishi_lanechange_seed4_npc4_tloff",
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _retry_plan_payload(
    *,
    label_root: Path,
    run_ids: tuple[str, ...] = RUN_IDS,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_retry_consideration_plan_ready"
            ),
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_retry_authorization_only"
            ),
            "safety_score_evaluation_retry_plan_ready": True,
            "safety_score_evaluation_retry_authorization_gate_authorized": True,
            "label_attachment_authorized": False,
            "safety_score_evaluation_retry_authorized": False,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
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
        "retry_consideration_plan": {
            "source_review_json": "/artifact/source_review.json",
            "weight_sensitivity_json": "/artifact/weight.json",
            "label_root": str(label_root),
            "evaluator_script": (
                "scripts/integrations/analyze_diffusion_planner_candidate_set_"
                "consensus_shadow_atom_safety_score_evaluation.py"
            ),
            "future_evaluator_command": [
                "python",
                (
                    "scripts/integrations/analyze_diffusion_planner_candidate_set_"
                    "consensus_shadow_atom_safety_score_evaluation.py"
                ),
                "--weight_sensitivity_json",
                "/artifact/weight.json",
                "--candidate_root",
                str(label_root),
                "--require_pass",
            ],
            "fixed_dp_head": EXPECTED_DP_HEAD,
            "expected_logs": 6,
            "expected_records": 60,
            "expected_candidates": 8,
            "route_seed_matrix": [
                {
                    "run_id": run_id,
                    "seed": index + 1,
                    "formal": False,
                }
                for index, run_id in enumerate(run_ids)
            ],
            "scenario_coverage": {
                "traffic_light": ["sample_tl59_seed1_npc0_tlon"],
                "turn": ["sample_tl59_seed1_npc0_tlon"],
                "normal": ["sample_normal2_seed1_npc0_tloff"],
            },
            "accept_criteria": [
                "formal seed strings remain absent",
                "future retry remains read-only and offline with no online selector effect",
            ],
            "reject_criteria": [
                "any gate attempts to train CAMP, promote an atom, enable online selection, run replay, or modify DP",
            ],
        },
    }


def _source_review_payload() -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "outcome_label_source_review_ready"
            ),
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_retry_consideration_plan_only"
            ),
            "outcome_label_source_review_ready": True,
            "safety_score_evaluation_retry_plan_authorized": True,
            "label_attachment_authorized": False,
            "safety_score_evaluation_retry_authorized": False,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
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
        "source_review": {
            "run_ids": list(RUN_IDS),
            "run_count": 6,
            "label_records": 60,
            "broader_records": 60,
            "records_compared": 60,
            "compatibility_mismatch_count": 0,
            "label_complete_outcome_records": 60,
            "broader_outcome_records_present": 0,
            "payload_no_leak_records": 60,
            "formal_seed_log_count": 0,
            "errors": [],
        },
    }


def _weight_payload() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "candidate_set_consensus_shadow_atom_weight_sensitivity_ready",
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_weight_sensitivity_"
                "result_review_only"
            ),
            "weight_sensitivity_ready": True,
            "max_changed_records": 10,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
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
        "sensitivity_summary": {
            "log_count": 6,
            "records": 60,
            "valid_records": 60,
            "formal_seed_log_count": 0,
            "record_error_counts": {},
            "by_lambda": [
                {"lambda": 0.0, "changed_records": 0},
                {"lambda": 1.0, "changed_records": 10},
            ],
        },
    }


def _row() -> dict[str, object]:
    return {
        "candidate_closed_loop_outcomes": [
            {"candidate_index": index, "progress_m": 1.0} for index in range(8)
        ],
        "candidate_set_consensus_payload_logging": {
            "closed_loop_outcome_fields_read": False,
            "future_outcome_leakage": False,
            "classical_benders_claim": False,
        },
    }


def _write_artifacts(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    retry_plan_root = tmp_path / "retry_plan"
    source_review_root = tmp_path / "source_review"
    weight_root = tmp_path / "weight"
    label_root = tmp_path / "labels"
    retry_plan_root.mkdir()
    source_review_root.mkdir()
    weight_root.mkdir()
    (retry_plan_root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_consideration_plan.json").write_text(
        json.dumps(_retry_plan_payload(label_root=label_root)),
        encoding="utf-8",
    )
    (retry_plan_root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_consideration_plan.md").write_text(
        "# retry plan\n",
        encoding="utf-8",
    )
    (retry_plan_root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (retry_plan_root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        retry_plan_root,
        (
            "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_consideration_plan.json",
            "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_consideration_plan.md",
            "COMMAND.log",
            "HEADS.txt",
        ),
    )
    (source_review_root / "candidate_set_consensus_shadow_atom_safety_score_outcome_label_source_review.json").write_text(
        json.dumps(_source_review_payload()),
        encoding="utf-8",
    )
    (source_review_root / "candidate_set_consensus_shadow_atom_safety_score_outcome_label_source_review.md").write_text(
        "# source review\n",
        encoding="utf-8",
    )
    (source_review_root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        source_review_root,
        (
            "candidate_set_consensus_shadow_atom_safety_score_outcome_label_source_review.json",
            "candidate_set_consensus_shadow_atom_safety_score_outcome_label_source_review.md",
            "HEADS.txt",
        ),
    )
    (weight_root / "candidate_set_consensus_shadow_atom_weight_sensitivity.json").write_text(
        json.dumps(_weight_payload()),
        encoding="utf-8",
    )
    (weight_root / "candidate_set_consensus_shadow_atom_weight_sensitivity.md").write_text(
        "# weight\n",
        encoding="utf-8",
    )
    (weight_root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        weight_root,
        (
            "candidate_set_consensus_shadow_atom_weight_sensitivity.json",
            "candidate_set_consensus_shadow_atom_weight_sensitivity.md",
            "HEADS.txt",
        ),
    )
    for run_id in RUN_IDS:
        run_root = label_root / run_id
        run_root.mkdir(parents=True)
        (run_root / "camp_selection_log.json").write_text(
            json.dumps([_row() for _ in range(10)]),
            encoding="utf-8",
        )
    return retry_plan_root, source_review_root, weight_root, label_root


def test_evaluation_retry_authorization_ready(tmp_path: Path) -> None:
    retry_plan_root, source_review_root, weight_root, label_root = _write_artifacts(
        tmp_path
    )

    report = build_report(
        retry_plan_root=retry_plan_root,
        source_review_root=source_review_root,
        weight_sensitivity_root=weight_root,
        label_root=label_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["safety_score_evaluation_retry_execution_authorized"] is True
    assert decision["safety_score_evaluation_retry_executed"] is False
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert report["label_root_summary"]["complete_outcome_records"] == 60


def test_evaluation_retry_authorization_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    retry_plan_root, source_review_root, weight_root, label_root = _write_artifacts(
        tmp_path
    )
    (retry_plan_root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_consideration_plan.md").write_text(
        "# mutated\n",
        encoding="utf-8",
    )

    report = build_report(
        retry_plan_root=retry_plan_root,
        source_review_root=source_review_root,
        weight_sensitivity_root=weight_root,
        label_root=label_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "retry_plan_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_evaluation_retry_authorization_rejects_dp_mismatch(tmp_path: Path) -> None:
    retry_plan_root, source_review_root, weight_root, label_root = _write_artifacts(
        tmp_path
    )

    report = build_report(
        retry_plan_root=retry_plan_root,
        source_review_root=source_review_root,
        weight_sensitivity_root=weight_root,
        label_root=label_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_evaluation_retry_authorization_rejects_missing_outcomes(
    tmp_path: Path,
) -> None:
    retry_plan_root, source_review_root, weight_root, label_root = _write_artifacts(
        tmp_path
    )
    path = label_root / RUN_IDS[0] / "camp_selection_log.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows[0]["candidate_closed_loop_outcomes"] = None
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = build_report(
        retry_plan_root=retry_plan_root,
        source_review_root=source_review_root,
        weight_sensitivity_root=weight_root,
        label_root=label_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "label_complete_outcome_records" in report["final_decision"][
        "failed_checks"
    ]


def test_evaluation_retry_authorization_rejects_formal_seed(tmp_path: Path) -> None:
    retry_plan_root, source_review_root, weight_root, label_root = _write_artifacts(
        tmp_path
    )
    run_root = label_root / "sample_tl59_seed11_npc4_tlon"
    run_root.mkdir()
    (run_root / "camp_selection_log.json").write_text(
        json.dumps([_row() for _ in range(10)]),
        encoding="utf-8",
    )

    report = build_report(
        retry_plan_root=retry_plan_root,
        source_review_root=source_review_root,
        weight_sensitivity_root=weight_root,
        label_root=label_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "label_log_count" in failed
    assert "label_no_formal_seed_logs" in failed


def test_evaluation_retry_authorization_markdown(tmp_path: Path) -> None:
    retry_plan_root, source_review_root, weight_root, label_root = _write_artifacts(
        tmp_path
    )
    report = build_report(
        retry_plan_root=retry_plan_root,
        source_review_root=source_review_root,
        weight_sensitivity_root=weight_root,
        label_root=label_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Safety-Score Evaluation Retry Authorization" in markdown
    assert "Retry execution authorized: `True`" in markdown
    assert "Retry executed: `False`" in markdown
    assert "candidate_closed_loop_outcomes" in markdown
    assert "classical Benders" in markdown


def test_evaluation_retry_authorization_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    retry_plan_root, source_review_root, weight_root, label_root = _write_artifacts(
        tmp_path
    )
    output_json = tmp_path / "authorization.json"
    output_md = tmp_path / "authorization.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-shadow-atom-safety-score-evaluation-retry-authorization",
            "--retry_plan_root",
            str(retry_plan_root),
            "--source_review_root",
            str(source_review_root),
            "--weight_sensitivity_root",
            str(weight_root),
            "--label_root",
            str(label_root),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
            "--dp_head",
            EXPECTED_DP_HEAD,
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
    assert "Retry Authorization" in output_md.read_text(encoding="utf-8")
