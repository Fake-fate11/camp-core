import hashlib
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_fixed_dp_candidate_generation.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_public_sim_preflight", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: bytes = b"data") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, audit_target: str | None = None, nuscenes_missing: bool = False):
    module = _load_module()
    camp_repo = tmp_path / "camp"
    dp_repo = tmp_path / "dp"
    assets_dir = tmp_path / "assets"
    nu_root = tmp_path / "nuScenes"
    dp_python = tmp_path / "venv" / "bin" / "python"
    candidate_output_root = tmp_path / "planned_outputs"

    _write(camp_repo / module.REPLAY_SCRIPT)
    _write(camp_repo / module.REWARD_CONFIG)
    _write(dp_repo / module.DP_REPLAY_CONFIG)
    _write(dp_python)
    nu_root.mkdir(parents=True)

    expected_assets = []
    for asset in module.EXPECTED_PUBLIC_ASSETS:
        path = assets_dir / asset["relative_path"]
        _write(path, f"asset:{asset['name']}".encode("utf-8"))
        expected_assets.append(
            {
                "name": asset["name"],
                "relative_path": asset["relative_path"],
                "sha256": _sha(path),
            }
        )
    static_weights = assets_dir / module.STATIC_WEIGHTS_REL
    atom_scales = assets_dir / module.ATOM_SCALES_REL
    _write(static_weights, b"weights")
    _write(atom_scales, b"scales")

    audit_target = audit_target or module.AUTHORIZED_CURRENT_WORK
    v14_audit = tmp_path / "docs" / "diffusion_planner_v14_iteration_audit.md"
    v14_audit.parent.mkdir(parents=True)
    v14_audit.write_text(
        "\n".join(
            [
                "current_v14_status=old_status",
                "next_work_target=old_target",
                f"current_v14_status={module.CURRENT_V14_STATUS}",
                "public_nuscenes_archives_available=True",
                f"v14_public_simulator_source_reclassification_nuscenes_marked_missing={nuscenes_missing}",
                f"next_work_target={audit_target}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    current_status = tmp_path / "docs" / "diffusion_planner_current_status.md"
    current_status.write_text(
        "\n".join(
            [
                "docs/diffusion_planner_v14_iteration_audit.md",
                module.CURRENT_V14_STATUS,
                module.AUTHORIZED_CURRENT_WORK,
                "",
            ]
        ),
        encoding="utf-8",
    )
    kwargs = {
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "candidate_output_root": candidate_output_root,
        "current_camp_head": "abc123",
        "current_camp_origin_main": "abc123",
        "current_dp_head": module.FIXED_DP_HEAD,
        "dp_repo": dp_repo,
        "camp_repo": camp_repo,
        "assets_dir": assets_dir,
        "dp_python": dp_python,
        "public_nuscenes_root": nu_root,
        "expected_public_assets": expected_assets,
        "expected_static_weights_sha256": _sha(static_weights),
        "expected_atom_scales_sha256": _sha(atom_scales),
    }
    return module, kwargs


def test_v14_public_simulator_preflight_ready_contract(tmp_path: Path) -> None:
    module, kwargs = _fixture(tmp_path)

    report = module.build_report(**kwargs)

    decision = report["final_decision"]
    preflight = report["public_simulator_preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["score_expression"] == "score_k(w)=a_k^T w"
    assert preflight["planned_command_count"] == 32
    assert preflight["expected_records"] == 3200
    assert preflight["num_candidates"] == 8
    assert set(preflight["seeds"]).isdisjoint({11, 12, 13})
    assert preflight["executed_output_policy"] == "dp_top1"
    assert preflight["default_off_shadow_selector"] is True
    assert preflight["candidate_tensor_provenance_logging"] is True
    first_command = preflight["planned_commands"][0]
    assert "--camp_default_off_shadow_selector" in first_command
    assert "--camp_candidate_tensor_provenance_logging" in first_command
    assert "--camp_selector_mode" in first_command
    assert first_command[first_command.index("--camp_selector_mode") + 1] == "static"
    assert first_command[first_command.index("--num_candidates") + 1] == "8"


def test_v14_public_simulator_preflight_rejects_wrong_eof_gate(tmp_path: Path) -> None:
    module, kwargs = _fixture(
        tmp_path,
        audit_target="external_valid_nonfixture_dp_native_npz_source_manifest_required_before_fixed_dp_candidate_generation_execution",
    )

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_v14_public_simulator_preflight_rejects_missing_nuscenes_marker(tmp_path: Path) -> None:
    module, kwargs = _fixture(tmp_path, nuscenes_missing=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_nuscenes_not_marked_missing" in report["final_decision"]["failed_checks"]


def test_v14_public_simulator_preflight_rejects_existing_output_root(tmp_path: Path) -> None:
    module, kwargs = _fixture(tmp_path)
    kwargs["candidate_output_root"].mkdir(parents=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "candidate_output_root_absent" in report["final_decision"]["failed_checks"]


def test_v14_public_simulator_preflight_cli_writes_guarded_artifacts(tmp_path: Path) -> None:
    module, kwargs = _fixture(tmp_path)
    output_json = tmp_path / "artifact" / "preflight.json"
    output_md = tmp_path / "artifact" / "preflight.md"
    output_runbook = tmp_path / "artifact" / "run.sh"

    real_sha256 = module._sha256
    expected_by_suffix = {
        asset["relative_path"].replace("\\", "/"): asset["sha256"]
        for asset in module.EXPECTED_PUBLIC_ASSETS
    }
    expected_by_suffix[str(module.STATIC_WEIGHTS_REL).replace("\\", "/")] = (
        module.EXPECTED_STATIC_WEIGHTS_SHA256
    )
    expected_by_suffix[str(module.ATOM_SCALES_REL).replace("\\", "/")] = (
        module.EXPECTED_ATOM_SCALES_SHA256
    )

    def fake_sha256(path: Path) -> str:
        normalized = str(path).replace("\\", "/")
        for suffix, expected in expected_by_suffix.items():
            if normalized.endswith(suffix):
                return expected
        return real_sha256(path)

    module._sha256 = fake_sha256
    try:
        exit_code = module.main(
            [
                "--v14_audit_md",
                str(kwargs["v14_audit_md"]),
                "--current_status_md",
                str(kwargs["current_status_md"]),
                "--output_json",
                str(output_json),
                "--output_md",
                str(output_md),
                "--output_runbook",
                str(output_runbook),
                "--candidate_output_root",
                str(kwargs["candidate_output_root"]),
                "--current_camp_head",
                kwargs["current_camp_head"],
                "--current_camp_origin_main",
                kwargs["current_camp_origin_main"],
                "--current_dp_head",
                kwargs["current_dp_head"],
                "--dp_repo",
                str(kwargs["dp_repo"]),
                "--camp_repo",
                str(kwargs["camp_repo"]),
                "--assets_dir",
                str(kwargs["assets_dir"]),
                "--dp_python",
                str(kwargs["dp_python"]),
                "--public_nuscenes_root",
                str(kwargs["public_nuscenes_root"]),
            ]
        )
    finally:
        module._sha256 = real_sha256

    assert exit_code == 0
    assert module.READY_STATUS in output_json.read_text(encoding="utf-8")
    runbook = output_runbook.read_text(encoding="utf-8")
    assert module.GUARD_ENV_VAR in runbook
    assert "camp_candidate_tensor_provenance_logging" in runbook
    assert "camp_default_off_shadow_selector" in runbook
    assert "Refusing to run: set" in runbook
