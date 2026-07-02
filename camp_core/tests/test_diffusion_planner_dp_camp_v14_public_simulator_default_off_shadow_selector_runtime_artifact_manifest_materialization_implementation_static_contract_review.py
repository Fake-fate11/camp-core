from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract.py"
)
CAMP_HEAD = "c86ea1dd5617347e7f429c0c4a77bdbfba5094ca"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_runtime_manifest_materialization_implementation_static_review",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _source_plan(
    module,
    manifest_path: Path,
    *,
    static_review_authorized: bool = True,
    implementation_authorized: bool = False,
    materialization_authorized: bool = False,
    manifest_written: bool = False,
    stale_schema: bool = False,
    drop_step: str | None = None,
) -> dict[str, Any]:
    atom_path = "/tmp/atom_scales_dp_static.json"
    weights_path = "/tmp/offline_weights_dp_static.npy"
    runtime_schema = "stale_runtime_schema" if stale_schema else module.RUNTIME_SCHEMA_VERSION
    steps = [
        "create parent directory for the planned runtime manifest path",
        "verify DP head equals the fixed TiERIV Diffusion Planner commit",
        "verify atom_scales and static_weights files exist",
        "verify atom_scales and static_weights sha256 values match the source plan",
        "build manifest JSON with only atom_scales and static_weights entries plus hash aliases",
        "validate manifest schema, source scope, default-off fail-closed policy, K=8, atom_count=9, and affine score expression before write",
        "write a temp JSON file in the target directory and fsync before atomic replace",
        "sha256 the final manifest and emit SHA256SUMS evidence",
    ]
    steps = [step for step in steps if step != drop_step]
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "final_decision": {
            "status": module.SOURCE_PLAN_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "runtime_artifact_manifest_materialization_implementation_plan_ready": True,
            "runtime_artifact_manifest_materialization_implementation_static_contract_review_authorized": static_review_authorized,
            "runtime_artifact_manifest_materialization_implementation_authorized": implementation_authorized,
            "runtime_artifact_manifest_materialization_authorized": materialization_authorized,
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "runtime_manifest_written_by_this_gate": manifest_written,
            "runtime_manifest_materialized_by_this_gate": manifest_written,
        },
        "implementation_plan": {
            "status": "implementation_plan_ready_no_runtime_manifest_written",
            "planned_runtime_manifest_path": str(manifest_path),
            "runtime_manifest_written_by_this_gate": manifest_written,
            "runtime_manifest_materialized_by_this_gate": manifest_written,
            "runtime_execution_enabled_by_this_gate": False,
            "future_materializer_contract": {
                "write_strategy": "same-directory temp file plus atomic replace",
                "writes_exactly_one_runtime_manifest": True,
                "planned_output_path": str(manifest_path),
                "required_dp_head": module.FIXED_DP_HEAD,
                "manifest_required_content": {
                    "schema_version": runtime_schema,
                    "source_scope": module.SOURCE_SCOPE,
                    "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
                    "default_off": True,
                    "fail_closed": True,
                    "selection_effect": False,
                    "online_selector_change": False,
                    "selector_mode": "static",
                    "candidate_operation": "fixed DP candidate reranking only",
                    "executed_output_policy": "dp_top1",
                    "required_candidate_count": module.EXPECTED_CANDIDATE_COUNT,
                    "atom_count": module.EXPECTED_ATOM_COUNT,
                    "atom_schema_version": module.ATOM_SCHEMA_VERSION,
                    "score_expression": module.SCORE_EXPRESSION,
                    "artifacts": {
                        "atom_scales": {
                            "logical_name": "atom_scales",
                            "path": atom_path,
                            "sha256": "1" * 64,
                        },
                        "static_weights": {
                            "logical_name": "static_weights",
                            "path": weights_path,
                            "sha256": "2" * 64,
                        },
                    },
                    "sha256": {
                        "atom_scales": "1" * 64,
                        atom_path: "1" * 64,
                        "static_weights": "2" * 64,
                        weights_path: "2" * 64,
                    },
                },
                "steps": steps,
            },
        },
    }


def _plan_script_source(module) -> str:
    return f'''
SCHEMA_VERSION = "{module.SOURCE_PLAN_SCHEMA_VERSION}"
AUTHORIZED_NEXT_WORK = "{module.SOURCE_AUTHORIZED_NEXT_WORK}"
RUNTIME_SCHEMA_VERSION = "{module.RUNTIME_SCHEMA_VERSION}"
SOURCE_SCOPE = "{module.SOURCE_SCOPE}"
"write_strategy": "same-directory temp file plus atomic replace"
"writes_exactly_one_runtime_manifest": True
"runtime_manifest_written_by_this_gate": False
"runtime_manifest_materialized_by_this_gate": False
"runtime_artifact_manifest_materialization_implementation_authorized": False
"runtime_artifact_manifest_materialization_authorized": False
{module.SCORE_EXPRESSION}
'''


def _plan_test_source() -> str:
    return """
def test_runtime_artifact_manifest_materialization_implementation_plan_ready(): pass
def test_runtime_artifact_manifest_materialization_implementation_plan_disabled(): pass
def test_runtime_artifact_manifest_materialization_implementation_plan_rejects_review_authorization_leak(): pass
def test_runtime_artifact_manifest_materialization_implementation_plan_rejects_written_manifest(): pass
def test_runtime_artifact_manifest_materialization_implementation_plan_rejects_stale_schema(): pass
def test_runtime_artifact_manifest_materialization_implementation_plan_rejects_wrong_eof(): pass
"""


def _docs(module, *, complete: bool = False, wrong_next: bool = False) -> tuple[str, str]:
    if complete:
        status = module.READY_STATUS
        next_work = module.AUTHORIZED_NEXT_WORK
    else:
        status = module.SOURCE_PLAN_STATUS
        next_work = "wrong_gate" if wrong_next else module.SOURCE_AUTHORIZED_NEXT_WORK
    block = "\n".join(
        [
            "## Current V14 Runtime Manifest Materialization Implementation Static Review Boundary",
            f"current_v14_status={status}",
            f"next_work_target={next_work}",
            "runtime_artifact_manifest_materialization_implementation_plan_ready=True",
            "runtime_artifact_manifest_materialization_implementation_static_contract_review_authorized=True",
            "runtime_artifact_manifest_materialization_implementation_authorized=False",
            "runtime_artifact_manifest_materialization_authorized=False",
            "default_off_shadow_selector_runtime_execution_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    return block, block


def _fixture(
    tmp_path: Path,
    module,
    *,
    static_review_authorized: bool = True,
    implementation_authorized: bool = False,
    materialization_authorized: bool = False,
    manifest_written: bool = False,
    stale_schema: bool = False,
    drop_step: str | None = None,
    wrong_next: bool = False,
    complete: bool = False,
) -> dict[str, Any]:
    manifest_path = tmp_path / "planned_runtime" / "manifest.json"
    audit, status = _docs(module, wrong_next=wrong_next, complete=complete)
    return {
        "runtime_artifact_manifest_materialization_implementation_plan_json": _write_json(
            tmp_path / "implementation_plan.json",
            _source_plan(
                module,
                manifest_path,
                static_review_authorized=static_review_authorized,
                implementation_authorized=implementation_authorized,
                materialization_authorized=materialization_authorized,
                manifest_written=manifest_written,
                stale_schema=stale_schema,
                drop_step=drop_step,
            ),
        ),
        "runtime_artifact_manifest_materialization_implementation_plan_script_py": _write(
            tmp_path / "implementation_plan.py",
            _plan_script_source(module),
        ),
        "runtime_artifact_manifest_materialization_implementation_plan_test_py": _write(
            tmp_path / "test_implementation_plan.py",
            _plan_test_source(),
        ),
        "v14_audit_md": _write(tmp_path / "audit.md", audit),
        "current_status_md": _write(tmp_path / "status.md", status),
        "output_dir": tmp_path / "review",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_runtime_artifact_manifest_materialization_implementation_static_review_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)
    decision = report["final_decision"]

    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert (
        decision[
            "runtime_artifact_manifest_materialization_implementation_static_contract_review_passed"
        ]
        is True
    )
    assert decision["runtime_artifact_manifest_materialization_implementation_authorized"] is True
    assert decision["runtime_artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert report["future_implementation_contract"]["future_materializer_script"] == module.FUTURE_MATERIALIZER
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_artifact_manifest_materialization_implementation_static_review_disabled(
    tmp_path: Path,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.DISABLED_STATUS
    assert report["review_checks"] == []


def test_runtime_artifact_manifest_materialization_implementation_static_review_rejects_gate_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(
        **_fixture(tmp_path, module, static_review_authorized=False)
    )

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_plan_static_review_authorized" in report["final_decision"][
        "failed_checks"
    ]


def test_runtime_artifact_manifest_materialization_implementation_static_review_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(
        **_fixture(
            tmp_path,
            module,
            implementation_authorized=True,
            materialization_authorized=True,
        )
    )

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_plan_implementation_not_yet_authorized" in report["final_decision"][
        "failed_checks"
    ]
    assert "source_plan_materialization_forbidden" in report["final_decision"][
        "failed_checks"
    ]


def test_runtime_artifact_manifest_materialization_implementation_static_review_rejects_written_manifest(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(
        **_fixture(tmp_path, module, manifest_written=True)
    )

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_plan_manifest_not_written_decision" in report["final_decision"][
        "failed_checks"
    ]
    assert "source_plan_runtime_manifest_not_written" in report["final_decision"][
        "failed_checks"
    ]


def test_runtime_artifact_manifest_materialization_implementation_static_review_rejects_schema_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, stale_schema=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "future_runtime_schema" in report["final_decision"]["failed_checks"]


def test_runtime_artifact_manifest_materialization_implementation_static_review_rejects_missing_step(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(
        **_fixture(
            tmp_path,
            module,
            drop_step="write a temp JSON file in the target directory and fsync before atomic replace",
        )
    )

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "future_step_atomic_write" in report["final_decision"]["failed_checks"]


def test_runtime_artifact_manifest_materialization_implementation_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, wrong_next=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert (
        "audit_latest_boundary_matches_materialization_implementation_static_review_gate"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_artifact_manifest_materialization_implementation_static_review_accepts_completed_boundary(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, complete=True))

    assert report["final_decision"]["status"] == module.READY_STATUS
    assert report["final_decision"]["failed_checks"] == []


def test_runtime_artifact_manifest_materialization_implementation_static_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    output_dir = tmp_path / "cli_review"
    argv = [
        "v14-runtime-manifest-materialization-implementation-static-review",
        "--runtime_artifact_manifest_materialization_implementation_plan_json",
        str(kwargs["runtime_artifact_manifest_materialization_implementation_plan_json"]),
        "--runtime_artifact_manifest_materialization_implementation_plan_script_py",
        str(kwargs["runtime_artifact_manifest_materialization_implementation_plan_script_py"]),
        "--runtime_artifact_manifest_materialization_implementation_plan_test_py",
        str(kwargs["runtime_artifact_manifest_materialization_implementation_plan_test_py"]),
        "--v14_audit_md",
        str(kwargs["v14_audit_md"]),
        "--current_status_md",
        str(kwargs["current_status_md"]),
        "--output_dir",
        str(output_dir),
        "--current_camp_head",
        CAMP_HEAD,
        "--current_camp_origin_main",
        CAMP_HEAD,
        "--current_dp_head",
        module.FIXED_DP_HEAD,
        "--enable_v14_public_simulator_runtime_artifact_manifest_materialization_implementation_static_contract_review",
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert module.main() == 0

    payload = json.loads(
        (
            output_dir
            / "runtime_artifact_manifest_materialization_implementation_static_contract_review.json"
        ).read_text(encoding="utf-8")
    )
    markdown = (
        output_dir
        / "runtime_artifact_manifest_materialization_implementation_static_contract_review.md"
    ).read_text(encoding="utf-8")
    assert payload["schema_version"] == module.SCHEMA_VERSION
    assert payload["final_decision"]["status"] == module.READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert payload["final_decision"]["runtime_artifact_manifest_materialization_authorized"] is False
    assert "static only" in markdown
