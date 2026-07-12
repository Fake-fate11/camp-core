# V19 Persistent Safety-Evidence Controller Design

## Decision

Keep the existing v19 audit EOF as the only controller state and add two
bounded persistence mechanisms:

1. a pre-outcome source-protocol ladder that may advance without repeated
   user approval; and
2. an hourly heartbeat that wakes the existing v19 task after an external job
   finishes.

No new general controller framework is introduced. The design exists to avoid
freezing unsupported scenario choices one at a time while preserving the
scientific boundary between source discovery and evaluation.

## Goals

- Exhaust source feasibility before freezing an evaluation protocol.
- Continue automatically through ordinary plan, review, TDD, preflight, and
  existing-data smoke gates.
- Avoid duplicate installs, fetches, simulator runs, and metric executions.
- Preserve fixed-DP, fixed-candidate, affine-score, simplex, convex-master,
  zero-overlap, and no-outcome-training contracts.
- Stop only at a real scientific, resource, or deployment decision.

## Non-goals

This controller does not authorize:

- invented or default route speeds;
- DP code, configuration, weight, checkpoint, or environment changes;
- trajectory generation, repair, blending, or postselection;
- atom-schema, selector-weight, or training-objective changes;
- v18 holdout reopening;
- new large data acquisition, Full36, or formal seeds 11/12/13;
- promotion, deployment, activation, model replacement, or broad claims.

## Authority And State

The live EOF of `docs/diffusion_planner_v19_iteration_audit.md` remains the
sole next-gate authority. `docs/diffusion_planner_current_status.md` mirrors
its latest tuple. Local, GitHub, and AutoDL CAMP heads plus the fixed DP head
must agree before each mutating gate.

The controller has these phases:

```text
DISCOVERY
  -> SOURCE_SUPPORT_CENSUS
  -> PROTOCOL_SELECTION
  -> FREEZE_REVIEW
  -> EXECUTION
  -> RESULT_REVIEW
  -> TERMINAL_OR_SCALEUP
```

Ordinary gate completion does not end the persistent goal. After verification,
artifact sealing, audit update, commit/push, and AutoDL ff-only sync, the task
rereads the EOF and continues.

## Source-Support Census

Before selecting replacement smoke scenarios, perform one exhaustive,
read-only census over every existing-data scene not excluded by the frozen v18
log/scene manifests. The census records, by official tag, location, log, and
scene:

- three-second history and eight-second future timestamp availability;
- mission-goal and route availability;
- route uniqueness and connectivity;
- official finite positive route-speed coverage;
- full-window and candidate-local speed-source availability;
- zero-overlap eligibility; and
- exact rejection reason counts.

The census may construct official scenario objects and perform source-only
fixed-DP candidate probes. It may not advance either simulation arm, compute a
safety or trajectory metric, read expert/holdout labels, tune a selector, or
use any evaluation outcome in protocol selection.

## Pre-outcome Protocol Ladder

The controller selects the first rung with an independently reviewed valid
pair: both required buckets must be populated by two scenarios from distinct
logs/scenes. Every rung keeps two scenarios, deterministic seed `3411`, the
existing fixed-DP/selector artifacts, SafetyCost formula, metrics, thresholds,
and no-result-driven-selection rule.

### Rung 1: Full-window Exact Speed

Use an explicitly enumerated official non-interactive tag whitelist for the
first bucket and the existing interaction whitelist for the second. Every
route slot consumed by the adapter must have a finite positive official
`speed_limit_mps`.

### Rung 2: Candidate-local Exact Speed

Keep the same honest bucket names, but require real speed only on route
segments geometrically used by each fixed-DP candidate. A candidate touching
an unknown-speed segment is source-ineligible. A record with no eligible K=8
candidate fails closed. No zero, ego-speed, statutory-default, nearby-lane, or
large-value fallback is allowed.

The DP-default candidate must also be source-complete for a paired record to
enter evaluation.

### Rung 3: Interaction-only Smoke

If no non-interactive support exists, use the candidate-local exact-speed rule
from Rung 2 and select two source-complete interaction scenarios from distinct
official tag families and distinct logs. The artifact must call them
interaction scenarios; it may not relabel either as `normal`.

### Exhaustion

If all three rungs have zero support, stop once with a complete support matrix.
Continuing then requires a new data scope or an atom/source-contract decision;
the controller may not invent another rung.

## Freeze Boundary

Scenario identities, bucket semantics, route-speed rule, seeds, metrics,
thresholds, baseline provenance, and claim criteria become immutable before
the first closed-loop arm advances or any evaluation metric is computed.

Source-only scenario construction and candidate probes performed during the
census are not evaluation outcomes, but their identities, commands, and hashes
must be retained. Once either arm advances, no scenario replacement or
protocol-ladder transition is allowed, even if the result is unfavorable.

## Long-running Jobs And Heartbeat

Create one hourly heartbeat attached to the existing v19 task.

- If the task is active, the heartbeat does nothing.
- If one authorized external process is running, it reports PID, progress,
  stderr tail, output/staging state, and disk headroom without restarting it.
- If the process completed and the task is idle, it sends one continuation
  message containing the fresh evidence and current EOF.
- If no process exists but a transient sync failed, it permits only the
  bounded retry policy below.
- It stores the last observed EOF/artifact/job identity and does not send the
  same continuation twice.
- It stays silent while the EOF is a genuine `user_decision_required` or
  terminal boundary and is paused when the v19 goal completes.
- It never executes a simulator, changes protocol, deletes data, or makes a
  claim by itself.

The paused historical `nuplan-mini` download automation is not reused because
its prompt and evidence contract target the completed v18 acquisition.

## Retry And Failure Policy

- Network fetch/download failures: at most two evidence-preserving retries,
  with AutoDL network turbo enabled before each attempt.
- Wrapper/import/path mistakes: minimal TDD repair and rerun of the same gate
  only when formulas, protocol, candidates, and outputs are unchanged.
- Running job: monitor only; never mark blocked merely because work is slow.
- Source-support failure before evaluation: advance to the next frozen ladder
  rung after independent review.
- Evaluation failure after freeze: retain the result and stop; do not change
  the protocol or select a replacement scenario.
- The goal is marked blocked only after the same genuine external or
  user-decision condition repeats for the required consecutive turns.

## Verification And Evidence

Every gate retains the existing evidence shape:

- `HEADS`, `COMMAND`, stdout, stderr, and exit status;
- machine-readable summary plus concise Markdown review;
- `SHA256SUMS` and root digest;
- local and AutoDL `py_compile`, focused pytest, v18/v19 pointer tests, and
  `git diff --check`;
- tracked-clean CAMP/fixed-DP/nuPlan source state; and
- free bytes above the 10 GiB floor.

The source census and each selected ladder rung receive independent read-only
review before the freeze pointer advances.

## Success Criteria

The controller is successful when:

1. routine gates continue without repeated user approval;
2. long-running jobs resume through the heartbeat without duplicate starts;
3. the closed-loop protocol is frozen only after a nonzero, independently
   reviewed source-support set exists; and
4. unsupported data produces one complete decision artifact instead of a
   sequence of narrowly discovered blockers.
