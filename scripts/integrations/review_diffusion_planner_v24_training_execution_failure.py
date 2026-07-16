#!/usr/bin/env python3
"""Independently review the first v24 convex-training execution failure."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Optional, Sequence


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.preflight_diffusion_planner_v24_convex_training import (  # noqa: E402
    _canonical_json_bytes,
    _file_sha256,
    _require_clean_repo,
    verify_complete_seal,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FAILURE_CAMP_HEAD = "c61fc9c62866fdb335b2490d19443c7126a70120"
FAILURE_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_convex_selector_training_execution_c61fc9c6_20260716T214429CST"
)
FAILURE_ROOT_SHA256 = (
    "275f5a652173f95e6ee3ef34b4b7954703799e5e4c5d8c575648aa6e9227d866"
)
AUTHORIZATION_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_training_executor_static_preflight_independent_review_80e971d5_"
    "20260716T213922CST"
)
AUTHORIZATION_ROOT_SHA256 = (
    "ee73c6611fbf369e09f29f2fc9d852815ba15bb8e2077299aef524667de3cce7"
)
EXECUTOR_RELATIVE = "scripts/integrations/train_diffusion_planner_v24_selector.py"
REVIEWER_RELATIVE = (
    "scripts/integrations/review_diffusion_planner_v24_training_execution_failure.py"
)
AUDIT_RELATIVE = Path("docs/diffusion_planner_v24_iteration_audit.md")
LOCKS = (
    Path("/root/autodl-tmp/.camp_dp_v24_convex_training.lock"),
    Path("/root/autodl-tmp/.camp_dp_v24_native_corpus_remaining.lock"),
    Path("/root/autodl-tmp/.camp_dp_v24_training_label_materialization.lock"),
)
MINIMUM_FREE_BYTES = 10 * 1024**3


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _git_blob(repo: Path, head: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def diagnose_projection_boundary(source: str) -> dict[str, bool]:
    tree = ast.parse(source)
    functions = {
        node.name: ast.get_source_segment(source, node) or ""
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    solve = functions.get("solve_v24_cutting_plane", "")
    accept = functions.get("accepted_weights_and_gap", "")
    diagnosis = {
        "cut_generation_uses_raw_weights": (
            "atoms, raw_weights, oracle, margin_values, feasible" in solve
        ),
        "cut_generation_projects_weights": "project_simplex_rows" in solve,
        "acceptance_projects_weights": "project_simplex_rows(raw)[0]" in accept,
        "acceptance_recomputes_full_k": "cut_and_full_losses" in accept,
        "acceptance_rejects_projected_gap": (
            "projected saved-weight full-K gap exceeds tolerance" in accept
        ),
    }
    if diagnosis != {
        "cut_generation_uses_raw_weights": True,
        "cut_generation_projects_weights": False,
        "acceptance_projects_weights": True,
        "acceptance_recomputes_full_k": True,
        "acceptance_rejects_projected_gap": True,
    }:
        raise ValueError("failure-source projection-boundary diagnosis drift")
    return diagnosis


def _lock_free(path: Path) -> bool:
    import fcntl

    with Path(path).open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _running_executor_pids() -> list[int]:
    result = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            argv = (item / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        values = [part.decode("utf-8", errors="replace") for part in argv if part]
        if any(
            value == EXECUTOR_RELATIVE or value.endswith("/" + EXECUTOR_RELATIVE)
            for value in values
        ):
            result.append(int(item.name))
    return sorted(result)


def _seal_artifact(root: Path) -> str:
    sums = root / "SHA256SUMS"
    receipt = root / "ROOT_SHA256SUMS"
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("failure-review symlink is forbidden")
        if path.is_file() and path not in {sums, receipt}:
            if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
                raise ValueError("nested failure-review manifest is forbidden")
            files.append(path)
    files.sort()
    sums.write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(sums)
    receipt.write_text(f"{digest}  SHA256SUMS\n", encoding="ascii")
    return digest


def review_failure(
    *, repo: Path, dp_repo: Path, current_camp_head: str
) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("v24 failure review requires AutoDL")
    _require_clean_repo(repo, current_camp_head)
    _require_clean_repo(dp_repo, FIXED_DP_HEAD)
    failure_files = verify_complete_seal(FAILURE_ARTIFACT, FAILURE_ROOT_SHA256)
    authorization_files = verify_complete_seal(
        AUTHORIZATION_ARTIFACT, AUTHORIZATION_ROOT_SHA256
    )
    if (
        (FAILURE_ARTIFACT / "run.exit").read_text(encoding="ascii") != "1\n"
        or (FAILURE_ARTIFACT / "stdout.txt").read_text(encoding="utf-8") != ""
        or (FAILURE_ARTIFACT / "stderr.txt").read_text(encoding="utf-8")
        != "RuntimeError: projected saved-weight full-K gap exceeds tolerance\n"
    ):
        raise ValueError("v24 failure execution receipt drift")
    failure = _read_json(FAILURE_ARTIFACT / "failure.json")
    progress = _read_json(FAILURE_ARTIFACT / "progress.json")
    names = {path.name for path in FAILURE_ARTIFACT.iterdir()}
    if (
        failure.get("schema")
        != "camp_dp_v24_convex_training_execution_failure_v1"
        or failure.get("status") != "failed"
        or failure.get("failure_type") != "RuntimeError"
        or failure.get("failure_reason")
        != "projected saved-weight full-K gap exceeds tolerance"
        or failure.get("camp_head") != FAILURE_CAMP_HEAD
        or failure.get("fixed_dp_head") != FIXED_DP_HEAD
        or failure.get("training_execution_attempted") is not True
        or failure.get("calibration_accessed") is not False
        or failure.get("holdout_opened") is not False
        or failure.get("actual_closed_loop_outcomes_read") is not False
        or failure.get("claim_authorized") is not False
        or progress.get("phase") != "training_failed"
        or progress.get("training_execution_active") is not False
        or progress.get("completed_levels") != []
        or "models" in names
        or "training_manifest.json" in names
    ):
        raise ValueError("v24 failure boundary receipt drift")
    authorization = _read_json(AUTHORIZATION_ARTIFACT / "review.json")
    if (
        authorization.get("status") != "passed"
        or authorization.get("decision", {}).get("training_execution_authorized")
        is not True
        or authorization.get("executor_source_sha256")
        != hashlib.sha256(
            _git_blob(repo, FAILURE_CAMP_HEAD, EXECUTOR_RELATIVE)
        ).hexdigest()
    ):
        raise ValueError("v24 failure source authorization drift")
    eof = dict(
        line.split("=", 1)
        for line in (repo / AUDIT_RELATIVE).read_text(encoding="utf-8").rstrip().splitlines()[
            -15:
        ]
        if "=" in line
    )
    if (
        eof.get("current_v24_status")
        != "v24_convex_training_executor_static_preflight_independent_review_passed"
        or eof.get("current_v24_artifact") != str(AUTHORIZATION_ARTIFACT)
        or eof.get("current_v24_artifact_root_sha256")
        != AUTHORIZATION_ROOT_SHA256
        or eof.get("next_work_target")
        != "v24_convex_selector_training_execution_only"
    ):
        raise ValueError("live v24 EOF drifted before failure review")
    failure_source = _git_blob(repo, FAILURE_CAMP_HEAD, EXECUTOR_RELATIVE).decode(
        "utf-8"
    )
    diagnosis = diagnose_projection_boundary(failure_source)
    reviewer_live = (repo / REVIEWER_RELATIVE).read_bytes()
    reviewer_current = _git_blob(repo, current_camp_head, REVIEWER_RELATIVE)
    if reviewer_live != reviewer_current:
        raise ValueError("failure reviewer is not tracked at current HEAD")
    running = _running_executor_pids()
    lock_free = [_lock_free(path) for path in LOCKS]
    free_bytes = shutil.disk_usage(FAILURE_ARTIFACT.parent).free
    if running or not all(lock_free) or free_bytes <= MINIMUM_FREE_BYTES:
        raise RuntimeError("post-failure process/lock/disk gate failed")
    checks = [
        "failure_complete_seal",
        "authorization_complete_seal",
        "failure_exit_and_stderr",
        "terminal_progress",
        "zero_completed_levels",
        "no_model_or_manifest",
        "closed_calibration_holdout_outcomes",
        "failure_source_sha",
        "reviewer_current_head_sha",
        "raw_cut_generation_confirmed",
        "projected_acceptance_confirmed",
        "no_executor_process",
        "all_locks_free",
        "disk_floor_passed",
    ]
    return {
        "schema": "camp_dp_v24_convex_training_execution_failure_review_v1",
        "status": "passed",
        "camp_head": current_camp_head,
        "failure_camp_head": FAILURE_CAMP_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_failure_artifact": str(FAILURE_ARTIFACT),
        "source_failure_root_sha256": FAILURE_ROOT_SHA256,
        "source_failure_verified_file_count": len(failure_files),
        "source_authorization_artifact": str(AUTHORIZATION_ARTIFACT),
        "source_authorization_root_sha256": AUTHORIZATION_ROOT_SHA256,
        "source_authorization_verified_file_count": len(authorization_files),
        "failure_executor_source_sha256": hashlib.sha256(
            failure_source.encode("utf-8")
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
            "project_weights_before_cut_separation": True,
            "require_raw_and_projected_full_k_gap_at_most_1e-6": True,
            "retain_exact_20_iteration_cap": True,
            "retain_clarabel_optimal_only_no_fallback": True,
            "record_raw_and_projected_gap_diagnostics": True,
            "protocol_or_data_change_authorized": False,
        },
        "decision": {
            "projection_boundary_repair_tdd_static_preflight_authorized": True,
            "training_retry_authorized": False,
            "calibration_authorized": False,
            "holdout_authorized": False,
            "claim_authorized": False,
        },
        "next_work_target": (
            "v24_convex_training_projection_boundary_repair_tdd_static_preflight_only"
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
        raise FileExistsError("v24 failure review target already exists")
    result = review_failure(
        repo=args.repo, dp_repo=args.dp_repo, current_camp_head=args.camp_head
    )
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "review.json").write_bytes(_canonical_json_bytes(result))
    (args.output_dir / "review.md").write_text(
        "# V24 Convex Training Execution Failure Review\n\n"
        "- status: `passed`\n"
        "- model: `not produced`\n"
        "- diagnosis: `raw-cut / projected-save numerical boundary mismatch`\n"
        "- next: `repair TDD and static preflight only`\n",
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
