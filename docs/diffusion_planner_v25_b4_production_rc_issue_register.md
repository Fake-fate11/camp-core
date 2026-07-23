# V25 B4 production RC issue register

This register is frozen for the single B4 production-RC engineering stage.  It
does not add a scientific gate or change the fixed DP, K8, trajectory, atom,
model, threshold, NI, multiplicity, evaluation, or claim contracts.

| ID | Priority | Failure signature | Required closure | Status |
| --- | --- | --- | --- | --- |
| B4-RC-001 | P0 | `validate_v25_zero_overlap()` body became unreachable after the B3 validator definition | Restore independent function bodies and direct/caller tests | implementation and local regression complete; AutoDL suite pending |
| B4-RC-002 | P0 | Real candidate0 native receipt and pool consumer disagree on required K8 fields | One versioned actual-native ABI with distinct candidate0 primary/supplementary branches | implementation and ABI mutations complete; production canary pending |
| B4-RC-003 | P0 | Producer and reviewer share a projector/helper and can self-confirm the same defect | Reviewer reads the ABI declaration but independently parses and recomputes evidence | independent parser/recompute implemented; production canary pending |
| B4-RC-004 | P0 | Prior production preflight did not instantiate every real native branch | Same production entrypoints, raw callback, three scenario classes, 3 arms x 64 ticks | authority/plan/certificate implemented; production canary pending |
| B4-RC-005 | P0 | Release reservation and first scientific exposure are conflated | Separate operational-attempt and scientific-exposure ledgers with atomic transitions | implementation and state-machine mutations complete; production canary pending |
| B4-RC-006 | P1 | A renamed source family can be mistaken for independent provenance | Record common generator provenance; prove independence using geometry/export/semantic clone hashes | implementation and local regression complete; B4 pre-open review pending |
| B4-RC-007 | P1 | Native field access can outgrow the ABI without a failing test | Static consumer inventory plus required/extra/type/shape/cross-branch mutations | implementation and local ABI regression complete; AutoDL suite pending |
| B4-RC-008 | P1 | Raw receipt or tensor evidence can be lost before projection failure | Persist and seal raw/preprojection evidence before comparison/projection | implementation and independent mutation regression complete; production canary pending |
| B4-RC-009 | P1 | Independently selected real signal branches can share one route identity and violate the route-asset denominator | Select the lexicographically first route-distinct real fixture combination and reject an unavailable combination | implementation and AutoDL focused regression complete; production canary pending |
| B4-RC-010 | P1 | Production-RC wrapper accepted a canary CAS root but delegated it to a legacy validator that only permits the live canonical CAS | Validate the discarded legacy field against its canonical placeholder while binding all production-RC operational/scientific ledgers to the caller's exact isolated CAS root | implementation and AutoDL focused regression complete; production canary pending |
| B4-RC-011 | P0 | The actual native arm callback validated a production-RC release/exposure receipt with the legacy holdout release/consumption validators | Dispatch on the frozen release schema and normalize only the common pre-forward one-time-state predicates | implementation and focused regression pending |
| B4-RC-012 | P0 | The mapped-signal ABI required both route and map row lists to be nonempty even though the frozen producer permits either side to be empty; a validator failure also occurred before the supplementary raw receipt was persisted | Match the frozen combined-nonempty row semantics, bind IDs/content SHA/phase/count independently, and invoke a strict-copy raw-receipt sink before validation | implementation and focused regression pending |
| B4-RC-013 | P0 | The execution wrapper appended logical decision-evidence references to a validated raw native receipt and then passed the enriched object back through the raw-header ABI | Strip and type-check the exact two storage-enrichment fields before raw ABI validation while preserving the enriched sealed receipt for storage review | implementation and focused regression pending |

The production-equivalence certificate is created only after all critical
implementation work is complete.  After the certificate, critical code is
frozen; only the existing pointer/audit documentation allowlist may change.
