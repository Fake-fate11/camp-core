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
