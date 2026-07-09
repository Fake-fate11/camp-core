from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_contract.py"
)
CURRENT_HEAD = "132bfc179b085d838b9825676d493e942d9a5e6c"
SOURCE_PLAN_HEAD = "174c2538a735307a611abb80b9bb6afe9ae39d6b"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_ROOT_SHA = "151b22be196dcd0911857e1e43a9a5919bab5211294fc593941853ada67dbce7"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_"
    "174c2538a7_20260710T002424CST"
)
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_"
    "132bfc179b_20260710T011711CST"
)
REVIEW_ROOT_SHA = "4fbf099cbe84472c26320db8f3e10c07d0291e4d7cfa4de25aaa544fa1354535"
REVIEW_ROOT_SHA256SUMS_SHA = "0cdfd477841dcf81d0fd2ad5b928aa9fb05a43365e5296d7ffa6732f62189438"
REVIEW_JSON_SHA = "4ebc127a58c796928686dd96e9434d6a708442332aaf8dd63c7a5f2d8a317203"
REVIEW_MD_SHA = "64e468087810698eeb9ef3e663ef285a2b22bdcd8c158a9f8bf4101182f34d74"
REVIEW_HEADS_SHA = "22927665033c59e9d453c98e950a43383bef3be3f1187de40f2fb7765dd496d3"
REVIEW_COMMAND_SHA = "8d52720ca51449f5cac40191f4b42472c8626318d800fb072a5c11d441fc7241"
REVIEW_COMMAND_SHELL_SHA = "4de27b090297c26b25bdf026b45f04a34b04991e04d2279b9d646edd66c1752a"
REVIEW_STDOUT_SHA = "091a562a774bb109a474bcdfd2f2c9caeeaa9648317156799b1599097323ac44"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_claim_decision_only"
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


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_claim_boundary_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_claim_boundary_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["claim_boundary_plan_static_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["claim_executed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert review["allowed_claim_id"] == "fixed_dp_k8_current_paired_metric_reduction"
    assert review["allowed_claim_scope"] == {
        "dataset_scope": "v16 nuScenes scale-up paired evaluation",
        "fixed_dp_head": DP_HEAD,
        "k_candidate_count": [8, 8],
        "primary_eval_rows": 3737,
        "records": 10000,
        "rows_scope": "calibration+holdout",
        "scenes": 50,
    }
    assert review["metrics"] == _metrics()
    assert review["forbidden_claims"] == FORBIDDEN_CLAIMS
    assert review["forbidden_wording"] == FORBIDDEN_WORDING
    assert review["wording_mode"] == "limited/descriptive"
    assert review["preclaim_checks"] == {
        "affine_simplex_preserved": True,
        "better_greater_than_worse": True,
        "ci95_high_less_than_zero": True,
        "fixed_dp_head": True,
        "no_candidate_tensor_mutation": True,
        "no_dp_modification": True,
        "no_train_leakage_into_primary_eval": True,
        "primary_eval_rows_at_least_3737": True,
        "source_artifacts_sha_verified": True,
    }
    assert review["next_gates"] == [
        module.AUTHORIZED_NEXT_WORK,
        "claim decision only after static review",
        "optional 32k expansion plan if stronger evidence is requested",
    ]
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_claim_boundary_plan_static_review_rejects_forbidden_allowed_wording(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, allowed_wording=["This is safe to deploy."])

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "allowed_wording_avoids_forbidden_terms" in report["final_decision"]["failed_checks"]


def test_v16_claim_boundary_plan_static_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    current_v16 = status.split("## Current V15 Status", maxsplit=1)[0]

    for text in (audit, current_v16):
        assert REVIEW_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_status={module.READY_STATUS}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_artifact={REVIEW_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_source_plan_artifact={PLAN_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_source_plan_root_sha256={PLAN_ROOT_SHA}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_exit=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_passed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_check_count=81" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_allowed_claim_id=fixed_dp_k8_current_paired_metric_reduction" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_allowed_claim_scope=10k records/50 scenes/calibration+holdout 3737 rows/fixed-DP K=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_forbidden_claims=[safety claim,closed-loop safety claim,deployment claim,broad nuScenes benchmark claim,Full36/formal seeds claim,DP model improvement claim,trajectory generation claim]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_wording_mode=limited/descriptive" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_forbidden_wording=[safe,deployable,beats DP generally,improves TIER IV DP model]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_source_artifacts_sha_verified=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_fixed_dp_head=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_no_dp_modification=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_no_candidate_tensor_mutation=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_no_train_leakage_into_primary_eval=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_affine_simplex_preserved=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_ci95_high_less_than_zero=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_better_greater_than_worse=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_primary_eval_rows_at_least_3737=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_static_review_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_claim_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_promotion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_deployment_executed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_camp_head={CURRENT_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_source_camp_head={SOURCE_PLAN_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_dp_head={DP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_root_sha256={REVIEW_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_root_sha256s_sha256={REVIEW_ROOT_SHA256SUMS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_report_json_sha256={REVIEW_JSON_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_report_md_sha256={REVIEW_MD_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_heads_sha256={REVIEW_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_command_sha256={REVIEW_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_command_shell_sha256={REVIEW_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_stdout_sha256={REVIEW_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_stderr_sha256={REVIEW_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_run_exit_sha256={REVIEW_RUN_EXIT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_authorized_next_work={module.AUTHORIZED_NEXT_WORK}" in text

    assert f"current_v16_status={module.READY_STATUS}" in current_v16
    assert f"current_v16_artifact={REVIEW_ARTIFACT}" in current_v16
    assert f"next_work_target={NEXT_WORK_TARGET}" in current_v16


def _write_fixture(tmp_path: Path, module, *, allowed_wording: list[str] | None = None) -> dict:
    artifact = tmp_path / "claim_boundary_plan"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.PLAN_MODULE.READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    _write_json(artifact / module.PLAN_MODULE.PLAN_JSON_NAME, _source_payload(module, allowed_wording=allowed_wording))
    _write(artifact / module.PLAN_MODULE.PLAN_MD_NAME, "# Claim boundary plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={SOURCE_PLAN_HEAD}\nCAMP_ORIGIN_MAIN={SOURCE_PLAN_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "claim boundary plan\n",
        "COMMAND.shell": "claim boundary plan shell\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    _write_sha_manifest(artifact)
    _write(artifact / "ROOT_SHA256SUMS", f"{PLAN_ROOT_SHA}  SHA256SUMS\n")
    return {
        "source_plan_artifact_dir": artifact,
        "source_plan_json": artifact / module.PLAN_MODULE.PLAN_JSON_NAME,
        "source_plan_md": artifact / module.PLAN_MODULE.PLAN_MD_NAME,
        "source_plan_sha256s": artifact / "SHA256SUMS",
        "source_plan_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module, *, allowed_wording: list[str] | None) -> dict:
    wording = allowed_wording or [
        "In the v16 nuScenes scale-up paired evaluation on fixed-DP K=8 candidate tensors, the CAMP selector reduced the current paired metric over 3737 calibration+holdout rows.",
        "This is limited descriptive evidence for the current paired metric within the 10k-record / 50-scene v16 scale-up scope.",
    ]
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": module.PLAN_MODULE.READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "camp_over_dp_claimed": False,
            "candidate_tensor_modified": False,
            "claim_boundary_plan_only": True,
            "claim_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "limited_descriptive_claim_planned": True,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "safety_claimed": False,
            "training_executed": False,
        },
        "heads": {
            "camp_head": SOURCE_PLAN_HEAD,
            "camp_origin_main": SOURCE_PLAN_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "claim_boundary_plan": {
            "forbidden_claims": FORBIDDEN_CLAIMS,
            "forbidden_work": [
                "direct_claim",
                "promotion",
                "deployment",
                "new_training",
                "new_paired_evaluation",
                "dp_modification",
                "candidate_tensor_mutation",
            ],
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
            "supported_claims": [
                {
                    "id": "fixed_dp_k8_current_paired_metric_reduction",
                    "metrics": _metrics(),
                    "scope": {
                        "dataset_scope": "v16 nuScenes scale-up paired evaluation",
                        "fixed_dp_head": module.FIXED_DP_HEAD,
                        "k_candidate_count": [8, 8],
                        "primary_eval_rows": 3737,
                        "records": 10000,
                        "rows_scope": "calibration+holdout",
                        "scenes": 50,
                    },
                    "wording": "On fixed-DP K=8 candidate tensors, the CAMP selector reduced the current paired metric in the v16 nuScenes scale-up paired evaluation.",
                }
            ],
            "wording": {
                "allowed_wording": wording,
                "forbidden_terms": FORBIDDEN_WORDING,
                "mode": "limited/descriptive",
            },
        },
    }


def _metrics() -> dict:
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


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
