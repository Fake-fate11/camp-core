from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_targeted_failure_attribution import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    main,
    render_markdown,
)


def _bucket(
    bucket: str,
    *,
    oracle_ci: float = -0.4,
    camp_ci: float = 0.08,
    gap_ci: float = 0.9,
) -> dict[str, object]:
    return {
        "bucket": bucket,
        "records": 100,
        "logs": 5,
        "record_rates": {"hard_guarded_oracle_beats_top1": 0.5},
        "run_level_delta_ci": {
            "hard_guarded_oracle_minus_top1": {
                "mean": -1.0,
                "ci95_high": oracle_ci,
            },
            "camp_minus_top1": {"mean": -0.2, "ci95_high": camp_ci},
            "camp_minus_hard_guarded_oracle": {
                "mean": 0.6,
                "ci95_high": gap_ci,
            },
        },
    }


def _oracle(*, traffic_oracle_ci: float = -0.4) -> dict[str, object]:
    return {
        "logs": {"total": 108, "formal_seed_logs": 0},
        "records": {"total": 21600},
        "coverage_gaps": {"missing_required_buckets": []},
        "opportunity_gate": {"passed": True},
        "by_bucket": [
            _bucket("overall", oracle_ci=-1.0, camp_ci=-0.4, gap_ci=1.2),
            _bucket("traffic_light", oracle_ci=traffic_oracle_ci),
            _bucket("red_light_turn", oracle_ci=-0.41),
        ],
    }


def _selector_gap() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "current_selector_gap_open",
            "passed": False,
            "authorized_next_work": "selector_label_weight_design_preflight",
            "oracle_passed": True,
            "evaluated_passed_proof_protocol_v2": False,
            "evaluated_gap_closed": False,
            "evaluated_same_as_logged": True,
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "evaluated_selector": {
            "top1_bucket_failures": {
                "traffic_light": 0.08,
                "red_light_turn": 0.09,
            },
            "gap_bucket_failures": {
                "traffic_light": 0.9,
                "red_light_turn": 0.91,
            },
            "by_bucket": {
                "traffic_light": {
                    "overall": {
                        "camp_minus_top1_ci_high": 0.08,
                        "camp_minus_hard_guarded_oracle_ci_high": 0.9,
                    }
                },
                "red_light_turn": {
                    "overall": {
                        "camp_minus_top1_ci_high": 0.09,
                        "camp_minus_hard_guarded_oracle_ci_high": 0.91,
                    }
                },
            },
        },
    }


def _training_diag() -> dict[str, object]:
    def row(bucket: str) -> dict[str, object]:
        return {
            "bucket": bucket,
            "changed_record_rate": 0.2,
            "evaluated_minus_logged_cost_mean": 0.08,
            "evaluated_minus_logged_cost_ci_high": 0.25,
            "regression_components": [
                {"name": "collision", "value": 0.08},
                {"name": "near_miss", "value": 0.002},
            ],
            "atom_pressure": [{"name": "jerk_full", "value": -20.0}],
            "failure_modes": {
                "camp_not_hard_guarded_oracle_when_available": 0.35
            },
            "candidate_pool_coverage": {
                "hard_guarded_oracle_available_rate": 0.99
            },
        }

    return {
        "final_decision": {
            "status": "offline_convex_selector_training_failure_diagnosed",
            "passed": True,
            "dry_run_selector_rejected": True,
            "authorized_next_work": "offline_convex_objective_and_label_sensitivity_plan_only",
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "failure_hypotheses": [
            {"name": "weight_mass_concentrated_on_red_stop_atoms"},
            {"name": "critical_bucket_top1_gate_failure"},
            {"name": "hard_guarded_oracle_gap_remains_open"},
        ],
        "bucket_diagnosis": [row("traffic_light"), row("red_light_turn")],
    }


def _sensitivity_diag() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "offline_convex_objective_label_sensitivity_results_diagnosed",
            "passed": True,
            "sensitivity_route_rejected": True,
            "credible_direction_candidates": [],
            "authorized_next_work": "predeclare_no_leak_atom_or_proof_objective_redesign_plan_only",
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "route_diagnosis": {
            "persistent_failed_checks": [
                "component_nonpositive_collision",
                "top1_bucket_gate_passed",
            ]
        },
        "comparison_summary": {"credible_direction_candidates": []},
    }


def _bridge() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "current_observable_separability_bridge_duplicate_rejected",
            "passed": True,
            "authorized_next_work": "proof_objective_or_new_descriptor_family_design_only",
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "equivalence": {
            "duplicate_route_evidence": True,
            "materially_new_route": False,
            "uncovered_current_material_fields": [],
        },
    }


def _inventory() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "current_tick_no_leak_atom_support_inventory_no_unclosed_fields",
            "passed": False,
            "authorized_next_work": "proof_objective_v2_or_default_off_logging_preflight_design_only",
            "admissible_unclosed_candidate_families": [],
            "available_existing_or_closed_proxy_families": ["existing_traffic_proxy"],
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _report(**overrides: dict[str, object]) -> dict[str, object]:
    inputs = {
        "targeted_oracle": _oracle(),
        "selector_gap": _selector_gap(),
        "training_failure_diagnosis": _training_diag(),
        "sensitivity_diagnosis": _sensitivity_diag(),
        "observable_bridge": _bridge(),
        "support_inventory": _inventory(),
    }
    inputs.update(overrides)
    return build_report(**inputs, label="unit")


def test_targeted_failure_attribution_rejects_current_route() -> None:
    report = _report()
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["current_camp_dp_selector_route_rejected"] is True
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert report["failure_summary"]["candidate_pool_opportunity_confirmed"] is True
    assert report["failure_summary"]["current_camp_targeted_failure_confirmed"] is True
    assert report["failure_summary"]["new_no_leak_support_missing_in_current_artifacts"] is True

    traffic = {
        row["bucket"]: row for row in report["target_bucket_attribution"]
    }["traffic_light"]
    assert "candidate_pool_has_hard_guarded_safetycost_opportunity" in traffic[
        "attribution"
    ]
    assert "current_selector_fails_bucket_top1_gate" in traffic["attribution"]
    assert "rejected_training_route_increased_hard_safety_components" in traffic[
        "attribution"
    ]


def test_targeted_failure_attribution_blocks_missing_oracle_opportunity() -> None:
    report = _report(targeted_oracle=_oracle(traffic_oracle_ci=0.1))

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "traffic_light_hard_guarded_oracle_opportunity" in failed


def test_targeted_failure_attribution_markdown_states_boundary() -> None:
    report = _report()
    markdown = render_markdown(report)

    assert "Targeted DP-CAMP Failure Attribution" in markdown
    assert "traffic_light" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "not a DP-side classical Benders" in markdown


def test_targeted_failure_attribution_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    paths = {
        "targeted_oracle_json": tmp_path / "oracle.json",
        "selector_gap_json": tmp_path / "gap.json",
        "training_failure_diagnosis_json": tmp_path / "training_diag.json",
        "sensitivity_diagnosis_json": tmp_path / "sensitivity_diag.json",
        "observable_bridge_json": tmp_path / "bridge.json",
        "support_inventory_json": tmp_path / "inventory.json",
    }
    payloads = [
        _oracle(),
        _selector_gap(),
        _training_diag(),
        _sensitivity_diag(),
        _bridge(),
        _inventory(),
    ]
    for path, payload in zip(paths.values(), payloads, strict=True):
        path.write_text(json.dumps(payload), encoding="utf-8")
    output_json = tmp_path / "out.json"
    output_md = tmp_path / "out.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "targeted_failure_attribution",
            "--targeted_oracle_json",
            str(paths["targeted_oracle_json"]),
            "--selector_gap_json",
            str(paths["selector_gap_json"]),
            "--training_failure_diagnosis_json",
            str(paths["training_failure_diagnosis_json"]),
            "--sensitivity_diagnosis_json",
            str(paths["sensitivity_diagnosis_json"]),
            "--observable_bridge_json",
            str(paths["observable_bridge_json"]),
            "--support_inventory_json",
            str(paths["support_inventory_json"]),
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
    assert "Targeted DP-CAMP Failure" in output_md.read_text(encoding="utf-8")
