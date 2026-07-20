#!/usr/bin/env python3
"""Create one sealed A1.7 full-config or full-corpus execution release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v25_a17_full_corpus_authority import (  # noqa: E402
    UPSTREAM_ROLES,
    build_execute_release_decision,
    build_preflight_release_decision,
)
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (  # noqa: E402
    FIXED_DP_HEAD,
    canonical_json_bytes,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    _seal,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "execute"), required=True)
    parser.add_argument("--implementation-source-head", required=True)
    parser.add_argument("--pointer-head-at-release", required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--authorized-output-dir", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    for role in UPSTREAM_ROLES:
        option = role.replace("_", "-")
        parser.add_argument(f"--{option}-artifact", type=Path, required=True)
        parser.add_argument(f"--{option}-root-sha256", required=True)
    parser.add_argument("--preflight-artifact", type=Path)
    parser.add_argument("--preflight-root-sha256")
    parser.add_argument("--preflight-review-artifact", type=Path)
    parser.add_argument("--preflight-review-root-sha256")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    roots = {}
    for role in UPSTREAM_ROLES:
        roots[role] = {
            "path": str(getattr(args, f"{role}_artifact").resolve()),
            "root_sha256": getattr(args, f"{role}_root_sha256"),
            "report_file": (
                "decision.json" if role == "bounded_release" else "report.json"
            ),
        }
    common = {
        "repo": ROOT,
        "implementation_source_head": args.implementation_source_head,
        "pointer_head_at_release": args.pointer_head_at_release,
        "root_artifacts": roots,
        "run_nonce": args.run_nonce,
        "authorized_output_dir": args.authorized_output_dir,
        "dp_repo": args.dp_repo,
        "probe_template": args.probe_template,
    }
    if args.mode == "preflight":
        if any(
            value is not None
            for value in (
                args.preflight_artifact,
                args.preflight_root_sha256,
                args.preflight_review_artifact,
                args.preflight_review_root_sha256,
            )
        ):
            raise ValueError("preflight release cannot bind prior preflight evidence")
        decision = build_preflight_release_decision(**common)
    else:
        if any(
            value is None
            for value in (
                args.preflight_artifact,
                args.preflight_root_sha256,
                args.preflight_review_artifact,
                args.preflight_review_root_sha256,
            )
        ):
            raise ValueError("execute release requires preflight and review roots")
        decision = build_execute_release_decision(
            **common,
            preflight_artifact=args.preflight_artifact,
            preflight_root_sha256=args.preflight_root_sha256,
            preflight_review_artifact=args.preflight_review_artifact,
            preflight_review_root_sha256=args.preflight_review_root_sha256,
        )

    args.output_dir.mkdir(parents=True)
    (args.output_dir / "decision.json").write_bytes(canonical_json_bytes(decision))
    (args.output_dir / "HEADS").write_text(
        (
            f"camp_source_head={args.implementation_source_head}\n"
            f"camp_pointer_head={args.pointer_head_at_release}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ),
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "status": decision["status"],
                "output_dir": str(args.output_dir),
                "root_sha256": root,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
