"""Freeze a V26-native, route-disjoint development comparison inventory.

This entry is identity-only and zero-model.  It reads authoritative source
maps plus final training-population identities; it never reads training rows,
candidate/label/trajectory/outcome payloads, or holdout data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_development_comparison_inventory import (  # noqa: E402
    build_development_comparison_inventory,
    collect_v26_source_authoritative_candidates,
    require_selection_rebuild_stability,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (  # noqa: E402
    V25_ZERO_SHOT_REFERENCE_READ_ONLY,
    V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, encoding="utf-8"
    ).strip()


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _load_json(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    return value


def _adapted_selector_identity(receipt_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = _load_json(receipt_path, "V26 adaptation receipt")
    if (
        receipt.get("schema_version") != "camp_dp_v26_selector_adaptation_receipt_v1"
        or receipt.get("evidence_role") != "development_train_only_selector_adaptation"
        or receipt.get("terminal", {}).get("status") != "complete"
        or receipt.get("weight_roles", {}).get("adapted")
        != V26_ADAPTED_WEIGHTS_SCHEMA_VERSION
        or receipt.get("weight_roles", {}).get("reference")
        != V25_ZERO_SHOT_REFERENCE_READ_ONLY
    ):
        raise ValueError("V26 adapted selector receipt identity drifted")
    assets = receipt.get("adapted_assets")
    if type(assets) is not dict or set(assets) != {
        "parameters",
        "model_reports",
        "runtime_atom_scales",
        "static14d_runtime_weights",
    }:
        raise ValueError("V26 adapted selector assets are incomplete")
    for item in assets.values():
        if type(item) is not dict or type(item.get("sha256")) is not str:
            raise ValueError("V26 adapted selector asset binding is invalid")
        if type(item.get("path")) is str:
            path = Path(item["path"])
        elif type(item.get("relative_path")) is str:
            relative = Path(item["relative_path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("V26 adapted selector relative asset path is unsafe")
            path = receipt_path.parent / relative
        else:
            raise ValueError("V26 adapted selector asset path is invalid")
        if not path.is_file() or _sha256_file(path) != item["sha256"]:
            raise ValueError("V26 adapted selector asset hash drifted")
    manifest = dict(receipt.get("manifest", {}))
    reference = manifest.get("reference")
    if type(reference) is not dict:
        raise ValueError("V26 zero-shot reference identity is unavailable")
    adapted = {
        "artifact_role": V26_ADAPTED_WEIGHTS_SCHEMA_VERSION,
        "adaptation_receipt_path": str(receipt_path.resolve()),
        "adaptation_receipt_sha256": _sha256_file(receipt_path),
        "camp_head": manifest.get("camp_head"),
        "assets": assets,
    }
    reference_identity = {
        "artifact_role": V25_ZERO_SHOT_REFERENCE_READ_ONLY,
        "reference": reference,
    }
    return adapted, reference_identity


def run(args: argparse.Namespace) -> Path:
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if _git_head(ROOT) != args.expected_camp_head:
        raise ValueError("V26 development inventory CAMP head drifted")
    training_population_path = args.training_population.resolve()
    revision_plan_path = args.revision_plan.resolve()
    training_population = _load_json(training_population_path, "training population")
    revision_plan = _load_json(revision_plan_path, "revision plan")
    checkpoint = args.fixed_dp_checkpoint.resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    adapted, reference = _adapted_selector_identity(args.adaptation_receipt.resolve())
    collection = collect_v26_source_authoritative_candidates(
        training_population=training_population,
        revision_plan=revision_plan,
        fixed_dp_repo=args.fixed_dp_repo.resolve(),
    )
    manifest = build_development_comparison_inventory(
        source_collection=collection,
        camp_head=args.expected_camp_head,
        fixed_dp_checkpoint={"path": str(checkpoint), "sha256": _sha256_file(checkpoint)},
        adapted_selector=adapted,
        reference_selector=reference,
        final_training_population_sha256=_sha256_file(training_population_path),
        revision_plan_sha256=_sha256_file(revision_plan_path),
    )
    if args.prior_inventory is not None:
        require_selection_rebuild_stability(
            previous=_load_json(args.prior_inventory.resolve(), "prior V26 inventory"),
            rebuilt=manifest,
        )
    _atomic_write_json(output, manifest)
    return output


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--training-population", type=Path, required=True)
    parser.add_argument("--revision-plan", type=Path, required=True)
    parser.add_argument("--adaptation-receipt", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--fixed-dp-checkpoint", type=Path, required=True)
    parser.add_argument("--expected-camp-head", required=True)
    parser.add_argument(
        "--prior-inventory",
        type=Path,
        help="identity-only prior inventory whose ordered selection must remain byte-stable",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    output = run(parse_args(argv))
    print(json.dumps({"status": "prepared_identity_only_no_execution_no_claim", "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
