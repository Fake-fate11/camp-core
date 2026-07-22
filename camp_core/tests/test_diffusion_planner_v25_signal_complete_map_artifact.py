from __future__ import annotations

import hashlib
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
    "scripts/integrations/materialize_diffusion_planner_v25_signal_complete_maps.py",
    "v25_signal_map_producer",
)
REVIEWER = _module(
    "scripts/integrations/review_diffusion_planner_v25_signal_complete_maps.py",
    "v25_signal_map_reviewer",
)


@pytest.mark.parametrize(
    ("split", "maps", "routes"),
    (("calibration", 5, 50), ("fresh_b2", 25, 100)),
)
def test_signal_complete_map_artifact_and_independent_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, split: str, maps: int, routes: int
) -> None:
    monkeypatch.setattr(PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(PRODUCER, "_git_head", lambda: "a" * 40)
    artifact = tmp_path / f"{split}_maps"
    root = PRODUCER.build(split=split, output_dir=artifact)
    report = REVIEWER.review(artifact, root)
    assert report["status"] == "passed_independent_signal_complete_map_review"
    assert report["map_count"] == maps
    assert report["corridor_count"] == routes
    assert report["route_count"] == routes
    assert report["all_regulatory_chains_recomputed"] is True
    assert report["source_independent_geometry_clone_count"] == 0
    assert report["fresh_b2_opened"] is False


def test_resealed_future_schedule_mutation_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(PRODUCER, "_git_head", lambda: "b" * 40)
    artifact = tmp_path / "maps"
    PRODUCER.build(split="calibration", output_dir=artifact)
    suite_path = artifact / "signal_complete_suite.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    suite["maps"][0]["routes"][0]["future_phase_schedule_consumed"] = True
    suite_path.write_bytes(
        (json.dumps(suite, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
    )
    report_path = artifact / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["suite_sha256"] = hashlib.sha256(suite_path.read_bytes()).hexdigest()
    report_path.write_bytes(
        (json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
    )
    root = seal_artifact(artifact, label="mutated signal maps")
    with pytest.raises(ValueError, match="runtime-source"):
        REVIEWER.review(artifact, root)


def test_resealed_extra_payload_is_rejected_by_exact_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(PRODUCER, "_tracked_dirty", lambda: False)
    monkeypatch.setattr(PRODUCER, "_git_head", lambda: "c" * 40)
    artifact = tmp_path / "maps"
    PRODUCER.build(split="calibration", output_dir=artifact)
    (artifact / "future.json").write_text("{}\n", encoding="utf-8")
    root = seal_artifact(artifact, label="mutated signal maps")
    with pytest.raises(ValueError, match="inventory"):
        REVIEWER.review(artifact, root)
