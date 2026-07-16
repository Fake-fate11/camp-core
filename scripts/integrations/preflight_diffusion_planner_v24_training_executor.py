#!/usr/bin/env python3
"""Static preflight for the frozen v24 train-only convex selector executor."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
from typing import Any, Optional, Sequence

import numpy as np


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
from scripts.integrations.train_diffusion_planner_v24_selector import (  # noqa: E402
    ACCEPTANCE_GAP,
    AUDIT_RELATIVE,
    CORPUS_LOCK,
    CVAR_ALPHA,
    EXPECTED_ALL_K_HIGH_RISK,
    EXPECTED_CANDIDATES,
    EXPECTED_LEVELS,
    EXPECTED_LEVEL_ROUTES,
    EXPECTED_LEVEL_SNAPSHOTS,
    EXPECTED_PHYSICAL_FEASIBLE_CANDIDATES,
    EXPECTED_ROUTES,
    EXPECTED_ROUTE_SEEDS,
    EXPECTED_SNAPSHOTS,
    EXPECTED_SOURCE_VALID_CANDIDATES,
    FIXED_DP_HEAD,
    L2_REGULARIZATION,
    LABEL_ARTIFACT,
    LABEL_LOCK,
    LABEL_REVIEW_ARTIFACT,
    LABEL_REVIEW_ROOT_SHA256,
    LABEL_ROOT_SHA256,
    MAX_ITERATIONS,
    MINIMUM_FREE_BYTES,
    PLAN_ARTIFACT,
    PLAN_ROOT_SHA256,
    SOLVER,
    SOLVER_OPTIONS,
    TRAINING_LOCK,
    _lock_is_free,
    load_training_inputs,
    seal_artifact,
    tracked_source_provenance,
)


TEST_SCHEMA = "camp_dp_v24_training_executor_static_tests_v1"
PREFLIGHT_SCHEMA = "camp_dp_v24_training_executor_static_preflight_v1"
REQUIRED_TEST_FILES = (
    "camp_core/tests/test_diffusion_planner_v24_training_executor.py",
    "camp_core/tests/test_diffusion_planner_v24_convex_training_preflight.py",
    "camp_core/tests/test_diffusion_planner_v24_training_labels.py",
    "camp_core/tests/test_diffusion_planner_v24_atom_availability.py",
    "camp_core/tests/test_diffusion_planner_v24_iteration_audit.py",
)


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _safe_autodl_artifact(path: Path) -> None:
    pure = PurePosixPath(str(path))
    if (
        not pure.is_absolute()
        or pure.parts[:3] != ("/", "root", "autodl-tmp")
        or ".." in pure.parts
    ):
        raise ValueError("v24 test artifact must be a safe AutoDL path")


def verify_static_test_artifact(
    *, root: Path, expected_root_sha256: str, camp_head: str
) -> dict[str, Any]:
    _safe_autodl_artifact(root)
    files = verify_complete_seal(root, expected_root_sha256)
    if (
        (root / "run.exit").read_text(encoding="ascii") != "0\n"
        or (root / "stderr.txt").read_text(encoding="utf-8") != ""
    ):
        raise ValueError("v24 training executor static tests are not clean")
    receipt = _read_json(root / "test_receipt.json")
    stdout = (root / "stdout.txt").read_text(encoding="utf-8")
    matches = re.findall(r"(?m)(\d+) passed(?:, \d+ skipped)? in ", stdout)
    if (
        receipt.get("schema") != TEST_SCHEMA
        or receipt.get("status") != "passed"
        or receipt.get("camp_head") != camp_head
        or receipt.get("fixed_dp_head") != FIXED_DP_HEAD
        or receipt.get("required_test_files") != list(REQUIRED_TEST_FILES)
        or type(receipt.get("passed_count")) is not int
        or receipt["passed_count"] < 14
        or not matches
        or int(matches[-1]) != receipt["passed_count"]
        or receipt.get("training_executed") is not False
        or receipt.get("corpus_solver_called") is not False
        or receipt.get("calibration_accessed") is not False
        or receipt.get("holdout_opened") is not False
    ):
        raise ValueError("v24 training executor static test receipt drift")
    return {"verified_file_count": len(files), **receipt}


def _authorization_from_live_eof(repo: Path) -> dict[str, str]:
    lines = (Path(repo) / AUDIT_RELATIVE).read_text(encoding="utf-8").rstrip().splitlines()
    parsed = dict(line.split("=", 1) for line in lines[-15:] if "=" in line)
    expected = {
        "current_v24_status": (
            "v24_train_only_causal_label_materialization_independent_review_passed"
        ),
        "current_v24_artifact": str(LABEL_REVIEW_ARTIFACT),
        "current_v24_artifact_root_sha256": LABEL_REVIEW_ROOT_SHA256,
        "next_work_target": "v24_convex_selector_training_executor_tdd_static_preflight_only",
    }
    if any(parsed.get(key) != value for key, value in expected.items()):
        raise ValueError("live v24 EOF does not authorize executor static preflight")
    verify_complete_seal(LABEL_REVIEW_ARTIFACT, LABEL_REVIEW_ROOT_SHA256)
    return expected


def _running_executor_pids() -> list[int]:
    target = "scripts/integrations/train_diffusion_planner_v24_selector.py"
    pids: list[int] = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            argv = (item / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        decoded = [part.decode("utf-8", errors="replace") for part in argv if part]
        if any(value == target or value.endswith("/" + target) for value in decoded):
            pids.append(int(item.name))
    return sorted(pids)


def run_static_preflight(
    *,
    repo: Path,
    dp_repo: Path,
    camp_head: str,
    test_artifact: Path,
    test_root_sha256: str,
) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("v24 training executor preflight requires AutoDL")
    _require_clean_repo(repo, camp_head)
    _require_clean_repo(dp_repo, FIXED_DP_HEAD)
    authorization = _authorization_from_live_eof(repo)
    test_receipt = verify_static_test_artifact(
        root=test_artifact,
        expected_root_sha256=test_root_sha256,
        camp_head=camp_head,
    )
    source_provenance = tracked_source_provenance(repo=repo, current_head=camp_head)
    running = _running_executor_pids()
    lock_states = {
        "training_lock_free": _lock_is_free(TRAINING_LOCK),
        "corpus_lock_free": _lock_is_free(CORPUS_LOCK),
        "label_lock_free": _lock_is_free(LABEL_LOCK),
    }
    free_bytes = shutil.disk_usage(test_artifact.parent).free
    if running or not all(lock_states.values()) or free_bytes <= MINIMUM_FREE_BYTES:
        raise RuntimeError("v24 training execution preflight process/lock/disk gate failed")

    import cvxpy as cp

    installed = sorted(str(name).upper() for name in cp.installed_solvers())
    if SOLVER not in installed:
        raise RuntimeError("CLARABEL is unavailable on AutoDL")
    inputs = load_training_inputs()
    if (
        np.asarray(inputs["atoms"]).shape != (EXPECTED_SNAPSHOTS, 8, 14)
        or np.asarray(inputs["candidate_cost"]).shape != (EXPECTED_SNAPSHOTS, 8)
        or int(np.asarray(inputs["source_valid_mask"], dtype=bool).sum())
        != EXPECTED_SOURCE_VALID_CANDIDATES
        or int(np.asarray(inputs["physical_feasible_mask"], dtype=bool).sum())
        != EXPECTED_PHYSICAL_FEASIBLE_CANDIDATES
        or int(np.asarray(inputs["all_k_high_risk"], dtype=bool).sum())
        != EXPECTED_ALL_K_HIGH_RISK
        or np.asarray(inputs["atom_scales"]).shape != (14,)
        or [len(inputs["level_indices"][level]) for level in EXPECTED_LEVELS]
        != list(EXPECTED_LEVEL_SNAPSHOTS)
    ):
        raise ValueError("v24 training input static closure drift")

    executor_relative = "scripts/integrations/train_diffusion_planner_v24_selector.py"
    reviewer_relative = (
        "scripts/integrations/review_diffusion_planner_v24_training_executor_preflight.py"
    )
    return {
        "schema": PREFLIGHT_SCHEMA,
        "status": "passed",
        "camp_head": camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "live_eof_authorization": authorization,
        "test_artifact": str(test_artifact),
        "test_artifact_root_sha256": test_root_sha256,
        "test_receipt": test_receipt,
        "source_provenance": source_provenance,
        "executor_source_sha256": source_provenance[executor_relative]["sha256"],
        "reviewer_source_sha256": source_provenance[reviewer_relative]["sha256"],
        "input_authority": {
            "training_plan": {"path": str(PLAN_ARTIFACT), "root_sha256": PLAN_ROOT_SHA256},
            "causal_labels": {"path": str(LABEL_ARTIFACT), "root_sha256": LABEL_ROOT_SHA256},
            "causal_label_review": {
                "path": str(LABEL_REVIEW_ARTIFACT),
                "root_sha256": LABEL_REVIEW_ROOT_SHA256,
            },
        },
        "input_counts": {
            "routes": EXPECTED_ROUTES,
            "retained_route_seeds": EXPECTED_ROUTE_SEEDS,
            "snapshots": EXPECTED_SNAPSHOTS,
            "candidates": EXPECTED_CANDIDATES,
            "source_valid_candidates": EXPECTED_SOURCE_VALID_CANDIDATES,
            "physical_feasible_candidates": EXPECTED_PHYSICAL_FEASIBLE_CANDIDATES,
            "all_k_high_risk_snapshots": EXPECTED_ALL_K_HIGH_RISK,
            "learning_curve_levels": list(EXPECTED_LEVELS),
            "learning_curve_route_counts": list(EXPECTED_LEVEL_ROUTES),
            "learning_curve_snapshot_counts": list(EXPECTED_LEVEL_SNAPSHOTS),
        },
        "master_contract": {
            "score": "score_k(w)=a_k^T w",
            "weights": "nonnegative_simplex_14d",
            "risk_type": "cvar",
            "cvar_alpha": CVAR_ALPHA,
            "l2_regularization": L2_REGULARIZATION,
            "solver": SOLVER,
            "solver_status_required": "optimal",
            "solver_options": dict(SOLVER_OPTIONS),
            "solver_fallback_allowed": False,
            "max_iterations": MAX_ITERATIONS,
            "post_cap_final_resolve_allowed": False,
            "acceptance_gap": ACCEPTANCE_GAP,
            "full_k_saved_weight_recomputation_required": True,
        },
        "solver_environment": {
            "cvxpy_version": cp.__version__,
            "installed_solvers": installed,
            "required_solver_available": True,
        },
        "process_and_resource_gate": {
            "running_executor_pids": running,
            **lock_states,
            "free_bytes": free_bytes,
            "minimum_free_bytes": MINIMUM_FREE_BYTES,
            "disk_floor_passed": True,
        },
        "source_verified_file_counts": inputs["source_verified_file_counts"],
        "direct_source_verified_file_counts": inputs[
            "direct_source_verified_file_counts"
        ],
        "training_executed": False,
        "corpus_solver_called": False,
        "synthetic_solver_called": False,
        "model_written": False,
        "actual_closed_loop_outcomes_read": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "decision": {
            "independent_static_review_authorized": True,
            "training_execution_authorized": False,
        },
        "next_work_target": (
            "v24_convex_training_executor_static_preflight_independent_review_only"
        ),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--test-artifact", type=Path, required=True)
    parser.add_argument("--test-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError("v24 training executor preflight target already exists")
    result = run_static_preflight(
        repo=args.repo,
        dp_repo=args.dp_repo,
        camp_head=args.camp_head,
        test_artifact=args.test_artifact,
        test_root_sha256=args.test_root_sha256,
    )
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "preflight.json").write_bytes(_canonical_json_bytes(result))
    (args.output_dir / "preflight.md").write_text(
        "# V24 Training Executor Static Preflight\n\n"
        "- status: `passed`\n"
        "- corpus solver / training: `not executed`\n"
        "- next: `independent static review only`\n",
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
    root_sha256 = seal_artifact(args.output_dir)
    print(json.dumps({"artifact_root_sha256": root_sha256}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
