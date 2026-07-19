#!/usr/bin/env python3
"""Create a one-shot diagnostic-only A1.7 preprojection release."""

from __future__ import annotations

import argparse
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
)
from camp_core.integrations.diffusion_planner_v25_a163_bounded_authority import (  # noqa: E402
    FIXED_DP_HEAD,
    ROOT_ROLES,
    build_a17_diagnostic_release_decision,
    canonical_json_bytes,
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-source-head", required=True)
    parser.add_argument("--pointer-head-at-release", required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--authorized-output-dir", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--diagnostic-run-ordinal", type=int, default=0)
    for role in ROOT_ROLES:
        parser.add_argument(
            f"--{role.replace('_', '-')}-artifact", type=Path, required=True
        )
        parser.add_argument(
            f"--{role.replace('_', '-')}-root-sha256", required=True
        )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    if _git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("CAMP tracked worktree is dirty")
    if _git("rev-parse", "HEAD") != args.pointer_head_at_release:
        raise ValueError("A1.7 release pointer HEAD is not the live CAMP HEAD")
    bindings = {
        role: {
            "path": str(getattr(args, f"{role}_artifact").resolve()),
            "root_sha256": getattr(args, f"{role}_root_sha256"),
            "report_file": "report.json",
        }
        for role in ROOT_ROLES
    }
    decision = build_a17_diagnostic_release_decision(
        repo=ROOT,
        implementation_source_head=args.implementation_source_head,
        pointer_head_at_release=args.pointer_head_at_release,
        root_artifacts=bindings,
        run_nonce=args.run_nonce,
        authorized_output_dir=args.authorized_output_dir,
        dp_repo=args.dp_repo,
        probe_template=args.probe_template,
        diagnostic_run_ordinal=args.diagnostic_run_ordinal,
    )
    args.output_dir.mkdir(parents=True)
    _write(args.output_dir / "decision.json", decision)
    (args.output_dir / "HEADS").write_text(
        f"camp_source_head={args.implementation_source_head}\n"
        f"camp_pointer_head={args.pointer_head_at_release}\n"
        f"fixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    (args.output_dir / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(args.output_dir, label="V25 A1.7 diagnostic-only release")
    print(json.dumps({**decision, "artifact_root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
