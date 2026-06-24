from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path


MODULE = (
    "scripts.integrations."
    "review_diffusion_planner_guarded_material_v3_post_implementation_static_contract"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
## 2026-06-24 - Failure-attribution remediation guarded fixed-snapshot screen rerun failure attribution remediation implementation only

Gate:
`{target.IMPLEMENTATION_GATE}`

status={target.IMPLEMENTATION_GATE.replace("_only", "_complete")}
passed=True
failed_checks=[]
authorized_next_work={target.CURRENT_GATE}
fixed_snapshot_screen_rerun_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
added_default_off_profile={target.MATERIAL_PROFILE_V3}
added_generator_policy={target.MATERIAL_POLICY_V3}

Next admissible gate:

`{target.CURRENT_GATE}`.
"""


def _read_current(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    source_text: str | None = None,
    route_test_text: str | None = None,
    contract_test_text: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    audit = tmp_path / "audit.md"
    source = tmp_path / "source.py"
    route_test = tmp_path / "test_route.py"
    contract_test = tmp_path / "test_contract.py"
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    source.write_text(
        source_text if source_text is not None else _read_current(target.DEFAULT_SOURCE_PATH),
        encoding="utf-8",
    )
    route_test.write_text(
        route_test_text
        if route_test_text is not None
        else _read_current(target.DEFAULT_ROUTE_TEST_PATH),
        encoding="utf-8",
    )
    contract_test.write_text(
        contract_test_text
        if contract_test_text is not None
        else _read_current(target.DEFAULT_CONTRACT_TEST_PATH),
        encoding="utf-8",
    )
    return audit, source, route_test, contract_test


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    source_text: str | None = None,
    route_test_text: str | None = None,
    contract_test_text: str | None = None,
    dp_head: str = target.EXPECTED_DP_HEAD,
) -> dict:
    audit, source, route_test, contract_test = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        source_text=source_text,
        route_test_text=route_test_text,
        contract_test_text=contract_test_text,
    )
    return target.build_report(
        audit_path=audit,
        source_path=source,
        route_test_path=route_test,
        contract_test_path=contract_test,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_guarded_material_v3_post_static_review_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["post_implementation_static_contract_review"]

    assert decision["status"] == target.READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_plan_authorized"] is True
    assert review["source_contract"]["contracts"]["explicit_v3_profile_policy_pair"]
    assert review["source_contract"]["contracts"][
        "v3_comfort_first_precheck_fail_closed"
    ]
    assert review["contract_test_contract"]["contracts"][
        "v3_implementation_contract_tests_present"
    ]


def test_guarded_material_v3_post_static_review_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="bad")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_guarded_material_v3_post_static_review_requires_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        audit_text=_audit_text().replace(target.CURRENT_GATE, "wrong_gate"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_current_gate" in report["final_decision"]["failed_checks"]


def test_guarded_material_v3_post_static_review_rejects_missing_v3_descriptor(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_read_current(target.DEFAULT_SOURCE_PATH).replace(
            "diagnostic_descriptor_payload_v3_report_only",
            "diagnostic_descriptor_payload_removed",
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "source_contract.v3_descriptor_legality_report_only"
        in report["final_decision"]["failed_checks"]
    )


def test_guarded_material_v3_post_static_review_rejects_missing_contract_test(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        contract_test_text=_read_current(target.DEFAULT_CONTRACT_TEST_PATH).replace(
            "test_v3_material_support_fails_closed_on_comfort_first_precheck",
            "test_removed",
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "contract_test_contract.v3_implementation_contract_tests_present"
        in report["final_decision"]["failed_checks"]
    )


def test_guarded_material_v3_post_static_review_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    audit, source, route_test, contract_test = _write_inputs(tmp_path)
    out_json = tmp_path / "review.json"
    out_md = tmp_path / "review.md"

    completed = subprocess.run(
        [
            sys.executable,
            str(target.Path(target.__file__)),
            "--audit_path",
            str(audit),
            "--source_path",
            str(source),
            "--route_test_path",
            str(route_test),
            "--contract_test_path",
            str(contract_test),
            "--camp_head",
            CAMP_COMMIT,
            "--camp_origin_main",
            CAMP_COMMIT,
            "--dp_head",
            target.EXPECTED_DP_HEAD,
            "--output_json",
            str(out_json),
            "--output_md",
            str(out_md),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(out_json.read_text(encoding="utf-8"))
    markdown = out_md.read_text(encoding="utf-8")
    assert report["final_decision"]["status"] == target.READY_STATUS
    assert target.AUTHORIZED_NEXT_WORK in markdown
    assert "Math Boundary" in markdown
    assert target.READY_STATUS in completed.stdout
