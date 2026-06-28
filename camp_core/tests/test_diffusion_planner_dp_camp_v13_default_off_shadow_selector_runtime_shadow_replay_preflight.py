import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CAMP_HEAD = "0be256a17e054fafcc2037dde214982dd3de7409"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _runner_source(*, missing_shadow_flag: bool = False) -> str:
    source = """
parser.add_argument(
        "--camp_shadow_artifact_manifest"
)
def _load_shadow_artifact_manifest(path): pass
def _manifest_expected_sha256(manifest, logical_name, path): pass
{"executed_output_policy": "dp_top1"}
shadow_selected_index
--camp_default_off_shadow_selector cannot be combined
"""
    if not missing_shadow_flag:
        source += 'parser.add_argument(\n        "--camp_default_off_shadow_selector"\n)\n'
    return source


def _audit_text(*, wrong_scope: bool = False) -> str:
    next_target = (
        "next_work_target=old_scope"
        if wrong_scope
        else "next_work_target=dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_only"
    )
    return "\n".join(
        [
            "current_v13_status=current_source_default_off_shadow_selector_runtime_artifact_manifest_materialized",
            next_target,
            "runtime_shadow_selector_execution_authorized=False",
            "training_execution_authorized_by_current_boundary=False",
        ]
    )


def _paths(tmp_path: Path, *, manifest_drift: bool = False) -> dict[str, Path]:
    atom_scales = _write(tmp_path / "artifacts" / "atom_scales.json", "{}")
    static_weights = tmp_path / "artifacts" / "weights.npy"
    static_weights.parent.mkdir(parents=True, exist_ok=True)
    static_weights.write_bytes(b"weights")
    atom_sha = _sha256(atom_scales)
    weights_sha = _sha256(static_weights)
    manifest = {
        "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
        "default_off": True,
        "selection_effect": False,
        "selector_mode": "static",
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "required_candidate_count": 7 if manifest_drift else 8,
        "atom_count": 14,
        "atom_schema_version": "dp_camp_v10_14d",
        "score_expression": "score_k(w)=a_k^T w",
        "required_dp_head": FIXED_DP_HEAD,
        "current_dp_head": FIXED_DP_HEAD,
        "current_camp_head": CAMP_HEAD,
        "artifacts": {
            "atom_scales": {
                "logical_name": "atom_scales",
                "path": str(atom_scales),
                "required": True,
                "sha256": atom_sha,
            },
            "static_weights": {
                "logical_name": "static_weights",
                "path": str(static_weights),
                "required": True,
                "sha256": weights_sha,
            },
        },
    }
    runtime_manifest = tmp_path / "runtime_manifest.json"
    runtime_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    diffusion_repo = tmp_path / "Diffusion-Planner"
    diffusion_repo.mkdir()
    route_path = _write(tmp_path / "route.pkl", "route")
    model_path = tmp_path / "diffusion_planner.pth"
    model_path.write_bytes(b"model")
    config = _write(tmp_path / "replay_default.json", "{}")
    runner = _write(tmp_path / "run_diffusion_planner_camp_replay.py", _runner_source())
    audit = _write(tmp_path / "audit.md", _audit_text())
    return {
        "runtime_manifest_json": runtime_manifest,
        "replay_runner_py": runner,
        "v13_audit_md": audit,
        "diffusion_repo": diffusion_repo,
        "route_path": route_path,
        "model_path": model_path,
        "config": config,
        "planned_replay_output_dir": tmp_path / "planned" / "replay",
    }


def _report(tmp_path: Path, **overrides):
    paths = _paths(tmp_path, manifest_drift=overrides.pop("manifest_drift", False))
    if overrides.pop("missing_shadow_flag", False):
        paths["replay_runner_py"].write_text(
            _runner_source(missing_shadow_flag=True),
            encoding="utf-8",
        )
    if overrides.pop("wrong_audit_scope", False):
        paths["v13_audit_md"].write_text(_audit_text(wrong_scope=True), encoding="utf-8")
    if overrides.pop("existing_output", False):
        paths["planned_replay_output_dir"].mkdir(parents=True)
    params = {
        **paths,
        "route_name": "sample_normal",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": FIXED_DP_HEAD,
        "seed": overrides.pop("seed", 301),
        "enabled": True,
    }
    params.update(overrides)
    return build_report(**params)


def test_preflight_is_default_off_and_does_not_read_missing_inputs(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = build_report(
        runtime_manifest_json=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
        diffusion_repo=missing,
        route_name="sample_normal",
        route_path=missing,
        model_path=missing,
        config=missing,
        planned_replay_output_dir=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        seed=301,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["review_checks"] == []
    assert report["final_decision"]["shadow_replay_execution_authorized_next"] is False


def test_preflight_accepts_valid_fixture_and_builds_single_shadow_command(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    command = report["planned_command"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["shadow_replay_execution_authorized_next"] is True
    assert decision["replay_execution_performed"] is False
    assert "--camp_default_off_shadow_selector" in command
    assert "--camp_shadow_artifact_manifest" in command
    assert "--candidate_reference_blend_steps" not in command
    assert "--candidate_guidance_config" not in command
    assert "--camp_underprogress_relaxation" not in command
    assert report["preflight"]["planned_output_absent"] is True


def test_preflight_rejects_formal_seed(tmp_path: Path) -> None:
    report = _report(tmp_path, seed=11)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "seed_is_nonformal" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_preflight_rejects_manifest_candidate_count_drift(tmp_path: Path) -> None:
    report = _report(tmp_path, manifest_drift=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "manifest_required_candidate_count" in report["final_decision"]["failed_checks"]


def test_preflight_rejects_runner_contract_drift(tmp_path: Path) -> None:
    report = _report(tmp_path, missing_shadow_flag=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_has_shadow_flag" in report["final_decision"]["failed_checks"]


def test_preflight_rejects_existing_output_dir(tmp_path: Path) -> None:
    report = _report(tmp_path, existing_output=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "planned_output_absent" in report["final_decision"]["failed_checks"]


def test_preflight_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, wrong_audit_scope=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_current_scope_authorizes_preflight" in report["final_decision"][
        "failed_checks"
    ]


def test_preflight_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    output_json = tmp_path / "out" / "preflight.json"
    output_md = tmp_path / "out" / "preflight.md"

    exit_code = main(
        [
            "--runtime_manifest_json",
            str(paths["runtime_manifest_json"]),
            "--replay_runner_py",
            str(paths["replay_runner_py"]),
            "--v13_audit_md",
            str(paths["v13_audit_md"]),
            "--diffusion_repo",
            str(paths["diffusion_repo"]),
            "--route_name",
            "sample_normal",
            "--route_path",
            str(paths["route_path"]),
            "--model_path",
            str(paths["model_path"]),
            "--config",
            str(paths["config"]),
            "--planned_replay_output_dir",
            str(paths["planned_replay_output_dir"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--seed",
            "301",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--enable_v13_default_off_shadow_selector_runtime_shadow_replay_preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "static preflight only" in output_md.read_text(encoding="utf-8")
