from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.authorize_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality_replay import (
    AUTHORIZED_NEXT_WORK,
    GUARD_ENV_ASSIGNMENT,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
    build_report as build_plan_report,
    render_bash as render_plan_bash,
    render_markdown as render_plan_markdown,
)


CURRENT_CAMP_HEAD = "b2c8695facdc2318575b1e27afde3a9f3b36954b"
ARTIFACT_CAMP_HEAD = "e3b4a4fe67d3a6958df6fc2b395d24ae805576ab"


def _tiny_materiality() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "candidate_set_consensus_tiny_materiality_diagnosis_ready",
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_broader_nonformal_materiality_plan_only"
            ),
            "signal_present": True,
            "materiality_gate_passed": False,
            "sample_too_small_for_promotion": True,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "record_summary": {
            "records": 3,
            "available_records": 3,
            "valid_records": 3,
            "positive_spread_records": 3,
            "selected_not_consensus_best_records": 3,
            "finite_lambda_records": 3,
            "selected_rank_mean": 6.0,
            "selected_rank_max": 7.0,
            "min_lambda_to_change_any_record": 0.20212395639810232,
        },
    }


def _runtime(**overrides: object) -> dict[str, object]:
    runtime: dict[str, object] = {
        "current_camp_head": CURRENT_CAMP_HEAD,
        "current_origin_main": CURRENT_CAMP_HEAD,
        "current_dp_head": EXPECTED_DP_HEAD,
        "current_camp_branch": "main",
        "current_dp_branch": "tier4-main",
        "current_camp_status": (
            "## main...origin/main\n"
            "?? diffusion_planner_integration.md\n"
            "?? dp_camp_device_handoff.md\n"
        ),
        "current_dp_status": "## tier4-main...origin/tier4-main\n",
    }
    runtime.update(overrides)
    return runtime


def _write_artifact(
    root: Path,
    *,
    plan: dict[str, object] | None = None,
    runbook: str | None = None,
    heads: dict[str, str] | None = None,
) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    plan_payload = plan or build_plan_report(
        tiny_materiality=_tiny_materiality(),
        label="unit_artifact",
    )
    runbook_payload = runbook or render_plan_bash(plan_payload)
    heads_payload = heads or {
        "CAMP_HEAD": ARTIFACT_CAMP_HEAD,
        "CAMP_ORIGIN_MAIN": ARTIFACT_CAMP_HEAD,
        "DP_HEAD": EXPECTED_DP_HEAD,
    }
    (root / "candidate_set_consensus_broader_nonformal_materiality_plan.json").write_text(
        json.dumps(plan_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "candidate_set_consensus_broader_nonformal_materiality_plan.md").write_text(
        render_plan_markdown(plan_payload),
        encoding="utf-8",
    )
    (root / "run_candidate_set_consensus_broader_nonformal_materiality.sh").write_text(
        runbook_payload,
        encoding="utf-8",
    )
    (root / "HEADS.txt").write_text(
        "\n".join(f"{key}={value}" for key, value in heads_payload.items()) + "\n",
        encoding="utf-8",
    )
    files = [
        "candidate_set_consensus_broader_nonformal_materiality_plan.json",
        "candidate_set_consensus_broader_nonformal_materiality_plan.md",
        "run_candidate_set_consensus_broader_nonformal_materiality.sh",
        "HEADS.txt",
    ]
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in files),
        encoding="utf-8",
    )
    return plan_payload


def test_broader_materiality_replay_authorization_allows_guarded_replay_only(
    tmp_path: Path,
) -> None:
    _write_artifact(tmp_path)

    report = build_report(plan_root=tmp_path, runtime=_runtime(), label="unit")
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["broader_replay_authorized"] is True
    assert decision["new_replay_authorized"] is True
    assert decision["closed_loop_replay_authorized"] is True
    assert decision["guard_env_var"] == GUARD_ENV_ASSIGNMENT
    assert decision["formal_seeds_authorized"] is False
    assert decision["full36_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["classic_benders_claim_authorized"] is False
    assert report["plan_summary"]["run_count"] == 6
    assert report["plan_summary"]["paired_replay_count"] == 12
    assert report["plan_summary"]["planned_records"] == 60
    assert report["plan_summary"]["planned_candidate_rows"] == 480
    assert report["runtime_summary"]["camp_tracked_dirty_lines"] == []
    assert report["runtime_summary"]["camp_untracked_lines"]
    assert all(check["passed"] for check in report["checks"])


def test_broader_materiality_replay_authorization_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    _write_artifact(tmp_path)
    plan_path = tmp_path / "candidate_set_consensus_broader_nonformal_materiality_plan.json"
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["analysis"]["label"] = "tampered"
    plan_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = build_report(plan_root=tmp_path, runtime=_runtime())

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "artifact_sha_entries_match" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["broader_replay_authorized"] is False


def test_broader_materiality_replay_authorization_rejects_missing_runbook_guard(
    tmp_path: Path,
) -> None:
    plan = _write_artifact(tmp_path)
    runbook = render_plan_bash(plan).replace(
        "CANDIDATE_SET_CONSENSUS_BROADER_MATERIALITY_REPLAY_APPROVED",
        "UNGUARDED_REPLAY_APPROVED",
    )
    _write_artifact(tmp_path, plan=plan, runbook=runbook)

    report = build_report(plan_root=tmp_path, runtime=_runtime())

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runbook_guard_env_present" in report["final_decision"]["failed_checks"]


def test_broader_materiality_replay_authorization_rejects_formal_seed(
    tmp_path: Path,
) -> None:
    plan = _write_artifact(tmp_path)
    plan["route_seed_matrix"][0]["seed"] = 11
    command = plan["commands"]["paired_replays"][0]["command"]
    command[command.index("--seed") + 1] = "11"
    _write_artifact(tmp_path, plan=plan, runbook=render_plan_bash(plan))

    report = build_report(plan_root=tmp_path, runtime=_runtime())

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "scope_route_matrix_no_formal_seeds" in report["final_decision"]["failed_checks"]
    assert "scope_replay_commands_no_formal_seeds" in report["final_decision"]["failed_checks"]


def test_broader_materiality_replay_authorization_rejects_runtime_head_failures(
    tmp_path: Path,
) -> None:
    _write_artifact(tmp_path)

    report = build_report(
        plan_root=tmp_path,
        runtime=_runtime(
            current_origin_main="0" * 40,
            current_dp_head="1" * 40,
            current_camp_status="## main...origin/main\n M tracked.py\n",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runtime_camp_head_matches_origin_main" in report["final_decision"]["failed_checks"]
    assert "runtime_dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert "runtime_camp_no_tracked_dirty" in report["final_decision"]["failed_checks"]


def test_broader_materiality_replay_authorization_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact = tmp_path / "artifact"
    output_json = tmp_path / "authorization.json"
    output_md = tmp_path / "authorization.md"
    camp_status = tmp_path / "camp_status.txt"
    dp_status = tmp_path / "dp_status.txt"
    _write_artifact(artifact)
    camp_status.write_text(_runtime()["current_camp_status"], encoding="utf-8")
    dp_status.write_text(_runtime()["current_dp_status"], encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "authorize-candidate-set-consensus-broader-replay",
            "--plan_root",
            str(artifact),
            "--current_camp_head",
            CURRENT_CAMP_HEAD,
            "--current_origin_main",
            CURRENT_CAMP_HEAD,
            "--current_dp_head",
            EXPECTED_DP_HEAD,
            "--current_camp_branch",
            "main",
            "--current_dp_branch",
            "tier4-main",
            "--current_camp_status_path",
            str(camp_status),
            "--current_dp_status_path",
            str(dp_status),
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
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Replay Authorization" in output_md.read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()
