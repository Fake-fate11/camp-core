# V19 Closed-loop Smoke Speed-complete Reselection Design

## Decision

Replace the two frozen Singapore smoke scenarios because their official live
route objects expose no `speed_limit_mps`. This is an input-source correction
before simulator or metric execution, not result-based scenario selection.

The replacement remains exactly two scenarios: one normal bucket and one
interaction bucket. It must not read expert futures, labels, prior safety
outcomes, trajectory-quality outcomes, or latency results.

## Frozen Inputs

- Existing nuPlan mini data only; no download.
- Selection seed `3411`.
- Priority hash exactly
  `sha256("3411|bucket|log_token|scene_token|scenario_token")`.
- The existing normal/interaction tag rules, three-second past coverage,
  eight-second future timestamp coverage, mission goal, and nonempty mission
  route rules remain unchanged.
- Every log and scene in the frozen v18 causal manifest at SHA256
  `703a47bec14d9ee4605184618e6bb61b6a4ce4ed73bee4173df508d6a6dfa5e5`
  remains excluded. Selected logs and scenes must be mutually distinct.
- Source eligibility uses two deterministic tiers: existing unseen Las Vegas
  and Pittsburgh logs first, then existing unseen Boston logs only for a
  bucket with no eligible first-tier candidate. Singapore is excluded by the
  already-reviewed `0/2001` complete-speed-source inventory. Selection fails
  closed if the two tiers cannot supply both buckets.

## New Eligibility Gate

For each candidate in ascending priority order, construct the official
`NuPlanScenario`, call `Simulation.initialize()` and
`Simulation.get_planner_input()`, anchor the existing connected route window at
the current roadblock, and inspect the at-most-25 lane/lane-connector objects
consumed by the causal adapter. Every selected route slot must have finite,
strictly positive official `speed_limit_mps`.

Zero, current ego speed, statutory defaults, `100 m/s`, nearby-lane routes,
and any other fallback remain forbidden. A missing speed source is a retained
eligibility rejection.

## Freeze and Review

Within each bucket, the lowest source tier containing an eligible candidate is
used, then candidates are ordered by the unchanged priority hash. The gate
writes the complete candidate audit, ordered rejection reasons, two
selected records, exclusion receipts, and a replacement `smoke_config.json`.
The replacement config must be byte-equivalent in parsed content to the prior
config except for `selected_scenarios`.

An independent review must recompute selection hashes, prove that every lower
tier was exhausted and every lower-priority candidate in the chosen tier was
ineligible or conflicted with the distinct-log rule,
recheck log/scene zero overlap, reconstruct both official route windows, verify
all route speeds, and confirm that no simulator runner, planner compute,
worker, metric, holdout, label, or outcome was accessed.

Only after the independent review passes may the live v19 controller advance
back to the real-source execution preflight. SafetyCost v1, metrics, thresholds,
seeds, baseline provenance, selector artifacts, and all claim boundaries stay
unchanged.

## Rejected Alternatives

- A location allowlist without checking official route objects is insufficient.
- Filling missing speeds would violate the causal source contract.
- Selecting after observing simulator or metric outcomes would contaminate the
  experiment and is forbidden.
