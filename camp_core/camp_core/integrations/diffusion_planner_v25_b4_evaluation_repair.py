from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .diffusion_planner_v25_holdout_contract import canonical_sha256, strict_equal


SCHEMA_VERSION = "camp_dp_v25_fresh_b4_pre_artifact_evaluation_repair_v1"
STATUS = "authorized_outcome_blind_pre_artifact_evaluation_consumer_repair"
REVIEW_SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_pre_artifact_evaluation_repair_review_v1"
)
REVIEW_STATUS = (
    "passed_independent_outcome_blind_pre_artifact_evaluation_repair_review"
)
ERROR = "Fresh B2 arm order is not balanced within scenario_family=cut_in_merge"
FIX_BASIS = (
    "static_frozen_plan_orders_by_identity_ordinal_plus_seed_index_modulo_3_"
    "which_guarantees_pair_permutation_overall_and_per_inference_cluster_"
    "balance_but_not_per_scenario_family_exact_balance"
)
ALLOWED_CHANGED_PATHS = (
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
_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "original_correction_authority",
        "original_correction_authority_review",
        "continuation_ledger",
        "continuation_state_before",
        "failed_evaluation_control",
        "failure_class",
        "error_message",
        "fix_basis",
        "old_correction_head",
        "old_correction_manifest_sha256",
        "new_correction_head",
        "new_correction_manifest_sha256",
        "focused_tests",
        "changed_paths",
        "corrected_evaluation_output_dir",
        "corrected_evaluation_review_output_dir",
        "valid_evaluation_artifact_formed_before_repair",
        "raw_outcome_values_inspected",
        "fresh_execution_rerun",
        "scientific_contract_changed",
        "denominator_changed",
        "claim_rule_changed",
        "repair_payload_sha256",
    }
)
_REVIEW_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "reviewed_repair",
        "original_correction_authority_root_sha256",
        "original_correction_authority_review_root_sha256",
        "continuation_ledger_path",
        "continuation_state",
        "failed_control_independently_rehashed",
        "static_plan_contract_independently_verified",
        "changed_paths_independently_verified",
        "new_correction_head",
        "new_correction_manifest_sha256",
        "focused_test_root_sha256",
        "corrected_evaluation_output_dir",
        "corrected_evaluation_review_output_dir",
        "valid_evaluation_artifact_formed_before_repair",
        "raw_outcome_values_inspected",
        "fresh_execution_rerun",
        "scientific_contract_changed",
        "denominator_changed",
        "claim_rule_changed",
    }
)


def freeze_repair(
    *,
    original_correction_authority: Mapping[str, Any],
    original_correction_authority_review: Mapping[str, Any],
    continuation_ledger: Mapping[str, Any],
    failed_evaluation_control: Mapping[str, Any],
    old_correction_head: str,
    old_correction_manifest_sha256: str,
    new_correction_head: str,
    new_correction_manifest_sha256: str,
    focused_tests: Mapping[str, Any],
    changed_paths: list[str],
    corrected_evaluation_output_dir: str,
    corrected_evaluation_review_output_dir: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "original_correction_authority": _binding(
            original_correction_authority, "original correction authority"
        ),
        "original_correction_authority_review": _binding(
            original_correction_authority_review,
            "original correction authority review",
        ),
        "continuation_ledger": _file_binding(
            continuation_ledger, "continuation ledger"
        ),
        "continuation_state_before": "evaluation_started",
        "failed_evaluation_control": _control(failed_evaluation_control),
        "failure_class": "pre_artifact_evaluation_consumer_contract_omission",
        "error_message": ERROR,
        "fix_basis": FIX_BASIS,
        "old_correction_head": _sha(old_correction_head, "old correction head"),
        "old_correction_manifest_sha256": _sha(
            old_correction_manifest_sha256, "old correction manifest"
        ),
        "new_correction_head": _sha(new_correction_head, "new correction head"),
        "new_correction_manifest_sha256": _sha(
            new_correction_manifest_sha256, "new correction manifest"
        ),
        "focused_tests": _binding(focused_tests, "focused tests"),
        "changed_paths": _strings(changed_paths, "changed paths"),
        "corrected_evaluation_output_dir": _absolute(
            corrected_evaluation_output_dir, "corrected evaluation output"
        ),
        "corrected_evaluation_review_output_dir": _absolute(
            corrected_evaluation_review_output_dir,
            "corrected evaluation review output",
        ),
        "valid_evaluation_artifact_formed_before_repair": False,
        "raw_outcome_values_inspected": False,
        "fresh_execution_rerun": False,
        "scientific_contract_changed": False,
        "denominator_changed": False,
        "claim_rule_changed": False,
    }
    if tuple(payload["changed_paths"]) != ALLOWED_CHANGED_PATHS:
        raise ValueError("Fresh B4 repair changed-path allowlist drifted")
    payload["repair_payload_sha256"] = canonical_sha256(payload)
    return payload


def validate_repair(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError("Fresh B4 repair field set drifted")
    expected = freeze_repair(
        original_correction_authority=value["original_correction_authority"],
        original_correction_authority_review=value[
            "original_correction_authority_review"
        ],
        continuation_ledger=value["continuation_ledger"],
        failed_evaluation_control=value["failed_evaluation_control"],
        old_correction_head=value["old_correction_head"],
        old_correction_manifest_sha256=value["old_correction_manifest_sha256"],
        new_correction_head=value["new_correction_head"],
        new_correction_manifest_sha256=value["new_correction_manifest_sha256"],
        focused_tests=value["focused_tests"],
        changed_paths=value["changed_paths"],
        corrected_evaluation_output_dir=value["corrected_evaluation_output_dir"],
        corrected_evaluation_review_output_dir=value[
            "corrected_evaluation_review_output_dir"
        ],
    )
    if not strict_equal(value, expected):
        raise ValueError("Fresh B4 repair exact value drifted")
    return expected


def freeze_repair_review(
    *, reviewed_repair: Mapping[str, Any], repair: Mapping[str, Any]
) -> dict[str, Any]:
    value = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "status": REVIEW_STATUS,
        "reviewed_repair": _binding(reviewed_repair, "reviewed repair"),
        "original_correction_authority_root_sha256": repair[
            "original_correction_authority"
        ]["root_sha256"],
        "original_correction_authority_review_root_sha256": repair[
            "original_correction_authority_review"
        ]["root_sha256"],
        "continuation_ledger_path": repair["continuation_ledger"]["path"],
        "continuation_state": "evaluation_started",
        "failed_control_independently_rehashed": True,
        "static_plan_contract_independently_verified": True,
        "changed_paths_independently_verified": True,
        "new_correction_head": repair["new_correction_head"],
        "new_correction_manifest_sha256": repair[
            "new_correction_manifest_sha256"
        ],
        "focused_test_root_sha256": repair["focused_tests"]["root_sha256"],
        "corrected_evaluation_output_dir": repair[
            "corrected_evaluation_output_dir"
        ],
        "corrected_evaluation_review_output_dir": repair[
            "corrected_evaluation_review_output_dir"
        ],
        "valid_evaluation_artifact_formed_before_repair": False,
        "raw_outcome_values_inspected": False,
        "fresh_execution_rerun": False,
        "scientific_contract_changed": False,
        "denominator_changed": False,
        "claim_rule_changed": False,
    }
    return validate_repair_review(value)


def validate_repair_review(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _REVIEW_FIELDS:
        raise ValueError("Fresh B4 repair review field set drifted")
    result = json.loads(json.dumps(value))
    if (
        result["schema_version"] != REVIEW_SCHEMA_VERSION
        or result["status"] != REVIEW_STATUS
        or result["continuation_state"] != "evaluation_started"
        or any(
            result[name] is not True
            for name in (
                "failed_control_independently_rehashed",
                "static_plan_contract_independently_verified",
                "changed_paths_independently_verified",
            )
        )
        or any(
            result[name] is not False
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
        raise ValueError("Fresh B4 repair review value drifted")
    _binding(result["reviewed_repair"], "reviewed repair")
    for name in (
        "original_correction_authority_root_sha256",
        "original_correction_authority_review_root_sha256",
        "new_correction_head",
        "new_correction_manifest_sha256",
        "focused_test_root_sha256",
    ):
        _sha(result[name], name)
    _absolute(result["continuation_ledger_path"], "continuation ledger")
    _absolute(result["corrected_evaluation_output_dir"], "evaluation output")
    _absolute(
        result["corrected_evaluation_review_output_dir"],
        "evaluation review output",
    )
    return result


def _control(value: Mapping[str, Any]) -> dict[str, Any]:
    fields = {"directory", "run_exit", "stderr", "run_script", "run_receipt"}
    if type(value) is not dict or set(value) != fields or value["run_exit"] != 1:
        raise ValueError("Fresh B4 failed evaluation control drifted")
    return {
        "directory": _absolute(value["directory"], "failed control"),
        "run_exit": 1,
        "stderr": _file_binding(value["stderr"], "failed stderr"),
        "run_script": _file_binding(value["run_script"], "failed run script"),
        "run_receipt": _file_binding(value["run_receipt"], "failed run receipt"),
    }


def _binding(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"{label} binding drifted")
    return {"path": _absolute(value["path"], label), "root_sha256": _sha(value["root_sha256"], label)}


def _file_binding(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "sha256"}:
        raise ValueError(f"{label} file binding drifted")
    return {"path": _absolute(value["path"], label), "sha256": _sha(value["sha256"], label)}


def _strings(value: Any, label: str) -> list[str]:
    if type(value) is not list or any(type(item) is not str for item in value):
        raise ValueError(f"{label} list drifted")
    return list(value)


def _absolute(value: Any, label: str) -> str:
    if type(value) is not str or not value.startswith("/") or value.endswith("/"):
        raise ValueError(f"{label} path drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label} SHA drifted")
    return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
