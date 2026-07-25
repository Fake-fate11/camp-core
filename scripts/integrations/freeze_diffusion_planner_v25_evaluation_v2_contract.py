from __future__ import annotations

import argparse
import hashlib
import json
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
from camp_core.integrations.diffusion_planner_v25_evaluation_v2 import (  # noqa: E402
    EXECUTION_ROOT,
    evaluation_v2_contract,
    validate_evaluation_v2_contract,
)


SCHEMA_VERSION = "camp_dp_v25_evaluation_v2_contract_artifact_v2"


def freeze_contract(*, output: Path, execution: Path, execution_root: str) -> str:
    if execution_root != EXECUTION_ROOT:
        raise ValueError("Evaluation v2 execution root authority drifted")
    verify_complete_seal(execution, execution_root, label="Fresh B4 execution")
    contract = evaluation_v2_contract()
    validate_evaluation_v2_contract(contract)
    source_audit = _outcome_free_source_audit(execution)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "sealed_outcome_free_evaluation_v2_corrected_contract",
        "contract": contract,
        "source_capability_audit": source_audit,
        "superseded_v2_static_correction_diagnosis": {
            "basis": (
                "static evaluator source plus the published aggregate-only v1 "
                "summary; no per-run outcome values"
            ),
            "old_route_missing_arm_count": 1500,
            "old_route_reported_reason": (
                "no_unique_kinematically_feasible_route_path"
            ),
            "first_evaluator_branch_category": (
                "next route-state inventory became empty under forward-only "
                "adjacency and speed-only travel bound"
            ),
            "corrections_selected_without_outcome_values": [
                "forward_or_backward_frozen_adjacency",
                "max_trapezoidal_speed_or_sealed_displacement_bound",
                "forward_increment_completion",
                "goal_endpoint_independent_of_route_projection",
            ],
        },
        "execution_binding": {
            "path": str(execution.resolve()),
            "root_sha256": execution_root,
        },
        "implementation_head": _git_head(),
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


def _outcome_free_source_audit(execution: Path) -> dict[str, Any]:
    runs = sorted(path for path in (execution / "runs").iterdir() if path.is_dir())
    if len(runs) != 1500:
        raise ValueError("Evaluation v2 source audit run denominator drifted")
    maps: dict[str, str] = {}
    routes: dict[str, str] = {}
    config_count = 0
    supplementary_count = 0
    controlled = 0
    naturalistic = 0
    spawn_fields: set[str] = set()
    actor_fields: set[str] = set()
    for run in runs:
        config_path = run / "run_config.json"
        if not config_path.is_file():
            raise ValueError("Evaluation v2 sealed run_config is missing")
        config = _object(config_path)
        config_count += 1
        spawn = _mapping(config, "spawn_config")
        spawn_fields.update(spawn)
        for name in (
            "ego_length",
            "ego_width",
            "ego_wheelbase",
            "goal_tolerance_m",
            "goal_pass_window_m",
        ):
            if name not in spawn:
                raise ValueError(f"Evaluation v2 spawn capability missing: {name}")
        runtime = _mapping(config, "signal_complete_runtime")
        case = _mapping(runtime, "case")
        actors = case.get("actors")
        if type(actors) is not list:
            raise ValueError("Evaluation v2 actor inventory drifted")
        if actors:
            controlled += 1
        else:
            naturalistic += 1
        for actor in actors:
            if type(actor) is not dict:
                raise ValueError("Evaluation v2 actor spec drifted")
            actor_fields.update(actor)
            for name in ("id", "length_m", "width_m"):
                if name not in actor:
                    raise ValueError(
                        f"Evaluation v2 actor geometry capability missing: {name}"
                    )
        map_asset = _mapping(config, "map")
        _asset(map_asset, maps, "map")
        route_assets = config.get("routes")
        if type(route_assets) is not list or len(route_assets) != 1:
            raise ValueError("Evaluation v2 route asset inventory drifted")
        _asset(route_assets[0], routes, "route")
        if (run / "candidate0_supplementary_actual_native_raw.json").is_file():
            supplementary_count += 1
    if (
        config_count != 1500
        or supplementary_count != 500
        or controlled != 960
        or naturalistic != 540
        or len(maps) != 25
    ):
        raise ValueError("Evaluation v2 source capability denominator drifted")
    return {
        "audit_mode": "metadata_and_asset_hashes_only_no_outcome_values",
        "run_config_count": config_count,
        "candidate0_supplementary_raw_file_existence_count": supplementary_count,
        "controlled_arm_config_count": controlled,
        "naturalistic_arm_config_count": naturalistic,
        "unique_map_count": len(maps),
        "unique_route_count": len(routes),
        "all_map_assets_present_and_sha_bound": True,
        "all_route_assets_present_and_sha_bound": True,
        "spawn_fields": sorted(spawn_fields),
        "actor_fields": sorted(actor_fields),
        "full_polygon_capability": "conditionally_available_after_per_run_root_binding",
        "ordered_route_capability": "conditionally_available_after_per_run_root_binding",
        "candidate0_dynamic_pair_capability": (
            "conditional_on_materialization_time_exact_primary_supplementary_equivalence"
        ),
        "outcome_values_read": False,
    }


def _asset(value: Any, inventory: dict[str, str], label: str) -> None:
    if type(value) is not dict:
        raise ValueError(f"Evaluation v2 {label} asset drifted")
    path = Path(str(value.get("path", ""))).resolve()
    expected = value.get("sha256")
    if (
        type(expected) is not str
        or len(expected) != 64
        or not path.is_file()
        or _file_sha256(path) != expected
    ):
        raise ValueError(f"Evaluation v2 {label} asset SHA drifted")
    known = inventory.setdefault(expected, str(path))
    if known != str(path):
        raise ValueError(f"Evaluation v2 {label} SHA/path ambiguity")


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("Evaluation v2 contract output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "role": "evaluation_v2_corrected_contract",
                    "implementation_head": report["implementation_head"],
                    "execution_root_sha256": report["execution_binding"]["root_sha256"],
                    "fixed_dp_head": report["contract"]["bindings"]["fixed_dp_head"],
                }
            )
        )
        root = seal_artifact(staging, label="V25 Evaluation v2 corrected contract")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 Evaluation v2 corrected contract"
        )
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


def _mapping(value: dict[str, Any], name: str) -> dict[str, Any]:
    result = value.get(name)
    if type(result) is not dict:
        raise ValueError(f"{name} must be an object")
    return result


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--execution-root", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = freeze_contract(
        output=args.output,
        execution=args.execution,
        execution_root=args.execution_root,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
