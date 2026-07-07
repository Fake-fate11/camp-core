from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_preflight.py"
)
HEAD = "f36994cf561cf147b6723b156658b810637a7fcc"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_broader_nonformal_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_broader_nonformal_preflight_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["full36_used"] is False
    assert decision["formal_seed_11_12_13_used"] is False
    assert report["paired_protocol"]["scenario_buckets"] == list(module.SCENARIO_BUCKETS)
    assert "timing.json" in report["artifact_layout"]
    assert "timing.md" in report["artifact_layout"]
    assert (fixture["output_dir"] / module.REPORT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REPORT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v15_broader_nonformal_preflight_rejects_formal_seed(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["matrix"] = dict(module.NONFORMAL_MATRIX)
    fixture["matrix"]["holdout_seeds"] = (11,)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "matrix_no_formal_seeds" in report["final_decision"]["failed_checks"]


def test_v15_broader_nonformal_preflight_rejects_dp_drift(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["current_dp_head"] = "0" * 40

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_v15_broader_nonformal_preflight_rejects_missing_v15_status(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["current_status_md"].write_text("v14 is sealed evidence\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "current_status_mentions_v15" in report["final_decision"]["failed_checks"]


def test_v15_iteration_audit_and_current_status_are_switched() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v15_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status_text = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    assert "v15_broader_nonformal_evidence_expansion_plan_preflight" in audit_text
    assert f"v15_broader_nonformal_evidence_expansion_plan_preflight_status={module.READY_STATUS}" in audit_text
    assert (
        "v15_broader_nonformal_evidence_expansion_plan_preflight_authorized_next_work="
        f"{module.AUTHORIZED_NEXT_WORK}"
        in audit_text
    )
    assert "docs/diffusion_planner_v15_iteration_audit.md" in status_text
    assert "current_v15_status=" in status_text
    assert "next_work_target=" in status_text
    assert "v14 is sealed evidence" in status_text


def _write_fixture(tmp_path: Path, module) -> dict:
    docs = tmp_path / "docs"
    docs.mkdir()
    v14_audit = docs / "diffusion_planner_v14_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    v14_audit.write_text(
        "\n".join(
            [
                "auditable_integration_complete=True",
                "next_work_target=no_further_action_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation_auditable_integration_complete",
                "CAMP selector over fixed Diffusion Planner candidate tensor",
                "dp_modification=False",
                "candidate_tensor_modification=False",
                "",
            ]
        ),
        encoding="utf-8",
    )
    current_status.write_text(
        "\n".join(
            [
                "docs/diffusion_planner_v15_iteration_audit.md",
                "v14 is sealed evidence",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }
