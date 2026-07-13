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

## Closed-loop Safety Component and Latency TDD Plan Static Review

The preauthorized writing-plans gate froze the implementation plan at:

- `docs/superpowers/plans/2026-07-12-v19-nuplan-closed-loop-safety-component-latency-tdd.md`
- SHA256 `eeb7b4fde36ee3fed24ff99595b673bfb7acc5c2150fcb74e4d019de10688f2c`

The plan contains five tasks and four implementation slices. It first fixes the
native `0.05 s` to fixed-DP `0.1 s` causal history boundary; then reuses the
existing replay summary helpers through one official-history adapter; adds
selected planned-red and two worker timing fields without altering candidate
tensors; adds four planner-side timing fields and immutable tick receipts; and
finishes with separated-runtime non-execution review and controller update.

Each implementation slice requires a retained RED result, minimal GREEN,
py_compile/target tests, and a small commit/push. It adds no dependency and
does not authorize a real planner compute, worker/checkpoint execution,
simulator, metric compute, holdout access, or claim.

The successful AutoDL static review artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_tdd_plan_static_review_760e174f_20260712T175725CST`
- `7d251174503765201a3050cb3d9fac5c8861d352b8ecb66b1e1e307a7e6f7fb6`

It verified the plan SHA, five tasks, four RED/GREEN/commit slices, exact
interfaces, design/protocol boundaries, no placeholders, zero peer git jobs,
fixed DP/source heads, and the 10 GiB disk floor. Free bytes were
`15076581376`. No planner, worker, simulator, metric, or holdout ran.

Candidate 0 remains only the `DP-default deterministic/MAP baseline`, with
`native_ranked_top1=false`. The user previously selected Inline Execution, so
the next gate is TDD implementation only without another approval checkpoint.

current_v19_status=v19_nuplan_v12_closed_loop_safety_component_and_latency_tdd_plan_static_review_passed_execution_not_ready
current_v19_artifact_scope=five_task_four_slice_closed_loop_safety_component_latency_tdd_plan_static_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_tdd_plan_static_review_760e174f_20260712T175725CST
current_v19_artifact_root_sha256=7d251174503765201a3050cb3d9fac5c8861d352b8ecb66b1e1e307a7e6f7fb6
next_work_target=v19_nuplan_v12_closed_loop_safety_component_and_latency_tdd_implementation_only

## Closed-loop Safety Component and Latency TDD Independent Review

The four TDD implementation slices completed on current `main`:

- `d4ec4865a6961fb0f33ea264fefcea199ffbd922` causally downsamples 61 native
  `0.05 s` history samples to the fixed 31-sample `0.1 s` online input;
- `5ffa4b86e2a135556a7035c557a5fbf1488e07d4` reuses existing replay summary
  helpers through one official-history posterior evidence adapter;
- `857361523b6405cdd2a615653b26395442a0e939` records selected planned-red,
  the CAMP raw planned-red vector, and two worker timing fields while preserving
  candidate hashes and the one-call DP-default path;
- `abf8415e823bd450e3367fab4f2b2064d3b11217` writes one immutable per-tick
  receipt with request/response/selected SHAs and all six latency fields and
  wires the harness directly to those receipts and evidence materialization.

The successful separated-runtime TDD artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_tdd_abf8415e_20260712T181140CST`
- `53788f39ff8fa31c1644004e2b501b249488fd3b0c1a49a64f380c66b53faf13`

The official nuPlan Python 3.9 suite reported `78 passed, 2 skipped`; the
fixed-DP Python 3.12 bridge/worker suite reported `15 passed`. Pycompile and
diff check passed. The artifact reverified CAMP/GitHub/AutoDL agreement, fixed
DP/source heads, selector/scales/weights/checkpoint, SafetyCost/design/plan
hashes, prior artifact manifests, zero jobs, and `15075004416` free bytes.

The independent review did not rerun tests. It recomputed the source manifest
and root, checked recorded test counts and source contracts, and reverified
heads, no jobs, and disk floor. Its artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_tdd_result_review_abf8415e_20260712T181211CST`
- `aaac385112ffc2c16f991c0d28521c5b9884de42b3b9a9d6368f36b77a5424f8`

Implementation tests used fake inference, runner, and planner boundaries. No
real checkpoint worker, planner compute, simulator, metric compute, or holdout
access occurred. No safety, ADE/FDE/miss, or latency result was generated.
Candidate 0 remains the `DP-default deterministic/MAP baseline`, with
`native_ranked_top1=false`.

Execution remains not ready. The next gate may repeat only the execution
preflight against the real selected scenarios and frozen runtime/worker command
to prove all online sources, posterior components, and six receipt fields are
constructible. It may not run either arm.

current_v19_status=v19_nuplan_v12_closed_loop_safety_component_and_latency_tdd_independent_review_passed_execution_not_ready
current_v19_artifact_scope=causal_history_safetycost_component_planned_red_and_six_latency_receipt_tdd_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_safety_component_latency_tdd_result_review_abf8415e_20260712T181211CST
current_v19_artifact_root_sha256=aaac385112ffc2c16f991c0d28521c5b9884de42b3b9a9d6368f36b77a5424f8
next_work_target=v19_nuplan_v12_closed_loop_smoke_execution_preflight_retry_only

## Closed-loop Smoke Execution Preflight Retry Failure Review

The bounded retry failed closed before any planner compute. The first retained
attempt called `SimulationHistoryBuffer.initialize_from_scenario` directly and
therefore omitted the current frame that official nuPlan appends inside
`Simulation.initialize()`. The causal adapter correctly rejected that input
because its history did not end at the decision tick. The completed failure
artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_execution_preflight_retry_c6fdc9f3_20260712T181427CST`
- `adc8a7ad206ca538ea25b718f1f075edb5f4ab571fd70933a0fd243afde3de54`

Official source inspection and a two-scenario timestamp probe established the
root cause without changing the adapter. The corrected retry used exactly
`Simulation.initialize()` and `Simulation.get_planner_input()`. It passed the
decision-tick history boundary, then failed at the next mandatory causal source:
`route speed_limit_mps is required`. Its retained artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_execution_preflight_retry_c6fdc9f3_20260712T181943CST`
- `b9ee87967a7e1aa299ebc6ceaee57b9304bfb00f15b98e71d378b254afc738f4`

An independent read-only review reconstructed both frozen route paths from the
official map API. All `50/50` selected route slots across the normal and
interaction scenarios had `speed_limit_mps=None`, including lane and lane
connector objects and their incoming/outgoing edges. This matches the v18
source inventory: Singapore has `0/2001` map roadblocks with complete speed
sources. Zero, current-speed, statutory-default, and `100 m/s` fallbacks remain
forbidden. The review artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_execution_preflight_retry_failure_review_c6fdc9f3_20260712T182110CST`
- `e64031e0ff0a0f2ed5fa9084cd2fea66a276e1e850c813f4742371e54f1104d1`

Continuing requires replacing the already frozen two-scenario selection with
speed-complete existing-data scenarios and repeating zero-overlap plus freeze
gates. That changes a frozen protocol input and is outside routine harness
remediation, so no third preflight was started. No DP/candidate mutation,
planner compute, worker execution, simulator run, metric compute, old holdout
access, or claim occurred.

The scientific taxonomy remains unchanged:

1. `performance_claim=no_claim`;
2. `bounded_offline_safety_proxy_improvement=supported` within the frozen
   observable source;
3. `closed_loop_safety_claim=not_yet_supported`;
4. `broad_CAMP_over_native_DP_Top1_claim=not_supported`.

Candidate 0 remains the `DP-default deterministic/MAP baseline`, with
`native_ranked_top1=false`.

current_v19_status=v19_nuplan_v12_closed_loop_smoke_execution_preflight_retry_failed_missing_frozen_route_speed_source_user_decision_required
current_v19_artifact_scope=two_selected_singapore_scenarios_50_of_50_route_speed_sources_missing_fail_closed_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_execution_preflight_retry_failure_review_c6fdc9f3_20260712T182110CST
current_v19_artifact_root_sha256=e64031e0ff0a0f2ed5fa9084cd2fea66a276e1e850c813f4742371e54f1104d1
next_work_target=user_decision_required_before_replacing_frozen_v19_closed_loop_smoke_scenario_selection_for_real_route_speed_sources

## Speed-complete Smoke Scenario Reselection Failure Review

The user authorized a source-only correction before any simulator or metric
execution: keep two smoke scenarios and the existing normal/interaction rules,
exclude all frozen v18 logs/scenes, select deterministically without labels or
outcomes, prefer existing Las Vegas/Pittsburgh data, and change no metric,
threshold, seed, baseline, selector, or SafetyCost rule.

The frozen qualification documents are:

- `docs/superpowers/specs/2026-07-12-v19-closed-loop-smoke-speed-complete-reselection-design.md`,
  SHA256 `5057052f6aac4c6157dbc55285ba5d151cc50ea62ed53a2b2839f3cb1b67f4ec`;
- `docs/superpowers/plans/2026-07-12-v19-closed-loop-smoke-speed-complete-reselection.md`,
  SHA256 `2a8ff16826f9d3e5e30466ec70c65d519b25e2fb2059f5091815b541dfd4e70a`.

The first selection artifact/root is retained at:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_speed_complete_reselection_de05110a_20260712T185124CST`;
- `f63de3229936a8671e4184222f93da36445c8447ebec4e6c4c82ccd5d1e40892`.

It failed because DB `location=las_vegas` is not the official maps metadata
key. The same DB exposes `map_version=us-nv-las-vegas-strip`. The shared
`construct_nuplan_scenario` boundary was fixed test-first at
`d67dbaf00bb48697a7b4d9aac0d0bd8de8991206`; the harness suite reported
`6 passed` locally and on AutoDL. The fix changes no route, candidate, metric,
or model semantics.

The preferred tier contained `30` normal candidates in one Las Vegas scene and
zero interaction candidates. Its normal route was disconnected. Consistent
with the user's word "prefer", Boston became the only tier-1 source for a
missing bucket; Singapore remained excluded by the independently reviewed
`0/2001` complete-speed-source inventory. The exact priority hash remained
`sha256("3411|bucket|log_token|scene_token|scenario_token")` within each tier.

The retry evaluated all `964` normal candidates: tier 0 `30`, tier 1 `934`.
Every candidate was retained with its failure reason; none was eligible or
selected. No interaction candidate was evaluated after the mandatory normal
bucket failed, and no replacement `smoke_config.json` was frozen. The immutable
selection failure artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_speed_complete_reselection_retry_517ab14a_20260712T185855CST`;
- `4488dbc74beab84333fe0f69f87527b68a20f8fa155eb02047773afc01a255a0`.

The first independent-review implementation correctly found the same
ineligibility but omitted the selection's earlier nonempty/unique route check,
causing a reason-string mismatch at row 43. Its retained artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_speed_complete_reselection_failure_review_517ab14a_20260712T190144CST`;
- `f073901d7a1573f225cd58e0642cbd791e589cb8c03a2fe445cfe31bb7b6f2fc`.

The corrected independent review rebuilt all `964/964` SQLite identities,
source tiers, SHA ordering, coverage, v18 exclusions, and official route
objects. It confirmed `eligible_normal_candidates=0`, zero log/scene overlap,
and failure-class counts `146` `NuPlanCausalSourceError` plus `818`
`ValueError`. Its passed artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_speed_complete_reselection_failure_review_retry_517ab14a_20260712T190230CST`;
- `5d4fe87c2d2f9e1f8ac8ad642eaf11c3acb504df37db3bdacd73911bf640ed23`.

All gates recorded zero label/outcome reads and no planner compute, worker,
simulation runner, metric compute, old holdout reopening, or claim. Candidate
0 remains the `DP-default deterministic/MAP baseline` with
`native_ranked_top1=false`. The scientific taxonomy remains performance
no-claim, bounded-offline proxy improvement supported within its frozen source,
closed-loop safety not yet supported, and broad CAMP-over-native-DP-Top1 not
supported.

Continuing now requires changing the frozen normal-bucket definition, route
window/source contract, or existing-data scope. That is not authorized by the
source-only replacement decision, so the controller stops for a new user
decision before any simulator execution.

current_v19_status=v19_nuplan_v12_closed_loop_smoke_speed_complete_reselection_failed_no_eligible_normal_candidate_independent_review_passed_user_decision_required
current_v19_artifact_scope=approved_two_tier_source_reselection_964_normal_candidates_zero_eligible_fail_closed_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_closed_loop_smoke_speed_complete_reselection_failure_review_retry_517ab14a_20260712T190230CST
current_v19_artifact_root_sha256=5d4fe87c2d2f9e1f8ac8ad642eaf11c3acb504df37db3bdacd73911bf640ed23
next_work_target=user_decision_required_before_changing_v19_closed_loop_smoke_bucket_or_route_source_contract_after_no_speed_complete_normal_candidate

## Persistent Source-Support Census Exhaustion Review

The user authorized the persistent controller to supersede the preceding
legacy user-decision pointer and execute the already approved three-rung
source-support plan without changing scenarios from outcomes, DP, candidates,
atoms, weights, SafetyCost, metrics, thresholds, baseline provenance, or seed
`3411`.

The single exhaustive source-only census completed all `9212/9212`
zero-overlap existing-data identities. Its immutable artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_source_support_census_fc3a10facc_20260712T202548CST`;
- `7ec02db81091784d888a67ecb3d89f02815afd2c6050e9c57c965e81a00533f0`.

The census made `656` fixed-DP K=8 source probes and retained every row plus
its source failure. Rejection counts were `2655` `AttributeError`, `4803`
`NuPlanCausalSourceError`, and `1098` `ValueError`. The independently computed
support matrix found zero support in every location and tag family for all
three preregistered rungs:

- `full_window_exact_speed=0`;
- `candidate_local_exact_speed=0`;
- `interaction_only_candidate_local_exact_speed=0`.

No rung or scenario was selected, and selection used no outcome. The census
recorded zero expert-future reads, simulator advances, outcome reads, or metric
computations. Its stderr was empty and all SHA256 entries passed.

The exactly-once independent review rebuilt all `9212` identities and official
route sources without fixed-DP worker, simulator, outcome, or metric calls. It
confirmed the same rows, rejection counts, zero-support matrix, and unselected
protocol. Its artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_source_support_independent_review_fc3a10facc_20260712T214750CST`;
- `9acbea9fcd86039e64f8ce61bf5126db54d1eaad6db98a9402fd1d8fa69df618`.

The review exited zero, recorded `worker_calls=0`, `simulator_advances=0`,
`outcome_reads=0`, and `metric_computations=0`, and passed its complete SHA
chain. No second census or review was started.

Following the frozen decision table, the controller wrote one immutable
exhaustion artifact and did not invent a fourth rung or any speed fallback:

- `/root/autodl-tmp/camp_dp_v19_source_protocol_exhaustion_fc3a10facc_20260712T220918CST`;
- `021b9a654477d77d1410b4a2227cda257c5d450d7125bad846130e6e5a72636d`.

That artifact reverified tracked-clean CAMP
`fc3a10facce83577291e4b6bb88dd055eba5707a`, fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, and official nuPlan source
`ce3c323af01c0d7ec5672f7832ef53f9c679aab0`, with zero related jobs and
`15042048000` free bytes. It copied the independently reviewed support matrix
and selected protocol, recorded no holdout access, and passed every SHA entry.

No simulator arm, SafetyCost/trajectory metric, holdout, promotion,
deployment, activation, model replacement, or claim was run. Candidate 0
remains the `DP-default deterministic/MAP baseline`, with
`native_ranked_top1=false`. The claim taxonomy remains:

1. `performance_claim=no_claim`;
2. `bounded_offline_safety_proxy_improvement=supported` only within the frozen
   observable source;
3. `closed_loop_safety_claim=not_yet_supported`;
4. `broad_CAMP_over_native_DP_Top1_claim=not_supported`.

All three authorized rungs are exhausted. Continuing requires a user decision
that changes either the existing data scope or the atom/source contract.

current_v19_status=v19_nuplan_v12_source_protocol_exhausted_all_three_rungs_zero_independent_review_passed_user_decision_required
current_v19_artifact_scope=existing_data_9212_rows_three_rung_exact_speed_support_zero_exhaustion_fail_closed
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_source_protocol_exhaustion_fc3a10facc_20260712T220918CST
current_v19_artifact_root_sha256=021b9a654477d77d1410b4a2227cda257c5d450d7125bad846130e6e5a72636d
next_work_target=user_decision_required_before_new_data_scope_or_atom_source_contract

## Source-Protocol Exhaustion Synchronization Verification

After the exhaustion pointer commit, local verification reported `59 passed,
1 skipped` for the focused v19 suite and `5 passed` for the v18/v19 pointer
contracts. Local pycompile and `git diff --check` passed. The broader v18 test
module was not used as a pointer gate because its unrelated torch import
aborted in the Windows Anaconda runtime; the two named v18 pointer tests both
passed.

AutoDL fast-forwarded cleanly to CAMP
`985eb0f02c9c2e643258283fa7a3bfa08a5b986d`. The official nuPlan Python 3.9
environment passed the complete focused suite with `60 passed`; the separated
fixed-DP Python 3.12 environment passed its worker/bridge/source/pointer subset
with `34 passed`. The fixed-DP environment intentionally has no Shapely, so
the official smoke harness remains tested in the nuPlan environment rather
than weakening runtime isolation. Both environments passed pycompile. AutoDL
`git diff --check` passed, CAMP was tracked-clean and matched `origin/main`,
fixed DP remained `7a1d33da277a1992ec474b5383a0c963c72e04e4`, official
nuPlan remained `ce3c323af01c0d7ec5672f7832ef53f9c679aab0`, and free space
was `15041601536` bytes.

No census, review, worker, simulator, metric, outcome, or holdout job remained
active. The verified exhaustion result and claim taxonomy are unchanged.

current_v19_status=v19_nuplan_v12_source_protocol_exhausted_all_three_rungs_zero_independent_review_passed_user_decision_required
current_v19_artifact_scope=existing_data_9212_rows_three_rung_exact_speed_support_zero_exhaustion_fail_closed
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_source_protocol_exhaustion_fc3a10facc_20260712T220918CST
current_v19_artifact_root_sha256=021b9a654477d77d1410b4a2227cda257c5d450d7125bad846130e6e5a72636d
next_work_target=user_decision_required_before_new_data_scope_or_atom_source_contract

## WOMD/Waymax and CARLA New-Data Qualification

The user authorized changing only the existing-data scope. Fixed DP, K=8
candidates, affine/simplex selection, the convex master, 14D source semantics,
baseline naming, and claim taxonomy remained unchanged.

Official WOMD evidence was reviewed without a dataset download. WOMD supplies
one second of history and eight seconds of future, so it cannot satisfy the
frozen unpadded three-second history plus eight-second evaluation contract.
Candidate-route speed coverage and unchanged fixed-DP compatibility also
remain unproven; WOMD therefore failed closed before sample or adapter work.

CARLA then failed its synthetic-fallback resource preflight. Its official
0.9.16 Linux archive is `8346095504` bytes compressed, while only
`4303986688` bytes were available above the 10 GiB floor: a pre-extraction
deficit of `4042108816` bytes. Exact route-speed coverage and fixed-DP input
compatibility remain unproven.

The exactly-once read-only artifact/root is
`/root/autodl-tmp/camp_dp_v19_new_data_qualification_79f8aae41d_20260712T225405CST`
and `fb257b871fa75ecd769e0772899187edd309529eae6eaacf44ca785f93ee954c`.
Its command exited zero, all hashes passed, and independent review recorded
zero downloads, simulator/metric calls, or holdout reads. Candidate 0 remains
the `DP-default deterministic/MAP baseline`, `native_ranked_top1=false`, and
the four-part claim taxonomy is unchanged.

current_v19_status=v19_womd_waymax_hard_failed_3s_history_carla_fallback_disk_preflight_failed_closed_user_decision_required
current_v19_artifact_scope=womd_waymax_and_carla_new_data_qualification_no_download_fail_closed
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_new_data_qualification_79f8aae41d_20260712T225405CST
current_v19_artifact_root_sha256=fb257b871fa75ecd769e0772899187edd309529eae6eaacf44ca785f93ee954c
next_work_target=user_decision_required_before_carla_large_download_additional_disk_and_license_source_preflight

## CARLA Acquisition Preflight After Disk Expansion

The user added 60 GB and authorized one official CARLA 0.9.16 Linux package
download after license/source/disk review. AutoDL measured `118111600640`
total and `79465508864` free bytes on `/root/autodl-tmp`; there were no related
jobs or CARLA partials, and CAMP/DP were aligned and tracked-clean.

Official tag receipts establish MIT code and CC-BY assets without a
click-through. The release URL resolves to a `8346095504`-byte archive with
ETag `ff92e6da32553dc81d993079c6782f6d-995`. The route-speed source is frozen
to official speed-limit actors/landmarks mapped through OpenDRIVE IDs. The
stateful vehicle speed-limit getter, current speed, defaults, estimates, and
fallbacks are prohibited. Actual candidate-used coverage remains a mandatory
post-extraction, pre-simulator fail-closed gate.

Using a conservative 31 GiB extraction bound plus 2 GiB reserve, peak use is
`43779575696` bytes and projected free space is `35685933168` bytes, above the
10 GiB floor. Official synchronous ticks support exact 3 s history
accumulation and an 8 s evaluation rollout; map topology/boundaries,
traffic-light states, dynamic actors, and CAMP-side conversion to the frozen
DP input/K=8 call are statically feasible without modifying DP.

The exactly-once preflight artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_acquisition_preflight_8a5374d307_20260712T230711CST`
and `5ed26e0ee862dd83442fa3321bde8975f407978a21be511ee654131ca0973fcc`.
Independent review passed all pre-download gates and recorded zero download,
simulator, metric, and holdout calls. Claims and baseline semantics remain
unchanged.

current_v19_status=v19_carla_license_source_temporal_fixed_dp_disk_preflight_independent_review_passed_download_ready
current_v19_artifact_scope=carla_0_9_16_license_source_temporal_fixed_dp_disk_preflight_no_download
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_acquisition_preflight_8a5374d307_20260712T230711CST
current_v19_artifact_root_sha256=5ed26e0ee862dd83442fa3321bde8975f407978a21be511ee654131ca0973fcc
next_work_target=v19_carla_0_9_16_official_linux_package_download_only

## CARLA Download Review And Extraction-Preflight Harness Stop

The only authorized download completed once with exit 0 and zero retries. The
final archive is `8346095504` bytes, no `.part` remains, and its independently
recomputed SHA256 is
`09e3ebb28df17962f0c997e66f4b914ad5ea6f1d6a6dbbf13c9f87eb38346d57`.
Response provenance retained ETag `ff92e6da32553dc81d993079c6782f6d-995`.
The sealed download artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_download_e97264189f_20260712T230835CST`
and `118825ade6b8826059950f62a5ac4c0b2d485fae5fe32e80df9d3de8a4d719ab`.

Read-only tar scanning found `32857` members, `31437` regular files totaling
`20272275914` bytes, required launcher/PythonAPI/maps, and zero unsafe paths.
The decision wrapper failed three times before a valid decision: missing bare
`python3`, missing `ss`, then Python 3.9 lacking
`platform.freedesktop_os_release`. Failed roots are
`57e70a5a8dfa2efe946b509d913638ce5c05bc4099e9db135c7d50e1bdd898f7`,
`c558545a1fc83448a89872ae164b13b2849082d50df87cd7ec8cfcd2ccfff17a`,
and `3d478f63c7e4699d63642554b5c9a1645d5c4e66b186f45d647adc295591d757`.
No fourth retry, extraction, simulator, metric, or holdout access occurred.

current_v19_status=v19_carla_download_review_passed_extraction_preflight_harness_failed_three_attempts_user_decision_required
current_v19_artifact_scope=carla_download_passed_extraction_preflight_harness_three_failures_no_extraction
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_extraction_preflight_final_e97264189f_20260712T233025CST
current_v19_artifact_root_sha256=3d478f63c7e4699d63642554b5c9a1645d5c4e66b186f45d647adc295591d757
next_work_target=user_decision_required_before_v19_carla_extraction_preflight_harness_consolidation_retry

## Unified Python 3.9 Extraction Preflight Remediation

The user authorized replacing the three temporary wrappers with one checked-in
Python 3.9 standard-library harness. The root cause was the split shell/Python
trust boundary: bare `python3`, missing `ss`, and a Python 3.10-only platform
API. Target tests reproduced PATH independence and diagnostic failure output
before the minimal implementation. Local and AutoDL Python 3.9 suites passed.

The unified gate ran exactly once without rescanning or modifying the archive.
All 16 checks passed with empty `failed_checks`: frozen archive and inventory
SHA/size, `32857` members, `31437` regular files, `20272275914` extracted
bytes, zero unsafe paths, required launcher/PythonAPI/maps, response headers,
disk floor, ports/processes, absent extraction root, Ubuntu 22.04, and GPU.
Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_unified_extraction_preflight_0ee305ec7f_20260712T234106CST`
and `7164a02568addc268492a8890d427a31cb59d4aa02bdb5482abd18f66e96df8d`.

Independent review rehashed the archive and inventory, verified the source
manifest/root, recomputed disk headroom, and confirmed zero execution calls.
Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_unified_extraction_preflight_independent_review_0ee305ec7f_20260712T234148CST`
and `eefe8f094f44cd585c78d304ee413a66eacff31db48ba6d5f758b8605662e2bf`.

current_v19_status=v19_carla_unified_extraction_preflight_independent_review_passed
current_v19_artifact_scope=carla_unified_python39_extraction_preflight_read_only_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_unified_extraction_preflight_independent_review_0ee305ec7f_20260712T234148CST
current_v19_artifact_root_sha256=eefe8f094f44cd585c78d304ee413a66eacff31db48ba6d5f758b8605662e2bf
next_work_target=v19_carla_extraction_execution_preflight_only

## CARLA Extraction Execution Preflight

The execution preflight froze the exact archive, explicit `/usr/bin/tar`,
`runtime.tmp` staging root, `runtime` final root, safe tar flags,
same-filesystem atomic rename, and a failure policy that retains staging and
stops without automatic deletion. It rechecked the source review, archive,
free space, ports/processes, and absent staging/final roots. All ten checks
passed; projected free space was `48698031670` bytes.

Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_extraction_execution_preflight_046b40ef5a_20260712T234331CST`
and `3c4a3e521a4359208b3fac889575ddf447842cd807936d9227e5f6a945734791`.
Independent review passed all eight checks with zero extraction, simulator,
metric, or holdout calls. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_extraction_execution_preflight_independent_review_046b40ef5a_20260712T234349CST`
and `92837a632fe05c5c8bad3e9cb2c7b6cdae598fa6fd1f53b05b31e34d91d819dc`.

current_v19_status=v19_carla_extraction_execution_preflight_independent_review_passed
current_v19_artifact_scope=carla_0_9_16_extraction_execution_preflight_independent_review_no_extraction
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_extraction_execution_preflight_independent_review_046b40ef5a_20260712T234349CST
current_v19_artifact_root_sha256=92837a632fe05c5c8bad3e9cb2c7b6cdae598fa6fd1f53b05b31e34d91d819dc
next_work_target=v19_carla_0_9_16_extraction_execution_only

## CARLA 0.9.16 Single Extraction And Result Review

All five prerequisite SHA chains, CAMP/DP heads, archive size/SHA, free space,
and absent roots/jobs were reverified. A necessary read-only link inventory
identified two safe relative SQLite SONAME links, both targeting the same
in-archive regular library without absolute or parent traversal.

Exactly one explicit `/usr/bin/tar` process extracted to the frozen
`runtime.tmp` staging root. Monitoring retained PID `3891`, byte/file progress,
empty stderr, and free bytes above the 10 GiB floor. The job was never
restarted. Because the detached direct tar process did not persist a shell
exit status, process completion alone was not accepted as success.

The exactly-once pre-publish review instead proved the unchanged archive and
inventory SHA, `32857` filesystem entries, `31437` regular files totaling
`20272275914` bytes, required launcher/PythonAPI/maps, empty stderr, sufficient
free space, and both symlinks resolving inside staging to existing targets.
Only after all checks passed was staging atomically renamed to the final
`runtime` root on the same filesystem. Final free bytes were `50782457856`.

The immutable extraction artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_extraction_626cd5ae11_20260713T000320CST`
and `2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce`.
No download, simulator, planner, metric, or holdout access occurred.

current_v19_status=v19_carla_extraction_result_review_passed_runtime_published
current_v19_artifact_scope=carla_0_9_16_single_extraction_exactly_once_review_atomic_publish
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_extraction_626cd5ae11_20260713T000320CST
current_v19_artifact_root_sha256=2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce
next_work_target=v19_carla_post_extraction_runtime_source_inventory_plan_static_review_preflight_only

## CARLA Post-Extraction Source Inventory And Exact-Speed Ladder Resume

The read-only runtime/source inventory completed without starting CARLA or
calling a planner, metric, holdout, or outcome path. All eight main Town XODRs,
runtime launchers, client wheels, speed-limit blueprints, traffic-light assets,
and vehicle assets are present. The main Towns contain `397` ordinary roads,
all with finite-positive explicit OpenDRIVE `<type><speed>` values, and `1362`
junction connector roads, all without an explicit speed. All driving lanes
have width/border geometry. No Town XODR contains a type-274 speed-limit
landmark.

Under the then-frozen actor/landmark-only source, actual candidate-route speed
coverage could not be proven without runtime observations. The source audit
therefore failed closed before simulator planning. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_post_extraction_runtime_source_inventory_1d866e494f_20260713T001545CST`
and `cef560f9e52179e8cf591b2e885ec860fa924029629c77783ac7a646f30ccc87`.
Independent review recomputed the road/junction counts and zero type-274
landmarks, validated the full manifest, and supported the fail-closed decision.
Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_post_extraction_runtime_source_inventory_independent_review_1d866e494f_20260713T001619CST`
and `f4c02827b9e3e07be5ae672c4aa6b35e05e154aa744b46c6c11bb28bb45691eb`.

The user then explicitly authorized overnight continuation and pre-registered
the ordered exact-speed ladder. Rung A is a unique official speed-limit
actor/landmark mapping. Rung B is an explicit finite-positive speed on every
candidate-used non-junction OpenDRIVE road. Rung C permits a speedless junction
connector only when topology is unique and all related incoming and outgoing
driving roads have one identical explicit finite-positive speed. Any missing,
ambiguous, unequal, or one-sided source makes the candidate ineligible;
all-K-ineligible records remain retained and excluded fail-closed.

The design and implementation plan are now frozen in
`docs/superpowers/specs/2026-07-13-v19-carla-exact-speed-source-ladder-design.md`
and
`docs/superpowers/plans/2026-07-13-v19-carla-exact-speed-source-ladder.md`.
They prohibit `Vehicle.get_speed_limit()`, current/default/average speed,
nearest-neighbour or one-sided inheritance, interpolation, result-driven
selection, and a fourth rung. Claim taxonomy and all fixed-DP, K=8, 3+8,
14D, affine/simplex/convex, baseline, holdout, and deployment boundaries remain
unchanged.

current_v19_status=v19_carla_exact_speed_source_ladder_spec_plan_frozen
current_v19_artifact_scope=carla_0_9_16_post_extraction_static_source_review_and_abc_exact_speed_ladder_plan
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_post_extraction_runtime_source_inventory_independent_review_1d866e494f_20260713T001619CST
current_v19_artifact_root_sha256=f4c02827b9e3e07be5ae672c4aa6b35e05e154aa744b46c6c11bb28bb45691eb
next_work_target=v19_carla_exact_speed_source_ladder_tdd_implementation_only

## CARLA Exact-Speed Ladder TDD Implementation

The minimal implementation adds one pure Python 3.9 source module and one
thin census CLI. Rung A requires exactly one finite-positive official mapping;
rung B accepts only an explicit non-junction road speed; rung C accepts a
speedless connector only with one incoming road, one outgoing road, matching
junction connection, and one identical explicit speed across both adjacent
roads. Candidate eligibility is the conjunction of every traversed segment.

Tests cover accepted and rejected A/B/C sources, missing/ambiguous/unequal or
one-sided topology, all-segment fail-closed behavior, deterministic census,
retained masks/reasons, DP-default eligibility, and rejection of any
outcome/label/metric field. Local Python 3.9 compilation passed; local tests
passed `4 + 5`. AutoDL Python 3.9 independently passed the same `4 + 5` tests.
The immutable TDD artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_exact_speed_ladder_tdd_c9245a120a_20260713T002436CST`
and `f7c165b455ae6c38cf16e511ab4682ba10edb0057be907b02546e4cbf1899d32`.
No CARLA runtime, planner, metric, holdout, DP change, or outcome read occurred.

current_v19_status=v19_carla_exact_speed_source_ladder_tdd_implementation_passed
current_v19_artifact_scope=carla_exact_speed_source_ladder_python39_tdd_no_runtime_or_outcomes
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_exact_speed_ladder_tdd_c9245a120a_20260713T002436CST
current_v19_artifact_root_sha256=f7c165b455ae6c38cf16e511ab4682ba10edb0057be907b02546e4cbf1899d32
next_work_target=v19_carla_runtime_actor_landmark_source_probe_preflight_only

## CARLA Runtime Client And A/B/C Map-Source Preflight

The source preflight found no CARLA or evaluation process, no port conflict,
and `50781089792` free bytes. The official cp312 wheel SHA is
`c497edf1b8747194c55b4a24b65b5010d91a4c03baf72c06d11e7cff2b961528`;
its 186726018 uncompressed bytes fit the isolated
`/root/autodl-tmp/camp_v19_carla_client` plan without modifying the fixed-DP
environment. Static official stubs expose OpenDRIVE IDs on landmarks but not
on ordinary `TrafficSign` actors, and all eight main Town XODRs contain zero
type-274 landmarks. A therefore has zero legal unique map mappings.

The checked-in ladder then censused all `2495` driving-lane map units. B
accepted `1134` explicit non-junction units. C accepted `1716`, including
`582` strict topology-derived connector units; ambiguous or unequal connectors
remained unavailable. This is only map-source support. No fixed-DP candidate
path was generated or read, no rung was selected, and no simulator, planner,
metric, holdout, or outcome call occurred.

The preflight artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_runtime_source_preflight_0a37602772_20260713T002723CST`
and `697e45468e2d1403c91297fdaf1398c9282f1592bc6dcfc91451efba7563f4dc`.
Independent review validated its manifest, frozen counts, zero-call boundary,
fixed DP, free-space floor, and absence of a premature rung decision. Its
artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_runtime_source_preflight_independent_review_0a37602772_20260713T002746CST`
and `8f98702a5eaaecd63b78695c8267e6d49c432756ed235c7ec7fb65b032fa7af4`.

current_v19_status=v19_carla_runtime_source_preflight_review_passed_A_exhausted_BC_map_support_only
current_v19_artifact_scope=carla_runtime_client_and_abc_map_source_preflight_independent_review_no_simulator
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_runtime_source_preflight_independent_review_0a37602772_20260713T002746CST
current_v19_artifact_root_sha256=8f98702a5eaaecd63b78695c8267e6d49c432756ed235c7ec7fb65b032fa7af4
next_work_target=v19_carla_fixed_dp_k8_candidate_route_source_probe_plan_tdd_preflight_only

## CARLA Fixed-DP K8 Candidate-Route Source Probe Plan

Static review confirmed the shortest safe path is to reuse the existing v19
bridge, fixed-DP worker `source_probe`, causal materializer, and exact-speed
census. The only new product code is a thin CARLA snapshot-to-causal-schema
adapter; the only new execution code is a source-only harness. No new worker or
general controller is permitted.

The implementation plan is frozen at
`docs/superpowers/plans/2026-07-13-v19-carla-fixed-dp-k8-candidate-route-source-probe.md`.
It keeps CARLA cp312 and the fixed-DP Python 3.12 worker isolated, requires
candidate SHA equality, candidate-0 source completeness, retained all-K
failures, B-before-C ordering, and a zero-outcome independent freeze review
before any arm advancement.

current_v19_status=v19_carla_fixed_dp_k8_candidate_route_source_probe_plan_frozen_preflight_passed
current_v19_artifact_scope=carla_fixed_dp_k8_candidate_route_source_probe_plan_and_runtime_preflight_no_simulator
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_runtime_source_preflight_independent_review_0a37602772_20260713T002746CST
current_v19_artifact_root_sha256=8f98702a5eaaecd63b78695c8267e6d49c432756ed235c7ec7fb65b032fa7af4
next_work_target=v19_carla_causal_snapshot_adapter_tdd_implementation_only

## CARLA Causal Snapshot Adapter TDD And Review

The minimal CAMP-side adapter was implemented test-first. The focused test
first failed because the module did not exist, then passed after adding a
single wrapper around the existing causal materializer. It validates exactly
31 integer timestamps at uniform 100 ms intervals ending at the decision
tick, same-tick traffic source, `current_map_topology_successors`, and nested
future/outcome/label/holdout/metric source rejection. Existing materializer
logic retains the 32 dynamic and 5 static observable caps, SE(2) conversion,
fixed tensor schema, and 8 s candidate horizon.

Local Python 3.9 compilation passed. The combined adapter and v17 causal suite
reported `18 passed, 1 skipped`; the v19 pointer suite reported `3 passed`.
AutoDL Python 3.9 reproduced both results at CAMP HEAD
`20f7384fd65044481aebd99ccf3493e71b47167d`, with fixed DP still
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. The implementation artifact/root
is
`/root/autodl-tmp/camp_dp_v19_carla_causal_snapshot_adapter_20f7384fd6_20260713T003637CST`
and `5a1a9728396c5c6b7bd4f15417060508176ea0e4ea8d2ca25a2e79723d7aacd3`.

Independent review validated the full manifest, exact heads, zero call counts,
materializer reuse, history/traffic/forbidden-field guards, and absence of a
CARLA import. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_causal_snapshot_adapter_independent_review_20f7384fd6_20260713T003700CST`
and `1fe5fc52a559807ff1266ab4c9782e4f31aefce60207e49e436b5efb40454e13`.
No simulator, planner, metric, holdout, DP modification, or outcome read
occurred.

current_v19_status=v19_carla_causal_snapshot_adapter_tdd_independent_review_passed
current_v19_artifact_scope=carla_causal_snapshot_adapter_python39_tdd_and_independent_review_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_causal_snapshot_adapter_independent_review_20f7384fd6_20260713T003700CST
current_v19_artifact_root_sha256=1fe5fc52a559807ff1266ab4c9782e4f31aefce60207e49e436b5efb40454e13
next_work_target=v19_carla_candidate_source_probe_harness_tdd_and_execution_preflight_only

## Existing Source-Probe Harness Reuse Review

Ponytail review found that a new candidate-source runner would duplicate the
checked-in v19 bridge, fixed-DP worker `source_probe`, source-support artifact
helpers, and exact-speed census. The final AutoDL command used the explicit
repo and nested-package roots and passed all `33` bridge, worker, source-probe,
and CARLA speed-census tests. Two earlier commands failed only at collection
because each exposed one of the two required Python roots; both causes and the
successful third command are retained rather than hidden.

The reuse artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_source_probe_harness_reuse_review_28d0c454cf_20260713T003925CST`
and `1ba0c9c5202fa59e044f2c3ad5d6536918e12d8de39180e5391d1ee6db9f422f`.
Independent review validated the manifest, `33 passed`, all three attempt
records, exact heads, zero calls, and the no-new-runner decision. Its
artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_source_probe_harness_reuse_independent_review_28d0c454cf_20260713T003947CST`
and `01e9cf0f442df68ecc2db97df97d6d6f1c82f46c499526ef67bd6404e670b608`.
No simulator, planner, metric, holdout, DP modification, or outcome read
occurred.

current_v19_status=v19_carla_source_probe_harness_reuse_independent_review_passed
current_v19_artifact_scope=existing_v19_bridge_worker_source_probe_harness_reuse_review_no_new_runner
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_source_probe_harness_reuse_independent_review_28d0c454cf_20260713T003947CST
current_v19_artifact_root_sha256=01e9cf0f442df68ecc2db97df97d6d6f1c82f46c499526ef67bd6404e670b608
next_work_target=v19_carla_runtime_snapshot_collector_tdd_and_isolated_client_materialization_preflight_only

## CARLA Isolated Client Materialization Preflight

The read-only preflight verified the official cp312 wheel, Python 3.12 match,
18 archive members, zero unsafe paths, absent
`/root/autodl-tmp/camp_v19_carla_client`, no CARLA/source-probe job, fixed DP,
and projected free space `50592807294` bytes above the 10 GiB floor. The first
sealed artifact failed only because its expected full CAMP HEAD receipt was
mistyped; all other checks passed and no extraction occurred.

The corrected retry artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_isolated_client_materialization_preflight_retry_c275eff4e2_20260713T004138CST`
and `5667543567d5ef46638848aa691658788f2fef9ddfb90e687620e8cf743bb2df`.
Independent review validated its manifest, every check, retained prior failure,
zero call counts, absent target, and floor. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_isolated_client_materialization_preflight_independent_review_c275eff4e2_20260713T004158CST`
and `25fa8bf7dab8a787c82827e9ce5cd8bbc6f37b26113534d2448f26187b1c2456`.
No client extraction, simulator, planner, metric, holdout, or outcome read
occurred.

current_v19_status=v19_carla_isolated_client_materialization_preflight_independent_review_passed
current_v19_artifact_scope=carla_cp312_isolated_client_materialization_preflight_review_no_extraction
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_isolated_client_materialization_preflight_independent_review_c275eff4e2_20260713T004158CST
current_v19_artifact_root_sha256=25fa8bf7dab8a787c82827e9ce5cd8bbc6f37b26113534d2448f26187b1c2456
next_work_target=v19_carla_runtime_snapshot_collector_tdd_implementation_only

## CARLA Runtime Snapshot Collector TDD And Review

The existing causal adapter was extended test-first with one history collector.
The test first failed on the missing API, then passed after implementing the
minimum conversion from 31 official CARLA source ticks to the shared
materializer batch. Actor histories are contiguous at the decision tail,
ordered by current distance and stable track ID, transformed into the current
ego frame, and carry explicit type and extent data. Nested outcome fields are
rejected before conversion.

Local Python 3.9 compilation passed; the adapter plus v17 causal suite reported
`20 passed, 1 skipped`, and the pointer suite reported `3 passed`. After one
evidence-preserving GitHub 503 retry, AutoDL reproduced both results at CAMP
HEAD `5e887d460878c0486d2b40a3a8acd5ed1bb269d5` with fixed DP unchanged.
The implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_runtime_snapshot_collector_5e887d4608_20260713T004620CST`
and `45b7f5e1c3a816b3ab29fb152510e2d1f8eb65ea7c1cac3afcd814777571a0f1`.
Independent review validated its manifest, tests, history builder, forbidden
guard, world-to-ego transform, zero calls, and absence of a CARLA import. Its
artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_runtime_snapshot_collector_independent_review_5e887d4608_20260713T004620CST`
and `d894f575f136e1cc87b984a09f2ad01edfb90b1e58243ba92a5f87a211075b45`.

current_v19_status=v19_carla_runtime_snapshot_collector_tdd_independent_review_passed
current_v19_artifact_scope=carla_runtime_snapshot_history_collector_python39_tdd_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_runtime_snapshot_collector_independent_review_5e887d4608_20260713T004620CST
current_v19_artifact_root_sha256=d894f575f136e1cc87b984a09f2ad01edfb90b1e58243ba92a5f87a211075b45
next_work_target=v19_carla_isolated_client_materialization_execution_and_import_review_only

## CARLA Isolated Client Materialization And A-Source Qualification

The official cp312 wheel was extracted once to
`/root/autodl-tmp/camp_v19_carla_client.tmp`, imported with Python 3.12, checked
with an offline Town01 `carla.Map`, and atomically renamed to the final client
root. The target contains the expected 18 members and client manifest root
`ba3b3d97783a16211f1ed855b0c2640e58ed97fd5258cf17ff99a00037683f3e`;
free space remains above the 10 GiB floor. A first execution precheck failed
before extraction because of an incorrect expected full HEAD receipt; its
actual retained evidence root is
`/root/autodl-tmp/camp_dp_v19_carla_isolated_client_materialization_25d8dd8e0a_20260713T004732CST.tmp`.

The successful materialization artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_isolated_client_materialization_retry_25d8dd8e71_20260713T004811CST`
and `421a2490281cf90c43031ce642713fdddeabe6b7017f143f1f5b802d5a3d49d5`.
Independent review validated the client manifest, final import, absent client
staging root, retained failed evidence, and an offline full-map source census.
Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_isolated_client_materialization_independent_review_25d8dd8e71_20260713T004910CST`
and `9fed6265a50b7336702f15fdbe68996f7d9ae51da42a85e2db36ddc32081cfe3`.

The official offline CARLA map parser exposes 153 type-274 landmarks:
Town01/02/03/04/05/06/07/Town10HD counts are `22/21/6/53/18/0/33/0`.
Town01 has one duplicate `(road_id,s)` key. This source-only evidence qualifies
the earlier A=0 statement, which inspected only raw OpenDRIVE signal elements.
A is not exhausted and is not yet selected; exact candidate-route uniqueness
and coverage remain mandatory. No simulator, planner, metric, holdout, or
outcome call occurred.

current_v19_status=v19_carla_isolated_client_materialization_review_passed_A_landmark_source_reopened
current_v19_artifact_scope=carla_cp312_client_atomic_publish_import_review_and_offline_type274_census
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_isolated_client_materialization_independent_review_25d8dd8e71_20260713T004910CST
current_v19_artifact_root_sha256=9fed6265a50b7336702f15fdbe68996f7d9ae51da42a85e2db36ddc32081cfe3
next_work_target=v19_carla_type274_landmark_segment_mapping_tdd_and_candidate_route_probe_preflight_only

## CARLA Type-274 Landmark Segment Mapping TDD

The official runtime schema exposes lane ranges through
`Landmark.get_lane_validities()`. The mapping contract was implemented
test-first: the new test failed on the missing source type/API, then passed
after adding one pure resolver. A candidate segment may use a type-274 source
only from the same OpenDRIVE road, an inclusive official lane-validity range,
and the unique latest landmark with `landmark.s <= segment.s`. Duplicate
records at the latest `s` are ambiguous even if their values match. No source
crosses a road or junction; nearest-neighbour, current vehicle state, defaults,
and result-driven fallback remain forbidden.

Local and AutoDL Python 3.9 checks passed `6` focused mapping tests plus `5`
census/pointer tests at CAMP HEAD
`2bd18d669b5a6fa7d9f3d730cc35c90b77427e50`; fixed DP remains unchanged.
The implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_type274_landmark_segment_mapping_2bd18d669b_20260713T012127CST`
and `3b0a0c8228f7cab2c359a458384be1b4caafeccd959e89b06dde6472335fcbbc`.
Independent review validated the manifest, tests, same-road/lane/latest-s
contract, duplicate rejection, and zero call counts. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_type274_landmark_segment_mapping_independent_review_2bd18d669b_20260713T012127CST`
and `bc934a052c2c27dde49869457e776d30517e903d5ce764629f7316493c663238`.
No simulator, planner, metric, holdout, or outcome call occurred.

current_v19_status=v19_carla_type274_landmark_segment_mapping_tdd_independent_review_passed
current_v19_artifact_scope=carla_type274_same_road_lane_validity_unique_predecessor_mapping_tdd
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_type274_landmark_segment_mapping_independent_review_2bd18d669b_20260713T012127CST
current_v19_artifact_root_sha256=bc934a052c2c27dde49869457e776d30517e903d5ce764629f7316493c663238
next_work_target=v19_carla_type274_full_map_mapping_census_and_candidate_route_probe_preflight_only

## CARLA Type-274 Full-Map Mapping Census And Candidate Projection Preflight

The offline full-map census applied the frozen same-road, lane-validity, and
unique-predecessor resolver to `60748` CARLA waypoint units. It found `9342`
exact A-source mappings, `51279` missing mappings, and `127` ambiguous
mappings. Town06 and Town10HD have zero A-source support. This establishes
map-level support only; it does not establish coverage on any fixed-DP K=8
candidate route, select an exact-speed rung, or freeze a scenario.

The first sealed census artifact failed only its strict API evidence check:
the harness expected the legacy annotation `project_to_road: bool = True`,
while the official CARLA 0.9.16 stub uses `bool | None = True` and returns
`Waypoint | None`. All scientific census, head, DP, disk, client-manifest, and
no-job checks passed. That retained artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_type274_full_map_mapping_census_preflight_a9601de0d2_20260713T022005CST`
and `5c8e6d77c2088e11ae32d0ec0e55988cde84d763e97952c139237c78c35c406d`.
A first remediation construction attempt also remains sealed at
`/root/autodl-tmp/camp_dp_v19_carla_type274_full_map_mapping_census_preflight_remediation_a9601de0d2_20260713T022404CST_failed`
with root `10d6dac54981df30ed2d99909a21b4c08e05967831ed684a53d7dcc99c6371c9`;
it failed before any rescan because client provenance lives in its independent
review artifact rather than a client-local `ROOT_SHA256` file.

The corrected remediation reused the sealed census without rescanning maps,
matched the official Python 3.9-compatible overload, and passed all checks.
Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_type274_full_map_mapping_census_preflight_remediation_a9601de0d2_20260713T022543CST`
and `d795dd630818c758771b2a386bd2b0bbe041970cd8b84593dc0b4c97553e4fc1`.
Independent review revalidated the source manifest, recomputed every map
partition and total, confirmed `project_to_road=False` support and fail-closed
`None`, and found no CARLA runtime process. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_type274_full_map_mapping_census_preflight_independent_review_a9601de0d2_20260713T022656CST`
and `74d92ad451a38c9a439537581bbe5a8dfcc80f5c6ad8f41088f26491405a5ffe`.
Free space was `50590949376` bytes. No simulator, planner, candidate tensor,
metric, holdout, or outcome call occurred, and `selected_rung` remains null.

current_v19_status=v19_carla_type274_full_map_mapping_census_and_candidate_probe_preflight_independent_review_passed
current_v19_artifact_scope=carla_type274_full_map_waypoint_mapping_census_and_strict_candidate_projection_preflight
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_type274_full_map_mapping_census_preflight_independent_review_a9601de0d2_20260713T022656CST
current_v19_artifact_root_sha256=74d92ad451a38c9a439537581bbe5a8dfcc80f5c6ad8f41088f26491405a5ffe
next_work_target=v19_carla_strict_candidate_world_point_to_opendrive_segment_projection_tdd_only

## CARLA Strict Candidate World-Point Projection TDD

The strict candidate projection helper was implemented test-first at CAMP
commit `e7b66186235138ae94a42c24d2513f664e74977e`. The isolated RED probe failed
on the missing `project_world_point_to_segment` symbol. The minimum GREEN
implementation reuses `SegmentRef`, calls the official map API with explicit
`project_to_road=False` and the driving-lane filter, returns `None` for an
off-road point, and rejects non-finite coordinates, non-driving waypoints, or
invalid OpenDRIVE metadata. It imports no CARLA package and adds no new type or
dependency.

AutoDL Python 3.9 passed compilation and `47 passed, 1 skipped` across the
focused exact-speed, causal-adapter, and v18/v19 pointer suites. The
implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_strict_segment_projection_e7b66186_20260713T032316CST`
and `453c0ce374676bae561d44ea85e69c7f1c738210d8ee9673bf77a75b5dd8becc`.

The first independent review sealed all static checks as passing except for a
mistyped expected full CAMP commit receipt. That retained artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_strict_segment_projection_independent_review_e7b66186_20260713T032413CST`
and `34ca25e1a74f3b5cae4f0e8dd3e9cacb775547eb1a1be9740750a4ca7dee5d5e`.
The receipt-only retry reused those sealed checks without rerunning tests and
passed at
`/root/autodl-tmp/camp_dp_v19_carla_strict_segment_projection_independent_review_retry_e7b66186_20260713T032505CST`
with root `0ef58adfa6eb084d15ed4d777bd474640381ddfd40598c06d7762782eb244245`.
No simulator, planner, candidate tensor, metric, holdout, or outcome call
occurred; no rung or scenario is selected or frozen.

current_v19_status=v19_carla_strict_candidate_world_point_to_opendrive_segment_projection_tdd_independent_review_passed
current_v19_artifact_scope=carla_strict_world_point_to_existing_segment_ref_projection_tdd_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_strict_segment_projection_independent_review_retry_e7b66186_20260713T032505CST
current_v19_artifact_root_sha256=0ef58adfa6eb084d15ed4d777bd474640381ddfd40598c06d7762782eb244245
next_work_target=v19_carla_strict_candidate_world_point_to_opendrive_segment_projection_static_review_only

## CARLA Strict Candidate Projection Static Review

The read-only static review passed at CAMP HEAD
`d659bdf19ce1c57f6e98d95e2b10a6302c9c7981`. It verified the sealed TDD
artifact, official CARLA 0.9.16 strict `get_waypoint` overload, unchanged fixed
DP worker SHA receipts, dependency-free helper, tracked-clean heads, and disk
floor. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_strict_segment_projection_static_review_d659bdf1_20260713T042131CST`
and `b75ba30875fb8e7f1870a6dcda10cd48be2192e4acdd5bd7544fb1a10479c6c0`.
Independent result review passed at
`/root/autodl-tmp/camp_dp_v19_carla_strict_segment_projection_static_review_independent_review_d659bdf1_20260713T042220CST`
with root `2d922b11619a8b34c519fda2148c252ff8b81c410a2c2be62cd08637942caaec`.

The review identified two mandatory preflight boundaries. Fixed-DP candidates
are in `ego_base_link`, while the CARLA map API consumes world locations, so
world XY must be derived only by the inverse of the same-tick
`agents_from_world_tf`; the immutable K=8 tensor cannot be modified. CARLA z
semantics must also be proven before a candidate probe, without invented z or
road projection. Each of all 80 points must resolve strictly or the candidate
is source-ineligible; candidate 0 must be source-complete.

The dedicated probe plan's statement that A was exhausted and B should run
first is now historically stale. The independently reviewed `9342` map-level
A mappings supersede it, so the frozen ladder remains A then B then C, stopping
at the first independently reviewed legal paired support. This is a
source-evidence qualification, not an outcome-driven protocol change. No
candidate tensor, simulator, planner, metric, holdout, outcome, rung, or
scenario was generated, read, selected, or frozen.

current_v19_status=v19_carla_strict_candidate_world_point_to_opendrive_segment_projection_static_review_independent_review_passed
current_v19_artifact_scope=carla_strict_projection_coordinate_frame_z_semantics_and_A_first_ladder_static_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_strict_segment_projection_static_review_independent_review_d659bdf1_20260713T042220CST
current_v19_artifact_root_sha256=2d922b11619a8b34c519fda2148c252ff8b81c410a2c2be62cd08637942caaec
next_work_target=v19_carla_A_first_candidate_route_world_transform_and_source_probe_preflight_only

## CARLA A-First Candidate World-Transform Preflight Failure

The offline preflight failed closed before any fixed-DP candidate generation.
Across `25091` official 5 m driving waypoints in the eight main Town maps,
strict `project_to_road=False` lookup preserved the original road/section/lane
identity for only `23765` points at each waypoint's own z and `23497` at z=0.
Changing only z to `actual +/- 1000 m` produced `16527/19422` matches. Thus the
official CARLA 0.9.16 strict lookup is z-sensitive and is not identity-
preserving even when started from every generated waypoint's own transform.
All eight Towns had nonzero actual-z identity gaps.

The failed preflight artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_A_first_world_transform_source_probe_preflight_b2f1360d_20260713T052313CST`
and `b6c7c9609733a31d966f8782508509dd4047c37f9572bd558e6d8c6eb7469f94`.
Its only failed checks were exact actual-z identity and z invariance; heads,
fixed DP, disk, transform roundtrip, official maps, worker SHA receipts, and
no-job checks passed.

Independent review recomputed every total and found at least one actual-z
identity mismatch in every Town plus an independently observed z-sensitive
point. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_A_first_world_transform_source_probe_preflight_independent_failure_review_b2f1360d_20260713T052457CST`
and `fb096a9f5453d64a6f63f354c56afd07c68cdd64507318b2d3e75ad400ef40d9`.

Fixed-DP candidates remain immutable ego-frame `float32 [8,80,4]` trajectories
containing planar x/y and heading representation but no z. Exact candidate
OpenDRIVE segment identity therefore cannot be established under the frozen
strict world-point contract. Inventing candidate z, enabling road projection,
using nearest-lane or route/lane z interpolation/inheritance, modifying DP, or
calling the result exact would change the approved atom/source semantics.
Those remediations were not attempted. No candidate tensor, simulator,
planner, metric, holdout, outcome, rung, or scenario was generated, read,
selected, or frozen. Claim taxonomy remains unchanged.

current_v19_status=v19_carla_A_first_candidate_route_world_transform_and_source_probe_preflight_failed_closed
current_v19_artifact_scope=carla_strict_lookup_z_sensitivity_and_2d_candidate_to_3d_opendrive_source_gap
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_A_first_world_transform_source_probe_preflight_independent_failure_review_b2f1360d_20260713T052457CST
current_v19_artifact_root_sha256=fb096a9f5453d64a6f63f354c56afd07c68cdd64507318b2d3e75ad400ef40d9
next_work_target=user_decision_required_before_carla_candidate_2d_to_3d_opendrive_atom_source_contract_change

## CARLA Route-Constrained Lifting Design Approved And Reviewed

The user approved scheme 1, a strict route-constrained 2D-to-3D OpenDRIVE
lifting contract, superseding the preceding source-contract decision boundary.
The design is written at
`docs/superpowers/specs/2026-07-13-v19-carla-route-constrained-lifting-design.md`
with SHA256
`84c2ba324b522bbf09086ba725c38aa4984745fd04d16026349014900fdee31d`.

The contract keeps the fixed K=8 tensor immutable, converts ego XY only through
the inverse same-tick transform, matches only the pre-registered route/lane
surface, obtains z only from verified `get_waypoint_xodr`, requires unique
identity/station and topology continuity, and seals canonical receipts before
CAMP scoring. The paired baseline is named DP operational Top-1 while retaining
`native_ranked_top1=false`; no native K-ranking is claimed. Flat-only filtering
is not enabled and DP modification remains forbidden.

Two failed review artifacts preserve an initial ff-only ordering failure and a
missing literal 10 GiB floor check. The corrected final independent review
passed all contract, scope, placeholder, head, DP, disk, and no-runtime checks.
Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_spec_review_final_dbe1b2af_20260713T091826CST`
and `45d7c214fda7e06774a87b2e7aecc1028f889e7df3714349cdd3a320c5b98b98`.
No simulator, planner, candidate tensor, metric, holdout, or outcome call
occurred; no rung or scenario was selected or frozen.

current_v19_status=v19_carla_route_constrained_lifting_design_independent_review_passed
current_v19_artifact_scope=approved_route_constrained_2d_to_3d_opendrive_lifting_design
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_spec_review_final_dbe1b2af_20260713T091826CST
current_v19_artifact_root_sha256=45d7c214fda7e06774a87b2e7aecc1028f889e7df3714349cdd3a320c5b98b98
next_work_target=v19_carla_route_constrained_lifting_tdd_plan_only

## CARLA Route-Constrained Lifting TDD Plan Reviewed

The approved design was expanded into a five-task TDD plan at
`docs/superpowers/plans/2026-07-13-v19-carla-route-constrained-lifting.md`
with SHA256
`d1e68d6736f812ff23a874efdbfe96acae7db876852f3c9e6d5db55a164f4499`.
The plan covers the pure route-surface kernel, full K8 plus operational Top-1
receipts, active provenance naming, the existing exact-speed census CLI, and
pre-outcome tolerance/probe/census/freeze gates. It creates no runner,
controller, dependency, DP change, or outcome path.

Independent review verified five complete tasks, TDD RED/GREEN cycles, type and
name consistency, full 80-point failure receipts, spec SHA, fixed DP, clean
heads, no CARLA process, and the 10 GiB floor. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_tdd_plan_review_b83ead33_20260713T092456CST`
and `a5135ca42ef1555e9a8c17d45bbf7578f3fb0b603ace238e24e4ea7fb9d7240e`.
The user preselected Inline Execution on current main, so no further execution
choice is required. No simulator, planner, candidate tensor, metric, holdout,
or outcome call occurred; no rung or scenario was selected or frozen.

current_v19_status=v19_carla_route_constrained_lifting_tdd_plan_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_five_task_tdd_plan
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_tdd_plan_review_b83ead33_20260713T092456CST
current_v19_artifact_root_sha256=a5135ca42ef1555e9a8c17d45bbf7578f3fb0b603ace238e24e4ea7fb9d7240e
next_work_target=v19_carla_route_constrained_lifting_task1_tdd_implementation_only

## CARLA Route-Constrained Lifting Task 1 Reviewed

Task 1 added the pure route-surface lifting kernel and focused tests at CAMP
commit `160f4e4fe1969f6344561fc012fdec8f6bb88a18`. The kernel accepts immutable
80-point candidate input, uses only the inverse same-tick planar transform and
consecutive chords in the frozen route context, and calls only the injected
official `get_waypoint_xodr` path for identity-checked finite z. It retains all
80 receipts and fails closed on identity/station ambiguity, missing or
mismatched XODR data, excessive residual, or route discontinuity.

Local Python 3.12 and AutoDL Python 3.9 each reproduced `21 passed` across the
focused lifting and existing exact-speed suites; `py_compile` and
`git diff --check` also passed. The implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task1_160f4e4fe1_20260713T103621CST`
and `75eeb7ed08f97c0277483d54a6808aee448afda114bcf031d4893e946f989c69`.

One evidence-packaging attempt is preserved at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task1_160f4e4fe1_20260713T103522CST.tmp`
with root `1842f4fc890e5956fa74a73196a1f5863faea7b664fa037385c8c7276e486a83`.
Its tests and static checks had passed, but the wrapper exited `127` because it
used an unavailable bare `python3` only while writing `result.json`. The sole
remediation used the already-preflighted explicit Python 3.9 interpreter; no
code or protocol changed.

The independent review reverified the source manifest/root, clean matching
CAMP heads, fixed clean DP commit, 10 GiB floor, fresh focused tests, no global
map lookup in the lifting path, official-XODR-only z, candidate immutability
coverage, full failure receipts, and ambiguity/continuity guards. Its
artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task1_independent_review_160f4e4fe1_20260713T103652CST`
and `b591ab21ef99a32be84501bced8d8c00f19c6eadf6c3410f7085690540515448`.
No simulator, planner outcome, metric, holdout, rung, scenario, or claim was
produced. The fixed DP remains unchanged and `native_ranked_top1=false`.

current_v19_status=v19_carla_route_constrained_lifting_task1_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_task1_pure_kernel_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task1_independent_review_160f4e4fe1_20260713T103652CST
current_v19_artifact_root_sha256=b591ab21ef99a32be84501bced8d8c00f19c6eadf6c3410f7085690540515448
next_work_target=v19_carla_route_constrained_lifting_task2_tdd_implementation_only

## CARLA Route-Constrained Lifting Task 2 Reviewed

Task 2 added a canonical K=8 tick receipt at CAMP commit
`f85dc7446ae4f22272c354d4ca4bccd0ef259fac`. It validates the immutable
float32 `[8,80,4]` tensor and independent operational-output SHA before and
after lifting, emits all eight eligibility masks/reasons and complete point
receipts, and leaves `selected_index=None`. Per-trajectory hashes omit only the
origin index so independently lifted candidate 0 and DP operational Top-1 can
be compared without hiding XY, segment, station, z, or failure differences.

Local Python 3.12 and AutoDL Python 3.9 reproduced `38 passed` across the
lifting and fixed-DP worker suites. Tests cover tensor preservation, expected
SHA mismatch, operational XY drift, independent z-receipt drift, candidate-0
incompleteness, all-K fail-closed records, and rejection of outcome provenance.
`py_compile` and `git diff --check` passed.

The first evidence wrapper is preserved at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task2_f85dc7446a_20260713T104354CST.tmp`
with root `c041022c7847b6460bc6d9481902abda55075b3a51b23dcf25a49239b796d8dc`.
All `38` tests passed, but its static checker incorrectly rejected the literal
`holdout` in the code's forbidden-field list. The sole remediation asserted
that the rejection guard and its test exist; implementation and protocol were
unchanged. The passing implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task2_f85dc7446a_20260713T104456CST`
and `8b2a1ba08cfe3dad76a2eb76eebcdbd50d3da26c1b2d41282eb5ba5a305ad8ad`.

Independent review verified that source manifest/root and result, reproduced
the `38` tests, and built a fresh eight-candidate receipt proving unchanged
candidate bytes, complete 8-by-80 receipts, operational/candidate-0 lifting
equivalence, and no selected index. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task2_independent_review_f85dc7446a_20260713T104706CST`
and `1925a0641d106b5013326429c35e2f346cc0955d19a5957665a76ddc2e42bdd9`.
No simulator, planner outcome, metric, holdout, rung, scenario, or claim was
produced. Fixed DP remains unchanged and `native_ranked_top1=false`.

current_v19_status=v19_carla_route_constrained_lifting_task2_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_task2_k8_operational_top1_receipt_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task2_independent_review_f85dc7446a_20260713T104706CST
current_v19_artifact_root_sha256=1925a0641d106b5013326429c35e2f346cc0955d19a5957665a76ddc2e42bdd9
next_work_target=v19_carla_route_constrained_lifting_task3_tdd_implementation_only

## CARLA Route-Constrained Lifting Task 3 Reviewed

Task 3 updated only active v19 runtime/report provenance at CAMP commit
`78c82091a0dec5963d975e393ad9aac990a7eb71`. One shared bridge constant now
defines `DP operational Top-1` and the exact provenance `unmodified single DP
output; independently equivalent to K=8 candidate 0`. The worker includes both
fields on successful and fail-closed DP responses; the bridge validates them;
the adapter exposes the active planner name; the smoke config validates both;
and future source-support freeze/review configs replace superseded aliases.
Every path still requires `native_ranked_top1=false`, so this is not native
K-ranking evidence. Historical v18 artifacts and prose were not rewritten.

Local Python 3.12 reproduced `56 passed, 1 skipped`; AutoDL Python 3.9 with the
official runtime reproduced `57 passed` with 18 existing matplotlib/pyparsing
deprecation warnings. `py_compile`, `git diff --check`, and the active-source
old-name absence check passed. The implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task3_78c82091a0_20260713T105538CST`
and `802e54d58e8dbf539beec865c667711c980f7303b8a9942acabb2083d7e95c07`.

Independent review reverified the source manifest/root, clean matching CAMP
heads and fixed DP, reproduced all `57` tests, found no superseded active
baseline string, and verified failed-response plus future-freeze provenance.
Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task3_independent_review_78c82091a0_20260713T105608CST`
and `15823afc672546512c07d5c93bf1d764a91e01b589a9129baf2f2bfe58fb73ef`.
No simulator, planner outcome, metric, holdout, rung, scenario, or claim was
produced. Claim taxonomy remains unchanged.

current_v19_status=v19_carla_route_constrained_lifting_task3_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_task3_operational_top1_active_provenance_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task3_independent_review_78c82091a0_20260713T105608CST
current_v19_artifact_root_sha256=15823afc672546512c07d5c93bf1d764a91e01b589a9129baf2f2bfe58fb73ef
next_work_target=v19_carla_route_constrained_lifting_task4_tdd_implementation_only

## CARLA Route-Constrained Lifting Task 4 Reviewed

Task 4 updated the existing CARLA exact-speed census at CAMP commit
`abdedb2a9dc2b0b74875d3b15d2e659cdad731e9`. The new path consumes only the
canonical Task 2 receipt JSON. It verifies the receipt root, candidate and
operational before/after SHAs, map/source/route-graph SHAs, eight candidate
decisions, every 80-point trajectory hash, masks/reasons, operational
completeness, and candidate-0 equivalence before using any segment. It then
reconstructs `SegmentRef` rows from validated point receipts, derives junction
status from the frozen XODR index, and intersects lifting eligibility with the
existing A/B/C speed-source decision. All K masks, reasons, and point failures
are retained. The historical segment-only builder remains unchanged and the
CLI requires exactly one input mode.

Local focused tests reproduced `21 passed`. AutoDL Python 3.9 reproduced `49
passed, 1 skipped` across the receipt census, source-support, and complete v18
orchestrator suites; `py_compile`, `git diff --check`, and static contract
checks passed. The implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task4_abdedb2a9d_20260713T110707CST`
and `f8f6cc71b8e4f65e66c4866dd50deeb7737b4d3ff2a115b4377dbf50b71d1b6a`.

Independent review reverified the implementation manifest/root, reproduced
`19 passed`, and confirmed canonical validation, nine SHA fields, eight-by-80
completeness, mask intersection, operational hard gate, zero access counters,
and the retained historical path. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task4_independent_review_abdedb2a9d_20260713T110744CST`
and `bd956bf03411ea0b513e65102072e1a13b0ca960e3bcbb32a56a99960ec995f1`.
No simulator, planner outcome, metric, holdout, rung, scenario, or claim was
produced. Fixed DP and claim taxonomy remain unchanged.

current_v19_status=v19_carla_route_constrained_lifting_task4_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_task4_exact_speed_census_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_task4_independent_review_abdedb2a9d_20260713T110744CST
current_v19_artifact_root_sha256=bd956bf03411ea0b513e65102072e1a13b0ca960e3bcbb32a56a99960ec995f1
next_work_target=v19_carla_route_constrained_lifting_task5_implementation_static_review_only

## CARLA Route-Constrained Lifting Combined Static Review

The combined review verified the four Task 1-4 independent artifact roots and
all manifest entries, clean matching CAMP heads, fixed clean DP commit, and the
10 GiB floor. It reproduced `93 passed` across the pure lifting, K=8 receipt,
active provenance, receipt census, bridge, worker, adapter, smoke, and
source-support suites.

The first wrapper at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_implementation_static_review_d63b6a21fe_20260713T110945CST`
with root `3fda9d22384ff319b235d8425fdb3de2bb30fa4aebe2989c17bea3a2397a6aa0`
is invalid review evidence. Its tests passed, but its call-graph slice ended
before `_xodr_receipt`, and its subshell lacked `set -e`, so the resulting
assertion in stderr was masked by a later successful diff check. It is retained
for audit only and is not used as a passed gate.

The corrected review used shell errexit and traced both the public kernel and
the private XODR helper. It confirmed route-only matching, no global map
projection, official `get_waypoint_xodr` as the sole z lookup, no CARLA import
in the pure module, separate operational lifting, eight complete receipts, no
selection in the lifting gate, canonical census validation, lifting/speed mask
intersection, zero outcome/metric access, active operational provenance, and
`native_ranked_top1=false`. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_implementation_static_review_final_d63b6a21fe_20260713T111027CST`
and `69e0012e75c66e60935dd2355ccc43a3d64ed76c0b706d0ad92275f7b7cd21ec`.
No candidate generation, simulator, metric, holdout, rung, scenario, or claim
occurred.

current_v19_status=v19_carla_route_constrained_lifting_implementation_static_review_passed
current_v19_artifact_scope=route_constrained_lifting_tasks1_4_combined_static_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_implementation_static_review_final_d63b6a21fe_20260713T111027CST
current_v19_artifact_root_sha256=69e0012e75c66e60935dd2355ccc43a3d64ed76c0b706d0ad92275f7b7cd21ec
next_work_target=v19_carla_route_constrained_lifting_map_only_tolerance_freeze_only

## CARLA Route-Constrained Lifting Map-Only Tolerance Freeze

The outcome-free tolerance census used offline `carla.Map` with the official
CARLA 0.9.16 Town01-Town07 and Town10HD XODRs and the preregistered `5.0 m`
route sampling step. It did not start CarlaUE4 or access DP candidates,
scenarios, outcomes, metrics, holdout, or formal seeds.

Across `25091` generated driving waypoints, official `get_waypoint_xodr`
round trips retained identity with zero failures. Across `22601` consecutive
same-identity chords, the maximum midpoint chord residual was
`1.5273609979704583 m`; maximum XY round-trip error was `0.0`, maximum station
error was `1.7763568394002505e-15 m`, maximum z error was `0.0`, and coordinate
scale was `810.0 m`. The frozen deterministic formula produced geometry,
station, z, and continuity epsilons of `1.5273609989704584`,
`1.0000017763568395e-9`, `1e-9`, and `1.0000017763568395e-9` metres.

The source artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_map_only_tolerance_freeze_147c0d56_20260713T111727CST`
and `1683f40e56df022b2f60bf8e39fe54beac26491362e2982014d4bbc0186e1a47`.
Independent review rehashed all eight maps, recomputed every JSONL maximum,
row/chord count, combined map SHA, floating allowance, and final tolerance.
Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_map_only_tolerance_freeze_independent_review_147c0d56_20260713T111805CST`
and `966a9f6169248186e470c0b1d89a177485794ba916df92c65aef2804fdae986b`.
All access counters remain zero and claim taxonomy is unchanged.

current_v19_status=v19_carla_route_constrained_lifting_map_only_tolerance_freeze_review_passed
current_v19_artifact_scope=route_constrained_lifting_official_map_only_tolerance_freeze_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_map_only_tolerance_freeze_independent_review_147c0d56_20260713T111805CST
current_v19_artifact_root_sha256=966a9f6169248186e470c0b1d89a177485794ba916df92c65aef2804fdae986b
next_work_target=v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_only

## CARLA Route-Constrained Lifting Source-Only K8 Probe Preflight

The read-only preflight reverified the reviewed causal adapter, existing
source-probe bridge/worker, receipt-consuming exact-speed census, Tasks 1-4,
combined static review, official map tolerance freeze, fixed DP assets, clean
matching CAMP/DP heads, zero related jobs, and the 10 GiB floor. It froze the
exact future `source_probe` worker command without materializing a request,
loading the checkpoint, generating a candidate tensor, or advancing a
simulator arm.

Execution is not ready for one narrow engineering reason: the current CARLA
causal adapter produces the same-tick `agents_from_world_tf` but has no
decision-time builder that converts the preregistered
`current_map_topology_successors` route into the canonical
`RouteLiftingContext`/`LaneSurfaceSample` sidecar. Starting the worker without
that sidecar would bypass the approved route-constrained 2D-to-3D lifting
contract, so the probe remains fail-closed.

The preflight artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_7fcfb32efa_20260713T114815CST`
and `8c80f0064316129cd356b0698bb4407345aadb1cd202f606fa982e118bc70713`.
Independent review rehashed that artifact and all upstream roots, reproduced
the missing sidecar builder, confirmed the exact operational baseline naming,
and found no request/response/candidate file or outcome access. Its
artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_independent_review_7fcfb32efa_20260713T114845CST`
and `3691a86781588d94b28ee43e953918eead1324ad7943bebbc694d8788a53b3e2`.
No simulator, planner arm, metric, holdout, rung, scenario, or claim was
produced. The approved minimal remediation is a CAMP-side TDD route-sidecar
builder; no new runner or protocol change is required.

current_v19_status=v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_review_passed_execution_not_ready
current_v19_artifact_scope=route_constrained_lifting_source_only_k8_probe_preflight_independent_review_and_route_sidecar_gap
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_independent_review_7fcfb32efa_20260713T114845CST
current_v19_artifact_root_sha256=3691a86781588d94b28ee43e953918eead1324ad7943bebbc694d8788a53b3e2
next_work_target=v19_carla_route_constrained_lifting_route_sidecar_tdd_implementation_only

## CARLA Route-Constrained Lifting Route-Sidecar TDD

The missing decision-time sidecar builder was implemented test-first at CAMP
commit `efe2a58c647bcb9bf726b48cac369899cf8a1a33`. The RED test failed only
because `build_route_lifting_context` did not exist. The minimal GREEN reuses
the existing `LaneSurfaceSample`, `RouteLiftingContext`, canonical JSON SHA,
and context validator. It accepts only the preregistered
`current_map_topology_successors` source, exact frozen sample fields, and
explicit directed route identities; it hashes the ordered source geometry,
map, graph, sample step, and frozen tolerances without importing CARLA or
calling a global map lookup.

AutoDL Python 3.9 reproduced `49 passed`; py_compile and diff checks passed.
The implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_route_sidecar_tdd_efe2a58c_20260713T115724CST`
and `1dd3aa7093ba2d22fc171bff94e94b227d97c56c90a1dcad8a56619df73a1998`.
An earlier evidence wrapper stopped before creating staging because it compared
against an incorrectly expanded short CAMP SHA; the successful artifact
records that non-runtime attempt.

Independent review rehashed the source artifact, reproduced `9 passed`, and
confirmed strict sample/edge validation, tolerance-bound canonical source
hashing, route-only provenance, validator reuse, and absence of CARLA/global
lookup calls. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_route_sidecar_tdd_independent_review_efe2a58c_20260713T115753CST`
and `b7f9f0f88e90ad6c45b7421fd330f6bbe7e77c41afd8e93155540aff4cfa29c8`.
No candidate, checkpoint worker, simulator, metric, holdout, rung, scenario, or
claim was produced. The next gate is one read-only preflight retry against the
same frozen probe command and upstream evidence.

current_v19_status=v19_carla_route_constrained_lifting_route_sidecar_tdd_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_decision_time_route_sidecar_tdd_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_route_sidecar_tdd_independent_review_efe2a58c_20260713T115753CST
current_v19_artifact_root_sha256=b7f9f0f88e90ad6c45b7421fd330f6bbe7e77c41afd8e93155540aff4cfa29c8
next_work_target=v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_retry_only

## CARLA Route-Constrained Lifting Source-Only K8 Probe Preflight Retry

The unique read-only retry synchronized AutoDL to CAMP
`5ea480b68f38e6bba77a294eec80d00fc94de94a`, found no related task or duplicate
staging, and reverified fixed DP, the first preflight, route-sidecar TDD/review,
map-only tolerances, bridge, worker, assets, and the 10 GiB floor. A dynamic
Python 3.9 check successfully constructed the canonical sidecar with the frozen
tolerances.

The full execution chain remains fail-closed for a different, narrower gap:
there is no checked-in CARLA source-only runtime entry that obtains official
ticks/route samples and invokes the existing bridge/worker. The existing
source-support census and closed-loop smoke harness are nuPlan-specific, so
using either as a CARLA runner would be false provenance. The retry did not
materialize a request or call the worker, simulator, or metrics.

The retry artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_retry_5ea480b6_20260713T124547CST`
and `31e80e7181b42b39cbba95a5dcda7c44f2aaf2562302e521402c5a3ce55c05e1`.
Independent review reproduced the missing runtime entry and the nuPlan-only
scope of the two existing harnesses while revalidating all zero-call and
baseline fields. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_retry_independent_review_5ea480b6_20260713T124616CST`
and `cd73c614fa82521cf41164a39f07be85a73f3dfa544e84d8d3fc5d1f80fb1b70`.
The approved remediation is the original plan's thin CARLA source-only harness
that composes the existing adapter, sidecar builder, bridge, worker command,
and lifting receipt; it is not a new general controller.

current_v19_status=v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_retry_review_passed_execution_not_ready
current_v19_artifact_scope=route_constrained_lifting_source_only_k8_probe_preflight_retry_independent_review_and_runtime_entry_gap
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_preflight_retry_independent_review_5ea480b6_20260713T124616CST
current_v19_artifact_root_sha256=cd73c614fa82521cf41164a39f07be85a73f3dfa544e84d8d3fc5d1f80fb1b70
next_work_target=v19_carla_route_constrained_lifting_source_probe_runtime_harness_tdd_implementation_only

## CARLA Source-Probe Runtime Harness TDD

The approved thin CARLA source-only runtime entry was implemented test-first at
CAMP `346f668a05e8d1b2fb0814ce4a161a364aac22cf`. The initial RED failed because
the planned module did not exist. The minimal implementation has three explicit
process-boundary modes: collect one deterministic 31-tick official CARLA source
history, materialize the existing causal request plus route-lifting sidecar,
and turn existing fixed-worker responses into the canonical lifting receipt.
It reuses the causal adapter, route-sidecar builder, v19 bridge, fixed worker
directories, and K=8 lifting receipt; it does not implement a second worker or
general controller.

The harness rejects forbidden future/outcome fields, fixes selection seed 3411
and DP seed root 3412, refuses existing outputs, leaves route speed explicitly
unavailable for later exact OpenDRIVE receipt/census resolution, and preserves
the active `DP operational Top-1` / `native_ranked_top1=false` provenance. Its
source-only access receipt fixes simulator-arm advances, outcome reads, metric
calls, and holdout reads at zero. Local no-temporary-directory tests reproduced
`40 passed`; the bridge/worker tests that require pytest temporary directories
remain blocked locally by the pre-existing Windows temp ACL rather than an
assertion failure.

AutoDL synchronized ff-only to the implementation commit, remained tracked
clean with fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, and reproduced `80 passed`,
py_compile, and diff check. The implementation artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_probe_runtime_harness_tdd_346f668a_20260713T133128CST`
and `b7f27758b34c5a20f9264f14e1b3dd893c2c82c1a157cf9b9925880b0a20f217`.
Independent manifest rehash and static contract review passed all 15 checks;
its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_probe_runtime_harness_tdd_independent_review_346f668a_20260713T133128CST`
and `b99d79063f550506aef10924575e4461057c5634f9148f80f4d1cb7227f72e26`.
Free space remained `50,573,070,336` bytes. No CARLA runtime, worker inference,
candidate tensor, simulator arm, metric, outcome, or holdout was executed.

current_v19_status=v19_carla_route_constrained_lifting_source_probe_runtime_harness_tdd_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_source_probe_runtime_harness_tdd_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_probe_runtime_harness_tdd_independent_review_346f668a_20260713T133128CST
current_v19_artifact_root_sha256=b99d79063f550506aef10924575e4461057c5634f9148f80f4d1cb7227f72e26
next_work_target=v19_carla_route_constrained_lifting_source_only_k8_probe_execution_preflight_only

## CARLA Source-Only K8 Probe Execution Preflight

The unique read-only execution preflight reverified CAMP/GitHub/AutoDL at
`7347417c60e1a9563f56e212660da09f0be67f29`, fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, tracked-clean state, no related
process or port listener, CUDA, the extracted official CARLA runtime and
isolated cp312 client, all checkpoint/config/selector hashes, five upstream
review roots, and `50,572,677,120` free bytes.

The gate froze one absent staging/final root, Town01, deterministic source-only
seed 3411, DP seed root 3412, the current-map topology route source at 5 m,
the reviewed map-only lifting tolerances, CARLA extraction provenance root,
the exact checked-in harness/worker SHAs, and six command stages: one CARLA
server, capture, causal request materialization, CAMP worker `source_probe`,
independent DP `default_provenance`, and same-map lifting receipt. The execution
must resolve its live CAMP HEAD only if the frozen harness SHA is unchanged.
It must retain staging and stop on any command failure, candidate mutation,
operational/candidate-0 mismatch, source-receipt invariant failure, or disk
floor breach. Only exact recorded CARLA PIDs may be terminated after receipt
sealing.

All 22 preflight checks passed. The preflight artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_preflight_7347417c_20260713T134427CST`
and `e10e8c949e36c37e145e6fe1ba171294ca6e0dcabe0b4b562bdc8e5cac4c9107`.
Independent manifest, frozen-command, root-absence, fixed-DP, and zero-call
review passed at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_preflight_independent_review_7347417c_20260713T134427CST`
with root `c9296189ca96cbe531b2c5dcc3cffa30e689035ce991fe9984805e43b4bcf199`.
No server, worker, checkpoint inference, candidate, simulator arm, rung,
scenario, metric, outcome, or holdout ran.

current_v19_status=v19_carla_route_constrained_lifting_source_only_k8_probe_execution_preflight_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_source_only_k8_probe_execution_preflight_independent_review_no_execution
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_preflight_independent_review_7347417c_20260713T134427CST
current_v19_artifact_root_sha256=c9296189ca96cbe531b2c5dcc3cffa30e689035ce991fe9984805e43b4bcf199
next_work_target=v19_carla_route_constrained_lifting_source_only_k8_probe_execution_only

## CARLA Source-Only K8 Probe Rootless-CWD Retry Preflight

The unique source-only execution attempt retained its failed staging root at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_7347417c_20260713T134427CST.tmp`
with root `809227ae5a914c9f44a24cc27439d4778b358433e7bf9b57b434ed587cf24a4c`.
The packaged Unreal process exited `1` before port readiness with
`Refusing to run with the root privileges.` Capture, materialization, both
workers, receipt construction, candidates, metrics, outcomes, and holdout
access therefore remained at zero. The official binary retained SHA256
`03bcd413615fa1fc61a5b846342dbdc4e6b3541320a40d6bf17ff927039731f9`;
no process remained and free space was `50,572,210,176` bytes.

A smaller read-only overlay remediation preflight proved that the kernel lists
overlay support but this container lacks mount capability. It exited `32`
before any server call, retained its sealed staging artifact/root at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_overlay_retry_preflight_a6988f3f_20260713T140325CST.tmp`
and `c768aea8fb53221f4a2e34214a586f3e395705460580fa4672d5e7e3906665ba`,
and left its exact mountpoint absent. It was not an additional runtime attempt.

The minimal no-mount rootless-CWD retry preflight then passed all 19 checks.
Root enters the unchanged official runtime directory and drops to UID/GID
65534 with `/usr/bin/setpriv`, after which relative access to the packaged
binary and Town01 asset succeeds despite `/root` remaining mode 700. The
preflight also proved the exact runtime write location through an isolated
`CarlaUE4/Saved` directory, then atomically retained that directory inside its
artifact; the runtime Saved path is absent afterward. It created no user,
mount, permission change, server, worker, candidate, metric, outcome, or
holdout access. The binary SHA remained unchanged and free space was
`50,572,169,216` bytes.

The passed preflight artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_cwd_retry_preflight_a6988f3f_20260713T140654CST`
and `aa160dc9066f962b331d967eaa676bf52cb925387e6e15b6c966f604acb420ac`.
Independent manifest, command, permission, runtime-SHA, root-absence, and
zero-call review passed at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_cwd_retry_preflight_independent_review_a6988f3f_20260713T140654CST`
with root `dc9996ad08f42346b9786e5371a521ef30298f003131301bc2d67c910e49b6d2`.
The next gate permits exactly one rootless-CWD retry of the already frozen
Town01 source-only probe. It does not permit a metric, outcome, or claim.

current_v19_status=v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_cwd_retry_preflight_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_source_only_k8_probe_rootless_cwd_retry_preflight_independent_review_no_execution
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_cwd_retry_preflight_independent_review_a6988f3f_20260713T140654CST
current_v19_artifact_root_sha256=dc9996ad08f42346b9786e5371a521ef30298f003131301bc2d67c910e49b6d2
next_work_target=v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_cwd_execution_retry_only

## CARLA Source-Only K8 Probe Rootless Loader Retry Preflight

The unique rootless-CWD runtime attempt started only the frozen CARLA process,
which exited `127` before port readiness. Its exact stderr is
`libChronoEngine.so: cannot open shared object file`; capture, materialization,
both workers, receipt construction, candidates, metrics, outcomes, and holdout
access remained at zero. The retained failed stage/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_retry_a6988f3f_20260713T140654CST.tmp`
and `8fe2ed5fb8822dcc3556ad5a861de12b94f1554a5f74b7621d63677bed98b7f6`.
It atomically retained the generated Saved directory outside the runtime,
left no process, preserved `/root` mode 700 and binary SHA256
`03bcd413615fa1fc61a5b846342dbdc4e6b3541320a40d6bf17ff927039731f9`,
and left `50,571,735,040` free bytes.

Read-only loader diagnosis found that the packaged binary RPATH resolves from
its absolute `/root/...` origin after UID drop, which UID 65534 cannot traverse.
Adding only the two packaged relative library directories resolves this
engineering compatibility gap: `CarlaUE4/Plugins/Carla/CarlaDependencies/lib`
for Chrono and `Engine/Binaries/ThirdParty/PhysX3/Linux/x86_64-unknown-linux-gnu`
for PhysX. No default, copied library, mount, permission change, or runtime
file mutation is used.

The formal no-server loader preflight passed all 18 checks and independently
resolved the full binary dependency graph with zero `not found` entries. Its
artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_loader_retry_preflight_7d67160b_20260713T141937CST`
and `0f388976519f78bf78561927ab11f8eed8340483c4323482164a949f087ac845`.
Independent manifest rehash and rootless `ldd` review passed all 15 checks at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_loader_retry_preflight_independent_review_7d67160b_20260713T141937CST`
with root `6357b6c999fd016699c54bcadf921be8d7693cfa12f8d0c2bd4eb0572ae4eb01`.
No server, worker, candidate, metric, outcome, or holdout ran. The next gate
permits one final rootless loader retry with this exact environment addition;
all source, model, candidate, and protocol inputs remain frozen.

current_v19_status=v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_loader_retry_preflight_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_source_only_k8_probe_rootless_loader_retry_preflight_independent_review_no_execution
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_loader_retry_preflight_independent_review_7d67160b_20260713T141937CST
current_v19_artifact_root_sha256=6357b6c999fd016699c54bcadf921be8d7693cfa12f8d0c2bd4eb0572ae4eb01
next_work_target=v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_loader_execution_retry_only

## CARLA Source-Only K8 Probe Rootless Loader Execution Failure Review

The unique loader-remediated runtime attempt used the independently reviewed
relative CARLA-dependency and PhysX library paths. The packaged process reached
the UE 4.26.2 banner, proving that direct shared-library resolution advanced,
then exited `1` before RPC readiness. It created no UE log and reported only
`Exiting abnormally (error code: 1)`, so the exact internal UE cause is not
established. No capture, materialization, worker, fixed-DP inference, candidate,
lifting receipt, metric, outcome, or holdout access occurred.

The retained failed stage/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_rootless_loader_retry_7d67160b_20260713T141937CST.tmp`
and `91b0ff001536212a4ab430b940db3cc61f9a99929c7057fe1d575473309bc01a`.
It records server PID 36458, readiness false, no pipeline exit codes, zero
outcome counters, unchanged binary SHA256
`03bcd413615fa1fc61a5b846342dbdc4e6b3541320a40d6bf17ff927039731f9`,
`/root` mode 700, absent runtime Saved after evidence retention, and
`50,571,284,480` free bytes.

The first independent-review wrapper sealed a valid 18-check payload/root at
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_rootless_loader_retry_independent_review_89767dba_20260713T142546CST`
and `ca56fcb49d3c337ad7493c9e41d4750bb1cdf5fc3c2db1762135fa6f9c5d526c`,
then returned nonzero after sealing because its wrapper omitted `import sys`.
That wrapper is retained but is not the authoritative review gate.

The minimal manifest-only retry preserved and rehashed both source and prior
review artifacts, exited zero, and passed all 11 checks. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_rootless_loader_retry_independent_review_retry_89767dba_20260713T142655CST`
and `188ba10301cb0e4f428a1d624891cfa9f7b04a477d1b42ab58419dbf2ab17d41`.
It reconfirmed no related job or port, no runtime Saved path, unchanged CAMP/DP
heads and binary, tracked-clean state, the disk floor, and zero candidate or
outcome access.

Three CARLA runtime starts have now failed before readiness: root execution was
rejected by Unreal, rootless execution exposed inaccessible absolute-origin
library resolution, and the reviewed relative-loader remediation reached UE
but exited before log/RPC creation. No fourth automatic runtime attempt is
authorized. Continuing requires a user decision to provide an accessible
non-root CARLA runtime path/mount or to authorize a narrowly reviewed
parent-path execute-permission contract; either path requires fresh disk and
security preflight. The claim taxonomy remains unchanged: performance is
no-claim, bounded offline proxy improvement is supported, closed-loop safety is
not yet supported, and broad CAMP-over-native-DP-Top1 is not supported.

current_v19_status=v19_carla_route_constrained_lifting_source_only_k8_probe_rootless_loader_execution_failure_independent_review_passed
current_v19_artifact_scope=route_constrained_lifting_source_only_k8_probe_rootless_loader_execution_failure_independent_review_no_candidate_or_outcome
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_route_constrained_lifting_source_only_k8_probe_execution_rootless_loader_retry_independent_review_retry_89767dba_20260713T142655CST
current_v19_artifact_root_sha256=188ba10301cb0e4f428a1d624891cfa9f7b04a477d1b42ab58419dbf2ab17d41
next_work_target=user_decision_required_before_carla_nonroot_runtime_access_contract_or_runtime_relocation

## CARLA Non-Root Execute-Only ACL Tooling and Restore Drill

The user explicitly selected the narrow parent-path ACL option without
expanding any DP, candidate, holdout, runtime-relocation, deployment, or claim
boundary. A fresh read-only audit at CAMP/GitHub/AutoDL
`633fc40ee1140166bb3336133e38ee42a75fee4d` and fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4` found no tracked drift, related
process, listener, runtime `Saved` path, or peer ACL artifact. All frozen CARLA
components below `/root` remained mode 755; `/root` alone remained mode 700
with no access/default ACL xattr. Free space was `50,570,862,592` bytes.

The container initially lacked `getfacl` and `setfacl`. Its unchanged Ubuntu
22.04 package configuration uses the Huawei Ubuntu mirror with Ubuntu archive
keys. A signed-index refresh and install simulation authorized only one new
package, `acl 2.3.1-1`, with zero upgrades or removals. The downloaded deb SHA
`42d0071e8c1898fb2910ce7b8f7e8fbe353fdada4416148530fd22bddab7e0b1`
matched the signed package index; installed tool bytes matched the deb and the
package added no service. The first wrapper installed the package but failed
only because it expected extracted usrmerge tools under `/usr/bin` instead of
the package's `/bin` paths. Its retained failed artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_acl_tool_preparation_633fc40e_20260713T150320CST.tmp`
and `26205df785c8b9a6746481643c6e6150db18997f4bc2b9dc2c51ae18d022241f`.
Manifest-only result review corrected that evidence-path assumption and passed
at
`/root/autodl-tmp/camp_dp_v19_carla_acl_tool_preparation_result_review_633fc40e_20260713T150758CST`
with root `7804fc41726a3fad2f01a7a45bf31239322c2477f3d0ac779880df9f707e6da6`.
No ACL or runtime mutation occurred in that gate.

The mutation contract preflight saved numeric `getfacl`, mode/owner/device/
inode, and raw ACL xattr state before any mutation. It uses one exact
`setfacl -m u:65534:--x /root` call and an EXIT restore trap, with HUP, INT, and
TERM converted to trapped exits. It prohibits recursive ACL, chmod, chown,
read, write, or list access and starts no runtime. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_acl_execute_only_traverse_contract_preflight_633fc40e_20260713T151028CST`
and `f0cf867f2c4dcf7745dee87755bdd51e949a578ae4afb5dbace9fa107dc82bb1`.
The first static review root
`40039aafb5b1e95ca80f6631eb7832d00b0864bd141598daea2bd5f7be3984f6`
was superseded because a non-contract FINAL_STATE probe placed `setpriv` inside
`[`. A first retry also remained non-authoritative because its handwritten ACL
string omitted `getfacl`'s final blank line; its retained root is
`ce95e63c69d2e27dd35c04ada7d92cb7d31b970efc104f6436b37c34b2790256`.
The minimal shell-native retry then rehashed all sources and compared the live
ACL/stat/xattr bytes directly. It passed at
`/root/autodl-tmp/camp_dp_v19_carla_acl_execute_only_traverse_contract_preflight_independent_review_retry2_633fc40e_20260713T151232CST`
with root `09afd4f83958aa9d3f8402684bea3c4813e6763dbbd24c3ada19474320dcf180`.

The exact reviewed transaction then ran three restore-drill cases: normal
success exited 0, controlled command failure exited 23, and TERM exited 143.
Each case temporarily exposed only execute traversal on `/root`; UID 65534
could resolve the frozen binary and packaged libraries while read, write, and
directory listing remained denied. Absolute-path `ldd` reported zero missing
libraries. Every EXIT trap restored successfully, and original versus restored
ACL, stat, and xattr snapshots were byte-equal. The live final state is again
mode 700 with no extended ACL and no UID 65534 traversal. The drill artifact/
root is
`/root/autodl-tmp/camp_dp_v19_carla_acl_execute_only_traverse_restore_drill_633fc40e_20260713T151333CST`
and `93962da25efcbf3726c2d2f90fefdb6ee8b9c0f65ab54f874a36d3d102ae3c42`.
Independent review reproduced all three restore receipts, exact execute-only
ACL, access denials, binary SHA, no-job state, and final byte comparisons at
`/root/autodl-tmp/camp_dp_v19_carla_acl_execute_only_traverse_restore_drill_independent_review_633fc40e_20260713T151413CST`
with root `2319ec75e5c0710698d6c4dc1b8bdb165c93a5d650887a73081d5f472057405a`.
Free space remained `50,569,920,512` bytes. No CARLA server, worker, candidate,
metric, outcome, holdout, promotion, deployment, or claim ran.

current_v19_status=v19_carla_nonroot_execute_only_acl_restore_drill_independent_review_passed
current_v19_artifact_scope=carla_nonroot_execute_only_acl_tooling_contract_restore_drill_independent_review_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_acl_execute_only_traverse_restore_drill_independent_review_633fc40e_20260713T151413CST
current_v19_artifact_root_sha256=2319ec75e5c0710698d6c4dc1b8bdb165c93a5d650887a73081d5f472057405a
next_work_target=v19_carla_nonroot_execute_only_acl_runtime_attempt_preflight_only

## CARLA Non-Root ACL Source-Only K8 Runtime Attempt Preflight

The frozen attempt plan uses the reviewed single
`setfacl -m u:65534:--x /root` mutation, EXIT/HUP/INT/TERM restoration, and
read/write/list denials. Inside that transaction it starts the unchanged CARLA
binary as UID/GID 65534 with only the reviewed relative CARLA-dependency and
PhysX library paths, waits at most 60 seconds for Town01 RPC readiness, and
then runs the fixed capture, materialize, CAMP `source_probe`, DP
`default_provenance`, and receipt sequence. Fixed DP remains
`7a1d33da277a1992ec474b5383a0c963c72e04e4`; the worker and harness hashes,
checkpoint, fixed args, selector artifacts, K=8 candidate contract, source
head, seed, and source-only zero-access counters remain frozen. The execution
stage and final roots are single-use and absent.

The first TDD wrapper failed before producing a runner because its test omitted
the module loader call; its retained root is
`6b6a40453b2c39e02f480bb12dd13aca803b81a0861ea030f6c175cb79fe6f38`.
The corrected preflight passed with root
`bcad314d3268e69b83bdbb5cc26fe6a07b2f02040c5e266a368211adc48bb038`.
Several fail-closed review-development artifacts were retained while replacing
fragile stderr, handwritten hash, and unavailable `ss` assumptions. A review
replay then changed only the corrected preflight's two generated
`__pycache__` files; every frozen source, wrapper, plan, and test hash still
matched. Because the sealed artifact was no longer wholly immutable, it was
superseded and not used to authorize execution. None of those review attempts
changed ACLs or started CARLA.

The cache-safe replacement re-observed the expected missing-runner RED and
passing GREEN with bytecode writes disabled, compiled only to files inside its
own artifact, revalidated the shell and Python plans, rehashed all assets and
scripts, and recorded the two-cache-only supersession evidence. Its artifact/
root is
`/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_preflight_cache_safe_retry2_dd5d8122_20260713T153850CST`
and `a85bb086654074ebfcc9af092a1e2081d7327ae9f047adca65a0f2811a90b358`.
Independent review replayed tests with `-B`, directed compilation output only
to the review artifact, and rehashed the source manifest both before and after
review. It passed with a byte-identical manifest at
`/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_preflight_cache_safe_retry2_independent_review_dd5d8122_20260713T153946CST`
and root `eeafefda6607faaae001a0f0b665c35237596cbbaac7da8f3f31ec958bf538c6`.
The final state has no related process/listener, no runtime Saved or execution
root, `/root` mode 700 without UID 65534 traversal, and `50,568,769,536` free
bytes. No ACL mutation, server, worker, candidate, metric, outcome, holdout,
promotion, deployment, activation, or claim ran.

current_v19_status=v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_preflight_cache_safe_independent_review_passed
current_v19_artifact_scope=carla_nonroot_acl_source_only_k8_probe_runtime_attempt_preflight_cache_safe_independent_review_no_execution
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_preflight_cache_safe_retry2_independent_review_dd5d8122_20260713T153946CST
current_v19_artifact_root_sha256=eeafefda6607faaae001a0f0b665c35237596cbbaac7da8f3f31ec958bf538c6
next_work_target=v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_execution_readiness_recheck_only

## CARLA Non-Root ACL Runtime Attempt Execution Readiness Recheck

After the cache-safe preflight checkpoint, GitHub, local, origin, and AutoDL
all resolved to `30feaec8a47f47aed8696cc7699cf857c44bc21c`; fixed DP remained
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, and both repositories were
tracked-clean. The recheck fully rehashed the preflight and review roots,
runner, ACL wrapper, execution plan, harness, worker, checkpoint, fixed args,
selector artifacts, binary, and Town01 client prerequisites. The sole frozen
execution stage/final roots and runtime Saved path remained absent, with no
related process or port 2000 listener.

The exact authorized command remains the reviewed ACL wrapper followed by the
single execution stage, frozen plan, and frozen runner:
`acl_runtime_attempt.sh <execution-stage> execution_plan.json runtime_attempt.py`.
The recorded absolute argv is in the artifact and authorizes exactly one new
runtime attempt under user-selected option A. Before execution, `/root`
remained mode 700 with no access/default ACL xattr; UID 65534 could not read,
write, list, or traverse it. The ACL package remained `acl 2.3.1-1`, disk free
space was `50,567,270,400` bytes, and CUDA plus the frozen CARLA client import
remained available.

The passed readiness artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_execution_readiness_recheck_30feaec8_20260713T154831CST`
and `6379e24a5878bfca482c2289573eb15a85cb6027b9b3d81eba26b6cc9cdcc877`.
Independent review rehashed it before and after all read-only checks, compared
the exact argv and attempt budget, and reproduced the heads, root ACL, disk,
no-job, no-listener, and absent-root conditions at
`/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_execution_readiness_recheck_independent_review_30feaec8_20260713T154919CST`
with root `33be35b2b727441c89458dadfb21f203f0b53f455111f542b447d602d6d0a225`.
No ACL mutation, runtime, worker, candidate, metric, outcome, holdout,
promotion, deployment, activation, or claim ran.

current_v19_status=v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_execution_readiness_recheck_independent_review_passed
current_v19_artifact_scope=carla_nonroot_acl_source_only_k8_probe_runtime_attempt_execution_readiness_recheck_independent_review_no_execution
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_execution_readiness_recheck_independent_review_30feaec8_20260713T154919CST
current_v19_artifact_root_sha256=33be35b2b727441c89458dadfb21f203f0b53f455111f542b447d602d6d0a225
next_work_target=v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_execution_only

## CARLA Non-Root ACL Runtime Attempt Pre-Readiness Failure Review

The immediate launch guard rehashed the cache-safe preflight, readiness, and
readiness-review artifacts after the documentation checkpoint. It bound
GitHub, local, origin, and AutoDL to
`12212340d696a1c660d92a72e2aa95e93f044ca3`, fixed clean DP to
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, the exact wrapper/runner/plan
argv, frozen scripts and assets, absent execution roots, no peer process or
listener, the disk floor, and `/root` mode 700 with no ACL. Its artifact/root
is
`/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_runtime_attempt_execution_launch_guard_12212340_20260713T155208CST`
and `78b9b8daaea5830a0c4db65aba696ca12d4bb1ca0095c73911932a4790b34c07`.

The sole newly authorized option-A attempt then ran the exact argv once. The
wrapper saved the original numeric ACL, stat, and ACL xattrs, granted only
`u:65534:--x` on `/root`, proved UID 65534 still could not read, write, or list
that directory, and started the unchanged CARLA binary as UID/GID 65534. CARLA
printed the UE 4.26.2 banner and exited `1` after 0.60 seconds, before port
readiness. The only server stderr was `sh: 1: xdg-user-dir: not found`. Local
inspection confirms that helper is absent, but no UE log, trace, or other
evidence establishes it as the cause; no causal remediation claim is made.

The runner therefore invoked zero capture, materialization, CAMP worker, DP
worker, or receipt commands. It generated no candidate tensor or receipt and
performed zero metric, outcome, or holdout reads. DP operational Top-1 was not
evaluated, CAMP made no selection, and there is no paired support. The retained
failed staging artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_execution_dd5d8122_20260713T152639CST.tmp`
and `a43483c9bc4d2efadff7e40b538631c6842e56bd9db7f720dd22a46188923271`.

The EXIT trap restored successfully with body rc 1, restore rc 0, and zero ACL,
stat, and xattr comparison return codes. All three original/restored records
are byte-equal; `/root` is again mode 700 with no UID 65534 traversal. The two
empty Saved subdirectories were retained inside the failed artifact, while the
runtime Saved path, CARLA process, workers, and port 2000 listener are absent.
Independent review rehashed the execution artifact before and after review,
reproduced every restore and zero-call assertion, and passed at
`/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_execution_failure_independent_review_12212340_20260713T155450CST`
with root `bd64b788ac7aa231823742317996685ca1bd78283374c2dba2fd21a98cd9ff6d`.
Free space is `50,566,725,632` bytes.

This was the fourth total CARLA start and the only new attempt explicitly
authorized under option A; no further retry or dependency mutation is
authorized. Performance remains no-claim, bounded offline proxy improvement
remains supported, closed-loop safety remains unsupported, and broad
CAMP-over-DP-operational-Top-1 remains unsupported. Promotion, deployment, and
activation remain prohibited. Continuing requires a new explicit user
decision before any dependency remediation or additional runtime attempt.

current_v19_status=v19_carla_nonroot_acl_source_only_k8_probe_execution_pre_readiness_failure_independent_review_passed
current_v19_artifact_scope=carla_nonroot_acl_source_only_k8_probe_execution_pre_readiness_failure_independent_review_no_candidate_or_outcome
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_nonroot_acl_source_only_k8_probe_execution_failure_independent_review_12212340_20260713T155450CST
current_v19_artifact_root_sha256=bd64b788ac7aa231823742317996685ca1bd78283374c2dba2fd21a98cd9ff6d
next_work_target=user_decision_required_after_v19_carla_acl_runtime_attempt_pre_readiness_failure_before_any_dependency_remediation_or_additional_runtime_attempt

## CARLA `xdg-user-dir` Read-Only Call-Chain and Causality Diagnosis

The user authorized only a read-only diagnosis. GitHub, local, origin, and
AutoDL remained at `0fcad73837925e4318bd2f9e42b898ef0d1e0582`; fixed DP
remained tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The
sealed execution and review roots were fully rehashed before analysis. No ACL,
mode, owner, xattr, user, runtime, PATH/profile, package, DP, candidate, map,
protocol, or holdout state was changed.

The frozen runner copies its parent environment, overlays the recorded server
variables, and directly invokes `/usr/bin/setpriv` plus the shipping binary by
argv with `shell=False`. The packaged `CarlaUE4.sh` contains no
`xdg-user-dir` call. Static ELF analysis found the exact ASCII command
`xdg-user-dir DOCUMENTS` at file offset `0xc39247` inside the unchanged
shipping binary. Its only direct static implementation is
`FUnixPlatformProcess::UserDir()`, which calls `popen(command, "r")`, attempts
one `fgets`, and calls `pclose`.

Crucially, the disassembly does not test or propagate the `pclose` return
value. If no stdout populates the result, `UserDir()` calls
`FUnixPlatformProcess::UserHomeDir()`, which first uses
`secure_getenv("HOME")` and otherwise `getpwuid(euid)`, then appends the UTF-16
literal `/Documents/`. Under the exact attempt environment this fallback is
`CarlaUE4/Saved/home/Documents/`; its parent existed and was writable by UID
65534 during the attempt. The three static `UserDir()` callers are config
hierarchy construction, the Kismet platform-user-dir accessor, and sandbox
platform-file initialization.

A safe dynamic provenance probe ran only `/bin/sh` as UID/GID 65534 under the
exact cwd and HOME/XDG/PATH values; it did not invoke CARLA or UE. It reproduced
missing-command rc 127 and `xdg-user-dir: not found`, while the runtime Saved
path remained absent. This confirms where the stderr text originates. It also
shows that `/usr/bin` is present in PATH, so the failure is package absence,
not PATH omission. Because UE explicitly handles empty stdout with a fallback
and ignores the child status, the missing helper is not proven as the direct
exit-1 cause. An indirect effect through later path consumers cannot be ruled
out from static evidence, so the overall CARLA exit-1 root cause remains
`unknown`.

The packaged Dockerfile independently declares `xdg-user-dirs` as a runtime
dependency specifically so Unreal Engine can locate the user's Documents
directory. The current Ubuntu signed index reports it absent and offers
`xdg-user-dirs 0.17-2ubuntu4` with package SHA256
`06c1cb52d3b249aa4b74da0b9fe17c6bfe9b66c3df47e7f7252af14d2a770ce6`.
`apt-get -s` reports zero upgrades, one new package, and zero removals. Thus a
minimal dependency-gap remediation plan exists, but it is not proven to fix
exit 1 and was not executed. The plan requires new user authorization before
any download/install, exact signed-package and rollback preflight, a no-CARLA
UID/environment command-resolution check, and a separate later decision before
any additional CARLA attempt.

The diagnosis artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_xdg_user_dir_read_only_causality_diagnosis_0fcad738_20260713T161525CST`
and `74cd122e24322d62fdb588c378d642443b888743a9e582c9371e00c0f7f5821b`.
Independent review rehashed every input and the source manifest before and
after review, repeated the selected disassembly, exact binary-offset checks,
safe UID shell probe, signed-index inspection, simulation, and live-state
checks, and passed at
`/root/autodl-tmp/camp_dp_v19_carla_xdg_user_dir_read_only_causality_diagnosis_independent_review_0fcad738_20260713T161806CST`
with root `70829ca25e9ec7ad0b322ee3defce30fe091d8915851b7b940d292fb91064ba6`.
Free space was `50,552,483,840` bytes. No CARLA, DP worker, pipeline,
candidate, receipt, metric, outcome, holdout, package download/install,
promotion, deployment, activation, or claim ran.

The claim taxonomy is unchanged: performance is no-claim, bounded offline
proxy improvement remains supported, closed-loop safety remains unsupported,
and broad CAMP-over-DP-operational-Top-1 remains unsupported. Continuing now
requires a new user decision before the signed package dependency-gap
remediation or any additional CARLA runtime attempt.

current_v19_status=v19_carla_xdg_user_dir_read_only_causality_diagnosis_independent_review_passed
current_v19_artifact_scope=carla_xdg_user_dir_read_only_causality_diagnosis_independent_review_no_runtime_no_mutation
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_xdg_user_dir_read_only_causality_diagnosis_independent_review_0fcad738_20260713T161806CST
current_v19_artifact_root_sha256=70829ca25e9ec7ad0b322ee3defce30fe091d8915851b7b940d292fb91064ba6
next_work_target=user_decision_required_before_v19_signed_xdg_user_dirs_dependency_gap_remediation_or_any_additional_carla_runtime_attempt

## Signed `xdg-user-dirs` Install Failure and Verified Rollback

The user authorized only the signed `xdg-user-dirs 0.17-2ubuntu4` package and
an exact UID/environment validation without CARLA. Local, GitHub, origin, and
AutoDL began at `0d5deec8a55a7aeb29b67a3b53777dc82c4bf285`; fixed DP
remained tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
No related process, port-2000 listener, or runtime Saved path existed.

The install preflight verified the configured Huawei Cloud mirror's Ubuntu
jammy InRelease with `/usr/share/keyrings/ubuntu-archive-keyring.gpg`, matched
the signed uncompressed main/amd64 Packages hash and size, and matched the
downloaded package to signed SHA256
`06c1cb52d3b249aa4b74da0b9fe17c6bfe9b66c3df47e7f7252af14d2a770ce6`.
Simulation selected only `xdg-user-dirs`; its sole direct dependency
`libc6 (>= 2.34)` was already installed. The package-owned path baseline,
HOME/XDG baseline, no-autoremove rollback, and success-state keep contract
were recorded. The preflight/review roots are
`e933cea76ceb7903dad9c74caae4fd8b5d5de2f760688b0107624d500f2bf633`
and `ed8b51ca709718df1889b9cb72fd9f319111bac1ff2e59438edc86c693914beb`.

An exact-local apt simulation with `--no-download` failed rc 100 before any
mutation because that option also forbids acquiring the local archive. The
replacement `dpkg --install` command was dry-run because it cannot download or
auto-install dependencies. Two correction evidence attempts failed before
mutation due evidence-driver initialization and literal-newline manifest bugs;
both were retained. The corrected command preflight and independent review
then passed with roots
`4e045717a55378ee98eddf010310b8fdea7d363354daf695ea1f974cfb546bd2`
and `dcc714db42321913edf84eeffaa7f8f1b29783ee0eb6bbcf87173efe2aee5c77`.

The exact signed package installed with rc 0 and was the sole installed-package
change. The next integrity check, `dpkg -V xdg-user-dirs`, returned rc 0 but
printed 124 missing locale/man files. Independent classification proved every
one matches the image's existing `/usr/share/locale/*` or
`/usr/share/man/*` dpkg `path-exclude` policy. Nevertheless the preregistered
validation required empty stdout, so the controller failed closed before
running `xdg-user-dir DOCUMENTS` as UID/GID 65534.

The controller immediately invoked the preflight rollback. It purged only the
target package without autoremove or cache cleanup and proved the original
`unknown ok not-installed` state, absent executable, zero package-owned-path
differences, and byte/normalized-equal HOME/XDG baselines. The rollback root is
`531c26848d2a10a25bb9fd22a9d6251e9b71f2440dc18ed4bf572af6595738e9`.
The failure/rollback review passed at
`/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_signed_dpkg_install_validation_failure_rollback_review_0d5deec8_20260713T170333CST`
with root `6513cabc011e038b6d407db09ca2e3ad5210146db98b3de33902efad91e4a66f`.
Its independent review passed at
`/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_signed_dpkg_install_validation_failure_rollback_review_0d5deec8_20260713T170333CST_independent_review`
with root `d3d19b3646da934c43a7267e5cf1c66b9b3b0dbe20afce6a82a8a78e16919631`.

No package is retained, so the dependency gap remains open. No CARLA, UE,
exact-UID helper validation, DP worker, pipeline, candidate, receipt, metric,
outcome, or holdout operation ran. The missing helper remains unproven as the
prior CARLA exit-1 cause. Performance remains no-claim, bounded offline proxy
improvement remains supported, closed-loop safety remains unsupported, and
broad CAMP-over-DP-operational-Top-1 remains unsupported. A new explicit user
decision is required before any install retry or CARLA runtime attempt.

current_v19_status=v19_xdg_user_dirs_signed_dpkg_install_validation_failed_path_exclude_rollback_restored_independent_review_passed
current_v19_artifact_scope=xdg_user_dirs_signed_dpkg_install_validation_failure_rollback_independent_review_no_package_retained_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_signed_dpkg_install_validation_failure_rollback_review_0d5deec8_20260713T170333CST_independent_review
current_v19_artifact_root_sha256=d3d19b3646da934c43a7267e5cf1c66b9b3b0dbe20afce6a82a8a78e16919631
next_work_target=user_decision_required_after_v19_xdg_user_dirs_install_validation_failure_and_verified_rollback_before_any_retry_or_carla_runtime_attempt

## Exclude-Aware Signed Package Integrity and Exact-UID No-CARLA Validation

The user explicitly authorized reinstalling the same repository-signed
`xdg-user-dirs 0.17-2ubuntu4` package under a strict, per-line,
path-exclude-aware integrity contract, followed only by an exact UID and
environment helper check. Local, origin, GitHub, and AutoDL began at
`248baa8d28a08e24ea2c9629efbc8af9e54c6069`; fixed DP remained tracked-clean
at `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The target package was
`unknown ok not-installed`, `/usr/bin/xdg-user-dir` and all target dpkg-info
files were absent, no related process or runtime Saved path existed, and more
than 10 GiB was free.

The new read-only preflight reverified every sealed source root from the
signed-package, exact-command, and rollback gates. It reran the Ubuntu archive
keyring signature verification, matched exact version
`0.17-2ubuntu4`, package SHA256
`06c1cb52d3b249aa4b74da0b9fe17c6bfe9b66c3df47e7f7252af14d2a770ce6`,
the already-satisfied `libc6 >= 2.34` dependency, and a simulation containing
only the target package. It copied every active dpkg config in load order and
sealed each SHA without changing the configuration. The effective rules were:

- exclude `/usr/share/man/*`;
- exclude `/usr/share/locale/*/LC_MESSAGES/*.mo`;
- exclude `/usr/share/doc/*`;
- then include `/usr/share/doc/*/copyright`;
- then include `/usr/share/doc/*/changelog.*`.

Every one of the previous 124 `dpkg -V` lines was parsed individually. Each
was missing-type only, present in the frozen package manifest, absent on disk,
and covered by a final matching exclude with no later include. No nonmissing
difference was permitted. The preflight passed at
`/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_exclude_aware_integrity_preflight_248baa8d_20260713T172214CST`
with root
`2d0749c18c5fd12ec44e774330d8d46e0e4dfe1f59f34b84f77cc47a04f23354`.
Its independent review passed with root
`068baab4cc18cb979a7ddfec634637f60fe348a34218c03b7294b951783ef754`.

The first protected install execution passed the package and exclude-aware
file-integrity checks, then failed closed before the UID helper because the
evidence driver applied ELF-only `readelf` checks to the package's actual
POSIX shell helper. The controller restored the original not-installed state;
an independent controller check found the command absent and zero dpkg-info
residue. The failed artifact is
`/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_exclude_aware_install_execution_248baa8d_20260713T173140CST`.
The rollback root is
`531c26848d2a10a25bb9fd22a9d6251e9b71f2440dc18ed4bf572af6595738e9`.

A no-install correction preflight verified that the exact package payload has
SHA256 `66f6896a88c333b2c3152617fd3be51d7e896481abc07028a064dad17e64f6b8`,
starts with exact `#!/bin/sh`, is accepted by `/bin/sh -n`, and must be
validated through its shell interpreter rather than as an ELF. The correction
and review roots are
`bc4c24627ba6924a95c94d9c370c1f61bf58d42a61a14497ad9de6c6e49a9b6d`
and `783431271dfe6e07a4b33df3fc81fa0c18c2065733147e8c57cf10fbcd16da72`.

The next protected install again passed package integrity and script
provenance, then failed closed while querying dpkg with a canonical
`/usr/lib/...` realpath that this usrmerge image records under `/lib/...`.
It did not run the UID helper and again restored not-installed with an absent
command and zero dpkg-info residue. The failed artifact is
`/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_exclude_aware_install_execution_248baa8d_20260713T174009CST`;
its rollback has the same independently reproduced root
`531c26848d2a10a25bb9fd22a9d6251e9b71f2440dc18ed4bf572af6595738e9`.

A second no-install correction preflight accepted ownership only through a
path alias that exists, resolves to the identical file, has the identical
SHA, and returns a dpkg owner. It verified `/usr/bin/dash` through
`/bin/dash`, `/usr/lib/x86_64-linux-gnu/libc.so.6` through
`/lib/x86_64-linux-gnu/libc.so.6`, and the loader through its package-owned
`/lib64` path. Its preflight/review roots are
`fa53ca7c7f333870de078eb67c3c8796e159c0785c5e221e9d3a1cf7448cc53d`
and `2987833a28490df928038c73a89ea9f3507b81d56c1fa003a3c6362aa513aadd`.
The package was still not installed, and neither correction started CARLA.

The final protected execution rehashed all source and correction roots before
mutation. Exact `dpkg --install` was again the sole package-universe change.
`dpkg-query -L` exactly equaled the frozen package manifest. `dpkg -V`
returned zero and exactly 124 nonempty lines; every line was reparsed and
allowed only under the preflight predicate. The execution then compared all
included payload paths by type, root owner/group, mode, size, and SHA or
symlink target. It permitted no extra package-owned content path, uncovered
missing path, nonmissing verification difference, executable/library absence,
or metadata/hash drift. The exact helper was package-owned, mode 0755, and
matched the signed payload SHA. Its `#!/bin/sh` syntax and the shell and
library owner/mode/SHA provenance, including only proved usrmerge aliases,
all passed.

Only after those checks, the execution used UID/GID 65534, cwd
`/root/autodl-tmp/carla_0.9.16/runtime`, and the frozen HOME, XDG_RUNTIME_DIR,
USER, LOGNAME, PATH, and LD_LIBRARY_PATH overlay. `command -v xdg-user-dir`
returned `/usr/bin/xdg-user-dir`. `xdg-user-dir DOCUMENTS` exited zero with
stdout `CarlaUE4/Saved/home` and empty stderr, resolving to
`/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Saved/home`. The previously
observed missing-helper fallback would be
`/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Saved/home/Documents/`.
Neither command created the runtime Saved path.

The execution passed at
`/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_exclude_aware_install_execution_248baa8d_20260713T174326CST`
with root
`9a2fe23a3626ad2ebfeb42f37ec3826f37528cda1ecd645ed34271a914847ac1`.
Independent review rehashed the source before and after review, reverified the
active config bytes and every package path, reparsed all 124 lines, independently
rechecked script/interpreter/library provenance, and replayed the exact UID
command. It passed at
`/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_exclude_aware_install_execution_248baa8d_20260713T174326CST_independent_review`
with root
`23c45897ecedfdae5b3576c5b64e1719367837e2e6949b6b8498a279f55ff2ba`.

The preregistered success contract therefore retains exactly
`xdg-user-dirs 0.17-2ubuntu4`; current package state is
`install ok installed 0.17-2ubuntu4`. Fresh verification still reports the
same 124 allowed missing paths and empty stderr, the executable SHA is
`66f6896a88c333b2c3152617fd3be51d7e896481abc07028a064dad17e64f6b8`,
no runtime Saved path or related process exists, and free space is
`50,546,200,576` bytes.

No CARLA, UE, DP worker, pipeline, simulator, candidate, receipt, metric,
outcome, or holdout operation ran. The successful no-CARLA helper check closes
the package dependency gap but does not prove the missing helper caused the
prior CARLA exit 1; that root cause remains unknown. Performance remains
no-claim, bounded offline proxy improvement remains supported, closed-loop
safety remains unsupported, and broad CAMP-over-DP-operational-Top-1 remains
unsupported. No promotion, deployment, or activation is authorized. Any new
CARLA runtime attempt requires a separate explicit user decision.

current_v19_status=v19_xdg_user_dirs_exclude_aware_integrity_exact_uid_no_carla_validation_independent_review_passed
current_v19_artifact_scope=xdg_user_dirs_exclude_aware_integrity_exact_uid_no_carla_validation_package_temporarily_retained
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_xdg_user_dirs_exclude_aware_install_execution_248baa8d_20260713T174326CST_independent_review
current_v19_artifact_root_sha256=23c45897ecedfdae5b3576c5b64e1719367837e2e6949b6b8498a279f55ff2ba
next_work_target=user_decision_required_before_any_additional_carla_runtime_attempt_after_v19_xdg_user_dirs_exact_environment_validation

## Continuous-Authorization CARLA Runtime Attempt Readiness

The user replaced ordinary per-gate and per-attempt approval stops with
continuous v19 authorization inside the existing fixed scientific and
reversible-system contract. Local, GitHub, origin, and AutoDL CAMP were
`2d6693db59673976f78ad6e7a769943160da372a`; fixed DP remained tracked-clean
at `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The stale blocked goal metadata
was not treated as an execution boundary.

A new read-only execution-readiness driver rehashed the prior runtime-attempt
preflight/review and the successful signed-package execution/review roots. It
created a new unique execution stage/final pair, while reusing the unchanged
audited runtime runner and execute-only ACL wrapper. The preflight verified:

- exact CAMP/origin/GitHub and fixed DP heads with both repos tracked-clean;
- signed `xdg-user-dirs 0.17-2ubuntu4`, executable SHA, all 124 individually
  allowed `path-exclude` missing entries, and the frozen UID/GID 65534 helper
  result `CarlaUE4/Saved/home`;
- unchanged CARLA binary, Town01 files, Python client import, GPU, harness,
  worker, checkpoint, fixed args, selector, atom scales, and static weights;
- mode-700 root with no UID 65534 read/write/list/traverse, trusted ACL tools,
  absent runtime Saved path, execution paths, related process, and listener;
- more than the 10 GiB disk floor and a validate-only runner/test pass.

Two preflight launcher directories failed before their drivers began because
the launcher and driver both required exclusive directory creation. A third
attempt failed before mutation on a 60-second GitHub `ls-remote` timeout.
Those directories were retained. Loading `/etc/network_turbo` resolved the
independent network condition. The successful no-mutation preflight passed at
`/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_runtime_attempt_preflight_2d6693db_20260713T184609CST`
with root
`2c95412295bdc77c62b05967da6e3b2a81adb7ab7647418ca34557f48df29d5d`.
Independent review passed at the corresponding `_independent_review` path
with root
`a9318a958a229f2aaa58a205666da4fcd00b9bbe02f58835a5c9152ae9529196`.

Readback caught a fail-closed evidence error before execution: the preflight
had recorded its wrapper, plan, and runner under the staging `.tmp` path,
which no longer existed after the artifact was renamed. A minimal correction
artifact rehashed both sources, preserved the unique execution pair and all
frozen files, but changed only those three command paths to the final artifact
directory. Its independent review required each command file to exist,
reran `bash -n` and runner `--validate-only`, and rechecked heads, package,
root permissions, absent execution paths, and disk floor.

The corrected preflight passed at
`/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_runtime_attempt_preflight_path_corrected_2d6693db_20260713T184808CST`
with root
`c3ea71c31bcd63aec15821d31b57339a67d071c08d521b7cf20ea5dd35cfbe7f`.
Independent review passed at the corresponding `_independent_review` path
with root
`ea112274570064bc55a74148a8523a68002ae4f6c6fc6c59d0d08b2d32d4441a`.
The exact authorized execution command is now:

```text
/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_runtime_attempt_preflight_path_corrected_2d6693db_20260713T184808CST/acl_runtime_attempt.sh /root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_source_only_k8_execution_2d6693db_20260713T184609CST.tmp /root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_runtime_attempt_preflight_path_corrected_2d6693db_20260713T184808CST/execution_plan.json /root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_runtime_attempt_preflight_path_corrected_2d6693db_20260713T184808CST/runtime_attempt.py
```

No ACL mutation, CARLA/UE, worker, pipeline, candidate, receipt, metric,
outcome, or holdout operation occurred. The package remains retained under
its reviewed success contract, and the prior CARLA exit-1 cause remains
unknown. Performance remains no-claim, bounded offline proxy improvement
remains supported, closed-loop safety remains unsupported, and broad
CAMP-over-DP-operational-Top-1 remains unsupported.

current_v19_status=v19_carla_xdg_closed_dependency_runtime_attempt_preflight_path_corrected_independent_review_passed
current_v19_artifact_scope=carla_xdg_closed_dependency_runtime_attempt_preflight_path_corrected_independent_review_no_runtime_no_acl_mutation
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_runtime_attempt_preflight_path_corrected_2d6693db_20260713T184808CST_independent_review
current_v19_artifact_root_sha256=ea112274570064bc55a74148a8523a68002ae4f6c6fc6c59d0d08b2d32d4441a
next_work_target=v19_carla_xdg_closed_dependency_source_only_k8_execution_only_continuous_authorization

## XDG-Closed CARLA Exit-1 Recovery and Read-Only Diagnosis

Continuous v19 authorization permitted the next frozen, reversible option-A
attempt without another ordinary approval stop. Local, origin, GitHub, and
AutoDL CAMP were `976ba7a41f0141de936467c24dce09b5ec645085`; fixed DP was
tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The launch guard
rehashed the corrected runtime preflight/review, exclude-aware signed-package
execution/review, CARLA binary, Town01 assets, harness, worker, checkpoint,
fixed arguments, selector artifacts, and disk floor. It also proved no related
process, port-2000 listener, runtime Saved path, execution root, or preexisting
UID 65534 traversal.

The first guard sealed successfully but its exact direct command was rejected
before wrapper entry because `acl_runtime_attempt.sh` is intentionally mode
0644. No execution stage, ACL mutation, or runtime existed; the retained guard
root is `bf414cb621099537df56f7580851adcedafe9d94ec318501336507e59eb645c7`.
The next guard independently proved the mode and SHA, preserved that failed
guard, and froze `/usr/bin/bash <audited-wrapper> ...` without chmod, ACL, or
source changes. Its artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_source_only_k8_execution_launch_guard_976ba7a4_20260713T190018CST`
and `84f9556e21cf99ce329b33bd57afe7d51a2ee8a351c29b21962837a486dc3c36`.

The corrected invocation was a real CARLA start. The wrapper saved numeric
ACL, stat, and ACL-xattr state, granted only `u:65534:--x` on `/root`, proved
read/write/list denial, and launched the unchanged binary as UID/GID 65534.
CARLA printed `4.26.2-0+++UE4+Release-4.26 522 0` and `Disabling core dumps.`,
then exited 1 after 1.13 seconds before readiness. Server stderr was empty.
The runner called no capture, materialization, CAMP worker, DP worker, or
receipt step; it generated no candidate or receipt and performed zero outcome,
metric, or holdout read.

The EXIT trap recorded body rc 1, restore rc 0, zero ACL/stat/xattr compare
codes, and blocked traversal after restore. Original and restored records are
byte-equal; the live root is again mode 700 without UID 65534 traversal. The
runtime Saved path is absent and its two empty UID-65534 HOME/XDG directories
are retained in the failed stage. No related process or listener survived.

The outer evidence controller returned from the wrapper before the execution
stage became visible to its immediate post-run check. It therefore missed its
own wrapper stdout/stderr and direct return-code files even though the runner,
server, result, ACL, and Saved records were complete. A recovery sealer did
not fabricate those fields: it recorded them unavailable, inferred wrapper rc
1 only from runner rc 1 plus restore body rc 1, and sealed the capture gap.
Independent review accepted the bounded gap and reproduced all runtime-failure,
zero-call, restore, package, head, binary, disk, and no-job assertions. The
failed execution/root is
`/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_source_only_k8_execution_2d6693db_20260713T184609CST.tmp`
and `60abbea94acc621543ae52710acaeee53f994d185ef0f9df5e951d414d4688ef`.
Its recovery review/root is
`/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_source_only_k8_execution_2d6693db_20260713T184609CST_independent_review`
and `0eb876ca7a42ea080a2816582304f596d1a68a745a804261b4fb4f59d3eb976b`.

A subsequent read-only diagnosis fully rehashed this execution/review plus the
prior ACL and loader-remediated exit-1 artifacts. One initial diagnosis stage
failed before commands because its verifier assumed current two-space manifest
format for a historical one-space manifest; that stage is retained. The
compatible retry passed and independently reviewed these facts:

- three CARLA starts have now reached the UE banner and exited 1 before log/RPC;
- the signed helper removed the previous `xdg-user-dir: not found` stderr, but
  exit 1 persisted, so helper absence alone was not a sufficient remediation;
- the unchanged binary has zero missing `ldd` dependencies;
- UID 65534 can query the RTX 5090 and can read/write its GPU device nodes;
- cgroup memory events show zero OOM/kill, and `strace` is not installed;
- frozen `HOME=CarlaUE4/Saved/home` and
  `XDG_RUNTIME_DIR=CarlaUE4/Saved/xdg` are relative, which is an observation
  only and does not establish causality.

The exact internal UE cause therefore remains unknown. The successful
diagnosis/root is
`/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_exit1_read_only_diagnosis_976ba7a4_20260713T190933CST`
and `a8c71519b4f10766ba4f69ff485ff55303b6895fbcef58f8c7fff6710ddd895b`.
Independent review passed at the corresponding `_independent_review` path
with root `5f4fff594eef4839b46e31f819b828fa8763b091198dc1b563121ae1a40283d7`.

No performance, closed-loop safety, broad CAMP-over-DP-operational-Top-1,
promotion, deployment, or activation claim is added. The next continuously
authorized gate is a no-runtime preflight for a full-stdout/log diagnostic
attempt. It may alter only diagnostic capture, not DP, K=8 candidates,
scientific inputs, outcomes, metrics, or holdout access.

current_v19_status=v19_carla_xdg_closed_dependency_pre_readiness_exit1_recovery_review_and_read_only_diagnosis_passed
current_v19_artifact_scope=carla_xdg_closed_dependency_pre_readiness_exit1_recovery_review_and_read_only_diagnosis_no_candidate_or_outcome
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_xdg_closed_dependency_exit1_read_only_diagnosis_976ba7a4_20260713T190933CST_independent_review
current_v19_artifact_root_sha256=5f4fff594eef4839b46e31f819b828fa8763b091198dc1b563121ae1a40283d7
next_work_target=v19_carla_full_stdout_log_diagnostic_runtime_attempt_preflight_only_continuous_authorization

## Full-Stdout/Log Diagnostic Runtime Attempt Preflight

The next continuous-authorization gate performed no runtime or ACL mutation.
Local, origin, GitHub, and AutoDL CAMP were
`5ea824321cbccde4baddbdce5926cdcbbc9929b9`; fixed DP remained clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. The preflight fully rehashed the
current failed execution/recovery review, exit-1 diagnosis/review, corrected
ACL wrapper, runner, shipping binary, assets, harness, worker, checkpoint,
fixed arguments, and selector artifacts. It reconfirmed no peer process,
listener, runtime Saved path, execution path, or UID 65534 root traversal and
more than the 10 GiB floor.

Because `strace`, gdb, and ltrace are unavailable and no package installation
is authorized, the smallest diagnostic capture uses existing Unreal logging.
Direct binary-byte provenance found the exact UTF-16 strings `stdout`,
`FullStdOutLogOutput`, `AllowStdOutLogVerbosity`, and `Abslog`. A new unique
plan appends only these four diagnostic arguments:

```text
-stdout
-FullStdOutLogOutput
-AllowStdOutLogVerbosity
-Abslog=/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Saved/diagnostic.log
```

The absolute log remains inside the already transient UID-65534 Saved tree and
will be retained in the execution artifact. A contract test proved that all
non-path plan fields, server cwd/environment, UID/GID, Town01/RPC arguments,
readiness timeout, DP and asset hashes, five source-only steps, and forbidden-
operation exclusions are unchanged. Only the unique stage/final paths, their
step references, and four diagnostic flags differ. `bash -n`, the contract
test, and runner `--validate-only` all passed; independent review replayed them
and left the source manifest byte-identical.

The preflight artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_full_stdout_log_diagnostic_runtime_attempt_preflight_5ea82432_20260713T192404CST`
and `667aa64306e6bcaa541237b10e5c06dd655b01b13a7dca10afa2b7cf94759c74`.
Its independent review/root is the corresponding `_independent_review` path
and `bd2ebc274dae14b2122e13edde1407fbc57604e769f2d10d60c0d1892bbe8a65`.
No claim boundary changes.

current_v19_status=v19_carla_full_stdout_log_diagnostic_runtime_attempt_preflight_independent_review_passed
current_v19_artifact_scope=carla_full_stdout_log_diagnostic_runtime_attempt_preflight_independent_review_no_runtime_no_acl_mutation
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_full_stdout_log_diagnostic_runtime_attempt_preflight_5ea82432_20260713T192404CST_independent_review
current_v19_artifact_root_sha256=bd2ebc274dae14b2122e13edde1407fbc57604e769f2d10d60c0d1892bbe8a65
next_work_target=v19_carla_full_stdout_log_diagnostic_runtime_attempt_execution_only_continuous_authorization

## Full-Log Failure and Absolute-XDG Read-Only Diagnosis

The full-stdout/log attempt was bound to CAMP/GitHub/AutoDL
`d36a98e892b1941723da08cf6337a63f41764ceb` and fixed clean DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Its immediate guard rehashed the
preflight/review and prior diagnosis roots, reran plan validation, checked
GitHub main, package/binary state, no peer/listener/Saved/execution path, the
disk floor, and the mode-700 root without UID 65534 traversal. The guard/root
is
`/root/autodl-tmp/camp_dp_v19_carla_full_stdout_log_diagnostic_execution_controller_d36a98e8_20260713T192933CST`
and `b0689f76e403281fdb3916fc45d22bf92f2f166cc5805f8f5cb5edead50e3c76`.

A separately precreated wrapper-capture artifact avoided the earlier stage
visibility gap. It records the exact command, empty wrapper stdout/stderr,
direct exit 1, start/end times, and restored final state with root
`97e9dad6e12a02eaf455e84c67bbb15854316194f12e2262d62767d94f17fd08`.
The wrapper granted only `u:65534:--x`, retained read/write/list denial, and
launched the unchanged shipping binary as UID/GID 65534.

CARLA again printed only `4.26.2-0+++UE4+Release-4.26 522 0` and
`Disabling core dumps.`, then exited 1 after 0.60 seconds before RPC readiness.
Server stderr remained empty. `-stdout`, `-FullStdOutLogOutput`,
`-AllowStdOutLogVerbosity`, and the Saved-local absolute `-Abslog` produced no
log file, so the diagnostic attempt added no internal UE error text. It invoked
zero capture, materialization, CAMP worker, DP worker, or receipt commands and
generated no candidate or receipt. Outcome, metric, and holdout counters stayed
zero.

The ACL trap restored with body rc 1, restore rc 0, zero ACL/stat/xattr compare
codes, byte-equal snapshots, and blocked post-restore traversal. The failed
execution/root is
`/root/autodl-tmp/camp_dp_v19_carla_full_stdout_log_diagnostic_execution_5ea82432_20260713T192404CST.tmp`
and `2a5c0ba1b3f441dd7f5a49584f2280369f8c80955747826616d4ae18d2a7fb85`.
Independent review rehashed guard, capture, and execution, replayed every
restore/zero-call/log-inventory assertion, and passed at
`/root/autodl-tmp/camp_dp_v19_carla_full_stdout_log_diagnostic_execution_controller_d36a98e8_20260713T192933CST_independent_review`
with root `1e4a0e5da18b28f71aeb71a4c9d4e1eb746641c2b10ac646cc94d267a11c086d`.
This is the fourth UE-banner exit-1 observation; the internal cause remains
unknown rather than being renamed.

A new read-only gate then rehashed all four artifacts and retrieved the
official XDG Base Directory Specification 0.7. It establishes that paths set
in XDG base-directory variables must be absolute and relative paths should be
treated as invalid. The frozen `XDG_RUNTIME_DIR=CarlaUE4/Saved/xdg` violates
that contract. Under UID/GID 65534, the current value caused
`systemd-path user-runtime` to exit 1 with `No such device or address`; the
proposed value
`/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Saved/xdg` exited zero and
returned itself. Prior execution evidence proves the runner creates that
directory as UID/GID 65534, mode 0700.

This is an independently established environment-contract defect, not proof
of the CARLA exit-1 cause. The diagnosis/root is
`/root/autodl-tmp/camp_dp_v19_carla_absolute_xdg_runtime_dir_read_only_diagnosis_d36a98e8_20260713T193206CST`
and `da6810fe60acd4f290531f696a57c4c2a39b89e026ac3e14593eeaf484995c7f`.
Its independent review/root is the corresponding `_independent_review` path
and `d5e384fe5adf1bb37ca01dc91383495024c2fb1b77ba39558abcbc93bd1ebb8c`.
The next continuously authorized gate is a no-runtime preflight for attempt 1
of this absolute-XDG hypothesis, changing only `XDG_RUNTIME_DIR` while retaining
full-log capture and every scientific boundary.

current_v19_status=v19_carla_full_stdout_log_diagnostic_execution_failure_and_absolute_xdg_read_only_diagnosis_independent_review_passed
current_v19_artifact_scope=carla_full_stdout_log_diagnostic_execution_failure_and_absolute_xdg_read_only_diagnosis_no_candidate_or_outcome
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_absolute_xdg_runtime_dir_read_only_diagnosis_d36a98e8_20260713T193206CST_independent_review
current_v19_artifact_root_sha256=d5e384fe5adf1bb37ca01dc91383495024c2fb1b77ba39558abcbc93bd1ebb8c
next_work_target=v19_carla_absolute_xdg_full_stdout_log_runtime_attempt_preflight_only_continuous_authorization

## Absolute-XDG Full-Log Runtime Attempt Preflight

The first remediation attempt for the independently established relative-XDG
contract defect began with a no-runtime preflight at CAMP/GitHub/AutoDL
`8010cdd7058442e3990e34df336d77a91f51caec` and fixed clean DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. It rehashed the full-log plan,
absolute-XDG diagnosis/review, wrapper, runner, scripts, assets, and binary;
reconfirmed the disk floor, mode-700 root, absent UID traversal, and no peer,
listener, Saved, or execution path.

A whole-object contract test built the new unique plan from the reviewed
full-log plan and proved the sole environment change:

```text
XDG_RUNTIME_DIR:
  CarlaUE4/Saved/xdg
  -> /root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Saved/xdg
```

HOME, PATH, LD_LIBRARY_PATH, cwd, UID/GID, the four logging arguments, Town01,
RPC port, readiness timeout, all five pipeline steps, fixed DP/checkpoint/
args/selector hashes, K=8 contract, seed, and forbidden-operation exclusions
remain unchanged. Under UID/GID 65534 with the proposed environment,
`systemd-path user-runtime` exited zero, printed the exact absolute path, and
had empty stderr. `bash -n`, plan tests, and runner validate-only passed.

The preflight/root is
`/root/autodl-tmp/camp_dp_v19_carla_absolute_xdg_full_stdout_log_runtime_attempt_preflight_8010cdd7_20260713T193613CST`
and `ee2e5c757d63ba7e5d3d5dba32c587ec64800bd0fff4afaee16a16684bdac0e1`.
Independent review replayed every comparison and validation, left the source
manifest unchanged, and passed at the corresponding `_independent_review`
path with root
`742d9f7d69e3dae9b317395d6b1d8333df212335a82e5b2f69774a485a88383d`.
No ACL, CARLA, worker, candidate, receipt, metric, outcome, or holdout activity
occurred, and no claim boundary changed.

current_v19_status=v19_carla_absolute_xdg_full_stdout_log_runtime_attempt_preflight_independent_review_passed
current_v19_artifact_scope=carla_absolute_xdg_full_stdout_log_runtime_attempt_preflight_independent_review_no_runtime_no_acl_mutation
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_absolute_xdg_full_stdout_log_runtime_attempt_preflight_8010cdd7_20260713T193613CST_independent_review
current_v19_artifact_root_sha256=742d9f7d69e3dae9b317395d6b1d8333df212335a82e5b2f69774a485a88383d
next_work_target=v19_carla_absolute_xdg_full_stdout_log_runtime_attempt_execution_only_continuous_authorization

## Absolute-XDG Failure and Missing Vulkan Loader Diagnosis

Absolute-XDG hypothesis attempt 1 was bound to synchronized CAMP/GitHub/AutoDL
`e54414a8d5119c810a0ab9ccf422ce5f8db6cf86` and fixed clean DP. The controller
reused the reviewed full-log/ACL implementation, substituting only the new
preflight/diagnosis roots, HEAD, schema name, and exact unique execution path.
The sealed controller source SHA is
`6ae3781bc5e661e7334bf3d4941f9c65fbfb3ae41c425d1f2f245d4aba49790b`.

The immediate guard rehashed the absolute-XDG preflight/review and diagnosis/
review, checked GitHub, plan validation, package/binary/disk state, and absent
peer/listener/Saved/execution state. Its root is
`2dc93de08a3fe5bed4e5cdc4dcc22bbc07589d95c160ca9ca43144a0f3c4b152`.
The separate complete wrapper capture has root
`76e938c73f805ba4d5c2301aafe5522c5fd938e848086891ae78cfca2cf25cef`.

CARLA started with absolute XDG, retained full-log flags, and unchanged
scientific inputs, but again printed only the UE 4.26.2 banner and core-dump
line before exit 1 at 0.60 seconds. It never reached RPC readiness, produced
no diagnostic log, and invoked zero pipeline steps. No candidate or receipt
was generated and outcome/metric/holdout counters remained zero. The ACL trap
recorded body rc 1, restore rc 0, zero ACL/stat/xattr comparisons, byte-equal
snapshots, and blocked post-restore traversal. Execution/review roots are
`4ffd2ac913cc7e36ad2e8821ca024748d32731103cf4eaed6ec7434fb1ef607c`
and `051b71ea9cfba19717e874badd1871ac680bac2a0b7a34d4ef37a472a50cbdb1`.
Thus changing only XDG was not a sufficient remediation; the hypothesis has
used one of at most three fail-closed attempts.

A subsequent read-only graphics diagnosis rehashed all four artifacts and
found a distinct dependency gap:

- the unchanged shipping binary contains ASCII/UTF-16 references to
  `libvulkan.so.1`, `VulkanRHI`, and `vkCreateInstance`;
- NVIDIA's ICD JSON points to an existing `libGLX_nvidia.so.0` driver;
- `ldconfig`, `/lib`, `/usr/lib`, and the CARLA runtime contain no
  `libvulkan.so*` loader, and dpkg reports no installed `libvulkan1`;
- root `ctypes.CDLL("libvulkan.so.1")` fails with exact error
  `cannot open shared object file: No such file or directory`;
- Ubuntu apt metadata offers `libvulkan1 1.3.204.1-2`, and a no-recommends
  simulation proposes exactly one new package, zero upgrades/removals.

Earlier `ldd` checks did not expose this gap because Vulkan is runtime-loaded
rather than an ELF `NEEDED` dependency. The gap is independently established,
but its sole responsibility for CARLA exit 1 remains unproven until a strictly
signed, exact-version, rollback-safe remediation is validated. The diagnosis/
review roots are
`d522d77083cec6e7edc6adf31389d2e345fe171a067a6af89e02fd168a6009c7`
and `e1454d797d0ffece63e875f12209c529d98e2174eede9602bdc12653a21df21c`.
No package was installed and no claim boundary changed.

current_v19_status=v19_carla_absolute_xdg_execution_failure_missing_vulkan_loader_diagnosis_independent_review_passed
current_v19_artifact_scope=carla_absolute_xdg_execution_failure_missing_vulkan_loader_read_only_diagnosis_no_package_no_candidate_or_outcome
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_missing_vulkan_loader_read_only_diagnosis_e54414a8_20260713T194347CST_independent_review
current_v19_artifact_root_sha256=e1454d797d0ffece63e875f12209c529d98e2174eede9602bdc12653a21df21c
next_work_target=v19_signed_libvulkan1_exact_package_preflight_only_continuous_authorization

## Signed Exact libvulkan1 Package Preflight

The preflight at synchronized CAMP/GitHub/AutoDL
`1b7d7c0190f57ed058695a548753d5be700b4afa` performed no installation and no
runtime start. Ubuntu jammy/main's `InRelease` signature and signed
uncompressed package-index hash/size were verified before selecting exact
`libvulkan1 1.3.204.1-2` for amd64. Its signed stanza, apt metadata, and the
downloaded 128,014-byte `.deb` agree on SHA256
`192adcff489996b3398e7e7c0012b98e9586b46fe9a9eb13fb02c0feba88548b`.
The no-recommends transaction simulation contains only `libvulkan1`, with
zero upgrades or removals.

Before any future mutation, the gate sealed every active dpkg configuration
file and all path-exclude/path-include rules. There are zero effective rules
and zero exemptions for this package; the real loader and SONAME symlink are
both present in the package manifest and cannot be exempted. The original
dpkg-query state is package-not-found, all package-owned paths and loader
paths were baselined, and a purge-only rollback check proved that exact
baseline. Autoremove, cache cleanup, upgrades, unrelated package changes, and
CARLA start are forbidden by the contract.

The source artifact/root is
`/root/autodl-tmp/camp_dp_v19_libvulkan1_signed_exact_preflight_1b7d7c01_20260713T195033CST`
and `3e9865dd8f1bc71349adb0ad7fdd552204cf54f35a88aefb2ba077893939e182`.
Independent review rehashed the immutable source manifest and `.deb`, replayed
signature/version/single-package/rollback checks, confirmed dpkg configuration
unchanged and the package still absent, and passed at the corresponding
`_independent_review` path with root
`7d34fce54be5f080ffa85f88e36ac13007b86acc2f821ec85718286b3743ea6a`.
No candidate, outcome, metric, or holdout activity occurred. Missing-loader
causality for the prior CARLA exit 1 remains unproven.

current_v19_status=v19_signed_libvulkan1_exact_package_preflight_independent_review_passed
current_v19_artifact_scope=signed_exact_libvulkan1_package_preflight_rollback_contract_and_independent_review_no_install_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_libvulkan1_signed_exact_preflight_1b7d7c01_20260713T195033CST_independent_review
current_v19_artifact_root_sha256=7d34fce54be5f080ffa85f88e36ac13007b86acc2f821ec85718286b3743ea6a
next_work_target=v19_signed_libvulkan1_exact_package_install_and_integrity_validation_only_continuous_authorization

## Exact libvulkan1 Install and Integrity Validation

At synchronized CAMP/GitHub/AutoDL
`13e6241b561aed21dba5b13eca616ab1ec9e1c96`, the fail-closed package
controller ran the exact signed local `.deb` transaction. Its first validation
harness incorrectly required absent `/usr/bin/python3`. The controller purged
only `libvulkan1`, and root
`e6bdb05e0ef6b211870e47cd99bc7414b18a41ba70908b2dcb03cf426712088b`
proves the original package-not-found, package-path, dpkg-config, and no-loader
baseline was restored. Read-only diagnosis/review roots
`6fa504607d595e8ddb00c8d7bb1cf8bbac3a5366995aefdd3e514ebba811f3c3`
and `a058e8b043e4bcbdb135324a0d7c125896bacbc1115904e7041b694bf81110eb`
bound the defect and replaced the probe with root conda `ctypes` plus UID 65534
`setpriv`/`LD_PRELOAD` execution of `/bin/true`.

The second transaction passed all loader checks but the reviewer rejected
shared parent directories because its owner parser examined only the first
package in dpkg's comma-separated ownership list. It again purged only the
target and produced the same restored-baseline root. The preserved integrity
output shows `dpkg -V`, tar/list equality, loader, SONAME, `ldd`, `ldconfig`,
root load, and UID 65534 load had all passed; every rejected directory had
correct content and raw ownership containing `libvulkan1:amd64`. Read-only
diagnosis/review roots are
`1c6d3de9992b7c920f68a1904e23b58f37cb7b8596567d9545a71a017918c4d5`
and `aa1c950b9a4493d208873d0abe9ff497b99aca8f380415417fd8158ffacf47d7`.
The fix parses the exact comma-separated owner set before the path suffix.

The final bounded execution passed. Package snapshots changed only
`libvulkan1:amd64`; dpkg's installed path set exactly equals the signed tar
manifest; all package files and symlinks match archive type/mode/owner/hash,
pre-existing shared directories retain baseline metadata and include the
target owner, and `dpkg -V` is empty. SONAME target
`libvulkan.so.1.3.204`, `ldd`, `ldconfig`, root `ctypes.CDLL`, and UID 65534
`LD_PRELOAD` execution all pass with unchanged dpkg configuration. Source and
independent-review roots are
`57eb755770f0d24e4eb1330412a69eb0378e775806d5154d87e5fe663cd93194`
and `44d99f3b5042b64a66ee9f9cb3ba89cdfb126509fb1f2e75c35a965f9548089b`.
Exact `libvulkan1 1.3.204.1-2` is temporarily retained under the success
contract. No runtime, candidate, outcome, metric, or holdout activity occurred;
prior exit-1 causality remains unproven.

current_v19_status=v19_signed_libvulkan1_exact_package_install_integrity_independent_review_passed
current_v19_artifact_scope=exact_signed_libvulkan1_single_package_install_integrity_validation_and_independent_review_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_libvulkan1_install_integrity_13e6241b_20260713T200103CST_independent_review
current_v19_artifact_root_sha256=44d99f3b5042b64a66ee9f9cb3ba89cdfb126509fb1f2e75c35a965f9548089b
next_work_target=v19_carla_missing_vulkan_loader_remediation_runtime_attempt_preflight_only_continuous_authorization

## Vulkan-Loader Runtime Attempt Preflight

At synchronized CAMP/GitHub/AutoDL
`364af116fd32e0921bb6188592c7add42d09e470`, the no-runtime preflight verified
the prior absolute-XDG failure review, missing-loader diagnosis review, and
exact package install/review manifests. The retained exact package replayed
its installed-path, owner/mode/hash, empty `dpkg -V`, SONAME, `ldd`/`ldconfig`,
root `ctypes`, and UID 65534 load checks successfully.

The execution plan was made by substituting only fresh stage/final paths in
the already reviewed absolute-XDG/full-log plan. A whole-object comparison
proves server argv/environment, logging flags, Town01/RPC/readiness, all five
source-only steps, capture source head, fixed DP/checkpoint/args/selectors,
K=8/scientific contracts, and forbidden-operation counters unchanged. Runner
validate-only and exact UID XDG probes pass. No process/listener/Saved/staging
state exists; root ACL is restored and UID 65534 cannot traverse it; disk is
above the 10 GiB floor.

The source artifact/root is
`/root/autodl-tmp/camp_dp_v19_carla_vulkan_loader_runtime_attempt_preflight_364af116_20260713T200519CST`
and `b80b93515a9c60fbc66bcf43b1185c71b3a0846a1e7746c30d5659f0ad9ab553`.
Independent review repeated package/plan/runtime-absence checks without
changing the source manifest and passed at the corresponding review path with
root `ecb6d0302f39a039b9e53092d6e51742833061e98751c65292ad1c43b19d8f06`.
This freezes attempt 1 for the independently supported missing-Vulkan-loader
root cause. It does not yet prove causality, and it performed no ACL mutation,
runtime start, candidate, outcome, metric, or holdout activity.

current_v19_status=v19_carla_missing_vulkan_loader_remediation_runtime_attempt_preflight_independent_review_passed
current_v19_artifact_scope=missing_vulkan_loader_remediation_runtime_attempt_preflight_and_independent_review_no_runtime_no_acl_mutation
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_vulkan_loader_runtime_attempt_preflight_364af116_20260713T200519CST_independent_review
current_v19_artifact_root_sha256=ecb6d0302f39a039b9e53092d6e51742833061e98751c65292ad1c43b19d8f06
next_work_target=v19_carla_missing_vulkan_loader_remediation_runtime_attempt_execution_only_continuous_authorization

## Vulkan-Loader Remediation Runtime Attempt 1 Failure

The execution controller was generated from the prior sealed implementation by
exact one-count substitutions for synchronized HEAD
`a964961ef01177c9c1b2488cc5e54e447be1bcf5`, the new preflight/diagnosis, and
the exact package evidence, plus an installed-loader integrity guard. Static
source/review roots are
`b05e9df28484d97ae132b2918771196c11b1200b510a1d5310f108d06ece0ca5`
and `310cc12b7c4ed1dc6ace8145604f78f52b1297082d1dbf4e272cdf3996520270`.

Its first launch guard observed GitHub HTTP 503 before the wrapper, ACL, or
CARLA was reached. This preserved failure and the independent read-only retry
that matched GitHub HEAD have roots
`3db0edcc749d09ea21bc1a882b845a45289150fb7920492d4fe61ac2b7d2b275`
and `70ae87e27255ec6ae95fd2b5e4bfc4c214bcc5803b203aee4eb550d59908f866`.
It consumed no runtime attempt.

The fresh guard then passed all HEAD, fixed-DP, exact-package, no-peer,
no-listener, no-Saved/staging, disk, plan, and root-restoration checks before
the unique launch. CARLA ran with the frozen absolute-XDG/full-log command and
exact `libvulkan1 1.3.204.1-2`, but printed only two banner/core-dump lines and
exited 1 after 1.13 seconds before readiness. It produced no diagnostic log;
all five source-only pipeline commands remained uncalled. The ACL trap recorded
body rc 1, restore rc 0, zero ACL/stat/xattr comparisons, byte-equal original/
restored state, and blocked post-restore traversal. Guard/capture/execution/
review roots are
`f4072ef0e42dcde625267fd813a4ddbc50241c3140f44df43b38ffbf7f2a9aae`,
`44b92bec9a897f085d838db4e0c7d40d6b33452b6165255937f01182be79e5dd`,
`46aa8ac60eda753cf8e8144e1fbfa0f9fc46d38860df7f727ea2453c641d7e98`,
and `de9119a29557ac071b64bbb5f2fb87555ea0c6d15a7ee5be1bb0c56fcc621af9`.

Thus the loader gap was real but its remediation was not sufficient for
readiness; missing-loader root-cause attempt 1/3 is consumed. Exact package
integrity remains valid. No candidate, receipt, outcome, metric, or holdout
activity occurred and no claim boundary changed.

current_v19_status=v19_carla_missing_vulkan_loader_remediation_runtime_attempt_1_failure_independent_review_passed
current_v19_artifact_scope=missing_vulkan_loader_remediation_runtime_attempt_1_pre_readiness_failure_acl_restoration_and_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_vulkan_loader_execution_controller_a964961e_20260713T201212CST_execution_review_retry1
current_v19_artifact_root_sha256=de9119a29557ac071b64bbb5f2fb87555ea0c6d15a7ee5be1bb0c56fcc621af9
next_work_target=v19_carla_post_vulkan_loader_failure_read_only_root_cause_diagnosis_only_continuous_authorization

## Post-Loader Graphics and Headless EGL-ICD Diagnosis

At synchronized CAMP/GitHub/AutoDL
`6cfbaea0f06616b33df5495d5288309960c55a3e`, a compiled, temporary no-CARLA
probe exercised Vulkan loader, NVIDIA ICD, instance creation, and physical-
device enumeration. The first evidence-capture run encountered only a
non-UTF-8 loader-debug decoding error; its temporary executable was still
removed and the evidence reader was narrowed to replacement decoding.

The corrected root and UID 65534 probes both load `libvulkan.so.1`, report
loader 1.3.204, and enumerate two instance extensions, but `vkCreateInstance`
returns `VK_ERROR_INCOMPATIBLE_DRIVER (-9)`. `VK_LOADER_DEBUG=all` reports that
the configured `libGLX_nvidia.so.0` cannot yield `vkCreateInstance` through
`vk_icdGetInstanceProcAddr`; forcing the same ICD JSON produces the same result.
The loader/driver/kernel versions and libraries are present and aligned at
595.71.05. Probe/review roots are
`92a9a10a12fb7bc23bc1851e22e78601d5a29ae97e53e2c12820dafb4c10d66f`
and `81a9c2703f974fb41b1e7e2e63d29878f1a2f5cce8c3a482ef9824cfa3cfa934`.

Direct negotiation against `libGLX_nvidia.so.0` verifies all expected symbols
are exported, but requested loader interfaces 0, 1 through 8, and 10 all return
`VK_ERROR_INITIALIZATION_FAILED (-3)`, leave the version unchanged, and return
a null create pointer. UID 65534 independently reproduces versions 5 through 7.
The source/review roots are
`54bcdcb4d7b9dd92e4521707d8a6bb05fe4e93389c1d22ff10758c34450f3c26`
and `6087121e51d9141b8e0a48dde81f031695d96cc228de93dc6783e93506fb1b8c`.

Finally, an A/B probe created a temporary ICD JSON that differed only by
pointing to the already installed `libEGL_nvidia.so.0`. Root and UID 65534 both
then completed loader discovery, instance creation, and physical-device
enumeration with exit 0. The independent reviewer replayed UID 65534 and
confirmed the result. `/etc` and system ICD files were never modified; both
temporary probe/manifest files were explicitly removed. Source/review roots are
`371e2a466b6a370e8e990937d994f3da8a768ee75a97edb6bd84c0c4f5fbf2fd`
and `7ef2b3586fd7635dba7aba166da6d8632f7f71f7b67e0736b7fd64f6ccf0e5ce`.
This supports a minimal temporary headless EGL-ICD environment remediation,
but does not yet establish CARLA readiness or prior exit-1 sole causality. No
runtime, ACL, candidate, outcome, metric, or holdout activity occurred.

current_v19_status=v19_carla_post_loader_graphics_diagnosis_headless_egl_icd_probe_independent_review_passed
current_v19_artifact_scope=post_loader_vulkan_icd_negotiation_and_temporary_headless_egl_icd_ab_probe_independent_review_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_headless_egl_icd_probe_6cfbaea0_20260713T202749CST_independent_review
current_v19_artifact_root_sha256=7ef2b3586fd7635dba7aba166da6d8632f7f71f7b67e0736b7fd64f6ccf0e5ce
next_work_target=v19_carla_headless_egl_icd_runtime_attempt_preflight_only_continuous_authorization

## Headless EGL-ICD Runtime Attempt Preflight

At synchronized CAMP/GitHub/AutoDL
`87301d4d47c43bf4bf1a0d4dbfd2729ed5faa231`, the no-runtime preflight rehashed
the prior failed execution, successful headless EGL-ICD A/B diagnosis, exact
package install, and reviews. It created a new plan from the reviewed
absolute-XDG/full-log plan by substituting only unique stage/final paths and
adding server-only
`VK_ICD_FILENAMES=/tmp/camp_dp_v19_nvidia_egl_icd_87301d4d.json`.

The temporary manifest's canonical JSON, mode 0644, and SHA256
`25e77ea0175e0c4e7af36d7e002db235ba50305dd8d2f801487a17513184ec65`
are frozen. It points only to existing `libEGL_nvidia.so.0`; the execution
contract creates it immediately before wrapper launch and deletes it from a
`finally` path on success, failure, or interruption. Preflight and independent
review both recreated the exact manifest, passed the complete UID 65534 Vulkan
instance/device probe, and removed all temporary files.

Whole-object comparison proves server argv, other environment, Town01/RPC/
readiness, all five pipeline commands, fixed DP/checkpoint/args/selectors,
capture source, K=8, and scientific/forbidden-operation fields unchanged.
No process/listener/Saved/staging state exists; root ACL is restored and disk
is above the floor. Source/review roots are
`b40e6228d40cb869a68a6c54cf73e331ab81a1a973337cf09984ed7406bb7311`
and `0f673bc72a082a1378cf8dc7f27e130379aaf4d3c858b32365b140deab3a5f73`.
No CARLA, ACL, candidate, outcome, metric, or holdout activity occurred. This
freezes headless-GLX-ICD incompatibility remediation attempt 1 without yet
claiming CARLA readiness or sole causality.

current_v19_status=v19_carla_headless_egl_icd_runtime_attempt_preflight_independent_review_passed
current_v19_artifact_scope=headless_egl_icd_temporary_manifest_runtime_attempt_preflight_and_independent_review_no_runtime_no_acl_mutation
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_headless_egl_icd_runtime_attempt_preflight_87301d4d_20260713T203124CST_independent_review
current_v19_artifact_root_sha256=0f673bc72a082a1378cf8dc7f27e130379aaf4d3c858b32365b140deab3a5f73
next_work_target=v19_carla_headless_egl_icd_runtime_attempt_execution_only_continuous_authorization

## Headless EGL-ICD Runtime Readiness and Materialize Git-Head Diagnosis/TDD Fix

At synchronized CAMP/GitHub/AutoDL
`f341898625fa0b9d9fb74b16e22609d02edf94d1`, the execution controller was
generated from the reviewed implementation with only the frozen headless
EGL-ICD preflight and unique artifact substitutions. Controller static source
and review roots are
`a0f9fd00e8231408ac3c31d2cd1f2e64f860ce8215692912951d89120d8750c3`
and `8644dd1dac7ba71aa308193b50670983e23480f015173fd9ad1c3b5090a2ff46`.

The guard reverified local/GitHub/AutoDL HEAD, fixed clean DP, exact retained
packages, no peer/listener/Saved/staging state, disk, restored root ACL, and the
exact plan. It created the canonical mode-0644 temporary manifest pointing to
`libEGL_nvidia.so.0`, entered the reviewed UID 65534 execute-only ACL wrapper,
and launched CARLA once. CARLA passed RPC readiness for the first time. The
source-only capture step exited 0 and wrote immutable `capture.json` with
SHA256 `ba0fdd6d0b0f2d0582e96b0aaf7511b3b51d13d591d9635b7f3a475e06f550c5`.

The next materialize step exited 1. Its empty stdout and exact stderr show
`ValueError: CAMP head SHA256 is invalid` at
`_require_sha256(camp_head, "CAMP head")`. The command supplied the actual
40-hex CAMP commit and fixed 40-hex DP commit; the harness incorrectly applied
its 64-hex content-digest validator. This happened before either request
directory or `lifting_context.json` was written. The remaining DP workers and
receipt step were not called. The server later reported signal 11 during the
failed-pipeline cleanup interval, but current evidence does not attribute that
as the materialize stop's cause. Guard/capture/execution/review roots are
`ec1ae5c53ed6eaa1eaebb2134b9798907dbd9d276a24909f0d02b77a03f2d15b`,
`5667cd20ca73de8cab94c41995b4addca39800bcfbcfbda24e3cfcc821d6c43c`,
`7be9b8ac748b484f9b8d2c46a4d7c2c18e9f11be978ac4d09a9106b2ab5a2a8c`,
and `5406159e0253dc6335dfc0cf5e8528cd56116d059cb6895e22785c55c88398e8`.
The temporary ICD manifest was removed and the ACL/stat/xattr restoration was
independently verified.

The first read-only diagnosis driver rejected four pre-existing unrelated
untracked CAMP paths because its clean-tree check was over-broad. It created no
runtime or scientific output; its preserved failure/review roots are
`06df56f57f1ef5cdd9543448e6936875725af6cffc54391b0f7f539c4aaeca34`
and `28a3c94862569227e6b87732dd32f5aabd6975f0efdafe9394427aa5d8e6d6b1`.
The tracked-only rerun proved CAMP/DP tracked-clean, no relevant process, passed
readiness/capture, exact traceback/command agreement, and absence of request
outputs. Diagnosis/review roots are
`3d3cb757fd882c7c848806df929e3f42e30c6362a80d495a1d9e8f0d12bdc9dc`
and `44a9533051d1355dc64ae551e62079a464f3ecdcf40a6c6573a8475abc607e5c`.

The narrow TDD remediation changes only the two CAMP/DP head checks to an exact
40-hex Git-commit validator. Selector and source digests retain the existing
64-hex SHA256 validator. A real-head regression test failed before the change
and passes after it; a negative test rejects a 64-hex content digest where a
Git commit is required. No DP code/config/weights/checkpoint, captured source,
K=8 candidate, lifting/scientific contract, outcome, metric, or holdout changed.
Closed-loop safety and broad CAMP-over-DP claims remain unsupported.

current_v19_status=v19_carla_headless_egl_icd_readiness_passed_materialize_git_head_validation_failure_diagnosed_tdd_fix_ready
current_v19_artifact_scope=headless_egl_icd_runtime_readiness_source_capture_materialize_git_head_validation_failure_diagnosis_and_tdd_fix_no_candidate_no_outcome
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_diagnosis_f3418986_20260713T204056CST_review
current_v19_artifact_root_sha256=44a9533051d1355dc64ae551e62079a464f3ecdcf40a6c6573a8475abc607e5c
next_work_target=v19_carla_materialize_git_head_validation_tdd_fix_static_review_and_runtime_preflight_only_continuous_authorization

## Materialize Git-Head Fix Static Review and Runtime Attempt 1 Preflight

At synchronized CAMP/GitHub/AutoDL
`b82eb784a43289f50f5bb857740f09f8a0808ff2`, the remote static contract
matched source-probe SHA256
`931366a927c53e2c9045caec589814c75aff2fd979ea8ac86e6b75368d674c41`
and test SHA256
`6d40349ab127c09d0987fc027be135a55b008caf1d979276531a8831997d477f`.
It verified both CAMP/DP calls use the exact 40-hex Git-commit validator while
the 64-hex SHA256 validator remains on selector/source content digests. The
source-probe plus live-pointer suite reported `8 passed` in both the source and
independent review; `py_compile` and `git diff --check` also passed.

The no-runtime preflight rehashed the prior headless EGL-ICD preflight/review,
the readiness/capture/materialize-failure execution/review, the direct Git-head
diagnosis/review, and the exact retained `libvulkan1` install/review. Package
integrity replay passed. UID 65534 independently completed the temporary
EGL-ICD Vulkan instance/device probe twice, and each probe/manifest was removed.

The guard state proves local/origin/GitHub CAMP HEAD agreement, fixed clean DP,
no relevant process or RPC listener, absent runtime Saved and new execution
paths, root mode 0700 with UID 65534 traversal blocked, and disk above the
10-GiB floor. The execution plan is the last reviewed headless plan with only
fresh stage/final paths:

- stage:
  `/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_fix_execution_b82eb784_20260713T204700CST.tmp`
- final:
  `/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_fix_execution_b82eb784_20260713T204700CST`

Whole-object checks keep the server argv/environment, temporary ICD manifest,
all source-only steps, fixed DP/checkpoint/args/selectors, K=8, route/speed/
lifting/tolerance/eligibility, seeds, and forbidden-operation counters
unchanged. Runner validate-only passed. Source and independent-review roots are
`0bf3b1915a7bd49cf94ef4d6fd5f464a47b62af734d91a5baaae94aca3731cea`
and `0b1d95cc2b1e54de5dc42fed8f0cdf78af774b33144f6b9a2708e29f70e8c1f8`.
This freezes attempt 1 for the independently supported CAMP-side materialize
Git-head validator root cause. No CARLA, ACL mutation, DP worker, candidate,
outcome, metric, or holdout activity occurred; claim boundaries are unchanged.

current_v19_status=v19_carla_materialize_git_head_validation_tdd_fix_static_review_runtime_preflight_independent_review_passed
current_v19_artifact_scope=materialize_git_head_validation_tdd_fix_static_review_runtime_attempt_1_preflight_and_independent_review_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_fix_runtime_preflight_b82eb784_20260713T204700CST_independent_review
current_v19_artifact_root_sha256=0b1d95cc2b1e54de5dc42fed8f0cdf78af774b33144f6b9a2708e29f70e8c1f8
next_work_target=v19_carla_materialize_git_head_validation_remediation_runtime_attempt_1_execution_only_continuous_authorization

## Materialize Remediation Pre-Start Harness-SHA Failure

At synchronized CAMP/GitHub/AutoDL
`763190831cae8ae9efe73456d4c9f64de2fe8caa`, the first controller-generation
call stopped before creating its target because it addressed the already sealed
source static review with an incorrect `_independent_review` suffix. The
corrected generator used the exact `_static_review` artifact, preserved that
path-attribution failure inside its output, and changed only current CAMP HEAD,
preflight roots, and the attempt label in the previously reviewed controller.
Static controller source/review roots are
`b350b4e31a1425b3659a5487c4f9ae9481c16b76359895bb89580b50ed08f92d`
and `bbde55a0b8c7546947beb9a73c68feccc5a9bdcaa8dd39e757beec256986d4b7`;
controller SHA256 is
`6d2199814f39f4c605e3bc3f695f15b16e1bd4636462d37aab2bfdc2e2ef6ad2`.

The first controller invocation omitted its contract-required pre-created
`GUARD_STAGE` and stopped on the initial assertion. It performed no guard,
manifest, ACL, or runtime action. The repeated invocation created only that
unique mode-0700 staging directory first. Its guard then passed synchronized
HEAD/GitHub, fixed clean DP, package, no peer/listener/Saved/staging, restored
root, disk, and plan checks before entering the reviewed wrapper.

Inside the wrapper, the runner failed at line 28, before `COMMAND.resolved.json`
and before the server variable/start block, with `ValueError: harness SHA
drift`. The preflight plan retained the pre-fix harness SHA256
`45801d5653cc5f04a000af033e1ac3c57ec2127f390ede68bcd98f8af698a86a`,
while synchronized source SHA256 is
`931366a927c53e2c9045caec589814c75aff2fd979ea8ac86e6b75368d674c41`.
The prior preflight correctly tested the new source but incorrectly asserted
that only execution paths needed plan replacement; it did not update the plan's
integrity pin.

The ACL trap reports `body_rc=1`, `restore_rc=0`, all ACL/stat/xattr comparison
rc values 0, and `blocked_after_restore=true`; original and restored files are
byte-equal. Root is mode 0700, UID 65534 cannot traverse, the temporary manifest
is absent, and there is no process/listener/Saved state. Guard, wrapper-capture,
execution, and independent-review roots are
`39ecba553e706d3ef47fcc268363b93f5a4ae4ac883b7dd8cfbf87605238e69d`,
`bb263568bd6cc4ddb151dca9cb3ae57dba0d0a30bd8dfaee74d18fe0d304155d`,
`26c17fbc2e36160f7dbc5c4a3931003a699af57c02132361cda510dee9c71946`,
and `a6542a10376bbb1b26bdd3e849119de9c82be8b8bd56f2466ec8708d905b04ab`.
CARLA and DP were not started; no candidate, outcome, metric, or holdout access
occurred. Materialize Git-head root-cause attempt 1 is therefore not consumed.
The next preflight may update only fresh execution paths plus the harness
integrity pin to the exact committed source SHA; scientific contracts remain
unchanged.

current_v19_status=v19_carla_materialize_git_head_remediation_prestart_harness_sha_drift_failure_independent_review_passed
current_v19_artifact_scope=materialize_git_head_remediation_prestart_harness_sha_drift_failure_acl_restoration_and_independent_review_no_runtime_attempt_consumed
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_execution_controller_76319083_20260713T205117CST_execution_review
current_v19_artifact_root_sha256=a6542a10376bbb1b26bdd3e849119de9c82be8b8bd56f2466ec8708d905b04ab
next_work_target=v19_carla_materialize_git_head_remediation_harness_sha_corrected_runtime_preflight_only_continuous_authorization

## Harness-SHA-Corrected Materialize Runtime Attempt 1 Preflight

At synchronized CAMP/GitHub/AutoDL
`a85109ffd99899334964a1687cfe7954d93bd35a`, the no-runtime preflight verified
the sealed failed preflight/review, pre-start failure/review, original CARLA
readiness/capture failure/review, Git-head diagnosis/review, and exact package
install/review. It then derived the new plan from the sealed failed plan with
exactly two permitted change classes:

- fresh execution stage/final paths;
- `harness_sha256` changed from pre-fix
  `45801d5653cc5f04a000af033e1ac3c57ec2127f390ede68bcd98f8af698a86a`
  to committed fixed-source SHA256
  `931366a927c53e2c9045caec589814c75aff2fd979ea8ac86e6b75368d674c41`.

The new stage/final paths are:

- `/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_harness_sha_corrected_execution_a85109ff_20260713T205709CST.tmp`
- `/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_harness_sha_corrected_execution_a85109ff_20260713T205709CST`

Whole-object comparison keeps server argv/environment, temporary EGL-ICD
manifest, all five source-only pipeline steps, fixed DP/checkpoint/args/
selectors, K=8, route/speed/lifting/source/tolerance/eligibility, seeds, and
forbidden-operation counters unchanged. Both source and independent review ran
the source-probe/live-pointer suite with `8 passed`; exact source/test SHA,
40-hex Git and 64-hex content validators, `py_compile`, and diff check passed.
Exact package integrity and UID 65534 EGL/Vulkan were replayed, with temporary
files removed. Runner validate-only, synchronized local/origin/GitHub CAMP,
fixed clean DP, restored root, no process/listener/Saved/staging, and disk floor
all passed.

Source/review roots are
`12033a3d5cddbaacfca3c9162234acd0c646ff2cda9997b9865400f0a164dabc`
and `a8c2bff7cc79830f86f60d905f10a090f216798f7e384d79a39ffb670ba58f45`.
No CARLA, ACL mutation, DP worker, candidate, outcome, metric, or holdout
activity occurred. Materialize Git-head root-cause attempt 1 remains
unconsumed and is ready under the corrected integrity contract. Claim
boundaries remain unchanged.

current_v19_status=v19_carla_materialize_git_head_remediation_harness_sha_corrected_runtime_preflight_independent_review_passed
current_v19_artifact_scope=materialize_git_head_remediation_harness_sha_corrected_runtime_attempt_1_preflight_and_independent_review_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_harness_sha_corrected_runtime_preflight_a85109ff_20260713T205709CST_independent_review
current_v19_artifact_root_sha256=a8c2bff7cc79830f86f60d905f10a090f216798f7e384d79a39ffb670ba58f45
next_work_target=v19_carla_materialize_git_head_remediation_runtime_attempt_1_execution_only_continuous_authorization

## Source-Only K=8 Runtime Passed: Zero Legal Paired Support Hard Stop

At synchronized CAMP/GitHub/AutoDL
`c8953d6c6d650219103626ddbde33bfed416cdfc`, the execution controller was
derived from the last sealed controller by replacing only current HEAD and the
harness-SHA-corrected preflight/review roots. Static controller source/review
roots are
`8b73b24f517a22fc1bddb8751b4c3835751c67de830664260e7710ef398d9cc6`
and `87c75fa5be895abfeefe97a16cd53c3d50198d5a6c73c9b2148dd2dba790557f`;
controller SHA256 is
`e44d24738d25394ca0cbd0d1d8f6fa3ce952b84f064fc07a35804ed733de7176`.

The unique launch guard passed synchronized local/origin/GitHub CAMP HEAD,
fixed clean DP, exact package, corrected harness pin, no peer/listener/Saved/
staging state, root restoration, disk, and frozen-plan checks. It created the
exact temporary EGL-ICD manifest, entered the UID 65534 execute-only ACL
wrapper, and launched CARLA. CARLA reached RPC readiness. The complete source-
only pipeline then reported exit 0 for all steps:

- `capture=0`
- `materialize=0`
- `camp_worker=0`
- `default_worker=0`
- `receipt=0`

Runtime result passed in `32.86031484603882` seconds. Both workers used the
fixed DP HEAD, checkpoint, args, selectors, K=8 contract, and CUDA path. The
wrapper returned 0. The ACL trap restored original ACL/stat/xattrs byte-
equally, UID 65534 traversal is blocked, the temporary manifest and live Saved
tree are absent, and no related process/listener remains. Guard and wrapper-
capture roots are
`059587f9813d1eee116346a1b1045827c0a55078f7ef707d42803b4b59a3e4ce`
and `54fa3a0c8c2835ba055497defb2e068f7be71b7bf6826133486406e44f040448`.

The controller's first post-runtime evidence-validation call failed after the
passed result because it inserted `/root/autodl-tmp/camp_core` instead of
`/root/autodl-tmp/camp_core/camp_core` before importing
`camp_core.integrations`. No runtime rerun occurred. A bounded evidence-only
finalizer added the correct package root, executed the controller's original
restore/inventory/log/K=8 validation functions twice against the same immutable
execution, sealed it, and independently reviewed the seal.

The source-only scientific receipt is exact and fail-closed:

- candidate tensor SHA256 before/current/after:
  `8ca8c2e35de6363d40a154033ebee08e326114da0d7ae6790013329988f6a42c`
- DP operational Top-1 SHA256 before/current/after:
  `d01bd26929034d356e57d8f731bf90b5aba8b93b54839ee36b0f74f58a4d967c`
- candidate 0 equivalent to DP operational Top-1: `true`
- native ranked Top-1: `false`
- selected index: `null`
- record source eligible: `false`
- eligibility mask: `[false, false, false, false, false, false, false, false]`
- eligible candidate count: `0`
- reason: `all_k_source_ineligible`
- simulator arm advances / outcome reads / metric calls / holdout reads:
  `0 / 0 / 0 / 0`

Execution and independent-review roots are
`d4632d9cdcfece6c82edad73a4e3a9bc937508107cee3ee6f587af0d9a0d4652`
and `46d65dc6942e3890085acf727a72675106866e9872f5b7a03fb4c82bceb745fb`.
The captured logs include server signal 11 after the pipeline, but the pipeline
and receipt had already passed; this record makes no causal claim about that
signal. It also makes no closed-loop or safety claim.

This is the continuous-authorization hard stop for zero legal paired support.
A retry under the identical frozen contract cannot create eligibility. Any
attempt to change route construction, speed source, lifting source, tolerances,
eligibility, candidate data, or another frozen scientific field requires a new
explicit user decision. No matched closed-loop arm, SafetyCost, official metric,
or latency comparison is legal from this record. The claim taxonomy remains:
performance no-claim; bounded offline proxy supported; closed-loop safety not
supported; broad CAMP-over-DP operational Top-1 not supported; promotion,
deployment, and activation not authorized.

current_v19_status=v19_carla_source_only_k8_probe_runtime_passed_zero_legal_paired_support_independent_review_passed
current_v19_artifact_scope=source_only_fixed_dp_k8_probe_runtime_passed_candidate_immutable_zero_legal_paired_support_hard_stop_independent_review
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_carla_materialize_git_head_corrected_execution_controller_c8953d6c_20260713T210038CST_execution_review
current_v19_artifact_root_sha256=46d65dc6942e3890085acf727a72675106866e9872f5b7a03fb4c82bceb745fb
next_work_target=user_decision_required_before_any_frozen_scientific_contract_change_after_zero_legal_paired_support_hard_stop

## Zero-Support Source-Only Point Breakdown Independently Reviewed

The user explicitly superseded the preceding scientific-contract decision
boundary with a separate redesign scope. The first gate remained completely
source-only and outcome-free. At clean synchronized CAMP
`a27e292ff7154a84a62c813325da98f094f50276` and fixed clean DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, it rehashed the sealed source
execution/review, K=8 and operational Top-1 arrays, capture, route context,
lifting receipt, and the exact Town10HD OpenDRIVE whose SHA256 is
`5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7`.
No CARLA server, DP worker, pipeline, simulator arm, candidate generation,
metric, outcome, or holdout access occurred.

The complete candidate x 80 grid contains these original receipt reasons:

- `lateral_residual_exceeds_tolerance`: 154;
- `xodr_identity_mismatch`: 405;
- `route_topology_discontinuous`: 81.

The source-only reclassification retains all 640 rows and does not stop at the
first candidate error:

- route-window-before-start: 127;
- directed identity-transition sampling gap: 24;
- true lateral/non-route: 3, all candidate 7 points 77-79;
- XODR float32 station round-trip: 405;
- continuity propagated after an earlier source failure: 81.

The immutable candidate tensor and DP operational Top-1 SHA256 values remain
`8ca8c2e35de6363d40a154033ebee08e326114da0d7ae6790013329988f6a42c`
and `d01bd26929034d356e57d8f731bf90b5aba8b93b54839ee36b0f74f58a4d967c`;
candidate 0 is still exactly equivalent to the operational Top-1. The frozen
route has 81 samples, seven directed identity edges, source SHA256
`fcc1c6b3655cd44690ae0223ad8ef76ff1c54d6d9a9d9c0bc2f3454534bd0e58`,
and graph SHA256
`a3a850dd70b170782edf8fdc09b76c1fc7490ea19a4f292389af9caa52772a76`.

For every one of the 486 points with a unique route-chord match, converting the
interpolated double station to the CARLA API's float32 input predicts the
receipt split exactly: all 405 XODR mismatch rows exceed the frozen
`1.0000017763568395e-9 m` station epsilon, and all 81 later continuity rows do
not. Roads 0 and 10 each have one lane section containing lane -2 and are
non-junction roads, so section/lane/junction ambiguity does not explain the
observed split. An independent, candidate-free census of all road lengths in
the same eight official XODRs gives a global float32 station half-ULP bound of
`3.0517578125e-05 m`. This identifies a precision-census/implementation defect
but does not yet select or apply a replacement tolerance.

The remaining route coverage evidence is separate: 127 points lie just before
the first sampled route chord, while 24 lie on the geometric connection between
consecutive samples whose identities form the frozen directed edge `(0,0,-2)`
to `(10,0,-2)`. The present same-identity chord representation contains neither
the predecessor-side route surface nor an identity-valid boundary
representation. Whether to add an outcome-free predecessor halo, materialize
exact OpenDRIVE boundary samples, or retain strict future-only exclusion has not
been scientifically selected. No current-candidate magnitude is used to derive
a threshold.

The source breakdown artifact/root is
`/root/autodl-tmp/camp_dp_v19_zero_support_source_only_breakdown_a27e292f_20260713T213103CST`
and `e2601162e8bbeb1c6ddc781e99246097dda95f4ff5ae7f30b4004d2d512efb4a`.
Independent review passed 13/13 checks at
`/root/autodl-tmp/camp_dp_v19_zero_support_source_only_breakdown_a27e292f_20260713T213118CST_independent_review`
with root
`d540bf6b195db9a33cf31c6b6769d52d1d82d01cda5a19135ac6934c805e5b34`.
No lifting/source/tolerance/eligibility field changed. Legal paired support is
still zero, candidate 0 remains source-incomplete, and performance,
closed-loop safety, broad CAMP-over-DP, promotion, deployment, and activation
claims remain unsupported.

current_v19_status=v19_zero_support_source_only_candidate_point_breakdown_independent_review_passed
current_v19_artifact_scope=zero_support_complete_candidate_x80_source_only_failure_breakdown_float32_station_diagnosis_and_route_coverage_ambiguity_no_contract_change
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_zero_support_source_only_breakdown_a27e292f_20260713T213118CST_independent_review
current_v19_artifact_root_sha256=d540bf6b195db9a33cf31c6b6769d52d1d82d01cda5a19135ac6934c805e5b34
next_work_target=v19_zero_support_scientific_contract_redesign_design_spec_static_review_and_tdd_plan_only

## Zero-Support Contract Redesign Static Review Passed

The source-only redesign spec and inline TDD plan were committed at
synchronized CAMP/GitHub/AutoDL
`17a2c5a9a4621e428c1146fc987035585f4a5a27`. Their paths and SHA256 values are:

- `docs/superpowers/specs/2026-07-13-v19-zero-support-source-contract-redesign.md`:
  `58ecc1a7e90efcc4c1c983c13792442b929a9a5e8453470f87d57003dce623d7`;
- `docs/superpowers/plans/2026-07-13-v19-zero-support-source-contract-redesign.md`:
  `0a29b7481a69e986547a3d9c2c83f1c783ab877819493177498f43730dd62486`.

Independent static review passed all 24 checks. It rehashed the sealed
640-point breakdown/review, fixed DP/candidate literals, official CARLA and
ASAM sources, the float32 formula, the eight-map bound, all three route-policy
alternatives, RED/GREEN steps, no-runtime guards, and the unchanged
implementation source.

The unique selected implementation fix is limited to the API precision defect.
The previous census passed only stations already quantized by CARLA, whereas
production passes double chord-interpolated stations through CARLA's `float s`
API. The preregistered map-only formula takes half the maximum float32 spacing
over every road length in the eight frozen XODRs, yielding
`3.0517578125e-05 m`, then adds the unchanged `1e-9 m` allowance. The only
authorized source change is a named frozen tolerance with station and
continuity values `3.0518578125e-05 m`; geometry remains
`1.5273609989704584 m` and z remains `1e-9 m`.

The review explicitly records `route_contract_selected=false` and
`new_source_probe_authorized_by_review=false`. Official map semantics do not
choose among retaining strict future-only exclusion, adding a predecessor plus
exact boundary representation, or redefining endpoint/transition matching.
Current-candidate coverage is not used to decide among them. No CARLA server,
DP worker, pipeline, candidate generation, outcome, metric, or holdout access
occurred.

The static-review artifact/root is
`/root/autodl-tmp/camp_dp_v19_zero_support_contract_redesign_static_review_17a2c5a9_20260713T213823CST`
and `5c2b6ba0c82c4d37c1474ea8c33597195513151d466631f8a9c87c6ff1855db6`.
Claim taxonomy and zero legal paired support remain unchanged.

current_v19_status=v19_zero_support_contract_redesign_spec_tdd_plan_static_review_passed
current_v19_artifact_scope=zero_support_contract_redesign_float32_station_precision_fix_only_route_contract_unselected_no_runtime
current_v19_artifact=/root/autodl-tmp/camp_dp_v19_zero_support_contract_redesign_static_review_17a2c5a9_20260713T213823CST
current_v19_artifact_root_sha256=5c2b6ba0c82c4d37c1474ea8c33597195513151d466631f8a9c87c6ff1855db6
next_work_target=v19_zero_support_float32_xodr_station_tolerance_tdd_implementation_and_static_review_only
