#!/usr/bin/env python3
"""Independently review a sealed V25 candidate0 calibration execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    FixedDpCandidateGenerationCapabilityFailure,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_calibration_corpus import (  # noqa: E402
    project_candidate0_calibration_corpus,
    validate_candidate0_calibration_corpus,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_execution import (  # noqa: E402
    build_candidate0_calibration_config,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    validate_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)


SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_execution_review_v1"
EXECUTION_SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_execution_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
STOP_LINE_GEOMETRY_ATOL_M = 1e-6
ROUTE_TANGENT_ATOL = 1e-5
ROUTE_SCALAR_ATOL_M = 2e-4


def review(
    *,
    artifact: Path,
    artifact_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    execution = artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        execution,
        artifact_root_sha256,
        label="candidate0 calibration execution",
    )
    if (execution / "run.exit").read_bytes() != b"0\n":
        raise ValueError("candidate0 calibration execution did not exit successfully")
    dp_root = dp_repo.resolve()
    if _git_head(dp_root) != FIXED_DP_HEAD or _tracked_dirty(dp_root):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")

    report = _canonical_json(execution / "report.json")
    _validate_report(report, execution=execution)
    roots = report["input_roots"]
    _verify_input_roots(roots)
    plan_root = Path(roots["plan_artifact"])
    map_root = Path(roots["map_artifact"])
    route_root = Path(roots["route_artifact"])
    plan = validate_signal_complete_execution_plan(
        _canonical_json(plan_root / "execution_plan.json")
    )
    if plan["split"] != "calibration":
        raise ValueError("reviewed execution is not the calibration split")
    probe = _legacy_json_object(
        Path(report["probe_template"]), report["probe_template_sha256"]
    )
    route_manifest = _canonical_json(route_root / "route_assets.json")
    route_rows = route_manifest.get("route_assets")
    if type(route_rows) is not list:
        raise ValueError("candidate0 route asset inventory is malformed")
    route_by_identity = {
        row["route_identity_sha256"]: dict(row["route_asset"])
        for row in route_rows
    }
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity,
            map_artifact=map_root,
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    }
    runtime_receipt_sha256_by_scenario = _bind_reviewed_runtime_receipts(
        plan=plan,
        prepared_runtime_by_scenario=prepared,
        runtime_artifact=Path(roots["runtime_artifact"]),
    )
    if not _strict_equal(
        report.get("runtime_receipt_sha256_by_scenario"),
        runtime_receipt_sha256_by_scenario,
    ):
        raise ValueError("candidate0 calibration reviewed runtime binding drifted")
    identities = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    results = _canonical_json_list(execution / "run_results.json")
    if len(results) != 100:
        raise ValueError("candidate0 calibration terminal denominator drifted")
    run_dirs = sorted((execution / "runs").iterdir())
    if len(run_dirs) != 100 or any(not path.is_dir() for path in run_dirs):
        raise ValueError("candidate0 calibration run directory denominator drifted")

    for unit, result, run_dir in zip(
        plan["execution_units"], results, run_dirs, strict=True
    ):
        expected_name = f"{unit['unit_ordinal']:04d}_{unit['unit_sha256'][:16]}"
        if run_dir.name != expected_name:
            raise ValueError("candidate0 calibration run directory order drifted")
        identity = identities[unit["scenario_identity_sha256"]]
        route_asset = route_by_identity[identity["route_identity_sha256"]]
        expected_config = build_candidate0_calibration_config(
            probe_template=probe,
            prepared_runtime=prepared[unit["scenario_identity_sha256"]],
            execution_unit=unit,
            route_asset=route_asset,
            dp_repo=dp_root,
        )
        if not _strict_equal(_canonical_json(run_dir / "run_config.json"), expected_config):
            raise ValueError("candidate0 calibration run config drifted")
        terminal = _canonical_json(run_dir / "terminal.json")
        if not _strict_equal(terminal, result):
            raise ValueError("candidate0 calibration terminal/result binding drifted")
        if result.get("status") == "complete":
            _review_complete(result, unit=unit, identity=identity, route_asset=route_asset)
        elif result.get("status") == "retained_fixed_dp_capability_failure":
            _review_failure(execution, result, unit=unit, identity=identity)
        else:
            raise ValueError("candidate0 calibration terminal status drifted")

    reconstructed = validate_candidate0_calibration_corpus(
        project_candidate0_calibration_corpus(plan, results)
    )
    recorded = validate_candidate0_calibration_corpus(
        _canonical_json(execution / "calibration_corpus.json")
    )
    if not _strict_equal(recorded, reconstructed):
        raise ValueError("candidate0 calibration corpus differs from reconstruction")
    if (
        report["run_results_sha256"] != _canonical_sha(results)
        or report["calibration_corpus_sha256"] != _canonical_sha(recorded)
        or report["terminal_run_count"] != 100
        or report["complete_run_count"] != recorded["complete_run_count"]
        or report["retained_fixed_dp_capability_failure_count"]
        != recorded["retained_fixed_dp_capability_failure_count"]
        or report["paired_eligible_rate"] != recorded["paired_eligible_rate"]
    ):
        raise ValueError("candidate0 calibration report accounting drifted")

    output.mkdir(parents=True)
    review_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_candidate0_calibration_execution_review",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(execution),
        "reviewed_root_sha256": seal["root_sha256"],
        "planned_run_count": 100,
        "terminal_run_count": 100,
        "complete_run_count": recorded["complete_run_count"],
        "retained_fixed_dp_capability_failure_count": recorded[
            "retained_fixed_dp_capability_failure_count"
        ],
        "paired_eligible_rate": recorded["paired_eligible_rate"],
        "all_configs_independently_rebuilt": True,
        "all_complete_receipts_reprojected": True,
        "all_retained_k8_failures_recomputed": True,
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "camp_method_outcomes_consumed": False,
        "training_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    _write_json(output / "report.json", review_report)
    (output / "HEADS").write_text(
        f"camp_head={review_report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 candidate0 calibration execution review")


def _validate_report(report: Mapping[str, Any], *, execution: Path) -> None:
    expected = {
        "artifact_schema_version": EXECUTION_SCHEMA_VERSION,
        "fixed_dp_head": FIXED_DP_HEAD,
        "planned_run_count": 100,
        "terminal_run_count": 100,
        "independent_reset_per_run": True,
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "camp_method_outcomes_consumed": False,
        "training_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "device": "cuda",
        "model_loaded": True,
        "candidate_generation_executed": True,
        "independent_review_completed": False,
    }
    if any(not _strict_equal(report.get(name), value) for name, value in expected.items()):
        raise ValueError("candidate0 calibration execution report contract drifted")
    if report.get("status") not in {
        "passed_candidate0_calibration_execution",
        "candidate0_calibration_execution_scientifically_ineligible",
    }:
        raise ValueError("candidate0 calibration execution status drifted")
    if type(report.get("input_roots")) is not dict:
        raise ValueError("candidate0 calibration input roots are missing")
    runtime_bindings = report.get("runtime_receipt_sha256_by_scenario")
    if (
        type(runtime_bindings) is not dict
        or len(runtime_bindings) != 100
        or any(type(key) is not str or not _sha_value(value) for key, value in runtime_bindings.items())
    ):
        raise ValueError("candidate0 calibration runtime receipt bindings are invalid")
    if not (execution / "runs").is_dir():
        raise ValueError("candidate0 calibration run inventory is missing")


def _verify_input_roots(roots: Mapping[str, Any]) -> None:
    roles = (
        "plan",
        "map",
        "route",
        "route_review",
        "runtime",
        "runtime_review",
    )
    expected_fields = {
        field for role in roles for field in (f"{role}_artifact", f"{role}_root_sha256")
    }
    if set(roots) != expected_fields:
        raise ValueError("candidate0 calibration input root field set drifted")
    for role in roles:
        artifact = Path(str(roots[f"{role}_artifact"])).resolve()
        verify_complete_seal(
            artifact,
            str(roots[f"{role}_root_sha256"]),
            label=f"candidate0 calibration {role}",
        )
        if (artifact / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"candidate0 calibration {role} run.exit drifted")
    route_review = _canonical_json(Path(roots["route_review_artifact"]) / "report.json")
    runtime_review = _canonical_json(
        Path(roots["runtime_review_artifact"]) / "report.json"
    )
    if (
        route_review.get("reviewed_root_sha256") != roots["route_root_sha256"]
        or runtime_review.get("reviewed_root_sha256") != roots["runtime_root_sha256"]
    ):
        raise ValueError("candidate0 calibration independent input review drifted")


def _review_complete(
    result: Mapping[str, Any],
    *,
    unit: Mapping[str, Any],
    identity: Mapping[str, Any],
    route_asset: Mapping[str, Any],
) -> None:
    native = result.get("native_receipt")
    if type(native) is not dict or result.get("failure_receipt") is not None:
        raise ValueError("complete candidate0 terminal evidence drifted")
    if (
        native.get("schema_version") != "v21_native_arm_receipt_v1"
        or native.get("status") != "ok"
        or native.get("arm") != "dp"
        or native.get("fixed_dp_head") != FIXED_DP_HEAD
        or native.get("route_name") != identity["route_identity_sha256"]
        or native.get("route_sha256") != route_asset["sha256"]
        or native.get("scenario_seed") != unit["seed"]
        or native.get("claim_authorized") is not False
    ):
        raise ValueError("complete candidate0 native authority drifted")
    ticks = native.get("ticks")
    if type(ticks) is not list or len(ticks) != 64:
        raise ValueError("complete candidate0 tick denominator drifted")
    for index, tick in enumerate(ticks):
        if (
            type(tick) is not dict
            or tick.get("tick_index") != index
            or tick.get("selected_index") != 0
            or tick.get("candidate0_operational_default") is not True
            or tick.get("selection_policy") != "candidate0_operational_default"
            or tick.get("score_contract") != "candidate0_operational_default"
            or tick.get("eligibility_mask_name") != "candidate0_operational_default"
            or tick.get("candidate_tensor_sha256_before")
            != tick.get("candidate_tensor_sha256_after")
        ):
            raise ValueError("complete candidate0 tick authority drifted")


def _review_failure(
    execution: Path,
    result: Mapping[str, Any],
    *,
    unit: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> None:
    summary = result.get("failure_receipt")
    if type(summary) is not dict or result.get("native_receipt") is not None:
        raise ValueError("retained K8 failure terminal evidence drifted")
    digest = summary.get("raw_failure_receipt_sha256")
    details = [
        path
        for path in (execution / "fixed_dp_capability_failures").glob("*.json")
        if _sha256(path) == digest
    ]
    if len(details) != 1:
        raise ValueError("retained K8 failure detail binding drifted")
    detail = _canonical_json(details[0])
    raw_info = detail.get("raw_preimage")
    if type(raw_info) is not dict:
        raise ValueError("retained K8 failure raw preimage is missing")
    raw_path = (execution / str(raw_info.get("relative_path"))).resolve()
    if execution not in raw_path.parents or _sha256(raw_path) != raw_info.get("file_sha256"):
        raise ValueError("retained K8 failure raw preimage drifted")
    raw = raw_path.read_bytes()
    if len(raw) != 8 * 80 * 4 * 4:
        raise ValueError("retained K8 failure raw preimage size drifted")
    candidates = np.frombuffer(raw, dtype=np.float32).copy().reshape(8, 80, 4)
    try:
        validate_fixed_k8_candidate_tensor(
            candidates,
            tick_index=detail["tick_index"],
            default_output_sha256=detail["default_output_sha256"],
            default_candidate0_identity=detail["default_candidate0_identity"],
        )
    except FixedDpCandidateGenerationCapabilityFailure as failure:
        metadata = failure.canonical_metadata()
    else:
        raise ValueError("retained K8 failure no longer reproduces")
    for name, value in metadata.items():
        if not _strict_equal(detail.get(name), value):
            raise ValueError("retained K8 failure metadata drifted")
    if (
        detail.get("scenario_identity_sha256") != identity["scenario_identity_sha256"]
        or detail.get("route_identity_sha256") != identity["route_identity_sha256"]
        or detail.get("seed") != unit["seed"]
        or summary.get("failure_class") != metadata["failure_class"]
        or summary.get("reason") != metadata["reason"]
        or summary.get("training_eligible") is not False
        or summary.get("calibration_eligible") is not False
        or summary.get("evaluation_eligible") is not False
    ):
        raise ValueError("retained K8 failure authority drifted")


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError("authority JSON must be a mapping")
    return value


def _canonical_json_list(path: Path) -> list[dict[str, Any]]:
    value = _canonical_value(path)
    if type(value) is not list or any(type(row) is not dict for row in value):
        raise ValueError("authority JSON must be a list of mappings")
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = _strict_json_value(raw)
    if raw != _canonical_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _legacy_json_object(path: Path, expected_sha256: str) -> dict[str, Any]:
    if _sha256(path) != expected_sha256:
        raise ValueError("probe template SHA256 drifted")
    value = _strict_json_value(path.read_bytes())
    if type(value) is not dict:
        raise ValueError("probe template must be a JSON mapping")
    return value


def _strict_json_value(raw: bytes) -> Any:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError("authority JSON contains a duplicate key")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token: {token}")
        ),
    )


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _bind_reviewed_runtime_receipts(
    *,
    plan: Mapping[str, Any],
    prepared_runtime_by_scenario: Mapping[str, Mapping[str, Any]],
    runtime_artifact: Path,
) -> dict[str, str]:
    receipts = _canonical_json_list(
        runtime_artifact.resolve() / "runtime_source_receipts.json"
    )
    identities = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    by_scenario: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        scenario = receipt.get("scenario_identity_sha256")
        if type(scenario) is not str or scenario in by_scenario:
            raise ValueError("candidate0 calibration runtime receipt identity drifted")
        by_scenario[scenario] = receipt
    if (
        len(identities) != len(plan["identities"])
        or len(receipts) != len(identities)
        or set(by_scenario) != set(identities)
    ):
        raise ValueError("candidate0 calibration runtime receipt denominator drifted")
    result: dict[str, str] = {}
    for scenario, identity in identities.items():
        prepared = prepared_runtime_by_scenario.get(scenario)
        receipt = by_scenario[scenario]
        if type(prepared) is not dict:
            raise ValueError("candidate0 calibration prepared runtime is missing")
        case = prepared.get("case")
        planned = prepared.get("mapped_signal_authority")
        actual = receipt.get("source_chain")
        if not all(type(value) is dict for value in (case, planned, actual)):
            raise ValueError("candidate0 calibration runtime source chain is malformed")
        exact = {
            "identity_ordinal": identity["identity_ordinal"],
            "scenario_identity_sha256": scenario,
            "scenario_id": case["scenario_id"],
            "scenario_family": identity["scenario_family"],
            "risk_tier": identity["risk_tier"],
            "benchmark_stratum": identity["benchmark_stratum"],
            "map_sha256": identity["map_sha256"],
            "map_geometry_sha256": identity["map_geometry_sha256"],
            "corridor_sha256": identity["corridor_sha256"],
            "intersection_sha256": identity["intersection_sha256"],
            "route_identity_sha256": identity["route_identity_sha256"],
            "phase_authority_mode": identity["phase_authority_mode"],
        }
        if any(not _strict_equal(receipt.get(name), value) for name, value in exact.items()):
            raise ValueError("candidate0 calibration runtime receipt metadata drifted")
        if not _independent_chain_consistent(planned, actual):
            raise ValueError("candidate0 calibration reviewed runtime chain drifted")
        actual_without_hash = {
            key: value for key, value in actual.items() if key != "source_chain_sha256"
        }
        if (
            actual.get("source_chain_sha256") != _canonical_sha(actual_without_hash)
            or receipt.get("source_chain_sha256") != actual.get("source_chain_sha256")
        ):
            raise ValueError("candidate0 calibration runtime source-chain SHA drifted")
        runtime_receipt = receipt.get("runtime_receipt")
        if type(runtime_receipt) is not dict or not _strict_equal(
            receipt.get("current_phase"), runtime_receipt.get("current_phase")
        ):
            raise ValueError("candidate0 calibration same-tick phase receipt drifted")
        phase = receipt.get("current_phase")
        if identity["phase_authority_mode"] == "controlled_same_tick_override":
            if phase != identity["controlled_current_phase"]:
                raise ValueError("candidate0 calibration controlled phase drifted")
        elif phase not in {"green", "yellow", "red"}:
            raise ValueError("candidate0 calibration observed phase drifted")
        if (
            receipt.get("phase_remaining_available") is not False
            or receipt.get("future_phase_schedule_consumed") is not False
            or receipt.get("outcome_fields_consumed") != []
        ):
            raise ValueError("candidate0 calibration runtime receipt leaked future/outcome")
        result[scenario] = _canonical_sha(receipt)
    return result


def _independent_chain_consistent(
    planned: Mapping[str, Any], actual: Mapping[str, Any]
) -> bool:
    exact_fields = (
        "scenario_id",
        "route_identity_sha256",
        "source_map_sha256",
        "phase_authority_mode",
        "expected_current_phase",
        "formal_phase",
        "formal_mapped_source_required",
        "regulatory_element_ids",
        "physical_light_ids",
        "bulb_ids",
        "controlled_lanelet_ids",
        "route_lanelet_ids",
        "stop_line_id",
    )
    if any(not _strict_equal(planned.get(name), actual.get(name)) for name in exact_fields):
        return False
    try:
        for name, atol in (
            ("stop_line_geometry_m", STOP_LINE_GEOMETRY_ATOL_M),
            ("route_tangent_world", ROUTE_TANGENT_ATOL),
        ):
            left = [float(value) for row in planned[name] for value in (row if type(row) is list else [row])]
            right = [float(value) for row in actual[name] for value in (row if type(row) is list else [row])]
            if len(left) != len(right) or any(
                not math.isclose(a, b, rel_tol=0.0, abs_tol=atol)
                for a, b in zip(left, right, strict=True)
            ):
                return False
        return all(
            math.isclose(
                float(planned[name]),
                float(actual[name]),
                rel_tol=0.0,
                abs_tol=ROUTE_SCALAR_ATOL_M,
            )
            for name in ("stop_line_route_distance_m", "route_arc_m", "route_length_m")
        )
    except (KeyError, TypeError, ValueError):
        return False


def _sha_value(value: Any) -> bool:
    if type(value) is not str or len(value) != 64:
        return False
    try:
        bytes.fromhex(value)
    except ValueError:
        return False
    return True


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty(root: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(root), "status", "--short", "--untracked-files=no"],
            text=True,
        ).strip()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(**vars(args))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
