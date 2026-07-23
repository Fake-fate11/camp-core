#!/usr/bin/env python3
"""Seal an outcome-blind V25 signal-complete calibration/Fresh B2 plan."""

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
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (  # noqa: E402
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    build_signal_complete_execution_plan_from_suite,
    validate_signal_complete_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_plan_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_SOURCE = (
    PACKAGE_ROOT
    / "camp_core"
    / "integrations"
    / "diffusion_planner_v25_signal_complete_plan.py"
)


def build(
    *, split: str, map_artifact: Path, map_root_sha256: str, output_dir: Path
) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    map_root = map_artifact.resolve()
    verify_complete_seal(map_root, map_root_sha256, label="signal-complete maps")
    suite = _load_suite_with_payloads(map_root)
    if suite.get("split") != split:
        raise ValueError("signal-complete map artifact split drifted")
    output_dir.mkdir(parents=True)
    try:
        plan = build_signal_complete_execution_plan_from_suite(split, suite)
        plan = validate_signal_complete_execution_plan(plan)
        _write_json(output_dir / "execution_plan.json", plan)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_signal_complete_plan_materialization",
            "camp_head": _git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "split": split,
            "map_artifact": str(map_root),
            "map_root_sha256": map_root_sha256,
            "map_suite_sha256": _sha256(map_root / "signal_complete_suite.json"),
            "plan_source": str(PLAN_SOURCE.resolve()),
            "plan_source_sha256": _sha256(PLAN_SOURCE),
            "plan_sha256": _sha256(output_dir / "execution_plan.json"),
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
        _write_json(output_dir / "report.json", report)
        (output_dir / "HEADS").write_bytes(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
                "ascii"
            )
        )
        (output_dir / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
        (output_dir / "run.exit").write_bytes(b"0\n")
        return seal_artifact(output_dir, label="V25 signal-complete execution plan")
    except BaseException as exc:
        _write_json(
            output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (output_dir / "run.exit").write_bytes(b"1\n")
        seal_artifact(output_dir, label="failed V25 signal-complete execution plan")
        raise


def _load_suite_with_payloads(root: Path) -> dict[str, Any]:
    suite = _canonical_json(root / "signal_complete_suite.json")
    payloads: dict[str, bytes] = {}
    for receipt in suite.get("maps", []):
        path = receipt.get("relative_path")
        if type(path) is not str:
            raise ValueError("signal-complete map receipt path drifted")
        payloads[path] = (root / path).read_bytes()
    suite["map_payloads"] = payloads
    validate_signal_complete_suite(suite)
    return suite


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
    ).encode("utf-8")
    if raw != expected:
        raise ValueError("authority JSON is not canonical")
    return value


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=no"],
            text=True,
        ).strip()
    )


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
        ).encode("utf-8")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split", choices=("calibration", "fresh_b2", "fresh_b3"), required=True
    )
    parser.add_argument("--map-artifact", type=Path, required=True)
    parser.add_argument("--map-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = build(
        split=args.split,
        map_artifact=args.map_artifact,
        map_root_sha256=args.map_root_sha256,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
