from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_calibration_corpus import (
    project_candidate0_calibration_corpus_from_paired_terminals,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration import (
    build_paired_calibration_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)


ROOT = Path(__file__).resolve().parents[2]
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def _module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BRIDGE = _module(
    "scripts/integrations/freeze_diffusion_planner_v25_calibration_from_paired.py",
    "v25_calibration_from_paired_bridge",
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode()
    )


def _native(identity: dict, unit: dict) -> dict:
    ordinal = unit["unit_ordinal"]
    ticks = []
    for tick_index in range(64):
        input_sha = f"{ordinal * 1000 + tick_index + 1:064x}"
        candidate_sha = f"{ordinal * 1000 + tick_index + 101:064x}"
        ticks.append(
            {
                "tick_index": tick_index,
                "selected_index": 0,
                "input_sha256": input_sha,
                "default_output_sha256": (
                    f"{ordinal * 1000 + tick_index + 201:064x}"
                ),
                "candidate_tensor_sha256_before": candidate_sha,
                "candidate_tensor_sha256_after": candidate_sha,
                "pre_decision_speed_mps": 8.0,
                "safety": {"speed_mps": 7.9 if tick_index == 0 else 8.0},
            }
        )
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "arm": "dp",
        "fixed_dp_head": FIXED_DP_HEAD,
        "claim_authorized": False,
        "route_name": identity["route_identity_sha256"],
        "route_sha256": identity["route_identity_sha256"],
        "scenario_seed": unit["seed"],
        "spawn_config_sha256": f"{ordinal + 10000:064x}",
        "initial_state_sha256": f"{ordinal + 20000:064x}",
        "initial_input_sha256": ticks[0]["input_sha256"],
        "ticks": ticks,
        "secondary": {
            "route_progress_m": 100.0 + ordinal,
            "route_completion_rate": 0.9,
            "mean_abs_jerk_mps3": 0.5,
            "max_jerk_mps3": 1.0,
            "mean_abs_lateral_acceleration_mps2": 0.2,
            "max_abs_lateral_acceleration_mps2": 0.5,
        },
    }


def _materialize(tmp_path: Path) -> tuple[dict, dict, Path]:
    base = build_signal_complete_execution_plan("calibration")
    paired = build_paired_calibration_execution_plan(base)
    identities = {
        row["scenario_identity_sha256"]: row for row in paired["identities"]
    }
    raw = tmp_path / "raw"
    for unit in paired["execution_units"]:
        order = unit["ordered_arms"].index("candidate0_operational_default")
        ordinal = unit["unit_ordinal"] * 3 + order
        identity = identities[unit["scenario_identity_sha256"]]
        terminal = {
            "run_ordinal": ordinal,
            "unit_ordinal": unit["unit_ordinal"],
            "unit_sha256": unit["unit_sha256"],
            "arm_order_index": order,
            "plan_arm": "candidate0_operational_default",
            "scenario_identity_sha256": unit["scenario_identity_sha256"],
            "route_identity_sha256": identity["route_identity_sha256"],
            "seed": unit["seed"],
            "status": "complete",
            "native_receipt": _native(identity, unit),
            "failure_receipt": None,
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        }
        relative = (
            f"runs/{ordinal:04d}_{unit['unit_ordinal']:04d}_{order}_"
            "candidate0_operational_default/terminal.json"
        )
        _write(raw / relative, terminal)
    return base, paired, raw


def test_streamed_bridge_proves_no_exact_candidate0_repeats(tmp_path: Path) -> None:
    base, paired, raw = _materialize(tmp_path)
    terminals, receipt_rows = BRIDGE._stream_candidate0_terminals(raw, paired)
    result = project_candidate0_calibration_corpus_from_paired_terminals(
        calibration_plan=base,
        paired_plan=paired,
        candidate0_terminals=terminals,
    )
    assert len(receipt_rows) == 100
    assert all(row["size_bytes"] < BRIDGE.MAX_TERMINAL_FILE_BYTES for row in receipt_rows)
    assert all(
        row["sha256"]
        == hashlib.sha256((raw / row["relative_path"]).read_bytes()).hexdigest()
        for row in receipt_rows
    )
    assert result["heterogeneity_diagnostic_cluster_count"] == 5
    assert result["exact_duplicate_repeatability_group_count"] == 0
    assert len(
        {
            row["repeatability_identity_sha256"]
            for row in result["candidate0_rows"]
        }
    ) == 100


def test_streamed_bridge_rejects_noncanonical_or_oversize_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, paired, raw = _materialize(tmp_path)
    unit = paired["execution_units"][0]
    order = unit["ordered_arms"].index("candidate0_operational_default")
    ordinal = unit["unit_ordinal"] * 3 + order
    target = raw / (
        f"runs/{ordinal:04d}_{unit['unit_ordinal']:04d}_{order}_"
        "candidate0_operational_default/terminal.json"
    )
    value = json.loads(target.read_text(encoding="utf-8"))
    target.write_text(json.dumps(value, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="not canonical"):
        terminals, _ = BRIDGE._stream_candidate0_terminals(raw, paired)
        list(terminals)
    _write(target, value)
    monkeypatch.setattr(BRIDGE, "MAX_TERMINAL_FILE_BYTES", 8)
    with pytest.raises(ValueError, match="memory ceiling"):
        terminals, _ = BRIDGE._stream_candidate0_terminals(raw, paired)
        list(terminals)


def test_streamed_bridge_rejects_candidate0_terminal_pairing_drift(
    tmp_path: Path,
) -> None:
    base, paired, raw = _materialize(tmp_path)
    terminal_stream, _ = BRIDGE._stream_candidate0_terminals(raw, paired)
    terminals = list(terminal_stream)
    terminals[0]["run_ordinal"] += 1
    with pytest.raises(ValueError, match="authority drifted"):
        project_candidate0_calibration_corpus_from_paired_terminals(
            calibration_plan=base,
            paired_plan=paired,
            candidate0_terminals=terminals,
        )
