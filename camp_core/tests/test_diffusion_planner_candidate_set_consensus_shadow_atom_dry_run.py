from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_shadow_atom_dry_run import (
    AUTHORIZED_NEXT_WORK,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES,
    CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
    READY_STATUS,
    REJECT_STATUS,
    analyze,
    main,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_dry_run import (
    ATOM_NAME,
    COEFFICIENT_FIELD,
    PAYLOAD_KEY,
)


def _shadow_plan(
    *,
    expected_logs: int = 2,
    expected_records: int = 4,
    expected_candidates: int = 2,
    **decision_overrides: object,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": "candidate_set_consensus_shadow_atom_dry_run_plan_ready",
        "passed": True,
        "authorized_next_work": (
            "candidate_set_consensus_shadow_atom_dry_run_implementation_unit_tests_only"
        ),
        "shadow_atom_dry_run_plan_ready": True,
        "dry_run_implementation_authorized": True,
        "dry_run_execution_authorized": False,
        "atom_promotion_authorized": False,
        "safety_benefit_evidence": False,
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
    }
    decision.update(decision_overrides)
    return {
        "final_decision": decision,
        "dry_run_plan": {
            "plan_only": True,
            "expected_logs": expected_logs,
            "expected_records": expected_records,
            "expected_candidates": expected_candidates,
            "formal_seeds_forbidden": [11, 12, 13],
            "atom_name": ATOM_NAME,
            "payload_key": PAYLOAD_KEY,
            "coefficient_field": COEFFICIENT_FIELD,
            "shadow_append_policy": {
                "weight_append_value": 0.0,
                "selection_weight_append_value": 0.0,
                "score_delta_tolerance": 0.0,
                "write_runtime_logs": False,
            },
        },
    }


def _payload(*, coeff: list[float] | None = None, available: bool = True) -> dict:
    return {
        "schema_version": CANDIDATE_SET_CONSENSUS_PAYLOAD_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "deployed_atom_vector_change": False,
        "classical_benders_claim": False,
        "candidate_count": 2,
        "available": available,
        "availability_reason": None if available else "candidate_count_less_than_two",
        COEFFICIENT_FIELD: [0.5, 0.1] if coeff is None else coeff,
        "atom_candidate_names": list(CANDIDATE_SET_CONSENSUS_PAYLOAD_ATOM_CANDIDATE_NAMES),
    }


def _record(*, bad_score: bool = False, coeff: list[float] | None = None) -> dict:
    normalized_atoms = [[0.0, 1.0], [1.0, 0.0]]
    weights = [0.2, 0.8]
    scores = [0.8, 0.2]
    if bad_score:
        scores = [0.7, 0.2]
    return {
        "selected_index": 1,
        "candidate_closed_loop_outcomes": None,
        PAYLOAD_KEY: _payload(coeff=coeff),
        "atom_names": ["a", "b"],
        "atoms": normalized_atoms,
        "normalized_atoms": normalized_atoms,
        "selection_normalized_atoms": normalized_atoms,
        "weights": weights,
        "selection_weights": weights,
        "scores": scores,
        "selection_scores": scores,
        "feasible_mask": [True, True],
        "used_fallback": False,
        "camp_fallback_mode": "uniform",
        "infeasibility_reasons": [[], []],
    }


def _write_logs(
    root: Path,
    *,
    bad_score: bool = False,
    coeff: list[float] | None = None,
    formal_seed: bool = False,
    logs: int = 2,
    records_per_log: int = 2,
) -> None:
    for run_idx in range(logs):
        run_name = (
            f"sample_tl59_seed11_npc0_tlon_{run_idx}"
            if formal_seed and run_idx == 0
            else f"sample_tl59_seed20{run_idx}_npc0_tlon"
        )
        run = root / run_name
        run.mkdir(parents=True)
        rows = [
            _record(
                bad_score=bad_score and run_idx == 0 and record_idx == 0,
                coeff=coeff,
            )
            for record_idx in range(records_per_log)
        ]
        run.joinpath("camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )


def test_candidate_set_consensus_shadow_atom_dry_run_accepts_zero_weight_append(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        shadow_plan=_shadow_plan(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["dry_run_summary"]["available_records"] == 4
    assert report["dry_run_summary"]["shadow_appended_records"] == 4
    assert report["dry_run_summary"]["ranking_signal_records"] == 4
    assert report["dry_run_summary"]["max_shadow_zero_weight_score_abs_diff"] == 0.0
    assert (
        report["dry_run_summary"]["max_shadow_zero_weight_selection_score_abs_diff"]
        == 0.0
    )
    assert report["dry_run_records"][0]["shadow_atom_count"] == 3
    assert report["dry_run_records"][0]["shadow_weight_last"] == 0.0
    assert report["dry_run_records"][0]["deployed_selection_preserved"] is True
    assert report["dry_run_records"][0]["fallback_state_preserved"] is True
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]


def test_candidate_set_consensus_shadow_atom_dry_run_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root)

    report = analyze(
        shadow_plan=_shadow_plan(
            status="candidate_set_consensus_shadow_atom_dry_run_plan_rejected",
            passed=False,
            authorized_next_work=None,
            shadow_atom_dry_run_plan_ready=False,
            dry_run_implementation_authorized=False,
        ),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_authorizes_implementation_unit_tests" in failed


def test_candidate_set_consensus_shadow_atom_dry_run_rejects_bad_base_score(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, bad_score=True)

    report = analyze(
        shadow_plan=_shadow_plan(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_records_valid" in report["final_decision"]["failed_checks"]
    assert report["dry_run_summary"]["record_error_counts"]["base_affine_score_mismatch"] == 1


def test_candidate_set_consensus_shadow_atom_dry_run_rejects_negative_coefficient(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, coeff=[0.5, -0.1])

    report = analyze(
        shadow_plan=_shadow_plan(),
        candidate_root=root,
        expected_logs=2,
        expected_records=4,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_records_valid" in report["final_decision"]["failed_checks"]
    assert (
        report["dry_run_summary"]["record_error_counts"][
            "coefficient_nonfinite_or_negative"
        ]
        == 4
    )


def test_candidate_set_consensus_shadow_atom_dry_run_rejects_formal_seed_path(
    tmp_path: Path,
) -> None:
    root = tmp_path / "logging_enabled"
    _write_logs(root, formal_seed=True, logs=1, records_per_log=1)

    report = analyze(
        shadow_plan=_shadow_plan(expected_logs=1, expected_records=1),
        candidate_root=root,
        expected_logs=1,
        expected_records=1,
        expected_candidates=2,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "no_formal_seed_logs" in report["final_decision"]["failed_checks"]
    assert report["dry_run_summary"]["record_error_counts"]["formal_seed_detected"] == 1


def test_candidate_set_consensus_shadow_atom_dry_run_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "logging_enabled"
    source_json = tmp_path / "shadow_plan.json"
    output_json = tmp_path / "dry_run.json"
    output_md = tmp_path / "dry_run.md"
    _write_logs(root)
    source_json.write_text(json.dumps(_shadow_plan()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-shadow-atom-dry-run",
            "--shadow_plan_json",
            str(source_json),
            "--candidate_root",
            str(root),
            "--expected_logs",
            "2",
            "--expected_records",
            "4",
            "--expected_candidates",
            "2",
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_pass",
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Candidate-Set Consensus Shadow Atom Dry Run" in output_md.read_text(
        encoding="utf-8"
    )


def test_candidate_set_consensus_shadow_atom_dry_run_script_file_cli(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = (
        repo_root
        / "scripts"
        / "integrations"
        / "analyze_diffusion_planner_candidate_set_consensus_shadow_atom_dry_run.py"
    )
    root = tmp_path / "logging_enabled"
    source_json = tmp_path / "shadow_plan.json"
    output_json = tmp_path / "dry_run.json"
    output_md = tmp_path / "dry_run.md"
    _write_logs(root)
    source_json.write_text(json.dumps(_shadow_plan()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--shadow_plan_json",
            str(source_json),
            "--candidate_root",
            str(root),
            "--expected_logs",
            "2",
            "--expected_records",
            "4",
            "--expected_candidates",
            "2",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--require_pass",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "candidate_set_consensus_shadow_atom_dry_run_ready" in result.stdout
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"][
        "status"
    ] == READY_STATUS
