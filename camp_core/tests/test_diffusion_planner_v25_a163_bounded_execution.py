from __future__ import annotations

from contextlib import contextmanager
import copy
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import random
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
from camp_core.integrations.diffusion_planner_v21_native import (
    deterministic_array_mapping_sha256 as native_array_mapping_sha256,
)
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
from camp_core.integrations.diffusion_planner_v25_causal_evidence_store import (
    ARRAY_CONTRACT,
    LOGICAL_SCHEMA_VERSION,
    externalize_causal_evidence,
)
from camp_core.integrations.diffusion_planner_v25_snapshot_store import (
    SNAPSHOT_SUFFIX,
    encode_snapshot,
)
from scripts.integrations import run_diffusion_planner_v25_a163_bounded_execution as runner
from scripts.integrations import review_diffusion_planner_v25_a163_bounded_execution as post_reviewer
from scripts.integrations import run_diffusion_planner_dp_camp_v21_native as native_runner
from scripts.integrations import create_diffusion_planner_v25_a163_bounded_release as release_creator


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
                "source_class": "no_signal",
                "phase_authority_mode": None,
                "family": "lead_vehicle_hard_brake",
                "tier": "easy",
                "route_identity_sha256": "4" * 64,
                "source_map_sha256": "5" * 64,
                "corridor_group_sha256": "6" * 64,
                "semantic_clone_sha256": "7" * 64,
                "source_row_sha256": "8" * 64,
                "k8_relevant_physical_payload_sha256": "9" * 64,
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
    (root / "HEADS").write_bytes(
        (
            f"camp_source_head={decision['implementation_source_head']}\n"
            f"camp_pointer_head={decision['pointer_head_at_release']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (root / "COMMAND").write_bytes(b"test\n")
    (root / "run.exit").write_bytes(b"0\n")
    return seal_artifact(root, label="test bounded release")


def _write_static_root(
    root: Path, *, payloads: dict[str, object], heads: bytes
) -> str:
    root.mkdir()
    for name, payload in payloads.items():
        (root / name).write_bytes(authority.canonical_json_bytes(payload))
    (root / "HEADS").write_bytes(heads)
    (root / "COMMAND").write_bytes(b"diagnostic-only\n")
    (root / "run.exit").write_bytes(b"0\n")
    return seal_artifact(root, label="test static bounded authority")


def _four_root_chain(
    tmp_path: Path, *, source_head: str = "1" * 40
) -> tuple[dict[str, dict[str, str]], dict]:
    source_dir = (tmp_path / "source").resolve()
    source_root = _write_static_root(
        source_dir,
        payloads={
            "formal_route_source_contract_supplement.json": {},
            "route_signal_source_receipts.json": {},
            "report.json": {
                "status": authority.SOURCE_STATUS,
                "authority": {
                    "camp_source_head": source_head,
                    "fixed_dp_head": FIXED_DP_HEAD,
                },
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        },
        heads=(
            f"camp_source_head={source_head}\nfixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii"),
    )
    source_review_dir = (tmp_path / "source_review").resolve()
    source_review_root = _write_static_root(
        source_review_dir,
        payloads={
            "report.json": {
                "status": authority.SOURCE_REVIEW_STATUS,
                "camp_source_head": source_head,
                "fixed_dp_head": FIXED_DP_HEAD,
                "reviewed_root_sha256": source_root,
                "reviewed_artifact": str(source_dir),
            }
        },
        heads=(
            f"review_head={source_head}\nfixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii"),
    )
    plan = _plan()
    plan_dir = (tmp_path / "bounded_plan").resolve()
    plan_root = _write_static_root(
        plan_dir,
        payloads={
            "bounded_execution_plan.json": plan,
            "report.json": {
                "status": authority.PLAN_STATUS,
                "camp_source_head": source_head,
                "fixed_dp_head": FIXED_DP_HEAD,
                "source_root_sha256": source_root,
                "source_review_root_sha256": source_review_root,
                "plan_sha256": canonical_sha256(plan),
            },
        },
        heads=(
            f"camp_source_head={source_head}\nfixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii"),
    )
    plan_review_dir = (tmp_path / "bounded_plan_review").resolve()
    plan_review_root = _write_static_root(
        plan_review_dir,
        payloads={
            "report.json": {
                "status": authority.PLAN_REVIEW_STATUS,
                "review_head": source_head,
                "fixed_dp_head": FIXED_DP_HEAD,
                "reviewed_root_sha256": plan_root,
                "reviewed_artifact": str(plan_dir),
                "source_root_sha256": source_root,
                "source_review_root_sha256": source_review_root,
            }
        },
        heads=(
            f"review_head={source_head}\nfixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii"),
    )
    roots = {
        "source": source_root,
        "source_review": source_review_root,
        "bounded_plan": plan_root,
        "bounded_plan_review": plan_review_root,
    }
    bindings = {
        role: {
            "path": str((tmp_path / role).resolve()),
            "root_sha256": roots[role],
            "report_file": "report.json",
        }
        for role in authority.ROOT_ROLES
    }
    return bindings, plan


def test_four_root_chain_rejects_resealed_noncanonical_plan_bytes(
    tmp_path: Path,
) -> None:
    bindings, plan = _four_root_chain(tmp_path)
    authority.verify_four_root_chain(
        bindings=bindings,
        implementation_source_head="1" * 40,
        fixed_dp_head=FIXED_DP_HEAD,
    )
    plan_path = tmp_path / "bounded_plan" / "bounded_execution_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    bindings["bounded_plan"]["root_sha256"] = seal_artifact(
        tmp_path / "bounded_plan", label="resealed noncanonical plan"
    )
    with pytest.raises(ValueError, match="canonical single-LF"):
        authority.verify_four_root_chain(
            bindings=bindings,
            implementation_source_head="1" * 40,
            fixed_dp_head=FIXED_DP_HEAD,
        )


@pytest.mark.parametrize(
    "payload_name",
    [
        "formal_route_source_contract_supplement.json",
        "route_signal_source_receipts.json",
    ],
)
def test_four_root_chain_strictly_opens_every_source_json_payload(
    tmp_path: Path, payload_name: str
) -> None:
    bindings, _ = _four_root_chain(tmp_path)
    source_path = tmp_path / "source" / payload_name
    source_path.write_bytes(b'{"value":1,"value":2}\n')
    bindings["source"]["root_sha256"] = seal_artifact(
        tmp_path / "source", label="resealed strict source JSON mutation"
    )
    with pytest.raises(ValueError, match="strict UTF-8 JSON"):
        authority.verify_four_root_chain(
            bindings=bindings,
            implementation_source_head="1" * 40,
            fixed_dp_head=FIXED_DP_HEAD,
        )


def _patch_release_dependencies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(authority, "NONCE_LEDGER", tmp_path / "nonce-ledger")
    monkeypatch.setattr(
        authority, "A17_DIAGNOSTIC_NONCE_LEDGER", tmp_path / "a17-nonce-ledger"
    )
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


def test_a17_diagnostic_release_is_exact_identity0_and_non_scientific(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dp_repo = tmp_path / "dp"
    dp_repo.mkdir()
    template = tmp_path / "template.json"
    template.write_text("{}\n", encoding="utf-8")
    output = (tmp_path / "a17-diagnostic-output").resolve()
    roots = {
        role: {
            "path": str((tmp_path / role).resolve()),
            "root_sha256": "b" * 64,
            "report_file": "report.json",
        }
        for role in authority.ROOT_ROLES
    }
    manifest = {"critical.py": "a" * 64}
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
        authority, "build_critical_implementation_manifest", lambda repo: manifest
    )
    monkeypatch.setattr(
        authority,
        "_git",
        lambda repo, *args: FIXED_DP_HEAD
        if args == ("rev-parse", "HEAD")
        else "",
    )
    monkeypatch.setattr(
        authority,
        "EXPECTED_PROBE_TEMPLATE_SHA256",
        hashlib.sha256(template.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(
        authority, "A17_DIAGNOSTIC_NONCE_LEDGER", tmp_path / "a17-nonce-ledger"
    )
    decision = authority.build_a17_diagnostic_release_decision(
        repo=ROOT,
        implementation_source_head="1" * 40,
        pointer_head_at_release="2" * 40,
        root_artifacts=roots,
        run_nonce="c" * 64,
        authorized_output_dir=str(output),
        dp_repo=dp_repo,
        probe_template=template,
    )
    assert set(decision) == authority.A17_DIAGNOSTIC_RELEASE_FIELDS
    assert decision["diagnostic_run"] == _plan()["runs"][0]
    assert decision["unique_identity_count"] == 1
    assert decision["run_count"] == 1
    assert decision["snapshot_capacity"] == 64
    assert decision["diagnostic_execute_authorized"] is True
    assert decision["bounded_execute_authorized"] is False
    assert decision["accepted_as_scientific_evidence"] is False
    selected = authority.build_a17_diagnostic_release_decision(
        repo=ROOT,
        implementation_source_head="1" * 40,
        pointer_head_at_release="2" * 40,
        root_artifacts=roots,
        run_nonce="d" * 64,
        authorized_output_dir=str((tmp_path / "a17-selected-output").resolve()),
        dp_repo=dp_repo,
        probe_template=template,
        diagnostic_run_ordinal=155,
    )
    assert selected["diagnostic_run"] == _plan()["runs"][155]
    for invalid in (True, -1, EXPECTED_RUNS):
        with pytest.raises(ValueError, match="diagnostic run ordinal"):
            authority.build_a17_diagnostic_release_decision(
                repo=ROOT,
                implementation_source_head="1" * 40,
                pointer_head_at_release="2" * 40,
                root_artifacts=roots,
                run_nonce="e" * 64,
                authorized_output_dir=str((tmp_path / "a17-invalid-output").resolve()),
                dp_repo=dp_repo,
                probe_template=template,
                diagnostic_run_ordinal=invalid,
            )
    release = tmp_path / "a17-release"
    root = _seal_release(release, decision)
    verified = authority.verify_a17_diagnostic_release(
        repo=ROOT,
        release_artifact=release,
        release_root_sha256=root,
        requested_output_dir=str(output),
        current_pointer_head="2" * 40,
        dp_repo=dp_repo,
        probe_template=template,
        requested_device="cuda",
        consume=True,
    )
    assert verified["plan"] == {"runs": [_plan()["runs"][0]]}
    assert verified["nonce_marker"] is not None


def _candidate_evidence_fixture() -> tuple[np.ndarray, dict[str, object]]:
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[:, :, 0] = np.arange(8, dtype=np.float32)[:, None]
    candidates[:, :, 1] = np.arange(80, dtype=np.float32)[None, :]
    candidates[:, :, 2] = 1.0
    tensor_sha = native_runner.array_sha256(candidates)
    rows = [native_runner.array_sha256(candidates[index]) for index in range(8)]
    return candidates, {
        "candidate_tensor_sha256": tensor_sha,
        "candidate_row_sha256": rows,
        "default_output_sha256": rows[0],
        "default_candidate0_identity": {
            "elementwise_equal": True,
            "max_abs_difference": 0.0,
            "default_output_sha256": rows[0],
            "candidate0_sha256": rows[0],
            "native_ranked_k8": False,
        },
    }


def test_candidate_prematerialization_evidence_survives_heading_failure_seal(
    tmp_path: Path,
) -> None:
    candidates, metadata = _candidate_evidence_fixture()
    candidates[3, 17, 2:4] = 0.0
    metadata["candidate_tensor_sha256"] = native_runner.array_sha256(candidates)
    metadata["candidate_row_sha256"] = [
        native_runner.array_sha256(candidates[index]) for index in range(8)
    ]
    path = runner._write_candidate_prematerialization_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 155, "occurrence": "unique_identity"},
        tick_index=0,
        candidates=candidates,
        metadata=metadata,
    )
    record = runner._load_canonical_json(path)
    assert record["run_ordinal"] == 155
    assert record["heading_norm_min"] == 0.0
    assert record["heading_norm_below_half_count"] == 1
    assert record["accepted_as_scientific_evidence"] is False
    tensor_path = tmp_path / record["candidate_tensor_relative_path"]
    assert np.array_equal(np.load(tensor_path, allow_pickle=False), candidates)
    root = seal_artifact(tmp_path, label="A1.7 candidate boundary failure fixture")
    seal = verify_complete_seal(
        tmp_path, root, label="A1.7 candidate boundary failure fixture"
    )
    assert path.relative_to(tmp_path).as_posix() in seal["manifest_paths"]
    assert tensor_path.relative_to(tmp_path).as_posix() in seal["manifest_paths"]


@pytest.mark.parametrize("mutation", ["missing", "extra", "dtype", "shape", "row_sha"])
def test_candidate_prematerialization_evidence_contract_fail_closed(
    tmp_path: Path, mutation: str
) -> None:
    candidates, metadata = _candidate_evidence_fixture()
    if mutation == "missing":
        metadata.pop("default_output_sha256")
    elif mutation == "extra":
        metadata["future_outcome"] = None
    elif mutation == "dtype":
        candidates = candidates.astype(np.float64)
    elif mutation == "shape":
        candidates = candidates[:, :-1]
    else:
        metadata["candidate_row_sha256"][1] = "f" * 64
    with pytest.raises(ValueError, match="candidate evidence"):
        runner._write_candidate_prematerialization_evidence(
            output_dir=tmp_path,
            run={"run_ordinal": 155, "occurrence": "unique_identity"},
            tick_index=0,
            candidates=candidates,
            metadata=metadata,
        )


def test_preprojection_mapping_digest_preserves_native_zero_dimensional_shape() -> None:
    value = {
        "matrix": np.arange(6, dtype=np.float32).reshape(2, 3)[:, ::-1],
        "version": np.asarray(7, dtype=np.int64),
    }
    assert value["version"].shape == ()
    assert runner._deterministic_array_mapping_sha256(value) == (
        native_array_mapping_sha256(value)
    )


@pytest.mark.parametrize("asset_kind", ["probe_template", "fixed_dp_args"])
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b'{"a":1,"a":2}\n', "strict UTF-8 JSON"),
        (b'{"a":NaN}\n', "strict UTF-8 JSON"),
        (b'{"a":"\xff"}\n', "strict UTF-8 JSON"),
        (b'[1,2,3]\n', "exact object"),
    ],
)
def test_frozen_legacy_probe_loader_rejects_invalid_json_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
    expected: str,
    asset_kind: str,
) -> None:
    probe = (tmp_path / "legacy-probe.json").resolve()
    probe.write_bytes(raw)
    if asset_kind == "probe_template":
        monkeypatch.setattr(authority, "EXPECTED_PROBE_TEMPLATE", probe)
        monkeypatch.setattr(
            authority,
            "EXPECTED_PROBE_TEMPLATE_SHA256",
            hashlib.sha256(raw).hexdigest(),
        )
    else:
        monkeypatch.setattr(
            authority,
            "EXPECTED_FIXED_DP_ARGS",
            {"path": str(probe), "sha256": hashlib.sha256(raw).hexdigest()},
        )
    with pytest.raises(ValueError, match=expected):
        authority._load_frozen_external_legacy_json_object(
            probe, asset_kind=asset_kind
        )


@pytest.mark.parametrize("asset_kind", ["probe_template", "fixed_dp_args"])
def test_frozen_legacy_probe_loader_rejects_alternate_path_or_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, asset_kind: str
) -> None:
    raw = b'{"a":1}\n'
    probe = (tmp_path / "legacy-probe.json").resolve()
    alternate = (tmp_path / "alternate.json").resolve()
    probe.write_bytes(raw)
    alternate.write_bytes(raw)
    if asset_kind == "probe_template":
        monkeypatch.setattr(authority, "EXPECTED_PROBE_TEMPLATE", probe)
        monkeypatch.setattr(
            authority,
            "EXPECTED_PROBE_TEMPLATE_SHA256",
            hashlib.sha256(raw).hexdigest(),
        )
    else:
        monkeypatch.setattr(
            authority,
            "EXPECTED_FIXED_DP_ARGS",
            {"path": str(probe), "sha256": hashlib.sha256(raw).hexdigest()},
        )
    with pytest.raises(ValueError, match="canonical path"):
        authority._load_frozen_external_legacy_json_object(
            alternate, asset_kind=asset_kind
        )
    if asset_kind == "probe_template":
        monkeypatch.setattr(authority, "EXPECTED_PROBE_TEMPLATE_SHA256", "0" * 64)
    else:
        monkeypatch.setattr(
            authority,
            "EXPECTED_FIXED_DP_ARGS",
            {"path": str(probe), "sha256": "0" * 64},
        )
    with pytest.raises(ValueError, match="bytes drifted"):
        authority._load_frozen_external_legacy_json_object(
            probe, asset_kind=asset_kind
        )


@pytest.mark.parametrize("asset_kind", ["probe_template", "fixed_dp_args"])
def test_registered_external_legacy_json_object_accepts_precanonical_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, asset_kind: str
) -> None:
    raw = b'{\n  "b": 2,\n  "a": 1\n}\n'
    asset = (tmp_path / f"{asset_kind}.json").resolve()
    asset.write_bytes(raw)
    contract = {"path": str(asset), "sha256": hashlib.sha256(raw).hexdigest()}
    if asset_kind == "probe_template":
        monkeypatch.setattr(authority, "EXPECTED_PROBE_TEMPLATE", asset)
        monkeypatch.setattr(
            authority, "EXPECTED_PROBE_TEMPLATE_SHA256", contract["sha256"]
        )
    else:
        monkeypatch.setattr(authority, "EXPECTED_FIXED_DP_ARGS", contract)
    assert authority._load_frozen_external_legacy_json_object(
        asset, asset_kind=asset_kind
    ) == {"a": 1, "b": 2}


@pytest.mark.skipif(
    not authority.EXPECTED_DP_REPO.is_dir()
    or not authority.EXPECTED_PROBE_TEMPLATE.is_file(),
    reason="canonical fixed-DP and legacy probe assets are available only on AutoDL",
)
def test_real_create_entry_accepts_exact_precanonical_legacy_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    bindings, _ = _four_root_chain(tmp_path, source_head=head)
    release = (tmp_path / "sealed-release").resolve()
    authorized_output = (tmp_path / "authorized-output").resolve()
    run_nonce = "7" * 64
    argv = [
        "--implementation-source-head",
        head,
        "--pointer-head-at-release",
        head,
        "--run-nonce",
        run_nonce,
        "--authorized-output-dir",
        str(authorized_output),
        "--dp-repo",
        str(authority.EXPECTED_DP_REPO),
        "--probe-template",
        str(authority.EXPECTED_PROBE_TEMPLATE),
    ]
    for role in authority.ROOT_ROLES:
        binding = bindings[role]
        argv.extend(
            [
                f"--{role.replace('_', '-')}-artifact",
                binding["path"],
                f"--{role.replace('_', '-')}-root-sha256",
                binding["root_sha256"],
            ]
        )
    argv.extend(["--output-dir", str(release)])
    monkeypatch.setattr(sys, "argv", [str(release_creator.__file__), *argv])
    release_creator.main(argv)
    emitted = json.loads(capsys.readouterr().out)
    seal = verify_complete_seal(release, emitted["artifact_root_sha256"])
    assert seal["manifest_paths"] == authority.RELEASE_PAYLOADS
    decision = json.loads((release / "decision.json").read_text(encoding="utf-8"))
    assert decision["probe_template"] == str(authority.EXPECTED_PROBE_TEMPLATE)
    assert decision["probe_template_sha256"] == authority.EXPECTED_PROBE_TEMPLATE_SHA256
    nonce_marker = authority.NONCE_LEDGER / (
        f"v25_{authority.RELEASE_GATE}_{run_nonce}.consumed.json"
    )
    assert not nonce_marker.exists()


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
        requested_output_dir=str(output),
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
            requested_output_dir=str(output),
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
            requested_output_dir=str(tmp_path / "alternate"),
            current_pointer_head=decision["pointer_head_at_release"],
            dp_repo=dp_repo,
            probe_template=template,
            requested_device="cuda",
            consume=False,
        )


def test_archived_release_review_binds_historical_producer_and_review_only_delta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    decision["probe_template_sha256"] = (
        post_reviewer.EXPECTED_PROBE_TEMPLATE_SHA256
    )
    release = tmp_path / "archived-release"
    root = _seal_release(release, decision)
    review_head = "4" * 40
    monkeypatch.setattr(
        post_reviewer,
        "_historical_critical_manifest",
        lambda repo, head: copy.deepcopy(decision["critical_implementation_manifest"]),
    )
    deltas = {
        (decision["implementation_source_head"], decision["pointer_head_at_release"]): [],
        (decision["pointer_head_at_release"], review_head): [
            "scripts/integrations/review_diffusion_planner_v25_a163_bounded_execution.py",
            "camp_core/tests/test_diffusion_planner_v25_a163_bounded_execution.py",
        ],
    }
    monkeypatch.setattr(
        post_reviewer,
        "_changed_paths",
        lambda repo, start, end: list(deltas[(start, end)]),
    )
    monkeypatch.setattr(
        post_reviewer.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=b"", stderr=b""),
    )
    monkeypatch.setattr(
        post_reviewer.bounded_authority,
        "verify_frozen_execution_assets",
        lambda **kwargs: copy.deepcopy(decision["execution_assets"]),
    )
    monkeypatch.setattr(
        post_reviewer.bounded_authority,
        "verify_four_root_chain",
        lambda **kwargs: {"plan": _plan()},
    )

    verified = post_reviewer._verify_archived_bounded_release_for_review(
        repo=ROOT,
        review_head=review_head,
        release_artifact=release,
        release_root_sha256=root,
        requested_output_dir=str(output),
        dp_repo=dp_repo,
        probe_template=template,
    )
    assert verified["producer_pointer_head"] == decision["pointer_head_at_release"]
    assert verified["review_head"] == review_head
    assert verified["review_only_changed_paths"] == deltas[
        (decision["pointer_head_at_release"], review_head)
    ]

    deltas[(decision["pointer_head_at_release"], review_head)].append(
        "scripts/integrations/run_diffusion_planner_v25_a163_bounded_execution.py"
    )
    with pytest.raises(ValueError, match="review-only"):
        post_reviewer._verify_archived_bounded_release_for_review(
            repo=ROOT,
            review_head=review_head,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=str(output),
            dp_repo=dp_repo,
            probe_template=template,
        )


@pytest.mark.parametrize(
    "raw_builder",
    [
        lambda payload: (json.dumps(payload, indent=2) + "\n").encode("utf-8"),
        lambda payload: b'{"schema_version":"first","schema_version":"second"}\n',
    ],
)
def test_bounded_release_rejects_resealed_noncanonical_or_duplicate_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_builder,
) -> None:
    decision, dp_repo, template, output = _decision(tmp_path)
    release = tmp_path / "release"
    _seal_release(release, decision)
    (release / "decision.json").write_bytes(raw_builder(decision))
    root = seal_artifact(release, label="resealed release byte mutation")
    _patch_release_dependencies(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="strict UTF-8|canonical single-LF"):
        verify_bounded_release(
            repo=ROOT,
            release_artifact=release,
            release_root_sha256=root,
            requested_output_dir=str(output),
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
            requested_output_dir=str(output),
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
            requested_output_dir=str(requested),
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
            requested_output_dir=str(alias),
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
            requested_output_dir=str(output),
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
            requested_output_dir=str(output),
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
            requested_output_dir=str(output),
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
        output_dir=str(tmp_path / "output"),
        release_artifact=tmp_path / "release",
        release_root_sha256="1" * 64,
        probe_template=tmp_path / "template",
        device="cuda",
    )
    with pytest.raises(ValueError, match="authority blocked"):
        runner._run(args)
    assert model_called is False
    assert not Path(args.output_dir).exists()


@pytest.mark.parametrize("alias_kind", ["dot", "duplicate", "trailing"])
def test_runner_rejects_raw_output_alias_before_authority_or_nonce(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias_kind: str
) -> None:
    canonical = str(tmp_path / "bounded-output")
    if alias_kind == "dot":
        raw = str(tmp_path) + os.sep + "." + os.sep + "bounded-output"
    elif alias_kind == "duplicate":
        raw = str(tmp_path) + os.sep + os.sep + "bounded-output"
    else:
        raw = canonical + os.sep
    called = False

    def authority_call(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("authority must not see aliased output text")

    monkeypatch.setattr(runner, "verify_bounded_release", authority_call)
    args = SimpleNamespace(
        dp_repo=tmp_path / "dp",
        output_dir=raw,
        release_artifact=tmp_path / "release",
        release_root_sha256="1" * 64,
        probe_template=tmp_path / "template",
        device="cuda",
    )
    with pytest.raises(ValueError, match="canonical"):
        runner._run(args)
    assert called is False
    assert not Path(canonical).exists()


def test_bounded_snapshot_index_carries_repeat_occurrence(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    stream = io.StringIO()
    run = _plan()["runs"][-1]
    payload = {
        "schema_version": "old",
        "feature_payload": {
            "causal_evidence": {
                "schema_version": LOGICAL_SCHEMA_VERSION,
                **{
                    name: np.zeros(shape, dtype=dtype).tolist()
                    for name, (shape, dtype) in ARRAY_CONTRACT.items()
                },
            }
        },
        "sidecar": {},
    }
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


def test_run_evidence_is_derived_from_raw_snapshots_and_native_ticks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    scene_hashes = [f"{tick_index:064x}" for tick_index in range(64)]
    config = {"routes": [{"name": "route"}]}
    route = config["routes"][0]
    native_dir = tmp_path / "native"
    derived_inputs: dict[str, object] = {}

    def derive_failure_class(receipt: dict, **kwargs: object) -> str:
        derived_inputs["receipt"] = receipt
        derived_inputs.update(kwargs)
        return "none"

    monkeypatch.setattr(
        runner, "_derive_native_failure_class", derive_failure_class
    )
    native_receipt = {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "arm": "camp",
        "claim_authorized": False,
        "ticks": ticks,
    }
    evidence = runner.build_run_evidence(
        run=run,
        payloads=payloads,
        native_receipt=native_receipt,
        scene_materialization_hashes=scene_hashes,
        config=config,
        route=route,
        native_dir=native_dir,
    )
    assert evidence["candidate0_sha256_sequence"] == ["0" * 64] * 64
    assert evidence["k8_row_sha256_sequence"][0][7] == "7" * 64
    assert evidence["selected_index_sequence"] == [value % 8 for value in range(64)]
    assert len(evidence["closed_loop_trajectory_sha256"]) == 64
    assert len(evidence["speed_probe_sha256"]) == 64
    assert evidence["failure_class"] == "none"
    assert derived_inputs == {
        "receipt": native_receipt,
        "scene_materialization_hashes": scene_hashes,
        "config": config,
        "route": route,
        "native_dir": native_dir,
    }


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
            "causal_evidence": {},
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
            "scene_materialization_sha256": "6" * 64,
            "causal_evidence_sha256": "a" * 64,
            "route_lanes_sha256": "b" * 64,
            "route_lanes_speed_limit_sha256": "c" * 64,
            "route_lanes_has_speed_limit_sha256": "d" * 64,
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
    native = {
        "source_complete_mask": [True] * 8,
        "candidate_reasons": [[] for _ in range(8)],
    }
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
    monkeypatch.setattr(
        post_reviewer,
        "_validate_causal_evidence",
        lambda **kwargs: {
            "route_lanes": np.zeros((25, 20, 33), dtype=np.float32),
            "route_lanes_speed_limit": np.ones((25, 1), dtype=np.float32),
            "route_lanes_has_speed_limit": np.ones((25, 1), dtype=np.bool_),
            "fixed_dp_planned_red_light_cost": np.zeros(8, dtype=np.float64),
        },
    )
    monkeypatch.setattr(
        post_reviewer,
        "_validate_scene_materialization_snapshot_binding",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        post_reviewer,
        "_independent_route_projection",
        lambda *args, **kwargs: {"source": np.ones(8, dtype=np.bool_)},
    )
    monkeypatch.setattr(
        post_reviewer,
        "_independent_physical_mask",
        lambda *args, **kwargs: ([False] * 8, [[] for _ in range(8)]),
    )
    monkeypatch.setattr(
        post_reviewer,
        "_independent_planned_red_cost",
        lambda *args, **kwargs: np.zeros(8),
    )
    monkeypatch.setattr(
        post_reviewer,
        "_independent_raw_context",
        lambda *args, **kwargs: ({}, {}),
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
        scene_materialization={},
        scales=scales,
        weights=weights,
        scale_sha256="7" * 64,
    )
    assert reviewed["selected"] == 0


def test_post_reviewer_rejects_self_reported_all_physical_true() -> None:
    payload, run, source_row, native, scales, weights = _minimal_post_review_tick()
    feature, sidecar = payload["feature_payload"], payload["sidecar"]
    feature["physical_feasible_mask"] = [True] * 8
    sidecar["physical_feasible_mask"] = [True] * 8
    sidecar["all_k_high_risk"] = False
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_post_tick_dependencies(monkeypatch)
        with pytest.raises(ValueError, match="canonical atom/source"):
            post_reviewer._review_tick(
                payload=payload,
                run=run,
                tick_index=0,
                source_row=source_row,
                source_root_sha256="8" * 64,
                native_tick=native,
                scene_materialization={},
                scales=scales,
                weights=weights,
                scale_sha256="7" * 64,
            )


def test_post_reviewer_rejects_self_consistent_planned_red_col10_mutation() -> None:
    payload, run, source_row, native, scales, weights = _minimal_post_review_tick()
    payload["feature_payload"]["atom_matrix"][0][10] = 1.0
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_post_tick_dependencies(monkeypatch)
        monkeypatch.setattr(
            post_reviewer,
            "_validate_signal_receipts",
            lambda **kwargs: {"current_phase": "red"},
        )
        for row in payload["feature_payload"]["atom_applicable_mask"]:
            row[10] = True
            row[12] = True
        with pytest.raises(ValueError, match="planned-red"):
            post_reviewer._review_tick(
                payload=payload,
                run=run,
                tick_index=0,
                source_row=source_row,
                source_root_sha256="8" * 64,
                native_tick=native,
                scene_materialization={},
                scales=scales,
                weights=weights,
                scale_sha256="7" * 64,
            )


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
            scene_materialization={},
            scales=scales,
            weights=weights,
            scale_sha256="7" * 64,
        )


def test_post_reviewer_rejects_self_reported_route_speed_ineligible_candidate(
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
    with pytest.raises(ValueError, match="route oracle"):
        post_reviewer._review_tick(
            payload=payload,
            run=run,
            tick_index=0,
            source_row=source_row,
            source_root_sha256="8" * 64,
            native_tick=native,
            scene_materialization={},
            scales=scales,
            weights=weights,
            scale_sha256="7" * 64,
        )


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


def _no_signal_source_row() -> dict:
    semantic = _semantic_fixture(mapped=False)
    chain = {
        "schema_version": "camp_dp_v25_no_signal_source_chain_v1",
        "scenario_id": "1" * 64,
        "route_identity_sha256": "2" * 64,
        "source_map_sha256": "3" * 64,
        "route_lanelet_ids": [10, 11],
        "route_geometry_sha256": post_reviewer._sha(
            {"route_polyline_local_m": semantic["route_polyline_local_m"]}
        ),
        "traffic_light_regulatory_element_ids": [],
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": post_reviewer._sha(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = post_reviewer._sha(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    return {
        "scenario_id": chain["scenario_id"],
        "formal_case_sha256": "4" * 64,
        "runner_eligible": True,
        "retention_role": "executable",
        "family": "lead_vehicle_hard_brake",
        "tier": "easy",
        "seed": 25001,
        "source_map_sha256": chain["source_map_sha256"],
        "route_identity_sha256": chain["route_identity_sha256"],
        "actual_mapped_signal": False,
        "id_free_tensor_layout": {},
        "source_class": "no_signal",
        "phase_authority_mode": None,
        "source_chain": chain,
        "runtime_receipt": None,
        "tensor_evidence": None,
    }


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


def test_post_reviewer_validates_source_only_no_signal_row_without_runtime_receipt() -> None:
    source_row = _no_signal_source_row()
    assert post_reviewer._validate_source_row(source_row) is source_row

    source_row["runtime_receipt"] = {}
    with pytest.raises(ValueError, match="source-only no-signal runtime evidence"):
        post_reviewer._validate_source_row(source_row)


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
        "scene_materialization_sha256": sidecar["scene_materialization_sha256"],
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
        "_safety_pre": {"pre_decision_speed_mps": 0.0},
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
        "causal_evidence_sha256": "9" * 64,
        "route_lanes_sha256": "a" * 64,
        "route_lanes_speed_limit_sha256": "b" * 64,
        "route_lanes_has_speed_limit_sha256": "c" * 64,
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
        "candidate_reasons": [[] for _ in range(8)],
        "scores": [0.0] * 8,
        "all_k_high_risk": True,
        "controlled_scene": native["controlled_scene"],
        "v25_context": native["v25_context"],
    }
    public = native_runner._public_tick_receipt(internal, "camp")
    assert public["status"] == "ok"
    assert public["pre_decision_speed_mps"] == 0.0
    assert public["controlled_scene"] == native["controlled_scene"]
    assert public["v25_context"] == native["v25_context"]


def _exact_public_tick_fixture() -> dict:
    tick = {field: None for field in post_reviewer.PUBLIC_TICK_FIELDS}
    tick.update(
        {
            "tick_index": 0,
            "status": "ok",
            "scene_materialization_sha256": "0" * 64,
            "padding": {
                "observed_frames": 31,
                "padded_frames": 0,
                "padding_policy": "native_zero_left_pad_to_31_v1",
            },
            "tracker": {"status": "ok"},
            "safety": {
                "tick_index": 0,
                "position_xy": [0.0, 0.0],
                "speed_mps": 1.0,
                "ego_heading_rad": 0.0,
                "route_heading_rad": 0.0,
                "route_progress_m": 0.0,
                "five_point_drivable_coverage": True,
                "min_obb_clearance_m": 10.0,
                "red_light_at_interval_start": False,
                "front_center_prev_xy": [0.0, 0.0],
                "front_center_xy": [0.1, 0.0],
                "red_stop_lines": [],
                "speed_limit_mps": 10.0,
                "constant_velocity_circle_ttc_diagnostic_s": None,
                "source_complete": True,
            },
            "latency_ms": {name: 1.0 for name in post_reviewer.LATENCY_FIELDS},
            "pre_decision_speed_mps": 1.0,
            "physical_feasible_mask": [False] * 8,
            "source_valid_mask": [True] * 8,
            "source_complete_mask": [True] * 8,
            "candidate_reasons": [[] for _ in range(8)],
        }
    )
    return tick


@pytest.mark.parametrize(
    "field", ["fault", "success", "aborted", "crash", "exit_code", "status_code"]
)
def test_native_public_tick_unknown_failure_fields_fail_closed(field: str) -> None:
    tick = _exact_public_tick_fixture()
    tick[field] = False if field in {"success", "aborted", "crash"} else 1
    with pytest.raises(ValueError, match="field set"):
        post_reviewer._validate_public_success_tick(tick, tick_index=0)


def test_native_public_tick_exact_success_schema_is_accepted() -> None:
    post_reviewer._validate_public_success_tick(_exact_public_tick_fixture(), tick_index=0)


def test_native_public_tick_nested_failure_field_fails_closed() -> None:
    tick = _exact_public_tick_fixture()
    tick["safety"]["fault"] = "gpu_oom"
    with pytest.raises(ValueError, match="schema"):
        post_reviewer._validate_public_success_tick(tick, tick_index=0)


def test_post_reviewer_independent_context_rejects_safety_speed_contradiction() -> None:
    candidate = np.zeros((8, 80, 4), dtype=np.float32)
    candidate[:, :, 2] = 1.0
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :3, 0] = [0.0, 1.0, 2.0]
    route[0, :3, 2] = 1.0
    route[0, :3, 5] = 1.0
    route[0, :3, 7] = -1.0
    ego = np.zeros(10, dtype=np.float32)
    ego[4] = 1.0
    evidence = {
        "ego_current_state": ego,
        "neighbor_agents_past": np.zeros((32, 31, 11), dtype=np.float32),
        "route_lanes": route,
        "route_lanes_speed_limit": np.ones((25, 1), dtype=np.float32) * 10.0,
        "route_lanes_has_speed_limit": np.ones((25, 1), dtype=np.bool_),
    }
    raw, complete = post_reviewer._independent_raw_context(
        evidence=evidence, candidates=candidate, source_valid=[True] * 8
    )
    assert raw["ego_speed_mps"] == 1.0
    assert complete["ego_speed_mps"] is True
    contradicted = copy.deepcopy(raw)
    contradicted["ego_speed_mps"] = 999.0
    with pytest.raises(ValueError, match="independent causal oracle"):
        post_reviewer._validate_independent_context(
            feature={
                "raw_context": contradicted,
                "context_source_complete": complete,
            },
            evidence=evidence,
            candidates=candidate,
            source_valid=[True] * 8,
        )


def test_post_reviewer_causal_evidence_rejects_predecision_speed_contradiction(
    tmp_path: Path,
) -> None:
    ego = np.zeros(10, dtype=np.float32)
    ego[4] = 999.0
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route_speed = np.ones((25, 1), dtype=np.float32)
    route_has_speed = np.ones((25, 1), dtype=np.bool_)
    neighbors = np.zeros((8, 32, 80, 4), dtype=np.float32)
    raw = {
        "schema_version": "camp_dp_v25_bounded_causal_evidence_v1",
        "ego_current_state": ego.tolist(),
        "ego_shape": np.asarray([2.8, 4.8, 2.0], dtype=np.float32).tolist(),
        "neighbor_agents_past": np.zeros((32, 31, 11), dtype=np.float32).tolist(),
        "neighbor_valid_mask": np.zeros(32, dtype=np.bool_).tolist(),
        "candidate_neighbor_predictions": neighbors.tolist(),
        "static_objects": np.zeros((5, 10), dtype=np.float32).tolist(),
        "route_lanes": route.tolist(),
        "route_lanes_speed_limit": route_speed.tolist(),
        "route_lanes_has_speed_limit": route_has_speed.tolist(),
        "signal_mask": np.ones(8, dtype=np.bool_).tolist(),
        "fixed_dp_planned_red_light_cost": np.zeros(8).tolist(),
    }
    sidecar = {
        "causal_evidence_sha256": post_reviewer._sha(raw),
        "route_lanes_sha256": post_reviewer._array_sha(route),
        "route_lanes_speed_limit_sha256": post_reviewer._array_sha(route_speed),
        "route_lanes_has_speed_limit_sha256": post_reviewer._array_sha(
            route_has_speed
        ),
    }
    native = {
        **sidecar,
        "candidate_neighbor_sha256": post_reviewer._array_sha(neighbors),
        "pre_decision_speed_mps": 1.0,
    }
    with pytest.raises(ValueError, match="raw causal evidence"):
        post_reviewer._validate_causal_evidence(
            artifact_root=tmp_path,
            feature={
                "causal_evidence": externalize_causal_evidence(
                    output_dir=tmp_path, causal_evidence=raw
                )
            },
            sidecar=sidecar,
            native_tick=native,
            referenced_shards=set(),
        )


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
    receipt = _exact_native_receipt_fixture()
    if mutation == "top_status":
        receipt["status"] = "failed"
        assert (
            post_reviewer._derive_native_failure_class(receipt)
            == "native_evidence_schema_invalid"
        )
    elif mutation == "tick_status":
        receipt["ticks"][0]["status"] = "failed"
        assert (
            post_reviewer._derive_native_failure_class(receipt)
            == "native_evidence_schema_invalid"
        )
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


def _terminal_fixture() -> dict:
    return {
        "schema_version": "camp_dp_v25_a163_route_level_bounded_terminal_v2",
        "status": "passed_exact_bounded_terminal",
        "run_count": EXPECTED_RUNS,
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "tick_count": EXPECTED_TICKS,
        "retained_capability_failure_count": 0,
        "mapped_runtime_source_failure_count": 0,
        "identity0_repeat_deterministic": True,
        "repeat_comparison": {
            "candidate0_sha256_sequence_equal": True,
            "k8_row_sha256_sequence_equal": True,
            "atom_matrix_sequence_equal": True,
            "context_sequence_equal": True,
            "selected_index_sequence_equal": True,
            "failure_class_equal": True,
            "closed_loop_trajectory_equal": True,
            "speed_probe_equal": True,
        },
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _execution_source_authority_fixture() -> tuple[dict, dict, dict, dict, dict]:
    manifest = {"critical.py": "1" * 64}
    roots = {"source": {"path": "/root/source", "root_sha256": "2" * 64}}
    decision = {
        "device": "cuda",
        "run_nonce": "3" * 64,
        "critical_implementation_manifest": manifest,
        "root_artifacts": roots,
    }
    authority_payload = {
        "release_root_sha256": "4" * 64,
        "release_artifact": "/root/release",
        "decision": decision,
    }
    marker = {"path": "/root/nonce.consumed.json", "sha256": "5" * 64}
    terminal = _terminal_fixture()
    report = post_reviewer._expected_execution_report(
        terminal=terminal, wall_seconds=1.25
    )
    receipt = post_reviewer._expected_execution_source_receipt(
        authority=authority_payload, nonce_marker=marker
    )
    return report, receipt, authority_payload, marker, terminal


@pytest.mark.parametrize(
    "field",
    [
        "release_artifact",
        "release_run_nonce",
        "formal_root_sha256",
        "critical_implementation_manifest",
    ],
)
def test_post_reviewer_execution_source_authority_is_exact(field: str) -> None:
    report, receipt, authority_payload, marker, terminal = (
        _execution_source_authority_fixture()
    )
    post_reviewer._validate_execution_source_authority(
        source_receipt=receipt,
        report=report,
        authority=authority_payload,
        nonce_marker=marker,
        expected_terminal=terminal,
    )
    if field == "critical_implementation_manifest":
        receipt[field] = {"critical.py": "9" * 64}
    else:
        receipt[field] = "9" * 64
    with pytest.raises(ValueError, match="source authority"):
        post_reviewer._validate_execution_source_authority(
            source_receipt=receipt,
            report=report,
            authority=authority_payload,
            nonce_marker=marker,
            expected_terminal=terminal,
        )


def test_post_reviewer_report_device_is_exact_cuda() -> None:
    report, receipt, authority_payload, marker, terminal = (
        _execution_source_authority_fixture()
    )
    report["device"] = "cpu"
    with pytest.raises(ValueError, match="source authority"):
        post_reviewer._validate_execution_source_authority(
            source_receipt=receipt,
            report=report,
            authority=authority_payload,
            nonce_marker=marker,
            expected_terminal=terminal,
        )


def _leaf_paths(value, prefix=()):
    if type(value) is dict:
        if not value:
            return [prefix]
        return [
            path
            for key in sorted(value)
            for path in _leaf_paths(value[key], prefix + (key,))
        ]
    if type(value) is list:
        if not value:
            return [prefix]
        return [
            path
            for index, item in enumerate(value)
            for path in _leaf_paths(item, prefix + (index,))
        ]
    return [prefix]


def _mutate_leaf(value, path):
    changed = copy.deepcopy(value)
    parent = changed
    for part in path[:-1]:
        parent = parent[part]
    old = parent[path[-1]] if path else changed
    if type(old) is bool:
        replacement = not old
    elif type(old) is int:
        replacement = old + 1
    elif type(old) is float:
        replacement = old + 0.5
    elif type(old) is str:
        replacement = "mutated"
    elif old is None:
        replacement = "not-null"
    elif type(old) is list:
        replacement = ["forbidden"]
    elif type(old) is dict:
        replacement = {"forbidden": True}
    else:  # pragma: no cover - fixtures contain JSON-native leaves only.
        raise AssertionError(type(old))
    if path:
        parent[path[-1]] = replacement
        return changed
    return replacement


def _replace_leaf(value, path, replacement):
    changed = copy.deepcopy(value)
    parent = changed
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = replacement
    return changed


def _delete_leaf(value, path):
    changed = copy.deepcopy(value)
    parent = changed
    for part in path[:-1]:
        parent = parent[part]
    if type(parent) is dict:
        del parent[path[-1]]
    else:
        del parent[path[-1]]
    return changed


def _strictly_distinct_replacements(old):
    candidates = [False, 0, 0.0, "wrong-type-or-value", None]
    return [
        value
        for value in candidates
        if not post_reviewer._strict_equal(old, value)
    ]


def test_source_receipt_every_leaf_has_exact_value_and_native_type() -> None:
    report, receipt, authority_payload, marker, terminal = (
        _execution_source_authority_fixture()
    )
    assert set(receipt) == post_reviewer.SOURCE_RECEIPT_FIELDS
    for path in _leaf_paths(receipt):
        old = receipt
        for part in path:
            old = old[part]
        mutations = [_mutate_leaf(receipt, path), _delete_leaf(receipt, path)]
        mutations.extend(
            _replace_leaf(receipt, path, replacement)
            for replacement in _strictly_distinct_replacements(old)
        )
        for changed in mutations:
            with pytest.raises(ValueError, match="source authority"):
                post_reviewer._validate_execution_source_authority(
                    source_receipt=changed,
                    report=report,
                    authority=authority_payload,
                    nonce_marker=marker,
                    expected_terminal=terminal,
                )


def test_execution_report_every_leaf_has_exact_value_and_native_type() -> None:
    report, receipt, authority_payload, marker, terminal = (
        _execution_source_authority_fixture()
    )
    assert set(report) == post_reviewer.EXECUTION_REPORT_FIELDS
    for path in _leaf_paths(report):
        old = report
        for part in path:
            old = old[part]
        mutations = [_delete_leaf(report, path)]
        if path != ("wall_seconds",):
            mutations.extend(
                _replace_leaf(report, path, replacement)
                for replacement in _strictly_distinct_replacements(old)
            )
            mutations.append(_mutate_leaf(report, path))
        else:
            mutations.extend(
                _replace_leaf(report, path, replacement)
                for replacement in (False, "1.25", None, -1.0)
            )
        for changed in mutations:
            with pytest.raises(ValueError, match="source authority"):
                post_reviewer._validate_execution_source_authority(
                    source_receipt=receipt,
                    report=changed,
                    authority=authority_payload,
                    nonce_marker=marker,
                    expected_terminal=terminal,
                )


def _exact_native_receipt_fixture() -> dict:
    ticks = []
    for tick_index in range(64):
        tick = _exact_public_tick_fixture()
        tick["tick_index"] = tick_index
        tick["safety"]["tick_index"] = tick_index
        ticks.append(tick)
    initial_materialization = ticks[0]["scene_materialization_sha256"]
    initial_world = {
        "schema_version": post_reviewer.INITIAL_WORLD_STATE_SCHEMA_VERSION,
        "position_xy": [0.0, 0.0],
        "heading_rad": 0.0,
        "speed_mps": 1.0,
    }
    return {
        "schema_version": "camp_dp_v25_a1610_bounded_native_receipt_v2",
        "status": "ok",
        "route_name": "1" * 64,
        "route_sha256": "2" * 64,
        "logical_map_sha256": "3" * 64,
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": post_reviewer.EXPECTED_FIXED_DP_CHECKPOINT["sha256"],
        "args_sha256": post_reviewer.EXPECTED_FIXED_DP_ARGS["sha256"],
        "arm": "camp",
        "scenario_seed": 25001,
        "spawn_config_sha256": "4" * 64,
        "initial_world_state_sha256": post_reviewer._sha(initial_world),
        "initial_scene_materialization_sha256": initial_materialization,
        "ticks": ticks,
        "native_result": {
            "final_step": 63,
            "goal_reached": False,
            "reason": "max_steps",
            "n_npc_spawned": 0,
            "trajectory_log_path": "/root/run/trajectory_log.json",
            "clearance_log_path": "/root/run/clearance_log.json",
        },
        "claim_authorized": False,
        "selector_scale_contract": copy.deepcopy(
            post_reviewer.EXPECTED_SELECTOR_SCALE_CONTRACT
        ),
        "runtime_annotation_compatibility": (
            post_reviewer.EXPECTED_RUNTIME_ANNOTATION_COMPATIBILITY
        ),
        "causal_scene_materialization_evidence": {
            "schema_version": (
                post_reviewer.SCENE_MATERIALIZATION_EVIDENCE_SCHEMA_VERSION
            ),
            "relative_path": f"causal_scene_materializations/{'a' * 64}.npz",
            "sha256": "a" * 64,
            "tick_count": 64,
            "arrays": {
                name: {
                    "dtype": np.dtype(dtype_name).str,
                    "shape": [64, *shape],
                    "sha256": "b" * 64,
                }
                for name, (shape, dtype_name) in (
                    post_reviewer.SCENE_MATERIALIZATION_ARRAY_SCHEMA.items()
                )
            },
        },
    }


def test_native_header_result_every_leaf_is_covered_by_exact_contract() -> None:
    receipt = _exact_native_receipt_fixture()
    expected = {
        "schema_version": "camp_dp_v25_a1610_bounded_native_receipt_v2",
        "status": "ok",
        "route_name": "1" * 64,
        "route_sha256": "2" * 64,
        "logical_map_sha256": "3" * 64,
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": post_reviewer.EXPECTED_FIXED_DP_CHECKPOINT["sha256"],
        "args_sha256": post_reviewer.EXPECTED_FIXED_DP_ARGS["sha256"],
        "arm": "camp",
        "scenario_seed": 25001,
        "spawn_config_sha256": "4" * 64,
        "initial_world_state_sha256": post_reviewer._sha(
            {
                "schema_version": post_reviewer.INITIAL_WORLD_STATE_SCHEMA_VERSION,
                "position_xy": [0.0, 0.0],
                "heading_rad": 0.0,
                "speed_mps": 1.0,
            }
        ),
        "initial_scene_materialization_sha256": "0" * 64,
        "native_result": {
            "final_step": 63,
            "goal_reached": False,
            "reason": "max_steps",
            "n_npc_spawned": 0,
            "trajectory_log_path": "/root/run/trajectory_log.json",
            "clearance_log_path": "/root/run/clearance_log.json",
        },
        "claim_authorized": False,
        "selector_scale_contract": copy.deepcopy(
            post_reviewer.EXPECTED_SELECTOR_SCALE_CONTRACT
        ),
        "runtime_annotation_compatibility": (
            post_reviewer.EXPECTED_RUNTIME_ANNOTATION_COMPATIBILITY
        ),
        "causal_scene_materialization_evidence": copy.deepcopy(
            receipt["causal_scene_materialization_evidence"]
        ),
    }
    assert set(receipt) == post_reviewer.NATIVE_RECEIPT_FIELDS
    assert set(expected) == post_reviewer.NATIVE_HEADER_RESULT_FIELDS
    post_reviewer._validate_native_header_result_exact(
        receipt=receipt, expected=expected
    )
    for path in _leaf_paths(expected):
        old = expected
        for part in path:
            old = old[part]
        mutations = [_mutate_leaf(receipt, path), _delete_leaf(receipt, path)]
        mutations.extend(
            _replace_leaf(receipt, path, replacement)
            for replacement in _strictly_distinct_replacements(old)
        )
        for changed in mutations:
            with pytest.raises(ValueError, match="native header/result"):
                post_reviewer._validate_native_header_result_exact(
                    receipt=changed, expected=expected
                )


@pytest.mark.parametrize("summary", ["safety", "secondary", "latency"])
def test_bounded_authoritative_native_receipt_rejects_top_level_summary(
    summary: str,
) -> None:
    receipt = _exact_native_receipt_fixture()
    receipt[summary] = {}
    assert post_reviewer._derive_native_failure_class(receipt) != "none"


def test_nested_marker_and_terminal_extras_fail_exact_contract() -> None:
    report, receipt, authority_payload, marker, terminal = (
        _execution_source_authority_fixture()
    )
    for target, path in ((receipt, "nonce_marker"), (report, "terminal")):
        changed = copy.deepcopy(target)
        changed[path]["futureOutcome"] = True
        with pytest.raises(ValueError, match="source authority"):
            post_reviewer._validate_execution_source_authority(
                source_receipt=changed if target is receipt else receipt,
                report=changed if target is report else report,
                authority=authority_payload,
                nonce_marker=marker,
                expected_terminal=terminal,
            )


def _write_native_logs(
    native_dir: Path,
    receipt: dict,
    *,
    pre_positions: dict[int, float] | None = None,
    goal_x: float = 100.0,
) -> None:
    native_dir.mkdir(parents=True)
    trajectory = []
    clearance = []
    positions = {
        index: float(index) for index in range(64)
    }
    if pre_positions is not None:
        positions.update(pre_positions)
    goal_xy = np.asarray([goal_x, 0.0], dtype=np.float32)
    for index, tick in enumerate(receipt["ticks"]):
        pre_x = positions[index]
        position_xy = np.asarray([pre_x, 0.0], dtype=np.float32)
        logged_x = float(position_xy[0])
        trajectory.append(
            {
                "step": index,
                "x": logged_x,
                "y": 0.0,
                "heading": 0.0,
                "speed": 1.0,
                "goal_d": float(np.linalg.norm(position_xy - goal_xy)),
            }
        )
        clearance.append(
            {
                "step": index,
                "ego_x": logged_x,
                "ego_y": 0.0,
                "ego_yaw": 0.0,
                "rb_dist": None,
                "stopped_dist": None,
                "stopped_id": None,
                "moving_dist": None,
                "moving_id": None,
                "png": f"step_{index:04d}.png",
            }
        )
        post_x = positions[index + 1] if index < 63 else positions[index] + 1.0
        tick["safety"]["position_xy"] = [float(np.float32(post_x)), 0.0]
        tick["safety"]["ego_heading_rad"] = 0.0
        tick["safety"]["speed_mps"] = 1.0
    (native_dir / "trajectory_log.json").write_text(json.dumps(trajectory))
    (native_dir / "clearance_log.json").write_text(
        json.dumps(
            {
                "ego_shape": [2.79, 4.9, 1.9],
                "max_range_m": 30.0,
                "png_dir": str(native_dir),
                "records": clearance,
            }
        )
    )


def _patch_initial_world_oracle(
    monkeypatch: pytest.MonkeyPatch, *, position_x: float = 0.0
) -> None:
    monkeypatch.setattr(
        post_reviewer,
        "_independent_initial_world_state",
        lambda **kwargs: {
            "schema_version": post_reviewer.INITIAL_WORLD_STATE_SCHEMA_VERSION,
            "position_xy": [position_x, 0.0],
            "heading_rad": 0.0,
            "speed_mps": 1.0,
        },
    )


def _native_log_authority_fixture() -> tuple[dict, dict, dict]:
    return (
        {
            "route_spec": {"goal_pose": [100.0, 0.0, 0.0]},
            "parameters": {"ego_speed_mps": 8.0},
        },
        {
            "spawn_config": {
                "ego_wheelbase": 2.79,
                "ego_length": 4.9,
                "ego_width": 1.9,
            }
        },
        {"source_class": "no_signal", "source_chain": {}},
    )


def test_independent_initial_world_state_rebuilds_fixed_dp_snapped_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dp_repo = tmp_path / "dp"
    builder_source = (
        dp_repo / "scenario_generation" / "gui" / "lanelet_scene_builder.py"
    )
    builder_source.parent.mkdir(parents=True)
    builder_source.write_bytes(b"# pinned builder fixture\n")
    map_path = (tmp_path / "map.osm").resolve()
    map_path.write_bytes(b"map")

    class CacheRow:
        raw_centerline = np.asarray([[0.0, 0.0], [2.0, 0.0]], dtype=np.float64)

    class FakeBuilder:
        def __init__(self, path: str) -> None:
            assert path == str(map_path)
            self._cache = {7: CacheRow()}

        def snap_to_nearest_ll(self, xy, *, candidate_ids):
            assert list(candidate_ids) == [7]
            assert np.array_equal(
                np.asarray(xy), np.asarray([1.9, 0.0], dtype=np.float32)
            )
            return 7

        def _build_backward_polyline(
            self, lanelet_id, position_xy, heading, n_steps, speed, dt
        ):
            assert lanelet_id == 7
            assert np.array_equal(position_xy, np.asarray([2.0, 0.0], dtype=np.float32))
            points = np.column_stack(
                (
                    2.0 + np.arange(n_steps + 6, dtype=np.float64) * speed * dt,
                    np.zeros(n_steps + 6, dtype=np.float64),
                )
            )
            return points, {7}

    fake_module = SimpleNamespace(
        __file__=str(builder_source), LaneletSceneBuilder=FakeBuilder
    )
    monkeypatch.setattr(
        post_reviewer.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=builder_source.read_bytes()),
    )
    monkeypatch.setattr(
        post_reviewer.importlib,
        "import_module",
        lambda name: fake_module,
    )
    monkeypatch.setattr(
        post_reviewer,
        "require_source_preserving_lanelet2_regulatory_adapter",
        lambda path: None,
    )
    monkeypatch.setattr(
        post_reviewer, "install_lanelet2_projection_fallback", lambda path: None
    )
    post_reviewer._INITIAL_STATE_BUILDERS.clear()
    formal_case = {
        "source_map_path": str(map_path),
        "source_map_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
        "route_spec": {
            "lanelet_ids": [7],
            "start_pose": [1.9, 0.0, float(np.pi)],
        },
        "parameters": {"ego_speed_mps": 8.0},
    }
    template = {"spawn_config": {}}
    state = post_reviewer._independent_initial_world_state(
        formal_case=formal_case, template=template, dp_repo=dp_repo
    )
    draw = np.random.RandomState(25001).normal(0, 0.05)
    previous = np.asarray([2.8, -draw], dtype=np.float32)
    current = np.asarray([2.0, 0.0], dtype=np.float32)
    velocity = np.zeros(2, dtype=np.float32)
    velocity[:] = (current - previous) / 0.1
    expected_speed = float(np.linalg.norm(velocity))
    assert state == {
        "schema_version": post_reviewer.INITIAL_WORLD_STATE_SCHEMA_VERSION,
        "position_xy": [2.0, 0.0],
        "heading_rad": float(np.float32(np.pi)),
        "speed_mps": expected_speed,
    }
    assert state["speed_mps"] != 8.0


@pytest.mark.skipif(
    not post_reviewer.EXPECTED_DP_REPO.is_dir()
    or not post_reviewer.EXPECTED_FORMAL_ARTIFACT.is_dir()
    or not post_reviewer.EXPECTED_PROBE_TEMPLATE.is_file(),
    reason="canonical fixed-DP source fixture is available only on AutoDL",
)
def test_initial_world_speed_matches_real_fixed_dp_generate_history_source() -> None:
    formal = json.loads(
        (
            post_reviewer.EXPECTED_FORMAL_ARTIFACT
            / "controlled_corpus_final_plan.json"
        ).read_text(encoding="utf-8")
    )
    template = json.loads(
        post_reviewer.EXPECTED_PROBE_TEMPLATE.read_text(encoding="utf-8")
    )
    formal_case = formal["train"][0]
    state = post_reviewer._independent_initial_world_state(
        formal_case=formal_case,
        template=template,
        dp_repo=post_reviewer.EXPECTED_DP_REPO,
    )
    spec = formal_case["route_spec"]
    route_ids = spec["lanelet_ids"]
    start_pose = np.asarray(spec["start_pose"], dtype=np.float32)
    builder = post_reviewer._INITIAL_STATE_BUILDERS[
        str(Path(formal_case["source_map_path"]))
    ]
    start_lanelet = builder.snap_to_nearest_ll(
        start_pose[:2], candidate_ids=list(route_ids)
    ) or route_ids[0]
    centerline = np.asarray(builder._cache[start_lanelet].raw_centerline)
    closest = int(np.argmin(np.linalg.norm(centerline - start_pose[:2], axis=1)))
    snapped_xy = centerline[closest].astype(np.float32)
    spawn = post_reviewer._independent_spawn_config_payload(
        template=template, formal_case=formal_case
    )
    init_speed = float(spawn["ego_init_speed"])
    rng_state = np.random.get_state()
    python_random_state = random.getstate()
    try:
        np.random.seed(25001)
        random.seed(25001)
        history, _ = builder.generate_history(
            snapped_xy, float(start_pose[2]), init_speed, start_lanelet
        )
    finally:
        np.random.set_state(rng_state)
        random.setstate(python_random_state)
    history[-1, 2] = float(start_pose[2])
    velocities = np.zeros((history.shape[0], 2), dtype=np.float32)
    for index in range(1, history.shape[0]):
        velocities[index] = (history[index, :2] - history[index - 1, :2]) / 0.1
    velocities[0] = velocities[1]
    expected_speed = float(np.linalg.norm(velocities[-1]))
    assert state["position_xy"] == [float(snapped_xy[0]), float(snapped_xy[1])]
    assert state["heading_rad"] == float(start_pose[2])
    assert state["speed_mps"] == expected_speed
    assert state["speed_mps"] != init_speed


@pytest.mark.skipif(
    not post_reviewer.EXPECTED_DP_REPO.is_dir()
    or not post_reviewer.EXPECTED_FORMAL_ARTIFACT.is_dir()
    or not post_reviewer.EXPECTED_PROBE_TEMPLATE.is_file(),
    reason="canonical fixed-DP source fixture is available only on AutoDL",
)
def test_branching_predecessor_history_is_rng_isolated_and_matches_real_builder() -> None:
    formal = json.loads(
        (
            post_reviewer.EXPECTED_FORMAL_ARTIFACT
            / "controlled_corpus_final_plan.json"
        ).read_text(encoding="utf-8")
    )
    template = json.loads(
        post_reviewer.EXPECTED_PROBE_TEMPLATE.read_text(encoding="utf-8")
    )
    branching = None
    for formal_case in formal["train"]:
        spec = formal_case["route_spec"]
        route_ids = spec["lanelet_ids"]
        assert route_ids and all(type(value) is int for value in route_ids)
        state = post_reviewer._independent_initial_world_state(
            formal_case=formal_case,
            template=template,
            dp_repo=post_reviewer.EXPECTED_DP_REPO,
        )
        builder = post_reviewer._INITIAL_STATE_BUILDERS[
            str(Path(formal_case["source_map_path"]))
        ]
        start_pose = np.asarray(spec["start_pose"], dtype=np.float32)
        start_lanelet = builder.snap_to_nearest_ll(
            start_pose[:2], candidate_ids=list(route_ids)
        ) or route_ids[0]
        predecessors = list(
            builder._routing_graph.previous(builder._ll_by_id[start_lanelet])
        )
        if len(predecessors) >= 2:
            branching = (formal_case, state, builder, start_pose, start_lanelet)
            break
    assert branching is not None, "formal corpus has no branching-predecessor start"
    formal_case, first_state, builder, start_pose, start_lanelet = branching

    random.seed(998877)
    for _ in range(17):
        random.random()
    disturbed_state = random.getstate()
    repeated_state = post_reviewer._independent_initial_world_state(
        formal_case=formal_case,
        template=template,
        dp_repo=post_reviewer.EXPECTED_DP_REPO,
    )
    assert random.getstate() == disturbed_state
    assert repeated_state == first_state

    centerline = np.asarray(builder._cache[start_lanelet].raw_centerline)
    closest = int(np.argmin(np.linalg.norm(centerline - start_pose[:2], axis=1)))
    snapped_xy = centerline[closest].astype(np.float32)
    spawn = post_reviewer._independent_spawn_config_payload(
        template=template, formal_case=formal_case
    )
    init_speed = float(spawn["ego_init_speed"])
    numpy_state = np.random.get_state()
    python_state = random.getstate()
    try:
        np.random.seed(25001)
        random.seed(25001)
        history, _ = builder.generate_history(
            snapped_xy, float(start_pose[2]), init_speed, start_lanelet
        )
    finally:
        np.random.set_state(numpy_state)
        random.setstate(python_state)
    history[-1, 2] = float(start_pose[2])
    velocities = np.zeros((history.shape[0], 2), dtype=np.float32)
    for index in range(1, history.shape[0]):
        velocities[index] = (history[index, :2] - history[index - 1, :2]) / 0.1
    velocities[0] = velocities[1]
    assert repeated_state["speed_mps"] == float(np.linalg.norm(velocities[-1]))


def test_native_terminal_logs_bind_pre_and_post_tracker_timing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_initial_world_oracle(monkeypatch)
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / "run").resolve()
    receipt["native_result"]["trajectory_log_path"] = str(
        native_dir / "trajectory_log.json"
    )
    receipt["native_result"]["clearance_log_path"] = str(
        native_dir / "clearance_log.json"
    )
    _write_native_logs(native_dir, receipt)
    formal_case, template, source_row = _native_log_authority_fixture()
    post_reviewer._validate_native_log_files(
        native_dir=native_dir,
        receipt=receipt,
        formal_case=formal_case,
        template=template,
        source_row=source_row,
        dp_repo=tmp_path / "dp",
    )
    trajectory = json.loads((native_dir / "trajectory_log.json").read_text())
    trajectory[0]["speed"] += 1.0
    (native_dir / "trajectory_log.json").write_text(json.dumps(trajectory))
    with pytest.raises(ValueError, match="snapped initial world state"):
        post_reviewer._validate_native_log_files(
            native_dir=native_dir,
            receipt=receipt,
            formal_case=formal_case,
            template=template,
            source_row=source_row,
            dp_repo=tmp_path / "dp",
        )


def test_native_terminal_logs_bind_post_speed_with_fixed_dp_float32_log_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_initial_world_oracle(monkeypatch)
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / "float32-speed").resolve()
    receipt["native_result"]["trajectory_log_path"] = str(
        native_dir / "trajectory_log.json"
    )
    receipt["native_result"]["clearance_log_path"] = str(
        native_dir / "clearance_log.json"
    )
    _write_native_logs(native_dir, receipt)
    trajectory = json.loads((native_dir / "trajectory_log.json").read_text())
    post_speed = 6.59780826481711
    trajectory[1]["speed"] = float(np.float32(post_speed))
    (native_dir / "trajectory_log.json").write_text(json.dumps(trajectory))
    receipt["ticks"][0]["safety"]["speed_mps"] = post_speed
    formal_case, template, source_row = _native_log_authority_fixture()

    post_reviewer._validate_native_log_files(
        native_dir=native_dir,
        receipt=receipt,
        formal_case=formal_case,
        template=template,
        source_row=source_row,
        dp_repo=tmp_path / "dp",
    )

    receipt["ticks"][0]["safety"]["speed_mps"] = post_speed + 1e-3
    with pytest.raises(ValueError, match="pre/post tracker temporal"):
        post_reviewer._validate_native_log_files(
            native_dir=native_dir,
            receipt=receipt,
            formal_case=formal_case,
            template=template,
            source_row=source_row,
            dp_repo=tmp_path / "dp",
        )


def test_native_terminal_logs_accept_exact_one_ulp_between_fixed_dp_reductions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_initial_world_oracle(monkeypatch)
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / "one-ulp-speed").resolve()
    receipt["native_result"]["trajectory_log_path"] = str(
        native_dir / "trajectory_log.json"
    )
    receipt["native_result"]["clearance_log_path"] = str(
        native_dir / "clearance_log.json"
    )
    _write_native_logs(native_dir, receipt)
    trajectory = json.loads((native_dir / "trajectory_log.json").read_text())
    trajectory[1]["speed"] = 3.200817584991455
    (native_dir / "trajectory_log.json").write_text(json.dumps(trajectory))
    receipt["ticks"][0]["safety"]["speed_mps"] = 3.200817346572876
    formal_case, template, source_row = _native_log_authority_fixture()

    post_reviewer._validate_native_log_files(
        native_dir=native_dir,
        receipt=receipt,
        formal_case=formal_case,
        template=template,
        source_row=source_row,
        dp_repo=tmp_path / "dp",
    )

    lower = np.float32(receipt["ticks"][0]["safety"]["speed_mps"])
    two_ulps_higher = np.nextafter(
        np.nextafter(lower, np.float32(np.inf), dtype=np.float32),
        np.float32(np.inf),
        dtype=np.float32,
    )
    trajectory[1]["speed"] = float(two_ulps_higher)
    (native_dir / "trajectory_log.json").write_text(json.dumps(trajectory))
    with pytest.raises(ValueError, match="pre/post tracker temporal"):
        post_reviewer._validate_native_log_files(
            native_dir=native_dir,
            receipt=receipt,
            formal_case=formal_case,
            template=template,
            source_row=source_row,
            dp_repo=tmp_path / "dp",
        )


def test_post_reviewer_uses_frozen_fixed_k8_heading_norm_envelope() -> None:
    candidate = np.zeros((8, 80, 4), dtype=np.float32)
    candidate[:, :, 2] = np.linspace(0.5, 1.5, 8, dtype=np.float32)[:, None]
    norms = post_reviewer._validate_fixed_k8_heading_envelope(candidate)
    assert float(norms.min()) == 0.5
    assert float(norms.max()) == 1.5

    for invalid in (np.float32(0.499), np.float32(1.501)):
        mutated = candidate.copy()
        mutated[3, 17, 2] = invalid
        mutated[3, 17, 3] = 0.0
        with pytest.raises(ValueError, match="heading norm envelope"):
            post_reviewer._validate_fixed_k8_heading_envelope(mutated)


def test_terminal_oracle_uses_pre_rows_and_excludes_post_safety_63(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_initial_world_oracle(monkeypatch)
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / "temporal").resolve()
    receipt["native_result"]["trajectory_log_path"] = str(
        native_dir / "trajectory_log.json"
    )
    receipt["native_result"]["clearance_log_path"] = str(
        native_dir / "clearance_log.json"
    )
    _write_native_logs(native_dir, receipt, goal_x=1000.0)
    formal_case, template, source_row = _native_log_authority_fixture()
    formal_case["route_spec"]["goal_pose"] = [1000.0, 0.0, 0.0]
    receipt["ticks"][63]["safety"]["position_xy"] = [1000.0, 0.0]
    derived = post_reviewer._validate_native_log_files(
        native_dir=native_dir,
        receipt=receipt,
        formal_case=formal_case,
        template=template,
        source_row=source_row,
        dp_repo=tmp_path / "dp",
    )
    assert derived["reason"] == "max_steps"
    receipt["ticks"][0]["safety"]["position_xy"] = [999.0, 0.0]
    with pytest.raises(ValueError, match="pre/post tracker temporal"):
        post_reviewer._validate_native_log_files(
            native_dir=native_dir,
            receipt=receipt,
            formal_case=formal_case,
            template=template,
            source_row=source_row,
            dp_repo=tmp_path / "dp",
        )


@pytest.mark.parametrize(
    ("start_x", "goal_x"),
    [(0.1, 10.2), (100000.1, 100003.2)],
)
def test_terminal_oracle_matches_route_float32_numeric_semantics(
    tmp_path: Path,
    start_x: float,
    goal_x: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rounded_start = float(np.float32(start_x))
    _patch_initial_world_oracle(monkeypatch, position_x=rounded_start)
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / f"float32_{abs(hash((start_x, goal_x)))}").resolve()
    receipt["native_result"]["trajectory_log_path"] = str(
        native_dir / "trajectory_log.json"
    )
    receipt["native_result"]["clearance_log_path"] = str(
        native_dir / "clearance_log.json"
    )
    _write_native_logs(
        native_dir,
        receipt,
        pre_positions={index: start_x for index in range(64)},
        goal_x=goal_x,
    )
    formal_case, template, source_row = _native_log_authority_fixture()
    formal_case["route_spec"]["goal_pose"] = [goal_x, 0.0, 0.0]
    derived = post_reviewer._validate_native_log_files(
        native_dir=native_dir,
        receipt=receipt,
        formal_case=formal_case,
        template=template,
        source_row=source_row,
        dp_repo=tmp_path / "dp",
    )
    expected = float(
        np.linalg.norm(
            np.asarray([start_x, 0.0], dtype=np.float32)
            - np.asarray([goal_x, 0.0], dtype=np.float32)
        )
    )
    trajectory = json.loads((native_dir / "trajectory_log.json").read_text())
    assert trajectory[0]["goal_d"] == expected
    assert derived == {
        "final_step": 63,
        "goal_reached": False,
        "reason": "max_steps",
        "n_npc_spawned": 0,
        "trajectory_log_path": str(native_dir / "trajectory_log.json"),
        "clearance_log_path": str(native_dir / "clearance_log.json"),
    }


def test_producer_native_header_terminal_contract_is_exact(tmp_path: Path) -> None:
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / "native").resolve()
    route = {"name": "1" * 64, "sha256": "2" * 64}
    config = {
        "map": {"sha256": "3" * 64},
        "spawn_config": {"seed": 25001, "ego_init_speed": 8.0},
    }
    spawn = {**config["spawn_config"], "max_steps": 64}
    receipt["spawn_config_sha256"] = hashlib.sha256(
        json.dumps(spawn, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    receipt["native_result"]["trajectory_log_path"] = str(
        native_dir / "trajectory_log.json"
    )
    receipt["native_result"]["clearance_log_path"] = str(
        native_dir / "clearance_log.json"
    )
    _write_native_logs(native_dir, receipt)
    runner._validate_success_native_receipt(
        receipt,
        config=config,
        route=route,
        native_dir=native_dir,
        scene_materialization_hashes=["0" * 64] * 64,
    )
    receipt["native_result"]["goal_reached"] = True
    receipt["native_result"]["reason"] = "goal_reached"
    with pytest.raises(ValueError, match="native result exact schema"):
        runner._validate_success_native_receipt(
            receipt,
            config=config,
            route=route,
            native_dir=native_dir,
            scene_materialization_hashes=["0" * 64] * 64,
        )
    receipt["native_result"]["goal_reached"] = False
    receipt["native_result"]["reason"] = "max_steps"
    receipt["route_sha256"] = "9" * 64
    with pytest.raises(ValueError, match="producer header"):
        runner._validate_success_native_receipt(
            receipt,
            config=config,
            route=route,
            native_dir=native_dir,
            scene_materialization_hashes=["0" * 64] * 64,
        )


def test_pre_authority_failure_creates_no_output_or_nonce(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "failed"
    nonce_ledger = tmp_path / "nonce-ledger"

    @contextmanager
    def lock(path):
        yield

    monkeypatch.setattr(runner, "_exclusive_lock", lock)
    monkeypatch.setattr(authority, "NONCE_LEDGER", nonce_ledger)
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
    assert not output.exists()
    assert not nonce_ledger.exists()


def test_post_authority_failure_is_sealed_and_releases_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "failed-after-authority"

    @contextmanager
    def lock(path):
        yield

    def fail_after_authority(args):
        args.output_dir = output
        args.authority_consumed = True
        raise RuntimeError("synthetic post-authority failure")

    monkeypatch.setattr(runner, "_exclusive_lock", lock)
    monkeypatch.setattr(runner, "_run", fail_after_authority)
    with pytest.raises(RuntimeError, match="post-authority"):
        runner.main(
            [
                "--probe-template", str(tmp_path / "template"),
                "--dp-repo", str(tmp_path / "dp"),
                "--release-artifact", str(tmp_path / "release"),
                "--release-root-sha256", "a" * 64,
                "--output-dir", str(output),
                "--device", "cuda",
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


def _scene_materialization_rows() -> list[dict[str, np.ndarray]]:
    rows: list[dict[str, np.ndarray]] = []
    for tick_index in range(64):
        row = {
            name: np.zeros(shape, dtype=np.dtype(dtype_name))
            for name, (shape, dtype_name) in (
                post_reviewer.SCENE_MATERIALIZATION_ARRAY_SCHEMA.items()
            )
        }
        row["version"] = np.asarray(1, dtype=np.int64)
        row["ego_current_state"][0] = np.float32(tick_index)
        row["ego_current_state"][4] = np.float32(1.0)
        row["ego_shape"][:] = np.asarray([2.79, 4.9, 1.9], dtype=np.float32)
        row["goal_pose"][:] = np.asarray([100.0 - tick_index, 0.0, 0.0], dtype=np.float32)
        row["route_lanes_has_speed_limit"][:] = True
        row["route_lanes_speed_limit"][:] = np.float32(10.0)
        rows.append(row)
    return rows


def _native_causal_receipts(
    rows: list[dict[str, np.ndarray]],
) -> list[dict[str, object]]:
    receipts: list[dict[str, object]] = []
    for row in rows:
        receipts.append(
            {
                "source_observed_frames": 31,
                "observed_frames": 31,
                "padded_frames": 0,
                "truncated_frames": 0,
                "padding_policy": "native_zero_left_pad_to_31_v1",
                "arrays": {
                    name: {
                        "shape": list(value.shape),
                        "dtype": value.dtype.str,
                        "sha256": hashlib.sha256(
                            np.ascontiguousarray(value).tobytes()
                        ).hexdigest(),
                    }
                    for name, value in sorted(row.items())
                },
                "input_sha256": runner._deterministic_array_mapping_sha256(row),
            }
        )
    return receipts


def _write_preprojection_fixture(
    tmp_path: Path,
) -> tuple[
    list[dict[str, np.ndarray]],
    list[dict[str, object]],
    dict[str, object],
    list[str],
]:
    rows = _scene_materialization_rows()
    reference, hashes = runner._write_scene_materialization_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        rows=rows,
    )
    return rows, _native_causal_receipts(rows), reference, hashes


def test_scene_materialization_sink_retains_all_16_exact_arrays() -> None:
    module = native_runner
    captured: list[tuple[int, dict[str, np.ndarray]]] = []
    original = _scene_materialization_rows()[0]
    sink = lambda index, arrays: captured.append((index, dict(arrays)))
    sink(0, original)
    assert captured[0][0] == 0
    assert set(captured[0][1]) == set(
        post_reviewer.SCENE_MATERIALIZATION_ARRAY_SCHEMA
    )
    for name, (shape, dtype_name) in (
        post_reviewer.SCENE_MATERIALIZATION_ARRAY_SCHEMA.items()
    ):
        assert captured[0][1][name].shape == shape
        assert captured[0][1][name].dtype == np.dtype(dtype_name)
    assert "causal_input_sink" in module.NativeCampPredictBatch.__init__.__code__.co_varnames
    assert (
        "causal_input_receipt_sink"
        in module.NativeCampPredictBatch.__init__.__code__.co_varnames
    )


@pytest.mark.parametrize("tick_index", [0, 63])
def test_preprojection_digest_mismatch_is_persisted_before_fail_closed(
    tmp_path: Path, tick_index: int
) -> None:
    _, receipts, reference, hashes = _write_preprojection_fixture(tmp_path)
    receipts[tick_index]["input_sha256"] = "f" * 64
    path, evidence = runner._write_preprojection_digest_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        native_receipts=receipts,
        materialization_hashes=hashes,
        materialization_evidence=reference,
    )
    assert path.is_file()
    assert path.read_bytes().endswith(b"\n")
    assert not path.read_bytes().endswith(b"\n\n")
    assert evidence["mismatch_indices"] == [tick_index]
    assert evidence["first_mismatch"]["tick_index"] == tick_index
    assert evidence["first_mismatch"]["native_input_sha256"] == "f" * 64
    assert evidence["accepted_as_scientific_evidence"] is False
    with pytest.raises(
        ValueError, match=rf"preprojection digest mismatch at tick {tick_index}"
    ):
        runner._require_preprojection_digest_equality(evidence)
    root = seal_artifact(tmp_path, label="A1.7 mismatch failure fixture")
    seal = verify_complete_seal(tmp_path, root, label="A1.7 mismatch failure fixture")
    assert path.relative_to(tmp_path).as_posix() in seal["manifest_paths"]


def test_preprojection_constant_tick_offset_is_localized_from_tick_zero(
    tmp_path: Path,
) -> None:
    _, receipts, reference, hashes = _write_preprojection_fixture(tmp_path)
    shifted = receipts[1:] + receipts[:1]
    path, evidence = runner._write_preprojection_digest_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        native_receipts=shifted,
        materialization_hashes=hashes,
        materialization_evidence=reference,
    )
    assert path.is_file()
    assert evidence["mismatch_indices"] == list(range(64))
    assert evidence["first_mismatch"]["tick_index"] == 0
    assert evidence["first_mismatch"]["first_different_array"]["name"] == (
        "ego_current_state"
    )
    with pytest.raises(ValueError, match="mismatch at tick 0"):
        runner._require_preprojection_digest_equality(evidence)


@pytest.mark.parametrize("mutation", ["missing", "extra", "dtype", "shape"])
def test_preprojection_native_array_schema_mutations_fail_closed(
    tmp_path: Path, mutation: str
) -> None:
    _, receipts, reference, hashes = _write_preprojection_fixture(tmp_path)
    arrays = receipts[0]["arrays"]
    if mutation == "missing":
        arrays.pop("goal_pose")
    elif mutation == "extra":
        arrays["future_outcome"] = {
            "shape": [1], "dtype": "<f4", "sha256": "a" * 64,
        }
    elif mutation == "dtype":
        arrays["goal_pose"]["dtype"] = "<f8"
    else:
        arrays["goal_pose"]["shape"] = [2]
    with pytest.raises(ValueError, match="native causal array"):
        runner._write_preprojection_digest_evidence(
            output_dir=tmp_path,
            run={"run_ordinal": 0, "occurrence": "identity0_first"},
            native_receipts=receipts,
            materialization_hashes=hashes,
            materialization_evidence=reference,
        )


def test_preprojection_per_array_sha_mutation_is_localized(
    tmp_path: Path,
) -> None:
    _, receipts, reference, hashes = _write_preprojection_fixture(tmp_path)
    receipts[12]["arrays"]["goal_pose"]["sha256"] = "d" * 64
    path, evidence = runner._write_preprojection_digest_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        native_receipts=receipts,
        materialization_hashes=hashes,
        materialization_evidence=reference,
    )
    assert path.is_file()
    assert evidence["mismatch_indices"] == [12]
    difference = evidence["first_mismatch"]["first_different_array"]
    assert difference["name"] == "goal_pose"
    assert difference["native"]["sha256"] == "d" * 64
    with pytest.raises(ValueError, match="mismatch at tick 12"):
        runner._require_preprojection_digest_equality(evidence)


def test_preprojection_equal_roundtrip_preserves_projected_receipt_semantics(
    tmp_path: Path,
) -> None:
    _, receipts, reference, hashes = _write_preprojection_fixture(tmp_path)
    native_dir = (tmp_path / "native").resolve()
    bounded = _exact_native_receipt_fixture()
    _write_native_logs(native_dir, bounded)
    legacy = copy.deepcopy(bounded)
    legacy["schema_version"] = "v21_native_arm_receipt_v1"
    legacy.pop("causal_scene_materialization_evidence")
    legacy["initial_input_sha256"] = hashes[0]
    legacy["initial_state_sha256"] = hashlib.sha256(
        ("v21_native_scene_context_v1\0" + hashes[0]).encode("ascii")
    ).hexdigest()
    legacy.pop("initial_world_state_sha256")
    for tick_index, tick in enumerate(legacy["ticks"]):
        tick["input_sha256"] = hashes[tick_index]
        tick.pop("scene_materialization_sha256", None)
    expected = runner._project_bounded_scientific_receipt(
        copy.deepcopy(legacy),
        scene_materialization_hashes=hashes,
        scene_materialization_evidence=reference,
        native_dir=native_dir,
    )
    path, evidence = runner._write_preprojection_digest_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        native_receipts=receipts,
        materialization_hashes=hashes,
        materialization_evidence=reference,
    )
    assert evidence["mismatch_indices"] == []
    assert evidence["first_mismatch"] is None
    runner._require_preprojection_digest_equality(evidence)
    runner._discard_equal_preprojection_evidence(path)
    assert not path.exists()
    actual = runner._project_bounded_scientific_receipt(
        copy.deepcopy(legacy),
        scene_materialization_hashes=hashes,
        scene_materialization_evidence=reference,
        native_dir=native_dir,
    )
    assert actual == expected


@pytest.mark.parametrize(
    "mutation",
    ["top_future", "nested_outcome", "nonfinite", "type_smuggling"],
)
def test_preprojection_unknown_leakage_nonfinite_and_types_fail_closed(
    tmp_path: Path, mutation: str
) -> None:
    _, receipts, reference, hashes = _write_preprojection_fixture(tmp_path)
    _, evidence = runner._write_preprojection_digest_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        native_receipts=receipts,
        materialization_hashes=hashes,
        materialization_evidence=reference,
    )
    mutated = copy.deepcopy(evidence)
    if mutation == "top_future":
        mutated["future_schedule"] = []
    elif mutation == "nested_outcome":
        mutated["native_causal_receipts"][0]["outcome"] = False
    elif mutation == "nonfinite":
        mutated["run_ordinal"] = float("nan")
    else:
        mutated["run_ordinal"] = False
    with pytest.raises(ValueError, match="preprojection"):
        runner._validate_preprojection_digest_evidence(
            mutated, output_dir=tmp_path
        )


def test_scene_materialization_shard_roundtrip_and_independent_hashes(
    tmp_path: Path,
) -> None:
    rows = _scene_materialization_rows()
    reference, producer_hashes = runner._write_scene_materialization_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        rows=rows,
    )
    receipt = _exact_native_receipt_fixture()
    receipt["causal_scene_materialization_evidence"] = reference
    for index, digest in enumerate(producer_hashes):
        receipt["ticks"][index]["scene_materialization_sha256"] = digest
    receipt["initial_scene_materialization_sha256"] = producer_hashes[0]
    loaded, reviewer_hashes = post_reviewer._load_scene_materialization_evidence(
        artifact=tmp_path, receipt=receipt
    )
    assert reviewer_hashes == producer_hashes
    assert len(loaded) == 64
    np.testing.assert_array_equal(loaded[37]["goal_pose"], rows[37]["goal_pose"])
    post_reviewer._validate_scene_materialization_hash_sequence(
        receipt=receipt, hashes=reviewer_hashes
    )
    assert "initial_input_sha256" not in receipt
    assert "initial_state_sha256" not in receipt
    assert "causal_input_evidence" not in receipt


def test_legacy_native_npz_receipt_is_projected_to_scene_materialization_only(
    tmp_path: Path,
) -> None:
    bounded = _exact_native_receipt_fixture()
    native_dir = (tmp_path / "projection").resolve()
    _write_native_logs(native_dir, bounded)
    legacy = copy.deepcopy(bounded)
    legacy["schema_version"] = "v21_native_arm_receipt_v1"
    legacy.pop("causal_scene_materialization_evidence")
    legacy["initial_input_sha256"] = legacy.pop(
        "initial_scene_materialization_sha256"
    )
    legacy["initial_state_sha256"] = hashlib.sha256(
        (
            "v21_native_scene_context_v1\0"
            + legacy["initial_input_sha256"]
        ).encode("ascii")
    ).hexdigest()
    legacy.pop("initial_world_state_sha256")
    for tick in legacy["ticks"]:
        tick["input_sha256"] = tick.pop("scene_materialization_sha256")
    evidence = bounded["causal_scene_materialization_evidence"]
    projected = runner._project_bounded_scientific_receipt(
        legacy,
        scene_materialization_hashes=["0" * 64] * 64,
        scene_materialization_evidence=evidence,
        native_dir=native_dir,
    )
    assert projected["schema_version"] == (
        "camp_dp_v25_a1610_bounded_native_receipt_v2"
    )
    assert projected["ticks"][0]["scene_materialization_sha256"] == "0" * 64
    assert "input_sha256" not in projected["ticks"][0]
    assert "initial_input_sha256" not in projected
    assert "initial_state_sha256" not in projected
    assert "causal_input_evidence" not in projected


def test_coordinated_scene_digest_sidecar_mutation_cannot_replace_preimage(
    tmp_path: Path,
) -> None:
    rows = _scene_materialization_rows()
    reference, hashes = runner._write_scene_materialization_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        rows=rows,
    )
    receipt = _exact_native_receipt_fixture()
    receipt["causal_scene_materialization_evidence"] = reference
    for index, digest in enumerate(hashes):
        receipt["ticks"][index]["scene_materialization_sha256"] = digest
    receipt["initial_scene_materialization_sha256"] = hashes[0]
    coordinated_fake = "f" * 64
    receipt["ticks"][0]["scene_materialization_sha256"] = coordinated_fake
    receipt["initial_scene_materialization_sha256"] = coordinated_fake
    sidecar = {"scene_materialization_sha256": coordinated_fake}
    assert sidecar["scene_materialization_sha256"] == receipt["ticks"][0][
        "scene_materialization_sha256"
    ]
    with pytest.raises(ValueError, match="materialization hash sequence"):
        post_reviewer._validate_scene_materialization_hash_sequence(
            receipt=receipt, hashes=hashes
        )


@pytest.mark.parametrize("mutation", ["missing", "extra", "dtype", "shape"])
def test_scene_materialization_shard_schema_mutations_fail_closed(
    tmp_path: Path, mutation: str
) -> None:
    rows = _scene_materialization_rows()
    reference, _ = runner._write_scene_materialization_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        rows=rows,
    )
    receipt = _exact_native_receipt_fixture()
    original = tmp_path / reference["relative_path"]
    with np.load(original, allow_pickle=False) as loaded:
        arrays = {name: np.array(loaded[name], copy=True) for name in loaded.files}
    if mutation == "missing":
        arrays.pop("goal_pose")
    elif mutation == "extra":
        arrays["future_outcome"] = np.zeros((64, 1), dtype=np.float32)
    elif mutation == "dtype":
        arrays["goal_pose"] = arrays["goal_pose"].astype(np.float64)
    else:
        arrays["goal_pose"] = arrays["goal_pose"][:, :2]
    changed = tmp_path / "changed.npz"
    with changed.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    digest = hashlib.sha256(changed.read_bytes()).hexdigest()
    target = tmp_path / "causal_scene_materializations" / f"{digest}.npz"
    changed.replace(target)
    mutated_reference = copy.deepcopy(reference)
    mutated_reference["relative_path"] = (
        f"causal_scene_materializations/{digest}.npz"
    )
    mutated_reference["sha256"] = digest
    if mutation == "missing":
        mutated_reference["arrays"].pop("goal_pose")
    elif mutation == "extra":
        mutated_reference["arrays"]["future_outcome"] = {
            "dtype": np.dtype(np.float32).str,
            "shape": [64, 1],
            "sha256": post_reviewer._array_sha(arrays["future_outcome"]),
        }
    else:
        mutated_reference["arrays"]["goal_pose"] = {
            "dtype": arrays["goal_pose"].dtype.str,
            "shape": list(arrays["goal_pose"].shape),
            "sha256": post_reviewer._array_sha(arrays["goal_pose"]),
        }
    receipt["causal_scene_materialization_evidence"] = mutated_reference
    with pytest.raises(ValueError, match="scene materialization"):
        post_reviewer._load_scene_materialization_evidence(
            artifact=tmp_path, receipt=receipt
        )


def test_scene_materialization_cross_run_swap_fails_snapshot_binding() -> None:
    first = _scene_materialization_rows()[0]
    second = {name: value.copy() for name, value in first.items()}
    second["ego_current_state"][4] = np.float32(99.0)
    evidence = {
        name: first[name]
        for name in (
            "ego_current_state", "ego_shape", "neighbor_agents_past",
            "static_objects", "route_lanes", "route_lanes_speed_limit",
            "route_lanes_has_speed_limit",
        )
    }
    with pytest.raises(ValueError, match="materialization/snapshot"):
        post_reviewer._validate_scene_materialization_snapshot_binding(
            evidence=evidence, scene_materialization=second
        )


def test_scene_materialization_byte_mutation_still_fails_snapshot_binding(
    tmp_path: Path,
) -> None:
    rows = _scene_materialization_rows()
    reference, _ = runner._write_scene_materialization_evidence(
        output_dir=tmp_path,
        run={"run_ordinal": 0, "occurrence": "identity0_first"},
        rows=rows,
    )
    original = tmp_path / reference["relative_path"]
    with np.load(original, allow_pickle=False) as loaded:
        arrays = {name: np.array(loaded[name], copy=True) for name in loaded.files}
    arrays["ego_current_state"][0, 4] = np.float32(77.0)
    changed = tmp_path / "changed-byte.npz"
    with changed.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    digest = hashlib.sha256(changed.read_bytes()).hexdigest()
    target = tmp_path / "causal_scene_materializations" / f"{digest}.npz"
    changed.replace(target)
    resigned = copy.deepcopy(reference)
    resigned["relative_path"] = f"causal_scene_materializations/{digest}.npz"
    resigned["sha256"] = digest
    resigned["arrays"]["ego_current_state"] = {
        "dtype": arrays["ego_current_state"].dtype.str,
        "shape": list(arrays["ego_current_state"].shape),
        "sha256": post_reviewer._array_sha(arrays["ego_current_state"]),
    }
    receipt = _exact_native_receipt_fixture()
    receipt["causal_scene_materialization_evidence"] = resigned
    loaded_rows, _ = post_reviewer._load_scene_materialization_evidence(
        artifact=tmp_path, receipt=receipt
    )
    snapshot_evidence = {
        name: rows[0][name]
        for name in (
            "ego_current_state", "ego_shape", "neighbor_agents_past",
            "static_objects", "route_lanes", "route_lanes_speed_limit",
            "route_lanes_has_speed_limit",
        )
    }
    with pytest.raises(ValueError, match="materialization/snapshot"):
        post_reviewer._validate_scene_materialization_snapshot_binding(
            evidence=snapshot_evidence, scene_materialization=loaded_rows[0]
        )


def test_goal_oracle_rejects_coordinated_goal_distance_forgery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_initial_world_oracle(monkeypatch)
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / "run").resolve()
    receipt["native_result"]["trajectory_log_path"] = str(
        native_dir / "trajectory_log.json"
    )
    receipt["native_result"]["clearance_log_path"] = str(
        native_dir / "clearance_log.json"
    )
    _write_native_logs(native_dir, receipt)
    trajectory = json.loads((native_dir / "trajectory_log.json").read_text())
    trajectory[-1]["goal_d"] = 0.0
    (native_dir / "trajectory_log.json").write_text(json.dumps(trajectory))
    formal_case, template, source_row = _native_log_authority_fixture()
    with pytest.raises(ValueError, match="trajectory goal oracle"):
        post_reviewer._validate_native_log_files(
            native_dir=native_dir,
            receipt=receipt,
            formal_case=formal_case,
            template=template,
            source_row=source_row,
            dp_repo=tmp_path / "dp",
        )


@pytest.mark.parametrize(
    ("mode", "goal_x", "positions", "expected_reason"),
    [
        ("reached", 100.0, {63: 100.0}, "goal_reached"),
        ("passed", 50.0, {62: 30.0, 63: 80.0}, "goal_passed"),
    ],
)
def test_goal_oracle_rejects_pre_advance_terminal_with_64_post_safety_ticks(
    tmp_path: Path,
    mode: str,
    goal_x: float,
    positions: dict[int, float],
    expected_reason: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_initial_world_oracle(monkeypatch)
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / mode).resolve()
    receipt["native_result"]["trajectory_log_path"] = str(native_dir / "trajectory_log.json")
    receipt["native_result"]["clearance_log_path"] = str(native_dir / "clearance_log.json")
    pre_positions = {index: 0.0 for index in range(64)}
    pre_positions.update(positions)
    _write_native_logs(
        native_dir, receipt, pre_positions=pre_positions, goal_x=goal_x
    )
    formal_case, template, source_row = _native_log_authority_fixture()
    formal_case["route_spec"]["goal_pose"] = [goal_x, 0.0, 0.0]
    with pytest.raises(ValueError, match=f"cannot coexist.*{expected_reason}"):
        post_reviewer._validate_native_log_files(
            native_dir=native_dir,
            receipt=receipt,
            formal_case=formal_case,
            template=template,
            source_row=source_row,
            dp_repo=tmp_path / "dp",
        )


@pytest.mark.parametrize("target", ["red_stop_lines", "clearance_extra", "negative_distance", "bad_id"])
def test_native_nested_log_leakage_and_type_mutations_fail_closed(
    tmp_path: Path, target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_initial_world_oracle(monkeypatch)
    receipt = _exact_native_receipt_fixture()
    native_dir = (tmp_path / target).resolve()
    receipt["native_result"]["trajectory_log_path"] = str(native_dir / "trajectory_log.json")
    receipt["native_result"]["clearance_log_path"] = str(native_dir / "clearance_log.json")
    _write_native_logs(native_dir, receipt)
    formal_case, template, source_row = _native_log_authority_fixture()
    if target == "red_stop_lines":
        receipt["ticks"][0]["safety"]["red_stop_lines"] = [{"futureOutcome": True}]
    else:
        clearance = json.loads((native_dir / "clearance_log.json").read_text())
        if target == "clearance_extra":
            clearance["records"][0]["futureOutcome"] = True
        elif target == "negative_distance":
            clearance["records"][0]["rb_dist"] = -1.0
        else:
            clearance["records"][0]["stopped_dist"] = 1.0
            clearance["records"][0]["stopped_id"] = 7
        (native_dir / "clearance_log.json").write_text(json.dumps(clearance))
    with pytest.raises(ValueError):
        post_reviewer._validate_native_log_files(
            native_dir=native_dir,
            receipt=receipt,
            formal_case=formal_case,
            template=template,
            source_row=source_row,
            dp_repo=tmp_path / "dp",
        )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1, "b":2}\n',
        b'{"a":1}\n\n',
        b'{"a":1,"a":2}\n',
        b'{"a":NaN}\n',
    ],
)
def test_strict_canonical_json_rejects_noncanonical_double_lf_duplicate_and_nan(
    tmp_path: Path, raw: bytes
) -> None:
    path = tmp_path / "authority.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        post_reviewer._load(path, canonical=True)


def test_resealed_duplicate_key_json_still_fails_strict_loader(tmp_path: Path) -> None:
    artifact = tmp_path / "resealed"
    artifact.mkdir()
    payload = artifact / "report.json"
    payload.write_bytes(b'{"status":"passed","status":"failed"}\n')
    seal_artifact(artifact, label="duplicate-key mutation")
    verify_complete_seal(artifact)
    with pytest.raises(ValueError, match="strict JSON"):
        post_reviewer._load(payload, canonical=True)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"status": "complete"}\n',
        b'{"status":"complete","status":"failed"}\n',
    ],
)
def test_real_post_review_entry_executes_manifest_byte_policy_after_reseal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raw: bytes
) -> None:
    artifact = (tmp_path / "execution").resolve()
    artifact.mkdir()
    (artifact / "report.json").write_bytes(raw)
    (artifact / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(artifact, label="post-review byte mutation")
    dp_repo = tmp_path / "dp"
    dp_repo.mkdir()
    monkeypatch.setattr(
        post_reviewer,
        "_git",
        lambda repo, *args: (
            FIXED_DP_HEAD
            if repo == dp_repo and args == ("rev-parse", "HEAD")
            else "1" * 40
            if args == ("rev-parse", "HEAD")
            else ""
        ),
    )
    args = SimpleNamespace(
        execution_artifact=artifact,
        execution_root_sha256=root,
        release_artifact=tmp_path / "release",
        release_root_sha256="0" * 64,
        probe_template=tmp_path / "template",
        dp_repo=dp_repo,
    )
    with pytest.raises(ValueError, match="canonical|strict JSON"):
        post_reviewer.review(args)


def test_canonical_jsonl_rejects_pretty_double_lf_and_duplicate_key(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rows.jsonl"
    for raw in (
        b'{"a": 1}\n',
        b'{"a":1}\n\n',
        b'{"a":1,"a":2}\n',
    ):
        path.write_bytes(raw)
        with pytest.raises(ValueError):
            post_reviewer._jsonl(path)


def test_every_execution_authority_file_executes_exactly_one_byte_policy(
    tmp_path: Path,
) -> None:
    snapshot_data = encode_snapshot({"value": 1})
    snapshot_sha = hashlib.sha256(snapshot_data).hexdigest()
    shard_data = lzma.compress(
        b"deterministic-array-shard",
        format=lzma.FORMAT_XZ,
        check=lzma.CHECK_SHA256,
        preset=6,
    )
    shard_sha = hashlib.sha256(shard_data).hexdigest()
    examples = {
        "COMMAND",
        "HEADS",
        "run.exit",
        "report.json",
        "source_receipt.json",
        "progress.json",
        "results.jsonl",
        "snapshot_index.jsonl",
        "run_evidence.jsonl",
        f"routes/{'a' * 64}.pkl",
        f"snapshots/{snapshot_sha}{SNAPSHOT_SUFFIX}",
        f"causal_evidence_shards/{shard_sha}.bin.xz",
        f"causal_scene_materializations/{'c' * 64}.npz",
        "native_runs/run_000_identity0_first_case/bounded_native_receipt.json",
        "native_runs/run_000_identity0_first_case/trajectory_log.json",
        "native_runs/run_000_identity0_first_case/clearance_log.json",
        "native_runs/run_000_identity0_first_case/native.stdout.txt",
        "native_runs/run_000_identity0_first_case/native.stderr.txt",
    }
    for relative in examples:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "COMMAND":
            path.write_bytes(b"diagnostic\n")
        elif relative == "HEADS":
            path.write_bytes(
                b"camp_source_head=" + b"1" * 40 + b"\n"
                b"camp_pointer_head=" + b"2" * 40 + b"\n"
                b"fixed_dp_head=" + FIXED_DP_HEAD.encode("ascii") + b"\n"
            )
        elif relative == "run.exit":
            path.write_bytes(b"0\n")
        elif relative.endswith(".jsonl"):
            path.write_bytes(post_reviewer._canonical_bytes({"row": 1}))
        elif relative.endswith(".json") and "trajectory_log" not in relative and "clearance_log" not in relative:
            post_reviewer._write(path, {"value": 1})
        elif relative.endswith(".json"):
            path.write_text('{"value":1}', encoding="utf-8")
        elif relative.endswith(".npz"):
            with path.open("wb") as handle:
                np.savez_compressed(handle, value=np.asarray([1], dtype=np.int64))
        elif relative.endswith(".bin.xz"):
            path.write_bytes(shard_data)
        elif relative.endswith(SNAPSHOT_SUFFIX):
            path.write_bytes(snapshot_data)
        elif relative.endswith(".pkl"):
            path.write_bytes(b"fixed-dp-route")
        else:
            path.write_text("diagnostic", encoding="utf-8")
    policies = post_reviewer._validate_execution_manifest_policies(
        artifact=tmp_path, paths=sorted(examples)
    )
    assert set(policies) == examples
    with pytest.raises(ValueError, match="no unique byte/schema policy"):
        post_reviewer._execution_file_byte_policy("native_runs/run/spawn_config.json")
