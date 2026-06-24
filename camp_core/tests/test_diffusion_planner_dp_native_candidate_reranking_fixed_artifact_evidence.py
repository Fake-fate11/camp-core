from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_dp_native_candidate_reranking_fixed_artifact_evidence import (
    COMPLETE_STATUS,
    GAP_NEXT_WORK,
    READY_NEXT_WORK,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _record(*, selected_index: int = 1, tensor_hash: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "selection_step": 0,
        "selected_index": selected_index,
        "num_candidates": 2,
        "feasible_mask": [True, False],
        "infeasibility_reasons": [[], ["dp_kinematic"]],
        "scores": [0.1, 0.2],
        "selection_scores": [0.1, 0.2],
        "atoms": [[0.1, 0.0], [0.2, 0.3]],
        "normalized_atoms": [[0.1, 0.0], [0.2, 0.3]],
        "candidate_first_reference_xy": [[1.0, 2.0], [3.0, 4.0]],
        "candidate_perfect_tracker_reference_first_xy": [[1.0, 2.0], [3.0, 4.0]],
        "candidate_perfect_tracker_first_step_reach_m": [0.5, 0.6],
    }
    if tensor_hash:
        payload["candidate_tensor_sha256"] = "abc123"
        payload["raw_candidate_tensor"] = [
            [[1.0, 2.0, 0.0, 1.0]],
            [[3.0, 4.0, 0.0, 1.0]],
        ]
    return payload


def _selector_equivalence(*, equivalent: bool = True) -> dict[str, object]:
    value = 0 if equivalent else 1
    return {
        "equivalent": equivalent,
        "records": 1,
        "exact_field_mismatches": {
            "selected_index": value,
            "feasible_mask": 0,
            "infeasibility_reasons": 0,
        },
        "numeric_field_mismatches": {
            "scores": 0,
            "selection_scores": 0,
            "atoms": 0,
            "normalized_atoms": 0,
        },
        "numeric_shape_mismatches": {
            "scores": 0,
            "selection_scores": 0,
            "atoms": 0,
            "normalized_atoms": 0,
        },
        "numeric_nonexact_entries": {
            "scores": 0,
            "selection_scores": 0,
            "atoms": 0,
            "normalized_atoms": 0,
        },
    }


def _payload_audit() -> dict[str, object]:
    return {
        "analysis": {
            "selection_effect_allowed": False,
            "future_outcome_labels_used": False,
        },
        "counts": {
            "records": 1,
            "available_payload_records": 1,
            "invalid_payload_records": 0,
        },
        "final_decision": {
            "status": "candidate_set_consensus_payload_smoke_audit_passed",
            "passed": True,
            "new_replay_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _dataset_audit() -> dict[str, object]:
    return {
        "passed": True,
        "counts": {"records": 1, "candidates": 2},
        "checks": {
            "finite_candidate_contract_verified": True,
            "closed_loop_outcomes_forbidden": True,
            "closed_loop_outcome_records": 0,
            "forbidden_seed_check": True,
        },
    }


def _replay_summary(
    *,
    tensor_hash: bool = False,
    changes_candidate_set: bool = True,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "num_candidates": 2,
        "candidate_generation_contract": {
            "num_candidates": 2,
            "changes_candidate_set": changes_candidate_set,
            "changes_camp_score": False,
            "changes_diffusion_planner_weights": False,
        },
        "candidate_reference_blend": {
            "selection_effect": changes_candidate_set,
        },
        "dp_camp_finite_candidate_contract": {
            "candidate_set": "fixed current-tick Diffusion Planner candidate tensor before CAMP scoring",
            "score": "a_ik^T w",
            "selection_rule": "argmin over finite feasible candidates by CAMP selection score",
        },
    }
    if tensor_hash:
        summary["candidate_tensor_sha256"] = "abc123"
    return summary


def _oracle() -> dict[str, object]:
    return {
        "analysis": {
            "future_outcome_leakage": False,
            "training": False,
            "online_selector_change": False,
        },
        "opportunity_gate": {
            "passed": True,
            "interpretation": "fixed DP candidate pool contains alternatives",
        },
        "overall": {"mean_eligible_candidates": 1.5},
        "records": {"total": 10},
    }


def _design_plan() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "dp_native_candidate_reranking_design_plan_ready",
            "passed": True,
            "authorized_next_work": (
                "dp_native_candidate_reranking_fixed_artifact_evidence_audit_only"
            ),
            "candidate_generation_execution_authorized": False,
            "trajectory_rewrite_authorized": False,
            "candidate_tensor_mutation_authorized": False,
        },
        "design_plan": {"route": "dp_native_candidate_reranking_only"},
    }


def _report(
    *,
    selector_equivalent: bool = True,
    selected_index: int = 1,
    tensor_hash: bool = False,
    changes_candidate_set: bool = True,
) -> dict[str, object]:
    records = [_record(selected_index=selected_index, tensor_hash=tensor_hash)]
    return build_report(
        selector_equivalence=_selector_equivalence(equivalent=selector_equivalent),
        payload_audit=_payload_audit(),
        dataset_audit=_dataset_audit(),
        baseline_selection_log=records,
        candidate_selection_log=records,
        baseline_replay_summary=_replay_summary(
            tensor_hash=tensor_hash,
            changes_candidate_set=changes_candidate_set,
        ),
        candidate_replay_summary=_replay_summary(
            tensor_hash=tensor_hash,
            changes_candidate_set=changes_candidate_set,
        ),
        safety_cost_oracle=_oracle(),
        design_plan=_design_plan(),
        source_paths={"selector": "/tmp/selector.json"},
    )


def test_evidence_audit_completes_but_records_tensor_provenance_gap() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == COMPLETE_STATUS
    assert decision["evidence_audit_complete"] is True
    assert decision["dp_native_reranking_evidence_ready"] is False
    assert decision["authorized_next_work"] == GAP_NEXT_WORK
    assert "candidate_tensor_hash_missing" in decision["evidence_gaps"]
    assert "raw_dp_pre_camp_candidate_set_immutability_not_proven" in decision[
        "evidence_gaps"
    ]
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["camp_retraining_authorized"] is False


def test_evidence_audit_ready_when_tensor_hash_and_no_candidate_set_change() -> None:
    report = _report(tensor_hash=True, changes_candidate_set=False)
    decision = report["final_decision"]

    assert decision["status"] == COMPLETE_STATUS
    assert decision["dp_native_reranking_evidence_ready"] is True
    assert decision["authorized_next_work"] == READY_NEXT_WORK
    assert decision["evidence_gaps"] == []
    assert decision["weak_evidence"] == []


def test_evidence_audit_rejects_selector_mismatch() -> None:
    report = _report(selector_equivalent=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "selector_equivalent" in report["final_decision"]["failed_checks"]
    assert "selector_required_exact_zero" in report["final_decision"]["failed_checks"]


def test_evidence_audit_rejects_selected_index_out_of_range() -> None:
    report = _report(selected_index=3)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "baseline_selected_index_range" in report["final_decision"]["failed_checks"]
    assert "candidate_selected_index_range" in report["final_decision"]["failed_checks"]


def test_evidence_audit_markdown_reports_no_claim_boundary() -> None:
    markdown = render_markdown(_report())

    assert "DP-Native Candidate Reranking Fixed-Artifact Evidence Audit" in markdown
    assert "Candidate generation authorized: `False`" in markdown
    assert "candidate_tensor_hash_missing" in markdown
    assert "does not generate candidates" in markdown


def test_evidence_audit_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    audit_dir = source / "candidate_set_consensus_payload_smoke" / "audit"
    baseline_dir = source / "candidate_set_consensus_payload_smoke" / "baseline"
    candidate_dir = source / "candidate_set_consensus_payload_smoke" / "logging_enabled"
    oracle_dir = source / "safety_cost_oracle_d2899e6"
    plan_dir = source / "dp_native_candidate_reranking_design_plan_b330901"
    for directory in (audit_dir, baseline_dir, candidate_dir, oracle_dir, plan_dir):
        directory.mkdir(parents=True)
    (audit_dir / "selector_equivalence.json").write_text(
        json.dumps(_selector_equivalence()),
        encoding="utf-8",
    )
    (audit_dir / "candidate_set_consensus_payload_smoke.json").write_text(
        json.dumps(_payload_audit()),
        encoding="utf-8",
    )
    (audit_dir / "dataset_audit.json").write_text(
        json.dumps(_dataset_audit()),
        encoding="utf-8",
    )
    log_text = json.dumps([_record()])
    (baseline_dir / "camp_selection_log.json").write_text(log_text, encoding="utf-8")
    (candidate_dir / "camp_selection_log.json").write_text(log_text, encoding="utf-8")
    summary_text = json.dumps(_replay_summary())
    (baseline_dir / "camp_replay_summary.json").write_text(
        summary_text,
        encoding="utf-8",
    )
    (candidate_dir / "camp_replay_summary.json").write_text(
        summary_text,
        encoding="utf-8",
    )
    (oracle_dir / "safety_cost_oracle.json").write_text(
        json.dumps(_oracle()),
        encoding="utf-8",
    )
    (plan_dir / "dp_native_candidate_reranking_design_plan.json").write_text(
        json.dumps(_design_plan()),
        encoding="utf-8",
    )
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "evidence-audit",
            "--source_root",
            str(source),
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
    assert payload["final_decision"]["status"] == COMPLETE_STATUS
    assert "Fixed-Artifact Evidence Audit" in output_md.read_text(encoding="utf-8")
