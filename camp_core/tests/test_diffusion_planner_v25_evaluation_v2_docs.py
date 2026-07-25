from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"
AUDIT = ROOT / "docs" / "diffusion_planner_v25_iteration_audit.md"
REPORT = ROOT / "docs" / "diffusion_planner_v25_evaluation_v2_report.md"
INDEX = ROOT / "docs" / "diffusion_planner_v25_evaluation_v2_evidence_index.md"
MIGRATION = ROOT / "docs" / "diffusion_planner_v25_evaluation_v2_migration_matrix.md"
FUTURE_PLAN = (
    ROOT
    / "docs"
    / "diffusion_planner_v25_evaluation_v2_future_nonholdout_acquisition_plan.md"
)
AGGREGATE = ROOT / "docs" / "diffusion_planner_v25_evaluation_v2_aggregate_summary.json"
CURRENT_HEADING = (
    "## Current V25 Status - Evaluation v2 Corrected Independently Reviewed "
    "Exploratory Honest No-Claim"
)
AUDIT_HEADING = (
    "## 2026-07-25 - Evaluation v2 Corrected Independently Reviewed "
    "Exploratory Honest No-Claim"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tuple(section: str) -> dict[str, str]:
    rows = [
        row for row in section.splitlines() if re.fullmatch(r"[a-z][a-z0-9_]*=.*", row)
    ]
    result = dict(row.split("=", 1) for row in rows)
    assert len(result) == len(rows)
    return result


def _current(text: str) -> str:
    assert text.count("## Current V25 Status") == 1
    assert text.count(CURRENT_HEADING) == 1
    return text.split(CURRENT_HEADING, 1)[1].split(
        "## Historical V25 Status Through A1.6.11", 1
    )[0]


def _eof(text: str) -> str:
    assert text.count(AUDIT_HEADING) == 1
    return text.split(AUDIT_HEADING, 1)[1]


def test_evaluation_v2_pointer_and_audit_are_exact() -> None:
    status = _tuple(_current(STATUS.read_text(encoding="utf-8")))
    audit = _tuple(_eof(AUDIT.read_text(encoding="utf-8")))
    assert status == audit
    assert status["current_v25_status"] == (
        "v25_evaluation_v2_corrected_independently_reviewed_exploratory_honest_no_claim"
    )
    assert status["current_v25_phase"] == (
        "evaluation_v2_corrected_independently_reviewed_terminal"
    )
    assert status["next_work_target"] == (
        "high_evaluation_v2_corrected_combined_package_review"
    )
    assert status["current_v25_evaluation_v2_report_sha256"] == _sha(REPORT)
    assert status["current_v25_evaluation_v2_evidence_index_sha256"] == _sha(INDEX)
    assert status["current_v25_evaluation_v2_migration_matrix_sha256"] == _sha(
        MIGRATION
    )
    assert status["current_v25_evaluation_v2_future_plan_sha256"] == _sha(FUTURE_PLAN)
    assert status["current_v25_evaluation_v2_aggregate_summary_sha256"] == _sha(
        AGGREGATE
    )


def test_evaluation_v2_docs_and_aggregate_preserve_claim_boundary() -> None:
    documents = [
        REPORT.read_text(encoding="utf-8"),
        INDEX.read_text(encoding="utf-8"),
        MIGRATION.read_text(encoding="utf-8"),
        FUTURE_PLAN.read_text(encoding="utf-8"),
    ]
    for text in documents:
        assert "@@V2_" not in text
        assert "honest_no_claim_under_frozen_preregistered_all_gate" in text
    aggregate = json.loads(AGGREGATE.read_text(encoding="utf-8"))
    assert (
        aggregate["schema_version"]
        == "camp_dp_v25_evaluation_v2_corrected_aggregate_summary_v1"
    )
    assert aggregate["per_run_values_included"] is False
    assert aggregate["legacy_evaluation_values_included"] is False
    assert aggregate["v2_claim_authorized"] is False
    assert aggregate["result_semantics"] == (
        "exploratory_posthoc_not_claim_authorizing"
    )
    assert set(aggregate["endpoint_vector"]) == {
        "collision",
        "dynamic_proximity",
        "road_containment",
        "certified_red_crossing",
        "speed",
        "route",
        "goal",
        "vehicle_body_planar_kinematic_proxy",
        "latency",
    }
    for endpoint in aggregate["endpoint_vector"].values():
        assert set(endpoint) == {
            "formula",
            "units",
            "source_root_sha256",
            "evidence_class",
            "denominator",
            "opportunity",
            "aggregate",
            "status",
            "missing_reason_counts",
        }
        assert endpoint["source_root_sha256"] == (
            "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
        )
        assert endpoint["denominator"]["required_arm_count"] == 1500
        if endpoint["denominator"]["missing_arm_count"]:
            assert endpoint["aggregate"] == {
                "status": "evidence_missing",
                "paired_inference": "cancelled_missing_full_paired_denominator",
                "complete_case_shrinkage_used": False,
            }

    assert aggregate["superseded_diagnostic"] == {
        "contract_review_root_sha256": (
            "a15edb5cad2279991dec2f091e134cd3a711a1b949eb38523a20125578500fed"
        ),
        "contract_root_sha256": (
            "2a3c39aea959a9e311859f8af2c4ea81e22ac093b4e62ea48cbca6f4808d5795"
        ),
        "materialization_root_sha256": (
            "0cd17b28553b1ae8b1f23eb8796974e6c06f1d5e1c020998d302526f3b07c72d"
        ),
        "preserved": True,
        "review_root_sha256": (
            "d1cfb29dbb34e3bb92592f803820a6a0454af89b3b9fc2100b45cbaf8215f91d"
        ),
    }
    assert aggregate["endpoint_vector"]["route"]["denominator"][
        "available_arm_count"
    ] == 929
    assert aggregate["endpoint_vector"]["route"]["denominator"][
        "missing_arm_count"
    ] == 571
    assert aggregate["endpoint_vector"]["goal"]["denominator"][
        "available_arm_count"
    ] == 1500


def test_evaluation_v2_corrected_btw_is_paired_not_variance() -> None:
    aggregate = json.loads(AGGREGATE.read_text(encoding="utf-8"))
    collision = aggregate["endpoint_vector"]["collision"]["aggregate"]
    for method in ("static14d", "scene14d"):
        summary = collision["paired_cluster_summaries"][method]["/collision_any"]
        btw = summary["better_tie_worse"]
        assert btw["sum"] == 500
        assert btw["better"] + btw["tie"] + btw["worse"] == 500
        assert btw["tie_rule"] == "exact_zero_delta"
        assert summary["variance_fields_are_not_better_tie_worse"] is True
        assert summary["cluster_count"] == 100
    unclassified = collision["paired_cluster_summaries"]["static14d"][
        "/kinematic_relative_speed_proxy_is_severity"
    ]["better_tie_worse"]
    assert unclassified == {
        "reason": "no_outcome_independent_natural_direction",
        "status": "descriptive_unclassified",
    }


def test_evaluation_v2_docs_bind_no_rerun_and_no_cas_mutation() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPORT, INDEX, MIGRATION, FUTURE_PLAN)
    )
    required = (
        "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881",
        "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d",
        "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f",
        "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459",
        "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392",
        "ab99f6740038136409b9f131c8bd38dd35b1b19c338e85c4df6ba86b25f59306",
        "0962b233a2a0391649433233bd4e7fcbd688ddedc28f2d25fa5cf4eda9354628",
        "3a4575f346188d87c4c3c18e4cc817540eac09aa38cd0cf886628c3013402588",
        "372550201df3f62907d7fe247cb9889cecfa2abef91ab7db425613f70c816827",
        "not_prospectively_defined_for_v2",
        "exploratory_posthoc_not_claim_authorizing",
    )
    for value in required:
        assert value in combined
    prohibited_claims = (
        "Fresh benefit",
        "real-road safety",
        "broad unseen-map",
        "native-ranked Top1",
        "production readiness",
    )
    for claim in prohibited_claims:
        assert claim in combined
