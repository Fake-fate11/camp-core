// SPDX-License-Identifier: Apache-2.0
// Offline example uses the same installed official projector and centerline
// helpers as lanelet2_map_loader. Online users pass the already loaded map.
#include "camp/lanelet_context.hpp"
#include <autoware/geography_utils/lanelet2_projector.hpp>
#include <autoware/map_projection_loader/map_projection_loader.hpp>
#include <autoware_lanelet2_extension/utility/utilities.hpp>
#include <autoware/lanelet2_utils/conversion.hpp>
#include <lanelet2_io/Io.h>
#include <lanelet2_traffic_rules/TrafficRulesFactory.h>
#include <fstream>
#include <iostream>
int main(int argc, char ** argv) {
  try {
    if (argc != 5) throw std::invalid_argument("usage: camp_export_map map.osm projector.yaml route_ids.json output.json");
    auto info = autoware::map_projection_loader::load_info_from_yaml(argv[2]);
    auto projector = autoware::geography_utils::get_lanelet2_projector(info);
    lanelet::ErrorMessages errors;
    lanelet::LaneletMapPtr map = lanelet::load(argv[1], *projector, &errors);
    for (const auto & e : errors) std::cerr << e << '\n';
    if (!errors.empty()) throw std::runtime_error("official lanelet parser reported errors");
    lanelet::utils::overwriteLaneletsCenterlineWithWaypoints(map, 5.0, false);
    // Same binary conversion used by the installed official map loader.
    namespace ll_utils = autoware::experimental::lanelet2_utils;
    auto binary = ll_utils::to_autoware_map_msgs(map);
    auto loaded = ll_utils::from_autoware_map_msgs(binary);
    double drift = 0.;
    for (const auto & p : map->pointLayer) {
      const auto q = loaded->pointLayer.get(p.id());
      drift = std::max(drift, (p.basicPoint() - q.basicPoint()).norm());
    }
    auto [graph, rules] = ll_utils::instantiate_routing_graph_and_traffic_rules(loaded);
    std::ifstream route_stream(argv[3]); auto ids = nlohmann::json::parse(route_stream);
    lanelet::ConstLanelets route;
    for (const auto & id : ids) route.push_back(loaded->laneletLayer.get(id.get<lanelet::Id>()));
    auto result = camp::lanelet_context(loaded, route, *graph, *rules);
    if (!route.empty()) {
      autoware::route_handler::RouteHandler host;
      host.setMap(binary);
      autoware_planning_msgs::msg::LaneletRoute message;
      message.header.frame_id = "map";
      message.start_pose.position = ll_utils::to_ros(route.front().centerline().front());
      message.start_pose.orientation.w = 1.0;
      message.goal_pose.position = ll_utils::to_ros(route.back().centerline().back());
      message.goal_pose.orientation.w = 1.0;
      for (const auto & ll : route) {
        autoware_planning_msgs::msg::LaneletSegment segment;
        segment.preferred_primitive.id = ll.id();
        segment.preferred_primitive.primitive_type = "lane";
        segment.primitives.push_back(segment.preferred_primitive);
        message.segments.push_back(segment);
      }
      host.setRoute(message);
      const auto host_result = camp::lanelet_context(host, message);
      if (host_result["route_lanelet_ids"] != result["route_lanelet_ids"])
        throw std::runtime_error("RouteHandler route IDs differ");
      result["route_segments"] = host_result["route_segments"];
      result["route_handler_example"] = true;
    }
    result["projector"] = {{"projector_type", info.projector_type}, {"mgrs_grid", info.mgrs_grid},
                            {"vertical_datum", info.vertical_datum}};
    result["binary_roundtrip_max_coordinate_error_m"] = drift;
    result["binary_bytes"] = binary.data.size();
    result["osm_source"] = argv[1]; result["projector_source"] = argv[2];
    std::ofstream(argv[4]) << result.dump(2) << '\n';
    std::cout << "lanelets=" << loaded->laneletLayer.size() << " binary_max_drift=" << drift << '\n';
  } catch (const std::exception & e) { std::cerr << e.what() << '\n'; return 1; }
}
