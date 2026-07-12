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

## nuPlan v1.2 Isolated Dependency and Disk Preflight

The dependency/source/disk preflight passed on AutoDL at CAMP
`bfca4fa391e52be830b1bd7f95ee93074bdbbc10`; fixed DP remained
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Successful artifact/root SHA256:

- `/root/autodl-tmp/camp_dp_v19_nuplan_v12_isolated_dependency_disk_preflight_bfca4fa3_20260711T232437CST`
- `0a61e0f050a97f91aa59e2697ed125fe1db77ec1d9a92755c1260beb2c973a27`

The official tag resolved to
`ce3c323af01c0d7ec5672f7832ef53f9c679aab0`. Official environment,
requirements, lock, torch-requirements, torch-lock, and license metadata were
captured. A fresh-prefix Python 3.9/pip 21.2.4 conda dry-run succeeded with a
base download estimate of `38365428` bytes.

Free bytes were `16221544448`. The frozen environment/source/failed-plus-
successful-smoke reserve is `5000000000` bytes, leaving projected free bytes
`11221544448`, above the `10737418240`-byte 10 GiB hard floor.

The first retained preflight staging root failed only because machine-level
conda configuration pointed at a malformed TUNA `pkgs/free/noarch` repodata
source:

`/root/autodl-tmp/camp_dp_v19_nuplan_v12_isolated_dependency_disk_preflight_bfca4fa3_20260711T232029CST.tmp`

The successful retry used command-local `--override-channels -c conda-forge`;
it did not modify global conda configuration. The isolated environment and
devkit roots remain absent. No package was installed, source cloned, simulator
run, or holdout label read.

current_v19_status=v19_nuplan_v12_isolated_dependency_and_disk_preflight_passed
current_v19_artifact_scope=official_nuplan_v12_dependency_metadata_conda_dry_run_and_10gib_disk_preflight
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_v12_isolated_dependency_disk_preflight_bfca4fa3_20260711T232437CST
current_v19_artifact_root_sha256=0a61e0f050a97f91aa59e2697ed125fe1db77ec1d9a92755c1260beb2c973a27
next_work_target=v19_nuplan_v12_isolated_dependency_and_source_materialization_only

## nuPlan v1.2 Isolated Materialization Failure Result Review

Materialization failed closed on AutoDL at CAMP
`7a2bdad6d6d419dbd3852e128a45d766b4046679`; fixed DP remained
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`, and the official
nuPlan source remained tracked-clean at
`ce3c323af01c0d7ec5672f7832ef53f9c679aab0`.

The independently verified failure artifact and review are:

- `/root/autodl-tmp/camp_dp_v19_nuplan_v12_isolated_dependency_source_materialization_retry6_7a2bdad6_20260712T113131CST.tmp`
- `eec658bc9652d18fdbb19bff1d3b8b1cd1b5760159f4342ae6764dfc9fe863e7`
- `/root/autodl-tmp/camp_dp_v19_nuplan_v12_isolated_dependency_source_materialization_failure_result_review_7a2bdad6_20260712T114713CST`
- `b7c7cf03df5e115d0ee9830ae034ceb0c9819905012ad8b8ec1a1d9a4cad103f`

All source-artifact SHA256 entries passed and its recorded root matched the
independently computed root. Preconditions, the derived official hash-locked
torch runtime subset, and the official main lock exited zero. The runtime
subset removed only the repository-unreferenced `torch_scatter` requirement;
it did not override the drifted upstream wheel hash. Its scope review root is
`c77106e63a1d77fe0a31e97ae2e9ca04d0d6d4da711fde333c3bf74ebdf7f524`.

Free space fell from `16016338944` bytes to `11217469440` bytes after the
torch runtime lock and then to `9593786368` bytes after the main lock. The
artifact recorded `9593782272` final free bytes, `1143635968` bytes below the
frozen `10737418240`-byte floor. The gate therefore skipped devkit install,
import smoke, and pip check and set `passed=false` / `overall=1`.

Independent read-only `pip check` found two additional official lock-union
conflicts: tensorboard 2.9.1 requires protobuf below 3.20 while the main lock
installed protobuf 3.20.2, and pytorch-lightning 1.3.8 requires PyYAML at most
5.4.1 while the main lock installed PyYAML 6.0. The isolated environment is
`6453283272` bytes. No nuPlan devkit was installed, no simulator ran, no
holdout label was read, and no CAMP/DP/source tracked file changed.

No retry or destructive cleanup is authorized while free space is below the
hard floor. Continuing requires a user decision to add disk or remove/recreate
the isolated environment, followed by a frozen runtime dependency-union
remediation. Claim qualification is unchanged:
`performance_claim=no_claim`,
`bounded_offline_safety_proxy_improvement=supported`,
`closed_loop_safety_claim=not_yet_supported`, and
`broad_CAMP_over_native_DP_Top1_claim=not_supported`.

current_v19_status=v19_nuplan_v12_isolated_dependency_source_materialization_failed_closed
current_v19_artifact_scope=official_nuplan_v12_hash_locked_runtime_subset_materialization_failure_disk_floor_and_dependency_union_result_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_v12_isolated_dependency_source_materialization_failure_result_review_7a2bdad6_20260712T114713CST
current_v19_artifact_root_sha256=b7c7cf03df5e115d0ee9830ae034ceb0c9819905012ad8b8ec1a1d9a4cad103f
next_work_target=user_decision_required_before_v19_nuplan_environment_cleanup_or_disk_expansion_and_runtime_dependency_union_remediation

## Exact Environment Cleanup and Minimal Runtime Lock Static Review

The user explicitly resumed the blocked v19 goal and authorized recursive
deletion of only `/root/autodl-tmp/camp_v19_nuplan_env`. Before deletion, the
resolved path matched exactly, no process used the environment, CAMP/fixed-DP/
official-source heads were tracked-clean, and every required preserved path
existed. The successful pre-delete artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_nuplan_env_cleanup_predelete_64b9ce08_20260712T131237CST`
- `971a3df09549cbde6f7d697cbf2db4ddc3afc62e38ad35e095f0a110ba788086`

It records the `6453283272`-byte failed prefix, `pip check` exit 1, absent
`nuplan-devkit`, and zero using processes. A retained failed pre-delete harness
artifact/root records that the host had no `python3` command; no deletion had
occurred at that point:

- `/root/autodl-tmp/camp_dp_v19_nuplan_env_cleanup_predelete_64b9ce08_20260712T131146CST.tmp`
- `95919285329bfd507b9836701cbabadbc6a5c7977ef0077823ff7ca0314f51f2`

The exact literal command deleted no other path. Free bytes rose from
`9593208832` to `16179240960`, an observed release of `6586032128` bytes, and
the four required keep paths remained present. The cleanup artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_nuplan_env_cleanup_execution_64b9ce08_20260712T131317CST`
- `d57abac9a58a018830656a70d8a4a9f139649c0a232d65b09ec589d5c07916b8`

The approved recovery design and implementation plan are:

- `docs/superpowers/specs/2026-07-12-v19-nuplan-minimal-runtime-rebuild-design.md`
  / `98cddcec8459044e8044bf657527d6c0b60e4d30089406389686cd696da514fa`
- `docs/superpowers/plans/2026-07-12-v19-nuplan-minimal-runtime-rebuild.md`
  / `a20ce962dd076f76bcdf2b9c2e134c8fc2fa8b2f819f8a33d8831fcabab7577c`
- frozen direct requirements SHA256:
  `923916b53d2a4dccc7a528e9bea98aa510dee9f81454545c805672e24e7c68b7`

The design keeps the official Python 3.9 simulator separate from the unchanged
Python 3.12 fixed-DP worker. Static import closure over 139 official nuPlan
modules proved that direct use of `Simulation`, `SimulationRunner`,
`PerfectTrackingController`, `TracksObservation`,
`StepSimulationTimeController`, and `MetricsEngine` does not require torch or
PyTorch Lightning. It avoids the top-level `run_simulation.py` orchestration
import without changing official simulator component implementations.

Two retained static-review failures document harness provenance rather than
dependency changes. The first used AutoDL's incomplete Aliyun pip mirror; the
second used a Python 3.12 cross-resolver that evaluated SciPy's
`Requires-Python` against itself. No environment was created:

- `/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_lock_static_review_98bb53c2_20260712T132240CST.tmp`
  / `7c66cd4a2564a7717a22371a60d65c2dee69004f2416e4f98268eb35df9a6cbc`
- `/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_lock_static_review_ad350fb3_20260712T132434CST.tmp`
  / `5e52a9cc30dd7c0d4fa1ca9f44625a53ca2c3b8a9f918c9f1ae94ab002022107`

The successful review used the existing read-only Python 3.9 resolver with
`--isolated` and official PyPI. Its artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_lock_static_review_ff375430_20260712T132719CST`
- `b0e7a4188e53d325ee9b285bcccc2960a495f51846b3695ac36643e8194c45de`

Independent recomputation passed all 15 SHA entries and matched the root. The
lock contains 65 wheel-only, SHA256-complete packages from 24 frozen direct
requirements; forbidden packages, protobuf, and PyYAML are absent. Estimated
download bytes are `240753441`; current free minus the frozen 5 GB reserve is
`11177954816`, above the `10737418240` hard floor. The exact target remains
absent. No simulator ran, no holdout was accessed, and claim qualification is
unchanged.

current_v19_status=v19_nuplan_v12_environment_cleanup_and_minimal_runtime_lock_static_review_passed
current_v19_artifact_scope=exact_single_environment_cleanup_and_torch_free_python39_wheel_lock_static_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_lock_static_review_ff375430_20260712T132719CST
current_v19_artifact_root_sha256=b0e7a4188e53d325ee9b285bcccc2960a495f51846b3695ac36643e8194c45de
next_work_target=v19_nuplan_v12_minimal_runtime_materialization_only

## Minimal Runtime Materialization Result Review

The single authorized materialization completed without a second install
attempt. Its immutable artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_materialization_d85ea23b_20260712T133356CST`
- `816367a0eec1b0e0563a1d09c0b8b988f9d407bef3f99678bd01ebc2d1f83f8c`

All 22 entries in `SHA256SUMS` passed and the independently computed
`sha256(SHA256SUMS)` matched both the recorded and expected root. Conda base,
reviewed 65-wheel runtime lock, and fixed-source installs all exited zero.
The final artifact records:

- `pip_check_exit=0`, with `No broken requirements found`;
- `import_exit=0` for scenario builder, sequential worker, official
  `Simulation`/`SimulationRunner`, perfect tracking, tracks observation,
  metric engine, collision, TTC, drivable-area, speed, comfort, progress, and
  driving-direction metric modules;
- `forbidden_check_exit=0`, with no torch, Lightning, training stack,
  protobuf, or PyYAML package;
- environment bytes `1035920810`;
- final outcome free bytes `15082639360`, above the `10737418240` hard floor;
- `no_simulator_run=true` and `no_holdout_access=true`.

The independent result review reran the artifact hashes, `pip check`, all 17
official import probes, forbidden-package inspection, resolved-path/disk
checks, related-process count, and CAMP/fixed-DP/source HEAD/tracked status.
It observed `15082561536` free bytes and zero related processes. Its immutable
artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_materialization_result_review_d85ea23b_20260712T160605CST`
- `4bad5fa9fe5e00033860870a6b0eafe50c8e3e195eea0d74c46430bfdc516031`

The first read-only review harness exited before creating staging because
`pipefail` treated the expected zero-process `grep` result as failure. The
successful review records that qualification and explicitly handles zero
matches. It ran no installer and did not modify the environment.

Materialization establishes simulator capability only. It adds no safety,
ADE/FDE/miss, or latency result and does not change the claim taxonomy:

- `performance_claim=no_claim`
- `bounded_offline_safety_proxy_improvement=supported`
- `closed_loop_safety_claim=not_yet_supported`
- `broad_CAMP_over_native_DP_Top1_claim=not_supported`

The next smallest gate may only write and statically review the CAMP-side
adapter plus executable DP-default deterministic/MAP provenance TDD plan. It
may not execute a simulator, call candidate 0 native ranked Top-1, modify DP,
open a holdout, or make a closed-loop claim.

current_v19_status=v19_nuplan_v12_minimal_runtime_materialization_result_review_passed
current_v19_artifact_scope=official_nuplan_v12_torch_free_python39_runtime_materialization_and_independent_result_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_materialization_result_review_d85ea23b_20260712T160605CST
current_v19_artifact_root_sha256=4bad5fa9fe5e00033860870a6b0eafe50c8e3e195eea0d74c46430bfdc516031
next_work_target=v19_nuplan_v12_adapter_and_executable_default_provenance_tdd_plan_only

## nuPlan Adapter and Executable DP-default Provenance TDD Plan Static Review

The plan-only gate froze the minimum CAMP-side implementation at:

- `docs/superpowers/plans/2026-07-12-v19-nuplan-adapter-default-provenance-tdd.md`
- plan SHA256 `2777b7bb6920a9a968f27f3a296be0f563c7e6a19d6b538da60f56948d3a5a27`

It reuses the passed minimal runtime and independent review without reinstalling
or launching another materialization:

- runtime root `816367a0eec1b0e0563a1d09c0b8b988f9d407bef3f99678bd01ebc2d1f83f8c`;
- independent review root `4bad5fa9fe5e00033860870a6b0eafe50c8e3e195eea0d74c46430bfdc516031`.

The source/interface audit fixed the implementation boundary to official
nuPlan v1.2 `AbstractPlanner`, `PlannerInput`,
`transform_predictions_to_states`, and `InterpolatedTrajectory` in the
isolated Python 3.9 process, plus one unchanged fixed-DP Python 3.12 worker.
Only atomic per-tick NPZ+JSON crosses that boundary. The plan requires causal
live-history conversion, exact direct-default versus independent
deterministic/MAP elementwise and SHA equivalence, pre/post CAMP candidate
tensor hashes, feasible-only affine/simplex selection, and preservation of
all-K-infeasible masks/reasons with no selected trajectory, candidate-0
fallback, or all-K progress reference.

Baseline provenance remains precisely qualified:

- name: `DP-default deterministic/MAP baseline`;
- candidate 0: fixed-DP deterministic/MAP reference;
- `native_ranked_top1=false`;
- no native K-ranking path or broad CAMP-over-native-DP-Top-1 claim is created
  by default-output equivalence.

The successful AutoDL static review artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_nuplan_adapter_default_provenance_tdd_plan_static_review_47497ef_20260712T162829CST`
- `d244718bd13bc74b88c5aaa9dc03e082ebf43453c12eb270c0e7138b11b73dbc`

It reverified CAMP local/GitHub/AutoDL starting HEAD
`47497ef353b5c0df1a0c6cef08031444e88ae793`, fixed DP HEAD
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, official source HEAD
`ce3c323af01c0d7ec5672f7832ef53f9c679aab0`, tracked-clean state, both prior
artifact manifests and roots, `pip check`, official adapter imports, zero
related Python jobs, and `15082151936` free bytes.

Three failed harness attempts are retained at timestamps `162402`, `162651`,
and `162735` CST. The first omitted the required network-turbo activation for
`git ls-remote`; the next two counted their own Paramiko/SSH command wrappers
as related jobs. An independent executable-name-scoped process audit observed
zero real jobs, and the corrected successful review records all failed paths.
No attempt executed an adapter, fixed-DP inference, simulator, holdout access,
or safety/ADE/FDE/latency metric.

Claim qualification is unchanged:

- `performance_claim=no_claim`
- `bounded_offline_safety_proxy_improvement=supported`
- `closed_loop_safety_claim=not_yet_supported`
- `broad_CAMP_over_native_DP_Top1_claim=not_supported`

current_v19_status=v19_nuplan_v12_adapter_and_executable_default_provenance_tdd_plan_static_review_passed
current_v19_artifact_scope=camp_side_nuplan_v12_adapter_and_executable_dp_default_provenance_tdd_plan_static_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_adapter_default_provenance_tdd_plan_static_review_47497ef_20260712T162829CST
current_v19_artifact_root_sha256=d244718bd13bc74b88c5aaa9dc03e082ebf43453c12eb270c0e7138b11b73dbc
next_work_target=v19_nuplan_v12_adapter_and_executable_default_provenance_tdd_only

## Minimal Runtime Installation Index Qualification

Final command review found that the reviewed official-PyPI wheel lock would
still be installed through AutoDL's incomplete machine-level mirror unless the
installation command repeated the resolver's isolation flags. The design and
plan were therefore narrowed before materialization: runtime lock installation
uses `--isolated --index-url https://pypi.org/simple`, and the fixed local
nuPlan source uses `--isolated --no-index --no-deps --no-build-isolation`.
Package versions, wheel hashes, process boundaries, disk gate, simulator
semantics, and all claim constraints are unchanged. No environment or
simulator was created by this qualification.

- qualified design SHA256:
  `c4084e405e2da636531c73a30a4d67a074634dd10e9bc41e6ded4f84ece33778`
- qualified plan SHA256:
  `88da8686900c8843f6fe6a64b96cbdbb113d3bed73d6505f22a2b36d138a5098`

current_v19_status=v19_nuplan_v12_environment_cleanup_and_minimal_runtime_lock_static_review_passed
current_v19_artifact_scope=exact_single_environment_cleanup_and_torch_free_python39_wheel_lock_static_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_lock_static_review_ff375430_20260712T132719CST
current_v19_artifact_root_sha256=b0e7a4188e53d325ee9b285bcccc2960a495f51846b3695ac36643e8194c45de
next_work_target=v19_nuplan_v12_minimal_runtime_materialization_only

## Minimal Runtime Materialization Review EOF Qualification

The complete materialization result-review section above was inserted before
the earlier installation-index qualification because the materialization
pointer appeared more than once. No historical text is moved, rewritten, or
deleted. The installation-index qualification happened first; the independent
result review at
`4bad5fa9fe5e00033860870a6b0eafe50c8e3e195eea0d74c46430bfdc516031`
is the latest gate. The pointer below is authoritative.

current_v19_status=v19_nuplan_v12_minimal_runtime_materialization_result_review_passed
current_v19_artifact_scope=official_nuplan_v12_torch_free_python39_runtime_materialization_and_independent_result_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_minimal_runtime_materialization_result_review_d85ea23b_20260712T160605CST
current_v19_artifact_root_sha256=4bad5fa9fe5e00033860870a6b0eafe50c8e3e195eea0d74c46430bfdc516031
next_work_target=v19_nuplan_v12_adapter_and_executable_default_provenance_tdd_plan_only

## nuPlan Adapter TDD Plan Review EOF Qualification

The complete adapter/default-provenance TDD plan static-review section above
precedes older qualifications because historical pointer text appears more than
once. No history is moved, rewritten, or deleted. The successful plan review
at root `d244718bd13bc74b88c5aaa9dc03e082ebf43453c12eb270c0e7138b11b73dbc`
is the latest gate, and the pointer below is authoritative.

current_v19_status=v19_nuplan_v12_adapter_and_executable_default_provenance_tdd_plan_static_review_passed
current_v19_artifact_scope=camp_side_nuplan_v12_adapter_and_executable_dp_default_provenance_tdd_plan_static_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_adapter_default_provenance_tdd_plan_static_review_47497ef_20260712T162829CST
current_v19_artifact_root_sha256=d244718bd13bc74b88c5aaa9dc03e082ebf43453c12eb270c0e7138b11b73dbc
next_work_target=v19_nuplan_v12_adapter_and_executable_default_provenance_tdd_only

## nuPlan Adapter and Executable DP-default Provenance TDD Result Review

The approved TDD plan was executed in three small CAMP-side checkpoints:

- `a168d337`: exact per-tick NPZ+JSON bridge, causal/request/response hashes,
  paired run keys, stale/forbidden-field rejection, and all-K failure payloads;
- `af2a8bf9`: live official `PlannerInput` causal materialization plus the
  non-oracle `NuPlanCAMPPlanner(AbstractPlanner)` shell and official relative
  pose conversion;
- `1ed984e1`: one-shot fixed-DP worker, independent default equivalence,
  deterministic K=8 fake-model generation, frozen affine/simplex selection,
  and fixed source/artifact CLI hashes.

All production behaviors were introduced through observed RED then GREEN
tests. The bridge preserves scalar NPZ shapes rather than allowing
`np.ascontiguousarray` to expand them. The live adapter consumes exactly 31
causal 0.1-second history ticks, mission-route lanes with true boundaries and
speed limits, same-tick traffic state, at most 32 dynamic and 5 static
observable objects, and rejects future/label/outcome fields. It uses official
`transform_predictions_to_states` only for coordinate/state conversion and
does not smooth, blend, guide, repair, postprocess, or postselect a trajectory.

The worker freezes DP HEAD
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, the four executable default-path
source hashes, checkpoint/config hashes, and selector root/scales/weights
hashes before a future one-shot call. Tests use a pure fake inference callable:
the direct default and candidate 0 are independent zero-latent calls; candidates
1-7 use deterministic `noise_scale=1.0`; selection is
`score_k(w)=a_k^T w` on nonnegative simplex weights and physical-feasible
candidates only. All-K-infeasible produces no selected index or trajectory.

Candidate 0 remains a fixed-DP deterministic/MAP reference. Neither source
provenance nor TDD establishes a native K-ranking path:

- baseline name: `DP-default deterministic/MAP baseline`;
- `native_ranked_top1=false`;
- `broad_CAMP_over_native_DP_Top1_claim=not_supported`.

The immutable AutoDL TDD result-review artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_nuplan_adapter_default_provenance_tdd_1ed984e1_20260712T164911CST`
- `c402c9e073a4b57be393e52a592cf81398c2fb2c56dd409c669b5496b377e73f`

It records CAMP/GitHub/AutoDL HEAD
`1ed984e152173d24f1426f728c1fbfb415690efd`, fixed DP HEAD above, official
nuPlan source `ce3c323af01c0d7ec5672f7832ef53f9c679aab0`, tracked-clean state,
zero related jobs, and `15080972288` free bytes. The fixed-DP environment ran
`9 passed`; the official nuPlan environment ran `119 passed, 3 skipped`.
Both py_compile checks and `git diff --check` exited zero. The official runtime
emitted only known third-party matplotlib/pyparsing deprecation warnings.

This gate did not call `NuPlanCAMPPlanner.compute_planner_trajectory`, worker
`main`, a real model/checkpoint, `Simulation`/`SimulationRunner`, any holdout,
or any safety/ADE/FDE/latency metric. Claim qualification therefore remains:

- `performance_claim=no_claim`
- `bounded_offline_safety_proxy_improvement=supported`
- `closed_loop_safety_claim=not_yet_supported`
- `broad_CAMP_over_native_DP_Top1_claim=not_supported`

current_v19_status=v19_nuplan_v12_adapter_and_executable_default_provenance_tdd_result_review_passed
current_v19_artifact_scope=camp_side_nuplan_v12_adapter_bridge_and_fixed_dp_default_provenance_tdd_only
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_nuplan_adapter_default_provenance_tdd_1ed984e1_20260712T164911CST
current_v19_artifact_root_sha256=c402c9e073a4b57be393e52a592cf81398c2fb2c56dd409c669b5496b377e73f
next_work_target=v19_nuplan_v12_executable_default_provenance_preflight_only

## Executable DP-default Provenance Preflight

The preflight selected the first immutable `train` record from the frozen v18
causal candidate receipt without reading its candidate tensor or any label:

- record index `0`, log `4d57015cb0245d59`, scene `3becdbe1dd655a34`,
  decision `d3ce291b9f8b5962`;
- source manifest SHA256
  `703a47bec14d9ee4605184618e6bb61b6a4ce4ed73bee4173df508d6a6dfa5e5`;
- candidate records receipt SHA256
  `dd44dd428a599f82583fbe4acda25e7fa3b5e86d89fd4488cac56281d73e88bf`.

The read-only nuPlan source materializer emitted only
`CAUSAL_DP_INPUT_SCHEMA`. Its SHA256
`4eb497aa771eeb3d60ce5fe9d45381105a6c7e197ef8cf2eb196c99bb99ede28`
exactly matched both historical source and candidate receipts. The request is
arm `dp_default`, seed root `3412`, scenario seed `3411`, contains no selector
hashes and no future/label/outcome/holdout/metric field, and keeps
`native_ranked_top1=false`.

The future one-shot command is frozen to:

- DP HEAD `7a1d33da277a1992ec474b5383a0c963c72e04e4`;
- checkpoint SHA256
  `4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75`;
- fixed args SHA256
  `42c1174de7db49d20343d9ff155093ee206ea9fb31bf0fa7185b108e36c66caa`;
- selector root/scales/weights SHA256
  `afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7`,
  `a4122b0fa56912818af92eacf90449633addf9872966aed975317b4307076952`,
  and `922ae11db719a2bda983bccf0c6bca842c37a899c4df222a1f7a5ac733285134`;
- the four previously audited default-path source SHA256 values.

CUDA is available, the checkpoint remained unloaded, worker tests report
`7 passed`, and the exact output contract requires `[80,4]` direct default,
independent deterministic reference, and selected trajectories with
elementwise equality, zero maximum absolute difference, and identical SHA.
Output SHA values are deliberately not invented in preflight; execution must
materialize and independent review must recompute them.

The immutable preflight artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_executable_default_provenance_preflight_16b58672_20260712T165340CST`
- `ff4f02f7963083c532ad36a047dc50135f4016b14739629807e4cc8c33c5f9e0`

No closed-loop adapter, worker `main`, checkpoint load, DP inference,
simulator, holdout, or safety/ADE/FDE/latency metric ran. Claim taxonomy is
unchanged, and a future pass still cannot be called native ranked Top-1.

current_v19_status=v19_nuplan_v12_executable_default_provenance_preflight_passed
current_v19_artifact_scope=label_free_train_causal_request_and_fixed_dp_default_provenance_command_freeze
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_executable_default_provenance_preflight_16b58672_20260712T165340CST
current_v19_artifact_root_sha256=ff4f02f7963083c532ad36a047dc50135f4016b14739629807e4cc8c33c5f9e0
next_work_target=v19_nuplan_v12_executable_default_provenance_execution_only

## Executable DP-default Provenance Execution and Result Review

The exact preflight request could not be executed in place because adding a
response would mutate its immutable artifact. The execution therefore copied
`request.json` and `request.npz` byte-for-byte into a new artifact and changed
only the artifact-local `--request-dir`. Independent review normalized that
path and proved all remaining command text identical. The preflight artifact
still contains exactly the two request files and its root remains
`ff4f02f7963083c532ad36a047dc50135f4016b14739629807e4cc8c33c5f9e0`.

The single worker invocation loaded the frozen checkpoint and made two
independent zero-latent fixed-DP calls on causal input SHA256
`4eb497aa771eeb3d60ce5fe9d45381105a6c7e197ef8cf2eb196c99bb99ede28`.
It exited zero in 5 seconds. The direct default, independent reference, and
selected trajectory are elementwise identical:

- maximum absolute difference: `0.0`;
- common trajectory SHA256:
  `0267c05e15b0aeace63187a169974cc7071027ce2bb1104c6de9da72c0fd3364`;
- baseline name: `DP-default deterministic/MAP baseline`;
- `native_ranked_top1=false` and `native_ranking_path_found=false`.

The execution artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_executable_default_provenance_execution_8b1ed84b_20260712T165600CST`
- `22baae7a64220074e3893b957a104c112dfe454a083f3cd1fe9dc76d076ce94c`

The independent review did not rerun the worker or load the checkpoint. It
recomputed both artifact manifests, request identity, causal-input SHA,
elementwise equality, all three output hashes, command equivalence, exact
baseline naming, and the false native-ranking flag. Its artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_executable_default_provenance_result_review_8b1ed84b_20260712T165700CST`
- `b47d1829f59718510f120a85ef80ba702ee6465d9b1b31b4140e6a276b434a30`

No simulator, holdout, safety/ADE/FDE/latency metric, native K-ranking, or
broad safety claim was involved. The result completes executable provenance
for the accurately named deterministic/MAP default baseline only.

current_v19_status=v19_nuplan_v12_executable_default_provenance_result_review_passed
current_v19_artifact_scope=single_label_free_executable_dp_default_equivalence_and_independent_result_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_executable_default_provenance_result_review_8b1ed84b_20260712T165700CST
current_v19_artifact_root_sha256=b47d1829f59718510f120a85ef80ba702ee6465d9b1b31b4140e6a276b434a30
next_work_target=v19_nuplan_v12_closed_loop_smoke_scenario_selection_and_zero_overlap_preflight_only

## Closed-loop Smoke Scenario Selection and Zero-overlap Preflight

The read-only selection compared every log and scene in the frozen v18 causal
manifest against all 64 existing nuPlan mini DB logs. V18 used 46 logs and 364
scenes; 18 whole logs remain unseen. No holdout label or trajectory future was
read. Frozen bucket rules produced 426 interaction and 3,350 normal eligible
scenario-tag anchors with at least 3 seconds of past and 8 seconds of future
timestamp coverage, a mission goal, and a nonempty route.

SHA256 ascending selection with seed `3411` froze two distinct logs:

- normal: scenario `6a73b61a412f5bce`, scene `8e094bf622b6556b`,
  log `91382cbd48a755ec`, tag `medium_magnitude_speed`, selection SHA256
  `000a3f5665eee39fd6373037129b1967c8fe7eaa372cf30932975162da1e9665`;
- interaction: scenario `eecd62f34d5e567e`, scene `e5a54d93210e5019`,
  log `ebaddc0a658856e0`, tag `waiting_for_pedestrian_to_cross`, selection SHA256
  `0090489250355c76557d2eb6cef522791dc91191dc77be94fa6c4e2f60c9b678`.

Both are in existing `sg-one-north` mini DBs. Selected log overlap with all
v18 train/calibration/holdout identities is zero; selected scene overlap is
zero; selected logs are distinct. The selection imported official scenario
builder/simulation classes only and instantiated no simulator.

The immutable selection preflight artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_scenario_selection_preflight_d0f3372e_20260712T170011CST`
- `80be83ed08b332ddd05a39016bc4618fb9679106bdd686d99b2ebf19c68ebf47`

current_v19_status=v19_nuplan_v12_closed_loop_smoke_scenario_selection_zero_overlap_preflight_passed
current_v19_artifact_scope=existing_mini_two_log_two_bucket_zero_overlap_scenario_selection_preflight
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_scenario_selection_preflight_d0f3372e_20260712T170011CST
current_v19_artifact_root_sha256=80be83ed08b332ddd05a39016bc4618fb9679106bdd686d99b2ebf19c68ebf47
next_work_target=v19_nuplan_v12_closed_loop_smoke_static_config_and_harness_preflight_only

## Closed-loop Smoke Static Configuration and Harness Preflight

The preflight froze official `closed_loop_nonreactive_agents` semantics for the
two selected unseen-log scenarios:

- `NuPlanScenarioBuilder`, `StepSimulationTimeController`,
  `TracksObservation`, `PerfectTrackingController`, `SimulationSetup`,
  `Simulation`, and sequential `SimulationRunner`;
- a 3.0-second simulation history buffer required by the causal adapter;
- separate DP-default and CAMP rollouts from identical scenario/initial state,
  with natural divergence allowed only after selections;
- seeds scenario `3411`, DP tick root `3412`, bootstrap `3410`, with formal
  `11/12/13` forbidden;
- primary lower-is-better SafetyCost v1 at protocol SHA256
  `5a3f6cd77bb5ff34e002321b1dbd201d2a4fd56af058fa57f7d6b8d06dffe9d3`;
- official collision/TTC/drivable-area/direction/progress/speed/comfort,
  secondary ADE/FDE/miss, separate latency fields, and all failure rules.

Static imports and official source hashes passed, but the expected CAMP-side
`scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py`
does not exist. Missing implementation is limited to constructing selected
scenario objects and paired setups, executing separate arms, retaining bridge
evidence, serializing official histories/metrics, materializing frozen
SafetyCost components/latencies, and failing closed on incomplete evidence.

The immutable artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_static_config_harness_preflight_17038d9a_20260712T170236CST`
- `2b9f07880fef3ada8700b85e3e964342eb9c953538e2fa9cbbc9f791c062d917`

The gate passed as a static contract but records `execution_ready=false`. It
instantiated no scenario, planner, worker, simulator, holdout label, or metric.

current_v19_status=v19_nuplan_v12_closed_loop_smoke_static_config_harness_preflight_passed_execution_not_ready
current_v19_artifact_scope=frozen_official_nonreactive_two_arm_smoke_config_and_missing_harness_contract
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_static_config_harness_preflight_17038d9a_20260712T170236CST
current_v19_artifact_root_sha256=2b9f07880fef3ada8700b85e3e964342eb9c953538e2fa9cbbc9f791c062d917
next_work_target=v19_nuplan_v12_closed_loop_smoke_harness_tdd_only

## Closed-loop Smoke Harness TDD and Independent Result Review

The CAMP-side harness was implemented test-first at CAMP/GitHub/AutoDL commit
`8dd926fd828d5d953f420f9d0c07a4c5bf42a8b4`. Fixed DP remained tracked-clean
at `7a1d33da277a1992ec474b5383a0c963c72e04e4`; official nuPlan source remained
tracked-clean at `ce3c323af01c0d7ec5672f7832ef53f9c679aab0`.

The new script is
`scripts/integrations/run_diffusion_planner_dp_camp_v19_closed_loop_smoke.py`.
Its pure contract tests cover the frozen two-scenario config, formal-seed and
zero-overlap rejection, shared paired identity with separate arm roots, the
exact frozen SafetyCost v1 formula, complete finite nonnegative six-field
latency evidence, retained history/official-metric/result files, cross-arm
rejection, and structured failure preservation. Its official constructors bind
`NuPlanScenario`, `StepSimulationTimeController`, `TracksObservation`,
`PerfectTrackingController`, `SimulationSetup`, `Simulation` with a 3.0-second
history buffer, and sequential `SimulationRunner` without Hydra.

The successful TDD artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_harness_tdd_8dd926fd_20260712T171349CST`
- `615b50e1223a8334f049c1f70f9590372b8e6e67c0afaf388e0dbcffed031696`

The isolated official nuPlan Python 3.9 suite reported `29 passed, 1 skipped`;
the fixed-DP Python 3.12 suite reported `13 passed`. `py_compile`, the frozen
config validation-only command, and `git diff --check` all exited zero. Free
bytes were `15077896192`, above the 10 GiB floor. Validation-only produced four
rows: two arms for each frozen scenario, sharing a pair key but using distinct
arm roots.

One retained command-harness failure at
`/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_harness_tdd_8dd926fd_20260712T171311CST.tmp`
omitted command-local `PYTHONPATH=camp_core` and exited before importing the
harness. Both pytest commands had already passed; no scenario, planner, worker,
simulator, metric, or holdout was reached. The corrected command changed only
that environment setting.

The independent result review reverified the successful manifest/root, the
retained failure manifest, fixed heads/tracked state, four-row pairing, separate
arm roots, zero related jobs, and disk floor. Its artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_harness_tdd_result_review_8dd926fd_20260712T171453CST`
- `2d9cadaf251eee87de91428ba5150533af08fb3826554da429af37d489ee9ac7`

This TDD gate computed no scientific result. Candidate 0 remains only the
`DP-default deterministic/MAP baseline`, with `native_ranked_top1=false`.
Execution is not ready: the next preflight must freeze and validate exact
runtime arguments, real selected-scenario construction, official metric
builders, SafetyCost component materialization including planned-red evidence,
and six latency receipts. It may not run either arm.

current_v19_status=v19_nuplan_v12_closed_loop_smoke_harness_tdd_and_independent_review_passed_execution_not_ready
current_v19_artifact_scope=camp_side_two_arm_smoke_harness_contract_tdd_validate_only_and_independent_result_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_harness_tdd_result_review_8dd926fd_20260712T171453CST
current_v19_artifact_root_sha256=2d9cadaf251eee87de91428ba5150533af08fb3826554da429af37d489ee9ac7
next_work_target=v19_nuplan_v12_closed_loop_smoke_execution_preflight_only

## Closed-loop Smoke Execution Preflight

The execution preflight passed its bounded purpose at CAMP/GitHub/AutoDL
`0042c79ce886dd03ef1447a0215fc025abdeb79e`. Fixed DP remained
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`, and official nuPlan
source remained tracked-clean at
`ce3c323af01c0d7ec5672f7832ef53f9c679aab0`.

The preflight independently constructed four scenario/simulation objects: a
fresh `NuPlanScenario` and `Simulation` for each DP-default/CAMP arm of both
frozen scenarios. Every object had a mission goal, a nonempty route, at least
161 iterations, `StepSimulationTimeController`, `TracksObservation`,
`PerfectTrackingController`, and a 3.0-second history buffer. No object was
initialized or run.

The official `closed_loop_nonreactive_agents` metric YAML and exact source
hashes were captured. A 15-metric `MetricsEngine` using the official thresholds
for lane change, jerk, lateral/longitudinal acceleration, longitudinal jerk,
yaw acceleration/rate, expert-route progress, collision, TTC, drivable area,
speed limit, comfort, making progress, and driving direction constructed
successfully. The fixed executable-provenance command was converted to a
shell-free per-tick `plan_tick` argument list by removing only the frozen
request directory and changing only the operation. It was not executed.

The immutable preflight artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_execution_preflight_0042c79c_20260712T171917CST`
- `350076df70f12364531b0494d63a5e089d570a124a3b4c03f7e1a29a8c125822`

Free bytes were `15077511168`, above the 10 GiB floor. No planner initialize or
compute, worker, simulator runner, metric compute, or holdout access occurred.

The preflight correctly records `execution_ready=false`. Official nuPlan v1.2
has no red-light metric. The current bridge also lacks matched DP-default
planned-red evidence, exact run-rate materializers for TTC/lane/progress/
dynamics, and all six frozen latency receipts. These fields may not be replaced
with convenient official booleans or other proxies. Closing them requires a
new pre-execution evaluation contract and CAMP-side TDD; it does not authorize
changing fixed DP, candidate tensors, SafetyCost weights/formula, or the
baseline name.

current_v19_status=v19_nuplan_v12_closed_loop_smoke_execution_preflight_passed_execution_not_ready
current_v19_artifact_scope=four_independent_official_scenario_simulation_and_metric_engine_construction_with_safety_component_latency_gap
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_execution_preflight_0042c79c_20260712T171917CST
current_v19_artifact_root_sha256=350076df70f12364531b0494d63a5e089d570a124a3b4c03f7e1a29a8c125822
next_work_target=v19_nuplan_v12_closed_loop_safety_component_and_latency_contract_design_only

## Closed-loop Safety Component and Latency Design Static Review

The preauthorized design gate froze the missing execution evidence contract at:

- `docs/superpowers/specs/2026-07-12-v19-nuplan-closed-loop-safety-component-latency-design.md`
- SHA256 `56a24ce729f5c7b4a8f13b9f9dc8cec9563d28251fc4f011425dbfcc6d91e50e`

The selected design rejects both incomplete official-only substitution and any
post-hoc SafetyCost formula change. It adds one CAMP-side posterior evaluation
adapter over official history/map/traffic-light sources and immutable bridge
receipts while leaving the official metric engine as secondary reporting.

The contract freezes:

- causal `61 x 0.05 s` to `31 x 0.1 s` history downsampling with no future,
  interpolation, or cross-stream index mismatch;
- OBB collision and 2.0 m near-miss step rates over the full official posterior
  observation, explicitly separate from online frozen 32+5 feasibility;
- route-corridor lane violation, existing state-transition realized-red,
  selected-trajectory planned-red at tolerance `1e-12`, observed-dt dynamics,
  and monotone route completion;
- six `perf_counter_ns` receipts for causal conversion, bridge write, DP
  inference, atom/selector, bridge read, and total planning path;
- complete per-tick SHA/run-key/arm evidence and matched-pair fail-closed
  handling without candidate-0 or cross-arm fallback.

The successful AutoDL static review artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_design_static_review_2f0973ec_20260712T175249CST`
- `b6acf99b6cc69d2141c96c4351b4773cd307d0eb21fec8495e9a63cc76ef084a`

It verified the spec SHA and fixed boundaries and independently constructed both
selected scenarios at database interval `0.05 s` with 161 iterations. Free
bytes were `15077048320`. No planner, worker, simulator, metric, or holdout ran.

Two retained static-review attempts used nonexistent case-sensitive proxy
literals and failed before interval review. The spec did not change:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_design_static_review_2f0973ec_20260712T175035CST.tmp`
  / `8323444ccb7eb392424bc50bd6e361fd36669bf737dee23cae61b7fcdebfff43`;
- `/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_design_static_review_2f0973ec_20260712T175155CST.tmp`
  / `a5a011e2a88ce903678e8a9bf23125f84b984a52261785874ea77e6368303948`.

Candidate 0 remains only the `DP-default deterministic/MAP baseline`, with
`native_ranked_top1=false`. The next gate is TDD plan-only and may not run a
planner, worker, simulator, metric, or holdout.

current_v19_status=v19_nuplan_v12_closed_loop_safety_component_and_latency_design_static_review_passed_execution_not_ready
current_v19_artifact_scope=closed_loop_history_map_bridge_safetycost_component_and_six_segment_latency_design_static_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_design_static_review_2f0973ec_20260712T175249CST
current_v19_artifact_root_sha256=b6acf99b6cc69d2141c96c4351b4773cd307d0eb21fec8495e9a63cc76ef084a
next_work_target=v19_nuplan_v12_closed_loop_safety_component_and_latency_tdd_plan_only
