import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay.py"
)
CAMP_HEAD = "f6118926b20c245ed4624820db23163e5f4680d3"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_runtime_shadow_replay_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _runner_source() -> str:
    return """
parser.add_argument("--camp_default_off_shadow_selector")
parser.add_argument("--camp_shadow_artifact_manifest")
parser.add_argument("--camp_shadow_expected_atom_scales_sha256")
parser.add_argument("--camp_shadow_expected_static_weights_sha256")
def _load_shadow_artifact_manifest(path): pass
{"executed_output_policy": "dp_top1"}
shadow_selected_index
--camp_default_off_shadow_selector cannot be combined
"""


def _audit_text(module, *, wrong_gate: bool = False) -> str:
    next_work = "old_gate" if wrong_gate else module.AUTHORIZED_CURRENT_WORK
    return "\n".join(
        [
            f"current_v14_status={module.EXPECTED_CURRENT_STATUS}",
            f"next_work_target={next_work}",
            "default_off_shadow_selector_runtime_shadow_replay_preflight_authorized=True",
            "default_off_shadow_selector_runtime_execution_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )


def _fixture(tmp_path: Path, module, monkeypatch, **overrides):
    assets_dir = tmp_path / "assets"
    patched_assets = []
    for asset in module.EXPECTED_PUBLIC_ASSETS:
        path = assets_dir / asset["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"asset:{asset['name']}".encode("utf-8"))
        patched_assets.append({**asset, "sha256": _sha256(path)})
    monkeypatch.setattr(module, "EXPECTED_PUBLIC_ASSETS", tuple(patched_assets))

    dp_repo = tmp_path / "Diffusion-Planner"
    _write(dp_repo / module.DP_REPLAY_CONFIG, "{}")
    camp_repo = tmp_path / "camp_core"
    _write(camp_repo / module.REWARD_CONFIG, "{}")
    _write(camp_repo / module.REPLAY_SCRIPT, _runner_source())
    dp_python = _write(tmp_path / "dp312_venv" / "bin" / "python", "#!/usr/bin/env python\n")

    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(parents=True)
    atom_scales = artifact_dir / "atom_scales_dp_static.json"
    atom_scales.write_text(
        json.dumps({"scales": [float(index + 1) for index in range(module.EXPECTED_ATOM_COUNT)]}),
        encoding="utf-8",
    )
    static_weights = artifact_dir / "offline_weights_dp_static.npy"
    weights = np.full(module.EXPECTED_ATOM_COUNT, 1.0 / module.EXPECTED_ATOM_COUNT)
    if overrides.pop("negative_weight", False):
        weights[0] = -0.1
        weights[1] += 0.1
    np.save(static_weights, weights)

    manifest = {
        "schema_version": module.RUNTIME_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
        "source_scope": module.SOURCE_SCOPE,
        "default_off": True,
        "fail_closed": True,
        "selection_effect": False,
        "online_selector_change": False,
        "selector_mode": "static",
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "required_candidate_count": (
            7 if overrides.pop("manifest_candidate_count_drift", False) else module.EXPECTED_CANDIDATE_COUNT
        ),
        "atom_count": module.EXPECTED_ATOM_COUNT,
        "atom_schema_version": module.ATOM_SCHEMA_VERSION,
        "score_expression": module.SCORE_EXPRESSION,
        "required_dp_head": module.FIXED_DP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "current_camp_head": CAMP_HEAD,
        "artifacts": {
            "atom_scales": {
                "logical_name": "atom_scales",
                "path": str(atom_scales),
                "sha256": _sha256(atom_scales),
                "required": True,
            },
            "static_weights": {
                "logical_name": "static_weights",
                "path": str(static_weights),
                "sha256": _sha256(static_weights),
                "required": True,
            },
        },
        "authorizations": {
            **{name: False for name in module.BLOCKED_AUTHORIZATIONS},
            "training_executed": False,
        },
    }
    runtime_manifest = tmp_path / "runtime_manifest.json"
    runtime_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    v14_audit = _write(tmp_path / "v14_audit.md", _audit_text(module, wrong_gate=overrides.pop("wrong_gate", False)))
    current_status = _write(tmp_path / "current_status.md", _audit_text(module))
    replay_output_root = tmp_path / "planned_runtime_shadow_replay"
    if overrides.pop("existing_output", False):
        replay_output_root.mkdir(parents=True)

    return {
        "runtime_manifest_json": runtime_manifest,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_json": tmp_path / "out" / "runtime_shadow_replay_preflight.json",
        "output_md": tmp_path / "out" / "runtime_shadow_replay_preflight.md",
        "output_runbook": tmp_path / "out" / "run_runtime_shadow_replay.sh",
        "replay_output_root": replay_output_root,
        "expected_runtime_manifest_sha256": _sha256(runtime_manifest),
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "dp_repo": dp_repo,
        "camp_repo": camp_repo,
        "assets_dir": assets_dir,
        "dp_python": dp_python,
        "steps": module.EXPECTED_STEPS_PER_LOG,
        "num_candidates": module.EXPECTED_CANDIDATE_COUNT,
        "max_npcs": 4,
        "spawn_probability": 0.3,
        "seeds": overrides.pop("seeds", module.DEFAULT_SEEDS),
        "traffic_light_modes": module.DEFAULT_TRAFFIC_LIGHT_MODES,
        "enabled": True,
        **overrides,
    }


def test_runtime_shadow_replay_preflight_passes_and_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, monkeypatch)

    report = module.build_report(**kwargs)
    module.write_outputs(
        output_json=kwargs["output_json"],
        output_md=kwargs["output_md"],
        output_runbook=kwargs["output_runbook"],
        report=report,
    )

    decision = report["final_decision"]
    preflight = report["shadow_replay_preflight"]
    command_text = "\n".join(" ".join(command) for command in preflight["planned_commands"])
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["shadow_replay_execution_authorized_next"] is True
    assert decision["replay_execution_performed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert preflight["planned_command_count"] == module.EXPECTED_LOG_COUNT
    assert preflight["expected_records"] == module.EXPECTED_RECORDS
    assert "--camp_default_off_shadow_selector" in command_text
    assert "--camp_shadow_artifact_manifest" in command_text
    assert "--camp_collect_closed_loop_outcomes" not in command_text
    assert "--candidate_guidance_config" not in command_text
    assert kwargs["output_json"].is_file()
    assert kwargs["output_md"].is_file()
    assert kwargs["output_runbook"].is_file()
    assert (kwargs["output_json"].parent / "SHA256SUMS").is_file()


def test_runtime_shadow_replay_preflight_is_default_off_when_disabled(tmp_path: Path) -> None:
    module = _load_module()
    missing = tmp_path / "missing"
    report = module.build_report(
        runtime_manifest_json=missing,
        v14_audit_md=missing,
        current_status_md=missing,
        output_json=tmp_path / "out.json",
        output_md=tmp_path / "out.md",
        output_runbook=tmp_path / "run.sh",
        replay_output_root=tmp_path / "planned",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=module.FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == module.DISABLED_STATUS
    assert report["checks"] == []
    assert report["final_decision"]["shadow_replay_execution_authorized_next"] is False


def test_runtime_shadow_replay_preflight_rejects_wrong_eof(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, monkeypatch, wrong_gate=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_shadow_replay_preflight_rejects_formal_seed(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, monkeypatch, seeds=(11, 12))

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "formal_seeds_forbidden" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "forbidden_shadow_replay_command_contract_failure"


def test_runtime_shadow_replay_preflight_rejects_manifest_drift(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, monkeypatch, manifest_candidate_count_drift=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "manifest_candidate_count" in report["final_decision"]["failed_checks"]


def test_runtime_shadow_replay_preflight_rejects_negative_weight(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, monkeypatch, negative_weight=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "static_weights_nonnegative" in report["final_decision"]["failed_checks"]


def test_runtime_shadow_replay_preflight_rejects_existing_output_root(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, monkeypatch, existing_output=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "replay_output_root_absent" in report["final_decision"]["failed_checks"]
