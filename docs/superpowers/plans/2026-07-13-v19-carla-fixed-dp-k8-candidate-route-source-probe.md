# V19 CARLA Fixed-DP K8 Candidate-Route Source Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate real unchanged fixed-DP K=8 candidate paths from source-only CARLA ticks and determine the first A/B/C rung with legal paired-smoke support.

**Architecture:** Reuse the v19 bridge, fixed-DP worker `source_probe`, causal materializer, and exact-speed census. Add only a thin CARLA snapshot adapter and one source-probe harness; CARLA and DP remain separate processes/environments joined by immutable bridge directories.

**Tech Stack:** CARLA 0.9.16 cp312 client in an isolated extracted wheel root, CAMP Python 3.9 adapter/tests, existing DP Python 3.12 worker, JSON/NPZ/SHA artifacts.

## Global Constraints

- No simulator outcome, planner-arm advancement, metric, label, holdout, or scenario selection input enters this probe.
- Fixed DP remains `7a1d33da277a1992ec474b5383a0c963c72e04e4`; K=8 tensors are hashed before/after and never modified.
- Rungs are tested A then B then C. A is already independently exhausted at map level; B must be tested before C.
- DP-default candidate 0 must be source-complete. All-K-ineligible records retain masks/reasons and are excluded.
- Maintain seed 3411, 3+8 history/evaluation contract, 10 GiB floor, one job/staging/final, and unchanged claim taxonomy.

---

### Task 1: Thin CARLA causal snapshot adapter

**Files:**
- Create: `camp_core/camp_core/integrations/carla_causal_adapter.py`
- Create: `camp_core/tests/test_carla_causal_adapter.py`

**Interfaces:**
- Consumes: 31 source-only 0.1 s ego/actor snapshots, mission goal, route
  waypoints, lane boundaries/topology, traffic-light state, and ladder speed
  index.
- Produces: `CausalDPMaterialization` matching the existing fixed-DP schema and
  a candidate-to-OpenDRIVE projection context; no future/outcome fields.

- [ ] Write failing tests for exact 3 s history, timestamp uniformity, 32 dynamic
  and 5 static observable caps, route/lane IDs, traffic-light timestamp, global
  SE(2) invariance, future-field rejection, and unavailable speed masks.
- [ ] Reuse `materialize_causal_dp_input`; implement only CARLA attribute-to-
  existing-context conversion. Do not duplicate tensor normalization or DP code.
- [ ] Run Python 3.9 py_compile and target pytest locally and on AutoDL.
- [ ] Commit/push and ff-only sync the adapter checkpoint.

### Task 2: Source-only CARLA/DP bridge harness

**Files:**
- Create: `scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py`
- Create: `camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py`

**Interfaces:**
- Consumes: CARLA snapshot adapter output and existing bridge/worker CLIs.
- Produces: immutable per-tick request/response, K=8 tensor SHA, candidate
  OpenDRIVE segments, B/C masks/reasons, and zero-outcome counters.

- [ ] Test one-job enforcement, forbidden outcome fields, fixed heads, seed,
  candidate SHA equality, candidate-0 eligibility, all-K fail-closed, and no
  selection or metric output.
- [ ] Extract the official cp312 wheel once into
  `/root/autodl-tmp/camp_v19_carla_client`; verify import and SHA without
  modifying DP or the nuPlan Python 3.9 environment.
- [ ] Implement the harness as orchestration of existing bridge, worker
  `source_probe`, and exact-speed census; do not add another worker.
- [ ] Seal the implementation/preflight artifact and independently review it.

### Task 3: Ordered candidate-route census and freeze

**Files:**
- Evidence under `/root/autodl-tmp/camp_dp_v19_carla_*`.
- Modify only audit/current-status pointer and its regression test.

**Interfaces:**
- Consumes: deterministic source-only CARLA ticks and real fixed-DP K=8 paths.
- Produces: first independently reviewed supported rung and frozen source-only
  scenario set, or a hard-stop exhaustion artifact.

- [ ] Start one CARLA source-probe job; collect 3 s history without evaluating
  either arm or computing any outcome.
- [ ] Run B candidate-route census first. If it has a legal paired smoke,
  independently review and freeze B without running C.
- [ ] Only if B has zero legal pair, run and independently review C. If C also
  has zero support, stop at the authorized all-three-rungs boundary.
- [ ] Before any arm advances, freeze scenario/run keys, zero overlap, source
  rung, K=8 candidate hashes, baseline, seed, simulator/config, metrics,
  thresholds, bootstrap, latency definitions, and failure rules.
- [ ] Run focused tests, v18/v19 pointer tests, diff check, artifact SHA review,
  commit/push, AutoDL ff-only sync, and reread EOF.
