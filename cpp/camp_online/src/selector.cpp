// Copyright 2026 Xinchen Lin
// SPDX-License-Identifier: Apache-2.0
// The status lookup, scaled atom sum and stable argmin reuse the existing
// CAMP ranker prototype; affine Scene heads are the only scoring extension.
#include "camp/selector.hpp"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <stdexcept>

namespace camp {
namespace {
const std::array<std::string, 16> names{
  "predicted_obb_collision_exposure_fraction", "ttc_deficit_0_95s",
  "dynamic_clearance_buffer_deficit", "overspeed_integral_m2_per_s",
  "full_footprint_road_exit_severity_s", "reverse_progress_severity_m",
  "red_light_crossing_exposure_fraction", "red_stopping_margin_m2_s",
  "route_progress_shortfall_m", "longitudinal_acceleration_energy_s",
  "lateral_acceleration_energy_s", "yaw_rate_energy_s", "yaw_acceleration_energy_s",
  "longitudinal_jerk_energy_s", "jerk_magnitude_energy_s",
  "previous_plan_execution_transition_rms"};
void require(bool value, const char * message) {
  if (!value) throw std::invalid_argument(message);
}
}
Selector::Selector(const std::filesystem::path & path) {
  std::ifstream stream(path);
  if (!stream) throw std::runtime_error("cannot open CAMP model");
  const auto root = nlohmann::json::parse(stream);
  require(root.at("format_version") == 2, "expected CAMP affine export version 2");
  require(root.at("atom_names").get<std::array<std::string, 16>>() == names, "atom order differs");
  k_ = root.at("candidate_pool_k"); width_ = root.at("theta_width");
  const std::string kind = root.at("model_kind");
  scene_ = kind == "scene";
  require(k_ > 0 && (scene_ ? width_ > 2 : (kind == "fixed" && (width_ == 1 || width_ == 2))),
          "invalid model dimensions");
  scales_ = root.at("scales").get<Atoms>();
  for (double s : scales_) require(std::isfinite(s) && s > 0, "invalid atom scale");
  const auto & t = root.at("transition_scales");
  transition_ = {t.at("position_m"), t.at("yaw_rad"), t.at("longitudinal_velocity_mps")};
  for (double s : transition_) require(std::isfinite(s) && s > 0, "invalid transition scale");
  for (const auto & row : root.at("patterns")) {
    Head h{row.at("status").get<Status>(), row.at("active").get<std::vector<std::size_t>>(),
           row.at("theta").get<std::vector<std::vector<double>>>()};
    std::vector<std::size_t> active;
    for (std::size_t j = 0; j < atom_count; ++j) {
      const auto & s = h.status[j];
      require(s == "observed" || s == "not_applicable" || s == "typed_missing", "invalid status");
      if (s == "observed") active.push_back(j);
    }
    require(active == h.active && h.theta.size() == active.size(), "head dimensions differ");
    for (const auto & coefficients : h.theta) {
      require(coefficients.size() == width_, "theta width differs");
      for (double v : coefficients) require(std::isfinite(v), "nonfinite theta");
    }
    heads_.push_back(std::move(h));
  }
  require(!heads_.empty(), "model has no status heads");
}
Result Selector::select(const std::vector<Atoms> & raw, const Status & status,
                        const std::vector<double> & phi) {
  require(raw.size() == k_, "pool size differs from export");
  auto h = std::find_if(heads_.begin(), heads_.end(), [&](const Head & p) { return p.status == status; });
  require(h != heads_.end(), "model has no head for this status pattern");
  std::vector<double> z(width_, 0.0); z.back() = 1.0;
  if (scene_) {
    require(phi.size() + 1 == width_, "Scene embedding width differs");
    for (std::size_t j = 0; j < phi.size(); ++j) {
      require(std::isfinite(phi[j]), "nonfinite phi"); z[j] = phi[j];
    }
  }
  Result result;
  for (const auto & coefficients : h->theta) {
    double w = 0.0;
    for (std::size_t j = 0; j < width_; ++j) w += coefficients[j] * z[j];
    require(std::isfinite(w), "nonfinite affine weight");
    result.active_weights.push_back(w);  // No inference-time simplex projection.
  }
  for (const auto & row : raw) {
    double cost = 0.0;
    for (std::size_t j = 0; j < h->active.size(); ++j) {
      auto a = h->active[j];
      require(std::isfinite(row[a]) && row[a] >= 0, "invalid observed atom");
      cost += std::clamp(row[a] / scales_[a], 0.0, 10.0) * result.active_weights[j];
    }
    require(std::isfinite(cost), "nonfinite score");
    result.scores.push_back(cost);
  }
  result.selected_row = std::min_element(result.scores.begin(), result.scores.end()) - result.scores.begin();
  last_result_ = result;
  return result;
}
std::vector<double> masked_mean(const std::vector<std::vector<double>> & tokens,
                               const std::vector<bool> & padding_mask) {
  require(tokens.size() == padding_mask.size(), "token mask size differs");
  require(!tokens.empty(), "empty tokens");
  std::vector<double> result(tokens.front().size(), 0.0);
  std::size_t n = 0;
  for (std::size_t i = 0; i < tokens.size(); ++i) {
    require(tokens[i].size() == result.size(), "token widths differ");
    if (padding_mask[i]) continue;
    ++n;
    for (std::size_t j = 0; j < result.size(); ++j) {
      require(std::isfinite(tokens[i][j]), "nonfinite valid token"); result[j] += tokens[i][j];
    }
  }
  require(n > 0, "no valid encoder tokens");
  for (double & v : result) v /= static_cast<double>(n);
  return result;
}
}  // namespace camp
