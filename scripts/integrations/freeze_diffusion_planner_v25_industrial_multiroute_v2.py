from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2 import (  # noqa: E402
    ATOM_SCALES_SHA256,
    AUTHORITY_SHA256,
    BASE_HEAD,
    CAPTURE_CLASSES,
    CLUSTER_COUNT,
    CONTINUATION_REVIEW_ROOT_SHA256,
    CONTINUATION_ROOT_SHA256,
    EXACT_DIRS,
    FIXED_DP_HEAD,
    INDUSTRIAL_CAPABILITY_ROOT_SHA256,
    INDUSTRIAL_CONTRACT_ROOT_SHA256,
    MIN_FREE_AFTER_BYTES,
    MIN_FREE_INODES_AFTER,
    PLANNED_TICKS,
    SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256,
    SOURCE_MATERIALIZATION_ROOT_SHA256,
    SOURCE_SELECTED_MANIFEST_SHA256,
    TRAINING_REVIEW_ROOT_SHA256,
    TRAINING_ROOT_SHA256,
    canonical_bytes,
    canonical_sha256,
    contract,
    latent_receipt,
    validate_contract,
    validate_selected_manifest,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


PRODUCTION_FILES = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_industrial_multiroute_v2.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_industrial_multiroute_v2_review.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_industrial_evaluation_contract_v3.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_controlled_scenarios.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_route_signal_authority.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_scene_runtime.py",
    "scripts/integrations/validate_diffusion_planner_v25_fair_nonholdout.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py",
    "scripts/integrations/freeze_diffusion_planner_v25_industrial_multiroute_v2.py",
    "scripts/integrations/run_diffusion_planner_v25_industrial_multiroute_v2.py",
    "scripts/integrations/review_diffusion_planner_v25_industrial_multiroute_v2.py",
    "scripts/integrations/evaluate_diffusion_planner_v25_industrial_multiroute_v2.py",
    "scripts/integrations/finalize_diffusion_planner_v25_industrial_multiroute_v2.py",
)
AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _interpreter(*, require_runtime: bool) -> dict[str, Any]:
    if require_runtime and Path(sys.executable).as_posix() != AUTODL_INTERPRETER:
        raise ValueError("AutoDL entrypoint must use frozen dp312 interpreter")
    if sys.version_info < (3, 10):
        raise ValueError("Python >=3.10 is required")
    imports = {}
    for name in (("json", "hashlib") if not require_runtime else ("numpy", "torch", "lanelet2")):
        try:
            module = __import__(name)
        except Exception as exc:
            raise ValueError(f"required import unavailable: {name}") from exc
        imports[name] = str(getattr(module, "__version__", "stdlib"))
    return {
        "sys_executable": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "sys_prefix": sys.prefix,
        "imports": imports,
    }


def _git_head(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _tracked_changes(path: Path) -> list[str]:
    output = subprocess.run(
        ["git", "-C", str(path), "status", "--short", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in output.splitlines() if line.strip()]


def _verify(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def freeze_contract(
    output: Path,
    *,
    source_contract_dir: Path,
    source_contract_root: str,
    source_contract_review_dir: Path,
    source_contract_review_root: str,
    source_materialization_dir: Path,
    source_materialization_root: str,
    source_materialization_review_dir: Path,
    source_materialization_review_root: str,
    continuation_dir: Path,
    continuation_root: str,
    continuation_review_dir: Path,
    continuation_review_root: str,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
) -> str:
    if output.resolve() != Path(EXACT_DIRS["contract"]):
        raise ValueError("multiroute-v2 contract exact dir drifted")
    bindings = (
        (source_contract_dir, source_contract_root, "source contract"),
        (source_contract_review_dir, source_contract_review_root, "source contract review"),
        (source_materialization_dir, source_materialization_root, "source materialization"),
        (
            source_materialization_review_dir,
            source_materialization_review_root,
            "source materialization review",
        ),
        (continuation_dir, continuation_root, "source continuation"),
        (continuation_review_dir, continuation_review_root, "source continuation review"),
        (industrial_contract_dir, industrial_contract_root, "industrial v3 contract"),
    )
    for path, root, label in bindings:
        _verify(path, root, label)
    if (
        source_materialization_root != SOURCE_MATERIALIZATION_ROOT_SHA256
        or source_materialization_review_root
        != SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256
        or continuation_root != CONTINUATION_ROOT_SHA256
        or continuation_review_root != CONTINUATION_REVIEW_ROOT_SHA256
        or industrial_contract_root != INDUSTRIAL_CONTRACT_ROOT_SHA256
    ):
        raise ValueError("multiroute-v2 upstream root drifted")
    payload = validate_contract(contract())
    files = {
        relative: _file_sha(ROOT / relative)
        for relative in PRODUCTION_FILES
        if (ROOT / relative).is_file()
    }
    if set(files) != set(PRODUCTION_FILES):
        raise ValueError("multiroute-v2 production inventory incomplete")
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_contract_artifact_v1",
        "status": "sealed_outcome_independent_multiroute_v2_contract",
        "authority_sha256": AUTHORITY_SHA256,
        "source_continuation_sha256": payload["authority"]["continuation_sha256"],
        "contract": payload,
        "implementation_head": git_head(),
        "base_head": BASE_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "production_file_sha256": files,
        "upstream_bindings": [
            {"path": str(path.resolve()), "root_sha256": root, "label": label}
            for path, root, label in bindings
        ],
        "interpreter": _interpreter(require_runtime=False),
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_multiroute_v2_contract",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        label="V25 industrial-v3 multiroute-v2 contract",
    )


def freeze_matrix(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    capability_dir: Path,
    capability_root: str,
) -> str:
    if output.resolve() != Path(EXACT_DIRS["hardening_matrix"]):
        raise ValueError("multiroute-v2 matrix exact dir drifted")
    contract_report = _verify(contract_dir, contract_root, "multiroute-v2 contract")
    capability = _verify(
        capability_dir, capability_root, "industrial v3 capability matrix"
    )
    if capability_root != INDUSTRIAL_CAPABILITY_ROOT_SHA256:
        raise ValueError("industrial capability root drifted")
    rows = capability.get("rows")
    if type(rows) is not list:
        rows = capability.get("capability_matrix", {}).get("rows")
    if type(rows) is not list or len(rows) != 161:
        raise ValueError("industrial capability matrix leaf topology drifted")
    capture_rows = []
    for row in rows:
        evidence = row["evidence_class"]
        if evidence == "scientifically_inapplicable":
            capture_class = "route_inapplicable"
        elif evidence == "evidence_missing":
            capture_class = "permanent_evidence_missing"
        elif evidence in {
            "directly_reconstructable",
            "reconstructable_with_frozen_transform",
        }:
            capture_class = (
                "runner_capture_direct"
                if evidence == "directly_reconstructable"
                else "runner_capture_plus_frozen_transform"
            )
        else:
            raise ValueError("unknown capability evidence class")
        capture_rows.append(
            {
                "leaf_id": row["leaf_id"],
                "baseline_evidence_class": evidence,
                "capture_class": capture_class,
                "source_shape": row["source_shape"],
                "source_units": row["source_units"],
                "canonical_json_pointers": row["canonical_json_pointers"],
                "applicability_prerequisites": row["applicability_prerequisites"],
                "transform_inputs": row["transform_inputs"],
                "prior_single_route_gap_classification": (
                    "route_applicability_or_receipt_transform_resolved_per_cluster"
                    if capture_class
                    in {
                        "runner_capture_direct",
                        "runner_capture_plus_frozen_transform",
                    }
                    else capture_class
                ),
            }
        )
    parameter_rows = [
        {
            "parameter": name,
            "sealed_source": source,
            "loader": loader,
            "production_callsite": callsite,
            "receipt": receipt,
            "reviewer_or_evaluator": consumer,
            "implicit_default_allowed": False,
        }
        for name, source, loader, callsite, receipt, consumer in (
            (
                "interpreter",
                contract_report["contract"]["hardening"]["autodl_interpreter"],
                "sys.executable",
                "all versioned entrypoints",
                "report.interpreter",
                "all independent reviewers",
            ),
            (
                "simplex_nonnegative_atol",
                "TRAINED_SIMPLEX_NONNEGATIVE_ATOL=1e-9",
                "load_v25_runtime_selector_assets",
                "_FairPredictBatch._evaluate_pool required keyword",
                "selector tolerances",
                "execution reviewer local literal",
            ),
            (
                "14d_scales",
                ATOM_SCALES_SHA256,
                "load_v25_runtime_selector_assets",
                "materialize_canonical_14d",
                "atom scale SHA",
                "execution and evaluation reviewers",
            ),
            (
                "Static14D_weights",
                TRAINING_ROOT_SHA256,
                "load_v25_runtime_selector_assets",
                "production Static14D selector",
                "weights SHA and values",
                "execution reviewer local literal",
            ),
            (
                "Scene14D_Theta_context",
                TRAINING_REVIEW_ROOT_SHA256,
                "load_v25_runtime_selector_assets",
                "production Scene14D selector",
                "Theta/context receipts",
                "execution reviewer local literal",
            ),
            (
                "source_signal_actor_applicability",
                SOURCE_MATERIALIZATION_ROOT_SHA256,
                "build_scene_adapter",
                "_FairPredictBatch before tensor conversion",
                "controlled_scene and causal signal",
                "execution/evaluation reviewers",
            ),
            (
                "terminal_failure_denominator",
                "contract.denominator",
                "typed config",
                "multiroute execution loop",
                "cluster terminal accounting",
                "execution reviewer",
            ),
            (
                "latency_namespaces",
                "contract.latency_namespaces",
                "typed config",
                "runner timing callsites",
                "per-tick latency",
                "evaluation reviewer",
            ),
            (
                "root_head_route_latent",
                "contract authority and preflight",
                "sealed preflight loader",
                "before each formal forward",
                "slot binding",
                "execution reviewer",
            ),
        )
    ]
    matrix = {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_hardening_matrix_v1",
        "status": "sealed_zero_model_pre_execution_hardening_matrix",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "capability_root_sha256": capability_root,
        "parameter_propagation_rows": parameter_rows,
        "scalar_leaf_capture_mapping": capture_rows,
        "capture_class_counts": {
            name: sum(row["capture_class"] == name for row in capture_rows)
            for name in CAPTURE_CLASSES
        },
        "production_entrypoints": [
            {
                "relative_path": relative,
                "sha256": _file_sha(ROOT / relative),
                "actually_executed": relative
                in {
                    "scripts/integrations/validate_diffusion_planner_v25_fair_nonholdout.py",
                    "scripts/integrations/run_diffusion_planner_v25_industrial_multiroute_v2.py",
                },
            }
            for relative in PRODUCTION_FILES
        ],
        "dry_run_cases": [
            "pass_entrypoint_receipt_atomic_seal_review_evaluation_review",
            "typed_failure_entrypoint_receipt_atomic_seal_review_evaluation_review",
            "missing_required_keyword_or_default_fallback",
            "wrong_interpreter_or_schema_version",
            "extra_missing_duplicate_field",
            "nan_inf_or_typed_missing",
            "path_alias_or_partial_atomic_write",
            "resign_repin_or_wrong_root_head",
        ],
        "residual_risk_register": [
            {
                "class": "actually_executed",
                "scope": "project-authored 100-cluster three-arm runtime paths",
                "residual_risk": "bounded development inventory and pinned runtime only",
            },
            {
                "class": "static_only",
                "scope": "authority drift and typed-failure mutation branches",
                "residual_risk": "mutations are synthetic",
            },
            {
                "class": "unexecuted",
                "scope": "Fresh, other maps, other hardware, deployment",
                "residual_risk": "no evidence and no claim",
            },
        ],
        "zero_bug_claimed": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return write_atomic(
        output,
        matrix,
        {
            "role": "industrial_v3_multiroute_v2_hardening_matrix",
            "authority_sha256": AUTHORITY_SHA256,
            "contract_root_sha256": contract_root,
            "capability_root_sha256": capability_root,
        },
        label="V25 industrial-v3 multiroute-v2 hardening matrix",
    )


def _tree_size_and_files(path: Path) -> tuple[int, int]:
    total = 0
    count = 0
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        for name in files:
            item = Path(root) / name
            if item.is_symlink():
                raise ValueError("capacity source contains symlink")
            total += item.stat().st_size
            count += 1
    return total, count


def freeze_focused(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    matrix_dir: Path,
    matrix_root: str,
    matrix_review_dir: Path,
    matrix_review_root: str,
    test_count: int,
    command_sha256: str,
    stdout_sha256: str,
) -> str:
    if output.resolve() != Path(EXACT_DIRS["hardening_focused"]):
        raise ValueError("multiroute-v2 focused exact dir drifted")
    for path, root, label in (
        (contract_dir, contract_root, "multiroute-v2 contract"),
        (contract_review_dir, contract_review_root, "multiroute-v2 contract review"),
        (matrix_dir, matrix_root, "multiroute-v2 hardening matrix"),
        (matrix_review_dir, matrix_review_root, "multiroute-v2 matrix review"),
    ):
        _verify(path, root, label)
    if test_count <= 0:
        raise ValueError("focused test count must be positive")
    for value, label in (
        (command_sha256, "focused command SHA"),
        (stdout_sha256, "focused stdout SHA"),
    ):
        if (
            type(value) is not str
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError(f"{label} is invalid")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_hardening_focused_v1"
        ),
        "status": "passed_zero_model_pre_execution_hardening_focused",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "matrix_root_sha256": matrix_root,
        "matrix_review_root_sha256": matrix_review_root,
        "test_count": test_count,
        "test_command_sha256": command_sha256,
        "stdout_sha256": stdout_sha256,
        "interpreter": _interpreter(require_runtime=True),
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_multiroute_v2_hardening_focused",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": git_head(),
            "contract_root_sha256": contract_root,
            "matrix_root_sha256": matrix_root,
        },
        label="V25 industrial-v3 multiroute-v2 hardening focused",
    )


def _write_preflight(
    output: Path,
    report: Mapping[str, Any],
    *,
    selected: list[dict[str, Any]],
    source_dir: Path,
    probe_config: Mapping[str, Any],
    fixed_dp_repo: Path,
) -> str:
    import numpy as np

    for path in (fixed_dp_repo, fixed_dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.route import Route

    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        prepared_manifest = []
        for selected_row in selected:
            cluster = int(selected_row["cluster_index"])
            candidate = selected_row["candidate"]
            record = selected_row["source_record"]
            cluster_dir = staging / "prepared" / f"{cluster:03d}"
            final_cluster_dir = output / "prepared" / f"{cluster:03d}"
            cluster_dir.mkdir(parents=True)
            source_map = source_dir / record["map"]["relative_path"]
            target_map = cluster_dir / "lanelet2_map.osm"
            final_map = final_cluster_dir / "lanelet2_map.osm"
            shutil.copyfile(source_map, target_map)
            if _file_sha(target_map) != record["map"]["sha256"]:
                raise ValueError("prepared source map SHA drifted")
            geometry = record["route"]["geometry"]
            centerline = np.asarray(geometry["centerline_points_m"], dtype=np.float64)
            headings = np.asarray(geometry["segment_headings_rad"], dtype=np.float64)
            route_ids = [
                3_000_000 + int(record["ordinal"]) * 1_000 + 401 + index
                for index in range(4)
            ]
            route = Route(
                map_path=str(final_map),
                start_pose=np.asarray(
                    [centerline[0, 0], centerline[0, 1], headings[0]],
                    dtype=np.float64,
                ),
                goal_pose=np.asarray(
                    [centerline[-1, 0], centerline[-1, 1], headings[-1]],
                    dtype=np.float64,
                ),
                start_lanelet_id=route_ids[0],
                goal_lanelet_id=route_ids[-1],
                waypoint_poses=[
                    np.asarray(
                        [
                            point[0],
                            point[1],
                            headings[min(index, len(headings) - 1)],
                        ],
                        dtype=np.float64,
                    )
                    for index, point in enumerate(centerline)
                ],
                waypoint_lanelet_ids=[
                    route_ids[min(index, len(route_ids) - 1)]
                    for index in range(len(centerline))
                ],
                route_lanelet_ids=route_ids,
            )
            route_path = cluster_dir / "route.pkl"
            final_route_path = final_cluster_dir / "route.pkl"
            route.save(route_path)
            config = deepcopy(dict(probe_config))
            config["map"] = {
                "path": str(final_map),
                "sha256": record["map"]["sha256"],
            }
            config["routes"] = [
                {
                    "name": f"project_multiroute_{cluster:03d}",
                    "path": str(final_route_path),
                    "sha256": _file_sha(route_path),
                }
            ]
            config["seeds"]["scenario"] = int(record["seeds"]["scenario"])
            config_path = cluster_dir / "config.json"
            config_path.write_bytes(canonical_bytes(config))
            latent_manifest = [
                latent_receipt(candidate["clone_key_sha256"], tick)
                for tick in range(64)
            ]
            latent_path = cluster_dir / "latent_manifest.json"
            latent_path.write_bytes(canonical_bytes({"ticks": latent_manifest}))
            record_path = cluster_dir / "source_record.json"
            record_path.write_bytes(canonical_bytes(record))
            prepared_manifest.append(
                {
                    "cluster_index": cluster,
                    "ordinal": int(record["ordinal"]),
                    "clone_key_sha256": candidate["clone_key_sha256"],
                    "source_record_sha256": record["source_record_sha256"],
                    "map_sha256": _file_sha(target_map),
                    "route_file_sha256": _file_sha(route_path),
                    "config_sha256": _file_sha(config_path),
                    "latent_manifest_sha256": _file_sha(latent_path),
                    "source_record_file_sha256": _file_sha(record_path),
                }
            )
        (staging / "prepared_manifest.json").write_bytes(
            canonical_bytes({"clusters": prepared_manifest})
        )
        (staging / "report.json").write_bytes(canonical_bytes(dict(report)))
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "role": "industrial_v3_multiroute_v2_preflight",
                    "authority_sha256": AUTHORITY_SHA256,
                    "implementation_head": git_head(),
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="V25 industrial-v3 multiroute-v2 preflight")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 industrial-v3 multiroute-v2 preflight"
        )
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def freeze_preflight(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    matrix_dir: Path,
    matrix_root: str,
    matrix_review_dir: Path,
    matrix_review_root: str,
    focused_dir: Path,
    focused_root: str,
    source_dir: Path,
    source_root: str,
    source_review_dir: Path,
    source_review_root: str,
    probe_config: Path,
    fixed_dp_repo: Path,
    capacity_sources: list[Path],
) -> str:
    if output.resolve() != Path(EXACT_DIRS["preflight"]):
        raise ValueError("multiroute-v2 preflight exact dir drifted")
    for path, root, label in (
        (contract_dir, contract_root, "multiroute-v2 contract"),
        (contract_review_dir, contract_review_root, "multiroute-v2 contract review"),
        (matrix_dir, matrix_root, "multiroute-v2 matrix"),
        (matrix_review_dir, matrix_review_root, "multiroute-v2 matrix review"),
        (focused_dir, focused_root, "multiroute-v2 hardening focused"),
        (source_dir, source_root, "project source materialization"),
        (source_review_dir, source_review_root, "project source review"),
    ):
        _verify(path, root, label)
    if (
        source_root != SOURCE_MATERIALIZATION_ROOT_SHA256
        or source_review_root != SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256
    ):
        raise ValueError("source materialization root drifted")
    if _git_head(fixed_dp_repo) != FIXED_DP_HEAD or _tracked_changes(fixed_dp_repo):
        raise ValueError("fixed DP authority drifted")
    if _tracked_changes(ROOT):
        allowed = {
            "scripts/integrations/materialize_diffusion_planner_v25_batch8_training_support_reference.py",
            "scripts/integrations/review_diffusion_planner_v25_batch8_training_support_reference.py",
        }
        actual = {
            line[3:].replace("\\", "/")
            for line in _tracked_changes(ROOT)
            if len(line) > 3
        }
        if not actual.issubset(allowed):
            raise ValueError("CAMP tracked scope drifted before model")
    source_report = object_from(source_dir / "report.json")
    source_records = object_from(source_dir / "source_records.json")["records"]
    selected_manifest = object_from(source_dir / "selected_manifest.json")
    if (
        source_report.get("status")
        != "passed_project_authored_source_materialization"
        or source_report.get("selected_manifest_sha256")
        != SOURCE_SELECTED_MANIFEST_SHA256
    ):
        raise ValueError("source materialization status drifted")
    selected = validate_selected_manifest(selected_manifest, source_records)
    if len(selected) != CLUSTER_COUNT:
        raise ValueError("preflight cluster denominator drifted")
    per_class = []
    for path in capacity_sources:
        size, count = _tree_size_and_files(path)
        per_class.append(
            {
                "path": str(path.resolve()),
                "single_route_payload_bytes": size,
                "single_route_file_count": count,
                "projected_bytes": math.ceil(size * 100 * 1.25),
                "projected_files": math.ceil(count * 100 * 1.25),
            }
        )
    persistent = sum(row["projected_bytes"] for row in per_class) + 2 * 1024**3
    peak = max((row["projected_bytes"] for row in per_class), default=0)
    reserve = max(5 * 1024**3, math.ceil(peak * 0.25))
    usage = shutil.disk_usage(output.parent)
    projected_free = usage.free - persistent - peak
    free_inodes = int(os.statvfs(output.parent).f_favail)
    projected_inodes = free_inodes - sum(row["projected_files"] for row in per_class)
    if (
        projected_free < MIN_FREE_AFTER_BYTES + reserve
        or projected_inodes < MIN_FREE_INODES_AFTER
    ):
        raise RuntimeError("multiroute-v2 capacity gate failed before model")
    config = object_from(probe_config)
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_multiroute_v2_preflight_v1",
        "status": "passed_before_first_model_call",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "matrix_root_sha256": matrix_root,
        "matrix_review_root_sha256": matrix_review_root,
        "hardening_focused_root_sha256": focused_root,
        "source_root_sha256": source_root,
        "source_review_root_sha256": source_review_root,
        "selected_manifest_sha256": SOURCE_SELECTED_MANIFEST_SHA256,
        "cluster_count": CLUSTER_COUNT,
        "planned_tick_slots": PLANNED_TICKS,
        "zero_overlap": source_report["zero_overlap"],
        "capacity": {
            "classes": per_class,
            "free_before_bytes": usage.free,
            "persistent_bytes": persistent,
            "peak_bytes": peak,
            "reserve_bytes": reserve,
            "projected_free_after_persistent_and_peak_bytes": projected_free,
            "required_free_after_bytes": MIN_FREE_AFTER_BYTES + reserve,
            "free_inodes_before": free_inodes,
            "projected_free_inodes": projected_inodes,
            "required_free_inodes": MIN_FREE_INODES_AFTER,
        },
        "dry_run": {
            "pass_and_typed_failure_full_pipeline": True,
            "nan_inf_typed_missing_and_atomic_seal": True,
            "wrong_root_head_schema_field_and_path_alias_mutations_rejected": True,
        },
        "interpreter": _interpreter(require_runtime=True),
        "worker_count": 0,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
    }
    return _write_preflight(
        output,
        report,
        selected=selected,
        source_dir=source_dir,
        probe_config=config,
        fixed_dp_repo=fixed_dp_repo,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    contract_parser = sub.add_parser("contract")
    contract_parser.add_argument("--output", type=Path, required=True)
    for name in (
        "source-contract-dir",
        "source-contract-review-dir",
        "source-materialization-dir",
        "source-materialization-review-dir",
        "continuation-dir",
        "continuation-review-dir",
        "industrial-contract-dir",
    ):
        contract_parser.add_argument(f"--{name}", type=Path, required=True)
        contract_parser.add_argument(
            f"--{name.replace('-dir', '-root')}", required=True
        )
    matrix_parser = sub.add_parser("matrix")
    matrix_parser.add_argument("--output", type=Path, required=True)
    matrix_parser.add_argument("--contract-dir", type=Path, required=True)
    matrix_parser.add_argument("--contract-root", required=True)
    matrix_parser.add_argument("--capability-dir", type=Path, required=True)
    matrix_parser.add_argument("--capability-root", required=True)
    focused_parser = sub.add_parser("focused")
    focused_parser.add_argument("--output", type=Path, required=True)
    for name in ("contract", "contract-review", "matrix", "matrix-review"):
        focused_parser.add_argument(f"--{name}-dir", type=Path, required=True)
        focused_parser.add_argument(f"--{name}-root", required=True)
    focused_parser.add_argument("--test-count", type=int, required=True)
    focused_parser.add_argument("--command-sha256", required=True)
    focused_parser.add_argument("--stdout-sha256", required=True)
    preflight_parser = sub.add_parser("preflight")
    preflight_parser.add_argument("--output", type=Path, required=True)
    for name in (
        "contract",
        "contract-review",
        "matrix",
        "matrix-review",
        "focused",
        "source",
        "source-review",
    ):
        preflight_parser.add_argument(f"--{name}-dir", type=Path, required=True)
        preflight_parser.add_argument(f"--{name}-root", required=True)
    preflight_parser.add_argument("--probe-config", type=Path, required=True)
    preflight_parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    preflight_parser.add_argument(
        "--capacity-source", type=Path, action="append", default=[]
    )
    args = parser.parse_args()
    if args.command == "contract":
        root = freeze_contract(
            args.output,
            source_contract_dir=args.source_contract_dir,
            source_contract_root=args.source_contract_root,
            source_contract_review_dir=args.source_contract_review_dir,
            source_contract_review_root=args.source_contract_review_root,
            source_materialization_dir=args.source_materialization_dir,
            source_materialization_root=args.source_materialization_root,
            source_materialization_review_dir=args.source_materialization_review_dir,
            source_materialization_review_root=args.source_materialization_review_root,
            continuation_dir=args.continuation_dir,
            continuation_root=args.continuation_root,
            continuation_review_dir=args.continuation_review_dir,
            continuation_review_root=args.continuation_review_root,
            industrial_contract_dir=args.industrial_contract_dir,
            industrial_contract_root=args.industrial_contract_root,
        )
    elif args.command == "matrix":
        root = freeze_matrix(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            capability_dir=args.capability_dir,
            capability_root=args.capability_root,
        )
    elif args.command == "focused":
        root = freeze_focused(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
            matrix_dir=args.matrix_dir,
            matrix_root=args.matrix_root,
            matrix_review_dir=args.matrix_review_dir,
            matrix_review_root=args.matrix_review_root,
            test_count=args.test_count,
            command_sha256=args.command_sha256,
            stdout_sha256=args.stdout_sha256,
        )
    else:
        root = freeze_preflight(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
            matrix_dir=args.matrix_dir,
            matrix_root=args.matrix_root,
            matrix_review_dir=args.matrix_review_dir,
            matrix_review_root=args.matrix_review_root,
            focused_dir=args.focused_dir,
            focused_root=args.focused_root,
            source_dir=args.source_dir,
            source_root=args.source_root,
            source_review_dir=args.source_review_dir,
            source_review_root=args.source_review_root,
            probe_config=args.probe_config,
            fixed_dp_repo=args.fixed_dp_repo,
            capacity_sources=args.capacity_source,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
