from __future__ import annotations

from contextlib import contextmanager
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
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
from scripts.integrations import review_diffusion_planner_v25_a163_bounded_execution as post_reviewer
from scripts.integrations import run_diffusion_planner_dp_camp_v21_native as native_runner


ROOT = Path(__file__).resolve().parents[2]
_TEST_EXECUTION_ASSETS = {"schema_version": "test_frozen_execution_assets_v1"}


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
        "execution_assets": copy.deepcopy(_TEST_EXECUTION_ASSETS),
        "execution_assets_sha256": canonical_sha256(_TEST_EXECUTION_ASSETS),
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
        "device": "cuda",
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
        "verify_frozen_execution_assets",
        lambda **kwargs: copy.deepcopy(_TEST_EXECUTION_ASSETS),
    )
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
    monkeypatch.setattr(
        authority,
        "EXPECTED_PROBE_TEMPLATE_SHA256",
        hashlib.sha256((tmp_path / "template.json").read_bytes()).hexdigest(),
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
        requested_device="cuda",
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
            requested_device="cuda",
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
            requested_device="cuda",
            consume=False,
        )


@pytest.mark.parametrize("requested_device", ["cpu", "", 0, None])
def test_release_rejects_non_cuda_device_before_nonce(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requested_device: object,
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    release = tmp_path / "release"
    root = _seal_release(release, decision)
    _patch_release_dependencies(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="CUDA"):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=output,
            current_pointer_head=decision["pointer_head_at_release"],
            dp_repo=dp_repo,
            probe_template=template,
            requested_device=requested_device,  # type: ignore[arg-type]
            consume=True,
        )
    assert not (tmp_path / "nonce-ledger").exists()


@pytest.mark.parametrize("alias_kind", ["relative", "dotdot"])
def test_release_rejects_output_text_alias_before_nonce(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias_kind: str
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    release = tmp_path / "release"
    root = _seal_release(release, decision)
    _patch_release_dependencies(monkeypatch, tmp_path)
    requested = (
        Path("bounded-output")
        if alias_kind == "relative"
        else output.parent / "alias-parent" / ".." / output.name
    )
    with pytest.raises(ValueError, match="output"):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=requested,
            current_pointer_head=decision["pointer_head_at_release"],
            dp_repo=dp_repo,
            probe_template=template,
            requested_device="cuda",
            consume=True,
        )
    assert not (tmp_path / "nonce-ledger").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX symlink semantics")
def test_release_rejects_output_symlink_alias_before_nonce(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    release = tmp_path / "release"
    root = _seal_release(release, decision)
    _patch_release_dependencies(monkeypatch, tmp_path)
    output.mkdir()
    alias = tmp_path / "bounded-output-alias"
    alias.symlink_to(output, target_is_directory=True)
    with pytest.raises(ValueError, match="output"):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=alias,
            current_pointer_head=decision["pointer_head_at_release"],
            dp_repo=dp_repo,
            probe_template=template,
            requested_device="cuda",
            consume=True,
        )
    assert not (tmp_path / "nonce-ledger").exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_count", 243),
        ("unique_identity_count", 245),
        ("full_r_execute_authorized", True),
        ("bounded_execute_authorized", False),
        ("fixed_dp_head", "0" * 40),
        ("run_nonce", 3),
        ("device", "cpu"),
        ("device", None),
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
            requested_device="cuda",
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
            requested_device="cuda",
            consume=False,
        )


@pytest.mark.parametrize("asset", ["template", "weights", "checkpoint", "args"])
def test_self_consistent_alternate_execution_assets_fail_closed_before_nonce(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, asset: str
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    decision["execution_assets"] = {
        "schema_version": "self_consistent_but_alternate",
        "asset": asset,
    }
    decision["execution_assets_sha256"] = canonical_sha256(
        decision["execution_assets"]
    )
    release = tmp_path / "release"
    root = _seal_release(release, decision)
    _patch_release_dependencies(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="asset|binding"):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=output,
            current_pointer_head=decision["pointer_head_at_release"],
            dp_repo=dp_repo,
            probe_template=template,
            requested_device="cuda",
            consume=True,
        )
    assert not (tmp_path / "nonce-ledger").exists()


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
        device="cuda",
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
                "status": "ok",
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
        native_receipt={
            "schema_version": "v21_native_arm_receipt_v1",
            "status": "ok",
            "arm": "camp",
            "claim_authorized": False,
            "ticks": ticks,
        },
    )
    assert evidence["candidate0_sha256_sequence"] == ["0" * 64] * 64
    assert evidence["k8_row_sha256_sequence"][0][7] == "7" * 64
    assert evidence["selected_index_sequence"] == [value % 8 for value in range(64)]
    assert len(evidence["closed_loop_trajectory_sha256"]) == 64
    assert len(evidence["speed_probe_sha256"]) == 64


def _minimal_post_review_tick() -> tuple[dict, dict, dict, dict, np.ndarray, np.ndarray]:
    candidate = np.zeros((8, 80, 4), dtype=np.float32)
    candidate[:, :, 2] = 1.0
    rows = [
        hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
        for value in candidate
    ]
    tensor_sha = hashlib.sha256(
        np.ascontiguousarray(candidate).tobytes()
    ).hexdigest()
    atoms = np.zeros((8, 14), dtype=np.float64)
    normalized_sha = hashlib.sha256(
        np.ascontiguousarray(atoms).tobytes()
    ).hexdigest()
    scenario_id = "1" * 64
    semantic_sha = "2" * 64
    source_row = {
        "scenario_id": scenario_id,
        "family": "lead_vehicle_hard_brake",
        "tier": "easy",
        "seed": 25001,
        "route_identity_sha256": "3" * 64,
        "source_map_sha256": "4" * 64,
        "source_class": "no_signal",
        "phase_authority_mode": None,
        "source_chain": {"semantic_clone_sha256": semantic_sha},
    }
    run = {
        "run_ordinal": 0,
        "occurrence": "identity0_first",
        "scenario_id": scenario_id,
    }
    payload = {
        "schema_version": post_reviewer.SNAPSHOT_SCHEMA_VERSION,
        "feature_payload": {
            "atom_matrix": atoms.tolist(),
            "source_valid_mask": [True] * 8,
            "atom_source_valid_mask": [[True] * 14 for _ in range(8)],
            "atom_applicable_mask": [
                [column not in (10, 12) for column in range(14)] for _ in range(8)
            ],
            "physical_feasible_mask": [False] * 8,
            "candidate_row_sha256": rows,
            "candidate_tensor": candidate.tolist(),
            "default_output": candidate[0].tolist(),
            "raw_context": {},
            "context_source_complete": {},
        },
        "sidecar": {
            "tick_index": 0,
            "dt_s": 0.1,
            "scenario_id": scenario_id,
            "family": source_row["family"],
            "tier": source_row["tier"],
            "parameter_block_id": "fixture",
            "route_identity_sha256": source_row["route_identity_sha256"],
            "corridor_group_sha256": "5" * 64,
            "map_family_id": "fixture-map",
            "source_map_sha256": source_row["source_map_sha256"],
            "seed": 25001,
            "candidate_tensor_sha256_before": tensor_sha,
            "candidate_tensor_sha256_after": tensor_sha,
            "default_output_sha256": rows[0],
            "candidate0_sha256": rows[0],
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "default_output_sha256": rows[0],
                "candidate0_sha256": rows[0],
                "native_ranked_k8": False,
            },
            "candidate0_semantics": "operational_default_alias_from_same_forward",
            "candidate0_independent_second_forward": False,
            "causal_input_sha256": "6" * 64,
            "physical_feasible_mask": [False] * 8,
            "source_valid_mask": [True] * 8,
            "all_k_high_risk": True,
            "selected_index": 0,
            "selected_trajectory_sha256": rows[0],
            "scores": [0.0] * 8,
            "score_contract": "score_k=clip(a_k/s,0,10)^T w",
            "tie_break_contract": "lowest_eligible_candidate_index",
            "normalized_atom_matrix_sha256": normalized_sha,
            "context_schema_version": "camp_dp_v25_causal_context_raw_v2",
            "context_source_receipt": {},
            "generation_behavior_scale_sha256": "7" * 64,
            "canonical_semantic_clone_sha256": semantic_sha,
            "route_signal_source_artifact_root_sha256": "8" * 64,
            "route_signal_source_row_sha256": post_reviewer._sha(source_row),
            "signal_source_class": "no_signal",
            "phase_authority_mode": None,
            "controlled_signal_source_receipt": {},
            "controlled_signal_tensor_evidence": None,
            "controlled_model_input_cache_receipt": {},
            "causal_signal_atom_input": {},
            "offline_label_provenance": "pending_train_only_causal_label",
            "outcome_fields_consumed": [],
            "fresh_b_opened": False,
            "run_ordinal": 0,
            "occurrence": "identity0_first",
        },
    }
    native = {"source_complete_mask": [True] * 8}
    return payload, run, source_row, native, np.ones(14), np.ones(14) / 14.0


def _patch_post_tick_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        post_reviewer,
        "_validate_signal_receipts",
        lambda **kwargs: {"current_phase": "none"},
    )
    monkeypatch.setattr(post_reviewer, "_validate_causal_signal", lambda **kwargs: {})
    monkeypatch.setattr(post_reviewer, "_validate_context", lambda **kwargs: None)
    monkeypatch.setattr(post_reviewer, "_validate_cache", lambda **kwargs: None)
    monkeypatch.setattr(
        post_reviewer,
        "_independent_red_stopping_oracle",
        lambda *args, **kwargs: np.zeros(8),
    )
    monkeypatch.setattr(
        post_reviewer, "_validate_native_cross_binding", lambda **kwargs: None
    )


def test_post_reviewer_accepts_nonempty_all_k_physically_bad_source_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_post_tick_dependencies(monkeypatch)
    payload, run, source_row, native, scales, weights = _minimal_post_review_tick()
    reviewed = post_reviewer._review_tick(
        payload=payload,
        run=run,
        tick_index=0,
        source_row=source_row,
        source_root_sha256="8" * 64,
        native_tick=native,
        scales=scales,
        weights=weights,
        scale_sha256="7" * 64,
    )
    assert reviewed["selected"] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        "all_source_false",
        "none_source_mask",
        "numeric_source_mask",
        "string_source_mask",
        "feature_sidecar_mismatch",
        "physical_not_source_subset",
        "bad_heading",
        "source_root_swap",
        "source_row_swap",
        "false_nonsignal_applicability",
        "speed_source_not_bound",
    ],
)
def test_post_reviewer_mask_and_fixed_k8_mutations_fail_closed(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    _patch_post_tick_dependencies(monkeypatch)
    payload, run, source_row, native, scales, weights = _minimal_post_review_tick()
    source_root = "8" * 64
    feature = payload["feature_payload"]
    sidecar = payload["sidecar"]
    if mutation == "all_source_false":
        feature["source_valid_mask"] = [False] * 8
        feature["atom_source_valid_mask"] = [[False] * 14 for _ in range(8)]
        sidecar["source_valid_mask"] = [False] * 8
        sidecar["all_k_high_risk"] = False
    elif mutation == "none_source_mask":
        feature["source_valid_mask"] = None
    elif mutation == "numeric_source_mask":
        feature["source_valid_mask"][0] = 1
    elif mutation == "string_source_mask":
        feature["source_valid_mask"][0] = "true"
    elif mutation == "feature_sidecar_mismatch":
        sidecar["source_valid_mask"][0] = False
    elif mutation == "physical_not_source_subset":
        feature["source_valid_mask"][0] = False
        feature["atom_source_valid_mask"][0] = [False] * 14
        sidecar["source_valid_mask"][0] = False
        feature["physical_feasible_mask"][0] = True
        sidecar["physical_feasible_mask"][0] = True
        sidecar["all_k_high_risk"] = False
    elif mutation == "bad_heading":
        feature["candidate_tensor"][0][0][2] = 0.0
    elif mutation == "source_root_swap":
        source_root = "9" * 64
    elif mutation == "false_nonsignal_applicability":
        feature["atom_applicable_mask"][0][0] = False
    elif mutation == "speed_source_not_bound":
        native["source_complete_mask"][0] = False
    else:
        source_row["scenario_id"] = "9" * 64
    with pytest.raises(ValueError):
        post_reviewer._review_tick(
            payload=payload,
            run=run,
            tick_index=0,
            source_row=source_row,
            source_root_sha256=source_root,
            native_tick=native,
            scales=scales,
            weights=weights,
            scale_sha256="7" * 64,
        )


def test_post_reviewer_accepts_route_speed_ineligible_candidate_with_exact_masks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_post_tick_dependencies(monkeypatch)
    payload, run, source_row, native, scales, weights = _minimal_post_review_tick()
    feature = payload["feature_payload"]
    sidecar = payload["sidecar"]
    native["source_complete_mask"][0] = False
    for column in range(4, 7):
        feature["atom_source_valid_mask"][0][column] = False
    feature["source_valid_mask"][0] = False
    sidecar["source_valid_mask"][0] = False
    sidecar["all_k_high_risk"] = False
    sidecar["selected_index"] = 1
    sidecar["selected_trajectory_sha256"] = feature["candidate_row_sha256"][1]
    reviewed = post_reviewer._review_tick(
        payload=payload,
        run=run,
        tick_index=0,
        source_row=source_row,
        source_root_sha256="8" * 64,
        native_tick=native,
        scales=scales,
        weights=weights,
        scale_sha256="7" * 64,
    )
    assert reviewed["selected"] == 1


def test_post_reviewer_independent_red_atom_oracle_detects_mutation() -> None:
    candidate = np.zeros((8, 80, 4), dtype=np.float64)
    candidate[:, :, 0] = np.linspace(0.0, 15.8, 80)
    candidate[:, :, 2] = 1.0
    causal = {
        "applicable": True,
        "stop_line_geometry_ego_m": [[10.0, -1.0], [10.0, 1.0]],
        "route_tangent_ego": [1.0, 0.0],
    }
    expected = post_reviewer._independent_red_stopping_oracle(candidate, causal, 0.1)
    assert np.all(expected > 0.0)
    mutated = expected.copy()
    mutated[0] += 1e-3
    assert not np.allclose(mutated, expected, rtol=0.0, atol=1e-12)


def _semantic_fixture(*, mapped: bool) -> dict:
    payload = {
        "schema_version": "camp_dp_v25_semantic_clone_payload_v3",
        "family": "red_light_phase_timing" if mapped else "lead_vehicle_hard_brake",
        "tier": "easy",
        "semantic_variant": "fixture",
        "parameters": {},
        "actors": [],
        "signal": {
            "current_phase": "none",
            "mapped_source_required": mapped,
            "source_mode": "no_v2i",
        },
        "route_polyline_local_m": [[float(index), 0.0] for index in range(64)],
    }
    if mapped:
        payload["stop_line_local_m"] = [[10.0, -1.0], [10.0, 1.0]]
    return payload


def _mapped_source_and_tick(phase: str = "red") -> tuple[dict, dict]:
    semantic = _semantic_fixture(mapped=True)
    stop = [[10.0, -1.0], [10.0, 1.0]]
    chain = {
        "schema_version": "camp_dp_v25_family_independent_mapped_signal_source_chain_v1",
        "scenario_id": "a" * 64,
        "route_identity_sha256": "b" * 64,
        "source_map_sha256": "c" * 64,
        "phase_authority_mode": "observe_same_tick_request",
        "expected_current_phase": None,
        "formal_phase": "none",
        "formal_mapped_source_required": False,
        "formal_route_mapped_traffic_light": True,
        "phase_remaining_available": False,
        "regulatory_element_ids": [101],
        "physical_light_ids": [201],
        "bulb_ids": [301, 302, 303],
        "controlled_lanelet_ids": [11],
        "route_lanelet_ids": [10, 11],
        "route_geometry_sha256": post_reviewer._sha(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        ),
        "stop_line_id": 401,
        "stop_line_geometry_m": stop,
        "stop_line_geometry_sha256": post_reviewer._sha(stop),
        "stop_line_route_distance_m": 0.01,
        "route_arc_m": 10.0,
        "route_length_m": 63.0,
        "route_tangent_world": [1.0, 0.0],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": post_reviewer._sha(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = post_reviewer._sha(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    column = {"green": 0, "yellow": 1, "red": 2}[phase]
    vector = [0.0] * 5
    vector[column] = 1.0
    route_rows = [{"lanelet_id": 11, "signal_channels_8_12": [vector] * 20}]
    map_rows = copy.deepcopy(route_rows)
    receipt = {
        "schema_version": "camp_dp_v25_family_independent_current_signal_receipt_v1",
        "scenario_id": chain["scenario_id"],
        "tick_index": 0,
        "phase_authority_mode": "observe_same_tick_request",
        "current_phase": phase,
        "decision_timestamp_s": 0.0,
        "source_timestamp_s": 0.0,
        "source_age_s": 0.0,
        "freshness": "same_tick",
        "source_id": "fixed_dp_current_request_route_map_signal_one_hot",
        "regulatory_element_id": 101,
        "physical_light_ids": [201],
        "bulb_ids": [301, 302, 303],
        "controlled_lanelet_ids": [11],
        "stop_line_id": 401,
        "stop_line_geometry_sha256": chain["stop_line_geometry_sha256"],
        "route_geometry_sha256": chain["route_geometry_sha256"],
        "route_arc_m": 10.0,
        "source_chain_sha256": chain["source_chain_sha256"],
        "observed_route_lanelet_ids": [11],
        "observed_map_lanelet_ids": [11],
        "route_signal_tensor_sha256": post_reviewer._sha(route_rows),
        "map_signal_tensor_sha256": post_reviewer._sha(map_rows),
        "phase_remaining_available": False,
        "source_valid": True,
        "applicable": phase == "red",
    }
    evidence = {
        "schema_version": "camp_dp_v25_production_signal_tensor_evidence_v2",
        "tick_index": 0,
        "decision_timestamp_s": 0.0,
        "source_timestamp_s": 0.0,
        "route_signal_rows": route_rows,
        "map_signal_rows": map_rows,
        "current_phase": phase,
        "route_signal_tensor_sha256": receipt["route_signal_tensor_sha256"],
        "map_signal_tensor_sha256": receipt["map_signal_tensor_sha256"],
        "future_schedule_consumed": False,
        "phase_remaining_available": False,
    }
    source_row = {
        "scenario_id": chain["scenario_id"],
        "formal_case_sha256": "d" * 64,
        "runner_eligible": True,
        "retention_role": "executable",
        "family": "red_light_phase_timing",
        "tier": "easy",
        "seed": 25001,
        "source_map_sha256": chain["source_map_sha256"],
        "route_identity_sha256": chain["route_identity_sha256"],
        "actual_mapped_signal": True,
        "id_free_tensor_layout": {},
        "source_class": "mapped_signal",
        "phase_authority_mode": "observe_same_tick_request",
        "source_chain": chain,
        "runtime_receipt": receipt,
        "tensor_evidence": evidence,
    }
    causal = {
        "schema_version": "camp_dp_v25_causal_signal_atom_input_v2",
        "source_state": "available",
        "source_valid": True,
        "applicable": phase == "red",
        "current_phase": phase,
        "decision_time_s": 0.0,
        "ego_position_world_m": [0.0, 0.0],
        "ego_heading_rad": 0.0,
        "regulatory_element_id": 101,
        "stop_line_id": 401,
        "stop_line_geometry_world_m": stop,
        "stop_line_geometry_ego_m": stop,
        "stop_line_geometry_sha256": chain["stop_line_geometry_sha256"],
        "route_tangent_world": [1.0, 0.0],
        "route_tangent_ego": [1.0, 0.0],
        "route_geometry_sha256": chain["route_geometry_sha256"],
        "route_arc_m": 10.0,
        "source_chain_sha256": chain["source_chain_sha256"],
        "runtime_receipt": receipt,
        "runtime_receipt_sha256": post_reviewer._sha(receipt),
    }
    sidecar = {
        "signal_source_class": "mapped_signal",
        "phase_authority_mode": "observe_same_tick_request",
        "controlled_signal_source_receipt": receipt,
        "controlled_signal_tensor_evidence": evidence,
        "causal_signal_atom_input": causal,
    }
    return source_row, sidecar


def _controlled_source_and_tick(
    *, expected_phase: str = "red", observed_phase: str = "red"
) -> tuple[dict, dict]:
    source_row, sidecar = _mapped_source_and_tick(observed_phase)
    chain = source_row["source_chain"]
    chain["phase_authority_mode"] = "controlled_same_tick_override"
    chain["expected_current_phase"] = expected_phase
    chain["formal_phase"] = expected_phase
    chain["formal_mapped_source_required"] = True
    chain["semantic_clone_payload"]["signal"]["current_phase"] = expected_phase
    chain["semantic_clone_payload"]["signal"]["mapped_source_required"] = True
    chain["semantic_clone_sha256"] = post_reviewer._sha(
        chain["semantic_clone_payload"]
    )
    chain["source_chain_sha256"] = post_reviewer._sha(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    source_row["phase_authority_mode"] = "controlled_same_tick_override"
    receipt = sidecar["controlled_signal_source_receipt"]
    receipt["phase_authority_mode"] = "controlled_same_tick_override"
    receipt["source_chain_sha256"] = chain["source_chain_sha256"]
    source_row["runtime_receipt"] = copy.deepcopy(receipt)
    source_row["tensor_evidence"] = copy.deepcopy(
        sidecar["controlled_signal_tensor_evidence"]
    )
    sidecar["phase_authority_mode"] = "controlled_same_tick_override"
    causal = sidecar["causal_signal_atom_input"]
    causal["source_chain_sha256"] = chain["source_chain_sha256"]
    causal["runtime_receipt"] = copy.deepcopy(receipt)
    causal["runtime_receipt_sha256"] = post_reviewer._sha(receipt)
    return source_row, sidecar


def test_post_reviewer_independently_validates_mapped_source_chain_and_red_input() -> None:
    source_row, sidecar = _mapped_source_and_tick("red")
    assert post_reviewer._validate_source_row(source_row) is source_row
    receipt = post_reviewer._validate_signal_receipts(
        sidecar=sidecar, source_row=source_row, tick_index=0
    )
    causal = post_reviewer._validate_causal_signal(
        sidecar=sidecar, source_row=source_row, receipt=receipt
    )
    assert causal["stop_line_geometry_sha256"] == source_row["source_chain"][
        "stop_line_geometry_sha256"
    ]


def test_post_reviewer_controlled_phase_is_bound_to_frozen_expected_phase() -> None:
    source_row, sidecar = _controlled_source_and_tick(
        expected_phase="red", observed_phase="red"
    )
    assert post_reviewer._validate_source_row(source_row) is source_row
    post_reviewer._validate_signal_receipts(
        sidecar=sidecar, source_row=source_row, tick_index=0
    )

    source_row, sidecar = _controlled_source_and_tick(
        expected_phase="red", observed_phase="green"
    )
    with pytest.raises(ValueError, match="same-tick|phase"):
        post_reviewer._validate_signal_receipts(
            sidecar=sidecar, source_row=source_row, tick_index=0
        )


def _mapped_native_source_context_fixture() -> tuple[dict, dict, dict, dict]:
    source_row, signal_sidecar = _mapped_source_and_tick("red")
    raw = {name: 0.0 for name in post_reviewer.RAW_CONTEXT_NAMES}
    raw["traffic_phase_red"] = 1.0
    complete = {name: True for name in post_reviewer.RAW_CONTEXT_NAMES}
    complete["traffic_signal_phase_remaining_s"] = False
    feature = {"raw_context": raw, "context_source_complete": complete}
    cache = {
        "schema_version": "camp_dp_v25_model_input_signal_cache_receipt_v1",
        "scenario_id": source_row["scenario_id"],
        "tick_index": 0,
        "signal_source_class": "mapped_signal",
        "phase_authority_mode": "observe_same_tick_request",
        "scene_map_tl_sha256": "1" * 64,
        "model_cache_tl_sha256_before": "1" * 64,
        "model_cache_tl_sha256_after": "1" * 64,
        "model_route_lanes_tl_sha256": "2" * 64,
        "cache_matches_scene_after": True,
        "observe_cache_unchanged": True,
        "sync_applied_before_tensor_conversion": True,
        "future_schedule_consumed": False,
        "phase_remaining_available": False,
    }
    sidecar = {
        **signal_sidecar,
        "controlled_model_input_cache_receipt": cache,
        "context_schema_version": "camp_dp_v25_causal_context_raw_v2",
        "context_source_receipt": {
            "mode": "no_v2i",
            "phase_remaining_available": False,
            "regulatory_signal_mapped": True,
        },
    }
    native = {
        "status": "ok",
        "controlled_scene": {
            "scenario_id": source_row["scenario_id"],
            "tick_index": 0,
            "sim_time_s": 0.0,
            "actor_count": 0,
            "actors": [],
            "signal": {
                "phase": "red",
                "source_row_count": 2,
                "applied": False,
                "source_receipt": copy.deepcopy(
                    sidecar["controlled_signal_source_receipt"]
                ),
                "tensor_evidence": copy.deepcopy(
                    sidecar["controlled_signal_tensor_evidence"]
                ),
            },
            "outcome_fields_consumed": [],
            "candidate_tensor_consumed": False,
            "selected_trajectory_consumed": False,
            "model_input_cache": copy.deepcopy(cache),
        },
        "v25_context": {
            "schema_version": sidecar["context_schema_version"],
            "raw_context": copy.deepcopy(raw),
            "source_complete": copy.deepcopy(complete),
            "source_receipt": copy.deepcopy(sidecar["context_source_receipt"]),
        },
    }
    return native, feature, sidecar, source_row


@pytest.mark.parametrize("mutation", ["receipt", "tensor", "cache", "context"])
def test_post_reviewer_native_mapped_source_context_is_exact(mutation: str) -> None:
    native, feature, sidecar, source_row = _mapped_native_source_context_fixture()
    post_reviewer._validate_native_source_context(
        native_tick=native,
        feature=feature,
        sidecar=sidecar,
        source_row=source_row,
        tick_index=0,
    )
    if mutation == "receipt":
        native["controlled_scene"]["signal"]["source_receipt"]["current_phase"] = "green"
    elif mutation == "tensor":
        native["controlled_scene"]["signal"]["tensor_evidence"]["current_phase"] = "green"
    elif mutation == "cache":
        native["controlled_scene"]["model_input_cache"]["scene_map_tl_sha256"] = "f" * 64
    else:
        native["v25_context"]["source_complete"]["ego_speed_mps"] = False
    with pytest.raises(ValueError, match="native"):
        post_reviewer._validate_native_source_context(
            native_tick=native,
            feature=feature,
            sidecar=sidecar,
            source_row=source_row,
            tick_index=0,
        )


@pytest.mark.parametrize(
    "mutation",
    ["timestamp", "phase", "tensor", "stopline", "route", "future", "missing"],
)
def test_post_reviewer_mapped_receipt_mutations_fail_closed(mutation: str) -> None:
    source_row, sidecar = _mapped_source_and_tick("red")
    receipt = sidecar["controlled_signal_source_receipt"]
    evidence = sidecar["controlled_signal_tensor_evidence"]
    if mutation == "timestamp":
        receipt["source_timestamp_s"] = 0.1
    elif mutation == "phase":
        evidence["current_phase"] = "green"
    elif mutation == "tensor":
        evidence["route_signal_rows"][0]["signal_channels_8_12"][0][2] = 0.0
    elif mutation == "stopline":
        receipt["stop_line_geometry_sha256"] = "e" * 64
    elif mutation == "route":
        receipt["route_geometry_sha256"] = "e" * 64
    elif mutation == "future":
        evidence["future_schedule"] = ["red", "green"]
    else:
        receipt.pop("freshness")
    with pytest.raises(ValueError):
        post_reviewer._validate_signal_receipts(
            sidecar=sidecar, source_row=source_row, tick_index=0
        )


def test_post_reviewer_context_rejects_phase_remaining_and_extra_fields() -> None:
    _, sidecar = _mapped_source_and_tick("green")
    sidecar["context_schema_version"] = "camp_dp_v25_causal_context_raw_v2"
    sidecar["context_source_receipt"] = {
        "mode": "no_v2i",
        "phase_remaining_available": False,
        "regulatory_signal_mapped": True,
    }
    raw = {name: 0.0 for name in post_reviewer.RAW_CONTEXT_NAMES}
    raw["traffic_phase_green"] = 1.0
    complete = {name: True for name in post_reviewer.RAW_CONTEXT_NAMES}
    complete["traffic_signal_phase_remaining_s"] = False
    feature = {"raw_context": raw, "context_source_complete": complete}
    receipt = sidecar["controlled_signal_source_receipt"]
    post_reviewer._validate_context(feature=feature, sidecar=sidecar, receipt=receipt)
    for mutation in ("phase_remaining", "extra", "numeric_source"):
        changed = copy.deepcopy(feature)
        if mutation == "phase_remaining":
            changed["raw_context"]["traffic_signal_phase_remaining_s"] = 1.0
        elif mutation == "extra":
            changed["raw_context"]["route_id"] = 1.0
        else:
            changed["context_source_complete"]["ego_speed_mps"] = 1
        with pytest.raises(ValueError):
            post_reviewer._validate_context(
                feature=changed, sidecar=sidecar, receipt=receipt
            )


def _native_cross_fixture() -> tuple[
    dict, dict, dict, dict, np.ndarray, np.ndarray, list[str], str
]:
    payload, _, source_row, _, scales, weights = _minimal_post_review_tick()
    feature = payload["feature_payload"]
    sidecar = payload["sidecar"]
    candidate = np.asarray(feature["candidate_tensor"], dtype=np.float32)
    atoms = np.asarray(feature["atom_matrix"], dtype=np.float64)
    normalized = np.clip(atoms / scales.reshape(1, 14), 0.0, 10.0)
    scores = normalized @ weights
    rows = feature["candidate_row_sha256"]
    tensor_sha = sidecar["candidate_tensor_sha256_before"]
    native = {
        "tick_index": 0,
        "status": "ok",
        "input_sha256": sidecar["causal_input_sha256"],
        "candidate_tensor_sha256_before": tensor_sha,
        "candidate_tensor_sha256_after": tensor_sha,
        "candidate_row_sha256": copy.deepcopy(rows),
        "default_output_sha256": rows[0],
        "selected_trajectory_sha256": rows[0],
        "selected_index": 0,
        "scores": scores.tolist(),
        "selection_policy": "v22_source_valid",
        "score_contract": "score_k=clip(a_k/s,0,10)^T w",
        "eligibility_mask_name": "source_valid_mask",
        "tie_break_contract": "lowest_eligible_candidate_index",
        "all_k_high_risk": True,
        "source_valid_mask": [True] * 8,
        "physical_feasible_mask": [False] * 8,
        "source_complete_mask": [True] * 8,
        "controlled_scene": {
            "scenario_id": source_row["scenario_id"],
            "tick_index": 0,
            "sim_time_s": 0.0,
            "actor_count": 0,
            "actors": [],
            "signal": {
                "phase": None,
                "source_row_count": 0,
                "applied": False,
                "source_receipt": copy.deepcopy(
                    sidecar["controlled_signal_source_receipt"]
                ),
            },
            "outcome_fields_consumed": [],
            "candidate_tensor_consumed": False,
            "selected_trajectory_consumed": False,
            "model_input_cache": copy.deepcopy(
                sidecar["controlled_model_input_cache_receipt"]
            ),
        },
        "v25_context": {
            "schema_version": sidecar["context_schema_version"],
            "raw_context": copy.deepcopy(feature["raw_context"]),
            "source_complete": copy.deepcopy(feature["context_source_complete"]),
            "source_receipt": copy.deepcopy(sidecar["context_source_receipt"]),
        },
        "default_candidate0_identity": copy.deepcopy(
            sidecar["default_candidate0_identity"]
        ),
        "atom_matrix_sha256": hashlib.sha256(
            np.ascontiguousarray(atoms).tobytes()
        ).hexdigest(),
        "normalized_atom_matrix_sha256": hashlib.sha256(
            np.ascontiguousarray(normalized).tobytes()
        ).hexdigest(),
    }
    return native, feature, sidecar, source_row, candidate, atoms, rows, tensor_sha


def test_native_public_tick_persists_status_controlled_scene_and_v25_context() -> None:
    native, _, _, _, _, _, rows, tensor_sha = _native_cross_fixture()
    internal = {
        "tick_index": 0,
        "status": "ok",
        "causal_input": {
            "input_sha256": "6" * 64,
            "observed_frames": 31,
            "padded_frames": 0,
            "padding_policy": "native_zero_left_pad_to_31_v1",
        },
        "tracker": {"status": "ok"},
        "_safety_record": {
            "position_xy": [0.0, 0.0],
            "ego_heading_rad": 0.0,
            "route_progress_m": 0.0,
            "speed_mps": 0.0,
        },
        "latency_ms": {"hook_total": 1.0},
        "default_output_sha256": rows[0],
        "candidate_tensor_sha256_before": tensor_sha,
        "candidate_tensor_sha256_after": tensor_sha,
        "candidate_neighbor_sha256": "7" * 64,
        "selected_trajectory_sha256": rows[0],
        "global_rng_sha256_before": "8" * 64,
        "global_rng_sha256_after": "8" * 64,
        "candidate_row_sha256": rows,
        "selection_policy": "v22_source_valid",
        "score_contract": "score_k=clip(a_k/s,0,10)^T w",
        "tie_break_contract": "lowest_eligible_candidate_index",
        "eligibility_mask_name": "source_valid_mask",
        "selected_index": 0,
        "default_candidate0_identity": native["default_candidate0_identity"],
        "source_valid_mask": [True] * 8,
        "physical_feasible_mask": [False] * 8,
        "source_complete_mask": [True] * 8,
        "scores": [0.0] * 8,
        "all_k_high_risk": True,
        "controlled_scene": native["controlled_scene"],
        "v25_context": native["v25_context"],
    }
    public = native_runner._public_tick_receipt(internal, "camp")
    assert public["status"] == "ok"
    assert public["controlled_scene"] == native["controlled_scene"]
    assert public["v25_context"] == native["v25_context"]


@pytest.mark.parametrize(
    "mutation",
    ["candidate", "atom", "score", "mask", "selected", "trajectory"],
)
def test_post_reviewer_native_snapshot_cross_binding_mutations_fail_closed(
    mutation: str,
) -> None:
    native, feature, sidecar, source_row, candidate, atoms, rows, tensor_sha = (
        _native_cross_fixture()
    )
    normalized = atoms.copy()
    scores = np.zeros(8, dtype=np.float64)
    if mutation == "candidate":
        native["candidate_row_sha256"][0] = "f" * 64
    elif mutation == "atom":
        native["atom_matrix_sha256"] = "f" * 64
    elif mutation == "score":
        native["scores"][0] = 1.0
    elif mutation == "mask":
        native["source_valid_mask"][0] = False
    elif mutation == "selected":
        native["selected_index"] = 1
    else:
        native["selected_trajectory_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="native/snapshot"):
        post_reviewer._validate_native_cross_binding(
            native_tick=native,
            tick_index=0,
            feature=feature,
            sidecar=sidecar,
            source_row=source_row,
            candidate=candidate,
            atoms=atoms,
            normalized=normalized,
            scores=scores,
            row_shas=rows,
            tensor_sha=tensor_sha,
        )


@pytest.mark.parametrize(
    "mutation",
    ["controlled_source", "controlled_cache", "v25_context", "native_status"],
)
def test_post_reviewer_native_source_context_mutations_fail_closed(
    mutation: str,
) -> None:
    native, feature, sidecar, source_row, candidate, atoms, rows, tensor_sha = (
        _native_cross_fixture()
    )
    if mutation == "controlled_source":
        native["controlled_scene"]["signal"]["source_receipt"]["source_valid"] = False
    elif mutation == "controlled_cache":
        native["controlled_scene"]["model_input_cache"]["future_schedule"] = []
    elif mutation == "v25_context":
        native["v25_context"]["raw_context"]["route_id"] = 7.0
    else:
        native["status"] = "failed"
    with pytest.raises(ValueError, match="native"):
        post_reviewer._validate_native_cross_binding(
            native_tick=native,
            tick_index=0,
            feature=feature,
            sidecar=sidecar,
            source_row=source_row,
            candidate=candidate,
            atoms=atoms,
            normalized=atoms.copy(),
            scores=np.zeros(8, dtype=np.float64),
            row_shas=rows,
            tensor_sha=tensor_sha,
        )


@pytest.mark.parametrize("mutation", ["top_status", "tick_status", "error", "future"])
def test_post_reviewer_derives_native_failure_and_rejects_unknown_fields(
    mutation: str,
) -> None:
    native, _, _, _, _, _, _, _ = _native_cross_fixture()
    receipt = {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "arm": "camp",
        "claim_authorized": False,
        "ticks": [copy.deepcopy(native) for _ in range(64)],
    }
    if mutation == "top_status":
        receipt["status"] = "failed"
        assert post_reviewer._derive_native_failure_class(receipt) == "native_receipt_failed"
    elif mutation == "tick_status":
        receipt["ticks"][0]["status"] = "failed"
        assert post_reviewer._derive_native_failure_class(receipt) == "native_tick_failed"
    elif mutation == "error":
        receipt["ticks"][0]["error_message"] = "synthetic"
        with pytest.raises(ValueError, match="failure field"):
            post_reviewer._derive_native_failure_class(receipt)
    else:
        receipt["ticks"][0]["future_schedule"] = []
        with pytest.raises(ValueError, match="future field"):
            post_reviewer._derive_native_failure_class(receipt)


def test_post_reviewer_cache_schema_and_mode_are_exact() -> None:
    source_row, _ = _mapped_source_and_tick("green")
    digest = "9" * 64
    sidecar = {
        "controlled_model_input_cache_receipt": {
            "schema_version": "camp_dp_v25_model_input_signal_cache_receipt_v1",
            "scenario_id": source_row["scenario_id"],
            "tick_index": 0,
            "signal_source_class": "mapped_signal",
            "phase_authority_mode": "observe_same_tick_request",
            "scene_map_tl_sha256": digest,
            "model_cache_tl_sha256_before": digest,
            "model_cache_tl_sha256_after": digest,
            "model_route_lanes_tl_sha256": "8" * 64,
            "cache_matches_scene_after": True,
            "observe_cache_unchanged": True,
            "sync_applied_before_tensor_conversion": True,
            "future_schedule_consumed": False,
            "phase_remaining_available": False,
        }
    }
    post_reviewer._validate_cache(sidecar=sidecar, source_row=source_row, tick_index=0)
    for mutation in ("missing", "extra", "mismatch"):
        changed = copy.deepcopy(sidecar)
        cache = changed["controlled_model_input_cache_receipt"]
        if mutation == "missing":
            cache.pop("model_route_lanes_tl_sha256")
        elif mutation == "extra":
            cache["future_schedule"] = []
        else:
            cache["model_cache_tl_sha256_after"] = "7" * 64
        with pytest.raises(ValueError):
            post_reviewer._validate_cache(
                sidecar=changed, source_row=source_row, tick_index=0
            )


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
                "cuda",
                "--bounded-execute",
            ]
        )
    assert (output / "run.exit").read_bytes() == b"1\n"
    assert verify_complete_seal(output)["file_count"] == 2


@pytest.mark.skipif(os.name != "posix", reason="Linux flock integration")
def test_bounded_runner_exclusive_lock_rejects_second_process_and_releases(
    tmp_path: Path,
) -> None:
    lock_path = tmp_path / "bounded.lock"
    probe = (
        "import fcntl,sys; "
        "p=open(sys.argv[1],'a+'); "
        "\ntry: fcntl.flock(p.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)"
        "\nexcept BlockingIOError: raise SystemExit(23)"
    )
    with runner._exclusive_lock(lock_path):
        blocked = subprocess.run([sys.executable, "-c", probe, str(lock_path)])
        assert blocked.returncode == 23
    released = subprocess.run([sys.executable, "-c", probe, str(lock_path)])
    assert released.returncode == 0


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
