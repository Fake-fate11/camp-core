from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

import numpy as np

from .diffusion_planner_artifact_seal import verify_complete_seal
from .diffusion_planner_v25_full_r_authority import (
    CRITICAL_IMPLEMENTATION_PATHS,
    FIXED_DP_HEAD,
    build_critical_implementation_manifest,
    canonical_json_bytes,
    canonical_sha256,
    strict_json_equal,
    verify_dual_head_contract,
)


RELEASE_SCHEMA_VERSION = "camp_dp_v25_ultra_a164_bounded_execute_release_v2"
RELEASE_STATUS = "bounded_execute_released"
RELEASE_GATE = "a164_bounded_execute"
NONCE_LEDGER = Path("/root/autodl-tmp/.camp_dp_v25_a164_bounded_execute_nonces")
EXPECTED_SEED = 25001
EXPECTED_UNIQUE_IDENTITIES = 243
EXPECTED_RUNS = 244
EXPECTED_TICKS = 15616
PLAN_SCHEMA_VERSION = "camp_dp_v25_a162_route_level_bounded_execution_plan_v2"
SOURCE_STATUS = "passed_source_only_route_signal_authority_census"
SOURCE_REVIEW_STATUS = "passed_independent_route_signal_source_review"
PLAN_STATUS = "passed_bounded_execution_plan_preflight_k8_execute_closed"
PLAN_REVIEW_STATUS = "passed_independent_bounded_execution_plan_review_k8_closed"

EXPECTED_CAMP_REPO = Path("/root/autodl-tmp/camp_core")
EXPECTED_DP_REPO = Path("/root/autodl-tmp/Diffusion-Planner")
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
    "path": (
        "/root/autodl-tmp/camp_core/configs/integrations/"
        "diffusion_planner_v25_atom_scales_correction_v2.json"
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
EXPECTED_STATIC_WEIGHT_VALUES = (
    0.10947278201682221,
    4.5339121051258635e-14,
    4.436657731585812e-14,
    0.33777087074295037,
    7.284723165939581e-10,
    0.0,
    0.0,
    0.0,
    0.34158690923521606,
    0.10033962151340078,
    0.0,
    0.1108291578563568,
    6.579066917788303e-07,
    0.0,
)
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

ROOT_ROLES = (
    "source",
    "source_review",
    "bounded_plan",
    "bounded_plan_review",
)
ROOT_PAYLOADS = {
    "source": sorted(
        {
            "COMMAND",
            "HEADS",
            "formal_route_source_contract_supplement.json",
            "report.json",
            "route_signal_source_receipts.json",
            "run.exit",
        }
    ),
    "source_review": sorted({"COMMAND", "HEADS", "report.json", "run.exit"}),
    "bounded_plan": sorted(
        {"COMMAND", "HEADS", "bounded_execution_plan.json", "report.json", "run.exit"}
    ),
    "bounded_plan_review": sorted(
        {"COMMAND", "HEADS", "report.json", "run.exit"}
    ),
}
RELEASE_PAYLOADS = sorted({"COMMAND", "HEADS", "decision.json", "run.exit"})
ROOT_REPORT_FILES = {
    "source": "report.json",
    "source_review": "report.json",
    "bounded_plan": "report.json",
    "bounded_plan_review": "report.json",
}


def _is_sha256(value: Any) -> bool:
    return (
        type(value) is str
        and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    )


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"authority JSON is not an exact object: {path}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()


def _require_exact_path(actual: Path, expected: Path, *, label: str) -> Path:
    if (
        not actual.is_absolute()
        or str(actual) != str(expected)
        or actual.is_symlink()
        or actual.resolve() != expected.resolve()
    ):
        raise ValueError(f"{label} must use the frozen canonical path")
    return actual.resolve()


def _verify_exact_asset(contract: Mapping[str, Any], *, label: str) -> Path:
    if type(contract) is not dict or set(contract) != {"path", "sha256"}:
        raise ValueError(f"{label} asset contract drifted")
    path = _canonical_absolute_path(contract["path"], label=f"{label} path")
    if path.is_symlink() or not path.is_file() or _file_sha256(path) != contract["sha256"]:
        raise ValueError(f"{label} asset bytes drifted")
    return path


def verify_frozen_execution_assets(
    *, repo: Path, dp_repo: Path, probe_template: Path
) -> dict[str, Any]:
    """Bind A1.6.4 execution to one template/weights/fixed-DP universe."""

    camp = _require_exact_path(repo, EXPECTED_CAMP_REPO, label="CAMP repository")
    dp = _require_exact_path(dp_repo, EXPECTED_DP_REPO, label="fixed-DP repository")
    template_path = _require_exact_path(
        probe_template, EXPECTED_PROBE_TEMPLATE, label="probe template"
    )
    if (
        not camp.is_dir()
        or not dp.is_dir()
        or _git(dp, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(dp, "status", "--porcelain")
        or not template_path.is_file()
        or _file_sha256(template_path) != EXPECTED_PROBE_TEMPLATE_SHA256
    ):
        raise ValueError("bounded frozen repository/template authority drifted")

    template = _load_object(template_path)
    fixed = template.get("fixed_dp")
    selector = template.get("selector")
    if (
        template.get("schema_version") != EXPECTED_PROBE_TEMPLATE_SCHEMA_VERSION
        or type(fixed) is not dict
        or set(fixed)
        != {"repo", "head", "checkpoint", "args_json", "native_source_sha256"}
        or fixed.get("repo") != str(EXPECTED_DP_REPO)
        or fixed.get("head") != FIXED_DP_HEAD
        or not strict_json_equal(fixed.get("checkpoint"), EXPECTED_FIXED_DP_CHECKPOINT)
        or not strict_json_equal(fixed.get("args_json"), EXPECTED_FIXED_DP_ARGS)
        or not strict_json_equal(
            fixed.get("native_source_sha256"), EXPECTED_DP_NATIVE_SOURCE_SHA256
        )
        or type(selector) is not dict
        or not strict_json_equal(selector.get("weights"), EXPECTED_STATIC_WEIGHTS)
        or selector.get("candidate_k") != 8
        or selector.get("nonnegative_simplex") is not True
        or selector.get("selection_policy") != "v22_source_valid"
        or selector.get("score_contract") != "score_k(w)=a_k^T w"
    ):
        raise ValueError("bounded canonical template content drifted")

    generation_path = _verify_exact_asset(
        EXPECTED_GENERATION_SCALES, label="generation scales"
    )
    weights_path = _verify_exact_asset(EXPECTED_STATIC_WEIGHTS, label="static weights")
    checkpoint_path = _verify_exact_asset(
        EXPECTED_FIXED_DP_CHECKPOINT, label="fixed-DP checkpoint"
    )
    args_path = _verify_exact_asset(EXPECTED_FIXED_DP_ARGS, label="fixed-DP args")
    args_payload = _load_object(args_path)
    if not args_payload:
        raise ValueError("fixed-DP args content is empty")

    weights = np.load(weights_path, allow_pickle=False)
    expected_weights = np.asarray(EXPECTED_STATIC_WEIGHT_VALUES, dtype=np.float64)
    if (
        weights.dtype != np.dtype(np.float64)
        or weights.shape != (14,)
        or not np.array_equal(weights, expected_weights)
        or not np.all(np.isfinite(weights))
        or np.any(weights < 0.0)
        or not np.isclose(float(weights.sum()), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("static weight content/value contract drifted")

    native_receipts: dict[str, dict[str, str]] = {}
    for relative, expected_sha256 in EXPECTED_DP_NATIVE_SOURCE_SHA256.items():
        source = dp / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError("fixed-DP native source path drifted")
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative],
            cwd=dp,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        committed = subprocess.run(
            ["git", "show", f"{FIXED_DP_HEAD}:{relative}"],
            cwd=dp,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        actual = source.read_bytes()
        digest = hashlib.sha256(actual).hexdigest()
        if actual != committed or digest != expected_sha256:
            raise ValueError("fixed-DP native source differs from frozen git object")
        native_receipts[relative] = {
            "path": str(source.resolve()),
            "sha256": digest,
        }

    return {
        "probe_template": {
            "path": str(template_path),
            "sha256": EXPECTED_PROBE_TEMPLATE_SHA256,
            "schema_version": EXPECTED_PROBE_TEMPLATE_SCHEMA_VERSION,
        },
        "generation_scales": dict(EXPECTED_GENERATION_SCALES),
        "static_weights": {
            **EXPECTED_STATIC_WEIGHTS,
            "dtype": "float64",
            "shape": [14],
            "values": expected_weights.tolist(),
        },
        "fixed_dp_checkpoint": {
            **EXPECTED_FIXED_DP_CHECKPOINT,
            "size_bytes": checkpoint_path.stat().st_size,
        },
        "fixed_dp_args_json": {
            **EXPECTED_FIXED_DP_ARGS,
            "content_sha256": canonical_sha256(args_payload),
        },
        "native_sources": native_receipts,
        "generation_scales_size_bytes": generation_path.stat().st_size,
    }


def _parse_heads(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if line.count("=") != 1:
            raise ValueError("bounded authority HEADS is malformed")
        key, value = line.split("=", 1)
        if not key or not value or key in fields:
            raise ValueError("bounded authority HEADS has empty/duplicate keys")
        fields[key] = value
    if set(fields) not in (
        {"camp_source_head", "fixed_dp_head"},
        {"camp_source_head", "camp_pointer_head", "fixed_dp_head"},
        {"review_head", "fixed_dp_head"},
    ):
        raise ValueError("bounded authority HEADS key set drifted")
    return fields


def _canonical_absolute_path(value: Any, *, label: str) -> Path:
    if type(value) is not str or not value:
        raise ValueError(f"{label} must be a native nonempty string")
    raw = Path(value)
    resolved = raw.resolve()
    if not raw.is_absolute() or value != str(resolved):
        raise ValueError(f"{label} must be an absolute canonical path")
    return resolved


def verify_four_root_chain(
    *,
    bindings: Mapping[str, Any],
    implementation_source_head: str,
    fixed_dp_head: str,
) -> dict[str, Any]:
    """Open and bind the exact A1.6 source/design roots required by execution."""

    if fixed_dp_head != FIXED_DP_HEAD:
        raise ValueError("bounded authority fixed DP drifted")
    if type(bindings) is not dict or set(bindings) != set(ROOT_ROLES):
        raise ValueError("bounded release must bind the exact four prerequisite roots")
    verified: dict[str, Any] = {}
    for role in ROOT_ROLES:
        binding = bindings[role]
        if type(binding) is not dict or set(binding) != {
            "path",
            "root_sha256",
            "report_file",
        }:
            raise ValueError(f"{role} binding schema drifted")
        artifact = _canonical_absolute_path(binding["path"], label=f"{role} path")
        root = binding["root_sha256"]
        report_file = binding["report_file"]
        if not _is_sha256(root) or report_file != ROOT_REPORT_FILES[role]:
            raise ValueError(f"{role} root/report binding drifted")
        seal = verify_complete_seal(artifact, root, label=f"V25 A1.6.4 {role}")
        if (
            seal["manifest_paths"] != ROOT_PAYLOADS[role]
            or (artifact / "run.exit").read_bytes() != b"0\n"
        ):
            raise ValueError(f"{role} inventory/run.exit drifted")
        report = _load_object(artifact / report_file)
        heads = _parse_heads(artifact / "HEADS")
        source_head = heads.get("camp_source_head") or heads.get("review_head")
        if source_head != implementation_source_head or heads["fixed_dp_head"] != fixed_dp_head:
            raise ValueError(f"{role} HEAD authority drifted")
        verified[role] = {
            "path": str(artifact),
            "root_sha256": seal["root_sha256"],
            "report": report,
        }

    source = verified["source"]["report"]
    source_review = verified["source_review"]["report"]
    plan_report = verified["bounded_plan"]["report"]
    plan_review = verified["bounded_plan_review"]["report"]
    plan = _load_object(
        Path(verified["bounded_plan"]["path"]) / "bounded_execution_plan.json"
    )
    source_authority = source.get("authority")
    if (
        source.get("status") != SOURCE_STATUS
        or type(source_authority) is not dict
        or source_authority.get("camp_source_head") != implementation_source_head
        or source_authority.get("fixed_dp_head") != fixed_dp_head
        or source.get("fresh_b2_opened") is not False
        or source.get("outcome_fields_consumed") != []
        or source_review.get("status") != SOURCE_REVIEW_STATUS
        or source_review.get("camp_source_head") != implementation_source_head
        or source_review.get("fixed_dp_head") != fixed_dp_head
        or source_review.get("reviewed_root_sha256")
        != verified["source"]["root_sha256"]
        or Path(str(source_review.get("reviewed_artifact"))).resolve()
        != Path(verified["source"]["path"])
        or plan_report.get("status") != PLAN_STATUS
        or plan_report.get("camp_source_head") != implementation_source_head
        or plan_report.get("fixed_dp_head") != fixed_dp_head
        or plan_report.get("source_root_sha256")
        != verified["source"]["root_sha256"]
        or plan_report.get("source_review_root_sha256")
        != verified["source_review"]["root_sha256"]
        or plan_report.get("plan_sha256") != canonical_sha256(plan)
        or plan_review.get("status") != PLAN_REVIEW_STATUS
        or plan_review.get("review_head") != implementation_source_head
        or plan_review.get("fixed_dp_head") != fixed_dp_head
        or plan_review.get("reviewed_root_sha256")
        != verified["bounded_plan"]["root_sha256"]
        or Path(str(plan_review.get("reviewed_artifact"))).resolve()
        != Path(verified["bounded_plan"]["path"])
        or plan_review.get("source_root_sha256")
        != verified["source"]["root_sha256"]
        or plan_review.get("source_review_root_sha256")
        != verified["source_review"]["root_sha256"]
    ):
        raise ValueError("bounded four-root cross-link/status authority drifted")
    validate_bounded_plan(plan)
    return {"verified": verified, "plan": plan}


def validate_bounded_plan(plan: Mapping[str, Any]) -> None:
    """Validate exact bounded denominator/order without opening producer code."""

    if (
        type(plan) is not dict
        or plan.get("schema_version") != PLAN_SCHEMA_VERSION
        or plan.get("status") != "passed_preflight_plan_k8_execute_closed"
        or type(plan.get("seed")) is not int
        or plan["seed"] != EXPECTED_SEED
        or type(plan.get("unique_identity_count")) is not int
        or plan["unique_identity_count"] != EXPECTED_UNIQUE_IDENTITIES
        or type(plan.get("run_count")) is not int
        or plan["run_count"] != EXPECTED_RUNS
        or type(plan.get("snapshot_capacity")) is not int
        or plan["snapshot_capacity"] != EXPECTED_TICKS
        or plan.get("sequential_fixed_k8") is not True
        or plan.get("k8_executed") is not False
        or plan.get("candidate_generation_started") is not False
        or plan.get("model_loaded") is not False
        or plan.get("simulator_started") is not False
        or plan.get("training_executed") is not False
        or plan.get("calibration_executed") is not False
        or plan.get("fresh_b2_opened") is not False
        or plan.get("outcome_fields_consumed") != []
    ):
        raise ValueError("bounded plan execution contract drifted")
    runs = plan.get("runs")
    if type(runs) is not list or len(runs) != EXPECTED_RUNS:
        raise ValueError("bounded plan run denominator drifted")
    for ordinal, run in enumerate(runs):
        if (
            type(run) is not dict
            or type(run.get("run_ordinal")) is not int
            or run["run_ordinal"] != ordinal
            or type(run.get("ticks")) is not int
            or run["ticks"] != 64
            or type(run.get("seed")) is not int
            or run["seed"] != EXPECTED_SEED
        ):
            raise ValueError("bounded plan run order/type drifted")
    if (
        runs[0].get("occurrence") != "identity0_first"
        or runs[-1].get("occurrence") != "identity0_final_repeat"
        or runs[0].get("scenario_id") != runs[-1].get("scenario_id")
        or len({run.get("scenario_id") for run in runs[:-1]})
        != EXPECTED_UNIQUE_IDENTITIES
    ):
        raise ValueError("bounded identity0 repeat/order contract drifted")


RELEASE_FIELDS = {
    "schema_version",
    "status",
    "gate",
    "implementation_source_head",
    "pointer_head_at_release",
    "fixed_dp_head",
    "dp_repo",
    "probe_template",
    "probe_template_sha256",
    "execution_assets",
    "execution_assets_sha256",
    "critical_implementation_manifest",
    "critical_implementation_manifest_sha256",
    "root_artifacts",
    "root_artifacts_sha256",
    "run_nonce",
    "authorized_output_dir",
    "seed",
    "unique_identity_count",
    "run_count",
    "snapshot_capacity",
    "bounded_execute_authorized",
    "full_config_preflight_authorized",
    "full_r_execute_authorized",
    "monitor_enabled",
    "training_executed",
    "calibration_executed",
    "scene_runtime_enabled",
    "v2i_enabled",
    "fresh_b2_opened",
    "outcome_fields_consumed",
}


def build_release_decision(
    *,
    repo: Path,
    implementation_source_head: str,
    pointer_head_at_release: str,
    root_artifacts: Mapping[str, Any],
    run_nonce: str,
    authorized_output_dir: str,
    dp_repo: Path,
    probe_template: Path,
) -> dict[str, Any]:
    if not _is_sha256(run_nonce):
        raise ValueError("bounded release nonce must be a lowercase 64-hex string")
    _canonical_absolute_path(authorized_output_dir, label="authorized output directory")
    assets = verify_frozen_execution_assets(
        repo=repo, dp_repo=dp_repo, probe_template=probe_template
    )
    canonical_dp = dp_repo.resolve()
    canonical_template = probe_template.resolve()
    manifest = build_critical_implementation_manifest(repo)
    verify_dual_head_contract(
        repo=repo,
        implementation_source_head=implementation_source_head,
        current_pointer_head=pointer_head_at_release,
        implementation_manifest=manifest,
    )
    verify_four_root_chain(
        bindings=root_artifacts,
        implementation_source_head=implementation_source_head,
        fixed_dp_head=FIXED_DP_HEAD,
    )
    roots = json.loads(json.dumps(root_artifacts))
    return {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "status": RELEASE_STATUS,
        "gate": RELEASE_GATE,
        "implementation_source_head": implementation_source_head,
        "pointer_head_at_release": pointer_head_at_release,
        "fixed_dp_head": FIXED_DP_HEAD,
        "dp_repo": str(canonical_dp),
        "probe_template": str(canonical_template),
        "probe_template_sha256": EXPECTED_PROBE_TEMPLATE_SHA256,
        "execution_assets": assets,
        "execution_assets_sha256": canonical_sha256(assets),
        "critical_implementation_manifest": manifest,
        "critical_implementation_manifest_sha256": canonical_sha256(manifest),
        "root_artifacts": roots,
        "root_artifacts_sha256": canonical_sha256(roots),
        "run_nonce": run_nonce,
        "authorized_output_dir": authorized_output_dir,
        "seed": EXPECTED_SEED,
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_capacity": EXPECTED_TICKS,
        "bounded_execute_authorized": True,
        "full_config_preflight_authorized": False,
        "full_r_execute_authorized": False,
        "monitor_enabled": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _consume_nonce(*, nonce: str, authorized_output_dir: str, output_dir: Path) -> Path:
    expected = _canonical_absolute_path(
        authorized_output_dir, label="authorized output directory"
    )
    if output_dir.resolve() != expected:
        raise ValueError("bounded release is bound to a different exact output directory")
    NONCE_LEDGER.mkdir(parents=True, exist_ok=True)
    marker = NONCE_LEDGER / f"v25_{RELEASE_GATE}_{nonce}.consumed.json"
    payload = {
        "gate": RELEASE_GATE,
        "nonce": nonce,
        "authorized_output_dir": str(expected),
    }
    try:
        with marker.open("xb") as handle:
            handle.write(canonical_json_bytes(payload))
    except FileExistsError as exc:
        raise ValueError("bounded release nonce was already consumed") from exc
    return marker


def verify_bounded_release(
    *,
    repo: Path,
    release_artifact: Path,
    release_root_sha256: str,
    requested_output_dir: Path,
    current_pointer_head: str,
    dp_repo: Path,
    probe_template: Path,
    consume: bool,
) -> dict[str, Any]:
    seal = verify_complete_seal(
        release_artifact, release_root_sha256, label="V25 A1.6.4 bounded release"
    )
    if (
        seal["manifest_paths"] != RELEASE_PAYLOADS
        or (release_artifact / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("bounded release inventory/run.exit drifted")
    decision = _load_object(release_artifact / "decision.json")
    heads = _parse_heads(release_artifact / "HEADS")
    if set(decision) != RELEASE_FIELDS:
        raise ValueError("bounded release field set drifted")
    exact = {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "status": RELEASE_STATUS,
        "gate": RELEASE_GATE,
        "fixed_dp_head": FIXED_DP_HEAD,
        "seed": EXPECTED_SEED,
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": EXPECTED_RUNS,
        "snapshot_capacity": EXPECTED_TICKS,
        "bounded_execute_authorized": True,
        "full_config_preflight_authorized": False,
        "full_r_execute_authorized": False,
        "monitor_enabled": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    for key, expected in exact.items():
        if not strict_json_equal(decision.get(key), expected):
            raise ValueError(f"bounded release exact value drifted: {key}")
    if (
        not _is_sha256(decision.get("run_nonce"))
        or not _is_sha256(decision.get("critical_implementation_manifest_sha256"))
        or decision["critical_implementation_manifest_sha256"]
        != canonical_sha256(decision.get("critical_implementation_manifest"))
        or not _is_sha256(decision.get("execution_assets_sha256"))
        or decision["execution_assets_sha256"]
        != canonical_sha256(decision.get("execution_assets"))
        or not _is_sha256(decision.get("root_artifacts_sha256"))
        or decision["root_artifacts_sha256"]
        != canonical_sha256(decision.get("root_artifacts"))
        or decision.get("pointer_head_at_release") != current_pointer_head
        or heads
        != {
            "camp_source_head": decision.get("implementation_source_head"),
            "camp_pointer_head": decision.get("pointer_head_at_release"),
            "fixed_dp_head": FIXED_DP_HEAD,
        }
    ):
        raise ValueError("bounded release hashes/pointer authority drifted")
    assets = verify_frozen_execution_assets(
        repo=repo, dp_repo=dp_repo, probe_template=probe_template
    )
    canonical_dp = dp_repo.resolve()
    canonical_template = probe_template.resolve()
    if (
        Path(str(decision.get("dp_repo"))).resolve() != canonical_dp
        or decision.get("dp_repo") != str(canonical_dp)
        or _git(canonical_dp, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(canonical_dp, "status", "--porcelain")
        or Path(str(decision.get("probe_template"))).resolve() != canonical_template
        or decision.get("probe_template") != str(canonical_template)
        or decision.get("probe_template_sha256") != EXPECTED_PROBE_TEMPLATE_SHA256
        or not strict_json_equal(decision.get("execution_assets"), assets)
    ):
        raise ValueError("bounded release DP/template binding drifted")
    verify_dual_head_contract(
        repo=repo,
        implementation_source_head=decision["implementation_source_head"],
        current_pointer_head=current_pointer_head,
        implementation_manifest=decision["critical_implementation_manifest"],
    )
    chain = verify_four_root_chain(
        bindings=decision["root_artifacts"],
        implementation_source_head=decision["implementation_source_head"],
        fixed_dp_head=decision["fixed_dp_head"],
    )
    output = _canonical_absolute_path(
        decision["authorized_output_dir"], label="authorized output directory"
    )
    if output != requested_output_dir.resolve():
        raise ValueError("bounded release output directory mismatch")
    marker = None
    if consume:
        marker = _consume_nonce(
            nonce=decision["run_nonce"],
            authorized_output_dir=decision["authorized_output_dir"],
            output_dir=requested_output_dir,
        )
    return {
        "release_artifact": str(release_artifact.resolve()),
        "release_root_sha256": seal["root_sha256"],
        "decision": decision,
        "plan": chain["plan"],
        "nonce_marker": None
        if marker is None
        else {
            "path": str(marker),
            "sha256": hashlib.sha256(marker.read_bytes()).hexdigest(),
        },
    }


def reset_nonce_ledger_for_tests(path: Path) -> None:
    """Test-only hook; production code never removes consumed nonce markers."""

    if os.environ.get("PYTEST_CURRENT_TEST") is None:
        raise RuntimeError("nonce reset is test-only")
    path.unlink(missing_ok=True)
