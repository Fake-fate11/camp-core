"""Stream the frozen official-nuPlan B8 corpus without reading outcomes.

This entry is deliberately V26-native.  It consumes the already frozen
result-blind plan, reads only current official source state, and creates one
same-ego B8 pool per selected Boston/Pittsburgh anchor.  Singapore remains an
identity-only held-out city in this stage.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v21_native import array_sha256  # noqa: E402
from camp_core.integrations.diffusion_planner_camp_context_math import RAW_FEATURE_NAMES  # noqa: E402
from camp_core.integrations.diffusion_planner_camp_training_math import (  # noqa: E402
    build_train_only_causal_labels,
    fit_train_only_atom_scales,
    hierarchical_snapshot_weights,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (  # noqa: E402
    V26_GENERATOR_ID,
    V26_TRAINING_ROWS_SCHEMA_VERSION,
    V26_TRAINING_SOURCE_SCHEMA_VERSION,
    v26_generator_topology,
)
from camp_core.integrations.diffusion_planner_v26_source_capabilities import (  # noqa: E402
    build_v26_camp_raw_context,
    materialize_v26_camp_atoms,
    v26_source_capabilities,
)
from camp_core.integrations.diffusion_planner_v26_nuplan import (  # noqa: E402
    FIXED_DP_HEAD,
    NUPLAN_V26_ADAPTER_ID,
    NUPLAN_V26_RUNNER_ID,
    build_v26_nuplan_unavailable_signal_authority,
    canonical_json_sha256,
    materialize_v26_nuplan_saved_state_input,
    run_v26_nuplan_single_invocation_b8,
    validate_v26_nuplan_source_record,
)
from scripts.integrations.run_diffusion_planner_v26_nuplan_mini_b8_smoke import (  # noqa: E402
    _CapturingModel,
    _load_fixed_dp_context,
    _normalized_single_input,
)


EVIDENCE_ROLE = "development_training_same_ego_b8_acquisition"
MANIFEST_SCHEMA_VERSION = "camp_dp_v26_nuplan_b8_corpus_manifest_v1"
UNIT_SCHEMA_VERSION = "camp_dp_v26_nuplan_b8_corpus_unit_v1"
RECEIPT_SCHEMA_VERSION = "camp_dp_v26_nuplan_b8_corpus_receipt_v1"
REPORTING_SCHEMA_VERSION = "camp_dp_v26_frozen_coverage_balanced_reporting_v1"
LABEL_SIDECAR_SCHEMA_VERSION = "camp_dp_v26_causal_policy_distillation_label_sidecar_v1"
PLAN_SCHEMA_VERSION = "camp_dp_v26_nuplan_result_blind_corpus_plan_v2"
PLAN_ROLE = "development_nonholdout_nuplan_result_blind_corpus_plan"
TRAIN_CITIES = frozenset({"boston", "pittsburgh"})
MATERIALIZED_PARTITIONS = frozenset({"train_iid", "val_iid"})
CITY_MAP_FAMILY = {
    "boston": "us-ma-boston",
    "pittsburgh": "us-pa-pittsburgh-hazelwood",
    "singapore": "sg-one-north",
}
POST_POOL_ZERO = {
    "model": 0,
    "dp": 0,
    "latent": 0,
    "generation": 0,
    "candidate_pool_mutation": 0,
    "trajectory_regeneration": 0,
}


class _UnitProcessingError(RuntimeError):
    def __init__(self, cause: Exception, *, model_calls: int) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.model_calls = int(model_calls)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def _atomic_write_npz(path: Path, **arrays: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, delete=False) as handle:
        np.savez_compressed(handle, **arrays)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def _json_native(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_native(item) for item in value]
    return value


@contextmanager
def _exclusive_worker_lock(path: Path) -> Iterator[None]:
    try:
        import fcntl
    except ImportError as exc:  # pragma: no cover - remote worker is Linux
        raise RuntimeError("V26 corpus worker lock requires POSIX fcntl") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        with path.open("r+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        path.unlink(missing_ok=True)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{label} must be a SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be hexadecimal") from exc
    return value


def _anchor_seed(plan_sha256: str, anchor_id: str) -> int:
    digest = hashlib.sha256(f"{plan_sha256}:{anchor_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1)


def _map_path(maps_root: Path, city: str) -> Path:
    family = CITY_MAP_FAMILY[city]
    candidates = sorted((maps_root / family).glob("*/map.gpkg"))
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"official nuPlan maps need exactly one map.gpkg for {city}: {candidates}"
        )
    return candidates[0]


def _source_identity(anchor: Mapping[str, Any]) -> dict[str, Any]:
    city = str(anchor["city"])
    event_memberships = anchor.get("event_memberships")
    if type(event_memberships) is not list:
        raise ValueError("frozen anchor event memberships are missing")
    event_strata = sorted(
        {
            str(item["stratum"])
            for item in event_memberships
            if type(item) is dict and type(item.get("stratum")) is str
        }
    )
    if not event_strata:
        raise ValueError("frozen anchor has no source event strata")
    scenario_scene = str(anchor["scenario_scene_token"])
    return validate_v26_nuplan_source_record(
        {
            "record_id": str(anchor["anchor_id"]),
            "official_split": "train",
            "log_token": str(anchor["log_token"]),
            "scenario_token": scenario_scene,
            "scene_token": scenario_scene,
            "state_token": str(anchor["state_token"]),
            "mission_route_roadblock_chain_sha256": str(
                anchor["mission_route_roadblock_chain_sha256"]
            ),
            "corridor_id": str(anchor["corridor_id"]),
            "geometry_clone_group_sha256": str(anchor["geometry_clone_group_sha256"]),
            "city": city,
            "map_family": CITY_MAP_FAMILY[city],
            "source_db_sha256": str(anchor["source_db_sha256"]),
            "map_sha256": str(anchor["map_sha256"]),
            "event_strata": event_strata,
        }
    )


def _validate_result_blind_plan(
    value: Mapping[str, Any], *, expected_plan_sha256: str
) -> dict[str, Any]:
    plan = dict(value)
    if (
        plan.get("schema_version") != PLAN_SCHEMA_VERSION
        or plan.get("evidence_role") != PLAN_ROLE
        or plan.get("payload_read") is not False
        or plan.get("outcome_fields_consumed") != []
        or plan.get("plan_sha256") != _require_sha256(expected_plan_sha256, "plan SHA")
    ):
        raise ValueError("result-blind plan identity or outcome boundary drifted")
    anchors = plan.get("planned_anchors")
    if type(anchors) is not list or len(anchors) != 63082:
        raise ValueError("result-blind plan anchor denominator drifted")
    if len({str(anchor.get("anchor_id")) for anchor in anchors}) != len(anchors):
        raise ValueError("result-blind plan anchor identities are not unique")
    return plan


def select_materialization_anchors(
    plan: Mapping[str, Any], *, expected_counts: Mapping[tuple[str, str], int] | None = None
) -> list[dict[str, Any]]:
    """Select exactly the frozen B/P train+validation memberships.

    The held-out Singapore identities stay in the plan but are deliberately not
    materialized or read by this training-stage worker.
    """

    selected = [
        dict(anchor)
        for anchor in plan["planned_anchors"]
        if anchor.get("city") in TRAIN_CITIES
        and anchor.get("partition") in MATERIALIZED_PARTITIONS
    ]
    selected.sort(key=lambda anchor: str(anchor["anchor_id"]))
    if len(selected) != len({anchor["anchor_id"] for anchor in selected}):
        raise ValueError("frozen B/P materialization anchor identities are not unique")
    counts: dict[tuple[str, str], int] = {}
    for anchor in selected:
        key = (str(anchor["city"]), str(anchor["partition"]))
        counts[key] = counts.get(key, 0) + 1
    expected = {
        ("boston", "train_iid"): 25000,
        ("pittsburgh", "train_iid"): 25000,
        ("boston", "val_iid"): 3550,
        ("pittsburgh", "val_iid"): 4532,
    }
    required = expected if expected_counts is None else dict(expected_counts)
    if counts != required:
        raise ValueError(f"frozen B/P partition membership drifted: {counts}")
    if expected_counts is None and len(selected) != 58082:
        raise ValueError("frozen B/P materialization denominator drifted")
    return selected


def build_frozen_reporting_contract(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Bind the post-audit reporting rule before any validation values exist."""

    rows = plan.get("city_partition_denominator")
    if type(rows) is not list:
        raise ValueError("result-blind plan lacks city/partition denominators")
    validation_logs: dict[str, int] = {}
    for row in rows:
        if type(row) is not dict or row.get("partition") != "val_iid":
            continue
        city = str(row.get("city"))
        validation_logs[city] = int(row.get("log_cluster_count", -1))
    if validation_logs != {"boston": 188, "pittsburgh": 25}:
        raise ValueError("frozen validation log-cluster counts drifted")
    return {
        "schema_version": REPORTING_SCHEMA_VERSION,
        "bound_result_blind_plan_sha256": str(plan["plan_sha256"]),
        "within_city_estimand": "frozen_coverage_balanced_corpus_performance",
        "within_city_weighting": "each frozen selected anchor contributes to its city corpus estimate; sampling_probability is retained, not inverse-probability weighted",
        "natural_traffic_prevalence_estimand": "not_target",
        "post_hoc_prevalence_weights_permitted": False,
        "between_city_iid_aggregation": {
            "method": "equal_city_macro",
            "weights": {"boston": 0.5, "pittsburgh": 0.5},
            "scope": "between_city_aggregation_only",
        },
        "independent_n": {
            "unit": "frozen_log_token_cluster",
            "validation_log_cluster_counts": validation_logs,
            "anchors_are_independent_n": False,
            "b8_rows_are_independent_n": False,
            "pittsburgh_precision_limitation": "25 validation log clusters; city-specific and pooled intervals must report this limitation",
        },
        "city_cluster_ci": dict(plan["analysis_freeze"]["cluster_aware_ci"]),
        "validation_values_read": False,
    }


def build_materialization_manifest(
    *,
    plan: Mapping[str, Any],
    plan_file_sha256: str,
    camp_head: str,
    fixed_dp: Mapping[str, str],
    raw_root: Path,
    maps_root: Path,
    shard_size: int,
) -> dict[str, Any]:
    anchors = select_materialization_anchors(plan)
    if shard_size < 1:
        raise ValueError("shard_size must be positive")
    reporting = build_frozen_reporting_contract(plan)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "camp_head": camp_head,
        "result_blind_plan": {
            "path_sha256": _require_sha256(plan_file_sha256, "plan file SHA"),
            "plan_sha256": str(plan["plan_sha256"]),
            "planned_unique_anchor_count": len(plan["planned_anchors"]),
            "materialized_unique_anchor_count": len(anchors),
            "held_out_identity_only_count": 5000,
            "materialized_partitions": ["train_iid", "val_iid"],
            "held_out_partition": "test_ood",
        },
        "fixed_dp": dict(fixed_dp),
        "runner_id": NUPLAN_V26_RUNNER_ID,
        "adapter_id": NUPLAN_V26_ADAPTER_ID,
        "generator_id": V26_GENERATOR_ID,
        "generator_topology": v26_generator_topology(),
        "same_pool_contract": {
            "candidate0_row": 0,
            "same_ego_batch_size": 8,
            "one_primary_forward_per_anchor": True,
            "post_pool_model_dp_latent_generation_calls": 0,
            "selector_status": "not_run_during_training_pool_generation",
        },
        "raw_source": {
            "raw_root": str(raw_root),
            "maps_root": str(maps_root),
            "source_payload_policy": "current_state_and_history_only_no_future_label_or_outcome",
        },
        "reporting_contract": reporting,
        "sharding": {
            "shard_size": shard_size,
            "candidate_pool_storage": "compressed_npz_by_city_partition",
            "atomic_unit_ledger": "units/{unit_index:05d}.json",
        },
        "outcome_fields_consumed": [],
        "holdout_accessed": False,
    }


def _resource_precheck(output_root: Path, selected_count: int, torch_module: Any) -> dict[str, int]:
    if not torch_module.cuda.is_available():
        raise RuntimeError("official nuPlan B8 corpus materialization requires CUDA")
    stat = os.statvfs(output_root.parent)
    free_bytes = int(stat.f_bavail * stat.f_frsize)
    candidate_bytes = int(selected_count) * 8 * 80 * 4 * 4
    minimum_bytes = max(2 * 1024**3, int(candidate_bytes * 2.5))
    if free_bytes < minimum_bytes:
        raise RuntimeError(
            f"insufficient output capacity: free={free_bytes} required={minimum_bytes}"
        )
    return {"free_bytes_before": free_bytes, "estimated_minimum_output_bytes": minimum_bytes}


def _status(ledger: "_CorpusLedger", *, phase: str) -> dict[str, Any]:
    counts = ledger.counts()
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "status": "running",
        "phase": phase,
        "denominator": counts,
        "model_calls": ledger.model_calls,
        "dp_calls": ledger.model_calls,
        "gpu_calls": int(ledger.model_calls > 0),
    }


class _CorpusLedger:
    def __init__(self, *, output_root: Path, manifest: Mapping[str, Any], anchors: Sequence[Mapping[str, Any]]) -> None:
        self.output_root = output_root.resolve()
        if self.output_root.exists() or self.output_root.is_symlink():
            raise FileExistsError(self.output_root)
        self.output_root.mkdir(parents=True)
        self.manifest = dict(manifest)
        self.anchors = [dict(anchor) for anchor in anchors]
        self.recorded: dict[int, str] = {}
        self.model_calls = 0
        self.shards: list[dict[str, Any]] = []
        self._buffer: list[tuple[dict[str, Any], np.ndarray]] = []
        _atomic_write_json(self.output_root / "manifest.json", self.manifest)
        _atomic_write_json(self.output_root / "run.status.json", _status(self, phase="pre_model"))

    def counts(self) -> dict[str, int]:
        complete = sum(status == "complete" for status in self.recorded.values())
        failed = sum(status == "typed_failure" for status in self.recorded.values())
        unattempted = sum(status == "unattempted" for status in self.recorded.values())
        return {
            "planned": len(self.anchors),
            "complete": complete,
            "failed": failed,
            "unattempted": unattempted,
        }

    def record(self, unit: Mapping[str, Any]) -> None:
        index = int(unit["unit_index"])
        if index < 0 or index >= len(self.anchors) or index in self.recorded:
            raise ValueError("V26 corpus unit index is invalid or already recorded")
        status = str(unit["terminal"]["status"])
        if status not in {"complete", "typed_failure", "unattempted"}:
            raise ValueError("V26 corpus unit terminal status is invalid")
        _atomic_write_json(self.output_root / "units" / f"{index:05d}.json", dict(unit))
        self.recorded[index] = status

    def append_candidate_pool(self, unit: Mapping[str, Any], candidates: np.ndarray) -> None:
        self._buffer.append((dict(unit), np.ascontiguousarray(candidates, dtype=np.float32)))

    def flush_shard(self) -> None:
        if not self._buffer:
            return
        units = [item[0] for item in self._buffer]
        candidate_pools = np.asarray([item[1] for item in self._buffer], dtype=np.float32)
        city = str(units[0]["source"]["city"])
        partition = str(units[0]["source"]["partition"])
        if any(
            str(unit["source"]["city"]) != city
            or str(unit["source"]["partition"]) != partition
            for unit in units
        ):
            raise ValueError("candidate shard cannot mix city or partition")
        number = sum(
            entry["city"] == city and entry["partition"] == partition for entry in self.shards
        )
        relative = Path("shards") / partition / city / f"shard_{number:05d}.npz"
        destination = self.output_root / relative
        _atomic_write_npz(
            destination,
            schema_version=np.asarray("camp_dp_v26_nuplan_b8_candidate_shard_v1"),
            plan_sha256=np.asarray(self.manifest["result_blind_plan"]["plan_sha256"]),
            unit_indices=np.asarray([unit["unit_index"] for unit in units], dtype=np.int64),
            anchor_ids=np.asarray([unit["source"]["anchor_id"] for unit in units], dtype="U512"),
            candidate_pools=candidate_pools,
            candidate_pool_sha256=np.asarray(
                [unit["candidate_pool"]["sha256"] for unit in units], dtype="U64"
            ),
            latent_row_sha256=np.asarray(
                [unit["latent"]["row_sha256"] for unit in units], dtype="U64"
            ),
        )
        self.shards.append(
            {
                "relative_path": str(relative),
                "sha256": _sha256_file(destination),
                "city": city,
                "partition": partition,
                "unit_indices": [int(unit["unit_index"]) for unit in units],
                "count": len(units),
            }
        )
        _atomic_write_json(
            self.output_root / "candidate_shard_catalog.json",
            {
                "schema_version": "camp_dp_v26_nuplan_b8_candidate_shard_catalog_v1",
                "plan_sha256": self.manifest["result_blind_plan"]["plan_sha256"],
                "shards": self.shards,
            },
        )
        self._buffer.clear()

    def complete_units(self, *, partition: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for index in sorted(self.recorded):
            if self.recorded[index] != "complete":
                continue
            unit = _read_json(self.output_root / "units" / f"{index:05d}.json", "unit receipt")
            if unit["source"]["partition"] == partition:
                result.append(unit)
        return result

    def finalize(self, *, terminal_error: str | None = None) -> dict[str, Any]:
        for index, anchor in enumerate(self.anchors):
            if index not in self.recorded:
                self.record(
                    _unattempted_unit(index=index, anchor=anchor, reason="parent_terminal_before_unit")
                )
        self.flush_shard()
        training = self.complete_units(partition="train_iid")
        validation = self.complete_units(partition="val_iid")
        training_artifacts = _write_training_artifacts(
            output_root=self.output_root,
            manifest=self.manifest,
            complete=training,
        )
        overall = self.counts()
        training_denominator = _partition_denominator(self, "train_iid")
        validation_denominator = _partition_denominator(self, "val_iid")
        report = {
            "schema_version": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "evidence_role": EVIDENCE_ROLE,
            "status": "terminal_training_evidence" if training else "terminal_no_trainable_pools",
            "fixed_dp_head": self.manifest["fixed_dp"]["head"],
            "camp_head": self.manifest["camp_head"],
            "result_blind_plan_sha256": self.manifest["result_blind_plan"]["plan_sha256"],
            "generator_id": V26_GENERATOR_ID,
            "generator_topology": v26_generator_topology(),
            "runner_id": NUPLAN_V26_RUNNER_ID,
            "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "training_rows_schema_version": V26_TRAINING_ROWS_SCHEMA_VERSION,
            "evaluation_schema": "camp_dp_v26_training_evidence_only_no_formal_evaluation_v1",
            "outcome_fields_consumed": [],
            "holdout_accessed": False,
            "source_manifest_sha256": self.manifest["result_blind_plan"]["plan_sha256"],
            **training_artifacts,
            "snapshot_count": len(training),
            "candidate_count": len(training) * 8,
            "denominator": training_denominator,
            "corpus_denominator": overall,
            "validation_pool_denominator": validation_denominator,
            "held_out_identity_only": {"partition": "test_ood", "count": 5000, "materialized": False},
            "reporting_contract_sha256": canonical_json_sha256(
                self.manifest["reporting_contract"]
            ),
            "terminal_error": terminal_error,
        }
        _atomic_write_json(self.output_root / "report.json", report)
        raw_receipt = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "evidence_role": EVIDENCE_ROLE,
            "manifest_sha256": _sha256_file(self.output_root / "manifest.json"),
            "result_blind_plan_sha256": self.manifest["result_blind_plan"]["plan_sha256"],
            "corpus_denominator": overall,
            "training_denominator": training_denominator,
            "validation_pool_denominator": validation_denominator,
            "model_calls": self.model_calls,
            "dp_calls": self.model_calls,
            "gpu_calls": int(self.model_calls > 0),
            "outcome_fields_consumed": [],
            "terminal_error": terminal_error,
        }
        _atomic_write_json(self.output_root / "raw_receipt.json", raw_receipt)
        terminal_status = "complete" if terminal_error is None else "typed_failure"
        _atomic_write_json(
            self.output_root / "run.status.json",
            {**raw_receipt, "status": terminal_status},
        )
        _atomic_write_json(
            self.output_root / "run.exit.json",
            {"terminal_status": terminal_status, **raw_receipt},
        )
        return report


def _partition_denominator(ledger: _CorpusLedger, partition: str) -> dict[str, int]:
    counts = {"planned": 0, "complete": 0, "failed": 0, "unattempted": 0}
    for index, anchor in enumerate(ledger.anchors):
        if anchor["partition"] != partition:
            continue
        counts["planned"] += 1
        status = ledger.recorded.get(index, "unattempted")
        if status == "complete":
            counts["complete"] += 1
        elif status == "typed_failure":
            counts["failed"] += 1
        else:
            counts["unattempted"] += 1
    return counts


def _unattempted_unit(*, index: int, anchor: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "unit_index": index,
        "source": {
            "anchor_id": str(anchor["anchor_id"]),
            "city": str(anchor["city"]),
            "partition": str(anchor["partition"]),
            "state_token": str(anchor["state_token"]),
        },
        "forward_topology": {
            "model_calls": 0,
            "dp_calls": 0,
            "primary_forward_count": 0,
            "sequential_forward_count": 0,
            **POST_POOL_ZERO,
        },
        "terminal": {"status": "unattempted", "failure_class": None, "failure_reason": reason},
    }


def _typed_failure_unit(
    *, index: int, anchor: Mapping[str, Any], error: Exception, model_calls: int
) -> dict[str, Any]:
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "unit_index": index,
        "source": {
            "anchor_id": str(anchor["anchor_id"]),
            "city": str(anchor["city"]),
            "partition": str(anchor["partition"]),
            "state_token": str(anchor["state_token"]),
        },
        "forward_topology": {
            "model_calls": model_calls,
            "dp_calls": model_calls,
            "primary_forward_count": model_calls,
            "sequential_forward_count": 0,
            **POST_POOL_ZERO,
        },
        "terminal": {
            "status": "typed_failure",
            "failure_class": type(error).__name__,
            "failure_reason": str(error),
        },
    }


def _raw_context_receipt(raw_context: Any) -> tuple[dict[str, float], dict[str, bool]]:
    raw_values = raw_context.as_dict()
    if tuple(raw_values) != RAW_FEATURE_NAMES:
        raise ValueError("raw-context feature order drifted")
    source_complete = tuple(bool(value) for value in raw_context.source_complete)
    if len(source_complete) != len(RAW_FEATURE_NAMES):
        raise ValueError("raw-context completeness dimension drifted")
    return raw_values, dict(zip(RAW_FEATURE_NAMES, source_complete))


def _complete_unit(
    *,
    index: int,
    anchor: Mapping[str, Any],
    source: Mapping[str, Any],
    pool: Mapping[str, Any],
    atoms: Mapping[str, Any],
    raw_context: Any,
    signal_authority: Mapping[str, Any],
    phase_receipt: Mapping[str, Any],
    seed: int,
) -> dict[str, Any]:
    atom_matrix = np.asarray(atoms["atom_matrix"], dtype=np.float64)
    raw_values, source_complete = _raw_context_receipt(raw_context)
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "unit_index": index,
        "source": {
            "anchor_id": str(anchor["anchor_id"]),
            "city": str(anchor["city"]),
            "partition": str(anchor["partition"]),
            "state_token": str(anchor["state_token"]),
            "log_token": str(anchor["log_token"]),
            "scenario_scene_token": str(anchor["scenario_scene_token"]),
            "corridor_id": str(anchor["corridor_id"]),
            "geometry_clone_group_sha256": str(anchor["geometry_clone_group_sha256"]),
            "mission_route_roadblock_chain_sha256": str(
                anchor["mission_route_roadblock_chain_sha256"]
            ),
            "source_db_sha256": str(anchor["source_db_sha256"]),
            "map_sha256": str(anchor["map_sha256"]),
            "event_memberships": _json_native(anchor["event_memberships"]),
            "seed": seed,
            "source_identity_sha256": str(source["source_identity_sha256"]),
        },
        "latent": {
            "shape": list(pool["latent_shape"]),
            "tensor_sha256": str(pool["latent_tensor_sha256"]),
            "row_sha256": list(pool["latent_row_sha256"]),
            "unique": len(set(pool["latent_row_sha256"])) == 8,
        },
        "candidate_pool": {
            "shape": list(pool["candidate_shape"]),
            "dtype": str(pool["candidate_dtype"]),
            "finite": bool(pool["candidate_finite"]),
            "sha256": str(pool["candidate_tensor_sha256_before"]),
            "row_sha256": list(pool["candidate_row_sha256"]),
            "candidate0_row": 0,
            "candidate0_default_identity": dict(pool["candidate0"]),
        },
        "forward_topology": {
            "model_calls": 1,
            "dp_calls": 1,
            "primary_forward_count": int(pool["primary_forward_count"]),
            "sequential_forward_count": int(pool["sequential_forward_count"]),
            **POST_POOL_ZERO,
        },
        "signal_authority": {
            "adapter_id": signal_authority["adapter_id"],
            "source_state": signal_authority["source_state"],
            "typed_missing_atoms": list(signal_authority["typed_missing_atoms"]),
            "red_light_endpoint_status": signal_authority["red_light_endpoint_status"],
            "source_chain_sha256": signal_authority["causal_signal_atom_input"]["source_chain_sha256"],
        },
        "atom_phase_receipt": _json_native(phase_receipt),
        "training_pool": {
            "atom_matrix": atom_matrix.tolist(),
            "atom_source_valid_mask": np.asarray(atoms["atom_source_valid_mask"], dtype=bool).tolist(),
            "atom_applicable_mask": np.asarray(atoms["atom_applicable_mask"], dtype=bool).tolist(),
            "source_valid_mask": np.asarray(atoms["source_valid_mask"], dtype=bool).tolist(),
            "physical_feasible_mask": np.asarray(atoms["physical_feasible_mask"], dtype=bool).tolist(),
            "raw_context": raw_values,
            "context_source_complete": source_complete,
            "event_manifest_sha256": canonical_json_sha256(
                {"event_memberships": anchor["event_memberships"]}
            ),
        },
        "selector": {"status": "not_run_training_pool_generation"},
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
    }


def _write_training_artifacts(
    *, output_root: Path, manifest: Mapping[str, Any], complete: Sequence[Mapping[str, Any]]
) -> dict[str, str]:
    count = len(complete)
    rows_path = output_root / "training_rows.npz"
    scales_path = output_root / "training_scales.json"
    label_path = output_root / "label_sidecar.json"
    if count:
        atoms = np.asarray([unit["training_pool"]["atom_matrix"] for unit in complete], dtype=np.float64)
        atom_source = np.asarray(
            [unit["training_pool"]["atom_source_valid_mask"] for unit in complete], dtype=np.bool_
        )
        applicable = np.asarray(
            [unit["training_pool"]["atom_applicable_mask"] for unit in complete], dtype=np.bool_
        )
        source = np.asarray(
            [unit["training_pool"]["source_valid_mask"] for unit in complete], dtype=np.bool_
        )
        physical = np.asarray(
            [unit["training_pool"]["physical_feasible_mask"] for unit in complete], dtype=np.bool_
        )
        route_ids = np.asarray(
            [unit["source"]["mission_route_roadblock_chain_sha256"] for unit in complete], dtype="U64"
        )
        corridor_ids = np.asarray([unit["source"]["corridor_id"] for unit in complete], dtype="U128")
        family_ids = np.asarray([CITY_MAP_FAMILY[unit["source"]["city"]] for unit in complete], dtype="U128")
        seeds = np.asarray([unit["source"]["seed"] for unit in complete], dtype=np.int64)
        scenario_ids = np.asarray([unit["source"]["anchor_id"] for unit in complete], dtype="U512")
        raw_context = np.asarray(
            [
                [unit["training_pool"]["raw_context"][name] for name in RAW_FEATURE_NAMES]
                for unit in complete
            ],
            dtype=np.float64,
        )
        context_source = np.asarray(
            [
                [unit["training_pool"]["context_source_complete"][name] for name in RAW_FEATURE_NAMES]
                for unit in complete
            ],
            dtype=np.bool_,
        )
        latent_hashes = np.asarray([unit["latent"]["row_sha256"] for unit in complete], dtype="U64")
        candidate_hashes = np.asarray(
            [unit["candidate_pool"]["row_sha256"] for unit in complete], dtype="U64"
        )
        event_hashes = np.asarray(
            [unit["training_pool"]["event_manifest_sha256"] for unit in complete], dtype="U64"
        )
        weights = hierarchical_snapshot_weights(
            route_ids.tolist(), corridor_ids.tolist(), seeds.tolist(), [0] * count
        )
        scale_receipt = fit_train_only_atom_scales(
            atoms, source, atom_source, applicable, weights, corridor_ids.tolist()
        )
        scales = np.asarray(scale_receipt["scales"], dtype=np.float64)
        labels = build_train_only_causal_labels(
            atoms, source, atom_source, applicable, physical, scales
        )
    else:
        atoms = np.zeros((0, 8, 14), dtype=np.float64)
        atom_source = np.zeros((0, 8, 14), dtype=np.bool_)
        applicable = np.zeros((0, 8, 14), dtype=np.bool_)
        source = np.zeros((0, 8), dtype=np.bool_)
        physical = np.zeros((0, 8), dtype=np.bool_)
        route_ids = np.asarray([], dtype="U1")
        corridor_ids = np.asarray([], dtype="U1")
        family_ids = np.asarray([], dtype="U1")
        seeds = np.asarray([], dtype=np.int64)
        scenario_ids = np.asarray([], dtype="U1")
        raw_context = np.zeros((0, len(RAW_FEATURE_NAMES)), dtype=np.float64)
        context_source = np.zeros((0, len(RAW_FEATURE_NAMES)), dtype=np.bool_)
        latent_hashes = np.zeros((0, 8), dtype="U64")
        candidate_hashes = np.zeros((0, 8), dtype="U64")
        event_hashes = np.asarray([], dtype="U64")
        weights = np.zeros((0,), dtype=np.float64)
        scales = np.ones(14, dtype=np.float64)
        scale_receipt = {
            "schema_version": "camp_dp_v26_no_trainable_pool_scales_v1",
            "scales": scales.tolist(),
            "status": "not_evaluated_no_complete_pools",
        }
        labels = {
            "normalized_atoms": atoms,
            "oracle_indices": np.zeros((0,), dtype=np.int64),
            "margins": np.zeros((0, 8), dtype=np.float64),
        }
    _atomic_write_json(scales_path, _json_native(scale_receipt))
    _atomic_write_npz(
        rows_path,
        schema_version=np.asarray(V26_TRAINING_ROWS_SCHEMA_VERSION),
        normalized_atoms_14d=np.asarray(labels["normalized_atoms"], dtype=np.float64),
        raw_context=raw_context,
        context_source_complete=context_source,
        oracle_indices=np.asarray(labels["oracle_indices"], dtype=np.int64),
        margins=np.asarray(labels["margins"], dtype=np.float64),
        source_valid_mask=source,
        atom_source_valid_mask=atom_source,
        atom_applicable_mask=applicable,
        physical_feasible_mask=physical,
        record_weights=np.asarray(weights, dtype=np.float64),
        route_ids=route_ids,
        corridor_ids=corridor_ids,
        map_family_ids=family_ids,
        seeds=seeds,
        scenario_ids=scenario_ids,
        source_manifest_sha256=np.asarray(manifest["result_blind_plan"]["plan_sha256"]),
        event_manifest_sha256=event_hashes,
        model_call_count=np.ones((count,), dtype=np.int64),
        sequential_forward_count=np.zeros((count,), dtype=np.int64),
        candidate0_row=np.zeros((count,), dtype=np.int64),
        post_pool_model_dp_latent_generation_calls=np.zeros((count,), dtype=np.int64),
        candidate_pool_mutation_count=np.zeros((count,), dtype=np.int64),
        trajectory_regeneration_count=np.zeros((count,), dtype=np.int64),
        latent_row_sha256=latent_hashes,
        candidate_row_sha256=candidate_hashes,
        training_scales=scales,
    )
    label = {
        "schema_version": LABEL_SIDECAR_SCHEMA_VERSION,
        "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
        "label_contract": "causal_policy_distillation_no_outcome",
        "fresh_or_outcome_consumed": False,
        "identity_fields_used_as_label_or_feature": False,
        "source_manifest_sha256": manifest["result_blind_plan"]["plan_sha256"],
        "training_scales_sha256": _sha256_file(scales_path),
    }
    _atomic_write_json(label_path, label)
    return {
        "training_rows_sha256": _sha256_file(rows_path),
        "training_scales_sha256": _sha256_file(scales_path),
        "label_sidecar_sha256": _sha256_file(label_path),
    }


def _source_paths(anchor: Mapping[str, Any], raw_root: Path, maps_root: Path) -> tuple[Path, Path]:
    relative = Path(str(anchor["raw_db_relative_path"]))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("frozen raw DB relative path escaped the raw root")
    db_path = (raw_root / relative).resolve()
    raw_parent = raw_root.resolve()
    if raw_parent not in db_path.parents or not db_path.is_file():
        raise FileNotFoundError(f"frozen source DB is absent: {db_path}")
    return db_path, _map_path(maps_root, str(anchor["city"]))


def _process_anchor(
    *,
    index: int,
    anchor: Mapping[str, Any],
    plan_sha256: str,
    raw_root: Path,
    maps_root: Path,
    context: Mapping[str, Any],
) -> tuple[dict[str, Any], np.ndarray]:
    capture: _CapturingModel | None = None
    try:
        source = _source_identity(anchor)
        db_path, map_path = _source_paths(anchor, raw_root, maps_root)
        adapted = materialize_v26_nuplan_saved_state_input(
            db_path=str(db_path),
            map_path=str(map_path),
            state_token=source["state_token"],
            source_identity=source,
        )
        causal_input = {key: np.asarray(value) for key, value in adapted["dp_input"].items()}
        signal_authority = build_v26_nuplan_unavailable_signal_authority(
            source_identity=source,
            route_lanes=np.asarray(causal_input["route_lanes"]),
            decision_timestamp_us=int(adapted["decision_timestamp_us"]),
            traffic_light_state_available=bool(
                adapted["materialization_metadata"]["traffic_light_state_available"]
            ),
        )
        normalized = _normalized_single_input(causal_input, context)
        capture = _CapturingModel(context["model"])
        decoder = context["model"].decoder
        prior_guidance_fn, prior_guidance_scale = decoder._guidance_fn, decoder._guidance_scale
        decoder._guidance_fn, decoder._guidance_scale = None, 0.5
        try:
            pool = run_v26_nuplan_single_invocation_b8(
                model=capture,
                normalized_single_input=normalized,
                route_identity_sha256=source["mission_route_roadblock_chain_sha256"],
                tick_index=index,
                root_seed=_anchor_seed(plan_sha256, source["record_id"]),
                torch_module=context["torch"],
            )
        finally:
            decoder._guidance_fn, decoder._guidance_scale = prior_guidance_fn, prior_guidance_scale
        if capture.calls != 1 or capture.full_prediction is None:
            raise ValueError("official corpus anchor did not make exactly one B8 forward")
        candidates = np.asarray(pool["candidate_tensor"], dtype=np.float32)
        before = str(pool["candidate_tensor_sha256_before"])
        neighbor_valid = np.any(
            np.abs(np.asarray(causal_input["neighbor_agents_past"])) > 1e-8,
            axis=tuple(range(1, np.asarray(causal_input["neighbor_agents_past"]).ndim)),
        )
        phase_receipt: dict[str, Any] = {}
        capabilities = v26_source_capabilities(
            speed_limit_status="typed_missing",
            signal_authority=signal_authority,
        )
        atoms = materialize_v26_camp_atoms(
            candidates=candidates,
            causal_input=causal_input,
            neighbor_predictions=np.asarray(capture.full_prediction[:, 1:33]),
            neighbor_valid_mask=neighbor_valid,
            signal_mask=np.ones(8, dtype=bool),
            planned_red_light_cost=np.zeros(8, dtype=np.float64),
            signal_authority=signal_authority,
            capabilities=capabilities,
            dt=0.1,
            phase_receipt=phase_receipt,
        )
        if atoms.get("atom_matrix") is None:
            raise ValueError(f"official corpus atom materialization unavailable: {atoms.get('exclusion_reason')}")
        if array_sha256(candidates) != before:
            raise ValueError("official corpus atom materialization mutated the B8 pool")
        raw_context = build_v26_camp_raw_context(
            causal_input=causal_input,
            candidates=candidates,
            source_valid_mask=np.asarray(atoms["source_valid_mask"], dtype=bool),
            signal_authority=signal_authority,
            capabilities=capabilities,
        )
        seed = _anchor_seed(plan_sha256, source["record_id"])
        return (
            _complete_unit(
                index=index,
                anchor=anchor,
                source=source,
                pool=pool,
                atoms=atoms,
                raw_context=raw_context,
                signal_authority=signal_authority,
                phase_receipt=phase_receipt,
                seed=seed,
            ),
            candidates,
        )
    except Exception as error:
        raise _UnitProcessingError(
            error,
            model_calls=0 if capture is None else capture.calls,
        ) from error


def run(args: argparse.Namespace) -> Path:
    plan_path = args.plan.resolve(strict=True)
    plan = _validate_result_blind_plan(
        _read_json(plan_path, "result-blind plan"), expected_plan_sha256=args.plan_sha256
    )
    raw_root = args.raw_root.resolve(strict=True)
    maps_root = args.maps_root.resolve(strict=True)
    output_root = args.output_root.resolve(strict=False)
    dp_repo = args.fixed_dp_repo.resolve(strict=True)
    checkpoint = args.checkpoint.resolve(strict=True)
    args_json = args.args_json.resolve(strict=True)
    if args.fixed_dp_head != FIXED_DP_HEAD:
        raise ValueError("fixed-DP scientific head drifted")
    if _sha256_file(checkpoint) != args.checkpoint_sha256 or _sha256_file(args_json) != args.args_sha256:
        raise ValueError("fixed-DP checkpoint or args identity drifted")
    camp_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    anchors = select_materialization_anchors(plan)
    fixed_dp = {
        "head": args.fixed_dp_head,
        "checkpoint_sha256": args.checkpoint_sha256,
        "args_sha256": args.args_sha256,
        "guidance_policy": "disabled",
    }
    manifest = build_materialization_manifest(
        plan=plan,
        plan_file_sha256=_sha256_file(plan_path),
        camp_head=camp_head,
        fixed_dp=fixed_dp,
        raw_root=raw_root,
        maps_root=maps_root,
        shard_size=args.shard_size,
    )
    lock_path = args.lock_path.resolve(strict=False)
    ledger: _CorpusLedger | None = None
    current_index: int | None = None
    try:
        with _exclusive_worker_lock(lock_path):
            ledger = _CorpusLedger(output_root=output_root, manifest=manifest, anchors=anchors)
            context = _load_fixed_dp_context(dp_repo, checkpoint, args_json)
            _atomic_write_json(output_root / "capacity_preflight.json", _resource_precheck(output_root, len(anchors), context["torch"]))
            _atomic_write_json(output_root / "run.status.json", _status(ledger, phase="streaming_b8"))
            for current_index, anchor in enumerate(anchors):
                try:
                    unit, candidates = _process_anchor(
                        index=current_index,
                        anchor=anchor,
                        plan_sha256=args.plan_sha256,
                        raw_root=raw_root,
                        maps_root=maps_root,
                        context=context,
                    )
                    ledger.model_calls += 1
                    ledger.record(unit)
                    if ledger._buffer and (
                        ledger._buffer[0][0]["source"]["city"] != unit["source"]["city"]
                        or ledger._buffer[0][0]["source"]["partition"]
                        != unit["source"]["partition"]
                    ):
                        ledger.flush_shard()
                    ledger.append_candidate_pool(unit, candidates)
                    if len(ledger._buffer) >= args.shard_size:
                        ledger.flush_shard()
                    if (current_index + 1) % args.status_interval == 0:
                        _atomic_write_json(output_root / "run.status.json", _status(ledger, phase="streaming_b8"))
                except Exception as error:
                    observed = error.model_calls if isinstance(error, _UnitProcessingError) else 0
                    ledger.model_calls += observed
                    ledger.record(
                        _typed_failure_unit(
                            index=current_index,
                            anchor=anchor,
                            error=error,
                            model_calls=observed,
                        )
                    )
                    _atomic_write_json(output_root / "run.status.json", _status(ledger, phase="streaming_b8"))
            report = ledger.finalize()
            return output_root / "report.json"
    except Exception as error:
        if ledger is not None:
            if current_index is not None and current_index not in ledger.recorded:
                ledger.record(
                    _typed_failure_unit(
                        index=current_index,
                        anchor=anchors[current_index],
                        error=error,
                        model_calls=0,
                    )
                )
            ledger.finalize(terminal_error=f"{type(error).__name__}: {error}")
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--maps-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--args-json", type=Path, required=True)
    parser.add_argument("--args-sha256", required=True)
    parser.add_argument("--fixed-dp-head", required=True)
    parser.add_argument("--shard-size", type=int, default=64)
    parser.add_argument("--status-interval", type=int, default=64)
    args = parser.parse_args(argv)
    if args.shard_size < 1 or args.status_interval < 1:
        parser.error("--shard-size and --status-interval must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    output = run(parse_args(argv))
    print(json.dumps({"terminal": "complete", "report": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
