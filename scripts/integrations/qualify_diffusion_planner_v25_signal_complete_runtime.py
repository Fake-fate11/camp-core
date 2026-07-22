#!/usr/bin/env python3
"""Source-only pinned-DP qualification for V25 signal-complete maps/plans."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

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
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_runtime_qualification_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
MINIMUM_FREE_BYTES = 10 * 1024**3
TRAIN_LOCK = Path("/root/autodl-tmp/.camp_dp_v25_controlled_train_corpus.lock")


def run(args: argparse.Namespace) -> str:
    _preconditions(args)
    map_seal = verify_complete_seal(
        args.map_artifact, args.map_root_sha256, label="signal-complete maps"
    )
    plan_seal = verify_complete_seal(
        args.plan_artifact, args.plan_root_sha256, label="signal-complete plan"
    )
    plan = _canonical_json(args.plan_artifact / "execution_plan.json")
    plan_report = _canonical_json(args.plan_artifact / "report.json")
    if (
        plan_report.get("map_root_sha256") != map_seal["root_sha256"]
        or Path(str(plan_report.get("map_artifact"))).resolve()
        != args.map_artifact.resolve()
        or plan.get("fresh_b2_opened") is not False
        or plan.get("outcome_fields_consumed") != []
    ):
        raise ValueError("signal-complete map/plan authority drifted")
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        from scripts.integrations.preflight_diffusion_planner_v25_a16_r06_route_signal_source import (
            _actual_route_regulatory_elements,
            _builder_for,
            _extract_mapped_chain,
            _id_free_tensor_layout,
            _materialize_current_request,
        )

        builders: dict[str, Any] = {}
        receipts: list[dict[str, Any]] = []
        for identity in plan["identities"]:
            prepared = build_signal_complete_runtime_case(
                identity,
                map_artifact=args.map_artifact,
                seeds=list(plan["seeds"]),
            )
            case = prepared["case"]
            builder = _builder_for(case, builders, args.dp_repo)
            regs = _actual_route_regulatory_elements(case, builder)
            actual_chain = _extract_mapped_chain(case, builder, regs)
            planned_chain = prepared["mapped_signal_authority"]
            if not _planned_actual_chain_consistent(planned_chain, actual_chain):
                raise ValueError(
                    "pinned-DP Lanelet2 regulatory chain differs from materialized source"
                )
            runtime_receipt, tensor_evidence = _materialize_current_request(
                case, builder, actual_chain
            )
            layout = _id_free_tensor_layout(case, builder)
            receipts.append(
                {
                    "identity_ordinal": identity["identity_ordinal"],
                    "scenario_identity_sha256": identity[
                        "scenario_identity_sha256"
                    ],
                    "scenario_id": case["scenario_id"],
                    "scenario_family": identity["scenario_family"],
                    "risk_tier": identity["risk_tier"],
                    "benchmark_stratum": identity["benchmark_stratum"],
                    "map_sha256": identity["map_sha256"],
                    "map_geometry_sha256": identity["map_geometry_sha256"],
                    "corridor_sha256": identity["corridor_sha256"],
                    "intersection_sha256": identity["intersection_sha256"],
                    "route_identity_sha256": identity[
                        "route_identity_sha256"
                    ],
                    "source_chain_sha256": actual_chain["source_chain_sha256"],
                    "source_chain": actual_chain,
                    "phase_authority_mode": actual_chain[
                        "phase_authority_mode"
                    ],
                    "current_phase": runtime_receipt["current_phase"],
                    "runtime_receipt": runtime_receipt,
                    "tensor_evidence": tensor_evidence,
                    "id_free_tensor_layout": layout,
                    "phase_remaining_available": False,
                    "future_phase_schedule_consumed": False,
                    "model_loaded": False,
                    "candidate_generation_executed": False,
                    "outcome_fields_consumed": [],
                }
            )
        if len(receipts) != plan["identity_count"]:
            raise ValueError("signal-complete runtime qualification denominator drifted")
        _write_json(args.output_dir / "runtime_source_receipts.json", receipts)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_signal_complete_pinned_dp_source_qualification",
            "camp_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "map_artifact": str(args.map_artifact.resolve()),
            "map_root_sha256": map_seal["root_sha256"],
            "plan_artifact": str(args.plan_artifact.resolve()),
            "plan_root_sha256": plan_seal["root_sha256"],
            "split": plan["split"],
            "map_count": plan["map_count"],
            "corridor_count": plan["corridor_count"],
            "route_count": plan["route_count"],
            "qualified_identity_count": len(receipts),
            "source_failure_count": 0,
            "all_regulatory_chains_rebuilt_from_pinned_dp": True,
            "all_same_tick_request_tensors_qualified": True,
            "route_graph_loaded_by_fixed_dp": True,
            "model_loaded": False,
            "candidate_generation_executed": False,
            "training_executed": False,
            "calibration_outcomes_consumed": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
            "receipts_sha256": _sha256(
                args.output_dir / "runtime_source_receipts.json"
            ),
        }
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_bytes(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode()
        )
        (args.output_dir / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
        (args.output_dir / "run.exit").write_bytes(b"0\n")
        return seal_artifact(
            args.output_dir, label="V25 signal-complete pinned-DP qualification"
        )
    except BaseException as exc:
        _write_json(
            args.output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (args.output_dir / "run.exit").write_bytes(b"1\n")
        seal_artifact(
            args.output_dir, label="failed V25 signal-complete pinned-DP qualification"
        )
        raise


def _preconditions(args: argparse.Namespace) -> None:
    if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")
    if _git_head(args.dp_repo) != FIXED_DP_HEAD or _tracked_dirty(args.dp_repo):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    if TRAIN_LOCK.exists():
        import fcntl

        with TRAIN_LOCK.open("a+b") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("controlled corpus lock is held") from exc
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(repo), "status", "--short", "--untracked-files=no"],
            text=True,
        ).strip()
    )


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict:
        raise ValueError("authority JSON must be a mapping")
    expected = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()
    if raw != expected:
        raise ValueError("authority JSON is not canonical")
    return value


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
    if any(not _strict_equal(planned.get(field), actual.get(field)) for field in exact_fields):
        return False
    try:
        stop_matches = np.allclose(
            np.asarray(planned["stop_line_geometry_m"], dtype=np.float64),
            np.asarray(actual["stop_line_geometry_m"], dtype=np.float64),
            rtol=0.0,
            atol=1e-6,
        )
        tangent_matches = np.allclose(
            np.asarray(planned["route_tangent_world"], dtype=np.float64),
            np.asarray(actual["route_tangent_world"], dtype=np.float64),
            rtol=0.0,
            atol=1e-6,
        )
        scalar_matches = all(
            math.isclose(
                float(planned[field]),
                float(actual[field]),
                rel_tol=0.0,
                abs_tol=1e-5,
            )
            for field in (
                "stop_line_route_distance_m",
                "route_arc_m",
                "route_length_m",
            )
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(stop_matches and tangent_matches and scalar_matches)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map-artifact", type=Path, required=True)
    parser.add_argument("--map-root-sha256", required=True)
    parser.add_argument("--plan-artifact", type=Path, required=True)
    parser.add_argument("--plan-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = run(args)
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
