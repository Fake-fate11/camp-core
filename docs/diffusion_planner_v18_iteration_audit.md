# DP-CAMP V18 nuPlan Iteration Audit

Last verified: 2026-07-10, Asia/Shanghai.

This is the append-only gate ledger for the v18 nuPlan mini to causal nuPlan
10k path. Historical v14-v17 conclusions remain in their original audits.

## Fixed Boundary

- Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`; its code, configuration,
  weights, and checkpoint are immutable.
- K is fixed at 8. CAMP may only score, rerank, and select the fixed candidate
  tensor; it may not generate, repair, rewrite, blend, or postprocess a
  trajectory.
- The score remains `score_k(w)=a_k^T w`; weights are a nonnegative simplex
  over approved atoms, and CVaR/L2/master remain convex.
- Decision-time inputs, canonical `dp_camp_v10_14d` atoms, split seeds, data
  isolation, fail-closed rules, evidence requirements, claim criteria, and
  stop conditions are those in the active Codex goal objective.
- Old nuScenes corpora and artifacts are historical only and may not be
  restored, revalidated, or reused for v18.

## Gate 0: V17 Supersession and V18 Bootstrap

Status: local preflight ready; checkpoint, push, and AutoDL fast-forward
verification remain pending.

- V17 EOF was read and closed only with
  `v17_nuscenes_path_superseded_by_user_decision_and_artifacts_deleted`; its
  missing-input blocker was not resumed.
- Local branch: `main`.
- Pre-transition local CAMP HEAD / GitHub `main` / AutoDL CAMP HEAD / AutoDL
  `origin/main`:
  `db3376866181fdcd97c926c6c1d6e28e516c2fcd`.
- Local and AutoDL CAMP tracked status: clean. Unrelated local untracked files
  were not modified.
- AutoDL Diffusion Planner HEAD / tracked status:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- AutoDL `/root/autodl-tmp` contains only `.autodl`, `camp_core`,
  `Diffusion-Planner`, `camp_dp_assets`, and `dp312_venv`, with approximately
  `42G` available. No v17/v18 generation, training, or evaluation job is
  active.
- nuPlan source inventory and acquisition were not executed by this docs-only
  bootstrap. No substitute or synthetic dataset was created.
- Candidate tensors, corpus rows, splits, weights, metrics, training time, and
  selector latency: not applicable at this gate.
- Local v18 document-contract self-check and `git diff --check`: passed.
- Python 3.12 `py_compile` for the causal materializer and atom gate: passed.
- Focused causal materializer/availability tests: `19 passed, 1 skipped`; the
  skip is the environment-gated fixed-DP contract test.

current_v18_status=v18_nuplan_mini_source_inventory_pending
current_v18_artifact_scope=v17_supersession_and_v18_nuplan_bootstrap
current_v18_artifact=docs/diffusion_planner_v18_iteration_audit.md
next_work_target=v18_nuplan_mini_source_inventory_and_acquisition_preflight_only

### Gate 0 Checkpoint and Cross-Surface Verification

Status: passed.

- Bootstrap checkpoint:
  `b43bae6eb559c6185e2702386c0aa7dd8167489b`.
- Local CAMP HEAD, GitHub `main`, AutoDL CAMP HEAD, and AutoDL `origin/main`
  equaled the checkpoint when verified; local and AutoDL tracked states were
  clean.
- AutoDL Diffusion Planner remained tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- AutoDL document SHA256:
  - current status:
    `1da4f219f4fb9bda5abd90a7878fac9bb3804ea42b4e3c2c5eb399e9fe374975`
  - v17 audit with supersession marker:
    `38a07e09c78182b6284a1a0641a4cae53f3286181b34d8f83e6704c85fc43977`
  - v18 audit bootstrap:
    `95992bcbdc916d63180e3dac71c0767ae8cf705d7629f2ecbea256de2eb97628`
- No v17/v18 generation, training, or evaluation job was active. No nuPlan
  source inventory, acquisition, candidate generation, training, evaluation,
  claim, promotion, deployment, or activation occurred in this gate.

current_v18_status=v18_nuplan_mini_source_inventory_pending
current_v18_artifact_scope=v17_supersession_and_v18_nuplan_bootstrap_verified
current_v18_artifact=docs/diffusion_planner_v18_iteration_audit.md
next_work_target=v18_nuplan_mini_source_inventory_and_acquisition_preflight_only

## Gate 1: nuPlan Mini Source Inventory and Acquisition Preflight

Status: source inventory passed; acquisition stopped before download at the
manual license-authorization boundary.

- Evidence artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_source_inventory_preflight_eff4f89a_20260710T142636CST`
- Artifact root SHA256:
  `1cdae5c6a7543f8575abca44d25b9a552dca88eb1add9757654add33a0df41c0`
- JSON / MD SHA256:
  `8f47fe1f735f6bd2f3f18a2d1e49467dbe627ee60cdaf56b9fdca9639741666d` /
  `c736fffcfd91193355df6051ab250ef6fa08c0d2e19a58ced208acdd826d7531`.
- `SHA256SUMS` and `ROOT_SHA256SUMS` verification: passed; all preflight
  checks passed and `run.exit=0`.
- CAMP HEAD / origin:
  `eff4f89a872e3e4cf897ecefc1c59a5fcc131afe`; tracked clean.
- Fixed DP HEAD / tracked status:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- Fixed DP native nuPlan references, loader, and config: `0 / none / none`.
  Its native dataset surface is a JSON list, or a `files` dict, of NPZ paths
  loaded by `DiffusionPlannerData`.
- Bounded source search under `/root/autodl-tmp` and `/autodl-pub/data`, to
  depth 5, found zero nuPlan-named source paths. Available data-disk space was
  `45045547008` bytes. No v17/v18 job was active.
- Official source inventory:
  - registry: `https://registry.opendata.aws/motional-nuplan/`
  - maps archive: `971557640` bytes, HTTP `200`
  - mini archive: `8550100030` bytes, HTTP `200`
  - compressed total: `9521657670` bytes
- The official website/setup path requires an account and agreement to the
  Motional Dataset Terms. The official AWS Open Data copy requires no AWS
  account, but anonymous access does not remove those terms. The terms apply to
  downloads from the website or elsewhere, allow eligible non-commercial use,
  and require a commercial license for commercial use.
- Non-commercial eligibility, user acceptance, and commercial-license
  authorization are all unconfirmed. No agent may accept that legal boundary
  on the user's behalf, so no archive was downloaded or extracted.
- Data records / split / K: `0 / none / 8` (contract only). Weights, metrics,
  training time, selector latency, and reranking overhead: not applicable.
- No adapter implementation, candidate generation, atom materialization,
  training, holdout access, evaluation, claim, promotion, deployment, or
  activation occurred.

current_v18_status=v18_nuplan_mini_source_inventory_passed_acquisition_blocked_pending_license_authorization
current_v18_artifact_scope=nuplan_mini_source_inventory_and_acquisition_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_source_inventory_preflight_eff4f89a_20260710T142636CST
current_v18_artifact_root_sha256=1cdae5c6a7543f8575abca44d25b9a552dca88eb1add9757654add33a0df41c0
next_work_target=user_confirmation_of_noncommercial_terms_acceptance_or_commercial_nuplan_license_before_acquisition

## Gate 2: Non-Commercial Dataset Authorization

Status: authorization recorded; acquisition execution is the only next gate.

The user confirmed all of the following:

- the project is limited to personal, academic, or other non-commercial
  research;
- the project has no present or future revenue purpose;
- the Motional Dataset Terms were read and accepted;
- the official Motional AWS anonymous source is authorized for nuPlan mini
  acquisition and use; and
- raw nuPlan data must not be redistributed.

This resolves the Gate 1 manual-license blocker without changing the fixed DP,
K=8, causal-input, atom, split, convexity, or claim boundaries. It authorizes
only the official maps and mini archive acquisition. No archive was downloaded
or extracted by this docs-only authorization gate, and no adapter, candidate,
atom, training, evaluation, claim, promotion, deployment, or activation work
occurred.

current_v18_status=v18_nuplan_mini_noncommercial_license_authorization_recorded
current_v18_artifact_scope=nuplan_mini_noncommercial_terms_acceptance_and_no_raw_redistribution_authorization
current_v18_artifact=docs/diffusion_planner_v18_iteration_audit.md
next_work_target=v18_nuplan_mini_official_aws_maps_and_mini_acquisition_execution_only

## Gate 3: Official AWS Acquisition Execution

Status: running; stop and monitor only. Do not launch a second acquisition.

- Authorization checkpoint CAMP HEAD / origin / AutoDL:
  `1fd912587dd416bac091eb76c976a38c64051903`.
- Fixed DP HEAD / tracked status:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- Execution artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_1fd91258_20260710T143617CST`
- AutoDL PID: `439876`.
- Started: `2026-07-10T14:36:22+08:00`.
- The single resumable command downloads the official maps archive first and
  the mini archive second, using `.part` files and an exclusive acquisition
  lock. It requires the audited sizes `971557640` and `8550100030` bytes,
  generates `ARCHIVE_SHA256SUMS`, and runs ZIP integrity checks before exit.
- First observation at approximately 30 seconds:
  - process: running
  - maps partial: `1867776` bytes
  - `run.exit`: pending
  - stderr tail: empty
  - data-disk available: approximately `42G`
- A later live process check confirmed the active `curl` inherited the
  `http_proxy` and `https_proxy` environment keys from `/etc/network_turbo`;
  proxy values were not printed or stored. The maps partial had grown to
  `11862016` bytes and the process remained active.
- Artifact/root SHA: pending until the job exits and the evidence package is
  finalized.
- No mini bytes, extraction, adapter implementation, candidate generation,
  atom materialization, split, training, evaluation, claim, promotion,
  deployment, activation, or raw-data redistribution occurred at this
  observation.

current_v18_status=v18_nuplan_mini_official_aws_acquisition_running
current_v18_artifact_scope=nuplan_mini_official_aws_maps_and_mini_archive_acquisition
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_1fd91258_20260710T143617CST
next_work_target=stop_while_v18_nuplan_mini_official_aws_acquisition_job_running_monitor_only

### Gate 3 Retry Remediation: Fresh Curl Per Attempt

Status: corrected acquisition running; stop and monitor only.

- Root cause: AutoDL curl `7.81.0` combined `--continue-at -` with
  `--retry 20 --retry-all-errors`. The mini invocation started without a
  partial, so its initial resume offset was zero. After two curl exit-18
  transfers, in-process retry restored the output toward that initial offset
  instead of preserving the latest partial length.
- Source capability was not the blocker. An ETag-pinned byte-range probe
  returned HTTP `206`, `Content-Range: bytes
  123456789-123456799/8550100030`, and mini ETag
  `"08abc074db9227e758cc41c6b1ee223c-1020"`.
- RED command-contract check against the old `COMMAND`: exit `1`, as expected,
  because `--continue-at -` and internal `--retry` coexisted.
- Old artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_1fd91258_20260710T143617CST`
- Old wrapper / terminated curl / recorded exit:
  `439876 / 440416 / 143`.
- Old failure class / finalized root SHA256:
  `curl_internal_retry_resets_resume_offset` /
  `9e4705e5e6ac00eb378d10e28ed8b5cf65033e6e0e284f88f14276a638bedb02`.
- The partial was `370872320` bytes before and after stopping. Its trailing
  64 KiB local SHA256 and corresponding remote Range SHA256 both equaled
  `bdbe865516fc5458294670b9f719317c9f4009b9b54abf8b8a7d51ab0c150f73`.
  The ETag and Range probe passed, so the partial was preserved. The approved
  fallback deletes only the literal mini `.part` if size, ETag, Range, curl
  exit 33/36, or monotonicity proves it cannot resume; no backup is created.
- Corrected artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_outer_retry_2d92202d_20260710T165604CST`
- Corrected wrapper PID / start:
  `443827 / 2026-07-10T16:56:07+08:00`.
- The corrected command passed `bash -n` and the GREEN contract check. It has
  no curl `--retry*` flag, uses at most 20 outer attempts, starts a fresh curl
  per attempt, pins `If-Range`, and retains the exact-size, SHA256, and ZIP
  integrity checks.
- Resume log: `bytes=370872320`; first active curl PID: `443843`.
- Same-inode 20-second sample:
  `374747136 -> 378183680` bytes (`+3436544`).
- Download inventory while running:
  `nuplan-maps-v1.0.zip=971557640` and exactly one
  `nuplan-v1.1_mini.zip.part`; total files / partial files: `2 / 1`.
- Maps / mini ETags:
  `"4581f21a3562c097041ab68f2d1177d9-116"` /
  `"08abc074db9227e758cc41c6b1ee223c-1020"`.
- Corrected launch JSON / MD / immutable launch-root SHA256:
  `665f17a60b3796ffb15c7c628b808ab9662bb8c28cdf6eec756b55fb8c6fdd39` /
  `b673b5c106cdb87d5d4d356b5771eea092e062eb6cb258ce57e8284d2adc5dbb` /
  `339af1f78a2bf91ec1d25817b6dea165fe3c923bfaa3bef43fb31aa0c46a8d3f`.
- Pre-launch CAMP HEAD / origin / tracked changes:
  `2d92202d1f0161762e6c6d3adb08c2d9a1207947` /
  `2d92202d1f0161762e6c6d3adb08c2d9a1207947` / `0`.
- Fixed DP HEAD / tracked changes:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / 0`.
- No extraction, adapter work, candidate generation, atom materialization,
  split, training, evaluation, claim, promotion, deployment, activation, raw
  data redistribution, duplicate acquisition, or additional partial occurred.

current_v18_status=v18_nuplan_mini_official_aws_acquisition_running
current_v18_artifact_scope=nuplan_mini_official_aws_acquisition_outer_retry_resume_remediation
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_outer_retry_2d92202d_20260710T165604CST
current_v18_old_failed_artifact_root_sha256=9e4705e5e6ac00eb378d10e28ed8b5cf65033e6e0e284f88f14276a638bedb02
current_v18_launch_root_sha256=339af1f78a2bf91ec1d25817b6dea165fe3c923bfaa3bef43fb31aa0c46a8d3f
next_work_target=stop_while_v18_nuplan_mini_official_aws_acquisition_job_running_monitor_only

### Gate 3 Retry Remediation Checkpoint Verification

Status: passed; corrected acquisition still running, so stop and monitor only.

- Remediation checkpoint local / GitHub / AutoDL CAMP HEAD and AutoDL origin:
  `1528681fc612920babfe39b8a1bbddaae63a9f24`.
- Local and AutoDL CAMP tracked states: clean. Unrelated local untracked files
  were not staged or modified.
- AutoDL fixed DP HEAD / tracked state:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- Local and AutoDL causal `py_compile`: passed.
- Local focused tests: `19 passed, 1 skipped in 1.40s`.
- AutoDL focused tests: `19 passed, 1 skipped in 0.81s`.
- Old failure artifact `SHA256SUMS` / root verification and corrected launch
  artifact `LAUNCH_SHA256SUMS` / launch-root verification: all passed.
- During AutoDL checkpoint verification, the same active job grew from
  `586768384` to `588849152` bytes (`+2080768`) without size regression.
- The active child command contains no `--retry*`; stderr remained empty.
- Download directory remained exactly two files with one partial:
  `nuplan-maps-v1.0.zip` and `nuplan-v1.1_mini.zip.part`.
- No duplicate task, backup partial, extra part file, extraction, adapter work,
  candidate generation, atom materialization, split, training, evaluation,
  claim, promotion, deployment, activation, or raw-data redistribution
  occurred.

current_v18_status=v18_nuplan_mini_official_aws_acquisition_running
current_v18_artifact_scope=nuplan_mini_official_aws_acquisition_outer_retry_resume_remediation_verified
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_outer_retry_2d92202d_20260710T165604CST
current_v18_old_failed_artifact_root_sha256=9e4705e5e6ac00eb378d10e28ed8b5cf65033e6e0e284f88f14276a638bedb02
current_v18_launch_root_sha256=339af1f78a2bf91ec1d25817b6dea165fe3c923bfaa3bef43fb31aa0c46a8d3f
next_work_target=stop_while_v18_nuplan_mini_official_aws_acquisition_job_running_monitor_only

### Gate 3 Acquisition Result Review

Status: passed; official archive extraction is the only next gate.

- Corrected acquisition completed at `2026-07-10T20:01:34+08:00` with
  `run.exit=0`.
- The first fresh curl attempt began at byte `370872320`, exited `18` after
  preserving `5964344032` bytes, and the outer loop's second fresh curl began
  at that exact offset. This is direct runtime evidence that the remediation
  accumulated progress across connection failure.
- Final maps / mini sizes:
  `971557640 / 8550100030` bytes.
- Final maps / mini SHA256:
  `d0310009fa9e8dd88014038336538aca678842c009fbf03fae76ed28f702ffc6` /
  `a3fe40afd81cc634884f8d0b7ea3604f2e617e365d5c258c61cfdd833c8d987b`.
- Independent `sha256sum -c` and `unzip -tq` review: passed for both archives.
- Download directory final files / partial files: `2 / 0`; no duplicate,
  backup, or orphan partial exists.
- Result JSON / MD SHA256:
  `68824c4cbbbee54420b279cb54a2ad6f0e81f9b5d5ffe7126b2e8c4441030448` /
  `4104065f4b70b9780ea3c6943d1e5e2044f7d7cc3a7cb1449c8b27d98329f473`.
- Final artifact root SHA256:
  `4d0a77dfab9f649df65e138fa41139afea01e2fc51144a4da897722a0a7c76c9`.
- CAMP HEAD / origin / tracked changes at result review:
  `88460d701eeda4788d2352c17c63d7292b5d6877` /
  `88460d701eeda4788d2352c17c63d7292b5d6877` / `0`.
- Fixed DP HEAD / tracked changes:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / 0`.
- No extraction, adapter implementation, candidate generation, atom
  materialization, split, training, evaluation, claim, promotion, deployment,
  activation, or raw-data redistribution occurred in this result review.

current_v18_status=v18_nuplan_mini_official_aws_acquisition_complete_verified
current_v18_artifact_scope=nuplan_mini_official_aws_acquisition_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_outer_retry_2d92202d_20260710T165604CST
current_v18_artifact_root_sha256=4d0a77dfab9f649df65e138fa41139afea01e2fc51144a4da897722a0a7c76c9
next_work_target=v18_nuplan_mini_official_archives_extraction_execution_only

## Gate 4: Official Archive Extraction Execution

Status: running; stop and monitor only. Do not launch a second extraction.

- Extraction artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_archives_extraction_29eee9c9_20260710T204004CST`
- AutoDL PID / start:
  `450283 / 2026-07-10T20:40:05+08:00`.
- Target dataset root: `/root/autodl-tmp/nuplan/dataset`; it did not exist at
  preflight, and the command holds an exclusive extraction lock.
- ZIP path-safety review: passed; no absolute path, `..`, or symlink entry.
- Both archive `LICENSE` entries are identical: size `25319`, SHA256
  `1a218286e733f6d6135fc5698d614cda2be94ea096f6eee280278458e570636a`.
  The second identical license is skipped instead of overwritten.
- Expected unique extracted bytes / available bytes before launch:
  `15777787771 / 35522355200`.
- Expected final files / map files / mini SQLite databases:
  `72 / 7 / 64`.
- The command re-verifies source archive SHA256 before extraction, validates
  all 64 SQLite headers and readable schemas after extraction, and creates a
  full extracted-file SHA256 manifest.
- First observation: PID alive, `run.exit` pending, and approximately
  `1182928415` bytes existed under the dataset root.
- Launch JSON / MD / immutable launch-root SHA256:
  `86f33e27ebaad5b8bfb15165dfbb304bb73486768a5a55298f23fd25c55c42eb` /
  `4511e4d400cfcfa49c8c9ca838fb7c64cb757f4f79696cb1b2d9c3ccd2b8f2f8` /
  `ab340899aab8f5714559328499e7e11926160291d2815501f4ace2bf05d0e42f`.
- Launch CAMP HEAD / origin / fixed DP HEAD:
  `29eee9c99f55bfb773b7166b03e456035ca621af` /
  `29eee9c99f55bfb773b7166b03e456035ca621af` /
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- No adapter implementation, candidate generation, atom materialization,
  split, training, evaluation, claim, promotion, deployment, activation, raw
  data redistribution, duplicate extraction, or extra partial occurred.

current_v18_status=v18_nuplan_mini_official_archives_extraction_running
current_v18_artifact_scope=nuplan_mini_official_archives_official_hierarchy_extraction
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_archives_extraction_29eee9c9_20260710T204004CST
current_v18_launch_root_sha256=ab340899aab8f5714559328499e7e11926160291d2815501f4ace2bf05d0e42f
next_work_target=stop_while_v18_nuplan_mini_official_archives_extraction_job_running_monitor_only

### Gate 4 Extraction Result Review

Status: passed; causal-adapter source-contract inventory/test preflight is the
only next gate.

- Extraction completed at `2026-07-10T20:43:14+08:00` with `run.exit=0` and
  empty stderr.
- Dataset root: `/root/autodl-tmp/nuplan/dataset`.
- Extracted files / unique bytes / map files / mini SQLite databases:
  `72 / 15777787771 / 7 / 64`.
- All 64 SQLite headers and schemas were readable; every database exposed
  exactly 12 tables.
- Extracted-file SHA256 verification: `72 / 72` passed.
- Dataset manifest root SHA256:
  `43d09389dafd53f8486e9305fca005dede2ae8ba5aa97d908953a7084c435c72`.
- Result JSON / MD SHA256:
  `1d24d652a774fc3df24984a90f5c5fd89b507de1985433805a7f30ca5279d4e2` /
  `8552c6d7fea739a7d7a128a0a4cb79e5ac3c3fdd2050fcdb6a108e0b63ccb768`.
- Final extraction artifact root SHA256:
  `25edf589f115bcda2a24937d5b64d8ea317b5ee61d75a0429b506e58a1806dbd`.
- Available data-disk bytes after extraction: `19744247808`.
- CAMP HEAD / origin / tracked changes at result review:
  `d8f29b37fc16c472c203c80d4b0680d429b5569b` /
  `d8f29b37fc16c472c203c80d4b0680d429b5569b` / `0`.
- Fixed DP HEAD / tracked changes:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / 0`.
- No adapter implementation, candidate generation, atom materialization,
  split, training, evaluation, claim, promotion, deployment, activation, or
  raw-data redistribution occurred in this result review.

current_v18_status=v18_nuplan_mini_official_archives_extraction_complete_verified
current_v18_artifact_scope=nuplan_mini_official_archives_extraction_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_archives_extraction_29eee9c9_20260710T204004CST
current_v18_artifact_root_sha256=25edf589f115bcda2a24937d5b64d8ea317b5ee61d75a0429b506e58a1806dbd
next_work_target=v18_nuplan_mini_causal_adapter_source_contract_inventory_and_test_preflight_only

## Gate 5: Causal-Adapter Source-Contract Inventory and Test Preflight

Status: passed; test-driven adapter implementation is the only next gate.

- Evidence artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_adapter_source_contract_preflight_397ea2c8_20260710T205550CST`
- Source dataset manifest root SHA256:
  `43d09389dafd53f8486e9305fca005dede2ae8ba5aa97d908953a7084c435c72`.
- All 64 mini databases share one schema fingerprint and expose real
  decision-time tables for scene mission goal/route, lidar ticks, ego pose,
  lidar boxes/tracks/categories, and traffic-light state.
- Scene contract totals:
  - total / route present / route mapped / strict connected:
    `1364 / 1338 / 1338 / 1090`
  - mission goal present and resolvable: `662 / 662`
  - full route speed / boundary / baseline: `1141 / 1338 / 1338`
  - fully eligible: `526` scenes across `48` logs
  - eligible by location: Las Vegas `488`, Pittsburgh `38`, Singapore `0`,
    Boston `0`
  - eligible scenario-tag rows / distinct decision ticks:
    `345490 / 154291`.
- Mission route lengths are `0..47`; eligible routes are `6..39`, and 266
  eligible scenes exceed the fixed 25 route slots. The adapter must anchor a
  connected at-most-25-roadblock mission-route window at the current roadblock;
  it must not truncate from the route start or construct a nearby-lane route.
- Map roadblock contracts with complete speed sources:
  Singapore `0/2001`, Boston `220/2413`, Las Vegas `1883/1883`, Pittsburgh
  `814/814`. Missing `speed_limit_mps` is ineligible; `min_speed`, current ego
  speed, statutory defaults, and `100 m/s` are forbidden fallbacks.
- Boundary and baseline geometry cover every mapped route roadblock. Mission
  goal comes from `scene.goal_ego_pose_token -> ego_pose`, never the route
  endpoint. Traffic state comes only from `traffic_light_status` for the exact
  current `lidar_pc_token`; the table contains `4513257` resolved red/green
  rows. Ego pose x/y, timestamps, velocity, acceleration, and orientation have
  zero missing values. Lidar dt is derived from linked timestamps near 50 ms,
  never hardcoded.
- Current environments have no nuPlan devkit, Shapely, Fiona, GeoPandas, GDAL,
  or OGR. The official devkit setup targets a Python 3.9/full dependency stack,
  while fixed DP runs Python 3.12. The minimum adapter dependency is therefore
  optional `Shapely>=2.0`; raw table and GeoPackage metadata access remains
  standard-library `sqlite3`.
- Fixed DP still has zero native nuPlan references. Its `DiffusionPlannerData`
  accepts an arbitrary JSON-listed NPZ dictionary, so the existing causal
  materializer remains the input boundary.
- Minimum implementation scope:
  `camp_core/pyproject.toml`, new
  `camp_core/camp_core/integrations/nuplan_causal_adapter.py`, the existing
  causal materializer, and one new v18 adapter test file. No new runner or
  abstraction layer is authorized.
- Required RED/GREEN tests: future sentinel, future perturbation invariance,
  mission-route connectivity and current-roadblock 25-slot anchoring,
  `speed_limit_mps` projection/missing-speed fail closed, exact traffic-light
  tick timestamp, left/right boundary semantics, dt from timestamps, global
  SE(2) invariance, and mission goal distinct from route endpoint.
- Candidate-neighbor predictions and candidate-0 DP Top-1 semantic remain
  unavailable/fail-closed until the same fixed-DP execution exports and verifies
  them. No 14D availability claim is made at this gate.
- Result JSON / MD / artifact-root SHA256:
  `f86dda4b89925c904e35e41f4161c197312a67c7fa798b44471525b264c99327` /
  `8e8bca63edb3357cfbb43db45e37d1459dc40c577e72032bbf88a5bcebd64245` /
  `ddb955794808c28610fe55830eec18d500e693eb0751714879bee46819fcc465`.
- CAMP HEAD / origin / fixed DP HEAD:
  `397ea2c898205546d8fd022c5360728c23d91db1` /
  `397ea2c898205546d8fd022c5360728c23d91db1` /
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- No adapter code, dependency installation, candidate generation, atom
  materialization, split, training, evaluation, claim, promotion, deployment,
  activation, or raw-data redistribution occurred.

current_v18_status=v18_nuplan_mini_causal_adapter_source_contract_preflight_complete
current_v18_artifact_scope=nuplan_mini_causal_adapter_source_contract_inventory_and_test_plan
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_adapter_source_contract_preflight_397ea2c8_20260710T205550CST
current_v18_artifact_root_sha256=ddb955794808c28610fe55830eec18d500e693eb0751714879bee46819fcc465
next_work_target=v18_nuplan_mini_causal_adapter_test_driven_implementation_only

## Gate 6: Causal Adapter Test-Driven Implementation

Status: passed; removal of one unused dependency target is required before the
mini split/candidate-generation preflight.

- Evidence artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_adapter_implementation_19d007ff_20260710T213816CST`.
- Final CAMP / GitHub main / AutoDL CAMP:
  `19d007ffb81f4c3865cc28117096732e7acbb1bd`.
- Fixed DP HEAD / expected HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / 7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- AutoDL py_compile, v17 causal materializer tests, v18 adapter tests, real mini
  test, and fixed-DP loader/normalizer contract all passed: `22 passed`.
- Implemented only the authorized CAMP-side files:
  `camp_core/pyproject.toml`,
  `camp_core/camp_core/integrations/nuplan_causal_adapter.py`,
  `camp_core/camp_core/integrations/diffusion_planner_causal_materializer.py`,
  and
  `camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py`.
- Required causal tests now cover future sentinels and future perturbation
  invariance, current-roadblock mission-route anchoring/connectivity, complete
  `speed_limit_mps`, exact lidar-tick traffic state, true left/right boundary
  semantics, timestamp-derived dt, UTM-scale global SE(2) invariance, and an
  independent mission goal rather than a route-endpoint surrogate.
- The real checked decision was
  `165060762e765a5a:8b9c1329bd1855c9` at timestamp
  `1620857893850826`, source dt `0.050009s`, current roadblock `66976`, 18
  selected connected route slots, 18/18 real route speed limits, exact-tick red
  traffic state, and 32 nonzero neighbor slots.
- Real materialization produced the exact 16-key fixed-DP input schema with no
  future key and all finite values. The derived NPZ SHA256 is
  `85e13ed3b56604938f2a20b322372a7a74808675c336617d6b740c3c3528da69`;
  one decision snapshot plus materialization took `0.415355s` wall time in the
  evidence run. This is adapter validation, not a K=8 candidate-generation or
  performance claim.
- The preflight's optional Shapely-only dependency assumption was falsified by
  the real map: GeoPackage geometry is EPSG:4326 and the `meta` layer declares
  projected CRS EPSG:32611 for this sample. The minimal dependency contract is
  therefore optional `Shapely>=2.0` plus `pyproj>=3.6`; full GeoPandas, Fiona,
  GDAL, OGR, pyogrio, and the nuPlan devkit remain unnecessary.
- The first isolated `pip --target` attempt created
  `/root/autodl-tmp/camp_v18_site` with an unwanted NumPy 2.5.1. It was never
  used or added to `PYTHONPATH`; all passing tests used the clean isolated
  `/root/autodl-tmp/camp_v18_shapely` containing only Shapely 2.1.2 and pyproj
  3.7.2. The unused directory remains pending explicit recursive deletion
  authorization under the repository deletion-safety rule.
- Two transient test overlays, one Git bundle, and the transient artifact
  runner were each removed by exact name. Existing unrelated untracked files
  were preserved. Fixed DP code, configuration, weights, checkpoints, and
  candidate tensors were not modified.
- Result JSON / MD / artifact-root SHA256:
  `a2d83098b8c23556fbc633bc69d9159d4acf3bc2eee16adadf9f8e6bd0cfdd3c` /
  `a639ae3cec2affaa3721c6982998b678de44934b88ec325e4cc0fc71402c375e` /
  `8dda1bab94afccfbd154c339f2fe16b00c6558dd230870e09e96989c957844ad`.
- `SHA256SUMS` and `ROOT_SHA256SUMS` both reverified with all entries passing.
- No fixed-DP candidate generation, candidate corpus, split, atom
  materialization, training, calibration, holdout access, evaluation, claim,
  promotion, deployment, activation, or raw-data redistribution occurred.

current_v18_status=v18_nuplan_mini_causal_adapter_implementation_passed_cleanup_pending
current_v18_artifact_scope=nuplan_mini_causal_adapter_test_driven_implementation_and_real_decision_materialization
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_adapter_implementation_19d007ff_20260710T213816CST
current_v18_artifact_root_sha256=8dda1bab94afccfbd154c339f2fe16b00c6558dd230870e09e96989c957844ad
next_work_target=v18_nuplan_mini_causal_adapter_unused_dependency_target_cleanup_and_result_review_only

## Gate 7: Unused Dependency Target Cleanup Result Review

Status: passed; mini split and fixed-DP K=8 candidate-generation preflight is
the only next gate.

- Evidence artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_adapter_cleanup_20260710T214851CST`.
- The user explicitly authorized deletion of
  `/root/autodl-tmp/camp_v18_site` while preserving
  `/root/autodl-tmp/camp_v18_shapely`.
- Before deletion, the target was reverified as a real direct child of
  `/root/autodl-tmp`, not a symlink, with exactly the seven expected NumPy
  2.5.1 / Shapely 2.1.2 pip-target entries. One literal-path recursive delete
  removed `81275412` bytes; the target is now absent.
- The preserved dependency target imports exactly Shapely `2.1.2` and pyproj
  `3.7.2`. Without its explicit `PYTHONPATH`, the fixed DP Python environment
  still resolves neither package, proving that the fixed DP venv was not
  modified.
- AutoDL reran the v17 causal materializer and v18 adapter suite after cleanup:
  `22 passed in 2.24s`. CAMP tracked files and fixed DP were clean at
  `a58e94551d489dc5d4576a9a2c0f1a03a3973f9d` and
  `7a1d33da277a1992ec474b5383a0c963c72e04e4` respectively.
- The nuPlan tree contains zero `.part` and `.partial` files. The transient
  cleanup runner was removed by exact name; unrelated untracked files and all
  referenced evidence artifacts were preserved.
- Result JSON / MD / artifact-root SHA256:
  `df06983c0fb763b618dbdd312e916de003300caa1b67bc603ff3a7e6af8551c6` /
  `3c1b3f1ce6d40351981f4f1e3781db3a253fa48c0d6e9836afc2a47ba712a022` /
  `06e900fc79ce3872673670eeb289b57bf237725022c839d102e90a32d87042b9`.
- `SHA256SUMS` and `ROOT_SHA256SUMS` both reverified with every entry passing;
  stderr is empty and `run.exit=0`.
- No candidate generation, candidate corpus, split, atom materialization,
  training, calibration, holdout access, evaluation, claim, promotion,
  deployment, activation, or raw-data redistribution occurred.

current_v18_status=v18_nuplan_mini_causal_adapter_implementation_complete_verified
current_v18_artifact_scope=nuplan_mini_causal_adapter_unused_dependency_target_cleanup_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_adapter_cleanup_20260710T214851CST
current_v18_artifact_root_sha256=06e900fc79ce3872673670eeb289b57bf237725022c839d102e90a32d87042b9
next_work_target=v18_nuplan_mini_smoke_split_and_fixed_dp_candidate_generation_preflight_only

## Gate 8: Mini Split and Fixed-DP Candidate-Generation Preflight

Status: passed after failure review; causal fixed-DP export-path
test-driven implementation is the only next gate.

- Source preflight artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_split_candidate_preflight_20260710T220921CST`
  / `43ca8805bfe47b833b37ca8e50186efb039f3a488bbb8a2d11253625cd8533f0`.
- Failure-review artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_split_candidate_preflight_failure_review_20260710T221642CST`
  / `2b116b902c59232238301298470d9954a0d7a28c44b4ea8fd57f1726ba57d55e`.
- The source inventory covered every one of the `64` official mini SQLite
  logs and all `1364` nuPlan scene tokens. Eligibility was predeclared as one
  deterministic official scenario-tag anchor nearest the scene midpoint with
  at least `3s` history, `8s` future-label coverage, a real mission goal and
  mapped route, and a passing causal adapter materialization. Missing or
  invalid real sources remained fail closed.
- Eligible corpus: `46` logs and `367` scenes. Whole-log assignment with
  split seed `3407` produced train/calibration/holdout scene counts
  `226 / 68 / 73` and log counts `25 / 9 / 12`; log overlap and scene overlap
  are both exactly zero. Manifest SHA256:
  `44b4082ce707428bf24bc9cd00bf19ddbb58f4867dac4e031969b02b967d74d0`.
- The source artifact's sole failed check was
  `every_source_map_has_eligible_scene`. Failure review classified this as
  `preflight_policy_overconstraint`: the objective requires all eligible
  mini logs/scenarios and log/scene zero overlap, but does not require each
  downloaded map to contribute an eligible scene. Singapore and Boston
  therefore remain excluded rather than receiving invented mission goals,
  routes, speed limits, boundaries, or other fallback inputs.
- A diagnostic sampled ten midpoint traffic-state failures and found four
  alternate passing tag ticks within the first 50 candidates. It did not
  change the predeclared selection rule or manifest after results were known.
- The fixed checkpoint SHA256 is
  `4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75`.
  Reconstructing `args.json` from fixed-DP training defaults plus the tracked
  normalization file loaded all `14545305` parameters with zero missing and
  zero unexpected keys.
- The existing v16 exporter can provide its fixed-model loader and native
  sampling helper, but its NPZ validation/loader requires expert-future
  fields. Fixed-DP inference only reads the causal schema, so reusing that
  v16 input boundary would violate the v18 future-leakage rule. The next gate
  is one thin CAMP-side causal export path; DP remains untouched at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4` and K remains `8`.
- Failure-review result JSON / MD SHA256:
  `b6753f6326c6d54953a1adbc58300f8565990a7dbdf20cac09a73be5a0714a01` /
  `6ac0d70109b18451df21852ffb4445d529654703fcd83c011ca4b02746a1fca8`.
  Both source and review `SHA256SUMS` chains reverified; review stderr is
  empty and `run.exit=0`.
- No fixed-DP inference, candidate generation, candidate corpus, atom
  materialization, training, calibration, holdout access, evaluation, claim,
  promotion, deployment, activation, DP modification, or raw-data
  redistribution occurred.

current_v18_status=v18_nuplan_mini_smoke_split_and_candidate_generation_preflight_failure_review_passed
current_v18_artifact_scope=nuplan_mini_smoke_split_candidate_generation_preflight_failure_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_split_candidate_preflight_failure_review_20260710T221642CST
current_v18_artifact_root_sha256=2b116b902c59232238301298470d9954a0d7a28c44b4ea8fd57f1726ba57d55e
next_work_target=v18_nuplan_mini_smoke_causal_fixed_dp_export_path_test_driven_implementation_only

## Gate 9: Causal Fixed-DP Export Path Implementation

Status: passed after evidence-check failure review; one-record fixed-DP
candidate generation is the only next gate.

- CAMP implementation commit:
  `4aa3ef98de2e00e278de5aaaf4d831abfd5ddb6d`; local, GitHub, and AutoDL were
  synchronized before AutoDL verification. Fixed DP remained tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Implementation / test:
  `scripts/integrations/run_diffusion_planner_dp_camp_v18.py` /
  `camp_core/tests/test_diffusion_planner_v18_orchestrator.py`.
- TDD RED produced three expected failures because the v18 orchestrator was
  absent. GREEN passed all three new tests. Local combined verification passed
  `23` with two environment-only skips; AutoDL set the real fixed-DP and
  nuPlan roots and passed all `25` tests plus py_compile.
- The orchestrator validates the exact causal schema before padding only
  `neighbor_agents_past` from 32 to the fixed model's native width of 320.
  It contains no expert ego/neighbor future field. It reuses the existing
  fixed-model load context and native sampling helper rather than modifying DP
  or duplicating model code.
- The frozen-manifest dry-run used SHA256
  `44b4082ce707428bf24bc9cd00bf19ddbb58f4867dac4e031969b02b967d74d0`,
  selected one record, verified K=8 and the fixed DP HEAD, reported
  `candidate_generation_executed=false`, and created no output root.
- Implementation artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_fixed_dp_export_path_implementation_4aa3ef98_20260710T222621CST`
  / `fb98a9bcc9636ea22085fe1bf3fbbf0023c0ac9939a2e401c4b652d00bc1c83a`.
  Its sole failed check, `future_schema_not_used`, matched Python's standard
  `from __future__ import annotations` line rather than a data field.
- Failure-review artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_fixed_dp_export_path_implementation_failure_review_4aa3ef98_20260710T222705CST`
  / `86b6d3b30887e9e0b15e9b2f31d9875f59d74aa99ba8645bd54c9a6810ab0037`.
  It verified exact forbidden field names, passed every check, left the code
  unchanged, and recorded result JSON / MD SHA256
  `5e4c9a12537c71297cabf294fc0f037860ea937dff6084a70dfe81acc5e3c200` /
  `ec7e8217042b9e37ab49b5dbab0718ed4a2cc66047a657d48c95f3579c4007e8`.
- No fixed-DP inference, candidate generation, candidate corpus, atom
  materialization, training, calibration, holdout access, evaluation, claim,
  promotion, deployment, activation, DP modification, or raw-data
  redistribution occurred.

current_v18_status=v18_nuplan_mini_smoke_causal_fixed_dp_export_path_implementation_failure_review_passed
current_v18_artifact_scope=nuplan_mini_smoke_causal_fixed_dp_export_path_implementation_failure_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_fixed_dp_export_path_implementation_failure_review_4aa3ef98_20260710T222705CST
current_v18_artifact_root_sha256=86b6d3b30887e9e0b15e9b2f31d9875f59d74aa99ba8645bd54c9a6810ab0037
next_work_target=v18_nuplan_mini_smoke_fixed_dp_candidate_generation_single_record_execution_only

## Gate 10: Fixed-DP Candidate Single-Record Execution and Result Review

Status: passed; full frozen-manifest candidate generation is the only next
gate.

- Execution artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_fixed_dp_candidate_single_record_execution_34c6300a_20260710T223059CST`
  / `b0479d0d54604d428c14c883433b3ff7afc4daf02c0dd4584d79df56589b2d32`.
- CAMP local/GitHub/AutoDL HEAD was
  `34c6300a533f21cf01a9b52e203eca8f3ec02fc6`; fixed DP stayed tracked-clean
  at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- The execution used the frozen manifest SHA256
  `44b4082ce707428bf24bc9cd00bf19ddbb58f4867dac4e031969b02b967d74d0`
  with `--max_records 1 --execute`. The rematerialized causal input SHA256
  `f6e92d3752b1548af53a316adc723cef94ef36760544a7ce2dd48d1d7e75b2b4`
  exactly matched the manifest record.
- Fixed DP emitted shape `[8, 80, 4]`, K=8, eight unique trajectories, and
  DP Top-1 index 0. Candidate tensor SHA256:
  `38b2a5c54978f33bf8e778f7c472bace94ad7c6bbf3f7ddd4375b3e9bbc81b37`;
  saved NPZ SHA256:
  `3bae7a4bdcb01e37ace1a4f56b22a03f0d87a87ce7290325f7962112f4407f8c`.
  Reloaded tensor hash matched the in-memory record, so CAMP did not mutate
  the candidate tensor.
- Wall-clock / per-record time: `5.854982s / 5.854982s`. Execution result
  JSON / MD SHA256:
  `97301eea8b28057bcf2114642c60ba1d9be7d086ebfe9011623fd0bf12cc05fe` /
  `d4434b8dfc493156b9f43e1539034035cd1a0cdd178f1b3f1aad48076e97d0e7`.
- The first result review's active-job filter self-matched the inline reviewer
  command text and failed only `no_active_candidate_job`; it did not rerun or
  alter the candidate. A file-backed refresh after that process exited passed
  with zero active jobs.
- Passing result-review refresh artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_fixed_dp_candidate_single_record_result_review_refresh_34c6300a_20260710T223304CST`
  / `c3f7572fa8cbc4ae4a3f57806d19d78b221e5feb42b07e2eef64aac7c5e906f5`.
  Result JSON / MD SHA256:
  `404892e166cf30e91c1b801c3a60ccc089884136b12a44d27733524e166c6258` /
  `7266210972d632b77b820ab40eb8cefd0904ad2186c21cc76ba50077495cf5a0`.
- Full-run plan: 367 frozen records, measured projection `2148.778394s`
  (`35.812973` minutes), estimated candidate NPZ bytes `4252796`, and
  available bytes `20090437632`. The full output root
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_candidates_44b4082ce707`
  was absent.
- This gate generated exactly one candidate tensor. No atom materialization,
  training, calibration, holdout-label access, evaluation, claim, promotion,
  deployment, activation, DP modification, or raw-data redistribution
  occurred.

current_v18_status=v18_nuplan_mini_smoke_fixed_dp_candidate_generation_single_record_result_review_passed
current_v18_artifact_scope=nuplan_mini_smoke_fixed_dp_candidate_generation_single_record_result_review_refresh
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_fixed_dp_candidate_single_record_result_review_refresh_34c6300a_20260710T223304CST
current_v18_artifact_root_sha256=c3f7572fa8cbc4ae4a3f57806d19d78b221e5feb42b07e2eef64aac7c5e906f5
next_work_target=v18_nuplan_mini_smoke_fixed_dp_candidate_generation_full_execution_only

## Gate 11: Full Fixed-DP Candidate Generation Execution

Status: passed; independent semantic result review is the only next gate.

- Execution artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_fixed_dp_candidate_generation_full_execution_0e2a2ddb_20260710T223739CST`
  / `9f08ef177c657504d3db3138e788441dcf6439da37df1e797c63bca472578101`.
- Candidate output root / manifest-root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_candidates_44b4082ce707`
  / `7a53d2ac348d0b8ddd49e11434131dce26619873a038d5709fa3c8d931441f73`.
- CAMP local/GitHub/AutoDL was
  `0e2a2ddb1e75acd2b07f5fd8c4aec19c0ff09911`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- The initial SSH launch-control channel timed out after starting the
  background wrapper. A read-only check found exactly one live exporter PID
  (`460586`) and an already growing output, so no duplicate was started.
  Monitoring observed `67`, `136`, `206`, `285`, then `367` records; the sole
  process exited and wrote `run.exit=0`.
- The frozen manifest SHA256 was
  `44b4082ce707428bf24bc9cd00bf19ddbb58f4867dac4e031969b02b967d74d0`.
  Output counts are exactly `367` JSONL records and `367` NPZ files.
- Wall-clock / per-record time: `229.258946s / 0.624684s`. Execution result
  JSON / MD SHA256:
  `432530b1b536b308cdf500358cce299da77904c6ce243f0918ace794f30b89de` /
  `bfa6c3de7afc182da20453e05d2f535bb16fabdae9034fcb028d2f9e05ecab81`.
  Candidate summary / records JSONL SHA256:
  `43213ac70871a7aba5265805c2a98ba194b999062f675b472060013df8bd26ea` /
  `301e2035fa5b88e1528724feb6a1e5b7653d980f35352858fa9259121225ae7b`.
- Finalization reverified CAMP/DP HEADs and tracked-clean state, zero active
  candidate jobs, empty stderr, the execution artifact SHA chain, and the
  candidate-output root manifest. It intentionally did not open every NPZ for
  semantic validation; that is the next independent gate.
- Candidate generation is complete for the mini manifest. No atom
  materialization, training, calibration, holdout-label access, evaluation,
  claim, promotion, deployment, activation, DP modification, or raw-data
  redistribution occurred.

current_v18_status=v18_nuplan_mini_smoke_fixed_dp_candidate_generation_full_execution_passed
current_v18_artifact_scope=nuplan_mini_smoke_fixed_dp_candidate_generation_full_execution
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_fixed_dp_candidate_generation_full_execution_0e2a2ddb_20260710T223739CST
current_v18_artifact_root_sha256=9f08ef177c657504d3db3138e788441dcf6439da37df1e797c63bca472578101
next_work_target=v18_nuplan_mini_smoke_fixed_dp_candidate_generation_full_result_review_only

## Gate 12: Full Fixed-DP Candidate Generation Result Review

Status: passed; causal atom and expert-label materialization preflight is the
only next gate.

- Review artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_fixed_dp_candidate_generation_full_result_review_b7a69c6f_20260710T224507CST`
  / `e78707569b7559662d64621140926ee7119519726471acc661a19a57adf7cf81`.
- Review CAMP HEAD was
  `b7a69c6f0b805a9d0d7a46ecc040634e11f07000`; generation CAMP HEAD was
  `0e2a2ddb1e75acd2b07f5fd8c4aec19c0ff09911`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- The independent reviewer invoked the model zero times. It verified the
  execution artifact and candidate-output SHA chains, then opened every one
  of the `367` NPZ files with pickle disabled and matched them one-to-one
  against the frozen manifest and `records.jsonl`.
- Semantic failures: `0`. Shape / dtype / K / DP Top-1 values were exactly
  `[8, 80, 4] / float32 / 8 / 0` for every record. Every value was finite,
  every causal input SHA matched the frozen manifest, and every tensor/file
  SHA matched its generation record.
- Unique candidates per record min/max: `8 / 8`. Unique candidate-tensor
  hashes / unique NPZ hashes across the corpus: `367 / 367`. The first
  full-run tensor hash matched the independently generated single-record
  smoke, proving deterministic replay from seed `3407` and manifest order.
- Train/calibration/holdout scene counts remained `226 / 68 / 73`; log counts
  remained `25 / 9 / 12`; log overlap and scene overlap remained exactly zero.
- Result-review JSON / MD SHA256:
  `bb68e46849c22f82d6c7e29fd38c0c62c5537ca4f86a696e13bb77f33517beff` /
  `a0a85231010e0558d37c030be4d9f884ef637199babfc608868877581ecd7814`.
  `SHA256SUMS` and `ROOT_SHA256SUMS` reverified, stderr is empty, and
  `run.exit=0`.
- Candidate generation is now semantically verified for the mini corpus. No
  atom materialization, training, calibration, holdout-label access,
  evaluation, claim, promotion, deployment, activation, DP modification, or
  raw-data redistribution occurred.

current_v18_status=v18_nuplan_mini_smoke_fixed_dp_candidate_generation_full_result_review_passed
current_v18_artifact_scope=nuplan_mini_smoke_fixed_dp_candidate_generation_full_semantic_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_fixed_dp_candidate_generation_full_result_review_b7a69c6f_20260710T224507CST
current_v18_artifact_root_sha256=e78707569b7559662d64621140926ee7119519726471acc661a19a57adf7cf81
next_work_target=v18_nuplan_mini_causal_atom_and_expert_label_materialization_preflight_only

## Gate 13: Causal Atom and Expert-Label Materialization Preflight

Status: preflight passed; canonical 14D materialization remains fail-closed
pending causal-source remediation.

- Preflight artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_atom_expert_label_preflight_20260710T230529CST`
  / `6a6d49474d264da43169ad0bb0328891ff7797a9a0c49a3682502f3ad2f90c85`.
- CAMP local/GitHub/AutoDL was tracked-clean at
  `a7bd279199ac24685e54ff912457240ebcba4a9d`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
  The preflight invoked the model zero times and did not generate candidates,
  materialize atoms or labels, train, calibrate, or read holdout label values.
- The frozen 367-record K=8 candidate corpus remains valid and immutable as
  its original candidate-generation evidence. It is not eligible for final
  14D materialization: none of its NPZ files contains same-call neighbor
  predictions or a frozen feasibility mask, and repairing the causal static
  input changes the input hashes, so candidates must be regenerated under a
  new root rather than overwritten.
- Real route speed limits and lane boundaries are complete for `367 / 367`
  records and for every projected candidate horizon. Route speed limits span
  `2.2351362705230713` to `15.645954132080078 m/s`; the shortest encoded route
  has `80` real points. Candidate kinematics, DP Top-1 index-0 semantics, and
  the planned lateral / DP-prior inputs are also available.
- Static context is currently invalid: `362 / 367` records contain real
  current non-dynamic boxes, but the adapter emits zero `static_objects` for
  `367 / 367`. Aggregate current counts are `537` barriers, `61` construction
  zone signs, `2185` traffic cones, and `19287` generic objects. Fixed-DP git
  history verifies the exact ten-field schema and one-hot order
  `czone_sign / barrier / traffic_cone / generic_object`; the nearest five
  real objects must be materialized on the CAMP side.
- The fixed config has `predicted_neighbor_num=320`, and the unmodified DP
  call already returns full `[B,321,80,4]` predictions. CAMP can therefore
  export candidate-specific `[8,32,80,4]` predictions for the causal 32-slot
  input plus a 32-slot real-neighbor mask from those same calls without
  modifying DP. Current records contain `3` to `32` real neighbor slots.
- Traffic state remains fail-closed where unresolved. `352` records contain
  at least one `WHITE/unknown` controlled route segment; under the current
  immutable candidates, `13` records / `93` candidates actually reach one
  using the fixed-DP red-light geometry predicate. This reachability must be
  recomputed after candidate regeneration, and affected records must be
  excluded or failed closed rather than treating unknown as green/no-red.
- Expert-label timestamps were inspected only for all `294` train plus
  calibration records. Every record has a sample at or after 8 seconds
  (`8.000001s` to `8.050019s`), the largest timestamp gap through the bracket
  is `0.057246s`, and a train-only pose bracket is finite. Labels may therefore
  interpolate to the 0.1-second grid without extrapolation. Holdout label
  values remain sealed.
- Current all-record canonical availability blocks `clearance` (same-call
  neighbor prediction and real static context absent), `progress_shortfall`
  (feasibility mask absent), and both red-light atoms (reachable unknown phase
  on a subset). No zero-filled atom, future input, or extrapolated label was
  accepted.

current_v18_status=v18_nuplan_mini_causal_atom_and_expert_label_materialization_preflight_complete_source_remediation_required
current_v18_artifact_scope=nuplan_mini_causal_atom_and_expert_label_materialization_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_atom_expert_label_preflight_20260710T230529CST
current_v18_artifact_root_sha256=6a6d49474d264da43169ad0bb0328891ff7797a9a0c49a3682502f3ad2f90c85
next_work_target=v18_nuplan_mini_causal_atom_source_remediation_test_driven_implementation_only

## Gate 14: Causal-Source Remediation Test-Driven Implementation

Status: passed; refreshed causal manifest plus single-record source smoke
preflight is the only next gate.

- Implementation artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_atom_source_remediation_implementation_20260710T235400CST`
  / `7016757c79febfde27918a6246703108060ab229755ceef1b164d7c4392c787f`.
- CAMP local/GitHub/AutoDL was
  `af46fd7060fc8b1b2b0d65c36d797cecb14c264f`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
  `/root/autodl-tmp/camp_v18_shapely` remained present.
- Test-driven changes materialize the nearest five real decision-tick
  non-dynamic objects in the fixed ten-field schema; preserve paired ego and
  first-32 neighbor predictions from each of eight fixed-DP calls; freeze the
  32-slot real-neighbor mask; and fail closed only for candidates that reach a
  `WHITE/unknown` controlled route segment.
- The exporter now supports an atomic, no-overwrite v2 causal-manifest
  refresh. Candidate execution accepts only that v2 schema and records the
  same-call neighbor tensor, source-availability masks, hashes, and canonical
  eligibility. Physical feasibility remains explicitly unmaterialized.
- Local verification passed `34` tests with `2` real-data skips. AutoDL
  verification passed `35` tests with `1` skip against the installed nuPlan
  mini source. The artifact has empty stderr, `run.exit=0`, and a verified
  `SHA256SUMS` chain.
- This gate invoked the real model zero times and did not refresh the manifest,
  generate candidates, materialize feasibility/atoms/labels, train, calibrate,
  access holdout label values, evaluate, or make a claim. The old candidate
  root `/root/autodl-tmp/camp_dp_v18_nuplan_mini_smoke_candidates_44b4082ce707`
  remains immutable.

current_v18_status=v18_nuplan_mini_causal_atom_source_remediation_implementation_passed
current_v18_artifact_scope=nuplan_mini_causal_atom_source_remediation_test_driven_implementation
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_causal_atom_source_remediation_implementation_20260710T235400CST
current_v18_artifact_root_sha256=7016757c79febfde27918a6246703108060ab229755ceef1b164d7c4392c787f
next_work_target=v18_nuplan_mini_refreshed_causal_manifest_and_single_record_source_smoke_preflight_only

## Gate 15: Refreshed Causal Manifest and Single-Record Source-Smoke Preflight

Status: passed after an environment-only failed attempt; single-record source
smoke execution is the only next gate.

- The first artifact / root SHA256 was
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_preflight_20260711T000418CST`
  / `e7a9ce79bb143f6a805f9d7a5b0a699aa62d01853cf8a1eadc719b9367a34a28`.
  Its target tests passed `16 / 16`, but the main artifact process lacked the
  preserved Shapely target in `PYTHONPATH` and failed before manifest creation
  with `ModuleNotFoundError: shapely`. No refresh or model call occurred in
  that attempt; its logs and SHA chain remain immutable.
- The passing retry artifact / root SHA256 is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_preflight_retry_20260711T000659CST`
  / `7a98d8a82bb4e65e774a7145a192098e13ce4180eb9320d20c770613f4c2c3e4`.
  It reused `/root/autodl-tmp/camp_v18_shapely`, passed all `16` target tests,
  has empty stderr and `run.exit=0`, and reverified its complete SHA chain.
- The new immutable v2 manifest is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_preflight_retry_20260711T000659CST/refreshed_scenario_manifest_v2.jsonl`
  with SHA256
  `bcf19b29b9c3654f41502d494a441858142d2d9c3b77bd686b5a764c1107d7a2`.
  All `367` identities and their order match parent manifest SHA256
  `44b4082ce707428bf24bc9cd00bf19ddbb58f4867dac4e031969b02b967d74d0`.
- Split scene counts remain train/calibration/holdout `226 / 68 / 73`; split
  log counts remain `25 / 9 / 12`, with zero log overlap and `367` unique
  scene tokens. The v2 extension is exact and records the parent SHA, source
  schema, static-object count, neighbor-valid count, and refreshed causal
  input SHA.
- `362 / 367` causal-input hashes changed, exactly matching the `362` records
  with nonzero real static objects. Static counts span `0..5`; real neighbor
  counts span `3..32`. Refresh wall-clock was `72.115406s`; complete gate
  wall-clock was `75.152347s`.
- The predeclared first manifest record is calibration scene
  `07ef2e232c8450f9`, decision `53710c1319405da6`. Re-materialization matched
  causal SHA256
  `73b924db02289be79e931e895d5107996ce2684b1a2059aee3fe0dec8ab651a8`,
  with `5` static objects, `32` valid neighbors, and `60` WHITE route points.
  Its dry-run plan verified v2 schema, K=8, and fixed DP without loading the
  model or creating a candidate output.
- CAMP local/GitHub/AutoDL was
  `c8d825a41c991fea625ca0022d15de2551d83d2a`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
  The old manifest and old candidate root remained immutable; all `369` old
  candidate SHA checks passed before and after refresh.
- No candidate generation, physical-feasibility/atom/label materialization,
  training, holdout-label access, evaluation, claim, promotion, deployment,
  activation, DP modification, or raw-data redistribution occurred. No
  weights or performance metrics exist at this source-only gate.

current_v18_status=v18_nuplan_mini_refreshed_causal_manifest_and_single_record_source_smoke_preflight_passed
current_v18_artifact_scope=nuplan_mini_refreshed_causal_manifest_and_single_record_source_smoke_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_preflight_retry_20260711T000659CST
current_v18_artifact_root_sha256=7a98d8a82bb4e65e774a7145a192098e13ce4180eb9320d20c770613f4c2c3e4
next_work_target=v18_nuplan_mini_refreshed_causal_manifest_and_single_record_source_smoke_execution_only

## Gate 16: Refreshed-Source Single-Record Fixed-DP Execution

Status: execution passed after read-only evidence review; independent semantic
NPZ result review is the only next gate.

- Execution artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_execution_951edfc0_20260711T001154CST`
  / `e50b7cff0f6f2422a890718487097f6940b3b146c4007c01a28769284162d9df`.
- Read-only evidence-review artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_execution_evidence_review_20260711T001320CST`
  / `a11bb0d78e4c6fa51b89bc282da42fd689a4bdb11f42fcd2bd42ac92332309fc`.
  The review invoked the model zero times and did not rerun execution.
- CAMP local/GitHub/AutoDL was
  `951edfc02538d8318b6d9f5886acb905fad4117c`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- The execution used refreshed v2 manifest SHA256
  `bcf19b29b9c3654f41502d494a441858142d2d9c3b77bd686b5a764c1107d7a2`,
  seed `3407`, K=8, and only the predeclared first calibration record
  `07ef2e232c8450f9` / decision `53710c1319405da6`. Its causal input SHA256
  remained
  `73b924db02289be79e931e895d5107996ce2684b1a2059aee3fe0dec8ab651a8`.
- All `16` target tests passed before execution. Fixed DP completed the eight
  contract calls in `1.146308s`; DP Top-1 remained index 0. The candidate
  tensor / same-call neighbor tensor SHA256 values are
  `95191e53823392010ac5372d1a1dc66ae84c62fb90bd5358e0088b5dfaca3bb5`
  / `da713dee29d1aa99d93cbd5c7521d3c5570923d84f86ea3e8894d2cfcef29ba5`.
- The 32-slot neighbor-valid mask SHA256 is
  `72cd6e8422c407fb6d098690f1130b7ded7ec2f7f5e1d30bd9d521f015363793`;
  all `32` source neighbor slots are valid. The per-candidate signal-source
  mask SHA256 is
  `04abc8821a06e5a30937967d11ad10221cb5ac3b5273e434f1284ee87129a061`;
  all `8 / 8` candidates retain a resolvable signal source.
- The saved NPZ SHA256 is
  `637dcf326c68afab1d06044afdc817705ae64f9a80c3b62636d96b444b9d7c6d`.
  Execution mechanical checks passed, but this gate intentionally did not
  open the NPZ for independent semantic review.
- The source execution's only stderr was the fixed-DP dependency warning that
  importing `timm.models.layers` is deprecated. The independent review
  verified the exact two-line FutureWarning, no traceback/error, source
  `run.exit=0`, result pass, NPZ hash, and the complete SHA chain. Its own
  stderr is empty and exit is 0.
- The saved `eligible_for_canonical_14d=true` flag means only that the
  candidate signal-source mask is all true. Physical feasibility remains
  explicitly unmaterialized, so final canonical-14D materialization readiness
  is still false. No feasibility/atom/label materialization, training,
  holdout-label access, evaluation, claim, promotion, deployment, activation,
  DP modification, or raw-data redistribution occurred.

current_v18_status=v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_execution_passed
current_v18_artifact_scope=nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_execution_evidence_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_execution_evidence_review_20260711T001320CST
current_v18_artifact_root_sha256=a11bb0d78e4c6fa51b89bc282da42fd689a4bdb11f42fcd2bd42ac92332309fc
next_work_target=v18_nuplan_mini_refreshed_causal_manifest_and_single_record_source_smoke_result_review_only

## Gate 17: Refreshed-Source Single-Record Semantic Result Review

Status: passed after a review-artifact serialization retry; full refreshed
candidate-regeneration preflight is the only next gate.

- The first review artifact / root SHA256 was
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_result_review_20260711T001643CST`
  / `7206df3bab64c6a9e82cd791f653d7641b6b6b0473f3c67d42f61f52671caa00`.
  All `16` tests passed and semantic computation reached result writing, but
  JSON serialization rejected a `numpy.bool_`. The source NPZ was not changed
  and the failed review artifact remains immutable.
- The passing retry review artifact / root SHA256 is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_result_review_retry_20260711T001715CST`
  / `787ae9f02095a5cea17887052256feb0ca52c4cbdfc4085412bbb9dd33d01582`.
  Its only repair normalized check values to built-in booleans before JSON
  serialization. It passed with empty stderr, `run.exit=0`, and a verified
  SHA chain.
- The independent reviewer invoked the model zero times and generated no
  candidate. It reverified execution artifact root
  `e50b7cff0f6f2422a890718487097f6940b3b146c4007c01a28769284162d9df`
  and evidence-review root
  `a11bb0d78e4c6fa51b89bc282da42fd689a4bdb11f42fcd2bd42ac92332309fc`,
  then opened the sole NPZ with pickle disabled.
- Semantic failures: `0`. The NPZ has exactly the nine v2 fields, finite
  float32 candidate `[8,80,4]` and neighbor `[8,32,80,4]` tensors, bool
  neighbor `[32]` and signal `[8]` masks, K=8, and DP Top-1 index 0. Every
  tensor/file hash matched the execution record and the review left both the
  candidate tensor and NPZ bytes unchanged.
- All `8 / 8` candidates and all `8 / 8` candidate-specific neighbor bundles
  are unique. All `32` source neighbor slots are valid. Independent causal
  replay matched refreshed input SHA256
  `73b924db02289be79e931e895d5107996ce2684b1a2059aee3fe0dec8ab651a8`.
- The route contains `60` WHITE source points. An independently implemented
  distance/heading/moving predicate exactly reproduced the saved signal mask:
  all `8 / 8` candidates retain a resolvable signal source. No future field is
  present in the NPZ.
- `materialization_ready=false` remains authoritative because
  `physical_feasibility_mask` is absent. Signal-source eligibility alone is
  not canonical-14D readiness. No feasibility/atom/label materialization,
  training, holdout-label access, evaluation, claim, promotion, deployment,
  activation, DP modification, or raw-data redistribution occurred.
- CAMP local/GitHub/AutoDL was
  `c6a7d182329112fdf19b42601eb5382ce48c63cf`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

current_v18_status=v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_result_review_passed
current_v18_artifact_scope=nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_semantic_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_single_record_source_smoke_result_review_retry_20260711T001715CST
current_v18_artifact_root_sha256=787ae9f02095a5cea17887052256feb0ca52c4cbdfc4085412bbb9dd33d01582
next_work_target=v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_preflight_only

## Gate 18: Full Refreshed Candidate-Regeneration Preflight

Status: passed; full refreshed candidate regeneration execution is the only
next gate.

- Preflight artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_preflight_20260711T002024CST`
  / `f1d25397bc93906c57d4503c4ec4fe0941d1af3d4cf3d113d20f59fda09d150e`.
  All `16` target tests passed; artifact stderr is empty, `run.exit=0`, and the
  complete SHA chain reverified.
- CAMP local/GitHub/AutoDL was
  `ba13792f18b0caefbebcd9cd194cdcdff26f95a1`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- The dry-run validated all `367` v2 manifest rows at SHA256
  `bcf19b29b9c3654f41502d494a441858142d2d9c3b77bd686b5a764c1107d7a2`,
  K=8, seed `3407`, fixed checkpoint SHA256
  `4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75`,
  and fixed args SHA256
  `42c1174de7db49d20343d9ff155093ee206ea9fb31bf0fa7185b108e36c66caa`.
  Scene/log counts remain `226/68/73` and `25/9/12`, with zero log overlap
  and `367` unique scene tokens.
- The planned immutable output root is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_candidates_bcf19b29b9c`;
  it was absent before and after preflight. The model context was never loaded
  and candidate generation was false.
- The measured single-record NPZ is `340883` bytes and fixed-DP execution took
  `1.146308s`. Linear full-run projection is `420.695036s`
  (`7.011584` minutes), `125104061` candidate bytes, `417279` record bytes,
  and `125525436` total projected bytes. Available space was
  `20080553984` bytes, more than twice the projection.
- Source execution/review SHA chains and the old candidate-root SHA
  `7a53d2ac348d0b8ddd49e11434131dce26619873a038d5709fa3c8d931441f73`
  reverified. No candidate generation, feasibility/atom/label materialization,
  training, holdout-label access, evaluation, claim, promotion, deployment,
  activation, DP modification, or raw-data redistribution occurred.

current_v18_status=v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_preflight_passed
current_v18_artifact_scope=nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_preflight_20260711T002024CST
current_v18_artifact_root_sha256=f1d25397bc93906c57d4503c4ec4fe0941d1af3d4cf3d113d20f59fda09d150e
next_work_target=v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_execution_only

## Gate 19: Full Refreshed Candidate Regeneration Execution

Status: passed; independent full semantic result review is the only next
gate.

- Execution artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_execution_0c925a6f_20260711T002344CST`
  / `16ce79895571e422652e1e1f61baaf38a002312b8dcb32a0d47e518bbd7f9c2b`.
- New immutable candidate output / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_candidates_bcf19b29b9c`
  / `92b2c989187d58387e3310579cc9d3ea9695b2b369684d807020c98f6885b028`.
  `records.jsonl` / `summary.json` SHA256 values are
  `7ea1e0e58a10eb4e3d652e99e4baa34642c4329ddff42587df0b519350244476`
  / `6c44a6888da3c5d3d68eb3f5e4954468fae6ba73a38fff1025c7aa2b3a1f4e13`.
- CAMP local/GitHub/AutoDL was
  `0c925a6f874b057b3f0cbd6b954b3cd368891d19`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- One background process only was launched and monitored at `20`, `106`,
  `201`, `296`, then `367` records. It exited with `run.exit=0`, zero active
  jobs, empty stderr, and exactly `367` JSONL records plus `367` NPZ files.
  The exact fixed-DP timm FutureWarning classified at Gate 16 was suppressed
  by a recorded message/category warning filter; no other stderr was hidden.
- All `16` target tests passed. Refreshed manifest SHA256
  `bcf19b29b9c3654f41502d494a441858142d2d9c3b77bd686b5a764c1107d7a2`,
  K=8, seed `3407`, 2936 contract forward calls, identity/order, causal hashes,
  DP Top-1 index 0, per-NPZ file hashes, source schema, and split counts all
  passed mechanical finalization.
- Wall-clock / per-record time was `251.953510s / 0.686522s`. The output uses
  `125561203` bytes. Neighbor-valid counts span `3..32`.
- Execution metadata reports `2847 / 2936` candidate signal sources available
  and `89` unavailable. `354 / 367` records have all eight sources available;
  `13` are fail-closed. These aggregate values are not accepted as semantic
  truth until the independent reviewer opens every NPZ and recomputes them.
- Physical feasibility remains unmaterialized for every record. No semantic
  NPZ review, atom/label materialization, training, holdout-label access,
  evaluation, claim, promotion, deployment, activation, DP modification, or
  raw-data redistribution occurred.

current_v18_status=v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_execution_passed
current_v18_artifact_scope=nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_execution
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_execution_0c925a6f_20260711T002344CST
current_v18_artifact_root_sha256=16ce79895571e422652e1e1f61baaf38a002312b8dcb32a0d47e518bbd7f9c2b
next_work_target=v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_result_review_only

## Gate 20: Full Refreshed Candidate Regeneration Semantic Result Review

Status: passed; physical-feasibility plus canonical-atom/expert-label
materialization preflight is the only next gate.

- Review artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_full_candidate_regeneration_result_review_20260711T003105CST`
  / `c8c7aa07a59ca6a3b460e51fbba775f4c59dfc721e1b73e3303cf623692929c5`.
  All `16` target tests passed; review stderr is empty, `run.exit=0`, and the
  complete SHA chain reverified.
- CAMP local/GitHub/AutoDL was
  `b77c53439b237afe4debc8478daa70d08d35ddda`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- The reviewer invoked the model zero times and generated no candidates. It
  reverified execution root
  `16ce79895571e422652e1e1f61baaf38a002312b8dcb32a0d47e518bbd7f9c2b`
  and candidate-output root
  `92b2c989187d58387e3310579cc9d3ea9695b2b369684d807020c98f6885b028`
  before and after review.
- It opened all `367` NPZ files with pickle disabled, independently replayed
  all `367` causal inputs, and recomputed every WHITE distance/heading/moving
  signal predicate. Semantic failures: `0`; review wall-clock was
  `69.974425s`; holdout label values remained sealed.
- Exact fields, `[8,80,4]` candidate and `[8,32,80,4]` paired-neighbor shapes,
  bool masks, dtypes, finiteness, K=8, DP Top-1 index 0, identities, causal
  hashes, tensor/file hashes, and split counts all passed. No future NPZ field
  exists and review did not mutate the output root.
- Every record has `8 / 8` unique candidates and `8 / 8` unique paired-neighbor
  bundles. Candidate-tensor, neighbor-tensor, and NPZ hashes are each unique
  for all `367 / 367` records. The first full-run tensors exactly reproduce
  the independently generated single-record smoke. Neighbor-valid counts span
  `3..32`.
- The independently recomputed signal aggregate is exactly `2847` available
  and `89` unavailable candidates; `354` records have all eight available and
  `13` remain fail-closed. These values match execution metadata.
- `materialization_ready=false` remains authoritative solely because the
  physical feasibility mask has not been materialized. No feasibility/atom/
  label materialization, training, holdout-label access, evaluation, claim,
  promotion, deployment, activation, DP modification, or raw-data
  redistribution occurred.

current_v18_status=v18_nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_result_review_passed
current_v18_artifact_scope=nuplan_mini_refreshed_causal_manifest_full_candidate_regeneration_semantic_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_refreshed_full_candidate_regeneration_result_review_20260711T003105CST
current_v18_artifact_root_sha256=c8c7aa07a59ca6a3b460e51fbba775f4c59dfc721e1b73e3303cf623692929c5
next_work_target=v18_nuplan_mini_physical_feasibility_canonical_atom_and_expert_label_materialization_preflight_only

## Gate 21: Physical-Feasibility / Canonical-Atom / Expert-Label Preflight

Status: passed; test-driven implementation of the exact materialization path
is the only next gate.

- Preflight artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_preflight_20260711T003754CST`
  / `0032427b9950572cba0ce1c4cdfe0b9a59e93a135810120a62e8305eaf1b9b36`.
  All `22` target tests passed; stderr is empty, `run.exit=0`, and the complete
  SHA chain reverified.
- CAMP local/GitHub/AutoDL was
  `6651dfae02b321cdcf6091ad66202417e5be08ff`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Candidate-output and semantic-review SHA chains reverified. The regenerated
  signal mask leaves `354` source-complete records and `13` preserved
  fail-closed records. Eligible train/calibration/holdout scene counts are
  `217 / 66 / 71`; log counts remain `25 / 9 / 12`.
- The sample calibration record converts its `32` valid same-slot neighbor
  predictions plus `5` real static boxes into finite OBB source tensors with
  shapes `[8,32,80,5]`, `[8,5,80,5]`, and combined `[8,37,80,5]`.
  Neighbor width/length come from current causal history indices `6 / 7`;
  static width/length come from the fixed ten-field schema.
- The sample route contains `400` real points, boundary half-widths from
  `1.1316393613815308` to `3.897575855255127` m, and actual segment speed
  limits from `2.2351362705230713` to `13.410818099975586` m/s. These varying
  sources cannot be replaced by one scalar.
- Reusable low-level paths are canonical availability/matrix validation,
  CAMP's dynamic OBB collision branch, red-stopping cost, and the frozen
  fixed-DP red-light reward formula. No complete existing materializer is
  directly reusable.
- Existing `build_context_from_scene` and `compute_atom_bank_vector` paths are
  forbidden or insufficient here: they use first/median scalar speed or lane
  values, a current-speed desired fallback, static point distances, and a
  zero-feasible progress fallback. Those would violate the registered
  per-segment and fail-closed contracts.
- The required physical mask is saved signal-source availability AND exact
  variable-boundary lane corridor AND exact OBB collision over same-call
  neighbors plus real static objects. Canonical atoms require per-segment
  speed/boundary projection, OBB clearance, feasible-set progress, fixed-DP
  red cost, lateral/red-stopping costs, and DP-prior jerk excess.
- Prior immutable evidence covers expert timestamp brackets for all `294`
  train+calibration records. The implementation may materialize labels only
  for the `283` source-complete train+calibration records, in the decision
  SE(2) frame on the 0.1-second grid through 8 seconds, with interpolation but
  no extrapolation. Holdout label values remain sealed.
- `materialization_ready=false` and `implementation_required=true`. This gate
  invoked the model zero times and did not generate candidates, materialize
  feasibility/atoms/labels, train, access holdout labels, evaluate, claim,
  promote, deploy, activate, modify DP, or redistribute raw data.

current_v18_status=v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_preflight_passed
current_v18_artifact_scope=nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_preflight_20260711T003754CST
current_v18_artifact_root_sha256=0032427b9950572cba0ce1c4cdfe0b9a59e93a135810120a62e8305eaf1b9b36
next_work_target=v18_nuplan_mini_physical_feasibility_canonical_atom_and_expert_label_materialization_test_driven_implementation_only

## Gate 21 Acceptance-Contract Addendum (Record Only)

Status: recorded without rerunning Gate 21 or changing its next target.

- The actual EOF of `docs/diffusion_planner_current_status.md` remains a
  historical v14 pointer. v18 controllers may read only its
  `## Current V18 Status` section, and this v18 audit EOF remains the sole
  current-gate authority. TDD must require the latest five-field v18 pointer
  tuple in both sources to match exactly.
- Candidate 0 is the fixed-DP `draw(noise_scale=0)` deterministic/MAP baseline.
  The historical `dp_top1_index=0` field is position-only and is not evidence
  that fixed DP natively ranked K=8 candidates. Before the first paired
  evaluation, an independent same-input fixed-DP deterministic/MAP inference
  must match candidate 0 elementwise or by tensor SHA256. v18 documentation,
  evaluation, and claim gates must not call it native ranked Top-1 without
  separate native-ranking evidence.
- OBB collision and clearance are exact only within the frozen observable
  source of at most 32 valid same-call dynamic objects and five current static
  boxes. The resulting mask is not complete-scene physical feasibility,
  realized closed-loop safety, or a safety claim. TDD and later artifacts must
  freeze that 32+5 scope and an explicit false closed-loop-safety-claim flag.
- These acceptance constraints do not repeat a gate, invoke the model,
  regenerate candidates, materialize atoms/labels, train, evaluate, access
  holdout labels, modify DP, or change the implementation-only next target.

current_v18_status=v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_preflight_passed
current_v18_artifact_scope=nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_preflight_20260711T003754CST
current_v18_artifact_root_sha256=0032427b9950572cba0ce1c4cdfe0b9a59e93a135810120a62e8305eaf1b9b36
next_work_target=v18_nuplan_mini_physical_feasibility_canonical_atom_and_expert_label_materialization_test_driven_implementation_only

## Gate 22: Canonical Materializer Test-Driven Implementation

Status: passed; materialization execution preflight is the only next gate.

- Immutable AutoDL implementation artifact / root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materializer_implementation_20260711T013440CST`
  / `20dd71a8c7c03a87e9b2a633c708901f345287677e61c6ac7017d936a30a2361`.
  Independent review reverified every SHA256 entry and the root hash;
  `run.exit=0`, stderr is empty, and stdout reports `51 passed, 2 skipped`.
- CAMP local/GitHub/AutoDL was
  `c47d47f559a96d91a07021bb46bcbf6386190e6f`; fixed DP remained
  tracked-clean at `7a1d33da277a1992ec474b5383a0c963c72e04e4`, no v18 job was active,
  and the frozen candidate-root SHA256 remained
  `92b2c989187d58387e3310579cc9d3ea9695b2b369684d807020c98f6885b028`.
- TDD implemented section-bounded current-status reading, independent audit
  EOF equality, sealed-split expert interpolation, ordered route projection,
  exact-within-source OBB collision/clearance, canonical 14D assembly, and an
  immutable materialization mode in the existing v18 orchestrator. The runner
  verifies all 367 candidate identities, NPZ/array hashes, replayed causal
  hashes, source immutability, and fixed-DP state without loading the model.
- The saved physical mask is exactly saved signal-source availability AND
  variable-boundary lane feasibility AND OBB collision-free within the frozen
  at-most-32-dynamic + 5-static observable source. Source-incomplete and all-K
  infeasible rows retain masks/reasons in `records.jsonl` but have no canonical
  NPZ or label, and no candidate-0/all-K progress fallback exists.
- Candidate 0 is recorded only as the fixed-DP deterministic/MAP baseline.
  `dp_top1_index=0` remains position-only, `equivalence_verified=false`, and
  `native_ranked_top1=false`. Independent same-input baseline equivalence is
  still required before the first paired evaluation.
- Eligible holdout canonical NPZs contain atoms and masks but no expert label;
  holdout label values remain sealed. OBB statements remain limited to the
  frozen 32+5 observable source, and `closed_loop_safety_claim=false`.
- This implementation-only gate made zero model calls and did not generate or
  mutate candidates, execute corpus materialization, read any expert label,
  train, evaluate, claim, promote, deploy, activate, modify DP, or redistribute
  raw data. `materialization_ready=false` until execution and result review.

current_v18_status=v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_implementation_passed
current_v18_artifact_scope=nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_test_driven_implementation
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materializer_implementation_20260711T013440CST
current_v18_artifact_root_sha256=20dd71a8c7c03a87e9b2a633c708901f345287677e61c6ac7017d936a30a2361
next_work_target=v18_nuplan_mini_physical_feasibility_canonical_atom_and_expert_label_materialization_execution_preflight_only

## Gate 24: Canonical Materialization Execution Preflight

Status: passed after bounded harness/import remediation; execution only is next.

- After the Gate 23 SHA-count fix, preflight retry 1 failed before execution
  because the fixed-DP reward import did not add the repository's nested
  `diffusion_planner/` package root. Its artifact/root is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_preflight_retry_20260711T014306CST`
  / `ae0ffcd0265a14e3e9ef4e84a1114c8005c5daf9a3e13fb52f6e0a9fd23fa6aa`.
  TDD added only that real package root at commit
  `a0ba0938cb5e382782d5959e4d201661bafba704`; reward math was unchanged.
- Retry 2's parent had not ff-only synchronized before the child imported the
  orchestrator, so the child retained the old module in memory. Its
  artifact/root is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_preflight_retry2_20260711T014513CST`
  / `0ce3a18e940d5e4fd6be97223af3fdbf3bda9860388658cc97e253b9bf1f6ded`.
  No code or data change was required; the parent now ff-only synchronizes
  before starting the validation Python process.
- Retry 3 then passed every functional check and `52 passed, 2 skipped`, but
  its only stderr was the exact already classified upstream
  `timm.models.layers` deprecation FutureWarning. The artifact/root is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_preflight_retry3_20260711T014651CST`
  / `cde6f9380511ce4a9d7bfa0639b608b89fb76157fcc35f17046ea49f3b304076`.
  Retry 4 suppressed only that exact message and `FutureWarning` category;
  all other stderr remained visible.
- Passed retry-4 artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_preflight_retry4_20260711T014741CST`
  / `8e0bf08a5259e1ec9bf41c5d580f5a69250b4f65b99167bea85e733a18c90ffb`.
  Independent review reverified the complete SHA chain, empty stderr,
  `run.exit=0`, and `52 passed, 2 skipped`.
- CAMP/GitHub/AutoDL was
  `a0ba0938cb5e382782d5959e4d201661bafba704`; fixed DP was tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The preflight verified all
  `369` frozen source entries / `367` NPZ files and identities, split counts
  `226/68/73`, fixed-DP red reward import/formula on CPU, live EOF, and
  `19951403008` free bytes versus `125104061` source NPZ bytes.
- Planned output
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_92b2c989`
  and its `.tmp` staging root remain absent. Model calls, candidate generation
  or mutation, corpus materialization, expert-label reads, holdout access,
  training, evaluation, and claims remain zero. Candidate 0 remains the
  deterministic/MAP baseline with `equivalence_verified=false`; OBB scope is
  frozen 32+5 observable only with no closed-loop safety claim.

current_v18_status=v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_execution_preflight_passed
current_v18_artifact_scope=nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_execution_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_preflight_retry4_20260711T014741CST
current_v18_artifact_root_sha256=8e0bf08a5259e1ec9bf41c5d580f5a69250b4f65b99167bea85e733a18c90ffb
next_work_target=v18_nuplan_mini_physical_feasibility_canonical_atom_and_expert_label_materialization_execution_only

## Gate 23: Execution-Preflight SHA-Contract Failure Review and Remediation

Status: passed remediation; execution preflight retry is the only next gate.

- The first execution-preflight artifact/root SHA256 is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_preflight_20260711T013841CST`
  / `e8ee3ffea74f79ddfc20183781c7f16831f2a4f94059ba112a869454c81f46ff`.
  It failed before execution because `_verified_candidate_source` required the
  total `SHA256SUMS` line count to equal the NPZ count. The immutable source
  correctly has `369` lines: `367` NPZ files plus `records.jsonl` and
  `summary.json`. The planned output and staging roots remained absent.
- TDD changed the fixture to the exact 369-entry layout and reproduced the
  failure. The minimal implementation now validates every source entry but
  classifies/counts only `.npz` entries as candidate files. No atom, split,
  baseline, feasibility, or label semantics changed.
- Remediation commit was `2728c98b472b620439d1b1d504a52ae643ebe045` across
  local/GitHub/AutoDL; fixed DP remained tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The remediation artifact/root is
  `/root/autodl-tmp/camp_dp_v18_candidate_root_sha_contract_remediation_20260711T014134CST`
  / `708e5f854de825132f88200a1f5e9ffe76dd120cacbe9d5bc7f5826a4e1eb718`.
  Its full SHA chain, empty stderr, `run.exit=0`, and `51 passed, 2 skipped`
  were independently reverified.
- The real-root verifier now reports exactly `369` source entries, `367` NPZ
  entries, `367` candidate records, and `367` manifest rows under frozen root
  SHA256 `92b2c989187d58387e3310579cc9d3ea9695b2b369684d807020c98f6885b028`.
  Output/staging remain absent; model calls, corpus materialization, candidate
  mutation, expert-label reads, training, evaluation, and claims remain zero.

current_v18_status=v18_nuplan_mini_canonical_materialization_execution_preflight_sha_contract_remediation_passed
current_v18_artifact_scope=nuplan_mini_canonical_materialization_execution_preflight_sha_contract_remediation
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_candidate_root_sha_contract_remediation_20260711T014134CST
current_v18_artifact_root_sha256=708e5f854de825132f88200a1f5e9ffe76dd120cacbe9d5bc7f5826a4e1eb718
next_work_target=v18_nuplan_mini_physical_feasibility_canonical_atom_and_expert_label_materialization_execution_preflight_only

## Gate 25: Gate-24 EOF Placement Correction (Record Only)

Status: Gate 24 remains passed; no preflight or earlier gate was rerun.

The Gate 24 block was inserted before the Gate 23 remediation block because
both historical pointers used the same preflight target. This record restores
the approved controller contract by placing the already-reviewed Gate 24
five-field pointer at the actual audit EOF. It changes no artifact, result,
code, data, candidate, label, baseline, feasibility, or claim semantics.

current_v18_status=v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_execution_preflight_passed
current_v18_artifact_scope=nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_execution_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_preflight_retry4_20260711T014741CST
current_v18_artifact_root_sha256=8e0bf08a5259e1ec9bf41c5d580f5a69250b4f65b99167bea85e733a18c90ffb
next_work_target=v18_nuplan_mini_physical_feasibility_canonical_atom_and_expert_label_materialization_execution_only

## Gate 26: Canonical Materialization Execution and Independent Result Review

Status: passed; deterministic/MAP baseline equivalence preflight is next.

- The first execution failed closed before record 0 under an implementation-
  added `0.5` neighbor-heading norm threshold. Its artifact/root is
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_ad6caa80_20260711T015018CST`
  / `cc78aa8beefc1130dcfd10759d2cdc953d2f4113c24075c5e433aa57570427a1`.
  Corpus diagnostics found `7795` finite non-unit neighbor vectors below 0.5
  across 298 records, zero zero-vectors, and minimum norm
  `0.00295239663682878`. TDD at commit
  `3b5a2453eaa1c7bb6f40c0a73ec870eea026feef` accepts finite norms `>=1e-6`
  through `atan2` and still rejects a zero heading. Atom, split, candidate,
  baseline, and mathematical semantics were unchanged.
- The remediation preflight artifact/root is
  `/root/autodl-tmp/camp_dp_v18_nonunit_heading_remediation_preflight_20260711T015350CST`
  / `a09d310a5e316ed432afa7b950ce1a86b56966c5f2d4a0656176fc176fd41d73`.
  It passed `53` tests with `2` skips plus a real first-record in-memory
  canonical smoke, with zero model and label calls. The old failed staging
  root remains preserved; retry used a new immutable output name.
- Successful execution artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_execution_retry1_3b5a2453_20260711T015444CST`
  / `3ae8cfd536154a2aa71227c17ff2f16d1710d5e601cab9e507b09d16e85ea5f8`.
  Run exit was zero and wall time `233.649882s`. Its only stderr was an
  evidence-runner `PYTHONWARNINGS` parse warning caused by a comma in the
  option; the materializer emitted no traceback. Candidate generation and
  model calls were zero, and the frozen source remained unchanged.
- Immutable canonical output / externally stored output-root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_92b2c989_retry1`
  / `7c89f73e2b26308a42fbd453fff7e0ece4c7d0b49e219a9c56f99bdb2a65d1cc`.
  All 367 source rows remain in `records.jsonl`; 350 canonical NPZs were
  written. Overall counts are 354 signal-source-complete, 13 source-incomplete,
  four all-K-infeasible, 350 materialized, and 279 labelled. By split,
  train/calibration/holdout materialized counts are `214/65/71`; only the
  `214+65` train/calibration outputs contain labels. All 73 holdout rows are
  sealed, including two source-incomplete exclusions.
- The first result reviewer failed before record 0 because its environment
  omitted the preserved Shapely path; artifact/root
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_result_review_20260711T020040CST`
  / `cbdc7b44461e83feef8acad691a28f29bd34ede2cb99e7141a1473272fc96bc8`.
  The next failed on one `2.22e-16` continuous-clearance recomputation delta
  under bit-exact comparison; artifact/root
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_result_review_retry_20260711T020215CST`
  / `108e0952e6756bfd997beb64dbe4d55a1e93273d0e1940ed3e2c88d4d5bbd41b`.
  A third generated reviewer had an indentation error before record 0;
  artifact/root
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_result_review_retry2_20260711T020352CST`
  / `7b900027fd16f0f71e29ee55d4f3708043fc22df096310d8a78d850827fd573d`.
  All were read-only and retained.
- Final independent result-review artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_result_review_retry3_20260711T020531CST`
  / `522cb692dca065990bc3c1307dbcc052db3b76535fa364c6eaba8476a5f9bc0f`.
  It used exact masks, continuous geometry `atol=1e-12`, and atom
  `atol=1e-10` / `rtol=1e-12`; then replayed all 367 causal inputs, recomputed
  all 350 atom matrices/masks, verified all 352 output hashes, requeried all
  214 train and 65 calibration labels, and confirmed 71 materialized holdout
  NPZs contain no label without querying holdout GT. Stderr was empty,
  candidate source was unchanged, and model calls were zero.
- All-K rows retain masks/reasons but no NPZ/label, candidate 0 is never forced,
  and progress has no all-K fallback. Candidate 0 is still only the fixed-DP
  deterministic/MAP baseline with `equivalence_verified=false` and no native
  ranking claim. OBB exactness remains frozen 32+5 observable only with
  `closed_loop_safety_claim=false`.

current_v18_status=v18_nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_result_review_passed
current_v18_artifact_scope=nuplan_mini_physical_feasibility_canonical_atom_expert_label_materialization_semantic_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_canonical_14d_materialization_result_review_retry3_20260711T020531CST
current_v18_artifact_root_sha256=522cb692dca065990bc3c1307dbcc052db3b76535fa364c6eaba8476a5f9bc0f
next_work_target=v18_nuplan_mini_fixed_dp_deterministic_map_baseline_equivalence_preflight_only

## Gate 27: Fixed-DP Deterministic/MAP Baseline Equivalence Preflight

Status: passed after evidence-harness count remediation; equivalence execution
only is next.

- The first preflight's functional command passed its source, live-EOF,
  syntax, SHA, and absent-output checks plus the complete target test file,
  which reported `23 passed`. Its artifact summary nevertheless failed closed
  because the evidence wrapper expected `24 passed`. The preserved
  artifact/root SHA256 is
  `/root/autodl-tmp/camp_dp_v18_fixed_dp_deterministic_map_equivalence_preflight_20260711T021301CST`
  / `4817422e778f4ae496b888f88731e4df295401b059eb992f4c5d86d6dae30c3c`.
- Retry 1 changed only that harness expectation. The equivalence execution
  script remained byte-identical. It passed `23` tests, `run.exit=0`, empty
  stderr, script compilation, source validation, controller validation, and
  `git diff --check`. Independent review reverified every artifact hash and
  confirmed both the planned output and its `.tmp` staging root remain absent.
- Passed preflight artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_fixed_dp_deterministic_map_equivalence_preflight_retry1_20260711T021515CST`
  / `04ed3d80afe6bd48b39ced903e97604c010d32e743c8499fca61635fe5631a48`.
  CAMP local/GitHub/AutoDL is
  `f64390b3fe877d9492c5cb49e55aca78d51b9718`; fixed DP is tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The preflight pinned candidate,
  canonical-output, checkpoint, and args SHA256 identities and all 367
  records.
- The planned execution makes 367 independent native fixed-DP
  `noise_scale=0` model calls on the same causal inputs and records exact
  elementwise/SHA comparisons against saved candidate 0. It cannot generate
  or mutate candidate tensors and reads no expert labels. This gate made zero
  model calls; all 71 holdout labels remain sealed.
- Candidate 0 remains only the fixed-DP deterministic/MAP baseline with
  `equivalence_verified=false`; `dp_top1_index=0` is not native ranking
  evidence and no native K=8 Top-1 claim is made. OBB exactness remains limited
  to the frozen 32 dynamic + 5 static observable source and is not a complete-
  scene, closed-loop, or safety claim.

current_v18_status=v18_nuplan_mini_fixed_dp_deterministic_map_baseline_equivalence_preflight_passed
current_v18_artifact_scope=nuplan_mini_fixed_dp_deterministic_map_baseline_equivalence_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_fixed_dp_deterministic_map_equivalence_preflight_retry1_20260711T021515CST
current_v18_artifact_root_sha256=04ed3d80afe6bd48b39ced903e97604c010d32e743c8499fca61635fe5631a48
next_work_target=v18_nuplan_mini_fixed_dp_deterministic_map_baseline_equivalence_execution_only

## Gate 28: Fixed-DP Deterministic/MAP Equivalence Execution and Result Review

Status: passed; the preauthorized static-14D training/calibration/paired-
evaluation spec and implementation plan are next.

- CAMP local/GitHub/AutoDL was
  `43eed86ae23072ff5491b904bac7612f3dcdf3aa`; fixed DP remained tracked-clean
  at `7a1d33da277a1992ec474b5383a0c963c72e04e4`. The single execution job used
  the byte-identical Gate-27-preflighted script and completed in `99.297708s`.
- Execution artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_fixed_dp_deterministic_map_equivalence_execution_43eed86a_20260711T021821CST`
  / `6f110774bcae701489466957aaed27c859896cb3e254185eeda943b5ab67245a`.
  Its 12-file SHA chain, empty stderr, `run.exit=0`, frozen CAMP/DP/checkpoint/
  args identities, and candidate source before/after identity all passed.
- Immutable equality output/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_fixed_dp_deterministic_map_equivalence_7a1d33da_92b2c989`
  / `8c73b250d253989cb378b4d7fd7e36be878303e76bb7ce205b2810ccc6fea9b0`.
  The 367 direct native fixed-DP `noise_scale=0` calls yielded 367/367 exact
  elementwise matches, 367/367 SHA matches, and maximum absolute difference
  `0.0` against frozen candidate 0. Candidate generation/mutation and expert-
  label reads were zero; all holdout labels remained sealed.
- Independent result-review artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_fixed_dp_deterministic_map_equivalence_result_review_20260711T022156CST`
  / `25f8e3f3763b5af53d70cdba7dddcf85872b42ce459b6b223b1b65cb5b59ea50`.
  The reviewer verified the complete execution/output SHA chains, exact
  script identity and direct-native-call semantics, all 367 unique identities,
  actual frozen candidate-0 hashes, split counts `226/68/73`, and unchanged
  source. Review model calls and label reads were zero; stderr was empty.
- `equivalence_verified=true`: candidate 0 is proven equal to an independent,
  same-input fixed-DP deterministic/MAP output. This is baseline identity
  evidence only. `native_ranked_top1=false`; `dp_top1_index=0` still does not
  establish native K=8 ranking and no such claim is authorized.
- OBB feasibility/exactness remains bounded to the frozen 32 dynamic + 5
  static observable source. No complete-scene physical-feasibility, closed-
  loop safety, or safety claim follows from this gate.

current_v18_status=v18_nuplan_mini_fixed_dp_deterministic_map_baseline_equivalence_result_review_passed
current_v18_artifact_scope=nuplan_mini_fixed_dp_deterministic_map_baseline_equivalence_semantic_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_fixed_dp_deterministic_map_equivalence_result_review_20260711T022156CST
current_v18_artifact_root_sha256=25f8e3f3763b5af53d70cdba7dddcf85872b42ce459b6b223b1b65cb5b59ea50
next_work_target=v18_nuplan_mini_static_14d_convex_training_calibration_paired_evaluation_spec_and_plan_only

## Gate 29: Static-14D Training, Calibration, and Paired-Evaluation Spec/Plan

Status: frozen design; inline TDD implementation is next without another
approval checkpoint.

- Frozen combined spec/plan:
  `docs/superpowers/plans/2026-07-11-v18-static-training-calibration-paired-evaluation.md`
  / SHA256 `fed21178ec0c2e13d839dc02c3a1fd38add3b0b281c8437bd06292a2b79d3f42`.
- The plan adds one thin v18 runner and reuses the existing finite-candidate
  robust-margin cutting-plane master. It forbids the v16 legacy epoch trainer,
  Theta, candidate changes, non-affine/non-simplex scoring, and any calibration
  or holdout contribution to scaling/training.
- It freezes train-only feasible-row 95th-percentile scaling, ADE-primary and
  FDE-secondary oracle semantics, margin scale/clip `0.1/2.0`, CVaR `0.9`, L2
  `1e-4`, CLARABEL, 20 iterations, tolerance `1e-6`, exact optimal/convergence/
  final-cut acceptance, and seeds `3408/3409/3410` with 11/12/13 forbidden.
- Calibration is tuning-free and cannot modify the checkpoint or paired-eval
  protocol. Before holdout access, the plan freezes weights/scales/hashes,
  `2.0m` miss, `1e-9m` tie, zero non-regression slack, 10,000 log/scene cluster
  bootstrap replicates, latency measurement, one-shot receipt, and all claim
  boundaries.
- Candidate 0 remains the equivalence-proven fixed-DP deterministic/MAP
  baseline with `native_ranked_top1=false`. OBB exactness remains bounded to
  the frozen 32+5 observable source. Mini results remain smoke/directional only.
- No model call, training, calibration, holdout label access, evaluation,
  candidate mutation, claim, promotion, deployment, or activation occurred in
  this plan-only gate.

current_v18_status=v18_nuplan_mini_static_14d_convex_training_calibration_paired_evaluation_spec_plan_passed
current_v18_artifact_scope=nuplan_mini_static_14d_convex_training_calibration_one_shot_paired_evaluation_frozen_spec_plan
current_v18_artifact=docs/superpowers/plans/2026-07-11-v18-static-training-calibration-paired-evaluation.md
current_v18_artifact_root_sha256=fed21178ec0c2e13d839dc02c3a1fd38add3b0b281c8437bd06292a2b79d3f42
next_work_target=v18_nuplan_mini_static_14d_convex_training_calibration_paired_evaluation_tdd_implementation_only

## Gate 30: Static-14D Training/Calibration/Paired-Evaluation Implementation

Status: passed; train/calibration execution preflight only is next.

- TDD produced one thin runner,
  `scripts/integrations/run_diffusion_planner_dp_camp_v18_training_evaluation.py`,
  and one focused test file. The runner reuses
  `solve_robust_margin_cutting_plane`, supports atomic `train-calibrate`, no-
  label `paired-eval-preflight`, and one-shot `paired-eval` modes, and never
  uses the legacy epoch trainer or Theta.
- The existing robust-margin master changed only to expose the actual CVXPY
  solver name. No objective, constraint, cut, variable, or convergence logic
  changed. The v18 acceptance gate requires actual CLARABEL plus exact
  `optimal`, convergence, final gap `<=1e-6`, no final new cut, independent
  complete-candidate violation agreement, and nonnegative simplex weights.
- The implementation enforces immutable canonical/candidate/equivalence roots,
  exact 14D schema, train/cal/holdout materialized-only loading, train-only
  feasible-row scaling, ADE-primary/FDE-secondary labels, seeded ties, all-K
  fail-closed exclusion, tuning-free calibration, atomic freeze manifests,
  zero-label preflight, one label read per holdout identity, derived-metric-only
  persistence, paired metrics, log/scene CI95, and latency reporting.
- Local validation passed `75 passed, 2 skipped, 1 deselected`; the deselection
  is the known Windows torch import abort. Local robust-margin validation was
  `4 passed, 2 skipped`. AutoDL ran that torch case and all solver tests.
- The first AutoDL artifact correctly retained failed status because its
  evidence harness expected local robust-margin skip counts even though the
  functional run passed `76 passed, 2 skipped` plus six robust-margin tests.
  Artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_static_14d_training_evaluation_implementation_a8d2e439_20260711T023801CST`
  / `90654d3b3e55acdf7a07cf94b5f75b1bb928baf4b8286efbdce69cc2e2529c6c`.
- Retry 1 changed only that expected count and passed compile, the full suite
  (`76 passed, 2 skipped`), robust-margin regression (`6 passed`), and diff
  check with empty stderr. Its artifact/root SHA256 is
  `/root/autodl-tmp/camp_dp_v18_static_14d_training_evaluation_implementation_retry1_a8d2e439_20260711T023833CST`
  / `58fb4b4c3a63f8c5d21df41f9ef5ba456b003a2015aa25a70473a438f0c2c4c6`.
  Independent review reverified all hashes, local/GitHub/AutoDL CAMP
  `a8d2e439f1984b2a28230c71743b4f676c666987`, fixed DP
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`, tracked-clean status, and no job.
- Model calls, candidate generation/mutation, training, calibration, expert
  label reads, and holdout label reads remained zero. Candidate 0 remains the
  equivalence-proven fixed-DP deterministic/MAP baseline with
  `native_ranked_top1=false`; feasibility exactness remains bounded 32+5 and
  is not a safety claim.

current_v18_status=v18_nuplan_mini_static_14d_convex_training_calibration_paired_evaluation_implementation_passed
current_v18_artifact_scope=nuplan_mini_static_14d_convex_training_calibration_one_shot_paired_evaluation_tdd_implementation
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_static_14d_training_evaluation_implementation_retry1_a8d2e439_20260711T023833CST
current_v18_artifact_root_sha256=58fb4b4c3a63f8c5d21df41f9ef5ba456b003a2015aa25a70473a438f0c2c4c6
next_work_target=v18_nuplan_mini_static_14d_convex_training_calibration_execution_preflight_only

## Gate 31: Static-14D Training and Calibration Execution Preflight

Status: passed; one atomic train/calibration execution is next.

- CAMP local/GitHub/AutoDL is
  `018013e33f1193bb4a2b6e206b62013c2982555c`; fixed DP remains tracked-clean
  at `7a1d33da277a1992ec474b5383a0c963c72e04e4`; no v18 training/evaluation job
  is active.
- Artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_static_14d_training_calibration_execution_preflight_20260711T024457CST`
  / `96d8a94ce306878a086359ce267a688771f1d6c8d1bb2370bf842bd1293fe673`.
  Independent review reverified every hash, empty stderr, and `run.exit=0`.
- The preflight verified 352 canonical output hashes, 367 immutable candidate
  identities, candidate root
  `92b2c989187d58387e3310579cc9d3ea9695b2b369684d807020c98f6885b028`,
  canonical root
  `7c89f73e2b26308a42fbd453fff7e0ece4c7d0b49e219a9c56f99bdb2a65d1cc`,
  and equivalence review root
  `25f8e3f3763b5af53d70cdba7dddcf85872b42ce459b6b223b1b65cb5b59ea50`.
- Exact materialized shapes/counts passed: train `214 x 8 x 14` with 214
  stored labels, calibration `65 x 8 x 14` with 65 stored labels, and holdout
  `71 x 8 x 14` with zero labels. Train-only scales, train/cal ADE/FDE oracles,
  and `[214,8]` margins were constructed without an optimizer call.
- CVXPY `1.6.7` has CLARABEL installed. The planned output
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_static_14d_train_calibrate_018013e3_7c89f73e`
  and its `.tmp` root remain absent; `19940229120` data-disk bytes were free.
- DB expert-label queries, holdout label reads, model calls, optimizer calls,
  training, calibration execution, candidate generation/mutation, and claims
  remained zero. Candidate 0 wording and 32+5/no-safety boundaries are
  unchanged.

current_v18_status=v18_nuplan_mini_static_14d_convex_training_calibration_execution_preflight_passed
current_v18_artifact_scope=nuplan_mini_static_14d_convex_training_calibration_execution_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_static_14d_training_calibration_execution_preflight_20260711T024457CST
current_v18_artifact_root_sha256=96d8a94ce306878a086359ce267a688771f1d6c8d1bb2370bf842bd1293fe673
next_work_target=v18_nuplan_mini_static_14d_convex_training_calibration_execution_only

## Gate 32: Static-14D Training/Calibration Execution, Review, and Freeze Gate

Status: passed; one-shot holdout paired-evaluation preflight only is next.

- Atomic execution completed at CAMP
  `91c707c72b0b6caa15751f2df5719a7f73585d7b` in `1.616792s`. Its
  artifact/root SHA256 is
  `/root/autodl-tmp/camp_dp_v18_static_14d_training_calibration_execution_91c707c7_20260711T025646CST`
  / `54efa11e844f1daeb5a5b2b05fe18cd02ff2903ffd640db8ab2892c3482dead0`.
  Stderr was empty, `run.exit=0`, candidate generation/mutation and holdout
  label reads were zero.
- Immutable selector freeze/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_static_14d_train_calibrate_018013e3_7c89f73e`
  / `b09a81f94776a59ad6ac8fe93ec27f610d4b74859efa1b10f7f4d0160596a058`.
  It freezes weights, train-only atom scales, training/calibration evidence,
  and every paired-evaluation seed, threshold, metric, bootstrap, latency,
  baseline, feasibility, and claim boundary.
- CLARABEL reported exact `optimal`. Three cutting-plane iterations ended at
  `final_master_gap=3.7112410922190975e-09`, `final_new_cuts=0`, simplex sum
  `0.9999999999999998`, and minimum weight `0.0`. No legacy epoch, Theta,
  non-affine, non-simplex, or candidate-tensor path ran.
- Train paired directionals: ADE delta `-0.06059399938511513m`, FDE delta
  `-0.21927360864829598m`, miss delta `+0.018691588785046728`, and
  better/tie/worse `119/12/83`. Calibration directionals: ADE delta
  `+0.011207092485777554m`, FDE delta `-0.016912244014756304m`, miss delta
  `0.0`, and better/tie/worse `33/3/29`. Calibration was tuning-free and made
  zero model/scale/protocol updates.
- The first independent reviewer failed only because saved simplex-projected
  weights changed CVaR from raw-solver history by `1.6691e-11` under an
  over-strict `1e-12` check. Its artifact/root is
  `/root/autodl-tmp/camp_dp_v18_static_14d_training_calibration_result_review_20260711T025822CST`
  / `64a063d2ae5d6a843821c2c954027529846dc2a0e89e9d48fb52691d1173cacf`.
- Retry 1 used only `atol=1e-10`, still one ten-thousandth of the frozen
  training tolerance, and independently passed all execution/freeze hashes,
  exact train-only scales, all-candidate violations, final convergence,
  simplex weights, train/cal metrics, frozen protocol, and 71 label-free
  holdout records. Artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_static_14d_training_calibration_result_review_retry1_20260711T025915CST`
  / `de5a90b7ac5e4295b58f11f48ddbb519646130129644c7cbc8d7b559051b29ea`.
- A post-review contract audit found paired evaluation verified the freeze's
  own SHA but did not require an external passed result-review artifact. TDD at
  CAMP/GitHub/AutoDL `f64ef70d253b61eb413e13b62690bc3ef1a3c794` added exactly
  that gate; weights/scales/protocol were unchanged. AutoDL passed `77 tests`
  with `2` skips, all six robust-margin tests, and the real review/freeze root
  pair. Remediation artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_selector_freeze_review_gate_remediation_f64ef70d_20260711T030239CST`
  / `e2705016a6c490ed051f4a7f7f4f8e96df33ec01556ba997d0def7e669d33312`.
- Reviewer optimizer/model/DB-label/holdout-label calls were zero. All 71
  holdout labels remain sealed. Candidate 0 naming, native-ranking false, mini
  directional-only, 32+5 observable, and no-safety boundaries remain frozen.

current_v18_status=v18_nuplan_mini_static_14d_training_calibration_result_review_and_freeze_gate_passed
current_v18_artifact_scope=nuplan_mini_static_14d_training_calibration_freeze_independent_result_review_and_required_review_root_gate
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_selector_freeze_review_gate_remediation_f64ef70d_20260711T030239CST
current_v18_artifact_root_sha256=e2705016a6c490ed051f4a7f7f4f8e96df33ec01556ba997d0def7e669d33312
next_work_target=v18_nuplan_mini_one_shot_holdout_paired_evaluation_preflight_only

## Gate 33: One-Shot Holdout Paired-Evaluation Final Preflight

Status: passed with zero label reads; one-shot execution only is next.

- CAMP local/GitHub/AutoDL is
  `3d720141f16d79da8814cc6326db1a81301e8254`; fixed DP is tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`; no v18 evaluation job is active.
- Artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_one_shot_holdout_paired_evaluation_preflight_20260711T030625CST`
  / `a3727459ab405eab2214c3fe24e80e56c202527ba323fc32ceeba2f78932f4bf`.
  Independent review reverified every hash, empty stderr, and `run.exit=0`.
- The gate jointly verified candidate root `92b2c989...`, canonical root
  `7c89f73e...`, equivalence review `25f8e3f3...`, frozen selector
  `b09a81f94776a59ad6ac8fe93ec27f610d4b74859efa1b10f7f4d0160596a058`,
  and mandatory independent freeze review
  `de5a90b7ac5e4295b58f11f48ddbb519646130129644c7cbc8d7b559051b29ea`.
- Exactly 71 canonical holdout NPZs are label-free and map to unique immutable
  source identities. Two source holdout rows remain fail-closed excluded;
  train/calibration/holdout overlap is zero.
- Planned one-shot output
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_one_shot_paired_eval_b09a81f9_3d720141`
  and its `.tmp` root are absent. Label reads, raw-label persistence, model
  calls, training/model/scale updates, candidate changes, and claims remain
  zero.
- The frozen execution will query each of the 71 expert futures once, persist
  only label SHA receipts and derived candidate metrics, and cannot be rerun
  because either final or staging root blocks entry. Candidate-0 wording,
  native-ranking false, mini directional-only, 32+5, and no-safety boundaries
  are unchanged.

current_v18_status=v18_nuplan_mini_one_shot_holdout_paired_evaluation_preflight_passed
current_v18_artifact_scope=nuplan_mini_reviewed_frozen_static_14d_one_shot_holdout_paired_evaluation_no_label_read_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_one_shot_holdout_paired_evaluation_preflight_20260711T030625CST
current_v18_artifact_root_sha256=a3727459ab405eab2214c3fe24e80e56c202527ba323fc32ceeba2f78932f4bf
next_work_target=v18_nuplan_mini_one_shot_holdout_paired_evaluation_execution_only

## Gate 34: One-Shot Holdout Paired-Evaluation Execution and Result Review

Status: completed with directional/no-claim result; the continuous authorization
ends here and a new user decision is required for any next stage.

- The unique one-shot execution ran at CAMP/GitHub/AutoDL
  `88c3a6fbaa498dd943e98360380e20e054419e24`, fixed DP tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`, and wall time `5.216912s`.
- Execution artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_one_shot_holdout_paired_evaluation_execution_88c3a6fb_20260711T031042CST`
  / `fcbae734d847e250c2ef69563b1de1b356ff7d6fca42e26b0e750ba53a66519d`.
  Stderr was empty and `run.exit=0`.
- Immutable derived evaluation output/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_one_shot_paired_eval_b09a81f9_3d720141`
  / `6ca6bdd70497173356277ce4cb6ed5ba23420a99c381c68f44c5e446c3ffd366`.
  It contains exactly 71 label SHA receipts, 71 derived metric records, and one
  summary; it contains no raw expert future.
- CAMP ADE/FDE/miss are `2.5597696204592677m / 6.806143429715728m /
  0.5915492957746479`; fixed-DP deterministic/MAP baseline ADE/FDE/miss are
  `2.554556872165273m / 7.094755233959905m / 0.6056338028169014`.
  Paired deltas are ADE `+0.005212748293994815m`, FDE
  `-0.28861180424417765m`, and miss `-0.014084507042253521`; ADE
  better/tie/worse is `39/4/28`.
- Log-cluster CI95 for ADE/FDE/miss is
  `[-0.3340948932943097,0.26519963817447834] /
  [-1.4443544304327212,0.45670503604772883] /
  [-0.04918032786885246,0.0]`. Scene-cluster CI95 is
  `[-0.2922391449153926,0.25703153468632395] /
  [-1.2042251649966418,0.39098948966152947] /
  [-0.056338028169014086,0.028169014084507043]`.
- Mean FDE and miss pass the preregistered zero-slack diagnostic, but all
  ADE/FDE CI95 intervals cross zero and scene-cluster miss also crosses zero.
  This cannot establish a performance advantage.
- CAMP and baseline feasible-oracle ADE gaps are `0.6932336480525806m` and
  `0.6880208997585857m`. Candidate 0 was selected four times. Fallback count
  is zero; two nonmaterialized source holdout rows remain fail-closed excluded.
- Selector latency p50/p95/p99/max is
  `0.045659 / 0.04715305 / 0.04987702 / 0.65341 ms`.
- Independent result-review artifact/root SHA256:
  `/root/autodl-tmp/camp_dp_v18_one_shot_holdout_paired_evaluation_result_review_20260711T031321CST`
  / `92a40093ca9baa7b15df4bfab7dfc1dd5166c2f61969703ad0d62d225f4ee2f1`.
  It made zero label queries and reverified all execution/output hashes,
  identities/receipts, selector/oracle decisions, aggregates, 10,000-replicate
  log/scene bootstraps, latency ordering, and immutable upstream roots.
- The only authorized interpretation is nuPlan-mini smoke/directional evidence.
  No performance/safety/CAMP-over-DP claim, promotion, deployment, or activation
  follows. `native_ranked_top1=false`; candidate 0 remains the proven fixed-DP
  deterministic/MAP baseline. OBB exactness remains frozen 32+5 observable
  only and is not complete-scene or closed-loop safety evidence.

current_v18_status=v18_nuplan_mini_one_shot_holdout_paired_evaluation_result_review_completed_directional_no_claim
current_v18_artifact_scope=nuplan_mini_reviewed_frozen_static_14d_one_shot_paired_evaluation_directional_smoke_no_claim
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_one_shot_holdout_paired_evaluation_result_review_20260711T031321CST
current_v18_artifact_root_sha256=92a40093ca9baa7b15df4bfab7dfc1dd5166c2f61969703ad0d62d225f4ee2f1
next_work_target=v18_nuplan_mini_user_decision_required_after_paired_evaluation_result_review_before_any_claim_promotion_deployment_activation_or_next_stage
