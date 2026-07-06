from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation.py"
)
SOURCE_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_online_selector_activation_execution",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_actual_safetycost_online_selector_activation_execution_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["online_selector_activation_execution"] is True
    assert decision["online_selector_change_authorized"] is True
    assert decision["dp_modification"] is False
    assert decision["closed_loop_outcomes_used_for_online_selector"] is False
    activation = report["activation_state"]
    assert activation["online_selector_enabled"] is True
    assert activation["fail_closed_fallback_policy"] == "dp_top1"
    online_manifest = report["online_runtime_manifest"]
    assert online_manifest["schema_version"] == module.ONLINE_RUNTIME_MANIFEST_SCHEMA_VERSION
    assert online_manifest["default_off"] is False
    assert online_manifest["selection_effect"] is True
    assert online_manifest["executed_output_policy"] == module.EXECUTED_OUTPUT_POLICY
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.ACTIVATION_STATE_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.ONLINE_RUNTIME_MANIFEST_JSON_NAME).is_file()


def test_candidate_index_actual_safetycost_online_selector_activation_execution_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "online_selector_activation_execution_enabled" in report["final_decision"]["failed_checks"]


def test_candidate_index_actual_safetycost_online_selector_activation_execution_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_actual_safetycost_online_selector_activation_execution_rejects_source_gap(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={
            "objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_authorized": False,
        },
    )

    report = module.build_report(**fixture)

    assert "source_activation_execution_authorized" in report["final_decision"]["failed_checks"]


def test_candidate_index_actual_safetycost_online_selector_activation_execution_rejects_runtime_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["expected_default_off_runtime_manifest_sha256"] = "0" * 64

    report = module.build_report(**fixture)

    assert "default_off_runtime_manifest_sha256" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_or_runtime_artifact_hash_mismatch"


def test_candidate_index_actual_safetycost_online_selector_activation_execution_rejects_bad_runtime_manifest(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, runtime_updates={"default_off": False})

    report = module.build_report(**fixture)

    assert "runtime_manifest_default_off" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "runtime_manifest_contract_failure"


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    runtime_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_authorized=True",
            "selector_promotion_authorized=True",
            "deployment_authorized=True",
            "online_selector_change_authorized=True",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_artifact = _write_source_static_review_artifact(
        tmp_path / "source_static_review_artifact",
        module,
        source_decision_updates=source_decision_updates,
    )
    runtime_manifest = _write_runtime_manifest(
        tmp_path / "runtime" / "default_off_manifest.json",
        module,
        runtime_updates=runtime_updates,
    )
    return {
        "source_static_review_artifact_dir": source_artifact["artifact"],
        "source_static_review_json": source_artifact["json"],
        "source_static_review_md": source_artifact["md"],
        "source_static_review_sha256s": source_artifact["sha256s"],
        "default_off_runtime_manifest_json": runtime_manifest,
        "expected_default_off_runtime_manifest_sha256": _sha256(runtime_manifest),
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_source_static_review_artifact(
    artifact: Path,
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Path]:
    review_dir = artifact / "review"
    review_json = _write_json(
        review_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_static_review_report(module, source_decision_updates=source_decision_updates),
    )
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# source static review\n")
    review_sha = _write_sha256s(review_dir / "SHA256SUMS", [review_json, review_md])
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    command = _write(artifact / "COMMAND", "python static_review.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, review_json, review_md, review_sha],
        relative_to=artifact,
    )
    return {"artifact": artifact, "json": review_json, "md": review_md, "sha256s": review_sha}


def _source_static_review_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "failure_class": None,
        "failed_checks": [],
        "check_count": module.EXPECTED_SOURCE_REVIEW_CHECK_COUNT,
        "failed_check_count": 0,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_authorized": True,
        "selector_promotion_authorized": True,
        "deployment_authorized": True,
        "online_selector_change_authorized": True,
        "online_selector_activation_execution": False,
        "safety_benefit_claim_authorized": True,
        "camp_over_dp_top1_claim_authorized": True,
    }
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {"schema_version": module.SOURCE_REVIEW_SCHEMA, "final_decision": decision}


def _write_runtime_manifest(
    path: Path,
    module,
    *,
    runtime_updates: dict[str, Any] | None,
) -> Path:
    atom = _write(path.parent / "atom_scales.json", "{}\n")
    weights = _write(path.parent / "offline_weights.npy", "weights\n")
    manifest = {
        "schema_version": module.DEFAULT_OFF_RUNTIME_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
        "source_scope": module.SOURCE_SCOPE,
        "default_off": True,
        "fail_closed": True,
        "selection_effect": False,
        "online_selector_change": False,
        "selector_mode": "static",
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "required_candidate_count": module.EXPECTED_CANDIDATE_COUNT,
        "atom_count": 9,
        "atom_schema_version": "camp_legacy_v1_9d",
        "score_expression": module.SCORE_EXPRESSION,
        "required_dp_head": module.FIXED_DP_HEAD,
        "artifacts": {
            "atom_scales": {"path": str(atom), "sha256": _sha256(atom)},
            "static_weights": {"path": str(weights), "sha256": _sha256(weights)},
        },
        "sha256": {
            "atom_scales": _sha256(atom),
            "static_weights": _sha256(weights),
            str(atom): _sha256(atom),
            str(weights): _sha256(weights),
        },
        "authorizations": {"online_selector_change_authorized": False},
    }
    if runtime_updates:
        manifest.update(runtime_updates)
    return _write_json(path, manifest)


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_sha256s(path: Path, files: list[Path], *, relative_to: Path | None = None) -> Path:
    lines = []
    for file in files:
        name = file.relative_to(relative_to).as_posix() if relative_to else file.name
        lines.append(f"{_sha256(file)}  {name}")
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
