# V20 Offline CARLA Route-Corridor Contact-Tolerance Census Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:test-driven-development` and
> `superpowers:verification-before-completion` task by task.

**Goal:** Freeze one candidate-independent route-boundary contact tolerance
from the sealed official Town10HD_Opt map before any new K=8 source probe.

**Architecture:** Add one runner around the existing deterministic route,
corridor builder, frozen ceiling, and tolerance freezer. The runner receives an
offline native CARLA map, makes one measurement pass and one final pass, and
atomically writes one receipt. No builder refactor, dependency, server, or new
orchestrator is needed.

## Frozen authority

- Gate start CAMP head:
  `9537f1998100a32b74cdb6cc6dc36db4837c77f4`.
- Fixed DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Official CARLA: `0.9.16`.
- Map name: `Carla/Maps/Town10HD_Opt`.
- XODR path:
  `/root/autodl-tmp/carla_0.9.16/runtime/CarlaUE4/Content/Carla/Maps/OpenDrive/Town10HD_Opt.xodr`.
- XODR SHA256:
  `5d883b799f634030af92be1e9d79d107845540ba04338e8c60e095be1aef7be7`.
- CARLA source root SHA256:
  `2d9df1315e941f60caf650fb7c8b9ea72b960bb880066355081b71eaedf912ce`.
- Client root: `/root/autodl-tmp/camp_v19_carla_client`.
- `libcarla.cpython-312-x86_64-linux-gnu.so` SHA256:
  `c99a3754561a4ac910a584cc31952a10cbc21cbe1e8b14c032c1b31d5afbb6e2`.
- `CLIENT_SHA256SUMS` SHA256:
  `ba3b3d97783a16211f1ed855b0c2640e58ed97fd5258cf17ff99a00037683f3e`.
- Route: exactly `81` points at `5.0 m`.
- First-pass ceiling:
  `FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m`.

The fixed DP repository, checkpoint, config, request, candidate tensor,
selector, affine/simplex/convex contracts, outcomes, future labels, holdout,
formal seeds, Full36, promotion, deployment, activation, and claims are out of
scope.

## Files and interfaces

Create only:

- `scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py`
- `camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py`

Do not modify the corridor builder or the existing source-probe runner.

The runner exposes:

```python
def census_route_corridor_contact_tolerance(
    *,
    map_api: Any,
    opendrive_xml: str,
    camp_head: str,
) -> dict[str, Any]:
```

It imports and reuses exactly these existing contracts:

```python
from camp_core.integrations.carla_causal_adapter import (
    build_pre_generation_route_corridor,
)
from camp_core.integrations.carla_exact_speed_source import (
    canonical_json_sha256,
    freeze_lifting_tolerances,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe import (
    FIXED_DP_HEAD,
    FROZEN_LIFTING_TOLERANCES,
    _deterministic_route,
    _write_json_atomic,
)
```

The thin CLI accepts only `--camp-head` and `--output-json`. It reads the
frozen XODR path, verifies its SHA, imports the sealed client, and constructs:

```python
map_api = carla.Map("Carla/Maps/Town10HD_Opt", opendrive_xml)
```

There is no host, port, server argv, `carla.Client`, world, actor, tick, DP,
candidate, selector, eligibility, metric, outcome, or holdout interface.

The JSON receipt schema is
`dp_camp_v20_carla_route_corridor_contact_tolerance_census_v1` and contains:

```text
schema_version
camp_gate_start_head, camp_execution_head, fixed_dp_head
carla_version, carla_source_root_sha256, map_name
xodr_sha256, map_sha256, route_sha256
measurement_corridor_sha256, final_corridor_sha256
corridor_evidence_sha256, boundary_receipts_sha256
route_point_count, route_sample_step_m
measurement_ceiling_m, raw_contact_gaps_m, max_contact_gap_m
coordinate_scale_m, allowance_formula, allowance_m
frozen_contact_tolerance_m, boundary_identity_receipts
builder_contact_tolerances_m, call_counters
forbidden_access_counters, receipt_sha256
```

`forbidden_access_counters` has exact zero values for server connections,
server launches, world gets, actor spawns, world ticks, candidate reads, DP
request/worker calls, outcome reads, metric calls, future-label reads, holdout
reads, selector calls, and eligibility calls.

## Task 1: Add RED runner tests

**Files:**

- Create: `camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py`

Use fake map/waypoint objects only. The fake map supplies `name`,
`generate_waypoints`, `get_waypoint_xodr`, and raising actor/tick/server methods.
The route is an 81-waypoint, 5.0 m chain with one unique predecessor and one
identity boundary.

Add exactly these nine test cases (use local loops for the two-value rejection
checks so collection remains nine cases):

1. identical fake maps yield byte-identical receipts and hashes;
2. the first builder tolerance is exactly the frozen geometry ceiling, the
   second is exactly the returned frozen tolerance, and there are two calls;
3. `coordinate_scale_m` uses only finite entry/exit XYZ values, and
   `allowance_m == max(1e-9, 64 * math.ulp(coordinate_scale_m))`;
4. a nonfinite boundary coordinate fails before the freeze call;
5. zero or two predecessors fail closed;
6. contact above the frozen measurement ceiling fails without a second pass;
7. second-pass map/route/boundary drift or changed maximum fails closed;
8. forbidden fields are absent outside the zero counter object, and fake
   server/actor/tick counters remain zero;
9. the CLI constructs only offline `carla.Map`, writes one atomic receipt, and
   rejects either an existing output or `.tmp` path before reading XODR.

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py -q
```

Expected RED: collection fails with `ModuleNotFoundError` for the missing
census runner. No production file exists yet.

## Task 2: Implement the minimum runner

**Files:**

- Create: `scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py`
- Test: `camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py`

Implement the function in this fixed order:

1. Require a 40-hex `camp_head`, exact map name, and exact XODR SHA.
2. Call `_deterministic_route(map_api, 5.0, 81)` once; require 81 points and
   hash canonical road/section/lane/station/XYZ waypoint records.
3. Call `build_pre_generation_route_corridor` once with the route, exact XODR,
   `route_sample_step_m=5.0`, frozen station allowance, and
   `contact_tolerance_m=FROZEN_LIFTING_TOLERANCES.geometry_epsilon_m`.
4. Extract every non-`None` `contact_to_next_m` in order. Require exactly one
   finite nonnegative value per adjacent boundary identity, and require their
   maximum to equal `max_contact_gap_m`. Builder failure or ceiling excess is
   terminal; never widen the ceiling.
5. Flatten only `entry_xyz` and `exit_xyz` from the returned boundary receipts.
   Require nonempty finite coordinates and set
   `coordinate_scale_m=max(abs(value) for value in coordinates)`; require it
   positive.
6. Call `freeze_lifting_tolerances` exactly once with:

```python
max_chord_error_m=max_contact_gap_m
max_station_roundtrip_error_m=0.0
max_z_roundtrip_error_m=0.0
coordinate_scale_m=coordinate_scale_m
```

7. Use only the returned `geometry_epsilon_m`. Record
   `allowance_m=geometry_epsilon_m-max_contact_gap_m` and the literal formula
   `max(1e-9, 64*ulp(coordinate_scale_m))`; do not duplicate the formula in
   production code.
8. Call the builder a second and final time with the same inputs and the frozen
   geometry epsilon as `contact_tolerance_m`.
9. Require canonical bytes to match for `map_sha256`, `route_samples`,
   `directed_edges`, `identity_directions`, `predecessor_receipt`, and
   `boundary_receipts`; require the same raw gaps/maximum and final
   `max_contact_gap_m <= frozen_contact_tolerance_m`.
10. Hash the shared evidence projection, boundary receipts, final receipt
    payload, and return it. Do not retain candidate/outcome/selector fields.

The CLI checks both output and `output.json.tmp` are absent before CARLA import
or XODR read, verifies the sealed module/path hashes, constructs one offline
map, calls the function once, and reuses `_write_json_atomic`.

Run GREEN:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor.py -q
py -3.12 -m py_compile scripts\integrations\census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py
git diff --check
```

Expected GREEN: `25 passed`, compile exits `0` without output, and the diff
check is silent.

Run the current seven-file `159`-test suite plus the nine new cases:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core;F:\camp_core-main'
py -3.12 -m pytest camp_core\tests\test_carla_exact_speed_source.py camp_core\tests\test_carla_causal_adapter.py camp_core\tests\test_diffusion_planner_v19_carla_candidate_source_probe.py camp_core\tests\test_diffusion_planner_v19_carla_exact_speed_sources.py camp_core\tests\test_diffusion_planner_v19_dp_worker.py camp_core\tests\test_diffusion_planner_v19_nuplan_bridge.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor.py camp_core\tests\test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py -q
```

Expected: `168 passed`.

Commit only the runner and test:

```powershell
git add -- scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py camp_core/tests/test_diffusion_planner_v20_carla_route_corridor_contact_tolerance_census.py
git commit -m "Add v20 map-only contact tolerance census"
```

## Task 3: Plan static review, then no-run preflight

Static review must pass before Task 2 begins. Review the exact function/CLI,
two-pass rule, receipt fields, sealed constants, tests, artifact contract, and
stop rules. It runs no CARLA import or map construction.

After the verified Task 2 commit is pushed by an authorized controller, create
one immutable preflight root:

```text
/root/autodl-tmp/camp_dp_v20_carla_route_corridor_contact_tolerance_census_preflight_<UTC>/
  HEADS
  COMMAND
  stdout
  stderr
  preflight.json
  preflight.md
  SHA256SUMS
  ROOT_SHA256
```

The preflight freezes and verifies:

- exact local/origin CAMP head and tracked-clean tree;
- fixed-DP head and tracked-clean tree;
- resolved Python 3.12 executable, CARLA module path, client root, client
  manifest SHA, and `libcarla` SHA;
- exact offline constructor text
  `carla.Map("Carla/Maps/Town10HD_Opt", opendrive_xml)`;
- exact XODR path/name/hash and CARLA source-root hash;
- runner/dependency/test source hashes and exact execution argv/env;
- at least `10737418240` free bytes;
- absent execution output and `.tmp` paths;
- no related jobs and no listeners on CARLA ports `2000/2001`;
- no host/port/server argv anywhere in `COMMAND`.

Any remote git/network command begins with:

```bash
source /etc/network_turbo >/dev/null 2>&1 || true
```

The preflight may import the client module for path/version evidence, but must
not construct a map, connect/launch a server, or run the census.

## Task 4: Execute exactly one offline census

Only an independently reviewed, passing preflight authorizes execution. Create
one new absent execution root with the same eight artifact names, replacing
`preflight.json/.md` with `receipt.json/result.md`.

Freeze this argv in `COMMAND` before execution:

```bash
PYTHONPATH=/root/autodl-tmp/camp_v19_carla_client:/root/autodl-tmp/camp_core/camp_core:/root/autodl-tmp/camp_core \
<FROZEN_PYTHON_3_12> \
  /root/autodl-tmp/camp_core/scripts/integrations/census_diffusion_planner_dp_camp_v20_carla_route_corridor_contact_tolerance.py \
  --camp-head <FROZEN_CAMP_HEAD> \
  --output-json <ABSENT_EXECUTION_ROOT>/receipt.json
```

Run it once. Do not retry. Preserve exit status, stdout, and stderr even on
failure. Seal all regular files into `SHA256SUMS`, then hash that manifest into
`ROOT_SHA256`.

Stop failed if the output/temp path exists; any sealed head/hash/path drifts;
the map constructor fails; the route is not 81 at 5.0 m; predecessor/boundary
evidence is absent, ambiguous, nonfinite, or over the measurement ceiling; the
second pass drifts; any forbidden counter is nonzero; or receipt sealing fails.
Do not change tolerance, route, XODR, source rules, or rerun after seeing data.

## Task 5: Independent result review and next boundary

Review without rerunning the census. Rehash `HEADS`, `COMMAND`, stdout, stderr,
JSON, MD, `SHA256SUMS`, and `ROOT_SHA256`; recompute every receipt hash and the
allowance using the existing freezer; confirm exactly two builder calls, exact
tolerances, stable evidence, final gap within tolerance, all forbidden counters
zero, tracked-clean heads, and no server/listener/process evidence.

Only a passing independent review may set the next target to exactly one
source-only fixed-DP K=8 probe under the already approved v20 design. That
later probe keeps DP/candidate/request/config/checkpoint bytes fixed and may
not use outcomes, future labels, holdout, promotion, deployment, activation,
formal seeds, Full36, or make a broad performance/safety claim.

Gate order is fixed:

```text
plan static review
-> TDD runner plus no-run preflight
-> exactly one offline map-only census
-> independent result review
-> exactly one source-only fixed-DP K=8 probe
```
