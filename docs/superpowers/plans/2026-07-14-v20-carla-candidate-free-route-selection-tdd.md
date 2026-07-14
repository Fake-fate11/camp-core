# V20 Candidate-Free CARLA Route Selection TDD Plan

**Goal:** Replace the failed route start with a deterministic, map-only route
whose start already satisfies the unchanged exactly-one-predecessor contract.

**Frozen inputs:** official CARLA 0.9.16 Town10HD_Opt XODR, route step `5.0 m`,
route length `81`, existing `_waypoint_key`, fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

1. Add a focused failing test to the existing v19 probe test file: canonical
   ambiguous starts are skipped, the first fully unique route is selected,
   and no valid route raises the frozen-window error.
2. Surgically update the existing `_deterministic_route`; add no runner,
   framework, dependency, or general abstraction.
3. Run `py_compile`, focused v19/v20 tests, audit-pointer tests, merged route
   suite, and `git diff --check`.
4. Perform one independent static review. Only Critical/Important findings
   affecting scientific contract, execution correctness, false-success
   evidence, data integrity, or safety boundaries block.
5. Commit/push, AutoDL ff-only sync and verify, then run one preflight and
   exactly one revised map-only census. Any failure is sealed fail-closed; do
   not change route, tolerance, corridor, or source from its result.
