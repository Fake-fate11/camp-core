from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner import CAMPSelector
from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    RetainedScenarioCapabilityFailure,
    ScenarioCapabilityReason,
)
from scripts.integrations import (
    build_diffusion_planner_v25_static_atom_ledger as builder,
    review_diffusion_planner_v25_stage_a0_authority as a0,
    run_diffusion_planner_v25_controlled_training_corpus as corpus,
    validate_diffusion_planner_v25_static_atom_ledger as validator,
)


def _rewrite_manifest(root: Path, text: str) -> str:
    (root / "SHA256SUMS").write_bytes(text.encode("utf-8"))
    digest = hashlib.sha256((root / "SHA256SUMS").read_bytes()).hexdigest()
    (root / "ROOT_SHA256SUMS").write_bytes(
        f"{digest}  SHA256SUMS\n".encode("ascii")
    )
    return digest


def _sealed_root(tmp_path: Path, name: str = "artifact") -> tuple[Path, str]:
    root = tmp_path / name
    (root / "nested").mkdir(parents=True)
    (root / "nested" / "payload.json").write_text("{}\n", encoding="utf-8")
    return root, seal_artifact(root, label=name)


def test_shared_seal_verifier_accepts_exact_recursive_inventory(tmp_path: Path) -> None:
    root, digest = _sealed_root(tmp_path)
    receipt = verify_complete_seal(root, digest, label="test")
    assert receipt["file_count"] == 1
    assert receipt["manifest_paths"] == ["nested/payload.json"]


def test_shared_seal_verifier_rejects_unlisted_payload(tmp_path: Path) -> None:
    root, digest = _sealed_root(tmp_path)
    (root / "unlisted.txt").write_text("not sealed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory is inexact"):
        verify_complete_seal(root, digest, label="test")


@pytest.mark.parametrize("mutation", ["traversal", "duplicate", "empty"])
def test_shared_seal_verifier_rejects_unsafe_duplicate_or_empty_manifest(
    tmp_path: Path, mutation: str
) -> None:
    root, _ = _sealed_root(tmp_path, mutation)
    line = (root / "SHA256SUMS").read_text(encoding="utf-8").strip()
    digest, _relative = line.split("  ", 1)
    if mutation == "traversal":
        manifest = f"{digest}  ../outside.json\n"
        pattern = "unsafe manifest path"
    elif mutation == "duplicate":
        manifest = f"{line}\n{line}\n"
        pattern = "duplicate manifest path"
    else:
        manifest = ""
        pattern = "must be nonempty"
    root_digest = _rewrite_manifest(root, manifest)
    with pytest.raises(ValueError, match=pattern):
        verify_complete_seal(root, root_digest, label="test")


def test_shared_seal_verifier_rejects_symlink_when_supported(tmp_path: Path) -> None:
    root, digest = _sealed_root(tmp_path)
    link = root / "link.json"
    try:
        os.symlink(root / "nested" / "payload.json", link)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="symlink"):
        verify_complete_seal(root, digest, label="test")


@pytest.mark.parametrize(
    "weights,pattern",
    [
        (np.full(14, np.nan), "finite"),
        (np.full(14, np.inf), "finite"),
        (np.r_[-1.0, np.ones(13)], "nonnegative"),
        (np.zeros(14), "positive total"),
        (np.full(14, np.finfo(np.float64).max), "finite positive total"),
    ],
)
def test_generic_static14d_weights_fail_closed(
    weights: np.ndarray, pattern: str
) -> None:
    with pytest.raises(ValueError, match=pattern):
        CAMPSelector(
            atom_scales=np.ones(14),
            static_weights=weights,
            mode="static",
        )


def test_generic_static_and_learned_fallback_share_strict_simplex_helper() -> None:
    main = np.arange(1.0, 15.0)
    fallback = np.arange(14.0, 0.0, -1.0)
    selector = CAMPSelector(
        atom_scales=np.ones(14),
        static_weights=main,
        mode="static",
        fallback_mode="learned",
        fallback_atom_scales=np.ones(14),
        fallback_static_weights=fallback,
    )
    np.testing.assert_allclose(selector.static_weights.sum(), 1.0, atol=1e-12)
    np.testing.assert_allclose(
        selector.fallback_static_weights.sum(), 1.0, atol=1e-12
    )
    with pytest.raises(ValueError, match="finite positive total"):
        CAMPSelector(
            atom_scales=np.ones(14),
            static_weights=main,
            mode="static",
            fallback_mode="learned",
            fallback_atom_scales=np.ones(14),
            fallback_static_weights=np.full(14, np.finfo(np.float64).max),
        )


def test_probe_case_authority_selects_exact_formal_identity0_and_red_easy() -> None:
    assert a0.FORMAL_SOURCE_CAMP_HEAD == "ff02838780c7b2fa7fc557680e43d85967ee843e"
    identity0 = {
        "scenario_id": "1" * 64,
        "family": "lead_vehicle_hard_brake",
        "tier": "easy",
        "runner_eligible": True,
    }
    red_easy = {
        "scenario_id": "2" * 64,
        "family": "red_light_phase_timing",
        "tier": "easy",
        "runner_eligible": True,
    }
    extra = {
        "scenario_id": "3" * 64,
        "family": "red_light_phase_timing",
        "tier": "borderline",
        "runner_eligible": True,
    }
    assert a0._expected_probe_cases({"train": [identity0, extra, red_easy]}) == [
        identity0,
        red_easy,
    ]
    with pytest.raises(ValueError, match="identity0"):
        a0._expected_probe_cases({"train": [red_easy, identity0]})


def test_stage_a_numeric_fixture_is_independently_recomputed() -> None:
    scales = np.array(
        json.loads(builder.CORRECTED_GENERATION_SCALES.read_text(encoding="utf-8"))[
            "scales"
        ],
        dtype=np.float64,
    )
    fixture = builder._numeric_fixture(scales)
    numeric = validator._independent_numeric_recompute(fixture)
    progress = validator._validate_progress_fixture(fixture)
    assert all(numeric["checks"].values())
    assert all(progress["checks"].values())
    assert numeric["independent_selected_index"] == 0


def test_stage_a_independent_algebra_covers_jerk_partition_and_speed_thresholds() -> None:
    receipt = validator._independent_kinematic_algebra()
    assert receipt["checks"] == {
        "jerk_full_equals_early_plus_late": True,
        "speed_thresholds_exact_order": True,
        "speed_thresholds_distinct_on_fixture": True,
    }


def test_stage_a_validator_contract_checks_are_strict_booleans() -> None:
    source = Path(validator.__file__).read_text(encoding="utf-8")
    assert 'and bool(scale.get("red_binary_alternative"))' in source


def test_all_21_red_capability_failures_are_scientifically_ineligible() -> None:
    reason = ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE.value
    rows = [
        {
            "scenario_id": "f" * 64,
            "family": "lead_vehicle_hard_brake",
            "status": "complete",
            "snapshot_count": 64,
        }
    ]
    allowlist: dict[str, dict[str, object]] = {}
    authority: dict[str, dict[str, object]] = {}
    tiers = ["easy"] * 6 + ["borderline"] * 10 + ["high_risk"] * 5
    for index, tier in enumerate(tiers):
        scenario_id = f"{index + 100:064x}"
        allowlist[scenario_id] = {
            "family": "red_light_phase_timing",
            "reasons": [reason],
        }
        authority[scenario_id] = {
            "tier": tier,
            "source_map_sha256": f"{index % 4 + 1:064x}",
            "mapped_traffic_light": True,
        }
        rows.append(
            {
                "scenario_id": scenario_id,
                "family": "red_light_phase_timing",
                "status": "failed",
                "snapshot_count": 0,
                "failure_type": RetainedScenarioCapabilityFailure.__name__,
                "failure_reason": "typed capability failure",
                "capability_failure": {
                    "scenario_id": scenario_id,
                    "family": "red_light_phase_timing",
                    "reason": reason,
                },
            }
        )
    with pytest.raises(
        corpus.ArtifactContractViolation, match="scientifically ineligible"
    ):
        corpus.validate_terminal_acceptance(
            rows,
            snapshot_index_count=64,
            expected_identity_count=22,
            capability_allowlist=allowlist,
            expected_red_authority=authority,
        )
