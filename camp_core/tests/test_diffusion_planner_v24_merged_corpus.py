from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PILOT_HEAD = "a" * 40
REMAINING_HEAD = "b" * 40
ASSEMBLY_HEAD = "c" * 40
PILOT_SEED = 24001
REMAINING_SEEDS = [24002, 24003, 24004, 24005]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, allow_nan=False), encoding="utf-8"
    )


def _seal(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    )
    (root / "SHA256SUMS").write_text(
        "".join(
            f"{_file_sha256(path)}  {path.relative_to(root).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )
    digest = _file_sha256(root / "SHA256SUMS")
    (root / "ROOT_SHA256SUMS").write_text(f"{digest}  SHA256SUMS\n", encoding="ascii")
    return digest


def _closed_boundaries() -> dict[str, object]:
    return {
        "model_loaded": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "tuning_executed": False,
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }


def _phase_artifact(
    root: Path,
    *,
    phase: str,
    seeds: list[int],
    schema_prefix: str,
    camp_head: str,
) -> tuple[str, dict[str, object]]:
    root.mkdir()
    routes = [_sha("route:0"), _sha("route:1")]
    failure_reason = "RuntimeError: retained test failure"
    complete = failed = snapshot_count = 0
    for route_index, route in enumerate(routes):
        for seed_index, seed in enumerate(seeds):
            is_failure = route_index == 0 and seed_index == 0
            snapshots: list[str] = []
            if is_failure:
                failed += 1
            else:
                payload = {
                    "schema": "test_snapshot_v1",
                    "sidecar": {
                        "route_identity_sha256": route,
                        "seed": seed,
                        "source_stratum": {"tight_corridor": True},
                    },
                }
                encoded = json.dumps(payload, sort_keys=True).encode()
                digest = hashlib.sha256(encoded).hexdigest()
                path = root / "snapshots" / f"{digest}.json"
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(encoded)
                snapshots.append(digest)
                complete += 1
                snapshot_count += 1
            receipt = {
                "schema": f"camp_dp_v24_native_corpus_{schema_prefix}_run_receipt_v1",
                "status": "failed" if is_failure else "ok",
                "split": "train",
                "phase": phase,
                "record_key": f"record-{route_index}",
                "map_family_id": "map-family-test",
                "logical_map_sha256": _sha("logical-map"),
                "corridor_group_sha256": _sha(f"corridor:{route_index}"),
                "route_identity_sha256": route,
                "seed": seed,
                "snapshot_sha256": snapshots,
                "failure_stage": "native_replay" if is_failure else None,
                "failure_reason": failure_reason if is_failure else None,
                "retained_in_denominator": True,
                "wall_clock_s": 1.0,
            }
            _write_json(
                root / "receipts" / "train" / route / f"seed_{seed}.json", receipt
            )

    planned = len(routes) * len(seeds)
    summary = {
        "schema": f"camp_dp_v24_native_corpus_{schema_prefix}_summary_v1",
        "status": "complete_with_retained_failures",
        "phase": phase,
        "planned_route_seed_runs": planned,
        "complete_route_seed_runs": complete,
        "failed_route_seed_runs": failed,
        "retained_route_seed_runs": planned,
        "pending_route_seed_runs": 0,
        "route_coverage": 1.0,
        "snapshot_count": snapshot_count,
        "snapshot_count_by_source_stratum": {"tight_corridor": snapshot_count},
        "all_k_high_risk_snapshot_count": 0,
        "corpus_steps": 64,
        "sample_every_ticks": 1,
        "theoretical_max_snapshots": planned * 64,
        "wall_clock_s": float(planned),
        "free_disk_gib": 20.0,
        "all_routes_retained_in_denominator": True,
        "tuning_executed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "outcome_fields_consumed": [],
        "claim_authorized": False,
    }
    if seeds == [PILOT_SEED]:
        summary["seed"] = PILOT_SEED
        summary_name = "pilot_summary.json"
    else:
        summary["seeds"] = seeds
        summary_name = "remaining_summary.json"
    _write_json(root / summary_name, summary)
    _write_json(root / "execution.json", summary)
    (root / "HEADS").write_text(
        f"CAMP_HEAD={camp_head}\nFIXED_DP_HEAD={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (root / "run.exit").write_text("0\n", encoding="ascii")
    return _seal(root), {
        "routes": routes,
        "complete": complete,
        "failed": failed,
        "snapshots": snapshot_count,
        "failure_reason": failure_reason,
    }


def _review_artifact(
    root: Path,
    *,
    source_root_sha256: str,
    phase: str,
    recomputed: dict[str, object],
) -> str:
    root.mkdir()
    pilot = phase == "pilot"
    payload = {
        "schema": (
            "camp_dp_v24_native_corpus_pilot_independent_review_v1"
            if pilot
            else "camp_dp_v24_native_corpus_remaining_independent_review_v1"
        ),
        "status": "passed_with_warning" if pilot else "passed",
        "check_count": 1,
        "failed_count": 0,
        "failed_checks": [],
        "checks": [{"name": "fixture", "passed": True}],
        "review_only": True,
        **_closed_boundaries(),
        "source_pilot_root_sha256": source_root_sha256 if pilot else None,
        "source_remaining_root_sha256": None if pilot else source_root_sha256,
        "recomputed": {
            "planned_route_seed_runs": len(recomputed["routes"]) * (1 if pilot else 4),
            "complete_route_seed_runs": recomputed["complete"],
            "failed_route_seed_runs": recomputed["failed"],
            "retained_route_seed_runs": len(recomputed["routes"]) * (1 if pilot else 4),
            "pending_route_seed_runs": 0,
            "route_coverage": 1.0,
            "snapshot_count": recomputed["snapshots"],
            "snapshot_count_by_source_stratum": {
                "tight_corridor": recomputed["snapshots"]
            },
            "all_k_high_risk_snapshot_count": 0,
            "failure_reason_counts": {recomputed["failure_reason"]: 1},
            "receipt_count_by_source_map_sha256": {
                _sha("logical-map"): len(recomputed["routes"]) * (1 if pilot else 4)
            },
            "snapshot_count_by_source_map_sha256": {
                _sha("logical-map"): recomputed["snapshots"]
            },
        },
        "decision": (
            {
                "action": "execute_frozen_remaining_train_seeds",
                "authorized": True,
                "preserve_all_failures_and_denominator": True,
                "seeds": REMAINING_SEEDS,
                "route_count": len(recomputed["routes"]),
                "route_order": ["record-0", "record-1"],
                "route_removal_replacement_reordering_authorized": False,
                "tuning_authorized": False,
                "outcome_access_authorized": False,
                "calibration_access_authorized": False,
                "holdout_access_authorized": False,
                "claim_authorized": False,
            }
            if pilot
            else {
                "action": "assemble_frozen_pilot_and_remaining_train_corpus",
                "merged_train_corpus_assembly_authorized": True,
                "preserve_all_failures_and_denominator": True,
                "training_authorized": False,
                "tuning_authorized": False,
                "outcome_access_authorized": False,
                "calibration_access_authorized": False,
                "holdout_access_authorized": False,
                "claim_authorized": False,
            }
        ),
    }
    _write_json(root / "review.json", payload)
    (root / "HEADS").write_text(
        f"CAMP_HEAD={_sha(phase)[:40]}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_{phase.upper()}_ROOT_SHA256={source_root_sha256}\n",
        encoding="ascii",
    )
    (root / "run.exit").write_text("0\n", encoding="ascii")
    return _seal(root)


def _sources(tmp_path: Path) -> dict[str, object]:
    pilot_root = tmp_path / "pilot"
    pilot_sha, pilot_recomputed = _phase_artifact(
        pilot_root,
        phase="capability_pilot_all_train_routes_first_seed",
        seeds=[PILOT_SEED],
        schema_prefix="pilot",
        camp_head=PILOT_HEAD,
    )
    remaining_root = tmp_path / "remaining"
    remaining_sha, remaining_recomputed = _phase_artifact(
        remaining_root,
        phase="main_completion_remaining_frozen_seeds",
        seeds=REMAINING_SEEDS,
        schema_prefix="remaining",
        camp_head=REMAINING_HEAD,
    )
    pilot_review_root = tmp_path / "pilot-review"
    pilot_review_sha = _review_artifact(
        pilot_review_root,
        source_root_sha256=pilot_sha,
        phase="pilot",
        recomputed=pilot_recomputed,
    )
    remaining_review_root = tmp_path / "remaining-review"
    remaining_review_sha = _review_artifact(
        remaining_review_root,
        source_root_sha256=remaining_sha,
        phase="remaining",
        recomputed=remaining_recomputed,
    )
    return {
        "pilot_root": pilot_root,
        "expected_pilot_root_sha256": pilot_sha,
        "pilot_review_root": pilot_review_root,
        "expected_pilot_review_root_sha256": pilot_review_sha,
        "remaining_root": remaining_root,
        "expected_remaining_root_sha256": remaining_sha,
        "remaining_review_root": remaining_review_root,
        "expected_remaining_review_root_sha256": remaining_review_sha,
        "expected_pilot_camp_head": PILOT_HEAD,
        "expected_remaining_camp_head": REMAINING_HEAD,
        "expected_route_count": 2,
    }


def _complete_assembly_evidence(output: Path, sources: dict[str, object]) -> None:
    summary = json.loads((output / "merged_summary.json").read_text())
    (output / "HEADS").write_text(
        f"CAMP_HEAD={ASSEMBLY_HEAD}\n"
        f"FIXED_DP_HEAD={FIXED_DP_HEAD}\n"
        f"SOURCE_PILOT_ROOT_SHA256={sources['expected_pilot_root_sha256']}\n"
        f"SOURCE_PILOT_REVIEW_ROOT_SHA256={sources['expected_pilot_review_root_sha256']}\n"
        f"SOURCE_REMAINING_ROOT_SHA256={sources['expected_remaining_root_sha256']}\n"
        "SOURCE_REMAINING_REVIEW_ROOT_SHA256="
        f"{sources['expected_remaining_review_root_sha256']}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(
        "v24 native corpus deterministic merged train index assembly\n",
        encoding="utf-8",
    )
    (output / "assembly.md").write_text("# fixture\n", encoding="utf-8")
    (output / "stdout.txt").write_text(
        json.dumps(summary, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "stderr.txt").write_text("", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")


def _rechain_review_source(
    review_root: Path,
    *,
    source_field: str,
    old_source_sha256: str,
    new_source_sha256: str,
) -> str:
    review_path = review_root / "review.json"
    review = json.loads(review_path.read_text())
    review[source_field] = new_source_sha256
    _write_json(review_path, review)
    heads = review_root / "HEADS"
    heads.write_text(
        heads.read_text().replace(old_source_sha256, new_source_sha256),
        encoding="ascii",
    )
    return _seal(review_root)


def test_merged_assembly_preserves_denominator_without_copying_snapshots(
    tmp_path: Path,
) -> None:
    from scripts.integrations.assemble_diffusion_planner_v24_native_corpus import (
        assemble_merged_corpus,
    )

    output = tmp_path / "merged"
    summary = assemble_merged_corpus(output_dir=output, **_sources(tmp_path))

    assert summary["status"] == "passed"
    assert summary["route_count"] == 2
    assert summary["seeds"] == [24001, 24002, 24003, 24004, 24005]
    assert summary["planned_route_seed_runs"] == 10
    assert summary["retained_route_seed_runs"] == 10
    assert summary["complete_route_seed_runs"] == 8
    assert summary["failed_route_seed_runs"] == 2
    assert summary["snapshot_count"] == 8
    assert summary["snapshot_overlap_count"] == 0
    assert summary["snapshot_payloads_copied"] is False
    assert not (output / "snapshots").exists()
    assert len((output / "snapshot_index.jsonl").read_text().splitlines()) == 8
    assert len((output / "receipt_index.jsonl").read_text().splitlines()) == 10
    assert summary["training_executed"] is False
    assert summary["holdout_opened"] is False


def test_merged_assembly_rejects_resealed_snapshot_filename_drift(
    tmp_path: Path,
) -> None:
    from scripts.integrations.assemble_diffusion_planner_v24_native_corpus import (
        assemble_merged_corpus,
    )

    kwargs = _sources(tmp_path)
    pilot_root = kwargs["pilot_root"]
    old_pilot_sha256 = kwargs["expected_pilot_root_sha256"]
    snapshot = next((pilot_root / "snapshots").glob("*.json"))
    snapshot.rename(snapshot.with_name(f"{_sha('wrong-name')}.json"))
    kwargs["expected_pilot_root_sha256"] = _seal(pilot_root)
    kwargs["expected_pilot_review_root_sha256"] = _rechain_review_source(
        kwargs["pilot_review_root"],
        source_field="source_pilot_root_sha256",
        old_source_sha256=old_pilot_sha256,
        new_source_sha256=kwargs["expected_pilot_root_sha256"],
    )

    with pytest.raises(ValueError, match="snapshot content address"):
        assemble_merged_corpus(output_dir=tmp_path / "merged", **kwargs)


def test_merged_assembly_rejects_resealed_route_metadata_drift(
    tmp_path: Path,
) -> None:
    from scripts.integrations.assemble_diffusion_planner_v24_native_corpus import (
        assemble_merged_corpus,
    )

    kwargs = _sources(tmp_path)
    remaining_root = kwargs["remaining_root"]
    old_remaining_sha256 = kwargs["expected_remaining_root_sha256"]
    receipts = sorted((remaining_root / "receipts").rglob("seed_*.json"))
    route = json.loads(receipts[0].read_text())["route_identity_sha256"]
    receipt = next(
        path
        for path in receipts
        if json.loads(path.read_text())["route_identity_sha256"] == route
        and json.loads(path.read_text())["seed"] == 24003
    )
    payload = json.loads(receipt.read_text())
    payload["map_family_id"] = "drifted-map-family"
    _write_json(receipt, payload)
    kwargs["expected_remaining_root_sha256"] = _seal(remaining_root)
    kwargs["expected_remaining_review_root_sha256"] = _rechain_review_source(
        kwargs["remaining_review_root"],
        source_field="source_remaining_root_sha256",
        old_source_sha256=old_remaining_sha256,
        new_source_sha256=kwargs["expected_remaining_root_sha256"],
    )

    with pytest.raises(ValueError, match="route metadata changed"):
        assemble_merged_corpus(output_dir=tmp_path / "merged", **kwargs)


@pytest.mark.parametrize("target", ["pilot", "pilot_review"])
def test_merged_assembly_rejects_resealed_nonzero_source_exit(
    tmp_path: Path, target: str
) -> None:
    from scripts.integrations.assemble_diffusion_planner_v24_native_corpus import (
        assemble_merged_corpus,
    )

    kwargs = _sources(tmp_path)
    root = kwargs[f"{target}_root"]
    (root / "run.exit").write_text("1\n", encoding="ascii")
    kwargs[f"expected_{target}_root_sha256"] = _seal(root)
    if target == "pilot":
        old_pilot_sha256 = kwargs["expected_pilot_root_sha256"]
        # Re-sealing already replaced the expected value; recover old source from review.
        review = json.loads((kwargs["pilot_review_root"] / "review.json").read_text())
        old_pilot_sha256 = review["source_pilot_root_sha256"]
        kwargs["expected_pilot_review_root_sha256"] = _rechain_review_source(
            kwargs["pilot_review_root"],
            source_field="source_pilot_root_sha256",
            old_source_sha256=old_pilot_sha256,
            new_source_sha256=kwargs["expected_pilot_root_sha256"],
        )

    with pytest.raises(ValueError, match="source run.exit"):
        assemble_merged_corpus(output_dir=tmp_path / "merged", **kwargs)


def test_merged_independent_review_recomputes_indexes(tmp_path: Path) -> None:
    from scripts.integrations.assemble_diffusion_planner_v24_native_corpus import (
        assemble_merged_corpus,
        seal_artifact,
    )
    from scripts.integrations.review_diffusion_planner_v24_native_corpus_merged import (
        review_merged_corpus,
    )

    sources = _sources(tmp_path)
    output = tmp_path / "merged"
    assemble_merged_corpus(output_dir=output, **sources)
    _complete_assembly_evidence(output, sources)
    assembly_sha = seal_artifact(output)

    review = review_merged_corpus(
        assembly_root=output,
        expected_assembly_root_sha256=assembly_sha,
        expected_assembly_camp_head=ASSEMBLY_HEAD,
        **sources,
    )

    assert review["status"] == "passed"
    assert review["failed_count"] == 0
    assert review["recomputed"]["snapshot_count"] == 8
    assert review["decision"]["atom_availability_review_authorized"] is True
    assert review["decision"]["training_authorized"] is False


def test_merged_independent_review_rejects_resealed_index_drift(
    tmp_path: Path,
) -> None:
    from scripts.integrations.assemble_diffusion_planner_v24_native_corpus import (
        assemble_merged_corpus,
        seal_artifact,
    )
    from scripts.integrations.review_diffusion_planner_v24_native_corpus_merged import (
        review_merged_corpus,
    )

    sources = _sources(tmp_path)
    output = tmp_path / "merged"
    assemble_merged_corpus(output_dir=output, **sources)
    _complete_assembly_evidence(output, sources)
    index = output / "snapshot_index.jsonl"
    rows = index.read_text().splitlines()
    row = json.loads(rows[0])
    row["phase"] = "remaining" if row["phase"] == "pilot" else "pilot"
    rows[0] = json.dumps(row, sort_keys=True, separators=(",", ":"))
    index.write_text("\n".join(rows) + "\n", encoding="utf-8")
    assembly_sha = seal_artifact(output)

    review = review_merged_corpus(
        assembly_root=output,
        expected_assembly_root_sha256=assembly_sha,
        expected_assembly_camp_head=ASSEMBLY_HEAD,
        **sources,
    )

    assert review["status"] == "failed"
    assert "snapshot_index_exact" in review["failed_checks"]


def test_merged_independent_review_rejects_resealed_run_exit_drift(
    tmp_path: Path,
) -> None:
    from scripts.integrations.assemble_diffusion_planner_v24_native_corpus import (
        assemble_merged_corpus,
        seal_artifact,
    )
    from scripts.integrations.review_diffusion_planner_v24_native_corpus_merged import (
        review_merged_corpus,
    )

    sources = _sources(tmp_path)
    output = tmp_path / "merged"
    assemble_merged_corpus(output_dir=output, **sources)
    _complete_assembly_evidence(output, sources)
    (output / "run.exit").write_text("1\n", encoding="ascii")
    assembly_sha = seal_artifact(output)

    review = review_merged_corpus(
        assembly_root=output,
        expected_assembly_root_sha256=assembly_sha,
        expected_assembly_camp_head=ASSEMBLY_HEAD,
        **sources,
    )

    assert review["status"] == "failed"
    assert "assembly_execution_receipts" in review["failed_checks"]


def test_merged_independent_review_rejects_resealed_source_review_exit(
    tmp_path: Path,
) -> None:
    from scripts.integrations.assemble_diffusion_planner_v24_native_corpus import (
        assemble_merged_corpus,
        seal_artifact,
    )
    from scripts.integrations.review_diffusion_planner_v24_native_corpus_merged import (
        review_merged_corpus,
    )

    sources = _sources(tmp_path)
    output = tmp_path / "merged"
    assemble_merged_corpus(output_dir=output, **sources)
    _complete_assembly_evidence(output, sources)
    old_review_sha256 = sources["expected_pilot_review_root_sha256"]
    pilot_review_root = sources["pilot_review_root"]
    (pilot_review_root / "run.exit").write_text("1\n", encoding="ascii")
    sources["expected_pilot_review_root_sha256"] = _seal(pilot_review_root)
    heads = output / "HEADS"
    heads.write_text(
        heads.read_text().replace(
            old_review_sha256, sources["expected_pilot_review_root_sha256"]
        ),
        encoding="ascii",
    )
    summary_path = output / "merged_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["source_artifacts"]["pilot_review"]["root_sha256"] = sources[
        "expected_pilot_review_root_sha256"
    ]
    _write_json(summary_path, summary)
    (output / "stdout.txt").write_text(
        json.dumps(summary, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    assembly_sha = seal_artifact(output)

    review = review_merged_corpus(
        assembly_root=output,
        expected_assembly_root_sha256=assembly_sha,
        expected_assembly_camp_head=ASSEMBLY_HEAD,
        **sources,
    )

    assert review["status"] == "failed"
    assert "source_execution_receipts" in review["failed_checks"]


@pytest.mark.parametrize(
    "script",
    [
        "assemble_diffusion_planner_v24_native_corpus.py",
        "review_diffusion_planner_v24_native_corpus_merged.py",
    ],
)
def test_merged_corpus_clis_bootstrap_repo_root(script: str) -> None:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "integrations" / script), "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
