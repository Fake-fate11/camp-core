from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_fixed_snapshot_screen_rerun import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    DEFAULT_DEVELOPMENT_ROOT,
    DEFAULT_EXPECTED_SNAPSHOT_COUNT,
    EXPECTED_DP_HEAD,
    GUARD_ENV_ASSIGNMENT,
    GUARD_ENV_VAR,
    PLANNED_POLICY,
    POST_REVIEW_AUTHORIZED_NEXT_WORK,
    POST_REVIEW_JSON,
    POST_REVIEW_MD,
    POST_REVIEW_READY_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _post_review_payload(
    *,
    status: str = POST_REVIEW_READY_STATUS,
    passed: bool = True,
    authorized_next_work: str = POST_REVIEW_AUTHORIZED_NEXT_WORK,
    plan_authorized: bool = True,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "fixed_snapshot_screen_rerun_plan_authorized": plan_authorized,
    }
    for key in BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["fixed_snapshot_screen_rerun_authorized"] = True
    return {"final_decision": decision}


def _write_post_review_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    markdown_text: str | None = None,
) -> Path:
    root = tmp_path / "post_review"
    root.mkdir()
    (root / POST_REVIEW_JSON).write_text(
        json.dumps(payload or _post_review_payload(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (root / POST_REVIEW_MD).write_text(
        markdown_text
        if markdown_text is not None
        else "# Post Review\n\n## Next Gate\n\nfixed-snapshot screen rerun plan only\n",
        encoding="utf-8",
    )
    return root


def _build(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    markdown_text: str | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    root = _write_post_review_root(
        tmp_path,
        payload=payload,
        markdown_text=markdown_text,
    )
    return build_report(
        post_review_root=root,
        execution_root=Path(DEFAULT_DEVELOPMENT_ROOT) / "unit_execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=dp_head,
        label="unit",
    )


def test_fixed_snapshot_screen_rerun_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["fixed_snapshot_screen_rerun_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_next_gate_authorized"] is True
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["selected_next_work"] == AUTHORIZED_NEXT_WORK
    assert plan["guard_env_assignment"] == GUARD_ENV_ASSIGNMENT
    assert plan["snapshot_scope"]["seed"] == 2
    assert plan["snapshot_scope"]["formal_seed"] is False
    assert plan["snapshot_scope"]["expected_snapshot_count"] == DEFAULT_EXPECTED_SNAPSHOT_COUNT
    assert plan["candidate_config"]["generator_policy"] == PLANNED_POLICY
    assert plan["execution_artifacts"]["output_root"].endswith("unit_execution")


def test_fixed_snapshot_screen_rerun_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_fixed_snapshot_screen_rerun_plan_rejects_missing_post_review_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_post_review_payload(authorized_next_work="not_this_gate"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "post_review_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_fixed_snapshot_screen_rerun_plan_rejects_blocked_action_leak(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_post_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "post_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_fixed_snapshot_screen_rerun_plan_rejects_missing_next_gate_markdown(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, markdown_text="# Post Review\n")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "post_review_markdown_records_next_gate" in report["final_decision"][
        "failed_checks"
    ]


def test_fixed_snapshot_screen_rerun_runbook_is_guarded_and_scoped(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    runbook = report["runbook"]["text"]

    assert GUARD_ENV_VAR in runbook
    assert '!= "yes"' in runbook
    assert "analyze_diffusion_planner_route_topology_candidate_screen.py" in runbook
    assert f"--generator_policy {PLANNED_POLICY}" in runbook
    assert "--red_stop_margin_m 2.0" in runbook
    assert "--backup_stop_offset_m 1.0" in runbook
    assert "--prefix_step 5" in runbook
    assert "--bridge_step 5" in runbook
    assert "--lane_projected_offset_scale 0.0" in runbook
    assert "--jerk_progress_max_jerk_mps3 8.0" in runbook
    assert "--min_snapshot_support_rate 0.25" in runbook
    assert "--default_off_remediation_profile" not in runbook
    assert "replay" not in runbook.lower()
    assert "git pull" not in runbook.lower()
    assert "git checkout" not in runbook.lower()


def test_fixed_snapshot_screen_rerun_markdown_records_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Fixed-Snapshot Screen Rerun Plan" in markdown
    assert GUARD_ENV_ASSIGNMENT in markdown
    assert PLANNED_POLICY in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_fixed_snapshot_screen_rerun_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = _write_post_review_root(tmp_path)
    output_json = tmp_path / "out" / "fixed_snapshot_screen_rerun_plan.json"
    output_md = tmp_path / "out" / "fixed_snapshot_screen_rerun_plan.md"
    output_bash = tmp_path / "out" / "fixed_snapshot_screen_rerun_guarded_runbook.sh"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--post_review_root",
            str(root),
            "--execution_root",
            str(Path(DEFAULT_DEVELOPMENT_ROOT) / "unit_execution"),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--label",
            "unit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_bash",
            str(output_bash),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    runbook = output_bash.read_text(encoding="utf-8")
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Fixed-Snapshot Screen Rerun Plan" in markdown
    assert GUARD_ENV_VAR in runbook
