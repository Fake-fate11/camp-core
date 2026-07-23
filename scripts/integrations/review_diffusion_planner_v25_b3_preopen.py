#!/usr/bin/env python3
"""Independently rebuild and review the sealed Fresh B3 pre-open authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_b3_preopen import (
    FIXED_DP_HEAD,
    build_b3_preopen_authority,
    validate_b3_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (
    canonical_json_bytes,
    project_train_split_rows,
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    strict_equal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_protocol import (
    derive_protocol_assets_from_accepted_preopen,
    validate_protocol_assets_receipt,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_runtime_case,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_routes import (
    validate_signal_complete_route_assets,
)
from scripts.integrations.materialize_diffusion_planner_v25_signal_complete_routes import (
    _route_class,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b3_preopen_independent_review_v1"


def review(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    output_dir: Path,
) -> str:
    source = source_artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        source, source_root_sha256, label="Fresh B3 pre-open"
    )
    paths = set(seal["manifest_paths"])
    fixed = {
        "COMMAND",
        "HEADS",
        "accepted_evaluation_preregistration.json",
        "fresh_b3_execution_plan.json",
        "fresh_b3_route_assets.json",
        "fresh_b3_map_suite.json",
        "fresh_b3_prepared_runtime_cases.json",
        "preopen_authority.json",
        "report.json",
        "run.exit",
    }
    maps = {path for path in paths if path.startswith("maps/")}
    route_files = {
        path for path in paths if path.startswith("route_materialization/")
    }
    if paths != fixed | maps | route_files or len(maps) != 25:
        raise ValueError("Fresh B3 pre-open inventory drifted")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B3 pre-open did not pass")
    stored = validate_b3_preopen_authority(
        _canonical_object(source / "preopen_authority.json")
    )
    suite_full = build_signal_complete_suite("fresh_b3")
    suite_receipt = validate_signal_complete_suite(suite_full)
    if not strict_equal(
        _canonical_object(source / "fresh_b3_map_suite.json"),
        suite_receipt,
    ):
        raise ValueError("Fresh B3 map suite receipt drifted")
    for relative, payload in suite_full["map_payloads"].items():
        path = source / "maps" / relative
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise ValueError(f"Fresh B3 map payload drifted: {relative}")
    plan = build_signal_complete_execution_plan("fresh_b3")
    if not strict_equal(
        _canonical_object(source / "fresh_b3_execution_plan.json"), plan
    ):
        raise ValueError("Fresh B3 execution plan drifted")
    route_class, _route_source = _route_class(
        Path("/root/autodl-tmp/Diffusion-Planner")
    )
    route_manifest = validate_signal_complete_route_assets(
        _canonical_object(source / "fresh_b3_route_assets.json"),
        plan=plan,
        map_artifact=source / "maps",
        route_class=route_class,
    )
    if (
        not route_files
        or not strict_equal(
            _canonical_object(
                source / "route_materialization" / "route_assets.json"
            ),
            route_manifest,
        )
        or not strict_equal(stored["route_assets"], route_manifest)
    ):
        raise ValueError("Fresh B3 route materialization drifted")
    prepared = [
        build_signal_complete_runtime_case(
            identity,
            map_artifact=source / "maps",
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    ]
    if not strict_equal(
        _canonical_value(source / "fresh_b3_prepared_runtime_cases.json"),
        prepared,
    ):
        raise ValueError("Fresh B3 prepared runtime cases drifted")
    bindings = stored["upstream_bindings"]
    for role, binding in bindings.items():
        verify_complete_seal(
            Path(binding["path"]),
            binding["root_sha256"],
            label=f"Fresh B3 upstream {role}",
        )
    train_source = _strict_external_object(
        Path(bindings["train_route_source"]["path"])
        / "route_signal_source_receipts.json"
    )
    if train_source.get("source_failures") != []:
        raise ValueError("Fresh B3 train source failures drifted")
    b2_closeout = _canonical_object(
        Path(bindings["b2_consumed_failure"]["path"]) / "closeout.json"
    )
    b2_review = _canonical_object(
        Path(bindings["b2_consumed_failure_review"]["path"]) / "report.json"
    )
    preflight = _canonical_object(
        Path(bindings["production_composition_preflight"]["path"])
        / "preflight.json"
    )
    preflight_outer_review = _canonical_object(
        Path(bindings["production_composition_preflight_review"]["path"])
        / "report.json"
    )
    storage = _canonical_object(
        Path(bindings["storage"]["path"]) / "storage_manifest.json"
    )
    old_b2 = _canonical_object(
        Path(bindings["accepted_b2_preopen"]["path"])
        / "preopen_authority.json"
    )
    protocol_receipt = validate_protocol_assets_receipt(
        _canonical_object(
            Path(bindings["production_composition_preflight"]["path"])
            / "protocol_assets_receipt.json"
        )
    )
    protocol_assets, independently_derived_receipt = (
        derive_protocol_assets_from_accepted_preopen(
            preopen_artifact=Path(
                bindings["accepted_b2_preopen"]["path"]
            ),
            preopen_root_sha256=bindings["accepted_b2_preopen"][
                "root_sha256"
            ],
            preopen_review_artifact=Path(
                bindings["accepted_b2_preopen_review"]["path"]
            ),
            preopen_review_root_sha256=bindings[
                "accepted_b2_preopen_review"
            ]["root_sha256"],
        )
    )
    if not strict_equal(protocol_receipt, independently_derived_receipt):
        raise ValueError("Fresh B3 protocol provenance receipt drifted")
    if any(
        stored["experiment_protocol"][name] != expected
        for name, expected in protocol_assets.items()
    ):
        raise ValueError("Fresh B3 experiment protocol asset binding drifted")
    cas_path = (
        Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas")
        / (
            stored["holdout_identity"]["holdout_identity_sha256"]
            + ".json"
        )
    )
    if cas_path.exists():
        raise ValueError("Fresh B3 holdout identity was already reserved")
    expected = build_b3_preopen_authority(
        implementation_head=_git_head(),
        critical_implementation_manifest=tracked_implementation_manifest(ROOT),
        upstream_bindings=bindings,
        train_source_rows=train_source["cases"],
        calibration_plan=build_signal_complete_execution_plan("calibration"),
        b2_plan=build_signal_complete_execution_plan("fresh_b2"),
        b3_suite=suite_full,
        b3_plan=plan,
        b3_map_artifact=source / "maps",
        route_asset_manifest=route_manifest,
        license_sha256=_sha256(ROOT / "LICENSE"),
        prepared_runtime_cases=prepared,
        protocol_assets=protocol_assets,
        b2_consumed_failure=b2_closeout,
        b2_consumed_failure_review=b2_review,
        production_composition_preflight=preflight,
        production_composition_preflight_review=preflight_outer_review[
            "native_composition_review"
        ],
        power=old_b2["power"],
        evaluation=old_b2["evaluation"],
        storage_manifest=storage,
        storage_binding=bindings["storage"],
        storage_review_binding=bindings["storage_review"],
        atom_mechanism_binding=bindings["atom_mechanism"],
        atom_mechanism_review_binding=bindings["atom_mechanism_review"],
        free_bytes_before=stored["capacity"]["free_bytes_before"],
        output_parent=Path(
            stored["capacity"]["canonical_output_parent"]
        ),
        cas_tombstone_exists=False,
    )
    if not strict_equal(stored, expected):
        raise ValueError("Fresh B3 pre-open differs from independent rebuild")
    report = _canonical_object(source / "report.json")
    if (
        report.get("status")
        != "passed_outcome_blind_fresh_b3_preopen_materialization"
        or report.get("camp_head") != _git_head()
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("holdout_identity_sha256")
        != stored["holdout_identity"]["holdout_identity_sha256"]
        or report.get("experiment_protocol_sha256")
        != stored["experiment_protocol"]["experiment_protocol_sha256"]
        or report.get("b2_raw_outcome_values_used") is not False
        or report.get("b2_complete_paired_rows_used") != 0
        or report.get("fresh_b3_opened") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B3 pre-open report drifted")
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_fresh_b3_preopen_review",
        "reviewed_root_sha256": source_root_sha256,
        "implementation_head": _git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
        "holdout_identity_sha256": stored["holdout_identity"][
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": stored["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "critical_implementation_manifest_sha256": stored[
            "critical_implementation_manifest"
        ]["manifest_sha256"],
        "map_count": 25,
        "route_count": 100,
        "paired_unit_count": 500,
        "arm_run_count": 1500,
        "tick_capacity": 96_000,
        "train_cal_b1_b2_b3_zero_overlap": True,
        "b2_raw_outcome_values_used": False,
        "b2_complete_paired_rows_used": 0,
        "production_preflight_reviewed": True,
        "persistent_b2_tombstone_reviewed": True,
        "storage_capacity_passed": True,
        "fresh_open_authorized": False,
        "nonce_created": False,
        "fresh_b3_opened": False,
        "outcome_fields_consumed": [],
    }
    output.mkdir(parents=True)
    (output / "report.json").write_bytes(canonical_json_bytes(result))
    (output / "HEADS").write_bytes(
        (
            f"camp_head={result['implementation_head']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes(
        (" ".join(sys.argv) + "\n").encode("utf-8")
    )
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(
        output, label="independent V25 Fresh B3 consolidated pre-open review"
    )


def _canonical_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = _parse(raw, path)
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = _parse(raw, path)
    if raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _strict_external_object(path: Path) -> dict[str, Any]:
    value = _parse(path.read_bytes(), path)
    if type(value) is not dict:
        raise ValueError(f"sealed external JSON object required: {path}")
    return value


def _parse(raw: bytes, path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(
        source_artifact=args.source_artifact,
        source_root_sha256=args.source_root_sha256,
        output_dir=args.output_dir,
    )
    print(root)


if __name__ == "__main__":
    main()
