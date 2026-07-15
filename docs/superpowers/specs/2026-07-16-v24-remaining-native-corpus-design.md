# v24 Remaining Native Corpus Design

## Scope

Complete the frozen train-corpus namespace after the reviewed seed-24001 pilot.
This gate may design, test, and statically preflight the work. It must not load
the model, run the simulator, generate candidates, consume outcomes, train, or
open calibration or holdout.

## Frozen inputs

- Corpus preflight root:
  `17b5a8ca7c974997b1cd89905b50e86e95f5a032cab171e44898c48973867e72`.
- Corpus static-review root:
  `fe69c61e9da0a11233bb6c5862e2becc8fddb4e1e8e133c60cb21e80a5efe6db`.
- Seed-24001 pilot root:
  `f8cce7a9fd2b26583241aa53ed5886dc0a87c45d8ffcff89dc01a0421fa270be`.
- Pilot independent-review root:
  `e6794589ef5319879b84543b0d046d9814519d953effb89233f91779fb4e8101`.
- Fixed DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The pilot review alone authorizes the next phase. Its decision must remain
`authorized=true`, name exactly seeds `24002-24005`, name the exact sorted 375
route keys, require denominator preservation, forbid route removal/replacement/
reordering, and keep tuning, outcome, calibration, holdout, and claims closed.

## Execution contract

The remaining phase is `main_completion_remaining_frozen_seeds`. It contains
the same 375 train routes and exactly four seeds, yielding 1,500 route-seed
runs. Order is frozen as route `record_key` ascending, then seed ascending.
Every run allows at most 64 native ticks and captures every available tick, so
the theoretical maximum is 96,000 causal fixed-DP K=8 snapshots.

All routes remain in the denominator for every seed. In particular, the 153
pilot routes without a positive source speed remain scheduled and must produce
retained failure receipts if the same source boundary recurs. Pilot outcomes
cannot remove, replace, reorder, tune, or otherwise alter a row.

The existing pilot entry points remain compatible. Shared row validation and
execution mechanics are parameterized; pilot wrappers retain their existing
schemas and filenames. The remaining phase writes a separate artifact with its
own lock, progress, receipts, snapshots, summary, seal, and source-root chain.
It never mutates or resumes inside the sealed pilot artifact.

## Fail-closed boundaries

Static preflight fails before runner construction if any source root, manifest
SHA, DP HEAD/status, route order, seed namespace, review decision, route asset,
source map, disk floor, or closed-boundary flag differs. Remaining execution
requires a unique nonblocking artifact lock and refuses an existing output
unless explicit same-artifact resume is requested. Resume accepts only matching
route/seed receipts retained in the denominator.

Free disk is checked before and after each row. Reaching the 10 GiB floor seals
a terminal `stopped_disk_floor` result and does not authorize another task.
Ordinary per-route failures are retained and execution continues.

## Evidence and next gate

This gate emits a separate sealed static-preflight artifact containing HEADS,
COMMAND, JSON, Markdown, stdout/stderr, run.exit, SHA256SUMS, and
ROOT_SHA256SUMS. The next gate is an independent review of this preflight. Only
that review may authorize one unique remaining-seed execution.
