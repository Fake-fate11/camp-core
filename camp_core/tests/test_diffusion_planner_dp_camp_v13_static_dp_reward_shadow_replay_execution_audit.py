from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.audit_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_execution import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CAMP_HEAD = "88d5bbedb0e443ec372c9518a9c5d92ba4ef8b21"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _record(
    *,
    selection_effect: bool = False,
    affine_delta: float = 0.0,
    masked_selection_score: bool = False,
) -> dict:
    weights = [1.0 / 14.0] * 14
    atoms = [[float(candidate + atom) / 100.0 for atom in range(14)] for candidate in range(8)]
    scores = [sum(a * w for a, w in zip(row, weights)) for row in atoms]
    scores[0] += affine_delta
    selection_scores = list(scores)
    feasible_mask = [True] * 8
    if masked_selection_score:
        feasible_mask[3] = False
        selection_scores[3] = float("inf")
    return {
        "default_off_shadow_selector": {
            "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "enabled": True,
            "default_off": True,
            "selection_effect": selection_effect,
            "online_selector_change": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "executed_index": 0,
            "executed_output_policy": "dp_top1",
            "shadow_selected_index": 2,
            "failed_closed_reason": None,
            "artifact_contract_ready": True,
        },
        "selected_index": 0,
        "executed_index": 0,
        "shadow_selected_index": 2,
        "num_candidates": 8,
        "atom_schema_version": "dp_camp_v10_14d",
        "selection_weights": weights,
        "selection_normalized_atoms": atoms,
        "scores": scores,
        "selection_scores": selection_scores,
        "feasible_mask": feasible_mask,
        "used_fallback": False,
        "candidate_reference_blend_steps": None,
        "perfect_tracker_command_postselection": None,
        "traffic_light_hybrid_postselection": None,
        "underprogress_relaxation": None,
        "splice_shadow_rule": None,
        "candidate_closed_loop_outcomes": None,
        "candidate_closed_loop_outcome_weights": None,
        "candidate_generation_contract": {
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "guidance": {
                "config_path": None,
                "config_sha256": None,
                "functions": [],
                "guidance_scale": None,
            },
            "changes_diffusion_planner_weights": False,
        },
    }


def _make_artifact(
    tmp_path: Path,
    *,
    selection_effect: bool = False,
    affine_delta: float = 0.0,
    masked_selection_score: bool = False,
) -> dict[str, Path]:
    execution_dir = tmp_path / "execution"
    base_output = tmp_path / "base"
    execution_dir.mkdir()
    _write(
        execution_dir / "HEADS.txt",
        "\n".join(
            [
                f"camp_head={CAMP_HEAD}",
                f"camp_origin_main={CAMP_HEAD}",
                f"dp_head={FIXED_DP_HEAD}",
            ]
        ),
    )
    _write(execution_dir / "runbook.exit", "0\n")
    _write(execution_dir / "runbook.stdout.log", "Python 3.12.3\n")
    _write(execution_dir / "runbook.stderr.log", "FutureWarning: harmless\n")
    _write(execution_dir / "SHA256SUMS.txt", "sha  file\n")
    preflight = _write(
        tmp_path / "preflight.json",
        json.dumps(
            {
                "final_decision": {
                    "passed": True,
                    "runtime_manifest_written": True,
                    "shadow_replay_evaluation_execution_authorized_next": True,
                }
            }
        ),
    )
    manifest = _write(
        tmp_path / "runtime_manifest.json",
        json.dumps(
            {
                "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
                "selection_effect": False,
                "executed_output_policy": "dp_top1",
                "default_off": True,
                "score_expression": "score_k(w)=a_k^T w",
                "current_dp_head": FIXED_DP_HEAD,
            }
        ),
    )
    for route in ("sample_normal", "nishi_release"):
        log = (
            base_output
            / route
            / "seed_301"
            / "npc_0"
            / "spawn_0p3"
            / "tl_on"
            / "static_shadow"
            / "camp_selection_log.json"
        )
        _write(
            log,
            json.dumps(
                [
                    _record(selection_effect=selection_effect, affine_delta=affine_delta)
                    if not masked_selection_score
                    else _record(masked_selection_score=True)
                    for _ in range(3)
                ]
            ),
        )
    return {
        "execution_dir": execution_dir,
        "base_output": base_output,
        "preflight": preflight,
        "manifest": manifest,
    }


def _report(tmp_path: Path, **overrides):
    paths = _make_artifact(
        tmp_path,
        selection_effect=overrides.pop("selection_effect", False),
        affine_delta=overrides.pop("affine_delta", 0.0),
        masked_selection_score=overrides.pop("masked_selection_score", False),
    )
    params = {
        "execution_dir": paths["execution_dir"],
        "base_output_dir": paths["base_output"],
        "preflight_json": paths["preflight"],
        "runtime_manifest_json": paths["manifest"],
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": FIXED_DP_HEAD,
        "expected_log_count": 2,
        "expected_steps_per_log": 3,
        "expected_records": 6,
        "enabled": True,
    }
    params.update(overrides)
    return build_report(**params)


def test_execution_audit_disabled_is_non_effectful(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = build_report(
        execution_dir=missing,
        base_output_dir=missing,
        preflight_json=missing,
        runtime_manifest_json=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["replay_execution_performed_by_this_audit"] is False


def test_execution_audit_accepts_default_off_shadow_logs(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["execution"]["selection_log_count"] == 2
    assert report["records"]["record_count"] == 6
    assert report["records"]["route_log_counts"] == {
        "nishi_release": 1,
        "sample_normal": 1,
    }
    assert report["records"]["shadow_differs_from_dp_top1_records"] == 6
    assert report["records"]["max_affine_score_error"] == 0.0
    assert decision["selector_promotion_authorized"] is False


def test_execution_audit_accepts_authorized_next_work_override(tmp_path: Path) -> None:
    next_work = "dp_camp_v13_shadow_replay_execution_result_review_only"
    report = _report(tmp_path, authorized_next_work=next_work)

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == next_work


def test_execution_audit_accepts_wrapper_log_file_names(tmp_path: Path) -> None:
    paths = _make_artifact(tmp_path)
    execution_dir = paths["execution_dir"]
    (execution_dir / "runbook.stdout.log").rename(execution_dir / "stdout.log")
    (execution_dir / "runbook.stderr.log").rename(execution_dir / "stderr.log")
    (execution_dir / "SHA256SUMS.txt").rename(execution_dir / "SHA256SUMS")

    report = build_report(
        execution_dir=execution_dir,
        base_output_dir=paths["base_output"],
        preflight_json=paths["preflight"],
        runtime_manifest_json=paths["manifest"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_log_count=2,
        expected_steps_per_log=3,
        expected_records=6,
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["source_hashes"]["execution_stdout"] is not None
    assert report["source_hashes"]["execution_stderr"] is not None
    assert report["source_hashes"]["execution_sha256sums"] is not None


def test_execution_audit_accepts_explicit_execution_camp_head(tmp_path: Path) -> None:
    current_head = "a" * 40
    paths = _make_artifact(tmp_path)

    report = build_report(
        execution_dir=paths["execution_dir"],
        base_output_dir=paths["base_output"],
        preflight_json=paths["preflight"],
        runtime_manifest_json=paths["manifest"],
        current_camp_head=current_head,
        current_camp_origin_main=current_head,
        execution_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_log_count=2,
        expected_steps_per_log=3,
        expected_records=6,
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["current_camp_head"] == current_head
    assert report["analysis"]["execution_camp_head"] == CAMP_HEAD


def test_execution_audit_rejects_selection_effect(tmp_path: Path) -> None:
    report = _report(tmp_path, selection_effect=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "default_off_contract_violations" in report["final_decision"]["failed_checks"]


def test_execution_audit_rejects_non_affine_scores(tmp_path: Path) -> None:
    report = _report(tmp_path, affine_delta=0.1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "affine_score_violations" in report["final_decision"]["failed_checks"]


def test_execution_audit_allows_infeasible_selection_score_inf_mask(tmp_path: Path) -> None:
    report = _report(tmp_path, masked_selection_score=True)

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["records"]["masked_selection_score_inf_count"] == 6
    assert report["records"]["violation_counts"]["selection_score_mask"] == 0


def test_execution_audit_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    paths = _make_artifact(tmp_path)
    output_json = tmp_path / "out" / "audit.json"
    output_md = tmp_path / "out" / "audit.md"

    exit_code = main(
        [
            "--execution_dir",
            str(paths["execution_dir"]),
            "--base_output_dir",
            str(paths["base_output"]),
            "--preflight_json",
            str(paths["preflight"]),
            "--runtime_manifest_json",
            str(paths["manifest"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--expected_log_count",
            "2",
            "--expected_steps_per_log",
            "3",
            "--expected_records",
            "6",
            "--authorized_next_work",
            "dp_camp_v13_shadow_replay_execution_result_review_only",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--enable_v13_static_dp_reward_shadow_replay_execution_audit",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert (
        payload["final_decision"]["authorized_next_work"]
        == "dp_camp_v13_shadow_replay_execution_result_review_only"
    )
    assert "Runbook exit: `0`" in output_md.read_text(encoding="utf-8")
