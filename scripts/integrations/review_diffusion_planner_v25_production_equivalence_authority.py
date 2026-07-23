#!/usr/bin/env python3
"""Independently review the nonFresh production-equivalence authority."""

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
from camp_core.integrations.diffusion_planner_v25_actual_native_receipt_contract import (  # noqa: E402
    actual_native_receipt_contract,
    actual_native_receipt_contract_sha256,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    strict_equal,
)
from camp_core.integrations.diffusion_planner_v25_production_equivalence_authority import (  # noqa: E402
    FILES,
    REVIEW_STATUS,
    validate_nonfresh_production_equivalence_authority,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_routes import (  # noqa: E402
    validate_signal_complete_route_assets,
)
from scripts.integrations.materialize_diffusion_planner_v25_signal_complete_routes import (  # noqa: E402
    _route_class,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _git_head,
    _tracked_dirty,
)


def review(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    source = Path(source_artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        source,
        source_root_sha256,
        label="nonFresh production-equivalence authority",
    )
    authority = validate_nonfresh_production_equivalence_authority(
        _canonical_json(source / "preopen_authority.json")
    )
    route_paths = {
        str(
            Path(row["route_asset"]["path"])
            .resolve()
            .relative_to(source)
        ).replace("\\", "/")
        for row in authority["route_asset_manifest"]["route_assets"]
    }
    map_paths = {
        row["relative_path"] for row in authority["map_suite"]["maps"]
    }
    expected_paths = {
        "COMMAND",
        "HEADS",
        "preopen_authority.json",
        "report.json",
        "run.exit",
        "runtime_qualification_rows.json",
        "selected_source_fixtures.json",
        "route_materialization/route_assets.json",
        *FILES.values(),
        *route_paths,
        *map_paths,
    }
    if set(seal["manifest_paths"]) != expected_paths:
        raise ValueError("production-equivalence authority inventory drifted")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("production-equivalence authority did not pass")
    if (
        _tracked_dirty(ROOT)
        or _git_head(ROOT) != authority["implementation_head"]
        or not strict_equal(
            authority["critical_implementation_manifest"],
            tracked_implementation_manifest(ROOT),
        )
        or not strict_equal(
            authority["actual_native_receipt_contract"],
            actual_native_receipt_contract(),
        )
        or authority["actual_native_receipt_contract_sha256"]
        != actual_native_receipt_contract_sha256()
    ):
        raise ValueError("production-equivalence implementation/ABI drifted")
    for field, file_name in (
        ("execution_plan", FILES["plan"]),
        ("prepared_runtime_rows", FILES["prepared_runtime"]),
        ("route_asset_manifest", FILES["route_assets"]),
        ("map_suite", FILES["map_suite"]),
    ):
        if not strict_equal(
            authority[field], _canonical_value(source / file_name)
        ):
            raise ValueError(
                f"production-equivalence {field} payload drifted"
            )
    if not strict_equal(
        authority["runtime_qualification_rows"],
        _canonical_value(source / "runtime_qualification_rows.json"),
    ):
        raise ValueError(
            "production-equivalence runtime qualification payload drifted"
        )
    if not strict_equal(
        authority["route_asset_manifest"],
        _canonical_json(
            source / "route_materialization" / "route_assets.json"
        ),
    ):
        raise ValueError(
            "production-equivalence route manifest copy drifted"
        )
    route_class, _route_source = _route_class(Path(dp_repo).resolve())
    validate_signal_complete_route_assets(
        authority["route_asset_manifest"],
        plan=authority["execution_plan"],
        map_artifact=source,
        route_class=route_class,
    )
    fixture_rows = _canonical_value(
        source / "selected_source_fixtures.json"
    )
    expected_fixtures = [
        {
            "nonfresh_scenario_class": identity[
                "nonfresh_scenario_class"
            ],
            "source_scenario_id": prepared["case"]["scenario_id"],
            "route_identity_sha256": identity[
                "route_identity_sha256"
            ],
            "source_chain_sha256": identity["source_chain_sha256"],
        }
        for identity, prepared in zip(
            authority["execution_plan"]["identities"],
            authority["prepared_runtime_rows"],
            strict=True,
        )
    ]
    if not strict_equal(fixture_rows, expected_fixtures):
        raise ValueError(
            "production-equivalence selected source fixture drifted"
        )
    for collection in ("upstream_bindings", "source_fixture_bindings"):
        for role, binding in authority[collection].items():
            path = Path(binding["path"]).resolve()
            verify_complete_seal(
                path,
                binding["root_sha256"],
                label=f"reviewed production-equivalence {collection} {role}",
            )
            if (path / "run.exit").read_bytes() != b"0\n":
                raise ValueError(
                    f"reviewed production-equivalence {collection} "
                    f"{role} failed"
                )
    for role, asset in authority["frozen_external_assets"].items():
        path = Path(asset["path"]).resolve()
        if (
            not path.is_file()
            or path.is_symlink()
            or _sha256(path) != asset["sha256"]
        ):
            raise ValueError(
                f"reviewed production-equivalence asset {role} drifted"
            )
    result = {
        "schema_version": (
            "camp_dp_v25_nonfresh_production_equivalence_authority_"
            "independent_review_v1"
        ),
        "status": REVIEW_STATUS,
        "reviewed_root_sha256": source_root_sha256,
        "implementation_head": authority["implementation_head"],
        "actual_native_receipt_contract_sha256": authority[
            "actual_native_receipt_contract_sha256"
        ],
        "scenario_classes": authority["scenario_classes"],
        "paired_unit_count": 3,
        "arm_run_count": 9,
        "tick_count": 576,
        "fresh_rows_or_outcomes_used": False,
        "claim_authorized": False,
    }
    output.mkdir(parents=True)
    _write(output / "report.json", result)
    (output / "HEADS").write_bytes(
        (
            f"camp_head={authority['implementation_head']}\n"
            f"fixed_dp_head={authority['fixed_dp_head']}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes(
        (" ".join(sys.argv) + "\n").encode("utf-8")
    )
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(
        output,
        label="independent nonFresh production-equivalence authority review",
    )


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"{path.name} must contain an object")
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = json.loads(
        raw.decode("utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token: {token}")
        ),
        object_pairs_hook=_pairs,
    )
    if raw != _bytes(value):
        raise ValueError(f"{path.name} is not canonical JSON")
    return value


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _bytes(value: Any) -> bytes:
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


def _write(path: Path, value: Any) -> None:
    path.write_bytes(_bytes(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
