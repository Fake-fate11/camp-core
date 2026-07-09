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
    / "decide_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim.py"
)
CURRENT_HEAD = "a0b4e1a33fe7155956e48f7ae50319e03b036c97"
SOURCE_STATIC_REVIEW_HEAD = "132bfc179b085d838b9825676d493e942d9a5e6c"
SOURCE_PLAN_HEAD = "174c2538a735307a611abb80b9bb6afe9ae39d6b"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_PLAN_ROOT_SHA = "151b22be196dcd0911857e1e43a9a5919bab5211294fc593941853ada67dbce7"
STATIC_REVIEW_ROOT_SHA = "4fbf099cbe84472c26320db8f3e10c07d0291e4d7cfa4de25aaa544fa1354535"
STATIC_REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_"
    "132bfc179b_20260710T011711CST"
)
DECISION_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_"
    "a0b4e1a3_20260710T012719CST"
)
DECISION_ROOT_SHA = "7920ce632f417b56344feef054fdf5a766978603fb1ffd46c8423ab9c68ffbe7"
DECISION_ROOT_SHA256SUMS_SHA = "4668bba577a8682b0322a372f0f8d1cf5f8c9c93b30c12976f08483fdd57e40e"
DECISION_JSON_SHA = "f4c3d27267ab46da4acd23c7e5f32d9c7ae50d4aad245e9da72ef9727815816b"
DECISION_MD_SHA = "871f4a58a137d595003d8c708ad1ca7827c1d7dd050fecee4a38049b6229e882"
DECISION_HEADS_SHA = "65e0138eb1c923a0953b6e90f5c5a345a852de8e873c11f10d8fa6436ee38d79"
DECISION_COMMAND_SHA = "a9e9c2f8c2587c047d5b5a01cd9ee1c3c9e83c1a4a6f6f0b9ff0eb6646063438"
DECISION_COMMAND_SHELL_SHA = "ad45ac9e3d45df2ac9b54636f7051f26e03e50ab2dee06f6554e69dfc766ed86"
DECISION_STDOUT_SHA = "94a5718684c0ee839d16ea0644a7c41c0c531814135c95bd9762e22ae610bb8c"
DECISION_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
DECISION_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_result_review_only"
MEAN_DELTA = -0.01762098077036227
CI95_LOW = -0.021974139797953596
CI95_HIGH = -0.01326782174277094
NON_TOP1_SELECTION_RATE = 0.903933636606904
ORACLE_GAP_CLOSED = 0.9619006786247026
FORBIDDEN_CLAIMS = [
    "safety claim",
    "closed-loop safety claim",
    "deployment claim",
    "broad nuScenes benchmark claim",
    "Full36/formal seeds claim",
    "DP model improvement claim",
    "trajectory generation claim",
]
FORBIDDEN_WORDING = ["safe", "deployable", "beats DP generally", "improves TIER IV DP model"]
CLAIM_TEXT = (
    "在固定 TiER IV Diffusion Planner commit 7a1d33da、固定 K=8 candidate tensors、"
    "v16 nuScenes scale-up paired evaluation 的 3737 calibration+holdout rows 上，"
    "CAMP selector 相比 DP Top-1 降低了当前定义的 paired metric。"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_claim_decision", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_claim_decision_records_limited_descriptive_claim(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    claim = report["claim_record"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["claim_executed_by_this_gate"] is True
    assert decision["limited_descriptive_claim_authorized"] is True
    assert decision["safety_claim_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["promotion_authorized"] is False
    assert decision["online_activation_authorized"] is False
    assert claim["claim_text"] == CLAIM_TEXT
    assert claim["language"] == "zh-CN"
    assert claim["scope"] == _scope()
    assert claim["metrics"] == _metrics()
    assert claim["source_static_review_root_sha256"] == STATIC_REVIEW_ROOT_SHA
    assert claim["source_plan_root_sha256"] == SOURCE_PLAN_ROOT_SHA
    assert claim["forbidden_claims"] == FORBIDDEN_CLAIMS
    assert claim["forbidden_wording"] == FORBIDDEN_WORDING
    assert claim["non_claim_boundary"] == {
        "broad_nuscenes_benchmark_claim": False,
        "candidate_tensor_mutation": False,
        "closed_loop_safety_claim": False,
        "deployment": False,
        "dp_model_improvement_claim": False,
        "dp_modification": False,
        "full36_or_formal_seeds_claim": False,
        "online_activation": False,
        "promotion": False,
        "safety_claim": False,
        "training": False,
        "trajectory_generation_claim": False,
        "trajectory_generation_or_repair": False,
    }
    assert (fixture["output_dir"] / module.DECISION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.DECISION_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_claim_decision_rejects_forbidden_claim_wording(tmp_path: Path) -> None:
    module = _load_module()
    module.CLAIM_TEXT = "This is safe and deployable."
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "claim_text_avoids_forbidden_terms" in report["final_decision"]["failed_checks"]


def test_v16_claim_decision_rejects_wrong_eof_target(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_current_next_work" in report["final_decision"]["failed_checks"]


def test_v16_claim_decision_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    current_v16 = status.split("## Current V15 Status", maxsplit=1)[0]

    for text in (audit, current_v16):
        assert DECISION_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_status={module.READY_STATUS}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_artifact={DECISION_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_source_static_review_artifact={STATIC_REVIEW_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_source_static_review_root_sha256={STATIC_REVIEW_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_source_plan_root_sha256={SOURCE_PLAN_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_camp_head={CURRENT_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_source_static_review_camp_head={SOURCE_STATIC_REVIEW_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_source_plan_camp_head={SOURCE_PLAN_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_dp_head={DP_HEAD}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_exit=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_passed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_check_count=59" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_failed_checks=[]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_claim_text={CLAIM_TEXT}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_claim_language=zh-CN" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_limited_descriptive_claim_authorized=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_claim_executed_by_this_gate=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_safety_claim_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_closed_loop_safety_claim_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_deployment_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_promotion_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_online_activation_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_broad_nuscenes_benchmark_claim_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_full36_or_formal_seed_claim_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_dp_model_improvement_claim_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_trajectory_generation_claim_authorized=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_paired_evaluation_rerun=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_dp_modified=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_candidate_tensor_modified=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_forbidden_claims=[safety claim,closed-loop safety claim,deployment claim,broad nuScenes benchmark claim,Full36/formal seeds claim,DP model improvement claim,trajectory generation claim]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_forbidden_wording=[safe,deployable,beats DP generally,improves TIER IV DP model]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_root_sha256={DECISION_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_root_sha256s_sha256={DECISION_ROOT_SHA256SUMS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_report_json_sha256={DECISION_JSON_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_report_md_sha256={DECISION_MD_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_heads_sha256={DECISION_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_command_sha256={DECISION_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_command_shell_sha256={DECISION_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_stdout_sha256={DECISION_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_stderr_sha256={DECISION_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_run_exit_sha256={DECISION_RUN_EXIT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_authorized_next_work={module.AUTHORIZED_NEXT_WORK}" in text

    assert f"current_v16_status={module.READY_STATUS}" in current_v16
    assert f"current_v16_artifact={DECISION_ARTIFACT}" in current_v16
    assert f"next_work_target={NEXT_WORK_TARGET}" in current_v16
    latest_audit_target = audit.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert latest_audit_target == NEXT_WORK_TARGET


def _write_fixture(tmp_path: Path, module, *, next_work: str | None = None) -> dict[str, Any]:
    artifact = tmp_path / "static_review"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    _write_json(artifact / module.SOURCE_REVIEW_JSON_NAME, _source_review_payload(module))
    _write(artifact / module.SOURCE_REVIEW_MD_NAME, "# Claim boundary plan static review\n")
    for name, content in {
        "HEADS": (
            f"CAMP_HEAD={SOURCE_STATIC_REVIEW_HEAD}\n"
            f"CAMP_ORIGIN_MAIN={SOURCE_STATIC_REVIEW_HEAD}\n"
            f"DP_HEAD={module.FIXED_DP_HEAD}\n"
            f"SOURCE_CAMP_HEAD={SOURCE_PLAN_HEAD}\n"
            f"SOURCE_PLAN_ROOT_SHA256={SOURCE_PLAN_ROOT_SHA}\n"
            f"NEXT_WORK_TARGET={module.AUTHORIZED_CURRENT_WORK}\n"
        ),
        "COMMAND": "claim boundary plan static review\n",
        "COMMAND.shell": "claim boundary plan static review shell\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    _write_sha_manifest(artifact)
    _write(artifact / "ROOT_SHA256SUMS", f"{STATIC_REVIEW_ROOT_SHA}  SHA256SUMS\n")
    return {
        "source_static_review_artifact_dir": artifact,
        "source_static_review_json": artifact / module.SOURCE_REVIEW_JSON_NAME,
        "source_static_review_md": artifact / module.SOURCE_REVIEW_MD_NAME,
        "source_static_review_sha256s": artifact / "SHA256SUMS",
        "source_static_review_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": DP_HEAD,
        "expected_static_review_root_sha256": STATIC_REVIEW_ROOT_SHA,
        "enabled": True,
    }


def _source_review_payload(module) -> dict[str, Any]:
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "status": module.SOURCE_REVIEW_STATUS,
        "authorized_current_work": module.SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "claim_boundary_plan_static_review": {
            "allowed_claim_id": "fixed_dp_k8_current_paired_metric_reduction",
            "allowed_claim_scope": _scope(),
            "forbidden_claims": FORBIDDEN_CLAIMS,
            "forbidden_wording": FORBIDDEN_WORDING,
            "metrics": _metrics(),
            "next_gates": [
                module.AUTHORIZED_CURRENT_WORK,
                "claim decision only after static review",
                "optional 32k expansion plan if stronger evidence is requested",
            ],
            "preclaim_checks": {
                "affine_simplex_preserved": True,
                "better_greater_than_worse": True,
                "ci95_high_less_than_zero": True,
                "fixed_dp_head": True,
                "no_candidate_tensor_mutation": True,
                "no_dp_modification": True,
                "no_train_leakage_into_primary_eval": True,
                "primary_eval_rows_at_least_3737": True,
                "source_artifacts_sha_verified": True,
            },
            "source_plan_root_sha256": SOURCE_PLAN_ROOT_SHA,
            "wording_mode": "limited/descriptive",
        },
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "camp_over_dp_claimed": False,
            "candidate_tensor_modified": False,
            "claim_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "failed_checks": [],
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "safety_claimed": False,
            "static_review_only": True,
            "status": module.SOURCE_REVIEW_STATUS,
            "training_executed": False,
        },
        "heads": {
            "camp_head": SOURCE_STATIC_REVIEW_HEAD,
            "camp_origin_main": SOURCE_STATIC_REVIEW_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_camp_head": SOURCE_PLAN_HEAD,
        },
        "source_plan_artifact": {
            "root_sha256": SOURCE_PLAN_ROOT_SHA,
        },
    }


def _scope() -> dict[str, Any]:
    return {
        "dataset_scope": "v16 nuScenes scale-up paired evaluation",
        "fixed_dp_head": DP_HEAD,
        "k_candidate_count": [8, 8],
        "primary_eval_rows": 3737,
        "records": 10000,
        "rows_scope": "calibration+holdout",
        "scenes": 50,
    }


def _metrics() -> dict[str, Any]:
    return {
        "better_tie_worse": {"better": 3365, "tie": 359, "worse": 13},
        "ci95": {"high": CI95_HIGH, "low": CI95_LOW},
        "mean_delta": MEAN_DELTA,
        "non_top1_selection_rate": NON_TOP1_SELECTION_RATE,
        "oracle_gap_closed": ORACLE_GAP_CLOSED,
    }


def _write_sha_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.iterdir()):
        if file_path.is_file() and file_path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(file_path)}  {file_path.name}\n")
    _write(path / "SHA256SUMS", "".join(rows))


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict[str, Any]) -> None:
    _write(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
