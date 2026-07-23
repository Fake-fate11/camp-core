#!/usr/bin/env python3
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

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    canonical_json_bytes,
    install_terminal_tombstone,
)
from camp_core.integrations.diffusion_planner_v25_holdout_failure_closeout import (
    build_historical_b2_experiment_protocol,
    build_historical_b2_holdout_identity,
    freeze_consumed_holdout_failure_closeout,
    freeze_historical_b2_reservation_commitment,
)
from camp_core.integrations.diffusion_planner_v25_holdout_protocol import (
    derive_protocol_assets_from_accepted_preopen,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    FIXED_DP_HEAD,
)


def build_artifact(
    *,
    accepted_preopen_artifact: Path,
    accepted_preopen_root_sha256: str,
    accepted_preopen_review_artifact: Path,
    accepted_preopen_review_root_sha256: str,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    consumed_marker_path: Path,
    consumed_marker_sha256: str,
    failure_artifact: Path,
    failure_root_sha256: str,
    cas_root: Path,
    output_dir: Path,
) -> str:
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(output)
    for label, path, root in (
        (
            "B2 controller decision",
            controller_decision_artifact,
            controller_decision_root_sha256,
        ),
        ("B2 opening release", opening_release_artifact, opening_release_root_sha256),
        ("B2 execution failure", failure_artifact, failure_root_sha256),
    ):
        verify_complete_seal(Path(path), root, label=label)
    marker = Path(consumed_marker_path)
    if _file_sha256(marker) != consumed_marker_sha256:
        raise ValueError("B2 consumed marker SHA drifted")
    protocol_assets, protocol_receipt = (
        derive_protocol_assets_from_accepted_preopen(
            preopen_artifact=accepted_preopen_artifact,
            preopen_root_sha256=accepted_preopen_root_sha256,
            preopen_review_artifact=accepted_preopen_review_artifact,
            preopen_review_root_sha256=accepted_preopen_review_root_sha256,
        )
    )
    closeout = freeze_consumed_holdout_failure_closeout(
        benchmark="fresh_b2",
        holdout_identity=build_historical_b2_holdout_identity(),
        experiment_protocol=build_historical_b2_experiment_protocol(
            protocol_assets
        ),
        reservation_commitment_sha256=(
            freeze_historical_b2_reservation_commitment(
                controller_decision_root_sha256=(
                    controller_decision_root_sha256
                ),
                opening_release_root_sha256=opening_release_root_sha256,
                consumed_marker_sha256=consumed_marker_sha256,
                failure_artifact_root_sha256=failure_root_sha256,
            )
        ),
        controller_decision={
            "path": str(Path(controller_decision_artifact).resolve()),
            "root_sha256": controller_decision_root_sha256,
        },
        opening_release={
            "path": str(Path(opening_release_artifact).resolve()),
            "root_sha256": opening_release_root_sha256,
        },
        consumed_marker={
            "path": str(marker.resolve()),
            "root_sha256": consumed_marker_sha256,
        },
        failure_artifact={
            "path": str(Path(failure_artifact).resolve()),
            "root_sha256": failure_root_sha256,
        },
        attempted_unit_ordinal=0,
        attempted_arm="candidate0",
        raw_run_count=1,
        complete_paired_row_count=0,
    )
    cas_path = install_terminal_tombstone(
        cas_root,
        tombstone=closeout["cas_tombstone"],
    )
    output.mkdir(parents=True)
    (output / "closeout.json").write_bytes(canonical_json_bytes(closeout))
    (output / "protocol_assets_receipt.json").write_bytes(
        canonical_json_bytes(protocol_receipt)
    )
    (output / "CAS_TOMBSTONE_PATH").write_bytes(
        (str(cas_path.resolve()) + "\n").encode("utf-8")
    )
    (output / "HEADS").write_bytes(
        (
            f"camp_head={_git_head(ROOT)}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 B2 consumed holdout failure closeout")


def _canonical_object(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--accepted-preopen-artifact", type=Path, required=True
    )
    parser.add_argument("--accepted-preopen-root-sha256", required=True)
    parser.add_argument(
        "--accepted-preopen-review-artifact", type=Path, required=True
    )
    parser.add_argument(
        "--accepted-preopen-review-root-sha256", required=True
    )
    for name in ("controller-decision", "opening-release", "failure"):
        parser.add_argument(f"--{name}-artifact", type=Path, required=True)
        parser.add_argument(f"--{name}-root-sha256", required=True)
    parser.add_argument("--consumed-marker-path", type=Path, required=True)
    parser.add_argument("--consumed-marker-sha256", required=True)
    parser.add_argument(
        "--cas-root",
        type=Path,
        default=Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = build_artifact(
        accepted_preopen_artifact=args.accepted_preopen_artifact,
        accepted_preopen_root_sha256=args.accepted_preopen_root_sha256,
        accepted_preopen_review_artifact=args.accepted_preopen_review_artifact,
        accepted_preopen_review_root_sha256=(
            args.accepted_preopen_review_root_sha256
        ),
        controller_decision_artifact=args.controller_decision_artifact,
        controller_decision_root_sha256=args.controller_decision_root_sha256,
        opening_release_artifact=args.opening_release_artifact,
        opening_release_root_sha256=args.opening_release_root_sha256,
        consumed_marker_path=args.consumed_marker_path,
        consumed_marker_sha256=args.consumed_marker_sha256,
        failure_artifact=args.failure_artifact,
        failure_root_sha256=args.failure_root_sha256,
        cas_root=args.cas_root,
        output_dir=args.output_dir,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
