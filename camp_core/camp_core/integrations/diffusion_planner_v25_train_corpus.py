from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np

from camp_core.integrations.diffusion_planner_artifact_seal import (
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_context import (
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_snapshot_review import (
    independently_read_snapshot,
)
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (
    ATOM_COUNT,
    CANDIDATE_COUNT,
    hierarchical_snapshot_weights,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_FULL_CORPUS_IDENTITIES = 1500
MINIMUM_COMPLETE_IDENTITIES = 1425
CORPUS_STEPS = 64


@dataclass(frozen=True)
class V25TrainCorpus:
    raw_atoms: np.ndarray
    source_valid_mask: np.ndarray
    atom_source_valid_mask: np.ndarray
    atom_applicable_mask: np.ndarray
    physical_feasible_mask: np.ndarray
    raw_context: np.ndarray
    context_source_complete: np.ndarray
    route_ids: tuple[str, ...]
    semantic_block_ids: tuple[str, ...]
    corridor_ids: tuple[str, ...]
    map_family_ids: tuple[str, ...]
    family_tier: tuple[str, ...]
    seeds: tuple[int, ...]
    ticks: tuple[int, ...]
    scenario_ids: tuple[str, ...]
    snapshot_weights: np.ndarray
    generation_behavior_scale_sha256: str
    report: dict[str, Any]


def load_reviewed_train_corpus(
    corpus_artifact: Path,
    corpus_root_sha256: str,
    review_artifact: Path,
    review_root_sha256: str,
) -> V25TrainCorpus:
    """Load only complete, independently reviewed, outcome-free train rows."""

    corpus = Path(corpus_artifact).resolve()
    review = Path(review_artifact).resolve()
    verify_complete_seal(corpus, corpus_root_sha256, label="V25 train corpus")
    verify_complete_seal(review, review_root_sha256, label="V25 train corpus review")
    corpus_report = _json_object(corpus / "report.json")
    review_report = _json_object(review / "report.json")
    authority = validate_reviewed_train_corpus_reports(
        corpus_report,
        review_report,
        corpus_artifact=corpus,
        corpus_root_sha256=corpus_root_sha256,
    )

    accumulators: dict[str, list[Any]] = {
        "raw_atoms": [],
        "source_valid_mask": [],
        "atom_source_valid_mask": [],
        "atom_applicable_mask": [],
        "physical_feasible_mask": [],
        "raw_context": [],
        "context_source_complete": [],
        "route_ids": [],
        "semantic_block_ids": [],
        "corridor_ids": [],
        "map_family_ids": [],
        "family_tier": [],
        "seeds": [],
        "ticks": [],
        "scenario_ids": [],
        "scale_sha": [],
    }
    seen: set[tuple[str, int]] = set()
    index_path = corpus / "snapshot_index.jsonl"
    with index_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            index_row = _json_line(line, index_path, line_number)
            scenario_id = _sha(index_row.get("scenario_id"), "scenario_id")
            tick = _native_int(index_row.get("tick_index"), "tick_index")
            relative = index_row.get("relative_path")
            digest = _sha(index_row.get("sha256"), "snapshot sha256")
            if (
                type(relative) is not str
                or Path(relative).is_absolute()
                or ".." in Path(relative).parts
                or relative != f"snapshots/{digest}.json.xz"
                or (scenario_id, tick) in seen
            ):
                raise ValueError("snapshot index path/key authority is invalid")
            snapshot = independently_read_snapshot(corpus / relative, digest)
            row = extract_training_row(snapshot, index_row)
            for key in accumulators:
                accumulators[key].append(row[key])
            seen.add((scenario_id, tick))

    count = len(accumulators["raw_atoms"])
    if count != review_report["snapshot_count"]:
        raise ValueError("loaded snapshot count differs from independent review")
    scale_shas = set(accumulators.pop("scale_sha"))
    if len(scale_shas) != 1:
        raise ValueError("generation behavior scale SHA drifted within train corpus")
    route_ids = tuple(accumulators["route_ids"])
    block_ids = tuple(accumulators["semantic_block_ids"])
    seeds = tuple(accumulators["seeds"])
    ticks = tuple(accumulators["ticks"])
    weights = hierarchical_snapshot_weights(route_ids, block_ids, seeds, ticks)
    leaf_count = len(set(zip(route_ids, block_ids, seeds, ticks)))
    report = {
        "schema_version": "camp_dp_v25_reviewed_train_corpus_projection_v1",
        "corpus_artifact": str(corpus),
        "corpus_root_sha256": corpus_root_sha256,
        "review_artifact": str(review),
        "review_root_sha256": review_root_sha256,
        "snapshot_count": count,
        "fixed_dp_head": FIXED_DP_HEAD,
        "identity_denominator": authority["identity_denominator"],
        "complete_identity_count": authority["complete_identity_count"],
        "typed_retained_failure_count": authority["typed_retained_failure_count"],
        "fixed_dp_support_coverage": authority["fixed_dp_support_coverage"],
        "unique_weight_leaf_count": leaf_count,
        "duplicate_weight_leaf_row_count": count - leaf_count,
        "unique_route_count": len(set(route_ids)),
        "unique_semantic_block_count": len(set(block_ids)),
        "unique_corridor_count": len(set(accumulators["corridor_ids"])),
        "unique_map_family_count": len(set(accumulators["map_family_ids"])),
        "identity_fields_used_as_model_features": False,
        "fresh_or_outcome_consumed": False,
    }
    return V25TrainCorpus(
        raw_atoms=np.asarray(accumulators["raw_atoms"], dtype=np.float64),
        source_valid_mask=np.asarray(accumulators["source_valid_mask"], dtype=np.bool_),
        atom_source_valid_mask=np.asarray(
            accumulators["atom_source_valid_mask"], dtype=np.bool_
        ),
        atom_applicable_mask=np.asarray(
            accumulators["atom_applicable_mask"], dtype=np.bool_
        ),
        physical_feasible_mask=np.asarray(
            accumulators["physical_feasible_mask"], dtype=np.bool_
        ),
        raw_context=np.asarray(accumulators["raw_context"], dtype=np.float64),
        context_source_complete=np.asarray(
            accumulators["context_source_complete"], dtype=np.bool_
        ),
        route_ids=route_ids,
        semantic_block_ids=block_ids,
        corridor_ids=tuple(accumulators["corridor_ids"]),
        map_family_ids=tuple(accumulators["map_family_ids"]),
        family_tier=tuple(accumulators["family_tier"]),
        seeds=seeds,
        ticks=ticks,
        scenario_ids=tuple(accumulators["scenario_ids"]),
        snapshot_weights=weights,
        generation_behavior_scale_sha256=next(iter(scale_shas)),
        report=report,
    )


def validate_reviewed_train_corpus_reports(
    corpus_report: dict[str, Any],
    review_report: dict[str, Any],
    *,
    corpus_artifact: Path,
    corpus_root_sha256: str,
) -> dict[str, Any]:
    """Bind training admission to the reviewed full-corpus support domain."""

    corpus = Path(corpus_artifact).resolve()
    if type(corpus_report) is not dict or type(review_report) is not dict:
        raise ValueError("reviewed corpus reports must be native mappings")
    complete = review_report.get("complete_identity_count")
    retained = review_report.get("typed_retained_failure_count")
    snapshots = review_report.get("snapshot_count")
    if (
        review_report.get("status") != "passed_independent_full_corpus_review"
        or review_report.get("fixed_dp_head") != FIXED_DP_HEAD
        or Path(str(review_report.get("reviewed_artifact"))).resolve() != corpus
        or review_report.get("reviewed_root_sha256") != corpus_root_sha256
        or review_report.get("identity_denominator") != EXPECTED_FULL_CORPUS_IDENTITIES
        or type(complete) is not int
        or type(retained) is not int
        or complete < MINIMUM_COMPLETE_IDENTITIES
        or complete + retained != EXPECTED_FULL_CORPUS_IDENTITIES
        or type(snapshots) is not int
        or snapshots != complete * CORPUS_STEPS
        or review_report.get("partial_snapshot_count") != 0
        or review_report.get("fresh_b2_opened") is not False
        or review_report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("independent corpus review authority is invalid")
    support = corpus_report.get("fixed_dp_support_coverage")
    if (
        corpus_report.get("status") != "passed"
        or corpus_report.get("mode") != "execute"
        or corpus_report.get("fixed_dp_head") != FIXED_DP_HEAD
        or corpus_report.get("attempted_identity_count")
        != EXPECTED_FULL_CORPUS_IDENTITIES
        or corpus_report.get("retained_identity_count")
        != EXPECTED_FULL_CORPUS_IDENTITIES
        or corpus_report.get("complete_identity_count") != complete
        or corpus_report.get("failed_identity_count") != retained
        or corpus_report.get("snapshot_count") != snapshots
        or corpus_report.get("fresh_b_opened") is not False
        or corpus_report.get("outcome_fields_consumed") != []
        or corpus_report.get("training_snapshot_outcome_fields") != []
        or corpus_report.get("runtime_outcomes_not_read_or_copied_to_training_snapshots")
        is not True
        or corpus_report.get("candidate_tensors_modified") is not False
        or corpus_report.get("selector_training_executed") is not False
        or corpus_report.get("calibration_executed") is not False
        or corpus_report.get("claim_authorized") is not False
        or type(support) is not dict
        or support.get("passed") is not True
    ):
        raise ValueError("full corpus scientific support authority is invalid")
    return {
        "identity_denominator": EXPECTED_FULL_CORPUS_IDENTITIES,
        "complete_identity_count": complete,
        "typed_retained_failure_count": retained,
        "snapshot_count": snapshots,
        "fixed_dp_support_coverage": support,
    }


def extract_training_row(
    snapshot: Any,
    index_row: dict[str, Any],
) -> dict[str, Any]:
    if type(snapshot) is not dict or set(snapshot) != {
        "schema_version",
        "feature_payload",
        "sidecar",
    }:
        raise ValueError("training snapshot top-level schema drifted")
    features = snapshot.get("feature_payload")
    sidecar = snapshot.get("sidecar")
    if type(features) is not dict or type(sidecar) is not dict:
        raise ValueError("training snapshot payloads must be objects")
    scenario_id = _sha(index_row.get("scenario_id"), "scenario_id")
    tick = _native_int(index_row.get("tick_index"), "tick_index")
    if (
        sidecar.get("scenario_id") != scenario_id
        or sidecar.get("tick_index") != tick
        or sidecar.get("fresh_b_opened") is not False
        or sidecar.get("outcome_fields_consumed") != []
        or sidecar.get("offline_label_provenance")
        != "pending_train_only_causal_label"
    ):
        raise ValueError("snapshot train-only authority drifted")
    atoms = _native_numeric(features.get("atom_matrix"), (8, 14), "atom_matrix")
    if np.any(atoms < 0.0):
        raise ValueError("atom_matrix must be nonnegative")
    source = _native_bool(features.get("source_valid_mask"), (8,), "source_valid")
    atom_source = _native_bool(
        features.get("atom_source_valid_mask"), (8, 14), "atom_source_valid"
    )
    applicable = _native_bool(
        features.get("atom_applicable_mask"), (8, 14), "atom_applicable"
    )
    physical = _native_bool(
        features.get("physical_feasible_mask"), (8,), "physical_feasible"
    )
    if (
        np.any(applicable & ~atom_source)
        or not np.array_equal(source, np.all(atom_source, axis=1))
        or np.any(physical & ~source)
        or not np.any(source)
    ):
        raise ValueError("snapshot source/applicability/physical contract drifted")
    raw_context = features.get("raw_context")
    context_source = features.get("context_source_complete")
    if type(raw_context) is not dict or set(raw_context) != set(RAW_FEATURE_NAMES):
        raise ValueError("raw_context must match the exact frozen feature set")
    if type(context_source) is not dict or set(context_source) != set(RAW_FEATURE_NAMES):
        raise ValueError("context source mask must match the exact frozen feature set")
    context_values = np.asarray(
        [_native_number(raw_context[name], f"raw_context.{name}") for name in RAW_FEATURE_NAMES],
        dtype=np.float64,
    )
    context_mask = np.asarray(
        [_native_bool_scalar(context_source[name], f"context_source.{name}") for name in RAW_FEATURE_NAMES],
        dtype=np.bool_,
    )
    block = _sha(
        sidecar.get("canonical_semantic_clone_sha256"),
        "canonical_semantic_clone_sha256",
    )
    family = _native_string(sidecar.get("family"), "family")
    tier = _native_string(sidecar.get("tier"), "tier")
    return {
        "raw_atoms": atoms,
        "source_valid_mask": source,
        "atom_source_valid_mask": atom_source,
        "atom_applicable_mask": applicable,
        "physical_feasible_mask": physical,
        "raw_context": context_values,
        "context_source_complete": context_mask,
        "route_ids": _sha(sidecar.get("route_identity_sha256"), "route identity"),
        "semantic_block_ids": block,
        "corridor_ids": _sha(sidecar.get("corridor_group_sha256"), "corridor"),
        "map_family_ids": _native_string(sidecar.get("map_family_id"), "map family"),
        "family_tier": f"{family}/{tier}",
        "seeds": _native_int(sidecar.get("seed"), "seed"),
        "ticks": tick,
        "scenario_ids": scenario_id,
        "scale_sha": _sha(
            sidecar.get("generation_behavior_scale_sha256"),
            "generation behavior scale",
        ),
    }


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"expected JSON object: {path}")
    return value


def _json_line(line: str, path: Path, line_number: int) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
    if type(value) is not dict:
        raise ValueError(f"expected JSON object at {path}:{line_number}")
    return value


def _native_numeric(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError(f"{name} must be native numeric{shape}")
    result = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


def _native_bool(value: Any, shape: tuple[int, ...], name: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype != np.bool_:
        raise ValueError(f"{name} must be native bool{shape}")
    return raw


def _native_bool_scalar(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a native boolean")
    return value


def _native_number(value: Any, name: str) -> float:
    if type(value) not in (int, float) or not np.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite native number")
    return float(value)


def _native_int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be a native integer")
    return value


def _native_string(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a nonempty native string")
    return value


def _sha(value: Any, name: str) -> str:
    result = _native_string(value, name)
    if len(result) != 64 or set(result) - set("0123456789abcdef"):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return result
