from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
import subprocess

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXECUTOR_FILE = "scripts/integrations/execute_diffusion_planner_v24_native_corpus.py"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()


def _clean_files(root: Path, *, camp_head: str) -> None:
    (root / "HEADS").write_text(
        f"CAMP_HEAD={camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (root / "COMMAND").write_text("test fixture\n", encoding="utf-8")
    (root / "stdout.txt").write_text("{}\n", encoding="utf-8")
    (root / "stderr.txt").write_text("", encoding="utf-8")
    (root / "run.exit").write_text("0\n", encoding="ascii")


def _stable_provenance_bytes(repo: Path, head: str, relative: str) -> bytes:
    if relative == EXECUTOR_FILE and head == "a" * 40:
        return subprocess.run(
            [
                "git",
                "show",
                "c697137d4769b22ca5db6a60fd570f13f949cbef:" + relative,
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
    return (repo / relative).read_bytes()


def _snapshot(*, seed: int, second_atom2: float) -> dict:
    rows = [_sha(f"row:{seed}:{index}") for index in range(8)]
    tensor = _sha(f"tensor:{seed}")
    matrix = np.ones((8, 14), dtype=np.float64)
    matrix[:, 0] = np.arange(8, dtype=np.float64)
    matrix[:, 1] = [5.0, 5.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    matrix[:, 2] = 2.0
    matrix[1, 2] = second_atom2
    return {
        "schema_version": "v22_native_decision_snapshot_v1",
        "feature_payload": {
            "atom_matrix": matrix.tolist(),
            "source_valid_mask": [True, True, False, False, False, False, False, False],
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
            "causal_input_sha256": _sha(f"causal:{seed}"),
            "physical_feasible_mask": [True, True, False, False, False, False, False, False],
            "all_k_high_risk": False,
            "offline_label_provenance": (
                "pending_train_only_offline_supervision_sidecar"
            ),
            "record_key": "record-test",
            "map_family_id": "map-family-test",
            "logical_map_sha256": _sha("logical-map"),
            "route_identity_sha256": _sha("route-identity"),
            "group_sha256": _sha("group"),
            "corridor_group_sha256": _sha("corridor"),
            "seed": seed,
            "source_stratum": {
                "branch_intersection": False,
                "short_progress_opportunity": False,
                "tight_corridor": True,
                "traffic_light": False,
            },
            "split": "train",
        },
    }


def _phase_root(
    root: Path, *, camp_head: str, snapshot: dict | None
) -> tuple[str, str | None]:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        seal_artifact,
    )

    root.mkdir()
    digest = None
    if snapshot is not None:
        content = _canonical(snapshot)
        digest = hashlib.sha256(content).hexdigest()
        path = root / "snapshots" / f"{digest}.json"
        path.parent.mkdir()
        path.write_bytes(content)
    _clean_files(root, camp_head=camp_head)
    return seal_artifact(root), digest


def _fixture(tmp_path: Path) -> dict[str, object]:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        seal_artifact,
    )

    pilot_head = "a" * 40
    remaining_head = "b" * 40
    pilot = tmp_path / "pilot"
    pilot_sha, pilot_snapshot = _phase_root(
        pilot,
        camp_head=pilot_head,
        snapshot=_snapshot(seed=24001, second_atom2=2.0),
    )
    remaining = tmp_path / "remaining"
    remaining_sha, remaining_snapshot = _phase_root(
        remaining,
        camp_head=remaining_head,
        snapshot=_snapshot(seed=24002, second_atom2=3.0),
    )
    pilot_review = tmp_path / "pilot-review"
    pilot_review_sha, _ = _phase_root(
        pilot_review, camp_head=pilot_head, snapshot=None
    )
    remaining_review = tmp_path / "remaining-review"
    remaining_review_sha, _ = _phase_root(
        remaining_review, camp_head=remaining_head, snapshot=None
    )
    rows = sorted(
        [
            {
                "phase": "pilot",
                "relative_path": f"snapshots/{pilot_snapshot}.json",
                "sha256": pilot_snapshot,
            },
            {
                "phase": "remaining",
                "relative_path": f"snapshots/{remaining_snapshot}.json",
                "sha256": remaining_snapshot,
            },
        ],
        key=lambda row: (row["sha256"], row["phase"]),
    )
    index_bytes = b"".join(_canonical(row) for row in rows)
    merged = tmp_path / "merged"
    merged.mkdir()
    (merged / "snapshot_index.jsonl").write_bytes(index_bytes)
    summary = {
        "schema": "camp_dp_v24_native_corpus_merged_train_index_v1",
        "status": "passed",
        "phase": "merged_train_corpus_assembly_only",
        "split": "train",
        "snapshot_count": 2,
        "snapshot_index_row_count": 2,
        "snapshot_index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "source_artifacts": {
            "pilot": {"path": str(pilot), "root_sha256": pilot_sha},
            "pilot_review": {
                "path": str(pilot_review),
                "root_sha256": pilot_review_sha,
            },
            "remaining": {"path": str(remaining), "root_sha256": remaining_sha},
            "remaining_review": {
                "path": str(remaining_review),
                "root_sha256": remaining_review_sha,
            },
        },
        "snapshot_payloads_copied": False,
        "snapshot_payloads_modified": False,
        "route_or_seed_removed_replaced_or_reordered": False,
        "assembly_only": True,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    (merged / "merged_summary.json").write_bytes(_canonical(summary))
    _clean_files(merged, camp_head="c" * 40)
    (merged / "stdout.txt").write_bytes(_canonical(summary))
    merged_sha = seal_artifact(merged)
    merged_review = tmp_path / "merged-review"
    merged_review.mkdir()
    review = {
        "schema": "camp_dp_v24_native_corpus_merged_independent_review_v1",
        "status": "passed",
        "source_assembly_root_sha256": merged_sha,
        "fixed_dp_head": FIXED_DP_HEAD,
        "check_count": 1,
        "failed_count": 0,
        "failed_checks": [],
        "checks": [{"name": "fixture", "passed": True}],
        "decision": {
            "action": "review_atom_availability_and_freeze_train_only_mask",
            "atom_availability_review_authorized": True,
            "training_authorized": False,
            "tuning_authorized": False,
            "outcome_access_authorized": False,
            "calibration_access_authorized": False,
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
        "review_only": True,
        "model_loaded": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "next_work_target": (
            "v24_native_corpus_atom_availability_and_freeze_review_only"
        ),
    }
    (merged_review / "review.json").write_bytes(_canonical(review))
    _clean_files(merged_review, camp_head="d" * 40)
    (merged_review / "stdout.txt").write_bytes(_canonical(review))
    merged_review_sha = seal_artifact(merged_review)
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return {
        "merged_root": merged,
        "expected_merged_root_sha256": merged_sha,
        "merged_review_root": merged_review,
        "expected_merged_review_root_sha256": merged_review_sha,
        "repo": ROOT,
        "expected_camp_head": current_head,
        "expected_snapshot_count": 2,
    }


def _produce_sealed_freeze(
    fixture: dict[str, object], output: Path
) -> tuple[dict, str]:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        freeze_atom_availability,
        seal_artifact,
    )

    resolver = lambda _repo, _head, _relative: "d" * 40
    bytes_resolver = _stable_provenance_bytes
    freeze = freeze_atom_availability(
        **fixture,
        output_dir=output,
        free_bytes=lambda: 20 * 1024**3,
        blob_resolver=resolver,
        blob_bytes_resolver=bytes_resolver,
        git_state_checker=lambda _repo, _head: None,
    )
    (output / "HEADS").write_text("CAMP_HEAD=test\n", encoding="ascii")
    (output / "COMMAND").write_text("test freeze\n", encoding="utf-8")
    (output / "atom_freeze.md").write_text("test\n", encoding="utf-8")
    (output / "stdout.txt").write_bytes(_canonical(freeze))
    (output / "stderr.txt").write_text("", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return freeze, seal_artifact(output)


def test_train_only_statistics_ignore_source_invalid_candidate_variation() -> None:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        compute_atom_statistics,
    )

    atoms = np.asarray(
        [
            _snapshot(seed=24001, second_atom2=2.0)["feature_payload"]["atom_matrix"],
            _snapshot(seed=24002, second_atom2=3.0)["feature_payload"]["atom_matrix"],
        ],
        dtype=np.float64,
    )
    valid = np.asarray([[True, True] + [False] * 6] * 2, dtype=bool)
    stats, scales, active = compute_atom_statistics(atoms, valid)

    assert active.tolist() == [True, False, True] + [False] * 11
    assert scales[0] == pytest.approx(1.0)
    assert scales[1] == pytest.approx(5.0)
    assert scales[2] == pytest.approx(np.percentile([2.0, 2.0, 2.0, 3.0], 95))
    assert stats[1]["variable_snapshot_count"] == 0
    assert stats[1]["exclusion_reason"] == (
        "no_source_valid_cross_candidate_range_above_1e-12"
    )
    assert all(row["source_available"] is True for row in stats)
    assert all(row["gt_future_allowed"] is False for row in stats)
    assert all(row["holdout_label_allowed"] is False for row in stats)
    assert all(row["depends_on_w"] is False for row in stats)
    assert all(row["depends_on_rank"] is False for row in stats)
    assert all(row["depends_on_selected_index"] is False for row in stats)


def test_atom_contract_drift_fails_closed_against_frozen_digest() -> None:
    from camp_core.integrations.diffusion_planner_causal_atoms import (
        CANONICAL_ATOM_CONTRACTS,
    )
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        _validated_atom_contracts,
    )

    drifted = list(CANONICAL_ATOM_CONTRACTS)
    drifted[0] = replace(drifted[0], holdout_label_allowed=True)
    with pytest.raises(ValueError, match="frozen v24 contract"):
        _validated_atom_contracts(drifted)


def test_snapshot_feature_identity_and_candidate_drift_fail_closed() -> None:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        _validate_snapshot,
    )

    payload = _snapshot(seed=24001, second_atom2=2.0)
    payload["feature_payload"]["map_id"] = "forbidden"
    with pytest.raises(ValueError, match="feature or sidecar"):
        _validate_snapshot(payload, phase="pilot", expected_sha256=_sha("snapshot"))

    payload = _snapshot(seed=24001, second_atom2=2.0)
    payload["sidecar"]["candidate_tensor_sha256_after"] = _sha("drift")
    with pytest.raises(ValueError, match="candidate immutability"):
        _validate_snapshot(payload, phase="pilot", expected_sha256=_sha("snapshot"))

    payload = _snapshot(seed=24001, second_atom2=2.0)
    payload["sidecar"]["actual_closed_loop_outcome"] = {"collision": False}
    with pytest.raises(ValueError, match="feature or sidecar"):
        _validate_snapshot(payload, phase="pilot", expected_sha256=_sha("snapshot"))

    payload = _snapshot(seed=24001, second_atom2=2.0)
    payload["sidecar"]["source_stratum"] = {
        "branch_intersection": False,
        "short_progress_opportunity": False,
        "tight_corridor": True,
        "traffic_light": False,
        "futureLabel": False,
    }
    with pytest.raises(ValueError, match="source-stratum"):
        _validate_snapshot(payload, phase="pilot", expected_sha256=_sha("snapshot"))

    payload = _snapshot(seed=24001, second_atom2=2.0)
    payload["sidecar"]["tick_index"] = 64
    with pytest.raises(ValueError, match="cadence"):
        _validate_snapshot(payload, phase="pilot", expected_sha256=_sha("snapshot"))


def test_source_provenance_requires_identical_atom_code_blobs() -> None:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        EXECUTOR_PROVENANCE_FILE,
        PROVENANCE_FILES,
        source_provenance,
    )

    stable = lambda _repo, _head, _relative: "d" * 40
    pilot_executor = subprocess.run(
        [
            "git",
            "show",
            "c697137d4769b22ca5db6a60fd570f13f949cbef:"
            + EXECUTOR_PROVENANCE_FILE,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout

    def stable_bytes(repo: Path, head: str, relative: str) -> bytes:
        if relative == EXECUTOR_PROVENANCE_FILE and head == "a" * 40:
            return pilot_executor
        return (repo / relative).read_bytes()

    result = source_provenance(
        repo=ROOT,
        pilot_head="a" * 40,
        remaining_head="b" * 40,
        current_head="c" * 40,
        blob_resolver=stable,
        blob_bytes_resolver=stable_bytes,
    )
    assert set(result["files"]) == set(PROVENANCE_FILES)
    assert all(
        item["identical_across_pilot_remaining_freeze"] is True
        for item in result["files"].values()
    )
    assert result["execution_semantic_contract"][
        "method_identical_across_pilot_remaining_freeze"
    ] is True

    def drift(_repo: Path, head: str, _relative: str) -> str:
        return ("e" if head == "b" * 40 else "d") * 40

    with pytest.raises(ValueError, match="source drift"):
        source_provenance(
            repo=ROOT,
            pilot_head="a" * 40,
            remaining_head="b" * 40,
            current_head="c" * 40,
            blob_resolver=drift,
            blob_bytes_resolver=stable_bytes,
        )

    with pytest.raises(ValueError, match="source drift"):
        source_provenance(
            repo=ROOT,
            pilot_head="a" * 40,
            remaining_head="b" * 40,
            current_head="c" * 40,
            blob_resolver=stable,
            blob_bytes_resolver=lambda _repo, _head, _relative: b"drift",
        )


def test_live_git_head_drift_fails_closed() -> None:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        _require_clean_git_state,
    )

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _require_clean_git_state(ROOT, head)
    with pytest.raises(ValueError, match="live CAMP HEAD"):
        _require_clean_git_state(ROOT, "0" * 40)


def test_executor_semantic_projection_rejects_critical_call_drift() -> None:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        EXECUTOR_PROVENANCE_FILE,
        _canonical_json_bytes,
        _executor_critical_projection,
        _method_ast_sha256,
    )

    pilot = b"class V24CorpusSnapshotWriter:\n    def __call__(self, value):\n        return value\n\nPHASE = 'pilot'\n"
    remaining = b"class V24CorpusSnapshotWriter:\n    def __call__(self, value):\n        return value\n\nPHASE = 'remaining'\n"
    drifted = b"class V24CorpusSnapshotWriter:\n    def __call__(self, value):\n        return value.copy()\n"
    pilot_hash = _method_ast_sha256(
        pilot, class_name="V24CorpusSnapshotWriter", method_name="__call__"
    )
    assert pilot_hash == _method_ast_sha256(
        remaining, class_name="V24CorpusSnapshotWriter", method_name="__call__"
    )
    assert pilot_hash != _method_ast_sha256(
        drifted, class_name="V24CorpusSnapshotWriter", method_name="__call__"
    )
    current = (ROOT / EXECUTOR_PROVENANCE_FILE).read_bytes()
    outside = current.replace(
        b".camp_dp_v24_native_corpus_remaining.lock",
        b".camp_dp_v24_native_corpus_remaining.test.lock",
        1,
    )
    critical = current.replace(b"max_steps=64", b"max_steps=65", 1)
    baseline = _canonical_json_bytes(
        _executor_critical_projection(current, legacy_pilot=False)
    )
    assert baseline == _canonical_json_bytes(
        _executor_critical_projection(outside, legacy_pilot=False)
    )
    assert baseline != _canonical_json_bytes(
        _executor_critical_projection(critical, legacy_pilot=False)
    )


def test_atom_freeze_and_independent_review_recompute_exactly(tmp_path: Path) -> None:
    from scripts.integrations.review_diffusion_planner_v24_atom_availability import (
        review_atom_freeze,
    )

    fixture = _fixture(tmp_path)
    output = tmp_path / "freeze"
    resolver = lambda _repo, _head, _relative: "d" * 40
    bytes_resolver = _stable_provenance_bytes
    freeze, freeze_sha = _produce_sealed_freeze(fixture, output)
    assert freeze["active_atom_mask"] == [True, False, True] + [False] * 11
    assert freeze["training_executed"] is False
    assert freeze["holdout_opened"] is False

    review = review_atom_freeze(
        freeze_root=output,
        expected_freeze_root_sha256=freeze_sha,
        merged_root=fixture["merged_root"],
        expected_merged_root_sha256=fixture["expected_merged_root_sha256"],
        merged_review_root=fixture["merged_review_root"],
        expected_merged_review_root_sha256=fixture[
            "expected_merged_review_root_sha256"
        ],
        repo=ROOT,
        expected_camp_head=fixture["expected_camp_head"],
        expected_snapshot_count=2,
        blob_resolver=resolver,
        blob_bytes_resolver=bytes_resolver,
        git_state_checker=lambda _repo, _head: None,
    )
    assert review["status"] == "passed"
    assert review["failed_count"] == 0
    assert review["recomputed"]["active_atom_mask"] == freeze["active_atom_mask"]
    assert review["decision"][
        "training_plan_tdd_static_preflight_authorized"
    ] is True
    assert review["decision"]["training_execution_authorized"] is False


@pytest.mark.parametrize(
    "tamper",
    [
        "merged_schema",
        "payload_modified",
        "route_seed_mutated",
        "tuning_executed",
        "source_fixed_dp",
        "review_claim",
        "review_fixed_dp",
        "review_failed_count",
        "review_failed_count_bool",
        "review_action",
        "review_tuning",
        "review_next_target",
        "review_not_only",
        "review_model",
        "review_candidate",
        "review_simulator_added",
    ],
)
def test_independent_review_rejects_coordinated_resealed_authority_drift(
    tmp_path: Path, tamper: str
) -> None:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        _validate_merged_authority,
        seal_artifact,
    )
    from scripts.integrations.review_diffusion_planner_v24_atom_availability import (
        review_atom_freeze,
    )

    fixture = _fixture(tmp_path)
    output = tmp_path / "freeze"
    freeze, _ = _produce_sealed_freeze(fixture, output)
    merged_root = Path(fixture["merged_root"])
    merged_review_root = Path(fixture["merged_review_root"])
    merged = json.loads((merged_root / "merged_summary.json").read_text())
    merged_review = json.loads((merged_review_root / "review.json").read_text())
    merged_tampers = {
        "merged_schema": ("schema", "malicious_resealed_schema"),
        "payload_modified": ("snapshot_payloads_modified", True),
        "route_seed_mutated": (
            "route_or_seed_removed_replaced_or_reordered",
            True,
        ),
        "tuning_executed": ("tuning_executed", True),
    }
    if tamper == "source_fixed_dp":
        pilot_root = Path(merged["source_artifacts"]["pilot"]["path"])
        (pilot_root / "HEADS").write_text(
            f"CAMP_HEAD={'a' * 40}\nFIXED_DP_HEAD={'0' * 40}\n",
            encoding="ascii",
        )
        merged["source_artifacts"]["pilot"]["root_sha256"] = seal_artifact(
            pilot_root
        )
    elif tamper in merged_tampers:
        field, value = merged_tampers[tamper]
        merged[field] = value
    elif tamper == "review_claim":
        merged_review["decision"]["claim_authorized"] = True
        merged_review["claim_authorized"] = True
    elif tamper == "review_fixed_dp":
        merged_review["fixed_dp_head"] = "0" * 40
    elif tamper == "review_failed_count":
        merged_review["failed_count"] = 1
        merged_review["failed_checks"] = ["fixture_failure"]
    elif tamper == "review_failed_count_bool":
        merged_review["failed_count"] = False
    elif tamper == "review_action":
        merged_review["decision"]["action"] = "train_now"
    elif tamper == "review_tuning":
        merged_review["decision"]["tuning_authorized"] = True
    elif tamper == "review_next_target":
        merged_review["next_work_target"] = "training_execution"
    elif tamper == "review_not_only":
        merged_review["review_only"] = False
    elif tamper == "review_model":
        merged_review["model_loaded"] = True
    elif tamper == "review_candidate":
        merged_review["candidate_generation_started"] = True
    elif tamper == "review_simulator_added":
        merged_review["simulator_executed"] = True
    else:
        raise AssertionError(tamper)
    (merged_root / "merged_summary.json").write_bytes(_canonical(merged))
    (merged_root / "stdout.txt").write_bytes(_canonical(merged))
    merged_sha = seal_artifact(merged_root)
    merged_review["source_assembly_root_sha256"] = merged_sha
    (merged_review_root / "review.json").write_bytes(_canonical(merged_review))
    (merged_review_root / "stdout.txt").write_bytes(_canonical(merged_review))
    merged_review_sha = seal_artifact(merged_review_root)
    freeze["source_merged_root_sha256"] = merged_sha
    freeze["source_merged_review_root_sha256"] = merged_review_sha
    (output / "atom_freeze.json").write_bytes(_canonical(freeze))
    (output / "stdout.txt").write_bytes(_canonical(freeze))
    freeze_sha = seal_artifact(output)
    resolver = lambda _repo, _head, _relative: "d" * 40
    bytes_resolver = _stable_provenance_bytes

    if tamper in {"review_tuning", "review_failed_count_bool"}:
        with pytest.raises(ValueError, match="merged independent review"):
            _validate_merged_authority(
                merged_root=merged_root,
                expected_merged_root_sha256=merged_sha,
                merged_review_root=merged_review_root,
                expected_merged_review_root_sha256=merged_review_sha,
                expected_snapshot_count=2,
            )

    review = review_atom_freeze(
        freeze_root=output,
        expected_freeze_root_sha256=freeze_sha,
        merged_root=merged_root,
        expected_merged_root_sha256=merged_sha,
        merged_review_root=merged_review_root,
        expected_merged_review_root_sha256=merged_review_sha,
        repo=ROOT,
        expected_camp_head=fixture["expected_camp_head"],
        expected_snapshot_count=2,
        blob_resolver=resolver,
        blob_bytes_resolver=bytes_resolver,
        git_state_checker=lambda _repo, _head: None,
    )
    assert review["status"] == "failed"
    if tamper in merged_tampers:
        assert "merged_authority" in review["failed_checks"]
    elif tamper == "source_fixed_dp":
        assert "review_input_valid" in review["failed_checks"]
    else:
        assert "merged_review_authority" in review["failed_checks"]
    assert review["decision"][
        "training_plan_tdd_static_preflight_authorized"
    ] is False


def test_atom_freeze_preserves_exact_ten_gib_fail_closed_boundary(
    tmp_path: Path,
) -> None:
    from scripts.integrations.freeze_diffusion_planner_v24_atom_availability import (
        MINIMUM_FREE_BYTES,
        freeze_atom_availability,
    )

    fixture = _fixture(tmp_path)
    with pytest.raises(RuntimeError, match="10 GiB disk floor"):
        freeze_atom_availability(
            **fixture,
            output_dir=tmp_path / "freeze",
            free_bytes=lambda: MINIMUM_FREE_BYTES,
            blob_resolver=lambda _repo, _head, _relative: "d" * 40,
            blob_bytes_resolver=lambda repo, _head, relative: (
                repo / relative
            ).read_bytes(),
            git_state_checker=lambda _repo, _head: None,
        )
