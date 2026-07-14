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
