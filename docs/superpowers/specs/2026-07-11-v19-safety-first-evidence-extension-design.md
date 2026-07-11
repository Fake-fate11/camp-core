# V19 Safety-First Evidence Extension Design

**Date:** 2026-07-11
**Status:** Approved by the user's v19 goal and clarification; execution remains gate-bound
**Scope:** CAMP-side qualification, read-only evidence audits, and only then a matched closed-loop smoke if every prerequisite passes

## Objective

The final scientific objective is to test whether a CAMP selector is safer than
the fixed TiER IV Diffusion Planner's own native default or native Top-1
selection in matched closed-loop scenarios. Safety is primary. ADE, FDE, and
miss rate are secondary trajectory-quality and non-regression metrics.

The existing v18 evidence is qualified, not erased:

1. `performance_claim=no_claim`
2. `bounded_offline_safety_proxy_improvement=supported`
3. `closed_loop_safety_claim=not_yet_supported`
4. `broad_CAMP_over_native_DP_Top1_claim=not_supported`

The v18 bounded result is exact only within the frozen observable source of 32
dynamic and 5 static objects. It is not complete-scene feasibility, official
nuPlan closed-loop safety, or real-world safety.

## Non-negotiable Baseline Semantics

Candidate 0 is currently proven only as the fixed-DP deterministic/MAP output.
That equivalence does not prove that the fixed DP exposes a native K-candidate
ranking or a native Top-1 selector.

Before any closed-loop claim-bearing execution, a read-only provenance audit of
fixed DP commit `7a1d33da277a1992ec474b5383a0c963c72e04e4` must establish:

- the executable native inference, sampling, ranking, and default-selection
  path;
- whether a native ranking actually exists;
- the source-derived index or output chosen by the native implementation;
- source-blob, model/config/checkpoint, command, input, output, and selection
  hashes sufficient to reproduce that conclusion.

If the fixed implementation has no native candidate ranking, the only allowed
name is `DP-default deterministic/MAP baseline`. The absence of a native Top-1
cannot be repaired by renaming candidate 0, by using a research/training reward
ranker, or by treating batch item 0 as ranked Top-1 without an executable native
selection contract. In that case the broad native-Top-1 objective remains
unmet even if a default-baseline comparison is run.

## Matched Closed-Loop Arms

Both arms start from the same scenario, seed, and initial state and use the same
fixed DP model, config, checkpoint, simulator, traffic policy, tracker, timing,
and failure rules.

- Baseline arm: execute the fixed DP's proven native default/Top-1 selection.
- CAMP arm: at every planning tick generate K=8 with the same fixed DP and let
  CAMP select one unchanged trajectory from that tick's immutable tensor.

The two arms roll out independently. State and future candidate tensors may
naturally diverge after the first selection. CAMP must never generate, repair,
blend, guide, postprocess, or rewrite a trajectory.

## Primary Evidence Contract

Primary reporting uses the lower-is-better closed-loop SafetyCost v1 defined in
`docs/dp_camp_safety_score_v1.md`, paired by scenario/run key. It reports mean
delta, deterministic 10,000-replicate cluster-bootstrap CI95, CVaR90,
better/tie/worse, scenario buckets, all hard gates, selector latency, and total
planning-path latency when measurable.

The primary support condition is:

```text
hard_gate_passed=true
and ci95_high(DeltaSafetyCost_v1)<0
```

Official nuPlan collision, TTC, drivable-area, progress, speed, and comfort
metrics are additionally reported when the official engine is available. A
missing official metric is recorded as missing and is never replaced by the
bounded offline proxy. ADE/FDE/miss remain secondary and cannot override the
safety result.

All simulator, scenarios, seeds, buckets, metrics, thresholds, bootstrap,
failure rules, baseline provenance, and latency definitions must be frozen
before execution. Formal seeds 11/12/13 and Full36 remain forbidden.

## Chosen Architecture

Use a capability-first sequence and reuse existing code:

1. Bootstrap an append-only v19 audit and a named `Current V19 Status` pointer.
   The v19 audit EOF is the controller authority. The status reader is confined
   to the named section and must match the audit EOF.
2. Produce one read-only native-baseline and safety-evidence-gap audit. Reuse
   the existing SafetyCost v1 aggregation/hard-gate code; do not build a second
   statistics stack.
3. Audit official nuPlan simulator/devkit availability and fixed-DP integration
   capability without modifying DP.
4. Only if native/default provenance and simulator capability pass, write and
   statically review a thin CAMP-side adapter/preflight for a minimal
   existing-data smoke.
5. Only if the smoke, zero-overlap, immutable-candidate, metric-integrity, and
   result-review gates pass, permit a larger non-formal matched evaluation.

This is intentionally preferred over two alternatives:

- Reusing the v14 TiER IV `scenario_generation`/PerfectTracker replay directly
  cannot satisfy official nuPlan closed-loop evidence and therefore remains a
  reference implementation only.
- Installing a simulator stack and writing an adapter before capability and
  provenance qualification risks building against the wrong baseline and is
  deferred.

## Live Capability Facts at Design Time

These facts are audit inputs, not permanent assumptions:

- CAMP local, GitHub, and AutoDL were synchronized at
  `e80ea339425e54598218d697650304989a5c2404` with no related job running.
- Fixed DP was tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- nuPlan mini contained 64 SQLite DBs plus maps under the existing licensed
  data root.
- The fixed DP environment did not contain `nuplan-devkit`, and the fixed DP
  repository exposed no nuPlan integration reference.
- The fixed DP core decoder returns one prediction per batch item and contains
  no inference-time K-ranking step. The Python ROS path defaults to
  `batch_size=1` and publishes item 0, while separate research/training code
  contains reward ranking. The provenance audit must decide which, if any,
  constitutes the fixed implementation's executable native default.

## Evidence-Gap Output

The read-only audit emits JSON and Markdown plus `HEADS`, `COMMAND`, captured
stdout/stderr, and `SHA256SUMS`. At minimum it records:

- the four claim-taxonomy values;
- v18 bounded-proxy protocol/result roots and their limited scope;
- native baseline provenance status and exact missing evidence;
- fixed DP source-blob hashes for every relied-on native path;
- nuPlan data, devkit, simulator, planner-adapter, and official metric-engine
  availability;
- whether matched arm execution is currently possible without DP mutation;
- the smallest remediation or scale-up requirement;
- explicit booleans prohibiting execution and claims when any hard gate fails.

No v18 holdout label is reopened or read by this audit.

## Failure and Stop Behavior

Fail closed before execution when native/default provenance, fixed-DP identity,
candidate immutability, zero-overlap, affine/simplex/convex boundaries, simulator
matching, metric completeness, or no-leakage cannot be established.

Stop and report the minimum gap if the next step requires modifying DP,
reopening the old holdout, downloading a large new dataset, using Full36 or
formal seeds, changing frozen metrics after results, or obtaining an unavailable
official source. No promotion, deployment, activation, model replacement, or
broad safety claim is in scope.

## Verification

Each implementation gate runs the narrow target tests, v18/v19 pointer and
audit/status tests, `py_compile`, relevant causal/safety suites, and
`git diff --check`; then it is reproduced on AutoDL with artifact hashes before
the audit/status pointer advances. An already-running job is monitored and not
duplicated.
