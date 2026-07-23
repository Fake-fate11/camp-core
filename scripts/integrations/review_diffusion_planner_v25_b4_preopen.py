#!/usr/bin/env python3
"""Independently rebuild and review the sealed Fresh B4 pre-open authority."""

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
    validate_b3_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_b4_preopen import (
    FIXED_DP_HEAD,
    build_b4_preopen_authority,
    validate_b4_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (
    canonical_json_bytes,
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    strict_equal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (
    operational_identity_path,
    scientific_identity_path,
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


SCHEMA_VERSION = "camp_dp_v25_fresh_b4_preopen_independent_review_v1"
CAS_ROOT = Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas")


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
        source, source_root_sha256, label="Fresh B4 pre-open"
    )
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B4 pre-open did not pass")
    paths = set(seal["manifest_paths"])
    fixed = {
        "COMMAND",
        "HEADS",
        "fresh_b4_execution_plan.json",
        "fresh_b4_map_suite.json",
        "fresh_b4_prepared_runtime_cases.json",
        "fresh_b4_route_assets.json",
        "preopen_authority.json",
        "report.json",
        "run.exit",
    }
    maps = {path for path in paths if path.startswith("maps/")}
    route_files = {
        path for path in paths if path.startswith("route_materialization/")
    }
    if paths != fixed | maps | route_files or len(maps) != 25:
        raise ValueError("Fresh B4 pre-open inventory drifted")
    stored = validate_b4_preopen_authority(
        _canonical_object(source / "preopen_authority.json")
    )
    suite_full = build_signal_complete_suite("fresh_b4")
    suite_receipt = validate_signal_complete_suite(suite_full)
    if not strict_equal(
        _canonical_object(source / "fresh_b4_map_suite.json"),
        suite_receipt,
    ):
        raise ValueError("Fresh B4 map suite receipt drifted")
    for relative, payload in suite_full["map_payloads"].items():
        path = source / "maps" / relative
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise ValueError(f"Fresh B4 map payload drifted: {relative}")
    plan = build_signal_complete_execution_plan("fresh_b4")
    if not strict_equal(
        _canonical_object(source / "fresh_b4_execution_plan.json"), plan
    ):
        raise ValueError("Fresh B4 execution plan drifted")
    route_class, _route_source = _route_class(
        Path("/root/autodl-tmp/Diffusion-Planner")
    )
    route_manifest = validate_signal_complete_route_assets(
        _canonical_object(source / "fresh_b4_route_assets.json"),
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
        raise ValueError("Fresh B4 route materialization drifted")
    prepared = [
        build_signal_complete_runtime_case(
            identity,
            map_artifact=source / "maps",
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    ]
    if not strict_equal(
        _canonical_value(source / "fresh_b4_prepared_runtime_cases.json"),
        prepared,
    ):
        raise ValueError("Fresh B4 prepared runtime cases drifted")

    bindings = stored["upstream_bindings"]
    for role, binding in bindings.items():
        verify_complete_seal(
            Path(binding["path"]),
            binding["root_sha256"],
            label=f"Fresh B4 upstream {role}",
        )
    train_source = _strict_external_object(
        Path(bindings["train_route_source"]["path"])
        / "route_signal_source_receipts.json"
    )
    if train_source.get("source_failures") != []:
        raise ValueError("Fresh B4 train source failures drifted")
    prior = validate_b3_preopen_authority(
        _canonical_object(
            Path(bindings["accepted_b3_preopen"]["path"])
            / "preopen_authority.json"
        )
    )
    b2_closeout = _canonical_object(
        Path(bindings["b2_consumed_failure"]["path"]) / "closeout.json"
    )
    b2_review = _canonical_object(
        Path(bindings["b2_consumed_failure_review"]["path"]) / "report.json"
    )
    b3_closeout = _canonical_object(
        Path(bindings["b3_terminal_closeout"]["path"]) / "closeout.json"
    )
    b3_review = _canonical_object(
        Path(bindings["b3_terminal_closeout_review"]["path"]) / "report.json"
    )
    certificate = _canonical_object(
        Path(bindings["production_equivalence_certificate"]["path"])
        / "preflight.json"
    )
    certificate_review = _canonical_object(
        Path(bindings["production_equivalence_certificate_review"]["path"])
        / "report.json"
    )
    storage = _canonical_object(
        Path(bindings["storage"]["path"]) / "storage_manifest.json"
    )
    identity_sha = stored["holdout_identity"]["holdout_identity_sha256"]
    operational_exists = operational_identity_path(
        CAS_ROOT, identity_sha
    ).exists()
    scientific_exists = scientific_identity_path(CAS_ROOT, identity_sha).exists()
    expected = build_b4_preopen_authority(
        implementation_head=_git_head(),
        critical_implementation_manifest=tracked_implementation_manifest(ROOT),
        upstream_bindings=bindings,
        train_source_rows=train_source["cases"],
        calibration_plan=build_signal_complete_execution_plan("calibration"),
        b2_plan=build_signal_complete_execution_plan("fresh_b2"),
        b3_plan=build_signal_complete_execution_plan("fresh_b3"),
        b4_suite=suite_full,
        b4_plan=plan,
        b4_map_artifact=source / "maps",
        route_asset_manifest=route_manifest,
        license_sha256=_sha256(ROOT / "LICENSE"),
        prepared_runtime_cases=prepared,
        prior_experiment_protocol=prior["experiment_protocol"],
        b2_consumed_failure=b2_closeout,
        b2_consumed_failure_review=b2_review,
        b3_terminal_closeout=b3_closeout,
        b3_terminal_closeout_review=b3_review,
        production_equivalence_certificate=certificate,
        production_equivalence_certificate_review=certificate_review,
        power=prior["power"],
        evaluation=prior["evaluation"],
        storage_manifest=storage,
        atom_mechanism_binding=bindings["atom_mechanism"],
        atom_mechanism_review_binding=bindings["atom_mechanism_review"],
        free_bytes_before=stored["capacity"]["free_bytes_before"],
        output_parent=Path(stored["capacity"]["canonical_output_parent"]),
        operational_attempt_exists=operational_exists,
        scientific_ledger_exists=scientific_exists,
    )
    if not strict_equal(stored, expected):
        raise ValueError("Fresh B4 pre-open differs from independent rebuild")
    report = _canonical_object(source / "report.json")
    if (
        report.get("status")
        != "passed_outcome_blind_fresh_b4_preopen_materialization"
        or report.get("camp_head") != _git_head()
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("holdout_identity_sha256") != identity_sha
        or report.get("prior_holdout_raw_values_used") is not False
        or report.get("operational_attempt_exists") is not False
        or report.get("scientific_ledger_exists") is not False
        or report.get("fresh_b4_opened") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B4 pre-open report drifted")
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_fresh_b4_preopen_review",
        "reviewed_root_sha256": source_root_sha256,
        "implementation_head": _git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
        "holdout_identity_sha256": identity_sha,
        "experiment_protocol_sha256": stored["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "critical_implementation_manifest_sha256": stored[
            "critical_implementation_manifest"
        ]["manifest_sha256"],
        "actual_native_receipt_contract_sha256": stored[
            "actual_native_receipt_contract"
        ]["contract_sha256"],
        "map_count": 25,
        "route_count": 100,
        "paired_unit_count": 500,
        "arm_run_count": 1500,
        "tick_capacity": 96_000,
        "train_cal_b1_b2_b3_b4_zero_overlap": True,
        "prior_holdout_raw_values_used": False,
        "production_equivalence_certificate_reviewed": True,
        "operational_attempt_exists": False,
        "scientific_ledger_exists": False,
        "storage_capacity_passed": True,
        "fresh_open_authorized": False,
        "nonce_created": False,
        "fresh_b4_opened": False,
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
        output, label="independent V25 Fresh B4 consolidated pre-open review"
    )


def _canonical_object(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"canonical object required: {path}")
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
