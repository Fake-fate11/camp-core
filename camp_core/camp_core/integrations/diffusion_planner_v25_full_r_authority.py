"""Fail-closed machine authority for the V25 full-R preflight/execute gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Mapping

from camp_core.integrations.diffusion_planner_artifact_seal import (
    verify_complete_seal,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PREFLIGHT_RELEASE_SCHEMA_VERSION = (
    "camp_dp_v25_ultra_full_config_preflight_release_v2"
)
EXECUTE_RELEASE_SCHEMA_VERSION = "camp_dp_v25_ultra_full_r_execute_release_v2"
ROOT_ROLES = (
    "a11_decision",
    "a11_ledger",
    "a11_validation",
    "r01_source",
    "r01_source_review",
    "r01_bounded",
    "r01_bounded_review",
)
EXPECTED_ROOT_STATUSES = {
    "a11_decision": "A1_1_R0_1_only_released",
    "a11_ledger": "passed_with_warnings_progress_source_valid_frozen",
    "a11_validation": "passed_with_warnings_progress_source_valid_frozen",
    "r01_source": "passed_source_only_full_r_closed",
    "r01_source_review": "passed_independent_source_review_full_r_closed",
    "r01_bounded": "passed_bounded_21red_1nosignal_x64_full_r_closed",
    "r01_bounded_review": (
        "passed_independent_21red_1nosignal_x64_review_full_r_closed"
    ),
}
POINTER_ONLY_PATHS = frozenset(
    {
        "docs/diffusion_planner_current_status.md",
        "docs/diffusion_planner_v25_iteration_audit.md",
        "camp_core/tests/test_diffusion_planner_v25_iteration_audit.py",
    }
)
CRITICAL_IMPLEMENTATION_PATHS = (
    "camp_core/camp_core/integrations/diffusion_planner.py",
    "camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_context.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_semantic_authority.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_full_r_authority.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py",
    "scripts/integrations/run_diffusion_planner_v25_controlled_training_corpus.py",
    "scripts/integrations/preflight_diffusion_planner_v25_r0_red_k8.py",
    "scripts/integrations/review_diffusion_planner_v25_r0_red_k8.py",
    "scripts/integrations/review_diffusion_planner_v25_full_config_preflight.py",
    "configs/integrations/diffusion_planner_v25_atom_scales_correction_v2.json",
    "configs/integrations/diffusion_planner_v25_atom_ledger_plan_v4.json",
)
_SHA_CHARS = frozenset("0123456789abcdef")


def canonical_sha256(payload: Any) -> str:
    encoded = (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not set(value) - _SHA_CHARS
    )


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"authority JSON is not an object: {path}")
    return value


def _safe_repo_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("implementation manifest path is empty")
    normalized = value.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts or normalized != pure.as_posix():
        raise ValueError("implementation manifest path is unsafe")
    return normalized


def build_critical_implementation_manifest(repo: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for relative in CRITICAL_IMPLEMENTATION_PATHS:
        path = repo / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"critical implementation file is unavailable: {relative}")
        manifest[relative] = file_sha256(path)
    return manifest


def verify_dual_head_contract(
    *,
    repo: Path,
    implementation_source_head: str,
    current_pointer_head: str,
    implementation_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(implementation_source_head, str)
        or len(implementation_source_head) != 40
        or not isinstance(current_pointer_head, str)
        or len(current_pointer_head) != 40
    ):
        raise ValueError("dual-HEAD values are invalid")
    expected_manifest = build_critical_implementation_manifest(repo)
    normalized_manifest = {
        _safe_repo_path(key): value for key, value in implementation_manifest.items()
    }
    if normalized_manifest != expected_manifest:
        raise ValueError("critical implementation manifest drifted")
    changed: list[str] = []
    if implementation_source_head != current_pointer_head:
        completed = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                implementation_source_head,
                current_pointer_head,
                "--",
            ],
            cwd=repo,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        changed = [line.replace("\\", "/") for line in completed.stdout.splitlines()]
        if not changed or set(changed) - POINTER_ONLY_PATHS:
            raise ValueError("dual-HEAD diff exceeds the pointer/docs allowlist")
    return {
        "implementation_source_head": implementation_source_head,
        "current_pointer_head": current_pointer_head,
        "pointer_only_changed_paths": changed,
        "implementation_manifest_sha256": canonical_sha256(expected_manifest),
    }


def _parse_heads(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if "=" not in line:
            raise ValueError(f"malformed HEADS line: {path}")
        key, value = line.split("=", 1)
        if not key or key in result or not value:
            raise ValueError(f"duplicate/empty HEADS field: {path}")
        result[key] = value
    if not result:
        raise ValueError(f"empty HEADS: {path}")
    return result


def _report_source_head(report: Mapping[str, Any], heads: Mapping[str, str]) -> str | None:
    for key in (
        "corrected_source_head",
        "stage_a_source_head",
        "camp_head",
        "review_head",
        "source_head",
    ):
        value = report.get(key)
        if isinstance(value, str) and len(value) == 40:
            return value
    for key in ("camp_source_head", "camp_head"):
        value = heads.get(key)
        if isinstance(value, str) and len(value) == 40:
            return value
    return None


def verify_seven_root_chain(
    *,
    bindings: Mapping[str, Any],
    implementation_source_head: str,
    fixed_dp_head: str,
    rejected_root_sha256: str,
) -> dict[str, dict[str, Any]]:
    if set(bindings) != set(ROOT_ROLES):
        raise ValueError("release does not bind the exact seven prerequisite roots")
    verified: dict[str, dict[str, Any]] = {}
    for role in ROOT_ROLES:
        binding = bindings[role]
        if not isinstance(binding, Mapping) or set(binding) != {
            "path",
            "root_sha256",
            "report_file",
        }:
            raise ValueError(f"{role} binding field set drifted")
        artifact = Path(str(binding["path"]))
        root = str(binding["root_sha256"])
        report_file = str(binding["report_file"])
        if Path(report_file).name != report_file or not is_sha256(root):
            raise ValueError(f"{role} binding is unsafe")
        seal = verify_complete_seal(artifact, root, label=f"V25 {role}")
        if (artifact / "run.exit").read_text(encoding="ascii") != "0\n":
            raise ValueError(f"{role} run.exit is not zero")
        report = _load_object(artifact / report_file)
        heads = _parse_heads(artifact / "HEADS")
        if (
            report.get("status") != EXPECTED_ROOT_STATUSES[role]
            or heads.get("fixed_dp_head") != fixed_dp_head
            or _report_source_head(report, heads) != implementation_source_head
        ):
            raise ValueError(f"{role} status/HEADS authority drifted")
        verified[role] = {
            "path": str(artifact),
            "root_sha256": seal["root_sha256"],
            "report": report,
        }

    roots = {role: row["root_sha256"] for role, row in verified.items()}
    decision = verified["a11_decision"]["report"]
    ledger = verified["a11_ledger"]["report"]
    validation = verified["a11_validation"]["report"]
    source = verified["r01_source"]["report"]
    source_review = verified["r01_source_review"]["report"]
    bounded = verified["r01_bounded"]["report"]
    bounded_review = verified["r01_bounded_review"]["report"]
    if (
        decision.get("rejected_roots") != [rejected_root_sha256]
        or ledger.get("authority", {}).get("ultra_decision_root_sha256")
        != roots["a11_decision"]
        or validation.get("reviewed_root_sha256") != roots["a11_ledger"]
        or source.get("ultra_decision_root_sha256") != roots["a11_decision"]
        or source.get("a1_ledger_root_sha256") != roots["a11_ledger"]
        or source.get("a1_validation_root_sha256") != roots["a11_validation"]
        or source_review.get("reviewed_root_sha256") != roots["r01_source"]
        or bounded.get("r0_source_root_sha256") != roots["r01_source"]
        or bounded.get("r0_review_root_sha256") != roots["r01_source_review"]
        or bounded_review.get("reviewed_root_sha256") != roots["r01_bounded"]
        or bounded_review.get("r0_source_root_sha256") != roots["r01_source"]
        or bounded_review.get("r0_source_review_root_sha256")
        != roots["r01_source_review"]
    ):
        raise ValueError("seven-root cross-link authority drifted")
    return verified


def consume_one_shot_nonce(
    *,
    ledger_dir: Path,
    gate: str,
    nonce: str,
    authorized_output_dir: str,
    requested_output_dir: Path,
) -> Path:
    if gate not in {"preflight", "execute"} or not is_sha256(nonce):
        raise ValueError("one-shot gate/nonce is invalid")
    expected = Path(authorized_output_dir).resolve()
    requested = requested_output_dir.resolve()
    if requested != expected:
        raise ValueError("release is bound to a different exact output directory")
    ledger_dir.mkdir(parents=True, exist_ok=True)
    marker = ledger_dir / f"v25_{gate}_{nonce}.consumed.json"
    payload = {
        "gate": gate,
        "nonce": nonce,
        "authorized_output_dir": str(expected),
    }
    encoded = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")
    try:
        with marker.open("xb") as handle:
            handle.write(encoded)
    except FileExistsError as exc:
        raise ValueError("release nonce was already consumed") from exc
    return marker
