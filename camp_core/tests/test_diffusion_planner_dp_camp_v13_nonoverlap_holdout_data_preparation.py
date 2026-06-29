from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.run_diffusion_planner_dp_camp_v13_nonoverlap_holdout_data_preparation import (
    AUTHORIZED_CURRENT_WORK,
    DISABLED_STATUS,
    EXPECTED_LOG_COUNT,
    EXPECTED_RECORDS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    _materialize_registries,
)


CAMP_HEAD = "8a9cfb30232ec13b90c1875df137524365841df5"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _request_manifest(path: Path, *, formal_seed: bool = False) -> Path:
    requests = [
        {
            "request_id": f"v13_nonformal_holdout_{index:03d}",
            "route_id": f"nonformal_route_{index:03d}",
            "scenario_tag": "nonformal_holdout_manifest_only",
            "seed": 1000 + index,
        }
        for index in range(EXPECTED_LOG_COUNT)
    ]
    if formal_seed:
        requests[0]["seed"] = 11
    return _write_json(
        path,
        {
            "schema_version": "dp_camp_v13_nonoverlap_holdout_candidate_request_manifest_v1",
            "target_holdout_selection_logs": EXPECTED_LOG_COUNT,
            "target_holdout_records": EXPECTED_RECORDS,
            "expected_steps_per_log": 100,
            "expected_candidate_count": 8,
            "expected_atom_count": 14,
            "formal_seeds_11_12_13_excluded": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "nonnegative_simplex_weights_only": True,
            "route_seed_requests": requests,
        },
    )


def _expected_manifest(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "dp_camp_v13_nonoverlap_holdout_expected_artifact_manifest_v1",
            "manifest_role": "nonoverlap_holdout_expected_artifact_manifest",
            "expected_selection_log_count": EXPECTED_LOG_COUNT,
            "expected_records": EXPECTED_RECORDS,
            "expected_steps_per_log": 100,
            "expected_candidate_count": 8,
            "expected_atom_count": 14,
            "required_outputs": [
                "selection_logs",
                "candidate_tensor_hash_registry.json",
                "path_signature_registry.json",
                "record_identity_hash_registry.json",
                "SHA256SUMS",
            ],
        },
    )


def _exclusion_manifest(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "dp_camp_v13_nonoverlap_holdout_exclusion_registry_manifest_v1",
            "manifest_role": "nonoverlap_holdout_exclusion_registry_manifest",
            "train_eval_candidate_tensor_intersection_must_be_zero": True,
            "train_eval_path_signature_intersection_must_be_zero": True,
            "train_eval_record_identity_intersection_must_be_zero": True,
            "formal_seeds_11_12_13_excluded": True,
        },
    )


def _runtime_manifest(path: Path, atom_scales: Path, weights: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
            "default_off": True,
            "selection_effect": False,
            "selector_mode": "static",
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "required_candidate_count": 8,
            "score_expression": "score_k(w)=a_k^T w",
            "current_dp_head": FIXED_DP_HEAD,
            "required_dp_head": FIXED_DP_HEAD,
            "artifacts": {
                "atom_scales": {
                    "logical_name": "atom_scales",
                    "path": str(atom_scales),
                    "required": True,
                    "sha256": _sha256(atom_scales),
                },
                "static_weights": {
                    "logical_name": "static_weights",
                    "path": str(weights),
                    "required": True,
                    "sha256": _sha256(weights),
                },
            },
        },
    )


def _runner_source(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                'parser.add_argument("--camp_default_off_shadow_selector")',
                '{"executed_output_policy": "dp_top1"}',
                "shadow_selected_index",
                "",
            ]
        ),
    )


def _audit(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"next_work_target={AUTHORIZED_CURRENT_WORK}",
                "data_preparation_authorized_by_current_boundary=True",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=True",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def _fixture(tmp_path: Path, *, formal_seed: bool = False) -> dict[str, Any]:
    atom_scales = _write(tmp_path / "artifacts" / "atom_scales.json", "{}")
    weights = tmp_path / "artifacts" / "weights.npy"
    weights.parent.mkdir(parents=True, exist_ok=True)
    weights.write_bytes(b"weights")
    route_a = _write(tmp_path / "routes" / "sample_normal.pkl", "route")
    route_b = _write(tmp_path / "routes" / "sample_tl.pkl", "route")
    diffusion_repo = tmp_path / "Diffusion-Planner"
    diffusion_repo.mkdir()
    model_path = tmp_path / "diffusion_planner.pth"
    model_path.write_bytes(b"model")
    return {
        "holdout_candidate_request_manifest_json": _request_manifest(
            tmp_path / "request.json",
            formal_seed=formal_seed,
        ),
        "expected_holdout_artifact_manifest_json": _expected_manifest(
            tmp_path / "expected.json"
        ),
        "nonoverlap_exclusion_registry_manifest_json": _exclusion_manifest(
            tmp_path / "exclusion.json"
        ),
        "runtime_manifest_json": _runtime_manifest(
            tmp_path / "runtime_manifest.json",
            atom_scales,
            weights,
        ),
        "replay_runner_py": _runner_source(tmp_path / "runner.py"),
        "v13_audit_md": _audit(tmp_path / "audit.md"),
        "diffusion_repo": diffusion_repo,
        "route_specs": (f"sample_normal={route_a}", f"sample_tl={route_b}"),
        "model_path": model_path,
        "model_args": _write(tmp_path / "diffusion_planner.param.json", "{}"),
        "config": _write(tmp_path / "replay_default.json", "{}"),
        "reward_config": _write(tmp_path / "dp_camp_reward_eval.json", "{}"),
        "base_output_dir": tmp_path / "holdout_data",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": FIXED_DP_HEAD,
        "enabled": True,
        "execute": False,
    }


def test_data_preparation_disabled_has_no_side_effects(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = build_report(
        holdout_candidate_request_manifest_json=missing,
        expected_holdout_artifact_manifest_json=missing,
        nonoverlap_exclusion_registry_manifest_json=missing,
        runtime_manifest_json=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
        diffusion_repo=missing,
        route_specs=("sample=/missing.pkl",),
        model_path=missing,
        model_args=missing,
        config=missing,
        reward_config=missing,
        base_output_dir=tmp_path / "out",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["planned_commands"] == []
    assert not (tmp_path / "out").exists()


def test_data_preparation_plans_fixed_dp_default_off_commands(tmp_path: Path) -> None:
    report = build_report(**_fixture(tmp_path))
    decision = report["final_decision"]
    commands = report["planned_commands"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] is None
    assert decision["training_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert len(commands) == EXPECTED_LOG_COUNT
    assert commands[0]["seed"] == 1000
    assert commands[-1]["seed"] == 1127
    assert all("--camp_default_off_shadow_selector" in row["command"] for row in commands)
    assert all("--camp_shadow_artifact_manifest" in row["command"] for row in commands)
    assert all("--camp_atom_scales" in row["command"] for row in commands)
    assert all("--camp_static_weights" in row["command"] for row in commands)
    assert all("--candidate_guidance_config" not in row["command"] for row in commands)
    assert all("--candidate_reference_blend_steps" not in row["command"] for row in commands)
    assert all("--camp_collect_closed_loop_outcomes" not in row["command"] for row in commands)


def test_data_preparation_rejects_formal_seed(tmp_path: Path) -> None:
    report = build_report(**_fixture(tmp_path, formal_seed=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "formal_seeds_excluded" in report["final_decision"]["failed_checks"]


def _record(step: int, *, selected_index: int = 0) -> dict[str, Any]:
    tensor_sha = hashlib.sha256(f"tensor-{step}".encode()).hexdigest()
    return {
        "selection_step": step,
        "selected_index": selected_index,
        "executed_index": selected_index,
        "shadow_selected_index": 1,
        "num_candidates": 8,
        "atom_schema_version": "dp_camp_v10_14d",
        "default_off_shadow_selector": {
            "candidate_tensor_hash": {
                "sha256": tensor_sha,
                "shape": [8, 80, 2],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            }
        },
        "candidate_generation_contract": {
            "reference_blend_steps": None,
            "guidance_enabled": False,
        },
    }


def test_registry_materialization_requires_dp_top1_execution(tmp_path: Path) -> None:
    output_dir = tmp_path / "out" / "selection_logs" / "request_000" / "static_shadow"
    log_path = output_dir / "camp_selection_log.json"
    _write_json(log_path, [_record(0), _record(1)])
    commands = [
        {
            "request_id": "request_000",
            "source_route_id": "route_000",
            "route_name": "sample",
            "route_path": "/tmp/route.pkl",
            "seed": 1000,
            "max_npcs": 0,
            "traffic_lights": "off",
            "spawn_probability": 0.3,
            "selection_log": str(log_path),
        }
    ]

    log_summary, registry_summary, failures = _materialize_registries(
        commands=commands,
        base_output_dir=tmp_path / "out",
        expected_log_count=1,
        expected_steps_per_log=2,
        expected_records=2,
        expected_num_candidates=8,
    )

    assert failures == []
    assert log_summary["log_count"] == 1
    assert log_summary["record_count"] == 2
    assert registry_summary["candidate_tensor_hash_count"] == 2
    assert registry_summary["record_identity_hash_count"] == 2
    assert (tmp_path / "out" / "candidate_tensor_hash_registry.json").is_file()

    _write_json(log_path, [_record(0), _record(1, selected_index=2)])
    _, _, failures = _materialize_registries(
        commands=commands,
        base_output_dir=tmp_path / "out",
        expected_log_count=1,
        expected_steps_per_log=2,
        expected_records=2,
        expected_num_candidates=8,
    )

    assert "executed_index_dp_top1" in failures
