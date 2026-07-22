from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import (
    FixedDpCandidateGenerationCapabilityFailure,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_calibration_execution import (
    execute_candidate0_calibration_units,
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
from scripts.integrations.review_diffusion_planner_v25_candidate0_calibration import (
    _bind_reviewed_runtime_receipts as _review_runtime_bindings,
    _review_complete,
    _review_failure,
)
from scripts.integrations.run_diffusion_planner_v25_candidate0_calibration import (
    _bind_reviewed_runtime_receipts as _production_runtime_bindings,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SHA = "1" * 64


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _inputs(tmp_path: Path) -> tuple[dict, dict, dict, dict]:
    suite = build_signal_complete_suite("calibration")
    map_root = tmp_path / "maps"
    for relative, payload in suite["map_payloads"].items():
        path = map_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    plan = build_signal_complete_execution_plan("calibration")
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity,
            map_artifact=map_root,
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    }
    route_assets = {
        identity["route_identity_sha256"]: {
            "name": identity["route_identity_sha256"],
            "path": str(tmp_path / "routes" / f"{identity['route_identity_sha256']}.pkl"),
            "sha256": SHA,
        }
        for identity in plan["identities"]
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
    return plan, prepared, route_assets, probe


def _native(config: dict) -> dict:
    ordinal = config["signal_complete_plan_authority"]["unit_ordinal"]
    seed = config["seeds"]["scenario"]
    route = config["routes"][0]
    ticks = [
        {
            "tick_index": index,
            "selected_index": 0,
            "input_sha256": f"{ordinal * 1000 + index + 1:064x}",
            "default_output_sha256": f"{ordinal * 1000 + index + 101:064x}",
            "candidate_tensor_sha256_before": f"{ordinal * 1000 + index + 201:064x}",
            "candidate_tensor_sha256_after": f"{ordinal * 1000 + index + 201:064x}",
            "candidate0_operational_default": True,
            "selection_policy": "candidate0_operational_default",
            "score_contract": "candidate0_operational_default",
            "eligibility_mask_name": "candidate0_operational_default",
            "pre_decision_speed_mps": 8.0,
            "safety": {"speed_mps": 7.9 if index == 0 else 8.0},
        }
        for index in range(64)
    ]
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "arm": "dp",
        "fixed_dp_head": FIXED_DP_HEAD,
        "route_name": route["name"],
        "route_sha256": route["sha256"],
        "scenario_seed": seed,
        "initial_state_sha256": f"{ordinal + 30001:064x}",
        "initial_input_sha256": ticks[0]["input_sha256"],
        "ticks": ticks,
        "secondary": {
            "route_progress_m": 100.0,
            "route_completion_rate": 0.9,
            "mean_abs_jerk_mps3": 0.5,
            "max_jerk_mps3": 1.0,
            "mean_abs_lateral_acceleration_mps2": 0.2,
            "max_abs_lateral_acceleration_mps2": 0.5,
        },
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


def _reviewed_runtime_receipts(
    plan: dict, prepared: dict[str, dict]
) -> list[dict]:
    receipts: list[dict] = []
    for identity in plan["identities"]:
        scenario = identity["scenario_identity_sha256"]
        runtime = prepared[scenario]
        case = runtime["case"]
        chain = json.loads(json.dumps(runtime["mapped_signal_authority"]))
        without_hash = {
            key: value for key, value in chain.items() if key != "source_chain_sha256"
        }
        chain["source_chain_sha256"] = hashlib.sha256(
            _canonical_bytes(without_hash)
        ).hexdigest()
        phase = identity["controlled_current_phase"]
        if phase is None:
            phase = "green"
        receipts.append(
            {
                "identity_ordinal": identity["identity_ordinal"],
                "scenario_identity_sha256": scenario,
                "scenario_id": case["scenario_id"],
                "scenario_family": identity["scenario_family"],
                "risk_tier": identity["risk_tier"],
                "benchmark_stratum": identity["benchmark_stratum"],
                "map_sha256": identity["map_sha256"],
                "map_geometry_sha256": identity["map_geometry_sha256"],
                "corridor_sha256": identity["corridor_sha256"],
                "intersection_sha256": identity["intersection_sha256"],
                "route_identity_sha256": identity["route_identity_sha256"],
                "source_chain_sha256": chain["source_chain_sha256"],
                "source_chain": chain,
                "phase_authority_mode": identity["phase_authority_mode"],
                "current_phase": phase,
                "runtime_receipt": {"current_phase": phase},
                "phase_remaining_available": False,
                "future_phase_schedule_consumed": False,
                "outcome_fields_consumed": [],
            }
        )
    return receipts


def test_candidate0_calibration_executes_exact_denominator_and_retains_typed_failure(
    tmp_path: Path,
) -> None:
    plan, prepared, route_assets, probe = _inputs(tmp_path)

    def run_one(config: dict, _output: Path) -> dict:
        if config["signal_complete_plan_authority"]["unit_ordinal"] == 7:
            raise _capability_failure()
        return _native(config)

    report = execute_candidate0_calibration_units(
        plan=plan,
        probe_template=probe,
        prepared_runtime_by_scenario=prepared,
        route_asset_by_identity=route_assets,
        dp_repo=tmp_path / "Diffusion-Planner",
        output_dir=tmp_path / "execution",
        run_one=run_one,
    )
    assert report["planned_run_count"] == 100
    assert report["terminal_run_count"] == 100
    assert report["complete_run_count"] == 99
    assert report["retained_fixed_dp_capability_failure_count"] == 1
    assert report["paired_eligible_rate"] == 0.99
    assert report["status"] == "passed_candidate0_calibration_execution"
    assert len(list((tmp_path / "execution" / "runs").iterdir())) == 100
    failures = list(
        (tmp_path / "execution" / "fixed_dp_capability_failures").iterdir()
    )
    assert {path.suffix for path in failures} == {".bin", ".json"}
    failure_result = json.loads(
        (tmp_path / "execution" / "run_results.json").read_text(encoding="utf-8")
    )[7]
    _review_failure(
        tmp_path / "execution",
        failure_result,
        unit=plan["execution_units"][7],
        identity=next(
            row
            for row in plan["identities"]
            if row["scenario_identity_sha256"]
            == plan["execution_units"][7]["scenario_identity_sha256"]
        ),
    )


def test_candidate0_calibration_binds_reviewed_runtime_rows_before_execution(
    tmp_path: Path,
) -> None:
    plan, prepared, _route_assets, _probe = _inputs(tmp_path)
    runtime_artifact = tmp_path / "runtime_authority"
    runtime_artifact.mkdir()
    receipts = _reviewed_runtime_receipts(plan, prepared)
    receipt_path = runtime_artifact / "runtime_source_receipts.json"
    receipt_path.write_bytes(_canonical_bytes(receipts))

    production = _production_runtime_bindings(
        plan=plan,
        prepared_runtime_by_scenario=prepared,
        runtime_artifact=runtime_artifact,
    )
    independent = _review_runtime_bindings(
        plan=plan,
        prepared_runtime_by_scenario=prepared,
        runtime_artifact=runtime_artifact,
    )
    assert production == independent
    assert set(production) == {
        row["scenario_identity_sha256"] for row in plan["identities"]
    }

    receipts[0]["route_identity_sha256"] = "f" * 64
    receipt_path.write_bytes(_canonical_bytes(receipts))
    with pytest.raises(ValueError, match="metadata drifted"):
        _production_runtime_bindings(
            plan=plan,
            prepared_runtime_by_scenario=prepared,
            runtime_artifact=runtime_artifact,
        )
    with pytest.raises(ValueError, match="metadata drifted"):
        _review_runtime_bindings(
            plan=plan,
            prepared_runtime_by_scenario=prepared,
            runtime_artifact=runtime_artifact,
        )


def test_independent_complete_reviewer_binds_route_and_candidate0_ticks(
    tmp_path: Path,
) -> None:
    plan, _prepared, route_assets, _probe = _inputs(tmp_path)
    unit = plan["execution_units"][0]
    identity = next(
        row
        for row in plan["identities"]
        if row["scenario_identity_sha256"] == unit["scenario_identity_sha256"]
    )
    config = {
        "signal_complete_plan_authority": {"unit_ordinal": unit["unit_ordinal"]},
        "seeds": {"scenario": unit["seed"]},
        "routes": [route_assets[identity["route_identity_sha256"]]],
    }
    result = {
        "native_receipt": _native(config),
        "failure_receipt": None,
    }
    _review_complete(
        result,
        unit=unit,
        identity=identity,
        route_asset=route_assets[identity["route_identity_sha256"]],
    )
    result["native_receipt"]["ticks"][63]["selected_index"] = 1
    with pytest.raises(ValueError, match="tick authority drifted"):
        _review_complete(
            result,
            unit=unit,
            identity=identity,
            route_asset=route_assets[identity["route_identity_sha256"]],
        )


def test_candidate0_calibration_does_not_retain_untyped_errors(tmp_path: Path) -> None:
    plan, prepared, route_assets, probe = _inputs(tmp_path)

    def run_one(_config: dict, _output: Path) -> dict:
        raise ValueError("ordinary runner failure")

    with pytest.raises(ValueError, match="ordinary runner failure"):
        execute_candidate0_calibration_units(
            plan=plan,
            probe_template=probe,
            prepared_runtime_by_scenario=prepared,
            route_asset_by_identity=route_assets,
            dp_repo=tmp_path / "Diffusion-Planner",
            output_dir=tmp_path / "execution",
            run_one=run_one,
        )


def test_candidate0_calibration_rejects_route_asset_receipt_drift(
    tmp_path: Path,
) -> None:
    plan, prepared, route_assets, probe = _inputs(tmp_path)

    def run_one(config: dict, _output: Path) -> dict:
        native = _native(config)
        native["route_sha256"] = "2" * 64
        return native

    with pytest.raises(ValueError, match="native receipt drifted"):
        execute_candidate0_calibration_units(
            plan=plan,
            probe_template=probe,
            prepared_runtime_by_scenario=prepared,
            route_asset_by_identity=route_assets,
            dp_repo=tmp_path / "Diffusion-Planner",
            output_dir=tmp_path / "execution",
            run_one=run_one,
        )
