from __future__ import annotations

import hashlib
import json
from pathlib import Path

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_eval_plus_prior_training_preflight import (
    ATOM_SCHEMA_VERSION,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "6dd68caaf494cf66fb0ebf2cbf6fb7529227d882"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(hash_label: str, *, guidance_enabled: bool = False) -> dict:
    schema_version, atom_names = atom_schema_for_dimension(14)
    assert schema_version == ATOM_SCHEMA_VERSION
    return {
        "num_candidates": 8,
        "atoms": [[float(candidate + atom + 1) / 100.0 for atom in range(14)] for candidate in range(8)],
        "atom_names": list(atom_names),
        "atom_schema_version": schema_version,
        "feasible_mask": [True] * 8,
        "selected_index": 0,
        "executed_index": 0,
        "shadow_selected_index": 2,
        "candidate_reference_blend_steps": None,
        "perfect_tracker_command_postselection": None,
        "traffic_light_hybrid_postselection": None,
        "underprogress_relaxation": None,
        "splice_shadow_rule": None,
        "candidate_closed_loop_outcomes": None,
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": 8,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": guidance_enabled,
            "changes_diffusion_planner_weights": False,
        },
        "default_off_shadow_selector": {
            "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "enabled": True,
            "default_off": True,
            "selection_effect": False,
            "online_selector_change": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": "score_k(w)=a_k^T w",
            "executed_index": 0,
            "shadow_selected_index": 2,
            "failed_closed_reason": None,
            "artifact_contract_ready": True,
            "candidate_tensor_hash": {
                "sha256": _sha(hash_label),
                "shape": [8, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
        "dp_candidate_rewards": [
            {"total": float(index), "progress": float(index) / 10.0}
            for index in range(8)
        ],
    }


def _write_logs(
    root: Path,
    *,
    prefix: str,
    seed: int = 301,
    overlap_with: str | None = None,
) -> None:
    rows_a = [
        _record(f"{overlap_with or prefix}-a-{index}")
        for index in range(3)
    ]
    rows_b = [
        _record(f"{overlap_with or prefix}-b-{index}")
        for index in range(3)
    ]
    _write(
        root
        / "sample_normal"
        / f"seed_{seed}"
        / "npc_0"
        / "spawn_0p3"
        / "tl_on"
        / "static_shadow"
        / "camp_selection_log.json",
        json.dumps(rows_a),
    )
    _write(
        root
        / "sample_tl"
        / f"seed_{seed + 1}"
        / "npc_0"
        / "spawn_0p3"
        / "tl_off"
        / "static_shadow"
        / "camp_selection_log.json",
        json.dumps(rows_b),
    )


def _trainer(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "def _run_dp_native_training_data_contract_preflight(): pass",
                "def validate_atom_schema(): pass",
                "weights = exp_logits / np.sum(exp_logits)",
                "weights /= np.sum(weights)",
                "",
            ]
        ),
    )


def _audit(path: Path, *, wrong_scope: bool = False) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"next_work_target={'wrong_scope' if wrong_scope else AUTHORIZED_CURRENT_WORK}",
                "training_preflight_authorized=True",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def _report(
    tmp_path: Path,
    *,
    wrong_scope: bool = False,
    formal_seed: bool = False,
    planned_exists: bool = False,
    overlap: bool = False,
) -> dict:
    prior = tmp_path / "prior"
    evaluation = tmp_path / "evaluation"
    _write_logs(prior, prefix="prior", seed=11 if formal_seed else 301)
    _write_logs(
        evaluation,
        prefix="eval",
        seed=401,
        overlap_with="prior" if overlap else None,
    )
    trainer = _trainer(tmp_path / "train_diffusion_planner_static_camp.py")
    audit = _audit(tmp_path / "audit.md", wrong_scope=wrong_scope)
    planned = tmp_path / "planned_training"
    if planned_exists:
        planned.mkdir()
    return build_report(
        prior_output_dir=prior,
        evaluation_output_dir=evaluation,
        trainer_py=trainer,
        v13_audit_md=audit,
        planned_training_output_dir=planned,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_prior_selection_log_count=2,
        expected_evaluation_selection_log_count=2,
        expected_prior_records=6,
        expected_evaluation_records=6,
        python_executable="python",
        enabled=True,
    )


def test_preflight_disabled_has_no_next_work(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = build_report(
        prior_output_dir=missing,
        evaluation_output_dir=missing,
        trainer_py=missing,
        v13_audit_md=missing,
        planned_training_output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_preflight_accepts_fixed_prior_plus_eval_logs(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is False
    assert report["clean_contract"]["passed"] is True
    assert report["training_input_summary"]["combined"]["records_total"] == 12
    assert report["training_input_summary"]["combined"]["usable_feasible_records"] == 12
    assert report["candidate_tensor_overlap"]["prior_hashes_in_evaluation_count"] == 0
    assert report["training_command_plan"]["require_dp_native_training_data_contract"] is True
    assert report["training_command_plan"]["require_atom_schema"] is True
    assert "--label_source dp_reward" in report["training_command_plan"]["command"]


def test_preflight_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, wrong_scope=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work_target" in report["final_decision"]["failed_checks"]


def test_preflight_rejects_formal_seed(tmp_path: Path) -> None:
    report = _report(tmp_path, formal_seed=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "formal_seed_records_zero" in report["final_decision"]["failed_checks"]


def test_preflight_rejects_existing_planned_training_output(tmp_path: Path) -> None:
    report = _report(tmp_path, planned_exists=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "planned_training_output_dir_absent" in report["final_decision"]["failed_checks"]


def test_preflight_rejects_prior_eval_tensor_overlap(tmp_path: Path) -> None:
    report = _report(tmp_path, overlap=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "prior_eval_tensor_overlap_within_limit" in report["final_decision"]["failed_checks"]
    assert report["candidate_tensor_overlap"]["prior_hashes_in_evaluation_count"] == 6


def test_preflight_cli_writes_manifest_command_plan_and_runbook(tmp_path: Path) -> None:
    prior = tmp_path / "prior"
    evaluation = tmp_path / "evaluation"
    _write_logs(prior, prefix="prior", seed=301)
    _write_logs(evaluation, prefix="eval", seed=401)
    trainer = _trainer(tmp_path / "train_diffusion_planner_static_camp.py")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "out" / "preflight.json"
    output_md = tmp_path / "out" / "preflight.md"
    output_manifest = tmp_path / "out" / "selection_manifest.json"
    output_command = tmp_path / "out" / "training_command_plan.json"
    output_runbook = tmp_path / "out" / "run_training.sh"

    exit_code = main(
        [
            "--prior_output_dir",
            str(prior),
            "--evaluation_output_dir",
            str(evaluation),
            "--trainer_py",
            str(trainer),
            "--v13_audit_md",
            str(audit),
            "--planned_training_output_dir",
            str(tmp_path / "planned_training"),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--expected_prior_selection_log_count",
            "2",
            "--expected_evaluation_selection_log_count",
            "2",
            "--expected_prior_records",
            "6",
            "--expected_evaluation_records",
            "6",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_selection_manifest_json",
            str(output_manifest),
            "--output_command_plan_json",
            str(output_command),
            "--output_runbook",
            str(output_runbook),
            "--enable_v13_static_dp_reward_eval_plus_prior_training_preflight",
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"]["passed"] is True
    assert json.loads(output_manifest.read_text(encoding="utf-8"))["selection_log_count"] == 4
    assert json.loads(output_command.read_text(encoding="utf-8"))["selection_log_count"] == 4
    assert "training_execution_only" in output_md.read_text(encoding="utf-8")
    assert "--require_atom_schema" in output_runbook.read_text(encoding="utf-8")
