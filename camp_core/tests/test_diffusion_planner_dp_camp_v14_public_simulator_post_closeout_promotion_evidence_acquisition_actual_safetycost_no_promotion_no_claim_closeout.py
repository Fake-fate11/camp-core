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
    / "record_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_actual_safetycost_no_promotion_no_claim_closeout.py"
)
CURRENT_HEAD = "e" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_no_promotion_no_claim_closeout",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_actual_safetycost_no_promotion_no_claim_closeout_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["no_further_action_recommended"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["closeout_summary"]["closeout_reason"] == "actual_safetycost_shadow_selected_not_better_than_dp_top1"
    assert (fixture["output_dir"] / module.RECORD_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.RECORD_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_actual_safetycost_no_promotion_no_claim_closeout_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "closeout_record_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_actual_safetycost_no_promotion_closeout_authorization_missing"
    )


def test_actual_safetycost_no_promotion_no_claim_closeout_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_actual_safetycost_no_promotion_no_claim_closeout_rejects_supported_claim(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, claim_supported=True)

    report = module.build_report(**fixture)

    assert "source_review_safety_benefit_claim_supported" in report["final_decision"]["failed_checks"]
    assert "source_review_no_promotion_closeout_recommended" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False


def test_actual_safetycost_no_promotion_no_claim_closeout_accepts_lowercase_dp_head(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, lowercase_heads=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert report["heads"]["source_artifact_dp_head"] == module.FIXED_DP_HEAD


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    claim_supported: bool = False,
    lowercase_heads: bool = False,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source_artifact = tmp_path / "source_result_review"
    review_dir = source_artifact / "review"
    source_json = _write_json(
        review_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_result_review_report(module, claim_supported=claim_supported),
    )
    source_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# source result review\n")
    source_sha = _write_sha256s(review_dir / "SHA256SUMS", [source_json, source_md])
    head_key = "dp_head" if lowercase_heads else "DP_HEAD"
    _write(
        source_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={CURRENT_HEAD}",
                f"CAMP_ORIGIN_MAIN={CURRENT_HEAD}",
                f"{head_key}={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    _write(source_artifact / "COMMAND", "result review\n")
    _write(source_artifact / "stdout", "{}\n")
    _write(source_artifact / "stderr", "")
    _write(source_artifact / "run.exit", "0\n")
    _write_sha256s(
        source_artifact / "SHA256SUMS",
        [
            source_json,
            source_md,
            source_sha,
            source_artifact / "HEADS",
            source_artifact / "COMMAND",
            source_artifact / "stdout",
            source_artifact / "stderr",
            source_artifact / "run.exit",
        ],
        root=source_artifact,
    )

    return {
        "source_result_review_artifact_dir": source_artifact,
        "source_result_review_json": source_json,
        "source_result_review_md": source_md,
        "source_result_review_sha256s": source_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_result_review_report(module, *, claim_supported: bool) -> dict[str, Any]:
    better = 31 if claim_supported else 1
    worse = 1 if claim_supported else 31
    delta_mean = -0.9 if claim_supported else 0.9501537269208384
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "no_promotion_closeout_recommended": not claim_supported,
        "safety_benefit_claim_supported": claim_supported,
        "camp_over_dp_top1_claim_supported": claim_supported,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "final_decision": decision,
        "source_execution_summary": {
            "runtime_record_count": 3200,
            "top1_summary_count": 32,
            "shadow_summary_count": 32,
            "delta_count": 32,
            "delta_mean": delta_mean,
            "better_records": better,
            "worse_records": worse,
        },
        "actual_safetycost_claim_rule_summary": {
            "claim_rule": "shadow_minus_top1 SafetyCost mean < 0, CI95 high < 0, better>worse, no-go failed count == 0",
            "delta_mean": delta_mean,
            "delta_ci95_low": -1.2 if claim_supported else 0.7157895850136042,
            "delta_ci95_high": -0.2 if claim_supported else 1.171673912524327,
            "better_records": better,
            "worse_records": worse,
            "no_go_failed_count": 0,
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_sha256s(path: Path, files: list[Path], root: Path | None = None) -> Path:
    lines = []
    for file in files:
        name = file.name if root is None else file.relative_to(root).as_posix()
        lines.append(f"{_sha256(file)}  {name}")
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
