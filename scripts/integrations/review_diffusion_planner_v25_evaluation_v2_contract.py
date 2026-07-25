from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)


SCHEMA_VERSION = "camp_dp_v25_evaluation_v2_contract_review_artifact_v1"
EXPECTED_EXECUTION_ROOT = (
    "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
)
EXPECTED_FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_GRIDS = {
    "clearance_le_m": [0.0, 0.5, 1.0, 2.0],
    "ttc_le_s": [0.5, 1.0, 2.0, 3.0, 5.0],
    "closing_ge_mps": [0.5, 1.0, 2.0, 5.0],
    "drac_ge_mps2": [0.5, 1.0, 2.0, 3.0, 5.0],
    "speed_tolerance_mps": [0.0, 0.05, 0.1, 0.2],
    "acceleration_abs_gt_mps2": [0.5, 1.0, 2.0, 3.0],
    "jerk_abs_gt_mps3": [0.5, 1.0, 2.0, 5.0],
    "latency_deadline_ms": [50.0, 100.0, 200.0, 500.0, 1000.0],
}


def review_contract(
    *,
    output: Path,
    contract_dir: Path,
    contract_root: str,
    execution: Path,
    execution_root: str,
) -> str:
    if execution_root != EXPECTED_EXECUTION_ROOT:
        raise ValueError("independent Evaluation v2 execution root drifted")
    verify_complete_seal(contract_dir, contract_root, label="Evaluation v2 contract")
    verify_complete_seal(execution, execution_root, label="Fresh B4 execution")
    producer = _object(contract_dir / "report.json")
    _literal_contract_review(producer)
    independent_source_audit = _independent_source_audit(execution)
    producer_audit = producer["source_capability_audit"]
    for name in (
        "run_config_count",
        "candidate0_supplementary_raw_file_existence_count",
        "controlled_arm_config_count",
        "naturalistic_arm_config_count",
        "unique_map_count",
        "unique_route_count",
        "all_map_assets_present_and_sha_bound",
        "all_route_assets_present_and_sha_bound",
    ):
        if producer_audit.get(name) != independent_source_audit[name]:
            raise ValueError(f"independent Evaluation v2 source audit drifted: {name}")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_outcome_free_evaluation_v2_contract_review",
        "contract_binding": {
            "path": str(contract_dir.resolve()),
            "root_sha256": contract_root,
        },
        "execution_binding": {
            "path": str(execution.resolve()),
            "root_sha256": execution_root,
        },
        "independent_source_capability_audit": independent_source_audit,
        "literal_oracle": {
            "producer_contract_module_imported": False,
            "formula_literals_reconstructed": True,
            "grid_literals_reconstructed": True,
            "root_literals_reconstructed": True,
            "claim_policy_reconstructed": True,
            "sample_accounting_reconstructed": True,
        },
        "reviewer_head": _git_head(),
        "outcome_values_read": False,
        "native_receipt_values_read": False,
        "evaluation_rows_read": False,
        "raw_execution_outcomes_read": False,
        "fresh_execution_rerun": False,
        "corrected_evaluation_rerun": False,
        "scientific_or_continuation_cas_written": False,
        "claim_authorized": False,
    }
    return _write_atomic(output, report)


def _literal_contract_review(producer: dict[str, Any]) -> None:
    if set(producer) != {
        "schema_version",
        "status",
        "contract",
        "source_capability_audit",
        "execution_binding",
        "implementation_head",
        "outcome_values_read",
        "native_receipt_values_read",
        "evaluation_rows_read",
        "raw_execution_outcomes_read",
        "fresh_execution_rerun",
        "corrected_evaluation_rerun",
        "scientific_or_continuation_cas_written",
        "claim_authorized",
    }:
        raise ValueError("independent Evaluation v2 producer fields drifted")
    if (
        producer["schema_version"] != "camp_dp_v25_evaluation_v2_contract_artifact_v1"
        or producer["status"] != "sealed_outcome_free_evaluation_v2_contract"
        or producer["execution_binding"]["root_sha256"] != EXPECTED_EXECUTION_ROOT
        or any(
            producer[name] is not False
            for name in (
                "outcome_values_read",
                "native_receipt_values_read",
                "evaluation_rows_read",
                "raw_execution_outcomes_read",
                "fresh_execution_rerun",
                "corrected_evaluation_rerun",
                "scientific_or_continuation_cas_written",
                "claim_authorized",
            )
        )
    ):
        raise ValueError("independent Evaluation v2 producer authority drifted")
    contract = producer["contract"]
    if (
        type(contract) is not dict
        or contract.get("schema_version") != "camp_dp_v25_evaluation_v2_contract_v1"
        or contract.get("result_semantics")
        != "exploratory_posthoc_not_claim_authorizing"
        or contract.get("bindings", {}).get("execution_root_sha256")
        != EXPECTED_EXECUTION_ROOT
        or contract.get("bindings", {}).get("fixed_dp_head") != EXPECTED_FIXED_DP
        or contract.get("denominator")
        != {
            "pair_count": 500,
            "arm_count": 1500,
            "ticks_per_arm": 64,
            "tick_count": 96000,
            "fresh_execution_reused": True,
            "fresh_execution_rerun": False,
            "complete_case_denominator_shrinkage_allowed": False,
        }
    ):
        raise ValueError("independent Evaluation v2 contract identity drifted")
    policy = contract.get("claim_policy", {})
    if (
        policy.get("legacy_benchmark_v1_values_mutable") is not False
        or policy.get("legacy_preregistration_or_claim_mutable") is not False
        or policy.get("weighted_total_score_generated") is not False
        or policy.get("different_denominators_mixed") is not False
        or policy.get("v2_scientific_hard_gate") != "not_prospectively_defined_for_v2"
        or policy.get("v2_claim_authorized") is not False
    ):
        raise ValueError("independent Evaluation v2 claim policy drifted")
    grids = contract.get("grids", {})
    for name, expected in EXPECTED_GRIDS.items():
        if grids.get(name, {}).get("values") != expected:
            raise ValueError(f"independent Evaluation v2 grid drifted: {name}")
    catalog = contract.get("endpoint_catalog", {})
    if set(catalog) != {
        "collision",
        "dynamic_proximity",
        "road_containment",
        "certified_red_crossing",
        "speed",
        "route",
        "vehicle_body_planar_kinematic_proxy",
        "latency",
    }:
        raise ValueError("independent Evaluation v2 endpoint catalog drifted")
    if (
        "full frozen ego/actor OBB polygon intersection"
        not in catalog["collision"]["formula"]
        or "continuous SAT entry time"
        not in catalog["dynamic_proximity"]["formula"]["geometry_ttc"]
        or "area(F_t minus union(D_t))" not in catalog["road_containment"]["formula"]
        or "full front-edge swept geometry"
        not in catalog["certified_red_crossing"]["formula"]
        or "stateful ordered-route segment projection"
        not in catalog["route"]["formula"]
        or "64 positions -> 63 interval velocities -> 62 accelerations"
        not in catalog["vehicle_body_planar_kinematic_proxy"]["formula"]
    ):
        raise ValueError("independent Evaluation v2 formula literal drifted")
    geometry = contract.get("geometry", {})
    if (
        geometry.get("dt_s") != 0.1
        or geometry.get("geom_eps") != 1e-9
        or geometry.get("boxcar_padding") is not False
        or geometry.get("boxcar_kernel") != [1.0 / 11.0] * 11
        or not math.isclose(sum(geometry["boxcar_kernel"]), 1.0)
    ):
        raise ValueError("independent Evaluation v2 geometry contract drifted")


def _independent_source_audit(execution: Path) -> dict[str, Any]:
    runs = sorted(path for path in (execution / "runs").iterdir() if path.is_dir())
    maps: set[str] = set()
    routes: set[str] = set()
    supplementary = controlled = naturalistic = 0
    for run in runs:
        config = _object(run / "run_config.json")
        spawn = config.get("spawn_config")
        if type(spawn) is not dict or not {
            "ego_length",
            "ego_width",
            "ego_wheelbase",
            "goal_tolerance_m",
            "goal_pass_window_m",
        }.issubset(spawn):
            raise ValueError("independent Evaluation v2 spawn source drifted")
        case = config.get("signal_complete_runtime", {}).get("case")
        if type(case) is not dict or type(case.get("actors")) is not list:
            raise ValueError("independent Evaluation v2 case source drifted")
        if case["actors"]:
            controlled += 1
        else:
            naturalistic += 1
        for actor in case["actors"]:
            if type(actor) is not dict or not {
                "id",
                "length_m",
                "width_m",
            }.issubset(actor):
                raise ValueError("independent Evaluation v2 actor source drifted")
        map_asset = config.get("map")
        route_assets = config.get("routes")
        if type(route_assets) is not list or len(route_assets) != 1:
            raise ValueError("independent Evaluation v2 route inventory drifted")
        maps.add(_asset(map_asset, "map"))
        routes.add(_asset(route_assets[0], "route"))
        if (run / "candidate0_supplementary_actual_native_raw.json").is_file():
            supplementary += 1
    result = {
        "run_config_count": len(runs),
        "candidate0_supplementary_raw_file_existence_count": supplementary,
        "controlled_arm_config_count": controlled,
        "naturalistic_arm_config_count": naturalistic,
        "unique_map_count": len(maps),
        "unique_route_count": len(routes),
        "all_map_assets_present_and_sha_bound": True,
        "all_route_assets_present_and_sha_bound": True,
    }
    if (
        result["run_config_count"] != 1500
        or supplementary != 500
        or controlled != 960
        or naturalistic != 540
        or len(maps) != 25
    ):
        raise ValueError("independent Evaluation v2 source denominator drifted")
    return result


def _asset(value: Any, label: str) -> str:
    if type(value) is not dict:
        raise ValueError(f"independent {label} asset drifted")
    path = Path(str(value.get("path", ""))).resolve()
    expected = value.get("sha256")
    if (
        type(expected) is not str
        or len(expected) != 64
        or not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != expected
    ):
        raise ValueError(f"independent {label} asset SHA drifted")
    return expected


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("Evaluation v2 contract review output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "role": "independent_evaluation_v2_contract_review",
                    "reviewer_head": report["reviewer_head"],
                    "contract_root_sha256": report["contract_binding"]["root_sha256"],
                    "execution_root_sha256": report["execution_binding"]["root_sha256"],
                    "fixed_dp_head": EXPECTED_FIXED_DP,
                }
            )
        )
        root = seal_artifact(staging, label="V25 Evaluation v2 contract review")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 Evaluation v2 contract review")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--execution-root", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = review_contract(
        output=args.output,
        contract_dir=args.contract,
        contract_root=args.contract_root,
        execution=args.execution,
        execution_root=args.execution_root,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
