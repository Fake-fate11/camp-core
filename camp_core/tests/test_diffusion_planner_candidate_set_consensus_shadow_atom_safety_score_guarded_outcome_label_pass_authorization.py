from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.authorize_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass import (
    GUARD_ENV_ASSIGNMENT,
    build_report as build_plan_report,
    render_bash as render_plan_bash,
    render_markdown as render_plan_markdown,
)


CURRENT_CAMP_HEAD = "6f27df1ccfb9be5e47bba681872b4be6d24ca0d3"
ARTIFACT_CAMP_HEAD = "68241b67b450e121802bdff730a763445a598d77"


def _source_search() -> dict[str, object]:
    run_ids = (
        "sample_tl59_seed1_npc0_tlon",
        "sample_tl59_seed2_npc4_tlon",
        "sample_tl59_seed3_npc4_tloff",
        "sample_normal2_seed1_npc0_tloff",
        "nishi_release_seed2_npc4_tlon",
        "nishi_lanechange_seed4_npc4_tloff",
    )
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "outcome_label_existing_source_search_no_compatible_source"
            ),
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "guarded_outcome_label_pass_consideration_plan_only"
            ),
            "compatible_source_found": False,
            "guarded_outcome_label_pass_consideration_plan_authorized": True,
            "outcome_label_generation_authorized": False,
            "label_attachment_authorized": False,
            "safety_score_evaluation_retry_authorized": False,
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
        "source_summary": {
            "route_seed_matrix": [
                {"run_id": run_id, "seed": seed}
                for run_id, seed in zip(run_ids, (1, 2, 3, 1, 2, 4))
            ],
        },
        "expected_scope": {
            "expected_logs": 6,
            "expected_records": 60,
            "expected_candidates": 8,
            "run_ids": sorted(run_ids),
        },
        "search_summary": {
            "complete_outcome_log_count": 0,
            "formal_seed_log_count": 0,
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
        source_search=_source_search(),
        label="unit_plan",
    )
    _localize_asset_paths(root, plan_payload)
    runbook_payload = runbook or render_plan_bash(plan_payload)
    heads_payload = heads or {
        "camp_head": ARTIFACT_CAMP_HEAD,
        "camp_origin_main": ARTIFACT_CAMP_HEAD,
        "camp_branch": "main",
        "dp_head": EXPECTED_DP_HEAD,
        "dp_branch": "tier4-main",
        "source_search_json": "/artifact/source_search.json",
        "guard_env_assignment": GUARD_ENV_ASSIGNMENT,
        "label_output_root": (
            "/root/autodl-tmp/"
            "camp_dp_candidate_set_consensus_shadow_atom_safety_score_outcome_labels"
        ),
    }
    files = {
        "candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass_consideration_plan.json": (
            json.dumps(plan_payload, indent=2, sort_keys=True) + "\n"
        ),
        "candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass_consideration_plan.md": render_plan_markdown(
            plan_payload
        ),
        "candidate_set_consensus_shadow_atom_safety_score_guarded_outcome_label_pass_runbook.sh": runbook_payload,
        "HEADS.txt": "\n".join(f"{key}={value}" for key, value in heads_payload.items())
        + "\n",
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in files),
        encoding="utf-8",
    )
    return plan_payload


def _localize_asset_paths(root: Path, plan: dict[str, object]) -> None:
    asset_root = root / "assets"
    asset_root.mkdir(parents=True, exist_ok=True)
    route_rows = plan["guarded_outcome_label_pass_plan"]["route_seed_matrix"]
    for row in route_rows:
        for field in ("map_path", "route"):
            local = asset_root / f"{row['run_id']}_{field}.asset"
            local.write_text("asset\n", encoding="utf-8")
            row[field] = str(local)
    command_options = (
        "--map_path",
        "--route",
        "--model_path",
        "--model_args",
        "--config",
        "--reward_config",
        "--camp_atom_scales",
        "--camp_static_weights",
    )
    for item in plan["commands"]["label_passes"]:
        command = item["command"]
        for option in command_options:
            if option not in command:
                continue
            local = asset_root / f"{item['run_id']}_{option.lstrip('-')}.asset"
            local.write_text("asset\n", encoding="utf-8")
            command[command.index(option) + 1] = str(local)


def _assets_exist(path: str) -> bool:
    return bool(path)


def test_guarded_outcome_label_pass_authorization_allows_execution_only(
    tmp_path: Path,
) -> None:
    _write_artifact(tmp_path)

    report = build_report(
        plan_root=tmp_path,
        runtime=_runtime(),
        label="unit",
        asset_exists=_assets_exist,
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["outcome_label_pass_execution_authorized"] is True
    assert decision["outcome_label_pass_executed"] is False
    assert decision["label_attachment_authorized"] is False
    assert decision["safety_score_evaluation_retry_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["plan_summary"]["run_count"] == 6
    assert report["asset_summary"]["missing_assets"] == []
    assert report["runtime_summary"]["camp_untracked_lines"]
    assert all(check["passed"] for check in report["authorization_checks"])


def test_guarded_outcome_label_pass_authorization_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    _write_artifact(tmp_path)
    path = tmp_path / (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "guarded_outcome_label_pass_consideration_plan.md"
    )
    path.write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        plan_root=tmp_path,
        runtime=_runtime(),
        asset_exists=_assets_exist,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "artifact_sha_entries_match" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["outcome_label_pass_execution_authorized"] is False


def test_guarded_outcome_label_pass_authorization_rejects_missing_runbook_guard(
    tmp_path: Path,
) -> None:
    plan = _write_artifact(tmp_path)
    runbook = render_plan_bash(plan).replace(
        "CANDIDATE_SET_CONSENSUS_OUTCOME_LABEL_PASS_APPROVED",
        "UNGUARDED_OUTCOME_LABEL_PASS_APPROVED",
    )
    _write_artifact(tmp_path, plan=plan, runbook=runbook)

    report = build_report(
        plan_root=tmp_path,
        runtime=_runtime(),
        asset_exists=_assets_exist,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runbook_guard_env_present" in report["final_decision"]["failed_checks"]


def test_guarded_outcome_label_pass_authorization_rejects_formal_seed(
    tmp_path: Path,
) -> None:
    plan = _write_artifact(tmp_path)
    plan["guarded_outcome_label_pass_plan"]["route_seed_matrix"][0]["seed"] = 11
    command = plan["commands"]["label_passes"][0]["command"]
    command[command.index("--seed") + 1] = "11"
    _write_artifact(tmp_path, plan=plan, runbook=render_plan_bash(plan))

    report = build_report(
        plan_root=tmp_path,
        runtime=_runtime(),
        asset_exists=_assets_exist,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "scope_route_matrix_no_formal_seeds" in report["final_decision"]["failed_checks"]
    assert "scope_commands_no_formal_seeds" in report["final_decision"]["failed_checks"]


def test_guarded_outcome_label_pass_authorization_rejects_runtime_failures(
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
        asset_exists=_assets_exist,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runtime_camp_head_matches_origin_main" in report["final_decision"]["failed_checks"]
    assert "runtime_dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert "runtime_camp_no_tracked_dirty" in report["final_decision"]["failed_checks"]


def test_guarded_outcome_label_pass_authorization_rejects_missing_assets(
    tmp_path: Path,
) -> None:
    _write_artifact(tmp_path)

    report = build_report(
        plan_root=tmp_path,
        runtime=_runtime(),
        asset_exists=lambda _path: False,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "assets_all_exist" in report["final_decision"]["failed_checks"]


def test_guarded_outcome_label_pass_authorization_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
            "authorize-guarded-outcome-label-pass",
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
    assert "Outcome-Label Pass Authorization" in output_md.read_text(
        encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
