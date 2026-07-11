from __future__ import annotations

import importlib

import pytest


def _auditor():
    try:
        return importlib.import_module(
            "scripts.integrations.audit_diffusion_planner_v19_safety_evidence_gap"
        )
    except ModuleNotFoundError:
        pytest.fail("the v19 safety-evidence-gap auditor is missing")


def _write_source(root, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_read_only_audit_preserves_claims_and_fails_closed_without_simulator(
    tmp_path,
) -> None:
    module = _auditor()
    camp_repo = tmp_path / "camp"
    dp_repo = tmp_path / "dp"
    nuplan_root = tmp_path / "nuplan"
    camp_repo.mkdir()
    _write_source(
        dp_repo,
        "diffusion_planner/diffusion_planner/model/module/decoder.py",
        'return {"prediction": x0, "turn_indicator_logit": turn_indicator_logit}\n',
    )
    _write_source(
        dp_repo,
        "scenario_generation/tensor_converter.py",
        'data_torch["sampled_trajectories"] = torch.zeros((1, 1, 1, 4))\n',
    )
    _write_source(
        dp_repo,
        "scenario_generation/simulate.py",
        'preds = {agent_ids[0]: outputs["prediction"][0, 0].cpu().numpy()}\n',
    )
    _write_source(
        dp_repo,
        "diffusion_planner_ros/diffusion_planner_ros/diffusion_planner_node.py",
        'self.batch_size = self.declare_parameter("batch_size", value=1).value\n'
        "curr_pred = pred[b, 0]\n"
        "if b == 0:\n"
        "    self.pub_trajectory.publish(planning_trajectory)\n",
    )
    (nuplan_root / "data" / "cache" / "mini").mkdir(parents=True)
    (nuplan_root / "data" / "cache" / "mini" / "one.db").write_bytes(b"db")

    report = module.build_report(
        camp_repo=camp_repo,
        dp_repo=dp_repo,
        nuplan_data_root=nuplan_root,
        camp_head="a" * 40,
        dp_head=module.FIXED_DP_HEAD,
        nuplan_devkit_available=False,
        official_nuplan_simulator_available=False,
    )

    assert report["claim_taxonomy"] == {
        "performance_claim": "no_claim",
        "bounded_offline_safety_proxy_improvement": "supported",
        "closed_loop_safety_claim": "not_yet_supported",
        "broad_CAMP_over_native_DP_Top1_claim": "not_supported",
    }
    provenance = report["native_baseline_provenance"]
    assert provenance["baseline_name"] == "DP-default deterministic/MAP baseline"
    assert provenance["native_ranked_top1"] is False
    assert provenance["candidate0_is_native_top1"] is False
    assert provenance["native_inference_source_contracts_passed"] is True
    assert all(len(item["sha256"]) == 64 for item in provenance["source_files"])
    assert report["nuplan_capability"]["database_count"] == 1
    assert report["nuplan_capability"]["fixed_dp_nuplan_reference_files"] == []
    assert (
        report["nuplan_capability"]["fixed_dp_nuplan_closed_loop_adapter_present"]
        is False
    )
    assert report["gates"]["matched_closed_loop_execution_ready"] is False
    assert report["gates"]["closed_loop_claim_authorized"] is False
    assert report["gates"]["broad_native_top1_claim_authorized"] is False
    assert report["data_access"]["holdout_labels_read"] == 0


def test_cli_writes_json_and_markdown_without_executing_simulator(tmp_path) -> None:
    module = _auditor()
    camp_repo = tmp_path / "camp"
    dp_repo = tmp_path / "dp"
    nuplan_root = tmp_path / "nuplan"
    camp_repo.mkdir()
    _write_source(
        dp_repo,
        "diffusion_planner/diffusion_planner/model/module/decoder.py",
        'return {"prediction": x0}\n',
    )
    _write_source(
        dp_repo,
        "scenario_generation/tensor_converter.py",
        'data_torch["sampled_trajectories"] = torch.zeros((1, 1, 1, 4))\n',
    )
    _write_source(
        dp_repo,
        "scenario_generation/simulate.py",
        'x = outputs["prediction"][0, 0]\n',
    )
    _write_source(
        dp_repo,
        "diffusion_planner_ros/diffusion_planner_ros/diffusion_planner_node.py",
        'self.batch_size = self.declare_parameter("batch_size", value=1).value\n'
        "curr_pred = pred[b, 0]\n"
        "if b == 0:\n"
        "    publish()\n",
    )
    nuplan_root.mkdir()
    output_json = tmp_path / "audit.json"
    output_md = tmp_path / "audit.md"

    exit_code = module.main(
        [
            "--camp_repo",
            str(camp_repo),
            "--dp_repo",
            str(dp_repo),
            "--nuplan_data_root",
            str(nuplan_root),
            "--camp_head",
            "a" * 40,
            "--dp_head",
            module.FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    assert '"simulator_executed": false' in output_json.read_text(encoding="utf-8")
    markdown = output_md.read_text(encoding="utf-8")
    assert "DP-default deterministic/MAP baseline" in markdown
    assert "Matched closed-loop execution ready: `False`" in markdown
