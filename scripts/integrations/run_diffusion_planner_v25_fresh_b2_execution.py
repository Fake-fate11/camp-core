#!/usr/bin/env python3
"""Execute and seal the externally released V25 Fresh B2 denominator once."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable, Iterator, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_fresh_execution import (  # noqa: E402
    execute_fresh_b2_three_arm_units,
    materialize_fixed_dp_failure_evidence,
)
from camp_core.integrations.diffusion_planner_v25_fresh_opening import (  # noqa: E402
    freeze_fresh_b2_opening_consumption,
    validate_fresh_b2_controller_decision,
    validate_fresh_b2_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_fresh_storage import (  # noqa: E402
    compress_logical_json_file,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    V25RuntimeSelectorAssets,
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    validate_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_execution_artifact_v2"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
MINIMUM_FREE_BYTES = 10 * 1024**3
TRAIN_LOCK = Path("/root/autodl-tmp/.camp_dp_v25_controlled_train_corpus.lock")
NONCE_ROOT = Path("/root/autodl-tmp/.camp_dp_v25_fresh_b2_open_nonces")
INPUT_ROLES = (
    "plan",
    "map",
    "route",
    "route_review",
    "runtime",
    "runtime_review",
    "scenario_manifest",
    "training",
    "training_review",
    "preopen",
    "preopen_review",
)
RunOne = Callable[[Mapping[str, Any], Path], Mapping[str, Any]]


def run(
    *,
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    probe_template: Path,
    probe_template_sha256: str,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
    device: str,
    preflight_only: bool = False,
    run_one: RunOne | None = None,
    marker_root: Path = NONCE_ROOT,
) -> str:
    """Consume one external opening nonce, run 500 pairs, and seal evidence."""

    if device != "cuda":
        raise ValueError("Fresh B2 production execution requires cuda")
    if set(artifacts) != set(INPUT_ROLES) or set(roots) != set(INPUT_ROLES):
        raise ValueError("Fresh B2 input role set drifted")
    canonical_artifacts = {name: Path(artifacts[name]).resolve() for name in INPUT_ROLES}
    dp_root = Path(dp_repo).resolve()
    output = Path(output_dir)
    if str(output) != str(output.resolve()):
        raise ValueError("Fresh B2 output path must already be canonical")
    output = output.resolve()

    _preconditions(dp_root, output)
    verified_roots = _verify_inputs(canonical_artifacts, roots)
    probe = _legacy_json_object(probe_template.resolve(), probe_template_sha256)
    release_root = Path(opening_release_artifact).resolve()
    verify_complete_seal(
        release_root,
        opening_release_root_sha256,
        label="Fresh B2 one-time opening release",
    )
    if (release_root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B2 opening release did not exit successfully")
    release = validate_fresh_b2_opening_release(
        _canonical_json(release_root / "decision.json")
    )
    controller_root, controller = _verify_controller_decision(
        artifact=Path(controller_decision_artifact).resolve(),
        expected_root_sha256=controller_decision_root_sha256,
        release=release,
        artifacts=canonical_artifacts,
        roots=verified_roots,
        probe_template=Path(probe_template).resolve(),
        probe_template_sha256=probe_template_sha256,
        dp_repo=dp_root,
    )
    if str(output) != release["authorized_output_dir"]:
        raise ValueError("Fresh B2 output differs from the external release")
    if _git_head(ROOT) != release["pointer_head_at_release"]:
        raise ValueError("Fresh B2 release/current CAMP HEAD drifted")

    plan = validate_signal_complete_execution_plan(
        _canonical_json(canonical_artifacts["plan"] / "execution_plan.json")
    )
    if plan.get("split") != "fresh_b2":
        raise ValueError("Fresh B2 execution received a non-Fresh plan")
    route_by_identity = _route_assets(canonical_artifacts["route"])
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity,
            map_artifact=canonical_artifacts["map"],
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    }
    preopen = _canonical_json(
        canonical_artifacts["preopen"] / "preopen_authority.json"
    )
    qualifications = preopen.get("qualification_rows")
    if type(qualifications) is not list:
        raise ValueError("Fresh B2 preopen qualification rows are missing")
    assets = load_v25_runtime_selector_assets(
        training_artifact=canonical_artifacts["training"],
        training_root_sha256=verified_roots["training"],
        training_review_artifact=canonical_artifacts["training_review"],
        training_review_root_sha256=verified_roots["training_review"],
    )
    selector_authority = _runtime_selector_authority(
        assets=assets,
        artifacts=canonical_artifacts,
        roots=verified_roots,
        release=release,
    )
    if preflight_only:
        return _canonical_sha(
            {
                "schema_version": "camp_dp_v25_fresh_b2_production_entry_preflight_v1",
                "status": "passed_before_nonce_consumption",
                "controller_decision_root_sha256": controller_root,
                "opening_release_root_sha256": opening_release_root_sha256,
                "pointer_head": release["pointer_head_at_release"],
                "fixed_dp_head": FIXED_DP_HEAD,
                "input_roots": verified_roots,
                "model_registry_sha256": controller["model_registry_sha256"],
                "training_scale_sha256": controller["training_scale_sha256"],
                "context_scaler_sha256": controller["context_scaler_sha256"],
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            }
        )

    marker_path = _marker_path(release["run_nonce"], marker_root=marker_root)
    with _exclusive_lock(TRAIN_LOCK):
        marker_sha256 = _consume_opening_nonce(
            release=release,
            release_root_sha256=opening_release_root_sha256,
            marker_path=marker_path,
        )
        consumption = freeze_fresh_b2_opening_consumption(
            opening_release=release,
            release_root_sha256=opening_release_root_sha256,
            marker_sha256=marker_sha256,
        )
        production_run = run_one or _native_run_one(
            device=device,
            assets=assets,
            opening_authority={
                "opening_release": release,
                "opening_release_root_sha256": opening_release_root_sha256,
                "opening_consumption": consumption,
            },
        )
        try:
            report = execute_fresh_b2_three_arm_units(
                plan=plan,
                qualification_rows=qualifications,
                probe_template=probe,
                prepared_runtime_by_scenario=prepared,
                route_asset_by_identity=route_by_identity,
                dp_repo=dp_root,
                runtime_selector_authority=selector_authority,
                opening_release=release,
                opening_release_root_sha256=opening_release_root_sha256,
                opening_consumption=consumption,
                authorized_output_dir=release["authorized_output_dir"],
                output_dir=output,
                run_one=production_run,
                failure_evidence=materialize_fixed_dp_failure_evidence,
            )
            artifact_report = {
                "schema_version": SCHEMA_VERSION,
                "status": "sealed_fresh_b2_execution",
                "camp_head": _git_head(ROOT),
                "fixed_dp_head": FIXED_DP_HEAD,
                "device": "cuda",
                "input_artifacts": {
                    role: str(canonical_artifacts[role]) for role in INPUT_ROLES
                },
                "input_roots": verified_roots,
                "probe_template": str(probe_template.resolve()),
                "probe_template_sha256": probe_template_sha256,
                "controller_decision_artifact": str(controller_decision_artifact.resolve()),
                "controller_decision_root_sha256": controller_root,
                "opening_release_artifact": str(release_root),
                "opening_release_root_sha256": opening_release_root_sha256,
                "opening_consumption": consumption,
                "execution_report_sha256": _canonical_sha(report),
                "fresh_b2_opened_once": True,
                "training_executed": False,
                "calibration_executed": False,
                "claim_authorized_by_artifact": False,
            }
            _write_json(output / "artifact_report.json", artifact_report)
            _write_control_files(output, exit_code=0)
            return seal_artifact(output, label="V25 Fresh B2 three-arm execution")
        except BaseException as exc:
            output.mkdir(parents=True, exist_ok=True)
            _write_json(
                output / "failure.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "failed_closed_fresh_b2_execution",
                    "reason": str(exc),
                    "opening_release_root_sha256": opening_release_root_sha256,
                    "opening_run_nonce": release["run_nonce"],
                    "fresh_b2_opened_once": True,
                    "protocol_changed_after_opening": False,
                    "training_executed": False,
                    "calibration_executed": False,
                },
            )
            _write_control_files(output, exit_code=1)
            seal_artifact(output, label="failed V25 Fresh B2 execution")
            raise


def _verify_controller_decision(
    *,
    artifact: Path,
    expected_root_sha256: str,
    release: Mapping[str, Any],
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    probe_template: Path,
    probe_template_sha256: str,
    dp_repo: Path,
) -> tuple[str, dict[str, Any]]:
    seal = verify_complete_seal(
        artifact,
        expected_root_sha256,
        label="Fresh B2 controller decision",
    )
    if (artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B2 controller decision did not exit successfully")
    decision = validate_fresh_b2_controller_decision(
        _canonical_json(artifact / "decision.json")
    )
    expected_inputs = {
        role: {"path": str(artifacts[role]), "root_sha256": roots[role]}
        for role in INPUT_ROLES
    }
    preopen = _canonical_json(artifacts["preopen"] / "preopen_authority.json")
    expected_manifest = tracked_implementation_manifest(ROOT)
    exact = {
        "implementation_source_head": release["implementation_source_head"],
        "pointer_head_at_release": release["pointer_head_at_release"],
        "critical_implementation_manifest_sha256": expected_manifest[
            "manifest_sha256"
        ],
        "input_artifacts": expected_inputs,
        "probe_template": {
            "path": str(probe_template),
            "sha256": probe_template_sha256,
        },
        "dp_repo": {"path": str(dp_repo), "head": FIXED_DP_HEAD},
        "calibration_contract_root_sha256": release[
            "calibration_contract_root_sha256"
        ],
        "preopen_qualification_root_sha256": release[
            "preopen_qualification_root_sha256"
        ],
        "model_registry_sha256": release["model_registry_sha256"],
        "training_scale_sha256": release["training_scale_sha256"],
        "context_scaler_sha256": release["context_scaler_sha256"],
        "scenario_manifest_root_sha256": release[
            "scenario_manifest_root_sha256"
        ],
        "run_nonce": release["run_nonce"],
        "authorized_output_dir": release["authorized_output_dir"],
    }
    if (
        seal["root_sha256"] != release["controller_decision_root_sha256"]
        or any(
            not _strict_json_equal(decision.get(name), value)
            for name, value in exact.items()
        )
        or preopen.get("critical_implementation_manifest") != expected_manifest
    ):
        raise ValueError("Fresh B2 controller/release/input authority drifted")
    return seal["root_sha256"], decision


def _native_run_one(
    *,
    device: str,
    assets: V25RuntimeSelectorAssets,
    opening_authority: Mapping[str, Any],
) -> RunOne:
    holder: dict[str, Any] = {}

    def execute(config: Mapping[str, Any], run_dir: Path) -> Mapping[str, Any]:
        if "run_arm" not in holder:
            from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
                build_native_arm_runner,
            )

            holder["run_arm"] = build_native_arm_runner(
                config,
                device=device,
                fresh_b2_opening_authority=opening_authority,
            )
        plan_arm = config["protocol"]["fresh_b2_plan_arm"]
        arm = "dp" if plan_arm == "candidate0_operational_default" else "camp"
        scene_provider = (
            assets.scene14d_weight_provider
            if plan_arm == "camp_scene14d_no_v2i"
            else None
        )
        snapshots: list[dict[str, Any]] = []
        receipt = dict(holder["run_arm"](
            route=config["routes"][0],
            arm=arm,
            config=config,
            output_dir=run_dir / "native",
            max_steps=64,
            fixed_k8_candidate0=plan_arm == "candidate0_operational_default",
            v25_weight_provider=scene_provider,
            decision_sink=(
                snapshots.append
                if plan_arm != "candidate0_operational_default"
                else None
            ),
        ))
        expected_count = 0 if plan_arm == "candidate0_operational_default" else 64
        if len(snapshots) != expected_count or (
            snapshots
            and [row["sidecar"]["tick_index"] for row in snapshots]
            != list(range(64))
        ):
            raise ValueError("Fresh logical decision-evidence count drifted")
        logical = run_dir / "decision_evidence.json"
        _write_json(logical, snapshots)
        receipt["fresh_decision_evidence_reference"] = compress_logical_json_file(
            logical
        )
        receipt["fresh_decision_evidence_count"] = len(snapshots)
        return receipt

    return execute


def _runtime_selector_authority(
    *,
    assets: V25RuntimeSelectorAssets,
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    release: Mapping[str, Any],
) -> dict[str, Any]:
    authority = {
        "training_artifact": {
            "path": str(artifacts["training"]),
            "root_sha256": roots["training"],
        },
        "training_review_artifact": {
            "path": str(artifacts["training_review"]),
            "root_sha256": roots["training_review"],
        },
        "calibration_contract_root_sha256": release[
            "calibration_contract_root_sha256"
        ],
        "preopen_qualification_root_sha256": roots["preopen"],
        "scenario_manifest_root_sha256": roots["scenario_manifest"],
        "model_registry_sha256": _file_sha256(
            artifacts["training"] / "model_registry.json"
        ),
        "training_scale_sha256": assets.atom_scales_sha256,
        "context_scaler_sha256": (
            assets.scene14d_weight_provider.context_scaler_sha256
        ),
        "atom_scales": {
            "path": str(artifacts["training"] / "runtime_atom_scales.json"),
            "sha256": assets.atom_scales_sha256,
        },
        "static14d_weights": {
            "path": str(artifacts["training"] / "static14d_runtime_weights.npy"),
            "sha256": assets.static14d_weights_sha256,
        },
    }
    expected = {
        "preopen_qualification_root_sha256": roots["preopen"],
        "scenario_manifest_root_sha256": roots["scenario_manifest"],
        "model_registry_sha256": authority["model_registry_sha256"],
        "training_scale_sha256": authority["training_scale_sha256"],
        "context_scaler_sha256": authority["context_scaler_sha256"],
    }
    if any(release[name] != value for name, value in expected.items()):
        raise ValueError("Fresh B2 release differs from sealed runtime selector assets")
    return authority


def _verify_inputs(
    artifacts: Mapping[str, Path], roots: Mapping[str, str]
) -> dict[str, str]:
    verified: dict[str, str] = {}
    for role in INPUT_ROLES:
        seal = verify_complete_seal(
            artifacts[role], str(roots[role]), label=f"Fresh B2 {role}"
        )
        if (artifacts[role] / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"Fresh B2 {role} run.exit drifted")
        verified[role] = seal["root_sha256"]
    for role, reviewed_role in (
        ("route", "route_review"),
        ("runtime", "runtime_review"),
        ("preopen", "preopen_review"),
    ):
        report = _canonical_json(artifacts[reviewed_role] / "report.json")
        if report.get("reviewed_root_sha256") != verified[role]:
            raise ValueError(f"Fresh B2 {reviewed_role} root binding drifted")
    preopen_report = _canonical_json(artifacts["preopen"] / "report.json")
    preopen_review = _canonical_json(artifacts["preopen_review"] / "report.json")
    preopen_authority = _canonical_json(
        artifacts["preopen"] / "preopen_authority.json"
    )
    frozen = preopen_authority.get("upstream_bindings")
    if (
        preopen_report.get("status")
        != "passed_outcome_blind_fresh_b2_preopen_materialization"
        or preopen_report.get("fresh_b2_opened") is not False
        or preopen_report.get("outcome_fields_consumed") != []
        or preopen_review.get("status")
        != "passed_independent_outcome_blind_fresh_b2_preopen_review"
        or preopen_review.get("reviewed_root_sha256") != verified["preopen"]
        or type(frozen) is not dict
        or any(
            frozen.get(name, {}).get("root_sha256") != value
            for name, value in {
                "training": verified["training"],
                "training_review": verified["training_review"],
            }.items()
        )
    ):
        raise ValueError("Fresh B2 preopen frozen-root binding drifted")
    return verified


def _route_assets(route_artifact: Path) -> dict[str, dict[str, Any]]:
    payload = _canonical_json(route_artifact / "route_assets.json")
    rows = payload.get("route_assets")
    if type(rows) is not list:
        raise ValueError("Fresh B2 route asset inventory is malformed")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if type(row) is not dict or set(row) != {
            "route_identity_sha256",
            "scenario_identity_sha256",
            "map_sha256",
            "map_geometry_sha256",
            "corridor_sha256",
            "source_chain_sha256",
            "route_asset",
            "route_lanelet_ids",
            "start_pose_float32",
            "goal_pose_float32",
            "waypoint_count",
            "fixed_dp_route_source",
            "fresh_b2_opened",
            "outcome_fields_consumed",
        }:
            raise ValueError("Fresh B2 route asset row drifted")
        identity = row["route_identity_sha256"]
        asset = row["route_asset"]
        if (
            type(identity) is not str
            or identity in result
            or type(asset) is not dict
            or set(asset) != {"name", "path", "sha256"}
            or asset.get("name") != identity
            or row.get("fresh_b2_opened") is not False
            or row.get("outcome_fields_consumed") != []
        ):
            raise ValueError("Fresh B2 route identity is invalid or duplicated")
        result[identity] = dict(asset)
    return result


def _consume_opening_nonce(
    *,
    release: Mapping[str, Any],
    release_root_sha256: str,
    marker_path: Path,
) -> str:
    marker = Path(marker_path)
    marker.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "camp_dp_v25_fresh_b2_opening_nonce_marker_v1",
        "gate": "fresh_b2_one_time_opening",
        "release_root_sha256": release_root_sha256,
        "run_nonce": release["run_nonce"],
        "authorized_output_dir": release["authorized_output_dir"],
        "consumed_before_outcome_capable_operation": True,
        "outcome_fields_consumed_before_nonce": [],
        "second_consumption_allowed": False,
    }
    raw = _canonical_bytes(payload)
    descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        marker.unlink(missing_ok=True)
        raise
    return hashlib.sha256(raw).hexdigest()


def _marker_path(nonce: str, *, marker_root: Path) -> Path:
    _require_sha(nonce, "Fresh B2 run nonce")
    return Path(marker_root) / f"v25_fresh_b2_{nonce}.consumed.json"


def _preconditions(dp_root: Path, output: Path) -> None:
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    if _git_head(dp_root) != FIXED_DP_HEAD or _tracked_dirty(dp_root):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(output.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("exclusive corpus lock is held") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("exclusive corpus lock is held") from exc
        yield
    finally:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _legacy_json_object(path: Path, expected_sha256: str) -> dict[str, Any]:
    if _file_sha256(path) != expected_sha256:
        raise ValueError("Fresh B2 probe template SHA256 drifted")
    value = _strict_json_value(path.read_bytes())
    if type(value) is not dict:
        raise ValueError("Fresh B2 probe template must be a JSON object")
    return value


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = _strict_json_value(raw)
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"Fresh B2 authority JSON is not canonical: {path}")
    return value


def _strict_json_value(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Fresh B2 JSON contains a duplicate key")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token: {token}")
        ),
    )


def _strict_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_json_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _write_control_files(root: Path, *, exit_code: int) -> None:
    (root / "HEADS").write_bytes(
        f"camp_head={_git_head(ROOT)}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
            "ascii"
        )
    )
    (root / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (root / "run.exit").write_bytes(f"{exit_code}\n".encode("ascii"))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha(value: Any, name: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{name} must be a lowercase SHA256")
    return value


def _git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _tracked_dirty(repo: Path) -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for role in INPUT_ROLES:
        option = role.replace("_", "-")
        parser.add_argument(f"--{option}-artifact", type=Path, required=True)
        parser.add_argument(f"--{option}-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--controller-decision-artifact", type=Path, required=True)
    parser.add_argument("--controller-decision-root-sha256", required=True)
    parser.add_argument("--opening-release-artifact", type=Path, required=True)
    parser.add_argument("--opening-release-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda",), required=True)
    parser.add_argument("--fresh-b2-one-time-open", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.fresh_b2_one_time_open == args.preflight_only:
        raise ValueError(
            "Fresh B2 production entry requires exactly one of one-time open or preflight"
        )
    artifacts = {
        role: getattr(args, f"{role}_artifact") for role in INPUT_ROLES
    }
    roots = {
        role: getattr(args, f"{role}_root_sha256") for role in INPUT_ROLES
    }
    digest = run(
        artifacts=artifacts,
        roots=roots,
        probe_template=args.probe_template,
        probe_template_sha256=args.probe_template_sha256,
        controller_decision_artifact=args.controller_decision_artifact,
        controller_decision_root_sha256=args.controller_decision_root_sha256,
        opening_release_artifact=args.opening_release_artifact,
        opening_release_root_sha256=args.opening_release_root_sha256,
        dp_repo=args.dp_repo,
        output_dir=args.output_dir,
        device=args.device,
        preflight_only=args.preflight_only,
    )
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
