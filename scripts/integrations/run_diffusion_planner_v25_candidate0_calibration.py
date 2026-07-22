#!/usr/bin/env python3
"""Run and seal the unopened V25 candidate0-only calibration denominator."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable, Iterator, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_calibration_execution import (  # noqa: E402
    execute_candidate0_calibration_units,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    validate_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)


SCHEMA_VERSION = "camp_dp_v25_candidate0_calibration_execution_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
MINIMUM_FREE_BYTES = 10 * 1024**3
TRAIN_LOCK = Path("/root/autodl-tmp/.camp_dp_v25_controlled_train_corpus.lock")
RunOne = Callable[[Mapping[str, Any], Path], Mapping[str, Any]]


def run(
    *,
    plan_artifact: Path,
    plan_root_sha256: str,
    map_artifact: Path,
    map_root_sha256: str,
    route_artifact: Path,
    route_root_sha256: str,
    route_review_artifact: Path,
    route_review_root_sha256: str,
    runtime_artifact: Path,
    runtime_root_sha256: str,
    runtime_review_artifact: Path,
    runtime_review_root_sha256: str,
    probe_template: Path,
    probe_template_sha256: str,
    dp_repo: Path,
    output_dir: Path,
    device: str,
    run_one: RunOne | None = None,
) -> str:
    """Execute exactly 100 calibration runs under one exclusive corpus lock."""

    if device != "cuda":
        raise ValueError("candidate0 calibration production execution requires cuda")
    dp_root = dp_repo.resolve()
    output = output_dir.resolve()
    _preconditions(dp_root, output)
    roots = _verify_inputs(
        plan_artifact=plan_artifact,
        plan_root_sha256=plan_root_sha256,
        map_artifact=map_artifact,
        map_root_sha256=map_root_sha256,
        route_artifact=route_artifact,
        route_root_sha256=route_root_sha256,
        route_review_artifact=route_review_artifact,
        route_review_root_sha256=route_review_root_sha256,
        runtime_artifact=runtime_artifact,
        runtime_root_sha256=runtime_root_sha256,
        runtime_review_artifact=runtime_review_artifact,
        runtime_review_root_sha256=runtime_review_root_sha256,
    )
    probe = _legacy_json_object(probe_template, probe_template_sha256)
    plan = validate_signal_complete_execution_plan(
        _canonical_json(plan_artifact.resolve() / "execution_plan.json")
    )
    route_manifest = _canonical_json(
        route_artifact.resolve() / "route_assets.json"
    )
    route_rows = route_manifest.get("route_assets")
    if type(route_rows) is not list:
        raise ValueError("signal-complete route inventory is malformed")
    route_by_identity = {
        row["route_identity_sha256"]: dict(row["route_asset"])
        for row in route_rows
    }
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity,
            map_artifact=map_artifact.resolve(),
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    }
    runtime_receipt_sha256_by_scenario = _bind_reviewed_runtime_receipts(
        plan=plan,
        prepared_runtime_by_scenario=prepared,
        runtime_artifact=Path(roots["runtime_artifact"]),
    )
    production_run = run_one or _native_run_one(device=device)

    with _exclusive_lock(TRAIN_LOCK):
        try:
            report = execute_candidate0_calibration_units(
                plan=plan,
                probe_template=probe,
                prepared_runtime_by_scenario=prepared,
                route_asset_by_identity=route_by_identity,
                dp_repo=dp_root,
                output_dir=output,
                run_one=production_run,
            )
            report.update(
                {
                    "artifact_schema_version": SCHEMA_VERSION,
                    "camp_head": _git_head(ROOT),
                    "device": device,
                    "input_roots": roots,
                    "probe_template": str(probe_template.resolve()),
                    "probe_template_sha256": probe_template_sha256,
                    "runtime_receipt_sha256_by_scenario": (
                        runtime_receipt_sha256_by_scenario
                    ),
                    "model_loaded": run_one is None,
                    "candidate_generation_executed": run_one is None,
                    "independent_review_completed": False,
                }
            )
            _write_json(output / "report.json", report)
            _write_control_files(output, exit_code=0)
            return seal_artifact(output, label="V25 candidate0 calibration execution")
        except BaseException as exc:
            if output.exists():
                _write_json(
                    output / "failure.json",
                    {
                        "schema_version": SCHEMA_VERSION,
                        "status": "failed_closed_candidate0_calibration_execution",
                        "reason": str(exc),
                        "fresh_b2_opened": False,
                        "outcome_fields_consumed": [],
                    },
                )
                _write_control_files(output, exit_code=1)
                seal_artifact(output, label="failed V25 candidate0 calibration execution")
            raise


def _native_run_one(*, device: str) -> RunOne:
    holder: dict[str, Any] = {}

    def execute(config: Mapping[str, Any], run_dir: Path) -> Mapping[str, Any]:
        if "run_arm" not in holder:
            from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
                build_native_arm_runner,
            )

            holder["run_arm"] = build_native_arm_runner(config, device=device)
        return holder["run_arm"](
            route=config["routes"][0],
            arm="dp",
            config=config,
            output_dir=run_dir / "native",
            max_steps=64,
            fixed_k8_candidate0=True,
        )

    return execute


def _preconditions(dp_root: Path, output: Path) -> None:
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    if _git_head(dp_root) != FIXED_DP_HEAD or _tracked_dirty(dp_root):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")


def _verify_inputs(**values: Any) -> dict[str, str]:
    roles = (
        "plan",
        "map",
        "route",
        "route_review",
        "runtime",
        "runtime_review",
    )
    roots: dict[str, str] = {}
    for role in roles:
        artifact = Path(values[f"{role}_artifact"]).resolve()
        digest = str(values[f"{role}_root_sha256"])
        seal = verify_complete_seal(artifact, digest, label=f"signal-complete {role}")
        roots[f"{role}_artifact"] = str(artifact)
        roots[f"{role}_root_sha256"] = seal["root_sha256"]
        if (artifact / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"signal-complete {role} run.exit drifted")
    route_review = _canonical_json(
        Path(roots["route_review_artifact"]) / "report.json"
    )
    runtime_review = _canonical_json(
        Path(roots["runtime_review_artifact"]) / "report.json"
    )
    if (
        route_review.get("status")
        != "passed_independent_signal_complete_route_review"
        or route_review.get("reviewed_root_sha256")
        != roots["route_root_sha256"]
        or runtime_review.get("status")
        != "passed_independent_signal_complete_runtime_review"
        or runtime_review.get("reviewed_root_sha256")
        != roots["runtime_root_sha256"]
    ):
        raise ValueError("signal-complete independent review binding drifted")
    return roots


def _legacy_json_object(path: Path, expected_sha256: str) -> dict[str, Any]:
    if _sha256(path) != expected_sha256:
        raise ValueError("probe template SHA256 drifted")
    value = _strict_json_value(path.read_bytes())
    if type(value) is not dict:
        raise ValueError("probe template must be a JSON object")
    return value


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _canonical_json_list(path: Path) -> list[dict[str, Any]]:
    value = _canonical_value(path)
    if type(value) is not list or any(type(row) is not dict for row in value):
        raise ValueError(f"authority JSON list is malformed: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = _strict_json_value(raw)
    if raw != _canonical_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _bind_reviewed_runtime_receipts(
    *,
    plan: Mapping[str, Any],
    prepared_runtime_by_scenario: Mapping[str, Mapping[str, Any]],
    runtime_artifact: Path,
) -> dict[str, str]:
    """Bind every executed config to one row from the reviewed runtime root."""

    receipts = _canonical_json_list(
        runtime_artifact.resolve() / "runtime_source_receipts.json"
    )
    identities = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    if len(identities) != len(plan["identities"]) or len(receipts) != len(identities):
        raise ValueError("candidate0 calibration runtime receipt denominator drifted")
    by_scenario: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        scenario = receipt.get("scenario_identity_sha256")
        if type(scenario) is not str or scenario in by_scenario:
            raise ValueError("candidate0 calibration runtime receipt identity drifted")
        by_scenario[scenario] = receipt
    if set(by_scenario) != set(identities):
        raise ValueError("candidate0 calibration runtime receipt inventory drifted")

    result: dict[str, str] = {}
    for scenario, identity in identities.items():
        prepared = prepared_runtime_by_scenario.get(scenario)
        receipt = by_scenario[scenario]
        if type(prepared) is not dict:
            raise ValueError("candidate0 calibration prepared runtime is missing")
        case = prepared.get("case")
        planned_chain = prepared.get("mapped_signal_authority")
        actual_chain = receipt.get("source_chain")
        if not all(type(value) is dict for value in (case, planned_chain, actual_chain)):
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
        if not _planned_actual_chain_consistent(planned_chain, actual_chain):
            raise ValueError("candidate0 calibration reviewed runtime chain drifted")
        actual_without_hash = {
            key: value for key, value in actual_chain.items() if key != "source_chain_sha256"
        }
        if (
            actual_chain.get("source_chain_sha256") != _canonical_sha(actual_without_hash)
            or receipt.get("source_chain_sha256")
            != actual_chain.get("source_chain_sha256")
        ):
            raise ValueError("candidate0 calibration runtime source-chain SHA drifted")
        runtime_receipt = receipt.get("runtime_receipt")
        if type(runtime_receipt) is not dict or not _strict_equal(
            receipt.get("current_phase"), runtime_receipt.get("current_phase")
        ):
            raise ValueError("candidate0 calibration same-tick phase receipt drifted")
        current_phase = receipt.get("current_phase")
        if identity["phase_authority_mode"] == "controlled_same_tick_override":
            if current_phase != identity["controlled_current_phase"]:
                raise ValueError("candidate0 calibration controlled phase drifted")
        elif current_phase not in {"green", "yellow", "red"}:
            raise ValueError("candidate0 calibration observed phase drifted")
        if (
            receipt.get("phase_remaining_available") is not False
            or receipt.get("future_phase_schedule_consumed") is not False
            or receipt.get("outcome_fields_consumed") != []
        ):
            raise ValueError("candidate0 calibration runtime receipt leaked future/outcome")
        result[scenario] = _canonical_sha(receipt)
    return result


def _planned_actual_chain_consistent(
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
    numeric_lists = ("stop_line_geometry_m", "route_tangent_world")
    try:
        for name in numeric_lists:
            left = [float(value) for row in planned[name] for value in (row if type(row) is list else [row])]
            right = [float(value) for row in actual[name] for value in (row if type(row) is list else [row])]
            if len(left) != len(right) or any(
                not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-6)
                for a, b in zip(left, right, strict=True)
            ):
                return False
        return all(
            math.isclose(
                float(planned[name]), float(actual[name]), rel_tol=0.0, abs_tol=1e-5
            )
            for name in ("stop_line_route_distance_m", "route_arc_m", "route_length_m")
        )
    except (KeyError, TypeError, ValueError):
        return False


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


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


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _write_control_files(output: Path, *, exit_code: int) -> None:
    (output / "HEADS").write_text(
        f"camp_head={_git_head(ROOT)}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text(f"{exit_code}\n", encoding="ascii")


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    if os.name != "posix":
        yield
        return
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("controlled corpus lock is held") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "map", "route", "route-review", "runtime", "runtime-review"):
        parser.add_argument(f"--{name}-artifact", type=Path, required=True)
        parser.add_argument(f"--{name}-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    root = run(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
