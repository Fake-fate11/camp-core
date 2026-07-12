# V19 CARLA Exact-Speed Source Ladder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement, census, independently review, and freeze the first legal CARLA exact-speed source rung before any planner or simulator outcome.

**Architecture:** Add one pure Python 3.9 ladder module and one thin source-only census CLI. Runtime actor observations and fixed-DP candidate paths enter as frozen JSON; the ladder never imports CARLA or reads outcomes.

**Tech Stack:** Python 3.9 standard library, NumPy already used by CAMP, pytest, existing v19 artifact helpers and audit/status pointer.

## Global Constraints

- Ladder order is exactly A actor/landmark, B explicit non-junction road speed, C unique all-adjacent-equal junction topology.
- No `Vehicle.get_speed_limit()`, current speed, default, average, one-sided inheritance, nearest-neighbour, interpolation, or fourth rung.
- Every candidate-used segment must be source-complete; all-K-ineligible is retained and excluded fail-closed.
- No outcome reads before source/scenario/candidate freeze and independent review.
- Fixed DP, K=8 tensors, 3+8 contract, 14D atoms, weights, affine/simplex/convex constraints, baseline provenance, seed, metrics, and claim taxonomy do not change.
- Maintain one job, immutable artifacts, SHA manifests, tracked-clean heads, and at least 10 GiB free.

---

### Task 1: Pure ladder contract

**Files:**
- Create: `camp_core/camp_core/integrations/carla_exact_speed_source.py`
- Create: `camp_core/tests/test_carla_exact_speed_source.py`

**Interfaces:**
- Produces: `parse_opendrive_speed_index(xml_text: str) -> OpenDriveSpeedIndex`
- Produces: `resolve_segment_speed(segment, index, actor_values, rung) -> SegmentSpeedDecision`
- Produces: `candidate_source_mask(candidate_segments, index, actor_values, rung) -> CandidateSourceDecision`

- [ ] **Step 1: Write failing tests** for a unique A mapping, ambiguous A
  values, explicit B non-junction speed, B rejecting junctions, C accepting
  unique equal incoming/outgoing speeds, and C rejecting missing, ambiguous,
  unequal, or one-sided topology. Assert finite-positive normalization and
  all-segment conjunction.
- [ ] **Step 2: Run**
  `py -3.9 -m pytest camp_core/tests/test_carla_exact_speed_source.py -q`.
  Expected: collection failure because the module does not exist.
- [ ] **Step 3: Implement the smallest immutable dataclasses and functions.**
  Parse only `<road>`, `<type><speed>`, lane sections, road/junction links, and
  speed signals needed by the frozen rules. Return explicit reason strings;
  never infer a value on failure.
- [ ] **Step 4: Re-run the target test.** Expected: all pass.
- [ ] **Step 5: Commit** module and test as one TDD checkpoint.

### Task 2: Source-only census CLI

**Files:**
- Create: `scripts/integrations/audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py`
- Create: `camp_core/tests/test_diffusion_planner_v19_carla_exact_speed_sources.py`

**Interfaces:**
- Consumes: main Town XODRs, optional actor-observation JSON, optional frozen
  candidate-segment JSON, `--rung {A,B,C}`.
- Produces: JSON with per-map/record/candidate masks, reasons, support counts,
  zero outcome-call counters, HEADS, input SHA values, and decision.

- [ ] **Step 1: Write failing CLI tests** using tiny XODRs and candidate JSON.
  Assert deterministic output, no fallback, candidate-0 eligibility, all-K
  exclusion, and rejection of any outcome-labelled input field.
- [ ] **Step 2: Run the target tests.** Expected: missing script failure.
- [ ] **Step 3: Implement the CLI** as argument parsing plus calls to Task 1;
  do not duplicate source logic or add a dependency.
- [ ] **Step 4: Run py_compile and both target test files.** Expected: pass.
- [ ] **Step 5: Commit** the census checkpoint.

### Task 3: Runtime actor/landmark source preflight and census

**Files:**
- Modify only if required by tested CLI contract: the two Task 2 files.
- Evidence only: `/root/autodl-tmp/camp_dp_v19_carla_exact_speed_source_*`

**Interfaces:**
- Consumes: published CARLA 0.9.16 runtime and Task 2 CLI.
- Produces: source-only actor/landmark observations keyed by OpenDRIVE IDs and
  full A/B/C census artifacts; no planner, arm, metric, or outcome.

- [ ] **Step 1: Preflight** heads, DP commit, no peer job, CARLA port/process,
  runtime/client compatibility, free bytes, one staging/final root, and zero
  outcome inputs.
- [ ] **Step 2: Start one runtime source probe** only after preflight. Enumerate
  official speed-limit actors/landmarks and OpenDRIVE IDs; do not call
  `Vehicle.get_speed_limit()` or advance an evaluation arm.
- [ ] **Step 3: Run A, B, and C full source-only censuses in order.** Stop at the
  first rung with legal paired support, but preserve later rungs as unexecuted.
- [ ] **Step 4: Seal artifacts** with HEADS, COMMAND, stdout/stderr, exit,
  input/output SHA manifests, call counters, masks, reasons, and free bytes.
- [ ] **Step 5: Independently recompute and review** the selected rung. If all
  three have zero support, stop at the authorized hard boundary.

### Task 4: Candidate/source/scenario freeze

**Files:**
- Evidence and docs only unless a target test exposes a minimal contract bug.
- Modify: `docs/diffusion_planner_v19_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`
- Modify: `camp_core/tests/test_diffusion_planner_v19_orchestrator.py`

**Interfaces:**
- Consumes: first reviewed supported rung, fixed-DP K=8 candidate tensors,
  source-only masks, existing zero-overlap rules.
- Produces: immutable freeze artifact and exact next gate.

- [ ] **Step 1: Generate fixed-DP K=8 candidate paths** without reading
  outcomes; hash tensors and candidate-to-segment mappings.
- [ ] **Step 2: Select scenarios deterministically** from source eligibility
  and zero-overlap only. Preserve all rejected masks/reasons.
- [ ] **Step 3: Freeze** rung, scenarios, seed, simulator/config, candidate
  hashes, baseline, SafetyCost v1, official metrics, thresholds, bootstrap,
  latency definitions, and failure rules.
- [ ] **Step 4: Independently review** zero overlap, no outcome reads,
  candidate immutability, source completeness, DP-default eligibility, and
  all scientific invariants.
- [ ] **Step 5: Run** py_compile, focused pytest, v18/v19 pointer tests, and
  `git diff --check`; commit/push and AutoDL ff-only sync.

### Task 5: Paired smoke and evidence package

**Files:**
- Reuse existing v19 adapter/bridge/worker/harness and SafetyCost v1 code.
- Modify only tested CAMP-side compatibility points and audit/status docs.

**Interfaces:**
- Consumes: the independently reviewed freeze artifact.
- Produces: descriptive/directional paired closed-loop results and evidence;
  it does not change claim taxonomy.

- [ ] **Step 1: Run one preflight** proving frozen inputs and zero prior arm
  outcomes; start only one job.
- [ ] **Step 2: Execute both arms** from matching scenario/seed/initial state.
  Baseline uses DP-default deterministic/MAP selection; CAMP only selects from
  each cycle's unchanged fixed-DP K=8 tensor.
- [ ] **Step 3: Compute frozen metrics**: SafetyCost v1 hard gates, official
  CARLA safety and trajectory metrics, selector and total planning-path
  latency, paired deltas, CVaR90, better/tie/worse, and deterministic
  10,000-replicate log/scene-cluster CI95.
- [ ] **Step 4: Independently review and seal** all results, failures, SHA
  receipts, and claim boundaries. Keep the result descriptive/directional.
- [ ] **Step 5: Update audit/status, test, commit/push, AutoDL ff-only sync, and
  stop before any promotion, deployment, activation, model replacement, or
  broad claim decision.
