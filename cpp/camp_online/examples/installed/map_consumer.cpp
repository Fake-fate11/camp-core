// SPDX-License-Identifier: Apache-2.0
#include <camp/lanelet_context.hpp>
#include <lanelet2_traffic_rules/TrafficRulesFactory.h>
#include <iostream>
#include <memory>

int main() {
  try {
    const auto map = std::make_shared<lanelet::LaneletMap>();
    const auto rules = lanelet::traffic_rules::TrafficRulesFactory::create(
      lanelet::Locations::Germany, lanelet::Participants::Vehicle);
    const auto graph = lanelet::routing::RoutingGraph::build(*map, *rules);
    const auto snapshot = camp::lanelet_context(map, {}, *graph, *rules);
    return snapshot.at("lanelets").empty() && snapshot.at("route_lanelet_ids").empty() ? 0 : 1;
  } catch (const std::exception & e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
