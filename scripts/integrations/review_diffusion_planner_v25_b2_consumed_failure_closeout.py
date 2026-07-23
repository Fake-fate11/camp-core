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
    strict_equal,
    validate_tombstone,
)
from camp_core.integrations.diffusion_planner_v25_holdout_failure_closeout import (
    independent_failure_review,
    validate_consumed_holdout_failure_closeout,
)
from camp_core.integrations.diffusion_planner_v25_holdout_protocol import (
    derive_protocol_assets_from_accepted_preopen,
    validate_protocol_assets_receipt,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    FIXED_DP_HEAD,
)


def review_artifact(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    output_dir: Path,
) -> str:
    source = Path(source_artifact).resolve()
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        source, source_root_sha256, label="V25 B2 failure closeout"
    )
    if set(seal["manifest_paths"]) != {
        "CAS_TOMBSTONE_PATH",
        "COMMAND",
        "HEADS",
        "closeout.json",
        "protocol_assets_receipt.json",
        "run.exit",
    }:
        raise ValueError("B2 failure closeout inventory drifted")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("B2 failure closeout did not exit successfully")
    closeout = validate_consumed_holdout_failure_closeout(
        _canonical_object(source / "closeout.json")
    )
    protocol_receipt = validate_protocol_assets_receipt(
        _canonical_object(source / "protocol_assets_receipt.json")
    )
    independently_derived_assets, independently_derived_receipt = (
        derive_protocol_assets_from_accepted_preopen(
            preopen_artifact=Path(
                protocol_receipt["accepted_preopen"]["path"]
            ),
            preopen_root_sha256=protocol_receipt["accepted_preopen"][
                "root_sha256"
            ],
            preopen_review_artifact=Path(
                protocol_receipt["accepted_preopen_review"]["path"]
            ),
            preopen_review_root_sha256=protocol_receipt[
                "accepted_preopen_review"
            ]["root_sha256"],
        )
    )
    if (
        not strict_equal(
            independently_derived_assets,
            protocol_receipt["protocol_assets"],
        )
        or not strict_equal(
            independently_derived_receipt,
            protocol_receipt,
        )
    ):
        raise ValueError("B2 closeout protocol provenance drifted")
    protocol = closeout["experiment_protocol"]
    if any(
        protocol[name] != expected
        for name, expected in protocol_receipt["protocol_assets"].items()
    ):
        raise ValueError("B2 closeout protocol assets drifted")
    for role in ("controller_decision", "opening_release", "failure_artifact"):
        binding = closeout[role]
        verify_complete_seal(
            Path(binding["path"]),
            binding["root_sha256"],
            label=f"B2 {role}",
        )
    marker = closeout["consumed_marker"]
    if _file_sha256(Path(marker["path"])) != marker["root_sha256"]:
        raise ValueError("B2 consumed marker SHA drifted")
    cas_text = (source / "CAS_TOMBSTONE_PATH").read_text(
        encoding="utf-8"
    )
    if not cas_text.endswith("\n") or cas_text.count("\n") != 1:
        raise ValueError("B2 CAS tombstone path bytes drifted")
    cas_path = Path(cas_text[:-1])
    expected_cas = (
        Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas")
        / (
            closeout["holdout_identity"]["holdout_identity_sha256"]
            + ".json"
        )
    )
    if cas_path != expected_cas:
        raise ValueError("B2 CAS tombstone canonical path drifted")
    actual_tombstone = validate_tombstone(_canonical_object(cas_path))
    if not strict_equal(actual_tombstone, closeout["cas_tombstone"]):
        raise ValueError("B2 persistent CAS tombstone differs from closeout")
    report = independent_failure_review(
        closeout, reviewed_root_sha256=source_root_sha256
    )
    output.mkdir(parents=True)
    (output / "report.json").write_bytes(canonical_json_bytes(report))
    (output / "HEADS").write_bytes(
        (
            f"camp_head={_git_head(ROOT)}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="independent V25 B2 failure closeout review")


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
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = review_artifact(
        source_artifact=args.source_artifact,
        source_root_sha256=args.source_root_sha256,
        output_dir=args.output_dir,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
