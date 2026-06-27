# Diffusion Planner CAMP Integration V9 Audit

Date: 2026-06-27

This file is the current short-form audit entry point for the CAMP integration
with the fixed TiERIV Diffusion Planner. The previous
`docs/diffusion_planner_v8_iteration_audit.md` remains historical evidence, but
new current-state writes should land here to avoid duplicate tail reads and
middle-of-file append errors in the oversized v8 log.

## Current Authority

```text
current_authoritative_audit=docs/diffusion_planner_v9_iteration_audit.md
historical_audit=docs/diffusion_planner_v8_iteration_audit.md
handoff_base_camp_head=2b4d76c78e72b681675a837e5f36ba2c18efe5ef
required_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
autodl_camp_path=/root/autodl-tmp/camp_core
autodl_dp_path=/root/autodl-tmp/Diffusion-Planner
formal_seeds_11_12_13_frozen=True
```

## Current Training Fact

The CAMP retraining did run on AutoDL and exited successfully. This is only a
training-artifact fact, not a performance, safety, deployment, or CAMP-over-DP
claim.

```text
camp_training_executed=True
training_command_exit=0
training_commit=0867cc8b468320b7aaef94ce12e6272ca1d362c4
training_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_manual_authorized_0867cc8b_20260627T092951CST
training_summary_json_sha256=ebcae6f710fe8f46387de7c383ca934ac28a22d48b2accc6ccb066f392c47246
offline_weights_json_sha256=6718721393726de47ff7137c6287821bade63dea5e66b9ae0fdff725bbb90896
offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40
atom_scales_json_sha256=a3815169bb734d1039df3527faa9961007a948d30ff757398d9c8b1bc1cef631
training_records=13
validation_records=2
atom_schema_version=dp_camp_v10_14d
num_atoms=14
weights_simplex_nonnegative=True
score_expression=score_k(w)=a_k^T w
fixed_dp_candidate_reranking_only=True
candidate_generation_authorized=False
trajectory_rewrite_authorized=False
dp_modification_authorized=False
```

## Data Sufficiency Finding

The current holdout evidence is too small to support any generalization
statement. Two validation records can catch broken plumbing or contract
violations; they cannot validate performance.

```text
validation_records=2
validation_records_are_insufficient_for_generalization=True
development_holdout_is_smoke_and_contract_only=True
performance_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
deployable_checkpoint_claim_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
holdout_static_underperforms_uniform=True
static_oracle_match_rate=0.5
uniform_oracle_match_rate=1.0
recorded_oracle_match_rate=1.0
requires_broader_nonformal_validation_before_performance_claim=True
```

## Mathematical Boundary

```text
dp_role=fixed_black_box_candidate_trajectory_generator
camp_role=current_tick_fixed_candidate_reranker
allowed_candidate_operation=argmin_k score_k(w)
candidate_tensor_unchanged=True
score_expression=score_k(w)=a_k^T w
atom_inputs=current_tick_finite_candidate_features_only
simplex_master_convex=True
cvar_master_convex=True
l2_master_convex=True
new_atoms_require_nonnegativity_or_signed_split_or_hinge_legality_proof=True
closed_loop_outcome_online_input_authorized=False
reference_blend_authorized=False
guidance_authorized=False
postprocess_postselection_authorized=False
```

## Next Work Target

The next useful step is not another claim over the two-record validation set.
It is to expand the nonformal development data, rebuild the train/validation
split without formal seeds 11/12/13, retrain CAMP on the expanded fixed DP
candidate dataset, and then audit the larger holdout before any promotion or
safety statement.

```text
next_work_target=dp_camp_v9_expand_nonformal_development_dataset_and_retrain_static_reranker
manual_retraining_authorization_present=True
formal_seeds_11_12_13_authorized=False
dp_retraining_authorized=False
dp_tuning_authorized=False
dp_modification_authorized=False
candidate_generation_by_camp_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```
