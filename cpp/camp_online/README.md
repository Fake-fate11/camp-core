# CAMP online library

This C++17 library scores an original candidate pool with an exported CAMP
Fixed or Scene model. The scorer depends on `nlohmann_json`, not ROS, the
generator, a map loader, or a training solver. A separate optional library
provides the Lanelet2/RouteHandler map bridge.

## Build, test and install the scorer

With a C++17 compiler, CMake and the `nlohmann_json` CMake package installed:

```sh
cmake -S cpp/camp_online -B build/camp
cmake --build build/camp
ctest --test-dir build/camp --output-on-failure
./build/camp/camp_score deployment/scene.json saved_ticks.json
```

Install it for another CMake project with:

```sh
cmake --install build/camp --prefix install/camp
cmake -S cpp/camp_online/examples/installed -B build/camp-consumer \
  -DCMAKE_PREFIX_PATH="$PWD/install/camp"
cmake --build build/camp-consumer
```

The installed target is `camp::camp_online`. The consumer builds against the
installed package, not source-tree include paths. For a multi-configuration
generator, add the same configuration to build, test and install commands.

CTest covers hand-calculated Fixed and Scene scores, raw affine weights,
status-specific heads, original-row tie breaking, export/pool K agreement,
invalid inputs, reset and encoder padding masks. These are interface and
numerical contract tests, not evidence of driving quality or ROS integration.

## Selection contract

Export either model using `camp_core.dp.export_cpp`. Link `camp_online` and call:

```cpp
#include <camp/selector.hpp>
camp::Selector fixed("fixed.json"), scene("scene.json");
// raw_atoms[k][j]: the existing 16-atom materializer output for the whole pool.
// status[j] is shared by every row. Unavailable entries may be NaN, not zero.
const auto phi = camp::masked_mean(encoder_tokens, encoder_padding_mask);
auto result = scene.select(raw_atoms, status, phi);
auto selected_trajectory = original_candidates.at(result.selected_row);
scene.reset();  // Clear cached result at an episode boundary.
```

The host continues to own the previous actually executed plan and its clock;
reset that materializer state at the same episode boundary. `Selector` neither
claims an unexecuted choice was executed nor changes candidate trajectories.
The class receives atoms, not arbitrary ROS messages; it does not replace the
host's existing atom materializer. Python's full tensor-to-atom selector remains
the executable reference for those 16 formulas.

Scene weights are exactly `Theta * [phi;1]`, without softmax, nonnegative clipping
or inference-time simplex projection. Observed atoms alone use existing scales
and clipping to [0,10]. Fixed ignores phi and uses its bias. The exported
`observed`, `not_applicable` and `typed_missing` pattern chooses the head;
unavailable atoms are not converted to zero observations. An unexported status
pattern, invalid observed atom, invalid Scene embedding or nonfinite score is
rejected. Ties keep the first original row. Encoder padding masks are true for
**invalid** tokens, as in DP.

The scoring executable takes a JSON array of ticks with `raw_atoms` (K by 16),
`status` (16 strings), and either `phi` or `tokens` plus `padding_mask`. Fixed
ticks can omit `phi`; Scene ticks cannot omit their embedding. JSON `null` atom
entries represent unavailable values and are valid only in unobserved columns.

### Candidate-pool K

`candidate_pool_k` is an explicit deployment-export contract: C++ requires
exactly that many original rows and returns one score per row. It does not
truncate a larger pool, pad a smaller pool, or always use a K=8 prefix.

The same trained weights can be exported separately for K=8, K=16 and K=32 with
the Python export API, then used to score the corresponding complete pools.
Use the matching deployment file for each K; a K=8 export deliberately rejects
K=16 or K=32 inputs. See the [Python library documentation](../../docs/camp_python_library.md)
for export and candidate construction. This interface support does not change
the upstream planner's K=8 default, its generator, candidate ordering, or atom
definitions, and does not establish equivalent outcomes across different pools.

## Official map bridge

The bridge is built only when requested and requires a configured ROS/Autoware
underlay. Source that environment's setup files before configuring. The library
uses `autoware_planning_msgs`, `autoware_route_handler`, `lanelet2_core`,
`lanelet2_routing` and `lanelet2_traffic_rules`, in addition to `nlohmann_json`;
`ament_cmake` supplies the build helpers.

Build and install the bridge without the offline map-loader example:

```sh
cmake -S cpp/camp_online -B build/camp-map -DCAMP_AUTOWARE_MAP_BRIDGE=ON
cmake --build build/camp-map
cmake --install build/camp-map --prefix install/camp-map
```

Installed consumers request the component explicitly:

```cmake
find_package(camp_online CONFIG REQUIRED COMPONENTS lanelet_context)
target_link_libraries(my_map_adapter PRIVATE camp::camp_lanelet_context)
```

`find_package(camp_online CONFIG REQUIRED)` alone still loads only the scorer,
even when the same installation also contains the bridge. The optional
installed-consumer example checks the bridge's public headers and linkage:

```sh
cmake -S cpp/camp_online/examples/installed -B build/camp-map-consumer \
  -DCMAKE_PREFIX_PATH="$PWD/install/camp-map" -DCAMP_INSTALLED_MAP_BRIDGE=ON
cmake --build build/camp-map-consumer
ctest --test-dir build/camp-map-consumer --output-on-failure
```

Online code should call
`camp::lanelet_context(const autoware::route_handler::RouteHandler &,
const autoware_planning_msgs::msg::LaneletRoute &)` with DP/RouteHandler's
already loaded Lanelet2 map and current route. The lower-level overload accepts
the map, ordered route lanelets, routing graph and traffic rules directly.
Do not reproject the map or parse an independent OSM inside CAMP. Keep the
original LaneletMapBin and LaneletRoute ownership in the host. The snapshot
retains IDs, geometry, original attributes, regulatory references and directed
successors; the original map remains authoritative for full ROS routing.

For offline map export, `CAMP_AUTOWARE_MAP_EXAMPLE=ON` enables the bridge and
builds `camp_export_map`. This additionally requires
`autoware_geography_utils`, `autoware_map_projection_loader`,
`autoware_lanelet2_extension`, `autoware_lanelet2_utils`, `lanelet2_io` and
`autoware_map_msgs` from the target Autoware installation:

```sh
cmake -S cpp/camp_online -B build/camp-map -DCAMP_AUTOWARE_MAP_EXAMPLE=ON
cmake --build build/camp-map
build/camp-map/camp_export_map lanelet2_map.osm map_projector_info.yaml route_ids.json map.json
```

The executable uses the installed official YAML projection helper, Lanelet2
loader, centerline helper and LaneletMapBin conversion. It reports the maximum
coordinate difference after binary conversion and compares route IDs through
RouteHandler when a nonempty route is supplied. Those checks do not replace
validation of the target map, route or ROS integration. `AutowareMap` in Python
consumes the projected coordinates directly and transforms them to the same
ego frame as the DP arrays; it does not project latitude/longitude again.

Traffic signal state is a separate, timestamped host input. Regulatory light
geometry is preserved but never interpreted as a red/green phase. The existing
Python signal-source semantics, including missingness, remain unchanged.
