from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact


ROOT = Path(__file__).resolve().parents[2]


def _module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRODUCER = _module(
    "scripts/integrations/run_diffusion_planner_v25_power_pilot.py",
    "v25_power_pilot_producer",
)
REVIEWER = _module(
    "scripts/integrations/review_diffusion_planner_v25_power_pilot.py",
    "v25_power_pilot_reviewer",
)
FIXTURES = _module(
    "camp_core/tests/test_diffusion_planner_v25_power_pilot.py",
    "v25_power_pilot_fixtures",
)


def _write(path: Path, value: object) -> None:
    path.write_bytes(
        (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    )


def _inputs(tmp_path: Path) -> tuple[Path, str, Path, str, Path, str]:
    plan_payload, results = FIXTURES._results()
    plan = tmp_path / "plan"
    plan.mkdir()
    _write(plan / "execution_plan.json", plan_payload)
    _write(
        plan / "report.json",
        {
            "status": "passed_signal_complete_plan_materialization",
            "split": "calibration",
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        },
    )
    (plan / "run.exit").write_bytes(b"0\n")
    plan_root = seal_artifact(plan, label="test calibration plan")

    calibration = tmp_path / "calibration"
    calibration.mkdir()
    _write(calibration / "run_results.json", results)
    _write(
        calibration / "report.json",
        {
            "status": "passed_candidate0_calibration_execution",
            "input_roots": {"plan_root_sha256": plan_root},
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        },
    )
    (calibration / "run.exit").write_bytes(b"0\n")
    calibration_root = seal_artifact(calibration, label="test candidate0 calibration")

    review = tmp_path / "calibration_review"
    review.mkdir()
    _write(
        review / "report.json",
        {
            "status": "passed_independent_candidate0_calibration_execution_review",
            "reviewed_root_sha256": calibration_root,
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        },
    )
    (review / "run.exit").write_bytes(b"0\n")
    review_root = seal_artifact(review, label="test candidate0 calibration review")
    return calibration, calibration_root, review, review_root, plan, plan_root


def test_power_pilot_artifact_and_independent_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calibration, calibration_root, review, review_root, plan, plan_root = _inputs(
        tmp_path
    )
    monkeypatch.setattr(PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(PRODUCER, "_git_head", lambda: "b" * 40)
    artifact = tmp_path / "power"
    root = PRODUCER.build(
        calibration_artifact=calibration,
        calibration_root_sha256=calibration_root,
        calibration_review_artifact=review,
        calibration_review_root_sha256=review_root,
        plan_artifact=plan,
        plan_root_sha256=plan_root,
        output_dir=artifact,
    )
    report = REVIEWER.review(artifact, root)
    assert report["status"] == "passed_independent_candidate0_power_pilot_review"
    assert report["row_count"] == 100
    assert report["total_independent_cluster_count"] >= 2
    assert report["red_independent_cluster_count"] >= 2
    assert report["fresh_b2_opened"] is False


def test_power_pilot_rejects_unreviewed_calibration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calibration, calibration_root, review, _review_root, plan, plan_root = _inputs(
        tmp_path
    )
    monkeypatch.setattr(PRODUCER, "_tracked_dirty", lambda: False)
    output = tmp_path / "power"
    with pytest.raises(ValueError):
        PRODUCER.build(
            calibration_artifact=calibration,
            calibration_root_sha256=calibration_root,
            calibration_review_artifact=review,
            calibration_review_root_sha256="f" * 64,
            plan_artifact=plan,
            plan_root_sha256=plan_root,
            output_dir=output,
        )
    assert not output.exists()
