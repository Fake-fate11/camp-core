#!/usr/bin/env python3
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

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    canonical_json_bytes,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preflight import (
    run_production_composition_preflight,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    FIXED_DP_HEAD,
    build_holdout_production_preflight_callback_receipt,
)


def build_artifact(
    *,
    holdout_identity_path: Path,
    experiment_protocol_path: Path,
    preflight_authority_path: Path,
    fixture_root_sha256: str,
    config_paths: dict[str, Path],
    output_dir: Path,
) -> str:
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(output)
    identity = _canonical_object(holdout_identity_path)
    protocol = _canonical_object(experiment_protocol_path)
    authority = _canonical_object(preflight_authority_path)
    configs = {arm: _canonical_object(path) for arm, path in config_paths.items()}
    payload = run_production_composition_preflight(
        holdout_identity=identity,
        experiment_protocol=protocol,
        nonfresh_preflight_authority=authority,
        fixture_root_sha256=fixture_root_sha256,
        config_payloads=configs,
        native_callback=build_holdout_production_preflight_callback_receipt,
    )
    output.mkdir(parents=True)
    (output / "preflight.json").write_bytes(canonical_json_bytes(payload))
    (output / "HEADS").write_bytes(
        (
            f"camp_head={_git_head(ROOT)}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(
        output, label="V25 holdout exact production-composition preflight"
    )


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


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdout-identity", type=Path, required=True)
    parser.add_argument("--experiment-protocol", type=Path, required=True)
    parser.add_argument("--preflight-authority", type=Path, required=True)
    parser.add_argument("--fixture-root-sha256", required=True)
    parser.add_argument("--candidate0-config", type=Path, required=True)
    parser.add_argument("--static14d-config", type=Path, required=True)
    parser.add_argument("--scene14d-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = build_artifact(
        holdout_identity_path=args.holdout_identity,
        experiment_protocol_path=args.experiment_protocol,
        preflight_authority_path=args.preflight_authority,
        fixture_root_sha256=args.fixture_root_sha256,
        config_paths={
            "candidate0": args.candidate0_config,
            "static14d": args.static14d_config,
            "scene14d": args.scene14d_config,
        },
        output_dir=args.output_dir,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
