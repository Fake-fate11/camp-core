from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations."
    "plan_diffusion_planner_guarded_material_v4_fixed_snapshot_screen_rerun"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _post_review_payload(
    *,
    status: str = target.POST_REVIEW_READY_STATUS,
    passed: bool = True,
    authorized_next_work: str = target.POST_REVIEW_AUTHORIZED_NEXT_WORK,
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
    for key in target.BLOCKED_ACTIONS:
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
    (root / target.POST_REVIEW_JSON).write_text(
        json.dumps(payload or _post_review_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / target.POST_REVIEW_MD).write_text(
        markdown_text
        if markdown_text is not None
        else (
            "# Post Review\n\n"
            f"- Authorized next work: `{target.POST_REVIEW_AUTHORIZED_NEXT_WORK}`\n"
            "- Next gate: fixed-snapshot screen rerun plan only\n"
        ),
        encoding="utf-8",
    )
    return root


def _build(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    markdown_text: str | None = None,
    dp_head: str = target.EXPECTED_DP_HEAD,
) -> dict:
    root = _write_post_review_root(
        tmp_path,
        payload=payload,
        markdown_text=markdown_text,
    )
    return target.build_report(
        post_review_root=root,
        execution_root=Path(target.DEFAULT_EXECUTION_ROOT) / "unit_v4_rerun",
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_guarded_material_v4_fixed_snapshot_screen_rerun_plan_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["fixed_snapshot_screen_rerun_plan"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_plan_complete"] is True
    assert decision["guarded_fixed_snapshot_screen_rerun_next_gate_authorized"] is True
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["selected_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert plan["guard_env_assignment"] == target.GUARD_ENV_ASSIGNMENT
    assert plan["snapshot_scope"]["seed"] == 2
    assert plan["snapshot_scope"]["formal_seed"] is False
    assert plan["snapshot_scope"]["formal_seeds_frozen"] == [11, 12, 13]
    assert plan["candidate_config"]["generator_policy"] == target.PLANNED_POLICY
    assert plan["candidate_config"]["default_off_remediation_profile"] == (
        target.REMEDIATION_PROFILE
    )
    assert plan["candidate_config"]["prefix_steps"] == [1]
    assert plan["candidate_config"]["bridge_steps"] == [0]


def test_guarded_material_v4_fixed_snapshot_screen_rerun_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_guarded_material_v4_fixed_snapshot_screen_rerun_plan_rejects_missing_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_post_review_payload(authorized_next_work="not_this_gate"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "post_review_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v4_fixed_snapshot_screen_rerun_plan_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_post_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "post_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v4_fixed_snapshot_screen_rerun_runbook_is_guarded(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    runbook = report["runbook"]["text"]

    assert target.GUARD_ENV_VAR in runbook
    assert '!= "yes"' in runbook
    assert "analyze_diffusion_planner_route_topology_candidate_screen.py" in runbook
    assert f"--generator_policy {target.PLANNED_POLICY}" in runbook
    assert (
        f"--default_off_remediation_profile {target.REMEDIATION_PROFILE}"
        in runbook
    )
    assert "--prefix_step 1" in runbook
    assert "--bridge_step 0" in runbook
    assert "--lane_projected_offset_scale 0.0" in runbook
    assert "--command_jerk_worse_budget_mps3 0.0" in runbook
    assert "--rollout_jerk_worse_budget_mps3 0.0" in runbook
    assert "--rollout_lateral_worse_budget_mps2 0.0" in runbook
    assert (
        f"--max_remediation_candidates {target.DEFAULT_MAX_REMEDIATION_CANDIDATES}"
        in runbook
    )
    assert target.DEFAULT_REMOTE_PYTHON == "/root/miniconda3/bin/python"
    assert target.DEFAULT_REMOTE_PYTHON in runbook
    assert target.EXPECTED_DP_HEAD in runbook
    assert "SNAPSHOT_COUNT" in runbook
    assert "replay" not in runbook.lower()
    assert "git pull" not in runbook.lower()
    assert "git checkout" not in runbook.lower()


def test_guarded_material_v4_fixed_snapshot_screen_rerun_markdown_records_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = target.render_markdown(report)

    assert "Guarded Material V4 Fixed-Snapshot Screen Rerun Plan" in markdown
    assert target.GUARD_ENV_ASSIGNMENT in markdown
    assert target.PLANNED_POLICY in markdown
    assert target.REMEDIATION_PROFILE in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_guarded_material_v4_fixed_snapshot_screen_rerun_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = _write_post_review_root(tmp_path)
    output_json = tmp_path / "out" / "fixed_snapshot_screen_rerun_plan.json"
    output_md = tmp_path / "out" / "fixed_snapshot_screen_rerun_plan.md"
    output_bash = tmp_path / "out" / "guarded_material_v4_runbook.sh"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--post_review_root",
            str(root),
            "--execution_root",
            str(Path(target.DEFAULT_EXECUTION_ROOT) / "unit_v4_rerun"),
            "--camp_head",
            CAMP_COMMIT,
            "--camp_origin_main",
            CAMP_COMMIT,
            "--dp_head",
            target.EXPECTED_DP_HEAD,
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

    target.main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    runbook = output_bash.read_text(encoding="utf-8")
    assert payload["final_decision"]["status"] == target.READY_STATUS
    assert "Guarded Material V4 Fixed-Snapshot Screen Rerun Plan" in markdown
    assert target.GUARD_ENV_VAR in runbook
