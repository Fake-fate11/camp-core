#!/usr/bin/env python3
"""Independently review the sealed 1500-identity V25 full-R config preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORPUS_STEPS,
    EXPECTED_EXECUTABLE_IDENTITIES,
    EXPECTED_RETAINED_INELIGIBLE,
    SCHEMA_VERSION as EXECUTION_SCHEMA_VERSION,
    _canonical_sha256,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_full_config_preflight_review_v1"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def review(preflight: Path, expected_root: str) -> dict[str, Any]:
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    seal = verify_complete_seal(
        preflight, expected_root, label="V25 full-config preflight"
    )
    report = _load(preflight / "report.json")
    source = _load(preflight / "source_receipt.json")
    receipts = report.get("config_receipts")
    if (
        (preflight / "run.exit").read_text(encoding="ascii") != "0\n"
        or source != report
        or report.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or report.get("status") != "passed"
        or report.get("mode") != "preflight"
        or report.get("camp_head") != head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("validated_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("formal_train_manifest_identity_count")
        != EXPECTED_EXECUTABLE_IDENTITIES + EXPECTED_RETAINED_INELIGIBLE
        or report.get("source_ineligible_retained_identity_count")
        != EXPECTED_RETAINED_INELIGIBLE
        or report.get("corpus_steps") != CORPUS_STEPS
        or report.get("snapshot_capacity")
        != EXPECTED_EXECUTABLE_IDENTITIES * CORPUS_STEPS
        or report.get("model_loaded") is not False
        or report.get("candidate_generation_started") is not False
        or report.get("training_executed") is not False
        or report.get("calibration_executed") is not False
        or report.get("fresh_b_opened") is not False
        or report.get("outcome_fields_consumed") != []
        or not isinstance(receipts, list)
        or len(receipts) != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("config_receipts_root_sha256")
        != _canonical_sha256(receipts)
    ):
        raise ValueError("full-config preflight report contract drifted")
    seen: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise ValueError("config receipt is not an object")
        payload = {
            key: value
            for key, value in receipt.items()
            if key != "config_authority_sha256"
        }
        scenario_id = receipt.get("scenario_id")
        if (
            not isinstance(scenario_id, str)
            or len(scenario_id) != 64
            or scenario_id in seen
            or receipt.get("config_authority_sha256")
            != _canonical_sha256(payload)
            or receipt.get("fixed_dp_head") != FIXED_DP_HEAD
            or receipt.get("corpus_steps") != CORPUS_STEPS
            or receipt.get("signal_source_chain_sha256") is None
            or receipt.get("selector_training_execution_authorized") is not False
            or receipt.get("calibration_authorized") is not False
            or receipt.get("holdout_access_authorized") is not False
            or receipt.get("fresh_b_opened") is not False
            or receipt.get("outcome_fields_consumed") != []
        ):
            raise ValueError("config receipt authority drifted")
        seen.add(scenario_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_1500_config_preflight_review_execute_closed",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(preflight),
        "reviewed_root_sha256": seal["root_sha256"],
        "identity_count": EXPECTED_EXECUTABLE_IDENTITIES,
        "executable_config_count": EXPECTED_EXECUTABLE_IDENTITIES,
        "retained_source_ineligible_count": (
            EXPECTED_RETAINED_INELIGIBLE
        ),
        "corpus_steps": CORPUS_STEPS,
        "full_r_execute_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-artifact", type=Path, required=True)
    parser.add_argument("--preflight-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args.preflight_artifact, args.preflight_root_sha256)
        _write(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 full-config preflight review")
        print(json.dumps({"status": report["status"], "root_sha256": root}))
    except BaseException as exc:
        _write(
            args.output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 failed full-config preflight review")
        raise


if __name__ == "__main__":
    main()
