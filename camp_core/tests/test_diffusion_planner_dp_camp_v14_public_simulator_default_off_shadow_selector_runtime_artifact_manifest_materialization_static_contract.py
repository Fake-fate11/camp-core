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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract.py"
)
CAMP_HEAD = "2b2c2ee5d1c715dbecec9dda6406e2d2a25f46e9"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_runtime_manifest_materialization_static_review",
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
    tmp_path: Path,
    *,
    materialization_authorized: bool = False,
    runtime_manifest_written: bool = False,
    stale_schema: bool = False,
) -> dict[str, Any]:
    manifest_path = tmp_path / "planned_runtime" / "manifest.json"
    runtime_schema = (
        "dp_camp_v13_default_off_shadow_selector_runtime_v1"
        if stale_schema
        else module.RUNTIME_SCHEMA_VERSION
    )
    return {
        "schema_version": module.PLAN_SCHEMA_VERSION,
        "final_decision": {
            "status": module.SOURCE_PLAN_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "runtime_artifact_manifest_materialization_plan_ready": True,
            "runtime_artifact_manifest_materialization_static_contract_review_authorized": True,
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
            "runtime_manifest_written_by_this_gate": runtime_manifest_written,
            "runtime_manifest_materialized_by_this_gate": runtime_manifest_written,
        },
        "materialization_plan": {
            "status": "plan_ready_no_runtime_manifest_written",
            "planned_runtime_manifest_path": str(manifest_path),
            "source_planned_runtime_manifest_path": str(manifest_path),
            "this_plan_is_runtime_manifest": False,
            "runtime_manifest_written_by_this_gate": runtime_manifest_written,
            "runtime_manifest_materialized_by_this_gate": runtime_manifest_written,
            "runtime_execution_enabled_by_this_gate": False,
            "future_manifest_required_content": {
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
                "required_dp_head": module.FIXED_DP_HEAD,
                "dp_head_at_plan": module.FIXED_DP_HEAD,
                "artifacts": {
                    "atom_scales": {
                        "logical_name": "atom_scales",
                        "path": "/tmp/atom_scales_dp_static.json",
                        "sha256": "1" * 64,
                    },
                    "static_weights": {
                        "logical_name": "static_weights",
                        "path": "/tmp/offline_weights_dp_static.npy",
                        "sha256": "2" * 64,
                    },
                },
                "sha256": {
                    "atom_scales": "1" * 64,
                    "atom_scales_dp_static.json": "1" * 64,
                    "/tmp/atom_scales_dp_static.json": "1" * 64,
                    "static_weights": "2" * 64,
                    "offline_weights_dp_static.npy": "2" * 64,
                    "/tmp/offline_weights_dp_static.npy": "2" * 64,
                },
            },
            "future_runtime_invocation_template": [
                "--camp_shadow_artifact_manifest /tmp/manifest.json",
                "--camp_shadow_expected_atom_scales_sha256 " + "1" * 64,
                "--camp_shadow_expected_static_weights_sha256 " + "2" * 64,
            ],
        },
    }


def _plan_script_source(module) -> str:
    return f'''
SCHEMA_VERSION = "{module.PLAN_SCHEMA_VERSION}"
RUNTIME_SCHEMA_VERSION = "{module.RUNTIME_SCHEMA_VERSION}"
SOURCE_SCOPE = "{module.SOURCE_SCOPE}"
AUTHORIZED_NEXT_WORK = "{module.SOURCE_AUTHORIZED_NEXT_WORK}"
"runtime_manifest_written_by_this_gate": False
"runtime_manifest_materialized_by_this_gate": False
"artifacts": {{
"atom_scales"
"static_weights"
"{module.SCORE_EXPRESSION}"
'''


def _plan_test_source() -> str:
    return """
def test_runtime_artifact_manifest_materialization_plan_ready_without_writing_manifest(): pass
def test_runtime_artifact_manifest_materialization_plan_is_disabled_until_enabled(): pass
def test_runtime_artifact_manifest_materialization_plan_rejects_authorization_leak(): pass
def test_runtime_artifact_manifest_materialization_plan_rejects_planned_path_drift(): pass
def test_runtime_artifact_manifest_materialization_plan_rejects_wrong_eof(): pass
"""


def _runner_source(module) -> str:
    return f'''
DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION = "{module.RUNTIME_SCHEMA_VERSION}"
DEFAULT_OFF_SHADOW_SELECTOR_SOURCE_SCOPE = "{module.SOURCE_SCOPE}"
def _load_shadow_artifact_manifest(path): pass
def _manifest_expected_sha256(manifest, logical_name): pass
logical_name="atom_scales"
logical_name="static_weights"
hash_mismatch
selected_index = 0 if default_off_shadow_selector else baseline_selected_index
record = {{"score_expression": "{module.SCORE_EXPRESSION}"}}
'''


def _docs(module, *, complete: bool = False, wrong_next: bool = False) -> tuple[str, str]:
    if complete:
        status = module.READY_STATUS
        next_work = module.AUTHORIZED_NEXT_WORK
    else:
        status = module.SOURCE_PLAN_STATUS
        next_work = "wrong_gate" if wrong_next else module.SOURCE_AUTHORIZED_NEXT_WORK
    block = "\n".join(
        [
            "## Current V14 Runtime Artifact Manifest Materialization Static Review Boundary",
            f"current_v14_status={status}",
            f"next_work_target={next_work}",
            "runtime_artifact_manifest_materialization_plan_ready=True",
            "runtime_artifact_manifest_materialization_static_contract_review_authorized=True",
            "runtime_artifact_manifest_materialization_authorized=False",
            "default_off_shadow_selector_runtime_execution_authorized=False",
            "training_execution_authorized=False",
            "replay_execution_authorized=False",
            "candidate_generation_authorized=False",
            "dp_modification_authorized=False",
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
    materialization_authorized: bool = False,
    runtime_manifest_written: bool = False,
    stale_schema: bool = False,
    wrong_next: bool = False,
    complete: bool = False,
) -> dict[str, Any]:
    audit, status = _docs(module, wrong_next=wrong_next, complete=complete)
    return {
        "runtime_artifact_manifest_materialization_plan_json": _write_json(
            tmp_path / "materialization_plan.json",
            _source_plan(
                module,
                tmp_path,
                materialization_authorized=materialization_authorized,
                runtime_manifest_written=runtime_manifest_written,
                stale_schema=stale_schema,
            ),
        ),
        "runtime_artifact_manifest_materialization_plan_script_py": _write(
            tmp_path / "plan_script.py",
            _plan_script_source(module),
        ),
        "runtime_artifact_manifest_materialization_plan_test_py": _write(
            tmp_path / "test_plan.py",
            _plan_test_source(),
        ),
        "replay_runner_py": _write(tmp_path / "runner.py", _runner_source(module)),
        "v14_audit_md": _write(tmp_path / "audit.md", audit),
        "current_status_md": _write(tmp_path / "status.md", status),
        "output_dir": tmp_path / "review",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_runtime_artifact_manifest_materialization_static_review_passes(
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
        decision["runtime_artifact_manifest_materialization_static_contract_review_passed"]
        is True
    )
    assert (
        decision["runtime_artifact_manifest_materialization_implementation_plan_authorized"]
        is True
    )
    assert decision["runtime_artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert report["contract_summary"]["required_runtime_entries"] == [
        "atom_scales",
        "static_weights",
    ]
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_artifact_manifest_materialization_static_review_is_disabled(
    tmp_path: Path,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.DISABLED_STATUS
    assert report["review_checks"] == []


def test_runtime_artifact_manifest_materialization_static_review_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(
        **_fixture(tmp_path, module, materialization_authorized=True)
    )

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_plan_materialization_forbidden" in report["final_decision"][
        "failed_checks"
    ]
    assert (
        "source_plan_runtime_artifact_manifest_materialization_authorized_false"
        in report["final_decision"]["failed_checks"]
    )


def test_runtime_artifact_manifest_materialization_static_review_rejects_written_manifest(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(
        **_fixture(tmp_path, module, runtime_manifest_written=True)
    )

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_plan_runtime_manifest_not_written" in report["final_decision"][
        "failed_checks"
    ]
    assert "source_plan_runtime_manifest_written_false" in report["final_decision"][
        "failed_checks"
    ]


def test_runtime_artifact_manifest_materialization_static_review_rejects_stale_schema(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, stale_schema=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "future_runtime_schema" in report["final_decision"]["failed_checks"]


def test_runtime_artifact_manifest_materialization_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, wrong_next=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert (
        "audit_latest_boundary_matches_materialization_static_review_gate"
        in report["final_decision"]["failed_checks"]
    )
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_artifact_manifest_materialization_static_review_accepts_completed_boundary(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, complete=True))

    assert report["final_decision"]["status"] == module.READY_STATUS
    assert report["final_decision"]["failed_checks"] == []


def test_runtime_artifact_manifest_materialization_static_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    output_dir = tmp_path / "cli_review"
    argv = [
        "v14-runtime-manifest-materialization-static-review",
        "--runtime_artifact_manifest_materialization_plan_json",
        str(kwargs["runtime_artifact_manifest_materialization_plan_json"]),
        "--runtime_artifact_manifest_materialization_plan_script_py",
        str(kwargs["runtime_artifact_manifest_materialization_plan_script_py"]),
        "--runtime_artifact_manifest_materialization_plan_test_py",
        str(kwargs["runtime_artifact_manifest_materialization_plan_test_py"]),
        "--replay_runner_py",
        str(kwargs["replay_runner_py"]),
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
        "--enable_v14_public_simulator_runtime_artifact_manifest_materialization_static_contract_review",
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert module.main() == 0

    payload = json.loads(
        (
            output_dir
            / "runtime_artifact_manifest_materialization_static_contract_review.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["schema_version"] == module.SCHEMA_VERSION
    assert payload["final_decision"]["status"] == module.READY_STATUS
    assert (
        payload["final_decision"][
            "runtime_artifact_manifest_materialization_implementation_plan_authorized"
        ]
        is True
    )
    assert (
        payload["final_decision"]["runtime_artifact_manifest_materialization_authorized"]
        is False
    )
    assert "static only" in (
        output_dir
        / "runtime_artifact_manifest_materialization_static_contract_review.md"
    ).read_text(encoding="utf-8")
