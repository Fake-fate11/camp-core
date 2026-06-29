from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.diagnose_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_overlap_failure import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DIAGNOSED_STATUS,
    FIXED_DP_HEAD,
    OVERLAP_FAILED_CHECK,
    build_report,
    main,
)


CAMP_HEAD = "9cdf56c10bfc872f4fd02e17d5313a7984c81c95"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _record(hash_label: str) -> dict:
    return {
        "default_off_shadow_selector": {
            "candidate_tensor_hash": {
                "sha256": _sha(hash_label),
                "shape": [8, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
    }


def _log_path(root: Path, route: str, seed: int, npc: int, tl: str) -> Path:
    return (
        root
        / route
        / f"seed_{seed}"
        / f"npc_{npc}"
        / "spawn_0p3"
        / tl
        / "static_shadow"
        / "camp_selection_log.json"
    )


def _write_logs(root: Path, *, prefix: str) -> list[Path]:
    logs = [
        _log_path(root, "sample_normal", 301, 0, "tl_on"),
        _log_path(root, "sample_tl", 302, 4, "tl_off"),
    ]
    for log_index, path in enumerate(logs):
        rows = [
            _record(f"{prefix}-{log_index}-{record_index}")
            for record_index in range(3)
        ]
        _write(path, json.dumps(rows))
    return logs


def _write_audit_md(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"next_work_target={AUTHORIZED_CURRENT_WORK}",
                "training_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def _write_result_readiness(path: Path) -> Path:
    return _write(
        path,
        json.dumps(
            {
                "final_decision": {
                    "status": "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_result_readiness_rejected",
                    "passed": False,
                    "failed_checks": [OVERLAP_FAILED_CHECK],
                },
                "candidate_tensor_overlap": {
                    "eval_hash_count": 6,
                    "eval_hashes_in_previous_count": 6,
                    "eval_hashes_in_previous_rate": 1.0,
                    "previous_hash_count": 12,
                },
            }
        ),
    )


def _case(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    evaluation = tmp_path / "evaluation"
    nonmatching_train = tmp_path / "nonmatching_train"
    prior_eval = tmp_path / "prior_eval"
    eval_logs = _write_logs(evaluation, prefix="eval")
    nonmatching_logs = _write_logs(nonmatching_train, prefix="train")
    prior_eval_logs = _write_logs(prior_eval, prefix="eval")
    training_summary = _write(
        tmp_path / "training_summary.json",
        json.dumps(
            {
                "selection_logs": [
                    *(str(path) for path in nonmatching_logs),
                    *(str(path) for path in prior_eval_logs),
                ]
            }
        ),
    )
    assert len(eval_logs) == 2
    result_readiness = _write_result_readiness(tmp_path / "result_readiness.json")
    audit_md = _write_audit_md(tmp_path / "audit.md")
    return evaluation, result_readiness, training_summary, audit_md


def test_overlap_failure_diagnosis_finds_prior_eval_reuse(tmp_path: Path) -> None:
    evaluation, result_readiness, training_summary, audit_md = _case(tmp_path)

    report = build_report(
        evaluation_output_dir=evaluation,
        result_readiness_json=result_readiness,
        previous_training_summary_json=training_summary,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_selection_log_count=2,
        expected_records=6,
    )

    assert report["final_decision"]["status"] == DIAGNOSED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["training_executed"] is False
    assert report["final_decision"]["candidate_generation_executed"] is False
    assert report["path_provenance"]["evaluation_signatures_in_previous_count"] == 2
    assert report["hash_provenance"]["matched_evaluation_record_count"] == 6
    assert report["hash_provenance"]["same_signature_and_step_hash_match_records"] == 6
    assert report["hash_provenance"]["matched_evaluation_record_rate"] == 1.0
    assert (
        report["diagnosis"]["failure_class"]
        == "training_summary_includes_prior_evaluation_replay_logs_reused_by_current_evaluation"
    )


def test_overlap_failure_diagnosis_rejects_nonoverlap_inputs(tmp_path: Path) -> None:
    evaluation, result_readiness, training_summary, audit_md = _case(tmp_path)
    payload = json.loads(training_summary.read_text(encoding="utf-8"))
    payload["selection_logs"] = payload["selection_logs"][:2]
    training_summary.write_text(json.dumps(payload), encoding="utf-8")

    report = build_report(
        evaluation_output_dir=evaluation,
        result_readiness_json=result_readiness,
        previous_training_summary_json=training_summary,
        v13_audit_md=audit_md,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        expected_selection_log_count=2,
        expected_records=6,
    )

    assert report["final_decision"]["passed"] is False
    assert "matched_evaluation_record_count" in report["final_decision"]["failed_checks"]
    assert "same_signature_and_step_hash_match_records" in report["final_decision"]["failed_checks"]


def test_overlap_failure_diagnosis_main_writes_outputs(tmp_path: Path) -> None:
    evaluation, result_readiness, training_summary, audit_md = _case(tmp_path)
    output_json = tmp_path / "diagnosis.json"
    output_md = tmp_path / "diagnosis.md"

    exit_code = main(
        [
            "--evaluation_output_dir",
            str(evaluation),
            "--result_readiness_json",
            str(result_readiness),
            "--previous_training_summary_json",
            str(training_summary),
            "--v13_audit_md",
            str(audit_md),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--expected_selection_log_count",
            "2",
            "--expected_records",
            "6",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"]["passed"] is True
    assert DIAGNOSED_STATUS in output_md.read_text(encoding="utf-8")
