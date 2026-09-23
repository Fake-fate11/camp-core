// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <lanelet2_core/LaneletMap.h>
#include <lanelet2_routing/RoutingGraph.h>
#include <lanelet2_traffic_rules/TrafficRules.h>
#include <nlohmann/json.hpp>
#include <autoware/route_handler/route_handler.hpp>
#include <autoware_planning_msgs/msg/lanelet_route.hpp>

namespace camp {
// Online: supply the map, route lanelets, graph and rules already owned by DP's
// RouteHandler after LaneletMapBin/LaneletRoute callbacks. No OSM reprojection.
// Signal phase is intentionally not inferred from regulatory geometry.
nlohmann::json lanelet_context(const lanelet::LaneletMapConstPtr & map,
  const lanelet::ConstLanelets & route, const lanelet::routing::RoutingGraph & graph,
  const lanelet::traffic_rules::TrafficRules & rules);
nlohmann::json lanelet_context(const autoware::route_handler::RouteHandler & host,
                              const autoware_planning_msgs::msg::LaneletRoute & route);
}
