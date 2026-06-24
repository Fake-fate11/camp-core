# DP Native Candidate Tensor Provenance Payload Authorization

Date: 2026-06-24

Gate:

```text
dp_native_candidate_tensor_provenance_payload_implementation_authorization_only
```

## Status Evidence

```text
git status --short --branch
## main...origin/main
?? camp-dp-session-019eb4d3-20260618-174834-HANDOFF.md
?? camp-dp-session-2b67d33-20260615-231639-HANDOFF.md
?? camp-dp-session-8ae0950-20260616-235726/
?? camp-dp-session-a1da97f-20260618-002803-HANDOFF.md
?? "slides prompt.md"

git fetch --prune origin
exit=1
reason=GitHub HTTPS/TLS handshake failure before any repo mutation

git rev-parse HEAD origin/main
43167e72a928ecab74d2b60b08b78259b67cebae
43167e72a928ecab74d2b60b08b78259b67cebae

git ls-remote origin refs/heads/main
exit=1
reason=GitHub HTTPS/TLS handshake failure
```

The untracked paths above are unrelated session or slide artifacts and are not
part of this gate.

## Code Evidence

The replay integration already has a single in-memory candidate tensor flow that
can be instrumented without changing candidate generation, scoring, or selected
trajectory semantics:

```text
scripts/integrations/run_diffusion_planner_camp_replay.py
  generate_candidate_trajectories(...) returns candidates
  selector.select(candidates, ...) reads those candidates and returns selection
  selected_trajectory = candidates[selected_index]
  records.append(...) writes per-tick selector evidence
```

The DP integration code keeps candidate generation in one helper:

```text
camp_core/camp_core/integrations/diffusion_planner.py
  generate_candidate_trajectories(...) returns ego_candidates [K,T,4]
  CAMPSelector.select(...) consumes candidates and returns CAMPSelectionResult
```

The current audit tail and atom audit both require CAMP to remain a fixed
candidate reranker and identify the missing proof as candidate tensor
provenance, not as missing replay/training evidence.

## Authorized Implementation Boundary

Authorize only a minimal, default-off provenance payload with these properties:

```text
selection_effect=False
pre_camp_scoring_tensor_sha256 present when enabled
post_camp_selector_tensor_sha256 present when enabled
hash_input=contiguous tensor bytes plus explicit shape and dtype
nan_policy=preserve tensor bytes; do not stringify floating point values
candidate_count recorded
selected_index_in_range recorded
pre_post_tensor_hash_equal recorded
no_candidate_row_append recorded
no_coordinate_heading_speed_rewrite_by_camp recorded
outcome_label_input=False
```

Reference-blend stage separation must be reported if reference blending is ever
present in a legacy or diagnostic run, but reference blending remains rejected
by the paper-faithful boundary and is not authorized for mainline execution.

## Prohibited By This Gate

```text
candidate_generation_execution_authorized=False
trajectory_rewrite_authorized=False
candidate_tensor_mutation_authorized=False
new_replay_authorized=False
formal_seeds_authorized=False
full36_authorized=False
camp_retraining_authorized=False
training_execution_authorized=False
atom_promotion_authorized=False
online_selector_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Decision

```text
status=implementation_authorized
implementation_authorized_now=True
authorized_next_work=dp_native_candidate_tensor_provenance_payload_minimal_default_off_implementation
```

The implementation may add only default-off provenance logging and static
contract tests. It must not run replay, generate new candidates, modify DP,
train CAMP, promote atoms/selectors, or make safety/DP-superiority claims.

## Next Gate

`dp_native_candidate_tensor_provenance_payload_minimal_default_off_implementation`
