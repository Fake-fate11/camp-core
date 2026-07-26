"""Mechanically update the Current V25 section and audit EOF tuple."""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "docs/diffusion_planner_current_status.md"
AUDIT = ROOT / "docs/diffusion_planner_v25_iteration_audit.md"

REPORT_SHA = "96f27d51e9845342877c755773c1b8474358904a26e9d75682391e72e235d9e9"
INDEX_SHA = "a2c1e14172bb3161aab149f91f5b102541dad1f6562ac5ffb884d9679f79094a"

ADDITIONS = {
    "current_v25_status": "batch8_generator_only_calibration_full_denominator_threshold_independently_reviewed_control_decision_required",
    "current_v25_phase": "batch8_generator_only_calibration_full_denominator_threshold_independently_reviewed",
    "current_v25_batch8_generator_calibration_authority_sha256": "677c3792f52cd817871b6c9948360edced81198d4207cd59b22050080697ee21",
    "current_v25_batch8_generator_calibration_schema": "camp_dp_v25_batch8_generator_calibration_contract_v1",
    "current_v25_batch8_generator_calibration_implementation_head": "cdea31b642830015113661007a456a553acd3ab8",
    "current_v25_batch8_generator_calibration_source_spec_manifest_sha256": "569718077a1c6c7f5193074ba86e646da4a3a40a2fdc573c7bfa51f3cfaa722f",
    "current_v25_batch8_generator_calibration_contract_root_sha256": "5bdf49344a7a22cac09bfdcd139381f17cc0488c4acf825861c0d0b06e07f43c",
    "current_v25_batch8_generator_calibration_contract_review_root_sha256": "722e7c1beac4c9a846213c6620587a0e9f57973d12023caa0744de2f8d001c53",
    "current_v25_batch8_generator_calibration_focused_root_sha256": "6c0a1dc3bc0326aa090c7506e653efa68cf66a9a4cb9a2500568bbee22ff32a2",
    "current_v25_batch8_generator_calibration_focused_test_count": "25",
    "current_v25_batch8_generator_calibration_preflight_root_sha256": "2e3935ed1690ea168daba29a07a497640de0b3d092e7f465bd10c7f4fa416348",
    "current_v25_batch8_generator_calibration_preflight_review_root_sha256": "196828896cbb10fb51622d3b3f582a3eb71551336ceb1319f1e12ab0ce1180ee",
    "current_v25_batch8_generator_calibration_raw_root_sha256": "1dc673dc99df411ccee571fe80a1261c08fba5b52ab87ff397bb2733c2868f82",
    "current_v25_batch8_generator_calibration_raw_review_root_sha256": "8756b1d5aa32f666aaabe7cab6bdfddc3ced0ded638caed673f7a4d05f61b45b",
    "current_v25_batch8_generator_calibration_threshold_root_sha256": "abc15b2cae990e8465aa2fd1a97a6f2903dda948c0606ba167867dcf1a1c0e5b",
    "current_v25_batch8_generator_calibration_threshold_review_root_sha256": "0d3388f0d4821a09d4c7b0d90710a469a3042f2040c3d0d05865ff7f8c9cf519",
    "current_v25_batch8_generator_calibration_state_count": "64",
    "current_v25_batch8_generator_calibration_repeats_per_state": "5",
    "current_v25_batch8_generator_calibration_planned_run_count": "320",
    "current_v25_batch8_generator_calibration_completed_run_count": "320",
    "current_v25_batch8_generator_calibration_formal_model_call_count": "320",
    "current_v25_batch8_generator_calibration_pair_count": "640",
    "current_v25_batch8_generator_calibration_candidate_shape_dtype": "8,80,4_float32",
    "current_v25_batch8_generator_calibration_neighbor_shape_dtype": "8,32,80,4_float32",
    "current_v25_batch8_generator_calibration_candidate_unique8_count": "320",
    "current_v25_batch8_generator_calibration_typed_failure_count": "0",
    "current_v25_batch8_generator_calibration_hard_integrity_failure_count": "0",
    "current_v25_batch8_generator_calibration_sequential_model_call_count": "0",
    "current_v25_batch8_generator_calibration_selector_call_count": "0",
    "current_v25_batch8_generator_calibration_post_pool_call_count": "0",
    "current_v25_batch8_generator_calibration_candidate_position_threshold_m": "8.538636633630066",
    "current_v25_batch8_generator_calibration_candidate_heading_threshold_rad": "0.007386684417724609",
    "current_v25_batch8_generator_calibration_candidate_speed_threshold_mps": "0.017767117824405432",
    "current_v25_batch8_generator_calibration_neighbor_position_threshold_m": "63.36473171992804",
    "current_v25_batch8_generator_calibration_neighbor_heading_threshold_rad": "0.4141414761543274",
    "current_v25_batch8_generator_calibration_neighbor_speed_threshold_mps": "0.09179673623293638",
    "current_v25_batch8_generator_calibration_bootstrap": "PCG64DXSM_seed825071_10000_resamples_q99_higher_index63_ucb_index9500",
    "current_v25_batch8_generator_calibration_interpretation": "bounded_development_repeatability_envelope_not_validation_equivalence_or_effect_claim",
    "current_v25_batch8_generator_calibration_training_support_pass_claimed": "false",
    "current_v25_batch8_generator_calibration_selector_compatibility_claimed": "false",
    "current_v25_batch8_generator_calibration_scientific_benefit_claimed": "false",
    "current_v25_batch8_generator_calibration_outcome_read": "false",
    "current_v25_batch8_generator_calibration_old_artifact_or_cas_write_count": "0",
    "current_v25_batch8_generator_calibration_report": "docs/diffusion_planner_v25_batch8_generator_calibration_report.md",
    "current_v25_batch8_generator_calibration_report_sha256": REPORT_SHA,
    "current_v25_batch8_generator_calibration_evidence_index": "docs/diffusion_planner_v25_batch8_generator_calibration_evidence_index.md",
    "current_v25_batch8_generator_calibration_evidence_index_sha256": INDEX_SHA,
    "next_work_target": "high_control_decision_selector_adaptation_reference_or_versioned_v3_closed_loop_design",
}


def tuple_lines(section: str) -> list[str]:
    return [
        line
        for line in section.splitlines()
        if re.fullmatch(r"[a-z0-9_]+=[^\r\n]*", line)
    ]


def main() -> int:
    text = CURRENT.read_text(encoding="utf-8")
    start = text.index("## Current V25 Status")
    end = text.index("\n## ", start + 3)
    old_lines = tuple_lines(text[start:end])
    order = [line.split("=", 1)[0] for line in old_lines]
    values = dict(line.split("=", 1) for line in old_lines)
    for key, value in ADDITIONS.items():
        if key not in values:
            order.append(key)
        values[key] = value
    machine = "\n".join(f"{key}={values[key]}" for key in order)
    prose = """## Current V25 Status - Batch8 Generator-Only Calibration Independently Reviewed
Reader contract: this named section is the only current V25 pointer source in
this file. Its machine tuple must match the EOF tuple in
`docs/diffusion_planner_v25_iteration_audit.md` field for field.

The sole authorized development calibration formed the complete 64-state x
5-repeat denominator: 320 same-ego single-invocation B=8 model calls and 640
unordered repeat pairs. Every candidate and neighbor tensor passed the frozen
shape, finite, diversity and provenance gates. No selector or post-pool model,
DP, latent or candidate-generation call occurred.

Independent review rebuilt the 320 raw receipts, 640 pair values and all 64
state statistics. A separate threshold review rebuilt the exact PCG64DXSM
bootstrap preimage and six generator-only envelopes. This is bounded
development repeatability evidence, not validation, selector compatibility,
training support, effect, industrial-safety or deployment evidence.

Preserved superseded engineering diagnostic: the accepted
industrial-oriented evaluation v3 contract remains unchanged.
The corrected evaluation review remains a separate-role sealed deterministic
replay using the frozen canonical evaluation core.
SafetyCost remains an immutable legacy exploratory diagnostic; the historical
scientific result remains `honest_no_claim_under_frozen_preregistered_all_gate`.
High/control must choose the next selector-adaptation reference or versioned
v3 closed-loop design.

"""
    CURRENT.write_text(text[:start] + prose + machine + "\n" + text[end:], encoding="utf-8")
    audit_heading = (
        "## V25 Batch8 Generator-Only Calibration Full Denominator and Threshold Review"
    )
    audit = AUDIT.read_text(encoding="utf-8")
    if audit_heading in audit:
        audit = audit.split(audit_heading, 1)[0].rstrip()
    else:
        audit = audit.rstrip()
    audit += (
        "\n\n" + audit_heading + "\n\n"
        "This EOF tuple records the accepted generator-only development calibration. "
        "It adds no selector, effect, Fresh, training-support, claim or deployment authority. "
        "The corrected evaluation review remains a separate-role sealed deterministic replay "
        "using the frozen canonical evaluation core.\n\n"
        + machine
        + "\n"
    )
    AUDIT.write_text(audit, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
