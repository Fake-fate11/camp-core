# Diffusion Planner + CAMP V19 Iteration Audit

This audit is append-only. Its EOF pointer is the sole v19 controller
authority. V18 and earlier audits remain historical evidence and are not
rewritten by v19 qualification.

## Safety-first Claim Taxonomy and Controller Bootstrap

The user explicitly continued from the v18 terminal decision boundary into a
v19 safety-first evidence extension. This continuation does not reopen the
1,931-row v18 holdout, modify the fixed DP, authorize promotion/deployment, or
broaden the scope of the existing bounded offline result.

Live bootstrap checks found CAMP local, GitHub, and AutoDL synchronized on
`main` at `e80ea339425e54598218d697650304989a5c2404`. AutoDL CAMP was
tracked-clean, fixed DP was tracked-clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, and no related job was running.
The existing nuPlan mini source contained 64 SQLite DBs plus maps. No new data
was downloaded.

The v18 result is qualified with four independent claim values:

- `performance_claim=no_claim`
- `bounded_offline_safety_proxy_improvement=supported`
- `closed_loop_safety_claim=not_yet_supported`
- `broad_CAMP_over_native_DP_Top1_claim=not_supported`

The positive bounded result remains restricted to the frozen observable source
of 32 dynamic and 5 static objects. It is not complete-scene physical
feasibility, official nuPlan closed-loop safety, or real-world safety.

Candidate 0 remains the fixed-DP deterministic/MAP baseline with
`native_ranked_top1=false`. Candidate-0 equivalence cannot establish native
ranking. Before any closed-loop comparison, a read-only audit must identify the
fixed commit's executable inference/sample/ranking/default-selection path,
source hashes, selected index or output provenance, and model/config/checkpoint
identity. If no native ranking exists, the baseline must remain named
`DP-default deterministic/MAP baseline`, and the broad native-Top-1 objective
cannot be completed by renaming it.

The capability-first design and inline plan are frozen in:

- `docs/superpowers/specs/2026-07-11-v19-safety-first-evidence-extension-design.md`
  (SHA256 `c4ec98ea736d1cc2fcf8d3394d56f037f67f92899c83ecea79da5288037cddbe`)
- `docs/superpowers/plans/2026-07-11-v19-safety-first-evidence-extension.md`
  (SHA256 `1a0ac3ed11bc683948d6af05e7b026e4757170395ec90c8356a22549f6e32741`)

The next gate is read-only. It must not execute a simulator, read holdout
labels, install a large dependency stack, modify DP, or make a closed-loop or
native-Top-1 claim.

current_v19_status=v19_safety_first_claim_taxonomy_and_controller_bootstrap_passed
current_v19_artifact_scope=v19_safety_first_design_plan_claim_taxonomy_and_controller_bootstrap
current_v19_artifact=docs/superpowers/specs/2026-07-11-v19-safety-first-evidence-extension-design.md
current_v19_artifact_root_sha256=c4ec98ea736d1cc2fcf8d3394d56f037f67f92899c83ecea79da5288037cddbe
next_work_target=v19_native_baseline_provenance_and_safety_evidence_gap_read_only_audit_only

## Native Baseline Provenance and Safety Evidence Gap Read-only Audit

The read-only audit and independent review completed on AutoDL at CAMP
`5a6a09765a1c71ed7300b16bedb1dc64cf422276`; fixed DP remained
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Artifact and root SHA256:

- `/root/autodl-tmp/camp_dp_v19_native_baseline_safety_evidence_gap_5a6a0976_20260711T230539CST`
- `8d860e61165f77cc0893ad17199970f833b41be2a4d2696dd168d789f929a791`

`py_compile`, v18/v19 tests, audit execution, independent review, and diff
checks all exited `0`; pytest reported `30 passed in 2.76s` with empty stderr.
The independent review passed all 18 checks.

Fixed-DP source provenance established the source contract for its default
single-output deterministic/MAP path, but did not find a native K-ranking or
Top-1 selection path:

- decoder SHA256: `8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd`
- deterministic zero-latent tensor-converter SHA256:
  `af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7`
- default replay single-output consumer SHA256:
  `de4542fbc8685718379dbf0626499113d8bca6f7dead1c4456d2d34ffd0b9e4e`
- ROS default batch-one/item-zero path SHA256:
  `3341028ca11f45e73b7b43ab49dbf38980711f422dccfdb2f816f301443a5f53`

The accurate baseline name is therefore `DP-default deterministic/MAP
baseline`. Candidate 0 remains equivalent to the deterministic/MAP output but
is not native Top-1 provenance. `native_ranked_top1=false`,
`native_ranking_path_found=false`, and the broad native-Top-1 objective remains
unsupported. Research/training reward rankers are not relabeled as native
default inference.

The existing nuPlan root contains 64 DBs totaling `14351183872` bytes and 4
map databases. The fixed DP environment has no `nuplan-devkit` or official
nuPlan simulator module. The fixed DP repository has no nuPlan reference or
closed-loop adapter. CAMP's causal SQLite adapter is present, but it is an
open-loop source materializer, not a matched closed-loop planner harness.

Consequently `matched_closed_loop_execution_ready=false`. No simulator ran,
no holdout label was read, and no data or dependency was downloaded. No safety,
ADE/FDE/miss, or latency metric is reported by this capability-only gate.

The claim taxonomy remains:

- `performance_claim=no_claim`
- `bounded_offline_safety_proxy_improvement=supported`
- `closed_loop_safety_claim=not_yet_supported`
- `broad_CAMP_over_native_DP_Top1_claim=not_supported`

The next gate may only plan and statically review how to prove the executable
DP-default path and add an isolated CAMP-side nuPlan simulation adapter. It may
not modify DP, execute a smoke, install dependencies, or claim closed-loop
safety yet.

current_v19_status=v19_native_baseline_provenance_and_safety_evidence_gap_audit_complete_execution_not_ready
current_v19_artifact_scope=fixed_dp_native_default_source_provenance_and_nuplan_closed_loop_capability_read_only_audit_and_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_native_baseline_safety_evidence_gap_5a6a0976_20260711T230539CST
current_v19_artifact_root_sha256=8d860e61165f77cc0893ad17199970f833b41be2a4d2696dd168d789f929a791
next_work_target=v19_native_default_executable_provenance_and_nuplan_closed_loop_capability_plan_only

## Safety-first Controller Bootstrap AutoDL Verification

The bootstrap gate was independently reproduced on AutoDL after an ff-only
update to CAMP `35226fcfff6ab3aa5c32764e50a7c1ef1006ec59`; fixed DP remained
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The immutable verification artifact is:

`/root/autodl-tmp/camp_dp_v19_safety_first_controller_bootstrap_35226fcf_20260711T225917CST`

Its root SHA256 is
`d323414e252f1c122865a5ead7e0b7c5b94dff5c70b4671dc95ca11e1ecc3d3b`.
`py_compile`, the complete v18/v19 orchestrator suites, and `git diff --check`
exited `0`; pytest reported `28 passed in 2.51s` with empty stderr. The artifact
contains `HEADS`, `COMMAND`, stdout/stderr, exit code, JSON/Markdown claim
qualification, and `SHA256SUMS`. No simulator ran and no holdout label was
opened.

The local full v18 suite could not import torch because the machine-local
Anaconda environment aborts on duplicate Intel OpenMP runtimes. The unaffected
local pointer/status subset passed `5 passed`; the complete suite passed in the
fixed AutoDL environment above. No unsafe OpenMP bypass was used.

current_v19_status=v19_safety_first_claim_taxonomy_and_controller_bootstrap_passed
current_v19_artifact_scope=v19_safety_first_claim_taxonomy_controller_bootstrap_and_autodl_verification
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_safety_first_controller_bootstrap_35226fcf_20260711T225917CST
current_v19_artifact_root_sha256=d323414e252f1c122865a5ead7e0b7c5b94dff5c70b4671dc95ca11e1ecc3d3b
next_work_target=v19_native_baseline_provenance_and_safety_evidence_gap_read_only_audit_only

## Evidence-gap Entry Chronology Qualification

The preceding evidence-gap result was mechanically inserted before the
bootstrap AutoDL verification because its repeated next-target text was an
ambiguous append anchor. No prior text is removed or rewritten. This
append-only qualification records the actual chronology: bootstrap verification
completed first, followed by the read-only evidence-gap audit at
`5a6a09765a1c71ed7300b16bedb1dc64cf422276`. The pointer below is authoritative.

current_v19_status=v19_native_baseline_provenance_and_safety_evidence_gap_audit_complete_execution_not_ready
current_v19_artifact_scope=fixed_dp_native_default_source_provenance_and_nuplan_closed_loop_capability_read_only_audit_and_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_native_baseline_safety_evidence_gap_5a6a0976_20260711T230539CST
current_v19_artifact_root_sha256=8d860e61165f77cc0893ad17199970f833b41be2a4d2696dd168d789f929a791
next_work_target=v19_native_default_executable_provenance_and_nuplan_closed_loop_capability_plan_only

## Native-default nuPlan Closed-loop Capability Plan

The plan-only gate froze the smallest non-DP-mutating architecture in:

`docs/superpowers/plans/2026-07-11-v19-native-default-nuplan-closed-loop-capability.md`

Plan SHA256 is
`9c7c0ce43e8117e1ee9223ababf2a2e75687eb9fa89a9c821fe01d60757b07c7`.

The plan pins official Motional nuPlan devkit tag `nuplan-devkit-v1.2` at
`ce3c323af01c0d7ec5672f7832ef53f9c679aab0`, uses a separate Python 3.9
conda environment, and keeps the existing Python 3.12 fixed-DP environment
unchanged. A file-based NPZ/JSON bridge separates the official simulator from
the fixed-DP worker and counts bridge time in total planning-path latency.

The immutable v18 corrected14D selector root and its scales/weights hashes are
frozen. Baseline provenance must first prove executable deterministic/MAP
equivalence on an identical label-free input. CAMP remains K=8 candidate-only
selection with candidate 0 zero-noise, candidates 1-7 at noise scale 1.0,
before/after tensor hashes, and fail-closed all-K-infeasible behavior.

The proposed smoke is official nuPlan `closed_loop_nonreactive_agents`, two
zero-overlap scenarios from distinct unused logs, with seeds 3411/3412 and
bootstrap seed 3410. Its scope must remain explicit: official ego closed-loop
with nonreactive logged traffic, not reactive-traffic or real-world safety.
SafetyCost v1 remains primary; official collision/drivable-area/direction/TTC/
progress/speed/comfort metrics are additional, and ADE/FDE/miss remain
secondary.

No source was cloned, dependency installed, simulator executed, holdout label
read, or artifact deleted by this plan-only gate. The next gate is a static
review of the plan; it cannot install or execute anything.

current_v19_status=v19_native_default_executable_provenance_and_nuplan_closed_loop_capability_plan_passed
current_v19_artifact_scope=official_nuplan_v12_process_isolated_native_default_capability_and_smoke_plan
current_v19_artifact=docs/superpowers/plans/2026-07-11-v19-native-default-nuplan-closed-loop-capability.md
current_v19_artifact_root_sha256=9c7c0ce43e8117e1ee9223ababf2a2e75687eb9fa89a9c821fe01d60757b07c7
next_work_target=v19_native_default_executable_provenance_and_nuplan_closed_loop_capability_plan_static_review_only

## Native-default nuPlan Capability Plan Static Review

The plan static review passed on AutoDL at CAMP
`f4a3b699ba5cc21ef8360828b085c15a642135a4`; fixed DP remained
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Successful artifact/root SHA256:

- `/root/autodl-tmp/camp_dp_v19_native_default_nuplan_capability_plan_static_review_f4a3b699_20260711T231818CST`
- `9ed9c42deef58fd8dca3cc90a63af9b8bbcb53df63871c84da49d48b3e75d0da`

All 26 static checks passed. The v18/v19 suites reported `30 passed in 2.73s`.
The review reverified the plan SHA, official nuPlan v1.2 tag commit, isolated
Python 3.9 boundary, unchanged DP environment, file bridge, default-baseline
naming, native-Top-1 limit, K=8/no-mutation/all-K failure behavior, selector
root/scales/weights hashes, zero overlap, simulator scope, seeds, SafetyCost
claim rule, official metrics, total-path latency, conda availability, disk
threshold, and no-install/no-promotion limits.

Two retained failed review artifacts record exact-string harness false
negatives before whitespace-normalized semantic matching passed:

- `/root/autodl-tmp/camp_dp_v19_native_default_nuplan_capability_plan_static_review_f4a3b699_20260711T231611CST.tmp`
- `/root/autodl-tmp/camp_dp_v19_native_default_nuplan_capability_plan_static_review_f4a3b699_20260711T231727CST.tmp`

The plan did not change. No dependency was installed, no devkit source was
cloned, no simulator ran, and no holdout label was read. The next gate may
perform only dependency/source/disk dry-run preflight; it may not materialize
the environment or execute the adapter.

current_v19_status=v19_native_default_executable_provenance_and_nuplan_closed_loop_capability_plan_static_review_passed
current_v19_artifact_scope=official_nuplan_v12_process_isolated_capability_plan_static_review_and_failure_harness_audit
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_native_default_nuplan_capability_plan_static_review_f4a3b699_20260711T231818CST
current_v19_artifact_root_sha256=9ed9c42deef58fd8dca3cc90a63af9b8bbcb53df63871c84da49d48b3e75d0da
next_work_target=v19_nuplan_v12_isolated_dependency_and_disk_preflight_only
