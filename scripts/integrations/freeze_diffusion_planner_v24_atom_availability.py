#!/usr/bin/env python3
"""Audit v24 train-only atoms and freeze scales plus the active atom mask."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_CAMP_ATOM_NAMES_V10,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    CANONICAL_ATOM_CONTRACTS,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
TRAIN_SEEDS = (24001, 24002, 24003, 24004, 24005)
SCALE_PERCENTILE = 95.0
SCALE_FLOOR = 1e-6
VARIATION_TOLERANCE = 1e-12
MINIMUM_FREE_BYTES = 10 * 1024**3
FEATURE_FIELDS = frozenset(
    {"atom_matrix", "source_valid_mask", "candidate_row_sha256"}
)
IDENTITY_FIELDS = frozenset(
    {
        "logical_map_sha256",
        "map_id",
        "route_id",
        "route_identity_sha256",
        "route_sha256",
        "group_sha256",
        "corridor_group_sha256",
        "record_key",
        "map_family_id",
        "split",
        "seed",
    }
)
FORBIDDEN_SIDECAR_FIELDS = frozenset(
    {
        "actual_closed_loop_outcome",
        "closed_loop_outcome",
        "outcome",
        "future_label",
        "candidate_cost",
        "oracle_index",
        "safety_cost",
        "collision",
        "near_miss",
        "offroad",
        "red_light_violation",
        "speed_violation",
        "wrong_way",
    }
)
SIDECAR_FIELDS = frozenset(
    {
        "tick_index",
        "route_sha256",
        "default_output_sha256",
        "candidate0_sha256",
        "default_candidate0_identity",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "causal_input_sha256",
        "physical_feasible_mask",
        "all_k_high_risk",
        "offline_label_provenance",
        "logical_map_sha256",
        "route_identity_sha256",
        "group_sha256",
        "split",
        "seed",
        "source_stratum",
        "record_key",
        "map_family_id",
        "corridor_group_sha256",
    }
)
DEFAULT_IDENTITY_FIELDS = frozenset(
    {
        "elementwise_equal",
        "max_abs_difference",
        "candidate0_sha256",
        "default_output_sha256",
        "native_ranked_k8",
    }
)
SOURCE_STRATUM_FIELDS = frozenset(
    {
        "branch_intersection",
        "short_progress_opportunity",
        "tight_corridor",
        "traffic_light",
    }
)
PROVENANCE_FILES = (
    "camp_core/camp_core/integrations/diffusion_planner.py",
    "camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py",
    "camp_core/camp_core/integrations/diffusion_planner_causal_materializer.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v18.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py",
    "scripts/integrations/materialize_diffusion_planner_v22_native_corpus.py",
    "scripts/integrations/prepare_diffusion_planner_v24_native_corpus.py",
    "scripts/integrations/review_diffusion_planner_v24_native_corpus.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v19_worker.py",
    "scripts/integrations/run_diffusion_planner_camp_replay.py",
    "camp_core/camp_core/integrations/diffusion_planner_v19_nuplan_bridge.py",
    "camp_core/camp_core/integrations/diffusion_planner_v21_native.py",
    "camp_core/camp_core/integrations/diffusion_planner_v22_native.py",
)
EXECUTOR_PROVENANCE_FILE = (
    "scripts/integrations/execute_diffusion_planner_v24_native_corpus.py"
)
EXECUTOR_CONTRACT_CLASS = "V24CorpusSnapshotWriter"
EXECUTOR_CONTRACT_METHOD = "__call__"
EXPECTED_ATOM_CONTRACT_SHA256 = (
    "b82b3ffe2579c567ab4460a78d630a9191bd18bea7874e9d85e32d1219bc50de"
)
_SHA256_HEX = frozenset("0123456789abcdef")


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= _SHA256_HEX
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _contains_forbidden_sidecar_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).lower()
            if (
                normalized in FORBIDDEN_SIDECAR_FIELDS
                or "outcome" in normalized
                or "future_label" in normalized
            ):
                return True
            if _contains_forbidden_sidecar_key(nested):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_sidecar_key(item) for item in value)
    return False


def _contract_projection(contracts: Sequence[Any]) -> list[dict[str, Any]]:
    fields = (
        "name",
        "unit",
        "formula",
        "inputs",
        "decision_time_availability",
        "future_dependency",
        "finite_required",
        "nonnegative",
        "depends_on_w",
        "depends_on_rank",
        "depends_on_selected_index",
        "gt_future_allowed",
        "holdout_label_allowed",
        "candidate_index_dependency",
    )
    return [
        {
            field: (
                list(getattr(contract, field))
                if isinstance(getattr(contract, field), tuple)
                else getattr(contract, field)
            )
            for field in fields
        }
        for contract in contracts
    ]


def _validated_atom_contracts(
    contracts: Sequence[Any] = CANONICAL_ATOM_CONTRACTS,
) -> dict[str, Any]:
    projection = _contract_projection(contracts)
    digest = hashlib.sha256(_canonical_json_bytes(projection)).hexdigest()
    if digest != EXPECTED_ATOM_CONTRACT_SHA256:
        raise ValueError("canonical atom causal contract differs from frozen v24 contract")
    by_name = {contract.name: contract for contract in contracts}
    if tuple(by_name) != tuple(DP_CAMP_ATOM_NAMES_V10):
        raise ValueError("canonical atom contract order changed")
    for contract in contracts:
        if (
            contract.finite_required is not True
            or contract.nonnegative is not True
            or contract.depends_on_w is not False
            or contract.depends_on_rank is not False
            or contract.depends_on_selected_index is not False
            or contract.gt_future_allowed is not False
            or contract.holdout_label_allowed is not False
        ):
            raise ValueError("atom causal or holdout boundary is not fail-closed")
    return by_name


def _method_ast_sha256(source: bytes, *, class_name: str, method_name: str) -> str:
    try:
        tree = ast.parse(source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ValueError("executor source cannot be parsed for semantic provenance") from exc
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    item.name == method_name
                ):
                    normalized = ast.dump(item, annotate_fields=True, include_attributes=False)
                    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    raise ValueError("executor semantic contract method is missing")


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _executor_critical_projection(source: bytes, *, legacy_pilot: bool) -> dict[str, str]:
    try:
        tree = ast.parse(source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ValueError("executor source cannot be parsed for critical calls") from exc
    function_name = "execute_pilot_manifest" if legacy_pilot else "_execute_manifest_rows"
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        ),
        None,
    )
    if function is None:
        raise ValueError("executor critical function is missing")
    required = {
        "V24CorpusSnapshotWriter",
        "build_corpus_run_config",
        "validate_v24_corpus_run_config",
        "run_arm",
    }
    calls: dict[str, list[ast.Call]] = {name: [] for name in required}
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and _call_name(node) in calls:
            calls[_call_name(node)].append(node)
    if any(len(items) != 1 for items in calls.values()):
        raise ValueError("executor critical call count changed")
    writer = calls["V24CorpusSnapshotWriter"][0]
    writer_keywords = {item.arg: item.value for item in writer.keywords if item.arg}
    expected_writer_fields = {"route", "output_dir", "seed"}
    if legacy_pilot:
        if set(writer_keywords) != expected_writer_fields:
            raise ValueError("legacy pilot writer call contract changed")
    else:
        phase_value = writer_keywords.pop("phase", None)
        if (
            set(writer_keywords) != expected_writer_fields
            or not isinstance(phase_value, ast.Name)
            or phase_value.id != "phase"
        ):
            raise ValueError("remaining writer phase call contract changed")
    normalized_writer = ast.Call(
        func=ast.Name(id="V24CorpusSnapshotWriter", ctx=ast.Load()),
        args=[],
        keywords=[
            ast.keyword(arg=name, value=writer_keywords[name])
            for name in ("route", "output_dir", "seed")
        ],
    )
    return {
        "writer_inputs": ast.dump(normalized_writer, include_attributes=False),
        "run_config_builder": ast.dump(
            calls["build_corpus_run_config"][0], include_attributes=False
        ),
        "run_config_validator": ast.dump(
            calls["validate_v24_corpus_run_config"][0], include_attributes=False
        ),
        "native_arm_call": ast.dump(calls["run_arm"][0], include_attributes=False),
    }


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            digest, relative = line.split(None, 1)
        except ValueError as exc:
            raise ValueError("invalid SHA256SUMS line") from exc
        relative = relative.strip().removeprefix("./")
        item = Path(relative)
        if (
            not _is_sha256(digest)
            or item.is_absolute()
            or ".." in item.parts
            or item.as_posix() in entries
        ):
            raise ValueError("unsafe or duplicate SHA256SUMS entry")
        entries[item.as_posix()] = digest
    if not entries:
        raise ValueError("SHA256SUMS is empty")
    return entries


def verify_seal(root: Path, expected_root_sha256: str) -> dict[str, str]:
    source = Path(root).resolve()
    if not source.is_dir() or not _is_sha256(expected_root_sha256):
        raise ValueError("sealed artifact root or expected SHA256 is invalid")
    manifest = source / "SHA256SUMS"
    root_receipt = source / "ROOT_SHA256SUMS"
    if not manifest.is_file() or not root_receipt.is_file():
        raise ValueError("sealed artifact receipts are missing")
    if _file_sha256(manifest) != expected_root_sha256:
        raise ValueError("artifact root SHA256 mismatch")
    if root_receipt.read_text(encoding="ascii") != (
        f"{expected_root_sha256}  SHA256SUMS\n"
    ):
        raise ValueError("ROOT_SHA256SUMS receipt mismatch")
    entries = _read_manifest(manifest)
    actual = {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    }
    if actual != set(entries):
        raise ValueError("sealed artifact inventory mismatch")
    for relative, digest in entries.items():
        if _file_sha256(source / relative) != digest:
            raise ValueError(f"sealed artifact file hash mismatch: {relative}")
    return entries


def _heads(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in Path(path).read_text(encoding="ascii").splitlines():
        if not line.strip() or "=" not in line:
            raise ValueError("HEADS line is invalid")
        key, value = line.split("=", 1)
        if not key or key in result or not value:
            raise ValueError("HEADS key is invalid or duplicated")
        result[key] = value
    return result


def _require_execution_receipt(root: Path) -> None:
    if (
        (root / "run.exit").read_text(encoding="ascii") != "0\n"
        or (root / "stderr.txt").read_text(encoding="utf-8") != ""
    ):
        raise ValueError("source artifact execution receipt is not clean")


def _git_blob(repo: Path, head: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(result) != 40 or set(result) - _SHA256_HEX:
        raise ValueError("git blob identity is invalid")
    return result


def _git_blob_bytes(repo: Path, head: str, relative: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


def _require_clean_git_state(repo: Path, expected_head: str) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tracked = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if head != expected_head or tracked:
        raise ValueError("live CAMP HEAD or tracked state differs from freeze authority")


def source_provenance(
    *,
    repo: Path,
    pilot_head: str,
    remaining_head: str,
    current_head: str,
    blob_resolver: Callable[[Path, str, str], str] = _git_blob,
    blob_bytes_resolver: Callable[[Path, str, str], bytes] = _git_blob_bytes,
) -> dict[str, Any]:
    if any(len(head) != 40 or set(head) - _SHA256_HEX for head in (
        pilot_head,
        remaining_head,
        current_head,
    )):
        raise ValueError("CAMP provenance head is invalid")
    result: dict[str, Any] = {
        "pilot_camp_head": pilot_head,
        "remaining_camp_head": remaining_head,
        "freeze_camp_head": current_head,
        "files": {},
    }
    for relative in PROVENANCE_FILES:
        blobs = {
            "pilot": blob_resolver(Path(repo), pilot_head, relative),
            "remaining": blob_resolver(Path(repo), remaining_head, relative),
            "freeze": blob_resolver(Path(repo), current_head, relative),
        }
        blob_sha256 = {
            phase: hashlib.sha256(
                blob_bytes_resolver(Path(repo), head, relative)
            ).hexdigest()
            for phase, head in (
                ("pilot", pilot_head),
                ("remaining", remaining_head),
                ("freeze", current_head),
            )
        }
        live_sha256 = _file_sha256(Path(repo) / relative)
        if (
            len(set(blobs.values())) != 1
            or len(set(blob_sha256.values())) != 1
            or blob_sha256["freeze"] != live_sha256
        ):
            raise ValueError(f"atom provenance source drift: {relative}")
        result["files"][relative] = {
            "git_blob": blobs["freeze"],
            "git_blob_sha256": blob_sha256["freeze"],
            "sha256": live_sha256,
            "live_file_matches_freeze_git_blob": True,
            "identical_across_pilot_remaining_freeze": True,
        }
    executor_blobs = {
        phase: blob_resolver(Path(repo), head, EXECUTOR_PROVENANCE_FILE)
        for phase, head in (
            ("pilot", pilot_head),
            ("remaining", remaining_head),
            ("freeze", current_head),
        )
    }
    executor_sources = {
        phase: blob_bytes_resolver(Path(repo), head, EXECUTOR_PROVENANCE_FILE)
        for phase, head in (
            ("pilot", pilot_head),
            ("remaining", remaining_head),
            ("freeze", current_head),
        )
    }
    executor_source_sha256 = {
        phase: hashlib.sha256(source).hexdigest()
        for phase, source in executor_sources.items()
    }
    method_ast_sha256 = {
        phase: _method_ast_sha256(
            source,
            class_name=EXECUTOR_CONTRACT_CLASS,
            method_name=EXECUTOR_CONTRACT_METHOD,
        )
        for phase, source in executor_sources.items()
    }
    critical_projections = {
        phase: _executor_critical_projection(
            source, legacy_pilot=phase == "pilot"
        )
        for phase, source in executor_sources.items()
    }
    critical_projection_sha256 = {
        phase: hashlib.sha256(_canonical_json_bytes(projection)).hexdigest()
        for phase, projection in critical_projections.items()
    }
    live_executor_sha256 = _file_sha256(Path(repo) / EXECUTOR_PROVENANCE_FILE)
    if (
        len(set(method_ast_sha256.values())) != 1
        or len(set(critical_projection_sha256.values())) != 1
        or executor_source_sha256["freeze"] != live_executor_sha256
    ):
        raise ValueError("v24 executor snapshot-writer semantic contract drift")
    result["execution_semantic_contract"] = {
        "file": EXECUTOR_PROVENANCE_FILE,
        "class": EXECUTOR_CONTRACT_CLASS,
        "method": EXECUTOR_CONTRACT_METHOD,
        "git_blobs": executor_blobs,
        "source_sha256": executor_source_sha256,
        "method_ast_sha256": method_ast_sha256["freeze"],
        "method_identical_across_pilot_remaining_freeze": True,
        "critical_call_projection_sha256": critical_projection_sha256["freeze"],
        "critical_call_projection_identical_across_pilot_remaining_freeze": True,
        "critical_call_contract": {
            "arm": "camp",
            "max_steps": 64,
            "decision_sink": "V24CorpusSnapshotWriter",
            "config_builder_and_validator_frozen": True,
            "snapshot_sampling_implementation_frozen_by_provenance_file": (
                "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py"
            ),
        },
        "freeze_live_file_matches_git_blob": True,
        "allowed_noncontract_executor_drift": (
            "phase seed enumeration, resume receipts, progress summaries, and locks; "
            "sealed merged indexes and upstream independent review bind those outputs"
        ),
    }
    return result


def _validate_merged_authority(
    *,
    merged_root: Path,
    expected_merged_root_sha256: str,
    merged_review_root: Path,
    expected_merged_review_root_sha256: str,
    expected_snapshot_count: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, str]]]:
    inventories = {
        "merged": verify_seal(merged_root, expected_merged_root_sha256),
        "merged_review": verify_seal(
            merged_review_root, expected_merged_review_root_sha256
        ),
    }
    _require_execution_receipt(Path(merged_root))
    _require_execution_receipt(Path(merged_review_root))
    summary = _read_json(Path(merged_root) / "merged_summary.json")
    review = _read_json(Path(merged_review_root) / "review.json")
    if (
        summary.get("schema")
        != "camp_dp_v24_native_corpus_merged_train_index_v1"
        or summary.get("status") != "passed"
        or summary.get("phase") != "merged_train_corpus_assembly_only"
        or summary.get("split") != "train"
        or summary.get("snapshot_count") != expected_snapshot_count
        or summary.get("snapshot_index_row_count") != expected_snapshot_count
        or summary.get("snapshot_payloads_copied") is not False
        or summary.get("snapshot_payloads_modified") is not False
        or summary.get("route_or_seed_removed_replaced_or_reordered") is not False
        or summary.get("assembly_only") is not True
        or summary.get("model_loaded") is not False
        or summary.get("simulator_executed") is not False
        or summary.get("candidate_generation_started") is not False
        or summary.get("training_executed") is not False
        or summary.get("tuning_executed") is not False
        or summary.get("outcome_fields_consumed") != []
        or summary.get("calibration_accessed") is not False
        or summary.get("holdout_opened") is not False
        or summary.get("claim_authorized") is not False
    ):
        raise ValueError("merged corpus authority is invalid or not train-only")
    decision = review.get("decision")
    checks = review.get("checks")
    check_count = review.get("check_count")
    failed_count = review.get("failed_count")
    if (
        review.get("schema")
        != "camp_dp_v24_native_corpus_merged_independent_review_v1"
        or review.get("status") != "passed"
        or review.get("source_assembly_root_sha256")
        != expected_merged_root_sha256
        or review.get("fixed_dp_head") != FIXED_DP_HEAD
        or isinstance(check_count, bool)
        or not isinstance(check_count, int)
        or check_count <= 0
        or not isinstance(checks, list)
        or check_count != len(checks)
        or isinstance(failed_count, bool)
        or not isinstance(failed_count, int)
        or failed_count != 0
        or review.get("failed_checks") != []
        or any(
            not isinstance(check, Mapping) or check.get("passed") is not True
            for check in checks
        )
        or not isinstance(decision, Mapping)
        or decision.get("action")
        != "review_atom_availability_and_freeze_train_only_mask"
        or decision.get("atom_availability_review_authorized") is not True
        or decision.get("training_authorized") is not False
        or decision.get("tuning_authorized") is not False
        or decision.get("outcome_access_authorized") is not False
        or decision.get("calibration_access_authorized") is not False
        or decision.get("holdout_access_authorized") is not False
        or decision.get("claim_authorized") is not False
        or review.get("training_executed") is not False
        or review.get("review_only") is not True
        or review.get("model_loaded") is not False
        or "simulator_executed" in review
        or review.get("candidate_generation_started") is not False
        or review.get("tuning_executed") is not False
        or review.get("outcome_accessed") is not False
        or review.get("calibration_accessed") is not False
        or review.get("holdout_opened") is not False
        or review.get("claim_authorized") is not False
        or review.get("next_work_target")
        != "v24_native_corpus_atom_availability_and_freeze_review_only"
    ):
        raise ValueError("merged independent review does not authorize atom freeze")
    return summary, review, inventories


def _validate_snapshot(
    payload: Mapping[str, Any], *, phase: str, expected_sha256: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if payload.get("schema_version") != "v22_native_decision_snapshot_v1":
        raise ValueError("decision snapshot schema mismatch")
    features = payload.get("feature_payload")
    sidecar = payload.get("sidecar")
    if (
        not isinstance(features, Mapping)
        or set(features) != FEATURE_FIELDS
        or IDENTITY_FIELDS.intersection(features)
        or not isinstance(sidecar, Mapping)
        or set(sidecar) != SIDECAR_FIELDS
        or sidecar.get("split") != "train"
        or _contains_forbidden_sidecar_key(sidecar)
    ):
        raise ValueError("train snapshot feature or sidecar boundary mismatch")
    atoms = np.asarray(features["atom_matrix"], dtype=np.float64)
    valid_raw = features["source_valid_mask"]
    physical_raw = sidecar.get("physical_feasible_mask")
    rows = features["candidate_row_sha256"]
    if (
        atoms.shape != (8, 14)
        or not np.isfinite(atoms).all()
        or np.any(atoms < 0.0)
        or not isinstance(valid_raw, list)
        or len(valid_raw) != 8
        or any(not isinstance(value, bool) for value in valid_raw)
        or not any(valid_raw)
        or not isinstance(physical_raw, list)
        or len(physical_raw) != 8
        or any(not isinstance(value, bool) for value in physical_raw)
        or not isinstance(rows, list)
        or len(rows) != 8
        or any(not _is_sha256(value) for value in rows)
    ):
        raise ValueError("snapshot atoms, masks, or candidate row hashes are invalid")
    seed = sidecar.get("seed")
    allowed_seeds = {24001} if phase == "pilot" else set(TRAIN_SEEDS[1:])
    if isinstance(seed, bool) or seed not in allowed_seeds:
        raise ValueError("snapshot seed is outside the frozen phase namespace")
    tick_index = sidecar.get("tick_index")
    source_stratum = sidecar.get("source_stratum")
    if (
        isinstance(tick_index, bool)
        or not isinstance(tick_index, int)
        or not 0 <= tick_index < 64
        or not isinstance(source_stratum, Mapping)
        or set(source_stratum) != SOURCE_STRATUM_FIELDS
        or any(
            not isinstance(key, str) or not isinstance(value, bool)
            for key, value in source_stratum.items()
        )
    ):
        raise ValueError("snapshot cadence or source-stratum receipt is invalid")
    for name in (
        "logical_map_sha256",
        "route_identity_sha256",
        "group_sha256",
        "corridor_group_sha256",
        "route_sha256",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "candidate0_sha256",
        "default_output_sha256",
        "causal_input_sha256",
    ):
        if not _is_sha256(sidecar.get(name)):
            raise ValueError(f"snapshot {name} is invalid")
    identity = sidecar.get("default_candidate0_identity")
    if (
        sidecar["candidate_tensor_sha256_before"]
        != sidecar["candidate_tensor_sha256_after"]
        or sidecar["candidate0_sha256"] != rows[0]
        or sidecar["default_output_sha256"] != rows[0]
        or not isinstance(identity, Mapping)
        or set(identity) != DEFAULT_IDENTITY_FIELDS
        or identity.get("elementwise_equal") is not True
        or identity.get("max_abs_difference") != 0.0
        or identity.get("candidate0_sha256") != rows[0]
        or identity.get("default_output_sha256") != rows[0]
        or identity.get("native_ranked_k8") is not False
        or sidecar.get("offline_label_provenance")
        != "pending_train_only_offline_supervision_sidecar"
        or not isinstance(sidecar.get("all_k_high_risk"), bool)
    ):
        raise ValueError("candidate immutability or candidate-0 identity failed")
    if not _is_sha256(expected_sha256):
        raise ValueError("snapshot index SHA256 is invalid")
    return (
        atoms,
        np.asarray(valid_raw, dtype=bool),
        np.asarray(physical_raw, dtype=bool),
    )


def compute_atom_statistics(
    atoms: np.ndarray,
    source_valid: np.ndarray,
) -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray]:
    matrix = np.asarray(atoms, dtype=np.float64)
    valid = np.asarray(source_valid, dtype=bool)
    if (
        matrix.ndim != 3
        or matrix.shape[1:] != (8, 14)
        or valid.shape != matrix.shape[:2]
        or not np.isfinite(matrix).all()
        or np.any(matrix < 0.0)
        or not valid.any(axis=1).all()
    ):
        raise ValueError("train atom matrix or source-valid mask is invalid")
    valid_values = matrix[valid]
    scales = np.maximum(
        np.percentile(valid_values, SCALE_PERCENTILE, axis=0), SCALE_FLOOR
    )
    variable_counts = np.zeros(14, dtype=np.int64)
    for snapshot, mask in zip(matrix, valid):
        values = snapshot[mask]
        if values.shape[0] >= 2:
            variable_counts += np.ptp(values, axis=0) > VARIATION_TOLERANCE
    active = variable_counts > 0
    if not active.any():
        raise ValueError("train corpus has no source-valid nonconstant atom")
    contracts = _validated_atom_contracts()
    stats: list[dict[str, Any]] = []
    for index, name in enumerate(DP_CAMP_ATOM_NAMES_V10):
        values = valid_values[:, index]
        contract = contracts[name]
        is_active = bool(active[index])
        stats.append(
            {
                "index": index,
                "name": name,
                "unit": contract.unit,
                "formula": contract.formula,
                "inputs": list(contract.inputs),
                "decision_time_availability": contract.decision_time_availability,
                "future_dependency": contract.future_dependency,
                "finite_required": contract.finite_required,
                "nonnegative": contract.nonnegative,
                "depends_on_w": contract.depends_on_w,
                "depends_on_rank": contract.depends_on_rank,
                "depends_on_selected_index": contract.depends_on_selected_index,
                "gt_future_allowed": contract.gt_future_allowed,
                "holdout_label_allowed": contract.holdout_label_allowed,
                "candidate_index_dependency": contract.candidate_index_dependency,
                "source_available": True,
                "source_availability_proof": (
                    "canonical materializer emitted the sealed finite 14D matrix only "
                    "after require_canonical_schema accepted every decision-time source"
                ),
                "source_valid_value_count": int(values.size),
                "finite_value_count": int(np.isfinite(values).sum()),
                "nonnegative_value_count": int(np.sum(values >= 0.0)),
                "zero_value_count": int(np.sum(values == 0.0)),
                "positive_value_count": int(np.sum(values > 0.0)),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
                "mean": float(np.mean(values)),
                "standard_deviation": float(np.std(values)),
                "p50": float(np.percentile(values, 50.0)),
                "p95": float(np.percentile(values, SCALE_PERCENTILE)),
                "scale": float(scales[index]),
                "variable_snapshot_count": int(variable_counts[index]),
                "train_only_nonconstant": is_active,
                "active": is_active,
                "exclusion_reason": (
                    None
                    if is_active
                    else "no_source_valid_cross_candidate_range_above_1e-12"
                ),
            }
        )
    return stats, scales, active


def _load_train_snapshots(
    *,
    merged_root: Path,
    summary: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any], dict[str, dict[str, str]]]:
    sources = summary.get("source_artifacts")
    if not isinstance(sources, Mapping):
        raise ValueError("merged source artifact map is missing")
    source_roots: dict[str, Path] = {}
    source_inventories: dict[str, dict[str, str]] = {}
    for name in ("pilot", "pilot_review", "remaining", "remaining_review"):
        source = sources.get(name)
        if not isinstance(source, Mapping):
            raise ValueError(f"merged source artifact {name} is missing")
        root = Path(str(source.get("path"))).resolve()
        digest = source.get("root_sha256")
        source_roots[name] = root
        source_inventories[name] = verify_seal(root, digest)
        _require_execution_receipt(root)
    index_path = Path(merged_root) / "snapshot_index.jsonl"
    index_bytes = index_path.read_bytes()
    if (
        hashlib.sha256(index_bytes).hexdigest()
        != summary.get("snapshot_index_sha256")
    ):
        raise ValueError("merged snapshot index SHA256 mismatch")
    rows = [json.loads(line) for line in index_bytes.splitlines() if line.strip()]
    count = int(summary["snapshot_count"])
    if len(rows) != count:
        raise ValueError("merged snapshot index count mismatch")
    atoms = np.empty((count, 8, 14), dtype=np.float64)
    source_valid = np.empty((count, 8), dtype=bool)
    physical = np.empty((count, 8), dtype=bool)
    seen: set[str] = set()
    prior_order: tuple[str, str] | None = None
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != {
            "phase",
            "relative_path",
            "sha256",
        }:
            raise ValueError("snapshot index row schema mismatch")
        phase = row["phase"]
        digest = row["sha256"]
        relative = Path(str(row["relative_path"]))
        order = (str(digest), str(phase))
        if (
            phase not in {"pilot", "remaining"}
            or not _is_sha256(digest)
            or relative.as_posix() != f"snapshots/{digest}.json"
            or relative.is_absolute()
            or ".." in relative.parts
            or digest in seen
            or (prior_order is not None and order <= prior_order)
        ):
            raise ValueError("snapshot index identity, path, or order mismatch")
        seen.add(digest)
        prior_order = order
        source_path = source_roots[str(phase)] / relative
        content = source_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("snapshot content address mismatch")
        payload = json.loads(content)
        atoms[index], source_valid[index], physical[index] = _validate_snapshot(
            payload, phase=str(phase), expected_sha256=str(digest)
        )
    receipt = {
        "snapshot_count": count,
        "candidate_count": count * 8,
        "source_valid_candidate_count": int(source_valid.sum()),
        "source_invalid_candidate_count": int(source_valid.size - source_valid.sum()),
        "physical_feasible_candidate_count": int(physical.sum()),
        "all_k_high_risk_snapshot_count": int(
            np.sum(source_valid.all(axis=1) & ~physical.any(axis=1))
        ),
        "candidate_tensor_immutability_count": count,
        "candidate0_default_identity_count": count,
        "feature_identity_field_count": 0,
        "outcome_field_count": 0,
    }
    return atoms, source_valid, physical, receipt, source_inventories


def freeze_atom_availability(
    *,
    merged_root: Path,
    expected_merged_root_sha256: str,
    merged_review_root: Path,
    expected_merged_review_root_sha256: str,
    repo: Path,
    expected_camp_head: str,
    output_dir: Path,
    blob_resolver: Callable[[Path, str, str], str] = _git_blob,
    blob_bytes_resolver: Callable[[Path, str, str], bytes] = _git_blob_bytes,
    git_state_checker: Callable[[Path, str], None] = _require_clean_git_state,
    free_bytes: Callable[[], int] | None = None,
    expected_snapshot_count: int = 67796,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"evidence target already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    available = (
        int(free_bytes())
        if free_bytes is not None
        else int(shutil.disk_usage(output.parent).free)
    )
    if available <= MINIMUM_FREE_BYTES:
        raise RuntimeError("10 GiB disk floor is not available")
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if current_head != expected_camp_head:
        raise ValueError("live CAMP HEAD differs from expected freeze HEAD")
    git_state_checker(Path(repo), expected_camp_head)
    summary, _review, inventories = _validate_merged_authority(
        merged_root=merged_root,
        expected_merged_root_sha256=expected_merged_root_sha256,
        merged_review_root=merged_review_root,
        expected_merged_review_root_sha256=expected_merged_review_root_sha256,
        expected_snapshot_count=expected_snapshot_count,
    )
    atoms, source_valid, _physical, corpus_receipt, source_inventories = (
        _load_train_snapshots(merged_root=merged_root, summary=summary)
    )
    source_heads = {
        name: _heads(Path(summary["source_artifacts"][name]["path"]) / "HEADS")
        for name in ("pilot", "remaining")
    }
    if any(
        heads.get("FIXED_DP_HEAD") != FIXED_DP_HEAD
        for heads in source_heads.values()
    ):
        raise ValueError("source corpus fixed DP HEAD drifted")
    provenance = source_provenance(
        repo=repo,
        pilot_head=source_heads["pilot"]["CAMP_HEAD"],
        remaining_head=source_heads["remaining"]["CAMP_HEAD"],
        current_head=current_head,
        blob_resolver=blob_resolver,
        blob_bytes_resolver=blob_bytes_resolver,
    )
    stats, scales, active = compute_atom_statistics(atoms, source_valid)
    active_names = [
        name for name, enabled in zip(DP_CAMP_ATOM_NAMES_V10, active) if enabled
    ]
    excluded_names = [
        name for name, enabled in zip(DP_CAMP_ATOM_NAMES_V10, active) if not enabled
    ]
    result = {
        "schema": "camp_dp_v24_train_atom_availability_freeze_v1",
        "status": "passed",
        "split": "train",
        "source_merged_root_sha256": expected_merged_root_sha256,
        "source_merged_review_root_sha256": expected_merged_review_root_sha256,
        "fixed_dp_head": FIXED_DP_HEAD,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "atom_names": list(DP_CAMP_ATOM_NAMES_V10),
        "atom_count": 14,
        "atom_contract_projection_sha256": EXPECTED_ATOM_CONTRACT_SHA256,
        "corpus_receipt": corpus_receipt,
        "scale_rule": {
            "scope": "source_valid_train_candidates_only",
            "percentile": SCALE_PERCENTILE,
            "floor": SCALE_FLOOR,
        },
        "variation_rule": {
            "scope": "within_tick_source_valid_candidates_only",
            "cross_candidate_range_strictly_greater_than": VARIATION_TOLERANCE,
            "active_requires_any_variable_train_snapshot": True,
        },
        "atom_scales": scales.tolist(),
        "active_atom_mask": active.tolist(),
        "active_atom_names": active_names,
        "excluded_atom_names": excluded_names,
        "atom_statistics": stats,
        "source_provenance": provenance,
        "verified_file_counts": {
            **{name: len(files) for name, files in inventories.items()},
            **{name: len(files) for name, files in source_inventories.items()},
        },
        "score_contract": "score_k(w)=a_k^T w",
        "weight_domain": "nonnegative_simplex_over_active_atoms_only",
        "inactive_atom_weight_rule": "explicit_exact_zero_not_silent",
        "active_mask_selected_from": (
            "causal_source_availability_and_train_only_cross_candidate_variance"
        ),
        "calibration_or_holdout_used_for_mask": False,
        "snapshot_payloads_modified": False,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_fields_consumed": [],
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "independent_review_authorized": True,
        "training_plan_authorized": False,
        "training_execution_authorized": False,
        "free_disk_gib": available / (1024**3),
        "minimum_free_disk_gib": 10,
        "next_work_target": (
            "v24_native_corpus_atom_availability_freeze_independent_review_only"
        ),
    }
    output.mkdir()
    (output / "atom_freeze.json").write_bytes(_canonical_json_bytes(result))
    return result


def seal_artifact(root: Path) -> str:
    source = Path(root)
    files = sorted(
        path
        for path in source.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    (source / "SHA256SUMS").write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(source).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(source / "SHA256SUMS")
    (source / "ROOT_SHA256SUMS").write_text(
        f"{digest}  SHA256SUMS\n", encoding="ascii"
    )
    return digest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merged-root", type=Path, required=True)
    parser.add_argument("--expected-merged-root-sha256", required=True)
    parser.add_argument("--merged-review-root", type=Path, required=True)
    parser.add_argument("--expected-merged-review-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--expected-snapshot-count", type=int, default=67796)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = freeze_atom_availability(
        merged_root=args.merged_root,
        expected_merged_root_sha256=args.expected_merged_root_sha256,
        merged_review_root=args.merged_review_root,
        expected_merged_review_root_sha256=args.expected_merged_review_root_sha256,
        repo=ROOT,
        expected_camp_head=args.camp_head,
        output_dir=args.output_dir,
        expected_snapshot_count=args.expected_snapshot_count,
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_MERGED_ROOT_SHA256={args.expected_merged_root_sha256}\n"
        "SOURCE_MERGED_REVIEW_ROOT_SHA256="
        f"{args.expected_merged_review_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 train-only atom availability and active-mask freeze\n",
        encoding="utf-8",
    )
    (args.output_dir / "atom_freeze.md").write_text(
        "# v24 train-only atom availability freeze\n\n"
        f"- status: `{result['status']}`\n"
        f"- snapshots: `{result['corpus_receipt']['snapshot_count']}`\n"
        f"- active / excluded atoms: `{len(result['active_atom_names'])} / "
        f"{len(result['excluded_atom_names'])}`\n"
        f"- active atoms: `{', '.join(result['active_atom_names'])}`\n"
        f"- excluded atoms: `{', '.join(result['excluded_atom_names'])}`\n"
        "- training / outcomes / calibration / holdout / claim: "
        "`false/false/false/false/false`\n",
        encoding="utf-8",
    )
    stdout = json.dumps(result, sort_keys=True, allow_nan=False) + "\n"
    (args.output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root_sha256 = seal_artifact(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha256,
                "status": result["status"],
                "snapshot_count": result["corpus_receipt"]["snapshot_count"],
                "active_atom_count": len(result["active_atom_names"]),
                "excluded_atom_count": len(result["excluded_atom_names"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
