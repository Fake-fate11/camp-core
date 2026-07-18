#!/usr/bin/env python3
"""Execute only a sealed A1.6.4 bounded plan after an Ultra one-shot release."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Iterator, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
)
from camp_core.integrations.diffusion_planner_v25_a162_bounded_execution import (  # noqa: E402
    RUN_EVIDENCE_SCHEMA_VERSION,
    TICKS_PER_RUN,
    canonical_sha256,
    validate_bounded_terminal_acceptance,
)
from camp_core.integrations.diffusion_planner_v25_a163_bounded_authority import (  # noqa: E402
    EXPECTED_RUNS,
    EXPECTED_TICKS,
    EXPECTED_UNIQUE_IDENTITIES,
    FIXED_DP_HEAD,
    verify_bounded_release,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (  # noqa: E402
    V25ControlledSceneAdapter,
)
from scripts.integrations import (  # noqa: E402
    run_diffusion_planner_v25_controlled_training_corpus as corpus,
)


SCHEMA_VERSION = "camp_dp_v25_a164_bounded_execution_v2"
SNAPSHOT_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_snapshot_v1"
INDEX_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_snapshot_index_row_v1"
RESULT_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_result_v1"
FAILURE_SCHEMA_VERSION = "camp_dp_v25_a163_bounded_failure_v1"
TRAIN_LOCK = Path("/root/autodl-tmp/.camp_dp_v25_controlled_train_corpus.lock")
MINIMUM_FREE_BYTES = 10 * 1024**3


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    )


def _write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    _write_json(temporary, value)
    temporary.replace(path)


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _native_number(value: Any, *, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite native number")
    return float(value)


def _repeat_context_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    feature = payload.get("feature_payload")
    sidecar = payload.get("sidecar")
    if type(feature) is not dict or type(sidecar) is not dict:
        raise ValueError("bounded snapshot feature/sidecar is malformed")
    return {
        "raw_context": feature.get("raw_context"),
        "context_source_complete": feature.get("context_source_complete"),
        "context_source_receipt": sidecar.get("context_source_receipt"),
        "signal_source_class": sidecar.get("signal_source_class"),
        "phase_authority_mode": sidecar.get("phase_authority_mode"),
        "controlled_signal_source_receipt": sidecar.get(
            "controlled_signal_source_receipt"
        ),
        "controlled_signal_tensor_evidence": sidecar.get(
            "controlled_signal_tensor_evidence"
        ),
        "controlled_model_input_cache_receipt": sidecar.get(
            "controlled_model_input_cache_receipt"
        ),
        "causal_signal_atom_input": sidecar.get("causal_signal_atom_input"),
    }


def build_run_evidence(
    *,
    run: Mapping[str, Any],
    payloads: list[Mapping[str, Any]],
    native_receipt: Mapping[str, Any],
    failure_class: str,
) -> dict[str, Any]:
    """Build evidence values, never caller-supplied repeat-pass booleans."""

    ticks = native_receipt.get("ticks")
    if type(ticks) is not list or len(ticks) != TICKS_PER_RUN:
        raise ValueError("bounded native receipt must contain exactly 64 ticks")
    if len(payloads) != TICKS_PER_RUN:
        raise ValueError("bounded run must contain exactly 64 paired snapshots")
    candidate0: list[str] = []
    rows: list[list[str]] = []
    atoms: list[str] = []
    contexts: list[str] = []
    selected: list[int] = []
    trajectory: list[dict[str, Any]] = []
    speeds: list[float] = []
    for index, (payload, tick) in enumerate(zip(payloads, ticks)):
        feature = payload.get("feature_payload")
        sidecar = payload.get("sidecar")
        safety = tick.get("safety") if type(tick) is dict else None
        if type(feature) is not dict or type(sidecar) is not dict or type(safety) is not dict:
            raise ValueError("bounded repeat evidence lacks raw snapshot/native safety")
        candidate0_sha = sidecar.get("candidate0_sha256")
        row_sha = feature.get("candidate_row_sha256")
        selected_index = sidecar.get("selected_index")
        position = safety.get("position_xy")
        if (
            type(candidate0_sha) is not str
            or len(candidate0_sha) != 64
            or type(row_sha) is not list
            or len(row_sha) != 8
            or any(type(value) is not str or len(value) != 64 for value in row_sha)
            or type(selected_index) is not int
            or selected_index < 0
            or selected_index >= 8
            or type(position) is not list
            or len(position) != 2
        ):
            raise ValueError("bounded repeat candidate/trajectory evidence drifted")
        candidate0.append(candidate0_sha)
        rows.append(list(row_sha))
        atoms.append(canonical_sha256(feature.get("atom_matrix")))
        contexts.append(canonical_sha256(_repeat_context_payload(payload)))
        selected.append(selected_index)
        trajectory.append(
            {
                "tick_index": index,
                "position_xy": [
                    _native_number(position[0], label="position x"),
                    _native_number(position[1], label="position y"),
                ],
                "ego_heading_rad": _native_number(
                    safety.get("ego_heading_rad"), label="ego heading"
                ),
                "route_progress_m": _native_number(
                    safety.get("route_progress_m"), label="route progress"
                ),
            }
        )
        speeds.append(_native_number(safety.get("speed_mps"), label="speed probe"))
    return {
        "schema_version": RUN_EVIDENCE_SCHEMA_VERSION,
        "run_ordinal": run["run_ordinal"],
        "scenario_id": run["scenario_id"],
        "occurrence": run["occurrence"],
        "tick_count": TICKS_PER_RUN,
        "candidate0_sha256_sequence": candidate0,
        "k8_row_sha256_sequence": rows,
        "atom_matrix_sha256_sequence": atoms,
        "context_sha256_sequence": contexts,
        "selected_index_sequence": selected,
        "failure_class": failure_class,
        "closed_loop_trajectory_sha256": canonical_sha256(trajectory),
        "speed_probe_sha256": canonical_sha256(speeds),
    }


def _write_snapshot(
    *,
    output_dir: Path,
    index_file: Any,
    run: Mapping[str, Any],
    tick_index: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    sidecar = payload.get("sidecar")
    if type(sidecar) is not dict:
        raise ValueError("bounded snapshot sidecar is missing")
    payload["schema_version"] = SNAPSHOT_SCHEMA_VERSION
    sidecar["run_ordinal"] = run["run_ordinal"]
    sidecar["occurrence"] = run["occurrence"]
    data = (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    relative = Path("snapshots") / f"{digest}.json"
    target = output_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != data:
        raise ValueError("bounded content-addressed snapshot collision")
    if not target.exists():
        target.write_bytes(data)
    row = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "run_ordinal": run["run_ordinal"],
        "occurrence": run["occurrence"],
        "scenario_id": run["scenario_id"],
        "tick_index": tick_index,
        "relative_path": relative.as_posix(),
        "sha256": digest,
    }
    index_file.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    return row


def _execute(
    *,
    args: argparse.Namespace,
    plan: Mapping[str, Any],
    cases: Mapping[str, Mapping[str, Any]],
    template: Mapping[str, Any],
    route_assets: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    runs = plan["runs"]
    first_case = cases[str(runs[0]["scenario_id"])]
    first_config = corpus.build_controlled_train_config(
        template,
        first_case,
        route_assets[str(first_case["route_identity_sha256"])],
    )
    # This is the first model/simulator/candidate-capable operation.  The
    # caller reaches here only after verify_bounded_release consumed authority.
    runner = corpus.build_native_arm_runner(first_config, device=args.device)
    results: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    snapshot_count = 0
    started = time.perf_counter()
    with (args.output_dir / "results.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as result_file, (args.output_dir / "snapshot_index.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as index_file, (args.output_dir / "run_evidence.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as evidence_file:
        for run in runs:
            if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
                raise RuntimeError("free disk fell below the 10 GiB floor")
            case = cases[str(run["scenario_id"])]
            identity = str(case["route_identity_sha256"])
            config = corpus.build_controlled_train_config(
                template, case, route_assets[identity]
            )
            adapter = V25ControlledSceneAdapter(
                case,
                mapped_signal_authority=case.get("mapped_signal_authority"),
                no_signal_authority=case.get("no_signal_authority"),
            )
            snapshots: list[Mapping[str, Any]] = []
            contexts: list[Mapping[str, Any]] = []
            native_dir = (
                args.output_dir
                / "native_runs"
                / (
                    f"run_{int(run['run_ordinal']):03d}_"
                    f"{run['occurrence']}_{run['scenario_id']}"
                )
            )
            receipt = runner(
                route=config["routes"][0],
                arm="camp",
                config=config,
                output_dir=native_dir,
                max_steps=TICKS_PER_RUN,
                decision_sink=snapshots.append,
                scene_adapter=adapter,
                v25_context_sink=contexts.append,
            )
            if (
                type(receipt) is not dict
                or len(receipt.get("ticks", [])) != TICKS_PER_RUN
                or len(snapshots) != TICKS_PER_RUN
                or len(contexts) != TICKS_PER_RUN
                or len(adapter.receipts) != TICKS_PER_RUN
            ):
                raise RuntimeError("bounded run was partial or lacked exact tick evidence")
            corpus.validate_native_arm_receipt(
                receipt,
                "camp",
                expected_ticks=TICKS_PER_RUN,
                require_summary=False,
                expected_selection_policy="v22_source_valid",
                expected_safety_schema="safety_cost_native_v22",
            )
            payloads: list[dict[str, Any]] = []
            for tick_index in range(TICKS_PER_RUN):
                payload = corpus.combine_snapshot_context(
                    snapshot=snapshots[tick_index],
                    context=contexts[tick_index],
                    case=case,
                    tick_index=tick_index,
                    controlled_scene_receipt=adapter.receipts[tick_index],
                )
                # The full-corpus projection validates the canonical scores
                # before returning but intentionally omits them.  Bounded
                # independent review needs the actual finite affine values,
                # so preserve that already-validated sequence explicitly.
                payload["sidecar"]["scores"] = list(
                    snapshots[tick_index]["sidecar"]["scores"]
                )
                _write_snapshot(
                    output_dir=args.output_dir,
                    index_file=index_file,
                    run=run,
                    tick_index=tick_index,
                    payload=payload,
                )
                payloads.append(payload)
            _write_json(native_dir / "bounded_native_receipt.json", receipt)
            evidence = build_run_evidence(
                run=run,
                payloads=payloads,
                native_receipt=receipt,
                failure_class="none",
            )
            result = {
                "schema_version": RESULT_SCHEMA_VERSION,
                "run_ordinal": run["run_ordinal"],
                "scenario_id": run["scenario_id"],
                "occurrence": run["occurrence"],
                "status": "complete",
                "tick_count": TICKS_PER_RUN,
                "retained_capability_failure": None,
                "failure_class": "none",
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            }
            results.append(result)
            evidence_rows.append(evidence)
            result_file.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
            evidence_file.write(
                json.dumps(evidence, sort_keys=True, allow_nan=False) + "\n"
            )
            result_file.flush()
            evidence_file.flush()
            index_file.flush()
            snapshot_count += TICKS_PER_RUN
            _write_json_atomic(
                args.output_dir / "progress.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "running",
                    "completed_runs": len(results),
                    "total_runs": EXPECTED_RUNS,
                    "snapshot_count": snapshot_count,
                    "fresh_b2_opened": False,
                    "outcome_fields_consumed": [],
                },
            )
    terminal = validate_bounded_terminal_acceptance(
        plan, results, run_evidence=evidence_rows
    )
    _write_json_atomic(
        args.output_dir / "progress.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "complete",
            "completed_runs": len(results),
            "total_runs": EXPECTED_RUNS,
            "snapshot_count": snapshot_count,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        },
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_exact_bounded_execution",
        "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
        "run_count": len(results),
        "snapshot_count": snapshot_count,
        "snapshot_capacity": EXPECTED_TICKS,
        "terminal": terminal,
        "wall_seconds": time.perf_counter() - started,
        "retained_capability_failure_count": 0,
        "mapped_runtime_source_failure_count": 0,
        "candidate0_semantics": "operational_default_alias_from_same_forward",
        "sequential_fixed_k8": True,
        "candidate_tensors_modified": False,
        "full_r_execute_authorized": False,
        "training_executed": False,
        "calibration_executed": False,
        "scene_runtime_enabled": False,
        "v2i_enabled": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _run(args: argparse.Namespace) -> dict[str, Any]:
    camp_head = _git(ROOT, "rev-parse", "HEAD")
    if _git(ROOT, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("CAMP tracked worktree is dirty")
    if (
        _git(args.dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(args.dp_repo, "status", "--porcelain")
    ):
        raise ValueError("fixed DP drifted or is not fully clean")
    if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")

    # Fail closed and consume the one-shot release before loading the formal
    # universe, materializing routes, building the model, simulator or K8.
    authority = verify_bounded_release(
        repo=ROOT,
        release_artifact=args.release_artifact,
        release_root_sha256=args.release_root_sha256,
        requested_output_dir=args.output_dir,
        current_pointer_head=camp_head,
        dp_repo=args.dp_repo,
        probe_template=args.probe_template,
        consume=True,
    )
    plan = authority["plan"]
    formal, formal_root = corpus._load_formal_plan()
    template = corpus._load_json(args.probe_template)
    formal_cases = {
        str(case["scenario_id"]): case
        for case in formal["train"]
        if case.get("runner_eligible") is True
    }
    selected_ids = {str(run["scenario_id"]) for run in plan["runs"]}
    if len(selected_ids) != EXPECTED_UNIQUE_IDENTITIES or not selected_ids <= set(
        formal_cases
    ):
        raise ValueError("bounded plan/formal selected identity universe drifted")
    source_binding = authority["decision"]["root_artifacts"]["source"]
    selected = [formal_cases[scenario_id] for scenario_id in sorted(selected_ids)]
    attached = corpus._attach_semantic_clone_authority(
        selected,
        dp_repo=args.dp_repo,
        r0_source_artifact=Path(source_binding["path"]),
        expected_camp_source_head=authority["decision"]["implementation_source_head"],
        r0_source_root_sha256=source_binding["root_sha256"],
    )
    cases = {str(case["scenario_id"]): case for case in attached}
    args.output_dir.mkdir(parents=True)
    route_assets = corpus._materialize_routes(
        attached, args.output_dir / "routes", args.dp_repo
    )
    (args.output_dir / "HEADS").write_text(
        f"camp_source_head={authority['decision']['implementation_source_head']}\n"
        f"camp_pointer_head={camp_head}\n"
        f"fixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )
    _write_json(
        args.output_dir / "source_receipt.json",
        {
            "schema_version": SCHEMA_VERSION,
            "release_artifact": authority["release_artifact"],
            "release_root_sha256": authority["release_root_sha256"],
            "release_run_nonce": authority["decision"]["run_nonce"],
            "nonce_marker": authority["nonce_marker"],
            "root_artifacts": authority["decision"]["root_artifacts"],
            "formal_root_sha256": formal_root,
            "critical_implementation_manifest": authority["decision"][
                "critical_implementation_manifest"
            ],
            "unique_identity_count": EXPECTED_UNIQUE_IDENTITIES,
            "run_count": EXPECTED_RUNS,
            "snapshot_capacity": EXPECTED_TICKS,
            "full_r_execute_authorized": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        },
    )
    return _execute(
        args=args,
        plan=plan,
        cases=cases,
        template=template,
        route_assets=route_assets,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--release-artifact", type=Path, required=True)
    parser.add_argument("--release-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--bounded-execute", action="store_true", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    with _exclusive_lock(TRAIN_LOCK):
        if args.output_dir.exists():
            raise FileExistsError(args.output_dir)
        try:
            report = _run(args)
            _write_json(args.output_dir / "report.json", report)
            (args.output_dir / "run.exit").write_bytes(b"0\n")
            root = seal_artifact(args.output_dir, label="V25 A1.6.4 bounded execution")
            print(json.dumps({**report, "artifact_root_sha256": root}, sort_keys=True))
        except BaseException as exc:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            _write_json(
                args.output_dir / "failure.json",
                {
                    "schema_version": FAILURE_SCHEMA_VERSION,
                    "status": "failed_closed_bounded_execution",
                    "failure_type": type(exc).__name__,
                    "failure_reason": str(exc),
                    "full_r_execute_authorized": False,
                    "fresh_b2_opened": False,
                    "outcome_fields_consumed": [],
                },
            )
            (args.output_dir / "run.exit").write_bytes(b"1\n")
            seal_artifact(args.output_dir, label="failed V25 A1.6.4 bounded execution")
            raise


if __name__ == "__main__":
    main()
