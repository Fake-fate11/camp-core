from __future__ import annotations

import json
from pathlib import Path

import pytest

from camp_core.integrations import diffusion_planner_v25_a17_full_corpus_authority as authority
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (
    canonical_json_bytes,
)


def _assets() -> dict:
    return {
        "probe_template": {
            "path": str(authority.EXPECTED_PROBE_TEMPLATE),
            "sha256": authority.EXPECTED_PROBE_TEMPLATE_SHA256,
            "schema_version": "camp_dp_v24_single_record_source_probe_v1",
        },
        "generation_scales": dict(authority.EXPECTED_GENERATION_SCALES),
        "static_weights": {
            **authority.EXPECTED_STATIC_WEIGHTS,
            "dtype": "float64",
            "shape": [14],
            "values": list(authority.EXPECTED_STATIC_WEIGHT_VALUES),
        },
        "fixed_dp_checkpoint": {
            **authority.EXPECTED_FIXED_DP_CHECKPOINT,
            "size_bytes": 1,
        },
        "fixed_dp_args_json": {
            **authority.EXPECTED_FIXED_DP_ARGS,
            "content_sha256": "b" * 64,
        },
        "native_sources": {},
        "generation_scales_size_bytes": 1,
    }


def _roots() -> dict:
    return {
        role: {
            "path": f"/authority/{role}",
            "root_sha256": f"{index + 1:064x}",
            "report_file": "decision.json" if role == "bounded_release" else "report.json",
        }
        for index, role in enumerate(authority.UPSTREAM_ROLES)
    }


def _prepare(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    dp = tmp_path / "dp"
    repo.mkdir()
    dp.mkdir()
    probe = tmp_path / "probe.json"
    probe.write_text(
        json.dumps(
            {
                "fixed_dp": {
                    "checkpoint": authority.EXPECTED_FIXED_DP_CHECKPOINT,
                    "args_json": authority.EXPECTED_FIXED_DP_ARGS,
                },
                "selector": {"weights": authority.EXPECTED_STATIC_WEIGHTS},
            }
        ),
        encoding="utf-8",
    )
    upstream = {
        "bounded_source_head": "c" * 40,
        "release_root_sha256": "d" * 64,
        "execution_root_sha256": "e" * 64,
        "review_root_sha256": "f" * 64,
        "execution_assets": _assets(),
    }
    monkeypatch.setattr(authority, "verify_upstream_chain", lambda **_: upstream)
    monkeypatch.setattr(authority, "verify_frozen_execution_assets", lambda **_: _assets())
    monkeypatch.setattr(
        authority,
        "build_critical_implementation_manifest",
        lambda _repo: {"critical.py": "a" * 64},
    )
    monkeypatch.setattr(authority, "verify_dual_head_contract", lambda **_: {})
    return repo, dp, probe


def test_preflight_release_is_exact_one_shot_and_all_later_gates_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, dp, probe = _prepare(monkeypatch, tmp_path)
    output = str((tmp_path / "preflight").resolve())
    decision = authority.build_preflight_release_decision(
        repo=repo,
        implementation_source_head="1" * 40,
        pointer_head_at_release="1" * 40,
        root_artifacts=_roots(),
        run_nonce="2" * 64,
        authorized_output_dir=output,
        dp_repo=dp,
        probe_template=probe,
    )
    assert set(decision) == authority.PREFLIGHT_RELEASE_FIELDS
    assert decision["full_config_preflight_authorized"] is True
    for field in (
        "full_r_execute_authorized",
        "monitor_enabled",
        "training_executed",
        "calibration_executed",
        "scene_runtime_enabled",
        "v2i_enabled",
        "fresh_b2_opened",
    ):
        assert decision[field] is False
    assert decision["executable_identity_count"] == 1500
    assert decision["retained_source_ineligible_count"] == 153
    assert decision["snapshot_capacity"] == 96000

    release = tmp_path / "release"
    release.mkdir()
    (release / "decision.json").write_bytes(canonical_json_bytes(decision))
    (release / "HEADS").write_bytes((
        f"camp_source_head={'1' * 40}\n"
        f"camp_pointer_head={'1' * 40}\n"
        f"fixed_dp_head={authority.FIXED_DP_HEAD}\n"
    ).encode("ascii"))
    (release / "COMMAND").write_text("create preflight\n", encoding="utf-8")
    (release / "run.exit").write_bytes(b"0\n")
    monkeypatch.setattr(
        authority,
        "verify_complete_seal",
        lambda *_args, **_kwargs: {
            "root_sha256": "3" * 64,
            "manifest_paths": authority.RELEASE_PAYLOADS,
        },
    )
    monkeypatch.setattr(authority, "NONCE_LEDGER", tmp_path / "nonces")
    verified = authority.verify_release(
        repo=repo,
        release_artifact=release,
        release_root_sha256="3" * 64,
        requested_output_dir=output,
        current_pointer_head="1" * 40,
        dp_repo=dp,
        probe_template=probe,
        mode="preflight",
        consume=True,
    )
    assert verified["nonce_marker"] is not None
    with pytest.raises(ValueError, match="already consumed"):
        authority.verify_release(
            repo=repo,
            release_artifact=release,
            release_root_sha256="3" * 64,
            requested_output_dir=output,
            current_pointer_head="1" * 40,
            dp_repo=dp,
            probe_template=probe,
            mode="preflight",
            consume=True,
        )


def test_release_rejects_extra_field_and_noncanonical_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, dp, probe = _prepare(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="canonical path"):
        authority.build_preflight_release_decision(
            repo=repo,
            implementation_source_head="1" * 40,
            pointer_head_at_release="1" * 40,
            root_artifacts=_roots(),
            run_nonce="2" * 64,
            authorized_output_dir=str(tmp_path / "x" / ".." / "preflight"),
            dp_repo=dp,
            probe_template=probe,
        )
