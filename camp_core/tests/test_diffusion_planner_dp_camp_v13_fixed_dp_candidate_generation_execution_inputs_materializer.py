from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.materialize_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_execution_inputs import (
    APPROVED_SOURCE_KIND,
    APPROVED_SOURCE_REMEDIATION_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


def _write(path: Path, data: bytes | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _fixture(tmp_path: Path, *, source_name: str = "fresh_fixed_dp_scene_001.npz") -> dict[str, Path]:
    source = _write(tmp_path / "sources" / source_name, b"npz-bytes")
    checkpoint = _write(tmp_path / "dp" / "diffusion_planner.pth", b"checkpoint")
    args_json = _write_json(tmp_path / "dp" / "diffusion_planner.args.json", {"model": "fixed_dp"})
    manifest = _write_json(
        tmp_path / "approved_sources.json",
        {
            "approved_source_kind": APPROVED_SOURCE_KIND,
            "files": [str(source.resolve())],
        },
    )
    return {
        "source": source,
        "checkpoint": checkpoint,
        "args_json": args_json,
        "manifest": manifest,
    }


def _report(tmp_path: Path, *, source_name: str = "fresh_fixed_dp_scene_001.npz") -> dict[str, object]:
    paths = _fixture(tmp_path, source_name=source_name)
    return build_report(
        source_npz=[paths["source"]],
        approved_source_manifest_json=paths["manifest"],
        source_manifest_root="fresh_eval_split_v13_nonformal",
        fixed_dp_checkpoint=paths["checkpoint"],
        fixed_dp_args_json=paths["args_json"],
        current_dp_head=FIXED_DP_HEAD,
        output_dir=tmp_path / "materialized",
    )


def test_materializer_writes_fixed_dp_input_contract_without_execution(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    contract = report["input_contract"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert contract["approved_source_kind"] == APPROVED_SOURCE_KIND
    assert contract["closed_loop_outcome_read"] is False
    assert contract["dp_modification"] is False
    assert contract["required_zero_overlap_keys"] == list(ZERO_OVERLAP_KEYS)
    record = contract["records"][0]
    for key in ZERO_OVERLAP_KEYS:
        assert record[key]


def test_materializer_rejects_empty_source_list(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    report = build_report(
        source_npz=[],
        approved_source_manifest_json=paths["manifest"],
        source_manifest_root="fresh_eval_split_v13_nonformal",
        fixed_dp_checkpoint=paths["checkpoint"],
        fixed_dp_args_json=paths["args_json"],
        current_dp_head=FIXED_DP_HEAD,
        output_dir=tmp_path / "materialized",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_npz_nonempty" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "missing_approved_fixed_dp_source_npz_manifest"
    )
    assert report["final_decision"]["recommended_next_work"] == APPROVED_SOURCE_REMEDIATION_NEXT_WORK


def test_materializer_rejects_full36_formal_seed_and_closed_loop_sources(tmp_path: Path) -> None:
    for source_name, expected in [
        ("fresh_fixed_dp_Full36_scene.npz", "source_npz_forbids_full36"),
        ("fresh_fixed_dp_formal_seed_11_scene.npz", "source_npz_forbids_formal_seed_11"),
        ("fresh_fixed_dp_closed_loop_scene.npz", "source_npz_forbids_closed_loop"),
    ]:
        report = _report(tmp_path / source_name, source_name=source_name)

        assert report["final_decision"]["status"] == REJECT_STATUS
        assert any(
            failed.startswith(expected)
            for failed in report["final_decision"]["failed_checks"]
        )


def test_materializer_rejects_unapproved_manifest_source(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    _write_json(
        paths["manifest"],
        {
            "approved_source_kind": APPROVED_SOURCE_KIND,
            "files": [],
        },
    )

    report = build_report(
        source_npz=[paths["source"]],
        approved_source_manifest_json=paths["manifest"],
        source_manifest_root="fresh_eval_split_v13_nonformal",
        fixed_dp_checkpoint=paths["checkpoint"],
        fixed_dp_args_json=paths["args_json"],
        current_dp_head=FIXED_DP_HEAD,
        output_dir=tmp_path / "materialized",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any(
        failed.startswith("source_npz_manifest_approved")
        for failed in report["final_decision"]["failed_checks"]
    )


def test_materializer_main_writes_valid_set_list_and_report(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"
    output_dir = tmp_path / "materialized"

    exit_code = main(
        [
            "--source_npz",
            str(paths["source"]),
            "--approved_source_manifest_json",
            str(paths["manifest"]),
            "--source_manifest_root",
            "fresh_eval_split_v13_nonformal",
            "--fixed_dp_checkpoint",
            str(paths["checkpoint"]),
            "--fixed_dp_args_json",
            str(paths["args_json"]),
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_dir",
            str(output_dir),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    valid_set_list = Path(payload["input_contract"]["valid_set_list"])
    valid_set = json.loads(valid_set_list.read_text(encoding="utf-8"))
    assert valid_set["files"] == [str(paths["source"].resolve())]
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "training_preflight_authorized: `False`" in output_md.read_text(encoding="utf-8")


def test_materializer_main_writes_rejected_report_without_source_npz(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    output_json = tmp_path / "report.json"
    output_md = tmp_path / "report.md"
    output_dir = tmp_path / "materialized"

    exit_code = main(
        [
            "--approved_source_manifest_json",
            str(paths["manifest"]),
            "--source_manifest_root",
            "fresh_eval_split_v13_nonformal",
            "--fixed_dp_checkpoint",
            str(paths["checkpoint"]),
            "--fixed_dp_args_json",
            str(paths["args_json"]),
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_dir",
            str(output_dir),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 1
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == REJECT_STATUS
    assert payload["final_decision"]["failure_class"] == (
        "missing_approved_fixed_dp_source_npz_manifest"
    )
    assert payload["final_decision"]["recommended_next_work"] == APPROVED_SOURCE_REMEDIATION_NEXT_WORK
    assert not (output_dir / "valid_set_list.json").exists()
