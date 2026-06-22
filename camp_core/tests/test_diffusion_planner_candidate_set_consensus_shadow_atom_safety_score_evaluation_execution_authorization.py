from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.authorize_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation_execution import (
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


def _plan_payload(*, route_ids: tuple[str, ...] = RUN_IDS) -> dict[str, object]:
    return {
        "final_decision": {
            "status": "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan_ready",
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_evaluation_"
                "implementation_unit_tests_only"
            ),
            "safety_score_evaluation_plan_ready": True,
            "safety_score_evaluation_implementation_authorized": True,
            "safety_score_evaluation_execution_authorized": False,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
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
        "safety_score_evaluation_plan": {
            "expected_logs": 6,
            "expected_records": 60,
            "expected_candidates": 8,
            "fixed_dp_head": EXPECTED_DP_HEAD,
            "route_seed_matrix": [
                {
                    "run_id": run_id,
                    "seed": index + 1,
                    "scenario_buckets": (
                        ["normal"]
                        if "normal" in run_id
                        else ["traffic_light", "sharp_turn"]
                    ),
                }
                for index, run_id in enumerate(route_ids)
            ],
            "scenario_coverage": {
                "traffic_light": ["sample_tl59_seed1_npc0_tlon"],
                "turn": ["sample_tl59_seed1_npc0_tlon"],
                "normal": ["sample_normal2_seed1_npc0_tloff"],
            },
            "accept_criteria": [
                "artifact JSON/markdown/HEADS/SHA256SUMS are recorded before result review",
                "formal_seed_log_count remains zero and route seeds exclude 11/12/13",
                "safety or outcome fields never enter online selection",
            ],
            "reject_criteria": [
                "artifact SHA/HEADS recording is missing",
                "any formal seed log or route seed 11/12/13 is detected",
                "safety or outcome fields are used for online scoring",
            ],
        },
    }


def _weight_payload() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "candidate_set_consensus_shadow_atom_weight_sensitivity_ready",
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_weight_sensitivity_result_review_only"
            ),
            "weight_sensitivity_ready": True,
            "max_changed_records": 10,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
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


def _write_artifacts(tmp_path: Path) -> tuple[Path, Path, Path]:
    plan_root = tmp_path / "plan"
    weight_root = tmp_path / "weight"
    candidate_root = tmp_path / "logging_enabled"
    plan_root.mkdir()
    weight_root.mkdir()
    (plan_root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.json").write_text(
        json.dumps(_plan_payload()),
        encoding="utf-8",
    )
    (plan_root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.md").write_text(
        "# plan\n",
        encoding="utf-8",
    )
    (plan_root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        plan_root,
        (
            "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.json",
            "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.md",
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
        run_root = candidate_root / run_id
        run_root.mkdir(parents=True)
        rows = [{"num_candidates": 8, "selected_index": 0} for _ in range(10)]
        (run_root / "camp_selection_log.json").write_text(
            json.dumps(rows),
            encoding="utf-8",
        )
    return plan_root, weight_root, candidate_root


def test_safety_score_evaluation_execution_consideration_ready(tmp_path: Path) -> None:
    plan_root, weight_root, candidate_root = _write_artifacts(tmp_path)

    report = build_report(
        safety_plan_root=plan_root,
        weight_sensitivity_root=weight_root,
        candidate_root=candidate_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["safety_score_evaluation_read_only_execution_authorized"] is True
    assert decision["safety_score_evaluation_executed"] is False
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["candidate_log_summary"]["log_count"] == 6
    assert report["candidate_log_summary"]["records"] == 60


def test_safety_score_evaluation_execution_consideration_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    plan_root, weight_root, candidate_root = _write_artifacts(tmp_path)
    (plan_root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.md").write_text(
        "# mutated\n",
        encoding="utf-8",
    )

    report = build_report(
        safety_plan_root=plan_root,
        weight_sensitivity_root=weight_root,
        candidate_root=candidate_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "safety_plan_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_safety_score_evaluation_execution_consideration_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    plan_root, weight_root, candidate_root = _write_artifacts(tmp_path)

    report = build_report(
        safety_plan_root=plan_root,
        weight_sensitivity_root=weight_root,
        candidate_root=candidate_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_safety_score_evaluation_execution_consideration_rejects_formal_seed(
    tmp_path: Path,
) -> None:
    plan_root, weight_root, candidate_root = _write_artifacts(tmp_path)
    formal_root = candidate_root / "sample_tl59_seed11_npc0_tlon"
    formal_root.mkdir()
    (formal_root / "camp_selection_log.json").write_text(
        json.dumps([{"num_candidates": 8} for _ in range(10)]),
        encoding="utf-8",
    )

    report = build_report(
        safety_plan_root=plan_root,
        weight_sensitivity_root=weight_root,
        candidate_root=candidate_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "candidate_log_count" in failed
    assert "candidate_log_no_formal_seed" in failed


def test_safety_score_evaluation_execution_consideration_rejects_route_mismatch(
    tmp_path: Path,
) -> None:
    plan_root, weight_root, candidate_root = _write_artifacts(tmp_path)
    (plan_root / "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.json").write_text(
        json.dumps(_plan_payload(route_ids=RUN_IDS[:-1] + ("unexpected_seed4",))),
        encoding="utf-8",
    )
    _write_sha256sums(
        plan_root,
        (
            "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.json",
            "candidate_set_consensus_shadow_atom_safety_score_evaluation_plan.md",
            "HEADS.txt",
        ),
    )

    report = build_report(
        safety_plan_root=plan_root,
        weight_sensitivity_root=weight_root,
        candidate_root=candidate_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "candidate_log_run_ids_match_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_safety_score_evaluation_execution_consideration_markdown(tmp_path: Path) -> None:
    plan_root, weight_root, candidate_root = _write_artifacts(tmp_path)
    report = build_report(
        safety_plan_root=plan_root,
        weight_sensitivity_root=weight_root,
        candidate_root=candidate_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Safety-Score Execution Consideration" in markdown
    assert "Read-only execution authorized: `True`" in markdown
    assert "does not execute the evaluator" in markdown
    assert "classical Benders" in markdown


def test_safety_score_evaluation_execution_consideration_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_root, weight_root, candidate_root = _write_artifacts(tmp_path)
    output_json = tmp_path / "consideration.json"
    output_md = tmp_path / "consideration.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "candidate-set-consensus-shadow-atom-safety-score-evaluation-execution-consideration",
            "--safety_plan_root",
            str(plan_root),
            "--weight_sensitivity_root",
            str(weight_root),
            "--candidate_root",
            str(candidate_root),
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
    assert "Execution Consideration" in output_md.read_text(encoding="utf-8")
