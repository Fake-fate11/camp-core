from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.audit_diffusion_planner_dp_camp_v13_nonoverlap_holdout_data_preparation_execution import (
    ATOM_SCHEMA_VERSION,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_READY_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "d5350de824c55ff122d670395013642e2dcc6b9a"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _record(index: int, *, selected_index: int = 0) -> dict[str, Any]:
    return {
        "selection_step": index,
        "selected_index": selected_index,
        "executed_index": selected_index,
        "shadow_selected_index": 2,
        "num_candidates": 8,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "default_off_shadow_selector": {
            "default_off": True,
            "selection_effect": False,
            "executed_output_policy": "dp_top1",
            "score_expression": "score_k(w)=a_k^T w",
            "candidate_tensor_hash": {
                "sha256": _sha(f"tensor-{index}-{selected_index}"),
                "shape": [8, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
        "candidate_generation_contract": {
            "reference_blend_steps": None,
            "guidance_enabled": False,
        },
        "perfect_tracker_command_postselection": None,
        "traffic_light_hybrid_postselection": None,
        "underprogress_relaxation": None,
        "splice_shadow_rule": None,
    }


def _source_artifact(tmp_path: Path, *, bad_record: bool = False) -> Path:
    root = tmp_path / "source"
    holdout = root / "holdout_data"
    logs = []
    tensor_entries = []
    identity_entries = []
    path_entries = []
    record_count = 0
    for log_index in range(2):
        log_path = (
            holdout
            / "selection_logs"
            / f"request_{log_index:03d}"
            / "sample"
            / f"seed_{1000 + log_index}"
            / "static_shadow"
            / "camp_selection_log.json"
        )
        records = [
            _record(log_index * 3 + row, selected_index=2 if bad_record and log_index == 1 and row == 2 else 0)
            for row in range(3)
        ]
        _write_json(log_path, records)
        logs.append(str(log_path))
        path_entries.append(
            {
                "path_signature_hash": _sha(f"path-{log_index}"),
                "selection_log": str(log_path),
                "seed": 1000 + log_index,
            }
        )
        for row, record in enumerate(records):
            tensor_hash = record["default_off_shadow_selector"]["candidate_tensor_hash"]["sha256"]
            tensor_entries.append(
                {
                    "candidate_tensor_hash": tensor_hash,
                    "selection_log": str(log_path),
                    "record_index": row,
                }
            )
            identity_entries.append(
                {
                    "record_identity_hash": _sha(f"identity-{log_index}-{row}"),
                    "candidate_tensor_hash": tensor_hash,
                    "selection_log": str(log_path),
                }
            )
            record_count += 1
    _write_json(holdout / "candidate_tensor_hash_registry.json", {"entries": tensor_entries})
    _write_json(holdout / "path_signature_registry.json", {"entries": path_entries})
    _write_json(holdout / "record_identity_hash_registry.json", {"entries": identity_entries})
    _write(holdout / "selection_logs.txt", "\n".join(logs) + "\n")
    summary = {
        "schema_version": "dp_camp_v13_nonoverlap_holdout_data_preparation_v1",
        "final_decision": {
            "status": SOURCE_READY_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "training_preflight_authorized_next": True,
            "data_preparation_executed": True,
            "fixed_dp_candidate_generation_executed": True,
            "training_executed": False,
            "replay_evaluation_executed": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "execution": {
            "commands_completed": 2,
            "commands_planned": 2,
            "failed_commands": [],
        },
        "selection_log_summary": {
            "log_count": 2,
            "record_count": record_count,
            "expected_log_count": 2,
            "expected_records": record_count,
            "executed_index_violations": 0,
            "default_off_missing": 0,
            "atom_schema_violations": 0,
            "forbidden_runtime_flags": 0,
        },
        "registry_summary": {
            "candidate_tensor_hash_count": record_count,
            "unique_candidate_tensor_hash_count": record_count,
            "path_signature_count": 2,
            "record_identity_hash_count": record_count,
            "unique_record_identity_hash_count": record_count,
        },
        "training_data_contract": {
            "passed": True,
            "records": record_count,
            "failed_records": 0,
            "future_training_input_contract_satisfied": True,
        },
        "heads": {
            "current_camp_head": CAMP_HEAD,
            "current_camp_origin_main": CAMP_HEAD,
            "current_dp_head": FIXED_DP_HEAD,
            "required_dp_head": FIXED_DP_HEAD,
        },
    }
    _write_json(root / "data_preparation_summary.json", summary)
    _write(root / "execution.pid", "123")
    _write(root / "execution.stdout.txt", "final stdout")
    _write(root / "execution.stderr.txt", "")
    _write(
        root / "SHA256SUMS",
        "\n".join(
            [
                f"{_sha('stale')}  execution.stdout.txt",
                f"{hashlib.sha256((root / 'data_preparation_summary.json').read_bytes()).hexdigest()}  data_preparation_summary.json",
            ]
        )
        + "\n",
    )
    return root


def _audit(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"next_work_target={AUTHORIZED_CURRENT_WORK}",
                "data_preparation_authorized_by_current_boundary=True",
                "training_execution_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def test_execution_audit_accepts_complete_data_with_recorded_launch_warnings(tmp_path: Path) -> None:
    source = _source_artifact(tmp_path)
    report = build_report(
        source_artifact_dir=source,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_log_count=2,
        expected_steps_per_log=3,
        expected_records=6,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["training_preflight_authorized_next"] is True
    assert report["actual_selection_log_scan"]["record_count"] == 6
    assert report["actual_selection_log_scan"]["executed_index_violations"] == 0
    assert report["registry_files"]["candidate_tensor_hash_registry"]["entries"] == 6
    assert "source_raw_run_data_preparation_exit_missing" in decision["warnings"]
    assert "source_sha256sums_does_not_verify_post_execution" in decision["warnings"]


def test_execution_audit_rejects_non_dp_top1_execution(tmp_path: Path) -> None:
    source = _source_artifact(tmp_path, bad_record=True)
    report = build_report(
        source_artifact_dir=source,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_log_count=2,
        expected_steps_per_log=3,
        expected_records=6,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "actual_executed_index_violations_zero" in report["final_decision"]["failed_checks"]


def test_execution_audit_main_writes_independent_sha256sums(tmp_path: Path) -> None:
    source = _source_artifact(tmp_path)
    out_dir = tmp_path / "audit_out"
    rc = main(
        [
            "--source_artifact_dir",
            str(source),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
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
            "--output_json",
            str(out_dir / "execution_audit.json"),
            "--output_md",
            str(out_dir / "execution_audit.md"),
            "--output_source_sha256sums",
            str(out_dir / "source_artifact_post_execution_sha256sums.txt"),
        ]
    )

    assert rc == 0
    assert (out_dir / "execution_audit.json").is_file()
    assert (out_dir / "execution_audit.md").is_file()
    assert (out_dir / "source_artifact_post_execution_sha256sums.txt").is_file()
    assert (out_dir / "SHA256SUMS").is_file()
