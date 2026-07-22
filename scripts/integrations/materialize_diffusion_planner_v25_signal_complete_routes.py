#!/usr/bin/env python3
"""Seal fixed-DP Route assets for a V25 signal-complete execution plan."""

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
    materialize_signal_complete_route_assets,
    validate_signal_complete_route_assets,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_route_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ROUTE_SOURCE_RELATIVE = "scenario_generation/route.py"


def build(
    *,
    plan_artifact: Path,
    plan_root_sha256: str,
    map_artifact: Path,
    map_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    plan_root = plan_artifact.resolve()
    map_root = map_artifact.resolve()
    dp_root = dp_repo.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    verify_complete_seal(plan_root, plan_root_sha256, label="signal-complete plan")
    verify_complete_seal(map_root, map_root_sha256, label="signal-complete maps")
    _verify_dp(dp_root)
    plan = _canonical_json(plan_root / "execution_plan.json")
    route_class, route_source = _route_class(dp_root)
    try:
        manifest = materialize_signal_complete_route_assets(
            plan=plan,
            map_artifact=map_root,
            output_dir=output,
            route_class=route_class,
        )
        manifest = validate_signal_complete_route_assets(
            manifest,
            plan=plan,
            map_artifact=map_root,
            route_class=route_class,
        )
        _write_json(output / "route_assets.json", manifest)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_signal_complete_route_materialization",
            "camp_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "plan_artifact": str(plan_root),
            "plan_root_sha256": plan_root_sha256,
            "map_artifact": str(map_root),
            "map_root_sha256": map_root_sha256,
            "route_source": str(route_source),
            "route_source_git_object_sha256": _sha256_bytes(
                _git_object(dp_root, ROUTE_SOURCE_RELATIVE)
            ),
            "route_source_file_sha256": _sha256(route_source),
            "route_manifest_sha256": _sha256(output / "route_assets.json"),
            "split": manifest["split"],
            "route_count": manifest["route_count"],
            "model_loaded": False,
            "candidate_generation_executed": False,
            "fixed_dp_modified": False,
            "map_semantics_modified": False,
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
        return seal_artifact(output, label="V25 signal-complete fixed-DP routes")
    except BaseException as exc:
        if output.exists():
            _write_json(
                output / "failure.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "failed",
                    "reason": str(exc),
                },
            )
            (output / "run.exit").write_text("1\n", encoding="ascii")
            seal_artifact(output, label="failed V25 signal-complete fixed-DP routes")
        raise


def _verify_dp(root: Path) -> None:
    if _git_head(root) != FIXED_DP_HEAD or _tracked_dirty(root):
        raise ValueError("fixed DP repository authority drifted")


def _route_class(root: Path) -> tuple[type[Any], Path]:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    module = importlib.import_module("scenario_generation.route")
    source = Path(module.__file__).resolve()
    expected = (root / ROUTE_SOURCE_RELATIVE).resolve()
    if source != expected:
        raise ValueError("fixed DP Route imported from an alternate source")
    committed = _git_object(root, ROUTE_SOURCE_RELATIVE)
    if source.read_bytes() != committed:
        raise ValueError("fixed DP Route source differs from the pinned git object")
    return module.Route, source


def _git_object(root: Path, relative: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(root), "show", f"{FIXED_DP_HEAD}:{relative}"]
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


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
    parser.add_argument("--plan-artifact", type=Path, required=True)
    parser.add_argument("--plan-root-sha256", required=True)
    parser.add_argument("--map-artifact", type=Path, required=True)
    parser.add_argument("--map-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = build(**vars(args))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
