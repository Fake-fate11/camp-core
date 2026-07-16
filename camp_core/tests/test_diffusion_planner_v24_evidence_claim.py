from __future__ import annotations

import copy
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_v24_evidence_claim.py"
)
SPEC = importlib.util.spec_from_file_location("v24_evidence_claim", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


REVIEW_HEAD = "aff69dfcae3d3dcde79b9c46912493767f9208f2"
EXECUTION_HEAD = "8caa2699b3657154f464e14c2f274190d3036c4a"
PACKAGE_HEAD = "1" * 40
STATIC_PREFLIGHT_HEAD = "a" * 40
CONFIG_SHA = "2" * 64
EVALUATOR_SHA = "3" * 64


@pytest.fixture(autouse=True)
def _isolated_live_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    camp = (tmp_path / "camp").resolve()
    dp = (tmp_path / "dp").resolve()
    state = (tmp_path / "holdout_once_state.json").resolve()
    lock = tmp_path / "paired.global.lock"
    lock.write_text("", encoding="ascii")
    monkeypatch.setattr(module, "CANONICAL_CAMP_REPO", camp)
    monkeypatch.setattr(module, "CANONICAL_DP_REPO", dp)
    monkeypatch.setattr(module, "CANONICAL_OUTPUT_PARENT", tmp_path.resolve())
    monkeypatch.setattr(module, "CANONICAL_HOLDOUT_STATE_PATH", state)
    monkeypatch.setattr(module, "GLOBAL_LOCK_PATH", lock.resolve())
    monkeypatch.setattr(module, "_active_v24_processes", lambda: [])
    monkeypatch.setattr(module, "_git_is_ancestor", lambda *_args: True)
    monkeypatch.setattr(module, "_git_bytes", _fake_git_bytes)
    monkeypatch.setattr(module, "_fsync_tree", lambda _path: None)
    monkeypatch.setattr(module, "_fsync_directory", lambda _path: None)

    @contextlib.contextmanager
    def fake_lock(_path: Path):
        yield

    def fake_rename(source: Path, destination: Path) -> None:
        if Path(destination).exists():
            raise FileExistsError(destination)
        os.rename(source, destination)

    monkeypatch.setattr(module, "_exclusive_global_lock", fake_lock)
    monkeypatch.setattr(module, "_rename_noreplace", fake_rename)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(
            value,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _source_guards() -> dict[str, bool]:
    return {
        name: name != "independent_review_passed"
        for name in module.EVIDENCE_GUARD_NAMES
    }


def _summary(
    pair_count: int,
    *,
    mean: float = 0.0,
    median: float = 0.0,
    low: float = 0.0,
    high: float = 0.0,
    better: int = 0,
    tie: int | None = None,
    worse: int = 0,
    direction: str | None = None,
) -> dict[str, object]:
    result = {
        "pair_count": pair_count,
        "mean": mean,
        "median": median,
        "ci95_low": low,
        "ci95_high": high,
        "better_tie_worse": {
            "better": better,
            "tie": pair_count - better - worse if tie is None else tie,
            "worse": worse,
        },
    }
    if direction is not None:
        result["direction"] = direction
        result["descriptive_unclassified_count"] = 0
    return result


def _latency_distribution() -> dict[str, object]:
    return {
        "count": 7680,
        "mean": 1.0,
        "median": 1.0,
        "p95": 1.0,
        "p99": 1.0,
        "max": 1.0,
    }


def _metrics(*, ci95_high: float = module.EXPECTED_CI95_HIGH) -> dict[str, object]:
    guards = _source_guards()
    gates = {
        "retention_rate": True,
        "paired_complete_rate": True,
        "source_invalid_rate": True,
        "execution_invalid_rate": True,
        "safety_cost_mean_delta_below_zero": True,
        "clustered_ci95_upper_below_zero": ci95_high < 0.0,
        "better_exceeds_worse": True,
        "no_additional_collision_pairs": True,
        "no_additional_offroad_pairs": True,
        "no_additional_red_light_pairs": True,
        "no_additional_wrong_way_pairs": True,
        "evidence_guards": False,
    }
    failed = [name for name in module.CLAIM_GATE_NAMES if not gates[name]]
    overall = _summary(
        120,
        mean=module.EXPECTED_MEAN_DELTA,
        low=module.EXPECTED_CI95_LOW,
        high=ci95_high,
        better=4,
        tie=113,
        worse=3,
    )
    return {
        "schema": "camp_dp_v24_holdout_main_independent_statistics_v1",
        "bootstrap_contract": {
            "primary_hierarchy": [
                "corridor_group_sha256",
                "route_identity_sha256",
                "seed",
            ],
            "map_family_cluster_level_authorized": False,
            "resamples": 5000,
            "seed": 24047,
        },
        "coverage": {
            "planned_pair_count": 120,
            "retained_pair_count": 120,
            "paired_complete_count": 120,
            "source_invalid_pair_count": 0,
            "execution_invalid_pair_count": 0,
            "retention_rate": 1.0,
            "paired_complete_rate": 1.0,
            "source_invalid_rate": 0.0,
            "execution_invalid_rate": 0.0,
        },
        "failure_accounting": {
            "dp_status": {"ok": 120},
            "camp_status": {"ok": 120},
            "failure_class": {"None": 120},
            "failed_pairs_dropped": False,
            "replacement_or_resampling_used": False,
        },
        "safety_cost_delta": overall,
        "strata": {
            "overall": copy.deepcopy(overall),
            "all_k_high_risk": _summary(8, better=2, tie=4, worse=2),
        },
        "components": {
            name: _summary(120) for name in module.SAFETY_COMPONENT_NAMES
        },
        "speed_sensitivity": {
            name: _summary(120) for name in module.SPEED_SENSITIVITY_NAMES
        },
        "secondary": {
            name: _summary(
                120,
                direction=(
                    None
                    if direction == "lower_is_better"
                    else direction
                ),
            )
            for name, direction in module.SECONDARY_DIRECTIONS.items()
        },
        "additional_event_pairs": {
            name: 0 for name in module.MAJOR_EVENT_FIELDS
        },
        "candidate_selection": {
            "camp_tick_count": 7680,
            "candidate0_selection_count": 1401,
            "non_candidate0_selection_count": 6279,
            "all_k_high_risk_pair_count": 8,
            "all_k_high_risk_tick_count": 36,
            "camp_selected_index_histogram": {
                "0": 1401,
                "1": 6279,
                "2": 0,
                "3": 0,
                "4": 0,
                "5": 0,
                "6": 0,
                "7": 0,
            },
        },
        "latency": {
            arm: {
                stage: _latency_distribution()
                for stage in stages
            }
            for arm, stages in module.LATENCY_STAGE_NAMES.items()
        },
        "latency_comparison_authorized": False,
        "latency_reporting_role": "descriptive_instrumented_only",
        "evidence_guards": guards,
        "claim_gate_result": {
            "decision": "honest_no_claim",
            "final_claim_authorized": False,
            "claim_scope": (
                "frozen_held_out_map_family_and_three_corridor_groups_only"
            ),
            "map_family_level_ci": False,
            "unseen_map_generalization": False,
            "native_ranked_k8_superiority": False,
            "latency_comparative_conclusion": False,
            "gates": gates,
            "failed_gates": failed,
        },
    }


def _schedule() -> dict[str, object]:
    return {
        "pair_count": 120,
        "unique_pair_count": 120,
        "route_count": 24,
        "seed_count_per_route": 5,
        "seeds": [24201, 24202, 24203, 24204, 24205],
        "map_family_count": 1,
        "corridor_group_count": 3,
        "arm_order_counts": {"dp_camp": 60, "camp_dp": 60},
        "arm_order_domain_separator": "camp-v24-paired-arm-order-v1",
        "deterministic_hash_rank_verified": True,
        "outcome_blind_preregistered_order_control_verified": True,
        "independent_reset_per_arm_verified": True,
        "latency_comparative_conclusion_authorized": False,
    }


def _provenance() -> dict[str, object]:
    return {
        "live_camp_head": REVIEW_HEAD,
        "execution_source_head": EXECUTION_HEAD,
        "execution_source_is_ancestor": True,
        "prior_gate_heads_are_execution_source_ancestors": {},
        "live_camp_tracked_clean": True,
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "fixed_dp_tracked_clean": True,
        "producer_blob_sha256": {},
        "config_blob_sha256": CONFIG_SHA,
        "expected_config_sha256": CONFIG_SHA,
        "evaluator_blob_sha256": EVALUATOR_SHA,
        "expected_evaluator_sha256": EVALUATOR_SHA,
    }


def _source_roots() -> dict[str, object]:
    return {
        name: {
            "label": name,
            "root": f"/sealed/{name}",
            "root_sha256": _sha(name),
            "file_count": 1,
            "manifest_paths": [f"{name}.json"],
        }
        for name in module.EXPECTED_SOURCE_ROOT_NAMES
    }


def _review_result(metrics: dict[str, object]) -> dict[str, object]:
    schedule = _schedule()
    provenance = _provenance()
    return {
        "schema": module.REVIEW_SCHEMA,
        "status": "passed",
        "check_count": module.EXPECTED_REVIEW_CHECK_COUNT,
        "failed_count": 0,
        "failed_checks": [],
        "checks": {name: True for name in module.EXPECTED_REVIEW_CHECK_NAMES},
        "source_roots": _source_roots(),
        "schedule": schedule,
        "execution": {
            "planned_pair_count": 120,
            "retained_pair_count": 120,
            "paired_complete_count": 120,
            "source_invalid_pair_count": 0,
            "execution_failure_pair_count": 0,
            "dp_tick_count": 7680,
            "camp_tick_count": 7680,
            "all_k_high_risk_tick_count": 36,
        },
        "holdout_state": {
            "schema": "camp_dp_v24_holdout_once_state_v1",
            "holdout_opened": True,
            "holdout_open_count": 1,
            "rerun_authorized": False,
            "camp_head": EXECUTION_HEAD,
            "authorization_root_sha256": "8" * 64,
            "preflight_root_sha256": "9" * 64,
            "output_dir": "/sealed/holdout-main-once",
        },
        "provenance": provenance,
        "evidence_limitations": {
            "raw_candidate_tensor_bytes_present": False,
            "raw_atom_matrix_bytes_present": False,
            "affine_score_receipt_consistency_verified": True,
            "affine_scores_recomputed_from_raw_atoms": False,
            "candidate_hashes_recomputed_from_raw_tensor_bytes": False,
            "candidate_and_atom_hash_scope": (
                "complete_sealed_receipt_consistency_only"
            ),
            "raw_byte_proof_claimed": False,
        },
        "claim_guard_handoff": {
            "independent_review_passed": False,
            "status": (
                "pending_separate_claim_decision_rehash_of_sealed_reviewer_root"
            ),
            "reviewer_self_authorization_forbidden": True,
        },
        "frozen_metric_contract": {
            "train_route_seed_source_coverage_disclosure": copy.deepcopy(
                module.EXPECTED_TRAIN_SOURCE_COVERAGE
            ),
            "learning_curve_stability": copy.deepcopy(
                module.EXPECTED_LEARNING_CURVE_STABILITY
            ),
            "distribution_concentration_risk_disclosed": True,
            "calibration_or_holdout_repair_authorized": False,
        },
        "metrics": metrics,
        "camp_head": REVIEW_HEAD,
        "execution_source_head": EXECUTION_HEAD,
        "preflight_camp_head": "4" * 40,
        "preflight_config_sha256": "5" * 64,
        "pilot_review_camp_head": "6" * 40,
        "pilot_execution_source_head": "7" * 40,
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "source_execution_reexecuted": False,
        "runner_built": False,
        "model_loaded": False,
        "simulator_executed": False,
        "holdout_reopened": False,
        "holdout_open_count": 1,
        "latency_comparison_authorized": False,
        "map_family_level_ci_authorized": False,
        "unseen_map_generalization_authorized": False,
        "native_ranked_k8_claim_authorized": False,
        "final_claim_authorized": False,
    }


def _write_review_artifact(root: Path) -> tuple[Path, str]:
    if root.name == "review":
        root = root.with_name(f"{module.REVIEW_NAME_PREFIX}test")
    root.mkdir()
    metrics = _metrics()
    result = _review_result(metrics)
    _write_json(root / "review_result.json", result)
    _write_json(root / "recomputed_metrics.json", metrics)
    _write_json(root / "schedule_receipt.json", result["schedule"])
    _write_json(root / "provenance.json", result["provenance"])
    (root / "summary.md").write_text("# sealed review\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD={REVIEW_HEAD}\n"
        f"EXECUTION_SOURCE_HEAD={EXECUTION_HEAD}\n"
        f"PREFLIGHT_CAMP_HEAD={'4' * 40}\n"
        f"PILOT_REVIEW_CAMP_HEAD={'6' * 40}\n"
        f"PILOT_EXECUTION_SOURCE_HEAD={'7' * 40}\n"
        f"FIXED_DP_HEAD={module.FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (root / "COMMAND.txt").write_text("review\n", encoding="utf-8")
    (root / "stdout.txt").write_text("{}\n", encoding="utf-8")
    (root / "stderr.txt").write_bytes(b"")
    (root / "run.exit").write_bytes(b"0\n")
    return root, module._seal_artifact(root)


def _reseal(root: Path) -> str:
    return module._seal_artifact(root)


def _fake_git(repo: Path, *args: str) -> str:
    repo = Path(repo).resolve()
    if args == ("rev-parse", "--show-toplevel"):
        return str(repo)
    if args == ("rev-parse", "HEAD"):
        return PACKAGE_HEAD if Path(repo).name == "camp" else module.FIXED_DP_HEAD
    if args == ("rev-parse", "origin/main"):
        if Path(repo).name != "camp":
            raise AssertionError((repo, args))
        return PACKAGE_HEAD
    if args == ("symbolic-ref", "--short", "HEAD"):
        return "main"
    if args == ("remote", "get-url", "origin"):
        return module.CANONICAL_ORIGIN_URL
    if args == ("ls-remote", "origin", "refs/heads/main"):
        return f"{PACKAGE_HEAD}\trefs/heads/main"
    if len(args) == 3 and args[:2] == ("cat-file", "-t"):
        return "commit"
    if args == ("status", "--porcelain", "--untracked-files=no"):
        return ""
    raise AssertionError((repo, args))


def _fake_git_bytes(repo: Path, object_name: str) -> bytes:
    _head, separator, relative = object_name.partition(":")
    if not separator:
        raise AssertionError(object_name)
    return (Path(repo) / Path(relative)).read_bytes()


def _build_kwargs(tmp_path: Path, review_root: Path, review_sha: str) -> dict:
    camp = tmp_path / "camp"
    dp = tmp_path / "dp"
    camp.mkdir(exist_ok=True)
    dp.mkdir(exist_ok=True)
    docs = camp / "docs"
    docs.mkdir(exist_ok=True)
    review = _load(review_root / "review_result.json")
    state_path = module.CANONICAL_HOLDOUT_STATE_PATH
    _write_json(state_path, review["holdout_state"])
    state_sha = hashlib.sha256(state_path.read_bytes()).hexdigest()
    static_preflight = (
        tmp_path / f"{module.STATIC_PREFLIGHT_NAME_PREFIX}test"
    ).resolve()
    static_preflight.mkdir()
    (static_preflight / "static_preflight.json").write_bytes(b"{}\n")
    (static_preflight / "stderr.txt").write_bytes(b"")
    (static_preflight / "run.exit").write_bytes(b"0\n")
    static_preflight_sha = module._seal_artifact(static_preflight)
    authority = {
        "current_v24_status": module.AUTHORIZED_CURRENT_STATUS,
        "current_v24_artifact_source_head": STATIC_PREFLIGHT_HEAD,
        "current_v24_final_synced_head": (
            "pending_current_docs_commit_not_source_drift"
        ),
        "current_v24_artifact": static_preflight.as_posix(),
        "current_v24_artifact_root_sha256": static_preflight_sha,
        "current_v24_reviewer_artifact": review_root.resolve().as_posix(),
        "current_v24_reviewer_artifact_root_sha256": review_sha,
        "current_v24_reviewer_source_head": REVIEW_HEAD,
        "current_v24_holdout_state": state_path.resolve().as_posix(),
        "current_v24_holdout_state_sha256": state_sha,
        "current_v24_holdout_open_count": "1",
        "current_v24_holdout_rerun_authorized": "false",
        "source_a_status": (
            "source_ineligible_missing_authorized_build_prerequisites"
        ),
        "source_a_terminal": "true",
        "source_b_status": module.AUTHORIZED_SOURCE_B_STATUS,
        "source_b_terminal": "false",
        "authorized_source_count": "2",
        "source_terminal_count": "1",
        "global_stop_authorized": "false",
        "global_stop_reason": "none",
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "next_work_target": module.AUTHORIZED_NEXT_WORK_TARGET,
    }
    receipt = "".join(f"{key}={value}\n" for key, value in authority.items())
    (docs / "diffusion_planner_v24_iteration_audit.md").write_text(
        "# v24 audit\n\n" + receipt,
        encoding="utf-8",
    )
    (docs / "diffusion_planner_current_status.md").write_text(
        "# status\n\n## Current V24 Status\n\n"
        + receipt
        + "\n## Current V23 Status\n\nold\n",
        encoding="utf-8",
    )
    return {
        "review_root": review_root,
        "expected_review_root_sha256": review_sha,
        "expected_review_camp_head": REVIEW_HEAD,
        "expected_execution_source_head": EXECUTION_HEAD,
        "expected_config_sha256": CONFIG_SHA,
        "expected_evaluator_sha256": EVALUATOR_SHA,
        "camp_repo": camp,
        "package_camp_head": PACKAGE_HEAD,
        "dp_repo": dp,
        "output_dir": module._expected_output_path(PACKAGE_HEAD, review_sha),
        "enable_evidence_claim": True,
        "command": ["python", "build-evidence-claim"],
        "minimum_free_bytes": 0,
    }


def _replace_authority_field(
    camp: Path, key: str, value: str, *, audit: bool = True, status: bool = True
) -> None:
    names = []
    if audit:
        names.append("diffusion_planner_v24_iteration_audit.md")
    if status:
        names.append("diffusion_planner_current_status.md")
    for name in names:
        path = camp / "docs" / name
        text = path.read_text(encoding="utf-8")
        text, count = re.subn(
            rf"(?m)^{re.escape(key)}=.*$",
            f"{key}={value}",
            text,
        )
        assert count == 1
        path.write_text(text, encoding="utf-8")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_rehashes_source_closes_only_self_guard_and_seals_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    source_before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in review_root.iterdir()
        if path.is_file()
    }
    monkeypatch.setattr(module, "_git_text", _fake_git)

    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    result = module.build_evidence_claim(**kwargs)

    output = Path(kwargs["output_dir"])
    assert result["status"] == "passed"
    assert result["decision"] == "honest_no_claim"
    assert result["final_claim_authorized"] is False
    assert result["final_post_publication_checks_passed"] is True
    assert result["free_bytes_after_gate"] > 0
    assert output.is_dir()
    assert not output.with_name(output.name + ".tmp").exists()
    assert module.verify_complete_seal(output, result["root_sha256"])
    evidence = _load(output / "evidence_package.json")
    claim = _load(output / "claim_decision.json")
    source = _load(review_root / "review_result.json")
    assert source["claim_guard_handoff"]["independent_review_passed"] is False
    assert source["metrics"]["evidence_guards"]["independent_review_passed"] is False
    assert claim["derived_evidence_guards"]["independent_review_passed"] is True
    assert all(claim["derived_evidence_guards"].values())
    assert claim["failed_gates"] == ["clustered_ci95_upper_below_zero"]
    assert claim["decision"] == "honest_no_claim"
    assert claim["final_claim_authorized"] is False
    assert evidence["reviewer_root"]["source_bytes_unchanged"] is True
    assert evidence["transitive_source_roots_rehashed_by_this_gate"] is False
    assert evidence["repository_provenance"]["camp_origin_main"] == PACKAGE_HEAD
    assert evidence["repository_provenance"]["camp_remote_main"] == PACKAGE_HEAD
    assert (
        evidence["repository_provenance"]["static_preflight_source_head"]
        == STATIC_PREFLIGHT_HEAD
        != PACKAGE_HEAD
    )
    assert evidence["live_authority"]["static_preflight"]["root_sha256"] == (
        evidence["live_authority"]["fields"][
            "current_v24_artifact_root_sha256"
        ]
    )
    assert evidence["live_authority"]["verified_before_and_after"] is True
    assert evidence["live_holdout_once"] == {
        "path": module.CANONICAL_HOLDOUT_STATE_PATH.as_posix(),
        "sha256": evidence["live_authority"]["fields"][
            "current_v24_holdout_state_sha256"
        ],
        "open_count": 1,
        "rerun_authorized": False,
        "marker_bytes_unchanged_before_and_after": True,
        "global_lock_exclusively_held_by_this_gate": True,
        "active_evaluator_or_reviewer_process_count": 0,
    }
    assert evidence["latency_comparison_authorized"] is False
    assert evidence["latency_reporting_role"] == "descriptive_instrumented_only"
    assert evidence["final_post_publication_checks_required"] is True
    assert (
        evidence["free_bytes_after_gate_recorded_in_return_and_launch_receipt"]
        is True
    )
    assert evidence["reviewed_metrics"] == source["metrics"]
    assert evidence["evaluation_summary"] == {
        "planned_pair_count": 120,
        "retained_pair_count": 120,
        "paired_complete_count": 120,
        "source_invalid_pair_count": 0,
        "execution_failure_pair_count": 0,
        "dp_tick_count": 7680,
        "camp_tick_count": 7680,
        "candidate0_selection_count": 1401,
        "non_candidate0_selection_count": 6279,
        "all_k_high_risk_pair_count": 8,
        "all_k_high_risk_tick_count": 36,
        "map_family_count": 1,
        "corridor_group_count": 3,
    }
    assert evidence["frozen_training_risk_disclosure"] == source[
        "frozen_metric_contract"
    ]
    assert set(evidence["source_root_inventory"]) == set(
        module.EXPECTED_SOURCE_ROOT_NAMES
    )
    source_after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in review_root.iterdir()
        if path.is_file()
    }
    assert source_after == source_before
    with pytest.raises(FileExistsError):
        module.build_evidence_claim(**kwargs)


def test_pure_claim_evaluator_can_pass_all_gates_without_hard_coding() -> None:
    metrics = _metrics(ci95_high=-0.001)

    result = module.evaluate_claim_gates(metrics)

    assert result["decision"] == "limited_claim_gates_passed"
    assert result["final_claim_authorized"] is True
    assert result["failed_gates"] == []
    assert all(result["gates"].values())
    assert metrics["evidence_guards"]["independent_review_passed"] is False


@pytest.mark.parametrize(
    "mutation",
    (
        "docs_disagree",
        "control_field_disagree",
        "unauthorized_target",
        "global_stop",
        "reviewer_root",
        "marker_sha",
        "static_root",
    ),
)
def test_live_authority_tampering_fails_before_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    camp = Path(kwargs["camp_repo"])
    if mutation == "docs_disagree":
        _replace_authority_field(
            camp,
            "next_work_target",
            "v24_wrong_gate",
            status=False,
        )
    elif mutation == "control_field_disagree":
        _replace_authority_field(
            camp,
            "source_b_terminal",
            "true",
            status=False,
        )
    elif mutation == "unauthorized_target":
        _replace_authority_field(camp, "next_work_target", "v24_wrong_gate")
    elif mutation == "global_stop":
        _replace_authority_field(camp, "global_stop_authorized", "true")
    elif mutation == "reviewer_root":
        _replace_authority_field(
            camp,
            "current_v24_reviewer_artifact_root_sha256",
            "a" * 64,
        )
    elif mutation == "marker_sha":
        _replace_authority_field(
            camp,
            "current_v24_holdout_state_sha256",
            "b" * 64,
        )
    elif mutation == "static_root":
        _replace_authority_field(
            camp,
            "current_v24_artifact_root_sha256",
            "c" * 64,
        )
    monkeypatch.setattr(module, "_git_text", _fake_git)

    with pytest.raises(ValueError):
        module.build_evidence_claim(**kwargs)

    assert not Path(kwargs["output_dir"]).exists()


def test_live_authority_must_match_tracked_package_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    camp = Path(kwargs["camp_repo"])
    tracked = {
        path.as_posix(): (camp / path).read_bytes()
        for path in (
            module.AUDIT_RELATIVE_PATH,
            module.CURRENT_STATUS_RELATIVE_PATH,
        )
    }
    _replace_authority_field(
        camp,
        "next_work_target",
        "v24_wrong_gate",
        audit=False,
    )

    def tracked_git_bytes(_repo: Path, object_name: str) -> bytes:
        _head, _separator, relative = object_name.partition(":")
        return tracked[relative]

    monkeypatch.setattr(module, "_git_text", _fake_git)
    monkeypatch.setattr(module, "_git_bytes", tracked_git_bytes)

    with pytest.raises(ValueError, match="differ from package CAMP HEAD"):
        module.build_evidence_claim(**kwargs)


def test_verified_byte_read_closes_seal_to_json_toctou(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    monkeypatch.setattr(module, "_git_text", _fake_git)
    original = module._read_verified_sealed_bytes
    changed = False

    def race(seal: dict, relative: str) -> bytes:
        nonlocal changed
        if relative == "review_result.json" and not changed:
            changed = True
            path = review_root / relative
            path.write_bytes(path.read_bytes() + b" ")
        return original(seal, relative)

    monkeypatch.setattr(module, "_read_verified_sealed_bytes", race)

    with pytest.raises(ValueError, match="changed before verified read"):
        module.build_evidence_claim(**kwargs)

    assert not Path(kwargs["output_dir"]).exists()


def test_live_marker_and_process_are_reverified_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    monkeypatch.setattr(module, "_git_text", _fake_git)
    original = module._verify_live_holdout_state
    calls = 0

    def changing_marker(authority: dict, review_state: dict) -> dict:
        nonlocal calls
        calls += 1
        if calls == 2:
            module.CANONICAL_HOLDOUT_STATE_PATH.write_bytes(b"{}\n")
        return original(authority, review_state)

    monkeypatch.setattr(module, "_verify_live_holdout_state", changing_marker)
    with pytest.raises(ValueError, match="marker SHA256"):
        module.build_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()

    _write_json(
        module.CANONICAL_HOLDOUT_STATE_PATH,
        _load(review_root / "review_result.json")["holdout_state"],
    )
    calls = 0

    def process_probe() -> list[int]:
        nonlocal calls
        calls += 1
        return [] if calls == 1 else [12345]

    monkeypatch.setattr(module, "_verify_live_holdout_state", original)
    monkeypatch.setattr(module, "_active_v24_processes", process_probe)
    with pytest.raises(ValueError, match="process started"):
        module.build_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()


@pytest.mark.parametrize(
    "mutation",
    (
        "status",
        "check",
        "metrics_mismatch",
        "self_guard_true",
        "other_guard_false",
        "handoff",
        "failed_coverage",
        "major_event",
        "config_pin",
        "scope_execution",
        "holdout_state",
        "train_coverage",
        "learning_curve",
        "source_root_path",
        "source_root_manifest_duplicate",
        "source_root_label",
        "check_name",
        "full_metric_scope",
        "all_high_stratum",
        "latency_scope",
        "failure_histogram",
        "claim_scope",
        "arm_order",
    ),
)
def test_semantic_tampering_fails_before_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    review_root, _ = _write_review_artifact(tmp_path / "review")
    review = _load(review_root / "review_result.json")
    metrics = _load(review_root / "recomputed_metrics.json")
    provenance = _load(review_root / "provenance.json")
    schedule = _load(review_root / "schedule_receipt.json")
    if mutation == "status":
        review["status"] = "failed"
    elif mutation == "check":
        review["checks"][sorted(module.EXPECTED_REVIEW_CHECK_NAMES)[0]] = False
    elif mutation == "metrics_mismatch":
        review["metrics"]["coverage"]["retained_pair_count"] = 119
    elif mutation == "self_guard_true":
        metrics["evidence_guards"]["independent_review_passed"] = True
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "other_guard_false":
        metrics["evidence_guards"]["artifact_sha_verified"] = False
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "handoff":
        review["claim_guard_handoff"]["status"] = "passed"
    elif mutation == "failed_coverage":
        metrics["coverage"]["paired_complete_count"] = 119
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "major_event":
        metrics["additional_event_pairs"]["collision_any"] = 1
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "config_pin":
        provenance["config_blob_sha256"] = _sha("wrong-config")
        provenance["expected_config_sha256"] = _sha("wrong-config")
        review["provenance"] = copy.deepcopy(provenance)
    elif mutation == "scope_execution":
        review["simulator_executed"] = True
    elif mutation == "holdout_state":
        review["holdout_state"]["holdout_open_count"] = 2
    elif mutation == "train_coverage":
        review["frozen_metric_contract"][
            "train_route_seed_source_coverage_disclosure"
        ]["failed"] = 820
    elif mutation == "learning_curve":
        review["frozen_metric_contract"]["learning_curve_stability"][
            "full_effective_support_indices"
        ] = [7, 8]
    elif mutation == "source_root_path":
        first = sorted(module.EXPECTED_SOURCE_ROOT_NAMES)[0]
        review["source_roots"][first]["manifest_paths"] = ["../escape.json"]
    elif mutation == "source_root_manifest_duplicate":
        first = sorted(module.EXPECTED_SOURCE_ROOT_NAMES)[0]
        path = review["source_roots"][first]["manifest_paths"][0]
        review["source_roots"][first]["manifest_paths"] = [path, path]
    elif mutation == "source_root_label":
        first = sorted(module.EXPECTED_SOURCE_ROOT_NAMES)[0]
        review["source_roots"][first]["label"] = "wrong"
    elif mutation == "check_name":
        first = sorted(review["checks"])[0]
        review["checks"]["invented_check"] = review["checks"].pop(first)
    elif mutation == "full_metric_scope":
        metrics["components"].pop(sorted(module.SAFETY_COMPONENT_NAMES)[0])
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "all_high_stratum":
        metrics["strata"]["all_k_high_risk"]["pair_count"] = 7
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "latency_scope":
        metrics["latency"]["camp"]["total"]["count"] = 7679
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "failure_histogram":
        metrics["failure_accounting"]["dp_status"] = {"ok": 119}
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "claim_scope":
        metrics["claim_gate_result"]["unseen_map_generalization"] = True
        review["metrics"] = copy.deepcopy(metrics)
    elif mutation == "arm_order":
        schedule["arm_order_counts"] = {"dp_camp": 120, "camp_dp": 0}
        review["schedule"] = copy.deepcopy(schedule)
    _write_json(review_root / "review_result.json", review)
    _write_json(review_root / "recomputed_metrics.json", metrics)
    _write_json(review_root / "provenance.json", provenance)
    _write_json(review_root / "schedule_receipt.json", schedule)
    review_sha = _reseal(review_root)
    monkeypatch.setattr(module, "_git_text", _fake_git)
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)

    with pytest.raises(ValueError):
        module.build_evidence_claim(**kwargs)

    assert not Path(kwargs["output_dir"]).exists()
    assert not Path(str(kwargs["output_dir"]) + ".tmp").exists()


def test_nonfinite_json_is_rejected_before_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, _ = _write_review_artifact(tmp_path / "review")
    metrics_path = review_root / "recomputed_metrics.json"
    review_path = review_root / "review_result.json"
    metrics_path.write_text(
        metrics_path.read_text(encoding="utf-8").replace(
            '"ci95_high":0.01953125', '"ci95_high":1e999'
        ),
        encoding="utf-8",
    )
    review_path.write_text(
        review_path.read_text(encoding="utf-8").replace(
            '"ci95_high":0.01953125', '"ci95_high":1e999'
        ),
        encoding="utf-8",
    )
    review_sha = _reseal(review_root)
    monkeypatch.setattr(module, "_git_text", _fake_git)
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)

    with pytest.raises(ValueError, match="non-finite"):
        module.build_evidence_claim(**kwargs)

    assert not Path(kwargs["output_dir"]).exists()


@pytest.mark.parametrize("mutation", ("file", "extra", "root", "run_exit", "stderr", "heads"))
def test_seal_and_receipt_tampering_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    expected = review_sha
    if mutation == "file":
        (review_root / "summary.md").write_text("tampered\n", encoding="utf-8")
    elif mutation == "extra":
        (review_root / "extra.txt").write_text("extra\n", encoding="utf-8")
    elif mutation == "root":
        expected = _sha("wrong-root")
    elif mutation == "run_exit":
        (review_root / "run.exit").write_text("1\n", encoding="ascii")
        expected = _reseal(review_root)
    elif mutation == "stderr":
        (review_root / "stderr.txt").write_text("error\n", encoding="utf-8")
        expected = _reseal(review_root)
    elif mutation == "heads":
        text = (review_root / "HEADS.txt").read_text(encoding="ascii")
        (review_root / "HEADS.txt").write_text(
            text.replace(REVIEW_HEAD, "8" * 40), encoding="ascii"
        )
        expected = _reseal(review_root)
    monkeypatch.setattr(module, "_git_text", _fake_git)
    kwargs = _build_kwargs(tmp_path, review_root, expected)

    with pytest.raises(ValueError):
        module.build_evidence_claim(**kwargs)

    assert not Path(kwargs["output_dir"]).exists()
    assert not Path(str(kwargs["output_dir"]) + ".tmp").exists()


def test_symlink_in_sealed_source_is_rejected_when_supported(tmp_path: Path) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    link = review_root / "link.txt"
    try:
        os.symlink(review_root / "summary.md", link)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(ValueError, match="symlink"):
        module.verify_complete_seal(review_root, review_sha)


def test_manifest_hash_and_parse_use_one_byte_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    manifest = (review_root / "SHA256SUMS").resolve()
    original = Path.read_bytes
    reads = 0

    def counted(path: Path) -> bytes:
        nonlocal reads
        if Path(path).resolve() == manifest:
            reads += 1
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", counted)

    module.verify_complete_seal(review_root, review_sha)

    assert reads == 1


def test_atomic_staging_is_removed_when_output_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    monkeypatch.setattr(module, "_git_text", _fake_git)
    original = module._write_json

    def fail_evidence(path: Path, value: object) -> None:
        if Path(path).name == "evidence_package.json":
            raise RuntimeError("write-sentinel")
        original(path, value)

    monkeypatch.setattr(module, "_write_json", fail_evidence)
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)

    with pytest.raises(RuntimeError, match="write-sentinel"):
        module.build_evidence_claim(**kwargs)

    assert not Path(kwargs["output_dir"]).exists()
    assert not Path(str(kwargs["output_dir"]) + ".tmp").exists()


def test_repo_identity_remote_and_ancestry_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)

    def wrong_origin(repo: Path, *args: str) -> str:
        if args == ("remote", "get-url", "origin"):
            return "https://github.com/example/wrong.git"
        return _fake_git(repo, *args)

    monkeypatch.setattr(module, "_git_text", wrong_origin)
    with pytest.raises(ValueError, match="branch/origin/remote"):
        module.build_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()

    monkeypatch.setattr(module, "_git_text", _fake_git)
    monkeypatch.setattr(module, "_git_is_ancestor", lambda *_args: False)
    with pytest.raises(ValueError, match="ancestry"):
        module.build_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()

    def only_static_is_not_ancestor(
        _repo: Path, ancestor: str, _descendant: str
    ) -> bool:
        return ancestor != STATIC_PREFLIGHT_HEAD

    monkeypatch.setattr(module, "_git_is_ancestor", only_static_is_not_ancestor)
    with pytest.raises(ValueError, match="static-preflight source"):
        module.build_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()


def test_held_global_lock_blocks_gate_before_source_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)

    @contextlib.contextmanager
    def held_lock(_path: Path):
        raise ValueError("v24 global lock is already held")
        yield

    monkeypatch.setattr(module, "_exclusive_global_lock", held_lock)
    with pytest.raises(ValueError, match="already held"):
        module.build_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()


def test_atomic_noreplace_preserves_racer_and_final_path_is_reverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    output = Path(kwargs["output_dir"])
    staging = output.with_name(output.name + ".tmp")
    monkeypatch.setattr(module, "_git_text", _fake_git)

    def race_destination(_source: Path, destination: Path) -> None:
        destination.mkdir()
        (destination / "racer.txt").write_text("preserve\n", encoding="utf-8")
        raise FileExistsError(destination)

    monkeypatch.setattr(module, "_rename_noreplace", race_destination)
    with pytest.raises(FileExistsError):
        module.build_evidence_claim(**kwargs)
    assert (output / "racer.txt").read_text(encoding="utf-8") == "preserve\n"
    assert not staging.exists()

    shutil.rmtree(output)

    def tamper_after_rename(source: Path, destination: Path) -> None:
        os.rename(source, destination)
        with (destination / "summary.md").open("ab") as handle:
            handle.write(b"tamper")

    monkeypatch.setattr(module, "_rename_noreplace", tamper_after_rename)
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        module.build_evidence_claim(**kwargs)
    assert not output.exists()
    assert not staging.exists()


def test_success_path_fsyncs_tree_and_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    monkeypatch.setattr(module, "_git_text", _fake_git)
    calls: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        module, "_fsync_tree", lambda path: calls.append(("tree", Path(path)))
    )
    monkeypatch.setattr(
        module,
        "_fsync_directory",
        lambda path: calls.append(("directory", Path(path))),
    )

    module.build_evidence_claim(**kwargs)

    output = Path(kwargs["output_dir"])
    assert calls == [
        ("tree", output.with_name(output.name + ".tmp")),
        ("directory", output.parent),
    ]


def test_disk_floor_and_live_repo_drift_fail_before_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    kwargs["minimum_free_bytes"] = module.MINIMUM_FREE_BYTES
    monkeypatch.setattr(module, "_git_text", _fake_git)
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=module.MINIMUM_FREE_BYTES),
    )
    with pytest.raises(ValueError, match="10 GiB"):
        module.build_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()

    def dirty_git(repo: Path, *args: str) -> str:
        if Path(repo).name == "camp" and args[0] == "status":
            return " M tracked.py"
        return _fake_git(repo, *args)

    monkeypatch.setattr(module, "_git_text", dirty_git)
    monkeypatch.setattr(
        module.shutil, "disk_usage", lambda _path: SimpleNamespace(free=2**50)
    )
    with pytest.raises(ValueError, match="live CAMP"):
        module.build_evidence_claim(**kwargs)
    assert not Path(kwargs["output_dir"]).exists()


def test_post_publication_rechecks_remove_gate_output_on_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    kwargs["minimum_free_bytes"] = module.MINIMUM_FREE_BYTES
    output = Path(kwargs["output_dir"])
    monkeypatch.setattr(module, "_git_text", _fake_git)
    disk_calls = 0

    def disk_usage(_path: Path) -> SimpleNamespace:
        nonlocal disk_calls
        disk_calls += 1
        free = 2**50 if disk_calls == 1 else module.MINIMUM_FREE_BYTES
        return SimpleNamespace(free=free)

    monkeypatch.setattr(module.shutil, "disk_usage", disk_usage)
    with pytest.raises(ValueError, match="post-publication.*10 GiB"):
        module.build_evidence_claim(**kwargs)
    assert not output.exists()
    assert not output.with_name(output.name + ".tmp").exists()

    monkeypatch.setattr(
        module.shutil, "disk_usage", lambda _path: SimpleNamespace(free=2**50)
    )

    def mutate_reviewer_after_publish(source: Path, destination: Path) -> None:
        os.rename(source, destination)
        with (review_root / "summary.md").open("ab") as handle:
            handle.write(b"source-drift")

    monkeypatch.setattr(
        module, "_rename_noreplace", mutate_reviewer_after_publish
    )
    with pytest.raises(ValueError):
        module.build_evidence_claim(**kwargs)
    assert not output.exists()
    assert not output.with_name(output.name + ".tmp").exists()


def test_cli_requires_explicit_switch_and_pin_domains(tmp_path: Path) -> None:
    required = [
        "--review-root",
        str(tmp_path / "review"),
        "--expected-review-root-sha256",
        "a" * 64,
        "--expected-review-camp-head",
        "b" * 40,
        "--expected-execution-source-head",
        "c" * 40,
        "--expected-config-sha256",
        "d" * 64,
        "--expected-evaluator-sha256",
        "e" * 64,
        "--camp-repo",
        str(tmp_path / "camp"),
        "--package-camp-head",
        "f" * 40,
        "--dp-repo",
        str(tmp_path / "dp"),
        "--output-dir",
        str(tmp_path / "output"),
    ]
    assert module.parse_args(required).enable_evidence_claim is False
    assert (
        module.parse_args(required + ["--enable-evidence-claim"]).enable_evidence_claim
        is True
    )
    with pytest.raises(ValueError, match="enable-evidence-claim"):
        module.main(required)
    with pytest.raises(ValueError, match="64-character"):
        module.build_evidence_claim(
            review_root=tmp_path / "review",
            expected_review_root_sha256="a" * 40,
            expected_review_camp_head="b" * 40,
            expected_execution_source_head="c" * 40,
            expected_config_sha256="d" * 64,
            expected_evaluator_sha256="e" * 64,
            camp_repo=tmp_path / "camp",
            package_camp_head="f" * 40,
            dp_repo=tmp_path / "dp",
            output_dir=tmp_path / "output",
            enable_evidence_claim=True,
        )
    with pytest.raises(ValueError, match="40-character"):
        module.build_evidence_claim(
            review_root=tmp_path / "review",
            expected_review_root_sha256="a" * 64,
            expected_review_camp_head="b" * 64,
            expected_execution_source_head="c" * 40,
            expected_config_sha256="d" * 64,
            expected_evaluator_sha256="e" * 64,
            camp_repo=tmp_path / "camp",
            package_camp_head="f" * 40,
            dp_repo=tmp_path / "dp",
            output_dir=tmp_path / "output",
            enable_evidence_claim=True,
        )


def test_output_must_be_disjoint_and_implementation_is_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    review_root, review_sha = _write_review_artifact(tmp_path / "review")
    monkeypatch.setattr(module, "_git_text", _fake_git)
    kwargs = _build_kwargs(tmp_path, review_root, review_sha)
    kwargs["output_dir"] = review_root / f"{module.OUTPUT_NAME_PREFIX}nested"
    with pytest.raises(ValueError):
        module.build_evidence_claim(**kwargs)
    source = SCRIPT.read_text(encoding="utf-8")
    assert "from scripts.integrations.review_diffusion_planner" not in source
    assert "from scripts.integrations.evaluate_diffusion_planner" not in source
    assert "from camp_core.evaluation.diffusion_planner_v24_statistics" not in source
