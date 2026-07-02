import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension  # noqa: E402

SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_fixed_dp_candidate_training.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_training_preflight", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _patch_small(module, monkeypatch) -> None:
    monkeypatch.setattr(module, "EXPECTED_LOG_COUNT", 2)
    monkeypatch.setattr(module, "EXPECTED_RECORDS", 6)


def _record(step: int, tensor_hash: str, *, feasible: bool = True) -> dict:
    candidate_count = 8
    atom_version, atom_names = atom_schema_for_dimension(9)
    atoms = [[float(index + 1) for index in range(9)] for _ in range(candidate_count)]
    tensor = {
        "sha256": tensor_hash,
        "shape": [candidate_count, 16, 3],
        "dtype": "float32",
        "hash_input": "contiguous_candidate_tensor_bytes",
        "nan_policy": "preserve_tensor_bytes",
    }
    feasible_mask = [False] * candidate_count
    if feasible:
        feasible_mask[0] = True
    return {
        "selection_step": step,
        "selected_index": 0,
        "executed_index": 0,
        "shadow_selected_index": 0,
        "num_candidates": candidate_count,
        "atoms": atoms,
        "normalized_atoms": atoms,
        "atom_schema_version": atom_version,
        "atom_names": list(atom_names),
        "feasible_mask": feasible_mask,
        "dp_candidate_rewards": [
            {"total": 10.0 - float(index), "progress": float(index) * 0.1}
            for index in range(candidate_count)
        ],
        "candidate_closed_loop_outcomes": None,
        "candidate_reference_blend_steps": None,
        "perfect_tracker_command_postselection": None,
        "traffic_light_hybrid_postselection": None,
        "underprogress_relaxation": None,
        "splice_shadow_rule": None,
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": candidate_count,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "changes_diffusion_planner_weights": False,
        },
        "camp_candidate_tensor_provenance": {
            "schema_version": "dp_native_candidate_tensor_provenance_payload_v1",
            "selection_effect": False,
            "candidate_generation_effect": False,
            "candidate_tensor_mutation_effect": False,
            "candidate_generation_authorized": False,
            "trajectory_rewrite_authorized": False,
            "dp_modification_authorized": False,
            "outcome_label_input": False,
            "closed_loop_outcome_fields_read": False,
            "payload_valid": True,
            "pre_post_tensor_hash_equal": True,
            "selected_index_in_range": True,
            "no_candidate_row_append": True,
            "no_coordinate_heading_speed_rewrite_by_camp": True,
            "reference_blend_stage_hash_separated": True,
            "candidate_count": candidate_count,
            "post_selector_candidate_count": candidate_count,
            "selected_index": 0,
            "pre_camp_scoring_tensor": tensor,
            "post_camp_selector_tensor": tensor,
        },
        "default_off_shadow_selector": {
            "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "enabled": True,
            "default_off": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "score_expression": "score_k(w)=a_k^T w",
            "selection_effect": False,
            "online_selector_change": False,
            "artifact_contract_ready": True,
            "failed_closed_reason": None,
            "executed_index": 0,
            "shadow_selected_index": 0,
            "candidate_tensor_hash": tensor,
        },
    }


def _trainer(tmp_path: Path) -> Path:
    path = tmp_path / "train_diffusion_planner_static_camp.py"
    path.write_text(
        "\n".join(
            [
                "def _run_dp_native_training_data_contract_preflight():",
                "    pass",
                "def validate_atom_schema():",
                "    pass",
                "weights = exp_logits / np.sum(exp_logits)",
                "weights /= np.sum(weights)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _fixture(
    tmp_path: Path,
    module,
    *,
    wrong_gate: bool = False,
    planned_output_exists: bool = False,
) -> dict:
    source_root = tmp_path / "execution"
    logs = []
    for log_index, seed in enumerate((1, 2), start=1):
        out_dir = source_root / f"route_{log_index}" / f"seed_{seed}"
        records = [
            _record(step, f"{log_index:02x}{step:02x}" * 16, feasible=step != 2)
            for step in range(3)
        ]
        _write_json(out_dir / "camp_selection_log.json", records)
        logs.append(out_dir / "camp_selection_log.json")

    data_prep_dir = tmp_path / "data_preparation"
    data_prep_dir.mkdir()
    manifest_path = data_prep_dir / "training_input_manifest.json"
    _write_json(
        manifest_path,
        {
            "schema_version": module.EXPECTED_TRAINING_INPUT_MANIFEST_SCHEMA_VERSION,
            "manifest_role": "v14_public_simulator_fixed_dp_candidate_training_input_manifest",
            "source_execution_output_root": str(source_root),
            "source_zero_overlap_artifact_dir": str(tmp_path / "zero_overlap"),
            "planned_output_dir": str(data_prep_dir),
            "selection_logs": [str(path) for path in logs],
            "expected_selection_log_count": module.EXPECTED_LOG_COUNT,
            "expected_steps_per_log": 3,
            "expected_records": module.EXPECTED_RECORDS,
            "expected_num_candidates": module.EXPECTED_NUM_CANDIDATES,
            "zero_overlap_intersections": {
                "candidate_tensor_hash_intersection_count": 0,
                "path_signature_intersection_count": 0,
                "record_identity_intersection_count": 0,
                "split_manifest_root_intersection_count": 0,
            },
            "training_data_contract": {
                "passed": True,
                "records": module.EXPECTED_RECORDS,
                "failed_record_count": 0,
                "future_training_input_contract_satisfied": True,
            },
            "fixed_dp_candidate_tensor_only": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
            "formal_seeds_11_12_13_excluded": True,
            "forbidden_operations": {
                "candidate_generation_by_camp": False,
                "trajectory_generation_by_camp": False,
                "trajectory_modification_by_camp": False,
                "reference_blend": False,
                "guidance": False,
                "postprocess_or_postselection": False,
                "closed_loop_outcome_input": False,
                "dp_modification": False,
                "selector_promotion": False,
                "atom_promotion": False,
                "deployment": False,
                "safety_benefit_claim": False,
                "camp_over_dp_top1_claim": False,
            },
            "heads": {
                "current_camp_head": "abc",
                "current_dp_head": module.FIXED_DP_HEAD,
                "required_dp_head": module.FIXED_DP_HEAD,
            },
        },
    )

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    target = "old_gate" if wrong_gate else module.AUTHORIZED_CURRENT_WORK
    v14_audit = docs_dir / "diffusion_planner_v14_iteration_audit.md"
    v14_audit.write_text(
        "\n".join(
            [
                f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
                f"next_work_target={target}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    current_status = docs_dir / "diffusion_planner_current_status.md"
    current_status.write_text(
        "\n".join(
            [
                module.EXPECTED_CURRENT_STATUS,
                module.AUTHORIZED_CURRENT_WORK,
                "",
            ]
        ),
        encoding="utf-8",
    )
    planned_training_output_dir = tmp_path / "planned_training"
    if planned_output_exists:
        planned_training_output_dir.mkdir()
    return {
        "training_input_manifest_json": manifest_path,
        "data_preparation_artifact_dir": data_prep_dir,
        "trainer_py": _trainer(tmp_path),
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "planned_training_output_dir": planned_training_output_dir,
        "output_dir": tmp_path / "out",
        "current_camp_head": "abc",
        "current_camp_origin_main": "abc",
        "current_dp_head": module.FIXED_DP_HEAD,
    }


def test_v14_training_preflight_passes_and_writes_guarded_plan(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    summary = report["training_input_summary"]
    command_plan = report["training_command_plan"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_execution_authorized_next"] is True
    assert decision["training_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["score_expression"] == "score_k(w)=a_k^T w"
    assert decision["approved_atoms_nonnegative_simplex_only"] is True
    assert summary["records_total"] == 6
    assert summary["usable_feasible_records"] == 4
    assert summary["all_infeasible_records"] == 2
    assert summary["atom_schema_versions"] == {"camp_legacy_v1_9d": 6}
    assert command_plan["training_execution_performed"] is False
    assert command_plan["label_source"] == "dp_reward"
    assert command_plan["forbidden_tokens_absent"] is True
    assert "--require_dp_native_training_data_contract" in command_plan["command"]
    assert "--require_atom_schema" in command_plan["command"]
    assert (kwargs["output_dir"] / "selection_manifest.json").is_file()
    assert (kwargs["output_dir"] / "training_command_plan.json").is_file()
    assert (kwargs["output_dir"] / "run_training_after_authorization.sh").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_training_preflight_rejects_wrong_eof_gate(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, wrong_gate=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_v14_training_preflight_rejects_existing_planned_output(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, planned_output_exists=True)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    assert report["final_decision"]["passed"] is False
    assert "planned_training_output_dir_absent" in report["final_decision"]["failed_checks"]
    assert not (kwargs["output_dir"] / "training_command_plan.json").exists()
    assert not (kwargs["output_dir"] / "run_training_after_authorization.sh").exists()
    assert (kwargs["output_dir"] / "training_preflight_report.json").is_file()


def test_v14_training_preflight_rejects_closed_loop_label_source(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs, label_source="closed_loop_outcome")

    assert report["final_decision"]["passed"] is False
    assert "label_source_dp_reward" in report["final_decision"]["failed_checks"]
    assert "command_excludes_forbidden_tokens" in report["final_decision"]["failed_checks"]
