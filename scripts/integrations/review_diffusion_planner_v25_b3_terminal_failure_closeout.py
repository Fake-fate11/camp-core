#!/usr/bin/env python3
"""Independently review the consumed Fresh B3 terminal-failure closeout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
    canonical_json_bytes,
    strict_equal,
    validate_fatal_artifact,
    validate_tombstone,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening import (  # noqa: E402
    FIXED_DP_HEAD,
    validate_holdout_controller_decision,
    validate_holdout_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_terminal_closeout import (  # noqa: E402
    independent_terminal_failure_review,
    validate_terminal_failure_closeout,
)


def review(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    output_dir: Path,
) -> str:
    source = Path(source_artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        source, source_root_sha256, label="Fresh B3 terminal closeout"
    )
    if set(seal["manifest_paths"]) != {
        "COMMAND",
        "HEADS",
        "closeout.json",
        "run.exit",
    }:
        raise ValueError("Fresh B3 terminal closeout inventory drifted")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B3 terminal closeout did not pass")
    closeout = validate_terminal_failure_closeout(
        _strict_canonical_json(source / "closeout.json")
    )
    bindings = {
        role: closeout[role]
        for role in (
            "controller_decision",
            "opening_release",
            "failure_artifact",
            "failure_review",
        )
    }
    for role, binding in bindings.items():
        verify_complete_seal(
            Path(binding["path"]),
            binding["root_sha256"],
            label=f"Fresh B3 closeout {role}",
        )
    controller = validate_holdout_controller_decision(
        _strict_canonical_json(
            Path(bindings["controller_decision"]["path"]) / "decision.json"
        )
    )
    release = validate_holdout_opening_release(
        _strict_canonical_json(
            Path(bindings["opening_release"]["path"]) / "decision.json"
        )
    )
    failure_path = Path(bindings["failure_artifact"]["path"])
    fatal = validate_fatal_artifact(
        _strict_canonical_json(failure_path / "fatal.json")
    )
    failure_review = _strict_canonical_json(
        Path(bindings["failure_review"]["path"]) / "report.json"
    )
    cas_path = Path(closeout["cas_tombstone_path"])
    cas = validate_tombstone(_strict_canonical_json(cas_path))
    stderr_binding = closeout["worker_stderr"]
    stderr_path = Path(stderr_binding["path"])
    stderr = stderr_path.read_text(encoding="utf-8")
    if (
        controller["holdout_identity"] != release["holdout_identity"]
        or controller["experiment_protocol"] != release["experiment_protocol"]
        or release["controller_decision_root_sha256"]
        != bindings["controller_decision"]["root_sha256"]
        or failure_review.get("status")
        != "passed_independent_holdout_artifact_fatal_review"
        or failure_review.get("reviewed_root_sha256")
        != bindings["failure_artifact"]["root_sha256"]
        or not strict_equal(cas, closeout["cas_tombstone"])
        or _file_sha256(cas_path) != closeout["cas_tombstone_sha256"]
        or _file_sha256(stderr_path) != stderr_binding["sha256"]
        or "KeyError: 'candidate_tensor_sha256_before'" not in stderr
        or "build_candidate0_pool_evidence(native)" not in stderr
    ):
        raise ValueError("Fresh B3 terminal closeout evidence drifted")
    report = independent_terminal_failure_review(
        closeout,
        fatal_artifact=fatal,
        reviewed_root_sha256=source_root_sha256,
    )
    output.mkdir(parents=True)
    (output / "report.json").write_bytes(canonical_json_bytes(report))
    (output / "HEADS").write_bytes(
        (
            f"camp_head={_git_head(ROOT)}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes(
        (" ".join(sys.argv) + "\n").encode("utf-8")
    )
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(
        output, label="independent Fresh B3 terminal failure closeout review"
    )


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
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
