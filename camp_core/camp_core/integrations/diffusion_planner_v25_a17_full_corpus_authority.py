"""One-shot A1.7 authority for the corrected 1,500x64 train corpus.

This module deliberately binds the already reviewed A1.7 bounded evidence to
the existing full-corpus runner without reusing the historical A1.5 seven-root
release chain.  It authorizes configuration preflight or corrected-corpus
execution only; training, calibration, Scene/V2I, Fresh, and outcome access
remain closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .diffusion_planner_artifact_seal import verify_complete_seal
from .diffusion_planner_v25_a163_bounded_authority import (
    EXPECTED_FIXED_DP_ARGS,
    EXPECTED_FIXED_DP_CHECKPOINT,
    EXPECTED_GENERATION_SCALES,
    EXPECTED_PROBE_TEMPLATE,
    EXPECTED_PROBE_TEMPLATE_SHA256,
    EXPECTED_STATIC_WEIGHT_VALUES,
    EXPECTED_STATIC_WEIGHTS,
    ROOT_ROLES as BOUNDED_ROOT_ROLES,
    verify_four_root_chain,
    verify_frozen_execution_assets,
)
from .diffusion_planner_v25_full_r_authority import (
    FIXED_DP_HEAD,
    REJECTED_PARTIAL_ROOT_SHA256,
    build_critical_implementation_manifest,
    canonical_json_bytes,
    canonical_sha256,
    strict_json_equal,
    verify_dual_head_contract,
)


PREFLIGHT_RELEASE_SCHEMA_VERSION = (
    "camp_dp_v25_a17_full_config_preflight_release_v1"
)
EXECUTE_RELEASE_SCHEMA_VERSION = "camp_dp_v25_a17_full_corpus_execute_release_v1"
PREFLIGHT_RELEASE_STATUS = "a17_full_config_preflight_released"
EXECUTE_RELEASE_STATUS = "a17_full_corpus_execute_released"
PREFLIGHT_GATE = "a17_full_config_preflight"
EXECUTE_GATE = "a17_full_corpus_execute"
NONCE_LEDGER = Path("/root/autodl-tmp/.camp_dp_v25_a17_full_corpus_nonces")
EXPECTED_EXECUTABLE_IDENTITIES = 1500
EXPECTED_RETAINED_INELIGIBLE = 153
EXPECTED_SEED = 25001
EXPECTED_CORPUS_STEPS = 64
EXPECTED_SNAPSHOT_CAPACITY = 96000

UPSTREAM_ROLES = (
    "source",
    "source_review",
    "bounded_plan",
    "bounded_plan_review",
    "bounded_release",
    "bounded_execution",
    "bounded_execution_review",
)
RELEASE_PAYLOADS = sorted({"COMMAND", "HEADS", "decision.json", "run.exit"})
_SHA_RE = re.compile(r"[0-9a-f]{64}")
_BASE_RELEASE_FIELDS = {
    "schema_version", "status", "gate", "implementation_source_head",
    "pointer_head_at_release", "fixed_dp_head", "formal_artifact",
    "formal_root_sha256", "probe_template", "probe_template_sha256",
    "generation_scales", "static_weights", "dp_repo", "fixed_dp_checkpoint",
    "fixed_dp_args_json", "native_source_roots", "root_artifacts",
    "root_artifacts_sha256", "bounded_prerequisite_summary",
    "critical_implementation_manifest", "critical_implementation_manifest_sha256",
    "run_nonce", "authorized_output_dir", "seed", "executable_identity_count",
    "retained_source_ineligible_count", "corpus_steps", "snapshot_capacity",
    "device", "rejected_roots", "monitor_enabled", "training_executed",
    "calibration_executed", "scene_runtime_enabled", "v2i_enabled",
    "fresh_b2_opened", "outcome_fields_consumed",
    "full_config_preflight_authorized", "full_r_execute_authorized",
}
PREFLIGHT_RELEASE_FIELDS = frozenset(_BASE_RELEASE_FIELDS)
EXECUTE_RELEASE_FIELDS = frozenset(
    _BASE_RELEASE_FIELDS
    | {
        "preflight_artifact", "preflight_root_sha256",
        "preflight_review_artifact", "preflight_review_root_sha256",
        "preflight_release_artifact", "preflight_release_root_sha256",
        "preflight_release_run_nonce",
    }
)


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA_RE.fullmatch(value) is not None


def _reject_constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON constant is forbidden: {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _load_canonical_object(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    try:
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"authority JSON is not strict UTF-8 JSON: {path}") from exc
    if type(value) is not dict or data != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical object bytes: {path}")
    return value


def _canonical_output(value: Any, *, label: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{label} must be a native nonempty string")
    path = Path(value)
    resolved = path.resolve()
    if not path.is_absolute() or value != str(resolved) or path.is_symlink():
        raise ValueError(f"{label} is not an absolute canonical path")
    return value


def _binding(value: Any, *, role: str) -> tuple[Path, str, str]:
    if type(value) is not dict or set(value) != {
        "path",
        "root_sha256",
        "report_file",
    }:
        raise ValueError(f"A1.7 upstream {role} binding schema drifted")
    path = Path(value["path"])
    root = value["root_sha256"]
    report_file = value["report_file"]
    if (
        not path.is_absolute()
        or str(path.resolve()) != str(path)
        or not _is_sha256(root)
        or type(report_file) is not str
        or Path(report_file).name != report_file
        or report_file
        != ("decision.json" if role == "bounded_release" else "report.json")
    ):
        raise ValueError(f"A1.7 upstream {role} binding is unsafe")
    return path, root, report_file


def verify_upstream_chain(
    *,
    bindings: Mapping[str, Any],
    repo: Path,
    dp_repo: Path,
    probe_template: Path,
) -> dict[str, Any]:
    """Verify the four static roots and bounded release/execution/review chain."""

    if type(bindings) is not dict or set(bindings) != set(UPSTREAM_ROLES):
        raise ValueError("A1.7 full-corpus release does not bind exact upstream roles")
    rows = {role: _binding(bindings[role], role=role) for role in UPSTREAM_ROLES}

    release_path, release_root, _ = rows["bounded_release"]
    release_seal = verify_complete_seal(
        release_path, release_root, label="V25 A1.7 bounded release prerequisite"
    )
    if release_seal["manifest_paths"] != RELEASE_PAYLOADS:
        raise ValueError("A1.7 bounded release prerequisite inventory drifted")
    release = _load_canonical_object(release_path / "decision.json")
    bounded_source_head = release.get("implementation_source_head")
    if (
        not _is_sha256(bounded_source_head)
        or release.get("pointer_head_at_release") != bounded_source_head
        or release.get("fixed_dp_head") != FIXED_DP_HEAD
        or release.get("run_count") != 244
        or release.get("unique_identity_count") != 243
        or release.get("snapshot_capacity") != 15616
        or release.get("bounded_execute_authorized") is not True
        or release.get("full_config_preflight_authorized") is not False
        or release.get("full_r_execute_authorized") is not False
        or release.get("fresh_b2_opened") is not False
        or release.get("outcome_fields_consumed") != []
    ):
        raise ValueError("A1.7 bounded release prerequisite contract drifted")

    static_bindings = {
        role: dict(bindings[role]) for role in BOUNDED_ROOT_ROLES
    }
    if not strict_json_equal(release.get("root_artifacts"), static_bindings):
        raise ValueError("A1.7 bounded release/static-root binding drifted")
    verify_four_root_chain(
        bindings=static_bindings,
        implementation_source_head=bounded_source_head,
        fixed_dp_head=FIXED_DP_HEAD,
    )

    execution_path, execution_root, _ = rows["bounded_execution"]
    execution_seal = verify_complete_seal(
        execution_path,
        execution_root,
        label="V25 A1.7 bounded execution prerequisite",
    )
    execution = _load_canonical_object(execution_path / "report.json")
    terminal = execution.get("terminal")
    coverage = terminal.get("fixed_dp_support_coverage") if type(terminal) is dict else None
    if (
        execution_seal["root_sha256"] != execution_root
        or execution.get("schema_version")
        != "camp_dp_v25_a1610_bounded_execution_v8"
        or execution.get("status") != "passed_exact_bounded_execution"
        or execution.get("run_count") != 244
        or execution.get("unique_identity_count") != 243
        or execution.get("snapshot_count") != 15488
        or execution.get("retained_capability_failure_count") != 2
        or execution.get("mapped_runtime_source_failure_count") != 0
        or execution.get("sequential_fixed_k8") is not True
        or execution.get("candidate_tensors_modified") is not False
        or execution.get("full_r_execute_authorized") is not False
        or execution.get("training_executed") is not False
        or execution.get("calibration_executed") is not False
        or execution.get("fresh_b2_opened") is not False
        or execution.get("outcome_fields_consumed") != []
        or type(terminal) is not dict
        or terminal.get("status") != "passed_exact_bounded_terminal"
        or terminal.get("run_count") != 244
        or terminal.get("unique_identity_count") != 243
        or terminal.get("tick_count") != 15488
        or terminal.get("identity0_repeat_deterministic") is not True
        or type(coverage) is not dict
        or coverage.get("passed") is not True
        or coverage.get("complete_unique_identity_count") != 241
    ):
        raise ValueError("A1.7 bounded execution prerequisite contract drifted")

    review_path, review_root, _ = rows["bounded_execution_review"]
    review_seal = verify_complete_seal(
        review_path,
        review_root,
        label="V25 A1.7 bounded execution review prerequisite",
    )
    review = _load_canonical_object(review_path / "report.json")
    if (
        review_seal["root_sha256"] != review_root
        or review.get("schema_version")
        != "camp_dp_v25_a17_bounded_execution_review_v11"
        or review.get("status") != "passed_independent_bounded_execution_review"
        or review.get("fixed_dp_head") != FIXED_DP_HEAD
        or Path(str(review.get("reviewed_artifact"))).resolve()
        != execution_path.resolve()
        or review.get("reviewed_root_sha256") != execution_root
        or review.get("release_root_sha256") != release_root
        or not strict_json_equal(review.get("root_artifacts"), static_bindings)
        or review.get("run_count") != 244
        or review.get("unique_identity_count") != 243
        or review.get("snapshot_count") != 15488
        or review.get("retained_capability_failure_count") != 2
        or review.get("mapped_runtime_source_failure_count") != 0
        or review.get("full_r_execute_authorized") is not False
        or review.get("fresh_b2_opened") is not False
        or review.get("outcome_fields_consumed") != []
        or type(review.get("identity0_repeat_comparison")) is not dict
        or not all(review["identity0_repeat_comparison"].values())
    ):
        raise ValueError("A1.7 bounded independent-review prerequisite drifted")

    # Reopen the frozen model-side assets without permitting any DP mutation.
    assets = verify_frozen_execution_assets(
        repo=repo,
        dp_repo=dp_repo,
        probe_template=probe_template,
    )
    return {
        "bounded_source_head": bounded_source_head,
        "release_root_sha256": release_root,
        "execution_root_sha256": execution_root,
        "review_root_sha256": review_root,
        "execution_assets": assets,
    }


def _base_decision(
    *,
    repo: Path,
    implementation_source_head: str,
    pointer_head_at_release: str,
    root_artifacts: Mapping[str, Any],
    run_nonce: str,
    authorized_output_dir: str,
    dp_repo: Path,
    probe_template: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not _is_sha256(run_nonce):
        raise ValueError("A1.7 full-corpus nonce must be lowercase 64-hex")
    output = _canonical_output(authorized_output_dir, label="authorized output")
    upstream = verify_upstream_chain(
        bindings=root_artifacts,
        repo=repo,
        dp_repo=dp_repo,
        probe_template=probe_template,
    )
    assets = verify_frozen_execution_assets(
        repo=repo, dp_repo=dp_repo, probe_template=probe_template
    )
    manifest = build_critical_implementation_manifest(repo)
    verify_dual_head_contract(
        repo=repo,
        implementation_source_head=implementation_source_head,
        current_pointer_head=pointer_head_at_release,
        implementation_manifest=manifest,
    )
    template = json.loads(probe_template.read_text(encoding="utf-8"))
    fixed = template["fixed_dp"]
    roots = json.loads(json.dumps(root_artifacts))
    base = {
        "implementation_source_head": implementation_source_head,
        "pointer_head_at_release": pointer_head_at_release,
        "fixed_dp_head": FIXED_DP_HEAD,
        "formal_artifact": (
            "/root/autodl-tmp/camp_dp_v25_controlled_corpus_source_freeze_retry2_"
            "ff028387_20260717T140842CST"
        ),
        "formal_root_sha256": (
            "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
        ),
        "probe_template": str(probe_template.resolve()),
        "probe_template_sha256": EXPECTED_PROBE_TEMPLATE_SHA256,
        "generation_scales": dict(EXPECTED_GENERATION_SCALES),
        "static_weights": json.loads(json.dumps(template["selector"]["weights"])),
        "dp_repo": str(dp_repo.resolve()),
        "fixed_dp_checkpoint": fixed["checkpoint"],
        "fixed_dp_args_json": fixed["args_json"],
        "native_source_roots": {
            "s01_preflight": "bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451",
            "s01_review": "facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d",
        },
        "root_artifacts": roots,
        "root_artifacts_sha256": canonical_sha256(roots),
        "bounded_prerequisite_summary": upstream,
        "critical_implementation_manifest": manifest,
        "critical_implementation_manifest_sha256": canonical_sha256(manifest),
        "run_nonce": run_nonce,
        "authorized_output_dir": output,
        "seed": EXPECTED_SEED,
        "executable_identity_count": EXPECTED_EXECUTABLE_IDENTITIES,
        "retained_source_ineligible_count": EXPECTED_RETAINED_INELIGIBLE,
        "corpus_steps": EXPECTED_CORPUS_STEPS,
        "snapshot_capacity": EXPECTED_SNAPSHOT_CAPACITY,
        "device": "cuda",
        "rejected_roots": [REJECTED_PARTIAL_ROOT_SHA256],
        "monitor_enabled": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if (
        not strict_json_equal(
            {key: assets["fixed_dp_checkpoint"][key] for key in ("path", "sha256")},
            EXPECTED_FIXED_DP_CHECKPOINT,
        )
        or not strict_json_equal(
            {key: assets["fixed_dp_args_json"][key] for key in ("path", "sha256")},
            EXPECTED_FIXED_DP_ARGS,
        )
        or not strict_json_equal(assets["generation_scales"], EXPECTED_GENERATION_SCALES)
        or not strict_json_equal(
            {key: assets["static_weights"][key] for key in ("path", "sha256")},
            EXPECTED_STATIC_WEIGHTS,
        )
        or tuple(assets["static_weights"]["values"]) != EXPECTED_STATIC_WEIGHT_VALUES
    ):
        raise ValueError("A1.7 full-corpus frozen execution assets drifted")
    return base, upstream


def build_preflight_release_decision(**kwargs: Any) -> dict[str, Any]:
    base, _ = _base_decision(**kwargs)
    return {
        "schema_version": PREFLIGHT_RELEASE_SCHEMA_VERSION,
        "status": PREFLIGHT_RELEASE_STATUS,
        "gate": PREFLIGHT_GATE,
        **base,
        "full_config_preflight_authorized": True,
        "full_r_execute_authorized": False,
    }


def build_execute_release_decision(
    *,
    preflight_artifact: Path,
    preflight_root_sha256: str,
    preflight_review_artifact: Path,
    preflight_review_root_sha256: str,
    **kwargs: Any,
) -> dict[str, Any]:
    base, _ = _base_decision(**kwargs)
    preflight = verify_complete_seal(
        preflight_artifact,
        preflight_root_sha256,
        label="V25 A1.7 full-config preflight",
    )
    review = verify_complete_seal(
        preflight_review_artifact,
        preflight_review_root_sha256,
        label="V25 A1.7 full-config preflight review",
    )
    preflight_report = _load_canonical_object(preflight_artifact / "report.json")
    review_report = _load_canonical_object(preflight_review_artifact / "report.json")
    if (
        preflight_report.get("status") != "passed"
        or preflight_report.get("mode") != "preflight"
        or review_report.get("status")
        != "passed_independent_1500_config_preflight_review_execute_closed"
        or review_report.get("reviewed_root_sha256") != preflight["root_sha256"]
        or review_report.get("identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or review_report.get("full_r_execute_authorized") is not False
        or review_report.get("fresh_b2_opened") is not False
        or review_report.get("outcome_fields_consumed") != []
        or type(preflight_report.get("release_run_nonce")) is not str
        or not _is_sha256(preflight_report.get("release_run_nonce"))
        or type(
            preflight_report.get("ultra_full_config_preflight_release_artifact")
        )
        is not str
        or not _is_sha256(
            preflight_report.get(
                "ultra_full_config_preflight_release_root_sha256"
            )
        )
    ):
        raise ValueError("A1.7 full-config preflight/review prerequisite drifted")
    return {
        "schema_version": EXECUTE_RELEASE_SCHEMA_VERSION,
        "status": EXECUTE_RELEASE_STATUS,
        "gate": EXECUTE_GATE,
        **base,
        "preflight_artifact": str(preflight_artifact.resolve()),
        "preflight_root_sha256": preflight["root_sha256"],
        "preflight_review_artifact": str(preflight_review_artifact.resolve()),
        "preflight_review_root_sha256": review["root_sha256"],
        "preflight_release_artifact": preflight_report[
            "ultra_full_config_preflight_release_artifact"
        ],
        "preflight_release_root_sha256": preflight_report[
            "ultra_full_config_preflight_release_root_sha256"
        ],
        "preflight_release_run_nonce": preflight_report["release_run_nonce"],
        "full_config_preflight_authorized": False,
        "full_r_execute_authorized": True,
    }


def _consume_nonce(*, gate: str, nonce: str, authorized: str, requested: str) -> Path:
    if gate not in {PREFLIGHT_GATE, EXECUTE_GATE} or not _is_sha256(nonce):
        raise ValueError("A1.7 full-corpus nonce/gate drifted")
    expected = _canonical_output(authorized, label="authorized output")
    actual = _canonical_output(requested, label="requested output")
    if actual != expected:
        raise ValueError("A1.7 full-corpus release output directory mismatch")
    NONCE_LEDGER.mkdir(parents=True, exist_ok=True)
    marker = NONCE_LEDGER / f"v25_{gate}_{nonce}.consumed.json"
    payload = {"gate": gate, "nonce": nonce, "authorized_output_dir": expected}
    try:
        with marker.open("xb") as handle:
            handle.write(canonical_json_bytes(payload))
    except FileExistsError as exc:
        raise ValueError("A1.7 full-corpus release nonce was already consumed") from exc
    return marker


def verify_release(
    *,
    repo: Path,
    release_artifact: Path,
    release_root_sha256: str,
    requested_output_dir: str,
    current_pointer_head: str,
    dp_repo: Path,
    probe_template: Path,
    mode: str,
    consume: bool,
) -> dict[str, Any]:
    if mode not in {"preflight", "execute"}:
        raise ValueError("A1.7 full-corpus release mode is invalid")
    seal = verify_complete_seal(
        release_artifact,
        release_root_sha256,
        label=f"V25 A1.7 full-corpus {mode} release",
    )
    if seal["manifest_paths"] != RELEASE_PAYLOADS or (
        release_artifact / "run.exit"
    ).read_bytes() != b"0\n":
        raise ValueError("A1.7 full-corpus release inventory/run.exit drifted")
    decision = _load_canonical_object(release_artifact / "decision.json")
    expected_schema = (
        PREFLIGHT_RELEASE_SCHEMA_VERSION if mode == "preflight" else EXECUTE_RELEASE_SCHEMA_VERSION
    )
    expected_status = PREFLIGHT_RELEASE_STATUS if mode == "preflight" else EXECUTE_RELEASE_STATUS
    expected_gate = PREFLIGHT_GATE if mode == "preflight" else EXECUTE_GATE
    expected_fields = (
        PREFLIGHT_RELEASE_FIELDS if mode == "preflight" else EXECUTE_RELEASE_FIELDS
    )
    heads = (release_artifact / "HEADS").read_bytes()
    expected_heads = (
        f"camp_source_head={decision.get('implementation_source_head')}\n"
        f"camp_pointer_head={decision.get('pointer_head_at_release')}\n"
        f"fixed_dp_head={FIXED_DP_HEAD}\n"
    ).encode("ascii")
    if (
        set(decision) != expected_fields
        or heads != expected_heads
        or not (release_artifact / "COMMAND").read_text(
            encoding="utf-8", errors="strict"
        ).strip()
    ):
        raise ValueError("A1.7 full-corpus release exact schema/HEADS drifted")
    exact = {
        "schema_version": expected_schema,
        "status": expected_status,
        "gate": expected_gate,
        "fixed_dp_head": FIXED_DP_HEAD,
        "seed": EXPECTED_SEED,
        "executable_identity_count": EXPECTED_EXECUTABLE_IDENTITIES,
        "retained_source_ineligible_count": EXPECTED_RETAINED_INELIGIBLE,
        "corpus_steps": EXPECTED_CORPUS_STEPS,
        "snapshot_capacity": EXPECTED_SNAPSHOT_CAPACITY,
        "device": "cuda",
        "monitor_enabled": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "full_config_preflight_authorized": mode == "preflight",
        "full_r_execute_authorized": mode == "execute",
        "rejected_roots": [REJECTED_PARTIAL_ROOT_SHA256],
    }
    for key, expected in exact.items():
        if not strict_json_equal(decision.get(key), expected):
            raise ValueError(f"A1.7 full-corpus release exact value drifted: {key}")
    if (
        not _is_sha256(decision.get("run_nonce"))
        or decision.get("pointer_head_at_release") != current_pointer_head
        or decision.get("critical_implementation_manifest_sha256")
        != canonical_sha256(decision.get("critical_implementation_manifest"))
        or decision.get("root_artifacts_sha256")
        != canonical_sha256(decision.get("root_artifacts"))
        or decision.get("probe_template") != str(probe_template.resolve())
        or decision.get("probe_template_sha256") != EXPECTED_PROBE_TEMPLATE_SHA256
        or decision.get("dp_repo") != str(dp_repo.resolve())
        or decision.get("formal_artifact")
        != (
            "/root/autodl-tmp/camp_dp_v25_controlled_corpus_source_freeze_retry2_"
            "ff028387_20260717T140842CST"
        )
        or decision.get("formal_root_sha256")
        != "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
        or not strict_json_equal(
            decision.get("generation_scales"), EXPECTED_GENERATION_SCALES
        )
        or decision.get("native_source_roots")
        != {
            "s01_preflight": "bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451",
            "s01_review": "facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d",
        }
    ):
        raise ValueError("A1.7 full-corpus release hash/path authority drifted")
    verify_dual_head_contract(
        repo=repo,
        implementation_source_head=decision["implementation_source_head"],
        current_pointer_head=current_pointer_head,
        implementation_manifest=decision["critical_implementation_manifest"],
    )
    upstream = verify_upstream_chain(
        bindings=decision["root_artifacts"],
        repo=repo,
        dp_repo=dp_repo,
        probe_template=probe_template,
    )
    if not strict_json_equal(decision.get("bounded_prerequisite_summary"), upstream):
        raise ValueError("A1.7 bounded prerequisite summary drifted")
    template = json.loads(probe_template.read_text(encoding="utf-8"))
    fixed = template.get("fixed_dp")
    selector = template.get("selector")
    if (
        type(fixed) is not dict
        or type(selector) is not dict
        or decision.get("fixed_dp_checkpoint") != fixed.get("checkpoint")
        or decision.get("fixed_dp_args_json") != fixed.get("args_json")
        or decision.get("static_weights") != selector.get("weights")
    ):
        raise ValueError("A1.7 full-corpus release fixed asset fields drifted")
    if mode == "execute":
        preflight_artifact = Path(str(decision.get("preflight_artifact")))
        preflight_review_artifact = Path(
            str(decision.get("preflight_review_artifact"))
        )
        preflight_release_artifact = Path(
            str(decision.get("preflight_release_artifact"))
        )
        preflight_seal = verify_complete_seal(
            preflight_artifact,
            decision.get("preflight_root_sha256"),
            label="V25 A1.7 execute-release preflight binding",
        )
        review_seal = verify_complete_seal(
            preflight_review_artifact,
            decision.get("preflight_review_root_sha256"),
            label="V25 A1.7 execute-release preflight-review binding",
        )
        release_seal = verify_complete_seal(
            preflight_release_artifact,
            decision.get("preflight_release_root_sha256"),
            label="V25 A1.7 execute-release preflight-release binding",
        )
        preflight_report = _load_canonical_object(preflight_artifact / "report.json")
        review_report = _load_canonical_object(
            preflight_review_artifact / "report.json"
        )
        if (
            preflight_seal["root_sha256"] != decision.get("preflight_root_sha256")
            or review_seal["root_sha256"]
            != decision.get("preflight_review_root_sha256")
            or release_seal["root_sha256"]
            != decision.get("preflight_release_root_sha256")
            or preflight_report.get("status") != "passed"
            or review_report.get("status")
            != "passed_independent_1500_config_preflight_review_execute_closed"
            or review_report.get("reviewed_root_sha256")
            != preflight_seal["root_sha256"]
            or preflight_report.get("release_run_nonce")
            != decision.get("preflight_release_run_nonce")
            or preflight_report.get(
                "ultra_full_config_preflight_release_root_sha256"
            )
            != release_seal["root_sha256"]
        ):
            raise ValueError("A1.7 execute release preflight chain drifted")
    marker = None
    if consume:
        marker = _consume_nonce(
            gate=expected_gate,
            nonce=decision["run_nonce"],
            authorized=decision["authorized_output_dir"],
            requested=requested_output_dir,
        )
    return {
        "release_artifact": str(release_artifact.resolve()),
        "release_root_sha256": seal["root_sha256"],
        "decision": decision,
        "upstream": upstream,
        "nonce_marker": None
        if marker is None
        else {
            "path": str(marker),
            "sha256": hashlib.sha256(marker.read_bytes()).hexdigest(),
        },
    }
