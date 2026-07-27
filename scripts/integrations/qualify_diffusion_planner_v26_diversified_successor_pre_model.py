"""Zero-model qualification for the exact V26 Stage8b continuation tail.

This path qualifies only revised-plan ordinals 485..1782.  It consumes route,
map, signal, and frozen reference-schema authority, never parent candidate or
training artifacts, and never constructs a model, DP forward, latent, or GPU
workload.
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
from typing import Any, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v25_scene_runtime import FIXED_DP_HEAD  # noqa: E402
from camp_core.integrations.diffusion_planner_v26_diversified_route_plan import (  # noqa: E402
    canonical_json_sha256,
)
from camp_core.integrations.diffusion_planner_v26_diversified_successor import (  # noqa: E402
    SUCCESSOR_COUNT,
    SUCCESSOR_END,
    SUCCESSOR_PLAN_EVIDENCE_ROLE,
    SUCCESSOR_PLAN_SCHEMA_VERSION,
    SUCCESSOR_START,
    load_verified_successor_plan,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (  # noqa: E402
    enforce_v26_dp312_lanelet2_precedence,
    resolve_v26_signal_adapter,
    v26_generator_topology,
)
from camp_core.integrations.diffusion_planner_v26_source_authority import (  # noqa: E402
    build_v26_source_signal_config,
    require_v26_route_connectivity,
    v26_route_geometry_receipt,
    v26_source_bound_projection,
    v26_source_projection_binding,
)
from scripts.integrations.run_diffusion_planner_v26_development_profiling import (  # noqa: E402
    _load_zero_shot_reference_selector_assets,
)
from scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition import (  # noqa: E402
    _load_base_probe_config,
    _route_asset,
)


EVIDENCE_ROLE = "development_training_same_ego_b8_successor_pre_model_qualification"
MANIFEST_SCHEMA_VERSION = "camp_dp_v26_stage8b_successor_pre_model_qualification_manifest_v1"
UNIT_SCHEMA_VERSION = "camp_dp_v26_stage8b_successor_pre_model_qualification_unit_v1"
RECEIPT_SCHEMA_VERSION = "camp_dp_v26_stage8b_successor_pre_model_qualification_receipt_v1"
BOUNDARY_DIAGNOSTIC_SCHEMA_VERSION = "camp_dp_v26_stage8b_successor_boundary_diagnostic_v1"


def _file_sha256(path: Path) -> str:
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
    staging = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        staging.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"V26 successor qualification lock already exists: {path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "role": EVIDENCE_ROLE}, handle)
            handle.flush()
        yield
    finally:
        path.unlink(missing_ok=True)


def _zero_calls() -> dict[str, int]:
    return {
        "model_forward_count": 0,
        "dp_forward_count": 0,
        "gpu_invocation_count": 0,
        "latent_generation_count": 0,
        "candidate_generation_count": 0,
        "sequential_forward_count": 0,
    }


def _unit_identity(*, plan_sha256: str, ordinal: int, schedule: Mapping[str, Any]) -> str:
    return canonical_json_sha256(
        {
            "route_plan_sha256": plan_sha256,
            "revised_plan_ordinal": ordinal,
            "route_id": schedule["route_id"],
            "route_identity_sha256": schedule["route_record"]["identity_sha256"],
            "evidence_role": EVIDENCE_ROLE,
        }
    )


def _probe_config(
    *, route_path: Path, route_sha256: str, schedule: Mapping[str, Any], signal: Mapping[str, Any]
) -> dict[str, Any]:
    record = dict(schedule["route_record"])
    return {
        "routes": [{"path": str(route_path), "sha256": route_sha256}],
        "map": {"path": record["source_map_path"], "sha256": record["source_map_sha256"]},
        **dict(signal),
    }


def _route_projection(schedule: Mapping[str, Any]) -> dict[str, Any]:
    record = dict(schedule["route_record"])
    return {
        "revised_plan_ordinal": int(schedule["revised_plan_ordinal"]),
        "family_id": schedule["family_id"],
        "route_id": schedule["route_id"],
        "corridor_id": schedule["corridor_id"],
        "parent_ordinal": int(schedule["parent_ordinal"]),
        "scenario_seed": int(schedule["scenario_seed"]),
        "source_artifact_sha256": schedule["source_artifact_sha256"],
        "event_manifest_sha256": schedule["event_manifest_sha256"],
        "route_identity_sha256": record["identity_sha256"],
        "source_map_sha256": record["source_map_sha256"],
        "source_geometry_sha256": record["source_geometry_sha256"],
        "route_lanelet_ids": list(record["lanelet_ids"]),
        "source_stratum": dict(record["source_stratum"]),
    }


def _qualified_unit(
    *,
    ordinal: int,
    plan_sha256: str,
    schedule: Mapping[str, Any],
    route_sha256: str,
    projection: Mapping[str, Any],
    geometry: Mapping[str, Any],
    signal: Mapping[str, Any],
    signal_binding: Any,
    scene_reference: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "unit_index": ordinal,
        "revised_plan_ordinal": ordinal,
        "unit_identity_sha256": _unit_identity(
            plan_sha256=plan_sha256, ordinal=ordinal, schedule=schedule
        ),
        "route": _route_projection(schedule),
        "route_asset_sha256": route_sha256,
        "source_projection": dict(projection),
        "parsed_geometry": dict(geometry),
        "signal": {
            "mode": signal["signal_authority_mode"],
            "adapter_id": signal_binding.adapter_id,
            "source_provenance": dict(signal["source_signal_authority"]),
            "adapter_binding": dict(signal_binding.receipt),
        },
        "scene14d_reference": dict(scene_reference),
        "scene_payload": {
            "schema_scaler_tolerance_verified": True,
            "runtime_payload_materialized": False,
            "reason": "pre_model_qualification_does_not_impute_current_state_or_candidates",
        },
        "generator_topology": v26_generator_topology(),
        "forward_calls": _zero_calls(),
        "terminal": {"status": "qualified", "failure_class": None, "failure_reason": None},
    }


def _failed_unit(
    *, ordinal: int, plan_sha256: str, schedule: Mapping[str, Any], exc: Exception
) -> dict[str, Any]:
    return {
        "schema_version": UNIT_SCHEMA_VERSION,
        "unit_index": ordinal,
        "revised_plan_ordinal": ordinal,
        "unit_identity_sha256": _unit_identity(
            plan_sha256=plan_sha256, ordinal=ordinal, schedule=schedule
        ),
        "route": _route_projection(schedule),
        "forward_calls": _zero_calls(),
        "terminal": {
            "status": "failed",
            "failure_class": type(exc).__name__,
            "failure_reason": str(exc),
        },
    }


def _boundary_diagnostic(*, unit: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    if int(unit["revised_plan_ordinal"]) != SUCCESSOR_START:
        raise ValueError("V26 successor boundary diagnostic must be ordinal 485")
    if unit["terminal"]["status"] != "qualified":
        raise ValueError("V26 successor boundary diagnostic requires a qualified ordinal 485")
    return {
        "schema_version": BOUNDARY_DIAGNOSTIC_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "successor_plan_sha256": plan["route_plan_sha256"],
        "parent_revised_plan_sha256": plan["parent_revised_plan"]["route_plan_sha256"],
        "revised_plan_ordinal": SUCCESSOR_START,
        "route": dict(unit["route"]),
        "route_asset_sha256": unit["route_asset_sha256"],
        "source_projection": dict(unit["source_projection"]),
        "parsed_geometry": dict(unit["parsed_geometry"]),
        "signal": dict(unit["signal"]),
        "scene14d_reference": dict(unit["scene14d_reference"]),
        "generator_topology": dict(unit["generator_topology"]),
        "forward_calls": dict(unit["forward_calls"]),
        "terminal": dict(unit["terminal"]),
        "full_atomic_unit_capture": True,
    }


def _aggregate(
    *, manifest: Mapping[str, Any], units: Sequence[Mapping[str, Any]], terminal_error: str | None
) -> dict[str, Any]:
    planned = len(units)
    complete = sum(unit["terminal"]["status"] == "qualified" for unit in units)
    failed = sum(unit["terminal"]["status"] == "failed" for unit in units)
    unattempted = planned - complete - failed
    route_ids = [str(unit["route"]["route_id"]) for unit in units]
    ordinals = [int(unit["revised_plan_ordinal"]) for unit in units]
    valid = (
        planned == SUCCESSOR_COUNT
        and complete == SUCCESSOR_COUNT
        and failed == 0
        and unattempted == 0
        and len(set(route_ids)) == planned
        and sorted(ordinals) == list(range(SUCCESSOR_START, SUCCESSOR_END + 1))
        and terminal_error is None
    )
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "status": "passed" if valid else "failed",
        "manifest_sha256": canonical_json_sha256(dict(manifest)),
        "successor_plan_sha256": manifest["successor_plan_sha256"],
        "parent_revised_plan_sha256": manifest["parent_revised_plan_sha256"],
        "denominator": {
            "planned": planned,
            "complete": complete,
            "failed": failed,
            "unattempted": unattempted,
        },
        "identity": {
            "family_count": len({unit["route"]["family_id"] for unit in units}),
            "corridor_count": len({unit["route"]["corridor_id"] for unit in units}),
            "route_count": len(set(route_ids)),
            "revised_plan_ordinal_interval": [SUCCESSOR_START, SUCCESSOR_END],
        },
        "zero_model_totals": _zero_calls(),
        "terminal_error": terminal_error,
        "acquisition_authorized": valid,
    }


def run(args: argparse.Namespace) -> Path:
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"V26 successor qualification output already exists: {output_dir}")
    authority = load_verified_successor_plan(
        successor_plan_path=args.successor_plan,
        parent_revised_plan_path=args.parent_revised_plan,
        parent_recovered_root=args.parent_recovered_root,
    )
    route_plan = authority["route_plan"]
    if (
        route_plan["schema_version"] != SUCCESSOR_PLAN_SCHEMA_VERSION
        or route_plan["evidence_role"] != SUCCESSOR_PLAN_EVIDENCE_ROLE
        or route_plan["route_plan_sha256"] != args.expected_successor_plan_sha256
        or route_plan["fixed_dp_head"] != FIXED_DP_HEAD
    ):
        raise ValueError("V26 successor qualification plan identity drifted")
    if _tracked_changes(ROOT) or _git_head(ROOT) != args.expected_camp_head:
        raise ValueError("V26 successor qualification requires an exact clean CAMP checkout")
    fixed_dp_repo = args.fixed_dp_repo.resolve()
    if _tracked_changes(fixed_dp_repo) or _git_head(fixed_dp_repo) != FIXED_DP_HEAD:
        raise ValueError("V26 successor qualification requires an exact clean fixed-DP checkout")
    base = _load_base_probe_config(args.base_probe_config)
    assets = _load_zero_shot_reference_selector_assets(args)
    scene_reference = assets.scene14d_adapter.reference_contract()
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "camp_head": args.expected_camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "successor_plan_path": str(args.successor_plan.resolve()),
        "successor_plan_sha256": route_plan["route_plan_sha256"],
        "parent_revised_plan_sha256": route_plan["parent_revised_plan"]["route_plan_sha256"],
        "parent_recovered_root": route_plan["parent_recovered_root"],
        "base_probe": base,
        "scene14d_reference": scene_reference,
        "generator_topology": v26_generator_topology(),
        "zero_model_contract": _zero_calls(),
        "revised_plan_ordinal_interval": [SUCCESSOR_START, SUCCESSOR_END],
        "parent_candidates_labels_training_rows_consumed": False,
    }
    units: dict[int, dict[str, Any] | None] = {
        int(schedule["revised_plan_ordinal"]): None for schedule in route_plan["routes"]
    }
    family_by_id = {
        str(row["family_id"]): dict(row) for row in route_plan["family_projections"]
    }
    terminal_error: str | None = None
    with _exclusive_lock(args.qualification_lock.resolve()):
        output_dir.mkdir(parents=True, exist_ok=False)
        _atomic_write_json(output_dir / "manifest.json", manifest)
        for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        enforce_v26_dp312_lanelet2_precedence()
        from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder  # noqa: PLC0415
        from scenario_generation.route import Route  # noqa: PLC0415

        grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for schedule in route_plan["routes"]:
            record = dict(schedule["route_record"])
            grouped.setdefault(
                (str(record["source_map_path"]), str(record["source_map_sha256"])), []
            ).append(schedule)
        for (map_path, map_sha256), schedules in grouped.items():
            try:
                projection = v26_source_projection_binding(Path(map_path), map_sha256)
                with v26_source_bound_projection(projection):
                    builder = LaneletSceneBuilder(map_path)
                    for schedule in schedules:
                        ordinal = int(schedule["revised_plan_ordinal"])
                        try:
                            record = dict(schedule["route_record"])
                            route_path = output_dir / "route_assets" / f"{ordinal:04d}.pkl"
                            route_sha256 = _route_asset(Route, record, route_path)
                            require_v26_route_connectivity(builder, record["lanelet_ids"])
                            geometry = v26_route_geometry_receipt(
                                builder, record["lanelet_ids"], projection
                            )
                            signal = build_v26_source_signal_config(
                                schedule=schedule,
                                family=family_by_id[str(schedule["family_id"])],
                                route_sha256=route_sha256,
                            )
                            binding = resolve_v26_signal_adapter(
                                _probe_config(
                                    route_path=route_path,
                                    route_sha256=route_sha256,
                                    schedule=schedule,
                                    signal=signal,
                                )
                            )
                            binding.adapter.bind_builder(builder)
                            binding.adapter.bind_runtime_lanelet_ids(
                                route_lanelet_ids=record["lanelet_ids"],
                                map_lanelet_ids=record["lanelet_ids"],
                            )
                            unit = _qualified_unit(
                                ordinal=ordinal,
                                plan_sha256=route_plan["route_plan_sha256"],
                                schedule=schedule,
                                route_sha256=route_sha256,
                                projection=projection,
                                geometry=geometry,
                                signal=signal,
                                signal_binding=binding,
                                scene_reference=scene_reference,
                            )
                        except Exception as exc:  # atomic typed per-route failure
                            unit = _failed_unit(
                                ordinal=ordinal,
                                plan_sha256=route_plan["route_plan_sha256"],
                                schedule=schedule,
                                exc=exc,
                            )
                        units[ordinal] = unit
                        unit_path = output_dir / "units" / f"{ordinal:04d}.json"
                        _atomic_write_json(unit_path, unit)
                        if ordinal == SUCCESSOR_START and unit["terminal"]["status"] == "qualified":
                            diagnostic = _boundary_diagnostic(unit=unit, plan=route_plan)
                            diagnostic["atomic_unit_path"] = str(unit_path)
                            diagnostic["atomic_unit_sha256"] = _file_sha256(unit_path)
                            _atomic_write_json(
                                output_dir / "boundary_diagnostics" / f"{ordinal:04d}.json",
                                diagnostic,
                            )
            except Exception as exc:
                for schedule in schedules:
                    ordinal = int(schedule["revised_plan_ordinal"])
                    unit = _failed_unit(
                        ordinal=ordinal,
                        plan_sha256=route_plan["route_plan_sha256"],
                        schedule=schedule,
                        exc=exc,
                    )
                    units[ordinal] = unit
                    _atomic_write_json(output_dir / "units" / f"{ordinal:04d}.json", unit)
        finalized = [unit for unit in units.values() if unit is not None]
        if len(finalized) != SUCCESSOR_COUNT:
            terminal_error = "qualification left an unattempted successor route"
            for schedule in route_plan["routes"]:
                ordinal = int(schedule["revised_plan_ordinal"])
                if units[ordinal] is None:
                    failed = _failed_unit(
                        ordinal=ordinal,
                        plan_sha256=route_plan["route_plan_sha256"],
                        schedule=schedule,
                        exc=RuntimeError(terminal_error),
                    )
                    units[ordinal] = failed
                    _atomic_write_json(output_dir / "units" / f"{ordinal:04d}.json", failed)
            finalized = [unit for unit in units.values() if unit is not None]
        ordered = [units[ordinal] for ordinal in range(SUCCESSOR_START, SUCCESSOR_END + 1)]
        receipt = _aggregate(
            manifest=manifest, units=[unit for unit in ordered if unit is not None], terminal_error=terminal_error
        )
        _atomic_write_json(output_dir / "raw_receipt.json", receipt)
        _atomic_write_json(
            output_dir / "run.status.json",
            {"status": receipt["status"], "receipt": str(output_dir / "raw_receipt.json")},
        )
        (output_dir / "run.exit").write_text(
            "0\n" if receipt["status"] == "passed" else "1\n", encoding="utf-8"
        )
        return output_dir / "raw_receipt.json"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--qualification-lock", type=Path, required=True)
    parser.add_argument("--successor-plan", type=Path, required=True)
    parser.add_argument("--parent-revised-plan", type=Path, required=True)
    parser.add_argument("--parent-recovered-root", type=Path, required=True)
    parser.add_argument("--expected-successor-plan-sha256", required=True)
    parser.add_argument("--base-probe-config", type=Path, required=True)
    parser.add_argument("--reference-weights", type=Path, required=True)
    parser.add_argument("--reference-weights-root", required=True)
    parser.add_argument("--reference-weights-review", type=Path, required=True)
    parser.add_argument("--reference-weights-review-root", required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--expected-camp-head", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    print(run(parse_args(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
