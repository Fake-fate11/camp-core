#!/usr/bin/env python3
"""Independent review of the v24 convex training-executor static preflight."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from typing import Any, Mapping, Optional, Sequence


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
PLAN_SOURCE_HEAD = "bfc0a52307bf7d9184a5f4596b951058c02ba67c"
LABEL_REVIEW_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_train_causal_labels_independent_review_56596779_"
    "20260716T204427CST"
)
LABEL_REVIEW_ROOT_SHA256 = (
    "d23d09564ea675b0ef7ce35d968c6dd03ead1df5e1282c498704827986eab468"
)
PLAN_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_convex_training_static_preflight_bfc0a523_20260716T195856CST"
)
PLAN_ROOT_SHA256 = (
    "43f26263ff24cad5966cb3a740af6d3307490ab1bd3e07d03284589bee0d28f5"
)
LABEL_ARTIFACT = Path(
    "/root/autodl-tmp/camp_dp_v24_train_causal_labels_56596779_20260716T204104CST"
)
LABEL_ROOT_SHA256 = (
    "9a14fb003fe9145e62b24c20fcecc013baedd72e312add82a8c6a6e6dcde966c"
)
MERGED_ARTIFACT = Path(
    "/root/autodl-tmp/camp_dp_v24_native_corpus_merged_train_assembly_5b725629_"
    "20260716T154602CST"
)
MERGED_ROOT_SHA256 = (
    "d8278d030cabd71af88f60d13c410a37c515f22e0ea4c606a592abecc598bdcc"
)
AUDIT_RELATIVE = Path("docs/diffusion_planner_v24_iteration_audit.md")
EXECUTOR_RELATIVE = "scripts/integrations/train_diffusion_planner_v24_selector.py"
PREFLIGHT_RELATIVE = (
    "scripts/integrations/preflight_diffusion_planner_v24_training_executor.py"
)
REVIEWER_RELATIVE = (
    "scripts/integrations/review_diffusion_planner_v24_training_executor_preflight.py"
)
EXPECTED_PROVENANCE = {
    EXECUTOR_RELATIVE,
    PREFLIGHT_RELATIVE,
    REVIEWER_RELATIVE,
    "configs/integrations/diffusion_planner_v24_convex_training_plan.json",
    "camp_core/camp_core/outer_master/robust_margin_master.py",
    "scripts/integrations/preflight_diffusion_planner_v24_convex_training.py",
    "scripts/integrations/review_diffusion_planner_v24_atom_availability.py",
}
PLAN_STABLE = EXPECTED_PROVENANCE - {
    EXECUTOR_RELATIVE,
    PREFLIGHT_RELATIVE,
    REVIEWER_RELATIVE,
}
EXPECTED_TEST_FILES = [
    "camp_core/tests/test_diffusion_planner_v24_training_executor.py",
    "camp_core/tests/test_diffusion_planner_v24_convex_training_preflight.py",
    "camp_core/tests/test_diffusion_planner_v24_training_labels.py",
    "camp_core/tests/test_diffusion_planner_v24_atom_availability.py",
    "camp_core/tests/test_diffusion_planner_v24_iteration_audit.py",
]
MINIMUM_FREE_BYTES = 10 * 1024**3
LOCKS = (
    Path("/root/autodl-tmp/.camp_dp_v24_convex_training.lock"),
    Path("/root/autodl-tmp/.camp_dp_v24_native_corpus_remaining.lock"),
    Path("/root/autodl-tmp/.camp_dp_v24_training_label_materialization.lock"),
)
REVIEW_SCHEMA = (
    "camp_dp_v24_training_executor_static_preflight_independent_review_v1"
)


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _safe_autodl_path(path: Path) -> bool:
    pure = PurePosixPath(str(path))
    return bool(
        pure.is_absolute()
        and pure.parts[:3] == ("/", "root", "autodl-tmp")
        and ".." not in pure.parts
    )


def _verify_clean_seal(path: Path, root_sha256: str) -> int:
    if not _safe_autodl_path(path):
        raise ValueError("v24 upstream artifact path is unsafe")
    files = verify_complete_seal(path, root_sha256)
    if (
        (path / "run.exit").read_text(encoding="ascii") != "0\n"
        or (path / "stderr.txt").read_text(encoding="utf-8") != ""
    ):
        raise ValueError("v24 upstream execution receipt is not clean")
    return len(files)


def _git_blob(repo: Path, head: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _verify_source_provenance(
    *, repo: Path, camp_head: str, reported: Mapping[str, Any]
) -> dict[str, str]:
    if not isinstance(reported, Mapping) or set(reported) != EXPECTED_PROVENANCE:
        raise ValueError("v24 executor source provenance inventory drift")
    digests: dict[str, str] = {}
    for relative in sorted(EXPECTED_PROVENANCE):
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        live = (repo / relative).read_bytes()
        current = _git_blob(repo, camp_head, relative)
        receipt = reported.get(relative)
        digest = hashlib.sha256(live).hexdigest()
        if (
            live != current
            or not isinstance(receipt, Mapping)
            or receipt.get("sha256") != digest
            or receipt.get("matches_current_head") is not True
        ):
            raise ValueError(f"v24 executor source provenance drift: {relative}")
        if relative in PLAN_STABLE:
            if live != _git_blob(repo, PLAN_SOURCE_HEAD, relative):
                raise ValueError(f"Gate 36 frozen source changed: {relative}")
            if receipt.get("matches_plan_source_head") is not True:
                raise ValueError(f"Gate 36 source receipt drift: {relative}")
        elif receipt.get("matches_plan_source_head") is not False:
            raise ValueError(f"new Gate 38 source stability receipt drift: {relative}")
        digests[relative] = digest
    return digests


def _function_source(tree: ast.Module, name: str, source: str) -> str:
    node = next(
        item
        for item in tree.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name
    )
    return ast.get_source_segment(source, node) or ""


def _static_executor_review(source: str) -> list[str]:
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    historical_strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and ("v18" in node.value.lower() or "v22" in node.value.lower())
    }
    solve = _function_source(tree, "solve_v24_cutting_plane", source)
    accept = _function_source(tree, "accepted_weights_and_gap", source)
    load = _function_source(tree, "load_training_inputs", source)
    curve = _function_source(tree, "train_learning_curve", source)
    if (
        "_solve_master" not in imported
        or "solve_robust_margin_cutting_plane" in imported
        or "pickle" in imported
        or "torch" in imported
        or historical_strings != {"v18_v22_weights_loaded"}
        or "for iteration in range(1, MAX_ITERATIONS + 1)" not in solve
        or '"final_resolve": False' not in solve
        or 'solver_status != "optimal"' not in solve
        or "clarabel_only_solver_registry" not in solve
        or "post-cap final-resolve is forbidden" not in accept
        or "cut_and_full_losses" not in accept
        or "omitted_violating_snapshot_count" not in accept
        or "verify_complete_seal" not in load
        or "_verify_label_payload_receipts" not in load
        or "for sequence, level in enumerate(inputs[\"levels\"], start=1)" not in curve
        or 'list(models) != ["25", "50", "75", "100"]' not in curve
        or "progress_callback" not in curve
    ):
        raise ValueError("v24 training executor static contract review failed")
    return [
        "frozen_core_master_reused",
        "clarabel_only_registry",
        "exact_optimal_required",
        "no_post_cap_final_resolve",
        "saved_weights_recomputed_full_k",
        "all_four_levels_fresh_and_required",
        "no_historical_weight_load",
        "no_outcome_or_holdout_loader",
        "identity_not_feature",
        "sealed_input_closure",
    ]


def _lock_free(path: Path) -> bool:
    import fcntl

    with path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def _running_executor_pids() -> list[int]:
    pids = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            argv = (item / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        values = [part.decode("utf-8", errors="replace") for part in argv if part]
        if any(value == EXECUTOR_RELATIVE or value.endswith("/" + EXECUTOR_RELATIVE) for value in values):
            pids.append(int(item.name))
    return sorted(pids)


def _seal_artifact(root: Path) -> str:
    sums = root / "SHA256SUMS"
    receipt = root / "ROOT_SHA256SUMS"
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("v24 review artifact symlink is forbidden")
        if path.is_file() and path not in {sums, receipt}:
            if path.name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
                raise ValueError("nested v24 review manifest is forbidden")
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


def review_preflight(
    *, repo: Path, dp_repo: Path, camp_head: str, artifact: Path, root_sha256: str
) -> dict[str, Any]:
    if os.name != "posix":
        raise RuntimeError("v24 executor preflight review requires AutoDL")
    _require_clean_repo(repo, camp_head)
    _require_clean_repo(dp_repo, FIXED_DP_HEAD)
    if not _safe_autodl_path(artifact):
        raise ValueError("v24 preflight artifact path is unsafe")
    verified = verify_complete_seal(artifact, root_sha256)
    if (
        (artifact / "run.exit").read_text(encoding="ascii") != "0\n"
        or (artifact / "stderr.txt").read_text(encoding="utf-8") != ""
    ):
        raise ValueError("v24 executor preflight execution receipt is not clean")
    report = _read_json(artifact / "preflight.json")
    if (
        report.get("schema") != "camp_dp_v24_training_executor_static_preflight_v1"
        or report.get("status") != "passed"
        or report.get("camp_head") != camp_head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("training_executed") is not False
        or report.get("corpus_solver_called") is not False
        or report.get("synthetic_solver_called") is not False
        or report.get("model_written") is not False
        or report.get("actual_closed_loop_outcomes_read") is not False
        or report.get("calibration_accessed") is not False
        or report.get("holdout_opened") is not False
        or report.get("claim_authorized") is not False
        or report.get("decision", {}).get("independent_static_review_authorized")
        is not True
        or report.get("decision", {}).get("training_execution_authorized") is not False
    ):
        raise ValueError("v24 executor preflight boundary receipt drift")

    eof = dict(
        line.split("=", 1)
        for line in (repo / AUDIT_RELATIVE).read_text(encoding="utf-8").rstrip().splitlines()[-15:]
        if "=" in line
    )
    if (
        eof.get("current_v24_status")
        != "v24_train_only_causal_label_materialization_independent_review_passed"
        or eof.get("current_v24_artifact") != str(LABEL_REVIEW_ARTIFACT)
        or eof.get("current_v24_artifact_root_sha256") != LABEL_REVIEW_ROOT_SHA256
        or eof.get("next_work_target")
        != "v24_convex_selector_training_executor_tdd_static_preflight_only"
    ):
        raise ValueError("live v24 EOF drifted before independent static review")

    digests = _verify_source_provenance(
        repo=repo, camp_head=camp_head, reported=report.get("source_provenance")
    )
    if (
        report.get("executor_source_sha256") != digests[EXECUTOR_RELATIVE]
        or report.get("reviewer_source_sha256") != digests[REVIEWER_RELATIVE]
    ):
        raise ValueError("v24 preflight source SHA receipt drift")
    static_checks = _static_executor_review((repo / EXECUTOR_RELATIVE).read_text(encoding="utf-8"))

    expected_authority = {
        "training_plan": {"path": str(PLAN_ARTIFACT), "root_sha256": PLAN_ROOT_SHA256},
        "causal_labels": {"path": str(LABEL_ARTIFACT), "root_sha256": LABEL_ROOT_SHA256},
        "causal_label_review": {
            "path": str(LABEL_REVIEW_ARTIFACT),
            "root_sha256": LABEL_REVIEW_ROOT_SHA256,
        },
    }
    if report.get("input_authority") != expected_authority:
        raise ValueError("v24 executor input authority drift")
    input_verified = {
        name: _verify_clean_seal(Path(spec["path"]), spec["root_sha256"])
        for name, spec in expected_authority.items()
    }
    input_verified["merged_corpus"] = _verify_clean_seal(
        MERGED_ARTIFACT, MERGED_ROOT_SHA256
    )
    plan = _read_json(PLAN_ARTIFACT / "training_plan_preflight.json")
    source_authority = plan.get("source_authority")
    if not isinstance(source_authority, Mapping) or set(source_authority) != {
        "merged_train_corpus",
        "merged_train_corpus_review",
        "atom_freeze",
        "atom_freeze_review",
    }:
        raise ValueError("Gate 36 source authority drift")
    source_verified = {}
    for name, spec in source_authority.items():
        if not isinstance(spec, Mapping):
            raise ValueError("Gate 36 source authority row is invalid")
        source_verified[name] = _verify_clean_seal(
            Path(str(spec.get("artifact"))), str(spec.get("artifact_root_sha256"))
        )
    merged = _read_json(MERGED_ARTIFACT / "merged_summary.json")
    direct_verified = {}
    for name in ("pilot", "pilot_review", "remaining", "remaining_review"):
        spec = merged.get("source_artifacts", {}).get(name)
        if not isinstance(spec, Mapping):
            raise ValueError("merged corpus direct source authority drift")
        direct_verified[name] = _verify_clean_seal(
            Path(str(spec.get("path"))), str(spec.get("root_sha256"))
        )
    if (
        report.get("source_verified_file_counts") != source_verified
        or report.get("direct_source_verified_file_counts") != direct_verified
    ):
        raise ValueError("v24 upstream verified file counts drift")
    counts = report.get("input_counts")
    if not isinstance(counts, Mapping) or counts != {
        "routes": 375,
        "retained_route_seeds": 1875,
        "snapshots": 67796,
        "candidates": 542368,
        "source_valid_candidates": 542368,
        "physical_feasible_candidates": 470138,
        "all_k_high_risk_snapshots": 7783,
        "learning_curve_levels": [25, 50, 75, 100],
        "learning_curve_route_counts": [94, 188, 281, 375],
        "learning_curve_snapshot_counts": [16979, 35022, 50752, 67796],
    }:
        raise ValueError("v24 executor input counts drift")
    master = report.get("master_contract")
    if (
        not isinstance(master, Mapping)
        or master.get("solver") != "CLARABEL"
        or master.get("solver_status_required") != "optimal"
        or master.get("solver_fallback_allowed") is not False
        or master.get("max_iterations") != 20
        or master.get("post_cap_final_resolve_allowed") is not False
        or master.get("acceptance_gap") != 1e-6
        or master.get("full_k_saved_weight_recomputation_required") is not True
    ):
        raise ValueError("v24 executor master contract drift")

    test_artifact = Path(str(report.get("test_artifact")))
    test_root = report.get("test_artifact_root_sha256")
    if not _safe_autodl_path(test_artifact) or not isinstance(test_root, str):
        raise ValueError("v24 static test artifact authority is invalid")
    test_verified = verify_complete_seal(test_artifact, test_root)
    test = _read_json(test_artifact / "test_receipt.json")
    stdout = (test_artifact / "stdout.txt").read_text(encoding="utf-8")
    matches = re.findall(r"(?m)(\d+) passed(?:, \d+ skipped)? in ", stdout)
    if (
        (test_artifact / "run.exit").read_text(encoding="ascii") != "0\n"
        or (test_artifact / "stderr.txt").read_text(encoding="utf-8") != ""
        or test.get("schema") != "camp_dp_v24_training_executor_static_tests_v1"
        or test.get("camp_head") != camp_head
        or test.get("fixed_dp_head") != FIXED_DP_HEAD
        or test.get("required_test_files") != EXPECTED_TEST_FILES
        or not matches
        or int(matches[-1]) != test.get("passed_count")
        or test.get("passed_count", 0) < 14
    ):
        raise ValueError("v24 static test independent receipt review failed")

    running = _running_executor_pids()
    lock_free = [_lock_free(path) for path in LOCKS]
    free_bytes = shutil.disk_usage(artifact.parent).free
    if running or not all(lock_free) or free_bytes <= MINIMUM_FREE_BYTES:
        raise RuntimeError("v24 execution process/lock/disk gate changed during review")
    import cvxpy as cp

    installed = sorted(str(name).upper() for name in cp.installed_solvers())
    if "CLARABEL" not in installed:
        raise RuntimeError("CLARABEL disappeared during independent review")

    checks = static_checks + [
        "preflight_complete_seal",
        "test_complete_seal",
        "source_sha_recomputed",
        "gate36_source_unchanged",
        "upstream_complete_seals",
        "exact_input_counts",
        "process_uniqueness",
        "all_locks_free",
        "disk_floor_passed",
        "clarabel_available",
        "no_training_or_model_output",
        "calibration_holdout_outcomes_closed",
    ]
    return {
        "schema": REVIEW_SCHEMA,
        "status": "passed",
        "camp_head": camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_preflight_artifact": str(artifact),
        "source_preflight_root_sha256": root_sha256,
        "source_preflight_verified_file_count": len(verified),
        "source_test_artifact": str(test_artifact),
        "source_test_root_sha256": test_root,
        "source_test_verified_file_count": len(test_verified),
        "executor_source_sha256": digests[EXECUTOR_RELATIVE],
        "preflight_source_sha256": digests[PREFLIGHT_RELATIVE],
        "reviewer_source_sha256": digests[REVIEWER_RELATIVE],
        "input_verified_file_counts": input_verified,
        "source_verified_file_counts": source_verified,
        "direct_source_verified_file_counts": direct_verified,
        "passed_checks": checks,
        "passed_count": len(checks),
        "failed_count": 0,
        "solver_environment": {
            "cvxpy_version": cp.__version__,
            "installed_solvers": installed,
            "required_solver_available": True,
        },
        "running_executor_pids": running,
        "lock_free": lock_free,
        "free_bytes": free_bytes,
        "minimum_free_bytes": MINIMUM_FREE_BYTES,
        "training_executed": False,
        "model_written": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "decision": {
            "training_execution_authorized": True,
            "training_independent_review_authorized": True,
            "calibration_authorized": False,
            "holdout_authorized": False,
            "claim_authorized": False,
        },
        "next_work_target": "v24_convex_selector_training_execution_only",
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError("v24 executor preflight review target already exists")
    result = review_preflight(
        repo=args.repo,
        dp_repo=args.dp_repo,
        camp_head=args.camp_head,
        artifact=args.artifact,
        root_sha256=args.artifact_root_sha256,
    )
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "review.json").write_bytes(_canonical_json_bytes(result))
    (args.output_dir / "review.md").write_text(
        "# V24 Training Executor Static Preflight Independent Review\n\n"
        "- status: `passed`\n"
        "- training execution: `authorized next, not executed here`\n"
        "- calibration / holdout / outcomes / claim: `closed`\n",
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
