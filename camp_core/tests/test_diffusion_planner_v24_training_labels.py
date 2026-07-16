from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "scripts" / "integrations" / "materialize_diffusion_planner_v24_training_labels.py"
REVIEWER = ROOT / "scripts" / "integrations" / "review_diffusion_planner_v24_training_labels.py"


def _producer():
    from scripts.integrations import materialize_diffusion_planner_v24_training_labels

    return materialize_diffusion_planner_v24_training_labels


def _reviewer():
    from scripts.integrations import review_diffusion_planner_v24_training_labels

    return review_diffusion_planner_v24_training_labels


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _valid_snapshot() -> dict:
    rows = [_sha(f"candidate:{index}") for index in range(8)]
    tensor = _sha("tensor")
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": {
            "atom_matrix": np.zeros((8, 14), dtype=np.float64).tolist(),
            "source_valid_mask": [True] * 8,
            "candidate_row_sha256": rows,
        },
        "sidecar": {
            "tick_index": 0,
            "route_sha256": _sha("route-file"),
            "default_output_sha256": rows[0],
            "candidate0_sha256": rows[0],
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "candidate0_sha256": rows[0],
                "default_output_sha256": rows[0],
                "native_ranked_k8": False,
            },
            "candidate_tensor_sha256_before": tensor,
            "candidate_tensor_sha256_after": tensor,
            "causal_input_sha256": _sha("causal"),
            "physical_feasible_mask": [True] * 8,
            "all_k_high_risk": False,
            "offline_label_provenance": "pending_train_only_offline_supervision_sidecar",
            "record_key": "record-test",
            "map_family_id": "map-family-test",
            "logical_map_sha256": _sha("logical-map"),
            "route_identity_sha256": _sha("route-identity"),
            "group_sha256": _sha("group"),
            "corridor_group_sha256": _sha("corridor"),
            "seed": 24001,
            "source_stratum": {
                "branch_intersection": False,
                "short_progress_opportunity": False,
                "tight_corridor": True,
                "traffic_light": False,
            },
            "split": "train",
        },
    }


def _label_problem() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    atoms = np.zeros((2, 8, 14), dtype=np.float64)
    atoms[0, :, 8] = np.arange(8, dtype=np.float64)
    atoms[1, :, 10] = np.arange(8, dtype=np.float64)
    valid = np.ones((2, 8), dtype=bool)
    physical = np.ones((2, 8), dtype=bool)
    return atoms, valid, physical


def _compute(
    atoms: np.ndarray, valid: np.ndarray, physical: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    module = _producer()
    return module.compute_label_batch(
        atoms,
        valid,
        physical,
        frozen_scales=np.ones(14),
        severity_weights=np.asarray(module.EXPECTED_SEVERITY),
        physical_risk_penalty=100.0,
        normalized_atom_clip=10.0,
    )


def test_label_formula_is_frozen_causal_policy_with_lowest_index_ties() -> None:
    atoms, valid, physical = _label_problem()
    physical[0] = False
    costs, oracle, all_k = _compute(atoms, valid, physical)

    np.testing.assert_allclose(costs[0], 100.0 + 10.0 * np.arange(8))
    np.testing.assert_allclose(costs[1], 15.0 * np.arange(8))
    assert oracle.tolist() == [0, 0]
    assert all_k.tolist() == [1, 0]


def test_source_invalid_candidate_is_ineligible_but_physical_risk_is_not_veto() -> None:
    atoms, valid, physical = _label_problem()
    atoms[:] = 0.0
    valid[0, 0] = False
    physical[0, 1:] = False
    costs, oracle, _all_k = _compute(atoms, valid, physical)

    assert costs[0, 0] == 0.0
    assert np.all(costs[0, 1:] == 100.0)
    assert oracle[0] == 1


@pytest.mark.parametrize(
    "mask",
    [
        np.ones((2, 8), dtype=np.int64),
        np.ones((2, 8), dtype=np.float64),
        np.full((2, 8), "true", dtype="U4"),
    ],
)
def test_label_masks_reject_implicit_boolean_coercion(mask: np.ndarray) -> None:
    module = _producer()
    atoms, valid, physical = _label_problem()
    with pytest.raises(ValueError, match="strict booleans"):
        module.compute_label_batch(
            atoms,
            mask,
            physical,
            frozen_scales=np.ones(14),
            severity_weights=np.asarray(module.EXPECTED_SEVERITY),
            physical_risk_penalty=100.0,
            normalized_atom_clip=10.0,
        )
    with pytest.raises(ValueError, match="strict booleans"):
        module.compute_label_batch(
            atoms,
            valid,
            mask,
            frozen_scales=np.ones(14),
            severity_weights=np.asarray(module.EXPECTED_SEVERITY),
            physical_risk_penalty=100.0,
            normalized_atom_clip=10.0,
        )


def test_label_contract_rejects_scale_severity_penalty_or_clip_drift() -> None:
    module = _producer()
    atoms, valid, physical = _label_problem()
    cases = [
        (np.zeros(14), np.asarray(module.EXPECTED_SEVERITY), 100.0, 10.0),
        (np.ones(14), np.full(14, -1.0), 100.0, 10.0),
        (np.ones(14), np.asarray(module.EXPECTED_SEVERITY), -1.0, 10.0),
        (np.ones(14), np.asarray(module.EXPECTED_SEVERITY), 100.0, 0.0),
    ]
    for scales, severity, penalty, clip in cases:
        with pytest.raises(ValueError):
            module.compute_label_batch(
                atoms,
                valid,
                physical,
                frozen_scales=scales,
                severity_weights=severity,
                physical_risk_penalty=penalty,
                normalized_atom_clip=clip,
            )


def test_little_endian_and_uint8_columns_are_deterministic() -> None:
    module = _producer()
    values = np.asarray([[1.0, -2.5]], dtype=np.float64)
    assert module._little_endian_f64_bytes(values) == struct.pack("<dd", 1.0, -2.5)
    assert module._u8_bytes(np.asarray([0, 1, 255])) == b"\x00\x01\xff"
    with pytest.raises(ValueError):
        module._u8_bytes(np.asarray([256]))


def test_preflight_path_and_root_are_exact_not_caller_selected(tmp_path: Path) -> None:
    module = _producer()
    with pytest.raises(ValueError, match="path or root drift"):
        module._validate_preflight(
            preflight_root=tmp_path,
            expected_preflight_root_sha256="0" * 64,
        )


def test_producer_has_no_scale_fit_or_percentile_path() -> None:
    source = PRODUCER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "percentile" not in calls
    assert "fit_train_atom_scales" not in source
    assert "materialize_diffusion_planner_v22_labels" not in source


def test_label_columns_keep_identity_only_in_separate_provenance() -> None:
    module = _producer()
    assert set(module.OUTPUT_FILES) == {
        "snapshot_sha256.txt",
        "snapshot_provenance.jsonl",
        "candidate_cost.f64le",
        "oracle_index.u8",
        "source_valid_mask.u8",
        "physical_feasible_mask.u8",
        "all_k_high_risk.u8",
    }


def test_source_snapshot_validator_rejects_identity_feature_and_nested_outcome() -> None:
    module = _producer()
    payload = _valid_snapshot()
    module._validate_snapshot(payload, phase="pilot", expected_sha256=_sha("snapshot"))

    identity = json.loads(json.dumps(payload))
    identity["feature_payload"]["map_id"] = "forbidden"
    with pytest.raises(ValueError):
        module._validate_snapshot(
            identity, phase="pilot", expected_sha256=_sha("snapshot")
        )

    outcome = json.loads(json.dumps(payload))
    outcome["sidecar"]["source_stratum"]["future_outcome"] = 1
    with pytest.raises(ValueError):
        module._validate_snapshot(
            outcome, phase="pilot", expected_sha256=_sha("snapshot")
        )
    assert module.PROVENANCE_FIELDS == {
        "snapshot_sha256",
        "route_identity_sha256",
        "seed",
        "phase",
        "source_relative_path",
        "tick_index",
    }


def test_producer_seal_rejects_post_seal_injection_and_nested_reserved(
    tmp_path: Path,
) -> None:
    module = _producer()
    reviewer = _reviewer()
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "payload.bin").write_bytes(b"payload")
    digest = module.seal_artifact(root)
    assert reviewer.verify_complete_seal(root, digest)
    (root / "injected.bin").write_bytes(b"injected")
    with pytest.raises(ValueError, match="inventory"):
        reviewer.verify_complete_seal(root, digest)

    nested_root = tmp_path / "nested-artifact"
    nested = nested_root / "nested"
    nested.mkdir(parents=True)
    (nested_root / "payload.bin").write_bytes(b"payload")
    (nested / "SHA256SUMS").write_text("forbidden\n", encoding="utf-8")
    with pytest.raises(ValueError, match="nested"):
        module.seal_artifact(nested_root)


def test_independent_reviewer_does_not_import_label_producer() -> None:
    source = REVIEWER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        "materialize_diffusion_planner_v24_training_labels" in module
        for module in imported_modules
    )
    assert "compute_label_batch" not in source
    assert "for atom_index in range(14)" in source
    assert "exact_binary_float64" in source
    assert "np.allclose" not in source


def test_label_and_review_artifact_schemas_and_roots_are_frozen() -> None:
    producer = _producer()
    reviewer = _reviewer()
    assert producer.MANIFEST_SCHEMA == "camp_dp_v24_train_causal_label_manifest_v1"
    assert producer.PREFLIGHT_ROOT_SHA256 == reviewer.PREFLIGHT_ROOT_SHA256
    assert producer.PREFLIGHT_ARTIFACT == reviewer.PREFLIGHT_ARTIFACT
    assert reviewer.MERGED_ROOT_SHA256 == (
        "d8278d030cabd71af88f60d13c410a37c515f22e0ea4c606a592abecc598bdcc"
    )
    assert reviewer.MERGED_REVIEW_ROOT_SHA256 == (
        "925db2aa58f136c20b3e9054d87dbd8d73d4162d18d079b10abbcacc63f09490"
    )
    assert reviewer.ATOM_FREEZE_REVIEW_ROOT_SHA256 == (
        "a88e6d43041e4f8005a7df5cccd9dd64510758a9c2a4af1de15e339e250e80b8"
    )


def test_canonical_provenance_hash_is_order_stable() -> None:
    module = _producer()
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}
    assert module._canonical_json_bytes(left) == module._canonical_json_bytes(right)
    assert hashlib.sha256(module._canonical_json_bytes(left)).hexdigest() == hashlib.sha256(
        module._canonical_json_bytes(right)
    ).hexdigest()


def test_independent_source_provenance_requires_tracked_head_exact_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    producer = _producer()
    reviewer = _reviewer()
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    relative = "runner.py"
    (repo / relative).write_bytes(b"value = 1\n")
    subprocess.run(["git", "add", relative], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=v24-test",
            "-c",
            "user.email=v24-test@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    monkeypatch.setattr(producer, "PRODUCER_PROVENANCE_FILES", (relative,))
    monkeypatch.setattr(producer, "PREFLIGHT_STABLE_PROVENANCE_FILES", ())
    producer_receipt = producer.tracked_source_provenance(
        repo=repo,
        current_head=head,
    )
    assert producer_receipt[relative]["matches_current_head"] is True
    assert producer_receipt[relative]["matches_preflight_head"] is False
    receipt = reviewer._tracked_source_provenance(
        repo=repo,
        current_head=head,
        relative_paths=(relative,),
    )
    assert receipt[relative]["matches_current_head"] is True
    assert receipt[relative]["matches_preflight_head"] is False
    assert len(receipt[relative]["git_blob"]) == 40

    (repo / relative).write_bytes(b"value = 2\n")
    with pytest.raises(ValueError, match="not tracked by current HEAD"):
        producer.tracked_source_provenance(repo=repo, current_head=head)
    with pytest.raises(ValueError, match="not tracked by current HEAD"):
        reviewer._tracked_source_provenance(
            repo=repo,
            current_head=head,
            relative_paths=(relative,),
        )
    (repo / "untracked.py").write_bytes(b"value = 3\n")
    with pytest.raises(subprocess.CalledProcessError):
        reviewer._tracked_source_provenance(
            repo=repo,
            current_head=head,
            relative_paths=("untracked.py",),
        )
