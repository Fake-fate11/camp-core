#!/usr/bin/env python3
"""Independently review the v24 projected-separation training retry failure."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Optional, Sequence


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.preflight_diffusion_planner_v24_convex_training import (  # noqa: E402
    _canonical_json_bytes,
    _require_clean_repo,
    verify_complete_seal,
)
from scripts.integrations.review_diffusion_planner_v24_training_execution_failure import (  # noqa: E402
    EXECUTOR_RELATIVE,
    FIXED_DP_HEAD,
    LOCKS,
    MINIMUM_FREE_BYTES,
    _git_blob,
    _lock_free,
    _running_executor_pids,
    _seal_artifact,
)


RETRY_CAMP_HEAD = "e00b66047a735604db8daaa719f44f7d5e8921cc"
RETRY_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_convex_selector_training_retry_execution_e00b6604_"
    "20260716T220822CST"
)
RETRY_ROOT_SHA256 = (
    "4f7b28cfbb24c49dd9682d899acf32dd87016d6050e6acab059703d236d3c1c3"
)
AUTHORIZATION_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_training_projection_repair_static_preflight_independent_review_"
    "a325b687_20260716T220107CST"
)
AUTHORIZATION_ROOT_SHA256 = (
    "6cd16510b7cf2c82277d086271a56ebc36a803a5db2ce1a2289e86616bbe2e13"
)
REVIEWER_RELATIVE = (
    "scripts/integrations/review_diffusion_planner_v24_training_retry_failure.py"
)
AUDIT_RELATIVE = Path("docs/diffusion_planner_v24_iteration_audit.md")


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def diagnose_master_vs_cut_gap(source: str) -> dict[str, bool]:
    tree = ast.parse(source)
    functions = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    solve = functions.get("solve_v24_cutting_plane", "")
    accept = functions.get("accepted_weights_and_gap", "")
    diagnosis = {
        "projected_cut_separation_present": (
            "projected_worst" in solve and "projected_gap[row]" in solve
        ),
        "projected_gap_is_relative_to_master_losses": (
            "projected_true_losses - master_losses" in solve
        ),
        "cut_relative_gap_computed_during_separation": (
            "cut_and_full_losses" in solve
        ),
        "cut_relative_gap_required_during_acceptance": (
            "cut_and_full_losses" in accept
            and "projected saved-weight full-K gap exceeds tolerance" in accept
        ),
    }
    if diagnosis != {
        "projected_cut_separation_present": True,
        "projected_gap_is_relative_to_master_losses": True,
        "cut_relative_gap_computed_during_separation": False,
        "cut_relative_gap_required_during_acceptance": True,
    }:
        raise ValueError("retry-source master-vs-cut diagnosis drift")
    return diagnosis


def review_retry_failure(
    *, repo: Path, dp_repo: Path, current_camp_head: str
) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("v24 retry-failure review requires AutoDL")
    _require_clean_repo(repo, current_camp_head)
    _require_clean_repo(dp_repo, FIXED_DP_HEAD)
    retry_files = verify_complete_seal(RETRY_ARTIFACT, RETRY_ROOT_SHA256)
    authorization_files = verify_complete_seal(
        AUTHORIZATION_ARTIFACT, AUTHORIZATION_ROOT_SHA256
    )
    if (
        (RETRY_ARTIFACT / "run.exit").read_text(encoding="ascii") != "1\n"
        or (RETRY_ARTIFACT / "stdout.txt").read_text(encoding="utf-8") != ""
        or (RETRY_ARTIFACT / "stderr.txt").read_text(encoding="utf-8")
        != "RuntimeError: projected saved-weight full-K gap exceeds tolerance\n"
    ):
        raise ValueError("v24 retry failure execution receipt drift")
    failure = _read_json(RETRY_ARTIFACT / "failure.json")
    progress = _read_json(RETRY_ARTIFACT / "progress.json")
    names = {path.name for path in RETRY_ARTIFACT.iterdir()}
    if (
        failure.get("status") != "failed"
        or failure.get("camp_head") != RETRY_CAMP_HEAD
        or failure.get("fixed_dp_head") != FIXED_DP_HEAD
        or failure.get("failure_reason")
        != "projected saved-weight full-K gap exceeds tolerance"
        or failure.get("calibration_accessed") is not False
        or failure.get("holdout_opened") is not False
        or failure.get("actual_closed_loop_outcomes_read") is not False
        or progress.get("phase") != "training_failed"
        or progress.get("completed_levels") != []
        or progress.get("training_execution_active") is not False
        or "models" in names
        or "training_manifest.json" in names
    ):
        raise ValueError("v24 retry failure boundary receipt drift")
    authorization = _read_json(AUTHORIZATION_ARTIFACT / "review.json")
    retry_source = _git_blob(repo, RETRY_CAMP_HEAD, EXECUTOR_RELATIVE).decode("utf-8")
    if (
        authorization.get("status") != "passed"
        or authorization.get("decision", {}).get("training_retry_authorized")
        is not True
        or authorization.get("executor_source_sha256")
        != hashlib.sha256(retry_source.encode("utf-8")).hexdigest()
    ):
        raise ValueError("v24 retry source authorization drift")
    eof = dict(
        line.split("=", 1)
        for line in (repo / AUDIT_RELATIVE).read_text(encoding="utf-8").rstrip().splitlines()[
            -15:
        ]
        if "=" in line
    )
    if (
        eof.get("current_v24_status")
        != "v24_convex_training_projection_boundary_repair_static_preflight_independent_review_passed"
        or eof.get("current_v24_artifact") != str(AUTHORIZATION_ARTIFACT)
        or eof.get("current_v24_artifact_root_sha256")
        != AUTHORIZATION_ROOT_SHA256
        or eof.get("next_work_target")
        != "v24_convex_selector_training_retry_execution_only"
    ):
        raise ValueError("live v24 EOF drifted before retry-failure review")
    diagnosis = diagnose_master_vs_cut_gap(retry_source)
    reviewer_live = (repo / REVIEWER_RELATIVE).read_bytes()
    if reviewer_live != _git_blob(repo, current_camp_head, REVIEWER_RELATIVE):
        raise ValueError("retry-failure reviewer is not tracked at current HEAD")
    running = _running_executor_pids()
    lock_free = [_lock_free(path) for path in LOCKS]
    free_bytes = shutil.disk_usage(RETRY_ARTIFACT.parent).free
    if running or not all(lock_free) or free_bytes <= MINIMUM_FREE_BYTES:
        raise RuntimeError("post-retry process/lock/disk gate failed")
    checks = [
        "retry_failure_complete_seal",
        "retry_authorization_complete_seal",
        "failure_exit_and_stderr",
        "terminal_zero-level_progress",
        "no_model_or_manifest",
        "closed_calibration_holdout_outcomes",
        "retry_source_sha",
        "reviewer_current_head_sha",
        "projected_separation_confirmed",
        "master_relative_gap_confirmed",
        "acceptance_cut_relative_gap_confirmed",
        "no_executor_process",
        "all_locks_free",
        "disk_floor_passed",
    ]
    return {
        "schema": "camp_dp_v24_convex_training_retry_failure_review_v1",
        "status": "passed",
        "camp_head": current_camp_head,
        "retry_camp_head": RETRY_CAMP_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_retry_artifact": str(RETRY_ARTIFACT),
        "source_retry_root_sha256": RETRY_ROOT_SHA256,
        "source_retry_verified_file_count": len(retry_files),
        "source_authorization_artifact": str(AUTHORIZATION_ARTIFACT),
        "source_authorization_root_sha256": AUTHORIZATION_ROOT_SHA256,
        "source_authorization_verified_file_count": len(authorization_files),
        "retry_executor_source_sha256": hashlib.sha256(
            retry_source.encode("utf-8")
        ).hexdigest(),
        "reviewer_source_sha256": hashlib.sha256(reviewer_live).hexdigest(),
        "diagnosis": diagnosis,
        "passed_checks": checks,
        "passed_count": len(checks),
        "failed_count": 0,
        "running_executor_pids": running,
        "lock_free": lock_free,
        "free_bytes": free_bytes,
        "minimum_free_bytes": MINIMUM_FREE_BYTES,
        "model_produced": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "actual_closed_loop_outcomes_read": False,
        "claim_authorized": False,
        "repair_contract": {
            "separate_on_raw_and_projected_full_minus_cut_gap": True,
            "retain_raw_and_projected_master_gap_diagnostics": True,
            "require_all_four_gaps_at_most_1e-6": True,
            "retain_exact_20_iteration_cap": True,
            "retain_clarabel_optimal_only_no_fallback": True,
            "protocol_or_data_change_authorized": False,
        },
        "decision": {
            "cut_relative_gap_repair_tdd_static_preflight_authorized": True,
            "training_retry_authorized": False,
            "calibration_authorized": False,
            "holdout_authorized": False,
            "claim_authorized": False,
        },
        "next_work_target": (
            "v24_convex_training_cut_relative_gap_repair_tdd_static_preflight_only"
        ),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError("v24 retry-failure review target already exists")
    result = review_retry_failure(
        repo=args.repo, dp_repo=args.dp_repo, current_camp_head=args.camp_head
    )
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "review.json").write_bytes(_canonical_json_bytes(result))
    (args.output_dir / "review.md").write_text(
        "# V24 Convex Training Retry Failure Review\n\n"
        "- status: `passed`\n"
        "- model: `not produced`\n"
        "- diagnosis: `master-relative separation vs cut-relative acceptance`\n"
        "- next: `cut-relative gap repair TDD/static preflight only`\n",
        encoding="utf-8",
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (args.output_dir / "stdout.txt").write_text(
        json.dumps(
            {"status": "passed", "next_work_target": result["next_work_target"]},
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root_sha256 = _seal_artifact(args.output_dir)
    print(json.dumps({"artifact_root_sha256": root_sha256}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
