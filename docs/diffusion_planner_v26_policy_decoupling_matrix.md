# V26 neutral CAMP-kernel dependency matrix

## Scope

This matrix covers the active V26 nuPlan path: source adapter, same-ego B8
materialization, selector adaptation, and development comparison.  It does not
delete V25 historical entry points or reinterpret existing corpus rows.

| V26 surface | Before | Neutral interface now used | Classification | V26 behavior |
| --- | --- | --- | --- | --- |
| nuPlan B8 corpus materializer | V25 raw-context and train-atom-audit imports | `diffusion_planner_camp_context_math`, `diffusion_planner_camp_training_math`, `diffusion_planner_v26_source_capabilities` | shared arithmetic | Same 26D context, scale, label, tie, and mask arithmetic; no V25 release path |
| official mini B8 smoke | V25 raw context plus per-call optional-source flags | V26 source-capability boundary | source capability | speed/signal absence is typed-missing and masked, never defaulted |
| fixed-DP atom materializer | V25 semantic-authority validator | `diffusion_planner_camp_signal_contract` | shared signal contract | Same schema literal and geometry/receipt checks; no V25 authority module import |
| native replay, Scene14D, adaptation, comparison | V25 context/fixed-DP helper imports | neutral context and fixed-DP reference APIs | shared arithmetic/identity | same frozen scaler, simplex tolerance, parameter fingerprint, and B8 contract |
| selector fit | V25-named training call | `diffusion_planner_camp_selector_training` | math-only compatibility facade | CAMP convex selector arithmetic only; no V25 runner/evaluator/release API exposed to V26 |
| historical V26 zero-shot profiling | V25 scene reference loader | `diffusion_planner_camp_reference_runtime` | frozen reference compatibility only | retained read-only reference bridge; excluded from the active nuPlan corpus registry |

## Static V25-reference inventory

The active registry checked by
`test_diffusion_planner_v26_policy_decoupling.py` is the nuPlan adapter,
signal/capability boundary, native runner, Scene14D/selector/comparison
surfaces, and the mini/corpus materializers.  It has no direct import of a
`diffusion_planner_v25_*` or V25 validator module.  The neutral CAMP-core
modules are checked separately for the same property.

Two V25-named references deliberately remain outside that registry:

| Location | Reference kind | Classification |
| --- | --- | --- |
| `diffusion_planner_v26_target_bounded_surface.py` | Stage-2 allowlist strings for `run_diffusion_planner_v25_industrial_bounded_closed_loop.py` and `validate_diffusion_planner_v25_fair_nonholdout.py` | immutable historical provenance only; no import or runtime dispatch |
| `run_diffusion_planner_v26_one_state_development_smoke.py` | direct V25 fair-runner, scene-runtime, and `_run_one` imports | retained legacy Autoware diagnostic; not an official nuPlan production entry and excluded from the active registry |

The latter is intentionally not silently reclassified as current V26
production.  Current nuPlan corpus rows do not execute either retained
reference.

## Capability policy

`V26SourceCapabilities` is the only active optional-source boundary.  It
declares `speed_limit_status` and `signal_source_state`; the boundary converts
those states once into the shared atom and context masks.  It rejects a
source-authority/capability mismatch.  There is no V25 context `allow_*`
argument at a V26 materializer or smoke callsite.

## Deliberately retained hard failures

- Frozen split/identity, fixed-DP head, same-ego B8 topology, finite unique
  candidate rows, candidate0=row0, and post-pool-zero are still required.
- Non-computable route geometry remains a typed hard failure.
- Optional speed/signal/stopline absence is not a hard failure when the source
  capability explicitly declares it; the affected atoms/endpoints are masked
  or typed missing.

## Explicitly excluded V25 policy

The active V26 registry does not directly import V25 authority, release,
nonce, CAS, opening, holdout, evaluator, or industrial-runner modules.  The
static dependency test enforces that direct-import boundary.  V25 historical
modules remain available through their own entry points and retain their
existing semantics.
