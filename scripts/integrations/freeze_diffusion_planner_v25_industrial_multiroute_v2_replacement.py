from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2 import (  # noqa: E402
    latent_receipt,
    validate_selected_manifest,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_replacement import (  # noqa: E402
    AUTHORITY_SHA256,
    FIXED_DP_HEAD,
    MIN_FREE_AFTER_BYTES,
    MIN_FREE_INODES_AFTER,
    OLD_ATTEMPT_CLASSIFICATION,
    OLD_ATTEMPT_CONTROL,
    OLD_ATTEMPT_LAUNCHER,
    OLD_ATTEMPT_STDERR_SHA256,
    OLD_ATTEMPT_STDOUT_SHA256,
    PARENT_B5CA_AUTHORITY_SHA256,
    PARENT_CONTINUATION_SHA256,
    PARENT_SOURCE_AUTHORITY_SHA256,
    PLANNED_TICKS,
    SOURCE_CONTRACT_REVIEW_ROOT_SHA256,
    SOURCE_CONTRACT_ROOT_SHA256,
    SOURCE_CONTINUATION_REVIEW_ROOT_SHA256,
    SOURCE_CONTINUATION_ROOT_SHA256,
    SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256,
    SOURCE_MATERIALIZATION_ROOT_SHA256,
    SOURCE_SELECTED_MANIFEST_SHA256,
    canonical_bytes,
    canonical_sha256,
    replacement_contract,
    replacement_exact_dirs,
    semantic_runtime_receipt,
    validate_replacement_contract,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)
from scripts.integrations.freeze_diffusion_planner_v25_industrial_multiroute_v2 import (  # noqa: E402
    _interpreter,
    _tree_size_and_files,
    _tracked_changes,
    _write_preflight,
)


AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"
PRODUCTION_FILES = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_industrial_multiroute_v2_replacement.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_industrial_multiroute_v2_replacement_review.py",
    "scripts/integrations/freeze_diffusion_planner_v25_industrial_multiroute_v2_replacement.py",
    "scripts/integrations/review_diffusion_planner_v25_industrial_multiroute_v2_replacement.py",
    "scripts/integrations/run_diffusion_planner_v25_industrial_multiroute_v2.py",
    "scripts/integrations/review_diffusion_planner_v25_industrial_multiroute_v2.py",
    "scripts/integrations/evaluate_diffusion_planner_v25_industrial_multiroute_v2.py",
    "scripts/integrations/finalize_diffusion_planner_v25_industrial_multiroute_v2.py",
    "scripts/integrations/validate_diffusion_planner_v25_fair_nonholdout.py",
    "camp_core/tests/test_diffusion_planner_v25_industrial_multiroute_v2_replacement.py",
)


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def _heads(role: str, implementation_head: str, **extra: Any) -> dict[str, Any]:
    return {
        "role": role,
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        **extra,
    }


def freeze_old_attempt_closeout(output: Path) -> str:
    control = Path(OLD_ATTEMPT_CONTROL)
    launcher = Path(OLD_ATTEMPT_LAUNCHER)
    milestone = object_from(control / "milestone.json")
    stdout = Path(str(launcher) + ".stdout")
    stderr = Path(str(launcher) + ".stderr")
    launcher_exit = Path(str(launcher) + ".run.exit")
    if (
        milestone
        != {
            "completed_clusters": 5,
            "completed_tick_slots": 960,
            "formal_model_calls": 960,
            "last_cluster_index": 4,
        }
        or launcher_exit.read_text(encoding="ascii").strip() != "1"
        or _file_sha(stdout) != OLD_ATTEMPT_STDOUT_SHA256
        or _file_sha(stderr) != OLD_ATTEMPT_STDERR_SHA256
        or (control.parent / control.name.removeprefix(".").removesuffix("_control")).exists()
    ):
        raise ValueError("old partial attempt evidence drifted")
    cluster_dirs = sorted(
        path.name
        for path in (control / "clusters").iterdir()
        if path.is_dir()
    )
    if cluster_dirs != [f"{index:03d}" for index in range(5)]:
        raise ValueError("old partial cluster denominator drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "old_attempt_closeout_v1"
        ),
        "status": "immutable_partial_attempt_closed_without_outcome_read",
        "classification": OLD_ATTEMPT_CLASSIFICATION,
        "authority_sha256": AUTHORITY_SHA256,
        "old_control_path": str(control),
        "old_launcher_path": str(launcher),
        "launcher_exit": 1,
        "stdout_sha256": OLD_ATTEMPT_STDOUT_SHA256,
        "stderr_sha256": OLD_ATTEMPT_STDERR_SHA256,
        "milestone": milestone,
        "completed_cluster_dirs": cluster_dirs,
        "failed_selected_index": 5,
        "failed_source_ordinal": 159,
        "failed_cell": {
            "family": "red_light_phase_timing",
            "source_availability": "no_signal",
        },
        "failure_exception": (
            "ValueError: no-signal semantic clone payload/hash mismatch"
        ),
        "execution_artifact_formed": False,
        "old_partial_reuse": False,
        "cluster_effect_or_outcome_values_read": False,
        "model_calls_added": 0,
    }
    return write_atomic(
        output,
        report,
        _heads("multiroute_v2_replacement_old_attempt_closeout", git_head()),
        label="V25 multiroute-v2 replacement old attempt closeout",
    )


def continuation_preimage(
    *,
    implementation_head: str,
    closeout_root: str,
    closeout_review_root: str,
) -> dict[str, Any]:
    return {
        "high_authority_sha256": AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "source_roots_and_reviews": {
            "contract": SOURCE_CONTRACT_ROOT_SHA256,
            "contract_review": SOURCE_CONTRACT_REVIEW_ROOT_SHA256,
            "materialization": SOURCE_MATERIALIZATION_ROOT_SHA256,
            "materialization_review": SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256,
            "continuation": SOURCE_CONTINUATION_ROOT_SHA256,
            "continuation_review": SOURCE_CONTINUATION_REVIEW_ROOT_SHA256,
        },
        "selected_manifest_sha256": SOURCE_SELECTED_MANIFEST_SHA256,
        "parent_source_authority_sha256": PARENT_SOURCE_AUTHORITY_SHA256,
        "parent_b5ca_authority_sha256": PARENT_B5CA_AUTHORITY_SHA256,
        "parent_continuation_sha256": PARENT_CONTINUATION_SHA256,
        "old_attempt_closeout_root": closeout_root,
        "old_attempt_closeout_review_root": closeout_review_root,
        "formal_runtime_semantics": {
            "raw_family_signal_is_formal_authority": False,
            "no_signal_forces_none_false_absence": True,
            "mapped_signal_requires_same_tick_certified_phase": True,
            "future_phase_or_schedule_consumed": False,
        },
        "unchanged_parent_scientific_contract_fields": {
            "clusters": 100,
            "arms": 300,
            "ticks": 19_200,
            "start_from_zero": True,
            "old_partial_reuse": False,
            "industrial_leaf_count": 161,
            "weighted_total": False,
            "claim_authorized": False,
        },
    }


def freeze_contract(
    output: Path,
    *,
    implementation_head: str,
    closeout_dir: Path,
    closeout_root: str,
    closeout_review_dir: Path,
    closeout_review_root: str,
) -> str:
    _verify(closeout_dir, closeout_root, "replacement old attempt closeout")
    _verify(
        closeout_review_dir,
        closeout_review_root,
        "replacement old attempt closeout review",
    )
    preimage = continuation_preimage(
        implementation_head=implementation_head,
        closeout_root=closeout_root,
        closeout_review_root=closeout_review_root,
    )
    continuation_sha = canonical_sha256(preimage)
    exact = replacement_exact_dirs(implementation_head, continuation_sha)
    if output.resolve() != Path(exact["contract"]):
        raise ValueError("replacement contract exact dir drifted")
    contract = validate_replacement_contract(
        replacement_contract(
            implementation_head=implementation_head,
            replacement_continuation_sha256=continuation_sha,
            replacement_continuation_root=canonical_sha256(
                {"continuation_preimage": preimage, "continuation_sha256": continuation_sha}
            ),
            replacement_continuation_review_root=canonical_sha256(
                {
                    "reviewed_continuation_preimage": preimage,
                    "continuation_sha256": continuation_sha,
                    "review_status": "independent_literal_passed",
                }
            ),
            old_attempt_closeout_root=closeout_root,
            old_attempt_closeout_review_root=closeout_review_root,
        )
    )
    files = {relative: _file_sha(ROOT / relative) for relative in PRODUCTION_FILES}
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "replacement_contract_artifact_v1"
        ),
        "status": "sealed_outcome_independent_replacement_contract",
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "continuation_preimage": preimage,
        "replacement_continuation_sha256": continuation_sha,
        "contract": contract,
        "production_file_sha256": files,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
    }
    return write_atomic(
        output,
        report,
        _heads(
            "multiroute_v2_replacement_contract",
            implementation_head,
            replacement_continuation_sha256=continuation_sha,
        ),
        label="V25 multiroute-v2 no-signal consumer replacement contract",
    )


def freeze_matrix(
    output: Path, *, contract_dir: Path, contract_root: str
) -> str:
    contract = _verify(contract_dir, contract_root, "replacement contract")
    exact = contract["contract"]["exact_dirs"]
    if output.resolve() != Path(exact["semantic_hardening_matrix"]):
        raise ValueError("replacement matrix exact dir drifted")
    rows = [
        {
            "parameter": "source_availability",
            "sealed_source": "source_records.json#/records/*/cell/source_availability",
            "loader": "validate_source_record_after_deterministic_rebuild",
            "production_callsite": "reconstruct_controlled_case(source_record)",
            "receipt": "semantic_runtime_receipt.source_availability",
            "reviewer_literal": "_literal_case",
            "evaluator": "industrial red-leaf applicability",
            "implicit_default_allowed": False,
        },
        {
            "parameter": "formal_phase",
            "sealed_source": "semantic_block.signal_semantics as raw family evidence",
            "loader": "availability-driven transform after source equality",
            "production_callsite": "build_signal_authority(source_record,case)",
            "receipt": "formal_phase/phase_authority_mode",
            "reviewer_literal": "_literal_chain",
            "evaluator": "same-tick certified phase only",
            "implicit_default_allowed": False,
        },
        {
            "parameter": "formal_signal_objects",
            "sealed_source": "map/source availability inventories",
            "loader": "mapped chain or no-signal absence validator",
            "production_callsite": "V25ControlledSceneAdapter required keyword",
            "receipt": "formal_signal_object_counts/source_chain_sha256",
            "reviewer_literal": "_literal_chain",
            "evaluator": "red opportunity/applicability typed policy",
            "implicit_default_allowed": False,
        },
        {
            "parameter": "future_phase_schedule",
            "sealed_source": "not available and forbidden",
            "loader": "no loader",
            "production_callsite": "unreachable",
            "receipt": "future_phase_consumed=false/future_schedule_consumed=false",
            "reviewer_literal": "exact false",
            "evaluator": "not consumed",
            "implicit_default_allowed": False,
        },
        {
            "parameter": "runtime_authority",
            "sealed_source": "CAMP HEAD/fixed-DP HEAD/checkpoint/runtime/interpreter",
            "loader": "typed preflight bindings",
            "production_callsite": "replacement runner",
            "receipt": "HEADS/model/checkpoint/runtime IDs",
            "reviewer_literal": "local exact roots and hashes",
            "evaluator": "provenance only",
            "implicit_default_allowed": False,
        },
        {
            "parameter": "full_denominator_and_failure",
            "sealed_source": "100x3x64 replacement contract",
            "loader": "typed terminal policy",
            "production_callsite": "runner per-slot retention",
            "receipt": "complete+failed+unattempted=19200",
            "reviewer_literal": "100 clusters/300 arms/19200 ticks",
            "evaluator": "full denominator no complete-case",
            "implicit_default_allowed": False,
        },
    ]
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "replacement_semantic_hardening_matrix_v1"
        ),
        "status": "outcome_independent_parameter_propagation_matrix_frozen",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "rows": rows,
        "production_entrypoints": [
            "reconstruct_controlled_case",
            "build_signal_authority",
            "build_scene_adapter",
            "semantic_runtime_receipt",
            "validate_diffusion_planner_v25_fair_nonholdout._run_one",
            "run_diffusion_planner_v25_industrial_multiroute_v2.execute",
            "industrial-v3 evaluator",
        ],
        "residual_risk_register": {
            "actually_executed": [
                "252x64 semantic adapter dry-run",
                "replacement runner after preflight",
            ],
            "static_only": ["future schedule unreachability scan"],
            "unexecuted": ["Fresh/holdout and deployment paths"],
            "zero_bug_claimed": False,
        },
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return write_atomic(
        output,
        report,
        _heads(
            "multiroute_v2_replacement_semantic_hardening_matrix",
            contract["implementation_head"],
            contract_root_sha256=contract_root,
        ),
        label="V25 multiroute-v2 replacement semantic hardening matrix",
    )


def freeze_focused(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    matrix_dir: Path,
    matrix_root: str,
    test_count: int,
    command_sha256: str,
    stdout_sha256: str,
) -> str:
    contract = _verify(contract_dir, contract_root, "replacement contract")
    _verify(matrix_dir, matrix_root, "replacement hardening matrix")
    if output.resolve() != Path(
        contract["contract"]["exact_dirs"]["semantic_hardening_focused"]
    ):
        raise ValueError("replacement focused exact dir drifted")
    if test_count < 1 or len(command_sha256) != 64 or len(stdout_sha256) != 64:
        raise ValueError("focused receipt is invalid")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "replacement_semantic_hardening_focused_v1"
        ),
        "status": "passed_zero_model_semantic_hardening_focused",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "matrix_root_sha256": matrix_root,
        "test_count": test_count,
        "test_command_sha256": command_sha256,
        "stdout_sha256": stdout_sha256,
        "interpreter": _interpreter(require_runtime=True),
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return write_atomic(
        output,
        report,
        _heads(
            "multiroute_v2_replacement_semantic_hardening_focused",
            contract["implementation_head"],
            contract_root_sha256=contract_root,
        ),
        label="V25 multiroute-v2 replacement semantic hardening focused",
    )


def _write_extra_files(
    output: Path,
    report: Mapping[str, Any],
    heads: Mapping[str, Any],
    files: Mapping[str, bytes],
    *,
    label: str,
) -> str:
    if output.exists():
        raise FileExistsError(output)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(canonical_bytes(dict(report)))
        (staging / "HEADS.json").write_bytes(canonical_bytes(dict(heads)))
        for relative, payload in files.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label=label)
        os.replace(staging, output)
        verify_complete_seal(output, root, label=label)
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def freeze_dryrun(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    matrix_dir: Path,
    matrix_root: str,
    source_dir: Path,
    source_root: str,
    source_review_dir: Path,
    source_review_root: str,
) -> str:
    contract = _verify(contract_dir, contract_root, "replacement contract")
    _verify(matrix_dir, matrix_root, "replacement matrix")
    _verify(source_dir, source_root, "project source materialization")
    _verify(source_review_dir, source_review_root, "project source review")
    if (
        source_root != SOURCE_MATERIALIZATION_ROOT_SHA256
        or source_review_root != SOURCE_MATERIALIZATION_REVIEW_ROOT_SHA256
        or output.resolve()
        != Path(contract["contract"]["exact_dirs"]["semantic_adapter_dryrun"])
    ):
        raise ValueError("replacement dry-run authority drifted")
    records = object_from(source_dir / "source_records.json")["records"]
    if len(records) != 252:
        raise ValueError("replacement dry-run candidate ceiling drifted")
    receipts = []
    class_counts = {"mapped_signal": 0, "no_signal": 0}
    phase_counts = {"green": 0, "yellow": 0, "red": 0}
    for record in records:
        source_class = record["cell"]["source_availability"]
        class_counts[source_class] += 1
        first = semantic_runtime_receipt(record, 0)
        if source_class == "mapped_signal":
            phase_counts[first["formal_phase"]] += 64
        for tick in range(64):
            receipts.append(semantic_runtime_receipt(record, tick))
    if (
        len(receipts) != 16_128
        or class_counts != {"mapped_signal": 126, "no_signal": 126}
        or any(phase_counts[phase] == 0 for phase in phase_counts)
    ):
        raise ValueError("replacement dry-run coverage drifted")
    payload = {"receipts": receipts}
    payload_bytes = canonical_bytes(payload)
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "replacement_semantic_adapter_dryrun_v1"
        ),
        "status": "passed_252_candidate_64_tick_zero_model_semantic_dryrun",
        "authority_sha256": AUTHORITY_SHA256,
        "contract_root_sha256": contract_root,
        "matrix_root_sha256": matrix_root,
        "source_root_sha256": source_root,
        "source_review_root_sha256": source_review_root,
        "candidate_count": 252,
        "ticks_per_candidate": 64,
        "receipt_count": len(receipts),
        "source_class_candidate_counts": class_counts,
        "mapped_phase_receipt_counts": phase_counts,
        "receipts_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "no_signal_receipts": 126 * 64,
        "mapped_signal_receipts": 126 * 64,
        "future_phase_or_schedule_consumed_count": 0,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return _write_extra_files(
        output,
        report,
        _heads(
            "multiroute_v2_replacement_semantic_adapter_dryrun",
            contract["implementation_head"],
            contract_root_sha256=contract_root,
        ),
        {"receipts.json": payload_bytes},
        label="V25 multiroute-v2 replacement semantic adapter dry-run",
    )


def freeze_preflight(
    output: Path,
    *,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    matrix_dir: Path,
    matrix_root: str,
    matrix_review_dir: Path,
    matrix_review_root: str,
    focused_dir: Path,
    focused_root: str,
    dryrun_dir: Path,
    dryrun_root: str,
    dryrun_review_dir: Path,
    dryrun_review_root: str,
    source_dir: Path,
    source_root: str,
    source_review_dir: Path,
    source_review_root: str,
    probe_config: Path,
    fixed_dp_repo: Path,
    capacity_sources: list[Path],
) -> str:
    contract = _verify(contract_dir, contract_root, "replacement contract")
    for path, root, label in (
        (contract_review_dir, contract_review_root, "contract review"),
        (matrix_dir, matrix_root, "matrix"),
        (matrix_review_dir, matrix_review_root, "matrix review"),
        (focused_dir, focused_root, "focused"),
        (dryrun_dir, dryrun_root, "semantic dry-run"),
        (dryrun_review_dir, dryrun_review_root, "semantic dry-run review"),
        (source_dir, source_root, "source materialization"),
        (source_review_dir, source_review_root, "source review"),
    ):
        _verify(path, root, label)
    if output.resolve() != Path(contract["contract"]["exact_dirs"]["preflight"]):
        raise ValueError("replacement preflight exact dir drifted")
    if (
        subprocess.run(
            ["git", "-C", str(fixed_dp_repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        != FIXED_DP_HEAD
        or _tracked_changes(fixed_dp_repo)
    ):
        raise ValueError("fixed DP authority drifted")
    allowed = {
        "scripts/integrations/materialize_diffusion_planner_v25_batch8_training_support_reference.py",
        "scripts/integrations/review_diffusion_planner_v25_batch8_training_support_reference.py",
    }
    actual = {
        line[3:].replace("\\", "/")
        for line in _tracked_changes(ROOT)
        if len(line) > 3
    }
    if not actual.issubset(allowed):
        raise ValueError("CAMP tracked scope drifted before replacement model")
    source_report = object_from(source_dir / "report.json")
    records = object_from(source_dir / "source_records.json")["records"]
    selected_manifest = object_from(source_dir / "selected_manifest.json")
    selected = validate_selected_manifest(selected_manifest, records)
    if (
        source_report["selected_manifest_sha256"]
        != SOURCE_SELECTED_MANIFEST_SHA256
        or len(selected) != 100
    ):
        raise ValueError("replacement selected source drifted")
    per_class = []
    for path in capacity_sources:
        size, count = _tree_size_and_files(path)
        per_class.append(
            {
                "path": str(path.resolve()),
                "single_route_payload_bytes": size,
                "single_route_file_count": count,
                "projected_bytes": math.ceil(size * 100 * 1.25),
                "projected_files": math.ceil(count * 100 * 1.25),
            }
        )
    persistent = sum(item["projected_bytes"] for item in per_class) + 2 * 1024**3
    peak = max(item["projected_bytes"] for item in per_class)
    reserve = max(5 * 1024**3, math.ceil(peak * 0.25))
    usage = shutil.disk_usage(output.parent)
    projected = usage.free - persistent - peak
    free_inodes = int(os.statvfs(output.parent).f_favail)
    projected_inodes = free_inodes - sum(item["projected_files"] for item in per_class)
    if (
        projected < MIN_FREE_AFTER_BYTES + reserve
        or projected_inodes < MIN_FREE_INODES_AFTER
    ):
        raise RuntimeError("replacement capacity gate failed before model")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_replacement_preflight_v1"
        ),
        "status": "passed_before_first_replacement_model_call",
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": contract["implementation_head"],
        "replacement_continuation_sha256": contract[
            "replacement_continuation_sha256"
        ],
        "exact_dirs": contract["contract"]["exact_dirs"],
        "contract_root_sha256": contract_root,
        "contract_review_root_sha256": contract_review_root,
        "matrix_root_sha256": matrix_root,
        "matrix_review_root_sha256": matrix_review_root,
        "hardening_focused_root_sha256": focused_root,
        "semantic_dryrun_root_sha256": dryrun_root,
        "semantic_dryrun_review_root_sha256": dryrun_review_root,
        "source_root_sha256": source_root,
        "source_review_root_sha256": source_review_root,
        "selected_manifest_sha256": SOURCE_SELECTED_MANIFEST_SHA256,
        "cluster_count": 100,
        "planned_tick_slots": PLANNED_TICKS,
        "start_from_zero": True,
        "old_partial_reuse": False,
        "zero_overlap": source_report["zero_overlap"],
        "capacity": {
            "classes": per_class,
            "free_before_bytes": usage.free,
            "persistent_bytes": persistent,
            "peak_bytes": peak,
            "reserve_bytes": reserve,
            "projected_free_after_persistent_and_peak_bytes": projected,
            "required_free_after_bytes": MIN_FREE_AFTER_BYTES + reserve,
            "free_inodes_before": free_inodes,
            "projected_free_inodes": projected_inodes,
            "required_free_inodes": MIN_FREE_INODES_AFTER,
        },
        "interpreter": _interpreter(require_runtime=True),
        "worker_count": 0,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
    }
    return _write_preflight(
        output,
        report,
        selected=selected,
        source_dir=source_dir,
        probe_config=object_from(probe_config),
        fixed_dp_repo=fixed_dp_repo,
        authority_sha256=AUTHORITY_SHA256,
        role="industrial_v3_multiroute_v2_replacement_preflight",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    closeout = sub.add_parser("closeout")
    closeout.add_argument("--output", type=Path, required=True)
    contract = sub.add_parser("contract")
    contract.add_argument("--output", type=Path, required=True)
    contract.add_argument("--implementation-head", required=True)
    contract.add_argument("--closeout-dir", type=Path, required=True)
    contract.add_argument("--closeout-root", required=True)
    contract.add_argument("--closeout-review-dir", type=Path, required=True)
    contract.add_argument("--closeout-review-root", required=True)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("--output", type=Path, required=True)
    matrix.add_argument("--contract-dir", type=Path, required=True)
    matrix.add_argument("--contract-root", required=True)
    focused = sub.add_parser("focused")
    focused.add_argument("--output", type=Path, required=True)
    focused.add_argument("--contract-dir", type=Path, required=True)
    focused.add_argument("--contract-root", required=True)
    focused.add_argument("--matrix-dir", type=Path, required=True)
    focused.add_argument("--matrix-root", required=True)
    focused.add_argument("--test-count", type=int, required=True)
    focused.add_argument("--command-sha256", required=True)
    focused.add_argument("--stdout-sha256", required=True)
    dryrun = sub.add_parser("dryrun")
    dryrun.add_argument("--output", type=Path, required=True)
    dryrun.add_argument("--contract-dir", type=Path, required=True)
    dryrun.add_argument("--contract-root", required=True)
    dryrun.add_argument("--matrix-dir", type=Path, required=True)
    dryrun.add_argument("--matrix-root", required=True)
    dryrun.add_argument("--source-dir", type=Path, required=True)
    dryrun.add_argument("--source-root", required=True)
    dryrun.add_argument("--source-review-dir", type=Path, required=True)
    dryrun.add_argument("--source-review-root", required=True)
    preflight = sub.add_parser("preflight")
    for name in (
        "contract",
        "contract-review",
        "matrix",
        "matrix-review",
        "focused",
        "dryrun",
        "dryrun-review",
        "source",
        "source-review",
    ):
        preflight.add_argument(f"--{name}-dir", type=Path, required=True)
        preflight.add_argument(f"--{name}-root", required=True)
    preflight.add_argument("--output", type=Path, required=True)
    preflight.add_argument("--probe-config", type=Path, required=True)
    preflight.add_argument("--fixed-dp-repo", type=Path, required=True)
    preflight.add_argument(
        "--capacity-source", type=Path, action="append", required=True
    )
    args = parser.parse_args()
    if args.command == "closeout":
        root = freeze_old_attempt_closeout(args.output)
    elif args.command == "contract":
        root = freeze_contract(
            args.output,
            implementation_head=args.implementation_head,
            closeout_dir=args.closeout_dir,
            closeout_root=args.closeout_root,
            closeout_review_dir=args.closeout_review_dir,
            closeout_review_root=args.closeout_review_root,
        )
    elif args.command == "matrix":
        root = freeze_matrix(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
        )
    elif args.command == "focused":
        root = freeze_focused(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            matrix_dir=args.matrix_dir,
            matrix_root=args.matrix_root,
            test_count=args.test_count,
            command_sha256=args.command_sha256,
            stdout_sha256=args.stdout_sha256,
        )
    elif args.command == "dryrun":
        root = freeze_dryrun(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            matrix_dir=args.matrix_dir,
            matrix_root=args.matrix_root,
            source_dir=args.source_dir,
            source_root=args.source_root,
            source_review_dir=args.source_review_dir,
            source_review_root=args.source_review_root,
        )
    else:
        root = freeze_preflight(
            args.output,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review_dir,
            contract_review_root=args.contract_review_root,
            matrix_dir=args.matrix_dir,
            matrix_root=args.matrix_root,
            matrix_review_dir=args.matrix_review_dir,
            matrix_review_root=args.matrix_review_root,
            focused_dir=args.focused_dir,
            focused_root=args.focused_root,
            dryrun_dir=args.dryrun_dir,
            dryrun_root=args.dryrun_root,
            dryrun_review_dir=args.dryrun_review_dir,
            dryrun_review_root=args.dryrun_review_root,
            source_dir=args.source_dir,
            source_root=args.source_root,
            source_review_dir=args.source_review_dir,
            source_review_root=args.source_review_root,
            probe_config=args.probe_config,
            fixed_dp_repo=args.fixed_dp_repo,
            capacity_sources=args.capacity_source,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
