import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "audit_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution.py"
)
CAMP_HEAD = "dbd5b539a0117c47ea0809e923940619ec41214a"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_runtime_execution_audit", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _record(
    module,
    *,
    selected_index: int = 0,
    shadow_index: int = 1,
    feasible_mask=None,
    selection_scores=None,
    used_fallback: bool = False,
):
    weights = [1.0 / module.EXPECTED_ATOM_COUNT] * module.EXPECTED_ATOM_COUNT
    atoms = [
        [float(candidate + atom + 1) for atom in range(module.EXPECTED_ATOM_COUNT)]
        for candidate in range(module.EXPECTED_NUM_CANDIDATES)
    ]
    scores = [sum(value * weight for value, weight in zip(row, weights)) for row in atoms]
    if feasible_mask is None:
        feasible_mask = [True] * module.EXPECTED_NUM_CANDIDATES
    if selection_scores is None:
        selection_scores = scores
    return {
        "selection_step": 0,
        "selected_index": selected_index,
        "executed_index": selected_index,
        "shadow_selected_index": shadow_index,
        "default_off_shadow_selector": {
            "schema_version": module.RUNTIME_MANIFEST_SCHEMA,
            "enabled": True,
            "default_off": True,
            "source_scope": "public_simulator_fixed_dp_candidate_tensor",
            "selection_effect": False,
            "online_selector_change": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": module.SCORE_EXPRESSION,
            "executed_index": selected_index,
            "executed_output_policy": "dp_top1",
            "shadow_selected_index": shadow_index,
            "failed_closed_reason": None,
            "artifact_contract_ready": True,
        },
        "perfect_tracker_command_postselection": None,
        "traffic_light_hybrid_postselection": None,
        "underprogress_relaxation": None,
        "splice_shadow_rule": None,
        "candidate_reference_blend_steps": None,
        "candidate_generation_contract": {
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "changes_diffusion_planner_weights": False,
            "guidance": {
                "config_path": None,
                "config_sha256": None,
                "functions": [],
                "guidance_scale": None,
            },
        },
        "candidate_closed_loop_outcomes": None,
        "candidate_closed_loop_outcome_weights": None,
        "atom_schema_version": module.ATOM_SCHEMA_VERSION,
        "feasible_mask": feasible_mask,
        "used_fallback": used_fallback,
        "scores": scores,
        "weights": weights,
        "selection_scores": selection_scores,
        "selection_weights": weights,
        "normalized_atoms": atoms,
        "selection_normalized_atoms": atoms,
    }


def _fixture(tmp_path: Path, module, *, selected_index: int = 0):
    execution_dir = tmp_path / "execution_artifact"
    execution_dir.joinpath("logs").mkdir(parents=True)
    execution_dir.joinpath("HEADS").write_text(
        "\n".join(
            [
                f"CAMP_HEAD={CAMP_HEAD}",
                f"CAMP_ORIGIN_MAIN={CAMP_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    execution_dir.joinpath("COMMAND.txt").write_text("bash run_runtime_shadow_replay.sh\n", encoding="utf-8")
    execution_dir.joinpath("runbook.exit").write_text("0\n", encoding="utf-8")
    execution_dir.joinpath("logs", "stdout.log").write_text(
        "Running runtime default-off shadow replay command 1/2\n",
        encoding="utf-8",
    )
    execution_dir.joinpath("logs", "stderr.log").write_text("", encoding="utf-8")
    execution_dir.joinpath("SHA256SUMS").write_text("", encoding="utf-8")

    manifest = {
        "schema_version": module.RUNTIME_MANIFEST_SCHEMA,
        "default_off": True,
        "fail_closed": True,
        "selection_effect": False,
        "online_selector_change": False,
        "selector_mode": "static",
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "required_candidate_count": module.EXPECTED_NUM_CANDIDATES,
        "atom_count": module.EXPECTED_ATOM_COUNT,
        "atom_schema_version": module.ATOM_SCHEMA_VERSION,
        "score_expression": module.SCORE_EXPRESSION,
        "required_dp_head": module.FIXED_DP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "authorizations": {
            "runtime_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    runtime_manifest = _write_json(tmp_path / "runtime_manifest.json", manifest)
    preflight = _write_json(
        tmp_path / "preflight.json",
        {
            "final_decision": {
                "passed": True,
                "shadow_replay_execution_authorized_next": True,
                "candidate_generation_by_camp_authorized": False,
                "trajectory_modification_by_camp_authorized": False,
                "dp_modification_authorized": False,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
            }
        },
    )
    output_root = tmp_path / "runtime_execution"
    for run_id in range(2):
        run_root = (
            output_root
            / "sample_normal"
            / f"seed_{run_id + 1}"
            / "tl_on"
            / "runtime_default_off_shadow_replay"
        )
        records = [
            _record(module, selected_index=selected_index, shadow_index=record_index % 2)
            for record_index in range(3)
        ]
        _write_json(run_root / "camp_selection_log.json", records)
        _write_json(run_root / "camp_validation_summary.json", {"records": 3})
        _write_json(run_root / "camp_replay_summary.json", {"records": 3})

    return {
        "execution_artifact_dir": execution_dir,
        "base_output_dir": output_root,
        "preflight_json": preflight,
        "runtime_manifest_json": runtime_manifest,
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_log_count": 2,
        "expected_steps_per_log": 3,
        "expected_records": 6,
        "enabled": True,
    }


def test_runtime_shadow_replay_execution_audit_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["status"] == module.READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["candidate_generation_by_camp_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False
    assert report["execution"]["selection_log_count"] == 2
    assert report["records"]["record_count"] == 6
    assert report["records"]["executed_top1_records"] == 6
    assert report["records"]["shadow_selected_index_nonzero_records"] == 2
    assert report["records"]["max_affine_score_error"] == 0.0


def test_runtime_shadow_replay_execution_audit_is_default_off_when_disabled(tmp_path: Path) -> None:
    module = _load_module()
    missing = tmp_path / "missing"

    report = module.build_report(
        execution_artifact_dir=missing,
        base_output_dir=missing,
        preflight_json=missing,
        runtime_manifest_json=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=module.FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == module.DISABLED_STATUS
    assert report["final_decision"]["passed"] is False
    assert report["review_checks"] == []


def test_runtime_shadow_replay_execution_audit_rejects_execution_effect(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, selected_index=2)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "executed_top1_violations" in report["final_decision"]["failed_checks"]
    assert "default_off_contract_violations" in report["final_decision"]["failed_checks"]


def test_runtime_shadow_replay_execution_audit_accepts_fail_closed_mask(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    log_path = next(kwargs["base_output_dir"].rglob("camp_selection_log.json"))
    fallback_records = [
        _record(
            module,
            shadow_index=0,
            feasible_mask=[False] * module.EXPECTED_NUM_CANDIDATES,
            selection_scores=[0.0]
            + [float("inf")] * (module.EXPECTED_NUM_CANDIDATES - 1),
            used_fallback=True,
        )
        for _ in range(3)
    ]
    _write_json(log_path, fallback_records)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is True
    assert report["records"]["used_fallback_records"] == 3
    assert report["records"]["violation_counts"]["selection_score_mask"] == 0
