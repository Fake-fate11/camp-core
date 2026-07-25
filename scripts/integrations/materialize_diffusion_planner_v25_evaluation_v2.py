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

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_actual_native_receipt_contract import (  # noqa: E402
    validate_actual_native_receipt,
)
from camp_core.integrations.diffusion_planner_v25_evaluation_v2 import (  # noqa: E402
    CORRECTED_EVALUATION_REVIEW_ROOT,
    CORRECTED_EVALUATION_ROOT,
    CONTINUATION_LEDGER_SHA256,
    EXECUTION_REVIEW_ROOT,
    EXECUTION_ROOT,
    FIXED_DP_HEAD,
    build_evaluation_v2_result,
    canonical_sha256,
    summarize_run_v2,
)


SCHEMA_VERSION = "camp_dp_v25_evaluation_v2_materialization_artifact_v1"


def materialize(
    *,
    output: Path,
    execution: Path,
    execution_root: str,
    execution_review: Path,
    execution_review_root: str,
    corrected_evaluation: Path,
    corrected_evaluation_root: str,
    corrected_evaluation_review: Path,
    corrected_evaluation_review_root: str,
    continuation_ledger: Path,
    continuation_ledger_sha256: str,
    contract: Path,
    contract_root: str,
    contract_review: Path,
    contract_review_root: str,
) -> str:
    expected = (
        ("execution", execution, execution_root, EXECUTION_ROOT),
        (
            "execution review",
            execution_review,
            execution_review_root,
            EXECUTION_REVIEW_ROOT,
        ),
        (
            "corrected evaluation",
            corrected_evaluation,
            corrected_evaluation_root,
            CORRECTED_EVALUATION_ROOT,
        ),
        (
            "corrected evaluation review",
            corrected_evaluation_review,
            corrected_evaluation_review_root,
            CORRECTED_EVALUATION_REVIEW_ROOT,
        ),
    )
    for label, path, actual_root, known_root in expected:
        if actual_root != known_root:
            raise ValueError(f"Evaluation v2 {label} root authority drifted")
        verify_complete_seal(path, actual_root, label=f"Fresh B4 {label}")
    for label, path, root in (
        ("Evaluation v2 contract", contract, contract_root),
        ("Evaluation v2 contract review", contract_review, contract_review_root),
    ):
        verify_complete_seal(path, root, label=label)
    if (
        continuation_ledger_sha256 != CONTINUATION_LEDGER_SHA256
        or _file_sha256(continuation_ledger) != continuation_ledger_sha256
    ):
        raise ValueError("Evaluation v2 continuation ledger SHA drifted")
    contract_report = _object(contract / "report.json")
    contract_review_report = _object(contract_review / "report.json")
    if (
        contract_report.get("status") != "sealed_outcome_free_evaluation_v2_contract"
        or contract_report.get("outcome_values_read") is not False
        or contract_review_report.get("status")
        != "passed_independent_outcome_free_evaluation_v2_contract_review"
        or contract_review_report.get("outcome_values_read") is not False
        or contract_review_report.get("contract_binding", {}).get("root_sha256")
        != contract_root
    ):
        raise ValueError("Evaluation v2 contract chain is not eligible")
    corrected_report = _object(corrected_evaluation / "report.json")
    corrected_review_report = _object(corrected_evaluation_review / "report.json")
    if (
        corrected_report.get("status") != "sealed_holdout_three_arm_evaluation"
        or corrected_review_report.get("status")
        not in {
            "passed_independent_holdout_evaluation_review",
            "passed_independent_corrected_holdout_evaluation_review",
        }
        or corrected_review_report.get("evaluation_root_sha256")
        not in {None, corrected_evaluation_root}
        and corrected_review_report.get("evaluation_binding", {}).get("root_sha256")
        != corrected_evaluation_root
    ):
        raise ValueError("Evaluation v2 corrected evaluation chain drifted")
    rows = _list(execution / "evaluation_rows.json")
    terminals = _list(execution / "run_terminals.json")
    runs = sorted(path for path in (execution / "runs").iterdir() if path.is_dir())
    if len(rows) != 1500 or len(terminals) != 1500 or len(runs) != 1500:
        raise ValueError("Evaluation v2 sealed denominator drifted")
    row_by_key = {(row.get("pair_key"), row.get("arm")): row for row in rows}
    if len(row_by_key) != 1500:
        raise ValueError("Evaluation v2 evaluation-row identity drifted")
    geometry_cache: dict[tuple[str, str], dict[str, Any]] = {}
    summaries = []
    seen: set[tuple[str, str]] = set()
    for run_dir, terminal in zip(runs, terminals, strict=True):
        stored_terminal = _object(run_dir / "terminal.json")
        if stored_terminal != terminal or terminal.get("status") != "complete":
            raise ValueError("Evaluation v2 sealed terminal drifted")
        pair_key = terminal.get("unit_sha256")
        arm = terminal.get("evaluation_arm")
        key = (pair_key, arm)
        if key in seen or key not in row_by_key:
            raise ValueError("Evaluation v2 run/evaluation-row binding drifted")
        seen.add(key)
        config = _object(run_dir / "run_config.json")
        native = _object(run_dir / "native_receipt.json")
        raw_path = run_dir / "actual_native_receipt_raw.json"
        primary = _object(raw_path) if raw_path.is_file() else native
        validate_actual_native_receipt(
            primary,
            branch=(
                "candidate0_primary"
                if arm == "candidate0"
                else "static14d" if arm == "static14d" else "scene14d"
            ),
        )
        projected = dict(native)
        projected.pop("fresh_decision_evidence_reference", None)
        projected.pop("fresh_decision_evidence_count", None)
        if primary != projected:
            raise ValueError("Evaluation v2 sealed raw/projected native drifted")
        if canonical_sha256(native) != terminal.get("native_receipt_sha256"):
            raise ValueError("Evaluation v2 sealed native receipt SHA drifted")
        supplementary = None
        if arm == "candidate0":
            supplementary_path = (
                run_dir / "candidate0_supplementary_actual_native_raw.json"
            )
            if not supplementary_path.is_file():
                raise ValueError(
                    "Evaluation v2 candidate0 supplementary source missing"
                )
            supplementary = _object(supplementary_path)
            validate_actual_native_receipt(
                supplementary, branch="candidate0_supplementary"
            )
        map_sha = config["map"]["sha256"]
        route_sha = config["routes"][0]["sha256"]
        geometry = geometry_cache.get((map_sha, route_sha))
        if geometry is None:
            geometry = _load_root_bound_geometry(config)
            geometry_cache[(map_sha, route_sha)] = geometry
        summaries.append(
            summarize_run_v2(
                native_receipt=primary,
                evaluation_row=row_by_key[key],
                run_config=config,
                geometry=geometry,
                supplementary_receipt=supplementary,
            )
        )
    if len(seen) != 1500:
        raise ValueError("Evaluation v2 run inventory incomplete")
    bindings = {
        "execution": _binding(execution, execution_root),
        "execution_review": _binding(execution_review, execution_review_root),
        "corrected_evaluation": _binding(
            corrected_evaluation, corrected_evaluation_root
        ),
        "corrected_evaluation_review": _binding(
            corrected_evaluation_review, corrected_evaluation_review_root
        ),
        "continuation_ledger": {
            "path": str(continuation_ledger.resolve()),
            "sha256": continuation_ledger_sha256,
            "state": "independently_reviewed_terminal",
        },
        "contract": _binding(contract, contract_root),
        "contract_review": _binding(contract_review, contract_review_root),
        "implementation_head": _git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
    }
    result = build_evaluation_v2_result(
        summaries,
        bindings=bindings,
        contract_root_sha256=contract_root,
        contract_review_root_sha256=contract_review_root,
        legacy_evaluation=_mapping(corrected_report, "evaluation"),
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "sealed_read_only_evaluation_v2_materialization",
        "evaluation_v2": result,
        "implementation_head": _git_head(),
        "geometry_cache_entry_count": len(geometry_cache),
        "execution_read_only": True,
        "execution_files_written": False,
        "corrected_evaluation_read_only": True,
        "corrected_evaluation_files_written": False,
        "fresh_execution_rerun": False,
        "arm_or_dp_k8_rerun": False,
        "corrected_evaluation_rerun": False,
        "scientific_or_continuation_cas_written": False,
        "legacy_values_mutated": False,
        "claim_authorized": False,
    }
    return _write_atomic(output, report)


def _load_root_bound_geometry(config: dict[str, Any]) -> dict[str, Any]:
    fixed = _mapping(config, "fixed_dp")
    if fixed.get("head") != FIXED_DP_HEAD:
        raise ValueError("Evaluation v2 fixed-DP geometry authority drifted")
    dp_repo = Path(str(fixed.get("repo", ""))).resolve()
    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    map_asset = _mapping(config, "map")
    route_assets = config.get("routes")
    if type(route_assets) is not list or len(route_assets) != 1:
        raise ValueError("Evaluation v2 route asset inventory drifted")
    route_asset = route_assets[0]
    map_path = _verified_asset(map_asset, "map")
    route_path = _verified_asset(route_asset, "route")
    from camp_core.integrations.diffusion_planner import (
        install_lanelet2_projection_fallback,
        require_source_preserving_lanelet2_regulatory_adapter,
    )
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route

    require_source_preserving_lanelet2_regulatory_adapter(map_path)
    install_lanelet2_projection_fallback(map_path)
    builder = LaneletSceneBuilder(str(map_path))
    route = Route.load(route_path)
    route_ids = list(route.route_lanelet_ids or ())
    if not route_ids:
        raise ValueError("Evaluation v2 ordered route is unresolved")
    drivable_polygons = []
    for lanelet_id in sorted(builder._cache):
        lane = builder._cache[lanelet_id]
        left = np.asarray(lane.raw_left, dtype=np.float64)[:, :2]
        right = np.asarray(lane.raw_right, dtype=np.float64)[:, :2]
        if left.shape[0] < 2 or right.shape[0] < 2:
            raise ValueError("Evaluation v2 lanelet polygon geometry drifted")
        drivable_polygons.append(np.concatenate([left, right[::-1]], axis=0).tolist())
    centerline_parts = []
    for lanelet_id in route_ids:
        if lanelet_id not in builder._cache:
            raise ValueError("Evaluation v2 route lanelet missing from map")
        points = np.asarray(
            builder._cache[lanelet_id].raw_centerline, dtype=np.float64
        )[:, :2]
        if points.shape[0] < 2:
            raise ValueError("Evaluation v2 route centerline drifted")
        if (
            centerline_parts
            and np.linalg.norm(centerline_parts[-1][-1] - points[0]) <= 1e-6
        ):
            points = points[1:]
        if points.size:
            centerline_parts.append(points)
    centerline = np.concatenate(centerline_parts, axis=0)
    segments = []
    arc = 0.0
    for index, (start, end) in enumerate(zip(centerline[:-1], centerline[1:])):
        length = float(np.linalg.norm(end - start))
        if length <= 1e-9:
            continue
        segment_index = len(segments)
        segments.append(
            {
                "index": segment_index,
                "start_xy": start.tolist(),
                "end_xy": end.tolist(),
                "arc_start_m": arc,
                "arc_end_m": arc + length,
                "next_indices": [segment_index + 1],
            }
        )
        arc += length
    if not segments:
        raise ValueError("Evaluation v2 route segment inventory is empty")
    segments[-1]["next_indices"] = []
    start_pose = np.asarray(route.start_pose, dtype=np.float64)
    goal_pose = np.asarray(route.goal_pose, dtype=np.float64)
    if start_pose.shape != (3,) or goal_pose.shape != (3,):
        raise ValueError("Evaluation v2 route pose geometry drifted")
    return {
        "drivable_polygons": drivable_polygons,
        "route_segments": segments,
        "initial_heading_rad": float(start_pose[2]),
        "goal_pose": goal_pose.tolist(),
        "map_geometry_sha256": map_asset["sha256"],
        "route_geometry_sha256": route_asset["sha256"],
        "route_lanelet_ids": route_ids,
    }


def _verified_asset(value: dict[str, Any], label: str) -> Path:
    path = Path(str(value.get("path", ""))).resolve()
    expected = value.get("sha256")
    if (
        type(expected) is not str
        or len(expected) != 64
        or not path.is_file()
        or _file_sha256(path) != expected
    ):
        raise ValueError(f"Evaluation v2 {label} asset SHA drifted")
    return path


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("Evaluation v2 output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "role": "evaluation_v2_materialization",
                    "implementation_head": report["implementation_head"],
                    "execution_root_sha256": report["evaluation_v2"]["bindings"][
                        "execution"
                    ]["root_sha256"],
                    "corrected_evaluation_root_sha256": report["evaluation_v2"][
                        "bindings"
                    ]["corrected_evaluation"]["root_sha256"],
                    "contract_root_sha256": report["evaluation_v2"][
                        "contract_root_sha256"
                    ],
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="V25 Evaluation v2 materialization")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 Evaluation v2 materialization")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _binding(path: Path, root: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "root_sha256": root}


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


def _list(path: Path) -> list[Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not list:
        raise ValueError(f"{path} must contain a list")
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
    parser.add_argument("--execution-review", type=Path, required=True)
    parser.add_argument("--execution-review-root", required=True)
    parser.add_argument("--corrected-evaluation", type=Path, required=True)
    parser.add_argument("--corrected-evaluation-root", required=True)
    parser.add_argument("--corrected-evaluation-review", type=Path, required=True)
    parser.add_argument("--corrected-evaluation-review-root", required=True)
    parser.add_argument("--continuation-ledger", type=Path, required=True)
    parser.add_argument("--continuation-ledger-sha256", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = materialize(
        output=args.output,
        execution=args.execution,
        execution_root=args.execution_root,
        execution_review=args.execution_review,
        execution_review_root=args.execution_review_root,
        corrected_evaluation=args.corrected_evaluation,
        corrected_evaluation_root=args.corrected_evaluation_root,
        corrected_evaluation_review=args.corrected_evaluation_review,
        corrected_evaluation_review_root=args.corrected_evaluation_review_root,
        continuation_ledger=args.continuation_ledger,
        continuation_ledger_sha256=args.continuation_ledger_sha256,
        contract=args.contract,
        contract_root=args.contract_root,
        contract_review=args.contract_review,
        contract_review_root=args.contract_review_root,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
