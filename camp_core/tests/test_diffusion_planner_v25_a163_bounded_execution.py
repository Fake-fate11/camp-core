from __future__ import annotations

from contextlib import contextmanager
import copy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations import diffusion_planner_v25_a163_bounded_authority as authority
from camp_core.integrations.diffusion_planner_v25_a163_bounded_authority import (
    EXPECTED_RUNS,
    EXPECTED_TICKS,
    EXPECTED_UNIQUE_IDENTITIES,
    FIXED_DP_HEAD,
    RELEASE_FIELDS,
    RELEASE_GATE,
    RELEASE_SCHEMA_VERSION,
    RELEASE_STATUS,
    canonical_sha256,
    validate_bounded_plan,
    verify_bounded_release,
)
from scripts.integrations import run_diffusion_planner_v25_a163_bounded_execution as runner


ROOT = Path(__file__).resolve().parents[2]


def _plan() -> dict:
    runs = []
    for ordinal in range(EXPECTED_RUNS):
        identity = 0 if ordinal in (0, EXPECTED_RUNS - 1) else ordinal
        runs.append(
            {
                "run_ordinal": ordinal,
                "scenario_id": f"{identity:064x}",
                "occurrence": "identity0_first"
                if ordinal == 0
                else "identity0_final_repeat"
                if ordinal == EXPECTED_RUNS - 1
                else "unique_identity",
                "ticks": 64,
                "seed": 25001,
            }
        )
    return {
        "schema_version": authority.PLAN_SCHEMA_VERSION,
        "status": "passed_preflight_plan_k8_execute_closed",
        "seed": 25001,
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_capacity": EXPECTED_TICKS,
        "sequential_fixed_k8": True,
        "k8_executed": False,
        "candidate_generation_started": False,
        "model_loaded": False,
        "simulator_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "runs": runs,
    }


def _decision(tmp_path: Path) -> tuple[dict, Path, Path, Path]:
    dp_repo = tmp_path / "dp"
    dp_repo.mkdir()
    template = tmp_path / "template.json"
    template.write_text("{}\n", encoding="utf-8")
    output = (tmp_path / "bounded-output").resolve()
    manifest = {"critical.py": "a" * 64}
    roots = {role: {"path": str((tmp_path / role).resolve()), "root_sha256": "b" * 64, "report_file": "report.json"} for role in authority.ROOT_ROLES}
    decision = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "status": RELEASE_STATUS,
        "gate": RELEASE_GATE,
        "implementation_source_head": "1" * 40,
        "pointer_head_at_release": "2" * 40,
        "fixed_dp_head": FIXED_DP_HEAD,
        "dp_repo": str(dp_repo.resolve()),
        "probe_template": str(template.resolve()),
        "probe_template_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
        "critical_implementation_manifest": manifest,
        "critical_implementation_manifest_sha256": canonical_sha256(manifest),
        "root_artifacts": roots,
        "root_artifacts_sha256": canonical_sha256(roots),
        "run_nonce": "3" * 64,
        "authorized_output_dir": str(output),
        "seed": 25001,
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_capacity": EXPECTED_TICKS,
        "bounded_execute_authorized": True,
        "full_config_preflight_authorized": False,
        "full_r_execute_authorized": False,
        "monitor_enabled": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    assert set(decision) == RELEASE_FIELDS
    return decision, dp_repo, template, output


def _seal_release(root: Path, decision: dict) -> str:
    root.mkdir()
    (root / "decision.json").write_bytes(authority.canonical_json_bytes(decision))
    (root / "HEADS").write_text(
        f"camp_source_head={decision['implementation_source_head']}\n"
        f"camp_pointer_head={decision['pointer_head_at_release']}\n"
        f"fixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (root / "COMMAND").write_text("test\n", encoding="ascii")
    (root / "run.exit").write_bytes(b"0\n")
    return seal_artifact(root, label="test bounded release")


def _patch_release_dependencies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(authority, "NONCE_LEDGER", tmp_path / "nonce-ledger")
    monkeypatch.setattr(authority, "verify_dual_head_contract", lambda **kwargs: {})
    monkeypatch.setattr(
        authority,
        "verify_four_root_chain",
        lambda **kwargs: {"verified": {}, "plan": _plan()},
    )
    monkeypatch.setattr(
        authority,
        "_git",
        lambda repo, *args: FIXED_DP_HEAD if args == ("rev-parse", "HEAD") else "",
    )


def test_bounded_plan_rejects_denominator_order_and_full_r_drift() -> None:
    plan = _plan()
    validate_bounded_plan(plan)
    for key, value in (
        ("unique_identity_count", 245),
        ("run_count", 243),
        ("snapshot_capacity", EXPECTED_TICKS - 64),
        ("k8_executed", True),
    ):
        mutated = copy.deepcopy(plan)
        mutated[key] = value
        with pytest.raises(ValueError):
            validate_bounded_plan(mutated)
    mutated = copy.deepcopy(plan)
    mutated["runs"][1]["run_ordinal"] = 2
    with pytest.raises(ValueError, match="order"):
        validate_bounded_plan(mutated)


def test_release_consumption_is_one_shot_and_exact_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    release = tmp_path / "release"
    root = _seal_release(release, decision)
    _patch_release_dependencies(monkeypatch, tmp_path)
    verified = verify_bounded_release(
        repo=ROOT,
        release_artifact=release,
        release_root_sha256=root,
        requested_output_dir=output,
        current_pointer_head=decision["pointer_head_at_release"],
        dp_repo=dp_repo,
        probe_template=template,
        consume=True,
    )
    assert verified["nonce_marker"] is not None
    with pytest.raises(ValueError, match="already consumed"):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=output,
            current_pointer_head=decision["pointer_head_at_release"],
            dp_repo=dp_repo,
            probe_template=template,
            consume=True,
        )
    with pytest.raises(ValueError, match="output"):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=tmp_path / "alternate",
            current_pointer_head=decision["pointer_head_at_release"],
            dp_repo=dp_repo,
            probe_template=template,
            consume=False,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_count", 243),
        ("unique_identity_count", 245),
        ("full_r_execute_authorized", True),
        ("bounded_execute_authorized", False),
        ("fixed_dp_head", "0" * 40),
        ("run_nonce", 3),
    ],
)
def test_release_mutations_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    decision[field] = value
    release = tmp_path / "release"
    root = _seal_release(release, decision)
    _patch_release_dependencies(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=output,
            current_pointer_head=decision["pointer_head_at_release"],
            dp_repo=dp_repo,
            probe_template=template,
            consume=False,
        )


@pytest.mark.parametrize("mutation", ["root", "manifest", "pointer", "dp_repo"])
def test_release_authority_bindings_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    current_pointer = decision["pointer_head_at_release"]
    if mutation == "root":
        decision["root_artifacts"]["source"]["root_sha256"] = "c" * 64
    elif mutation == "manifest":
        decision["critical_implementation_manifest"]["critical.py"] = "c" * 64
    elif mutation == "pointer":
        decision["pointer_head_at_release"] = "9" * 40
    else:
        decision["dp_repo"] = str((tmp_path / "alternate-dp").resolve())
    release = tmp_path / "release"
    root = _seal_release(release, decision)
    _patch_release_dependencies(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=output,
            current_pointer_head=current_pointer,
            dp_repo=dp_repo,
            probe_template=template,
            consume=False,
        )


def test_authority_fails_before_model_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_called = False

    def model(*args, **kwargs):
        nonlocal model_called
        model_called = True
        raise AssertionError("model must not be reached")

    monkeypatch.setattr(runner.corpus, "build_native_arm_runner", model)
    monkeypatch.setattr(
        runner,
        "_git",
        lambda repo, *args: FIXED_DP_HEAD if repo.name == "dp" and args == ("rev-parse", "HEAD") else ("4" * 40 if args == ("rev-parse", "HEAD") else ""),
    )
    monkeypatch.setattr(
        runner,
        "verify_bounded_release",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("authority blocked")),
    )
    monkeypatch.setattr(
        runner.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(free=20 * 1024**3),
    )
    dp_repo = tmp_path / "dp"
    dp_repo.mkdir()
    args = SimpleNamespace(
        dp_repo=dp_repo,
        output_dir=tmp_path / "output",
        release_artifact=tmp_path / "release",
        release_root_sha256="1" * 64,
        probe_template=tmp_path / "template",
        device="cpu",
    )
    with pytest.raises(ValueError, match="authority blocked"):
        runner._run(args)
    assert model_called is False
    assert not args.output_dir.exists()


def test_bounded_snapshot_index_carries_repeat_occurrence(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    stream = io.StringIO()
    run = _plan()["runs"][-1]
    payload = {"schema_version": "old", "feature_payload": {}, "sidecar": {}}
    row = runner._write_snapshot(
        output_dir=output,
        index_file=stream,
        run=run,
        tick_index=63,
        payload=payload,
    )
    assert row["run_ordinal"] == 243
    assert row["occurrence"] == "identity0_final_repeat"
    assert payload["sidecar"]["run_ordinal"] == 243
    assert payload["sidecar"]["occurrence"] == "identity0_final_repeat"


def test_run_evidence_is_derived_from_raw_snapshots_and_native_ticks() -> None:
    run = _plan()["runs"][0]
    payloads = []
    ticks = []
    for tick_index in range(64):
        payloads.append(
            {
                "feature_payload": {
                    "candidate_row_sha256": [f"{index:x}" * 64 for index in range(8)],
                    "atom_matrix": [[float(index + column) for column in range(14)] for index in range(8)],
                    "raw_context": {"ego_speed_mps": float(tick_index)},
                    "context_source_complete": {"ego_speed_mps": True},
                },
                "sidecar": {
                    "candidate0_sha256": "0" * 64,
                    "selected_index": tick_index % 8,
                    "context_source_receipt": {"mode": "no_v2i"},
                    "signal_source_class": "no_signal",
                    "phase_authority_mode": None,
                    "controlled_signal_source_receipt": {"current_phase": None},
                    "controlled_signal_tensor_evidence": None,
                    "controlled_model_input_cache_receipt": {"tick_index": tick_index},
                    "causal_signal_atom_input": {"source_state": "not_applicable"},
                },
            }
        )
        ticks.append(
            {
                "safety": {
                    "position_xy": [float(tick_index), 0.0],
                    "ego_heading_rad": 0.0,
                    "route_progress_m": float(tick_index),
                    "speed_mps": 1.0,
                }
            }
        )
    evidence = runner.build_run_evidence(
        run=run,
        payloads=payloads,
        native_receipt={"ticks": ticks},
        failure_class="none",
    )
    assert evidence["candidate0_sha256_sequence"] == ["0" * 64] * 64
    assert evidence["k8_row_sha256_sequence"][0][7] == "7" * 64
    assert evidence["selected_index_sequence"] == [value % 8 for value in range(64)]
    assert len(evidence["closed_loop_trajectory_sha256"]) == 64
    assert len(evidence["speed_probe_sha256"]) == 64


def test_failure_path_is_sealed_and_releases_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "failed"

    @contextmanager
    def lock(path):
        yield

    monkeypatch.setattr(runner, "_exclusive_lock", lock)
    monkeypatch.setattr(
        runner,
        "_run",
        lambda args: (_ for _ in ()).throw(RuntimeError("synthetic failure")),
    )
    with pytest.raises(RuntimeError, match="synthetic failure"):
        runner.main(
            [
                "--probe-template",
                str(tmp_path / "template"),
                "--dp-repo",
                str(tmp_path / "dp"),
                "--release-artifact",
                str(tmp_path / "release"),
                "--release-root-sha256",
                "a" * 64,
                "--output-dir",
                str(output),
                "--device",
                "cpu",
                "--bounded-execute",
            ]
        )
    assert (output / "run.exit").read_bytes() == b"1\n"
    assert verify_complete_seal(output)["file_count"] == 2


def test_post_run_reviewer_does_not_import_producer_evidence_helper() -> None:
    text = (
        ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_v25_a163_bounded_execution.py"
    ).read_text(encoding="utf-8")
    assert "build_run_evidence" not in text
    assert "run_diffusion_planner_v25_a163_bounded_execution import" not in text
    assert "bounded_native_receipt.json" in text
    assert "candidate_tensor" in text
    assert "closed_loop_trajectory_sha256" in text


def test_new_runtime_paths_are_in_critical_manifest() -> None:
    required = {
        "camp_core/camp_core/integrations/diffusion_planner_v25_a163_bounded_authority.py",
        "scripts/integrations/create_diffusion_planner_v25_a163_bounded_release.py",
        "scripts/integrations/run_diffusion_planner_v25_a163_bounded_execution.py",
        "scripts/integrations/review_diffusion_planner_v25_a163_bounded_execution.py",
    }
    assert required.issubset(set(authority.CRITICAL_IMPLEMENTATION_PATHS))
