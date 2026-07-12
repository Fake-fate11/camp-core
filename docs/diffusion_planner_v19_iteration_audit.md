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
