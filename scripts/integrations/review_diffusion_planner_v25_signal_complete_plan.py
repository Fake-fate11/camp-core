#!/usr/bin/env python3
"""Review a sealed V25 signal-complete calibration/Fresh B2 plan artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (  # noqa: E402
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    ARMS,
    EVENT_FAMILIES,
    RISK_TIERS,
    build_signal_complete_execution_plan_from_suite,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_plan_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_SOURCE = (
    PACKAGE_ROOT
    / "camp_core"
    / "integrations"
    / "diffusion_planner_v25_signal_complete_plan.py"
)


def review(artifact: Path, expected_root: str) -> dict[str, Any]:
    root = artifact.resolve()
    seal = verify_complete_seal(root, expected_root, label="signal-complete plan")
    if set(seal["manifest_paths"]) != {
        "COMMAND",
        "HEADS",
        "execution_plan.json",
        "report.json",
        "run.exit",
    }:
        raise ValueError("signal-complete plan artifact inventory drifted")
    if (root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("signal-complete plan exit drifted")
    report = _canonical_json(root / "report.json")
    plan = _canonical_json(root / "execution_plan.json")
    if report.get("plan_sha256") != _sha256(root / "execution_plan.json"):
        raise ValueError("signal-complete plan SHA drifted")
    map_root = Path(str(report.get("map_artifact"))).resolve()
    map_root_sha = report.get("map_root_sha256")
    if type(map_root_sha) is not str:
        raise ValueError("signal-complete map root is invalid")
    verify_complete_seal(map_root, map_root_sha, label="signal-complete maps")
    suite = _load_suite_with_payloads(map_root)
    expected = build_signal_complete_execution_plan_from_suite(plan.get("split"), suite)
    if not _strict_equal(plan, expected):
        raise ValueError("signal-complete plan differs from map-backed reconstruction")
    _review_plan_semantics(plan)
    expected_report = {
        "schema_version": "camp_dp_v25_signal_complete_plan_artifact_v1",
        "status": "passed_signal_complete_plan_materialization",
        "camp_head": report.get("camp_head"),
        "fixed_dp_head": FIXED_DP_HEAD,
        "split": plan["split"],
        "map_artifact": str(map_root),
        "map_root_sha256": map_root_sha,
        "map_suite_sha256": _sha256(map_root / "signal_complete_suite.json"),
        "plan_source": str(PLAN_SOURCE.resolve()),
        "plan_source_sha256": _sha256(PLAN_SOURCE),
        "plan_sha256": _sha256(root / "execution_plan.json"),
        "map_count": plan["map_count"],
        "corridor_count": plan["corridor_count"],
        "route_count": plan["route_count"],
        "execution_unit_count": plan["execution_unit_count"],
        "planned_arm_run_count": plan["planned_arm_run_count"],
        "model_loaded": False,
        "candidate_generation_executed": False,
        "training_executed": False,
        "calibration_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if not _strict_equal(report, expected_report):
        raise ValueError("signal-complete plan report drifted")
    expected_heads = (
        f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n"
    ).encode("ascii")
    if (root / "HEADS").read_bytes() != expected_heads:
        raise ValueError("signal-complete plan HEADS drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_signal_complete_plan_review",
        "reviewed_artifact": str(root),
        "reviewed_root_sha256": seal["root_sha256"],
        "camp_head": report["camp_head"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "map_root_sha256": map_root_sha,
        "split": plan["split"],
        "map_count": plan["map_count"],
        "corridor_count": plan["corridor_count"],
        "route_count": plan["route_count"],
        "execution_unit_count": plan["execution_unit_count"],
        "planned_arm_run_count": plan["planned_arm_run_count"],
        "all_family_tier_cells_nonzero": True,
        "same_tick_signal_contract_recomputed": True,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _review_plan_semantics(plan: dict[str, Any]) -> None:
    family_tiers = {
        (row.get("scenario_family"), row.get("risk_tier"))
        for row in plan["identities"]
        if row.get("benchmark_stratum") == "controlled_stress"
    }
    if family_tiers != {
        (family, tier) for family in EVENT_FAMILIES for tier in RISK_TIERS
    }:
        raise ValueError("signal-complete family/tier coverage drifted")
    for row in plan["identities"]:
        if (
            row.get("signal_source_class") != "mapped_signal"
            or row.get("same_tick_current_phase_required") is not True
            or row.get("phase_remaining_available") is not False
            or row.get("future_phase_program_present") is not False
            or row.get("outcome_fields_consumed") != []
        ):
            raise ValueError("signal-complete identity source contract drifted")
        if row.get("benchmark_stratum") not in {"naturalistic", "controlled_stress"}:
            raise ValueError("signal-complete benchmark stratum drifted")
        if row["scenario_family"] == "red_light_phase_timing":
            expected_phase = {
                "easy": "green",
                "borderline": "yellow",
                "high_risk": "red",
            }[row["risk_tier"]]
            if (
                row.get("phase_authority_mode") != "controlled_same_tick_override"
                or row.get("controlled_current_phase") != expected_phase
            ):
                raise ValueError("signal-complete red current-phase contract drifted")
        elif (
            row.get("phase_authority_mode") != "observe_same_tick_request"
            or row.get("controlled_current_phase") is not None
        ):
            raise ValueError("signal-complete observed phase contract drifted")
    if plan["split"] == "fresh_b2":
        for unit in plan["execution_units"]:
            if set(unit.get("ordered_arms", [])) != set(ARMS):
                raise ValueError("Fresh B2 three-arm order drifted")


def _load_suite_with_payloads(root: Path) -> dict[str, Any]:
    suite = _canonical_json(root / "signal_complete_suite.json")
    suite["map_payloads"] = {
        receipt["relative_path"]: (root / receipt["relative_path"]).read_bytes()
        for receipt in suite.get("maps", [])
    }
    validate_signal_complete_suite(suite)
    return suite


def _canonical_json(path: Path) -> dict[str, Any]:
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
    ).encode("utf-8")
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = review(args.artifact, args.root_sha256)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "report.json").write_bytes(
        (
            json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode("utf-8")
    )
    (args.output_dir / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
    (args.output_dir / "HEADS").write_bytes(
        f"camp_head={report.get('camp_head', '')}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode()
    )
    (args.output_dir / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(args.output_dir, label="V25 signal-complete plan review")
    print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
