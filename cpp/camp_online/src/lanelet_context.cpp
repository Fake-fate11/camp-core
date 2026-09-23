// SPDX-License-Identifier: Apache-2.0
#include "camp/lanelet_context.hpp"
#include <lanelet2_core/primitives/RegulatoryElement.h>

namespace camp {
using nlohmann::json;
namespace {
template<class T> json attributes(const T & item) {
  json a = json::object();
  for (const auto & p : item.attributes()) a[p.first] = p.second.value();
  return a;
}
template<class T> json points(const T & line) {
  json out = json::array();
  for (const auto & p : line) out.push_back({p.x(), p.y(), p.z()});
  return out;
}
template<class T> json point_ids(const T & line) {
  json out = json::array();
  for (const auto & p : line) out.push_back(p.id());
  return out;
}
}
json lanelet_context(const lanelet::LaneletMapConstPtr & map, const lanelet::ConstLanelets & route,
                    const lanelet::routing::RoutingGraph & graph,
                    const lanelet::traffic_rules::TrafficRules & rules) {
  json result{{"frame_id", "map"}, {"source", "Autoware_projected_LaneletMap"},
              {"route_lanelet_ids", json::array()}, {"lanelets", json::array()},
              {"line_strings", json::array()}, {"polygons", json::array()},
              {"regulatory_elements", json::array()}};
  for (const auto & ll : route) result["route_lanelet_ids"].push_back(ll.id());
  for (const auto & ll : map->laneletLayer) {
    json following = json::array(), regs = json::array();
    for (const auto & next : graph.following(ll)) following.push_back(next.id());
    for (const auto & reg : ll.regulatoryElements()) regs.push_back(reg->id());
    // Traffic rules may supply a jurisdictional default; preserve that distinction.
    auto speed = rules.speedLimit(ll);
    result["lanelets"].push_back({{"id", ll.id()}, {"attributes", attributes(ll)},
      {"left_id", ll.leftBound().id()}, {"right_id", ll.rightBound().id()},
      {"left", points(ll.leftBound())}, {"right", points(ll.rightBound())},
      {"centerline", points(ll.centerline())}, {"polygon", points(ll.polygon3d())},
      {"following_ids", following}, {"regulatory_ids", regs},
      {"vehicle_passable", rules.canPass(ll)}, {"rule_speed_limit_mps", speed.speedLimit.value()},
      {"explicit_speed_limit", ll.hasAttribute("speed_limit")}});
  }
  for (const auto & line : map->lineStringLayer)
    result["line_strings"].push_back({{"id", line.id()}, {"attributes", attributes(line)},
      {"point_ids", point_ids(line)}, {"points", points(line)}});
  for (const auto & poly : map->polygonLayer)
    result["polygons"].push_back({{"id", poly.id()}, {"attributes", attributes(poly)},
      {"point_ids", point_ids(poly)}, {"points", points(poly)}});
  for (const auto & reg : map->regulatoryElementLayer) {
    json roles = json::object();
    for (const auto & role : reg->getParameters()) {
      json ids = json::array();
      for (const auto & parameter : role.second) ids.push_back(lanelet::traits::getId(parameter));
      roles[role.first] = ids;
    }
    result["regulatory_elements"].push_back({{"id", reg->id()}, {"attributes", attributes(*reg)}, {"roles", roles}});
  }
  return result;
}
json lanelet_context(const autoware::route_handler::RouteHandler & host,
                     const autoware_planning_msgs::msg::LaneletRoute & message) {
  lanelet::ConstLanelets route;
  json segments = json::array();
  auto map = host.getLaneletMapPtr();
  for (const auto & segment : message.segments) {
    json primitives = json::array();
    for (const auto & primitive : segment.primitives) {
      primitives.push_back({{"id", primitive.id}, {"type", primitive.primitive_type}});
      route.push_back(map->laneletLayer.get(primitive.id));
    }
    segments.push_back({{"preferred_id", segment.preferred_primitive.id}, {"primitives", primitives}});
  }
  auto result = lanelet_context(map, route, *host.getRoutingGraphPtr(), *host.getTrafficRulesPtr());
  result["route_segments"] = segments;
  result["route_frame_id"] = message.header.frame_id;
  return result;
}
}
