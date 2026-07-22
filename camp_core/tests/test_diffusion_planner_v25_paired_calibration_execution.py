from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import (
    FixedDpCandidateGenerationCapabilityFailure,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration import (
    build_paired_calibration_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration_execution import (
    execute_paired_calibration_units,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_runtime_case,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SHA = "1" * 64


def _inputs(tmp_path: Path) -> tuple[dict, dict, dict, dict, dict]:
    suite = build_signal_complete_suite("calibration")
    map_root = tmp_path / "maps"
    for relative, payload in suite["map_payloads"].items():
        path = map_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    base = build_signal_complete_execution_plan("calibration")
    paired = build_paired_calibration_execution_plan(base)
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity, map_artifact=map_root, seeds=base["seeds"]
        )
        for identity in base["identities"]
    }
    routes = {
        identity["route_identity_sha256"]: {
            "name": identity["route_identity_sha256"],
            "path": str(tmp_path / "routes" / f"{identity['route_identity_sha256']}.pkl"),
            "sha256": SHA,
        }
        for identity in base["identities"]
    }
    probe = {
        "fixed_dp": {
            "head": FIXED_DP_HEAD,
            "repo": str(tmp_path / "ignored"),
            "checkpoint": {"path": str(tmp_path / "model.pt"), "sha256": SHA},
            "args_json": {"path": str(tmp_path / "args.json"), "sha256": SHA},
            "native_source_sha256": {"replay.py": SHA},
        },
        "selector": {
            "atom_scales": {"path": str(tmp_path / "scales.json"), "sha256": SHA},
            "weights": {"path": str(tmp_path / "weights.json"), "sha256": SHA},
            "score_contract": "score_k(w)=a_k^T w",
            "nonnegative_simplex": True,
        },
        "spawn_config": {},
    }
    return base, paired, prepared, routes, probe


def _selector_authority(tmp_path: Path) -> dict:
    return {
        "training_artifact": {"path": str(tmp_path / "training"), "root_sha256": "2" * 64},
        "training_review_artifact": {"path": str(tmp_path / "review"), "root_sha256": "3" * 64},
        "model_registry_sha256": "4" * 64,
        "training_scale_sha256": "5" * 64,
        "context_scaler_sha256": "6" * 64,
        "atom_scales": {"path": str(tmp_path / "scales.json"), "sha256": "7" * 64},
        "static14d_weights": {"path": str(tmp_path / "weights.npy"), "sha256": "8" * 64},
    }


def _native(config: dict, plan_arm: str) -> dict:
    arm = "dp" if plan_arm == "candidate0_operational_default" else "camp"
    ticks = []
    for index in range(64):
        tick = {"tick_index": index, "selected_index": 0}
        if plan_arm == "camp_scene14d_no_v2i":
            tick["v25_scene_selector"] = {"model_name": "CAMP-Scene14D"}
            tick["v25_context"] = {
                "source_receipt": {"phase_remaining_available": False}
            }
        ticks.append(tick)
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "arm": arm,
        "fixed_dp_head": FIXED_DP_HEAD,
        "route_name": config["routes"][0]["name"],
        "route_sha256": config["routes"][0]["sha256"],
        "scenario_seed": config["seeds"]["scenario"],
        "ticks": ticks,
        "claim_authorized": False,
    }


def _capability_failure() -> FixedDpCandidateGenerationCapabilityFailure:
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[..., 2] = 1.0
    candidates[5, 11, 2:4] = 0.0
    candidate0_sha = hashlib.sha256(
        np.ascontiguousarray(candidates[0]).tobytes(order="C")
    ).hexdigest()
    identity = {
        "elementwise_equal": True,
        "max_abs_difference": 0.0,
        "default_output_sha256": candidate0_sha,
        "candidate0_sha256": candidate0_sha,
        "native_ranked_k8": False,
    }
    with pytest.raises(FixedDpCandidateGenerationCapabilityFailure) as caught:
        validate_fixed_k8_candidate_tensor(
            candidates,
            tick_index=7,
            default_output_sha256=candidate0_sha,
            default_candidate0_identity=identity,
        )
    return caught.value


def test_paired_calibration_executes_all_arm_terminals_and_retains_pair_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, paired, prepared, routes, probe = _inputs(tmp_path)
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    monkeypatch.setattr(
        run_diffusion_planner_dp_camp_v21_native,
        "validate_native_arm_receipt",
        lambda *_args, **_kwargs: None,
    )
    eligible_group = next(
        name for name, count in base["family_tier_counts"].items() if count >= 3
    )
    failure_identity = next(
        row
        for row in base["identities"]
        if f"{row['scenario_family']}/{row['risk_tier']}" == eligible_group
    )
    failure_unit = next(
        row["unit_ordinal"]
        for row in paired["execution_units"]
        if row["scenario_identity_sha256"]
        == failure_identity["scenario_identity_sha256"]
    )

    def run_one(config: dict, _run_dir: Path, plan_arm: str) -> dict:
        if (
            config["signal_complete_plan_authority"]["unit_ordinal"]
            == failure_unit
            and plan_arm == "camp_static14d"
        ):
            raise _capability_failure()
        return _native(config, plan_arm)

    report = execute_paired_calibration_units(
        calibration_plan=base,
        paired_plan=paired,
        probe_template=probe,
        prepared_runtime_by_scenario=prepared,
        route_asset_by_identity=routes,
        runtime_selector_authority=_selector_authority(tmp_path),
        dp_repo=tmp_path / "Diffusion-Planner",
        output_dir=tmp_path / "execution",
        run_one=run_one,
    )
    assert report["planned_arm_run_count"] == 300
    assert report["terminal_arm_run_count"] == 300
    assert report["complete_arm_run_count"] == 299
    assert report["retained_fixed_dp_capability_failure_count"] == 1
    assert report["paired_eligible_pair_count"] == 99
    assert report["paired_eligible_rate"] == 0.99
    assert report["coverage_gate_passed"] is True
    assert report["status"] == "passed_paired_calibration_execution"
    assert len(list((tmp_path / "execution" / "runs").iterdir())) == 300


def test_paired_calibration_does_not_retain_untyped_failure(
    tmp_path: Path,
) -> None:
    base, paired, prepared, routes, probe = _inputs(tmp_path)

    def run_one(_config: dict, _run_dir: Path, _plan_arm: str) -> dict:
        raise ValueError("ordinary calibration runner failure")

    with pytest.raises(ValueError, match="ordinary calibration runner failure"):
        execute_paired_calibration_units(
            calibration_plan=base,
            paired_plan=paired,
            probe_template=probe,
            prepared_runtime_by_scenario=prepared,
            route_asset_by_identity=routes,
            runtime_selector_authority=_selector_authority(tmp_path),
            dp_repo=tmp_path / "Diffusion-Planner",
            output_dir=tmp_path / "execution",
            run_one=run_one,
        )
