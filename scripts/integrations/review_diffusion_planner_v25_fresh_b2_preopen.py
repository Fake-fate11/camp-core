#!/usr/bin/env python3
"""Independently review the consolidated unopened V25 Fresh-B2 authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_calibration_preregistration import (  # noqa: E402
    validate_paired_calibration_preregistration,
)
from camp_core.integrations.diffusion_planner_v25_fresh_coverage import (  # noqa: E402
    build_fresh_b2_explicit_coverage,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    FIXED_DP_HEAD,
    canonical_json_bytes,
    fresh_power_at_corridor_ceiling,
    project_train_split_rows,
    tracked_implementation_manifest,
    validate_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_fresh_storage import (  # noqa: E402
    validate_storage_manifest,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (  # noqa: E402
    build_signal_complete_suite,
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_preopen import (  # noqa: E402
    project_fresh_b2_qualification_rows,
    project_signal_complete_split_rows,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)
from camp_core.integrations.diffusion_planner_v25_split import (  # noqa: E402
    validate_signal_complete_map_license,
    validate_v25_zero_overlap,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_preopen_independent_review_v1"


def review(artifact: Path, root_sha256: str) -> dict[str, Any]:
    root = artifact.resolve()
    seal = verify_complete_seal(root, root_sha256, label="Fresh B2 pre-open materialization")
    paths = set(seal["manifest_paths"])
    required = {
        "COMMAND",
        "HEADS",
        "accepted_evaluation_preregistration.json",
        "fresh_b2_execution_plan.json",
        "fresh_b2_map_suite.json",
        "fresh_b2_prepared_runtime_cases.json",
        "preopen_authority.json",
        "report.json",
        "run.exit",
    }
    map_paths = {name for name in paths if name.startswith("maps/")}
    if paths != required | map_paths or len(map_paths) != 25 or (root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B2 pre-open inventory/exit drifted")
    report = _canonical_json(root / "report.json")
    authority = validate_preopen_authority(_canonical_json(root / "preopen_authority.json"))
    heads = _heads(root)
    if (
        report.get("status") != "passed_outcome_blind_fresh_b2_preopen_materialization"
        or report.get("camp_head") != heads["camp_head"]
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or authority["implementation_head"] != heads["camp_head"]
        or report.get("preopen_authority_sha256") != _sha256(root / "preopen_authority.json")
        or report.get("fresh_open_authorized") is not False
        or report.get("nonce_created") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B2 pre-open report authority drifted")

    expected_suite = build_signal_complete_suite("fresh_b2")
    expected_suite_receipt = validate_signal_complete_suite(expected_suite)
    stored_suite = _canonical_json(root / "fresh_b2_map_suite.json")
    if not _strict_equal(stored_suite, expected_suite_receipt):
        raise ValueError("Fresh B2 map suite differs from independent reconstruction")
    for relative, payload in expected_suite["map_payloads"].items():
        path = root / "maps" / relative
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise ValueError(f"Fresh B2 materialized map bytes drifted: {relative}")

    plan = build_signal_complete_execution_plan("fresh_b2")
    if not _strict_equal(_canonical_json(root / "fresh_b2_execution_plan.json"), plan):
        raise ValueError("Fresh B2 execution plan differs from reconstruction")
    prepared = [
        build_signal_complete_runtime_case(
            identity,
            map_artifact=root / "maps",
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    ]
    stored_prepared = _canonical_value(root / "fresh_b2_prepared_runtime_cases.json")
    if not _strict_equal(stored_prepared, prepared):
        raise ValueError("Fresh B2 prepared static source cases differ from reconstruction")
    expected_rows = project_fresh_b2_qualification_rows(
        plan,
        prepared_runtime_cases=prepared,
    )
    if not _strict_equal(authority["qualification_rows"], expected_rows):
        raise ValueError("Fresh B2 qualification rows differ from reconstruction")
    expected_coverage = build_fresh_b2_explicit_coverage(
        plan,
        prepared_runtime_cases=prepared,
    )
    if not _strict_equal(authority["explicit_coverage"], expected_coverage):
        raise ValueError("Fresh B2 explicit coverage differs from reconstruction")

    bindings = authority["upstream_bindings"]
    for role, binding in bindings.items():
        path = Path(binding["path"])
        verify_complete_seal(path, binding["root_sha256"], label=f"Fresh B2 review {role}")
    source = _canonical_json(
        Path(bindings["train_route_source"]["path"]) / "route_signal_source_receipts.json"
    )
    train_rows = project_train_split_rows(source["cases"])
    split_rows = (
        train_rows
        + project_signal_complete_split_rows(build_signal_complete_execution_plan("calibration"))
        + project_signal_complete_split_rows(plan)
    )
    overlap = validate_v25_zero_overlap(split_rows)
    if not _strict_equal(authority["zero_overlap_receipt"], overlap):
        raise ValueError("Fresh B2 train/cal/Fresh zero-overlap receipt drifted")
    validate_signal_complete_map_license(authority["map_license_rows"])

    prereg_source = Path(bindings["calibration_preregistration"]["path"]) / "preregistration.json"
    prereg_raw = prereg_source.read_bytes()
    prereg_copy = (root / "accepted_evaluation_preregistration.json").read_bytes()
    if prereg_copy != prereg_raw:
        raise ValueError("Fresh B2 evaluation preregistration is not byte-exact")
    prereg = validate_paired_calibration_preregistration(_canonical_json(prereg_source))
    if authority["evaluation"]["accepted_preregistration_sha256"] != _sha256(prereg_source):
        raise ValueError("Fresh B2 evaluation root differs from accepted preregistration")
    if prereg["calibration_result_driven_protocol_change_authorized"] is not False:
        raise ValueError("Fresh B2 evaluation was changed from calibration results")

    calibration_analysis = _canonical_json(
        Path(bindings["calibration_recovery"]["path"]) / "calibration_analysis.json"
    )
    expected_power = fresh_power_at_corridor_ceiling(calibration_analysis, corridor_count=100)
    if not _strict_equal(authority["power"], expected_power):
        raise ValueError("Fresh B2 prospective power differs from accepted calibration variance")
    expected_manifest = tracked_implementation_manifest(ROOT)
    if not _strict_equal(authority["critical_implementation_manifest"], expected_manifest):
        raise ValueError("Fresh B2 tracked implementation manifest drifted")

    mechanism = authority["atom_mechanism"]
    mechanism_artifact = Path(mechanism["artifact_path"])
    mechanism_review_artifact = Path(mechanism["review_artifact_path"])
    verify_complete_seal(
        mechanism_artifact,
        mechanism["artifact_root_sha256"],
        label="Fresh B2 atom-mechanism authority",
    )
    verify_complete_seal(
        mechanism_review_artifact,
        mechanism["review_root_sha256"],
        label="Fresh B2 atom-mechanism independent review",
    )
    if (
        (mechanism_artifact / "run.exit").read_bytes() != b"0\n"
        or (mechanism_review_artifact / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("Fresh B2 atom-mechanism terminal state drifted")
    mechanism_report = _canonical_json(mechanism_artifact / "report.json")
    mechanism_review = _canonical_json(mechanism_review_artifact / "report.json")
    if (
        mechanism_report.get("status")
        != "frozen_atom_mechanism_ready_before_fresh_b2_opening"
        or mechanism_report.get("contract_sha256") != mechanism["contract_sha256"]
        or mechanism_report.get("calibration_atom_mechanism_sha256")
        != mechanism["analysis_sha256"]
        or mechanism_review.get("status")
        != "passed_independent_atom_mechanism_preopen_review"
        or mechanism_review.get("reviewed_root_sha256")
        != mechanism["artifact_root_sha256"]
        or mechanism_review.get("single_atom_closed_loop_causal_effect_claimed")
        is not False
        or mechanism_review.get("primary_fresh_design_changed") is not False
        or mechanism_review.get("fresh_b2_opened") is not False
        or mechanism_review.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B2 atom-mechanism cross-binding drifted")

    storage = validate_storage_manifest(authority["storage"])
    capacity = authority["capacity"]
    free_now = shutil.disk_usage(Path(capacity["canonical_output_parent"])).free
    if free_now - storage["metrics"]["projected_1500_arm_upper_bound_nbytes"] < 10 * 1024**3:
        raise ValueError("Fresh B2 live capacity no longer preserves the 10GiB floor")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_outcome_blind_fresh_b2_preopen_review",
        "reviewed_artifact": str(root),
        "reviewed_root_sha256": seal["root_sha256"],
        "implementation_head": heads["camp_head"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "critical_implementation_manifest_sha256": expected_manifest["manifest_sha256"],
        "map_count": 25,
        "route_count": 100,
        "paired_unit_count": 500,
        "arm_run_count": 1500,
        "tick_capacity": 96_000,
        "static_signal_chain_qualified_count": 100,
        "zero_overlap_status": overlap["status"],
        "storage_logical_tree_sha256": storage["logical_tree_sha256"],
        "projected_1500_arm_upper_bound_nbytes": storage["metrics"]["projected_1500_arm_upper_bound_nbytes"],
        "free_bytes_at_review": free_now,
        "atom_mechanism_artifact_root_sha256": mechanism["artifact_root_sha256"],
        "atom_mechanism_review_root_sha256": mechanism["review_root_sha256"],
        "atom_mechanism_decision_tick_count": mechanism["decision_tick_count"],
        "atom_mechanism_primary_fresh_design_changed": False,
        "atom_mechanism_single_atom_closed_loop_causal_effect_claimed": False,
        "fresh_open_authorized": False,
        "one_time_opening_release_required": True,
        "nonce_created": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _heads(root: Path) -> dict[str, str]:
    lines = (root / "HEADS").read_bytes().decode("ascii").splitlines()
    values = dict(line.split("=", 1) for line in lines if "=" in line)
    if set(values) != {"camp_head", "fixed_dp_head"} or values["fixed_dp_head"] != FIXED_DP_HEAD:
        raise ValueError("Fresh B2 pre-open HEADS drifted")
    return values


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_no_duplicate_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"authority JSON object expected: {path}")
    return value


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    report = review(args.artifact, args.root_sha256)
    output.mkdir(parents=True)
    _write_json(output / "report.json", report)
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
    (output / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(output, label="V25 Fresh B2 consolidated pre-open independent review")
    print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
