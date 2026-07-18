from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (
    CRITICAL_IMPLEMENTATION_PATHS,
)
from scripts.integrations import (
    preflight_diffusion_planner_v25_a16_r06_route_signal_source as producer,
)
from scripts.integrations import (
    review_diffusion_planner_v25_a16_r06_route_signal_source as reviewer,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sealed(tmp_path: Path, names: frozenset[str]) -> tuple[Path, str]:
    root = tmp_path / ("artifact_" + hashlib.sha256("|".join(sorted(names)).encode()).hexdigest()[:8])
    root.mkdir()
    for name in names:
        (root / name).write_text(f"{name}\n", encoding="utf-8")
    return root, seal_artifact(root, label="A1.6.1 inventory fixture")


@pytest.mark.parametrize(
    "expected",
    [reviewer.SOURCE_PAYLOAD_PATHS, reviewer.REVIEW_PAYLOAD_PATHS],
    ids=["source", "review"],
)
@pytest.mark.parametrize("mutation", ["extra", "missing", "renamed"])
def test_payload_inventory_is_exact_not_merely_self_consistent(
    tmp_path: Path, expected: frozenset[str], mutation: str
) -> None:
    names = set(expected)
    if mutation == "extra":
        names.add("future_schedule.json")
    elif mutation == "missing":
        names.remove(sorted(names)[0])
    else:
        names.remove("report.json")
        names.add("report-renamed.json")
    root, digest = _sealed(tmp_path, frozenset(names))
    with pytest.raises(ValueError, match="exact payload inventory"):
        reviewer._verify_exact_payload_inventory(
            root,
            digest,
            expected_paths=expected,
            label="fixture",
        )


def test_source_and_review_exact_inventory_positive(tmp_path: Path) -> None:
    for expected in (reviewer.SOURCE_PAYLOAD_PATHS, reviewer.REVIEW_PAYLOAD_PATHS):
        root, digest = _sealed(tmp_path, expected)
        receipt = reviewer._verify_exact_payload_inventory(
            root, digest, expected_paths=expected, label="fixture"
        )
        assert frozenset(receipt["manifest_paths"]) == expected
        assert receipt["file_count"] == len(expected)


def test_consumed_marker_rejects_copy_alias_symlink_and_field_drift(
    tmp_path: Path,
) -> None:
    expected_payload = {
        "gate": "preflight",
        "nonce": "5" * 64,
        "authorized_output_dir": "/root/autodl-tmp/exact-output",
    }
    canonical = tmp_path / "canonical.consumed.json"
    canonical.write_text(
        json.dumps(expected_payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    expected_sha = _sha(canonical)
    assert producer._validate_consumed_marker(
        canonical,
        expected_path=canonical,
        expected_sha256=expected_sha,
        expected_payload=expected_payload,
    )["nonce"] == "5" * 64

    copied = tmp_path / "copied.consumed.json"
    copied.write_bytes(canonical.read_bytes())
    with pytest.raises(ValueError, match="canonical path"):
        producer._validate_consumed_marker(
            copied,
            expected_path=canonical,
            expected_sha256=expected_sha,
            expected_payload=expected_payload,
        )
    linked = tmp_path / "linked.consumed.json"
    try:
        linked.symlink_to(canonical)
    except OSError:
        pass
    else:
        with pytest.raises(ValueError, match="symlink"):
            producer._validate_consumed_marker(
                linked,
                expected_path=linked,
                expected_sha256=expected_sha,
                expected_payload=expected_payload,
            )
    drifted = dict(expected_payload, gate="execute")
    canonical.write_text(
        json.dumps(drifted, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        producer._validate_consumed_marker(
            canonical,
            expected_path=canonical,
            expected_sha256=_sha(canonical),
            expected_payload=expected_payload,
        )
    for key, value in (
        ("gate", 0),
        ("nonce", 5),
        ("authorized_output_dir", False),
    ):
        invalid = dict(expected_payload)
        invalid[key] = value
        canonical.write_text(
            json.dumps(invalid, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="schema/value/type"):
            producer._validate_consumed_marker(
                canonical,
                expected_path=canonical,
                expected_sha256=_sha(canonical),
                expected_payload=expected_payload,
            )


def _git_fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "dp"
    module_path = repo / "scenario_generation" / "traffic_light.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text("class TrafficLightController:\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Codex", "-c", "user.email=codex@example.invalid",
            "commit", "-qm", "fixture",
        ],
        cwd=repo,
        check=True,
    )
    return repo, module_path


def test_imported_dp_module_must_be_tracked_bytes_from_fixed_commit(
    tmp_path: Path,
) -> None:
    repo, module_path = _git_fixture(tmp_path)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    receipt = producer._verify_imported_dp_module(
        repo=repo,
        fixed_head=head,
        module=SimpleNamespace(__file__=str(module_path)),
        relative_path="scenario_generation/traffic_light.py",
    )
    assert receipt["relative_path"] == "scenario_generation/traffic_light.py"
    assert receipt["sha256"] == _sha(module_path)

    shadow = tmp_path / "shadow" / "scenario_generation" / "traffic_light.py"
    shadow.parent.mkdir(parents=True)
    shadow.write_bytes(module_path.read_bytes())
    with pytest.raises(ValueError, match="outside canonical fixed-DP repo"):
        producer._verify_imported_dp_module(
            repo=repo,
            fixed_head=head,
            module=SimpleNamespace(__file__=str(shadow)),
            relative_path="scenario_generation/traffic_light.py",
        )
    module_path.write_text("# uncommitted shadow\n", encoding="utf-8")
    with pytest.raises(ValueError, match="git object"):
        producer._verify_imported_dp_module(
            repo=repo,
            fixed_head=head,
            module=SimpleNamespace(__file__=str(module_path)),
            relative_path="scenario_generation/traffic_light.py",
        )


def test_a161_critical_manifest_covers_adapter_producer_and_both_reviewers() -> None:
    assert {
        "camp_core/camp_core/integrations/diffusion_planner_v25_controlled_scenarios.py",
        "scripts/integrations/preflight_diffusion_planner_v25_a16_r06_route_signal_source.py",
        "scripts/integrations/review_diffusion_planner_v25_a16_r06_route_signal_source.py",
        "scripts/integrations/run_diffusion_planner_v25_controlled_training_corpus.py",
        "scripts/integrations/review_diffusion_planner_v25_controlled_training_corpus.py",
    }.issubset(CRITICAL_IMPLEMENTATION_PATHS)


def test_bounded_coverage_design_is_outcome_blind_deterministic_and_capped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for module in (producer, reviewer):
        monkeypatch.setattr(module, "EXPECTED_EXECUTABLE", 4)
        monkeypatch.setattr(module, "EXPECTED_EXECUTABLE_MAPPED", 2)
    cases = []
    rows = []
    for index, source_class in enumerate(
        ["mapped_signal", "mapped_signal", "no_signal", "no_signal"]
    ):
        scenario_id = f"{index + 1:064x}"
        case = {
            "scenario_id": scenario_id,
            "runner_eligible": True,
            "family": "lead_vehicle_hard_brake",
            "semantic_variant": "lead_vehicle_hard_brake",
            "tier": "easy",
            "source_map_sha256": "a" * 64,
            "route_identity_sha256": f"{index + 10:064x}",
            "corridor_group_sha256": ("b" if index != 3 else "c") * 64,
        }
        row = {
            "scenario_id": scenario_id,
            "source_class": source_class,
            "source_chain": {"semantic_clone_sha256": f"{index + 20:064x}"},
            "id_free_tensor_layout": {"layout_sha256": "d" * 64},
        }
        cases.append(case)
        rows.append(row)

    produced = producer._bounded_coverage_design(cases, rows)
    independently_reviewed = reviewer._oracle_bounded_coverage_design(cases, rows)
    assert produced == independently_reviewed
    assert produced["mapped_selected_count"] == 2
    assert produced["selected_identity_count"] == 4
    assert produced["k8_executed"] is False
    assert produced["outcome_fields_consumed"] == []
    assert produced["tie_break_fields"] == [
        "semantic_clone_sha256",
        "route_identity_sha256",
        "scenario_id",
    ]
    forbidden_mutation = copy.deepcopy(cases)
    forbidden_mutation[0].update(
        outcome="collision", score=-999.0, atom_margin=999.0, selected_index=7
    )
    assert producer._bounded_coverage_design(forbidden_mutation, rows) == produced

    for module in (producer, reviewer):
        monkeypatch.setattr(module, "BOUNDED_COVERAGE_MAX_IDENTITIES", 3)
    with pytest.raises(ValueError, match="hard cap"):
        producer._bounded_coverage_design(cases, rows)
    with pytest.raises(ValueError, match="hard cap"):
        reviewer._oracle_bounded_coverage_design(cases, rows)
