#!/usr/bin/env python3
"""Freeze an identity-only V26 official-nuPlan source/split manifest.

The input inventory is intentionally restricted to source identity and strata.
It must not contain candidate, trajectory, label, or outcome payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v26_nuplan import (  # noqa: E402
    build_v26_nuplan_split_manifest,
    canonical_json_bytes,
    validate_v26_nuplan_split_manifest,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _parse_ood_pair(value: str) -> tuple[str, str]:
    try:
        city, family = value.split(":", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("OOD pair must be CITY:MAP_FAMILY") from exc
    if not city or not family:
        raise argparse.ArgumentTypeError("OOD pair must be CITY:MAP_FAMILY")
    return city, family


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    inventory = _read_json(args.inventory, "identity inventory")
    if not isinstance(inventory, dict) or set(inventory) != {"raw_source", "records"}:
        raise ValueError("identity inventory must contain exactly raw_source and records")
    if not isinstance(inventory["records"], list):
        raise ValueError("identity inventory records must be a list")
    fixed_dp = _read_json(args.fixed_dp_binding, "fixed-DP binding")
    manifest = build_v26_nuplan_split_manifest(
        inventory["records"],
        raw_source=inventory["raw_source"],
        fixed_dp=fixed_dp,
        camp_source_head=args.camp_source_head,
        ood_city_map_families=args.ood_city_map_family,
    )
    manifest["input_bindings"] = {
        "identity_inventory_sha256": _sha256_file(args.inventory),
        "fixed_dp_binding_sha256": _sha256_file(args.fixed_dp_binding),
    }
    # Bind inputs before final validation; no self-referential manifest hash is used.
    manifest["identity_manifest_sha256"] = hashlib.sha256(
        canonical_json_bytes(
            {key: value for key, value in manifest.items() if key != "identity_manifest_sha256"}
        )
    ).hexdigest()
    return manifest


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json_bytes(manifest))
    temporary.replace(path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--fixed-dp-binding", type=Path, required=True)
    parser.add_argument("--camp-source-head", required=True)
    parser.add_argument("--ood-city-map-family", type=_parse_ood_pair, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_manifest(args)
    # The builder validates the structural contract; this additionally keeps the
    # command's own input binding outside the rebuildable core receipt.
    core = {key: value for key, value in manifest.items() if key != "input_bindings"}
    core["identity_manifest_sha256"] = (
        __import__("camp_core.integrations.diffusion_planner_v26_nuplan", fromlist=["canonical_json_sha256"])
        .canonical_json_sha256({key: value for key, value in core.items() if key != "identity_manifest_sha256"})
    )
    validate_v26_nuplan_split_manifest(core)
    write_manifest(args.output, manifest)
    print(json.dumps({"output": str(args.output), "identity_manifest_sha256": manifest["identity_manifest_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
