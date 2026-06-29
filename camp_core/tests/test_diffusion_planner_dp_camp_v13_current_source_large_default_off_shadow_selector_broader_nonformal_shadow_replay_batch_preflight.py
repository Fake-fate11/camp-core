import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_current_source_large_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CAMP_HEAD = "5abd79a0a1035ed5cc3379de14a0f90f2c934b74"


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
        else (
            "next_work_target=dp_camp_v13_current_source_large_default_off_"
            "shadow_selector_broader_nonformal_shadow_replay_batch_preflight_only"
        )
    )
    return "\n".join(
        [
            "current_v13_status=current_source_large_default_off_shadow_selector_runtime_shadow_replay_smoke_execution_passed",
            next_target,
            "runtime_shadow_selector_execution_authorized=False",
            "replay_execution_authorized_by_current_boundary=False",
            "training_execution_authorized_by_current_boundary=False",
        ]
    )


def _paths(tmp_path: Path, *, missing_shadow_flag: bool = False) -> dict[str, Path]:
    atom_scales = _write(tmp_path / "artifacts" / "atom_scales.json", "{}")
    static_weights = tmp_path / "artifacts" / "weights.npy"
    static_weights.parent.mkdir(parents=True, exist_ok=True)
    static_weights.write_bytes(b"weights")
    route_normal = _write(tmp_path / "routes" / "sample_normal.pkl", "route")
    route_tl = _write(tmp_path / "routes" / "sample_tl.pkl", "route")
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
        "required_candidate_count": 8,
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
    model_path = tmp_path / "diffusion_planner.pth"
    model_path.write_bytes(b"model")
    model_args = _write(tmp_path / "diffusion_planner.param.json", "{}")
    config = _write(tmp_path / "replay_default.json", "{}")
    reward_config = _write(tmp_path / "dp_camp_reward_eval.json", "{}")
    runner = _write(
        tmp_path / "run_diffusion_planner_camp_replay.py",
        _runner_source(missing_shadow_flag=missing_shadow_flag),
    )
    audit = _write(tmp_path / "audit.md", _audit_text())
    return {
        "runtime_manifest_json": runtime_manifest,
        "replay_runner_py": runner,
        "v13_audit_md": audit,
        "diffusion_repo": diffusion_repo,
        "route_normal": route_normal,
        "route_tl": route_tl,
        "model_path": model_path,
        "model_args": model_args,
        "config": config,
        "reward_config": reward_config,
        "base_replay_output_dir": tmp_path / "planned_batch",
    }


def _report(tmp_path: Path, **overrides):
    paths = _paths(
        tmp_path,
        missing_shadow_flag=overrides.pop("missing_shadow_flag", False),
    )
    if overrides.pop("wrong_audit_scope", False):
        paths["v13_audit_md"].write_text(_audit_text(wrong_scope=True), encoding="utf-8")
    if overrides.pop("existing_output", False):
        paths["base_replay_output_dir"].mkdir(parents=True)
    route_specs = overrides.pop(
        "route_specs",
        (
            f"sample_normal={paths['route_normal']}",
            f"sample_tl={paths['route_tl']}",
        ),
    )
    params = {
        "runtime_manifest_json": paths["runtime_manifest_json"],
        "replay_runner_py": paths["replay_runner_py"],
        "v13_audit_md": paths["v13_audit_md"],
        "diffusion_repo": paths["diffusion_repo"],
        "route_specs": route_specs,
        "model_path": paths["model_path"],
        "model_args": paths["model_args"],
        "config": paths["config"],
        "reward_config": paths["reward_config"],
        "base_replay_output_dir": paths["base_replay_output_dir"],
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": FIXED_DP_HEAD,
        "enabled": True,
    }
    params.update(overrides)
    return build_report(**params)


def test_preflight_disabled_does_not_read_missing_inputs(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    report = build_report(
        runtime_manifest_json=missing,
        replay_runner_py=missing,
        v13_audit_md=missing,
        diffusion_repo=missing,
        route_specs=("sample_normal=/missing.pkl",),
        model_path=missing,
        model_args=missing,
        config=missing,
        reward_config=missing,
        base_replay_output_dir=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["review_checks"] == []
    assert report["final_decision"]["batch_execution_authorized_next"] is False


def test_preflight_accepts_valid_fixture_and_builds_batch_runbook(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    preflight = report["preflight"]
    commands = report["planned_commands"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["batch_execution_authorized_next"] is True
    assert decision["replay_execution_performed"] is False
    assert preflight["command_count"] == 16
    assert preflight["expected_records"] == 1600
    assert preflight["formal_seeds_excluded"] is True
    assert preflight["route_names"] == ["sample_normal", "sample_tl"]
    assert all("--camp_default_off_shadow_selector" in item["command"] for item in commands)
    assert all("--camp_shadow_artifact_manifest" in item["command"] for item in commands)
    assert all("--model_args" in item["command"] for item in commands)
    assert all("--reward_config" in item["command"] for item in commands)
    assert all("--candidate_reference_blend_steps" not in item["command"] for item in commands)
    assert all("--candidate_guidance_config" not in item["command"] for item in commands)
    assert all("--camp_underprogress_relaxation" not in item["command"] for item in commands)


def test_preflight_rejects_formal_seed(tmp_path: Path) -> None:
    report = _report(tmp_path, seeds=(11, 301))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "seeds_exclude_formal" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_preflight_rejects_wrong_latest_audit_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, wrong_audit_scope=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_scope_allows_batch_preflight" in report["final_decision"][
        "failed_checks"
    ]


def test_preflight_rejects_existing_base_output_dir(tmp_path: Path) -> None:
    report = _report(tmp_path, existing_output=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "base_output_absent" in report["final_decision"]["failed_checks"]


def test_preflight_rejects_runner_contract_drift(tmp_path: Path) -> None:
    report = _report(tmp_path, missing_shadow_flag=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_has_shadow_flag" in report["final_decision"]["failed_checks"]


def test_preflight_cli_writes_json_markdown_and_runbook(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    output_json = tmp_path / "out" / "preflight.json"
    output_md = tmp_path / "out" / "preflight.md"
    output_runbook = tmp_path / "out" / "runbook.sh"

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
            "--route",
            f"sample_normal={paths['route_normal']}",
            "--route",
            f"sample_tl={paths['route_tl']}",
            "--model_path",
            str(paths["model_path"]),
            "--model_args",
            str(paths["model_args"]),
            "--config",
            str(paths["config"]),
            "--reward_config",
            str(paths["reward_config"]),
            "--base_replay_output_dir",
            str(paths["base_replay_output_dir"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--output_runbook",
            str(output_runbook),
            "--enable_v13_current_source_large_default_off_shadow_selector_broader_nonformal_shadow_replay_batch_preflight",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "static preflight only" in output_md.read_text(encoding="utf-8")
    runbook = output_runbook.read_text(encoding="utf-8")
    assert "Do not execute unless the audit EOF authorizes batch execution" in runbook
    assert "--camp_default_off_shadow_selector" in runbook
