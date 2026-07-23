#!/usr/bin/env python3
"""Freeze the sealed nonFresh production-equivalence lifecycle certificate."""

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
from camp_core.integrations.diffusion_planner_v25_actual_native_receipt_contract import (  # noqa: E402
    validate_actual_native_receipt,
)
from camp_core.integrations.diffusion_planner_v25_production_equivalence_certificate import (  # noqa: E402
    freeze_production_equivalence_certificate,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_production_equivalence_authority import (  # noqa: E402
    validate_nonfresh_production_equivalence_authority,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _git_head,
    _tracked_dirty,
)


ROLES = (
    "authority",
    "authority_review",
    "controller",
    "opening_release",
    "execution",
    "execution_review",
    "evaluation",
    "evaluation_review",
    "focused_tests",
)


def build(
    *,
    artifacts: dict[str, Path],
    roots: dict[str, str],
    output_dir: Path,
) -> str:
    if set(artifacts) != set(ROLES) or set(roots) != set(ROLES):
        raise ValueError("production-equivalence certificate roles drifted")
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    canonical = {role: Path(artifacts[role]).resolve() for role in ROLES}
    for role in ROLES:
        verify_complete_seal(
            canonical[role],
            roots[role],
            label=f"production-equivalence certificate {role}",
        )
        if (canonical[role] / "run.exit").read_bytes() != b"0\n":
            raise ValueError(
                f"production-equivalence certificate {role} failed"
            )
    authority = validate_nonfresh_production_equivalence_authority(
        _canonical_json(canonical["authority"] / "preopen_authority.json")
    )
    if (
        _tracked_dirty(ROOT)
        or _git_head(ROOT) != authority["implementation_head"]
        or tracked_implementation_manifest(ROOT)["manifest_sha256"]
        != authority["critical_implementation_manifest"]["manifest_sha256"]
    ):
        raise ValueError("production-equivalence certificate HEAD drifted")
    expected_statuses = {
        "authority_review": (
            "passed_independent_nonfresh_production_equivalence_"
            "authority_review"
        ),
        "execution_review": "passed_independent_holdout_execution_review",
        "evaluation": "sealed_holdout_three_arm_evaluation",
        "evaluation_review": "passed_independent_holdout_evaluation_review",
        "focused_tests": "passed_b4_production_rc_focused_suite",
    }
    for role, status in expected_statuses.items():
        file_name = (
            "evaluation.json"
            if role == "evaluation" and not (
                canonical[role] / "report.json"
            ).exists()
            else "report.json"
        )
        report = _canonical_json(canonical[role] / file_name)
        if report.get("status") != status:
            raise ValueError(
                f"production-equivalence {role} status drifted"
            )
    execution = canonical["execution"]
    branches = {
        "candidate0_primary": [],
        "candidate0_supplementary": [],
        "static14d": [],
        "scene14d": [],
    }
    run_dirs = sorted(
        path
        for path in (execution / "runs").iterdir()
        if path.is_dir() and not path.is_symlink()
    )
    if len(run_dirs) != 9:
        raise ValueError("production-equivalence run denominator drifted")
    for run_dir in run_dirs:
        config = _canonical_json(run_dir / "run_config.json")
        arm = config["protocol"]["holdout_opening_arm"]
        branch = (
            "candidate0_primary"
            if arm == "candidate0"
            else arm
        )
        raw = _canonical_json(run_dir / "actual_native_receipt_raw.json")
        validate_actual_native_receipt(raw, branch=branch)
        branches[branch].extend(raw["ticks"])
        if arm == "candidate0":
            supplementary = _canonical_json(
                run_dir
                / "candidate0_supplementary_actual_native_raw.json"
            )
            validate_actual_native_receipt(
                supplementary, branch="candidate0_supplementary"
            )
            branches["candidate0_supplementary"].extend(
                supplementary["ticks"]
            )
    if {name: len(rows) for name, rows in branches.items()} != {
        "candidate0_primary": 192,
        "candidate0_supplementary": 192,
        "scene14d": 192,
        "static14d": 192,
    }:
        raise ValueError("production-equivalence branch coverage drifted")
    certificate = freeze_production_equivalence_certificate(
        implementation_head=authority["implementation_head"],
        manifest_sha256=authority["critical_implementation_manifest"][
            "manifest_sha256"
        ],
        holdout_identity_sha256=authority["holdout_identity"][
            "holdout_identity_sha256"
        ],
        experiment_protocol_sha256=authority["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        sealed_chain={
            role: {
                "path": str(canonical[role]),
                "root_sha256": roots[role],
            }
            for role in ROLES
        },
    )
    output.mkdir(parents=True)
    _write(output / "preflight.json", certificate)
    _write(
        output / "report.json",
        {
            "schema_version": (
                "camp_dp_v25_nonfresh_production_equivalence_"
                "certificate_artifact_v1"
            ),
            "status": certificate["status"],
            "implementation_head": authority["implementation_head"],
            "holdout_identity_sha256": certificate[
                "holdout_identity_sha256"
            ],
            "experiment_protocol_sha256": certificate[
                "experiment_protocol_sha256"
            ],
            "paired_unit_count": 3,
            "arm_run_count": 9,
            "tick_count": 576,
            "fresh_rows_or_outcomes_used": False,
        },
    )
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
        output, label="V25 nonFresh production-equivalence certificate"
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
    for role in ROLES:
        option = role.replace("_", "-")
        parser.add_argument(f"--{option}-artifact", type=Path, required=True)
        parser.add_argument(f"--{option}-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = build(
        artifacts={
            role: getattr(args, f"{role}_artifact") for role in ROLES
        },
        roots={
            role: getattr(args, f"{role}_root_sha256") for role in ROLES
        },
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
