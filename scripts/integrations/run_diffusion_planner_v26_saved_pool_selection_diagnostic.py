"""Run the V26 outcome-blind saved-pool selector-input diagnostic.

This entry reads reviewed training-only saved B8 pools and frozen zero-shot
weights.  It does not construct Diffusion Planner, invoke a model/DP forward,
or write into either source artifact.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v26_selector_adaptation import (  # noqa: E402
    SAVED_POOL_DIAGNOSTIC_ROLE,
    build_saved_pool_selection_diagnostic,
    load_train_only_saved_pools,
    load_zero_shot_reference_assets,
)


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def run(args: argparse.Namespace) -> Path:
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    try:
        pools = load_train_only_saved_pools(args.training_source)
        reference = load_zero_shot_reference_assets(args.reference_training)
        receipt = build_saved_pool_selection_diagnostic(pools, reference)
        _atomic_write_json(output_dir / "receipt.json", receipt)
        _atomic_write_json(
            output_dir / "run.status.json",
            {
                "evidence_role": SAVED_POOL_DIAGNOSTIC_ROLE,
                "status": "complete_no_model_invocation",
                "model_dp_latent_generation_calls": 0,
            },
        )
        (output_dir / "run.exit").write_text("0\n", encoding="ascii")
        return output_dir
    except BaseException as exc:
        _atomic_write_json(
            output_dir / "run.status.json",
            {
                "evidence_role": SAVED_POOL_DIAGNOSTIC_ROLE,
                "status": "typed_failure_no_model_invocation",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "model_dp_latent_generation_calls": 0,
            },
        )
        (output_dir / "run.exit").write_text("1\n", encoding="ascii")
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--training-source", type=Path, required=True)
    parser.add_argument("--reference-training", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    output = run(parse_args(argv))
    print(
        json.dumps(
            {
                "status": "complete_no_model_invocation",
                "output_dir": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
