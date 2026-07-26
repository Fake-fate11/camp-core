from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2 import (  # noqa: E402
    ARMS,
    AUTHORITY_SHA256,
    CLUSTER_COUNT,
    EXACT_DIRS,
    FIXED_DP_HEAD,
    PLANNED_TICKS,
    TICKS_PER_ARM,
    TRAINING_REVIEW_ROOT_SHA256,
    TRAINING_ROOT_SHA256,
    build_scene_adapter,
    bytes_sha256,
    canonical_bytes,
    canonical_sha256,
    latent_tensor,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
)
from scripts.integrations.run_diffusion_planner_v25_industrial_bounded_closed_loop import (  # noqa: E402
    _execution_tick,
    _post_safety_enricher,
)
from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import (  # noqa: E402
    _git_head,
    _install_fixed_dp_annotation_compatibility,
    _run_one,
    _tracked_changes,
)


AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"


def _interpreter() -> dict[str, Any]:
    if Path(sys.executable).as_posix() != AUTODL_INTERPRETER:
        raise ValueError("AutoDL execution requires frozen dp312 interpreter")
    if sys.version_info < (3, 10):
        raise ValueError("Python >=3.10 is required")
    imports = {}
    for name in ("numpy", "torch", "lanelet2"):
        module = __import__(name)
        imports[name] = str(getattr(module, "__version__", "present"))
    return {
        "sys_executable": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "sys_prefix": sys.prefix,
        "imports": imports,
    }


def _verify(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def _cluster_payload(
    *,
    cluster_index: int,
    clone_key_sha256: str,
    source_record: Mapping[str, Any],
    arms: list[dict[str, Any]],
    model_calls: int,
    selector_calls: Mapping[str, int],
    arrays: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    return {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_cluster_execution_v1",
        "status": "complete_full_denominator"
        if all(row["unattempted_tick_count"] == 0 for row in arms)
        else "incomplete",
        "authority_sha256": AUTHORITY_SHA256,
        "cluster_index": cluster_index,
        "clone_key_sha256": clone_key_sha256,
        "source_record_sha256": source_record["source_record_sha256"],
        "cell": dict(source_record["cell"]),
        "route": {
            "geometry_sha256": source_record["route"]["geometry_sha256"],
            "route_lanelet_arc_sha256": source_record["route"][
                "route_lanelet_arc_sha256"
            ],
            "map_sha256": source_record["map"]["sha256"],
        },
        "arms": arms,
        "terminal_accounting": {
            "complete": sum(row["complete_tick_count"] for row in arms),
            "failed": sum(row["failed_tick_count"] for row in arms),
            "unattempted": sum(row["unattempted_tick_count"] for row in arms),
            "planned": len(ARMS) * TICKS_PER_ARM,
        },
        "formal_model_calls": model_calls,
        "selector_calls": dict(selector_calls),
        "sequential_calls": 0,
        "post_pool_model_dp_latent_generation_calls": 0,
        "tensor_mutation_count": 0,
        "array_inventory": {
            key: {
                "shape": list(np.asarray(value).shape),
                "dtype": np.asarray(value).dtype.str,
                "sha256": bytes_sha256(
                    np.ascontiguousarray(np.asarray(value)).tobytes()
                ),
            }
            for key, value in arrays.items()
        },
        "failure_retention": "full_denominator_no_drop_replace_complete_case",
        "outcome_values_read": False,
        "claim_authorized": False,
    }


def _write_cluster(
    output: Path, report: Mapping[str, Any], arrays: Mapping[str, np.ndarray]
) -> str:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    (output / "report.json").write_bytes(canonical_bytes(dict(report)))
    np.savez_compressed(
        output / "preimages.npz",
        **{key: np.asarray(value) for key, value in arrays.items()},
    )
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label=f"V25 multiroute-v2 cluster {report['cluster_index']}")


def execute(
    *,
    output: Path,
    preflight_dir: Path,
    preflight_root: str,
    preflight_review_dir: Path,
    preflight_review_root: str,
    training_dir: Path,
    training_root: str,
    training_review_dir: Path,
    training_review_root: str,
    fixed_dp_repo: Path,
    device: str,
) -> str:
    output = output.resolve()
    if output != Path(EXACT_DIRS["execution"]):
        raise ValueError("multiroute-v2 execution exact dir drifted")
    if output.exists():
        raise FileExistsError(output)
    preflight = _verify(preflight_dir, preflight_root, "multiroute-v2 preflight")
    _verify(
        preflight_review_dir,
        preflight_review_root,
        "multiroute-v2 preflight review",
    )
    if (
        preflight.get("status") != "passed_before_first_model_call"
        or preflight.get("cluster_count") != CLUSTER_COUNT
        or preflight.get("planned_tick_slots") != PLANNED_TICKS
        or preflight.get("model_pool_selector_calls") != 0
    ):
        raise ValueError("multiroute-v2 execution preflight drifted")
    if (
        training_root != TRAINING_ROOT_SHA256
        or training_review_root != TRAINING_REVIEW_ROOT_SHA256
    ):
        raise ValueError("selector training authority drifted")
    _verify(training_dir, training_root, "accepted selector training")
    _verify(training_review_dir, training_review_root, "accepted training review")
    fixed_dp_repo = fixed_dp_repo.resolve()
    if _git_head(fixed_dp_repo) != FIXED_DP_HEAD or _tracked_changes(fixed_dp_repo):
        raise ValueError("fixed DP authority drifted")
    interpreter = _interpreter()
    for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    _install_fixed_dp_annotation_compatibility(fixed_dp_repo)
    import torch
    import scenario_generation.replay as replay
    import scenario_generation.tensor_converter as tensor_converter
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route
    from camp_core.integrations.diffusion_planner import (
        install_lanelet2_projection_fallback,
        require_source_preserving_lanelet2_regulatory_adapter,
    )
    from scripts.integrations.run_diffusion_planner_camp_replay import _load_model

    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    prepared_manifest = object_from(preflight_dir / "prepared_manifest.json")[
        "clusters"
    ]
    if len(prepared_manifest) != CLUSTER_COUNT:
        raise ValueError("prepared cluster manifest denominator drifted")
    template_config = object_from(
        preflight_dir / "prepared" / "000" / "config.json"
    )
    model, model_args = _load_model(
        Path(template_config["fixed_dp"]["checkpoint"]["path"]),
        Path(template_config["fixed_dp"]["args_json"]["path"]),
        device,
    )
    model.eval()
    assets = load_v25_runtime_selector_assets(
        training_artifact=training_dir,
        training_root_sha256=training_root,
        training_review_artifact=training_review_dir,
        training_review_root_sha256=training_review_root,
    )
    control = output.parent / f".{output.name}_control"
    if control.exists():
        raise FileExistsError(control)
    control.mkdir(parents=True)
    started_ns = time.time_ns()
    total_model_calls = 0
    total_selector_calls = {"Static14D": 0, "Scene14D": 0}
    totals = {"complete": 0, "failed": 0, "unattempted": 0}
    cluster_summaries = []
    try:
        for prepared in prepared_manifest:
            cluster = int(prepared["cluster_index"])
            cluster_dir = preflight_dir / "prepared" / f"{cluster:03d}"
            config = object_from(cluster_dir / "config.json")
            source_record = object_from(cluster_dir / "source_record.json")
            clone_key = prepared["clone_key_sha256"]
            map_path = Path(config["map"]["path"])
            require_source_preserving_lanelet2_regulatory_adapter(map_path)
            install_lanelet2_projection_fallback(map_path)
            arms = []
            arrays: dict[str, np.ndarray] = {}
            cluster_model_calls = 0
            cluster_selector_calls = {"Static14D": 0, "Scene14D": 0}
            for arm_index, arm in enumerate(ARMS):
                adapter = build_scene_adapter(source_record)

                def tick_latent(tick: int, *, clone: str = clone_key) -> np.ndarray:
                    return latent_tensor(clone, tick)

                run = _run_one(
                    config=config,
                    model=model,
                    model_args=model_args,
                    tensor_converter=tensor_converter,
                    replay=replay,
                    builder_type=LaneletSceneBuilder,
                    route_type=Route,
                    fixed_dp_repo=fixed_dp_repo,
                    assets=assets,
                    device=device,
                    max_ticks=TICKS_PER_ARM,
                    operational_arm=arm,
                    evaluate_all_arms=False,
                    adaptation_diagnostics=False,
                    scratch_parent=control,
                    scene_adapter=adapter,
                    latent_provider=tick_latent,
                    post_safety_enricher=_post_safety_enricher,
                    retain_runtime_failures=True,
                )
                ticks = []
                complete = 0
                failed = 0
                for tick, receipt in enumerate(run["receipts"]):
                    terminal = "complete" if receipt.get("status") == "ok" else "failed"
                    complete += terminal == "complete"
                    failed += terminal == "failed"
                    normalized = _execution_tick(receipt, terminal)
                    expected_latent = latent_tensor(clone_key, tick)
                    if (
                        normalized.get("latent_tensor_sha256")
                        != bytes_sha256(expected_latent.tobytes())
                        or normalized.get("primary_pool_model_call_count") != 1
                        or normalized.get("candidate_tensor_sha256_before")
                        != normalized.get("candidate_tensor_sha256_after")
                    ):
                        raise RuntimeError(
                            "multiroute-v2 latent, call, or tensor binding drifted"
                        )
                    zero = normalized.get("zero_call_receipt")
                    if (
                        type(zero) is not dict
                        or zero.get("dp_or_model_calls_after_pool") != 0
                        or zero.get("latent_replacements_after_pool") != 0
                        or zero.get("candidate_generations_after_pool") != 0
                    ):
                        raise RuntimeError("multiroute-v2 post-pool call drifted")
                    ticks.append(normalized)
                unattempted = TICKS_PER_ARM - len(ticks)
                if unattempted:
                    raise RuntimeError("multiroute-v2 arm left unattempted ticks")
                model_calls = int(run["callback"].model_call_count)
                if model_calls != TICKS_PER_ARM:
                    raise RuntimeError("multiroute-v2 formal model call count drifted")
                cluster_model_calls += model_calls
                if arm in cluster_selector_calls:
                    cluster_selector_calls[arm] += len(ticks)
                arms.append(
                    {
                        "arm": arm,
                        "status": "complete_full_denominator",
                        "ticks": ticks,
                        "complete_tick_count": complete,
                        "failed_tick_count": failed,
                        "unattempted_tick_count": unattempted,
                        "native_result": dict(run["native_result"]),
                    }
                )
                arrays[f"{arm_index}_candidates"] = np.stack(
                    run["callback"].primary_candidates
                )
                arrays[f"{arm_index}_neighbors"] = np.stack(
                    run["callback"].primary_neighbors
                )
                if run["callback"].primary_atoms:
                    arrays[f"{arm_index}_atoms"] = np.stack(
                        run["callback"].primary_atoms
                    )
                    arrays[f"{arm_index}_source_masks"] = np.stack(
                        run["callback"].primary_source_masks
                    )
                    arrays[f"{arm_index}_physical_masks"] = np.stack(
                        run["callback"].primary_physical_masks
                    )
                if run["callback"].primary_causal_inputs:
                    causal_keys = set(run["callback"].primary_causal_inputs[0])
                    if any(
                        set(value) != causal_keys
                        for value in run["callback"].primary_causal_inputs
                    ):
                        raise RuntimeError("causal input keyset drifted across ticks")
                    for key in sorted(causal_keys):
                        arrays[f"{arm_index}_causal_{key}"] = np.stack(
                            [
                                value[key]
                                for value in run["callback"].primary_causal_inputs
                            ]
                        )
            if cluster_model_calls != len(ARMS) * TICKS_PER_ARM:
                raise RuntimeError("multiroute-v2 cluster model denominator drifted")
            cluster_report = _cluster_payload(
                cluster_index=cluster,
                clone_key_sha256=clone_key,
                source_record=source_record,
                arms=arms,
                model_calls=cluster_model_calls,
                selector_calls=cluster_selector_calls,
                arrays=arrays,
            )
            cluster_root = _write_cluster(
                control / "clusters" / f"{cluster:03d}",
                cluster_report,
                arrays,
            )
            terminal = cluster_report["terminal_accounting"]
            for key in totals:
                totals[key] += int(terminal[key])
            total_model_calls += cluster_model_calls
            for key in total_selector_calls:
                total_selector_calls[key] += cluster_selector_calls[key]
            cluster_summaries.append(
                {
                    "cluster_index": cluster,
                    "clone_key_sha256": clone_key,
                    "root_sha256": cluster_root,
                    "terminal_accounting": terminal,
                    "formal_model_calls": cluster_model_calls,
                    "selector_calls": cluster_selector_calls,
                }
            )
            (control / "milestone.json").write_bytes(
                canonical_bytes(
                    {
                        "completed_clusters": cluster + 1,
                        "completed_tick_slots": totals["complete"] + totals["failed"],
                        "formal_model_calls": total_model_calls,
                        "last_cluster_index": cluster,
                    }
                )
            )
        if (
            totals["complete"] + totals["failed"] != PLANNED_TICKS
            or totals["unattempted"] != 0
            or total_model_calls != PLANNED_TICKS
            or total_selector_calls != {"Static14D": 6_400, "Scene14D": 6_400}
        ):
            raise RuntimeError("multiroute-v2 global denominator or failure gate failed")
        report = {
            "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_execution_v1",
            "status": "complete_full_denominator_hard_integrity_passed",
            "authority_sha256": AUTHORITY_SHA256,
            "preflight_root_sha256": preflight_root,
            "preflight_review_root_sha256": preflight_review_root,
            "cluster_count": CLUSTER_COUNT,
            "arm_run_count": CLUSTER_COUNT * len(ARMS),
            "planned_tick_slots": PLANNED_TICKS,
            "terminal_accounting": {**totals, "planned": PLANNED_TICKS},
            "formal_model_calls": total_model_calls,
            "selector_calls": total_selector_calls,
            "sequential_calls": 0,
            "post_pool_model_dp_latent_generation_calls": 0,
            "candidate_tensor_mutation_count": 0,
            "hard_integrity_failure_count": 0,
            "cluster_artifacts": cluster_summaries,
            "implementation_head": git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "interpreter": interpreter,
            "elapsed_seconds": (time.time_ns() - started_ns) / 1e9,
            "fresh_or_b4_outcome_values_read": False,
            "old_artifact_or_cas_writes": 0,
            "claim_authorized": False,
        }
        (control / "report.json").write_bytes(canonical_bytes(report))
        (control / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "role": "industrial_v3_multiroute_v2_execution",
                    "authority_sha256": AUTHORITY_SHA256,
                    "implementation_head": git_head(),
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (control / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(control, label="V25 industrial-v3 multiroute-v2 execution")
        os.replace(control, output)
        verify_complete_seal(
            output, root, label="V25 industrial-v3 multiroute-v2 execution"
        )
        return root
    except BaseException:
        # The deterministic control tree is intentionally preserved after the
        # first model call; no replacement attempt is authorized.
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-dir", type=Path, required=True)
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--preflight-review-dir", type=Path, required=True)
    parser.add_argument("--preflight-review-root", required=True)
    parser.add_argument("--training-dir", type=Path, required=True)
    parser.add_argument("--training-root", required=True)
    parser.add_argument("--training-review-dir", type=Path, required=True)
    parser.add_argument("--training-review-root", required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    root = execute(
        output=args.output,
        preflight_dir=args.preflight_dir,
        preflight_root=args.preflight_root,
        preflight_review_dir=args.preflight_review_dir,
        preflight_review_root=args.preflight_review_root,
        training_dir=args.training_dir,
        training_root=args.training_root,
        training_review_dir=args.training_review_dir,
        training_review_root=args.training_review_root,
        fixed_dp_repo=args.fixed_dp_repo,
        device=args.device,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
