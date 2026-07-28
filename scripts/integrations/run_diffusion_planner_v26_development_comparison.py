"""Run the frozen V26 source-authoritative adapted-14D development comparison.

Each of candidate0, CAMP-Static14D, and CAMP-Scene14D owns a reset state and
one same-ego B8 forward.  This is development capability evidence only; it
does not share pools across arms and it makes no effect or safety claim.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v21_native import array_sha256  # noqa: E402
from camp_core.integrations.diffusion_planner_v26_development_comparison import (  # noqa: E402
    CANDIDATE0_ARM,
    COMPARISON_ARMS,
    COMPARISON_EVIDENCE_ROLE,
    COMPARISON_RECEIPT_SCHEMA_VERSION,
    RUNTIME_ARM_BY_COMPARISON_ARM,
    STATIC14D_ARM,
    SCENE14D_ARM,
    build_development_comparison_manifest,
    canonical_json_sha256,
    industrial_v3_endpoint_vector,
    load_v26_adapted_selector_assets,
    validate_development_comparison_inventory,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (  # noqa: E402
    V26_SOURCE_TRAFFIC_SIGNAL_MODE,
    build_v26_adapted_comparison_integration_boundary,
    enforce_v26_dp312_lanelet2_precedence,
    resolve_v26_signal_adapter,
    validate_v26_source_map_signal_binding,
)
from camp_core.integrations.diffusion_planner_v26_native_runner import (  # noqa: E402
    run_v26_native_same_ego_b8_replay,
)
from camp_core.integrations.diffusion_planner_v26_source_authority import (  # noqa: E402
    build_v26_source_signal_config,
    require_v26_route_connectivity,
    v26_route_geometry_receipt,
    v26_source_bound_projection,
    v26_source_inventory_binding,
)


MIN_FREE_BYTES = 10 * 1024**3


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, encoding="utf-8"
    ).strip()


def _tracked_changes(path: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=path,
            text=True,
            encoding="utf-8",
        ).strip()
    )


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


@contextmanager
def _exclusive_worker_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"V26 development-comparison worker lock already exists: {path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {"pid": os.getpid(), "role": COMPARISON_EVIDENCE_ROLE},
                handle,
                sort_keys=True,
                separators=(",", ":"),
            )
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        path.unlink(missing_ok=True)


def _require_file_binding(value: Any, label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "sha256"}:
        raise ValueError(f"V26 comparison {label} binding is required")
    path = Path(str(value["path"])).resolve()
    expected = str(value["sha256"])
    if not path.is_file() or _sha256_file(path) != expected:
        raise ValueError(f"V26 comparison {label} asset drifted")
    return {"path": str(path), "sha256": expected}


def _load_base_probe_config(path: Path) -> dict[str, Any]:
    source = Path(path).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    value = json.loads(source.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("V26 comparison base probe must be an object")
    protocol = value.get("protocol")
    fixed_dp = value.get("fixed_dp")
    spawn = value.get("spawn_config")
    seeds = value.get("seeds")
    if (
        type(protocol) is not dict
        or protocol.get("route_role") != "development_nonholdout"
        or protocol.get("holdout_access_authorized") is not False
        or type(fixed_dp) is not dict
        or type(fixed_dp.get("head")) is not str
        or type(fixed_dp.get("native_source_sha256")) is not dict
        or type(spawn) is not dict
        or type(seeds) is not dict
    ):
        raise ValueError("V26 comparison base probe identity drifted")
    checkpoint = _require_file_binding(fixed_dp.get("checkpoint"), "checkpoint")
    args_json = _require_file_binding(fixed_dp.get("args_json"), "args")
    source_hashes = {
        str(key): str(item) for key, item in dict(fixed_dp["native_source_sha256"]).items()
    }
    if not source_hashes or any(len(item) != 64 for item in source_hashes.values()):
        raise ValueError("V26 comparison fixed-DP native source hashes are incomplete")
    return {
        "source_path": str(source),
        "source_sha256": _sha256_file(source),
        "fixed_dp": {
            "head": str(fixed_dp["head"]),
            "checkpoint": checkpoint,
            "args_json": args_json,
            "native_source_sha256": source_hashes,
        },
        "spawn_config": dict(spawn),
        "seed_template": {str(key): item for key, item in seeds.items()},
    }


def _route_asset(route_type: Any, route_record: Mapping[str, Any], path: Path) -> str:
    import numpy as np

    spec = dict(route_record["route_spec"])
    lanelets = [int(item) for item in spec["lanelet_ids"]]
    route = route_type(
        str(spec["map_path"]),
        np.asarray(spec["start_pose"], dtype=np.float64),
        np.asarray(spec["goal_pose"], dtype=np.float64),
        int(lanelets[0]),
        int(lanelets[-1]),
        route_lanelet_ids=lanelets,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    route.save(path)
    return _sha256_file(path)


def _schedule(cluster: Mapping[str, Any]) -> dict[str, Any]:
    route = dict(cluster["route"])
    return {
        "family_id": route["family_id"],
        "route_id": route["route_id"],
        "corridor_id": route["corridor_id"],
        "source_artifact_sha256": route["source_artifact_sha256"],
        "event_manifest_sha256": route["event_manifest_sha256"],
        "route_record": {
            "identity_sha256": route["route_identity_sha256"],
            "source_map_path": route["route_spec"]["map_path"],
            "source_map_sha256": route["source_map_sha256"],
            "source_geometry_sha256": route["derived_geometry_sha256"],
            "lanelet_ids": list(route["route_lanelet_ids"]),
            "source_stratum": dict(route["source_stratum"]),
            "route_spec": dict(route["route_spec"]),
        },
    }


def _route_probe_config(
    *,
    base: Mapping[str, Any],
    schedule: Mapping[str, Any],
    route_path: Path,
    route_sha256: str,
    scenario_seed: int,
    signal: Mapping[str, Any],
) -> dict[str, Any]:
    record = dict(schedule["route_record"])
    seeds = dict(base["seed_template"])
    seeds["scenario"] = int(scenario_seed)
    spawn = dict(base["spawn_config"])
    spawn["seed"] = int(scenario_seed)
    return {
        "schema_version": "camp_dp_v26_development_comparison_probe_config_v1",
        "evidence_role": COMPARISON_EVIDENCE_ROLE,
        "protocol": {
            "route_role": "development_nonholdout",
            "holdout_access_authorized": False,
            "claim_authorized": False,
            "comparison_only": True,
            "route_id": schedule["route_id"],
        },
        "routes": [{"name": schedule["route_id"], "path": str(route_path), "sha256": route_sha256}],
        "map": {"path": record["source_map_path"], "sha256": record["source_map_sha256"]},
        "seeds": seeds,
        "spawn_config": spawn,
        "fixed_dp": dict(base["fixed_dp"]),
        **dict(signal),
    }


def _resource_precheck(output_dir: Path, device: str, torch: Any) -> None:
    if device != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("V26 comparison requires an available CUDA GPU")
    if shutil.disk_usage(output_dir.parent).free < MIN_FREE_BYTES:
        raise RuntimeError("V26 comparison requires at least 10 GiB free disk")
    probe = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if probe.returncode:
        raise RuntimeError("V26 comparison cannot verify GPU conflict via nvidia-smi")
    if any(line.strip() for line in probe.stdout.splitlines()):
        raise RuntimeError("V26 comparison GPU conflict detected before model load")


def _selector_subset(arm_id: str) -> tuple[str, ...]:
    if arm_id == CANDIDATE0_ARM:
        return ("pool_matched_candidate0",)
    if arm_id == STATIC14D_ARM:
        return ("pool_matched_candidate0", "Static14D")
    if arm_id == SCENE14D_ARM:
        return ("pool_matched_candidate0", "Scene14D")
    raise ValueError("V26 comparison arm is unknown")


def _forward_calls(*, callback: Any | None, raw: Mapping[str, Any] | None) -> dict[str, int]:
    after = 0 if callback is None else int(callback.model_call_count)
    primary = 0 if raw is None else int(raw.get("primary_pool_model_call_count", 0))
    return {
        "model_call_count_before": max(0, after - primary),
        "model_call_count_after": after,
        "model_call_delta": primary,
        "primary_forward_count": primary,
        "sequential_forward_count": 0,
        "post_pool_model_forward_count": 0,
        "post_pool_dp_forward_count": 0,
        "post_pool_latent_replacement_count": 0,
        "post_pool_candidate_generation_count": 0,
        "candidate_pool_mutation_count": 0,
        "trajectory_regeneration_count": 0,
    }


def _runtime_unit(
    *, raw: Mapping[str, Any], callback: Any, unit: Mapping[str, Any], cluster: Mapping[str, Any]
) -> dict[str, Any]:
    if raw.get("status") != "ok":
        raise ValueError("V26 comparison completed unit requires a successful runtime tick")
    rows = [str(item) for item in raw["candidate_row_sha256"]]
    arm_id = str(unit["arm_id"])
    operational = str(unit["runtime_operational_arm"])
    selector_arms = list(raw.get("selector_arms", []))
    expected_selector_arms = list(_selector_subset(arm_id))
    if (
        len(rows) != 8
        or len(set(rows)) != 8
        or raw.get("candidate_tensor_sha256_before") != raw.get("candidate_tensor_sha256_after")
        or selector_arms != expected_selector_arms
        or raw.get("operational_arm") != operational
        or int(raw.get("primary_pool_model_call_count", -1)) != 1
    ):
        raise ValueError("V26 comparison B8/selector topology drifted")
    zero = dict(raw["zero_call_receipt"])
    if any(
        int(zero.get(key, -1)) != 0
        for key in (
            "dp_or_model_calls_after_pool",
            "latent_replacements_after_pool",
            "candidate_generations_after_pool",
        )
    ):
        raise ValueError("V26 comparison post-pool zero-call receipt drifted")
    selected = int(raw["selected_index"])
    operational_receipt = dict(raw["real_selector_receipts"][operational])
    if (
        operational_receipt.get("status") != "ok"
        or int(operational_receipt.get("selected_index")) != selected
        or operational_receipt.get("selected_row_sha256") != rows[selected]
        or raw.get("selected_trajectory_sha256") != rows[selected]
        or raw.get("default_output_sha256") != rows[0]
    ):
        raise ValueError("V26 comparison selected/simulator row binding drifted")
    metadata = dict(raw["same_ego_batch_metadata"])
    if metadata.get("same_ego_batch_size") != 8 or metadata.get("nonlatent_rows_identical") is not True:
        raise ValueError("V26 comparison same-ego B8 input drifted")
    latency = dict(raw.get("latency_ms", {})).get("total_planning")
    return {
        "unit_index": int(unit["unit_index"]),
        "cluster_index": int(unit["cluster_index"]),
        "cluster_id_sha256": str(unit["cluster_id_sha256"]),
        "planned_state_id_sha256": str(unit["planned_state_id_sha256"]),
        "arm_id": arm_id,
        "route": {
            "route_id": cluster["route"]["route_id"],
            "corridor_id": cluster["route"]["corridor_id"],
            "family_id": cluster["route"]["family_id"],
            "source_event_identity_sha256": cluster["route"]["source_event_identity_sha256"],
            "physical_route_identity_sha256": cluster["route"]["physical_route_identity_sha256"],
        },
        "input": {
            "source_input_sha256": str(raw["source_input_sha256"]),
            "expanded_input_sha256": str(raw["input_sha256"]),
            "same_ego_batch_size": 8,
            "nonlatent_rows_identical": True,
            "tensor_metadata": dict(metadata["tensor_metadata"]),
        },
        "latent": {
            "seed": int(raw["latent_seed"]),
            "shape": list(raw["latent_shape"]),
            "dtype": str(raw["latent_dtype"]),
            "finite": bool(raw.get("candidate_finite")),
            "tensor_sha256": str(raw["latent_tensor_sha256"]),
            "row_sha256": [str(item) for item in raw["latent_row_sha256"]],
            "row0_zero": True,
        },
        "candidate_pool": {
            "pool_sha256": str(raw["candidate_tensor_sha256_after"]),
            "row_sha256": rows,
            "shape": list(raw["candidate_shape"]),
            "dtype": str(raw["candidate_dtype"]),
            "finite": bool(raw["candidate_finite"]),
            "candidate0_row": 0,
            "default_output_sha256": rows[0],
        },
        "forward_calls": _forward_calls(callback=callback, raw=raw),
        "selection": {
            "operational_arm": operational,
            "selector_arms": selector_arms,
            "selected_index": selected,
            "selected_row_sha256": rows[selected],
            "selected_arm_receipt": operational_receipt,
            "selection_flip_vs_row0": bool(selected != 0),
        },
        "simulator": {"selected_index": selected, "selected_row_sha256": rows[selected]},
        "endpoint_vector": industrial_v3_endpoint_vector(
            planning_latency_ms=None if latency is None else float(latency)
        ),
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
    }


def _failure_unit(
    *,
    unit: Mapping[str, Any],
    cluster: Mapping[str, Any],
    failure_class: str,
    failure_reason: str,
    raw: Mapping[str, Any] | None = None,
    callback: Any | None = None,
) -> dict[str, Any]:
    route = cluster["route"]
    raw_data = {} if raw is None else dict(raw)
    return {
        "unit_index": int(unit["unit_index"]),
        "cluster_index": int(unit["cluster_index"]),
        "cluster_id_sha256": str(unit["cluster_id_sha256"]),
        "planned_state_id_sha256": str(unit["planned_state_id_sha256"]),
        "arm_id": str(unit["arm_id"]),
        "route": {
            "route_id": route["route_id"],
            "corridor_id": route["corridor_id"],
            "family_id": route["family_id"],
            "source_event_identity_sha256": route["source_event_identity_sha256"],
            "physical_route_identity_sha256": route["physical_route_identity_sha256"],
        },
        "input": None,
        "latent": None,
        "candidate_pool": None,
        "forward_calls": _forward_calls(callback=callback, raw=raw),
        "selection": None,
        "simulator": None,
        "endpoint_vector": industrial_v3_endpoint_vector(planning_latency_ms=None),
        "raw_status": raw_data.get("status"),
        "terminal": {
            "status": "typed_failure",
            "failure_class": str(failure_class),
            "failure_reason": str(failure_reason),
        },
    }


def _unattempted_unit(*, unit: Mapping[str, Any], cluster: Mapping[str, Any]) -> dict[str, Any]:
    result = _failure_unit(
        unit=unit,
        cluster=cluster,
        failure_class="",
        failure_reason="",
    )
    result["terminal"] = {"status": "unattempted", "failure_class": None, "failure_reason": None}
    return result


class _Ledger:
    def __init__(self, *, output_dir: Path, manifest: Mapping[str, Any]) -> None:
        self.output_dir = output_dir.resolve()
        if self.output_dir.exists():
            raise FileExistsError(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.manifest = dict(manifest)
        self.units: list[dict[str, Any] | None] = [None] * len(self.manifest["unit_plan"])
        _atomic_write_json(self.output_dir / "manifest.json", self.manifest)
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {
                "evidence_role": COMPARISON_EVIDENCE_ROLE,
                "status": "running_pre_model_qualification",
                "planned_clusters": len(self.manifest["clusters"]),
                "planned_arm_units": len(self.units),
            },
        )

    def record(self, value: Mapping[str, Any]) -> None:
        unit = dict(value)
        index = int(unit["unit_index"])
        if self.units[index] is not None:
            raise ValueError("V26 comparison atomic unit ledger already has this unit")
        self.units[index] = unit
        _atomic_write_json(self.output_dir / "units" / f"{index:03d}.json", unit)

    def write_preflight(self, cluster_index: int, value: Mapping[str, Any]) -> None:
        _atomic_write_json(self.output_dir / "preflight" / f"{cluster_index:03d}.json", value)

    def mark_model_phase(self) -> None:
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {
                "evidence_role": COMPARISON_EVIDENCE_ROLE,
                "status": "running_same_ego_b8_comparison",
                "planned_clusters": len(self.manifest["clusters"]),
                "planned_arm_units": len(self.units),
            },
        )

    def finalize(self, *, terminal_error: str | None) -> Path:
        clusters = list(self.manifest["clusters"])
        plan = list(self.manifest["unit_plan"])
        for index, value in enumerate(self.units):
            if value is None:
                self.record(_unattempted_unit(unit=plan[index], cluster=clusters[int(plan[index]["cluster_index"])]))
        units = [value for value in self.units if value is not None]
        complete = sum(row["terminal"]["status"] == "complete" for row in units)
        failed = sum(row["terminal"]["status"] == "typed_failure" for row in units)
        unattempted = sum(row["terminal"]["status"] == "unattempted" for row in units)
        cluster_rows = []
        for cluster in clusters:
            rows = [row for row in units if row["cluster_index"] == cluster["cluster_index"]]
            statuses = [row["terminal"]["status"] for row in rows]
            cluster_rows.append(
                {
                    "cluster_index": cluster["cluster_index"],
                    "cluster_id_sha256": cluster["cluster_id_sha256"],
                    "terminal": (
                        "complete" if statuses == ["complete"] * len(COMPARISON_ARMS)
                        else "typed_failure" if "typed_failure" in statuses else "unattempted"
                    ),
                }
            )
        family_counts = Counter(str(row["route"]["family_id"]) for row in units)
        receipt = {
            "schema_version": COMPARISON_RECEIPT_SCHEMA_VERSION,
            "evidence_role": COMPARISON_EVIDENCE_ROLE,
            "status": "terminal_development_comparison_no_claim",
            "manifest_sha256": self.manifest["manifest_sha256"],
            "denominator": {
                "planned_clusters": len(clusters),
                "complete_clusters": sum(row["terminal"] == "complete" for row in cluster_rows),
                "typed_failure_clusters": sum(row["terminal"] == "typed_failure" for row in cluster_rows),
                "unattempted_clusters": sum(row["terminal"] == "unattempted" for row in cluster_rows),
                "planned_arm_units": len(units),
                "complete_arm_units": complete,
                "typed_failure_arm_units": failed,
                "unattempted_arm_units": unattempted,
            },
            "identity": {
                "family_counts_by_arm_unit": dict(sorted(family_counts.items())),
                "cluster_ids_exact_once": len({row["cluster_id_sha256"] for row in cluster_rows}) == len(cluster_rows),
                "arm_unit_indices_exact_once": sorted(int(row["unit_index"]) for row in units) == list(range(len(units))),
                "arms": list(COMPARISON_ARMS),
            },
            "endpoint_contract": dict(self.manifest["endpoint_contract"]),
            "legacy_safetycost_consumed": False,
            "terminal_error": terminal_error,
            "cluster_terminal": cluster_rows,
        }
        _atomic_write_json(self.output_dir / "raw_receipt.json", receipt)
        _atomic_write_json(
            self.output_dir / "summary.json",
            {
                "evidence_role": COMPARISON_EVIDENCE_ROLE,
                "denominator": dict(receipt["denominator"]),
                "identity": dict(receipt["identity"]),
                "claim_scope": self.manifest["claim_scope"],
            },
        )
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {
                "evidence_role": COMPARISON_EVIDENCE_ROLE,
                "status": "terminal",
                "denominator": dict(receipt["denominator"]),
                "terminal_error": terminal_error,
            },
        )
        (self.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        return self.output_dir / "raw_receipt.json"


def _prepare_cluster(
    *,
    cluster: Mapping[str, Any],
    output_dir: Path,
    route_type: Any,
    builder_type: Any,
    family_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    schedule = _schedule(cluster)
    record = dict(schedule["route_record"])
    source_binding = v26_source_inventory_binding(
        Path(record["source_map_path"]), str(record["source_map_sha256"])
    )
    projection = dict(source_binding["source_projection"])
    with v26_source_bound_projection(projection):
        builder = builder_type(str(record["source_map_path"]))
        require_v26_route_connectivity(builder, record["lanelet_ids"])
        geometry = v26_route_geometry_receipt(
            builder, record["lanelet_ids"], projection
        )
        route_path = output_dir / "route_assets" / f"{int(cluster['cluster_index']):03d}.pkl"
        route_sha256 = _route_asset(route_type, record, route_path)
        if geometry["derived_geometry_sha256"] != record["source_geometry_sha256"]:
            raise ValueError("V26 comparison route geometry drifted from frozen inventory")
        signal = build_v26_source_signal_config(
            schedule=schedule,
            family=family_by_id[str(schedule["family_id"])],
            route_sha256=route_sha256,
            source_inventory_binding=source_binding,
        )
        probe = {
            "routes": [{"path": str(route_path), "sha256": route_sha256}],
            "map": {"path": record["source_map_path"], "sha256": record["source_map_sha256"]},
            **dict(signal),
        }
        signal_binding = resolve_v26_signal_adapter(probe)
        signal_binding.adapter.bind_builder(builder)
        signal_binding.adapter.bind_runtime_lanelet_ids(
            route_lanelet_ids=record["lanelet_ids"], map_lanelet_ids=record["lanelet_ids"]
        )
        if signal_binding.mode == V26_SOURCE_TRAFFIC_SIGNAL_MODE:
            validate_v26_source_map_signal_binding(
                signal_binding.receipt,
                route_sha256=route_sha256,
                map_sha256=record["source_map_sha256"],
                route_geometry_sha256=record["source_geometry_sha256"],
                source_projection_sha256=projection["projection_sha256"],
                source_inventory_sha256=source_binding["source_inventory"]["inventory_sha256"],
            )
    return {
        "schedule": schedule,
        "projection": projection,
        "source_inventory": dict(source_binding["source_inventory"]),
        "route_path": route_path,
        "route_sha256": route_sha256,
        "geometry": geometry,
        "signal": signal,
        "signal_adapter_id": signal_binding.adapter_id,
    }


def run(args: argparse.Namespace) -> Path:
    output_dir = args.output_dir.resolve()
    inventory_path = args.inventory.resolve()
    if not inventory_path.is_file():
        raise FileNotFoundError(inventory_path)
    inventory = validate_development_comparison_inventory(
        json.loads(inventory_path.read_text(encoding="utf-8"))
    )
    if _sha256_file(inventory_path) != args.expected_inventory_file_sha256:
        raise ValueError("V26 comparison inventory file SHA drifted")
    if _tracked_changes(ROOT) or _git_head(ROOT) != args.expected_camp_head:
        raise ValueError("V26 comparison requires an exact clean CAMP checkout")
    fixed_dp_repo = args.fixed_dp_repo.resolve()
    if _tracked_changes(fixed_dp_repo):
        raise ValueError("V26 comparison requires an exact clean fixed-DP checkout")
    base = _load_base_probe_config(args.base_probe_config)
    if base["fixed_dp"]["head"] != inventory["fixed_dp"]["head"]:
        raise ValueError("V26 comparison fixed-DP identity drifted")
    if _git_head(fixed_dp_repo) != inventory["fixed_dp"]["head"]:
        raise ValueError("V26 comparison fixed-DP checkout head drifted")
    adapted = load_v26_adapted_selector_assets(args.adaptation_receipt)
    manifest = build_development_comparison_manifest(
        inventory=inventory,
        inventory_file_sha256=_sha256_file(inventory_path),
        camp_head=args.expected_camp_head,
        base_probe=base,
        adapted_assets=adapted,
    )
    with _exclusive_worker_lock(args.worker_lock.resolve()):
        ledger = _Ledger(output_dir=output_dir, manifest=manifest)
        for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        enforce_v26_dp312_lanelet2_precedence()
        from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder  # noqa: PLC0415
        from scenario_generation.route import Route  # noqa: PLC0415

        family_by_id = {
            str(item["family_id"]): dict(item) for item in inventory["source_families"]
        }
        prepared: dict[int, dict[str, Any]] = {}
        terminal_error: str | None = None
        active_unit: Mapping[str, Any] | None = None
        try:
            for cluster in manifest["clusters"]:
                index = int(cluster["cluster_index"])
                try:
                    prepared[index] = _prepare_cluster(
                        cluster=cluster,
                        output_dir=output_dir,
                        route_type=Route,
                        builder_type=LaneletSceneBuilder,
                        family_by_id=family_by_id,
                    )
                    ledger.write_preflight(
                        index,
                        {
                            "cluster_index": index,
                            "cluster_id_sha256": cluster["cluster_id_sha256"],
                            "status": "passed_v26_native_source_preflight",
                            "route_asset_sha256": prepared[index]["route_sha256"],
                            "source_projection_sha256": prepared[index]["projection"]["projection_sha256"],
                            "source_inventory_sha256": prepared[index]["source_inventory"]["inventory_sha256"],
                            "parsed_geometry_sha256": prepared[index]["geometry"]["derived_geometry_sha256"],
                            "signal_adapter_id": prepared[index]["signal_adapter_id"],
                            "model_dp_gpu_latent_candidate_calls": {
                                "model_forward_count": 0,
                                "dp_forward_count": 0,
                                "gpu_invocation_count": 0,
                                "latent_generation_count": 0,
                                "candidate_generation_count": 0,
                                "sequential_forward_count": 0,
                            },
                        },
                    )
                except Exception as exc:
                    ledger.write_preflight(
                        index,
                        {
                            "cluster_index": index,
                            "cluster_id_sha256": cluster["cluster_id_sha256"],
                            "status": "typed_failure",
                            "failure_class": type(exc).__name__,
                            "failure_reason": str(exc),
                            "model_dp_gpu_latent_candidate_calls": {
                                "model_forward_count": 0,
                                "dp_forward_count": 0,
                                "gpu_invocation_count": 0,
                                "latent_generation_count": 0,
                                "candidate_generation_count": 0,
                                "sequential_forward_count": 0,
                            },
                        },
                    )
                    for unit in (
                        row for row in manifest["unit_plan"] if int(row["cluster_index"]) == index
                    ):
                        ledger.record(
                            _failure_unit(
                                unit=unit,
                                cluster=cluster,
                                failure_class=type(exc).__name__,
                                failure_reason=str(exc),
                            )
                        )
            if len(prepared) != len(manifest["clusters"]):
                return ledger.finalize(
                    terminal_error="pre_model_qualification_failed_no_model_initialized"
                )
            import torch  # noqa: PLC0415

            _resource_precheck(output_dir, args.device, torch)
            from camp_core.integrations.diffusion_planner import (  # noqa: PLC0415
                install_lanelet2_projection_fallback,
                require_source_preserving_lanelet2_regulatory_adapter,
            )
            from scripts.integrations.run_diffusion_planner_camp_replay import _load_model  # noqa: PLC0415
            from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: PLC0415
                _install_fixed_dp_annotation_compatibility,
            )
            import scenario_generation.replay as replay  # noqa: PLC0415
            import scenario_generation.tensor_converter as tensor_converter  # noqa: PLC0415

            # All route/source checks above happened before this fixed-DP model load.
            first = prepared[min(prepared)]
            require_source_preserving_lanelet2_regulatory_adapter(
                Path(first["schedule"]["route_record"]["source_map_path"])
            )
            install_lanelet2_projection_fallback(
                Path(first["schedule"]["route_record"]["source_map_path"])
            )
            _install_fixed_dp_annotation_compatibility(fixed_dp_repo)
            model, model_args = _load_model(
                Path(base["fixed_dp"]["checkpoint"]["path"]),
                Path(base["fixed_dp"]["args_json"]["path"]),
                args.device,
            )
            model.eval()
            ledger.mark_model_phase()
            clusters = {int(row["cluster_index"]): row for row in manifest["clusters"]}
            for unit in manifest["unit_plan"]:
                active_unit = unit
                cluster = clusters[int(unit["cluster_index"])]
                item = prepared[int(unit["cluster_index"])]
                config = _route_probe_config(
                    base=base,
                    schedule=item["schedule"],
                    route_path=item["route_path"],
                    route_sha256=item["route_sha256"],
                    scenario_seed=int(unit["scenario_seed"]),
                    signal=item["signal"],
                )
                config["source_projection"] = dict(item["projection"])
                signal = resolve_v26_signal_adapter(config)
                callback_box: dict[str, Any] = {}

                def on_completed(raw: Mapping[str, Any], callback: Any) -> None:
                    callback_box["callback"] = callback
                    ledger.record(_runtime_unit(raw=raw, callback=callback, unit=unit, cluster=cluster))

                with v26_source_bound_projection(item["projection"]):
                    receipts, callback, native_result = run_v26_native_same_ego_b8_replay(
                        config=config,
                        model=model,
                        model_args=model_args,
                        tensor_converter=tensor_converter,
                        replay=replay,
                        builder_type=LaneletSceneBuilder,
                        route_type=Route,
                        fixed_dp_repo=fixed_dp_repo,
                        selector_assets=adapted,
                        signal_adapter=signal.adapter,
                        integration_boundary=build_v26_adapted_comparison_integration_boundary(
                            signal=signal,
                            reference_manifest_sha256=adapted.reference_manifest_sha256,
                            adaptation_receipt_sha256=adapted.adaptation_receipt_sha256,
                            adapted_asset_manifest_sha256=adapted.asset_manifest_sha256,
                        ),
                        device=args.device,
                        max_ticks=1,
                        scratch_parent=output_dir.parent,
                        on_completed_unit=on_completed,
                        selector_arms=_selector_subset(str(unit["arm_id"])),
                        operational_arm=RUNTIME_ARM_BY_COMPARISON_ARM[str(unit["arm_id"])],
                    )
                if ledger.units[int(unit["unit_index"])] is None:
                    raw = receipts[0] if receipts else None
                    ledger.record(
                        _failure_unit(
                            unit=unit,
                            cluster=cluster,
                            failure_class=str(native_result.get("failure_class", "NativeReplayFailure")),
                            failure_reason=str(
                                native_result.get(
                                    "failure_reason", native_result.get("reason", "no_terminal_receipt")
                                )
                            ),
                            raw=raw,
                            callback=callback,
                        )
                    )
        except Exception as exc:
            terminal_error = f"{type(exc).__name__}: {exc}"
            if active_unit is not None and ledger.units[int(active_unit["unit_index"])] is None:
                cluster = manifest["clusters"][int(active_unit["cluster_index"])]
                ledger.record(
                    _failure_unit(
                        unit=active_unit,
                        cluster=cluster,
                        failure_class="ParentExecutionException",
                        failure_reason=terminal_error,
                    )
                )
        return ledger.finalize(terminal_error=terminal_error)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--worker-lock", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--expected-inventory-file-sha256", required=True)
    parser.add_argument("--adaptation-receipt", type=Path, required=True)
    parser.add_argument("--base-probe-config", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--expected-camp-head", required=True)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    receipt = run(parse_args(argv))
    print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
