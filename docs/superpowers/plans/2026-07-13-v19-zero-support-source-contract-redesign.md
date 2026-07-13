# V19 Zero-Support Source-Contract Redesign Implementation Plan

> **For agentic workers:** Execute inline on current `main`; subagents are
> forbidden for this task. Follow RED-GREEN TDD and checkpoint only files in
> this plan.

**Goal:** Correct the proven CARLA float32 XODR station tolerance defect while
leaving the unresolved route-window contract unchanged and prohibiting a new
probe.

**Architecture:** Reuse the existing `LiftingTolerances` value and source-probe
harness. Add one named frozen value, test its candidate-independent derivation
and exact use, and change no lifting algorithm, route sample, or DP path.

**Tech Stack:** Python 3.12/3.9, NumPy float32 numeric checks, pytest, existing
CARLA source-probe harness.

## Global Constraints

- Fixed DP stays exactly `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Candidate tensor stays immutable at SHA256
  `8ca8c2e35de6363d40a154033ebee08e326114da0d7ae6790013329988f6a42c`.
- Keep geometry/z tolerances, route construction, route matching, identities,
  eligibility, seeds, A/B/C speed rungs, 14D atoms, affine/simplex/convex math,
  and operational Top-1 rules unchanged.
- Do not start CARLA, DP, a pipeline, a simulator arm, a metric, or an outcome.
- Do not run another K=8 source probe because the route contract is unresolved.

---

### Task 1: Freeze the correct XODR float32 station tolerance

**Files:**

- Modify: `camp_core/tests/test_diffusion_planner_v19_carla_candidate_source_probe.py`
- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py`

**Interface:**

- Produces: module constant `FROZEN_LIFTING_TOLERANCES`.
- Consumed by: the existing `materialize` mode only.
- Does not change: `build_probe_materialization(...)` or any lifting matcher.

- [ ] **Step 1: Add the RED contract test**

Add a test that imports the source-probe module and asserts:

```python
def test_frozen_station_tolerance_covers_carla_float32_xodr_api() -> None:
    probe = _probe()
    bound = 3.0517578125e-05
    allowance = 1e-9
    assert probe.FROZEN_LIFTING_TOLERANCES == LiftingTolerances(
        1.5273609989704584,
        bound + allowance,
        1e-9,
        bound + allowance,
    )
    road_length = 966.8900000000001
    assert abs(float(np.float32(road_length)) - road_length) <= bound
```

- [ ] **Step 2: Run RED and confirm the intended failure**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v19_carla_candidate_source_probe.py -k frozen_station_tolerance -q
```

Expected: fail because `FROZEN_LIFTING_TOLERANCES` does not exist.

- [ ] **Step 3: Implement the minimum GREEN change**

Define exactly one module constant next to the existing seeds:

```python
FROZEN_LIFTING_TOLERANCES = LiftingTolerances(
    1.5273609989704584,
    3.0518578125e-05,
    1e-9,
    3.0518578125e-05,
)
```

Replace only the inline `LiftingTolerances(...)` in `materialize` mode with
`FROZEN_LIFTING_TOLERANCES`.

- [ ] **Step 4: Run GREEN and focused regressions**

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v19_carla_candidate_source_probe.py camp_core\tests\test_carla_exact_speed_source.py -q
py -3.12 -m py_compile scripts\integrations\run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe.py
git diff --check
```

Expected: all tests pass, compilation passes, and diff check is empty.

- [ ] **Step 5: Independent static review and closeout**

Seal source/test SHAs, RED/GREEN output, exact tolerance values, the eight-map
bound/root, CAMP/DP heads, zero runtime/outcome counters, and an independent
review. Update the v19 audit/current-status tuple, commit, push, AutoDL ff-only,
and reread EOF. The next target is honest no-claim v19 closeout; do not create a
runtime preflight or source-probe command.
