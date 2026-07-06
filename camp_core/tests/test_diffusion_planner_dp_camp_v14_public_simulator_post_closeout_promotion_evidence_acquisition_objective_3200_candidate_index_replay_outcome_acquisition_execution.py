from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition.py"
)
SOURCE_HEAD = "a" * 40
CURRENT_HEAD = "b" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_execution",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_replay_outcome_acquisition_execution_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    acquisition = report["strict_pairing_summary"]
    commands = report["command_manifest"]["commands"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["candidate_index_replay_execution_executed_by_this_gate"] is True
    assert decision["outcome_acquisition_executed_by_this_gate"] is True
    assert acquisition["candidate_closed_loop_outcome_records"] == 2
    assert acquisition["paired_record_key_count"] == 2
    assert commands[0]["command"][-2:] == [
        "--camp_collect_closed_loop_outcomes",
        "--candidate_index_replay",
    ]
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.EXECUTION_MD_NAME).is_file()
    assert (fixture["output_dir"] / module.RUNBOOK_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_replay_outcome_acquisition_execution_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "execution_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_replay_outcome_acquisition_execution_authorization_missing"
    )


def test_candidate_index_replay_outcome_acquisition_execution_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["execution"]["attempted"] is False


def test_candidate_index_replay_outcome_acquisition_execution_rejects_preexisting_output(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["candidate_index_output_root"].mkdir(parents=True)

    report = module.build_report(**fixture)

    assert "candidate_index_output_root_preexisting" in report["final_decision"]["failed_checks"]
    assert report["execution"]["attempted"] is False


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_replay_outcome_acquisition_preflight_static_review_passed=True",
            "objective_3200_candidate_index_replay_outcome_acquisition_execution_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source_artifact = tmp_path / "source_static_review_artifact"
    review_dir = source_artifact / "review"
    review_json = _write_json(review_dir / module.SOURCE_STATIC_REVIEW_JSON_NAME, _source_review_report(module))
    review_md = _write(review_dir / module.SOURCE_STATIC_REVIEW_MD_NAME, "# static review\n")
    review_sha = _write_sha256s(review_dir / "SHA256SUMS", [review_json, review_md])
    heads = _write(
        source_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    command = _write(source_artifact / "COMMAND", "python static_review.py\n")
    stdout = _write(source_artifact / "stdout", "{}\n")
    stderr = _write(source_artifact / "stderr", "")
    run_exit = _write(source_artifact / "run.exit", "0\n")
    _write_sha256s(
        source_artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, review_json, review_md, review_sha],
        relative_to=source_artifact,
    )

    source_runtime = tmp_path / "source_runtime"
    fake_runner = _write_fake_runner(tmp_path / "run_diffusion_planner_camp_replay.py")
    runbook = _write_source_runbook(
        tmp_path / "source_runbook.sh",
        source_runtime=source_runtime,
        fake_runner=fake_runner,
    )

    return {
        "source_preflight_static_review_artifact_dir": source_artifact,
        "source_preflight_static_review_json": review_json,
        "source_preflight_static_review_md": review_md,
        "source_preflight_static_review_sha256s": review_sha,
        "source_runtime_execution_dir": source_runtime,
        "source_runtime_runbook": runbook,
        "candidate_index_output_root": tmp_path / "candidate_index_runtime",
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_record_count": 2,
        "expected_selection_log_count": 2,
        "expected_num_candidates": module.EXPECTED_NUM_CANDIDATES,
        "enabled": True,
        "execute_commands": True,
    }


def _source_review_report(module) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_STATIC_REVIEW_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_candidate_index_replay_outcome_acquisition_execution_authorized": True,
        "objective_required_records": 2,
        "candidate_closed_loop_outcome_records": 0,
        "missing_candidate_closed_loop_outcome_records": 2,
        "candidate_index_replay_harness_implemented": True,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "outcome_acquisition_executed": False,
            "dp_modification": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "final_decision": decision,
    }


def _write_source_runbook(path: Path, *, source_runtime: Path, fake_runner: Path) -> Path:
    output_dirs = [
        source_runtime / "sample_normal" / "seed_1" / "tl_on" / "runtime_default_off_shadow_replay",
        source_runtime / "sample_normal" / "seed_1" / "tl_off" / "runtime_default_off_shadow_replay",
    ]
    for index, output_dir in enumerate(output_dirs):
        _write_selection_log(output_dir / "camp_selection_log.json", record_index=index, candidate_index=False)
        _write_json(output_dir / "camp_validation_summary.json", {"ok": True})
    commands = []
    for output_dir in output_dirs:
        command = [
            sys.executable,
            str(fake_runner),
            "--output_dir",
            str(output_dir),
            "--seed",
            "1",
            "--steps",
            "1",
            "--num_candidates",
            "8",
            "--camp_selector_mode",
            "static",
            "--camp_candidate_tensor_provenance_logging",
            "--camp_default_off_shadow_selector",
        ]
        commands.append(" ".join(_quote(part) for part in command))
    return _write(path, "\n".join(commands) + "\n")


def _write_fake_runner(path: Path) -> Path:
    return _write(
        path,
        r'''
from __future__ import annotations
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output_dir", type=Path, required=True)
parser.add_argument("--seed")
parser.add_argument("--steps")
parser.add_argument("--num_candidates")
parser.add_argument("--camp_selector_mode")
parser.add_argument("--camp_candidate_tensor_provenance_logging", action="store_true")
parser.add_argument("--camp_default_off_shadow_selector", action="store_true")
parser.add_argument("--camp_collect_closed_loop_outcomes", action="store_true")
parser.add_argument("--candidate_index_replay", action="store_true")
args = parser.parse_args()

if not args.camp_collect_closed_loop_outcomes or not args.candidate_index_replay:
    raise SystemExit(17)

args.output_dir.mkdir(parents=True, exist_ok=True)
record = {
    "selected_index": 3,
    "executed_index": 3,
    "num_candidates": 8,
    "selection_weights": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "candidate_closed_loop_outcomes": [{"safety_cost_v1": 0.0}] * 8,
    "default_off_shadow_selector": {
        "score_expression": "score_k(w)=a_k^T w",
        "shadow_selected_index": 3,
        "executed_index": 3,
        "candidate_tensor_hash": {"sha256": "abc"},
    },
    "candidate_index_replay_harness": {
        "payload_valid": True,
        "executed_shadow_selected_index": True,
        "closed_loop_outcomes_used_for_training": False,
        "closed_loop_outcomes_used_for_online_selector": False,
        "candidate_tensor_hash": {"sha256": "abc"},
    },
    "camp_candidate_tensor_provenance": {
        "pre_camp_scoring_tensor": {"sha256": "abc"},
        "post_camp_selector_tensor": {"sha256": "abc"},
        "candidate_tensor_mutation_effect": False,
        "pre_post_tensor_hash_equal": True,
        "reference_blend_present": False,
        "outcome_label_input": False,
    },
}
(args.output_dir / "camp_selection_log.json").write_text(json.dumps([record], indent=2), encoding="utf-8")
(args.output_dir / "camp_validation_summary.json").write_text(json.dumps({"ok": True}, indent=2), encoding="utf-8")
(args.output_dir / "camp_replay_summary.json").write_text(json.dumps({"ok": True}, indent=2), encoding="utf-8")
'''.lstrip(),
    )


def _write_selection_log(path: Path, *, record_index: int, candidate_index: bool) -> Path:
    record = {
        "selected_index": 0 if not candidate_index else 3,
        "executed_index": 0 if not candidate_index else 3,
        "num_candidates": 8,
        "selection_weights": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "default_off_shadow_selector": {
            "score_expression": "score_k(w)=a_k^T w",
            "shadow_selected_index": 3,
            "executed_index": 0 if not candidate_index else 3,
            "candidate_tensor_hash": {"sha256": f"abc-{record_index}"},
        },
        "camp_candidate_tensor_provenance": {
            "pre_camp_scoring_tensor": {"sha256": f"abc-{record_index}"},
            "post_camp_selector_tensor": {"sha256": f"abc-{record_index}"},
            "candidate_tensor_mutation_effect": False,
            "pre_post_tensor_hash_equal": True,
            "reference_blend_present": False,
            "outcome_label_input": False,
        },
    }
    if candidate_index:
        record["candidate_closed_loop_outcomes"] = [{"safety_cost_v1": 0.0}] * 8
        record["candidate_index_replay_harness"] = {
            "payload_valid": True,
            "executed_shadow_selected_index": True,
            "closed_loop_outcomes_used_for_training": False,
            "closed_loop_outcomes_used_for_online_selector": False,
            "candidate_tensor_hash": {"sha256": f"abc-{record_index}"},
        }
    return _write_json(path, [record])


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write_sha256s(
    path: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    lines = []
    for file in files:
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        label = file.relative_to(relative_to).as_posix() if relative_to else file.name
        lines.append(f"{digest}  {label}")
    return _write(path, "\n".join(lines) + "\n")


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"
