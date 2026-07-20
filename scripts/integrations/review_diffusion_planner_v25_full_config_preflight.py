#!/usr/bin/env python3
"""Independently rebuild and review the sealed V25 1500-config preflight."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import pickle
import re
import subprocess
import sys
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (  # noqa: E402
    CRITICAL_IMPLEMENTATION_PATHS,
    FIXED_DP_HEAD,
    PREFLIGHT_RELEASE_SCHEMA_VERSION,
    file_sha256,
    verify_dual_head_contract,
    verify_seven_root_chain,
)
from camp_core.integrations.diffusion_planner_v25_a17_full_corpus_authority import (  # noqa: E402
    NONCE_LEDGER as A17_NONCE_LEDGER,
    PREFLIGHT_GATE as A17_PREFLIGHT_GATE,
    PREFLIGHT_RELEASE_FIELDS as A17_PREFLIGHT_RELEASE_FIELDS,
    PREFLIGHT_RELEASE_SCHEMA_VERSION as A17_PREFLIGHT_RELEASE_SCHEMA_VERSION,
    UPSTREAM_ROLES as A17_UPSTREAM_ROLES,
    verify_release as verify_a17_full_corpus_release,
    verify_upstream_chain as verify_a17_upstream_chain,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    validate_no_signal_chain,
    validate_signal_chain,
)


SCHEMA_VERSION = "camp_dp_v25_full_config_preflight_review_v4"
EXECUTION_SCHEMA_VERSION = "camp_dp_v25_controlled_training_corpus_execution_v8"
CANONICAL_JSON_BYTE_SPEC_VERSION = "camp_dp_v25_canonical_json_utf8_lf_v1"
SEMANTIC_PAYLOAD_SCHEMA_VERSION = "camp_dp_v25_semantic_clone_payload_v3"
SEMANTIC_AUTHORITY_SIDECAR_SCHEMA_VERSION = (
    "camp_dp_v25_full_r_semantic_authority_chains_v3"
)
EXPECTED_EXECUTABLE_IDENTITIES = 1500
EXPECTED_RETAINED_INELIGIBLE = 153
EXPECTED_SEED = 25001
CORPUS_STEPS = 64
CONTEXT_SCHEMA_VERSION = "camp_dp_v25_causal_context_raw_v2"
SUPERSEDED_PARTIAL_CORPUS_ROOT = (
    "a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481"
)
EXPECTED_TRAIN_LOCK = "/root/autodl-tmp/.camp_dp_v25_controlled_train_corpus.lock"
EXPECTED_NONCE_LEDGER = Path(
    "/root/autodl-tmp/.camp_dp_v25_controlled_train_release_nonces"
)
REVIEW_CORRECTION_PATHS = frozenset(
    {
        "scripts/integrations/review_diffusion_planner_v25_full_config_preflight.py",
        "camp_core/tests/test_diffusion_planner_v25_a13_r03.py",
    }
)
POINTER_ONLY_PATHS = frozenset(
    {
        "docs/diffusion_planner_current_status.md",
        "docs/diffusion_planner_v25_iteration_audit.md",
        "camp_core/tests/test_diffusion_planner_v25_iteration_audit.py",
    }
)
MINIMUM_FREE_BYTES = 10 * 1024**3
S01_NATIVE_SOURCE_ROOTS = {
    "s01_preflight": "bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451",
    "s01_review": "facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d",
}
EXPECTED_FORMAL_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_"
    "20260717T140842CST"
)
EXPECTED_FORMAL_ROOT_SHA256 = (
    "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
)
EXPECTED_FORMAL_REPORT_SCHEMA_VERSION = "camp_dp_v25_controlled_scenario_phase_v1"
EXPECTED_FORMAL_PLAN_SCHEMA_VERSION = "camp_dp_v25_controlled_corpus_final_plan_v1"
EXPECTED_FORMAL_CASE_SCHEMA_VERSION = "camp_dp_v25_controlled_scenario_case_v1"
EXPECTED_FORMAL_REPORT_FIELDS = {
    "schema_version", "status", "mode", "checks", "pilot_review",
    "source_summary", "model_loaded", "candidate_generation_started",
    "training_executed", "calibration_executed", "fresh_b_opened",
    "outcome_fields_consumed", "claim_authorized",
}
EXPECTED_FORMAL_PLAN_FIELDS = {
    "schema_version", "outcome_blind", "outcome_fields_consumed",
    "fresh_b_outcome_opened", "summary", "train", "calibration", "fresh_b",
}
EXPECTED_PROBE_TEMPLATE = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_"
    "a53d6ee3_20260715T204719CST/prepared/probe_config.json"
)
EXPECTED_PROBE_TEMPLATE_SHA256 = (
    "1e734165f7a614e93019df0a5c22b5e36722298cb50b21c5ce8fd0e4e2cf82bc"
)
EXPECTED_PROBE_TEMPLATE_SCHEMA_VERSION = "camp_dp_v24_single_record_source_probe_v1"
EXPECTED_GENERATION_SCALES = {
    "path": str(
        ROOT
        / "configs"
        / "integrations"
        / "diffusion_planner_v25_atom_scales_correction_v2.json"
    ),
    "sha256": "e844d159dc6c9c21b099084f5a46bf90fb77ca92571749f529e61e08814fe316",
}
EXPECTED_STATIC_WEIGHTS = {
    "path": (
        "/root/autodl-tmp/"
        "camp_dp_v18_nuplan_causal_10k_static_14d_train_calibrate_"
        "79c9570b_0c22f85e/models/corrected14d_weights.npy"
    ),
    "sha256": "922ae11db719a2bda983bccf0c6bca842c37a899c4df222a1f7a5ac733285134",
}
EXPECTED_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
EXPECTED_FIXED_DP_CHECKPOINT = {
    "path": "/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth",
    "sha256": "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75",
}
EXPECTED_FIXED_DP_ARGS = {
    "path": (
        "/root/autodl-tmp/"
        "camp_dp_v18_nuplan_mini_smoke_split_candidate_preflight_"
        "20260710T220921CST/fixed_dp_args.json"
    ),
    "sha256": "42c1174de7db49d20343d9ff155093ee206ea9fb31bf0fa7185b108e36c66caa",
}
EXPECTED_DP_NATIVE_SOURCE_SHA256 = {
    "scenario_generation/mpc_tracker.py": (
        "bf2fdc6398898a42eda4ab3d12045c5204eb5ce8a993dbf96feee975de04395a"
    ),
    "scenario_generation/replay.py": (
        "92158e32f8e2626a20aeee1783501d1afad228f06d5948f3426716d93320c5eb"
    ),
    "scenario_generation/simulate.py": (
        "de4542fbc8685718379dbf0626499113d8bca6f7dead1c4456d2d34ffd0b9e4e"
    ),
    "scenario_generation/tensor_converter.py": (
        "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
    ),
    "scenario_generation/traffic_light.py": (
        "5a1659fe753102c514528c0bd93c261124bdf8de11bbc00ba5b941c151956af4"
    ),
}
CONFIG_RECEIPT_FIELDS = {
    "schema_version",
    "scenario_id",
    "family",
    "tier",
    "route_identity_sha256",
    "canonical_semantic_clone_sha256",
    "signal_source_chain_sha256",
    "map_sha256",
    "route_sha256",
    "fixed_dp_head",
    "fixed_dp_checkpoint_sha256",
    "fixed_dp_args_sha256",
    "generation_scales_sha256",
    "static_weights_sha256",
    "selector_role",
    "seed",
    "corpus_steps",
    "context_schema_version",
    "context_mode",
    "selector_training_execution_authorized",
    "calibration_authorized",
    "holdout_access_authorized",
    "fresh_b_opened",
    "outcome_fields_consumed",
    "config_authority_sha256",
}
REQUIRED_REPORT_FIELDS = {
    "schema_version",
    "canonical_json_byte_spec",
    "status",
    "mode",
    "camp_head",
    "implementation_source_head",
    "released_camp_source_head",
    "current_repo_head_at_run",
    "fixed_dp_head",
    "dp_repo",
    "formal_artifact",
    "formal_root_sha256",
    "probe_template",
    "probe_template_sha256",
    "generation_scales",
    "static_weights",
    "seed",
    "corpus_steps",
    "snapshot_capacity",
    "train_lock",
    "minimum_free_bytes",
    "rejected_roots",
    "r0_review_artifact",
    "r0_review_root_sha256",
    "r0_source_artifact",
    "r0_source_root_sha256",
    "seven_root_bindings",
    "seven_root_bindings_sha256",
    "release_run_nonce",
    "release_nonce_consumption_marker",
    "authorized_output_dir",
    "critical_implementation_manifest",
    "ultra_full_config_preflight_release_artifact",
    "ultra_full_config_preflight_release_root_sha256",
    "semantic_authority_root_sha256",
    "semantic_authority_identity_count",
    "semantic_authority_chains_root_sha256",
    "terminal_lock_scope",
    "free_bytes_at_start",
    "fresh_b_opened",
    "outcome_fields_consumed",
    "config_receipts_root_sha256",
    "validated_identity_count",
    "source_ineligible_retained_identity_count",
    "retained_ineligible_receipts",
    "retained_ineligible_receipts_root_sha256",
    "formal_train_manifest_identity_count",
    "unique_route_count",
    "family_counts",
    "tier_counts",
    "model_loaded",
    "candidate_generation_started",
    "simulator_started",
    "training_executed",
    "calibration_executed",
    "claim_authorized",
    "config_receipts",
}


def _oracle_canonical_json_bytes(payload: Any) -> bytes:
    """Independent implementation of the frozen canonical byte contract."""
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _oracle_sha256(payload: Any) -> str:
    return hashlib.sha256(_oracle_canonical_json_bytes(payload)).hexdigest()


def _git_changed_paths(repo: Path, left: str, right: str) -> set[str]:
    return {
        line.replace("\\", "/")
        for line in subprocess.check_output(
            ["git", "diff", "--name-only", left, right, "--"],
            cwd=repo,
            text=True,
        ).splitlines()
        if line
    }


def _historical_manifest(
    repo: Path, source_head: str, manifest: Mapping[str, Any]
) -> dict[str, str]:
    if (
        type(manifest) is not dict
        or not manifest
        or set(manifest) != set(CRITICAL_IMPLEMENTATION_PATHS)
        or any(
            type(path) is not str
            or not path
            or "\\" in path
            or path.startswith("/")
            or ".." in Path(path).parts
            or _require_sha256_string(value, f"historical manifest {path}")
            != value
            for path, value in manifest.items()
        )
    ):
        raise ValueError("historical critical implementation manifest is invalid")
    return {
        path: hashlib.sha256(
            subprocess.check_output(["git", "show", f"{source_head}:{path}"], cwd=repo)
        ).hexdigest()
        for path in manifest
    }


def _verify_archived_producer_contract(
    *,
    repo: Path,
    implementation_source_head: Any,
    producer_pointer_head: Any,
    live_review_head: str,
    implementation_manifest: Any,
) -> list[str]:
    for label, head in (
        ("implementation source", implementation_source_head),
        ("producer pointer", producer_pointer_head),
        ("live review", live_review_head),
    ):
        if type(head) is not str or re.fullmatch(r"[0-9a-f]{40}", head) is None:
            raise ValueError(f"A1.7 {label} HEAD is invalid")
    if _historical_manifest(
        repo, implementation_source_head, implementation_manifest
    ) != implementation_manifest:
        raise ValueError("A1.7 archived producer manifest drifted")
    if implementation_source_head != producer_pointer_head:
        producer_delta = _git_changed_paths(
            repo, implementation_source_head, producer_pointer_head
        )
        if not producer_delta or producer_delta - POINTER_ONLY_PATHS:
            raise ValueError("A1.7 producer dual-HEAD diff exceeds pointer allowlist")
    if producer_pointer_head == live_review_head:
        return []
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", producer_pointer_head, live_review_head],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    review_delta = _git_changed_paths(repo, producer_pointer_head, live_review_head)
    if not review_delta or review_delta - REVIEW_CORRECTION_PATHS:
        raise ValueError("full-config review HEAD exceeds review-only delta")
    return sorted(review_delta)


def _strict_json_equal(actual: Any, expected: Any) -> bool:
    """Independent type-exact JSON comparison (bool is never an int)."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _strict_json_equal(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _strict_json_equal(left, right)
            for left, right in zip(actual, expected)
        )
    if isinstance(expected, float):
        return math.isfinite(actual) and actual == expected
    return actual == expected


def _require_json_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be a native JSON integer")
    return value


def _require_json_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a native JSON boolean")
    return value


def _require_sha256_string(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a native 64-hex string")
    return value


def _require_canonical_absolute_path(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{label} must be a native path string")
    path = Path(value)
    if not path.is_absolute() or value != str(path.resolve()):
        raise ValueError(f"{label} must be an absolute canonical path string")
    return value


def _validate_config_receipts(
    actual: Any, expected: list[dict[str, Any]], reported_root: Any
) -> str:
    if type(actual) is not list or len(actual) != len(expected):
        raise ValueError("config receipt list/count drifted")
    for ordinal, row in enumerate(actual):
        if type(row) is not dict or set(row) != CONFIG_RECEIPT_FIELDS:
            raise ValueError(f"config receipt {ordinal} field set drifted")
        _require_json_int(row.get("seed"), f"config receipt {ordinal} seed")
        _require_json_int(
            row.get("corpus_steps"), f"config receipt {ordinal} corpus_steps"
        )
        for field in (
            "selector_training_execution_authorized",
            "calibration_authorized",
            "holdout_access_authorized",
            "fresh_b_opened",
        ):
            _require_json_bool(row.get(field), f"config receipt {ordinal} {field}")
        authority = {
            key: value
            for key, value in row.items()
            if key != "config_authority_sha256"
        }
        claimed = row.get("config_authority_sha256")
        if type(claimed) is not str or claimed != _oracle_sha256(authority):
            raise ValueError(f"config receipt {ordinal} row authority SHA drifted")
    if not _strict_json_equal(actual, expected):
        raise ValueError("actual config receipts differ type-exactly from oracle")
    actual_root = _oracle_sha256(actual)
    expected_root = _oracle_sha256(expected)
    if (
        type(reported_root) is not str
        or reported_root != actual_root
        or actual_root != expected_root
    ):
        raise ValueError("config receipt actual/expected/reported root drifted")
    return actual_root


def _same_path(value: Any, expected: Path) -> bool:
    return isinstance(value, str) and Path(value).resolve() == expected.resolve()


def _verify_frozen_authority_universe(
    report: Mapping[str, Any], release: Mapping[str, Any]
) -> None:
    """Bind review to the one frozen formal/template/DP universe.

    This oracle intentionally uses local literals rather than producer or
    release-derived values, so a completely re-signed alternate universe is
    rejected even when it is internally self-consistent.
    """
    if (
        not _same_path(report.get("formal_artifact"), EXPECTED_FORMAL_ARTIFACT)
        or report.get("formal_root_sha256") != EXPECTED_FORMAL_ROOT_SHA256
        or not _same_path(report.get("probe_template"), EXPECTED_PROBE_TEMPLATE)
        or report.get("probe_template_sha256") != EXPECTED_PROBE_TEMPLATE_SHA256
        or report.get("generation_scales") != EXPECTED_GENERATION_SCALES
        or report.get("static_weights") != EXPECTED_STATIC_WEIGHTS
        or not _same_path(report.get("dp_repo"), EXPECTED_DP_REPO)
        or not _same_path(release.get("formal_artifact"), EXPECTED_FORMAL_ARTIFACT)
        or release.get("formal_root_sha256") != EXPECTED_FORMAL_ROOT_SHA256
        or not _same_path(release.get("probe_template"), EXPECTED_PROBE_TEMPLATE)
        or release.get("probe_template_sha256")
        != EXPECTED_PROBE_TEMPLATE_SHA256
        or release.get("generation_scales") != EXPECTED_GENERATION_SCALES
        or release.get("static_weights") != EXPECTED_STATIC_WEIGHTS
        or not _same_path(release.get("dp_repo"), EXPECTED_DP_REPO)
        or release.get("fixed_dp_head") != FIXED_DP_HEAD
        or release.get("fixed_dp_checkpoint") != EXPECTED_FIXED_DP_CHECKPOINT
        or release.get("fixed_dp_args_json") != EXPECTED_FIXED_DP_ARGS
        or release.get("native_source_roots") != S01_NATIVE_SOURCE_ROOTS
    ):
        raise ValueError("frozen formal/template/DP authority universe drifted")


def _round_clean(values: np.ndarray, decimals: int = 6) -> np.ndarray:
    rounded = np.round(np.asarray(values, dtype=np.float64), decimals)
    rounded[np.abs(rounded) < 0.5 * 10.0 ** (-decimals)] = 0.0
    return rounded


def _resample_polyline(points: np.ndarray, count: int = 64) -> np.ndarray:
    values = np.asarray(points, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("independent route polyline is invalid")
    lengths = np.linalg.norm(np.diff(values, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(lengths)))
    if cumulative[-1] <= 1e-9:
        raise ValueError("independent route polyline has no length")
    result = np.empty((count, 2), dtype=np.float64)
    for index, target in enumerate(np.linspace(0.0, float(cumulative[-1]), count)):
        left = min(max(int(np.searchsorted(cumulative, target, side="right") - 1), 0), len(values) - 2)
        span = float(cumulative[left + 1] - cumulative[left])
        fraction = 0.0 if span <= 1e-12 else (target - cumulative[left]) / span
        result[index] = values[left] + fraction * (values[left + 1] - values[left])
    return result


def _independent_semantic_payload(
    case: Mapping[str, Any], route_world: np.ndarray, stop_world: np.ndarray | None
) -> dict[str, Any]:
    """Locally rebuild semantic-v3 without calling the producer implementation."""
    sampled = _resample_polyline(route_world)
    origin = sampled[0]
    direction = sampled[1] - sampled[0]
    tangent = direction / np.linalg.norm(direction)
    normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
    rotation = np.stack((tangent, normal), axis=1)
    parameter_fields = {
        "headway_m", "ego_speed_mps", "other_speed_mps", "deceleration_mps2",
        "trigger_time_s", "lateral_offset_m", "lateral_speed_mps",
        "crossing_speed_mps", "variant",
    }
    parameters_raw = case.get("parameters")
    if not isinstance(parameters_raw, Mapping) or set(parameters_raw) - parameter_fields:
        raise ValueError("independent semantic parameter fields drifted")
    parameters: dict[str, float] = {}
    for key, value in parameters_raw.items():
        if key == "variant":
            if type(value) is not int:
                raise ValueError("semantic variant parameter must be an integer")
            continue
        if type(value) not in (int, float) or not math.isfinite(float(value)):
            raise ValueError("semantic physical parameter is invalid")
        parameters[key] = float(value)
    actor_input_fields = {
        "id", "agent_type", "initial_xy", "initial_heading_rad", "route_tangent",
        "route_normal", "trigger_time_s", "longitudinal_speed_mps",
        "lateral_offset_m", "lateral_speed_mps", "lateral_target_m",
        "longitudinal_acceleration_mps2", "length_m", "width_m", "wheelbase_m",
    }
    actors = []
    for raw in case.get("actors", []):
        if not isinstance(raw, Mapping) or set(raw) - actor_input_fields or not (actor_input_fields - {"id"}).issubset(raw):
            raise ValueError("independent semantic actor fields drifted")
        initial = np.asarray(raw["initial_xy"], dtype=np.float64)
        actor_tangent = np.asarray(raw["route_tangent"], dtype=np.float64)
        actor_normal = np.asarray(raw["route_normal"], dtype=np.float64)
        heading = float(raw["initial_heading_rad"])
        item: dict[str, Any] = {
            "agent_type": str(raw["agent_type"]),
            "initial_xy_local_m": _round_clean((initial - origin) @ rotation).tolist(),
            "initial_heading_local_unit": _round_clean(
                np.asarray([math.cos(heading), math.sin(heading)]) @ rotation
            ).tolist(),
            "route_tangent_local": _round_clean(actor_tangent @ rotation).tolist(),
            "route_normal_local": _round_clean(actor_normal @ rotation).tolist(),
        }
        for key in sorted((actor_input_fields - {"id"}) - {
            "agent_type", "initial_xy", "initial_heading_rad", "route_tangent", "route_normal"
        }):
            value = raw[key]
            if key == "lateral_target_m" and value is None:
                item[key] = None
            elif type(value) in (int, float) and math.isfinite(float(value)):
                item[key] = float(value)
            else:
                raise ValueError("independent semantic actor physical field is invalid")
        actors.append(item)
    actors.sort(key=_oracle_sha256)
    signal = case.get("signal")
    if not isinstance(signal, Mapping) or set(signal) not in (
        {"phase", "mapped_source_required"},
        {"phase", "phase_remaining_s", "mapped_source_required"},
    ):
        raise ValueError("independent semantic signal fields drifted")
    if "phase_remaining_s" in signal and (
        type(signal["phase_remaining_s"]) not in (int, float)
        or not math.isfinite(float(signal["phase_remaining_s"]))
        or float(signal["phase_remaining_s"]) < 0.0
    ):
        raise ValueError("independent scenario timing field is invalid")
    payload: dict[str, Any] = {
        "schema_version": SEMANTIC_PAYLOAD_SCHEMA_VERSION,
        "family": str(case.get("family")),
        "tier": str(case.get("tier")),
        "semantic_variant": str(case.get("semantic_variant")),
        "parameters": parameters,
        "actors": actors,
        "signal": {
            "current_phase": str(signal["phase"]),
            "mapped_source_required": signal["mapped_source_required"] is True,
            "source_mode": "no_v2i",
        },
        "route_polyline_local_m": _round_clean((sampled - origin) @ rotation).tolist(),
    }
    if stop_world is not None:
        stop = np.asarray(stop_world, dtype=np.float64)
        payload["stop_line_local_m"] = _round_clean((stop - origin) @ rotation).tolist()
    return payload


def _independent_route_polyline(builder: Any, route_ids: list[int]) -> np.ndarray:
    pieces = []
    for lanelet_id in route_ids:
        if lanelet_id not in builder._cache:
            raise ValueError("formal route lanelet is absent from actual map")
        line = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        pieces.append(line if not pieces else line[1:])
    return np.concatenate(pieces, axis=0)


def _independent_stop_projection(
    builder: Any, route_ids: list[int], controlled: list[int], stop: np.ndarray
) -> tuple[float, float, float, np.ndarray]:
    midpoint = stop.mean(axis=0)
    route_offset = 0.0
    best: tuple[float, float, np.ndarray] | None = None
    for lanelet_id in route_ids:
        line = np.asarray(builder._cache[lanelet_id].raw_centerline, dtype=np.float64)
        local_offset = 0.0
        for start, end in zip(line[:-1], line[1:]):
            vector = end - start
            length = float(np.linalg.norm(vector))
            fraction = 0.0 if length <= 1e-12 else float(np.clip(((midpoint - start) @ vector) / length**2, 0.0, 1.0))
            if lanelet_id in controlled and length > 1e-12:
                projected = start + fraction * vector
                candidate = (
                    float(np.linalg.norm(midpoint - projected)),
                    route_offset + local_offset + fraction * length,
                    vector / length,
                )
                if best is None or candidate[:2] < best[:2]:
                    best = candidate
            local_offset += length
        route_offset += local_offset
    if best is None:
        raise ValueError("certified stop line does not project to the formal controlled route")
    return best[0], best[1], route_offset, best[2]


def _independent_reconstruct_chain(case: Mapping[str, Any], builder: Any) -> dict[str, Any]:
    route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
    route_world = _independent_route_polyline(builder, route_ids)
    regs: dict[int, dict[str, Any]] = {}
    for lanelet_id in route_ids:
        lanelet = builder._ll_by_id.get(lanelet_id)
        if lanelet is None:
            raise ValueError("formal route lanelet is missing from actual map")
        for reg in lanelet.trafficLights():
            row = regs.setdefault(int(reg.id), {"reg": reg, "lanelet_ids": []})
            row["lanelet_ids"].append(lanelet_id)
    if case.get("signal", {}).get("phase") == "none":
        if regs:
            raise ValueError("formal no-signal route has actual signal authority")
        semantic = _independent_semantic_payload(case, route_world, None)
        result: dict[str, Any] = {
            "schema_version": "camp_dp_v25_no_signal_source_chain_v1",
            "scenario_id": str(case["scenario_id"]),
            "route_identity_sha256": str(case["route_identity_sha256"]),
            "source_map_sha256": str(case["source_map_sha256"]),
            "route_lanelet_ids": route_ids,
            "route_geometry_sha256": _oracle_sha256(
                {"route_polyline_local_m": semantic["route_polyline_local_m"]}
            ),
            "traffic_light_regulatory_element_ids": [],
            "semantic_clone_payload": semantic,
            "semantic_clone_sha256": _oracle_sha256(semantic),
            "source_chain_sha256": "",
        }
    else:
        if len(regs) != 1:
            raise ValueError("formal signal route does not map to one actual regulatory element")
        reg_id, row = next(iter(regs.items()))
        reg = row["reg"]
        stop_line = reg.stopLine
        if stop_line is None:
            raise ValueError("actual regulatory element has no stop line")
        stop = np.asarray([(point.x, point.y) for point in stop_line], dtype=np.float64)
        controlled = sorted(set(int(value) for value in row["lanelet_ids"]))
        distance, arc, length, tangent = _independent_stop_projection(
            builder, route_ids, controlled, stop
        )
        semantic = _independent_semantic_payload(case, route_world, stop)
        params = reg.parameters
        result = {
            "schema_version": "camp_dp_v25_red_signal_source_chain_v2",
            "scenario_id": str(case["scenario_id"]),
            "route_identity_sha256": str(case["route_identity_sha256"]),
            "source_map_sha256": str(case["source_map_sha256"]),
            "regulatory_element_ids": [reg_id],
            "physical_light_ids": sorted(
                int(value.id) for value in (params["refers"] if "refers" in params else [])
            ),
            "bulb_ids": sorted(
                int(value.id)
                for value in (params["light_bulbs"] if "light_bulbs" in params else [])
            ),
            "controlled_lanelet_ids": controlled,
            "route_lanelet_ids": route_ids,
            "route_geometry_sha256": _oracle_sha256(
                {
                    "route_polyline_local_m": semantic["route_polyline_local_m"],
                    "stop_line_local_m": semantic["stop_line_local_m"],
                }
            ),
            "stop_line_id": int(stop_line.id),
            "stop_line_geometry_m": stop.tolist(),
            "stop_line_geometry_sha256": _oracle_sha256(stop.tolist()),
            "stop_line_route_distance_m": distance,
            "route_arc_m": arc,
            "route_length_m": length,
            "route_tangent_world": tangent.tolist(),
            "expected_current_phase": str(case["signal"]["phase"]),
            "semantic_clone_payload": semantic,
            "semantic_clone_sha256": _oracle_sha256(semantic),
            "source_chain_sha256": "",
        }
    result["source_chain_sha256"] = _oracle_sha256(
        {key: value for key, value in result.items() if key != "source_chain_sha256"}
    )
    return result


def _independent_validate_route_pickle(
    route_path: Path, case: Mapping[str, Any], dp_repo: Path
) -> None:
    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.route import Route

    route = Route.load(route_path)
    spec = case["route_spec"]
    lanelet_ids = [int(value) for value in spec["lanelet_ids"]]
    if (
        set(vars(route)) != {
            "map_path", "start_pose", "goal_pose", "start_lanelet_id",
            "goal_lanelet_id", "waypoint_poses", "waypoint_lanelet_ids",
            "route_lanelet_ids",
        }
        or str(route.map_path) != str(case["source_map_path"])
        or not np.array_equal(route.start_pose, np.asarray(spec["start_pose"], dtype=np.float32))
        or not np.array_equal(route.goal_pose, np.asarray(spec["goal_pose"], dtype=np.float32))
        or route.start_lanelet_id != lanelet_ids[0]
        or route.goal_lanelet_id != lanelet_ids[-1]
        or route.waypoint_poses != []
        or route.waypoint_lanelet_ids != []
        or route.route_lanelet_ids != lanelet_ids
    ):
        raise ValueError("route pickle does not exactly serialize the formal route spec")


def _load_independent_map_builder(map_path: Path, dp_repo: Path) -> Any:
    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from camp_core.integrations.diffusion_planner import (
        install_lanelet2_projection_fallback,
        require_source_preserving_lanelet2_regulatory_adapter,
    )
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

    require_source_preserving_lanelet2_regulatory_adapter(map_path)
    sys.modules.pop("autoware_lanelet2_extension_python.projection", None)
    sys.modules.pop("autoware_lanelet2_extension_python", None)
    install_lanelet2_projection_fallback(map_path)
    return LaneletSceneBuilder(str(map_path.resolve()))


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


def _verify_asset(payload: Any) -> dict[str, str]:
    if not isinstance(payload, Mapping) or set(payload) != {"path", "sha256"}:
        raise ValueError("asset receipt field set drifted")
    path = Path(str(payload["path"]))
    if not path.is_file() or path.is_symlink() or file_sha256(path) != payload["sha256"]:
        raise ValueError(f"asset receipt does not match the actual file: {path}")
    return {"path": str(path), "sha256": str(payload["sha256"])}


def _retained_ineligible_receipts(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for case in plan["train"]:
        if case.get("runner_eligible") is not False:
            continue
        result.append(
            {
                "scenario_id": str(case["scenario_id"]),
                "family": str(case["family"]),
                "tier": str(case["tier"]),
                "route_identity_sha256": str(case["route_identity_sha256"]),
                "source_map_sha256": str(case["source_map_sha256"]),
                "source_requirements": list(case["source_requirements"]),
                "source_availability": dict(case["source_availability"]),
                "retention_role": str(case["retention_role"]),
            }
        )
    return result


def _independent_config_receipts(
    *,
    preflight: Path,
    cases: list[Mapping[str, Any]],
    chains: list[Mapping[str, Any]],
    template: Mapping[str, Any],
    generation_scales_sha256: str,
    static_weights_sha256: str,
    dp_repo: Path,
) -> list[dict[str, Any]]:
    chain_by_id: dict[str, dict[str, Any]] = {}
    for raw_chain in chains:
        if raw_chain.get("expected_current_phase") is None:
            chain = validate_no_signal_chain(raw_chain)
        else:
            chain = validate_signal_chain(raw_chain)
        scenario_id = str(chain["scenario_id"])
        if scenario_id in chain_by_id:
            raise ValueError("semantic authority contains duplicate identities")
        chain_by_id[scenario_id] = chain
    if len(chain_by_id) != len(cases):
        raise ValueError("semantic authority identity denominator drifted")

    fixed_dp = template.get("fixed_dp")
    if not isinstance(fixed_dp, Mapping) or fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("fixed-DP template authority drifted")
    checkpoint = _verify_asset(fixed_dp.get("checkpoint"))
    args_json = _verify_asset(fixed_dp.get("args_json"))
    builders: dict[str, Any] = {}
    receipts = []
    for case in cases:
        scenario_id = str(case["scenario_id"])
        chain = chain_by_id.get(scenario_id)
        if chain is None:
            raise ValueError("formal identity has no independently valid source chain")
        identity = str(case["route_identity_sha256"])
        if (
            chain.get("route_identity_sha256") != identity
            or chain.get("source_map_sha256") != case.get("source_map_sha256")
            or chain.get("semantic_clone_payload", {}).get("family")
            != case.get("family")
            or chain.get("semantic_clone_payload", {}).get("tier")
            != case.get("tier")
        ):
            raise ValueError("source chain does not match the formal semantic identity")
        map_path = Path(str(case["source_map_path"]))
        route_path = preflight / "routes" / f"{identity}.pkl"
        if (
            not map_path.is_file()
            or map_path.is_symlink()
            or file_sha256(map_path) != case["source_map_sha256"]
            or not route_path.is_file()
            or route_path.is_symlink()
        ):
            raise ValueError("formal map/route actual SHA authority drifted")
        _independent_validate_route_pickle(route_path, case, dp_repo)
        map_key = str(map_path.resolve())
        if map_key not in builders:
            builders[map_key] = _load_independent_map_builder(map_path, dp_repo)
        expected_chain = _independent_reconstruct_chain(case, builders[map_key])
        if chain != expected_chain:
            raise ValueError(
                "source chain is self-consistent but does not match formal case/actual map"
            )
        authority = {
            "schema_version": "camp_dp_v25_controlled_train_v2",
            "scenario_id": scenario_id,
            "family": str(case["family"]),
            "tier": str(case["tier"]),
            "route_identity_sha256": identity,
            "canonical_semantic_clone_sha256": str(
                chain["semantic_clone_sha256"]
            ),
            "signal_source_chain_sha256": str(chain["source_chain_sha256"]),
            "map_sha256": file_sha256(map_path),
            "route_sha256": file_sha256(route_path),
            "fixed_dp_head": FIXED_DP_HEAD,
            "fixed_dp_checkpoint_sha256": checkpoint["sha256"],
            "fixed_dp_args_sha256": args_json["sha256"],
            "generation_scales_sha256": generation_scales_sha256,
            "static_weights_sha256": static_weights_sha256,
            "selector_role": "v25_controlled_train_fixed_static_behavior_policy",
            "seed": EXPECTED_SEED,
            "corpus_steps": CORPUS_STEPS,
            "context_schema_version": CONTEXT_SCHEMA_VERSION,
            "context_mode": "no_v2i",
            "selector_training_execution_authorized": False,
            "calibration_authorized": False,
            "holdout_access_authorized": False,
            "fresh_b_opened": False,
            "outcome_fields_consumed": [],
        }
        receipts.append(
            {**authority, "config_authority_sha256": _oracle_sha256(authority)}
        )
    return receipts


def review(preflight: Path, expected_root: str) -> dict[str, Any]:
    live_camp_head = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    seal = verify_complete_seal(
        preflight, expected_root, label="V25 full-config preflight"
    )
    report = _load(preflight / "report.json")
    source = _load(preflight / "source_receipt.json")
    _require_sha256_string(report.get("release_run_nonce"), "preflight report nonce")
    _require_canonical_absolute_path(
        report.get("authorized_output_dir"), "preflight report output directory"
    )
    for field in (
        "seed",
        "corpus_steps",
        "snapshot_capacity",
        "minimum_free_bytes",
        "free_bytes_at_start",
        "semantic_authority_identity_count",
        "validated_identity_count",
        "source_ineligible_retained_identity_count",
        "formal_train_manifest_identity_count",
        "unique_route_count",
    ):
        _require_json_int(report.get(field), f"preflight report {field}")
    for field in (
        "model_loaded",
        "candidate_generation_started",
        "simulator_started",
        "training_executed",
        "calibration_executed",
        "fresh_b_opened",
        "claim_authorized",
    ):
        _require_json_bool(report.get(field), f"preflight report {field}")
    if (
        (preflight / "run.exit").read_text(encoding="ascii") != "0\n"
        or not _strict_json_equal(source, report)
        or set(report) != REQUIRED_REPORT_FIELDS
        or report.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or report.get("canonical_json_byte_spec")
        != CANONICAL_JSON_BYTE_SPEC_VERSION
        or report.get("status") != "passed"
        or report.get("mode") != "preflight"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("implementation_source_head")
        != report.get("released_camp_source_head")
        or report.get("camp_head") != report.get("current_repo_head_at_run")
        or report.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or report.get("corpus_steps") != CORPUS_STEPS
        or report.get("seed") != EXPECTED_SEED
        or report.get("train_lock") != EXPECTED_TRAIN_LOCK
        or report.get("minimum_free_bytes") != MINIMUM_FREE_BYTES
        or report.get("free_bytes_at_start") < MINIMUM_FREE_BYTES
        or report.get("terminal_lock_scope")
        != "preflight_or_execution_from_before_output_creation_through_progress_report_run_exit_and_seal"
        or report.get("validated_identity_count")
        != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("source_ineligible_retained_identity_count")
        != EXPECTED_RETAINED_INELIGIBLE
        or report.get("formal_train_manifest_identity_count")
        != EXPECTED_EXECUTABLE_IDENTITIES + EXPECTED_RETAINED_INELIGIBLE
        or report.get("snapshot_capacity")
        != EXPECTED_EXECUTABLE_IDENTITIES * CORPUS_STEPS
        or report.get("semantic_authority_identity_count")
        != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("model_loaded") is not False
        or report.get("candidate_generation_started") is not False
        or report.get("simulator_started") is not False
        or report.get("training_executed") is not False
        or report.get("calibration_executed") is not False
        or report.get("fresh_b_opened") is not False
        or report.get("claim_authorized") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("full-config preflight report contract drifted")
    if subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--"],
        check=False,
    ).returncode != 0:
        raise ValueError("CAMP live worktree is tracked-dirty")
    dp_repo = Path(str(report["dp_repo"]))
    if (
        not dp_repo.is_dir()
        or subprocess.check_output(
            ["git", "-C", str(dp_repo), "rev-parse", "HEAD"], text=True
        ).strip()
        != FIXED_DP_HEAD
        or subprocess.run(
            ["git", "-C", str(dp_repo), "diff", "--quiet", "HEAD", "--"],
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("fixed DP live repository drifted or is tracked-dirty")
    heads = (preflight / "HEADS").read_text(encoding="ascii").splitlines()
    if heads != [
        f"camp_source_head={report['implementation_source_head']}",
        f"camp_pointer_head={report['camp_head']}",
        f"fixed_dp_head={FIXED_DP_HEAD}",
    ] or not (preflight / "COMMAND").read_text(encoding="utf-8").strip():
        raise ValueError("full-config preflight HEADS/COMMAND drifted")
    a17_report_authority = set(report["seven_root_bindings"]) == set(
        A17_UPSTREAM_ROLES
    )
    if a17_report_authority:
        review_only_changed_paths = _verify_archived_producer_contract(
            repo=ROOT,
            implementation_source_head=report["implementation_source_head"],
            producer_pointer_head=report["camp_head"],
            live_review_head=live_camp_head,
            implementation_manifest=report["critical_implementation_manifest"],
        )
    else:
        if report["camp_head"] != live_camp_head:
            raise ValueError("legacy full-config review requires the producer HEAD")
        verify_dual_head_contract(
            repo=ROOT,
            implementation_source_head=str(report["implementation_source_head"]),
            current_pointer_head=str(report["camp_head"]),
            implementation_manifest=report["critical_implementation_manifest"],
        )
        review_only_changed_paths = []
    if a17_report_authority:
        verified_roots = verify_a17_upstream_chain(
            bindings=report["seven_root_bindings"],
            repo=ROOT,
            dp_repo=dp_repo,
            probe_template=Path(str(report["probe_template"])),
        )
        expected_source_root = report["seven_root_bindings"]["source"][
            "root_sha256"
        ]
        expected_review_root = report["seven_root_bindings"][
            "bounded_execution_review"
        ]["root_sha256"]
        a17_authority = True
    else:
        verified_roots = verify_seven_root_chain(
            bindings=report["seven_root_bindings"],
            implementation_source_head=str(report["implementation_source_head"]),
            fixed_dp_head=FIXED_DP_HEAD,
            rejected_root_sha256=SUPERSEDED_PARTIAL_CORPUS_ROOT,
        )
        expected_source_root = verified_roots["r01_source"]["root_sha256"]
        expected_review_root = verified_roots["r01_bounded_review"]["root_sha256"]
        a17_authority = False
    if (
        report.get("seven_root_bindings_sha256")
        != _oracle_sha256(report["seven_root_bindings"])
        or report.get("r0_source_root_sha256") != expected_source_root
        or report.get("r0_review_root_sha256") != expected_review_root
    ):
        raise ValueError("full-config prerequisite-root machine authority drifted")
    release_artifact = Path(
        str(report["ultra_full_config_preflight_release_artifact"])
    )
    verify_complete_seal(
        release_artifact,
        str(report["ultra_full_config_preflight_release_root_sha256"]),
        label="V25 full-config preflight release",
    )
    release = _load(release_artifact / "decision.json")
    _require_sha256_string(release.get("run_nonce"), "preflight release nonce")
    _require_canonical_absolute_path(
        release.get("authorized_output_dir"), "preflight release output directory"
    )
    legacy_release_fields = {
        "schema_version", "status", "implementation_source_head",
        "pointer_head_at_release", "fixed_dp_head", "formal_artifact",
        "formal_root_sha256", "probe_template", "probe_template_sha256",
        "generation_scales", "static_weights", "dp_repo",
        "fixed_dp_checkpoint", "fixed_dp_args_json", "native_source_roots",
        "root_artifacts", "rejected_roots", "critical_implementation_manifest",
        "run_nonce", "authorized_output_dir", "full_config_preflight_authorized",
        "full_r_execute_authorized", "fresh_b2_opened", "outcome_fields_consumed",
    }
    if a17_authority:
        release_review_delta = _verify_archived_producer_contract(
            repo=ROOT,
            implementation_source_head=release.get("implementation_source_head"),
            producer_pointer_head=release.get("pointer_head_at_release"),
            live_review_head=live_camp_head,
            implementation_manifest=release.get("critical_implementation_manifest"),
        )
        if release_review_delta != review_only_changed_paths:
            raise ValueError("A1.7 report/release review-only delta drifted")
        if (
            set(release) != set(A17_PREFLIGHT_RELEASE_FIELDS)
            or release.get("gate") != A17_PREFLIGHT_GATE
            or release.get("seed") != EXPECTED_SEED
            or release.get("executable_identity_count")
            != EXPECTED_EXECUTABLE_IDENTITIES
            or release.get("retained_source_ineligible_count")
            != EXPECTED_RETAINED_INELIGIBLE
            or release.get("corpus_steps") != CORPUS_STEPS
            or release.get("snapshot_capacity")
            != EXPECTED_EXECUTABLE_IDENTITIES * CORPUS_STEPS
            or release.get("device") != "cuda"
            or release.get("monitor_enabled") is not False
            or release.get("training_executed") is not False
            or release.get("calibration_executed") is not False
            or release.get("scene_runtime_enabled") is not False
            or release.get("v2i_enabled") is not False
            or release.get("critical_implementation_manifest_sha256")
            != _oracle_sha256(release.get("critical_implementation_manifest"))
            or release.get("root_artifacts_sha256")
            != _oracle_sha256(release.get("root_artifacts"))
            or not _strict_json_equal(
                release.get("bounded_prerequisite_summary"), verified_roots
            )
        ):
            raise ValueError("A1.7 full-config release exact contract drifted")
        if release.get("pointer_head_at_release") == live_camp_head:
            verified_release = verify_a17_full_corpus_release(
                repo=ROOT,
                release_artifact=release_artifact,
                release_root_sha256=str(
                    report["ultra_full_config_preflight_release_root_sha256"]
                ),
                requested_output_dir=str(preflight.resolve()),
                current_pointer_head=str(release["pointer_head_at_release"]),
                dp_repo=dp_repo,
                probe_template=Path(str(report["probe_template"])),
                mode="preflight",
                consume=False,
            )
            if verified_release["decision"] != release:
                raise ValueError("A1.7 full-config release reopen drifted")
    if (
        (release_artifact / "run.exit").read_text(encoding="ascii") != "0\n"
        or (
            not a17_authority
            and set(release) != legacy_release_fields
        )
        or release.get("schema_version")
        != (
            A17_PREFLIGHT_RELEASE_SCHEMA_VERSION
            if a17_authority
            else PREFLIGHT_RELEASE_SCHEMA_VERSION
        )
        or release.get("status")
        != (
            "a17_full_config_preflight_released"
            if a17_authority
            else "full_config_preflight_released"
        )
        or release.get("implementation_source_head")
        != report["implementation_source_head"]
        or release.get("pointer_head_at_release") != report["camp_head"]
        or release.get("root_artifacts") != report["seven_root_bindings"]
        or release.get("rejected_roots") != report["rejected_roots"]
        or release.get("critical_implementation_manifest")
        != report["critical_implementation_manifest"]
        or release.get("fixed_dp_head") != FIXED_DP_HEAD
        or Path(str(release.get("formal_artifact"))).resolve()
        != Path(str(report["formal_artifact"])).resolve()
        or release.get("formal_root_sha256") != report["formal_root_sha256"]
        or Path(str(release.get("probe_template"))).resolve()
        != Path(str(report["probe_template"])).resolve()
        or release.get("probe_template_sha256") != report["probe_template_sha256"]
        or release.get("generation_scales") != report["generation_scales"]
        or release.get("static_weights") != report["static_weights"]
        or Path(str(release.get("dp_repo"))).resolve()
        != Path(str(report["dp_repo"])).resolve()
        or release.get("native_source_roots") != S01_NATIVE_SOURCE_ROOTS
        or release.get("run_nonce") != report["release_run_nonce"]
        or release.get("authorized_output_dir") != str(preflight.resolve())
        or report["authorized_output_dir"] != str(preflight.resolve())
        or release.get("full_config_preflight_authorized") is not True
        or release.get("full_r_execute_authorized") is not False
        or release.get("fresh_b2_opened") is not False
        or release.get("outcome_fields_consumed") != []
    ):
        raise ValueError("full-config preflight release binding drifted")
    _verify_frozen_authority_universe(report, release)
    template_authority = _load(EXPECTED_PROBE_TEMPLATE)
    fixed_template = template_authority.get("fixed_dp")
    if (
        template_authority.get("schema_version")
        != EXPECTED_PROBE_TEMPLATE_SCHEMA_VERSION
        or not isinstance(fixed_template, Mapping)
        or set(fixed_template)
        != {"repo", "head", "checkpoint", "args_json", "native_source_sha256"}
        or fixed_template.get("repo") != str(EXPECTED_DP_REPO)
        or fixed_template.get("head") != FIXED_DP_HEAD
        or fixed_template.get("checkpoint") != EXPECTED_FIXED_DP_CHECKPOINT
        or fixed_template.get("args_json") != EXPECTED_FIXED_DP_ARGS
        or fixed_template.get("native_source_sha256")
        != EXPECTED_DP_NATIVE_SOURCE_SHA256
        or release.get("fixed_dp_checkpoint") != EXPECTED_FIXED_DP_CHECKPOINT
        or release.get("fixed_dp_args_json") != EXPECTED_FIXED_DP_ARGS
    ):
        raise ValueError("full-config release fixed-DP asset binding drifted")
    _verify_asset(EXPECTED_FIXED_DP_CHECKPOINT)
    _verify_asset(EXPECTED_FIXED_DP_ARGS)
    for relative, expected_sha256 in EXPECTED_DP_NATIVE_SOURCE_SHA256.items():
        if file_sha256(EXPECTED_DP_REPO / relative) != expected_sha256:
            raise ValueError("fixed-DP native source file drifted")
    if not a17_authority:
        verify_dual_head_contract(
            repo=ROOT,
            implementation_source_head=str(release["implementation_source_head"]),
            current_pointer_head=str(release["pointer_head_at_release"]),
            implementation_manifest=release["critical_implementation_manifest"],
        )
    marker = report.get("release_nonce_consumption_marker")
    expected_marker_path = (
        A17_NONCE_LEDGER
        / f"v25_{A17_PREFLIGHT_GATE}_{report['release_run_nonce']}.consumed.json"
        if a17_authority
        else EXPECTED_NONCE_LEDGER
        / f"v25_preflight_{report['release_run_nonce']}.consumed.json"
    )
    if (
        not isinstance(marker, Mapping)
        or set(marker) != {"path", "sha256"}
        or Path(str(marker.get("path"))).resolve() != expected_marker_path.resolve()
        or not expected_marker_path.is_file()
        or file_sha256(expected_marker_path) != marker.get("sha256")
        or _load(expected_marker_path)
        != {
            "gate": A17_PREFLIGHT_GATE if a17_authority else "preflight",
            "nonce": report["release_run_nonce"],
            "authorized_output_dir": str(preflight.resolve()),
        }
    ):
        raise ValueError("full-config preflight nonce consumption marker drifted")

    formal = Path(str(report["formal_artifact"]))
    verify_complete_seal(
        formal, str(report["formal_root_sha256"]), label="V25 formal plan"
    )
    formal_report = _load(formal / "report.json")
    plan = _load(formal / "controlled_corpus_final_plan.json")
    executable = [case for case in plan["train"] if case.get("runner_eligible") is True]
    ineligible = _retained_ineligible_receipts(plan)
    expected_train_summary = {
        "executable_corridor_count": 1,
        "executable_identity_count": 1500,
        "executable_route_count": 222,
        "family_counts": {
            "blocked_lane_static_obstacle": 407,
            "cut_in_merge": 215,
            "lead_vehicle_hard_brake": 215,
            "narrow_encounter": 214,
            "pedestrian_cyclist_crossing": 214,
            "red_light_phase_timing": 21,
            "unprotected_turn_oncoming_conflict": 214,
        },
        "inventory_corridor_count": 1,
        "inventory_route_count": 375,
        "manifest_identity_count": 1653,
        "scenario_seed_run_count": 1500,
        "source_ineligible_identity_count": 153,
        "tier_counts": {"borderline": 444, "easy": 612, "high_risk": 444},
    }
    if (
        (formal / "run.exit").read_text(encoding="ascii") != "0\n"
        or set(formal_report) != EXPECTED_FORMAL_REPORT_FIELDS
        or formal_report.get("schema_version")
        != EXPECTED_FORMAL_REPORT_SCHEMA_VERSION
        or formal_report.get("status") != "passed"
        or formal_report.get("mode") != "freeze_formal"
        or not _strict_json_equal(
            formal_report.get("source_summary"), plan.get("summary")
        )
        or formal_report.get("model_loaded") is not False
        or formal_report.get("candidate_generation_started") is not False
        or formal_report.get("training_executed") is not False
        or formal_report.get("calibration_executed") is not False
        or formal_report.get("fresh_b_opened") is not False
        or formal_report.get("claim_authorized") is not False
        or formal_report.get("outcome_fields_consumed") != []
        or set(plan) != EXPECTED_FORMAL_PLAN_FIELDS
        or plan.get("schema_version") != EXPECTED_FORMAL_PLAN_SCHEMA_VERSION
        or plan.get("outcome_blind") is not True
        or plan.get("outcome_fields_consumed") != []
        or plan.get("fresh_b_outcome_opened") is not False
        or not isinstance(plan.get("train"), list)
        or len(plan["train"])
        != EXPECTED_EXECUTABLE_IDENTITIES + EXPECTED_RETAINED_INELIGIBLE
        or len(executable) != EXPECTED_EXECUTABLE_IDENTITIES
        or len(ineligible) != EXPECTED_RETAINED_INELIGIBLE
        or len({case.get("scenario_id") for case in plan["train"]})
        != EXPECTED_EXECUTABLE_IDENTITIES + EXPECTED_RETAINED_INELIGIBLE
        or any(
            case.get("schema_version") != EXPECTED_FORMAL_CASE_SCHEMA_VERSION
            or type(case.get("seeds")) is not list
            or len(case["seeds"]) != 1
            or type(case["seeds"][0]) is not int
            or case["seeds"][0] != EXPECTED_SEED
            or case.get("split") != "train"
            or case.get("outcome_blind") is not True
            or case.get("outcome_fields_consumed") != []
            or case.get("holdout_outcome_consumed") is not False
            or (
                case.get("runner_eligible") is True
                and case.get("retention_role") != "executable"
            )
            or (
                case.get("runner_eligible") is False
                and case.get("retention_role") != "source_ineligible_retained"
            )
            or type(case.get("runner_eligible")) is not bool
            for case in plan["train"]
        )
        or not _strict_json_equal(
            plan.get("summary", {}).get("split_counts", {}).get("train", {}),
            expected_train_summary,
        )
        or not _strict_json_equal(
            report.get("retained_ineligible_receipts"), ineligible
        )
        or type(report.get("retained_ineligible_receipts_root_sha256")) is not str
        or report.get("retained_ineligible_receipts_root_sha256")
        != _oracle_sha256(report.get("retained_ineligible_receipts"))
        or report.get("retained_ineligible_receipts_root_sha256")
        != _oracle_sha256(ineligible)
    ):
        raise ValueError("formal retained-ineligible denominator/root drifted")

    template_path = EXPECTED_PROBE_TEMPLATE
    if file_sha256(template_path) != EXPECTED_PROBE_TEMPLATE_SHA256:
        raise ValueError("probe template actual SHA drifted")
    template = _load(template_path)
    scales = _verify_asset(report["generation_scales"])
    weights = _verify_asset(report["static_weights"])
    if template.get("selector", {}).get("weights") != weights:
        raise ValueError("template/static-weight authority drifted")
    chain_payload = _load(preflight / "semantic_authority_chains.json")
    chains = chain_payload.get("chains")
    if (
        set(chain_payload)
        != {"schema_version", "identity_count", "chains_root_sha256", "chains"}
        or chain_payload.get("schema_version")
        != SEMANTIC_AUTHORITY_SIDECAR_SCHEMA_VERSION
        or type(chain_payload.get("identity_count")) is not int
        or chain_payload.get("identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or not isinstance(chains, list)
        or len(chains) != EXPECTED_EXECUTABLE_IDENTITIES
        or chain_payload.get("chains_root_sha256") != _oracle_sha256(chains)
        or report.get("semantic_authority_chains_root_sha256")
        != _oracle_sha256(chains)
    ):
        raise ValueError("semantic authority chain sidecar drifted")
    semantic_receipts = []
    for ordinal, chain in enumerate(chains):
        if type(chain) is not dict:
            raise ValueError(f"semantic chain {ordinal} is not an object")
        for field in (
            "scenario_id", "semantic_clone_sha256", "source_chain_sha256"
        ):
            if type(chain.get(field)) is not str:
                raise ValueError(
                    f"semantic chain {ordinal} {field} is not a native string"
                )
        semantic_receipts.append(
            {
                "scenario_id": chain["scenario_id"],
                "semantic_clone_sha256": chain["semantic_clone_sha256"],
                "source_chain_sha256": chain["source_chain_sha256"],
            }
        )
    if report.get("semantic_authority_root_sha256") != _oracle_sha256(
        semantic_receipts
    ):
        raise ValueError("semantic authority receipt root drifted")
    expected = _independent_config_receipts(
        preflight=preflight,
        cases=executable,
        chains=chains,
        template=template,
        generation_scales_sha256=scales["sha256"],
        static_weights_sha256=weights["sha256"],
        dp_repo=Path(str(report["dp_repo"])),
    )
    receipts = report.get("config_receipts")
    _validate_config_receipts(
        receipts, expected, report.get("config_receipts_root_sha256")
    )
    expected_family_counts = dict(
        collections.Counter(case["family"] for case in executable)
    )
    expected_tier_counts = dict(
        collections.Counter(case["tier"] for case in executable)
    )
    if (
        not _strict_json_equal(report.get("family_counts"), expected_family_counts)
        or not _strict_json_equal(report.get("tier_counts"), expected_tier_counts)
        or report.get("unique_route_count")
        != len({case["route_identity_sha256"] for case in executable})
    ):
        raise ValueError("independently rebuilt full-config receipts/root drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_1500_config_preflight_review_execute_closed",
        "implementation_source_head": report["implementation_source_head"],
        "review_pointer_head": live_camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(preflight),
        "reviewed_root_sha256": seal["root_sha256"],
        "identity_count": EXPECTED_EXECUTABLE_IDENTITIES,
        "executable_config_count": EXPECTED_EXECUTABLE_IDENTITIES,
        "retained_source_ineligible_count": EXPECTED_RETAINED_INELIGIBLE,
        "corpus_steps": CORPUS_STEPS,
        "snapshot_capacity": EXPECTED_EXECUTABLE_IDENTITIES * CORPUS_STEPS,
        "config_receipts_root_sha256": _oracle_sha256(expected),
        "retained_ineligible_receipts_root_sha256": _oracle_sha256(ineligible),
        "seven_root_bindings_sha256": report["seven_root_bindings_sha256"],
        "review_only_changed_paths": review_only_changed_paths,
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
            (
                f"camp_source_head={report['implementation_source_head']}\n"
                f"camp_pointer_head={report['review_pointer_head']}\n"
                f"fixed_dp_head={FIXED_DP_HEAD}\n"
            ),
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
