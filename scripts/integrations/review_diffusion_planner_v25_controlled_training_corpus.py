#!/usr/bin/env python3
"""Independently validate a sealed V25 corrected 1500-identity corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORPUS_STEPS,
    EXPECTED_EXECUTABLE_IDENTITIES,
    SCHEMA_VERSION as EXECUTION_SCHEMA_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_controlled_training_corpus_review_v1"
SNAPSHOT_INDEX_FIELDS = frozenset(
    {"scenario_id", "tick_index", "relative_path", "sha256"}
)
SNAPSHOT_FIELDS = frozenset({"schema_version", "feature_payload", "sidecar"})
FEATURE_PAYLOAD_FIELDS = frozenset(
    {
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
)
SIDECAR_FIELDS = frozenset(
    {
        "tick_index",
        "dt_s",
        "scenario_id",
        "family",
        "tier",
        "parameter_block_id",
        "route_identity_sha256",
        "corridor_group_sha256",
        "map_family_id",
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
        "score_contract",
        "tie_break_contract",
        "normalized_atom_matrix_sha256",
        "context_schema_version",
        "context_source_receipt",
        "generation_behavior_scale_sha256",
        "canonical_semantic_clone_sha256",
        "controlled_signal_source_receipt",
        "causal_signal_atom_input",
        "offline_label_provenance",
        "outcome_fields_consumed",
        "fresh_b_opened",
    }
)
DEFAULT_CANDIDATE0_IDENTITY_FIELDS = frozenset(
    {
        "elementwise_equal",
        "default_output_sha256",
        "candidate0_sha256",
        "native_ranked_k8",
    }
)
_SHA_CHARS = frozenset("0123456789abcdef")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSONL objects: {path}")
        rows.append(value)
    return rows


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _oracle_canonical_snapshot_bytes(payload: Any) -> bytes:
    """Locally implement the frozen V25 snapshot byte contract."""
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _is_sha256(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and not set(value) - _SHA_CHARS


def _native_bool_list(value: Any, length: int, label: str) -> None:
    if type(value) is not list or len(value) != length or any(
        type(item) is not bool for item in value
    ):
        raise ValueError(f"{label} must be a native boolean list[{length}]")


def _reject_forbidden_nested_fields(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if type(key) is not str:
                raise ValueError("snapshot contains a non-string JSON key")
            lowered = key.lower()
            forbidden = (
                "future" in lowered
                or "holdout" in lowered
                or "id_proxy" in lowered
                or "identity_proxy" in lowered
                or ("outcome" in lowered and key != "outcome_fields_consumed")
                or ("label" in lowered and key != "offline_label_provenance")
            )
            if forbidden:
                raise ValueError(
                    "snapshot contains forbidden field: " + ".".join((*path, key))
                )
            _reject_forbidden_nested_fields(child, (*path, key))
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_nested_fields(child, path)


def _validate_snapshot_index_row(row: Any) -> None:
    if type(row) is not dict or set(row) != SNAPSHOT_INDEX_FIELDS:
        raise ValueError("snapshot index row exact field set drifted")
    if not _is_sha256(row.get("scenario_id")):
        raise ValueError("snapshot index scenario_id must be a SHA256 string")
    if type(row.get("tick_index")) is not int:
        raise ValueError("snapshot index tick_index must be a native integer")
    relative = row.get("relative_path")
    if type(relative) is not str:
        raise ValueError("snapshot index relative_path must be a native string")
    if not _is_sha256(row.get("sha256")):
        raise ValueError("snapshot index sha256 must be a SHA256 string")


def _validate_snapshot_field_schema(snapshot: Any) -> None:
    if type(snapshot) is not dict or set(snapshot) != SNAPSHOT_FIELDS:
        raise ValueError("snapshot top-level exact field set drifted")
    features = snapshot.get("feature_payload")
    sidecar = snapshot.get("sidecar")
    if type(features) is not dict or set(features) != FEATURE_PAYLOAD_FIELDS:
        raise ValueError("snapshot feature_payload exact field set drifted")
    if type(sidecar) is not dict or set(sidecar) != SIDECAR_FIELDS:
        raise ValueError("snapshot sidecar exact field set drifted")
    if type(snapshot.get("schema_version")) is not str:
        raise ValueError("snapshot schema_version must be a native string")

    _native_bool_list(features.get("source_valid_mask"), 8, "source_valid_mask")
    _native_bool_list(
        features.get("physical_feasible_mask"), 8, "physical_feasible_mask"
    )
    for field in ("atom_source_valid_mask", "atom_applicable_mask"):
        matrix = features.get(field)
        if type(matrix) is not list or any(
            type(row) is not list or any(type(item) is not bool for item in row)
            for row in matrix
        ):
            raise ValueError(f"{field} must contain only native booleans")
    rows = features.get("candidate_row_sha256")
    if type(rows) is not list or len(rows) != 8 or any(
        not _is_sha256(value) for value in rows
    ):
        raise ValueError("candidate_row_sha256 must be eight SHA256 strings")
    for field in ("atom_matrix", "candidate_tensor", "default_output"):
        if type(features.get(field)) is not list:
            raise ValueError(f"{field} must be a JSON list")
    raw_context = features.get("raw_context")
    source_complete = features.get("context_source_complete")
    if type(raw_context) is not dict or any(
        type(value) not in (int, float) or not np.isfinite(float(value))
        for value in raw_context.values()
    ):
        raise ValueError("raw_context must contain finite native numbers")
    if type(source_complete) is not dict or any(
        type(value) is not bool for value in source_complete.values()
    ):
        raise ValueError("context_source_complete must contain native booleans")

    if type(sidecar.get("tick_index")) is not int:
        raise ValueError("sidecar tick_index must be a native integer")
    if type(sidecar.get("dt_s")) is not float or not np.isfinite(sidecar["dt_s"]):
        raise ValueError("sidecar dt_s must be a finite native float")
    if type(sidecar.get("seed")) is not int:
        raise ValueError("sidecar seed must be a native integer")
    for field in (
        "scenario_id",
        "family",
        "tier",
        "parameter_block_id",
        "route_identity_sha256",
        "corridor_group_sha256",
        "map_family_id",
        "candidate0_semantics",
        "score_contract",
        "tie_break_contract",
        "context_schema_version",
        "offline_label_provenance",
    ):
        if type(sidecar.get(field)) is not str:
            raise ValueError(f"sidecar {field} must be a native string")
    for field in (
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "default_output_sha256",
        "candidate0_sha256",
        "causal_input_sha256",
        "selected_trajectory_sha256",
        "normalized_atom_matrix_sha256",
        "generation_behavior_scale_sha256",
    ):
        if not _is_sha256(sidecar.get(field)):
            raise ValueError(f"sidecar {field} must be a SHA256 string")
    semantic = sidecar.get("canonical_semantic_clone_sha256")
    if semantic is not None and not _is_sha256(semantic):
        raise ValueError("canonical semantic clone must be null or SHA256")
    for field in (
        "candidate0_independent_second_forward",
        "all_k_high_risk",
        "fresh_b_opened",
    ):
        if type(sidecar.get(field)) is not bool:
            raise ValueError(f"sidecar {field} must be a native boolean")
    if type(sidecar.get("selected_index")) is not int:
        raise ValueError("sidecar selected_index must be a native integer")
    _native_bool_list(
        sidecar.get("physical_feasible_mask"), 8, "sidecar physical_feasible_mask"
    )
    _native_bool_list(
        sidecar.get("source_valid_mask"), 8, "sidecar source_valid_mask"
    )
    identity = sidecar.get("default_candidate0_identity")
    if type(identity) is not dict or set(identity) != DEFAULT_CANDIDATE0_IDENTITY_FIELDS:
        raise ValueError("default_candidate0_identity exact field set drifted")
    if (
        type(identity.get("elementwise_equal")) is not bool
        or type(identity.get("native_ranked_k8")) is not bool
        or not _is_sha256(identity.get("default_output_sha256"))
        or not _is_sha256(identity.get("candidate0_sha256"))
    ):
        raise ValueError("default_candidate0_identity type contract drifted")
    if type(sidecar.get("context_source_receipt")) is not dict:
        raise ValueError("context_source_receipt must be an object")
    for field in ("controlled_signal_source_receipt", "causal_signal_atom_input"):
        value = sidecar.get(field)
        if value is not None and type(value) is not dict:
            raise ValueError(f"sidecar {field} must be null or an object")
    if type(sidecar.get("outcome_fields_consumed")) is not list:
        raise ValueError("outcome_fields_consumed must be a list")
    _reject_forbidden_nested_fields(snapshot)


def _read_verified_content_addressed_snapshot(
    path: Path, expected_sha256: Any
) -> dict[str, Any]:
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(
            character not in "0123456789abcdef" for character in expected_sha256
        )
    ):
        raise ValueError("snapshot index SHA256 is invalid")
    data = path.read_bytes()
    if not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise ValueError("snapshot bytes do not end in exactly one LF")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("snapshot bytes are not canonical UTF-8 JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("snapshot payload is not an object")
    canonical = _oracle_canonical_snapshot_bytes(payload)
    digest = hashlib.sha256(canonical).hexdigest()
    if (
        data != canonical
        or digest != expected_sha256
        or path.name != f"{expected_sha256}.json"
    ):
        raise ValueError("snapshot canonical bytes/content address drifted")
    return payload


def review(corpus: Path, expected_root: str) -> dict[str, Any]:
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    seal = verify_complete_seal(corpus, expected_root, label="V25 corrected corpus")
    report = _json(corpus / "report.json")
    progress = _json(corpus / "progress.json")
    results = _jsonl(corpus / "results.jsonl")
    index = _jsonl(corpus / "snapshot_index.jsonl")
    if (
        (corpus / "run.exit").read_text(encoding="ascii") != "0\n"
        or report.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or report.get("status") != "passed"
        or report.get("mode") != "execute"
        or report.get("camp_head") != head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("attempted_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("retained_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or len(results) != EXPECTED_EXECUTABLE_IDENTITIES
        or progress.get("status") != "complete"
        or progress.get("completed") != EXPECTED_EXECUTABLE_IDENTITIES
        or progress.get("total") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("fresh_b_opened") is not False
        or report.get("training_snapshot_outcome_fields") != []
        or report.get("selector_training_executed") is not False
        or report.get("calibration_executed") is not False
    ):
        raise ValueError("corrected corpus terminal report contract drifted")
    seen_results: set[str] = set()
    expected_snapshots = 0
    for ordinal, row in enumerate(results):
        scenario_id = row.get("scenario_id")
        status = row.get("status")
        count = row.get("snapshot_count")
        if (
            row.get("ordinal") != ordinal
            or not isinstance(scenario_id, str)
            or len(scenario_id) != 64
            or scenario_id in seen_results
            or row.get("retained") is not True
            or row.get("fresh_b_opened") is not False
            or row.get("outcome_fields_consumed") != []
        ):
            raise ValueError("corpus result denominator drifted")
        if status == "complete":
            if count != CORPUS_STEPS or row.get("capability_failure") is not None:
                raise ValueError("complete corpus identity is not exactly 64 ticks")
            expected_snapshots += CORPUS_STEPS
        elif status == "failed":
            failure = row.get("capability_failure")
            if (
                count != 0
                or row.get("failure_type") != "RetainedScenarioCapabilityFailure"
                or not isinstance(failure, Mapping)
                or failure.get("scenario_id") != scenario_id
                or failure.get("family") != row.get("family")
            ):
                raise ValueError("failed corpus identity is not a typed retained failure")
        else:
            raise ValueError("corpus identity has an illegal terminal status")
        seen_results.add(scenario_id)
    if (
        len(index) != expected_snapshots
        or report.get("snapshot_count") != expected_snapshots
        or progress.get("snapshot_count") != expected_snapshots
    ):
        raise ValueError("corpus snapshot denominator is inconsistent")
    seen_ticks: set[tuple[str, int]] = set()
    for row in index:
        _validate_snapshot_index_row(row)
        key = (row["scenario_id"], row["tick_index"])
        relative = row.get("relative_path")
        if (
            key in seen_ticks
            or key[0] not in seen_results
            or isinstance(key[1], bool)
            or not isinstance(key[1], int)
            or not 0 <= key[1] < CORPUS_STEPS
            or not isinstance(relative, str)
            or not relative.startswith("snapshots/")
            or ".." in Path(relative).parts
        ):
            raise ValueError("snapshot index authority is invalid")
        path = corpus / relative
        digest = row.get("sha256")
        snapshot = _read_verified_content_addressed_snapshot(path, digest)
        _validate_snapshot_field_schema(snapshot)
        features = snapshot["feature_payload"]
        sidecar = snapshot["sidecar"]
        source = np.asarray(features.get("atom_source_valid_mask"))
        applicable = np.asarray(features.get("atom_applicable_mask"))
        physical = features.get("physical_feasible_mask")
        atoms = np.asarray(features.get("atom_matrix"), dtype=np.float64)
        candidates = np.asarray(features.get("candidate_tensor"), dtype=np.float32)
        default = np.asarray(features.get("default_output"), dtype=np.float32)
        candidate_rows = (
            [
                hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
                for value in candidates
            ]
            if candidates.ndim == 3 and candidates.shape[0] == 8
            else []
        )
        tensor_sha = (
            hashlib.sha256(np.ascontiguousarray(candidates).tobytes()).hexdigest()
            if candidate_rows
            else None
        )
        default_sha = (
            hashlib.sha256(np.ascontiguousarray(default).tobytes()).hexdigest()
            if default.shape == (80, 4)
            else None
        )
        selected = sidecar.get("selected_index")
        if (
            snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION
            or sidecar.get("scenario_id") != key[0]
            or sidecar.get("tick_index") != key[1]
            or source.dtype != np.bool_
            or applicable.dtype != np.bool_
            or source.shape != (8, 14)
            or applicable.shape != (8, 14)
            or np.any(applicable & ~source)
            or atoms.shape != (8, 14)
            or not np.isfinite(atoms).all()
            or np.any(atoms < 0.0)
            or candidates.shape != (8, 80, 4)
            or default.shape != (80, 4)
            or features.get("candidate_row_sha256") != candidate_rows
            or sidecar.get("candidate_tensor_sha256_before") != tensor_sha
            or sidecar.get("candidate_tensor_sha256_after") != tensor_sha
            or sidecar.get("default_output_sha256") != default_sha
            or sidecar.get("candidate0_sha256") != candidate_rows[0]
            or not np.array_equal(default, candidates[0])
            or isinstance(selected, bool)
            or not isinstance(selected, int)
            or not 0 <= selected < 8
            or sidecar.get("selected_trajectory_sha256")
            != candidate_rows[selected]
            or not isinstance(physical, list)
            or len(physical) != 8
            or any(not isinstance(value, bool) for value in physical)
            or sidecar.get("fresh_b_opened") is not False
            or sidecar.get("outcome_fields_consumed") != []
        ):
            raise ValueError("snapshot schema/source/hash contract drifted")
        seen_ticks.add(key)
    for row in results:
        if row["status"] == "complete":
            keys = {key[1] for key in seen_ticks if key[0] == row["scenario_id"]}
            if keys != set(range(CORPUS_STEPS)):
                raise ValueError("complete identity has missing or duplicate tick index")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_full_corpus_review",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(corpus),
        "reviewed_root_sha256": seal["root_sha256"],
        "identity_denominator": len(results),
        "complete_identity_count": sum(row["status"] == "complete" for row in results),
        "typed_retained_failure_count": sum(row["status"] == "failed" for row in results),
        "snapshot_count": expected_snapshots,
        "partial_snapshot_count": 0,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-artifact", type=Path, required=True)
    parser.add_argument("--corpus-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args.corpus_artifact, args.corpus_root_sha256)
        _write(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 corrected corpus review")
        print(json.dumps({"status": report["status"], "root_sha256": root}))
    except BaseException as exc:
        _write(
            args.output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 failed corrected corpus review")
        raise


if __name__ == "__main__":
    main()
