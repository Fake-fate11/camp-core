from __future__ import annotations

from pathlib import Path

from scripts.integrations.plan_diffusion_planner_offline_convex_selector_training import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    build_report,
    render_markdown,
)


def _preflight() -> dict:
    return {
        "final_decision": {
            "status": "selector_label_weight_preflight_ready",
            "passed": True,
            "authorized_next_work": "offline_convex_selector_training_plan_design_only",
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def test_offline_convex_selector_training_plan_ready() -> None:
    report = build_report(
        preflight=_preflight(),
        training_log_root="/logs/nonformal",
        output_training_dir="/tmp/training",
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_execution_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert report["training_plan"]["label_source"] == "safety_cost_v1_hard_guarded"
    assert report["training_plan"]["risk_type"] == "cvar"
    assert "--require_atom_schema" in report["training_plan"]["command_template"]
    assert report["input_manifest_gate"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK

    markdown = render_markdown(report)
    assert "Offline Convex Selector Training Plan" in markdown
    assert "safety_cost_v1_hard_guarded" in markdown
    assert "training execution authorized: `False`" in markdown
    assert "+  " not in markdown
    assert "classical Benders" in markdown


def test_offline_convex_selector_training_plan_blocks_bad_preflight() -> None:
    preflight = _preflight()
    preflight["final_decision"]["status"] = "selector_label_weight_preflight_blocked"

    report = build_report(
        preflight=preflight,
        training_log_root="/logs/nonformal",
        output_training_dir="/tmp/training",
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "preflight_status_ready" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_offline_convex_selector_training_plan_blocks_missing_training_support(
    tmp_path: Path,
) -> None:
    training_source = tmp_path / "train.py"
    training_source.write_text("print('no robust source')\n", encoding="utf-8")

    report = build_report(
        preflight=_preflight(),
        training_source=training_source,
        training_log_root="/logs/nonformal",
        output_training_dir="/tmp/training",
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    support = [
        check
        for check in report["source_checks"]
        if check["name"] == "training_source_supports_hard_guarded_cvar"
    ][0]
    assert support["passed"] is False
    assert "safety_cost_v1_hard_guarded" in support["missing_tokens"]


def test_offline_convex_selector_training_plan_requires_nonempty_paths() -> None:
    report = build_report(
        preflight=_preflight(),
        training_log_root="",
        output_training_dir="/tmp/training",
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert "training_log_root_declared" in failed
