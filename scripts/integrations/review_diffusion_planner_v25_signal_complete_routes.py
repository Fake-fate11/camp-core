#!/usr/bin/env python3
"""Review a sealed V25 signal-complete fixed-DP Route artifact."""

from __future__ import annotations

import argparse
import hashlib
import importlib
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
from camp_core.integrations.diffusion_planner_v25_signal_complete_routes import (  # noqa: E402
    validate_signal_complete_route_assets,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_route_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ROUTE_SOURCE_RELATIVE = "scenario_generation/route.py"


def review(
    *,
    route_artifact: Path,
    route_root_sha256: str,
    plan_artifact: Path,
    plan_root_sha256: str,
    map_artifact: Path,
    map_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    route_root = route_artifact.resolve()
    plan_root = plan_artifact.resolve()
    map_root = map_artifact.resolve()
    dp_root = dp_repo.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    for path, digest, label in (
        (route_root, route_root_sha256, "signal-complete routes"),
        (plan_root, plan_root_sha256, "signal-complete plan"),
        (map_root, map_root_sha256, "signal-complete maps"),
    ):
        verify_complete_seal(path, digest, label=label)
    if _git_head(dp_root) != FIXED_DP_HEAD or _tracked_dirty(dp_root):
        raise ValueError("fixed DP repository authority drifted")
    route_source = (dp_root / ROUTE_SOURCE_RELATIVE).resolve()
    if str(dp_root) not in sys.path:
        sys.path.insert(0, str(dp_root))
    module = importlib.import_module("scenario_generation.route")
    if Path(module.__file__).resolve() != route_source:
        raise ValueError("fixed DP Route imported from an alternate source")
    committed = subprocess.check_output(
        ["git", "-C", str(dp_root), "show", f"{FIXED_DP_HEAD}:{ROUTE_SOURCE_RELATIVE}"]
    )
    if route_source.read_bytes() != committed:
        raise ValueError("fixed DP Route source differs from the pinned git object")
    plan = _canonical_json(plan_root / "execution_plan.json")
    manifest = _canonical_json(route_root / "route_assets.json")
    validated = validate_signal_complete_route_assets(
        manifest,
        plan=plan,
        map_artifact=map_root,
        route_class=module.Route,
    )
    source_report = _canonical_json(route_root / "report.json")
    if (
        source_report.get("status")
        != "passed_signal_complete_route_materialization"
        or source_report.get("fixed_dp_head") != FIXED_DP_HEAD
        or source_report.get("plan_root_sha256") != plan_root_sha256
        or source_report.get("map_root_sha256") != map_root_sha256
        or source_report.get("route_manifest_sha256")
        != _sha256(route_root / "route_assets.json")
        or source_report.get("route_count") != validated["route_count"]
        or source_report.get("fresh_b2_opened") is not False
        or source_report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("signal-complete route source report drifted")
    output.mkdir(parents=True)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_signal_complete_route_review",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(route_root),
        "reviewed_root_sha256": route_root_sha256,
        "plan_artifact": str(plan_root),
        "plan_root_sha256": plan_root_sha256,
        "map_artifact": str(map_root),
        "map_root_sha256": map_root_sha256,
        "route_count": validated["route_count"],
        "route_manifest_reopened": True,
        "all_route_pickles_reloaded": True,
        "float32_start_goal_exact": True,
        "lanelet_sequences_exact": True,
        "fixed_dp_route_git_object_exact": True,
        "model_loaded": False,
        "candidate_generation_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    _write_json(output / "report.json", report)
    (output / "HEADS").write_text(
        f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 signal-complete route review")


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
    parser.add_argument("--route-artifact", type=Path, required=True)
    parser.add_argument("--route-root-sha256", required=True)
    parser.add_argument("--plan-artifact", type=Path, required=True)
    parser.add_argument("--plan-root-sha256", required=True)
    parser.add_argument("--map-artifact", type=Path, required=True)
    parser.add_argument("--map-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(**vars(args))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
