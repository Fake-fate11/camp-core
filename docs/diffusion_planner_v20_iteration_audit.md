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
