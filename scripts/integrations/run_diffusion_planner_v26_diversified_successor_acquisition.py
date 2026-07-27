"""Acquire only the untouched V26 Stage8b successor ordinals 485..1782.

This is a continuation identity, never a rerun: the immutable parent root
contributes ordinals 0..484, while this runner owns only the previously
unattempted interval.  It uses one same-ego B8 forward per attempted route and
records an atomic typed boundary if a parent-level exception stops the worker.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v25_scene_runtime import FIXED_DP_HEAD  # noqa: E402
from camp_core.integrations.diffusion_planner_v26_diversified_successor import (  # noqa: E402
    SUCCESSOR_COUNT,
    SUCCESSOR_END,
    SUCCESSOR_START,
    load_verified_successor_plan,
    materialize_immutable_union_manifest,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (  # noqa: E402
    FROZEN_SIMPLEX_TOLERANCE,
    V26_GENERATOR_ID,
    V26_TRAINING_ROWS_SCHEMA_VERSION,
    V26_TRAINING_SOURCE_SCHEMA_VERSION,
    build_v26_integration_boundary,
    enforce_v26_dp312_lanelet2_precedence,
    v26_generator_topology,
)
from camp_core.integrations.diffusion_planner_v26_native_runner import (  # noqa: E402
    run_v26_native_same_ego_b8_replay,
)
from camp_core.integrations.diffusion_planner_v26_source_authority import (  # noqa: E402
    v26_source_bound_projection,
)
from scripts.integrations.run_diffusion_planner_v26_development_profiling import (  # noqa: E402
    _load_zero_shot_reference_selector_assets,
)
from scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition import (  # noqa: E402
    EVIDENCE_ROLE as PARENT_EVIDENCE_ROLE,
    LABEL_SIDECAR_SCHEMA_VERSION,
    SCENARIO_SEED_BASE,
    _AcquisitionLedger,
    _atomic_write_json,
    _completed_unit,
    _exclusive_worker_lock,
    _file_sha256,
    _git_head,
    _load_base_probe_config,
    _prepare_route,
    _resource_precheck,
    _source_ordinal,
    _tracked_changes,
    _typed_failure_unit,
    _unattempted_unit,
)


EVIDENCE_ROLE = "development_training_same_ego_b8_successor_acquisition"
MANIFEST_SCHEMA_VERSION = "camp_dp_v26_diversified_successor_acquisition_manifest_v1"
RECEIPT_SCHEMA_VERSION = "camp_dp_v26_diversified_successor_acquisition_receipt_v1"


class _SuccessorLedger:
    """Atomic ledger indexed by original revised-plan ordinal, not a local tail index."""

    def __init__(self, *, output_dir: Path, manifest: Mapping[str, Any], route_plan: Mapping[str, Any]) -> None:
        self.output_dir = output_dir.resolve()
        if self.output_dir.exists():
            raise FileExistsError(f"V26 successor acquisition output already exists: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.manifest = dict(manifest)
        self.route_plan = dict(route_plan)
        self.schedules = {
            int(schedule["revised_plan_ordinal"]): dict(schedule)
            for schedule in self.route_plan["routes"]
        }
        if sorted(self.schedules) != list(range(SUCCESSOR_START, SUCCESSOR_END + 1)):
            raise ValueError("V26 successor ledger ordinal interval drifted")
        self.units: dict[int, dict[str, Any] | None] = {ordinal: None for ordinal in self.schedules}
        _atomic_write_json(self.output_dir / "manifest.json", self.manifest)
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {
                "evidence_role": EVIDENCE_ROLE,
                "status": "running",
                "planned": SUCCESSOR_COUNT,
                "revised_plan_ordinal_interval": [SUCCESSOR_START, SUCCESSOR_END],
            },
        )

    def record(self, unit: Mapping[str, Any]) -> None:
        ordinal = int(unit["unit_index"])
        if ordinal not in self.units or self.units[ordinal] is not None:
            raise ValueError("V26 successor unit ledger ordinal is invalid or already recorded")
        materialized = dict(unit)
        if materialized["route"].get("revised_plan_ordinal") != ordinal:
            raise ValueError("V26 successor unit receipt ordinal binding drifted")
        self.units[ordinal] = materialized
        _atomic_write_json(self.output_dir / "units" / f"{ordinal:04d}.json", materialized)

    def record_parent_exception_boundary(
        self,
        *,
        ordinal: int,
        schedule: Mapping[str, Any],
        scenario_seed: int,
        phase: str,
        exc: Exception,
        callback: Any | None = None,
        raw: Mapping[str, Any] | None = None,
    ) -> bool:
        """Persist the stopping route before marking later work unattempted."""

        if ordinal not in self.units:
            raise ValueError("V26 successor parent-exception boundary ordinal drifted")
        if self.units[ordinal] is not None:
            return False
        unit = _typed_failure_unit(
            unit_index=ordinal,
            route_plan_sha256=self.route_plan["route_plan_sha256"],
            schedule=schedule,
            scenario_seed=scenario_seed,
            failure_class="ParentExecutionException",
            failure_reason=f"{type(exc).__name__}: {exc}",
            callback=callback,
            raw=raw,
        )
        unit["parent_exception_boundary"] = {
            "phase": str(phase),
            "exception_class": type(exc).__name__,
            "exception_message": str(exc),
            "revised_plan_ordinal": ordinal,
        }
        self.record(unit)
        return True

    def finalize(self, *, terminal_error: str | None = None) -> Path:
        plan_sha = str(self.route_plan["route_plan_sha256"])
        for ordinal, schedule in self.schedules.items():
            if self.units[ordinal] is None:
                self.record(
                    _unattempted_unit(
                        unit_index=ordinal,
                        route_plan_sha256=plan_sha,
                        schedule=schedule,
                        scenario_seed=SCENARIO_SEED_BASE + _source_ordinal(schedule, ordinal),
                    )
                )
        ordered = [self.units[ordinal] for ordinal in range(SUCCESSOR_START, SUCCESSOR_END + 1)]
        finalized = [unit for unit in ordered if unit is not None]
        if len(finalized) != SUCCESSOR_COUNT:
            raise AssertionError("V26 successor ledger was not fully materialized")
        complete = [unit for unit in finalized if unit["terminal"]["status"] == "complete"]
        failed = [unit for unit in finalized if unit["terminal"]["status"] == "typed_failure"]
        unattempted = [unit for unit in finalized if unit["terminal"]["status"] == "unattempted"]
        denominator = {
            "planned": SUCCESSOR_COUNT,
            "complete": len(complete),
            "failed": len(failed),
            "unattempted": len(unattempted),
        }
        rows_sha, scales_sha, label_sha = _AcquisitionLedger.write_training_artifacts_from_atomic_units(
            output_dir=self.output_dir,
            manifest=self.manifest,
            complete=complete,
        )
        report = {
            "schema_version": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "evidence_role": EVIDENCE_ROLE,
            "status": "terminal_training_evidence" if complete else "terminal_no_trainable_pools",
            "fixed_dp_head": FIXED_DP_HEAD,
            "camp_head": self.manifest["camp_head"],
            "route_plan_sha256": self.manifest["successor_plan_sha256"],
            "parent_revised_plan_sha256": self.manifest["parent_revised_plan_sha256"],
            "generator_id": V26_GENERATOR_ID,
            "generator_topology": v26_generator_topology(),
            "runner_id": "camp_dp_v26_native_same_ego_b8_successor_acquisition_runner_v1",
            "training_source_schema": V26_TRAINING_SOURCE_SCHEMA_VERSION,
            "training_rows_schema_version": V26_TRAINING_ROWS_SCHEMA_VERSION,
            "evaluation_schema": "camp_dp_v26_training_evidence_only_no_formal_evaluation_v1",
            "outcome_fields_consumed": [],
            "holdout_accessed": False,
            "parent_candidates_labels_training_rows_consumed": False,
            "source_manifest_sha256": self.manifest["successor_plan_sha256"],
            "training_rows_sha256": rows_sha,
            "training_scales_sha256": scales_sha,
            "label_sidecar_sha256": label_sha,
            "snapshot_count": len(complete),
            "candidate_count": len(complete) * 8,
            "denominator": denominator,
            "failure_denominator_complete": True,
            "terminal_error": terminal_error,
            "revised_plan_ordinal_interval": [SUCCESSOR_START, SUCCESSOR_END],
        }
        _atomic_write_json(self.output_dir / "report.json", report)
        _atomic_write_json(
            self.output_dir / "raw_receipt.json",
            {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "evidence_role": EVIDENCE_ROLE,
                "manifest_sha256": _file_sha256(self.output_dir / "manifest.json"),
                "successor_plan_sha256": self.manifest["successor_plan_sha256"],
                "parent_revised_plan_sha256": self.manifest["parent_revised_plan_sha256"],
                "denominator": denominator,
                "terminal_error": terminal_error,
            },
        )
        _atomic_write_json(
            self.output_dir / "run.status.json",
            {"evidence_role": EVIDENCE_ROLE, "status": "terminal", "denominator": denominator},
        )
        (self.output_dir / "run.exit").write_bytes(b"0\n")
        return self.output_dir / "report.json"


def _require_successor_qualification(
    *, path: Path, route_plan: Mapping[str, Any], camp_head: str
) -> dict[str, Any]:
    receipt_path = path.resolve()
    manifest_path = receipt_path.parent / "manifest.json"
    boundary_path = receipt_path.parent / "boundary_diagnostics" / f"{SUCCESSOR_START:04d}.json"
    if not receipt_path.is_file() or not manifest_path.is_file() or not boundary_path.is_file():
        raise FileNotFoundError("V26 successor qualification evidence is incomplete")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_denominator = {
        "planned": SUCCESSOR_COUNT,
        "complete": SUCCESSOR_COUNT,
        "failed": 0,
        "unattempted": 0,
    }
    if (
        receipt.get("status") != "passed"
        or receipt.get("acquisition_authorized") is not True
        or receipt.get("denominator") != expected_denominator
        or receipt.get("zero_model_totals")
        != {
            "model_forward_count": 0,
            "dp_forward_count": 0,
            "gpu_invocation_count": 0,
            "latent_generation_count": 0,
            "candidate_generation_count": 0,
            "sequential_forward_count": 0,
        }
        or receipt.get("successor_plan_sha256") != route_plan["route_plan_sha256"]
        or receipt.get("parent_revised_plan_sha256")
        != route_plan["parent_revised_plan"]["route_plan_sha256"]
        or manifest.get("camp_head") != camp_head
    ):
        raise ValueError("V26 successor pre-model qualification receipt drifted")
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    if (
        boundary.get("revised_plan_ordinal") != SUCCESSOR_START
        or boundary.get("terminal", {}).get("status") != "qualified"
        or boundary.get("forward_calls")
        != {
            "model_forward_count": 0,
            "dp_forward_count": 0,
            "gpu_invocation_count": 0,
            "latent_generation_count": 0,
            "candidate_generation_count": 0,
            "sequential_forward_count": 0,
        }
        or boundary.get("full_atomic_unit_capture") is not True
    ):
        raise ValueError("V26 successor ordinal485 boundary diagnostic drifted")
    return {
        "path": str(receipt_path),
        "sha256": _file_sha256(receipt_path),
        "manifest_sha256": _file_sha256(manifest_path),
        "boundary_diagnostic_path": str(boundary_path),
        "boundary_diagnostic_sha256": _file_sha256(boundary_path),
        "status": receipt["status"],
    }


def _manifest(
    *,
    route_plan: Mapping[str, Any],
    base: Mapping[str, Any],
    camp_head: str,
    assets: Any,
    qualification: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "evidence_role": EVIDENCE_ROLE,
        "camp_head": str(camp_head),
        "fixed_dp_head": FIXED_DP_HEAD,
        "successor_plan_schema_version": route_plan["schema_version"],
        "successor_plan_evidence_role": route_plan["evidence_role"],
        "successor_plan_sha256": route_plan["route_plan_sha256"],
        "route_plan_sha256": route_plan["route_plan_sha256"],
        "parent_revised_plan_sha256": route_plan["parent_revised_plan"]["route_plan_sha256"],
        "parent_recovered_root": route_plan["parent_recovered_root"],
        "planned_unit_count": SUCCESSOR_COUNT,
        "revised_plan_ordinal_interval": [SUCCESSOR_START, SUCCESSOR_END],
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "parent_candidates_labels_training_rows_consumed": False,
        "generator_id": V26_GENERATOR_ID,
        "generator_topology": v26_generator_topology(),
        "fixed_dp": dict(base["fixed_dp"]),
        "base_probe": {"path": base["source_path"], "sha256": base["source_sha256"]},
        "pre_model_qualification": dict(qualification),
        "selector": {
            "reference_role": "v25_zero_shot_reference_read_only",
            "reference_weights_root_sha256": assets.reference_weights_root_sha256,
            "reference_weights_review_root_sha256": assets.reference_weights_review_root_sha256,
            "atom_scales_sha256": assets.atom_scales_sha256,
            "static9d_weights_sha256": assets.static9d_weights_sha256,
            "scene9d_theta_sha256": assets.scene9d_theta_sha256,
            "static14d_weights_sha256": assets.static14d_weights_sha256,
            "scene14d_theta_sha256": assets.scene14d_theta_sha256,
            "context_scaler_sha256": assets.context_scaler_sha256,
            "simplex_nonnegative_atol": FROZEN_SIMPLEX_TOLERANCE,
        },
        "execution_topology": {
            "route_state": "fresh_own_state_per_planned_route",
            "state_ticks": 1,
            "pool_generation": "one_same_ego_b8_forward_per_unit",
            "candidate0": "frozen_row0_default_output_and_simulator_action",
            "selector": "five_same_pool_counterfactual_selectors_only",
            "post_pool_model_dp_latent_generation_mutation_regeneration": 0,
            "parent_ordinals_0_484_replayed": False,
        },
    }


def run(args: argparse.Namespace) -> Path:
    output_dir = args.output_dir.resolve()
    if output_dir.exists() or args.union_output_dir.resolve().exists():
        raise FileExistsError("V26 successor acquisition/union output already exists")
    authority = load_verified_successor_plan(
        successor_plan_path=args.successor_plan,
        parent_revised_plan_path=args.parent_revised_plan,
        parent_recovered_root=args.parent_recovered_root,
    )
    route_plan = authority["route_plan"]
    if route_plan["route_plan_sha256"] != args.expected_successor_plan_sha256:
        raise ValueError("V26 successor acquisition plan SHA drifted")
    if route_plan["fixed_dp_head"] != FIXED_DP_HEAD:
        raise ValueError("V26 successor acquisition fixed-DP identity drifted")
    if _tracked_changes(ROOT) or _git_head(ROOT) != args.expected_camp_head:
        raise ValueError("V26 successor acquisition requires an exact clean CAMP checkout")
    fixed_dp_repo = args.fixed_dp_repo.resolve()
    if _tracked_changes(fixed_dp_repo) or _git_head(fixed_dp_repo) != FIXED_DP_HEAD:
        raise ValueError("V26 successor acquisition requires an exact clean fixed-DP checkout")
    base = _load_base_probe_config(args.base_probe_config)
    assets = _load_zero_shot_reference_selector_assets(args)
    qualification = _require_successor_qualification(
        path=args.pre_model_qualification, route_plan=route_plan, camp_head=args.expected_camp_head
    )
    manifest = _manifest(
        route_plan=route_plan,
        base=base,
        camp_head=args.expected_camp_head,
        assets=assets,
        qualification=qualification,
    )
    with _exclusive_worker_lock(args.worker_lock.resolve()):
        import torch

        _resource_precheck(output_dir, args.device, torch)
        for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        enforce_v26_dp312_lanelet2_precedence()
        from scripts.integrations.run_diffusion_planner_camp_replay import _load_model  # noqa: PLC0415
        from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: PLC0415
            _install_fixed_dp_annotation_compatibility,
        )
        import scenario_generation.replay as replay  # noqa: PLC0415
        import scenario_generation.tensor_converter as tensor_converter  # noqa: PLC0415
        from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder  # noqa: PLC0415
        from scenario_generation.route import Route  # noqa: PLC0415

        ledger = _SuccessorLedger(output_dir=output_dir, manifest=manifest, route_plan=route_plan)
        prepared: dict[int, dict[str, Any]] = {}
        family_by_id = {
            str(item["family_id"]): item for item in route_plan["family_projections"]
        }
        qualified_units_root = args.pre_model_qualification.resolve().parent / "units"
        terminal_error: str | None = None
        active_boundary: tuple[int, Mapping[str, Any], int, str] | None = None
        try:
            for schedule in route_plan["routes"]:
                ordinal = int(schedule["revised_plan_ordinal"])
                source_ordinal = _source_ordinal(schedule, ordinal)
                seed = SCENARIO_SEED_BASE + source_ordinal
                active_boundary = (ordinal, schedule, seed, "pre_model_preparation")
                try:
                    qualified_path = qualified_units_root / f"{ordinal:04d}.json"
                    if not qualified_path.is_file():
                        raise FileNotFoundError(qualified_path)
                    qualified_unit = json.loads(qualified_path.read_text(encoding="utf-8"))
                    if qualified_unit.get("terminal", {}).get("status") != "qualified":
                        raise ValueError("successor qualification unit is not qualified")
                    prepared_item, failure = _prepare_route(
                        route_type=Route,
                        output_dir=output_dir,
                        unit_index=ordinal,
                        schedule=schedule,
                        family_by_id=family_by_id,
                        base=base,
                        qualified_unit=qualified_unit,
                        source_ordinal=source_ordinal,
                    )
                    if failure is not None:
                        ledger.record(
                            _typed_failure_unit(
                                unit_index=ordinal,
                                route_plan_sha256=route_plan["route_plan_sha256"],
                                schedule=schedule,
                                scenario_seed=seed,
                                failure_class="PreModelSignalAuthorityUnavailable",
                                failure_reason=failure,
                            )
                        )
                    else:
                        assert prepared_item is not None
                        prepared[ordinal] = prepared_item
                except Exception as exc:
                    ledger.record(
                        _typed_failure_unit(
                            unit_index=ordinal,
                            route_plan_sha256=route_plan["route_plan_sha256"],
                            schedule=schedule,
                            scenario_seed=seed,
                            failure_class=type(exc).__name__,
                            failure_reason=str(exc),
                        )
                    )
            if prepared:
                first_ordinal = min(prepared)
                first_schedule = next(
                    item for item in route_plan["routes"] if int(item["revised_plan_ordinal"]) == first_ordinal
                )
                active_boundary = (
                    first_ordinal,
                    first_schedule,
                    SCENARIO_SEED_BASE + _source_ordinal(first_schedule, first_ordinal),
                    "model_initialization",
                )
                _install_fixed_dp_annotation_compatibility(fixed_dp_repo)
                model, model_args = _load_model(
                    Path(base["fixed_dp"]["checkpoint"]["path"]),
                    Path(base["fixed_dp"]["args_json"]["path"]),
                    args.device,
                )
                model.eval()
                for schedule in route_plan["routes"]:
                    ordinal = int(schedule["revised_plan_ordinal"])
                    if ordinal not in prepared or ledger.units[ordinal] is not None:
                        continue
                    prepared_item = prepared[ordinal]
                    seed = int(prepared_item["scenario_seed"])
                    active_boundary = (ordinal, schedule, seed, "native_same_ego_b8_replay")
                    callback_box: dict[str, Any] = {}

                    def on_completed(raw: Mapping[str, Any], callback: Any, *, _ordinal: int = ordinal, _schedule: Mapping[str, Any] = schedule, _seed: int = seed) -> None:
                        callback_box["callback"] = callback
                        ledger.record(
                            _completed_unit(
                                raw,
                                callback,
                                unit_index=_ordinal,
                                route_plan_sha256=route_plan["route_plan_sha256"],
                                schedule=_schedule,
                                scenario_seed=_seed,
                            )
                        )

                    with v26_source_bound_projection(prepared_item["projection"]):
                        receipts, callback, native_result = run_v26_native_same_ego_b8_replay(
                            config=prepared_item["config"],
                            model=model,
                            model_args=model_args,
                            tensor_converter=tensor_converter,
                            replay=replay,
                            builder_type=LaneletSceneBuilder,
                            route_type=Route,
                            fixed_dp_repo=fixed_dp_repo,
                            selector_assets=assets,
                            signal_adapter=prepared_item["signal"].adapter,
                            integration_boundary=build_v26_integration_boundary(
                                signal=prepared_item["signal"],
                                reference_weights_root_sha256=assets.reference_weights_root_sha256,
                            ),
                            device=args.device,
                            max_ticks=1,
                            scratch_parent=output_dir.parent,
                            on_completed_unit=on_completed,
                        )
                    if ledger.units[ordinal] is None:
                        raw = receipts[0] if receipts else None
                        ledger.record(
                            _typed_failure_unit(
                                unit_index=ordinal,
                                route_plan_sha256=route_plan["route_plan_sha256"],
                                schedule=schedule,
                                scenario_seed=seed,
                                failure_class=str(native_result.get("failure_class", "NativeReplayFailure")),
                                failure_reason=str(
                                    native_result.get(
                                        "failure_reason", native_result.get("reason", "no_terminal_receipt")
                                    )
                                ),
                                callback=callback,
                                raw=raw,
                            )
                        )
        except Exception as exc:
            terminal_error = f"{type(exc).__name__}: {exc}"
            if active_boundary is not None:
                ordinal, schedule, seed, phase = active_boundary
                ledger.record_parent_exception_boundary(
                    ordinal=ordinal,
                    schedule=schedule,
                    scenario_seed=seed,
                    phase=phase,
                    exc=exc,
                )
        report = ledger.finalize(terminal_error=terminal_error)
    materialize_immutable_union_manifest(
        successor_plan_path=args.successor_plan,
        parent_revised_plan_path=args.parent_revised_plan,
        parent_recovered_root=args.parent_recovered_root,
        successor_acquisition_root=output_dir,
        output_dir=args.union_output_dir,
    )
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--union-output-dir", type=Path, required=True)
    parser.add_argument("--worker-lock", type=Path, required=True)
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
    parser.add_argument("--pre-model-qualification", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    print(run(parse_args(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
