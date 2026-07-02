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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization.py"
)
CAMP_HEAD = "fa9b64514f38b4fbc40a809b4634f7dda46d5cf2"
PLANNED_MANIFEST = "/tmp/dp_camp_v14_shadow_selector_runtime_manifest.json"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_runtime_manifest_materialization_plan",
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


def _source_review(module, *, materialization_authorized: bool = False) -> dict[str, Any]:
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA_VERSION,
        "contract_summary": {
            "runtime_schema_version": module.RUNTIME_SCHEMA_VERSION,
            "source_scope": module.SOURCE_SCOPE,
            "required_runtime_entries": ["atom_scales", "static_weights"],
            "score_expression": module.SCORE_EXPRESSION,
        },
        "final_decision": {
            "status": module.SOURCE_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "runtime_artifact_manifest_static_contract_review_passed": True,
            "runtime_artifact_manifest_materialization_plan_authorized": True,
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
            "runtime_manifest_materialized_by_this_gate": False,
        },
    }


def _source_plan(module, *, planned_path: str = PLANNED_MANIFEST) -> dict[str, Any]:
    return {
        "schema_version": module.PLAN_SCHEMA_VERSION,
        "runtime_artifact_manifest_plan": {
            "status": "plan_ready_no_runtime_manifest_materialized",
            "planned_runtime_manifest_path": planned_path,
            "runtime_schema_version": module.RUNTIME_SCHEMA_VERSION,
            "source_scope": module.SOURCE_SCOPE,
            "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
            "this_plan_is_runtime_manifest": False,
            "materialized_by_this_gate": False,
            "real_runtime_manifest_materialized": False,
            "default_off": True,
            "fail_closed": True,
            "selector_mode": "static",
            "executed_output_policy": "dp_top1",
            "selection_effect": False,
            "online_selector_change": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "required_candidate_count": module.EXPECTED_CANDIDATE_COUNT,
            "atom_count": module.EXPECTED_ATOM_COUNT,
            "atom_schema_version": module.ATOM_SCHEMA_VERSION,
            "score_expression": module.SCORE_EXPRESSION,
            "required_runtime_entries": {
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
            "required_evidence_entries": {
                "training_summary": {"path": "/tmp/training_summary.json", "sha256": "3" * 64},
                "post_static_review": {"path": "/tmp/post_review.json", "sha256": "4" * 64},
                "implementation_result": {"path": "/tmp/result.json", "sha256": "5" * 64},
                "replay_runner": {"path": "/tmp/runner.py", "sha256": "6" * 64},
            },
            "planned_runner_args": [
                "--camp_selector_mode static",
                "--num_candidates 8",
                "--camp_default_off_shadow_selector",
                "--camp_shadow_artifact_manifest <future_runtime_manifest_json>",
                "--camp_shadow_expected_atom_scales_sha256 " + "1" * 64,
                "--camp_shadow_expected_static_weights_sha256 " + "2" * 64,
            ],
        },
        "final_decision": {
            "status": "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_ready",
            "passed": True,
            "failed_checks": [],
            "runtime_artifact_manifest_materialization_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
        },
    }


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
        status = module.SOURCE_REVIEW_STATUS
        next_work = "wrong_gate" if wrong_next else module.SOURCE_AUTHORIZED_NEXT_WORK
    block = "\n".join(
        [
            "## Current V14 Runtime Artifact Manifest Materialization Plan Boundary",
            f"current_v14_status={status}",
            f"next_work_target={next_work}",
            "runtime_artifact_manifest_static_contract_review_passed=True",
            "runtime_artifact_manifest_materialization_plan_authorized=True",
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
    source_planned_path: str = PLANNED_MANIFEST,
    requested_planned_path: str = PLANNED_MANIFEST,
    wrong_next: bool = False,
    complete: bool = False,
) -> dict[str, Any]:
    audit, status = _docs(module, wrong_next=wrong_next, complete=complete)
    return {
        "runtime_artifact_manifest_static_review_json": _write_json(
            tmp_path / "static_review.json",
            _source_review(
                module,
                materialization_authorized=materialization_authorized,
            ),
        ),
        "runtime_artifact_manifest_plan_json": _write_json(
            tmp_path / "plan.json",
            _source_plan(module, planned_path=source_planned_path),
        ),
        "replay_runner_py": _write(tmp_path / "runner.py", _runner_source(module)),
        "v14_audit_md": _write(tmp_path / "audit.md", audit),
        "current_status_md": _write(tmp_path / "status.md", status),
        "planned_runtime_manifest_path": requested_planned_path,
        "output_dir": tmp_path / "materialization_plan",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_runtime_artifact_manifest_materialization_plan_ready_without_writing_manifest(
    tmp_path: Path,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)
    decision = report["final_decision"]
    plan = report["materialization_plan"]
    future = plan["future_manifest_required_content"]

    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["runtime_artifact_manifest_materialization_plan_ready"] is True
    assert (
        decision["runtime_artifact_manifest_materialization_static_contract_review_authorized"]
        is True
    )
    assert decision["runtime_artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["runtime_manifest_written_by_this_gate"] is False
    assert plan["runtime_manifest_written_by_this_gate"] is False
    assert plan["this_plan_is_runtime_manifest"] is False
    assert Path(plan["planned_runtime_manifest_path"]).exists() is False
    assert future["schema_version"] == module.RUNTIME_SCHEMA_VERSION
    assert future["source_scope"] == module.SOURCE_SCOPE
    assert future["executed_output_policy"] == "dp_top1"
    assert future["sha256"]["atom_scales"] == "1" * 64
    assert future["sha256"]["static_weights"] == "2" * 64
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_artifact_manifest_materialization_plan_is_disabled_until_enabled(
    tmp_path: Path,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.DISABLED_STATUS
    assert report["plan_checks"] == []


def test_runtime_artifact_manifest_materialization_plan_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(
        **_fixture(tmp_path, module, materialization_authorized=True)
    )

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_review_materialization_forbidden" in report["final_decision"][
        "failed_checks"
    ]
    assert (
        "source_review_runtime_artifact_manifest_materialization_authorized_false"
        in report["final_decision"]["failed_checks"]
    )


def test_runtime_artifact_manifest_materialization_plan_rejects_planned_path_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(
        **_fixture(
            tmp_path,
            module,
            source_planned_path=PLANNED_MANIFEST,
            requested_planned_path="/tmp/different_manifest.json",
        )
    )

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_plan_planned_path_matches_requested" in report["final_decision"][
        "failed_checks"
    ]


def test_runtime_artifact_manifest_materialization_plan_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, wrong_next=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "audit_latest_boundary_matches_materialization_plan_gate" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_artifact_manifest_materialization_plan_accepts_completed_boundary(
    tmp_path: Path,
) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, complete=True))

    assert report["final_decision"]["status"] == module.READY_STATUS
    assert report["final_decision"]["failed_checks"] == []


def test_runtime_artifact_manifest_materialization_plan_cli_writes_plan_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    output_dir = tmp_path / "cli_plan"
    argv = [
        "v14-runtime-manifest-materialization-plan",
        "--runtime_artifact_manifest_static_review_json",
        str(kwargs["runtime_artifact_manifest_static_review_json"]),
        "--runtime_artifact_manifest_plan_json",
        str(kwargs["runtime_artifact_manifest_plan_json"]),
        "--replay_runner_py",
        str(kwargs["replay_runner_py"]),
        "--v14_audit_md",
        str(kwargs["v14_audit_md"]),
        "--current_status_md",
        str(kwargs["current_status_md"]),
        "--planned_runtime_manifest_path",
        kwargs["planned_runtime_manifest_path"],
        "--output_dir",
        str(output_dir),
        "--current_camp_head",
        CAMP_HEAD,
        "--current_camp_origin_main",
        CAMP_HEAD,
        "--current_dp_head",
        module.FIXED_DP_HEAD,
        "--enable_v14_public_simulator_runtime_artifact_manifest_materialization_plan",
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert module.main() == 0

    payload = json.loads(
        (output_dir / "runtime_artifact_manifest_materialization_plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["schema_version"] == module.SCHEMA_VERSION
    assert payload["final_decision"]["status"] == module.READY_STATUS
    assert payload["final_decision"]["runtime_artifact_manifest_materialization_authorized"] is False
    assert payload["materialization_plan"]["this_plan_is_runtime_manifest"] is False
    assert payload["materialization_plan"]["runtime_manifest_written_by_this_gate"] is False
    assert "plan-only" in (
        output_dir / "runtime_artifact_manifest_materialization_plan.md"
    ).read_text(encoding="utf-8")
