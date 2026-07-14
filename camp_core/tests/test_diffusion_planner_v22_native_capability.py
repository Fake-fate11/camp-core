import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "diffusion_planner_v22_native_capability.json"


def _runner():
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    return run_diffusion_planner_dp_camp_v21_native


def _config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_v22_capability_config_is_diagnostic_and_not_holdout() -> None:
    module = _runner()
    config = _config()

    module.validate_v22_capability_config(config)

    assert config["selector"]["selection_policy"] == "v22_source_valid"
    assert config["selector"]["role"] == "v18_ablation_capability_only"
    assert config["protocol"]["safety_schema"] == "safety_cost_native_v22"
    assert config["protocol"]["tiny_steps"] == 4
    assert config["protocol"]["route_role"] == (
        "diagnostic_v21_observed_not_holdout"
    )
    assert config["protocol"]["claim_authorized"] is False
    assert config["protocol"]["training_authorized"] is False
    assert config["protocol"]["holdout_access_authorized"] is False
    assert config["seeds"]["formal_forbidden"] == [11, 12, 13]


def test_v22_capability_normalization_preserves_v21_frozen_base() -> None:
    module = _runner()
    config = _config()
    before = json.loads(json.dumps(config))

    normalized = module._v21_compatible_capability_config(config)

    module.validate_smoke_config(normalized)
    assert config == before
    assert normalized["schema_version"] == "camp_dp_v21_native_smoke_v1"
    assert normalized["protocol"]["safety_schema"] == "safety_cost_native_v1"
    assert "selection_policy" not in normalized["selector"]


def test_existing_native_runner_reads_v22_selection_policy() -> None:
    module = _runner()
    config = _config()

    assert module._selection_policy(config) == "v22_source_valid"


def test_v22_capability_preflight_writes_no_execution_receipt(tmp_path) -> None:
    module = _runner()
    config = _config()
    output = tmp_path / "preflight"

    result = module.execute_smoke(
        config,
        output,
        mode="preflight",
        run_arm=None,
        verified_assets={"fixed_dp_head": config["fixed_dp"]["head"]},
        command="v22 capability preflight unit test",
    )

    assert result["status"] == "passed"
    assert result["mode"] == "preflight"
    assert result["arm_count"] == 0
    assert result["route_count"] == 0
    assert result["claim_authorized"] is False
    assert result["preflight"]["config_valid"] is True
    assert not (output / "receipts").exists()
