# Diffusion Planner V20 Iteration Audit

## Documentation Bootstrap

This gate repairs the checked-in status pointer before any v20 map-only
runtime work. The reviewed implementation state is CAMP, GitHub, and AutoDL
head `61c607d144688a42ea71a0b2418fa6bf483540c5`, with fixed DP head
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

At that CAMP head, the v20 CARLA route-corridor TDD implementation is ready.
Independent final review recorded `Critical=0` and `Important=0`. The local
and AutoDL seven-file suites each recorded `159 passed`.

This documentation gate ran no candidate, outcome, metric, holdout, simulator,
promotion, deployment, or broad claim. Its next work target is plan-only:
`v20_carla_route_corridor_map_only_contact_tolerance_census_plan_only`.

## Authoritative EOF Pointer

current_v20_status=v20_carla_route_corridor_tdd_ready_independent_final_review_passed
camp_github_autodl_head=61c607d144688a42ea71a0b2418fa6bf483540c5
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
next_work_target=v20_carla_route_corridor_map_only_contact_tolerance_census_plan_only

## Offline Map-Only Contact-Tolerance Census Plan

The concrete TDD plan is frozen at CAMP/GitHub/AutoDL start head
`9537f1998100a32b74cdb6cc6dc36db4837c77f4`, with fixed DP unchanged at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. It adds only one future runner
and one focused test file, reuses the existing route/builder/tolerance
contracts, and binds the sealed CARLA 0.9.16
`Carla/Maps/Town10HD_Opt` XODR to an offline native `carla.Map`.

The planned gate order is static review, TDD runner plus no-run preflight,
exactly one offline map-only census, independent result review, and only then
one source-only fixed-DP K=8 probe. This plan-only gate ran no CARLA server,
map census, candidate, DP worker, outcome, metric, holdout, promotion,
deployment, or claim.

## Authoritative EOF Pointer

current_v20_status=v20_carla_route_corridor_map_only_contact_tolerance_census_plan_ready
camp_github_autodl_head=9537f1998100a32b74cdb6cc6dc36db4837c77f4
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
next_work_target=v20_carla_route_corridor_map_only_contact_tolerance_census_plan_static_review_only

## Census Runtime, Preflight, and AutoDL Verification

At CAMP/GitHub/AutoDL head
`9b35143b0b4dd6b9f432c7a88edf22e7976eb4c1`, the census uses one checked-in
runner and one focused test. The final focused review's two Important runtime
findings were closed: all 16 sealed CARLA client files and `carla.Map` binding
are verified, and normal execution must reproduce the exact preflight runtime,
provenance, and production-import evidence before map construction.

Local verification recorded `10 passed` focused, `169 passed` merged, and
`4 passed` pointer tests, plus clean `py_compile` and `git diff --check`.
AutoDL recorded `59 passed` plus `4 passed`; the listener-remediation evidence
sealed those already-completed tests without rerunning them:

`/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_tdd_listener_remediation_20260714T033121Z`

Root SHA256: `71f456a8fd4ac21399e10da0b63a8205ade0e3bd791211b55933d046a6a516e4`.

The no-map/no-census/no-server production preflight passed at:

`/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_preflight_20260714T033643Z`

Root SHA256: `334c607095755657dbfbf2a843698e48d1780468d584058a02fe0c60998935ff`.

## Exactly-Once Map-Only Census and Independent Result Review

The frozen census command was invoked exactly once against official CARLA
0.9.16 `Carla/Maps/Town10HD_Opt` XODR. It returned exit `1` at the first
corridor-builder call with:

`ValueError: route corridor requires exactly one predecessor`

The execution artifact is:

`/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_census_execution_20260714T033759Z`

Root SHA256: `69b62b632a53265699b6b2ff2ce9ab48c8d98291cde2fa3d712b8b3dff865e50`.

Prechecks passed, `CENSUS_INVOCATION_COUNT=1`, and no prior execution artifact
existed. No receipt or temporary receipt was produced. Related processes and
CARLA listeners were empty before and after execution. The failure occurred
before tolerance freezing and did not load candidates, invoke the DP worker,
or read outcomes, metrics, future labels, or holdout data.

The one independent result review recorded `Critical=0`, `Important=1`, and
`Minor=0` at:

`/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_census_result_review_20260714T034352Z`

Root SHA256: `841a96a97bee37e88a8c27c38e5d81fa1225a4d552ce2bb75b8e79c73b8fc48c`.

The Important finding is a genuine frozen-contract stop: the existing 81 by
5 m deterministic route satisfies the forward-window helper but its first
waypoint does not satisfy the corridor's exactly-one-predecessor requirement.
Success would require changing route selection or the predecessor/source
contract after observing the census result. Census retry and the K=8 probe are
therefore not authorized.

## Authoritative EOF Pointer

current_v20_status=v20_carla_route_corridor_map_only_contact_tolerance_census_failed_closed_frozen_route_predecessor_contract_unsatisfied
camp_github_autodl_head=9b35143b0b4dd6b9f432c7a88edf22e7976eb4c1
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
next_work_target=user_decision_required_before_any_v20_frozen_route_corridor_contract_change_or_census_retry

## Fail-Closed Census Record-Only Closeout Consistency

The census and result-review artifacts remain bound to execution source head
`9b35143b0b4dd6b9f432c7a88edf22e7976eb4c1`. The record-only closeout commit
was then fast-forward synchronized across local, origin, GitHub, and AutoDL at
`3260576186f4efd8d462dc0d5937f9677943b333`, with fixed DP unchanged at
`7a1d33da277a1992ec474b5383a0c963c72e04e4` and both tracked trees clean.

The closeout validation recorded `14 passed`, did not reexecute the census or
K=8, and is sealed at:

`/root/autodl-tmp/camp_dp_v20_carla_contact_tolerance_census_closeout_validation_20260714T034536Z`

Root SHA256: `4b6a6d31fe8dc03a2b69c8f0aad94387367abb43d2ea9fda28f5b23551e7d052`.

The user subsequently authorized one candidate-free, read-only predecessor
topology diagnosis. It may inspect only official XODR, the frozen deterministic
route, and existing map helpers; it cannot run candidates, DP, outcomes,
metrics, future labels, holdout, or a CARLA server.

## Authoritative EOF Pointer

current_v20_status=v20_carla_route_corridor_map_only_census_fail_closed_closeout_synced
current_v20_artifact_source_head=9b35143b0b4dd6b9f432c7a88edf22e7976eb4c1
camp_github_autodl_head=3260576186f4efd8d462dc0d5937f9677943b333
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
next_work_target=v20_carla_route_corridor_predecessor_topology_diagnosis_only

## Candidate-Free Predecessor Topology Diagnosis

The diagnosis executed once against official CARLA 0.9.16 Town10HD_Opt XODR
at CAMP head `4ede23266956eb657c151737d8f860024fd66460`, with fixed DP unchanged.
It loaded no candidates, DP worker, outcomes, metrics, future labels, holdout,
or CARLA server.

The source execution is sealed at:

`/root/autodl-tmp/camp_dp_v20_predecessor_topology_diagnosis_execution_20260714T054917Z`

Root SHA256: `79bd60e6622427212870ff1b7699ae68e510ac8c4a05daca3bb2b335059658ae`.
Receipt SHA256: `d05580d711f226f9335c696842821f7e1ca929092e8b280c7c61b7b01af8e0f1`.

The receipt records start identity `['0', 0, -2]`, predecessor cardinality
`2`, road predecessor link `road 3 / contactPoint end`, lane predecessor
`-2`, `is_junction=false`, and two CARLA predecessor waypoints
`['566', 0, -2]` and `['630', 0, -1]`. The start is not a true OpenDRIVE
topology root and the lookup did not omit a legal predecessor. All forbidden
access counters are zero.

The execution wrapper's malformed result summary and blank invocation counter
were repaired evidence-only, without rerunning CARLA or the diagnosis, at:

`/root/autodl-tmp/camp_dp_v20_predecessor_topology_diagnosis_evidence_remediation_20260714T055031Z`

Root SHA256: `ccdc41bd704beb26afc1bd8ed70624b3162709d52296136be1366e32daee3242`.
This remediation validates the source receipt, seal, timestamps, exit status,
and absence of related processes; it explicitly records
`diagnosis_reexecuted=false`.

The preregistered `cardinality > 1` branch is selected. Ambiguity remains
fail-closed. The minimal design and TDD plan freeze a candidate-free map-level
route selection and prohibit choosing a route from candidate coverage or any
outcome.

## Authoritative EOF Pointer

current_v20_status=v20_carla_route_corridor_predecessor_topology_diagnosed_cardinality_two_ambiguity_fail_closed
current_v20_artifact_source_head=4ede23266956eb657c151737d8f860024fd66460
camp_github_autodl_head=4ede23266956eb657c151737d8f860024fd66460
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
next_work_target=v20_carla_route_corridor_candidate_free_map_level_deterministic_route_selection_tdd_implementation_only

## Candidate-Free Route Selection TDD and Static Review

The existing deterministic-route helper now considers starts in canonical
map order, accepts only a start with exactly one 5 m predecessor, and accepts
each forward step only when the raw successor list contains exactly one
previously unseen waypoint. Invalid starts are skipped; absence of an 81-point
route fails closed. The diagnosis-only call explicitly preserves the former
route helper behavior so the already-sealed diagnosis remains reproducible.

Local verification recorded `48 passed` focused and `174 passed` merged, with
clean `py_compile` and `git diff --check`. The one independent static review
recorded `Critical=0`, `Important=1`, and `Minor=0`. Its Important finding was
closed: a raw `[seen, unseen]` successor list can no longer be reduced to one
apparently valid unseen successor. No second review round was opened.

No candidate, DP worker, outcome, metric, future label, holdout, CARLA server,
or census was used by this gate. The next gate is AutoDL ff-only validation
and no-map preflight before the single authorized revised census.

## Authoritative EOF Pointer

current_v20_status=v20_carla_route_corridor_candidate_free_route_selection_tdd_ready_review_finding_closed
current_v20_artifact_source_head=4ede23266956eb657c151737d8f860024fd66460
camp_github_autodl_head=4ede23266956eb657c151737d8f860024fd66460
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
next_work_target=v20_carla_route_corridor_candidate_free_route_selection_autodl_validation_and_preflight_only

## Candidate-Free Route Selection Validation and Revised Census

AutoDL ff-only synchronized CAMP at
`a8238ba14b20c43176e4d5889f3eb713e877f249`; fixed DP remained
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. The first TDD seal stopped before
tests because `ss` was unavailable. It is preserved fail-marked at:

`/root/autodl-tmp/camp_dp_v20_candidate_free_route_selection_tdd_20260714T060607Z`

Root SHA256: `d3f99d739aab044a6ea0cd52fe6528d3619d307dda80504bfe9b704f04fdd5f9`.
The `/proc/net/tcp*` listener-check remediation ran `174 passed`, compile and
diff checks, without CARLA or census:

`/root/autodl-tmp/camp_dp_v20_candidate_free_route_selection_tdd_listener_remediation_20260714T060709Z`

Root SHA256: `2512bb67e0dd8affca91017b9deed200cfdc0d3080aea3e8e3337d2fea033332`.
The no-map/no-census/no-server production preflight passed at:

`/root/autodl-tmp/camp_dp_v20_candidate_free_route_selection_preflight_20260714T060828Z`

Root SHA256: `331ce41bef60b17b86da5b78a222f4724a6e4819b4a8891a82c7a87acc1d2840`.

The revised map-only census then executed exactly once. Its before/after
invocation counters are `0 / 1`; runner and artifact exits are `0`; all
forbidden counters, related processes, and listeners are zero. It is sealed at:

`/root/autodl-tmp/camp_dp_v20_candidate_free_route_selection_revised_census_execution_20260714T060933Z`

Root SHA256: `a3884f6cb4cf001bd65fe2fdcfcb5eb90b2fc3be1553b20011440e131ca0ed25`.
Receipt SHA256 is `a0c9960b74bdc605983f0c86dd2a2e2c27f0154e6414d20a604640b00699a311`;
route SHA256 is `4bd077585527913491461dd2d446bcc1621aa44c811ca7f0826e3ef461a783b6`;
maximum contact gap is `0.0007186340973698577 m`; frozen tolerance is
`0.0007186350973698577 m`.

The one independent result review passed 33 checks with
`Critical=0`, `Important=0`, and `Minor=0`, without rerunning the census:

`/root/autodl-tmp/camp_dp_v20_candidate_free_route_selection_revised_census_result_review_20260714T061321Z`

Root SHA256: `277a8b3cf9cfebfb70f53b0c3df089b5a53d6cec7ed379ef330619dd6a7294f1`.
It authorizes exactly one source-only fixed-DP K=8 probe and forbids another
census. No outcome, metric, future label, holdout, promotion, deployment, or
claim is authorized.

## Authoritative EOF Pointer

current_v20_status=v20_carla_route_corridor_revised_map_only_census_independent_review_passed
current_v20_artifact_source_head=a8238ba14b20c43176e4d5889f3eb713e877f249
camp_github_autodl_head=a8238ba14b20c43176e4d5889f3eb713e877f249
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
next_work_target=v20_carla_route_corridor_source_only_fixed_dp_k8_probe_preflight_then_once

## Single Source-Only Fixed-DP K=8 Probe and Hard Stop

At synchronized CAMP/GitHub/AutoDL head
`3b69cde1849d258b9e328abedd3819e232f81b98`, with fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, the no-runtime K=8 preflight
preserved the fixed checkpoint, args, selectors, worker, server contract, and
DP request semantics. It changed only fresh artifact paths, current CAMP head
and runner hash, and the census-frozen contact tolerance:

`/root/autodl-tmp/camp_dp_v20_carla_source_only_k8_probe_preflight_20260714T061756Z`

Root SHA256: `c7b9f855ac4cd5d93b95b52cbac27f79db698adc5b565db8be76338068181a1c`.

The probe was then invoked exactly once. Its guard and execution are:

- `/root/autodl-tmp/camp_dp_v20_carla_source_only_k8_probe_launch_guard_20260714T061756Z`
  with root SHA256
  `0bba2b3f973a8fad936d6a62b58ee85e20952f381c14b777a368f0e41345b27e`;
- `/root/autodl-tmp/camp_dp_v20_carla_source_only_k8_probe_execution_20260714T061756Z`
  with root SHA256
  `14324d41b6eb21db8a374dc1e30677a0ef8b880b68eac81e744f07512fd6f2a2`.

Invocation count is `0 / 1`; wrapper, runner, capture, materialize, CAMP
worker, DP-default worker, and receipt exits are all `0`. The source artifact
retains exit `1` only because its post-runtime validator compared rich capture
route records directly with the census's compact records. Normalizing the same
81 points closes that evidence defect without rerunning the probe:

`/root/autodl-tmp/camp_dp_v20_carla_source_only_k8_probe_evidence_remediation_20260714T062333Z`

Root SHA256: `c6e5a00ab88a3a74129693e360852d08530aa5bdc34544e0f8d03f4b27691299`.
The normalized route SHA256 is the frozen
`4bd077585527913491461dd2d446bcc1621aa44c811ca7f0826e3ef461a783b6`,
and the capture corridor SHA256 equals the census final corridor SHA256
`1fa5173bc1f2d88d7db003357ae214027736d7aff896d39692377d4349bd6114`.

Scientific result:

- candidate tensor before/current/after SHA256:
  `1a32c4f7245281636accd995a423ae248a7dcad5c1ac63a28540646fe358244b`;
- operational Top-1 before/current/after and candidate 0 SHA256:
  `8a566ef7c03445ad5b19ad4ade5382c7e602c3284bd8c528e4bdd1347a266e28`;
- candidate 0 equivalent to operational Top-1: `true`;
- source-complete mask: `[false, false, false, false, false, false, false, false]`;
- source-complete candidate count: `0`;
- paired support / reason: `false / all_k_source_ineligible`;
- selected index: `null`;
- outcome reads / metric calls / holdout reads / simulator arm advances:
  `0 / 0 / 0 / 0`.

The one independent result review recorded `Critical=0`, `Important=0`, and
`Minor=0`, verified the SHA chains and evidence-only remediation, and confirmed
that candidate 0 plus an additional source-complete candidate does not exist:

`/root/autodl-tmp/camp_dp_v20_carla_source_only_k8_probe_result_review_20260714T062838Z`

Root SHA256: `cc5e4424506f2fac72a34caf0e518bde7889af342a440f678daefe3bfa349544`.

This is the authorized hard stop. The probe, route, tolerance, source contract,
or candidate tensor must not be adapted or retried. Tiny matched closed-loop
SafetyCost smoke is not authorized. No closed-loop safety, CAMP-over-DP,
promotion, deployment, activation, or broad claim is supported.

## Authoritative EOF Pointer

current_v20_status=v20_carla_route_corridor_source_only_k8_zero_legal_paired_support_hard_stop_reviewed
current_v20_artifact_source_head=3b69cde1849d258b9e328abedd3819e232f81b98
camp_github_autodl_head=3b69cde1849d258b9e328abedd3819e232f81b98
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
next_work_target=no_further_action_v20_zero_legal_paired_support_honest_source_ineligible_closeout
