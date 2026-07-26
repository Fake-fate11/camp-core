"""Mechanically update the Current V25 section and audit EOF tuple."""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "docs/diffusion_planner_current_status.md"
AUDIT = ROOT / "docs/diffusion_planner_v25_iteration_audit.md"

REPORT_SHA = "a931fdbd42aa4713683936405f776c3a2b1981404616553f10a50103bf40b7fd"
INDEX_SHA = "02acd866ccf1c874fc5b864783456804050a8c3ec6d8990950783e3cc27599f5"

ADDITIONS = {
    "current_v25_status": "batch8_generator_repeatability_corrected_full_denominator_threshold_independently_reviewed_control_decision_required",
    "current_v25_phase": "bounded_development_corrected_same_input_same_latent_generator_repeatability_calibration_full_denominator_and_independently_reviewed_envelope",
    "current_v25_batch8_generator_calibration_authority_sha256": "eba03c38f8eb6272c9cc31de464b88752a94e622ac352ffe349c70726bbe4f77",
    "current_v25_batch8_generator_calibration_schema": "camp_dp_v25_batch8_generator_repeatability_corrected_contract_v1",
    "current_v25_batch8_generator_calibration_implementation_head": "24b4d35eb422fc3404c70f9deaf7ebb888be2095",
    "current_v25_batch8_generator_calibration_source_spec_manifest_sha256": "569718077a1c6c7f5193074ba86e646da4a3a40a2fdc573c7bfa51f3cfaa722f",
    "current_v25_batch8_generator_calibration_contract_root_sha256": "4aacc1addf1ecefb4ddea4c58ef96391f09a350eaf687eea3fd59fc6a356c60a",
    "current_v25_batch8_generator_calibration_contract_review_root_sha256": "9dcd2e6b7d928768b0344b9b2423ec4acd58c4d013af9de87923b795996ef8a7",
    "current_v25_batch8_generator_calibration_focused_root_sha256": "1aa3344a30ba95585604f40d5b082e21e80af77602e749389948d3ce9d90d5ef",
    "current_v25_batch8_generator_calibration_focused_test_count": "27",
    "current_v25_batch8_generator_calibration_preflight_root_sha256": "5be8831533f0a46ecc5439c3eafbff85118689f7696996d825c4b09838189fac",
    "current_v25_batch8_generator_calibration_preflight_review_root_sha256": "280e45b18630f286147bfe8796df71085701841d339c602a5cd30de6d7943584",
    "current_v25_batch8_generator_calibration_raw_root_sha256": "731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4",
    "current_v25_batch8_generator_calibration_raw_review_root_sha256": "c0e24bb60a4eb9694bfda099d4d6d9b9be07f85fb486577275f0b32178cfbfc8",
    "current_v25_batch8_generator_calibration_threshold_root_sha256": "a4f6c54cb46378119b261fe0ef19f83f8b92d18fa3be3e02693f7905f3f8ac89",
    "current_v25_batch8_generator_calibration_threshold_review_root_sha256": "8882f0fa66d1690460662848fa67673657926cc663b0edf476866e1418034e0e",
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
    "current_v25_batch8_generator_calibration_candidate_position_threshold_m": "0.0001",
    "current_v25_batch8_generator_calibration_candidate_heading_threshold_rad": "0.00001",
    "current_v25_batch8_generator_calibration_candidate_speed_threshold_mps": "0.0001",
    "current_v25_batch8_generator_calibration_neighbor_position_threshold_m": "0.0001",
    "current_v25_batch8_generator_calibration_neighbor_heading_threshold_rad": "0.00001",
    "current_v25_batch8_generator_calibration_neighbor_speed_threshold_mps": "0.0001",
    "current_v25_batch8_generator_calibration_bootstrap": "PCG64DXSM_seed825071_10000_resamples_q99_higher_index63_ucb_index9500",
    "current_v25_batch8_generator_calibration_interpretation": "bounded_development_corrected_same_input_same_latent_generator_repeatability_calibration_full_denominator_and_independently_reviewed_envelope",
    "current_v25_batch8_generator_calibration_same_state_input_sha_cardinality": "1",
    "current_v25_batch8_generator_calibration_same_state_latent_tensor_sha_cardinality": "1",
    "current_v25_batch8_generator_calibration_bootstrap_ucb_all_zero": "true",
    "current_v25_batch8_generator_calibration_old_dispersion_classification": "bounded_development_latent_resampled_candidate_pool_dispersion_diagnostic",
    "current_v25_batch8_generator_calibration_old_dispersion_raw_root_sha256": "1dc673dc99df411ccee571fe80a1261c08fba5b52ab87ff397bb2733c2868f82",
    "current_v25_batch8_generator_calibration_old_dispersion_raw_review_root_sha256": "8756b1d5aa32f666aaabe7cab6bdfddc3ced0ded638caed673f7a4d05f61b45b",
    "current_v25_batch8_generator_calibration_old_dispersion_threshold_root_sha256": "abc15b2cae990e8465aa2fd1a97a6f2903dda948c0606ba167867dcf1a1c0e5b",
    "current_v25_batch8_generator_calibration_old_dispersion_threshold_review_root_sha256": "0d3388f0d4821a09d4c7b0d90710a469a3042f2040c3d0d05865ff7f8c9cf519",
    "current_v25_batch8_generator_calibration_old_dispersion_values_used": "false",
    "current_v25_batch8_generator_calibration_training_support_pass_claimed": "false",
    "current_v25_batch8_generator_calibration_selector_compatibility_claimed": "false",
    "current_v25_batch8_generator_calibration_scientific_benefit_claimed": "false",
    "current_v25_batch8_generator_calibration_outcome_read": "false",
    "current_v25_batch8_generator_calibration_old_artifact_or_cas_write_count": "0",
    "current_v25_batch8_generator_calibration_report": "docs/diffusion_planner_v25_batch8_generator_calibration_report.md",
    "current_v25_batch8_generator_calibration_report_sha256": REPORT_SHA,
    "current_v25_batch8_generator_calibration_evidence_index": "docs/diffusion_planner_v25_batch8_generator_calibration_evidence_index.md",
    "current_v25_batch8_generator_calibration_evidence_index_sha256": INDEX_SHA,
    "next_work_target": "high_control_decision_after_corrected_generator_repeatability_envelope",
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
    prose = """## Current V25 Status - Corrected Same-Input/Same-Latent Batch8 Repeatability Independently Reviewed
Reader contract: this named section is the only current V25 pointer source in
this file. Its machine tuple must match the EOF tuple in
`docs/diffusion_planner_v25_iteration_audit.md` field for field.

The corrected development calibration formed the complete 64-state x 5-repeat
denominator: 320 same-ego single-invocation B=8 model calls and 640 unordered
repeat pairs. Each state reused one exact canonical input and latent tensor
across all five calls. Every candidate and neighbor tensor passed the frozen
shape, finite, diversity and provenance gates. No selector or post-pool call
occurred.

Independent review rebuilt the 320 raw receipts, 640 pair values and all 64
state statistics. A separate threshold review rebuilt the exact PCG64DXSM
bootstrap preimage and six generator-only envelopes. All UCBs were zero, so
the final thresholds equal the pre-frozen resolution floors. This is bounded
development repeatability evidence, not validation, selector compatibility,
training support, effect, industrial-safety or deployment evidence.

Preserved superseded engineering diagnostic: the prior latent-resampled chain
remains immutable and is classified only as
candidate-pool dispersion diagnostic; none of its values entered this chain.
The accepted industrial-oriented evaluation v3 contract remains unchanged.
The corrected evaluation review remains a separate-role sealed deterministic
replay using the frozen canonical evaluation core.
SafetyCost remains an immutable legacy exploratory diagnostic; the historical
scientific result remains `honest_no_claim_under_frozen_preregistered_all_gate`.
High/control must choose the next scientific route.

"""
    CURRENT.write_text(text[:start] + prose + machine + "\n" + text[end:], encoding="utf-8")
    audit_heading = (
        "## V25 Corrected Same-Input/Same-Latent Batch8 Repeatability Review"
    )
    audit = AUDIT.read_text(encoding="utf-8")
    if audit_heading in audit:
        audit = audit.split(audit_heading, 1)[0].rstrip()
    else:
        audit = audit.rstrip()
    audit += (
        "\n\n" + audit_heading + "\n\n"
        "This EOF tuple records the corrected same-input/same-latent development calibration. "
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
