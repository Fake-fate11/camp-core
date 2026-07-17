from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pickle

import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from scripts.integrations import (
    review_diffusion_planner_v25_controlled_training_corpus as corpus_reviewer,
    review_diffusion_planner_v25_full_config_preflight as full_config_reviewer,
    run_diffusion_planner_v25_controlled_training_corpus as corpus,
)


def test_real_snapshot_writer_one_identity_roundtrip_index_and_seal(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "identity"
    artifact.mkdir()
    scenario_id = "a" * 64
    rows = []
    with (artifact / "snapshot_index.jsonl").open("w", encoding="utf-8") as index:
        for tick in range(corpus.CORPUS_STEPS):
            payload = {
                "schema_version": corpus.SNAPSHOT_SCHEMA_VERSION,
                "feature_payload": {"tick_value": float(tick)},
                "sidecar": {
                    "scenario_id": scenario_id,
                    "tick_index": tick,
                    "outcome_fields_consumed": [],
                    "fresh_b_opened": False,
                },
            }
            rows.append(
                corpus._write_content_addressed_snapshot(
                    output_dir=artifact,
                    index_file=index,
                    scenario_id=scenario_id,
                    tick_index=tick,
                    payload=payload,
                )
            )

    (artifact / "identity.json").write_text(
        json.dumps(
            {
                "scenario_id": scenario_id,
                "status": "complete",
                "snapshot_count": corpus.CORPUS_STEPS,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (artifact / "run.exit").write_text("0\n", encoding="ascii")
    root = seal_artifact(artifact, label="V25 one-identity writer regression")
    assert verify_complete_seal(artifact, root, label="writer regression")[
        "root_sha256"
    ] == root

    index_rows = [
        json.loads(line)
        for line in (artifact / "snapshot_index.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert index_rows == rows
    assert len(index_rows) == corpus.CORPUS_STEPS
    for row in index_rows:
        path = artifact / row["relative_path"]
        raw = path.read_bytes()
        assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
        payload = corpus_reviewer._read_verified_content_addressed_snapshot(
            path, row["sha256"]
        )
        assert hashlib.sha256(raw).hexdigest() == corpus._canonical_sha256(payload)
        assert path.name == f"{row['sha256']}.json"

    first = index_rows[0]
    path = artifact / first["relative_path"]
    double_lf = path.read_bytes() + b"\n"
    path.write_bytes(double_lf)
    with pytest.raises(ValueError, match="exactly one LF"):
        corpus_reviewer._read_verified_content_addressed_snapshot(
            path, first["sha256"]
        )


def test_frozen_authority_rejects_resigned_alternate_universe(
    tmp_path: Path,
) -> None:
    alternate_map = tmp_path / "alternate_map.osm"
    alternate_map.write_text("<osm version='0.6'/>\n", encoding="utf-8")
    alternate_route = tmp_path / "alternate_route.pkl"
    alternate_route.write_bytes(
        pickle.dumps({"lanelet_ids": [999], "map": str(alternate_map)})
    )
    alternate_template = tmp_path / "alternate_template.json"
    alternate_template.write_text(
        json.dumps(
            {
                "schema_version": (
                    full_config_reviewer.EXPECTED_PROBE_TEMPLATE_SCHEMA_VERSION
                ),
                "map": {
                    "path": str(alternate_map),
                    "sha256": hashlib.sha256(alternate_map.read_bytes()).hexdigest(),
                },
                "routes": {
                    "path": str(alternate_route),
                    "sha256": hashlib.sha256(alternate_route.read_bytes()).hexdigest(),
                },
                "fixed_dp": {
                    "repo": str(full_config_reviewer.EXPECTED_DP_REPO),
                    "head": full_config_reviewer.FIXED_DP_HEAD,
                    "checkpoint": dict(
                        full_config_reviewer.EXPECTED_FIXED_DP_CHECKPOINT
                    ),
                    "args_json": dict(full_config_reviewer.EXPECTED_FIXED_DP_ARGS),
                    "native_source_sha256": dict(
                        full_config_reviewer.EXPECTED_DP_NATIVE_SOURCE_SHA256
                    ),
                },
                "selector": {
                    "weights": dict(full_config_reviewer.EXPECTED_STATIC_WEIGHTS)
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    alternate_formal = tmp_path / "alternate_formal"
    alternate_formal.mkdir()
    train = [
        {
            "schema_version": (
                full_config_reviewer.EXPECTED_FORMAL_CASE_SCHEMA_VERSION
            ),
            "scenario_id": hashlib.sha256(f"alternate-{index}".encode()).hexdigest(),
            "split": "train",
            "seeds": [full_config_reviewer.EXPECTED_SEED],
            "outcome_blind": True,
            "outcome_fields_consumed": [],
            "holdout_outcome_consumed": False,
            "runner_eligible": index < 1500,
            "retention_role": (
                "executable" if index < 1500 else "source_ineligible_retained"
            ),
            "source_map_path": str(alternate_map),
            "source_map_sha256": hashlib.sha256(
                alternate_map.read_bytes()
            ).hexdigest(),
            "route_spec": {"path": str(alternate_route)},
        }
        for index in range(1653)
    ]
    summary = {
        "split_counts": {
            "train": {
                "manifest_identity_count": 1653,
                "executable_identity_count": 1500,
                "source_ineligible_identity_count": 153,
            }
        }
    }
    formal_report = {
        "schema_version": (
            full_config_reviewer.EXPECTED_FORMAL_REPORT_SCHEMA_VERSION
        ),
        "status": "passed",
        "mode": "freeze_formal",
        "checks": {"alternate_universe_self_consistent": True},
        "pilot_review": {"status": "passed"},
        "source_summary": summary,
        "model_loaded": False,
        "candidate_generation_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
        "claim_authorized": False,
    }
    (alternate_formal / "report.json").write_text(
        json.dumps(formal_report, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (alternate_formal / "controlled_corpus_final_plan.json").write_text(
        json.dumps(
            {
                "schema_version": (
                    full_config_reviewer.EXPECTED_FORMAL_PLAN_SCHEMA_VERSION
                ),
                "outcome_blind": True,
                "outcome_fields_consumed": [],
                "fresh_b_outcome_opened": False,
                "train": train,
                "calibration": [],
                "fresh_b": [],
                "summary": summary,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (alternate_formal / "run.exit").write_text("0\n", encoding="ascii")
    formal_root = seal_artifact(alternate_formal, label="alternate formal")
    assert verify_complete_seal(
        alternate_formal, formal_root, label="alternate formal"
    )["root_sha256"] == formal_root

    alternate_release = tmp_path / "alternate_release"
    alternate_release.mkdir()
    report = {
        "formal_artifact": str(alternate_formal),
        "formal_root_sha256": formal_root,
        "probe_template": str(alternate_template),
        "probe_template_sha256": hashlib.sha256(
            alternate_template.read_bytes()
        ).hexdigest(),
        "generation_scales": dict(
            full_config_reviewer.EXPECTED_GENERATION_SCALES
        ),
        "static_weights": dict(full_config_reviewer.EXPECTED_STATIC_WEIGHTS),
        "dp_repo": str(full_config_reviewer.EXPECTED_DP_REPO),
    }
    release = {
        **report,
        "schema_version": full_config_reviewer.PREFLIGHT_RELEASE_SCHEMA_VERSION,
        "status": "full_config_preflight_released",
        "implementation_source_head": "a" * 40,
        "pointer_head_at_release": "a" * 40,
        "fixed_dp_head": full_config_reviewer.FIXED_DP_HEAD,
        "fixed_dp_checkpoint": dict(
            full_config_reviewer.EXPECTED_FIXED_DP_CHECKPOINT
        ),
        "fixed_dp_args_json": dict(full_config_reviewer.EXPECTED_FIXED_DP_ARGS),
        "native_source_roots": dict(full_config_reviewer.S01_NATIVE_SOURCE_ROOTS),
        "root_artifacts": {},
        "rejected_roots": [full_config_reviewer.SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "critical_implementation_manifest": {},
        "run_nonce": "b" * 64,
        "authorized_output_dir": str(tmp_path / "alternate_preflight"),
        "full_config_preflight_authorized": True,
        "full_r_execute_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    (alternate_release / "decision.json").write_text(
        json.dumps(release, sort_keys=True) + "\n", encoding="utf-8"
    )
    (alternate_release / "run.exit").write_text("0\n", encoding="ascii")
    release_root = seal_artifact(alternate_release, label="alternate release")
    assert verify_complete_seal(
        alternate_release, release_root, label="alternate release"
    )["root_sha256"] == release_root

    with pytest.raises(ValueError, match="authority universe"):
        full_config_reviewer._verify_frozen_authority_universe(report, release)


def test_seed_and_frozen_primary_universe_are_literal_authority() -> None:
    assert full_config_reviewer.EXPECTED_SEED == 25001
    assert full_config_reviewer.EXPECTED_SEED != 20260716
    assert full_config_reviewer.EXPECTED_FORMAL_ROOT_SHA256 == (
        "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
    )
    assert full_config_reviewer.EXPECTED_PROBE_TEMPLATE_SHA256 == (
        "1e734165f7a614e93019df0a5c22b5e36722298cb50b21c5ce8fd0e4e2cf82bc"
    )
