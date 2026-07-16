from __future__ import annotations

import argparse
import contextlib
import ctypes
import errno
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CANONICAL_CAMP_REPO = Path("/root/autodl-tmp/camp_core")
CANONICAL_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
CANONICAL_OUTPUT_PARENT = Path("/root/autodl-tmp")
CANONICAL_ORIGIN_URL = "https://github.com/Fake-fate11/camp-core.git"
GLOBAL_LOCK_PATH = Path(
    "/root/autodl-tmp/camp_dp_v24_paired_evaluation.global.lock"
)
CANONICAL_HOLDOUT_STATE_PATH = Path(
    "/root/autodl-tmp/camp_dp_v24_paired_holdout_once_state.json"
)
AUDIT_RELATIVE_PATH = Path("docs/diffusion_planner_v24_iteration_audit.md")
CURRENT_STATUS_RELATIVE_PATH = Path("docs/diffusion_planner_current_status.md")
AUTHORIZED_NEXT_WORK_TARGET = (
    "v24_evidence_package_and_preregistered_claim_decision_execution_only"
)
OUTPUT_NAME_PREFIX = "camp_dp_v24_evidence_package_and_claim_decision_"
REVIEW_NAME_PREFIX = (
    "camp_dp_v24_paired_holdout_main_once_execution_independent_review_"
)
STATIC_PREFLIGHT_NAME_PREFIX = "camp_dp_v24_evidence_claim_static_preflight_"
FORBIDDEN_LIVE_PROCESS_TOKENS = (
    "evaluate_diffusion_planner_v24_pairs.py",
    "review_diffusion_planner_v24_holdout_main_result.py",
)
AUTHORITY_BINDING_FIELDS = (
    "current_v24_reviewer_artifact",
    "current_v24_reviewer_artifact_root_sha256",
    "current_v24_reviewer_source_head",
    "current_v24_holdout_state",
    "current_v24_holdout_state_sha256",
    "current_v24_holdout_open_count",
    "current_v24_holdout_rerun_authorized",
    "fixed_dp_head",
    "next_work_target",
)
AUTHORITY_CONTROL_FIELDS = (
    "current_v24_status",
    "current_v24_artifact_source_head",
    "current_v24_final_synced_head",
    "current_v24_artifact",
    "current_v24_artifact_root_sha256",
    "source_a_status",
    "source_a_terminal",
    "source_b_status",
    "source_b_terminal",
    "authorized_source_count",
    "source_terminal_count",
    "global_stop_authorized",
    "global_stop_reason",
)
AUTHORIZED_CURRENT_STATUS = (
    "v24_evidence_package_and_preregistered_claim_decision_tdd_static_preflight_passed"
)
AUTHORIZED_SOURCE_B_STATUS = (
    "paired_holdout_main_once_execution_complete_open_count_1_rerun_forbidden_"
    "independent_result_review_passed_evidence_claim_static_preflight_passed_"
    "honest_no_claim_execution_pending"
)
REVIEW_SCHEMA = (
    "camp_dp_v24_paired_holdout_main_once_execution_independent_review_v1"
)
PACKAGE_SCHEMA = "camp_dp_v24_evidence_package_v1"
CLAIM_SCHEMA = "camp_dp_v24_preregistered_claim_decision_v1"
EXPECTED_DECISION = "honest_no_claim"
EXPECTED_REVIEW_CHECK_COUNT = 27
EXPECTED_REVIEW_CHECK_NAMES = frozenset(
    {
        "all_source_complete_seals_verified",
        "execution_launch_chain_bound",
        "preflight_authorization_reviews_passed",
        "split_and_training_roots_verified",
        "split_census_schedule_exact_join_verified",
        "source_census_arc_length_denominators_verified",
        "frozen_train_coverage_and_learning_curve_risk_disclosed",
        "runtime_selector_matches_training",
        "fixed_request_and_assets_hash_bound",
        "main_schedule_24x5_120",
        "arm_order_hash_rank_balance_60_60",
        "outcome_blind_preregistered_arm_order_control_verified",
        "independent_reset_same_initial_state_and_exogenous_seed_verified",
        "one_family_three_corridors",
        "holdout_state_exact_open_once",
        "live_camp_and_fixed_dp_clean",
        "producer_code_provenance_unchanged",
        "all_pair_arm_tick_receipts_recomputed",
        "t0_cross_arm_identity_only",
        "post_divergence_cross_arm_tensors_not_compared",
        "safety_secondary_latency_recomputed",
        "producer_descriptive_statistics_consistent",
        "raw_byte_evidence_limit_disclosed",
        "latency_descriptive_only",
        "latency_comparative_conclusion_forbidden",
        "map_family_ci_and_unseen_claim_forbidden",
        "disk_floor",
    }
)
EXPECTED_REVIEW_MANIFEST_PATHS = frozenset(
    {
        "COMMAND.txt",
        "HEADS.txt",
        "provenance.json",
        "recomputed_metrics.json",
        "review_result.json",
        "run.exit",
        "schedule_receipt.json",
        "stderr.txt",
        "stdout.txt",
        "summary.md",
    }
)
EXPECTED_SOURCE_ROOT_NAMES = frozenset(
    {
        "execution",
        "launch",
        "preflight",
        "preflight_review",
        "pilot_review",
        "authorization",
        "authorization_review",
        "split",
        "split_review",
        "route_census",
        "route_census_review",
        "training",
        "training_review",
        "runtime_selector",
    }
)
EVIDENCE_GUARD_NAMES = (
    "artifact_sha_verified",
    "per_arm_candidate_immutability_verified",
    "per_arm_candidate0_default_identity_verified",
    "t0_cross_arm_input_and_candidate_identity_verified",
    "independent_review_passed",
    "split_zero_overlap_verified",
    "holdout_once_verified",
    "arm_order_balance_verified",
    "feature_identity_denylist_verified",
)
CLAIM_GATE_NAMES = (
    "retention_rate",
    "paired_complete_rate",
    "source_invalid_rate",
    "execution_invalid_rate",
    "safety_cost_mean_delta_below_zero",
    "clustered_ci95_upper_below_zero",
    "better_exceeds_worse",
    "no_additional_collision_pairs",
    "no_additional_offroad_pairs",
    "no_additional_red_light_pairs",
    "no_additional_wrong_way_pairs",
    "evidence_guards",
)
MAJOR_EVENT_FIELDS = (
    "collision_any",
    "offroad_rate",
    "red_light_violation_any",
    "wrong_way_rate",
)
SAFETY_COMPONENT_NAMES = frozenset(
    {
        "collision_any",
        "near_miss_noncollision_rate",
        "offroad_rate",
        "wrong_way_rate",
        "red_light_violation_any",
        "speed_limit_violation_rate",
    }
)
SPEED_SENSITIVITY_NAMES = frozenset(
    {
        "0.0",
        "0.05",
        "0.1",
        "0.2",
        "continuous_maximum_excess_mps_delta",
        "continuous_mean_excess_mps_delta",
        "continuous_excess_duration_s_delta",
        "continuous_magnitude_duration_m_delta",
    }
)
SECONDARY_DIRECTIONS = {
    "dt_s": "descriptive_only",
    "route_progress_m": "higher_is_better",
    "route_length_m": "descriptive_only",
    "route_completion_rate": "higher_is_better",
    "distance_traveled_m": "descriptive_only",
    "stopped_fraction": "descriptive_only",
    "mean_speed_mps": "descriptive_only",
    "max_speed_mps": "descriptive_only",
    "mean_abs_acceleration_mps2": "descriptive_only",
    "max_acceleration_mps2": "descriptive_only",
    "mean_abs_jerk_mps3": "lower_is_better",
    "max_jerk_mps3": "lower_is_better",
    "mean_abs_yaw_rate_radps": "descriptive_only",
    "max_abs_yaw_rate_radps": "descriptive_only",
    "mean_abs_lateral_acceleration_mps2": "lower_is_better",
    "max_abs_lateral_acceleration_mps2": "lower_is_better",
}
SECONDARY_NAMES = frozenset(SECONDARY_DIRECTIONS)
LATENCY_STAGE_NAMES = {
    "dp": frozenset({"default", "tracker", "total"}),
    "camp": frozenset(
        {"default", "k8_candidate", "atom", "selector", "tracker", "total"}
    ),
}
METRICS_TOP_LEVEL_NAMES = frozenset(
    {
        "schema",
        "bootstrap_contract",
        "coverage",
        "failure_accounting",
        "safety_cost_delta",
        "strata",
        "components",
        "speed_sensitivity",
        "secondary",
        "additional_event_pairs",
        "candidate_selection",
        "latency",
        "latency_comparison_authorized",
        "latency_reporting_role",
        "evidence_guards",
        "claim_gate_result",
    }
)
EXPECTED_MEAN_DELTA = -0.014322916666666666
EXPECTED_CI95_LOW = -0.06380208333333333
EXPECTED_CI95_HIGH = 0.01953125
EXPECTED_BETTER_TIE_WORSE = {"better": 4, "tie": 113, "worse": 3}
EXPECTED_TRAIN_SOURCE_COVERAGE = {
    "retained": 1875,
    "complete": 1054,
    "failed": 821,
    "failure_rate": 821 / 1875,
}
EXPECTED_LEARNING_CURVE_STABILITY = {
    "levels_percent": [25, 50, 75, 100],
    "weights_l1_to_full": [
        0.3998769535788546,
        0.18971764213000833,
        0.20611942009995507,
        0.0,
    ],
    "effective_support_gt_1e_6": [3, 3, 3, 3],
    "candidate0_selection_rate": [
        0.20219094175157548,
        0.2786534178516361,
        0.25863020176544765,
        0.270222432001888,
    ],
    "selected_index_histogram_l1_to_full": [
        0.13606298050062507,
        0.019765760782601463,
        0.023184460472880697,
        0.0,
    ],
    "selected_index_argmax": [0, 0, 0, 0],
    "full_effective_support_indices": [7, 8, 13],
    "full_effective_support_names": [
        "lane_deviation",
        "clearance",
        "dp_prior_jerk_excess_cost",
    ],
    "full_effective_support_weights": [
        0.4178605234516141,
        0.5784894895043772,
        0.0036499870440052018,
    ],
    "distribution_concentration_is_automatic_failure": False,
    "risk_disclosure_required": True,
    "calibration_or_holdout_repair_authorized": False,
}
MINIMUM_FREE_BYTES = 10 * 1024**3
HEX = frozenset("0123456789abcdef")
ALLOWED_CLAIM_TEXT = (
    "Within the frozen single held-out map family, three corridor groups, and "
    "120 paired runs, CAMP's SafetyCost mean was directionally lower than the "
    "DP operational candidate-0 default, but the preregistered clustered CI95 "
    "crossed zero, so the preregistered safety-improvement claim is not supported."
)
FORBIDDEN_CLAIMS = (
    "statistically_supported_safety_improvement",
    "broad_unseen_map_generalization",
    "map_family_level_ci",
    "native_ranked_top1_superiority",
    "comparative_latency_conclusion",
    "real_world_safety",
    "promotion",
    "deployment",
    "online_activation",
    "independent_raw_candidate_tensor_rehash",
    "independent_raw_atom_matrix_recomputation",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def _require_sha256(value: Any, name: str) -> str:
    if not _is_sha256(value):
        raise ValueError(f"{name} must be a 64-character lowercase SHA256")
    return str(value)


def _require_git_oid(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or not set(value) <= HEX:
        raise ValueError(f"{name} must be a 40-character lowercase Git OID")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _require_finite_json(value: Any, name: str = "JSON") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} contains a non-finite number")
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require_finite_json(item, f"{name}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _require_finite_json(item, f"{name}[{index}]")


def _load_json(path: Path) -> Any:
    return _loads_json_bytes(Path(path).read_bytes(), str(path))


def _loads_json_bytes(value: bytes, name: str) -> Any:
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{name} is not valid UTF-8") from exc
    parsed = json.loads(
        text,
        parse_constant=_reject_json_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )
    _require_finite_json(parsed, name)
    return parsed


def _write_json(path: Path, value: Any) -> None:
    Path(path).write_text(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _mapping(container: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = container.get(name)
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _exact_int(value: Any, name: str, expected: int | None = None) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an exact integer")
    if expected is not None and value != expected:
        raise ValueError(f"{name} mismatch")
    return value


def _finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def verify_complete_seal(
    root: Path,
    expected_root_sha256: str,
    *,
    exact_manifest_paths: frozenset[str] | None = None,
) -> dict[str, Any]:
    raw_root = Path(root)
    if raw_root.is_symlink():
        raise ValueError("review artifact root must not be a symlink")
    root = raw_root.resolve()
    expected_root_sha256 = _require_sha256(
        expected_root_sha256, "review expected root"
    )
    if not root.is_dir():
        raise ValueError("review artifact directory is missing")
    sums = root / "SHA256SUMS"
    root_sums = root / "ROOT_SHA256SUMS"
    if not sums.is_file() or not root_sums.is_file():
        raise ValueError("review complete seal is missing")
    manifest_bytes = sums.read_bytes()
    actual_root = _sha256_bytes(manifest_bytes)
    if actual_root != expected_root_sha256:
        raise ValueError("review root SHA256 mismatch")
    if root_sums.read_bytes() != f"{actual_root}  SHA256SUMS\n".encode("ascii"):
        raise ValueError("review ROOT_SHA256SUMS mismatch")

    declared: dict[str, str] = {}
    try:
        manifest_text = manifest_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("review SHA256SUMS is not valid UTF-8") from exc
    for line_number, line in enumerate(
        manifest_text.splitlines(), start=1
    ):
        if line.count("  ") != 1 or line != line.strip():
            raise ValueError(f"malformed SHA256SUMS line {line_number}")
        digest, relative = line.split("  ", 1)
        _require_sha256(digest, f"manifest digest line {line_number}")
        pure = PurePosixPath(relative)
        if (
            not relative
            or pure.is_absolute()
            or ".." in pure.parts
            or "\\" in relative
            or pure.as_posix() != relative
            or relative in declared
            or relative in {"SHA256SUMS", "ROOT_SHA256SUMS"}
        ):
            raise ValueError(f"unsafe or duplicate manifest path: {relative}")
        path = root.joinpath(*pure.parts)
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"manifest file is missing or symlinked: {relative}")
        if _sha256_file(path) != digest:
            raise ValueError(f"manifest file SHA256 mismatch: {relative}")
        declared[relative] = digest

    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("review artifact contains a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            actual.add(relative)
    if actual != set(declared):
        raise ValueError("review seal is incomplete")
    if exact_manifest_paths is not None and set(declared) != set(
        exact_manifest_paths
    ):
        raise ValueError("review manifest path set mismatch")
    return {
        "root": root,
        "root_sha256": actual_root,
        "file_count": len(declared),
        "manifest_digests": dict(sorted(declared.items())),
    }


def _read_verified_sealed_bytes(
    seal: Mapping[str, Any], relative: str
) -> bytes:
    digests = _mapping(seal, "manifest_digests")
    expected = digests.get(relative)
    if not _is_sha256(expected):
        raise ValueError(f"sealed file is not declared: {relative}")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
        raise ValueError(f"unsafe sealed file path: {relative}")
    root = Path(str(seal.get("root")))
    path = root.joinpath(*pure.parts)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"sealed file is missing or symlinked: {relative}")
    value = path.read_bytes()
    if _sha256_bytes(value) != expected:
        raise ValueError(f"sealed file changed before verified read: {relative}")
    return value


def _seal_artifact(root: Path) -> str:
    root = Path(root)
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    lines = [
        f"{_sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in files
    ]
    manifest_bytes = ("\n".join(lines) + "\n").encode("utf-8")
    (root / "SHA256SUMS").write_bytes(manifest_bytes)
    root_sha256 = _sha256_bytes(manifest_bytes)
    (root / "ROOT_SHA256SUMS").write_bytes(
        f"{root_sha256}  SHA256SUMS\n".encode("ascii")
    )
    return root_sha256


def _parse_heads_bytes(value: bytes) -> dict[str, str]:
    try:
        text = value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("review HEADS receipt is not ASCII") from exc
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result or not value:
            raise ValueError("review HEADS receipt is malformed")
        result[key] = value
    expected = {
        "CAMP_HEAD",
        "EXECUTION_SOURCE_HEAD",
        "PREFLIGHT_CAMP_HEAD",
        "PILOT_REVIEW_CAMP_HEAD",
        "PILOT_EXECUTION_SOURCE_HEAD",
        "FIXED_DP_HEAD",
    }
    if set(result) != expected:
        raise ValueError("review HEADS key set mismatch")
    for key in expected:
        _require_git_oid(result[key], f"review HEADS {key}")
    return result


def _validate_source_root_inventory(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, Mapping) or set(value) != EXPECTED_SOURCE_ROOT_NAMES:
        raise ValueError("review source-root inventory mismatch")
    inventory: dict[str, dict[str, Any]] = {}
    for name in sorted(EXPECTED_SOURCE_ROOT_NAMES):
        receipt = value[name]
        if not isinstance(receipt, Mapping):
            raise ValueError(f"review source root {name} must be a mapping")
        root_sha256 = _require_sha256(
            receipt.get("root_sha256"), f"review source root {name}"
        )
        file_count = _exact_int(
            receipt.get("file_count"), f"review source root {name} file count"
        )
        manifest_paths = receipt.get("manifest_paths")
        root_path = receipt.get("root")
        if (
            receipt.get("label") != name
            or file_count <= 0
            or not isinstance(manifest_paths, list)
        ):
            raise ValueError(f"review source root {name} receipt is incomplete")
        if (
            not isinstance(root_path, str)
            or not root_path
            or not (
                PurePosixPath(root_path).is_absolute()
                or PureWindowsPath(root_path).is_absolute()
            )
        ):
            raise ValueError(f"review source root {name} path is not absolute")
        if (
            len(manifest_paths) != file_count
            or len(set(manifest_paths)) != len(manifest_paths)
            or any(
                not isinstance(path, str)
                or not path
                or PurePosixPath(path).is_absolute()
                or ".." in PurePosixPath(path).parts
                or "\\" in path
                or PurePosixPath(path).as_posix() != path
                for path in manifest_paths
            )
        ):
            raise ValueError(f"review source root {name} manifest mismatch")
        inventory[name] = {
            "label": name,
            "root": root_path,
            "root_sha256": root_sha256,
            "file_count": file_count,
            "manifest_paths": list(manifest_paths),
        }
    return inventory


def _final_receipt_from_text(value: bytes, name: str) -> dict[str, str]:
    try:
        lines = value.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{name} is not valid UTF-8") from exc
    while lines and not lines[-1].strip():
        lines.pop()
    receipt: dict[str, str] = {}
    pattern = re.compile(r"^([a-z0-9_]+)=(.+)$")
    for line in reversed(lines):
        match = pattern.fullmatch(line)
        if match is None:
            break
        key, item = match.groups()
        if key in receipt:
            raise ValueError(f"{name} final receipt has a duplicate field: {key}")
        receipt[key] = item
    if not receipt:
        raise ValueError(f"{name} has no final authority receipt")
    return receipt


def _current_v24_receipt(value: bytes) -> dict[str, str]:
    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("current status is not valid UTF-8") from exc
    start_marker = "## Current V24 Status"
    end_marker = "## Current V23 Status"
    if text.count(start_marker) != 1 or text.count(end_marker) != 1:
        raise ValueError("current status v24 named-section markers mismatch")
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    if end <= start:
        raise ValueError("current status v24 named section is malformed")
    return _final_receipt_from_text(
        text[start:end].encode("utf-8"), "current status v24 section"
    )


def _verify_live_authority(
    camp_repo: Path,
    package_camp_head: str,
    *,
    review_root: Path,
    expected_review_root_sha256: str,
    expected_review_camp_head: str,
) -> dict[str, Any]:
    audit_path = camp_repo / AUDIT_RELATIVE_PATH
    status_path = camp_repo / CURRENT_STATUS_RELATIVE_PATH
    if (
        audit_path.is_symlink()
        or status_path.is_symlink()
        or not audit_path.is_file()
        or not status_path.is_file()
    ):
        raise ValueError("live v24 authority files are missing or symlinked")
    audit_bytes = audit_path.read_bytes()
    status_bytes = status_path.read_bytes()
    if (
        audit_bytes
        != _git_bytes(
            camp_repo, f"{package_camp_head}:{AUDIT_RELATIVE_PATH.as_posix()}"
        )
        or status_bytes
        != _git_bytes(
            camp_repo,
            f"{package_camp_head}:{CURRENT_STATUS_RELATIVE_PATH.as_posix()}",
        )
    ):
        raise ValueError("live v24 authority bytes differ from package CAMP HEAD")
    audit = _final_receipt_from_text(audit_bytes, "live v24 audit EOF")
    status = _current_v24_receipt(status_bytes)
    if audit != status:
        raise ValueError("audit EOF and current-status v24 receipts differ")
    if any(
        field not in audit
        for field in (*AUTHORITY_BINDING_FIELDS, *AUTHORITY_CONTROL_FIELDS)
    ):
        raise ValueError("live v24 authority binding field is missing")
    authority = dict(audit)
    if (
        authority["current_v24_status"] != AUTHORIZED_CURRENT_STATUS
        or authority["current_v24_final_synced_head"]
        != "pending_current_docs_commit_not_source_drift"
        or authority["next_work_target"] != AUTHORIZED_NEXT_WORK_TARGET
        or authority["fixed_dp_head"] != FIXED_DP_HEAD
        or authority["current_v24_holdout_open_count"] != "1"
        or authority["current_v24_holdout_rerun_authorized"] != "false"
        or authority["source_a_status"]
        != "source_ineligible_missing_authorized_build_prerequisites"
        or authority["source_a_terminal"] != "true"
        or authority["source_b_status"] != AUTHORIZED_SOURCE_B_STATUS
        or authority["source_b_terminal"] != "false"
        or authority["authorized_source_count"] != "2"
        or authority["source_terminal_count"] != "1"
        or authority["global_stop_authorized"] != "false"
        or authority["global_stop_reason"] != "none"
    ):
        raise ValueError("live v24 authority does not authorize this exact gate")
    static_source_head = _require_git_oid(
        authority["current_v24_artifact_source_head"],
        "authority static-preflight source head",
    )
    if (
        static_source_head == package_camp_head
        or _git_text(camp_repo, "cat-file", "-t", static_source_head) != "commit"
        or not _git_is_ancestor(camp_repo, static_source_head, package_camp_head)
    ):
        raise ValueError("static-preflight source is not a package HEAD ancestor")
    current_artifact = Path(authority["current_v24_artifact"])
    if (
        not current_artifact.is_absolute()
        or current_artifact.parent.resolve() != CANONICAL_OUTPUT_PARENT.resolve()
        or not current_artifact.name.startswith(STATIC_PREFLIGHT_NAME_PREFIX)
    ):
        raise ValueError("live v24 static-preflight artifact path mismatch")
    static_root_sha256 = _require_sha256(
        authority["current_v24_artifact_root_sha256"],
        "authority static-preflight root",
    )
    static_seal = verify_complete_seal(current_artifact, static_root_sha256)
    if (
        _read_verified_sealed_bytes(static_seal, "run.exit") != b"0\n"
        or _read_verified_sealed_bytes(static_seal, "stderr.txt") != b""
    ):
        raise ValueError("static-preflight artifact did not pass cleanly")
    authority_review_root = Path(
        authority["current_v24_reviewer_artifact"]
    )
    if (
        not authority_review_root.is_absolute()
        or authority_review_root.parent.resolve()
        != CANONICAL_OUTPUT_PARENT.resolve()
        or not authority_review_root.name.startswith(REVIEW_NAME_PREFIX)
        or authority_review_root.resolve() != Path(review_root).resolve()
        or authority["current_v24_reviewer_artifact_root_sha256"]
        != expected_review_root_sha256
        or authority["current_v24_reviewer_source_head"]
        != expected_review_camp_head
    ):
        raise ValueError("live v24 authority reviewer binding mismatch")
    _require_sha256(
        authority["current_v24_reviewer_artifact_root_sha256"],
        "authority reviewer root",
    )
    _require_git_oid(
        authority["current_v24_reviewer_source_head"],
        "authority reviewer source head",
    )
    _require_sha256(
        authority["current_v24_holdout_state_sha256"],
        "authority holdout-state",
    )
    state_path = Path(authority["current_v24_holdout_state"])
    if (
        not state_path.is_absolute()
        or state_path.resolve() != CANONICAL_HOLDOUT_STATE_PATH.resolve()
    ):
        raise ValueError("live v24 authority holdout-state path mismatch")
    return {
        "fields": authority,
        "audit_sha256": _sha256_bytes(audit_bytes),
        "current_status_sha256": _sha256_bytes(status_bytes),
        "audit_bytes": audit_bytes,
        "current_status_bytes": status_bytes,
        "static_preflight_seal": static_seal,
    }


def _verify_live_holdout_state(
    authority: Mapping[str, Any], review_state: Mapping[str, Any]
) -> dict[str, Any]:
    fields = _mapping(authority, "fields")
    state_path = Path(str(fields["current_v24_holdout_state"]))
    if state_path.is_symlink() or not state_path.is_file():
        raise ValueError("live holdout-once marker is missing or symlinked")
    value = state_path.read_bytes()
    expected_sha256 = str(fields["current_v24_holdout_state_sha256"])
    if _sha256_bytes(value) != expected_sha256:
        raise ValueError("live holdout-once marker SHA256 mismatch")
    state = _loads_json_bytes(value, "live holdout-once marker")
    if not isinstance(state, Mapping) or dict(state) != dict(review_state):
        raise ValueError("live holdout-once marker differs from reviewed state")
    if (
        state.get("schema") != "camp_dp_v24_holdout_once_state_v1"
        or state.get("holdout_opened") is not True
        or _exact_int(state.get("holdout_open_count"), "live holdout open count")
        != 1
        or state.get("rerun_authorized") is not False
    ):
        raise ValueError("live holdout-once marker contract mismatch")
    return {
        "path": state_path.as_posix(),
        "sha256": expected_sha256,
        "bytes": value,
        "open_count": 1,
        "rerun_authorized": False,
    }


def _active_v24_processes() -> list[int]:
    proc = Path("/proc")
    if not proc.is_dir():
        raise RuntimeError("/proc is required for fail-closed process inspection")
    current = os.getpid()
    active: list[int] = []
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == current:
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if any(token in command for token in FORBIDDEN_LIVE_PROCESS_TOKENS):
            active.append(int(entry.name))
    return sorted(active)


@contextlib.contextmanager
def _exclusive_global_lock(path: Path):
    path = Path(path)
    if path.resolve() != GLOBAL_LOCK_PATH.resolve():
        raise ValueError("global lock path is not canonical")
    if path.is_symlink() or not path.is_file():
        raise ValueError("existing global lock sentinel is missing or symlinked")
    try:
        import fcntl
    except ImportError as exc:  # pragma: no cover - AutoDL is Linux
        raise RuntimeError("fcntl is required for the v24 global lock") from exc
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("v24 global lock is already held") from exc
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _claim_gates(
    metrics: Mapping[str, Any], guards: Mapping[str, bool]
) -> dict[str, bool]:
    coverage = _mapping(metrics, "coverage")
    overall = _mapping(metrics, "safety_cost_delta")
    better_tie_worse = _mapping(overall, "better_tie_worse")
    regressions = _mapping(metrics, "additional_event_pairs")
    mean = _finite_number(overall.get("mean"), "SafetyCost mean delta")
    ci95_high = _finite_number(overall.get("ci95_high"), "SafetyCost CI95 upper")
    for name in ("better", "tie", "worse"):
        _exact_int(better_tie_worse.get(name), f"better/tie/worse {name}")
    for name in MAJOR_EVENT_FIELDS:
        _exact_int(regressions.get(name), f"additional event count {name}")
    gates = {
        "retention_rate": _finite_number(
            coverage.get("retention_rate"), "retention rate"
        )
        == 1.0,
        "paired_complete_rate": _finite_number(
            coverage.get("paired_complete_rate"), "paired complete rate"
        )
        == 1.0,
        "source_invalid_rate": _finite_number(
            coverage.get("source_invalid_rate"), "source invalid rate"
        )
        == 0.0,
        "execution_invalid_rate": _finite_number(
            coverage.get("execution_invalid_rate"), "execution invalid rate"
        )
        == 0.0,
        "safety_cost_mean_delta_below_zero": mean < 0.0,
        "clustered_ci95_upper_below_zero": ci95_high < 0.0,
        "better_exceeds_worse": better_tie_worse["better"]
        > better_tie_worse["worse"],
        "no_additional_collision_pairs": regressions["collision_any"] == 0,
        "no_additional_offroad_pairs": regressions["offroad_rate"] == 0,
        "no_additional_red_light_pairs": regressions["red_light_violation_any"]
        == 0,
        "no_additional_wrong_way_pairs": regressions["wrong_way_rate"] == 0,
        "evidence_guards": all(guards.values()),
    }
    if tuple(gates) != CLAIM_GATE_NAMES:
        raise AssertionError("internal claim gate order drift")
    return gates


def evaluate_claim_gates(metrics: Mapping[str, Any]) -> dict[str, Any]:
    source_guards = _mapping(metrics, "evidence_guards")
    if set(source_guards) != set(EVIDENCE_GUARD_NAMES):
        raise ValueError("source evidence guard set mismatch")
    if source_guards.get("independent_review_passed") is not False:
        raise ValueError("source reviewer must retain its false self-guard")
    if any(
        source_guards.get(name) is not True
        for name in EVIDENCE_GUARD_NAMES
        if name != "independent_review_passed"
    ):
        raise ValueError("a non-self source evidence guard did not pass")
    derived_guards = dict(source_guards)
    derived_guards["independent_review_passed"] = True
    gates = _claim_gates(metrics, derived_guards)
    failed = [name for name in CLAIM_GATE_NAMES if not gates[name]]
    decision = "limited_claim_gates_passed" if not failed else "honest_no_claim"
    return {
        "schema": CLAIM_SCHEMA,
        "decision": decision,
        "final_claim_authorized": not failed,
        "derived_evidence_guards": derived_guards,
        "gates": gates,
        "failed_gates": failed,
        "claim_scope": "frozen_held_out_map_family_and_three_corridor_groups_only",
        "map_family_level_ci": False,
        "unseen_map_generalization": False,
        "native_ranked_k8_superiority": False,
        "latency_comparative_conclusion": False,
        "allowed_claim_text": ALLOWED_CLAIM_TEXT,
        "forbidden_claims": list(FORBIDDEN_CLAIMS),
    }


def _validate_paired_summary(
    value: Any, *, name: str, pair_count: int
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    _exact_int(value.get("pair_count"), f"{name} pair count", pair_count)
    for field in ("mean", "median", "ci95_low", "ci95_high"):
        _finite_number(value.get(field), f"{name} {field}")
    counts = _mapping(value, "better_tie_worse")
    if set(counts) != {"better", "tie", "worse"}:
        raise ValueError(f"{name} better/tie/worse key set mismatch")
    total = sum(
        _exact_int(counts.get(field), f"{name} {field}")
        for field in ("better", "tie", "worse")
    )
    descriptive = value.get("descriptive_unclassified_count", 0)
    if "descriptive_unclassified_count" in value:
        descriptive = _exact_int(descriptive, f"{name} descriptive count")
    if total + descriptive != pair_count:
        raise ValueError(f"{name} better/tie/worse denominator mismatch")
    return value


def _validate_full_metric_scope(metrics: Mapping[str, Any]) -> None:
    if set(metrics) != METRICS_TOP_LEVEL_NAMES:
        raise ValueError("review metrics top-level key set mismatch")
    overall = _validate_paired_summary(
        metrics.get("safety_cost_delta"),
        name="SafetyCost delta",
        pair_count=120,
    )
    strata = _mapping(metrics, "strata")
    if set(strata) != {"overall", "all_k_high_risk"}:
        raise ValueError("review strata key set mismatch")
    if strata.get("overall") != overall:
        raise ValueError("overall stratum differs from SafetyCost delta")
    _validate_paired_summary(
        strata.get("all_k_high_risk"),
        name="all-K-high-risk SafetyCost delta",
        pair_count=8,
    )
    for field, expected in (
        ("components", SAFETY_COMPONENT_NAMES),
        ("speed_sensitivity", SPEED_SENSITIVITY_NAMES),
        ("secondary", SECONDARY_NAMES),
    ):
        values = _mapping(metrics, field)
        if set(values) != expected:
            raise ValueError(f"review {field} key set mismatch")
        for name, summary in values.items():
            _validate_paired_summary(
                summary,
                name=f"{field} {name}",
                pair_count=120,
            )
            if field == "secondary":
                expected_direction = SECONDARY_DIRECTIONS[name]
                if expected_direction == "lower_is_better":
                    if (
                        "direction" in summary
                        or "descriptive_unclassified_count" in summary
                    ):
                        raise ValueError(
                            f"review secondary {name} direction mismatch"
                        )
                elif (
                    summary.get("direction") != expected_direction
                    or type(summary.get("descriptive_unclassified_count"))
                    is not int
                ):
                    raise ValueError(
                        f"review secondary {name} direction mismatch"
                    )

    failure = _mapping(metrics, "failure_accounting")
    if (
        failure.get("dp_status") != {"ok": 120}
        or failure.get("camp_status") != {"ok": 120}
        or failure.get("failure_class") != {"None": 120}
        or failure.get("failed_pairs_dropped") is not False
        or failure.get("replacement_or_resampling_used") is not False
    ):
        raise ValueError("review full failure accounting mismatch")

    selection = _mapping(metrics, "candidate_selection")
    histogram = _mapping(selection, "camp_selected_index_histogram")
    if set(histogram) != {str(index) for index in range(8)}:
        raise ValueError("review selected-index histogram key set mismatch")
    histogram_counts = {
        key: _exact_int(value, f"selected-index histogram {key}")
        for key, value in histogram.items()
    }
    if (
        sum(histogram_counts.values()) != 7680
        or histogram_counts["0"] != 1401
    ):
        raise ValueError("review selected-index histogram mismatch")

    latency = _mapping(metrics, "latency")
    if set(latency) != set(LATENCY_STAGE_NAMES):
        raise ValueError("review latency arm set mismatch")
    for arm, expected_stages in LATENCY_STAGE_NAMES.items():
        stages = _mapping(latency, arm)
        if set(stages) != expected_stages:
            raise ValueError(f"review {arm} latency stage set mismatch")
        for stage, distribution in stages.items():
            if not isinstance(distribution, Mapping) or set(distribution) != {
                "count",
                "mean",
                "median",
                "p95",
                "p99",
                "max",
            }:
                raise ValueError(f"review {arm}/{stage} latency shape mismatch")
            _exact_int(
                distribution.get("count"),
                f"review {arm}/{stage} latency count",
                7680,
            )
            for field in ("mean", "median", "p95", "p99", "max"):
                _finite_number(
                    distribution.get(field),
                    f"review {arm}/{stage} latency {field}",
                )


def _validate_fixed_review_metrics(metrics: Mapping[str, Any]) -> None:
    _validate_full_metric_scope(metrics)
    if metrics.get("schema") != "camp_dp_v24_holdout_main_independent_statistics_v1":
        raise ValueError("review metrics schema mismatch")
    bootstrap = _mapping(metrics, "bootstrap_contract")
    if bootstrap != {
        "primary_hierarchy": [
            "corridor_group_sha256",
            "route_identity_sha256",
            "seed",
        ],
        "map_family_cluster_level_authorized": False,
        "resamples": 5000,
        "seed": 24047,
    }:
        raise ValueError("review bootstrap contract mismatch")
    coverage = _mapping(metrics, "coverage")
    exact_coverage = {
        "planned_pair_count": 120,
        "retained_pair_count": 120,
        "paired_complete_count": 120,
        "source_invalid_pair_count": 0,
        "execution_invalid_pair_count": 0,
    }
    for name, expected in exact_coverage.items():
        _exact_int(coverage.get(name), f"coverage {name}", expected)
    for name, expected in {
        "retention_rate": 1.0,
        "paired_complete_rate": 1.0,
        "source_invalid_rate": 0.0,
        "execution_invalid_rate": 0.0,
    }.items():
        if _finite_number(coverage.get(name), f"coverage {name}") != expected:
            raise ValueError(f"coverage {name} mismatch")
    failure = _mapping(metrics, "failure_accounting")
    if (
        failure.get("failed_pairs_dropped") is not False
        or failure.get("replacement_or_resampling_used") is not False
    ):
        raise ValueError("review failure-retention contract mismatch")
    overall = _mapping(metrics, "safety_cost_delta")
    if (
        _finite_number(overall.get("mean"), "SafetyCost mean")
        != EXPECTED_MEAN_DELTA
        or _finite_number(overall.get("median"), "SafetyCost median") != 0.0
        or _finite_number(overall.get("ci95_low"), "SafetyCost CI95 lower")
        != EXPECTED_CI95_LOW
        or _finite_number(overall.get("ci95_high"), "SafetyCost CI95 upper")
        != EXPECTED_CI95_HIGH
        or dict(_mapping(overall, "better_tie_worse"))
        != EXPECTED_BETTER_TIE_WORSE
    ):
        raise ValueError("review SafetyCost result mismatch")
    regressions = _mapping(metrics, "additional_event_pairs")
    if set(regressions) != set(MAJOR_EVENT_FIELDS) or any(
        type(regressions[name]) is not int or regressions[name] != 0
        for name in MAJOR_EVENT_FIELDS
    ):
        raise ValueError("review major-event regression result mismatch")
    if (
        metrics.get("latency_comparison_authorized") is not False
        or metrics.get("latency_reporting_role")
        != "descriptive_instrumented_only"
    ):
        raise ValueError("review latency scope mismatch")
    selection = _mapping(metrics, "candidate_selection")
    for name, expected in {
        "camp_tick_count": 7680,
        "candidate0_selection_count": 1401,
        "non_candidate0_selection_count": 6279,
        "all_k_high_risk_pair_count": 8,
        "all_k_high_risk_tick_count": 36,
    }.items():
        _exact_int(selection.get(name), f"candidate selection {name}", expected)


def _verify_review_contract(
    root: Path,
    expected_root_sha256: str,
    *,
    expected_review_camp_head: str,
    expected_execution_source_head: str,
    expected_config_sha256: str,
    expected_evaluator_sha256: str,
) -> dict[str, Any]:
    seal = verify_complete_seal(
        root,
        expected_root_sha256,
        exact_manifest_paths=EXPECTED_REVIEW_MANIFEST_PATHS,
    )
    root = Path(seal["root"])
    if _read_verified_sealed_bytes(seal, "run.exit") != b"0\n":
        raise ValueError("review run.exit did not pass")
    if _read_verified_sealed_bytes(seal, "stderr.txt") != b"":
        raise ValueError("review stderr is not empty")
    review = _loads_json_bytes(
        _read_verified_sealed_bytes(seal, "review_result.json"),
        "sealed review_result.json",
    )
    metrics = _loads_json_bytes(
        _read_verified_sealed_bytes(seal, "recomputed_metrics.json"),
        "sealed recomputed_metrics.json",
    )
    schedule = _loads_json_bytes(
        _read_verified_sealed_bytes(seal, "schedule_receipt.json"),
        "sealed schedule_receipt.json",
    )
    provenance = _loads_json_bytes(
        _read_verified_sealed_bytes(seal, "provenance.json"),
        "sealed provenance.json",
    )
    if not all(
        isinstance(value, Mapping)
        for value in (review, metrics, schedule, provenance)
    ):
        raise ValueError("review JSON roots must be mappings")
    checks = review.get("checks")
    if (
        review.get("schema") != REVIEW_SCHEMA
        or review.get("status") != "passed"
        or type(review.get("check_count")) is not int
        or review.get("check_count") != EXPECTED_REVIEW_CHECK_COUNT
        or type(review.get("failed_count")) is not int
        or review.get("failed_count") != 0
        or review.get("failed_checks") != []
        or not isinstance(checks, Mapping)
        or set(checks) != EXPECTED_REVIEW_CHECK_NAMES
        or any(value is not True for value in checks.values())
    ):
        raise ValueError("review status/check contract did not pass")
    if review.get("metrics") != metrics:
        raise ValueError("embedded and standalone review metrics differ")
    if review.get("schedule") != schedule:
        raise ValueError("embedded and standalone review schedules differ")
    if review.get("provenance") != provenance:
        raise ValueError("embedded and standalone review provenance differ")

    expected_review_camp_head = _require_git_oid(
        expected_review_camp_head, "expected review CAMP head"
    )
    expected_execution_source_head = _require_git_oid(
        expected_execution_source_head, "expected execution source head"
    )
    expected_config_sha256 = _require_sha256(
        expected_config_sha256, "expected config"
    )
    expected_evaluator_sha256 = _require_sha256(
        expected_evaluator_sha256, "expected evaluator"
    )
    heads = _parse_heads_bytes(_read_verified_sealed_bytes(seal, "HEADS.txt"))
    if (
        review.get("camp_head") != expected_review_camp_head
        or heads["CAMP_HEAD"] != expected_review_camp_head
        or review.get("execution_source_head") != expected_execution_source_head
        or heads["EXECUTION_SOURCE_HEAD"] != expected_execution_source_head
        or review.get("fixed_dp_head") != FIXED_DP_HEAD
        or heads["FIXED_DP_HEAD"] != FIXED_DP_HEAD
    ):
        raise ValueError("review HEAD provenance mismatch")
    if (
        provenance.get("live_camp_head") != expected_review_camp_head
        or provenance.get("execution_source_head")
        != expected_execution_source_head
        or provenance.get("fixed_dp_head") != FIXED_DP_HEAD
        or provenance.get("live_camp_tracked_clean") is not True
        or provenance.get("fixed_dp_tracked_clean") is not True
        or provenance.get("config_blob_sha256") != expected_config_sha256
        or provenance.get("expected_config_sha256") != expected_config_sha256
        or provenance.get("evaluator_blob_sha256") != expected_evaluator_sha256
        or provenance.get("expected_evaluator_sha256")
        != expected_evaluator_sha256
    ):
        raise ValueError("review source-blob provenance mismatch")

    handoff = _mapping(review, "claim_guard_handoff")
    if handoff != {
        "independent_review_passed": False,
        "status": "pending_separate_claim_decision_rehash_of_sealed_reviewer_root",
        "reviewer_self_authorization_forbidden": True,
    }:
        raise ValueError("review claim-guard handoff mismatch")
    _validate_fixed_review_metrics(metrics)
    derived_claim = evaluate_claim_gates(metrics)
    source_claim = _mapping(metrics, "claim_gate_result")
    source_gates = _claim_gates(metrics, _mapping(metrics, "evidence_guards"))
    source_failed = [name for name in CLAIM_GATE_NAMES if not source_gates[name]]
    if (
        source_claim.get("decision") != EXPECTED_DECISION
        or source_claim.get("final_claim_authorized") is not False
        or source_claim.get("gates") != source_gates
        or source_claim.get("failed_gates") != source_failed
        or source_claim.get("claim_scope")
        != "frozen_held_out_map_family_and_three_corridor_groups_only"
        or source_claim.get("map_family_level_ci") is not False
        or source_claim.get("unseen_map_generalization") is not False
        or source_claim.get("native_ranked_k8_superiority") is not False
        or source_claim.get("latency_comparative_conclusion") is not False
        or source_failed
        != ["clustered_ci95_upper_below_zero", "evidence_guards"]
        or derived_claim["decision"] != EXPECTED_DECISION
        or derived_claim["final_claim_authorized"] is not False
        or derived_claim["failed_gates"]
        != ["clustered_ci95_upper_below_zero"]
    ):
        raise ValueError("review preregistered claim-gate result mismatch")
    if (
        review.get("final_claim_authorized") is not False
        or review.get("latency_comparison_authorized") is not False
        or review.get("map_family_level_ci_authorized") is not False
        or review.get("unseen_map_generalization_authorized") is not False
        or review.get("native_ranked_k8_claim_authorized") is not False
        or review.get("holdout_reopened") is not False
        or review.get("holdout_open_count") != 1
        or review.get("source_execution_reexecuted") is not False
        or review.get("runner_built") is not False
        or review.get("model_loaded") is not False
        or review.get("simulator_executed") is not False
    ):
        raise ValueError("review claim/holdout scope mismatch")
    holdout_state = _mapping(review, "holdout_state")
    if (
        holdout_state.get("holdout_opened") is not True
        or type(holdout_state.get("holdout_open_count")) is not int
        or holdout_state.get("holdout_open_count") != 1
        or holdout_state.get("rerun_authorized") is not False
    ):
        raise ValueError("review holdout-once state mismatch")
    limitations = _mapping(review, "evidence_limitations")
    expected_limitations = {
        "raw_candidate_tensor_bytes_present": False,
        "raw_atom_matrix_bytes_present": False,
        "affine_score_receipt_consistency_verified": True,
        "affine_scores_recomputed_from_raw_atoms": False,
        "candidate_hashes_recomputed_from_raw_tensor_bytes": False,
        "candidate_and_atom_hash_scope": "complete_sealed_receipt_consistency_only",
        "raw_byte_proof_claimed": False,
    }
    if dict(limitations) != expected_limitations:
        raise ValueError("review raw-byte evidence limitation mismatch")
    execution = _mapping(review, "execution")
    for name, expected in {
        "planned_pair_count": 120,
        "retained_pair_count": 120,
        "paired_complete_count": 120,
        "source_invalid_pair_count": 0,
        "execution_failure_pair_count": 0,
        "dp_tick_count": 7680,
        "camp_tick_count": 7680,
        "all_k_high_risk_tick_count": 36,
    }.items():
        _exact_int(execution.get(name), f"review execution {name}", expected)
    if (
        schedule.get("pair_count") != 120
        or schedule.get("unique_pair_count") != 120
        or schedule.get("route_count") != 24
        or schedule.get("seed_count_per_route") != 5
        or schedule.get("seeds") != [24201, 24202, 24203, 24204, 24205]
        or schedule.get("map_family_count") != 1
        or schedule.get("corridor_group_count") != 3
        or schedule.get("arm_order_counts")
        != {"dp_camp": 60, "camp_dp": 60}
        or schedule.get("arm_order_domain_separator")
        != "camp-v24-paired-arm-order-v1"
        or schedule.get("deterministic_hash_rank_verified") is not True
        or schedule.get("outcome_blind_preregistered_order_control_verified")
        is not True
        or schedule.get("independent_reset_per_arm_verified") is not True
        or schedule.get("latency_comparative_conclusion_authorized") is not False
    ):
        raise ValueError("review schedule receipt mismatch")
    frozen = _mapping(review, "frozen_metric_contract")
    if (
        frozen.get("train_route_seed_source_coverage_disclosure")
        != EXPECTED_TRAIN_SOURCE_COVERAGE
        or frozen.get("learning_curve_stability")
        != EXPECTED_LEARNING_CURVE_STABILITY
        or frozen.get("distribution_concentration_risk_disclosed") is not True
        or frozen.get("calibration_or_holdout_repair_authorized") is not False
    ):
        raise ValueError("review frozen training-risk disclosure mismatch")
    inventory = _validate_source_root_inventory(review.get("source_roots"))
    return {
        "seal": seal,
        "review": review,
        "metrics": metrics,
        "derived_claim": derived_claim,
        "source_root_inventory": inventory,
        "heads": heads,
    }


def _git_text(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_bytes(repo: Path, object_name: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), "show", object_name],
        check=True,
        capture_output=True,
    ).stdout


def _git_is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            ],
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _verify_live_repositories(
    camp_repo: Path,
    package_camp_head: str,
    dp_repo: Path,
    *,
    expected_review_camp_head: str,
    expected_execution_source_head: str,
) -> dict[str, Any]:
    package_camp_head = _require_git_oid(package_camp_head, "package CAMP head")
    camp_repo = Path(camp_repo).resolve()
    dp_repo = Path(dp_repo).resolve()
    if camp_repo != CANONICAL_CAMP_REPO.resolve():
        raise ValueError("CAMP repo path is not canonical")
    if dp_repo != CANONICAL_DP_REPO.resolve():
        raise ValueError("fixed DP repo path is not canonical")
    if Path(_git_text(camp_repo, "rev-parse", "--show-toplevel")).resolve() != camp_repo:
        raise ValueError("CAMP repo is not its canonical Git top-level")
    if Path(_git_text(dp_repo, "rev-parse", "--show-toplevel")).resolve() != dp_repo:
        raise ValueError("fixed DP repo is not its canonical Git top-level")
    camp_head = _git_text(camp_repo, "rev-parse", "HEAD")
    origin_main = _git_text(camp_repo, "rev-parse", "origin/main")
    branch = _git_text(camp_repo, "symbolic-ref", "--short", "HEAD")
    origin_url = _git_text(camp_repo, "remote", "get-url", "origin")
    remote_main_receipt = _git_text(
        camp_repo, "ls-remote", "origin", "refs/heads/main"
    )
    camp_status = _git_text(
        camp_repo, "status", "--porcelain", "--untracked-files=no"
    )
    dp_head = _git_text(dp_repo, "rev-parse", "HEAD")
    dp_status = _git_text(
        dp_repo, "status", "--porcelain", "--untracked-files=no"
    )
    if (
        camp_head != package_camp_head
        or origin_main != package_camp_head
        or branch != "main"
        or origin_url != CANONICAL_ORIGIN_URL
        or remote_main_receipt != f"{package_camp_head}\trefs/heads/main"
        or camp_status
    ):
        raise ValueError("live CAMP branch/origin/remote/tracked state mismatch")
    if dp_head != FIXED_DP_HEAD or dp_status:
        raise ValueError("fixed DP HEAD or tracked state mismatch")
    for head, label in (
        (expected_review_camp_head, "review CAMP head"),
        (expected_execution_source_head, "execution source head"),
    ):
        if _git_text(camp_repo, "cat-file", "-t", head) != "commit":
            raise ValueError(f"{label} is not a commit")
    if (
        not _git_is_ancestor(camp_repo, expected_review_camp_head, package_camp_head)
        or not _git_is_ancestor(
            camp_repo, expected_execution_source_head, expected_review_camp_head
        )
    ):
        raise ValueError("review/execution/package CAMP ancestry mismatch")
    return {
        "package_camp_head": camp_head,
        "camp_origin_main": origin_main,
        "camp_remote_main": package_camp_head,
        "camp_branch": branch,
        "camp_origin_url": origin_url,
        "review_camp_head_is_ancestor": True,
        "execution_source_is_review_ancestor": True,
        "camp_tracked_clean": True,
        "fixed_dp_head": dp_head,
        "fixed_dp_tracked_clean": True,
    }


def _verify_output_isolation(
    output: Path,
    staging: Path,
    *,
    review_root: Path,
    camp_repo: Path,
    dp_repo: Path,
    holdout_state_path: Path,
) -> None:
    if not output.is_absolute() or not staging.is_absolute():
        raise ValueError("output and staging paths must be absolute")
    if output.parent.resolve() != CANONICAL_OUTPUT_PARENT.resolve():
        raise ValueError("output must be a direct child of the canonical artifact root")
    if not output.name.startswith(OUTPUT_NAME_PREFIX):
        raise ValueError("output artifact name prefix mismatch")
    resolved = [
        output.resolve(),
        staging.resolve(),
        Path(review_root).resolve(),
        Path(camp_repo).resolve(),
        Path(dp_repo).resolve(),
        Path(holdout_state_path).resolve(),
    ]
    output_resolved, staging_resolved, *protected = resolved
    if output_resolved == staging_resolved:
        raise ValueError("output and staging paths collide")
    for candidate in (output_resolved, staging_resolved):
        for boundary in protected:
            if (
                candidate == boundary
                or boundary in candidate.parents
                or candidate in boundary.parents
            ):
                raise ValueError("output/staging path is not isolated")


def _expected_output_path(
    package_camp_head: str, review_root_sha256: str
) -> Path:
    package_camp_head = _require_git_oid(package_camp_head, "package CAMP head")
    review_root_sha256 = _require_sha256(
        review_root_sha256, "expected review root"
    )
    return CANONICAL_OUTPUT_PARENT / (
        f"{OUTPUT_NAME_PREFIX}{package_camp_head}_{review_root_sha256}"
    )


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root: Path) -> None:
    root = Path(root)
    directories = [root]
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("staging artifact contains a symlink")
        if path.is_dir():
            directories.append(path)
        elif path.is_file():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
    for directory in reversed(directories):
        _fsync_directory(directory)


def _rename_noreplace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise RuntimeError("renameat2(RENAME_NOREPLACE) is required")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        -100,
        os.fsencode(source),
        -100,
        os.fsencode(destination),
        1,
    )
    if result == 0:
        return
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        raise FileExistsError(destination)
    raise OSError(error, os.strerror(error), destination)


def _build_evidence_claim_locked(
    *,
    review_root: Path,
    expected_review_root_sha256: str,
    expected_review_camp_head: str,
    expected_execution_source_head: str,
    expected_config_sha256: str,
    expected_evaluator_sha256: str,
    camp_repo: Path,
    package_camp_head: str,
    dp_repo: Path,
    output_dir: Path,
    enable_evidence_claim: bool,
    command: Sequence[str] | None = None,
    minimum_free_bytes: int = MINIMUM_FREE_BYTES,
) -> dict[str, Any]:
    if enable_evidence_claim is not True:
        raise ValueError("explicit --enable-evidence-claim is required")
    expected_review_root_sha256 = _require_sha256(
        expected_review_root_sha256, "expected review root"
    )
    expected_review_camp_head = _require_git_oid(
        expected_review_camp_head, "expected review CAMP head"
    )
    expected_execution_source_head = _require_git_oid(
        expected_execution_source_head, "expected execution source head"
    )
    expected_config_sha256 = _require_sha256(
        expected_config_sha256, "expected config"
    )
    expected_evaluator_sha256 = _require_sha256(
        expected_evaluator_sha256, "expected evaluator"
    )
    output = Path(output_dir)
    staging = output.with_name(output.name + ".tmp")
    expected_output = _expected_output_path(
        package_camp_head, expected_review_root_sha256
    )
    if output.resolve() != expected_output.resolve():
        raise ValueError("output path is not the deterministic gate path")
    if output.exists() or staging.exists():
        raise FileExistsError(output if output.exists() else staging)
    if output.parent.is_symlink() or not output.parent.is_dir():
        raise ValueError("output parent directory is missing")
    review_resolved = Path(review_root).resolve()
    _verify_output_isolation(
        output,
        staging,
        review_root=review_resolved,
        camp_repo=Path(camp_repo),
        dp_repo=Path(dp_repo),
        holdout_state_path=CANONICAL_HOLDOUT_STATE_PATH,
    )
    if type(minimum_free_bytes) is not int or minimum_free_bytes < 0:
        raise ValueError("minimum free bytes must be a nonnegative integer")

    repository_receipt = _verify_live_repositories(
        Path(camp_repo),
        package_camp_head,
        Path(dp_repo),
        expected_review_camp_head=expected_review_camp_head,
        expected_execution_source_head=expected_execution_source_head,
    )
    authority_before = _verify_live_authority(
        Path(camp_repo).resolve(),
        package_camp_head,
        review_root=review_resolved,
        expected_review_root_sha256=expected_review_root_sha256,
        expected_review_camp_head=expected_review_camp_head,
    )
    authority_fields = _mapping(authority_before, "fields")
    repository_receipt = {
        **repository_receipt,
        "static_preflight_source_head": authority_fields[
            "current_v24_artifact_source_head"
        ],
        "static_preflight_source_is_package_ancestor": True,
    }
    verified = _verify_review_contract(
        review_resolved,
        expected_review_root_sha256,
        expected_review_camp_head=expected_review_camp_head,
        expected_execution_source_head=expected_execution_source_head,
        expected_config_sha256=expected_config_sha256,
        expected_evaluator_sha256=expected_evaluator_sha256,
    )
    holdout_state_before = _verify_live_holdout_state(
        authority_before,
        _mapping(verified["review"], "holdout_state"),
    )
    active_processes = _active_v24_processes()
    if active_processes:
        raise ValueError("a v24 evaluator/reviewer process is still active")
    free_bytes = shutil.disk_usage(output.parent).free
    if free_bytes <= minimum_free_bytes:
        raise ValueError("evidence/claim gate violates the 10 GiB disk floor")

    before_seal = verified["seal"]
    derived_claim = verified["derived_claim"]
    source_guards = dict(_mapping(verified["metrics"], "evidence_guards"))
    guard_receipt = {
        "source_reviewer_root_sha256": expected_review_root_sha256,
        "source_self_guard": source_guards["independent_review_passed"],
        "derived_independent_review_passed": True,
        "authority": "external_complete_seal_rehash_of_reviewer_root",
        "source_reviewer_json_modified": False,
        "only_guard_changed": "independent_review_passed",
    }
    if derived_claim["decision"] != EXPECTED_DECISION:
        raise ValueError("fixed reviewer root did not produce expected honest no-claim")

    staging.mkdir()
    published = False
    try:
        claim_decision = {
            **derived_claim,
            "status": "passed_honest_no_claim",
            "source_reviewer_root_sha256": expected_review_root_sha256,
            "guard_closure": guard_receipt,
            "directional_safety_cost_summary": {
                "mean_delta": EXPECTED_MEAN_DELTA,
                "ci95": [EXPECTED_CI95_LOW, EXPECTED_CI95_HIGH],
                "better_tie_worse": EXPECTED_BETTER_TIE_WORSE,
                "additional_major_event_pairs": {
                    name: 0 for name in MAJOR_EVENT_FIELDS
                },
            },
        }
        _write_json(staging / "claim_decision.json", claim_decision)

        evidence_package = {
            "schema": PACKAGE_SCHEMA,
            "status": "passed",
            "reviewer_root": {
                "path": review_resolved.as_posix(),
                "root_sha256": expected_review_root_sha256,
                "file_count": before_seal["file_count"],
                "manifest_digests": before_seal["manifest_digests"],
                "review_result_sha256": before_seal["manifest_digests"][
                    "review_result.json"
                ],
                "recomputed_metrics_sha256": before_seal["manifest_digests"][
                    "recomputed_metrics.json"
                ],
                "complete_seal_rehashed_before_and_after": True,
                "source_bytes_unchanged": True,
            },
            "guard_closure": guard_receipt,
            "live_authority": {
                "fields": dict(_mapping(authority_before, "fields")),
                "audit_sha256": authority_before["audit_sha256"],
                "current_status_sha256": authority_before[
                    "current_status_sha256"
                ],
                "verified_before_and_after": True,
                "static_preflight": {
                    "source_head": authority_fields[
                        "current_v24_artifact_source_head"
                    ],
                    "path": authority_fields["current_v24_artifact"],
                    "root_sha256": authority_fields[
                        "current_v24_artifact_root_sha256"
                    ],
                    "file_count": authority_before[
                        "static_preflight_seal"
                    ]["file_count"],
                    "manifest_digests": authority_before[
                        "static_preflight_seal"
                    ]["manifest_digests"],
                },
            },
            "live_holdout_once": {
                "path": holdout_state_before["path"],
                "sha256": holdout_state_before["sha256"],
                "open_count": 1,
                "rerun_authorized": False,
                "marker_bytes_unchanged_before_and_after": True,
                "global_lock_exclusively_held_by_this_gate": True,
                "active_evaluator_or_reviewer_process_count": 0,
            },
            "source_root_inventory": verified["source_root_inventory"],
            "transitive_source_roots_rehashed_by_this_gate": False,
            "transitive_source_roots_role": (
                "inventory_from_complete_sealed_independent_reviewer"
            ),
            "repository_provenance": repository_receipt,
            "reviewer_camp_head": expected_review_camp_head,
            "execution_source_head": expected_execution_source_head,
            "fixed_dp_head": FIXED_DP_HEAD,
            "config_sha256": expected_config_sha256,
            "evaluator_sha256": expected_evaluator_sha256,
            "evidence_limitations": dict(
                _mapping(verified["review"], "evidence_limitations")
            ),
            "reviewed_metrics": verified["metrics"],
            "frozen_training_risk_disclosure": dict(
                _mapping(verified["review"], "frozen_metric_contract")
            ),
            "evaluation_summary": {
                "planned_pair_count": 120,
                "retained_pair_count": 120,
                "paired_complete_count": 120,
                "source_invalid_pair_count": 0,
                "execution_failure_pair_count": 0,
                "dp_tick_count": 7680,
                "camp_tick_count": 7680,
                "candidate0_selection_count": 1401,
                "non_candidate0_selection_count": 6279,
                "all_k_high_risk_pair_count": 8,
                "all_k_high_risk_tick_count": 36,
                "map_family_count": 1,
                "corridor_group_count": 3,
            },
            "claim_decision": {
                "decision": claim_decision["decision"],
                "final_claim_authorized": claim_decision[
                    "final_claim_authorized"
                ],
                "failed_gates": claim_decision["failed_gates"],
            },
            "latency_comparison_authorized": False,
            "latency_reporting_role": "descriptive_instrumented_only",
            "reviewer_or_execution_rerun": False,
            "runner_built": False,
            "model_loaded": False,
            "simulator_executed": False,
            "holdout_reopened": False,
            "promotion_authorized": False,
            "deployment_authorized": False,
            "online_activation_authorized": False,
            "free_bytes_before_package": free_bytes,
            "final_post_publication_checks_required": True,
            "free_bytes_after_gate_recorded_in_return_and_launch_receipt": True,
            "next_work_target": "v24_honest_no_claim_record_only_closeout",
        }
        _write_json(staging / "evidence_package.json", evidence_package)
        (staging / "summary.md").write_text(
            "# v24 evidence package and preregistered claim decision\n\n"
            "- Evidence-package status: `passed`\n"
            f"- Reviewer root rehashed: `{expected_review_root_sha256}`\n"
            "- Derived independent-review guard: `true` (source remains `false`)\n"
            f"- SafetyCost mean delta: `{EXPECTED_MEAN_DELTA}`\n"
            f"- Clustered CI95: `[{EXPECTED_CI95_LOW}, {EXPECTED_CI95_HIGH}]`\n"
            "- Better / tie / worse: `4 / 113 / 3`\n"
            "- Claim decision: `honest_no_claim`\n"
            "- Failed gate: `clustered_ci95_upper_below_zero`\n"
            "- Latency remains descriptive-only; promotion/deployment are forbidden.\n",
            encoding="utf-8",
        )
        (staging / "HEADS.txt").write_text(
            f"PACKAGE_CAMP_HEAD={repository_receipt['package_camp_head']}\n"
            f"REVIEWER_CAMP_HEAD={expected_review_camp_head}\n"
            f"EXECUTION_SOURCE_HEAD={expected_execution_source_head}\n"
            f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
            f"REVIEWER_ROOT_SHA256={expected_review_root_sha256}\n"
            f"CONFIG_SHA256={expected_config_sha256}\n"
            f"EVALUATOR_SHA256={expected_evaluator_sha256}\n",
            encoding="ascii",
        )
        rendered_command = list(command) if command is not None else list(sys.argv)
        (staging / "COMMAND.txt").write_text(
            " ".join(str(item) for item in rendered_command) + "\n",
            encoding="utf-8",
        )
        stdout = {
            "status": "passed",
            "decision": EXPECTED_DECISION,
            "final_claim_authorized": False,
            "failed_gates": ["clustered_ci95_upper_below_zero"],
            "next_work_target": "v24_honest_no_claim_record_only_closeout",
        }
        _write_json(staging / "stdout.txt", stdout)
        (staging / "stderr.txt").write_text("", encoding="utf-8")
        (staging / "run.exit").write_text("0\n", encoding="ascii")
        repository_after = _verify_live_repositories(
            Path(camp_repo),
            package_camp_head,
            Path(dp_repo),
            expected_review_camp_head=expected_review_camp_head,
            expected_execution_source_head=expected_execution_source_head,
        )
        repository_after = {
            **repository_after,
            "static_preflight_source_head": authority_fields[
                "current_v24_artifact_source_head"
            ],
            "static_preflight_source_is_package_ancestor": True,
        }
        if repository_after != repository_receipt:
            raise ValueError("live repository provenance changed during packaging")
        authority_after = _verify_live_authority(
            Path(camp_repo).resolve(),
            package_camp_head,
            review_root=review_resolved,
            expected_review_root_sha256=expected_review_root_sha256,
            expected_review_camp_head=expected_review_camp_head,
        )
        if (
            authority_after["audit_bytes"] != authority_before["audit_bytes"]
            or authority_after["current_status_bytes"]
            != authority_before["current_status_bytes"]
            or authority_after["fields"] != authority_before["fields"]
            or authority_after["static_preflight_seal"]["manifest_digests"]
            != authority_before["static_preflight_seal"]["manifest_digests"]
        ):
            raise ValueError("live v24 authority changed during packaging")
        holdout_state_after = _verify_live_holdout_state(
            authority_after,
            _mapping(verified["review"], "holdout_state"),
        )
        if holdout_state_after["bytes"] != holdout_state_before["bytes"]:
            raise ValueError("live holdout-once marker changed during packaging")
        if _active_v24_processes():
            raise ValueError("a v24 evaluator/reviewer process started during packaging")
        after_seal = verify_complete_seal(
            review_resolved,
            expected_review_root_sha256,
            exact_manifest_paths=EXPECTED_REVIEW_MANIFEST_PATHS,
        )
        if (
            before_seal["root_sha256"] != after_seal["root_sha256"]
            or before_seal["manifest_digests"]
            != after_seal["manifest_digests"]
        ):
            raise ValueError("source reviewer bytes changed during packaging")
        output_root_sha256 = _seal_artifact(staging)
        staged_seal = verify_complete_seal(staging, output_root_sha256)
        _fsync_tree(staging)
        _rename_noreplace(staging, output)
        published = True
        _fsync_directory(output.parent)
        final_seal = verify_complete_seal(output, output_root_sha256)
        if final_seal["manifest_digests"] != staged_seal["manifest_digests"]:
            raise ValueError("final output seal changed during final-path verification")
        final_reviewer_seal = verify_complete_seal(
            review_resolved,
            expected_review_root_sha256,
            exact_manifest_paths=EXPECTED_REVIEW_MANIFEST_PATHS,
        )
        if (
            final_reviewer_seal["manifest_digests"]
            != before_seal["manifest_digests"]
        ):
            raise ValueError("source reviewer changed after publication")
        final_repository = _verify_live_repositories(
            Path(camp_repo),
            package_camp_head,
            Path(dp_repo),
            expected_review_camp_head=expected_review_camp_head,
            expected_execution_source_head=expected_execution_source_head,
        )
        final_repository = {
            **final_repository,
            "static_preflight_source_head": authority_fields[
                "current_v24_artifact_source_head"
            ],
            "static_preflight_source_is_package_ancestor": True,
        }
        if final_repository != repository_receipt:
            raise ValueError("live repository provenance changed after publication")
        final_authority = _verify_live_authority(
            Path(camp_repo).resolve(),
            package_camp_head,
            review_root=review_resolved,
            expected_review_root_sha256=expected_review_root_sha256,
            expected_review_camp_head=expected_review_camp_head,
        )
        if (
            final_authority["audit_bytes"] != authority_before["audit_bytes"]
            or final_authority["current_status_bytes"]
            != authority_before["current_status_bytes"]
            or final_authority["fields"] != authority_before["fields"]
            or final_authority["static_preflight_seal"]["manifest_digests"]
            != authority_before["static_preflight_seal"]["manifest_digests"]
        ):
            raise ValueError("live v24 authority changed after publication")
        final_holdout_state = _verify_live_holdout_state(
            final_authority,
            _mapping(verified["review"], "holdout_state"),
        )
        if final_holdout_state["bytes"] != holdout_state_before["bytes"]:
            raise ValueError("live holdout-once marker changed after publication")
        if _active_v24_processes():
            raise ValueError("a v24 evaluator/reviewer process exists after publication")
        free_bytes_after_gate = shutil.disk_usage(output.parent).free
        if free_bytes_after_gate <= minimum_free_bytes:
            raise ValueError("post-publication gate violates the 10 GiB disk floor")
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        if published and output.exists():
            shutil.rmtree(output)
            _fsync_directory(output.parent)
        raise
    return {
        "status": "passed",
        "decision": EXPECTED_DECISION,
        "final_claim_authorized": False,
        "output_dir": output.as_posix(),
        "root_sha256": output_root_sha256,
        "free_bytes_after_gate": free_bytes_after_gate,
        "final_post_publication_checks_passed": True,
        "next_work_target": "v24_honest_no_claim_record_only_closeout",
    }


def build_evidence_claim(
    *,
    review_root: Path,
    expected_review_root_sha256: str,
    expected_review_camp_head: str,
    expected_execution_source_head: str,
    expected_config_sha256: str,
    expected_evaluator_sha256: str,
    camp_repo: Path,
    package_camp_head: str,
    dp_repo: Path,
    output_dir: Path,
    enable_evidence_claim: bool,
    command: Sequence[str] | None = None,
    minimum_free_bytes: int = MINIMUM_FREE_BYTES,
) -> dict[str, Any]:
    if enable_evidence_claim is not True:
        raise ValueError("explicit --enable-evidence-claim is required")
    with _exclusive_global_lock(GLOBAL_LOCK_PATH):
        return _build_evidence_claim_locked(
            review_root=review_root,
            expected_review_root_sha256=expected_review_root_sha256,
            expected_review_camp_head=expected_review_camp_head,
            expected_execution_source_head=expected_execution_source_head,
            expected_config_sha256=expected_config_sha256,
            expected_evaluator_sha256=expected_evaluator_sha256,
            camp_repo=camp_repo,
            package_camp_head=package_camp_head,
            dp_repo=dp_repo,
            output_dir=output_dir,
            enable_evidence_claim=enable_evidence_claim,
            command=command,
            minimum_free_bytes=minimum_free_bytes,
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--expected-review-root-sha256", required=True)
    parser.add_argument("--expected-review-camp-head", required=True)
    parser.add_argument("--expected-execution-source-head", required=True)
    parser.add_argument("--expected-config-sha256", required=True)
    parser.add_argument("--expected-evaluator-sha256", required=True)
    parser.add_argument("--camp-repo", type=Path, required=True)
    parser.add_argument("--package-camp-head", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--enable-evidence-claim", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_evidence_claim(
        review_root=args.review_root,
        expected_review_root_sha256=args.expected_review_root_sha256,
        expected_review_camp_head=args.expected_review_camp_head,
        expected_execution_source_head=args.expected_execution_source_head,
        expected_config_sha256=args.expected_config_sha256,
        expected_evaluator_sha256=args.expected_evaluator_sha256,
        camp_repo=args.camp_repo,
        package_camp_head=args.package_camp_head,
        dp_repo=args.dp_repo,
        output_dir=args.output_dir,
        enable_evidence_claim=args.enable_evidence_claim,
    )
    print(json.dumps(result, allow_nan=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
