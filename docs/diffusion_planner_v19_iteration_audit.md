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
