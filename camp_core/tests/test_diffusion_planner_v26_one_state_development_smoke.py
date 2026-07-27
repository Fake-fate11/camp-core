from __future__ import annotations

import copy
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import (
    materialization_phase_receipt_not_available,
)
from camp_core.integrations.diffusion_planner_v26_one_state_development_smoke import (
    EVIDENCE_ROLE,
    SMOKE_ARM,
    build_development_smoke_manifest,
    build_development_smoke_receipt,
    validate_development_smoke_manifest,
    validate_development_smoke_receipt,
)
from camp_core.integrations.diffusion_planner_v26_target_bounded_surface import (
    PRODUCTION_SURFACE_ID,
    build_target_bounded_tick_receipt,
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _manifest() -> dict[str, object]:
    return build_development_smoke_manifest(
        camp_head="a" * 40,
        probe_config_sha256=_sha(1),
        route_sha256=_sha(2),
        scenario_seed=17,
        spawn_config={"scenario_seed": 17},
        fixed_dp_head="b" * 40,
        checkpoint_path="/fixed/model.ckpt",
        checkpoint_sha256=_sha(3),
        args_path="/fixed/args.json",
        args_sha256=_sha(4),
        training_root_sha256=_sha(5),
        training_review_root_sha256=_sha(6),
        atom_scales_sha256=_sha(7),
        static14d_weights_sha256=_sha(8),
    )


def _completed_unit() -> dict[str, object]:
    rows = [_sha(20 + index) for index in range(8)]
    latent_rows = [_sha(40 + index) for index in range(8)]
    return {
        "unit_index": 0,
        "operational_arm": SMOKE_ARM,
        "state_sha256": _sha(9),
        "input": {
            "source_input_sha256": _sha(10),
            "expanded_input_sha256": _sha(11),
            "same_ego_batch_size": 8,
            "nonlatent_rows_identical": True,
            "tensor_metadata": {
                "history": {"shape": [8, 31, 11], "dtype": "torch.float32", "finite": True},
                "sampled_trajectories": {"shape": [8, 321, 81, 4], "dtype": "torch.float32", "finite": True},
            },
        },
        "latent": {
            "seed": 19,
            "shape": [8, 321, 81, 4],
            "dtype": "float32",
            "finite": True,
            "tensor_sha256": _sha(12),
            "row_sha256": latent_rows,
            "row0_zero": True,
        },
        "candidate_pool": {
            "shape": [8, 80, 4],
            "dtype": "float32",
            "finite": True,
            "pool_sha256": _sha(13),
            "row_sha256": rows,
            "candidate0": {"index": 0, "row_sha256": rows[0], "default_output_sha256": rows[0]},
        },
        "forward_calls": {
            "model_call_count_before": 0,
            "model_call_count_after": 1,
            "model_call_delta": 1,
            "primary_forward_count": 1,
            "sequential_forward_count": 0,
            "post_pool_model_forward_count": 0,
            "post_pool_dp_forward_count": 0,
            "post_pool_latent_replacement_count": 0,
            "post_pool_candidate_generation_count": 0,
            "candidate_pool_mutation_count": 0,
            "trajectory_regeneration_count": 0,
        },
        "selection": {"selected_index": 2, "selected_row_sha256": rows[2]},
        "simulator": {"selected_row_sha256": rows[2]},
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
    }


def test_manifest_is_one_nonholdout_static14d_unit_and_rejects_extra_paths() -> None:
    manifest = _manifest()
    assert validate_development_smoke_manifest(manifest) == manifest
    assert manifest["evidence_role"] == EVIDENCE_ROLE
    assert manifest["state_count"] == 1
    assert manifest["operational_arm"] == SMOKE_ARM

    holdout = copy.deepcopy(manifest)
    holdout["state"]["split"] = "holdout"
    holdout["state"]["holdout"] = True
    with pytest.raises(ValueError, match="rejects holdout"):
        validate_development_smoke_manifest(holdout)

    extra_forward = copy.deepcopy(manifest)
    extra_forward["production_surface_manifest"]["execution_options"]["evaluate_all_arms"] = True
    with pytest.raises(ValueError, match="one operational arm"):
        validate_development_smoke_manifest(extra_forward)

    wrong_arm = copy.deepcopy(manifest)
    wrong_arm["operational_arm"] = "Scene14D"
    with pytest.raises(ValueError, match="Static14D"):
        validate_development_smoke_manifest(wrong_arm)


def test_completed_receipt_binds_one_b8_pool_candidate0_and_simulator_row() -> None:
    receipt = build_development_smoke_receipt(
        manifest=_manifest(), unit=_completed_unit()
    )
    assert validate_development_smoke_receipt(receipt) == receipt
    assert receipt["denominator"] == {"planned": 1, "complete": 1, "failed": 0, "unattempted": 0}
    unit = receipt["unit"]
    assert unit["candidate_pool"]["candidate0"]["index"] == 0
    assert unit["forward_calls"]["primary_forward_count"] == 1
    assert unit["forward_calls"]["post_pool_dp_forward_count"] == 0
    assert unit["selection"]["selected_row_sha256"] == unit["simulator"]["selected_row_sha256"]
    assert not {"support", "ood", "stability", "safety", "claim"} & set(receipt)

    bad = copy.deepcopy(receipt)
    bad["unit"]["candidate_pool"]["candidate0"]["default_output_sha256"] = _sha(99)
    with pytest.raises(ValueError, match="default output"):
        validate_development_smoke_receipt(bad)
    bad = copy.deepcopy(receipt)
    bad["unit"]["forward_calls"]["sequential_forward_count"] = 1
    with pytest.raises(ValueError, match="extra or post-pool"):
        validate_development_smoke_receipt(bad)


def test_typed_failure_keeps_one_unit_denominator_without_action_claim() -> None:
    failed = _completed_unit()
    failed["selection"] = None
    failed["simulator"] = None
    failed["terminal"] = {
        "status": "typed_failure",
        "failure_class": "RuntimeError",
        "failure_reason": "selector unavailable",
    }
    failed["forward_calls"]["model_call_count_after"] = 1
    failed["forward_calls"]["model_call_delta"] = 1
    receipt = build_development_smoke_receipt(manifest=_manifest(), unit=failed)
    assert receipt["denominator"] == {"planned": 1, "complete": 0, "failed": 1, "unattempted": 0}
    assert receipt["unit"]["selection"] is None
    assert receipt["unit"]["simulator"] is None


def test_runner_projects_actual_v26_tick_binding_into_one_unit_ledger() -> None:
    rows = [_sha(20 + index) for index in range(8)]
    v26_tick = build_target_bounded_tick_receipt(
        production_surface_id=PRODUCTION_SURFACE_ID,
        options={
            "adaptation_diagnostics": False,
            "sequential_forward_enabled": False,
            "replay_extra_forward_enabled": False,
            "guidance_policy": "disabled",
            "evaluate_all_arms": False,
        },
        operational_arm=SMOKE_ARM,
        tick_index=0,
        state_sha256=_sha(9),
        candidate_pool_sha256_before=_sha(13),
        candidate_pool_sha256_after=_sha(13),
        primary_forward_count=1,
        sequential_forward_count=0,
        zero_call_receipt={
            "dp_or_model_calls_after_pool": 0,
            "latent_replacements_after_pool": 0,
            "candidate_generations_after_pool": 0,
        },
        selector_receipt={
            "status": "ok",
            "selected_index": 2,
            "selected_row_sha256": rows[2],
            "physical_feasible_mask": [True] * 8,
            "source_valid_mask": [True] * 8,
            "margin_best_vs_runner_up": 0.1,
            "exact_tie_set": [2],
        },
        simulator_selected_row_sha256=rows[2],
        materialization_phase_receipt=materialization_phase_receipt_not_available(),
    )
    raw = {
        "v26_production_surface_receipt": v26_tick,
        "candidate_row_sha256": rows,
        "state_sha256": _sha(9),
        "source_input_sha256": _sha(10),
        "input_sha256": _sha(11),
        "latent_seed": 19,
        "latent_shape": [8, 321, 81, 4],
        "latent_dtype": "float32",
        "latent_tensor_sha256": _sha(12),
        "latent_row_sha256": [_sha(40 + index) for index in range(8)],
        "candidate_tensor_sha256_after": _sha(13),
        "default_output_sha256": rows[0],
    }
    raw["same_ego_batch_metadata"] = {
        "same_ego_batch_size": 8,
        "nonlatent_rows_identical": True,
        "tensor_metadata": _completed_unit()["input"]["tensor_metadata"],
    }
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_one_state_development_smoke"
    )
    unit = runner._completed_unit(
        raw,
        SimpleNamespace(
            primary_candidates=[np.zeros((8, 80, 4), dtype=np.float32)],
            model_call_count=1,
        ),
    )
    receipt = build_development_smoke_receipt(manifest=_manifest(), unit=unit)
    assert receipt["unit"]["selection"]["selected_row_sha256"] == rows[2]
    assert receipt["unit"]["simulator"]["selected_row_sha256"] == rows[2]


def test_cli_has_one_explicit_static_arm_and_rejects_legacy_flags() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_one_state_development_smoke"
    )
    args = runner.parse_args(
        [
            "--output-dir", "out",
            "--worker-lock", "worker.lock",
            "--probe-config", "probe.json",
            "--training", "training",
            "--training-root", _sha(1),
            "--training-review", "review",
            "--training-review-root", _sha(2),
            "--fixed-dp-repo", "fixed-dp",
            "--arm", "Static14D",
        ]
    )
    assert args.arm == SMOKE_ARM
    with pytest.raises(SystemExit):
        runner.parse_args(
            [
                "--output-dir", "out",
                "--worker-lock", "worker.lock",
                "--probe-config", "probe.json",
                "--training", "training",
                "--training-root", _sha(1),
                "--training-review", "review",
                "--training-review-root", _sha(2),
                "--fixed-dp-repo", "fixed-dp",
                "--arm", "Static14D",
                "--legacy-preflight",
            ]
        )
    source = Path(runner.__file__).read_text(encoding="utf-8")
    for literal in (
        "max_ticks=1",
        "operational_arm=SMOKE_ARM",
        "evaluate_all_arms=False",
        "adaptation_diagnostics=False",
        "production_surface_id=PRODUCTION_SURFACE_ID",
    ):
        assert literal in source
    assert "preflight(" not in source
    assert "evaluate(" not in source


def test_same_ego_batch_metadata_requires_identical_nonlatent_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResult:
        def __init__(self, value: bool) -> None:
            self.value = value

        def all(self) -> "FakeResult":
            return self

        def item(self) -> bool:
            return self.value

    class FakeTensor:
        def __init__(self, shape: tuple[int, ...], *, rows_equal: bool = True) -> None:
            self.shape = shape
            self.ndim = len(shape)
            self.dtype = "torch.float32"
            self.rows_equal = rows_equal

        def is_floating_point(self) -> bool:
            return True

        def is_complex(self) -> bool:
            return False

        def __getitem__(self, _index: object) -> "FakeTensor":
            return self

        def expand_as(self, _other: "FakeTensor") -> "FakeTensor":
            return self

    class FakeTorch:
        @staticmethod
        def isfinite(_value: FakeTensor) -> FakeResult:
            return FakeResult(True)

        @staticmethod
        def equal(value: FakeTensor, _other: FakeTensor) -> bool:
            return value.rows_equal

    monkeypatch.setitem(sys.modules, "torch", FakeTorch())
    fair = importlib.import_module(
        "scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout"
    )
    metadata = fair._same_ego_batch_metadata(
        {
            "history": FakeTensor((8, 31, 11)),
            "sampled_trajectories": FakeTensor((8, 2)),
        }
    )
    assert metadata["same_ego_batch_size"] == 8
    assert metadata["nonlatent_rows_identical"] is True
    assert metadata["tensor_metadata"]["history"]["finite"] is True

    with pytest.raises(ValueError, match="nonlatent input rows drifted"):
        fair._same_ego_batch_metadata(
            {
                "history": FakeTensor((8, 31, 11), rows_equal=False),
                "sampled_trajectories": FakeTensor((8, 2)),
            }
        )
