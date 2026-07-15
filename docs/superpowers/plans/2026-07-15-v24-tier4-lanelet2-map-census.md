# v24 TIER IV Lanelet2 map census plan

## Objective and frozen input

Advance Branch B independently after Branch A's source-local failure. The sole
input is the sealed v23 source payload/root
`/root/autodl-tmp/camp_dp_v23_source_license_freeze_retry2_51c97eb2_20260715T172832CST`
/
`c49f129f092497f6eb30cf887cf3bfbf36fc924244055ada0d0ff221d5ab3265`.
Its exact TIER IV `scenario_simulator_v2` commit is
`e22f01093fa6516c0552549ada302270329c59a4`, with 14 path receipts / 12
unique byte blobs under Apache-2.0 and root NOTICE absent at the commit.

No additional map source is allowed. Source payloads are read-only. No relation
or subtype is rewritten, no map is sanitized, and filenames are not evidence
of independent geography.

## Static census contract

The standard-library census first verifies the frozen manifest, commit, URL,
license, path count, blob count, per-path SHA256, and byte length. It then
records for every path, including duplicates and failures:

- XML validity and exact failure reason;
- regulatory subtype counts and lanelet attachments;
- latitude/longitude bbox;
- translation- and ID-invariant way geometry at frozen `1e-8` degree
  quantization;
- ID-invariant lanelet topology using boundary geometry, member roles,
  regulatory subtype attachments, and semantic lanelet tags;
- node/way/relation/lanelet and missing-reference counts;
- explicit speed tags/regulatory sources and traffic-control sources; and
- pending fixed-builder and route-support status.

Map-family count remains unset during raw census. The report exposes byte-blob,
geometry, and geometry-plus-topology cluster candidates for later reviewed
family adjudication. Configuration variants and ROS/no-ROS copies are not
promoted to independent map families by path name or file count.

Malformed XML, a source mismatch, absent geometry, or unsupported content
creates a per-path receipt; all 14 paths remain in the denominator. No result,
label, route quality, simulator outcome, or holdout data is read. The route
threshold is frozen outcome-blind at `>=80m`, but route generation is a later
gate.

## Fixed-builder smoke

After static census review, run one isolated process per unique byte blob so a
process-local projection module cannot leak between maps. Each process must:

1. rehash source bytes before load;
2. call the existing regulatory preparation gate before the existing no-ROS
   projection fallback;
3. construct the stock fixed-DP `LaneletSceneBuilder` without a route, model,
   checkpoint, candidate, or outcome action;
4. record stdout, stderr, exit code, detected unsupported subtype/projection
   cause, and observable builder layer counts; and
5. rehash source bytes after load.

Byte-identical paths inherit the one blob execution receipt but still receive
separate path receipts. A successful blob is not rerun under its duplicate
path. An unsupported element excludes only that map; remaining maps continue.
No relation or subtype is rewritten, and fixed DP remains tracked-clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

## TDD, evidence, and continuation

Unit tests cover exact path/blob accounting, coordinate normalization, ID
invariance, regulatory/speed/control sources, per-map XML/hash failure, output
immutability, and the unset map-family boundary. Local and AutoDL run focused
pytest, py_compile, and diff checks.

The preflight and execution artifacts contain HEADS, COMMAND, stdout, stderr,
JSON, Markdown, SHA256SUMS, ROOT_SHA256SUMS, disk floor, task census, source
root verification, and DP immutability. If at least one map remains builder-
loadable, proceed outcome-blind to reviewed family adjudication and route
census. Only after every authorized source finishes map/route/K=8 accounting
may zero support authorize a global stop.
