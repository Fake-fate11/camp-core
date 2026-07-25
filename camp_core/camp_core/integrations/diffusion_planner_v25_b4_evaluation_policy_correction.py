from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_fresh_preopen_authority import (
    TRACKED_AUTHORITY_FILES,
)
from .diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
    strict_equal,
)


SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_evaluator_policy_correction_authority_v1"
)
STATUS = (
    "authorized_outcome_blind_evaluator_policy_correction_from_"
    "preserved_denominator"
)
REVIEW_SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_evaluator_policy_correction_authority_review_v1"
)
REVIEW_STATUS = (
    "passed_independent_fresh_b4_evaluator_policy_correction_authority_review"
)
BENCHMARK = "fresh_b4"
PHASE = "evaluation"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
IMPLEMENTATION_SOURCE_HEAD = "7be93df20deee03587b9898e8560909662df972c"
POINTER_HEAD = "06d3a1f3a37061f93f5c9788312ae59d1356d126"
CRITICAL_IMPLEMENTATION_MANIFEST_SHA256 = (
    "f3b707d480b30e1d37d2c10355d8a824df4cff8230af7d78d803dd4504ef6c2b"
)
HOLDOUT_IDENTITY_SHA256 = (
    "5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a"
)
EXPERIMENT_PROTOCOL_SHA256 = (
    "aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f"
)
EXECUTION_PLAN_SHA256 = (
    "41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0"
)
RUN_NONCE = "8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42"
CONTROLLER_ROOT_SHA256 = (
    "06f2bf198b9983e0e15f9e0feaba52bc0d595fdd5703d73d98e21c1e8c4f08a2"
)
OPENING_RELEASE_ROOT_SHA256 = (
    "7deec7b81a1ad20dd9eb4657c0c3066ce695bc797349def843c0e7152f85851b"
)
EXECUTION_ROOT_SHA256 = (
    "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
)
EXECUTION_REVIEW_ROOT_SHA256 = (
    "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d"
)
OLD_CLOSEOUT_ROOT_SHA256 = (
    "a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398"
)
OLD_CLOSEOUT_REVIEW_ROOT_SHA256 = (
    "86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062"
)
OLD_TERMINAL_LEDGER_SHA256 = (
    "c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4"
)
OLD_TERMINAL_REASON = "post_exposure_evaluation_control_fatal"
OLD_TERMINAL_HISTORY = (
    "exposure_started",
    "full_denominator_formed",
    "terminal_failure",
)
OLD_EVALUATION_ERROR = "holdout execution/evaluation role HEAD drifted"
OLD_CONTROL_COMMAND_SHA256 = (
    "5c2134847ef9a1686d3653d48d0147912ee5abc713cf15f574dc5ec02cc0e304"
)
OLD_CONTROL_RUN_EXIT_SHA256 = (
    "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865"
)
OLD_CONTROL_STDERR_SHA256 = (
    "23ffd85aa1c6abf6c04a4bef15469fdd83a1e05a01f53aadbc6d5a4a3a1d8a60"
)
USER_OVERRIDE_DATE = "2026-07-25"
USER_OVERRIDE_DECISION = (
    "prospective_policy_correction_reuse_existing_sealed_fresh_b4_"
    "denominator_for_corrected_evaluation_only"
)
POINTER_ONLY_PATHS = (
    "camp_core/tests/test_diffusion_planner_v25_iteration_audit.py",
    "docs/diffusion_planner_current_status.md",
    "docs/diffusion_planner_v25_iteration_audit.md",
)
CONTINUATION_KEY_SCHEME = (
    "sha256(holdout_identity_sha256:old_terminal_ledger_sha256:"
    "correction_authority_root_sha256)"
)
CONTINUATION_STATE_SEQUENCE = (
    "authorized_from_preserved_denominator",
    "evaluation_started",
    "evaluation_artifact_formed",
    "independently_reviewed_terminal",
)

CORRECTION_IMPLEMENTATION_PATHS = (
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_b4_evaluation_policy_correction.py"
    ),
    (
        "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_b4_evaluation_continuation.py"
    ),
    "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_evaluation.py",
    (
        "scripts/integrations/"
        "freeze_diffusion_planner_v25_b4_evaluation_policy_correction.py"
    ),
    (
        "scripts/integrations/"
        "review_diffusion_planner_v25_b4_evaluation_policy_correction.py"
    ),
    (
        "scripts/integrations/"
        "authorize_diffusion_planner_v25_b4_evaluation_continuation.py"
    ),
)

_BINDING_FIELDS = frozenset({"path", "root_sha256"})
_FILE_BINDING_FIELDS = frozenset({"path", "sha256"})
_OLD_LEDGER_FIELDS = frozenset(
    {
        "path",
        "sha256",
        "state",
        "history",
        "terminal_reason",
        "terminal_artifact_root_sha256",
    }
)
_OLD_CONTROL_FIELDS = frozenset(
    {
        "directory",
        "run_exit",
        "error_type",
        "error_message",
        "command",
        "run_exit_file",
        "stderr",
    }
)
_CORRECTION_IMPLEMENTATION_FIELDS = frozenset(
    {"head", "manifest_sha256", "manifest_paths"}
)
_CONTINUATION_FIELDS = frozenset(
    {
        "cas_namespace",
        "identity_slot_namespace",
        "key_scheme",
        "ledger_path_template",
        "identity_slot_path_template",
        "state_sequence",
    }
)
_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "benchmark",
        "phase",
        "user_override_date",
        "user_override_decision",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "execution_plan_sha256",
        "run_nonce",
        "controller_decision",
        "opening_release",
        "execution",
        "execution_review",
        "implementation_source_head",
        "pointer_head_at_release",
        "pointer_only_changed_paths",
        "critical_implementation_manifest_sha256",
        "fixed_dp_head",
        "old_evaluation_control",
        "old_terminal_closeout",
        "old_terminal_closeout_review",
        "old_scientific_ledger",
        "correction_implementation",
        "focused_tests",
        "corrected_evaluation_output_dir",
        "corrected_evaluation_review_output_dir",
        "continuation",
        "fresh_execution_reused",
        "fresh_execution_rerun",
        "raw_outcome_inspected_before_authority",
        "scientific_contract_changed",
        "old_terminal_diagnostic_preserved",
        "new_fresh_authorized",
        "promotion_deployment_activation_authorized",
        "next_authority",
        "authority_payload_sha256",
    }
)
_REVIEW_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "reviewed_authority",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "execution_plan_sha256",
        "run_nonce",
        "implementation_source_head",
        "pointer_head_at_release",
        "pointer_only_changed_paths",
        "critical_implementation_manifest_sha256",
        "fixed_dp_head",
        "old_terminal_ledger_sha256",
        "old_terminal_state",
        "old_terminal_history",
        "old_terminal_reason",
        "old_terminal_artifact_root_sha256",
        "correction_implementation_head",
        "correction_implementation_manifest_sha256",
        "focused_test_root_sha256",
        "corrected_evaluation_output_dir",
        "corrected_evaluation_review_output_dir",
        "continuation",
        "accepted_roots_independently_verified",
        "old_diagnostic_independently_verified",
        "corrected_output_dirs_absent",
        "second_authority_or_evaluation_absent",
        "raw_outcome_values_inspected",
        "fresh_execution_rerun",
        "scientific_contract_changed",
        "promotion_deployment_activation_authorized",
    }
)


def manifest_at_git_head(
    repo: Path,
    *,
    git_head: str,
    paths: Sequence[str] = TRACKED_AUTHORITY_FILES,
) -> dict[str, Any]:
    root = Path(repo).resolve()
    head = _git_head(git_head, "manifest source")
    rows: list[dict[str, str]] = []
    for raw_relative in paths:
        relative = _safe_relative(raw_relative)
        completed = subprocess.run(
            ["git", "-C", str(root), "show", f"{head}:{relative}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        rows.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(completed.stdout).hexdigest(),
            }
        )
    return {
        "schema_version": (
            "camp_dp_v25_fresh_b2_critical_implementation_manifest_v1"
        ),
        "paths": rows,
        "manifest_sha256": canonical_sha256(rows),
    }


def verify_release_dual_head_contract(
    repo: Path,
    *,
    release: Mapping[str, Any] | None = None,
    implementation_source_head: str | None = None,
    pointer_head_at_release: str | None = None,
    critical_implementation_manifest_sha256: str | None = None,
    execution_heads: Mapping[str, Any],
    execution_review_heads: Mapping[str, Any],
    fixed_dp_head: str = FIXED_DP_HEAD,
) -> dict[str, Any]:
    if release is not None:
        if type(release) is not dict:
            raise ValueError("holdout opening release binding drifted")
        if any(
            value is not None
            for value in (
                implementation_source_head,
                pointer_head_at_release,
                critical_implementation_manifest_sha256,
            )
        ):
            raise ValueError("holdout dual-HEAD inputs are ambiguous")
        implementation_source_head = release.get(
            "implementation_source_head"
        )
        pointer_head_at_release = release.get("pointer_head_at_release")
        critical_implementation_manifest_sha256 = release.get(
            "critical_implementation_manifest_sha256"
        )
    source = _git_head(implementation_source_head, "implementation source")
    pointer = _git_head(pointer_head_at_release, "pointer at release")
    manifest_sha = _sha(
        critical_implementation_manifest_sha256,
        "critical implementation manifest",
    )
    if fixed_dp_head != FIXED_DP_HEAD:
        raise ValueError("holdout fixed DP HEAD drifted")
    expected_heads = {"camp_head": source, "fixed_dp_head": FIXED_DP_HEAD}
    if (
        type(execution_heads) is not dict
        or type(execution_review_heads) is not dict
        or not strict_equal(execution_heads, expected_heads)
        or not strict_equal(execution_review_heads, expected_heads)
    ):
        raise ValueError("holdout execution source HEAD binding drifted")
    changed = _git_changed_paths(Path(repo).resolve(), source, pointer)
    if source == pointer:
        if changed:
            raise ValueError("same-HEAD pointer diff drifted")
    elif tuple(changed) != POINTER_ONLY_PATHS:
        raise ValueError("holdout pointer-only path allowlist drifted")
    source_manifest = manifest_at_git_head(
        Path(repo).resolve(),
        git_head=source,
    )
    if source_manifest["manifest_sha256"] != manifest_sha:
        raise ValueError("holdout release critical manifest drifted")
    return {
        "implementation_source_head": source,
        "pointer_head_at_release": pointer,
        "pointer_only_changed_paths": list(changed),
        "critical_implementation_manifest_sha256": manifest_sha,
        "fixed_dp_head": FIXED_DP_HEAD,
    }


def correction_implementation_manifest(repo: Path) -> dict[str, Any]:
    root = Path(repo).resolve()
    rows: list[dict[str, str]] = []
    for raw_relative in CORRECTION_IMPLEMENTATION_PATHS:
        relative = _safe_relative(raw_relative)
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--error-unmatch",
                "--",
                relative,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not completed.stdout:
            raise ValueError(f"correction implementation is untracked: {relative}")
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file() or path.is_symlink():
            raise ValueError(
                f"correction implementation path is unsafe: {relative}"
            )
        rows.append({"path": relative, "sha256": _file_sha256(path)})
    return {
        "schema_version": (
            "camp_dp_v25_b4_evaluation_policy_correction_manifest_v1"
        ),
        "paths": rows,
        "manifest_sha256": canonical_sha256(rows),
    }


def freeze_correction_authority(
    *,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    execution_plan_sha256: str,
    run_nonce: str,
    controller_decision: Mapping[str, Any],
    opening_release: Mapping[str, Any],
    execution: Mapping[str, Any],
    execution_review: Mapping[str, Any],
    implementation_source_head: str,
    pointer_head_at_release: str,
    pointer_only_changed_paths: Sequence[str],
    critical_implementation_manifest_sha256: str,
    old_evaluation_control: Mapping[str, Any],
    old_terminal_closeout: Mapping[str, Any],
    old_terminal_closeout_review: Mapping[str, Any],
    old_scientific_ledger: Mapping[str, Any],
    correction_implementation: Mapping[str, Any],
    focused_tests: Mapping[str, Any],
    corrected_evaluation_output_dir: str,
    corrected_evaluation_review_output_dir: str,
    continuation_cas_namespace: str,
    continuation_identity_slot_namespace: str,
) -> dict[str, Any]:
    identity = _sha(holdout_identity_sha256, "holdout identity")
    protocol = _sha(experiment_protocol_sha256, "experiment protocol")
    plan = _sha(execution_plan_sha256, "execution plan")
    nonce = _sha(run_nonce, "run nonce")
    controller = _binding(controller_decision, "controller")
    release = _binding(opening_release, "opening release")
    execution_binding = _binding(execution, "execution")
    execution_review_binding = _binding(execution_review, "execution review")
    source = _git_head(implementation_source_head, "implementation source")
    pointer = _git_head(pointer_head_at_release, "pointer at release")
    changed = _exact_string_list(
        pointer_only_changed_paths, "pointer-only changed paths"
    )
    manifest_sha = _sha(
        critical_implementation_manifest_sha256,
        "critical implementation manifest",
    )
    old_control = _old_control(old_evaluation_control)
    old_closeout = _binding(old_terminal_closeout, "old terminal closeout")
    old_closeout_review = _binding(
        old_terminal_closeout_review, "old terminal closeout review"
    )
    old_ledger = _old_ledger(old_scientific_ledger)
    correction = _correction_implementation(correction_implementation)
    focused = _binding(focused_tests, "focused tests")
    evaluation_dir = _absolute_posix(
        corrected_evaluation_output_dir, "corrected evaluation output"
    )
    review_dir = _absolute_posix(
        corrected_evaluation_review_output_dir,
        "corrected evaluation review output",
    )
    head8 = correction["head"][:8]
    if (
        identity != HOLDOUT_IDENTITY_SHA256
        or protocol != EXPERIMENT_PROTOCOL_SHA256
        or plan != EXECUTION_PLAN_SHA256
        or nonce != RUN_NONCE
        or controller["root_sha256"] != CONTROLLER_ROOT_SHA256
        or release["root_sha256"] != OPENING_RELEASE_ROOT_SHA256
        or execution_binding["root_sha256"] != EXECUTION_ROOT_SHA256
        or execution_review_binding["root_sha256"]
        != EXECUTION_REVIEW_ROOT_SHA256
        or source != IMPLEMENTATION_SOURCE_HEAD
        or pointer != POINTER_HEAD
        or tuple(changed) != POINTER_ONLY_PATHS
        or manifest_sha != CRITICAL_IMPLEMENTATION_MANIFEST_SHA256
        or old_closeout["root_sha256"] != OLD_CLOSEOUT_ROOT_SHA256
        or old_closeout_review["root_sha256"]
        != OLD_CLOSEOUT_REVIEW_ROOT_SHA256
        or old_ledger["sha256"] != OLD_TERMINAL_LEDGER_SHA256
        or evaluation_dir
        != (
            "/root/autodl-tmp/"
            "camp_dp_v25_fresh_b4_evaluation_corrected_"
            f"{head8}_8680c1b19ce0620b"
        )
        or review_dir
        != (
            "/root/autodl-tmp/"
            "camp_dp_v25_fresh_b4_evaluation_corrected_review_"
            f"{head8}_8680c1b19ce0620b"
        )
    ):
        raise ValueError("Fresh B4 correction authority binding drifted")
    continuation = _continuation(
        cas_namespace=continuation_cas_namespace,
        identity_slot_namespace=continuation_identity_slot_namespace,
    )
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "benchmark": BENCHMARK,
        "phase": PHASE,
        "user_override_date": USER_OVERRIDE_DATE,
        "user_override_decision": USER_OVERRIDE_DECISION,
        "holdout_identity_sha256": identity,
        "experiment_protocol_sha256": protocol,
        "execution_plan_sha256": plan,
        "run_nonce": nonce,
        "controller_decision": controller,
        "opening_release": release,
        "execution": execution_binding,
        "execution_review": execution_review_binding,
        "implementation_source_head": source,
        "pointer_head_at_release": pointer,
        "pointer_only_changed_paths": changed,
        "critical_implementation_manifest_sha256": manifest_sha,
        "fixed_dp_head": FIXED_DP_HEAD,
        "old_evaluation_control": old_control,
        "old_terminal_closeout": old_closeout,
        "old_terminal_closeout_review": old_closeout_review,
        "old_scientific_ledger": old_ledger,
        "correction_implementation": correction,
        "focused_tests": focused,
        "corrected_evaluation_output_dir": evaluation_dir,
        "corrected_evaluation_review_output_dir": review_dir,
        "continuation": continuation,
        "fresh_execution_reused": True,
        "fresh_execution_rerun": False,
        "raw_outcome_inspected_before_authority": False,
        "scientific_contract_changed": False,
        "old_terminal_diagnostic_preserved": True,
        "new_fresh_authorized": False,
        "promotion_deployment_activation_authorized": False,
        "next_authority": (
            "single_corrected_evaluation_then_independent_review_only"
        ),
    }
    payload["authority_payload_sha256"] = canonical_sha256(payload)
    return payload


def validate_correction_authority(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError("Fresh B4 correction authority field set drifted")
    expected = freeze_correction_authority(
        holdout_identity_sha256=value["holdout_identity_sha256"],
        experiment_protocol_sha256=value["experiment_protocol_sha256"],
        execution_plan_sha256=value["execution_plan_sha256"],
        run_nonce=value["run_nonce"],
        controller_decision=value["controller_decision"],
        opening_release=value["opening_release"],
        execution=value["execution"],
        execution_review=value["execution_review"],
        implementation_source_head=value["implementation_source_head"],
        pointer_head_at_release=value["pointer_head_at_release"],
        pointer_only_changed_paths=value["pointer_only_changed_paths"],
        critical_implementation_manifest_sha256=value[
            "critical_implementation_manifest_sha256"
        ],
        old_evaluation_control=value["old_evaluation_control"],
        old_terminal_closeout=value["old_terminal_closeout"],
        old_terminal_closeout_review=value[
            "old_terminal_closeout_review"
        ],
        old_scientific_ledger=value["old_scientific_ledger"],
        correction_implementation=value["correction_implementation"],
        focused_tests=value["focused_tests"],
        corrected_evaluation_output_dir=value[
            "corrected_evaluation_output_dir"
        ],
        corrected_evaluation_review_output_dir=value[
            "corrected_evaluation_review_output_dir"
        ],
        continuation_cas_namespace=value["continuation"]["cas_namespace"],
        continuation_identity_slot_namespace=value["continuation"][
            "identity_slot_namespace"
        ],
    )
    if not strict_equal(value, expected):
        raise ValueError("Fresh B4 correction authority exact value drifted")
    return expected


def freeze_correction_authority_review(
    *,
    reviewed_authority: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    authority_binding = _binding(reviewed_authority, "reviewed authority")
    value = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "status": REVIEW_STATUS,
        "reviewed_authority": authority_binding,
        "holdout_identity_sha256": authority["holdout_identity_sha256"],
        "experiment_protocol_sha256": authority[
            "experiment_protocol_sha256"
        ],
        "execution_plan_sha256": authority["execution_plan_sha256"],
        "run_nonce": authority["run_nonce"],
        "implementation_source_head": authority[
            "implementation_source_head"
        ],
        "pointer_head_at_release": authority["pointer_head_at_release"],
        "pointer_only_changed_paths": list(
            authority["pointer_only_changed_paths"]
        ),
        "critical_implementation_manifest_sha256": authority[
            "critical_implementation_manifest_sha256"
        ],
        "fixed_dp_head": authority["fixed_dp_head"],
        "old_terminal_ledger_sha256": authority[
            "old_scientific_ledger"
        ]["sha256"],
        "old_terminal_state": authority["old_scientific_ledger"]["state"],
        "old_terminal_history": list(
            authority["old_scientific_ledger"]["history"]
        ),
        "old_terminal_reason": authority["old_scientific_ledger"][
            "terminal_reason"
        ],
        "old_terminal_artifact_root_sha256": authority[
            "old_scientific_ledger"
        ]["terminal_artifact_root_sha256"],
        "correction_implementation_head": authority[
            "correction_implementation"
        ]["head"],
        "correction_implementation_manifest_sha256": authority[
            "correction_implementation"
        ]["manifest_sha256"],
        "focused_test_root_sha256": authority["focused_tests"][
            "root_sha256"
        ],
        "corrected_evaluation_output_dir": authority[
            "corrected_evaluation_output_dir"
        ],
        "corrected_evaluation_review_output_dir": authority[
            "corrected_evaluation_review_output_dir"
        ],
        "continuation": json.loads(json.dumps(authority["continuation"])),
        "accepted_roots_independently_verified": True,
        "old_diagnostic_independently_verified": True,
        "corrected_output_dirs_absent": True,
        "second_authority_or_evaluation_absent": True,
        "raw_outcome_values_inspected": False,
        "fresh_execution_rerun": False,
        "scientific_contract_changed": False,
        "promotion_deployment_activation_authorized": False,
    }
    return validate_correction_authority_review(value)


def validate_correction_authority_review(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _REVIEW_FIELDS:
        raise ValueError("Fresh B4 correction review field set drifted")
    result = json.loads(json.dumps(value))
    if (
        result["schema_version"] != REVIEW_SCHEMA_VERSION
        or result["status"] != REVIEW_STATUS
        or result["holdout_identity_sha256"] != HOLDOUT_IDENTITY_SHA256
        or result["experiment_protocol_sha256"]
        != EXPERIMENT_PROTOCOL_SHA256
        or result["execution_plan_sha256"] != EXECUTION_PLAN_SHA256
        or result["run_nonce"] != RUN_NONCE
        or result["implementation_source_head"] != IMPLEMENTATION_SOURCE_HEAD
        or result["pointer_head_at_release"] != POINTER_HEAD
        or tuple(result["pointer_only_changed_paths"]) != POINTER_ONLY_PATHS
        or result["critical_implementation_manifest_sha256"]
        != CRITICAL_IMPLEMENTATION_MANIFEST_SHA256
        or result["fixed_dp_head"] != FIXED_DP_HEAD
        or result["old_terminal_ledger_sha256"]
        != OLD_TERMINAL_LEDGER_SHA256
        or result["old_terminal_state"] != "terminal_failure"
        or tuple(result["old_terminal_history"]) != OLD_TERMINAL_HISTORY
        or result["old_terminal_reason"] != OLD_TERMINAL_REASON
        or result["old_terminal_artifact_root_sha256"]
        != OLD_CLOSEOUT_ROOT_SHA256
        or any(
            result[name] is not True
            for name in (
                "accepted_roots_independently_verified",
                "old_diagnostic_independently_verified",
                "corrected_output_dirs_absent",
                "second_authority_or_evaluation_absent",
            )
        )
        or any(
            result[name] is not False
            for name in (
                "raw_outcome_values_inspected",
                "fresh_execution_rerun",
                "scientific_contract_changed",
                "promotion_deployment_activation_authorized",
            )
        )
    ):
        raise ValueError("Fresh B4 correction review value drifted")
    _binding(result["reviewed_authority"], "reviewed authority")
    _git_head(
        result["correction_implementation_head"],
        "correction implementation",
    )
    _sha(
        result["correction_implementation_manifest_sha256"],
        "correction implementation manifest",
    )
    _sha(result["focused_test_root_sha256"], "focused test root")
    _absolute_posix(
        result["corrected_evaluation_output_dir"],
        "corrected evaluation output",
    )
    _absolute_posix(
        result["corrected_evaluation_review_output_dir"],
        "corrected evaluation review output",
    )
    continuation = _continuation(
        cas_namespace=result["continuation"]["cas_namespace"],
        identity_slot_namespace=result["continuation"][
            "identity_slot_namespace"
        ],
    )
    if not strict_equal(result["continuation"], continuation):
        raise ValueError("Fresh B4 correction review continuation drifted")
    return result


def _git_changed_paths(repo: Path, source: str, pointer: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", source, pointer, "--"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return tuple(
        sorted(
            line.replace("\\", "/")
            for line in completed.stdout.splitlines()
            if line
        )
    )


def _binding(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != _BINDING_FIELDS:
        raise ValueError(f"{label} binding field set drifted")
    return {
        "path": _absolute_posix(value["path"], label),
        "root_sha256": _sha(value["root_sha256"], label),
    }


def _file_binding(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != _FILE_BINDING_FIELDS:
        raise ValueError(f"{label} file binding field set drifted")
    return {
        "path": _absolute_posix(value["path"], label),
        "sha256": _sha(value["sha256"], label),
    }


def _old_control(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _OLD_CONTROL_FIELDS:
        raise ValueError("old evaluation control field set drifted")
    result = {
        "directory": _absolute_posix(
            value["directory"], "old evaluation control"
        ),
        "run_exit": value["run_exit"],
        "error_type": value["error_type"],
        "error_message": value["error_message"],
        "command": _file_binding(value["command"], "old control command"),
        "run_exit_file": _file_binding(
            value["run_exit_file"], "old control run.exit"
        ),
        "stderr": _file_binding(value["stderr"], "old control stderr"),
    }
    if (
        type(result["run_exit"]) is not int
        or result["run_exit"] != 1
        or result["error_type"] != "ValueError"
        or result["error_message"] != OLD_EVALUATION_ERROR
        or result["command"]["sha256"] != OLD_CONTROL_COMMAND_SHA256
        or result["run_exit_file"]["sha256"]
        != OLD_CONTROL_RUN_EXIT_SHA256
        or result["stderr"]["sha256"] != OLD_CONTROL_STDERR_SHA256
    ):
        raise ValueError("old evaluation control value drifted")
    return result


def _old_ledger(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _OLD_LEDGER_FIELDS:
        raise ValueError("old scientific ledger field set drifted")
    result = {
        "path": _absolute_posix(value["path"], "old scientific ledger"),
        "sha256": _sha(value["sha256"], "old scientific ledger"),
        "state": value["state"],
        "history": _exact_string_list(
            value["history"], "old scientific history"
        ),
        "terminal_reason": value["terminal_reason"],
        "terminal_artifact_root_sha256": _sha(
            value["terminal_artifact_root_sha256"],
            "old terminal artifact",
        ),
    }
    if (
        result["sha256"] != OLD_TERMINAL_LEDGER_SHA256
        or result["state"] != "terminal_failure"
        or tuple(result["history"]) != OLD_TERMINAL_HISTORY
        or result["terminal_reason"] != OLD_TERMINAL_REASON
        or result["terminal_artifact_root_sha256"]
        != OLD_CLOSEOUT_ROOT_SHA256
    ):
        raise ValueError("old scientific terminal ledger drifted")
    return result


def _correction_implementation(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _CORRECTION_IMPLEMENTATION_FIELDS
    ):
        raise ValueError("correction implementation field set drifted")
    paths = _exact_string_list(
        value["manifest_paths"], "correction manifest paths"
    )
    if tuple(paths) != CORRECTION_IMPLEMENTATION_PATHS:
        raise ValueError("correction implementation path set drifted")
    return {
        "head": _git_head(value["head"], "correction implementation"),
        "manifest_sha256": _sha(
            value["manifest_sha256"], "correction implementation manifest"
        ),
        "manifest_paths": paths,
    }


def _continuation(
    *,
    cas_namespace: str,
    identity_slot_namespace: str,
) -> dict[str, Any]:
    cas_root = _absolute_posix(cas_namespace, "continuation CAS namespace")
    slot_root = _absolute_posix(
        identity_slot_namespace, "continuation identity namespace"
    )
    return {
        "cas_namespace": cas_root,
        "identity_slot_namespace": slot_root,
        "key_scheme": CONTINUATION_KEY_SCHEME,
        "ledger_path_template": (
            f"{cas_root}/"
            "{sha256(identity:old_terminal_ledger:authority_root)}.json"
        ),
        "identity_slot_path_template": (
            f"{slot_root}/"
            "{sha256(identity:old_terminal_ledger)}.json"
        ),
        "state_sequence": list(CONTINUATION_STATE_SEQUENCE),
    }


def _safe_relative(value: Any) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise ValueError("correction implementation path is unsafe")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        raise ValueError("correction implementation path is unsafe")
    return value


def _absolute_posix(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or not value.startswith("/")
        or value.endswith("/")
        or "/../" in f"{value}/"
        or "/./" in f"{value}/"
    ):
        raise ValueError(f"{label} path drifted")
    return value


def _exact_string_list(value: Any, label: str) -> list[str]:
    if (
        type(value) is not list
        and type(value) is not tuple
    ):
        raise ValueError(f"{label} must be a list")
    result = list(value)
    if any(type(item) is not str or not item for item in result):
        raise ValueError(f"{label} value drifted")
    if len(result) != len(set(result)):
        raise ValueError(f"{label} contains duplicates")
    return result


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} SHA drifted")
    return value


def _git_head(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{label} HEAD drifted")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
