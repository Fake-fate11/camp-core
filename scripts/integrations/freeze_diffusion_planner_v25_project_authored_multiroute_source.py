"""Freeze, materialize, and continue the project-authored multiroute source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "camp_core", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_project_authored_multiroute_source import (  # noqa: E402
    AUDITED_BASE_SHA256,
    AUTHORITY_SHA256,
    AUTODL_INTERPRETER,
    BASE_HEAD,
    FIXED_DP_HEAD,
    PARENT_AUTHORITY_SHA256,
    SOURCE_EXACT_DIRS,
    ZERO_OVERLAP_LEVELS,
    build_universe,
    canonical_bytes,
    canonical_sha256,
    source_contract,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


PARENT_ARTIFACTS = {
    "parent_contract": (
        Path(
            "/root/autodl-tmp/"
            "camp_dp_v25_industrial_v3_multiroute_contract_923e6b29_b5ca942b"
        ),
        "a35f550364e2a75ff958cf8c0df81f9d44376c9611342b916319106c7eb2cbfb",
    ),
    "parent_contract_review": (
        Path(
            "/root/autodl-tmp/"
            "camp_dp_v25_industrial_v3_multiroute_contract_review_923e6b29_b5ca942b"
        ),
        "b8dab88cd2a57dc501872a5c7a190ab43d2a8543211fad427f61713bdced6e19",
    ),
    "parent_manifest_failure": (
        Path(
            "/root/autodl-tmp/"
            "camp_dp_v25_industrial_v3_multiroute_manifest_923e6b29_b5ca942b"
        ),
        "92d133e9acf7edac2c912442ddc10046e3854220b876120f1e80ea9557a89ea6",
    ),
    "parent_manifest_failure_review": (
        Path(
            "/root/autodl-tmp/"
            "camp_dp_v25_industrial_v3_multiroute_manifest_review_923e6b29_b5ca942b"
        ),
        "bb566079e2c86abd64bae181b03e087e86cfcd5f659a23236c915b9722cf7dd7",
    ),
    "parent_final_docs": (
        Path(
            "/root/autodl-tmp/"
            "camp_dp_v25_industrial_v3_multiroute_final_docs_focused_923e6b29_b5ca942b"
        ),
        "cad0c8b26e8a05a1c613cb4412eabd7fc66590508ef55119520c14d05917bd03",
    ),
}

FORBIDDEN_SOURCES = {
    "training": (
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_controlled_corpus_source_freeze_retry2_"
                "ff028387_20260717T140842CST"
            ),
            "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531",
        ),
    ),
    "calibration": (
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c"
            ),
            "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22",
        ),
    ),
    "legacy_nonholdout": (
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_a17_route_signal_source_census_"
                "c7b1cdba_20260720T124603CST"
            ),
            "252862ea50a6f1be906403b136c170ef16dbb2246568821bcbba9283290b0dbb",
        ),
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_industrial_v3_multiroute_manifest_923e6b29_b5ca942b"
            ),
            "92d133e9acf7edac2c912442ddc10046e3854220b876120f1e80ea9557a89ea6",
        ),
    ),
    "bounded_single_route": (
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_industrial_v3_bounded_closed_loop_"
                "preflight_a8b665a0_5e55899b"
            ),
            "e6cb543de41042f70ba7ad2ff83eff25ea7beda5afd8387c4885932f2378ba71",
        ),
    ),
    "corrected_64_state_development": (
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_batch8_generator_repeatability_corrected_"
                "preflight_v1_dc76fbc8"
            ),
            "5be8831533f0a46ecc5439c3eafbff85118689f7696996d825c4b09838189fac",
        ),
    ),
    "Fresh_B2": (
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_fresh_b4_preopen_authority_"
                "7be93df2_20260724TconsumerFinalCST"
            ),
            "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829",
        ),
    ),
    "Fresh_B3": (
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_fresh_b4_preopen_authority_"
                "7be93df2_20260724TconsumerFinalCST"
            ),
            "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829",
        ),
    ),
    "Fresh_B4": (
        (
            Path(
                "/root/autodl-tmp/"
                "camp_dp_v25_fresh_b4_preopen_authority_"
                "7be93df2_20260724TconsumerFinalCST"
            ),
            "bfb6727983cbb43a3612ea00d274b249277ed4abfa4f63219c5aaba4420b2829",
        ),
    ),
}

IMPLEMENTATION_FILES = {
    "producer": (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_project_authored_multiroute_source.py"
    ),
    "reviewer": (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_project_authored_multiroute_source_review.py"
    ),
    "materializer": Path(__file__).resolve(),
    "artifact_reviewer": (
        ROOT
        / "scripts/integrations/"
        "review_diffusion_planner_v25_project_authored_multiroute_source.py"
    ),
    "tests": (
        ROOT
        / "camp_core/tests/"
        "test_diffusion_planner_v25_project_authored_multiroute_source.py"
    ),
}

AUDITED_BASE_FILES = {
    "signal_complete_generator": (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_signal_complete_maps.py"
    ),
    "materializer": (
        ROOT
        / "scripts/integrations/"
        "materialize_diffusion_planner_v25_signal_complete_maps.py"
    ),
    "controlled_scenario_semantics": (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_controlled_scenarios.py"
    ),
    "signal_plan": (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_signal_complete_plan.py"
    ),
    "signal_runtime": (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_signal_complete_runtime.py"
    ),
    "mapped_signal_authority": (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_route_signal_authority.py"
    ),
    "no_signal_authority": (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_semantic_authority.py"
    ),
    "license": ROOT / "LICENSE",
}


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _interpreter() -> dict[str, Any]:
    return {
        "sys_executable": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "sys_prefix": sys.prefix,
        "minimum_version_passed": sys.version_info >= (3, 10),
        "autodl_exact_interpreter_passed": sys.executable == AUTODL_INTERPRETER,
        "required_imports": {
            "numpy": True,
            "xml.etree.ElementTree": True,
            "hashlib": True,
            "json": True,
        },
    }


def _require_runtime() -> None:
    receipt = _interpreter()
    if (
        receipt["minimum_version_passed"] is not True
        or receipt["autodl_exact_interpreter_passed"] is not True
    ):
        raise RuntimeError("formal source stage requires exact AutoDL dp312")


def _verify_parent() -> None:
    for label, (path, root) in PARENT_ARTIFACTS.items():
        verify_complete_seal(path, root, label=label)


def _implementation_inventory() -> dict[str, str]:
    values = {name: _file_sha(path) for name, path in IMPLEMENTATION_FILES.items()}
    if any(not path.is_file() for path in IMPLEMENTATION_FILES.values()):
        raise RuntimeError("source implementation inventory is incomplete")
    return values


def _verify_audited_base() -> dict[str, str]:
    actual = {name: _file_sha(path) for name, path in AUDITED_BASE_FILES.items()}
    if actual != AUDITED_BASE_SHA256:
        raise RuntimeError("audited project-authored generator base drifted")
    return actual


def freeze_contract(output: Path) -> str:
    _require_runtime()
    if output != Path(SOURCE_EXACT_DIRS["contract"]):
        raise ValueError("source contract exact dir drifted")
    _verify_parent()
    base_files = _verify_audited_base()
    implementation_files = _implementation_inventory()
    head = git_head()
    report = {
        "schema_version": (
            "camp_dp_v25_project_authored_multiroute_source_contract_artifact_v1"
        ),
        "status": "sealed_outcome_independent_source_contract",
        "authority_sha256": AUTHORITY_SHA256,
        "contract": source_contract(),
        "base_pointer_head": BASE_HEAD,
        "implementation_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "implementation_file_sha256": implementation_files,
        "audited_base_file_sha256": base_files,
        "parent_diagnostic_bindings": {
            key: {"path": str(path), "root_sha256": root}
            for key, (path, root) in PARENT_ARTIFACTS.items()
        },
        "interpreter": _interpreter(),
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
    }
    return write_atomic(
        output,
        report,
        {
            "role": "project_authored_multiroute_source_contract",
            "authority_sha256": AUTHORITY_SHA256,
            "base_pointer_head": BASE_HEAD,
            "implementation_head": head,
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        label="V25 project-authored multiroute source contract",
    )


def _walk(value: Any, prefix: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if type(value) is dict:
        for key, item in value.items():
            yield from _walk(item, prefix + (str(key),))
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _walk(item, prefix + (str(index),))
    else:
        yield prefix, value


def _extract_layers(values: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    result = {level: set() for level in ZERO_OVERLAP_LEVELS}
    for value in values:
        for path, item in _walk(value):
            key = ".".join(path).lower()
            if type(item) is str and len(item) == 64 and all(
                char in "0123456789abcdef" for char in item.lower()
            ):
                item = item.lower()
                if "route" in key or "lanelet" in key:
                    result["route"].add(item)
                if "state" in key or "input" in key or "spawn" in key:
                    result["state"].add(item)
                if "geometry" in key or "map_" in key:
                    result["geometry"].add(item)
                if "semantic" in key or "scenario" in key or "actor" in key:
                    result["semantic"].add(item)
                if "source" in key or "record" in key or "case" in key:
                    result["source"].add(item)
                if "seed" in key:
                    result["seed"].add(item)
                if "latent" in key:
                    result["latent_instance"].add(item)
                if "clone" in key or "composite" in key:
                    result["composite"].add(item)
            elif type(item) is int and not isinstance(item, bool) and "seed" in key:
                result["seed"].add(canonical_sha256({"seed": item}))
    return {level: sorted(items) for level, items in result.items()}


def _json_objects(path: Path) -> list[dict[str, Any]]:
    values = []
    for file_path in sorted(path.rglob("*.json")):
        if file_path.stat().st_size > 100_000_000:
            raise RuntimeError(f"forbidden inventory JSON unexpectedly large: {file_path}")
        value = json.loads(file_path.read_text(encoding="utf-8"))
        if type(value) is dict:
            values.append(value)
    if not values:
        raise RuntimeError(f"forbidden inventory contains no JSON: {path}")
    return values


def rebuild_forbidden_inventories() -> dict[str, Any]:
    result = {}
    for authority, sources in FORBIDDEN_SOURCES.items():
        values = []
        bindings = []
        for path, root in sources:
            verify_complete_seal(path, root, label=f"forbidden {authority}")
            values.extend(_json_objects(path))
            bindings.append({"path": str(path), "root_sha256": root})
        layers = _extract_layers(values)
        result[authority] = {
            "bindings": bindings,
            "layers": layers,
            "layer_counts": {key: len(value) for key, value in layers.items()},
            "inventory_sha256": canonical_sha256(layers),
        }
    return result


def _atomic_materialization(
    output: Path,
    *,
    report: dict[str, Any],
    records: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    selected_manifest: dict[str, Any],
    maps: Mapping[str, bytes],
    forbidden: Mapping[str, Any],
) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("source materialization output already exists")
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "role": "project_authored_multiroute_source_materialization",
                    "authority_sha256": AUTHORITY_SHA256,
                    "implementation_head": git_head(),
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "source_records.json").write_bytes(
            canonical_bytes({"records": records})
        )
        (staging / "candidates.json").write_bytes(
            canonical_bytes({"candidates": candidates})
        )
        (staging / "selected_manifest.json").write_bytes(
            canonical_bytes(selected_manifest)
        )
        (staging / "forbidden_inventories.json").write_bytes(
            canonical_bytes(forbidden)
        )
        for relative, raw in maps.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        root = seal_artifact(
            staging, label="V25 project-authored multiroute source materialization"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 project-authored multiroute source materialization",
        )
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def materialize(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
) -> str:
    _require_runtime()
    if output != Path(SOURCE_EXACT_DIRS["materialization"]):
        raise ValueError("source materialization exact dir drifted")
    verify_complete_seal(contract_dir, contract_root, label="source contract")
    verify_complete_seal(
        contract_review_dir, contract_review_root, label="source contract review"
    )
    contract_report = object_from(contract_dir / "report.json")
    if (
        contract_report.get("authority_sha256") != AUTHORITY_SHA256
        or contract_report.get("implementation_head") != git_head()
        or contract_report.get("implementation_file_sha256")
        != _implementation_inventory()
    ):
        raise RuntimeError("source contract implementation binding drifted")
    forbidden = rebuild_forbidden_inventories()
    universe = build_universe(source_contract_root_sha256=contract_root)
    selected = universe["selected_manifest"]["entries"]
    selected_layers = {
        level: {row["overlap_keys"][level] for row in selected}
        for level in ZERO_OVERLAP_LEVELS
    }
    overlap = {}
    for authority, inventory in forbidden.items():
        intersections = {
            level: sorted(
                selected_layers[level].intersection(
                    set(inventory["layers"][level])
                )
            )
            for level in ZERO_OVERLAP_LEVELS
        }
        if any(intersections.values()):
            raise RuntimeError(f"project-authored source overlaps {authority}")
        overlap[authority] = {
            "intersection_counts": {
                level: len(values) for level, values in intersections.items()
            },
            "intersection_sha256": {
                level: canonical_sha256(values)
                for level, values in intersections.items()
            },
        }
    selected_ordinals = universe["selected_manifest"][
        "selected_source_record_ordinals"
    ]
    report = {
        "schema_version": (
            "camp_dp_v25_project_authored_multiroute_source_materialization_artifact_v1"
        ),
        "status": "passed_project_authored_source_materialization",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "candidate_ceiling": 252,
        "materialized_candidate_count": 252,
        "generation_failure_count": 0,
        "map_count": len(universe["maps"]),
        "geometry_unique_count": len(
            {
                row["route"]["geometry_sha256"]
                for row in universe["records"]
            }
        ),
        "clone_key_unique_count": len(
            {row["clone_key_sha256"] for row in universe["candidates"]}
        ),
        "selected_count": 100,
        "selected_manifest_sha256": universe["selected_manifest"][
            "manifest_sha256"
        ],
        "selected_source_record_ordinals": selected_ordinals,
        "selected_clone_vector_sha256": canonical_sha256(
            universe["selected_manifest"]["selected_clone_key_sha256"]
        ),
        "zero_overlap": overlap,
        "forbidden_inventory_sha256": {
            authority: value["inventory_sha256"]
            for authority, value in forbidden.items()
        },
        "license_spdx": "MIT",
        "third_party_map_payload_derived": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
        "implementation_head": git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
        "interpreter": _interpreter(),
    }
    return _atomic_materialization(
        output,
        report=report,
        records=universe["records"],
        candidates=universe["candidates"],
        selected_manifest=universe["selected_manifest"],
        maps=universe["maps"],
        forbidden=forbidden,
    )


def freeze_continuation(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    materialization_dir: Path,
    materialization_root: str,
    materialization_review_dir: Path,
    materialization_review_root: str,
) -> str:
    _require_runtime()
    if output != Path(SOURCE_EXACT_DIRS["continuation_authority"]):
        raise ValueError("source continuation exact dir drifted")
    for path, root, label in (
        (contract_dir, contract_root, "source contract"),
        (contract_review_dir, contract_review_root, "source contract review"),
        (materialization_dir, materialization_root, "source materialization"),
        (
            materialization_review_dir,
            materialization_review_root,
            "source materialization review",
        ),
    ):
        verify_complete_seal(path, root, label=label)
    source = object_from(materialization_dir / "report.json")
    parent = object_from(PARENT_ARTIFACTS["parent_contract"][0] / "report.json")[
        "contract"
    ]
    preimage = {
        "parent_source_authority_sha256": AUTHORITY_SHA256,
        "source_contract_root": contract_root,
        "source_contract_review_root": contract_review_root,
        "source_materialization_root": materialization_root,
        "source_materialization_review_root": materialization_review_root,
        "selected_manifest_sha256": source["selected_manifest_sha256"],
        "implementation_head": git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
        "parent_b5ca_authority_sha256": PARENT_AUTHORITY_SHA256,
        "all_unchanged_b5ca_scientific_contract_fields": parent,
    }
    continuation_sha = canonical_sha256(preimage)
    report = {
        "schema_version": (
            "camp_dp_v25_project_authored_multiroute_continuation_authority_v1"
        ),
        "status": "continuation_authority_materialized_pending_independent_review",
        "authority_sha256": AUTHORITY_SHA256,
        "continuation_preimage": preimage,
        "continuation_sha256": continuation_sha,
        "multiroute_v2_exact_dir_prefix": (
            "/root/autodl-tmp/camp_dp_v25_industrial_v3_multiroute_v2_"
            f"{git_head()[:8]}_{continuation_sha[:8]}_"
        ),
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
        "implementation_head": git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
        "interpreter": _interpreter(),
    }
    return write_atomic(
        output,
        report,
        {
            "role": "project_authored_multiroute_continuation_authority",
            "authority_sha256": AUTHORITY_SHA256,
            "continuation_sha256": continuation_sha,
            "implementation_head": git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        label="V25 project-authored multiroute continuation authority",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="stage", required=True)
    contract = sub.add_parser("contract")
    contract.add_argument("--output", type=Path, required=True)
    materialization = sub.add_parser("materialization")
    materialization.add_argument("--output", type=Path, required=True)
    continuation = sub.add_parser("continuation")
    continuation.add_argument("--output", type=Path, required=True)
    for target in (materialization, continuation):
        target.add_argument("--contract-dir", type=Path, required=True)
        target.add_argument("--contract-root", required=True)
        target.add_argument("--contract-review-dir", type=Path, required=True)
        target.add_argument("--contract-review-root", required=True)
    for name in ("materialization-dir", "materialization-review-dir"):
        continuation.add_argument("--" + name, type=Path, required=True)
    for name in ("materialization-root", "materialization-review-root"):
        continuation.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.stage == "contract":
        root = freeze_contract(args.output)
    elif args.stage == "materialization":
        root = materialize(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
        )
    else:
        root = freeze_continuation(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
            materialization_dir=args.materialization_dir,
            materialization_root=args.materialization_root,
            materialization_review_dir=args.materialization_review_dir,
            materialization_review_root=args.materialization_review_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
