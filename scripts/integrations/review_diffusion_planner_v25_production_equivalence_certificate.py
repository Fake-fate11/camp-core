#!/usr/bin/env python3
"""Independently review the sealed production-equivalence certificate."""

from __future__ import annotations

import argparse
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
from camp_core.integrations.diffusion_planner_v25_production_equivalence_certificate import (  # noqa: E402
    validate_production_equivalence_certificate,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _git_head,
    _tracked_dirty,
)


def review(
    *, source_artifact: Path, source_root_sha256: str, output_dir: Path
) -> str:
    source = Path(source_artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        source,
        source_root_sha256,
        label="production-equivalence certificate",
    )
    if set(seal["manifest_paths"]) != {
        "COMMAND",
        "HEADS",
        "preflight.json",
        "report.json",
        "run.exit",
    } or (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("production-equivalence certificate inventory drifted")
    manifest = tracked_implementation_manifest(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("production-equivalence reviewer worktree is dirty")
    certificate = validate_production_equivalence_certificate(
        _canonical_json(source / "preflight.json"),
        implementation_head=_git_head(ROOT),
        manifest_sha256=manifest["manifest_sha256"],
    )
    for role, binding in certificate["sealed_chain"].items():
        path = Path(binding["path"]).resolve()
        verify_complete_seal(
            path,
            binding["root_sha256"],
            label=f"reviewed production-equivalence chain {role}",
        )
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(
                f"reviewed production-equivalence chain {role} failed"
            )
    result = {
        "schema_version": (
            "camp_dp_v25_nonfresh_production_equivalence_certificate_"
            "independent_review_v1"
        ),
        "status": (
            "passed_independent_nonfresh_production_equivalence_review"
        ),
        "reviewed_root_sha256": source_root_sha256,
        "implementation_head": certificate["implementation_head"],
        "holdout_identity_sha256": certificate[
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": certificate[
            "experiment_protocol_sha256"
        ],
        "sealed_chain_independently_reopened": True,
        "actual_native_receipt_contract_independently_bound": True,
        "full_3x3x64_denominator_reviewed": True,
        "fresh_rows_or_outcomes_used": False,
        "claim_authorized": False,
    }
    output.mkdir(parents=True)
    _write(output / "report.json", result)
    (output / "HEADS").write_bytes(
        (
            f"camp_head={certificate['implementation_head']}\n"
            "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes(
        (" ".join(sys.argv) + "\n").encode("utf-8")
    )
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(
        output,
        label="independent V25 production-equivalence certificate review",
    )


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(
        raw.decode("utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token: {token}")
        ),
        object_pairs_hook=_pairs,
    )
    if type(value) is not dict or raw != _bytes(value):
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


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
