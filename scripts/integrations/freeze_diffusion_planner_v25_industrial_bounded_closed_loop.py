from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_bounded_closed_loop import (  # noqa: E402
    AUTHORITY_SHA256,
    UPSTREAM_ROOTS,
    contract,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (  # noqa: E402
    validate_evaluation_contract_v3,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


PRODUCTION_FILES = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_industrial_bounded_closed_loop.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_industrial_bounded_closed_loop_review.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_industrial_evaluation_contract_v3.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_evaluation_v2.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_scene_runtime.py",
    "scripts/integrations/validate_diffusion_planner_v25_fair_nonholdout.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py",
    "scripts/integrations/run_diffusion_planner_v25_industrial_bounded_closed_loop.py",
    "scripts/integrations/review_diffusion_planner_v25_industrial_bounded_closed_loop.py",
)


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _interpreter_receipt() -> dict[str, Any]:
    return {
        "sys_executable": sys.executable,
        "version_info": list(sys.version_info[:3]),
        "sys_prefix": sys.prefix,
        "minimum_version_passed": sys.version_info >= (3, 10),
        "required_imports": {
            "json": True,
            "hashlib": True,
        },
    }


def freeze_contract(
    output: Path,
    industrial_contract_dir: Path,
    industrial_contract_root: str,
) -> str:
    if industrial_contract_root != UPSTREAM_ROOTS["industrial_contract"]:
        raise ValueError("industrial contract root is not authorized")
    verify_complete_seal(
        industrial_contract_dir,
        industrial_contract_root,
        label="accepted industrial v3 contract",
    )
    source = object_from(industrial_contract_dir / "report.json")
    validate_evaluation_contract_v3(source["contract"])
    payload = contract()
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_v3_bounded_closed_loop_contract_artifact_v1"
            ),
            "status": "sealed_outcome_independent_bounded_contract",
            "contract": payload,
            "industrial_contract_binding": {
                "path": str(industrial_contract_dir.resolve()),
                "root_sha256": industrial_contract_root,
            },
            "implementation_head": git_head(),
            "authority_sha256": AUTHORITY_SHA256,
            "interpreter": _interpreter_receipt(),
            "model_pool_selector_calls": 0,
            "fresh_or_b4_outcome_values_read": False,
            "old_artifact_or_cas_writes": 0,
        },
        {
            "role": "industrial_v3_bounded_closed_loop_contract",
            "implementation_head": git_head(),
            "authority_sha256": AUTHORITY_SHA256,
            "industrial_contract_root_sha256": industrial_contract_root,
        },
        label="V25 industrial-v3 bounded closed-loop contract",
    )


def freeze_matrix(output: Path, contract_dir: Path, contract_root: str) -> str:
    verify_complete_seal(contract_dir, contract_root, label="bounded contract")
    source = object_from(contract_dir / "report.json")
    frozen = source["contract"]
    files = []
    for relative in PRODUCTION_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise ValueError(f"production file is missing: {relative}")
        files.append(
            {
                "relative_path": relative,
                "sha256": _file_sha(path),
                "actual_execution_path": relative
                in {
                    "scripts/integrations/validate_diffusion_planner_v25_fair_nonholdout.py",
                    "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py",
                    "scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py",
                    "scripts/integrations/run_diffusion_planner_v25_industrial_bounded_closed_loop.py",
                },
            }
        )
    matrix = {
        "schema_version": "camp_dp_v25_industrial_v3_production_hardening_matrix_v1",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "parameter_rows": frozen["pre_execution_hardening"][
            "parameter_propagation_matrix"
        ],
        "production_entrypoints": files,
        "dry_run_topology": [
            "entrypoint",
            "typed_receipt",
            "atomic_seal",
            "independent_review",
            "evaluation",
            "independent_evaluation_review",
        ],
        "dry_run_cases": [
            "synthetic_pass",
            "typed_execution_failure",
            "missing_required_keyword",
            "wrong_interpreter",
            "wrong_schema_or_version",
            "extra_missing_duplicate_field",
            "nan_or_inf",
            "path_alias",
            "partial_atomic_write",
            "resign_or_repin",
            "wrong_root_head_model_checkpoint_route",
            "wrong_arm_denominator_or_latency_namespace",
        ],
        "production_policy": {
            "single_typed_contract": True,
            "implicit_default_fallback": False,
            "blanket_run_exit_as_scientific_status": False,
            "legacy_dispatch_on_target_path": False,
        },
        "residual_risk_register": [
            {
                "class": "actually_executed_paths",
                "scope": "three arm native replay, generator, selectors, receipts, seals",
                "residual_risk": "bounded route/runtime only",
            },
            {
                "class": "static_only_verified_paths",
                "scope": "typed failure mutations and authority drift branches",
                "residual_risk": "not all branches exercised by real runtime failures",
            },
            {
                "class": "unexecuted_paths",
                "scope": "Fresh, other routes, other hardware, deployment",
                "residual_risk": "no evidence and no claim",
            },
        ],
        "zero_bug_claimed": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return write_atomic(
        output,
        matrix,
        {
            "role": "industrial_v3_production_hardening_matrix",
            "implementation_head": git_head(),
            "authority_sha256": AUTHORITY_SHA256,
            "contract_root_sha256": contract_root,
        },
        label="V25 industrial-v3 production hardening matrix",
    )


def freeze_focused(
    output: Path,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    matrix_dir: Path,
    matrix_root: str,
    matrix_review_dir: Path,
    matrix_review_root: str,
) -> str:
    for path, root, label in (
        (contract_dir, contract_root, "bounded contract"),
        (contract_review_dir, contract_review_root, "bounded contract review"),
        (matrix_dir, matrix_root, "hardening matrix"),
        (matrix_review_dir, matrix_review_root, "hardening matrix review"),
    ):
        verify_complete_seal(path, root, label=label)
    tests = [
        "camp_core/tests/test_diffusion_planner_v25_industrial_bounded_closed_loop.py",
        "camp_core/tests/test_diffusion_planner_v25_fair_nonholdout.py",
        "camp_core/tests/test_diffusion_planner_v25_selector_after_pool_replay.py",
    ]
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = f"{ROOT / 'camp_core'}:{ROOT}"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *tests],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"hardening focused failed: exit={result.returncode}\n{result.stdout}\n{result.stderr}"
        )
    passed_token = next(
        (
            token
            for token in result.stdout.replace("\n", " ").split()
            if token.isdigit()
        ),
        None,
    )
    return write_atomic(
        output,
        {
            "schema_version": (
                "camp_dp_v25_industrial_v3_production_hardening_focused_v1"
            ),
            "status": "passed_zero_model_production_hardening_focused",
            "test_files": tests,
            "pytest_stdout": result.stdout,
            "pytest_stderr": result.stderr,
            "pytest_exit": result.returncode,
            "reported_pass_count_token": passed_token,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "matrix_root_sha256": matrix_root,
            "matrix_review_root_sha256": matrix_review_root,
            "implementation_head": git_head(),
            "interpreter": _interpreter_receipt(),
            "model_pool_selector_calls": 0,
            "outcome_values_read": False,
            "old_artifact_or_cas_writes": 0,
        },
        {
            "role": "industrial_v3_production_hardening_focused",
            "implementation_head": git_head(),
            "authority_sha256": AUTHORITY_SHA256,
            "contract_root_sha256": contract_root,
            "matrix_root_sha256": matrix_root,
        },
        label="V25 industrial-v3 production hardening focused",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="stage", required=True)
    contract_parser = subparsers.add_parser("contract")
    contract_parser.add_argument("--output", type=Path, required=True)
    contract_parser.add_argument("--industrial-contract-dir", type=Path, required=True)
    contract_parser.add_argument("--industrial-contract-root", required=True)
    matrix_parser = subparsers.add_parser("matrix")
    matrix_parser.add_argument("--output", type=Path, required=True)
    matrix_parser.add_argument("--contract-dir", type=Path, required=True)
    matrix_parser.add_argument("--contract-root", required=True)
    focused_parser = subparsers.add_parser("focused")
    focused_parser.add_argument("--output", type=Path, required=True)
    for name in (
        "contract-dir",
        "contract-review-dir",
        "matrix-dir",
        "matrix-review-dir",
    ):
        focused_parser.add_argument("--" + name, type=Path, required=True)
    for name in (
        "contract-root",
        "contract-review-root",
        "matrix-root",
        "matrix-review-root",
    ):
        focused_parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.stage == "contract":
        root = freeze_contract(
            args.output,
            args.industrial_contract_dir,
            args.industrial_contract_root,
        )
    elif args.stage == "matrix":
        root = freeze_matrix(args.output, args.contract_dir, args.contract_root)
    else:
        root = freeze_focused(
            args.output,
            args.contract_dir,
            args.contract_root,
            args.contract_review_dir,
            args.contract_review_root,
            args.matrix_dir,
            args.matrix_root,
            args.matrix_review_dir,
            args.matrix_review_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
