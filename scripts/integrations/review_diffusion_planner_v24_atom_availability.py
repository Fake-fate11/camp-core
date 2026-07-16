#!/usr/bin/env python3
"""Independently recompute the v24 train-only atom availability freeze."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
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
SCALE_PERCENTILE = 95.0
SCALE_FLOOR = 1e-6
VARIATION_TOLERANCE = 1e-12
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
EXPECTED_ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
EXPECTED_ATOM_CONTRACT_SHA256 = (
    "b82b3ffe2579c567ab4460a78d630a9191bd18bea7874e9d85e32d1219bc50de"
)
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


def _independently_validated_contracts() -> dict[str, Any]:
    projection = _contract_projection(CANONICAL_ATOM_CONTRACTS)
    digest = hashlib.sha256(_canonical_json_bytes(projection)).hexdigest()
    if (
        tuple(DP_CAMP_ATOM_NAMES_V10) != EXPECTED_ATOM_NAMES
        or tuple(contract.name for contract in CANONICAL_ATOM_CONTRACTS)
        != EXPECTED_ATOM_NAMES
        or digest != EXPECTED_ATOM_CONTRACT_SHA256
    ):
        raise ValueError("live atom contract differs from independent v24 freeze")
    for contract in CANONICAL_ATOM_CONTRACTS:
        if (
            contract.finite_required is not True
            or contract.nonnegative is not True
            or contract.depends_on_w is not False
            or contract.depends_on_rank is not False
            or contract.depends_on_selected_index is not False
            or contract.gt_future_allowed is not False
            or contract.holdout_label_allowed is not False
        ):
            raise ValueError("independent causal or holdout boundary failed")
    return {contract.name: contract for contract in CANONICAL_ATOM_CONTRACTS}


def _method_ast_sha256(source: bytes, *, class_name: str, method_name: str) -> str:
    try:
        tree = ast.parse(source.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ValueError("executor semantic provenance source is invalid") from exc
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    item.name == method_name
                ):
                    normalized = ast.dump(item, annotate_fields=True, include_attributes=False)
                    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    raise ValueError("executor semantic contract method is absent")


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
        raise ValueError("independent executor critical source is invalid") from exc
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
        raise ValueError("independent executor critical function is absent")
    names = {
        "V24CorpusSnapshotWriter",
        "build_corpus_run_config",
        "validate_v24_corpus_run_config",
        "run_arm",
    }
    calls: dict[str, list[ast.Call]] = {name: [] for name in names}
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and _call_name(node) in calls:
            calls[_call_name(node)].append(node)
    if any(len(items) != 1 for items in calls.values()):
        raise ValueError("independent executor critical call count changed")
    writer = calls["V24CorpusSnapshotWriter"][0]
    keywords = {item.arg: item.value for item in writer.keywords if item.arg}
    fields = {"route", "output_dir", "seed"}
    if legacy_pilot:
        if set(keywords) != fields:
            raise ValueError("independent legacy writer call changed")
    else:
        phase_value = keywords.pop("phase", None)
        if (
            set(keywords) != fields
            or not isinstance(phase_value, ast.Name)
            or phase_value.id != "phase"
        ):
            raise ValueError("independent remaining writer phase call changed")
    normalized_writer = ast.Call(
        func=ast.Name(id="V24CorpusSnapshotWriter", ctx=ast.Load()),
        args=[],
        keywords=[
            ast.keyword(arg=name, value=keywords[name])
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


def _manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split(None, 1)
        relative = relative.strip()
        if relative.startswith("./"):
            relative = relative[2:]
        item = Path(relative)
        normalized = item.as_posix()
        if (
            not _is_sha256(digest)
            or item.is_absolute()
            or ".." in item.parts
            or normalized in entries
        ):
            raise ValueError("invalid SHA256SUMS entry")
        entries[normalized] = digest
    if not entries:
        raise ValueError("empty SHA256SUMS")
    return entries


def _verify_seal(root: Path, expected: str) -> dict[str, str]:
    source = Path(root).resolve()
    if not source.is_dir() or not _is_sha256(expected):
        raise ValueError("invalid sealed source")
    sums = source / "SHA256SUMS"
    receipt = source / "ROOT_SHA256SUMS"
    if (
        _file_sha256(sums) != expected
        or receipt.read_text(encoding="ascii") != f"{expected}  SHA256SUMS\n"
    ):
        raise ValueError("sealed root receipt mismatch")
    entries = _manifest(sums)
    actual = {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    }
    if actual != set(entries):
        raise ValueError("sealed inventory mismatch")
    for relative, digest in entries.items():
        if _file_sha256(source / relative) != digest:
            raise ValueError("sealed file hash mismatch")
    return entries


def _heads(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in Path(path).read_text(encoding="ascii").splitlines():
        key, value = line.split("=", 1)
        if not key or not value or key in result:
            raise ValueError("invalid HEADS receipt")
        result[key] = value
    return result


def _clean_execution(root: Path) -> bool:
    return (
        (root / "run.exit").read_text(encoding="ascii") == "0\n"
        and (root / "stderr.txt").read_text(encoding="utf-8") == ""
    )


def _snapshot_arrays(
    *, merged_root: Path, summary: Mapping[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, dict[str, str]]]:
    sources = summary["source_artifacts"]
    roots: dict[str, Path] = {}
    inventories: dict[str, dict[str, str]] = {}
    for name in ("pilot", "pilot_review", "remaining", "remaining_review"):
        source = sources[name]
        roots[name] = Path(source["path"]).resolve()
        inventories[name] = _verify_seal(roots[name], source["root_sha256"])
        if not _clean_execution(roots[name]):
            raise ValueError("unclean source execution receipt")
    index_bytes = (Path(merged_root) / "snapshot_index.jsonl").read_bytes()
    if hashlib.sha256(index_bytes).hexdigest() != summary["snapshot_index_sha256"]:
        raise ValueError("snapshot index hash mismatch")
    rows = [json.loads(line) for line in index_bytes.splitlines() if line.strip()]
    if len(rows) != summary["snapshot_count"]:
        raise ValueError("snapshot index count mismatch")
    atoms = np.empty((len(rows), 8, 14), dtype=np.float64)
    valid = np.empty((len(rows), 8), dtype=bool)
    physical = np.empty((len(rows), 8), dtype=bool)
    seen: set[str] = set()
    previous: tuple[str, str] | None = None
    for index, row in enumerate(rows):
        if set(row) != {"phase", "relative_path", "sha256"}:
            raise ValueError("snapshot index schema mismatch")
        phase = row["phase"]
        digest = row["sha256"]
        relative = Path(row["relative_path"])
        order = (digest, phase)
        if (
            phase not in {"pilot", "remaining"}
            or not _is_sha256(digest)
            or relative.as_posix() != f"snapshots/{digest}.json"
            or digest in seen
            or (previous is not None and order <= previous)
        ):
            raise ValueError("snapshot index identity mismatch")
        seen.add(digest)
        previous = order
        content = (roots[phase] / relative).read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError("snapshot content address mismatch")
        payload = json.loads(content)
        features = payload.get("feature_payload")
        sidecar = payload.get("sidecar")
        if (
            payload.get("schema_version") != "v22_native_decision_snapshot_v1"
            or not isinstance(features, Mapping)
            or set(features) != FEATURE_FIELDS
            or IDENTITY_FIELDS.intersection(features)
            or not isinstance(sidecar, Mapping)
            or set(sidecar) != SIDECAR_FIELDS
            or sidecar.get("split") != "train"
            or _contains_forbidden_sidecar_key(sidecar)
        ):
            raise ValueError("snapshot schema or feature boundary mismatch")
        matrix = np.asarray(features["atom_matrix"], dtype=np.float64)
        valid_raw = features["source_valid_mask"]
        physical_raw = sidecar.get("physical_feasible_mask")
        candidate_rows = features["candidate_row_sha256"]
        if (
            matrix.shape != (8, 14)
            or not np.isfinite(matrix).all()
            or np.any(matrix < 0.0)
            or not isinstance(valid_raw, list)
            or len(valid_raw) != 8
            or any(not isinstance(value, bool) for value in valid_raw)
            or not any(valid_raw)
            or not isinstance(physical_raw, list)
            or len(physical_raw) != 8
            or any(not isinstance(value, bool) for value in physical_raw)
            or not isinstance(candidate_rows, list)
            or len(candidate_rows) != 8
            or any(not _is_sha256(value) for value in candidate_rows)
        ):
            raise ValueError("snapshot atoms or masks invalid")
        expected_seeds = {24001} if phase == "pilot" else {24002, 24003, 24004, 24005}
        seed = sidecar.get("seed")
        tick_index = sidecar.get("tick_index")
        source_stratum = sidecar.get("source_stratum")
        if (
            isinstance(seed, bool)
            or seed not in expected_seeds
            or isinstance(tick_index, bool)
            or not isinstance(tick_index, int)
            or not 0 <= tick_index < 64
            or not isinstance(source_stratum, Mapping)
            or set(source_stratum) != SOURCE_STRATUM_FIELDS
            or any(
                not isinstance(key, str) or not isinstance(value, bool)
                for key, value in source_stratum.items()
            )
        ):
            raise ValueError("snapshot phase seed mismatch")
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
                raise ValueError("snapshot identity receipt invalid")
        identity = sidecar.get("default_candidate0_identity")
        if (
            sidecar["candidate_tensor_sha256_before"]
            != sidecar["candidate_tensor_sha256_after"]
            or sidecar["candidate0_sha256"] != candidate_rows[0]
            or sidecar["default_output_sha256"] != candidate_rows[0]
            or not isinstance(identity, Mapping)
            or set(identity) != DEFAULT_IDENTITY_FIELDS
            or identity.get("elementwise_equal") is not True
            or identity.get("max_abs_difference") != 0.0
            or identity.get("candidate0_sha256") != candidate_rows[0]
            or identity.get("default_output_sha256") != candidate_rows[0]
            or identity.get("native_ranked_k8") is not False
            or sidecar.get("offline_label_provenance")
            != "pending_train_only_offline_supervision_sidecar"
        ):
            raise ValueError("snapshot candidate identity mismatch")
        atoms[index] = matrix
        valid[index] = np.asarray(valid_raw, dtype=bool)
        physical[index] = np.asarray(physical_raw, dtype=bool)
    return atoms, valid, physical, inventories


def _recomputed_stats(
    atoms: np.ndarray, valid: np.ndarray
) -> tuple[list[dict[str, Any]], list[float], list[bool]]:
    values = atoms[valid]
    scales = np.maximum(
        np.percentile(values, SCALE_PERCENTILE, axis=0), SCALE_FLOOR
    )
    variable = np.zeros(14, dtype=np.int64)
    for snapshot, mask in zip(atoms, valid):
        selected = snapshot[mask]
        if selected.shape[0] >= 2:
            variable += np.ptp(selected, axis=0) > VARIATION_TOLERANCE
    active = variable > 0
    if not active.any():
        raise ValueError("train corpus has no source-valid nonconstant atom")
    contracts = _independently_validated_contracts()
    stats = []
    for index, name in enumerate(DP_CAMP_ATOM_NAMES_V10):
        atom = values[:, index]
        contract = contracts[name]
        enabled = bool(active[index])
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
                "source_valid_value_count": int(atom.size),
                "finite_value_count": int(np.isfinite(atom).sum()),
                "nonnegative_value_count": int(np.sum(atom >= 0.0)),
                "zero_value_count": int(np.sum(atom == 0.0)),
                "positive_value_count": int(np.sum(atom > 0.0)),
                "minimum": float(np.min(atom)),
                "maximum": float(np.max(atom)),
                "mean": float(np.mean(atom)),
                "standard_deviation": float(np.std(atom)),
                "p50": float(np.percentile(atom, 50.0)),
                "p95": float(np.percentile(atom, SCALE_PERCENTILE)),
                "scale": float(scales[index]),
                "variable_snapshot_count": int(variable[index]),
                "train_only_nonconstant": enabled,
                "active": enabled,
                "exclusion_reason": (
                    None
                    if enabled
                    else "no_source_valid_cross_candidate_range_above_1e-12"
                ),
            }
        )
    return stats, scales.tolist(), active.tolist()


def _source_provenance(
    *,
    repo: Path,
    pilot_head: str,
    remaining_head: str,
    freeze_head: str,
    blob_resolver: Callable[[Path, str, str], str],
    blob_bytes_resolver: Callable[[Path, str, str], bytes],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "pilot_camp_head": pilot_head,
        "remaining_camp_head": remaining_head,
        "freeze_camp_head": freeze_head,
        "files": {},
    }
    for relative in PROVENANCE_FILES:
        blobs = []
        for head in (pilot_head, remaining_head, freeze_head):
            blob = blob_resolver(Path(repo), head, relative)
            blobs.append(blob)
        blob_hashes = [
            hashlib.sha256(
                blob_bytes_resolver(Path(repo), head, relative)
            ).hexdigest()
            for head in (pilot_head, remaining_head, freeze_head)
        ]
        live_sha256 = _file_sha256(Path(repo) / relative)
        if (
            len(set(blobs)) != 1
            or len(set(blob_hashes)) != 1
            or blob_hashes[-1] != live_sha256
        ):
            raise ValueError("atom source drift across corpus and freeze heads")
        result["files"][relative] = {
            "git_blob": blobs[0],
            "git_blob_sha256": blob_hashes[-1],
            "sha256": live_sha256,
            "live_file_matches_freeze_git_blob": True,
            "identical_across_pilot_remaining_freeze": True,
        }
    executor_blobs = {
        phase: blob_resolver(Path(repo), head, EXECUTOR_PROVENANCE_FILE)
        for phase, head in (
            ("pilot", pilot_head),
            ("remaining", remaining_head),
            ("freeze", freeze_head),
        )
    }
    executor_sources = {
        phase: blob_bytes_resolver(Path(repo), head, EXECUTOR_PROVENANCE_FILE)
        for phase, head in (
            ("pilot", pilot_head),
            ("remaining", remaining_head),
            ("freeze", freeze_head),
        )
    }
    executor_source_sha256 = {
        phase: hashlib.sha256(source).hexdigest()
        for phase, source in executor_sources.items()
    }
    method_hashes = {
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
    critical_hashes = {
        phase: hashlib.sha256(_canonical_json_bytes(projection)).hexdigest()
        for phase, projection in critical_projections.items()
    }
    if (
        len(set(method_hashes.values())) != 1
        or len(set(critical_hashes.values())) != 1
        or executor_source_sha256["freeze"]
        != _file_sha256(Path(repo) / EXECUTOR_PROVENANCE_FILE)
    ):
        raise ValueError("v24 executor snapshot-writer semantic contract drift")
    result["execution_semantic_contract"] = {
        "file": EXECUTOR_PROVENANCE_FILE,
        "class": EXECUTOR_CONTRACT_CLASS,
        "method": EXECUTOR_CONTRACT_METHOD,
        "git_blobs": executor_blobs,
        "source_sha256": executor_source_sha256,
        "method_ast_sha256": method_hashes["freeze"],
        "method_identical_across_pilot_remaining_freeze": True,
        "critical_call_projection_sha256": critical_hashes["freeze"],
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


def _git_blob(repo: Path, head: str, relative: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", f"{head}:{relative}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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
        raise ValueError("live CAMP HEAD or tracked state differs from review authority")


def _check(checks: list[dict[str, Any]], name: str, passed: bool) -> None:
    checks.append({"name": name, "passed": bool(passed)})


def review_atom_freeze(
    *,
    freeze_root: Path,
    expected_freeze_root_sha256: str,
    merged_root: Path,
    expected_merged_root_sha256: str,
    merged_review_root: Path,
    expected_merged_review_root_sha256: str,
    repo: Path,
    expected_camp_head: str,
    expected_snapshot_count: int = 67796,
    blob_resolver: Callable[[Path, str, str], str] = _git_blob,
    blob_bytes_resolver: Callable[[Path, str, str], bytes] = _git_blob_bytes,
    git_state_checker: Callable[[Path, str], None] = _require_clean_git_state,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    inventories: dict[str, dict[str, str]] = {}
    recomputed: dict[str, Any] = {}
    try:
        git_state_checker(Path(repo), expected_camp_head)
        inventories["freeze"] = _verify_seal(
            freeze_root, expected_freeze_root_sha256
        )
        inventories["merged"] = _verify_seal(
            merged_root, expected_merged_root_sha256
        )
        inventories["merged_review"] = _verify_seal(
            merged_review_root, expected_merged_review_root_sha256
        )
        _check(checks, "source_seals", True)
        _check(
            checks,
            "source_execution_receipts",
            all(
                _clean_execution(path)
                for path in (freeze_root, merged_root, merged_review_root)
            ),
        )
        freeze = _read_json(Path(freeze_root) / "atom_freeze.json")
        merged = _read_json(Path(merged_root) / "merged_summary.json")
        merged_review = _read_json(Path(merged_review_root) / "review.json")
        _check(
            checks,
            "freeze_stdout_identity",
            _read_json(Path(freeze_root) / "stdout.txt") == freeze,
        )
        _check(
            checks,
            "merged_authority",
            merged.get("schema")
            == "camp_dp_v24_native_corpus_merged_train_index_v1"
            and merged.get("status") == "passed"
            and merged.get("phase") == "merged_train_corpus_assembly_only"
            and merged.get("split") == "train"
            and merged.get("snapshot_count") == expected_snapshot_count
            and merged.get("snapshot_index_row_count") == expected_snapshot_count
            and merged.get("snapshot_payloads_copied") is False
            and merged.get("snapshot_payloads_modified") is False
            and merged.get("route_or_seed_removed_replaced_or_reordered") is False
            and merged.get("assembly_only") is True
            and merged.get("model_loaded") is False
            and merged.get("simulator_executed") is False
            and merged.get("candidate_generation_started") is False
            and merged.get("training_executed") is False
            and merged.get("tuning_executed") is False
            and merged.get("outcome_fields_consumed") == []
            and merged.get("calibration_accessed") is False
            and merged.get("holdout_opened") is False
            and merged.get("claim_authorized") is False,
        )
        decision = merged_review.get("decision", {})
        upstream_checks = merged_review.get("checks")
        upstream_check_count = merged_review.get("check_count")
        upstream_failed_count = merged_review.get("failed_count")
        _check(
            checks,
            "merged_review_authority",
            merged_review.get("schema")
            == "camp_dp_v24_native_corpus_merged_independent_review_v1"
            and merged_review.get("status") == "passed"
            and merged_review.get("source_assembly_root_sha256")
            == expected_merged_root_sha256
            and merged_review.get("fixed_dp_head") == FIXED_DP_HEAD
            and not isinstance(upstream_check_count, bool)
            and isinstance(upstream_check_count, int)
            and upstream_check_count > 0
            and isinstance(upstream_checks, list)
            and upstream_check_count == len(upstream_checks)
            and not isinstance(upstream_failed_count, bool)
            and isinstance(upstream_failed_count, int)
            and upstream_failed_count == 0
            and merged_review.get("failed_checks") == []
            and all(
                isinstance(check, Mapping) and check.get("passed") is True
                for check in upstream_checks
            )
            and decision.get("action")
            == "review_atom_availability_and_freeze_train_only_mask"
            and decision.get("atom_availability_review_authorized") is True
            and decision.get("training_authorized") is False
            and decision.get("tuning_authorized") is False
            and decision.get("outcome_access_authorized") is False
            and decision.get("calibration_access_authorized") is False
            and decision.get("holdout_access_authorized") is False
            and decision.get("claim_authorized") is False
            and merged_review.get("training_executed") is False
            and merged_review.get("review_only") is True
            and merged_review.get("model_loaded") is False
            and "simulator_executed" not in merged_review
            and merged_review.get("candidate_generation_started") is False
            and merged_review.get("tuning_executed") is False
            and merged_review.get("outcome_accessed") is False
            and merged_review.get("calibration_accessed") is False
            and merged_review.get("holdout_opened") is False
            and merged_review.get("claim_authorized") is False
            and merged_review.get("next_work_target")
            == "v24_native_corpus_atom_availability_and_freeze_review_only",
        )
        atoms, valid, physical, source_inventories = _snapshot_arrays(
            merged_root=merged_root, summary=merged
        )
        inventories.update(source_inventories)
        stats, scales, active = _recomputed_stats(atoms, valid)
        active_names = [
            name for name, enabled in zip(DP_CAMP_ATOM_NAMES_V10, active) if enabled
        ]
        excluded_names = [
            name for name, enabled in zip(DP_CAMP_ATOM_NAMES_V10, active) if not enabled
        ]
        corpus_receipt = {
            "snapshot_count": int(atoms.shape[0]),
            "candidate_count": int(atoms.shape[0] * 8),
            "source_valid_candidate_count": int(valid.sum()),
            "source_invalid_candidate_count": int(valid.size - valid.sum()),
            "physical_feasible_candidate_count": int(physical.sum()),
            "all_k_high_risk_snapshot_count": int(
                np.sum(valid.all(axis=1) & ~physical.any(axis=1))
            ),
            "candidate_tensor_immutability_count": int(atoms.shape[0]),
            "candidate0_default_identity_count": int(atoms.shape[0]),
            "feature_identity_field_count": 0,
            "outcome_field_count": 0,
        }
        source_heads = {
            name: _heads(Path(merged["source_artifacts"][name]["path"]) / "HEADS")
            for name in ("pilot", "remaining")
        }
        if any(
            heads.get("FIXED_DP_HEAD") != FIXED_DP_HEAD
            for heads in source_heads.values()
        ):
            raise ValueError("independent source fixed DP HEAD mismatch")
        provenance = _source_provenance(
            repo=repo,
            pilot_head=source_heads["pilot"]["CAMP_HEAD"],
            remaining_head=source_heads["remaining"]["CAMP_HEAD"],
            freeze_head=expected_camp_head,
            blob_resolver=blob_resolver,
            blob_bytes_resolver=blob_bytes_resolver,
        )
        recomputed = {
            "corpus_receipt": corpus_receipt,
            "atom_contract_projection_sha256": EXPECTED_ATOM_CONTRACT_SHA256,
            "atom_scales": scales,
            "active_atom_mask": active,
            "active_atom_names": active_names,
            "excluded_atom_names": excluded_names,
            "atom_statistics": stats,
            "source_provenance": provenance,
        }
        _check(
            checks,
            "freeze_schema",
            freeze.get("schema")
            == "camp_dp_v24_train_atom_availability_freeze_v1"
            and freeze.get("status") == "passed"
            and freeze.get("split") == "train"
            and freeze.get("atom_schema_version") == "dp_camp_v10_14d"
            and freeze.get("atom_names") == list(DP_CAMP_ATOM_NAMES_V10)
            and freeze.get("atom_count") == 14
            and freeze.get("atom_contract_projection_sha256")
            == EXPECTED_ATOM_CONTRACT_SHA256,
        )
        _check(
            checks,
            "source_roots_exact",
            freeze.get("source_merged_root_sha256") == expected_merged_root_sha256
            and freeze.get("source_merged_review_root_sha256")
            == expected_merged_review_root_sha256
            and freeze.get("fixed_dp_head") == FIXED_DP_HEAD,
        )
        _check(
            checks,
            "scale_rule_frozen",
            freeze.get("scale_rule")
            == {
                "scope": "source_valid_train_candidates_only",
                "percentile": 95.0,
                "floor": 1e-6,
            },
        )
        _check(
            checks,
            "variation_rule_frozen",
            freeze.get("variation_rule")
            == {
                "scope": "within_tick_source_valid_candidates_only",
                "cross_candidate_range_strictly_greater_than": 1e-12,
                "active_requires_any_variable_train_snapshot": True,
            },
        )
        for name, value in recomputed.items():
            _check(checks, f"recomputed_{name}", freeze.get(name) == value)
        _check(
            checks,
            "affine_convex_boundary",
            freeze.get("score_contract") == "score_k(w)=a_k^T w"
            and freeze.get("weight_domain")
            == "nonnegative_simplex_over_active_atoms_only"
            and freeze.get("inactive_atom_weight_rule")
            == "explicit_exact_zero_not_silent",
        )
        _check(
            checks,
            "mask_source_boundary",
            freeze.get("active_mask_selected_from")
            == "causal_source_availability_and_train_only_cross_candidate_variance"
            and freeze.get("calibration_or_holdout_used_for_mask") is False,
        )
        _check(
            checks,
            "closed_boundaries",
            freeze.get("snapshot_payloads_modified") is False
            and freeze.get("model_loaded") is False
            and freeze.get("simulator_executed") is False
            and freeze.get("candidate_generation_started") is False
            and freeze.get("training_executed") is False
            and freeze.get("tuning_executed") is False
            and freeze.get("outcome_fields_consumed") == []
            and freeze.get("calibration_accessed") is False
            and freeze.get("holdout_opened") is False
            and freeze.get("claim_authorized") is False
            and freeze.get("training_plan_authorized") is False
            and freeze.get("training_execution_authorized") is False,
        )
        _check(
            checks,
            "next_gate",
            freeze.get("next_work_target")
            == "v24_native_corpus_atom_availability_freeze_independent_review_only",
        )
    except Exception:
        _check(checks, "review_input_valid", False)
    failed = [item["name"] for item in checks if not item["passed"]]
    passed = not failed
    return {
        "schema": "camp_dp_v24_train_atom_availability_freeze_independent_review_v1",
        "status": "passed" if passed else "failed",
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "verified_file_count": sum(len(value) for value in inventories.values()),
        "source_freeze_root_sha256": expected_freeze_root_sha256,
        "source_merged_root_sha256": expected_merged_root_sha256,
        "source_merged_review_root_sha256": expected_merged_review_root_sha256,
        "fixed_dp_head": FIXED_DP_HEAD,
        "recomputed": recomputed,
        "decision": {
            "action": (
                "design_and_preflight_v24_train_only_convex_training"
                if passed
                else "atom_freeze_failure_analysis_only"
            ),
            "training_plan_tdd_static_preflight_authorized": passed,
            "training_execution_authorized": False,
            "outcome_access_authorized": False,
            "calibration_access_authorized": False,
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
        "review_only": True,
        "model_loaded": False,
        "simulator_executed": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "next_work_target": (
            "v24_convex_selector_training_plan_tdd_static_preflight_only"
            if passed
            else "v24_atom_availability_freeze_failure_analysis_only"
        ),
    }


def _seal(root: Path) -> str:
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
    parser.add_argument("--freeze-root", type=Path, required=True)
    parser.add_argument("--expected-freeze-root-sha256", required=True)
    parser.add_argument("--merged-root", type=Path, required=True)
    parser.add_argument("--expected-merged-root-sha256", required=True)
    parser.add_argument("--merged-review-root", type=Path, required=True)
    parser.add_argument("--expected-merged-review-root-sha256", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--expected-snapshot-count", type=int, default=67796)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        raise FileExistsError(f"evidence target already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    review = review_atom_freeze(
        freeze_root=args.freeze_root,
        expected_freeze_root_sha256=args.expected_freeze_root_sha256,
        merged_root=args.merged_root,
        expected_merged_root_sha256=args.expected_merged_root_sha256,
        merged_review_root=args.merged_review_root,
        expected_merged_review_root_sha256=args.expected_merged_review_root_sha256,
        repo=ROOT,
        expected_camp_head=args.camp_head,
        expected_snapshot_count=args.expected_snapshot_count,
    )
    (args.output_dir / "HEADS").write_text(
        f"CAMP_HEAD={args.camp_head}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_FREEZE_ROOT_SHA256={args.expected_freeze_root_sha256}\n"
        f"SOURCE_MERGED_ROOT_SHA256={args.expected_merged_root_sha256}\n"
        "SOURCE_MERGED_REVIEW_ROOT_SHA256="
        f"{args.expected_merged_review_root_sha256}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        "v24 train-only atom availability freeze independent review\n",
        encoding="utf-8",
    )
    (args.output_dir / "review.json").write_bytes(_canonical_json_bytes(review))
    (args.output_dir / "review.md").write_text(
        "# v24 train-only atom availability freeze independent review\n\n"
        f"- status: `{review['status']}`\n"
        f"- checks / failed: `{review['check_count']} / {review['failed_count']}`\n"
        f"- verified files: `{review['verified_file_count']}`\n"
        "- training execution / outcomes / calibration / holdout / claim: "
        "`false/false/false/false/false`\n",
        encoding="utf-8",
    )
    stdout = json.dumps(review, sort_keys=True, allow_nan=False) + "\n"
    (args.output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (args.output_dir / "stderr.txt").write_text("", encoding="utf-8")
    success = review["status"] == "passed"
    (args.output_dir / "run.exit").write_text(
        "0\n" if success else "1\n", encoding="ascii"
    )
    root_sha256 = _seal(args.output_dir)
    print(
        json.dumps(
            {
                "artifact": str(args.output_dir.resolve()),
                "root_sha256": root_sha256,
                "status": review["status"],
                "checks": review["check_count"],
                "failed": review["failed_count"],
            },
            sort_keys=True,
        )
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
