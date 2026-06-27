from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.build_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest import (
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    RUNTIME_MANIFEST_SCHEMA_VERSION,
    build_runtime_manifest,
    main,
)


CAMP_HEAD = "ea886159676ef306faf244786403336efe037857"


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_materialization_plan(
    tmp_path: Path,
    *,
    output_runtime_manifest_json: Path,
    atom_bytes: bytes = b"atom-scales",
    weights_bytes: bytes = b"static-weights",
    atom_sha_override: str | None = None,
    runtime_schema: str = RUNTIME_MANIFEST_SCHEMA_VERSION,
    candidate_count: int = 8,
    runtime_authorized: bool = False,
) -> tuple[Path, Path, Path]:
    atom_scales = tmp_path / "atom_scales.json"
    static_weights = tmp_path / "weights.npy"
    atom_scales.write_bytes(atom_bytes)
    static_weights.write_bytes(weights_bytes)
    atom_sha = atom_sha_override or _sha256(atom_scales)
    weights_sha = _sha256(static_weights)
    plan = {
        "schema_version": (
            "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_v1"
        ),
        "materialization_plan": {
            "status": "plan_ready_no_runtime_manifest_written",
            "planned_runtime_manifest_path": str(output_runtime_manifest_json),
            "this_plan_is_runtime_manifest": False,
            "runtime_manifest_written_by_this_gate": False,
            "runtime_execution_enabled_by_this_gate": False,
            "future_manifest_required_content": {
                "schema_version": runtime_schema,
                "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
                "default_off": True,
                "selection_effect": False,
                "selector_mode": "static",
                "candidate_operation": "fixed DP candidate reranking only",
                "executed_output_policy": "dp_top1",
                "required_candidate_count": candidate_count,
                "atom_count": 14,
                "atom_schema_version": "dp_camp_v10_14d",
                "score_expression": "score_k(w)=a_k^T w",
                "required_dp_head": FIXED_DP_HEAD,
                "artifacts": {
                    "atom_scales": {
                        "logical_name": "atom_scales",
                        "path": str(atom_scales),
                        "sha256": atom_sha,
                        "required": True,
                    },
                    "static_weights": {
                        "logical_name": "static_weights",
                        "path": str(static_weights),
                        "sha256": weights_sha,
                        "required": True,
                    },
                },
                "sha256": {
                    "atom_scales": atom_sha,
                    "atom_scales.json": atom_sha,
                    "static_weights": weights_sha,
                    "weights.npy": weights_sha,
                },
            },
        },
        "final_decision": {
            "status": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_ready"
            ),
            "passed": True,
            "failed_checks": [],
            "default_off_shadow_selector_runtime_execution_authorized": runtime_authorized,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "production_selector_change_authorized": False,
        },
    }
    plan_path = tmp_path / "materialization_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return plan_path, atom_scales, static_weights


def test_materializer_is_default_off_and_does_not_read_missing_inputs(tmp_path: Path) -> None:
    output = tmp_path / "runtime_manifest.json"
    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=tmp_path / "missing_plan.json",
        expected_materialization_plan_sha256="0" * 64,
        output_runtime_manifest_json=output,
        current_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["checks"] == []
    assert not output.exists()


def test_materializer_writes_exact_runtime_manifest_shape_when_enabled(
    tmp_path: Path,
) -> None:
    output = tmp_path / "runtime_manifest.json"
    plan_path, atom_scales, static_weights = _write_materialization_plan(
        tmp_path,
        output_runtime_manifest_json=output,
    )

    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=plan_path,
        expected_materialization_plan_sha256=_sha256(plan_path),
        output_runtime_manifest_json=output,
        current_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        label="unit-test",
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["runtime_manifest_written"] is True
    assert output.is_file()
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == RUNTIME_MANIFEST_SCHEMA_VERSION
    assert manifest["manifest_role"] == "default_off_shadow_selector_runtime_artifact_manifest"
    assert manifest["default_off"] is True
    assert manifest["selection_effect"] is False
    assert manifest["selector_mode"] == "static"
    assert manifest["candidate_operation"] == "fixed DP candidate reranking only"
    assert manifest["executed_output_policy"] == "dp_top1"
    assert manifest["required_candidate_count"] == 8
    assert manifest["atom_count"] == 14
    assert manifest["atom_schema_version"] == "dp_camp_v10_14d"
    assert manifest["score_expression"] == "score_k(w)=a_k^T w"
    assert manifest["required_dp_head"] == FIXED_DP_HEAD
    assert manifest["artifacts"]["atom_scales"]["path"] == str(atom_scales)
    assert manifest["artifacts"]["atom_scales"]["sha256"] == _sha256(atom_scales)
    assert manifest["artifacts"]["static_weights"]["path"] == str(static_weights)
    assert manifest["artifacts"]["static_weights"]["sha256"] == _sha256(static_weights)
    assert manifest["sha256"]["atom_scales"] == _sha256(atom_scales)
    assert manifest["sha256"][str(atom_scales)] == _sha256(atom_scales)
    assert manifest["sha256"]["static_weights"] == _sha256(static_weights)
    assert manifest["sha256"][str(static_weights)] == _sha256(static_weights)
    assert manifest["authorizations"]["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert manifest["authorizations"]["dp_modification_authorized"] is False
    assert manifest["authorizations"]["training_executed"] is False


def test_materializer_rejects_plan_hash_mismatch_without_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "runtime_manifest.json"
    plan_path, _, _ = _write_materialization_plan(tmp_path, output_runtime_manifest_json=output)

    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=plan_path,
        expected_materialization_plan_sha256="0" * 64,
        output_runtime_manifest_json=output,
        current_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "materialization_plan_sha256_matches_expected" in report["final_decision"]["failed_checks"]
    assert not output.exists()


def test_materializer_rejects_artifact_hash_mismatch_without_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "runtime_manifest.json"
    plan_path, _, _ = _write_materialization_plan(
        tmp_path,
        output_runtime_manifest_json=output,
        atom_sha_override="0" * 64,
    )

    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=plan_path,
        expected_materialization_plan_sha256=_sha256(plan_path),
        output_runtime_manifest_json=output,
        current_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "atom_scales_sha256_matches" in report["final_decision"]["failed_checks"]
    assert not output.exists()


def test_materializer_rejects_dp_head_drift_without_output(tmp_path: Path) -> None:
    output = tmp_path / "runtime_manifest.json"
    plan_path, _, _ = _write_materialization_plan(tmp_path, output_runtime_manifest_json=output)

    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=plan_path,
        expected_materialization_plan_sha256=_sha256(plan_path),
        output_runtime_manifest_json=output,
        current_camp_head=CAMP_HEAD,
        current_dp_head="0" * 40,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert not output.exists()


def test_materializer_rejects_output_path_drift_without_output(tmp_path: Path) -> None:
    planned_output = tmp_path / "planned_runtime_manifest.json"
    actual_output = tmp_path / "actual_runtime_manifest.json"
    plan_path, _, _ = _write_materialization_plan(
        tmp_path,
        output_runtime_manifest_json=planned_output,
    )

    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=plan_path,
        expected_materialization_plan_sha256=_sha256(plan_path),
        output_runtime_manifest_json=actual_output,
        current_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "output_path_matches_source_plan" in report["final_decision"]["failed_checks"]
    assert not planned_output.exists()
    assert not actual_output.exists()


def test_materializer_rejects_existing_output_without_overwrite(tmp_path: Path) -> None:
    output = _write(tmp_path / "runtime_manifest.json", "existing")
    plan_path, _, _ = _write_materialization_plan(tmp_path, output_runtime_manifest_json=output)

    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=plan_path,
        expected_materialization_plan_sha256=_sha256(plan_path),
        output_runtime_manifest_json=output,
        current_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "output_runtime_manifest_absent_before_write" in report["final_decision"]["failed_checks"]
    assert output.read_text(encoding="utf-8") == "existing"


def test_materializer_rejects_schema_or_candidate_count_drift_without_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "runtime_manifest.json"
    plan_path, _, _ = _write_materialization_plan(
        tmp_path,
        output_runtime_manifest_json=output,
        runtime_schema="wrong_schema",
        candidate_count=9,
    )

    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=plan_path,
        expected_materialization_plan_sha256=_sha256(plan_path),
        output_runtime_manifest_json=output,
        current_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "future_manifest_schema" in report["final_decision"]["failed_checks"]
    assert "future_manifest_candidate_count" in report["final_decision"]["failed_checks"]
    assert not output.exists()


def test_materializer_rejects_runtime_or_promotion_authorization_leaks(
    tmp_path: Path,
) -> None:
    output = tmp_path / "runtime_manifest.json"
    plan_path, _, _ = _write_materialization_plan(
        tmp_path,
        output_runtime_manifest_json=output,
        runtime_authorized=True,
    )

    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=plan_path,
        expected_materialization_plan_sha256=_sha256(plan_path),
        output_runtime_manifest_json=output,
        current_camp_head=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_plan_default_off_shadow_selector_runtime_execution_authorized_false"
        in report["final_decision"]["failed_checks"]
    )
    assert not output.exists()


def test_materializer_does_not_run_replay_or_touch_dp_sources() -> None:
    source = Path(
        "scripts/integrations/build_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest.py"
    ).read_text(encoding="utf-8")

    assert "subprocess" not in source
    assert "run_diffusion_planner" not in source
    assert "/root/autodl-tmp/Diffusion-Planner" not in source
    assert "Diffusion-Planner" not in source


def test_materializer_cli_writes_manifest(tmp_path: Path) -> None:
    output = tmp_path / "runtime_manifest.json"
    plan_path, _, _ = _write_materialization_plan(tmp_path, output_runtime_manifest_json=output)

    exit_code = main(
        [
            "--artifact_manifest_materialization_plan_json",
            str(plan_path),
            "--expected_materialization_plan_sha256",
            _sha256(plan_path),
            "--output_runtime_manifest_json",
            str(output),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--enable_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == RUNTIME_MANIFEST_SCHEMA_VERSION
