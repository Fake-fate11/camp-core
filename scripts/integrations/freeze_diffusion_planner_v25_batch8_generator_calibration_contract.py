"""Seal corrected same-input/same-latent repeatability contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration import (  # noqa: E402
    EXACT_DIRS,
    FIXED_DP_HEAD,
    contract,
    validate_contract,
)

SOURCE_PATHS = {
    "producer_module": "camp_core/camp_core/integrations/diffusion_planner_v25_batch8_generator_calibration.py",
    "reviewer_module": "camp_core/camp_core/integrations/diffusion_planner_v25_batch8_generator_calibration_review.py",
    "freeze_script": "scripts/integrations/freeze_diffusion_planner_v25_batch8_generator_calibration_contract.py",
    "contract_review_script": "scripts/integrations/review_diffusion_planner_v25_batch8_generator_calibration_contract.py",
    "preflight_script": "scripts/integrations/materialize_diffusion_planner_v25_batch8_generator_calibration_preflight.py",
    "preflight_review_script": "scripts/integrations/review_diffusion_planner_v25_batch8_generator_calibration_preflight.py",
    "raw_script": "scripts/integrations/materialize_diffusion_planner_v25_batch8_generator_calibration_raw.py",
    "raw_review_script": "scripts/integrations/review_diffusion_planner_v25_batch8_generator_calibration_raw.py",
    "threshold_script": "scripts/integrations/materialize_diffusion_planner_v25_batch8_generator_calibration_threshold.py",
    "threshold_review_script": "scripts/integrations/review_diffusion_planner_v25_batch8_generator_calibration_threshold.py",
    "tests": "camp_core/tests/test_diffusion_planner_v25_batch8_generator_calibration.py",
}


def freeze(output: Path, fixed_dp_repo: Path) -> str:
    head = _git(ROOT, "rev-parse", "HEAD")
    if _git(ROOT, "status", "--porcelain=v1", "--untracked-files=no"):
        raise RuntimeError("CAMP tracked authority dirty")
    if _git(fixed_dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD:
        raise RuntimeError("fixed DP HEAD drifted")
    if _git(fixed_dp_repo, "status", "--porcelain=v1", "--untracked-files=no"):
        raise RuntimeError("fixed DP tracked authority dirty")
    sources = {
        key: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        for key, rel in SOURCE_PATHS.items()
    }
    value = validate_contract(contract(
        implementation_head=head, source_sha256=sources
    ))
    report = {
        "schema_version": "camp_dp_v25_batch8_generator_repeatability_corrected_contract_artifact_v1",
        "status": "PASS",
        "contract": value,
        "source_paths": SOURCE_PATHS,
        "fixed_dp_head": FIXED_DP_HEAD,
        "model_pool_selector_call_count": 0,
        "outcome_values_read": False,
    }
    return _atomic(
        output, report, "V25 corrected batch8 generator repeatability contract"
    )


def _atomic(output: Path, report: dict, label: str) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent))
    try:
        (staging / "report.json").write_bytes(
            (json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")
        )
        (staging / "HEADS.json").write_bytes(
            (json.dumps(
                {"implementation_head": report["contract"]["implementation_head"],
                 "fixed_dp_head": FIXED_DP_HEAD, "role": "contract"},
                sort_keys=True, separators=(",", ":")
            ) + "\n").encode("ascii")
        )
        root = seal_artifact(staging, label=label)
        os.replace(staging, output)
        verify_complete_seal(output, root, label=label)
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(EXACT_DIRS["contract"]))
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    args = parser.parse_args()
    print(freeze(args.output, args.fixed_dp_repo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
