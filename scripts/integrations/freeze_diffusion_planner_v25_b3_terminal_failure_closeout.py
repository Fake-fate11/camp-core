#!/usr/bin/env python3
"""Seal the consumed Fresh B3 engineering-failure closeout."""

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

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
    canonical_json_bytes,
    validate_fatal_artifact,
    validate_tombstone,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening import (  # noqa: E402
    FIXED_DP_HEAD,
    validate_holdout_controller_decision,
    validate_holdout_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_terminal_closeout import (  # noqa: E402
    freeze_terminal_failure_closeout,
)


def build(
    *,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    failure_artifact: Path,
    failure_root_sha256: str,
    failure_review_artifact: Path,
    failure_review_root_sha256: str,
    cas_tombstone_path: Path,
    worker_stderr_path: Path,
    output_dir: Path,
) -> str:
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    bindings = {
        "controller_decision": (
            Path(controller_decision_artifact).resolve(),
            controller_decision_root_sha256,
        ),
        "opening_release": (
            Path(opening_release_artifact).resolve(),
            opening_release_root_sha256,
        ),
        "failure_artifact": (
            Path(failure_artifact).resolve(),
            failure_root_sha256,
        ),
        "failure_review": (
            Path(failure_review_artifact).resolve(),
            failure_review_root_sha256,
        ),
    }
    for label, (path, root) in bindings.items():
        verify_complete_seal(path, root, label=f"Fresh B3 {label}")
    if (
        (bindings["controller_decision"][0] / "run.exit").read_bytes()
        != b"0\n"
        or (bindings["opening_release"][0] / "run.exit").read_bytes()
        != b"0\n"
        or (bindings["failure_artifact"][0] / "run.exit").read_bytes()
        != b"1\n"
        or (bindings["failure_review"][0] / "run.exit").read_bytes()
        != b"0\n"
    ):
        raise ValueError("Fresh B3 closeout input exit code drifted")
    controller = validate_holdout_controller_decision(
        _strict_canonical_json(
            bindings["controller_decision"][0] / "decision.json"
        )
    )
    release = validate_holdout_opening_release(
        _strict_canonical_json(
            bindings["opening_release"][0] / "decision.json"
        )
    )
    fatal = validate_fatal_artifact(
        _strict_canonical_json(bindings["failure_artifact"][0] / "fatal.json")
    )
    failure_review = _strict_canonical_json(
        bindings["failure_review"][0] / "report.json"
    )
    if (
        controller["holdout_identity"] != release["holdout_identity"]
        or controller["experiment_protocol"] != release["experiment_protocol"]
        or release["controller_decision_root_sha256"]
        != controller_decision_root_sha256
        or failure_review.get("status")
        != "passed_independent_holdout_artifact_fatal_review"
        or failure_review.get("reviewed_root_sha256") != failure_root_sha256
    ):
        raise ValueError("Fresh B3 closeout authority chain drifted")
    cas_path = Path(cas_tombstone_path).resolve()
    tombstone = validate_tombstone(_strict_canonical_json(cas_path))
    stderr_path = Path(worker_stderr_path).resolve()
    stderr = stderr_path.read_text(encoding="utf-8")
    if (
        "KeyError: 'candidate_tensor_sha256_before'" not in stderr
        or "build_candidate0_pool_evidence(native)" not in stderr
    ):
        raise ValueError("Fresh B3 worker failure signature drifted")
    closeout = freeze_terminal_failure_closeout(
        benchmark="fresh_b3",
        holdout_identity_sha256=release["holdout_identity"][
            "holdout_identity_sha256"
        ],
        experiment_protocol_sha256=release["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        run_nonce=release["run_nonce"],
        controller_decision=_binding(*bindings["controller_decision"]),
        opening_release=_binding(*bindings["opening_release"]),
        failure_artifact=_binding(*bindings["failure_artifact"]),
        failure_review=_binding(*bindings["failure_review"]),
        cas_tombstone_path=str(cas_path),
        cas_tombstone_sha256=_file_sha256(cas_path),
        cas_tombstone=tombstone,
        worker_stderr={
            "path": str(stderr_path),
            "sha256": _file_sha256(stderr_path),
        },
        fatal_artifact=fatal,
    )
    output.mkdir(parents=True)
    (output / "closeout.json").write_bytes(canonical_json_bytes(closeout))
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
    return seal_artifact(output, label="Fresh B3 terminal failure closeout")


def _binding(path: Path, root: str) -> dict[str, str]:
    return {"path": str(path), "root_sha256": root}


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
    for name in (
        "controller-decision",
        "opening-release",
        "failure",
        "failure-review",
    ):
        parser.add_argument(f"--{name}-artifact", type=Path, required=True)
        parser.add_argument(f"--{name}-root-sha256", required=True)
    parser.add_argument("--cas-tombstone-path", type=Path, required=True)
    parser.add_argument("--worker-stderr-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = build(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
