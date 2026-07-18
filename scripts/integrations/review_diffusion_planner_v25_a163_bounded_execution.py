#!/usr/bin/env python3
"""Independently review a sealed A1.6.3 bounded K8 execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_a163_bounded_authority import (  # noqa: E402
    EXPECTED_RUNS,
    EXPECTED_TICKS,
    EXPECTED_UNIQUE_IDENTITIES,
    FIXED_DP_HEAD,
    NONCE_LEDGER,
    RELEASE_GATE,
    verify_bounded_release,
)


SCHEMA_VERSION = "camp_dp_v25_a163_bounded_execution_review_v1"
EXECUTION_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_execution_v1"
SNAPSHOT_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_snapshot_v1"
INDEX_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_snapshot_index_row_v1"
RUN_EVIDENCE_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_run_evidence_v1"
RESULT_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_result_v1"
RESULT_FIELDS = {
    "schema_version",
    "run_ordinal",
    "scenario_id",
    "occurrence",
    "status",
    "tick_count",
    "retained_capability_failure",
    "failure_class",
    "fresh_b2_opened",
    "outcome_fields_consumed",
}
EXECUTION_REPORT_FIELDS = {
    "schema_version",
    "status",
    "unique_identity_count",
    "run_count",
    "snapshot_count",
    "snapshot_capacity",
    "terminal",
    "wall_seconds",
    "retained_capability_failure_count",
    "mapped_runtime_source_failure_count",
    "candidate0_semantics",
    "sequential_fixed_k8",
    "candidate_tensors_modified",
    "full_r_execute_authorized",
    "training_executed",
    "calibration_executed",
    "scene_runtime_enabled",
    "v2i_enabled",
    "fresh_b2_opened",
    "outcome_fields_consumed",
}
SOURCE_RECEIPT_FIELDS = {
    "schema_version",
    "release_artifact",
    "release_root_sha256",
    "release_run_nonce",
    "nonce_marker",
    "root_artifacts",
    "formal_root_sha256",
    "critical_implementation_manifest",
    "unique_identity_count",
    "run_count",
    "snapshot_capacity",
    "full_r_execute_authorized",
    "fresh_b2_opened",
    "outcome_fields_consumed",
}
SNAPSHOT_FIELDS = {"schema_version", "feature_payload", "sidecar"}
FEATURE_FIELDS = {
    "atom_matrix",
    "source_valid_mask",
    "atom_source_valid_mask",
    "atom_applicable_mask",
    "physical_feasible_mask",
    "candidate_row_sha256",
    "candidate_tensor",
    "default_output",
    "raw_context",
    "context_source_complete",
}
SIDECAR_FIELDS = {
    "tick_index",
    "dt_s",
    "scenario_id",
    "family",
    "tier",
    "parameter_block_id",
    "route_identity_sha256",
    "corridor_group_sha256",
    "map_family_id",
    "source_map_sha256",
    "seed",
    "candidate_tensor_sha256_before",
    "candidate_tensor_sha256_after",
    "default_output_sha256",
    "candidate0_sha256",
    "default_candidate0_identity",
    "candidate0_semantics",
    "candidate0_independent_second_forward",
    "causal_input_sha256",
    "physical_feasible_mask",
    "source_valid_mask",
    "all_k_high_risk",
    "selected_index",
    "selected_trajectory_sha256",
    "scores",
    "score_contract",
    "tie_break_contract",
    "normalized_atom_matrix_sha256",
    "context_schema_version",
    "context_source_receipt",
    "generation_behavior_scale_sha256",
    "canonical_semantic_clone_sha256",
    "route_signal_source_artifact_root_sha256",
    "route_signal_source_row_sha256",
    "signal_source_class",
    "phase_authority_mode",
    "controlled_signal_source_receipt",
    "controlled_signal_tensor_evidence",
    "controlled_model_input_cache_receipt",
    "causal_signal_atom_input",
    "offline_label_provenance",
    "outcome_fields_consumed",
    "fresh_b_opened",
    "run_ordinal",
    "occurrence",
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _canonical_bytes(value: Any) -> bytes:
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


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _jsonl(path: Path) -> list[Any]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _native_numeric_array(value: Any, shape: tuple[int, ...], *, label: str) -> np.ndarray:
    def walk(node: Any, depth: int) -> list[float]:
        if depth == len(shape):
            if type(node) not in (int, float) or not math.isfinite(float(node)):
                raise ValueError(f"{label} contains a non-native/nonfinite value")
            return [float(node)]
        if type(node) is not list or len(node) != shape[depth]:
            raise ValueError(f"{label} shape drifted")
        flattened: list[float] = []
        for child in node:
            flattened.extend(walk(child, depth + 1))
        return flattened

    return np.asarray(walk(value, 0), dtype=np.float64).reshape(shape)


def _native_number(value: Any, *, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite native number")
    return float(value)


def _context_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    feature = payload["feature_payload"]
    sidecar = payload["sidecar"]
    return {
        "raw_context": feature["raw_context"],
        "context_source_complete": feature["context_source_complete"],
        "context_source_receipt": sidecar["context_source_receipt"],
        "signal_source_class": sidecar["signal_source_class"],
        "phase_authority_mode": sidecar["phase_authority_mode"],
        "controlled_signal_source_receipt": sidecar[
            "controlled_signal_source_receipt"
        ],
        "controlled_signal_tensor_evidence": sidecar[
            "controlled_signal_tensor_evidence"
        ],
        "controlled_model_input_cache_receipt": sidecar[
            "controlled_model_input_cache_receipt"
        ],
        "causal_signal_atom_input": sidecar["causal_signal_atom_input"],
    }


def _review_tick(
    *,
    payload: Mapping[str, Any],
    run: Mapping[str, Any],
    tick_index: int,
    source_row: Mapping[str, Any],
    scales: np.ndarray,
    weights: np.ndarray,
    scale_sha256: str,
) -> dict[str, Any]:
    if (
        type(payload) is not dict
        or set(payload) != SNAPSHOT_FIELDS
        or payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION
    ):
        raise ValueError("bounded snapshot schema drifted")
    feature = payload.get("feature_payload")
    sidecar = payload.get("sidecar")
    if (
        type(feature) is not dict
        or set(feature) != FEATURE_FIELDS
        or type(sidecar) is not dict
        or set(sidecar) != SIDECAR_FIELDS
    ):
        raise ValueError("bounded snapshot feature/sidecar drifted")
    if (
        type(sidecar.get("run_ordinal")) is not int
        or sidecar["run_ordinal"] != run["run_ordinal"]
        or sidecar.get("occurrence") != run["occurrence"]
        or sidecar.get("scenario_id") != run["scenario_id"]
        or type(sidecar.get("tick_index")) is not int
        or sidecar["tick_index"] != tick_index
        or sidecar.get("route_signal_source_row_sha256") != _sha(source_row)
        or sidecar.get("signal_source_class") != source_row["source_class"]
        or sidecar.get("phase_authority_mode")
        != source_row["phase_authority_mode"]
        or sidecar.get("fresh_b_opened") is not False
        or sidecar.get("outcome_fields_consumed") != []
        or sidecar.get("generation_behavior_scale_sha256") != scale_sha256
    ):
        raise ValueError("bounded snapshot run/source/Fresh binding drifted")
    candidate = _native_numeric_array(
        feature.get("candidate_tensor"), (8, 80, 4), label="candidate tensor"
    ).astype(np.float32)
    default = _native_numeric_array(
        feature.get("default_output"), (80, 4), label="default output"
    ).astype(np.float32)
    atoms = _native_numeric_array(feature.get("atom_matrix"), (8, 14), label="atoms")
    if np.any(atoms < 0.0):
        raise ValueError("bounded raw atoms are negative")
    row_shas = [
        hashlib.sha256(np.ascontiguousarray(candidate[index]).tobytes()).hexdigest()
        for index in range(8)
    ]
    tensor_sha = hashlib.sha256(np.ascontiguousarray(candidate).tobytes()).hexdigest()
    raw_rows = feature.get("candidate_row_sha256")
    identity = sidecar.get("default_candidate0_identity")
    if (
        raw_rows != row_shas
        or not np.array_equal(default, candidate[0])
        or sidecar.get("candidate0_sha256") != row_shas[0]
        or sidecar.get("default_output_sha256") != row_shas[0]
        or sidecar.get("candidate_tensor_sha256_before") != tensor_sha
        or sidecar.get("candidate_tensor_sha256_after") != tensor_sha
        or type(identity) is not dict
        or identity.get("elementwise_equal") is not True
        or identity.get("candidate0_sha256") != row_shas[0]
        or identity.get("default_output_sha256") != row_shas[0]
        or sidecar.get("candidate0_independent_second_forward") is not False
    ):
        raise ValueError("bounded K8/candidate0 same-forward evidence drifted")
    atom_source = feature.get("atom_source_valid_mask")
    applicable = feature.get("atom_applicable_mask")
    source_valid = feature.get("source_valid_mask")
    physical = feature.get("physical_feasible_mask")
    if (
        type(atom_source) is not list
        or len(atom_source) != 8
        or any(type(row) is not list or len(row) != 14 for row in atom_source)
        or any(type(value) is not bool for row in atom_source for value in row)
        or type(applicable) is not list
        or len(applicable) != 8
        or any(type(row) is not list or len(row) != 14 for row in applicable)
        or any(type(value) is not bool for row in applicable for value in row)
        or type(source_valid) is not list
        or len(source_valid) != 8
        or any(type(value) is not bool for value in source_valid)
        or source_valid != [all(row) for row in atom_source]
        or type(physical) is not list
        or len(physical) != 8
        or any(type(value) is not bool for value in physical)
        or any(feasible and not valid for feasible, valid in zip(physical, source_valid))
        or sidecar.get("all_k_high_risk")
        is not (all(source_valid) and not any(physical))
    ):
        raise ValueError("bounded source/applicability/physical mask drifted")
    scores = _native_numeric_array(sidecar.get("scores"), (8,), label="scores")
    expected_scores = np.clip(atoms / scales.reshape(1, 14), 0.0, 10.0) @ weights
    selected = sidecar.get("selected_index")
    expected_selected = int(
        np.argmin(np.where(np.asarray(source_valid, dtype=bool), scores, np.inf))
    )
    if (
        type(selected) is not int
        or not np.allclose(scores, expected_scores, rtol=0.0, atol=1e-12)
        or selected != expected_selected
        or sidecar.get("selected_trajectory_sha256") != row_shas[selected]
        or sidecar.get("tie_break_contract") != "lowest_eligible_candidate_index"
    ):
        raise ValueError("bounded selector argmin/tie evidence drifted")
    cache = sidecar.get("controlled_model_input_cache_receipt")
    if (
        type(cache) is not dict
        or cache.get("scenario_id") != run["scenario_id"]
        or cache.get("tick_index") != tick_index
        or cache.get("signal_source_class") != source_row["source_class"]
        or cache.get("phase_authority_mode") != source_row["phase_authority_mode"]
        or cache.get("cache_matches_scene_after") is not True
        or cache.get("sync_applied_before_tensor_conversion") is not True
        or cache.get("model_cache_tl_sha256_after") != cache.get("scene_map_tl_sha256")
        or cache.get("future_schedule_consumed") is not False
        or cache.get("phase_remaining_available") is not False
    ):
        raise ValueError("bounded model-consumed signal cache evidence drifted")
    return {
        "candidate0": row_shas[0],
        "rows": row_shas,
        "atoms": _sha(feature["atom_matrix"]),
        "context": _sha(_context_payload(payload)),
        "selected": selected,
    }


def _review_run(
    *,
    artifact: Path,
    run: Mapping[str, Any],
    index_rows: list[Mapping[str, Any]],
    source_row: Mapping[str, Any],
    scales: np.ndarray,
    weights: np.ndarray,
    scale_sha256: str,
) -> dict[str, Any]:
    ordinal = run["run_ordinal"]
    selected_rows = [row for row in index_rows if row.get("run_ordinal") == ordinal]
    if len(selected_rows) != 64:
        raise ValueError("bounded run snapshot denominator drifted")
    selected_rows.sort(key=lambda row: row.get("tick_index", -1))
    tick_oracles = []
    for tick_index, index_row in enumerate(selected_rows):
        if (
            type(index_row) is not dict
            or set(index_row) != {
                "schema_version",
                "run_ordinal",
                "occurrence",
                "scenario_id",
                "tick_index",
                "relative_path",
                "sha256",
            }
            or index_row.get("schema_version") != INDEX_SCHEMA_VERSION
            or index_row.get("occurrence") != run["occurrence"]
            or index_row.get("scenario_id") != run["scenario_id"]
            or type(index_row.get("tick_index")) is not int
            or index_row["tick_index"] != tick_index
            or type(index_row.get("relative_path")) is not str
            or index_row["relative_path"]
            != f"snapshots/{index_row.get('sha256')}.json"
        ):
            raise ValueError("bounded snapshot index schema/order drifted")
        path = artifact / index_row["relative_path"]
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != index_row["sha256"]:
            raise ValueError("bounded snapshot content-address hash drifted")
        payload = json.loads(data)
        if data != _canonical_bytes(payload):
            raise ValueError("bounded snapshot bytes are not canonical")
        tick_oracles.append(
            _review_tick(
                payload=payload,
                run=run,
                tick_index=tick_index,
                source_row=source_row,
                scales=scales,
                weights=weights,
                scale_sha256=scale_sha256,
            )
        )
    native_dir = (
        artifact
        / "native_runs"
        / f"run_{ordinal:03d}_{run['occurrence']}_{run['scenario_id']}"
    )
    receipt = _load(native_dir / "bounded_native_receipt.json")
    ticks = receipt.get("ticks") if type(receipt) is dict else None
    if type(ticks) is not list or len(ticks) != 64:
        raise ValueError("bounded native receipt tick denominator drifted")
    trajectory = []
    speeds = []
    for tick_index, tick in enumerate(ticks):
        safety = tick.get("safety") if type(tick) is dict else None
        position = safety.get("position_xy") if type(safety) is dict else None
        if type(position) is not list or len(position) != 2:
            raise ValueError("bounded native trajectory evidence drifted")
        trajectory.append(
            {
                "tick_index": tick_index,
                "position_xy": [
                    _native_number(position[0], label="position x"),
                    _native_number(position[1], label="position y"),
                ],
                "ego_heading_rad": _native_number(
                    safety.get("ego_heading_rad"), label="ego heading"
                ),
                "route_progress_m": _native_number(
                    safety.get("route_progress_m"), label="route progress"
                ),
            }
        )
        speeds.append(_native_number(safety.get("speed_mps"), label="speed"))
    return {
        "schema_version": RUN_EVIDENCE_SCHEMA_VERSION,
        "run_ordinal": ordinal,
        "scenario_id": run["scenario_id"],
        "occurrence": run["occurrence"],
        "tick_count": 64,
        "candidate0_sha256_sequence": [row["candidate0"] for row in tick_oracles],
        "k8_row_sha256_sequence": [row["rows"] for row in tick_oracles],
        "atom_matrix_sha256_sequence": [row["atoms"] for row in tick_oracles],
        "context_sha256_sequence": [row["context"] for row in tick_oracles],
        "selected_index_sequence": [row["selected"] for row in tick_oracles],
        "failure_class": "none",
        "closed_loop_trajectory_sha256": _sha(trajectory),
        "speed_probe_sha256": _sha(speeds),
    }


def review(args: argparse.Namespace) -> dict[str, Any]:
    head = _git(ROOT, "rev-parse", "HEAD")
    if _git(ROOT, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("CAMP tracked worktree is dirty")
    if (
        _git(args.dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(args.dp_repo, "status", "--porcelain")
    ):
        raise ValueError("fixed DP drifted or is not fully clean")
    seal = verify_complete_seal(
        args.execution_artifact,
        args.execution_root_sha256,
        label="V25 A1.6.3 bounded execution",
    )
    if (args.execution_artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError("bounded execution run.exit is not zero")
    if any(
        token in path.lower()
        for path in seal["manifest_paths"]
        for token in ("outcome", "fresh", "holdout")
    ):
        raise ValueError("bounded execution inventory contains a forbidden path")
    report = _load(args.execution_artifact / "report.json")
    source_receipt = _load(args.execution_artifact / "source_receipt.json")
    authority = verify_bounded_release(
        repo=ROOT,
        release_artifact=args.release_artifact,
        release_root_sha256=args.release_root_sha256,
        requested_output_dir=args.execution_artifact,
        current_pointer_head=head,
        dp_repo=args.dp_repo,
        probe_template=args.probe_template,
        consume=False,
    )
    decision = authority["decision"]
    plan = authority["plan"]
    marker = NONCE_LEDGER / f"v25_{RELEASE_GATE}_{decision['run_nonce']}.consumed.json"
    marker_payload = _load(marker)
    if (
        marker.is_symlink()
        or set(marker_payload) != {"gate", "nonce", "authorized_output_dir"}
        or marker_payload.get("gate") != RELEASE_GATE
        or marker_payload.get("nonce") != decision["run_nonce"]
        or marker_payload.get("authorized_output_dir")
        != str(args.execution_artifact.resolve())
        or source_receipt.get("nonce_marker", {}).get("path") != str(marker)
        or source_receipt.get("nonce_marker", {}).get("sha256")
        != hashlib.sha256(marker.read_bytes()).hexdigest()
    ):
        raise ValueError("bounded nonce consumption marker drifted")
    if (
        type(report) is not dict
        or set(report) != EXECUTION_REPORT_FIELDS
        or type(source_receipt) is not dict
        or set(source_receipt) != SOURCE_RECEIPT_FIELDS
        or report.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or report.get("status") != "passed_exact_bounded_execution"
        or type(report.get("unique_identity_count")) is not int
        or report["unique_identity_count"] != EXPECTED_UNIQUE_IDENTITIES
        or type(report.get("run_count")) is not int
        or report["run_count"] != EXPECTED_RUNS
        or type(report.get("snapshot_count")) is not int
        or report["snapshot_count"] != EXPECTED_TICKS
        or type(report.get("snapshot_capacity")) is not int
        or report["snapshot_capacity"] != EXPECTED_TICKS
        or report.get("retained_capability_failure_count") != 0
        or report.get("mapped_runtime_source_failure_count") != 0
        or report.get("full_r_execute_authorized") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("outcome_fields_consumed") != []
        or source_receipt.get("release_root_sha256") != authority["release_root_sha256"]
        or source_receipt.get("root_artifacts") != decision["root_artifacts"]
    ):
        raise ValueError("bounded execution report/authority drifted")

    source_artifact = Path(decision["root_artifacts"]["source"]["path"])
    source_payload = _load(source_artifact / "route_signal_source_receipts.json")
    source_rows = source_payload.get("cases")
    if type(source_rows) is not list:
        raise ValueError("bounded source rows are unavailable")
    rows_by_id = {str(row.get("scenario_id")): row for row in source_rows}
    if len(rows_by_id) != len(source_rows):
        raise ValueError("bounded source row IDs are duplicated")
    scale_path = (
        ROOT
        / "configs"
        / "integrations"
        / "diffusion_planner_v25_atom_scales_correction_v2.json"
    )
    scale_payload = _load(scale_path)
    scale_sha256 = hashlib.sha256(scale_path.read_bytes()).hexdigest()
    atom_names = scale_payload.get("atom_names")
    scales = _native_numeric_array(
        scale_payload.get("scales"), (14,), label="generation scales"
    )
    template = _load(args.probe_template)
    weights_by_name = template.get("selector", {}).get("weights")
    if (
        type(atom_names) is not list
        or len(atom_names) != 14
        or type(weights_by_name) is not dict
        or set(weights_by_name) != set(atom_names)
        or np.any(scales <= 0.0)
    ):
        raise ValueError("bounded scale/weight authority drifted")
    weights = _native_numeric_array(
        [weights_by_name[name] for name in atom_names],
        (14,),
        label="static weights",
    )
    if np.any(weights < 0.0) or not np.isclose(
        float(weights.sum()), 1.0, rtol=0.0, atol=1e-12
    ):
        raise ValueError("bounded static weights are not a nonnegative simplex")
    results = _jsonl(args.execution_artifact / "results.jsonl")
    evidence = _jsonl(args.execution_artifact / "run_evidence.jsonl")
    index_rows = _jsonl(args.execution_artifact / "snapshot_index.jsonl")
    if (
        len(results) != EXPECTED_RUNS
        or len(evidence) != EXPECTED_RUNS
        or len(index_rows) != EXPECTED_TICKS
    ):
        raise ValueError("bounded results/evidence/index denominator drifted")
    rebuilt = []
    for run, result in zip(plan["runs"], results):
        if (
            type(result) is not dict
            or set(result) != RESULT_FIELDS
            or result.get("schema_version") != RESULT_SCHEMA_VERSION
            or result.get("run_ordinal") != run["run_ordinal"]
            or result.get("scenario_id") != run["scenario_id"]
            or result.get("occurrence") != run["occurrence"]
            or result.get("status") != "complete"
            or type(result.get("tick_count")) is not int
            or result["tick_count"] != 64
            or result.get("retained_capability_failure") is not None
            or result.get("failure_class") != "none"
            or result.get("fresh_b2_opened") is not False
            or result.get("outcome_fields_consumed") != []
        ):
            raise ValueError("bounded result/order/failure contract drifted")
        rebuilt.append(
            _review_run(
                artifact=args.execution_artifact,
                run=run,
                index_rows=index_rows,
                source_row=rows_by_id[str(run["scenario_id"])],
                scales=scales,
                weights=weights,
                scale_sha256=scale_sha256,
            )
        )
    if _canonical_bytes(rebuilt) != _canonical_bytes(evidence):
        raise ValueError("bounded producer run evidence differs from independent rebuild")
    first, final = rebuilt[0], rebuilt[-1]
    repeat_fields = (
        "candidate0_sha256_sequence",
        "k8_row_sha256_sequence",
        "atom_matrix_sha256_sequence",
        "context_sha256_sequence",
        "selected_index_sequence",
        "failure_class",
        "closed_loop_trajectory_sha256",
        "speed_probe_sha256",
    )
    comparison = {f"{field}_equal": first[field] == final[field] for field in repeat_fields}
    if any(value is not True for value in comparison.values()):
        raise ValueError("bounded identity0 repeat independent comparison failed")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_bounded_execution_review",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(args.execution_artifact.resolve()),
        "reviewed_root_sha256": seal["root_sha256"],
        "release_root_sha256": authority["release_root_sha256"],
        "root_artifacts": decision["root_artifacts"],
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_count": EXPECTED_TICKS,
        "identity0_repeat_comparison": comparison,
        "retained_capability_failure_count": 0,
        "mapped_runtime_source_failure_count": 0,
        "full_r_execute_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-artifact", type=Path, required=True)
    parser.add_argument("--execution-root-sha256", required=True)
    parser.add_argument("--release-artifact", type=Path, required=True)
    parser.add_argument("--release-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args)
        _write(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"review_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(args.output_dir, label="V25 A1.6.3 bounded review")
        print(json.dumps({**report, "artifact_root_sha256": root}, sort_keys=True))
    except Exception as exc:
        _write(
            args.output_dir / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed_independent_bounded_execution_review",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "full_r_execute_authorized": False,
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (args.output_dir / "run.exit").write_bytes(b"1\n")
        seal_artifact(args.output_dir, label="failed V25 A1.6.3 bounded review")
        raise


if __name__ == "__main__":
    main()
