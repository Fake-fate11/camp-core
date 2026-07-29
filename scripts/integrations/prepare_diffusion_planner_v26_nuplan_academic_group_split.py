#!/usr/bin/env python3
"""Freeze the V26 three-city outcome-independent academic group split."""

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
    build_v26_nuplan_academic_group_split_manifest,
    canonical_json_bytes,
    canonical_json_sha256,
    validate_v26_nuplan_academic_group_split_manifest,
)


INVENTORY_SCHEMA = "camp_dp_v26_nuplan_three_city_identity_inventory_v1"
INVENTORY_ROLE = "development_nonholdout_nuplan_identity_inventory"


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


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    inventory = _read_json(args.inventory, "three-city identity inventory")
    if not isinstance(inventory, dict):
        raise ValueError("three-city identity inventory must be a mapping")
    if inventory.get("schema_version") != INVENTORY_SCHEMA or inventory.get("evidence_role") != INVENTORY_ROLE:
        raise ValueError("three-city identity inventory schema or role drifted")
    if inventory.get("outcome_fields_consumed") != []:
        raise ValueError("three-city identity inventory consumed outcomes")
    if not isinstance(inventory.get("records"), list):
        raise ValueError("three-city identity inventory records are missing")
    actual_inventory_sha = canonical_json_sha256(
        {key: value for key, value in inventory.items() if key != "identity_inventory_sha256"}
    )
    if inventory.get("identity_inventory_sha256") != actual_inventory_sha:
        raise ValueError("three-city identity inventory hash drifted")
    fixed_dp = _read_json(args.fixed_dp_binding, "fixed-DP binding")
    manifest = build_v26_nuplan_academic_group_split_manifest(
        inventory["records"],
        raw_source=inventory.get("raw_source", {}),
        fixed_dp=fixed_dp,
        camp_source_head=args.camp_source_head,
        raw_acquisition_manifest_sha256=inventory.get("raw_acquisition_manifest_sha256"),
        allocation_seed=args.allocation_seed,
        iid_validation_fraction=args.iid_validation_fraction,
    )
    manifest["input_bindings"] = {
        "identity_inventory_sha256": _sha256_file(args.inventory),
        "fixed_dp_binding_sha256": _sha256_file(args.fixed_dp_binding),
    }
    manifest["identity_manifest_sha256"] = canonical_json_sha256(
        {key: value for key, value in manifest.items() if key != "identity_manifest_sha256"}
    )
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
    parser.add_argument("--allocation-seed", type=int, default=3407)
    parser.add_argument("--iid-validation-fraction", type=float, default=0.2)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_manifest(args)
    core = {key: value for key, value in manifest.items() if key != "input_bindings"}
    core["identity_manifest_sha256"] = canonical_json_sha256(
        {key: value for key, value in core.items() if key != "identity_manifest_sha256"}
    )
    validate_v26_nuplan_academic_group_split_manifest(core)
    write_manifest(args.output, manifest)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "identity_manifest_sha256": manifest["identity_manifest_sha256"],
                "partitions": {
                    name: value["record_count"]
                    for name, value in manifest["partitions"].items()
                },
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
