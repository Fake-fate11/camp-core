#!/usr/bin/env python3
"""Independently review a V25 pinned-DP signal-complete qualification."""

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

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_runtime_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def review(
    *, artifact: Path, expected_root: str, dp_repo: Path
) -> dict[str, Any]:
    seal = verify_complete_seal(
        artifact, expected_root, label="signal-complete runtime qualification"
    )
    if set(seal["manifest_paths"]) != {
        "COMMAND",
        "HEADS",
        "report.json",
        "run.exit",
        "runtime_source_receipts.json",
    }:
        raise ValueError("signal-complete qualification inventory drifted")
    if (artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError("signal-complete qualification exit drifted")
    if _git_head(dp_repo) != FIXED_DP_HEAD or _tracked_dirty(dp_repo):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")
    report = _canonical_json(artifact / "report.json")
    receipts = _canonical_json_list(artifact / "runtime_source_receipts.json")
    map_artifact = Path(str(report.get("map_artifact"))).resolve()
    plan_artifact = Path(str(report.get("plan_artifact"))).resolve()
    map_seal = verify_complete_seal(
        map_artifact, str(report.get("map_root_sha256")), label="signal-complete maps"
    )
    plan_seal = verify_complete_seal(
        plan_artifact, str(report.get("plan_root_sha256")), label="signal-complete plan"
    )
    plan = _canonical_json(plan_artifact / "execution_plan.json")
    if (
        len(receipts) != plan.get("identity_count")
        or report.get("receipts_sha256")
        != _sha256(artifact / "runtime_source_receipts.json")
    ):
        raise ValueError("signal-complete qualification denominator/root drifted")

    from scripts.integrations.preflight_diffusion_planner_v25_a16_r06_route_signal_source import (
        _actual_route_regulatory_elements,
        _builder_for,
        _extract_mapped_chain,
        _id_free_tensor_layout,
        _materialize_current_request,
    )

    builders: dict[str, Any] = {}
    expected_receipts: list[dict[str, Any]] = []
    for identity in plan["identities"]:
        prepared = build_signal_complete_runtime_case(
            identity, map_artifact=map_artifact, seeds=list(plan["seeds"])
        )
        case = prepared["case"]
        builder = _builder_for(case, builders, dp_repo)
        actual_chain = _extract_mapped_chain(
            case, builder, _actual_route_regulatory_elements(case, builder)
        )
        runtime_receipt, tensor_evidence = _materialize_current_request(
            case, builder, actual_chain
        )
        expected_receipts.append(
            {
                "identity_ordinal": identity["identity_ordinal"],
                "scenario_identity_sha256": identity["scenario_identity_sha256"],
                "scenario_id": case["scenario_id"],
                "scenario_family": identity["scenario_family"],
                "risk_tier": identity["risk_tier"],
                "benchmark_stratum": identity["benchmark_stratum"],
                "map_sha256": identity["map_sha256"],
                "map_geometry_sha256": identity["map_geometry_sha256"],
                "corridor_sha256": identity["corridor_sha256"],
                "intersection_sha256": identity["intersection_sha256"],
                "route_identity_sha256": identity["route_identity_sha256"],
                "source_chain_sha256": actual_chain["source_chain_sha256"],
                "source_chain": actual_chain,
                "phase_authority_mode": actual_chain["phase_authority_mode"],
                "current_phase": runtime_receipt["current_phase"],
                "runtime_receipt": runtime_receipt,
                "tensor_evidence": tensor_evidence,
                "id_free_tensor_layout": _id_free_tensor_layout(case, builder),
                "phase_remaining_available": False,
                "future_phase_schedule_consumed": False,
                "model_loaded": False,
                "candidate_generation_executed": False,
                "outcome_fields_consumed": [],
            }
        )
    if not _strict_equal(receipts, expected_receipts):
        raise ValueError("signal-complete runtime receipts differ from independent replay")
    expected_report = {
        "schema_version": "camp_dp_v25_signal_complete_runtime_qualification_v1",
        "status": "passed_signal_complete_pinned_dp_source_qualification",
        "camp_head": report.get("camp_head"),
        "fixed_dp_head": FIXED_DP_HEAD,
        "map_artifact": str(map_artifact),
        "map_root_sha256": map_seal["root_sha256"],
        "plan_artifact": str(plan_artifact),
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
        "receipts_sha256": _sha256(artifact / "runtime_source_receipts.json"),
    }
    if not _strict_equal(report, expected_report):
        raise ValueError("signal-complete qualification report drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_signal_complete_runtime_review",
        "reviewed_artifact": str(artifact.resolve()),
        "reviewed_root_sha256": seal["root_sha256"],
        "map_root_sha256": map_seal["root_sha256"],
        "plan_root_sha256": plan_seal["root_sha256"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "split": plan["split"],
        "qualified_identity_count": len(receipts),
        "all_receipts_recomputed": True,
        "model_loaded": False,
        "candidate_generation_executed": False,
        "training_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


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
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError("authority JSON must be a mapping")
    return value


def _canonical_json_list(path: Path) -> list[dict[str, Any]]:
    value = _canonical_value(path)
    if type(value) is not list or any(type(item) is not dict for item in value):
        raise ValueError("authority JSON must be a list of mappings")
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError("authority JSON contains a duplicate key")
            result[key] = value
        return result
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token: {token}")
        ),
    )
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = review(
        artifact=args.artifact,
        expected_root=args.root_sha256,
        dp_repo=args.dp_repo,
    )
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    _write_json(args.output_dir / "report.json", report)
    (args.output_dir / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
    (args.output_dir / "HEADS").write_bytes(
        f"fixed_dp_head={FIXED_DP_HEAD}\n".encode()
    )
    (args.output_dir / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(args.output_dir, label="V25 signal-complete runtime review")
    print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
