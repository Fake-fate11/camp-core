"""Independently review a sealed V25 fair nonholdout contract."""

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
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_fair_nonholdout_review import (  # noqa: E402
    FIXED_DP_HEAD,
    review_contract_literal,
)


def review(
    *,
    source: Path,
    source_root: str,
    output: Path,
    fixed_dp_repo: Path,
) -> str:
    source = source.resolve()
    verify_complete_seal(source, source_root, label="fair nonholdout contract")
    if (
        _git_head(fixed_dp_repo.resolve()) != FIXED_DP_HEAD
        or _tracked_changes(fixed_dp_repo.resolve())
    ):
        raise ValueError("fixed DP authority drifted before contract review")
    source_report = _object(source / "report.json")
    contract_bytes = (source / "contract.json").read_bytes()
    contract = json.loads(contract_bytes)
    review_contract_literal(contract)
    if (
        source_report.get("status")
        != "sealed_outcome_independent_fair_nonholdout_contract"
        or source_report.get("contract") != contract
        or source_report.get("fresh_or_b4_raw_outcome_read") is not False
        or source_report.get("model_loaded_or_forward_called") is not False
        or source_report.get("selector_replay_or_closed_loop_started") is not False
        or source_report.get("training_executed") is not False
        or source_report.get("claim_authorized") is not False
    ):
        raise ValueError("fair contract artifact boundary drifted")
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        report = {
            "schema_version": (
                "camp_dp_v25_fair_nonholdout_contract_independent_review_v1"
            ),
            "status": "passed_independent_fair_nonholdout_contract_review",
            "source": {"path": str(source), "root_sha256": source_root},
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "reviewer_imported_producer_contract_module": False,
            "literal_generator_rebuilt": True,
            "literal_denominators_rebuilt": True,
            "literal_hard_stops_rebuilt": True,
            "literal_latency_and_claim_boundaries_rebuilt": True,
            "fresh_or_b4_raw_outcome_read": False,
            "model_loaded_or_forward_called": False,
            "selector_replay_or_closed_loop_started": False,
            "training_executed": False,
            "claim_authorized": False,
            "review_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
        }
        payload = (
            json.dumps(
                report,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        (staging / "report.json").write_bytes(payload)
        (staging / "HEADS.json").write_bytes(
            (
                json.dumps(
                    {
                        "review_head": report["review_head"],
                        "fixed_dp_head": FIXED_DP_HEAD,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("ascii")
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 fair nonholdout contract independent review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 fair nonholdout contract independent review",
        )
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _object(path: Path) -> dict:
    value = json.loads(path.read_text("utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must be an object")
    return value


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=repo,
            text=True,
        ).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    args = parser.parse_args()
    print(review(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
