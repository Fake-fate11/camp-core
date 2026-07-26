"""Separate-role artifact review for the project-authored source stage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "camp_core", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_project_authored_multiroute_source_review import (  # noqa: E402
    AUTHORITY_SHA256,
    BASE_HEAD,
    FIXED_DP_HEAD,
    OVERLAP_LEVELS,
    review_contract_literal,
    review_materialization_literal,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    canonical_bytes,
    git_head,
    object_from,
    write_atomic,
)


AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"
EXACT_DIRS = {
    "contract_review": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_contract_review"
    ),
    "materialization_review": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_materialization_review"
    ),
    "continuation_authority_review": (
        "/root/autodl-tmp/camp_dp_v25_project_authored_multiroute_"
        "source_dea1a0a6_9315b09b_continuation_authority_review"
    ),
}
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
    "materializer": (
        ROOT
        / "scripts/integrations/"
        "freeze_diffusion_planner_v25_project_authored_multiroute_source.py"
    ),
    "artifact_reviewer": Path(__file__).resolve(),
    "tests": (
        ROOT
        / "camp_core/tests/"
        "test_diffusion_planner_v25_project_authored_multiroute_source.py"
    ),
}


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _interpreter() -> dict[str, Any]:
    return {
        "sys_executable": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "sys_prefix": sys.prefix,
        "minimum_version_passed": sys.version_info >= (3, 10),
        "autodl_exact_interpreter_passed": sys.executable == AUTODL_INTERPRETER,
    }


def _require_runtime() -> None:
    value = _interpreter()
    if (
        value["minimum_version_passed"] is not True
        or value["autodl_exact_interpreter_passed"] is not True
    ):
        raise RuntimeError("source independent review requires exact AutoDL dp312")


def _walk(value: Any, prefix: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    if type(value) is dict:
        for key, item in value.items():
            yield from _walk(item, prefix + (str(key),))
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _walk(item, prefix + (str(index),))
    else:
        yield prefix, value


def _extract(values: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    result = {level: set() for level in OVERLAP_LEVELS}
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
                result["seed"].add(_digest({"seed": item}))
    return {level: sorted(items) for level, items in result.items()}


def _review_forbidden() -> dict[str, Any]:
    result = {}
    for authority, sources in FORBIDDEN_SOURCES.items():
        values = []
        bindings = []
        for path, root in sources:
            verify_complete_seal(path, root, label=f"review forbidden {authority}")
            for file_path in sorted(path.rglob("*.json")):
                if file_path.stat().st_size > 100_000_000:
                    raise RuntimeError("review forbidden JSON unexpectedly large")
                value = json.loads(file_path.read_text(encoding="utf-8"))
                if type(value) is dict:
                    values.append(value)
            bindings.append({"path": str(path), "root_sha256": root})
        layers = _extract(values)
        result[authority] = {
            "bindings": bindings,
            "layers": layers,
            "layer_counts": {key: len(value) for key, value in layers.items()},
            "inventory_sha256": _digest(layers),
        }
    return result


def review_contract_artifact(
    output: Path, *, contract_dir: Path, contract_root: str
) -> str:
    _require_runtime()
    if output != Path(EXACT_DIRS["contract_review"]):
        raise ValueError("source contract review exact dir drifted")
    verify_complete_seal(contract_dir, contract_root, label="source contract")
    for label, (path, root) in PARENT_ARTIFACTS.items():
        verify_complete_seal(path, root, label=f"review {label}")
    source = object_from(contract_dir / "report.json")
    reviewed = review_contract_literal(source["contract"])
    actual_files = {
        name: _file_sha(path) for name, path in IMPLEMENTATION_FILES.items()
    }
    if (
        source.get("implementation_head") != git_head()
        or source.get("implementation_file_sha256") != actual_files
        or source.get("model_pool_selector_calls") != 0
        or source.get("outcome_values_read") is not False
    ):
        raise ValueError("source contract implementation binding drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_project_authored_multiroute_source_contract_review_v1"
        ),
        "status": "passed_independent_literal_source_contract_review",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "contract_sha256": _digest(reviewed),
        "implementation_file_sha256": actual_files,
        "reviewer_imported_source_producer": False,
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
            "role": "project_authored_multiroute_source_contract_review",
            "authority_sha256": AUTHORITY_SHA256,
            "contract_root_sha256": contract_root,
            "implementation_head": git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        label="V25 project-authored multiroute source contract review",
    )


def review_materialization_artifact(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    materialization_dir: Path,
    materialization_root: str,
) -> str:
    _require_runtime()
    if output != Path(EXACT_DIRS["materialization_review"]):
        raise ValueError("source materialization review exact dir drifted")
    for path, root, label in (
        (contract_dir, contract_root, "source contract"),
        (contract_review_dir, contract_review_root, "source contract review"),
        (materialization_dir, materialization_root, "source materialization"),
    ):
        verify_complete_seal(path, root, label=label)
    records = object_from(materialization_dir / "source_records.json")["records"]
    candidates = object_from(materialization_dir / "candidates.json")["candidates"]
    selected = object_from(materialization_dir / "selected_manifest.json")
    producer_forbidden = object_from(
        materialization_dir / "forbidden_inventories.json"
    )
    local_forbidden = _review_forbidden()
    if producer_forbidden != local_forbidden:
        raise ValueError("source forbidden inventory was not independently reproduced")
    maps = {
        record["map"]["relative_path"]: (
            materialization_dir / record["map"]["relative_path"]
        ).read_bytes()
        for record in records
    }
    reviewed = review_materialization_literal(
        records=records,
        maps=maps,
        candidates=candidates,
        selected_manifest=selected,
        contract_root_sha256=contract_root,
        forbidden={
            authority: value["layers"]
            for authority, value in local_forbidden.items()
        },
    )
    source = object_from(materialization_dir / "report.json")
    if (
        source.get("materialized_candidate_count") != 252
        or source.get("selected_count") != 100
        or source.get("selected_manifest_sha256")
        != selected.get("manifest_sha256")
        or source.get("model_pool_selector_calls") != 0
        or source.get("outcome_values_read") is not False
    ):
        raise ValueError("source materialization summary drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_project_authored_multiroute_source_materialization_review_v1"
        ),
        "status": "passed_independent_project_authored_source_review",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "materialization_root_sha256": materialization_root,
        "reviewed": reviewed,
        "selected_manifest_sha256": selected["manifest_sha256"],
        "forbidden_inventory_sha256": {
            authority: value["inventory_sha256"]
            for authority, value in local_forbidden.items()
        },
        "reviewer_imported_source_producer": False,
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
            "role": "project_authored_multiroute_source_materialization_review",
            "authority_sha256": AUTHORITY_SHA256,
            "materialization_root_sha256": materialization_root,
            "selected_manifest_sha256": selected["manifest_sha256"],
            "implementation_head": git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        label="V25 project-authored multiroute source materialization review",
    )


def review_continuation_artifact(
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
    continuation_dir: Path,
    continuation_root: str,
) -> str:
    _require_runtime()
    if output != Path(EXACT_DIRS["continuation_authority_review"]):
        raise ValueError("continuation review exact dir drifted")
    for path, root, label in (
        (contract_dir, contract_root, "source contract"),
        (contract_review_dir, contract_review_root, "source contract review"),
        (materialization_dir, materialization_root, "source materialization"),
        (
            materialization_review_dir,
            materialization_review_root,
            "source materialization review",
        ),
        (continuation_dir, continuation_root, "source continuation authority"),
    ):
        verify_complete_seal(path, root, label=label)
    continuation = object_from(continuation_dir / "report.json")
    parent = object_from(PARENT_ARTIFACTS["parent_contract"][0] / "report.json")[
        "contract"
    ]
    materialization = object_from(materialization_dir / "report.json")
    expected = {
        "parent_source_authority_sha256": AUTHORITY_SHA256,
        "source_contract_root": contract_root,
        "source_contract_review_root": contract_review_root,
        "source_materialization_root": materialization_root,
        "source_materialization_review_root": materialization_review_root,
        "selected_manifest_sha256": materialization[
            "selected_manifest_sha256"
        ],
        "implementation_head": git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
        "parent_b5ca_authority_sha256": (
            "b5ca942b4a91c0ef0cbe4e9ff8180852fb193471fb9f73514f6017622547718f"
        ),
        "all_unchanged_b5ca_scientific_contract_fields": parent,
    }
    expected_sha = _digest(expected)
    if (
        continuation.get("continuation_preimage") != expected
        or continuation.get("continuation_sha256") != expected_sha
        or continuation.get("model_pool_selector_calls") != 0
        or continuation.get("outcome_values_read") is not False
    ):
        raise ValueError("continuation authority preimage drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_project_authored_multiroute_continuation_review_v1"
        ),
        "status": "passed_independent_continuation_authority_review",
        "authority_sha256": AUTHORITY_SHA256,
        "continuation_root_sha256": continuation_root,
        "continuation_sha256": expected_sha,
        "selected_manifest_sha256": materialization[
            "selected_manifest_sha256"
        ],
        "parent_b5ca_contract_unchanged": True,
        "reviewer_imported_source_producer": False,
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
            "role": "project_authored_multiroute_continuation_review",
            "authority_sha256": AUTHORITY_SHA256,
            "continuation_root_sha256": continuation_root,
            "continuation_sha256": expected_sha,
            "implementation_head": git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        label="V25 project-authored multiroute continuation authority review",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="stage", required=True)
    contract = sub.add_parser("contract")
    contract.add_argument("--output", type=Path, required=True)
    contract.add_argument("--contract-dir", type=Path, required=True)
    contract.add_argument("--contract-root", required=True)
    materialization = sub.add_parser("materialization")
    materialization.add_argument("--output", type=Path, required=True)
    continuation = sub.add_parser("continuation")
    continuation.add_argument("--output", type=Path, required=True)
    for target in (materialization, continuation):
        for name in ("contract-dir", "contract-review-dir", "materialization-dir"):
            target.add_argument("--" + name, type=Path, required=True)
        for name in ("contract-root", "contract-review-root", "materialization-root"):
            target.add_argument("--" + name, required=True)
    for name in ("materialization-review-dir", "continuation-dir"):
        continuation.add_argument("--" + name, type=Path, required=True)
    for name in ("materialization-review-root", "continuation-root"):
        continuation.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.stage == "contract":
        root = review_contract_artifact(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
        )
    elif args.stage == "materialization":
        root = review_materialization_artifact(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
            materialization_dir=args.materialization_dir,
            materialization_root=args.materialization_root,
        )
    else:
        root = review_continuation_artifact(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
            materialization_dir=args.materialization_dir,
            materialization_root=args.materialization_root,
            materialization_review_dir=args.materialization_review_dir,
            materialization_review_root=args.materialization_review_root,
            continuation_dir=args.continuation_dir,
            continuation_root=args.continuation_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
