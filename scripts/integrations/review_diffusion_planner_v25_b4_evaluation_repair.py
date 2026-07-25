#!/usr/bin/env python3
"""Independently review an additive Fresh B4 pre-artifact evaluation repair."""

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
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact, verify_complete_seal  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_holdout_contract import _strict_canonical_json, canonical_json_bytes, canonical_sha256  # noqa: E402


ERROR = "Fresh B2 arm order is not balanced within scenario_family=cut_in_merge"
CHANGED_PATHS = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_b4_evaluation_repair.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_evaluation.py",
    "camp_core/tests/test_diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
    "scripts/integrations/freeze_diffusion_planner_v25_b4_evaluation_repair.py",
    "scripts/integrations/review_diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "scripts/integrations/review_diffusion_planner_v25_b4_evaluation_repair.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_evaluation.py",
)
FIELDS = frozenset(
    {
        "schema_version", "status", "original_correction_authority",
        "original_correction_authority_review", "continuation_ledger",
        "continuation_state_before", "failed_evaluation_control",
        "failure_class", "error_message", "fix_basis", "old_correction_head",
        "old_correction_manifest_sha256", "new_correction_head",
        "new_correction_manifest_sha256", "focused_tests", "changed_paths",
        "corrected_evaluation_output_dir",
        "corrected_evaluation_review_output_dir",
        "valid_evaluation_artifact_formed_before_repair",
        "raw_outcome_values_inspected", "fresh_execution_rerun",
        "scientific_contract_changed", "denominator_changed",
        "claim_rule_changed", "repair_payload_sha256",
    }
)


def review(*, repair_artifact: Path, repair_root_sha256: str, output_dir: Path) -> str:
    source = Path(repair_artifact).resolve()
    output = Path(output_dir).resolve()
    head = _git_head()
    expected_source = Path(
        "/root/autodl-tmp/"
        f"camp_dp_v25_fresh_b4_evaluation_policy_correction_repair_{head[:8]}_8680c1b19ce0620b"
    )
    expected_output = Path(
        "/root/autodl-tmp/"
        f"camp_dp_v25_fresh_b4_evaluation_policy_correction_repair_review_{head[:8]}_8680c1b19ce0620b"
    )
    if source != expected_source or output != expected_output or output.exists() or _tracked_changes():
        raise ValueError("Fresh B4 repair review repository/output drifted")
    verify_complete_seal(source, repair_root_sha256, label="Fresh B4 evaluation repair")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B4 evaluation repair did not pass")
    repair = _object(source / "repair.json")
    if set(repair) != FIELDS:
        raise ValueError("Fresh B4 repair field set drifted")
    unsigned = dict(repair)
    payload_sha = unsigned.pop("repair_payload_sha256")
    if payload_sha != canonical_sha256(unsigned):
        raise ValueError("Fresh B4 repair payload SHA drifted")
    if (
        repair["new_correction_head"] != head
        or tuple(repair["changed_paths"]) != CHANGED_PATHS
        or repair["continuation_state_before"] != "evaluation_started"
        or repair["error_message"] != ERROR
        or any(
            repair[name] is not False
            for name in (
                "valid_evaluation_artifact_formed_before_repair",
                "raw_outcome_values_inspected",
                "fresh_execution_rerun",
                "scientific_contract_changed",
                "denominator_changed",
                "claim_rule_changed",
            )
        )
    ):
        raise ValueError("Fresh B4 repair literal value drifted")
    continuation = repair["continuation_ledger"]
    if _file_sha256(Path(continuation["path"])) != continuation["sha256"]:
        raise ValueError("Fresh B4 repair continuation SHA drifted")
    ledger = _object(Path(continuation["path"]))
    if ledger["state"] != "evaluation_started" or ledger["evaluation_root_sha256"] is not None:
        raise ValueError("Fresh B4 repair continuation state drifted")
    control = repair["failed_evaluation_control"]
    if (
        control["run_exit"] != 1
        or _file_sha256(Path(control["stderr"]["path"])) != control["stderr"]["sha256"]
        or _file_sha256(Path(control["run_script"]["path"])) != control["run_script"]["sha256"]
        or _file_sha256(Path(control["run_receipt"]["path"])) != control["run_receipt"]["sha256"]
        or ERROR not in Path(control["stderr"]["path"]).read_text(encoding="utf-8")
    ):
        raise ValueError("Fresh B4 repair failed control drifted")
    changed = tuple(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-only", repair["old_correction_head"], head, "--"],
            text=True,
        ).splitlines()
    )
    if changed != CHANGED_PATHS:
        raise ValueError("Fresh B4 repair changed paths drifted")
    plan_source = (
        ROOT
        / "camp_core/camp_core/integrations/diffusion_planner_v25_signal_complete_plan.py"
    ).read_text(encoding="utf-8")
    evaluator_source = (
        ROOT / "camp_core/camp_core/integrations/diffusion_planner_v25_evaluation.py"
    ).read_text(encoding="utf-8")
    if (
        'offset = (identity["identity_ordinal"] + seed_index) % len(arms)'
        not in plan_source
        or 'require_balanced=field == "inference_cluster_id"' not in evaluator_source
        or "require_balanced and max(counts) - min(counts) > 1"
        not in evaluator_source
    ):
        raise ValueError("Fresh B4 repair static plan proof drifted")
    focused = repair["focused_tests"]
    verify_complete_seal(Path(focused["path"]), focused["root_sha256"], label="Fresh B4 repair focused tests")
    if (Path(focused["path"]) / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B4 repair focused tests did not pass")
    if (
        Path(repair["corrected_evaluation_output_dir"]).exists()
        or Path(repair["corrected_evaluation_review_output_dir"]).exists()
    ):
        raise FileExistsError("Fresh B4 valid corrected artifact already exists")
    report = {
        "schema_version": "camp_dp_v25_fresh_b4_pre_artifact_evaluation_repair_review_v1",
        "status": "passed_independent_outcome_blind_pre_artifact_evaluation_repair_review",
        "reviewed_repair": {"path": str(source), "root_sha256": repair_root_sha256},
        "original_correction_authority_root_sha256": repair["original_correction_authority"]["root_sha256"],
        "original_correction_authority_review_root_sha256": repair["original_correction_authority_review"]["root_sha256"],
        "continuation_ledger_path": continuation["path"],
        "continuation_state": "evaluation_started",
        "failed_control_independently_rehashed": True,
        "static_plan_contract_independently_verified": True,
        "changed_paths_independently_verified": True,
        "new_correction_head": head,
        "new_correction_manifest_sha256": repair["new_correction_manifest_sha256"],
        "focused_test_root_sha256": focused["root_sha256"],
        "corrected_evaluation_output_dir": repair["corrected_evaluation_output_dir"],
        "corrected_evaluation_review_output_dir": repair["corrected_evaluation_review_output_dir"],
        "valid_evaluation_artifact_formed_before_repair": False,
        "raw_outcome_values_inspected": False,
        "fresh_execution_rerun": False,
        "scientific_contract_changed": False,
        "denominator_changed": False,
        "claim_rule_changed": False,
    }
    return _write_atomic(output, report)


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "report.json").write_bytes(canonical_json_bytes(report))
        (staging / "HEADS").write_bytes(f"repair_implementation_head={_git_head()}\n".encode("ascii"))
        (staging / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="independent Fresh B4 evaluation repair review")
        os.rename(staging, output)
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _object(path: Path) -> dict[str, Any]:
    value = _strict_canonical_json(path)
    if type(value) is not dict:
        raise ValueError(f"Fresh B4 repair JSON object drifted: {path}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def _tracked_changes() -> bool:
    return bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], text=True).strip())


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repair-artifact", type=Path, required=True)
    parser.add_argument("--repair-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
