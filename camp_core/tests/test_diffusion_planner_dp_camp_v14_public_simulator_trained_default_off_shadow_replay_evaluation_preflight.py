import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


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
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_trained_default_off_shadow_replay_evaluation.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_shadow_replay_preflight", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_sha256sums(path: Path, files: list[Path]) -> None:
    lines = [f"{_sha256(file)}  {file.name}" for file in files]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _patch_small(module, monkeypatch) -> None:
    monkeypatch.setattr(module, "ROUTE_SPECS", module.ROUTE_SPECS[:1])
    monkeypatch.setattr(module, "EXPECTED_PUBLIC_ASSETS", ())
    monkeypatch.setattr(module, "EXPECTED_LOG_COUNT", 2)
    monkeypatch.setattr(module, "EXPECTED_STEPS_PER_LOG", 3)
    monkeypatch.setattr(module, "EXPECTED_RECORDS", 6)
    monkeypatch.setattr(module, "EXPECTED_RECORDS_USED", 2)
    monkeypatch.setattr(module, "EXPECTED_DROPPED_RECORDS", 1)
    monkeypatch.setattr(module, "EXPECTED_CONTRACT_RECORDS", 3)


def _fixture(
    tmp_path: Path,
    module,
    *,
    wrong_gate: bool = False,
    negative_weight: bool = False,
    seeds: tuple[int, ...] = (1, 2),
) -> dict:
    training_dir = tmp_path / "training_execution"
    training_dir.mkdir()
    atom_schema, atom_names = atom_schema_for_dimension(module.EXPECTED_NUM_ATOMS)
    weights = np.full(module.EXPECTED_NUM_ATOMS, 1.0 / module.EXPECTED_NUM_ATOMS)
    if negative_weight:
        weights[0] = -0.1
        weights[1] += 0.1
    np.save(training_dir / "offline_weights_dp_static.npy", weights)
    _write_json(
        training_dir / "atom_scales_dp_static.json",
        {
            "atom_schema_version": atom_schema,
            "atom_names": list(atom_names),
            "scales": [1.0 + float(index) for index in range(module.EXPECTED_NUM_ATOMS)],
        },
    )
    _write_json(
        training_dir / "training_summary.json",
        {
            "training_type": module.EXPECTED_TRAINING_TYPE,
            "label_source": module.EXPECTED_LABEL_SOURCE,
            "reward_key": module.EXPECTED_REWARD_KEY,
            "reward_progress_weight": module.EXPECTED_REWARD_PROGRESS_WEIGHT,
            "selection_logs": ["one", "two"],
            "num_records": module.EXPECTED_RECORDS_USED,
            "dropped_records_without_feasible_candidate": (
                module.EXPECTED_DROPPED_RECORDS
            ),
            "num_candidates": module.EXPECTED_NUM_CANDIDATES,
            "num_atoms": module.EXPECTED_NUM_ATOMS,
            "atom_schema_version": atom_schema,
            "atom_names": list(atom_names),
            "dp_native_training_data_contract": {
                "records": module.EXPECTED_CONTRACT_RECORDS,
                "failed_records": [],
                "future_training_input_contract_satisfied": True,
            },
            "outcome_key": None,
            "outcome_weights_path": None,
            "outcome_weights": None,
            "trained_weights": weights.tolist(),
        },
    )
    (training_dir / "HEADS").write_text(
        "\n".join(
            [
                "CAMP_HEAD=abc",
                "CAMP_ORIGIN_MAIN=abc",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (training_dir / "exit.code").write_text("0\n", encoding="utf-8")
    (training_dir / "planned_output_files.txt").write_text(
        "\n".join(module.EXPECTED_OUTPUT_FILES) + "\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        training_dir / "SHA256SUMS",
        [
            training_dir / "training_summary.json",
            training_dir / "atom_scales_dp_static.json",
            training_dir / "offline_weights_dp_static.npy",
        ],
    )

    review_dir = tmp_path / "training_review"
    review_dir.mkdir()
    review_report = {
        "final_decision": {
            "passed": True,
            "status": module.EXPECTED_CURRENT_STATUS,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        }
    }
    _write_json(review_dir / "training_artifact_static_contract_report.json", review_report)
    (review_dir / "HEADS").write_text(
        "\n".join(
            [
                "CAMP_HEAD=def",
                "CAMP_ORIGIN_MAIN=def",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (review_dir / "exit.code").write_text("0\n", encoding="utf-8")
    _write_sha256sums(
        review_dir / "SHA256SUMS",
        [review_dir / "training_artifact_static_contract_report.json"],
    )

    docs = tmp_path / "docs"
    docs.mkdir()
    target = "old_gate" if wrong_gate else module.AUTHORIZED_CURRENT_WORK
    v14_audit = docs / "diffusion_planner_v14_iteration_audit.md"
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
    current_status = docs / "diffusion_planner_current_status.md"
    current_status.write_text(
        "\n".join([module.EXPECTED_CURRENT_STATUS, module.AUTHORIZED_CURRENT_WORK, ""]),
        encoding="utf-8",
    )

    camp_repo = tmp_path / "camp_core"
    replay_script = camp_repo / module.REPLAY_SCRIPT
    replay_script.parent.mkdir(parents=True, exist_ok=True)
    replay_script.write_text("# replay\n", encoding="utf-8")
    reward_config = camp_repo / module.REWARD_CONFIG
    reward_config.parent.mkdir(parents=True, exist_ok=True)
    reward_config.write_text("{}\n", encoding="utf-8")
    dp_repo = tmp_path / "Diffusion-Planner"
    dp_config = dp_repo / module.DP_REPLAY_CONFIG
    dp_config.parent.mkdir(parents=True, exist_ok=True)
    dp_config.write_text("{}\n", encoding="utf-8")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    dp_python = tmp_path / "python"
    dp_python.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    nuscenes_root = tmp_path / "nuScenes"
    nuscenes_root.mkdir()
    output_dir = tmp_path / "out"
    return {
        "training_execution_artifact_dir": training_dir,
        "training_artifact_static_contract_review_artifact_dir": review_dir,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_json": output_dir / "shadow_replay_preflight_report.json",
        "output_md": output_dir / "shadow_replay_preflight_report.md",
        "output_runbook": output_dir / "run_trained_shadow_replay.sh",
        "output_runtime_manifest_json": output_dir / "runtime_manifest.json",
        "replay_output_root": tmp_path / "planned_shadow_replay",
        "current_camp_head": "abc",
        "current_camp_origin_main": "abc",
        "current_dp_head": module.FIXED_DP_HEAD,
        "dp_repo": dp_repo,
        "camp_repo": camp_repo,
        "assets_dir": assets_dir,
        "dp_python": dp_python,
        "public_nuscenes_root": nuscenes_root,
        "steps": module.EXPECTED_STEPS_PER_LOG,
        "num_candidates": module.EXPECTED_NUM_CANDIDATES,
        "max_npcs": 4,
        "spawn_probability": 0.3,
        "seeds": seeds,
        "traffic_light_modes": ("on",),
    }


def test_trained_default_off_shadow_replay_preflight_passes(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(
        output_json=kwargs["output_json"],
        output_md=kwargs["output_md"],
        output_runbook=kwargs["output_runbook"],
        output_runtime_manifest_json=kwargs["output_runtime_manifest_json"],
        report=report,
    )

    decision = report["final_decision"]
    preflight = report["shadow_replay_preflight"]
    manifest = report["runtime_manifest"]
    command_text = "\n".join(" ".join(command) for command in preflight["planned_commands"])
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["replay_executed"] is False
    assert decision["executed_output_policy"] == "dp_top1"
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert preflight["planned_command_count"] == module.EXPECTED_LOG_COUNT
    assert preflight["expected_records"] == module.EXPECTED_RECORDS
    assert manifest["schema_version"] == module.RUNTIME_MANIFEST_SCHEMA_VERSION
    assert manifest["artifacts"]["static_weights"]["sha256"]
    assert manifest["artifacts"]["atom_scales"]["sha256"]
    assert "--camp_default_off_shadow_selector" in command_text
    assert "--camp_shadow_artifact_manifest" in command_text
    assert "--camp_collect_closed_loop_outcomes" not in command_text
    assert kwargs["output_runtime_manifest_json"].is_file()
    assert kwargs["output_runbook"].is_file()
    assert (kwargs["output_json"].parent / "SHA256SUMS").is_file()


def test_trained_default_off_shadow_replay_preflight_rejects_wrong_eof(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, wrong_gate=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_trained_default_off_shadow_replay_preflight_rejects_negative_weight(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, negative_weight=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "weights_nonnegative" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "training_artifact_weight_or_atom_contract_failure"
    )


def test_trained_default_off_shadow_replay_preflight_rejects_formal_seed(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, seeds=(11, 12))

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "formal_seeds_forbidden" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "forbidden_shadow_replay_command_contract_failure"
    )
