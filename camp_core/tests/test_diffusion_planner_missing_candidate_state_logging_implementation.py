from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.audit_diffusion_planner_missing_candidate_state_logging_implementation import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_STATUS,
    READY_STATUS,
    TEST_CONTRACTS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.design_diffusion_planner_observable_state_logging import (
    FIELD_SPECS,
)
from scripts.integrations.plan_diffusion_planner_missing_candidate_state_logging_preflight import (
    AUTHORIZED_NEXT_WORK as PREFLIGHT_NEXT_WORK,
    BLOCKED_ACTIONS,
    READY_STATUS as PREFLIGHT_READY_STATUS,
)


def _preflight_report(
    *,
    status: str = PREFLIGHT_READY_STATUS,
    authorized_next_work: str | None = PREFLIGHT_NEXT_WORK,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": status == PREFLIGHT_READY_STATUS,
            "authorized_next_work": authorized_next_work,
            "recommended_first_action": (
                "implement_default_off_logging_unit_gate"
                if status == PREFLIGHT_READY_STATUS
                else None
            ),
            **{key: False for key in BLOCKED_ACTIONS},
        },
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
    }


def _write_replay_source(tmp_path: Path, *, include_payload: bool = True) -> Path:
    source = tmp_path / "run_diffusion_planner_camp_replay.py"
    fields = [field.name for field in FIELD_SPECS]
    latency = [field.latency_bucket for field in FIELD_SPECS]
    payload_block = (
        "\n".join(
            [
                "OBSERVABLE_STATE_LOGGING_SCHEMA_VERSION = 'dp_camp_observable_state_logging_v1'",
                "def _observable_state_logging_payload():",
                "    return {",
                "        \"enabled\": True,",
                "        \"default_off\": True,",
                "        \"selection_effect\": False,",
                "        \"future_outcome_leakage\": False,",
                "        \"candidate_count\": 8,",
                "        \"field_shapes\": {},",
                "        \"finite_checks\": {},",
                "        \"latency_ms\": {},",
                "    }",
                *fields,
                *latency,
                "observable_state_logging_payload = None",
                "observable_state_logging_payload = _observable_state_logging_payload(",
                "if collect_closed_loop_outcomes:",
                "    pass",
                "selection = selector.select(",
                "\"observable_state_logging\": observable_state_logging_payload",
                "camp_observable_state_logging = {",
                "    \"online_selector_change\": False,",
                "    \"classical_benders_claim\": False,",
                "    \"records\": (",
                "}",
                "if args.camp_observable_state_logging:",
                "    pass",
                "\"camp_observable_state_logging\": camp_observable_state_logging",
            ]
        )
        if include_payload
        else ""
    )
    source.write_text(
        "\n".join(
            [
                "parser.add_argument(",
                "    \"--camp_observable_state_logging\",",
                "    action=\"store_true\",",
                "    help=\"Default-off no-leak logging that does not change feasibility, scores, or selection\",",
                ")",
                payload_block,
            ]
        ),
        encoding="utf-8",
    )
    return source


def _write_test_sources(tmp_path: Path, *, drop_contract: str | None = None) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for contract in TEST_CONTRACTS:
        path = tmp_path / f"{contract.path_key}.py"
        tokens = list(contract.required_tokens)
        if contract.name == drop_contract:
            tokens = tokens[:-1]
        path.write_text("\n".join(tokens), encoding="utf-8")
        paths[contract.path_key] = path
    return paths


def test_missing_candidate_state_logging_implementation_gate_ready(
    tmp_path: Path,
) -> None:
    report = build_report(
        preflight_report=_preflight_report(),
        replay_source=_write_replay_source(tmp_path),
        test_sources=_write_test_sources(tmp_path),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["closed_loop_replay_authorized"] is False
    assert decision["tiny_smoke_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]

    markdown = render_markdown(report)
    assert "Implementation Unit Gate" in markdown
    assert "does not run replay" in markdown


def test_missing_candidate_state_logging_implementation_gate_blocks_wrong_source(
    tmp_path: Path,
) -> None:
    report = build_report(
        preflight_report=_preflight_report(
            status="missing_candidate_state_logging_preflight_blocked",
            authorized_next_work=None,
        ),
        replay_source=_write_replay_source(tmp_path),
        test_sources=_write_test_sources(tmp_path),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["source_preflight_gate"]["passed"] is False


def test_missing_candidate_state_logging_implementation_gate_blocks_runtime_gap(
    tmp_path: Path,
) -> None:
    report = build_report(
        preflight_report=_preflight_report(),
        replay_source=_write_replay_source(tmp_path, include_payload=False),
        test_sources=_write_test_sources(tmp_path),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    failed = [check["name"] for check in report["runtime_checks"] if not check["passed"]]
    assert "runtime_payload_contract_tokens" in failed


def test_missing_candidate_state_logging_implementation_gate_blocks_test_gap(
    tmp_path: Path,
) -> None:
    report = build_report(
        preflight_report=_preflight_report(),
        replay_source=_write_replay_source(tmp_path),
        test_sources=_write_test_sources(
            tmp_path,
            drop_contract="payload_coverage_rejects_outcome_leakage",
        ),
    )

    assert report["final_decision"]["status"] == BLOCKED_STATUS
    failed = [
        check["name"] for check in report["test_contract_checks"] if not check["passed"]
    ]
    assert failed == ["payload_coverage_rejects_outcome_leakage"]


def test_missing_candidate_state_logging_implementation_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    preflight_path = tmp_path / "preflight.json"
    output_json = tmp_path / "implementation.json"
    output_md = tmp_path / "implementation.md"
    preflight_path.write_text(json.dumps(_preflight_report()), encoding="utf-8")

    monkeypatch.setattr(
        "scripts.integrations.audit_diffusion_planner_missing_candidate_state_logging_implementation.DEFAULT_TEST_SOURCES",
        _write_test_sources(tmp_path),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "implementation_gate",
            "--preflight_json",
            str(preflight_path),
            "--replay_source",
            str(_write_replay_source(tmp_path)),
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Missing Candidate-State" in output_md.read_text(encoding="utf-8")
