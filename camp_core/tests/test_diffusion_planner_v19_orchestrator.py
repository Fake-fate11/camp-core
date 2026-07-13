from __future__ import annotations

import importlib

import pytest


def _orchestrator():
    try:
        return importlib.import_module(
            "scripts.integrations.run_diffusion_planner_dp_camp_v19"
        )
    except ModuleNotFoundError:
        pytest.fail("the thin v19 status reader is missing")


def test_v19_pointer_reader_ignores_historical_file_tail(tmp_path) -> None:
    module = _orchestrator()
    pointer = {
        "current_v19_status": "ready",
        "current_v19_artifact_scope": "scope",
        "current_v19_artifact": "/artifact",
        "current_v19_artifact_root_sha256": "a" * 64,
        "next_work_target": "native_provenance_audit_only",
    }
    lines = "\n".join(f"{key}={value}" for key, value in pointer.items())
    status = tmp_path / "status.md"
    status.write_text(
        "## Current V19 Status\n"
        + lines
        + "\n## Historical V18\nnext_work_target=wrong\n",
        encoding="utf-8",
    )
    audit = tmp_path / "audit.md"
    audit.write_text(lines + "\n", encoding="utf-8")

    assert module.read_v19_status_pointer(status, audit) == pointer


def test_v19_pointer_reader_rejects_status_audit_mismatch(tmp_path) -> None:
    module = _orchestrator()
    status = tmp_path / "status.md"
    status.write_text(
        "## Current V19 Status\n"
        "current_v19_status=ready\n"
        "current_v19_artifact_scope=scope\n"
        "current_v19_artifact=/artifact\n"
        f"current_v19_artifact_root_sha256={'a' * 64}\n"
        "next_work_target=wrong\n",
        encoding="utf-8",
    )
    audit = tmp_path / "audit.md"
    audit.write_text(
        "current_v19_status=ready\n"
        "current_v19_artifact_scope=scope\n"
        "current_v19_artifact=/artifact\n"
        f"current_v19_artifact_root_sha256={'a' * 64}\n"
        "next_work_target=correct\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match v19 audit EOF"):
        module.read_v19_status_pointer(status, audit)


def test_checked_in_current_v19_pointer_matches_v19_audit_eof() -> None:
    module = _orchestrator()

    pointer = module.read_v19_status_pointer(
        module.Path("docs/diffusion_planner_current_status.md"),
        module.Path("docs/diffusion_planner_v19_iteration_audit.md"),
    )

    assert pointer["current_v19_status"] == (
        "v19_carla_nonroot_execute_only_acl_restore_drill_independent_review_"
        "passed"
    )
    assert pointer["next_work_target"] == (
        "v19_carla_nonroot_execute_only_acl_runtime_attempt_preflight_only"
    )
