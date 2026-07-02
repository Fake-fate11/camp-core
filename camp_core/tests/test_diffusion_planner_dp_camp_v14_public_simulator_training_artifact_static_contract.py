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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_training_artifact_review", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(path: Path, files: list[Path]) -> None:
    lines = [f"{_sha256(file)}  {file.name}" for file in files]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _patch_small(module, monkeypatch) -> None:
    monkeypatch.setattr(module, "EXPECTED_RECORDS_USED", 2)
    monkeypatch.setattr(module, "EXPECTED_DROPPED_RECORDS", 1)
    monkeypatch.setattr(module, "EXPECTED_CONTRACT_RECORDS", 3)


def _fixture(
    tmp_path: Path,
    module,
    *,
    wrong_gate: bool = False,
    negative_weight: bool = False,
    label_source: str = "dp_reward",
) -> dict:
    artifact = tmp_path / "training_execution"
    artifact.mkdir()
    atom_schema, atom_names = atom_schema_for_dimension(module.EXPECTED_NUM_ATOMS)
    weights = np.full(module.EXPECTED_NUM_ATOMS, 1.0 / module.EXPECTED_NUM_ATOMS)
    if negative_weight:
        weights[0] = -0.1
        weights[1] += 0.1
    np.save(artifact / "offline_weights_dp_static.npy", weights)
    _write_json(
        artifact / "atom_scales_dp_static.json",
        {
            "atom_schema_version": atom_schema,
            "atom_names": list(atom_names),
            "scales": [1.0 + float(index) for index in range(module.EXPECTED_NUM_ATOMS)],
        },
    )
    _write_json(
        artifact / "training_summary.json",
        {
            "training_type": module.EXPECTED_TRAINING_TYPE,
            "label_source": label_source,
            "reward_key": module.EXPECTED_REWARD_KEY if label_source == "dp_reward" else None,
            "outcome_key": "value" if label_source == "closed_loop_outcome" else None,
            "outcome_weights_path": None,
            "outcome_weights": None,
            "reward_progress_weight": (
                module.EXPECTED_REWARD_PROGRESS_WEIGHT
                if label_source == "dp_reward"
                else None
            ),
            "selection_logs": ["one", "two"],
            "num_records": module.EXPECTED_RECORDS_USED,
            "dropped_records_without_feasible_candidate": module.EXPECTED_DROPPED_RECORDS,
            "num_candidates": module.EXPECTED_NUM_CANDIDATES,
            "num_atoms": module.EXPECTED_NUM_ATOMS,
            "atom_schema_version": atom_schema,
            "atom_names": list(atom_names),
            "atom_schema": {"passed": True},
            "dp_native_training_data_contract": {
                "records": module.EXPECTED_CONTRACT_RECORDS,
                "failed_records": [],
                "future_training_input_contract_satisfied": True,
                "candidate_generation_executed": False,
                "dp_modification_authorized": False,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
            },
            "scale_percentile": 95.0,
            "proxy_weights_normalized": None,
            "trained_weights": weights.tolist(),
            "oracle_match_rate": 0.25,
            "feasible_candidate_rate": 1.0,
            "records_with_any_infeasible": 1,
            "weights_path": str(artifact / "offline_weights_dp_static.npy"),
            "atom_scales_path": str(artifact / "atom_scales_dp_static.json"),
            "history": [{"epoch": 1.0, "loss": 1.0, "oracle_match_rate": 0.25}],
            "caveat": "Candidate-level DP rewards are model-based preferences.",
        },
    )
    (artifact / "HEADS").write_text(
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
    (artifact / "exit.code").write_text("0\n", encoding="utf-8")
    (artifact / "planned_output_files.txt").write_text(
        "\n".join(module.EXPECTED_OUTPUT_FILES) + "\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        artifact / "SHA256SUMS",
        [
            artifact / "training_summary.json",
            artifact / "atom_scales_dp_static.json",
            artifact / "offline_weights_dp_static.npy",
        ],
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
        "\n".join(
            [
                module.EXPECTED_CURRENT_STATUS,
                module.AUTHORIZED_CURRENT_WORK,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "training_execution_artifact_dir": artifact,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": "abc",
        "current_camp_origin_main": "abc",
        "current_dp_head": module.FIXED_DP_HEAD,
    }


def test_training_artifact_static_contract_review_passes(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    review = report["artifact_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["trained_default_off_shadow_replay_evaluation_preflight_authorized_next"] is True
    assert decision["replay_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert review["weights_nonnegative"] is True
    assert abs(review["weights_sum"] - 1.0) <= 1e-9
    assert (kwargs["output_dir"] / "training_artifact_static_contract_report.json").is_file()
    assert (kwargs["output_dir"] / "training_artifact_static_contract_report.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_training_artifact_static_contract_review_rejects_wrong_eof(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, wrong_gate=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_training_artifact_static_contract_review_rejects_negative_weight(tmp_path: Path, monkeypatch) -> None:
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


def test_training_artifact_static_contract_review_rejects_closed_loop_label(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    _patch_small(module, monkeypatch)
    kwargs = _fixture(tmp_path, module, label_source="closed_loop_outcome")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "label_source" in report["final_decision"]["failed_checks"]
    assert "closed_loop_outcome_key_absent" in report["final_decision"]["failed_checks"]
