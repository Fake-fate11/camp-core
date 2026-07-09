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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary.py"
)
CURRENT_HEAD = "174c2538a735307a611abb80b9bb6afe9ae39d6b"
SOURCE_HEAD = "7c68ea4a621311b54d81d09d2af5e7dad8c2307f"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_ROOT_SHA = "cba791fbfcac0c9bee5889eaae95deafb2560ec8361df7c2d61f3c7de2cd5206"
PACKAGE_ROOT_SHA = "f1c2a80b7efa4929e4100e09815a455af50b040403cc0e35a292ce44d11b3d15"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_"
    "174c2538a7_20260710T002424CST"
)
PLAN_ROOT_SHA = "151b22be196dcd0911857e1e43a9a5919bab5211294fc593941853ada67dbce7"
PLAN_ROOT_SHA256SUMS_SHA = "f36f3f7d547399dbac4c2d3c5f6e27d3af086f8560a44ad7233207d864cea2dc"
PLAN_JSON_SHA = "abba39d326d7da597bd972accf27ce3c2182b326b67710015f790e74448c01d3"
PLAN_MD_SHA = "b5a454f1532a4162a1388f38987d53981181b838ec17c6c438a89d4893917678"
PLAN_HEADS_SHA = "3af780b68cf14b42e0cb800ad9816a9c8aa3ff16b93a2a9c27b5ba7cc5af870c"
PLAN_COMMAND_SHA = "7b3e1ccb8e8694dd0cc7411d1a0e44f15124c6917738e40cfbdf37af2833e37a"
PLAN_COMMAND_SHELL_SHA = "b57088eab7b13cb46c33c8248d8414b41b30d3c4c841b035ad22e3a912839633"
PLAN_STDOUT_SHA = "85b32c5a3be43d9c9b1f14977e63e191f325e93fb8b8ad350cbef3d3fae3f52e"
PLAN_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PLAN_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_only"
MEAN_DELTA = -0.01762098077036227
CI95_LOW = -0.021974139797953596
CI95_HIGH = -0.01326782174277094
NON_TOP1_SELECTION_RATE = 0.903933636606904
ORACLE_GAP_CLOSED = 0.9619006786247026
SOURCE_IDS = [
    "scaleup_corpus_generation",
    "scaleup_corpus_result_review",
    "scaleup_split_execution",
    "scaleup_split_result_review",
    "scaleup_training_execution",
    "scaleup_training_result_review",
    "scaleup_paired_evaluation_execution",
    "scaleup_paired_evaluation_result_review",
]
FORBIDDEN_CLAIMS = [
    "safety claim",
    "closed-loop safety claim",
    "deployment claim",
    "broad nuScenes benchmark claim",
    "Full36/formal seeds claim",
    "DP model improvement claim",
    "trajectory generation claim",
]


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_claim_boundary_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_claim_boundary_plan_lists_limited_claim_and_forbidden_claims(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["claim_boundary_plan"]
    allowed_claim = plan["supported_claims"][0]
    prechecks = plan["preclaim_checks"]
    wording = plan["wording"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["claim_boundary_plan_only"] is True
    assert decision["claim_executed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert allowed_claim["id"] == "fixed_dp_k8_current_paired_metric_reduction"
    assert allowed_claim["scope"] == {
        "dataset_scope": "v16 nuScenes scale-up paired evaluation",
        "fixed_dp_head": DP_HEAD,
        "k_candidate_count": [8, 8],
        "primary_eval_rows": 3737,
        "records": 10000,
        "rows_scope": "calibration+holdout",
        "scenes": 50,
    }
    assert allowed_claim["metrics"] == _metrics()
    assert plan["forbidden_claims"] == FORBIDDEN_CLAIMS
    assert plan["source_artifact_count"] == 8
    assert plan["source_artifact_ids"] == SOURCE_IDS
    assert prechecks == {
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
    assert wording["mode"] == "limited/descriptive"
    assert wording["forbidden_terms"] == [
        "safe",
        "deployable",
        "beats DP generally",
        "improves TIER IV DP model",
    ]
    assert all(term.lower() not in " ".join(wording["allowed_wording"]).lower() for term in wording["forbidden_terms"])
    assert plan["next_gates"] == [
        "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_static_review_only",
        "claim decision only after static review",
        "optional 32k expansion plan if stronger evidence is requested",
    ]
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_claim_boundary_plan_rejects_nonnegative_ci_high(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, ci95_high=0.01)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "ci95_high_less_than_zero" in report["final_decision"]["failed_checks"]


def test_v16_claim_boundary_plan_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    current_v16 = status.split("## Current V15 Status", maxsplit=1)[0]

    for text in (audit, current_v16):
        assert PLAN_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_status={module.READY_STATUS}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_authorized_next_work={module.AUTHORIZED_NEXT_WORK}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_source_result_review_root_sha256={SOURCE_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_source_package_root_sha256={PACKAGE_ROOT_SHA}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_check_count=56" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_allowed_claim_id=fixed_dp_k8_current_paired_metric_reduction" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_allowed_claim_scope=10k records/50 scenes/calibration+holdout 3737 rows/fixed-DP K=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_forbidden_claims=[safety claim,closed-loop safety claim,deployment claim,broad nuScenes benchmark claim,Full36/formal seeds claim,DP model improvement claim,trajectory generation claim]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_wording_mode=limited/descriptive" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_forbidden_wording=[safe,deployable,beats DP generally,improves TIER IV DP model]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_scenes=50" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_primary_eval_rows=3737" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_better_tie_worse=[3365,359,13]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_mean_delta={MEAN_DELTA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_ci95_high={CI95_HIGH}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_non_top1_selection_rate={NON_TOP1_SELECTION_RATE}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_oracle_gap_closed={ORACLE_GAP_CLOSED}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_source_artifacts_sha_verified=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_fixed_dp_head=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_no_dp_modification=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_no_candidate_tensor_mutation=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_no_train_leakage_into_primary_eval=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_affine_simplex_preserved=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_ci95_high_less_than_zero=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_better_greater_than_worse=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_primary_eval_rows_at_least_3737=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_claim_boundary_plan_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_claim_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_promotion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_deployment_executed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_camp_head={CURRENT_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_dp_head={DP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_root_sha256={PLAN_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_root_sha256s_sha256={PLAN_ROOT_SHA256SUMS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_report_json_sha256={PLAN_JSON_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_report_md_sha256={PLAN_MD_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_heads_sha256={PLAN_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_command_sha256={PLAN_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_command_shell_sha256={PLAN_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_stdout_sha256={PLAN_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_stderr_sha256={PLAN_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_run_exit_sha256={PLAN_RUN_EXIT_SHA}" in text

    assert f"current_v16_status={module.READY_STATUS}" in current_v16
    assert f"current_v16_artifact={PLAN_ARTIFACT}" in current_v16
    assert f"next_work_target={NEXT_WORK_TARGET}" in current_v16
    latest_audit_target = audit.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert latest_audit_target == NEXT_WORK_TARGET


def _write_fixture(tmp_path: Path, module, *, ci95_high: float = CI95_HIGH) -> dict:
    source = tmp_path / "source_result_review"
    source.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    _write_json(source / module.SOURCE_JSON_NAME, _source_payload(module, ci95_high=ci95_high))
    _write(source / module.SOURCE_MD_NAME, "# Scale-up evidence package result review\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={SOURCE_HEAD}\nCAMP_ORIGIN_MAIN={SOURCE_HEAD}\nDP_HEAD={DP_HEAD}\n",
        "COMMAND": "review package\n",
        "COMMAND.shell": "review package shell\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(source / name, content)
    _write_sha_manifest(source)
    _write(source / "ROOT_SHA256SUMS", f"{SOURCE_ROOT_SHA}  SHA256SUMS\n")
    return {
        "source_result_review_artifact_dir": source,
        "source_result_review_json": source / module.SOURCE_JSON_NAME,
        "source_result_review_sha256s": source / "SHA256SUMS",
        "source_result_review_root_sha256s": source / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": DP_HEAD,
        "expected_source_root_sha256": SOURCE_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module, *, ci95_high: float) -> dict:
    metrics = _metrics(ci95_high=ci95_high)
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "camp_over_dp_claimed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "result_review_only": True,
            "safety_claimed": False,
            "training_executed": False,
        },
        "heads": {
            "camp_head": SOURCE_HEAD,
            "camp_origin_main": SOURCE_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "source_package_artifact": {
            "root_sha256": PACKAGE_ROOT_SHA,
        },
        "scaleup_evidence_package_result_review": {
            "affine_simplex_preserved": True,
            "all_source_artifact_sha_verified": True,
            "candidate_tensor_unmodified": True,
            "dp_head_fixed": module.FIXED_DP_HEAD,
            "k_candidate_count": [8, 8],
            "no_claim_boundary": {
                "descriptive_paired_metrics_only": True,
                "no_camp_over_dp_claim": True,
                "no_performance_claim": True,
                "no_promotion_or_deployment": True,
                "no_safety_claim": True,
            },
            "package_report": {
                "metrics_summary": metrics,
                "paired_eval_rows": 3737,
                "records": 10000,
                "scenes": 50,
                "split_rows": {"calibration": 2156, "holdout": 1581, "train": 6263},
            },
            "source_artifact_count": 8,
            "source_artifact_ids": SOURCE_IDS,
            "source_final_decisions_no_claim_promotion_deploy": True,
            "train_rows_in_primary_eval": 0,
        },
    }


def _metrics(*, ci95_high: float = CI95_HIGH) -> dict:
    return {
        "better_tie_worse": {"better": 3365, "tie": 359, "worse": 13},
        "ci95": {"high": ci95_high, "low": CI95_LOW},
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
